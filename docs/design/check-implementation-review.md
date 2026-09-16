# Technical Check 구현 전체 리뷰

> 현재 구현된 Technical Check와 Engine(Collector/Evaluator/Runner/CLI)이
> Check Specification / Result / Message / Evidence 설계와 일관되고 확장 가능한지 검증한다.
> 이 문서는 리뷰 결과만 기록하며, 이번 단계에서 코드를 수정하지 않는다.

심각도 기준: P0(설계 결함) / P1(정확성·증적 신뢰성) / P2(일관성·유지보수성) / P3(개선 권장)

---

## 1. 계층 흐름 점검

```
Check Specification  →  Collector  →  Raw Observation  →  Evaluator  →  Result  →  Message + Evidence
```

- **역할 분리**: 대체로 양호하다. Collector가 raw 사실을 수집하고, Evaluator가 `expect`와 비교해 Result를 내며, Evidence는 Collector의 관찰값으로 구성된다.
- **Message 생성**: `runner._result_message`가 type별로 생성한다. 단순하지만, type별 분기 하드코딩이 늘어나는 구조다(아래 P2-1).

---

## 2. Evidence 공통 구조 점검

공통 구조 `target / attribute / observed [/ expected]`는 모든 Check에 일관 적용되어 있다.

- **raw observation**: `yes`/`0644`/`root`/`not_running`/`not_present`/`none` 등 raw에 가깝다. 위반은 U-01-003의 `observed=PASS`(참조값, P2)가 유일하다.
- **target 명확성**: 파일 경로, `systemd`, `xinetd`, `inetd`, `tcp/23`, `tcp/79`, `telnetd`/`fingerd` 모두 이해 가능하다.
- **attribute 명확성**: `owner`/`mode`/`PermitRootLogin`/`process`/`listening`/`uid` 적절하다. 단, config 전체 내용 검사에서 `attribute=content`는 지나치게 일반적이다(P1-2).
- **expected 누락**: file_mode(`observed=0644`에 expected 없음), config contains/not_contains에서 조건 누락(P1-2/P1-3).

---

## 3. Result 상태 점검

| 상태 | 사용 | 평가 |
| --- | --- | --- |
| PASS/FAIL | 전 Check | 적절 |
| NOT_APPLICABLE | U-01-003(전제조건 불충족) | 정상(Error 아님)으로 처리됨 ✓ |
| ERROR | 파일 접근/파싱 실패, 정의 오류 | 적절 |
| NOT_SUPPORTED | U-64-002(package_version) | 적절하나 사유 표현 부정확(P3) |
| MANUAL_REQUIRED | U-64-001(document) | 적절 |

---

## 4. Cross-cutting 이슈

### P1-1. `eq`/`ne`의 전역 대소문자 무시

`evaluator._eq`가 문자열이면 항상 `.lower()`로 비교한다. SSH `No` vs `no` 사례를 위해 도입했지만, 향후 대소문자를 구분해야 하는 값(사용자명·해시·경로 등)을 비교하는 Check에서 오판을 유발한다. **config_value 전용 정규화**로 한정하거나, op 단위로 케이스 정책을 명시해야 한다.

### P1-2. file_mode의 `expected` 누락

U-16-002 Evidence는 `observed=0644`만 남긴다. 사람은 "왜 PASS인지"(허용 마스크가 644)를 Evidence만으로 알 수 없다. `mode_allowed`를 `expected=0644` 또는 `expected=rw-r--r--` 형태로 Evidence에 남길 필요가 있다.

### P1-3. config 전체 내용 검사의 증적 부족

U-01-003(사용 시)은 `contains pam_securetty.so` / `not_contains pts`를 검사하지만, Evidence는 `attribute=content, observed=<파일 전체>`만 남긴다. 어떤 문자열 포함 여부를 검사했는지(`expected`/조건)가 없어, PASS/FAIL 근거가 불명확하다.

### P1-4. "파일 없음 → NOT_APPLICABLE" (비전제조건)

precondition이 없는 Check(U-16 등)에서 대상 파일이 없으면 `NOT_APPLICABLE`을 반환한다. `/etc/passwd` 부재는 "적용 불가"가 아니라 **심각한 오류**여야 한다. (이전 리뷰에서 이미 지적된 미해결 사항)

### P2-1. `expected` 추출/적용의 하드코딩

