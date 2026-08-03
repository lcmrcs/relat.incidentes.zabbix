import copy
import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from executive_summary import (  # noqa: E402
    build_executive_summary,
    sanitize_executive_identifier,
    sanitize_executive_text,
)
from summary import build_report_summary  # noqa: E402

VALID_INTEGRITY = {
    "received": 0,
    "processed": 0,
    "adjusted": 0,
    "discarded": 0,
    "warning_count": 0,
    "level": "valid",
}


def incident(index=1, **overrides):
    item = {
        "eventid": str(index),
        "incident_key": f"condition-{index}",
        "host": f"HOST-{index}",
        "unit_code": "1011",
        "unit": "Unidade Fictícia",
        "equipment": "Câmera",
        "incident": "Indisponibilidade fictícia",
        "incident_type": "Indisponibilidade",
        "severity": "Média",
        "status": "Aberto",
        "timestamp": 1000 + index,
        "duration_seconds": 3600,
        "duration_label": "1h 0min",
        "open_age_seconds": 3600,
        "open_age_label": "1h 0min",
        "age_seconds": 3600,
        "age_label": "1h 0min",
        "resolved_timestamp": None,
        "resolved_at": "",
    }
    item.update(overrides)
    return item


def build(incidents, integrity=None, comparison=None):
    summary = build_report_summary(incidents)
    data_integrity = copy.deepcopy(VALID_INTEGRITY)
    data_integrity.update(
        {
            "received": len(incidents),
            "processed": len(incidents),
        }
    )
    if integrity:
        data_integrity.update(integrity)
    return build_executive_summary(
        summary,
        comparison,
        data_integrity,
        "31/07/2026 12:00",
        "últimas 24 horas",
    )


