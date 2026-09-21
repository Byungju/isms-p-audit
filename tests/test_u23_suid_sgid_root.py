"""U-23 root 소유 SUID/SGID(all/any) 지원 테스트.

- criteria의 `all`/`any` 2단 AND/OR 결합 평가를 검증한다.
- validator의 all/any 구조 검증과 flat predicate 검증 regression을 확인한다.
"""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from engine import collector
from tools import validate_checks as v

NON_ROOT_UID = 65534  # nobody

U23_CRITERIA = {
    "all": [
        {"owner_eq": "root"},
        {"any": [{"suid": True}, {"sgid": True}]},
    ],
}


class TestU23Collector(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _mkfile(self, relpath: str, mode: int = 0o644, uid: int = 0, gid: int = 0):
        p = self.root / relpath.lstrip("/")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        os.chown(p, uid, gid)
        p.chmod(mode)
        return p

    def _mkdir(self, relpath: str, mode: int = 0o755, uid: int = 0, gid: int = 0):
        p = self.root / relpath.lstrip("/")
        p.mkdir(parents=True, exist_ok=True)
        os.chown(p, uid, gid)
        p.chmod(mode)
        return p

    def _scan(self, root_path="/s", criteria=None, types=None):
        target = {"kind": "scan", "root": root_path, "recursive": False, "criteria": criteria or U23_CRITERIA}
        if types is not None:
            target["types"] = types
        outcome = collector.collect(target, root=str(self.root))
        return outcome.value or []

    def test_root_suid_match(self):
        self._mkfile("/s/a", mode=0o4755, uid=0)
        self.assertEqual(len(self._scan(types=["file"])), 1)

    def test_root_sgid_match(self):
        self._mkfile("/s/a", mode=0o2755, uid=0)
        self.assertEqual(len(self._scan(types=["file"])), 1)

    def test_root_suid_sgid_single_match(self):
        self._mkfile("/s/a", mode=0o6755, uid=0)
        self.assertEqual(len(self._scan(types=["file"])), 1)

    def test_root_plain_file_no_match(self):
        self._mkfile("/s/a", mode=0o755, uid=0)
        self.assertEqual(self._scan(types=["file"]), [])

    def test_nonroot_suid_no_match(self):
        # owner_eq: root AND 조건이 비root 소유를 걸러낸다.
        self._mkfile("/s/a", mode=0o4755, uid=NON_ROOT_UID)
        self.assertEqual(self._scan(types=["file"]), [])

    def test_directory_excluded_with_types_file(self):
        self._mkdir("/s/adir", mode=0o4755)
        self._mkfile("/s/afile", mode=0o4755)
        paths = self._scan(types=["file"])
        self.assertEqual(len(paths), 1)
        self.assertTrue(any(p.endswith("afile") for p in paths))


class TestU23Validator(unittest.TestCase):
    def _errs(self, criteria):
        v.errors.clear()
        v.validate_scan_criteria(criteria, "t")
        return list(v.errors)

    def test_valid_all_any(self):
        self.assertEqual(self._errs(U23_CRITERIA), [])

    def test_all_with_extra_key(self):
        criteria = {"all": [{"owner_eq": "root"}], "owner_ne": "root"}
        errs = self._errs(criteria)
        self.assertTrue(any("all은 다른 criteria 키와 함께" in e for e in errs))

    def test_any_inside_all_nested(self):
        criteria = {"all": [{"any": [{"all": [{"suid": True}]}]}]}
        errs = self._errs(criteria)
        self.assertTrue(any("3단 이상 중첩" in e for e in errs))

    def test_top_level_any_rejected(self):
        criteria = {"any": [{"suid": True}]}
        errs = self._errs(criteria)
        self.assertTrue(any("any는 all 내부에서만" in e for e in errs))

    def test_owner_eq_non_string(self):
        errs = self._errs({"owner_eq": 123})
        self.assertTrue(any("owner_eq는 문자열" in e for e in errs))

    def test_suid_non_bool(self):
        errs = self._errs({"suid": "yes"})
        self.assertTrue(any("suid는 bool" in e for e in errs))

    def test_flat_dict_regression(self):
        self.assertEqual(self._errs({"owner_ne": "root"}), [])
        self.assertEqual(self._errs({"mode_not_allowed": {"owner": "rw", "group": "r", "other": "r"}}), [])
        self.assertEqual(self._errs({"nouser": True, "nogroup": True}), [])
        self.assertEqual(self._errs({"owner_eq": "root", "suid": True}), [])


if __name__ == "__main__":
    unittest.main()
