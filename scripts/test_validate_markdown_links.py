import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from validate_markdown_links import LinkError, main, validate_repository


class ValidateMarkdownLinksTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write(self, path, content=""):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def test_supported_links_and_anchors_pass(self):
        self.write(
            "README.md",
            """# Home

## Local section

[same file](#local-section)

## 本仓库验证

[Chinese heading](#本仓库验证)
[cross file](docs/guide.md#details)
![image](assets/pixel.png)
[reference][guide]
[guide]: docs/guide.md
<a href="docs/guide.md#manual-anchor">HTML link</a>
<img src="assets/pixel.png">
""",
        )
        self.write(
            "docs/guide.md",
            """# Guide

## Details

<a id="manual-anchor"></a>
""",
        )
        self.write("assets/pixel.png", "not a real image")

        self.assertEqual([], validate_repository(self.root))

    def test_missing_same_file_anchor_fails(self):
        self.write("README.md", "# Home\n\n[missing](#not-here)\n")

        self.assertEqual(
            [
                LinkError(
                    Path("README.md"), "#not-here", "anchor not found"
                )
            ],
            validate_repository(self.root),
        )

    def test_missing_cross_file_anchor_fails(self):
        self.write(
            "README.md", "[missing](docs/guide.md#not-here)\n"
        )
        self.write("docs/guide.md", "# Guide\n")

        self.assertEqual(
            [
                LinkError(
                    Path("README.md"),
                    "docs/guide.md#not-here",
                    "anchor not found",
                )
            ],
            validate_repository(self.root),
        )

    def test_missing_file_fails(self):
        self.write("README.md", "[missing](docs/missing.md)\n")

        self.assertEqual(
            [
                LinkError(
                    Path("README.md"),
                    "docs/missing.md",
                    "target not found",
                )
            ],
            validate_repository(self.root),
        )

    def test_cli_reports_source_target_and_reason(self):
        self.write("README.md", "[missing](docs/missing.md)\n")
        output = io.StringIO()

        with redirect_stdout(output):
            result = main([str(self.root)])

        self.assertEqual(1, result)
        self.assertIn(
            "BROKEN LINK: README.md -> docs/missing.md "
            "(target not found)",
            output.getvalue(),
        )

    def test_code_examples_and_comments_are_ignored(self):
        self.write(
            "README.md",
            """# Home

`[inline](missing-inline.md)`

```markdown
[fenced](missing-fenced.md)
```

<!-- [comment](missing-comment.md) -->
""",
        )

        self.assertEqual([], validate_repository(self.root))

    def test_repository_escape_fails(self):
        outside = self.root.parent / f"{self.root.name}-outside.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        self.addCleanup(outside.unlink)
        target = f"../{outside.name}"
        self.write("README.md", f"[outside]({target})\n")

        self.assertEqual(
            [
                LinkError(
                    Path("README.md"),
                    target,
                    "target escapes repository",
                )
            ],
            validate_repository(self.root),
        )

    def test_missing_reference_definition_fails(self):
        self.write("README.md", "[guide][missing]\n")

        self.assertEqual(
            [
                LinkError(
                    Path("README.md"),
                    "missing",
                    "missing reference definition",
                )
            ],
            validate_repository(self.root),
        )

    def test_duplicate_heading_anchor_suffix_passes(self):
        self.write(
            "README.md",
            "# Repeat\n\n# Repeat\n\n[second](#repeat-1)\n",
        )

        self.assertEqual([], validate_repository(self.root))

    def test_external_links_are_ignored(self):
        self.write(
            "README.md",
            "[HTTPS](https://example.com/missing#anchor)\n"
            '<a href="//example.com/path">protocol relative</a>\n',
        )

        self.assertEqual([], validate_repository(self.root))


if __name__ == "__main__":
    unittest.main()
