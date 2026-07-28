"""
Geração dos PDFs executivo e técnico do relatório Zabbix.

O módulo escreve PDF 1.4 diretamente para manter a exportação portátil no
Windows/WSL e sem serviços externos. Todos os indicadores chegam prontos de
``summary.py``; aqui existem apenas composição, limites e hierarquia visual.
"""

import re
from pathlib import Path

PAGE_WIDTH = 842
PAGE_HEIGHT = 595
EXECUTIVE_RANKING_LIMIT = 6
TECHNICAL_ROWS_PER_PAGE = 14

COLORS = {
    "navy": (0.04, 0.20, 0.25),
    "navy_light": (0.05, 0.33, 0.38),
    "teal": (0.03, 0.50, 0.55),
    "cyan": (0.15, 0.66, 0.70),
    "text": (0.05, 0.14, 0.22),
    "muted": (0.30, 0.38, 0.45),
    "line": (0.86, 0.91, 0.92),
    "surface": (0.96, 0.98, 0.98),
    "white": (1, 1, 1),
    "red": (0.76, 0.14, 0.18),
    "orange": (0.90, 0.42, 0.04),
    "green": (0.10, 0.52, 0.38),
}

SENSITIVE_PATTERNS = (
    (re.compile(r"https?://\S+", re.IGNORECASE), "[URL omitida]"),
    (
        re.compile(
            r"\b(token|password|senha|secret|authorization|api[_-]?key)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
        r"\1=[omitido]",
    ),
)


def sanitize_pdf_text(value):
    """Remove URLs e valores com aparência de credencial antes da escrita."""

    text = str(value or "").replace("\r", " ").replace("\n", " ")
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return " ".join(text.split())


def pdf_escape(value):
    """Escapa uma string para uso seguro em um stream PDF WinAnsi."""

    data = sanitize_pdf_text(value).encode("cp1252", errors="replace")
    return data.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def wrap_text(value, max_chars, max_lines=None):
    """Quebra texto por palavras e limita linhas para evitar sobreposições."""

    words = sanitize_pdf_text(value).split()
    lines = []
    current = ""

    for word in words:
        while len(word) > max_chars:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:max_chars])
            word = word[max_chars:]

        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)
    if not lines:
        lines = [""]

    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = f"{lines[-1][: max(1, max_chars - 1)].rstrip()}…"
    return lines


def _color_command(color, stroke=False):
    operator = b"RG" if stroke else b"rg"
    return b"%.3f %.3f %.3f %b\n" % (*color, operator)


def add_pdf_text(commands, x, y, text, size=9, font="F1", color=None):
    """Adiciona uma linha de texto ao stream corrente."""

    color = color or COLORS["text"]
    commands.append(_color_command(color))
    commands.append(
        b"BT /%b %.1f Tf %.2f %.2f Td (%b) Tj ET\n"
        % (font.encode("ascii"), size, x, y, pdf_escape(text))
    )


def add_rect(commands, x, y, width, height, fill=None, stroke=None, line_width=1):
    if fill:
        commands.append(_color_command(fill))
        commands.append(b"%.2f %.2f %.2f %.2f re f\n" % (x, y, width, height))
    if stroke:
        commands.append(_color_command(stroke, stroke=True))
        commands.append(b"%.2f w %.2f %.2f %.2f %.2f re S\n" % (line_width, x, y, width, height))


def add_line(commands, x1, y1, x2, y2, color=None, width=1):
    commands.append(_color_command(color or COLORS["line"], stroke=True))
    commands.append(b"%.2f w %.2f %.2f m %.2f %.2f l S\n" % (width, x1, y1, x2, y2))


def add_wrapped_text(
    commands,
    x,
    y,
    text,
    max_chars,
    size=9,
    line_height=12,
    font="F1",
    color=None,
    max_lines=None,
):
    lines = wrap_text(text, max_chars, max_lines=max_lines)
    for index, line in enumerate(lines):
        add_pdf_text(commands, x, y - (index * line_height), line, size, font, color)
    return y - (len(lines) * line_height)


