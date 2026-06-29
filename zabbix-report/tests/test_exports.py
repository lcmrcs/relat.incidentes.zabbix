import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from pdf_report import write_pdf_report  # noqa: E402
from summary import build_report_summary  # noqa: E402
from zabbix_report import export_excel  # noqa: E402


def sample_incident():
    return {
        "host": "1040_23-TERM_FACIAL - PORTARIA",
        "unit_code": "1040",
        "unit": "1040-CETI de Catu",
        "incident_key": "1040|host|Terminal Facial|High ICMP ping loss|Alta",
        "equipment": "Terminal Facial",
        "incident": "High ICMP ping loss - 10.0.0.1",
        "incident_type": "High ICMP ping loss",
        "severity": "Alta",
        "status": "Aberto",
        "date": "26/06/2026 14:16",
        "timestamp": 1782480000,
        "age_seconds": 3600,
        "age_label": "1h 0min",
        "resolved_at": "",
        "eventid": "123456",
    }


class ExportTests(unittest.TestCase):
    def test_export_excel_creates_executive_sheets(self):
        incidents = [sample_incident()]
        summary = build_report_summary(incidents)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "relatorio.xlsx"
            export_excel(
                output,
                incidents,
                incidents,
                [],
                [],
                summary,
                "26/06/2026 14:16",
                "histórico completo (abertos): até 26/06/2026 14:16",
            )

            workbook = load_workbook(output)

        self.assertEqual(
            workbook.sheetnames,
            ["Resumo Executivo", "Rankings", "Inteligência", "Unidades", "Todos"],
        )
        self.assertEqual(workbook["Resumo Executivo"]["A3"].value, "Gerado em")
        self.assertEqual(workbook["Inteligência"]["A1"].value, "Distribuição temporal")
        self.assertEqual(workbook["Unidades"]["A1"].value, "Data de abertura")
        self.assertEqual(workbook["Unidades"]["K1"].value, "Evento Zabbix")

    def test_write_pdf_report_creates_pdf_file(self):
        incidents = [sample_incident()]
        summary = build_report_summary(incidents)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "relatorio.pdf"
            write_pdf_report(
                output,
                incidents,
                "26/06/2026 14:16",
                summary,
                "histórico completo (abertos): até 26/06/2026 14:16",
            )
            pdf_bytes = output.read_bytes()

        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        self.assertIn(b"%%EOF", pdf_bytes)


if __name__ == "__main__":
    unittest.main()
