# Check Implementation 설계

> U-01 Technical Check(`CK-lnx-U01-001`)를 실제 Linux 환경에서 실행하기 위한 Implementation 설계.
>
> 이 문서는 `docs/design/check-specification.md`(Check Specification 기준)을 구현하는 방법을 정의한다.
> Check Specification은 변경하지 않는다.

---

## 1. 역할 구분

| 계층 | 역할 |
| --- | --- |
| Check Specification (`data/checks/linux/*.yaml`) | **무엇을** 검사하고 **어떤 조건**으로 판정하는가 |
| Check Implementation (`engine/`) | **Linux에서 실제 값을 어떻게 수집**하고 평가하는가 |

- Specification에는 실행 명령·경로 해석 방법이 없다.
- Implementation은 Specification(targets/expect)을 읽어 실제 시스템에서 값을 수집·평가한다.

---

## 2. 구현 범위

U-01을 기준으로 검증된 Check 모델(Result/Message/Evidence)을 기존 Check에 확장 적용한다.

| Check ID | type | 목적 |
| --- | --- | --- |
| CK-lnx-U01-001 | config_value | SSH root 직접 접속 제한 |
| CK-lnx-U01-002 | service_status | Telnet 원격터미널 서비스 사용 여부 |
| CK-lnx-U01-003 | config_value (precondition) | Telnet 사용 시 root 직접 접속 제한 |
| CK-lnx-U05-001 | account_uid | root 외 UID 0 계정 존재 여부 |
| CK-lnx-U16-001 | file_owner | /etc/passwd 소유자 |
| CK-lnx-U16-002 | file_mode | /etc/passwd 권한 |
| CK-lnx-U34-001 | service_status | Finger 서비스 비활성화 |

구현된 Check type: `config_value`, `service_status`, `account_uid`, `file_owner`, `file_mode`.
미구현: `package_version`(value_ref), `document`(manual).

---

## 3. 실행 흐름

```
CLI (check-id)
    ↓
Loader — data/checks/linux/*.yaml 에서 Check 조회
    ↓
Runner
    ├─ Collector — targets 수집 (config_value: 파일 읽기 → key 값 추출)
    ├─ Evaluator — expect 평가 (관측값 vs 기대값)
    └─ Result 생성
```

각 단계는 독립 함수/모듈로 분리한다.

---

## 4. 코드 구조

```
engine/
├── __init__.py
├── model.py       # ResultStatus, Result
├── loader.py      # Check YAML 로드·조회
├── collector.py   # config_value 수집 (파일 → key 값)
├── evaluator.py   # expect 평가 (leaf op + all/any/not)
├── runner.py      # 수집 → 평가 → 결과 조율
└── cli.py         # CLI 진입점
tests/
└── test_runner.py # fixture 기반 테스트
```

실행:

```bash
python -m engine.cli CK-lnx-U01-001
```

---

## 5. Result 상태 모델

Specification의 6종 상태를 사용하되, 이번 슬라이스에서 실제 발생하는 것은 다음이다.

| 상태 | 의미 |
| --- | --- |
| `PASS` | 관측값이 기대값을 만족 |
| `FAIL` | 관측값이 기대값을 만족하지 않음(취약) |
| `NOT_APPLICABLE` | 점검 대상 파일이 존재하지 않음 |
| `ERROR` | 파일 읽기 실패·파싱 실패·잘못된 Spec |

`NOT_SUPPORTED`(미구현 type), `MANUAL_REQUIRED`(manual/semi)는 이번엔 발생하지 않지만 enum으로 정의해 둔다.

### FAIL vs ERROR (중요)

- **FAIL**: 값을 정상 수집·평가했고 결과가 취약(예: `PermitRootLogin yes`).
- **ERROR**: 수집·평가 자체가 실패해 판정 불가(예: 읽기 권한 없음, 파싱 실패).

---

## 6. 오류 처리 규칙

| 상황 | 결과 상태 | 비고 |
| --- | --- | --- |
| precondition 불충족 | `NOT_APPLICABLE` | Check가 선언한 적용성 미충족 |
| precondition 충족 + 필수 파일 없음 | `ERROR` | 적용 대상이나 판정 불가 |
| precondition 없음 + 파일 없음 | `NOT_APPLICABLE` | 기존 U-01-001 동작 유지 |
| 파일 읽기 실패(권한·IO) | `ERROR` | 수집 불가 |
| key(설정)가 없음 | `FAIL` | 명시적 차단 없음(기본값 의존) |
| 값 파싱 실패 | `ERROR` | 수집값 해석 불가 |
| 잘못된 Check Spec | `ERROR` | 필수 필드 누락/type 미지원 |
| `PermitRootLogin=yes` 등 | `FAIL` | 정상 평가, 취약 |
| `PermitRootLogin=no` | `PASS` | 정상 평가, 양호 |

