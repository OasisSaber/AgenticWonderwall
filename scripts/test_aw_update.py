"""Unit tests for scripts/aw-update.sh (offline, using --source fake upstream).

The script resolves its repository root from its own location, so tests copy it
into a temporary fake adoption project and run it there. All tests use
--source + --ref so no network access is required.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AW_UPDATE = REPO_ROOT / "scripts" / "aw-update.sh"


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


def posix(path: Path) -> str:
    """Convert a path to the POSIX form Git Bash understands."""
    return str(path).replace(os.sep, "/")

UPSTREAM_MANIFEST = """\
keep AGENTS.md
sync scripts/check.sh
sync scripts/new.sh
sync docs/
sync scripts/lib/*.py
"""

UPSTREAM_FILES = {
    "AGENTS.md": "upstream agents v1\n",
    "scripts/check.sh": "new check\n",
    "scripts/new.sh": "new file\n",
    "scripts/lib/one.py": "one\n",
    "scripts/lib/two.py": "two\n",
    "scripts/lib/three.py": "three\n",
    "docs/guide.md": "guide v1\n",
}


def write_lf(path: Path, content: str) -> None:
    """Write text with LF line endings regardless of platform."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def run_script(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, "scripts/aw-update.sh", *args],
        cwd=str(project),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


class AwUpdateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.upstream = root / "upstream"
        self.project = root / "project"
        (self.project / "scripts" / "lib").mkdir(parents=True)
        (self.project / "docs").mkdir(parents=True)

        for path, content in UPSTREAM_FILES.items():
            full = self.upstream / path
            full.parent.mkdir(parents=True, exist_ok=True)
            write_lf(full, content)
        write_lf(self.upstream / "scripts" / "aw-update-manifest.txt", UPSTREAM_MANIFEST)

        shutil.copy(AW_UPDATE, self.project / "scripts" / "aw-update.sh")
        write_lf(self.project / "AGENTS.md", "custom agents\n")
        write_lf(self.project / "scripts" / "check.sh", "old check\n")
        write_lf(self.project / "scripts" / "lib" / "one.py", "one\n")
        write_lf(self.project / "docs" / "guide.md", "guide old\n")

    def tearDown(self):
        self._tmp.cleanup()

    def write_version(self, version: str) -> None:
        write_lf(self.project / ".aw-update" / "VERSION", version)

    def manifest_arg(self) -> tuple[str, str]:
        manifest = self.upstream / "scripts" / "aw-update-manifest.txt"
        return "--manifest", posix(manifest)

    # ---- check ----

    def test_check_no_version_recorded(self):
        result = run_script(self.project, "check", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("未记录本地版本", result.stdout)

    def test_check_up_to_date(self):
        self.write_version("v1.1.0")
        result = run_script(self.project, "check", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", *self.manifest_arg())
        self.assertEqual(result.returncode, 0)
        self.assertIn("已是最新", result.stdout)

    def test_check_update_available(self):
        self.write_version("v1.0.0")
        result = run_script(self.project, "check", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("可更新", result.stdout)

    def test_check_source_requires_ref(self):
        result = run_script(self.project, "check", "--source", posix(self.upstream))
        self.assertEqual(result.returncode, 3)
        self.assertIn("--source 模式必须同时指定 --ref", result.stderr)

    # ---- diff ----

    def test_diff_lists_new_changed_keep(self):
        result = run_script(self.project, "diff", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("[新增] sync scripts/new.sh", result.stdout)
        self.assertIn("[变更] sync scripts/check.sh", result.stdout)
        self.assertIn("[差异] keep AGENTS.md", result.stdout)
        self.assertIn("[变更] sync docs/guide.md", result.stdout)

    def test_diff_wildcard_and_directory_entries(self):
        result = run_script(self.project, "diff", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("[新增] sync scripts/lib/three.py", result.stdout)
        # 内容相同的文件不出现
        self.assertNotIn("lib/one.py", result.stdout)

    def test_diff_no_difference(self):
        self.write_version("v1.1.0")
        for path, content in UPSTREAM_FILES.items():
            full = self.project / path
            write_lf(full, content)
        write_lf(self.project / "AGENTS.md", "upstream agents v1\n")
        result = run_script(self.project, "diff", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", *self.manifest_arg())
        self.assertEqual(result.returncode, 0)
        self.assertIn("无差异", result.stdout)

    # ---- apply ----

    def test_apply_dry_run_writes_nothing(self):
        result = run_script(self.project, "apply", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", "--dry-run", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)  # keep 差异需要人工处理
        self.assertIn("[dry-run] 将更新: scripts/check.sh", result.stdout)
        self.assertEqual(
            (self.project / "scripts" / "check.sh").read_text(encoding="utf-8"),
            "old check\n",
        )
        self.assertFalse((self.project / "scripts" / "new.sh").exists())
        self.assertFalse((self.project / ".aw-update" / "VERSION").exists())

    def test_apply_yes_updates_sync_keeps_keep_and_records_version(self):
        result = run_script(self.project, "apply", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", "--yes", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)  # keep 差异需要人工处理
        self.assertEqual(
            (self.project / "scripts" / "check.sh").read_text(encoding="utf-8"),
            "new check\n",
        )
        self.assertTrue((self.project / "scripts" / "new.sh").exists())
        self.assertEqual(
            (self.project / "AGENTS.md").read_text(encoding="utf-8"),
            "custom agents\n",
        )
        self.assertEqual(
            (self.project / ".aw-update" / "VERSION").read_text(encoding="utf-8").strip(),
            "v1.1.0",
        )

    def test_apply_removed_file_is_not_deleted(self):
        # 上游移除 scripts/check.sh：本地保留并提示
        (self.upstream / "scripts" / "check.sh").unlink()
        result = run_script(self.project, "apply", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", "--yes", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("不删除本地文件", result.stdout)
        self.assertTrue((self.project / "scripts" / "check.sh").exists())

    def test_apply_keep_downgrade_is_protected(self):
        # 本地 manifest 将 scripts/check.sh 标为 keep，上游为 sync：
        # 即使 apply --yes 也不覆盖本地定制
        write_lf(self.project / "scripts" / "aw-update-manifest.txt",
                 "keep scripts/check.sh\n")
        result = run_script(self.project, "apply", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", "--yes", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("不自动覆盖", result.stdout)
        self.assertEqual(
            (self.project / "scripts" / "check.sh").read_text(encoding="utf-8"),
            "old check\n",
        )

    def test_apply_cp_failure_keeps_version(self):
        # 把 docs/ 目录替换为同名文件，使 docs/guide.md 的 mkdir/cp 失败：
        # VERSION 必须保持原值，不得推进到目标 ref
        shutil.rmtree(self.project / "docs")
        write_lf(self.project / "docs", "")
        write_lf(self.project / ".aw-update" / "VERSION", "v1.0.0")
        result = run_script(self.project, "apply", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", "--yes", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("无法更新", result.stderr)
        self.assertIn("版本记录未推进", result.stdout)
        self.assertEqual(
            (self.project / ".aw-update" / "VERSION").read_text(encoding="utf-8").strip(),
            "v1.0.0",
        )

    def test_apply_rejects_unsafe_manifest_paths(self):
        # 恶意/被攻陷上游 manifest 含 ../ 越界条目：apply 拒绝且不越界写入
        write_lf(self.upstream / "scripts" / "aw-update-manifest.txt",
                 "keep AGENTS.md\nsync ../evil.sh\nsync scripts/check.sh\n")
        result = run_script(self.project, "apply", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", "--yes", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("拒绝含 .. 组件的条目", result.stderr)
        self.assertFalse((self.upstream.parent / "evil.sh").exists())
        # 安全条目仍正常更新
        self.assertEqual(
            (self.project / "scripts" / "check.sh").read_text(encoding="utf-8"),
            "new check\n",
        )

    def test_apply_rejects_unsafe_ref(self):
        # --ref 含路径分隔/.. 会被拒绝（防拼入缓存路径后 rm -rf 越界）
        result = run_script(self.project, "apply", "--source", posix(self.upstream),
                            "--ref", "../../evil", "--yes", *self.manifest_arg())
        self.assertEqual(result.returncode, 3)
        self.assertIn("非法的 ref", result.stderr)

    def test_apply_rejects_symlink_target(self):
        # 目标文件是 symlink（指向仓库外）：apply --yes 拒绝覆盖
        outside = self.project.parent / "outside.txt"
        write_lf(outside, "outside\n")
        link_path = self.project / "scripts" / "lib" / "two.py"
        try:
            link_path.symlink_to(outside)
        except OSError:
            self.skipTest("symlink not supported in this environment")
        result = run_script(self.project, "apply", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", "--yes", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("拒绝覆盖符号链接目标", result.stderr)
        self.assertTrue(link_path.is_symlink())
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside\n")

    def test_apply_rejects_dangling_symlink_ancestor(self):
        # 中间组件是 dangling symlink（指向不存在的外部目录）：
        # 拒绝，防止 mkdir/cp 跟随写穿到外部
        outside_dir = self.project.parent / "outside_dir"
        link_dir = self.project / "scripts" / "lib"
        shutil.rmtree(link_dir)
        try:
            link_dir.symlink_to(outside_dir, target_is_directory=True)
        except OSError:
            self.skipTest("symlink not supported in this environment")
        result = run_script(self.project, "apply", "--source", posix(self.upstream),
                            "--ref", "v1.1.0", "--yes", *self.manifest_arg())
        self.assertEqual(result.returncode, 1)
        self.assertIn("拒绝越界目标路径", result.stderr)
        self.assertFalse((outside_dir / "two.py").exists())

    # ---- usage / errors ----

    def test_unknown_command(self):
        result = run_script(self.project, "frobnicate")
        self.assertEqual(result.returncode, 3)

    def test_help(self):
        result = run_script(self.project, "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("check", result.stdout)
        self.assertIn("apply", result.stdout)


if __name__ == "__main__":
    unittest.main()
