"""account_shell / account_home 판정 정확성 테스트.

U-11(로그인 불필요 계정 쉘 제한), U-55(FTP 계정 쉘 제한), U-32(홈 디렉토리 존재)를 검증한다.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine import runner
from engine.model import ResultStatus


def _write_passwd(root: Path, lines: list[str]) -> None:
    d = root / "etc"
    d.mkdir(parents=True, exist_ok=True)
    (d / "passwd").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestAccountShellHome(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, check_id):
        return runner.run(check_id, root=str(self.root))

    # --- U-11: 로그인 불필요 계정 쉘 제한 ---

    def test_u11_all_restricted_pass(self):
        _write_passwd(self.root, [
            "daemon:x:1:1::/usr/sbin:/bin/false",
            "bin:x:2:2::/bin:/sbin/nologin",
            "user:x:1000:1000::/home/user:/bin/bash",  # 대상 아님(일반 사용자)
        ])
        self.assertEqual(self._run("CK-lnx-U11-001").status, ResultStatus.PASS)

    def test_u11_one_login_shell_fail(self):
        _write_passwd(self.root, [
            "daemon:x:1:1::/usr/sbin:/bin/bash",  # 위반(로그인 쉘)
            "bin:x:2:2::/bin:/sbin/nologin",
        ])
        self.assertEqual(self._run("CK-lnx-U11-001").status, ResultStatus.FAIL)

    def test_u11_non_target_only_pass(self):
        # 대상 계정이 없고 일반 사용자만 /bin/bash → 대상 아님 → PASS
        _write_passwd(self.root, [
            "user:x:1000:1000::/home/user:/bin/bash",
        ])
        self.assertEqual(self._run("CK-lnx-U11-001").status, ResultStatus.PASS)

    def test_u11_target_absent_pass(self):
        # 대상 계정(daemon 등)이 /etc/passwd에 없음 → 위반 없음 → PASS
        _write_passwd(self.root, [
            "user:x:1000:1000::/home/user:/sbin/nologin",
        ])
        self.assertEqual(self._run("CK-lnx-U11-001").status, ResultStatus.PASS)

    # --- U-55: FTP 계정 쉘 제한 ---

    def test_u55_ftp_restricted_pass(self):
        _write_passwd(self.root, [
            "ftp:x:134:65534::/srv/ftp:/sbin/nologin",
        ])
        self.assertEqual(self._run("CK-lnx-U55-001").status, ResultStatus.PASS)

    def test_u55_ftp_bash_fail(self):
        _write_passwd(self.root, [
            "ftp:x:134:65534::/srv/ftp:/bin/bash",
        ])
        self.assertEqual(self._run("CK-lnx-U55-001").status, ResultStatus.FAIL)

    # --- 공통: passwd 파일 없음 ---

    def test_passwd_missing_error(self):
        self.assertEqual(self._run("CK-lnx-U11-001").status, ResultStatus.ERROR)

    # --- U-32: 홈 디렉토리 존재 ---

    def test_u32_all_home_exist_pass(self):
        (self.root / "home" / "user1").mkdir(parents=True)
        (self.root / "home" / "user2").mkdir(parents=True)
        _write_passwd(self.root, [
            "user1:x:1000:1000::/home/user1:/bin/bash",
            "user2:x:1001:1001::/home/user2:/bin/bash",
        ])
        self.assertEqual(self._run("CK-lnx-U32-001").status, ResultStatus.PASS)

    def test_u32_home_missing_fail(self):
        (self.root / "home" / "user1").mkdir(parents=True)
        # user2의 홈(/home/user2)은 만들지 않음 → 위반
        _write_passwd(self.root, [
            "user1:x:1000:1000::/home/user1:/bin/bash",
            "user2:x:1001:1001::/home/user2:/bin/bash",
        ])
        self.assertEqual(self._run("CK-lnx-U32-001").status, ResultStatus.FAIL)

    def test_u32_boundary_no_home_dir_fail(self):
        # 시스템 계정(daemon)의 홈(/nonexistent)이 없음 → 위반
        (self.root / "home" / "user1").mkdir(parents=True)
        _write_passwd(self.root, [
            "daemon:x:1:1::/nonexistent:/sbin/nologin",
            "user1:x:1000:1000::/home/user1:/bin/bash",
        ])
        self.assertEqual(self._run("CK-lnx-U32-001").status, ResultStatus.FAIL)


if __name__ == "__main__":
    unittest.main()
