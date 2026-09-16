# KISA Linux/Unix 전체 Check 설계 분석 (Inventory)

> KISA Linux/Unix 기술적 취약점 점검 항목 전체(U-01 ~ U-67)를 Technical Check 단위로 어떻게 분해할지 분석한 문서다.
> 이 문서는 **설계/분석만 수행**하며, 코드·Check YAML·Engine·데이터는 수정하지 않는다.

---

## 1. 분석 축 정의

분해, 자동화, 구현 상태를 **서로 독립된 세 축**으로 분리한다.

### 축 1. 분해 (check_count)

하나의 KISA 항목을 몇 개의 Technical Check로 분해하는가. (1 / 2 / 3)

### 축 2. 자동화 수준 (Technical Check 단위, 관찰/판단 분리)

```
Technical Check → Observation(관찰) → Assessment(판단)
```

- **Observation(관찰)**: "시스템에서 어떤 사실을 확인했는가?" — 기술적 metadata 수집.
- **Assessment(판단)**: "그 사실을 기준에 따라 어떻게 판단하는가?" — 기계 판정 / 사람 판단 / 외부 데이터 비교.

| 관찰 | 판단 | 표기 | 의미 |
| --- | --- | --- | --- |
| AUTO | AUTO | `A/A` | 기술 관찰 + 기술 조건 판정 모두 자동 |
| AUTO | HUMAN | `A/H` | 기술 관찰 자동, 최종 판단 사람 |
| AUTO | EXTERNAL_DATA | `A/E` | 기술 관찰 자동, 외부 DB/벤더 권고와 비교해 판단 |
| MANUAL | HUMAN | `M/H` | 자동 관찰 불가(정책/문서), 사람 확인 |

> **`A/A`의 의미**: "Technical Check에서 정의한 기술적 관찰과 그 기술적 조건의 판정이 모두 자동화 가능함"을 뜻한다.
> KISA 전체 취약점 점검 결과나 ISMS-P 인증 결과를 의미하지 않는다.

> 핵심: "기술적 관찰"과 "판단"을 섞지 않는다.
> - 계정/SUID/world-writable **파일 목록 수집** → 관찰 AUTO
> - 그 계정/파일이 "불필요한지" **판단** → 판단 HUMAN

### 축 3. 구현 상태 (Technical Check 단위, 정확히 하나)

| 상태 | 의미 |
| --- | --- |
| `SUPPORTED` | **현재 Engine의 collector/evaluator 기능으로 해당 Technical Check의 기술적 조건을 정확하게 표현·구현 가능** |
| `NEW_COLLECTOR` | 기존 type이지만 수집 로직 확장 필요(복잡 설정 문법·값 추출, 파일 존재, 계정/그룹 열거) |
| `NEW_CHECK_TYPE` | 신규 Check type 정의 필요(file_scan, account_duplicate/shell, package_version) |
| `MANUAL` | 자동 수집 불가(정책/문서) |

> `SUPPORTED`는 "동일한 Check type이 존재한다"는 뜻이 아니다. 기존 collector로 해당 기술 조건을 **정확히** 구현 가능한 경우만 해당한다.
> `EXTERNAL_DATA`는 구현 상태가 아니라 **Assessment 방식(`A/E`)**으로만 표현한다.

---

## 2. 기존 Check type / Engine 현황

- **구현된 type**: `config_value`, `service_status`, `account_uid`, `file_owner`, `file_mode`
- **Spec 정의·미구현 type**: `file_existence`, `account_gid`, `account_shell`, `account_duplicate`, `process_running`, `package_version`, `command_output`, `document`
- **신규 type 후보**: `file_scan`(파일 열거), `account_group`(그룹 멤버십), account 확장

---

## 3. 계정 관리 (U-01 ~ U-13)

