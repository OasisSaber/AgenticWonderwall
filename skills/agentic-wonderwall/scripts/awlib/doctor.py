"""doctor diagnostics for the /aw executor (read-only).

Reports installation health with minimal remediation suggestions. Never
writes files.
"""

from __future__ import annotations

from pathlib import Path

from .util import AwError, read_json, safe_join, sha256_of_block, sha256_of_file

CORE_PATHS = ("core/policy.md", "core/workflow.md")
EXECUTOR_MODULES = (
    "__init__.py", "util.py", "manifest.py", "source.py",
    "inspect.py", "planning.py", "apply.py", "verify.py", "update.py", "doctor.py",
)


def _check_managed(project_root: Path, relative: str, recorded: dict) -> list[str]:
    try:
        target = safe_join(project_root, relative)
    except AwError as exc:
        return [f"unsafe path in state: {relative} ({exc})"]
    if not target.is_file():
        return [f"missing managed file: {relative}"]
    if recorded.get("ownership") == "managed-block":
        current = sha256_of_block(target)
        if not current:
            return [f"managed block missing in: {relative}"]
    else:
        current = sha256_of_file(target)
    if current != recorded.get("installed_sha256"):
        return [f"hash mismatch (managed file modified): {relative}"]
    return []


def doctor(project_root: Path) -> dict:
    """Diagnose the local AW installation; returns report with suggestions."""
    issues: list[str] = []
    suggestions: list[str] = []

    state_path = project_root / ".aw/state.json"
    if not state_path.is_file():
        return {
            "ok": False,
            "status": "ABSENT",
            "issues": ["missing .aw/state.json (AW not adopted)"],
            "suggestions": ["run plan-adopt + apply-adopt to adopt this project"],
        }
    try:
        state = read_json(state_path)
    except AwError as exc:
        return {
            "ok": False,
            "status": "BROKEN",
            "issues": [f"state.json unreadable: {exc}"],
            "suggestions": ["repair or re-adopt .aw/state.json"],
        }

    source = state.get("source", {})
    if not source.get("version") or not source.get("commit"):
        issues.append("state.json source.version/commit missing")
        suggestions.append("re-run plan-adopt to record the resolver identity")

    selection = state.get("selection", {})
    validation_path = selection.get("validation_path")
    if not validation_path:
        issues.append("state.json selection.validation_path missing")
    else:
        try:
            vtarget = safe_join(project_root, validation_path)
        except AwError:
            issues.append(f"unsafe validation_path in state: {validation_path}")
        else:
            if not vtarget.is_file():
                issues.append(f"missing validation entrypoint: {validation_path}")
                suggestions.append(f"implement or restore {validation_path}")

    for relative in CORE_PATHS:
        try:
            target = safe_join(project_root, relative)
        except AwError:
            issues.append(f"unsafe core path: {relative}")
            continue
        if not target.is_file():
            issues.append(f"missing required: {relative}")
            suggestions.append(f"re-run apply-adopt to install {relative}")

    managed = state.get("managed_files", {})
    if not isinstance(managed, dict):
        issues.append("state.json managed_files must be an object")
    else:
        for relative, recorded in managed.items():
            if not isinstance(recorded, dict) or "installed_sha256" not in recorded:
                issues.append(f"malformed state entry: {relative}")
                continue
            issues.extend(_check_managed(project_root, relative, recorded))
            if issues and issues[-1].startswith("hash mismatch"):
                suggestions.append(
                    f"local changes to {relative} block the update; review or revert them"
                )

    bin_root = project_root / ".aw/bin"
    required_bin = ["aw.py"] + [f"awlib/{m}" for m in EXECUTOR_MODULES]
    for rel in required_bin:
        if not (bin_root / rel).is_file():
            issues.append(f"missing executor file: .aw/bin/{rel}")
    if not issues:
        return {"ok": True, "status": "OK", "issues": [], "suggestions": []}
    return {
        "ok": False,
        "status": "ISSUES_FOUND",
        "issues": issues,
        "suggestions": suggestions,
    }
