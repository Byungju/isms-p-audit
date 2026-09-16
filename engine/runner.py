"""Check 실행 조율: 수집 → 평가 → 결과 생성."""

from __future__ import annotations

import sys

from . import collector, evaluator, loader
from .model import Evidence, Result, ResultStatus

SUPPORTED_TYPES = {
    "config_value", "service_status", "account_uid", "account_shell",
    "account_duplicate", "account_group", "file_owner", "file_mode",
    "file_existence", "file_scan", "package_version", "document",
}


def run(check_id: str, root: str | None = None) -> Result:
    """Check ID 하나를 실행해 Result를 반환한다.

    root가 주어지면 파일 접근을 해당 디렉터리로 샌드박스한다(테스트용).
    """
    check = loader.find_check(check_id)
    if check is None:
        return Result(
            check_id=check_id,
            status=ResultStatus.ERROR,
            message=f"Check를 찾을 수 없음: {check_id}",
        )

    description = check.get("description", "")

    # automation (2축: observation/assessment 지원)
    automation = check.get("automation", "auto")
    if isinstance(automation, dict):
        if automation.get("observation") == "manual":
            return Result(
                check_id=check_id,
                status=ResultStatus.MANUAL_REQUIRED,
                description=description,
                message="관찰이 수동인 Check는 자동 실행 대상이 아님",
            )
    elif automation == "manual":
        return Result(
            check_id=check_id,
            status=ResultStatus.MANUAL_REQUIRED,
            description=description,
            message="manual Check는 자동 실행 대상이 아님",
        )

    # type
    ctype = check.get("type")
    if ctype not in SUPPORTED_TYPES:
        return Result(
            check_id=check_id,
            status=ResultStatus.NOT_SUPPORTED,
            description=description,
            message=f"지원하지 않는 Check type: {ctype!r}",
        )

    # platform (최소 확인)
    platforms = check.get("platforms", [])
    if _current_platform() not in platforms:
        return Result(
            check_id=check_id,
            status=ResultStatus.NOT_SUPPORTED,
            description=description,
            message=f"현재 플랫폼이 대상이 아님: {platforms!r}",
        )

    # 전제조건(precondition): 불충족이면 Check가 적용되지 않음
    precondition = check.get("precondition")
    if precondition:
        result = _run_precondition(check_id, description, precondition, root)
        if result is not None:
            return result

    targets = check.get("targets") or []
    expect = check.get("expect")
    if not targets or not isinstance(expect, dict):
        return Result(
            check_id=check_id,
            status=ResultStatus.ERROR,
            description=description,
            message="Check에 targets/expect가 없음",
        )

    # 수집
    observed: dict = {}
    evidence: list[Evidence] = []
    assessment = _assessment(check)
    for target in targets:
        outcome = collector.collect(target, root=root, ctype=ctype)
        if outcome.error is not None:
            return Result(
                check_id=check_id,
                status=ResultStatus.ERROR,
                description=description,
                message=outcome.error,
            )
        if outcome.missing_target:
            # 점검 대상이 없어 점검 자체가 불가능 → ERROR (P1-4)
            return Result(
                check_id=check_id,
                status=ResultStatus.ERROR,
                description=description,
                message=f"대상 파일이 없음: {target.get('path')}",
            )
        tid = target.get("id")
        observed[tid] = outcome.value
        evidence.extend(_build_evidence(target, outcome, expect, tid))

    # assessment=human: 관찰은 자동, 최종 판단은 사람 (A/H)
    if assessment == "human":
        return Result(
            check_id=check_id,
            status=ResultStatus.MANUAL_REQUIRED,
            description=description,
            evidence=evidence,
            message="관찰 결과를 기준으로 사람의 판단이 필요함",
        )

    # 평가
    try:
        passed = evaluator.evaluate(expect, observed)
    except evaluator.UnsupportedError as exc:
        return Result(
            check_id=check_id,
            status=ResultStatus.NOT_SUPPORTED,
            description=description,
            message=str(exc),
        )
    except evaluator.SpecError as exc:
        return Result(
            check_id=check_id,
            status=ResultStatus.ERROR,
            description=description,
            message=str(exc),
        )

    status = ResultStatus.PASS if passed else ResultStatus.FAIL
    message = _result_message(check, status, targets, observed, expect)
    return Result(
        check_id=check_id,
        status=status,
        description=description,
        evidence=evidence,
        message=message,
    )


