"""
Gera relatórios de incidentes do Zabbix em Excel, HTML e PDF.

Fluxo geral do script:
1. Lê credenciais e endpoint do arquivo .env.
2. Busca eventos de problema no intervalo exato informado.
3. Busca os hosts relacionados às triggers dos problemas.
4. Classifica os incidentes por severidade, equipamento e host.
5. Exporta os dados em três formatos para a pasta reports.

O arquivo é executado diretamente pelo Python e, por isso, mantém algumas
operações no nível principal do script em vez de separar tudo em classes.
"""

import argparse
import os
import re
import requests
import pandas as pd

from collections import Counter
from datetime import datetime, timedelta
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

# Tempo máximo, em segundos, que cada chamada HTTP pode ficar aguardando o
# Zabbix responder. Isso evita que o script trave indefinidamente.
REQUEST_TIMEOUT = 60

# ==================================================
# DEFINIR CAMINHOS DO PROJETO
# ==================================================

# BASE_DIR sempre aponta para a pasta onde este arquivo está. Isso permite
# executar o script a partir de outros diretórios sem quebrar os caminhos.
BASE_DIR = Path(__file__).resolve().parent

# Arquivos e pastas usados pelo relatório. Mantê-los centralizados facilita
# mudar a estrutura do projeto no futuro.
ENV_FILE = BASE_DIR / ".env"
TEMPLATES_DIR = BASE_DIR / "templates"
REPORTS_DIR = BASE_DIR / "reports"

# ==================================================
# LER ARGUMENTOS DO TERMINAL
# ==================================================

# argparse permite configurar o relatório sem editar o código. Por padrão,
# mantemos 7 dias para preservar o comportamento original do script.
parser = argparse.ArgumentParser(
    description="Gera relatórios de incidentes do Zabbix."
)
parser.add_argument(
    "--dias",
    type=int,
    default=None,
    help="Quantidade de dias que serão pesquisados. Mantido por compatibilidade."
)
parser.add_argument(
    "--periodo",
    default="7d",
    help="Intervalo pesquisado. Exemplos: 24h, 2d, 5d, 7d, 30d. Padrão: 7d."
)
args = parser.parse_args()

if args.dias is not None and args.dias <= 0:
    print("ERRO: o argumento --dias precisa ser maior que zero.")
    raise SystemExit(1)


def parse_period(value):
    """
    Converte textos como 24h, 2d e 7d em um timedelta.

    Isso permite alternar rapidamente entre últimas 24 horas, 2 dias, 5 dias e
    outros intervalos sem editar o código.
    """

    normalized = str(value).strip().lower()

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

# ==================================================
# CARREGAR VARIÁVEIS DO .ENV
# ==================================================

# load_dotenv() lê o arquivo .env
# e carrega as variáveis para dentro do Python. Fazemos isso depois do argparse
# para que --help funcione mesmo quando o .env ainda não foi configurado.
load_dotenv(ENV_FILE)

# os.getenv() pega os valores do .env
ZABBIX_URL = os.getenv("ZABBIX_URL")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN")

# ==================================================
# VALIDAR VARIÁVEIS
# ==================================================

if not ZABBIX_URL or not ZABBIX_TOKEN:
    print("ERRO: Variáveis do .env não encontradas.")
    raise SystemExit(1)

# ==================================================
# DEFINIR PERÍODO DO RELATÓRIO
# ==================================================

# today é a data/hora final do relatório e também é usada no nome dos arquivos.
today = datetime.now()

# --dias continua funcionando, mas --periodo é mais flexível para 24h, 2d, 5d.
if args.dias is not None:
    period_delta = timedelta(days=args.dias)
    period_name = f"últimos {args.dias} dia(s)"
    period_slug = f"{args.dias}d"
else:
    period_delta, period_name = parse_period(args.periodo)
    period_slug = str(args.periodo).strip().lower()

# Volta no tempo conforme o intervalo informado no terminal.
start_week = today - period_delta

