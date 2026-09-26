# Evidence store — the Harness-of-Harness concepts and the environment review, folded into one plan (2026-09-05)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) and `tools/factory/dark-factory.js` both read the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and `commit subject`.

**Goal:** one append-only evidence store on the host, a claims file in the repo that separates verified claims from gaps, tiles and a board that are rebuilt from that evidence instead of from persisted prose, a factory that records what it did, and the environment review's confirmed defects closed (one blocker in the broker, the Helm tiles, the runbooks, the basket teardown, the seat guard).

**Architecture:** `/var/lib/evidence/` holds JSONL streams (checks observed, Helm verdict transitions, factory run reports, the token/cost ledger), written under a file lock by the Helm units, the seat driver and the dark factory. `docs/ledger/claims.toml` — called "the claims file" everywhere in prose; "the ledger" keeps meaning the pre-existing token/cost ledger of `tools/ledger/factory.py` — holds the project's claims as `verified`, `gap` or `parked`; a flake check validates its shape and the pre-commit hook fails on a stale gap. `evidence bundle` prints the live facts a fresh session needs; `docs/OPERATIONS.md` shrinks to one START HERE block that carries the plan and never the facts. Helm's flake-check and drift tiles read observations and tolerate docs-only differences.

**Tech Stack:** Python 3 stdlib only in `pkgs/` (`json`, `fcntl`, `tomllib`, `subprocess`), NixOS modules + tmpfiles, pytest, bats, node (the factory's own test harness), mitmproxy's test helpers (broker), treefmt/ruff/shellcheck/statix/deadnix.

**Spec:** `docs/research-2026-09-04-paper-2609.01481.md` (the digest; mechanisms, never magnitudes), `docs/reviews/2026-09-05-environment-review.md` (89 confirmed findings; the R tasks below cite their ids), and the design decisions in §"Decisions". Executors read all three. Operator words that fix scope: "Fold as many of those concepts we can use from the paper into the plan we get"; "high levels of parallel development are encouraged".

**Review of this plan:** four adversarial reviewers (feasibility Python/Nix, feasibility JS/shell, falsifiability and waves, paper coverage) on 2026-09-05; every blocker and major they raised is folded in below (pickling under Python 3.14, the store-path import, the etc `.text` null, the `_status` collision, zoneinfo in the sandbox, `runScript` arity, `importlib.reload`, the bats identity and shebang, `spent` ordering, the wave table).

## What exists today (inventory, 2026-09-05 07:40 CDT)

There is no central database. Data lands in ten places, five formats, no index, no history for Helm:

| store | format | writer | history? | backed up? |
|---|---|---|---|---|
| `~/strategy/ledger/*.jsonl` (the token/cost ledger, `tools/ledger/factory.py`) | JSONL, idempotent by key | run by hand; **directory does not exist**, so the ledger has never held real data | yes | yes (`~/strategy` is a restic path) |
| `/var/lib/lanes/<lane>/ledger.jsonl` | JSONL | lane unit (root-owned dir, unreadable by the operator) | yes | no |
| `/var/lib/egress-broker/<name>/audit.jsonl` | JSONL | broker | yes | no |
| `/var/lib/helm/status.json`, `flake-check.json` | JSON snapshot, overwritten | helm-collect (5 min), helm-flake-check (03:00) | **no** | no |
| `~/.local/share/dsh-openrouter/sessions/…` | dsh transcripts | the seat | yes | no |
| `~/factory/runs/<run>/<KEY>.{log,result}` (112 runs, 96 MB) | text + parsed result | seat driver | yes | no |
| `~/.claude/projects/…/subagents/workflows/<wf>/journal.jsonl` | JSONL | Claude workflows | yes | no |
| `docs/reviews/*.json`, `docs/OPERATIONS.md` (106 KB) | JSON / prose | orchestrator | in git | yes |
| systemd journal (helm-serve switch audit lines) | journal | units | yes (rotation) | no |
| restic repo | ciphertext | backup unit | yes | is the backup |

## Decisions

- **D1 Store.** `/var/lib/evidence/` (declared by `nixosModules/evidenceStore.nix`, created by tmpfiles `0750 <operator>:users`, added to the restic paths). Streams are JSONL files, one object per line, every row carrying `v`, `ts` (UTC, RFC3339 `Z`) and `kind`. Appends hold an exclusive `flock`. Nothing is rewritten in place except the token/cost ledger's own idempotent merge files under `ledger/`. A derived SQLite index is **not** built now; the trigger to add one is any stream over 50 MB or any `evidence bundle` run over 2 s.
- **D2 Claims are policy, observations are data.** `docs/ledger/claims.toml` (repo, reviewed in diffs) holds claims: `verified` rows name the check and revision that proved them (`check:<name>@<rev>`) or the operator drill (`operator:<date> …`) and an evidence class; `gap` rows name an owner, a review date and what would close them; `parked` rows name the decision. Observations (`checks.jsonl`) record that a named check ran at a revision with a result. A claim is never `verified` by prose: the validator refuses evidence that is not in one of those two shapes.
- **D3 Evidence class** is part of every observation and every verified claim: `unit | eval | vm | nix-check | curl | browser | operator | unmeasured`. A curl-verified claim is visibly weaker than a browser-verified one (field lesson H3).
- **D4 Tiles read observations, tolerate docs-only diffs.** Two revisions are *docs-equivalent* when `git diff --quiet A B -- . ':!docs' ':!*.md'` exits 0. flake-check is green when an observation covers a rev docs-equivalent to HEAD; drift is green when live is docs-equivalent to HEAD. Both carry `since`. Comparing toplevel store paths cannot replace this (the toplevel bakes the commit id via `system.configurationRevision`); the exact measure is a closure diff that shows only the nixos-version file, recorded as a gap.
- **D5 The board carries the plan, the bundle carries the facts.** `docs/OPERATIONS.md` keeps exactly one `## START HERE` block and at most 160 lines; the log and the archive move under `docs/board/`. Facts (live generation, heads, checks covering HEAD, open gaps, Helm verdicts) come from `evidence bundle --markdown` at session start. This is the paper's mechanism: the plan is rebuilt each turn from the fixed spec plus the last evidence bundle, not carried forward as accumulated prose. (The turn's log entry is still appended to `docs/board/log-2026-09.md`; only START HERE itself is replaced, never appended to.)
- **D6 The factory records itself.** Every structured result carries `task_key`, `round` and `label`; the verifier records its `nix flake check` as an observation; a final recorder agent appends the run report to `runs.jsonl`. The ledger reads the attribution.
- **D7 Runs nightly stay, re-runs stop.** The 03:00 flake check remains a safety net; the seat integrator and the factory verifier record the checks they already run, so nothing is re-run to colour a tile.
- **D8 The broker keys on the destination it routes to**, never on a client-supplied Host header (review r2-1-1, blocker): allowlist, credential injection, deny paths and body patch all use `flow.request.host`, and any disagreement between the routed host, the Host header and the SNI is a deny.

## Global Constraints

- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown outside `tests/run-mount-tests.sh`, no reading `/var/lib/secrets/*`, `~/.config/openrouter/key` or `~/.config/restic/password`. The operator switches (§"Operator" below).
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null` a gated command.
- Each task's spec names its own commit subject; the trailer is exactly `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- TDD: the failing check first, shown red, then green. A load-bearing test counts only once it has been shown to fail; a test that cannot fail is a `vacuous-test` major finding. Every proxy names what it stands in for and its gap (`docs/decisions/2026-09-03-test-based-reality-amendments.md`).
- **The Python blocks below are specifications, not byte-exact files.** The repo has no ruff config, so `ruff format` (88 columns, via treefmt and `checks.lint`) rewraps most of them. After writing each block run `nix develop -c ruff format <the paths this task created or changed>`, re-run the task's tests, then the lint gate. A reformatting-only difference from the plan text is not a deviation.
- Python is stdlib only in `pkgs/evidence`, `pkgs/helm`, `pkgs/broker` (mitmproxy is the one runtime dependency the broker already has). Tests may use pytest.
- **One writer per tree.** An implementer works only in the isolated worktree it was started in, on exactly one branch named by its task key; `touches` is a contract — a file outside it is a deviation to report, not to write.
- Claude agents never write inside `~/flakes/dsh-harness`; this plan touches only `~/nixos-agent-env`.
- Nix style: statix rejects `{ ... }:` headers (write `_:` or name the args); `hosts/core/hardware-configuration.nix` is exempt from formatting. Shell pasted into `githooks/pre-commit` is reformatted by shfmt: paste, run treefmt, then copy the formatted text into any Nix string that must stay identical.
- No secrets in the repo; no example row in `claims.toml` may quote a key, token or path under `/var/lib/secrets`.

## Assumptions

1. The host pin's `python3` is ≥ 3.11 (`tomllib` in the stdlib); the devShell has 3.14.7, whose `multiprocessing` default is `forkserver` (tests spawn subprocesses instead). `pyyaml` is **not** available, hence TOML.
2. `EVIDENCE_STORE` (a directory path) is honoured by every writer; tests set it to a temp dir and never touch `/var/lib/evidence`. Every writer passes `--store "${EVIDENCE_STORE:-/var/lib/evidence}"` explicitly.
3. Until the operator switches after wave 2, `/var/lib/evidence` does not exist on the host: recorders report "not recorded" and carry on (never a failure), and the Helm tiles fall back to today's file-based rule when `checks.jsonl` is absent (E5). Nothing in this plan needs the switch to be tested.
4. E1 and E3 integrate in the same wave: E3's prompt text names `pkgs/evidence/evidence.py`, which E1 creates. Their unit tests are text-only and do not execute it.
5. `git diff --quiet A B -- . ':!docs' ':!*.md'` exits 0 for docs-equivalent, 1 for different, 128 for an unknown revision (treated as different). Verified 2026-09-05.
6. The operator re-syncs `~/factory/bin` from `tools/factory/seat` after E7 and R10 land (R10 makes the copy unnecessary).
7. The Nix build sandbox has no zoneinfo and no `/usr/bin/env`: local-time tests use a POSIX `TZ` string (`CST6CDT,M3.2.0,M11.1.0`), bats stubs use the `$REAL_BASH` the file already resolves.
8. `checks.unit` skips the basket mount tests (they need namespace root); R7's red-first proof runs under `nix develop -c tests/run-mount-tests.sh`.

## Waves

Waves follow `dependsOn` (the scheduler builds them with Kahn's algorithm; two tasks in one wave that edit the same file serialise in key order).

| wave | tasks | dependsOn | notes |
|---|---|---|---|
| 1 | E1, E3, E4, R1, R2, R4, R5, R7, R8 | — | E1, R4, R5 all edit `flake.nix` → serialised; everything else is disjoint |
| 2 | E2, E5, E7, R9 | E2: [E1]; E5: [E1, R4]; E7: [E1]; R9: [R8] | E2 and E5 both edit `flake.nix` → serialised |
| 3 | E6, E8, E9, R10 | E6: [E5]; E8: [E2, R5]; E9: [E2, E8]; R10: [E7] | E8 before E9 because CLAUDE.md points at `docs/board/` |
| 4 | R3 | R3: [E6] | collect.py after E6 |

## Operator

One switch after wave 2 (creates `/var/lib/evidence`, gives the Helm units their write path, puts `evidence` on PATH, lands the broker fix): `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core`, then `systemctl --user start helm-collect.service`. The broker instance restarts with the switch; the seat needs a relaunch (hook guard). Rollback is the previous generation. Nothing else.

---

## Tasks

### E1 (code, M) — the evidence store: module, CLI, schema, checks

**dependsOn:** none

**Files:**
- Create: `nixosModules/evidenceStore.nix`, `pkgs/evidence/evidence.py`, `pkgs/evidence/SCHEMA.md`, `tests/evidence/test_evidence.py`
- Modify: `flake.nix` (nixosModules export; `packages.evidence`; `checks.evidence-unit`, `checks.evidence-eval`; `host-core` assertions; the `lint` ruff lists; `nixosConfigurations.core.modules`), `hosts/core/default.nix` (enable), `hosts/core/proton-backup.nix` (restic path), `githooks/pre-commit` (ruff lists)

**Interfaces:**
- Produces the CLI `evidence` (installed on the host by the module; runnable pre-switch as `nix develop -c python3 pkgs/evidence/evidence.py …` or `nix run .#evidence --`):
  - `evidence [--store DIR] record <stream> --json '<object with "kind">'` → appends `{"v":1,"ts":"<UTC Z>", …object}`, prints the row.
  - `evidence [--store DIR] record-check --name N --rev <40 hex> (--ok|--fail) --class C --src S [--duration SECONDS] [--log-tail-file F]` → appends to `checks.jsonl` a row `{"kind":"check","name":N,"rev":…,"ok":bool,"class":C,"src":S,"duration_s":…,"log_tail":…}`.
  - `evidence [--store DIR] latest-check --name N --rev SHA` → prints the newest matching row, exit 0; exit 1 when none.
  - `--store` defaults to `$EVIDENCE_STORE`, then `/var/lib/evidence`.
- Produces the Python API in `pkgs/evidence/evidence.py`: `append(store, stream, row, ts=None) -> dict`, `read(store, stream) -> list[dict]`, `latest_check(store, name, rev) -> dict | None`, constants `VERSION = 1`, `CLASSES`, `STREAM_RE`, `REV_RE`.
- Produces the NixOS options `services.evidence-store.{enable, path (default "/var/lib/evidence"), owner (default "dalhaka"), group (default "users"), package}`; the module installs the CLI and the tmpfiles rules `d <path> 0750 <owner> <group> -` and `d <path>/ledger 0750 <owner> <group> -`. The wrapper embeds the **directory** `pkgs/evidence` (E9's `bundle` imports the sibling `claims.py`), never the lone file.
- `pkgs/evidence/SCHEMA.md` is the contract every other task writes against.

- [ ] **Step 1: Write the failing tests** — `tests/evidence/test_evidence.py`:

```python
"""Evidence store unit tests (plan 2026-09-05-evidence-store, E1)."""

import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "evidence.py",
        pathlib.Path("pkgs/evidence/evidence.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))  # bundle() imports the sibling claims.py
    spec = importlib.util.spec_from_file_location("evidence", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["evidence"] = mod
    spec.loader.exec_module(mod)
    return mod, src


ev, SRC = load()
REV_A = "a" * 40
REV_B = "b" * 40


def test_append_creates_stream_with_envelope_and_mode(tmp_path):
    row = ev.append(str(tmp_path), "checks", {"kind": "check", "name": "lint"}, ts="2026-09-05T12:00:00Z")
    path = tmp_path / "checks.jsonl"
    assert row == {"v": 1, "ts": "2026-09-05T12:00:00Z", "kind": "check", "name": "lint"}
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    lines = path.read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0]) == row


def test_append_is_append_only_and_ordered(tmp_path):
    ev.append(str(tmp_path), "runs", {"kind": "factory-run", "n": 1}, ts="2026-09-05T12:00:00Z")
    ev.append(str(tmp_path), "runs", {"kind": "factory-run", "n": 2}, ts="2026-09-05T12:00:01Z")
    assert [r["n"] for r in ev.read(str(tmp_path), "runs")] == [1, 2]


def test_bad_stream_name_is_refused(tmp_path):
    with pytest.raises(ValueError):
        ev.append(str(tmp_path), "../etc", {"kind": "x"})
    with pytest.raises(ValueError):
        ev.append(str(tmp_path), "Checks", {"kind": "x"})


def test_read_missing_stream_is_empty(tmp_path):
    assert ev.read(str(tmp_path), "checks") == []


def test_read_skips_a_torn_line(tmp_path):
    ev.append(str(tmp_path), "checks", {"kind": "check", "name": "a"}, ts="2026-09-05T12:00:00Z")
    with open(tmp_path / "checks.jsonl", "a") as fh:
        fh.write('{"v":1,"ts":"2026-09-05T12:00:01Z","kind":"che')
    assert [r["name"] for r in ev.read(str(tmp_path), "checks")] == ["a"]


def test_latest_check_picks_newest_for_name_and_rev(tmp_path):
    s = str(tmp_path)
    ev.append(s, "checks", {"kind": "check", "name": "flake-check", "rev": REV_A, "ok": False}, ts="2026-09-05T01:00:00Z")
    ev.append(s, "checks", {"kind": "check", "name": "flake-check", "rev": REV_A, "ok": True}, ts="2026-09-05T03:00:00Z")
    ev.append(s, "checks", {"kind": "check", "name": "flake-check", "rev": REV_B, "ok": False}, ts="2026-09-05T04:00:00Z")
    ev.append(s, "checks", {"kind": "check", "name": "lint", "rev": REV_A, "ok": False}, ts="2026-09-05T05:00:00Z")
    assert ev.latest_check(s, "flake-check", REV_A)["ok"] is True
    assert ev.latest_check(s, "flake-check", REV_B)["ok"] is False
    assert ev.latest_check(s, "unit", REV_A) is None


def cli(tmp_path, *args):
    env = dict(os.environ, EVIDENCE_STORE=str(tmp_path))
    return subprocess.run([sys.executable, str(SRC), *args], capture_output=True, text=True, env=env, check=False)


def test_cli_record_check_ok_and_fail(tmp_path):
    tail = tmp_path / "tail.txt"
    tail.write_text("last lines\n")
    r = cli(tmp_path, "record-check", "--name", "flake-check", "--rev", REV_A, "--ok", "--class", "nix-check", "--src", "helm-nightly", "--duration", "105", "--log-tail-file", str(tail))
    assert r.returncode == 0, r.stderr
    printed = json.loads(r.stdout)
    assert printed["ok"] is True and printed["duration_s"] == 105 and printed["log_tail"] == "last lines\n"
    r = cli(tmp_path, "record-check", "--name", "flake-check", "--rev", REV_A, "--fail", "--class", "nix-check", "--src", "seat-integrate")
    assert r.returncode == 0 and json.loads(r.stdout)["ok"] is False
    assert [row["ok"] for row in ev.read(str(tmp_path), "checks")] == [True, False]


def test_cli_record_check_rejects_short_rev_and_unknown_class(tmp_path):
    r = cli(tmp_path, "record-check", "--name", "lint", "--rev", "abc1234", "--ok", "--class", "nix-check", "--src", "x")
    assert r.returncode == 2 and not (tmp_path / "checks.jsonl").exists()
    r = cli(tmp_path, "record-check", "--name", "lint", "--rev", REV_A, "--ok", "--class", "guess", "--src", "x")
    assert r.returncode == 2


def test_cli_record_requires_kind(tmp_path):
    r = cli(tmp_path, "record", "runs", "--json", '{"plan": "p"}')
    assert r.returncode == 2 and not (tmp_path / "runs.jsonl").exists()
    r = cli(tmp_path, "record", "runs", "--json", '{"kind": "factory-run", "plan": "p"}')
    assert r.returncode == 0 and json.loads(r.stdout)["plan"] == "p"


def test_cli_latest_check_exit_codes(tmp_path):
    assert cli(tmp_path, "latest-check", "--name", "lint", "--rev", REV_A).returncode == 1
    cli(tmp_path, "record-check", "--name", "lint", "--rev", REV_A, "--ok", "--class", "nix-check", "--src", "x")
    r = cli(tmp_path, "latest-check", "--name", "lint", "--rev", REV_A)
    assert r.returncode == 0 and json.loads(r.stdout)["name"] == "lint"


def test_concurrent_appends_keep_every_line_parseable(tmp_path):
    # PROXY, stated per the amendments: Linux serialises O_APPEND writes of
    # this size on a local filesystem even without the flock, so this test
    # cannot turn red by removing the lock. It proves N processes leave
    # N*M parseable rows; the lock's own effect is a recorded gap
    # (claims.toml: evidence-flock-effect-unmeasured, E2).
    # Subprocesses, not multiprocessing: Python 3.14 defaults to forkserver
    # on Linux, which pickles the target and cannot carry a function defined
    # inside a test.
    prog = (
        "import sys;"
        "sys.path.insert(0, sys.argv[1]);"
        "import evidence as ev;"
        "i = int(sys.argv[3]);"
        "[ev.append(sys.argv[2], 'runs', {'kind': 't', 'i': i, 'j': j, 'pad': 'x' * 2000}) for j in range(50)]"
    )
    procs = [subprocess.Popen([sys.executable, "-c", prog, str(SRC.parent), str(tmp_path), str(i)]) for i in range(8)]
    for p in procs:
        assert p.wait() == 0
    rows = ev.read(str(tmp_path), "runs")
    assert len(rows) == 400
    assert {(r["i"], r["j"]) for r in rows} == {(i, j) for i in range(8) for j in range(50)}
```

- [ ] **Step 2: Run it red** — `cd ~/nixos-agent-env && nix develop -c pytest tests/evidence -q` → collection error, `StopIteration` from `load()` (no `pkgs/evidence/evidence.py`).

- [ ] **Step 3: Write `pkgs/evidence/evidence.py`**

```python
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
import json
import os
import pathlib
import re
import sys

VERSION = 1
DEFAULT_STORE = "/var/lib/evidence"
STREAM_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
CLASSES = ("unit", "eval", "vm", "nix-check", "curl", "browser", "operator", "unmeasured")


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stream_path(store: str, stream: str) -> pathlib.Path:
    if not STREAM_RE.match(stream):
        raise ValueError(f"bad stream name: {stream!r}")
    return pathlib.Path(store) / f"{stream}.jsonl"


def append(store: str, stream: str, row: dict, ts: str | None = None) -> dict:
    """Append one row (envelope added) under an exclusive lock; return it."""
    full = {"v": VERSION, "ts": ts or now_iso(), **row}
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
    return max(rows, key=lambda r: r["ts"]) if rows else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evidence")
    parser.add_argument("--store", default=os.environ.get("EVIDENCE_STORE", DEFAULT_STORE))
    sub = parser.add_subparsers(dest="cmd", required=True)

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

    p_lat = sub.add_parser("latest-check", help="newest observation for a check at a revision")
    p_lat.add_argument("--name", required=True)
    p_lat.add_argument("--rev", required=True)

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
        row: dict = {"kind": "check", "name": a.name, "rev": a.rev, "ok": bool(a.ok), "class": a.cls, "src": a.src}
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
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Write `pkgs/evidence/SCHEMA.md`** (the contract; other tasks quote it):

```markdown
# Evidence store — streams and row shapes (v1)

Directory: `services.evidence-store.path`, default `/var/lib/evidence` (env `EVIDENCE_STORE`
overrides for tests and pre-switch use; every writer also passes `--store` explicitly). One JSONL
file per stream; append-only under flock; every row: `{"v":1,"ts":"2026-09-05T12:00:00Z","kind":"<kind>", ...}`.
Stream names match `^[a-z][a-z0-9-]{0,31}$`.

| stream | kind | fields | writers |
|---|---|---|---|
| `checks` | `check` | `name` (check name; `flake-check` = the whole `nix flake check`), `rev` (40 hex), `ok` (bool), `class` (`unit|eval|vm|nix-check|curl|browser|operator|unmeasured`), `src` (`helm-nightly`, `seat-integrate`, `dark-factory-verify`, …), `duration_s`?, `log_tail`? (≤ 4000 chars) | helm-flake-check (E5), factory-integrate (E7), dark-factory verify (E3) |
| `helm-status` | `helm-status` | `tiles` (name → `ok|warn|fail|unknown`), `reason` (`change|heartbeat`) | helm-collect (E6) |
| `runs` | `factory-run` | `plan`, `prefix`, `baseline`, `integration_branch`, `tasks[]{key,status,commit,fixRounds}`, `verify` (`pass|fail|skipped|none`), `delivered`, `agents`, `output_tokens`, `run_id`? | dark-factory recorder (E3) |
| `ledger/*.jsonl` | per `tools/ledger/schema.md` | the token/cost ledger; unchanged shapes; idempotent merge, the one non-append-only area | `tools/ledger/factory.py` (E4) |

Readers: `pkgs/helm/collect.py` (tiles), `evidence bundle` (E9), `tools/ledger/factory.py`.
A reader skips a torn line and never fails the whole read on one bad row.
The claims file `docs/ledger/claims.toml` is NOT a stream: it is policy, in the repo (E2).
```

- [ ] **Step 5: Write `nixosModules/evidenceStore.nix`**

```nix
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.evidence-store;
  # The whole directory, not the lone file: evidence.py imports its sibling
  # claims.py at run time (E9's bundle), and a file-valued path would copy
  # only evidence.py into the store.
  evidenceSrc = ../pkgs/evidence;
  evidenceCli = pkgs.writeShellApplication {
    name = "evidence";
    runtimeInputs = [
      pkgs.python3
      pkgs.git
    ];
    text = ''
      export EVIDENCE_STORE="''${EVIDENCE_STORE:-${cfg.path}}"
      exec python3 ${evidenceSrc}/evidence.py "$@"
    '';
  };
in
{
  options.services.evidence-store = {
    enable = lib.mkEnableOption "the append-only evidence store (JSONL streams; docs/superpowers/plans/2026-09-05-evidence-store.md)";
    path = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/evidence";
      description = "Directory holding the streams. Must be absolute; added to the backup paths by the host.";
    };
    owner = lib.mkOption {
      type = lib.types.str;
      default = "dalhaka";
      description = "Owner of the store; every writer runs as this user.";
    };
    group = lib.mkOption {
      type = lib.types.str;
      default = "users";
      description = "Group of the store directory (0750).";
    };
    package = lib.mkOption {
      type = lib.types.package;
      default = evidenceCli;
      defaultText = "the evidence CLI wrapping pkgs/evidence/evidence.py";
      description = "The evidence CLI other modules may reference.";
    };
  };
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = lib.hasPrefix "/" cfg.path;
        message = "services.evidence-store.path must be absolute";
      }
    ];
    systemd.tmpfiles.rules = [
      "d ${cfg.path} 0750 ${cfg.owner} ${cfg.group} -"
      "d ${cfg.path}/ledger 0750 ${cfg.owner} ${cfg.group} -"
    ];
    environment.systemPackages = [ cfg.package ];
  };
}
```

- [ ] **Step 6: Wire the flake and the host.** In `flake.nix`: add `evidenceStore = import ./nixosModules/evidenceStore.nix;` to `nixosModules`; add `self.nixosModules.evidenceStore` to `nixosConfigurations.core`'s module list next to `self.nixosModules.helm`; add `packages.${system}.evidence = pkgs.writeShellApplication { name = "evidence"; runtimeInputs = [ pkgs.python3 pkgs.git ]; text = ''exec python3 ${./pkgs/evidence}/evidence.py "$@"''; };`; add the checks below; extend both `ruff check` and `ruff format --check` lists (in `lint` and in `githooks/pre-commit`) with `pkgs/evidence tests/evidence`. In `hosts/core/default.nix` set `services.evidence-store.enable = true;` inside the existing `services = { … }` block. In `hosts/core/proton-backup.nix` append `"/var/lib/evidence"` to `paths`.

```nix
        evidence-unit =
          pkgs.runCommand "evidence-unit"
            {
              nativeBuildInputs = [
                helmPython
                # E9's bundle tests build a throwaway repo and run git diff.
                pkgs.git
              ];
            }
            ''
              export HOME=$TMPDIR
              export GIT_CONFIG_GLOBAL=$TMPDIR/.gitconfig
              mkdir -p pkgs tests docs
              cp -r ${self}/pkgs/evidence pkgs/evidence
              cp -r ${self}/tests/evidence tests/evidence
              # E2's validator resolves parked claims' decision files.
              cp -r ${self}/docs/decisions docs/decisions
              pytest tests/evidence -q
              touch $out
            '';
        evidence-eval =
          let
            c = evidenceEvalSystem.config;
          in
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.elem "d /var/lib/evidence 0750 dalhaka users -" c.systemd.tmpfiles.rules
            && nixpkgs.lib.elem "d /var/lib/evidence/ledger 0750 dalhaka users -" c.systemd.tmpfiles.rules
          ) "evidence-eval: the store and its ledger dir must be created 0750 dalhaka:users";
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.any (p: (p.pname or p.name or "") == "evidence") c.environment.systemPackages
          ) "evidence-eval: the evidence CLI must be installed";
          builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "evidence-eval-ok" { } "touch $out");