def _run_precondition(
    check_id: str, description: str, precondition: dict, root: str | None
) -> Result | None:
    """전제조건을 평가한다.

    - 불충족(False)이면 NOT_APPLICABLE Result를 반환.
    - 충족(True)이면 None(계속 진행).
    - 평가 오류면 ERROR Result를 반환.
    """
    targets = precondition.get("targets") or []
    expect = precondition.get("expect")
    observed: dict = {}
    all_observations: list[dict] = []
    for target in targets:
        outcome = collector.collect(target, root=root)
        if outcome.error is not None:
            return Result(
                check_id=check_id,
                status=ResultStatus.ERROR,
                description=description,
                message=outcome.error,
            )
        if outcome.missing_target:
            return Result(
                check_id=check_id,
                status=ResultStatus.ERROR,
                description=description,
                message=f"전제조건 대상이 없음: {target.get('path')}",
            )
        observed[target.get("id")] = outcome.value
        if outcome.observations:
            all_observations.extend(outcome.observations)

    try:
        applicable = evaluator.evaluate(expect, observed)
    except evaluator.UnsupportedError as exc:
        return Result(
            check_id=check_id,
            status=ResultStatus.NOT_SUPPORTED,
            description=description,
            message=str(exc),
        )
    except evaluator.SpecError as exc:
        return Result(
            check_id=check_id,
            status=ResultStatus.ERROR,
            description=description,
            message=str(exc),
        )

    if not applicable:
        evidence: list[Evidence] = []
        ref = precondition.get("ref")
        if ref:
            evidence.append(Evidence(target=ref, attribute="result", observed=_ref_result_status(ref, check_id, root)))
        for obs in all_observations:
            evidence.append(
                Evidence(
                    target=obs["target"],
                    attribute=obs["attribute"],
                    observed=obs["observed"],
                )
            )
        return Result(
            check_id=check_id,
            status=ResultStatus.NOT_APPLICABLE,
            description=description,
            evidence=evidence,
            message=_not_applicable_message(precondition),
        )
    return None


def _ref_result_status(ref: str, current_check_id: str, root: str | None) -> str:
    """선행 Check(ref)를 실제 실행해 그 Result 상태를 반환한다."""
    if ref == current_check_id:
        return "UNKNOWN"
    try:
        return run(ref, root=root).status.value
    except RecursionError:
        return "UNKNOWN"


def _not_applicable_message(precondition: dict) -> str:
    """NOT_APPLICABLE 결과를 설명하는 문장(오류성 표현 아님)."""
    targets = precondition.get("targets") or []
    if targets and targets[0].get("kind") == "service":
        name = targets[0].get("name", "서비스")
        return f"{name} 서비스를 사용하지 않아 해당 점검은 적용되지 않음"
    return "해당 점검은 이 환경에 적용되지 않음"


def _build_evidence(target: dict, outcome, expect: dict, tid) -> list[Evidence]:
    """한 target의 Evidence 목록을 생성한다."""
    kind = target.get("kind")
    path = target.get("path")
    key = target.get("key")

    # config 전체 내용(contains/not_contains): 판단 조건을 Evidence에 드러낸다.
    if kind == "config" and not key:
        leaf = _leaf_for_target(expect, tid)
        if leaf and leaf[0] in ("contains", "not_contains"):
            op, value = leaf
            content = outcome.value or ""
            matched = str(value) in str(content)
            ok = matched if op == "contains" else (not matched)
            return [
                Evidence(
                    target=path,
                    attribute=op,
                    observed="true" if ok else "false",
                    expected=str(value),
                )
            ]
        return [_to_evidence(o) for o in (outcome.observations or [])]

    # config(key)/file: 단일값 비교 → expected 부여
    if kind in ("config", "file"):
        expected = _expected_for(expect)
        return [_to_evidence(o, expected) for o in (outcome.observations or [])]

    # service/account/group/scan/package/document: 사실 목록 그대로(expected 없음)
    return [_to_evidence(o) for o in (outcome.observations or [])]


