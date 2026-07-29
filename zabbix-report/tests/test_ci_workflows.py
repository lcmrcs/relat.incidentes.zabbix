import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_html_browser  # noqa: E402

WORKFLOW_DIR = ROOT / ".github" / "workflows"
ACTION_PATTERN = re.compile(r"uses:\s*[^@\s]+@([0-9a-f]{40})\s*$", re.MULTILINE)


class CiWorkflowTests(unittest.TestCase):
    def workflow(self, name):
        path = WORKFLOW_DIR / name
        text = path.read_text(encoding="utf-8")
        parsed = yaml.load(text, Loader=yaml.BaseLoader)
        return text, parsed

    def test_workflows_have_valid_yaml_events_permissions_and_concurrency(self):
        for name in ("qualidade-continua.yml", "validacao-navegador.yml"):
            text, workflow = self.workflow(name)

            self.assertIsInstance(workflow, dict)
            self.assertIn("push", workflow["on"])
            self.assertIn("pull_request", workflow["on"])
            self.assertIn("workflow_dispatch", workflow["on"])
            self.assertEqual(workflow["permissions"], {"contents": "read"})
            self.assertEqual(workflow["concurrency"]["cancel-in-progress"], "true")
            self.assertNotIn("ZABBIX_TOKEN", text)
            self.assertNotRegex(text, r"\$\{\{\s*secrets\.")

            used_actions = re.findall(r"^\s*uses:\s*(.+)$", text, re.MULTILINE)
            pinned_actions = ACTION_PATTERN.findall(text)
            self.assertEqual(len(used_actions), len(pinned_actions))

            for job in workflow["jobs"].values():
                self.assertIn("timeout-minutes", job)

    def test_quality_checks_have_stable_names_and_safe_commands(self):
        text, workflow = self.workflow("qualidade-continua.yml")
        names = {job["name"] for job in workflow["jobs"].values()}

        self.assertTrue({"Qualidade Python", "Testes", "Segurança"} <= names)
        self.assertIn("ruff check .", text)
        self.assertIn("xargs -0 -n 1 black --check", text)
        self.assertIn("python scripts/check_secrets.py", text)
        self.assertIn("pytest", text)
        self.assertIn("fetch-depth: 2", text)
        self.assertNotIn("test_zabbix_api.py", text)

    def test_browser_workflow_never_updates_baselines_and_limits_artifacts(self):
        text, workflow = self.workflow("validacao-navegador.yml")
        names = {job["name"] for job in workflow["jobs"].values()}

        self.assertTrue({"HTML no Navegador", "Regressão Visual", "Acessibilidade"} <= names)
        self.assertNotIn("--update-baselines", text)
        self.assertIn("--visual-only", text)
        self.assertIn("--accessibility-only", text)
        self.assertIn("if: failure()", text)
        self.assertIn("retention-days: 5", text)
        self.assertIn("zabbix-report/tests/visual_baselines/", text)
        self.assertIn("Remover evidência anterior", text)
        self.assertIn("artifacts/html-browser/", text)

    def test_windows_browser_candidates_use_native_environment(self):
        environment = {
            "PROGRAMFILES(X86)": r"C:\Program Files (x86)",
            "PROGRAMFILES": r"C:\Program Files",
            "LOCALAPPDATA": r"C:\Users\runner\AppData\Local",
        }
        candidates = validate_html_browser.browser_candidates(
            system_name="nt",
            environment=environment,
        )

        paths = {str(path) for path in candidates}
        self.assertIn(
            str(
                Path(environment["PROGRAMFILES(X86)"])
                / "Microsoft"
                / "Edge"
                / "Application"
                / "msedge.exe"
            ),
            paths,
        )


if __name__ == "__main__":
    unittest.main()
