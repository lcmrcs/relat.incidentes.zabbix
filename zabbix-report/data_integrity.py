"""Validação segura dos registros recebidos antes da construção dos incidentes."""

import logging
from collections import Counter
from datetime import datetime

from classifiers import SEVERITY_MAP, classify_equipment, classify_unit_group

LOGGER = logging.getLogger("zabbix-report.integrity")


ISSUE_DEFINITIONS = {
    "missing_eventid": ("Evento sem identificador", "Descartado", "Sem rastreabilidade confiável."),
    "duplicate_eventid": ("Evento duplicado", "Duplicata descartada", "Evita contagem repetida."),
    "invalid_timestamp": (
        "Timestamp ausente ou inválido",
        "Descartado",
        "Duração não pode ser calculada.",
    ),
    "future_timestamp": (
        "Timestamp futuro",
        "Descartado",
        "Evento fora da linha temporal confiável.",
    ),
    "missing_objectid": (
        "Objeto ausente",
        "Descartado",
        "Não é possível relacionar o evento ao ativo.",
    ),
    "missing_description": ("Descrição ausente", "Normalizada", "Exibida como não informada."),
    "invalid_recovery": (
        "Recuperação inconsistente",
        "Mantido como aberto",
        "Duração resolvida não é confiável.",
    ),
    "missing_host": (
        "Host não identificado",
        "Mantido com aviso",
        "Classificação do ativo pode ficar limitada.",
    ),
    "unidentified_unit": (
        "Unidade não identificada",
        "Mantido em infraestrutura",
        "Não entra como unidade escolar.",
    ),
    "unclassified_equipment": (
        "Equipamento não classificado",
        "Mantido como diversos",
        "Ranking fica menos específico.",
    ),
    "unknown_severity": (
        "Severidade desconhecida",
        "Normalizada",
        "Tratada como não classificada.",
    ),
    "unexpected_record": ("Registro inesperado", "Descartado", "Formato não suportado."),
}


def _timestamp(value):
    if value in (None, "", "0", 0):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(datetime.strptime(str(value), "%d/%m/%Y %H:%M").timestamp())
        except (TypeError, ValueError, OverflowError):
            return None


def _summary(received, processed, adjusted, discarded, counts):
    issues = [
        {
            "key": key,
            "category": ISSUE_DEFINITIONS[key][0],
            "quantity": counts[key],
            "treatment": ISSUE_DEFINITIONS[key][1],
            "impact": ISSUE_DEFINITIONS[key][2],
        }
        for key in ISSUE_DEFINITIONS
        if counts[key]
    ]
    level = "incomplete" if discarded else ("warning" if issues else "valid")
    return {
        "received": received,
        "processed": processed,
        "adjusted": adjusted,
        "discarded": discarded,
        "duplicates": counts["duplicate_eventid"],
        "invalid_timestamps": counts["invalid_timestamp"] + counts["future_timestamp"],
        "inconsistent_recoveries": counts["invalid_recovery"],
        "unidentified_hosts": counts["missing_host"],
        "unidentified_units": counts["unidentified_unit"],
        "unidentified_equipment": counts["unclassified_equipment"],
        "unknown_severities": counts["unknown_severity"],
        "warning_count": sum(item["quantity"] for item in issues),
        "level": level,
        "label": {
            "valid": "Dados validados",
            "warning": f"{sum(item['quantity'] for item in issues)} aviso(s) de integridade",
            "incomplete": "Relatório possivelmente incompleto",
        }[level],
        "issues": issues,
    }


def validate_problem_records(
    problems,
    hosts_by_trigger,
    host_ids_by_trigger,
    host_details_by_id,
    resolved_at_by_event,
    unit_catalog,
    generated_at,
):
    """Normaliza dados recuperáveis e descarta somente registros não rastreáveis."""

    received = len(problems or [])
    counts = Counter()
    seen_eventids = set()
    valid = []
    adjusted_records = set()
    discarded = 0
    generated_timestamp = int(generated_at.timestamp())

    for index, raw in enumerate(problems or []):
        if not isinstance(raw, dict):
            counts["unexpected_record"] += 1
            discarded += 1
            continue

        item = dict(raw)
        eventid = str(item.get("eventid") or "").strip()
        if not eventid:
            counts["missing_eventid"] += 1
            discarded += 1
            continue
        if eventid in seen_eventids:
            counts["duplicate_eventid"] += 1
            discarded += 1
            continue
        seen_eventids.add(eventid)

        timestamp = _timestamp(item.get("clock"))
        if timestamp is None:
            counts["invalid_timestamp"] += 1
            discarded += 1
            continue
        if timestamp > generated_timestamp:
            counts["future_timestamp"] += 1
            discarded += 1
            continue
        if not item.get("objectid"):
            counts["missing_objectid"] += 1
            discarded += 1
            continue

        if not str(item.get("name") or "").strip():
            item["name"] = "Não informado"
            counts["missing_description"] += 1
            adjusted_records.add(index)

        severity = str(item.get("severity") if item.get("severity") is not None else "")
        if severity not in SEVERITY_MAP:
            item["severity"] = "0"
            counts["unknown_severity"] += 1
            adjusted_records.add(index)

        recovery_id = item.get("r_eventid")
        if recovery_id and recovery_id != "0":
            recovery_timestamp = _timestamp(resolved_at_by_event.get(recovery_id))
            if recovery_timestamp is None or recovery_timestamp < timestamp:
                item["r_eventid"] = "0"
                counts["invalid_recovery"] += 1
                adjusted_records.add(index)

        objectid = item.get("objectid")
        host = hosts_by_trigger.get(objectid)
        if not str(host or "").strip():
            counts["missing_host"] += 1
            adjusted_records.add(index)
            host = "N/A"

        host_id = host_ids_by_trigger.get(objectid)
        host_details = host_details_by_id.get(host_id, {})
        unit_code, _ = classify_unit_group(host, host_details, unit_catalog)
        if unit_code == "INFRA":
            counts["unidentified_unit"] += 1
            adjusted_records.add(index)
        if classify_equipment(host) == "Diversos":
            counts["unclassified_equipment"] += 1
            adjusted_records.add(index)

        valid.append(item)

    summary = _summary(received, len(valid), len(adjusted_records), discarded, counts)
    LOGGER.info(
        "Integridade: %d recebidos, %d processados, %d ajustados, %d descartados",
        summary["received"],
        summary["processed"],
        summary["adjusted"],
        summary["discarded"],
    )
    if summary["warning_count"]:
        LOGGER.warning(
            "Integridade identificou %d ocorrência(s) categorizada(s)", summary["warning_count"]
        )
    return valid, summary
