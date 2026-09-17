"""file_scan criteria(owner_ne/mode_not_allowed) 확장 테스트.

U-17, U-67의 소유자/권한 결합 조건과 기존 문자열 criteria regression을 검증한다.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from engine import collector, runner
from engine.model import ResultStatus

# 비root 계정 UID (passwd에 "nobody"로 등록됨). 소유자 비교 테스트에 사용.
NON_ROOT_UID = 65534

MODE_644 = {"owner": "rw", "group": "r", "other": "r"}


class TestFileScanCriteriaPredicate(unittest.TestCase):
    """collector 수준에서 predicate criteria를 검증한다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _mkfile(self, relpath: str, mode: int, uid: int | None = None) -> str:
        p = self.root / relpath.lstrip("/")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        p.chmod(mode)
        if uid is not None:
            os.chown(p, uid, uid)
        return relpath

    def _scan(self, criteria, root_path: str = "/s"):
        outcome = collector.collect(
            {"kind": "scan", "root": root_path, "recursive": False, "criteria": criteria},
            root=str(self.root),
        )
        return outcome.value or []

    # --- owner_ne ---

    def test_owner_ne_root_not_match(self):
        self._mkfile("/s/root_owned", 0o644, uid=0)
        self.assertEqual(self._scan({"owner_ne": "root"}), [])

    def test_owner_ne_nonroot_match(self):
        self._mkfile("/s/user_owned", 0o644, uid=NON_ROOT_UID)
        paths = self._scan({"owner_ne": "root"})
        self.assertEqual(len(paths), 1)
        self.assertTrue(any(p.endswith("user_owned") for p in paths))

    # --- mode_not_allowed ---

    def test_mode_not_allowed_0644_not_match(self):
        self._mkfile("/s/f0644", 0o644)
        self.assertEqual(self._scan({"mode_not_allowed": MODE_644}), [])

    def test_mode_not_allowed_0664_match(self):
        self._mkfile("/s/f0664", 0o664)
        self.assertEqual(len(self._scan({"mode_not_allowed": MODE_644})), 1)

    def test_mode_not_allowed_0755_match(self):
        self._mkfile("/s/f0755", 0o755)
        self.assertEqual(len(self._scan({"mode_not_allowed": MODE_644})), 1)

    def test_mode_not_allowed_0677_match(self):
        self._mkfile("/s/f0677", 0o677)
        self.assertEqual(len(self._scan({"mode_not_allowed": MODE_644})), 1)

    # --- 복합 조건 (owner_ne + mode_not_allowed, OR) ---

    def _combined(self):
        return {"owner_ne": "root", "mode_not_allowed": MODE_644}

    def test_combined_root_0644_not_match(self):
        self._mkfile("/s/ok", 0o644, uid=0)
        self.assertEqual(self._scan(self._combined()), [])

    def test_combined_root_0664_match(self):
        self._mkfile("/s/gw", 0o664, uid=0)
        self.assertEqual(len(self._scan(self._combined())), 1)

    def test_combined_user_0644_match(self):
        self._mkfile("/s/uo", 0o644, uid=NON_ROOT_UID)
        self.assertEqual(len(self._scan(self._combined())), 1)

    def test_combined_user_0664_match(self):
        self._mkfile("/s/uo_gw", 0o664, uid=NON_ROOT_UID)
        self.assertEqual(len(self._scan(self._combined())), 1)

    # --- 기존 문자열 criteria regression ---

    def test_world_writable_string_unchanged(self):
        self._mkfile("/s/wr", 0o666)
        self._mkfile("/s/ro", 0o644)
        paths = self._scan("world_writable")
        self.assertTrue(any(p.endswith("wr") for p in paths))
        self.assertFalse(any(p.endswith("ro") for p in paths))


class TestRunU17U67(unittest.TestCase):
    """Check 수준에서 U-17/U-67의 PASS/FAIL을 검증한다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _mkfile(self, relpath: str, mode: int, uid: int | None = None):
        p = self.root / relpath.lstrip("/")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        p.chmod(mode)
        if uid is not None:
            os.chown(p, uid, uid)

    def _run(self, check_id):
        return runner.run(check_id, root=str(self.root))

    # --- U-17 (소유자 root + other 쓰기 없음) ---

    def test_u17_pass(self):
        self._mkfile("/etc/init.d/foo", 0o755, uid=0)
        self.assertEqual(self._run("CK-lnx-U17-001").status, ResultStatus.PASS)

    def test_u17_fail_owner(self):
        self._mkfile("/etc/init.d/foo", 0o755, uid=NON_ROOT_UID)
        self.assertEqual(self._run("CK-lnx-U17-001").status, ResultStatus.FAIL)

    def test_u17_fail_other_write(self):
        self._mkfile("/etc/init.d/foo", 0o757, uid=0)
        self.assertEqual(self._run("CK-lnx-U17-001").status, ResultStatus.FAIL)

    # --- U-67 (소유자 root + 권한 ≤ 644) ---

    def test_u67_pass(self):
        self._mkfile("/var/log/secure", 0o644, uid=0)
        self.assertEqual(self._run("CK-lnx-U67-001").status, ResultStatus.PASS)

    def test_u67_fail_group_write(self):
        self._mkfile("/var/log/secure", 0o664, uid=0)
        self.assertEqual(self._run("CK-lnx-U67-001").status, ResultStatus.FAIL)

    def test_u67_fail_execute(self):
        self._mkfile("/var/log/secure", 0o755, uid=0)
        self.assertEqual(self._run("CK-lnx-U67-001").status, ResultStatus.FAIL)

    def test_u67_fail_owner(self):
        self._mkfile("/var/log/secure", 0o644, uid=NON_ROOT_UID)
        self.assertEqual(self._run("CK-lnx-U67-001").status, ResultStatus.FAIL)


if __name__ == "__main__":
    unittest.main()
