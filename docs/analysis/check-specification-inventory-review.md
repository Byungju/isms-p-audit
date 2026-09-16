# Check Specification ↔ Inventory 정합성 검토

> `docs/analysis/kisa-linux-check-inventory.md`(67개 KISA Item / 77개 Technical Check)를
> 현재 `docs/design/check-specification.md` 설계가 충분히 수용할 수 있는지 검토한다.
>
> 이 문서는 **검토/분석만 수행**하며, 코드·Check YAML·Engine·check-specification.md는 수정하지 않는다.

---

## 1. 현재 Specification 요약

| 영역 | 핵심 구조 |
| --- | --- |
| Check 필드 | `id` / `type` / `description` / `targets` / `expect` / `automation` / `platforms` / `evidence` |
| Check type | file_mode, file_owner, file_existence, config_value, account_uid, account_gid, account_shell, account_duplicate, service_status, process_running, package_version, command_output, document |
| targets | `kind`: file / config / account / service / process / package / command / document |
| expect | 리프(`op`+`value`/`value_ref`) + 결합(`all`/`any`/`not`). op: eq/ne/le/lt/ge/gt/contains/not_contains/in/not_in/matches/exists |
| file_mode | `mode_allowed`(permission semantics, 비트 마스크) |
| external | `value_ref`: policy / vulnerability_db / vendor_advisory |
| automation | `auto` / `semi`(manual_reason) / `manual` (단일 축) |
| Result | PASS / FAIL / NOT_APPLICABLE / NOT_SUPPORTED / ERROR / MANUAL_REQUIRED |
| Evidence | `target` / `attribute` / `observed` [/ `expected`] |

---

## 2. Inventory 요구사항

Inventory가 Specification에 요구하는 기능:

1. **77개 Check의 분해 표현**: 1개 KISA Item → 1/2/3개 Technical Check.
2. **관찰/판단 분리**: Observation(AUTO/MANUAL) + Assessment(AUTO/HUMAN/EXTERNAL_DATA).
3. **다중 관찰 조합**: AND/OR/NOT, precondition, NOT_APPLICABLE, 다중 target.
4. **file_scan**: 디렉토리 하위 파일 metadata(path/type/uid/gid/owner/mode/size/suid/sgid/sticky) 열거 + 조건 평가.
5. **account 계열**: enumeration, group, duplicate, shell, uid.
6. **복잡 config**: PAM/sendmail.cf/named.conf/snmpd.conf/smb.conf/exports/hosts.allow 등.
7. **External Data**: A/E(U-45/49/64)의 취약 버전 판단.
8. **Evidence**: 여러 target/observation, file_scan 결과, human assessment, external ref, NOT_APPLICABLE, ERROR.

---

## 3. Coverage Matrix

| 요구사항 | 현재 Specification | 상태 | 관련 Check | 문제 |
| --- | --- | --- | --- | --- |
| 단일 config key=value | 지원(config_value) | OK | U-01, U-13, U-30 | 없음 |
| config contains/not_contains | 지원 | OK | U-06, U-57 | 없음 |
| 복잡 config 문법 | 선언적 지원(config `key`/전체내용) | OK(Spec) / NEW_COLLECTOR(Impl) | U-02, U-46~48, U-50, U-51, U-59~61 | Spec은 파서 비종속, 수집 로직은 Implementation |
| AND / OR / NOT | 지원(all/any/not) | OK | U-01-003, U-64 | 없음 |
| precondition | **Engine/YAML 사용, Spec 미문서** | GAP | U-01-003 | 필드가 7절 구조에 없음 |
| NOT_APPLICABLE | Result 상태 지원 | OK(부분) | U-01-003 | precondition→N/A 연계 미문서 |
| file_scan | **미지원** | GAP | U-15, U-17, U-23~26, U-31, U-33, U-67 | type/scan 대상/목록 평가 전부 부재 |
| account enumeration | 부분(account kind + exclude) | GAP | U-07, U-32 | 전체 열거·목록 평가 미표현 |
| account_group | **미지원** | GAP | U-08, U-09 | type 부재 |
| account_duplicate | type 존재 | 부분 | U-10 | 목록 중복 탐지 평가 미검증 |
| account_shell | type 존재 | 부분 | U-11, U-55 | 목록형 평가 미검증 |
| service_status | 지원 | OK | U-34 등 | 없음 |
| file_owner/file_mode | 지원 | OK | U-16 등 | 없음 |
| A/H (관찰A+판단H) | automation: semi + manual_reason | 부분 | U-07 등 | 관찰/판단 2축 미분리 |
| A/E (관찰A+판단E) | value_ref(12절) | 부분 | U-45, U-49 | automation 표현 없이 value_ref로만 |
| M/H (관찰M+판단H) | automation: manual | OK | U-64 | 없음 |
| 목록형 평가(count/empty/중복) | **미지원**(in/not_in만) | GAP | file_scan, account | count==0, empty, duplicate 미표현 |
| Evidence 다중 관찰 | 리스트 지원 | OK | 전 Check | 없음 |
| Evidence 목록형 observed | 부분 | GAP | file_scan | observed가 파일 목록인 경우 표현 |
| NOT_APPLICABLE 근거 Evidence | 미문서 | GAP | U-01-003 | precondition 근거 Evidence 규약 없음 |
| `source` 필드 | **의도적 제외**(KISA 파생 SSOT) | OK(의도) | 전 Check | 검토 대상 목록에 있으나 spec에 없음은 의도 |

