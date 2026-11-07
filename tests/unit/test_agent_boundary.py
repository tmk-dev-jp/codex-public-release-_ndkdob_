"""Boundary generator tests use disposable files and never start a model."""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import set_agent_boundary as boundary


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "project"
        self.root.mkdir()
        self.binary = self.base / "codex"
        self.binary.write_text("fixture", encoding="utf-8")
        self.config = self.root / ".codex" / "config.toml"
        self.config.parent.mkdir()
        self.original = b'# preserve comments\r\n[features]\r\nhooks = true\r\n'
        self.config.write_bytes(self.original)

    def profile(self, **kwargs):
        return boundary.make_profile(
            self.root, kwargs.get("reads", []), kwargs.get("writes", ["."]),
            kwargs.get("denies", []), self.binary,
        )

    def test_write_scope_preserves_control_directories(self):
        profile = self.profile()
        fs = profile["filesystem"]
        self.assertEqual(fs[":root"], "deny")
        self.assertEqual(fs[str(self.root)], "write")
        self.assertEqual(fs[str(self.binary)], "read")
        for name in boundary.PROTECTED:
            self.assertEqual(fs[str(self.root / name)], "read")
        self.assertNotIn(":workspace_roots", fs)
        self.assertNotIn(":slash_tmp", fs)
        self.assertFalse(profile["network"]["enabled"])
        parsed = boundary.parse_toml(boundary.render(self.original, profile))
        self.assertEqual(parsed["approval_policy"], "never")
        self.assertEqual(parsed["default_permissions"], boundary.PROFILE)
        self.assertEqual(parsed["permissions"][boundary.PROFILE], profile)

    def test_narrow_read_scope_does_not_grant_project_parent(self):
        notes = self.root / "notes"
        notes.mkdir()
        fs = self.profile(reads=["notes"], writes=[])["filesystem"]
        self.assertEqual(fs[str(notes)], "read")
        self.assertNotIn(str(self.root), fs)
        self.assertNotIn(str(self.base), fs)

    def test_explicit_deny_is_preserved(self):
        fs = self.profile(denies=[".codex"])["filesystem"]
        self.assertEqual(fs[str(self.root / ".codex")], "deny")

    def test_invalid_or_conflicting_rules(self):
        cases = [
            {"reads": [], "writes": []},
            {"reads": ["."], "writes": ["."]},
            {"writes": [".codex"]},
            {"writes": ["missing"]},
            {"writes": ["*.py"]},
            {"writes": [str(Path(self.root.anchor))]},
            {"writes": ["."], "denies": [str(self.base)]},
            {"writes": ["."], "denies": [str(self.binary)]},
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises((ValueError, OSError)):
                self.profile(**args)

    def test_symlink_scope_and_config_are_rejected(self):
        link = self.root / "alias"
        try:
            link.symlink_to(self.base, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):
            self.profile(reads=["alias"], writes=[])
        self.config.unlink()
        self.config.symlink_to(self.binary)
        with self.assertRaises(ValueError):
            boundary.configure(self.root, self.profile(), True)
        self.assertEqual(self.binary.read_text(), "fixture")

    def test_plan_does_not_mutate_files(self):
        before = set(self.config.parent.iterdir())
        result = boundary.configure(self.root, self.profile(), False)
        self.assertEqual(result["state"], "planned")
        self.assertEqual(set(self.config.parent.iterdir()), before)
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_apply_is_idempotent_and_restore_is_byte_exact(self):
        profile = self.profile()
        self.assertEqual(boundary.configure(self.root, profile, True)["state"], "configured")
        installed = self.config.read_bytes()
        self.assertEqual(boundary.configure(self.root, profile, True)["state"], "unchanged")
        self.assertEqual(self.config.read_bytes(), installed)
        self.assertEqual(boundary.status(self.root)["state"], "configured")
        boundary.restore(self.root)
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.config.parent / boundary.BACKUP).exists())

    def test_updating_boundary_keeps_original_backup(self):
        boundary.configure(self.root, self.profile(), True)
        boundary.configure(self.root, self.profile(reads=["."], writes=[]), True)
        boundary.restore(self.root)
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_restore_refuses_subsequent_user_edits(self):
        boundary.configure(self.root, self.profile(), True)
        modified = self.config.read_bytes() + b"\n# user change\n"
        self.config.write_bytes(modified)
        with self.assertRaisesRegex(ValueError, "config changed"):
            boundary.restore(self.root)
        self.assertEqual(self.config.read_bytes(), modified)

    def test_backup_corruption_is_detected(self):
        boundary.configure(self.root, self.profile(), True)
        backup = self.config.parent / boundary.BACKUP
        record = json.loads(backup.read_text())
        record["original"] = "# changed"
        backup.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "backup content"):
            boundary.restore(self.root)

    def test_invalid_backup_shape_is_rejected(self):
        backup = self.config.parent / boundary.BACKUP
        backup.write_text("[]")
        with self.assertRaisesRegex(ValueError, "JSON object"):
            boundary.status(self.root)

    def test_existing_policy_is_not_silently_overwritten(self):
        for key in ("default_permissions", "approval_policy", "sandbox_mode"):
            with self.subTest(key=key):
                self.config.write_text(f'{key} = "existing"\n')
                with self.assertRaisesRegex(ValueError, "manual review"):
                    boundary.configure(self.root, self.profile(), True)
                self.assertFalse((self.config.parent / boundary.BACKUP).exists())

    def test_missing_original_config_is_restored_to_absence(self):
        self.config.unlink()
        boundary.configure(self.root, self.profile(), True)
        boundary.restore(self.root)
        self.assertFalse(self.config.exists())

    def test_interrupted_update_can_be_restored(self):
        boundary.configure(self.root, self.profile(), True)
        write = boundary.atomic_write

        def fail_config(path, data):
            if path == self.config:
                raise OSError("interrupted")
            write(path, data)

        with mock.patch.object(boundary, "atomic_write", side_effect=fail_config):
            with self.assertRaises(OSError):
                boundary.configure(self.root, self.profile(reads=["."], writes=[]), True)
        self.assertEqual(boundary.status(self.root)["state"], "pending")
        boundary.restore(self.root)
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_cli_preserves_spaces_in_boundary_paths(self):
        folder = self.root / "two  spaces"
        folder.mkdir()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch.object(
            boundary, "executable", return_value=self.binary
        ):
            code = boundary.main(["plan", "--root", str(self.root), "--read", "two  spaces"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue().split(" ", 2)[2])
        self.assertEqual(payload["permissions"]["filesystem"][str(folder)], "read")

    def test_cli_error_is_one_line(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            result = boundary.main(["restore", "--read", ".", "--root", str(self.root)])
        self.assertEqual(result, 1)
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        self.assertTrue(output.getvalue().startswith("ERROR agent-boundary:"))

    def test_verify_does_not_accept_process_failure_or_missing_marker(self):
        boundary.configure(self.root, self.profile(), True)
        visible = self.root / "visible.txt"
        visible.write_text("test")
        for result in (subprocess.CompletedProcess([], 1, "boundary-ok", "failure"),
                       subprocess.CompletedProcess([], 0, "", "")):
            with self.subTest(result=result), mock.patch.object(
                boundary.subprocess, "run", return_value=result
            ), self.assertRaises(ValueError):
                boundary.verify(self.root, self.binary, str(visible), str(self.base))
        self.assertFalse(list(self.base.glob(".agent-boundary-probe-*")))


@unittest.skipUnless(sys.platform == "linux" and shutil.which("codex"),
                     "Linux/WSL Codex sandbox required")
class SandboxTests(unittest.TestCase):
    def test_installed_profile_verification_and_restore(self):
        with tempfile.TemporaryDirectory(prefix=".boundary-workflow-", dir=Path.cwd()) as tmp:
            parent = Path(tmp).resolve()
            root = parent / "project"
            root.mkdir()
            (root / "visible.txt").write_text("test")
            binary = boundary.executable("codex")
            boundary.configure(root, boundary.make_profile(root, [], ["."], [], binary), True)
            try:
                result = boundary.verify(root, binary, "visible.txt", str(parent))
                self.assertEqual(result["state"], "probe_passed")
            finally:
                boundary.restore(root)
            self.assertFalse((root / ".codex" / "config.toml").exists())

    def test_actual_sandbox_blocks_outside_and_symlink_reads_and_control_writes(self):
        # Keep fixtures outside /tmp to avoid inherited temporary-directory policies.
        with tempfile.TemporaryDirectory(prefix=".boundary-test-", dir=Path.cwd()) as tmp:
            base = Path(tmp).resolve()
            root = base / "allowed"
            root.mkdir()
            (root / ".codex").mkdir()
            (root / ".codex" / "config.toml").write_text("# fixture")
            (root / "visible.txt").write_text("visible")
            blocked = base / "blocked.txt"
            blocked.write_text("not-secret")
            (root / "escape").symlink_to(blocked)
            binary = boundary.executable("codex")
            profile = boundary.make_profile(root, [], ["."], [], binary)
            fs = ", ".join(f"{json.dumps(k)}={json.dumps(v)}"
                           for k, v in profile["filesystem"].items())
            override = f"permissions.{boundary.PROFILE}={{filesystem={{{fs}}},network={{enabled=false}}}}"
            probe = """
from pathlib import Path
import sys
root, blocked = map(Path, sys.argv[1:])
assert (root / "visible.txt").read_text() == "visible"
(root / "writable.txt").write_text("created")
for path in (blocked, root / "escape"):
    try:
        path.read_bytes()
    except (PermissionError, FileNotFoundError):
        pass
    else:
        raise SystemExit("outside read allowed")
try:
    (root / ".codex" / "config.toml").write_text("bad")
except (PermissionError, OSError):
    pass
else:
    raise SystemExit("configuration write allowed")
sys.stdout.write("boundary-ok\\n")
"""
            result = subprocess.run(
                [str(binary), "sandbox", "-P", boundary.PROFILE,
                 "--include-managed-config", "-c", override, "-C", str(root),
                 "--", sys.executable, "-c", probe, str(root), str(blocked)],
                capture_output=True, text=True, timeout=30, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "boundary-ok")
            self.assertEqual((root / ".codex" / "config.toml").read_text(), "# fixture")
            self.assertEqual((root / "writable.txt").read_text(), "created")


if __name__ == "__main__":
    unittest.main()
