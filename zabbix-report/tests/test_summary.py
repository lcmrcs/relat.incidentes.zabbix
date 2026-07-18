import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from summary import (  # noqa: E402
    build_age_summary,
    build_report_summary,
    build_resolved_duration_summary,
    format_age,
)

NOW = 10_000_000


class FixedNow:
    def timestamp(self):
        return NOW


class FixedDatetime:
    @classmethod
    def now(cls):
        return FixedNow()


def incident(
    key,
    *,
    status="Aberto",
    severity="Alta",
    unit="1011-CE Escola Teste",
    equipment="Câmera",
    incident_type="Unavailable by ICMP ping",
    incident_name="Unavailable by ICMP ping - 10.32.1.10",
    host=None,
    age_seconds=3600,
):
    return {
        "incident_key": key,
        "status": status,
        "severity": severity,
        "unit_code": unit.split("-", 1)[0],
        "unit": unit,
        "equipment": equipment,
        "incident_type": incident_type,
        "incident": incident_name,
        "host": host or f"{key}-host",
        "timestamp": NOW - age_seconds,
        "age_seconds": age_seconds,
        "age_label": format_age(age_seconds),
        "open_age_seconds": age_seconds if status == "Aberto" else 0,
        "open_age_label": format_age(age_seconds) if status == "Aberto" else "-",
        "duration_seconds": age_seconds,
        "duration_label": format_age(age_seconds),
    }


