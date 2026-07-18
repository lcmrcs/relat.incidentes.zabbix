"""
Montagem dos indicadores do relatório.

O HTML, o Excel e o PDF precisam dos mesmos totais. Centralizar esse cálculo
evita divergência entre os formatos de saída.
"""

from collections import Counter
from datetime import datetime

from classifiers import EQUIPMENT_ORDER

SEVERITY_SCORE = {
    "Não classificada": 5,
    "Informação": 10,
    "Atenção": 25,
    "Média": 42,
    "Alta": 66,
    "Desastre": 90,
}

PRIORITY_LEVELS = [
    (85, "Crítica", "critica"),
    (65, "Alta", "alta"),
    (38, "Média", "media"),
    (0, "Normal", "normal"),
]

EQUIPMENT_IMPACT_SCORE = {
    "Mikrotik": 100,
    "Switch": 88,
    "NVR": 74,
    "Central de Alarme": 66,
    "Portal Detector de Metal": 62,
    "Terminal Facial": 55,
    "Câmera": 42,
    "Servidor": 78,
}

UNIT_CRITICALITY_LEVELS = [
    (82, "Intervenção imediata", "critical"),
    (64, "Prioridade alta", "high"),
    (44, "Acompanhamento ativo", "medium"),
    (0, "Monitoramento normal", "normal"),
]


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


def priority_level(score):
    """
    Classifica um índice numérico em uma faixa executiva de prioridade.

    O índice combina severidade, tempo offline e recorrência. A faixa facilita a leitura
    para gestão sem expor o cálculo técnico no relatório.
    """

    for minimum, label, class_name in PRIORITY_LEVELS:
        if score >= minimum:
            return {
                "label": label,
                "class": class_name,
                "score": min(100, round(score)),
            }

    return {
        "label": "Normal",
        "class": "normal",
        "score": min(100, round(score)),
    }


def unit_criticality_level(score):
    """
    Converte o score de uma unidade em uma recomendação executiva.

    O texto é propositalmente orientado à ação, para que o ranking não seja
    apenas uma lista de números.
    """

    for minimum, label, class_name in UNIT_CRITICALITY_LEVELS:
        if score >= minimum:
            return {
                "label": label,
                "class": class_name,
                "score": min(100, round(score)),
            }

    return {
        "label": "Monitoramento normal",
        "class": "normal",
        "score": min(100, round(score)),
    }


def calculate_priority_score(incident, recurrence_count=1):
    """
    Calcula a urgência operacional de um incidente.

    A pontuação não substitui a severidade do Zabbix; ela cria uma leitura
    executiva combinando severidade, tempo offline e recorrência no mesmo host.
    """

    severity_score = SEVERITY_SCORE.get(incident.get("severity"), 8)
    age_seconds = max(0, incident.get("age_seconds", 0) or 0)

    if age_seconds >= 90 * 86400:
        age_score = 30
    elif age_seconds >= 30 * 86400:
        age_score = 24
    elif age_seconds >= 7 * 86400:
        age_score = 18
    elif age_seconds >= 3 * 86400:
        age_score = 12
    elif age_seconds >= 86400:
        age_score = 7
    else:
        age_score = 0

    recurrence_score = min(18, max(0, recurrence_count - 1) * 6)

    return min(100, severity_score + age_score + recurrence_score)


