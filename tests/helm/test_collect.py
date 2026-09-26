import builtins
import datetime as dt
import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
# collect.py `import evidence`s at module top; the `unit` sandbox lays
# pkgs/helm and pkgs/evidence side by side, and this test reproduces that
# relative shape by putting pkgs/evidence on the path before loading collect.
sys.path.insert(0, str(HERE.parents[2] / "pkgs" / "evidence"))
import evidence

SRC = HERE.parents[2] / "pkgs" / "helm" / "collect.py"
spec = importlib.util.spec_from_file_location("collect", SRC)
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)

NOW = dt.datetime(2026, 9, 3, 8, 0, tzinfo=dt.timezone.utc)


def cp(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def fake_run(table):
    """table maps argv[0] (or a tuple prefix) to a CompletedProcess or an Exception."""

    def _run(argv, timeout=10.0, env=None):
        for key, val in table.items():
            k = key if isinstance(key, tuple) else (key,)
            if tuple(argv[: len(k)]) == k:
                if isinstance(val, Exception):
                    raise val
                return val
        raise FileNotFoundError(argv[0])

    return _run


def _unit_show(result, status="0", active="active", nxt="Sat 2026-09-06 03:00:00 UTC"):
    # One blob serving both `show -p <timer props> <name>.timer` (consumed by
    # _timer_armed: ActiveState/NextElapse) and `show -p Result -p
    # ExecMainStatus <name>.service` (consumed by _unit_result).
    return cp(
        f"ActiveState={active}\n"
        f"NextElapseUSecRealtime={nxt}\n"
        f"NextElapseUSecMonotonic=\n"
        f"Result={result}\n"
        f"ExecMainStatus={status}\n"
    )


def systemctl_fake(by_unit, scope=None):
    """Dispatch `systemctl show ... <unit>` on the unit name in argv[-1];
    unlisted units (the sibling .service the timers tile now queries) answer
    a clean success, matching systemd's `Result=success` for a never-run unit.

    `scope` pins the systemd scope so a wrong-scope mutation turns red:
    "user" requires argv[:3] == ["systemctl", "--user", "show"], "system"
    forbids "--user" anywhere in argv; None (the default) pins nothing, for
    callers that exercise both scopes in one fake."""

    def _run(argv, timeout=10.0, env=None):
        if argv[0] != "systemctl":
            raise FileNotFoundError(argv[0])
        if scope == "user" and argv[:3] != ["systemctl", "--user", "show"]:
            raise AssertionError(f"expected --user systemctl show, got {argv}")
        if scope == "system" and "--user" in argv:
            raise AssertionError(f"system-scope call must not pass --user: {argv}")
        return by_unit.get(argv[-1], _unit_show("success"))

    return _run


def base_cfg(tmp_path):
    return {
        "operator_user": "alice",
        "interval_s": 300,
        "repo": str(tmp_path / "repo"),
        "restic_repository": "/var/lib/restic/core",
        "restic_password_file": "/pw",
        "restic_cache_dir": "/var/lib/helm-cache",
        "basket_bin": "basket",
        "broker_audit_paths": [],
        "timers_system": [],
        "timers_user": [],
        "flake_check_file": str(tmp_path / "flake-check.json"),
        "out_dir": str(tmp_path),
        "evidence_dir": str(tmp_path / "evidence"),
    }


REV_H = "1" * 40
REV_L = "2" * 40
REV_O = "3" * 40


def git_table(head, live, equivalent_pairs, porcelain=""):
    """git rev-parse -> head; nixos-version -> live; git diff --quiet A B -> 0 when
    {A,B} is an equivalent pair, else 1; git status -> porcelain."""

    def _run(argv, timeout=10.0, env=None):
        if argv[0] == "nixos-version":
            return cp(live + "\n")
        if argv[:2] == ["git", "-C"] and "rev-parse" in argv:
            return cp(head + "\n")
        if argv[:2] == ["git", "-C"] and "status" in argv:
            return cp(porcelain)
        if argv[:2] == ["git", "-C"] and "diff" in argv:
            i = argv.index("--quiet")
            pair = frozenset(argv[i + 1 : i + 3])
            assert argv[argv.index("--") + 1 :] == [".", ":!docs", ":!*.md"]
            return cp("", 0 if pair in equivalent_pairs or len(pair) == 1 else 1)
        raise FileNotFoundError(argv[0])

    return _run


def obs(tmp_path, rev, ok, ts, src="helm-nightly", cls="nix-check"):
    d = tmp_path / "evidence"
    d.mkdir(exist_ok=True)
    with open(d / "checks.jsonl", "a") as fh:
        fh.write(
            json.dumps(
                {
                    "v": 1,
                    "ts": ts,
                    "kind": "check",
                    "name": "flake-check",
                    "rev": rev,
                    "ok": ok,
                    "class": cls,
                    "src": src,
                    "duration_s": 100,
                }
            )
            + "\n"
        )


def test_snapshot_fresh_is_ok(monkeypatch, tmp_path):
    snap = json.dumps(
        [{"time": "2026-09-03T02:00:00Z", "short_id": "16e29ff5", "paths": ["/x"]}]
    )
    monkeypatch.setattr(collect, "run", fake_run({"restic": cp(snap)}))
    t = collect.tile_backup_snapshot(base_cfg(tmp_path), NOW)
    assert t["status"] == "ok" and "16e29ff5" in t["summary"]


def test_snapshot_picks_newest_across_groups(monkeypatch, tmp_path):
    # restic --latest N returns the latest N snapshots PER group (host +
    # path set); the newest entry is not necessarily first or last. Four
    # groups, newest at index 1 (interior), with one entry (59cd359e) on a
    # different UTC offset and nanosecond precision from the rest: the tile
    # must pick by real time (honoring the offset), not list position and
    # not a naive string slice of the timestamp, and report how many groups
    # it saw. Times use RFC3339 nanoseconds, as restic emits them.
    snaps = json.dumps(
        [
            {
                "time": "2026-09-02T18:54:00.123456789-05:00",
                "short_id": "16e29ff5",
                "paths": ["/old"],
            },
            {
                "time": "2026-09-03T02:00:00.123456789-05:00",
                "short_id": "6033584d",
                "paths": ["/all"],
            },
            {
                "time": "2026-09-03T05:00:00.123456789+00:00",
                "short_id": "59cd359e",
                "paths": ["/old"],
            },
            {
                "time": "2026-09-02T20:00:00.123456789-05:00",
                "short_id": "c8b82c94",
                "paths": ["/old"],
            },
        ]
    )
    monkeypatch.setattr(collect, "run", fake_run({"restic": cp(snaps)}))
    t = collect.tile_backup_snapshot(base_cfg(tmp_path), NOW)
    assert "6033584d" in t["summary"]
    assert "16e29ff5" not in t["summary"]
    assert t["detail"]["short_id"] == "6033584d"
    assert t["detail"]["groups"] == 4
    assert abs(t["detail"]["age_h"] - 1.0) < 0.05


def test_snapshot_30h_is_warn(monkeypatch, tmp_path):
    # 30h sits inside the warn band (26h <= age < 50h), distinguishing the
    # 26h ok/warn boundary from the 50h warn/fail boundary pinned below.
    snap = json.dumps([{"time": "2026-09-02T02:00:00Z", "short_id": "b", "paths": []}])
    monkeypatch.setattr(collect, "run", fake_run({"restic": cp(snap)}))
    assert collect.tile_backup_snapshot(base_cfg(tmp_path), NOW)["status"] == "warn"


def test_snapshot_50h_is_fail(monkeypatch, tmp_path):
    snap = json.dumps([{"time": "2026-08-31T20:00:00Z", "short_id": "a", "paths": []}])
    monkeypatch.setattr(collect, "run", fake_run({"restic": cp(snap)}))
    assert collect.tile_backup_snapshot(base_cfg(tmp_path), NOW)["status"] == "fail"


def test_snapshot_missing_binary_is_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(collect, "run", fake_run({}))
    assert collect.tile_backup_snapshot(base_cfg(tmp_path), NOW)["status"] == "unknown"


def test_snapshot_empty_list_is_fail(monkeypatch, tmp_path):
    # restic returning an empty JSON array (repo exists, zero snapshots)
    # is a distinct case from a missing/erroring binary -- pins the
    # `if not snaps:` branch on its own so a "fail" -> "ok" swap there is
    # caught rather than silently going green.
    monkeypatch.setattr(collect, "run", fake_run({"restic": cp("[]\n")}))
    t = collect.tile_backup_snapshot(base_cfg(tmp_path), NOW)
    assert t["status"] == "fail" and "no snapshot" in t["summary"]


def test_snapshot_restic_env_has_all_restic_keys(monkeypatch, tmp_path):
    captured = {}

    def _run(argv, timeout=10.0, env=None):
        captured["argv"] = argv
        captured["env"] = env
        return cp(
            json.dumps([{"time": "2026-09-03T02:00:00Z", "short_id": "x", "paths": []}])
        )

    monkeypatch.setattr(collect, "run", _run)
    collect.tile_backup_snapshot(base_cfg(tmp_path), NOW)
    assert captured["argv"][0] == "restic"
    env = captured["env"]
    assert env["RESTIC_REPOSITORY"] == "/var/lib/restic/core"
    assert env["RESTIC_PASSWORD_FILE"] == "/pw"
    # ProtectHome=read-only on helm-collect.service leaves restic with no
    # writable cache unless this is set (Major fix, plan Task 0).
    assert env["RESTIC_CACHE_DIR"] == "/var/lib/helm-cache"


def test_restic_snapshots_uses_no_lock(monkeypatch, tmp_path):
    # F5: the sandbox's ReadWritePaths only cover /var/lib/helm and
    # /var/lib/helm-cache, not the restic repository -- `snapshots` is a
    # pure read and must pass --no-lock or it dies after a 60s timeout
    # waiting for a lock it can never take.
    seen = {}

    def _run(argv, timeout=10.0, env=None):
        seen["argv"] = argv
        return cp(
            json.dumps([{"time": "2026-09-03T02:00:00Z", "short_id": "x", "paths": []}])
        )

    monkeypatch.setattr(collect, "run", _run)
    collect.tile_backup_snapshot(base_cfg(tmp_path), NOW)
    assert "--no-lock" in seen["argv"]
    assert seen["argv"][:2] == ["restic", "snapshots"]


def test_parity_ok_line(monkeypatch, tmp_path):
    line = json.dumps(
        {
            "MESSAGE": "proton-backup-push: OK snapshots=1 remote=1",
            "__REALTIME_TIMESTAMP": str(int(NOW.timestamp() * 1e6) - 3600 * 1e6),
        }
    )
    monkeypatch.setattr(
        collect,
        "run",
        fake_run({"journalctl": cp(line + "\n"), "systemctl": _unit_show("success")}),
    )
    assert collect.tile_backup_parity(base_cfg(tmp_path), NOW)["status"] == "ok"


def test_parity_ok_30h_is_warn(monkeypatch, tmp_path):
    # 30h sits past the 26h ok/warn boundary -- pins that `age_h < 26` is
    # the actual guard (a `< 1e9` mutation there would wrongly stay "ok").
    line = json.dumps(
        {
            "MESSAGE": "proton-backup-push: OK snapshots=1 remote=1",
            "__REALTIME_TIMESTAMP": str(
                int(NOW.timestamp() * 1e6) - int(30 * 3600 * 1e6)
            ),
        }
    )
    monkeypatch.setattr(
        collect,
        "run",
        fake_run({"journalctl": cp(line + "\n"), "systemctl": _unit_show("success")}),
    )
    t = collect.tile_backup_parity(base_cfg(tmp_path), NOW)
    assert t["status"] == "warn"


def test_parity_no_matching_message_is_fail(monkeypatch, tmp_path):
    # Journal has entries, but none match the proton-backup-push line format
    # -- distinct from an empty journal, and pins `last is None` -> "fail"
    # (a "fail" -> "ok" swap there is a silent false "healthy").
    line = json.dumps(
        {
            "MESSAGE": "some unrelated user unit log line",
            "__REALTIME_TIMESTAMP": str(int(NOW.timestamp() * 1e6)),
        }
    )
    monkeypatch.setattr(
        collect,
        "run",
        fake_run({"journalctl": cp(line + "\n"), "systemctl": _unit_show("success")}),
    )
    t = collect.tile_backup_parity(base_cfg(tmp_path), NOW)
    assert t["status"] == "fail" and "no proton-backup-push result" in t["summary"]


def test_parity_fail_line(monkeypatch, tmp_path):
    line = json.dumps(
        {
            "MESSAGE": "proton-backup-push: FAIL parity",
            "__REALTIME_TIMESTAMP": str(int(NOW.timestamp() * 1e6)),
        }
    )
    monkeypatch.setattr(
        collect,
        "run",
        fake_run({"journalctl": cp(line + "\n"), "systemctl": _unit_show("success")}),
    )
    assert collect.tile_backup_parity(base_cfg(tmp_path), NOW)["status"] == "fail"


def test_parity_unit_failure_beats_a_stale_ok_line(monkeypatch, tmp_path):
    # The unit's own Result (exit-code/1) must gate the tile before any
    # journal scan: a stale "OK" log line cannot hide a failed push. The fake
    # pins BOTH the unit name (keyed on "proton-drive-push.service") and the
    # --user scope, so mutating the tile to query a different unit or scope
    # turns this red rather than silently green.
    monkeypatch.setattr(
        collect,
        "run",
        systemctl_fake(
            {"proton-drive-push.service": _unit_show("exit-code", "1")}, scope="user"
        ),
    )
    t = collect.tile_backup_parity(base_cfg(tmp_path), NOW)
    assert t["status"] == "fail" and "exit-code" in t["summary"]


def test_parity_unit_success_keeps_the_journal_verdict(monkeypatch, tmp_path):
    line = json.dumps(
        {
            "MESSAGE": "proton-backup-push: OK snapshots=1 remote=1",
            "__REALTIME_TIMESTAMP": str(int(NOW.timestamp() * 1e6) - 3600 * 1e6),
        }
    )
    sc = systemctl_fake(
        {"proton-drive-push.service": _unit_show("success")}, scope="user"
    )

    def _run(argv, timeout=10.0, env=None):
        if argv[0] == "journalctl":
            return cp(line + "\n")
        return sc(argv, timeout, env)

    monkeypatch.setattr(collect, "run", _run)
    assert collect.tile_backup_parity(base_cfg(tmp_path), NOW)["status"] == "ok"


def test_parity_nonzero_exit_status_is_fail(monkeypatch, tmp_path):
    # Result=success with a non-zero ExecMainStatus must still red the tile:
    # the `status != "0"` half of tile_backup_parity's guard is the only thing
    # between a unit whose last journal line was OK and a "success" verdict.
    # The fake composes the journal answer with a scope-pinned systemctl answer
    # (exactly as test_parity_unit_success_keeps_the_journal_verdict does), so
    # dropping `or status != "0"` turns this red rather than silently green.
    line = json.dumps(
        {
            "MESSAGE": "proton-backup-push: OK snapshots=1 remote=1",
            "__REALTIME_TIMESTAMP": str(int(NOW.timestamp() * 1e6) - 3600 * 1e6),
        }
    )
    sc = systemctl_fake(
        {"proton-drive-push.service": _unit_show("success", "1")}, scope="user"
    )

    def _run(argv, timeout=10.0, env=None):
        if argv[0] == "journalctl":
            return cp(line + "\n")
        return sc(argv, timeout, env)

    monkeypatch.setattr(collect, "run", _run)
    t = collect.tile_backup_parity(base_cfg(tmp_path), NOW)
    assert t["status"] == "fail"
    assert t["detail"]["exec_main_status"] == "1"


def test_parity_red_summary_names_result_and_status(monkeypatch, tmp_path):
    # R3rb: a red tile whose unit Result=success but ExecMainStatus is non-zero
    # must name BOTH in its summary, not just "last result success" -- the
    # exit status is the only thing distinguishing "fine" from "silently
    # killed". Stub _unit_result directly (the early return never reaches
    # run/journalctl), so the summary string is the sole thing under test.
    monkeypatch.setattr(
        collect, "_unit_result", lambda scope_args, unit: ("success", "1")
    )
    t = collect.tile_backup_parity(base_cfg(tmp_path), NOW)
    assert t["status"] == "fail"
    assert t["summary"] == "proton-drive-push.service last result success, status 1"


def test_parity_red_summary_names_failed_result_with_zero_status(monkeypatch, tmp_path):
    # The same early-return fires when Result=failed with a zero status; the
    # summary must name both too, so the operator sees the failed result even
    # when the exit status happened to be 0.
    monkeypatch.setattr(
        collect, "_unit_result", lambda scope_args, unit: ("failed", "0")
    )
    t = collect.tile_backup_parity(base_cfg(tmp_path), NOW)
    assert t["status"] == "fail"
    assert t["summary"] == "proton-drive-push.service last result failed, status 0"


def test_timers_service_timeout_is_fail(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    cfg["timers_user"] = ["helm-flake-check.timer"]
    monkeypatch.setattr(
        collect,
        "run",
        systemctl_fake(
            {
                "helm-flake-check.timer": _unit_show("success"),
                "helm-flake-check.service": _unit_show(
                    "timeout", "0", active="failed", nxt=""
                ),
            },
            scope="user",
        ),
    )
    t = collect.tile_timers(cfg, NOW)
    assert t["status"] == "fail"
    # An armed timer whose service failed must be named under the "failed:"
    # prefix, never "not armed:" (the timer IS armed; only its service died).
    assert t["summary"] == "failed: helm-flake-check.service: timeout"


def test_timers_reports_unarmed_and_failed_together(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    cfg["timers_user"] = ["a.timer", "b.timer"]
    cfg["timers_system"] = []
    monkeypatch.setattr(
        collect,
        "run",
        systemctl_fake(
            {
                "a.timer": _unit_show("success"),
                "a.service": _unit_show("timeout", "0", active="failed", nxt=""),
                "b.timer": _unit_show("success", active="inactive", nxt=""),
                "b.service": _unit_show("success"),
            },
            scope="user",
        ),
    )
    t = collect.tile_timers(cfg, NOW)
    assert t["status"] == "fail"
    assert t["summary"] == "not armed: b.timer; failed: a.service: timeout"


def test_timers_system_service_oom_is_fail(monkeypatch, tmp_path):
    # System-scope half of tile_timers: the sibling .service of a
    # timers_system entry must be checked with _unit_result([], service) (no
    # --user). A nightly restic backup OOM-killed shows red even though the
    # timer itself is armed -- the exact case the branch exists to surface.
    cfg = dict(base_cfg(tmp_path), timers_system=["restic-backups-core-local.timer"])
    monkeypatch.setattr(
        collect,
        "run",
        systemctl_fake(
            {
                "restic-backups-core-local.timer": _unit_show("success"),
                "restic-backups-core-local.service": _unit_show("oom-kill", "0"),
            },
            scope="system",
        ),
    )
    t = collect.tile_timers(cfg, NOW)
    assert t["status"] == "fail"
    assert "restic-backups-core-local.service" in t["summary"]
    assert "oom-kill" in t["summary"]


def test_timers_inactive_is_fail(monkeypatch, tmp_path):
    cfg = dict(base_cfg(tmp_path), timers_system=["a.timer"], timers_user=["b.timer"])
    monkeypatch.setattr(
        collect,
        "run",
        systemctl_fake(
            {
                "a.timer": cp(
                    "ActiveState=active\nNextElapseUSecRealtime=Thu 2026-09-04 00:00:00 UTC\n"
                ),
                "b.timer": cp("ActiveState=inactive\nNextElapseUSecRealtime=\n"),
            }
        ),
    )
    t = collect.tile_timers(cfg, NOW)
    assert t["status"] == "fail" and "b.timer" in t["summary"]
    # One unarmed timer with no failed service: summary carries the "not
    # armed:" prefix and must not mention "failed:".
    assert t["summary"].startswith("not armed: ") and "failed" not in t["summary"]


def test_timers_monotonic_only_is_armed(monkeypatch, tmp_path):
    # OnUnitActiveSec=/OnBootSec=/OnActiveSec= timers (e.g. helm-collect.timer
    # itself) report a next-elapse only on the monotonic clock and always
    # leave NextElapseUSecRealtime empty, even while healthy.
    cfg = dict(base_cfg(tmp_path), timers_system=["helm-collect.timer"])
    monkeypatch.setattr(
        collect,
        "run",
        systemctl_fake(
            {
                "helm-collect.timer": cp(
                    "ActiveState=active\n"
                    "NextElapseUSecRealtime=\n"
                    "NextElapseUSecMonotonic=1d 15min\n"
                ),
            }
        ),
    )
    t = collect.tile_timers(cfg, NOW)
    assert t["status"] == "ok"


def test_timers_stopped_unit_is_fail(monkeypatch, tmp_path):
    # Real `systemctl show` output for a stopped/absent unit: ActiveState is
    # inactive, NextElapseUSecRealtime is empty, and NextElapseUSecMonotonic
    # is the literal string "infinity" (non-empty, != "0"). This pins the
    # ActiveState guard on its own: without it, "infinity" would read as an
    # armed monotonic next-elapse and this fixture would go green.
    cfg = dict(base_cfg(tmp_path), timers_user=["proton-drive-push.timer"])
    monkeypatch.setattr(
        collect,
        "run",
        systemctl_fake(
            {
                "proton-drive-push.timer": cp(
                    "ActiveState=inactive\n"
                    "NextElapseUSecRealtime=\n"
                    "NextElapseUSecMonotonic=infinity\n"
                ),
            }
        ),
    )
    t = collect.tile_timers(cfg, NOW)
    assert t["status"] == "fail" and "proton-drive-push.timer" in t["summary"]


def test_timers_monotonic_zero_is_fail(monkeypatch, tmp_path):
    # ActiveState=active with an empty realtime field and a *literal* "0"
    # monotonic field (distinct from "infinity" or a real duration) must
    # read as unarmed -- pins the `monotonic != "0"` guard on its own.
    cfg = dict(base_cfg(tmp_path), timers_system=["weird.timer"])
    monkeypatch.setattr(
        collect,
        "run",
        systemctl_fake(
            {
                "weird.timer": cp(
                    "ActiveState=active\nNextElapseUSecRealtime=\nNextElapseUSecMonotonic=0\n"
                ),
            }
        ),
    )
    t = collect.tile_timers(cfg, NOW)
    assert t["status"] == "fail" and "weird.timer" in t["summary"]


def test_doctor_warn_and_fail(monkeypatch, tmp_path):
    monkeypatch.setattr(
        collect,
        "run",
        fake_run({"basket": cp("PASS swap off\nWARN vsock module absent\n")}),
    )
    assert collect.tile_basket_doctor(base_cfg(tmp_path), NOW)["status"] == "warn"
    monkeypatch.setattr(
        collect,
        "run",
        fake_run(
            {"basket": cp("PASS swap off\nFAIL pcscd not running\n", returncode=1)}
        ),
    )
    assert collect.tile_basket_doctor(base_cfg(tmp_path), NOW)["status"] == "fail"
    monkeypatch.setattr(collect, "run", fake_run({"basket": cp("", returncode=1)}))
    assert collect.tile_basket_doctor(base_cfg(tmp_path), NOW)["status"] == "fail"


def test_broker_counts_last_24h(tmp_path):
    audit = tmp_path / "audit.jsonl"
    ts = NOW.timestamp()
    rows = [
        {
            "ts": ts - 100,
            "instance": "cowork",
            "host": "api.anthropic.com",
            "verdict": "allow",
        },
        {
            "ts": ts - 200,
            "instance": "cowork",
            "host": "evil.example",
            "verdict": "deny",
        },
        {
            "ts": ts - 200000,
            "instance": "cowork",
            "host": "old.example",
            "verdict": "deny",
        },
    ]
    audit.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    cfg = dict(
        base_cfg(tmp_path),
        broker_audit_paths=[{"instance": "cowork", "path": str(audit)}],
    )
    t = collect.tile_broker(cfg, NOW)
    d = t["detail"]["cowork"]
    assert (
        d["allow"] == 1 and d["deny"] == 1 and d["top_denied"][0][0] == "evil.example"
    )


def test_broker_nonexistent_path_is_unknown(tmp_path):
    # A configured audit path that does not exist (e.g. a broker instance
    # never started) must not read as "0 allow, 0 deny" -- it must surface
    # as tile "unknown" with a per-instance "error" marker so the operator
    # can tell "quiet" from "broken".
    cfg = dict(
        base_cfg(tmp_path),
        broker_audit_paths=[
            {"instance": "cowork", "path": str(tmp_path / "does-not-exist.jsonl")}
        ],
    )
    t = collect.tile_broker(cfg, NOW)
    assert t["status"] == "unknown"
    assert t["detail"]["cowork"] == "error"


def test_broker_tile_unknown_when_no_instances(tmp_path):
    # F20: an empty broker_audit_paths (no services.egress-broker.instances
    # declared, or brokerInstances = []) must not read as "0 allow, 0 deny"
    # -- that is indistinguishable from a quiet-but-healthy broker.
    cfg = dict(base_cfg(tmp_path), broker_audit_paths=[])
    t = collect.tile_broker(cfg, NOW)
    assert t["status"] == "unknown"
    assert "no broker instance" in t["summary"]


def test_gpu_parses_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(
        collect,
        "run",
        fake_run(
            {"nvidia-smi": cp("NVIDIA GeForce RTX 5090, 2, 1428, 32607, 39, 36.86\n")}
        ),
    )
    t = collect.tile_gpu(base_cfg(tmp_path), NOW)
    assert t["status"] == "ok" and t["detail"]["memory_used_mib"] == 1428


def test_gpu_uses_configured_nvidia_smi_bin_and_exact_argv(monkeypatch, tmp_path):
    # Blocker fix: a systemd --user unit's PATH lacks
    # /run/current-system/sw/bin, where nvidia-smi actually lives -- the
    # collector must invoke the configured absolute path as argv[0], and
    # every one of the six --query-gpu fields must survive verbatim.
    calls = []

    def _run(argv, timeout=10.0, env=None):
        calls.append(argv)
        return cp("NVIDIA GeForce RTX 5090, 2, 1428, 32607, 39, 36.86\n")

    monkeypatch.setattr(collect, "run", _run)
    cfg = dict(
        base_cfg(tmp_path), nvidia_smi_bin="/run/current-system/sw/bin/nvidia-smi"
    )
    collect.tile_gpu(cfg, NOW)
    assert calls[0] == [
        "/run/current-system/sw/bin/nvidia-smi",
        "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ]


def test_gpu_falls_back_to_bare_nvidia_smi(monkeypatch, tmp_path):
    calls = []

    def _run(argv, timeout=10.0, env=None):
        calls.append(argv)
        raise FileNotFoundError(argv[0])

    monkeypatch.setattr(collect, "run", _run)
    t = collect.tile_gpu(base_cfg(tmp_path), NOW)
    assert calls[0][0] == "nvidia-smi" and t["status"] == "unknown"


def test_gpu_returncode_nonzero_is_fail(monkeypatch, tmp_path):
    monkeypatch.setattr(
        collect,
        "run",
        fake_run({"nvidia-smi": cp("", returncode=1, stderr="No devices found")}),
    )
    t = collect.tile_gpu(base_cfg(tmp_path), NOW)
    assert t["status"] == "fail"


def test_gpu_hot_only_is_warn(monkeypatch, tmp_path):
    # temp 88 >= 85 trips the rule on its own; mem ~3% stays well under 95%.
    monkeypatch.setattr(
        collect, "run", fake_run({"nvidia-smi": cp("X, 90, 1000, 32607, 88, 400\n")})
    )
    assert collect.tile_gpu(base_cfg(tmp_path), NOW)["status"] == "warn"


def test_gpu_mem_full_only_is_warn(monkeypatch, tmp_path):
    # mem 31000/32607 ~= 95.07% >= 95% trips the rule on its own; temp 39 stays cool.
    monkeypatch.setattr(
        collect, "run", fake_run({"nvidia-smi": cp("X, 90, 31000, 32607, 39, 400\n")})
    )
    assert collect.tile_gpu(base_cfg(tmp_path), NOW)["status"] == "warn"


def test_host_swap_present_is_fail(monkeypatch, tmp_path):
    monkeypatch.setattr(
        collect,
        "read_text",
        lambda p: {
            "/proc/loadavg": "1.0 1.0 1.0 1/2 3",
            "/proc/meminfo": "MemTotal: 100 kB\nMemAvailable: 50 kB\n",
            "/proc/swaps": "Filename Type Size Used Priority\n/dev/sda2 partition 1 0 -2\n",
        }[p],
    )
    monkeypatch.setattr(collect, "disk_free_fraction", lambda path: 0.5)
    assert collect.tile_host(base_cfg(tmp_path), NOW)["status"] == "fail"


def _no_swap_read_text(p):
    return {
        "/proc/loadavg": "1.0 1.0 1.0 1/2 3",
        "/proc/meminfo": "MemTotal: 100 kB\nMemAvailable: 50 kB\n",
        # header line only: no swap device configured.
        "/proc/swaps": "Filename Type Size Used Priority\n",
    }[p]


def test_host_disk_thresholds_no_swap(monkeypatch, tmp_path):
    monkeypatch.setattr(collect, "read_text", _no_swap_read_text)

    monkeypatch.setattr(collect, "disk_free_fraction", lambda path: 0.5)
    assert collect.tile_host(base_cfg(tmp_path), NOW)["status"] == "ok"

    monkeypatch.setattr(collect, "disk_free_fraction", lambda path: 0.10)
    assert collect.tile_host(base_cfg(tmp_path), NOW)["status"] == "warn"

    monkeypatch.setattr(collect, "disk_free_fraction", lambda path: 0.02)
    assert collect.tile_host(base_cfg(tmp_path), NOW)["status"] == "fail"


def test_drift_branches(monkeypatch, tmp_path):
    def table(live_rc, live_out, head, porcelain):
        def _run(argv, timeout=10.0, env=None):
            if argv[0] == "nixos-version":
                return cp(
                    live_out,
                    live_rc,
                    ""
                    if live_rc == 0
                    else "nixos-version: configuration revision is unknown",
                )
            if argv[:2] == ["git", "-C"] and "rev-parse" in argv:
                return cp(head + "\n")
            if argv[:2] == ["git", "-C"] and "status" in argv:
                return cp(porcelain)
            if argv[:2] == ["git", "-C"] and "diff" in argv:
                return cp("", 1)
            raise FileNotFoundError(argv[0])

        return _run

    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", table(1, "", "abc", ""))
    no_rev = collect.tile_drift(cfg, NOW)
    # Pins the exit!=0 branch's message, not just its status -- a
    # "fail" -> "ok" swap on this branch is caught by the status
    # assertion below, but the summary must also name the actual defect
    # (no configuration revision) so an operator reading the tile knows
    # what to fix, distinct from the live != HEAD "fail" case further down.
    assert no_rev["status"] == "fail" and "configuration revision" in no_rev["summary"]
    monkeypatch.setattr(collect, "run", table(0, "abc\n", "abc", ""))
    assert collect.tile_drift(cfg, NOW)["status"] == "ok"
    monkeypatch.setattr(collect, "run", table(0, "abc-dirty\n", "abc", ""))
    assert collect.tile_drift(cfg, NOW)["status"] == "warn"
    monkeypatch.setattr(collect, "run", table(0, "abc\n", "abc", " M x\n"))
    assert collect.tile_drift(cfg, NOW)["status"] == "warn"
    monkeypatch.setattr(collect, "run", table(0, "dirty\n", "abc", ""))
    assert collect.tile_drift(cfg, NOW)["status"] == "warn"
    monkeypatch.setattr(collect, "run", table(0, "def\n", "abc", ""))
    assert collect.tile_drift(cfg, NOW)["status"] == "fail"


def test_drift_uses_configured_nixos_version_bin(monkeypatch, tmp_path):
    # Blocker fix: a systemd --user unit's PATH lacks
    # /run/current-system/sw/bin, where nixos-version actually lives -- the
    # collector must invoke the configured absolute path as argv[0].
    calls = []

    def _run(argv, timeout=10.0, env=None):
        calls.append(argv)
        if argv[0] == "/run/current-system/sw/bin/nixos-version":
            return cp("abc\n")
        if argv[:2] == ["git", "-C"] and "rev-parse" in argv:
            return cp("abc\n")
        if argv[:2] == ["git", "-C"] and "status" in argv:
            return cp("")
        raise FileNotFoundError(argv[0])

    monkeypatch.setattr(collect, "run", _run)
    cfg = dict(
        base_cfg(tmp_path),
        nixos_version_bin="/run/current-system/sw/bin/nixos-version",
    )
    t = collect.tile_drift(cfg, NOW)
    assert calls[0] == [
        "/run/current-system/sw/bin/nixos-version",
        "--configuration-revision",
    ]
    assert t["status"] == "ok"


def test_drift_falls_back_to_bare_nixos_version(monkeypatch, tmp_path):
    calls = []

    def _run(argv, timeout=10.0, env=None):
        calls.append(argv)
        raise FileNotFoundError(argv[0])

    monkeypatch.setattr(collect, "run", _run)
    t = collect.tile_drift(base_cfg(tmp_path), NOW)
    assert calls[0][0] == "nixos-version" and t["status"] == "unknown"


def test_flake_check_fresh_stale_missing(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table("abc", "abc", set()))
    f = pathlib.Path(cfg["flake_check_file"])
    assert collect.tile_flake_check(cfg, NOW)["status"] == "fail"  # missing
    f.write_text(
        json.dumps(
            {
                "rev": "abc",
                "ok": True,
                "exit": 0,
                "started": "2026-09-03T03:00:00Z",
                "duration_s": 100,
                "log_tail": "",
            }
        )
    )
    assert collect.tile_flake_check(cfg, NOW)["status"] == "ok"
    f.write_text(
        json.dumps(
            {
                "rev": "abc",
                "ok": True,
                "exit": 0,
                "started": "2026-08-30T03:00:00Z",
                "duration_s": 100,
                "log_tail": "",
            }
        )
    )
    assert collect.tile_flake_check(cfg, NOW)["status"] == "warn"
    f.write_text(
        json.dumps(
            {
                "rev": "abc",
                "ok": False,
                "exit": 1,
                "started": "2026-09-03T03:00:00Z",
                "duration_s": 100,
                "log_tail": "boom",
            }
        )
    )
    assert collect.tile_flake_check(cfg, NOW)["status"] == "fail"
    f.write_text(
        json.dumps(
            {
                "rev": "def",
                "ok": True,
                "exit": 0,
                "started": "2026-09-03T03:00:00Z",
                "duration_s": 100,
                "log_tail": "",
            }
        )
    )
    behind = collect.tile_flake_check(cfg, NOW)
    assert (
        behind["status"] == "warn" and "def" in behind["summary"]
    )  # behind: rev != HEAD "abc"


def test_flake_check_green_when_observation_covers_head_exactly(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_H, set()))
    obs(tmp_path, REV_H, True, "2026-09-03T04:00:00Z")
    t = collect.tile_flake_check(cfg, NOW)
    assert (
        t["status"] == "ok"
        and "covers HEAD" in t["summary"]
        and REV_H[:12] in t["summary"]
    )


def test_flake_check_green_when_observation_is_docs_equivalent_to_head(
    monkeypatch, tmp_path
):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(
        collect, "run", git_table(REV_H, REV_L, {frozenset({REV_O, REV_H})})
    )
    obs(tmp_path, REV_O, True, "2026-09-03T04:00:00Z")
    t = collect.tile_flake_check(cfg, NOW)
    assert t["status"] == "ok" and "covers HEAD" in t["summary"]


def test_flake_check_red_when_newest_covering_observation_failed(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_H, set()))
    obs(tmp_path, REV_H, True, "2026-09-03T02:00:00Z")
    obs(tmp_path, REV_H, False, "2026-09-03T04:00:00Z", src="seat-integrate")
    t = collect.tile_flake_check(cfg, NOW)
    assert t["status"] == "fail" and "seat-integrate" in t["summary"]


def test_flake_check_amber_when_only_live_is_covered(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_L, set()))
    obs(tmp_path, REV_L, True, "2026-09-03T04:00:00Z")
    t = collect.tile_flake_check(cfg, NOW)
    assert (
        t["status"] == "warn"
        and "covers the live system" in t["summary"]
        and "unchecked" in t["summary"]
    )


def test_flake_check_amber_when_covering_observation_is_old(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_H, set()))
    obs(tmp_path, REV_H, True, "2026-08-30T04:00:00Z")
    t = collect.tile_flake_check(cfg, NOW)
    assert t["status"] == "warn" and "old" in t["summary"]


