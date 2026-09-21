# isms-p-audit

ISMS-P 인증 준비 및 보안 점검을 지원하기 위한 오픈소스 프레임워크입니다.

주요 목표는 다음과 같습니다.

- ISMS-P 인증기준 분석
- 기술적 보안 점검 (초기 대상: Linux/Unix 서버)
- 보안 점검 결과 및 증적 수집
- 컴플라이언스 문서화
- 기술적으로 자동화 가능한 항목의 자동 점검
- 점검 결과와 ISMS-P 인증기준 간의 추적성 확보

> 현재는 **KISA 기술적 취약점 분석·평가(상세가이드 2026, Unix 서버 U-01~U-67)** 을
> Technical Check로 분해·구현하는 단계입니다.

---

## 핵심 원칙

- **출처 우선**: 공식 문서를 기준으로 판단한다. 임의로 요구사항을 만들어내지 않는다.
- **추적성**: 점검 결과가 어떤 Specification·Source에 의해 만들어졌는지 추적할 수 있어야 한다.
- **사실과 해석의 분리**: 공식 문서 내용과 프로젝트의 해석·자동화 방법을 명확히 구분한다.
- **결과와 인증판단의 분리**: Technical Check의 PASS/FAIL은 KISA 취약점 점검 결과와 동일하지 않으며,
  ISMS-P 인증 적합성 판단과도 동일하지 않다.

---

## 계층 구조

```
Source (data/kisa/, docs/sources/)      ← 공식 문서 원문·추출 (SSOT, 수정 금지)
        ↓
Analysis (docs/analysis/)               ← 분석 결과 (Source/Interpretation/Automation 구분)
        ↓
Specification (data/checks/, docs/design/check-specification.md) ← 판정 조건
        ↓
Mapping (data/mappings/)                ← KISA ↔ Check 연결 (SSOT)
        ↓
Implementation (engine/)                ← 실제 수집·평가 코드
        ↓
Test / Evidence / Result
```

- **Source**: 공식 문서에서 추출한 원본 요구사항·점검항목 (`data/kisa/linux/*.yaml`).
- **Specification**: 공식 요구사항을 실제 기술 점검으로 해석한 점검 명세 (`data/checks/linux/*.yaml`).
- **Implementation**: 점검 명세를 실제 시스템에서 실행하는 코드 (`engine/`).

---

## 디렉터리 구조

```
isms-p-audit/
├── data/
│   ├── isms-p/            # ISMS-P 인증기준·세부점검항목
│   ├── kisa/              # KISA 점검항목 (원본 SSOT, 수정 금지)
│   ├── checks/            # Technical Check 정의 (Check Specification)
│   └── mappings/          # KISA↔Check, ISMS-P↔Linux 매핑
├── docs/
│   ├── sources/           # 원본 소스 문서 (SSOT, 수정 금지)
│   ├── analysis/          # 분석 결과
│   └── design/            # 설계 문서 (check-specification.md 기준)
├── engine/                # Check 실행 엔진
│   ├── model.py           # Result / ResultStatus / Evidence
│   ├── loader.py          # Check YAML 로드·조회
│   ├── collector.py       # 값 수집 (config/service/file/account/group/scan/package/document)
│   ├── evaluator.py       # expect 평가 (리프/결합/mode_allowed)
│   ├── runner.py          # 수집 → 평가 → 결과 조율
│   └── cli.py             # CLI 진입점
├── tools/
│   └── validate_checks.py # Check/Mapping 스키마 검증
└── tests/                 # unittest 테스트
```

---

## 현재 진행 상태

| 항목 | 값 |
| --- | --- |
| KISA 점검항목 | 67개 (`data/kisa/linux/*.yaml`) |
| Technical Check | 77개 (`data/checks/linux/*.yaml`) |
| Mapping | 67 KISA ↔ 77 Check (`data/mappings/kisa-to-check.yaml`) |
| Check type | 14종 |

### Check type 분포

`config_value`(25), `service_status`(13), `file_scan`(8), `file_owner`(8), `file_mode`(8),
`package_version`(3), `account_uid`(2), `account_group`(2), `account_shell`(2),
`file_existence`(2), `account_duplicate`(1), `account_home`(1), `account_home_owner`(1), `document`(1)

### 자동화 수준 (관찰/판단 2축)

| 관찰 | 판단 | Check 수 |
| --- | --- | --- |
| auto | auto (A/A) | 65 |
| auto | human (A/H) | 8 |
| auto | external_data (A/E) | 3 |
| manual | human (M/H) | 1 |

---

## 실행 방법

### 단일 Check 실행

```bash
python3 -m engine.cli CK-lnx-U01-001
```

### 전체 Check 실행 / 목록

```bash
python3 -m engine.cli            # 전체 실행
python3 -m engine.cli --list     # Check ID 목록
```

### 검증

```bash
python3 tools/validate_checks.py      # Check/Mapping 스키마 검증
python3 -m unittest discover          # 전체 테스트
```

---

## Check Specification 개요

Check는 `id`, `type`, `targets`, `expect`, `automation`, `evidence` 등으로 정의된다.
상세 규약은 [`docs/design/check-specification.md`](docs/design/check-specification.md)를 기준으로 한다.

```yaml
- id: CK-lnx-U31-001
  type: account_home_owner
  targets:
    - kind: account
      source: /etc/passwd
      root: /home
  expect:
    op: empty
  automation:
    observation: auto
    assessment: auto
```

### Result 상태 모델

| 상태 | 의미 |
| --- | --- |
| `PASS` | 요구 조건을 만족 |
| `FAIL` | 요구 조건을 만족하지 않음(취약) |
| `NOT_APPLICABLE` | 적용 대상이 아님(precondition 불충족) |
| `NOT_SUPPORTED` | 현재 구현이 해당 환경/메커니즘을 지원하지 않음 |
| `ERROR` | 수집·판정 실패(정상 판단 불가) |
| `MANUAL_REQUIRED` | 사람 확인 필요 |

---

## 남은 작업 (현재 GAP)

- **`value_ref` 해석**: 취약점 DB/벤더 권고 연동 — U-45/U-49/U-64-002 (현재 `NOT_SUPPORTED`).
- **U-15 `nogroup` 보강**, **U-23 SGID/root owner**, **U-24 환경변수 파일명·계정 owner**, **U-26 device 의미**.
- **`account_gid`/`process_running`/`command_output`** type collector 미구현(77개 Check에서 미사용).

> 자세한 설계·분석 이력은 `docs/design/`, `docs/analysis/`의 문서를 참고한다.
