# Check Specification 설계

> KISA 점검항목(U-01 ~ U-67)을 실제 Linux 환경에서 자동 점검하기 위한
> "점검 정의(Check Specification)"와 "점검 구현(Check Implementation)"의 경계를 정의한다.
>
> 이 문서는 **현재 채택된 설계의 기준 문서**다. 구현자는 이 문서를 기준으로 Check Schema를 설계한다.
> 설계 변경 이력과 검증 과정은 `check-specification-validation.md`를 참고한다.

---

## 1. 문서 목적

- KISA 점검항목을 **기계가 판정 가능한 형태(Check Specification)**로 정의하는 규칙을 제공한다.
- Check Specification과 Check Implementation의 **경계**를 명확히 한다.
- Check 정의에 사용되는 ID, 대상(targets), 판정(expect), 상태(result), 증적(evidence)의 규약을 확정한다.

---

## 2. 설계 범위

- 대상 플랫폼: Linux/Unix 서버 (KISA U-01 ~ U-67)
- 포함: Check Specification(정의) 설계
- 제외: 실제 점검 코드(Shell/Python/C), 실행 엔진, 외부 시스템 연동
- 원본 SSOT(`data/kisa/linux/*.yaml`)와 ISMS-P/KISA 매핑은 변경하지 않는다.

---

## 3. 설계 원칙

1. **원문 추적성**: 모든 Check는 KISA 항목과 연결되어, 판정 결과의 근거가 되는 원문 기준을 추적할 수 있다.
2. **사양과 구현의 분리**: "무엇을 확인·판단하는가"(선언적 사양)와 "실제 OS에서 어떻게 실행하는가"(명령/API)를 분리한다.
3. **결과 상태의 정밀화**: 단순 PASS/FAIL이 아니라 미적용·미구현·오류·수동 필요를 구분한다.
4. **원문 불변**: KISA 원문의 `pass`/`fail`(양호/취약)은 그대로 보존하고, Check는 이를 참조하는 별도 계층이다.
5. **중복 최소화**: KISA에서 파생되는 정보는 Check에 중복 저장하지 않는다.
6. **확장 제한**: 실제 Check 표현에 필요한 수준만 설계하고, 범용 표현 언어나 불필요한 계층은 도입하지 않는다.

---

## 4. 전체 구조

```
KISA 원문 데이터 (data/kisa/linux/*.yaml)     ← 사실(SSOT)
        │
Check Specification (data/checks/linux/*.yaml) ← 해석(판정 조건)
        │
Mapping (data/mappings/kisa-to-check.yaml)     ← Check ↔ KISA 연결
        │
Check Implementation (향후 코드)               ← 실행(OS별)
```

- **Check Specification**: 무엇을 확인하고, 어떤 조건으로 PASS/FAIL을 판정하는지 정의한다. 실행 명령은 포함하지 않는다.
- **Check Implementation**: Specification을 받아 실제 명령·API·파일 접근을 수행하는 OS/배포판별 코드다.
- **Mapping**: Check와 KISA 항목의 관계를 관리하는 별도 계층이다.

---

## 5. Check와 KISA Item의 관계

Check는 KISA 항목을 직접 참조하지 않는다. 관계는 **별도의 mapping에서 관리**한다.

```text
KISA Item
    ↕
Mapping
    ↕
Check
```

### Mapping 형태

```yaml
mappings:
  - kisa_ref: U-01
    check_refs:
      - CK-lnx-U01-001
      - CK-lnx-U01-002
      - CK-lnx-U01-003
```

- `kisa_ref`: KISA 항목 ID.
- `check_refs`: 해당 KISA 항목을 구성하는 Check ID 목록.

이 구조로 1:N(하나의 KISA → 여러 Check)과 N:1(하나의 Check → 여러 KISA)을 모두 표현할 수 있다. 하나의 Check ID가 여러 매핑 레코드에 등장하면 N:1이 된다.

---

## 6. Check ID 규칙

Check ID는 항상 다음 형식을 따른다.

```text
CK-<platform>-<kisa-id>-<sequence>
```

| 요소 | 규칙 | 예시 |
| --- | --- | --- |
| `CK` | 고정 접두사 | `CK` |
| `platform` | 소문자 플랫폼 코드(`lnx`, `win`, `db`, `web`, `net`) | `lnx` |
| `kisa-id` | KISA 항목 ID(하이픈 제거) | `U01` |
| `sequence` | 3자리 0-패딩, 1부터 순차 | `001` |

예:
- `CK-lnx-U01-001`
- `CK-lnx-U01-002`
- `CK-lnx-U16-001`

**sequence는 단일 Check인 경우에도 생략하지 않는다.** ID는 Check의 분해 여부와 무관하게 안정적이다.

---

## 7. Check Specification 구조

Check는 순수 기술 정의만 담는다. KISA 파생 정보는 저장하지 않는다.

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `id` | string | Y | `CK-lnx-U05-001` |
| `type` | enum | Y | Check 유형 |
| `description` | string | N | 이 Check의 초점(하위 Check 구분용) |
| `targets` | list | Y | 검사 대상 목록(8절) |
| `expect` | object | Y | 판정 조건(9절) |
| `precondition` | object | N | 적용성 선언(선택, 아래 참조) |
| `automation` | object | Y | 관찰/판단 자동화(13절) |
| `platforms` | list | Y | 적용 OS/배포판 |
| `evidence` | list | N | 수집 증적(15절) |