---

## 4. Critical Gaps

### P0 — 설계상 반드시 수정

**GAP-1: `precondition` 필드 미문서화**

- 현재 Engine(`runner.py`)과 Check YAML(U-01-003)은 `precondition`을 사용하지만,
  `check-specification.md` 7절(Check 구조)에는 `precondition`이 없다.
- 구현과 기준 문서가 불일치한다. 구현자가 Spec만 보고 Check를 설계하면 precondition을 알 수 없다.
- NOT_APPLICABLE의 핵심 근거(적용성 선언)가 Spec에 정리되어 있지 않다.

### P1 — file_scan 구현 전에 수정 필요

**GAP-2: `file_scan` type / scan 대상 / 목록 평가 부재**

- Inventory의 최대 신규 요구사항(9개 Check: U-15/17/23~26/31/33/67)을 표현할 수단이 없다.
- 필요한 세 가지가 모두 없다: (a) `file_scan` type, (b) 디렉토리 스캔 target, (c) "일치 파일 개수==0" 같은 목록 평가.

**GAP-3: `account_group` type 부재**

- U-08(관리자 그룹 멤버), U-09(불필요 그룹)에 필요한 그룹 멤버십 확인 type이 Spec type 목록에 없다.

**GAP-4: 목록형 Observation 평가 연산자 부재**

- `in`/`not_in`(멤버십)만 있고, "빈 목록", "일치 개수==0", "중복 존재" 등을 표현하는 연산자가 없다.
- U-15(소유자 없는 파일 0개), U-10(중복 UID 없음), U-07(불필요 계정 없음) 등이 이에 해당.

### P2 — 현재 Vertical Slice 영향 적음, 향후 필요

**GAP-5: automation 단일 축 vs 관찰/판단 2축**

- Spec의 `automation: auto/semi/manual`은 단일 축이다.
- Inventory의 A/H는 `semi`로 근사 가능하지만, "관찰은 AUTO, 판단은 HUMAN"이라는 구분이 명시적으로 표현되지 않는다.
- A/E는 automation이 아니라 `value_ref`로만 표현되어, "외부 데이터 판단"이라는 성격이 automation 축에서 보이지 않는다.

**GAP-6: NOT_APPLICABLE 근거 Evidence 규약 부재**

- Result의 NOT_APPLICABLE은 있지만, precondition 불충족의 근거(선행 Check 결과 참조 + 관찰 사실)를 Evidence로 남기는 규약이 Spec에 없다.

**GAP-7: Evidence의 목록형 observed**

- file_scan이 파일 목록을 관찰할 때 `observed`가 목록(예: `["/a", "/b"]`)이 되는 경우를 Evidence 모델이 명시하지 않는다.

### P3 — 개선 사항

**GAP-8: `source` 필드**

- 검토 요구사항에 `source`가 있으나, Spec은 KISA 파생 정보(`source`)를 의도적으로 제외한다(SSOT 원칙). 이는 문제가 아니라 의도된 설계다.

**GAP-9: Check YAML `evidence` 필드 vs Result Evidence**

- Check YAML의 `evidence`(7절, `kind: file/path/field`)는 "수집 대상 선언"이고,
  Result Evidence(15절, `target/attribute/observed`)는 "수집된 사실"이다.
- 현재 Engine은 Result Evidence를 collector의 observation으로 생성하며, Check YAML의 `evidence` 필드는 선언적으로만 존재한다. 이 관계가 Spec에 명확히 정리되어 있지 않다.

---

## 5. 수정 제안 (최소 수정안)

### GAP-1: precondition (P0)

