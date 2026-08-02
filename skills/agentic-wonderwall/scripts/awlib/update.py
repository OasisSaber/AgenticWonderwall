"""plan-update / apply-update for the /aw executor (PR B).

Updates an adopted project from one distribution to another. Classification:

- ADD               new file not present locally nor recorded in state
- UPDATE_SAFE       managed file matches the recorded state hash (unmodified)
                    but differs from the new source -> safe to update
- UNCHANGED         local content already equals the new source
- LOCAL_MODIFIED    managed file differs from the recorded state hash ->
                    never overwritten, update stops
- REMOVED_UPSTREAM  recorded in state, absent from the new manifest; removed
                    only when the local file still matches the recorded hash
- PROJECT_OWNED     never touched
- SELECTION_CHANGED profile/adapter/validation_path changes are not applied
                    automatically; update stops for human review

All sources and targets are verified before the first write.
"""

from __future__ import annotations

from pathlib import Path

from .apply import (
    ApplyError,
    _apply_block,
    _block_content_matches,
    _current_hash,
    _make_minimal_agents,
    _prepare_sources,
    _render_template,
    _sha256_bytes,
    install_executor,
)
from .manifest import select_files
from .source import Source, package_manifest, read_package_file
from .util import AwError, read_json, safe_join, sha256_of_block, sha256_of_file, write_json_atomic, write_bytes_atomic

CLASSIFICATIONS = (
    "ADD", "UPDATE_SAFE", "UNCHANGED", "LOCAL_MODIFIED",
    "REMOVED_UPSTREAM", "PROJECT_OWNED", "SELECTION_CHANGED",
)


class UpdateError(AwError):
    """Raised when an update cannot be planned or applied safely."""


def _recorded_hash(state: dict, relative: str) -> str | None:
    entry = state.get("managed_files", {}).get(relative)
    if not isinstance(entry, dict):
        return None
    return entry.get("installed_sha256")


def _local_hash(project_root: Path, relative: str, ownership: str) -> str | None:
    try:
        target = safe_join(project_root, relative)
    except AwError:
        return None
    if not target.is_file():
        return None
    if ownership == "managed-block":
        return sha256_of_block(target)
    return sha256_of_file(target)