### KISA 파생 정보 (저장하지 않음)

다음 정보는 KISA 원문에서 파생되므로 Check에 저장하지 않고, mapping을 통해 KISA 데이터에서 참조한다.

- `title` (KISA 항목명)
- `severity` (중요도)
- `source` (출처)
- `pass`/`fail` (원문 양호/취약)

### Check 유형 (`type`)

| type | 설명 |
| --- | --- |
| `file_mode` | 파일/디렉토리 권한 (permission semantics, 10절) |
| `file_owner` | 파일/디렉토리 소유자 |
| `file_existence` | 파일 존재 여부 |
| `config_value` | 설정 파일의 키-값 |
| `account_uid` | 계정 UID |
| `account_gid` | 그룹 GID |
| `account_shell` | 계정 로그인 쉘(제한 쉘 검사 포함) |
| `account_duplicate` | UID/GID 중복 |
| `account_home` | 계정 홈 디렉토리 존재 |
| `service_status` | 서비스/데몬 상태 |
| `process_running` | 프로세스 실행 여부 |
| `package_version` | 패키지 설치/버전 |
| `command_output` | 명령 출력 |
| `document` | 정책/절차 문서 존재 |
| `file_scan` | 파일 열거(디렉토리 스캔, 12-1절) |
| `account_group` | 그룹 멤버십 (12-1절) |

### precondition (선택)

Check가 **이 환경에 적용되는지**를 선언하는 선택적 필드다. 하위 검사(mini-check) 구조를 갖는다.

```yaml
precondition:
  ref: CK-lnx-U01-002          # 선택: 근거가 되는 선행 Check ID
  type: service_status          # 하위 검사 type
  targets:                      # 하위 검사 대상
    - kind: service
      name: telnet
      mechanisms: [systemd, xinetd, inetd]
  expect:                       # 하위 검사 판정
    op: eq
    value: enabled
```

- `type` / `targets` / `expect`: Check 본체와 동일한 구조로, 적용성을 판정한다.
- `ref`: 선행 Check ID(선택). Evidence에서 "왜 적용되지 않았는지"의 근거로 참조한다.
- precondition의 `expect`가 **False**이면 이 Check는 적용 대상이 아니므로 Result는 `NOT_APPLICABLE`이 된다.
- precondition의 `expect`가 True이면 본 Check의 targets/expect를 계속 평가한다.

#### precondition과 NOT_APPLICABLE의 Evidence

precondition 불충족으로 인한 `NOT_APPLICABLE`은 **정상 결과**이며 Error가 아니다. 이때 Evidence에는 다음을 남긴다.

1. 선행 Check 결과 참조: `target=<ref>`, `attribute=result`, `observed=<선행 Check Result>`.
2. precondition에서 수집한 관찰 사실(target/attribute/observed).

사람이 "왜 이 Check가 적용되지 않았는지"를 추적할 수 있어야 한다.

---

## 8. targets

Check의 검사 대상은 하나 이상일 수 있다. `targets[]` 리스트로 표현한다.

```yaml
targets:
  - id: passwd
    kind: file
    path: /etc/passwd
    field: owner
  - id: uid0
    kind: account
    source: /etc/passwd
    field: uid
    exclude: [root]
```

- target마다 선택적 `id`를 부여해 `expect`의 각 조건이 **어느 target에 적용되는지** 참조한다.
- 단일 target이면 `id`를 생략할 수 있다.

### target `kind`와 주요 필드

| kind | 주요 필드 |
| --- | --- |
| `file` | `path`, `field`(owner/mode) |
| `config` | `path`, `key` |
| `account` | `source`, `field`(name/uid/gid/home/shell), `exclude`, `names`(선택), `restricted`(선택) |
| `group` | `source`, `name`(선택) |
| `scan` | `root`, `recursive`, `criteria`(12-1절) |
| `service` | `name`, `mechanisms`(선택, 11절) |
| `process` | `name` |
| `package` | `name` |
| `command` | `ref`(구현 계층의 명령 참조) |
| `document` | `name` |

### account target의 위반 목록 판정

`account` target은 수집 단계에서 **위반 계정 목록**을 필터해 반환하고, `expect: {op: empty}`로 판정한다.

- `account_shell` + `field: shell` + `names` + `restricted`:
  - `names`(검사 대상 계정명 목록)에 속한 계정 중, `restricted`(허용 제한 쉘 목록, 예: `/bin/false`·`/sbin/nologin`)에 없는 쉘을 가진 계정을 **위반 목록**으로 반환한다.
  - `names`에 없는 일반 사용자 계정의 쉘은 검사 대상에서 제외한다.
- `account_home` + `field: home`:
  - 홈 디렉토리가 존재하지 않는 계정을 **위반 목록**으로 반환한다.
- `account_duplicate`:
  - 중복 UID/GID를 가진 계정을 **위반 목록**으로 반환한다.

```yaml
# U-11 (로그인 불필요 계정의 쉘 제한)
targets:
  - kind: account
    source: /etc/passwd
    field: shell
    names: [daemon, bin, sys, adm, listen, nobody, nobody4, noaccess, diag, operator, games, gopher]
    restricted: [/bin/false, /sbin/nologin]
expect:
  op: empty        # 위반 계정 0개
```

