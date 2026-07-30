import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


class CheckEntryTests(unittest.TestCase):
    def test_check_fails_outside_git_worktree(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(REPOSITORY_ROOT / "scripts/check.sh", scripts / "check.sh")

            result = subprocess.run(
                ["bash", "scripts/check.sh"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn(
                "repository validation must run inside a Git worktree",
                result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
