import os
import requests
import pandas as pd

from collections import Counter
from datetime import datetime, timedelta
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

# ==================================================
# DEFINIR CAMINHOS DO PROJETO
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
TEMPLATES_DIR = BASE_DIR / "templates"
REPORTS_DIR = BASE_DIR / "reports"

# ==================================================
# CARREGAR VARIÁVEIS DO .ENV
# ==================================================

# load_dotenv() lê o arquivo .env
# e carrega as variáveis para dentro do Python
load_dotenv(ENV_FILE)

# os.getenv() pega os valores do .env
ZABBIX_URL = os.getenv("ZABBIX_URL")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN")

# ==================================================
# VALIDAR VARIÁVEIS
# ==================================================

if not ZABBIX_URL or not ZABBIX_TOKEN:
    print("ERRO: Variáveis do .env não encontradas.")
    exit()

# ==================================================
# DEFINIR PERÍODO DO RELATÓRIO
# ==================================================

today = datetime.now()

# timedelta(days=7)
# volta 7 dias no tempo
start_week = today - timedelta(days=7)

# timestamp = formato UNIX utilizado pelo Zabbix
time_from = int(start_week.timestamp())
time_till = int(today.timestamp())

# ==================================================
# CABEÇALHO HTTP
# ==================================================

headers = {
    "Content-Type": "application/json-rpc"
}

# ==================================================
# PAYLOAD DA API ZABBIX
# ==================================================

payload = {
    "jsonrpc": "2.0",
    "method": "problem.get",

    "params": {

        # output extend = pega todas as informações
        "output": "extend",

        # pega eventos recentes
        "recent": True,

        # ordenação
        "sortfield": ["eventid"],
        "sortorder": "DESC",

        # período
        "time_from": time_from,
        "time_till": time_till
    },

    # autenticação
    "auth": ZABBIX_TOKEN,

    "id": 1
}

# ==================================================
# REQUISIÇÃO HTTP
# ==================================================

print("Conectando ao Zabbix...")

response = requests.post(
    ZABBIX_URL,
    json=payload,
    headers=headers
)

# ==================================================
# VALIDAR RESPOSTA HTTP
# ==================================================

if response.status_code != 200:
    print(f"Erro HTTP: {response.status_code}")
    print(response.text)
    exit()

# ==================================================
# CONVERTER JSON
# ==================================================

data = response.json()

# ==================================================
# VALIDAR ERRO DA API
# ==================================================

if "error" in data:
    print("Erro retornado pela API Zabbix:")
    print(data["error"])
    exit()

# ==================================================
# BUSCAR HOSTS DOS PROBLEMAS
# ==================================================

problems = data.get("result", [])

trigger_ids = sorted({
    item.get("objectid")
    for item in problems
    if item.get("objectid")
})

hosts_by_trigger = {}

if trigger_ids:

    trigger_payload = {
        "jsonrpc": "2.0",
        "method": "trigger.get",

        "params": {
            "output": ["triggerid"],
            "triggerids": trigger_ids,
            "selectHosts": ["host", "name"]
        },

        "auth": ZABBIX_TOKEN,

        "id": 2
    }

    trigger_response = requests.post(
        ZABBIX_URL,
        json=trigger_payload,
        headers=headers
    )

    if trigger_response.status_code != 200:
        print(f"Erro HTTP ao buscar hosts: {trigger_response.status_code}")
        print(trigger_response.text)
        exit()

    trigger_data = trigger_response.json()

    if "error" in trigger_data:
        print("Erro retornado pela API Zabbix ao buscar hosts:")
        print(trigger_data["error"])
        exit()

    for trigger in trigger_data.get("result", []):
        hosts = trigger.get("hosts", [])

        if hosts:
            hosts_by_trigger[trigger["triggerid"]] = hosts[0].get(
                "host",
                "N/A"
            )

# ==================================================
# MAPEAMENTO DE SEVERIDADE
# ==================================================

severity_map = {
    "0": "Não classificada",
    "1": "Informação",
    "2": "Atenção",
    "3": "Média",
    "4": "Alta",
    "5": "Desastre"
}

# ==================================================
# CLASSIFICAR EQUIPAMENTO
# ==================================================