---

## 9. expect 및 조건 표현

`expect`는 **리프(비교)** 또는 **논리 결합(all/any/not)** 노드다.

### 리프 (단일 비교)

```yaml
expect:
  op: eq
  value: "No"
```

### 논리 결합

```yaml
# AND
expect:
  all:
    - { op: eq, value: "root" }
    - { op: contains, value: "pam_securetty.so" }

# OR
expect:
  any:
    - { op: eq, value: "No" }
    - { op: eq, value: disabled }

# NOT
expect:
  not:
    op: contains
    value: "pts"
```

### 비교 연산자 (`op`)

| op | 의미 | value 필요 |
| --- | --- | --- |
| `eq` / `ne` | 같음 / 같지 않음 | Y |
| `le` / `lt` / `ge` / `gt` | 수치 비교 (파일 권한 제외) | Y |
| `contains` / `not_contains` | 포함 / 미포함 | Y |
| `in` / `not_in` | 목록 포함 / 제외 | Y |
| `matches` | 정규식 | Y |
| `exists` | scalar/객체 존재(파일·문서) — unary | N |
| `empty` | 목록이 비어 있음(0개) — unary | N |

- `exists`는 scalar/객체 존재(파일·문서)에만 사용한다. 목록의 "1개 이상"은 `not: { op: empty }`로 표현한다.

### 대소문자 정책

- `eq`/`ne`는 **기본적으로 대소문자를 구분(case-sensitive)**한다.
- 대소문자를 무시해야 하는 값(예: SSH 설정의 `yes`/`no`)은 리프에 `case_insensitive: true`를 명시한다.

```yaml
expect:
  op: eq
  value: "No"
  case_insensitive: true
```

### 값의 종류

리프의 값은 정적 `value` 또는 외부 참조 `value_ref`(12절) 중 하나다.

```yaml
- op: eq
  value: "No"          # 정적
- op: ge
  value_ref:           # 외부 참조
      source: vendor_advisory
      item: { package: kernel, platform: linux }
```

### 규칙
- 결합 노드는 `all`/`any`/`not` 중 하나만 갖는다.
- **비교 리프**는 `op` + (`value` | `value_ref`)를 갖는다.
- **unary 리프**(`exists`, `empty`)는 value가 없다.
- `mode_allowed`(10절)는 `op`가 아닌 별도 구조다.
- 다중 target이면 리프에 `target`을 명시한다.
- `expect`는 Check 판정에 필요한 수준의 논리 조합만 표현한다. 범용 expression language로 확장하지 않는다.

### 목록형 관찰 평가 (Collection-level Assessment)

`file_scan`/`account_group` 등이 수집한 결과는 **목록(리스트)**일 수 있다. 목록에 대한 판정은 다음을 사용한다.

| 표현 | 의미 |
| --- | --- |
| `op: empty` | 목록이 비어 있음(0개) |
| `not: { op: empty }` | 목록이 비어 있지 않음(1개 이상) |
| `in` / `not_in` | 특정 값이 목록에 포함/미포함(멤버십) |

- `exists`는 **scalar/객체 존재**(파일/문서 존재) 의미로 한정한다. 목록의 "1개 이상"은 `not: { op: empty }`로 표현한다.
- "중복 UID 없음"(U-10), "조건에 맞는 파일 없음"(file_scan) 등은 **수집 단계에서 해당 항목만 필터**하고, 결과 목록이 `empty`인지로 판정한다.
- `count`(개수 수치 비교) 연산자는 현재 Inventory에서 "0개"만 필요하므로 추가하지 않는다. 필요 시 향후 확장한다.

---

## 10. 파일 권한 판정

Unix 파일 권한은 일반 숫자의 `le`/`lt` 비교로 판정하지 않는다. **Unix permission semantics**를 이용해 판정한다.

### 구조

`file_mode` type은 `expect.mode_allowed`로 허용 최대 권한을 정의한다.

```yaml
expect:
  mode_allowed:
    owner: rw
    group: r
    other: r
```

### 판정 규칙

`mode_allowed`는 각 주체(owner/group/other)에게 **허용되는 최대 권한**을 의미한다. 실제 파일 권한이 이 허용 범위를 벗어나는 비트를 하나라도 가지면 FAIL이다.

| 실제 권한 | 판정 |
| --- | --- |
| `rw-r--r--` (644) | PASS |
| `rw-r-----` (640) | PASS (더 제한적) |
| `rw-------` (600) | PASS (더 제한적) |
| `rw-rw-r--` (664) | FAIL (group에 w) |
| `rw-rw-rw-` (666) | FAIL (group/other에 w) |

- 판정은 "더 제한적이면 양호, 더 관대하면 취약"이라는 permission semantics를 따른다.
- 각 주체의 권한 문자는 `r`/`w`/`x` 조합이며, 없으면 빈 문자열(또는 `-`)로 표현한다.

---

## 11. 서비스 관리 방식

서비스 상태는 시스템별 서비스 관리 메커니즘이 다르므로, Specification에서 이를 표현할 수 있어야 한다.

### `service_status`의 mechanism

