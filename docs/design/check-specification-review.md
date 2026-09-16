# Check Specification 검증 리뷰

> `data/checks/linux/*.yaml`의 Technical Check 정의를 `docs/design/check-specification.md` 기준으로 검토하고,
> 설계에 영향을 줄 수 있는 문제를 중심으로 기록한다.

---

## 1. 전체 Check 검토 결과

| Check ID | type | targets | expect | automation | 검토 결과 |
| --- | --- | --- | --- | --- | --- |
| CK-lnx-U01-001 | config_value | config(PermitRootLogin) | eq "No" | auto | 일치 |
| CK-lnx-U01-002 | config_value | config×2(pam/securetty) | all(contains+not_contains) | auto | 일치 |
| CK-lnx-U05-001 | account_uid | account(uid, exclude root) | not_in [0] | auto | 일치 |
| CK-lnx-U16-001 | file_owner | file(owner) | eq "root" | auto | 일치 |
| CK-lnx-U16-002 | file_mode | file(mode) | mode_allowed | auto | 일치 |
| CK-lnx-U34-001 | service_status | service(finger, mechanisms) | eq disabled | auto | 일치 |
| CK-lnx-U64-001 | document | document(정책) | exists | manual | 일치 |
| CK-lnx-U64-002 | package_version | package(kernel) | any(ge/eq + value_ref) | semi | 일치 |

전반적으로 Check의 `id`/`type`/`targets`/`expect`/`automation`/`evidence` 필드는 설계와 일치한다.
수정이 필요했던 것은 `description` 필드뿐이다.

---

## 2. description 수정 원칙

`description`은 KISA 원문(purpose/pass/fail/detail)을 복사하는 필드가 아니라, **이 Technical Check가 시스템에서 무엇을 확인하는지 간결하게 설명**하는 필드다.

- 검사 대상을 명확히 표현한다.
- KISA 요구사항 문장이나 목적을 장황하게 옮기지 않는다.
- PASS/FAIL 조건을 반복하지 않는다.
- 실행 명령어를 넣지 않는다.
- 짧고 명확한 한국어 문장으로 작성한다.

---

## 3. 수정된 Check

모든 Check의 `description`을 위 원칙에 맞게 수정했다. (기술 필드는 변경 없음)

| Check ID | 수정 전 | 수정 후 |
| --- | --- | --- |
| CK-lnx-U01-001 | SSH root 직접 접속 차단 여부 | SSH 서버의 root 직접 원격 접속 허용 여부 확인 |
| CK-lnx-U01-002 | Telnet root 접속 제한 여부 | Telnet을 통한 root 직접 접속 제한 여부 확인 |
| CK-lnx-U05-001 | root 외 UID 0 계정 존재 여부 | /etc/passwd에서 UID 0 계정의 존재 여부 확인 |
| CK-lnx-U16-001 | /etc/passwd 소유자 확인 | /etc/passwd 파일의 소유자 확인 |
| CK-lnx-U16-002 | /etc/passwd 권한 확인 | /etc/passwd 파일의 Unix 권한 확인 |
| CK-lnx-U34-001 | Finger 서비스 비활성화 여부 | Finger 서비스의 비활성화 여부 확인 |
| CK-lnx-U64-001 | 패치 적용 정책 수립 여부 | 패치 적용 정책 문서의 존재 여부 확인 |
| CK-lnx-U64-002 | 보안 패치 적용 상태 확인 | 커널 보안 패치의 최신 버전 적용 여부 확인 |

---

## 4. 설계와 불일치했던 부분

이번 검토에서는 **Check YAML이 설계를 잘못 사용한 사례(구조적 불일치)는 없었다.**

- ID 규칙(`CK-lnx-Uxx-00N`), `targets[]` 구조, `expect`(leaf/all/any), `mode_allowed`, `mechanisms`, `value_ref`, `automation`(auto/semi/manual) 모두 설계와 일치.
- 파일 권한을 숫자 비교(`le`/`lt`)로 처리한 경우 없음.
- KISA title/severity/source/pass·fail 원문을 Check에 중복 저장하지 않음.

`description`의 기존 작성 방식은 설계의 "이 Check의 초점"이라는 정의에 비해 추상적이어서, 이번 원칙에 맞게 구체화했다(내용 품질 개선이며 구조 불일치는 아님).

---

