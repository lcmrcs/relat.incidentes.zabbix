"""
Prepara uma versão pública do relatório para publicação no LinkedIn.

O script parte do HTML executivo mais recente, mascara dados sensíveis e gera
prints do relatório sanitizado. A intenção é divulgar o projeto sem expor IPs,
nomes internos, hosts, URLs privadas ou números operacionais sensíveis.
"""

from __future__ import annotations

import re
import os
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "zabbix-report" / "reports"
OUTPUT_ROOT = ROOT / "entrega_supervisor" / "linkedin_sanitizado"
WINDOWS_EDGE = Path("/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
WINDOWS_CHROME = Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe")


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
    day_cycle = [0, 1, 2, 3, 4, 5, 6]

    def repl(match: re.Match[str]) -> str:
        original_days = int(match.group(1))
        original_hours = int(match.group(2))
        day = day_cycle[original_days % len(day_cycle)]
        hour = original_hours % 8
        return f"{day}d {hour}h" if day else f"{hour}h"

    text = re.sub(r"\b(\d{2,4})d\s+(\d{1,2})h\b", repl, text)

    def repl_minutes(match: re.Match[str]) -> str:
        original_hours = int(match.group(1))
        original_minutes = int(match.group(2))
        hour = max(1, original_hours % 6)
        minute = original_minutes % 60
        return f"{hour}h {minute}min"

    return re.sub(r"\b(\d{2,4})h\s+(\d{1,2})min\b", repl_minutes, text)


def protect_blocks(text: str) -> tuple[str, dict[str, str]]:
    """
    Protege blocos que não devem ser alterados por sanitização numérica.

    CSS, JavaScript e imagens base64 têm muitos números estruturais. Alterá-los
    quebraria o layout e os recursos do relatório.
    """

    protected: dict[str, str] = {}

    def store(match: re.Match[str]) -> str:
        key = f"__PROTECTED_BLOCK_{len(protected)}__"
        protected[key] = match.group(0)
        return key

    text = re.sub(r"<style\b.*?</style>", store, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script\b.*?</script>", store, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"data:image/[^\"']+", store, text)
    return text, protected


def restore_blocks(text: str, protected: dict[str, str]) -> str:
    for key, value in protected.items():
        text = text.replace(key, value)

    return text


def low_demo_number(number: int) -> int:
    """
    Converte valores reais para números baixos e plausíveis para divulgação.
    """

    if number <= 9:
        return number

    if number <= 30:
        return max(1, number % 8)

    if number <= 99:
        return 8 + (number % 12)

    if number <= 999:
        return 18 + (number % 24)

    return 1 + (number % 9)


def sanitize_public_numbers(text: str) -> str:
    """
    Baixa totais e contagens visíveis sem alterar datas, CSS, JS ou imagens.
    """

    protected_text, protected = protect_blocks(text)

    def replace_count(match: re.Match[str]) -> str:
        number = int(match.group(1))
        return str(low_demo_number(number))

    def replace_percent_pair(match: re.Match[str]) -> str:
        count = low_demo_number(int(match.group(1)))
        percent = min(9.8, max(0.3, float(match.group(2)) / 9))
        return f"{count} | {percent:.1f}%"

    def replace_event_total(match: re.Match[str]) -> str:
        return f"{low_demo_number(int(match.group(1)))}{match.group(2)}"

    protected_text = re.sub(r"\b(\d{2,4})\s*\|\s*(\d{1,3}(?:\.\d)?)%", replace_percent_pair, protected_text)
    protected_text = re.sub(r"\b(\d{2,4})(\s+incidentes?)\b", replace_event_total, protected_text, flags=re.IGNORECASE)
    protected_text = re.sub(r"\b(\d{2,4})(\s+equipamentos?)\b", replace_event_total, protected_text, flags=re.IGNORECASE)
    protected_text = re.sub(r"\b(\d{2,4})(\s+unidades?)\b", replace_event_total, protected_text, flags=re.IGNORECASE)
    protected_text = re.sub(r"(?<![/.-])\b(\d{2,4})\b(?![/.-])", replace_count, protected_text)

    return restore_blocks(protected_text, protected)


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
    text = sanitize_public_numbers(text)

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


def windows_path(path: Path) -> str:
    resolved = path.resolve()
    text = str(resolved)

    if text.startswith("/mnt/c/"):
        return "C:\\" + text.removeprefix("/mnt/c/").replace("/", "\\")

    return text


def windows_file_url(path: Path) -> str:
    win_path = windows_path(path).replace("\\", "/")

    if re.match(r"^[A-Za-z]:/", win_path):
        return f"file:///{win_path}"

    return path.as_uri()


def browser_executable() -> Path | None:
    for candidate in (WINDOWS_EDGE, WINDOWS_CHROME):
        if candidate.exists():
            return candidate

    return None


def capture_variant_html(html_path: Path, output_dir: Path, selector: str, filename: str) -> Path:
    html = html_path.read_text(encoding="utf-8")
    script = f"""
    <script>
        window.addEventListener("load", () => {{
            localStorage.clear();
            document.body.classList.add("theme-dark");
            const target = document.querySelector({selector!r});
            if (target) {{
                target.scrollIntoView({{ behavior: "instant", block: "start" }});
            }}
        }});
    </script>
    """
    variant_path = output_dir / f"capture_{filename}.html"
    variant_path.write_text(html.replace("</body>", f"{script}</body>", 1), encoding="utf-8")
    return variant_path


def screenshot_with_windows_browser(html_path: Path, output_dir: Path) -> list[Path]:
    executable = browser_executable()

    if not executable:
        raise FileNotFoundError("Microsoft Edge ou Google Chrome nao foi encontrado no Windows.")

    captures = [
        ("01_visao_geral.png", "main"),
        ("02_inteligencia_operacional.png", ".executive-intelligence"),
        ("03_mapa_criticidade.png", ".unit-criticality-map"),
        ("04_filtro_relatorio.png", ".filter-panel"),
    ]
    created: list[Path] = []
    capture_dir = output_dir / "_capture_html"
    capture_dir.mkdir(parents=True, exist_ok=True)

    for image_name, selector in captures:
        variant = capture_variant_html(html_path, capture_dir, selector, Path(image_name).stem)
        image_path = output_dir / image_name
        command = (
            f'"{windows_path(executable)}" '
            "--headless --disable-gpu --hide-scrollbars "
            "--window-size=1600,1000 --virtual-time-budget=2500 "
            f'--screenshot="{windows_path(image_path)}" '
            f'"{windows_file_url(variant)}"'
        )
        result = subprocess.run(
            ["cmd.exe", "/c", command],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "Falha desconhecida").strip())

        if image_path.exists():
            created.append(image_path)

    return created


def load_font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)

    return ImageFont.load_default()


