"""Derived task graph: plans are the nodes and edges, status is a derivation (plan 2026-09-05-session-context, G1/G4).

The dependency-satisfaction set handed to `derive_status` and `waves` is a set
of `(repo, chain_root)` pairs, never a bare root: a task's `depends_on` keys are
resolved in the namespace of the repo that DEFINES the task (a local task ->
this repo; an imported task -> its defining repo), and "landed" is judged in the
repo the resolved dependency is ATTRIBUTED to. Each task carries a `dep_repo`
map (`chain root -> attributed repo`) so `derive_status` and `waves` can key
satisfaction without leaking one repo's landed root into another repo's
same-named local key.

`scan_repo` publishes two namespace maps consumed by `check` and by the
scheduler: `imported` (`task key -> defining repo`, for tasks another repo's
plan files attribute here) and `resolved_elsewhere` (the `(repo, chain_root)`
pairs this repo's tasks depend on that are landed in another repo — never a
root this repo itself defines locally).

`read_results` returns ONE entry per `(repo, key)`: a live `.log` counts as
`running` only while it is stale-free and newer than any `.result`; otherwise
the newest `.result` wins (rule 3 stays reachable — a stale newest log does not
discard an older run's `.result`).

`--root` points the graph at a tree: `main` runs `bind_root` over the repos it
loads, rebinding the single `ledger = true` repo's `path` to that tree, so the
repo's plans, manifest and grandfather list come from the tree under test, not
the live clone `repos.toml` names. Only `touches` and `probes` (which read a
plan file by path) return before that binding; `repos.toml`'s `--repos` and the
four overlays (`plan-status`, `claims`, `task-status`, `runs-dir`/`store`) are
governed separately by `--root`/their own flags."""

from __future__ import annotations

import argparse
import datetime
import difflib
import fnmatch
import glob
import json
import math
import os
import pathlib
import re
import shlex
import statistics
import subprocess
import sys
import time

import streams
import tomllib

HEADING_RE = re.compile(
    r"^### (?P<key>[A-Za-z][A-Za-z0-9-]*) \((?P<kind>code|docs), (?P<size>XS|S|M|L)\) [—-] (?P<title>.+)$"
)
FIELD_RE = re.compile(
    r"^\*\*(?P<name>dependsOn|touches-exempt|touches|acceptance|areas|repo|commit subject|probe_env):\*\*\s*(?P<value>.*)$"
)
KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
# The `**probes:**` grammar: a bullet `- <name>: `<command>` :: <op>[ <value>] ::
# <provenance>`. `name` is lowercase-minus-32; the command is the text between
# the first and last backtick (a tab inside it is refused); `provenance` is
# non-empty. `probe_env` tokens are `NAME=VALUE` with an uppercase name.
PROBE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
PROBE_ENV_TOKEN_RE = re.compile(r"^[A-Z_][A-Z0-9_]*=[^ ]*$")
PROBE_DECIMAL_RE = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
PROBE_NUM_OPS = ("le", "lt", "ge", "gt")
PROBE_STR_OPS = ("eq", "ne")
PROBE_NONE_OPS = ("empty", "nonempty")
PROBE_OPS = PROBE_NUM_OPS + PROBE_STR_OPS + PROBE_NONE_OPS
# DF13: a probe on an open key that can only hold before the task lands is a
# plan defect the driver's post-commit evaluation finds every time — a
# provenance note naming the pre-state (`pre-state`, `before`, `(… after)`)
# or a command pinning a line number (`sed -n 'Np'`).
PRE_STATE_NOTE_RE = re.compile(r"pre-state|\bbefore\b|\([^)]*\bafter\)")
LINE_PIN_RE = re.compile(r"sed -n '[0-9]+p'|sed -n '[0-9]+,[0-9]+p'")
# DF16: a `**Steps.**` command that lands the task's own work — merging main
# (`git merge main`, `git merge origin/main`, or `git pull … main`) or restoring
# the board block (`write-board`, in either the `evidence tasks write-board` or
# `tasks.py … write-board` spelling). Matching runs only over backtick/fence
# text (see `_steps_land_spans`), never bare prose.
STEPS_LAND_RE = re.compile(
    r"git merge (?:origin/)?main|git pull\b.*\bmain\b"
    r"|evidence tasks write-board|tasks\.py\b.*write-board"
)
# EV19: a `**touches-exempt:** <path> — <reason>` line separates its path from
# its reason at the first spaced em dash / double hyphen / hyphen.
TOUCH_EXEMPT_SEP_RE = re.compile(r"\s+(?:—|--|-)\s+")
# EV19 (shape A): the touch arm runs only over drafts, and the two standing G5
# exemptions are declared here once, not per section.
TOUCH_ARM_STANDING_EXEMPT = ("docs/OPERATIONS.md", "docs/MAP.md")
# EV19 (shape B): the states a section whose probes describe a tree that
# existed is in — the tree has passed through the task's commit, so a numeric
# bound violated by the CURRENT tree is stale (it describes a tree that no
# longer exists). Open (ready/blocked) sections' probes describe the tree the
# task will produce and are never freshness-evaluated.
PROBE_FRESH_STATES = ("landed", "approved", "integrated", "ran", "recorded")
# ER9: the judged rule's cut-in — a plan whose first commit predates this
# date predates the rule itself, so none of its sections ever owe a
# judgement. The record is derived from what exists (D6): the judgement
# files' `plan:` and dates, the section panels' `tasks:`, and git's word on
# when a heading was committed.
JUDGED_FROM = "2026-09-25"
# ER9: the states the `judged` subcommand reports a row for. The brief line
# and the check warning cover only the open subset — a landed or in-flight
# key was judged (or its plan exempted) before it ran, and a
# withdrawn/parked key is never evaluated at all.
JUDGED_LINE_STATES = ("ready", "blocked", "held", "running", "ran")
JUDGED_OPEN_STATES = ("ready", "blocked", "held")
# EV19: only commands whose first word is a pure read are evaluated against the
# tree — the checker never builds, evaluates, shells into itself or reads
# another workspace, so probes that invoke nix, git or python are skipped.
PROBE_SAFE_READS = ("grep", "wc", "sed", "awk", "cat", "jq", "tail", "head")
# ER5: the tools that exist only inside the devShell — a probe command naming
# one of them BARE (outside a `nix develop` segment) cannot run on the
# driver's PATH (brief §3: all tooling lives in the devShell, nothing — not
# even jq or python3 — is on the host PATH), so `bare_tools` reports it and a
# draft that carries it is refused while an open section's is warned.
DEVSHELL_TOOLS = (
    "python3",
    "jq",
    "bats",
    "pytest",
    "ruff",
    "shellcheck",
    "node",
    "treefmt",
    "statix",
    "deadnix",
)
# ER5: the segment operators a probe command is split on for the bare-tool
# rule: every pipe, logical operator and list separator, and the boundaries
# of a `$(…)` substitution (its body is its own segment).
_BARE_SEGMENTS_RE = re.compile(r"\$\(|\)|\|\||&&|[|;]")
CHAIN_RE = re.compile(r"^(?P<root>.*[0-9A-Z])(?P<suffix>[a-z]{1,2})$")
# The technical class a task `touches` implies (plan SD2). The rules live in
# docs/ledger/task-classes.toml: `[[rule]]` blocks, each `class` one of the
# names in `streams.TASK_CLASS_NAMES` and `glob` a plain fnmatch pattern over
# the character set only (no `[`, no `**` semantics — `*` spans `/`). A file's
# class is the first rule whose glob matches it; a task's class is the
# most-common file class (ties -> the earliest rule's class); no touches, or
# none matching, is `any`.
CLASS_NAMES = streams.TASK_CLASS_NAMES
CLASS_GLOB_RE = re.compile(r"^[A-Za-z0-9._/*?-]+$")
STATES = (
    "landed",
    "approved",
    "integrated",
    "rejected",
    "ran",
    "running",
    "recorded",
    "ready",
    "blocked",
    "deferred-to-brief",
    "withdrawn",
    "parked",
    "held",
)
LEGACY_STATES = ("done", "superseded", "parked", "open")
REVIEW_RE = re.compile(
    r"^# Opus gate — seat run (?P<run>\S+), task (?P<key>\S+) — (?P<verdict>APPROVED|REJECTED)"
)
PLAN_DEFECT_ENUM = (
    "none",
    "vacuous",
    "missing-case",
    "underspecified",
    "wrong-fact",
    "implementer",
    "process",
)
PLAN_DEFECT_CAUSED = ("vacuous", "missing-case", "underspecified", "wrong-fact")
PLAN_DEFECT_SHORT = {
    "vacuous": "vac",
    "missing-case": "miss",
    "underspecified": "under",
    "wrong-fact": "fact",
}
# The completed review block's allowlisted keys (D8). `model` is allowed but
# not validated.
REVIEW_BLOCK_KEYS = (
    "plan_defect",
    "plan_defect_secondary",
    "mutants_total",
    "mutants_killed",
    "mutants_outside_named",
    "reviewer",
    "majors",
    "minors",
    "model",
)
REVIEWER_ENUM = ("opus", "sonnet", "deepseek", "fable", "unknown")
# The block's H1 shape, with a catch-all verdict word: the lint (from
# front_matter_from) refuses any word outside APPROVED | REJECTED by name, so
# e.g. REWORK is flagged even though REVIEW_RE (the gate's stricter regex)
# does not parse it.
REVIEW_SHAPE_RE = re.compile(
    r"^# Opus gate — seat run (?P<run>\S+), task (?P<key>\S+) — (?P<verdict>\S+)$"
)
DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")

DEFAULT_RUNS_DIR = os.path.expanduser("~/factory/runs")
DEFAULT_STALE_AFTER = 7200
PLANS_GLOB = "docs/superpowers/plans/*.md"
BEGIN, END = "<!-- tasks:begin -->", "<!-- tasks:end -->"


def run(argv, timeout=20.0):
    """The one subprocess seam (tests pass a fake)."""
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def chain_root(key):
    m = CHAIN_RE.match(key)
    return m.group("root") if m else key


def parse_keys(value):
    value = re.sub(r"\([^)]*\)", " ", value)
    out = []
    for tok in re.split(r"[,\s]+", value.replace("`", "")):
        if tok and tok.lower() != "none" and KEY_RE.match(tok):
            out.append(tok)
    return out


def parse_list(value):
    return [t for t in re.split(r"[,\s]+", value.replace("`", "").strip()) if t]


def _parse_probe_bullet(line):
    """Parse one `- name: `command` :: op[ value] :: provenance` bullet into a
    probe dict; returns ``(probe, None)`` on success or ``(None, error)`` where
    ``error`` is the ``probes: `-prefixed one-line check error. The command is
    extracted between the first and last backtick *before* the tail is split on
    ``::``, so a ``::`` inside the command stays whole."""
    body = line.removeprefix("- ")
    m = re.match(r"^([a-z][a-z0-9-]{0,31}):(.*)$", body)
    if m is None:
        return None, f"probes: malformed: {line}"
    name, rest = m[1], m[2]
    first, last = rest.find("`"), rest.rfind("`")
    if first < 0 or last <= first:
        return None, f"probes: malformed: {line}"
    cmd = rest[first + 1 : last]
    if "\t" in cmd:
        return None, f"probes: malformed: {line}"
    tail = rest[last + 1 :]
    segs = tail.split("::")
    if len(segs) < 3 or not segs[1].strip():
        return None, f"probes: malformed: {line}"
    opval = segs[1].strip()
    provenance = "::".join(segs[2:]).strip()
    if not provenance:
        return None, f"probes: malformed: {line}"
    tokens = opval.split()
    op = tokens[0]
    if op not in PROBE_OPS:
        return None, f"probes: malformed: {line}"
    if op in PROBE_NONE_OPS:
        if len(tokens) > 1:
            return None, f"probes: {name}: op {op} takes no value"
        value = None
    elif op in PROBE_NUM_OPS:
        if len(tokens) != 2 or PROBE_DECIMAL_RE.fullmatch(tokens[1]) is None:
            return None, f"probes: {name}: op {op} needs a numeric value"
        value = tokens[1]
    else:  # eq / ne: a non-space string that is not a number
        if len(tokens) != 2:
            return None, f"probes: malformed: {line}"
        if PROBE_DECIMAL_RE.fullmatch(tokens[1]) is not None:
            return None, f"probes: {name}: eq/ne on a number — state a bound (le, ge)"
        value = tokens[1]
    return {"name": name, "cmd": cmd, "op": op, "value": value, "by": provenance}, None


def _parse_record_bullet(line):
    """Parse one `- label: `command`` bullet into a ``{label, cmd}`` dict;
    returns ``(record, None)`` on success or ``(None, error)`` where ``error``
    is the ``record: malformed: <line>`` one-line check error. The command is
    the text between the first and last backtick; the label is lowercase-minus-32."""
    body = line.removeprefix("- ")
    m = re.match(r"^([a-z][a-z0-9-]{0,31}):(.*)$", body)
    if m is None:
        return None, f"record: malformed: {line}"
    label, rest = m[1], m[2]
    first, last = rest.find("`"), rest.rfind("`")
    if first < 0 or last <= first:
        return None, f"record: malformed: {line}"
    cmd = rest[first + 1 : last]
    return {"label": label, "cmd": cmd}, None


def _steps_land_spans(line, fenced):
    """Yield every command span in a ``**Steps.**`` line: for a fenced line, the
    whole line (a fenced block is already code); for a plain line, each
    backtick-delimited substring in turn (the first/last-backtick pairing
    ``_parse_probe_bullet`` already uses, applied to every pair rather than only
    the first and last)."""
    if fenced:
        yield line
        return
    parts = line.split("`")
    for i in range(1, len(parts), 2):
        yield parts[i]


def _bounds_empty(probes):
    """True when the numeric bounds of one command's probes cannot hold
    together (EV19, shape B: KN18's ``gt 9`` with ``le 9``). Interval
    arithmetic over the group: ``gt``/``ge`` raise the floor, ``lt``/``le``
    lower the ceiling; the interval is empty when the floor passes the
    ceiling, or equals it under an exclusive end."""
    lo, lo_open, hi, hi_open = -math.inf, False, math.inf, False
    for p in probes:
        v = float(p["value"])
        if p["op"] in ("gt", "ge"):
            if v > lo:
                lo, lo_open = v, p["op"] == "gt"
            elif v == lo and p["op"] == "ge":
                lo_open = False
        else:
            if v < hi:
                hi, hi_open = v, p["op"] == "lt"
            elif v == hi and p["op"] == "le":
                hi_open = False
    return lo > hi or (lo == hi and (lo_open or hi_open))


def _bound_holds(probe, measured):
    v = float(probe["value"])
    return {
        "gt": measured > v,
        "ge": measured >= v,
        "lt": measured < v,
        "le": measured <= v,
    }[probe["op"]]


def run_probe(cmd, cwd, timeout=10.0):
    """Run one probe command as a READ of the tree and return its last output
    line as a number, or None (EV19). Only commands whose first word is a pure
    read (``PROBE_SAFE_READS``) run, so the checker never builds, evaluates or
    recurses into itself; stdin is closed (a command that reads the terminal
    can never hang it); any failure, timeout or non-numeric output is None."""
    stripped = (cmd or "").strip()
    if not stripped:
        return None
    if stripped.split(None, 1)[0] not in PROBE_SAFE_READS:
        return None
    try:
        r = subprocess.run(
            ["bash", "-c", stripped],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            check=False,
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        return float(lines[-1].strip())
    except ValueError:
        return None


def bare_tools(command):
    """Every devShell tool `command` names BARE (ER5, spec §4 rec 2's
    backstop): the offending tokens in order, duplicates kept, [] when clean.
    The command is split into segments on the shell operators (|, ||, &&, ;) and
    on ``$(``…``)`` substitution boundaries; a segment whose first two tokens
    are ``nix develop`` (any options, ``-c`` or ``--command``) is exempt whole;
    a segment whose tokens carry ``sh``/``bash`` followed by ``-c`` and a
    string recurses into that string as a command; every other segment reports
    every token equal to a DEVSHELL_TOOLS name — any position, an argument
    included, so a probe that greps for the word writes ``pytho[n]3`` to stay
    clean (the accepted false positive). An unbalanced quote (shlex refuses a
    segment) falls back to the whole command as one ``command.split()``
    segment."""
    if not command:
        return []
    try:
        tokens_by_segment = [
            shlex.split(seg) for seg in _BARE_SEGMENTS_RE.split(command)
        ]
    except ValueError:
        tokens_by_segment = [command.split()]
    found = []
    for tokens in tokens_by_segment:
        if len(tokens) >= 2 and tokens[0] == "nix" and tokens[1] == "develop":
            continue  # run under the devShell: the one exemption
        inner = None
        for i in range(len(tokens) - 2):
            if tokens[i] in ("sh", "bash") and tokens[i + 1] == "-c":
                inner = tokens[i + 2]
                break
        if inner is not None:
            found.extend(bare_tools(inner))
            continue
        found.extend(tok for tok in tokens if tok in DEVSHELL_TOOLS)
    return found


def _py_top_level_names(path):
    """The top-level def/class/assignment names of a Python file — a lower
    bound on the symbols it defines; [] when the file cannot be read."""
    try:
        text = pathlib.Path(path).read_text(errors="replace")
    except OSError:
        return []
    names = [
        m.group(1)
        for m in re.finditer(
            r"^(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.MULTILINE
        )
    ]
    names += [
        m.group(1)
        for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", text, re.MULTILINE)
    ]
    return names


def _word_in(text, word):
    return (
        re.search(rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])", text)
        is not None
    )


def _is_test_path(path):
    """A path under a test directory: some component before the file name is
    `tests` (tests/…, media/tests/…)."""
    parts = pathlib.PurePosixPath(path).parts
    return "tests" in parts[:-1]


