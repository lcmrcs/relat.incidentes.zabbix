import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import zabbix_report  # noqa: E402


class ReportCleanupTests(unittest.TestCase):
    def test_cleanup_old_reports_keeps_current_group(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)

            for stem in ["report_old", "report_current"]:
                for extension in [".html", ".pdf", ".xlsx"]:
                    (reports_dir / f"{stem}{extension}").write_text(
                        stem,
                        encoding="utf-8",
                    )

            with patch.object(zabbix_report, "REPORTS_DIR", reports_dir):
                removed = zabbix_report.cleanup_old_reports(
                    "report_current",
                    keep_count=1,
                )

            removed_names = sorted(path.name for path in removed)
            remaining_names = sorted(path.name for path in reports_dir.iterdir())

            self.assertEqual(
                removed_names,
                [
                    "report_old.html",
                    "report_old.pdf",
                    "report_old.xlsx",
                ],
            )
            self.assertEqual(
                remaining_names,
                [
                    "report_current.html",
                    "report_current.pdf",
                    "report_current.xlsx",
                ],
            )

    def test_cleanup_treats_technical_annex_as_part_of_current_group(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)
            current_pdf = reports_dir / "report_2026-07-24_7d.pdf"
            annex_pdf = reports_dir / "report_2026-07-24_7d_anexo_tecnico.pdf"
            current_pdf.write_bytes(b"pdf")
            annex_pdf.write_bytes(b"annex")

            with patch.object(zabbix_report, "REPORTS_DIR", reports_dir):
                removed = zabbix_report.cleanup_old_reports(
                    "report_2026-07-24_7d",
                    keep_count=1,
                )

            self.assertEqual(removed, [])
            self.assertTrue(current_pdf.exists())
            self.assertTrue(annex_pdf.exists())


if __name__ == "__main__":
    unittest.main()
