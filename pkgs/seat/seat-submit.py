"""Operator/orchestrator CLI for the seat lane (plan 2026-09-05-seat-behind-broker,
SB3): writes a job directory for `seat-run` (SB1's unit entry) and starts the
unit that runs it, or -- in headless mode -- polls for that unit's result and
streams it back.

    seat-submit [--jobs-dir DIR] [--no-start] [--wait] [--spool-dir DIR]
        {headless|web|drive} --workspace PATH --dsh-home PATH --model ID
        --effort LEVEL [--brief FILE] [--task <run>/<key>] [--port N]
        [--timeout S]

Writes /var/lib/seat/jobs/<id>/ (0700, owner = invoking user), where <id> is
`YYYYmmdd-HHMMSS-<6 hex>`, containing job.json and, when --brief is given, the
brief copied to brief.txt. Prints the job id. Unless --no-start, runs
`systemctl start seat@<id>` (check=False, as lane-submit.py does) and -- for
headless mode -- waits (poll every 2 s, up to --timeout default 10800 s) until
the unit's result.txt appears, then copies stdout.txt to its own stdout and
exits with the code in exit_code.txt. When result.txt appears without a
stdout.txt (seat-spool refuses a capped job by writing only result.txt) it is
emitted instead -- carrying the reason -- and the exit is 1, never 0. The wait
is bound by min(--timeout, SEAT_POLL_TIMEOUT) when the env var is a positive
number. If the unit ends before result.txt
appears (ActiveState failed/inactive with a non-success Result), seat-submit
dumps the unit's journalctl tail to stderr and exits 4 at once, not after the
timeout. If --timeout expires first, the unit is stopped (`systemctl stop`)
and the exit code is 124. Refuses a --workspace that is not a directory or a
--brief that is unreadable (exit 2).

The running-unit cap (IS1, decision 72a; corrected in IS1c) is enforced only on
the started path, right before `systemctl start`: reads the cap from
SEAT_MAX_UNITS (tests), else /etc/seat-lane/max-units, else 5, counts
`systemctl list-units 'seat@*' --state=active,activating`, and -- failing
closed when the cap is malformed, when systemctl is absent or exits non-zero
(`cannot count seat units`), or when the count has reached the cap
(`<n> seat units running, cap <max>`) -- exits 3. The --no-start path never
counts and never refuses: it is not the actor that starts the unit, and inside
a seat@ unit systemctl is denied by design, so a count there would refuse every
seat-dispatched task. Exit 3 is reserved for the running-unit cap alone: the
`_poll` "ended without a result" path exits 4, so a caller can always tell
"cap full, retry later" from "the started unit produced no result".

--no-start (SD6) spools instead of starting: it writes an empty 0600 marker at
<--spool-dir>/<id> (the default spool dir is the sibling of --jobs-dir, e.g.
/var/lib/seat/spool) and returns -- seat-spool.path starts the unit, never
seat-submit via systemctl. --wait (headless, with --no-start) polls result.txt
and streams stdout.txt exactly as the started path does, but never calls
systemctl: on timeout it exits 124 and names the still-running seat@<id>
instead of stopping it. --wait without --no-start, or with a web job, is exit
2 (usage).

OC9: an optional --task <run>/<key> is recorded as `task` in job.json (null
when absent) and validated whole -- each half [A-Za-z0-9][A-Za-z0-9_-]{0,31},
the broker's FACTORY_TASK_RE shape -- before the job directory is created; a
refusal exits 2 with `--task must be <run>/<key>`. The unit exports the label
as SEAT_TASK (seat-run) and the wrapper sends it to the broker as the
x-factory-task header; outside the broker it never leaves the machine.

PT3 (plan 2026-09-22-planning-patterns): the allow-listed environment
(SEAT_JOB_ENV) a submitting shell carries is validated before the job
directory exists and recorded as `env` in job.json (`{}` when none);
seat-run exports exactly these names; `--help` lists them.

After result.txt appears, `_poll` streams stdout.txt and -- when that stream
lacks a FACTORY-RESULT line (seat-spool's refusal writes result.txt alone, no
stdout.txt) -- emits result.txt to stdout, so the reason reaches factory-task
instead of being synthesised generically. The exit code is exit_code.txt's
value when present, else 1 when result.txt carries `status=failed`, else 0.
The effective poll timeout on both the started and the --wait paths is
min(--timeout, SEAT_POLL_TIMEOUT) when SEAT_POLL_TIMEOUT is a positive number;
unset, --timeout alone rules; a malformed value exits 2 with
`seat-submit: SEAT_POLL_TIMEOUT=<raw> is not a positive number` and never
starts the wait.

SA3 (decision 13b): a web/drive seat's port is allocated by seat-spool, so
`--port` is a request, not a claim (optional for both web and drive; when given
it must be an int 1024-65535, and an unset port writes `port: null` into
job.json). For web/drive the started path spools the job (writes the marker)
and waits -- under the same `_poll_timeout` bound -- for `.spooled` (the spool
allocated a port and started the unit) or `result.txt` (the spool refused),
then prints `port=<n>` from the rewritten job.json on the second stdout line
(the first stays the job id), or emits the refusal and exits 1. The running-unit
cap check below applies to the headless started path alone: web/drive never
start a unit directly, so the spool (IS1c) is their enforcer.

The unit (SB1's seat-run.py) writes stdout.txt, stderr.txt, exit_code.txt and
result.txt into the job directory; the --jobs-dir default is /var/lib/seat/jobs
(tests pass a tmp dir and --no-start).
"""