- `expected` 추출이 `ctype in ("config_value", "file_owner")`로 type에 하드코딩돼 있다. expect 구조(eq/ne)가 기준이 되어야 한다.
- 추출된 `expected`가 Check의 **모든 observation에 동일하게** 적용된다. 다중 target + 서로 다른 기대값이 필요한 Check가 생기면 잘못된 expected가 붙는다.

### P2-2. U-01-003 NOT_APPLICABLE의 `observed=PASS` 하드코딩

`_run_precondition`이 참조 Evidence를 만들 때 `observed="PASS"`를 하드코딩한다. 전제조건의 실제 평가 결과에서 파생하지 않고, 다른 유형의 전제조건에는 맞지 않을 수 있다.

### P2-3. config 복합 조건의 Message가 일반적

U-01-003 사용 시 PASS/FAIL Message가 "조건을 충족함/충족하지 않음"이다. 어떤 조건인지(어느 파일·어느 문자열) 알 수 없다.

---

## 5. Check별 리뷰

### CK-lnx-U01-001 (config_value, SSH root 접속)

1. **목적**: SSH `PermitRootLogin`이 차단(`No`)인지 확인.
2. **정의 적절성**: 단일 target + `eq`로 명확. 적절.
3. **Evidence**: `target=/etc/ssh/sshd_config attribute=PermitRootLogin observed=yes expected=No` — 모범적.
4. **Result**: PASS/FAIL 적절.
5. **Message**: "PermitRootLogin 값이 기대값(No)과 다름 (관찰값: yes)" — raw 수준, 이해 가능. (더 친절하게 "root 직접 원격 접속이 허용됨"으로 바꿀 여지는 P3)
6. **Collector**: config key 추출(last-wins, 주석 무시) 적절.
7. **Evaluator**: `eq`(대소문자 무시) — P1-1에 해당.
8. **테스트**: PASS/FAIL/주석/대소문자/evidence 검증. 양호.
9. **문제점**: P1-1(대소문자).
10. **개선 제안**: eq 케이스 정책 한정.

### CK-lnx-U01-002 (service_status, Telnet 사용 여부)

1. **목적**: Telnet 서비스가 실제 사용 중인지 확인.
2. **정의 적절성**: systemd/xinetd/inetd/런타임 종합. 적절.
3. **Evidence**: 메커니즘별 + 런타임 5개 항목. raw 적절.
4. **Result**: PASS(미사용)/FAIL(사용) 적절.
5. **Message**: "telnet 서비스를 사용하지 않음" — 명확.
6. **Collector**: 각 메커니즘 상태 판별 적절.
7. **Evaluator**: `eq disabled`(단일값) 적절.
8. **테스트**: 상태별로 광범위. 양호.
9. **문제점**: 없음(주요). `eq` 대소문자(P1-1) 정도.
10. **개선 제안**: 없음.

### CK-lnx-U01-003 (config_value + precondition, Telnet root 제한)

1. **목적**: Telnet 사용 시 root 직접 접속 차단 확인.
2. **정의 적절성**: precondition(Telnet 사용) + config 전체 내용 2개. 구조는 적절.
3. **Evidence**: N/A 시 참조+사실 잘 남음. 단 `observed=PASS` 하드코딩(P2-2). 사용 시 `attribute=content`(P1-3).
4. **Result**: NOT_APPLICABLE을 정상 상태로 처리 ✓.
5. **Message**: N/A "…사용하지 않아 적용되지 않음" ✓. 사용 시 "조건을 충족함"(P2-3).
6. **Collector**: config 전체 내용 수집(contains용) 동작.
7. **Evaluator**: `all(contains, not_contains)` 재귀 평가 적절.
8. **테스트**: N/A/PASS/FAIL/ERROR 검증. 양호.
9. **문제점**: P2-2, P1-3, P2-3.
10. **개선 제안**: precondition 참조값 파생, config 증적에 조건 명시.

### CK-lnx-U05-001 (account_uid, UID 0 계정)

1. **목적**: root 외 UID 0 계정 존재 여부.
2. **정의 적절성**: `exclude: [root]` + `not_in [0]`. 적절.
3. **Evidence**: `target=/etc/passwd attribute=uid observed=none`(또는 계정명). `none`은 raw 요약(P3).
4. **Result**: PASS/FAIL 적절.
5. **Message**: "UID 0 계정이 존재하지 않음/존재함" — FAIL 시 계정명 미포함(P3).
6. **Collector**: /etc/passwd 파싱(주석·형식 처리) 적절.
7. **Evaluator**: `not_in` — 문자열 정규화로 int/str 불일치 해결(P3).
8. **테스트**: PASS/FAIL. 양호.
9. **문제점**: P3(observed="none" 해석, FAIL 메시지에 계정명 없음, `_in` 정규화).
10. **개선 제안**: FAIL Message에 관찰 계정명 포함.

