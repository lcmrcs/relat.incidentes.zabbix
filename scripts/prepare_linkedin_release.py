"""
Prepara uma versão pública do relatório para publicação no LinkedIn.

O script parte do HTML executivo mais recente, mascara dados sensíveis e gera
prints do relatório sanitizado. A intenção é divulgar o projeto sem expor IPs,
nomes internos, hosts, URLs privadas ou números operacionais sensíveis.
"""

from __future__ import annotations

import re
import os
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "zabbix-report" / "reports"
OUTPUT_ROOT = ROOT / "entrega_supervisor" / "linkedin_sanitizado"


LINKEDIN_TEXT = """Estou evoluindo este projeto de automação de relatórios com foco em monitoramento, infraestrutura e análise executiva de incidentes.

A solução consulta dados do Zabbix, organiza os incidentes por unidade, equipamento, severidade, tempo offline e recorrência, e transforma essas informações em um relatório HTML interativo, com exportação para Excel e PDF.

Nesta atualização, avancei principalmente em três pontos:

- visual mais executivo e limpo;
- mapa de criticidade por unidade, com score operacional;
- rankings mais úteis para priorização, como passivo mais antigo, severidade alta, equipamentos afetados e tipos de incidente recorrentes.

Também sigo cuidando da segurança do projeto, usando variáveis de ambiente, dados sanitizados para divulgação pública e validações antes de publicar alterações no repositório.

É um projeto em desenvolvimento contínuo, e tem sido uma experiência muito importante para minha evolução como programador: estou aplicando Python, automação, análise de dados e frontend em um problema real de operação e monitoramento.

Tecnologias utilizadas:
Python, Zabbix API, HTML, CSS, JavaScript, Jinja2, Pandas, OpenPyXL, python-dotenv, Git, GitHub e GitHub Actions.

Repositório:
https://github.com/lcmrcs/relat.incidentes.zabbix
"""


def latest_report() -> Path:
    reports = sorted(REPORTS_DIR.glob("report_*_historico_abertos.html"))

    if not reports:
        raise FileNotFoundError("Nenhum HTML de relatório foi encontrado em zabbix-report/reports.")

    return reports[-1]


def collect_values(text: str, patterns: list[str]) -> list[str]:
    values: list[str] = []
    seen = set()

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = match.group(1).strip()

            if value and value not in seen:
                seen.add(value)
                values.append(value)

    return values


def apply_mapping(text: str, values: list[str], prefix: str) -> str:
    mapping = {
        value: f"{prefix} {index:03d}"
        for index, value in enumerate(values, start=1)
    }

    for original, replacement in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(original, replacement)

    return text


def soften_age_labels(text: str) -> str:
    day_cycle = [2, 3, 4, 5, 7, 9, 11, 14, 18]

    def repl(match: re.Match[str]) -> str:
        original_days = int(match.group(1))
        original_hours = int(match.group(2))
        day = day_cycle[original_days % len(day_cycle)]
        hour = original_hours % 12
        return f"{day}d {hour}h"

    text = re.sub(r"\b(\d{2,4})d\s+(\d{1,2})h\b", repl, text)

    def repl_minutes(match: re.Match[str]) -> str:
        original_hours = int(match.group(1))
        original_minutes = int(match.group(2))
        hour = max(1, original_hours % 8)
        minute = original_minutes % 60
        return f"{hour}h {minute}min"

    return re.sub(r"\b(\d{2,4})h\s+(\d{1,2})min\b", repl_minutes, text)


def inject_public_badge(text: str) -> str:
    css = """
    <style>
        .linkedin-public-badge {
            position: fixed;
            right: 18px;
            bottom: 18px;
            z-index: 9999;
            border: 1px solid rgb(32 196 205 / 0.34);
            border-radius: 999px;
            background: rgb(5 31 38 / 0.82);
            color: #eaffff;
            font: 800 12px/1.2 Arial, sans-serif;
            letter-spacing: 0;
            padding: 10px 14px;
            box-shadow: 0 18px 34px rgb(0 0 0 / 0.20);
            backdrop-filter: blur(12px);
        }

        @media print {
            .linkedin-public-badge {
                display: none;
            }
        }
    </style>
    """
    badge = '<div class="linkedin-public-badge">Demonstração pública · dados sanitizados</div>'

    if "</head>" in text:
        text = text.replace("</head>", f"{css}\n</head>", 1)

    if "</body>" in text:
        text = text.replace("</body>", f"{badge}\n</body>", 1)

    return text


