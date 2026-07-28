#!/usr/bin/env python3
"""Executa regressão visual e auditoria de acessibilidade no relatório HTML.

Usa apenas dados fictícios e o Edge/Chrome já instalado no Windows. Baselines
somente são alteradas quando ``--update-baselines`` é informado explicitamente.
"""

from __future__ import annotations

import argparse
import html
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_html_browser import (  # noqa: E402
    browser_version,
    file_url,
    find_browser,
    render_fixture,
    windows_path,
)

BASELINE_DIR = ROOT / "zabbix-report" / "tests" / "visual_baselines"
RESULT_JSON = ROOT / "VALIDACAO_VISUAL_ACESSIBILIDADE_SPRINT_7.json"
RESULT_MARKDOWN = ROOT / "VALIDACAO_VISUAL_ACESSIBILIDADE_SPRINT_7.md"
RESULT_PATTERN = re.compile(
    r'<pre id="sprint7-accessibility-result"[^>]*>(.*?)</pre>',
    re.DOTALL,
)
PIXEL_TOLERANCE = 18
DIFFERENCE_LIMIT_PERCENT = 0.35

CAPTURES = (
    {
        "name": "desktop_solar_cabecalho",
        "size": (1600, 1000),
        "theme": "solar",
        "records": 40,
        "section": None,
        "modal": None,
    },
    {
        "name": "desktop_lunar_inteligencia",
        "size": (1600, 1000),
        "theme": "lunar",
        "records": 40,
        "section": ".executive-intelligence",
        "modal": None,
    },
    {
        "name": "desktop_solar_rankings",
        "size": (1600, 1000),
        "theme": "solar",
        "records": 40,
        "section": ".insights",
        "modal": None,
    },
    {
        "name": "tablet_solar_criticidade",
        "size": (768, 1024),
        "theme": "solar",
        "records": 40,
        "section": ".unit-criticality-map",
        "modal": None,
    },
    {
        "name": "tablet_lunar_filtros",
        "size": (768, 1024),
        "theme": "lunar",
        "records": 40,
        "section": ".filter-panel",
        "modal": None,
    },
    {
        "name": "mobile_solar_tabela",
        "size": (390, 844),
        "theme": "solar",
        "records": 40,
        "section": ".table-wrap",
        "modal": None,
    },
    {
        "name": "mobile_lunar_incidente",
        "size": (390, 844),
        "theme": "lunar",
        "records": 40,
        "section": None,
        "modal": "[data-details]",
    },
    {
        "name": "desktop_solar_zabbix",
        "size": (1600, 1000),
        "theme": "solar",
        "records": 40,
        "section": None,
        "modal": "[data-zabbix-open]",
    },
    {
        "name": "desktop_lunar_confea",
        "size": (1600, 1000),
        "theme": "lunar",
        "records": 40,
        "section": None,
        "modal": "[data-confea-open]",
    },
    {
        "name": "mobile_solar_vazio",
        "size": (390, 844),
        "theme": "solar",
        "records": 0,
        "section": ".empty-state",
        "modal": None,
    },
    {
        "name": "desktop_lunar_grande_volume",
        "size": (1600, 1000),
        "theme": "lunar",
        "records": 7171,
        "section": ".table-wrap",
        "modal": None,
    },
)

AUDITS = tuple(
    {
        "name": f"{device}_{theme}",
        "size": size,
        "theme": theme,
        "reduced_motion": device == "desktop",
        "zoom": 2 if device == "desktop" else 1,
    }
    for device, size in (
        ("mobile", (390, 844)),
        ("tablet", (768, 1024)),
        ("desktop", (1600, 1000)),
    )
    for theme in ("solar", "lunar")
)


def inject_capture_state(
    path: Path,
    *,
    theme: str,
    section: str | None,
    modal: str | None,
) -> None:
    document = path.read_text(encoding="utf-8")
    script = f"""
<style>
    *, *::before, *::after {{
        animation: none !important;
        caret-color: transparent !important;
        scroll-behavior: auto !important;
        transition: none !important;
    }}
</style>
<script>
localStorage.setItem("zabbix-report-theme", {json.dumps("dark" if theme == "lunar" else "light")});
document.body.classList.toggle("theme-dark", {str(theme == "lunar").lower()});
const modalTrigger = document.querySelector({json.dumps(modal)});
modalTrigger?.click();
const target = document.querySelector({json.dumps(section)});
if (target && !modalTrigger) {{
    const isolated = target.cloneNode(true);
    document.body.replaceChildren(isolated);
    document.body.style.padding = "20px";
}}
document.documentElement.dataset.visualReady = "true";
</script>
"""
    path.write_text(document.replace("</body>", f"{script}</body>", 1), encoding="utf-8")


