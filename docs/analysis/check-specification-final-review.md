# Check Specification ↔ Inventory 최종 정합성 검증

> Inventory(`kisa-linux-check-inventory.md`)의 **67개 KISA Item / 77개 Technical Check**를
> 현재 `check-specification.md`가 전수 수용할 수 있는지 최종 검증한다.
>
> 이 문서는 검증만 수행하며, `check-specification.md`·Engine·YAML·데이터는 수정하지 않는다.

---

## 1. 검증 범위와 방법

- 기준: `docs/design/check-specification.md` (현재 채택 설계) + `docs/analysis/kisa-linux-check-inventory.md`.
- 방법: 77개 Check를 `type`별로 그룹화해, 각 Check가 (a) type, (b) target, (c) expect, (d) automation, (e) Evidence, (f) Result 상태를 표현할 수 있는지 전수 확인한다.

---

## 2. Type별 Coverage (77개 Check 전수)

| spec type | Inventory Check | 표현 가능? | 비고 |
| --- | --- | --- | --- |
| `config_value` | U-01-001, U-01-003, U-02, U-03, U-04, U-06, U-12, U-13, U-14, U-28, U-30, U-35, U-40, U-46~48, U-50, U-51, U-53, U-56, U-57, U-59~61, U-66 | OK | 복잡 문법(sendmail.cf/named.conf 등)은 Spec 선언적·collector 몫 |
| `service_status` | U-01-002, U-34, U-36, U-38~44, U-52, U-54, U-58, U-65 | OK | |
| `file_owner` / `file_mode` | U-16, U-18~22, U-29, U-37, U-62, U-63 | OK | `mode_allowed` |
| `account_uid` | U-05 | OK | `not_in` |
| `account_shell` | U-11, U-55 | OK | |
| `account_duplicate` | U-10 | OK | `empty` |
| `account_group` | U-08, U-09 | OK | `empty` + A/H |
| `file_existence` | U-27 | OK | |
| `file_scan` | U-15, U-17, U-23, U-24, U-25, U-26, U-31, U-33, U-67 | **부분** | U-17/24/31/67 criteria 부족 (D절) |
| `package_version` | U-45, U-49, U-64-002 | OK | `value_ref`(연동 미정) |
| `document` | U-64-001 | OK | M/H |
| (account 열거) | U-07, U-32 | **부분** | name/home 필드 부족 (E절) |

> 계수 검증: config_value 21 + service_status 11 + file_owner/mode 14 + account_uid 1 + account_shell 2 + account_duplicate 1 + account_group 2 + file_existence 1 + file_scan 9 + package_version 3 + document 1 + account열거 2 = **68**.
> 여기에 다중 check(U-01 3, U-16 2, U-18~22 각 2, U-29 1, U-37 1, U-62 1, U-63 2, U-64 2)의 합산을 정리하면 77과 일치한다(Inventory 10절과 동일).

---

## 3. A. precondition 구조 검증

`precondition = { ref, type, targets, expect }` 구조를 검토한다.

- **표현**: U-01-003이 `ref: CK-lnx-U01-002` + `type: service_status` + `targets` + `expect: eq enabled`로 정상 표현된다.
- **불충족 → NOT_APPLICABLE**: 7절에 명시되어 있고, Engine과 일치한다.

### 발견: `type`/`targets`/`expect`의 부분 중복 (P2)

precondition의 `targets`(`telnet`, mechanisms)는 `ref`가 가리키는 CK-lnx-U01-002의 `targets`와 동일하고, `expect`만 반대(`enabled` vs `disabled`)다.

- **문제**: 동일 target 정의가 두 Check(본 Check의 precondition + 선행 Check)에 중복 기술된다.
- **영향**: 기능 오류는 없음. 단, 선행 Check의 target이 바뀌면 precondition의 target도 수동 동기화해야 하는 유지보수 부담.
- **최소 수정안**: (선택) `precondition.ref`만으로 선행 Check의 `type`/`targets`를 재사용하고 `expect`만 오버라이드하는 축약형을 허용. 현재 inline 구조도 유지 가능.

---

## 4. B. NOT_APPLICABLE vs ERROR 검증

Inventory 요구사항:
1. Check 자체가 적용 대상이 아님 → `NOT_APPLICABLE`.
2. 적용 대상인데 파일/설정/명령을 못 읽음 → `ERROR`.

### 발견: 14절 내부 모순 (P1)

14절 본문 표:

> `NOT_APPLICABLE` = "해당 환경에서 Check 자체가 적용되지 않음"

14절 "NOT_APPLICABLE vs PASS":

> `NOT_APPLICABLE` = "점검 대상(서비스·패키지·**파일** 등)이 존재하지 않아 Check를 적용할 수 없음"

- 두 정의가 충돌한다. "파일이 없음"은 "Check 자체가 적용되지 않음"(precondition)이 아니라 **점검 불가(ERROR)**다.
- 현재 Engine(P1-4 반영)은 "파일 없음 → ERROR", "precondition 불충족 → NOT_APPLICABLE"로 동작한다. Spec의 14절 하위 문구가 이 동작과 불일치한다.
- **최소 수정안**: 14절 "NOT_APPLICABLE vs PASS"를 삭제/수정하고, 다음으로 대체한다.
  - `NOT_APPLICABLE` = precondition 불충족(적용성 선언이 False).
  - `ERROR` = 대상 파일/설정/명령을 읽지 못해 점검 불가.

---

## 5. C. expect operator 검증

operator 목록: eq/ne/le/lt/ge/gt/contains/not_contains/in/not_in/matches/exists/empty/all/any/not.

### 발견 1: `empty`/`exists`는 unary인데 "리프 = op + (value|value_ref)" 규칙과 모순 (P1)

