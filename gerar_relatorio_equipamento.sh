#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==============================================="
echo "Relatorio Executivo de Incidentes Zabbix - Por Equipamento"
echo "==============================================="
echo

equipment="${1:-}"
if [ -z "$equipment" ]; then
    echo "Digite o equipamento que deseja filtrar."
    echo
    echo "Exemplos:"
    echo "- Terminal Facial"
    echo "- Câmera"
    echo "- Mikrotik"
    echo "- Switch"
    echo "- NVR"
    echo "- Central de Alarme"
    echo "- Portal Detector de Metal"
    echo
    read -r -p "Equipamento: " equipment
fi

if [ -z "$equipment" ]; then
    echo "ERRO: o equipamento nao pode ficar vazio."
    exit 1
fi

if [ ! -f "zabbix-report/.env" ]; then
    echo "ERRO: arquivo zabbix-report/.env nao encontrado."
    echo
    echo "Crie esse arquivo a partir de zabbix-report/.env.example"
    echo "e preencha ZABBIX_URL e ZABBIX_TOKEN."
    exit 1
fi

if [ ! -x "zabbix-report/venv/bin/python" ]; then
    echo "Ambiente virtual nao encontrado. Criando venv..."
    python3 -m venv "zabbix-report/venv"
fi

source "zabbix-report/venv/bin/activate"

echo "Instalando ou atualizando dependencias..."
python -m pip install -r "zabbix-report/requirements.txt"

echo
echo "Gerando relatorio exclusivo de: $equipment"
python "zabbix-report/zabbix_report.py" --periodo historico --status abertos --equipamento "$equipment"

last_html="$(
    {
        find zabbix-report/reports -maxdepth 1 -type f -name '*.html' -printf '%T@ %p\n' 2>/dev/null || true
    } | sort -nr | head -n 1 | cut -d' ' -f2-
)"

if [ -n "$last_html" ]; then
    echo
    echo "Abrindo relatorio: $last_html"

    if command -v cmd.exe >/dev/null 2>&1; then
        windows_path="$(wslpath -w "$last_html" 2>/dev/null || true)"
        if [ -n "$windows_path" ]; then
            cmd.exe /c start "" "$windows_path" >/dev/null 2>&1 || true
        fi
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$last_html" >/dev/null 2>&1 || true
    fi
else
    echo
    echo "Relatorio gerado, mas nenhum HTML foi encontrado."
    echo "Verifique a pasta zabbix-report/reports."
fi

echo
echo "Finalizado."
