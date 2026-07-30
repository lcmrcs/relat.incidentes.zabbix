import sys
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from comparison import build_comparison_windows, build_executive_comparison  # noqa: E402
from report_launcher import normalize_payload, render_page  # noqa: E402
from time_utils import DISPLAY_TIMEZONE  # noqa: E402


def incident(eventid, timestamp, **overrides):
    item = {
        "eventid": eventid,
        "timestamp": timestamp,
        "resolved_timestamp": None,
        "status": "Aberto",
        "duration_seconds": 0,
        "incident_key": f"condition-{eventid}",
        "host": f"host-{eventid}",
        "unit": "Unidade 1011",
        "equipment": "Câmera",
        "severity": "Média",
    }
    item.update(overrides)
    return item


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.windows = build_comparison_windows(
            datetime(2026, 1, 2, tzinfo=DISPLAY_TIMEZONE),
            datetime(2026, 1, 2, 23, 59, 59, tzinfo=DISPLAY_TIMEZONE),
        )
        self.valid = {"level": "valid", "discarded": 0, "warning_count": 0}

    def test_windows_are_equivalent_adjacent_and_do_not_overlap(self):
        current = self.windows["current"]
        previous = self.windows["previous"]
        self.assertEqual(current["time_from"] - previous["time_till"], 1)
        self.assertEqual(
            current["time_till"] - current["time_from"],
            previous["time_till"] - previous["time_from"],
        )

    def test_increase_reduction_stability_and_zero_base(self):
        current_start = self.windows["current"]["time_from"]
        previous_start = self.windows["previous"]["time_from"]
        model = build_executive_comparison(
            [
                incident("1", current_start),
                incident("2", current_start + 1, severity="Alta"),
            ],
            [incident("3", previous_start)],
            self.windows,
            self.valid,
            self.valid,
        )
        metrics = {item["key"]: item for item in model["metrics"]}
        self.assertEqual(metrics["started"]["direction"], "aumento")
        self.assertEqual(metrics["high_started"]["direction"], "novo aumento")
        self.assertEqual(metrics["units_affected"]["direction"], "estabilidade")
        self.assertEqual(metrics["resolved"]["percent_label"], "+0.0%")

    def test_resolved_duration_uses_only_recoveries_inside_each_window(self):
        current_start = self.windows["current"]["time_from"]
        previous_start = self.windows["previous"]["time_from"]
        model = build_executive_comparison(
            [
                incident(
                    "1",
                    current_start,
                    status="Resolvido",
                    resolved_timestamp=current_start + 7200,
                    duration_seconds=7200,
                )
            ],
            [
                incident(
                    "2",
                    previous_start,
                    status="Resolvido",
                    resolved_timestamp=previous_start + 3600,
                    duration_seconds=3600,
                )
            ],
            self.windows,
            self.valid,
            self.valid,
        )
        metric = next(
            item for item in model["metrics"] if item["key"] == "resolved_average_seconds"
        )
        self.assertEqual((metric["current"], metric["previous"]), (7200, 3600))
        self.assertEqual(metric["interpretation"], "Piora observada")

    def test_incomplete_window_suppresses_definitive_conclusions(self):
        model = build_executive_comparison(
            [],
            [],
            self.windows,
            self.valid,
            {"level": "incomplete", "discarded": 1},
        )
        self.assertFalse(model["quality_sufficient"])
        self.assertTrue(
            all(item["interpretation"] == "Dados insuficientes" for item in model["metrics"])
        )
        self.assertTrue(all(item["current"] is None for item in model["metrics"]))

    def test_launcher_exposes_and_forwards_explicit_comparison(self):
        page = render_page().decode("utf-8")
        self.assertIn("Comparar com o período anterior", page)
        args = normalize_payload(
            {
                "period": "24h",
                "status": "todos",
                "keep": 1,
                "compare": True,
            }
        )
        self.assertIn("--comparar", args)
        with self.assertRaisesRegex(ValueError, "período finito"):
            normalize_payload(
                {
                    "period": "historico",
                    "status": "todos",
                    "keep": 1,
                    "compare": True,
                }
            )

    def test_large_fictional_volume_remains_deterministic(self):
        current_start = self.windows["current"]["time_from"]
        previous_start = self.windows["previous"]["time_from"]
        current = [
            incident(
                f"current-{index}",
                current_start + index,
                incident_key=f"condition-{index % 500}",
                host=f"host-{index % 700}",
            )
            for index in range(20_000)
        ]
        previous = [
            incident(
                f"previous-{index}",
                previous_start + index,
                incident_key=f"condition-{index % 400}",
                host=f"host-{index % 600}",
            )
            for index in range(20_000)
        ]
        model = build_executive_comparison(
            current,
            previous,
            self.windows,
            self.valid,
            self.valid,
        )
        metrics = {item["key"]: item for item in model["metrics"]}
        self.assertEqual(metrics["started"]["current"], 20_000)
        self.assertEqual(metrics["started"]["previous"], 20_000)
        self.assertEqual(metrics["started"]["direction"], "estabilidade")
        self.assertEqual(metrics["recurrences"]["current"], 19_500)
        self.assertEqual(metrics["recurrences"]["previous"], 19_600)


if __name__ == "__main__":
    unittest.main()