def test_flake_check_falls_back_to_file_when_store_is_empty(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table("abc", "abc", set()))
    pathlib.Path(cfg["flake_check_file"]).write_text(
        json.dumps(
            {
                "rev": "abc",
                "ok": True,
                "exit": 0,
                "started": "2026-09-03T03:00:00Z",
                "duration_s": 100,
                "log_tail": "",
            }
        )
    )
    assert collect.tile_flake_check(cfg, NOW)["status"] == "ok"


def test_drift_docs_only_ahead_is_ok_and_named(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(
        collect, "run", git_table(REV_H, REV_L, {frozenset({REV_L, REV_H})})
    )
    t = collect.tile_drift(cfg, NOW)
    assert (
        t["status"] == "ok"
        and "except docs" in t["summary"]
        and t["detail"]["docs_only_ahead"] is True
    )
    monkeypatch.setattr(
        collect,
        "run",
        git_table(REV_H, REV_L, {frozenset({REV_L, REV_H})}, porcelain=" M x\n"),
    )
    assert collect.tile_drift(cfg, NOW)["status"] == "warn"
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_L, set()))
    assert collect.tile_drift(cfg, NOW)["status"] == "fail"


def test_collect_all_has_every_tile_and_never_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(collect, "run", fake_run({}))
    monkeypatch.setattr(
        collect, "read_text", lambda p: (_ for _ in ()).throw(OSError(p))
    )
    st = collect.collect_all(base_cfg(tmp_path), NOW)
    names = {t["name"] for t in st["tiles"]}
    assert names == {
        "backup-snapshot",
        "backup-parity",
        "timers",
        "basket-doctor",
        "broker",
        "gpu",
        "host",
        "drift",
        "flake-check",
    }
    assert all(t["status"] in {"ok", "warn", "fail", "unknown"} for t in st["tiles"])


