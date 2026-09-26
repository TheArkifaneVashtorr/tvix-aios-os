"""debug_sweep — the debug sweep's investigator: harvest the four bug
signals, fold them by signature, print the dry run and write the batch
record (plan 2026-09-23-debug-sweep, DS3).

`tools/debug/investigate` execs this module. Python 3 stdlib only, like
every module under pkgs/evidence: it runs on the operator's host and inside
the seat's confinement. The four signals are the inbox (bug-note lines), the
seat rows (failed/partial task results with an error class), the checks
stream (a name whose newest row at an ancestor of HEAD failed) and the bug
ledger's open, untasked rows. Rejected gate verdicts are never read here.
DS4 adds the confined runner: one Sonnet diagnosis per item (`run_item`,
`run_claude`, `confinement`); DS7 adds the batch loop that drives them
(`run_batch`: rung 1 three at once, rung 2 once for the hard ones with
rung 1's diagnosis as the prior, resume, D6: no rung 3); DS5 adds the
report: one Opus pass writes `report-body.md` (`PROMPT_REPORT`,
`render_report_prompt`), the script checks it (`body_check`), writes the
front matter and `report.md` and the one repo file (`front_matter`,
`write_report`).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence
import streams

SIG_RE = re.compile(r"^(seat|check|bug|note):[A-Za-z0-9._:-]{1,120}$")
FAIL_LINE_PREFIXES = ("not ok ", "FAILED ", "error: ")
HARVEST_STATUSES = ("failed", "partial")
DEFAULT_LIMIT = 10
WINDOW_DAYS = 14
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
HEX_RUN_RE = re.compile(r"[0-9a-f]{7,}")
DIGITS_RE = re.compile(r"[0-9]+")
WS_RE = re.compile(r"\s+")
TAP_NO_RE = re.compile(r"^not ok \d+ ")
STORE_PATH_RE = re.compile(r"/nix/store/[0-9a-z]{32}-")
REV40_RE = re.compile(r"[0-9a-f]{40}")
BATCH_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{4}(-\d+)?$")
WORD_L = r"(?<![A-Za-z0-9_])"
WORD_R = r"(?![A-Za-z0-9_])"


def normalise(text: str) -> str:
    """Lowercase, fold every maximal hex/digit run to `#`, collapse spaces."""
    out = text.lower()
    out = HEX_RUN_RE.sub("#", out)
    out = DIGITS_RE.sub("#", out)
    return WS_RE.sub(" ", out).strip()


def h12(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def failing_line(log_tail: str) -> str:
    """The one line a signature is hashed over (DS3 Interface 3): ANSI
    stripped, the first producer line (bats `not ok`, pytest `FAILED`, nix
    `error:`), else the last non-empty line, then normalised."""
    lines = [ANSI_RE.sub("", ln).strip() for ln in (log_tail or "").splitlines()]
    raw = ""
    for ln in lines:
        if ln.startswith(FAIL_LINE_PREFIXES):
            raw = ln
            break
    if not raw:
        for ln in reversed(lines):
            if ln:
                raw = ln
                break
    raw = TAP_NO_RE.sub("not ok ", raw)
    raw = STORE_PATH_RE.sub("/nix/store/*-", raw)
    raw = REV40_RE.sub("<rev>", raw)
    return WS_RE.sub(" ", raw).strip()


def _git(repo, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _is_ancestor(repo, rev: str, head: str) -> bool:
    if not rev or not head:
        return False
    return _git(repo, "merge-base", "--is-ancestor", rev, head).returncode == 0


def _parse_inbox_line(line: str):
    """(ts, reporter, symptom) for one inbox line, None when torn or not an
    object."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    ts, reporter, symptom = obj.get("ts"), obj.get("reporter"), obj.get("symptom")
    if not (
        isinstance(ts, str) and isinstance(reporter, str) and isinstance(symptom, str)
    ):
        return None
    return ts, reporter, symptom


def _item(kind: str, signatures: list[str]) -> dict:
    return {
        "id": None,
        "kind": kind,
        "signatures": signatures,
        "evidence": [],
        "occurrences": 0,
        "wall_s": 0,
        "sink": None,
    }


def harvest(repo, store, runs, home, since, recheck, stats=None):
    """The four signals as items, in source order: inbox, seat, check, bug."""
    if stats is None:
        stats = {}
    items: list[dict] = []

    notes: dict[str, dict] = {}
    skipped = 0
    inbox = pathlib.Path(home) / "inbox.jsonl"
    if inbox.is_file():
        with open(inbox) as fh:
            for line in fh:
                if not line.strip():
                    continue
                parsed = _parse_inbox_line(line)
                if parsed is None:
                    skipped += 1
                    continue
                ts, reporter, symptom = parsed
                if not ts > since:
                    continue
                sig = f"note:{h12(normalise(symptom))}"
                note = notes.setdefault(sig, _item("note", [sig]))
                note["evidence"].append(
                    {"src": "inbox", "ref": f"{ts}+{reporter}", "ts": ts}
                )
                note["occurrences"] += 1
    if skipped:
        stats["skipped_inbox"] = stats.get("skipped_inbox", 0) + skipped
    items.extend(notes.values())

    seats: dict[str, dict] = {}
    for row in evidence.read(store, "derived/tasks"):
        if row.get("kind") != "task-result":
            continue
        if row.get("status") not in HARVEST_STATUSES:
            continue
        ec = row.get("error_class")
        if ec in (None, "none"):
            continue
        mtime = row.get("result_mtime") or ""
        if not mtime > since:
            continue
        item = seats.setdefault(ec, _item("seat", []))
        item["signatures"].append(f"seat:{ec}:{row.get('key', '')}")
        item["evidence"].append(
            {"src": "seat", "ref": row.get("result_path") or "", "ts": mtime}
        )
        item["occurrences"] += 1
        item["wall_s"] += row.get("wall_s") or 0
    for item in seats.values():
        item["signatures"] = sorted(set(item["signatures"]))
    items.extend(seats.values())

    cp = _git(repo, "rev-parse", "HEAD")
    head = cp.stdout.strip() if cp.returncode == 0 else ""
    if head:
        by_name: dict[str, list[dict]] = {}
        for row in evidence.read(store, "checks"):
            if row.get("kind") != "check":
                continue
            by_name.setdefault(str(row.get("name", "")), []).append(row)
        for name in sorted(by_name):
            eligible = [
                r for r in by_name[name] if _is_ancestor(repo, r.get("rev") or "", head)
            ]
            if not eligible:
                continue
            newest = eligible[0]
            for r in eligible[1:]:
                if r.get("ts", "") >= newest.get("ts", ""):
                    newest = r
            if newest.get("ok") is not False:
                continue
            fails = [r for r in eligible if r.get("ok") is False]
            item = _item(
                "check",
                [f"check:{name}:{h12(failing_line(newest.get('log_tail') or ''))}"],
            )
            item["evidence"].append(
                {
                    "src": "check",
                    "ref": f"{name}@{newest.get('rev', '')}",
                    "ts": newest.get("ts", ""),
                }
            )
            item["occurrences"] = len(fails)
            item["wall_s"] = sum(r.get("duration_s") or 0 for r in fails)
            items.append(item)

    for row in _load_bugs(repo):
        if row.get("status") == "open" and row.get("task", "") == "":
            item = _item("bug", [f"bug:{row.get('id', '')}"])
            item["evidence"].append(
                {
                    "src": "bug",
                    "ref": str(row.get("id", "")),
                    "ts": str(row.get("found", "")),
                }
            )
            item["occurrences"] = 1
            items.append(item)
    return items


