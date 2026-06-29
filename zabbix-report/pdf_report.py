"""
Geracao do PDF operacional do relatorio Zabbix.

Este modulo mantem a escrita manual do PDF separada do fluxo principal. Ele nao
consulta o Zabbix nem conhece argumentos de terminal; recebe dados prontos e
cria o arquivo PDF final.
"""

def pdf_escape(value):
    """
    Prepara texto para ser escrito dentro de um stream PDF.

    O PDF manual usa parênteses para delimitar texto. Por isso, barras,
    parênteses e quebras de linha precisam ser escapados para não corromper o
    arquivo gerado.
    """

    # Garante que None vire string vazia e converte caracteres para cp1252,
    # codificação compatível com as fontes Type1 usadas no PDF.
    text = str(value or "")
    data = text.encode("cp1252", errors="replace")

    return (
        data
        .replace(b"\\", b"\\\\")
        .replace(b"(", b"\\(")
        .replace(b")", b"\\)")
        .replace(b"\r", b" ")
        .replace(b"\n", b" ")
    )


def wrap_text(value, max_chars):
    """
    Quebra textos longos em linhas menores para caber nas colunas do PDF.

    Como o PDF é montado manualmente, não existe quebra automática de linha. A
    função simula esse comportamento usando um limite aproximado de caracteres.
    """

    # split() separa por espaços e remove espaços repetidos, facilitando montar
    # linhas com tamanho previsível.
    words = str(value or "").split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()

        # Enquanto a palavra couber na linha atual, ela é acumulada.
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)

            # Se uma palavra isolada for grande demais, corta no limite para
            # evitar que ela invada a próxima coluna do PDF.
            current = word[:max_chars]

    if current:
        lines.append(current)

    return lines or [""]


def add_pdf_text(commands, x, y, text, size=8, font="F1", color=(0.05, 0.14, 0.22)):
    """
    Adiciona um comando de texto ao conteúdo de uma página PDF.

    commands é uma lista de bytes que representa o stream da página. A função
    centraliza a sintaxe PDF para que as páginas possam chamar apenas com
    coordenadas, texto, tamanho e fonte.
    """

    # Define a cor antes de cada texto. Sem isso, o PDF reutiliza a ultima cor
    # de preenchimento usada em fundos e o texto pode ficar apagado.
    commands.append(
        b"%.2f %.2f %.2f rg\n" % (
            color[0],
            color[1],
            color[2],
        )
    )

    # BT/ET iniciam e encerram um bloco de texto no PDF. Td posiciona o texto,
    # Tf escolhe fonte/tamanho e Tj desenha a string escapada.
    commands.append(
        b"BT /%b %d Tf %.2f %.2f Td (%b) Tj ET\n" % (
            font.encode("ascii"),
            size,
            x,
            y,
            pdf_escape(text)
        )
    )


