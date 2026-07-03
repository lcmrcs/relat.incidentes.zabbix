"""
Prepara uma versão pública do relatório para publicação no LinkedIn.

O script parte do HTML executivo mais recente, mascara dados sensíveis e gera
prints do relatório sanitizado quando há navegador disponível. A intenção é
divulgar o projeto sem expor IPs, nomes internos, hosts, URLs privadas ou
números operacionais sensíveis, preservando o visual real do HTML executivo.
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
CAPTURES = [
    ("01_visao_geral.png", "main"),
    ("02_inteligencia_operacional.png", ".executive-intelligence"),
    ("03_mapa_criticidade.png", ".unit-criticality-map"),
    ("04_filtro_relatorio.png", ".filter-panel"),
]


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
    text = re.sub(r"\b\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\b", store, text)
    text = re.sub(r"\b\d{1,2}:\d{2}\b", store, text)
    text = re.sub(r"\bÚltimas\s+\d{1,2}h\b", store, text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{1,2}\s+a\s+\d{1,2}\s+dias\b", store, text, flags=re.IGNORECASE)
    text = re.sub(r"\+\d{1,3}\s+dias\b", store, text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{1,2}-\d{1,2}d\b", store, text, flags=re.IGNORECASE)
    text = re.sub(r"\+\d{1,3}d\b", store, text, flags=re.IGNORECASE)
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


def force_lunar_mode(text: str) -> str:
    """
    Deixa o HTML público pronto para abrir e capturar no modo lunar.
    """

    text = re.sub(r"<body(?![^>]*class=)", '<body class="theme-dark"', text, count=1)
    text = re.sub(
        r'<body class="([^"]*)"',
        lambda match: (
            match.group(0)
            if "theme-dark" in match.group(1).split()
            else f'<body class="{match.group(1)} theme-dark"'
        ),
        text,
        count=1,
    )
    script = """
    <script>
        localStorage.setItem("zabbix-report-theme", "dark");
        document.addEventListener("DOMContentLoaded", () => {
            document.body.classList.add("theme-dark");
        });
    </script>
    """

    if "</head>" in text:
        text = text.replace("</head>", f"{script}\n</head>", 1)

    return text


def inject_public_dom_sanitizer(text: str) -> str:
    """
    Reaplica a sanitização depois que o JavaScript do relatório recalcula telas.

    O HTML original possui filtros e cartões que são atualizados no navegador.
    Para material público, essa camada evita que contagens reais voltem a
    aparecer depois do carregamento da página.
    """

    script = """
    <script>
        (() => {
            const dayCycle = [0, 1, 2, 3, 4, 5, 6];
            const lowDemoNumber = (value) => {
                const number = Number(value);
                if (!Number.isFinite(number) || number <= 9) return String(value);
                if (number <= 30) return String(Math.max(1, number % 8));
                if (number <= 99) return String(8 + (number % 12));
                if (number <= 999) return String(18 + (number % 24));
                return String(1 + (number % 9));
            };
            const softenAge = (text) => text
                .replace(/\\b(\\d{2,4})d\\s+(\\d{1,2})h\\b/g, (_, days, hours) => {
                    const day = dayCycle[Number(days) % dayCycle.length];
                    const hour = Number(hours) % 8;
                    return day ? `${day}d ${hour}h` : `${hour}h`;
                })
                .replace(/\\b(\\d{2,4})h\\s+(\\d{1,2})min\\b/g, (_, hours, minutes) => {
                    const hour = Math.max(1, Number(hours) % 6);
                    return `${hour}h ${Number(minutes) % 60}min`;
                });
            const sanitizeText = (text) => {
                if (!text || /\\d{2}\\/\\d{2}\\/\\d{4}/.test(text)) return text;
                let output = softenAge(text);
                output = output.replace(/\\b(\\d{2,4})\\s*\\|\\s*(\\d{1,3}(?:\\.\\d)?)%/g, (_, count, percent) => {
                    const safePercent = Math.min(9.8, Math.max(0.3, Number(percent) / 9)).toFixed(1);
                    return `${lowDemoNumber(count)} | ${safePercent}%`;
                });
                output = output.replace(/\\b(\\d{2,4})(\\s+(?:incidentes?|equipamentos?|unidades?))\\b/gi, (_, number, suffix) => {
                    return `${lowDemoNumber(number)}${suffix}`;
                });
                output = output.replace(/(?<![\\/.:\\-])\\b\\d{2,4}\\b(?![\\/.:\\-])/g, (number) => lowDemoNumber(number));
                return output;
            };
            const sanitizeDom = () => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                const nodes = [];
                while (walker.nextNode()) nodes.push(walker.currentNode);
                for (const node of nodes) {
                    const next = sanitizeText(node.nodeValue);
                    if (next !== node.nodeValue) node.nodeValue = next;
                }
                document.body.classList.add("theme-dark");
            };
            window.addEventListener("load", () => {
                sanitizeDom();
                setTimeout(sanitizeDom, 300);
                setTimeout(sanitizeDom, 900);
            });
        })();
    </script>
    """

    if "</body>" in text:
        text = text.replace("</body>", f"{script}\n</body>", 1)

    return text


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

    return inject_public_dom_sanitizer(force_lunar_mode(text))


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

    created: list[Path] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.evaluate("localStorage.clear(); document.body.classList.add('theme-dark');")
        page.wait_for_timeout(600)

        for filename, selector in CAPTURES:
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


def prepare_capture_variants(html_path: Path, output_dir: Path) -> dict[str, Path]:
    """
    Cria HTMLs auxiliares para capturar partes específicas do relatório real.

    Esses arquivos usam o próprio HTML sanitizado como base. A única diferença
    é um pequeno script que ativa o modo escuro e posiciona a página no bloco
    que será fotografado.
    """

    capture_dir = output_dir / "_capture_html"
    capture_dir.mkdir(parents=True, exist_ok=True)

    return {
        image_name: capture_variant_html(
            html_path,
            capture_dir,
            selector,
            Path(image_name).stem,
        )
        for image_name, selector in CAPTURES
    }


def write_windows_capture_bat(output_dir: Path, variants: dict[str, Path]) -> Path:
    """
    Gera um atalho Windows para capturar prints fiéis fora do WSL.
    """

    images_dir = output_dir / "imagens"
    bat_path = output_dir / "capturar_prints_no_windows.bat"
    lines = [
        "@echo off",
        "setlocal",
        "set BROWSER=%ProgramFiles(x86)%\\Microsoft\\Edge\\Application\\msedge.exe",
        "if not exist \"%BROWSER%\" set BROWSER=%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe",
        "if not exist \"%BROWSER%\" (",
        "  echo Nao foi encontrado Microsoft Edge ou Google Chrome.",
        "  pause",
        "  exit /b 1",
        ")",
        f"if not exist \"{windows_path(images_dir)}\" mkdir \"{windows_path(images_dir)}\"",
    ]

    for image_name, variant_path in variants.items():
        image_path = images_dir / image_name
        lines.append(
            "\"%BROWSER%\" --headless --disable-gpu --hide-scrollbars "
            "--window-size=1600,1000 --virtual-time-budget=2500 "
            f"--screenshot=\"{windows_path(image_path)}\" "
            f"\"{windows_file_url(variant_path)}\""
        )

    lines.extend([
        "echo.",
        f"echo Prints gerados em: {windows_path(images_dir)}",
        "pause",
    ])
    bat_path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return bat_path


def screenshot_with_windows_browser(html_path: Path, output_dir: Path) -> list[Path]:
    executable = browser_executable()

    if not executable:
        raise FileNotFoundError("Microsoft Edge ou Google Chrome nao foi encontrado no Windows.")

    created: list[Path] = []
    variants = prepare_capture_variants(html_path, output_dir)

    for image_name, variant in variants.items():
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


def main() -> None:
    source = latest_report()
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUT_ROOT / f"post_{today}"
    images_dir = output_dir / "imagens"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    for old_image in images_dir.glob("*.png"):
        old_image.unlink()

    sanitized_html = sanitize_html(source.read_text(encoding="utf-8"))
    html_path = output_dir / "relatorio_publico_linkedin.html"
    text_path = output_dir / "texto_linkedin.md"
    html_path.write_text(sanitized_html, encoding="utf-8")
    text_path.write_text(LINKEDIN_TEXT, encoding="utf-8")
    variants = prepare_capture_variants(html_path, images_dir)
    windows_capture_bat = write_windows_capture_bat(output_dir, variants)

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
            warning = (
                "O HTML sanitizado foi gerado. Como as capturas por navegador falharam,\n"
                "nenhum print foi criado automaticamente. Para manter fidelidade visual,\n"
                "este script nao gera imagens simuladas. Abra o HTML sanitizado no navegador\n"
                "e capture as telas manualmente, ou instale as dependencias do Playwright.\n"
                f"Motivo Playwright: {exc}\n"
                f"Motivo navegador Windows: {fallback_exc}\n"
            )

        (output_dir / "AVISO_PRINTS.txt").write_text(warning, encoding="utf-8")

    print(f"HTML sanitizado: {html_path}")
    print(f"Texto LinkedIn: {text_path}")
    print(f"Pasta de imagens: {images_dir}")
    print(f"Captura fiel no Windows: {windows_capture_bat}")

    if screenshots:
        print("Prints gerados:")
        for path in screenshots:
            print(f"- {path}")
    else:
        print("Prints automaticos nao foram gerados.")


if __name__ == "__main__":
    main()
