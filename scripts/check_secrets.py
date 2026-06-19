"""
Verifica se arquivos do projeto parecem conter tokens ou credenciais reais.

O objetivo é ser uma barreira simples antes de commits. O script não substitui
uma revisão humana, mas ajuda a evitar vazamentos comuns de .env, tokens do
Zabbix, tokens do GitHub e senhas escritas diretamente em arquivos versionados.
"""

from __future__ import annotations

import re
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

IGNORED_PARTS = {
    ".git",
    "venv",
    "venv-windows",
    "__pycache__",
    ".pytest_cache",
    ".cache",
    "reports",
    "entrega_supervisor",
}

TEXT_SUFFIXES = {
    ".bat",
    ".css",
    ".env",
    ".example",
    ".gitignore",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".txt",
    ".yml",
    ".yaml",
}

ALLOWED_ENV_FILES = {
    ROOT / "zabbix-report" / ".env.example",
}

PLACEHOLDER_WORDS = {
    "",
    "cole_o_token_real_apenas_no_env_local",
    "cole_seu_token_do_zabbix_aqui",
    "seu_token",
    "seu_token_da_api",
    "token",
}

PATTERNS = [
    (
        "token do GitHub",
        re.compile(r"\b(?:gho|ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "senha escrita diretamente",
        re.compile(r"(?i)\b(password|senha)\s*[:=]\s*['\"]?[^'\"\s]{6,}"),
    ),
]


def should_skip(path: Path) -> bool:
    relative_parts = set(path.relative_to(ROOT).parts)
    return bool(relative_parts & IGNORED_PARTS)


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {
        "README.md",
        "COMANDOS.md",
        "SEGURANCA.md",
    }


def normalize_env_value(value: str) -> str:
    return value.strip().strip("'\"").strip()


def check_env_assignment(path: Path, line_number: int, line: str) -> list[str]:
    findings: list[str] = []
    stripped = line.strip()

    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return findings

    if path.name not in {".env", ".env.example"} and not stripped.startswith(
        "ZABBIX_TOKEN="
    ):
        return findings

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = normalize_env_value(value)

    if key == "ZABBIX_TOKEN" and value.lower() not in PLACEHOLDER_WORDS:
        findings.append(
            f"{path}:{line_number}: ZABBIX_TOKEN parece conter valor real"
        )

    return findings


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")

    if path.name == ".env" and path.resolve() not in ALLOWED_ENV_FILES:
        findings.append(f"{path}: arquivo .env nao deve ser versionado")

    for line_number, line in enumerate(text.splitlines(), start=1):
        findings.extend(check_env_assignment(path, line_number, line))

        for label, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(f"{path}:{line_number}: possivel {label}")

    return findings


def main() -> int:
    findings: list[str] = []

    for current_root, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            dirname for dirname in dirnames if dirname not in IGNORED_PARTS
        ]

        for filename in filenames:
            path = Path(current_root) / filename

            if should_skip(path) or not is_text_file(path):
                continue

            findings.extend(scan_file(path))

    if findings:
        print("RISCOS ENCONTRADOS:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Nenhum segredo aparente encontrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
