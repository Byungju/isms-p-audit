# Check Specification 설계 검증

> `docs/design/check-specification.md`의 설계가 실제 KISA Linux 점검항목을
> 잘 표현하는지, 5개 항목(U-01, U-05, U-16, U-34, U-64)을 샘플로 작성해 검증한다.
>
> 규칙 준수:
> - `data/kisa/linux/*.yaml`, `data/mappings`는 수정하지 않음.
> - Shell/Python/C 코드 작성 없음. Check Specification(정의)만 작성.
> - 새 type·새 KISA 항목·새 매핑은 만들지 않음. 필요한 경우 "설계 이슈"로 기록.

---

## 1. 검증 목적

현재 Check Specification 설계가 실제 KISA 항목의 **판정 조건을 기계 판정 가능하게 구조화**할 수 있는지,
그리고 그 과정에서 **설계의 빈틈(부족한 연산자, 불충분한 type, ID 규칙 모순, 중복 데이터)**이 드러나는지를 확인한다.

검증 방식: 각 항목의 원문 `pass`/`fail`을 Check Spec으로 옮겨보고, 옮기면서 막히는 지점을 기록한다.

---

## 2. 대상 KISA 항목

| ID | 항목 | 중요도 | 현재 automation | 원문 판단 기준(요약) |
| --- | --- | --- | --- | --- |
| U-01 | root 계정 원격 접속 제한 | 상 | AUTO | 원격터미널 미사용 또는 root 직접 접속 차단 시 양호 |
| U-05 | root 이외 UID 0 계정 존재 여부 | 상 | AUTO | UID 0 계정(root 제외) 없으면 양호 |
| U-16 | /etc/passwd 소유자 및 권한 | 상 | AUTO | 소유자 root + 권한 644 이하 |
| U-34 | Finger 서비스 비활성화 | 상 | AUTO | Finger 비활성화 시 양호 |
| U-64 | 최신 보안 패치 적용 | 상 | SEMI | 패치 정책 수립 + 주기적 관리·적용 |

이 5개는 각각 다른 특성을 지닌다: U-05(단순), U-16(복합 AND), U-01(조건 OR + 다중 경로), U-34(서비스 프레임워크별 상이), U-64(정책 + 기술 혼합 + 외부 참조).

---

## 3. U-01 Check Specification

### 원문 판단 기준
- **pass**: 원격터미널 서비스를 사용하지 않거나, 사용 시 root 직접 접속을 차단한 경우
- **fail**: 원격터미널 서비스 사용 시 root 직접 접속을 허용한 경우

### 구조화

원문은 (a) "원격터미널 미사용" 또는 (b) "root 직접 접속 차단"의 **OR** 조건이다. (b)는 다시 SSH/Telnet **두 경로**로 나뉜다.

```yaml
- id: CK-lnx-U01-1
  kisa_ref: U-01
  title: SSH root 직접 접속 제한
  type: config_value
  automation: auto
  platforms: [linux]
  severity: 상
  target:
    kind: config_value
    setting: PermitRootLogin
  expect:
    op: eq
    value: "No"
  evidence:
    - { type: file, path: /etc/ssh/sshd_config, field: PermitRootLogin }

- id: CK-lnx-U01-2
  kisa_ref: U-01
  title: Telnet root 접속 제한 (securetty/PAM)
  type: config_value
  automation: auto
  platforms: [linux]
  severity: 상
  target:
    kind: config_value
    setting: pam_securetty
  expect:
    op: eq
    value: enabled
  evidence:
    - { type: file, path: /etc/pam.d/login }
    - { type: file, path: /etc/securetty }
```

