"""
Gera relatórios de incidentes do Zabbix em Excel, HTML e PDF.

Este arquivo agora funciona como coordenador do fluxo. As regras de
classificação, acesso ao Zabbix, cálculo de indicadores e geração do PDF ficam
em módulos separados para facilitar leitura, manutenção e testes.
"""

import argparse
import base64
import os
import re
import unicodedata

import pandas as pd

from datetime import datetime, timedelta
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from pathlib import Path

from classifiers import (
    SEVERITY_MAP,
    build_unit_catalog,
    classify_equipment,
    classify_incident_type,
    classify_unit_group,
)
from pdf_report import write_pdf_report
from summary import build_report_summary, format_age
from zabbix_api import ZabbixClient


# ==================================================
# CAMINHOS DO PROJETO
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
TEMPLATES_DIR = BASE_DIR / "templates"
ASSETS_DIR = BASE_DIR / "assets"
REPORTS_DIR = BASE_DIR / "reports"

EXCEL_COLUMNS = [
    ("date", "Data de abertura"),
    ("unit_code", "Código da unidade"),
    ("unit", "Unidade"),
    ("host", "Host"),
    ("equipment", "Equipamento"),
    ("incident_type", "Tipo de incidente"),
    ("incident", "Incidente"),
    ("severity", "Severidade"),
    ("status", "Status"),
    ("age_label", "Tempo offline"),
    ("eventid", "Evento Zabbix"),
]

EXCEL_SEVERITY_COLORS = {
    "Desastre": "7F1D1D",
    "Alta": "EA580C",
    "Média": "D97706",
    "Atenção": "15803D",
    "Informação": "2563EB",
    "Não classificada": "64748B",
}


def slugify(value):
    """
    Converte textos livres em parte segura para nome de arquivo.

    Exemplo: "Terminal Facial" vira "terminal_facial".
    """

    normalized = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = normalized.encode("ascii", errors="ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)

    return normalized.strip("_") or "filtro"


def load_asset_data_uri(filename):
    """
    Carrega um arquivo de imagem em formato embutido para o HTML.

    O relatório final precisa continuar abrindo sozinho quando for enviado por
    e-mail ou copiado para outro computador. Por isso a imagem é transformada
    em base64, evitando dependência de um arquivo separado ao lado do HTML.
    """

    logo_path = ASSETS_DIR / filename
    if not logo_path.exists():
        return None

    mime_types = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
    }
    mime_type = mime_types.get(logo_path.suffix.lower(), "application/octet-stream")
    encoded_logo = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded_logo}"


def load_logo_data_uri():
    """
    Carrega a logo principal do projeto em formato embutido para o HTML.
    """

    return load_asset_data_uri("logoTechPng.png")


def load_confea_logo_data_uri():
    """
    Carrega a logo da CONFEA para destacar o painel de VPN.
    """

    return load_asset_data_uri("logoConfea.png")


def load_zabbix_icon_data_uri():
    """
    Carrega o ícone oficial do Zabbix usado no painel resumido.
    """

    return load_asset_data_uri("zabbixLogoIcon.webp")


def load_zabbix_logo_data_uri():
    """
    Carrega a logo completa do Zabbix usada no modal de detalhes.
    """

    return load_asset_data_uri("zabbixLogoFull.png")


def cleanup_old_reports(current_base_name, keep_count=1):
    """
    Remove conjuntos antigos de relatórios gerados automaticamente.

    Cada execução cria um trio de arquivos com o mesmo nome base:
    .html, .pdf e .xlsx. Para evitar acumular arquivos antigos em
    zabbix-report/reports/, esta função mantém apenas os conjuntos mais
    recentes e apaga os anteriores.
    """

    try:
        keep_count = int(keep_count)
    except (TypeError, ValueError):
        keep_count = 1

    keep_count = max(1, keep_count)
    report_groups = {}

    for path in REPORTS_DIR.glob("report_*"):
        if path.suffix.lower() not in {".html", ".pdf", ".xlsx"}:
            continue

        report_groups.setdefault(path.stem, []).append(path)

    if current_base_name not in report_groups:
        report_groups[current_base_name] = []

    def group_mtime(item):
        _, paths = item
        if not paths:
            return 0
        return max(path.stat().st_mtime for path in paths if path.exists())

    ordered_groups = sorted(
        report_groups.items(),
        key=group_mtime,
        reverse=True,
    )
    keep_names = {current_base_name}

    for name, _ in ordered_groups:
        if len(keep_names) >= keep_count:
            break
        keep_names.add(name)
    removed = []

    for name, paths in report_groups.items():
        if name in keep_names:
            continue

        for path in paths:
            if path.exists():
                path.unlink()
                removed.append(path)

    return removed