```yaml
targets:
  - kind: service
    name: finger
    mechanisms: [inetd, xinetd]   # 점검할 메커니즘 힌트
expect:
  op: eq
  value: disabled
```

### mechanism 종류

| mechanism | 설명 |
| --- | --- |
| `systemd` | systemd unit 상태 |
| `xinetd` | `/etc/xinetd.d/*` 설정 |
| `inetd` | `/etc/inetd.conf` 설정 |
| `smf` | Solaris SMF |
| `initd` | SysV init 스크립트 |

- `mechanisms`는 이 Check가 점검해야 할 메커니즘의 범위를 나타내는 선택적 힌트다.
- 의미 판정(`disabled`/`enabled`)은 메커니즘과 무관하게 일관된다.
- 실제 점검 명령·경로는 전부 Implementation에 존재한다.

---

## 12. external reference

패치 버전이나 외부 기준값처럼 **Check 시점에 외부 기준을 참조**해야 하는 경우를 표현한다.

### `value_ref`

```yaml
expect:
  any:
    - op: ge
      value_ref:
        source: vendor_advisory
        item: { package: kernel, platform: linux }
    - op: eq
      value_ref:
        source: policy
        key: patch.accepted_kernel_version
```

### `value_ref.source`

| source | 의미 | 조회 키 |
| --- | --- | --- |
| `policy` | 조직 정책/기준값 | `key` |
| `vulnerability_db` | 취약점 DB | `item` |
| `vendor_advisory` | 벤더 권고 | `item` |

- `value_ref`는 **기준값을 어디서 가져올지**를 선언한다.
- 실제 외부 시스템 연동 방법(API·DB 접근·갱신 주기)은 이 단계에서 설계하지 않는다.
- 외부 참조를 해석하지 못하면 결과는 `NOT_SUPPORTED` 또는 `MANUAL_REQUIRED`가 된다.

---

## 12-1. Collection Observation (file_scan·account_group)

목록형 관찰을 수집하는 두 Check type을 정의한다. 이들은 KISA 점검 자체가 아니라
**시스템에서 사실(파일/그룹)을 열거해 목록으로 수집**하는 범용 type이다.

### file_scan (파일 열거)

디렉토리 하위 파일의 metadata를 열거해 목록으로 수집한다.

```yaml
- id: CK-lnx-U23-001
  type: file_scan
  targets:
    - id: suid_files
      kind: scan
      root: /usr/bin
      recursive: false
      criteria: suid
  expect:
    op: empty          # 조건에 맞는 파일이 0개
  automation:
    observation: auto
    assessment: human  # "불필요한지" 판단은 사람(A/H)
```

#### 대상(target: `scan`)

| 필드 | 의미 |
| --- | --- |
| `root` | 스캔 시작 경로 |
| `recursive` | 하위 디렉토리 재귀 여부 (기본 false) |
| `types` | 매칭 대상 entry 타입 목록(선택). `file` / `directory` / `device`. 기본값 `[file, device]` |
| `criteria` | 수집 조건(필터). 문자열 enum 또는 predicate 객체(아래 참고) |

#### traversal 및 types semantics

- **scan root 자신은 평가 대상이 아니다.** scan root의 직접 자식부터 평가한다.
- `recursive: false`는 scan root의 **직접 자식만** 평가하고 하위 디렉토리로 진입하지 않는다.
- `recursive: true`는 하위 디렉토리로 재귀 진입하며 각 entry를 평가한다.
- 디렉터리의 "재귀 진입"과 "criteria 매칭"은 독립적이다. `types`에 `directory`가 포함되면
  디렉터리도 criteria 평가 대상이 된다.
- symlink는 매칭·재귀·추적 모두 하지 않는다(건너뛴다).

| type 값 | 의미 |
| --- | --- |
| `file` | regular file (`S_ISREG`) |
| `directory` | 디렉터리 (`S_ISDIR`) |
| `device` | character/block device (`S_ISCHR`\|`S_ISBLK`) |

```yaml
# U-31 (홈 디렉터리 자체 검사)
targets:
  - kind: scan
    root: /home
    recursive: false
    types: [directory]
    criteria: world_writable
```

#### criteria 형식

`criteria`는 다음 두 가지 형식을 지원한다.

1. **문자열 enum** (기존): `ownerless` / `suid` / `sgid` / `sticky` / `world_writable` / `hidden` / `device`

   ```yaml
   criteria: world_writable
   ```

2. **predicate 객체** (확장): 소유자/권한 조건을 결합한다. 각 키는 **OR**로 결합된다(어느 하나라도 충족하면 매칭).

   ```yaml
   criteria:
     owner_ne: root
     mode_not_allowed:
       owner: rw
       group: r
       other: r
   ```

   - `owner_ne: <name>`: 파일 소유자 이름이 `<name>`이 아니면 매칭.
   - `mode_not_allowed: {owner, group, other}`: `file_mode.mode_allowed`와 동일 구조.
     파일 권한이 허용 최대 범위를 초과(`mode & ~mask != 0`)하면 매칭.
   - OR 의미: `{owner_ne: root, mode_not_allowed: {...}}`는 "소유자≠root **또는** 권한 초과"인 파일을 수집한다.
   - AND 조건이나 별도 논리식 DSL은 지원하지 않는다.