def _page_header(commands, eyebrow, title, subtitle=None):
    add_rect(commands, 0, PAGE_HEIGHT - 8, PAGE_WIDTH, 8, fill=COLORS["teal"])
    add_pdf_text(commands, 36, 554, eyebrow.upper(), 8, "F2", COLORS["teal"])
    add_pdf_text(commands, 36, 524, title, 22, "F2", COLORS["navy"])
    if subtitle:
        add_pdf_text(commands, 36, 502, subtitle, 9, "F1", COLORS["muted"])
    add_line(commands, 36, 486, 806, 486)


def _page_footer(commands, page_number, total_pages, generated, document_label="PDF executivo"):
    add_line(commands, 36, 32, 806, 32)
    add_pdf_text(commands, 36, 17, f"{document_label} · {generated}", 7, "F1", COLORS["muted"])
    add_pdf_text(
        commands,
        742,
        17,
        f"{page_number:02d} / {total_pages:02d}",
        8,
        "F2",
        COLORS["navy"],
    )


def _metric(commands, x, y, width, label, value, accent="teal"):
    add_rect(commands, x, y, width, 72, fill=COLORS["surface"])
    add_rect(commands, x, y, 4, 72, fill=COLORS[accent])
    add_pdf_text(commands, x + 14, y + 49, label.upper(), 7, "F2", COLORS["muted"])
    add_pdf_text(commands, x + 14, y + 19, value, 19, "F2", COLORS["navy"])


def _section_title(commands, x, y, title, note=None):
    add_pdf_text(commands, x, y, title, 11, "F2", COLORS["navy"])
    if note:
        add_pdf_text(commands, x, y - 15, note, 7, "F1", COLORS["muted"])
    return y - (28 if note else 18)


def _ranking(
    commands, x, y, width, title, items, value_label="eventos", limit=EXECUTIVE_RANKING_LIMIT
):
    """Desenha ranking compacto e retorna a ordenada final."""

    y = _section_title(commands, x, y, title)
    visible = list(items or [])[:limit]
    if not visible:
        add_pdf_text(
            commands, x, y - 8, "Sem dados relevantes no período.", 8, "F1", COLORS["muted"]
        )
        return y - 28

    maximum = max((float(item.get("total", 0) or 0) for item in visible), default=0)
    for index, item in enumerate(visible, start=1):
        row_y = y - 5
        name = wrap_text(item.get("name", "N/A"), 36 if width < 350 else 44, max_lines=1)[0]
        value = item.get("total", 0)
        ratio = (float(value) / maximum) if maximum else 0
        add_pdf_text(commands, x, row_y, f"{index:02d}", 8, "F2", COLORS["teal"])
        add_pdf_text(commands, x + 25, row_y, name, 8, "F1", COLORS["text"])
        add_pdf_text(
            commands, x + width - 76, row_y, f"{value} {value_label}", 7, "F2", COLORS["muted"]
        )
        add_rect(commands, x + 25, row_y - 9, width - 34, 3, fill=COLORS["line"])
        add_rect(commands, x + 25, row_y - 9, (width - 34) * ratio, 3, fill=COLORS["teal"])
        y -= 30
    return y


def _integrity_label(integrity):
    integrity = integrity or {}
    return integrity.get("label") or (
        "Dados validados" if not integrity.get("warning_count") else "Dados com avisos"
    )


