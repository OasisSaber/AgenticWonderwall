#!/usr/bin/env python3
"""Validate repository-local Markdown links and supported heading anchors."""

from __future__ import annotations

import html
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

EXCLUDED_DIRS = {
    ".git",
    ".jj",
    "node_modules",
    ".venv",
    "venv",
    ".cache",
    "__pycache__",
}
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass(frozen=True)
class LinkError:
    source: Path
    target: str
    reason: str


def normalize_label(value: str) -> str:
    return " ".join(value.strip().lower().split())


def strip_code(markdown: str) -> str:
    output = []
    fence_char = None
    fence_length = 0

    for line in markdown.splitlines(keepends=True):
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence_char is not None:
            if (
                fence
                and fence.group(1)[0] == fence_char
                and len(fence.group(1)) >= fence_length
            ):
                fence_char = None
                fence_length = 0
            output.append("\n" if line.endswith("\n") else "")
            continue
        if fence:
            fence_char = fence.group(1)[0]
            fence_length = len(fence.group(1))
            output.append("\n" if line.endswith("\n") else "")
            continue
        if line.startswith("    ") or line.startswith("\t"):
            output.append("\n" if line.endswith("\n") else "")
            continue

        result = []
        index = 0
        while index < len(line):
            if line[index] != "`":
                result.append(line[index])
                index += 1
                continue
            run_end = index
            while run_end < len(line) and line[run_end] == "`":
                run_end += 1
            marker = line[index:run_end]
            close = line.find(marker, run_end)
            if close == -1:
                result.append(marker)
                index = run_end
            else:
                result.append(" " * (close + len(marker) - index))
                index = close + len(marker)
        output.append("".join(result))

    return "".join(output)


def find_closing(
    text: str, start: int, opening: str, closing: str
) -> int | None:
    depth = 1
    index = start
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == opening:
            depth += 1
        elif text[index] == closing:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def destination_from_parentheses(content: str) -> str | None:
    content = content.strip()
    if not content:
        return ""
    if content.startswith("<"):
        end = content.find(">", 1)
        return content[1:end] if end != -1 else None

    depth = 0
    escaped = False
    destination = []
    for character in content:
        if escaped:
            destination.append(character)
            escaped = False
            continue
        if character == "\\":
            escaped = True
            destination.append(character)
            continue
        if character == "(":
            depth += 1
        elif character == ")" and depth > 0:
            depth -= 1
        elif character.isspace() and depth == 0:
            break
        destination.append(character)
    return "".join(destination)


def markdown_targets(text: str) -> list[str]:
    definitions = {}
    for match in re.finditer(
        r"(?m)^ {0,3}\[([^\]]+)\]:\s*(?:<([^>]+)>|(\S+))", text
    ):
        definitions[normalize_label(match.group(1))] = (
            match.group(2) or match.group(3)
        )

    targets = []
    explicit_references = []
    shortcut_references = []
    index = 0
    while index < len(text):
        image = text.startswith("![", index)
        if text[index] != "[" and not image:
            index += 1
            continue
        bracket = index + 1 if image else index
        backslashes = 0
        escape_index = index - 1
        while escape_index >= 0 and text[escape_index] == "\\":
            backslashes += 1
            escape_index -= 1
        if backslashes % 2 == 1:
            index += 1
            continue
        label_end = find_closing(text, bracket + 1, "[", "]")
        if label_end is None:
            index += 1
            continue
        label = text[bracket + 1 : label_end]
        next_index = label_end + 1
        if next_index < len(text) and text[next_index] == "(":
            target_end = find_closing(text, next_index + 1, "(", ")")
            if target_end is not None:
                target = destination_from_parentheses(
                    text[next_index + 1 : target_end]
                )
                if target is not None:
                    targets.append(target)
                index = target_end + 1
                continue
        if next_index < len(text) and text[next_index] == "[":
            reference_end = find_closing(
                text, next_index + 1, "[", "]"
            )
            if reference_end is not None:
                reference = text[next_index + 1 : reference_end] or label
                explicit_references.append(normalize_label(reference))
                index = reference_end + 1
                continue
        shortcut_references.append(normalize_label(label))
        index = label_end + 1

    for reference in explicit_references:
        if reference in definitions:
            targets.append(definitions[reference])
        else:
            targets.append(f"__MISSING_REFERENCE__:{reference}")
    for reference in shortcut_references:
        if reference in definitions:
            targets.append(definitions[reference])

    targets.extend(
        match.group(3)
        for match in re.finditer(
            r"\b(href|src)\s*=\s*([\"'])(.*?)\2",
            text,
            re.IGNORECASE,
        )
    )
    return targets


