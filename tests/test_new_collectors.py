"""새 Collector/Evaluator와 전체 Check Coverage 검증 테스트."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from engine import collector, evaluator, loader, runner
from engine.model import ResultStatus


def _obs(evidence, target):
    for ev in evidence:
        if ev.target == target:
            return ev.observed
    return None


class TestEvaluatorEmpty(unittest.TestCase):
    def test_empty_list(self):
        self.assertTrue(evaluator.evaluate({"op": "empty"}, {None: []}))

    def test_empty_nonempty_list(self):
        self.assertFalse(evaluator.evaluate({"op": "empty"}, {None: ["a"]}))

    def test_not_empty(self):
        self.assertTrue(evaluator.evaluate({"not": {"op": "empty"}}, {None: ["a"]}))

    def test_exists_false(self):
        self.assertFalse(evaluator.evaluate({"op": "exists"}, {None: False}))


class TestNewCollectors(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, check_id):
        return runner.run(check_id, root=str(self.root))

    def test_file_scan_world_writable(self):
        d = self.root / "tmp" / "scan"
        d.mkdir(parents=True)
        (d / "a.txt").write_text("x", encoding="utf-8")
        (d / "a.txt").chmod(0o666)
        (d / "b.txt").write_text("y", encoding="utf-8")
        (d / "b.txt").chmod(0o644)
        result = self._run("CK-lnx-U25-001")
        self.assertEqual(result.status, ResultStatus.MANUAL_REQUIRED)  # A/H

    def test_account_duplicate(self):
        d = self.root / "etc"
        d.mkdir(parents=True)
        (d / "passwd").write_text(
            "root:x:0:0:root:/root:/bin/bash\n"
            "user1:x:1000:1000::/home/user1:/bin/bash\n"
            "user2:x:1000:1000::/home/user2:/bin/bash\n",
            encoding="utf-8",
        )
        result = self._run("CK-lnx-U10-001")
        self.assertEqual(result.status, ResultStatus.FAIL)  # 중복 UID 존재

    def test_file_existence_not_exists(self):
        result = self._run("CK-lnx-U27-001")  # .rhosts/hosts.equiv 없음 → PASS
        self.assertEqual(result.status, ResultStatus.PASS)

    def test_scan_skips_pseudo_fs(self):
        # /sys 아래 world-writable 파일은 pseudo fs이므로 스캔에서 제외되어야 한다.
        sysdir = self.root / "sys" / "module" / "x" / "sections"
        sysdir.mkdir(parents=True)
        f1 = sysdir / ".strtab"
        f1.write_text("x", encoding="utf-8")
        f1.chmod(0o666)
        tmpdir = self.root / "tmp"
        tmpdir.mkdir(parents=True)
        f2 = tmpdir / "a.txt"
        f2.write_text("x", encoding="utf-8")
        f2.chmod(0o666)

        outcome = collector.collect(
            {"kind": "scan", "root": "/", "recursive": True, "criteria": "world_writable"},
            root=str(self.root),
        )
        paths = outcome.value
        self.assertTrue(any("/tmp/a.txt" in p for p in paths))
        self.assertFalse(any("/sys/" in p for p in paths))


class TestCoverageInvariant(unittest.TestCase):
    def test_77_checks_67_kisa(self):
        checks = []
        import glob
        from pathlib import Path as P
        base = P(__file__).resolve().parent.parent / "data"
        for f in sorted((base / "checks" / "linux").glob("*.yaml")):
            d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            checks.extend(d.get("checks", []))
        ids = [c["id"] for c in checks]
        self.assertEqual(len(checks), 77)
        self.assertEqual(len(set(ids)), 77)

        kisa_ids = set()
        for f in sorted((base / "kisa" / "linux").glob("*.yaml")):
            d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            kisa_ids.update(it["id"] for it in d.get("items", []))
        self.assertEqual(len(kisa_ids), 67)

        mapping = yaml.safe_load((base / "mappings" / "kisa-to-check.yaml").read_text(encoding="utf-8")) or {}
        self.assertEqual(len(mapping.get("mappings", [])), 67)
        refs = [cid for m in mapping.get("mappings", []) for cid in m.get("check_refs", [])]
        self.assertEqual(len(refs), 77)


if __name__ == "__main__":
    unittest.main()
