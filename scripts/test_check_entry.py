import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def find_bash() -> str:
    """Locate a real bash; on Windows prefer Git Bash over the WSL stub."""
    override = os.environ.get("AW_TEST_BASH")
    if override:
        return override
    found = shutil.which("bash")
    if found and os.name == "nt":
        lower = found.lower().replace("\\", "/")
        if "system32/bash.exe" in lower or "windowsapps/bash.exe" in lower:
            for candidate in (
                r"C:\Program Files\Git\bin\bash.exe",
                r"C:\Program Files\Git\usr\bin\bash.exe",
            ):
                if os.path.exists(candidate):
                    return candidate
    return found or "bash"


BASH = find_bash()


class CheckEntryTests(unittest.TestCase):
    def test_check_fails_outside_git_worktree(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copy2(REPOSITORY_ROOT / "scripts/check.sh", scripts / "check.sh")

            result = subprocess.run(
                [BASH, "scripts/check.sh"],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn(
                "repository validation must run inside a Git worktree",
                result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