def classify_equipment(host):

    # lower() transforma tudo em minúsculo
    host = host.lower()

    # any() verifica múltiplas palavras

    if any(x in host for x in ["mikrotik", "mk"]):
        return "Mikrotik"

    elif any(x in host for x in ["switch", "sw"]):
        return "Switch"

    elif "nvr" in host:
        return "NVR"

    elif any(x in host for x in ["camera", "cam"]):
        return "Câmera"

    elif "facial" in host:
        return "Terminal Facial"

    elif "metal" in host:
        return "Portal Detector de Metal"

    elif "alarme" in host:
        return "Central de Alarme"

    return "Outros"


# ==================================================
# GERAR PDF
# ==================================================

def pdf_escape(value):

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

    words = str(value or "").split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)

            current = word[:max_chars]

    if current:
        lines.append(current)

    return lines or [""]


def add_pdf_text(commands, x, y, text, size=8, font="F1"):

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

    severity_counter = Counter(
        item["severity"]
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

    def format_counter(counter):
        return [
            {
                "name": name,
                "total": count,
                "percent": round((count / total) * 100, 1) if total else 0
            }
            for name, count in counter.most_common()
        ]

    return {
        "total": total,
        "critical": severity_counter.get("Desastre", 0),
        "high": severity_counter.get("Alta", 0),
        "medium": severity_counter.get("Média", 0),
        "warning": severity_counter.get("Atenção", 0),
        "severity": format_counter(severity_counter),
        "equipment": format_counter(equipment_counter),
        "top_hosts": format_counter(host_counter)[:8],
    }


def build_summary_pdf_page(summary, generated, period_label, total_pages):

    commands = []

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

    cards = [
        ("Total", summary["total"]),
        ("Desastres", summary["critical"]),
        ("Altas", summary["high"]),
        ("Medias", summary["medium"]),
    ]

    x = 36

    for label, value in cards:
        commands.append(
            b"0.93 0.95 0.97 rg %.2f 470 178 48 re f\n" % x
        )
        commands.append(
            b"0.75 0.80 0.86 RG %.2f 470 178 48 re S\n" % x
        )
        add_pdf_text(commands, x + 12, 500, label, 9, "F2")
        add_pdf_text(commands, x + 12, 480, value, 18, "F2")
        x += 192

    add_pdf_text(commands, 36, 432, "Distribuicao por severidade", 12, "F2")
    y = 408

    for item in summary["severity"][:6]:
        add_pdf_text(
            commands,
            48,
            y,
            f"{item['name']}: {item['total']} ({item['percent']}%)",
            9
        )
        y -= 18

    add_pdf_text(commands, 330, 432, "Equipamentos mais afetados", 12, "F2")
    y = 408

    for item in summary["equipment"][:8]:
        add_pdf_text(
            commands,
            342,
            y,
            f"{item['name']}: {item['total']} ({item['percent']}%)",
            9
        )
        y -= 18

    add_pdf_text(commands, 36, 248, "Hosts com mais incidentes", 12, "F2")
    y = 224

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

    commands = []

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

    headers = ["Data", "Host", "Equipamento", "Incidente", "Sev.", "Evento"]
    columns = [
        (36, 82, 14),
        (118, 170, 28),
        (288, 112, 18),
        (400, 260, 44),
        (660, 58, 9),
        (718, 76, 12),
    ]

    y = 512

    commands.append(b"0.93 0.95 0.97 rg 34 500 774 22 re f\n")
    commands.append(b"0.75 0.80 0.86 RG 34 500 774 22 re S\n")

    for index, header in enumerate(headers):
        x, _, _ = columns[index]
        add_pdf_text(commands, x, y + 2, header, 8, "F2")

    y = 482

    for row in rows:
        row_lines = [
            wrap_text(row["date"], columns[0][2]),
            wrap_text(row["host"], columns[1][2]),
            wrap_text(row["equipment"], columns[2][2]),
            wrap_text(row["incident"], columns[3][2]),
            wrap_text(row["severity"], columns[4][2]),
            wrap_text(row["eventid"], columns[5][2]),
        ]

        line_count = max(len(lines) for lines in row_lines)
        row_height = max(20, line_count * 10 + 8)

        commands.append(
            b"0.86 0.89 0.93 RG 34 %.2f 774 %.2f re S\n" % (
                y - row_height + 10,
                row_height
            )
        )

        for column_index, lines in enumerate(row_lines):
            x, _, _ = columns[column_index]

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

    rows_per_page = 18
    pages = [
        incidents[index:index + rows_per_page]
        for index in range(0, len(incidents), rows_per_page)
    ] or [[]]

    total_pages = len(pages) + 1
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

    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
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
        objects[content_id] = (
            b"<< /Length %d >>\nstream\n%bendstream" % (
                len(stream),
                stream
            )
        )

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

    ordered_ids = sorted(objects)
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = {}

    for object_id in ordered_ids:
        offsets[object_id] = len(pdf)
        pdf.extend(b"%d 0 obj\n%b\nendobj\n" % (
            object_id,
            objects[object_id]
        ))

    xref_offset = len(pdf)
    pdf.extend(b"xref\n0 %d\n" % (max(ordered_ids) + 1))
    pdf.extend(b"0000000000 65535 f \n")

    for object_id in range(1, max(ordered_ids) + 1):
        pdf.extend(b"%010d 00000 n \n" % offsets[object_id])

    pdf.extend(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            max(ordered_ids) + 1,
            xref_offset
        )
    )

    with open(filename, "wb") as f:
        f.write(pdf)

