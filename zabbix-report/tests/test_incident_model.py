import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from time_utils import DISPLAY_TIMEZONE, unix_to_datetime  # noqa: E402
from zabbix_report import build_incident_key, build_incidents  # noqa: E402

GENERATED_AT = unix_to_datetime(10_000, target_timezone=DISPLAY_TIMEZONE)


def problem(**overrides):
    data = {
        "objectid": "trigger-1",
        "eventid": "event-1",
        "r_eventid": "0",
        "clock": "1000",
        "name": "Unavailable by ICMP ping - 10.0.0.1",
        "severity": "4",
    }
    data.update(overrides)
    return data


def build(problems, recoveries=None):
    return build_incidents(
        problems,
        {"trigger-1": "1011_CAMERA_01"},
        {"trigger-1": "host-1"},
        {"host-1": {"tags": [{"tag": "unidade", "value": "1011"}]}},
        recoveries or {},
        {"1011": "Escola Teste"},
        "todos",
        GENERATED_AT,
    )


class IncidentModelTests(unittest.TestCase):
    def test_open_incident_ages_until_generation(self):
        item = build([problem()])[0]
        self.assertEqual(
            (item["status"], item["duration_seconds"], item["open_age_seconds"]),
            ("Aberto", 9000, 9000),
        )

    def test_resolved_duration_is_frozen_at_recovery(self):
        item = build([problem(r_eventid="recovery-1")], {"recovery-1": "3600"})[0]
        self.assertEqual(
            (item["status"], item["duration_seconds"], item["open_age_seconds"]),
            ("Resolvido", 2600, 0),
        )
        self.assertEqual(item["open_age_label"], "-")

    def test_pre_epoch_and_same_instant_recovery_are_deterministic(self):
        generated_at = unix_to_datetime(10, target_timezone=DISPLAY_TIMEZONE)
        item = build_incidents(
            [problem(clock="-10", r_eventid="recovery-1")],
            {"trigger-1": "1011_CAMERA_01"},
            {"trigger-1": "host-1"},
            {"host-1": {"tags": [{"tag": "unidade", "value": "1011"}]}},
            {"recovery-1": "-10"},
            {"1011": "Escola Teste"},
            "todos",
            generated_at,
        )[0]
        self.assertEqual(item["timestamp"], -10)
        self.assertEqual(item["resolved_timestamp"], -10)
        self.assertEqual(item["status"], "Resolvido")
        self.assertEqual(item["duration_seconds"], 0)
        self.assertEqual(item["open_age_seconds"], 0)

    def test_missing_recovery_and_invalid_timestamps_are_safe(self):
        self.assertEqual(build([problem(r_eventid="missing")])[0]["status"], "Aberto")
        invalid = build([problem(clock="invalid")])[0]
        self.assertEqual((invalid["date"], invalid["duration_seconds"]), ("-", 0))
        missing = build([problem(clock=None)])[0]
        out_of_range = build([problem(clock="999999999999999999999")])[0]
        self.assertEqual((missing["date"], out_of_range["date"]), ("-", "-"))

    def test_incident_key_is_deterministic_and_normalized(self):
        first = build_incident_key("1011", " CÂMERA  01 ", "Câmera", "Unavailable by ICMP ping")
        second = build_incident_key("1011", "câmera 01", "CÂMERA", "unavailable BY icmp PING")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
