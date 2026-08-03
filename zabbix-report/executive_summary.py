"""Síntese executiva determinística construída somente com dados canônicos."""

from __future__ import annotations

import re

SENSITIVE_PATTERNS = (
    (re.compile(r"https?://\S+", re.IGNORECASE), "[URL omitida]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP omitido]"),
    (
        re.compile(
            r"\b(token|password|senha|secret|authorization|api[_-]?key)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
        r"\1=[omitido]",
    ),
)


def sanitize_executive_text(value):
    """Remove dados sensíveis previsíveis antes de qualquer exportação."""

    text = str(value or "").replace("\r", " ").replace("\n", " ")
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return " ".join(text.split())


def _finding(category, title, explanation, evidence, level, impact, recommendation, priority):
    return {
        "category": category,
        "title": sanitize_executive_text(title),
        "explanation": sanitize_executive_text(explanation),
        "evidence": sanitize_executive_text(evidence),
        "level": level,
        "impact": sanitize_executive_text(impact),
        "recommendation": sanitize_executive_text(recommendation),
        "priority": priority,
    }


def _confidence(integrity, comparison, event_total):
    discarded = int(integrity.get("discarded", 0) or 0)
    adjusted = int(integrity.get("adjusted", 0) or 0)
    warnings = int(integrity.get("warning_count", 0) or 0)
    comparison_limited = bool(comparison) and not comparison.get("quality_sufficient", False)

    if discarded or comparison_limited:
        reason = "Existem descartes ou limitação de integridade em pelo menos uma janela."
        return "Limitado", reason
    if not event_total:
        return "Moderado", "Não há eventos suficientes para uma leitura operacional abrangente."
    if adjusted or warnings:
        return "Moderado", "Os dados foram processados com normalizações ou avisos controlados."
    return "Alto", "Os registros usados na síntese foram validados sem descartes ou avisos."


def _comparison_findings(comparison):
    if not comparison or not comparison.get("quality_sufficient"):
        return []

    metrics = {item.get("key"): item for item in comparison.get("metrics", [])}
    candidates = []
    rules = (
        ("high_started", "Severidades altas no fluxo", 24),
        ("started", "Volume de incidentes iniciados", 28),
        ("recurrences", "Recorrência entre períodos", 22),
        ("resolved_average_seconds", "Tempo de resolução", 26),
        ("resolved", "Volume de encerramentos", 34),
    )
    for key, title, priority in rules:
        item = metrics.get(key)
        if not item or item.get("direction") in {"estabilidade", "indisponível"}:
            continue
        interpretation = item.get("interpretation", "")
        level = (
            "atenção" if "Piora" in interpretation or "Atenção" in interpretation else "informativo"
        )
        candidates.append(
            _finding(
                "tendência",
                title,
                f"{item.get('label', title)} apresentou {item.get('direction', 'mudança')} em relação à janela anterior.",
                f"Atual: {item.get('current_label', '-')} · anterior: {item.get('previous_label', '-')} · variação: {item.get('percent_label', 'não disponível')}.",
                level,
                interpretation or "Mudança operacional observada.",
                (
                    "Revisar os fatores operacionais associados à piora observada."
                    if level == "atenção"
                    else "Manter acompanhamento para confirmar a evolução nas próximas janelas."
                ),
                priority,
            )
        )
    return candidates[:2]


def build_executive_summary(summary, comparison, integrity, generated, period_label):
    """Retorna a estrutura única consumida por HTML, Excel e PDF."""

    summary = summary or {}
    integrity = integrity or {}
    event_total = int(summary.get("event_total", 0) or 0)
    open_total = int(summary.get("unique_open", 0) or 0)
    confidence, confidence_reason = _confidence(integrity, comparison, event_total)
    findings = []

    if not event_total:
        findings.append(
            _finding(
                "operação",
                "Sem ocorrências no recorte",
                "Nenhum evento foi registrado no período analisado; isso não comprova disponibilidade total da infraestrutura.",
                "0 eventos processados no escopo operacional.",
                "informativo",
                "A leitura fica restrita à ausência de registros no recorte.",
                "Confirmar a cobertura da coleta e manter o acompanhamento operacional regular.",
                40,
            )
        )
    else:
        priority = summary.get("priority", {})
        critical_units = summary.get("unit_criticality", {})
        critical_count = int(priority.get("critical", 0) or 0)
        high_priority = int(priority.get("high", 0) or 0)
        intervention_units = int(critical_units.get("critical", 0) or 0)
        high_severity = int(summary.get("high", 0) or 0) + int(summary.get("critical", 0) or 0)
        high_ratio = high_severity / event_total if event_total else 0

        if critical_count or intervention_units:
            findings.append(
                _finding(
                    "criticidade",
                    "Prioridade operacional elevada",
                    "A combinação de severidade, permanência e impacto posicionou itens no nível máximo de atuação.",
                    f"{critical_count} prioridades críticas e {intervention_units} unidades para intervenção imediata.",
                    "crítico",
                    "Há risco de indisponibilidade prolongada ou impacto concentrado.",
                    "Atuar primeiro nas unidades e ocorrências com maior score de criticidade.",
                    5,
                )
            )
        elif high_priority:
            findings.append(
                _finding(
                    "criticidade",
                    "Fila com prioridade alta",
                    "O passivo contém ocorrências que exigem acompanhamento ativo do NOC.",
                    f"{high_priority} prioridades altas entre {open_total} incidentes únicos abertos.",
                    "atenção",
                    "A demora na atuação pode ampliar o tempo de indisponibilidade.",
                    "Ordenar a fila pelo score e validar primeiro as ocorrências de maior severidade.",
                    10,
                )
            )

        if high_severity:
            findings.append(
                _finding(
                    "severidade",
                    "Concentração de severidades altas",
                    "Eventos classificados como Alta ou Desastre representam parte relevante do fluxo analisado.",
                    f"{high_severity} de {event_total} eventos ({high_ratio * 100:.1f}%).",
                    "crítico" if high_ratio >= 0.25 and high_severity >= 2 else "atenção",
                    "Severidades altas podem indicar maior impacto operacional.",
                    "Validar os eventos de Alta e Desastre e confirmar o impacto nos ativos afetados.",
                    12,
                )
            )

        age = summary.get("age", {})
        aged = int(age.get("over_7d", 0) or 0)
        if aged:
            findings.append(
                _finding(
                    "envelhecimento",
                    "Passivo aberto envelhecido",
                    "Há incidentes abertos acima de sete dias, separados das durações históricas já encerradas.",
                    f"{aged} incidentes acima de 7 dias; mais antigo: {age.get('oldest_label', '-')}.",
                    "crítico" if open_total and aged / open_total >= 0.25 else "atenção",
                    "O passivo antigo aumenta o risco de normalização operacional da indisponibilidade.",
                    "Revisar responsáveis, evidências e próximos passos dos incidentes mais antigos.",
                    14,
                )
            )

        recurrence = summary.get("recurrence", {})
        recurrent_hosts = int(recurrence.get("affected_hosts", 0) or 0)
        recurrent_events = int(recurrence.get("total_recurrent_events", 0) or 0)
        if recurrent_hosts:
            findings.append(
                _finding(
                    "recorrência",
                    "Falhas reincidentes exigem causa raiz",
                    "Os mesmos hosts e sintomas reapareceram no período analisado.",
                    f"{recurrent_hosts} hosts reincidentes e {recurrent_events} repetições além da ocorrência inicial.",
                    "atenção",
                    "A repetição pode consumir capacidade do NOC sem eliminar a origem do problema.",
                    "Selecionar os hosts mais reincidentes e abrir análise de causa raiz.",
                    18,
                )
            )

        top_unit = (summary.get("top_units") or [{}])[0]
        unit_percent = float(top_unit.get("percent", 0) or 0)
        if top_unit.get("name") and unit_percent >= 30:
            findings.append(
                _finding(
                    "concentração",
                    "Impacto concentrado em uma unidade",
                    "Uma única unidade concentra parcela expressiva dos eventos do recorte.",
                    f"{sanitize_executive_text(top_unit['name'])}: {top_unit.get('total', 0)} eventos ({unit_percent:.1f}%).",
                    "atenção",
                    "A concentração permite atuação localizada, mas amplia o impacto naquela unidade.",
                    "Priorizar a unidade concentradora e validar seus equipamentos mais afetados.",
                    20,
                )
            )

        top_equipment = (summary.get("top_equipment") or [{}])[0]
        if top_equipment.get("name") and float(top_equipment.get("percent", 0) or 0) >= 35:
            findings.append(
                _finding(
                    "equipamento",
                    "Concentração por tipo de equipamento",
                    "Um tipo de equipamento responde por parcela relevante dos eventos analisados.",
                    f"{sanitize_executive_text(top_equipment['name'])}: {top_equipment.get('total', 0)} eventos ({float(top_equipment.get('percent', 0) or 0):.1f}%).",
                    "atenção",
                    "Uma falha comum de tecnologia ou configuração pode ampliar o volume operacional.",
                    "Revisar o padrão técnico dos equipamentos concentradores e as ocorrências associadas.",
                    24,
                )
            )

        findings.extend(_comparison_findings(comparison))

    if integrity.get("discarded", 0):
        findings.append(
            _finding(
                "integridade",
                "Leitura possivelmente incompleta",
                "Registros sem confiabilidade suficiente foram descartados antes da construção dos indicadores.",
                f"{integrity.get('discarded', 0)} descartados de {integrity.get('received', 0)} recebidos.",
                "atenção",
                "As conclusões não devem ser tratadas como definitivas.",
                "Revisar as categorias de descarte antes de decisões executivas definitivas.",
                1,
            )
        )

    findings = sorted(
        findings, key=lambda item: (item["priority"], item["category"], item["title"])
    )[:5]
    critical_signals = sum(item["level"] == "crítico" for item in findings)
    attention_signals = sum(item["level"] == "atenção" for item in findings)

    if confidence == "Limitado" and (not event_total or integrity.get("discarded", 0)):
        situation = "Dados insuficientes"
    elif critical_signals >= 2 or (critical_signals and attention_signals):
        situation = "Crítica"
    elif critical_signals or attention_signals:
        situation = "Atenção"
    else:
        situation = "Estável"

    conclusion = {
        "Estável": "O recorte não apresenta sinais combinados de criticidade, sem equivaler a garantia de disponibilidade total.",
        "Atenção": "Há sinais objetivos que exigem acompanhamento e priorização operacional do NOC.",
        "Crítica": "Múltiplos sinais relevantes indicam necessidade de atuação coordenada e priorização imediata.",
        "Dados insuficientes": "A integridade ou a quantidade de dados limita uma conclusão operacional definitiva.",
    }[situation]

    return {
        "situation": situation,
        "confidence": confidence,
        "confidence_reason": sanitize_executive_text(confidence_reason),
        "findings": findings,
        "conclusion": conclusion,
        "comparison_available": bool(comparison),
        "comparison_note": (
            "Tendências usam o comparativo canônico entre janelas equivalentes."
            if comparison
            else "Sem base comparativa; a síntese descreve somente a situação atual."
        ),
        "generated": sanitize_executive_text(generated),
        "period": sanitize_executive_text(period_label),
    }
