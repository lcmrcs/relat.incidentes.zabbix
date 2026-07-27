import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from observability import ExecutionDiagnostics  # noqa: E402
from zabbix_api import ZabbixClient  # noqa: E402


class FakeClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


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

    def test_client_reports_api_call_count_and_duration_without_payload(self):
        diagnostics = ExecutionDiagnostics("7d", clock=FakeClock([0, 1, 3]))
        client = ZabbixClient(
            "https://private.invalid/api_jsonrpc.php",
            "token-secret",
            diagnostics=diagnostics,
        )
        response = Mock(status_code=200)
        response.json.return_value = {"result": []}
        with patch("zabbix_api.requests.post", return_value=response):
            result = client.call(
                {
                    "method": "problem.get",
                    "auth": "token-secret",
                    "params": {"host": "10.0.0.1"},
                },
                "buscar problemas",
            )

        self.assertEqual(result, {"result": []})
        self.assertEqual(len(diagnostics.api_calls), 1)
        self.assertEqual(diagnostics.api_calls[0]["operation"], "problem.get")
        self.assertEqual(diagnostics.api_calls[0]["duration_seconds"], 2)
        self.assertNotIn("token-secret", str(diagnostics.api_calls))
        self.assertNotIn("10.0.0.1", str(diagnostics.api_calls))


if __name__ == "__main__":
    unittest.main()
