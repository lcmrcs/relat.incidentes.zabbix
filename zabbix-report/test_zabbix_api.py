"""
Teste simples de conectividade com a API do Zabbix.

Este arquivo existe para validar rapidamente se o arquivo .env, o token da API
e a URL do Zabbix estão corretos antes de rodar o relatório completo em
zabbix_report.py. Ele faz uma chamada pequena, buscando até 5 hosts, e imprime
o resultado no terminal.
"""

import os
import requests

from dotenv import load_dotenv

# ==========================================
# CARREGAR .ENV
# ==========================================

print("Carregando variáveis do .env...")

# load_dotenv() procura um arquivo .env no diretório atual e disponibiliza
# as variáveis dentro de os.getenv(). Sem isso, o script não sabe a URL nem o
# token usados para autenticar no Zabbix.
load_dotenv()

# ZABBIX_URL deve apontar para o endpoint JSON-RPC da API do Zabbix.
# ZABBIX_TOKEN é o token de autenticação gerado no próprio Zabbix.
ZABBIX_URL = os.getenv("ZABBIX_URL")
ZABBIX_TOKEN = os.getenv("ZABBIX_TOKEN")

# ==========================================
# VALIDAR VARIÁVEIS
# ==========================================

# A validação para a execução cedo caso o .env esteja incompleto. Isso evita
# enviar uma requisição inválida e facilita identificar o problema real.
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

# A API do Zabbix usa JSON-RPC; por isso o Content-Type precisa indicar que o
# corpo da requisição será um JSON nesse formato.
headers = {
    "Content-Type": "application/json-rpc"
}

# ==========================================
# PAYLOAD DE TESTE
# ==========================================

# Payload é o corpo enviado para a API. Aqui usamos o método host.get porque é
# uma consulta leve e suficiente para confirmar que a conexão e o token estão
# funcionando.
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

    # requests.post() envia a consulta ao endpoint do Zabbix. O timeout evita
    # que o terminal fique preso indefinidamente se o servidor não responder.
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

# Status HTTP diferente de 200 significa que o problema aconteceu antes da
# resposta JSON-RPC ser processada, por exemplo URL errada, proxy, permissão ou
# erro no servidor web.
if response.status_code != 200:

    print("ERRO HTTP")
    print(response.text)

    exit()

# ==========================================
# CONVERTER RESPOSTA JSON
# ==========================================

try:

    # A API deve responder em JSON. Se isso falhar, normalmente a URL aponta
    # para uma página HTML, houve erro de servidor, ou a resposta veio truncada.
    data = response.json()

except Exception:

    print("ERRO: resposta inválida.")
    print(response.text)

    exit()

# ==========================================
# VALIDAR ERRO DA API
# ==========================================

# Mesmo com HTTP 200, a API JSON-RPC pode retornar uma chave "error" quando o
# método, token ou parâmetros estão incorretos.
if "error" in data:

    print("ERRO retornado pela API:")
    print()

    print(data["error"])

    exit()

# ==========================================
# PEGAR RESULTADO
# ==========================================

# "result" contém a lista de hosts retornada pelo método host.get. O padrão []
# evita erro caso a chave não exista por algum motivo.
result = data.get("result", [])

# ==========================================
# EXIBIR RESULTADOS
# ==========================================

print("Conexão realizada com sucesso.")
print()

print(f"Hosts encontrados: {len(result)}")
print()

# enumerate(..., start=1) numera os hosts de forma mais amigável no terminal.
for index, host in enumerate(result, start=1):

    # No Zabbix, status "0" indica host habilitado; outros valores indicam host
    # desabilitado. A tradução deixa a saída mais legível.
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
