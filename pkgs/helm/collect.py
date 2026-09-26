"""Helm collector: nine tiles -> status.json.

Python 3 stdlib only. One subprocess entry point (`run`) and two host-probe
seams (`read_text`, `disk_free_fraction`) so tests can monkeypatch cleanly.
Every tile function is wrapped so a missing binary, a timeout, or a parse
error yields status "unknown" instead of crashing the whole collection.

See docs/superpowers/specs/2026-09-02-helm-design.md for the normative
tile rules and the drift algorithm.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import functools
import html
import json
import os
import pathlib
import re
import socket
import subprocess
import sys

import evidence

TILE_NAMES = [
    "backup-snapshot",
    "backup-parity",
    "timers",
    "basket-doctor",
    "broker",
    "gpu",
    "host",
    "drift",
    "flake-check",
]


def run(
    argv: list[str], timeout: float = 10.0, env: dict | None = None
) -> subprocess.CompletedProcess:
    """The ONLY subprocess entry point. Tests monkeypatch this."""
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, env=env, check=False
    )


def read_text(path: str) -> str:
    """The ONLY filesystem-text-read seam for host-probe tiles. Tests monkeypatch this."""
    return pathlib.Path(path).read_text()


def disk_free_fraction(path: str) -> float:
    """Fraction of blocks free on the filesystem containing `path`. Tests monkeypatch this."""
    st = os.statvfs(path)
    return st.f_bavail / st.f_blocks


def system_generation() -> str | None:
    """Basename of the live system profile link; a seam for tests."""
    try:
        return os.path.basename(os.readlink("/nix/var/nix/profiles/system"))
    except OSError:
        return None


def _parse_iso(s: str) -> datetime.datetime:
    """Parse an RFC3339 timestamp, tolerating a trailing 'Z'."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dtv = datetime.datetime.fromisoformat(s)
    if dtv.tzinfo is None:
        dtv = dtv.replace(tzinfo=datetime.timezone.utc)
    return dtv


def tile(name: str):
    """Wrap a tile_* function: any Exception -> status unknown, never a crash."""

    def deco(fn):
        @functools.wraps(fn)
        def wrapped(cfg, now):
            checked_at = now.isoformat()
            try:
                result = fn(cfg, now)
            except Exception as e:  # noqa: BLE001 - per-tile isolation is the point
                return {
                    "name": name,
                    "status": "unknown",
                    "summary": f"{type(e).__name__}: {e}",
                    "detail": {},
                    "checked_at": checked_at,
                }
            status, summary, detail = result
            return {
                "name": name,
                "status": status,
                "summary": summary,
                "detail": detail,
                "checked_at": checked_at,
            }

        return wrapped

    return deco


@tile("backup-snapshot")
def tile_backup_snapshot(cfg, now):
    env = {
        **os.environ,
        "RESTIC_REPOSITORY": cfg["restic_repository"],
        "RESTIC_PASSWORD_FILE": cfg["restic_password_file"],
        # helm-collect.service runs with ProtectHome=read-only; restic
        # needs a writable cache dir, provided by the unit's tmpfiles rule.
        "RESTIC_CACHE_DIR": cfg["restic_cache_dir"],
    }
    # --no-lock: `snapshots` is a pure read and helm-collect.service's
    # sandbox (ProtectSystem=strict, ReadWritePaths only /var/lib/helm and
    # /var/lib/helm-cache) has no write access to the restic repository
    # itself -- restic's own lock file would otherwise need one, and
    # `snapshots` failed after a 60s timeout waiting on a lock it could
    # never take (audit F5). This is restic's documented flag for exactly
    # that case, not a correctness compromise.
    cp = run(
        ["restic", "snapshots", "--no-lock", "--json", "--latest", "1"],
        timeout=60,
        env=env,
    )
    if cp.returncode != 0:
        return "fail", f"restic exited {cp.returncode}", {"stderr": cp.stderr[-2000:]}
    snaps = json.loads(cp.stdout)
    if not snaps:
        return "fail", "no snapshot", {}
    # --latest N returns the latest N snapshots PER group (host + path set);
    # the newest overall is not necessarily the first list element, so pick
    # by `time` across every returned entry instead of trusting list order.
    snap = max(snaps, key=lambda s: _parse_iso(s["time"]))
    when = _parse_iso(snap["time"])
    age_h = (now - when).total_seconds() / 3600.0
    short_id = snap.get("short_id", "")
    detail = {
        "time": snap["time"],
        "short_id": short_id,
        "age_h": round(age_h, 2),
        "groups": len(snaps),
    }
    if age_h < 26:
        return "ok", f"snapshot {short_id} {age_h:.1f}h ago", detail
    if age_h < 50:
        return "warn", f"snapshot {short_id} {age_h:.1f}h ago", detail
    return "fail", f"snapshot {short_id} {age_h:.1f}h ago", detail