# ==================================================
# LISTA DE INCIDENTES
# ==================================================

incidents = []

print("Processando incidentes...")

# percorre cada problema retornado pela API
for item in problems:

    # pega o nome do host
    host = hosts_by_trigger.get(item.get("objectid"), "N/A")

    # nome do problema
    incident = item.get("name", "N/A")

    # severidade convertida
    severity = severity_map.get(
        item.get("severity", "0"),
        "Desconhecida"
    )

    # data formatada
    date = datetime.fromtimestamp(
        int(item["clock"])
    ).strftime("%d/%m/%Y %H:%M")

    # event id
    eventid = item.get("eventid")

    # classificação automática
    equipment = classify_equipment(host)

    # adiciona na lista
    incidents.append({
        "host": host,
        "equipment": equipment,
        "incident": incident,
        "severity": severity,
        "date": date,
        "eventid": eventid
    })

# ==================================================
# DATAFRAME PANDAS
# ==================================================

# transforma lista em tabela
df = pd.DataFrame(incidents)

# monta indicadores para apresentacao
summary = build_report_summary(incidents)
period_label = (
    f"{start_week.strftime('%d/%m/%Y %H:%M')} a "
    f"{today.strftime('%d/%m/%Y %H:%M')}"
)

# ==================================================
# CRIAR PASTA REPORTS
# ==================================================

# exist_ok=True evita erro se já existir
REPORTS_DIR.mkdir(exist_ok=True)

# ==================================================
# EXPORTAR EXCEL
# ==================================================

excel_name = (
    REPORTS_DIR /
    f"report_{today.strftime('%Y-%m-%d')}.xlsx"
)

# salva excel
df.to_excel(excel_name, index=False)

print(f"Excel gerado: {excel_name}")

# ==================================================
# GERAR HTML
# ==================================================

# carrega pasta templates
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR)
)

# carrega template HTML
template = env.get_template(
    "report_template.html"
)

# renderiza HTML com os dados
html_output = template.render(
    generated=today.strftime("%d/%m/%Y %H:%M"),
    period=period_label,
    total=len(df),
    incidents=incidents,
    summary=summary
)

# nome do arquivo
html_name = (
    REPORTS_DIR /
    f"report_{today.strftime('%Y-%m-%d')}.html"
)

# escreve arquivo HTML
with open(html_name, "w", encoding="utf-8") as f:
    f.write(html_output)

print(f"HTML gerado: {html_name}")

# ==================================================
# GERAR PDF
# ==================================================

# nome do arquivo
pdf_name = (
    REPORTS_DIR /
    f"report_{today.strftime('%Y-%m-%d')}.pdf"
)

# escreve arquivo PDF
write_pdf_report(
    pdf_name,
    incidents,
    today.strftime("%d/%m/%Y %H:%M"),
    summary,
    period_label
)

print(f"PDF gerado: {pdf_name}")

# ==================================================
# RESUMO FINAL
# ==================================================

print("\nRELATÓRIOS GERADOS COM SUCESSO")
print("--------------------------------")
print(f"Total de incidentes: {len(df)}")
print(f"Excel: {excel_name}")
print(f"HTML: {html_name}")
print(f"PDF: {pdf_name}")
