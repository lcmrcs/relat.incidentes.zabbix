"""Observabilidade local, segura e sem dependências externas.

O módulo mede etapas com ``perf_counter()``, resume gargalos e opcionalmente
persiste métricas técnicas em JSON. Ele nunca recebe payloads, credenciais,
URLs, hosts ou conteúdo de incidentes.
"""

import json
import logging
import re
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger("zabbix-report.observability")

STAGE_LABELS = {
    "configuration": "Configuração",
    "api_collection": "Coleta da API",
    "problem_search": "Busca de problemas",
    "recovery_search": "Busca de recuperações",
    "trigger_host_search": "Busca de triggers e hosts",
    "unit_catalog": "Catálogo de unidades",
    "validation": "Validação e normalização",
    "incident_build": "Construção dos incidentes",
    "summaries": "Geração dos resumos",
    "excel_export": "Exportação do Excel",
    "excel_dataframes": "Excel · criação dos DataFrames",
    "excel_sheet_writes": "Excel · escrita das abas",
    "excel_base_styles": "Excel · estilos-base",
    "excel_column_widths": "Excel · larguras das colunas",
    "excel_tables": "Excel · tabelas e filtros",
    "excel_conditional_formatting": "Excel · formatação condicional",
    "excel_charts": "Excel · gráficos",
    "excel_save": "Excel · salvamento final",
    "html_export": "Renderização do HTML",
    "pdf_export": "PDF executivo",
    "technical_pdf_export": "Anexo técnico",
    "report_cleanup": "Limpeza de relatórios",
    "diagnostic_json": "Diagnóstico JSON",
}

DEFAULT_THRESHOLDS = {
    "api_call_seconds": 10.0,
    "export_seconds": 15.0,
    "total_seconds": 60.0,
    "pdf_size_bytes": 25 * 1024 * 1024,
    "technical_pdf_size_bytes": 100 * 1024 * 1024,
    "high_event_volume": 10_000,
    "disproportionate_percent": 60.0,
    "disproportionate_min_seconds": 2.0,
}


def format_bytes(size):
    """Formata bytes sem perder o valor inteiro usado no JSON."""

    size = max(0, int(size or 0))
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