def capture_screenshot(
    browser: Path,
    fixture: Path,
    output: Path,
    profile: Path,
    size: tuple[int, int],
) -> None:
    width, height = size
    result = subprocess.run(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--hide-scrollbars",
            "--run-all-compositor-stages-before-draw",
            "--force-device-scale-factor=1",
            f"--window-size={width},{height}",
            f"--user-data-dir={windows_path(profile)}",
            "--virtual-time-budget=2500",
            f"--screenshot={windows_path(output)}",
            file_url(fixture),
        ],
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0 or not output.exists():
        detail = result.stderr.decode("utf-8", errors="replace")[-1000:]
        raise RuntimeError(f"Falha ao capturar {output.name}: {detail}")


def compare_images(current: Path, baseline: Path, diff_path: Path) -> dict:
    with Image.open(current).convert("RGB") as current_image:
        with Image.open(baseline).convert("RGB") as baseline_image:
            if current_image.size != baseline_image.size:
                return {
                    "passed": False,
                    "difference_percent": 100.0,
                    "reason": (
                        f"dimensão atual {current_image.size} diferente da "
                        f"baseline {baseline_image.size}"
                    ),
                }
            difference = ImageChops.difference(current_image, baseline_image)
            mask = difference.convert("L").point(
                lambda value: 255 if value > PIXEL_TOLERANCE else 0
            )
            changed = sum(1 for value in mask.get_flattened_data() if value)
            total = current_image.width * current_image.height
            percent = changed / total * 100
            if percent > DIFFERENCE_LIMIT_PERCENT:
                enhanced = difference.point(lambda value: min(255, value * 4))
                enhanced.save(diff_path)
            return {
                "passed": percent <= DIFFERENCE_LIMIT_PERCENT,
                "difference_percent": round(percent, 4),
                "reason": "",
            }