class SummaryTests(unittest.TestCase):
    def test_format_age_outputs_short_labels(self):
        self.assertEqual(format_age(0), "0h")
        self.assertEqual(format_age(60), "1min")
        self.assertEqual(format_age(3660), "1h 1min")
        self.assertEqual(format_age(90000), "1d 1h")

    @patch("summary.datetime", FixedDatetime)
    def test_build_age_summary_counts_expected_ranges(self):
        incidents = [
            incident("24h", age_seconds=3600),
            incident("1-3d", age_seconds=2 * 86400),
            incident("4-10d", age_seconds=5 * 86400),
            incident("11-20d", age_seconds=12 * 86400),
            incident("21-30d", age_seconds=22 * 86400),
            incident("31-50d", age_seconds=35 * 86400),
            incident("51-75d", age_seconds=60 * 86400),
            incident("76-90d", age_seconds=80 * 86400),
            incident("over-90d", age_seconds=100 * 86400),
        ]

        summary = build_age_summary(incidents)

        self.assertEqual(summary["oldest"]["incident_key"], "over-90d")
        self.assertEqual(summary["newest"]["incident_key"], "24h")
        self.assertEqual(summary["range_24h"], 1)
        self.assertEqual(summary["range_1_3d"], 1)
        self.assertEqual(summary["range_4_10d"], 1)
        self.assertEqual(summary["range_11_20d"], 1)
        self.assertEqual(summary["range_21_30d"], 1)
        self.assertEqual(summary["range_31_50d"], 1)
        self.assertEqual(summary["range_51_75d"], 1)
        self.assertEqual(summary["range_76_90d"], 1)
        self.assertEqual(summary["range_over_90d"], 1)
        self.assertEqual(summary["over_7d"], 6)
        self.assertEqual(summary["over_30d"], 4)
        self.assertEqual(summary["over_90d"], 1)

    @patch("summary.datetime", FixedDatetime)
    def test_build_report_summary_calculates_totals_and_rankings(self):
        incidents = [
            incident("cam-1", equipment="Câmera", severity="Alta", unit="1011-CE A"),
            incident("cam-1", equipment="Câmera", severity="Alta", unit="1011-CE A"),
            incident(
                "facial-1",
                equipment="Terminal Facial",
                severity="Atenção",
                unit="1012-CE B",
                incident_type="High ICMP ping loss",
                status="Resolvido",
            ),
            incident(
                "mkt-1",
                equipment="Mikrotik",
                severity="Média",
                unit="1011-CE A",
                incident_type="No SNMP data collection",
            ),
        ]

        summary = build_report_summary(incidents)

        self.assertEqual(summary["event_total"], 4)
        self.assertEqual(summary["unique_total"], 3)
        self.assertEqual(summary["unique_open"], 2)
        self.assertEqual(summary["unique_resolved"], 1)
        self.assertEqual(summary["repeated_events"], 1)
        self.assertEqual(summary["high"], 2)
        self.assertEqual(summary["attention"], 1)
        self.assertEqual(summary["medium"], 1)
        self.assertEqual(summary["open"], 3)
        self.assertEqual(summary["resolved"], 1)
        self.assertEqual(summary["avg_events_per_incident"], 1.3)

        equipment_names = [item["name"] for item in summary["equipment"]]
        self.assertEqual(equipment_names, ["Mikrotik", "Terminal Facial", "Câmera"])
        self.assertEqual(summary["top_equipment"][0]["name"], "Câmera")
        self.assertEqual(summary["top_equipment"][0]["total"], 2)
        self.assertEqual(summary["top_units"][0]["name"], "1011-CE A")
        self.assertEqual(summary["top_incident_types"][0]["name"], "Unavailable by ICMP ping")
        self.assertEqual(summary["period_comparison"]["fresh_total"], 3)
        self.assertEqual(summary["recurrence"]["affected_hosts"], 1)
        self.assertEqual(summary["recurrence"]["top"][0]["total"], 2)
        self.assertGreaterEqual(summary["priority"]["high"], 1)
        self.assertGreater(summary["priority"]["average_score"], 0)
        self.assertEqual(summary["unit_criticality"]["total_units"], 1)
        self.assertEqual(summary["unit_criticality"]["top"][0]["name"], "1011-CE A")
        self.assertGreaterEqual(
            summary["unit_criticality"]["top"][0]["affected_equipment_count"],
            1,
        )
        self.assertTrue(summary["unit_criticality"]["top"][0]["equipment_mix"])
        self.assertTrue(summary["unit_criticality"]["top"][0]["severity_mix"])
        self.assertTrue(summary["top_oldest_units"])
        self.assertTrue(summary["top_high_severity_units"])
        self.assertIn(
            summary["unit_criticality"]["top"][0]["level"],
            {
                "Intervenção imediata",
                "Prioridade alta",
                "Acompanhamento ativo",
                "Monitoramento normal",
            },
        )

    def test_empty_summary_is_safe(self):
        summary = build_report_summary([])

        self.assertEqual(summary["event_total"], 0)
        self.assertEqual(summary["unique_total"], 0)
        self.assertEqual(summary["age"]["oldest_label"], "-")
        self.assertEqual(summary["top_equipment"], [])
        self.assertEqual(summary["period_comparison"]["leading_total"], 0)
        self.assertEqual(summary["recurrence"]["top"], [])
        self.assertEqual(summary["priority"]["top"], [])
        self.assertEqual(summary["unit_criticality"]["top"], [])
        self.assertEqual(summary["top_oldest_units"], [])
        self.assertEqual(summary["top_high_severity_units"], [])

    @patch("summary.datetime", FixedDatetime)
    def test_aging_indicators_ignore_resolved_events(self):
        summary = build_report_summary(
            [
                incident("open", age_seconds=3600),
                incident("resolved", status="Resolvido", age_seconds=100 * 86400),
            ]
        )
        self.assertEqual(summary["age"]["oldest"]["incident_key"], "open")
        self.assertEqual(summary["age"]["over_90d"], 0)
        self.assertEqual(summary["period_comparison"]["fresh_total"], 1)

    def test_grouping_and_recurrence_use_the_canonical_incident_key(self):
        incidents = [
            incident("same-condition", host="host-a"),
            incident("same-condition", host="host-a", status="Resolvido"),
            incident("other-condition", host="host-a", incident_type="High ICMP ping loss"),
        ]

        summary = build_report_summary(incidents)

        self.assertEqual(summary["event_total"], 3)
        self.assertEqual(summary["unique_total"], 2)
        self.assertEqual(summary["repeated_events"], 1)
        self.assertEqual(summary["unique_open"], 2)
        self.assertEqual(summary["unique_resolved"], 0)
        self.assertEqual(summary["recurrence"]["total_recurrent_events"], 1)
        self.assertEqual(summary["recurrence"]["affected_hosts"], 1)

    def test_resolved_duration_has_average_median_maximum_and_ranges(self):
        incidents = [
            incident("r1", status="Resolvido", age_seconds=1800),
            incident("r2", status="Resolvido", age_seconds=2 * 3600),
            incident("r3", status="Resolvido", age_seconds=2 * 86400),
            incident("open", age_seconds=100 * 86400),
        ]
        result = build_resolved_duration_summary(incidents)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["average_seconds"], 60600)
        self.assertEqual(result["median_seconds"], 7200)
        self.assertEqual(result["maximum_seconds"], 172800)
        self.assertEqual([item["total"] for item in result["ranges"]], [1, 1, 0, 1, 0, 0])


if __name__ == "__main__":
    unittest.main()