def _dir_has_own_git_entry(path):
    """The directory holds its own `.git` entry — a `git worktree add`
    checkout's `.git` is a file, a nested clone's is a directory; either way
    the directory is a tree of its own, not this repo's."""
    return os.path.exists(os.path.join(path, ".git"))


def _repo_test_files(repo_path):
    """Every file under a `tests` directory of the repo as (relative path,
    text) — the touch arm's search space. Pruned: `.git` and `__pycache__`
    by name, and any directory holding its own `.git` entry (a worktree or
    a nested checkout, at any depth); an unreadable file is skipped, never
    fatal."""
    out = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in ("__pycache__", ".git")
            and not _dir_has_own_git_entry(os.path.join(dirpath, d))
        ]
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), repo_path)
            if not _is_test_path(rel):
                continue
            try:
                text = pathlib.Path(dirpath, fn).read_text(errors="replace")
            except OSError:
                continue
            out.append((rel, text))
    return out


def _reference_kind(touch, text, repo_path, stop_names=frozenset()):
    """How a test file's text references a touched path: 'path' (the path
    string), 'module <stem>' (a .py touch's module named as a word) or
    'symbol <name>' (a top-level name of the touch named as a word); None when
    the file does not reference the touch at all (EV19). A lower bound on the
    real reads-the-file relation — it needs no semantic model — and a
    directory of the touched path never matches. A name in `stop_names` is
    skipped before the bare-word check: common names fire on files that never
    read the module (EV23)."""
    if not touch:
        return None
    if touch in text:
        return "path"
    if touch.endswith(".py"):
        stem = pathlib.Path(touch).stem
        if stem and _word_in(text, stem):
            return f"module {stem}"
        for name in _py_top_level_names(os.path.join(repo_path, touch)):
            if name in stop_names:
                continue
            if _word_in(text, name):
                return f"symbol {name}"
    return None


# EV23: a top-level name that is a bare word in at least this fraction of the
# repo's own test-file corpus is not distinctive — it fires on files that
# never read the module. Below MIN_CORPUS_FOR_FLOOR test files the floor is
# off: every name counts, as before, no division, no crash.
NON_DISTINCTIVE_FLOOR = 0.10
MIN_CORPUS_FOR_FLOOR = 20


def _non_distinctive_symbol_names(touch, repo_path, test_files):
    """The touched .py file's top-level names that are bare words in >=
    NON_DISTINCTIVE_FLOOR of `test_files` (`_repo_test_files`'s filesystem
    walk) — the measured-frequency floor of the symbol match (EV23)."""
    if len(test_files) < MIN_CORPUS_FOR_FLOOR:
        return set()
    names = _py_top_level_names(os.path.join(repo_path, touch))
    return {
        name
        for name in names
        if sum(1 for _, text in test_files if _word_in(text, name)) / len(test_files)
        >= NON_DISTINCTIVE_FLOOR
    }


def _parse_touches_exempt(task):
    """A section's `**touches-exempt:** <path> — <reason>` lines: the set of
    exempted paths plus one refusal per line whose reason is missing (EV19)."""
    exempt, errors = set(), []
    for line in task.get("touches_exempt", []):
        m = TOUCH_EXEMPT_SEP_RE.search(line)
        path = line[: m.start()].strip(" `") if m is not None else ""
        reason = line[m.end() :].strip() if m is not None else ""
        if not path or not reason:
            errors.append(
                f"tasks: {task['key']} touches-exempt {line.strip()}: missing reason"
            )
            continue
        exempt.add(path)
    return exempt, errors


def parse_plan(path):
    path = pathlib.Path(path)
    tasks, cur = [], None
    in_fence = False
    in_probes = False
    in_record = False
    in_steps = False
    seen_probe_names = set()
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            if in_steps:
                cur["steps_lines"].append((line, True))
            continue
        if line.startswith("## ") or (
            line.startswith("### ") and not HEADING_RE.match(line)
        ):
            cur = None  # a section that is not a typed task ends the current one
            in_probes = False
            in_record = False
            in_steps = False
            seen_probe_names = set()
            continue
        m = HEADING_RE.match(line)
        if m:
            cur = {
                "key": m["key"],
                "kind": m["kind"],
                "size": m["size"],
                "title": m["title"].strip(),
                "depends_on": [],
                "touches": [],
                "touches_exempt": [],
                "acceptance": [],
                "areas": [],
                "repo": None,
                "commit_subject": None,
                "probes": [],
                "probe_env": None,
                "probe_errors": [],
                "probes_header": False,
                "record": [],
                "record_errors": [],
                "record_header": False,
                "class": "any",
                "body": "",
                "steps_lines": [],
                "line": n,
                "plan": path.name,
            }
            in_probes = False
            in_record = False
            in_steps = False
            seen_probe_names = set()
            tasks.append(cur)
            continue
        if cur is None:
            continue
        if in_steps:
            stripped = line.strip()
            if stripped.startswith("**Tests") or stripped == "**probes:**":
                in_steps = False
            else:
                cur["steps_lines"].append((line, False))
        if in_probes:
            if line.startswith("- "):
                cur["body"] += line + "\n"
                probe, err = _parse_probe_bullet(line)
                if err is not None:
                    cur["probe_errors"].append(err)
                elif probe["name"] in seen_probe_names:
                    cur["probe_errors"].append(f"probes: duplicate {probe['name']}")
                else:
                    seen_probe_names.add(probe["name"])
                    cur["probes"].append(probe)
                continue
            if line.strip() == "":
                # FA36: a blank line inside the block never ends it — the
                # block still ends at the first line that is neither blank
                # nor `- `-prefixed.
                cur["body"] += line + "\n"
                continue
            in_probes = False
        if in_record:
            if line.startswith("- "):
                cur["body"] += line + "\n"
                record, err = _parse_record_bullet(line)
                if err is not None:
                    cur["record_errors"].append(err)
                else:
                    cur["record"].append(record)
                continue
            if line.strip() == "":
                # FA36: the `**record:**` twin of the probes blank-line skip.
                cur["body"] += line + "\n"
                continue
            in_record = False
        f = FIELD_RE.match(line)
        if f:
            name, value = f["name"], f["value"].strip()
            if name == "dependsOn":
                cur["depends_on"] = parse_keys(value)
            elif name == "touches-exempt":
                # EV19: the raw line — the arm splits path from reason itself
                # so a reasonless exemption stays visible as one.
                cur["touches_exempt"].append(value)
            elif name == "touches":
                cur["touches"] = parse_list(value)
            elif name == "acceptance":
                cur["acceptance"] = parse_list(value)
            elif name == "areas":
                cur["areas"] = parse_list(value)
            elif name == "repo":
                cur["repo"] = value.strip("`").strip() or None
            elif name == "probe_env":
                cur["probe_env"] = value
                if value:
                    for tok in value.split():
                        if PROBE_ENV_TOKEN_RE.fullmatch(tok) is None:
                            cur["probe_errors"].append(
                                f"probe_env: malformed token {tok}"
                            )
            else:
                cur["commit_subject"] = value.strip("`").strip()
            continue
        if line.strip() == "**probes:**":
            cur["body"] += line + "\n"
            in_probes = True
            cur["probes_header"] = True
            continue
        if line.strip() == "**record:**":
            cur["body"] += line + "\n"
            in_record = True
            cur["record_header"] = True
            continue
        if line.strip() == "**Steps.**":
            cur["body"] += line + "\n"
            in_steps = True
            continue
        cur["body"] += line + "\n"
    # EV3: a fix-round section (a key with a chain suffix) that carries no
    # `repo:` of its own inherits its chain root's `repo`; a section with its
    # own keeps it, and a root without one stays None (this repo).
    root_repo = {}
    for t in tasks:
        if chain_root(t["key"]) == t["key"]:
            root_repo[t["key"]] = t["repo"]
    for t in tasks:
        root = chain_root(t["key"])
        if root != t["key"] and t["repo"] is None:
            t["repo"] = root_repo.get(root)
    return {"file": path.name, "path": str(path), "typed": bool(tasks), "tasks": tasks}


def cmd_touches(plan_path, key):
    """The `touches <plan> <KEY>` subcommand: the union of every section whose
    `chain_root` matches KEY's, first-seen order, deduplicated, trailing slash
    stripped, one per line. Reads the plan file only — no `--root`, repos.toml
    or store — so it runs on any file from any cwd. Exit 0 (empty union is "no
    contract"), 3 for no section, 2 for an unreadable plan."""
    try:
        parsed = parse_plan(plan_path)
    except OSError:
        print(f"tasks: touches: cannot read {plan_path}", file=sys.stderr)
        return 2
    by_key = {t["key"]: t for t in parsed["tasks"]}
    if key not in by_key:
        print(f"tasks: touches: no section {key} in {plan_path}", file=sys.stderr)
        return 3
    root = chain_root(key)
    seen = []
    out = []
    for t in parsed["tasks"]:
        if chain_root(t["key"]) != root:
            continue
        for entry in t["touches"]:
            entry = entry.rstrip("/")
            if entry not in seen:
                seen.append(entry)
                out.append(entry)
    for entry in out:
        print(entry)
    return 0


def cmd_probes(plan_path, key):
    """The `probes <plan> <KEY>` subcommand: line 1 `env\\t<probe_env or empty>`,
    then one tab-separated line per probe `<name>\\t<op>\\t<value>\\t<by>\\t<cmd>`
    (the command last). Exit 0 with only the env line when the section names no
    probe, 3 for no section, 2 for an unreadable plan. Reads the plan file only."""
    try:
        parsed = parse_plan(plan_path)
    except OSError:
        print(f"tasks: probes: cannot read {plan_path}", file=sys.stderr)
        return 2
    by_key = {t["key"]: t for t in parsed["tasks"]}
    if key not in by_key:
        print(f"tasks: probes: no section {key} in {plan_path}", file=sys.stderr)
        return 3
    task = by_key[key]
    print("env\t" + (task["probe_env"] or ""))
    for p in task["probes"]:
        print(f"{p['name']}\t{p['op']}\t{p['value'] or ''}\t{p['by']}\t{p['cmd']}")
    return 0


def cmd_area(root, plan_path, key):
    """The `area <plan> <KEY>` subcommand (OC8): the majority area of KEY's
    task — ``area_of(task, manifest)[0]`` — against the manifest under
    ``<root>/docs/ledger/subsystems.toml``. Exit 0 with the area; prints
    ``unknown``, exits 1 and writes one ``tasks: area: <reason>`` stderr line
    when the plan is unreadable, the key has no section, the manifest is
    unreadable or malformed, or no touched file matches a manifest row. Reads
    the plan by path (like `touches`), so it runs before any repos.toml/store
    resolution and from any cwd."""
    try:
        parsed = parse_plan(plan_path)
    except OSError:
        print(f"tasks: area: cannot read {plan_path}", file=sys.stderr)
        print("unknown")
        return 1
    by_key = {t["key"]: t for t in parsed["tasks"]}
    if key not in by_key:
        print(f"tasks: area: no section {key} in {plan_path}", file=sys.stderr)
        print("unknown")
        return 1
    rows, errors = load_manifest(
        os.path.join(root, "docs", "ledger", "subsystems.toml")
    )
    if errors:
        print(f"tasks: area: subsystems.toml: {errors[0]}", file=sys.stderr)
        print("unknown")
        return 1
    area, _tie = area_of(by_key[key], rows)
    if area is None:
        print(
            f"tasks: area: no touched file of {key} matches a manifest row",
            file=sys.stderr,
        )
        print("unknown")
        return 1
    print(area)
    return 0


def cmd_record(graph, key):
    """The `record --key <KEY>` subcommand: one `label\\tcmd` line per record
    bullet of the task named KEY, in order, across the scanned repos. A section
    without `**record:**` prints nothing and exits 0; an unknown key exits 3."""
    for repo in graph["repos"]:
        for t in repo["tasks"]:
            if t["key"] == key:
                for r in t.get("record", []):
                    print(f"{r['label']}\t{r['cmd']}")
                return 0
    print(f"tasks: record: no section {key}", file=sys.stderr)
    return 3


def load_class_rules(path):
    """Read a docs/ledger/task-classes.toml file into ``(rules, errors)``.
    ``rules`` is the list of ``(class, glob)`` pairs from the well-formed
    ``[[rule]]`` entries, in file order (priority); ``errors`` is the list of
    ``rule N: …`` messages for malformed entries, WITHOUT the
    ``tasks: task-classes:`` prefix (the caller adds it). A missing file is
    ``([], [])``."""
    path = pathlib.Path(path)
    if not path.is_file():
        return [], []
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [], [f"{path}: unreadable: {exc}"]
    entries = data.get("rule", [])
    if isinstance(entries, dict) or not isinstance(entries, list):
        # a `[rule]` table (not `[[rule]]`), or `rule` holding a scalar
        return [], ["not a [[rule]] table"]
    rules, errors = [], []
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            errors.append(f"rule {i}: not a [[rule]] table")
            continue
        klass = entry.get("class")
        glb = entry.get("glob")
        ok = True
        if klass is None:
            errors.append(f"rule {i}: missing class")
            ok = False
        elif klass not in CLASS_NAMES:
            errors.append(f"rule {i}: unknown class {klass}")
            ok = False
        if glb is None:
            errors.append(f"rule {i}: missing glob")
            ok = False
        elif CLASS_GLOB_RE.fullmatch(glb) is None:
            errors.append(f"rule {i}: glob {glb} is not a plain pattern")
            ok = False
        if ok:
            rules.append((klass, glb))
    return rules, errors


def file_class(path, rules):
    """The class of the FIRST rule whose glob matches `path`, or None."""
    for klass, glb in rules:
        if fnmatch.fnmatch(path, glb):
            return klass
    return None


def task_class(touches, rules):
    """The class of a task's `touches`: the class with the most files, a tie
    broken by the class whose rule comes first; no touches (or none matching
    any rule) is ``any``."""
    counts = {}
    for t in touches:
        klass = file_class(t, rules)
        if klass is not None:
            counts[klass] = counts.get(klass, 0) + 1
    if not counts:
        return "any"
    order = {}
    for i, (klass, _) in enumerate(rules):
        order.setdefault(klass, i)
    best = next(iter(counts))
    for klass, n in counts.items():
        if n > counts[best] or (n == counts[best] and order[klass] < order[best]):
            best = klass
    return best


def load_manifest(path):
    """Read a docs/ledger/subsystems.toml manifest into ``(rows, errors)``.

    ``rows`` is the list of ``[[subsystem]]`` dicts — ``name``, ``prefix``,
    ``area``, ``owns`` (glob list) and ``plans`` (glob list) — in file order
    (priority); ``errors`` is the list of ``subsystem N: …`` messages for
    malformed entries, WITHOUT the ``tasks:`` prefix (the caller adds it). A
    missing file is ``([], [])``."""
    path = pathlib.Path(path)
    if not path.is_file():
        return [], []
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [], [f"{path}: unreadable: {exc}"]
    entries = data.get("subsystem", [])
    if isinstance(entries, dict) or not isinstance(entries, list):
        return [], ["not a [[subsystem]] table"]
    rows, errors = [], []
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            errors.append(f"subsystem {i}: not a [[subsystem]] table")
            continue
        row = {
            "name": entry.get("name"),
            "prefix": entry.get("prefix"),
            "area": entry.get("area"),
            "owns": entry.get("owns", []),
            "plans": entry.get("plans", []),
        }
        if row["name"] is None:
            errors.append(f"subsystem {i}: missing name")
        if row["prefix"] is None:
            errors.append(f"subsystem {i}: missing prefix")
        if row["area"] is None:
            errors.append(f"subsystem {i}: missing area")
        if (
            row["name"] is not None
            and row["prefix"] is not None
            and row["area"] is not None
        ):
            rows.append(row)
    return rows, errors


def file_area(path, manifest):
    """The `area` of the FIRST manifest row whose `owns` glob matches `path`,
    or None when no row matches."""
    for row in manifest:
        for glb in row["owns"]:
            if fnmatch.fnmatch(path, glb):
                return row["area"]
    return None


def area_of(task, manifest):
    """``(area, tie)`` for a task: the `area` with the most touched files, a
    tie broken by the row that appears earliest in the manifest; ``tie`` is
    True when the majority was shared by more than one area. ``(None, False)``
    when no touched file matches any row."""
    touches = task.get("touches", [])
    counts = {}
    for t in touches:
        area = file_area(t, manifest)
        if area is not None:
            counts[area] = counts.get(area, 0) + 1
    if not counts:
        return None, False
    order = {row["area"]: i for i, row in enumerate(manifest)}
    best = max(counts, key=lambda a: (counts[a], -order.get(a, 1 << 30)))
    top = counts[best]
    tie = sum(1 for n in counts.values() if n == top) > 1
    return best, tie


def spanned_areas(task, manifest):
    """The distinct areas a task's touches reach, in first-seen (touch) order."""
    areas = []
    for t in task.get("touches", []):
        area = file_area(t, manifest)
        if area is not None and area not in areas:
            areas.append(area)
    return areas


PREFIX_RE = re.compile(r"^[A-Za-z]+")


def reserved_prefix(key):
    """A key's leading letters up to the first digit or hyphen (`EV1` → `EV`,
    `SPEC-PL` → `SPEC`, `EVX1` → `EVX`); the empty string when the key starts
    with a non-letter."""
    m = PREFIX_RE.match(key)
    return m.group(0) if m else ""


def load_grandfathered(path):
    """The set of keys `docs/ledger/areas-grandfather.toml` lists, or an empty
    set when the file is absent, unreadable or unparseable."""
    path = pathlib.Path(path)
    if not path.is_file():
        return set()
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return set()
    keys = data.get("keys", [])
    if not isinstance(keys, list):
        return set()
    return {k for k in keys if isinstance(k, str)}


