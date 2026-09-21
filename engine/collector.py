"""Check 대상(target)에서 값을 수집하는 구현 계층.

- config: 설정 파일의 key 값 추출
- service: 서비스 사용 여부(활성/비활성) 판별
- file: 파일 소유자/권한 수집
- account: 계정 정보(/etc/passwd) 수집
"""

from __future__ import annotations

import os
import pwd
import re
import stat
from dataclasses import dataclass
from pathlib import Path

from .evaluator import mode_allowed_mask


@dataclass
class CollectionOutcome:
    """수집 결과. value가 있으면 정상, 아니면 상태 플래그/오류로 판별한다."""

    value: str | None = None
    missing_target: bool = False  # 파일이 존재하지 않음
    missing_key: bool = False     # key가 설정에 없음
    error: str | None = None      # 읽기/파싱 오류 메시지
    observations: list[dict] | None = None  # Evidence용 관찰 사실 [{target, attribute, observed}]


def extract_config_value(content: str, key: str) -> str | None:
    """설정 파일 텍스트에서 key의 유효 값을 추출한다.

    - 빈 줄·주석(`#`로 시작)은 무시.
    - 첫 토큰이 key와 일치하면 값을 기록하고, 마지막 등장이 유효값(last-wins).
    - key를 찾지 못하면 None.
    """
    value: str | None = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] == key:
            value = tokens[1] if len(tokens) > 1 else None
    return value


def collect(target: dict, root: str | None = None, ctype: str | None = None) -> CollectionOutcome:
    """target의 kind에 따라 값을 수집한다.

    root가 주어지면 절대 경로를 root 아래로 재배치한다(테스트/샌드박스용).
    ctype은 account 계열(account_uid/account_duplicate 등)의 동작을 구분한다.
    """
    kind = target.get("kind")
    if kind == "config":
        return _collect_config(target, root)
    if kind == "service":
        return _collect_service(target, root)
    if kind == "file":
        return _collect_file(target, root)
    if kind == "account":
        return _collect_account(target, root, ctype)
    if kind == "group":
        return _collect_group(target, root)
    if kind == "scan":
        return _collect_scan(target, root)
    if kind == "package":
        return _collect_package(target, root)
    if kind == "document":
        return _collect_document(target, root)
    return CollectionOutcome(error=f"지원하지 않는 target kind: {kind!r}")


def _resolve(base: str | None, rel: str) -> Path:
    if base is not None:
        return Path(base) / rel.lstrip("/")
    return Path("/") / rel.lstrip("/")


def _collect_config(target: dict, root: str | None) -> CollectionOutcome:
    path = target.get("path")
    key = target.get("key")
    if not path:
        return CollectionOutcome(error="config target에 path가 없음")

    p = _resolve(root, path)
    if not p.exists():
        return CollectionOutcome(missing_target=True)

    try:
        content = p.read_text(encoding="utf-8")
    except OSError as exc:
        return CollectionOutcome(error=f"파일 읽기 실패: {exc}")

    # key가 없으면 파일 전체 내용을 관측값으로 반환(contains/not_contains용)
    if not key:
        return CollectionOutcome(
            value=content,
            observations=[{"target": path, "attribute": "content", "observed": content}],
        )

    value = extract_config_value(content, key)
    if value is None:
        return CollectionOutcome(missing_key=True)

    return CollectionOutcome(
        value=value,
        observations=[{"target": path, "attribute": key, "observed": value}],
    )


def _collect_file(target: dict, root: str | None) -> CollectionOutcome:
    """파일의 존재 여부(existence) 또는 소유자(owner)/권한(mode)을 수집한다."""
    path = target.get("path")
    field = target.get("field")
    if not path:
        return CollectionOutcome(error="file target에 path가 없음")

    p = _resolve(root, path)

    # field가 없으면 파일 존재 여부(file_existence)를 수집한다.
    if field is None:
        exists = p.exists()
        return CollectionOutcome(
            value=exists,
            observations=[{"target": path, "attribute": "existence",
                           "observed": "exists" if exists else "not_exists"}],
        )

    if not p.exists():
        return CollectionOutcome(missing_target=True)

    try:
        st = p.stat()
    except OSError as exc:
        return CollectionOutcome(error=f"파일 stat 실패: {exc}")

    if field == "owner":
        try:
            owner = pwd.getpwuid(st.st_uid).pw_name
        except KeyError:
            owner = str(st.st_uid)
        return CollectionOutcome(
            value=owner,
            observations=[{"target": path, "attribute": "owner", "observed": owner}],
        )

    if field == "mode":
        mode_str = f"{stat.S_IMODE(st.st_mode):04o}"
        return CollectionOutcome(
            value=mode_str,
            observations=[{"target": path, "attribute": "mode", "observed": mode_str}],
        )

    return CollectionOutcome(error=f"지원하지 않는 file field: {field!r}")