#### criteria의 의미와 경계

`criteria`는 **수집 단계의 기술적 필터**다. KISA의 PASS/FAIL 판단을 수행하지 않는다.

```text
scan filter (criteria)
    ↓  Observation 후보를 좁히는 기술적 필터
Observation (수집된 목록)
    ↓
expect
    ↓
Technical Assessment (기계 판정 / 사람 판단 / 외부 데이터)
```

- 예: `criteria: world_writable` → "world writable 파일 목록 수집"(Observation AUTO).
  - "그 파일이 불필요/제거 대상인지"는 expect 이후 **Assessment(HUMAN)**다.
- A/H(U-23/U-25/U-26/U-33)에서는 이 경계가 명확해야 한다: 목록 수집은 AUTO, "불필요" 판단은 HUMAN.

#### Observation (수집된 파일 metadata)

각 파일은 다음 metadata를 관찰한다.

```text
path, type, uid, gid, owner, mode, size, suid, sgid, sticky
```

- "불필요/의심/제거" 같은 **업무 판단**이 필요한 경우 `assessment: human`(A/H)로 두고, 파일 목록 수집은 `observation: auto`로 동작한다.
- "존재/권한/소유자" 등 기계 판정이면 `assessment: auto`(A/A)다.

### account_group (그룹 멤버십)

그룹의 이름/GID/멤버 목록을 수집·평가한다.

```yaml
- id: CK-lnx-U08-001
  type: account_group
  targets:
    - kind: group
      source: /etc/group
      name: wheel       # 선택: 특정 그룹만(생략 시 전체 그룹 열거)
  expect:
    op: empty          # 또는 in/not_in 등
  automation:
    observation: auto
    assessment: human  # "불필요한 멤버" 판단은 사람(A/H)
```

#### 대상(target: `group`)

| 필드 | 의미 |
| --- | --- |
| `source` | 그룹 정보 파일(/etc/group) |
| `name` | 대상 그룹명(선택. 생략 시 전체 그룹 열거) |

#### Observation

```text
group_name, gid, members[]
```

- `members`: 해당 그룹에 속한 사용자 이름 목록.

### account_duplicate (중복 UID/GID)

`account_duplicate`는 **중복 UID/GID를 Collector가 탐지**해 목록으로 제공하고, 그 목록이 `empty`인지로 판정한다.

```yaml
- id: CK-lnx-U10-001
  type: account_duplicate
  targets:
    - kind: account
      source: /etc/passwd
      field: uid
  expect:
    op: empty          # 중복 UID 목록이 비어 있음 = "중복 없음"
  automation:
    observation: auto
    assessment: auto   # 중복 여부는 기계 판정(A/A)
```

- Collector가 "중복 UID를 가진 계정"만 필터해 목록으로 반환한다. 별도 `duplicate` operator는 필요 없다.
- `empty`(0개)면 "중복 없음"=PASS, 아니면 FAIL.

### 판정(expect)의 공통 규칙

- 수집 결과는 목록이며, `empty` / `exists` / `not` / `in` / `not_in`(9절)으로 평가한다.
- "불필요" 판단이 필요한 Check는 `assessment: human`(A/H)로 두고, 목록 수집은 `observation: auto`로 동작한다.

---

## 13. Automation 모델

`automation`은 **관찰(Observation)/판단(Assessment) 두 축**으로 정의한다. 단일 `auto/semi/manual` 축이 아니라, 관찰과 판단을 분리해 표현한다.

```yaml
automation:
  observation: auto      # auto | manual
  assessment: auto       # auto | human | external_data
```

| 축 | 값 | 의미 |
| --- | --- | --- |
| `observation` | `auto` | 시스템에서 기술적 사실을 자동 수집 |
| `observation` | `manual` | 자동 수집 불가(정책/문서 확인) |
| `assessment` | `auto` | 수집한 사실을 기준에 따라 자동 판정 |
| `assessment` | `human` | 최종 판정은 사람(업무/정책 적정성) |
| `assessment` | `external_data` | 외부 DB/벤더 권고와 비교해 판정 |

### 관찰/판단 조합 (Inventory 표기 대응)

| observation | assessment | Inventory | 예 |
| --- | --- | --- | --- |
| auto | auto | A/A | U-01, U-05, U-16 |
| auto | human | A/H | U-07, U-23 |
| auto | external_data | A/E | U-45, U-49, U-64-002 |
| manual | human | M/H | U-64-001 |

- `assessment: external_data`는 `value_ref`(12절)와 함께 사용한다. `value_ref`가 기준값을 어디서 가져올지 선언하면, `assessment: external_data`가 "외부 데이터로 판정"함을 나타낸다.
- `assessment: human` 또는 `external_data`인 경우, 사람 확인/외부 데이터가 필요한 사유를 부가 필드로 설명할 수 있다.

```yaml
automation:
  observation: auto
  assessment: human
  manual_reason: "'불필요한' 계정 판단에 조직 기준 필요"
```

- `automation`은 Check 레벨에서 지정하며, 하나의 KISA 항목이 서로 다른 automation의 Check들로 나뉠 수 있다.

---

## 14. Result 상태 모델

Check 실행 결과는 다음 6가지 상태로 구분한다.

