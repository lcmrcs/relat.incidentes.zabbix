"""
Montagem dos indicadores do relatório.

O HTML, o Excel e o PDF precisam dos mesmos totais. Centralizar esse cálculo
evita divergência entre os formatos de saída.
"""

from collections import Counter
from datetime import datetime

from classifiers import EQUIPMENT_ORDER


def format_age(seconds):
    """
    Converte segundos em texto curto de idade do incidente.

    Exemplo: 90061 segundos vira "1d 1h". O formato curto cabe melhor nos cards
    do relatório HTML e no PDF.
    """

    if seconds <= 0:
        return "0h"

    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)

    if days:
        return f"{days}d {hours}h"

    if hours:
        return f"{hours}h {minutes}min"

    return f"{minutes}min"


def build_age_summary(incidents):
    """
    Calcula idade dos incidentes abertos a partir do timestamp de abertura.

    Esses dados ajudam a identificar problemas esquecidos ou parados há muito
    tempo, algo que a contagem simples não mostra.
    """

    now = datetime.now().timestamp()
    dated_incidents = [
        item
        for item in incidents
        if item.get("timestamp")
    ]

    if not dated_incidents:
        return {
            "oldest": None,
            "newest": None,
            "oldest_label": "-",
            "newest_label": "-",
            "average_label": "-",
            "over_1d": 0,
            "over_2d": 0,
            "over_5d": 0,
            "over_7d": 0,
            "over_30d": 0,
            "over_90d": 0,
            "range_24h": 0,
            "range_1_3d": 0,
            "range_4_10d": 0,
            "range_11_20d": 0,
            "range_21_30d": 0,
            "range_31_50d": 0,
            "range_51_75d": 0,
            "range_76_90d": 0,
            "range_over_90d": 0,
        }

    sorted_by_age = sorted(dated_incidents, key=lambda item: item["timestamp"])
    ages = [
        max(0, now - item["timestamp"])
        for item in dated_incidents
    ]

    return {
        "oldest": sorted_by_age[0],
        "newest": sorted_by_age[-1],
        "oldest_label": format_age(max(0, now - sorted_by_age[0]["timestamp"])),
        "newest_label": format_age(max(0, now - sorted_by_age[-1]["timestamp"])),
        "average_label": format_age(sum(ages) / len(ages)),
        "over_1d": sum(1 for age in ages if age >= 86400),
        "over_2d": sum(1 for age in ages if age >= 172800),
        "over_5d": sum(1 for age in ages if age >= 432000),
        "over_7d": sum(1 for age in ages if age >= 604800),
        "over_30d": sum(1 for age in ages if age >= 2592000),
        "over_90d": sum(1 for age in ages if age >= 7776000),
        "range_24h": sum(1 for age in ages if age < 86400),
        "range_1_3d": sum(1 for age in ages if 86400 <= age < 345600),
        "range_4_10d": sum(1 for age in ages if 345600 <= age < 950400),
        "range_11_20d": sum(1 for age in ages if 950400 <= age < 1814400),
        "range_21_30d": sum(1 for age in ages if 1814400 <= age < 2678400),
        "range_31_50d": sum(1 for age in ages if 2678400 <= age < 4406400),
        "range_51_75d": sum(1 for age in ages if 4406400 <= age < 6566400),
        "range_76_90d": sum(1 for age in ages if 6566400 <= age < 7862400),
        "range_over_90d": sum(1 for age in ages if age >= 7862400),
    }


def build_report_summary(incidents):
    """
    Calcula indicadores usados no HTML e na primeira página do PDF.

    O resumo evita recalcular contagens em vários pontos do código e concentra
    totais por severidade, equipamento e hosts mais afetados.
    """

    unique_incidents = {
        item["incident_key"]: item
        for item in incidents
    }

    unique_total = len(unique_incidents)
    unique_open = sum(
        1
        for item in unique_incidents.values()
        if item["status"] == "Aberto"
    )
    unique_resolved = unique_total - unique_open
    repeated_events = max(0, len(incidents) - unique_total)

    severity_counter = Counter(
        item["severity"]
        for item in incidents
    )
    status_counter = Counter(
        item["status"]
        for item in incidents
    )
    unit_counter = Counter(
        item["unit"]
        for item in incidents
    )
    equipment_counter = Counter(
        item["equipment"]
        for item in incidents
    )
    host_counter = Counter(
        item["host"]
        for item in incidents
        if item["host"] != "N/A"
    )

    total = len(incidents)
    avg_events_per_incident = (
        round(total / unique_total, 1)
        if unique_total
        else 0
    )
    age_summary = build_age_summary(incidents)

    def format_counter(counter, preferred_order=None):
        """
        Converte um Counter em lista de dicionários com total e percentual.

        O formato em lista é mais simples de percorrer no template HTML e no PDF.
        """

        ordered_items = []

        if preferred_order:
            ordered_items.extend([
                (name, counter[name])
                for name in preferred_order
                if counter.get(name, 0)
            ])

        ordered_names = {
            name
            for name, _ in ordered_items
        }
        ordered_items.extend([
            (name, count)
            for name, count in counter.most_common()
            if name not in ordered_names
        ])

        return [
            {
                "name": name,
                "total": count,
                "percent": round((count / total) * 100, 1) if total else 0,
            }
            for name, count in ordered_items
        ]

    return {
        "total": total,
        "event_total": total,
        "unique_total": unique_total,
        "unique_open": unique_open,
        "unique_resolved": unique_resolved,
        "repeated_events": repeated_events,
        "avg_events_per_incident": avg_events_per_incident,
        "age": age_summary,
        "unclassified": severity_counter.get("Não classificada", 0),
        "information": severity_counter.get("Informação", 0),
        "attention": severity_counter.get("Atenção", 0),
        "critical": severity_counter.get("Desastre", 0),
        "high": severity_counter.get("Alta", 0),
        "medium": severity_counter.get("Média", 0),
        "warning": severity_counter.get("Atenção", 0),
        "open": status_counter.get("Aberto", 0),
        "resolved": status_counter.get("Resolvido", 0),
        "status": format_counter(status_counter),
        "units": format_counter(unit_counter),
        "top_units": format_counter(unit_counter)[:12],
        "severity": format_counter(severity_counter),
        "equipment": format_counter(equipment_counter, EQUIPMENT_ORDER),
        "top_equipment": format_counter(equipment_counter)[:8],
        "top_hosts": format_counter(host_counter)[:8],
    }