def draw_text(draw, xy, text, size=24, fill="#eafcff", bold=False, anchor=None):
    font = load_font(size, bold)
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def rounded(draw, box, radius=28, fill="#0e343b", outline="#2a737b", width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_badge(draw, xy, text, fill="#123f46", outline="#2a737b", color="#bff8f8"):
    x, y = xy
    font = load_font(22, True)
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0] + 34
    h = 42
    draw.rounded_rectangle((x, y, x + w, y + h), radius=21, fill=fill, outline=outline, width=2)
    draw.ellipse((x + 14, y + 15, x + 24, y + 25), fill="#20c4cd")
    draw.text((x + 32, y + 10), text, font=font, fill=color)
    return w


def draw_metric_card(draw, box, label, value, accent="#20c4cd"):
    rounded(draw, box, radius=22, fill="#123b43", outline="#2a737b", width=2)
    x1, y1, x2, y2 = box
    draw.rectangle((x1, y1, x1 + 5, y2), fill=accent)
    draw_text(draw, (x1 + 24, y1 + 22), label.upper(), 18, "#a9cdd2", True)
    draw_text(draw, (x1 + 24, y1 + 62), value, 38, "#ffffff", True)


def draw_bar_row(draw, x, y, label, value, width=420, color="#20c4cd", detail=""):
    draw_text(draw, (x, y), label, 22, "#eafcff", True)
    draw_text(draw, (x + width - 4, y), value, 22, "#ffffff", True, anchor="ra")
    draw.rounded_rectangle((x, y + 36, x + width, y + 46), radius=5, fill="#254d55")
    first_number = re.search(r"\d+", value)
    numeric_value = int(first_number.group(0)) if first_number else 1
    bar_width = max(22, min(width, int(width * (numeric_value / 24))))
    draw.rounded_rectangle((x, y + 36, x + bar_width, y + 46), radius=5, fill=color)
    if detail:
        draw_text(draw, (x, y + 52), detail, 16, "#a9cdd2")


