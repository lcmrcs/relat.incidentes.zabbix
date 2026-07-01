"""
Tela local para gerar relatórios do Zabbix pelo navegador.

Este arquivo usa apenas a biblioteca padrão do Python. A ideia é oferecer uma
entrada visual para o projeto sem transformar o relatório em uma aplicação web
complexa ou dependente de frameworks externos.
"""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import re
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
REPORT_SCRIPT = BASE_DIR / "zabbix_report.py"
REPORTS_DIR = BASE_DIR / "reports"
ENV_FILE = BASE_DIR / ".env"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
ALLOWED_PERIODS = {"24h", "2d", "5d", "7d", "15d", "30d", "historico"}
ALLOWED_STATUS = {"abertos", "resolvidos", "todos"}
KNOWN_EQUIPMENTS = [
    "Mikrotik",
    "Switch",
    "NVR",
    "Central de Alarme",
    "Terminal Facial",
    "Portal Detector de Metal",
    "Câmera",
    "Servidor",
]

UNIT_CODE_START = 1011
UNIT_CODE_END = 1169


HTML_PAGE = r"""<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Central de Relatórios Zabbix</title>
    <style>
        :root {
            color-scheme: light;
            --ink: #082933;
            --muted: #5e7880;
            --line: #c8e0e4;
            --accent: #087f8c;
            --accent-bright: #20c4cd;
            --danger: #c92a2a;
            --warning: #e67700;
            --surface: #ffffff;
            --wash: #eefafa;
            --shadow: 0 24px 64px rgb(8 36 43 / 0.14);
        }

        * {
            box-sizing: border-box;
        }

        body {
            min-height: 100vh;
            margin: 0;
            background:
                radial-gradient(circle at 14% 6%, rgb(32 196 205 / 0.30), transparent 24%),
                radial-gradient(circle at 86% 0%, rgb(8 127 140 / 0.22), transparent 30%),
                linear-gradient(135deg, #f7fbfb 0%, #e8f4f4 52%, #dff0f0 100%);
            color: var(--ink);
            font-family: Inter, "Segoe UI", Arial, sans-serif;
            padding: 28px;
        }

        .shell {
            width: min(1180px, 100%);
            margin: 0 auto;
        }

        .hero {
            position: relative;
            overflow: hidden;
            border: 1px solid rgb(32 196 205 / 0.28);
            border-radius: 32px;
            background:
                radial-gradient(circle at 82% 10%, rgb(32 196 205 / 0.34), transparent 28%),
                linear-gradient(135deg, #071f26 0%, #0b3d46 48%, #087f8c 100%);
            color: #ffffff;
            padding: 34px;
            box-shadow:
                var(--shadow),
                inset 0 1px 0 rgb(255 255 255 / 0.14);
        }

        .hero::before {
            position: absolute;
            inset: 0;
            background:
                linear-gradient(112deg, transparent 0 58%, rgb(255 255 255 / 0.08) 58% 68%, transparent 68%),
                radial-gradient(circle at 18% 84%, rgb(255 255 255 / 0.10), transparent 24%);
            content: "";
            pointer-events: none;
        }

        .hero::after {
            position: absolute;
            inset: -44% -10% auto auto;
            width: 360px;
            height: 360px;
            border: 1px solid rgb(255 255 255 / 0.14);
            border-radius: 999px;
            content: "";
        }

        .hero-content {
            position: relative;
            z-index: 1;
        }

        .eyebrow {
            display: inline-flex;
            gap: 8px;
            align-items: center;
            margin: 0 0 16px;
            border: 1px solid rgb(255 255 255 / 0.22);
            border-radius: 999px;
            background: rgb(255 255 255 / 0.10);
            color: #bdf8f8;
            font-size: 12px;
            font-weight: 900;
            padding: 7px 11px;
            text-transform: uppercase;
        }

        .eyebrow::before {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: var(--accent-bright);
            content: "";
        }

        h1 {
            max-width: 780px;
            margin: 0;
            font-size: clamp(34px, 5vw, 64px);
            line-height: 0.98;
            letter-spacing: 0;
        }

        .hero p {
            max-width: 760px;
            margin: 18px 0 0;
            color: #d7f2f3;
            font-size: 17px;
            line-height: 1.55;
        }

        .status-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 24px;
        }

        .status-card {
            border: 1px solid rgb(255 255 255 / 0.16);
            border-radius: 18px;
            background:
                linear-gradient(135deg, rgb(255 255 255 / 0.14), rgb(255 255 255 / 0.06));
            padding: 14px;
            box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.12);
        }

        .status-card span {
            display: block;
            color: #aeeff0;
            font-size: 11px;
            font-weight: 900;
            text-transform: uppercase;
        }

        .status-card strong {
            display: block;
            margin-top: 6px;
            color: #ffffff;
            font-size: 16px;
        }

        .layout {
            display: grid;
            grid-template-columns: minmax(0, 1.1fr) minmax(330px, 0.52fr);
            gap: 18px;
            margin-top: 18px;
            align-items: start;
        }

        .panel {
            position: relative;
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 28px;
            background:
                radial-gradient(circle at 100% 0%, rgb(32 196 205 / 0.10), transparent 32%),
                linear-gradient(145deg, rgb(255 255 255 / 0.96), rgb(245 253 253 / 0.90));
            box-shadow:
                0 18px 44px rgb(8 36 43 / 0.10),
                inset 0 1px 0 rgb(255 255 255 / 0.80);
            padding: 22px;
        }

        .panel::after {
            position: absolute;
            inset: -110px -80px auto auto;
            width: 260px;
            height: 260px;
            border: 1px solid rgb(8 127 140 / 0.12);
            border-radius: 999px;
            content: "";
            pointer-events: none;
        }

        .panel-header {
            position: relative;
            z-index: 1;
            display: flex;
            gap: 14px;
            justify-content: space-between;
            margin-bottom: 18px;
        }

        .panel-header h2 {
            margin: 0;
            font-size: 22px;
        }

        .panel-header p {
            margin: 5px 0 0;
            color: var(--muted);
            line-height: 1.45;
        }

        form {
            position: relative;
            z-index: 1;
            display: grid;
            gap: 16px;
        }

        .field-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
        }

        label {
            display: grid;
            gap: 7px;
            color: #244850;
            font-size: 12px;
            font-weight: 900;
            text-transform: uppercase;
        }

        select,
        input {
            width: 100%;
            min-height: 46px;
            border: 1px solid #c8dde1;
            border-radius: 14px;
            background: #ffffff;
            color: var(--ink);
            font: inherit;
            font-size: 15px;
            padding: 11px 13px;
            outline: none;
            transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }

        select:focus,
        input:focus {
            border-color: var(--accent-bright);
            box-shadow: 0 0 0 4px rgb(32 196 205 / 0.18);
            transform: translateY(-1px);
        }

        .unit-picker {
            position: relative;
        }

        .unit-picker input {
            padding-right: 92px;
        }

        .unit-picker::after {
            position: absolute;
            right: 12px;
            bottom: 11px;
            border: 1px solid rgb(8 127 140 / 0.16);
            border-radius: 999px;
            background: rgb(32 196 205 / 0.12);
            color: var(--accent);
            content: "buscar";
            font-size: 10px;
            font-weight: 950;
            padding: 5px 8px;
            text-transform: uppercase;
            pointer-events: none;
        }

        .unit-options {
            position: absolute;
            inset: calc(100% + 8px) 0 auto;
            z-index: 20;
            display: none;
            max-height: 260px;
            overflow: auto;
            border: 1px solid rgb(8 127 140 / 0.20);
            border-radius: 18px;
            background:
                linear-gradient(145deg, rgb(255 255 255 / 0.98), rgb(239 252 252 / 0.96));
            box-shadow:
                0 18px 40px rgb(8 36 43 / 0.16),
                inset 0 1px 0 rgb(255 255 255 / 0.90);
            padding: 8px;
        }

        .unit-options.visible {
            display: grid;
            gap: 7px;
        }

        .unit-option {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr);
            gap: 10px;
            align-items: center;
            min-height: 42px;
            border: 1px solid rgb(8 127 140 / 0.12);
            border-radius: 13px;
            background: rgb(255 255 255 / 0.84);
            color: var(--ink);
            cursor: pointer;
            padding: 9px 10px;
            text-align: left;
            transition: 160ms ease;
        }

        .unit-option:hover,
        .unit-option:focus {
            border-color: rgb(32 196 205 / 0.48);
            background: rgb(32 196 205 / 0.12);
            transform: translateY(-1px);
        }

        .unit-option-code {
            display: inline-grid;
            place-items: center;
            min-width: 44px;
            border-radius: 999px;
            background: linear-gradient(135deg, #20c4cd, #087f8c);
            color: #ffffff;
            font-size: 12px;
            font-weight: 950;
            padding: 5px 8px;
        }

        .unit-option-name {
            overflow: hidden;
            font-size: 13px;
            font-weight: 850;
            text-overflow: ellipsis;
            text-transform: none;
            white-space: nowrap;
        }

        .unit-empty {
            border: 1px dashed #b8d6dc;
            border-radius: 13px;
            color: var(--muted);
            font-size: 13px;
            padding: 12px;
            text-transform: none;
        }

        .segmented {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            border: 1px solid #cfe3e6;
            border-radius: 999px;
            background:
                linear-gradient(135deg, rgb(255 255 255 / 0.82), rgb(239 250 250 / 0.72));
            padding: 6px;
        }

        .segmented input {
            position: absolute;
            opacity: 0;
            pointer-events: none;
        }

        .segmented span {
            position: relative;
            overflow: hidden;
            display: grid;
            place-items: center;
            min-height: 42px;
            border: 1px solid transparent;
            border-radius: 999px;
            background: transparent;
            color: #244850;
            cursor: pointer;
            font-weight: 900;
            text-transform: none;
            transition:
                background 180ms ease,
                border-color 180ms ease,
                box-shadow 180ms ease,
                color 180ms ease,
                transform 180ms ease;
        }

        .segmented span:hover {
            background: rgb(255 255 255 / 0.82);
            color: var(--accent);
            transform: translateY(-1px);
        }

        .segmented input:checked + span {
            border-color: rgb(8 127 140 / 0.40);
            background:
                linear-gradient(135deg, rgb(32 196 205 / 0.28), rgb(8 127 140 / 0.16));
            color: var(--accent);
            box-shadow:
                inset 0 1px 0 rgb(255 255 255 / 0.78),
                0 10px 20px rgb(8 127 140 / 0.12);
        }

        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            justify-content: flex-end;
            border-top: 1px solid #dbeaec;
            padding-top: 16px;
        }

        button,
        .link-button {
            position: relative;
            isolation: isolate;
            overflow: hidden;
            min-height: 46px;
            border: 1px solid transparent;
            border-radius: 999px;
            cursor: pointer;
            font: inherit;
            font-weight: 950;
            padding: 11px 18px;
            text-decoration: none;
            transition: 180ms ease;
        }

        button::before,
        .link-button::before {
            position: absolute;
            inset: 0;
            border-radius: inherit;
            background: linear-gradient(110deg, transparent, rgb(255 255 255 / 0.34), transparent);
            content: "";
            opacity: 0.55;
            transform: translateX(-55%);
            transition: transform 420ms ease;
            z-index: -1;
        }

        button:hover::before,
        .link-button:hover::before {
            transform: translateX(45%);
        }

        .primary {
            border-color: rgb(255 255 255 / 0.30);
            background:
                radial-gradient(circle at 18% 18%, rgb(255 255 255 / 0.30), transparent 30%),
                linear-gradient(135deg, #20c4cd, #087f8c);
            color: #ffffff;
            box-shadow:
                0 16px 30px rgb(8 127 140 / 0.22),
                inset 0 1px 0 rgb(255 255 255 / 0.22);
        }

        .secondary,
        .link-button {
            border-color: #c8dde1;
            background: #ffffff;
            color: var(--accent);
        }

        button:hover,
        .link-button:hover {
            transform: translateY(-1px);
        }

        button:disabled {
            cursor: progress;
            opacity: 0.72;
            transform: none;
        }

        .selection-summary {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
        }

        .selection-card {
            position: relative;
            overflow: hidden;
            min-height: 86px;
            border: 1px solid #c8dde1;
            border-radius: 20px;
            background:
                linear-gradient(145deg, #ffffff 0%, #f1fbfb 100%);
            padding: 15px;
        }

        .selection-card::after {
            position: absolute;
            right: -24px;
            bottom: -38px;
            width: 94px;
            height: 94px;
            border: 1px solid rgb(8 127 140 / 0.12);
            border-radius: 999px;
            content: "";
        }

        .selection-card span {
            display: block;
            color: var(--muted);
            font-size: 10px;
            font-weight: 950;
            text-transform: uppercase;
        }

        .selection-card strong {
            display: block;
            margin-top: 8px;
            color: var(--accent);
            font-size: 17px;
            line-height: 1.2;
        }

        .side-stack {
            display: grid;
            gap: 18px;
        }

        .health-list,
        .result-list {
            position: relative;
            z-index: 1;
            display: grid;
            gap: 10px;
            margin: 0;
            padding: 0;
            list-style: none;
        }

        .health-item,
        .result-item {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr);
            gap: 10px;
            align-items: center;
            border: 1px solid #d6e7ea;
            border-radius: 16px;
            background: #ffffff;
            padding: 12px;
        }

        .dot {
            width: 11px;
            height: 11px;
            border-radius: 999px;
            background: var(--accent-bright);
            box-shadow: 0 0 0 5px rgb(32 196 205 / 0.12);
        }

        .dot.warn {
            background: var(--warning);
            box-shadow: 0 0 0 5px rgb(230 119 0 / 0.12);
        }

        .dot.error {
            background: var(--danger);
            box-shadow: 0 0 0 5px rgb(201 42 42 / 0.12);
        }

        .health-item strong,
        .result-item strong {
            display: block;
            font-size: 14px;
        }

        .health-item span,
        .result-item span {
            display: block;
            margin-top: 2px;
            color: var(--muted);
            font-size: 13px;
            overflow-wrap: anywhere;
        }

        .output {
            display: none;
            position: relative;
            z-index: 1;
            max-height: 320px;
            overflow: auto;
            border: 1px solid #143b43;
            border-radius: 18px;
            background: #08242b;
            color: #dffbfb;
            font-family: "Cascadia Code", Consolas, monospace;
            font-size: 12px;
            line-height: 1.55;
            padding: 14px;
            white-space: pre-wrap;
        }

        .output.visible {
            display: block;
        }

        .result-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 12px;
        }

        .hidden {
            display: none !important;
        }

        @media (max-width: 920px) {
            body {
                padding: 14px;
            }

            .layout,
            .field-grid,
            .status-strip,
            .selection-summary {
                grid-template-columns: 1fr;
            }

            .hero {
                padding: 24px;
            }

            .actions {
                justify-content: stretch;
            }

            button,
            .link-button {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="shell">
        <section class="hero">
            <div class="hero-content">
                <span class="eyebrow">Central operacional</span>
                <h1>Gerador de Relatórios Zabbix</h1>
                <p>Escolha o recorte, gere os arquivos oficiais e abra o HTML executivo sem precisar memorizar comandos de terminal.</p>
                <div class="status-strip" id="status-strip"></div>
            </div>
        </section>

        <div class="layout">
            <section class="panel">
                <div class="panel-header">
                    <div>
                        <h2>Novo relatório</h2>
                        <p>Defina o período, a situação, a unidade escolar e o equipamento que deseja analisar.</p>
                    </div>
                </div>

                <form id="report-form">
                    <div class="field-grid">
                        <label>
                            Período
                            <select id="period" name="period">
                                <option value="historico">Histórico completo</option>
                                <option value="24h">Últimas 24h</option>
                                <option value="2d">Últimos 2 dias</option>
                                <option value="5d">Últimos 5 dias</option>
                                <option value="7d">Últimos 7 dias</option>
                                <option value="15d">Últimos 15 dias</option>
                                <option value="30d">Últimos 30 dias</option>
                                <option value="custom">A partir de uma data</option>
                            </select>
                        </label>

                        <label id="custom-date-wrap" class="hidden">
                            Data inicial
                            <input id="since" name="since" type="date">
                        </label>

                        <label>
                            Equipamento
                            <select id="equipment" name="equipment">
                                <option value="">Todos os equipamentos</option>
                            </select>
                        </label>

                        <label class="unit-picker">
                            Unidade escolar
                            <input id="unit-filter" name="unitFilter" type="search" placeholder="Código ou nome da unidade">
                            <div class="unit-options" id="unit-options" role="listbox" aria-label="Unidades escolares"></div>
                        </label>

                        <label>
                            Manter relatórios
                            <input id="keep" name="keep" type="number" min="1" max="20" value="1">
                        </label>
                    </div>

                    <label>
                        Situação
                        <div class="segmented" role="radiogroup" aria-label="Situação dos incidentes">
                            <label><input type="radio" name="status" value="abertos" checked><span>Abertos</span></label>
                            <label><input type="radio" name="status" value="todos"><span>Todos</span></label>
                            <label><input type="radio" name="status" value="resolvidos"><span>Resolvidos</span></label>
                        </div>
                    </label>

                    <div class="selection-summary" aria-label="Resumo da geração selecionada">
                        <div class="selection-card">
                            <span>Recorte</span>
                            <strong id="selection-period">Histórico completo</strong>
                        </div>
                        <div class="selection-card">
                            <span>Escopo</span>
                            <strong id="selection-scope">Todos os equipamentos</strong>
                        </div>
                        <div class="selection-card">
                            <span>Entrega</span>
                            <strong id="selection-delivery">HTML, Excel e PDF</strong>
                        </div>
                    </div>

                    <div class="actions">
                        <button class="primary" id="generate-button" type="submit">Gerar relatório</button>
                    </div>
                </form>
            </section>

            <aside class="side-stack">
                <section class="panel">
                    <div class="panel-header">
                        <div>
                            <h2>Ambiente</h2>
                            <p>Checagens rápidas antes da geração.</p>
                        </div>
                    </div>
                    <ul class="health-list" id="health-list"></ul>
                </section>

                <section class="panel">
                    <div class="panel-header">
                        <div>
                            <h2>Resultado</h2>
                            <p>Os links aparecem aqui ao finalizar.</p>
                        </div>
                    </div>
                    <ul class="result-list" id="result-list"></ul>
                    <div class="result-actions" id="result-actions"></div>
                    <pre class="output" id="output"></pre>
                </section>
            </aside>
        </div>
    </div>

    <script>
        const equipments = __EQUIPMENTS__;
        const units = __UNITS__;
        const health = __HEALTH__;
        const form = document.getElementById("report-form");
        const period = document.getElementById("period");
        const since = document.getElementById("since");
        const customDateWrap = document.getElementById("custom-date-wrap");
        const equipment = document.getElementById("equipment");
        const unitFilter = document.getElementById("unit-filter");
        const unitOptions = document.getElementById("unit-options");
        const keep = document.getElementById("keep");
        const generateButton = document.getElementById("generate-button");
        const healthList = document.getElementById("health-list");
        const resultList = document.getElementById("result-list");
        const resultActions = document.getElementById("result-actions");
        const output = document.getElementById("output");
        const statusStrip = document.getElementById("status-strip");
        const selectionPeriod = document.getElementById("selection-period");
        const selectionScope = document.getElementById("selection-scope");
        const selectionDelivery = document.getElementById("selection-delivery");

        function fillEquipmentOptions() {
            for (const name of equipments) {
                const option = document.createElement("option");
                option.value = name;
                option.textContent = name;
                equipment.appendChild(option);
            }
        }

        function normalizeText(value) {
            return String(value || "")
                .normalize("NFD")
                .replace(/[\u0300-\u036f]/g, "")
                .toLowerCase();
        }

        function renderUnitOptions() {
            const query = normalizeText(unitFilter.value);
            const filtered = units
                .filter((item) => {
                    if (!query) {
                        return true;
                    }

                    return normalizeText(`${item.code} ${item.name}`).includes(query);
                })
                .slice(0, 18);

            unitOptions.innerHTML = "";

            if (!filtered.length) {
                unitOptions.innerHTML = `<div class="unit-empty">Nenhuma unidade encontrada para esse termo.</div>`;
                unitOptions.classList.add("visible");
                return;
            }

            for (const item of filtered) {
                const button = document.createElement("button");
                button.className = "unit-option";
                button.type = "button";
                button.setAttribute("role", "option");
                button.dataset.value = item.name || item.code;

                const code = document.createElement("span");
                code.className = "unit-option-code";
                code.textContent = item.code || "----";

                const name = document.createElement("span");
                name.className = "unit-option-name";
                name.textContent = item.name || item.code;

                button.append(code, name);
                unitOptions.appendChild(button);
            }

            unitOptions.classList.add("visible");
        }

        function closeUnitOptions() {
            unitOptions.classList.remove("visible");
        }

        function getStatus() {
            return form.querySelector("input[name='status']:checked")?.value || "abertos";
        }

        function getPayload() {
            return {
                period: period.value,
                since: since.value,
                status: getStatus(),
                equipment: equipment.value,
                unit: unitFilter.value.trim(),
                keep: keep.value,
            };
        }

        function getPeriodLabel(payload) {
            const labels = {
                historico: "Histórico completo",
                "24h": "Últimas 24h",
                "2d": "Últimos 2 dias",
                "5d": "Últimos 5 dias",
                "7d": "Últimos 7 dias",
                "15d": "Últimos 15 dias",
                "30d": "Últimos 30 dias",
            };

            if (payload.period === "custom") {
                return payload.since ? `Desde ${payload.since}` : "Data inicial";
            }

            return labels[payload.period] || "Recorte selecionado";
        }

        function refreshSelection() {
            const payload = getPayload();
            customDateWrap.classList.toggle("hidden", period.value !== "custom");
            selectionPeriod.textContent = getPeriodLabel(payload);
            selectionScope.textContent = [
                payload.equipment || "Todos os equipamentos",
                payload.unit ? `Unidade ${payload.unit}` : "",
            ].filter(Boolean).join(" · ");
            selectionDelivery.textContent = "HTML, Excel e PDF";
        }

        function renderHealth() {
            healthList.innerHTML = "";
            statusStrip.innerHTML = "";

            for (const item of health) {
                const li = document.createElement("li");
                li.className = "health-item";
                li.innerHTML = `<i class="dot ${item.level}"></i><div><strong>${item.title}</strong><span>${item.detail}</span></div>`;
                healthList.appendChild(li);

                const card = document.createElement("div");
                card.className = "status-card";
                card.innerHTML = `<span>${item.title}</span><strong>${item.short}</strong>`;
                statusStrip.appendChild(card);
            }
        }

        function renderResults(data) {
            resultList.innerHTML = "";
            resultActions.innerHTML = "";
            const files = data.files || {};
            const entries = [
                ["HTML", files.html],
                ["Excel", files.excel],
                ["PDF", files.pdf],
            ].filter(([, file]) => file);

            if (!entries.length) {
                resultList.innerHTML = `<li class="result-item"><i class="dot warn"></i><div><strong>Nenhum arquivo localizado</strong><span>A geração terminou, mas nenhum arquivo final foi localizado.</span></div></li>`;
                return;
            }

            for (const [label, file] of entries) {
                const descriptions = {
                    HTML: "Relatório interativo pronto para análise.",
                    Excel: "Planilha executiva pronta para conferência.",
                    PDF: "Documento pronto para apresentação ou envio.",
                };
                const li = document.createElement("li");
                li.className = "result-item";
                li.innerHTML = `<i class="dot"></i><div><strong>${label}</strong><span>${descriptions[label] || "Arquivo gerado com sucesso."}</span></div>`;
                resultList.appendChild(li);

                const link = document.createElement("a");
                link.className = "link-button";
                link.href = file.url;
                link.target = "_blank";
                link.rel = "noreferrer";
                link.textContent = `Abrir ${label}`;
                resultActions.appendChild(link);
            }
        }

        async function generateReport(event) {
            event.preventDefault();
            const payload = getPayload();

            if (payload.period === "custom" && !payload.since) {
                alert("Escolha a data inicial para usar período personalizado.");
                since.focus();
                return;
            }

            output.classList.remove("visible");
            output.textContent = "";
            resultList.innerHTML = "";
            resultActions.innerHTML = "";
            resultList.innerHTML = `<li class="result-item"><i class="dot"></i><div><strong>Geração em andamento</strong><span>Consultando o Zabbix e preparando os arquivos finais.</span></div></li>`;
            generateButton.disabled = true;
            generateButton.textContent = "Gerando...";

            try {
                const response = await fetch("/api/generate", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(payload),
                });
                const data = await response.json();

                if (!response.ok || !data.ok) {
                    throw new Error(data.error || "Falha ao gerar relatório.");
                }

                renderResults(data);
            } catch (error) {
                resultList.innerHTML = `<li class="result-item"><i class="dot error"></i><div><strong>Falha na geração</strong><span>${error.message}</span></div></li>`;
                output.classList.remove("visible");
                output.textContent = "";
            } finally {
                generateButton.disabled = false;
                generateButton.textContent = "Gerar relatório";
            }
        }

        fillEquipmentOptions();
        renderHealth();
        refreshSelection();
        form.addEventListener("input", refreshSelection);
        form.addEventListener("change", refreshSelection);
        unitFilter.addEventListener("focus", renderUnitOptions);
        unitFilter.addEventListener("input", renderUnitOptions);
        unitOptions.addEventListener("click", (event) => {
            const option = event.target.closest(".unit-option");

            if (!option) {
                return;
            }

            unitFilter.value = option.dataset.value;
            closeUnitOptions();
            refreshSelection();
        });
        document.addEventListener("click", (event) => {
            if (!event.target.closest(".unit-picker")) {
                closeUnitOptions();
            }
        });
        form.addEventListener("submit", generateReport);
    </script>
</body>
</html>
"""


