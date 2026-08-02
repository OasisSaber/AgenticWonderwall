"""Unit tests for scripts/validate_skill_sync.py.

Tests the validate() function with real repository files plus synthetic
mutation cases, and main() exit codes against a temporary repository copy.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "validate_skill_sync.py"

# 强制子进程以 UTF-8 输出，避免 Windows 管道下 Python 使用 locale 编码（GBK）
UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

AGENTS = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
SKILL = (REPO_ROOT / "skills" / "agentic-wonderwall" / "SKILL.md").read_text(encoding="utf-8")


def validate(agents: str, skill: str) -> list[str]:
    import importlib.util

    spec = importlib.util.spec_from_file_location("validate_skill_sync", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate(agents, skill)


class SkillSyncTest(unittest.TestCase):
    def test_real_files_are_synced(self):
        self.assertEqual(validate(AGENTS, SKILL), [])

    def test_agents_missing_point(self):
        # 删除 AGENTS.md 中"审查意见三类用语"的全部关键词
        broken = AGENTS.replace("合并前必须修复", "X").replace("建议本次修复", "X").replace("可以后续处理", "X")
        errors = validate(broken, SKILL)
        self.assertTrue(any("AGENTS.md 缺失规则要点: 审查意见三类用语" in e for e in errors))

    def test_skill_missing_point(self):
        broken = SKILL.replace("Squash Merge", "X")
        errors = validate(AGENTS, broken)
        self.assertTrue(any("SKILL.md 缺失规则要点: Squash Merge 由人类决定" in e for e in errors))

    def test_both_missing_point(self):
        broken_agents = AGENTS.replace("权威顺序", "X")
        broken_skill = SKILL.replace("权威顺序", "X")
        errors = validate(broken_agents, broken_skill)
        self.assertTrue(any("规则要点在两侧均缺失: 权威顺序" in e for e in errors))

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "skills" / "agentic-wonderwall").mkdir(parents=True)
            shutil.copy(REPO_ROOT / "AGENTS.md", root / "AGENTS.md")
            shutil.copy(
                REPO_ROOT / "skills" / "agentic-wonderwall" / "SKILL.md",
                root / "skills" / "agentic-wonderwall" / "SKILL.md",
            )
            synced = subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=UTF8_ENV,
                check=False,
            )
            self.assertEqual(synced.returncode, 0)
            (root / "skills" / "agentic-wonderwall" / "SKILL.md").write_text(
                "no rules\n", encoding="utf-8"
            )
            desynced = subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=UTF8_ENV,
                check=False,
            )
            self.assertEqual(desynced.returncode, 1)
            self.assertIn("SKILL.md 缺失规则要点", desynced.stderr)

    def test_main_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "skills" / "agentic-wonderwall").mkdir(parents=True)
            shutil.copy(REPO_ROOT / "AGENTS.md", root / "AGENTS.md")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=UTF8_ENV,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("missing file", result.stderr)


if __name__ == "__main__":
    unittest.main()