### CK-lnx-U16-001 (file_owner, /etc/passwd 소유자)

1. **목적**: /etc/passwd 소유자 = root.
2. **정의 적절성**: `eq root`. 적절.
3. **Evidence**: `observed=root expected=root` — 적절.
4. **Result**: PASS/FAIL 적절.
5. **Message**: "소유자가 기대값(root)과 일치함/다름" — 적절. (getpwuid 실패 시 관찰값이 숫자 UID로 표시되는 것은 P3)
6. **Collector**: stat + getpwuid. 적절(미존재 UID fallback).
7. **Evaluator**: `eq`. (대소문자 P1-1은 owner 비교에선 무해)
8. **테스트**: chown 기반 PASS/FAIL. 양호.
9. **문제점**: P1-4(파일 없음 → N/A), P3(UID fallback 표시).
10. **개선 제안**: 필수 파일 부재 처리 재검토.

### CK-lnx-U16-002 (file_mode, /etc/passwd 권한)

1. **목적**: /etc/passwd 권한이 허용 범위(644) 이하.
2. **정의 적절성**: `mode_allowed`(permission semantics) 적절.
3. **Evidence**: `observed=0644` — **expected/허용범위 누락(P1-2)**.
4. **Result**: PASS/FAIL 적절.
5. **Message**: "권한이 허용 범위 내/벗어남" — 이해 가능하나 허용 범위 미표시.
6. **Collector**: stat mode 추출(4자리 octal) 적절.
7. **Evaluator**: 비트 마스크 서브셋(`mode & ~mask == 0`) — permission semantics 정확.
8. **테스트**: chmod 기반 PASS/FAIL. 양호.
9. **문제점**: P1-2(허용범위 미표시), P1-4.
10. **개선 제안**: `mode_allowed`를 Evidence에 허용 마스크로 표기.

### CK-lnx-U34-001 (service_status, Finger 비활성화)

U-01-002와 동일한 service_status 구조. Evidence에 `tcp/79`(finger 포트)가 올바르게 표기됨.
9. **문제점**: 없음(주요).
10. **개선 제안**: 없음.

### CK-lnx-U64-001 (document, 패치 정책 — manual)

1. **목적**: 패치 적용 정책 문서 존재 여부.
2. **정의 적절성**: `document` type + `manual`. 적절.
3. **Evidence**: 실행 전 MANUAL_REQUIRED로 반환되어 Evidence 없음. (manual이라 수집 자체를 안 하는 것은 의도된 설계)
4. **Result**: MANUAL_REQUIRED 적절.
5. **Message**: "manual Check는 자동 실행 대상이 아님" — 기술적 표현(P3).
6. **Collector/Evaluator**: 미실행.
8. **테스트**: 미검증(manual 경로).
9. **문제점**: P3(메시지).
10. **개선 제안**: 사람이 이해하기 쉬운 문구로.

### CK-lnx-U64-002 (package_version, 패치 버전 — semi/미구현)

1. **목적**: 커널 보안 패치 최신 버전 확인.
2. **정의 적절성**: `package_version` + `value_ref`(외부 기준). 적절하나 미구현.
3. **Evidence**: 없음(NOT_SUPPORTED).
4. **Result**: NOT_SUPPORTED 적절.
5. **Message**: "지원하지 않는 Check type: 'package_version'" — 실제 사유는 `value_ref` 미구현(P3).
6. **Collector/Evaluator**: `value_ref` 해석 미구현.
9. **문제점**: P3(사유 표현), value_ref 미구현은 설계상 남은 과제.
10. **개선 제안**: 사유를 "value_ref(외부 기준) 미구현"으로 명확히.

---

## 6. 우선순위 요약

| 심각도 | 이슈 |
| --- | --- |
| P1 | eq/ne 전역 대소문자 무시 (향후 case-sensitive Check 오판 위험) |
| P1 | file_mode의 허용 범위(expected) 미표시 |
| P1 | config 전체 내용 검사의 조건(contains/not_contains) 미표시 |
| P1 | 비전제조건 Check의 "파일 없음 → NOT_APPLICABLE"(/etc/passwd 부재 등) |
| P2 | expected 추출·적용의 type 하드코딩 + 다중 target 시 오적용 잠재 |
| P2 | U-01-003 N/A 참조 Evidence의 observed=PASS 하드코딩 |
| P2 | config 복합 조건의 Message 일반화 |
| P3 | U-05 observed="none" / FAIL 메시지 계정명 누락 / _in 정규화 |
| P3 | U-64-001/002 Message 문구 개선 |

