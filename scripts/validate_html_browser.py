#!/usr/bin/env python3
"""Valida o relatório HTML autocontido em um navegador Chromium real.

O script usa Edge ou Chrome já instalado no Windows. Os cenários são totalmente
fictícios e não executam nenhuma chamada à API do Zabbix.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "zabbix-report"
sys.path.insert(0, str(REPORT_DIR))

from executive_summary import build_executive_summary  # noqa: E402
from summary import build_report_summary  # noqa: E402
from zabbix_report import render_html  # noqa: E402


def browser_candidates(
    system_name: str | None = None,
    environment: dict[str, str] | None = None,
) -> tuple[Path, ...]:
    """Retorna navegadores locais tanto no Windows nativo quanto no WSL."""

    system_name = system_name or os.name
    environment = environment or os.environ
    if system_name == "nt":
        roots = [
            environment.get("PROGRAMFILES(X86)"),
            environment.get("PROGRAMFILES"),
            environment.get("LOCALAPPDATA"),
        ]
        candidates = []
        for root in filter(None, roots):
            base = Path(root)
            candidates.extend(
                (
                    base / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                    base / "Google" / "Chrome" / "Application" / "chrome.exe",
                )
            )
        return tuple(candidates)

    return (
        Path("/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe"),
        Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    )


RESULT_PATTERN = re.compile(
    r'<pre id="sprint6-browser-result"[^>]*>(.*?)</pre>',
    re.DOTALL,
)
DEFAULT_SCENARIOS = (0, 10, 7171, 20000)
MAX_DIAGNOSTIC_TEXT = 4000


class BrowserValidationError(RuntimeError):
    """Falha controlada com contexto seguro da sessão isolada do navegador."""

    def __init__(self, message: str, diagnostic: dict):
        super().__init__(message)
        self.diagnostic = diagnostic


def sanitize_diagnostic(value: object) -> str:
    """Reduz mensagens do navegador sem expor URLs, IPs ou credenciais."""

    text = str(value or "")
    text = re.sub(r"https?://\S+", "[URL_REMOVIDA]", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "[IP_REMOVIDO]",
        text,
    )
    text = re.sub(
        r"(?i)\b(token|password|senha|authorization)\b\s*[:=]\s*\S+",
        r"\1=[VALOR_REMOVIDO]",
        text,
    )
    return text[-MAX_DIAGNOSTIC_TEXT:]


def fake_incident(index: int) -> dict:
    """Cria um incidente determinístico sem qualquer dado de ambiente real."""

    resolved = index % 3 == 0
    duration = ((index % 180) + 1) * 3600
    unit_index = index % 5
    equipment = ("Mikrotik", "Switch", "Access Point")[index % 3]
    severity = ("Informação", "Atenção", "Média", "Alta", "Desastre")[index % 5]
    return {
        "date": f"{(index % 28) + 1:02d}/07/2026 {index % 24:02d}:{index % 60:02d}",
        "resolved_at": "27/07/2026 12:00" if resolved else "",
        "status": "Resolvido" if resolved else "Aberto",
        "unit_code": str(1000 + unit_index),
        "unit": f"Unidade Escolar {unit_index}",
        "host": f"HOST-FICTICIO-{index:05d}",
        "equipment": equipment,
        "incident": f"Falha fictícia controlada {index:05d}",
        "incident_type": "Indisponibilidade",
        "severity": severity,
        "timestamp": 1785146400 - duration,
        "age_seconds": 0 if resolved else duration,
        "age_label": "-" if resolved else f"{duration // 3600}h",
        "duration_seconds": duration,
        "duration_label": f"{duration // 3600}h",
        "open_age_seconds": 0 if resolved else duration,
        "open_age_label": "-" if resolved else f"{duration // 3600}h",
        "eventid": str(9_000_000 + index),
        "incident_key": f"host-ficticio-{index:05d}|indisponibilidade",
    }


def windows_path(path: Path) -> str:
    text = str(path.resolve())
    if os.name == "nt":
        return text
    if text.startswith("/mnt/") and len(text) > 6:
        drive = text[5].upper()
        return f"{drive}:\\" + text[7:].replace("/", "\\")
    return text


def file_url(path: Path) -> str:
    return "file:///" + windows_path(path).replace("\\", "/")


def find_browser() -> Path:
    for candidate in browser_candidates():
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Microsoft Edge ou Google Chrome não encontrado no Windows.")


def browser_version(browser: Path) -> str:
    command = (
        "$item = Get-Item -LiteralPath "
        f"'{windows_path(browser).replace(chr(39), chr(39) * 2)}'; "
        "$item.VersionInfo.ProductVersion"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return result.stdout.strip() or "não identificada"


def render_fixture(path: Path, count: int, include_executive_summary: bool = False) -> None:
    incidents = [fake_incident(index) for index in range(count)]
    special = [fake_incident(80_000), fake_incident(80_001)]
    summary = build_report_summary(incidents)
    integrity = {
        "received": count,
        "processed": count,
        "adjusted": 0,
        "discarded": 0,
        "warning_count": 0,
        "level": "valid",
        "label": "Dados validados",
        "issues": [],
    }
    executive = (
        build_executive_summary(
            summary,
            None,
            integrity,
            "27/07/2026 12:00",
            "período fictício da Sprint 12",
        )
        if include_executive_summary
        else None
    )
    render_html(
        path,
        "27/07/2026 12:00",
        "período fictício da Sprint 6",
        incidents,
        summary,
        special,
        build_report_summary(special),
        special[:1],
        build_report_summary(special[:1]),
        "https://example.invalid",
        integrity,
        executive_summary=executive,
    )


def validation_script(expected: int, full_validation: bool) -> str:
    return f"""