def accessibility_script(theme: str, zoom: int) -> str:
    dark = theme == "lunar"
    return f"""
<script>
(() => {{
    const violations = [];
    const checks = [];
    const add = (id, severity, message, selector = "") => {{
        violations.push({{ id, severity, message, selector }});
    }};
    const pass = (id) => checks.push(id);
    const visible = element => {{
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" &&
            rect.width > 0 && rect.height > 0;
    }};
    const accessibleName = element => {{
        const labelledBy = element.getAttribute("aria-labelledby");
        if (labelledBy) {{
            return labelledBy.split(/\\s+/).map(id => document.getElementById(id)?.textContent || "").join(" ").trim();
        }}
        return (
            element.getAttribute("aria-label") ||
            element.closest("label")?.textContent ||
            element.textContent ||
            element.getAttribute("alt") ||
            ""
        ).trim();
    }};
    const parseColor = value => {{
        const numbers = String(value).match(/[\\d.]+/g) || [];
        return numbers.slice(0, 3).map(Number);
    }};
    const luminance = color => {{
        const channels = color.map(value => {{
            const normalized = value / 255;
            return normalized <= 0.03928
                ? normalized / 12.92
                : ((normalized + 0.055) / 1.055) ** 2.4;
        }});
        return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    }};
    const contrast = (first, second) => {{
        const values = [luminance(first), luminance(second)].sort((a, b) => b - a);
        return (values[0] + 0.05) / (values[1] + 0.05);
    }};
    const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

    window.addEventListener("load", async () => {{
        await wait(220);
        document.body.classList.toggle("theme-dark", {str(dark).lower()});
        await wait(80);

        if (document.documentElement.lang.toLowerCase() !== "pt-br") {{
            add("html-lang", "critical", "Idioma principal ausente ou incorreto.", "html");
        }} else pass("html-lang");

        for (const landmark of ["main", "header", "nav"]) {{
            if (!document.querySelector(landmark)) {{
                add("landmark", "serious", `Landmark ausente: ${{landmark}}.`, landmark);
            }}
        }}

        const headings = [...document.querySelectorAll("h1, h2, h3, h4, h5, h6")];
        if (document.querySelectorAll("h1").length !== 1) {{
            add("heading-h1", "serious", "A página deve possuir exatamente um h1.", "h1");
        }}
        let previousLevel = 0;
        for (const heading of headings) {{
            const level = Number(heading.tagName.slice(1));
            if (previousLevel && level > previousLevel + 1) {{
                add("heading-order", "moderate", "Hierarquia de títulos salta níveis.", heading.tagName);
            }}
            previousLevel = level;
        }}

        for (const control of document.querySelectorAll("button, a[href], input, select")) {{
            if (visible(control) && !accessibleName(control)) {{
                add("accessible-name", "serious", "Controle sem nome acessível.", control.tagName);
            }}
        }}
        for (const image of document.querySelectorAll("img")) {{
            if (!image.hasAttribute("alt")) {{
                add("image-alt", "serious", "Imagem sem atributo alt.", "img");
            }}
        }}
        for (const header of document.querySelectorAll("table thead th")) {{
            if (header.getAttribute("scope") !== "col") {{
                add("table-header", "serious", "Cabeçalho de tabela sem scope=col.", "th");
            }}
        }}
        for (const dialog of document.querySelectorAll("dialog")) {{
            const reference = dialog.getAttribute("aria-labelledby");
            if (!reference || !document.getElementById(reference)) {{
                add("dialog-name", "serious", "Modal sem título associado.", `#${{dialog.id}}`);
            }}
        }}
        for (const reference of document.querySelectorAll("[aria-labelledby], [aria-describedby]")) {{
            for (const attribute of ["aria-labelledby", "aria-describedby"]) {{
                const ids = (reference.getAttribute(attribute) || "").split(/\\s+/).filter(Boolean);
                if (ids.some(id => !document.getElementById(id))) {{
                    add("aria-reference", "serious", `Referência ${{attribute}} inválida.`, reference.tagName);
                }}
            }}
        }}
        if (!document.querySelector('[role="status"][aria-live]')) {{
            add("live-status", "moderate", "Mensagens dinâmicas não possuem região viva.", "[role=status]");
        }}

        const positiveTabIndex = [...document.querySelectorAll("[tabindex]")].filter(
            element => Number(element.getAttribute("tabindex")) > 0
        );
        if (positiveTabIndex.length) {{
            add("tab-order", "serious", "Ordem de tabulação forçada com tabindex positivo.", "[tabindex]");
        }}
        const hiddenFocusable = [...document.querySelectorAll(
            '[hidden] button, [hidden] a[href], [aria-hidden="true"] button, [aria-hidden="true"] a[href]'
        )].filter(element => element.tabIndex >= 0);
        if (hiddenFocusable.length) {{
            add("hidden-focus", "serious", "Elemento oculto permanece focável.");
        }}

        const focusProbe = document.querySelector("[data-theme-toggle]");
        focusProbe?.focus();
        const focusStyle = focusProbe ? getComputedStyle(focusProbe) : null;
        if (!focusProbe || (
            focusStyle.outlineStyle === "none" &&
            focusStyle.boxShadow === "none"
        )) {{
            add("focus-visible", "serious", "Foco de teclado não possui indicação visual.");
        }}

        const details = document.querySelector("[data-details]");
        if (details) {{
            details.focus();
            details.click();
            await wait(30);
            const modal = document.getElementById("incident-dialog");
            if (!modal?.open || !modal.contains(document.activeElement)) {{
                add("modal-focus-entry", "critical", "Foco não entrou no modal.", "#incident-dialog");
            }}
            const outside = document.querySelector("[data-theme-toggle]");
            outside?.focus();
            if (document.activeElement === outside) {{
                add("modal-focus-trap", "critical", "Foco escapou do modal aberto.", "#incident-dialog");
            }}
            modal?.querySelector("[data-modal-close]")?.click();
            await wait(20);
            if (document.activeElement !== details) {{
                add("modal-focus-return", "serious", "Foco não retornou ao acionador.", "#incident-dialog");
            }}
        }}

        for (const element of document.querySelectorAll("button, input, select, a[href]")) {{
            if (!visible(element)) continue;
            const rect = element.getBoundingClientRect();
            if (rect.width < 24 || rect.height < 24) {{
                add(
                    "target-size",
                    "moderate",
                    `Área interativa menor que 24px: ${{Math.round(rect.width)}}x${{Math.round(rect.height)}}.`,
                    element.tagName
                );
                break;
            }}
        }}

        const colorProbe = document.createElement("span");
        colorProbe.style.color = "var(--text)";
        colorProbe.style.backgroundColor = "var(--bg)";
        document.body.appendChild(colorProbe);
        const probeStyle = getComputedStyle(colorProbe);
        const foreground = parseColor(probeStyle.color);
        const background = parseColor(probeStyle.backgroundColor);
        colorProbe.remove();
        if (foreground.length === 3 && background.length === 3 && contrast(foreground, background) < 4.5) {{
            add("contrast", "critical", "Contraste base inferior a 4.5:1.", "body");
        }}

        const overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
        if (overflow > 2) {{
            add("horizontal-overflow", "serious", `Overflow horizontal de ${{overflow}}px.`, "html");
        }}
        const cards = [...document.querySelectorAll(
            ".summary-item, .chart-card, .intelligence-card, .filtered-card"
        )].filter(visible);
        for (let index = 0; index < cards.length; index += 1) {{
            const first = cards[index].getBoundingClientRect();
            for (let otherIndex = index + 1; otherIndex < cards.length; otherIndex += 1) {{
                if (cards[index].parentElement !== cards[otherIndex].parentElement) continue;
                const second = cards[otherIndex].getBoundingClientRect();
                const overlap = (
                    first.left < second.right - 1 && first.right > second.left + 1 &&
                    first.top < second.bottom - 1 && first.bottom > second.top + 1
                );
                if (overlap) {{
                    add("card-overlap", "serious", "Cards irmãos estão sobrepostos.");
                    index = cards.length;
                    break;
                }}
            }}
        }}

        if ({str(zoom == 2).lower()} && document.documentElement.scrollWidth > innerWidth + 2) {{
            add("zoom-200", "serious", "Zoom de 200% criou overflow horizontal indevido.", "html");
        }}
        if ({str(zoom == 2).lower()} && !matchMedia("(prefers-reduced-motion: reduce)").matches) {{
            add("reduced-motion", "moderate", "Preferência de movimento reduzido não foi detectada.");
        }}

        const result = {{
            passed: !violations.some(item => ["critical", "serious"].includes(item.severity)),
            violations,
            checks,
            theme: {json.dumps(theme)},
            viewport: `${{innerWidth}}x${{innerHeight}}`,
            zoom: {zoom},
            reduced_motion: matchMedia("(prefers-reduced-motion: reduce)").matches,
            offline: location.protocol === "file:",
        }};
        const output = document.createElement("pre");
        output.id = "sprint7-accessibility-result";
        output.textContent = JSON.stringify(result);
        document.body.appendChild(output);
    }});
}})();
</script>
"""


