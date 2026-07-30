"""Modelo canônico do comparativo executivo entre duas janelas temporais."""

from collections import Counter
from datetime import timedelta

from summary import format_age
from time_utils import datetime_to_unix

HIGH_SEVERITIES = {"Alta", "Desastre"}


def build_comparison_windows(current_start, current_end):
    """Cria janelas inclusivas, equivalentes, adjacentes e sem sobreposição."""

    if current_start is None or current_end is None or current_start > current_end:
        raise ValueError("A comparação exige um período atual finito e válido.")

    duration = current_end - current_start
    previous_end = current_start - timedelta(seconds=1)
    previous_start = previous_end - duration
    return {
        "current": {
            "start": current_start,
            "end": current_end,
            "time_from": datetime_to_unix(current_start),
            "time_till": datetime_to_unix(current_end),
        },
        "previous": {
            "start": previous_start,
            "end": previous_end,
            "time_from": datetime_to_unix(previous_start),
            "time_till": datetime_to_unix(previous_end),
        },
    }


def _integrity_is_sufficient(integrity):
    integrity = integrity or {}
    return not integrity.get("discarded", 0) and integrity.get("level") != "incomplete"


def _period_metrics(incidents, window):
    started = [
        item
        for item in incidents
        if window["time_from"] <= (item.get("timestamp") or -1) <= window["time_till"]
    ]
    resolved = [
        item
        for item in incidents
        if item.get("status") == "Resolvido"
        and window["time_from"] <= (item.get("resolved_timestamp") or -1) <= window["time_till"]
    ]
    recurrence = Counter(item.get("incident_key") for item in started if item.get("incident_key"))
    host_recurrence = Counter(item.get("host") for item in started if item.get("host") != "N/A")
    durations = [item.get("duration_seconds", 0) or 0 for item in resolved]
    severities = Counter(item.get("severity", "Não classificada") for item in started)
    units = Counter(item.get("unit", "Não identificada") for item in started)
    equipment = Counter(item.get("equipment", "Não classificado") for item in started)
    return {
        "started": len(started),
        "resolved": len(resolved),
        "high_started": sum(1 for item in started if item.get("severity") in HIGH_SEVERITIES),
        "units_affected": len(units),
        "equipment_affected": len(equipment),
        "recurrent_hosts": sum(1 for count in host_recurrence.values() if count > 1),
        "recurrences": sum(max(0, count - 1) for count in recurrence.values()),
        "resolved_average_seconds": sum(durations) / len(durations) if durations else None,
        "severity": severities,
        "units": units,
        "equipment": equipment,
    }


def _variation(current, previous):
    if current is None or previous is None:
        return None, None, "indisponível"
    difference = current - previous
    if difference == 0:
        return difference, 0.0, "estabilidade"
    direction = "aumento" if difference > 0 else "redução"
    if previous == 0:
        return difference, None, "novo aumento"
    return difference, round((difference / previous) * 100, 1), direction


def _interpret(direction, favorable):
    if direction == "indisponível":
        return "Dados insuficientes"
    if direction == "estabilidade":
        return "Estabilidade"
    if favorable == "cautious":
        return "Atenção necessária: volume encerrado exige leitura contextual"
    improved = (direction == "redução" and favorable == "lower") or (
        direction in {"aumento", "novo aumento"} and favorable == "higher"
    )
    return "Melhora observada" if improved else "Piora observada"


def _metric(key, label, current, previous, favorable="lower", formatter=None, sufficient=True):
    if not sufficient:
        current_value = previous_value = None
    else:
        current_value, previous_value = current, previous
    difference, percent, direction = _variation(current_value, previous_value)
    display = formatter or (lambda value: "Não disponível" if value is None else str(value))
    return {
        "key": key,
        "label": label,
        "current": current_value,
        "previous": previous_value,
        "current_label": display(current_value),
        "previous_label": display(previous_value),
        "difference": difference,
        "difference_label": (
            "Não disponível" if difference is None else f"{difference:+.1f}".replace(".0", "")
        ),
        "percent": percent,
        "percent_label": (
            "Não disponível"
            if direction == "indisponível"
            else "Novo aumento" if direction == "novo aumento" else f"{percent:+.1f}%"
        ),
        "direction": direction,
        "interpretation": _interpret(direction, favorable),
    }