def build_report_summary(incidents):
    """
    Calcula indicadores usados no HTML e na primeira página do PDF.

    O resumo evita recalcular contagens em vários pontos do código e concentra
    totais por severidade, equipamento e hosts mais afetados.
    """

    # incident_key agrupa repeticoes do mesmo problema no mesmo equipamento.
    # Assim distinguimos "eventos gerados pelo Zabbix" de "incidentes unicos".
    unique_incidents = {
        item["incident_key"]: item
        for item in incidents
    }

    unique_total = len(unique_incidents)
    unique_open = sum(
        1
        for item in unique_incidents.values()
        if item["status"] == "Aberto"
    )
    unique_resolved = unique_total - unique_open
    repeated_events = max(0, len(incidents) - unique_total)

    # Counter conta quantas vezes cada categoria aparece na lista de eventos.
    severity_counter = Counter(
        item["severity"]
        for item in incidents
    )
    status_counter = Counter(
        item["status"]
        for item in incidents
    )
    unit_counter = Counter(
        item["unit"]
        for item in incidents
    )
    equipment_counter = Counter(
        item["equipment"]
        for item in incidents
    )
    host_counter = Counter(
        item["host"]
        for item in incidents
        if item["host"] != "N/A"
    )

    total = len(incidents)
    avg_events_per_incident = (
        round(total / unique_total, 1)
        if unique_total
        else 0
    )

    def format_counter(counter, preferred_order=None):
        """
        Converte um Counter em lista de dicionários com total e percentual.

        O formato em lista é mais simples de percorrer no template HTML e no PDF.
        """
        ordered_items = []

        if preferred_order:
            ordered_items.extend([
                (name, counter[name])
                for name in preferred_order
                if counter.get(name, 0)
            ])

        ordered_names = {
            name
            for name, _ in ordered_items
        }
        ordered_items.extend([
            (name, count)
            for name, count in counter.most_common()
            if name not in ordered_names
        ])

        return [
            {
                "name": name,
                "total": count,
                "percent": round((count / total) * 100, 1) if total else 0
            }
            for name, count in ordered_items
        ]

    return {
        "total": total,
        "event_total": total,
        "unique_total": unique_total,
        "unique_open": unique_open,
        "unique_resolved": unique_resolved,
        "repeated_events": repeated_events,
        "avg_events_per_incident": avg_events_per_incident,
        "unclassified": severity_counter.get("Não classificada", 0),
        "information": severity_counter.get("Informação", 0),
        "attention": severity_counter.get("Atenção", 0),
        "critical": severity_counter.get("Desastre", 0),
        "high": severity_counter.get("Alta", 0),
        "medium": severity_counter.get("Média", 0),
        "warning": severity_counter.get("Atenção", 0),
        "open": status_counter.get("Aberto", 0),
        "resolved": status_counter.get("Resolvido", 0),
        "status": format_counter(status_counter),
        "units": format_counter(unit_counter),
        "top_units": format_counter(unit_counter)[:12],
        "severity": format_counter(severity_counter),
        "equipment": format_counter(equipment_counter, equipment_order),
        "top_hosts": format_counter(host_counter)[:8],
    }


