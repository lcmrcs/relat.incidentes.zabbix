import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "validate_html_browser.py"
SPEC = importlib.util.spec_from_file_location("validate_html_browser", SCRIPT_PATH)
browser_validation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = browser_validation
SPEC.loader.exec_module(browser_validation)


class BrowserValidationTests(unittest.TestCase):
    def test_fake_incidents_are_deterministic_and_sanitized(self):
        first = browser_validation.fake_incident(7)
        repeated = browser_validation.fake_incident(7)

        self.assertEqual(first, repeated)
        self.assertEqual(first["host"], "HOST-FICTICIO-00007")
        self.assertNotIn("token", str(first).lower())
        self.assertNotIn("password", str(first).lower())

    def test_fixture_is_self_contained_and_does_not_call_zabbix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "fixture.html"
            browser_validation.render_fixture(output, 10)
            document = output.read_text(encoding="utf-8")

        self.assertIn('id="incident-data"', document)
        self.assertIn("HOST-FICTICIO-00009", document)
        self.assertNotIn('src="http', document)
        self.assertNotIn('href="http', document)

    def test_validation_injection_records_objective_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "fixture.html"
            browser_validation.render_fixture(output, 1)
            browser_validation.inject_validation(output, 1, full_validation=True)
            document = output.read_text(encoding="utf-8")

        self.assertIn("sprint6-browser-result", document)
        self.assertIn("Payload perdeu registros.", document)
        self.assertIn("CSV não contém todos os registros.", document)
        self.assertIn("Proteção de impressão volumosa", document)

    def test_browser_lifecycle_is_isolated_and_closed(self):
        source = SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("playwright.chromium.launch(", source)
        self.assertIn("browser_process.new_context(", source)
        self.assertIn("page.close()", source)
        self.assertIn("context.close()", source)
        self.assertIn("browser_process.close()", source)
        self.assertIn("playwright.stop()", source)
        self.assertIn("browser_watchdog_timeout", source)

    def test_sensitive_diagnostics_are_sanitized(self):
        diagnostic = browser_validation.sanitize_diagnostic(
            "token=secret https://private.invalid 10.20.30.40"
        )

        self.assertNotIn("secret", diagnostic)
        self.assertNotIn("private.invalid", diagnostic)
        self.assertNotIn("10.20.30.40", diagnostic)

    def test_timeout_still_writes_partial_json_and_markdown(self):
        completed_result = {
            "passed": True,
            "failures": [],
            "console_messages": [],
            "metrics": {"load_ms": 1},
        }

        def fake_render(path, _count):
            path.write_text("<html><body></body></html>", encoding="utf-8")

        def fake_browser(_browser, path, _profile, _timeout, _screenshot):
            if "report-10-" in path.name:
                raise browser_validation.BrowserValidationError(
                    "Watchdog encerrou o Edge.",
                    {
                        "error_type": "browser_watchdog_timeout",
                        "console": ["warning seguro"],
                        "stderr": "mensagem segura",
                        "browser_status": "closed",
                        "process_status": "closed",
                    },
                )
            return completed_result, {
                "browser_status": "closed",
                "process_status": "closed",
                "duration_ms": 1,
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "partial.json"
            args = argparse.Namespace(output=output, scenarios=[0, 10, 20000], timeout=1)
            with (
                patch.object(browser_validation, "parse_args", return_value=args),
                patch.object(
                    browser_validation,
                    "find_browser",
                    return_value=Path("msedge.exe"),
                ),
                patch.object(browser_validation, "browser_version", return_value="test"),
                patch.object(browser_validation, "render_fixture", side_effect=fake_render),
                patch.object(
                    browser_validation,
                    "validate_native_pdf",
                    return_value={"passed": True, "size_bytes": 1001},
                ),
                patch.object(browser_validation, "run_browser", side_effect=fake_browser),
            ):
                return_code = browser_validation.main()

            report = json.loads(output.read_text(encoding="utf-8"))
            markdown = output.with_suffix(".md").read_text(encoding="utf-8")

        self.assertEqual(return_code, 1)
        self.assertEqual(report["diagnostics"]["status"], "failed")
        self.assertEqual(report["diagnostics"]["last_scenario_started"], 10)
        self.assertEqual(report["scenarios"][0]["runs_completed"], 1)
        self.assertEqual(report["scenarios"][1]["runs_completed"], 0)
        self.assertEqual(
            report["diagnostics"]["error_type"],
            "browser_watchdog_timeout",
        )
        self.assertIn("Estado da execução: failed", markdown)


if __name__ == "__main__":
    unittest.main()
