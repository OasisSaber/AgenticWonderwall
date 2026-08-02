"""Apply adoption plans for the /aw executor.

``apply-adopt`` re-checks the plan against the current project state,
writes every planned file atomically, and only then writes
``.aw/state.json``. A failing step never leaves a half-written state file.
"""

from __future__ import annotations

from pathlib import Path

from .source import Source, package_manifest, read_package_file
from .util import AwError, read_json, safe_join, sha256_of_block, sha256_of_file, write_bytes_atomic, write_json_atomic

BLOCK_BEGIN = "<!-- AW:BEGIN MANAGED -->"
BLOCK_END = "<!-- AW:END MANAGED -->"
BLOCK_BEGIN_BYTES = b"<!-- AW:BEGIN MANAGED -->"
BLOCK_END_BYTES = b"<!-- AW:END MANAGED -->"

SELF_PREFIX = "<self>:"


def _sha256_bytes(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()


class ApplyError(AwError):
    """Raised when a plan cannot be applied safely; nothing is written."""


def _validate_plan(plan: dict) -> None:
    """Validate plan structure; raises ApplyError (not raw KeyError) on damage."""
    if plan.get("schema_version") != 1 or plan.get("plan_type") != "adopt":
        raise ApplyError("unsupported plan: schema_version/plan_type mismatch")
    for key in ("source", "selection", "files"):
        if key not in plan:
            raise ApplyError(f"plan missing key: {key}")
    if plan.get("stop_conditions"):
        raise ApplyError(f"plan has stop conditions: {plan['stop_conditions']}")
    files = plan["files"]
    if not isinstance(files, list) or not files:
        raise ApplyError("plan files must be a non-empty list")
    seen: set[str] = set()
    for op in files:
        if not isinstance(op, dict):
            raise ApplyError("plan file entry must be an object")
        for key in ("source", "destination", "ownership", "classification"):
            if key not in op:
                raise ApplyError(f"plan file entry missing key: {key}")
        if not isinstance(op["source"], str) or not op["source"]:
            raise ApplyError("plan file entry source must be a non-empty string")
        destination = op["destination"]
        if not isinstance(destination, str) or not destination:
            raise ApplyError("plan file destination must be a non-empty string")
        if destination in seen:
            raise ApplyError(f"plan has duplicate destination: {destination}")
        seen.add(destination)
        if op["ownership"] not in ("managed-replace", "managed-block", "generated-if-missing", "project-owned"):
            raise ApplyError(f"plan file entry has unknown ownership: {op['ownership']}")
        if op["classification"] not in (
            "ADD", "UNCHANGED", "CONFLICT", "BLOCK_PRESENT", "BLOCK_MISSING",
            "EXISTS_KEEP", "PROJECT_OWNED",
        ):
            raise ApplyError(f"plan file entry has unknown classification: {op['classification']}")


def _read_package_bytes(package_root: Path | None, op: dict) -> bytes:
    """Read a plan source file, verifying its content matches the plan hash.

    Raises ApplyError when the source file changed since planning, before
    anything is written.
    """
    source = op["source"]
    if source.startswith(SELF_PREFIX):
        # <self>:<path> resolves against the executor directory (aw.py's own
        # scripts/ dir) and is used for .aw/bin copies.
        return _read_self(source[len(SELF_PREFIX):])
    if package_root is None:
        raise ApplyError(f"plan requires package source for {op['destination']}; pass --source")
    content = read_package_file(package_root, source)
    expected = op.get("source_sha256")
    if expected and _sha256_bytes(content) != expected:
        raise ApplyError(f"source file changed since plan: {source}")
    return content


def _read_self(relative: str) -> bytes:
    executor_root = Path(__file__).resolve().parent.parent  # scripts/
    return read_package_file(executor_root, relative)


def _block_content_matches(dest: Path, block_content: bytes) -> bool:
    """True when the existing AGENTS.md block equals the template block."""
    text = dest.read_text(encoding="utf-8", errors="replace")
    bounds = _block_bounds(text)
    if bounds is None:
        return False
    begin, end = bounds
    cend = block_content.find(BLOCK_END_BYTES)
    if cend < 0:
        return False
    block = block_content[: cend + len(BLOCK_END_BYTES)].decode("utf-8")
    return text[begin:end].strip() == block.strip()


def _current_hash(target: Path, ownership: str) -> str:
    """Hash of a target at apply time (block hash for managed-block)."""
    if ownership == "managed-block":
        return sha256_of_block(target)
    return sha256_of_file(target)


def _check_observed(project_root: Path, op: dict) -> None:
    """Verify an existing target still matches the plan's observed hash.

    The observed hash is mandatory for classifications that imply an
    existing managed target; a plan missing it cannot bypass the lock.
    """
    dest = safe_join(project_root, op["destination"])
    observed = op.get("observed_sha256")
    if observed is None:
        raise ApplyError(f"plan missing observed hash for existing target: {op['destination']}")
    if not dest.is_file() or _current_hash(dest, op["ownership"]) != observed:
        raise ApplyError(f"target changed since plan; refusing to write: {op['destination']}")


def _check_precondition(
    project_root: Path,
    op: dict,
    prepared_sources: dict[str, bytes],
    plan: dict,
) -> None:
    """Re-check the plan's classification against current state.

    Sources are read from the pre-verified prepared cache only; no source
    file is re-read from disk here.
    """
    dest = safe_join(project_root, op["destination"])
    classification = op["classification"]
    if classification == "ADD":
        if dest.exists():
            content = prepared_sources[op["destination"]]
            if op["ownership"] == "managed-block":
                # Idempotent re-apply: block already matches the template.
                if _block_content_matches(dest, content):
                    return
                raise ApplyError(
                    f"AGENTS.md exists with a different block; agent must review: {op['destination']}"
                )
            rendered = content
            if op.get("render"):
                rendered = _render_template(rendered, plan)
            if sha256_of_file(dest) == _sha256_bytes(rendered):
                return
            raise ApplyError(f"plan says ADD but file exists with different content: {op['destination']}")
        return
    if classification == "UNCHANGED":
        if not dest.is_file():
            raise ApplyError(f"plan says UNCHANGED but file missing: {op['destination']}")
        _check_observed(project_root, op)
        return
    if classification in ("EXISTS_KEEP", "PROJECT_OWNED"):
        _check_observed(project_root, op)
        return
    if classification == "CONFLICT":
        raise ApplyError(f"managed file conflict, refusing to overwrite: {op['destination']}")
    if classification == "BLOCK_MISSING":
        raise ApplyError(f"AGENTS.md managed block missing; agent must choose insertion point: {op['destination']}")
    if classification == "BLOCK_PRESENT":
        text = dest.read_text(encoding="utf-8", errors="replace")
        if _block_bounds(text) is None:
            raise ApplyError(f"AGENTS.md block markers invalid at apply time: {op['destination']}")
        _check_observed(project_root, op)
        return
    raise ApplyError(f"unknown classification: {classification}")


def _block_bounds_bytes(data: bytes) -> tuple[int, int] | None:
    """Return (begin, end) of the AW managed block in bytes, or None when
    invalid. Requires exactly one BEGIN and one END marker, BEGIN before END."""
    begin_count = data.count(BLOCK_BEGIN_BYTES)
    end_count = data.count(BLOCK_END_BYTES)
    if begin_count != 1 or end_count != 1:
        return None
    begin = data.find(BLOCK_BEGIN_BYTES)
    end = data.find(BLOCK_END_BYTES)
    if end < begin:
        return None
    return begin, end + len(BLOCK_END_BYTES)


def _block_bounds(text: str) -> tuple[int, int] | None:
    """Return (begin, end) of the AW managed block, or None when invalid.

    Requires exactly one BEGIN and one END marker, BEGIN before END.
    """
    begin_count = text.count(BLOCK_BEGIN)
    end_count = text.count(BLOCK_END)
    if begin_count != 1 or end_count != 1:
        return None
    begin = text.index(BLOCK_BEGIN)
    end = text.index(BLOCK_END)
    if end <= begin:
        return None
    return begin, end + len(BLOCK_END)


def _apply_block(project_root: Path, op: dict, block_content: bytes) -> None:
    """Replace the AW managed block inside an existing AGENTS.md.

    Works on bytes so non-UTF-8 project content outside the block is
    preserved verbatim. The block written is the template's block range
    (BEGIN marker through END marker), excluding any trailing newline.
    """
    dest = safe_join(project_root, op["destination"])
    data = dest.read_bytes()
    bounds = _block_bounds_bytes(data)
    if bounds is None:
        raise ApplyError(f"AGENTS.md block markers invalid (must be unique, BEGIN before END): {op['destination']}")
    begin, end = bounds
    cend = block_content.find(BLOCK_END_BYTES)
    if cend < 0:
        raise ApplyError(f"managed block template missing END marker: {op['source']}")
    block = block_content[: cend + len(BLOCK_END_BYTES)]
    write_bytes_atomic(dest, data[:begin] + block + data[end:])


def _make_minimal_agents(block_content: bytes) -> bytes:
    """Generate a minimal AGENTS.md wrapping the managed block template."""
    block = block_content.decode("utf-8")
    return (
        "# AgenticWonderwall\n\n"
        "> 本文件由 /aw 接入生成；规则由 AW 管理区块声明。\n\n"
        f"{block}\n"
    ).encode("utf-8")


def _render_template(content: bytes, plan: dict) -> bytes:
    """Render supported template tokens from plan selection.

    Only two tokens are supported: {{validation_path}} and
    {{default_branch}}. No general template engine is introduced.
    """
    text = content.decode("utf-8")
    selection = plan.get("selection", {})
    validation_path = selection.get("validation_path", "scripts/check.sh")
    default_branch = selection.get("default_branch", "main")
    text = text.replace("{{validation_path}}", validation_path)
    text = text.replace("{{default_branch}}", default_branch)
    return text.encode("utf-8")


def _prepare_sources(plan: dict, package_root: Path | None) -> dict[str, bytes]:
    """Read and verify every source that may be written.

    Runs before the first project write. The returned bytes are also reused
    during the write pass, so apply writes exactly the content that passed
    plan source-hash verification.
    """
    prepared: dict[str, bytes] = {}
    writable = ("ADD", "UPDATE_SAFE", "BLOCK_PRESENT")
    for op in plan["files"]:
        if op["classification"] not in writable:
            continue
        prepared[op["destination"]] = _read_package_bytes(package_root, op)
    return prepared


def apply_adopt(project_root: Path, plan_path: Path, source: Source | None = None) -> dict:
    """Apply an adoption plan; returns the applied-file summary.

    Order: validate plan -> validate resolver source matches plan source ->
    read and verify every source that may be written -> validate every
    target precondition -> begin writes. A source mismatch therefore fails
    before the first project write.
    """
    plan = read_json(plan_path)
    _validate_plan(plan)

    # Source lock: the resolver-supplied source at apply time must match the
    # plan's recorded identity (repository/version/commit), checked before
    # any write.
    package_root: Path | None = None
    if source is not None:
        package_root = source.package_root
        plan_source = plan.get("source", {})
        if (
            source.version != plan_source.get("version")
            or source.repository != plan_source.get("repository")
            or source.commit != plan_source.get("commit")
        ):
            raise ApplyError(
                "resolver source does not match plan source "
                f"(plan {plan_source.get('version')}@{plan_source.get('commit')}); refusing to apply"
            )

    # Read and hash-check all content before the first write.
    prepared_sources = _prepare_sources(plan, package_root)

    # Validate every target before the first write.
    for op in plan["files"]:
        _check_precondition(project_root, op, prepared_sources, plan)

    written: list[str] = []
    unchanged: list[str] = []

    # Pass 2: write files (atomic per file), reusing verified content only.
    for op in plan["files"]:
        dest = safe_join(project_root, op["destination"])
        classification = op["classification"]
        if classification in ("EXISTS_KEEP", "PROJECT_OWNED", "UNCHANGED"):
            if classification == "UNCHANGED":
                unchanged.append(op["destination"])
            continue
        if classification == "ADD":
            if dest.is_file() and op["ownership"] != "managed-block":
                # Idempotent re-apply: content already matches source.
                unchanged.append(op["destination"])
                continue
            if dest.is_file() and op["ownership"] == "managed-block":
                # Re-apply: replace the block (content identical when unchanged).
                block_content = prepared_sources[op["destination"]]
                if _block_content_matches(dest, block_content):
                    unchanged.append(op["destination"])
                else:
                    _apply_block(project_root, op, block_content)
                    written.append(op["destination"])
                continue
            content = prepared_sources[op["destination"]]
            if op.get("render"):
                # Render template placeholders (e.g. {{validation_path}}).
                content = _render_template(content, plan)
            if op["destination"] == "AGENTS.md":
                content = _make_minimal_agents(content)
            write_bytes_atomic(dest, content)
            written.append(op["destination"])
        elif classification == "BLOCK_PRESENT":
            block_content = prepared_sources[op["destination"]]
            _apply_block(project_root, op, block_content)
            written.append(op["destination"])
        elif classification == "BLOCK_MISSING":
            raise ApplyError("AGENTS.md exists without managed block; stop (see plan)")
        else:
            raise ApplyError(f"cannot apply classification {classification}")

    # Install the executor into .aw/bin (managed-replace, source <self>).
    written, unchanged = install_executor(project_root, written, unchanged)

    # Only now write state.json.
    state = _build_state(project_root, plan, written, unchanged)
    write_json_atomic(project_root / ".aw/state.json", state)
    return {"written": written, "unchanged": unchanged}


def install_executor(project_root: Path, written: list[str], unchanged: list[str]) -> tuple[list[str], list[str]]:
    """Install (or refresh) the executor into .aw/bin; returns updated lists."""
    bin_root = safe_join(project_root, ".aw/bin")
    executor_files = [("aw.py", "aw.py")]
    for module in (
        "__init__.py", "util.py", "manifest.py", "source.py", "inspect.py",
        "planning.py", "apply.py", "verify.py", "update.py", "doctor.py",
    ):
        executor_files.append((f"awlib/{module}", f"awlib/{module}"))
    bin_installed = True
    for rel_src, rel_dst in executor_files:
        content = _read_self(rel_src)
        target = bin_root / rel_dst
        if target.is_file() and sha256_of_file(target) == _sha256_bytes(content):
            continue
        write_bytes_atomic(target, content)
        bin_installed = False
    if not bin_installed:
        written.append(".aw/bin/aw.py")
    else:
        unchanged.append(".aw/bin/aw.py")
    return written, unchanged


def _build_state(project_root: Path, plan: dict, written: list[str], unchanged: list[str]) -> dict:
    """Build .aw/state.json from the applied plan."""
    managed: dict = {}
    all_destinations = [op["destination"] for op in plan["files"] if op["ownership"] in ("managed-replace", "managed-block")]
    all_destinations.append(".aw/bin/aw.py")
    for dest in all_destinations:
        target = safe_join(project_root, dest)
        if not target.is_file():
            continue
        op = next((o for o in plan["files"] if o["destination"] == dest), None)
        source = op["source"] if op else "<self>:aw.py"
        ownership = op["ownership"] if op else "managed-replace"
        # managed-block: record the managed block hash, never the whole file,
        # so project content outside the block does not invalidate state.
        if ownership == "managed-block":
            installed_sha256 = sha256_of_block(target)
        else:
            installed_sha256 = sha256_of_file(target)
        managed[dest] = {
            "source": source,
            "source_sha256": op.get("source_sha256") if op else None,
            "installed_sha256": installed_sha256,
            "ownership": ownership,
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