def test_collect_all_envelope_fields(monkeypatch, tmp_path):
    # Pins the envelope fields around the tile list -- a dashboard renderer
    # or a monitoring scrape reads these directly, so silently dropping one
    # (or leaving a tile's checked_at stale from a prior collection) must
    # fail a test, not just look fine in the browser.
    monkeypatch.setattr(collect, "run", fake_run({}))
    monkeypatch.setattr(
        collect, "read_text", lambda p: (_ for _ in ()).throw(OSError(p))
    )
    cfg = base_cfg(tmp_path)
    st = collect.collect_all(cfg, NOW)
    assert st["generated_at"] == NOW.isoformat()
    assert st["interval_s"] == cfg["interval_s"]
    assert isinstance(st["hostname"], str) and st["hostname"]
    assert st["tiles"] and all(t["checked_at"] == NOW.isoformat() for t in st["tiles"])


def test_write_atomic_mode(tmp_path):
    p = tmp_path / "status.json"
    collect.write_atomic(p, "{}")
    assert (
        p.read_text() == "{}"
        and (p.stat().st_mode & 0o777) == 0o640
        and not list(tmp_path.glob("*.tmp"))
    )


def test_write_atomic_mode_survives_restrictive_umask(tmp_path):
    # Major fix: os.open's mode argument is masked by the process umask, so
    # without an explicit os.fchmod, a restrictive umask (e.g. the operator
    # user's real 0o077) silently drops the group-read bit that
    # static-web-server's SupplementaryGroups=helm relies on.
    p = tmp_path / "status.json"
    old = os.umask(0o077)
    try:
        collect.write_atomic(p, "{}")
    finally:
        os.umask(old)
    assert (p.stat().st_mode & 0o777) == 0o640


