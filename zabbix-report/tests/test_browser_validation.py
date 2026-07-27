import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