def build_cover_page(
    summary,
    generated,
    period_label,
    integrity,
    total_pages,
    special_summaries=None,
):
    commands = []
    add_rect(commands, 0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=COLORS["navy"])
    add_rect(commands, 0, 0, 13, PAGE_HEIGHT, fill=COLORS["teal"])
    add_rect(commands, 586, 0, 256, PAGE_HEIGHT, fill=COLORS["navy_light"])
    add_rect(commands, 586, 0, 6, PAGE_HEIGHT, fill=COLORS["cyan"])

    add_pdf_text(commands, 48, 535, "NETWORK OPERATIONS CENTER", 9, "F2", (0.68, 0.88, 0.88))
    add_wrapped_text(
        commands,
        48,
        478,
        "Relatório Executivo de Incidentes Zabbix",
        31,
        28,
        34,
        "F2",
        COLORS["white"],
        3,
    )
    add_pdf_text(
        commands,
        48,
        363,
        "Visão gerencial do passivo, impacto e prioridades operacionais",
        10,
        "F1",
        (0.76, 0.87, 0.87),
    )

    compact_period = str(period_label).split("|")[0].strip()
    add_pdf_text(commands, 48, 260, "PERÍODO ANALISADO", 7, "F2", (0.62, 0.82, 0.82))
    add_wrapped_text(commands, 48, 240, compact_period, 62, 11, 15, "F2", COLORS["white"], 2)
    add_pdf_text(commands, 48, 187, "GERAÇÃO", 7, "F2", (0.62, 0.82, 0.82))
    add_pdf_text(commands, 48, 166, generated, 11, "F2", COLORS["white"])
    add_pdf_text(commands, 48, 113, "ESCOPO", 7, "F2", (0.62, 0.82, 0.82))
    add_pdf_text(
        commands,
        48,
        92,
        "Unidades escolares · Servidor Zabbix e CONFEA tratados separadamente",
        9,
        "F1",
        COLORS["white"],
    )
    special_labels = [
        f"{label}: {item.get('event_total', 0)} eventos"
        for label, item in (special_summaries or {}).items()
        if item and item.get("event_total", 0)
    ]
    if special_labels:
        add_pdf_text(
            commands,
            48,
            66,
            " · ".join(special_labels),
            8,
            "F2",
            (0.68, 0.88, 0.88),
        )

    add_pdf_text(commands, 620, 510, "LEITURA RÁPIDA", 8, "F2", (0.68, 0.88, 0.88))
    cover_metrics = [
        ("Incidentes abertos", summary.get("unique_open", 0)),
        ("Eventos no período", summary.get("event_total", 0)),
        ("Unidades afetadas", summary.get("unit_criticality", {}).get("total_units", 0)),
        ("Prioridade crítica", summary.get("priority", {}).get("critical", 0)),
    ]
    y = 454
    for label, value in cover_metrics:
        add_pdf_text(commands, 620, y, label.upper(), 7, "F2", (0.62, 0.82, 0.82))
        add_pdf_text(commands, 620, y - 29, str(value), 23, "F2", COLORS["white"])
        add_line(commands, 620, y - 43, 800, y - 43, (0.19, 0.47, 0.50))
        y -= 92

    add_pdf_text(commands, 620, 76, "INTEGRIDADE", 7, "F2", (0.62, 0.82, 0.82))
    add_wrapped_text(
        commands,
        620,
        57,
        _integrity_label(integrity),
        27,
        9,
        12,
        "F2",
        COLORS["white"],
        2,
    )
    add_pdf_text(
        commands,
        48,
        27,
        f"Documento executivo · {total_pages} páginas",
        7,
        "F1",
        (0.62, 0.82, 0.82),
    )
    return b"".join(commands)


def build_overview_page(
    summary,
    generated,
    period_label,
    integrity,
    page_number,
    total_pages,
):
    commands = []
    _page_header(commands, "Visão executiva", "Indicadores principais", period_label)

    metrics = [
        ("Incidentes únicos", summary.get("unique_total", 0), "teal"),
        ("Passivo aberto", summary.get("unique_open", 0), "red"),
        ("Resolvidos", summary.get("unique_resolved", 0), "green"),
        ("Eventos repetidos", summary.get("repeated_events", 0), "orange"),
    ]
    for index, (label, value, accent) in enumerate(metrics):
        _metric(commands, 36 + (index * 194), 390, 178, label, str(value), accent)

    age = summary.get("age", {})
    y = _section_title(
        commands,
        36,
        350,
        "Idade do passivo aberto",
        "Somente incidentes que permanecem abertos.",
    )
    age_metrics = [
        ("Mais antigo aberto", age.get("oldest_label", "-")),
        ("Média de idade", age.get("average_label", "-")),
        ("Acima de 7 dias", age.get("over_7d", 0)),
    ]
    for index, (label, value) in enumerate(age_metrics):
        _metric(commands, 36 + (index * 194), y - 70, 178, label, str(value), "orange")

    severity = summary.get("severity", [])
    status = summary.get("status", [])
    _ranking(commands, 36, 185, 360, "Severidades", severity, "eventos", 6)
    _ranking(commands, 436, 185, 370, "Situação dos eventos", status, "eventos", 3)

    resolved = summary.get("resolved_duration", {})
    if resolved.get("total"):
        add_pdf_text(commands, 436, 80, "HISTÓRICO ENCERRADO", 7, "F2", COLORS["green"])
        add_pdf_text(
            commands,
            436,
            60,
            f"{resolved['total']} encerrados · média {resolved['average_label']} · "
            f"mediana {resolved['median_label']} · maior {resolved['maximum_label']}",
            8,
            "F1",
            COLORS["muted"],
        )

    _page_footer(commands, page_number, total_pages, generated)
    return b"".join(commands)