def _status(tiles):
    return {
        "generated_at": NOW.isoformat(),
        "hostname": "core",
        "interval_s": 300,
        "tiles": tiles,
    }


def _tile(name, status, summary, detail=None):
    return {
        "name": name,
        "status": status,
        "summary": summary,
        "detail": detail or {},
        "checked_at": NOW.isoformat(),
    }


def test_render_has_every_tile_and_no_external_refs():
    html = collect.render_html(
        _status([_tile("gpu", "ok", "RTX 5090"), _tile("broker", "ok", "x")]), NOW
    )
    assert "gpu" in html and "RTX 5090" in html and 'class="tile ok"' in html
    assert "<script" not in html and "src=" not in html and 'href="http' not in html


def test_render_escapes_adversarial_strings():
    bad = '<script>alert(1)</script>"><img src=x>'
    html = collect.render_html(
        _status(
            [
                _tile(
                    "broker",
                    "ok",
                    bad,
                    {"cowork": {"top_denied": [[bad, 3]]}},
                )
            ]
        ),
        NOW,
    )
    assert bad not in html and "&lt;script&gt;" in html and "src=" not in html


def test_page_has_no_stale_badge():
    # F9: the badge was computed at collection time, describing a page the
    # collector had just generated -- a viewer could never see it apply to
    # the actual page in front of them. Removed outright: the "timers" tile
    # already audits helm-collect.timer for exactly this.
    old = _status([_tile("gpu", "ok", "x")])
    old["generated_at"] = (NOW - dt.timedelta(seconds=700)).isoformat()
    html = collect.render_html(old, NOW)
    assert "collector stale" not in html
    assert ".stale" not in html
    assert "generated" in html