_PARITY_RE = re.compile(r"^proton-backup-push: (OK|FAIL)\b(.*)$")


@tile("backup-parity")
def tile_backup_parity(cfg, now):
    # The unit's own last result is the source of truth ahead of the journal:
    # a failed push or a killed run stays red even when the last log line was
    # a stale "OK". The journal scan below remains for the detail text and age.
    result, status = _unit_result(["--user"], "proton-drive-push.service")
    if result != "success" or status != "0":
        return (
            "fail",
            f"proton-drive-push.service last result {result}, status {status}",
            {"unit_result": result, "exec_main_status": status},
        )
    cp = run(
        [
            "journalctl",
            "--user",
            "-u",
            "proton-drive-push",
            "-o",
            "json",
            "--no-pager",
            "-n",
            "500",
        ]
    )
    if cp.returncode != 0:
        return (
            "fail",
            f"journalctl exited {cp.returncode}",
            {"stderr": cp.stderr[-2000:]},
        )
    last = None
    for line in cp.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("MESSAGE", "")
        if isinstance(msg, list):
            msg = "".join(msg)
        m = _PARITY_RE.match(msg)
        if m:
            last = (m.group(1), m.group(2).strip(), rec.get("__REALTIME_TIMESTAMP"))
    if last is None:
        return "fail", "no proton-backup-push result in journal", {}
    verdict, rest, ts_raw = last
    age_h = None
    if ts_raw is not None:
        try:
            ts = float(ts_raw) / 1e6
            age_h = (now.timestamp() - ts) / 3600.0
        except (TypeError, ValueError):
            age_h = None
    detail = {
        "verdict": verdict,
        "detail": rest,
        "age_h": round(age_h, 2) if age_h is not None else None,
    }
    if verdict == "FAIL":
        return "fail", f"proton-backup-push FAIL {rest}".strip(), detail
    if age_h is None:
        return "fail", "proton-backup-push OK but timestamp unparseable", detail
    if age_h < 26:
        return "ok", f"proton-backup-push OK {age_h:.1f}h ago", detail
    return "warn", f"proton-backup-push OK but {age_h:.1f}h ago", detail


_TIMER_PROPS = "ActiveState,NextElapseUSecRealtime,NextElapseUSecMonotonic"


def _timer_armed(cp):
    """A timer is armed iff active AND it has a next-elapse time in either
    clock. Calendar-triggered timers (OnCalendar=) report only
    NextElapseUSecRealtime; monotonic-triggered timers (OnUnitActiveSec=,
    OnBootSec=, OnActiveSec=, ...) report only NextElapseUSecMonotonic and
    leave NextElapseUSecRealtime empty even while healthy — requiring the
    realtime field unconditionally would flag every such timer as unarmed.
    """
    if cp.returncode != 0:
        return False
    kv = {}
    for line in cp.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            kv[k] = v
    if kv.get("ActiveState") != "active":
        return False
    if kv.get("NextElapseUSecRealtime", "").strip():
        return True
    monotonic = kv.get("NextElapseUSecMonotonic", "").strip()
    return bool(monotonic) and monotonic != "0"


