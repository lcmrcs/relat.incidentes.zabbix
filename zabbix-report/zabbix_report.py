import os
import requests
import pandas as pd

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

        # traz informações do host
        "selectHosts": ["host"],

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
# MAPEAMENTO DE SEVERIDADE
# ==================================================

severity_map = {
    "0": "Não classificado",
    "1": "Informação",
    "2": "Aviso",
    "3": "Média",
    "4": "Alta",
    "5": "Crítica"
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
# LISTA DE INCIDENTES
# ==================================================

incidents = []

print("Processando incidentes...")

# percorre cada problema retornado pela API
for item in data.get("result", []):

    # pega o nome do host
    host = (
        item["hosts"][0]["host"]
        if item.get("hosts")
        else "N/A"
    )

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
    total=len(df),
    incidents=incidents
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
# RESUMO FINAL
# ==================================================

print("\nRELATÓRIOS GERADOS COM SUCESSO")
print("--------------------------------")
print(f"Total de incidentes: {len(df)}")
print(f"Excel: {excel_name}")
print(f"HTML: {html_name}")