```

with, in the flake's `let`, beside `helmEvalSystem`:

```nix
      evidenceEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.evidenceStore
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            # NixOS requires every users.users entry to resolve isNormalUser
            # xor isSystemUser (same reason as helmEvalSystem).
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            services.evidence-store.enable = true;
          })
        ];
      };
```

In `host-core`, next to the Helm assertions:

```nix
          assert nixpkgs.lib.assertMsg c.services.evidence-store.enable
            "host-core: services.evidence-store must be enabled on core";
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.elem "/var/lib/evidence" c.services.proton-backup.paths
          ) "host-core: /var/lib/evidence must be a restic path (the store is the record)";
```

- [ ] **Step 7: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q` (11 passed); `git add` the new files; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `… evidence-eval`; `… host-core`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 8: Commit.**

**touches:** nixosModules/evidenceStore.nix, pkgs/evidence/evidence.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_evidence.py, flake.nix, hosts/core/default.nix, hosts/core/proton-backup.nix, githooks/pre-commit
**acceptance:** evidence-unit, evidence-eval, host-core, lint
**commit subject:** `evidence: append-only store on the host — module, CLI, schema, restic path (test: evidence-unit, evidence-eval, host-core, lint)`

### E3 (code, S) — the factory carries attribution and records its run

**dependsOn:** none (integrates in the same wave as E1; prompt text only)

**Files:**
- Modify: `tools/factory/dark-factory.js` (`IMPL_SCHEMA`, `REVIEW_SCHEMA`, `VERIFY_SCHEMA`, the implementer/fix/both reviewer/verify prompts, a recorder step after `const spent`, the header comment), `tests/factory/render.test.mjs`