import argparse
import datetime
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time

DEFAULT_JOBS_DIR = "/var/lib/seat/jobs"
DEFAULT_TIMEOUT = 10800
POLL_INTERVAL = 2

# OC9 (2026-09-21): the task address (<run>/<key>) a submitted job carries
# through to the unit (SEAT_TASK) and, behind the broker, the x-factory-task
# request header. The shape is the broker's FACTORY_TASK_RE (OC5,
# pkgs/broker/policy.py) -- each half the evidence store's KEY_RE with the
# same length bound -- so both ends of the pipe refuse the same values. The
# address is validated as ONE value, never split: "ocw3/../OC9" is refused
# whole (D9), not half-accepted.
TASK_RE = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9_-]{0,31})/([A-Za-z0-9][A-Za-z0-9_-]{0,31})$"
)

# PT3 (plan 2026-09-22-planning-patterns): the job's environment allow-list --
# the named variables a submitting shell may carry through the unit boundary
# (`systemctl start` keeps none of the caller's environment). The same tuple is
# defined in seat-run.py, which exports exactly these names; a test asserts the
# two are equal. One name per line, each with a validator below.
SEAT_JOB_ENV = ("OPENROUTER_CONTEXT_WINDOW",)

# Per allow-listed name: the value that is accepted, and the reason printed on a
# refusal. The window's rule is the wrapper's own (dsh-openrouter.sh dies 5 on a
# non-integer), tightened to refuse 0 and a leading zero -- neither is a usable
# window and both would reach the harness unremarked.
SEAT_JOB_ENV_RULES = {
    "OPENROUTER_CONTEXT_WINDOW": (
        re.compile(r"^[1-9][0-9]*$"),
        "must be a positive integer",
    ),
}


def job_env(environ):
    """(the allow-listed names present in `environ`, None) or (None, the
    refusal). Every name is validated before the job directory exists."""
    env = {}
    for name in SEAT_JOB_ENV:
        value = environ.get(name)
        if value is None:
            continue
        pattern, reason = SEAT_JOB_ENV_RULES[name]
        # PT3 [tester]: fullmatch, never match -- `$` also matches before a
        # trailing newline, and "1048576\n" is a value the wrapper then dies 5
        # on, after the job has been paid for.
        if not pattern.fullmatch(value):
            return None, f"seat-submit: {name} {reason}"
        env[name] = value
    return env, None


# IS1 (decision 72a): the running-unit cap -- read from SEAT_MAX_UNITS (tests),
# else the file the seatLane module writes, else 5. The file is the only runtime
# source on a live host besides the test override.
MAX_UNITS_FILE = "/etc/seat-lane/max-units"
DEFAULT_MAX_UNITS = 5

# SD7: the driver's skill set a `drive` --dsh-home must carry (files, or
# symlinks to files -- os.path.isfile follows a symlink), in report order.
DRIVE_SKILLS = (
    "skills/driving/SKILL.md",
    "skills/planning/SKILL.md",
    "AGENTS.md",
)


