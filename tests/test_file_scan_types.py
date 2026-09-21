"""file_scan types(entry type filter) 테스트.

file/directory/device 타입 구분과 recursive/scan-root/pseudo-FS/symlink semantics를 검증한다.
"""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from engine import collector, runner
from engine.model import ResultStatus

NON_ROOT_UID = 65534
UNRESOLVED_UID = 40000


class TestFileScanTypes(unittest.TestCase):
    """collector 수준에서 types 필터와 traversal semantics를 검증한다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _p(self, relpath: str) -> Path:
        return self.root / relpath.lstrip("/")

    def _mkfile(self, relpath: str, mode: int, uid: int | None = None):
        p = self._p(relpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        p.chmod(mode)
        if uid is not None:
            os.chown(p, uid, uid)
        return p

    def _mkdir(self, relpath: str, mode: int, uid: int | None = None):
        p = self._p(relpath)
        p.mkdir(parents=True, exist_ok=True)
        p.chmod(mode)
        if uid is not None:
            os.chown(p, uid, uid)
        return p

    def _mkchar(self, relpath: str, mode: int = 0o666):
        p = self._p(relpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        os.mknod(str(p), stat.S_IFCHR | 0o600, os.makedev(1, 3))
        p.chmod(mode)
        return p

    def _scan(self, root_path, criteria, recursive, types=None):
        target = {"kind": "scan", "root": root_path, "recursive": recursive, "criteria": criteria}
        if types is not None:
            target["types"] = types
        outcome = collector.collect(target, root=str(self.root))
        return outcome.value or []

    # --- 기본 동작 / types ---

    def test_default_types_matches_file(self):
        self._mkfile("/s/a.txt", 0o666)
        paths = self._scan("/s", "world_writable", recursive=False)
        self.assertEqual(len(paths), 1)

    def test_default_types_skips_directory(self):
        self._mkdir("/s/adir", 0o777)
        paths = self._scan("/s", "world_writable", recursive=False)
        self.assertEqual(paths, [])

    def test_types_directory_matches(self):
        self._mkdir("/s/adir", 0o777)
        paths = self._scan("/s", "world_writable", recursive=False, types=["directory"])
        self.assertEqual(len(paths), 1)

    def test_types_file_skips_directory(self):
        self._mkdir("/s/adir", 0o777)
        self._mkfile("/s/a.txt", 0o666)
        paths = self._scan("/s", "world_writable", recursive=False, types=["file"])
        self.assertEqual(len(paths), 1)
        self.assertTrue(any(p.endswith("a.txt") for p in paths))

    def test_types_device_matches(self):
        self._mkchar("/s/chardev", 0o666)
        self._mkfile("/s/a.txt", 0o666)
        paths = self._scan("/s", "world_writable", recursive=False, types=["device"])
        self.assertEqual(len(paths), 1)
        self.assertTrue(any(p.endswith("chardev") for p in paths))

    # --- recursive ---

    def test_recursive_false_only_children(self):
        self._mkfile("/s/top.txt", 0o666)
        self._mkdir("/s/sub", 0o755)
        self._mkfile("/s/sub/deep.txt", 0o666)
        paths = self._scan("/s", "world_writable", recursive=False)
        self.assertEqual(len(paths), 1)
        self.assertTrue(any(p.endswith("top.txt") for p in paths))

    def test_recursive_true_descends(self):
        self._mkfile("/s/top.txt", 0o666)
        self._mkdir("/s/sub", 0o755)
        self._mkfile("/s/sub/deep.txt", 0o666)
        paths = self._scan("/s", "world_writable", recursive=True)
        self.assertEqual(len(paths), 2)

    def test_recursive_true_matches_directory(self):
        self._mkdir("/s/sub", 0o777)
        self._mkfile("/s/sub/deep.txt", 0o666)
        paths = self._scan("/s", "world_writable", recursive=True, types=["file", "directory"])
        self.assertEqual(len(paths), 2)

    # --- scan root 자체 ---

    def test_scan_root_not_included(self):
        self._mkdir("/home", 0o777)
        self._mkdir("/home/user1", 0o777)
        self._mkdir("/home/user2", 0o777)
        paths = self._scan("/home", "world_writable", recursive=False, types=["directory"])
        base = str(self._p("/home"))
        self.assertEqual(len(paths), 2)
        self.assertNotIn(base, paths)
        self.assertTrue(any(p.endswith("user1") for p in paths))
        self.assertTrue(any(p.endswith("user2") for p in paths))

    # --- symlink ---

    def test_symlink_skipped(self):
        self._mkfile("/s/real.txt", 0o666)
        self._p("/s/link.txt").symlink_to(self._p("/s/real.txt"))
        paths = self._scan("/s", "world_writable", recursive=False)
        self.assertEqual(len(paths), 1)
        self.assertTrue(any(p.endswith("real.txt") for p in paths))
        self.assertFalse(any(p.endswith("link.txt") for p in paths))

    # --- pseudo FS ---

    def test_pseudo_fs_excluded(self):
        self._mkfile("/sys/module/x/sections/.strtab", 0o666)
        self._mkfile("/tmp/a.txt", 0o666)
        paths = self._scan("/", "world_writable", recursive=True)
        self.assertTrue(any("/tmp/a.txt" in p for p in paths))
        self.assertFalse(any("/sys/" in p for p in paths))

    # --- 기존 criteria regression (predicate) ---

    def test_predicate_owner_ne_still_works(self):
        self._mkfile("/s/user.txt", 0o644, uid=NON_ROOT_UID)
        paths = self._scan("/s", {"owner_ne": "root"}, recursive=False)
        self.assertEqual(len(paths), 1)

    def test_predicate_mode_not_allowed_still_works(self):
        self._mkfile("/s/f0664", 0o664)
        paths = self._scan(
            "/s", {"mode_not_allowed": {"owner": "rw", "group": "r", "other": "r"}}, recursive=False
        )
        self.assertEqual(len(paths), 1)


class TestRunDirectoryChecks(unittest.TestCase):
    """Check 수준에서 U-15/U-31/U-33의 디렉터리 탐지를 검증한다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _p(self, relpath: str) -> Path:
        return self.root / relpath.lstrip("/")

    def _run(self, check_id):
        return runner.run(check_id, root=str(self.root))

    def test_u15_ownerless_directory_fail(self):
        d = self._p("/etc/somedir")
        d.mkdir(parents=True)
        os.chown(d, UNRESOLVED_UID, UNRESOLVED_UID)
        self.assertEqual(self._run("CK-lnx-U15-001").status, ResultStatus.FAIL)

    def test_u15_pass(self):
        self._p("/etc").mkdir(parents=True)
        self.assertEqual(self._run("CK-lnx-U15-001").status, ResultStatus.PASS)

    def test_u33_hidden_directory_detected(self):
        self._p("/etc/.hidden").mkdir(parents=True)
        (self._p("/etc/.hiddenfile")).write_text("x", encoding="utf-8")
        outcome = collector.collect(
            {"kind": "scan", "root": "/", "recursive": True, "types": ["file", "directory"], "criteria": "hidden"},
            root=str(self.root),
        )
        paths = outcome.value or []
        self.assertTrue(any(p.endswith(".hidden") for p in paths))
        self.assertTrue(any(p.endswith(".hiddenfile") for p in paths))

    def test_u25_directory_not_matched(self):
        self._mkdir("/s/wdir", 0o777)
        self._mkfile("/s/wfile", 0o666)
        outcome = collector.collect(
            {"kind": "scan", "root": "/s", "recursive": False, "criteria": "world_writable"},
            root=str(self.root),
        )
        paths = outcome.value or []
        self.assertTrue(any(p.endswith("wfile") for p in paths))
        self.assertFalse(any(p.endswith("wdir") for p in paths))

    def _mkdir(self, relpath, mode):
        p = self._p(relpath)
        p.mkdir(parents=True, exist_ok=True)
        p.chmod(mode)
        return p

    def _mkfile(self, relpath, mode):
        p = self._p(relpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        p.chmod(mode)
        return p


if __name__ == "__main__":
    unittest.main()