# timestamp = formato UNIX utilizado pelo Zabbix
# A API do Zabbix espera time_from e time_till como timestamps UNIX em segundos.
time_from = int(start_week.timestamp())
time_till = int(today.timestamp())

# ==================================================
# CABEÇALHO HTTP
# ==================================================

# Todas as chamadas para a API usam JSON-RPC, então o mesmo cabeçalho pode ser
# reaproveitado nas requisições de problemas e triggers.
headers = {
    "Content-Type": "application/json-rpc"
}

# ==================================================
# FUNÇÃO AUXILIAR PARA CHAMAR A API
# ==================================================

def call_zabbix_api(payload, error_context):
    """
    Envia um payload JSON-RPC para o Zabbix e devolve o JSON validado.

    Esta função concentra timeout, erros de conexão, validação HTTP, conversão
    JSON e erro retornado pela API. Assim, as chamadas problem.get e trigger.get
    seguem o mesmo padrão de segurança.
    """

    try:
        response = requests.post(
            ZABBIX_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

    except requests.exceptions.ConnectionError:
        print(f"ERRO: não foi possível conectar ao Zabbix ({error_context}).")
        raise SystemExit(1)

    except requests.exceptions.Timeout:
        print(f"ERRO: tempo de conexão excedido ({error_context}).")
        raise SystemExit(1)

    except requests.exceptions.RequestException as error:
        print(f"ERRO: falha na requisição ao Zabbix ({error_context}).")
        print(error)
        raise SystemExit(1)

    # Erros HTTP indicam falha na camada web antes da resposta JSON-RPC, como
    # URL inválida, indisponibilidade do servidor ou bloqueio de rede.
    if response.status_code != 200:
        print(f"Erro HTTP em {error_context}: {response.status_code}")
        print(response.text)
        raise SystemExit(1)

    try:
        data = response.json()

    except ValueError:
        print(f"ERRO: resposta JSON inválida em {error_context}.")
        print(response.text)
        raise SystemExit(1)

    if "error" in data:
        print(f"Erro retornado pela API Zabbix em {error_context}:")
        print(data["error"])
        raise SystemExit(1)

    return data

# ==================================================
# PAYLOAD DA API ZABBIX
# ==================================================

# event.get busca eventos concretos no intervalo escolhido. Usamos source=0,
# object=0 e value=1 para coletar eventos de problema gerados por triggers.
payload = {
    "jsonrpc": "2.0",
    "method": "event.get",

    "params": {

        # Busca somente os campos usados no relatório. Isso torna a consulta
        # mais leve sem perder os dados concretos necessários.
        "output": [
            "eventid",
            "clock",
            "name",
            "severity",
            "objectid",
            "r_eventid"
        ],

        # source 0/object 0 = eventos de trigger; value 1 = evento de problema
        "source": 0,
        "object": 0,
        "value": 1,

        # ordenação
        "sortfield": ["clock", "eventid"],
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

# Envia a requisição principal para obter os problemas e já recebe a resposta
# convertida em dicionário Python, validada pela função auxiliar.
data = call_zabbix_api(payload, "buscar eventos de problema")

# ==================================================
# BUSCAR HOSTS DOS PROBLEMAS
# ==================================================

problems = data.get("result", [])

# Eventos resolvidos trazem r_eventid. Coletamos esses IDs para buscar a data de
# recuperação e deixar claro quando o incidente já foi encerrado.
recovery_event_ids = sorted({
    item.get("r_eventid")
    for item in problems
    if item.get("r_eventid") and item.get("r_eventid") != "0"
})
resolved_at_by_event = {}

if recovery_event_ids:

    recovery_payload = {
        "jsonrpc": "2.0",
        "method": "event.get",

        "params": {
            "output": ["eventid", "clock"],
            "eventids": recovery_event_ids
        },

        "auth": ZABBIX_TOKEN,

        "id": 2
    }

    recovery_data = call_zabbix_api(
        recovery_payload,
        "buscar datas de resolução"
    )

    for event in recovery_data.get("result", []):
        resolved_at_by_event[event["eventid"]] = datetime.fromtimestamp(
            int(event["clock"])
        ).strftime("%d/%m/%Y %H:%M")

# Cada problema aponta para uma trigger pelo campo objectid. Reunimos todos os
# IDs únicos para fazer uma segunda consulta e descobrir o host de cada trigger.
trigger_ids = sorted({
    item.get("objectid")
    for item in problems
    if item.get("objectid")
})

# Dicionários preenchidos no formato:
# {triggerid: hostid} e {hostid: detalhes_do_host}
hosts_by_trigger = {}
host_ids_by_trigger = {}
host_details_by_id = {}

if trigger_ids:

    # trigger.get com selectHosts é necessário porque problem.get não traz
    # diretamente o nome do host em todos os retornos.
    trigger_payload = {
        "jsonrpc": "2.0",
        "method": "trigger.get",

        "params": {
            "output": ["triggerid"],
            "triggerids": trigger_ids,
            "selectHosts": ["hostid", "host", "name"]
        },

        "auth": ZABBIX_TOKEN,

        "id": 3
    }

    # A consulta de hosts também usa a função auxiliar, pois sem host o
    # relatório perde uma de suas colunas principais.
    trigger_data = call_zabbix_api(trigger_payload, "buscar hosts das triggers")

    for trigger in trigger_data.get("result", []):
        hosts = trigger.get("hosts", [])

        if hosts:
            # Quando uma trigger possui mais de um host, usamos o primeiro para
            # manter o relatório simples e compatível com a coluna única "host".
            host = hosts[0]
            hosts_by_trigger[trigger["triggerid"]] = host.get(
                "host",
                "N/A"
            )
            host_ids_by_trigger[trigger["triggerid"]] = host.get("hostid")

    host_ids = sorted({
        hostid
        for hostid in host_ids_by_trigger.values()
        if hostid
    })

    if host_ids:

        # host.get busca as tags dos hosts. A tag "unidade" é a fonte oficial
        # para descobrir o código escolar, por exemplo unidade=1011.
        host_payload = {
            "jsonrpc": "2.0",
            "method": "host.get",

            "params": {
                "output": ["hostid", "host", "name"],
                "hostids": host_ids,
                "selectTags": ["tag", "value"]
            },

            "auth": ZABBIX_TOKEN,

            "id": 4
        }

        host_data = call_zabbix_api(host_payload, "buscar tags unidade")

        for host in host_data.get("result", []):
            host_details_by_id[host["hostid"]] = host

# ==================================================
# BUSCAR CATÁLOGO DE UNIDADES POR TAG
# ==================================================

# Esta consulta pega todos os hosts com suas tags para montar o catálogo oficial
# código -> unidade. Assim, o nome da unidade não depende de ter ocorrido
# incidente no host principal da escola dentro do período analisado.
all_hosts_payload = {
    "jsonrpc": "2.0",
    "method": "host.get",

    "params": {
        "output": ["hostid", "host", "name"],
        "selectTags": ["tag", "value"]
    },

    "auth": ZABBIX_TOKEN,

    "id": 5
}

all_hosts_data = call_zabbix_api(all_hosts_payload, "buscar catálogo de unidades")
all_host_details_by_id = {
    host["hostid"]: host
    for host in all_hosts_data.get("result", [])
}

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
    """
    Classifica o tipo de equipamento a partir do nome do host.

    O Zabbix normalmente guarda padrões nos nomes dos hosts, como "sw",
    "camera" ou "mikrotik". Esta função usa esses padrões para criar uma coluna
    de categoria no relatório sem depender de cadastro adicional.
    """

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


def extract_school_unit(host):
    """
    Extrai a unidade escolar a partir do nome do host.

    O padrão observado nos hosts começa com um código de 4 dígitos. Quando o
    nome termina com uma localidade real, como "Brotas", o relatório mostra
    "1011-Brotas". Quando o host só possui LOCAL_X ou nome técnico, mantemos o
    código como identificador da unidade.
    """

    text = str(host or "").strip()
    match = re.match(r"^(\d{4})", text)

    if not match:
        return "Unidade não identificada"

    code = match.group(1)
    parts = [
        part.strip()
        for part in text.split("-")
        if part.strip()
    ]

    ignored = {
        "CAM",
        "CAMERA",
        "LOCAL_X",
        "MKT",
        "MK",
        "NVR",
        "SW",
        "SWITCH",
        "TERM_FACIAL",
        "HUMOR",
    }

    for part in reversed(parts[1:]):
        normalized = part.upper().replace(" ", "_")

        if (
            normalized in ignored
            or normalized.startswith("TIPO_")
            or "_" in normalized
        ):
            continue

        if re.search(r"[A-Za-zÀ-ÿ]", part):
            return f"{code}-{part}"

    return code


def extract_unit_code(host):
    """
    Retorna apenas o código de 4 dígitos da unidade, quando existir.

    Esse código permite juntar hosts técnicos da mesma unidade com o nome
    completo descoberto em outro host, por exemplo câmeras 1011_* com
    1011-Brotas.
    """

    match = re.match(r"^(\d{4})", str(host or "").strip())

    return match.group(1) if match else ""


def get_unit_tag_value(host):
    """
    Lê a tag oficial unidade de um host retornado pelo Zabbix.

    A comparação é case-insensitive para aceitar "unidade", "Unidade" ou outras
    variações de capitalização, mas o valor precisa estar no padrão numérico.
    """

    for tag in host.get("tags", []):
        if str(tag.get("tag", "")).strip().lower() == "unidade":
            value = str(tag.get("value", "")).strip()

            if re.fullmatch(r"\d{4}", value):
                return value

    return ""


def clean_unit_name(host_name, unit_code):
    """
    Remove prefixos técnicos para transformar um host em nome de unidade.

    Exemplo: "1011-MKT CE Luiz Viana - Brotas" vira
    "1011-CE Luiz Viana - Brotas".
    """

    text = str(host_name or "").strip()
    text = re.sub(rf"^{unit_code}\s*[-_]\s*", "", text)
    text = re.sub(
        r"^(MKT|MK|ROTEADOR|ROUTER|FIREWALL)\s+",
        "",
        text,
        flags=re.IGNORECASE
    )

    if text:
        return f"{unit_code}-{text}"

    return unit_code


def score_unit_name_candidate(host_name):
    """
    Pontua hosts candidatos a nome oficial da unidade.

    Hosts de câmera, switch e NVR costumam ser equipamentos; nomes com MKT ou
    termos escolares tendem a carregar o nome real da escola.
    """

    text = str(host_name or "")
    upper = text.upper()
    score = 0

    if any(word in upper for word in ["MKT", "CE ", "CETI", "ESCOLA", "COLEGIO"]):
        score += 20

    if " - " in text:
        score += 8

    if any(word in upper for word in ["CAM", "SWITCH", "NVR", "TERM_FACIAL"]):
        score -= 15

    if "LOCAL_X" in upper:
        score -= 10

    return score


def build_unit_catalog(host_details):
    """
    Monta o catálogo código -> nome da unidade usando tags do Zabbix.

    O intervalo 1011-1169 cobre as 159 unidades esperadas. Quando existe uma
    tag unidade no host, ela prevalece sobre qualquer tentativa de deduzir pelo
    nome.
    """

    candidates_by_code = {}

    for host in host_details.values():
        unit_code = get_unit_tag_value(host)

        if not unit_code or not 1011 <= int(unit_code) <= 1169:
            continue

        display_name = host.get("name") or host.get("host") or unit_code
        candidates_by_code.setdefault(unit_code, []).append(display_name)

    catalog = {}

    for code, candidates in candidates_by_code.items():
        best_name = max(candidates, key=score_unit_name_candidate)
        catalog[code] = clean_unit_name(best_name, code)

    return catalog


# ==================================================
# GERAR PDF
# ==================================================

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

    # Counter conta quantas vezes cada categoria aparece na lista de incidentes.
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

    def format_counter(counter):
        """
        Converte um Counter em lista de dicionários com total e percentual.

        O formato em lista é mais simples de percorrer no template HTML e no PDF.
        """
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
        "equipment": format_counter(equipment_counter),
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
        ("Abertos", summary["open"]),
        ("Resolvidos", summary["resolved"]),
        ("Desastres", summary["critical"]),
        ("Altas", summary["high"]),
        ("Medias", summary["medium"]),
        ("Atencao", summary["attention"]),
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

# ==================================================
# LISTA DE INCIDENTES
# ==================================================

incidents = []
unit_catalog = build_unit_catalog(all_host_details_by_id)

print("Processando incidentes...")

# percorre cada problema retornado pela API
for item in problems:

    # pega o nome do host
    host = hosts_by_trigger.get(item.get("objectid"), "N/A")
    host_id = host_ids_by_trigger.get(item.get("objectid"))
    host_details = host_details_by_id.get(host_id, {})

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

    # r_eventid indica o evento de recuperação. Quando não existe ou vem "0",
    # o incidente ainda está aberto no Zabbix.
    recovery_eventid = item.get("r_eventid")
    resolved_at = resolved_at_by_event.get(recovery_eventid, "")
    status = "Resolvido" if resolved_at else "Aberto"

    # classificação automática
    equipment = classify_equipment(host)

    # unidade escolar usada para particionar e filtrar o relatório. A tag
    # unidade do Zabbix é a fonte principal; dedução pelo nome fica como fallback.
    unit_code = get_unit_tag_value(host_details) or extract_unit_code(host)
    unit = unit_catalog.get(unit_code, extract_school_unit(host))

    # adiciona na lista
    # Cada dicionário representa uma linha do relatório em Excel, HTML e PDF.
    incidents.append({
        "host": host,
        "unit_code": unit_code,
        "unit": unit,
        "equipment": equipment,
        "incident": incident,
        "severity": severity,
        "status": status,
        "date": date,
        "resolved_at": resolved_at,
        "eventid": eventid
    })

# ==================================================
# DATAFRAME PANDAS
# ==================================================

# transforma lista em tabela
# O DataFrame facilita exportar para Excel usando a integração do pandas.
df = pd.DataFrame(incidents)

# monta indicadores para apresentacao
# summary alimenta os indicadores do HTML e da primeira página do PDF.
summary = build_report_summary(incidents)

# period_label é uma versão legível do intervalo de datas pesquisado no Zabbix.
period_label = (
    f"{period_name}: {start_week.strftime('%d/%m/%Y %H:%M')} a "
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

# O nome do arquivo usa a data atual para sobrescrever apenas o relatório do
# mesmo dia e facilitar localizar os relatórios gerados.
excel_name = (
    REPORTS_DIR /
    f"report_{today.strftime('%Y-%m-%d')}_{period_slug}.xlsx"
)

# salva excel
df.to_excel(excel_name, index=False)

print(f"Excel gerado: {excel_name}")

# ==================================================
# GERAR HTML
# ==================================================

# carrega pasta templates
# O Jinja2 separa apresentação (HTML) dos dados processados neste script.
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

# carrega template HTML
template = env.get_template(
    "report_template.html"
)

# renderiza HTML com os dados
# O template recebe os incidentes e o resumo já prontos para exibição.
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
    f"report_{today.strftime('%Y-%m-%d')}_{period_slug}.html"
)

# escreve arquivo HTML
with open(html_name, "w", encoding="utf-8") as f:
    f.write(html_output)

print(f"HTML gerado: {html_name}")

# ==================================================
# GERAR PDF
# ==================================================

# nome do arquivo
# O PDF recebe o mesmo padrão de nome dos arquivos Excel e HTML.
pdf_name = (
    REPORTS_DIR /
    f"report_{today.strftime('%Y-%m-%d')}_{period_slug}.pdf"
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
print(f"Periodo: {period_label}")
print(f"Total de incidentes: {len(df)}")
print(f"Abertos: {summary['open']}")
print(f"Resolvidos: {summary['resolved']}")
print(f"Excel: {excel_name}")
print(f"HTML: {html_name}")
print(f"PDF: {pdf_name}")