> `precondition`은 Check가 "이 환경에 적용되는가"를 스스로 선언하는 선택적 필드다.
> "파일 없음"을 무조건 NOT_APPLICABLE로 처리하지 않고, precondition이 적용성을 결정한다.

> "key 없음 → FAIL"의 근거: U-01의 의미는 "root 직접 접속 **차단**"이며, 설정이 없으면 명시적으로 차단되지 않은 상태이므로 취약으로 본다.
> (OpenSSH 기본값이 버전에 따라 `prohibit-password`일 수 있으나, 이는 "키 기반 root 접속 허용"으로 엄밀히는 완전 차단이 아니다.)

---

## 7. config_value 수집

### 흐름

```
target: config(path, key)
    ↓
파일 읽기
    ↓
key(PermitRootLogin)의 유효 값 추출
    ↓
관측값 반환
```

### SSH 설정 파싱 규칙 (`/etc/ssh/sshd_config`)

- 한 줄씩 읽는다.
- 앞뒤 공백 제거 후, 빈 줄·주석(`#`로 시작)은 무시한다.
- 공백 기준으로 분리: 첫 토큰 = 지시자(keyword), 나머지 = 값(value).
- 지시자가 대상 `key`와 일치하면 값을 기록하고, **마지막으로 나타난 값이 유효값**(last-wins)이다.
- 값은 첫 토큰을 사용한다(단일 값 지시자 전제).

예:

```
PermitRootLogin yes           → "yes"
PermitRootLogin no            → "no"
PermitRootLogin prohibit-password → "prohibit-password"
#PermitRootLogin yes          → 주석이므로 무시
PermitRootLogin No            → "No" (원문 보존)
```

- 대소문자: **값 비교는 case-insensitive**로 처리한다. (`eq`에서 양쪽을 lower-case로 정규화)
- OpenSSH의 전체 문법(예: `Match` 블록, 여러 값 지시자)은 이번 단계에서 구현하지 않는다.

### key 생략 → 전체 내용 수집

config target에서 `key`를 생략하면 파일 전체 내용을 관측값으로 반환한다. key=value가 아닌 파일(예: `/etc/pam.d/login`의 모듈 포함 여부, `/etc/securetty`의 pts 항목)에 `contains`/`not_contains`를 적용할 때 사용한다.

```yaml
targets:
  - { kind: config, path: /etc/securetty }   # key 없음 → 전체 내용
expect:
  op: not_contains
  value: "pts"
```

---

## 8. expect 평가

Specification의 리프·결합 구조를 따른다.

### 리프

| op | 동작 |
| --- | --- |
| `eq` | 관측값 == 기대값 (문자열은 case-insensitive) |
| `ne` | 관측값 != 기대값 |
| `contains` / `not_contains` | 부분 문자열 포함 / 미포함 |
| `in` / `not_in` | 목록 포함 / 제외 |
| `exists` | 대상 존재 여부 |
| `le`/`lt`/`ge`/`gt` | 수치 비교 (이번 슬라이스 미사용) |
| `matches` | 정규식 (이번 슬라이스 미사용) |

### 결합

```yaml
expect: { all: [...] }   # 모두 참
expect: { any: [...] }   # 하나라도 참
expect: { not: {...} }   # 부정
```

이번 슬라이스는 `eq` 리프만 사용하지만, 평가기는 결합 구조를 재귀적으로 처리하도록 구현한다(하드코딩 금지).

### value_ref

`value_ref`가 있는 리프는 이번 단계에서 해석하지 않는다 → `NOT_SUPPORTED` 처리.

---

## 8-1. service_status 수집

`type: service_status`는 서비스가 **실제 사용 중인지** 판별한다.

- 관측값: `enabled`(사용 중) / `disabled`(미사용).
- Evidence의 `detail`에 메커니즘별 상태(존재/enabled/active)를 기록한다.

| mechanism | 상태 판별 (파일 기반, 테스트 가능) | 사용 중으로 보는 상태 |
| --- | --- | --- |
| `systemd` | `active`(런타임 마커) / `enabled`(wants 링크) / `masked`(/dev/null) / `disabled` / `not_installed` | `active` |
| `xinetd` | `enabled`(`disable=no`) / `disabled`(`disable=yes`) / `not_installed` | `enabled` |
| `inetd` | `enabled`(주석 없음) / `disabled`(주석) / `not_installed` | `enabled` |

