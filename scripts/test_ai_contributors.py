import tempfile
import unittest
from pathlib import Path

from ai_contributors import (
    ContributorError,
    generate_trailers,
    load_config,
    resolve_model,
    trailer_errors,
)

SAMPLE = """\
ai_contributors:
  codex:
    display_name: Codex
    email: codex@users.noreply.github.com
    aliases: [gpt, openai, gpt-5.6]
  claude:
    display_name: Claude
    email: noreply@anthropic.com
    aliases: [anthropic, claude-code]
  deepseek:
    display_name: DeepSeek
    email: ""
    aliases: [ds, deepseek-v4]
  custom:
    display_name: MyAgent
    email: my-agent@users.noreply.github.com
"""


class AiContributorConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = Path(self.directory.name) / ".ai-contributors.yaml"
        self.config.write_text(SAMPLE, encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def load(self):
        return load_config(self.config)

    def test_missing_file(self):
        with self.assertRaises(ContributorError):
            load_config(self.directory.name + "/missing.yaml")

    def test_missing_ai_contributors_key(self):
        self.config.write_text("other: true\n", encoding="utf-8")
        with self.assertRaises(ContributorError):
            self.load()

    def test_invalid_yaml(self):
        self.config.write_text("ai_contributors: [unclosed\n", encoding="utf-8")
        with self.assertRaises(ContributorError):
            self.load()

    def test_missing_display_name(self):
        self.config.write_text(
            "ai_contributors:\n  codex:\n    email: a@b.com\n", encoding="utf-8"
        )
        with self.assertRaises(ContributorError):
            self.load()

    def test_invalid_email_format(self):
        self.config.write_text(
            "ai_contributors:\n  codex:\n    display_name: Codex\n    email: not-an-email\n",
            encoding="utf-8",
        )
        with self.assertRaises(ContributorError):
            self.load()

    def test_aliases_must_be_list_of_strings(self):
        self.config.write_text(
            "ai_contributors:\n  codex:\n    display_name: Codex\n    email: a@b.com\n    aliases: [1, 2]\n",
            encoding="utf-8",
        )
        with self.assertRaises(ContributorError):
            self.load()

    def test_alias_conflict(self):
        self.config.write_text(
            "ai_contributors:\n"
            "  codex:\n    display_name: Codex\n    email: a@b.com\n    aliases: [gpt]\n"
            "  claude:\n    display_name: Claude\n    email: c@d.com\n    aliases: [gpt]\n",
            encoding="utf-8",
        )
        with self.assertRaises(ContributorError):
            self.load()

    def test_duplicate_email(self):
        self.config.write_text(
            "ai_contributors:\n"
            "  codex:\n    display_name: Codex\n    email: same@x.com\n"
            "  claude:\n    display_name: Claude\n    email: same@x.com\n",
            encoding="utf-8",
        )
        with self.assertRaises(ContributorError):
            self.load()

    def test_duplicate_display_name(self):
        self.config.write_text(
            "ai_contributors:\n"
            "  codex:\n    display_name: Same\n    email: a@x.com\n"
            "  claude:\n    display_name: Same\n    email: b@x.com\n",
            encoding="utf-8",
        )
        with self.assertRaises(ContributorError):
            self.load()

    def test_identity_matches_alias_of_other_model(self):
        self.config.write_text(
            "ai_contributors:\n"
            "  codex:\n    display_name: Codex\n    email: a@b.com\n    aliases: [claude]\n"
            "  claude:\n    display_name: Claude\n    email: c@d.com\n",
            encoding="utf-8",
        )
        with self.assertRaises(ContributorError):
            self.load()

    def test_valid_config(self):
        models = self.load()
        self.assertEqual(sorted(models), ["claude", "codex", "custom", "deepseek"])


class AiContributorGenerateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = Path(self.directory.name) / ".ai-contributors.yaml"
        self.config.write_text(SAMPLE, encoding="utf-8")
        self.models = load_config(self.config)

    def tearDown(self):
        self.directory.cleanup()

    def test_single_model(self):
        self.assertEqual(
            generate_trailers(["codex"], self.models),
            ["Co-authored-by: Codex <codex@users.noreply.github.com>"],
        )

    def test_multiple_models(self):
        self.assertEqual(
            generate_trailers(["codex", "claude"], self.models),
            [
                "Co-authored-by: Codex <codex@users.noreply.github.com>",
                "Co-authored-by: Claude <noreply@anthropic.com>",
            ],
        )

    def test_alias_resolution(self):
        self.assertEqual(
            generate_trailers(["gpt", "anthropic"], self.models),
            [
                "Co-authored-by: Codex <codex@users.noreply.github.com>",
                "Co-authored-by: Claude <noreply@anthropic.com>",
            ],
        )

    def test_duplicate_identity_deduplicated(self):
        self.assertEqual(
            generate_trailers(["codex", "gpt", "codex"], self.models),
            ["Co-authored-by: Codex <codex@users.noreply.github.com>"],
        )

    def test_unknown_model(self):
        with self.assertRaises(ContributorError):
            generate_trailers(["unknown-model"], self.models)

    def test_empty_email_rejected(self):
        with self.assertRaises(ContributorError):
            generate_trailers(["deepseek"], self.models)

    def test_custom_model(self):
        self.assertEqual(
            generate_trailers(["custom"], self.models),
            ["Co-authored-by: MyAgent <my-agent@users.noreply.github.com>"],
        )


class AiContributorResolveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = Path(self.directory.name) / ".ai-contributors.yaml"
        self.config.write_text(SAMPLE, encoding="utf-8")
        self.models = load_config(self.config)

    def tearDown(self):
        self.directory.cleanup()

    def test_resolve_by_id(self):
        self.assertEqual(resolve_model("claude", self.models)["display_name"], "Claude")

    def test_resolve_by_alias_case_insensitive(self):
        self.assertEqual(resolve_model("GPT", self.models)["display_name"], "Codex")
        self.assertEqual(resolve_model("DeepSeek-V4", self.models)["display_name"], "DeepSeek")

    def test_resolve_unknown(self):
        with self.assertRaises(ContributorError):
            resolve_model("nope", self.models)


class AiContributorValidateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = Path(self.directory.name) / ".ai-contributors.yaml"
        self.config.write_text(SAMPLE, encoding="utf-8")
        self.models = load_config(self.config)

    def tearDown(self):
        self.directory.cleanup()

    def test_valid_trailer(self):
        self.assertEqual(
            trailer_errors(
                "Subject\n\nCo-authored-by: Codex <codex@users.noreply.github.com>\n",
                self.models,
            ),
            [],
        )

    def test_multiple_valid_trailers(self):
        self.assertEqual(
            trailer_errors(
                "Subject\n\n"
                "Co-authored-by: Codex <codex@users.noreply.github.com>\n"
                "Co-authored-by: Claude <noreply@anthropic.com>\n",
                self.models,
            ),
            [],
        )

    def test_duplicate_trailer(self):
        errors = trailer_errors(
            "Co-authored-by: Codex <codex@users.noreply.github.com>\n"
            "Co-authored-by: Codex <codex@users.noreply.github.com>\n",
            self.models,
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("duplicate contributor", errors[0])

    def test_unknown_model(self):
        errors = trailer_errors(
            "Co-authored-by: Unknown <unknown@users.noreply.github.com>\n",
            self.models,
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("not registered", errors[0])

    def test_empty_email(self):
        errors = trailer_errors(
            "Co-authored-by: Codex <>\n", self.models
        )
        self.assertTrue(errors)

    def test_placeholder_email(self):
        errors = trailer_errors(
            "Co-authored-by: Codex <codex@example.com>\n", self.models
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("placeholder email", errors[0])

    def test_invalid_email_format(self):
        errors = trailer_errors(
            "Co-authored-by: Codex <not-an-email>\n", self.models
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid email", errors[0])

    def test_plain_text_without_trailers_is_valid(self):
        self.assertEqual(trailer_errors("Just some text.\n", self.models), [])


if __name__ == "__main__":
    unittest.main()