# ==================================================
# ARGUMENTOS E PERÍODO
# ==================================================

def parse_period(value):
    """
    Converte textos como 24h, 2d e 7d em um timedelta.

    O valor "historico" retorna None para indicar que a consulta deve buscar
    desde o registro mais antigo disponível no Zabbix.
    """

    normalized = str(value).strip().lower()

    if normalized in ["historico", "histórico", "tudo", "todos", "all"]:
        return None, "histórico completo"

    if len(normalized) < 2:
        print("ERRO: use um período como 24h, 2d, 5d ou 7d.")
        raise SystemExit(1)

    amount = normalized[:-1]
    unit = normalized[-1]

    if not amount.isdigit() or int(amount) <= 0:
        print("ERRO: o valor do período precisa ser maior que zero.")
        raise SystemExit(1)

    amount = int(amount)

    if unit == "h":
        return timedelta(hours=amount), f"últimas {amount} hora(s)"

    if unit == "d":
        return timedelta(days=amount), f"últimos {amount} dia(s)"

    print("ERRO: unidade inválida. Use h para horas ou d para dias.")
    raise SystemExit(1)


def parse_args():
    """
    Lê as opções do terminal sem exigir alteração no código.

    --dias foi mantido por compatibilidade, mas --periodo é a opção mais
    flexível para 24h, 2d, 5d, 7d e historico.
    """

    parser = argparse.ArgumentParser(
        description="Gera relatórios de incidentes do Zabbix."
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=None,
        help="Quantidade de dias que serão pesquisados. Mantido por compatibilidade.",
    )
    parser.add_argument(
        "--periodo",
        default="7d",
        help=(
            "Intervalo pesquisado. Exemplos: 24h, 2d, 5d, 7d, 30d, historico. "
            "Padrão: 7d."
        ),
    )
    parser.add_argument(
        "--desde",
        default=None,
        help="Data inicial no formato AAAA-MM-DD. Exemplo: --desde 2026-01-01.",
    )
    parser.add_argument(
        "--status",
        choices=["todos", "abertos", "resolvidos"],
        default="todos",
        help="Filtra eventos por situação. Use abertos para ignorar resolvidos.",
    )
    parser.add_argument(
        "--equipamento",
        default=None,
        help=(
            "Filtra o relatório por tipo de equipamento. "
            "Exemplo: --equipamento \"Terminal Facial\"."
        ),
    )
    parser.add_argument(
        "--manter-relatorios",
        type=int,
        default=1,
        help=(
            "Quantidade de conjuntos antigos que devem permanecer na pasta "
            "reports. Padrão: 1, mantendo apenas o relatório mais recente."
        ),
    )

    args = parser.parse_args()

    if args.dias is not None and args.dias <= 0:
        print("ERRO: o argumento --dias precisa ser maior que zero.")
        raise SystemExit(1)

    if args.manter_relatorios <= 0:
        print("ERRO: o argumento --manter-relatorios precisa ser maior que zero.")
        raise SystemExit(1)

    return args


