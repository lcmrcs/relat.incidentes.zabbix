"""
Gera relatórios de incidentes do Zabbix em Excel, HTML e PDF.

Este arquivo agora funciona como coordenador do fluxo. As regras de
classificação, acesso ao Zabbix, cálculo de indicadores e geração do PDF ficam
em módulos separados para facilitar leitura, manutenção e testes.
"""

import argparse
import os

import pandas as pd

from datetime import datetime, timedelta
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
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
REPORTS_DIR = BASE_DIR / "reports"


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

    args = parser.parse_args()

    if args.dias is not None and args.dias <= 0:
        print("ERRO: o argumento --dias precisa ser maior que zero.")
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


# ==================================================
# EXPORTAÇÃO
# ==================================================

def export_excel(path, all_incidents, main_incidents, zabbix_incidents, confea_incidents):
    """
    Gera a planilha Excel com abas separadas por finalidade.

    A aba Unidades é a visão escolar. As abas Servidor Zabbix e CONFEA VPN
    isolam infraestrutura especial. A aba Todos preserva a visão completa.
    """

    with pd.ExcelWriter(path) as writer:
        pd.DataFrame(main_incidents).to_excel(
            writer,
            sheet_name="Unidades",
            index=False,
        )

        if zabbix_incidents:
            pd.DataFrame(zabbix_incidents).to_excel(
                writer,
                sheet_name="Servidor Zabbix",
                index=False,
            )

        if confea_incidents:
            pd.DataFrame(confea_incidents).to_excel(
                writer,
                sheet_name="CONFEA VPN",
                index=False,
            )

        pd.DataFrame(all_incidents).to_excel(
            writer,
            sheet_name="Todos",
            index=False,
        )


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
        incidents,
        main_incidents,
        zabbix_incidents,
        confea_incidents,
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
