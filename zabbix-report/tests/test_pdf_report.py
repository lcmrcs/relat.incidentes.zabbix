import re
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from pdf_report import (  # noqa: E402
    EXECUTIVE_RANKING_LIMIT,
    TECHNICAL_ROWS_PER_PAGE,
    build_impact_page,
    technical_pdf_name,
    write_pdf_report,
    write_technical_pdf_report,
)
from summary import build_report_summary  # noqa: E402


def incident(index=1, status="Aberto", unit=None):
    unit = unit or f"{1000 + index}-Unidade {index}"
    return {
        "host": f"host-{index}",
        "unit_code": str(1000 + index),
        "unit": unit,
        "incident_key": f"{1000 + index}|host-{index}|Switch|Falha de comunicação",
        "equipment": f"Equipamento {index}",
        "incident": f"Falha de comunicação {index}",
        "incident_type": f"Tipo de incidente {index}",
        "severity": "Alta" if index % 2 else "Média",
        "status": status,
        "date": "24/07/2026 10:00",
        "timestamp": 1784898000 - (index * 3600),
        "age_seconds": index * 3600 if status == "Aberto" else 0,
        "age_label": f"{index}h 0min",
        "duration_seconds": index * 3600,
        "duration_label": f"{index}h 0min",
        "open_age_seconds": index * 3600 if status == "Aberto" else 0,
        "open_age_label": f"{index}h 0min" if status == "Aberto" else "-",
        "resolved_at": "" if status == "Aberto" else "24/07/2026 11:00",
        "eventid": str(9000 + index),
    }


def pdf_page_count(data):
    return len(re.findall(rb"/Type /Page\b", data))


class ExecutivePdfTests(unittest.TestCase):
    def write_executive(self, incidents):
        summary = build_report_summary(incidents)
        temp_dir = tempfile.TemporaryDirectory()
        output = Path(temp_dir.name) / "report_2026-07-24_7d.pdf"
        pages = write_pdf_report(
            output,
            incidents,
            "24/07/2026 12:00",
            summary,
            "últimos 7 dias",
            {
                "processed": len(incidents),
                "adjusted": 0,
                "discarded": 0,
                "warning_count": 0,
                "label": "Dados validados",
            },
        )
        return temp_dir, output.read_bytes(), pages, summary

    def test_zero_incidents_generates_compact_pdf_and_hides_empty_sections(self):
        temp_dir, data, pages, _ = self.write_executive([])
        self.addCleanup(temp_dir.cleanup)

        self.assertEqual(pages, 3)
        self.assertEqual(pdf_page_count(data), 3)
        self.assertNotIn(b"Equipamentos e unidades mais afetados", data)
        self.assertNotIn(b"Prioridades e recorr", data)
        self.assertIn("Não há incidentes".encode("cp1252"), data)

    def test_few_and_many_incidents_keep_executive_pdf_bounded(self):
        few_dir, few_data, few_pages, _ = self.write_executive([incident(1), incident(2)])
        many_dir, many_data, many_pages, _ = self.write_executive(
            [incident(index, unit=f"{1000 + (index % 20)}-Unidade") for index in range(1, 501)]
        )
        self.addCleanup(few_dir.cleanup)
        self.addCleanup(many_dir.cleanup)

        self.assertGreaterEqual(few_pages, 5)
        self.assertLessEqual(few_pages, 6)
        self.assertEqual(many_pages, few_pages)
        self.assertEqual(pdf_page_count(few_data), few_pages)
        self.assertEqual(pdf_page_count(many_data), many_pages)

    def test_rankings_are_limited_to_the_most_relevant_items(self):
        incidents = []
        for index in range(1, EXECUTIVE_RANKING_LIMIT + 3):
            incidents.extend([incident(index)] * (20 - index))

        summary = build_report_summary(incidents)
        data = build_impact_page(summary, "24/07/2026 12:00", 3, 6)

        self.assertIn(b"Equipamento 6", data)
        self.assertNotIn(b"Equipamento 7", data)
        self.assertIn(
            f"Rankings limitados aos {EXECUTIVE_RANKING_LIMIT} itens".encode("cp1252"),
            data,
        )

    def test_pdf_consumes_canonical_summary_values(self):
        incidents = [incident(1), incident(2, status="Resolvido")]
        temp_dir, data, _, summary = self.write_executive(incidents)
        self.addCleanup(temp_dir.cleanup)

        self.assertIn(str(summary["unique_open"]).encode(), data)
        self.assertIn(summary["age"]["oldest_label"].encode("cp1252"), data)
        self.assertIn(summary["resolved_duration"]["median_label"].encode("cp1252"), data)

    def test_special_panels_remain_separate_on_the_cover(self):
        main = [incident(1)]
        special = build_report_summary([incident(2)])
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.pdf"
            write_pdf_report(
                output,
                main,
                "24/07/2026 12:00",
                build_report_summary(main),
                "últimos 7 dias",
                special_summaries={
                    "Servidor Zabbix": special,
                    "CONFEA VPN": build_report_summary([]),
                },
            )
            data = output.read_bytes()

        self.assertIn(b"Servidor Zabbix: 1 eventos", data)
        self.assertNotIn(b"CONFEA VPN: 0 eventos", data)

    def test_pdf_preserves_accents_and_redacts_urls_and_credentials(self):
        item = incident(1, unit="1001-Unidade São José")
        item["incident"] = "Falha em https://zabbix.interno.local token=segredo"
        item["incident_type"] = item["incident"]
        item["incident_key"] = "sensitive"

        temp_dir, data, _, _ = self.write_executive([item])
        self.addCleanup(temp_dir.cleanup)

        self.assertIn("São José".encode("cp1252"), data)
        self.assertNotIn(b"zabbix.interno.local", data)
        self.assertNotIn(b"segredo", data)

    def test_optional_technical_annex_has_predictable_name_and_pagination(self):
        incidents = [incident(index) for index in range(1, TECHNICAL_ROWS_PER_PAGE + 2)]
        with tempfile.TemporaryDirectory() as temp_dir:
            executive = Path(temp_dir) / "report_2026-07-24_7d.pdf"
            annex = technical_pdf_name(executive)
            pages = write_technical_pdf_report(annex, incidents, "24/07/2026 12:00")
            data = annex.read_bytes()

        self.assertEqual(annex.name, "report_2026-07-24_7d_anexo_tecnico.pdf")
        self.assertEqual(pages, 2)
        self.assertEqual(pdf_page_count(data), 2)
        self.assertEqual(data.count(b"Detalhamento completo dos eventos"), 2)
        self.assertEqual(data.count("Anexo técnico".encode("cp1252")), 2)

if __name__ == "__main__":
    unittest.main()
