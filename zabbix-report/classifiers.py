"""
Regras de classificação usadas pelo relatório Zabbix.

Este módulo concentra traduções e regras de negócio que não dependem de rede,
Excel, HTML ou PDF. Isso facilita manter nomes de equipamento, severidade e
agrupamentos especiais sem mexer no fluxo principal do relatório.
"""

import re


SEVERITY_MAP = {
    "0": "Não classificada",
    "1": "Informação",
    "2": "Atenção",
    "3": "Média",
    "4": "Alta",
    "5": "Desastre",
}


EQUIPMENT_ORDER = [
    "Mikrotik",
    "Switch",
    "NVR",
    "Central de Alarme",
    "Terminal Facial",
    "Portal Detector de Metal",
    "Câmera",
]


def classify_equipment(host):
    """
    Classifica o tipo de equipamento a partir do nome do host.

    O Zabbix normalmente guarda padrões nos nomes dos hosts, como "sw",
    "camera" ou "mikrotik". Esta função usa esses padrões para criar uma coluna
    de categoria no relatório sem depender de cadastro adicional.
    """

    host = str(host or "").lower()

    if "zabbix" in host and any(x in host for x in ["srv", "server"]):
        return "Servidor Zabbix"

    if any(x in host for x in ["portal", "metal"]):
        return "Portal Detector de Metal"

    if any(x in host for x in ["srv", "server", "sp-hw-win", "cadgis", "cadweb"]):
        return "Servidor"

    if any(x in host for x in ["mikrotik", "mk"]):
        return "Mikrotik"

    if any(x in host for x in ["switch", "sw"]):
        return "Switch"

    if "nvr" in host:
        return "NVR"

    if any(x in host for x in ["camera", "cam"]):
        return "Câmera"

    if "facial" in host:
        return "Terminal Facial"

    if "alarme" in host:
        return "Central de Alarme"

    return "Diversos"


def classify_incident_type(incident):
    """
    Consolida nomes técnicos do Zabbix em famílias de incidente.

    Algumas triggers carregam IP, interface, host ou texto específico da
    unidade. Esta classificação remove esse ruído para que o ranking mostre o
    tipo real do problema, sem fragmentar o mesmo sintoma em várias linhas.
    """

    text = str(incident or "").strip()
    normalized = text.lower()

    if not text:
        return "Não informado"

    if "no snmp data collection" in normalized:
        return "No SNMP data collection"

    if any(term in normalized for term in [
        "unavailable by icmp ping",
        "indisponível por ping icmp",
        "indisponivel por ping icmp",
        "indisponível (sem resposta ao ping)",
        "indisponivel (sem resposta ao ping)",
    ]):
        return "Unavailable by ICMP ping"

    if any(term in normalized for term in [
        "high icmp ping loss",
        "alta perda de pacotes",
        "perda de pacotes",
    ]):
        return "High ICMP ping loss"

    if any(term in normalized for term in [
        "high icmp ping response time",
        "icmp ping response time",
        "tempo de resposta icmp",
    ]):
        return "High ICMP ping response time"

    if any(term in normalized for term in [
        "temperature is above warning threshold",
        "temperatura",
    ]):
        return "Temperature above threshold"

    if "high bandwidth usage" in normalized:
        return "High bandwidth usage"

    if any(term in normalized for term in [
        "ethernet has changed to lower speed",
        "lower speed",
    ]):
        return "Ethernet lower speed"

    if any(term in normalized for term in [
        "link down",
        "operational status down",
    ]):
        return "Interface down"

    return text


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
        return "Infraestrutura"

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

    if code == "0000":
        return "Zabbix Server"

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


def classify_unit_group(host, host_details, unit_catalog):
    """
    Define o agrupamento exibido na coluna Unidade.

    Escolas usam a tag unidade do Zabbix. O host 0000-SRV Zabbix server e as VMs
    da CONFEA monitoradas por VPN ficam em cantos especiais, porque não
    representam unidade escolar.
    """

    unit_code = get_unit_tag_value(host_details) or extract_unit_code(host)
    normalized_host = str(host or "").lower()

    if unit_code == "0000":
        return "ZBX", "Zabbix Server"

    if "sp-hw-win" in normalized_host and (
        "cfh" in normalized_host or "cad" in normalized_host
    ):
        return "CONFEA", "CONFEA VPN"

    if not unit_code:
        return "INFRA", "Infraestrutura"

    return unit_code, unit_catalog.get(unit_code, extract_school_unit(host))


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
        flags=re.IGNORECASE,
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
        if code == "0000":
            catalog[code] = "Zabbix Server"
            continue

        best_name = max(candidates, key=score_unit_name_candidate)
        catalog[code] = clean_unit_name(best_name, code)

    return catalog