def inject_accessibility(path: Path, theme: str, zoom: int) -> None:
    document = path.read_text(encoding="utf-8")
    path.write_text(
        document.replace("</body>", f"{accessibility_script(theme, zoom)}</body>", 1),
        encoding="utf-8",
    )


def run_accessibility_audit(
    browser: Path,
    fixture: Path,
    profile: Path,
    audit: dict,
) -> dict:
    width, height = (dimension // audit["zoom"] for dimension in audit["size"])
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        f"--window-size={width},{height}",
        f"--user-data-dir={windows_path(profile)}",
        "--virtual-time-budget=4000",
        "--dump-dom",
        file_url(fixture),
    ]
    if audit["reduced_motion"]:
        command.insert(-2, "--force-prefers-reduced-motion=reduce")
    result = subprocess.run(command, capture_output=True, timeout=70, check=False)
    document = result.stdout.decode("utf-8", errors="replace")
    match = RESULT_PATTERN.search(document)
    if result.returncode != 0 or not match:
        detail = result.stderr.decode("utf-8", errors="replace")[-1000:]
        raise RuntimeError(f"Auditoria {audit['name']} não respondeu: {detail}")
    audit_result = json.loads(html.unescape(match.group(1)))
    audit_result["name"] = audit["name"]
    audit_result["requested_viewport"] = f"{audit['size'][0]}x{audit['size'][1]}"
    return audit_result