def build_summary_pdf_page(summary, generated, period_label, total_pages):
    """
    Monta a página executiva do PDF com indicadores agregados.

    Retorna bytes com comandos PDF. Essa página aparece antes do detalhamento
    para dar uma visão rápida da quantidade e distribuição dos incidentes.
    """

    commands = []
    white = (1, 1, 1)
    cyan = (0.03, 0.50, 0.55)
    text = (0.05, 0.14, 0.22)
    muted = (0.26, 0.34, 0.43)

    # Capa inspirada no HTML: fundo escuro, marca operacional e cards executivos.
    commands.append(b"0.04 0.20 0.25 rg 0 392 842 203 re f\n")
    commands.append(b"0.03 0.50 0.55 rg 0 588 842 7 re f\n")
    commands.append(b"0.05 0.33 0.38 rg 616 392 226 203 re f\n")
    commands.append(b"0.03 0.50 0.55 RG 34 402 774 174 re S\n")

    add_pdf_text(
        commands,
        36,
        552,
        "Relatório Executivo de Incidentes Zabbix",
        24,
        "F2",
        white,
    )
    add_pdf_text(
        commands,
        38,
        573,
        "MONITORAMENTO ZABBIX",
        8,
        "F2",
        (0.74, 0.92, 0.91),
    )

    compact_period = str(period_label).split(":")[0].split("|")[0].strip()
    hero_cards = [
        ("GERADO EM", generated),
        ("PERÍODO", compact_period),
        ("PRODUZIDO POR", "Network Operations Center"),
    ]
    hero_width = 238
    hero_y = 430

    for index, (label, value) in enumerate(hero_cards):
        x = 44 + (index * 254)
        commands.append(
            b"0.08 0.31 0.35 rg %.2f %.2f %.2f 56 re f\n" % (
                x,
                hero_y,
                hero_width,
            )
        )
        commands.append(
            b"0.15 0.66 0.70 RG %.2f %.2f %.2f 56 re S\n" % (
                x,
                hero_y,
                hero_width,
            )
        )
        add_pdf_text(commands, x + 12, hero_y + 35, label, 8, "F2", (0.66, 0.86, 0.87))
        add_pdf_text(commands, x + 12, hero_y + 14, value, 13, "F2", white)

    def draw_metric_group(title, items, x, y, width, accent):
        commands.append(
            b"%.2f %.2f %.2f rg %.2f %.2f %.2f 118 re f\n" % (
                0.97,
                0.99,
                0.99,
                x,
                y,
                width,
            )
        )
        commands.append(
            b"%.2f %.2f %.2f RG %.2f %.2f %.2f 118 re S\n" % (
                accent[0],
                accent[1],
                accent[2],
                x,
                y,
                width,
            )
        )
        add_pdf_text(commands, x + 12, y + 96, title, 10, "F2", text)

        card_width = (width - 36) / max(1, len(items))

        for index, (label, value) in enumerate(items):
            card_x = x + 12 + (index * (card_width + 6))
            commands.append(
                b"0.94 0.98 0.98 rg %.2f %.2f %.2f 58 re f\n" % (
                    card_x,
                    y + 22,
                    card_width,
                )
            )
            commands.append(
                b"%.2f %.2f %.2f RG %.2f %.2f %.2f 58 re S\n" % (
                    accent[0],
                    accent[1],
                    accent[2],
                    card_x,
                    y + 22,
                    card_width,
                )
            )
            add_pdf_text(commands, card_x + 8, y + 59, label, 7, "F2", muted)
            add_pdf_text(commands, card_x + 8, y + 35, value, 16, "F2", accent)

    age = summary["age"]
    draw_metric_group(
        "OPERAÇÃO",
        [("INCIDENTES ABERTOS", summary["unique_open"])],
        36,
        258,
        180,
        (0.79, 0.13, 0.18),
    )
    draw_metric_group(
        "TEMPO OFFLINE",
        [
            ("MAIS ANTIGO", age["oldest_label"]),
            ("MÉDIA DE IDADE", age["average_label"]),
            ("ACIMA DE 7 DIAS", age["over_7d"]),
        ],
        228,
        258,
        300,
        (0.92, 0.43, 0.00),
    )
    draw_metric_group(
        "SEVERIDADE",
        [
            ("ALTA", summary["high"]),
            ("MÉDIA", summary["medium"]),
            ("ATENÇÃO", summary["attention"]),
            ("INFORMAÇÃO", summary["information"]),
        ],
        540,
        258,
        266,
        cyan,
    )

    def draw_section(title, items, x, y, width=350, limit=7):
        commands.append(
            b"0.04 0.20 0.25 rg %.2f %.2f %.2f 24 re f\n" % (
                x,
                y,
                width,
            )
        )
        commands.append(
            b"0.03 0.50 0.55 rg %.2f %.2f %.2f 3 re f\n" % (
                x,
                y + 21,
                width,
            )
        )
        add_pdf_text(commands, x + 10, y + 8, title, 10, "F2", white)
        cursor = y - 17

        for item in items[:limit]:
            name = item["name"]
            value = f"{item['total']} ({item['percent']}%)"
            name_lines = wrap_text(name, 45 if width > 300 else 32)

            add_pdf_text(commands, x + 10, cursor, name_lines[0], 8, "F1", text)
            add_pdf_text(commands, x + width - 84, cursor, value, 8, "F2", text)
            commands.append(
                b"0.90 0.95 0.96 RG %.2f %.2f %.2f 0.5 re S\n" % (
                    x + 10,
                    cursor - 5,
                    width - 20,
                )
            )
            cursor -= 14

            for extra in name_lines[1:2]:
                add_pdf_text(commands, x + 10, cursor, extra, 7, "F1", muted)
                cursor -= 12

        return cursor

    draw_section(
        "Tipos de incidente",
        summary.get("top_incident_types", []),
        36,
        214,
        370,
        8,
    )
    draw_section(
        "Equipamentos mais afetados",
        summary.get("top_equipment", summary["equipment"]),
        436,
        214,
        370,
        8,
    )
    draw_section(
        "Unidades com mais incidentes",
        summary["top_units"],
        36,
        54,
        370,
        7,
    )
    priority_items = [
        {
            "name": f"{item['label']} · {item['host']}",
            "total": item["score"],
            "percent": item["score"],
        }
        for item in summary.get("priority", {}).get("top", [])[:6]
    ]
    recurrence_items = [
        {
            "name": f"{item['host']} · {item['incident_type']}",
            "total": item["total"],
            "percent": item["percent"],
        }
        for item in summary.get("recurrence", {}).get("top", [])[:6]
    ]
    draw_section(
        "Fila de prioridade",
        priority_items,
        436,
        54,
        180,
        6,
    )
    draw_section(
        "Reincidencia",
        recurrence_items,
        626,
        54,
        180,
        6,
    )

    add_pdf_text(
        commands,
        36,
        20,
        f"Página 1 de {total_pages}",
        8,
        "F1",
        muted,
    )

    return b"".join(commands)