def _collect_account(target: dict, root: str | None, ctype: str | None) -> CollectionOutcome:
    """계정 정보(/etc/passwd)에서 필드(name/uid/gid/home/shell)를 수집한다.

    - ctype=account_duplicate: 중복 필드값을 가진 계정명 목록을 반환한다.
    - field=shell + names + restricted: names에 속한 계정 중 restricted에 없는 shell을
      가진 계정(위반) 목록을 반환한다.
    - field=home: 홈 디렉토리가 존재하지 않는 계정(위반) 목록을 반환한다.
    """
    from collections import Counter

    source = target.get("source")
    field = target.get("field") or "uid"
    exclude = target.get("exclude") or []
    names = target.get("names")
    restricted = target.get("restricted")
    if not source:
        return CollectionOutcome(error="account target에 source가 없음")

    idx = {"name": 0, "uid": 2, "gid": 3, "home": 5, "shell": 6}.get(field)
    if idx is None:
        return CollectionOutcome(error=f"지원하지 않는 account field: {field!r}")

    p = _resolve(root, source)
    if not p.exists():
        return CollectionOutcome(missing_target=True)

    try:
        content = p.read_text(encoding="utf-8")
    except OSError as exc:
        return CollectionOutcome(error=f"파일 읽기 실패: {exc}")

    pairs: list[tuple[str, str]] = []
    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(":")
        if len(parts) <= idx:
            continue
        if parts[0] in exclude:
            continue
        pairs.append((parts[0], parts[idx]))

    if ctype == "account_duplicate":
        # 중복 필드값을 가진 계정명 목록 (중복 = 같은 값이 2회 이상)
        counts = Counter(v for _, v in pairs)
        dup_names = [n for n, v in pairs if counts[v] > 1]
        observed_str = ",".join(dup_names) if dup_names else "none"
        return CollectionOutcome(
            value=dup_names,
            observations=[{"target": source, "attribute": f"{field}_duplicate", "observed": observed_str}],
        )

    # field=home: 홈 디렉토리가 존재하지 않는 계정(위반) 목록
    if field == "home":
        violating = [n for n, h in pairs if not _home_exists(h, root)]
        observed_str = ",".join(violating) if violating else "none"
        return CollectionOutcome(
            value=violating,
            observations=[{"target": source, "attribute": "home", "observed": observed_str}],
        )

    # field=shell + names + restricted: 제한 쉘 없는 대상 계정(위반) 목록
    if field == "shell" and names is not None and restricted is not None:
        names_set = set(names)
        restricted_set = set(restricted)
        violating = [n for n, v in pairs if n in names_set and v not in restricted_set]
        observed_str = ",".join(violating) if violating else "none"
        return CollectionOutcome(
            value=violating,
            observations=[{"target": source, "attribute": "shell", "observed": observed_str}],
        )

    values = [v for _, v in pairs]
    if field == "uid":
        matched = [n for n, v in pairs if v == "0"]
        observed_str = ",".join(matched) if matched else "none"
    else:
        observed_str = ",".join(values) if values else "none"

    return CollectionOutcome(
        value=values,
        observations=[{"target": source, "attribute": field, "observed": observed_str}],
    )


def _home_exists(home: str, root: str | None) -> bool:
    """계정의 홈 디렉토리가 실제 filesystem에 존재하는지 판단한다."""
    if not home:
        return False
    return _resolve(root, home).exists()