def heading_slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = html.unescape(value)
    value = re.sub(r"[`*_~]", "", value).strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"\s+", "-", value)


def markdown_anchors(markdown: str) -> set[str]:
    visible = strip_code(HTML_COMMENT.sub("", markdown))
    anchors = set()
    occurrences: dict[str, int] = {}

    for match in re.finditer(
        r"(?m)^ {0,3}#{1,6}[ \t]+(.+?)\s*$", visible
    ):
        heading = re.sub(r"[ \t]+#+[ \t]*$", "", match.group(1))
        base = heading_slug(heading)
        if not base:
            continue
        count = occurrences.get(base, 0)
        anchors.add(base if count == 0 else f"{base}-{count}")
        occurrences[base] = count + 1

    anchors.update(
        html.unescape(match.group(2))
        for match in re.finditer(
            r"\b(?:id|name)\s*=\s*([\"'])(.*?)\1",
            visible,
            re.IGNORECASE,
        )
        if match.group(2)
    )
    return anchors


def validate_target(
    root: Path,
    source: Path,
    raw_target: str,
    anchor_cache: dict[Path, set[str]],
) -> LinkError | None:
    relative_source = source.relative_to(root)
    if raw_target.startswith("__MISSING_REFERENCE__:"):
        reference = raw_target.split(":", 1)[1]
        return LinkError(
            relative_source, reference, "missing reference definition"
        )

    target = html.unescape(raw_target.strip())
    if not target or target.startswith("//"):
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
        return None

    target = target.replace("\\ ", " ")
    parts = urlsplit(target)
    path_text = unquote(parts.path)
    fragment = unquote(parts.fragment)

    if not path_text:
        candidate = source
    elif path_text.startswith("/"):
        candidate = root / path_text.lstrip("/")
    else:
        candidate = source.parent / path_text
    candidate = candidate.resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        return LinkError(
            relative_source, raw_target, "target escapes repository"
        )
    if not candidate.exists():
        return LinkError(relative_source, raw_target, "target not found")

    if fragment and candidate.suffix.lower() in {".md", ".markdown"}:
        if candidate not in anchor_cache:
            anchor_cache[candidate] = markdown_anchors(
                candidate.read_text(encoding="utf-8")
            )
        if fragment not in anchor_cache[candidate]:
            return LinkError(relative_source, raw_target, "anchor not found")
    return None


def validate_repository(root: Path) -> list[LinkError]:
    root = root.resolve()
    broken = []
    anchor_cache: dict[Path, set[str]] = {}

    for current, directories, files in os.walk(root):
        directories[:] = [
            directory
            for directory in directories
            if directory not in EXCLUDED_DIRS
        ]
        current_path = Path(current)
        for filename in files:
            if not filename.lower().endswith(".md"):
                continue
            source = current_path / filename
            markdown = source.read_text(encoding="utf-8")
            visible = strip_code(HTML_COMMENT.sub("", markdown))
            for target in markdown_targets(visible):
                error = validate_target(
                    root, source, target, anchor_cache
                )
                if error is not None:
                    broken.append(error)
    return broken


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    root = (
        Path(arguments[0])
        if arguments
        else Path(__file__).resolve().parent.parent
    )
    broken = validate_repository(root)
    if broken:
        for error in broken:
            print(
                f"  BROKEN LINK: {error.source} -> {error.target} "
                f"({error.reason})"
            )
        return 1
    print("  All internal Markdown links and anchors resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
