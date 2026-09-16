"""Check Specification YAML 로드 및 조회."""

from __future__ import annotations

from pathlib import Path

import yaml

# 프로젝트 루트 기준 경로
CHECKS_DIR = Path(__file__).resolve().parent.parent / "data" / "checks" / "linux"


def _load_all() -> list[dict]:
    """data/checks/linux/*.yaml 의 모든 Check를 로드한다."""
    checks: list[dict] = []
    if not CHECKS_DIR.is_dir():
        return checks
    for path in sorted(CHECKS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item in data.get("checks", []):
            checks.append(item)
    return checks


def find_check(check_id: str) -> dict | None:
    """Check ID로 Check 정의를 찾는다."""
    for check in _load_all():
        if check.get("id") == check_id:
            return check
    return None


def all_check_ids() -> list[str]:
    """모든 Check ID 목록을 반환한다."""
    return [c["id"] for c in _load_all() if c.get("id")]
