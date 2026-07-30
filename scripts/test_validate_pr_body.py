import unittest
from validate_pr_body import REQUIRED_REVIEW_ITEMS, validate


REVIEW = "\n".join(f"- [x] {item}" for item in REQUIRED_REVIEW_ITEMS)
BASE = f"""## Related task
- Issue: Closes #1
- Explicit human authorization:
  - Authorization source:
  - Goal:
  - Scope:

## Result
Done.

## Changes
Changed files.

## Verification
Tests passed.

## Agent self-review
{REVIEW}
"""


class ValidatePrBodyTests(unittest.TestCase):
    def test_valid_issue(self): self.assertEqual([], validate(BASE))
    def test_valid_closing_issue_keywords(self):
        for value in ("Fixes #12", "Resolves #345", "closed #6"):
            with self.subTest(value=value):
                self.assertEqual([], validate(BASE.replace("Closes #1", value)))

    def test_valid_authorization(self):
        body = BASE.replace("Closes #1", "").replace("  - Authorization source:\n  - Goal:\n  - Scope:", "  - Authorization source: chat\n  - Goal: fix\n  - Scope: scripts")
        self.assertEqual([], validate(body))

    def test_html_comment_is_allowed(self): self.assertEqual([], validate("<!-- 二选一，删除不适用项。 -->\n" + BASE))
    def test_hidden_issue_reference_does_not_pass(self):
        body = BASE.replace("Closes #1", "<!-- Closes #1 -->")
        self.assertTrue(validate(body))

    def test_both_paths(self): self.assertTrue(validate(BASE.replace("  - Authorization source:", "  - Authorization source: chat")))
    def test_no_paths(self): self.assertTrue(validate(BASE.replace("Closes #1", "")))
    def test_placeholder(self): self.assertTrue(validate(BASE.replace("#1", "#<number>")))

    def test_empty_sections(self):
        for heading in ("Result", "Changes", "Verification"):
            content = {"Result":"Done.", "Changes":"Changed files.", "Verification":"Tests passed."}[heading]
            with self.subTest(heading=heading):
                self.assertTrue(validate(BASE.replace(f"## {heading}\n{content}", f"## {heading}")))

    def test_comment_only_sections_are_empty(self):
        for heading in ("Result", "Changes", "Verification"):
            content = {"Result":"Done.", "Changes":"Changed files.", "Verification":"Tests passed."}[heading]
            with self.subTest(heading=heading):
                body = BASE.replace(
                    f"## {heading}\n{content}",
                    f"## {heading}\n<!-- hidden content -->",
                )
                self.assertTrue(validate(body))

    def test_missing_review_item(self): self.assertTrue(validate(BASE.replace(f"- [x] {REQUIRED_REVIEW_ITEMS[0]}\n", "")))
    def test_unrelated_review_item_does_not_pass(self): self.assertTrue(validate(BASE.replace(REVIEW, "- [x] Reviewed")))
    def test_review_item_unchecked(self): self.assertTrue(validate(BASE.replace(f"[x] {REQUIRED_REVIEW_ITEMS[0]}", f"[ ] {REQUIRED_REVIEW_ITEMS[0]}")))
    def test_hidden_checked_review_item_does_not_pass(self):
        item = REQUIRED_REVIEW_ITEMS[0]
        body = BASE.replace(f"- [x] {item}", f"<!-- - [x] {item} -->")
        self.assertTrue(validate(body))

    def test_authorization_fields(self):
        for field in ("Authorization source: chat", "Goal: fix", "Scope: scripts"):
            body = BASE.replace("Closes #1", "").replace("  - Authorization source:\n  - Goal:\n  - Scope:", "  - Authorization source: chat\n  - Goal: fix\n  - Scope: scripts").replace(field, field.split(":")[0] + ":")
            self.assertTrue(validate(body))

    def test_hidden_authorization_does_not_pass(self):
        body = BASE.replace("Closes #1", "").replace(
            "  - Authorization source:\n  - Goal:\n  - Scope:",
            "  - Authorization source: <!-- chat -->\n"
            "  - Goal: <!-- fix -->\n"
            "  - Scope: <!-- scripts -->",
        )
        self.assertTrue(validate(body))

    def test_invalid_issue_values(self):
        for value in (
            "not-an-issue",
            "reviewed in #123",
            "#123",
            "Closes #1 and fixes #2",
            "Closes owner/repository#123",
        ):
            with self.subTest(value=value):
                self.assertTrue(validate(BASE.replace("Closes #1", value)))


if __name__ == "__main__":
    unittest.main()
