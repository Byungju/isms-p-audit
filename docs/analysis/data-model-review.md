# 데이터 모델 리뷰 (Data Model Review)

> 이 문서는 `data/` 디렉터리의 YAML 데이터 모델을 점검 엔진 확장 관점에서 리뷰한 결과다.
> 현재 YAML은 수정하지 않았으며, 코드도 작성하지 않았다. 개선안은 권고(제안)로만 기술한다.

---

## 1. 현재 데이터 모델 개요

```
data/
├── isms-p/
│   ├── criteria.yaml          # ISMS-P 인증기준 (101개)
│   └── check-items.yaml       # ISMS-P 세부점검항목 (101개 기준 / 328개 확인사항)
├── kisa/
│   └── linux/
│       ├── account.yaml       # U-01 ~ U-13 (13개)
│       ├── file.yaml          # U-14 ~ U-33 (20개)
│       ├── service.yaml       # U-34 ~ U-63 (30개)
│       ├── patch.yaml         # U-64 (1개)
│       └── logging.yaml       # U-65 ~ U-67 (3개)
└── mappings/
    └── isms-p-to-linux.yaml   # ISMS-P → KISA Linux 매핑 (12개)
```

규모 요약:

| 파일 | 엔티티 | 수량 |
| --- | --- | --- |
| criteria.yaml | 인증기준(criteria) | 101 |
| check-items.yaml | 세부점검항목(items) / 확인사항(checks) | 101 / 328 |
| kisa/linux/*.yaml | KISA 점검항목 | 67 (AUTO 56, SEMI 11, MANUAL 0) |
| mappings | ISMS-P→KISA 매핑 | 12 (kisa 참조 80건) |

---

## 2. 파일별 역할

| 파일 | 역할 | 핵심 필드 |
| --- | --- | --- |
| `criteria.yaml` | ISMS-P 인증기준(요구사항 문장)의 원본 텍스트 보관 | `areas[].fields[].criteria[].{id, name, text}` |
| `check-items.yaml` | 인증기준을 확인 질문(체크리스트)으로 세분화 | `areas[].fields[].items[].{id, name, detail, checks[]}` |
| `kisa/linux/*.yaml` | KISA 기술적 점검 항목 + 판단 기준 | `items[].{id, name, severity, target, purpose, pass, fail, automation, evidence, isms_p}` |
| `mappings/isms-p-to-linux.yaml` | ISMS-P 인증기준 → KISA 점검항목 연관(해석) | `mappings[].{isms_p_criterion, name, kisa_items[]}` |

각 파일의 **책임은 분명히 분리**되어 있으나, 일부 데이터가 역할 경계를 넘어 중복 저장되고 있다(6절 참조).

---

## 3. 데이터 관계

현재 관계는 **문자열 ID를 통한 느슨한 참조**로만 연결되어 있다.

```
criteria.yaml  ──(id 동일)──  check-items.yaml   (기준 텍스트/이름 공유, 참조 필드 없음)
      │
      │  (문자열 "2.5.4" 로 참조, 링크 없음)
      ▼
mappings/isms-p-to-linux.yaml ──(문자열 "U-01" 로 참조)── kisa/linux/*.yaml
      ▲
      └── kisa/linux/*.yaml 의 items[].isms_p 필드에도 동일 관계가 역방향으로 저장됨
```

- 참조는 모두 **ID 문자열**(예: `"2.5.4"`, `"U-01"`)이며, 파일 간 **실제 링크/외래키는 없다.**
- 무결성(참조 대상 존재 여부)은 사람이 수작업으로만 보장할 수 있다.
- `criteria.yaml` ↔ `check-items.yaml` 사이에는 **어떤 참조 필드도 없다.** 두 파일은 단지 ID 체계를 공유할 뿐이다.

---

## 4. 잘 설계된 부분

1. **계층 구조가 명확하다.** ISMS-P는 `areas → fields → criteria`(3단계), KISA는 `platform/category → items`로 일관성 있게 나뉜다.
2. **출처(source) 블록**이 각 파일에 명시되어 문서명·버전·페이지/장을 추적할 수 있다(`kisa/linux/*.yaml`의 `source.chapter/page`).
3. **ID 전역 유일성**이 현재 범위에서는 유지된다. ISMS-P는 `N.N.N`, KISA는 `U-xx`로 충돌이 없다.
4. **N:M 매핑을 표현할 수 있다.** `kisa_items[]` 리스트와 `isms_p[]` 리스트로 다대다가 표현 가능하다.
5. **automation 분류가 점검항목에 붙어 있다.** 실행 엔진이 AUTO/SEMI를 참고해 구현 범위를 결정할 수 있다.
6. `pass`/`fail`이 **원본 가이드의 "양호/취약" 판단 기준을 그대로 보존**하고 있어 원문 추적이 가능하다.

---

## 5. 문제점

### 5-1. 매핑이 양방향으로 중복 저장됨 (가장 큰 문제)

동일한 연관 관계가 **서로 다른 두 파일에 역방향으로 저장**되어 있다.

- `data/kisa/linux/*.yaml`의 `items[].isms_p` (KISA → ISMS-P)
- `data/mappings/isms-p-to-linux.yaml`의 `mappings[].kisa_items[]` (ISMS-P → KISA)

검증 결과 두 곳의 참조 건수가 **정확히 80건으로 동일**하다(동일 관계의 중복). 한쪽을 수정하면 다른 쪽이 어긋나는 드리프트(drift)가 발생할 수밖에 없다.

### 5-2. 인증기준 텍스트가 두 파일에 중복

`criteria.yaml`의 `criteria[].text`와 `check-items.yaml`의 `items[].detail`은 **동일한 문장**(원문 인증기준 문구)이다. 실제로 2.5.4 등에서 같은 내용이 두 파일에 저장되어 있다. 하나의 기준 문구를 두 곳에서 관리하는 것은 SSOT 위반이다.

### 5-3. 기준 이름(id+name)이 세 곳에 중복

동일한 인증기준의 `name`이 다음 세 곳에 반복된다.

- `criteria.yaml` `criteria[].name`
- `check-items.yaml` `items[].name`
- `mappings/isms-p-to-linux.yaml` `mappings[].name`

예: `2.5.1`의 "사용자 계정 관리"가 3개 파일에 저장되어 있다. 이름 변경 시 3곳을 동시에 고쳐야 한다.

### 5-4. 실행 가능한 점검 정보가 없다

`pass`/`fail`이 한글 산문(예: "소유자가 root이고, 권한이 644 이하인 경우")이라 **엔진이 기계적으로 판정할 수 없다.** 실제 점검 명령(예: `ls -l /etc/passwd`, `grep PermitRootLogin /etc/ssh/sshd_config`)이나 구조화된 기대값(owner=root, mode<=644)이 데이터에 없다. 현재 모델은 "사양(spec)"일 뿐 "실행 가능한 체크"가 아니다.

### 5-5. 사실과 해석이 같은 객체에 혼재

`kisa/linux/*.yaml`의 각 item에 `pass`/`fail`(원문 추출 = 사실)과 `isms_p`(프로젝트가 만든 매핑 = 해석)가 같은 레벨에 병치되어 있다. 어느 필드가 원본 근거이고 어느 필드가 해석인지가 구조적으로 구분되지 않는다.

### 5-6. `target`/`evidence`가 자유 문자열

- `target: "SOLARIS, LINUX, AIX, HP-UX 등"` — 콤마 문자열에 "등"이 포함되어 구조화된 플랫폼 목록이 아니다.
- `evidence: "/etc/ssh/sshd_config (PermitRootLogin), /etc/pam.d/login, ..."` — 증적을 콤마로 나열한 단일 문자열이라 엔진이 파싱할 수 없다.

### 5-7. ISMS-P 기준/세부점검항목에는 automation/evidence가 없다

`criteria.yaml`, `check-items.yaml`에는 `automation`, `evidence`, `pass`/`fail` 필드가 **전혀 없다.** 자동화 등급은 KISA 항목에만 존재해, "ISMS-P 기준을 어떻게 증빙/자동화할지"는 모델에 표현되지 않는다. (ISMS-P 기준이 대부분 MANUAL이라는 점을 고려하면 이는 의미 있는 결여다.)

---

## 6. 중복 데이터

| # | 중복 데이터 | 위치 1 | 위치 2 | 위험 |
| --- | --- | --- | --- | --- |
| 1 | ISMS-P↔KISA 매핑 | `kisa/linux/*.yaml` `items[].isms_p` (80건) | `mappings/...yaml` `mappings[].kisa_items[]` (80건) | 한쪽 수정 시 불일치 |
| 2 | 인증기준 문구 | `criteria.yaml` `criteria[].text` | `check-items.yaml` `items[].detail` | 텍스트 불일치 가능 |
| 3 | 인증기준 이름 | `criteria.yaml`, `check-items.yaml`, `mappings/*.yaml` (3곳) | — | 이름 변경 시 3곳 수정 |
| 4 | 출처(source) 블록 | 5개 `kisa/linux/*.yaml` 각각 (document/version/chapter 동일) | — | 페이지(page)만 상이, 나머지 중복 |

---

## 7. Single Source of Truth 검토

**위반 사항 3건.**

1. **매핑**은 `mappings/isms-p-to-linux.yaml`이 진실 공급원(SSOT)이 되어야 한다. 그러나 현재 동일 매핑이 `kisa/*.yaml`의 `isms_p` 필드에도 존재한다. → **매핑은 mappings 파일 한 곳에만 두고, kisa 항목의 `isms_p` 필드는 제거하거나 생성 시 파생(derived)으로 만들어야 한다.**

2. **인증기준 문구**는 `criteria.yaml`이 SSOT여야 한다. `check-items.yaml`의 `detail`은 `criteria.yaml`의 `text`와 동일하므로, 중복을 없애고 참조하거나 두 파일을 병합해야 한다.

3. **기준 이름**은 한 곳(`criteria.yaml`)이 SSOT여야 하고, 다른 곳은 ID로만 참조해야 한다.

---

## 8. ID 체계 검토

### 현황

| 계열 | 형식 | 예시 |
| --- | --- | --- |
| ISMS-P 영역 | `'N'` (문자열) | `'1'`, `'2'` |
| ISMS-P 분야 | `'N.N'` (문자열) | `'1.1'`, `'2.10'` |
| ISMS-P 기준 | `N.N.N` (비인용 문자열) | `1.1.1`, `2.10.8` |
| KISA 항목 | `U-xx` | `U-01`, `U-64` |

### 문제

1. **인용 여부가 일관되지 않다.** `criteria.yaml`에서 기준 ID는 `1.1.1`(비인용)로, 분야 ID는 `'1.1'`/`'2.10'`(인용)으로 저장된다. `2.10` 같은 값이 인용 없이 나오면 YAML 파서가 **float `2.1`**로 오독할 수 있다. 현재는 분야 ID가 인용되어 있어 회피되고 있지만, 이 규칙은 어디에도 문서화되어 있지 않아 **취약하다.**

2. **ID 의미 규칙이 비문서화.** `U-` 접두사가 플랫폼(Unix)을 뜻하는지, `N.N.N`의 각 자리가 무엇인지(영역·분야·항목)가 데이터에 정의되어 있지 않다.

3. **KISA ID의 전역성.** `U-xx`는 Unix 전용이다. Windows(`W-xx`)를 추가하면 접두사가 플랫폼을 구분하므로 충돌은 없지만, **어떤 접두사가 존재하는지의 중앙 레지스트리가 없다.**

4. **매핑에서의 참조 무결성.** `mappings`의 `isms_p_criterion: 2.5.1`, `kisa_items: [U-07]`는 문자열일 뿐, 참조 대상이 실제 존재하는지 검증되지 않는다. 오타가 나도 감지할 수 없다.

---

## 9. Mapping 구조 검토

- **N:M은 표현 가능**하다(리스트 필드 양쪽 존재). 이 점은 양호.
- 그러나 다음 문제가 있다.

1. **방향 중복**: `mappings`(정방향)와 `kisa items[].isms_p`(역방향)이 동시에 존재한다. 하나만 SSOT로 두어야 한다.

2. **매핑 유형 미구분**: 현재 매핑은 "관련성"만 나타낸다. 실제로는 (a) KISA 점검이 ISMS-P 기준의 **일부 근거**가 되는지, (b) **완전히 충족**하는지가 다르다. 매핑에 `relationship`(예: `contributes` / `satisfies`) 속성이 없다. 이 결여가 9절(동일시 위험)의 원인이다.

3. **매핑의 해석 표기가 파일 헤더 주석에만 존재**하고, 개별 매핑 레코드에는 없다. 데이터를 코드로 읽으면 "해석"임을 알 수 없다.

4. **플랫폼 차원 누락**: `isms-p-to-linux.yaml`은 파일명으로 Linux임을 암시할 뿐, 매핑 레코드 자체에 플랫폼 필드가 없다. Windows 매핑을 추가하면 새 파일(`isms-p-to-windows.yaml`)을 만들어야 하며, 통합 질의가 어려워진다.

---

## 10. 자동화 모델 검토

### 현황

- `kisa/linux/*.yaml`의 `items[].automation`에 `AUTO`(56) / `SEMI`(11)만 존재. `MANUAL`은 값으로 존재하지 않음.
- `criteria.yaml`, `check-items.yaml`에는 automation 필드가 없음.

### 문제

1. **분류가 KISA 항목에만 있다.** ISMS-P 기준(대부분 절차·문서 검증 = MANUAL/SEMI)에는 automation 등급이 없다. 엔진이 "전체 작업 중 자동화 가능 범위"를 산정하려면 ISMS-P 쪽에도 등급이 필요하다.

2. **automation의 의미 모호성**: `automation`이 (a) "점검 자체를 자동 실행할 수 있는가"인지, (b) "현재 도구로 구현 가능한가"인지, (c) "완전 자동으로 판정까지 되는가"인지가 정의되어 있지 않다. 예를 들어 SEMI는 "기술 점검은 자동이지만 판정에 사람이 필요한가" vs "증적 수집만 자동인가"가 구분되지 않는다.

3. **정적 속성의 한계**: `automation`이 데이터(사양)에 고정되어 있다. 실제로는 "구현 진척도"에 따라 AUTO/SEMI가 변할 수 있다. 사양 단계의 항목 속성인지, 구현 단계의 상태인지가 혼재되어 있다. → 사양에는 "이론상 자동화 가능성"을, 구현 계층에는 "구현 상태"를 두는 분리가 필요하다.

4. **SEMI 항목의 판단 기준 입력 누락**: SEMI 항목(예: U-07 "불필요한 계정 제거")은 "불필요"의 조직 기준값이 필요하다. 이 기준값을 주입할 필드(예: `policy_input`, `threshold`)가 모델에 없다.

---

## 11. Evidence 모델 검토

### 현황

`evidence`는 단일 자유 문자열이다. 예:

- `evidence: /etc/ssh/sshd_config (PermitRootLogin), /etc/pam.d/login, /etc/securetty`
- `evidence: 패치 적용 현황/정책`

### 문제

1. **구조화 부재**: 증적이 콤마 나열 문자열이라, 엔진이 "어떤 파일을 수집하고 어떤 값을 비교할지"를 알 수 없다.

2. **증적의 의미 모호**: `evidence`가 (a) 점검 대상(수집할 파일/명령)인지, (b) 제출해야 할 증빙인지가 구분되지 않는다. `account.yaml`의 `U-07` evidence "계정 목록"은 점검 대상인 반면, `patch.yaml`의 `U-64` evidence "패치 적용 현황/정책"은 문서 증빙이다. 같은 필드에 두 의미가 섞여 있다.

3. **ISMS-P 쪽 증적 부재**: `criteria.yaml`/`check-items.yaml`에는 증거자료(안내서의 "증거자료 예시")가 전혀 저장되어 있지 않다. ISMS-P 심사 증빙을 자동화하려면 이 정보가 필요하다.

4. **수집 명령/경로 부재**: 실제 점검 명령과 설정 파일 경로는 원본 PDF에 있으나 데이터에는 반영되지 않았다.

---

## 12. 플랫폼 확장성 검토

### 현황

- `platform: linux` 필드가 파일 최상단에 있다(파일 레벨).
- 카테고리 파일이 플랫폼 디렉터리 아래 분리되어 있다(`kisa/linux/account.yaml`).

### Windows/DB/Web/Network 추가 시 문제

1. **카테고리 체계가 플랫폼별로 다르다.** Linux는 5분야(계정/파일·디렉토리/서비스/패치/로그), Windows는 5분야(계정/서비스/패치/로그/보안), DBMS는 4분야(계정/접근/옵션/패치)다. 현재 "파일명 = 카테고리" 방식은 각 플랫폼이 임의의 카테고리 집합을 가질 수 있어 중앙 카탈로그가 없다.

2. **`source.chapter`가 하드코딩**: `chapter: "01. Unix 서버"`가 파일마다 박혀 있다. 플랫폼이 늘면 이 값의 일관성 유지가 번거롭다. (플랫폼 메타데이터로 분리하는 게 낫다.)

3. **매핑 파일의 플랫폼 한정**: `isms-p-to-linux.yaml`이라는 파일명이 플랫폼을 고정한다. 매핑을 플랫폼 통합으로 확장하려면 매핑 레코드에 `platform` 차원을 추가해야 한다.

4. **ID 접두사 관리**: `U-`(Unix), `W-`(Windows) 등 접두사 규칙이 암묵적이다. 새 플랫폼의 접두사를 정하고 충돌을 피하는 규칙이 없다.

> 긍정적 측면: `platform` 필드와 플랫폼별 디렉터리 분리는 **기본 골격은 확장 친화적**이다. 문제는 카테고리/ID/매핑의 중앙 관리 규칙 부재다.

---

## 13. 권장 데이터 모델

> 아래는 권고안이며, 현재 파일을 즉시 수정하라는 지시가 아니다.

### 13-1. 매핑 단일화 (SSOT)

- 매핑은 `mappings/` 한 곳에만 저장한다.
- `kisa/linux/*.yaml`의 `items[].isms_p` 필드는 **제거**하고, 필요 시 빌드 스크립트가 mappings에서 역방향 뷰를 **생성**한다.
- 매핑 레코드에 관계 유형과 출처 근거를 명시:

```yaml
mappings:
  - isms_p: 2.5.5
    kisa: U-01
    relationship: contributes   # satisfies | contributes | evidence_of
    basis: interpretation       # extracted | interpretation
```

### 13-2. ISMS-P 기준/세부점검항목 병합 또는 참조

- 옵션 A(권장): `criteria.yaml`을 SSOT로 두고, `check-items.yaml`은 `criteria_id` 참조 + `checks[]`만 저장(이름·문구 재저장 금지).

```yaml
items:
  - id: 2.5.4
    criteria_id: 2.5.4      # criteria.yaml 참조
    checks: [ ... ]
```

- 옵션 B: 두 파일을 하나로 병합(`criteria[].checks[]`).

### 13-3. ID 체계 정형화

- 모든 ID를 **인용 문자열**로 통일(`"1.1.1"`, `"U-01"`).
- ID 규칙(자릿수 의미, 접두사)을 `data/schema/` 또는 각 파일 헤더에 문서화.
- 선택적으로 `$id`/`ref` 규약을 도입해 참조 무결성을 검증할 수 있게 한다.

### 13-4. 실행 가능한 점검 확장 (사양과 구현 분리)

- 현재 `pass`/`fail` 산문은 **사양(인간 판독용)**으로 유지하고, 그 아래에 **구조화된 체크 스펙**을 병행 추가한다.

```yaml
- id: U-16
  pass: /etc/passwd 파일의 소유자가 root이고, 권한이 644 이하인 경우   # 원문(사양)
  checks:
    - type: file_owner
      path: /etc/passwd
      expect: root
    - type: file_mode
      path: /etc/passwd
      expect: "<= 0644"
```

- 단, `checks` 구조는 별도 구현 계층(`checks/` 또는 엔진 코드)에서 정의하는 것도 가능하다. 데이터 모델은 최소한 **원문 판단 기준과 구조화 조건을 분리해 담을 자리**를 제공해야 한다.

### 13-5. `target`/`evidence` 구조화

```yaml
target:
  - linux
  - solaris
  - aix
  - hpux
evidence:
  - type: file
    path: /etc/ssh/sshd_config
    note: PermitRootLogin 설정 확인
```

- `target`은 플랫폼 열거형 리스트, `evidence`는 `{type, path, note}` 객체 리스트로.

### 13-6. 사실/해석 명시적 구분

- 각 필드의 출처 성격을 표기하는 컨벤션(예: `_interpretation`, `_source_ref`) 또는 별도 `meta` 블록을 도입.
- 최소한 `isms_p` 같은 매핑 필드는 사실 필드와 분리된 위치에 두고 `interpretation: true`를 표기.

### 13-7. automation 의미 확장

- `automation`을 `auto`/`semi`/`manual` 열거형으로 통일하고, ISMS-P 기준/세부점검항목에도 동일 필드를 부여.
- SEMI의 "사람 확인 이유"와 "필요 입력(policy input)"을 별도 필드로 표현.

### 13-8. 플랫폼/카테고리 레지스트리

- `data/schema/platforms.yaml`, `data/schema/categories.yaml` 등으로 플랫폼·카테고리·ID 접두사를 중앙 정의.
- 매핑 레코드에 `platform` 차원 추가(향후 통합 질의 지원).

---

## 14. 수정 우선순위

| 우선순위 | 항목 | 사유 |
| --- | --- | --- |
| P0 | 매핑 중복 제거 (`items[].isms_p` vs `mappings`) | 드리프트로 인한 데이터 불일치가 현재 이미 발생 가능 |
| P0 | 인증기준 문구/이름 중복 제거 (criteria vs check-items vs mappings) | SSOT 위반 |
| P1 | ID 인용/규칙 통일 및 문서화 | `2.10` float 오독 위험, 참조 무결성 |
| P1 | 사실/해석 구분 구조 도입 | KISA 결과 = ISMS-P 충족 오해 방지 |
| P2 | `target`/`evidence` 구조화 | 엔진 확장의 전제 |
| P2 | 실행 가능한 체크 스펙(checks) 자리 마련 | 엔진 구현 가능성 |
| P3 | automation 등급을 ISMS-P에도 부여 | 전체 자동화 범위 산정 |
| P3 | 플랫폼/카테고리 레지스트리 | Windows/DB/Web/Network 확장 |

---

## 15. 다음 개발 단계 제안

1. **스키마 확정**: 위 권고(13절)를 반영한 데이터 스키마(예: JSON Schema)를 문서로 먼저 확정.
2. **SSOT 정리**: 매핑 단일화, 기준 문구/이름 참조화를 수행(데이터 재생성 스크립트 수정).
3. **사실/해석 분리**: 매핑을 "해석"으로 격리하고, 각 데이터의 원본 근거(페이지/행)를 보강.
4. **체크 스펙 설계**: 점검 엔진이 소비할 구조화된 check/evidence 스펙을 정의(파일 소유자/권한, 서비스 상태, 계정/UID/GID, 설정값 비교 등).
5. **자동화 등급 재산정**: ISMS-P 기준에도 AUTO/SEMI/MANUAL을 부여하고 SEMI의 필요 입력을 식별.
6. **플랫폼 레지스트리 도입**: Windows/DB/Web/Network 추가에 대비한 ID 접두사·카테고리·매핑 차원 정의.