- **현재 구조**: Engine/YAML은 `precondition` 사용, Spec 7절에 없음.
- **문제**: 기준 문서 불일치.
- **최소 수정안**: Spec 7절 필드 표에 `precondition`(선택)을 추가하고, 14절(Result)에 "precondition 불충족 → NOT_APPLICABLE" 규칙을 명시.
- **영향 범위**: 문서 1곳(7절, 14절). Engine/YAML 변경 없음.

### GAP-2: file_scan (P1)

- **현재 구조**: file kind는 `path`/`field`(단일 파일). type에 file_scan 없음.
- **문제**: 디렉토리 하위 파일 열거 + 조건 평가를 표현할 수 없음.
- **최소 수정안**:
  - type 목록에 `file_scan` 추가.
  - target kind에 `scan` 추가: `{ kind: scan, root: <경로>, pattern/filter: <조건> }` (조건: ownerless, suid, sgid, world_writable, hidden 등).
  - expect에 목록 평가 추가(GAP-4와 병행): `op: count` + `value: 0` 등.
- **영향 범위**: Spec의 type/targets/expect 3곳 + 이후 file_scan collector(Implementation).

### GAP-3: account_group (P1)

- **현재 구조**: account 계열에 account_group 없음.
- **문제**: 그룹 멤버십 확인 type 부재.
- **최소 수정안**: type 목록에 `account_group` 추가, target에 그룹 멤버십 수집 정의.
- **영향 범위**: Spec type 목록 1곳.

### GAP-4: 목록형 평가 (P1)

- **현재 구조**: `in`/`not_in`만.
- **문제**: 빈 목록/개수/중복 표현 불가.
- **최소 수정안**: op에 `count`(개수 비교), `empty`(빈 목록), `duplicate`(중복 존재)를 추가하되, 과도한 확장은 피하고 Inventory에서 실제 필요한 최소 연산자만.
- **영향 범위**: Spec expect op 목록 + Evaluator.

### GAP-5: automation 2축 (P2)

- **현재 구조**: `automation: auto/semi/manual`.
- **문제**: 관찰/판단 구분이 명시적이지 않음.
- **최소 수정안**: automation을 `auto/semi/manual`로 유지하되, 의미 정의를 Inventory의 관찰/판단에 대응시키고(13절), A/E는 `value_ref`로 표현됨을 명시. 별도 2축 필드를 강제하지 않는다.
- **영향 범위**: Spec 13절 문서 보강.

### GAP-6: NOT_APPLICABLE 근거 Evidence (P2)

- **현재 구조**: Result에 NOT_APPLICABLE만 있고 근거 규약 없음.
- **최소 수정안**: 14절/15절에 "precondition 불충족 시 선행 Check 결과 + 관찰 사실을 Evidence로 남긴다"를 명시.
- **영향 범위**: Spec 문서.

### GAP-7: 목록형 observed (P2)

- **최소 수정안**: 15절에 "observed가 목록일 수 있다"는 규약 추가(예: file_scan 결과 파일 목록).
- **영향 범위**: Spec 15절.

### GAP-9: evidence 필드 관계 (P3)

- **최소 수정안**: Check YAML `evidence`(수집 선언)와 Result Evidence(수집 사실)의 역할을 명시.
- **영향 범위**: Spec 15절.

---

## 6. Vertical Slice 영향

현재 구현된 Check는 다음 이유로 **수정 없이 계속 동작**한다.

| Check | 영향 |
| --- | --- |
| CK-lnx-U01-001 | 영향 없음(config_value) |
| CK-lnx-U01-002 | 영향 없음(service_status) |
| CK-lnx-U01-003 | 영향 없음(precondition은 이미 Engine에 구현. Spec 문서화만 누락) |
| CK-lnx-U05-001 | 영향 없음(account_uid) |
| CK-lnx-U16-001/002 | 영향 없음(file_owner/file_mode) |
| CK-lnx-U34-001 | 영향 없음(service_status) |

- GAP-1(precondition)은 Engine이 이미 지원하므로 동작에 영향 없고, Spec 문서 보강만 필요.
- GAP-2~4(file_scan/account_group/목록평가)는 **신규 기능**이며, 기존 Check에 영향 없다.
- GAP-5~7, 9는 문서/규약 보강이며, 기존 동작에 영향 없다.

> 결론: 현재 Spec은 기존 Vertical Slice를 안정적으로 수용하며, 전체 77개 Check를 수용하려면
> P0(문서화) + P1(file_scan·account_group·목록 평가) 수정이 선행되어야 한다.
> Spec 수정은 **최소 수정**(type/op/필드 추가 + 문서 보강)으로 충분하고, Engine 전면 재설계는 필요 없다.