def _load_bugs(repo) -> list[dict]:
    path = pathlib.Path(repo) / "docs" / "ledger" / "bugs.toml"
    if not path.is_file():
        return []
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return []
    rows = data.get("bug", [])
    return rows if isinstance(rows, list) else []


def _sig_token(sig: str) -> str | None:
    """The `<KEY>` of a seat signature or the `<name>` of a check signature;
    None for every other shape (a bug row never sinks those)."""
    parts = sig.split(":")
    if parts[0] == "seat" and len(parts) >= 3:
        return parts[2]
    if parts[0] == "check" and len(parts) >= 2:
        return parts[1]
    return None


def build_sinks(repo, signatures) -> dict[str, str]:
    """signature -> sink name: every diagnosis file's front-matter items
    (whatever their decision) and every open, tasked bug row whose symptom
    or evidence names the signature's key/name as a whole word."""
    sinks: dict[str, str] = {}
    repo = pathlib.Path(repo)
    for path in sorted((repo / "docs" / "diagnoses").glob("*.md")):
        try:
            text = path.read_text()
        except OSError:
            continue
        if not text.startswith("+++"):
            continue
        end = text.find("+++", 3)
        if end < 0:
            continue
        try:
            data = tomllib.loads(text[3:end])
        except tomllib.TOMLDecodeError:
            continue
        for entry in data.get("item", []):
            if not isinstance(entry, dict):
                continue
            for sig in entry.get("signatures", []) or []:
                if isinstance(sig, str):
                    sinks[sig] = f"diagnosis:{path.name}:{entry.get('id', '')}"
    for row in _load_bugs(repo):
        if row.get("status") == "open" and row.get("task"):
            hay = f"{row.get('symptom', '')} {row.get('evidence', '')}"
            for sig in signatures:
                tok = _sig_token(sig)
                if not tok:
                    continue
                pattern = WORD_L + re.escape(tok) + WORD_R
                if re.search(pattern, hay):
                    sinks[sig] = f"bug:{row.get('id', '')}"
    return sinks


def fold(items, sinks, recheck, limit=None):
    """Remove sunk signatures, drop emptied items, sort by impact
    ((occurrences, wall_s) descending, D7) and cut to `limit`."""
    kept: list[dict] = []
    folded: list[str] = []
    for item in items:
        sigs = item.get("signatures", [])
        kept_sigs = [s for s in sigs if s not in sinks or s in recheck]
        for s in sigs:
            if s in sinks and s not in recheck:
                folded.append(f"{s} -> {sinks[s]}")
        if not kept_sigs:
            continue
        kept.append({**item, "signatures": kept_sigs})
    kept.sort(
        key=lambda it: (it.get("occurrences", 0), it.get("wall_s", 0)), reverse=True
    )
    if limit is not None:
        kept = kept[:limit]
    return kept, folded


def assign_ids(items):
    """item-01, item-02, ... in impact order; an item that carries an id
    keeps it."""
    for i, it in enumerate(items, 1):
        if not it.get("id"):
            it["id"] = f"item-{i:02d}"
    return items


def _batch_dirs(home) -> list[pathlib.Path]:
    home = pathlib.Path(home)
    if not home.is_dir():
        return []
    return sorted(
        p for p in home.iterdir() if p.is_dir() and BATCH_DIR_RE.match(p.name)
    )


def _meta_lines(path: pathlib.Path) -> list[str]:
    try:
        return (path / "batch.meta").read_text().splitlines()
    except OSError:
        return []


def batch_open(home, since, items, argv, head, confined=1, limit=DEFAULT_LIMIT):
    """`<home>/<YYYY-MM-DDTHHMM[-N]>/batch.meta`: the seven fields, one
    `item=` line per item, no `end=` line."""
    home = pathlib.Path(home)
    home.mkdir(parents=True, exist_ok=True)
    start = evidence.now_iso()
    base = start[:16].replace(":", "")
    bid = base
    n = 2
    while (home / bid).exists():
        bid = f"{base}-{n}"
        n += 1
    path = home / bid
    path.mkdir()
    assign_ids(items)
    lines = [
        f"start={start}",
        f"since={since}",
        f"head={head}",
        f"items={len(items)}",
        f"limit={limit}",
        f"confined={confined}",
        f"command={' '.join(str(x) for x in argv)}",
    ]
    for it in items:
        lines.append(
            "item=" + " ".join([it.get("id") or ""] + list(it.get("signatures", [])))
        )
    (path / "batch.meta").write_text("\n".join(lines) + "\n")
    return path


def batch_close(path):
    """Append `end=<ts>` — the one file rewritten in place (read, add, "w")."""
    meta = pathlib.Path(path) / "batch.meta"
    text = meta.read_text()
    with open(meta, "w") as fh:
        fh.write(text.rstrip("\n") + f"\nend={evidence.now_iso()}\n")


def batch_resume(home):
    """The newest batch directory whose batch.meta has no `end=` line."""
    for path in reversed(_batch_dirs(home)):
        lines = _meta_lines(path)
        if not lines:
            continue
        if any(ln.startswith("end=") for ln in lines):
            continue
        return path
    return None


