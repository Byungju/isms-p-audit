# Check Implementation Coverage Report

> KISA Linux 전체 Technical Check 구현(Phase 0~4) 완료 후 Coverage 보고서.

---

## 1. 총 KISA Item 수

**67개** (`data/kisa/linux/*.yaml`)

## 2. 총 Technical Check 수

**77개** (`data/checks/linux/*.yaml`)

## 3. 생성된 Check 수

**77개** — 5개 파일:
- `account.yaml` 15, `file.yaml` 26, `service.yaml` 31, `patch.yaml` 2, `logging.yaml` 3

## 4. Mapping 수

**67개 KISA Item ↔ 77개 Check 참조** (`data/mappings/kisa-to-check.yaml`)

## 5. 구현된 Collector 종류

| target kind | Check type | 상태 |
| --- | --- | --- |
| `config` | config_value | 기존 |
| `service` | service_status | 기존 |
| `file`(field=owner/mode) | file_owner / file_mode | 기존 |
| `file`(field 없음) | file_existence | 신규 |
| `account` | account_uid / account_shell / account_duplicate | 확장(name/home/중복) |
| `group` | account_group | 신규 |
| `scan` | file_scan | 신규 |
| `package` | package_version | 신규(마커 기반) |
| `document` | document | 신규(마커 기반) |

## 6. 구현된 Check Type

77개 Check가 사용하는 type 12종:
`config_value`(25), `service_status`(13), `file_owner`(8), `file_mode`(8), `file_scan`(9),
`account_shell`(3), `package_version`(3), `account_group`(2), `account_uid`(2),
`file_existence`(2), `account_duplicate`(1), `document`(1)

> Spec에 정의됐지만 77개 Check에서 미사용(collector 미구현)인 type: `account_gid`, `process_running`, `command_output`.

## 7. 자동 평가 가능한 Check (A/A)

**65개** — 관찰 AUTO + 판단 AUTO. 실제 collect → evaluate → PASS/FAIL/ERROR.

## 8. Human assessment Check (A/H)

**8개** — 관찰 AUTO + 판단 HUMAN. collect 후 `MANUAL_REQUIRED` 반환.
U-07, U-08, U-09, U-23, U-25, U-26, U-33, U-66

## 9. External data Check (A/E)

**3개** — 관찰 AUTO + 판단 EXTERNAL_DATA. `value_ref` 미구현으로 `NOT_SUPPORTED`.
U-45, U-49, U-64-002

## 10. 아직 실제 Linux에서 실행되지 않은 Check

- **package_version 3개**: `value_ref`(외부 취약점 DB/벤더 권고) 미구현 → NOT_SUPPORTED.
- **document 1개**: 관찰 MANUAL → MANUAL_REQUIRED (자동 수집 대상 아님).

## 11. NOT_SUPPORTED Check

**3개**: CK-lnx-U45-001, CK-lnx-U49-001, CK-lnx-U64-002 (모두 package_version + value_ref).

## 12. 남은 구현 GAP

1. **value_ref 해석**: 취약점 DB/벤더 권고 연동(U-45/49/64-002).
2. **file_scan의 owner/mode 결합 criteria**: U-17/24/31/67은 현재 `world_writable`으로 근사. 정확한 owner+mode 필터 확장 필요.
3. **복잡 config 문법 정밀 해석**: sendmail.cf/named.conf/snmpd.conf 등은 `contains` 근사. 정밀 파서(NEW_COLLECTOR) 필요.
4. **account_gid/process_running/command_output** type collector 미구현(77개 Check에서 미사용).

## 13. 테스트 결과

`python3 -m unittest discover` → **46 tests, OK**
- 기존 38개(vertical slice) + 신규 8개(empty/exists/file_scan/account_duplicate/file_existence/coverage invariant)

---

## 최종 검증

| 항목 | 값 | 일치 |
| --- | --- | --- |
| KISA Items | 67 | ✓ |
| Technical Checks | 77 | ✓ |
| Check IDs (unique) | 77 | ✓ |
| Mapping references | 77 | ✓ |

`python3 tools/validate_checks.py` → **모든 검증 통과 ✓**

---

## 결론

- **추적성 완성**: KISA 원문(67) → Inventory(77) → Check Specification(설계 계약) → Check YAML(77) → Collector → Evidence → Result의 전체 사슬이 연결되었다.
- **65개 Check는 자동 평가 가능**하고, 8개는 사람 판단(A/H), 3개는 외부 데이터(A/E), 1개는 수동(M/H)으로 분리되어 있다.
- **즉시 구현 가능한 남은 항목**: `value_ref` 해석(3개 Check), file_scan owner/mode criteria(4개 Check), 복잡 config 파서(약 8개 Check).

> Technical Check의 PASS/FAIL은 KISA 취약점 점검 결과와 동일하지 않으며, ISMS-P 인증 PASS/FAIL과도 동일하지 않다.