class ExecutiveSummaryTests(unittest.TestCase):
    def test_critical_priorities_and_zero_units_are_explained_separately(self):
        summary = build_report_summary([incident()])
        summary["priority"].update({"critical": 5, "high": 0})
        summary["unit_criticality"].update({"critical": 0})
        result = build_executive_summary(
            summary,
            None,
            {**VALID_INTEGRITY, "received": 1, "processed": 1},
            "31/07/2026 12:00",
            "últimas 24 horas",
        )
        critical = next(item for item in result["findings"] if item["category"] == "criticidade")
        self.assertIn(
            "5 prioridades críticas relacionadas a hosts ou equipamentos",
            critical["evidence"],
        )
        self.assertIn(
            "Nenhuma unidade atingiu o critério de intervenção imediata",
            critical["evidence"],
        )
        self.assertNotIn("5 prioridades críticas e 0 unidades", critical["evidence"])

    def test_singular_and_plural_are_correct_for_operational_entities(self):
        summary = build_report_summary([incident()])
        summary["priority"].update({"critical": 1, "high": 0})
        summary["unit_criticality"].update({"critical": 1})
        result = build_executive_summary(
            summary,
            None,
            {**VALID_INTEGRITY, "received": 1, "processed": 1},
            "31/07/2026 12:00",
            "últimas 24 horas",
        )
        critical = next(item for item in result["findings"] if item["category"] == "criticidade")
        self.assertIn("1 prioridade crítica relacionada", critical["evidence"])
        self.assertIn("1 unidade atingiu o critério", critical["evidence"])
        self.assertNotIn("1 prioridades", repr(result))
        self.assertNotIn("1 unidades", repr(result))

    def test_empty_report_is_prudent_and_has_no_false_availability_claim(self):
        result = build([])
        self.assertEqual(result["situation"], "Estável")
        self.assertEqual(result["confidence"], "Moderado")
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("não comprova disponibilidade total", result["findings"][0]["explanation"])
        self.assertIn("Sem base comparativa", result["comparison_note"])

    def test_critical_scenario_uses_multiple_signals_and_at_most_five_findings(self):
        incidents = [
            incident(
                index,
                severity="Desastre" if index < 4 else "Alta",
                open_age_seconds=15 * 86400,
                age_seconds=15 * 86400,
                open_age_label="15d 0h",
                age_label="15d 0h",
            )
            for index in range(1, 9)
        ]
        result = build(incidents)
        self.assertEqual(result["situation"], "Crítica")
        self.assertLessEqual(len(result["findings"]), 5)
        categories = {item["category"] for item in result["findings"]}
        self.assertIn("criticidade", categories)
        self.assertIn("severidade", categories)
        self.assertIn("envelhecimento", categories)

    def test_concentration_recurrence_and_action_are_specific(self):
        incidents = [
            incident(index, incident_key="same-condition", host="HOST-RECORRENTE")
            for index in range(1, 7)
        ]
        result = build(incidents)
        text = " ".join(
            f"{item['title']} {item['evidence']} {item['recommendation']}"
            for item in result["findings"]
        )
        self.assertIn("reincidentes", text)
        self.assertIn("causa raiz", text)
        self.assertIn("Unidade Fictícia", text)

    def test_comparison_uses_canonical_direction_and_zero_base_wording(self):
        comparison = {
            "quality_sufficient": True,
            "metrics": [
                {
                    "key": "high_started",
                    "label": "Alta/Desastre iniciados",
                    "direction": "novo aumento",
                    "current_label": "3",
                    "previous_label": "0",
                    "percent_label": "Novo aumento",
                    "interpretation": "Piora observada",
                },
                {
                    "key": "resolved_average_seconds",
                    "label": "Duração média dos resolvidos",
                    "direction": "redução",
                    "current_label": "1h 0min",
                    "previous_label": "2h 0min",
                    "percent_label": "-50.0%",
                    "interpretation": "Melhora observada",
                },
            ],
        }
        result = build([incident()], comparison=comparison)
        evidence = " ".join(item["evidence"] for item in result["findings"])
        self.assertIn("Novo aumento", evidence)
        self.assertNotIn("inf", evidence.casefold())
        self.assertIn("Tendências usam", result["comparison_note"])

    def test_incomplete_integrity_limits_confidence_and_conclusion(self):
        result = build(
            [incident()],
            integrity={"received": 3, "processed": 1, "discarded": 2, "warning_count": 2},
        )
        self.assertEqual(result["confidence"], "Limitado")
        self.assertEqual(result["situation"], "Dados insuficientes")
        self.assertEqual(result["findings"][0]["category"], "integridade")

    def test_conflicting_positive_and_negative_signals_remain_prudent(self):
        comparison = {
            "quality_sufficient": True,
            "metrics": [
                {
                    "key": "started",
                    "label": "Incidentes iniciados",
                    "direction": "aumento",
                    "current_label": "8",
                    "previous_label": "4",
                    "percent_label": "+100.0%",
                    "interpretation": "Piora observada",
                },
                {
                    "key": "resolved_average_seconds",
                    "label": "Duração média dos resolvidos",
                    "direction": "redução",
                    "current_label": "1h 0min",
                    "previous_label": "3h 0min",
                    "percent_label": "-66.7%",
                    "interpretation": "Melhora observada",
                },
            ],
        }
        result = build([incident()], comparison=comparison)
        interpretations = {item["impact"] for item in result["findings"]}
        self.assertIn("Piora observada", interpretations)
        self.assertIn("Melhora observada", interpretations)

    def test_text_is_sanitized_and_structure_is_deterministic(self):
        unsafe = "Unidade 10.1.2.3 https://private.invalid token=segredo"
        incidents = [incident(unit=unsafe, equipment=unsafe)]
        first = build(incidents)
        second = build(copy.deepcopy(incidents))
        serialized = repr(first)
        self.assertEqual(first, second)
        self.assertNotIn("10.1.2.3", serialized)
        self.assertNotIn("private.invalid", serialized)
        self.assertNotIn("segredo", serialized)
        self.assertEqual(
            sanitize_executive_text(unsafe),
            "Unidade [IP omitido] [URL omitida] token=[omitido]",
        )

    def test_fully_sanitized_identifier_uses_a_safe_descriptive_fallback(self):
        self.assertEqual(
            sanitize_executive_identifier("10.1.2.3", "Unidade com identificação protegida"),
            "Unidade com identificação protegida",
        )
        summary = build_report_summary([incident(unit="10.1.2.3", equipment="https://x.test")])
        result = build_executive_summary(
            summary,
            None,
            {**VALID_INTEGRITY, "received": 1, "processed": 1},
            "31/07/2026 12:00",
            "últimas 24 horas",
        )
        evidence = " ".join(item["evidence"] for item in result["findings"])
        self.assertIn("Unidade com identificação protegida", evidence)
        self.assertIn("Equipamento com identificação protegida", evidence)
        self.assertNotIn("[IP omitido]:", evidence)
        self.assertNotIn("[URL omitida]:", evidence)

    def test_large_volume_is_bounded_and_repeatable(self):
        incidents = [
            incident(
                index,
                incident_key=f"condition-{index % 400}",
                host=f"HOST-{index % 600}",
                unit=f"Unidade {index % 20}",
                equipment=("Câmera", "Switch", "Mikrotik")[index % 3],
            )
            for index in range(20_000)
        ]
        first = build(incidents)
        second = build(incidents)
        self.assertEqual(first, second)
        self.assertLessEqual(len(first["findings"]), 5)


if __name__ == "__main__":
    unittest.main()