| 상태 | 의미 |
| --- | --- |
| `PASS` | 적용 대상이며 요구 조건을 만족 |
| `FAIL` | 적용 대상이지만 요구 조건을 만족하지 않음 (취약) |
| `NOT_APPLICABLE` | 해당 환경에서 Check 자체가 적용되지 않음 |
| `NOT_SUPPORTED` | 현재 구현이 해당 환경/메커니즘을 지원하지 않음 |
| `ERROR` | 실행 또는 판정 과정에서 오류 발생 |
| `MANUAL_REQUIRED` | 자동화만으로 최종 판단할 수 없음 |

### FAIL vs ERROR

- **FAIL**: 검사가 정상 실행되었고 결과가 취약.
- **ERROR**: 검사 실행 자체가 실패해 판정을 내릴 수 없음(명령 오류, 권한 부족 등).

### NOT_APPLICABLE vs ERROR

- **NOT_APPLICABLE**: precondition이 충족되지 않아 **Check 자체가 적용되지 않는 경우**(정상 결과).
- **ERROR**: 적용 대상은 맞지만 필요한 파일/설정/명령을 **읽지 못해 점검할 수 없는 경우**.

> "파일이 존재하지 않으면 NOT_APPLICABLE"로 보지 않는다. 대상 파일 부재는 점검 불가이므로 ERROR다.
> NOT_APPLICABLE은 오직 precondition 불충족(적용성 선언이 False)일 때만 발생한다.

### automation과 상태

| automation | 발생 가능한 상태 |
| --- | --- |
| observation=auto, assessment=auto | PASS / FAIL / NOT_APPLICABLE / ERROR / NOT_SUPPORTED |
| observation=auto, assessment=human | 위 상태 + MANUAL_REQUIRED |
| observation=auto, assessment=external_data | 위 상태 + NOT_SUPPORTED(외부 데이터 미해석 시) |
| observation=manual | MANUAL_REQUIRED |

---

## 15. Evidence 모델

Evidence는 Check의 **판정 조건(expect)과 구분**하여 다룬다.

### Result와 Evidence의 분리

- **Result**: Technical Check의 최종 평가 결과(`PASS`/`FAIL`/`ERROR`/`NOT_APPLICABLE` …).
- **Evidence**: Result를 판단하기 위해 실제로 관찰한 사실.

Evidence 자체에 `PASS`/`FAIL`을 중복 기록하지 않는다. 종합 해석("미사용", "차단됨" 등)도 Evidence에 넣지 않는다.

```text
Collector → 실제 관찰값 → Evidence → Evaluator → Result
```

- Collector는 가능한 한 **원시 관찰 사실**을 수집한다.
- Evaluator가 그 사실을 기준으로 `expect`와 비교해 Result를 결정한다.

### 관찰값(`observed`)과 종합 판정의 구분

- `observed`는 **실제 수집된 원시 관찰값**을 의미한다(예: 설정 파일의 `PermitRootLogin = yes`).
- "미사용", "차단됨" 같은 종합 해석은 `observed`에 넣지 않는다. 그것은 Result의 몫이다.
- 서비스 상태처럼 원시값이 여럿인 경우, 각 관찰 사실을 별도의 Evidence 항목으로 나눈다.

### Evidence 공통 구조

모든 Evidence 항목은 기본적으로 다음 구조를 갖는다.

```yaml
evidence:
  - target: <관찰 대상>
    attribute: <관찰 속성>
    observed: <실제 관찰값>
    # 단일값 비교일 때만:
    expected: <기대값>
```

- `target`: 실제 확인한 대상(파일 경로/서비스/메커니즘 등).
- `attribute`: 확인한 속성(설정 항목 등).
- `observed`: 실제 시스템에서 관찰된 값(raw observation).
- `expected`: Check가 요구하는 값(단일값 `eq`/`ne` 비교일 때만).

Check 종류에 따라 `target`/`attribute`의 구체적인 값은 달라도 된다.

### Check 유형별 Evidence 예

| type | target / attribute / observed 예 |
| --- | --- |
| `config_value` | `target=/etc/ssh/sshd_config` · `attribute=PermitRootLogin` · `observed=yes` · `expected=No` |
| `service_status` | `target=systemd` · `attribute=telnet.service` · `observed=not_configured` 등 메커니즘별·런타임 항목 |
| `file_scan` | `target=<경로>` · `attribute=<metadata>` · `observed=<목록 또는 개별 파일>` |

공통 필드(target/attribute/observed)를 기본 구조로 하되, 모든 Check가 동일한 필드를 강제로 가질 필요는 없다.

### 목록형 observed와 NOT_APPLICABLE Evidence

- `observed`는 **목록일 수 있다**(예: `file_scan`이 수집한 파일 목록, `account_group`의 멤버 목록). 이 경우 각 항목을 개별 Evidence로 나누거나 목록으로 기록한다.
- **NOT_APPLICABLE**(precondition 불충족)의 Evidence는 7절에서 정의한 대로, 선행 Check 결과 참조 + 관찰 사실을 포함한다.

### 수집과 판정의 분리

1. **수집**: 대상을 읽어 관측값을 남긴다(항상 수행).
2. **판정**: 수집값을 `expect`와 비교해 상태를 결정한다.