def _collect_group(target: dict, root: str | None) -> CollectionOutcome:
    """그룹 정보(/etc/group)를 수집한다. (account_group)"""
    source = target.get("source")
    name = target.get("name")
    if not source:
        return CollectionOutcome(error="group target에 source가 없음")

    p = _resolve(root, source)
    if not p.exists():
        return CollectionOutcome(missing_target=True)

    try:
        content = p.read_text(encoding="utf-8")
    except OSError as exc:
        return CollectionOutcome(error=f"파일 읽기 실패: {exc}")

    groups: list[dict] = []
    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(":")
        if len(parts) < 4:
            continue
        gname, gid, members = parts[0], parts[2], parts[3].split(",") if parts[3] else []
        if name and gname != name:
            continue
        groups.append({"name": gname, "gid": gid, "members": members})

    if name:
        members = groups[0]["members"] if groups else []
        observed_str = ",".join(members) if members else "none"
        value = members
    else:
        observed_str = ",".join(g["name"] for g in groups) if groups else "none"
        value = [g["name"] for g in groups]

    return CollectionOutcome(
        value=value,
        observations=[{"target": source, "attribute": name or "groups", "observed": observed_str}],
    )


PSEUDO_FS_DIRS = {"proc", "sys", "run", "dev"}


def _collect_scan(target: dict, root: str | None) -> CollectionOutcome:
    """디렉토리 하위 entry를 criteria에 맞게 열거한다. (file_scan)

    - types(기본 [file, device])에 따라 file/directory/device를 매칭 대상으로 한다.
    - pseudo filesystem(/proc, /sys, /run, /dev)은 recursive scan에서 제외한다.
    - scan root 자신은 평가 대상이 아니며, 직접 자식부터 평가한다.
    - 수집 결과(일치 entry 목록)는 목록 형태로 관찰값을 반환한다.
    """
    scan_root = target.get("root")
    criteria = target.get("criteria")
    recursive = bool(target.get("recursive", False))
    types = target.get("types") or ["file", "device"]
    if not scan_root or not criteria:
        return CollectionOutcome(error="scan target에 root/criteria가 없음")

    base = _resolve(root, scan_root)
    if not base.exists():
        return CollectionOutcome(error=f"스캔 경로가 없음: {scan_root}")

    matched: list[str] = []

    def walk(dir_path: Path) -> None:
        try:
            entries = sorted(dir_path.iterdir())
        except OSError:
            return
        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    if _is_pseudo_fs(entry, base):
                        continue
                    if recursive:
                        walk(entry)
                if _entry_type_matches(entry, types) and _matches_criteria(entry, criteria):
                    matched.append(str(entry))
            except OSError:
                continue

    walk(base)

    return CollectionOutcome(
        value=matched,
        observations=[{"target": scan_root, "attribute": criteria, "observed": matched}],
    )


def _entry_type_matches(entry: Path, types: list[str]) -> bool:
    """entry의 파일 타입이 types(매칭 대상)에 포함되는지 판단한다.

    - file: regular file (S_ISREG)
    - directory: 디렉터리 (S_ISDIR)
    - device: character/block device (S_ISCHR|S_ISBLK)
    symlink는 호출 전에 걸러진다.
    """
    try:
        st = entry.stat()
    except OSError:
        return False
    mode = st.st_mode
    if "directory" in types and stat.S_ISDIR(mode):
        return True
    if "file" in types and stat.S_ISREG(mode):
        return True
    if "device" in types and (stat.S_ISCHR(mode) or stat.S_ISBLK(mode)):
        return True
    return False


def _is_pseudo_fs(entry: Path, base: Path) -> bool:
    """scan root 바로 아래의 pseudo filesystem 디렉토리인지 판단한다."""
    try:
        rel = entry.relative_to(base)
    except ValueError:
        return False
    return len(rel.parts) == 1 and rel.parts[0] in PSEUDO_FS_DIRS


