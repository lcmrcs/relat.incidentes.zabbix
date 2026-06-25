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


if __name__ == "__main__":
    unittest.main()