def build_health_items() -> list[dict[str, str]]:
    """Resume o estado local para exibir na tela inicial."""

    return [
        {
            "title": "Credenciais",
            "short": "OK" if ENV_FILE.exists() else "Pendente",
            "detail": (
                "Credenciais locais configuradas neste computador."
                if ENV_FILE.exists()
                else "Configure as credenciais locais antes de gerar."
            ),
            "level": "" if ENV_FILE.exists() else "warn",
        },
        {
            "title": "Gerador",
            "short": "Disponível" if REPORT_SCRIPT.exists() else "Erro",
            "detail": (
                "Motor de geração pronto para uso."
                if REPORT_SCRIPT.exists()
                else "Motor de geração não localizado."
            ),
            "level": "" if REPORT_SCRIPT.exists() else "error",
        },
        {
            "title": "Saída",
            "short": "Arquivos",
            "detail": "HTML, Excel e PDF serão entregues ao finalizar.",
            "level": "",
        },
    ]


def collect_known_units() -> list[dict[str, str]]:
    """Monta sugestões de unidades a partir dos relatórios locais já gerados."""

    units_by_code = {
        str(code): {"code": str(code), "name": str(code)}
        for code in range(UNIT_CODE_START, UNIT_CODE_END + 1)
    }

    for report_path in sorted(
        REPORTS_DIR.glob("*.html"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        try:
            content = report_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        rows = re.findall(r"<tr\b[^>]*>", content, flags=re.DOTALL)

        for row in rows:
            code_match = re.search(r'data-unit-code="([^"]*)"', row)
            name_match = re.search(r'data-unit="([^"]*)"', row)

            if not code_match or not name_match:
                continue

            raw_code = code_match.group(1)
            raw_name = name_match.group(1)
            code = html.unescape(raw_code).strip()
            name = html.unescape(raw_name).strip()

            if not code.isdigit() or not UNIT_CODE_START <= int(code) <= UNIT_CODE_END:
                continue

            if name and name != "-":
                units_by_code[code] = {"code": code, "name": name}

    return sorted(units_by_code.values(), key=lambda item: int(item["code"]))


def render_page() -> bytes:
    """Renderiza a tela inicial com dados locais simples."""

    page = HTML_PAGE.replace(
        "__EQUIPMENTS__",
        json.dumps(KNOWN_EQUIPMENTS, ensure_ascii=False),
    ).replace(
        "__UNITS__",
        json.dumps(collect_known_units(), ensure_ascii=False),
    ).replace(
        "__HEALTH__",
        json.dumps(build_health_items(), ensure_ascii=False),
    )
    return page.encode("utf-8")


def latest_report_files() -> dict[str, dict[str, str]]:
    """Localiza os arquivos mais recentes por extensão dentro de reports."""

    files: dict[str, dict[str, str]] = {}
    extension_map = {
        ".html": "html",
        ".xlsx": "excel",
        ".pdf": "pdf",
    }

    for suffix, key in extension_map.items():
        candidates = sorted(
            REPORTS_DIR.glob(f"*{suffix}"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        if candidates:
            path = candidates[0]
            files[key] = {
                "name": path.name,
                "url": f"/reports/{path.name}",
            }

    return files


def normalize_payload(payload: dict) -> list[str]:
    """Valida a entrada da tela e monta os argumentos do zabbix_report.py."""

    period = str(payload.get("period", "historico")).strip()
    since = str(payload.get("since", "")).strip()
    status = str(payload.get("status", "abertos")).strip()
    equipment = str(payload.get("equipment", "")).strip()
    unit = str(payload.get("unit", "")).strip()

    try:
        keep = int(payload.get("keep", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError("Quantidade de relatórios mantidos inválida.") from exc

    if keep < 1 or keep > 20:
        raise ValueError("Use manter relatórios entre 1 e 20.")

    if status not in ALLOWED_STATUS:
        raise ValueError("Situação inválida.")

    args = [sys.executable, str(REPORT_SCRIPT)]

    if period == "custom":
        if not since:
            raise ValueError("Informe a data inicial.")
        args.extend(["--desde", since])
    else:
        if period not in ALLOWED_PERIODS:
            raise ValueError("Período inválido.")
        args.extend(["--periodo", period])

    args.extend(["--status", status])

    if equipment:
        args.extend(["--equipamento", equipment])

    if unit:
        args.extend(["--unidade", unit])

    args.extend(["--manter-relatorios", str(keep)])
    return args


class LauncherHandler(BaseHTTPRequestHandler):
    """Atende a tela local, a geração e os relatórios finais."""

    server_version = "ZabbixReportLauncher/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            body = render_page()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.startswith("/reports/"):
            name = Path(unquote(self.path.removeprefix("/reports/"))).name
            path = REPORTS_DIR / name

            if not path.exists() or not path.is_file():
                self.send_error(404, "Relatório não encontrado.")
                return

            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404, "Página não encontrada.")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/generate":
            self.send_error(404, "Rota não encontrada.")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            args = normalize_payload(payload)
            completed = subprocess.run(
                args,
                cwd=PROJECT_DIR,
                check=False,
                capture_output=True,
                text=True,
                timeout=1800,
            )
            output = "\n".join(
                part
                for part in [completed.stdout.strip(), completed.stderr.strip()]
                if part
            )

            if completed.returncode != 0:
                self.send_json(
                    500,
                    {
                        "ok": False,
                        "error": "O gerador retornou erro.",
                        "output": output,
                    },
                )
                return

            self.send_json(
                200,
                {
                    "ok": True,
                    "output": output,
                    "files": latest_report_files(),
                },
            )
        except Exception as exc:  # noqa: BLE001
            self.send_json(
                400,
                {
                    "ok": False,
                    "error": str(exc),
                    "output": "",
                },
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Abre a tela local para geração de relatórios Zabbix."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), LauncherHandler)
    url = f"http://{args.host}:{args.port}/"

    print("Central de Relatórios Zabbix")
    print("--------------------------------")
    print(f"Acesse: {url}")
    print("Pressione Ctrl+C para encerrar.")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando tela local.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