def test_render_text_lists_status_per_tile():
    txt = collect.render_text(_status([_tile("gpu", "warn", "hot")]))
    assert "WARN" in txt and "gpu" in txt and "hot" in txt


def _status_of(names_to_status, now):
    return {
        "generated_at": now.isoformat(),
        "hostname": "h",
        "interval_s": 300,
        "tiles": [
            {
                "name": n,
                "status": s,
                "summary": "",
                "detail": {},
                "checked_at": now.isoformat(),
            }
            for n, s in names_to_status.items()
        ],
    }


def test_record_status_writes_on_change_and_heartbeat_only(tmp_path):
    cfg = base_cfg(tmp_path)
    t0 = NOW
    assert (
        collect.record_status(cfg, _status_of({"drift": "ok"}, t0), t0)["reason"]
        == "change"
    )
    assert (
        collect.record_status(
            cfg, _status_of({"drift": "ok"}, t0), t0 + dt.timedelta(minutes=5)
        )
        is None
    )
    assert (
        collect.record_status(
            cfg, _status_of({"drift": "fail"}, t0), t0 + dt.timedelta(minutes=10)
        )["reason"]
        == "change"
    )
    assert (
        collect.record_status(
            cfg, _status_of({"drift": "fail"}, t0), t0 + dt.timedelta(minutes=75)
        )["reason"]
        == "heartbeat"
    )
    rows = [
        json.loads(line)
        for line in (tmp_path / "evidence" / "helm-status.jsonl")
        .read_text()
        .splitlines()
    ]
    assert [r["reason"] for r in rows] == ["change", "change", "heartbeat"] and rows[
        -1
    ]["tiles"] == {"drift": "fail"}
    # Pin the stream file's mode: the docstring on _append_status_row claims
    # "same discipline as pkgs/evidence", where 0o640 is load-bearing for the
    # static-web-server group; a 0o644 mutation here must not go unnoticed.
    assert (
        stat.S_IMODE((tmp_path / "evidence" / "helm-status.jsonl").stat().st_mode)
        == 0o640
    )