수집과 판정을 분리하면 증적 재사용, 판정 로직 변경 시 재수집 불필요, 감사용 원시 증적 보존이 가능하다.

---

## 16. 대표적인 Check 예제

### 16.1 U-01 (root 계정 원격 접속 제한)

U-01은 3개 Check로 분해한다. (Inventory와 일치)

```yaml
# 1) SSH root 직접 접속 제한
- id: CK-lnx-U01-001
  type: config_value
  description: SSH 서버의 root 직접 원격 접속 허용 여부 확인
  platforms: [linux]
  automation:
    observation: auto
    assessment: auto
  targets:
    - kind: config
      path: /etc/ssh/sshd_config
      key: PermitRootLogin
  expect:
    op: eq
    value: "No"
    case_insensitive: true
  evidence:
    - { kind: file, path: /etc/ssh/sshd_config, field: PermitRootLogin }

# 2) Telnet 원격터미널 서비스 사용 여부
- id: CK-lnx-U01-002
  type: service_status
  description: Telnet 원격터미널 서비스 사용 여부 확인
  platforms: [linux]
  automation:
    observation: auto
    assessment: auto
  targets:
    - kind: service
      name: telnet
      port: 23
      mechanisms: [systemd, xinetd, inetd]
  expect:
    op: eq
    value: disabled
  evidence:
    - { kind: service, name: telnet, field: status }

# 3) Telnet 사용 시 root 직접 접속 제한
- id: CK-lnx-U01-003
  type: config_value
  description: Telnet 사용 시 root 직접 접속 제한 여부 확인
  platforms: [linux]
  precondition:
    ref: CK-lnx-U01-002
    type: service_status
    targets:
      - kind: service
        name: telnet
        port: 23
        mechanisms: [systemd, xinetd, inetd]
    expect:
      op: eq
      value: enabled
  automation:
    observation: auto
    assessment: auto
  targets:
    - id: pam
      kind: config
      path: /etc/pam.d/login
    - id: securetty
      kind: config
      path: /etc/securetty
  expect:
    all:
      - { target: pam, op: contains, value: "pam_securetty.so" }
      - { target: securetty, op: not_contains, value: "pts" }
  evidence:
    - { kind: file, path: /etc/pam.d/login }
    - { kind: file, path: /etc/securetty }
```

```yaml
mappings:
  - kisa_ref: U-01
    check_refs: [CK-lnx-U01-001, CK-lnx-U01-002, CK-lnx-U01-003]
```

- U-01-002는 "Telnet 사용 여부", U-01-003은 "Telnet 사용 시 root 제한"이다.
- U-01-003은 `precondition`으로 "Telnet이 사용되는 경우에만 적용"을 선언한다. Telnet 미사용이면 precondition이 False가 되어 `NOT_APPLICABLE`이 된다.

### 16.2 U-05 (root 이외 UID 0 계정 존재 여부)

```yaml
- id: CK-lnx-U05-001
  type: account_uid
  description: root 외 UID 0 계정 존재 여부
  automation:
    observation: auto
    assessment: auto
  platforms: [linux]
  targets:
    - kind: account
      source: /etc/passwd
      field: uid
      exclude: [root]
  expect:
    op: not_in
    value: [0]
  evidence:
    - { kind: account, source: /etc/passwd, field: uid }
```

```yaml
mappings:
  - kisa_ref: U-05
    check_refs: [CK-lnx-U05-001]
```

### 16.3 U-16 (/etc/passwd 소유자 및 권한)

```yaml
- id: CK-lnx-U16-001
  type: file_owner
  description: /etc/passwd 소유자
  automation:
    observation: auto
    assessment: auto
  platforms: [linux]
  targets:
    - { kind: file, path: /etc/passwd, field: owner }
  expect:
    op: eq
    value: "root"
  evidence:
    - { kind: file, path: /etc/passwd, field: owner }

- id: CK-lnx-U16-002
  type: file_mode
  description: /etc/passwd 권한
  automation:
    observation: auto
    assessment: auto
  platforms: [linux]
  targets:
    - { kind: file, path: /etc/passwd, field: mode }
  expect:
    mode_allowed:
      owner: rw
      group: r
      other: r
  evidence:
    - { kind: file, path: /etc/passwd, field: mode }
```

```yaml
mappings:
  - kisa_ref: U-16
    check_refs: [CK-lnx-U16-001, CK-lnx-U16-002]
```

### 16.4 U-34 (Finger 서비스 비활성화)

```yaml
- id: CK-lnx-U34-001
  type: service_status
  description: Finger 서비스 비활성화
  automation:
    observation: auto
    assessment: auto
  platforms: [linux]
  targets:
    - kind: service
      name: finger
      mechanisms: [inetd, xinetd]
  expect:
    op: eq
    value: disabled
  evidence:
    - { kind: service, name: finger, field: status }
```

```yaml
mappings:
  - kisa_ref: U-34
    check_refs: [CK-lnx-U34-001]
```

### 16.5 U-64 (최신 보안 패치 적용)

