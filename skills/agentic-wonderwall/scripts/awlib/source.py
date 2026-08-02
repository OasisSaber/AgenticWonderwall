"""Source resolution for the /aw executor (PR B).

A *Source* is the resolved identity of an AW distribution:

- ``repository``: owning repository (from the manifest);
- ``version``: distribution version (from the manifest);
- ``commit``: full commit SHA the package content came from (resolved by
  the resolver, never stored inside the static manifest itself);
- ``package_root``: local directory containing ``distribution/`` and the
  package files referenced by the manifest.

Resolvers: local directory (tests/maintenance) and remote Release tag /
full commit SHA (downloaded, safely extracted and cached under
``.aw/cache/``). Tests use local fixtures or a temporary HTTP server, never
live GitHub.
"""

from __future__ import annotations

import io
import json
import os
import re
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .manifest import FULL_SHA_RE, ManifestError, load_manifest
from .util import AwError, safe_join

DEFAULT_REPOSITORY = "OasisSaber/AgenticWonderwall"
ARCHIVE_URL = (
    "https://codeload.github.com/{repository}/tar.gz/{ref}"
)


class SourceError(AwError):
    """Raised when a source cannot be resolved or is unsafe."""


@dataclass(frozen=True)
class Source:
    """Resolved identity of an AW distribution."""

    repository: str
    version: str
    commit: str
    package_root: Path

    def as_dict(self) -> dict:
        return {
            "repository": self.repository,
            "version": self.version,
            "commit": self.commit,
        }


def _local_git_head(package_root: Path) -> str | None:
    """Return the 40-char HEAD SHA of a local git checkout, if any."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(package_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    sha = proc.stdout.strip()
    return sha if FULL_SHA_RE.fullmatch(sha) else None


def package_manifest(package_root: Path) -> dict:
    """Load and validate the package's distribution manifest."""
    manifest_path = package_root / "distribution" / "manifest.json"
    if not manifest_path.is_file():
        raise SourceError(f"package missing distribution/manifest.json at {package_root}")
    return load_manifest(manifest_path)


def read_package_file(package_root: Path, relative: str) -> bytes:
    """Read a file directly from a package root with path-safety checks."""
    target = safe_join(package_root, relative)
    if not target.is_file():
        raise SourceError(f"package file missing: {relative}")
    return target.read_bytes()


def resolve_local(package_root: Path, commit: str | None = None) -> Source:
    """Resolve a local package directory into a Source.

    version/repository come from the validated manifest; commit comes from
    the explicit argument (must be a full 40-char hex SHA) or the
    directory's git HEAD (never from the manifest itself).
    """
    package_root = package_root.resolve()
    manifest = package_manifest(package_root)
    version = manifest["distribution_version"]
    repository = manifest.get("source_repository", DEFAULT_REPOSITORY)
    if commit is None:
        commit = _local_git_head(package_root)
    if commit is None:
        raise SourceError(f"cannot resolve commit for local package {package_root}; pass --commit")
    if not FULL_SHA_RE.fullmatch(commit):
        raise SourceError(f"commit must be a full 40-char hex SHA: {commit!r}")
    return Source(repository=repository, version=version, commit=commit, package_root=package_root)


# ---- remote download ------------------------------------------------------