def resolve_period(args, today):
    """
    Calcula intervalo, rótulo e slug usados na API e no nome dos arquivos.
    """

    if args.desde:
        try:
            start_date = datetime.strptime(args.desde, "%Y-%m-%d")
        except ValueError:
            print("ERRO: use --desde no formato AAAA-MM-DD. Exemplo: 2026-01-01.")
            raise SystemExit(1)

        period_name = f"desde {start_date.strftime('%d/%m/%Y')}"
        period_slug = f"desde_{args.desde}"

    elif args.dias is not None:
        start_date = today - timedelta(days=args.dias)
        period_name = f"últimos {args.dias} dia(s)"
        period_slug = f"{args.dias}d"

    else:
        period_delta, period_name = parse_period(args.periodo)
        period_slug = str(args.periodo).strip().lower()
        start_date = today - period_delta if period_delta else None

    if args.status != "todos":
        period_name = f"{period_name} ({args.status})"
        period_slug = f"{period_slug}_{args.status}"

    return start_date, period_name, period_slug


def format_period_label(period_name, start_date, today):
    """
    Monta o texto exibido no HTML, PDF e terminal para o período consultado.
    """

    if start_date:
        return (
            f"{period_name}: {start_date.strftime('%d/%m/%Y %H:%M')} a "
            f"{today.strftime('%d/%m/%Y %H:%M')}"
        )

    return f"{period_name}: até {today.strftime('%d/%m/%Y %H:%M')}"


# ==================================================
# CONFIGURAÇÃO
# ==================================================

def load_config():
    """
    Carrega URL e token do arquivo .env local.

    O .env fica fora do Git porque contém credenciais. O script para cedo caso
    alguma variável obrigatória não exista.
    """

    load_dotenv(ENV_FILE)
    zabbix_url = os.getenv("ZABBIX_URL")
    zabbix_token = os.getenv("ZABBIX_TOKEN")

    if not zabbix_url or not zabbix_token:
        print("ERRO: Variáveis do .env não encontradas.")
        raise SystemExit(1)

    return zabbix_url, zabbix_token


def build_zabbix_web_url(zabbix_url):
    """
    Converte a URL da API em URL navegável do Zabbix.

    O .env guarda normalmente o endpoint JSON-RPC, como
    /api_jsonrpc.php. Para criar links clicáveis no relatório, removemos esse
    sufixo e usamos apenas a raiz web do Zabbix.
    """

    web_url = str(zabbix_url or "").strip()
    if web_url.endswith("/api_jsonrpc.php"):
        web_url = web_url[: -len("/api_jsonrpc.php")]

    return web_url.rstrip("/")


# ==================================================
# PROCESSAMENTO DOS INCIDENTES
# ==================================================

def build_incidents(
    problems,
    hosts_by_trigger,
    host_ids_by_trigger,
    host_details_by_id,
    resolved_at_by_event,
    unit_catalog,
    status_filter,
    generated_at,
):
    """
    Transforma problemas brutos do Zabbix em linhas prontas para relatório.

    Cada item retornado contém host, unidade, equipamento, incidente, severidade,
    status, datas e eventid. Esse formato único alimenta Excel, HTML e PDF.
    """

    incidents = []

    for item in problems:
        host = hosts_by_trigger.get(item.get("objectid"), "N/A")
        host_id = host_ids_by_trigger.get(item.get("objectid"))
        host_details = host_details_by_id.get(host_id, {})
        incident = item.get("name", "N/A")
        severity = SEVERITY_MAP.get(item.get("severity", "0"), "Desconhecida")
        timestamp = int(item["clock"])
        age_seconds = max(0, int(generated_at.timestamp()) - timestamp)
        date = datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")
        eventid = item.get("eventid")
        recovery_eventid = item.get("r_eventid")
        resolved_at = resolved_at_by_event.get(recovery_eventid, "")
        status = "Resolvido" if resolved_at else "Aberto"

        if status_filter == "abertos" and status != "Aberto":
            continue

        if status_filter == "resolvidos" and status != "Resolvido":
            continue

        equipment = classify_equipment(host)
        incident_type = classify_incident_type(incident)
        unit_code, unit = classify_unit_group(host, host_details, unit_catalog)

        incident_key = "|".join([
            unit_code,
            host,
            equipment,
            incident,
            severity,
        ])

        incidents.append({
            "host": host,
            "unit_code": unit_code,
            "unit": unit,
            "incident_key": incident_key,
            "equipment": equipment,
            "incident": incident,
            "incident_type": incident_type,
            "severity": severity,
            "status": status,
            "date": date,
            "timestamp": timestamp,
            "age_seconds": age_seconds,
            "age_label": format_age(age_seconds),
            "resolved_at": resolved_at,
            "eventid": eventid,
        })

    return incidents


