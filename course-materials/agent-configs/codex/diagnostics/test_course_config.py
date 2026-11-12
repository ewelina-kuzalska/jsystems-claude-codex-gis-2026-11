"""Acceptance checks for the course configuration; no provider calls or secret reads."""
import json
import re
from pathlib import Path
import subprocess
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[4]
CONFIGS = [ROOT / "course-materials/agent-configs/codex/config.toml",
           ROOT / "course-materials/agent-configs/codex/permissions.toml"]


class CourseConfigTests(unittest.TestCase):
    def test_reusable_examples_default_to_workspace_with_opt_in_course_tools(self):
        for path in CONFIGS:
            with self.subTest(path=path):
                data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
                self.assertEqual(data["default_permissions"], ":workspace")
                self.assertNotIn("sandbox_mode", data)
                profile = data["permissions"]["course-tools"]
                self.assertEqual(profile["extends"], ":workspace")
                self.assertTrue(profile["network"]["enabled"])
                self.assertNotIn("filesystem", profile)

    def test_legacy_backend_is_explicit_without_mxc_preference(self):
        for path in CONFIGS:
            with self.subTest(path=path):
                data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
                self.assertEqual(data["windows"]["sandbox"], "elevated")
                self.assertIs(data["features"]["prefer_mxc"], False)
                self.assertIs(data["features"].get("network_proxy"), False)
                self.assertEqual(data["approval_policy"], "on-request")
                self.assertEqual(data["approvals_reviewer"], "auto_review")

    def test_user_merge_instructions_disable_an_existing_network_proxy(self):
        for name in ("README.md", "WINDOWS-QUICKSTART-PL.md"):
            with self.subTest(document=name):
                text = (ROOT / "course-materials/agent-configs/codex" / name).read_text(encoding="utf-8")
                snippet = re.search(r"```toml\n(.*?)```", text, re.DOTALL).group(1)
                settings = tomllib.loads(snippet)
                existing_features = {"network_proxy": True, "unrelated_feature": True}
                existing_features.update(settings["features"])
                self.assertIs(existing_features["network_proxy"], False)
                self.assertIs(existing_features["unrelated_feature"], True)

    def test_strict_profiles_still_have_their_denials(self):
        for path in CONFIGS:
            with self.subTest(path=path):
                data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
                strict = data["permissions"]["course-workspace"]["filesystem"][":workspace_roots"]
                for name in [".env", ".env.local", ".env.dev", ".env.prod", ".env.test",
                             "**/.env", "**/.env.local", "**/.env.dev", "**/.env.prod",
                             "**/.env.test", "secrets", "**/secrets/**"]:
                    self.assertEqual(strict[name], "deny")
                self.assertEqual(data["permissions"]["course-root"]["extends"], "course-workspace")

    def test_permission_tables_match(self):
        tables = [tomllib.loads(p.read_text(encoding="utf-8-sig"))["permissions"] for p in CONFIGS]
        self.assertEqual(tables[0], tables[1])

    def test_context7_is_enabled_without_requiring_a_key(self):
        for path in CONFIGS[:1]:
            server = tomllib.loads(path.read_text(encoding="utf-8-sig"))["mcp_servers"]["context7"]
            self.assertTrue(server["enabled"])
            self.assertEqual(server["url"], "https://mcp.context7.com/mcp")
            self.assertFalse(server.get("env_http_headers"))

    def test_curated_rules_preserve_command_boundaries(self):
        rule_files = [ROOT / "course-materials/agent-configs/codex/rules/course.rules"]
        semantic = [
            [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
            for path in rule_files
        ]
        self.assertTrue(semantic[0])
        cases = [
            (["gh", "repo", "view", "example/synthetic"], "allow"),
            (["gh", "pr", "view", "1"], "allow"),
            (["gh", "pr", "edit", "1"], None),
            (["playwright-cli.cmd", "snapshot", "-s=course-demo"], "allow"),
            (["playwright-cli", "open", "about:blank", "-s=course-demo"], "allow"),
            (["playwright-cli.cmd", "open", "about:blank", "-s=course-demo"], "allow"),
            (["playwright-cli", "close", "-s=course-demo"], "allow"),
            (["playwright-cli", "run-code", "arbitrary-code"], None),
            (["gh", "api", "arbitrary-endpoint"], None),
            (["gh", "repo", "delete", "example/synthetic"], "forbidden"),
            (["git", "push", "origin", "main"], "forbidden"),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                result = subprocess.run(["codex", "execpolicy", "check", "--rules", str(rule_files[0]), "--", *argv],
                                        text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout).get("decision"), expected)


if __name__ == "__main__":
    unittest.main()
