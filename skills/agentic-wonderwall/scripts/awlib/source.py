"""Source resolution for the /aw executor.

PR A supports local sources only (upstream repository path or a version
string resolved against a local upstream checkout). Remote Release download
arrives in PR B.
"""

from __future__ import annotations

from pathlib import Path

from .manifest import ManifestError, load_manifest, validate_files
from .util import AwError, safe_join


class SourceError(AwError):
    """Raised when a source cannot be resolved or is unsafe."""


def resolve_source(source: str, local_upstream: Path | None = None) -> Path:
    """Resolve a source reference to a local package root.

    Accepts:
    - an existing local directory path (maintenance/testing);
    - a version string such as ``v2.2.0`` resolved against ``local_upstream``
      (the AW repository checkout containing ``distribution/``).

    Remote Release tags arrive in PR B; floating ``main`` is never the
    default production source.
    """
    candidate = Path(source)
    if candidate.is_dir():
        return candidate
    if local_upstream is not None:
        dist = local_upstream / "distribution"
        if dist.is_dir():
            return dist.parent  # package root == upstream checkout root
    raise SourceError(f"cannot resolve source: {source}")


def read_package_file(package_root: Path, relative: str) -> bytes:
    """Read a file directly from a package root with path-safety checks."""
    target = safe_join(package_root, relative)
    if not target.is_file():
        raise SourceError(f"package file missing: {relative}")
    return target.read_bytes()


def package_manifest(package_root: Path) -> dict:
    """Load and validate the package's distribution manifest."""
    manifest_path = package_root / "distribution" / "manifest.json"
    if not manifest_path.is_file():
        raise SourceError(f"package missing distribution/manifest.json at {package_root}")
    return load_manifest(manifest_path)