def build_impact_page(summary, generated, page_number, total_pages):
    commands = []
    _page_header(
        commands,
        "Concentração operacional",
        "Equipamentos e unidades mais afetados",
        f"Rankings limitados aos {EXECUTIVE_RANKING_LIMIT} itens de maior relevância.",
    )
    _ranking(
        commands,
        36,
        454,
        360,
        "Equipamentos",
        summary.get("top_equipment", []),
        "eventos",
    )
    _ranking(
        commands,
        436,
        454,
        370,
        "Unidades",
        summary.get("top_units", []),
        "eventos",
    )
    _ranking(
        commands,
        36,
        224,
        360,
        "Tipos de incidente",
        summary.get("top_incident_types", []),
        "eventos",
    )
    _ranking(
        commands,
        436,
        224,
        370,
        "Hosts mais afetados",
        summary.get("top_hosts", []),
        "eventos",
    )
    _page_footer(commands, page_number, total_pages, generated)
    return b"".join(commands)


def _priority_rows(commands, items, x, y, width, limit=6):
    visible = list(items or [])[:limit]
    for item in visible:
        add_rect(commands, x, y - 42, width, 48, fill=COLORS["surface"])
        add_rect(
            commands,
            x,
            y - 42,
            4,
            48,
            fill=COLORS["red"] if item.get("label") == "Crítica" else COLORS["orange"],
        )
        add_pdf_text(
            commands,
            x + 14,
            y - 9,
            f"{item.get('score', 0):02d} · {item.get('label', 'Normal')}",
            8,
            "F2",
            COLORS["navy"],
        )
        add_pdf_text(
            commands,
            x + 14,
            y - 26,
            wrap_text(f"{item.get('unit', 'N/A')} · {item.get('equipment', 'N/A')}", 45, 1)[0],
            7,
            "F1",
            COLORS["muted"],
        )
        add_pdf_text(
            commands,
            x + width - 92,
            y - 9,
            item.get("open_age_label", item.get("age_label", "-")),
            8,
            "F2",
            COLORS["orange"],
        )
        y -= 57
    return y


def _recurrence_rows(commands, items, x, y, width, limit=6):
    visible = list(items or [])[:limit]
    for item in visible:
        add_pdf_text(
            commands,
            x,
            y,
            wrap_text(item.get("host", "N/A"), 36, 1)[0],
            8,
            "F2",
            COLORS["navy"],
        )
        add_pdf_text(
            commands,
            x + width - 72,
            y,
            f"{item.get('total', 0)} eventos",
            8,
            "F2",
            COLORS["teal"],
        )
        add_pdf_text(
            commands,
            x,
            y - 16,
            wrap_text(item.get("incident_type", "N/A"), 46, 1)[0],
            7,
            "F1",
            COLORS["muted"],
        )
        add_line(commands, x, y - 25, x + width, y - 25)
        y -= 45
    return y