def split_special_groups(incidents):
    """
    Separa unidades escolares dos grupos especiais.

    Zabbix Server e CONFEA VPN são monitorados pelo Zabbix, mas não são unidade
    escolar. Separá-los mantém os indicadores escolares limpos.
    """

    main_incidents = [
        item
        for item in incidents
        if item["unit_code"] not in ["ZBX", "CONFEA"]
    ]
    zabbix_incidents = [
        item
        for item in incidents
        if item["unit_code"] == "ZBX"
    ]
    confea_incidents = [
        item
        for item in incidents
        if item["unit_code"] == "CONFEA"
    ]

    return main_incidents, zabbix_incidents, confea_incidents


def filter_by_equipment(incidents, equipment_name):
    """
    Mantém apenas incidentes do equipamento informado no argumento.

    A comparação ignora maiúsculas/minúsculas e espaços extras para facilitar o
    uso no terminal.
    """

    if not equipment_name:
        return incidents

    target = str(equipment_name).strip().lower()

    return [
        item
        for item in incidents
        if str(item.get("equipment", "")).strip().lower() == target
    ]


# ==================================================
# EXPORTAÇÃO
# ==================================================

def incidents_to_excel_frame(incidents):
    """
    Converte incidentes em DataFrame com nomes amigáveis para o Excel.

    A lista de colunas é fixa para manter a planilha previsível mesmo quando
    alguma execução não retorna incidentes.
    """

    rows = []

    for item in incidents:
        rows.append({
            label: item.get(key, "")
            for key, label in EXCEL_COLUMNS
        })

    return pd.DataFrame(rows, columns=[label for _, label in EXCEL_COLUMNS])


def counter_to_excel_frame(items):
    """
    Transforma rankings do resumo em uma tabela simples para o Excel.
    """

    return pd.DataFrame(
        [
            {
                "Nome": item["name"],
                "Total": item["total"],
                "Percentual": item["percent"],
            }
            for item in items
        ],
        columns=["Nome", "Total", "Percentual"],
    )


def build_excel_summary_rows(summary, generated, period_label):
    """
    Monta os blocos textuais da aba Resumo Executivo.
    """

    age = summary["age"]

    return [
        ("Relatório Executivo de Incidentes Zabbix", ""),
        ("Gerado em", generated),
        ("Período analisado", period_label),
        ("Produzido por", "Network Operations Center"),
        ("", ""),
        ("Incidentes abertos", summary["unique_open"]),
        ("Mais antigo aberto", age["oldest_label"]),
        ("Média de idade", age["average_label"]),
        ("Acima de 7 dias", age["over_7d"]),
        ("Índice médio de prioridade", summary["priority"]["average_score"]),
        ("Prioridade crítica", summary["priority"]["critical"]),
        ("Prioridade alta", summary["priority"]["high"]),
        ("Hosts reincidentes", summary["recurrence"]["affected_hosts"]),
        ("", ""),
        ("Alta", summary["high"]),
        ("Média", summary["medium"]),
        ("Atenção", summary["attention"]),
        ("Informação", summary["information"]),
        ("Desastre", summary["critical"]),
    ]


