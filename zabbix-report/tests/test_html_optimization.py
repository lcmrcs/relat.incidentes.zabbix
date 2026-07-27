import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:
    PlaywrightError = RuntimeError
    sync_playwright = None

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from summary import build_report_summary  # noqa: E402
from zabbix_report import build_html_incident_payload, render_html  # noqa: E402


def fake_incident(index):
    resolved = index % 3 == 0
    duration = (index + 1) * 60
    return {
        "date": f"{(index % 28) + 1:02d}/07/2026 08:00",
        "resolved_at": "27/07/2026 09:00" if resolved else "",
        "status": "Resolvido" if resolved else "Aberto",
        "unit_code": str(1000 + index % 5),
        "unit": f"Unidade Escolar {index % 5}",
        "host": f"HOST-{index}",
        "equipment": "Switch" if index % 2 else "Mikrotik",
        "incident": f"Falha fictícia {index}",
        "incident_type": "Indisponibilidade",
        "severity": "Alta" if index % 2 else "Média",
        "timestamp": 1785146400 - duration,
        "age_seconds": 0 if resolved else duration,
        "age_label": f"{duration // 60}min",
        "duration_seconds": duration,
        "duration_label": f"{duration // 60}min",
        "open_age_seconds": 0 if resolved else duration,
        "open_age_label": "-" if resolved else f"{duration // 60}min",
        "eventid": str(1_000_000 + index),
        "incident_key": f"host-{index}|indisponibilidade",
    }


def extract_payload(html):
    match = re.search(
        r'<script id="incident-data" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("Fonte compacta de incidentes não encontrada.")
    return json.loads(match.group(1))


class HtmlOptimizationTests(unittest.TestCase):
    def render_report(self, incidents, output):
        empty_summary = build_report_summary([])
        render_html(
            output,
            "27/07/2026 10:00",
            "período fictício",
            incidents,
            build_report_summary(incidents),
            [],
            empty_summary,
            [],
            empty_summary,
            "https://example.invalid",
        )

    def test_compact_payload_preserves_every_operational_field(self):
        incident = fake_incident(7)

        payload = build_html_incident_payload([incident])

        self.assertEqual(
            payload[0],
            [
                incident["date"],
                incident["resolved_at"],
                incident["status"],
                incident["unit_code"],
                incident["unit"],
                incident["host"],
                incident["equipment"],
                incident["incident"],
                incident["incident_type"],
                incident["severity"],
                incident["timestamp"],
                incident["age_seconds"],
                incident["age_label"],
                incident["duration_seconds"],
                incident["duration_label"],
                incident["open_age_seconds"],
                incident["open_age_label"],
                incident["eventid"],
            ],
        )

    def test_large_report_has_one_data_source_and_no_static_incident_rows(self):
        incidents = [fake_incident(index) for index in range(250)]

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.html"
            self.render_report(incidents, output)
            html = output.read_text(encoding="utf-8")

        self.assertEqual(extract_payload(html), build_html_incident_payload(incidents))
        self.assertEqual(html.count('id="incident-data"'), 1)
        self.assertNotRegex(html, r"<tr\s+data-equipment=")
        self.assertIn("let pageSize = 100;", html)
        self.assertIn('data-page-size aria-label="Quantidade de incidentes por página"', html)
        self.assertIn("renderIncidentRows(pageItems);", html)
        self.assertIn("renderIncidentRows(filteredRows);", html)
        self.assertIn("const visibleItems = getSortedRows().filter(rowMatches);", html)
        self.assertIn("const printLimit = 5000;", html)
        self.assertIn("Use Baixar CSV", html)

    def test_payload_escapes_script_termination_without_losing_data(self):
        incident = fake_incident(1)
        incident["incident"] = "</script><script>window.compromised = true</script>"

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.html"
            self.render_report([incident], output)
            html = output.read_text(encoding="utf-8")

        self.assertNotIn("</script><script>window.compromised", html)
        self.assertEqual(extract_payload(html)[0][7], incident["incident"])

    @unittest.skipIf(sync_playwright is None, "Playwright não instalado")
    def test_browser_keeps_pagination_filters_modal_and_full_csv(self):
        incidents = [fake_incident(index) for index in range(250)]

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.html"
            self.render_report(incidents, output)

            temporary_environment = {
                "TMPDIR": temp_dir,
                "TMP": temp_dir,
                "TEMP": temp_dir,
            }
            chromium_candidates = sorted(
                (Path.home() / ".cache" / "ms-playwright").glob("chromium-*/chrome-linux64/chrome")
            )
            if not chromium_candidates:
                self.skipTest("Navegador Chromium do Playwright não instalado")

            with (
                patch.dict(os.environ, temporary_environment),
                sync_playwright() as playwright,
            ):
                try:
                    browser = playwright.chromium.launch(
                        headless=True,
                        executable_path=str(chromium_candidates[-1]),
                    )
                except PlaywrightError as error:
                    self.skipTest(f"Chromium indisponível neste ambiente: {type(error).__name__}")
                page = browser.new_page(accept_downloads=True)
                page.goto(output.as_uri())
                page.wait_for_selector("#incidents-table tbody tr")

                self.assertEqual(
                    page.locator("#incidents-table tbody tr").count(),
                    100,
                )
                self.assertIn(
                    "250 registros",
                    page.locator("[data-page-status]").inner_text(),
                )

                page.locator("[data-page-next]").click()
                self.assertIn(
                    "Página 2 de 3",
                    page.locator("[data-page-status]").inner_text(),
                )

                page.locator('[data-status-filter="Aberto"]').click()
                self.assertIn(
                    "166 registros",
                    page.locator("[data-page-status]").inner_text(),
                )

                page.locator("[data-details]").first.click()
                self.assertTrue(page.locator("#incident-dialog").evaluate("el => el.open"))
                page.locator("#incident-dialog [data-dialog-close]").click()

                with page.expect_download() as download_info:
                    page.locator("#download-filtered").click()
                download = download_info.value
                csv_path = Path(temp_dir) / "filtered.csv"
                download.save_as(csv_path)
                csv_lines = csv_path.read_text(encoding="utf-8-sig").splitlines()
                self.assertEqual(len(csv_lines), 167)

                browser.close()


if __name__ == "__main__":
    unittest.main()
