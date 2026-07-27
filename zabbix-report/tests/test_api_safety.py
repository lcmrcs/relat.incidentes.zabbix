import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from zabbix_api import ZabbixClient  # noqa: E402


class ApiSafetyTests(unittest.TestCase):
    def test_invalid_recovery_clock_is_forwarded_to_integrity_validation(self):
        client = ZabbixClient("https://example.invalid", "secret")
        with patch.object(
            client,
            "call",
            return_value={"result": [{"eventid": "recovery-1", "clock": "invalid"}]},
        ):
            result = client.get_recovery_dates([{"r_eventid": "recovery-1"}])
        self.assertEqual(result, {"recovery-1": "invalid"})

    def test_host_lookup_ignores_unexpected_records_without_network(self):
        client = ZabbixClient("https://example.invalid", "secret")
        self.assertEqual(client.get_trigger_hosts([None, "invalid", {}]), ({}, {}, {}))


if __name__ == "__main__":
    unittest.main()