def load_repos(path):
    if not pathlib.Path(path).exists():
        return []
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    repos = [
        {
            "name": r["name"],
            "path": os.path.expanduser(r["path"]),
            "plans": r.get("plans", PLANS_GLOB),
            "ledger": bool(r.get("ledger", False)),
        }
        for r in data.get("repo", [])
    ]
    flagged = [r["name"] for r in repos if r["ledger"]]
    if len(flagged) > 1:
        print(
            f"tasks: {path} names more than one `ledger = true` repo: "
            + " and ".join(sorted(flagged)),
            file=sys.stderr,
        )
        raise SystemExit(1)
    return repos


def bind_root(repos, root):
    """Rebind the single `ledger = true` repo's `path` to `root` so `scan_repo`
    and `check` read that repo's plans, manifest and grandfather list from the
    tree under `--root` rather than the live clone `repos.toml` names; sibling
    repos keep their expanded path. A fresh list is returned, the caller's left
    untouched."""
    bound = []
    for r in repos:
        r = dict(r)
        if r["ledger"]:
            r["path"] = os.path.abspath(root)
        bound.append(r)
    return bound


def ledger_entries(repos_path):
    """Every repo flagged `ledger = true` in `repos_path`, in file order. The
    absence of the file is [] (not an error); `load_repos` refuses more than one
    flagged entry, so this returns at most one name."""
    return [r["name"] for r in load_repos(repos_path) if r["ledger"]]


def load_plan_status(path):
    if not pathlib.Path(path).exists():
        return {}
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return {
        (p["repo"], p["file"]): {"status": p["status"], "note": p.get("note", "")}
        for p in data.get("plan", [])
    }