def _missing_drive_skill(dsh_home):
    """The first entry of DRIVE_SKILLS missing from `dsh_home`, or None when
    all three are present (as files or symlinks to files)."""
    for rel in DRIVE_SKILLS:
        if not os.path.isfile(os.path.join(dsh_home, rel)):
            return rel
    return None


def _unit_state(job_id):
    """(ActiveState, Result) of seat@<id>, or ("unknown", "") when systemctl
    cannot be read -- never an exception, never a false early exit."""
    try:
        proc = subprocess.run(
            [
                "systemctl",
                "show",
                f"seat@{job_id}",
                "-p",
                "ActiveState",
                "-p",
                "Result",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return "unknown", ""
    if proc.returncode != 0:
        return "unknown", ""
    props = dict(
        line.split("=", 1) for line in (proc.stdout or "").splitlines() if "=" in line
    )
    return props.get("ActiveState", "unknown").strip(), props.get("Result", "").strip()


def _max_units_cap():
    """(cap, error) of the running-unit cap. cap is the parsed integer when the
    configuration is readable; error is a non-None reason string when a cap the
    operator DID configure is malformed (a non-numeric or empty SEAT_MAX_UNITS,
    or a malformed /etc/seat-lane/max-units) -- the caller fails closed on it,
    never silently reverting to the default 5."""
    env = os.environ.get("SEAT_MAX_UNITS")
    if env is not None:
        raw = env.strip()
        if raw == "":
            return None, "cannot read the seat cap (SEAT_MAX_UNITS is set but empty)"
        try:
            return int(raw), None
        except ValueError:
            return None, (
                f"cannot read the seat cap (SEAT_MAX_UNITS={raw!r} is not a number)"
            )
    try:
        with open(MAX_UNITS_FILE, encoding="utf-8") as f:
            raw = f.read().strip()
    except OSError:
        # No runtime cap configured (the seatLane module writes the file on a
        # live host): the module's default applies.
        return DEFAULT_MAX_UNITS, None
    if raw == "":
        return None, f"cannot read the seat cap ({MAX_UNITS_FILE} is empty)"
    try:
        return int(raw), None
    except ValueError:
        return None, (
            f"cannot read the seat cap ({MAX_UNITS_FILE} holds {raw!r}, not a number)"
        )


def _seat_unit_count():
    """(count, error) of active/activating seat@* units. error is a non-None
    reason string when systemctl is absent from PATH or exits non-zero -- the
    caller fails closed on it rather than risk a third wave / hand launch."""
    try:
        proc = subprocess.run(
            [
                "systemctl",
                "list-units",
                "seat@*",
                "--state=active,activating",
                "--plain",
                "--no-legend",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError) as e:
        return None, str(e)
    if proc.returncode != 0:
        return None, f"systemctl list-units exited {proc.returncode}"
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    return len(lines), None


def _poll_timeout(cli_timeout):
    """(timeout, error) of the poll deadline. timeout = min(cli_timeout,
    SEAT_POLL_TIMEOUT) when the env var is a positive number, else cli_timeout
    alone; error is a non-None message when SEAT_POLL_TIMEOUT is set but not a
    positive number -- the caller fails with exit 2 before any wait, never
    silently ignoring the misconfiguration."""
    raw = os.environ.get("SEAT_POLL_TIMEOUT")
    if raw is None:
        return cli_timeout, None
    try:
        value = float(raw)
    except ValueError:
        return None, f"SEAT_POLL_TIMEOUT={raw} is not a positive number"
    if value <= 0:
        return None, f"SEAT_POLL_TIMEOUT={raw} is not a positive number"
    return min(cli_timeout, value), None


def _poll(job_dir, job_id, timeout, started):
    """Wait for result.txt, stream stdout.txt, and exit with exit_code.txt.
    started=True: this process started the unit, so probe its state (end early
    on failure) and stop it on timeout. started=False (--no-start --wait): the
    spool unit owns the instance -- never call systemctl."""
    result_path = os.path.join(job_dir, "result.txt")
    deadline = time.time() + timeout
    while not os.path.exists(result_path):
        if started:
            # SB6b: end the wait at once when the unit itself has failed or
            # already become inactive without producing a result -- the
            # result.txt will never appear, so waiting out the timeout would
            # only stall the caller. `inactive` with `Result=success` and no
            # result.txt keeps polling (the timeout still owns that race).
            state, result = _unit_state(job_id)
            if state in ("inactive", "failed") and result not in ("", "success"):
                print(
                    f"seat-submit: seat@{job_id} ended without a result: "
                    f"ActiveState={state} Result={result}",
                    file=sys.stderr,
                )
                journal = subprocess.run(
                    ["journalctl", "-u", f"seat@{job_id}", "-n", "10", "--no-pager"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                sys.stderr.write(journal.stdout)
                # Exit 3 is reserved for the running-unit cap alone (IS1): an
                # ended-without-a-result wait is a distinct failure, so it exits
                # 4 to keep "cap full, retry later" inseparable from "the unit
                # produced no result". The cap's two refusal arms exit 3.
                return 4
        if time.time() >= deadline:
            if started:
                # A timed-out headless job must not be orphaned: stop the unit
                # and report 124 (the conventional timeout exit) so the caller
                # can tell a timeout apart from a task that merely failed.
                print(
                    f"seat-submit: timed out waiting for {result_path}",
                    file=sys.stderr,
                )
                subprocess.run(["systemctl", "stop", f"seat@{job_id}"], check=False)
            else:
                # --no-start --wait: the spool unit owns the instance, so the
                # caller must not stop it -- name it for the operator instead.
                print(
                    f"seat-submit: timed out waiting for {result_path}; "
                    f"seat@{job_id} may still be running — stop it with: "
                    f"systemctl stop seat@{job_id}",
                    file=sys.stderr,
                )
            return 124
        time.sleep(POLL_INTERVAL)

    stdout_path = os.path.join(job_dir, "stdout.txt")
    streamed = ""
    if os.path.exists(stdout_path):
        with open(stdout_path, encoding="utf-8") as f:
            streamed = f.read()
        sys.stdout.write(streamed)

    # IS1c minor 1: seat-spool refuses a capped job by writing only result.txt
    # (FACTORY-RESULT status=failed and the reason line) and never starting the
    # unit, so no stdout.txt or exit_code.txt exists. Emit result.txt here so
    # the reason reaches factory-task, exactly once -- seat-run already ends
    # stdout.txt with the same block, so never double it, and a bare result.txt
    # without a FACTORY-RESULT label is not a result to surface.
    result_text = ""
    if os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as f:
            result_text = f.read()
    if "FACTORY-RESULT" in result_text and "FACTORY-RESULT" not in streamed:
        sys.stdout.write(result_text)

    exit_code = 0
    exit_path = os.path.join(job_dir, "exit_code.txt")
    if os.path.exists(exit_path):
        with open(exit_path, encoding="utf-8") as f:
            raw = f.read().strip()
        try:
            exit_code = int(raw)
        except ValueError:
            exit_code = 0
    elif "status=failed" in result_text:
        # A refused job (no exit_code.txt, result.txt carrying status=failed)
        # exits 1, never 0 -- so factory-task reports the refusal, not success.
        exit_code = 1
    return exit_code


def _spool_marker(spool_dir, job_id):
    """Write the empty 0600 marker seat-spool.path watches. Returns (rc, msg):
    rc 0 on success, 2 with a message on failure -- a collision is a clean exit
    2 (O_CREAT|O_EXCL), never a silent overwrite of a marker about to be consumed."""
    try:
        os.makedirs(spool_dir, exist_ok=True)
    except OSError as e:
        return 2, f"seat-submit: could not create spool directory {spool_dir}: {e}"
    marker = os.path.join(spool_dir, job_id)
    try:
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except OSError as e:
        return 2, f"seat-submit: could not spool {job_id}: {e}"
    return 0, None


def _await_spooled(job_dir, timeout):
    """Wait, bounded by `timeout`, for the spool to allocate the job's port and
    start the unit (.spooled) or refuse it (result.txt). On .spooled, re-read
    job.json and print `port=<n>` on a second stdout line (SA3, decision 13b).
    On a refusal, emit result.txt -- carrying the spool's reason -- and exit 1
    (SA2's refusal path). On timeout (the spool has not yet run) exit 124."""
    spooled_path = os.path.join(job_dir, ".spooled")
    result_path = os.path.join(job_dir, "result.txt")
    deadline = time.time() + timeout
    while not os.path.exists(spooled_path) and not os.path.exists(result_path):
        if time.time() >= deadline:
            print(
                f"seat-submit: timed out waiting for {spooled_path}",
                file=sys.stderr,
            )
            return 124
        time.sleep(POLL_INTERVAL)
    if os.path.exists(result_path):
        # The spool refused the job (held port, no free port, cap): emit its
        # reason so the caller sees it, and exit 1, never 0.
        with open(result_path, encoding="utf-8") as f:
            result_text = f.read()
        sys.stdout.write(result_text)
        return 1
    # .spooled: the spool allocated the port and started the unit; job.json now
    # carries the allocated port.
    with open(os.path.join(job_dir, "job.json"), encoding="utf-8") as f:
        job = json.load(f)
    print(f"port={job['port']}")
    return 0


def cmd_submit(argv):
    p = argparse.ArgumentParser(
        prog="seat-submit",
        epilog=(
            "environment allow-list (recorded into job.json, exported by "
            "seat-run): " + ", ".join(SEAT_JOB_ENV)
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--jobs-dir", default=DEFAULT_JOBS_DIR)
    p.add_argument("--no-start", action="store_true")
    p.add_argument("--wait", action="store_true")
    p.add_argument("--spool-dir", default=None)
    p.add_argument("mode", choices=["headless", "web", "drive"])
    p.add_argument("--workspace", required=True)
    p.add_argument("--dsh-home", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--effort", required=True)
    p.add_argument("--task")
    p.add_argument("--brief")
    p.add_argument("--port", type=int)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = p.parse_args(argv)

    # The spool is the sibling of the jobs dir (module tmpfiles creates it on
    # the host; seat-submit just needs the marker path, and creates the dir
    # idempotently so a standalone/tmp --jobs-dir works too).
    if args.spool_dir is None:
        args.spool_dir = os.path.join(
            os.path.dirname(os.path.abspath(args.jobs_dir)), "spool"
        )

    # --wait is only meaningful for a spooled headless job: it polls result.txt
    # exactly as the started path does but must never touch systemctl, so it is
    # refused without --no-start or with a web job.
    if args.wait and (not args.no_start or args.mode != "headless"):
        print(
            "seat-submit: --wait requires --no-start and mode headless",
            file=sys.stderr,
        )
        return 2

    # SD7 (the drive job mode): drive is the web command plus a routed model,
    # refuses the headless brief, and requires the driver's skill set in
    # --dsh-home -- the isolated home is seeded by the caller (seat-drive.sh),
    # never from the operator's shared one (nothing automated inherits the
    # saved selection, addendum rule 1). SA3 (decision 13b): --port is optional
    # (the spool allocates it); when given it must still be an int 1024-65535.
    if args.mode == "drive":
        if args.port is not None and not (1024 <= args.port <= 65535):
            print("seat-submit: --port must be 1024-65535", file=sys.stderr)
            return 2
        if args.brief is not None:
            print("seat-submit: drive refuses --brief", file=sys.stderr)
            return 2
        missing = _missing_drive_skill(args.dsh_home)
        if missing is not None:
            print(
                f"seat-submit: --dsh-home {args.dsh_home} lacks {missing} — "
                "the driver's skill set "
                "(ln -s ~/flakes/dsh-harness/skills <dsh-home>/skills)",
                file=sys.stderr,
            )
            return 2

    if not os.path.isdir(args.workspace):
        print(
            f"seat-submit: --workspace {args.workspace} is not a directory",
            file=sys.stderr,
        )
        return 2
    if args.brief is not None and not os.access(args.brief, os.R_OK):
        print(f"seat-submit: --brief {args.brief} is not readable", file=sys.stderr)
        return 2

    # OC9: --task is validated whole BEFORE the job directory is created, so
    # a refused submit leaves nothing behind for the spool to start. Every
    # mode accepts the label; the unit exports it (seat-run) and the wrapper
    # sends it to the broker (x-factory-task) -- outside the broker the label
    # never leaves the machine, so it is optional and never fatal to omit.
    if args.task is not None and not TASK_RE.match(args.task):
        print("seat-submit: --task must be <run>/<key>", file=sys.stderr)
        return 2

    # PT3: the allow-listed environment is validated whole BEFORE the job
    # directory is created, the shape --task uses (OC9): a refused submit
    # leaves nothing behind for the spool to start.
    env, env_err = job_env(os.environ)
    if env_err is not None:
        print(env_err, file=sys.stderr)
        return 2

    now = datetime.datetime.now(datetime.timezone.utc)
    job_id = now.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    job_dir = os.path.join(args.jobs_dir, job_id)
    try:
        os.makedirs(job_dir, mode=0o700, exist_ok=False)
        # The unit later writes its results back into this directory; it stays
        # private to the invoking user (the operator, who also owns the unit).
        os.chmod(job_dir, 0o700)
    except OSError as e:
        print(
            f"seat-submit: could not create job directory {job_dir}: {e}",
            file=sys.stderr,
        )
        return 2

    job = {
        "mode": args.mode,
        "workspace": args.workspace,
        "dsh_home": args.dsh_home,
        "model": args.model,
        "effort": args.effort,
        "brief": "brief.txt" if args.brief else None,
        "port": args.port,
        "task": args.task,
        "env": env,
        "submitted": now.isoformat(),
    }
    job_path = os.path.join(job_dir, "job.json")
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(job, f)
    os.chmod(job_path, 0o600)

    if args.brief:
        brief_path = os.path.join(job_dir, "brief.txt")
        shutil.copyfile(args.brief, brief_path)
        os.chmod(brief_path, 0o600)

    # Flush the id immediately: stdout is block-buffered to a pipe, and the
    # caller (factory-task) reads the id from stdout alone; a later error on
    # stderr must never displace it.
    print(job_id, flush=True)

    if args.no_start:
        # Spool the job: write the empty marker that seat-spool.path watches.
        # The job directory stays behind (the operator may start it by hand).
        rc, msg = _spool_marker(args.spool_dir, job_id)
        if rc:
            print(msg, file=sys.stderr)
            return rc
        if args.wait:
            timeout, timeout_err = _poll_timeout(args.timeout)
            if timeout_err is not None:
                print(f"seat-submit: {timeout_err}", file=sys.stderr)
                return 2
            return _poll(job_dir, job_id, timeout, started=False)
        return 0

    # SA3 (decision 13b): a web/drive seat's port is allocated by seat-spool, so
    # the started path for those modes spools the job and waits for the spool to
    # allocate and start it -- printing `port=<n>` on the second stdout line
    # once `.spooled` appears (the first line stays the job id). The cap check
    # below is headless-only: the spool enforces the cap (IS1c) and seat-submit
    # never starts a web/drive unit directly.
    if args.mode in ("web", "drive"):
        rc, msg = _spool_marker(args.spool_dir, job_id)
        if rc:
            print(msg, file=sys.stderr)
            return rc
        timeout, timeout_err = _poll_timeout(args.timeout)
        if timeout_err is not None:
            print(f"seat-submit: {timeout_err}", file=sys.stderr)
            return 2
        return _await_spooled(job_dir, timeout)

    # IS1 (decision 72a, corrected in IS1c): the running-unit cap is enforced
    # only here, on the headless started path -- the path that actually starts a
    # unit. The --no-start path above never counts and never refuses (inside a
    # seat@ unit systemctl is denied by design). Fail closed on a malformed cap
    # or an unreadable count; exit 3 is reserved for this refusal alone (the
    # _poll "ended without a result" path exits 4).
    cap, cap_err = _max_units_cap()
    if cap_err is not None:
        print(f"seat-submit: {cap_err}", file=sys.stderr)
        return 3
    count, err = _seat_unit_count()
    if err is not None:
        print(f"seat-submit: cannot count seat units ({err})", file=sys.stderr)
        return 3
    if count >= cap:
        print(f"seat-submit: {count} seat units running, cap {cap}", file=sys.stderr)
        return 3

    # check=False, deliberately (the same reasoning as lane-submit.py): a
    # `systemctl start` on this unit waits for the unit to reach its terminal
    # state and reports the unit's own exit code, which reads identically to a
    # real failure to start. The valid outcome -- result included -- is always
    # in the job directory for the caller to read.
    subprocess.run(["systemctl", "start", f"seat@{job_id}"], check=False)

    timeout, timeout_err = _poll_timeout(args.timeout)
    if timeout_err is not None:
        print(f"seat-submit: {timeout_err}", file=sys.stderr)
        return 2
    return _poll(job_dir, job_id, timeout, started=True)


def main():
    return cmd_submit(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