## 5. 현재 Specification으로 표현하기 어려운 부분

1. **NOT_APPLICABLE과 PASS의 경계 (미결)**
   - U-34: finger가 시스템에 없으면 `NOT_APPLICABLE`인지 `PASS`(비활성과 동치)인지 Check 레벨에서 정해지지 않는다. KISA 원문("비활성화 = 양호")과 상태 정의("대상 부재 = NOT_APPLICABLE") 사이 경계다.

2. **"원격터미널 미사용 = 양호"의 표현 (미결)**
   - U-01 원문의 OR 조건("미사용 **또는** 차단") 중 "미사용"은 개별 Check로 표현되지 않고, 여러 Check 결과를 집계하는 단계의 몫으로 남아 있다.

3. **`config_value`의 key 시맨틱 한계**
   - `/etc/securetty`(U-01-002)는 key=value 형식이 아니라 라인 목록이다. `key: pts` + `not_contains`로 표현은 가능하지만, `config_value`의 "키-값" 의미와 다소 어긋난다.

4. **`value_ref`의 해석 (미정)**
   - U-64-002의 `vendor_advisory`/`policy`를 어떻게 실제 값으로 해석할지는 정의되지 않아, 이 Check는 실행 시점까지 판정 불가 상태다.

5. **설정값의 표기 차이**
   - `PermitRootLogin`의 값("No" vs "no")은 OS/버전에 따라 대소문자가 다를 수 있어, `eq` 비교 시 구현에서 정규화가 필요할 수 있다.

---

## 6. 향후 Specification 수정이 필요한 부분

| # | 수정 필요 사항 | 우선순위 |
| --- | --- | --- |
| 1 | target의 `key`(config) vs `field`(file/account) 명칭 통일 | 높음 |
| 2 | evidence `kind`와 target `kind`의 어휘 관계 명시(config target → file evidence) | 높음 |
| 3 | NOT_APPLICABLE과 PASS의 경계 규칙 정의(대상 부재 처리) | 높음 |
| 4 | `not` 복합 노드의 필요성 재검토(부정 연산자로 충분한지) | 중간 |
| 5 | `config_value`가 key=value 외 라인 목록/리스트 파일도 다루는지 명시 | 중간 |
| 6 | `description`의 목적을 "기술적 검사 대상의 간결한 설명"으로 명세에 반영 | 중간 |

이 항목들은 `docs/design/check-specification.md`의 다음 수정 시 반영한다. 이번 검토에서는 설계 문서를 수정하지 않았다.

---

## 7. U-01-002 NOT_APPLICABLE 심층 분석

> `CK-lnx-U01-002`가 실제 실행에서 `/etc/securetty` 부재로 `NOT_APPLICABLE`을 반환한 사례를 분석한다.

### 7.1 판단 요약

현재 결과(`NOT_APPLICABLE`)는 **결과적으로는 합리적이나, 도달 경로가 의미론적으로 옳지 않다.**

- 이 시스템은 Telnet 서버(`in.telnetd`)가 설치되지 않아 Telnet을 사용하지 않는다. 따라서 "Telnet root 직접 접속 제한"은 실제로 적용 대상이 아니다 → `NOT_APPLICABLE`이라는 결과 자체는 타당하다.
- 그러나 Engine은 이 결론을 "`/etc/securetty` 파일이 없음"이라는 **파일 존재 여부**만으로 도출했지, "Telnet 서비스를 사용하지 않음"이라는 **실제 적용성 근거**로 도출하지 않았다.

### 7.2 KISA 원문 기준으로 필요한 조건

KISA U-01 원문(`data/kisa/linux/account.yaml`, 상세가이드 01장):

- 판단 기준: "**원격터미널 서비스를 사용하지 않거나**, 사용 시 root 직접 접속을 차단한 경우" → 양호
- LINUX Telnet 조치: (1) `/etc/pam.d/login`에 `pam_securetty.so` 추가, (2) `/etc/securetty`의 `pts/` 주석·제거
- 원문 주석: "/etc/securetty 파일 내 pts/x 설정이 존재하면 PAM 모듈과 무관하게 root 접속을 허용하므로 **반드시 제거**"
- 원문 주석: "CentOS 8, Ubuntu 20.04 이상부터 `/etc/securetty` 파일이 **존재하지 않으며** 기본적으로 **Telnet 서비스가 비활성화**됨"

