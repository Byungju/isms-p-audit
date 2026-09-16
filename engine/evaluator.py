"""expect 조건 평가.

Specification의 리프(비교)와 결합(all/any/not)을 평가한다.
이번 슬라이스는 `eq` 리프를 사용하지만, 결합 구조는 재귀적으로 처리한다.
"""

from __future__ import annotations

import re


class SpecError(Exception):
    """잘못된 Check Specification."""


class UnsupportedError(Exception):
    """아직 지원하지 않는 표현(value_ref 등)."""


def _normalize(v):
    if isinstance(v, str):
        return v.strip()
    return v


def evaluate(expect: dict, observed: dict) -> bool:
    """expect 트리를 평가한다.

    observed: {target_id | None: 관측값}  (단일 target은 key None)
    """
    if not isinstance(expect, dict):
        raise SpecError(f"expect가 객체가 아님: {expect!r}")

    if "all" in expect:
        return all(evaluate(cond, observed) for cond in expect["all"])
    if "any" in expect:
        return any(evaluate(cond, observed) for cond in expect["any"])
    if "not" in expect:
        return not evaluate(expect["not"], observed)
    if "mode_allowed" in expect:
        return _evaluate_mode_allowed(expect["mode_allowed"], observed)

    return _evaluate_leaf(expect, observed)


def _evaluate_leaf(leaf: dict, observed: dict) -> bool:
    if "value_ref" in leaf:
        raise UnsupportedError("value_ref 해석은 지원하지 않음")

    op = leaf.get("op")
    value = leaf.get("value")
    case_insensitive = bool(leaf.get("case_insensitive", False))
    target_id = leaf.get("target")  # 단일 target이면 None
    obs = observed.get(target_id)

    if op is None:
        raise SpecError(f"leaf에 op가 없음: {leaf!r}")

    if op == "exists":
        return bool(obs)

    if op == "empty":
        return _empty(obs)

    if op in ("eq", "ne", "contains", "not_contains", "in", "not_in", "le", "lt", "ge", "gt", "matches"):
        if value is None:
            raise SpecError(f"op {op!r}에 value가 없음")

    if op in ("eq", "ne"):
        result = _eq(obs, value, case_insensitive=case_insensitive)
        return result if op == "eq" else not result

    if op in ("contains", "not_contains"):
        result = _contains(obs, value)
        return result if op == "contains" else not result

    if op in ("in", "not_in"):
        result = _in(obs, value)
        return result if op == "in" else not result

    if op in ("le", "lt", "ge", "gt"):
        return _numeric(obs, op, value)

    if op == "matches":
        return _matches(obs, value)

    raise SpecError(f"알 수 없는 op: {op!r}")


def _eq(obs, value, case_insensitive: bool = False) -> bool:
    if case_insensitive and isinstance(obs, str) and isinstance(value, str):
        return obs.lower() == value.lower()
    return _normalize(obs) == _normalize(value)


def _empty(obs) -> bool:
    """목록이 비어 있는지(0개) 판단한다."""
    if obs is None:
        return True
    if isinstance(obs, (list, tuple, set, str, dict)):
        return len(obs) == 0
    return False


def _contains(obs, value) -> bool:
    return str(value) in str(obs)


def _in(obs, value) -> bool:
    if isinstance(obs, (list, tuple, set)):
        obs_set = {str(o) for o in obs}
        return any(str(item) in obs_set for item in _as_list(value))
    return str(obs) in {str(v) for v in _as_list(value)}


def _as_list(value):
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _evaluate_mode_allowed(allowed: dict, observed: dict) -> bool:
    """Unix 권한 semantics: 관측 모드가 허용 최대 범위를 벗어나지 않으면 PASS."""
    mode_str = observed.get(None)
    if mode_str is None:
        return False
    try:
        mode = int(str(mode_str), 8)
    except ValueError as exc:
        raise SpecError(f"모드 값 해석 불가: {mode_str!r}") from exc
    mask = mode_allowed_mask(allowed)
    return (mode & ~mask) == 0


def mode_allowed_mask(allowed: dict) -> int:
    """mode_allowed({owner, group, other})를 허용 최대 권한 비트 마스크로 변환한다."""
    bit_map = {
        "owner": {"r": 0o400, "w": 0o200, "x": 0o100},
        "group": {"r": 0o040, "w": 0o020, "x": 0o010},
        "other": {"r": 0o004, "w": 0o002, "x": 0o001},
    }
    mask = 0
    for who in ("owner", "group", "other"):
        for ch in allowed.get(who, ""):
            mask |= bit_map[who].get(ch, 0)
    return mask


def _numeric(obs, op, value) -> bool:
    try:
        a = float(obs)
        b = float(value)
    except (TypeError, ValueError) as exc:
        raise SpecError(f"수치 비교 불가: obs={obs!r}, value={value!r}") from exc
    if op == "le":
        return a <= b
    if op == "lt":
        return a < b
    if op == "ge":
        return a >= b
    if op == "gt":
        return a > b
    raise SpecError(f"알 수 없는 수치 op: {op!r}")


def _matches(obs, value) -> bool:
    return re.search(str(value), str(obs)) is not None