def plan_update(project_root: Path, source: Source, state: dict) -> dict:
    """Generate an update plan comparing state + local files with `source`.

    The plan keeps the recorded selection (no automatic switching of
    profile/adapter/validation_path); a manifest that no longer supports the
    recorded selection produces SELECTION_CHANGED and stops.
    """
    package_root = source.package_root
    manifest = package_manifest(package_root)
    selection = state.get("selection", {})
    profile = selection.get("profile")
    adapter = selection.get("adapter")
    if not profile or not adapter:
        raise UpdateError("state.json selection missing profile/adapter")

    profile_names = set(manifest.get("components", {}).get("profiles", []))
    adapter_names = set(manifest.get("components", {}).get("adapters", []))
    if profile not in profile_names or adapter not in adapter_names:
        return {
            "schema_version": 1,
            "plan_type": "update",
            "source": source.as_dict(),
            "selection": selection,
            "files": [],
            "notes": [],
            "stop_conditions": [
                f"selection no longer supported by manifest: profile={profile}, adapter={adapter}"
            ],
        }

    entries = [
        e
        for e in select_files(manifest, profile, adapter)
        if e["destination"] not in (".github/workflows/check.yml", "scripts/check.sh")
    ]

    operations: list[dict] = []
    stop_conditions: list[str] = []
    notes: list[str] = []

    # Files present in the target manifest.
    for entry in entries:
        dest = entry["destination"]
        ownership = entry["ownership"]
        op = {
            "source": entry["source"],
            "destination": dest,
            "ownership": ownership,
            "required": entry.get("required", False),
        }
        recorded = _recorded_hash(state, dest)
        local = _local_hash(project_root, dest, ownership)

        if ownership == "project-owned":
            op["classification"] = "PROJECT_OWNED"
            operations.append(op)
            continue

        try:
            source_hash = sha256_of_file(safe_join(package_root, entry["source"]))
        except AwError:
            raise UpdateError(f"package source file missing: {entry['source']}")
        op["source_sha256"] = source_hash

        if local is None:
            # Not present locally.
            if recorded is None:
                op["classification"] = "ADD"
            else:
                # Recorded in state but deleted locally: treat as local
                # modification (never silently recreate or delete).
                op["classification"] = "LOCAL_MODIFIED"
                op["observed_sha256"] = recorded
                stop_conditions.append(f"locally deleted managed file: {dest}")
            operations.append(op)
            continue

        op["observed_sha256"] = local
        if ownership == "managed-block":
            source_block = sha256_of_block(safe_join(package_root, entry["source"]))
            if local == source_block:
                op["classification"] = "UNCHANGED"
            elif recorded is not None and local == recorded:
                op["classification"] = "UPDATE_SAFE"
            else:
                op["classification"] = "LOCAL_MODIFIED"
                stop_conditions.append(f"locally modified managed block: {dest}")
        elif ownership in ("managed-replace",):
            if local == source_hash:
                op["classification"] = "UNCHANGED"
            elif recorded is not None and local == recorded:
                op["classification"] = "UPDATE_SAFE"
            else:
                op["classification"] = "LOCAL_MODIFIED"
                stop_conditions.append(f"locally modified managed file: {dest}")
        else:  # generated-if-missing and anything else: never overwritten
            op["classification"] = "UNCHANGED"
        operations.append(op)

    # Files recorded in state but absent from the target manifest.
    state_destinations = set(state.get("managed_files", {}).keys())
    target_destinations = {op["destination"] for op in operations}
    for dest in sorted(state_destinations - target_destinations):
        if dest == ".aw/bin/aw.py":
            continue  # the executor is refreshed, not removed
        recorded = _recorded_hash(state, dest)
        local = _local_hash(project_root, dest, "managed-replace")
        op = {
            "source": None,
            "destination": dest,
            "ownership": "managed-replace",
            "required": False,
        }
        if local is not None and recorded is not None and local == recorded:
            op["classification"] = "REMOVED_UPSTREAM"
            op["observed_sha256"] = local
        else:
            op["classification"] = "LOCAL_MODIFIED"
            op["observed_sha256"] = local
            stop_conditions.append(f"upstream removed but local differs: {dest}")
        operations.append(op)

    if source.as_dict() != state.get("source", {}):
        notes.append(
            f"update {state.get('source', {}).get('version')} -> {source.version} "
            f"({source.commit})"
        )

    return {
        "schema_version": 1,
        "plan_type": "update",
        "source": source.as_dict(),
        "selection": selection,
        "files": operations,
        "notes": notes,
        "stop_conditions": stop_conditions,
    }


def _validate_update_plan(plan: dict) -> None:
    if plan.get("schema_version") != 1 or plan.get("plan_type") != "update":
        raise UpdateError("unsupported plan: schema_version/plan_type mismatch")
    for key in ("source", "selection", "files"):
        if key not in plan:
            raise UpdateError(f"plan missing key: {key}")
    if plan.get("stop_conditions"):
        raise UpdateError(f"plan has stop conditions: {plan['stop_conditions']}")
    if not isinstance(plan["files"], list):
        raise UpdateError("plan files must be a list")


def _check_update_target(project_root: Path, op: dict) -> None:
    """Verify an update target still matches its observed hash."""
    dest = safe_join(project_root, op["destination"])
    observed = op.get("observed_sha256")
    classification = op["classification"]
    if classification in ("ADD", "REMOVED_UPSTREAM"):
        if classification == "ADD" and dest.exists():
            raise UpdateError(f"plan says ADD but file exists: {op['destination']}")
        if classification == "REMOVED_UPSTREAM":
            if not dest.is_file():
                raise UpdateError(f"plan says REMOVED_UPSTREAM but file missing: {op['destination']}")
            if observed is None or sha256_of_file(dest) != observed:
                raise UpdateError(f"upstream-removed file changed locally: {op['destination']}")
        return
    if classification in ("UPDATE_SAFE",):
        if not dest.is_file():
            raise UpdateError(f"plan says UPDATE_SAFE but file missing: {op['destination']}")
        if observed is None or _current_hash(dest, op["ownership"]) != observed:
            raise UpdateError(f"target changed since plan; refusing to write: {op['destination']}")
        return
    if classification in ("UNCHANGED", "PROJECT_OWNED"):
        return
    raise UpdateError(f"cannot apply classification {classification}")