def _opener():
    """The name of the function that called an open wrapper: frame 0 is this
    helper, frame 1 is the wrapper, frame 2 is the opener itself."""
    return sys._getframe(2).f_code.co_name


def _record_openers(monkeypatch, evidence_dir):
    """Wrap os.open and builtins.open so any write-mode open of a path under
    `evidence_dir` records the name of the function that performed it. Returns
    the set of recorded names (module-qualified for the evidence writers)."""
    openers = set()

    def _wrap_os_open(orig):
        def wrapper(file, flags, *args, **kwargs):
            if str(file).startswith(evidence_dir) and flags & (
                os.O_WRONLY | os.O_RDWR | os.O_APPEND
            ):
                openers.add(_opener())
            return orig(file, flags, *args, **kwargs)

        return wrapper

    def _wrap_open(orig):
        def wrapper(file, mode="r", *args, **kwargs):
            if str(file).startswith(evidence_dir) and any(c in mode for c in "wax+"):
                openers.add(_opener())
            return orig(file, mode, *args, **kwargs)

        return wrapper

    monkeypatch.setattr(os, "open", _wrap_os_open(os.open))
    monkeypatch.setattr(builtins, "open", _wrap_open(builtins.open))
    return openers


def test_record_status_writes_only_through_evidence_append(monkeypatch, tmp_path):
    # The store row must be opened only by evidence.append (the evidence
    # module's writer), never by collect.py itself: a direct `os.open`/`open`
    # in `_append_status_row` would record `record_status` here and fail.
    cfg = base_cfg(tmp_path)
    openers = _record_openers(monkeypatch, cfg["evidence_dir"])
    collect.record_status(cfg, _status_of({"drift": "ok"}, NOW), NOW)
    assert openers == {"append"}