def create_canvas():
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1600, 900), "#061b21")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1600, 900), fill="#061b21")
    draw.ellipse((1180, -220, 1770, 370), outline="#1c737b", width=2)
    draw.rectangle((0, 0, 1600, 8), fill="#20c4cd")
    return image, draw


def generate_public_pngs(output_dir: Path) -> list[Path]:
    """
    Gera imagens públicas quando não há navegador headless disponível.

    Os dados são demonstrativos e propositalmente baixos para divulgação.
    """

    from PIL import ImageDraw

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    # Visão geral.
    image, draw = create_canvas()
    draw_badge(draw, (70, 54), "DEMONSTRAÇÃO PÚBLICA")
    draw_text(draw, (70, 130), "Relatório Executivo de Incidentes Zabbix", 54, "#ffffff", True)
    draw_text(draw, (70, 204), "Dados sanitizados para apresentação pública no LinkedIn", 24, "#c7e5e7")
    draw_metric_card(draw, (70, 285, 420, 410), "Incidentes abertos", "24", "#d92f3a")
    draw_metric_card(draw, (450, 285, 800, 410), "Mais antigo", "3d 4h", "#e67700")
    draw_metric_card(draw, (830, 285, 1180, 410), "Score médio", "18.6", "#20c4cd")
    rounded(draw, (70, 470, 740, 820), radius=28, fill="#0d3037", outline="#2a737b")
    draw_text(draw, (105, 505), "Severidade dos incidentes", 30, "#ffffff", True)
    draw.pieslice((120, 575, 340, 795), 0, 210, fill="#e67700")
    draw.pieslice((120, 575, 340, 795), 210, 315, fill="#2f9e44")
    draw.pieslice((120, 575, 340, 795), 315, 350, fill="#1c7ed6")
    draw.ellipse((170, 625, 290, 745), fill="#061b21")
    draw_text(draw, (230, 655), "24", 42, "#ffffff", True, "mm")
    draw_text(draw, (230, 700), "abertos", 17, "#a9cdd2", True, "mm")
    draw_bar_row(draw, 390, 585, "Alta", "12", 280, "#e67700")
    draw_bar_row(draw, 390, 660, "Atenção", "8", 280, "#2f9e44")
    draw_bar_row(draw, 390, 735, "Informação", "4", 280, "#1c7ed6")
    rounded(draw, (780, 470, 1530, 820), radius=28, fill="#0d3037", outline="#2a737b")
    draw_text(draw, (815, 505), "Equipamentos em destaque", 30, "#ffffff", True)
    for idx, (name, value) in enumerate([("Câmera", 9), ("Terminal", 6), ("Switch", 4), ("Mikrotik", 3), ("NVR", 2)]):
        x = 840 + idx * 130
        draw.rounded_rectangle((x, 605, x + 70, 760), radius=35, fill="#173f47")
        draw.rounded_rectangle((x, 760 - value * 11, x + 70, 760), radius=35, fill="#20c4cd")
        draw_text(draw, (x + 35, 780), str(value), 22, "#ffffff", True, "mm")
        draw_text(draw, (x + 35, 812), name, 16, "#c7e5e7", True, "mm")
    path = output_dir / "01_visao_geral_publica.png"
    image.save(path)
    paths.append(path)

    # Mapa de criticidade.
    image, draw = create_canvas()
    draw_badge(draw, (70, 54), "MAPA DE CRITICIDADE")
    draw_text(draw, (70, 125), "Unidades que exigem atenção operacional", 48, "#ffffff", True)
    draw_text(draw, (70, 190), "Score demonstrativo baseado em volume, severidade, tempo offline, recorrência e impacto do equipamento.", 23, "#c7e5e7")
    cards = [
        ("Unidade Escolar 001", 31, "Acompanhamento ativo", "6 incidentes", "2 equipamentos", "3d 4h"),
        ("Unidade Escolar 002", 24, "Monitoramento normal", "4 incidentes", "2 equipamentos", "2d 7h"),
        ("Unidade Escolar 003", 21, "Monitoramento normal", "3 incidentes", "1 equipamento", "1d 5h"),
        ("Unidade Escolar 004", 18, "Monitoramento normal", "2 incidentes", "1 equipamento", "8h"),
    ]
    for idx, card in enumerate(cards):
        x = 70 + (idx % 2) * 730
        y = 280 + (idx // 2) * 260
        rounded(draw, (x, y, x + 670, y + 220), radius=26, fill="#123b43", outline="#2a737b")
        draw.rounded_rectangle((x + 28, y + 30, x + 118, y + 120), radius=24, fill="#20a6b2")
        draw_text(draw, (x + 73, y + 75), str(card[1]), 36, "#ffffff", True, "mm")
        draw_text(draw, (x + 150, y + 32), card[0], 28, "#ffffff", True)
        draw_text(draw, (x + 150, y + 75), card[2], 17, "#9ff4f1", True)
        draw_text(draw, (x + 34, y + 150), card[3], 22, "#eafcff", True)
        draw_text(draw, (x + 245, y + 150), card[4], 22, "#eafcff", True)
        draw_text(draw, (x + 475, y + 150), card[5], 22, "#eafcff", True)
    path = output_dir / "02_mapa_criticidade_publico.png"
    image.save(path)
    paths.append(path)

    # Rankings.
    image, draw = create_canvas()
    draw_badge(draw, (70, 54), "RANKINGS EXECUTIVOS")
    draw_text(draw, (70, 125), "Prioridades operacionais do recorte", 48, "#ffffff", True)
    columns = [
        ("Equipamentos afetados", [("Câmera", "9"), ("Terminal Facial", "6"), ("Switch", "4"), ("Mikrotik", "3")]),
        ("Tipos de incidente", [("Unavailable by ICMP ping", "11"), ("High ICMP ping loss", "5"), ("No SNMP data", "3"), ("Interface down", "2")]),
        ("Passivo por unidade", [("Unidade Escolar 001", "3d 4h"), ("Unidade Escolar 002", "2d 7h"), ("Unidade Escolar 003", "1d 5h"), ("Unidade Escolar 004", "8h")]),
    ]
    for idx, (title, rows) in enumerate(columns):
        x = 70 + idx * 510
        rounded(draw, (x, 230, x + 470, 810), radius=28, fill="#0d3037", outline="#2a737b")
        draw_text(draw, (x + 32, 270), title, 28, "#ffffff", True)
        for row_idx, (label, value) in enumerate(rows):
            y = 340 + row_idx * 105
            draw_bar_row(draw, x + 32, y, label, value, 390, "#20c4cd")
    path = output_dir / "03_rankings_publicos.png"
    image.save(path)
    paths.append(path)

    # Detalhes.
    image, draw = create_canvas()
    rounded(draw, (250, 80, 1350, 820), radius=28, fill="#0d3037", outline="#2a737b", width=3)
    draw.rectangle((250, 80, 1350, 170), fill="#123f46")
    draw_text(draw, (295, 112), "Detalhes do Incidente", 34, "#ffffff", True)
    draw_text(draw, (1295, 118), "×", 42, "#dff7f5", True, "mm")
    rows = [
        ("Status", "Aberto"), ("Tempo offline", "4h"), ("Unidade", "Unidade Escolar 001"),
        ("Host", "HOST-DEMO 001"), ("Equipamento", "Câmera"),
        ("Tipo de incidente", "Unavailable by ICMP ping"), ("Severidade", "Atenção"),
        ("Prioridade", "Normal"), ("Evento", "7000000"),
    ]
    for idx, (label, value) in enumerate(rows):
        x = 295 + (idx % 2) * 510
        y = 215 + (idx // 2) * 105
        rounded(draw, (x, y, x + 470, y + 78), radius=16, fill="#123b43", outline="#2a737b")
        draw_text(draw, (x + 22, y + 16), label.upper(), 16, "#a9cdd2", True)
        draw_text(draw, (x + 22, y + 42), value, 22, "#ffffff", True)
    path = output_dir / "04_detalhes_publicos.png"
    image.save(path)
    paths.append(path)

    return paths


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
        try:
            screenshots = screenshot_with_windows_browser(html_path, images_dir)
            warning = (
                "Playwright local falhou, mas os prints foram gerados pelo navegador do Windows.\n"
                f"Motivo do Playwright: {exc}\n"
            )
        except Exception as fallback_exc:
            screenshots = generate_public_pngs(images_dir)
            warning = (
                "O HTML sanitizado foi gerado. Como as capturas por navegador falharam,\n"
                "foram gerados PNGs publicos demonstrativos com dados baixos e sanitizados.\n"
                f"Motivo Playwright: {exc}\n"
                f"Motivo navegador Windows: {fallback_exc}\n"
            )

        (output_dir / "AVISO_PRINTS.txt").write_text(warning, encoding="utf-8")

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