def _unit_result(scope_args, unit):
    """Last `Result=` and `ExecMainStatus=` from `systemctl <scope> show`.
    A service that has never run reports `Result=success` (systemd's default),
    so a fresh install is not red. systemd emits ExecMainStatus as an integer
    for every unit (the R3b and R3r Opus gates probed a never-run and a
    non-existent unit on core, 2026-09-05 — docs/reviews/2026-09-05-opus-review-ev3-R3b.md);
    when systemctl prints nothing, result is empty and the `result != "success"`
    clause reds the tile."""
    cp = run(
        [
            "systemctl",
            *scope_args,
            "show",
            "-p",
            "Result",
            "-p",
            "ExecMainStatus",
            unit,
        ]
    )
    result = ""
    status = ""
    for line in cp.stdout.splitlines():
        if line.startswith("Result="):
            result = line[len("Result=") :]
        elif line.startswith("ExecMainStatus="):
            status = line[len("ExecMainStatus=") :]
    return result, status


@tile("timers")
def tile_timers(cfg, now):
    unarmed = []
    failed = []
    checked = []
    for t in cfg.get("timers_system", []):
        cp = run(["systemctl", "show", "-p", _TIMER_PROPS, t])
        armed = _timer_armed(cp)
        checked.append({"timer": t, "scope": "system", "armed": armed})
        if not armed:
            unarmed.append(t)
        service = t[: -len(".timer")] + ".service"
        result, _ = _unit_result([], service)
        if result != "success":
            failed.append(f"{service}: {result}")
    for t in cfg.get("timers_user", []):
        cp = run(
            [
                "systemctl",
                "--user",
                "show",
                "-p",
                _TIMER_PROPS,
                t,
            ]
        )
        armed = _timer_armed(cp)
        checked.append({"timer": t, "scope": "user", "armed": armed})
        if not armed:
            unarmed.append(t)
        service = t[: -len(".timer")] + ".service"
        result, _ = _unit_result(["--user"], service)
        if result != "success":
            failed.append(f"{service}: {result}")
    detail = {"timers": checked}
    parts = []
    if unarmed:
        parts.append("not armed: " + ", ".join(unarmed))
    if failed:
        parts.append("failed: " + ", ".join(failed))
    if parts:
        return "fail", "; ".join(parts), detail
    return "ok", f"{len(checked)} timer(s) armed", detail


_DOCTOR_RE = re.compile(r"^(PASS|WARN|FAIL)\s+(\S+)\s*(.*)$")


@tile("basket-doctor")
def tile_basket_doctor(cfg, now):
    cp = run([cfg["basket_bin"], "doctor"], timeout=20)
    lines = []
    for line in cp.stdout.splitlines():
        m = _DOCTOR_RE.match(line.strip())
        if m:
            lines.append(
                {"level": m.group(1), "check": m.group(2), "detail": m.group(3)}
            )
    if not lines and cp.returncode != 0:
        return (
            "fail",
            f"basket doctor exited {cp.returncode} with no parsable output",
            {"stderr": cp.stderr[-2000:]},
        )
    fails = [entry for entry in lines if entry["level"] == "FAIL"]
    warns = [entry for entry in lines if entry["level"] == "WARN"]
    detail = {"lines": lines}
    if fails:
        return (
            "fail",
            "; ".join(f"{e['check']} {e['detail']}".strip() for e in fails),
            detail,
        )
    if warns:
        return (
            "warn",
            "; ".join(f"{e['check']} {e['detail']}".strip() for e in warns),
            detail,
        )
    return "ok", f"{len(lines)} check(s) passed", detail


