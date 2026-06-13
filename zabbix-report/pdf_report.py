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


def add_pdf_text(commands, x, y, text, size=8, font="F1"):
    """
    Adiciona um comando de texto ao conteúdo de uma página PDF.

    commands é uma lista de bytes que representa o stream da página. A função
    centraliza a sintaxe PDF para que as páginas possam chamar apenas com
    coordenadas, texto, tamanho e fonte.
    """

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

    # Cada item de commands é uma instrução PDF. No final elas são unidas em um
    # único stream de conteúdo.
    commands = []

    # Cabeçalho da página: título, período analisado, data de geração e paginação.
    add_pdf_text(
        commands,
        36,
        558,
        "Relatorio Executivo de Incidentes Zabbix",
        17,
        "F2"
    )
    add_pdf_text(
        commands,
        36,
        538,
        f"Periodo: {period_label} | Gerado em {generated} | Pagina 1 de {total_pages}",
        9
    )

    # Cards de indicadores principais. Cada tupla contém rótulo e valor.
    cards = [
        ("Eventos", summary["event_total"]),
        ("Inc. unicos", summary["unique_total"]),
        ("Unicos abertos", summary["unique_open"]),
        ("Unicos resolv.", summary["unique_resolved"]),
        ("Eventos repet.", summary["repeated_events"]),
        ("Media ev/inc", summary["avg_events_per_incident"]),
    ]

    x = 36
    y = 470

    for index, (label, value) in enumerate(cards):
        # Depois de três cards, inicia a segunda linha para manter o layout em
        # duas fileiras.
        if index == 3:
            x = 36
            y = 402

        # Desenha fundo e borda do card diretamente com comandos PDF.
        commands.append(
            b"0.93 0.95 0.97 rg %.2f %.2f 178 48 re f\n" % (x, y)
        )
        commands.append(
            b"0.75 0.80 0.86 RG %.2f %.2f 178 48 re S\n" % (x, y)
        )
        add_pdf_text(commands, x + 12, y + 30, label, 9, "F2")
        add_pdf_text(commands, x + 12, y + 10, value, 18, "F2")
        x += 192

    add_pdf_text(commands, 36, 346, "Distribuicao por severidade", 12, "F2")
    y = 322

    # Lista até seis severidades para manter a página executiva compacta.
    for item in summary["severity"][:6]:
        add_pdf_text(
            commands,
            48,
            y,
            f"{item['name']}: {item['total']} ({item['percent']}%)",
            9
        )
        y -= 18

    add_pdf_text(commands, 330, 346, "Equipamentos mais afetados", 12, "F2")
    y = 322

    # Mostra as categorias de equipamento com maior quantidade de incidentes.
    for item in summary["equipment"][:8]:
        add_pdf_text(
            commands,
            342,
            y,
            f"{item['name']}: {item['total']} ({item['percent']}%)",
            9
        )
        y -= 18

    add_pdf_text(commands, 330, 210, "Unidades com mais incidentes", 12, "F2")
    y = 186

    # Lista as unidades escolares mais afetadas para facilitar triagem por local.
    for item in summary["top_units"][:6]:
        add_pdf_text(
            commands,
            342,
            y,
            f"{item['name']}: {item['total']} ({item['percent']}%)",
            8
        )
        y -= 16

    add_pdf_text(commands, 36, 210, "Situacao dos incidentes", 12, "F2")
    y = 186

    # Separa incidentes ainda ativos dos que ja foram resolvidos no Zabbix.
    for item in summary["status"]:
        add_pdf_text(
            commands,
            48,
            y,
            f"{item['name']}: {item['total']} ({item['percent']}%)",
            9
        )
        y -= 18

    add_pdf_text(commands, 36, 110, "Hosts com mais incidentes", 12, "F2")
    y = 86

    # Mostra os hosts mais recorrentes para orientar investigação operacional.
    for item in summary["top_hosts"]:
        add_pdf_text(
            commands,
            48,
            y,
            f"{item['name']}: {item['total']} ({item['percent']}%)",
            8
        )
        y -= 16

    return b"".join(commands)


def build_pdf_page(rows, page_number, total_pages, generated):
    """
    Monta uma página de detalhamento do PDF.

    rows contém os incidentes que cabem nesta página. A função desenha cabeçalho,
    colunas e linhas usando coordenadas fixas para produzir um PDF em paisagem.
    """

    commands = []

    # Cabeçalho do detalhamento com data de geração e número da página.
    add_pdf_text(
        commands,
        36,
        558,
        "Detalhamento de Incidentes Zabbix",
        16,
        "F2"
    )
    add_pdf_text(
        commands,
        36,
        540,
        f"Gerado em {generated} | Pagina {page_number} de {total_pages}",
        9
    )

    headers = [
        "Data",
        "Unidade",
        "Resolvido",
        "Status",
        "Equipamento",
        "Incidente",
        "Sev.",
        "Evento"
    ]

    # Cada coluna define: posição X, largura visual e limite aproximado de
    # caracteres por linha. O limite alimenta wrap_text().
    columns = [
        (36, 76, 14),
        (112, 120, 20),
        (232, 76, 14),
        (308, 62, 10),
        (370, 94, 15),
        (464, 190, 32),
        (654, 54, 9),
        (708, 76, 12),
    ]

    y = 512

    # Faixa de fundo do cabeçalho da tabela.
    commands.append(b"0.93 0.95 0.97 rg 34 500 774 22 re f\n")
    commands.append(b"0.75 0.80 0.86 RG 34 500 774 22 re S\n")

    # Escreve os nomes das colunas.
    for index, header in enumerate(headers):
        x, _, _ = columns[index]
        add_pdf_text(commands, x, y + 2, header, 8, "F2")

    y = 482

    for row in rows:
        # Cada célula é quebrada em linhas para impedir sobreposição entre
        # colunas quando houver nomes ou incidentes longos.
        row_lines = [
            wrap_text(row["date"], columns[0][2]),
            wrap_text(row["unit"], columns[1][2]),
            wrap_text(row["resolved_at"], columns[2][2]),
            wrap_text(row["status"], columns[3][2]),
            wrap_text(row["equipment"], columns[4][2]),
            wrap_text(row["incident"], columns[5][2]),
            wrap_text(row["severity"], columns[6][2]),
            wrap_text(row["eventid"], columns[7][2]),
        ]

        # A altura da linha cresce conforme a célula com mais linhas.
        line_count = max(len(lines) for lines in row_lines)
        row_height = max(20, line_count * 10 + 8)

        # Desenha a borda da linha antes de escrever os textos.
        commands.append(
            b"0.86 0.89 0.93 RG 34 %.2f 774 %.2f re S\n" % (
                y - row_height + 10,
                row_height
            )
        )

        for column_index, lines in enumerate(row_lines):
            x, _, _ = columns[column_index]

            # Escreve cada linha de texto dentro da coluna atual.
            for line_index, line in enumerate(lines):
                add_pdf_text(
                    commands,
                    x,
                    y - (line_index * 10),
                    line,
                    7
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
    rows_per_page = 18
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
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
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
