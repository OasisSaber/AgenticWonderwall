"""Local file-layer verification for the /aw executor.

``verify`` checks that the installed AW files match .aw/state.json hashes,
that required files exist, and that the AGENTS.md managed block is valid.
It does not run the project's own validation entrypoint (that is the
Skill/Agent layer's job) and never writes files.
"""

from __future__ import annotations

from pathlib import Path

from .util import AwError, read_json, safe_join, sha256_of_block, sha256_of_file

CORE_PATHS = ("core/policy.md", "core/workflow.md")


def _check_hash(project_root: Path, relative: str, recorded: dict) -> list[str]:
    try:
        target = safe_join(project_root, relative)
    except AwError as exc:
        return [f"unsafe path in state: {relative} ({exc})"]
    if not target.is_file():
        return [f"missing: {relative}"]
    if recorded.get("ownership") == "managed-block":
        current = sha256_of_block(target)
        if not current:
            return [f"managed block missing in: {relative}"]
    else:
        current = sha256_of_file(target)
    if current != recorded.get("installed_sha256"):
        return [f"hash mismatch: {relative}"]
    return []


def verify(project_root: Path) -> dict:
    """Verify the local AW installation; returns a machine-readable report."""
    issues: list[str] = []
    state_path = project_root / ".aw/state.json"
    if not state_path.is_file():
        return {"ok": False, "status": "ABSENT", "issues": ["missing .aw/state.json"]}

    try:
        state = read_json(state_path)
    except AwError as exc:
        return {"ok": False, "status": "BROKEN", "issues": [str(exc)]}

    for relative in CORE_PATHS:
        if not (project_root / relative).is_file():
            issues.append(f"missing required: {relative}")

    managed = state.get("managed_files", {})
    if not isinstance(managed, dict):
        issues.append("state.json managed_files must be an object")
    else:
        for relative, recorded in managed.items():
            if not isinstance(recorded, dict) or "installed_sha256" not in recorded:
                issues.append(f"malformed state entry: {relative}")
                continue
            issues.extend(_check_hash(project_root, relative, recorded))

    # AGENTS.md managed block validity.
    agents = project_root / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8", errors="replace")
        begin = text.count("<!-- AW:BEGIN MANAGED -->")
        end = text.count("<!-- AW:END MANAGED -->")
        if begin != 1 or end != 1:
            issues.append(f"AGENTS.md managed block markers invalid (begin={begin}, end={end})")
    else:
        issues.append("missing AGENTS.md")

    # Selection validation path must exist.
    validation_path = state.get("selection", {}).get("validation_path")
    if not validation_path:
        issues.append("state.json selection.validation_path missing")
    else:
        try:
            validation_target = safe_join(project_root, validation_path)
        except AwError:
            issues.append(f"unsafe validation_path in state: {validation_path}")
        else:
            if not validation_target.is_file():
                issues.append(f"missing validation entrypoint: {validation_path}")

    # Executor installation must be complete (.aw/bin/aw.py + awlib/).
    bin_root = project_root / ".aw/bin"
    required_bin = ["aw.py"] + [
        f"awlib/{module}"
        for module in ("__init__.py", "util.py", "manifest.py", "source.py", "inspect.py", "planning.py", "apply.py", "verify.py")
    ]
    for rel in required_bin:
        if not (bin_root / rel).is_file():
            issues.append(f"missing executor file: .aw/bin/{rel}")

    ok = not issues
    return {"ok": ok, "status": "OK" if ok else "BROKEN", "issues": issues}
