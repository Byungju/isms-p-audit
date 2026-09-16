"""CK-lnx-U01-001 (config_value) Vertical Slice 테스트.

실제 /etc/ssh/sshd_config를 수정하지 않고, 임시 디렉터리에 fixture를 만들어
runner를 샌드박스(root)로 실행한다.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from engine import collector, evaluator, runner
from engine.model import ResultStatus


def _write_fixture(root: Path, content: str) -> None:
    d = root / "etc" / "ssh"
    d.mkdir(parents=True, exist_ok=True)
    (d / "sshd_config").write_text(content, encoding="utf-8")


class TestExtractConfigValue(unittest.TestCase):
    def test_last_wins(self):
        content = "PermitRootLogin yes\nPermitRootLogin no\n"
        self.assertEqual(collector.extract_config_value(content, "PermitRootLogin"), "no")

    def test_comment_ignored(self):
        content = "#PermitRootLogin yes\n"
        self.assertIsNone(collector.extract_config_value(content, "PermitRootLogin"))

    def test_whitespace(self):
        content = "   PermitRootLogin    no   \n"
        self.assertEqual(collector.extract_config_value(content, "PermitRootLogin"), "no")

    def test_key_absent(self):
        content = "Port 22\n"
        self.assertIsNone(collector.extract_config_value(content, "PermitRootLogin"))


class TestEvaluate(unittest.TestCase):
    def test_eq_case_insensitive_flag(self):
        self.assertTrue(evaluator.evaluate(
            {"op": "eq", "value": "No", "case_insensitive": True}, {None: "no"},
        ))

    def test_eq_case_sensitive_default(self):
        self.assertFalse(evaluator.evaluate({"op": "eq", "value": "No"}, {None: "no"}))

    def test_eq_mismatch(self):
        self.assertFalse(evaluator.evaluate({"op": "eq", "value": "No"}, {None: "yes"}))

    def test_not_contains(self):
        self.assertTrue(evaluator.evaluate({"op": "not_contains", "value": "pts"}, {None: "console"}))


class TestRunU01(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self):
        return runner.run("CK-lnx-U01-001", root=str(self.root))

    def test_pass(self):
        _write_fixture(self.root, "PermitRootLogin no\n")
        self.assertEqual(self._run().status, ResultStatus.PASS)

    def test_fail(self):
        _write_fixture(self.root, "PermitRootLogin yes\n")
        result = self._run()
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertIn("PermitRootLogin", result.message)
        self.assertIn("다름", result.message)

    def test_comment_only_is_fail(self):
        _write_fixture(self.root, "#PermitRootLogin yes\n")
        self.assertEqual(self._run().status, ResultStatus.FAIL)

    def test_case_insensitive_pass(self):
        _write_fixture(self.root, "PermitRootLogin No\n")
        self.assertEqual(self._run().status, ResultStatus.PASS)

    def test_missing_file_error(self):
        # 점검 대상 파일이 없으면 점검 불가 → ERROR (NOT_APPLICABLE 아님)
        self.assertEqual(self._run().status, ResultStatus.ERROR)

    def test_key_absent_fail(self):
        _write_fixture(self.root, "Port 22\n")
        self.assertEqual(self._run().status, ResultStatus.FAIL)

    def test_evidence(self):
        _write_fixture(self.root, "PermitRootLogin no\n")
        result = self._run()
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(len(result.evidence), 1)
        ev = result.evidence[0]
        self.assertEqual(ev.target, "/etc/ssh/sshd_config")
        self.assertEqual(ev.attribute, "PermitRootLogin")
        self.assertEqual(ev.observed, "no")
        self.assertEqual(ev.expected, "No")


def _write_xinetd_telnet(root: Path, enabled: bool) -> None:
    d = root / "etc" / "xinetd.d"
    d.mkdir(parents=True, exist_ok=True)
    value = "no" if enabled else "yes"
    (d / "telnet").write_text(f"disable = {value}\n", encoding="utf-8")


def _write_pam_login(root: Path, has_securetty: bool) -> None:
    d = root / "etc" / "pam.d"
    d.mkdir(parents=True, exist_ok=True)
    content = (
        "auth required pam_securetty.so\n" if has_securetty else "auth required pam_unix.so\n"
    )
    (d / "login").write_text(content, encoding="utf-8")


def _write_securetty(root: Path, has_pts: bool) -> None:
    d = root / "etc"
    d.mkdir(parents=True, exist_ok=True)
    content = "pts/0\npts/1\n" if has_pts else "console\n"
    (d / "securetty").write_text(content, encoding="utf-8")


def _write_systemd_active(root: Path, name: str = "telnet") -> None:
    d = root / "run" / "systemd"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.active").write_text("active\n", encoding="utf-8")


def _write_systemd_enabled(root: Path, name: str = "telnet") -> None:
    d = root / "etc" / "systemd" / "system" / "sockets.target.wants"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.socket").write_text("", encoding="utf-8")


def _write_systemd_masked(root: Path, name: str = "telnet") -> None:
    d = root / "etc" / "systemd" / "system"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.socket").symlink_to("/dev/null")


def _write_inetd_conf(root: Path, name: str = "telnet", enabled: bool = True) -> None:
    d = root / "etc"
    d.mkdir(parents=True, exist_ok=True)
    line = f"{name} stream tcp nowait root /usr/sbin/telnetd telnetd\n"
    (d / "inetd.conf").write_text(line if enabled else f"#{line}", encoding="utf-8")


def _write_systemd_unit(root: Path, name: str = "telnet") -> None:
    # unit 파일만 존재(disabled: enabled 아님, active 아님)
    d = root / "usr" / "lib" / "systemd" / "system"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.socket").write_text("", encoding="utf-8")


def _write_runtime_process(root: Path, name: str = "telnet") -> None:
    d = root / "run"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.pid").write_text("1\n", encoding="utf-8")


def _write_runtime_port(root: Path, name: str = "telnet") -> None:
    d = root / "run"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.listening").write_text("listening\n", encoding="utf-8")


def _obs(evidence, target):
    for ev in evidence:
        if ev.target == target:
            return ev.observed
    return None


class TestRunU01Telnet(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, check_id):
        return runner.run(check_id, root=str(self.root))

    # --- CK-lnx-U01-002 : Telnet 사용 여부 ---

    def test_u01_002_not_used_pass(self):
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(_obs(result.evidence, "systemd"), "not_present")
        self.assertEqual(_obs(result.evidence, "telnetd"), "not_running")
        self.assertEqual(_obs(result.evidence, "tcp/23"), "no")
        self.assertIn("사용하지 않음", result.message)

    def test_u01_002_used_fail(self):
        _write_xinetd_telnet(self.root, enabled=True)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertEqual(_obs(result.evidence, "xinetd"), "enabled")

    def test_u01_002_systemd_active_fail(self):
        _write_systemd_active(self.root)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertEqual(_obs(result.evidence, "systemd"), "active")

    def test_u01_002_systemd_enabled_inactive_pass(self):
        # enabled(auto-start)지만 active(실행 중)가 아니면 미사용
        _write_systemd_enabled(self.root)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(_obs(result.evidence, "systemd"), "enabled")

    def test_u01_002_systemd_disabled_pass(self):
        # unit만 존재(disabled): enabled도 active도 아님 → 미사용
        _write_systemd_unit(self.root)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(_obs(result.evidence, "systemd"), "disabled")

    def test_u01_002_systemd_masked_pass(self):
        _write_systemd_masked(self.root)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(_obs(result.evidence, "systemd"), "masked")

    def test_u01_002_xinetd_disabled_pass(self):
        _write_xinetd_telnet(self.root, enabled=False)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(_obs(result.evidence, "xinetd"), "disabled")

    def test_u01_002_inetd_enabled_fail(self):
        _write_inetd_conf(self.root, enabled=True)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertEqual(_obs(result.evidence, "inetd"), "enabled")

    def test_u01_002_inetd_commented_pass(self):
        _write_inetd_conf(self.root, enabled=False)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(_obs(result.evidence, "inetd"), "disabled")

    def test_u01_002_runtime_process_running_fail(self):
        # 서비스 매니저 설정이 전혀 없어도, telnetd 프로세스가 실행 중이면 사용 중
        _write_runtime_process(self.root)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertEqual(_obs(result.evidence, "telnetd"), "running")

    def test_u01_002_runtime_port_listening_fail(self):
        _write_runtime_port(self.root)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertEqual(_obs(result.evidence, "tcp/23"), "yes")

    def test_u01_002_systemd_absent_xinetd_enabled_fail(self):
        # systemd가 없어도 xinetd로 Telnet이 활성화돼 있으면 사용 중 (systemd 부재 ≠ 미사용)
        _write_xinetd_telnet(self.root, enabled=True)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertEqual(_obs(result.evidence, "systemd"), "not_present")
        self.assertEqual(_obs(result.evidence, "xinetd"), "enabled")

    def test_u01_002_config_unreadable_error(self):
        # xinetd 설정 파일을 읽을 수 없음(디렉터리) → 판단 불가 → ERROR
        d = self.root / "etc" / "xinetd.d" / "telnet"
        d.mkdir(parents=True)
        result = self._run("CK-lnx-U01-002")
        self.assertEqual(result.status, ResultStatus.ERROR)

    # --- CK-lnx-U01-003 : Telnet 사용 시 root 직접 접속 제한 ---

    def test_u01_003_not_used_not_applicable(self):
        result = self._run("CK-lnx-U01-003")
        self.assertEqual(result.status, ResultStatus.NOT_APPLICABLE)
        # ERROR가 아니라 정상 결과 상태여야 함
        self.assertNotEqual(result.status, ResultStatus.ERROR)
        # Message는 오류성 표현이 아니어야 하고 N/A 사유를 설명해야 함
        self.assertNotIn("충족되지 않음", result.message)
        self.assertIn("적용되지 않음", result.message)
        self.assertIn("사용하지 않아", result.message)
        # N/A 근거: U-01-002 결과 참조 + 실제 관찰 사실
        self.assertEqual(_obs(result.evidence, "CK-lnx-U01-002"), "PASS")
        self.assertEqual(_obs(result.evidence, "systemd"), "not_present")

    def test_u01_003_used_restricted_pass(self):
        _write_xinetd_telnet(self.root, enabled=True)
        _write_pam_login(self.root, has_securetty=True)
        _write_securetty(self.root, has_pts=False)
        result = self._run("CK-lnx-U01-003")
        self.assertEqual(result.status, ResultStatus.PASS)

    def test_u01_003_used_allowed_fail(self):
        _write_xinetd_telnet(self.root, enabled=True)
        _write_pam_login(self.root, has_securetty=True)
        _write_securetty(self.root, has_pts=True)
        result = self._run("CK-lnx-U01-003")
        self.assertEqual(result.status, ResultStatus.FAIL)

    def test_u01_003_used_missing_config_error(self):
        _write_xinetd_telnet(self.root, enabled=True)
        result = self._run("CK-lnx-U01-003")
        self.assertEqual(result.status, ResultStatus.ERROR)


def _write_passwd(root: Path, lines: list[str]) -> None:
    d = root / "etc"
    d.mkdir(parents=True, exist_ok=True)
    (d / "passwd").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestRunU05U16(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, check_id):
        return runner.run(check_id, root=str(self.root))

    # --- CK-lnx-U05-001 : UID 0 계정 존재 여부 ---

    def test_u05_pass(self):
        _write_passwd(self.root, [
            "root:x:0:0:root:/root:/bin/bash",
            "user:x:1000:1000::/home/user:/bin/bash",
        ])
        result = self._run("CK-lnx-U05-001")
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(_obs(result.evidence, "/etc/passwd"), "none")
        self.assertIn("존재하지 않음", result.message)

    def test_u05_fail(self):
        _write_passwd(self.root, [
            "root:x:0:0:root:/root:/bin/bash",
            "hacker:x:0:1001::/home/hacker:/bin/bash",
        ])
        result = self._run("CK-lnx-U05-001")
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertEqual(_obs(result.evidence, "/etc/passwd"), "hacker")
        self.assertIn("존재함", result.message)

    # --- CK-lnx-U16-001 : /etc/passwd 소유자 ---

    def test_u16_owner_pass(self):
        _write_passwd(self.root, ["root:x:0:0:root:/root:/bin/bash"])
        result = self._run("CK-lnx-U16-001")
        self.assertEqual(result.status, ResultStatus.PASS)
        ev = result.evidence[0]
        self.assertEqual(ev.attribute, "owner")
        self.assertEqual(ev.expected, "root")

    def test_u16_owner_fail(self):
        p = self.root / "etc" / "passwd"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("root:x:0:0:root:/root:/bin/bash\n", encoding="utf-8")
        os.chown(p, 1000, 1000)  # 소유자를 비root로 변경
        result = self._run("CK-lnx-U16-001")
        self.assertEqual(result.status, ResultStatus.FAIL)

    # --- CK-lnx-U16-002 : /etc/passwd 권한 ---

    def test_u16_mode_pass(self):
        p = self.root / "etc" / "passwd"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("root:x:0:0:root:/root:/bin/bash\n", encoding="utf-8")
        os.chmod(p, 0o644)
        result = self._run("CK-lnx-U16-002")
        self.assertEqual(result.status, ResultStatus.PASS)
        self.assertEqual(_obs(result.evidence, "/etc/passwd"), "0644")

    def test_u16_mode_fail(self):
        p = self.root / "etc" / "passwd"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("root:x:0:0:root:/root:/bin/bash\n", encoding="utf-8")
        os.chmod(p, 0o666)
        result = self._run("CK-lnx-U16-002")
        self.assertEqual(result.status, ResultStatus.FAIL)
        self.assertEqual(_obs(result.evidence, "/etc/passwd"), "0666")


if __name__ == "__main__":
    unittest.main()