@tile("broker")
def tile_broker(cfg, now):
    # An empty broker_audit_paths (no services.egress-broker.instances
    # declared, or brokerInstances = []) is not "0 allow, 0 deny" -- that
    # would read as a quiet-but-healthy broker on a host that has none.
    # Report "unknown" honestly before the loop even starts (audit F20).
    if not cfg.get("broker_audit_paths"):
        return "unknown", "no broker instance configured", {}
    per_instance = {}
    readable = 0
    cutoff = now.timestamp() - 86400
    for entry in cfg.get("broker_audit_paths", []):
        instance = entry["instance"]
        path = entry["path"]
        try:
            text = read_text(path)
        except OSError:
            per_instance[instance] = "error"
            continue
        readable += 1
        allow = 0
        deny = 0
        tunnels = 0
        denied_hosts = collections.Counter()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = rec.get("ts")
            if ts is None or ts < cutoff:
                continue
            verdict = rec.get("verdict")
            if verdict == "allow":
                allow += 1
                # An accepted CONNECT (policy.py's http_connect) opens a
                # tunnel rather than forwarding one decrypted request; it
                # still counts among "allow" (the tunnel WAS permitted) but
                # is broken out separately here so the tile does not blend
                # tunnel-opens into the same number as ordinary requests.
                if rec.get("method") == "CONNECT":
                    tunnels += 1
            elif verdict == "deny":
                deny += 1
                host = rec.get("host")
                if host:
                    denied_hosts[host] += 1
        per_instance[instance] = {
            "allow": allow,
            "deny": deny,
            "tunnels": tunnels,
            "top_denied": [list(x) for x in denied_hosts.most_common(5)],
        }
    if readable == 0:
        return "unknown", "no audit log readable", per_instance
    total_allow = sum(v["allow"] for v in per_instance.values() if isinstance(v, dict))
    total_deny = sum(v["deny"] for v in per_instance.values() if isinstance(v, dict))
    total_tunnels = sum(
        v["tunnels"] for v in per_instance.values() if isinstance(v, dict)
    )
    return (
        "ok",
        f"{total_allow} allow ({total_tunnels} tunnel(s)), {total_deny} deny (24h)",
        per_instance,
    )


