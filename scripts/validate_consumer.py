#!/usr/bin/env python3
"""Validate the minimum TheMasterplan consumer contract.

Mechanically verifies that a caller repository satisfies the adoption
contract required by the central Actions interface:

1. the repository root exists;
2. a root ``AGENTS.md`` exists;
3. ``project-check-path`` is a non-empty POSIX relative path without
   backslashes or ``..`` segments;
4. the target is a regular file, not a symbolic link;
5. the target is tracked by Git.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path, PurePosixPath


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_relative_path(raw_path: str) -> PurePosixPath:
    if not raw_path:
        fail("project-check-path must not be empty.")

    if "\\" in raw_path:
        fail("project-check-path must use POSIX separators.")

    path = PurePosixPath(raw_path)

    if path.is_absolute():
        fail("project-check-path must be relative.")

    if ".." in path.parts:
        fail("project-check-path must not contain '..'.")

    if any(part in {"", "."} for part in path.parts):
        fail("project-check-path contains an invalid path segment.")

    return path


def require_tracked_file(root: Path, relative: PurePosixPath) -> Path:
    target = root.joinpath(*relative.parts)

    if target.is_symlink():
        fail(f"{relative} must not be a symbolic link.")

    if not target.is_file():
        fail(f"{relative} does not exist or is not a regular file.")

    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--error-unmatch",
            "--",
            relative.as_posix(),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    if result.returncode != 0:
        fail(f"{relative} must be tracked by Git.")

    return target


def main() -> int:
    if len(sys.argv) != 3:
        fail("Usage: validate_consumer.py <repository-root> <project-check-path>")

    root = Path(sys.argv[1]).resolve()

    if not root.is_dir():
        fail("Caller repository root does not exist.")

    if not (root / "AGENTS.md").is_file():
        fail("Caller repository must contain a root AGENTS.md.")

    check_path = validate_relative_path(sys.argv[2])
    require_tracked_file(root, check_path)

    print("TheMasterplan consumer contract is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
