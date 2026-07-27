import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import zabbix_report  # noqa: E402


def args(diagnostic=False, detailed=False):
    return SimpleNamespace(
        dias=None,
        periodo="7d",
        desde=None,
        status="todos",
        equipamento=None,
        unidade=None,
        manter_relatorios=1,
        pdf_detalhado=detailed,
        diagnostico=diagnostic,
    )


class FakeClient:
    def __init__(self, _url, _token, diagnostics=None):
        self.diagnostics = diagnostics

    def _call(self, operation):
        self.diagnostics.record_api_call(operation, 0.25)

    def get_problems(self, *_args):
        self._call("event.get")
        return []

    def get_recovery_dates(self, _problems):
        self._call("event.get")
        return {}

    def get_trigger_hosts(self, _problems):
        self._call("trigger.get")
        return {}, {}, {}

    def get_all_hosts_with_tags(self):
        self._call("host.get")
        return {}


INTEGRITY = {
    "received": 0,
    "processed": 0,
    "adjusted": 0,
    "discarded": 0,
    "warning_count": 0,
    "issues": [],
}


class GenerationObservabilityTests(unittest.TestCase):
    def patches(self, report_dir, parsed_args, excel_error=None):
        def export_excel(path, *_args):
            if excel_error:
                raise excel_error
            Path(path).write_bytes(b"xlsx")

        def render_html(path, *_args):
            Path(path).write_text("<html></html>", encoding="utf-8")

        def write_pdf(path, *_args):
            Path(path).write_bytes(b"%PDF")
            return 3

        def write_annex(path, *_args):
            Path(path).write_bytes(b"%PDF technical")
            return 2

        return (
            patch.object(zabbix_report, "REPORTS_DIR", report_dir),
            patch.object(zabbix_report, "parse_args", return_value=parsed_args),
            patch.object(
                zabbix_report,
                "load_config",
                return_value=("https://private.invalid/api_jsonrpc.php", "token-secret"),
            ),
            patch.object(zabbix_report, "ZabbixClient", FakeClient),
            patch.object(zabbix_report, "build_unit_catalog", return_value={}),
            patch.object(
                zabbix_report,
                "validate_problem_records",
                return_value=([], dict(INTEGRITY)),
            ),
            patch.object(zabbix_report, "build_incidents", return_value=[]),
            patch.object(zabbix_report, "export_excel", side_effect=export_excel),
            patch.object(zabbix_report, "render_html", side_effect=render_html),
            patch.object(zabbix_report, "write_pdf_report", side_effect=write_pdf),
            patch.object(
                zabbix_report,
                "write_technical_pdf_report",
                side_effect=write_annex,
            ),
        )

    def run_main(self, report_dir, parsed_args, excel_error=None):
        patches = self.patches(report_dir, parsed_args, excel_error)
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        zabbix_report.main()

    def test_main_creates_safe_diagnostic_and_detailed_pdf_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            self.run_main(report_dir, args(diagnostic=True, detailed=True))
            diagnostic = next(report_dir.glob("*_diagnostico.json"))
            data = json.loads(diagnostic.read_text(encoding="utf-8"))
            serialized = json.dumps(data)

            self.assertEqual(data["api"]["call_count"], 4)
            self.assertEqual(data["files"]["pdf"]["pages"], 3)
            self.assertEqual(data["files"]["technical_pdf"]["pages"], 2)
            self.assertTrue(next(report_dir.glob("*_anexo_tecnico.pdf")).exists())
            self.assertNotIn("private.invalid", serialized)
            self.assertNotIn("token-secret", serialized)

    def test_main_does_not_create_json_without_diagnostic_flag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            self.run_main(report_dir, args(diagnostic=False))
            self.assertEqual(list(report_dir.glob("*_diagnostico.json")), [])

    def test_export_failure_writes_partial_safe_diagnostic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            with self.assertRaisesRegex(RuntimeError, "incidente confidencial"):
                self.run_main(
                    report_dir,
                    args(diagnostic=True),
                    RuntimeError(
                        "token-secret https://private.invalid 10.0.0.1 incidente confidencial"
                    ),
                )
            diagnostic = next(report_dir.glob("*_diagnostico.json"))
            data = json.loads(diagnostic.read_text(encoding="utf-8"))
            serialized = json.dumps(data)

        self.assertEqual(data["files"]["excel"]["completed"], False)
        self.assertEqual(data["files"]["excel"]["error_type"], "RuntimeError")
        self.assertEqual(data["files"]["html"]["completed"], False)
        self.assertNotIn("token-secret", serialized)
        self.assertNotIn("private.invalid", serialized)
        self.assertNotIn("10.0.0.1", serialized)
        self.assertNotIn("incidente confidencial", serialized)


if __name__ == "__main__":
    unittest.main()