**Interfaces:**
- Consumes `pkgs/evidence/evidence.py record-check` and `record runs` (E1; prompt text only).
- Produces: every implementer/fix/review result carries `task_key` (string), `round` (integer; 0 for the implementer, n for fix round n; reviewers echo the round reviewed) and `label` (the agent's own spawn label, e.g. `impl:A`, `fix:A:r1`, `review:A:r1`); the verify result carries `evidence_recorded` (boolean); the run's return gains `recorded` (boolean) and the journal a `recorder` result `{ok, ts}`. `tools/ledger/factory.py` reads `task_key`/`round`/`label` (E4).

- [ ] **Step 1: Write the failing assertions** in `tests/factory/render.test.mjs`, a new scenario after the existing ones. `runScript` takes the harness's eight positional arguments; `makeStubs(...)` returns `{agentFn, parallel, pipeline, phase, logFn, workflow, budget, calls, …}`:

```js
// Scenario: E3 — attribution in every structured result, an observation from
// the verifier, and a recorder that persists the run report.
{
  const stubs = makeStubs('ok')
  const out = await runScript(
    stubs.agentFn, stubs.parallel, stubs.pipeline, stubs.phase, stubs.logFn, stubs.workflow, stubs.budget,
    { ...fixture, tasks: [{ key: 'A', title: 'a', kind: 'code', checks: ['unit'], spec: 's' }] },
  )
  const impl = byLabel(stubs.calls, 'impl:A')
  for (const k of ['task_key', 'round', 'label']) assert.ok(impl.opts.schema.required.includes(k), `IMPL_SCHEMA requires ${k}`)
  assert.match(impl.prompt, /set task_key to "A", round to 0 and label to "impl:A"/i)
  const review = byLabel(stubs.calls, 'review:A:r1')
  for (const k of ['task_key', 'round', 'label']) assert.ok(review.opts.schema.required.includes(k), `REVIEW_SCHEMA requires ${k}`)
  assert.match(review.prompt, /set task_key to "A", round to 0 and label to "review:A:r1"/i)
  const verify = byLabel(stubs.calls, 'verify')
  assert.ok(verify.opts.schema.required.includes('evidence_recorded'), 'VERIFY_SCHEMA requires evidence_recorded')
  assert.match(verify.prompt, /pkgs\/evidence\/evidence\.py --store "\$\{EVIDENCE_STORE:-\/var\/lib\/evidence\}" record-check --name flake-check --rev \$\(git rev-parse HEAD\)/)
  assert.match(verify.prompt, /--class nix-check --src dark-factory-verify/)
  const recorder = byLabel(stubs.calls, 'recorder')
  assert.ok(recorder, 'a recorder agent is spawned at the end of the run')
  assert.match(recorder.prompt, /"kind":"factory-run"/)
  assert.match(recorder.prompt, /"delivered":true/)
  assert.match(recorder.prompt, /"key":"A","status":"approved"/)
  assert.match(recorder.prompt, /pkgs\/evidence\/evidence\.py --store "\$\{EVIDENCE_STORE:-\/var\/lib\/evidence\}" record runs --json/)
  assert.equal(recorder.opts.model, 'sonnet')
  assert.equal(out.recorded, true, 'the run reports that it was recorded')
  // the docs single-pass reviewer carries the same attribution sentence
  const stubsD = makeStubs('ok')
  await runScript(
    stubsD.agentFn, stubsD.parallel, stubsD.pipeline, stubsD.phase, stubsD.logFn, stubsD.workflow, stubsD.budget,
    { ...fixture, tasks: [{ key: 'B', title: 'b', kind: 'docs', spec: 's' }] },
  )
  assert.match(byLabel(stubsD.calls, 'review:B:r1').prompt, /set task_key to "B", round to 0 and label to "review:B:r1"/i)
}
```

In `makeStubs`'s `agentFn`, immediately after the `if (label === 'deliver')` branch (tests/factory/render.test.mjs:188-190), add:

```js
    if (label === 'recorder') {
      return { ok: true, ts: '2026-09-05T12:00:00Z' }
    }
```

- [ ] **Step 2: Run red** — `nix develop -c node tests/factory/render.test.mjs` → `AssertionError [ERR_ASSERTION]: IMPL_SCHEMA requires task_key`.

- [ ] **Step 3: Implement.** In `IMPL_SCHEMA` and `REVIEW_SCHEMA` add to `required`: `'task_key', 'round', 'label'`; properties `task_key: { type: 'string', description: 'the task key you were given, verbatim' }`, `round: { type: 'integer', description: '0 for the implementer, n for fix round n; reviewers echo the round they reviewed' }`, `label: { type: 'string', description: 'your spawn label, verbatim, as given in the prompt' }`. In `VERIFY_SCHEMA` add `evidence_recorded: { type: 'boolean', description: 'true only if evidence record-check printed a JSON row' }` to `required`. Prompt edits, each appended as one sentence: implementer — `Set task_key to "${t.key}", round to 0 and label to "impl:${t.key}" in your output.`; fix agent (label `fix:${t.key}:r${round + 1}`) — `Set task_key to "${t.key}", round to ${round + 1} and label to "fix:${t.key}:r${round + 1}" in your output.`; reviewer, in BOTH branches (the docs single-pass prompt at dark-factory.js:489 and the code adversarial prompt at :490-493) — `Set task_key to "${t.key}", round to ${round} and label to "review:${t.key}:r${round + 1}" in your output.`; verify — append step `6) Record the observation so Helm and the board can reuse it: cd ${REPO} && nix develop -c python3 pkgs/evidence/evidence.py --store "${EVIDENCE_STORE:-/var/lib/evidence}" record-check --name flake-check --rev $(git rev-parse HEAD) --ok --class nix-check --src dark-factory-verify --duration <seconds the flake check took> (use --fail instead of --ok when the flake check was red). If the store directory does not exist yet (pre-switch), report evidence_recorded=false and say so in notes — that is NOT a verify failure. evidence_recorded = true only if that printed a JSON row.` Insert the recorder block immediately AFTER `const spent = budget.spent()` (dark-factory.js:633) and before `const unreviewed = …` — the report reads `spent`:

```js
// E3: persist the run report (the paper's evidence bundle crossing the loop
// boundary). The Workflow sandbox has no filesystem, so one cheap agent
// writes the JSON and appends it to the store.
const report = {
  kind: 'factory-run',
  run_id: A.runId || null,
  plan: A.plan, prefix: A.prefix, baseline: baseline.head, integration_branch: INT_BRANCH,
  tasks: results.map(r => ({ key: r.key, status: statusOf.get(r.key), commit: r.commit || null, fixRounds: r.fixRounds })),
  verify: verify ? verify.verdict : 'none', delivered, agents, output_tokens: spent,
}
const reportJson = JSON.stringify(report)
const rec = await spawn(`You are the recorder for a dark-factory run in ${REPO}. Do exactly this: write the following JSON verbatim to ${SCRATCH}/run-report.json, then run: cd ${REPO} && nix develop -c python3 pkgs/evidence/evidence.py --store "\${EVIDENCE_STORE:-/var/lib/evidence}" record runs --json "$(cat ${SCRATCH}/run-report.json)". Report ok=true and the ts the command printed; if the store directory does not exist yet, report ok=false with the error (the orchestrator records it after the switch).
JSON: ${reportJson}`,
  { label: 'recorder', phase: 'Deliver', model: M.verify, effort: 'low', schema: { type: 'object', required: ['ok', 'ts'], properties: { ok: { type: 'boolean' }, ts: { type: 'string' } } } })
const recorded = !!(rec && rec.ok)
if (!recorded) log('run report NOT recorded — append it by hand: evidence record runs --json <the JSON in the transcript>')
```

Add `recorded,` to the returned object. Document `args.runId`, the attribution fields and the recorder in the header comment.

- [ ] **Step 4: Green** — `node tests/factory/render.test.mjs`; `nix build .#checks.x86_64-linux.factory-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**touches:** tools/factory/dark-factory.js, tests/factory/render.test.mjs
**acceptance:** factory-unit, lint
**commit subject:** `factory: every result carries task_key, round and label; the verifier records its flake check; a recorder persists the run report (test: factory-unit, lint)`

### E4 (code, S) — the ledger reads attribution and lives in the store

**dependsOn:** none

**Files:**
- Modify: `tools/ledger/factory.py` (`DEFAULT_LEDGER`, `_read_findings`), `tools/ledger/schema.md`, `tests/ledger/test_factory.py`, `docs/runbooks/lanes.md` (the "not yet built" phrase, which wraps across lines 199-200). **Do not touch `tests/ledger/fixtures/workflow/journal.jsonl`** — tests/ledger/test_factory.py:270 and :290 pin its finding count at 3; the new test builds its own journal in `tmp_path`.

**Interfaces:**
- Consumes the `task_key`/`round`/`label` fields E3 puts in review results.
- Produces `factory-findings.jsonl` rows with `task`, `round` and `label` filled when present (`null` for older runs); `DEFAULT_LEDGER = $EVIDENCE_STORE/ledger`, default `/var/lib/evidence/ledger`.

- [ ] **Step 1: Failing tests** in `tests/ledger/test_factory.py` (`load_factory()` at :38 re-executes the module by path and reads the environment at import time):

```python
def test_findings_carry_task_round_and_label_when_the_result_has_them(tmp_path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text(
        json.dumps({"type": "result", "key": "k1", "agentId": "a1", "result": {"task_key": "N9", "round": 1, "label": "review:N9:r2", "approved": False, "findings": [{"severity": "major", "file": "x.py", "issue": "bad", "fix": "fix"}], "summary": ""}}) + "\n"
        + json.dumps({"type": "result", "key": "k2", "agentId": "a2", "result": {"approved": True, "findings": [{"severity": "minor", "file": "y.py", "issue": "meh", "fix": "fix"}], "summary": ""}}) + "\n"
    )
    rows = factory._read_findings(journal, "run")
    assert (rows[0]["task"], rows[0]["round"], rows[0]["label"]) == ("N9", 1, "review:N9:r2")
    assert (rows[1]["task"], rows[1]["round"], rows[1]["label"]) == (None, None, None)


def test_default_ledger_is_under_the_evidence_store(monkeypatch):
    monkeypatch.setenv("EVIDENCE_STORE", "/tmp/ev")
    assert load_factory().DEFAULT_LEDGER == "/tmp/ev/ledger"
    monkeypatch.delenv("EVIDENCE_STORE")
    assert load_factory().DEFAULT_LEDGER == "/var/lib/evidence/ledger"
```

- [ ] **Step 2: Red** — `nix develop -c pytest tests/ledger -q -k "label or default_ledger"` → `KeyError: 'label'` and `~/strategy/ledger`.
- [ ] **Step 3: Implement** — `DEFAULT_LEDGER = os.path.join(os.environ.get("EVIDENCE_STORE", "/var/lib/evidence"), "ledger")`; in `_read_findings` set `"task": result.get("task_key")`, `"round": result.get("round")`, `"label": result.get("label")`. In `schema.md`: the location paragraph becomes "Ledger files are data, not source — they live under `/var/lib/evidence/ledger/` (`services.evidence-store`, a restic path), never committed; `EVIDENCE_STORE` overrides the root"; the `factory-findings.jsonl` example gains `"label":null` and its table row for `task`/`round`/`class` becomes "`task`/`round`/`label` from the result's `task_key`/`round`/`label` when the factory recorded them (E3, 2026-09-05); `null` for older runs; `class` still null"; the `factory-agents.jsonl` `label` row stays `null` with its reason (agent files carry no result). In `docs/runbooks/lanes.md` lines 199-200 the phrase becomes `… the raw material for the factory-wide ledger (\`tools/ledger/factory.py\`, store \`/var/lib/evidence/ledger\`) — until that …`, paragraph re-wrapped.
- [ ] **Step 4: Green** — `nix develop -c ruff format tools/ledger tests/ledger`; `nix develop -c pytest tests/ledger -q`; `nix build .#checks.x86_64-linux.ledger-unit -L --no-link`; lint gate.
- [ ] **Step 5: Commit.**

**touches:** tools/ledger/factory.py, tools/ledger/schema.md, tests/ledger/test_factory.py, docs/runbooks/lanes.md
**acceptance:** ledger-unit, lint
**commit subject:** `ledger: findings carry task, round and label; the ledger lives under the evidence store (test: ledger-unit, lint)`

### E2 (code, S) — the claims file: verified, gap, parked — validated, staleness-checked

**dependsOn:** E1

**Files:**
- Create: `docs/ledger/claims.toml`, `pkgs/evidence/claims.py`, `tests/evidence/test_claims.py`
- Modify: `flake.nix` (`checks.claims-validate`; `evidence-unit` copies `docs/ledger`), `githooks/pre-commit` (staleness call)

**Interfaces:**
- Consumes `CLASSES` from E1 (`claims.py` and `evidence.py` sit in the same directory; `claims.py` inserts its own directory into `sys.path` before `from evidence import CLASSES`).
- Produces `python3 pkgs/evidence/claims.py validate <file> [--today YYYY-MM-DD] [--repo-root DIR]` → exit 0, or exit 1 printing one `claims: <id>: <reason>` line per defect; the Python API `load(path, repo_root=None) -> list[dict]`, `validate(rows, today=None, repo_root=None) -> list[str]`, `open_gaps(rows) -> list[dict]` (sorted by `opened`, then id). `evidence bundle` (E9) reads the file through these.
- Plain-language name everywhere: **the claims file**. "The ledger" keeps meaning the token/cost ledger.

Claim row shape (TOML array of tables):

```toml
[[claim]]
id = "kebab-id"                 # ^[a-z0-9][a-z0-9-]{2,63}$, unique
text = "one sentence, falsifiable"
status = "verified"             # verified | gap | parked
class = "unit"                  # verified: any class but unmeasured
evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats test 79"   # verified: must START with check:<name>@<rev> or operator:<YYYY-MM-DD>
owner = "orchestrator"          # gap: required (orchestrator | operator | <repo key>)
opened = 2026-09-04             # TOML date
review_by = 2026-09-12          # gap: required; a gap past review_by fails the pre-commit hook
closes_by = "what measurement or check closes it"   # gap: required
decision = "docs/decisions/….md"                    # parked: required, must exist
```

- [ ] **Step 1: Failing tests** — `tests/evidence/test_claims.py`:

```python
import datetime as dt
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()


def load():
    root = HERE.parents[2]
    candidates = [root / "pkgs" / "evidence" / "claims.py", pathlib.Path("pkgs/evidence/claims.py")]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("claims", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, root


claims, ROOT = load()

GOOD = """
[[claim]]
id = "seat-denials-audited"
text = "every refused seat tool call is recorded in the transcript"
status = "verified"
class = "unit"
evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats"
owner = "orchestrator"
opened = 2026-09-04

[[claim]]
id = "effort-policy-n1"
text = "effort off costs less than medium for equal Opus verdicts"
status = "gap"
class = "unmeasured"
owner = "orchestrator"
opened = 2026-09-05
review_by = 2026-09-12
closes_by = "n >= 5 per arm, verdicts equal, tokens in the ledger"

[[claim]]
id = "cowork-tier-a"
text = "the Cowork tier-A bubble is built and verified"
status = "parked"
class = "vm"
owner = "operator"
opened = 2026-09-02
decision = "docs/decisions/2026-09-02-cowork-tier-parked.md"
"""


def write(tmp_path, text):
    p = tmp_path / "claims.toml"
    p.write_text(text)
    return p


def test_good_file_validates_and_open_gaps_sorted(tmp_path):
    rows = claims.load(write(tmp_path, GOOD), repo_root=ROOT)
    assert claims.validate(rows, today=dt.date(2026, 9, 6), repo_root=ROOT) == []
    assert [g["id"] for g in claims.open_gaps(rows)] == ["effort-policy-n1"]


def test_verified_needs_evidence_and_a_real_class(tmp_path):
    bad = GOOD.replace('evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats"\n', "").replace('class = "unit"', 'class = "unmeasured"', 1)
    errs = claims.validate(claims.load(write(tmp_path, bad), repo_root=ROOT), repo_root=ROOT)
    assert any("seat-denials-audited" in e and "evidence" in e for e in errs)
    assert any("seat-denials-audited" in e and "unmeasured" in e for e in errs)


def test_verified_evidence_must_be_check_or_operator_form(tmp_path):
    bad = GOOD.replace('evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats"', 'evidence = "trust me, I looked at it"')
    errs = claims.validate(claims.load(write(tmp_path, bad), repo_root=ROOT), repo_root=ROOT)
    assert any("seat-denials-audited" in e and "must start with" in e for e in errs)
    ok = GOOD.replace('evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats"', 'evidence = "operator:2026-09-04 drill step 7 in Firefox"')
    assert claims.validate(claims.load(write(tmp_path, ok), repo_root=ROOT), repo_root=ROOT) == []


def test_gap_needs_owner_review_by_closes_by(tmp_path):
    bad = GOOD.replace('closes_by = "n >= 5 per arm, verdicts equal, tokens in the ledger"\n', "").replace("review_by = 2026-09-12\n", "")
    errs = claims.validate(claims.load(write(tmp_path, bad), repo_root=ROOT), repo_root=ROOT)
    assert any("effort-policy-n1" in e and "closes_by" in e for e in errs)
    assert any("effort-policy-n1" in e and "review_by" in e for e in errs)


def test_stale_gap_fails_only_with_today(tmp_path):
    rows = claims.load(write(tmp_path, GOOD), repo_root=ROOT)
    assert claims.validate(rows, repo_root=ROOT) == []
    errs = claims.validate(rows, today=dt.date(2026, 9, 13), repo_root=ROOT)
    assert errs == ["claims: effort-policy-n1: gap past review_by 2026-09-12 (today 2026-09-13) — extend it with a reason or close it"]


def test_parked_needs_an_existing_decision_and_ids_are_unique(tmp_path):
    bad = GOOD.replace("2026-09-02-cowork-tier-parked.md", "2026-09-02-nope.md").replace('id = "effort-policy-n1"', 'id = "seat-denials-audited"')
    errs = claims.validate(claims.load(write(tmp_path, bad), repo_root=ROOT), repo_root=ROOT)
    assert any("cowork-tier-a" in e and "decision" in e for e in errs)
    assert any("duplicate id" in e for e in errs)


def test_repo_claims_file_validates_structurally():
    rows = claims.load(ROOT / "docs" / "ledger" / "claims.toml", repo_root=ROOT)
    assert claims.validate(rows, repo_root=ROOT) == []
    assert len(rows) >= 24
```

- [ ] **Step 2: Red** — `nix develop -c pytest tests/evidence/test_claims.py -q` → `StopIteration` (no `claims.py`).
- [ ] **Step 3: Write `pkgs/evidence/claims.py`**

```python
"""claims — validate docs/ledger/claims.toml, the claims file (plan 2026-09-05-evidence-store, E2).

A claim is verified only by a named check at a revision (check:<name>@<rev>) or an
operator-judged drill (operator:<date>) with an evidence class; a gap names its
owner, a review date and what closes it; a parked claim names its decision.
Structure is checked in the flake (no clock in the sandbox); staleness (--today)
in the pre-commit hook and by `evidence bundle`, where a real clock exists.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import sys

import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evidence import CLASSES

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
EVIDENCE_RE = re.compile(r"^(check:[a-z][a-z0-9-]{0,31}@[0-9a-f]{7,40}\b|operator:\d{4}-\d{2}-\d{2}\b)")
STATUSES = ("verified", "gap", "parked")


def load(path, repo_root=None) -> list[dict]:
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("claim", [])


def validate(rows: list[dict], today: datetime.date | None = None, repo_root=None) -> list[str]:
    errs: list[str] = []
    seen: set[str] = set()
    root = pathlib.Path(repo_root) if repo_root else None
    for r in rows:
        cid = str(r.get("id", "<no id>"))

        def say(msg, cid=cid):
            errs.append(f"claims: {cid}: {msg}")

        if not ID_RE.match(cid):
            say("id must match ^[a-z0-9][a-z0-9-]{2,63}$")
        if cid in seen:
            say("duplicate id")
        seen.add(cid)
        for key in ("text", "status", "class", "owner", "opened"):
            if key not in r:
                say(f"missing {key}")
        status = r.get("status")
        if status not in STATUSES:
            say(f"status must be one of {', '.join(STATUSES)}")
        if r.get("class") not in CLASSES:
            say(f"class must be one of {', '.join(CLASSES)}")
        if not isinstance(r.get("opened"), datetime.date):
            say("opened must be a TOML date")
        if status == "verified":
            ev = r.get("evidence")
            if not ev:
                say("verified claim needs evidence (check:<name>@<rev> … or operator:<date> …)")
            elif not EVIDENCE_RE.match(str(ev)):
                say(f"evidence must start with 'check:<name>@<rev>' or 'operator:<date>', got {ev!r}")
            if r.get("class") == "unmeasured":
                say("verified claim cannot have class unmeasured")
        if status == "gap":
            for key in ("owner", "review_by", "closes_by"):
                if not r.get(key):
                    say(f"gap needs {key}")
            rb = r.get("review_by")
            if rb is not None and not isinstance(rb, datetime.date):
                say("review_by must be a TOML date")
            if today is not None and isinstance(rb, datetime.date) and rb < today:
                say(f"gap past review_by {rb} (today {today}) — extend it with a reason or close it")
        if status == "parked":
            dec = r.get("decision")
            if not dec:
                say("parked claim needs decision")
            elif root is not None and not (root / dec).exists():
                say(f"decision file does not exist: {dec}")
    return errs


def open_gaps(rows: list[dict]) -> list[dict]:
    return sorted((r for r in rows if r.get("status") == "gap"), key=lambda r: (r.get("opened"), r.get("id")))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="claims")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("file")
    v.add_argument("--today", help="YYYY-MM-DD; enables the staleness rule")
    v.add_argument("--repo-root", default=None)
    a = p.parse_args(argv)
    root = a.repo_root or str(pathlib.Path(a.file).resolve().parents[2])
    today = datetime.date.fromisoformat(a.today) if a.today else None
    errs = validate(load(a.file, repo_root=root), today=today, repo_root=root)
    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Seed `docs/ledger/claims.toml`** with these rows (facts from the board, reviews and the 2026-09-05 environment review; `opened` = the day first recorded; every `text` one falsifiable sentence):

| id | status | class | owner | evidence / decision / closes_by (review_by) |
|---|---|---|---|---|
| `seat-denials-audited` | verified | unit | orchestrator | `check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats (record slicing turns test 79 red)` |
| `broker-denies-messages-path` | verified | vm | orchestrator | `check:lane-vm@abef7fe tests/integration/lane-vm.nix (POST /api/v1/messages denied before injection)` |
| `effort-override-is-real` | verified | unit | orchestrator | `check:unit@79f4c0a tests/unit/70-dsh-openrouter.bats (preserve test discriminates)` |
| `effort-policy-n1` | gap | unmeasured | orchestrator | "n ≥ 5 per arm off vs medium through the seat driver, Opus verdicts equal, tokens in the ledger" (2026-09-12) |
| `reasoning-tokens-not-itemised` | gap | unmeasured | orchestrator | "a usage record for the openrouter route carries reasoning tokens, or the ledger documents that the route never will" (2026-09-19) |
| `fake-upstream-proves-what-seat-sends` | gap | unmeasured | orchestrator | "one live probe per effort level against OpenRouter with the response's reasoning field recorded" (2026-09-19) |
| `ledger-attribution` | gap | unmeasured | orchestrator | "factory-findings.jsonl rows carry task, round and label for a real run (E3+E4)" (2026-09-12) |
| `factory-run-report-persisted` | gap | unmeasured | orchestrator | "runs.jsonl holds one factory-run row per dark-factory run (E3)" (2026-09-12) |
| `flake-check-tile-covers-head` | gap | unmeasured | orchestrator | "the tile is green when an observation covers a rev docs-equivalent to HEAD (E5)" (2026-09-12) |
| `drift-exact-measure` | gap | unmeasured | orchestrator | "nix store diff-closures between the live system and the toplevel built at HEAD lists only the nixos-version file; the docs-only rule is the proxy (store paths cannot match: the toplevel bakes the commit id)" (2026-09-19) |
| `evidence-flock-effect-unmeasured` | gap | unmeasured | orchestrator | "a test that fails without the flock, or a note that Linux O_APPEND makes it belt-and-braces" (2026-10-03) |
| `o4-framing-test` | gap | browser | operator | "the operator loads localhost:7700 inside a frame and records the refusal" (2026-09-12) |
| `d5-activity-export` | gap | operator | operator | "~/strategy/ledger/openrouter-activity.csv exists and rollup --activity parses it" (2026-09-12) |
| `s12-commit-metadata-decision` | gap | operator | operator | "a decision file on mixed trailers and non-check subjects (nixos-skill round 2 report)" (2026-09-12) |
| `xhigh-restore-or-keep-medium` | gap | operator | operator | "the seat's saved level is set on purpose and the backup file is deleted" (2026-09-12) |
| `m3-comfy-angle-aimdo` | gap | unmeasured | orchestrator | "comfy_angle imports and aimdo.so loads in the packaged ComfyUI, or both are documented as excluded" (2026-09-19) |
| `seat-key-exception-undecided` | gap | unmeasured | operator | review invariants-1: "a decision file scopes the seat's plaintext-key, no-broker exception (which agent, which data class, compensating controls, what closes it) or the seat is fronted by a broker instance" (2026-09-12) |
| `declared-agents-zero` | gap | eval | orchestrator | review invariants-6: "services.baskets.agents on core names the harnesses that actually run, or a decision records that A1–A4 have no live instance" (2026-09-19) |
| `uid1000-can-switch-profile` | gap | unmeasured | orchestrator | review invariants-3: "the switch needs a desktop password (polkit auth_admin_keep, Helm Home HH2); until then the seat guard refuses the control port (R8)" (2026-09-19) |
| `nixpkgs-host-pin-age` | gap | operator | operator | review hygiene-2: "nixpkgs-host bumped to a current 25.05 head with flake check, VM tests and a closure diff; a monthly pin-age item on the board" (2026-10-05) |
| `js-formatter-linter-missing` | gap | unmeasured | orchestrator | review hygiene-1: "tools/factory/dark-factory.js and tests/factory/*.mjs pass a JS formatter and linter in treefmt and the lint check" (2026-09-19) |
| `basket-verify-cannot-bind-payload` | gap | unmeasured | orchestrator | review r2-2-5: "encrypt packs once (hash and ciphertext from the same bytes), or verify states that payload↔content binding needs the identity" (2026-09-19) |
| `forbidden-list-single-source` | gap | unmeasured | orchestrator | review invariants-5: "the local-only path list is generated from Nix and the three copies are proven identical (R9 first proves they agree)" (2026-09-19) |
| `lane-ledger-and-broker-audit-unbacked` | gap | unmeasured | orchestrator | review r2-4-1/r2-4-2: "/var/lib/lanes/*/ledger.jsonl and /var/lib/egress-broker/*/audit.jsonl are in the restic paths, or a decision says they are disposable" (2026-09-19) |
| `cowork-tier-a-parked` | parked | vm | operator | decision `docs/decisions/2026-09-02-cowork-tier-parked.md` |
| `helm-workspace-buttons-parked` | parked | eval | operator | decision `docs/decisions/2026-09-04-helm-workspace-buttons-removed.md` |

- [ ] **Step 5: Wire the check and the hook.** `flake.nix`:

```nix
        claims-validate =
          pkgs.runCommand "claims-validate"
            {
              nativeBuildInputs = [ pkgs.python3 ];
            }
            ''
              cp -r ${self} src && cd src
              python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --repo-root .
              touch $out
            '';
```

and in `evidence-unit` add `cp -r ${self}/docs/ledger docs/ledger` after the `docs/decisions` copy (the repo-claims test reads it). `githooks/pre-commit` (after the ruff lines): `python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)" --repo-root .` — the hook runs in the devShell where python3 exists and the clock is real.

- [ ] **Step 6: Green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q`; `git add docs/ledger pkgs/evidence/claims.py tests/evidence/test_claims.py`; `nix build .#checks.x86_64-linux.claims-validate -L --no-link`; `… evidence-unit`; `nix develop -c githooks/pre-commit`. Then prove the hook is load-bearing once: set one gap's `review_by` to `2026-01-01`, run the hook, see `claims: <id>: gap past review_by`, restore.
- [ ] **Step 7: Commit.**

**touches:** docs/ledger/claims.toml, pkgs/evidence/claims.py, tests/evidence/test_claims.py, flake.nix, githooks/pre-commit
**acceptance:** evidence-unit, claims-validate, lint
**commit subject:** `evidence: claims file — verified, gap, parked; shape checked in the flake, staleness in the hook (test: evidence-unit, claims-validate, lint)`

### E5 (code, M) — Helm reads observations: flake-check covers HEAD, drift tolerates docs-only, the nightly records itself

**dependsOn:** E1, R4 (both edit `nixosModules/helm.nix` and `flake.nix`'s helm checks)

**Files:**
- Modify: `pkgs/helm/collect.py` (`_docs_equivalent`, `_check_rows`, `_live_rev`, `tile_flake_check`, `_tile_flake_check_from_file`, `tile_drift`), `tests/helm/test_collect.py`, `nixosModules/helm.nix` (`evidenceDir` option, `configJsonValue` internal option, `config.json` key, local `evidenceCli`, `flakeCheck` script, both units' `ReadWritePaths` and `EVIDENCE_STORE`), `flake.nix` (`helm-eval` assertions), `docs/runbooks/helm.md` (flake-check, drift, broker and tile-count paragraphs), `docs/runbooks/switch-helm-gaming.md` (§3 expected tiles)

**Interfaces:**
- Consumes `checks.jsonl` rows per `pkgs/evidence/SCHEMA.md` and the `evidence` CLI (E1).
- Produces: `cfg["evidence_dir"]` (string) in `/etc/helm/config.json`; option `services.helm.evidenceDir` (str, default `"/var/lib/evidence"`); internal option `services.helm.configJsonValue` (the attrset rendered into config.json, so eval checks can assert on it without reading a derivation); tile summaries of the form `flake check ok @<rev12> covers HEAD (nix-check, helm-nightly, 4.1h ago)`; detail keys `head`, `live`, `for_head`, `for_live`, `latest`, `age_h`; drift detail key `docs_only_ahead`.

- [ ] **Step 1: Failing tests** in `tests/helm/test_collect.py`. First add `"evidence_dir": str(tmp_path / "evidence")` to `base_cfg`. Then:

```python
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
        fh.write(json.dumps({"v": 1, "ts": ts, "kind": "check", "name": "flake-check", "rev": rev, "ok": ok, "class": cls, "src": src, "duration_s": 100}) + "\n")


def test_flake_check_green_when_observation_covers_head_exactly(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_H, set()))
    obs(tmp_path, REV_H, True, "2026-09-03T04:00:00Z")
    t = collect.tile_flake_check(cfg, NOW)
    assert t["status"] == "ok" and "covers HEAD" in t["summary"] and REV_H[:12] in t["summary"]


def test_flake_check_green_when_observation_is_docs_equivalent_to_head(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_L, {frozenset({REV_O, REV_H})}))
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
    assert t["status"] == "warn" and "covers the live system" in t["summary"] and "unchecked" in t["summary"]


def test_flake_check_amber_when_covering_observation_is_old(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_H, set()))
    obs(tmp_path, REV_H, True, "2026-08-30T04:00:00Z")
    t = collect.tile_flake_check(cfg, NOW)
    assert t["status"] == "warn" and "old" in t["summary"]


def test_flake_check_falls_back_to_file_when_store_is_empty(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table("abc", "abc", set()))
    pathlib.Path(cfg["flake_check_file"]).write_text(json.dumps({"rev": "abc", "ok": True, "exit": 0, "started": "2026-09-03T03:00:00Z", "duration_s": 100, "log_tail": ""}))
    assert collect.tile_flake_check(cfg, NOW)["status"] == "ok"


def test_drift_docs_only_ahead_is_ok_and_named(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_L, {frozenset({REV_L, REV_H})}))
    t = collect.tile_drift(cfg, NOW)
    assert t["status"] == "ok" and "except docs" in t["summary"] and t["detail"]["docs_only_ahead"] is True
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_L, {frozenset({REV_L, REV_H})}, porcelain=" M x\n"))
    assert collect.tile_drift(cfg, NOW)["status"] == "warn"
    monkeypatch.setattr(collect, "run", git_table(REV_H, REV_L, set()))
    assert collect.tile_drift(cfg, NOW)["status"] == "fail"
```

Also update `test_drift_branches`' inner `table()` to answer a `diff` argv with `cp("", 1)` (different) so its `def`≠`abc` case still reads fail, and change `test_flake_check_fresh_stale_missing` to `monkeypatch.setattr(collect, "run", git_table("abc", "abc", set()))` (the tile now asks `nixos-version` too).

- [ ] **Step 2: Red** — `nix develop -c pytest tests/helm -q` → the seven new tests fail on `t["status"]` (the old rule reads `warn`/`fail`); everything else stays green (117 today).
- [ ] **Step 3: Implement in `collect.py`**

```python
def _docs_equivalent(cfg, a: str, b: str) -> bool:
    """True when a and b differ only under docs/ or in *.md (D4). Exit 128
    (unknown revision) counts as different."""
    if a == b:
        return True
    cp = run(["git", "-C", cfg["repo"], "diff", "--quiet", a, b, "--", ".", ":!docs", ":!*.md"])
    return cp.returncode == 0


def _check_rows(cfg, name: str) -> list[dict]:
    """Observations for one check name from <evidence_dir>/checks.jsonl, oldest
    first, torn lines skipped, capped to the newest 50."""
    path = pathlib.Path(cfg.get("evidence_dir", "/var/lib/evidence")) / "checks.jsonl"
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
        if r.get("kind") == "check" and r.get("name") == name and isinstance(r.get("rev"), str):
            rows.append(r)
    rows.sort(key=lambda r: r.get("ts", ""))
    return rows[-50:]


def _live_rev(cfg) -> str | None:
    try:
        cp = run([cfg.get("nixos_version_bin", "nixos-version"), "--configuration-revision"])
    except FileNotFoundError:
        return None
    if cp.returncode != 0:
        return None
    live = cp.stdout.strip()
    return None if live in ("", "dirty") else live.removesuffix("-dirty")


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
    detail = {"head": head, "live": live, "for_head": for_head, "for_live": for_live, "latest": latest}

    def age_h(r):
        return round((now - _parse_iso(r["ts"])).total_seconds() / 3600.0, 2)

    if for_head is not None:
        detail["age_h"] = age_h(for_head)
        who = f"{for_head.get('class', '?')}, {for_head.get('src', '?')}"
        if not for_head.get("ok"):
            return "fail", f"flake check FAILED @{for_head['rev'][:12]} covers HEAD ({who})", detail
        if detail["age_h"] >= 48:
            return "warn", f"flake check ok @{for_head['rev'][:12]} covers HEAD but is {detail['age_h']:.1f}h old", detail
        return "ok", f"flake check ok @{for_head['rev'][:12]} covers HEAD ({who}, {detail['age_h']:.1f}h ago)", detail
    if for_live is not None and for_live.get("ok"):
        return "warn", f"flake check ok @{for_live['rev'][:12]} covers the live system; HEAD {str(head)[:12]} unchecked", detail
    if not latest.get("ok"):
        return "fail", f"flake check FAILED @{latest['rev'][:12]} ({latest.get('src', '?')})", detail
    return "warn", f"flake check ok @{latest['rev'][:12]} covers neither HEAD nor live", detail
```

`_tile_flake_check_from_file(cfg, now, head)` is today's body (from `path = pathlib.Path(cfg["flake_check_file"])` on) with `head` passed in instead of re-derived; it keeps the file-based rule for hosts with no store yet. In `tile_drift`, replace the final `return "fail", …` with:

```python
    if _docs_equivalent(cfg, base, head):
        detail["docs_only_ahead"] = True
        if dirty_live:
            return "warn", "switched from a dirty tree", detail
        if tree_dirty:
            return "warn", "working tree has uncommitted changes", detail
        return "ok", f"live {base[:12]} = HEAD {head[:12]} except docs", detail
    detail["docs_only_ahead"] = False
    return "fail", f"live {base[:12]} ≠ HEAD {head[:12]}", detail
```

- [ ] **Step 4: Module.** In `nixosModules/helm.nix`:
  - options: `evidenceDir = lib.mkOption { type = lib.types.str; default = "/var/lib/evidence"; description = "Where helm-flake-check records observations and the tiles read them (services.evidence-store.path)."; };` and `configJsonValue = lib.mkOption { internal = true; type = lib.types.attrs; default = { }; description = "The attrset rendered into /etc/helm/config.json; asserted by helm-eval without reading a derivation."; };`
  - hoist the attrset currently inlined in `configJson` into `configJsonAttrs = { … } // lib.optionalAttrs cfg.control.enable { … };`, add `evidence_dir = cfg.evidenceDir;` to it, keep `configJson = (pkgs.formats.json { }).generate "helm-config.json" configJsonAttrs;`, and set `services.helm.configJsonValue = configJsonAttrs;` in the module's `config` block.
  - a local recorder in the `let` — literal, not "the same as E1's" (helm.nix's `cfg` is `services.helm`, which has no `path`):

```nix
  # E5: the evidence recorder the nightly flake check calls. Embeds the whole
  # pkgs/evidence directory (evidence.py imports its sibling claims.py) and
  # deliberately sets no EVIDENCE_STORE default: the unit sets it and the
  # script passes --store explicitly.
  evidenceCli = pkgs.writeShellApplication {
    name = "evidence";
    runtimeInputs = [
      pkgs.python3
      pkgs.git
    ];
    text = ''exec python3 ${../pkgs/evidence}/evidence.py "$@"'';
  };
```

  - `flakeCheck.runtimeInputs` gains `evidenceCli`; the script becomes:

```bash
      out=/var/lib/helm/flake-check.json
      cd "$HELM_REPO"
      rev=$(git rev-parse HEAD 2>/dev/null || echo unknown)
      started=$(date -u +%FT%TZ); t0=$(date +%s)
      set +e
      log=$(nix flake check --offline --no-update-lock-file -L 2>&1); code=$?
      set -e
      dur=$(( $(date +%s) - t0 ))
      tail_txt=$(printf '%s\n' "$log" | tail -n 40)
      ok=false; [ "$code" -eq 0 ] && ok=true
      jq -n --arg rev "$rev" --argjson ok "$ok" --argjson exit "$code" --arg started "$started" --argjson dur "$dur" --arg tail "$tail_txt" \
        '{rev:$rev, ok:$ok, exit:$exit, started:$started, duration_s:$dur, log_tail:$tail}' >"$out.tmp"
      chmod 0640 "$out.tmp"; mv "$out.tmp" "$out"
      # E5: the observation the tiles and the bundle reuse (pkgs/evidence/SCHEMA.md).
      if [[ "$rev" =~ ^[0-9a-f]{40}$ ]]; then
        okflag=--fail; [ "$code" -eq 0 ] && okflag=--ok
        printf '%s\n' "$tail_txt" >"$out.tail"
        evidence --store "''${EVIDENCE_STORE:-${cfg.evidenceDir}}" record-check --name flake-check --rev "$rev" "$okflag" --class nix-check --src helm-nightly --duration "$dur" --log-tail-file "$out.tail" \
          || echo "helm-flake-check: observation not recorded (store missing until the switch?)" >&2
        rm -f "$out.tail"
      fi
```

  - both `helm-collect` and `helm-flake-check` get `environment.EVIDENCE_STORE = cfg.evidenceDir;` and `"-${cfg.evidenceDir}"` appended to their `ReadWritePaths`.
  - In `flake.nix` `helm-eval` add three assertions (red before the module change):

```nix
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.elem "-/var/lib/evidence" c.systemd.user.services.helm-flake-check.serviceConfig.ReadWritePaths
            && nixpkgs.lib.elem "-/var/lib/evidence" c.systemd.user.services.helm-collect.serviceConfig.ReadWritePaths
          ) "helm-eval: both Helm units must be able to write the evidence store";
          assert nixpkgs.lib.assertMsg (
            (c.services.helm.configJsonValue.evidence_dir or null) == "/var/lib/evidence"
          ) "helm-eval: /etc/helm/config.json must carry evidence_dir = /var/lib/evidence";
          assert nixpkgs.lib.assertMsg (
            c.services.helm.evidenceDir == "/var/lib/evidence"
          ) "helm-eval: services.helm.evidenceDir must default to /var/lib/evidence";
```

- [ ] **Step 5: Runbooks.** `docs/runbooks/helm.md`: (a) the **flake-check** paragraph now says green means "a recorded full flake check covers a revision that differs from HEAD only in docs", names the three writers (nightly, seat integrator, factory verifier), says amber means "covers the live system but not HEAD, or older than 48 h", red means "the newest covering check failed, or nothing has ever been recorded and the nightly file is missing", and drops the sentence that the tile is red right after a switch; (b) the **drift** paragraph adds "Green also when HEAD is ahead of the live system only in docs/ or *.md files: a switch would activate the same system"; (c) the **broker** paragraph (review helm-runbooks-5): green with 24 h allow/deny counts is the normal reading now that the `openrouter` instance exists; grey means Helm could not read the instance's `audit.jsonl` and is a fault; (d) the heading "The nine tiles" and line 6 become "nine health tiles plus the Profile card" (review helm-runbooks-7). `docs/runbooks/switch-helm-gaming.md` §3: flake-check is **amber until a covering check is recorded**, not red; broker is **green**, not grey.
- [ ] **Step 6: Green** — `nix develop -c ruff format pkgs/helm tests/helm`; `nix develop -c pytest tests/helm -q`; `nix build .#checks.x86_64-linux.helm-unit -L --no-link`; `… helm-eval`; `… host-core`; lint gate. Then prove the docs-only rule by mutation once: change `":!*.md"` to `":!*.markdown"` in `_docs_equivalent` and run `pytest -k docs_equivalent_to_head` → the test fails on `assert t["status"] == "ok"` (the fake's pathspec assertion is raised inside the tile and the `tile()` decorator converts it to status `unknown`, pkgs/helm/collect.py:79); restore.
- [ ] **Step 7: Commit.**

**touches:** pkgs/helm/collect.py, tests/helm/test_collect.py, nixosModules/helm.nix, flake.nix, docs/runbooks/helm.md, docs/runbooks/switch-helm-gaming.md
**acceptance:** helm-unit, helm-eval, host-core, lint
**commit subject:** `helm: flake-check reads recorded checks and covers HEAD across docs-only commits; drift tolerates docs-only; the nightly records itself (test: helm-unit, helm-eval, host-core, lint)`

### E7 (code, S) — the seat integrator records every check it runs

**dependsOn:** E1

**Files:**
- Modify: `tools/factory/seat/factory-integrate`, `tools/factory/seat/factory-lib.sh` (one helper), `tools/factory/seat/README.md` (one paragraph), `tests/unit/80-seat-driver.bats`

**Interfaces:**
- Consumes the `evidence` CLI (E1) through a new helper `factory_record_check <name> <rev> ok|fail <duration_s>` in `factory-lib.sh`, which runs `${FACTORY_EVIDENCE_CMD:-factory_python3 "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py"} --store "${EVIDENCE_STORE:-/var/lib/evidence}" record-check --name … --rev … --ok|--fail --class nix-check --src seat-integrate --duration …` and never fails the caller (a recording failure is logged, the check verdict stands).
- Produces one `checks` row per check run against `integ/<run>`'s head; the `FACTORY_CHECK_CMD` path records under the name `custom`.

- [ ] **Step 1: Failing bats test** in `tests/unit/80-seat-driver.bats` (the fixture repo needs a LOCAL committer identity: `factory_set_identity` copies it from the source repo's config; the stub's shebang uses `$REAL_BASH` because the sandbox has no `/usr/bin/env`):

```bash
@test "factory-integrate records one check observation per check it runs, at the integration head" {
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  git -C "$src" commit -q --allow-empty -m "init"
  git clone -q "$src" "$root/base/src"
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  echo x >"$root/ws/r1/K1/x"; git -C "$root/ws/r1/K1" add x
  git -C "$root/ws/r1/K1" commit -q -m "k1: add x (test: unit, lint)"
  rec="$BATS_TEST_TMPDIR/rec.sh"; log="$BATS_TEST_TMPDIR/rec.log"
  printf '#!%s\nprintf "%%s\\n" "$*" >>%q\n' "$REAL_BASH" "$log" >"$rec"
  chmod +x "$rec"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true FACTORY_EVIDENCE_CMD="$rec" EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev" \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 0 ]
  head=$(git -C "$root/base/src" rev-parse integ/r1)
  run cat "$log"
  [[ "$output" =~ ^--store\ $BATS_TEST_TMPDIR/ev\ record-check\ --name\ custom\ --rev\ $head\ --ok\ --class\ nix-check\ --src\ seat-integrate\ --duration\ [0-9]+$ ]]
}
```

- [ ] **Step 2: Red** — `nix develop -c bats tests/unit/80-seat-driver.bats` → the new case fails at `cat "$log"` (the integrator exits 0 and records nothing).
- [ ] **Step 3: Implement.** `factory-lib.sh`:

```bash
# Record one check observation in the evidence store (plan 2026-09-05-evidence-store, E7).
# Never fails the caller: a recording problem is logged and the check verdict stands.
# Usage: factory_record_check <name> <rev> ok|fail <duration_s>
factory_record_check() {
  local name=$1 rev=$2 verdict=$3 dur=$4 flag=--fail
  [ "$verdict" = ok ] && flag=--ok
  local store=${EVIDENCE_STORE:-/var/lib/evidence}
  if [ -n "${FACTORY_EVIDENCE_CMD:-}" ]; then
    "$FACTORY_EVIDENCE_CMD" --store "$store" record-check --name "$name" --rev "$rev" "$flag" --class nix-check --src seat-integrate --duration "$dur" ||
      factory_log "evidence: could not record $name@$rev ($?)"
  else
    factory_python3 "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py" --store "$store" record-check --name "$name" --rev "$rev" "$flag" --class nix-check --src seat-integrate --duration "$dur" ||
      factory_log "evidence: could not record $name@$rev ($?)"
  fi
}
```

In `factory-integrate`, compute `head=$(git -C "$base" rev-parse "integ/$run")` after the merge loop; around each check: `t0=$(date +%s)`, run, `dur=$(( $(date +%s) - t0 ))`, then `factory_record_check "$chk" "$head" ok "$dur"` or `… fail "$dur"` (the `FACTORY_CHECK_CMD` branch records the name `custom`). README, under "Fast-forwarding the real branch": every check the integrator runs is recorded in the evidence store with the integration head, so Helm's flake-check tile and `evidence bundle` see it once the branch is fast-forwarded; `FACTORY_EVIDENCE_CMD` overrides the recorder (tests), `EVIDENCE_STORE` the directory.
- [ ] **Step 4: Green** — the bats file passes; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate (shellcheck covers both scripts).
- [ ] **Step 5: Commit.**

**touches:** tools/factory/seat/factory-integrate, tools/factory/seat/factory-lib.sh, tools/factory/seat/README.md, tests/unit/80-seat-driver.bats
**acceptance:** unit, lint
**commit subject:** `factory: the seat integrator records every check it runs as an observation at the integration head (test: unit, lint)`

### E6 (code, S) — Helm keeps a verdict history: every tile says since when, prints its verdict word, times read in local time; status.json gains a schema, the active profile and the generation

**dependsOn:** E5

**Files:**
- Modify: `pkgs/helm/collect.py` (`_append_status_row`, `_status_rows`, `record_status`, `annotate_since`, `collect_all`, `main`, `render_html`, `render_text`), `tests/helm/test_collect.py`, `docs/runbooks/helm.md` (one paragraph)

**Interfaces:**
- Consumes `cfg["evidence_dir"]` (E5) and the `helm-status` stream shape from `pkgs/evidence/SCHEMA.md`.
- Produces: a `helm-status` row when any tile's verdict changed since the last row or the last row is ≥ 3600 s old (`reason` `change|heartbeat`); each tile in `status.json` gains `since` (RFC3339 UTC of the first row of the current unbroken run of that verdict, or `generated_at` when the stream is empty); the document gains `"schema": 1`, `"active_profile"` (the marker file, `cfg.get("profile_marker", "/etc/helm/profile")`, via the `read_text` seam; `"unknown"` on error) and `"generation"` (basename of `/nix/var/nix/profiles/system`, via a new seam `system_generation()`; `None` on error) — review helm-code-3; each tile header prints its verdict word (`<h2>drift <span class="verdict">FAIL</span></h2>`, review helm-runbooks-4); the header shows local time with the UTC in brackets and each tile shows `since 07:10 CDT`.

- [ ] **Step 1: Failing tests** (helper named `_status_of` — `_status` already exists at tests/helm/test_collect.py:685; the local-time test uses a POSIX `TZ` string because the build sandbox has no zoneinfo):

```python
def _status_of(names_to_status, now):
    return {"generated_at": now.isoformat(), "hostname": "h", "interval_s": 300,
            "tiles": [{"name": n, "status": s, "summary": "", "detail": {}, "checked_at": now.isoformat()} for n, s in names_to_status.items()]}


def test_record_status_writes_on_change_and_heartbeat_only(tmp_path):
    cfg = base_cfg(tmp_path)
    t0 = NOW
    assert collect.record_status(cfg, _status_of({"drift": "ok"}, t0), t0)["reason"] == "change"
    assert collect.record_status(cfg, _status_of({"drift": "ok"}, t0), t0 + dt.timedelta(minutes=5)) is None
    assert collect.record_status(cfg, _status_of({"drift": "fail"}, t0), t0 + dt.timedelta(minutes=10))["reason"] == "change"
    assert collect.record_status(cfg, _status_of({"drift": "fail"}, t0), t0 + dt.timedelta(minutes=75))["reason"] == "heartbeat"
    rows = [json.loads(line) for line in (tmp_path / "evidence" / "helm-status.jsonl").read_text().splitlines()]
    assert [r["reason"] for r in rows] == ["change", "change", "heartbeat"] and rows[-1]["tiles"] == {"drift": "fail"}


def test_annotate_since_uses_first_row_of_current_run(tmp_path):
    cfg = base_cfg(tmp_path)
    t0 = NOW
    collect.record_status(cfg, _status_of({"drift": "ok", "gpu": "ok"}, t0), t0)
    collect.record_status(cfg, _status_of({"drift": "fail", "gpu": "ok"}, t0), t0 + dt.timedelta(hours=1))
    collect.record_status(cfg, _status_of({"drift": "fail", "gpu": "ok"}, t0), t0 + dt.timedelta(hours=3))
    st = _status_of({"drift": "fail", "gpu": "ok"}, t0 + dt.timedelta(hours=3, minutes=5))
    collect.annotate_since(cfg, st)
    by = {t["name"]: t["since"] for t in st["tiles"]}
    assert by["drift"] == "2026-09-03T09:00:00Z" and by["gpu"] == "2026-09-03T08:00:00Z"


def test_annotate_since_without_history_uses_generated_at(tmp_path):
    st = _status_of({"drift": "ok"}, NOW)
    collect.annotate_since(base_cfg(tmp_path), st)
    assert st["tiles"][0]["since"] == NOW.isoformat()


def test_render_shows_verdict_word_since_and_local_time(monkeypatch, tmp_path):
    import time

    monkeypatch.setenv("TZ", "CST6CDT,M3.2.0,M11.1.0")  # POSIX rule: no zoneinfo needed in the sandbox
    time.tzset()
    try:
        st = _status_of({"drift": "fail"}, NOW)
        st["tiles"][0]["since"] = "2026-09-03T07:30:00Z"
        html_out = collect.render_html(st, NOW)
        assert '<h2>drift <span class="verdict">FAIL</span></h2>' in html_out
        assert "since 02:30 CDT" in html_out and "generated 03:00:00 CDT" in html_out and "08:00:00Z" in html_out
        assert "since" in collect.render_text(st)
        # every verdict word survives as text, colour is only reinforcement
        for word in ("OK", "WARN", "FAIL", "UNKNOWN"):
            st2 = _status_of({"a": "ok", "b": "warn", "c": "fail", "d": "unknown"}, NOW)
            assert f'<span class="verdict">{word}</span>' in collect.render_html(st2, NOW)
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()


def test_collect_all_document_has_schema_profile_and_generation(monkeypatch, tmp_path):
    monkeypatch.setattr(collect, "run", fake_run({}))
    monkeypatch.setattr(collect, "read_text", lambda p: "gaming\n" if p.endswith("helm/profile") else (_ for _ in ()).throw(OSError(p)))
    monkeypatch.setattr(collect, "system_generation", lambda: "system-39-link")
    st = collect.collect_all(base_cfg(tmp_path), NOW)
    assert st["schema"] == 1 and st["active_profile"] == "gaming" and st["generation"] == "system-39-link"
```

- [ ] **Step 2: Red** — `AttributeError: module 'collect' has no attribute 'record_status'`.
- [ ] **Step 3: Implement**

```python
def system_generation() -> str | None:
    """Basename of the live system profile link; a seam for tests."""
    try:
        return os.path.basename(os.readlink("/nix/var/nix/profiles/system"))
    except OSError:
        return None


def _append_status_row(path: pathlib.Path, row: dict) -> None:
    """Append one JSONL row under flock (same discipline as pkgs/evidence)."""
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    try:
        os.fchmod(fd, 0o640)
        fcntl.flock(fd, fcntl.LOCK_EX)
        with os.fdopen(fd, "a") as fh:
            fd = None
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    finally:
        if fd is not None:
            os.close(fd)


def _status_rows(cfg) -> list[dict]:
    path = pathlib.Path(cfg.get("evidence_dir", "/var/lib/evidence")) / "helm-status.jsonl"
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("kind") == "helm-status":
            rows.append(r)
    return rows


def record_status(cfg, status: dict, now) -> dict | None:
    """One row per verdict change, plus an hourly heartbeat; None when nothing is written."""
    current = {t["name"]: t["status"] for t in status["tiles"]}
    rows = _status_rows(cfg)
    last = rows[-1] if rows else None
    if last is None or last.get("tiles") != current:
        reason = "change"
    elif (now - _parse_iso(last["ts"])).total_seconds() >= 3600:
        reason = "heartbeat"
    else:
        return None
    row = {"v": 1, "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": "helm-status", "tiles": current, "reason": reason}
    _append_status_row(pathlib.Path(cfg.get("evidence_dir", "/var/lib/evidence")) / "helm-status.jsonl", row)
    return row


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
```

In `collect_all`, the returned document gains `"schema": 1`, `"active_profile": _read_marker(cfg)` (a helper: `read_text(cfg.get("profile_marker", "/etc/helm/profile")).strip()` with `OSError → "unknown"`) and `"generation": system_generation()`. In `main()`, after `status = collect_all(cfg, now)` and before writing: `record_status(cfg, status, now)` then `annotate_since(cfg, status)`, each wrapped in `try/except Exception` that prints to stderr — a history failure never blocks the page. In `render_html`: a helper `_local(ts)` → `_parse_iso(ts).astimezone().strftime("%H:%M %Z")`; the tile header becomes `f"<h2>{name} <span class=\"verdict\">{esc(tstatus_class.upper())}</span></h2>"`; each tile paragraph gains `<p class="since">since {esc(_local(t['since']))}</p>` when `since` is present; the header becomes `generated {local %H:%M:%S %Z} ({UTC %H:%M:%SZ}) · next {local}`; CSS adds `.verdict { font-size: 0.8rem; font-weight: 600; margin-left: 0.4rem; }` (no colour: the border already carries it). `render_text` appends `  since <local>` to each line when present. Runbook: one paragraph "Each tile prints its verdict word and says since when it has shown it; the history lives in the evidence store (`helm-status.jsonl`), one line per change plus one an hour. Times on the page are local (CDT); the collector's own file stays UTC."
- [ ] **Step 4: Green** — `nix develop -c ruff format pkgs/helm tests/helm`; `pytest tests/helm -q`; `nix build .#checks.x86_64-linux.helm-unit -L --no-link`; lint gate. The zero-outbound assertions (no `<script`, no `src=`, no `href="http`) must stay green: the new markup adds none.
- [ ] **Step 5: Commit.**

**touches:** pkgs/helm/collect.py, tests/helm/test_collect.py, docs/runbooks/helm.md
**acceptance:** helm-unit, lint
**commit subject:** `helm: verdict history in the evidence store; every tile prints its verdict and since when; local time; status.json carries schema, profile and generation (test: helm-unit, lint)`

### E8 (docs, S) — the board carries the plan: one START HERE, the log and the archive move out, a shape check

**dependsOn:** E2 (START HERE names the claims file), R5 (the runbook pass lands first so START HERE's pointers are true; the two tasks share no file)

**Files:**
- Create: `docs/board/log-2026-09.md`, `docs/board/archive-2026-09-02-to-05.md`, `docs/board/policies.md`
- Modify: `docs/OPERATIONS.md` (rewritten), `flake.nix` (`lint`: the board-shape lines), `githooks/pre-commit` (same lines)

**Interfaces:**
- Produces the rule the shape check enforces: exactly one `## START HERE` heading and at most 160 lines in `docs/OPERATIONS.md`. Consumed by every later turn and by `evidence bundle`'s runbook (E9).

- [ ] **Step 1: The failing check.** Add to `githooks/pre-commit` after the ruff lines, run `nix develop -c treefmt --config-file treefmt.toml --tree-root .` once, then copy the *formatted* text verbatim into the `lint` runCommand in `flake.nix` before `touch $out` (the snippet has no `${`, so it is safe inside the Nix `''` string):

```bash
# Board shape (plan 2026-09-05-evidence-store, E8/D5): the board carries the
# plan; facts come from `evidence bundle`. One START HERE, one screen or two.
test "$(grep -c '^## START HERE' docs/OPERATIONS.md)" -eq 1 || { echo "lint: docs/OPERATIONS.md must have exactly one '## START HERE' heading" >&2; exit 1; }
test "$(wc -l <docs/OPERATIONS.md)" -le 160 || { echo "lint: docs/OPERATIONS.md must be at most 160 lines (log and archive live under docs/board/)" >&2; exit 1; }
```

- [ ] **Step 2: Red** — `nix develop -c githooks/pre-commit` → "lint: docs/OPERATIONS.md must have exactly one '## START HERE' heading" (`grep -c '^## START HERE'` is 6 today: lines 3, 147, 164, 175, 202, 239; two more headings read `## Earlier START HERE` and are routed to the archive by the splitter below); the line-count rule would fire too (1029 lines).
- [ ] **Step 3: Split by headings, not line numbers** (the board changes every turn). Run once from the devShell; the current START HERE is archived, not dropped:

```python
# nix develop -c python3 - <<'PY'
import pathlib
src = pathlib.Path("docs/OPERATIONS.md").read_text().split("\n")
sections, cur = [], None
for line in src:
    if line.startswith("## "):
        cur = (line, [])
        sections.append(cur)
    elif cur is None:
        cur = (None, [line])
        sections.append(cur)
    else:
        cur[1].append(line)
first_start_seen = False
log, policies, archive = [], [], []
for h, body in sections:
    if h is None:
        continue
    if h.startswith("## START HERE") and not first_start_seen:
        first_start_seen = True
        archive += [h.replace("## START HERE", "## Superseded START HERE"), *body]
        continue
    if h.startswith("## Log "):
        log += [h, *body]
    elif h.startswith("## Standing policy"):
        policies += [h, *body]
    else:
        archive += [h, *body]
pathlib.Path("docs/board").mkdir(exist_ok=True)
pathlib.Path("docs/board/log-2026-09.md").write_text("# Board log — 2026-09 (newest first; moved verbatim from docs/OPERATIONS.md on 2026-09-05)\n\n" + "\n".join(log) + "\n")
pathlib.Path("docs/board/policies.md").write_text("# Standing policies (moved verbatim from docs/OPERATIONS.md on 2026-09-05)\n\n" + "\n".join(policies) + "\n")
pathlib.Path("docs/board/archive-2026-09-02-to-05.md").write_text("# Board archive — 2026-09-02 to 2026-09-05 (superseded START HERE blocks, lanes, files-in-flight; verbatim)\n\n" + "\n".join(archive) + "\n")
# PY
```

Then write the new `docs/OPERATIONS.md` (orchestrator text; refresh the dated items at execution time from the newest block in `docs/board/log-2026-09.md`, never from memory):

```markdown
# Operations board — nixos-agent-env

Facts are not written here. At the start of a session run
`evidence bundle --markdown` (live generation and revision, repo heads, which
checks cover HEAD and the live system, Helm verdicts and since when, open gaps
from the claims file docs/ledger/claims.toml). This file carries the plan: what
is queued, what is parked, what the operator owns. It is replaced every turn,
never appended.

## START HERE (2026-09-05)

**Queued, in order.** 1) plan `docs/superpowers/plans/2026-09-05-evidence-store.md`
waves 1–4 (see its Waves table). 2) Helm Home sub-project 1 (spec
`docs/superpowers/specs/2026-09-04-helm-home-design.md`) — plan next, after the
four decisions the environment review asks for (who calls polkit and what the
page's Switch does; where the declaration checker lives; the raise mechanism on
Wayland; the flakes option shape). 3) media M3 (claim `m3-comfy-angle-aimdo`).

**Operator owns** (each a `gap` row in the claims file, owner operator): one
switch after wave 2 of the evidence plan; `o4-framing-test`; `d5-activity-export`;
`s12-commit-metadata-decision`; `xhigh-restore-or-keep-medium`;
`seat-key-exception-undecided`; `nixpkgs-host-pin-age`; two brainstorms owed
(interpreter model; Helm Home sub-projects 2 and 3).

**Parked by decision** (`parked` rows): Cowork tier A; the Helm workspace buttons;
wiring round 2's media service; O7.

**How work runs.** Seat driver (`tools/factory/seat`, README there) or the dark
factory (`tools/factory/dark-factory.js`); Opus gates every task with a mutation
check; one bounded fix round then re-plan (rule A1); every check the integrator or
verifier runs is recorded in the evidence store; every run leaves a run report.
Effort policy: docs/XS tasks `OPENROUTER_REASONING_EFFORT=off`, code tasks medium
(claim `effort-policy-n1`, n=1).

**Where things are.** Log: `docs/board/log-2026-09.md` (newest first). Archive:
`docs/board/archive-2026-09-02-to-05.md`. Policies: `docs/board/policies.md`.
Plans `docs/superpowers/plans/`, reviews `docs/reviews/` (the 2026-09-05
environment review is the current defect list), decisions `docs/decisions/`,
concepts `docs/concepts/`, runbooks `docs/runbooks/` (`evidence.md` explains the
store and the claims file).

## Log

Every turn appends its block to `docs/board/log-2026-09.md` (newest first) and
rewrites START HERE above. A month rolls to a new log file.
```

- [ ] **Step 4: Green** — `nix develop -c githooks/pre-commit` passes (heading count 1, ≤ 160 lines); `git add docs/board`; `nix build .#checks.x86_64-linux.lint -L --no-link`. Completeness: `cat docs/board/*.md docs/OPERATIONS.md | wc -l` ≥ 1029 (the old text is all still present, the first block under its "Superseded" heading).
- [ ] **Step 5: Commit** (docs + lint change in one commit).

**touches:** docs/OPERATIONS.md, docs/board/log-2026-09.md, docs/board/archive-2026-09-02-to-05.md, docs/board/policies.md, flake.nix, githooks/pre-commit
**acceptance:** lint
**commit subject:** `docs: board — one START HERE that carries the plan; log, archive and policies move under docs/board; the lint gate checks the shape (test: lint)`

### E9 (code, M) — `evidence bundle`: the facts a fresh session reads, plus the runbook, CLAUDE.md and README

**dependsOn:** E2, E8

**Files:**
- Modify: `pkgs/evidence/evidence.py` (`run` seam, `_git`, `_docs_equivalent`, `bundle`, `render_bundle_markdown`, the `bundle` subcommand), `tests/evidence/test_evidence.py`, `CLAUDE.md` (board line, Commands block, Architecture bullets, "How work is done here", check list), `README.md` (status paragraph → pointer)
- Create: `docs/runbooks/evidence.md`

**Interfaces:**
- Consumes `checks.jsonl`, `helm-status.jsonl` (shapes in SCHEMA.md), the claims file via `claims.load`/`claims.open_gaps` (E2), `git`, `nixos-version`, `/nix/var/nix/profiles/system`.
- Produces `evidence [--store DIR] bundle [--markdown] [--repo PATH] [--claims FILE] [--sibling PATH]... [--nixos-version-bin PATH]` → JSON (default) or markdown; the Python API `bundle(store, repo, claims_path, siblings, nixos_version_bin, now) -> dict` and `render_bundle_markdown(b) -> str`; the `run` seam (`evidence.run(argv, timeout)`), same shape as `collect.run`.

Bundle dict:

```json
{"generated": "…Z", "live": {"generation": "system-39-link", "rev": "e1d4…"}, "head": "de51…",
 "docs_only_ahead": true, "dirty": false,
 "checks": {"flake-check": {"head": {row or null}, "live": {row or null}}, "lint": {}},
 "siblings": {"dsh-harness": "e31370d integrate F6c into integ/b9"},
 "helm": {"ts": "…Z", "tiles": {"drift": {"status": "fail", "since": "…Z"}}},
 "claims": {"verified": 3, "parked": 2, "gaps": [{"id": "…", "owner": "…", "opened": "2026-09-05", "review_by": "2026-09-12", "closes_by": "…", "stale": false}]}}
```

- [ ] **Step 1: Failing tests** (append to `tests/evidence/test_evidence.py`; `load()` already inserts the package directory into `sys.path`, so `bundle()`'s `import claims` resolves when this file runs alone):

```python
import datetime as dt


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"}

    def g(*a):
        return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True, env={**os.environ, **env}).stdout.strip()

    g("init", "-q", "-b", "main")
    (repo / "flake.nix").write_text("{}\n")
    g("add", ".")
    g("commit", "-q", "-m", "code")
    live = g("rev-parse", "HEAD")
    (repo / "docs").mkdir()
    (repo / "docs" / "OPERATIONS.md").write_text("board\n")
    g("add", ".")
    g("commit", "-q", "-m", "docs")
    head = g("rev-parse", "HEAD")
    return repo, live, head


CLAIMS = """
[[claim]]
id = "a-verified-thing"
text = "x"
status = "verified"
class = "unit"
evidence = "check:unit@abc1234 t"
owner = "orchestrator"
opened = 2026-09-04

[[claim]]
id = "an-open-gap"
text = "y"
status = "gap"
class = "unmeasured"
owner = "operator"
opened = 2026-09-01
review_by = 2026-09-02
closes_by = "do y"
"""


def fake_nixos_version(tmp_path, rev):
    p = tmp_path / "nixos-version"
    p.write_text(f"#!{sys.executable}\nprint({rev!r})\n")
    p.chmod(0o755)
    return str(p)


def test_bundle_reports_live_head_docs_only_checks_gaps_and_helm(tmp_path):
    repo, live, head = make_repo(tmp_path)
    store = tmp_path / "store"
    store.mkdir()
    ev.append(str(store), "checks", {"kind": "check", "name": "flake-check", "rev": live, "ok": True, "class": "nix-check", "src": "helm-nightly"}, ts="2026-09-05T08:00:00Z")
    ev.append(str(store), "helm-status", {"kind": "helm-status", "tiles": {"drift": "fail"}, "reason": "change"}, ts="2026-09-05T07:00:00Z")
    claims_file = tmp_path / "claims.toml"
    claims_file.write_text(CLAIMS)
    now = dt.datetime(2026, 9, 5, 12, 0, tzinfo=dt.timezone.utc)
    b = ev.bundle(str(store), str(repo), str(claims_file), [str(repo)], fake_nixos_version(tmp_path, live), now=now)
    assert b["live"]["rev"] == live and b["head"] == head and b["docs_only_ahead"] is True and b["dirty"] is False
    assert b["checks"]["flake-check"]["live"]["ok"] is True
    assert b["checks"]["flake-check"]["head"]["ok"] is True  # docs-equivalent coverage
    assert b["claims"]["verified"] == 1 and b["claims"]["gaps"][0]["id"] == "an-open-gap" and b["claims"]["gaps"][0]["stale"] is True
    assert b["helm"]["tiles"]["drift"] == {"status": "fail", "since": "2026-09-05T07:00:00Z"}
    assert "repo" in b["siblings"]
    md = ev.render_bundle_markdown(b)
    assert "an-open-gap" in md and "docs-only ahead" in md and "flake-check" in md and "drift" in md


def test_bundle_without_store_or_claims_still_renders(tmp_path):
    repo, live, head = make_repo(tmp_path)
    b = ev.bundle(str(tmp_path / "nostore"), str(repo), str(tmp_path / "none.toml"), [], fake_nixos_version(tmp_path, "unknown"), now=None)
    assert b["live"]["rev"] is None and b["checks"] == {} and b["claims"] == {"verified": 0, "parked": 0, "gaps": []}
    assert "no observations" in ev.render_bundle_markdown(b)


def test_cli_bundle_markdown(tmp_path):
    repo, live, head = make_repo(tmp_path)
    r = subprocess.run([sys.executable, str(SRC), "--store", str(tmp_path / "s"), "bundle", "--markdown", "--repo", str(repo), "--claims", str(tmp_path / "none.toml"), "--nixos-version-bin", fake_nixos_version(tmp_path, live)], capture_output=True, text=True, check=False)
    assert r.returncode == 0 and r.stdout.startswith("# Evidence bundle") and head[:12] in r.stdout
```

- [ ] **Step 2: Red** — `nix develop -c pytest tests/evidence/test_evidence.py -q` → `AttributeError: module 'evidence' has no attribute 'bundle'` (not `FileNotFoundError: 'git'` — E1's derivation already carries git and a HOME; locally the devShell has git).
- [ ] **Step 3: Implement** (in `evidence.py`; add `import subprocess` at the top):

```python
def run(argv, timeout=20.0):
    """The one subprocess seam (tests monkeypatch or pass stub binaries)."""
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)


def _git(repo, *args):
    try:
        cp = run(["git", "-C", repo, *args])
    except FileNotFoundError:
        return None
    return cp.stdout.strip() if cp.returncode == 0 else None


def _docs_equivalent(repo, a, b) -> bool:
    if a == b:
        return True
    cp = run(["git", "-C", repo, "diff", "--quiet", a, b, "--", ".", ":!docs", ":!*.md"])
    return cp.returncode == 0


def bundle(store, repo, claims_path, siblings, nixos_version_bin="/run/current-system/sw/bin/nixos-version", now=None) -> dict:
    now = now or datetime.datetime.now(datetime.timezone.utc)
    head = _git(repo, "rev-parse", "HEAD")
    dirty = bool(_git(repo, "status", "--porcelain") or "")
    live = None
    try:
        cp = run([nixos_version_bin, "--configuration-revision"])
        out = (cp.stdout.strip() if cp.returncode == 0 else "").removesuffix("-dirty")
        live = out if REV_RE.match(out) else None
    except (FileNotFoundError, OSError):
        live = None
    try:
        generation = os.path.basename(os.readlink("/nix/var/nix/profiles/system"))
    except OSError:
        generation = None
    docs_only = bool(head and live and _docs_equivalent(repo, live, head))

    checks: dict = {}
    rows = [r for r in read(store, "checks") if r.get("kind") == "check" and isinstance(r.get("rev"), str)]
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
        sib[os.path.basename(path.rstrip("/"))] = _git(path, "log", "-1", "--format=%h %s")

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
            claims_out["gaps"].append({"id": g["id"], "owner": g.get("owner"), "opened": str(g.get("opened")), "review_by": str(rb), "closes_by": g.get("closes_by"), "stale": bool(rb and rb < today)})

    return {"generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "live": {"generation": generation, "rev": live}, "head": head, "docs_only_ahead": docs_only, "dirty": dirty, "checks": checks, "siblings": sib, "helm": helm, "claims": claims_out}


def render_bundle_markdown(b: dict) -> str:
    def short(x):
        return (x or "none")[:12]

    lines = [f"# Evidence bundle — {b['generated']}", ""]
    lines.append(f"**Live:** {b['live']['generation'] or 'unknown generation'} at {short(b['live']['rev'])}. **HEAD:** {short(b['head'])}"
                 + (" (docs-only ahead of live)" if b["docs_only_ahead"] else "") + (" — WORKING TREE DIRTY" if b["dirty"] else "") + ".")
    lines += ["", "## Checks covering HEAD and the live system", ""]
    if not b["checks"]:
        lines.append("no observations recorded yet")
    for name, cov in b["checks"].items():
        def cell(r):
            return "—" if r is None else f"{'ok' if r.get('ok') else 'FAIL'} @{r['rev'][:12]} {r.get('class', '?')}/{r.get('src', '?')} {r.get('ts', '')}"

        lines.append(f"- {name}: HEAD {cell(cov['head'])}; live {cell(cov['live'])}")
    lines += ["", "## Repo heads", ""] + [f"- {k}: {v or 'unreadable'}" for k, v in b["siblings"].items()]
    lines += ["", "## Helm now", ""]
    if b["helm"] is None:
        lines.append("no observations (helm-status stream empty)")
    else:
        lines += [f"- {n}: {t['status']} since {t['since']}" for n, t in sorted(b["helm"]["tiles"].items())]
    c = b["claims"]
    lines += ["", f"## Claims: {c['verified']} verified, {c['parked']} parked, {len(c['gaps'])} open gaps", ""]
    for g in c["gaps"]:
        lines.append(f"- {'STALE ' if g['stale'] else ''}{g['id']} (owner {g['owner']}, opened {g['opened']}, review by {g['review_by']}): {g['closes_by']}")
    return "\n".join(lines) + "\n"
```

CLI: a `bundle` subparser with `--markdown`, `--repo` (default `/home/dalhaka/nixos-agent-env`), `--claims` (default `<repo>/docs/ledger/claims.toml`), `--sibling` (append; default the four `~/flakes/*` repos when none given), `--nixos-version-bin`; on `bundle` print `render_bundle_markdown(...)` or `json.dumps(..., indent=2, sort_keys=True)`.
- [ ] **Step 4: `docs/runbooks/evidence.md`** — plain language, one command each. Open with: "Two different things share the word ledger. The **claims file** (`docs/ledger/claims.toml`) is the list of what we believe about this system and whether each belief is proven. The **ledger** (`/var/lib/evidence/ledger/`) is the token and cost record. This page is about the store and the claims file." Then: what the store is and where (`/var/lib/evidence`, backed up nightly); what writes to it (the nightly flake check, the seat integrator, the factory, Helm's collector); how to read it (`evidence bundle --markdown`; `evidence latest-check --name flake-check --rev $(git rev-parse HEAD)`; `tail -n 3 /var/lib/evidence/checks.jsonl`); what "verified" means here (a named check green at a revision, recorded with how it was checked; an operator-judged drill is class `operator`); how to open a gap (a row with owner, review date and what closes it), how to close one (status `verified` with `check:<name>@<rev>`), what the hook refuses (a gap past its review date; evidence that is prose); the two tile rules that changed (flake-check green when a recorded check covers a revision that differs from HEAD only in docs; drift green when HEAD is ahead only in docs).
- [ ] **Step 5: `CLAUDE.md` and `README.md`.** CLAUDE.md: the board sentence becomes "Board of record: `docs/OPERATIONS.md` — read its START HERE block (the plan) and run `evidence bundle --markdown` (the facts) first; rewrite START HERE every turn, append the turn's block to `docs/board/log-<month>.md`." Commands block gains `evidence bundle --markdown   # live facts: generation, heads, checks covering HEAD, Helm since-when, open gaps` and `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"`. "How work is done here" gains (review claude-md-2): "Day-to-day tasks run through the seat driver (`tools/factory/seat`, DeepSeek headless, Opus gate by `factory-review`); `tools/factory/dark-factory.js` through the Workflow tool runs Claude-side factories (nixos-skill fix rounds, this repo when the scheduler is wanted)." Architecture gains four bullets, same shape as the existing ones (review claude-md-3): **Helm** (`nixosModules/helm.nix`, `pkgs/helm/`): the loopback status page and profile switch, collector every 5 min, root `helm-switch@` unit behind polkit; **Model lanes** (`nixosModules/modelLane.nix`, `pkgs/lane/`): confined OpenRouter jobs through the broker; **The seat** (`pkgs/dsh-openrouter/`): the operator's DeepSeek harness with the deny-only hook guard; **Ledger and evidence** (`tools/ledger/`, `pkgs/evidence/`, `nixosModules/evidenceStore.nix`): token/cost ledger, append-only evidence store under `/var/lib/evidence`, the claims file `docs/ledger/claims.toml`, runbook `docs/runbooks/evidence.md`. The check-name list gains `evidence-unit`, `evidence-eval`, `claims-validate`. README.md (review claude-md-1): the dated status paragraph becomes one sentence: "Status lives on the board: `docs/OPERATIONS.md` START HERE, and `evidence bundle --markdown` for the live facts."
- [ ] **Step 6: Green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `pytest tests/evidence -q`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; lint gate. Then the smoke that proves the store copy can import its sibling: `nix build .#packages.x86_64-linux.evidence -o /tmp/ev-cli && /tmp/ev-cli/bin/evidence --store /tmp/ev-smoke bundle --markdown --claims docs/ledger/claims.toml` prints live generation, HEAD, "no observations", the four heads and the open gaps; `rm /tmp/ev-cli`.
- [ ] **Step 7: Commit.**

**touches:** pkgs/evidence/evidence.py, tests/evidence/test_evidence.py, docs/runbooks/evidence.md, CLAUDE.md, README.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: bundle prints the facts a session starts from — live, HEAD, checks covering both, Helm since-when, open gaps; runbook; CLAUDE.md and README (test: evidence-unit, lint)`

---

## Tasks from the environment review (R1–R10)

Ids in brackets are finding ids in `docs/reviews/2026-09-05-environment-review.md` (addendum table).

### R1 (code, S) — the broker keys on the routed destination, normalises paths, fails closed on an unpatchable body [r2-1-1 blocker, r2-1-3, r2-1-4]

**dependsOn:** none

**Files:**
- Modify: `pkgs/broker/policy.py` (`_audit`, `_check`, `_denied_path`, `_inject`, `http_connect`, `_patch_spec`, `_patch_body`, new `_normalized_path`), `tests/broker/test_policy.py`, `tests/integration/broker-vm.nix` (one probe)

**Interfaces:**
- Every policy decision (allowlist, CONNECT gate, credential injection, deny paths, body patch) keys on `flow.request.host` — the address mitmproxy connects to. A request whose Host header (`flow.request.pretty_host`) or SNI disagrees with it is denied with reason `host-header-mismatch: host=<routed> header=<claimed>` / `host/sni mismatch: …`. Audit rows gain `host_header` (the claimed one) beside `host` (the routed one) — `test_audit_record_has_exact_fields` pins the new field set.
- `_normalized_path(raw) -> str | None`: query and fragment dropped, percent-decoded once, `.`/`..`/`//` resolved with `posixpath.normpath` (a trailing slash preserved), casefolded; `None` when a `%` survives one decode or the result does not start with `/`. Deny paths, inject paths and body-patch prefixes match against it; `None` on a deny-path host is denied with reason `path-not-normalizable`.
- On a body-patch host+prefix, a request whose body cannot be patched (content type not `application/json` after case-insensitive media-type parsing, body absent, not JSON, or not an object) is denied with reason `zdr-unpatchable-body` before injection. The existing test `test_body_patch_leaves_other_paths_hosts_and_non_json_alone` keeps its other-path/other-host halves and its non-JSON half flips to "is denied".

- [ ] **Step 1: Failing tests** in `tests/broker/test_policy.py` (`load_addon`, `https_flow`, `audit_lines` exist at the top of the file):

```python
def http_flow(routed_host, host_header, path="/x"):
    f = tflow.tflow()
    f.request.scheme = "http"
    f.request.host = routed_host
    f.request.port = 80
    f.request.path = path
    f.request.headers["Host"] = host_header
    f.client_conn.sni = None
    return f


def test_host_header_cannot_redirect_the_credential(tmp_path, monkeypatch):
    secret = tmp_path / "s"
    secret.write_text("vm-test-secret\n")
    addon, audit = load_addon(tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"], "inject": {"allowed.test": {"value_file": str(secret)}}})
    f = http_flow("attacker.test", "allowed.test")
    addon.requestheaders(f)
    addon.request(f)
    assert f.response is not None and f.response.status_code == 403
    assert "Authorization" not in f.request.headers
    rec = audit_lines(audit)[-1]
    assert rec["verdict"] == "deny" and rec["reason"].startswith("host-header-mismatch")
    assert rec["host"] == "attacker.test" and rec["host_header"] == "allowed.test"


def test_matching_host_header_with_port_is_allowed_and_injected(tmp_path, monkeypatch):
    secret = tmp_path / "s"
    secret.write_text("vm-test-secret\n")
    addon, audit = load_addon(tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"], "inject": {"allowed.test": {"value_file": str(secret)}}})
    f = http_flow("allowed.test", "allowed.test:80")
    addon.request(f)
    assert f.response is None and f.request.headers["Authorization"] == "Bearer vm-test-secret"


@pytest.mark.parametrize("path", ["/api/v1/%6dessages", "//api/v1/messages", "/api/v1/./messages", "/api/v1/x/../messages", "/API/v1/messages", "/api/v1/messages?x=1", "/api/v1/%252dmessages"])
def test_deny_paths_survive_path_equivalence_tricks(tmp_path, monkeypatch, path):
    addon, audit = load_addon(tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"], "deny_paths": {"allowed.test": {"path_prefixes": ["/api/v1/messages"]}}})
    f = https_flow("allowed.test", path)
    addon.request(f)
    assert f.response is not None and f.response.status_code == 403
    assert audit_lines(audit)[-1]["reason"] in ("path-not-permitted", "path-not-normalizable")


def test_other_paths_still_pass_after_normalisation(tmp_path, monkeypatch):
    addon, audit = load_addon(tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"], "deny_paths": {"allowed.test": {"path_prefixes": ["/api/v1/messages"]}}})
    f = https_flow("allowed.test", "/api/v1/chat/completions?stream=true")
    addon.request(f)
    assert f.response is None


@pytest.mark.parametrize("ctype,body,patched", [("APPLICATION/JSON", b'{"a":1}', True), ("application/json; charset=utf-8", b'{"a":1}', True), ("text/plain", b'{"a":1}', False), ("application/json", b"[1,2]", False), ("application/json", b"not json", False), ("application/json", b"", False)])
def test_body_patch_fails_closed_when_it_cannot_patch(tmp_path, monkeypatch, ctype, body, patched):
    addon, audit = load_addon(tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"], "body_patch": {"allowed.test": {"path_prefixes": ["/api/v1/chat/completions"], "merge": {"provider": {"zdr": True}}}}})
    f = https_flow("allowed.test", "/api/v1/chat/completions")
    f.request.headers["content-type"] = ctype
    f.request.content = body
    addon.request(f)
    if patched:
        assert f.response is None and json.loads(f.request.content)["provider"]["zdr"] is True
    else:
        assert f.response is not None and f.response.status_code == 403
        assert audit_lines(audit)[-1]["reason"] == "zdr-unpatchable-body"
```

Add `import pytest` to the file's imports. In `test_audit_record_has_exact_fields` add `"host_header"` to the expected key set.

- [ ] **Step 2: Red** — `nix develop -c pytest tests/broker -q`: the redirect test fails (`f.response is None`, Authorization present); five of the seven path tricks pass today only by accident of `startswith` — `%6d`, `//`, `./`, `..`, `API` fail red; the fail-closed cases fail (`f.response is None`); `test_audit_record_has_exact_fields` fails on the missing key.
- [ ] **Step 3: Implement** in `policy.py` (add `import posixpath` and `import urllib.parse`):

```python
def _normalized_path(raw):
    """Path without query/fragment, percent-decoded once, dots and duplicate
    slashes resolved, casefolded. None when the result still carries an escape
    (double encoding) or does not start with '/'."""
    path = raw.split("?", 1)[0].split("#", 1)[0]
    decoded = urllib.parse.unquote(path)
    if "%" in decoded or not decoded.startswith("/"):
        return None
    norm = posixpath.normpath(decoded)
    if decoded.endswith("/") and not norm.endswith("/"):
        norm += "/"
    return norm.casefold()


def _prefix_match(path, prefixes):
    norm = _normalized_path(path)
    if norm is None:
        return None  # caller decides: deny for deny_paths, no-match for inject
    return any(norm.startswith(_normalized_path(p) or "\0") for p in prefixes)
```

`_audit`: `"host": flow.request.host, "host_header": flow.request.pretty_host`. `_check`:

```python
        host = flow.request.host  # the destination mitmproxy connects to (D8)
        claimed = flow.request.pretty_host  # the Host header, client-controlled
        sni = getattr(flow.client_conn, "sni", None)
        if host not in self.allow:
            reason = "not-allowlisted"
            if sni and sni != host:
                reason = f"host/sni mismatch: sni={sni} host={host}"
            self._deny_request(flow, reason)
            return False
        if claimed != host:
            self._deny_request(flow, f"host-header-mismatch: host={host} header={claimed}")
            return False
        if sni and sni != host:
            self._deny_request(flow, f"host/sni mismatch: sni={sni} host={host}")
            return False
        return True
```

`_denied_path`: `spec = self.deny_paths.get(flow.request.host)`; `m = _prefix_match(flow.request.path, spec.get("path_prefixes", []))`; return `True` when `m is None or m` (the callers keep the reason `path-not-permitted`; add `path-not-normalizable` when `m is None` by returning the reason string instead of a bool — adjust both callers). `_inject`: `host = flow.request.host`; `if not _prefix_match(flow.request.path, spec.get("paths", ["/"])): return`. `http_connect`: `flow.request.host`. `_patch_spec`: `self.body_patch.get(flow.request.host)` and `_prefix_match`. `_patch_body`:

```python
        spec = self._patch_spec(flow)
        if not spec:
            return
        media = flow.request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        try:
            body = json.loads(flow.request.get_content(strict=False) or b"")
        except (ValueError, UnicodeDecodeError):
            body = None
        if media != "application/json" or not isinstance(body, dict):
            self._deny_request(flow, "zdr-unpatchable-body")
            return
        merge(body, spec.get("merge", {}))
        flow.request.content = json.dumps(body).encode("utf-8")
```

(`_deny_request` after `_inject` in `request()` — reorder so `_patch_body` runs before `_inject`, so a denied body never carries the credential; the streamed-body kill in `requestheaders` stays.)

- [ ] **Step 4: VM probe** in `tests/integration/broker-vm.nix` testScript after step 4 (the fronting probe):

```python
    # 4b. host-header routing trick (review r2-1-1): an absolute-form plain
    #     HTTP URL to a denied host with an allowlisted Host header must be
    #     refused before any connection, never credential-injected.
    code = machine.succeed(
        curl + " -H 'Host: allowed.test' -o /dev/null -w '%{http_code}' http://denied.test/ || true"
    )
    assert code.strip() == "403", f"host-header trick got {code}"
    machine.succeed(
        "jq -es '[.[] | select(.verdict==\"deny\" and (.reason | startswith(\"host-header-mismatch\")))] | length >= 1' /var/lib/egress-broker/agent1/audit.jsonl"
    )
```

Red first: run `nix build .#checks.x86_64-linux.integration -L --no-link` once with only the probe added — today the request is forwarded and the code is not 403.
- [ ] **Step 5: Green** — `nix develop -c ruff format pkgs/broker tests/broker`; `nix develop -c pytest tests/broker -q`; `nix build .#checks.x86_64-linux.addon -L --no-link`; `… integration` (VM, minutes); `… lane-vm` (the lane's deny of `/api/v1/messages` must still pass — it now goes through the normaliser); lint gate.
- [ ] **Step 6: Commit.**

**touches:** pkgs/broker/policy.py, tests/broker/test_policy.py, tests/integration/broker-vm.nix
**acceptance:** addon, integration, lane-vm, lint
**commit subject:** `broker: policy keys on the routed host, never the Host header; deny paths normalised; unpatchable bodies fail closed (test: addon, integration, lane-vm, lint)`

### R2 (code, S) — helm-serve: boot-scoped journal, a stale-page banner, `/control.json`, the three untested guards; render: local time and the Profile verdict word [helm-code-1, helm-code-5, helm-code-3, tests-4, r2-3-2, helm-runbooks-4]

**dependsOn:** none

**Files:**
- Modify: `pkgs/helm/serve.py` (`_journal_switch_records`, `_page`, `do_GET`), `pkgs/helm/render.py` (`_hm`, the Profile section), `tests/helm/test_serve.py`, `tests/helm/test_render_control.py`, `tests/acceptance/helm-v1.sh` (line 364-368: `/status.json` → `/control.json`), `docs/runbooks/helm-v1.md` (line 123)

**Interfaces:**
- `GET /control.json` returns the serve-time state (what `/status.json` returned until now); `GET /status.json` returns the collector's document (`<out_dir>/status.json`, `application/json`) or 404 when missing — so the name means one thing for Helm Home.
- `_journal_switch_records` calls `journalctl -b -u helm-switch@* -g '^helm-switch: (begin|end) ' -o json --no-pager -n 200`.
- `_page` reads `<out_dir>/status.json`'s `generated_at`/`interval_s`; when the document is older than `2 × interval_s` and no action banner is being shown, it shows a `fail` banner `status tiles are N min old — the collector last ran at HH:MM; check systemctl --user status helm-collect.timer`.
- `render._hm` prints local time; the Profile header is `<h2>Profile <span class="verdict">OK|WARN|FAIL|UNKNOWN</span></h2>`.

- [ ] **Step 1: Failing tests.** `tests/helm/test_serve.py` (`app`, `Server`, `http_response`, `GOOD`, `journal` exist; `serve.run_switch` at serve.py:210 is what `_do_switch` calls):

```python
import socket


def raw_request(port, text: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=5) as s:
        s.sendall(text)
        s.shutdown(socket.SHUT_WR)
        out = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    return out


def test_body_guards_reject_before_run_switch(monkeypatch):
    calls = []
    monkeypatch.setattr(serve, "run_switch", lambda name: calls.append(name))
    with Server() as srv:
        big = raw_request(srv.port, b"POST /action/switch HTTP/1.1\r\nHost: localhost:7700\r\nSec-Fetch-Site: same-origin\r\nContent-Length: 999999\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\nprofile=gaming&token=t")
        bad = raw_request(srv.port, b"POST /action/switch HTTP/1.1\r\nHost: localhost:7700\r\nSec-Fetch-Site: same-origin\r\nContent-Length: abc\r\n\r\n")
    assert big.split(b"\r\n", 1)[0].endswith(b" 400 Bad Request") or b" 400 " in big.split(b"\r\n", 1)[0]
    assert b" 400 " in bad.split(b"\r\n", 1)[0]
    assert calls == []


def test_journal_read_is_boot_scoped_and_filtered(monkeypatch, tmp_path):
    seen = []

    def fake_run(argv, timeout=10.0):
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(serve, "run", fake_run)
    serve.read_state({"marker": str(tmp_path / "profile")})
    argv = seen[0]
    assert "-b" in argv and argv[argv.index("-g") + 1] == "^helm-switch: (begin|end) "


def test_stale_status_document_shows_an_age_banner(tmp_path):
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=900)).isoformat()
    (tmp_path / "status.json").write_text(json.dumps({"generated_at": old, "interval_s": 300, "tiles": []}))
    with Server() as srv:
        code, hdrs, body = http_response(srv.port, "GET", "/", GOOD)
    assert code == 200 and "status tiles are 15 min old" in body
    (tmp_path / "status.json").write_text(json.dumps({"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "interval_s": 300, "tiles": []}))
    with Server() as srv:
        code, hdrs, body = http_response(srv.port, "GET", "/", GOOD)
    assert code == 200 and "min old" not in body


def test_control_json_is_the_state_and_status_json_is_the_collector_document(tmp_path):
    (tmp_path / "status.json").write_text(json.dumps({"schema": 1, "tiles": [{"name": "drift", "status": "ok"}]}))
    with Server() as srv:
        c_code, _, c_body = http_response(srv.port, "GET", "/control.json", GOOD)
        s_code, s_hdrs, s_body = http_response(srv.port, "GET", "/status.json", GOOD)
    assert c_code == 200 and json.loads(c_body)["active_profile"] == "base"
    assert s_code == 200 and json.loads(s_body)["tiles"][0]["name"] == "drift"
    assert s_hdrs.get("Content-Type", "").startswith("application/json")
```

(The `app` fixture points `out_dir` at `tmp_path`, so the tests above write `status.json` there.) Add `assert hdrs.get("X-Content-Type-Options") == "nosniff"` to the header loop in `test_send_carries_anti_framing_headers`. `tests/helm/test_render_control.py`:

```python
def test_profile_header_names_its_verdict_in_text():
    state = {"active_profile": "base", "now": "2026-09-03T21:44:00+00:00", "last_switch": {"from": "gaming", "to": "base", "result": "ok", "at": "2026-09-03T20:00:00+00:00"}, "switching": None}
    out = render.render_control(V0_PAGE, CONTROL, state, TOKEN)
    assert '<h2>Profile <span class="verdict">OK</span></h2>' in out


def test_hm_prints_local_time(monkeypatch):
    import time

    monkeypatch.setenv("TZ", "CST6CDT,M3.2.0,M11.1.0")
    time.tzset()
    try:
        assert render._hm("2026-09-03T21:44:00+00:00") == "16:44"
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()
```

- [ ] **Step 2: Red** — `nix develop -c pytest tests/helm -q`: `calls == []` holds but the two 400 assertions already pass today (the guards exist and are simply untested — these two cases are the missing pins, not red-first; say so in the commit body), the `-b`/`-g` assertion fails, the banner test fails, `/control.json` is 404, the Profile header lacks the span, `_hm` returns `21:44`.
- [ ] **Step 3: Implement.** serve.py: `_journal_switch_records` argv gains `"-b"` and `"-g", "^helm-switch: (begin|end) "`; a helper `_status_age(cfg)` reads `status.json`, returns `(age_seconds, interval, generated_dt)` or `(None, None, None)` on any error; `_page(banner)`: when `banner is None` and `age > 2 * interval`, `banner = {"kind": "fail", "text": f"status tiles are {int(age // 60)} min old — the collector last ran at {generated_dt.astimezone().strftime('%H:%M %Z')}; check systemctl --user status helm-collect.timer"}`; `do_GET`: `/control.json` → the state JSON; `/status.json` → `pathlib.Path(out_dir, "status.json").read_text()` as `application/json`, or `_plain(404, "no status document yet")`. render.py: `_hm` → `datetime.datetime.fromisoformat(str(iso)).astimezone().strftime("%H:%M")`; the Profile section's `<h2>Profile</h2>` becomes `f'<h2>Profile <span class="verdict">{status_class.upper()}</span></h2>'` (`status_class` is one of ok/warn/fail/unknown there already). `tests/acceptance/helm-v1.sh:364-368` and `docs/runbooks/helm-v1.md:123`: `/status.json` → `/control.json` for the serve-time state.
- [ ] **Step 4: Green** — `nix develop -c ruff format pkgs/helm tests/helm`; `pytest tests/helm -q`; `nix build .#checks.x86_64-linux.helm-unit -L --no-link`; `… helm-control-vm` (the VM test curls `/`; confirm it still passes); lint gate (shellcheck covers the acceptance script).
- [ ] **Step 5: Commit.**

**touches:** pkgs/helm/serve.py, pkgs/helm/render.py, tests/helm/test_serve.py, tests/helm/test_render_control.py, tests/acceptance/helm-v1.sh, docs/runbooks/helm-v1.md
**acceptance:** helm-unit, helm-control-vm, lint
**commit subject:** `helm-serve: boot-scoped switch journal, stale-page banner, /control.json, the untested guards pinned; render prints local time and the Profile verdict (test: helm-unit, helm-control-vm, lint)`

### R4 (code, S) — the profile negative check proves something: the module refuses a profile that is not a declared specialisation [tests-1]

**dependsOn:** none

**Files:**
- Modify: `nixosModules/helm.nix` (one assertion in the `control.enable` assertion list), `flake.nix` (`helm-control-assertion-negative-profiles`)

**Interfaces:**
- Module assertion: every non-`base` entry of `services.helm.control.profiles` names a declared `specialisation`, checked only in the base evaluation. Specialisations do not nest (`specialisation.<n>.configuration` is evaluated with `specialisation = {}`), so inside a child the check must be skipped; the child is recognised by its marker: `environment.etc."helm/profile".text != "base"`. The negative fixture `helmControlBadProfilesSystem` (flake.nix:318) has marker `base`, profiles `[base nope]` and `specialisation.alt` → red. The positive fixtures (`[base alt]` with `specialisation.alt`) and `core` (`[base gaming]` with `specialisation.gaming`) pass; the gaming child (marker `gaming`) is skipped.

- [ ] **Step 1: Make the check honest first (red).** Replace the body of `helm-control-assertion-negative-profiles` in `flake.nix` with the shape its three siblings use:

```nix
        helm-control-assertion-negative-profiles =
          let
            # G1 (D1): every non-base profile must be a declared specialisation --
            # asserted by the MODULE (nixosModules/helm.nix), not by this check.
            attempt = builtins.tryEval helmControlBadProfilesSystem.config.system.build.toplevel.drvPath;
          in
          if attempt.success then
            throw "helm-control-assertion-negative-profiles: profiles=[base nope] DID NOT FAIL the build"
          else
            pkgs.runCommand "helm-control-assertion-negative-profiles-ok" { } "touch $out";
```

- [ ] **Step 2: Red** — `nix build .#checks.x86_64-linux.helm-control-assertion-negative-profiles -L --no-link` → `DID NOT FAIL the build` (the module accepts `nope`).
- [ ] **Step 3: The module assertion**, appended to the `control.enable` assertion list in `nixosModules/helm.nix`:

```nix
        {
          # G1 (D1): a profile the page offers must be a specialisation this
          # toplevel can switch to. Checked in the base evaluation only: a
          # specialisation child is evaluated with `specialisation = {}` (they
          # do not nest), and is recognised by its own marker.
          assertion =
            (config.environment.etc."helm/profile".text or "base") != "base"
            || lib.all (p: p == "base" || config.specialisation ? ${p}) cfg.control.profiles;
          message = "services.helm.control.profiles names a profile that is not a declared specialisation: ${
            toString (lib.filter (p: p != "base" && !(config.specialisation ? ${p})) cfg.control.profiles)
          }";
        }
```

- [ ] **Step 4: Green** — the negative check passes; `nix build .#checks.x86_64-linux.helm-control-eval -L --no-link`; `… host-core` (core's gaming child must still evaluate: the marker guard skips it); lint gate.
- [ ] **Step 5: Commit.**

**touches:** nixosModules/helm.nix, flake.nix
**acceptance:** helm-control-assertion-negative-profiles, helm-control-eval, host-core, lint
**commit subject:** `helm: a profile that is no declared specialisation fails the build; the negative check no longer supplies its own assert (test: helm-control-assertion-negative-profiles, helm-control-eval, host-core, lint)`

### R5 (docs, S) — the runbooks tell the truth: backup paths gated by a check, the picker's four models, the ZDR date, the ledger contract, one price table, the seat README, a stale comment [lane-runbooks-1, -3, -4, -5, -6, -8, -9, -10]

**dependsOn:** none (does not touch `docs/runbooks/helm.md` or `switch-helm-gaming.md`, which E5 owns)

**Files:**
- Modify: `docs/runbooks/backup.md` (lines 14-19), `docs/runbooks/lanes.md` (lines 117-130, 188-202, 292-300), `tools/factory/seat/README.md` (script list; lines 208-216; the price sentence at 134-135), `hosts/core/lanes.nix` (lines 7-10 comment), `flake.nix` (`core-backup-wiring`)
- Create: `docs/ledger/openrouter-prices.csv`

**Interfaces:**
- `core-backup-wiring` additionally throws when a path in `services.proton-backup.paths` is named in `docs/runbooks/backup.md` in neither its `/home/dalhaka/…` nor its `~/…` spelling.
- `docs/ledger/openrouter-prices.csv` is the one price table, in the format `tools/ledger/schema.md` §"`rollup --costs`" defines: `date,model,in_per_1m,out_per_1m,cache_read_per_1m`. Both runbooks point at it and carry no per-million price literal.

- [ ] **Step 1: The failing check.** In `flake.nix` `core-backup-wiring`'s `let`, add:

```nix
            backupDoc = builtins.readFile ./docs/runbooks/backup.md;
            homeSpelling = p: builtins.replaceStrings [ "/home/dalhaka" ] [ "~" ] p;
            undocumented = builtins.filter (
              p: !(nixpkgs.lib.hasInfix p backupDoc || nixpkgs.lib.hasInfix (homeSpelling p) backupDoc)
            ) coreCfg.services.proton-backup.paths;
```

and a new branch before the final `else`: `else if undocumented != [ ] then throw "core-backup-wiring: docs/runbooks/backup.md does not name these backup paths: ${toString undocumented}"`.
- [ ] **Step 2: Red** — `nix build .#checks.x86_64-linux.core-backup-wiring -L --no-link` → names at least `/home/dalhaka/flakes`, `/home/dalhaka/strategy` and the three per-flake memory dirs (5 of 11 paths are documented today; after E1 lands `/var/lib/evidence` joins the list — R5 names it too).
- [ ] **Step 3: Edits.**
  - `backup.md` 14-19: replace the sentence with a list of the eleven paths grouped as: this repo and `/etc/nixos`; the basket store `/var/lib/baskets/store` and `~/.config/basket`; the sibling flakes `~/flakes` and `~/strategy`; the five Claude memory directories (`~/.claude/projects/-home-dalhaka/memory`, `…/-home-dalhaka-nixos-agent-env/memory`, `…/-home-dalhaka-flakes-gaming/memory`, `…/-home-dalhaka-flakes-media/memory`, `…/-home-dalhaka-strategy/memory`); the evidence store `/var/lib/evidence`. Keep the exclude sentence.
  - `lanes.md` 117-130: drop "Not yet confirmed done as of this runbook landing (2026-09-03) — …"; the date line becomes `Date set: **2026-09-04** (operator, board entry "O1 DONE", 20:14 CDT).`
  - `lanes.md` 188-202: describe all three job kinds' ledger behaviour as `pkgs/lane/lane-run.py:446-470` implements it: a `chat` job appends on success only; a `dsh` job appends its line whatever the exit code and carries no `usage`; a refused job writes only `error`. (R5 documents; changing the dsh append is a later code task — record it as a sentence, not a promise.)
  - `lanes.md` 292-300 and `README.md` 134-135: replace both price sentences with "Rates: `docs/ledger/openrouter-prices.csv` (dated rows; `tools/ledger/factory.py rollup --costs` reads it). Hand-multiplied dollar figures are not written in prose." List the four default picker entries with their roles (`deepseek/deepseek-v4-pro-0813` default; `deepseek/deepseek-v4-flash`; `moonshotai/kimi-k3`; `z-ai/glm-5.3`; `z-ai/glm-5.3-flash` per `dsh-openrouter.sh:178`) and add the sentence "Whether the account's Non-frontier ZDR group covers the Moonshot and Z.ai entries is unverified — an operator check (claims file: open a gap when you rely on them)."
  - `docs/ledger/openrouter-prices.csv`: header plus two dated rows for DeepSeek V4 Pro and Flash carrying the figures the two documents disagreed on, each with its source date (`2026-09-03,deepseek/deepseek-v4-pro-0813,1.02,2.05,` from lanes.md and `2026-09-04,deepseek/deepseek-v4-pro-0813,0.55,2.19,` from the seat README — both kept, dated, so the ledger's date join picks the right one; a comment line is not allowed in CSV, so the provenance goes in `tools/ledger/schema.md` one sentence).
  - `README.md` 208-216: the `XDG_CACHE_HOME` paragraph now says the wrapper sets it (`pkgs/dsh-openrouter/dsh-openrouter.sh:340`) and the driver only honours an inherited override; the script list adds `factory-usage.py` (per-task token usage from a dsh transcript) and `launch-today.sh` (a dated one-shot from 2026-09-04, kept as a worked example, not for reuse).
  - `hosts/core/lanes.nix` 7-10: delete the clause "is still T2's stub (pkgs/lane/lane-run.nix)"; keep "nothing here is wantedBy anything".
- [ ] **Step 4: Green** — `nix build .#checks.x86_64-linux.core-backup-wiring -L --no-link`; `nix develop -c pytest tests/ledger -q -k costs` (the CSV header is the one the rollup parses; add a one-line test that `docs/ledger/openrouter-prices.csv` loads through the existing price-table reader); lint gate.
- [ ] **Step 5: Commit.**

**touches:** docs/runbooks/backup.md, docs/runbooks/lanes.md, tools/factory/seat/README.md, hosts/core/lanes.nix, flake.nix, docs/ledger/openrouter-prices.csv, tests/ledger/test_factory.py, tools/ledger/schema.md (the provenance sentence; the R5 gate found this file missing from the list while Step 3 directs the edit)
**acceptance:** core-backup-wiring, ledger-unit, lint
**commit subject:** `docs: runbooks match the machine — eleven backup paths gated by a check, four picker models, ZDR date, ledger contract, one price table, seat README, lanes.nix comment (test: core-backup-wiring, ledger-unit, lint)`

### R7 (code, M) — basket teardown removes every layer and cleans an interrupted mount; mount cleans up after itself [r2-2-1, r2-2-2]

**dependsOn:** none

**Files:**
- Modify: `pkgs/basket/basket.sh` (`cmd_mount`, `cmd_teardown`), `tests/unit/30-mount.bats`

**Interfaces:**
- `basket teardown <id>` succeeds when either the visible mount `$mnt` or the hidden staging tmpfs `$staging` is mounted; it unmounts each until it is no longer a mountpoint (bounded to 8 rounds, `umount -l` as the last resort with a loud warning), removes both directories, and dies naming whichever path is still mounted. It still fails loudly when neither is mounted.
- `basket mount` installs an `EXIT INT TERM` trap that tears down the staging tmpfs and both directories unless the mount reached its last step; the explicit decrypt-failure branch is subsumed by the trap.
- Red-first runs under `nix develop -c tests/run-mount-tests.sh` (namespace root); `checks.unit` skips these cases (Assumption 8).

- [ ] **Step 1: Failing tests** in `tests/unit/30-mount.bats`:

```bash
@test "teardown removes every stacked mount layer and leaves no plaintext readable" {
  basket mount store/demo --identity key.txt --runtime-dir run --size 16M
  mount --bind run/demo run/demo # a second layer on the same mountpoint
  basket teardown demo --runtime-dir run
  ! mountpoint -q run/demo
  ! mountpoint -q run/.basket-tmpfs-demo
  [ ! -e run/demo/data.txt ]
  [ ! -d run/.basket-tmpfs-demo ]
}

@test "teardown cleans a staging tmpfs left behind by an interrupted mount" {
  mkdir -p run/.basket-tmpfs-demo
  mount -t tmpfs -o size=1M basket-demo run/.basket-tmpfs-demo
  echo leak >run/.basket-tmpfs-demo/x
  run basket teardown demo --runtime-dir run
  [ "$status" -eq 0 ]
  ! mountpoint -q run/.basket-tmpfs-demo
  [ ! -d run/.basket-tmpfs-demo ]
}

@test "a mount whose decryption fails leaves no staging tmpfs and no directories" {
  age-keygen -o wrong.txt 2>/dev/null
  run basket mount store/demo --identity wrong.txt --runtime-dir run --size 16M
  [ "$status" -ne 0 ]
  ! mountpoint -q run/.basket-tmpfs-demo
  [ ! -d run/.basket-tmpfs-demo ]
  [ ! -d run/demo ]
}
```

- [ ] **Step 2: Red** — `nix develop -c tests/run-mount-tests.sh`: the stacked-layer case fails (`rmdir: Device or resource busy`, then `run/demo/data.txt` still readable); the interrupted-mount case fails (`teardown: run/demo is not mounted`, exit 1). The decrypt-failure case passes today through the explicit branch: it is the regression pin for Step 3's trap, and the reviewer proves it by deleting the `trap` line (the case then leaves `run/.basket-tmpfs-demo` mounted).
- [ ] **Step 3: Implement** in `basket.sh`. `cmd_teardown` from the `local mnt=… staging=…` line on:

```bash
  local mnt="$runtime_dir/$id" staging="$runtime_dir/.basket-tmpfs-$id"
  if ! mountpoint -q "$mnt" 2>/dev/null && ! mountpoint -q "$staging" 2>/dev/null; then
    die "teardown: $id is not mounted (neither $mnt nor $staging)"
  fi
  # A basket may carry more than one mount layer (a stray bind on top of the
  # bind); unmount until nothing is left, bounded, lazy only as a last resort.
  unmount_all() {
    local p=$1 n=0
    while mountpoint -q "$p" 2>/dev/null; do
      n=$((n + 1))
      [[ $n -le 8 ]] || die "teardown: $p still mounted after 8 rounds"
      if ! umount "$p" 2>/dev/null; then
        echo "teardown: umount $p failed, detaching lazily (open handles keep the tmpfs alive until they close)" >&2
        umount -l "$p"
      fi
    done
  }
  unmount_all "$mnt"
  [[ -d "$mnt" ]] && rmdir "$mnt"
  unmount_all "$staging"
  [[ -d "$staging" ]] && rmdir "$staging"
  if mountpoint -q "$mnt" 2>/dev/null || mountpoint -q "$staging" 2>/dev/null; then
    die "teardown: $id still mounted"
  fi
  echo "torn down $id"
```

`cmd_mount`, replacing the block from `mkdir -p "$staging" "$mnt"` to the `echo "mounted …"`:

```bash
  mkdir -p "$staging" "$mnt"
  local mount_done=0
  cleanup_mount() {
    [[ $mount_done -eq 1 ]] && return 0
    umount "$mnt" 2>/dev/null || true
    umount "$staging" 2>/dev/null || true
    rmdir "$mnt" "$staging" 2>/dev/null || true
    echo "mount: aborted; staging tmpfs torn down" >&2
  }
  trap cleanup_mount EXIT INT TERM
  mount -t tmpfs -o "size=$size,mode=0700" "basket-$id" "$staging"
  # subshell: cmd_decrypt uses die (exit); the subshell turns that into a
  # failure the trap above cleans up after.
  (cmd_decrypt "$entry" --identity "$identity" --into "$staging") || die "mount: decryption failed, tmpfs torn down"
  mount --bind "$staging" "$mnt"
  if [[ "$access" == "ro" ]]; then
    mount -o remount,bind,ro "$mnt"
  fi
  mount_done=1
  trap - EXIT INT TERM
  echo "mounted $id at $mnt ($access)"
```

- [ ] **Step 4: Green** — `nix develop -c tests/run-mount-tests.sh` (both propagation modes); `nix build .#checks.x86_64-linux.unit -L --no-link` (skips, still green); lint gate (shellcheck). Then the mutation: comment out `trap cleanup_mount EXIT INT TERM`, re-run the decrypt-failure case → `run/.basket-tmpfs-demo` is still a mountpoint; restore.
- [ ] **Step 5: Commit.**

**touches:** pkgs/basket/basket.sh, tests/unit/30-mount.bats
**acceptance:** unit, lint (plus `tests/run-mount-tests.sh` run by the implementer and the reviewer, recorded in the commit body)
**commit subject:** `basket: teardown removes every mount layer and cleans an interrupted mount; mount tears its staging tmpfs down on any failure (test: unit, lint; run-mount-tests both modes)`

### R8 (code, S) — the seat guard refuses the Helm control port and its token; the runbook names the residual [invariants-3]

**dependsOn:** none

**Files:**
- Modify: `pkgs/dsh-openrouter/hook-guard.py` (`_bash_verdict`, one regex), `tests/unit/70-dsh-openrouter.bats` (two cases), `docs/runbooks/helm.md` (one paragraph under the Profile card)

**Interfaces:**
- A bash command that names the Helm control listener (`127.0.0.1:7700`, `localhost:7700`, `[::1]:7700`) or the per-boot token path (`/run/user/<uid>/helm/token`, `$XDG_RUNTIME_DIR/helm/token`) is denied with reason `the Helm control port and its token are refused (an operator action)`; ComfyUI's `127.0.0.1:8188` and everything else stays allowed. The runbook says plainly that any process running as the operator — the seat included — can otherwise drive a root profile switch, that this guard is a tripwire with an audit record (not a boundary), and that the boundary is the password prompt Helm Home brings (claim `uid1000-can-switch-profile`).

- [ ] **Step 1: Failing tests** in `tests/unit/70-dsh-openrouter.bats`, beside the existing hook-guard cases (`assert_denied`/`assert_allowed` helpers at :626-645):

```bash
@test "hook-guard denies a command aimed at the Helm control port or its token" {
  assert_denied '{"tool_name":"Bash","tool_input":{"command":"curl -s -X POST http://127.0.0.1:7700/action/switch -d profile=gaming -d token=$(cat /run/user/1000/helm/token)"}}'
  assert_denied '{"tool_name":"Bash","tool_input":{"command":"cat $XDG_RUNTIME_DIR/helm/token"}}'
  assert_denied '{"tool_name":"Bash","tool_input":{"command":"wget -qO- localhost:7700/"}}'
}

@test "hook-guard leaves other loopback ports alone" {
  assert_allowed '{"tool_name":"Bash","tool_input":{"command":"curl -s http://127.0.0.1:8188/object_info | head -c 100"}}'
}
```

- [ ] **Step 2: Red** — `nix develop -c bats tests/unit/70-dsh-openrouter.bats -f "Helm control"` → the deny case fails (the guard emits nothing).
- [ ] **Step 3: Implement** in `hook-guard.py`, beside `_SYSTEMCTL`:

```python
# The Helm control listener and its per-boot token: a POST there starts a
# root profile switch, and every process running as the operator can read the
# token. A tripwire with an audit record, not a boundary (plan
# 2026-09-05-evidence-store R8; the boundary is Helm Home's password prompt).
_HELM_CONTROL = re.compile(
    r"(?:127\.0\.0\.1|localhost|\[::1\]|0\.0\.0\.0):7700(?:\b|/)"
    r"|/run/user/\d+/helm/token"
    r"|\$\{?XDG_RUNTIME_DIR\}?/helm/token"
)
```

and in `_bash_verdict`, after the systemctl branch: `if _HELM_CONTROL.search(command): return "the Helm control port and its token are refused (an operator action)"`. Runbook paragraph (helm.md, after the Profile description): "The switch buttons work for anything that runs as you — including the DeepSeek seat and the desktop app's Claude Code — because the page's token lives in your session. The seat's guard refuses commands that name the port or the token and records the refusal (`dsh-openrouter --denials`); that is a tripwire, not a wall. The wall is the password prompt Helm Home adds (claim `uid1000-can-switch-profile`)."
- [ ] **Step 4: Green** — bats file; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate (ruff covers the guard). Operator: relaunch the seat after the switch (hooks.json is regenerated at launch).
- [ ] **Step 5: Commit.**

**touches:** pkgs/dsh-openrouter/hook-guard.py, tests/unit/70-dsh-openrouter.bats, docs/runbooks/helm.md
**acceptance:** unit, lint
**commit subject:** `dsh: the hook guard refuses the Helm control port and its token; the runbook names the uid-1000 residual (test: unit, lint)`

### R9 (code, S) — the three local-only path lists are proven identical [invariants-5, first step]

**dependsOn:** R8 (both edit `hook-guard.py`)

**Files:**
- Create: `tests/lane/test_forbidden_lists_agree.py`
- Modify: `pkgs/lane/lane-submit.py` (`FORBIDDEN_REPO_PREFIXES`), `pkgs/dsh-openrouter/hook-guard.py` (`PROTECTED_ABSOLUTE`, `_protected_prefixes`), `pkgs/dsh-openrouter/dsh-openrouter.sh` (the `forbidden=(…)` array at :190-194)

**Interfaces:**
- One test reads all three lists — the Python tuple, the guard's absolute list plus its HOME-relative literals (with `HOME=/home/x`), and the bash array (parsed from the script text between `forbidden=(` and `)`, `$HOME` → `/home/x`) — and asserts the three sets are equal after normalising `~`/`$HOME`. The lists are edited to agree (today the guard alone names `~/.config/openrouter`; the review found the three differ). Generating the list from Nix stays a gap (claim `forbidden-list-single-source`).

- [ ] **Step 1: Failing test** — `tests/lane/test_forbidden_lists_agree.py`:

```python
import importlib.util
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def norm(p):
    return str(p).replace("$HOME", "/home/x").replace("~", "/home/x").rstrip("/")


def test_the_three_local_only_lists_agree(monkeypatch):
    monkeypatch.setenv("HOME", "/home/x")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    lane = load(ROOT / "pkgs" / "lane" / "lane-submit.py", "lane_submit")
    guard = load(ROOT / "pkgs" / "dsh-openrouter" / "hook-guard.py", "hook_guard")
    sh = (ROOT / "pkgs" / "dsh-openrouter" / "dsh-openrouter.sh").read_text()
    body = re.search(r"^forbidden=\((.*?)^\)", sh, re.S | re.M).group(1)
    bash_list = {norm(tok.strip('"')) for tok in body.split() if tok.strip('"')}
    lane_list = {norm(p) for p in lane.FORBIDDEN_REPO_PREFIXES}
    guard_list = {norm(p) for p in guard._protected_prefixes()}
    assert lane_list == guard_list == bash_list, {"lane": sorted(lane_list), "guard": sorted(guard_list), "bash": sorted(bash_list)}
```

- [ ] **Step 2: Red** — `nix develop -c pytest tests/lane/test_forbidden_lists_agree.py -q` → the assertion prints the three sets and their differences (at least `~/.config/openrouter` only in the guard).
- [ ] **Step 3: Implement** — add the missing entries to the two shorter lists so all three name the same set (`~/.claude`, `~/.config/openrouter`, `~/strategy`, `/run/baskets`, `/var/lib/baskets`, `/var/lib/helm`, `/var/lib/egress-broker`, `/var/lib/lanes`, `/var/lib/secrets`); a comment at each list points at the test and at the claim.
- [ ] **Step 4: Green** — `nix develop -c ruff format tests/lane`; `pytest tests/lane -q`; `nix build .#checks.x86_64-linux.lane-unit -L --no-link`; `… unit` (the bats refusal cases still pass); lint gate.
- [ ] **Step 5: Commit.**

**touches:** tests/lane/test_forbidden_lists_agree.py, pkgs/lane/lane-submit.py, pkgs/dsh-openrouter/hook-guard.py, pkgs/dsh-openrouter/dsh-openrouter.sh, flake.nix (the `lane-unit` check must copy `pkgs/dsh-openrouter` into the sandbox so the cross-tree test can read the guard; found by the R9 implementer)
**acceptance:** lane-unit, unit, lint
**commit subject:** `lane+dsh: the three local-only path lists are one set, proven by a test (test: lane-unit, unit, lint)`

### R10 (code, S) — the seat scripts dispatch to their own directory; `~/factory/bin` retires [lane-runbooks-2, lane-runbooks-9, process-4]

**dependsOn:** E7

**Files:**
- Modify: `tools/factory/seat/factory-lib.sh` (`FACTORY_BIN`), `tools/factory/seat/factory-task` and `tools/factory/seat/factory-review` (drop their own `XDG_CACHE_HOME` default — the wrapper sets it, R5b's README sentence promises this removal), `tools/factory/seat/README.md`, `tests/unit/80-seat-driver.bats`

**Interfaces:**
- `FACTORY_BIN` defaults to the directory of `factory-lib.sh` itself (`$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)`); `FACTORY_BIN_OVERRIDE` replaces it. The README's layout drops `bin/` from the runtime root and says the operator deletes `~/factory/bin` after this lands (Assumption 6).

- [ ] **Step 1: Failing bats test:**

```bash
@test "factory-task dispatches to the seat directory it was run from, not to FACTORY_ROOT/bin" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"
  printf '#!%s\necho DISPATCHED-TO-COPY; exit 7\n' "$REAL_BASH" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws" "$root/runs"   # no bin/
  repo="$BATS_TEST_TMPDIR/repo"; git init -q "$repo"
  FACTORY_ROOT="$root" run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 7 ]
  [[ "$output" == *DISPATCHED-TO-COPY* ]]
}
```

- [ ] **Step 2: Red** — `nix develop -c bats tests/unit/80-seat-driver.bats` → `factory-task` fails looking for `$root/bin/factory-ws` (exit 127, no marker).
- [ ] **Step 3: Implement** — in `factory-lib.sh` replace `FACTORY_BIN=$FACTORY_ROOT/bin` with `FACTORY_BIN=${FACTORY_BIN_OVERRIDE:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)}` (keep the shellcheck directive); README: layout without `bin/`, the sentence "the scripts resolve their siblings relative to their own directory; `~/factory/bin` is no longer read — delete it after the switch", and the script list gains `factory-usage.py` and `launch-today.sh` (see R5).
- [ ] **Step 4: Green** — bats; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate.
- [ ] **Step 5: Commit.**

**touches:** tools/factory/seat/factory-lib.sh, tools/factory/seat/factory-task, tools/factory/seat/factory-review, tools/factory/seat/README.md, tests/unit/80-seat-driver.bats
**acceptance:** unit, lint
**commit subject:** `factory: seat scripts dispatch to their own directory; the redundant cache-dir default goes; ~/factory/bin retires (test: unit, lint)`

### R3 (code, S) — the backup-parity and timers tiles read the unit's result, so a killed or failed run is red [r2-3-1, r2-3-3]

**dependsOn:** E6

**Files:**
- Modify: `pkgs/helm/collect.py` (`tile_backup_parity`, `tile_timers`, a new `_unit_result` helper; `_TIMER_PROPS` and `_timer_armed` stay as they are — corrected 2026-09-05 after the R3 gate), `tests/helm/test_collect.py`, `docs/runbooks/helm.md` (two sentences)

**Interfaces:**
- backup-parity: before scanning the journal, `systemctl --user show -p Result -p ExecMainStatus proton-drive-push.service`; `Result` other than `success` (or a non-zero `ExecMainStatus`) → `fail` with the unit's result named, whatever the journal says. The journal scan stays for the detail text and the age.
- timers: for every audited timer, also `show -p Result -p ExecMainStatus <name>.service` on the matching service; a last result other than `success` fails the tile naming the service (`timeout`, `oom-kill`, `exit-code`), so a nightly flake check killed by its 2 h timeout or the OOM killer is visible.

- [ ] **Step 1: Failing tests** (the existing `fake_run` table dispatches on `argv[0]`; a `systemctl` entry answers both `show` shapes — key it on the tuple prefix `("systemctl", "--user", "show")` and check `argv[-1]` in the fake):

```python
def _unit_show(result, status="0", active="active", nxt="Sat 2026-09-06 03:00:00 UTC"):
    return cp(f"ActiveState={active}\nNextElapseUSecRealtime={nxt}\nNextElapseUSecMonotonic=\nResult={result}\nExecMainStatus={status}\n")


def test_parity_unit_failure_beats_a_stale_ok_line(monkeypatch, tmp_path):
    line = json.dumps({"MESSAGE": "proton-backup-push: OK snapshots=1 remote=1", "__REALTIME_TIMESTAMP": str(int(NOW.timestamp() * 1e6) - 3600 * 1e6)})
    monkeypatch.setattr(collect, "run", fake_run({"journalctl": cp(line + "\n"), "systemctl": _unit_show("exit-code", "1")}))
    t = collect.tile_backup_parity(base_cfg(tmp_path), NOW)
    assert t["status"] == "fail" and "exit-code" in t["summary"]


def test_parity_unit_success_keeps_the_journal_verdict(monkeypatch, tmp_path):
    line = json.dumps({"MESSAGE": "proton-backup-push: OK snapshots=1 remote=1", "__REALTIME_TIMESTAMP": str(int(NOW.timestamp() * 1e6) - 3600 * 1e6)})
    monkeypatch.setattr(collect, "run", fake_run({"journalctl": cp(line + "\n"), "systemctl": _unit_show("success")}))
    assert collect.tile_backup_parity(base_cfg(tmp_path), NOW)["status"] == "ok"


def test_timers_service_timeout_is_fail(monkeypatch, tmp_path):
    cfg = base_cfg(tmp_path)
    cfg["timers_user"] = ["helm-flake-check.timer"]

    def table(argv, timeout=10.0, env=None):
        if argv[0] == "systemctl" and argv[-1].endswith(".timer"):
            return _unit_show("success")
        if argv[0] == "systemctl" and argv[-1].endswith(".service"):
            return _unit_show("timeout", "0", active="failed", nxt="")
        raise FileNotFoundError(argv[0])

    monkeypatch.setattr(collect, "run", table)
    t = collect.tile_timers(cfg, NOW)
    assert t["status"] == "fail" and "helm-flake-check.service" in t["summary"] and "timeout" in t["summary"]
```

Existing parity tests get `"systemctl": _unit_show("success")` added to their tables; existing timer tests' tables must answer the `.service` query with `_unit_show("success")` too.
- [ ] **Step 2: Red** — `pytest tests/helm -q -k "parity_unit or service_timeout"` → the unit-failure case reads `ok`, the timeout case reads `ok`.
- [ ] **Step 3: Implement** — a helper `_unit_result(scope_args, unit)` running `systemctl <scope> show -p Result -p ExecMainStatus <unit>` and returning `(result, status)`; in `tile_backup_parity` call it for `proton-drive-push.service` first and return `("fail", f"proton-drive-push.service last result {result}", detail)` when `result != "success"` or `status not in ("0", "")`; in `tile_timers` after `_timer_armed`, query the sibling service (`t[:-len(".timer")] + ".service"`) and add it to `offenders` as `f"{service}: {result}"` when the result is not `success` (a service that never ran reports `Result=success`, so a fresh install is not red). Runbook: two sentences under **backup-parity** and **timers** saying the tile now reads the unit's own last result, so a push that failed or a nightly check that was killed shows red even when the last log line was a success.
- [ ] **Step 3b (added 2026-09-05 from the E6b gate's two minors, same file):** (i) `main()`'s write path records history *after* annotating, so on the run where a verdict changes `annotate_since` falls through to `status["generated_at"]` (microsecond `+00:00` form) while every later run reports the row's `…Z` form — two shapes in one field. Fix: on the write path call `record_status(cfg, status, now)` **before** the `annotate_since` block (the `--print` path still records nothing), and assert on `main()`'s write-path `status.json` that every tile's `since` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`. (ii) The write path's recording is unpinned (deleting the whole `record_status` try/except leaves every test green): add `test_write_path_records_history` — a sibling of `test_print_does_not_write_history` that calls `collect.main(["--config", cfg_path])` with the same fakes and an `--out` under `tmp_path`, then asserts `tmp_path/"evidence"/"helm-status.jsonl"` exists and its single row has `kind == "helm-status"` and `reason == "change"`. Red first for both: (i) fails on the shape today; (ii) fails after temporarily deleting the write-path `record_status` call.
- [ ] **Step 4: Green** — `ruff format`; `pytest tests/helm -q`; `helm-unit`; lint gate.
- [ ] **Step 5: Commit.**

**touches:** pkgs/helm/collect.py, tests/helm/test_collect.py, docs/runbooks/helm.md
**acceptance:** helm-unit, lint
**commit subject:** `helm: backup-parity and timers read the unit's last result — a failed push or a killed nightly check is red (test: helm-unit, lint)`

### R3r (code, XS) — re-plan of R3 after its fix round (board rule A1): the timers tile's tests pin unit and scope everywhere, both offender groups are named, the empty-status arm goes

**dependsOn:** R3b (branch `task/R3b`: the implementation is correct; two gates found its tests vacuous — R3 on parity, R3b on the user-scope timers branch)

**Files:**
- Modify: `tests/helm/test_collect.py` (`test_timers_service_timeout_is_fail`, a new combined-offenders test, delete `test_parity_empty_exec_status_is_ok`), `pkgs/helm/collect.py` (`tile_backup_parity`'s status guard and `_unit_result`'s docstring only)

**Interfaces:** unchanged from R3. The test fake for every `systemctl show` call is `systemctl_fake(<unit -> output>, scope="user"|"system")` (already in the file): it asserts `argv[:3] == ["systemctl", "--user", "show"]` for `scope="user"` (and refuses `--user` for `scope="system"`), answers by `argv[-1]` (the unit name), and answers an unlisted unit with `_unit_show("success")` — so a wrong unit or a wrong scope reads as success and the test goes red.

- [ ] **Step 1: Failing tests.** (a) Replace the local `table` fake in `test_timers_service_timeout_is_fail` with `monkeypatch.setattr(collect, "run", systemctl_fake({"helm-flake-check.timer": _unit_show("success"), "helm-flake-check.service": _unit_show("timeout", "0", active="failed", nxt="")}, scope="user"))`; keep its assertions (`summary == "failed: helm-flake-check.service: timeout"`). (b) Add:

```python
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
```

  (c) Delete `test_parity_empty_exec_status_is_ok` and its fixture comment.
- [ ] **Step 2: Red, by mutation** (the code is already correct, so each new assertion is proven by the mutant it kills — apply, run `nix develop -c pytest tests/helm -q`, revert): M7 — in `tile_timers`'s user loop `_unit_result(["--user"], service)` → `_unit_result([], service)` → (a) fails; M12 — the same call → `_unit_result([], "not-a-real-unit.service")` → (a) fails; M10 — `return "fail", "; ".join(parts), detail` → `return "fail", parts[0], detail` → (b) fails.
- [ ] **Step 3: Implement** the one code change: in `tile_backup_parity` `status not in ("0", "")` → `status != "0"`, and `_unit_result`'s docstring says: "systemd always emits ExecMainStatus as an integer (probed on core: a never-run unit and a non-existent unit both print `Result=success` / `ExecMainStatus=0`); when systemctl prints nothing at all `result` is empty and the `result != "success"` clause already reds the tile." Remove the comment that claimed otherwise.
- [ ] **Step 4: Green** — `ruff format`; `pytest tests/helm -q` (144 tests: 145 − 1 deleted + 1 added − … count what you get and name it in the result); `nix build .#checks.x86_64-linux.helm-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**touches:** pkgs/helm/collect.py, tests/helm/test_collect.py
**acceptance:** helm-unit, lint
**commit subject:** `helm: timers tests pin unit and scope in user scope too; unarmed and failed offenders both named; the empty-status arm goes (test: helm-unit, lint)`

---

## Not in this plan (recorded, not dropped)

- Helm Home sub-project 1: planned separately after four decisions (who calls polkit and what the page's Switch does; where the declaration checker lives — a `lib.checkHelmDeclaration` export, since sibling flakes are not inputs; the raise mechanism on Wayland — gsettings keybinding, Shell extension or the GlobalShortcuts portal; the flakes option shape). The review's proposed waves H51–H59 are in the report's addendum (`helm-home-10`).
- `nixpkgs-host` pin refresh (claim `nixpkgs-host-pin-age`, owner operator): its own plan with a closure diff.
- A JS formatter and linter (claim `js-formatter-linter-missing`): a new language landing rule, one task, after this plan.
- The dsh-kind lane ledger append on failure; basket `verify` payload binding; the seat's key exception; declared agents on the live host: claims with owners and dates, closed by later tasks or decisions.

## Self-review against the paper's mechanisms

| mechanism (digest §1–2) | task | note |
|---|---|---|
| evidence bundle with verified vs gap, bound to an execution record | E1 (observations), E2 (claims with class and `check@rev`, prose refused), E9 (the bundle) | "source presence never counts": a claim is verified only by a check at a revision or an operator drill |
| plan rebuilt from spec + evidence, START HERE replaced not appended | E8 (START HERE replaced, facts removed), E9 (facts generated) | the lint gate enforces the shape |
| roles by permission; QA on a frozen candidate that cannot repair | already true (dark factory, Opus gate); E3 makes each result name its task, round and label | no change to roles |
| structure over extra passes (A1) | landed 2026-09-04 (board rule + N12) | unchanged |
| warm start | already true (worktrees off the integration tip) | unchanged |
| regressions tracked across loops (17 of 81 reopened in the paper) | E6 (verdict history with since), E5 (a failing observation that covers HEAD is red at once), R3 (a killed run is red) | Helm shows how long a tile has been red |
| evidence-feedback channel into the next plan | E3 (run report), E4 (attribution), E7 (checks recorded once, reused) | the next START HERE reads the bundle, not a transcript |
| the review's defects closed with tests | R1 (broker blocker), R2, R4, R5, R7, R8, R9, R10, R3 | each names its finding id |
| not imported | magnitudes, blinded QA, unattended multi-day autonomy, one model for all roles | per the digest §3–4 |