def _iso_date(value):
    """A task-status row's date field as an ISO string: a bare TOML date
    (`since = 2026-09-16`) reaches here as a `datetime.date`, which `json`
    cannot serialize (the DF9 lesson), so every date-ish value is normalised
    with `isoformat()`; anything else passes through, absent as `""`."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value or ""


def load_task_status(path):
    if not pathlib.Path(path).exists():
        return {}
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return {
        (p["repo"], p["plan"], p["key"]): {
            "status": p["status"],
            "note": p.get("note", ""),
            "decided": p.get("decided", ""),
            "since": _iso_date(p.get("since", "")),
            "released": _iso_date(p.get("released", "")),
        }
        for p in data.get("task", [])
    }


def landed_subjects(repo_path, run=None):
    runner = run or globals()["run"]
    try:
        r = runner(["git", "-C", repo_path, "log", "--format=%s"], timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    if r.returncode != 0:
        return set()
    return {line for line in r.stdout.splitlines() if line.strip()}


def _git_available(repo_path, run=None):
    """True when git can read `repo_path` (one commit's subject), False when it
    cannot — a missing binary, a non-repository, or any subprocess failure. The
    probe rides the same `run`/`globals()["run"]` seam `landed_subjects` uses,
    so a monkeypatched `run` (every DF16 test) and the real git-less lint
    sandbox resolve identically."""
    runner = run or globals()["run"]
    try:
        r = runner(["git", "-C", repo_path, "log", "--format=%s", "-1"], timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def _board_queued_keys(repo_path):
    """The keys the last committed `docs/OPERATIONS.md` board block still lists
    as open (its `**Queued` line), read into a set via `parse_keys`. `None` when
    the file is unreadable or the `BEGIN`/`END` markers are absent or out of
    order — the caller then treats every key as in scope, so a missing board is
    never a silent exemption. The label's fallback body "nothing queued" (which
    `parse_keys` would otherwise read as two keys) is special-cased to `set()`."""
    path = pathlib.Path(repo_path) / "docs" / "OPERATIONS.md"
    try:
        text = path.read_text()
    except OSError:
        return None
    ib = text.find(BEGIN)
    ie = text.find(END)
    if ib < 0 or ie < 0 or ie < ib:
        return None
    for line in text[ib:ie].splitlines():
        if line.startswith("**Queued "):
            body = re.sub(r"^\*\*Queued\b.*?\*\*\s*", "", line, count=1)
            if body == "nothing queued":
                return set()
            return set(parse_keys(body))
    return None


def _base_root():
    """The base clone root: `FACTORY_BASE` when set, else `~/factory/base`."""
    return os.environ.get("FACTORY_BASE") or os.path.join(
        os.path.expanduser("~"), "factory", "base"
    )


def integrated_subjects(repo_name, landed, run=None):
    """Commit subjects reachable from an `integ/*` branch of the base clone for
    `repo_name`, minus `landed` (an already-landed subject never counts).
    Returns None when the base clone is absent: the probe is missing, so
    `integrated` is never derived and the gap is surfaced via `integ_probe`."""
    runner = run or globals()["run"]
    base = os.path.join(_base_root(), repo_name)
    if not os.path.isdir(base):
        return None
    try:
        r = runner(
            ["git", "-C", base, "log", "--format=%s", "--branches=integ/*"],
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if r.returncode != 0:
        return set()
    subjects = {line for line in r.stdout.splitlines() if line.strip()}
    return subjects - landed


def _split_front_matter(lines):
    """Split a review file's lines into (has_block, block, first, lookahead).
    A block is a leading `---` line closed by a later `---`; `block` maps its
    keys to values, `first` is the line immediately after the block ("" if
    none) and `lookahead` the next two lines (the H1 may follow within three
    lines of the block). A file without a block reads `first = lines[0]` and
    `lookahead = ()` — its H1 is `first`."""
    if not lines:
        return False, {}, "", ()
    if lines[0].strip() != "---":
        return False, {}, lines[0], ()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            block = {}
            for ln in lines[1:i]:
                if ":" in ln:
                    key, _, value = ln.partition(":")
                    block[key.strip()] = value.strip()
            first = lines[i + 1] if i + 1 < len(lines) else ""
            lookahead = tuple(lines[i + 2 : i + 4])
            return True, block, first, lookahead
    return False, {}, lines[0], ()


def _block_keys(lines):
    """The ordered `key:` names of a review file's front-matter block, with
    duplicates preserved. `_split_front_matter` collapses repeats last-wins, so
    the gate lint needs this separate view to see a repeated key. Empty when
    the file has no block."""
    if not lines or lines[0].strip() != "---":
        return []
    keys = []
    for ln in lines[1:]:
        if ln.strip() == "---":
            return keys
        if ":" in ln:
            keys.append(ln.partition(":")[0].strip())
    return keys


def _read_review(path):
    """Read a review file into the 4-tuple (has_block, block, first, lookahead):
    `has_block` is a bool, `block` a dict of the front-matter key/value lines,
    `first` the line immediately after the block (or the file's first line when
    it has no block), and `lookahead` the two lines after `first` (the H1 may
    fall within three lines of the block). An unreadable file reads as no-block:
    (False, {}, "", ())."""
    try:
        lines = pathlib.Path(path).read_text().splitlines()
    except OSError:
        return False, {}, "", ()
    return _split_front_matter(lines)


def _review_h1(first, lookahead):
    """The `# Opus gate …` H1 match over `first` then the two lookahead lines
    (a block's H1 may fall within three lines), or None."""
    m = REVIEW_RE.match(first)
    if m is not None:
        return m
    for ln in lookahead:
        m = REVIEW_RE.match(ln)
        if m is not None:
            return m
    return None


def _review_date(name):
    """The YYYY-MM-DD prefix of a review basename as a datetime.date, or None
    when the basename has no valid date prefix."""
    m = DATE_PREFIX_RE.match(name)
    if m is None:
        return None
    try:
        return datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def read_reviews(repo_path):
    out = {}
    d = pathlib.Path(repo_path) / "docs" / "reviews"
    if not d.is_dir():
        return out
    for path in sorted(d.glob("*opus-review*.md")):
        _, _, first, lookahead = _read_review(path)
        m = _review_h1(first, lookahead)
        if m:
            out[m["key"]] = {
                "verdict": m["verdict"],
                "run": m["run"],
                "file": path.name,
            }
    return out


def _field(text, pattern):
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _repo_from_workspace(workspace):
    """The repo name a workspace clone's origin points at (…/base/<name>), or
    None when the workspace is gone or its origin does not match that shape."""
    cfg = pathlib.Path(workspace) / ".git" / "config"
    try:
        ctext = cfg.read_text()
    except OSError:
        return None
    um = re.search(r"url\s*=\s*(.+)", ctext)
    if not um:
        return None
    m = re.search(r"/base/([^/\s]+)$", um.group(1).strip())
    return m.group(1) if m else None


def read_results(runs_dir, stale_after=DEFAULT_STALE_AFTER):
    """ONE entry per (repo, key): a `.log` counts as `running` only when a newer
    run holds no `.result` for that key AND the log's own mtime is younger than
    `stale_after` seconds. A stale (dead) log is ignored, so the key falls
    through to rules 3-5 — the newest `.result` still wins, even from an older
    run dir (rule 3 stays reachable). A `.log` beside a `.result` in the same
    run is the result (the seat finished)."""
    out = {}
    runs_root = str(runs_dir)
    now = time.time()
    # (repo, key) -> (run_dir_mtime, payload): the newest result and the newest
    # log, tracked separately so a stale newer log never discards an older one's
    # genuine result.
    newest_result = {}
    newest_log = {}

    def keep(target, key, run_mtime, payload):
        if key not in target or run_mtime > target[key][0]:
            target[key] = (run_mtime, payload)

    for p in glob.glob(os.path.join(runs_root, "*", "*.result")):
        try:
            text = pathlib.Path(p).read_text()
        except OSError:
            continue
        status = _field(text, r"FACTORY-RESULT status=(\S+)")
        run_name = _field(text, r"^run:\s*(.+)$")
        key = _field(text, r"^key:\s*(.+)$")
        workspace = _field(text, r"^workspace:\s*(.+)$")
        if not (status and key and workspace):
            continue
        repo = _repo_from_workspace(workspace)
        if not repo:
            continue
        run_mtime = os.path.getmtime(os.path.dirname(p))
        keep(
            newest_result,
            (repo, key),
            run_mtime,
            {"status": status, "run": run_name, "file": p},
        )

    for p in glob.glob(os.path.join(runs_root, "*", "*.log")):
        run_dir = os.path.dirname(p)
        key = os.path.basename(p)[: -len(".log")]
        run_name = os.path.basename(run_dir)
        # the seat logs under <ws>/<run>/<key>; its workspace clone's origin
        # attributes the repo, exactly as for results. A missing workspace makes
        # the log non-evidence.
        workspace = os.path.join(os.path.dirname(runs_root), "ws", run_name, key)
        repo = _repo_from_workspace(workspace)
        if not repo:
            continue
        run_mtime = os.path.getmtime(run_dir)
        payload = {"run": run_name, "log_mtime": os.path.getmtime(p)}
        keep(newest_log, (repo, key), run_mtime, payload)

    for key in set(newest_result) | set(newest_log):
        result = newest_result.get(key)
        log = newest_log.get(key)
        log_fresh = log is not None and now - log[1]["log_mtime"] < stale_after
        log_newer = log is not None and (result is None or log[0] > result[0])
        if log is not None and log_newer and log_fresh:
            out[key] = {"status": "running", "run": log[1]["run"]}
        elif result is not None:
            out[key] = result[1]
        elif log_fresh:
            out[key] = {"status": "running", "run": log[1]["run"]}
        # else: stale log, no result — no entry; the key falls to rules 3-5.
    return out


def read_run_meta(runs_dir, now=None):
    """Map task key -> {"run": name, "age_days": float} for every key named in
    a `run.meta` whose `then:` line names integrate. Keys come from the file's
    `group:` lines (each a `%q`-quoted list of keys); the age is the run
    directory's newest file mtime (the directory that holds the `run.meta`).
    Returns {} when runs_dir is None or holds no such run.meta. This is the
    first run.meta read in tasks.py (EV3)."""
    if runs_dir is None:
        return {}
    now = now if now is not None else time.time()
    out = {}
    for p in glob.glob(os.path.join(str(runs_dir), "*", "run.meta")):
        try:
            text = pathlib.Path(p).read_text()
        except OSError:
            continue
        then_line = _field(text, r"^then:\s*(.+)$")
        if not then_line or "integrate" not in then_line:
            continue
        run_name = _field(text, r"^run:\s*(.+)$") or os.path.basename(
            os.path.dirname(p)
        )
        keys = set()
        for line in text.splitlines():
            if line.startswith("group:"):
                keys.update(re.findall(r"[A-Za-z][A-Za-z0-9-]*", line[len("group:") :]))
        if not keys:
            continue
        run_dir = os.path.dirname(p)
        newest = 0.0
        for f in glob.glob(os.path.join(run_dir, "*")):
            try:
                newest = max(newest, os.path.getmtime(f))
            except OSError:
                continue
        if newest <= 0.0:
            continue
        age_days = (now - newest) / 86400.0
        for k in keys:
            out[k] = {"run": run_name, "age_days": age_days}
    return out


# The `.result` metadata fields `read_result_fields` copies verbatim (SD9). The
# one driver record a `.result` carries that this list omits — `plan`,
# `branch`, `error_class` — is not a ladder grouping or per-attempt figure, so
# it is deliberately left out: nothing here is inferred from a value the seat
# did not write.
RESULT_FIELD_KEYS = (
    "run",
    "key",
    "model",
    "effort",
    "route",
    "class",
    "area",
    "kind",
    "size",
    "rung",
    "prior",
    "fallback",
    "seat",
    "workspace",
    "head",
    "base",
    "wall_s",
    "exit_code",
    "usage",
)

COMMIT_NONE_MARKERS = ("(none)", "(no commits)")


def _commit_count(text):
    """The number of non-empty commit lines under the `commits (base..task/<KEY>):`
    header. `(none)`, `(no commits)` and a `(base commit unknown …)` line are not
    commits; a missing header reads zero."""
    n = 0
    in_section = False
    for line in text.splitlines():
        if re.match(r"^commits \(base\.\.task/[^)]+\):[ \t]*$", line):
            in_section = True
            continue
        if not in_section:
            continue
        if not line.strip():
            break
        s = line.strip()
        if s in COMMIT_NONE_MARKERS or s.startswith("(base commit unknown"):
            continue
        n += 1
    return n


def _output_tokens(value):
    """The `usage` line's `output` as an int, else None (a torn or non-int
    value never raises, per the docstring's error contract)."""
    if value is None:
        return None
    try:
        data = json.loads(value)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    out = data.get("output")
    if isinstance(out, int) and not isinstance(out, bool):
        return out
    return None


def read_result_fields(path):
    """One `.result` into a dict: `status` (the `FACTORY-RESULT status=` word),
    each metadata `key: value` line named in `RESULT_FIELD_KEYS` into its key,
    `commits` (the non-empty commit-line count, the three markers excluded) and
    `output_tokens` (`usage`'s `output` int, else None). A line that is absent
    is an absent key; a torn (unreadable) file reads `{}` and is the caller's
    to skip. (SD9 interface 1.)"""
    try:
        text = pathlib.Path(path).read_text()
    except OSError:
        return {}
    out = {}
    m = re.search(r"FACTORY-RESULT status=(\S+)", text)
    if m is not None:
        out["status"] = m.group(1)
    for key in RESULT_FIELD_KEYS:
        value = _field(text, rf"^{key}:[ \t]*(.+)$")
        if value is not None:
            out[key] = value
    out["commits"] = _commit_count(text)
    out["output_tokens"] = _output_tokens(out.get("usage"))
    return out


def read_escalations(runs_dir):
    """Each task key's newest `<KEY>.escalate` record (SD3). An `.escalate`
    carries no workspace, so there is no repo attribution; the newest run
    directory's record wins for a key. Returns ``{task key: {run, role,
    escalate, rung, launch}}``."""
    out = {}
    newest = {}
    runs_root = str(runs_dir)
    for p in glob.glob(os.path.join(runs_root, "*", "*.escalate")):
        try:
            text = pathlib.Path(p).read_text()
        except OSError:
            continue
        key = _field(text, r"^key:\s*(.+)$")
        run_name = _field(text, r"^run:\s*(.+)$")
        if not (key and run_name):
            continue
        run_mtime = os.path.getmtime(os.path.dirname(p))
        payload = {
            "run": run_name,
            "role": _field(text, r"^role:\s*(.+)$"),
            "escalate": _field(text, r"^escalate:\s*(.+)$"),
            "rung": _field(text, r"^rung:\s*(\d+)\s*$"),
            "launch": _field(text, r"^launch:\s*(.+)$"),
        }
        if key not in newest or run_mtime > newest[key][0]:
            newest[key] = (run_mtime, payload)
    for key, (_mtime, payload) in newest.items():
        out[key] = payload
    return out


def _judged_index(root):
    """`{plan basename: [(date, path), …]}` — every plan judgement under
    `docs/reviews/plan-judgements/`, its date the file basename's date prefix
    and its plan the basename of the front matter's `plan:` value. A file
    with no block, no `plan:` or no date prefix is skipped, never fatal."""
    import judgements

    root = str(root)
    out = {}
    d = os.path.join(root, "docs", "reviews", "plan-judgements")
    if not os.path.isdir(d):
        return out
    for path in sorted(glob.glob(os.path.join(d, "*.md"))):
        try:
            fm = judgements.parse_front_matter(pathlib.Path(path).read_text())
        except judgements.DuplicateKey:
            continue
        if not fm:
            continue
        plan = fm.get("plan")
        if not isinstance(plan, str) or not plan:
            continue
        m = DATE_PREFIX_RE.match(os.path.basename(path))
        if m is None:
            continue
        out.setdefault(os.path.basename(plan), []).append(
            (m.group(1), os.path.relpath(path, root))
        )
    return out


def judgements_for(root):
    """`{plan basename: [dates]}` — every plan judgement's own date, keyed by
    the basename of the plan its front matter names."""
    return {plan: [d for d, _ in rows] for plan, rows in _judged_index(root).items()}


def panels_naming(root):
    """`{key: [paths]}` — the section panels naming a key: every
    `docs/reviews/*-panel-*-section*.md`, plus any `plan-judgements` file
    whose `tasks:` is a key list rather than an integer (the canonicalised
    count; `parse_keys` drops bare numbers, so a count names no key)."""
    import judgements

    root = str(root)
    out = {}
    paths = sorted(
        glob.glob(os.path.join(root, "docs", "reviews", "*-panel-*-section*.md"))
    ) + sorted(
        glob.glob(os.path.join(root, "docs", "reviews", "plan-judgements", "*.md"))
    )
    for path in paths:
        try:
            fm = judgements.parse_front_matter(pathlib.Path(path).read_text())
        except judgements.DuplicateKey:
            continue
        if not fm:
            continue
        value = fm.get("tasks")
        if not isinstance(value, str) or not value:
            continue
        keys = parse_keys(value.replace("[", " ").replace("]", " "))
        if not keys:
            continue
        rel = os.path.relpath(path, root)
        for k in keys:
            out.setdefault(k, []).append(rel)
    return out


def plan_landing_date(root, plan_rel, cache=None):
    """The committer date (`%cs`) of the plan's first commit — `git log
    --diff-filter=A`, first line — or `None` when git cannot answer (no
    `.git` under root, a failing call, an untracked plan)."""
    cache = {} if cache is None else cache
    key = ("landing", plan_rel)
    if key not in cache:
        cache[key] = None
        if os.path.isdir(os.path.join(str(root), ".git")):
            r = run(
                [
                    "git",
                    "-C",
                    str(root),
                    "log",
                    "--diff-filter=A",
                    "--format=%cs",
                    "--",
                    plan_rel,
                ]
            )
            if r.returncode == 0 and r.stdout.strip():
                cache[key] = r.stdout.strip().splitlines()[0].strip()
    return cache[key]


def section_origin(root, plan_rel, line, cache=None):
    """`("landed"|"appended"|"uncommitted"|"unknown", date)` — git's word on
    when the plan's heading at `line` (1-based) was committed: the blame
    commit equals the plan's first commit (`git log --diff-filter=A
    --format=%H`, first line) → `landed` (the heading came in with the plan,
    date the plan's landing date); a different, non-zero hash → `appended`
    (the blame commit's committer date); the all-zeros hash → `uncommitted`
    (today); `unknown` when either git call fails or `root` has no `.git`
    (the lint sandbox, `evidence-unit`)."""
    cache = {} if cache is None else cache
    key = ("origin", plan_rel, line)
    if key in cache:
        return cache[key]
    out = ("unknown", None)
    root = str(root)
    if os.path.isdir(os.path.join(root, ".git")):
        blame = run(
            [
                "git",
                "-C",
                root,
                "blame",
                "--line-porcelain",
                f"-L{line},{line}",
                "--",
                plan_rel,
            ]
        )
        if blame.returncode == 0 and blame.stdout:
            fields = blame.stdout.splitlines()
            head = fields[0].split() if fields else []
            bhash = head[0] if head else ""
            ctime = None
            for ln in fields:
                if ln.startswith("committer-time "):
                    ctime = ln.partition(" ")[2].strip()
                    break
            if bhash and set(bhash) == {"0"}:
                out = ("uncommitted", _today_utc().isoformat())
            else:
                fkey = ("first-hash", plan_rel)
                if fkey not in cache:
                    r = run(
                        [
                            "git",
                            "-C",
                            root,
                            "log",
                            "--diff-filter=A",
                            "--format=%H",
                            "--",
                            plan_rel,
                        ]
                    )
                    cache[fkey] = (
                        r.stdout.strip().splitlines()[0].strip()
                        if r.returncode == 0 and r.stdout.strip()
                        else ""
                    )
                if cache[fkey]:
                    if bhash == cache[fkey]:
                        out = ("landed", plan_landing_date(root, plan_rel, cache))
                    elif ctime and ctime.isdigit():
                        out = (
                            "appended",
                            datetime.datetime.fromtimestamp(
                                int(ctime), datetime.timezone.utc
                            ).strftime("%Y-%m-%d"),
                        )
    cache[key] = out
    return out


def judged_state(root, task, cache=None):
    """`(state, reason)` — whether a section was judged, derived from what
    exists: `("judged", path)` when a section panel names the key or a
    judgement of its plan is dated on or after the heading's origin date
    (for a `landed` heading, the plan's landing date); `("exempt", reason)`
    when the plan first landed before JUDGED_FROM or git cannot date the
    tree (the sandbox reads `no git`); else `("unjudged", reason)`. A
    withdrawn or parked key is never evaluated — the caller filters."""
    cache = {} if cache is None else cache
    if "panels" not in cache:
        cache["panels"] = panels_naming(root)
    panels = cache["panels"]
    if task["key"] in panels:
        return ("judged", min(panels[task["key"]]))
    plan = task["plan"]
    plan_rel = f"docs/superpowers/plans/{plan}"
    landing = plan_landing_date(root, plan_rel, cache)
    if landing is None:
        return ("exempt", "no git")
    if landing < JUDGED_FROM:
        return ("exempt", f"plan landed {landing} before {JUDGED_FROM}")
    _, hdate = section_origin(root, plan_rel, task["line"], cache)
    if hdate is None:
        return ("exempt", "no git")
    if "index" not in cache:
        cache["index"] = _judged_index(root)
    best = None
    for date, path in sorted(cache["index"].get(plan, [])):
        if date >= hdate:
            best = (date, path)
    if best is not None:
        return ("judged", best[1])
    return ("unjudged", f"no judgement of {plan} dated on or after {hdate}")


def read_recorded(store):
    try:
        import evidence
    except ImportError:
        return {}
    try:
        rows = evidence.read(store, "runs")
        out = {}
        for row in rows:
            plan = os.path.basename(row.get("plan", "") or "")
            for t in row.get("tasks", []) or []:
                key = t.get("key")
                if key:
                    out[(plan, key)] = t.get("status", "recorded")
        return out
    except Exception:  # noqa: BLE001 - a malformed external run row degrades to {}
        return {}


def _chain_members(key, reviews, results, running=None):
    root = chain_root(key)
    running = running or {}
    members = {key}
    for k in set(reviews) | set(results) | set(running):
        if chain_root(k) == root:
            members.add(k)
    return sorted(members, key=lambda k: (k != root, k))


def derive_status(
    task,
    landed,
    reviews,
    results,
    recorded,
    landed_keys,
    extra_landed=None,
    running=None,
    repo=None,
    integrated=None,
    commit_subjects=None,
):
    key = task["key"]
    root = chain_root(key)
    running = running or {}
    members = _chain_members(key, reviews, results, running)
    last = members[-1]  # root first, then by suffix: the last member owns rules 2-4

    # 1. landed
    if task["commit_subject"] in landed:
        return ("landed", task["commit_subject"])
    if (
        any(k in reviews or k in results or k in running for k in members)
        and root in landed_keys
    ):
        return ("landed", root)

    # 2. approved / rejected / integrated — the last member's own review. An
    # approved key whose last member's commit is reachable from an `integ/*`
    # branch but not landed is `integrated` (EV3); the probe is None when the
    # base clone is absent, so `integrated` is then never derived.
    if last in reviews:
        info = reviews[last]
        verdict = info["verdict"].lower()
        if verdict == "approved" and integrated is not None:
            subjects = commit_subjects or {}
            last_subject = subjects.get(last, task.get("commit_subject"))
            if last_subject in integrated:
                return ("integrated", f"{last} by {info['run']}")
        return (verdict, f"{last} by {info['run']}")

    # 2.5 running — the last member's live seat log (outranks a stale result,
    # never outranks its own review)
    if last in running:
        info = running[last]
        return ("running", f"{last} run={info['run']}")

    # 3. ran — the last member's own result
    if last in results:
        info = results[last]
        return ("ran", f"{last} status={info['status']} run={info['run']}")

    # 4. recorded — the last member's own record
    if last in recorded:
        return ("recorded", recorded[last])

    # 5. ready / blocked — by the root's dependencies. Satisfaction is keyed by
    # (repo, chain root): a dependency whose chain root resolves locally (to
    # this repo) is satisfied iff it is in `landed_keys`; one attributed to
    # another repo is satisfied iff that (repo, root) pair is in `extra_landed`.
    # `dep_repo` maps each dependency's chain root to the repo it is attributed
    # to in the task's defining namespace; when absent (direct callers) fall
    # back to the bare-root sets, exactly as before.
    dep_repo = task.get("dep_repo") or {}
    resolved_elsewhere = extra_landed or set()
    missing = []
    for d in task["depends_on"]:
        root = chain_root(d)
        if repo is not None:
            target = dep_repo.get(root, repo)
            if target == repo:
                satisfied = root in landed_keys
            else:
                satisfied = (target, root) in resolved_elsewhere
        else:
            satisfied = root in (set(landed_keys) | resolved_elsewhere)
        if not satisfied:
            missing.append(d)
    if missing:
        return ("blocked", ", ".join(missing))
    return ("ready", "")


def scan_repo(
    repo,
    plan_status,
    runs_dir,
    store,
    run=None,
    repos=None,
    task_status=None,
    stale_after=DEFAULT_STALE_AFTER,
):
    repos = repos or [repo]
    task_status = task_status or {}
    repo_path = repo["path"]
    class_rules, _ = load_class_rules(
        os.path.join(repo_path, "docs", "ledger", "task-classes.toml")
    )
    manifest, _ = load_manifest(
        os.path.join(repo_path, "docs", "ledger", "subsystems.toml")
    )
    plans_glob = os.path.join(repo_path, repo["plans"])
    tasks, legacy, untracked = [], [], []
    # chain root -> the repo its task runs in (None means this repo), for every
    # typed key in this repo's own plan files. Kept whole (including `repo:`
    # redirects) because a `dependsOn` may only name keys defined in this
    # repo's own plans, whatever repo they are attributed to.
    defined = {}
    # chain root -> the set of commit subjects of every member, so a cross-repo
    # dependency resolves "landed in its attributed repo" against that repo's
    # git log rather than this one's.
    root_subjects = {}
    repo_by_name = {r["name"]: r for r in repos}
    # (task key, `repo:` value) for every task this repo's plans attribute to a
    # different repo, so `check` can refuse a value `repos.toml` does not
    # configure (a typo) instead of letting the task vanish from every graph.
    attributed = []

    def own_plan_tasks(plan):
        return [t for t in plan["tasks"] if t["repo"] in (None, repo["name"])]

    for path in sorted(glob.glob(plans_glob)):
        plan = parse_plan(path)
        if plan["typed"]:
            for t in plan["tasks"]:
                root = chain_root(t["key"])
                defined.setdefault(root, t["repo"])
                root_subjects.setdefault(root, set()).add(t["commit_subject"])
                if t["repo"] not in (None, repo["name"]):
                    attributed.append((t["key"], t["repo"]))
            tasks.extend(own_plan_tasks(plan))
        else:
            row = plan_status.get((repo["name"], plan["file"]))
            if row:
                legacy.append(
                    {
                        "file": plan["file"],
                        "status": row["status"],
                        "note": row.get("note", ""),
                    }
                )
            else:
                untracked.append(plan["file"])

    # tasks defined in OTHER configured repos' plans whose `repo` field names
    # this one run here and land here (cross-repo attribution). Each imported
    # task remembers its DEFINING repo (so `check` can resolve its `dependsOn`
    # against that repo's resolvable roots) and the defining repo's definitions
    # are kept for cross-repo landing resolution (MAJOR 2).
    imported = {}
    foreign_defined = {}
    foreign_subjects = {}
    for other in repos:
        if other["name"] == repo["name"]:
            continue
        od, osub = {}, {}
        other_glob = os.path.join(other["path"], other["plans"])
        for path in sorted(glob.glob(other_glob)):
            plan = parse_plan(path)
            if plan["typed"]:
                for t in plan["tasks"]:
                    root = chain_root(t["key"])
                    od.setdefault(root, t["repo"])
                    osub.setdefault(root, set()).add(t["commit_subject"])
                    if t["repo"] == repo["name"]:
                        tasks.append(t)
                        imported[t["key"]] = other["name"]
        foreign_defined[other["name"]] = od
        foreign_subjects[other["name"]] = osub

    landed = landed_subjects(repo_path, run=run)
    integrated = integrated_subjects(repo["name"], landed, run=run)
    reviews = read_reviews(repo_path)
    results = {}
    running = {}
    for (name, k), v in read_results(runs_dir, stale_after).items():
        if name != repo["name"]:
            continue
        # a live log is the entries read_results synthesises without a `file`;
        # a `.result` (including one whose block says `status=running`) always
        # carries `file` and is the seat's final result (`ran`).
        if "file" in v:
            results[k] = v
        else:
            running[k] = v
    recorded_all = read_recorded(store)

    # first pass: chain roots whose subject is landed
    landed_keys = {chain_root(t["key"]) for t in tasks if t["commit_subject"] in landed}

    # cross-repo resolution: a dependency whose chain root is attributed to
    # another repo is satisfied iff that repo's graph has it landed. Resolved
    # through that repo's own git log (results attributed by its base clone),
    # never by mere existence, so the edge never stays blocked once the
    # attributed repo lands the target. Keyed by (repo, chain root) — never a
    # bare root — so one repo's landed root cannot satisfy another repo's
    # same-named local key.
    extra_landed = set()
    landed_cache = {}

    def cached_landed(path):
        if path not in landed_cache:
            landed_cache[path] = landed_subjects(path, run=run)
        return landed_cache[path]

    for root, target in defined.items():
        if target is None or target == repo["name"]:
            continue
        tgt = repo_by_name.get(target)
        if tgt is None:
            continue  # names an unconfigured repo: stays blocked, not satisfied
        if root_subjects[root] & cached_landed(tgt["path"]):
            extra_landed.add((target, root))

    # imported tasks: a `dependsOn` resolves against the DEFINING repo's
    # definitions, and landing is judged where the dependency is attributed
    # there (its `repo:` in the defining repo, defaulting to the defining repo).
    # A dependency attributed back to THIS repo is judged locally (landed_keys),
    # so it is never published in `resolved_elsewhere`.
    for t in tasks:
        defining = imported.get(t["key"])
        if defining is None:
            continue
        od = foreign_defined.get(defining, {})
        osub = foreign_subjects.get(defining, {})
        for d in t["depends_on"]:
            droot = chain_root(d)
            target = od.get(droot)
            if target is None:
                target = defining
            if target == repo["name"]:
                continue  # judged locally, never "elsewhere"
            tgt = repo_by_name.get(target)
            if tgt is None:
                continue
            if osub.get(droot, set()) & cached_landed(tgt["path"]):
                extra_landed.add((target, droot))

    # Per-task dependency attribution: resolve each task's `depends_on` in its
    # DEFINING repo's namespace (a local task -> this repo; an imported task ->
    # its defining repo), mapping each chain root to the repo it is attributed
    # to. `derive_status` and `waves` use this to key satisfaction by
    # (repo, chain root).
    for t in tasks:
        defining = imported.get(t["key"], repo["name"])
        namespace = (
            defined if defining == repo["name"] else foreign_defined.get(defining, {})
        )
        dep_repo = {}
        for d in t["depends_on"]:
            root = chain_root(d)
            target = namespace.get(root)
            dep_repo[root] = defining if target is None else target
        t["dep_repo"] = dep_repo

    # chains: root -> ordered member keys
    chains = {}
    for t in tasks:
        root = chain_root(t["key"])
        if root not in chains:
            chains[root] = _chain_members(t["key"], reviews, results, running)

    # second pass: derive each task's state
    commit_subjects = {t["key"]: t["commit_subject"] for t in tasks}
    for t in tasks:
        recorded = {k: v for (f, k), v in recorded_all.items() if f == t["plan"]}
        state, detail = derive_status(
            t,
            landed,
            reviews,
            results,
            recorded,
            landed_keys,
            extra_landed,
            running,
            repo["name"],
            integrated,
            commit_subjects,
        )
        t["state"] = state
        t["detail"] = detail
        t["chain"] = chains[chain_root(t["key"])]
        t["class"] = task_class(t["touches"], class_rules)
        t["area"], t["area_tie"] = area_of(t, manifest)

    # a task-status row withdraws/parks a key regardless of derived state:
    # never scheduled, never conflicting, shown once in the brief. A `held`
    # row overrides only an open key (ready/blocked, D5) — a hold on a landed
    # key is a check error, never a state change — and a `released` row
    # changes no state at all: both leave the hold's dates on the task
    # (`held_since`/`released`) for the brief's Held line and `json`.
    for t in tasks:
        row = task_status.get((repo["name"], t["plan"], t["key"]))
        t["held_since"] = None
        t["released"] = None
        if not row:
            continue
        if row["status"] in ("held", "released"):
            t["held_since"] = row.get("since") or None
            t["released"] = row.get("released") or None
        if row["status"] in ("withdrawn", "parked"):
            t["state"] = row["status"]
            t["detail"] = row.get("note", "")
        elif row["status"] == "held" and t["state"] in ("ready", "blocked"):
            t["state"] = "held"
            t["detail"] = row.get("note", "")

    attributed_elsewhere = sorted(
        root for root, target in defined.items() if target not in (None, repo["name"])
    )
    return {
        "name": repo["name"],
        "path": repo_path,
        "tasks": tasks,
        "chains": chains,
        "resolvable_roots": sorted(defined),
        "resolved_elsewhere": sorted(extra_landed),
        "attributed_elsewhere": attributed_elsewhere,
        "attributed": sorted(attributed),
        "imported": imported,
        "legacy": legacy,
        "untracked_plans": untracked,
        "manifest": manifest,
        "integ_probe": "absent" if integrated is None else "present",
        "integ_meta": read_run_meta(runs_dir),
    }


def json_graph(graph):
    """The graph as `json` prints it: the task-status map, keyed in memory by the
    `(repo, plan, key)` tuple `check` and the board read, becomes a list of rows
    (`repo`, `plan`, `key` beside the row's own fields) sorted by that tuple;
    everything else is the graph as built."""
    out = dict(graph)
    out["task_status"] = [
        {"repo": repo, "plan": plan, "key": key, **row}
        for (repo, plan, key), row in sorted(graph.get("task_status", {}).items())
    ]
    return out


def build(root, runs_dir, store, run=None, stale_after=DEFAULT_STALE_AFTER):
    repos_path = os.path.join(root, "docs", "ledger", "repos.toml")
    status_path = os.path.join(root, "docs", "ledger", "plan-status.toml")
    task_status_path = os.path.join(root, "docs", "ledger", "task-status.toml")
    repos = load_repos(repos_path)
    plan_status = load_plan_status(status_path)
    task_status = load_task_status(task_status_path)
    return {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "repos": [
            scan_repo(
                r,
                plan_status,
                runs_dir,
                store,
                run=run,
                repos=repos,
                task_status=task_status,
                stale_after=stale_after,
            )
            for r in repos
        ],
        "configured_repos": [r["name"] for r in repos],
        "runs_dir": runs_dir,
        "store": store,
        "task_status": task_status,
    }


def board_graph(root, run=None):
    """The board's queue graph: THIS repo, THIS tree only. No runs dir, no store
    — so `write-board` and `check --board` derive the block identically anywhere,
    including a clean clone. The repo's name comes from the single `ledger = true`
    entry in this tree's `docs/ledger/repos.toml` when that file exists and has
    exactly one; otherwise the tree's basename, as before. A file with two or more
    flagged entries never reaches here — `load_repos` refuses it. The ledger's
    `path` is ignored (home paths differ per machine), so every task still derives
    from this tree; the rendered block omits the name (the header already says
    "this tree").
    """
    root = os.path.abspath(root)
    flagged = ledger_entries(os.path.join(root, "docs", "ledger", "repos.toml"))
    name = flagged[0] if flagged else (os.path.basename(root) or "repo")
    repo = {
        "name": name,
        "path": root,
        "plans": PLANS_GLOB,
    }
    task_status = load_task_status(
        os.path.join(root, "docs", "ledger", "task-status.toml")
    )
    repo_graph = scan_repo(
        repo, {}, None, None, run=run, repos=[repo], task_status=task_status
    )
    # Tree-only: a task whose dependsOn names a key attributed to another repo
    # can't be scheduled here (this tree never sees that repo's landing), so it
    # is deferred to the session brief rather than left `blocked` forever.
    attributed_elsewhere = set(repo_graph.get("attributed_elsewhere", ()))
    for t in repo_graph["tasks"]:
        if t["state"] in ("ready", "blocked") and any(
            chain_root(d) in attributed_elsewhere for d in t["depends_on"]
        ):
            t["state"] = "deferred-to-brief"
            t["detail"] = ""
    return {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "repos": [repo_graph],
        "task_status": task_status,
        "bugs": load_bugs(root),
    }


def touches_overlap(a, b):
    """Two touches conflict when equal, glob-matching either way, or one is
    a directory prefix of the other."""
    a, b = a.rstrip("/"), b.rstrip("/")
    return (
        a == b
        or fnmatch.fnmatch(a, b)
        or fnmatch.fnmatch(b, a)
        or a.startswith(b + "/")
        or b.startswith(a + "/")
    )


def open_tasks(repo_graph):
    """Tasks not yet dispatched: ready or blocked. Approved/rejected/ran/
    recorded tasks are in flight and are never re-scheduled."""
    return [t for t in repo_graph["tasks"] if t["state"] in ("ready", "blocked")]


def waves(repo_graph, plan=None):
    """Kahn layers of the open tasks. Deps outside the filter count as
    satisfied only when landed; an unknown or blocked dep never schedules."""
    name = repo_graph["name"]
    local_landed = {
        chain_root(t["key"]) for t in repo_graph["tasks"] if t["state"] == "landed"
    }
    # The SAME (repo, chain root) set derive_status used: chain roots landed in
    # the repo they are attributed to (cross-repo resolution), so a dependent
    # whose edge resolved to `ready` also enters a wave instead of silently
    # dropping out. Each task's `dep_repo` maps a dep's chain root to the repo
    # it is attributed to, so one repo's landed root never satisfies another
    # repo's same-named local key.
    resolved_elsewhere = {
        (repo, root) for repo, root in repo_graph.get("resolved_elsewhere", ())
    }
    nodes = {
        t["key"]: t for t in open_tasks(repo_graph) if plan is None or t["plan"] == plan
    }
    deps = {}
    for k, t in nodes.items():
        pending = set()
        dep_repo = t.get("dep_repo") or {}
        for d in t["depends_on"]:
            root = chain_root(d)
            target = dep_repo.get(root, name)
            if target == name:
                satisfied = root in local_landed
            else:
                satisfied = (target, root) in resolved_elsewhere
            if not satisfied:
                pending.add(root)
        deps[k] = pending
    out, done = [], set()
    while True:
        ready = sorted(
            k for k in nodes if k not in done and all(d in done for d in deps[k])
        )
        if not ready:
            break
        out.append(ready)
        done.update(ready)
    return out


def seat_group_lists(repo_graph, wave):
    """Merge a wave's keys whose touches overlap into lists of keys, groups
    sorted by first key. Shared by seat_groups (quoted) and wave_structure."""
    keys = sorted(wave)
    by_key = {t["key"]: t for t in repo_graph["tasks"]}
    parent = list(range(len(keys)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ti, tj = by_key[keys[i]]["touches"], by_key[keys[j]]["touches"]
            if any(touches_overlap(pi, pj) for pi in ti for pj in tj):
                union(i, j)

    merged = {}
    for i, key in enumerate(keys):
        merged.setdefault(find(i), []).append(key)
    return sorted((sorted(m) for m in merged.values()), key=lambda m: m[0])


def seat_groups(repo_graph, wave):
    """Merge a wave's keys whose touches overlap; render each group as a
    double-quoted, space-joined string, groups sorted by first key."""
    return [
        '"' + " ".join(members) + '"' for members in seat_group_lists(repo_graph, wave)
    ]


def wave_lines(repo_graph, plan=None):
    """One shell-quoted line per wave (the waves command's default, and the
    source of its --next line)."""
    return [" ".join(seat_groups(repo_graph, w)) for w in waves(repo_graph, plan=plan)]


def wave_structure(repo_graph, plan=None):
    """waves -> groups -> keys (unquoted): the waves command's --json shape."""
    return [seat_group_lists(repo_graph, w) for w in waves(repo_graph, plan=plan)]


def factory_args(repo_graph, plan, key=None):
    """The tasks[] JSON `tools/factory/dark-factory.js` takes for the open
    tasks of one plan. With `key`, that key's entry alone, whatever its derived
    state — the escalation of a running or ran key still names that key."""
    out = []
    tasks = repo_graph["tasks"] if key is not None else open_tasks(repo_graph)
    for t in tasks:
        if t["plan"] != plan:
            continue
        if key is not None and t["key"] != key:
            continue
        out.append(
            {
                "key": t["key"],
                "title": t["title"],
                "kind": t["kind"],
                "checks": t["acceptance"],
                "spec": t["body"].strip(),
                "dependsOn": t["depends_on"],
                "touches": t["touches"],
                "class": t["class"],
            }
        )
    return out


def conflicts(repo_graph):
    """Tasks in flight or queued (every state but landed, withdrawn and
    parked) whose touches overlap — across plans as before and within one
    plan, flagged `same_plan`; one row per overlapping path pair, each row
    carrying both tasks' states. Two tasks can only write the same file
    when their sections resolve to the same repo (a task's own
    `**repo:**` line, default this repo_graph's name) — a `--draft` check
    stitches a draft's tasks into the scanned repo unfiltered, whatever
    repo they are attributed to, so bare path equality alone would
    collide a sibling flake's flake.nix with this repo's."""
    name = repo_graph["name"]
    in_flight = (
        "ready",
        "blocked",
        "held",
        "running",
        "ran",
        "approved",
        "rejected",
        "recorded",
    )
    queued = [t for t in repo_graph["tasks"] if t["state"] in in_flight]
    rows = []
    for i, a in enumerate(queued):
        for b in queued[i + 1 :]:
            if (a["repo"] or name) != (b["repo"] or name):
                continue
            for pa in a["touches"]:
                for pb in b["touches"]:
                    if touches_overlap(pa, pb):
                        first, second = (a, b) if a["key"] < b["key"] else (b, a)
                        rows.append(
                            {
                                "a": first["key"],
                                "plan_a": first["plan"],
                                "state_a": first["state"],
                                "b": second["key"],
                                "plan_b": second["plan"],
                                "state_b": second["state"],
                                "path_a": pa if first is a else pb,
                                "path_b": pb if first is a else pa,
                                "same_plan": a["plan"] == b["plan"],
                            }
                        )
    return rows


def conflict_line(c):
    """One conflicts row as the CLI and the draft check print it: states
    in parentheses beside each plan, ` [same-plan]` on a same-plan row."""
    return (
        f"{c['a']} ({c['plan_a']}, {c['state_a']}) × {c['b']} "
        f"({c['plan_b']}, {c['state_b']}): {c['path_a']} ~ {c['path_b']}"
        + (" [same-plan]" if c["same_plan"] else "")
    )


def _find_cycles(repo):
    roots = {chain_root(t["key"]) for t in repo["tasks"]}
    edges = {}
    for t in repo["tasks"]:
        r = chain_root(t["key"])
        for d in t["depends_on"]:
            dr = chain_root(d)
            if dr in roots and dr != r:
                edges.setdefault(r, set()).add(dr)
    color = {r: 0 for r in roots}  # 0 white, 1 gray, 2 black
    cycles, stack = [], []

    def dfs(u):
        color[u] = 1
        stack.append(u)
        for v in sorted(edges.get(u, ())):
            if color[v] == 1:
                cycles.append(stack[stack.index(v) :] + [v])
            elif color[v] == 0:
                dfs(v)
        stack.pop()
        color[u] = 2

    for r in sorted(roots):
        if color[r] == 0:
            dfs(r)
    return cycles


def _plan_defects_for(repo_path):
    """Load a repo's plan-defect ledger. (front_matter_from, rows) where
    front_matter_from is a datetime.date or None and rows the `[[rejection]]`
    list; (None, []) when the file is absent; None when the file is present
    but unreadable or unparseable."""
    path = pathlib.Path(repo_path) / "docs" / "ledger" / "plan-defects.toml"
    if not path.is_file():
        return (None, [])
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    meta = data.get("meta", {})
    return (meta.get("front_matter_from"), data.get("rejection", []))


def _review_defect_errors(repo_path):
    """The check rule over one repo's reviews and plan-defect ledger."""
    errors = []
    rp = pathlib.Path(repo_path)
    loaded = _plan_defects_for(str(rp))
    if loaded is None:
        errors.append(
            f"tasks: plan-defects: {rp / 'docs' / 'ledger' / 'plan-defects.toml'} "
            "unreadable"
        )
        return errors
    fmf, rows = loaded
    enum_str = " | ".join(PLAN_DEFECT_ENUM)
    block_classes = {}
    reviews_dir = rp / "docs" / "reviews"
    if reviews_dir.is_dir():
        for path in sorted(reviews_dir.glob("*opus-review*.md")):
            name = path.name
            date = _review_date(name)
            try:
                lines = path.read_text().splitlines()
            except OSError:
                lines = []
            has_block, block, first, lookahead = _split_front_matter(lines)
            block_keys = _block_keys(lines)
            if not has_block and fmf is not None and date is not None and date >= fmf:
                errors.append(
                    f"tasks: review {name}: no front-matter block "
                    f"(plan_defect is required from {fmf.isoformat()})"
                )
            if has_block:
                if REVIEW_RE.match(first) is None:
                    errors.append(f"tasks: review {name}: the H1 must follow the block")
                if fmf is not None and date is not None and date >= fmf:
                    shape = REVIEW_SHAPE_RE.match(first)
                    if shape is not None and shape["verdict"] not in (
                        "APPROVED",
                        "REJECTED",
                    ):
                        errors.append(
                            f"tasks: review {name}: H1 verdict {shape['verdict']} "
                            "not in APPROVED | REJECTED"
                        )
                for key in (
                    "mutants_total",
                    "mutants_killed",
                    "mutants_outside_named",
                    "majors",
                    "minors",
                ):
                    raw = block.get(key)
                    if raw is None:
                        continue
                    if raw != "null" and re.fullmatch(r"[0-9]+", raw) is None:
                        errors.append(
                            f"tasks: review {name}: {key} must be an integer or null"
                        )
                rv = block.get("reviewer")
                if rv is not None and rv not in REVIEWER_ENUM:
                    errors.append(
                        f"tasks: review {name}: reviewer {rv} not in "
                        + " | ".join(REVIEWER_ENUM)
                    )
                seen = {}
                for key in block_keys:
                    seen[key] = seen.get(key, 0) + 1
                for key, count in seen.items():
                    if key not in REVIEW_BLOCK_KEYS:
                        errors.append(f"tasks: review {name}: unknown key {key}")
                    if count > 1:
                        errors.append(f"tasks: review {name}: duplicate key {key}")
                pd = block.get("plan_defect")
                pds = block.get("plan_defect_secondary")
                if pd is None:
                    if fmf is not None and date is not None and date >= fmf:
                        errors.append(f"tasks: review {name}: plan_defect missing")
                elif pd not in PLAN_DEFECT_ENUM:
                    errors.append(
                        f"tasks: review {name}: plan_defect {pd} not in {enum_str}"
                    )
                else:
                    m = _review_h1(first, lookahead)
                    if m is not None and m["verdict"] == "REJECTED" and pd == "none":
                        errors.append(
                            f"tasks: review {name}: a rejection names its cause"
                        )
                if pds is not None:
                    if pds not in PLAN_DEFECT_ENUM:
                        errors.append(
                            f"tasks: review {name}: plan_defect_secondary {pds} "
                            f"not in {enum_str}"
                        )
                    elif pds == pd:
                        errors.append(
                            f"tasks: review {name}: plan_defect_secondary equals plan_defect"
                        )
                m = _review_h1(first, lookahead)
                review_ref = "docs/reviews/" + name
                if m is not None and m["verdict"] == "REJECTED" and pd is not None:
                    block_classes[review_ref] = (pd, pds)
                if (
                    m is not None
                    and m["verdict"] == "APPROVED"
                    and any(row.get("review") == review_ref for row in rows)
                ):
                    errors.append(
                        f"tasks: review {name}: a ledger row contradicts an APPROVED block"
                    )
    for row in rows:
        review = row.get("review")
        if review is None:
            errors.append(
                f"tasks: plan-defects row {row.get('run')}/{row.get('key')}: review missing"
            )
            continue
        if not (rp / review).is_file():
            errors.append(
                f"tasks: plan-defects row {row.get('run')}/{row.get('key')}: "
                f"no such review {review}"
            )
        if review in block_classes:
            bc_pd, bc_pds = block_classes[review]
            row_pd = row.get("plan_defect")
            if row_pd != bc_pd:
                errors.append(
                    f"tasks: plan-defects row {row.get('run')}/{row.get('key')}: "
                    f"plan_defect {row_pd} disagrees with the review block ({bc_pd})"
                )
            row_pds = row.get("plan_defect_secondary")
            if row_pds != bc_pds:
                errors.append(
                    f"tasks: plan-defects row {row.get('run')}/{row.get('key')}: "
                    f"plan_defect_secondary {row_pds or 'none'} "
                    f"disagrees with the review block ({bc_pds or 'none'})"
                )
    return errors


def _today_utc():
    return datetime.datetime.now(datetime.timezone.utc).date()


def plan_defect_record(repos, today):
    """The seven-day rejection record aggregated over repos: (total, counts)
    where counts maps a primary plan_defect to its tally. A file both in the
    ledger and carrying a block counts once (the block wins). Returns None when
    any repo's ledger is unreadable."""
    start = today - datetime.timedelta(days=7)
    total = 0
    counts = {}
    for repo in repos:
        repo_path = repo.get("path")
        if repo_path is None:
            continue
        loaded = _plan_defects_for(repo_path)
        if loaded is None:
            return None
        fmf, rows = loaded
        # Blocks on files dated >= front_matter_from, within the window.
        block_primary = {}
        reviews_dir = pathlib.Path(repo_path) / "docs" / "reviews"
        if fmf is not None and reviews_dir.is_dir():
            for path in sorted(reviews_dir.glob("*opus-review*.md")):
                date = _review_date(path.name)
                if date is None or date < fmf or not (start <= date <= today):
                    continue
                has_block, block, first, lookahead = _read_review(path)
                if not has_block:
                    continue
                m = _review_h1(first, lookahead)
                if m is None or m["verdict"] != "REJECTED":
                    continue
                pd = block.get("plan_defect")
                if pd is not None:
                    block_primary["docs/reviews/" + path.name] = pd
        for pd in block_primary.values():
            total += 1
            counts[pd] = counts.get(pd, 0) + 1
        # Ledger rows in the window that a block does not shadow.
        for row in rows:
            pd = row.get("plan_defect")
            date = row.get("date")
            review = row.get("review")
            if pd is None or date is None:
                continue
            if not (start <= date <= today):
                continue
            if review in block_primary:
                continue
            total += 1
            counts[pd] = counts.get(pd, 0) + 1
    return (total, counts)


def integrated_refusals(graph):
    """EV3: a key stuck in `integrated` (approved, its commit on an `integ/*`
    branch, not landed) for more than 24 h, whose wave was launched with
    `--then integrate` (its run.meta says so), is refused — the integrator was
    meant to land it. A key with no run.meta (a hand-integrated task) is never
    refused, and the probe being absent (no base clone) means nothing is ever
    `integrated`, so nothing is refused."""
    errors = []
    for repo in graph["repos"]:
        name = repo["name"]
        integ_meta = repo.get("integ_meta", {})
        for t in repo["tasks"]:
            if t["state"] != "integrated":
                continue
            meta = integ_meta.get(t["key"])
            if meta is None or meta["age_days"] <= 1.0:
                continue
            errors.append(
                f"tasks: {name}/{t['key']}: approved {int(meta['age_days'])} days, "
                "neither landed nor withdrawn"
            )
    return errors


def check(graph, warnings=None):
    """Error strings; empty means the graph is sound. `warnings`, when a list
    is passed, collects the EV19 named-not-fatal probe-freshness warnings —
    the caller prints them and still exits zero."""
    errors = []
    # Repos `repos.toml` configures: the valid targets for a `**repo:**` value.
    # `build`/`main` carry the real ledger's names even when the graph itself was
    # scanned against a `--repos` override; a hand-built test graph falls back to
    # the repos it scanned.
    configured = set(graph.get("configured_repos", [r["name"] for r in graph["repos"]]))
    # Per-repo resolvable sets, so an imported task's `dependsOn` resolves against
    # the repo that DEFINES it (whose plan files name the key) rather than the
    # repo it runs in (MAJOR 2).
    resolvable_by_repo = {
        repo["name"]: set(repo.get("resolvable_roots", ()))
        | {chain_root(t["key"]) for t in repo["tasks"]}
        for repo in graph["repos"]
    }
    for repo in graph["repos"]:
        name = repo["name"]
        # Resolvable keys for THIS repo = every typed key in its own plan files
        # (whatever `repo:` they name) plus the chain roots of its retained and
        # attributed tasks. No global namespace: a key defined only in another
        # repo's own plan files is unknown here.
        resolvable = resolvable_by_repo[name]
        imported = repo.get("imported", {})
        git_ok = _git_available(repo["path"])
        queued = None if git_ok else _board_queued_keys(repo["path"])
        # ER9: one shared judged-state cache per repo — the landing date and
        # the first-commit hash are per plan, the panels and judgements per
        # tree, so a repo's open keys are dated once, not once per key.
        judged_cache = {}

        # a `**repo:**` naming a repo repos.toml does not configure is a silent
        # disappearance (the task leaves every graph); refuse it here.
        for key, value in repo.get("attributed", []):
            if value not in configured:
                errors.append(
                    f"tasks: {name}/{key} repo: {value} not in docs/ledger/repos.toml"
                )

        # the same key defined in more than one typed plan
        plan_order = {}
        for t in repo["tasks"]:
            plan_order.setdefault(t["key"], [])
            if t["plan"] not in plan_order[t["key"]]:
                plan_order[t["key"]].append(t["plan"])
        for key, plans in plan_order.items():
            if len(plans) > 1:
                errors.append(f"tasks: {name}/{key} defined in {' and '.join(plans)}")

        for t in repo["tasks"]:
            defining = imported.get(t["key"])
            rset = resolvable_by_repo.get(defining, resolvable)
            for d in t["depends_on"]:
                if chain_root(d) not in rset:
                    errors.append(
                        f"tasks: {name}/{t['key']} dependsOn {d}: unknown key"
                    )
            if t["kind"] == "code" and not t["acceptance"]:
                errors.append(f"tasks: {name}/{t['key']} (code) has no acceptance")
            for err in t.get("probe_errors", []):
                errors.append(f"tasks: {t['key']} {err}")
            for err in t.get("record_errors", []):
                errors.append(f"tasks: {t['key']} {err}")
            # FA36: a `**probes:**`/`**record:**` header that parsed zero
            # bullets is itself a check error — the seat driver would
            # otherwise run that key silent and unprobed. Guarded on zero
            # bullet-level errors too, so a block whose bullets are malformed
            # is reported once, through the per-bullet path, never twice.
            if (
                t.get("probes_header")
                and not t.get("probes")
                and not t.get("probe_errors")
            ):
                errors.append(f"tasks: {t['key']} probes: empty block")
            if (
                t.get("record_header")
                and not t.get("record")
                and not t.get("record_errors")
            ):
                errors.append(f"tasks: {t['key']} record: empty block")
            # DF13: pre-state and line-pinned probes are refused only on keys
            # still open (ready or blocked); a landed plan's probes were already
            # evaluated against the final tree at commit time.
            if t.get("state") in ("ready", "blocked"):
                for probe in t.get("probes", []):
                    if PRE_STATE_NOTE_RE.search(probe.get("by") or ""):
                        errors.append(
                            f"tasks: {t['key']} probes: pre-state: {probe['name']}"
                        )
                    if LINE_PIN_RE.search(probe.get("cmd") or ""):
                        errors.append(
                            f"tasks: {t['key']} probes: line-pin: {probe['name']}"
                        )
            # ER5: an OPEN section's probe naming a bare devShell tool is a
            # NAMED warning — never fatal, the fix is amending the section in
            # place; a landed/ran section's probes were already evaluated at
            # commit time and stay silent. A draft's new text is refused by
            # draft_rules instead; here only the queued plans warn.
            if warnings is not None and t.get("state") in ("ready", "blocked", "held"):
                for probe in t.get("probes", []):
                    for tok in bare_tools(probe["cmd"]):
                        warnings.append(
                            f"tasks: warning: {t['plan']}/{t['key']} probes: "
                            f"{probe['name']}: bare tool {tok} — the driver's "
                            "PATH lacks it; run it under nix develop -c"
                        )
            # ER9: an open key neither a section panel nor a plan judgement
            # dated on or after its heading's origin covers — a NAMED warning,
            # never fatal here (the dispatch refusal is ER10's). Landed and
            # in-flight keys were judged before they ran; a git-less tree (the
            # lint sandbox) degrades to exempt and stays silent.
            if warnings is not None and t.get("state") in JUDGED_OPEN_STATES:
                state, reason = judged_state(repo["path"], t, judged_cache)
                if state == "unjudged":
                    warnings.append(
                        f"tasks: warning: {t['plan']}/{t['key']} unjudged: {reason}"
                    )
            # EV19 (shape B, the refusal half): the section's own numeric
            # bounds on one command must be satisfiable together — a pair
            # like `gt 9` with `le 9` can never hold of any tree, so it is
            # refused for every section, landed or open, before a seat burns
            # an hour finding it.
            bounds_by_cmd = {}
            for probe in t.get("probes", []):
                if probe["op"] in PROBE_NUM_OPS:
                    bounds_by_cmd.setdefault(probe["cmd"], []).append(probe)
            for cmd, group in bounds_by_cmd.items():
                if _bounds_empty(group):
                    bounds = ", ".join(
                        f"{p['name']} ({p['op']} {p['value']})" for p in group
                    )
                    errors.append(
                        f"tasks: {t['plan']}/{t['key']} probes: unsatisfiable: "
                        f"`{cmd}` cannot hold {bounds} together"
                    )
            # EV19 (shape B, the warning half): a numeric bound of a section
            # that has run, violated by the current tree — a NAMED warning,
            # never fatal: the bound describes a tree that no longer exists.
            # Open sections' probes describe the tree the task will produce
            # and are never freshness-evaluated. Imported tasks run in
            # another repo's tree, so their probes are skipped here too.
            if (
                warnings is not None
                and t.get("state") in PROBE_FRESH_STATES
                and imported.get(t["key"]) is None
            ):
                for cmd, group in bounds_by_cmd.items():
                    measured = run_probe(cmd, repo["path"])
                    if measured is None:
                        continue
                    for p in group:
                        if not _bound_holds(p, measured):
                            warnings.append(
                                f"tasks: warning: {t['plan']}/{t['key']} probes: "
                                f"stale: {p['name']} ({p['op']} {p['value']}): "
                                f"the tree measures {measured:g}"
                            )
            # DF16: a `**Steps.**` command that lands the task's own work —
            # merging main or restoring the board block — is refused only on
            # keys still open. When git is readable the open set is
            # `ready`/`blocked`; in the git-less lint sandbox it falls back to
            # the board's Queued line (the one git-free record of which keys the
            # last commit still considered open), so a landed key the board
            # omits (KN17's shape) is exempt without git.
            if git_ok:
                in_scope = t.get("state") in ("ready", "blocked")
            else:
                in_scope = queued is None or t["key"] in queued
            if in_scope:
                for line, fenced in t.get("steps_lines", []):
                    for span in _steps_land_spans(line, fenced):
                        if STEPS_LAND_RE.search(span):
                            errors.append(
                                f"tasks: {t['key']} steps: lands own work "
                                f"({t['plan']}): {line.strip()}"
                            )
                            break

        for cycle in _find_cycles(repo):
            errors.append(f"tasks: cycle in {name}: {' -> '.join(cycle)}")

    # a task-status row must name a key some plan actually defines, and its
    # status must be exactly one of the four recorded values — never a
    # silently-scheduled mistype. A `held` row needs a `since` date, a
    # `released` row both dates in order, and `held` overrides only an open
    # key (ready/blocked, D5): the scanned state (a held row that applied
    # reads `held`) names the state it refused to override.
    defined_rows = {
        (repo["name"], t["plan"], t["key"])
        for repo in graph["repos"]
        for t in repo["tasks"]
    }
    task_states = {
        (repo["name"], t["plan"], t["key"]): t["state"]
        for repo in graph["repos"]
        for t in repo["tasks"]
    }
    for (repo, plan, key), row in graph.get("task_status", {}).items():
        if (repo, plan, key) not in defined_rows:
            errors.append(f"tasks: task-status names unknown key {repo}/{plan}/{key}")
        status = row.get("status")
        if status not in ("withdrawn", "parked", "held", "released"):
            errors.append(
                f"tasks: task-status row {repo}/{plan}/{key}: unknown status {status}"
            )
            continue
        since = None
        if status in ("held", "released"):
            try:
                since = datetime.date.fromisoformat(row.get("since") or "")
            except ValueError:
                errors.append(
                    f"tasks: task-status row {repo}/{plan}/{key}: "
                    "held requires since (YYYY-MM-DD)"
                )
        if status == "released":
            try:
                released = datetime.date.fromisoformat(row.get("released") or "")
            except ValueError:
                released = None
                errors.append(
                    f"tasks: task-status row {repo}/{plan}/{key}: "
                    "released requires released (YYYY-MM-DD)"
                )
            else:
                if since is not None and released < since:
                    errors.append(
                        f"tasks: task-status row {repo}/{plan}/{key}: "
                        "released before since"
                    )
        if status == "held":
            state = task_states.get((repo, plan, key))
            if state not in ("ready", "blocked", "held"):
                errors.append(
                    f"tasks: task-status row {repo}/{plan}/{key}: held but {state}"
                )
    # the plan-defect ledger, each gate review's front-matter block, and the
    # task-classes rules file (a malformed rule is refused, SD2)
    for repo in graph["repos"]:
        if repo.get("path"):
            rp = pathlib.Path(repo["path"]) / "docs" / "ledger" / "task-classes.toml"
            _, cls_errs = load_class_rules(str(rp))
            for e in cls_errs:
                errors.append(f"tasks: task-classes: {e}")
            errors.extend(_review_defect_errors(repo["path"]))
    # EV2: the area dimension. Each repo's manifest and grandfather list are
    # read once; a task whose touches span more than one area without an
    # `areas:` declaration is refused (unless its key is grandfathered), and a
    # key whose leading letters match a manifest prefix is refused when its
    # plan file matches none of that subsystem's `plans` globs (G7).
    for repo in graph["repos"]:
        if not repo.get("path"):
            continue
        ledger = pathlib.Path(repo["path"]) / "docs" / "ledger"
        manifest, manifest_errs = load_manifest(str(ledger / "subsystems.toml"))
        for e in manifest_errs:
            errors.append(f"tasks: manifest: {e}")
        grandfathered = load_grandfathered(str(ledger / "areas-grandfather.toml"))
        plans_dir = os.path.dirname(repo.get("plans", PLANS_GLOB))
        for t in repo["tasks"]:
            spans = spanned_areas(t, manifest)
            if (
                len(spans) > 1
                and t.get("state") in ("ready", "blocked", "ran", "running")
                and not t.get("areas")
                and t["key"] not in grandfathered
            ):
                errors.append(
                    f"tasks: {t['plan']}/{t['key']}: touches span areas "
                    f"{', '.join(spans)} without an areas: declaration"
                )
            prefix = reserved_prefix(t["key"])
            if prefix:
                plow = prefix.lower()
                for row in manifest:
                    if (row.get("prefix") or "").lower() == plow:
                        plan_path = os.path.join(plans_dir, t["plan"])
                        if not any(
                            fnmatch.fnmatch(plan_path, glb) for glb in row["plans"]
                        ):
                            errors.append(
                                f"tasks: {t['plan']}/{t['key']}: prefix "
                                f"{row['prefix']} is reserved for {row['name']}, "
                                f"whose plans are {', '.join(row['plans'])}"
                            )
                        break
    return errors


def map_check_names(root):
    """The check names listed under docs/MAP.md's `## Checks` heading — the same
    awk as the lint block (lines starting `- ` beneath that heading, stopping at
    the next `## `). None when the file cannot be read."""
    path = os.path.join(root, "docs", "MAP.md")
    try:
        lines = pathlib.Path(path).read_text().splitlines()
    except OSError:
        return None
    names = set()
    in_checks = False
    for line in lines:
        if line.startswith("## Checks"):
            in_checks = True
            continue
        if line.startswith("## "):
            in_checks = False
            continue
        if in_checks and line.startswith("- "):
            names.add(line[2:].strip())
    return names


def load_draft(file, root, repos, scanned):
    """Read a draft plan outside the plans directory and attach it to the repo
    whose configured `path` realpath-equals `root`. Usage errors (unreadable
    file, file already under the plans directory, root with no matching repo)
    exit 2. A basename that collides with an existing plan REPLACES that plan's
    tasks (replan: every `### ` line of the existing file must appear
    byte-identical) and otherwise the draft's tasks are ADDED; in either case
    the draft's tasks are given state `ready`. Returns the info `draft_rules`
    consumes, including any replan heading-drop errors."""
    # (1) readable
    try:
        text = pathlib.Path(file).read_text()
    except OSError:
        print(f"tasks: --draft: cannot read {file}", file=sys.stderr)
        raise SystemExit(2)

    root_real = os.path.realpath(root)
    # (3) the configured repo whose path realpath-equals root
    repo = None
    for r in repos:
        if os.path.realpath(r["path"]) == root_real:
            repo = r
            break
    if repo is None:
        print(f"tasks: --draft: no configured repo has path {root}", file=sys.stderr)
        raise SystemExit(2)

    # (2) the draft may not already live in the plans directory
    plans_dir = os.path.join(repo["path"], os.path.dirname(repo["plans"]))
    plans_real = os.path.realpath(plans_dir)
    real = os.path.realpath(file)
    if real == plans_real or real.startswith(plans_real + os.sep):
        print(
            f"tasks: --draft: {file} is already under the plans directory; "
            "run check without --draft",
            file=sys.stderr,
        )
        raise SystemExit(2)

    scanned_repo = next(r for r in scanned if r["name"] == repo["name"])
    landed = landed_subjects(scanned_repo["path"])
    draft = parse_plan(file)
    plan_name = draft["file"]
    # chain-root -> {existing tasks' chain roots} per commit subject, so the
    # "already landed" rule can exempt a fix round / re-plan reusing its root's
    # subject (task → its own root), judged before the draft is attached.
    existing_subject_roots = {}
    for t in scanned_repo["tasks"]:
        existing_subject_roots.setdefault(t["commit_subject"], set()).add(
            chain_root(t["key"])
        )

    errors = []
    existing_plan_file = os.path.join(plans_dir, plan_name)
    replan = os.path.isfile(existing_plan_file)
    if replan:
        try:
            existing_lines = pathlib.Path(existing_plan_file).read_text().splitlines()
        except OSError:
            existing_lines = []
        draft_lines = set(text.splitlines())
        for ln in existing_lines:
            if ln.startswith("### ") and ln not in draft_lines:
                errors.append(f"tasks: draft drops heading: {ln}")
        scanned_repo["tasks"] = [
            t for t in scanned_repo["tasks"] if t["plan"] != plan_name
        ]
    for t in draft["tasks"]:
        t["state"] = "landed" if t["commit_subject"] in landed else "ready"
    scanned_repo["tasks"].extend(draft["tasks"])

    return {
        "tasks": draft["tasks"],
        "plan_name": plan_name,
        "lines": text.splitlines(),
        "existing_subject_roots": existing_subject_roots,
        "landed": landed,
        "errors": errors,
        "replan": replan,
        "scanned": scanned_repo,
    }


REQUIRED_SECTIONS = (
    "## Global Constraints",
    "## Assumptions",
    "## Waves",
    "## Operator",
)


def draft_rules(draft, repo, map_names, landed):
    """The draft-only rules (never applied to landed plans, so no existing plan
    can turn red): acceptance names from docs/MAP.md, explicit touches, the
    commit-subject shape and its (test: …) names, size, the four house sections,
    and one section per key."""
    errors = []
    name = repo["name"]
    tasks = draft["tasks"]
    plan_name = draft["plan_name"]
    existing_subject_roots = draft["existing_subject_roots"]

    # (e) headers: the four house sections must be present (prefix match).
    lines = draft["lines"]
    for req in REQUIRED_SECTIONS:
        if not any(ln.startswith(req) for ln in lines):
            errors.append(f"tasks: draft lacks section {req[3:]}")

    # (f) one section per key, keyed by the draft's basename (check()'s
    # duplicate rule only counts distinct plan names, so it cannot see two
    # sections of one file).
    seen = set()
    for t in tasks:
        if t["key"] in seen:
            errors.append(f"tasks: {t['key']} defined twice in {plan_name}")
        seen.add(t["key"])

    for t in tasks:
        key = t["key"]
        attributed_elsewhere = t["repo"] not in (None, name)
        # (a) acceptance names — exempt for tasks attributed to another repo
        # (that repo's checks are not in this MAP).
        if not attributed_elsewhere:
            if map_names is None:
                errors.append(
                    f"tasks: {key}: docs/MAP.md unreadable; cannot verify acceptance"
                )
            else:
                for entry in t["acceptance"]:
                    if entry != "lint" and entry not in map_names:
                        errors.append(
                            f"tasks: {key} acceptance {entry} not in docs/MAP.md"
                        )
        # (b) touches — explicit paths only; a code task must touch something.
        if not t["touches"] and t["kind"] == "code":
            errors.append(f"tasks: {key} touches: empty")
        else:
            for entry in t["touches"]:
                if any(ch in entry for ch in "*?["):
                    errors.append(
                        f"tasks: {key} touches {entry}: glob is not an explicit path"
                    )
        # (d) size — L is refused and asked to split.
        if t["size"] == "L":
            errors.append(f"tasks: {key}: size L is refused; split it")
        # (c) commit subject — exempt for tasks attributed to another repo.
        if not attributed_elsewhere:
            subject = t["commit_subject"] or ""
            m = re.fullmatch(r"[a-z][a-z0-9-]*: .+ \(test: ([^)]+)\)", subject)
            if m is None:
                errors.append(
                    f"tasks: {key} commit subject (test: ?) differs from acceptance"
                )
            else:
                names = {x.strip() for x in m.group(1).split(",") if x.strip()}
                if names != set(t["acceptance"]):
                    errors.append(
                        f"tasks: {key} commit subject (test: {m.group(1)}) "
                        "differs from acceptance"
                    )
            if subject in landed and chain_root(key) not in existing_subject_roots.get(
                subject, set()
            ):
                errors.append(f"tasks: {key} commit subject already landed: {subject}")

    # (g) EV19, shape A — touch completeness: for every touched path not
    # itself under a test directory, every test file of this repo that
    # references it (by path string, by module name, or by a symbol the file
    # defines) must be declared in `touches` or exempted with a reason. The
    # refusal names the reference so the fix is an amendment, not a search;
    # reference matching is a lower bound on the real relation — it needs no
    # semantic model. A reasonless exemption is itself refused; the two
    # standing G5 exemptions are declared once in the checker.
    test_files = None
    for t in tasks:
        exempt, exempt_errors = _parse_touches_exempt(t)
        errors.extend(exempt_errors)
        if t["repo"] not in (None, name):
            continue  # its tests live in the repo it is attributed to
        if test_files is None:
            test_files = _repo_test_files(repo["path"])
        declared = set(t["touches"])
        for touch in t["touches"]:
            if touch in TOUCH_ARM_STANDING_EXEMPT or _is_test_path(touch):
                continue
            stop_names = (
                _non_distinctive_symbol_names(touch, repo["path"], test_files)
                if touch.endswith(".py")
                else frozenset()
            )
            for rel, text in test_files:
                if rel in declared or rel in exempt:
                    continue
                kind = _reference_kind(touch, text, repo["path"], stop_names)
                if kind is not None:
                    errors.append(
                        f"tasks: {plan_name}/{t['key']} touches {touch}: "
                        f"{rel} references it ({kind}) — declare it in touches "
                        "or exempt it with a reason"
                    )

    # two draft tasks with different chain roots may not share a subject
    root_by_subject = {}
    for t in tasks:
        subj = t["commit_subject"]
        root = chain_root(t["key"])
        if subj in root_by_subject and root_by_subject[subj] != root:
            errors.append(
                f"tasks: {t['key']} commit subject {subj} shared by a different "
                "chain root"
            )
        root_by_subject.setdefault(subj, root)

    # (h) ER5: a probe that names a devShell tool BARE — python3, jq, bats,
    # pytest, … — is refused: the driver's PATH lacks every one of them, so
    # the probe could never run green. One error line per offending token.
    for t in tasks:
        for probe in t.get("probes", []):
            for tok in bare_tools(probe["cmd"]):
                errors.append(
                    f"tasks: {plan_name}/{t['key']} probes: {probe['name']}: "
                    f"bare tool {tok} — the driver's PATH lacks it; "
                    "run it under nix develop -c"
                )

    return errors


SEATS_DAYS = 7


def seat_stats(runs_dir, now=None, days=SEATS_DAYS, store=None):
    """Per-model rows from the `.result` files under `runs_dir` whose mtime is
    within `days` days of `now` — a `.log` is never opened. model: the `model:`
    line (`unknown` when absent); runs; done: the last `FACTORY-RESULT status=`
    word is `done`; wall: the int `wall_s:` samples; billed: the `usage:` JSON's
    `input` + `output`; cached: its `cacheRead`. `usd` is read from `store`'s
    `ledger/openrouter-usage` — `instance == "seat"` rows with `status == "ok"`
    and `ts_epoch` inside the cutoff, `math.fsum(cost_usd)` per model, `None`
    for a model with no rows (and no `store`). `usd_attr` is the same sum over
    the attributed rows only (OC5: `attribution` in `header`/`window`) and
    `done_attr` counts the model's done `.result` files whose `(run, key)`
    (the file's own `run:`/`key:` lines) carries attributed dollars — the join
    `$/done` prints from (OC6). Sorted by runs descending, then model."""
    now = time.time() if now is None else now
    cutoff = now - days * 86400
    usd_by_model = {}
    usd_attr_by_model = {}
    attributed = set()
    if store:
        try:
            import evidence
        except ImportError:
            pass
        else:
            for row in evidence.read(store, "ledger/openrouter-usage"):
                if (
                    row.get("instance") == "seat"
                    and row.get("status") == "ok"
                    and (row.get("ts_epoch") or 0) >= cutoff
                    and row.get("model")
                ):
                    usd_by_model[row["model"]] = math.fsum(
                        [
                            usd_by_model.get(row["model"], 0.0),
                            row.get("cost_usd") or 0.0,
                        ]
                    )
                    if row.get("attribution") in ("header", "window"):
                        usd_attr_by_model[row["model"]] = math.fsum(
                            [
                                usd_attr_by_model.get(row["model"], 0.0),
                                row.get("cost_usd") or 0.0,
                            ]
                        )
                        attributed.add((row.get("run_id"), row.get("key")))
    rows = {}
    for p in glob.glob(os.path.join(str(runs_dir), "*", "*.result")):
        try:
            if os.path.getmtime(p) < cutoff:
                continue
            text = pathlib.Path(p).read_text()
        except OSError:
            continue
        statuses = re.findall(r"^FACTORY-RESULT status=(\S+)", text, re.MULTILINE)
        if not statuses:
            continue
        model = _field(text, r"^model:[ \t]*(.+)$") or "unknown"
        run = _field(text, r"^run:[ \t]*(.+)$")
        key = _field(text, r"^key:[ \t]*(.+)$")
        row = rows.setdefault(
            model,
            {
                "model": model,
                "runs": 0,
                "done": 0,
                "done_attr": 0,
                "wall": [],
                "billed": 0,
                "cache_read": 0,
                "usd": None,
                "usd_attr": 0.0,
            },
        )
        row["runs"] += 1
        if statuses[-1] == "done":
            row["done"] += 1
            if (run, key) in attributed:
                row["done_attr"] += 1
        wall = _field(text, r"^wall_s:[ \t]*(\d+)[ \t]*$")
        if wall is not None:
            row["wall"].append(int(wall))
        usage_line = _field(text, r"^usage:[ \t]*(.+)$")
        if usage_line:
            try:
                usage = json.loads(usage_line)
            except ValueError:
                usage = None
            if isinstance(usage, dict):
                for k in ("input", "output"):
                    v = usage.get(k)
                    if isinstance(v, int) and not isinstance(v, bool):
                        row["billed"] += v
                v = usage.get("cacheRead")
                if isinstance(v, int) and not isinstance(v, bool):
                    row["cache_read"] += v
    for row in rows.values():
        row["usd"] = usd_by_model.get(row["model"])
        row["usd_attr"] = usd_attr_by_model.get(row["model"], 0.0)
    return sorted(rows.values(), key=lambda r: (-r["runs"], r["model"]))


def render_seats_line(stats):
    if not stats:
        return "**Seats (7 d):** none"
    parts = []
    for r in stats:
        runs = f"{r['runs']} run" if r["runs"] == 1 else f"{r['runs']} runs"
        wall = (
            f"{(statistics.median_low(r['wall']) + 30) // 60} min"
            if r["wall"]
            else "? min"
        )
        piece = (
            f"{r['model']}: {runs}, {r['done']} done, {wall}, "
            f"{r['billed']} billed, {r['cache_read']} cached"
        )
        if r.get("usd") is not None:
            per = f"{r['usd_attr'] / r['done_attr']:.2f}" if r["done_attr"] else "-"
            share = round(100 * r["usd_attr"] / r["usd"]) if r["usd"] else 0
            piece += f", $/done {per} (attributed {share}% of ${r['usd']:.2f})"
        parts.append(piece)
    return "**Seats (7 d):** " + " · ".join(parts)


def load_bugs(root):
    """Read docs/ledger/bugs.toml's `[[bug]]` rows; [] when the file is absent
    or malformed (the validator reports malformed rows; the brief just omits).
    Converts any datetime.date or datetime.datetime value tomllib produces
    (e.g. bare TOML dates like `found = 2026-09-10`) to its ISO-8601 string so
    the graph carries only JSON-serializable values."""
    path = os.path.join(root, "docs", "ledger", "bugs.toml")
    try:
        with open(path, "rb") as fh:
            rows = tomllib.load(fh).get("bug", [])
    except (OSError, tomllib.TOMLDecodeError):
        return []
    for row in rows:
        for key, value in list(row.items()):
            if isinstance(value, (datetime.date, datetime.datetime)):
                row[key] = value.isoformat()
    return rows


def render_open_bugs(bugs):
    """`**Open bugs:** BUG-a (task), BUG-b (untyped)` from the open rows, else
    `none`."""
    open_rows = [b for b in bugs if b.get("status") == "open"]
    if not open_rows:
        return "**Open bugs:** none"
    parts = []
    for b in open_rows:
        bid = b.get("id", "?")
        task = b.get("task") or ""
        parts.append(f"{bid} ({task})" if task else f"{bid} (untyped)")
    return "**Open bugs:** " + ", ".join(parts)


def render_brief(graph, claims_rows=None, today=None):
    """One-screen markdown board brief: per-repo state counts, the next wave,
    the seven-day plan-defect record, rejected fixes owed, operator-owned gaps
    and untracked plans."""
    if today is None:
        today = _today_utc()
    elif isinstance(today, str):
        # the brief's `--today` arrives pre-parsed from the CLI; a string
        # today (an ISO date) is coerced so the Held line's age and the
        # seven-day record see the same date either way.
        today = datetime.date.fromisoformat(today)
    lines = [f"# Task brief (generated {graph['generated']})", ""]
    lines.append(
        "| repo | landed | approved | rejected | ran | running | recorded | ready | "
        "blocked | deferred-to-brief | withdrawn | parked | held | legacy open | "
        "untracked |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for repo in graph["repos"]:
        counts = {s: 0 for s in STATES}
        for t in repo["tasks"]:
            if t["state"] in counts:
                counts[t["state"]] += 1
        legacy_open = sum(1 for r in repo["legacy"] if r["status"] == "open")
        # EV3: `integrated` folds into the `approved` cell as `N (integrated k)`
        # — no new column, so the table width is unchanged. `N` is the approved
        # total (approved + integrated), `k` the integrated subset.
        state_cols = [counts[s] for s in STATES if s != "integrated"]
        approved_idx = STATES.index("approved")
        approved_total = counts["approved"] + counts["integrated"]
        if counts["integrated"]:
            state_cols[approved_idx] = (
                f"{approved_total} (integrated {counts['integrated']})"
            )
        else:
            state_cols[approved_idx] = approved_total
        cols = state_cols + [legacy_open, len(repo["untracked_plans"])]
        lines.append(f"| {repo['name']} | " + " | ".join(str(c) for c in cols) + " |")
    lines.append("")

    next_wave = []
    for repo in graph["repos"]:
        ws = waves(repo)
        if not ws:
            continue
        keys = ws[0]
        by_key = {t["key"]: t for t in repo["tasks"]}
        open_plans = {t["plan"] for t in open_tasks(repo)}
        wave_plans = {t["plan"] for t in open_tasks(repo) if t["key"] in keys}
        label = " ".join(f"{k}({by_key[k]['class']})" for k in keys)
        if len(wave_plans) == 1 and len(open_plans) > 1:
            label += f" (plan {next(iter(wave_plans))})"
        next_wave.append(f"{repo['name']}: {label}")
    lines.append("**Next wave** — " + (" · ".join(next_wave) if next_wave else "none"))

    for repo in graph["repos"]:
        if not repo.get("manifest"):
            continue
        lines.append(f"**Areas** ({repo['name']})")
        lines.extend(render_area_lines(repo))

    record = plan_defect_record(graph["repos"], today)
    if record is None:
        lines.append("**Record: unavailable**")
    else:
        total, counts = record
        caused = sum(counts.get(c, 0) for c in PLAN_DEFECT_CAUSED)
        parts = ", ".join(
            f"{PLAN_DEFECT_SHORT[c]} {counts.get(c, 0)}" for c in PLAN_DEFECT_CAUSED
        )
        lines.append(f"**Record (7 d):** {total} rej, {caused} plan ({parts})")

    if graph.get("runs_dir"):
        lines.append(
            render_seats_line(seat_stats(graph["runs_dir"], store=graph.get("store")))
        )
    else:
        lines.append("**Seats (7 d):** none")

    running = []
    for repo in graph["repos"]:
        seen = set()
        for t in repo["tasks"]:
            if t["state"] != "running":
                continue
            root = chain_root(t["key"])
            if root in seen:
                continue
            seen.add(root)
            item = f"{repo['name']}/{root}"
            if t["detail"]:
                item += f" ({t['detail']})"
            running.append(item)
    lines.append("**Running:** " + (" · ".join(running) if running else "none"))

    rejected = []
    for repo in graph["repos"]:
        # A root's fix-round successor (same plan, chain_root(key) == root,
        # longer key) that has already landed or been approved closes the
        # root's obligation, even though the root's own last review still
        # reads REJECTED.
        fixed_roots = {
            (t["plan"], chain_root(t["key"]))
            for t in repo["tasks"]
            if t["state"] in ("landed", "approved") and t["key"] != chain_root(t["key"])
        }
        seen = set()
        for t in repo["tasks"]:
            if t["state"] != "rejected":
                continue
            root = chain_root(t["key"])
            if root in seen:
                continue
            seen.add(root)
            if (t["plan"], root) in fixed_roots:
                continue
            item = f"{repo['name']}/{root}"
            if t["detail"]:
                item += f" ({t['detail']})"
            rejected.append(item)
    lines.append(
        "**Rejected, fix round owed:** "
        + (" · ".join(rejected) if rejected else "none")
    )

    escalations = read_escalations(graph["runs_dir"]) if graph.get("runs_dir") else {}
    # ER18: the line lists only escalations still owed to a human — a key that
    # resolves, in any repo of the graph, to a task whose chain root is landed,
    # withdrawn or parked is a debt already closed (the same rule the Rejected
    # fix-round line applies: a landed fix round `K1b` closes `K1`'s escalation
    # as it closes its rejection). A key no plan defines anywhere stays listed:
    # an ad-hoc escalation is still owed. The count of filtered entries is
    # appended when N > 0 (`**Design failures:**` keeps counting the full set).
    if escalations:
        closed = ("landed", "withdrawn", "parked")
        kept, filtered = [], 0
        for k, e in sorted(escalations.items()):
            root = chain_root(k)
            states = [
                t["state"]
                for repo in graph["repos"]
                for t in repo["tasks"]
                if chain_root(t["key"]) == root
            ]
            if states and any(s in closed for s in states):
                filtered += 1
                continue
            kept.append(f"{k} ({e['escalate']}, rung {e['rung']}, run {e['run']})")
        suffix = f" ({filtered} filtered)" if filtered else ""
        lines.append(
            "**Escalated:** " + (" · ".join(kept) if kept else "none") + suffix
        )
    else:
        lines.append("**Escalated:** none")

    # ER9: the open keys neither a section panel nor a plan judgement dated
    # on or after their heading's origin covers — one line after Escalated,
    # derived, never typed; the dispatch refusal itself is ER10's.
    unjudged = []
    for repo in graph["repos"]:
        cache = {}
        for t in repo["tasks"]:
            if t.get("state") not in JUDGED_OPEN_STATES:
                continue
            state, _ = judged_state(repo["path"], t, cache)
            if state == "unjudged":
                unjudged.append(f"{t['key']} ({t['plan']})")
    unjudged.sort()
    lines.append(
        "**Unjudged (open):** " + (" · ".join(unjudged) if unjudged else "none")
    )
    import bugs

    graph_json = json_graph(graph)
    open_count = sum(1 for k in escalations if bugs._closure(k, graph_json) == "open")
    lines.append(f"**Design failures:** {len(escalations)} ({open_count} open)")

    withdrawn = [
        f"{repo['name']}/{t['key']}"
        for repo in graph["repos"]
        for t in repo["tasks"]
        if t["state"] in ("withdrawn", "parked")
    ]
    lines.append(
        "**Withdrawn/parked:** " + (" · ".join(withdrawn) if withdrawn else "none")
    )

    if claims_rows is None:
        lines.append("**Operator owns:** (claims file not read)")
    else:
        owned = []
        for c in claims_rows:
            if c.get("status") == "gap" and c.get("owner") == "operator":
                item = c["id"]
                if c.get("review_by"):
                    item += f" (review by {c['review_by']})"
                elif c.get("note"):
                    item += f" ({c['note']})"
                owned.append(item)
        lines.append("**Operator owns:** " + (" · ".join(owned) if owned else "none"))

    # the operator's holds, one per held key with its age in whole days
    # (today is the brief's --today, else the generation date).
    held_items = []
    for repo in graph["repos"]:
        for t in repo["tasks"]:
            if t["state"] != "held":
                continue
            since = t.get("held_since") or ""
            age = ""
            try:
                age = f" ({(today - datetime.date.fromisoformat(since)).days} d)"
            except ValueError:
                age = ""
            held_items.append(
                (t["key"], f"{repo['name']}/{t['key']} since {since}{age}")
            )
    held_items.sort()
    lines.append(
        "**Held (operator):** "
        + (" · ".join(text for _, text in held_items) if held_items else "none")
    )

    untracked = [
        f"{repo['name']}/{f}"
        for repo in graph["repos"]
        for f in repo["untracked_plans"]
    ]
    lines.append(
        "**Untracked plans (no typed headings, no plan-status row):** "
        + (" · ".join(untracked) if untracked else "none")
    )

    lines.append(render_open_bugs(graph.get("bugs", [])))
    return "\n".join(lines) + "\n"


def render_area_lines(repo):
    """One `Area: <area> — …` string per manifest row, in manifest order, using
    the identical text the board block prints: a ready/blocked/running/rejected
    key lists by state; an area with no open (ready or blocked) key renders
    "none open". A repo with no manifest yields no lines."""
    manifest = repo.get("manifest", [])
    by_area = {}
    for t in repo["tasks"]:
        if t.get("state") in ("ready", "blocked", "running", "rejected"):
            by_area.setdefault(t.get("area"), []).append(t)
    lines = []
    for row in manifest:
        area = row["area"]
        tasks = by_area.get(area, [])
        by_state = {}
        for t in tasks:
            by_state.setdefault(t["state"], []).append(t["key"])
        open_keys = by_state.get("ready", []) + by_state.get("blocked", [])
        if not open_keys:
            lines.append(f"Area: {area} — none open")
            continue
        segs = []
        for state in ("ready", "blocked", "running", "rejected"):
            keys = by_state.get(state, [])
            segs.append(f"{state}: {' '.join(sorted(keys)) if keys else 'none'}")
        lines.append(f"Area: {area} — " + " · ".join(segs))
    return lines


def render_board_block(graph):
    """The queue's next wave-1 keys and the plan(s) they come from, one line;
    "nothing queued" when every repo is settled. Below it, one derived
    "Area: <name>" section per manifest area, in manifest order, listing each
    area's ready/blocked/running/rejected keys — an area with no open (ready or
    blocked) key renders "none open". The board covers this tree only, so the
    single repo's name is omitted (the header says "this tree"), which keeps the
    block identical across clones that rename the directory."""
    parts = []
    for repo in graph["repos"]:
        ws = waves(repo)
        if not ws:
            continue
        wave_plans = sorted({t["plan"] for t in open_tasks(repo) if t["key"] in ws[0]})
        parts.append(f"{' '.join(ws[0])} ({' '.join(wave_plans)})")
    body = " · ".join(parts) if parts else "nothing queued"
    lines = [
        (
            "**Queued (derived from this tree; tasks whose dependencies run in "
            f"other repos, and in-flight state, are in the session brief).** {body}"
        )
    ]
    for repo in graph["repos"]:
        lines.extend(render_area_lines(repo))
    lines.append(render_open_bugs(graph.get("bugs", [])))
    return "\n".join(lines) + "\n"


def _splice_board(text, content):
    """Return the text with the marked block replaced by `content`, or None
    when either marker is missing (or in the wrong order)."""
    ib = text.find(BEGIN)
    ie = text.find(END)
    if ib < 0 or ie < 0 or ie < ib:
        return None
    return text[:ib] + BEGIN + "\n" + content + END + text[ie + len(END) :]


def write_board(path, graph):
    """Replace the marked block; True when the file changed, False when already
    current. Missing markers raise SystemExit(1)."""
    path = pathlib.Path(path)
    text = path.read_text()
    new = _splice_board(text, render_board_block(graph))
    if new is None:
        print(f"tasks: {path} is missing the {BEGIN} … {END} markers", file=sys.stderr)
        raise SystemExit(1)
    if new == text:
        return False
    path.write_text(new)
    return True


def board_drift(path, graph):
    """None when the marked block is current, else a unified diff of the drift."""
    path = pathlib.Path(path)
    text = path.read_text()
    new = _splice_board(text, render_board_block(graph))
    if new is None:
        return f"{path}: board block markers missing\n"
    if new == text:
        return None
    return "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def _stale_after_default():
    """The `--stale-after` default, parsed defensively: a malformed
    TASKS_STALE_AFTER falls back to DEFAULT_STALE_AFTER with a one-line warning
    instead of crashing every subcommand while the parser is built."""
    raw = os.environ.get("TASKS_STALE_AFTER")
    if raw is None:
        return DEFAULT_STALE_AFTER
    try:
        return int(raw)
    except (TypeError, ValueError):
        print(
            f"tasks: TASKS_STALE_AFTER={raw!r} is not an integer; "
            f"using {DEFAULT_STALE_AFTER}",
            file=sys.stderr,
        )
        return DEFAULT_STALE_AFTER


def plan_headings(path):
    """`{key: the verbatim ``### `` line}` for every typed heading of a plan
    file that is **outside** a fenced block — the fence rule `parse_plan`
    applies, so a heading quoted inside a ``` example never supplies a key's
    heading (the corpus: 538 lines match `HEADING_RE`, 8 of them fenced)."""
    out = {}
    in_fence = False
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            out.setdefault(m["key"], line)
    return out


def _first_gates(gates):
    """`({key: the chosen first-round gate row}, invalid)` for C-OUTCOMES's
    join: `round_kind == "first"` and `key == chain_root`; per key the earliest
    dated row by `review_commit_ts`, else the undated row with the lexically
    smallest `review_path`. `invalid` counts the `gate-verdict` rows `streams`
    refuses — skipped, never a crash."""
    pools, invalid = {}, 0
    for g in gates:
        if g.get("kind") != "gate-verdict":
            continue
        if streams.validate("gate-verdict", g):
            invalid += 1
            continue
        if g.get("round_kind") != "first" or g.get("key") != g.get("chain_root"):
            continue
        if any(g.get(f) is None for f in ("key", "review_path", "verdict")):
            invalid += 1
            continue
        pools.setdefault(g["key"], []).append(g)
    chosen = {}
    for key, rows in pools.items():
        dated = [r for r in rows if r.get("review_commit_ts")]
        chosen[key] = min(
            dated or rows,
            key=lambda r: (r.get("review_commit_ts") or "", r["review_path"]),
        )
    return chosen, invalid


def outcomes_rows(repo_root, gates):
    """C-OUTCOMES's rows: one per typed task that is its own `chain_root`, over
    every typed plan under `<repo_root>/docs/superpowers/plans`, joined to its
    first-round gate row; ten fields, sorted by `(plan, key)`."""
    chosen, _invalid = _first_gates(gates)
    rows = []
    for path in sorted(
        glob.glob(os.path.join(repo_root, "docs", "superpowers", "plans", "*.md"))
    ):
        plan = parse_plan(path)
        if not plan["typed"]:
            continue
        headings = plan_headings(path)
        for t in plan["tasks"]:
            if chain_root(t["key"]) != t["key"]:
                continue
            g = chosen.get(t["key"])
            rows.append(
                {
                    "key": t["key"],
                    "plan": plan["file"],
                    "heading": headings.get(t["key"], ""),
                    "kind": t["kind"],
                    "size": t["size"],
                    "touches_n": len(t["touches"]),
                    "verdict": g["verdict"] if g else None,
                    "plan_defect": g.get("plan_defect") if g else None,
                    "review_path": g["review_path"] if g else None,
                    "gate_ts": g.get("review_commit_ts") if g else None,
                }
            )
    rows.sort(key=lambda r: (r["plan"], r["key"]))
    return rows


def write_outcomes(root, store, out):
    """Write C-OUTCOMES's ledger and print its one line; the exit code."""
    import evidence

    path = evidence.stream_path(store, "derived/gates")
    if not os.access(path, os.R_OK):
        print(f"tasks: outcomes: cannot read {path}", file=sys.stderr)
        return 2
    gates = evidence.read(store, "derived/gates")
    rows = outcomes_rows(root, gates)
    if not rows:
        print(f"tasks: outcomes: no typed plan under {root}", file=sys.stderr)
        return 1
    chosen, invalid = _first_gates(gates)
    keys = {r["key"] for r in rows}
    verdicts = sum(1 for r in rows if r["verdict"] is not None)
    undated = sum(1 for r in rows if r["verdict"] is not None and r["gate_ts"] is None)
    unmatched = sum(1 for k in chosen if k not in keys) + invalid
    text = "".join(
        json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows
    )
    tmp = f"{out}.tmp.{os.getpid()}"
    try:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(tmp, "w") as fh:
            fh.write(text)
        os.replace(tmp, out)
    except OSError:
        print(f"tasks: outcomes: cannot write {out}", file=sys.stderr)
        return 2
    print(
        f"outcomes: {out} rows={len(rows)} verdict={verdicts} "
        f"null={len(rows) - verdicts} undated={undated} unmatched-gates={unmatched}"
    )
    return 0


def main(argv=None):
    import evidence

    parser = argparse.ArgumentParser(prog="tasks")
    parser.add_argument("--root", default=".")
    parser.add_argument("--repos", default=None)
    parser.add_argument("--plan-status", default=None)
    parser.add_argument("--runs-dir", default=DEFAULT_RUNS_DIR)
    parser.add_argument(
        "--stale-after",
        type=int,
        default=_stale_after_default(),
    )
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    )
    parser.add_argument("--claims", default=None)
    parser.add_argument("--today", type=datetime.date.fromisoformat, default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("brief").add_argument(
        "--today", type=datetime.date.fromisoformat, default=argparse.SUPPRESS
    )
    sub.add_parser("json")
    waves_p = sub.add_parser("waves")
    waves_p.add_argument("--repo", required=True)
    waves_p.add_argument("--plan")
    waves_p.add_argument("--factory-args", action="store_true")
    waves_p.add_argument("--key")
    waves_p.add_argument("--next", action="store_true")
    waves_p.add_argument("--json", action="store_true")
    conflicts_p = sub.add_parser("conflicts")
    conflicts_p.add_argument("--repo")
    check_p = sub.add_parser("check")
    check_p.add_argument("--board", default=None)
    check_p.add_argument("--draft", default=None)
    write_board_p = sub.add_parser("write-board")
    write_board_p.add_argument("--board", default="docs/OPERATIONS.md")
    write_board_p.add_argument("--quiet", action="store_true")
    write_board_p.add_argument(
        "--refuse-stale",
        action="store_true",
        help="exit 1 on a stale board outside a factory workspace; inside one "
        "(a .factory-meta marker at --root) leave the board's bytes alone",
    )
    touches_p = sub.add_parser("touches")
    touches_p.add_argument("plan")
    touches_p.add_argument("key")
    probes_p = sub.add_parser("probes")
    probes_p.add_argument("plan")
    probes_p.add_argument("key")
    area_p = sub.add_parser("area")
    area_p.add_argument("plan")
    area_p.add_argument("key")
    record_p = sub.add_parser("record")
    record_p.add_argument("--key", required=True)
    judged_p = sub.add_parser("judged")
    judged_p.add_argument("plan")
    judged_p.add_argument("--repo")
    outcomes_p = sub.add_parser("outcomes")
    outcomes_p.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    # The touches/probes/area subcommands read only the named plan file (area
    # adds the manifest under --root), so they run before any --root/repos.toml/
    # store resolution and from any cwd (the sandbox included).
    if args.command == "touches":
        return cmd_touches(args.plan, args.key)
    if args.command == "probes":
        return cmd_probes(args.plan, args.key)
    if args.command == "area":
        return cmd_area(args.root, args.plan, args.key)
    if args.command == "outcomes":
        out = args.out or os.path.join(
            args.root, "docs", "ledger", "plan-outcomes.jsonl"
        )
        return write_outcomes(args.root, args.store, out)

    repos_path = args.repos or os.path.join(args.root, "docs", "ledger", "repos.toml")
    status_path = args.plan_status or os.path.join(
        args.root, "docs", "ledger", "plan-status.toml"
    )
    claims_path = args.claims or os.path.join(
        args.root, "docs", "ledger", "claims.toml"
    )

    repos = load_repos(repos_path)
    repos = bind_root(repos, args.root)
    plan_status = load_plan_status(status_path)
    task_status_path = os.path.join(args.root, "docs", "ledger", "task-status.toml")
    task_status = load_task_status(task_status_path)
    # The valid `**repo:**` targets come from the ledger under `--root`, even when
    # the graph itself was scanned against a `--repos` override (the lint check
    # points this tree at itself with a one-repo file); see `check`.
    configured_repos = [
        r["name"]
        for r in load_repos(os.path.join(args.root, "docs", "ledger", "repos.toml"))
    ]
    graph = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "repos": [
            scan_repo(
                r,
                plan_status,
                args.runs_dir,
                args.store,
                repos=repos,
                task_status=task_status,
                stale_after=args.stale_after,
            )
            for r in repos
        ],
        "configured_repos": configured_repos,
        "runs_dir": args.runs_dir,
        "store": args.store,
        "task_status": task_status,
        "bugs": load_bugs(args.root),
    }

    if args.command == "record":
        return cmd_record(graph, args.key)

    if args.command == "judged":
        repos = [
            r for r in graph["repos"] if args.repo is None or r["name"] == args.repo
        ]
        if not any(t["plan"] == args.plan for r in repos for t in r["tasks"]):
            print(f"tasks: judged: no plan {args.plan}", file=sys.stderr)
            return 2
        rows = []
        for repo in repos:
            cache = {}
            for t in repo["tasks"]:
                if t["plan"] != args.plan or t.get("state") not in JUDGED_LINE_STATES:
                    continue
                state, reason = judged_state(repo["path"], t, cache)
                rows.append((t["key"], state, reason))
        for key, state, reason in sorted(rows):
            print(f"{key}\t{state}\t{reason}")
        return 0

    if args.command == "brief":
        claims = None
        if pathlib.Path(claims_path).exists():
            with open(claims_path, "rb") as fh:
                claims = tomllib.load(fh).get("claim", [])
        print(render_brief(graph, claims, today=args.today), end="")
        return 0

    if args.command == "json":
        print(json.dumps(json_graph(graph)))
        return 0

    if args.command == "waves":
        if args.factory_args and not args.plan:
            waves_p.print_usage(sys.stderr)
            return 2
        repo = next((r for r in graph["repos"] if r["name"] == args.repo), None)
        if repo is None:
            print(f"tasks: unknown repo {args.repo}", file=sys.stderr)
            return 1
        if args.factory_args:
            if args.key is not None and not any(
                t["plan"] == args.plan and t["key"] == args.key for t in repo["tasks"]
            ):
                print(
                    f"tasks: waves --key {args.key}: not in {args.plan}",
                    file=sys.stderr,
                )
                return 1
            print(json.dumps(factory_args(repo, args.plan, key=args.key)))
            return 0
        if args.json:
            print(json.dumps(wave_structure(repo, plan=args.plan)))
            return 0
        lines = wave_lines(repo, plan=args.plan)
        if args.next:
            if lines:
                print(lines[0])
            return 0
        for line in lines:
            print(line)
        return 0

    if args.command == "conflicts":
        repos = [
            r for r in graph["repos"] if args.repo is None or r["name"] == args.repo
        ]
        found = False
        for repo in repos:
            for c in conflicts(repo):
                found = True
                print(f"{repo['name']}: {conflict_line(c)}")
        if not found:
            print("none")
        return 0

    if args.command == "check":
        draft = None
        if args.draft:
            draft = load_draft(args.draft, args.root, repos, graph["repos"])
        # EV19: the probe-freshness warnings print to stderr but never turn
        # the exit non-zero — a stale bound is named, not fatal.
        warn = []
        errors = check(graph, warnings=warn)
        for w in warn:
            print(w, file=sys.stderr)
        if args.board:
            board = os.path.join(args.root, args.board)
            if board_drift(board, board_graph(args.root)) is not None:
                errors.append(
                    f"tasks: {args.board} queue block is stale — "
                    "run: evidence tasks write-board"
                )
            errors += integrated_refusals(graph)
        if draft is not None:
            repo = draft["scanned"]
            landed = draft["landed"]
            map_names = map_check_names(args.root)
            errors += draft["errors"]
            errors += draft_rules(draft, repo, map_names, landed)
            if not errors:
                print(
                    f"waves: {json.dumps(wave_structure(repo, plan=draft['plan_name']))}"
                )
                rows = [
                    c
                    for c in conflicts(repo)
                    if c["plan_a"] == draft["plan_name"]
                    or c["plan_b"] == draft["plan_name"]
                ]
                if not rows:
                    print("conflicts: none")
                else:
                    for c in rows:
                        print(f"conflicts: {conflict_line(c)}")
                return 0
        for e in errors:
            print(e, file=sys.stderr)
        return 1 if errors else 0

    if args.command == "write-board":
        board = (
            args.board
            if os.path.isabs(args.board)
            else os.path.join(args.root, args.board)
        )
        if args.refuse_stale:
            # BUG-hook-forces-board-into-seat-commit: staleness is a byte
            # question — did regenerating change the file — answered here,
            # where the block is written, never by git (the lint sandbox has
            # none). A factory workspace is marked by `.factory-meta` at the
            # --root this command was given (factory-ws writes it into every
            # seat workspace and git-excludes it; the operator's checkout has
            # none), resolved against --root, never the cwd. In one, the
            # board is the integrator's: restore the pre-call bytes, say one
            # line, exit 0, so a seat's commit can never carry the file.
            board_path = pathlib.Path(board)
            before = board_path.read_bytes()
            write_board(board, board_graph(args.root))
            if board_path.read_bytes() == before:
                return 0
            if (pathlib.Path(args.root) / ".factory-meta").exists():
                board_path.write_bytes(before)
                print(
                    f"tasks: {args.board} queue block was stale and was left "
                    "alone — this is a factory workspace; the integrator "
                    "regenerates the board",
                    file=sys.stderr,
                )
                return 0
            print(
                f"tasks: {args.board} queue block was stale and has been "
                f"regenerated — git add {args.board} and commit again",
                file=sys.stderr,
            )
            return 1
        write_board(board, board_graph(args.root))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