def test_record_status_refusal_is_logged_not_raised(monkeypatch, tmp_path, capsys):
    # A refused row (streams.StreamRefused is a ValueError) must be logged to
    # stderr and return None, never fail the collector run.
    cfg = base_cfg(tmp_path)

    def boom(store, stream, row, ts=None):
        raise ValueError("x")

    monkeypatch.setattr(evidence, "append", boom)
    assert collect.record_status(cfg, _status_of({"drift": "ok"}, NOW), NOW) is None
    assert "helm-collect: evidence: x" in capsys.readouterr().err


def test_annotate_since_uses_first_row_of_current_run(tmp_path):
    cfg = base_cfg(tmp_path)
    t0 = NOW
    # The drift tile flaps: ok@08:00 -> fail@09:00 -> ok@10:00 -> fail@11:00
    # -> fail@12:00. The current unbroken fail run starts at 11:00, NOT at
    # the older 09:00 fail, so "since" must skip back only as far as the
    # start of the CURRENT run -- the break on a non-matching verdict is the
    # only thing that makes the run "unbroken", and a flap proves it.
    collect.record_status(cfg, _status_of({"drift": "ok", "gpu": "ok"}, t0), t0)
    collect.record_status(
        cfg, _status_of({"drift": "fail", "gpu": "ok"}, t0), t0 + dt.timedelta(hours=1)
    )
    collect.record_status(
        cfg, _status_of({"drift": "ok", "gpu": "ok"}, t0), t0 + dt.timedelta(hours=2)
    )
    collect.record_status(
        cfg, _status_of({"drift": "fail", "gpu": "ok"}, t0), t0 + dt.timedelta(hours=3)
    )
    collect.record_status(
        cfg, _status_of({"drift": "fail", "gpu": "ok"}, t0), t0 + dt.timedelta(hours=4)
    )
    st = _status_of(
        {"drift": "fail", "gpu": "ok"}, t0 + dt.timedelta(hours=4, minutes=5)
    )
    collect.annotate_since(cfg, st)
    by = {t["name"]: t["since"] for t in st["tiles"]}
    assert by["drift"] == "2026-09-03T11:00:00Z" and by["gpu"] == "2026-09-03T08:00:00Z"