def build_attention_page(summary, generated, page_number, total_pages):
    commands = []
    _page_header(
        commands,
        "Direcionamento",
        "Prioridades e recorrências relevantes",
        "Fila orientada por severidade, idade do passivo e repetição da condição.",
    )
    add_pdf_text(commands, 36, 456, "PRIORIDADES OPERACIONAIS", 10, "F2", COLORS["navy"])
    add_pdf_text(commands, 436, 456, "RECORRÊNCIAS", 10, "F2", COLORS["navy"])

    priority = summary.get("priority", {})
    recurrence = summary.get("recurrence", {})
    if priority.get("top"):
        _priority_rows(commands, priority["top"], 36, 426, 360)
    else:
        add_pdf_text(
            commands, 36, 420, "Nenhum incidente aberto priorizável.", 8, "F1", COLORS["muted"]
        )
    if recurrence.get("top"):
        _recurrence_rows(commands, recurrence["top"], 436, 426, 370)
    else:
        add_pdf_text(
            commands,
            436,
            420,
            "Nenhuma recorrência relevante no período.",
            8,
            "F1",
            COLORS["muted"],
        )

    add_rect(commands, 436, 92, 370, 64, fill=COLORS["surface"])
    add_pdf_text(commands, 452, 131, "HOSTS REINCIDENTES", 7, "F2", COLORS["muted"])
    add_pdf_text(
        commands, 452, 104, str(recurrence.get("affected_hosts", 0)), 18, "F2", COLORS["navy"]
    )
    add_pdf_text(
        commands,
        530,
        106,
        f"{recurrence.get('total_recurrent_events', 0)} eventos além da primeira ocorrência",
        8,
        "F1",
        COLORS["muted"],
    )
    _page_footer(commands, page_number, total_pages, generated)
    return b"".join(commands)


def build_criticality_page(summary, generated, page_number, total_pages):
    commands = []
    criticality = summary.get("unit_criticality", {})
    _page_header(
        commands,
        "Impacto por localidade",
        "Criticidade por unidade",
        "Score canônico combinando volume, severidade, idade, recorrência e equipamento.",
    )
    # Sete linhas preservam a área de síntese e o rodapé sem reduzir fonte.
    items = list(criticality.get("top", []))[:7]
    y = 452
    if not items:
        add_pdf_text(
            commands,
            36,
            y,
            "Nenhuma unidade com passivo aberto no período.",
            9,
            "F1",
            COLORS["muted"],
        )
    else:
        for index, item in enumerate(items, start=1):
            add_rect(commands, 36, y - 38, 770, 46, fill=COLORS["surface"])
            accent = (
                "red"
                if item.get("class") == "critical"
                else "orange" if item.get("class") == "high" else "teal"
            )
            add_rect(commands, 36, y - 38, 5, 46, fill=COLORS[accent])
            add_pdf_text(commands, 52, y - 10, f"{index:02d}", 8, "F2", COLORS["teal"])
            add_pdf_text(
                commands,
                82,
                y - 10,
                wrap_text(item.get("name", "N/A"), 54, 1)[0],
                8,
                "F2",
                COLORS["navy"],
            )
            add_pdf_text(
                commands,
                82,
                y - 27,
                f"{item.get('total', 0)} incidentes · {item.get('top_equipment', '-')} · "
                f"mais antigo {item.get('oldest_label', '-')}",
                7,
                "F1",
                COLORS["muted"],
            )
            add_pdf_text(commands, 604, y - 10, item.get("level", "-"), 7, "F2", COLORS[accent])
            add_pdf_text(commands, 748, y - 17, str(item.get("score", 0)), 17, "F2", COLORS["navy"])
            y -= 54

    add_pdf_text(
        commands,
        36,
        48,
        f"{criticality.get('total_units', 0)} unidades avaliadas · "
        f"{criticality.get('critical', 0)} em intervenção imediata · "
        f"{criticality.get('high', 0)} em prioridade alta.",
        8,
        "F1",
        COLORS["muted"],
    )
    _page_footer(commands, page_number, total_pages, generated)
    return b"".join(commands)