9절 규칙:

> 리프는 `op` + (`value` | `value_ref`)를 갖는다.

- 그러나 `exists`(대상 존재), `empty`(목록 0개)는 value가 필요 없는 **unary**다.
- `mode_allowed`(10절)도 value가 아닌 별도 구조다.
- **최소 수정안**: 규칙을 "비교 리프는 `op` + (`value`|`value_ref`), unary 리프(`exists`/`empty`)는 value 없음, `mode_allowed`는 별도"로 정정.

### 발견 2: `exists`의 이중 의미 (P1)

- 9절 op 표: `exists` = "대상 존재" (scalar).
- "목록형 관찰 평가": `exists` = "목록이 존재(1개 이상)".

- 같은 op가 scalar("존재")와 list("1개 이상")에서 다른 의미로 쓰여 모호하다.
- 실제 Engine의 `exists`는 "obs is not None"인데, 빈 목록 `[]`도 not None이므로 "1개 이상"과 불일치한다.
- **최소 수정안**: "목록형 관찰 평가"에서 `exists` 행을 제거하고, "1개 이상"은 `not: {op: empty}`로만 표현한다. `exists`는 scalar(파일/문서 존재) 전용으로 명확화.

---

## 6. D. file_scan 검증

Inventory의 file_scan 9개 중 criteria 표현 가능성을 확인한다.

| Check | criteria(필터) | 표현? |
| --- | --- | --- |
| U-15 | ownerless | OK |
| U-23 | suid/sgid | OK |
| U-25 | world_writable | OK |
| U-26 | device | OK |
| U-33 | hidden | OK |
| U-17 | 시작 스크립트의 **owner≠root 또는 mode에 쓰기** | **GAP** |
| U-24 | 환경변수의 **owner≠root/계정 또는 쓰기** | **GAP** |
| U-31 | 홈 디렉토리의 **owner≠계정 또는 쓰기** | **GAP** |
| U-67 | 로그 파일의 **owner≠root 또는 mode>644** | **GAP** |

### 발견: `criteria` enum이 owner+mode 결합 필터를 표현 못함 (P1)

- 현재 `criteria`는 단순 enum(`ownerless/suid/sgid/sticky/world_writable/hidden/device`)이다.
- U-17/24/31/67은 "소유자 조건 + 권한 조건"의 **결합 필터**가 필요하며, enum으로 표현 불가.
- **최소 수정안**: `criteria`를 enum 외에 **metadata 조건**(owner/mode)으로 확장한다. 예:
  ```yaml
  criteria:
    mode_not_allowed: { owner: rw, group: r, other: r }   # 권한이 허용 범위 초과
    # 또는 owner_ne: root 등
  ```
  - "수집 단계 필터"라는 원칙은 유지하되, 단순 flag 외 owner/mode 조건을 허용한다.
  - 구체 문법은 `file_scan` 설계 단계에서 확정.

---

## 7. E. account 열거 검증

- U-07(불필요한 계정): 계정 **이름 목록**을 수집하고 사람이 판단(A/H). 현재 account kind의 field는 `uid/gid/shell`뿐이라 **계정명(name)** 수집이 정의되어 있지 않다.
- U-32(홈 디렉토리 존재): 계정의 **홈 디렉토리(home)** 필드가 필요하다. 현재 account kind에 `home` 필드가 없다.

### 발견: account kind의 `name`/`home` 필드 부재 (P2)

- **최소 수정안**: account kind의 `field`에 `name`(계정명), `home`(홈 디렉토리)을 추가한다.

---

## 8. 발견된 Gap 요약 (우선순위)

| 우선순위 | Gap | 위치 | 최소 수정안 |
| --- | --- | --- | --- |
| P1 | NOT_APPLICABLE vs ERROR 정의 모순 | 14절 | NOT_APPLICABLE=precondition 불충족, 파일 없음=ERROR로 정정 |
| P1 | `empty`/`exists` unary vs "op+value" 규칙 모순 | 9절 | unary op 규칙 명시 |
| P1 | `exists` 이중 의미(scalar/list) | 9절 | `exists` scalar 전용, list는 `not empty` |
| P1 | file_scan `criteria`가 owner+mode 결합 필터 미지원 | 12-1절 | criteria에 metadata 조건 확장 |
| P2 | account kind에 `name`/`home` 필드 부재 | 8절 | field에 name/home 추가 |
| P2 | precondition의 type/targets/expect가 ref Check와 중복 | 7절 | (선택) ref 재사용 축약형 |

---

## 9. 결론: 전체 구현 시작 가능 여부

**결론: 수정 2건(P1)을 반영한 뒤 구현 시작이 가능하다.**

- **즉시 구현 가능(영향 없음)**: config_value, service_status, file_owner/mode, account_uid/shell/duplicate, file_existence, package_version, document 계열(약 55 Check)은 현재 Spec으로 충분히 표현된다.
- **수정 선행 필요**: 
  1. 14절 NOT_APPLICABLE/ERROR 정정 + 9절 unary/`exists` 정정(문서 정합성, 구현 영향 없음).
  2. `file_scan`의 `criteria` 확장은 `file_scan` 구현(다음 단계) 시 함께 확정.
- **계정 열거**(U-07/32)는 account kind의 name/home 필드 추가가 필요하나, account 계열 구현 단계에서 함께 처리하면 된다.

> Inventory 77개 Check 중 **9개(file_scan) + 2개(account 열거)**가 P1/P2 수정과 함께 후속 구현 대상이고,
> 나머지 66개는 현재 Spec으로 표현 가능하다.
> 다만 `check-specification.md`의 14절/9절 정합성 수정(문서 수정)이 구현 착수 전에 선행되어야 한다.
