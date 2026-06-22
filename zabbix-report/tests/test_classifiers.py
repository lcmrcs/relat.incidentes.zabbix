import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from classifiers import (  # noqa: E402
    build_unit_catalog,
    classify_equipment,
    classify_incident_type,
    classify_unit_group,
    extract_school_unit,
    extract_unit_code,
    get_unit_tag_value,
)


class ClassifierTests(unittest.TestCase):
    def test_classify_equipment_from_known_host_patterns(self):
        cases = {
            "0000-SRV Zabbix server": "Servidor Zabbix",
            "1040_23-TERM_FACIAL - PORTARIA": "Terminal Facial",
            "1011-MKT CE Escola Teste": "Mikrotik",
            "1011-SW Bloco A": "Switch",
            "1011-NVR CFTV": "NVR",
            "1011-CAM - LOCAL_X": "Câmera",
            "1011-Central de Alarme": "Central de Alarme",
            "1011-Portal Detector de Metal": "Portal Detector de Metal",
            "host-sem-padrao": "Diversos",
        }

        for host, expected in cases.items():
            with self.subTest(host=host):
                self.assertEqual(classify_equipment(host), expected)

    def test_classify_incident_type_normalizes_recurring_zabbix_triggers(self):
        cases = {
            "Unavailable by ICMP ping - 10.32.1.10": "Unavailable by ICMP ping",
            "High ICMP ping loss - 10.32.1.10": "High ICMP ping loss",
            "High ICMP ping response time - 10.32.1.10": "High ICMP ping response time",
            "No SNMP data collection": "No SNMP data collection",
            "Temperature is above warning threshold": "Temperature above threshold",
            "High bandwidth usage on interface": "High bandwidth usage",
            "Interface Gi0/1 link down": "Interface down",
            "": "Não informado",
            "Trigger específica sem regra": "Trigger específica sem regra",
        }

        for incident, expected in cases.items():
            with self.subTest(incident=incident):
                self.assertEqual(classify_incident_type(incident), expected)

    def test_extract_school_unit_and_unit_code(self):
        self.assertEqual(extract_unit_code("1011-MKT Escola Teste"), "1011")
        self.assertEqual(extract_unit_code("sem-codigo"), "")
        self.assertEqual(
            extract_school_unit("1011-MKT CE Escola Teste - Brotas"),
            "1011-Brotas",
        )
        self.assertEqual(extract_school_unit("0000-SRV Zabbix server"), "Zabbix Server")
        self.assertEqual(extract_school_unit("host-sem-codigo"), "Infraestrutura")

    def test_get_unit_tag_value_accepts_only_four_digit_unit_tags(self):
        self.assertEqual(
            get_unit_tag_value({"tags": [{"tag": "Unidade", "value": "1011"}]}),
            "1011",
        )
        self.assertEqual(
            get_unit_tag_value({"tags": [{"tag": "unidade", "value": "ABC"}]}),
            "",
        )
        self.assertEqual(get_unit_tag_value({"tags": []}), "")

    def test_classify_unit_group_keeps_special_infrastructure_separate(self):
        catalog = {"1011": "1011-CE Escola Teste - Brotas"}

        self.assertEqual(
            classify_unit_group(
                "1011-CAM - LOCAL_X",
                {"tags": [{"tag": "unidade", "value": "1011"}]},
                catalog,
            ),
            ("1011", "1011-CE Escola Teste - Brotas"),
        )
        self.assertEqual(
            classify_unit_group(
                "0000-SRV Zabbix server",
                {"tags": [{"tag": "unidade", "value": "0000"}]},
                catalog,
            ),
            ("ZBX", "Zabbix Server"),
        )
        self.assertEqual(
            classify_unit_group(
                "SP-HW-WIN-CFH-CADGIS",
                {"tags": []},
                catalog,
            ),
            ("CONFEA", "CONFEA VPN"),
        )
        self.assertEqual(
            classify_unit_group("host-sem-unidade", {"tags": []}, catalog),
            ("INFRA", "Infraestrutura"),
        )

    def test_build_unit_catalog_prefers_school_like_host_names(self):
        host_details = {
            "1": {
                "name": "1011_101-CAM - LOCAL_X",
                "tags": [{"tag": "unidade", "value": "1011"}],
            },
            "2": {
                "name": "1011-MKT CE Escola Teste - Brotas",
                "tags": [{"tag": "unidade", "value": "1011"}],
            },
            "3": {
                "name": "1169-MKT Fora do intervalo",
                "tags": [{"tag": "unidade", "value": "1170"}],
            },
        }

        self.assertEqual(
            build_unit_catalog(host_details),
            {"1011": "1011-CE Escola Teste - Brotas"},
        )


if __name__ == "__main__":
    unittest.main()
