"""Check YAML + Mapping 스키마 검증기.

- 77개 Check YAML의 구조/ID/type/target/expect/automation을 검증한다.
- Mapping이 67개 KISA Item ↔ 77개 Check를 올바르게 연결하는지 검증한다.

사용:
    python3 tools/validate_checks.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = ROOT / "data" / "checks" / "linux"
MAPPING_PATH = ROOT / "data" / "mappings" / "kisa-to-check.yaml"
KISA_DIR = ROOT / "data" / "kisa" / "linux"

ALLOWED_TYPES = {
    "file_mode", "file_owner", "file_existence", "config_value",
    "account_uid", "account_gid", "account_shell", "account_duplicate",
    "account_group", "account_home", "account_home_owner",
    "service_status", "process_running", "package_version",
    "command_output", "document", "file_scan",
}
ALLOWED_KINDS = {
    "file", "config", "account", "group", "scan", "service", "process",
    "package", "command", "document",
}
BINARY_OPS = {"eq", "ne", "le", "lt", "ge", "gt", "contains", "not_contains", "in", "not_in", "matches"}
UNARY_OPS = {"exists", "empty"}
ALLOWED_OPS = BINARY_OPS | UNARY_OPS
COMPOSITE_KEYS = {"all", "any", "not"}
SCAN_CRITERIA_ENUM = {"suid", "sgid", "sticky", "world_writable", "ownerless", "hidden", "device"}
CRITERIA_KEYS = {"owner_ne", "owner_eq", "mode_not_allowed", "nouser", "nogroup", "suid", "sgid"}
MODE_WHO = {"owner", "group", "other"}
SCAN_TYPES = {"file", "directory", "device"}
AUTO_VALUES = {
    "observation": {"auto", "manual"},
    "assessment": {"auto", "human", "external_data"},
}
ID_RE = re.compile(r"^CK-(lnx|win|db|web|net)-U\d{2}-\d{3}$")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def load_checks() -> list[dict]:
    checks: list[dict] = []
    for path in sorted(CHECKS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for c in data.get("checks", []):
            c["_file"] = path.name
            checks.append(c)
    return checks


def load_kisa_ids() -> set[str]:
    ids: set[str] = set()
    for path in sorted(KISA_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for it in data.get("items", []):
            ids.add(it["id"])
    return ids


def validate_expect(expect, ctx: str) -> None:
    if not isinstance(expect, dict):
        err(f"{ctx}: expect가 dict가 아님")
        return
    if "mode_allowed" in expect:
        return  # file_mode 전용, 별도 구조
    for key in COMPOSITE_KEYS:
        if key in expect:
            items = expect[key]
            if key in ("all", "any"):
                if not isinstance(items, list):
                    err(f"{ctx}: {key}의 값이 리스트가 아님")
                    return
                for i, cond in enumerate(items):
                    validate_expect(cond, f"{ctx}.{key}[{i}]")
            else:  # not
                validate_expect(items, f"{ctx}.not")
            return
    op = expect.get("op")
    if op is None:
        err(f"{ctx}: op가 없음: {expect!r}")
        return
    if op not in ALLOWED_OPS:
        err(f"{ctx}: 허용되지 않는 op: {op!r}")
        return
    if op in UNARY_OPS:
        if "value" in expect or "value_ref" in expect:
            err(f"{ctx}: unary op {op!r}는 value를 가질 수 없음")
        return
    # binary op
    if "value" not in expect and "value_ref" not in expect:
        err(f"{ctx}: op {op!r}는 value 또는 value_ref가 필요함")
    if "value" in expect and "value_ref" in expect:
        err(f"{ctx}: value와 value_ref를 동시에 가질 수 없음")


def validate_mode_allowed(ma, ctx: str) -> None:
    if not isinstance(ma, dict):
        err(f"{ctx}: mode_allowed는 dict여야 함")
        return
    for who, perms in ma.items():
        if who not in MODE_WHO:
            err(f"{ctx}: 알 수 없는 mode 주체: {who!r}")
        if not isinstance(perms, str):
            err(f"{ctx}: mode 권한은 문자열이어야 함: {perms!r}")
        elif any(ch not in "rwx" for ch in perms):
            err(f"{ctx}: 잘못된 mode 권한 문자: {perms!r}")


def validate_flat_predicate(d, ctx: str) -> None:
    """flat predicate dict의 키·타입을 검증한다(내부 키는 OR 결합)."""
    if not isinstance(d, dict):
        err(f"{ctx}: predicate는 dict여야 함")
        return
    if not d:
        err(f"{ctx}: predicate가 비어 있음")
        return
    for key, val in d.items():
        if key in ("owner_ne", "owner_eq"):
            if not isinstance(val, str):
                err(f"{ctx}: {key}는 문자열이어야 함: {val!r}")
        elif key == "mode_not_allowed":
            validate_mode_allowed(val, f"{ctx}.mode_not_allowed")
        elif key in ("nouser", "nogroup", "suid", "sgid"):
            if not isinstance(val, bool):
                err(f"{ctx}: {key}는 bool이어야 함: {val!r}")
        else:
            err(f"{ctx}: 정의되지 않은 criteria key: {key!r}")


def _validate_all(criteria, ctx: str) -> None:
    if set(criteria.keys()) != {"all"}:
        err(f"{ctx}: all은 다른 criteria 키와 함께 쓸 수 없음")
    items = criteria["all"]
    if not isinstance(items, list) or not items:
        err(f"{ctx}: all 값은 비어있지 않은 리스트여야 함")
        return
    for i, item in enumerate(items):
        ictx = f"{ctx}.all[{i}]"
        if not isinstance(item, dict):
            err(f"{ictx}: all 항목은 dict여야 함")
            continue
        if "any" in item:
            if set(item.keys()) != {"any"}:
                err(f"{ictx}: any는 다른 criteria 키와 함께 쓸 수 없음")
            _validate_any(item["any"], f"{ictx}.any")
        else:
            if "all" in item:
                err(f"{ictx}: 3단 이상 중첩은 지원하지 않음")
            else:
                validate_flat_predicate(item, ictx)


def _validate_any(items, ctx: str) -> None:
    if not isinstance(items, list) or not items:
        err(f"{ctx}: any 값은 비어있지 않은 리스트여야 함")
        return
    for i, item in enumerate(items):
        ictx = f"{ctx}[{i}]"
        if not isinstance(item, dict):
            err(f"{ictx}: any 항목은 dict여야 함")
            continue
        if "all" in item or "any" in item:
            err(f"{ictx}: 3단 이상 중첩은 지원하지 않음")
            continue
        validate_flat_predicate(item, ictx)


def validate_scan_criteria(criteria, ctx: str) -> None:
    if isinstance(criteria, str):
        if criteria not in SCAN_CRITERIA_ENUM:
            err(f"{ctx}: 알 수 없는 scan criteria: {criteria!r}")
        return
    if isinstance(criteria, dict):
        if "all" in criteria:
            _validate_all(criteria, ctx)
            return
        if "any" in criteria:
            err(f"{ctx}: any는 all 내부에서만 허용됨")
            return
        validate_flat_predicate(criteria, ctx)
        return
    err(f"{ctx}: criteria는 문자열 또는 객체여야 함: {criteria!r}")


def validate_targets(targets, ctx: str) -> None:
    if not isinstance(targets, list) or not targets:
        err(f"{ctx}: targets가 비어있거나 리스트가 아님")
        return
    ids: set = set()
    for t in targets:
        kind = t.get("kind")
        if kind not in ALLOWED_KINDS:
            err(f"{ctx}: 허용되지 않는 target kind: {kind!r}")
        if "id" in t:
            if t["id"] in ids:
                err(f"{ctx}: target id 중복: {t['id']!r}")
            ids.add(t["id"])
        # 필수 필드 최소 확인
        if kind in ("file", "config", "scan") and not t.get("path") and not t.get("root"):
            err(f"{ctx}: kind {kind!r}에 path/root가 없음")
        if kind == "account" and not t.get("source"):
            err(f"{ctx}: account target에 source가 없음")
        if kind == "group" and not t.get("source"):
            err(f"{ctx}: group target에 source가 없음")
        if kind in ("service", "process", "package") and not t.get("name"):
            err(f"{ctx}: {kind} target에 name이 없음")
        if kind == "document" and not t.get("name"):
            err(f"{ctx}: document target에 name이 없음")
        if kind == "scan":
            criteria = t.get("criteria")
            if criteria is None:
                err(f"{ctx}: scan target에 criteria가 없음")
            else:
                validate_scan_criteria(criteria, f"{ctx}.criteria")
            types = t.get("types")
            if types is not None:
                if not isinstance(types, list) or not types:
                    err(f"{ctx}: scan types는 비어있지 않은 리스트여야 함")
                else:
                    for ty in types:
                        if ty not in SCAN_TYPES:
                            err(f"{ctx}: 알 수 없는 scan type: {ty!r}")
            if "xdev" in t and not isinstance(t.get("xdev"), bool):
                err(f"{ctx}: scan xdev는 bool이어야 함: {t.get('xdev')!r}")


def validate_automation(auto, ctx: str) -> None:
    if not isinstance(auto, dict):
        err(f"{ctx}: automation이 dict가 아님 (2축 구조여야 함)")
        return
    if "observation" not in auto or "assessment" not in auto:
        err(f"{ctx}: automation에 observation/assessment가 없음")
        return
    if auto["observation"] not in AUTO_VALUES["observation"]:
        err(f"{ctx}: 잘못된 observation: {auto['observation']!r}")
    if auto["assessment"] not in AUTO_VALUES["assessment"]:
        err(f"{ctx}: 잘못된 assessment: {auto['assessment']!r}")


def main() -> int:
    checks = load_checks()
    kisa_ids = load_kisa_ids()

    # ---- Check 검증 ----
    seen_ids: set[str] = set()
    for c in checks:
        cid = c.get("id", "")
        ctx = f"{c.get('_file')}:{cid}"
        if not ID_RE.match(cid or ""):
            err(f"{ctx}: ID 형식이 올바르지 않음: {cid!r}")
        if cid in seen_ids:
            err(f"{ctx}: ID 중복: {cid}")
        seen_ids.add(cid)

        if c.get("type") not in ALLOWED_TYPES:
            err(f"{ctx}: 허용되지 않는 type: {c.get('type')!r}")

        validate_targets(c.get("targets"), ctx)
        validate_expect(c.get("expect"), ctx)
        validate_automation(c.get("automation"), ctx)

        if "precondition" in c:
            pre = c["precondition"]
            validate_targets(pre.get("targets"), f"{ctx}.precondition")
            validate_expect(pre.get("expect"), f"{ctx}.precondition")

    # ---- Mapping 검증 ----
    mapping = yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8")) or {}
    mrefs: set[str] = set()
    for m in mapping.get("mappings", []):
        kisa = m.get("kisa_ref")
        if kisa not in kisa_ids:
            err(f"mapping: 존재하지 않는 kisa_ref: {kisa!r}")
        for cid in m.get("check_refs", []):
            if cid not in seen_ids:
                err(f"mapping: 존재하지 않는 check_ref: {cid!r}")
            if cid in mrefs:
                err(f"mapping: check_ref가 여러 KISA에 연결됨: {cid!r}")
            mrefs.add(cid)

    mapped_kisa = {m["kisa_ref"] for m in mapping.get("mappings", [])}

    # ---- 집계 ----
    print("=" * 60)
    print(f"KISA Item (data/kisa): {len(kisa_ids)}")
    print(f"Technical Check (data/checks): {len(checks)}")
    print(f"Unique Check ID: {len(seen_ids)}")
    print(f"Mapping KISA 항목: {len(mapping.get('mappings', []))}")
    print(f"Mapping check 참조: {len(mrefs)}")
    print("=" * 60)

    # KISA ↔ Check 1:1 여부 확인
    missing_kisa = kisa_ids - mapped_kisa
    unmapped_checks = seen_ids - mrefs
    if missing_kisa:
        err(f"mapping 누락 KISA: {sorted(missing_kisa)}")
    if unmapped_checks:
        err(f"mapping 누락 Check: {sorted(unmapped_checks)}")

    if errors:
        print(f"ERROR {len(errors)}건:")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("모든 검증 통과 ✓")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