def write_markdown(report: dict) -> None:
    lines = [
        "# Validação Visual e de Acessibilidade — Sprint 7",
        "",
        f"- Data: {report['generated_at']}",
        f"- Navegador: {report['browser']['name']} {report['browser']['version']}",
        f"- Sistema: {report['system']}",
        "- Dados: exclusivamente fictícios e sanitizados.",
        f"- Tolerância visual: {DIFFERENCE_LIMIT_PERCENT:.2f}% dos pixels.",
        "",
        "## Regressão visual",
        "",
        "| Tela | Tema | Resolução | Diferença | Resultado |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for capture in report["visual"]:
        lines.append(
            f"| {capture['name']} | {capture['theme']} | {capture['resolution']} | "
            f"{capture['difference_percent']:.4f}% | "
            f"{'Aprovado' if capture['passed'] else 'Falhou'} |"
        )
    lines.extend(
        [
            "",
            "## Acessibilidade e responsividade",
            "",
            "| Cenário | Viewport | Zoom | Violações críticas/sérias | Resultado |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for audit in report["accessibility"]:
        blocking = sum(item["severity"] in {"critical", "serious"} for item in audit["violations"])
        lines.append(
            f"| {audit['name']} | {audit['requested_viewport']} | {audit['zoom'] * 100}% | "
            f"{blocking} | {'Aprovado' if audit['passed'] else 'Falhou'} |"
        )
    lines.extend(
        [
            "",
            "Baselines nunca são alteradas durante a validação comum. Para aprovar",
            "mudanças revisadas, execute explicitamente:",
            "",
            "```bash",
            "python scripts/validate_visual_accessibility.py --update-baselines",
            "```",
            "",
            "Diferenças reprovadas ficam em `artifacts/visual-accessibility/diffs/`.",
            "",
        ]
    )
    RESULT_MARKDOWN.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual-only", action="store_true")
    parser.add_argument("--accessibility-only", action="store_true")
    parser.add_argument("--update-baselines", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.visual_only and args.accessibility_only:
        raise SystemExit("Escolha apenas --visual-only ou --accessibility-only.")

    run_visual = not args.accessibility_only
    run_accessibility = not args.visual_only
    browser = find_browser()
    artifacts = ROOT / "artifacts" / "visual-accessibility"
    current_dir = artifacts / "current"
    diff_dir = artifacts / "diffs"
    current_dir.mkdir(parents=True, exist_ok=True)
    diff_dir.mkdir(parents=True, exist_ok=True)
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    visual_results = []
    accessibility_results = []

    with tempfile.TemporaryDirectory(prefix=".sprint7-", dir=ROOT) as temp:
        temp_dir = Path(temp)
        if run_visual:
            for index, capture in enumerate(CAPTURES):
                fixture = temp_dir / f"{capture['name']}.html"
                current = current_dir / f"{capture['name']}.png"
                baseline = BASELINE_DIR / current.name
                diff = diff_dir / current.name
                render_fixture(fixture, capture["records"])
                inject_capture_state(
                    fixture,
                    theme=capture["theme"],
                    section=capture["section"],
                    modal=capture["modal"],
                )
                capture_screenshot(
                    browser,
                    fixture,
                    current,
                    temp_dir / f"profile-visual-{index}",
                    capture["size"],
                )
                if args.update_baselines:
                    shutil.copy2(current, baseline)
                    comparison = {
                        "passed": True,
                        "difference_percent": 0.0,
                        "reason": "baseline atualizada explicitamente",
                    }
                elif not baseline.exists():
                    comparison = {
                        "passed": False,
                        "difference_percent": 100.0,
                        "reason": "baseline ausente; revise e use --update-baselines",
                    }
                else:
                    comparison = compare_images(current, baseline, diff)
                visual_results.append(
                    {
                        **comparison,
                        "name": capture["name"],
                        "theme": capture["theme"],
                        "resolution": f"{capture['size'][0]}x{capture['size'][1]}",
                        "records": capture["records"],
                        "baseline": str(baseline.relative_to(ROOT)),
                    }
                )
                print(
                    f"[{'OK' if comparison['passed'] else 'FALHA'}] visual "
                    f"{capture['name']} ({comparison['difference_percent']:.4f}%)"
                )

        if run_accessibility:
            for index, audit in enumerate(AUDITS):
                fixture = temp_dir / f"a11y-{audit['name']}.html"
                render_fixture(fixture, 40)
                inject_accessibility(fixture, audit["theme"], audit["zoom"])
                result = run_accessibility_audit(
                    browser,
                    fixture,
                    temp_dir / f"profile-a11y-{index}",
                    audit,
                )
                accessibility_results.append(result)
                print(
                    f"[{'OK' if result['passed'] else 'FALHA'}] acessibilidade "
                    f"{audit['name']} ({len(result['violations'])} avisos)"
                )

    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "browser": {
            "name": "Microsoft Edge" if "Edge" in str(browser) else "Google Chrome",
            "version": browser_version(browser),
            "executable": browser.name,
        },
        "system": f"Windows 11 / WSL ({platform.release()})",
        "visual": visual_results,
        "accessibility": accessibility_results,
        "passed": (
            all(item["passed"] for item in visual_results)
            and all(item["passed"] for item in accessibility_results)
        ),
    }
    RESULT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report)
    print(f"Resultado: {RESULT_JSON}")
    print(f"Resumo: {RESULT_MARKDOWN}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
