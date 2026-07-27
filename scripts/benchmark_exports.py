"""Benchmark reproduzível das exportações Excel e HTML com dados fictícios."""

import argparse
import json
import re
import statistics
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "zabbix-report"
sys.path.insert(0, str(REPORT_DIR))

from summary import build_report_summary  # noqa: E402
from zabbix_report import export_excel, render_html  # noqa: E402

DEFAULT_VOLUMES = [0, 10, 7171, 20_000]


def fake_incident(index):
    unit_number = 1000 + (index % 120)
    equipment = ("Switch", "Mikrotik", "Terminal Facial", "Câmera")[index % 4]
    severity = ("Alta", "Média", "Atenção", "Informação")[index % 4]
    age_seconds = (index % 240) * 3600
    return {
        "host": f"{unit_number}-HOST-{index % 300}",
        "unit_code": str(unit_number),
        "unit": f"{unit_number}-Unidade Escolar {unit_number}",
        "incident_key": f"{unit_number}|host-{index % 300}|{equipment}|falha-{index % 12}",
        "equipment": equipment,
        "incident": f"Indisponibilidade simulada do equipamento {index % 12}",
        "incident_type": f"Indisponibilidade {index % 12}",
        "severity": severity,
        "status": "Aberto",
        "date": "27/07/2026 08:00",
        "timestamp": 1785146400 - age_seconds,
        "age_seconds": age_seconds,
        "age_label": f"{age_seconds // 3600}h 0min",
        "duration_seconds": age_seconds,
        "duration_label": f"{age_seconds // 3600}h 0min",
        "open_age_seconds": age_seconds,
        "open_age_label": f"{age_seconds // 3600}h 0min",
        "resolved_at": "",
        "eventid": str(1_000_000 + index),
    }


def measure_export(callback):
    started = time.perf_counter()
    callback()
    return time.perf_counter() - started


def run_scenario(volume, runs, output_dir):
    incidents = [fake_incident(index) for index in range(volume)]
    summary = build_report_summary(incidents)
    integrity = {
        "received": volume,
        "processed": volume,
        "adjusted": 0,
        "discarded": 0,
        "warning_count": 0,
        "level": "valid",
        "label": "Dados validados",
        "issues": [],
    }
    excel_times = []
    html_times = []
    excel_size = 0
    html_size = 0
    initial_rows = 0

    for run in range(1, runs + 1):
        excel_path = output_dir / f"benchmark_{volume}_{run}.xlsx"
        html_path = output_dir / f"benchmark_{volume}_{run}.html"
        excel_times.append(
            measure_export(
                lambda excel_output=excel_path: export_excel(
                    excel_output,
                    incidents,
                    incidents,
                    [],
                    [],
                    summary,
                    "27/07/2026 08:00",
                    "benchmark fictício",
                    integrity,
                )
            )
        )
        html_times.append(
            measure_export(
                lambda html_output=html_path: render_html(
                    html_output,
                    "27/07/2026 08:00",
                    "benchmark fictício",
                    incidents,
                    summary,
                    [],
                    build_report_summary([]),
                    [],
                    build_report_summary([]),
                    "https://example.invalid",
                    integrity,
                )
            )
        )
        excel_size = excel_path.stat().st_size
        html_size = html_path.stat().st_size
        html_text = html_path.read_text(encoding="utf-8")
        static_rows = len(re.findall(r"<tr\s+data-equipment=", html_text))
        initial_rows = min(volume, 100) if 'id="incident-data"' in html_text else static_rows

    return {
        "records": volume,
        "runs": runs,
        "excel_seconds": [round(value, 6) for value in excel_times],
        "excel_median_seconds": round(statistics.median(excel_times), 6),
        "html_seconds": [round(value, 6) for value in html_times],
        "html_median_seconds": round(statistics.median(html_times), 6),
        "total_exports_median_seconds": round(
            statistics.median(excel_times) + statistics.median(html_times),
            6,
        ),
        "excel_size_bytes": excel_size,
        "html_size_bytes": html_size,
        "initial_incident_rows": initial_rows,
    }


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--volumes", nargs="+", type=int, default=DEFAULT_VOLUMES)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.runs < 1 or any(volume < 0 for volume in args.volumes):
        raise SystemExit("Use execuções e volumes positivos.")

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        scenarios = [run_scenario(volume, args.runs, output_dir) for volume in args.volumes]

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "runs_per_scenario": args.runs,
        "scenarios": scenarios,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
