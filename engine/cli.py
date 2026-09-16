"""CLI 진입점.

사용:
    python -m engine.cli CK-lnx-U01-001   # 단일 Check 실행
    python -m engine.cli                  # 전체 Check 실행
    python -m engine.cli --list           # Check ID 목록 출력
"""

from __future__ import annotations

import argparse
from collections import Counter

from . import loader
from .model import Result
from .runner import run


MAX_LIST_DISPLAY = 20


def _print_result(result: Result) -> None:
    print(f"Check: {result.check_id}")
    print(f"Description: {result.description}")
    print(f"Result: {result.status.value}")
    if result.evidence:
        print("Evidence:")
        for ev in result.evidence:
            if isinstance(ev.observed, list):
                _print_list_evidence(ev)
            else:
                fields = [f"target={ev.target}", f"attribute={ev.attribute}", f"observed={ev.observed}"]
                if ev.expected is not None:
                    fields.append(f"expected={ev.expected}")
                print("  - " + " ".join(fields))
    if result.message:
        print(f"Message: {result.message}")


def _print_list_evidence(ev) -> None:
    """목록형 observed(예: file_scan 일치 파일 목록)를 읽기 쉽게 출력한다."""
    items = ev.observed
    print(f"  - target={ev.target} attribute={ev.attribute}")
    print(f"    Matched: {len(items)} files")
    if items:
        for p in items[:MAX_LIST_DISPLAY]:
            print(f"      - {p}")
        if len(items) > MAX_LIST_DISPLAY:
            print(f"      ... {len(items) - MAX_LIST_DISPLAY} more")


def _print_summary(results: list[Result]) -> None:
    counts = Counter(r.status.value for r in results)
    print("---")
    print(f"Total: {len(results)}")
    for status in ("PASS", "FAIL", "NOT_APPLICABLE", "ERROR", "NOT_SUPPORTED", "MANUAL_REQUIRED"):
        if counts.get(status):
            print(f"{status}: {counts[status]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Technical Check 실행")
    parser.add_argument("check_id", nargs="?", help="Check ID (생략 시 전체 실행)")
    parser.add_argument("--list", action="store_true", help="Check ID 목록 출력")
    args = parser.parse_args(argv)

    if args.list:
        for check_id in loader.all_check_ids():
            print(check_id)
        return 0

    if args.check_id:
        result = run(args.check_id)
        _print_result(result)
        return 0 if result.status.value in ("PASS", "NOT_APPLICABLE") else 1

    results = [run(check_id) for check_id in loader.all_check_ids()]
    for i, result in enumerate(results):
        if i > 0:
            print()
        _print_result(result)
    _print_summary(results)
    return 0 if all(r.status.value in ("PASS", "NOT_APPLICABLE") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