<script>
(() => {{
    if (window !== window.top) {{
        window.addEventListener("load", () => {{
            window.parent.postMessage(
                {{
                    type: "sprint6-theme-probe",
                    dark: document.body.classList.contains("theme-dark"),
                }},
                "*"
            );
        }});
        return;
    }}

    const EXPECTED = {expected};
    const FULL = {str(full_validation).lower()};
    const failures = [];
    const warnings = [];
    const consoleMessages = [];
    const started = performance.now();
    let capturedBlob = null;
    let printRows = null;
    let alertMessage = "";

    window.addEventListener("error", event => failures.push(`JavaScript: ${{event.message}}`));
    window.addEventListener(
        "unhandledrejection",
        event => failures.push(`Promise: ${{String(event.reason)}}`)
    );
    for (const level of ["error", "warn"]) {{
        const original = console[level].bind(console);
        console[level] = (...args) => {{
            consoleMessages.push(`${{level}}: ${{args.map(String).join(" ")}}`);
            original(...args);
        }};
    }}

    const originalCreateObjectURL = URL.createObjectURL.bind(URL);
    URL.createObjectURL = blob => {{
        capturedBlob = blob;
        return originalCreateObjectURL(blob);
    }};
    HTMLAnchorElement.prototype.click = function() {{
        if (!this.download) {{
            HTMLElement.prototype.click.call(this);
        }}
    }};
    window.alert = message => {{ alertMessage = String(message); }};
    window.print = () => {{
        window.dispatchEvent(new Event("beforeprint"));
        printRows = document.querySelectorAll("#incidents-table tbody tr").length;
        window.dispatchEvent(new Event("afterprint"));
    }};

    function assert(condition, message) {{
        if (!condition) failures.push(message);
    }}
    const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
    const click = selector => {{
        const element = document.querySelector(selector);
        assert(Boolean(element), `Elemento ausente: ${{selector}}`);
        element?.click();
        return element;
    }};
    const rowCount = () => document.querySelectorAll("#incidents-table tbody tr").length;
    const statusText = () => document.querySelector("[data-page-status]")?.textContent || "";
    const timed = async callback => {{
        const begin = performance.now();
        await callback();
        return performance.now() - begin;
    }};

    window.addEventListener("load", async () => {{
        await wait(180);
        const metrics = {{}};
        metrics.initial_elements = document.querySelectorAll("*").length;
        const payload = JSON.parse(
            document.getElementById("incident-data")?.textContent || "[]"
        );
        assert(payload.length === EXPECTED, "Payload perdeu registros.");
        assert(
            document.querySelectorAll("[data-details]").length === Math.min(EXPECTED, 100),
            "DOM inicial fora do limite esperado."
        );

        if (EXPECTED === 0) {{
            assert(Boolean(document.querySelector(".empty-state")), "Estado vazio ausente.");
        }} else {{
            assert(statusText().includes(`${{EXPECTED}} registros`), "Contador global divergente.");

            const wasDark = document.body.classList.contains("theme-dark");
            click("[data-theme-toggle]");
            assert(
                document.body.classList.contains("theme-dark") !== wasDark,
                "Alternância de tema falhou."
            );
            const expectedPersistedDark = !wasDark;
            assert(
                localStorage.getItem("zabbix-report-theme") === (wasDark ? "light" : "dark"),
                "Persistência do tema falhou."
            );
            const persistedTheme = await new Promise(resolve => {{
                const frame = document.createElement("iframe");
                const timeout = window.setTimeout(() => resolve(null), 2500);
                const listener = event => {{
                    if (event.data?.type !== "sprint6-theme-probe") return;
                    window.clearTimeout(timeout);
                    window.removeEventListener("message", listener);
                    frame.remove();
                    resolve(event.data.dark);
                }};
                window.addEventListener("message", listener);
                frame.hidden = true;
                frame.src = `${{location.href.split("#")[0]}}#theme-probe`;
                document.body.appendChild(frame);
            }});
            assert(
                persistedTheme === expectedPersistedDark,
                "Tema não persistiu após nova carga do relatório."
            );
            click("[data-theme-toggle]");

            if (EXPECTED > 100) {{
                metrics.page_change_ms = await timed(async () => {{
                    click("[data-page-next]");
                    await wait(0);
                }});
                assert(statusText().includes("Página 2"), "Próxima página falhou.");

                const sizeControl = document.querySelector("[data-page-size]");
                sizeControl.value = "250";
                sizeControl.dispatchEvent(new Event("change", {{ bubbles: true }}));
                assert(rowCount() === Math.min(EXPECTED, 250), "Alteração para 250 linhas falhou.");
                assert(statusText().includes("Página 1"), "Troca de tamanho não voltou à página 1.");
            }}

            metrics.search_ms = await timed(async () => {{
                const search = document.getElementById("global-search");
                search.value = `HOST-FICTICIO-${{String(EXPECTED - 1).padStart(5, "0")}}`;
                search.dispatchEvent(new Event("input", {{ bubbles: true }}));
                await wait(180);
            }});
            assert(statusText().includes("1 registros"), "Busca não alcançou todos os dados.");

            click("#clear-filters");
            assert(statusText().includes(`${{EXPECTED}} registros`), "Limpeza de filtros falhou.");

            metrics.filter_ms = await timed(async () => {{
                click('[data-status-filter="Aberto"]');
                click('[data-equipment-filter="Switch"]');
                await wait(0);
            }});
            const combinedCount = payload.filter(
                item => item[2] === "Aberto" && item[6] === "Switch"
            ).length;
            assert(
                statusText().includes(`${{combinedCount}} registros`),
                "Combinação de filtros não considerou o conjunto completo."
            );
            click("#clear-filters");

            metrics.sort_ms = await timed(async () => {{
                click('[data-sort-key="unitCode"]');
                await wait(0);
            }});
            assert(Boolean(document.querySelector('[data-sort-key="unitCode"].active')), "Ordenação falhou.");

            click("[data-details]");
            assert(document.getElementById("incident-dialog")?.open, "Modal do incidente não abriu.");
            click("[data-modal-close]");
            assert(!document.getElementById("incident-dialog")?.open, "Modal do incidente não fechou.");

            for (const [openSelector, dialogId, closeSelector] of [
                ["[data-zabbix-open]", "zabbix-dialog", "[data-zabbix-close]"],
                ["[data-confea-open]", "confea-dialog", "[data-confea-close]"],
                ["[data-integrity-open]", "integrity-dialog", "[data-integrity-close]"],
            ]) {{
                click(openSelector);
                assert(document.getElementById(dialogId)?.open, `Modal ${{dialogId}} não abriu.`);
                click(closeSelector);
            }}

            if (FULL) {{
                click("#download-filtered");
                await wait(40);
                const csvText = capturedBlob ? await capturedBlob.text() : "";
                const csvLines = csvText.split(/\\r?\\n/).filter(Boolean).length;
                assert(csvLines === EXPECTED + 1, "CSV não contém todos os registros.");

                const pageBeforePrint = statusText();
                click("#export-pdf");
                await wait(260);
                if (EXPECTED > 5000) {{
                    assert(
                        alertMessage.includes("Baixar CSV"),
                        "Proteção de impressão volumosa não foi informada."
                    );
                    assert(printRows === null, "Impressão volumosa não foi interrompida.");
                }} else {{
                    assert(printRows === EXPECTED, "Impressão não expandiu todos os registros.");
                    assert(statusText() === pageBeforePrint, "Página não foi restaurada após impressão.");
                    assert(
                        !document.body.classList.contains("pdf-exporting"),
                        "Interface não foi restaurada após impressão."
                    );
                }}
            }}
        }}

        const navigation = performance.getEntriesByType("navigation")[0];
        metrics.dom_content_loaded_ms = navigation?.domContentLoadedEventEnd || 0;
        metrics.load_ms = navigation?.loadEventEnd || performance.now();
        metrics.validation_ms = performance.now() - started;
        metrics.html_bytes = new Blob([document.documentElement.outerHTML]).size;
        if (performance.memory) {{
            metrics.heap_used_bytes = performance.memory.usedJSHeapSize;
        }}

        const result = {{
            records: EXPECTED,
            passed: failures.length === 0,
            failures,
            warnings,
            console_messages: consoleMessages,
            metrics,
            final_rows: rowCount(),
            offline_protocol: location.protocol,
        }};
        const output = document.createElement("pre");
        output.id = "sprint6-browser-result";
        output.textContent = JSON.stringify(result);
        document.body.appendChild(output);
        document.documentElement.dataset.sprint6Complete = "true";
    }});
}})();
</script>
"""


def inject_validation(path: Path, expected: int, full_validation: bool) -> None:
    document = path.read_text(encoding="utf-8")
    script = validation_script(expected, full_validation)
    path.write_text(document.replace("</body>", f"{script}</body>", 1), encoding="utf-8")


def run_browser(
    browser: Path,
    path: Path,
    profile: Path,
    timeout: int,
    screenshot: Path | None = None,
) -> tuple[dict, dict]:
    """Executa uma única validação em um processo/contexto isolado do Edge."""

    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    started = time.monotonic()
    lifecycle = {
        "driver_status": "starting",
        "browser_status": "not_started",
        "process_status": "not_started",
        "page_status": "not_started",
        "stderr": "indisponível: processo gerenciado pelo Playwright",
        "console": [],
        "screenshot": "",
    }
    playwright = None
    browser_process = None
    context = None
    page = None
    pending_error: BrowserValidationError | None = None
    result_data: dict | None = None

    try:
        playwright = sync_playwright().start()
        lifecycle["driver_status"] = "running"
        profile.mkdir(parents=True, exist_ok=True)
        browser_process = playwright.chromium.launch(
            executable_path=str(browser),
            headless=True,
            timeout=timeout * 1000,
            args=[
                "--disable-gpu",
                "--no-first-run",
                "--disable-background-networking",
                "--enable-precise-memory-info",
            ],
        )
        lifecycle["browser_status"] = "running"
        lifecycle["process_status"] = "managed_by_playwright"
        context = browser_process.new_context(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=1,
        )
        page = context.new_page()
        lifecycle["page_status"] = "loading"
        page.on(
            "console",
            lambda message: lifecycle["console"].append(
                sanitize_diagnostic(f"{message.type}: {message.text}")
            ),
        )
        page.goto(path.resolve().as_uri(), wait_until="load", timeout=timeout * 1000)
        lifecycle["page_status"] = "validating"
        page.wait_for_function(
            "() => document.documentElement.dataset.sprint6Complete === 'true'",
            timeout=timeout * 1000,
        )
        raw_result = page.locator("#sprint6-browser-result").text_content()
        if not raw_result:
            raise BrowserValidationError(
                "O navegador concluiu a página sem devolver o resultado da validação.",
                lifecycle.copy(),
            )
        result_data = json.loads(html.unescape(raw_result))
        lifecycle["page_status"] = "completed"
    except PlaywrightTimeoutError as error:
        lifecycle["page_status"] = "timeout"
        lifecycle["error_type"] = "browser_watchdog_timeout"
        lifecycle["error"] = sanitize_diagnostic(error)
        pending_error = BrowserValidationError(
            f"Watchdog encerrou o Edge após {timeout}s sem conclusão do cenário.",
            lifecycle,
        )
    except BrowserValidationError as error:
        lifecycle.update(error.diagnostic)
        lifecycle.setdefault("error_type", "browser_validation_error")
        lifecycle["error"] = sanitize_diagnostic(error)
        pending_error = BrowserValidationError(str(error), lifecycle)
    except Exception as error:  # noqa: BLE001 - diagnóstico seguro antes de propagar
        lifecycle["error_type"] = type(error).__name__
        lifecycle["error"] = sanitize_diagnostic(error)
        pending_error = BrowserValidationError(
            "Falha controlada durante a sessão isolada do navegador.",
            lifecycle,
        )
    finally:
        if pending_error and page is not None and screenshot is not None:
            try:
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot), full_page=False, timeout=5000)
                lifecycle["screenshot"] = str(screenshot.name)
            except Exception as error:  # noqa: BLE001 - melhor esforço diagnóstico
                lifecycle["screenshot_error"] = sanitize_diagnostic(error)
        if page is not None:
            try:
                page.close()
            except Exception as error:  # noqa: BLE001
                lifecycle["page_close_error"] = sanitize_diagnostic(error)
        lifecycle["page_status"] = (
            "closed" if "page_close_error" not in lifecycle else "close_failed"
        )
        if context is not None:
            try:
                context.close()
            except Exception as error:  # noqa: BLE001
                lifecycle["context_close_error"] = sanitize_diagnostic(error)
        if browser_process is not None:
            try:
                browser_process.close()
            except Exception as error:  # noqa: BLE001
                lifecycle["browser_close_error"] = sanitize_diagnostic(error)
        lifecycle["browser_status"] = (
            "closed" if "browser_close_error" not in lifecycle else "close_failed"
        )
        lifecycle["process_status"] = lifecycle["browser_status"]
        if playwright is not None:
            try:
                playwright.stop()
            except Exception as error:  # noqa: BLE001
                lifecycle["driver_close_error"] = sanitize_diagnostic(error)
        lifecycle["driver_status"] = "closed"
        lifecycle["duration_ms"] = round((time.monotonic() - started) * 1000, 3)

    if pending_error:
        pending_error.diagnostic = lifecycle
        raise pending_error
    if result_data is None:
        raise BrowserValidationError(
            "Sessão encerrada sem resultado do navegador.",
            lifecycle,
        )
    return result_data, lifecycle


def median_metrics(runs: list[dict]) -> dict:
    names = sorted({name for run in runs for name in run["metrics"]})
    return {
        name: round(
            statistics.median(
                float(run["metrics"][name]) for run in runs if name in run["metrics"]
            ),
            3,
        )
        for name in names
    }


def validate_native_pdf(browser: Path, html_path: Path, profile: Path, output: Path) -> dict:
    result = subprocess.run(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--window-size=1600,1000",
            f"--user-data-dir={windows_path(profile)}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={windows_path(output)}",
            file_url(html_path),
        ],
        capture_output=True,
        timeout=90,
        check=False,
    )
    valid = (
        result.returncode == 0
        and output.exists()
        and output.stat().st_size > 1000
        and output.read_bytes()[:4] == b"%PDF"
    )
    return {
        "passed": valid,
        "size_bytes": output.stat().st_size if output.exists() else 0,
    }


def write_markdown(path: Path, report: dict) -> None:
    lines = [
        "# Validação da Sprint 6 em navegador real",
        "",
        f"- Data: {report['generated_at']}",
        f"- Navegador: {report['browser']['name']} {report['browser']['version']}",
        f"- Sistema: {report['system']}",
        f"- Resolução: {report['viewport']}",
        "- Abertura: arquivo HTML autocontido local (`file://`), modo headless.",
        "- Dados: exclusivamente fictícios; nenhuma conexão com Zabbix.",
        (
            "- Impressão nativa: "
            f"{'aprovada' if report['native_pdf']['passed'] else 'falhou'} "
            f"({report['native_pdf']['size_bytes'] / 1024:.1f} KB)."
        ),
        "",
        "| Registros | Execuções | Resultado | HTML | DOM inicial | Carregamento | Busca | Filtro | Página | Ordenação |",
        "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scenario in report["scenarios"]:
        metrics = scenario.get("median_metrics", {})
        lines.append(
            f"| {scenario['records']:,} | {scenario.get('runs_completed', scenario['runs'])}"
            f"/{scenario['runs']} | "
            f"{'Aprovado' if scenario['passed'] else 'Falhou'} | "
            f"{metrics.get('html_bytes', 0) / 1024 / 1024:.2f} MB | "
            f"{metrics.get('initial_elements', 0):.0f} | "
            f"{metrics.get('load_ms', 0):.1f} ms | "
            f"{metrics.get('search_ms', 0):.1f} ms | "
            f"{metrics.get('filter_ms', 0):.1f} ms | "
            f"{metrics.get('page_change_ms', 0):.1f} ms | "
            f"{metrics.get('sort_ms', 0):.1f} ms |"
        )
    lines.extend(
        [
            "",
            f"- Último cenário iniciado: {report['diagnostics']['last_scenario_started']}",
            f"- Última etapa concluída: {report['diagnostics']['last_stage_completed']}",
            f"- Estado da execução: {report['diagnostics']['status']}",
            "",
            "As métricas são comparativas nesta máquina e não constituem metas universais.",
            "A impressão acima de 5.000 linhas é interrompida com orientação para o CSV completo.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_report(output: Path, report: dict) -> None:
    """Persiste resultado parcial ou final para publicação pelo CI."""

    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    write_markdown(output.with_suffix(".md"), report)


def mark_stage(report: dict, output: Path, stage: str, *, completed: bool = False) -> None:
    diagnostics = report["diagnostics"]
    diagnostics["current_stage"] = stage
    if completed:
        diagnostics["last_stage_completed"] = stage
    write_report(output, report)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "VALIDACAO_NAVEGADOR_SPRINT_6.json",
        help="Arquivo JSON de resultado.",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        type=int,
        default=list(DEFAULT_SCENARIOS),
        help="Volumes fictícios a validar.",
    )
    parser.add_argument("--timeout", type=int, default=90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    browser = find_browser()
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "browser": {
            "name": "Microsoft Edge" if "Edge" in str(browser) else "Google Chrome",
            "version": browser_version(browser),
            "executable": browser.name,
        },
        "system": f"Windows 11 / WSL ({platform.release()})",
        "viewport": "1600x1000",
        "native_pdf": {"passed": False, "size_bytes": 0},
        "scenarios": [],
        "diagnostics": {
            "status": "running",
            "last_scenario_started": None,
            "last_stage_completed": "initialization",
            "current_stage": "initialization",
            "error_type": "",
            "error": "",
        },
        "passed": False,
    }
    write_report(args.output, report)
    return_code = 1

    try:
        with tempfile.TemporaryDirectory(prefix=".sprint6-browser-", dir=ROOT) as temp:
            temp_dir = Path(temp)
            diagnostics_dir = args.output.parent / "artifacts" / "html-browser"
            fatal_error = False
            for count in args.scenarios:
                run_count = 3 if count == 7171 else 1
                scenario_started = time.monotonic()
                scenario = {
                    "records": count,
                    "runs": run_count,
                    "runs_completed": 0,
                    "passed": False,
                    "median_metrics": {},
                    "failures": [],
                    "console_messages": [],
                    "run_diagnostics": [],
                    "stage_durations_ms": {},
                    "duration_ms": 0,
                }
                report["scenarios"].append(scenario)
                report["diagnostics"]["last_scenario_started"] = count
                mark_stage(report, args.output, f"scenario_{count}_started")
                runs = []
                for run_index in range(run_count):
                    fixture = temp_dir / f"report-{count}-{run_index}.html"
                    profile = temp_dir / f"profile-{count}-{run_index}"
                    stage_started = time.monotonic()
                    render_fixture(fixture, count)
                    scenario["stage_durations_ms"][f"render_{run_index + 1}"] = round(
                        (time.monotonic() - stage_started) * 1000,
                        3,
                    )
                    mark_stage(
                        report,
                        args.output,
                        f"scenario_{count}_render_{run_index + 1}",
                        completed=True,
                    )
                    if count == 10 and run_index == 0:
                        stage_started = time.monotonic()
                        report["native_pdf"] = validate_native_pdf(
                            browser,
                            fixture,
                            temp_dir / "profile-native-pdf",
                            temp_dir / "native-print.pdf",
                        )
                        scenario["stage_durations_ms"]["native_pdf"] = round(
                            (time.monotonic() - stage_started) * 1000,
                            3,
                        )
                        mark_stage(report, args.output, "native_pdf", completed=True)
                    inject_validation(fixture, count, full_validation=run_index == 0)
                    mark_stage(
                        report,
                        args.output,
                        f"scenario_{count}_browser_{run_index + 1}_started",
                    )
                    try:
                        result, lifecycle = run_browser(
                            browser,
                            fixture,
                            profile,
                            args.timeout,
                            diagnostics_dir / f"scenario-{count}-run-{run_index + 1}.png",
                        )
                    except BrowserValidationError as error:
                        scenario["failures"].append(str(error))
                        scenario["run_diagnostics"].append(error.diagnostic)
                        scenario["console_messages"].extend(error.diagnostic.get("console", []))
                        scenario["duration_ms"] = round(
                            (time.monotonic() - scenario_started) * 1000,
                            3,
                        )
                        report["diagnostics"]["status"] = "failed"
                        report["diagnostics"]["error_type"] = error.diagnostic.get(
                            "error_type", type(error).__name__
                        )
                        report["diagnostics"]["error"] = sanitize_diagnostic(error)
                        write_report(args.output, report)
                        fatal_error = True
                        break
                    runs.append(result)
                    scenario["runs_completed"] += 1
                    scenario["run_diagnostics"].append(lifecycle)
                    scenario["console_messages"].extend(result["console_messages"])
                    scenario["failures"].extend(result["failures"])
                    mark_stage(
                        report,
                        args.output,
                        f"scenario_{count}_browser_{run_index + 1}",
                        completed=True,
                    )
                    print(
                        f"[{'OK' if result['passed'] else 'FALHA'}] "
                        f"{count} registros, execução {run_index + 1}/{run_count}"
                    )
                if fatal_error:
                    break
                scenario.update(
                    {
                        "passed": all(run["passed"] for run in runs),
                        "median_metrics": median_metrics(runs),
                        "duration_ms": round(
                            (time.monotonic() - scenario_started) * 1000,
                            3,
                        ),
                    }
                )
                mark_stage(
                    report,
                    args.output,
                    f"scenario_{count}",
                    completed=True,
                )
            if fatal_error:
                return_code = 1
            else:
                report["passed"] = (
                    all(scenario["passed"] for scenario in report["scenarios"])
                    and report["native_pdf"]["passed"]
                )
                report["diagnostics"]["status"] = "completed"
                report["diagnostics"]["last_stage_completed"] = "all_scenarios"
                report["diagnostics"]["current_stage"] = "completed"
                return_code = 0 if report["passed"] else 1
    except Exception as error:  # noqa: BLE001 - garante diagnóstico publicável
        report["diagnostics"]["status"] = "failed"
        report["diagnostics"]["error_type"] = type(error).__name__
        report["diagnostics"]["error"] = sanitize_diagnostic(error)
        return_code = 1
    finally:
        write_report(args.output, report)

    print(f"Resultado JSON: {args.output}")
    print(f"Resumo Markdown: {args.output.with_suffix('.md')}")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
