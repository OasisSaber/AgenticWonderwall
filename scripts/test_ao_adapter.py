"""Contract tests for the Agent Orchestrator + OpenCode adaptation (v3.1.0).

Covers:
- OpenCode Skill entry (.opencode/skills/themasterplan/SKILL.md)
- OpenCode slash command (.opencode/commands/themasterplan.md)
- legacy entry and misspelled-command guards

Adapter and example-configuration contracts (tests 5-13 of the v3.1.0
adaptation plan) live in the same file, added by the adapter PR.
"""

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OPENCODE_SKILL = ROOT / ".opencode/skills/themasterplan/SKILL.md"
OPENCODE_COMMAND = ROOT / ".opencode/commands/themasterplan.md"
AO_ADAPTER = ROOT / "adapters/agent-orchestrator.md"
AO_EXAMPLE = ROOT / "examples/agent-orchestrator.yaml"
LOAD_ORDER_FILES = (
    "AGENTS.md",
    "core/workflow.md",
    "core/policy.md",
    "profiles/git.md",
    "adapters/agent-orchestrator.md",
)


def read_frontmatter(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError(f"{path}: frontmatter must start with '---'")
    end = next((i for i, line in enumerate(lines[1:], 1) if line == "---"), None)
    if end is None:
        raise AssertionError(f"{path}: frontmatter has no closing '---'")
    data = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(data, dict):
        raise AssertionError(f"{path}: frontmatter must be a mapping")
    return data


class OpenCodeSkillTests(unittest.TestCase):
    """Plan test 1-4: OpenCode Skill and command entry exist and load."""

    def test_opencode_skill_exists(self):
        self.assertTrue(OPENCODE_SKILL.is_file(), "OpenCode skill is missing")

    def test_opencode_skill_frontmatter_name(self):
        self.assertEqual(
            read_frontmatter(OPENCODE_SKILL).get("name"),
            "themasterplan",
        )

    def test_opencode_command_exists(self):
        self.assertTrue(
            OPENCODE_COMMAND.is_file(), "OpenCode command is missing"
        )
        self.assertIn(
            "description",
            read_frontmatter(OPENCODE_COMMAND),
            "OpenCode command frontmatter must be valid",
        )

    def test_opencode_command_loads_skill(self):
        body = OPENCODE_COMMAND.read_text(encoding="utf-8").lower()
        self.assertIn("themasterplan", body)
        self.assertIn("skill", body)


class LegacyEntryTests(unittest.TestCase):
    """Plan test 14-15: no legacy /aw entry, no misspelled command."""

    def test_no_legacy_skill_entry(self):
        self.assertFalse(
            (ROOT / ".opencode/skills/aw").exists(),
            "legacy 'aw' skill entry must not exist under .opencode/",
        )
        self.assertFalse(
            (ROOT / ".opencode/commands/aw.md").exists(),
            "legacy 'aw' command must not exist under .opencode/",
        )
        self.assertNotEqual(
            read_frontmatter(OPENCODE_SKILL).get("name"),
            "aw",
        )

    def test_no_misspelled_command(self):
        pattern = re.compile(r"themasterplane", re.IGNORECASE)
        for markdown in ROOT.glob(".opencode/**/*.md"):
            self.assertNotRegex(
                markdown.read_text(encoding="utf-8"),
                pattern,
                f"{markdown} contains the unsupported misspelled command",
            )


class AoAdapterTests(unittest.TestCase):
    """Plan test 5-12: AO adapter and example configuration contracts."""

    @classmethod
    def setUpClass(cls):
        cls.adapter = AO_ADAPTER.read_text(encoding="utf-8")
        cls.example = yaml.safe_load(AO_EXAMPLE.read_text(encoding="utf-8"))

    def test_ao_adapter_exists(self):
        self.assertTrue(AO_ADAPTER.is_file(), "AO adapter is missing")

    def test_adapter_single_delivery_owner(self):
        self.assertIn("单一交付责任人", self.adapter)

    def test_adapter_forbids_merge_release_deploy(self):
        for term in ("merge", "release", "deploy"):
            self.assertIn(term, self.adapter)
        self.assertIn("不得自动", self.adapter)

    def test_example_approved_and_green_not_auto(self):
        reaction = self.example["projects"]["my-project"]["reactions"][
            "approved-and-green"
        ]
        self.assertFalse(reaction["auto"])
        self.assertEqual(reaction["action"], "notify")

    def test_example_uses_git_worktree(self):
        self.assertEqual(self.example["defaults"]["workspace"], "worktree")

    def test_example_uses_opencode(self):
        self.assertEqual(self.example["defaults"]["agent"], "opencode")

    def test_example_ci_failed_sends_to_agent(self):
        reaction = self.example["projects"]["my-project"]["reactions"][
            "ci-failed"
        ]
        self.assertTrue(reaction["auto"])
        self.assertEqual(reaction["action"], "send-to-agent")

    def test_example_changes_requested_sends_to_agent(self):
        reaction = self.example["projects"]["my-project"]["reactions"][
            "changes-requested"
        ]
        self.assertTrue(reaction["auto"])
        self.assertEqual(reaction["action"], "send-to-agent")


class LoadOrderTests(unittest.TestCase):
    """Plan test 13: authoritative load order files are complete."""

    def test_authoritative_load_order_complete(self):
        missing = [
            name for name in LOAD_ORDER_FILES if not (ROOT / name).is_file()
        ]
        self.assertEqual(
            missing, [], f"load order files missing: {missing}"
        )


if __name__ == "__main__":
    unittest.main()