def _build_attention_points(summary, integrity):
    """Cria textos executivos somente a partir dos campos canônicos."""

    points = []
    if summary.get("unique_open", 0):
        age = summary.get("age", {})
        points.append(
            f"O passivo atual reúne {summary['unique_open']} incidentes únicos abertos; "
            f"o mais antigo está aberto há {age.get('oldest_label', '-')}."
        )
    else:
        points.append("Não há incidentes únicos abertos no escopo analisado.")

    priority = summary.get("priority", {})
    if priority.get("critical", 0) or priority.get("high", 0):
        points.append(
            f"A fila operacional contém {priority.get('critical', 0)} prioridades críticas "
            f"e {priority.get('high', 0)} prioridades altas."
        )

    recurrence = summary.get("recurrence", {})
    if recurrence.get("affected_hosts", 0):
        points.append(
            f"{recurrence['affected_hosts']} hosts apresentam recorrência, totalizando "
            f"{recurrence.get('total_recurrent_events', 0)} repetições além da ocorrência inicial."
        )

    criticality = summary.get("unit_criticality", {})
    if criticality.get("critical", 0):
        points.append(
            f"{criticality['critical']} unidades estão classificadas para intervenção imediata."
        )

    if (integrity or {}).get("warning_count", 0):
        points.append(
            f"A leitura considera {(integrity or {}).get('processed', 0)} registros processados "
            f"com {(integrity or {}).get('warning_count', 0)} avisos de integridade."
        )
    return points[:4]


def build_conclusion_page(summary, generated, period_label, integrity, page_number, total_pages):
    commands = []
    _page_header(
        commands,
        "Síntese",
        "Conclusão executiva",
        "Pontos objetivos para acompanhamento e tomada de decisão.",
    )
    points = _build_attention_points(summary, integrity)
    y = 442
    for index, point in enumerate(points, start=1):
        add_rect(commands, 36, y - 62, 770, 72, fill=COLORS["surface"])
        add_pdf_text(commands, 52, y - 20, f"{index:02d}", 10, "F2", COLORS["teal"])
        add_wrapped_text(commands, 88, y - 13, point, 90, 10, 14, "F1", COLORS["text"], 3)
        y -= 86

    integrity = integrity or {}
    add_rect(commands, 36, 68, 770, 60, fill=COLORS["navy"])
    add_pdf_text(commands, 52, 105, "INTEGRIDADE DOS DADOS", 7, "F2", (0.66, 0.86, 0.87))
    add_pdf_text(commands, 52, 82, _integrity_label(integrity), 11, "F2", COLORS["white"])
    add_pdf_text(
        commands,
        358,
        84,
        f"{integrity.get('processed', summary.get('event_total', 0))} processados · "
        f"{integrity.get('adjusted', 0)} ajustados · {integrity.get('discarded', 0)} descartados",
        8,
        "F1",
        (0.76, 0.87, 0.87),
    )
    add_pdf_text(
        commands,
        36,
        48,
        "Este documento resume a visão executiva. Consulte o HTML e o Excel para análise operacional completa.",
        7,
        "F1",
        COLORS["muted"],
    )
    _page_footer(commands, page_number, total_pages, generated)
    return b"".join(commands)


def build_technical_page(rows, page_number, total_pages, generated):
    """Monta uma página tabular do anexo técnico."""

    commands = []
    _page_header(
        commands,
        "Anexo técnico",
        "Detalhamento completo dos eventos",
        "Documento operacional separado do relatório executivo.",
    )
    headers = ["Abertura", "Unidade", "Equipamento", "Incidente", "Severidade", "Status", "Duração"]
    widths = [92, 132, 102, 190, 76, 72, 78]
    x_positions = [36]
    for width in widths[:-1]:
        x_positions.append(x_positions[-1] + width)

    add_rect(commands, 36, 444, sum(widths), 26, fill=COLORS["navy"])
    for x, header in zip(x_positions, headers, strict=True):
        add_pdf_text(commands, x + 5, 453, header, 7, "F2", COLORS["white"])

    y = 426
    for row_index, row in enumerate(rows):
        if row_index % 2 == 0:
            add_rect(commands, 36, y - 18, sum(widths), 28, fill=COLORS["surface"])
        values = [
            row.get("date", "-"),
            row.get("unit", "N/A"),
            row.get("equipment", "N/A"),
            row.get("incident_type") or row.get("incident", "N/A"),
            row.get("severity", "N/A"),
            row.get("status", "N/A"),
            row.get("duration_label", "-"),
        ]
        char_limits = [17, 22, 17, 31, 12, 11, 12]
        for x, value, limit in zip(x_positions, values, char_limits, strict=True):
            add_pdf_text(commands, x + 5, y, wrap_text(value, limit, 1)[0], 7, "F1", COLORS["text"])
        add_line(commands, 36, y - 18, 806, y - 18)
        y -= 28

    _page_footer(commands, page_number, total_pages, generated, "Anexo técnico")
    return b"".join(commands)