### 구조화 설명
- "root 직접 접속 차단"을 **SSH(PermitRootLogin=No)**와 **Telnet(pam_securetty/securetty)** 두 Check로 분리했다(1:N).
- 원문의 "원격터미널 미사용 → 양호"는 Check 레벨로 내려오면 **NOT_APPLICABLE**로 표현되어야 하는데, 현재 `expect`로는 표현되지 않는다(→ 설계 이슈 #1).

---

## 4. U-05 Check Specification

### 원문 판단 기준
- **pass**: root 계정과 동일한 UID를 갖는 계정이 존재하지 않는 경우
- **fail**: root 계정과 동일한 UID를 갖는 계정이 존재하는 경우

### 구조화

```yaml
- id: CK-lnx-U05
  kisa_ref: U-05
  title: root 외 UID 0 계정 존재 여부
  type: account_uid
  automation: auto
  platforms: [linux]
  severity: 상
  target:
    kind: account_uid
    source: /etc/passwd
    field: uid
    exclude: [root]
  expect:
    op: not_in
    value: [0]
  evidence:
    - { type: account, source: /etc/passwd, field: uid }
```

### 구조화 설명
- 원문의 "root 계정과 동일한 UID(=0)"를 `expect: {op: not_in, value: [0]}`로 표현.
- "root 이외의"는 `target.exclude: [root]`로 처리.
- `not_in` 연산자 하나로 표현 가능 → **설계가 충분**한 항목.

---

## 5. U-16 Check Specification

### 원문 판단 기준
- **pass**: 소유자가 root이고, 권한이 644 이하인 경우
- **fail**: 소유자가 root가 아니거나, 권한이 644 이하가 아닌 경우

### 구조화

원문은 "소유자 = root" **AND** "권한 ≤ 644"의 복합 조건이다.

```yaml
- id: CK-lnx-U16-1
  kisa_ref: U-16
  title: /etc/passwd 소유자
  type: file_owner
  automation: auto
  platforms: [linux]
  severity: 상
  target: { path: /etc/passwd, field: owner }
  expect: { op: eq, value: "root" }
  evidence:
    - { type: file, path: /etc/passwd, field: owner }

- id: CK-lnx-U16-2
  kisa_ref: U-16
  title: /etc/passwd 권한
  type: file_mode
  automation: auto
  platforms: [linux]
  severity: 상
  target: { path: /etc/passwd, field: mode }
  expect: { op: le, value: "0644" }
  evidence:
    - { type: file, path: /etc/passwd, field: mode }
```

### 구조화 설명
- 소유자·권한을 두 Check로 분리(판정 책임 분리). U-16 최종은 AND 집계.
- `op: eq`(소유자)는 명확하나, `op: le, value: "0644"`는 **숫자 대소 비교가 파일 권한 비트의 의미와 정확히 일치하지 않는다**(→ 설계 이슈 #3).

---

## 6. U-34 Check Specification

### 원문 판단 기준
- **pass**: Finger 서비스가 비활성화된 경우
- **fail**: Finger 서비스가 활성화된 경우

### 구조화

```yaml
- id: CK-lnx-U34
  kisa_ref: U-34
  title: Finger 서비스 비활성화
  type: service_status
  automation: auto
  platforms: [linux]
  severity: 상
  target:
    kind: service
    name: finger
  expect:
    op: eq
    value: disabled
  evidence:
    - { type: service, name: finger, field: status }
```

### 구조화 설명
- "Finger 비활성화"를 `service_status` + `expect: {op: eq, value: disabled}`로 표현.
- 그러나 원본 점검 사례를 보면 finger는 **inetd/xinetd/SMF/systemd** 등 프레임워크별로 점검 방식이 다르다.
  - inetd: `/etc/inetd.conf` 주석 처리
  - xinetd: `/etc/xinetd.d/finger`의 `disable = yes`
  - Solaris SMF: `inetadm -d`
- `service_status` 하나로는 이 **메커니즘 차이**를 표현하지 못한다(→ 설계 이슈 #4).
- "Finger가 아예 설치되지 않은 경우"가 양호(비활성)인지 NOT_APPLICABLE인지도 판단 기준에 명시되지 않았다(→ 설계 이슈 #5).

---

## 7. U-64 Check Specification

### 원문 판단 기준
- **pass**: 패치 적용 정책을 수립하여 주기적으로 패치 관리하며, 패치 관련 내용을 확인·적용한 경우
- **fail**: 패치 적용 정책 미수립, 주기적 관리 미흡, 패치 내용 미확인·미적용인 경우

### 구조화

원문은 (a) **정책 수립**(관리적)과 (b) **패치 적용 상태**(기술적)의 두 축이 결합된 조건이다. 둘은 성격이 전혀 다르므로 분리해야 한다.

```yaml
# (a) 정책 수립 여부 — 기술적 type으로 표현 불가 (MANUAL)
- id: CK-lnx-U64-1
  kisa_ref: U-64
  title: 패치 관리 정책 수립 여부
  type: (해당 없음 — policy/document)
  automation: manual
  platforms: [linux]
  severity: 상
  target:
    kind: policy
    name: 패치 적용 정책
  expect:
    op: exists
  evidence:
    - { type: document, name: 패치 적용 정책/절차 }

# (b) 패치 적용 상태 — 외부 참조(최신 버전) 필요 (SEMI)
- id: CK-lnx-U64-2
  kisa_ref: U-64
  title: 보안 패치 적용 상태
  type: package_version
  automation: semi
  platforms: [linux]
  severity: 상
  target:
    kind: package
    name: kernel        # OS별 대상 패키지 상이
  expect:
    op: ge
    value: (최신 보안 패치 버전 — 외부 참조 필요)
  evidence:
    - { type: package, name: kernel, field: version }
    - { type: command_output, note: 벤더 권고사항 확인 내역 }
```

### 구조화 설명
- (a) "정책 수립"은 파일/계정/서비스/패키지가 아니라 **문서·절차** 검사다. 현재 type 목록에 없음(→ 설계 이슈 #6, 새 type 추가 대신 이슈로 기록).
- (b) "최신 패치"의 `value`는 **정적 값이 아니라 외부 취약점 DB/벤더 권고에 의존하는 동적 기준**이다. `op: ge`로 표현하되, `value`를 어디서 가져올지가 미해결(→ 설계 이슈 #7).
- `automation`이 한 항목 내에서 **manual(정책)과 semi(패치)**로 갈린다. KISA 레벨의 `automation: SEMI`가 Check 레벨에서 더 세분화됨을 보여준다.

---

## 8. 현재 설계로 표현 가능한 부분

| 항목 | 표현 가능 여부 | 근거 |
| --- | --- | --- |
| U-05 | ✅ 완전 | 단일 조건, `not_in`으로 충분 |
| U-16 | ✅ (단, 권한 비교에 주의) | `eq` + `le` 두 Check로 AND 분해 가능 |
| U-01 | ⚠️ 부분 | SSH/Telnet 분해는 가능, "미사용→양호" OR 로직은 불가 |
| U-34 | ⚠️ 부분 | "비활성화" 단일 조건은 가능, 프레임워크 차이는 미표현 |
| U-64 | ⚠️ 부분 | 패치 버전 비교 골격은 가능, 정책/외부 참조는 미표현 |

- **단순 단일 조건 항목**(U-05)은 설계가 충분히 표현한다.
- **복합 AND**(U-16)는 복수 Check + 집계로 표현 가능하다.
- **Evidence와 판정 분리**(9절 설계)는 5개 모두 일관되게 적용 가능했다.

---

## 9. 현재 설계로 표현하기 어려운 부분

1. **조건의 논리 결합(OR/AND)**: U-01의 "미사용 **또는** 차단", U-16의 "소유자 **그리고** 권한". 현재 `expect`는 단일 `op/value`만 허용하고, 다중 조건의 결합 방식(AND/OR)을 표현할 필드가 없다.

2. **다중 대상/다중 값**: U-01 Telnet은 `/etc/pam.d/login` + `/etc/securetty` **두 파일**을 함께 봐야 한다. `target`이 단일 대상 가정이다.

3. **서비스 점검의 메커니즘 추상화**: U-34처럼 "서비스 비활성화"가 inetd/xinetd/SMF/systemd로 갈리는 것을 `service_status`가 담지 못한다.

4. **동적/외부 기준값**: U-64의 "최신 패치"는 정적 value로 쓸 수 없다. 취약점 DB·벤더 권고라는 외부 참조가 필요하다.

5. **비기술적(정책·절차) 검사**: U-64(a)의 "정책 수립"은 현재 type 목록에 없다.

---

## 10. 발견된 설계 문제

### 문제 1: 조건 결합(AND/OR) 표현 부재
`expect`가 단일 조건이라, 원문의 "A 또는 B", "A 그리고 B"를 표현할 방법이 없다.
- 영향: U-01(OR), U-16(AND), U-27(복수 조건), U-60(복수 조건) 등 다수 항목이 영향을 받는다.

### 문제 2: `target`이 단일 대상 가정
U-01-Telnet은 두 파일, U-02(비밀번호 정책)는 여러 PAM 파일을 봐야 한다. `target`을 리스트로 확장하거나 `targets[]`가 필요하다.

### 문제 3: 파일 권한 `op: le`의 의미 불일치
"권한 644 이하"를 `op: le, value: "0644"`로 표현하면, 0640·0600 등은 숫자상 이하라 통과하지만, **권한 비트의 의미**(어떤 비트가 허용되는가)와 숫자 비교가 항상 일치하지 않는다.
- 예: 0666은 숫자상 0644보다 크지만(FAIL), 0604는 0644보다 작다(그룹 r 비트가 빠짐 → 더 제한적이므로 실제로는 양호). 숫자 비교는 "더 제한적"과 "더 느슨"을 제대로 구분하지 못한다.
- 개선: `mode` 검사는 `expect: {op: le}` 대신 **허용 비트 마스크** 또는 **금지 비트 마스크** 방식이 필요할 수 있다.

### 문제 4: `service_status` type의 불충분
"서비스 상태"를 점검하는 메커니즘이 inetd(설정 주석), xinetd(disable 옵션), SMF(inetadm), systemd(unit state)로 나뉜다. 단일 `service_status`로는 표현이 어렵고, `service_status`의 **하위 메커니즘(sub-type/variant)**이 필요하다. (새 type 추가가 아니라, 기존 type의 변형 표현 이슈)

### 문제 5: NOT_APPLICABLE과 PASS의 경계 모호
"서비스가 설치되지 않음"이 양호(비활성)인지, 적용 대상 아님인지가 원문에 명시되지 않았다.
- U-34: finger 미설치 → "비활성화"로 PASS? 아니면 NOT_APPLICABLE?
- U-01: 원격터미널 미사용 → 원문은 "양호"로 명시(PASS). 서비스 미설치는 이와 구분되어야 함.
- **설계 결정 필요**: 서비스 미설치/미구성은 기본적으로 "비활성"과 동치로 볼 것인지, 별도 상태로 둘 것인지.

### 문제 6: 비기술적(정책/문서) 검사의 type 부재
U-64(a)의 "정책 수립"은 기술적 type에 매핑되지 않는다. 규칙에 따라 새 type을 추가하지 않고 이슈로 기록한다.
- 시사점: KISA 기술점검에도 "정책 수립"류 조건이 존재(U-64, U-66 등). 순수 기술 type만으로는 전체를 덮을 수 없다.

### 문제 7: 외부 참조(취약점 DB/벤더 권고) 모델 부재
"최신 패치"·"취약 버전 아님"(U-45, U-49, U-64)은 외부 취약점 정보에 의존한다. `expect.value`가 정적이면 표현 불가. 외부 데이터 소스 참조 필드가 필요하다.

### 문제 8: Check ID 규칙의 일관성
설계 문서의 예시에서 `CK-lnx-U16`(단일)과 `CK-lnx-U16-2`(분리 시)가 혼재한다. 규칙은 "단일이면 seq 생략, 복수면 1부터"인데, **한 항목을 2개로 분리하는 순간 기존 단일 ID의 seq가 붙는 문제**가 생긴다. 즉, ID가 "분해 여부"에 따라 불안정해진다.
- 개선: 처음부터 **모든 Check에 seq를 붙이거나**, 단일/복수와 무관하게 안정적인 ID를 부여하는 규칙이 필요하다.

### 문제 9: KISA 항목 속성의 중복
`kisa_ref`, `title`, `severity`, `source` 등은 한 KISA 항목에서 파생된 것이며, 한 항목을 N개 Check로 분해하면 **N번 반복 저장**된다. 이는 Check가 KISA 데이터를 중복 보유하는 것이 된다.

---

## 11. 수정이 필요한 설계

| # | 수정 사항 | 우선순위 |
| --- | --- | --- |
| 1 | `expect`를 단일 조건 → **조건 리스트 + 결합 연산자(and/or)**로 확장 | 높음 |
| 2 | `target`을 단일 대상 → **`targets[]`(복수 대상)**로 확장 | 높음 |
| 3 | 파일 권한 검사에 `op: le` 대신 **허용/금지 비트 마스크** 또는 전용 `file_mode` 판정 규칙 도입 | 중간 |
| 4 | `service_status`에 **하위 메커니즘(inetd/xinetd/systemd/SMF)** 표현 방법 정의 | 중간 |
| 5 | **NOT_APPLICABLE vs PASS 경계 규칙** 명시(서비스 미설치 처리) | 높음 |
| 6 | 비기술적 검사를 위한 별도 분류(예: `automation: manual` + `type` 없는 정책 체크) 정의 | 중간 |
| 7 | 외부 참조(취약점 DB/벤더 권고)를 위한 `expect.ref`(외부 소스) 도입 | 중간 |
| 8 | Check ID 규칙 재정의(seq 일관성) | 낮음 |
| 9 | Check에서 KISA 파생 속성(severity/source) 중복 제거(참조로 대체) | 낮음 |

---

## 12. 다음 단계 제안

1. **판정 모델 확정**: `expect`의 조건 결합(and/or), 복수 대상, file_mode 비트 마스크 규칙을 설계 문서에 반영.
2. **상태 경계 규칙 확정**: NOT_APPLICABLE(미설치/미구성)과 PASS(비활성)의 구분 기준을 명문화.
3. **서비스 점검 추상화**: service_status의 메커니즘 변형(initsystem/unit) 표현 방법을 정립.
4. **외부 참조 모델**: 패치/버전 검사(U-45/49/64)의 취약점 DB 연동 방식을 설계.
5. **ID 규칙 안정화**: Check 분해와 무관한 안정적 ID 규칙을 확정.
6. **대표 샘플 확장 검증**: 나머지 유형(서비스 다수, 계정 중복, SUID/SGID 등)으로 검증 범위를 넓혀 type 완결성 확인.