class ExecutionDiagnostics:
    """Coleta métricas de uma execução e produz saídas seguras e testáveis."""

    def __init__(self, period, clock=None, wall_clock=None, thresholds=None):
        self.period = str(period or "não informado")
        self.clock = clock or time.perf_counter
        self.wall_clock = wall_clock or datetime.now
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.started_at = self.wall_clock()
        self.started_counter = self.clock()
        self.finished_at = None
        self.total_seconds = 0.0
        self.stages = {}
        self.stage_order = []
        self.api_calls = []
        self.files = {}
        self.records = {
            "received": 0,
            "processed": 0,
            "adjusted": 0,
            "discarded": 0,
            "warnings": 0,
        }
        self.event_groups = {
            "units": 0,
            "zabbix_server": 0,
            "confea": 0,
        }
        self.warnings = []

    @contextmanager
    def measure(self, name):
        """Mede uma etapa, inclusive quando ela termina com exceção."""

        started = self.clock()
        error_type = None
        try:
            yield
        except (Exception, SystemExit) as error:
            error_type = type(error).__name__
            raise
        finally:
            duration = max(0.0, self.clock() - started)
            self._record_stage(name, duration, error_type)

    def _record_stage(self, name, duration, error_type=None):
        if name not in self.stages:
            self.stages[name] = {
                "name": name,
                "label": STAGE_LABELS.get(name, name.replace("_", " ").title()),
                "duration_seconds": 0.0,
                "runs": 0,
                "status": "completed",
            }
            self.stage_order.append(name)

        stage = self.stages[name]
        stage["duration_seconds"] += round(float(duration), 6)
        stage["runs"] += 1
        if error_type:
            stage["status"] = "failed"
            stage["error_type"] = error_type
            LOGGER.error(
                "Falha na etapa %s após %.2fs: %s",
                stage["label"],
                duration,
                error_type,
            )

    def record_api_call(self, operation, duration, success=True, error_type=None):
        """Registra somente método, tempo e resultado seguro da chamada."""

        operation = str(operation or "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", operation):
            operation = "unknown"
        call = {
            "operation": operation,
            "duration_seconds": round(max(0.0, float(duration)), 6),
            "success": bool(success),
        }
        if error_type:
            call["error_type"] = str(error_type)
        self.api_calls.append(call)

        if duration >= self.thresholds["api_call_seconds"]:
            self.add_warning(
                "slow_api_call",
                f"Chamada {call['operation']} levou {duration:.2f}s; o volume ou a rede podem "
                "estar influenciando a coleta.",
                stage="api_collection",
            )

    def set_record_counts(self, integrity):
        """Copia apenas contagens do resumo canônico de integridade."""

        integrity = integrity or {}
        for key in ("received", "processed", "adjusted", "discarded"):
            self.records[key] = max(0, int(integrity.get(key, 0) or 0))
        self.records["warnings"] = max(0, int(integrity.get("warning_count", 0) or 0))

    def set_event_groups(self, units, zabbix_server, confea):
        self.event_groups = {
            "units": max(0, int(units or 0)),
            "zabbix_server": max(0, int(zabbix_server or 0)),
            "confea": max(0, int(confea or 0)),
        }

    def record_file(self, kind, path, pages=None, completed=True):
        """Registra nome, tamanho e páginas sem guardar caminho completo."""

        path = Path(path)
        size = path.stat().st_size if completed and path.exists() else 0
        metric = {
            "format": str(kind),
            "size_bytes": size,
            "completed": bool(completed and path.exists()),
        }
        if pages is not None:
            metric["pages"] = max(0, int(pages))
        self.files[str(kind)] = metric

        threshold_key = "technical_pdf_size_bytes" if kind == "technical_pdf" else "pdf_size_bytes"
        if kind in {"pdf", "technical_pdf"} and size >= self.thresholds[threshold_key]:
            self.add_warning(
                "large_pdf",
                f"{'Anexo técnico' if kind == 'technical_pdf' else 'PDF executivo'} possui "
                f"{format_bytes(size)}; revise o volume do documento.",
                stage="technical_pdf_export" if kind == "technical_pdf" else "pdf_export",
            )
        return metric

    def record_failed_file(self, kind, path, error):
        self.files[str(kind)] = {
            "format": str(kind),
            "size_bytes": 0,
            "completed": False,
            "error_type": type(error).__name__,
        }

    def add_warning(self, code, message, stage=None):
        warning = {"code": str(code), "message": str(message)}
        if stage:
            warning["stage"] = str(stage)
        if warning not in self.warnings:
            self.warnings.append(warning)
            LOGGER.warning("%s", warning["message"])

    def finalize(self):
        """Fecha a execução e calcula percentuais e gargalos."""

        if self.finished_at is None:
            self.total_seconds = round(max(0.0, self.clock() - self.started_counter), 6)
            self.finished_at = self.wall_clock()

        for stage in self.stages.values():
            duration = stage["duration_seconds"]
            stage["percent_total"] = (
                round((duration / self.total_seconds) * 100, 1) if self.total_seconds else 0.0
            )
            if stage["name"].endswith("_export") and duration >= self.thresholds["export_seconds"]:
                self.add_warning(
                    "slow_export",
                    f"{stage['label']} levou {duration:.2f}s; o volume pode estar influenciando "
                    "a exportação.",
                    stage=stage["name"],
                )

        total_events = sum(self.event_groups.values())
        if total_events >= self.thresholds["high_event_volume"]:
            self.add_warning(
                "high_event_volume",
                f"Volume elevado: {total_events} eventos no escopo da execução.",
                stage="incident_build",
            )
        if self.total_seconds >= self.thresholds["total_seconds"]:
            self.add_warning(
                "slow_execution",
                f"Execução concluída em {self.total_seconds:.2f}s; avalie a etapa mais demorada.",
            )

        bottleneck = self.slowest_stage
        if (
            bottleneck
            and bottleneck["duration_seconds"] >= self.thresholds["disproportionate_min_seconds"]
            and bottleneck["percent_total"] >= self.thresholds["disproportionate_percent"]
        ):
            self.add_warning(
                "disproportionate_stage",
                f"{bottleneck['label']} consumiu {bottleneck['percent_total']:.1f}% do tempo total.",
                stage=bottleneck["name"],
            )
        return self

    @property
    def slowest_stage(self):
        if not self.stages:
            return None
        return max(self.stages.values(), key=lambda item: item["duration_seconds"])

    def as_dict(self):
        self.finalize()
        slowest = self.slowest_stage
        api_total = sum(item["duration_seconds"] for item in self.api_calls)
        return {
            "schema_version": 1,
            "period_requested": self.period,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "finished_at": self.finished_at.isoformat(timespec="seconds"),
            "total_seconds": self.total_seconds,
            "records": dict(self.records),
            "event_groups": dict(self.event_groups),
            "api": {
                "call_count": len(self.api_calls),
                "total_seconds": round(api_total, 6),
                "calls": list(self.api_calls),
            },
            "stages": [dict(self.stages[name]) for name in self.stage_order],
            "files": dict(self.files),
            "bottleneck": (
                {
                    "stage": slowest["name"],
                    "label": slowest["label"],
                    "duration_seconds": slowest["duration_seconds"],
                    "percent_total": slowest["percent_total"],
                }
                if slowest
                else None
            ),
            "warnings": list(self.warnings),
        }

    def write_json(self, path):
        """Grava o diagnóstico estruturado sem aceitar dados operacionais."""

        path = Path(path)
        path.write_text(
            json.dumps(self.as_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def print_terminal_summary(self):
        """Exibe uma síntese compacta, adequada ao fluxo normal do terminal."""

        data = self.as_dict()
        stage_times = {item["name"]: item["duration_seconds"] for item in data["stages"]}
        file_labels = {
            "html": "HTML",
            "excel": "Excel",
            "pdf": "PDF",
            "technical_pdf": "Anexo",
        }
        exports = [
            f"{file_labels[kind]} {format_bytes(metric['size_bytes'])}"
            for kind, metric in data["files"].items()
            if metric.get("completed") and kind in {"html", "excel", "pdf", "technical_pdf"}
        ]
        bottleneck = data["bottleneck"]

        print("\nDIAGNÓSTICO DA EXECUÇÃO")
        print("-----------------------")
        print(f"Tempo total: {data['total_seconds']:.2f}s")
        print(
            "Coleta API: "
            f"{stage_times.get('api_collection', 0):.2f}s "
            f"({data['api']['call_count']} chamada(s))"
        )
        print(
            "Processamento: "
            f"{sum(stage_times.get(name, 0) for name in ('validation', 'incident_build', 'summaries')):.2f}s"
        )
        print(
            "Exportações: "
            f"Excel {stage_times.get('excel_export', 0):.2f}s · "
            f"HTML {stage_times.get('html_export', 0):.2f}s · "
            f"PDF {stage_times.get('pdf_export', 0):.2f}s"
        )
        print(
            f"Registros: {self.records['processed']} processados · "
            f"{self.records['adjusted']} ajustados · {self.records['discarded']} descartados"
        )
        if exports:
            print(f"Arquivos: {' · '.join(exports)}")
        if bottleneck:
            print(
                f"Etapa mais demorada: {bottleneck['label']} "
                f"({bottleneck['duration_seconds']:.2f}s · {bottleneck['percent_total']:.1f}%)"
            )
        print(
            f"Avisos: {self.records['warnings']} de integridade · "
            f"{len(data['warnings'])} de desempenho"
        )


def write_optional_diagnostic(enabled, diagnostics, path):
    """Gera o JSON somente quando a opção explícita estiver ativa."""

    if not enabled:
        return None
    return diagnostics.write_json(path)