def build_excel_intelligence_frames(summary):
    """
    Monta tabelas executivas de comparativo, reincidência e prioridade.
    """

    comparison = pd.DataFrame(
        [
            {
                "Faixa": item["label"],
                "Total": item["total"],
                "Percentual": item["percent"],
                "Alta criticidade": item["high"],
            }
            for item in summary["period_comparison"]["ranges"]
        ],
        columns=["Faixa", "Total", "Percentual", "Alta criticidade"],
    )
    recurrence = pd.DataFrame(
        [
            {
                "Host": item["host"],
                "Unidade": item["unit"],
                "Equipamento": item["equipment"],
                "Tipo de incidente": item["incident_type"],
                "Ocorrências": item["total"],
                "Índice": item["score"],
            }
            for item in summary["recurrence"]["top"]
        ],
        columns=[
            "Host",
            "Unidade",
            "Equipamento",
            "Tipo de incidente",
            "Ocorrências",
            "Índice",
        ],
    )
    priority = pd.DataFrame(
        [
            {
                "Índice": item["score"],
                "Prioridade": item["label"],
                "Host": item["host"],
                "Unidade": item["unit"],
                "Equipamento": item["equipment"],
                "Tipo de incidente": item["incident_type"],
                "Severidade": item["severity"],
                "Tempo offline": item["age_label"],
                "Evento": item["eventid"],
            }
            for item in summary["priority"]["top"]
        ],
        columns=[
            "Índice",
            "Prioridade",
            "Host",
            "Unidade",
            "Equipamento",
            "Tipo de incidente",
            "Severidade",
            "Tempo offline",
            "Evento",
        ],
    )

    return [
        ("Distribuição temporal", comparison),
        ("Padrões recorrentes", recurrence),
        ("Prioridades operacionais", priority),
    ]


def style_excel_workbook(writer):
    """
    Aplica acabamento visual, filtros e congelamento em todas as abas.

    A formatação fica no final para que os dados sejam exportados primeiro pelo
    pandas e depois refinados com openpyxl.
    """

    workbook = writer.book
    header_fill = PatternFill("solid", fgColor="073B43")
    accent_fill = PatternFill("solid", fgColor="E8FAF8")
    dark_fill = PatternFill("solid", fgColor="062A30")
    soft_fill = PatternFill("solid", fgColor="F6FBFB")
    border_color = "BFD8DC"
    thin_border = Border(
        left=Side(style="thin", color=border_color),
        right=Side(style="thin", color=border_color),
        top=Side(style="thin", color=border_color),
        bottom=Side(style="thin", color=border_color),
    )

    for sheet_index, worksheet in enumerate(workbook.worksheets):
        worksheet.sheet_view.showGridLines = False
        worksheet.freeze_panes = "A2"

        if worksheet.max_row > 1 and worksheet.max_column > 1:
            worksheet.auto_filter.ref = worksheet.dimensions

        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        for row in worksheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                cell.border = thin_border
                if cell.row % 2 == 0:
                    cell.fill = soft_fill

        for column_cells in worksheet.columns:
            column_letter = get_column_letter(column_cells[0].column)
            max_length = max(
                len(str(cell.value or ""))
                for cell in column_cells[:80]
            )
            worksheet.column_dimensions[column_letter].width = min(
                max(max_length + 3, 13),
                42,
            )

        if (
            worksheet.title not in {"Resumo Executivo", "Rankings", "Inteligência"}
            and worksheet.max_row > 1
        ):
            table_ref = worksheet.dimensions
            table_name = f"Tabela{sheet_index + 1}"
            table = Table(displayName=table_name, ref=table_ref)
            table.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2",
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False,
            )
            worksheet.add_table(table)

            headers = [cell.value for cell in worksheet[1]]
            severity_index = headers.index("Severidade") + 1 if "Severidade" in headers else None
            status_index = headers.index("Status") + 1 if "Status" in headers else None

            for row in worksheet.iter_rows(min_row=2):
                if severity_index:
                    severity_cell = row[severity_index - 1]
                    color = EXCEL_SEVERITY_COLORS.get(str(severity_cell.value), "64748B")
                    severity_cell.fill = PatternFill("solid", fgColor=color)
                    severity_cell.font = Font(color="FFFFFF", bold=True)
                    severity_cell.alignment = Alignment(horizontal="center")

                if status_index:
                    status_cell = row[status_index - 1]
                    if status_cell.value == "Aberto":
                        status_cell.fill = PatternFill("solid", fgColor="FEE2E2")
                        status_cell.font = Font(color="B91C1C", bold=True)
                    elif status_cell.value == "Resolvido":
                        status_cell.fill = PatternFill("solid", fgColor="DCFCE7")
                        status_cell.font = Font(color="166534", bold=True)

        worksheet.row_dimensions[1].height = 24

    summary_sheet = workbook["Resumo Executivo"]
    summary_sheet.freeze_panes = None
    summary_sheet.column_dimensions["A"].width = 32
    summary_sheet.column_dimensions["B"].width = 44
    summary_sheet["A1"].fill = dark_fill
    summary_sheet["B1"].fill = dark_fill
    summary_sheet["A1"].font = Font(color="FFFFFF", bold=True, size=16)
    summary_sheet["B1"].font = Font(color="FFFFFF", bold=True, size=16)

    for row_number in range(2, 20):
        summary_sheet[f"A{row_number}"].font = Font(color="455A64", bold=True)
        summary_sheet[f"B{row_number}"].font = Font(color="073B43", bold=True)
        summary_sheet[f"A{row_number}"].fill = accent_fill
        summary_sheet[f"B{row_number}"].fill = accent_fill

    summary_sheet.sheet_properties.tabColor = "087F8C"

    for worksheet in workbook.worksheets:
        if worksheet.title == "Unidades":
            worksheet.sheet_properties.tabColor = "087F8C"
        elif worksheet.title == "Servidor Zabbix":
            worksheet.sheet_properties.tabColor = "DC2626"
        elif worksheet.title == "CONFEA VPN":
            worksheet.sheet_properties.tabColor = "7C3AED"
        elif worksheet.title == "Todos":
            worksheet.sheet_properties.tabColor = "0F766E"

    if "Rankings" in workbook.sheetnames:
        rankings_sheet = workbook["Rankings"]
        rankings_sheet.sheet_properties.tabColor = "0E7490"

    if "Inteligência" in workbook.sheetnames:
        intelligence_sheet = workbook["Inteligência"]
        intelligence_sheet.sheet_properties.tabColor = "12343B"

        for row in intelligence_sheet.iter_rows():
            first_cell = row[0]
            if first_cell.value and all(cell.value in (None, "") for cell in row[1:]):
                first_cell.fill = dark_fill
                first_cell.font = Font(color="FFFFFF", bold=True)