---

## 7. 결론

- **설계 방향은 견고하다.** Result/Message/Evidence 역할 분리, raw observation 원칙, 공통 Evidence 구조가 9개 Check에 일관 적용되어 있다.
- **확장 가능성**: Collector가 target kind 단위로 분기하고, Evaluator가 리프/결합을 재귀 처리하므로 새 type 추가가 용이하다.
- **개선 우선순위**: P1 이슈(특히 eq 케이스 정책, file_mode/config 증적의 조건 명시)가 향후 결과 신뢰성에 영향을 줄 수 있으므로, 다음 구현 단계에서 우선 정리하는 것이 좋다.

---

## 8. 수정 결과 (P1/P2 반영)

| # | 이슈 | 상태 | 변경 |
| --- | --- | --- | --- |
| P1-1 | eq/ne 전역 대소문자 무시 | FIXED | `eq` 기본 case-sensitive로 변경, 리프에 `case_insensitive: true` 옵션 추가. `engine/evaluator.py`, U-01-001 YAML |
| P1-2 | file_mode 허용 범위 미표시 | FIXED | `mode_allowed` → 허용 마스크(`expected=0644`)로 Evidence 표기. `engine/runner.py`, `engine/evaluator.py` |
| P1-3 | config 복합 조건 미표시 | FIXED | contains/not_contains를 `attribute=contains/not_contains` + `observed=true/false` + `expected=검색어`로 표현. `engine/runner.py` |
| P1-4 | 파일 없음 → NOT_APPLICABLE | FIXED | 대상 파일 없음 → `ERROR`(점검 불가). precondition 미충족만 `NOT_APPLICABLE`. `engine/runner.py` |
| P2-1 | expected 추출 type 하드코딩 | FIXED | expect 구조(eq/ne/mode_allowed) 기반 `_expected_for` + kind별 `_build_evidence`로 분리. `engine/runner.py` |
| P2-2 | precondition 참조 PASS 하드코딩 | FIXED | 선행 Check(`ref`)를 실제 실행해 Result 값을 사용. `engine/runner.py` |
| P2-3 | config 복합 조건 Message 일반화 | FIXED | description 기반 주어("…조건을 충족함/충족하지 않음")로 구체화. `engine/runner.py` |

P3 이슈는 DEFERRED(현재 사용에 문제 없음, 추후 개선).

### 전체 Check 작성 전에 해결해야 할 설계 문제

1. `value_ref`(외부 기준: 취약점 DB/벤더 권고) 해석 — `package_version`(U-64-002) 구현 전 필수.
2. KISA Item ↔ Check 결과 집계 규칙(AND/OR, NOT_APPLICABLE 처리) — 아직 정의 안 됨.
3. `document`(정책/절차) Check의 증적 수집·표현 방식(현재 MANUAL_REQUIRED로 즉시 반환).

### 현재 모델로 전체 Check 작성을 시작해도 되는가?

**가능하다.** 근거:
- 9개 Check가 Result/Message/Evidence 모델을 일관 적용하고, 38개 테스트가 모두 통과한다.
- Collector(kind 분기)와 Evaluator(리프/결합 재귀 + permission semantics)가 확장 가능한 구조다.
- 남은 P3 이슈와 value_ref/document는 특정 type에 국한되어, 나머지 Check(type: config_value/service_status/file_owner/file_mode/account_uid 등) 작성에는 영향을 주지 않는다.

단, `value_ref`를 쓰는 Check(패치·버전 계열)와 `document` Check는 해당 기능 구현 전까지 DEFERRED로 둔다.

### 아직 구현되지 않은 Check type 목록

| type | 사유 |
| --- | --- |
| `package_version` | `value_ref`(외부 기준값) 미구현 |
| `document` | manual 증적 수집 방식 미정(현재 MANUAL_REQUIRED 반환) |
| `process_running` | 수집기 미구현(서비스 런타임 프록시와 동일하게 구현 가능) |
| `account_gid` / `account_shell` / `account_duplicate` | account 수집기 확장 필요 |
| `command_output` | 명령 실행·파싱 미구현 |
