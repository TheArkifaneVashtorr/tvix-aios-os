#!/usr/bin/env python3
"""tools/experiments/jaz/confined_tools.py -- the REPL-bound tool functions
arm C's drafter gets, in place of the shell-command/sub-agent recipe that
draft-byref.js's own prompt uses (see extract_draft_prompt.py). Stdlib
only, except duckdb_query's optional `import duckdb` (used only if it's
importable in the caller's env -- run_arm_c.py's own env carries it via
the jazLangPython package, per flake.nix).

Spec: docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md
§6b ("The tools"): "JAZ's REPL fails closed... The drafter's access to the
snapshot is therefore explicit callables bound as REPL variables:
read_file, grep, tasks_py, duckdb_query over the evidence snapshot, and
git_log. Each is confined to the fixture checkout, and every call is
logged as arm B's queries.log was."

Each function below refuses (rather than raising) a path that resolves
(via os.path.realpath) outside the fixture root, and appends one line to
"<scratch>/queries.log" per call: "<ts> <tool> <args> exit=<n>" -- a
refusal logs exit=1, same as any other failure, so a run's queries.log is
a complete audit trail regardless of outcome.

2026-09-27 Opus review additions:
  - `write_scratch(name, text)`: the drafter's own write access, confined
    to `scratch` (never the fixture, which stays read-only) and logged
    exactly like the read-side tools. `run_arm_c.py` no longer writes
    `draft-0.md` itself from `invoke()`'s return value -- the agent writes
    its own draft via this tool, and the return value goes to
    `scratch/return.json` instead (see run_arm_c.py's own note on why).
  - `duckdb_query` locks the connection down BEFORE running the caller's
    SQL: `allowed_directories=[<fixture>/evidence]`,
    `enable_external_access=false` (no `read_text`/`COPY TO` reaching
    anywhere else on disk), then `lock_configuration=true` (verified
    2026-09-27 against duckdb 1.5.5: a `SET` after `lock_configuration`
    raises `InvalidInputException`, and a `read_json`/`read_csv` outside
    `allowed_directories` raises `PermissionException` -- both confirmed
    against this env's actual duckdb before landing this comment).
  - `git_log` takes only flags on a small allowlist (read-only,
    non-path-taking inspection flags); anything else -- most pointedly
    `--output`/`-o`, which WRITE git's output to an arbitrary path on
    disk, a real escape from confinement -- is refused before `git` ever
    runs.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys


class PathRefused(Exception):
    pass


def _log(scratch: str, tool: str, argstr: str, exit_code: int) -> None:
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    line = f"{ts} {tool} {argstr} exit={exit_code}\n"
    with open(os.path.join(scratch, "queries.log"), "a", encoding="utf-8") as fh:
        fh.write(line)


def resolve_confined(fixture_root: str, path: str) -> str:
    """Return the realpath of `path` (resolved relative to `fixture_root`
    if not absolute), raising PathRefused if it resolves outside
    `fixture_root`."""
    root = os.path.realpath(fixture_root)
    candidate = path if os.path.isabs(path) else os.path.join(root, path)
    real = os.path.realpath(candidate)
    if real != root and not real.startswith(root + os.sep):
        raise PathRefused(
            f"confined_tools: {path!r} resolves outside the fixture root {fixture_root!r}"
        )
    return real


# The run's own bookkeeping files -- never the drafter's to overwrite via
# write_scratch, even though they all live under `scratch`. `trajectory/`
# is TrajectoryDirectoryRecorder's own tree, not a single file, hence the
# prefix check on the resolved path's first component rather than a name.
RESERVED_SCRATCH_NAMES = frozenset(
    {"queries.log", "stopped.json", "jaz.log", "return.json"}
)


def resolve_scratch(scratch: str, name: str) -> str:
    """Like `resolve_confined`, but rooted at `scratch` -- for the one tool
    that writes (`write_scratch`), never at `fixture_root`."""
    root = os.path.realpath(scratch)
    candidate = name if os.path.isabs(name) else os.path.join(root, name)
    real = os.path.realpath(candidate)
    if real != root and not real.startswith(root + os.sep):
        raise PathRefused(
            f"confined_tools: {name!r} resolves outside the scratch dir {scratch!r}"
        )
    return real


# git log flags this tool serves -- read-only inspection, nothing that
# writes anywhere, and pointedly NOT --output/-o (which write git's own
# output to an arbitrary path -- a real write-escape, not just a read
# one). A handful take a separate value as the NEXT argv entry (free
# text -- "last week", an author substring, ... -- never itself checked
# against the flag allowlist, since it isn't a flag).
GIT_LOG_ALLOWED_FLAGS = frozenset(
    {
        "--oneline",
        "--all",
        "--graph",
        "--stat",
        "--name-only",
        "--name-status",
        "--format",
        "--pretty",
        "-n",
        "--max-count",
        "--since",
        "--until",
        "--author",
        "--grep",
        "-p",
        "--patch",
        "--no-color",
        "--date",
        "--reverse",
        "--merges",
        "--no-merges",
        "--first-parent",
    }
)
GIT_LOG_VALUE_FLAGS = frozenset(
    {"-n", "--max-count", "--since", "--until", "--author", "--grep", "--date"}
)


def _git_log_flag_allowed(arg: str) -> bool:
    """True iff `arg` is exactly an allowed flag, or `--flag=value`'s flag
    half is allowed."""
    if not arg.startswith("-"):
        return False
    flag = arg.split("=", 1)[0]
    return flag in GIT_LOG_ALLOWED_FLAGS


def _parse_git_log_args(
    fixture_root: str, args: tuple
) -> tuple[list | None, str | None]:
    """Validate git_log's *args into the real argv tail. Handles a value-
    taking flag given as two separate argv entries (`-n 5`, not just
    `-n=5`) -- the value itself is free text, never flag-checked -- and
    `--` followed by one or more pathspecs, each individually confined via
    `resolve_confined` (so `git log -- ../../etc/passwd` is refused the
    same way read_file's escape is). Returns (argv, None) on success or
    (None, reason) on refusal; never raises."""
    argv: list = []
    i = 0
    n = len(args)
    while i < n:
        arg = args[i]
        if arg == "--":
            argv.append(arg)
            for path in args[i + 1 :]:
                try:
                    resolve_confined(fixture_root, path)
                except PathRefused as exc:
                    return None, str(exc)
                argv.append(path)
            return argv, None
        if not _git_log_flag_allowed(arg):
            return None, f"confined_tools: git_log flag not on the allowlist: {arg!r}"
        argv.append(arg)
        flag = arg.split("=", 1)[0]
        if flag in GIT_LOG_VALUE_FLAGS and "=" not in arg:
            if i + 1 >= n:
                return None, f"confined_tools: git_log flag {arg!r} needs a value"
            argv.append(args[i + 1])
            i += 2
            continue
        i += 1
    return argv, None


def make_tools(fixture_root: str, scratch: str) -> dict:
    """Return the dict of REPL-bound callables for one run: read_file,
    list_dir, grep, tasks_py, duckdb_query, git_log, write_scratch --
    each confined to `fixture_root` (or, for write_scratch, `scratch`),
    each logging to `<scratch>/queries.log`."""

    def read_file(path: str) -> str:
        try:
            real = resolve_confined(fixture_root, path)
        except PathRefused as exc:
            _log(scratch, "read_file", repr(path), 1)
            return f"REFUSED: {exc}"
        try:
            with open(real, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            _log(scratch, "read_file", repr(path), 1)
            return f"ERROR: {exc}"
        _log(scratch, "read_file", repr(path), 0)
        return text

    def list_dir(path: str = ".") -> object:
        try:
            real = resolve_confined(fixture_root, path)
        except PathRefused as exc:
            _log(scratch, "list_dir", repr(path), 1)
            return f"REFUSED: {exc}"
        try:
            entries = sorted(os.listdir(real))
        except OSError as exc:
            _log(scratch, "list_dir", repr(path), 1)
            return f"ERROR: {exc}"
        _log(scratch, "list_dir", repr(path), 0)
        return entries

    def grep(pattern: str, path: str = ".") -> str:
        try:
            real = resolve_confined(fixture_root, path)
        except PathRefused as exc:
            _log(scratch, "grep", f"{pattern!r} {path!r}", 1)
            return f"REFUSED: {exc}"
        proc = subprocess.run(
            ["grep", "-rn", "--", pattern, real],
            capture_output=True,
            text=True,
            check=False,
        )
        _log(scratch, "grep", f"{pattern!r} {path!r}", proc.returncode)
        return proc.stdout

    def tasks_py(*args: str) -> str:
        try:
            real_root = resolve_confined(fixture_root, ".")
        except PathRefused as exc:
            _log(scratch, "tasks_py", " ".join(args), 1)
            return f"REFUSED: {exc}"
        script = os.path.join(real_root, "pkgs", "evidence", "tasks.py")
        proc = subprocess.run(
            ["python3", script, "--root", real_root, *args],
            capture_output=True,
            text=True,
            check=False,
        )
        _log(scratch, "tasks_py", " ".join(args), proc.returncode)
        return proc.stdout + proc.stderr

    def duckdb_query(sql: str) -> object:
        try:
            evidence_dir = resolve_confined(fixture_root, "evidence")
        except PathRefused as exc:
            _log(scratch, "duckdb_query", sql, 1)
            return f"REFUSED: {exc}"
        try:
            import duckdb  # local import: optional at module load, required here
        except ImportError:
            _log(scratch, "duckdb_query", sql, 1)
            return "REFUSED: duckdb is not importable in this environment"
        con = duckdb.connect(":memory:")
        try:
            # Locked down BEFORE the caller's SQL ever runs, and locked in
            # this exact order: allowed_directories + external access off
            # first, lock_configuration LAST (once locked, no further SET
            # -- including re-widening these two -- is possible). Verified
            # against this env's real duckdb (2026-09-27): a read outside
            # allowed_directories raises PermissionException; a SET after
            # the lock raises InvalidInputException.
            safe_dir = evidence_dir.replace("'", "''")
            con.execute(f"SET allowed_directories=['{safe_dir}']")
            con.execute("SET enable_external_access=false")
            con.execute("SET file_search_path=?", [evidence_dir])
            con.execute("SET lock_configuration=true")
            rows = con.execute(sql).fetchall()
        except Exception as exc:  # duckdb raises its own exception types
            _log(scratch, "duckdb_query", sql, 1)
            return f"ERROR: {exc}"
        finally:
            con.close()
        _log(scratch, "duckdb_query", sql, 0)
        return rows

    def git_log(*args: str) -> str:
        argv, err = _parse_git_log_args(fixture_root, args)
        if err is not None:
            _log(scratch, "git_log", " ".join(args), 1)
            return f"REFUSED: {err}"
        try:
            real_root = resolve_confined(fixture_root, ".")
        except PathRefused as exc:
            _log(scratch, "git_log", " ".join(args), 1)
            return f"REFUSED: {exc}"
        proc = subprocess.run(
            ["git", "-C", real_root, "log", *argv],
            capture_output=True,
            text=True,
            check=False,
        )
        _log(scratch, "git_log", " ".join(args), proc.returncode)
        return proc.stdout

    def write_scratch(name: str, text: str) -> str:
        try:
            real = resolve_scratch(scratch, name)
        except PathRefused as exc:
            _log(scratch, "write_scratch", repr(name), 1)
            return f"REFUSED: {exc}"
        rel = os.path.relpath(real, os.path.realpath(scratch))
        rel_head = rel.split(os.sep, 1)[0]
        if rel in RESERVED_SCRATCH_NAMES or rel_head == "trajectory":
            _log(scratch, "write_scratch", repr(name), 1)
            return f"REFUSED: confined_tools: write_scratch may not write {rel!r} (reserved for the run's own bookkeeping)"
        try:
            os.makedirs(os.path.dirname(real), exist_ok=True)
            with open(real, "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as exc:
            _log(scratch, "write_scratch", repr(name), 1)
            return f"ERROR: {exc}"
        _log(scratch, "write_scratch", repr(name), 0)
        return f"wrote {len(text)} bytes to {name}"

    return {
        "read_file": read_file,
        "list_dir": list_dir,
        "grep": grep,
        "tasks_py": tasks_py,
        "duckdb_query": duckdb_query,
        "git_log": git_log,
        "write_scratch": write_scratch,
    }


if __name__ == "__main__":
    # A tiny manual smoke: `python3 confined_tools.py <fixture_root> <scratch>`
    # exercises read_file/list_dir/grep against the given fixture and prints
    # the tail of queries.log -- never run by the bats suite, useful by hand.
    if len(sys.argv) != 3:
        print("usage: confined_tools.py <fixture_root> <scratch>", file=sys.stderr)
        raise SystemExit(2)
    tools = make_tools(sys.argv[1], sys.argv[2])
    print(tools["list_dir"]("."))
    print(tools["read_file"]("/etc/passwd"))