def _matches_criteria(p: Path, criteria) -> bool:
    if isinstance(criteria, dict):
        return _matches_criteria_predicate(p, criteria)
    try:
        st = p.stat()
    except OSError:
        return False
    mode = st.st_mode
    if criteria == "suid":
        return bool(mode & stat.S_ISUID)
    if criteria == "sgid":
        return bool(mode & stat.S_ISGID)
    if criteria == "sticky":
        return bool(mode & stat.S_ISVTX)
    if criteria == "world_writable":
        return bool(mode & 0o002)
    if criteria == "ownerless":
        try:
            pwd.getpwuid(st.st_uid)
            return False
        except KeyError:
            return True
    if criteria == "hidden":
        return p.name.startswith(".")
    if criteria == "device":
        return stat.S_ISCHR(mode) or stat.S_ISBLK(mode)
    return False


def _owner_name(uid: int) -> str:
    """UID의 소유자 이름을 반환한다. passwd에 없으면 UID 문자열로 대체한다."""
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def _matches_criteria_predicate(p: Path, criteria: dict) -> bool:
    """객체형 criteria를 평가한다. 각 조건은 OR로 결합된다(하나라도 충족하면 매칭)."""
    try:
        st = p.stat()
    except OSError:
        return False
    if "owner_ne" in criteria:
        if _owner_name(st.st_uid) != criteria["owner_ne"]:
            return True
    if "mode_not_allowed" in criteria:
        mask = mode_allowed_mask(criteria["mode_not_allowed"])
        if (stat.S_IMODE(st.st_mode) & ~mask) != 0:
            return True
    return False


def _collect_package(target: dict, root: str | None) -> CollectionOutcome:
    """설치된 패키지 버전을 수집한다. (마커 파일로 테스트 가능)"""
    name = target.get("name")
    if not name:
        return CollectionOutcome(error="package target에 name이 없음")

    p = _resolve(root, f"/var/lib/{name}.version")
    if p.exists():
        try:
            version = p.read_text(encoding="utf-8").strip()
        except OSError:
            version = "unknown"
    else:
        version = "unknown"

    return CollectionOutcome(
        value=version,
        observations=[{"target": name, "attribute": "version", "observed": version}],
    )


def _collect_document(target: dict, root: str | None) -> CollectionOutcome:
    """문서 존재 여부를 수집한다. (정책/절차 문서)"""
    name = target.get("name")
    if not name:
        return CollectionOutcome(error="document target에 name이 없음")

    p = _resolve(root, f"/docs/{name}.txt")
    exists = p.exists()
    return CollectionOutcome(
        value=exists,
        observations=[{"target": name, "attribute": "existence",
                       "observed": "exists" if exists else "not_exists"}],
    )


def _collect_service(target: dict, root: str | None) -> CollectionOutcome:
    name = target.get("name")
    if not name:
        return CollectionOutcome(error="service target에 name이 없음")
    mechanisms = target.get("mechanisms") or ["systemd", "inetd", "xinetd"]
    port = target.get("port")
    value, observations = service_status(name, mechanisms, root, port=port)
    if value == "error":
        detail = ", ".join(f"{o['target']}={o['observed']}" for o in observations)
        return CollectionOutcome(error=f"서비스 상태 판단 불가: {detail}")
    return CollectionOutcome(value=value, observations=observations)


def service_status(
    name: str, mechanisms: list[str], root: str | None, port: int | None = None
) -> tuple[str, list[dict]]:
    """서비스가 실제 사용 가능한 상태인지 판별한다.

    반환: (value, observations)
    - value: "enabled"(사용 중) / "disabled"(미사용) / "error"(판단 불가)
    - observations: 판단에 사용한 관찰 사실 [{target, attribute, observed}]

    판단 기준:
    - 런타임(telnetd 프로세스 실행 / TCP 포트 listening)이면 사용 중.
    - systemd는 "active"(실행 중)일 때 사용 중.
    - xinetd/inetd는 슈퍼서버 모델이므로 "enabled"일 때 사용 중.
    - 그 외(not_present/not_configured/disabled 등)는 미사용.

    주의: 메커니즘 부재(not_present)는 그 자체로 "미사용"의 근거가 되지 않는다.
    런타임 확인 + 모든 메커니즘의 상태를 종합해 판단한다.
    """
    states: dict[str, str] = {}
    for mech in mechanisms:
        if mech == "systemd":
            states["systemd"] = _systemd_state(name, root)
        elif mech == "xinetd":
            states["xinetd"] = _xinetd_state(name, root)
        elif mech == "inetd":
            states["inetd"] = _inetd_state(name, root)

    process_state = _process_state(name, root)
    port_state = _port_state(name, root)

    # 지정된 메커니즘만 관찰 항목으로 남기고, 런타임(프로세스/포트)은 항상 남긴다.
    observations: list[dict] = []
    if "systemd" in mechanisms:
        observations.append({"target": "systemd", "attribute": f"{name}.service", "observed": states["systemd"]})
    if "xinetd" in mechanisms:
        observations.append({"target": "xinetd", "attribute": name, "observed": states["xinetd"]})
    if "inetd" in mechanisms:
        observations.append({"target": "inetd", "attribute": name, "observed": states["inetd"]})
    observations.append({"target": f"{name}d", "attribute": "process", "observed": process_state})
    observations.append({"target": f"tcp/{port}" if port is not None else "tcp", "attribute": "listening", "observed": port_state})

    if any(v == "error" for v in states.values()):
        return "error", observations

    usable = (
        process_state == "running"
        or port_state == "yes"
        or states.get("systemd") == "active"
        or states.get("xinetd") == "enabled"
        or states.get("inetd") == "enabled"
    )
    return ("enabled" if usable else "disabled"), observations