def apply_update(project_root: Path, plan_path: Path, source: Source | None = None) -> dict:
    """Apply an update plan; verifies all sources/targets before first write."""
    plan = read_json(plan_path)
    _validate_update_plan(plan)

    package_root: Path | None = None
    if source is not None:
        package_root = source.package_root
        plan_source = plan.get("source", {})
        if (
            source.version != plan_source.get("version")
            or source.repository != plan_source.get("repository")
            or source.commit != plan_source.get("commit")
        ):
            raise UpdateError("resolver source does not match plan source; refusing to apply")

    prepared_sources = _prepare_sources(plan, package_root)

    # Preconditions: every writable target verified before any write.
    for op in plan["files"]:
        _check_update_target(project_root, op)

    written: list[str] = []
    unchanged: list[str] = []
    removed: list[str] = []

    for op in plan["files"]:
        dest = safe_join(project_root, op["destination"])
        classification = op["classification"]
        if classification == "UNCHANGED":
            unchanged.append(op["destination"])
        elif classification == "PROJECT_OWNED":
            unchanged.append(op["destination"])
        elif classification == "ADD":
            content = prepared_sources[op["destination"]]
            if op.get("render"):
                content = _render_template(content, plan)
            if op["destination"] == "AGENTS.md":
                content = _make_minimal_agents(content)
            write_bytes_atomic(dest, content)
            written.append(op["destination"])
        elif classification == "UPDATE_SAFE":
            content = prepared_sources[op["destination"]]
            if op.get("render"):
                content = _render_template(content, plan)
            if op["ownership"] == "managed-block":
                _apply_block(project_root, op, content)
            else:
                write_bytes_atomic(dest, content)
            written.append(op["destination"])
        elif classification == "REMOVED_UPSTREAM":
            dest.unlink()
            removed.append(op["destination"])
        else:
            raise UpdateError(f"cannot apply classification {classification}")

    written, unchanged = install_executor(project_root, written, unchanged)

    # Rebuild state from the applied update.
    state = _build_updated_state(project_root, plan, written, unchanged, removed)
    write_json_atomic(project_root / ".aw/state.json", state)
    return {"written": written, "unchanged": unchanged, "removed": removed}


def _build_updated_state(project_root: Path, plan: dict, written: list[str], unchanged: list[str], removed: list[str]) -> dict:
    """Build the new state after an update (selection preserved).

    Only managed-replace / managed-block files (plus the executor) are
    recorded, matching adopt's state model; project-owned files are never
    tracked and therefore never eligible for upstream-removal.
    """
    managed: dict = {}
    for op in plan["files"]:
        dest = op["destination"]
        if op["classification"] == "REMOVED_UPSTREAM":
            continue
        if op["ownership"] not in ("managed-replace", "managed-block"):
            continue
        target = safe_join(project_root, dest)
        if not target.is_file():
            continue
        if op["ownership"] == "managed-block":
            installed = sha256_of_block(target)
        else:
            installed = sha256_of_file(target)
        managed[dest] = {
            "source": op.get("source"),
            "source_sha256": op.get("source_sha256"),
            "installed_sha256": installed,
            "ownership": op["ownership"],
        }
    # Executor entry.
    bin_target = safe_join(project_root, ".aw/bin/aw.py")
    if bin_target.is_file():
        managed[".aw/bin/aw.py"] = {
            "source": "<self>:aw.py",
            "source_sha256": None,
            "installed_sha256": sha256_of_file(bin_target),
            "ownership": "managed-replace",
        }
    return {
        "schema_version": 1,
        "source": plan["source"],
        "selection": plan["selection"],
        "managed_files": managed,
        "adoption": {
            "date": None,
            "platform": None,
            "git_version": None,
            "jj_version": None,
            "status": "PARTIAL",
        },
    }