def default_since(home, now) -> str:
    """The start of the newest finished batch; `now - WINDOW_DAYS` days."""
    best = None
    for path in _batch_dirs(home):
        lines = _meta_lines(path)
        if not any(ln.startswith("start=") for ln in lines):
            continue
        if not any(ln.startswith("end=") for ln in lines):
            continue
        best = next(ln.split("=", 1)[1] for ln in lines if ln.startswith("start="))
    if best is not None:
        return best
    return (now - datetime.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _items_from_meta(batch: pathlib.Path) -> list[dict]:
    items = []
    for line in _meta_lines(batch):
        if not line.startswith("item="):
            continue
        parts = line[5:].split()
        items.append(
            {
                "id": parts[0] if parts else None,
                "kind": None,
                "signatures": parts[1:],
                "evidence": [],
                "occurrences": 0,
                "wall_s": 0,
                "sink": None,
            }
        )
    return items


def diagnosis_validate(obj) -> list[str]:
    """One `<field>: <reason>` message per defect; [] when the diagnosis
    object is valid."""
    if not isinstance(obj, dict):
        return ["diagnosis: not an object"]
    errs: list[str] = []
    for field in ("symptom", "repro", "root_cause", "fix", "draft_section"):
        if not isinstance(obj.get(field), str):
            errs.append(f"{field}: required")
    if isinstance(obj.get("symptom"), str) and not obj["symptom"].strip():
        errs.append("symptom: required")
    sigs = obj.get("signatures")
    if not isinstance(sigs, list) or not sigs:
        errs.append("signatures: required")
    else:
        for s in sigs:
            if not isinstance(s, str) or not SIG_RE.match(s):
                errs.append(f"signatures: not a signature: {s}")
    conf = obj.get("confidence")
    if not isinstance(conf, str) or conf not in ("confirmed", "probable", "unknown"):
        errs.append(f"confidence: must be confirmed, probable or unknown: {conf!r}")
    ev_rows = obj.get("evidence")
    if not isinstance(ev_rows, list):
        errs.append("evidence: required")
    else:
        for e in ev_rows:
            if (
                not isinstance(e, dict)
                or not isinstance(e.get("file"), str)
                or not isinstance(e.get("note"), str)
                or not (e.get("line") is None or isinstance(e.get("line"), int))
            ):
                errs.append("evidence: each entry needs file, line and note")
    if conf in ("confirmed", "probable"):
        if isinstance(obj.get("repro"), str) and not obj["repro"].strip():
            errs.append(f"repro: required for {conf}")
        if isinstance(obj.get("root_cause"), str) and not obj["root_cause"].strip():
            errs.append(f"root_cause: required for {conf}")
        if isinstance(ev_rows, list) and not ev_rows:
            errs.append(f"evidence: required for {conf}")
    return errs


def parse_since(value: str) -> str:
    """A date (UTC midnight) or an RFC3339 Z timestamp, canonicalised to
    `YYYY-MM-DDTHH:MM:SSZ`; ValueError otherwise."""
    try:
        return datetime.date.fromisoformat(value).strftime("%Y-%m-%dT00:00:00Z")
    except ValueError:
        pass
    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(value) from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- DS4: the confined runner, one diagnosis per item ------------------------
#
# Every model call runs behind a fake in the tests and behind the real pair
# only in §Operator: `confinement` builds the bwrap argv (the mount namespace
# is the boundary, D11) and `run_claude` the investigator argv; the deny
# spelling list is the belt under it. The two argvs are the Global
# Constraints' shapes, byte for byte.

HIDDEN_HOME = (
    ".config/openrouter",
    ".config/restic",
    ".ssh",
    ".gnupg",
    ".config/gh",
)
HIDDEN_ABS = ("/var/lib/secrets",)
TOOLS_DIAGNOSIS = "Bash,Read,Edit,Write,Grep,Glob"
RESULT_KEYS = (
    "status",
    "confidence",
    "rung",
    "model",
    "wall_s",
    "exit_code",
    "repro_rc",
    "draft",
    "evidence_modified",
    "repo_modified",
    "confined",
    "cost_usd",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "num_turns",
    "session_id",
    "diagnosis",
)

PROMPT_RUNG1 = """\
You are diagnosing one recurring failure of this repository's factory. You
propose; you never fix. Your working directory is a throwaway clone of the
repository at the batch's head; nothing you change in it is kept.

## The item

Signatures (one per piece of evidence):
{signatures}

Evidence (read-only; paths under {runs} and {store} are the factory's own
records and are never modified):
{evidence}

## Method: the four phases, in this order

1. Reproduce: find the smallest command that shows the failure in this clone,
   or in the evidence, before forming any opinion.
2. Compare with a working case: a run, a test or a commit that did not fail
   this way, and name the difference.
3. One hypothesis at a time: state it, run the one command that would refute
   it, keep or drop it; read, build, run tests and try mutants in the clone.
4. Propose: only after 1-3, write the root cause and the fix in prose.

## Rules

- Work only in this clone and {item_dir}. Never commit, never push, never
  touch the operator's checkout, never write docs/ledger/bugs.toml or any
  file under docs/superpowers/plans.
- confidence is "confirmed" only when you ran the repro in this clone and it
  exited 0; otherwise "probable" (a cause shown, not reproduced) or "unknown"
  (no cause shown). The script re-runs your repro in a pristine clone and
  demotes a "confirmed" it cannot reproduce.
- A second defect you meet on the way is noted, never chased:
  tools/debug/bug-note "<symptom>" --evidence <path|run/KEY|commit>

## Output: the one file that counts

Write {item_dir}/diagnosis.json, a JSON object with exactly these keys:
  symptom        one sentence
  signatures     the signatures above, as a list of strings
  repro          one `bash -c` command that exits 0 while the defect exists,
                 run from the repository root; "" when you have none
  root_cause     what is wrong and why, with file:line references
  evidence       a list of {{"file": "<repo-relative path>", "line": <int or
                 null>, "note": "<what this shows>"}}
  confidence     "confirmed" | "probable" | "unknown"
  fix            the proposed fix, in prose
  draft_section  a complete task section in this repository's plan format
                 ("### <KEY> (code, XS|S|M) — <title>" with dependsOn,
                 touches, acceptance, commit subject, a red-first test and
                 its mutants), or "" when you cannot write one
Nothing else you print is read.
"""


class ConfinementMissing(Exception):
    """The confinement binary named by DEBUG_SWEEP_BWRAP cannot be resolved:
    the investigator runs confined or not at all."""

    def __init__(self, name):
        super().__init__(f"confinement binary not found: {name}")
        self.name = name


def _claude_bin() -> str:
    """DEBUG_SWEEP_CLAUDE (default `claude`), resolved on PATH; a name with a
    directory part is used verbatim so a test's absolute path survives."""
    name = os.environ.get("DEBUG_SWEEP_CLAUDE") or "claude"
    if os.path.dirname(name):
        return name
    return shutil.which(name) or name


def investigator_argv(
    claude, model, tools, budget_usd, max_turns, add_dirs, runs, store
):
    """The Global Constraints' investigator argv: the prompt travels on stdin,
    never argv (a brief over 131072 bytes died on execve, session 35); DENY
    names the runs and store roots so the file tools cannot touch them."""
    deny = (
        "Bash(git commit*) Bash(git push*) Bash(sudo*) Bash(nixos-rebuild*) "
        "Bash(systemctl*) Bash(nix-collect-garbage*) "
        f"Edit({runs}/**) Write({runs}/**) Edit({store}/**) Write({store}/**)"
    )
    argv = [
        claude,
        "-p",
        "--model",
        model,
        "--output-format",
        "json",
        "--permission-mode",
        "acceptEdits",
        "--permission-prompts",
        "none",
        "--allowedTools",
        "Bash",
        "--no-session-persistence",
        "--restricted",
        "--tools",
        tools,
        "--max-budget-usd",
        str(budget_usd),
        "--max-turns",
        str(max_turns),
        "--disallowedTools",
        deny,
    ]
    for d in add_dirs:
        argv += ["--add-dir", str(d)]
    return argv


def run_claude(
    prompt,
    model,
    cwd,
    add_dirs,
    tools,
    budget_usd,
    max_turns,
    log_fh,
    timeout_s,
    confine,
    *,
    runs=None,
    store=None,
):
    """One model call: `confine + investigator argv` when confine is a list,
    else the investigator argv alone. The deny roots default to the
    documented overrides (FACTORY_RUNS, EVIDENCE_STORE) so a bare call (DS5's
    report pass) names the same roots run_item does. Returns the RunResult
    dict; every blob field is read nullable, a missing key is None, never a
    failure (Assumption 4)."""
    if runs is None:
        runs = os.environ.get("FACTORY_RUNS") or os.path.expanduser("~/factory/runs")
    if store is None:
        store = os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    claude = _claude_bin()
    argv = (confine or []) + investigator_argv(
        claude, model, tools, budget_usd, max_turns, add_dirs, runs, store
    )
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    t0 = time.monotonic()
    try:
        cp = subprocess.run(
            argv,
            input=prompt,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=log_fh,
            text=True,
            env=env,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _run_result(
            exit_code=124, wall_s=int(time.monotonic() - t0), blob=None, timed_out=True
        )
    except FileNotFoundError:
        log_fh.write(f"not found: {argv[0]}\n")
        return _run_result(
            exit_code=127, wall_s=int(time.monotonic() - t0), blob=None, timed_out=False
        )
    blob = None
    if cp.stdout:
        try:
            parsed = json.loads(cp.stdout)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            blob = parsed
    if blob is None and cp.stdout:
        log_fh.write(cp.stdout)
        if not cp.stdout.endswith("\n"):
            log_fh.write("\n")
    return _run_result(
        exit_code=cp.returncode,
        wall_s=int(time.monotonic() - t0),
        blob=blob,
        timed_out=False,
    )


def _run_result(exit_code, wall_s, blob, timed_out):
    """RunResult: the seven usage fields, every one read with .get so an
    absent key is None (a `-` in .result, a null in the row)."""
    usage = (blob or {}).get("usage")
    usage = usage if isinstance(usage, dict) else {}
    return {
        "exit_code": exit_code,
        "wall_s": wall_s,
        "blob": blob,
        "cost_usd": (blob or {}).get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "cache_creation_tokens": usage.get("cache_creation_input_tokens"),
        "num_turns": (blob or {}).get("num_turns"),
        "session_id": (blob or {}).get("session_id"),
        "timed_out": timed_out,
    }


def confinement(repo, runs, store, rw):
    """The Global Constraints' confinement argv, or None when
    DEBUG_SWEEP_BWRAP is `none` (recorded, D15). Raises ConfinementMissing
    when the binary cannot be resolved — the investigator runs confined or
    not at all. A --tmpfs is emitted only for a HIDDEN directory that exists
    (bwrap cannot create a mount point on the read-only root, F14), and
    --tmpfs /tmp precedes every --bind."""
    name = os.environ.get("DEBUG_SWEEP_BWRAP") or "bwrap"
    if name == "none":
        return None
    bin_path = shutil.which(name)
    if bin_path is None:
        raise ConfinementMissing(name)
    home = pathlib.Path(os.environ["HOME"])
    argv = [bin_path, "--ro-bind", "/", "/"]
    argv += ["--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp"]
    for rel in HIDDEN_HOME:
        hp = home / rel
        if hp.is_dir():
            argv += ["--tmpfs", str(hp)]
    for p in HIDDEN_ABS:
        if pathlib.Path(p).is_dir():
            argv += ["--tmpfs", p]
    for d in (repo, runs, store):
        if pathlib.Path(d).is_dir():
            argv += ["--ro-bind", str(d), str(d)]
    for d in rw:
        argv += ["--bind", str(d), str(d)]
    argv += [
        "--bind",
        str(home / ".claude"),
        str(home / ".claude"),
        "--bind",
        str(home / ".cache"),
        str(home / ".cache"),
    ]
    claude_json = home / ".claude.json"
    if claude_json.is_file():
        argv += ["--bind", str(claude_json), str(claude_json)]
    argv += ["--die-with-parent", "--new-session", "--"]
    return argv


def _run_key(ref: str) -> tuple[str, str]:
    """(run, KEY) from a seat result path — ~/factory/runs/<run>/<KEY>.result
    or any absolute shape: the parent's name and the stem."""
    p = pathlib.PurePosixPath(ref)
    return p.parent.name, p.stem


def render_prompt(item, item_dir, runs, store) -> str:
    """PROMPT_RUNG1 filled: one signature per line, one evidence line per
    entry (`- <src> <ref> <ts>`), a seat's ref spelled as the absolute
    <runs>/<run>/<KEY>.result and .log paths the investigator can read."""
    sig_lines = "\n".join(item.get("signatures") or [])
    ev_lines = []
    for e in item.get("evidence") or []:
        ref = str(e.get("ref") or "")
        if e.get("src") == "seat" and ref:
            run, key = _run_key(ref)
            if run and key:
                ref = f"{runs}/{run}/{key}.result {runs}/{run}/{key}.log"
        ev_lines.append(f"- {e.get('src')} {ref} {e.get('ts')}")
    return PROMPT_RUNG1.format(
        signatures=sig_lines,
        evidence="\n".join(ev_lines),
        runs=str(runs),
        store=str(store),
        item_dir=str(item_dir),
    )


def repo_state(repo) -> tuple:
    """The checkout guard's tuple: HEAD, the sha256 of the ref list and the
    porcelain lines (D12). Declared gap: an operator edit during the batch
    also trips it — honest, and one item re-run."""
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    refs = _git(repo, "for-each-ref", "--format=%(refname) %(objectname)").stdout
    status = _git(repo, "status", "--porcelain").stdout
    return (
        head,
        hashlib.sha256(refs.encode()).hexdigest(),
        frozenset(status.splitlines()),
    )


def evidence_paths(item, runs) -> list[pathlib.Path]:
    """Every <runs>/<run>/<KEY>.* file a seat item's evidence names; a check,
    bug or note item cites no seat files, so its list is empty."""
    runs_p = pathlib.Path(runs)
    if item.get("kind") != "seat":
        return []  # a non-seat item cites no seat files
    paths: list[pathlib.Path] = []
    for e in item.get("evidence") or []:
        run, key = _run_key(str(e.get("ref") or ""))
        if run and key:
            paths.extend(sorted((runs_p / run).glob(f"{key}.*")))
    return paths


def snapshot(paths) -> dict:
    """(size, mtime_ns) per path, taken before the run; a path that cannot be
    stat'd is recorded as None (its appearance is then a change)."""
    snap = {}
    for p in paths:
        try:
            st = p.stat()
        except OSError:
            snap[str(p)] = None
        else:
            snap[str(p)] = (st.st_size, st.st_mtime_ns)
    return snap


def evidence_modified(before) -> bool:
    """Any change or disappearance among the snapshotted paths. The store's
    own files are never snapshotted: other writers append to them
    legitimately."""
    for path, was in before.items():
        try:
            st = pathlib.Path(path).stat()
        except OSError:
            return True
        if was is None or (st.st_size, st.st_mtime_ns) != was:
            return True
    return False


def clone_at(repo, dst, head) -> int:
    """A throwaway clone of `repo` at `head` (tracked files only, F11): --local
    --no-checkout, checkout, then `remote remove origin` so no push can reach
    the checkout. A resumed item re-clones over its own earlier copy (DS7),
    so an existing destination is removed first. The first non-zero git
    exit; 0 when all three succeed."""
    dst = pathlib.Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    for args in (
        ["clone", "--local", "--quiet", "--no-checkout", str(repo), str(dst)],
        ["-C", str(dst), "checkout", "-q", str(head)],
        ["-C", str(dst), "remote", "remove", "origin"],
    ):
        cp = _git(repo, *args)
        if cp.returncode != 0:
            return cp.returncode
    return 0


def repro_check(pristine, repro) -> int:
    """The diagnosis's repro, re-run in the pristine clone: the exit code
    (124 on timeout). A `confirmed` whose repro fails is demoted, D5."""
    try:
        cp = subprocess.run(
            ["bash", "-c", repro],
            cwd=str(pristine),
            timeout=300,
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124
    return cp.returncode


DRAFT_FRAME = (
    "# Draft\n"
    "\n"
    "## Global Constraints\n"
    "- placeholder\n"
    "\n"
    "## Assumptions\n"
    "- placeholder\n"
    "\n"
    "## Waves\n"
    "- placeholder\n"
    "\n"
    "## Operator\n"
    "- placeholder\n"
    "\n"
)


def draft_check(pristine, item_dir, section) -> str:
    """`none` (no section), `valid` (the graph check accepts the draft on the
    pristine clone, F11) or `draft-invalid`; the first stderr line of a
    refusal is kept in <item_dir>/draft.reason for run_item to copy into
    .result as draft_reason. The draft and the repos file are kept."""
    if not (section or "").strip():
        return "none"
    item_dir = pathlib.Path(item_dir)
    draft = item_dir / "draft.md"
    draft.write_text(DRAFT_FRAME + section.rstrip("\n") + "\n")
    repos_file = item_dir / "repos.toml"
    repos_file.write_text(
        '[[repo]]\nname = "nixos-agent-env"\npath = "' + str(pristine) + '"\n'
    )
    dc = subprocess.run(
        [
            sys.executable,
            str(pathlib.Path(pristine) / "pkgs" / "evidence" / "tasks.py"),
            "--root",
            str(pristine),
            "--repos",
            str(repos_file),
            "--runs-dir",
            "/nonexistent",
            "--store",
            "/nonexistent",
            "check",
            "--draft",
            str(draft),
        ],
        cwd=str(pristine),
        timeout=120,
        capture_output=True,
        text=True,
        check=False,
    )
    if dc.returncode == 0:
        return "valid"
    first = next(
        (ln for ln in (dc.stderr or "").splitlines() if ln.strip()),
        "check failed",
    )
    (item_dir / "draft.reason").write_text(first + "\n")
    return "draft-invalid"


def record_usage(store, batch_id, item, rung, model, result) -> dict:
    """One ledger/debug-usage row (DS2's declaration): the nullable blob
    fields travel as null, never as strings; no free text."""
    sigs = item.get("signatures") or []
    row = {
        "kind": "debug-usage",
        "batch": batch_id,
        "item": item.get("id") or "",
        "rung": rung,
        "model": model,
        "status": result["status"],
        "confidence": result["confidence"],
        "wall_s": result["wall_s"],
        "signature": sigs[0] if sigs else "",
        "cost_usd": result["cost_usd"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cache_read_tokens": result["cache_read_tokens"],
        "cache_creation_tokens": result["cache_creation_tokens"],
        "num_turns": result["num_turns"],
        "session_id": result["session_id"],
    }
    return evidence.append(str(store), "ledger/debug-usage", row)


def _record_usage_safe(store, batch_id, item, rung, model, result, log_fh):
    """record_usage with the one refusal the sweep survives: a refused row is
    one log line, never a failed item (Interface 9). Any other exception
    propagates — a kill here costs one duplicate row on resume, never a lost
    one."""
    try:
        record_usage(store, batch_id, item, rung, model, result)
    except streams.StreamRefused as exc:
        log_fh.write(f"usage refused: {exc}\n")


def _fmt_result(value) -> str:
    return "-" if value is None else str(value)


def _write_result(path, result, draft_reason=None):
    """The 19 key: value lines in the Global Constraints' order, then the
    optional draft_reason line after diagnosis."""
    lines = [f"{k}: {_fmt_result(result[k])}" for k in RESULT_KEYS]
    if draft_reason is not None:
        lines.append(f"draft_reason: {draft_reason}")
    pathlib.Path(path).write_text("\n".join(lines) + "\n")


def _read_json(path):
    try:
        with open(path) as fh:
            obj = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    return obj


def run_item(
    batch,
    item,
    rung,
    model,
    repo,
    runs,
    store,
    budget,
    head,
    timeout_s=3600,
    prior="",
) -> dict:
    """One item: clone, confine, one model call, then the diagnosis checks
    (repro in a pristine clone, draft on the graph checker), the checkout
    guard, the usage row and only then .result — a kill between the last two
    costs one duplicate row on resume, never a lost one."""
    batch = pathlib.Path(batch)
    iid = item.get("id") or "item"
    suffix = ".r2" if rung == 2 else ""
    item_dir = batch / iid / "r2" if rung == 2 else batch / iid
    log_path = batch / f"{iid}{suffix}.log"
    result_path = batch / f"{iid}{suffix}.result"
    diag_copy = batch / f"{iid}{suffix}.diagnosis.json"
    result = {
        "status": "failed",
        "confidence": "none",
        "rung": rung,
        "model": model,
        "wall_s": 0,
        "exit_code": 0,
        "repro_rc": None,
        "draft": "none",
        "evidence_modified": 0,
        "repo_modified": 0,
        "confined": 0 if os.environ.get("DEBUG_SWEEP_BWRAP", "bwrap") == "none" else 1,
        "cost_usd": None,
        "input_tokens": None,
        "output_tokens": None,
        "cache_read_tokens": None,
        "cache_creation_tokens": None,
        "num_turns": None,
        "session_id": None,
        "diagnosis": "-",
        "draft_reason": None,
    }
    with open(log_path, "w") as log_fh:
        item_dir.mkdir(parents=True, exist_ok=True)
        ws = item_dir / "ws"
        clone_rc = clone_at(repo, ws, head)
        if clone_rc != 0:
            result["exit_code"] = clone_rc
            _write_result(result_path, result)
            return result
        before = repo_state(repo)
        snap = snapshot(evidence_paths(item, runs))
        confine = confinement(repo, runs, store, rw=[ws, item_dir])
        result["confined"] = 0 if confine is None else 1
        rr = run_claude(
            render_prompt(item, item_dir, runs, store) + prior,
            model,
            cwd=ws,
            add_dirs=[item_dir, runs, store],
            tools=TOOLS_DIAGNOSIS,
            budget_usd=budget,
            max_turns=90 if rung == 2 else 60,
            log_fh=log_fh,
            timeout_s=timeout_s,
            confine=confine,
            runs=runs,
            store=store,
        )
        result["exit_code"] = rr["exit_code"]
        result["wall_s"] = rr["wall_s"]
        result["cost_usd"] = rr["cost_usd"]
        result["input_tokens"] = rr["input_tokens"]
        result["output_tokens"] = rr["output_tokens"]
        result["cache_read_tokens"] = rr["cache_read_tokens"]
        result["cache_creation_tokens"] = rr["cache_creation_tokens"]
        result["num_turns"] = rr["num_turns"]
        result["session_id"] = rr["session_id"]
        result["repo_modified"] = 1 if repo_state(repo) != before else 0
        result["evidence_modified"] = 1 if evidence_modified(snap) else 0
        obj = None
        if rr["timed_out"]:
            result["status"] = "timeout"
        elif rr["exit_code"] != 0:
            result["status"] = "failed"
        else:
            raw = _read_json(item_dir / "diagnosis.json")
            if raw is None:
                log_fh.write("diagnosis.json: absent or unparseable\n")
            else:
                errs = diagnosis_validate(raw)
                if errs:
                    log_fh.writelines(err + "\n" for err in errs)
                else:
                    obj = raw
            if obj is None:
                # absent, unparseable or refused by the validator
                result["status"], result["confidence"] = "failed", "none"
            else:
                result["status"] = "done"
                result["confidence"] = obj["confidence"]
                pristine = item_dir / "pristine"
                if clone_at(repo, pristine, head) != 0:
                    result["status"] = "failed"
                else:
                    repro = (obj.get("repro") or "").strip()
                    if repro:
                        result["repro_rc"] = repro_check(pristine, repro)
                    if result["confidence"] == "confirmed" and (
                        not repro or result["repro_rc"]
                    ):
                        result["confidence"] = "probable"
                        obj["confidence"] = "probable"
                    result["draft"] = draft_check(
                        pristine, item_dir, obj.get("draft_section") or ""
                    )
                    if result["draft"] == "draft-invalid":
                        result["draft_reason"] = (
                            (item_dir / "draft.reason").read_text().strip()
                        )
                    diag_copy.write_text(
                        json.dumps(
                            {**obj, "rung": rung, "model": model},
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    result["diagnosis"] = diag_copy.name
        if result["repo_modified"] or result["evidence_modified"]:
            result["status"] = "failed"
        _record_usage_safe(store, batch.name, item, rung, model, result, log_fh)
        _write_result(result_path, result, result["draft_reason"])
        return result


def _print_dry_run(since, head, items, folded, stats):
    print(f"since: {since}")
    print(f"head: {head}")
    kinds = {"seat": 0, "check": 0, "bug": 0, "note": 0}
    for it in items:
        kinds[it.get("kind")] = kinds.get(it.get("kind"), 0) + 1
    print(
        f"harvested: {len(items)} items ({kinds['seat']} seat, {kinds['check']} check, "
        f"{kinds['bug']} bug, {kinds['note']} note)"
    )
    for it in items:
        sigs = it.get("signatures", [])
        line = f"{it.get('id')} {it.get('occurrences', 0)} {it.get('wall_s', 0)} "
        line += sigs[0] if sigs else "-"
        if len(sigs) > 1:
            line += f" [+{len(sigs) - 1} more]"
        print(line)
    for f in folded:
        print(f"folded: {f}")
    n = stats.get("skipped_inbox", 0)
    if n:
        print(f"skipped: {n} inbox lines")


# --- DS7: the batch loop — three at once, Opus once, resume -----------------
#
# D6: rung 1 is Sonnet, rung 2 is a fresh Opus run with rung 1's diagnosis
# and record pasted as the prior, and there is no rung 3.


PROMPT_PRIOR = """\

## Prior: rung 1 (Sonnet) could not settle this item

Rung 1 ended with confidence "{confidence}". Its diagnosis, verbatim:
{diagnosis_json}

Its record:
{result_lines}

rung 1 could not show: {gaps}
Start from what it found; do not repeat what it showed; show what it could
not, or say "unknown" with the evidence that rules each hypothesis out.
"""


def _repro_rc_from(result_lines: str):
    """The repro_rc of a .result text; '-' and absent are None."""
    for ln in (result_lines or "").splitlines():
        if ln.startswith("repro_rc:"):
            value = ln.split(":", 1)[1].strip()
            try:
                return int(value)
            except ValueError:
                return None
    return None


def prior_block(diagnosis: dict, result_lines: str) -> str:
    """PROMPT_PRIOR filled: rung 1's diagnosis verbatim (the copied JSON),
    its record verbatim, and the comma-joined gaps it leaves behind —
    `nothing named` when it leaves none."""
    diag = diagnosis if isinstance(diagnosis, dict) else {}
    gaps: list[str] = []
    if (diag.get("repro") or "") == "":
        gaps.append("repro (empty)")
    if (diag.get("root_cause") or "") == "":
        gaps.append("root_cause (empty)")
    if not diag.get("evidence"):
        gaps.append("evidence (none)")
    conf = diag.get("confidence")
    if conf == "unknown":
        gaps.append("confidence (unknown)")
    rc = _repro_rc_from(result_lines)
    if rc:
        gaps.append(f"repro exited {rc}")
    return PROMPT_PRIOR.format(
        confidence=conf,
        diagnosis_json=json.dumps(diag, indent=2, sort_keys=True),
        result_lines=(result_lines or "").rstrip("\n"),
        gaps=", ".join(gaps) if gaps else "nothing named",
    )


def rung2_wanted(results: list[dict], order: list[str]) -> list[str]:
    """The ids that climb to rung 2 (Interface 3), in impact order: every
    `unknown`, and a `probable` only inside the top third by impact
    (ceil(n/3) of the batch's order)."""
    by_id = {r.get("id"): r.get("confidence") for r in results}
    top = math.ceil(len(order) / 3)
    return [
        iid
        for pos, iid in enumerate(order)
        if by_id.get(iid) == "unknown" or (by_id.get(iid) == "probable" and pos < top)
    ]


def read_result_file(path) -> dict:
    """A .result file's `key: value` lines as a dict; {} when absent."""
    try:
        text = pathlib.Path(path).read_text()
    except OSError:
        return {}
    out: dict[str, str] = {}
    for ln in text.splitlines():
        if ": " in ln:
            key, value = ln.split(": ", 1)
            out[key] = value
    return out


def _any_repo_modified(results) -> bool:
    """True when any parsed .result says the checkout guard tripped (D12)."""
    return any(r.get("repo_modified") == "1" for r in results)


def _meta_field(batch, name: str) -> str:
    for ln in _meta_lines(batch):
        if ln.startswith(name + "="):
            return ln.split("=", 1)[1]
    return ""


def _confined_flag() -> int:
    """`0` when the confinement switch is `none` (recorded, D15), else `1`."""
    return 0 if os.environ.get("DEBUG_SWEEP_BWRAP", "bwrap") == "none" else 1


def _print_batch(batch, items):
    """`batch: <path>` and one line per item: its newest result, rung 2 over
    rung 1; a missing record is named, not hidden."""
    print(f"batch: {batch}")
    for it in items:
        iid = it.get("id") or "item"
        res = read_result_file(pathlib.Path(batch) / f"{iid}.r2.result")
        if not res:
            res = read_result_file(pathlib.Path(batch) / f"{iid}.result")
        if not res:
            print(f"{iid} missing missing r1 0s -")
            continue
        print(
            f"{iid} {res.get('status', '-')} {res.get('confidence', '-')} "
            f"r{res.get('rung', '-')} {res.get('wall_s', '0')}s "
            f"{res.get('cost_usd', '-')}"
        )


def _drain(pool, futures) -> None:
    """Wait for the submitted futures; a repo_modified result stops the rung
    (Interface 1): the queued jobs are cancelled, the ones already running
    finish first. An exception from run_item is one stderr line — the
    .result file is the record, and its absence is the failure."""
    for fut in concurrent.futures.as_completed(list(futures)):
        try:
            result = fut.result()
        except Exception as exc:  # noqa: BLE001 - the .result is the record
            print(f"item: {exc}", file=sys.stderr)
            continue
        if result.get("repo_modified") == 1:
            pool.shutdown(wait=False, cancel_futures=True)
            pool.shutdown(wait=True)
            break


def run_batch(args, batch_dir=None) -> int:
    """The batch loop (Interface 1). Rung 1 (Sonnet, `--budget`) over every
    item without a `.result`, at most three at once; rung 2 (Opus, three
    times the budget, rung 1's diagnosis as the prior) for every `unknown`
    and every top-third `probable` with no `.r2.result`; then `batch_close`,
    the per-item lines and the report pass (DS5) when the exit is 0 or 5.
    Exit 0 clean, 5 any failed or timeout, 6 a report that did not land
    (Interface 4), 7 a tripped checkout guard (no rung 2, no report), 8 no
    confinement, 130 interrupted (no `end=`; the next run resumes)."""
    batch = (
        pathlib.Path(batch_dir) if batch_dir is not None else batch_resume(args.home)
    )
    if batch is None:
        print(
            "investigate: no batch to run and none open under --home",
            file=sys.stderr,
        )
        return 3
    bwrap = os.environ.get("DEBUG_SWEEP_BWRAP") or "bwrap"
    if bwrap != "none" and shutil.which(bwrap) is None:
        print(
            "investigate: bwrap not on PATH — the investigator runs confined"
            " or not at all (DEBUG_SWEEP_BWRAP=none to override)",
            file=sys.stderr,
        )
        return 8
    head = _meta_field(batch, "head")
    items = _items_from_meta(batch)
    budget = float(args.budget)
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)
    try:
        futures = {}
        for it in items:
            iid = it.get("id") or "item"
            if (batch / f"{iid}.result").exists():
                print(f"skip {iid}: result exists")
                continue
            futures[
                pool.submit(
                    run_item,
                    batch,
                    it,
                    1,
                    "sonnet",
                    args.repo,
                    args.runs,
                    args.store,
                    budget,
                    head,
                )
            ] = iid
        _drain(pool, futures)
        results = [
            {
                "id": it.get("id"),
                **read_result_file(batch / f"{it.get('id')}.result"),
            }
            for it in items
        ]
        if not _any_repo_modified(results):
            order = [it.get("id") for it in items]
            futures = {}
            for iid in rung2_wanted(results, order):
                if (batch / f"{iid}.r2.result").exists():
                    continue
                item = next(x for x in items if x.get("id") == iid)
                prior = prior_block(
                    _read_json(batch / f"{iid}.diagnosis.json") or {},
                    (batch / f"{iid}.result").read_text(),
                )
                futures[
                    pool.submit(
                        run_item,
                        batch,
                        item,
                        2,
                        "opus",
                        args.repo,
                        args.runs,
                        args.store,
                        budget * 3,
                        head,
                        prior=prior,
                    )
                ] = iid
            _drain(pool, futures)
    except KeyboardInterrupt:
        pool.shutdown(wait=False, cancel_futures=True)
        return 130
    pool.shutdown(wait=True)
    batch_close(batch)
    _print_batch(batch, items)
    parsed: list[dict] = []
    bad = False
    for it in items:
        iid = it.get("id") or "item"
        rung1 = read_result_file(batch / f"{iid}.result")
        rung2 = read_result_file(batch / f"{iid}.r2.result")
        parsed += [rung1, rung2]
        if not rung1 or {**rung1, **rung2}.get("status") in ("failed", "timeout"):
            bad = True
    if _any_repo_modified(parsed):
        return 7
    rc = 5 if bad else 0
    if run_report_pass(
        batch, args.repo, args.runs, args.store, budget * REPORT_BUDGET_X
    ):
        return 6
    return rc


# --- DS5: the batch report — one Opus pass, the script's front matter -------
#
# The report is two halves: the model writes report-body.md (one confined
# Opus pass over the batch directory, Read/Write/Grep/Glob only); the script
# writes everything else — the front matter (Interface 1), the body check
# (Interface 3), report.md and the one repo file (Interface 4). The body
# check is the proxy for "invents nothing": a cited file does not prove the
# sentence is in it (the gap is declared there); the operator reads the
# report and marks each item.

TOOLS_REPORT = "Read,Write,Grep,Glob"
REPORT_MAX_TURNS = 40
REPORT_TIMEOUT_S = 1800
REPORT_BUDGET_X = 3  # question 2 answered 5: the report pass gets 15
BODY_HEADING_RE = re.compile(r"^## ([A-Za-z0-9._-]+) — ")
BODY_CITATION_RE = re.compile(r"\(([^()]*\.diagnosis\.json)\)")

PROMPT_REPORT = """\
You are merging one debug-sweep batch's diagnoses into its report body.
Invent nothing: every sentence cites a diagnosis file; a "probable" or
"unknown" diagnosis is called that, never "confirmed".

## The batch's records

Read these files, all in this directory:
{files}

## Output: the one file that counts

Write {output}, a Markdown body, nothing else:
- for every item, in this order:
{order}
  one section "## <id> — <title>" whose paragraphs each end with a citation
  "(<file>.diagnosis.json)" naming the diagnosis file the claim comes from;
- items that share one root cause are written once, under the first id, with
  a line "merged: <id2>, <id3>" in that section — every item still has its
  own heading, and a merged item's section names the section that carries it;
- a "probable" or "unknown" diagnosis is called that, never "confirmed";
- no other sections; write nothing outside this file.
"""


def render_report_prompt(batch) -> str:
    """PROMPT_REPORT filled: batch.meta and every diagnosis file in the
    batch, and the items in the front matter's order (batch.meta's)."""
    batch = pathlib.Path(batch)
    names = ["batch.meta"] + sorted(p.name for p in batch.glob("*.diagnosis.json"))
    order = [it.get("id") or "" for it in _items_from_meta(batch)]
    return PROMPT_REPORT.format(
        files="\n".join(f"- {name}" for name in names),
        order="\n".join(f"- {iid}" for iid in order),
        output=str(batch / "report-body.md"),
    )


def _toml_str(text: str) -> str:
    """A TOML basic string (json.dumps spells one TOML accepts)."""
    return json.dumps(text)


def _fm_number(rec: dict, key: str) -> float:
    """A .result field as a float, 0.0 when absent, `-` or not a number."""
    try:
        return float(rec.get(key, "-"))
    except ValueError:
        return 0.0


def front_matter(batch) -> str:
    """Interface 1: the report's front matter — TOML between '+++' fence
    lines. Per item: confidence/rung/status/diagnosis from the newest record
    (rung 2 over rung 1), cost_usd the sum over rungs (0.0 when unknown),
    wall_s the sum of the rungs' wall times, occurrences the signature count
    of the batch.meta line — the batch record carries no occurrence figure
    (a seat item's equals it; declared gap); merged_into and decision are
    the operator's to edit, and pending, launch, hold and drop are all sinks
    for the next batch (Interface 5)."""
    batch = pathlib.Path(batch)
    fields: dict[str, str] = {}
    item_lines: list[str] = []
    for ln in _meta_lines(batch):
        if ln.startswith("item="):
            item_lines.append(ln[5:])
        elif "=" in ln:
            key, value = ln.split("=", 1)
            fields[key] = value
    out = ["+++", f"batch = {_toml_str(batch.name)}"]
    for key in ("start", "end", "since", "head"):
        out.append(f"{key} = {_toml_str(fields.get(key, ''))}")
    out.append(f"limit = {fields.get('limit', str(DEFAULT_LIMIT))}")
    out.append(f"confined = {'false' if fields.get('confined') == '0' else 'true'}")
    for entry in item_lines:
        parts = entry.split()
        iid = parts[0] if parts else ""
        rung1 = read_result_file(batch / f"{iid}.result")
        rung2 = read_result_file(batch / f"{iid}.r2.result")
        newest = rung2 or rung1
        cost = _fm_number(rung1, "cost_usd") + _fm_number(rung2, "cost_usd")
        wall = int(_fm_number(rung1, "wall_s")) + int(_fm_number(rung2, "wall_s"))
        diagnosis = newest.get("diagnosis", "-")
        out += [
            "",
            "[[item]]",
            f"id = {_toml_str(iid)}",
            "signatures = [" + ", ".join(_toml_str(s) for s in parts[1:]) + "]",
            f"confidence = {_toml_str(newest.get('confidence', 'none'))}",
            f"rung = {newest.get('rung', '1')}",
            f"status = {_toml_str(newest.get('status', 'failed'))}",
            f"occurrences = {max(len(parts) - 1, 0)}",
            f"wall_s = {wall}",
            f"cost_usd = {cost!r}",
            f"diagnosis = {_toml_str('' if diagnosis == '-' else diagnosis)}",
            'merged_into = ""',
            'decision = "pending"',
        ]
    out.append("+++")
    return "\n".join(out) + "\n"


def _merged_pairs(body: str) -> list[tuple[str, str]]:
    """(section id, merged id) pairs, one per id on a `merged:` line inside
    that section."""
    pairs: list[tuple[str, str]] = []
    section: str | None = None
    for ln in body.splitlines():
        m = BODY_HEADING_RE.match(ln)
        if m:
            section = m.group(1)
            continue
        if section is not None and ln.strip().startswith("merged:"):
            for mid in ln.strip()[len("merged:") :].split(","):
                if mid.strip():
                    pairs.append((section, mid.strip()))
    return pairs


def body_check(batch, body, item_ids) -> list[str]:
    """Interface 3: one message per defect, [] when the body is clean —
    every batch id exactly one `## <id> — ` heading, every citation a file
    in the batch, every `merged:` id in the batch and not the section's own,
    no section for an id outside the batch. The proxy for "invents
    nothing": a cited file does not prove the sentence is in it (the gap is
    this docstring); the report is the operator's to read."""
    batch = pathlib.Path(batch)
    ids = list(item_ids)
    errs: list[str] = []
    counts: dict[str, int] = {}
    for ln in body.splitlines():
        m = BODY_HEADING_RE.match(ln)
        if m:
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    for iid in ids:
        n = counts.get(iid, 0)
        if n == 0:
            errs.append(f"{iid}: no section")
        elif n > 1:
            errs.append(f"{iid}: {n} sections")
    for hid in counts:
        if hid not in ids:
            errs.append(f"{hid}: not in the batch")
    for name in sorted({m.group(1) for m in BODY_CITATION_RE.finditer(body)}):
        if not (batch / name).is_file():
            errs.append(f"{name}: not a file in the batch")
    for sec, mid in _merged_pairs(body):
        if mid == sec:
            errs.append(f"{mid}: merged into its own section")
        elif mid not in ids:
            errs.append(f"{mid}: merged id not in the batch")
    return errs


def _fill_merged(fm: str, merged: dict[str, str]) -> str:
    """The front matter with merged_into filled from the body's `merged:`
    lines (the section id each id was merged under)."""
    out: list[str] = []
    cur: str | None = None
    for ln in fm.splitlines():
        m = re.match(r'^id = "(.*)"$', ln)
        if m:
            cur = m.group(1)
        if ln == 'merged_into = ""' and cur in merged:
            out.append(f'merged_into = "{merged[cur]}"')
        else:
            out.append(ln)
    return "\n".join(out)


def _report_invalid(batch: pathlib.Path, msgs: list[str], body) -> None:
    """Interface 4's refusal path: the messages to report.log (opened "w"),
    report.md still written with the marker as its first line, the front
    matter and the body kept for the operator's eye; nothing reaches the
    repo."""
    with open(batch / "report.log", "w") as fh:
        fh.writelines(m + "\n" for m in msgs)
    text = f"<!-- report-invalid: {len(msgs)} defects, see report.log -->\n\n"
    text += front_matter(batch)
    if body is not None:
        text += "\n" + body.rstrip("\n") + "\n"
    (batch / "report.md").write_text(text)


def write_report(batch, repo):
    """Interface 4: report.md (the front matter with merged_into filled, a
    blank line, the body, the Decisions section), then the one repo write —
    docs/diagnoses/<batch date>-batch.md, a same-day collision suffixing
    -batch-2, -3, ... — created with shutil.copyfile; prints `report:
    docs/diagnoses/<name>` and returns the path. A body that is absent or
    refused by the check writes report.md with the invalid marker and
    report.log, nothing into the repo, and returns None."""
    batch = pathlib.Path(batch)
    repo = pathlib.Path(repo)
    ids = [it.get("id") or "" for it in _items_from_meta(batch)]
    body_path = batch / "report-body.md"
    if not body_path.is_file():
        _report_invalid(batch, ["report-body.md: not written"], None)
        return None
    body = body_path.read_text()
    errs = body_check(batch, body, ids)
    if errs:
        _report_invalid(batch, errs, body)
        return None
    merged = {mid: sec for sec, mid in _merged_pairs(body)}
    fm = _fill_merged(front_matter(batch), merged)
    decisions = "\n".join(
        f'{iid}: pending — edit decision = "pending" in the front matter '
        "to launch, hold or drop"
        for iid in ids
    )
    (batch / "report.md").write_text(
        fm + "\n\n" + body.rstrip("\n") + "\n\n## Decisions\n\n" + decisions + "\n"
    )
    dest_dir = repo / "docs" / "diagnoses"
    dest_dir.mkdir(parents=True, exist_ok=True)
    date = batch.name[:10]
    name = f"{date}-batch.md"
    n = 2
    while (dest_dir / name).exists():
        name = f"{date}-batch-{n}.md"
        n += 1
    shutil.copyfile(batch / "report.md", dest_dir / name)
    rel = pathlib.Path("docs") / "diagnoses" / name
    print(f"report: {rel}")
    return rel


def run_report_pass(batch, repo, runs, store, budget) -> int:
    """Interfaces 2 and 4: the one Opus pass — the batch directory its cwd
    and its one writable dir besides the two homes, report.log its log —
    then write_report. 0 when the report landed (the caller keeps its own
    exit), 6 when it did not (the caller exits 6)."""
    batch = pathlib.Path(batch)
    with open(batch / "report.log", "w") as log_fh:
        run_claude(
            render_report_prompt(batch),
            "opus",
            cwd=batch,
            add_dirs=[],
            tools=TOOLS_REPORT,
            budget_usd=budget,
            max_turns=REPORT_MAX_TURNS,
            log_fh=log_fh,
            timeout_s=REPORT_TIMEOUT_S,
            confine=confinement(repo, runs, store, rw=[batch]),
            runs=runs,
            store=store,
        )
    return 0 if write_report(batch, repo) is not None else 6


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    p = argparse.ArgumentParser(
        prog="investigate",
        description="harvest the four bug signals, fold by signature, dry-run the batch",
    )
    p.add_argument("--since", help="a date or an RFC3339 Z timestamp")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p.add_argument(
        "--budget",
        type=float,
        default=5.0,
        help="the per-item dollar cap for a rung-1 Sonnet run (rung 2 gets 3x)",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--recheck", action="append", default=None)
    p.add_argument("--new", action="store_true")
    p.add_argument(
        "--home",
        default=os.environ.get("DEBUG_SWEEP_HOME")
        or os.path.expanduser("~/factory/debug"),
    )
    p.add_argument(
        "--repo",
        default=os.environ.get("DEBUG_SWEEP_REPO")
        or str(pathlib.Path(__file__).resolve().parents[2]),
    )
    p.add_argument(
        "--store",
        default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE,
    )
    p.add_argument(
        "--runs",
        default=os.environ.get("FACTORY_RUNS") or os.path.expanduser("~/factory/runs"),
    )
    a = p.parse_args(argv)
    rechecks = a.recheck or []

    if a.limit < 1:
        print(f"investigate: --limit must be >= 1 (got {a.limit})", file=sys.stderr)
        return 2
    since = None
    if a.since is not None:
        try:
            since = parse_since(a.since)
        except ValueError:
            print("investigate: --since: not a date", file=sys.stderr)
            return 2
    for sig in rechecks:
        if not (isinstance(sig, str) and SIG_RE.match(sig)):
            print(f"investigate: --recheck: not a signature: {sig}", file=sys.stderr)
            return 2
    if not os.path.isdir(a.store):
        print(f"investigate: store unreadable: {a.store}", file=sys.stderr)
        return 3
    cp = _git(a.repo, "rev-parse", "HEAD")
    head = cp.stdout.strip() if cp.returncode == 0 else ""
    if not head:
        print(f"investigate: not a git repository: {a.repo}", file=sys.stderr)
        return 3

    recheck = set(rechecks)
    if since is None:
        since = default_since(a.home, datetime.datetime.now(datetime.timezone.utc))
    resume = None if a.new else batch_resume(a.home)
    stats: dict = {}
    if resume is not None:
        print(f"investigate: resume {resume.name}", file=sys.stderr)
        items = _items_from_meta(resume)
        folded = []
    else:
        items = harvest(a.repo, a.store, a.runs, a.home, since, recheck, stats=stats)
        sinks = build_sinks(
            a.repo, [s for it in items for s in it.get("signatures", [])]
        )
        items, folded = fold(items, sinks, recheck, limit=a.limit)
    assign_ids(items)

    if a.dry_run:
        _print_dry_run(since, head, items, folded, stats)
        return 0
    if resume is not None:
        bdir = resume
    else:
        bdir = batch_open(
            a.home, since, items, argv, head, confined=_confined_flag(), limit=a.limit
        )
    return run_batch(a, bdir)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
