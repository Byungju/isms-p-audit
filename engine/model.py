"""Check 실행 결과 모델."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ResultStatus(str, Enum):
    """Check 실행 결과 상태."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    ERROR = "ERROR"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"


@dataclass
class Evidence:
    """수집된 관찰 사실 하나.

    - target: 관찰 대상(파일 경로/서비스/메커니즘 등)
    - attribute: 관찰 속성(설정 항목/속성명)
    - observed: 실제 관찰값(raw observation, str 또는 list)
    - expected: 기대값(단일값 비교일 때만)
    """

    target: str
    attribute: str
    observed: object
    expected: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Result:
    """Check 실행 결과."""

    check_id: str
    status: ResultStatus
    description: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    message: str = ""
