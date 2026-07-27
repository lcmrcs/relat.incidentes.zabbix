import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from observability import (  # noqa: E402
    ExecutionDiagnostics,
    write_optional_diagnostic,
)


class FakeClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


class FakeWallClock:
    def __init__(self):
        self.value = datetime(2026, 7, 27, 8, 0, 0)

    def __call__(self):
        current = self.value
        self.value += timedelta(seconds=10)
        return current


class ObservabilityTests(unittest.TestCase):
    def test_measures_stages_total_and_slowest_stage_with_simulated_time(self):
        diagnostics = ExecutionDiagnostics(
            "7d · status todos",
            clock=FakeClock([0, 1, 3, 3, 8, 10]),
            wall_clock=FakeWallClock(),
            thresholds={"disproportionate_min_seconds": 100},
        )

        with diagnostics.measure("validation"):
            pass
        with diagnostics.measure("pdf_export"):
            pass
        data = diagnostics.as_dict()

        self.assertEqual(data["total_seconds"], 10)
        self.assertEqual(data["stages"][0]["duration_seconds"], 2)
        self.assertEqual(data["stages"][1]["duration_seconds"], 5)
        self.assertEqual(data["bottleneck"]["stage"], "pdf_export")
        self.assertEqual(data["bottleneck"]["percent_total"], 50)

    def test_counts_api_calls_without_payload_or_connection_details(self):
        diagnostics = ExecutionDiagnostics(
            "7d",
            clock=FakeClock([0, 1]),
            wall_clock=FakeWallClock(),
        )
        diagnostics.record_api_call("problem.get", 1.25)
        diagnostics.record_api_call("https://private.invalid token=secret", 0.5)
        data = diagnostics.as_dict()
        serialized = json.dumps(data)

        self.assertEqual(data["api"]["call_count"], 2)
        self.assertEqual(data["api"]["calls"][0]["operation"], "problem.get")
        self.assertEqual(data["api"]["calls"][1]["operation"], "unknown")
        self.assertNotIn("private.invalid", serialized)
        self.assertNotIn("secret", serialized)

    def test_records_file_sizes_pages_and_optional_technical_pdf(self):
        diagnostics = ExecutionDiagnostics(
            "7d",
            clock=FakeClock([0, 1]),
            wall_clock=FakeWallClock(),
            thresholds={
                "pdf_size_bytes": 10_000,
                "technical_pdf_size_bytes": 10_000,
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            html = Path(temp_dir) / "report.html"
            pdf = Path(temp_dir) / "report.pdf"
            annex = Path(temp_dir) / "report_anexo_tecnico.pdf"
            html.write_bytes(b"h" * 20)
            pdf.write_bytes(b"p" * 30)
            annex.write_bytes(b"a" * 40)

            diagnostics.record_file("html", html)
            diagnostics.record_file("pdf", pdf, pages=6)
            diagnostics.record_file("technical_pdf", annex, pages=12)
            data = diagnostics.as_dict()

        self.assertEqual(data["files"]["html"]["size_bytes"], 20)
        self.assertEqual(data["files"]["pdf"]["pages"], 6)
        self.assertEqual(data["files"]["technical_pdf"]["pages"], 12)

    def test_json_is_generated_only_when_explicitly_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report_diagnostico.json"
            disabled = ExecutionDiagnostics(
                "7d",
                clock=FakeClock([0, 1]),
                wall_clock=FakeWallClock(),
            )
            self.assertIsNone(write_optional_diagnostic(False, disabled, output))
            self.assertFalse(output.exists())

            enabled = ExecutionDiagnostics(
                "7d",
                clock=FakeClock([0, 2]),
                wall_clock=FakeWallClock(),
            )
            self.assertEqual(write_optional_diagnostic(True, enabled, output), output)
            data = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["period_requested"], "7d")

    def test_objective_warnings_use_adjustable_thresholds(self):
        diagnostics = ExecutionDiagnostics(
            "7d",
            clock=FakeClock([0, 10]),
            wall_clock=FakeWallClock(),
            thresholds={
                "api_call_seconds": 1,
                "total_seconds": 5,
                "high_event_volume": 5,
                "disproportionate_min_seconds": 100,
            },
        )
        diagnostics.record_api_call("host.get", 2)
        diagnostics.set_event_groups(5, 0, 0)
        codes = {item["code"] for item in diagnostics.as_dict()["warnings"]}

        self.assertIn("slow_api_call", codes)
        self.assertIn("slow_execution", codes)
        self.assertIn("high_event_volume", codes)

    def test_failure_records_only_safe_error_type(self):
        diagnostics = ExecutionDiagnostics(
            "7d",
            clock=FakeClock([0, 1, 2, 3]),
            wall_clock=FakeWallClock(),
        )
        with self.assertRaisesRegex(RuntimeError, "token"):
            with diagnostics.measure("excel_export"):
                raise RuntimeError(
                    "token=secret https://private.invalid 10.0.0.1 incidente confidencial"
                )
        diagnostics.record_failed_file(
            "excel",
            "report_token-secret.xlsx",
            RuntimeError("https://private.invalid"),
        )
        serialized = json.dumps(diagnostics.as_dict())

        self.assertIn("RuntimeError", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("private.invalid", serialized)
        self.assertNotIn("10.0.0.1", serialized)
        self.assertNotIn("incidente confidencial", serialized)


if __name__ == "__main__":
    unittest.main()
