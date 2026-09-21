"""U-15 nogroup/xdev 지원 테스트.

- nouser/nogroup predicate 키(OR 결합)와 문자열 enum ownerless의 하위 호환을 검증한다.
- xdev(파일시스템 경계)가 재귀를 제한하는 동작을 검증한다.
"""

from __future__ import annotations

import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from engine import collector

NO_UID = 40000
NO_GID = 40000


def _fake_stat_for(patch_path: Path, fake_dev: int):
    """patch_path의 st_dev만 fake_dev로 바꾼 os.stat 래퍼를 반환한다."""
    real_stat = os.stat

    def wrapper(p, *args, **kwargs):
        if str(p) == str(patch_path):
            r = real_stat(p, *args, **kwargs)
            return types.SimpleNamespace(
                st_mode=r.st_mode,
                st_ino=r.st_ino,
                st_dev=fake_dev,
                st_nlink=r.st_nlink,
                st_uid=r.st_uid,
                st_gid=r.st_gid,
                st_size=r.st_size,
            )
        return real_stat(p, *args, **kwargs)

    return wrapper


class TestU15NogroupXdev(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _p(self, relpath: str) -> Path:
        return self.root / relpath.lstrip("/")

    def _mkfile(self, relpath: str, mode: int = 0o644, uid: int = 0, gid: int = 0):
        p = self._p(relpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        p.chmod(mode)
        os.chown(p, uid, gid)
        return p

    def _mkdir(self, relpath: str, mode: int = 0o755, uid: int = 0, gid: int = 0):
        p = self._p(relpath)
        p.mkdir(parents=True, exist_ok=True)
        p.chmod(mode)
        os.chown(p, uid, gid)
        return p

    def _scan(self, root_path, criteria, recursive=False, types=None, xdev=False):
        target = {"kind": "scan", "root": root_path, "recursive": recursive, "criteria": criteria}
        if types is not None:
            target["types"] = types
        if xdev:
            target["xdev"] = True
        outcome = collector.collect(target, root=str(self.root))
        return outcome.value or []

    # --- nouser / nogroup / OR ---

    def test_nouser_single(self):
        self._mkfile("/s/f_nouser", uid=NO_UID, gid=0)
        self._mkfile("/s/f_ok", uid=0, gid=0)
        paths = self._scan("/s", {"nouser": True})
        self.assertEqual(len(paths), 1)
        self.assertTrue(any(p.endswith("f_nouser") for p in paths))

    def test_nouser_matches_ownerless_enum(self):
        # nouser predicate는 기존 ownerless 문자열과 동일 결과여야 한다(하위 호환).
        self._mkfile("/s/f_nouser", uid=NO_UID, gid=0)
        self._mkfile("/s/f_ok", uid=0, gid=0)
        pred = self._scan("/s", {"nouser": True})
        enum = self._scan("/s", "ownerless")
        self.assertEqual(len(pred), 1)
        self.assertEqual(pred, enum)

    def test_nogroup_single(self):
        self._mkfile("/s/f_nogroup", uid=0, gid=NO_GID)
        self._mkfile("/s/f_ok", uid=0, gid=0)
        paths = self._scan("/s", {"nogroup": True})
        self.assertEqual(len(paths), 1)
        self.assertTrue(any(p.endswith("f_nogroup") for p in paths))

    def test_or_combination(self):
        # uid만 없음 / gid만 없음 / 둘 다 없음 → 매칭, 둘 다 있음 → 미매칭
        self._mkfile("/s/uid_only", uid=NO_UID, gid=0)
        self._mkfile("/s/gid_only", uid=0, gid=NO_GID)
        self._mkfile("/s/both", uid=NO_UID, gid=NO_GID)
        self._mkfile("/s/neither", uid=0, gid=0)
        paths = self._scan("/s", {"nouser": True, "nogroup": True})
        self.assertEqual(len(paths), 3)
        self.assertTrue(any(p.endswith("uid_only") for p in paths))
        self.assertTrue(any(p.endswith("gid_only") for p in paths))
        self.assertTrue(any(p.endswith("both") for p in paths))
        self.assertFalse(any(p.endswith("neither") for p in paths))

    def test_nogroup_directory(self):
        self._mkdir("/s/dir_nogroup", uid=0, gid=NO_GID)
        self._mkdir("/s/dir_ok", uid=0, gid=0)
        paths = self._scan("/s", {"nogroup": True}, types=["directory"])
        self.assertEqual(len(paths), 1)
        self.assertTrue(any(p.endswith("dir_nogroup") for p in paths))

    # --- xdev ---

    def test_xdev_true_no_recurse_other_device(self):
        self._mkfile("/s/top.txt", 0o666)
        self._mkdir("/s/mnt", 0o755)
        self._mkfile("/s/mnt/deep.txt", 0o666)
        mnt_path = self._p("/s/mnt")
        with mock.patch("os.stat", side_effect=_fake_stat_for(mnt_path, fake_dev=999)):
            paths = self._scan("/s", "world_writable", recursive=True, xdev=True)
        self.assertTrue(any(p.endswith("top.txt") for p in paths))
        self.assertFalse(any(p.endswith("deep.txt") for p in paths))

    def test_xdev_false_recurses_regardless(self):
        self._mkfile("/s/top.txt", 0o666)
        self._mkdir("/s/mnt", 0o755)
        self._mkfile("/s/mnt/deep.txt", 0o666)
        paths = self._scan("/s", "world_writable", recursive=True, xdev=False)
        self.assertTrue(any(p.endswith("top.txt") for p in paths))
        self.assertTrue(any(p.endswith("deep.txt") for p in paths))

    def test_xdev_mount_point_itself_evaluated(self):
        # 디바이스가 달라도 마운트 지점 디렉터리 자신은 criteria 평가 대상이다.
        self._mkdir("/s/mnt", 0o777)
        mnt_path = self._p("/s/mnt")
        with mock.patch("os.stat", side_effect=_fake_stat_for(mnt_path, fake_dev=999)):
            paths = self._scan(
                "/s", "world_writable", recursive=True, types=["file", "directory"], xdev=True
            )
        self.assertTrue(any(p.endswith("mnt") for p in paths))


if __name__ == "__main__":
    unittest.main()