def add_excel_charts(writer):
    """
    Cria gráficos simples na aba de resumo a partir da aba Rankings.
    """

    workbook = writer.book

    if "Rankings" not in workbook.sheetnames:
        return

    summary_sheet = workbook["Resumo Executivo"]
    rankings_sheet = workbook["Rankings"]

    if rankings_sheet.max_row < 3:
        return

    chart = DoughnutChart()
    chart.title = "Severidade"
    labels = Reference(rankings_sheet, min_col=1, min_row=2, max_row=6)
    data = Reference(rankings_sheet, min_col=2, min_row=1, max_row=6)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    chart.holeSize = 58
    chart.height = 7
    chart.width = 9
    summary_sheet.add_chart(chart, "D2")

    equipment_start = 10
    equipment_end = min(rankings_sheet.max_row, equipment_start + 7)

    if equipment_end > equipment_start:
        bar_chart = BarChart()
        bar_chart.title = "Equipamentos mais afetados"
        bar_chart.y_axis.title = "Incidentes"
        bar_chart.x_axis.title = "Equipamento"
        labels = Reference(
            rankings_sheet,
            min_col=1,
            min_row=equipment_start + 1,
            max_row=equipment_end,
        )
        data = Reference(
            rankings_sheet,
            min_col=2,
            min_row=equipment_start,
            max_row=equipment_end,
        )
        bar_chart.add_data(data, titles_from_data=True)
        bar_chart.set_categories(labels)
        bar_chart.height = 7
        bar_chart.width = 12
        summary_sheet.add_chart(bar_chart, "D18")