def _download_archive(url: str, cache_path: Path, timeout: int = 30) -> Path:
    """Download a source archive to the cache (atomic write); returns path."""
    if cache_path.exists():
        return cache_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        data = resp.read()
    fd, tmp = tempfile.mkstemp(dir=str(cache_path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, str(cache_path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return cache_path


def _extract_archive(archive: Path, destination: Path) -> None:
    """Safely extract a tar.gz or zip archive into destination.

    Rejects path traversal and absolute member paths; every member must
    stay inside destination.
    """
    destination.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip" or str(archive).endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                name = member.filename
                target = _safe_member_path(destination, name)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())
    else:
        with tarfile.open(archive, "r:*") as tf:
            for member in tf.getmembers():
                target = _safe_member_path(destination, member.name)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    extracted = tf.extractfile(member)
                    if extracted is None:
                        raise SourceError(f"cannot extract archive member: {member.name}")
                    with open(target, "wb") as fh:
                        fh.write(extracted.read())
                elif member.issym() or member.islnk():
                    raise SourceError(f"archive member must not be a link: {member.name}")


def _safe_member_path(destination: Path, name: str) -> Path:
    target = safe_join(destination, name)
    if target == destination:
        raise SourceError(f"unsafe archive member: {name}")
    return target


def _strip_top_level(package_root: Path) -> Path:
    """GitHub source archives contain a single top-level directory
    (<repo>-<ref>/); move its contents up to package_root."""
    children = [p for p in package_root.iterdir() if p.name != ".aw"]
    if len(children) == 1 and children[0].is_dir():
        inner = children[0]
        for item in list(inner.iterdir()):
            item.rename(package_root / item.name)
        inner.rmdir()
    return package_root


REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")
API_COMMIT_URL = "https://api.github.com/repos/{repository}/commits/{ref}"


def _validate_repository(repository: str) -> None:
    """Reject repository values that could break cache paths or the URL."""
    if not REPOSITORY_RE.fullmatch(repository):
        raise SourceError(f"repository must be owner/repo: {repository!r}")


def _resolve_tag_commit(repository: str, ref: str, timeout: int = 15) -> str:
    """Resolve a Release tag to its commit SHA via the GitHub API.

    Archive downloads contain no git metadata, so the commit identity for a
    tag ref must come from the API. Raises SourceError on failure (callers
    may fall back to an explicit --commit).
    """
    url = API_COMMIT_URL.format(repository=repository, ref=ref)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise SourceError(f"cannot resolve tag {ref} to a commit ({exc}); pass --commit")
    sha = (data or {}).get("sha")
    if not isinstance(sha, str) or not FULL_SHA_RE.fullmatch(sha):
        raise SourceError(f"cannot resolve tag {ref} to a commit; pass --commit")
    return sha


def resolve_remote(
    repository: str,
    ref: str,
    cache_dir: Path,
    *,
    commit: str | None = None,
    expected_version: str | None = None,
) -> Source:
    """Download, extract and resolve a remote Release tag or commit SHA.

    The returned Source.commit is the provided commit (immutable ref), or
    resolved via the GitHub API for a tag ref, or the explicit --commit.
    """
    _validate_repository(repository)
    if not FULL_SHA_RE.fullmatch(ref) and not TAG_RE.fullmatch(ref):
        raise SourceError(f"ref must be a Release tag (vX.Y.Z) or full commit SHA: {ref}")
    if commit is not None and not FULL_SHA_RE.fullmatch(commit):
        raise SourceError(f"commit must be a full 40-char hex SHA: {commit!r}")
    if commit is None and TAG_RE.fullmatch(ref):
        commit = _resolve_tag_commit(repository, ref)
    elif commit is None and FULL_SHA_RE.fullmatch(ref):
        commit = ref  # the ref itself is the immutable commit identity
    archive_url = ARCHIVE_URL.format(repository=repository, ref=ref)
    archive = _download_archive(archive_url, cache_dir / f"{repository.replace('/', '__')}@{ref}.tar.gz")
    extract_dir = Path(tempfile.mkdtemp(prefix="aw-src-"))
    try:
        _extract_archive(archive, extract_dir)
        package_root = _strip_top_level(extract_dir)
        manifest = package_manifest(package_root)
        version = manifest["distribution_version"]
        if expected_version is not None and version != expected_version:
            raise SourceError(f"manifest version mismatch: expected {expected_version}, got {version}")
        if commit is None:
            commit = _local_git_head(package_root)
        if commit is None:
            raise SourceError("cannot resolve commit for remote source; pass --commit")
        return Source(
            repository=manifest.get("source_repository", repository),
            version=version,
            commit=commit,
            package_root=package_root,
        )
    except BaseException:
        import shutil

        shutil.rmtree(extract_dir, ignore_errors=True)
        raise


def resolve_source(
    source_ref: str,
    cache_dir: Path | None = None,
    *,
    commit: str | None = None,
    expected_repository: str | None = None,
) -> Source:
    """Resolve a source reference to a Source.

    - existing local directory -> resolve_local
    - Release tag (vX.Y.Z) or full commit SHA -> resolve_remote
    """
    candidate = Path(source_ref)
    if candidate.is_dir():
        return resolve_local(candidate, commit=commit)
    if cache_dir is None:
        raise SourceError(f"remote source requires a cache dir: {source_ref}")
    repository = expected_repository or DEFAULT_REPOSITORY
    return resolve_remote(repository, source_ref, cache_dir, commit=commit)