@tile("gpu")
def tile_gpu(cfg, now):
    # A systemd --user unit's PATH lacks /run/current-system/sw/bin, where
    # the driver's nvidia-smi actually lives -- use the module-configured
    # absolute path, falling back to the bare name for callers (tests, a
    # manual `nix run`) that don't set it.
    cp = run(
        [
            cfg.get("nvidia_smi_bin", "nvidia-smi"),
            "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ]
    )
    if cp.returncode != 0:
        return (
            "fail",
            f"nvidia-smi exited {cp.returncode}",
            {"stderr": cp.stderr[-2000:]},
        )
    line = cp.stdout.strip().splitlines()[0]
    parts = [p.strip() for p in line.split(", ")]
    name, util, mem_used, mem_total, temp, power = parts
    detail = {
        "name": name,
        "utilization_pct": int(util),
        "memory_used_mib": int(mem_used),
        "memory_total_mib": int(mem_total),
        "temperature_c": int(temp),
        "power_draw_w": float(power),
    }
    mem_frac = (
        detail["memory_used_mib"] / detail["memory_total_mib"]
        if detail["memory_total_mib"]
        else 0.0
    )
    if detail["temperature_c"] >= 85 or mem_frac >= 0.95:
        return (
            "warn",
            f"{name} {detail['temperature_c']}C {mem_frac * 100:.0f}% mem",
            detail,
        )
    return "ok", f"{name} {detail['temperature_c']}C {mem_frac * 100:.0f}% mem", detail


@tile("host")
def tile_host(cfg, now):
    loadavg = read_text("/proc/loadavg").split()[:3]
    meminfo = {}
    for line in read_text("/proc/meminfo").splitlines():
        k, _, v = line.partition(":")
        v = v.strip().split()[0] if v.strip() else None
        if v is not None:
            meminfo[k] = int(v)
    swaps_lines = read_text("/proc/swaps").splitlines()
    swap_present = len([line for line in swaps_lines if line.strip()]) > 1
    free_frac = disk_free_fraction("/")
    detail = {
        "loadavg": loadavg,
        "mem_total_kb": meminfo.get("MemTotal"),
        "mem_available_kb": meminfo.get("MemAvailable"),
        "disk_free_fraction": round(free_frac, 4),
        "swap_present": swap_present,
    }
    if swap_present:
        return "fail", "swap in use", detail
    if free_frac < 0.05:
        return "fail", f"disk {free_frac * 100:.1f}% free", detail
    if free_frac < 0.15:
        return "warn", f"disk {free_frac * 100:.1f}% free", detail
    return "ok", f"disk {free_frac * 100:.1f}% free, no swap", detail


@tile("drift")
def tile_drift(cfg, now):
    # A systemd --user unit's PATH lacks /run/current-system/sw/bin, where
    # the system-generated nixos-version actually lives -- use the
    # module-configured absolute path, falling back to the bare name for
    # callers (tests, a manual `nix run`) that don't set it.
    cp = run(
        [cfg.get("nixos_version_bin", "nixos-version"), "--configuration-revision"]
    )
    if cp.returncode != 0:
        return (
            "fail",
            "live system has no configuration revision — set system.configurationRevision",
            {"stderr": cp.stderr.strip()},
        )
    live = cp.stdout.strip()
    dirty_live = live.endswith("-dirty") or live == "dirty"
    base = live.removesuffix("-dirty")

    head_cp = run(["git", "-C", cfg["repo"], "rev-parse", "HEAD"])
    if head_cp.returncode != 0:
        return (
            "unknown",
            "git rev-parse HEAD failed",
            {"stderr": head_cp.stderr.strip()},
        )
    head = head_cp.stdout.strip()

    status_cp = run(["git", "-C", cfg["repo"], "status", "--porcelain"])
    if status_cp.returncode != 0:
        return "unknown", "git status failed", {"stderr": status_cp.stderr.strip()}
    tree_dirty = bool(status_cp.stdout.strip())

    detail = {
        "live": live,
        "head": head,
        "dirty_live": dirty_live,
        "tree_dirty": tree_dirty,
    }

    if live == "dirty":
        return "warn", "switched from a tree with no commit", detail
    if base == head:
        if dirty_live:
            return "warn", "switched from a dirty tree", detail
        if tree_dirty:
            return "warn", "working tree has uncommitted changes", detail
        return "ok", f"live = HEAD {head[:12]}", detail
    if _docs_equivalent(cfg, base, head):
        detail["docs_only_ahead"] = True
        if dirty_live:
            return "warn", "switched from a dirty tree", detail
        if tree_dirty:
            return "warn", "working tree has uncommitted changes", detail
        return "ok", f"live {base[:12]} = HEAD {head[:12]} except docs", detail
    detail["docs_only_ahead"] = False
    return "fail", f"live {base[:12]} ≠ HEAD {head[:12]}", detail


def _docs_equivalent(cfg, a: str, b: str) -> bool:
    """True when a and b differ only under docs/ or in *.md (D4). Exit 128
    (unknown revision) counts as different."""
    if a == b:
        return True
    cp = run(
        [
            "git",
            "-C",
            cfg["repo"],
            "diff",
            "--quiet",
            a,
            b,
            "--",
            ".",
            ":!docs",
            ":!*.md",
        ]
    )
    return cp.returncode == 0


def _store(cfg) -> str:
    """The evidence store root for this config (EVIDENCE_STORE's default)."""
    return cfg.get("evidence_dir") or evidence.DEFAULT_STORE


def _check_rows(cfg, name: str) -> list[dict]:
    """Observations for one check name from <store>/checks.jsonl, oldest
    first, torn lines skipped, capped to the newest 50."""
    path = pathlib.Path(_store(cfg)) / "checks.jsonl"
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            r.get("kind") == "check"
            and r.get("name") == name
            and isinstance(r.get("rev"), str)
        ):
            rows.append(r)
    rows.sort(key=lambda r: r.get("ts", ""))
    return rows[-50:]


def _live_rev(cfg) -> str | None:
    try:
        cp = run(
            [cfg.get("nixos_version_bin", "nixos-version"), "--configuration-revision"]
        )
    except FileNotFoundError:
        return None
    if cp.returncode != 0:
        return None
    live = cp.stdout.strip()
    return None if live in ("", "dirty") else live.removesuffix("-dirty")


def _tile_flake_check_from_file(cfg, now, head):
    path = pathlib.Path(cfg["flake_check_file"])
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return "fail", "flake-check.json missing or unreadable", {}
    started = _parse_iso(data["started"])
    age_h = (now - started).total_seconds() / 3600.0
    detail = dict(data, age_h=round(age_h, 2), head=head)
    if not data.get("ok"):
        return "fail", f"flake check failed (exit {data.get('exit')})", detail
    if head is not None and data.get("rev") != head:
        return (
            "warn",
            f"flake check rev {str(data.get('rev'))[:12]} != HEAD {head[:12]}",
            detail,
        )
    if age_h >= 26:
        return "warn", f"flake check {age_h:.1f}h old", detail
    return "ok", f"flake check ok {age_h:.1f}h ago", detail