def build_pdf_page(rows, page_number, total_pages, generated):
    """
    Monta uma página de detalhamento do PDF.

    rows contém os incidentes que cabem nesta página. A função desenha cabeçalho,
    colunas e linhas usando coordenadas fixas para produzir um PDF em paisagem.
    """

    commands = []
    dark = (1, 1, 1)
    text = (0.05, 0.14, 0.22)
    muted = (0.26, 0.34, 0.43)

    commands.append(b"0.04 0.20 0.25 rg 0 548 842 47 re f\n")
    add_pdf_text(
        commands,
        36,
        573,
        "Detalhamento de Incidentes Zabbix",
        15,
        "F2",
        dark,
    )
    add_pdf_text(
        commands,
        36,
        556,
        f"Gerado em {generated} | Pagina {page_number} de {total_pages}",
        8,
        "F1",
        dark,
    )

    headers = [
        "Data",
        "Unidade",
        "Host",
        "Equipamento",
        "Tipo de incidente",
        "Sev.",
        "Tempo",
        "Evento"
    ]

    # Cada coluna define: posição X, largura visual e limite aproximado de
    # caracteres por linha. O limite alimenta wrap_text().
    columns = [
        (36, 70, 13),
        (106, 160, 28),
        (266, 146, 24),
        (412, 92, 14),
        (504, 142, 24),
        (646, 52, 8),
        (698, 58, 9),
        (756, 54, 12),
    ]

    y = 520

    # Faixa de fundo do cabeçalho da tabela.
    commands.append(b"0.07 0.29 0.34 rg 34 508 776 24 re f\n")
    commands.append(b"0.04 0.20 0.25 RG 34 508 776 24 re S\n")

    # Escreve os nomes das colunas.
    for index, header in enumerate(headers):
        x, _, _ = columns[index]
        add_pdf_text(commands, x, y, header, 8, "F2", dark)

    y = 490

    for row_index, row in enumerate(rows):
        # Cada célula é quebrada em linhas para impedir sobreposição entre
        # colunas quando houver nomes ou incidentes longos.
        row_lines = [
            wrap_text(row.get("date", ""), columns[0][2]),
            wrap_text(row.get("unit", ""), columns[1][2]),
            wrap_text(row.get("host", ""), columns[2][2]),
            wrap_text(row.get("equipment", ""), columns[3][2]),
            wrap_text(
                row.get("incident_type") or row.get("incident", ""),
                columns[4][2],
            ),
            wrap_text(row.get("severity", ""), columns[5][2]),
            wrap_text(row.get("age_label", ""), columns[6][2]),
            wrap_text(row.get("eventid", ""), columns[7][2]),
        ]

        # A altura da linha cresce conforme a célula com mais linhas.
        line_count = min(3, max(len(lines) for lines in row_lines))
        row_height = max(24, line_count * 10 + 10)

        if row_index % 2 == 0:
            commands.append(
                b"0.98 0.99 1.00 rg 34 %.2f 776 %.2f re f\n" % (
                    y - row_height + 10,
                    row_height,
                )
            )

        # Desenha a borda da linha antes de escrever os textos.
        commands.append(
            b"0.84 0.88 0.92 RG 34 %.2f 776 %.2f re S\n" % (
                y - row_height + 10,
                row_height
            )
        )

        for column_index, lines in enumerate(row_lines):
            x, _, _ = columns[column_index]

            # Escreve cada linha de texto dentro da coluna atual.
            for line_index, line in enumerate(lines[:3]):
                color = muted if line_index else text
                add_pdf_text(
                    commands,
                    x,
                    y - (line_index * 10),
                    line,
                    7,
                    "F1",
                    color,
                )

        y -= row_height

    return b"".join(commands)


