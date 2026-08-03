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


if __name__ == "__main__":
    unittest.main()