- systemd는 "active(실행 중)"일 때만 사용 중으로 본다. `enabled`(auto-start)지만 inactive면 미사용이다.
- xinetd/inetd는 슈퍼서버 모델이므로 `enabled`가 곧 사용 가능(사용 중)이다.
- 판단 근거는 Evidence `detail`에 `systemd=active, xinetd=not_installed, inetd=not_installed` 형태로 남긴다.

> systemd의 `active`는 런타임 확인(`systemctl is-active`)이 필요하므로, 이번 슬라이스에서는
> `<root>/run/systemd/<name>.active` 마커 파일을 active 프록시로 사용한다(테스트 가능성 확보).

## 8-2. precondition

Check가 "이 환경에 적용되는가"를 선언하는 선택적 필드다.

```yaml
precondition:
  type: service_status
  targets: [{ kind: service, name: telnet, mechanisms: [...] }]
  expect: { op: eq, value: enabled }
```

- precondition 평가가 False면 → `NOT_APPLICABLE`(Check 적용 안 됨).
- True면 → 본 Check의 targets/expect를 계속 평가한다.

---

## 9. Evidence

Evidence는 **Result를 판단하기 위해 실제로 관찰한 사실**을 남긴다. 종합 판정값은 Evidence에 넣지 않는다.

### 공통 구조

모든 Evidence 항목은 다음 구조를 따른다.

| 필드 | 의미 |
| --- | --- |
| `target` | 관찰 대상(파일 경로/서비스/메커니즘) |
| `attribute` | 관찰 속성(설정 항목/속성명) |
| `observed` | 실제 관찰값(raw observation) |
| `expected` | 기대값(단일값 `eq`/`ne` 비교일 때만) |

- config_value: `target=경로`, `attribute=설정키`, `observed=원시값`, `expected=기대값`.
- service_status: 각 관찰 사실을 별도 항목으로 나눈다(아래 표).

`service_status`의 Evidence 항목:

| target | attribute | observed |
| --- | --- | --- |
| `systemd` | `<name>.service` | active/enabled/masked/disabled/not_configured/not_present |
| `xinetd` | `<name>` | enabled/disabled/not_configured/not_present |
| `inetd` | `<name>` | enabled/disabled/not_configured/not_present |
| `<name>d` | process | running/not_running |
| `tcp/23` | listening | yes/no |

- `not_present`는 "해당 서비스 매니저가 없음"이며, 그 자체로 "Telnet 미사용"의 근거가 아니다.
- "미사용"은 Result(PASS/FAIL)가 결정하며, Evidence에는 사실만 남긴다.
- 런타임 확인은 서비스 매니저와 무관한 "실제 실행" 신호로, 테스트용 마커(`/run/<name>.pid`, `/run/<name>.listening`)를 사용한다.
- NOT_APPLICABLE은 적용되지 않은 이유(전제조건 결과 참조 + 관찰 사실)를 Evidence에 포함한다.

민감 정보는 전체 출력하지 않는다(이번 Check는 비민감 값).

---

## 10. CLI

```bash
python -m engine.cli CK-lnx-U01-001
```

출력:

```
Check: CK-lnx-U01-001
Description: SSH 서버의 root 직접 원격 접속 허용 여부 확인
Result: PASS
Evidence: path=/etc/ssh/sshd_config key=PermitRootLogin observed=no
```

오류 시 `message`를 함께 출력한다.

---

## 11. 테스트

실제 `/etc/ssh/sshd_config`를 수정하지 않고 **임시 fixture 파일**로 테스트한다.

| 케이스 | fixture 내용 | 기대 결과 |
| --- | --- | --- |
| 정상 PASS | `PermitRootLogin no` | PASS |
| FAIL | `PermitRootLogin yes` | FAIL |
| 주석 처리 | `#PermitRootLogin yes` | FAIL (유효값 없음 → key 미설정) |
| last-wins | `PermitRootLogin yes` + `PermitRootLogin no` | PASS |
| 파일 없음 | (존재 안 함) | NOT_APPLICABLE |
| key 없음 | `Port 22` | FAIL |
| 대소문자 | `PermitRootLogin No` | PASS |

테스트는 표준 라이브러리 `unittest`를 사용하고, 임시 디렉터리에 fixture 파일을 생성한다.

---

## 12. 이번 단계에서 하지 않을 것

- U-02 ~ U-67 구현
- config_value/service_status 외 type 구현(file_mode/account/package 등)
- value_ref 해석
- 매핑(kisa-to-check) 집계
- ISMS-P 최종 판단
- DB·웹·Docker·플러그인 구조

> **KISA U-01 Check 결과는 ISMS-P 인증 PASS를 의미하지 않는다.** 이번 결과는 순수한 Technical Check Result다.
