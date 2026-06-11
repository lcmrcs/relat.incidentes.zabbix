import os
import requests

from dotenv import load_dotenv

# ==========================================
# CARREGAR .ENV
# ==========================================

print("Carregando variáveis do .env...")

load_dotenv()

ZABBIX_URL = os.getenv("ZABBIX_URL")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN")

# ==========================================
# VALIDAR VARIÁVEIS
# ==========================================

if not ZABBIX_URL:
    print("ERRO: ZABBIX_URL não encontrada.")
    exit()

if not ZABBIX_TOKEN:
    print("ERRO: ZABBIX_TOKEN não encontrado.")
    exit()

print("Variáveis carregadas com sucesso.")
print()

# ==========================================
# HEADERS HTTP
# ==========================================

headers = {
    "Content-Type": "application/json-rpc"
}

# ==========================================
# PAYLOAD DE TESTE
# ==========================================

payload = {
    "jsonrpc": "2.0",

    # host.get busca hosts cadastrados
    "method": "host.get",

    "params": {

        # quais campos retornar
        "output": [
            "host",
            "name",
            "status"
        ],

        # limitar em 5 hosts
        "limit": 5
    },

    # token da API
    "auth": ZABBIX_TOKEN,

    "id": 1
}

print("Conectando ao Zabbix...")
print()

# ==========================================
# REQUISIÇÃO HTTP
# ==========================================

try:

    response = requests.post(
        ZABBIX_URL,
        json=payload,
        headers=headers,
        timeout=15
    )

except requests.exceptions.ConnectionError:
    print("ERRO: Não foi possível conectar ao servidor.")
    exit()

except requests.exceptions.Timeout:
    print("ERRO: Tempo de conexão excedido.")
    exit()

# ==========================================
# VALIDAR STATUS HTTP
# ==========================================

print(f"HTTP Status: {response.status_code}")
print()

if response.status_code != 200:

    print("ERRO HTTP")
    print(response.text)

    exit()

# ==========================================
# CONVERTER RESPOSTA JSON
# ==========================================

try:

    data = response.json()

except Exception:

    print("ERRO: resposta inválida.")
    print(response.text)

    exit()

# ==========================================
# VALIDAR ERRO DA API
# ==========================================

if "error" in data:

    print("ERRO retornado pela API:")
    print()

    print(data["error"])

    exit()

# ==========================================
# PEGAR RESULTADO
# ==========================================

result = data.get("result", [])

# ==========================================
# EXIBIR RESULTADOS
# ==========================================

print("Conexão realizada com sucesso.")
print()

print(f"Hosts encontrados: {len(result)}")
print()

for index, host in enumerate(result, start=1):

    status = (
        "Habilitado"
        if host["status"] == "0"
        else "Desabilitado"
    )

    print(f"[{index}]")
    print(f"Host: {host['host']}")
    print(f"Nome: {host['name']}")
    print(f"Status: {status}")
    print("-" * 40)

print()
print("TESTE FINALIZADO COM SUCESSO")