따라서 원문은 두 가지를 전제로 한다:

```text
Telnet 미사용            → 양호 (root 제한 검사 자체가 불필요)
Telnet 사용 + root 차단   → 양호
Telnet 사용 + root 허용   → 취약
```

즉 **"Telnet 사용 여부"가 root 제한 검사의 선행 조건**이며, `/etc/securetty` 부재는 "Telnet 비활성화"를 의미하는 신호다.

### 7.3 현재 YAML의 문제점

현재 `CK-lnx-U01-002`는 Telnet 사용 여부를 확인하지 않고 곧바로 `pam_securetty.so`와 `securetty`를 검사한다.

```yaml
targets:
  - { kind: config, path: /etc/pam.d/login, key: pam_securetty.so }
  - { kind: config, path: /etc/securetty, key: pts }
expect:
  all: [contains pam_securetty.so, not_contains pts]
```

문제:
1. **적용성(applicability)과 검사 자체를 혼동**한다. "Telnet 미사용 → 적용 안 함"이라는 선행 판단이 없다.
2. `/etc/securetty` 부재를 `not_contains "pts"`로 표현하면, "파일이 없어서 pts가 없다"가 아니라 "파일이 없음"이 Engine의 NOT_APPLICABLE 분기로 새어 나간다.
3. 원문이 구분하는 두 상황(Telnet 미사용 vs 사용+미제한)을 하나의 Check가 구분하지 못한다.

### 7.4 Engine의 NOT_APPLICABLE 처리 문제

Engine은 `collector`가 "대상 파일 없음(`missing_target`)"을 보고하면 무조건 `NOT_APPLICABLE`을 반환한다.

- 이 규칙은 **너무 일반적**이다. 예를 들어 `CK-lnx-U16-001`(/etc/passwd 소유자)에서 `/etc/passwd`가 없으면 "적용 불가"가 아니라 **심각한 오류/취약**으로 다뤄야 하는데, 현재는 `NOT_APPLICABLE`이 된다.
- 근본 원인은 **Specification의 NOT_APPLICABLE 정의 자체가 "파일 없음"과 "Check 미적용"을 동일시**하고 있다는 점이다.

| 상태 | Specification 현재 정의 | 실제 의미상 구분해야 할 것 |
| --- | --- | --- |
| `NOT_APPLICABLE` | "점검 대상(파일 등)이 존재하지 않아 적용 불가" | "Check가 이 환경에 적용되지 않음"(서비스 미사용 등) |
| `ERROR` | "실행/판정 오류" | "필수 대상 파일을 읽을 수 없음" |

즉, **"파일이 없다"는 수집 단계의 사실**이고, 그 의미(미적용/오류/취약)는 Check의 적용성 조건에 따라 달라진다. 현재는 이 구분이 없다.

### 7.5 개선안 (제안, 이번엔 미적용)

1. **Check 분리**: "Telnet 사용 여부"와 "Telnet 사용 시 root 제한"을 분리한다.

   ```text
   CK-lnx-U01-002  Telnet 서비스 사용 여부 (service_status)
   CK-lnx-U01-003  Telnet 사용 시 root 직접 접속 제한 (pam_securetty + securetty)
   ```

   - 이는 KISA 원문 판단 기준("미사용 **또는** 차단")에 부합하며, 임의 확장이 아니다.

2. **Specification에 적용성(applicability) 표현 추가**: NOT_APPLICABLE을 "파일 없음"이 아니라 Check가 선언한 적용성 조건으로 판단하도록 한다.

3. **Engine의 파일 부재 처리 재정의**: "파일 없음 → 무조건 NOT_APPLICABLE" 대신, Check의 적용성 조건에 따라 NOT_APPLICABLE/ERROR/FAIL을 결정하도록 한다. (예: 필수 파일 부재는 ERROR/FAIL, 선택적 신호 파일 부재는 Check 로직으로 처리)

> 이번 검토에서는 Specification·YAML·Engine을 수정하지 않았다. 위 개선안은 다음 설계 수정 시 반영 대상이다.

---

## 8. U-01 분리 반영 및 설계 판단

7절의 개선안을 반영해 U-01을 다음 3개 Check로 분리했다.

