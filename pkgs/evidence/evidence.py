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
import json
import os
import pathlib
import re
import subprocess
import sys

VERSION = 1
DEFAULT_STORE = "/var/lib/evidence"
STREAM_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
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
    """Append one row (envelope added) under an exclusive lock; return it."""
    full = {**row, "v": VERSION, "ts": ts or now_iso()}
    line = json.dumps(full, sort_keys=True, separators=(",", ":")) + "\n"
    path = stream_path(store, stream)
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


def read(store: str, stream: str) -> list[dict]:
    """Every parseable row of a stream, in file order; [] when absent."""
    path = stream_path(store, stream)
    if not path.exists():
        return []
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

    return {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "live": {"generation": generation, "rev": live},
        "head": head,
        "docs_only_ahead": docs_only,
        "dirty": dirty,
        "checks": checks,
        "siblings": sib,
        "helm": helm,
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
        # judgements.py sits beside this file; never rely on the caller's
        # sys.path. The store global is forwarded exactly as for tasks.
        if here not in sys.path:
            sys.path.insert(0, here)
        import judgements

        forwarded = (["--store", store] if store else []) + rest[1:]
        return judgements.main(forwarded)
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
        print(json.dumps(append(a.store, a.stream, row), sort_keys=True))
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
        print(json.dumps(append(a.store, "checks", row), sort_keys=True))
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