```yaml
- id: CK-lnx-U64-001
  type: document
  description: 패치 적용 정책 수립 여부
  automation:
    observation: manual
    assessment: human
  platforms: [linux]
  targets:
    - { kind: document, name: "패치 적용 정책/절차" }
  expect:
    op: exists
  evidence:
    - { kind: document, name: "패치 적용 정책/절차" }

- id: CK-lnx-U64-002
  type: package_version
  description: 보안 패치 적용 상태
  automation:
    observation: auto
    assessment: external_data
  platforms: [linux]
  targets:
    - kind: package
      name: kernel
  expect:
    any:
      - op: ge
        value_ref:
          source: vendor_advisory
          item: { package: kernel, platform: linux }
      - op: eq
        value_ref:
          source: policy
          key: patch.accepted_kernel_version
  evidence:
    - { kind: package, name: kernel, field: version }
```

```yaml
mappings:
  - kisa_ref: U-64
    check_refs: [CK-lnx-U64-001, CK-lnx-U64-002]
```

---

## 17. Schema 설계 원칙

1. Check에는 KISA 파생 정보(`title`/`severity`/`source`/`kisa_ref`)를 넣지 않는다.
2. Check ID의 sequence는 항상 3자리이며 생략하지 않는다.
3. `expect`는 리프 또는 결합(`all`/`any`/`not`) 중 하나다. 리프는 `op` + (`value` | `value_ref`).
4. 다중 target이면 리프에 `target` 참조를 명시한다.
5. 파일 권한은 `mode_allowed`(permission semantics)로 판정하고, 숫자 비교(`le`/`lt`)를 사용하지 않는다.
6. `service_status`의 `mechanisms`는 선택적 힌트이며, 의미 판정(`disabled`/`enabled`)은 일관되게 유지한다.
7. 외부 기준값은 `value_ref`로만 표현하고, 정적 `value`와 혼용하지 않는다.
8. 결과 상태는 6종을 사용하고, `FAIL`과 `ERROR`를 혼동하지 않는다.
9. `automation`은 `observation`/`assessment` 2축으로 표현한다. 단일 `auto/semi/manual` 축을 사용하지 않는다.
10. Evidence는 raw observation을 `target`/`attribute`/`observed`로 남기고, 판정 결과를 중복 기록하지 않는다.
11. Check↔KISA 관계는 mapping이 SSOT이며, Check에는 관계 정보를 두지 않는다.

---

## 18. 구현 단계

1. Check Schema 확정: 7~15절의 구조를 JSON/YAML Schema로 고정.
2. Mapping Schema 확정: `kisa_ref`/`check_refs` 구조 확정.
3. Check Specification 작성: U-01~U-67 전체를 본 설계로 구조화.
4. 판정 엔진 구현: `expect` 평가와 상태 산출 로직.
5. Evidence 수집기 구현: 수집과 판정의 분리 파이프라인.
6. OS 구현 계층: Linux 배포판별 mechanism/명령/경로 매핑.
7. 확장 검증: Windows/DB/Web/Network 추가 시 type/mechanism/value_ref 확장성 확인.

---

## 19. 남은 설계 과제

- 여러 Check의 결과를 하나의 KISA 항목 결과로 **집계하는 규칙**(AND/OR 결합, NOT_APPLICABLE 처리)은 아직 미확정.
- `value_ref`의 외부 데이터 조회 방식(연동 대상, 갱신 주기)은 미정.
- `command_output` type의 출력 파싱 표현 방식은 아직 상세 설계 없음.
- `file_scan`의 `criteria`(수집 필터)와 `account_group`의 멤버 열거는 **Spec 정의 완료**이나, 실제 수집기(collector)는 미구현.
- `account_duplicate`/`account_gid`/`process_running` 등 일부 type은 샘플로 검증되지 않음.

---

## 20. Inventory Coverage

현재 Specification으로 Inventory의 대표 항목이 표현 가능한지 확인한다.

| Check | 표현 요소 | 상태 |
| --- | --- | --- |
| U-01 | config_value + precondition + NOT_APPLICABLE | OK |
| U-05 | account_uid + `not_in` | OK |
| U-16 | file_owner/file_mode + `mode_allowed` | OK |
| U-23 | file_scan + `empty` + A/H | OK |
| U-25 | file_scan + `empty` + A/H | OK |
| U-45 | package_version + `value_ref` + A/E | OK(연동 미정) |
| U-64 | document(M/H) + package_version(A/E) | OK(연동 미정) |

### 자동화 2축 검증

| 조합 | `automation` 표현 | 의미 |
| --- | --- | --- |
| A/A | `{observation: auto, assessment: auto}` | 자동 관찰 + 자동 판단 |
| A/H | `{observation: auto, assessment: human}` | 자동 관찰 + 사람 판단 |
| A/E | `{observation: auto, assessment: external_data}` | 자동 관찰 + 외부 데이터 판단 |
| M/H | `{observation: manual, assessment: human}` | 수동 관찰 + 사람 판단 |

- U-07 → A/H, U-45 → A/E, U-64-001 → M/H, U-64-002 → A/E를 모두 표현할 수 있다.

표현 가능한 요소:

- **precondition**(선택 필드) → NOT_APPLICABLE
- **file_scan / account_group**(목록형 관찰) → `empty`/`exists`/`not`/`in`/`not_in`으로 평가
- **NOT_APPLICABLE** = precondition 불충족(정상 결과, Error 아님)

> 다음 단계는 `file_scan`의 실제 설계/구현이다.