def _write_pdf(filename, page_streams):
    """Serializa streams de página em um PDF 1.4 determinístico."""

    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    }
    page_ids = []
    for index, stream in enumerate(page_streams):
        page_id = 5 + (index * 2)
        content_id = page_id + 1
        page_ids.append(page_id)
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 842 595] "
            b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            b"/Contents %d 0 R >>" % content_id
        )
        objects[content_id] = b"<< /Length %d >>\nstream\n%bendstream" % (len(stream), stream)

    kids = b" ".join(b"%d 0 R" % page_id for page_id in page_ids)
    objects[2] = b"<< /Type /Pages /Kids [%b] /Count %d >>" % (kids, len(page_ids))
    ordered_ids = sorted(objects)
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for object_id in ordered_ids:
        offsets[object_id] = len(pdf)
        pdf.extend(b"%d 0 obj\n%b\nendobj\n" % (object_id, objects[object_id]))

    xref_offset = len(pdf)
    pdf.extend(b"xref\n0 %d\n" % (max(ordered_ids) + 1))
    pdf.extend(b"0000000000 65535 f \n")
    for object_id in range(1, max(ordered_ids) + 1):
        pdf.extend(b"%010d 00000 n \n" % offsets[object_id])
    pdf.extend(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (max(ordered_ids) + 1, xref_offset)
    )
    Path(filename).write_bytes(pdf)
    return len(page_streams)


def build_executive_pdf_pages(
    summary,
    generated,
    period_label,
    integrity_summary=None,
    special_summaries=None,
):
    """Compõe as páginas executivas; rankings e eventos nunca crescem sem limite."""

    builders = [
        lambda number, total: build_cover_page(
            summary,
            generated,
            period_label,
            integrity_summary,
            total,
            special_summaries,
        ),
        lambda number, total: build_overview_page(
            summary,
            generated,
            period_label,
            integrity_summary,
            number,
            total,
        ),
    ]

    if any(
        summary.get(key)
        for key in ("top_equipment", "top_units", "top_incident_types", "top_hosts")
    ):
        builders.append(lambda number, total: build_impact_page(summary, generated, number, total))
    if summary.get("priority", {}).get("top") or summary.get("recurrence", {}).get("top"):
        builders.append(
            lambda number, total: build_attention_page(summary, generated, number, total)
        )
    if summary.get("unit_criticality", {}).get("top"):
        builders.append(
            lambda number, total: build_criticality_page(summary, generated, number, total)
        )
    builders.append(
        lambda number, total: build_conclusion_page(
            summary, generated, period_label, integrity_summary, number, total
        )
    )

    total_pages = len(builders)
    return [builder(index, total_pages) for index, builder in enumerate(builders, start=1)]


def write_pdf_report(
    filename,
    incidents,
    generated,
    summary,
    period_label,
    integrity_summary=None,
    special_summaries=None,
):
    """
    Gera somente o PDF executivo.

    ``incidents`` é mantido na assinatura por compatibilidade, mas o documento
    principal consome exclusivamente os indicadores canônicos de ``summary``.
    """

    del incidents
    pages = build_executive_pdf_pages(
        summary,
        generated,
        period_label,
        integrity_summary,
        special_summaries,
    )
    return _write_pdf(filename, pages)


def technical_pdf_name(executive_filename):
    """Retorna o nome previsível do anexo técnico."""

    path = Path(executive_filename)
    return path.with_name(f"{path.stem}_anexo_tecnico{path.suffix}")


def write_technical_pdf_report(filename, incidents, generated):
    """Gera o detalhamento completo como documento separado e opcional."""

    chunks = [
        incidents[index : index + TECHNICAL_ROWS_PER_PAGE]
        for index in range(0, len(incidents), TECHNICAL_ROWS_PER_PAGE)
    ] or [[]]
    total_pages = len(chunks)
    streams = [
        build_technical_page(rows, index, total_pages, generated)
        for index, rows in enumerate(chunks, start=1)
    ]
    return _write_pdf(filename, streams)
