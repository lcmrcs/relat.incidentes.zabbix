#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==============================================="
echo "Central de Relatorios Zabbix"
echo "==============================================="
echo

if [ ! -x "zabbix-report/venv/bin/python" ]; then
    echo "Ambiente virtual nao encontrado. Criando venv..."
    python3 -m venv "zabbix-report/venv"
fi

source "zabbix-report/venv/bin/activate"

echo "Instalando ou atualizando dependencias..."
python -m pip install -r "zabbix-report/requirements.txt"

echo
echo "Abrindo tela local no navegador..."
python "zabbix-report/report_launcher.py"