@tile("flake-check")
def tile_flake_check(cfg, now):
    head_cp = run(["git", "-C", cfg["repo"], "rev-parse", "HEAD"])
    head = head_cp.stdout.strip() if head_cp.returncode == 0 else None
    rows = _check_rows(cfg, "flake-check")
    if not rows:
        return _tile_flake_check_from_file(cfg, now, head)
    live = _live_rev(cfg)

    def newest_covering(rev):
        if rev is None:
            return None
        for r in reversed(rows):
            if _docs_equivalent(cfg, r["rev"], rev):
                return r
        return None

    for_head = newest_covering(head)
    for_live = newest_covering(live)
    latest = rows[-1]
    detail = {
        "head": head,
        "live": live,
        "for_head": for_head,
        "for_live": for_live,
        "latest": latest,
    }

    def age_h(r):
        return round((now - _parse_iso(r["ts"])).total_seconds() / 3600.0, 2)

    if for_head is not None:
        detail["age_h"] = age_h(for_head)
        who = f"{for_head.get('class', '?')}, {for_head.get('src', '?')}"
        if not for_head.get("ok"):
            return (
                "fail",
                f"flake check FAILED @{for_head['rev'][:12]} covers HEAD ({who})",
                detail,
            )
        if detail["age_h"] >= 48:
            return (
                "warn",
                f"flake check ok @{for_head['rev'][:12]} covers HEAD but is {detail['age_h']:.1f}h old",
                detail,
            )
        return (
            "ok",
            f"flake check ok @{for_head['rev'][:12]} covers HEAD ({who}, {detail['age_h']:.1f}h ago)",
            detail,
        )
    if for_live is not None and for_live.get("ok"):
        return (
            "warn",
            f"flake check ok @{for_live['rev'][:12]} covers the live system; HEAD {str(head)[:12]} unchecked",
            detail,
        )
    if not latest.get("ok"):
        return (
            "fail",
            f"flake check FAILED @{latest['rev'][:12]} ({latest.get('src', '?')})",
            detail,
        )
    return (
        "warn",
        f"flake check ok @{latest['rev'][:12]} covers neither HEAD nor live",
        detail,
    )


def _read_marker(cfg) -> str:
    """The active profile marker file content, or "unknown" when unreadable."""
    try:
        return read_text(cfg.get("profile_marker", "/etc/helm/profile")).strip()
    except OSError:
        return "unknown"


def collect_all(cfg: dict, now: datetime.datetime) -> dict:
    tiles = [
        tile_backup_snapshot(cfg, now),
        tile_backup_parity(cfg, now),
        tile_timers(cfg, now),
        tile_basket_doctor(cfg, now),
        tile_broker(cfg, now),
        tile_gpu(cfg, now),
        tile_host(cfg, now),
        tile_drift(cfg, now),
        tile_flake_check(cfg, now),
    ]
    return {
        "schema": 1,
        "generated_at": now.isoformat(),
        "hostname": socket.gethostname(),
        "interval_s": cfg["interval_s"],
        "active_profile": _read_marker(cfg),
        "generation": system_generation(),
        "tiles": tiles,
    }


def _status_rows(cfg) -> list[dict]:
    return [
        r
        for r in evidence.read(_store(cfg), "helm-status")
        if r.get("kind") == "helm-status"
    ]