def export_excel(
    path,
    all_incidents,
    main_incidents,
    zabbix_incidents,
    confea_incidents,
    summary,
    generated,
    period_label,
):
    """
    Gera a planilha Excel com abas separadas por finalidade.

    A aba Unidades é a visão escolar. As abas Servidor Zabbix e CONFEA VPN
    isolam infraestrutura especial. A aba Todos preserva a visão completa.
    """

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(
            build_excel_summary_rows(summary, generated, period_label),
            columns=["Indicador", "Valor"],
        ).to_excel(
            writer,
            sheet_name="Resumo Executivo",
            index=False,
        )

        rankings_frames = [
            ("Severidade", counter_to_excel_frame(summary["severity"])),
            ("Equipamentos", counter_to_excel_frame(summary["top_equipment"])),
            ("Tipos de incidente", counter_to_excel_frame(summary["top_incident_types"])),
            ("Unidades", counter_to_excel_frame(summary["top_units"])),
            ("Hosts", counter_to_excel_frame(summary["top_hosts"])),
        ]
        start_row = 0

        for title, frame in rankings_frames:
            pd.DataFrame([[title, "", ""]], columns=["Nome", "Total", "Percentual"]).to_excel(
                writer,
                sheet_name="Rankings",
                index=False,
                header=start_row == 0,
                startrow=start_row,
            )
            frame.to_excel(
                writer,
                sheet_name="Rankings",
                index=False,
                header=False,
                startrow=start_row + 1,
            )
            start_row += len(frame) + 4

        start_row = 0

        for title, frame in build_excel_intelligence_frames(summary):
            pd.DataFrame([[title]], columns=["Indicador"]).to_excel(
                writer,
                sheet_name="Inteligência",
                index=False,
                header=False,
                startrow=start_row,
            )
            frame.to_excel(
                writer,
                sheet_name="Inteligência",
                index=False,
                startrow=start_row + 1,
            )
            start_row += len(frame) + 4

        incidents_to_excel_frame(main_incidents).to_excel(
            writer,
            sheet_name="Unidades",
            index=False,
        )

        if zabbix_incidents:
            incidents_to_excel_frame(zabbix_incidents).to_excel(
                writer,
                sheet_name="Servidor Zabbix",
                index=False,
            )

        if confea_incidents:
            incidents_to_excel_frame(confea_incidents).to_excel(
                writer,
                sheet_name="CONFEA VPN",
                index=False,
            )

        incidents_to_excel_frame(all_incidents).to_excel(
            writer,
            sheet_name="Todos",
            index=False,
        )

        style_excel_workbook(writer)
        add_excel_charts(writer)


def render_html(
    path,
    generated,
    period_label,
    main_incidents,
    summary,
    zabbix_incidents,
    zabbix_summary,
    confea_incidents,
    confea_summary,
    zabbix_web_url,
):
    """
    Renderiza o template HTML com os dados já processados.

    O Jinja2 separa apresentação dos dados: o Python prepara informações e o
    template decide como mostrar cards, filtros, tabelas e janelas.
    """

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report_template.html")
    html_output = template.render(
        generated=generated,
        period=period_label,
        total=len(main_incidents),
        incidents=main_incidents,
        summary=summary,
        zabbix_incidents=zabbix_incidents,
        zabbix_summary=zabbix_summary,
        confea_incidents=confea_incidents,
        confea_summary=confea_summary,
        logo_data_uri=load_logo_data_uri(),
        zabbix_icon_data_uri=load_zabbix_icon_data_uri(),
        zabbix_logo_data_uri=load_zabbix_logo_data_uri(),
        confea_logo_data_uri=load_confea_logo_data_uri(),
        zabbix_web_url=zabbix_web_url,
    )

    with open(path, "w", encoding="utf-8") as file:
        file.write(html_output)


# ==================================================
# EXECUÇÃO PRINCIPAL
# ==================================================