def _ranking_changes(current, previous, limit=5):
    names = set(current) | set(previous)
    changes = [
        {
            "name": name,
            "current": current.get(name, 0),
            "previous": previous.get(name, 0),
            "difference": current.get(name, 0) - previous.get(name, 0),
        }
        for name in names
    ]
    return sorted(
        changes, key=lambda item: (abs(item["difference"]), item["current"]), reverse=True
    )[:limit]


def build_executive_comparison(
    current_incidents,
    previous_incidents,
    windows,
    current_integrity,
    previous_integrity,
):
    """Produz a única estrutura consumida por HTML, Excel e PDF."""

    current_integrity = current_integrity or {}
    previous_integrity = previous_integrity or {}
    current = _period_metrics(current_incidents, windows["current"])
    previous = _period_metrics(previous_incidents, windows["previous"])
    sufficient = _integrity_is_sufficient(current_integrity) and _integrity_is_sufficient(
        previous_integrity
    )
    definitions = [
        ("started", "Incidentes iniciados", "lower"),
        ("resolved", "Incidentes resolvidos", "cautious"),
        ("high_started", "Alta/Desastre iniciados", "lower"),
        ("units_affected", "Unidades afetadas", "lower"),
        ("equipment_affected", "Equipamentos afetados", "lower"),
        ("recurrent_hosts", "Hosts reincidentes", "lower"),
        ("recurrences", "Recorrências", "lower"),
    ]
    metrics = [
        _metric(key, label, current[key], previous[key], favorable, sufficient=sufficient)
        for key, label, favorable in definitions
    ]
    metrics.append(
        _metric(
            "resolved_average_seconds",
            "Duração média dos resolvidos",
            current["resolved_average_seconds"],
            previous["resolved_average_seconds"],
            "lower",
            lambda value: "Não disponível" if value is None else format_age(value),
            sufficient,
        )
    )

    for severity in sorted(set(current["severity"]) | set(previous["severity"])):
        metrics.append(
            _metric(
                f"severity_{severity}",
                f"Severidade · {severity}",
                current["severity"].get(severity, 0),
                previous["severity"].get(severity, 0),
                "lower",
                sufficient=sufficient,
            )
        )

    return {
        "enabled": True,
        "quality_sufficient": sufficient,
        "quality_label": (
            "Comparação com qualidade suficiente"
            if sufficient
            else "Comparação possivelmente incompleta"
        ),
        "current_label": (
            f"{windows['current']['start']:%d/%m/%Y %H:%M} a "
            f"{windows['current']['end']:%d/%m/%Y %H:%M}"
        ),
        "previous_label": (
            f"{windows['previous']['start']:%d/%m/%Y %H:%M} a "
            f"{windows['previous']['end']:%d/%m/%Y %H:%M}"
        ),
        "metrics": metrics,
        "unit_changes": _ranking_changes(current["units"], previous["units"]),
        "equipment_changes": _ranking_changes(current["equipment"], previous["equipment"]),
        "integrity": {
            "current": current_integrity,
            "previous": previous_integrity,
        },
        "integrity_note": (
            f"Integridade: atual com {current_integrity.get('discarded', 0)} descarte(s) "
            f"e {current_integrity.get('warning_count', 0)} aviso(s); anterior com "
            f"{previous_integrity.get('discarded', 0)} descarte(s) e "
            f"{previous_integrity.get('warning_count', 0)} aviso(s)."
        ),
        "note": (
            "Compara o fluxo das ocorrências retornadas nas duas janelas equivalentes; "
            "não reconstrói o passivo aberto no fim do período anterior."
        ),
    }