def _process_state(name: str, root: str | None) -> str:
    """서비스 데몬 프로세스 실행 여부. (테스트용 마커 /run/<name>.pid)"""
    return "running" if _resolve(root, f"/run/{name}.pid").exists() else "not_running"


def _port_state(name: str, root: str | None) -> str:
    """서비스 포트 listening 여부. (테스트용 마커 /run/<name>.listening)"""
    return "yes" if _resolve(root, f"/run/{name}.listening").exists() else "no"


def _xinetd_state(name: str, root: str | None) -> str:
    """xinetd에서 서비스 상태를 판별한다.

    enabled / disabled / not_configured / not_present / error
    """
    dir_p = _resolve(root, "/etc/xinetd.d")
    if not dir_p.exists():
        return "not_present"
    p = dir_p / name
    if not p.exists():
        return "not_configured"
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*disable\s*=\s*(yes|no)\s*(#.*)?$", line, re.IGNORECASE)
            if m:
                return "enabled" if m.group(1).lower() == "no" else "disabled"
    except OSError:
        return "error"
    return "disabled"


def _inetd_state(name: str, root: str | None) -> str:
    """inetd에서 서비스 상태를 판별한다.

    enabled / disabled / not_configured / not_present / error
    """
    p = _resolve(root, "/etc/inetd.conf")
    if not p.exists():
        return "not_present"
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "error"

    has_line = False
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            stripped = s.lstrip("#").strip()
            if stripped.split() and stripped.split()[0] == name:
                has_line = True
            continue
        if s.split()[0] == name:
            return "enabled"
    return "disabled" if has_line else "not_configured"


def _systemd_state(name: str, root: str | None) -> str:
    """systemd에서 서비스 상태를 판별한다.

    active / enabled / masked / disabled / not_configured / not_present / error
    """
    unit_names = (f"{name}.socket", f"{name}.service")

    if not _systemd_present(root):
        return "not_present"

    # active (런타임 프록시)
    if _resolve(root, f"/run/systemd/{name}.active").exists():
        return "active"

    # masked
    for unit in unit_names:
        p = _resolve(root, f"/etc/systemd/system/{unit}")
        if p.is_symlink():
            try:
                if os.readlink(p) == "/dev/null":
                    return "masked"
            except OSError:
                return "error"

    # enabled (wants 심볼릭 링크)
    for wants in ("sockets.target.wants", "multi-user.target.wants"):
        for unit in unit_names:
            if _resolve(root, f"/etc/systemd/system/{wants}/{unit}").exists():
                return "enabled"

    # installed (unit 파일 존재)
    for base in ("/usr/lib/systemd/system", "/etc/systemd/system"):
        for unit in unit_names:
            if _resolve(root, f"{base}/{unit}").exists():
                return "disabled"

    return "not_configured"


def _systemd_present(root: str | None) -> bool:
    for d in ("/run/systemd", "/etc/systemd/system", "/usr/lib/systemd/system"):
        if _resolve(root, d).exists():
            return True
    return False