def record_status(cfg, status: dict, now) -> dict | None:
    """One row per verdict change, plus an hourly heartbeat; None when nothing
    is written. A recording problem is logged and never fails the collector."""
    current = {t["name"]: t["status"] for t in status["tiles"]}
    rows = _status_rows(cfg)
    last = rows[-1] if rows else None
    if last is None or last.get("tiles") != current:
        reason = "change"
    elif (now - _parse_iso(last["ts"])).total_seconds() >= 3600:
        reason = "heartbeat"
    else:
        return None
    row = {
        "kind": "helm-status",
        "tiles": current,
        "reason": reason,
    }
    try:
        return evidence.append(
            _store(cfg),
            "helm-status",
            row,
            ts=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
    except (OSError, ValueError) as e:
        print(f"helm-collect: evidence: {e}", file=sys.stderr)
        return None


def annotate_since(cfg, status: dict) -> None:
    rows = _status_rows(cfg)
    for t in status["tiles"]:
        since = status["generated_at"]
        for r in reversed(rows):
            if r.get("tiles", {}).get(t["name"]) == t["status"]:
                since = r["ts"]
            else:
                break
        t["since"] = since


def _local(ts: str) -> str:
    """Render an RFC3339 timestamp in the local zone as HH:MM TZ.

    A torn or hand-edited `since` from the history store is still shown:
    rendering is decoration and must never crash the collector. The value is
    escaped by render_html's `esc` either way, so nothing bypasses the
    zero-outbound invariant.
    """
    try:
        return _parse_iso(ts).astimezone().strftime("%H:%M %Z")
    except (ValueError, TypeError):
        return str(ts)


def write_atomic(path: pathlib.Path, data: str, mode: int = 0o640) -> None:
    path = pathlib.Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        # os.open's mode is masked by the process umask, so a restrictive
        # umask (the operator user's real one, e.g. 0o077) can silently
        # drop the group-read bit that static-web-server's
        # SupplementaryGroups=helm depends on -- fchmod sets it exactly.
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w") as f:
            f.write(data)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(str(tmp), str(path))


_STATUS_COLOR = {
    "ok": "#2e7d32",
    "warn": "#ed6c02",
    "fail": "#c62828",
    "unknown": "#616161",
}

_PAGE_CSS = """
  :root { color-scheme: light dark; }
  body { font-family: system-ui, sans-serif; margin: 0; padding: 1.5rem;
         background: #fafafa; color: #111; }
  header { margin-bottom: 1.5rem; }
  header h1 { margin: 0 0 0.25rem 0; font-size: 1.4rem; }
  header .meta { color: #555; font-size: 0.9rem; }
  main.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
              gap: 1rem; }
  section.tile { border-radius: 0.5rem; padding: 1rem; border-left: 0.4rem solid #616161;
                 background: #fff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15); }
  section.tile h2 { margin: 0 0 0.4rem 0; font-size: 1.05rem; text-transform: none; }
  section.tile p { margin: 0 0 0.5rem 0; }
  section.tile.ok { border-left-color: #2e7d32; }
  section.tile.warn { border-left-color: #ed6c02; }
  section.tile.fail { border-left-color: #c62828; }
  section.tile.unknown { border-left-color: #616161; }
  section.tile pre { white-space: pre-wrap; word-break: break-word; font-size: 0.8rem;
                      background: #f0f0f0; padding: 0.5rem; border-radius: 0.3rem; }
  .verdict { font-size: 0.8rem; font-weight: 600; margin-left: 0.4rem; }
  details summary { cursor: pointer; color: #555; }
  @media (prefers-color-scheme: dark) {
    body { background: #121212; color: #eee; }
    header .meta { color: #aaa; }
    section.tile { background: #1e1e1e; box-shadow: none; }
    section.tile pre { background: #2a2a2a; }
    details summary { color: #aaa; }
  }
""".strip()


def render_html(status: dict, now: datetime.datetime) -> str:
    """Render the self-contained status page. Every string that reaches the
    output passes through `esc`. No <script>, no src=, no href="http.

    `now` is kept in the signature for callers (main() passes the same
    `now` used to build `status`) even though the page no longer computes a
    staleness badge from it (audit F9: the collector regenerates this page,
    so a viewer can never see a page describing its own collector as stale
    -- the "timers" tile already audits helm-collect.timer for that).
    """
    # html.escape leaves "=" untouched, so an adversarial value like
    # `<img src=x>` becomes the inert text "&lt;img src=x&gt;" — safe as
    # markup, but it still contains the literal substring "src=", which the
    # zero-outbound invariant (no <script, no src=, no href="http anywhere
    # in the page) forbids even inside escaped free text. Escape "=" too so
    # no escaped value can ever reintroduce that substring.
    esc = lambda s: html.escape(str(s), quote=True).replace("=", "&#61;")

    hostname = esc(status.get("hostname", ""))
    generated_at = status.get("generated_at", "")
    interval_s = status.get("interval_s", 0)
    try:
        generated_dt = _parse_iso(generated_at)
        next_dt = generated_dt + datetime.timedelta(seconds=interval_s)
        generated_disp = esc(
            f"{generated_dt.astimezone().strftime('%H:%M:%S %Z')} "
            f"({generated_dt.strftime('%H:%M:%SZ')})"
        )
        next_disp = esc(next_dt.astimezone().strftime("%H:%M %Z"))
    except (ValueError, TypeError):
        generated_disp = esc(generated_at)
        next_disp = "?"

    tile_html = []
    for t in status.get("tiles", []):
        name = esc(t.get("name", ""))
        tstatus = t.get("status", "unknown")
        tstatus_class = tstatus if tstatus in _STATUS_COLOR else "unknown"
        summary = esc(t.get("summary", ""))
        detail_json = esc(
            json.dumps(t.get("detail", {}), indent=2, sort_keys=True, default=str)
        )
        parts = []
        parts.append(
            f'<h2>{name} <span class="verdict">{esc(tstatus_class.upper())}</span></h2>'
        )
        parts.append(f"<p>{summary}</p>")
        if t.get("since"):
            parts.append(f'<p class="since">since {esc(_local(t["since"]))}</p>')
        parts.append(
            f"<details><summary>detail</summary><pre>{detail_json}</pre></details>"
        )
        tile_html.append(
            f'<section class="tile {esc(tstatus_class)}">'
            + "".join(parts)
            + "</section>"
        )

    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="60; url=/">'
        f"<title>Helm · {hostname}</title>"
        f"<style>{_PAGE_CSS}</style>"
        "</head><body>"
        "<header>"
        f"<h1>Helm · {hostname}</h1>"
        '<div class="meta">'
        f"generated {generated_disp} · next {next_disp}"
        "</div>"
        "</header>"
        f'<main class="grid">{"".join(tile_html)}</main>'
        "</body></html>"
    )