def _to_evidence(obs: dict, expected: str | None = None) -> Evidence:
    return Evidence(
        target=obs["target"],
        attribute=obs["attribute"],
        observed=obs["observed"],
        expected=expected,
    )


def _leaf_for_target(expect: dict, tid) -> tuple[str, object] | None:
    """tid에 해당하는 리프 조건 (op, value)를 찾는다."""
    if not isinstance(expect, dict):
        return None
    if "op" in expect:
        return (expect.get("op"), expect.get("value"))
    for key in ("all", "any"):
        if key in expect:
            for cond in expect[key]:
                if cond.get("target") == tid:
                    return (cond.get("op"), cond.get("value"))
    return None


def _expected_for(expect: dict) -> str | None:
    """단일 리프 eq/ne의 기대값 또는 mode_allowed의 허용 마스크를 추출한다."""
    if not isinstance(expect, dict):
        return None
    if expect.get("op") in ("eq", "ne") and "value" in expect:
        return expect["value"]
    if "mode_allowed" in expect:
        return f"{evaluator.mode_allowed_mask(expect['mode_allowed']):04o}"
    return None


def _subject(description: str) -> str:
    """description에서 '여부 확인/확인' 접미사를 제거해 Message 주어로 사용한다."""
    for suffix in ("여부 확인", "확인", "여부"):
        if description.endswith(suffix):
            return description[: -len(suffix)].rstrip()
    return description or "조건"


def _result_message(check: dict, status, targets: list[dict], observed: dict, expect: dict) -> str:
    """PASS/FAIL 결과를 사람이 읽기 쉽게 설명한다."""
    ctype = check.get("type")
    description = check.get("description", "")

    def _obs():
        return observed.get(targets[0].get("id")) if targets else None

    if ctype == "service_status":
        name = targets[0].get("name", "서비스") if targets else "서비스"
        if status == ResultStatus.PASS:
            return f"{name} 서비스를 사용하지 않음"
        return f"{name} 서비스를 사용 중"

    if ctype == "config_value":
        expected = _expected_for(expect)
        if expected is not None:
            key = targets[0].get("key", "설정") if targets else "설정"
            if status == ResultStatus.PASS:
                return f"{key} 값이 기대값({expected})과 일치함"
            return f"{key} 값이 기대값({expected})과 다름 (관찰값: {_obs()})"
        subject = _subject(description)
        return f"{subject} 조건을 충족함" if status == ResultStatus.PASS else f"{subject} 조건을 충족하지 않음"

    if ctype == "file_owner":
        expected = _expected_for(expect)
        if status == ResultStatus.PASS:
            return f"소유자가 기대값({expected})과 일치함"
        return f"소유자가 기대값({expected})과 다름 (관찰값: {_obs()})"

    if ctype == "file_mode":
        if status == ResultStatus.PASS:
            return "권한이 허용 범위 내에 있음"
        return f"권한이 허용 범위를 벗어남 (관찰값: {_obs()})"

    if ctype == "account_uid":
        if status == ResultStatus.PASS:
            return "UID 0 계정이 존재하지 않음"
        return "UID 0 계정이 존재함"

    if ctype == "account_duplicate":
        if status == ResultStatus.PASS:
            return "중복 UID가 존재하지 않음"
        return "중복 UID가 존재함"

    if ctype == "file_scan":
        if status == ResultStatus.PASS:
            return "조건에 맞는 파일이 존재하지 않음"
        return "조건에 맞는 파일이 존재함"

    if ctype == "file_existence":
        if status == ResultStatus.PASS:
            return "대상 파일이 기대 상태와 일치함"
        return "대상 파일이 기대 상태와 다름"

    if ctype in ("account_shell", "account_group", "package_version", "document"):
        if status == ResultStatus.PASS:
            return "조건을 충족함"
        return "조건을 충족하지 않음"

    return ""


def _current_platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def _assessment(check: dict) -> str:
    """Check의 assessment(판단 자동화)를 반환한다."""
    automation = check.get("automation", {})
    if isinstance(automation, dict):
        return automation.get("assessment", "auto")
    return "auto"
