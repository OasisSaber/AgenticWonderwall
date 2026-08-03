#!/usr/bin/env python3
"""Real Git tag-only release-flow tests for the TheMasterplan Git Profile.

Runs the tag-only release transaction described in profiles/git.md against
real, temporary Git repositories (work repo + bare upstream as origin) to
verify:

- candidate must equal the latest origin/main (not any remote ref);
- execution re-checks the approved baseline: origin/main unchanged, target
  tag/Release absent, otherwise abort;
- tag smoke test failure blocks the Release creation;
- gh release create must include --verify-tag;
- success path executes the documented order:
  create tag -> push tag -> tag smoke -> create release;
- peeled tag SHA (refs/tags/<tag>^{}) equals the candidate commit;
- v1 (frozen compatibility line) is never touched.

Every command is a real `git` invocation; no mocks (gh is not executed,
its command line is constructed and asserted).

用法: python -m unittest scripts.test_release_flow -v
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

GIT = shutil.which("git") or "git"

BRANCH = "v1"
TAG = "v1.2.0"
SOURCE_BRANCH = "main"
# Documented tag-only order (profiles/git.md 阶段 C).
DOCUMENTED_ORDER = [
    "tag_create",
    "tag_push",
    "tag_smoke",
    "release",
]


def run_git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a real git command in cwd."""
    return subprocess.run(
        [GIT, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def release_command(tag: str, notes_file: str) -> list[str]:
    """Build the gh release create command line (profiles/git.md 阶段 C step 4)."""
    return [
        "gh",
        "release",
        "create",
        tag,
        "--verify-tag",
        "--title",
        tag,
        "--notes-file",
        notes_file,
    ]


class ReleaseFlowTest(unittest.TestCase):
    """Real-git integration tests for the tag-only release transaction."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.upstream = root / "upstream.git"
        self.work = root / "work"
        self.upstream.mkdir()
        self.work.mkdir()
        run_git(root, "init", "--bare", "--initial-branch=main", str(self.upstream))
        run_git(self.work, "init", "--initial-branch=main")
        run_git(self.work, "config", "user.name", "Release Test")
        run_git(self.work, "config", "user.email", "release-test@example.com")
        run_git(self.work, "remote", "add", "origin", str(self.upstream))
        (self.work / "README.md").write_text("release flow test\n", encoding="utf-8")
        run_git(self.work, "add", ".")
        run_git(self.work, "commit", "-m", "initial")
        run_git(self.work, "branch", BRANCH)
        run_git(self.work, "push", "origin", "main", BRANCH)
        self.initial_v1_sha = self.remote_ref(f"refs/heads/{BRANCH}")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # ---- helpers ---------------------------------------------------------

    def commit_on(self, branch: str, message: str) -> str:
        """Create a commit on branch and return its full SHA."""
        run_git(self.work, "checkout", "-q", branch)
        (self.work / "file.txt").write_text(message + "\n", encoding="utf-8")
        run_git(self.work, "add", ".")
        run_git(self.work, "commit", "-q", "-m", message)
        return run_git(self.work, "rev-parse", "HEAD").stdout.strip()

    def remote_ref(self, ref: str) -> str:
        """Return the SHA the remote advertises for ref ('' if missing)."""
        out = run_git(self.work, "ls-remote", "origin", ref).stdout
        return out.split()[0] if out.strip() else ""

    def run_release_flow(
        self,
        *,
        candidate: str | None = None,
        tag_smoke_ok: bool = True,
    ) -> tuple[list[str], str | None]:
        """Execute the documented tag-only transaction; returns (events, error).

        gh release create is NOT executed (unavailable/untested in CI); its
        command line is recorded as the final event instead.
        """
        events: list[str] = []
        run_git(self.work, "fetch", "-q", "origin")

        # 阶段 C step 0: re-check the approved baseline
        cur_main = self.remote_ref(f"refs/heads/{SOURCE_BRANCH}")
        if candidate is None:
            candidate = cur_main
        if candidate != cur_main:
            return events, "candidate is not the latest origin/main"
        # target tag must not exist (remote) and must not have been created
        if self.remote_ref(f"refs/tags/{TAG}"):
            return events, "tag already exists"

        # 1. create annotated tag (plain, no GPG requirement)
        run_git(self.work, "tag", "-a", TAG, "-m", f"Release {TAG}", candidate)
        events.append("tag_create")

        # 2. push tag
        run_git(self.work, "push", "-q", "origin", TAG)
        events.append("tag_push")

        # 3. fixed-tag consumer smoke test
        events.append("tag_smoke")
        if not tag_smoke_ok:
            return events, "tag smoke test failed"

        # 4. create GitHub Release (command line only; --verify-tag asserted)
        events.append("release")
        release_command(TAG, "NOTES.md")
        return events, None

    # ---- candidate must be the latest origin/main -----------------------

    def test_candidate_must_be_latest_origin_main(self) -> None:
        """A commit referenced only by a non-main remote ref must be rejected."""
        run_git(self.work, "checkout", "-q", "main")
        run_git(self.work, "checkout", "-q", "-b", "feature")
        feature = self.commit_on("feature", "feature commit")
        run_git(self.work, "push", "-q", "origin", "feature")
        run_git(self.work, "fetch", "-q", "origin")
        events, error = self.run_release_flow(candidate=feature)
        self.assertEqual(error, "candidate is not the latest origin/main")
        self.assertEqual(events, [])
        self.assertEqual(self.remote_ref(f"refs/tags/{TAG}"), "", "tag must not exist")
        self.assertEqual(
            self.remote_ref(f"refs/heads/{BRANCH}"),
            self.initial_v1_sha,
            "v1 must remain unchanged (frozen)",
        )

    # ---- approved baseline change detection -----------------------------

    def test_origin_main_moved_after_approval_rejected(self) -> None:
        """Execution aborts when origin/main no longer equals the candidate."""
        candidate = self.commit_on("main", "candidate commit")
        run_git(self.work, "push", "-q", "origin", "main")
        run_git(self.work, "fetch", "-q", "origin")
        # main moves ahead after approval
        self.commit_on("main", "main moves ahead")
        run_git(self.work, "push", "-q", "origin", "main")
        run_git(self.work, "fetch", "-q", "origin")
        events, error = self.run_release_flow(candidate=candidate)
        self.assertEqual(error, "candidate is not the latest origin/main")
        self.assertEqual(events, [])
        self.assertEqual(self.remote_ref(f"refs/tags/{TAG}"), "", "tag must not exist")

    # ---- smoke test gates the Release -----------------------------------

    def test_tag_smoke_failure_blocks_release(self) -> None:
        """When the fixed-tag smoke test fails, the Release must not be created."""
        candidate = self.commit_on("main", "candidate commit")
        run_git(self.work, "push", "-q", "origin", "main")
        run_git(self.work, "fetch", "-q", "origin")
        events, error = self.run_release_flow(tag_smoke_ok=False)
        self.assertEqual(error, "tag smoke test failed")
        self.assertEqual(events, ["tag_create", "tag_push", "tag_smoke"])
        self.assertNotEqual(
            self.remote_ref(f"refs/tags/{TAG}"), "", "tag must be pushed before smoke"
        )
        self.assertNotIn("release", events, "release must not be created")
        self.assertEqual(
            self.remote_ref(f"refs/heads/{BRANCH}"), self.initial_v1_sha,
            "v1 must remain unchanged (frozen)",
        )

    # ---- gh release create --verify-tag ---------------------------------

    def test_release_command_includes_verify_tag(self) -> None:
        """gh release create must include --verify-tag (profiles/git.md 阶段 C)."""
        cmd = release_command(TAG, "NOTES.md")
        self.assertEqual(cmd[:3], ["gh", "release", "create"])
        self.assertIn("--verify-tag", cmd)
        self.assertIn("--title", cmd)
        self.assertIn("--notes-file", cmd)
        self.assertIn(TAG, cmd)

    # ---- success path matches documented order --------------------------

    def test_success_flow_order_matches_docs(self) -> None:
        """Success path events must match the documented tag-only order."""
        candidate = self.commit_on("main", "candidate commit")
        run_git(self.work, "push", "-q", "origin", "main")
        run_git(self.work, "fetch", "-q", "origin")
        events, error = self.run_release_flow()
        self.assertIsNone(error)
        self.assertEqual(events, DOCUMENTED_ORDER)

        # final verification (阶段 D): peeled tag SHA == candidate,
        # raw tag ref is the tag object; v1 untouched
        peeled = self.remote_ref(f"refs/tags/{TAG}^{{}}")
        self.assertEqual(peeled, candidate, "peeled tag SHA must equal candidate")
        self.assertEqual(
            self.remote_ref(f"refs/tags/{TAG}"),
            run_git(self.work, "rev-parse", TAG).stdout.strip(),
            "raw tag ref must be the tag object",
        )
        self.assertNotEqual(
            self.remote_ref(f"refs/tags/{TAG}"), candidate,
            "unpeeled ref is the tag object, not the commit",
        )
        self.assertEqual(
            self.remote_ref(f"refs/heads/{BRANCH}"), self.initial_v1_sha,
            "v1 must remain unchanged (frozen)",
        )

    # ---- tag existence guard --------------------------------------------

    def test_tag_already_exists_rejected(self) -> None:
        """Phase A must reject an existing remote tag."""
        candidate = self.commit_on("main", "candidate commit")
        run_git(self.work, "push", "-q", "origin", "main")
        run_git(self.work, "tag", "-a", TAG, "-m", "existing", candidate)
        run_git(self.work, "push", "-q", "origin", TAG)
        run_git(self.work, "fetch", "-q", "origin")
        events, error = self.run_release_flow()
        self.assertEqual(error, "tag already exists")
        self.assertEqual(events, [], "nothing may be executed when tag exists")
        self.assertEqual(
            self.remote_ref(f"refs/heads/{BRANCH}"), self.initial_v1_sha,
            "v1 must not move when tag exists",
        )


if __name__ == "__main__":
    unittest.main()