def render_text(status: dict) -> str:
    """Plain-text rendering for `helm-collect --print`: one line per tile."""
    lines = [
        f"Helm · {status.get('hostname', '')} · generated {status.get('generated_at', '')}"
    ]
    for t in status.get("tiles", []):
        line = (
            f"{t.get('status', 'unknown').upper():<7} {t.get('name', ''):<16} "
            f"{t.get('summary', '')}"
        )
        if t.get("since"):
            line += f"  since {_local(t['since'])}"
        lines.append(line)
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="helm-collect")
    parser.add_argument("--config", default="/etc/helm/config.json")
    parser.add_argument("--out")
    parser.add_argument("--print", action="store_true", dest="do_print")
    args = parser.parse_args(argv)

    cfg = json.loads(pathlib.Path(args.config).read_text())
    now = datetime.datetime.now(datetime.timezone.utc)
    status = collect_all(cfg, now)

    if args.do_print:
        # A history failure never blocks the page: the verdict stream and the
        # per-tile "since" annotation are best-effort decoration.
        try:
            annotate_since(cfg, status)
        except Exception as e:  # noqa: BLE001 - history is best-effort
            print(f"helm-collect: history: {e}", file=sys.stderr)
        print(render_text(status))
        return 0

    # record_status runs only on the write path -- `helm-collect --print`
    # (what the read-only `helm-status` wrapper runs) reports verbatim without
    # appending verdict-history rows, so a hand run never interleaves with the
    # 5-minute collector's history. It runs BEFORE annotate_since so that on
    # the run where a verdict changes, the current row is already in the
    # history and annotate_since finds its "…Z" timestamp instead of falling
    # back to generated_at's microsecond "+00:00" form (two shapes in one
    # field -- audit E6b).
    try:
        record_status(cfg, status, now)
    except Exception as e:  # noqa: BLE001 - history is best-effort
        print(f"helm-collect: history: {e}", file=sys.stderr)

    try:
        annotate_since(cfg, status)
    except Exception as e:  # noqa: BLE001 - history is best-effort
        print(f"helm-collect: history: {e}", file=sys.stderr)

    out_dir = pathlib.Path(args.out or cfg["out_dir"])
    write_atomic(out_dir / "status.json", json.dumps(status, indent=2, sort_keys=True))
    write_atomic(out_dir / "index.html", render_html(status, now))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
