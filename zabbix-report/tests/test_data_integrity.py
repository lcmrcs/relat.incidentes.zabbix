import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from data_integrity import validate_problem_records  # noqa: E402
from zabbix_report import build_incidents  # noqa: E402

NOW = datetime.fromtimestamp(10_000)


def event(**overrides):
    item = {
        "eventid": "1",
        "clock": "1000",
        "objectid": "trigger-1",
        "name": "Unavailable by ICMP ping",
        "severity": "4",
        "r_eventid": "0",
    }
    item.update(overrides)
    return item


def validate(items, recoveries=None, host="1011-CAM Escola", with_unit=True):
    return validate_problem_records(
        items,
        {"trigger-1": host} if host is not None else {},
        {"trigger-1": "host-1"},
        {"host-1": {"tags": [{"tag": "unidade", "value": "1011"}]}} if with_unit else {},
        recoveries or {},
        {"1011": "Escola Teste"},
        NOW,
    )


class DataIntegrityTests(unittest.TestCase):
    def test_valid_event_and_duplicate(self):
        records, summary = validate([event(), event()])
        self.assertEqual(len(records), 1)
        self.assertEqual(summary["received"], 2)
        self.assertEqual(summary["processed"], 1)
        self.assertEqual(summary["discarded"], 1)
        self.assertEqual(summary["duplicates"], 1)

    def test_invalid_and_future_timestamps_do_not_stop_validation(self):
        records, summary = validate(
            [
                event(eventid="bad", clock="invalid"),
                event(eventid="future", clock="10001"),
                event(eventid="valid"),
            ]
        )
        self.assertEqual([item["eventid"] for item in records], ["valid"])
        self.assertEqual(summary["invalid_timestamps"], 2)
        self.assertEqual(summary["discarded"], 2)

    def test_inconsistent_recovery_is_kept_as_open(self):
        records, summary = validate([event(r_eventid="recovery-1")], {"recovery-1": "500"})
        self.assertEqual(records[0]["r_eventid"], "0")
        self.assertEqual(summary["inconsistent_recoveries"], 1)
        self.assertEqual(summary["adjusted"], 1)

    def test_unknown_host_unit_equipment_and_severity_are_safe(self):
        records, summary = validate([event(severity="99")], host=None, with_unit=False)
        self.assertEqual(records[0]["severity"], "0")
        self.assertEqual(summary["unidentified_hosts"], 1)
        self.assertEqual(summary["unidentified_units"], 1)
        self.assertEqual(summary["unidentified_equipment"], 1)
        self.assertEqual(summary["unknown_severities"], 1)

    def test_warnings_and_logs_do_not_contain_sensitive_values(self):
        secret = "token-super-secreto"
        with self.assertLogs("zabbix-report.integrity", level="INFO") as captured:
            _, summary = validate([event(name=secret, severity="99")])
        public_text = json.dumps(summary, ensure_ascii=False) + " ".join(captured.output)
        self.assertNotIn(secret, public_text)
        self.assertNotIn("10.0.0.1", public_text)

    def test_generation_continues_with_valid_records_after_discards(self):
        records, summary = validate([event(eventid="bad", clock=None), event(eventid="ok")])
        incidents = build_incidents(
            records,
            {"trigger-1": "1011-CAM Escola"},
            {"trigger-1": "host-1"},
            {"host-1": {"tags": [{"tag": "unidade", "value": "1011"}]}},
            {},
            {"1011": "Escola Teste"},
            "todos",
            NOW,
        )
        self.assertEqual(summary["discarded"], 1)
        self.assertEqual([item["eventid"] for item in incidents], ["ok"])


if __name__ == "__main__":
    unittest.main()