def test_annotate_since_without_history_uses_generated_at(tmp_path):
    st = _status_of({"drift": "ok"}, NOW)
    collect.annotate_since(base_cfg(tmp_path), st)
    assert st["tiles"][0]["since"] == NOW.isoformat()


def test_render_shows_verdict_word_since_and_local_time(monkeypatch, tmp_path):
    import time

    monkeypatch.setenv(
        "TZ", "CST6CDT,M3.2.0,M11.1.0"
    )  # POSIX rule: no zoneinfo needed in the sandbox
    time.tzset()
    try:
        st = _status_of({"drift": "fail"}, NOW)
        st["tiles"][0]["since"] = "2026-09-03T07:30:00Z"
        html_out = collect.render_html(st, NOW)
        assert '<h2>drift <span class="verdict">FAIL</span></h2>' in html_out
        assert (
            "since 02:30 CDT" in html_out
            and "generated 03:00:00 CDT" in html_out
            and "08:00:00Z" in html_out
        )
        assert "since" in collect.render_text(st)
        # every verdict word survives as text, colour is only reinforcement
        for word in ("OK", "WARN", "FAIL", "UNKNOWN"):
            st2 = _status_of({"a": "ok", "b": "warn", "c": "fail", "d": "unknown"}, NOW)
            assert f'<span class="verdict">{word}</span>' in collect.render_html(
                st2, NOW
            )
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()


def test_collect_all_document_has_schema_profile_and_generation(monkeypatch, tmp_path):
    monkeypatch.setattr(collect, "run", fake_run({}))
    monkeypatch.setattr(
        collect,
        "read_text",
        lambda p: (
            "gaming\n"
            if p.endswith("helm/profile")
            else (_ for _ in ()).throw(OSError(p))
        ),
    )
    monkeypatch.setattr(collect, "system_generation", lambda: "system-39-link")
    st = collect.collect_all(base_cfg(tmp_path), NOW)
    assert (
        st["schema"] == 1
        and st["active_profile"] == "gaming"
        and st["generation"] == "system-39-link"
    )


def test_render_handles_bad_timestamp_in_since(tmp_path):
    # A corrupted ts in the history store is copied verbatim into `since` by
    # annotate_since without raising; _local must absorb that ValueError so
    # render_html's unguarded per-tile loop does not crash the collector and
    # leave the page stale.
    st = _status_of({"drift": "fail"}, NOW)
    st["tiles"][0]["since"] = "not-a-time"
    html_out = collect.render_html(st, NOW)
    assert "not-a-time" in html_out


def test_print_does_not_write_history(monkeypatch, tmp_path):
    # `helm-status` is a read-only wrapper for `helm-collect --print`; a hand
    # run must not append verdict-history rows or heartbeat the stream (which
    # would interleave operator reads with the 5-minute collector).
    cfg = base_cfg(tmp_path)
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    monkeypatch.setattr(collect, "run", fake_run({}))
    monkeypatch.setattr(
        collect, "read_text", lambda p: (_ for _ in ()).throw(OSError(p))
    )
    assert collect.main(["--config", str(cfg_path), "--print"]) == 0
    assert not (tmp_path / "evidence" / "helm-status.jsonl").exists()


def test_write_path_records_history(monkeypatch, tmp_path):
    # The `--print` sibling proves a hand run writes nothing; this proves the
    # write path does record one verdict row. Unpinned (deleting the write
    # path's `record_status` call leaves every test green) until this test.
    cfg = base_cfg(tmp_path)
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    monkeypatch.setattr(collect, "run", fake_run({}))
    monkeypatch.setattr(
        collect, "read_text", lambda p: (_ for _ in ()).throw(OSError(p))
    )
    assert collect.main(["--config", str(cfg_path), "--out", str(out_dir)]) == 0
    rows_path = tmp_path / "evidence" / "helm-status.jsonl"
    assert rows_path.exists()
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["kind"] == "helm-status" and rows[0]["reason"] == "change"


def test_write_path_status_since_uses_z_suffix(monkeypatch, tmp_path):
    # E6b: record_status used to run AFTER annotate_since, so on the run where
    # a verdict first changed, "since" fell through to generated_at's
    # microsecond "+00:00" form while every later run reported the row's "…Z"
    # form — two timestamp shapes in one field. Every tile's since must be the
    # single "…Z" shape.
    import re

    cfg = base_cfg(tmp_path)
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    monkeypatch.setattr(collect, "run", fake_run({}))
    monkeypatch.setattr(
        collect, "read_text", lambda p: (_ for _ in ()).throw(OSError(p))
    )
    assert collect.main(["--config", str(cfg_path), "--out", str(out_dir)]) == 0
    st = json.loads((out_dir / "status.json").read_text())
    pat = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    assert st["tiles"]
    for t in st["tiles"]:
        assert pat.match(t["since"]), t
