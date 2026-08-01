import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validate_consumer import main, require_tracked_file, validate_relative_path

SCRIPT = Path(__file__).resolve().parent / "validate_consumer.py"
TEMP = Path(os.environ.get("TEMP", tempfile.gettempdir()))


class ValidateRelativePathTests(unittest.TestCase):
    def test_valid_relative_path(self):
        path = validate_relative_path("scripts/check.sh")
        self.assertEqual(path.as_posix(), "scripts/check.sh")

    def test_single_segment(self):
        self.assertEqual(validate_relative_path("check.sh").as_posix(), "check.sh")

    def test_empty_path_fails(self):
        with self.assertRaises(SystemExit):
            validate_relative_path("")

    def test_absolute_path_fails(self):
        with self.assertRaises(SystemExit):
            validate_relative_path("/usr/bin/check.sh")

    def test_parent_segment_fails(self):
        with self.assertRaises(SystemExit):
            validate_relative_path("scripts/../check.sh")

    def test_backslash_fails(self):
        with self.assertRaises(SystemExit):
            validate_relative_path("scripts\\check.sh")


class ValidateConsumerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "AGENTS.md").write_text("# Consumer\n", encoding="utf-8")
        scripts = self.root / "scripts"
        scripts.mkdir()
        self.check = scripts / "check.sh"
        self.check.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        subprocess.run(
            ["git", "init", "-q", str(self.root)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "add", "AGENTS.md", "scripts/check.sh"],
            check=True,
            capture_output=True,
        )
        env = dict(os.environ, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.com",
                   GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.com")
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-q", "-m", "seed"],
            check=True,
            capture_output=True,
            env=env,
        )

    def tearDown(self):
        self.directory.cleanup()

    def run_validator(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_consumer(self):
        result = self.run_validator(str(self.root), "scripts/check.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid", result.stdout)

    def test_missing_root_directory_fails(self):
        result = self.run_validator(str(self.root / "missing"), "scripts/check.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)

    def test_missing_agents_md_fails(self):
        (self.root / "AGENTS.md").unlink()
        result = self.run_validator(str(self.root), "scripts/check.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENTS.md", result.stderr)

    def test_missing_check_file_fails(self):
        (self.root / "scripts/check.sh").unlink()
        result = self.run_validator(str(self.root), "scripts/check.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)

    def test_untracked_check_file_fails(self):
        untracked = self.root / "scripts/untracked.sh"
        untracked.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        result = self.run_validator(str(self.root), "scripts/untracked.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tracked by Git", result.stderr)

    def test_symlink_check_file_fails(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks not supported")
        target = self.root / "scripts/real.sh"
        target.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        link = self.root / "scripts/check.sh"
        link.unlink()
        os.symlink("real.sh", link)
        result = self.run_validator(str(self.root), "scripts/check.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)

    def test_absolute_path_argument_fails(self):
        result = self.run_validator(str(self.root), "/abs/check.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be relative", result.stderr)

    def test_backslash_path_argument_fails(self):
        result = self.run_validator(str(self.root), "scripts\\check.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("POSIX", result.stderr)

    def test_parent_path_argument_fails(self):
        result = self.run_validator(str(self.root), "scripts/../scripts/check.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("'..'", result.stderr)

    def test_empty_path_argument_fails(self):
        result = self.run_validator(str(self.root), "")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be empty", result.stderr)

    def test_wrong_argument_count_fails(self):
        result = self.run_validator(str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage", result.stderr)


class RequireTrackedFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.root.joinpath("AGENTS.md").write_text("# x\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self.root), "add", "AGENTS.md"],
            check=True,
            capture_output=True,
        )
        env = dict(os.environ, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.com",
                   GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.com")
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-q", "-m", "seed"],
            check=True,
            capture_output=True,
            env=env,
        )

    def tearDown(self):
        self.directory.cleanup()

    def test_directory_target_fails(self):
        with self.assertRaises(SystemExit):
            require_tracked_file(self.root, Path(".git"))

    def test_untracked_target_fails(self):
        self.root.joinpath("extra.txt").write_text("x\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            require_tracked_file(self.root, Path("extra.txt"))


if __name__ == "__main__":
    unittest.main()