def sanitize_html(html: str) -> str:
    text = html

    unit_values = collect_values(text, [
        r'data-unit="([^"]+)"',
        r'data-quick-unit="([^"]+)"',
        r'<td class="table-unit">([^<]+)</td>',
        r'title="((?:10|11)\d{2}-[^"]+)"',
        r'<span class="metric-name"[^>]*>((?:10|11)\d{2}[^<]+)</span>',
        r'<strong title="((?:10|11)\d{2}[^"]+)">',
        r'<span>((?:10|11)\d{2}-(?:CE|CETI|CPM|CTEP|CEEP)[^<]+)</span>',
    ])
    host_values = collect_values(text, [
        r'data-host="([^"]+)"',
        r'data-quick-search="([^"]+)"',
        r'<td class="table-host">([^<]+)</td>',
        r'<td class="modal-host">([^<]+)</td>',
        r'<strong>((?:CFH|[0-9]{4})[^<]{4,80})</strong>',
        r'<span class="metric-name"[^>]*>((?:CFH|[0-9]{4})[^<]{4,80})</span>',
    ])

    # URLs privadas e links diretos para o Zabbix.
    text = re.sub(r"https?://[^\"'\\s<>)]+", "https://zabbix.exemplo.local/evento", text)

    # IPs internos e públicos no corpo do relatório.
    text = re.sub(
        r"\b(?:(?:10|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b",
        "10.x.x.x",
        text,
    )

    # Nomes de unidades e hosts aparecem em atributos, filtros, tabelas e
    # modais. A substituição global preserva consistência entre os componentes.
    text = apply_mapping(text, host_values, "HOST-DEMO")
    text = apply_mapping(text, unit_values, "Unidade Escolar")

    # Hosts citados dentro do texto do incidente nem sempre aparecem como
    # coluna/atributo separado, então recebem uma máscara adicional.
    text = re.sub(
        r"\b(?:10|11)\d{2}[_-]\d{1,3}-(?:CAM|TERM_FACIAL|SWITCH|CENTRAL|NVR)[^<\"']*",
        "HOST-DEMO",
        text,
    )
    text = re.sub(r"\b(?:10|11)\d{2}-MKT[^<\"']*", "HOST-DEMO", text)
    text = re.sub(r"Unidade Escolar \d{3}-MKT[^<\"']*", "HOST-DEMO", text)
    text = re.sub(r"\bCFH\d{3}-[A-Z0-9_-]+(?:\s*-\s*[A-Z0-9_-]+)?", "HOST-DEMO-CONFEA", text)
    text = text.replace("0000-SRV Zabbix server", "Servidor Zabbix demo")
    text = text.replace("LOCAL_X", "LOCAL_DEMO")

    # Reduz exposição de códigos reais de unidades sem quebrar o layout.
    text = re.sub(r'data-unit-code="\d{4}"', 'data-unit-code="0000"', text)
    text = re.sub(r">\d{4}</td>", ">0000</td>", text)

    # IDs e eventos não precisam ser reais em material público.
    text = re.sub(r"\b7\d{6,9}\b", "7000000", text)
    text = re.sub(r"\b8\d{6,9}\b", "8000000", text)

    # Para divulgação, reduz dias/horas muito altos sem alterar a estrutura.
    text = soften_age_labels(text)

    text = text.replace("Relatório Executivo de Incidentes Zabbix", "Relatório Executivo de Incidentes Zabbix · Demo")
    return inject_public_badge(text)


def screenshot_with_playwright(html_path: Path, output_dir: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright

    temp_dir = Path("/tmp") / "zabbix-linkedin-playwright"
    temp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(temp_dir)
    os.environ["TMP"] = str(temp_dir)
    os.environ["TEMP"] = str(temp_dir)
    os.environ["PLAYWRIGHT_ARTIFACTS_PATH"] = str(temp_dir)

    shots = [
        ("01_visao_geral.png", "main"),
        ("02_inteligencia_operacional.png", ".executive-intelligence"),
        ("03_mapa_criticidade.png", ".unit-criticality-map"),
        ("04_filtro_relatorio.png", ".filter-panel"),
    ]
    created: list[Path] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.evaluate("localStorage.clear(); document.body.classList.add('theme-dark');")
        page.wait_for_timeout(600)

        for filename, selector in shots:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            path = output_dir / filename
            locator.screenshot(path=str(path))
            created.append(path)

        details = page.locator(".details-button").first
        if details.count():
            details.click()
            page.wait_for_timeout(400)
            dialog = page.locator("dialog[open], .incident-modal").first
            if dialog.count():
                path = output_dir / "05_detalhes_incidente.png"
                dialog.screenshot(path=str(path))
                created.append(path)

        browser.close()

    return created


def main() -> None:
    source = latest_report()
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUT_ROOT / f"post_{today}"
    images_dir = output_dir / "imagens"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    sanitized_html = sanitize_html(source.read_text(encoding="utf-8"))
    html_path = output_dir / "relatorio_publico_linkedin.html"
    text_path = output_dir / "texto_linkedin.md"
    html_path.write_text(sanitized_html, encoding="utf-8")
    text_path.write_text(LINKEDIN_TEXT, encoding="utf-8")

    screenshots: list[Path] = []

    try:
        screenshots = screenshot_with_playwright(html_path, images_dir)
    except Exception as exc:  # pragma: no cover - depende do navegador local.
        (output_dir / "AVISO_PRINTS.txt").write_text(
            "O HTML sanitizado foi gerado, mas os prints automaticos falharam.\n"
            f"Motivo: {exc}\n"
            "Abra o HTML no navegador e capture as imagens manualmente.\n",
            encoding="utf-8",
        )

    print(f"HTML sanitizado: {html_path}")
    print(f"Texto LinkedIn: {text_path}")
    print(f"Pasta de imagens: {images_dir}")

    if screenshots:
        print("Prints gerados:")
        for path in screenshots:
            print(f"- {path}")
    else:
        print("Prints automaticos nao foram gerados.")


if __name__ == "__main__":
    main()