def build_age_summary(incidents):
    """
    Calcula idade dos incidentes abertos a partir do timestamp de abertura.

    Esses dados ajudam a identificar problemas esquecidos ou parados há muito
    tempo, algo que a contagem simples não mostra.
    """

    now = datetime.now().timestamp()
    dated_incidents = [
        item for item in incidents if item.get("status") == "Aberto" and item.get("timestamp")
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
        item.get("open_age_seconds", max(0, now - item["timestamp"])) for item in dated_incidents
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


def build_period_comparison(incidents, total):
    """
    Compara a concentração dos incidentes por faixas executivas de idade.

    Sem histórico persistido, este comparativo mostra onde o passivo operacional
    está concentrado: incidentes novos, recentes, envelhecidos e críticos.
    """

    ranges = [
        ("Últimas 24h", 0, 86400),
        ("1 a 3 dias", 86400, 345600),
        ("4 a 10 dias", 345600, 950400),
        ("11 a 30 dias", 950400, 2678400),
        ("+30 dias", 2678400, None),
    ]
    comparison = []

    for label, start, end in ranges:
        items = [
            item
            for item in incidents
            if item.get("age_seconds", 0) >= start
            and (end is None or item.get("age_seconds", 0) < end)
        ]
        high_count = sum(1 for item in items if item.get("severity") in {"Alta", "Desastre"})
        comparison.append(
            {
                "label": label,
                "total": len(items),
                "percent": round((len(items) / total) * 100, 1) if total else 0,
                "high": high_count,
                "open": len(items),
            }
        )

    leading = max(comparison, key=lambda item: item["total"], default=None)

    return {
        "ranges": comparison,
        "leading_label": leading["label"] if leading else "-",
        "leading_total": leading["total"] if leading else 0,
        "aging_total": sum(item["total"] for item in comparison[-2:]),
        "fresh_total": comparison[0]["total"] if comparison else 0,
    }


def build_recurrence_summary(incidents, recurrence_counter, total):
    """
    Identifica hosts e sintomas que aparecem repetidamente no período analisado.
    """

    recurrent_items = []
    seen_keys = set()

    for item in incidents:
        key = item.get("incident_key")
        count = recurrence_counter.get(key, 0)

        if not key or count <= 1 or key in seen_keys:
            continue

        seen_keys.add(key)

        recurrent_items.append(
            {
                "host": item.get("host", "N/A"),
                "unit": item.get("unit", "N/A"),
                "equipment": item.get("equipment", "N/A"),
                "incident_type": item.get("incident_type") or item.get("incident", "N/A"),
                "total": count,
                "percent": round((count / total) * 100, 1) if total else 0,
                "oldest_label": item.get("age_label", "-"),
                "score": calculate_priority_score(item, count),
            }
        )

    top_items = sorted(
        recurrent_items,
        key=lambda item: (item["total"], item["score"]),
        reverse=True,
    )[:8]

    return {
        "total_recurrent_events": sum(count - 1 for count in recurrence_counter.values()),
        "affected_hosts": len({item["host"] for item in recurrent_items}),
        "top": top_items,
    }


def build_priority_summary(incidents, recurrence_counter):
    """
    Gera uma leitura executiva dos incidentes que mais merecem atenção.
    """

    ranked = []

    for item in incidents:
        recurrence_key = item.get("incident_key")
        score = calculate_priority_score(
            item,
            recurrence_counter.get(recurrence_key, 1),
        )
        level = priority_level(score)
        ranked.append(
            {
                "score": level["score"],
                "label": level["label"],
                "class": level["class"],
                "host": item.get("host", "N/A"),
                "unit": item.get("unit", "N/A"),
                "equipment": item.get("equipment", "N/A"),
                "incident_type": item.get("incident_type") or item.get("incident", "N/A"),
                "severity": item.get("severity", "N/A"),
                "age_label": item.get("age_label", "-"),
                "open_age_label": item.get("open_age_label", item.get("age_label", "-")),
                "eventid": item.get("eventid", ""),
            }
        )

    by_level = Counter(item["label"] for item in ranked)
    top = sorted(
        ranked,
        key=lambda item: item["score"],
        reverse=True,
    )[:10]

    return {
        "top": top,
        "critical": by_level.get("Crítica", 0),
        "high": by_level.get("Alta", 0),
        "medium": by_level.get("Média", 0),
        "normal": by_level.get("Normal", 0),
        "average_score": (
            round(
                sum(item["score"] for item in ranked) / len(ranked),
                1,
            )
            if ranked
            else 0
        ),
    }


def build_unit_criticality_map(incidents, recurrence_counter):
    """
    Calcula o mapa de criticidade operacional por unidade escolar.

    A pontuação combina cinco fatores:
    - volume de incidentes;
    - severidade registrada no Zabbix;
    - tempo offline;
    - reincidência do mesmo host/sintoma;
    - impacto do tipo de equipamento afetado.
    """

    units = {}

    for item in incidents:
        unit = item.get("unit", "N/A")
        unit_code = item.get("unit_code", "")

        if unit not in units:
            units[unit] = {
                "name": unit,
                "code": unit_code,
                "incidents": [],
                "severity_counter": Counter(),
                "equipment_counter": Counter(),
                "recurrence_keys": set(),
                "max_age_seconds": 0,
            }

        recurrence_key = item.get("incident_key")
        recurrence_count = recurrence_counter.get(recurrence_key, 1)

        units[unit]["incidents"].append(item)
        units[unit]["severity_counter"][item.get("severity", "N/A")] += 1
        units[unit]["equipment_counter"][item.get("equipment", "N/A")] += 1
        if recurrence_count > 1:
            units[unit]["recurrence_keys"].add(recurrence_key)
        units[unit]["max_age_seconds"] = max(
            units[unit]["max_age_seconds"],
            item.get("age_seconds", 0) or 0,
        )

    max_volume = max(
        (len(data["incidents"]) for data in units.values()),
        default=0,
    )
    for data in units.values():
        data["recurrent_events"] = sum(
            recurrence_counter[key] - 1 for key in data["recurrence_keys"]
        )

    max_recurrence = max((data["recurrent_events"] for data in units.values()), default=0)

    ranked = []

    for data in units.values():
        incident_total = len(data["incidents"])
        severity_average = (
            sum(SEVERITY_SCORE.get(item.get("severity"), 8) for item in data["incidents"])
            / incident_total
            if incident_total
            else 0
        )
        age_average = (
            sum(item.get("age_seconds", 0) or 0 for item in data["incidents"]) / incident_total
            if incident_total
            else 0
        )

        if age_average >= 90 * 86400:
            age_score = 100
        elif age_average >= 30 * 86400:
            age_score = 82
        elif age_average >= 10 * 86400:
            age_score = 64
        elif age_average >= 3 * 86400:
            age_score = 44
        elif age_average >= 86400:
            age_score = 24
        else:
            age_score = 8

        equipment_average = (
            sum(EQUIPMENT_IMPACT_SCORE.get(item.get("equipment"), 34) for item in data["incidents"])
            / incident_total
            if incident_total
            else 0
        )
        volume_score = (incident_total / max_volume) * 100 if max_volume else 0
        recurrence_score = (
            (data["recurrent_events"] / max_recurrence) * 100 if max_recurrence else 0
        )

        score = (
            volume_score * 0.24
            + severity_average * 0.24
            + age_score * 0.20
            + recurrence_score * 0.18
            + equipment_average * 0.14
        )
        level = unit_criticality_level(score)
        top_equipment = data["equipment_counter"].most_common(1)
        top_severity = data["severity_counter"].most_common(1)
        equipment_mix = [
            {"name": name, "total": count}
            for name, count in data["equipment_counter"].most_common(4)
        ]
        severity_mix = [
            {"name": name, "total": count}
            for name, count in data["severity_counter"].most_common(3)
        ]

        ranked.append(
            {
                "name": data["name"],
                "code": data["code"],
                "score": level["score"],
                "level": level["label"],
                "class": level["class"],
                "total": incident_total,
                "severity_average": round(severity_average, 1),
                "age_label": format_age(age_average),
                "oldest_label": format_age(data["max_age_seconds"]),
                "recurrence": data["recurrent_events"],
                "top_equipment": top_equipment[0][0] if top_equipment else "-",
                "top_equipment_total": top_equipment[0][1] if top_equipment else 0,
                "affected_equipment_count": len(data["equipment_counter"]),
                "equipment_mix": equipment_mix,
                "top_severity": top_severity[0][0] if top_severity else "-",
                "top_severity_total": top_severity[0][1] if top_severity else 0,
                "severity_mix": severity_mix,
                "factors": {
                    "volume": round(volume_score),
                    "severity": round(severity_average),
                    "age": round(age_score),
                    "recurrence": round(recurrence_score),
                    "equipment": round(equipment_average),
                },
            }
        )

    ranked = sorted(
        ranked,
        key=lambda item: (item["score"], item["total"], item["recurrence"]),
        reverse=True,
    )
    by_level = Counter(item["level"] for item in ranked)

    return {
        "top": ranked[:8],
        "total_units": len(ranked),
        "critical": by_level.get("Intervenção imediata", 0),
        "high": by_level.get("Prioridade alta", 0),
        "medium": by_level.get("Acompanhamento ativo", 0),
        "normal": by_level.get("Monitoramento normal", 0),
        "average_score": (
            round(
                sum(item["score"] for item in ranked) / len(ranked),
                1,
            )
            if ranked
            else 0
        ),
    }


def build_unit_executive_rankings(incidents):
    """
    Cria rankings complementares por unidade escolar.

    Esses rankings evitam repetir a visão de volume puro: um destaca unidades
    com passivo mais antigo e outro evidencia concentração de severidade alta.
    """

    units = {}

    for item in incidents:
        unit = item.get("unit", "N/A")

        if unit not in units:
            units[unit] = {
                "name": unit,
                "total": 0,
                "high_total": 0,
                "oldest_seconds": 0,
                "oldest_label": "-",
            }

        units[unit]["total"] += 1

        if item.get("severity") in {"Alta", "Desastre"}:
            units[unit]["high_total"] += 1

        age_seconds = item.get("age_seconds", 0) or 0

        if age_seconds > units[unit]["oldest_seconds"]:
            units[unit]["oldest_seconds"] = age_seconds
            units[unit]["oldest_label"] = item.get("age_label") or format_age(age_seconds)

    aging_rank = sorted(
        (data for data in units.values() if data["oldest_seconds"] > 0),
        key=lambda item: (item["oldest_seconds"], item["total"]),
        reverse=True,
    )
    high_rank = sorted(
        (data for data in units.values() if data["high_total"] > 0),
        key=lambda item: (item["high_total"], item["total"]),
        reverse=True,
    )

    return {
        "oldest_units": [
            {
                "name": item["name"],
                "total": item["oldest_label"],
                "percent": (
                    round(
                        (item["oldest_seconds"] / aging_rank[0]["oldest_seconds"]) * 100,
                        1,
                    )
                    if aging_rank
                    else 0
                ),
                "detail": f"{item['total']} incidentes",
            }
            for item in aging_rank[:8]
        ],
        "high_severity_units": [
            {
                "name": item["name"],
                "total": item["high_total"],
                "percent": (
                    round(
                        (item["high_total"] / high_rank[0]["high_total"]) * 100,
                        1,
                    )
                    if high_rank
                    else 0
                ),
                "detail": f"{item['total']} incidentes",
            }
            for item in high_rank[:8]
        ],
    }


def build_report_summary(incidents):
    """
    Calcula indicadores usados no HTML e na primeira página do PDF.

    O resumo evita recalcular contagens em vários pontos do código e concentra
    totais por severidade, equipamento e hosts mais afetados.
    """

    grouped_incidents = {}
    for item in incidents:
        grouped_incidents.setdefault(item["incident_key"], []).append(item)

    # Uma condição é aberta se ao menos uma ocorrência do agrupamento continua aberta.
    unique_incidents = {
        key: next((item for item in items if item.get("status") == "Aberto"), items[-1])
        for key, items in grouped_incidents.items()
    }

    unique_total = len(unique_incidents)
    unique_open = sum(1 for item in unique_incidents.values() if item["status"] == "Aberto")
    unique_resolved = unique_total - unique_open
    repeated_events = max(0, len(incidents) - unique_total)

    severity_counter = Counter(item["severity"] for item in incidents)
    status_counter = Counter(item["status"] for item in incidents)
    unit_counter = Counter(item["unit"] for item in incidents)
    equipment_counter = Counter(item["equipment"] for item in incidents)
    incident_counter = Counter(item.get("incident_type", item["incident"]) for item in incidents)
    host_counter = Counter(item["host"] for item in incidents if item["host"] != "N/A")
    recurrence_counter = Counter(
        item.get("incident_key") for item in incidents if item.get("incident_key")
    )

    total = len(incidents)
    avg_events_per_incident = round(total / unique_total, 1) if unique_total else 0
    open_incidents = [item for item in incidents if item.get("status") == "Aberto"]
    age_summary = build_age_summary(open_incidents)
    period_comparison = build_period_comparison(open_incidents, len(open_incidents))
    recurrence_summary = build_recurrence_summary(
        incidents,
        recurrence_counter,
        total,
    )
    priority_summary = build_priority_summary(
        open_incidents,
        recurrence_counter,
    )
    unit_criticality = build_unit_criticality_map(
        open_incidents,
        recurrence_counter,
    )
    unit_rankings = build_unit_executive_rankings(open_incidents)

    def format_counter(counter, preferred_order=None):
        """
        Converte um Counter em lista de dicionários com total e percentual.

        O formato em lista é mais simples de percorrer no template HTML e no PDF.
        """

        ordered_items = []

        if preferred_order:
            ordered_items.extend(
                [(name, counter[name]) for name in preferred_order if counter.get(name, 0)]
            )

        ordered_names = {name for name, _ in ordered_items}
        ordered_items.extend(
            [(name, count) for name, count in counter.most_common() if name not in ordered_names]
        )

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
        "top_incident_types": format_counter(incident_counter)[:8],
        "top_hosts": format_counter(host_counter)[:8],
        "top_oldest_units": unit_rankings["oldest_units"],
        "top_high_severity_units": unit_rankings["high_severity_units"],
        "period_comparison": period_comparison,
        "recurrence": recurrence_summary,
        "priority": priority_summary,
        "unit_criticality": unit_criticality,
    }
