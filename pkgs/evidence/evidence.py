"""evidence — the append-only evidence store.

Plan: docs/superpowers/plans/2026-09-05-evidence-store.md. Python 3 stdlib
only: this file runs inside hardened systemd --user units (Helm) with the
bare pkgs.python3, in the seat driver, and in dark-factory agents.

Streams are JSONL files under one directory. Every row carries v (schema
version), ts (UTC, RFC3339 with 'Z') and kind. Appends hold an exclusive
flock on the stream file so the Helm units, the seat driver and several
factory agents can write at the same time without interleaving lines.
Rows are never rewritten in place (the token/cost ledger under <store>/ledger
is the one exception and is owned by tools/ledger/factory.py).
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import glob
import importlib
import json
import os
import pathlib
import re
import subprocess
import sys

import streams

DEFAULT_STORE = "/var/lib/evidence"
STREAM_RE = re.compile(r"^(?:(?:derived|ledger)/)?[a-z][a-z0-9-]{0,31}$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
INGEST_MODULES = {
    "judgements": "judgements",
    "result": "ingest_result",
    "reviews": "ingest_reviews",
    "openrouter-usage": "ingest_openrouter_usage",
    "otel": "ingest_otel",
}
INGEST_TARGETS = "|".join(INGEST_MODULES)
CLASSES = (
    "unit",
    "eval",
    "vm",
    "nix-check",
    "curl",
    "browser",
    "operator",
    "unmeasured",
)


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stream_path(store: str, stream: str) -> pathlib.Path:
    if not STREAM_RE.match(stream):
        raise ValueError(f"bad stream name: {stream!r}")
    return pathlib.Path(store) / f"{stream}.jsonl"


def append(store: str, stream: str, row: dict, ts: str | None = None) -> dict:
    """Append one row (envelope added) under an exclusive lock; return it.

    The row is validated against `streams.validate` before the lock: a refused
    row raises `streams.StreamRefused` with nothing written. The envelope `v`
    comes from the declared kind's version, not a global constant.
    """
    path = stream_path(store, stream)  # ValueError on a bad stream name
    kind = row.get("kind")
    errors = streams.validate(kind, row)
    if errors:
        raise streams.StreamRefused(errors)
    if streams.stream_of(kind, row) != stream:
        raise streams.StreamRefused([f"kind {kind} does not write stream {stream}"])
    full = {**row, "v": streams.KINDS[kind]["v"], "ts": ts or now_iso()}
    line = json.dumps(full, sort_keys=True, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    try:
        os.fchmod(fd, 0o640)  # the umask must not widen or narrow the group bit
        fcntl.flock(fd, fcntl.LOCK_EX)
        with os.fdopen(fd, "a") as fh:  # takes ownership of fd; close releases the lock
            fd = None
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
    finally:
        if fd is not None:
            os.close(fd)
    return full


def _read_rows(path: pathlib.Path) -> list[dict]:
    rows: list[dict] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a torn line never hides the rows around it
    return rows


def read(store: str, stream: str) -> list[dict]:
    """Every parseable row of a stream, in file order, followed by those of
    every monthly sibling ``<name>-YYYY-MM.jsonl`` in name order; [] when
    nothing exists. ``stream_path`` names one file (writers are unchanged)."""
    path = stream_path(store, stream)
    parent = path.parent
    if not parent.exists():
        return []
    rows: list[dict] = _read_rows(path) if path.exists() else []
    name = path.name.removesuffix(".jsonl")
    month_re = re.compile(r"^" + re.escape(name) + r"-\d{4}-\d{2}\.jsonl$")
    siblings = sorted(
        p for p in parent.iterdir() if p.is_file() and month_re.match(p.name)
    )
    for sibling in siblings:
        rows.extend(_read_rows(sibling))
    return rows


def _strip_env(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in ("v", "ts")}


def replace_stream(store: str, stream: str, rows: list[dict]) -> int:
    """Rewrite a keyed stream in place by key, all-or-nothing.

    Every incoming row is validated first (a refusal lists every reason of
    every row prefixed ``row {i}: ``); the kind must declare a key (keyless
    streams are append-only). Under one exclusive flock the existing parseable
    rows are read (torn lines dropped), an incoming row equal to the existing
    one ignoring ``v``/``ts`` keeps the existing ``ts``, a changed row gets
    ``ts=now``, a new key is appended, then the whole file is written to a
    ``<path>.tmp`` and ``os.replace``d atomically. Returns the row count.
    """
    path = stream_path(store, stream)
    errors: list[str] = []
    for i, row in enumerate(rows):
        kind = row.get("kind")
        for reason in streams.validate(kind, row):
            errors.append(f"row {i}: {reason}")
    if errors:
        raise streams.StreamRefused(errors)
    if not rows:
        return len(read(store, stream))
    kind = rows[0].get("kind")
    entry = streams.KINDS[kind]
    if entry["key"] is None:
        raise streams.StreamRefused([f"kind {kind}: no key; use append"])
    key_fields = entry["key"]
    now = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o750)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o640)
    try:
        os.fchmod(fd, 0o640)
        fcntl.flock(fd, fcntl.LOCK_EX)
        existing: list[dict] = []
        with os.fdopen(os.dup(fd), "r") as fh:
            fh.seek(0)
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a torn line never survives a rewrite

        def keyed(r):
            return tuple(r[f] for f in key_fields)

        merged = {keyed(r): r for r in existing}
        for row in rows:
            k = keyed(row)
            if k in merged and _strip_env(merged[k]) == _strip_env(row):
                continue  # unchanged: keep the existing ts byte-for-byte
            merged[k] = {**_strip_env(row), "v": entry["v"], "ts": now}

        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w") as fh:
            os.fchmod(fh.fileno(), 0o640)
            fh.writelines(
                json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n"
                for r in merged.values()
            )
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(str(tmp), str(path))
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
        return len(merged)
    finally:
        os.close(fd)


def _gate_key(g: dict) -> tuple:
    """Newest-wins key for a gate row: review_commit_ts (or "") then ts."""
    return (g.get("review_commit_ts") or "", g.get("ts") or "")


def join_tasks_gates(store: str) -> list[dict]:
    """One entry per ``derived/tasks`` row (kind ``task-result``) in file
    order: the row plus its newest gate on ``(run_id, key)`` and its
    ``ledger/activity-days`` row on ``(result_mtime[:10], model)``."""
    tasks = [r for r in read(store, "derived/tasks") if r.get("kind") == "task-result"]
    gates = [r for r in read(store, "derived/gates") if r.get("kind") == "gate-verdict"]
    newest: dict[tuple, dict] = {}
    for g in gates:
        k = (g.get("run_id"), g.get("key"))
        cur = newest.get(k)
        if cur is None or _gate_key(g) > _gate_key(cur):
            newest[k] = g
    activity = {
        (a.get("date"), a.get("model")): a
        for a in read(store, "ledger/activity-days")
        if a.get("kind") == "activity-day"
    }
    out: list[dict] = []
    for t in tasks:
        run_id = t.get("run_id")
        key = t.get("key")
        act_key = (t.get("result_mtime") or "")[:10], t.get("model")
        out.append(
            {
                "run_id": run_id,
                "key": key,
                "task": t,
                "gate": newest.get((run_id, key)),
                "activity": activity.get(act_key),
            }
        )
    return out


def n_gate(rows, n: int = 5):
    """`rows` when it holds at least `n` entries, else the refusal string."""
    if len(rows) >= n:
        return rows
    return f"insufficient (n={len(rows)})"


def latest_check(store: str, name: str, rev: str) -> dict | None:
    rows = [
        r
        for r in read(store, "checks")
        if r.get("kind") == "check" and r.get("name") == name and r.get("rev") == rev
    ]
    # Newest wins; on equal 1-second timestamps the later-appended row wins
    # (max() would return the first of a tie — a stale pass could mask a fail).
    best: dict | None = None
    for r in rows:
        if best is None or r["ts"] >= best["ts"]:
            best = r
    return best


def run(argv, timeout=20.0):
    """The one subprocess seam (tests monkeypatch or pass stub binaries)."""
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def _git(repo, *args):
    try:
        cp = run(["git", "-C", repo, *args])
    except (OSError, subprocess.SubprocessError):
        return None
    return cp.stdout.strip() if cp.returncode == 0 else None


def _docs_equivalent(repo, a, b) -> bool:
    if a == b:
        return True
    try:
        cp = run(
            ["git", "-C", repo, "diff", "--quiet", a, b, "--", ".", ":!docs", ":!*.md"]
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return cp.returncode == 0


def bundle(
    store,
    repo,
    claims_path,
    siblings,
    nixos_version_bin="/run/current-system/sw/bin/nixos-version",
    now=None,
) -> dict:
    now = now or datetime.datetime.now(datetime.timezone.utc)
    head = _git(repo, "rev-parse", "HEAD")
    status = _git(repo, "status", "--porcelain")
    dirty = None if status is None else bool(status)
    live = None
    try:
        cp = run([nixos_version_bin, "--configuration-revision"])
        out = (cp.stdout.strip() if cp.returncode == 0 else "").removesuffix("-dirty")
        live = out if REV_RE.match(out) else None
    except (OSError, subprocess.SubprocessError):
        live = None
    try:
        generation = os.path.basename(os.readlink("/nix/var/nix/profiles/system"))
    except OSError:
        generation = None
    docs_only = bool(
        head and live and live != head and _docs_equivalent(repo, live, head)
    )

    checks: dict = {}
    rows = [
        r
        for r in read(store, "checks")
        if r.get("kind") == "check" and isinstance(r.get("rev"), str)
    ]
    rows.sort(key=lambda r: r.get("ts", ""))
    for name in sorted({r["name"] for r in rows}):
        mine = [r for r in rows if r["name"] == name][-50:]

        def cover(rev, mine=mine):
            if rev is None:
                return None
            for r in reversed(mine):
                if _docs_equivalent(repo, r["rev"], rev):
                    return r
            return None

        checks[name] = {"head": cover(head), "live": cover(live)}

    sib = {}
    for path in siblings:
        sib[os.path.basename(path.rstrip("/"))] = _git(
            path, "log", "-1", "--format=%h %s"
        )

    helm = None
    srows = [r for r in read(store, "helm-status") if r.get("kind") == "helm-status"]
    if srows:
        last = srows[-1]
        tiles = {}
        for name, status in last.get("tiles", {}).items():
            since = last["ts"]
            for r in reversed(srows):
                if r.get("tiles", {}).get(name) == status:
                    since = r["ts"]
                else:
                    break
            tiles[name] = {"status": status, "since": since}
        helm = {"ts": last["ts"], "tiles": tiles}

    claims_out = {"verified": 0, "parked": 0, "gaps": []}
    if pathlib.Path(claims_path).exists():
        # claims.py sits beside this file; never rely on the caller's sys.path.
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import claims as claims_mod

        rows_c = claims_mod.load(claims_path)
        claims_out["verified"] = sum(1 for r in rows_c if r.get("status") == "verified")
        claims_out["parked"] = sum(1 for r in rows_c if r.get("status") == "parked")
        today = now.date()
        for g in claims_mod.open_gaps(rows_c):
            rb = g.get("review_by")
            claims_out["gaps"].append(
                {
                    "id": g["id"],
                    "owner": g.get("owner"),
                    "opened": str(g.get("opened")),
                    "review_by": str(rb),
                    "closes_by": g.get("closes_by"),
                    "stale": bool(rb and rb < today),
                }
            )

    joined = join_tasks_gates(store)
    join = {
        "tasks": len(joined),
        "with_gate": sum(1 for j in joined if j["gate"] is not None),
        "with_activity": sum(1 for j in joined if j["activity"] is not None),
    }

    return {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "live": {"generation": generation, "rev": live},
        "head": head,
        "docs_only_ahead": docs_only,
        "dirty": dirty,
        "checks": checks,
        "siblings": sib,
        "helm": helm,
        "join": join,
        "claims": claims_out,
    }


def render_bundle_markdown(b: dict) -> str:
    def short(x):
        return (x or "none")[:12]

    if b["live"]["rev"] == b["head"]:
        ahead = " (equal to live)"
    elif b["docs_only_ahead"]:
        ahead = " (docs-only ahead of live)"
    else:
        ahead = ""
    lines = [f"# Evidence bundle — {b['generated']}", ""]
    lines.append(
        f"**Live:** {b['live']['generation'] or 'unknown generation'} at {short(b['live']['rev'])}. **HEAD:** {short(b['head'])}"
        + ahead
        + (" — WORKING TREE DIRTY" if b["dirty"] else "")
        + "."
    )
    lines += ["", "## Checks covering HEAD and the live system", ""]
    if not b["checks"]:
        lines.append("no observations recorded yet")
    for name, cov in b["checks"].items():

        def cell(r):
            return (
                "—"
                if r is None
                else f"{'ok' if r.get('ok') else 'FAIL'} @{r['rev'][:12]} {r.get('class', '?')}/{r.get('src', '?')} {r.get('ts', '')}"
            )

        lines.append(f"- {name}: HEAD {cell(cov['head'])}; live {cell(cov['live'])}")
    lines += ["", "## Repo heads", ""] + [
        f"- {k}: {v or 'unreadable'}" for k, v in b["siblings"].items()
    ]
    lines += ["", "## Helm now", ""]
    if b["helm"] is None:
        lines.append("no observations (helm-status stream empty)")
    else:
        lines += [
            f"- {n}: {t['status']} since {t['since']}"
            for n, t in sorted(b["helm"]["tiles"].items())
        ]
    j = b["join"]
    lines += [
        "",
        f"## Join: {j['tasks']} task rows, {j['with_gate']} with a gate verdict, {j['with_activity']} with activity",
        "",
    ]
    c = b["claims"]
    lines += [
        "",
        f"## Claims: {c['verified']} verified, {c['parked']} parked, {len(c['gaps'])} open gaps",
        "",
    ]
    for g in c["gaps"]:
        lines.append(
            f"- {'STALE ' if g['stale'] else ''}{g['id']} (owner {g['owner']}, opened {g['opened']}, review by {g['review_by']}): {g['closes_by']}"
        )
    return "\n".join(lines) + "\n"


def split_global(argv: list[str]) -> tuple[str | None, list[str]]:
    """Consume leading ``--store X`` / ``--store=X`` global options; return
    (store, rest). Only the plain ``--store`` global option exists today, so
    anything else ends the global prefix."""
    store: str | None = None
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--store" and i + 1 < len(argv):
            store = argv[i + 1]
            i += 2
        elif tok.startswith("--store="):
            store = tok.split("=", 1)[1]
            i += 1
        else:
            break
    return store, argv[i:]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    store, rest = split_global(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    if rest and rest[0] == "tasks":
        # tasks.py sits beside this file; never rely on the caller's sys.path.
        if here not in sys.path:
            sys.path.insert(0, here)
        import tasks

        forwarded = (["--store", store] if store else []) + rest[1:]
        return tasks.main(forwarded)
    if rest and rest[0] == "repomap":
        if here not in sys.path:
            sys.path.insert(0, here)
        import repomap

        return repomap.main(rest[1:])
    if rest and rest[0] == "ingest":
        if len(rest) < 2:
            parser = argparse.ArgumentParser(prog="evidence")
            parser.error(f"ingest requires a target ({INGEST_TARGETS})")
        name = rest[1]
        if name not in INGEST_MODULES:
            print(
                f"evidence: ingest: unknown target {name} ({INGEST_TARGETS})",
                file=sys.stderr,
            )
            return 2
        if here not in sys.path:
            sys.path.insert(0, here)
        try:
            module = importlib.import_module(INGEST_MODULES[name])
        except ImportError:
            print(
                f"evidence: ingest {name}: not available in this tree", file=sys.stderr
            )
            return 2
        forwarded = (["--store", store] if store else []) + rest[1:]
        return module.main(forwarded)
    if rest and rest[0] == "report":
        # report.py sits beside this file; never rely on the caller's
        # sys.path. The store global is forwarded exactly as for tasks.
        if here not in sys.path:
            sys.path.insert(0, here)
        import report

        forwarded = (["--store", store] if store else []) + rest[1:]
        return report.main(forwarded)

    parser = argparse.ArgumentParser(prog="evidence")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE", DEFAULT_STORE)
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tasks", help="the derived task graph (see tasks.py --help)")
    sub.add_parser("repomap", help="the repo map (see repomap.py --help)")
    sub.add_parser("ingest", help="ingest derived streams (see judgements.py --help)")
    sub.add_parser("report", help="planning-agent metrics (see report.py --help)")

    p_rec = sub.add_parser("record", help="append one row to a stream")
    p_rec.add_argument("stream")
    p_rec.add_argument("--json", required=True, help='a JSON object with a "kind"')

    p_chk = sub.add_parser("record-check", help="append one check observation")
    p_chk.add_argument("--name", required=True)
    p_chk.add_argument("--rev", required=True)
    grp = p_chk.add_mutually_exclusive_group(required=True)
    grp.add_argument("--ok", action="store_true")
    grp.add_argument("--fail", action="store_true")
    p_chk.add_argument("--class", dest="cls", required=True, choices=CLASSES)
    p_chk.add_argument("--src", required=True)
    p_chk.add_argument("--duration", type=int)
    p_chk.add_argument("--log-tail-file")

    p_lat = sub.add_parser(
        "latest-check", help="newest observation for a check at a revision"
    )
    p_lat.add_argument("--name", required=True)
    p_lat.add_argument("--rev", required=True)

    p_bun = sub.add_parser(
        "bundle", help="the facts a fresh session reads: live, HEAD, checks, Helm, gaps"
    )
    p_bun.add_argument("--markdown", action="store_true")
    p_bun.add_argument("--repo", default="/home/dalhaka/nixos-agent-env")
    p_bun.add_argument("--claims", default=None)
    p_bun.add_argument("--sibling", action="append", default=None)
    p_bun.add_argument(
        "--nixos-version-bin", default="/run/current-system/sw/bin/nixos-version"
    )

    a = parser.parse_args(argv)
    if a.cmd == "record":
        try:
            row = json.loads(a.json)
        except json.JSONDecodeError as e:
            parser.error(f"--json is not valid JSON: {e}")
        if not isinstance(row, dict) or "kind" not in row:
            parser.error('--json must be an object with a "kind"')
        try:
            print(json.dumps(append(a.store, a.stream, row), sort_keys=True))
        except streams.StreamRefused as exc:
            for reason in exc.errors:
                print(f"evidence: refused: {reason}", file=sys.stderr)
            return 2
        return 0
    if a.cmd == "record-check":
        if not REV_RE.match(a.rev):
            parser.error("--rev must be a full 40-hex commit id")
        row: dict = {
            "kind": "check",
            "name": a.name,
            "rev": a.rev,
            "ok": bool(a.ok),
            "class": a.cls,
            "src": a.src,
        }
        if a.duration is not None:
            row["duration_s"] = a.duration
        if a.log_tail_file:
            row["log_tail"] = pathlib.Path(a.log_tail_file).read_text()[-4000:]
        try:
            print(json.dumps(append(a.store, "checks", row), sort_keys=True))
        except streams.StreamRefused as exc:
            for reason in exc.errors:
                print(f"evidence: refused: {reason}", file=sys.stderr)
            return 2
        return 0
    if a.cmd == "latest-check":
        row = latest_check(a.store, a.name, a.rev)
        if row is None:
            return 1
        print(json.dumps(row, sort_keys=True))
        return 0
    if a.cmd == "bundle":
        claims = a.claims or os.path.join(a.repo, "docs", "ledger", "claims.toml")
        siblings = a.sibling or sorted(
            p
            for p in glob.glob(os.path.join(os.path.expanduser("~"), "flakes", "*"))
            if os.path.isdir(p)
        )
        b = bundle(a.store, a.repo, claims, siblings, a.nixos_version_bin)
        if a.markdown:
            print(render_bundle_markdown(b), end="")
        else:
            print(json.dumps(b, indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