| ID | 항목명 | check | 관찰(수집) | 자동화 | 구현상태 | 난이도 |
| --- | --- | --- | --- | --- | --- | --- |
| U-01 | root 계정 원격 접속 제한 | 3 | SSH PermitRootLogin / Telnet 사용 여부 / Telnet root 제한 (config_value·service_status) | A/A | SUPPORTED | 하 |
| U-02 | 비밀번호 관리정책 설정 | 1 | PAM pwquality·login.defs 정책값 (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-03 | 계정 잠금 임계값 설정 | 1 | pam_tally2/faillock deny값 (config_value) | A/A | NEW_COLLECTOR(값 추출) | 하 |
| U-04 | 비밀번호 파일 보호 | 1 | /etc/passwd pw필드 'x' (account) | A/A | NEW_COLLECTOR(필드 파싱) | 하 |
| U-05 | root 외 UID 0 금지 | 1 | /etc/passwd UID 목록 (account_uid) | A/A | SUPPORTED | 하 |
| U-06 | 사용자 su 기능 제한 | 1 | /etc/pam.d/su pam_wheel (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-07 | 불필요한 계정 제거 | 1 | 계정 목록 열거 (account) | A/H | NEW_COLLECTOR | 중 |
| U-08 | 관리자 그룹 최소 계정 | 1 | wheel/root 그룹 멤버 (account_group) | A/H | NEW_COLLECTOR | 중 |
| U-09 | 불필요한 GID 금지 | 1 | 멤버 없는 그룹 (account_group) | A/H | NEW_COLLECTOR | 중 |
| U-10 | 동일한 UID 금지 | 1 | UID 중복 탐지 (account_duplicate) | A/A | NEW_CHECK_TYPE | 중 |
| U-11 | 사용자 shell 점검 | 1 | 계정별 로그인 쉘 (account_shell) | A/A | NEW_CHECK_TYPE | 중 |
| U-12 | 세션 종료 시간 설정 | 1 | /etc/profile TMOUT (config_value) | A/A | NEW_COLLECTOR(값 추출) | 하 |
| U-13 | 비밀번호 암호화 알고리즘 | 1 | ENCRYPT_METHOD SHA512 (config_value) | A/A | SUPPORTED | 하 |

> U-01은 3개 Check(SSH / Telnet 사용 여부 / Telnet root 제한)로 확정한다. Telnet root 제한은 Telnet 미사용 시 NOT_APPLICABLE이 될 수 있으나 Check 자체는 존재한다.
> U-02는 PAM pwquality('=' 문법)·login.defs 다중 파일의 정확한 값 검증이 필요해 NEW_COLLECTOR다. U-06은 pam.d/su 모듈 옵션 해석이 필요하다.
> U-07/08/09는 관찰(AUTO)=계정/그룹 열거, 판단(HUMAN)="불필요" 여부가 분리된다.

---

## 4. 파일 및 디렉토리 관리 (U-14 ~ U-33)

| ID | 항목명 | check | 관찰(수집) | 자동화 | 구현상태 | 난이도 |
| --- | --- | --- | --- | --- | --- | --- |
| U-14 | root PATH 설정 | 1 | root .profile PATH '.' (config_value) | A/A | NEW_COLLECTOR(PATH 파싱) | 하 |
| U-15 | 파일/디렉토리 소유자 설정 | 1 | 소유자 없는 파일 열거 (file_scan) | A/A | NEW_CHECK_TYPE | 상 |
| U-16 | /etc/passwd 소유자·권한 | 2 | /etc/passwd (file_owner+file_mode) | A/A | SUPPORTED | 하 |
| U-17 | 시스템 시작 스크립트 권한 | 1 | /etc/init.d·/etc/rc* 권한 (file_scan) | A/A | NEW_CHECK_TYPE | 중 |
| U-18 | /etc/shadow 소유자·권한 | 2 | /etc/shadow | A/A | SUPPORTED | 하 |
| U-19 | /etc/hosts 소유자·권한 | 2 | /etc/hosts | A/A | SUPPORTED | 하 |
| U-20 | /etc/(x)inetd.conf 권한 | 2 | inetd.conf·xinetd.conf | A/A | SUPPORTED | 하 |
| U-21 | /etc/(r)syslog.conf 권한 | 2 | rsyslog.conf | A/A | SUPPORTED | 하 |
| U-22 | /etc/services 권한 | 2 | /etc/services | A/A | SUPPORTED | 하 |
| U-23 | SUID/SGID/Sticky bit | 1 | SUID/SGID 파일 열거 (file_scan) | A/H | NEW_CHECK_TYPE | 상 |
| U-24 | 환경변수 파일 소유자·권한 | 1 | 홈 환경변수 파일 (file_scan) | A/A | NEW_CHECK_TYPE | 중 |
| U-25 | world writable 파일 | 1 | world writable 파일 열거 (file_scan) | A/H | NEW_CHECK_TYPE | 중 |
| U-26 | /dev device 파일 | 1 | /dev 존재하지 않는 device (file_scan) | A/H | NEW_CHECK_TYPE | 상 |
| U-27 | .rhosts/hosts.equiv 금지 | 1 | 파일 존재 (file_existence) | A/A | NEW_COLLECTOR | 하 |
| U-28 | 접속 IP·포트 제한 | 1 | hosts.allow/deny (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-29 | hosts.lpd 소유자·권한 | 1 | /etc/hosts.lpd (file_owner+file_mode) | A/A | SUPPORTED | 하 |
| U-30 | UMASK 설정 | 1 | /etc/profile umask (config_value) | A/A | SUPPORTED | 하 |
| U-31 | 홈 디렉토리 소유자·권한 | 1 | 각 홈 디렉토리 (file_scan) | A/A | NEW_CHECK_TYPE | 중 |
| U-32 | 홈 디렉토리 존재 | 1 | 계정별 홈 존재 (account) | A/A | NEW_COLLECTOR | 중 |
| U-33 | 숨김 파일 검색·제거 | 1 | 의심 숨김 파일 열거 (file_scan) | A/H | NEW_CHECK_TYPE | 중 |

> file_scan 계열의 **파일 목록 수집은 관찰 AUTO**다.
> - U-15/17/24/31/67: "존재/권한/소유자" 기계 판정 → A/A.
> - U-23/25/26/33: "불필요/의심/제거" 업무 판단 → A/H.
> U-28(hosts.allow/deny)은 `daemon: client` 문법 해석이 필요해 NEW_COLLECTOR다.

---

## 5. 서비스 관리 (U-34 ~ U-63)

| ID | 항목명 | check | 관찰(수집) | 자동화 | 구현상태 | 난이도 |
| --- | --- | --- | --- | --- | --- | --- |
| U-34 | Finger 비활성화 | 1 | finger 상태 (service_status) | A/A | SUPPORTED | 하 |
| U-35 | 공유 서비스 익명 접근 제한 | 1 | smb.conf 익명 설정 (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-36 | r 계열 서비스 비활성화 | 1 | rlogin/rsh/rexec (service_status) | A/A | SUPPORTED | 하 |
| U-37 | crontab 설정파일 권한 | 1 | cron.allow/deny 권한 (file_owner+file_mode) | A/A | SUPPORTED | 하 |
| U-38 | DoS 취약 서비스 비활성화 | 1 | echo/discard/chargen (service_status) | A/A | SUPPORTED | 하 |
| U-39 | 불필요한 NFS 비활성화 | 1 | nfsd (service_status) | A/A | SUPPORTED | 하 |
| U-40 | NFS 접근 통제 | 1 | /etc/exports (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-41 | automountd 제거 | 1 | automountd (service_status) | A/A | SUPPORTED | 하 |
| U-42 | 불필요한 RPC 비활성화 | 1 | rpcbind/rpc.statd (service_status) | A/A | SUPPORTED | 하 |
| U-43 | NIS/NIS+ 점검 | 1 | ypserv/ypbind (service_status) | A/A | SUPPORTED | 하 |
| U-44 | tftp/talk 비활성화 | 1 | tftp/talk/ntalk (service_status) | A/A | SUPPORTED | 하 |
| U-45 | 메일 서비스 버전 | 1 | 설치 버전 (package_version) | A/E | NEW_CHECK_TYPE | 상 |
| U-46 | 일반 사용자 메일 실행 방지 | 1 | sendmail.cf (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-47 | 스팸 릴레이 제한 | 1 | sendmail.cf (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-48 | expn/vrfy 제한 | 1 | sendmail.cf (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-49 | DNS 보안 버전 | 1 | BIND 버전 (package_version) | A/E | NEW_CHECK_TYPE | 상 |
| U-50 | DNS Zone Transfer 제한 | 1 | named.conf (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-51 | DNS 동적 업데이트 금지 | 1 | named.conf (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-52 | Telnet 비활성화 | 1 | telnet (service_status) | A/A | SUPPORTED | 하 |
| U-53 | FTP 정보 노출 제한 | 1 | FTP 배너 설정 (config_value) | A/A | NEW_COLLECTOR | 하 |
| U-54 | 암호화 안 된 FTP 비활성화 | 1 | ftp (service_status) | A/A | SUPPORTED | 하 |
| U-55 | FTP 계정 shell 제한 | 1 | ftp 계정 쉘 (account_shell) | A/A | NEW_CHECK_TYPE | 중 |
| U-56 | FTP 접근 제어 | 1 | ftpaccess (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-57 | Ftpusers 파일 설정 | 1 | /etc/ftpusers root (config_value) | A/A | SUPPORTED | 하 |
| U-58 | 불필요한 SNMP 비활성화 | 1 | snmpd (service_status) | A/A | SUPPORTED | 하 |
| U-59 | 안전한 SNMP 버전 | 1 | snmpd.conf (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-60 | SNMP Community String 복잡성 | 1 | snmpd.conf (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-61 | SNMP Access Control | 1 | snmpd.conf (config_value) | A/A | NEW_COLLECTOR | 중 |
| U-62 | 로그인 경고 메시지 | 1 | /etc/motd·issue (file) | A/A | SUPPORTED | 하 |
| U-63 | sudo 명령어 접근 관리 | 2 | /etc/sudoers (file_owner+file_mode) | A/A | SUPPORTED | 하 |

> sendmail.cf/named.conf/snmpd.conf/smb.conf/exports/FTP 배너 등은 복잡 설정 문법이라 단순 `contains`로 정확히 구현할 수 없어 NEW_COLLECTOR다.
> U-57(ftpusers)은 사용자 목록 파일에 `root` 포함 여부만 확인하므로 `contains`로 정확 → SUPPORTED.

---

## 6. 패치 관리 (U-64)

| ID | 항목명 | check | 관찰(수집) | 자동화 | 구현상태 | 난이도 |
| --- | --- | --- | --- | --- | --- | --- |
| U-64 | 주기적 보안 패치 적용 | 2 | (1) 정책 문서 (document) / (2) 패치 버전 (package_version) | (1) M/H / (2) A/E | (1) MANUAL / (2) NEW_CHECK_TYPE | 상 |

> U-64는 하나의 KISA Item이지만 성격이 다른 2개 Check로 분리한다. 자동화 수준을 Item 단위로 단정하지 않는다.

---

## 7. 로그 관리 (U-65 ~ U-67)

| ID | 항목명 | check | 관찰(수집) | 자동화 | 구현상태 | 난이도 |
| --- | --- | --- | --- | --- | --- | --- |
| U-65 | NTP 시각 동기화 | 1 | ntpd/chronyd + ntp.conf (service_status+config_value) | A/A | SUPPORTED | 중 |
| U-66 | 정책에 따른 로깅 | 1 | rsyslog 설정 (config_value) | A/H | SUPPORTED | 중 |
| U-67 | 로그 디렉토리 권한 | 1 | 로그 파일 소유자·권한 (file_scan) | A/A | NEW_CHECK_TYPE | 중 |

> U-66은 rsyslog 설정 수집(관찰 AUTO, SUPPORTED)은 자동이지만, "보안 정책에 따른 로깅" 부합 여부(판단 HUMAN)는 사람 몫이다.

---

## 8. config_value 복잡도 구분

| 구분 | 설명 | 구현상태 | 해당 항목 |
| --- | --- | --- | --- |
| 단순 key=value(공백 구분) | sshd_config, login.defs, profile umask | SUPPORTED | U-01, U-13, U-30 |
| 단순 text contains/not_contains | pam_wheel 모듈, ftpusers 목록 | SUPPORTED | U-57 |
| 값 추출 후 비교 | deny=N, TMOUT=N | NEW_COLLECTOR | U-03, U-12 |
| 구조화된 설정 문법 | sendmail.cf(O 옵션), named.conf(블록), snmpd.conf(지시자), smb.conf/exports/hosts.allow, PAM(pwquality/su), FTP 배너 | NEW_COLLECTOR | U-02, U-06, U-28, U-35, U-40, U-46~48, U-50, U-51, U-53, U-56, U-59~61 |

> `config_value` 하나로 모든 설정 파일 형식을 처리할 수 있다고 가정하지 않는다.

---

## 9. file_scan 항목의 관찰/판단 분리

파일 탐색·metadata 수집(path/uid/gid/owner/mode/type/size)은 **기술적 관찰(AUTO)**이다.

| 판단 | 자동화 | 설명 | 해당 항목 |
| --- | --- | --- | --- |
| 소유자 존재? 권한 범위? | AUTO | 기계 판정 | U-15, U-17, U-24, U-31, U-67 |
| 불필요/의심/제거 필요? | HUMAN | 업무 판단 | U-23, U-25, U-26, U-33 |

> 파일 목록을 수집하는 것 자체를 SEMI로 표현하지 않는다.

---

## 10. 전체 집계

### 10.1 분해 (check_count)

| 구분 | 항목 수 |
| --- | --- |
| 1개 Check | 58 |
| 2개 Check | 8 (U-16, U-18, U-19, U-20, U-21, U-22, U-63, U-64) |
| 3개 Check | 1 (U-01) |
| **전체 KISA 항목** | **67** |
| **전체 Technical Check 수** | **77** (58×1 + 8×2 + 1×3) |

### 10.2 Assessment (관찰/판단, Technical Check 기준)

| 관찰 | 판단 | Check 수 |
| --- | --- | --- |
| AUTO | AUTO | 65 |
| AUTO | HUMAN | 8 |
| AUTO | EXTERNAL_DATA | 3 |
| MANUAL | HUMAN | 1 |
| **합계** | | **77** |

### 10.3 구현 상태 (Technical Check 기준, 각각 1개)

| 상태 | Check 수 |
| --- | --- |
| SUPPORTED | 37 |
| NEW_COLLECTOR | 24 |
| NEW_CHECK_TYPE | 15 (file_scan 9 + account 3 + package_version 3) |
| MANUAL | 1 (U-64 문서) |
| **합계** | **77** |

### 10.4 난이도 분포 (항목 기준)

| 난이도 | 항목 수 |
| --- | --- |
| 하 | 32 |
| 중 | 29 |
| 상 | 6 (U-15, U-23, U-26, U-45, U-49, U-64) |

---

## 11. 집계 검증 (논리 일치성)

- **분해 합계**: 58 + 8 + 1 = 67 항목 ✓ / 58×1 + 8×2 + 1×3 = 77 Check ✓
- **Assessment 합계**: 65 + 8 + 3 + 1 = 77 ✓
- **구현상태 합계**: 37 + 24 + 15 + 1 = 77 ✓
- **교차 일치** (구현상태 → Assessment 매핑):

| 구현상태 | Check 수 | Assessment 내역 |
| --- | --- | --- |
| SUPPORTED | 37 | A/A 36 + A/H 1 (U-66) |
| NEW_COLLECTOR | 24 | A/A 21 + A/H 3 (U-07/08/09) |
| NEW_CHECK_TYPE | 15 | A/A 8(file_scan 5 + account 3) + A/H 4(file_scan) + A/E 3(package_version) |
| MANUAL | 1 | M/H 1 (U-64 문서) |

→ A/A = 36 + 21 + 8 = 65, A/H = 1 + 3 + 4 = 8, A/E = 3, M/H = 1. 합계 77 ✓

> 주: U-66은 관찰(rsyslog 설정)은 SUPPORTED, 판단은 HUMAN으로, 구현상태와 판단이 서로 다른 축이다.

---

## 12. 결론

### 구조

```
KISA Item
   ↓
Technical Check  (KISA 기준을 기술적으로 검증하기 위한 단위)
   ↓
Observation      (자동 수집: 파일/설정/서비스/계정 metadata)
   ↓
Assessment       (기계 판정 AUTO / 사람 판단 HUMAN / 외부 데이터 EXTERNAL)
   ↓
Evidence         (관찰 근거: target/attribute/observed/expected)
```

### 원칙

> Technical Check는 KISA 기준을 기술적으로 검증하기 위한 단위다.
> Technical Check의 PASS/FAIL은 KISA 취약점 점검 결과와 동일하지 않다.
> KISA 기술 점검 결과 역시 ISMS-P 인증 PASS/FAIL과 동일하지 않다.

### 다음 단계 제안

1. **즉시 구현 가능(SUPPORTED 37 Check)**: 단일 파일 권한, 서비스 상태, 단순 설정값 계열은 현재 Engine으로 바로 확장 가능하다.
2. **NEW_COLLECTOR(24 Check)**: config 복잡 문법 해석(sendmail.cf/named.conf/snmpd.conf 등), 값 추출, file_existence, 계정/그룹 열거.
3. **NEW_CHECK_TYPE(15 Check)**: `file_scan`(파일 열거) → 파일 계열 확장의 전제. account 확장(중복·shell·그룹), `package_version`.
4. **EXTERNAL_DATA 판단(3 Check)**: value_ref(취약점 DB/벤더 권고) 설계가 패치/버전 계열(U-45/49/64)의 선행 과제다. (구현 상태는 NEW_CHECK_TYPE)
5. **SEMI(관찰 AUTO + 판단 HUMAN)**: U-07/08/09/23/25/26/33/66은 자동 수집 + 사람 판단으로 두고, 조직 기준값(화이트리스트/정책) 주입 인터페이스를 고려한다.

> 추천 순서: (1) `file_scan` 수집기 → 파일 권한 계열 확장, (2) config 복잡 문법 수집기, (3) account 수집기 확장, (4) value_ref 설계.
> 이 Inventory는 여기서 확장을 멈추고, 다음 단계에서 `docs/design/check-specification.md`와의 정합성 검토 후 `file_scan` 설계로 넘어간다.