| Check ID | type | 목적 |
| --- | --- | --- |
| CK-lnx-U01-001 | config_value | SSH root 직접 접속 제한 |
| CK-lnx-U01-002 | service_status | Telnet 원격터미널 서비스 사용 여부 |
| CK-lnx-U01-003 | config_value | Telnet 사용 시 root 직접 접속 제한 |

이 과정에서 다음 설계 판단을 내렸다. (이후 `check-specification.md` 반영 필요)

### 8.1 `precondition` 개념 도입

CK-lnx-U01-003은 "Telnet 사용 중"일 때만 적용된다. 이 적용성(applicability)을 표현하기 위해 Check에 **선택적 `precondition`**을 추가했다.

```yaml
precondition:
  type: service_status
  targets: [{ kind: service, name: telnet, mechanisms: [...] }]
  expect: { op: eq, value: enabled }
```

- precondition 불충족 → `NOT_APPLICABLE`.
- 이는 7절에서 지적한 "적용성은 파일 부재가 아니라 Check가 선언해야 한다"는 원칙의 최소 구현이다.

### 8.2 NOT_APPLICABLE 판단 기준 변경

Engine의 "대상 파일 없음" 처리를 차별화했다.

| 상황 | 결과 |
| --- | --- |
| precondition 불충족 | NOT_APPLICABLE |
| precondition 충족 + 필수 파일 없음 | ERROR (적용 대상이지만 판정 불가) |
| precondition 없음 + 파일 없음 | NOT_APPLICABLE (기존 U-01-001 동작 유지) |

즉, "파일 없음 → 무조건 NOT_APPLICABLE"을 폐기하고, 적용성은 `precondition`이 결정하도록 했다.

### 8.3 config target의 key 생략 → 전체 내용 수집

`/etc/pam.d/login`(pam_securetty.so 포함 여부)·`/etc/securetty`(pts 포함 여부)는 key=value 형식이 아니라 **파일 내용 전체에 대한 contains/not_contains** 검사다. 이를 위해 config target에서 `key`를 생략하면 **파일 전체 내용**을 관측값으로 반환하도록 수집기를 확장했다.

```yaml
targets:
  - { kind: config, path: /etc/pam.d/login }        # key 없음 → 전체 내용
  - { kind: config, path: /etc/securetty }
expect:
  all:
    - { target: pam, op: contains, value: "pam_securetty.so" }
    - { target: securetty, op: not_contains, value: "pts" }
```

### 8.4 남은 과제

- `precondition`의 정식 스키마·필드명 확정과 `check-specification.md` 반영.
- CK-lnx-U01-002의 `FAIL`이 "Telnet 사용 중"을 의미함을 명세에 명확히 표기(취약 판정이 아님).
- `service_status`의 systemd 메커니즘은 단순 파일 휴리스틱이며, 실제 런타임 상태 확인은 미구현.

---

## 9. Evidence 표준화 (관찰 사실 vs 판정 결과 분리)

Evidence를 공통 구조 `target / attribute / observed / expected`로 통일했다.

### 9.1 원칙

- **Result** = 최종 평가 결과(PASS/FAIL/…). **Evidence** = 실제로 관찰한 사실.
- `observed`는 **원시 관찰값**만 의미한다(예: 설정 파일의 `yes`). 종합 해석("미사용", "차단됨")은 넣지 않는다.
- 모든 Evidence 항목은 `target`(대상) / `attribute`(속성) / `observed`(관찰값) 구조를 갖고, 단일값 `eq`/`ne` 비교일 때만 `expected`를 추가한다.

### 9.2 변경

| Check | 변경 후 Evidence |
| --- | --- |
| CK-lnx-U01-001 (config) | `target=/etc/ssh/sshd_config` · `attribute=PermitRootLogin` · `observed=yes` · `expected=No` |
| CK-lnx-U01-002 (service) | systemd/xinetd/inetd/process/tcp23 각각을 `target/attribute/observed` 항목으로 분리 |
| CK-lnx-U01-003 (NOT_APPLICABLE) | `target=CK-lnx-U01-002 · attribute=result · observed=PASS` 참조 + 관찰 사실 |

- `observed=disabled`(종합 판정값)를 제거하고, 각 관찰 사실을 Evidence 항목으로 남긴다.
- NOT_APPLICABLE은 "Error"가 아니라 정상 Result이며, N/A 근거(U-01-002 결과 참조 + 관찰 사실)를 Evidence로 남긴다.