def write_pdf_report(filename, incidents, generated, summary, period_label):
    """
    Escreve o arquivo PDF completo no disco.

    A função cria manualmente a estrutura mínima de um PDF: catálogo, páginas,
    fontes, streams de conteúdo, tabela de referências cruzadas e trailer. Isso
    evita depender de uma biblioteca externa específica para PDF.
    """

    # Divide os incidentes em páginas de detalhamento. A página executiva é
    # criada separadamente e sempre aparece primeiro.
    rows_per_page = 14
    pages = [
        incidents[index:index + rows_per_page]
        for index in range(0, len(incidents), rows_per_page)
    ] or [[]]

    total_pages = len(pages) + 1

    # Primeiro stream: resumo executivo. Depois: páginas com as linhas.
    page_streams = [
        build_summary_pdf_page(
            summary,
            generated,
            period_label,
            total_pages
        )
    ]
    page_streams.extend([
        build_pdf_page(rows, index + 2, total_pages, generated)
        for index, rows in enumerate(pages)
    ])

    # Objetos fixos do PDF: catálogo e fontes Helvetica normal/negrito.
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    }

    page_ids = []

    for index, stream in enumerate(page_streams):
        # Para cada página, criamos dois objetos: a página e o seu conteúdo.
        page_id = 5 + (index * 2)
        content_id = page_id + 1

        page_ids.append(page_id)

        # MediaBox [0 0 842 595] define página A4 em paisagem.
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 842 595] "
            b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            b"/Contents %d 0 R >>" % content_id
        )
        # O stream guarda os comandos de desenho/texto daquela página.
        objects[content_id] = (
            b"<< /Length %d >>\nstream\n%bendstream" % (
                len(stream),
                stream
            )
        )

    # O objeto /Pages precisa listar todas as páginas filhas do documento.
    kids = b" ".join(
        b"%d 0 R" % page_id
        for page_id in page_ids
    )
    objects[2] = (
        b"<< /Type /Pages /Kids [%b] /Count %d >>" % (
            kids,
            len(page_ids)
        )
    )

    # ordered_ids garante que os objetos sejam escritos em ordem previsível.
    ordered_ids = sorted(objects)
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = {}

    for object_id in ordered_ids:
        # offsets registra onde cada objeto começa; a tabela xref usa esses
        # números para que leitores de PDF encontrem os objetos.
        offsets[object_id] = len(pdf)
        pdf.extend(b"%d 0 obj\n%b\nendobj\n" % (
            object_id,
            objects[object_id]
        ))

    # A tabela xref é obrigatória em PDFs clássicos e aponta para cada objeto.
    xref_offset = len(pdf)
    pdf.extend(b"xref\n0 %d\n" % (max(ordered_ids) + 1))
    pdf.extend(b"0000000000 65535 f \n")

    for object_id in range(1, max(ordered_ids) + 1):
        pdf.extend(b"%010d 00000 n \n" % offsets[object_id])

    # Trailer encerra o arquivo informando o objeto raiz e onde começa a xref.
    pdf.extend(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            max(ordered_ids) + 1,
            xref_offset
        )
    )

    # O PDF é binário, por isso precisa ser escrito com modo "wb".
    with open(filename, "wb") as f:
        f.write(pdf)
