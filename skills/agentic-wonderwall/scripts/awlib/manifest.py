"""Manifest loading and validation for the /aw executor.

The distribution manifest (``distribution/manifest.json``) describes the
files shipped in an AW release package. This module validates its structure
and path safety without requiring a third-party JSON Schema library.
"""

from __future__ import annotations

from pathlib import Path

import re

from .util import AwError, SCHEMA_VERSION, read_json, safe_join

ALLOWED_OWNERSHIPS = ("managed-replace", "managed-block", "generated-if-missing", "project-owned")

REQUIRED_KEYS = ("schema_version", "distribution_version", "files")

# Full 40-char hex SHA pattern, used by the resolver for commit refs.
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ManifestError(AwError):
    """Raised when a manifest is structurally invalid or unsafe."""


def load_manifest(path: Path) -> dict:
    """Load and validate a distribution manifest.

    Returns the validated manifest dict. Raises ManifestError on any
    structural, schema or path-safety problem.
    """
    data = read_json(path)
    for key in REQUIRED_KEYS:
        if key not in data:
            raise ManifestError(f"manifest missing required key: {key}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ManifestError(
            f"unsupported manifest schema_version: {data['schema_version']}"
        )
    if not isinstance(data["distribution_version"], str) or not data["distribution_version"]:
        raise ManifestError("manifest distribution_version must be a non-empty string")
    if "source_repository" in data and not isinstance(data["source_repository"], str):
        raise ManifestError("manifest source_repository must be a string")
    if not isinstance(data["files"], list) or not data["files"]:
        raise ManifestError("manifest files must be a non-empty list")
    validate_files(data["files"])
    return data


def validate_files(files: list) -> None:
    """Validate file entries: required fields, path safety, no duplicate targets."""
    seen_destinations: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise ManifestError("manifest file entry must be an object")
        for key in ("source", "destination", "ownership"):
            if key not in entry:
                raise ManifestError(f"manifest file entry missing key: {key}")
        source = entry["source"]
        destination = entry["destination"]
        ownership = entry["ownership"]
        if not isinstance(source, str) or not source:
            raise ManifestError("manifest source must be a non-empty string")
        if not isinstance(destination, str) or not destination:
            raise ManifestError("manifest destination must be a non-empty string")
        if ownership not in ALLOWED_OWNERSHIPS:
            raise ManifestError(f"unknown ownership type: {ownership}")
        # Path safety: both source (relative to package root) and destination
        # (relative to project root) must be safe joins.
        for label, rel in (("source", source), ("destination", destination)):
            try:
                safe_join(Path("."), rel)
            except AwError as exc:
                raise ManifestError(f"manifest {label} {rel!r}: {exc}")
        if destination in seen_destinations:
            raise ManifestError(f"duplicate destination in manifest: {destination}")
        seen_destinations.add(destination)
        if "required" in entry and not isinstance(entry["required"], bool):
            raise ManifestError("manifest file entry 'required' must be a boolean")


def select_files(manifest: dict, profile: str, adapter: str) -> list[dict]:
    """Return manifest file entries selected for the given profile/adapter.

    Entries whose destination starts with ``profiles/`` are kept only when
    the profile is selected; ``adapters/`` likewise. The manifest may also
    carry a ``selection`` map declaring which profile/adapter names exist.
    """
    profile_names = set(manifest.get("components", {}).get("profiles", []))
    adapter_names = set(manifest.get("components", {}).get("adapters", []))
    selected: list[dict] = []
    for entry in manifest["files"]:
        dest = entry["destination"]
        if dest.startswith("profiles/"):
            if profile not in profile_names or not dest.startswith(f"profiles/{profile}."):
                continue
        if dest.startswith("adapters/"):
            if adapter not in adapter_names or not dest.startswith(f"adapters/{adapter}."):
                continue
        selected.append(entry)
    return selected
