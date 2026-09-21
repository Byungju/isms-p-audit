"""U-31 홈 디렉터리 소유자·권한(account_home_owner) 테스트.

KISA U-31: 홈 디렉터리 소유자 == 해당 계정 UID + other-write 없음.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from engine import runner
from engine.model import ResultStatus

ALICE_UID = 1000
BOB_UID = 1001


def _write_passwd(root: Path, lines: list[str]) -> None:
    d = root / "etc"
    d.mkdir(parents=True, exist_ok=True)
    (d / "passwd").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mkhome(root: Path, relpath: str, mode: int = 0o755, uid: int | None = None):
    p = root / relpath.lstrip("/")
    p.mkdir(parents=True, exist_ok=True)
    p.chmod(mode)
    if uid is not None:
        os.chown(p, uid, uid)
    return p


class TestU31HomeOwner(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self):
        return runner.run("CK-lnx-U31-001", root=str(self.root))

    # --- 소유자/권한 판정 ---

    def test_owner_match_pass(self):
        _mkhome(self.root, "/home/alice", uid=ALICE_UID)
        _write_passwd(self.root, [f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash"])
        self.assertEqual(self._run().status, ResultStatus.PASS)

    def test_owner_mismatch_fail(self):
        _mkhome(self.root, "/home/alice", uid=BOB_UID)  # 소유자가 alice가 아님
        _write_passwd(self.root, [f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash"])
        self.assertEqual(self._run().status, ResultStatus.FAIL)

    def test_other_write_fail(self):
        # alice UID 1000 + home owner UID 1000 + mode 0777 → other-write 위반
        _mkhome(self.root, "/home/alice", mode=0o777, uid=ALICE_UID)
        _write_passwd(self.root, [f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash"])
        self.assertEqual(self._run().status, ResultStatus.FAIL)

    def test_owner_mismatch_and_other_write_fail(self):
        # alice UID 1000 + home owner UID 1001 + mode 0777 → 소유자·other-write 모두 위반
        _mkhome(self.root, "/home/alice", mode=0o777, uid=BOB_UID)
        _write_passwd(self.root, [f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash"])
        self.assertEqual(self._run().status, ResultStatus.FAIL)

    def test_owner_and_mode_ok_pass(self):
        _mkhome(self.root, "/home/alice", mode=0o750, uid=ALICE_UID)
        _write_passwd(self.root, [f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash"])
        self.assertEqual(self._run().status, ResultStatus.PASS)

    def test_owner_mismatch_no_write_fail(self):
        _mkhome(self.root, "/home/alice", mode=0o750, uid=BOB_UID)
        _write_passwd(self.root, [f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash"])
        self.assertEqual(self._run().status, ResultStatus.FAIL)

    # --- 무관 디렉터리/계정 미매칭 ---

    def test_multiple_accounts_pass(self):
        # alice, bob 각각 올바른 UID로 홈 소유 → 계정 매핑 검증
        _mkhome(self.root, "/home/alice", mode=0o755, uid=ALICE_UID)
        _mkhome(self.root, "/home/bob", mode=0o755, uid=BOB_UID)
        _write_passwd(self.root, [
            f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash",
            f"bob:x:{BOB_UID}:{BOB_UID}::/home/bob:/bin/bash",
        ])
        self.assertEqual(self._run().status, ResultStatus.PASS)

    def test_unrelated_home_dir_not_matched(self):
        _mkhome(self.root, "/home/alice", mode=0o755, uid=ALICE_UID)
        _mkhome(self.root, "/home/stranger", mode=0o777, uid=0)  # 어떤 계정의 home도 아님
        _write_passwd(self.root, [f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash"])
        self.assertEqual(self._run().status, ResultStatus.PASS)

    def test_dir_without_account_not_matched(self):
        # /home/alice는 계정이 있으나 /home/bob은 passwd에 없음
        _mkhome(self.root, "/home/alice", mode=0o755, uid=ALICE_UID)
        _mkhome(self.root, "/home/bob", mode=0o777, uid=BOB_UID)
        _write_passwd(self.root, [f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash"])
        self.assertEqual(self._run().status, ResultStatus.PASS)

    # --- scope(홈이 /home 밖) ---

    def test_home_outside_scope_skipped(self):
        # root의 홈 /root는 scope(/home) 밖 → 검사하지 않음
        _mkhome(self.root, "/home/alice", mode=0o755, uid=ALICE_UID)
        _mkhome(self.root, "/root", mode=0o755, uid=ALICE_UID)  # /root는 alice 소유(잘못이지만 scope 밖)
        _write_passwd(self.root, [
            f"root:x:0:0:root:/root:/bin/bash",
            f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash",
        ])
        self.assertEqual(self._run().status, ResultStatus.PASS)

    # --- 존재하지 않는 홈 ---

    def test_missing_home_skipped(self):
        # bob의 홈 /home/bob이 없음 → U-31은 건너뜀(존재 검사는 U-32 담당)
        _mkhome(self.root, "/home/alice", mode=0o755, uid=ALICE_UID)
        _write_passwd(self.root, [
            f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash",
            f"bob:x:{BOB_UID}:{BOB_UID}::/home/bob:/bin/bash",
        ])
        self.assertEqual(self._run().status, ResultStatus.PASS)

    # --- passwd 파일 없음 ---

    def test_passwd_missing_error(self):
        self.assertEqual(self._run().status, ResultStatus.ERROR)

    # --- evidence ---

    def test_owner_mismatch_evidence(self):
        _mkhome(self.root, "/home/alice", uid=BOB_UID)
        _write_passwd(self.root, [f"alice:x:{ALICE_UID}:{ALICE_UID}::/home/alice:/bin/bash"])
        result = self._run()
        self.assertEqual(result.status, ResultStatus.FAIL)
        owners = [ev for ev in result.evidence if ev.attribute == "owner"]
        self.assertEqual(len(owners), 1)
        self.assertEqual(owners[0].target, "/home/alice")
        self.assertEqual(owners[0].expected, "alice")


if __name__ == "__main__":
    unittest.main()