def main():
    """
    Coordena o relatório inteiro, do terminal até os arquivos finais.
    """

    args = parse_args()
    zabbix_url, zabbix_token = load_config()
    zabbix_web_url = build_zabbix_web_url(zabbix_url)
    today = datetime.now()
    start_date, period_name, period_slug = resolve_period(args, today)
    period_label = format_period_label(period_name, start_date, today)
    time_from = int(start_date.timestamp()) if start_date else None
    time_till = int(today.timestamp())

    client = ZabbixClient(zabbix_url, zabbix_token)

    print("Conectando ao Zabbix...")
    problems = client.get_problems(args.status, time_from, time_till)
    resolved_at_by_event = client.get_recovery_dates(problems)
    (
        hosts_by_trigger,
        host_ids_by_trigger,
        host_details_by_id,
    ) = client.get_trigger_hosts(problems)
    all_host_details_by_id = client.get_all_hosts_with_tags()

    print("Processando incidentes...")
    unit_catalog = build_unit_catalog(all_host_details_by_id)
    incidents = build_incidents(
        problems,
        hosts_by_trigger,
        host_ids_by_trigger,
        host_details_by_id,
        resolved_at_by_event,
        unit_catalog,
        args.status,
        today,
    )
    main_incidents, zabbix_incidents, confea_incidents = split_special_groups(
        incidents
    )
    equipment_filter = str(args.equipamento).strip() if args.equipamento else ""

    if equipment_filter:
        main_incidents = filter_by_equipment(main_incidents, equipment_filter)
        zabbix_incidents = []
        confea_incidents = []
        period_label = f"{period_label} | Equipamento: {equipment_filter}"
        period_slug = f"{period_slug}_{slugify(equipment_filter)}"

    scoped_incidents = main_incidents + zabbix_incidents + confea_incidents
    summary = build_report_summary(main_incidents)
    zabbix_summary = build_report_summary(zabbix_incidents)
    confea_summary = build_report_summary(confea_incidents)

    REPORTS_DIR.mkdir(exist_ok=True)
    base_name = f"report_{today.strftime('%Y-%m-%d')}_{period_slug}"
    generated = today.strftime("%d/%m/%Y %H:%M")
    excel_name = REPORTS_DIR / f"{base_name}.xlsx"
    html_name = REPORTS_DIR / f"{base_name}.html"
    pdf_name = REPORTS_DIR / f"{base_name}.pdf"

    export_excel(
        excel_name,
        scoped_incidents,
        main_incidents,
        zabbix_incidents,
        confea_incidents,
        summary,
        generated,
        period_label,
    )
    print(f"Excel gerado: {excel_name}")

    render_html(
        html_name,
        generated,
        period_label,
        main_incidents,
        summary,
        zabbix_incidents,
        zabbix_summary,
        confea_incidents,
        confea_summary,
        zabbix_web_url,
    )
    print(f"HTML gerado: {html_name}")

    write_pdf_report(
        pdf_name,
        main_incidents,
        generated,
        summary,
        period_label,
    )
    print(f"PDF gerado: {pdf_name}")

    removed_reports = cleanup_old_reports(
        base_name,
        keep_count=args.manter_relatorios,
    )

    if removed_reports:
        print(
            "Relatórios antigos removidos: "
            f"{len(removed_reports)} arquivo(s)."
        )

    print("\nRELATÓRIOS GERADOS COM SUCESSO")
    print("--------------------------------")
    print(f"Periodo: {period_label}")
    print(f"Eventos de unidades: {summary['event_total']}")
    print(f"Incidentes únicos de unidades: {summary['unique_total']}")
    print(f"Incidentes únicos abertos de unidades: {summary['unique_open']}")
    print(f"Incidentes únicos resolvidos de unidades: {summary['unique_resolved']}")
    print(f"Eventos abertos de unidades: {summary['open']}")
    print(f"Eventos resolvidos de unidades: {summary['resolved']}")
    print(f"Eventos do Servidor Zabbix: {zabbix_summary['event_total']}")
    print(f"Eventos da CONFEA VPN: {confea_summary['event_total']}")
    print(f"Excel: {excel_name}")
    print(f"HTML: {html_name}")
    print(f"PDF: {pdf_name}")


if __name__ == "__main__":
    main()
