"""Operator/orchestrator CLI for the seat lane (plan 2026-09-05-seat-behind-broker,
SB3): writes a job directory for `seat-run` (SB1's unit entry) and starts the
unit that runs it, or -- in headless mode -- polls for that unit's result and
streams it back.

    seat-submit [--jobs-dir DIR] [--no-start] [--wait] [--spool-dir DIR]
        {headless|web|drive} --workspace PATH --dsh-home PATH --model ID
        --effort LEVEL [--brief FILE] [--port N] [--timeout S]

Writes /var/lib/seat/jobs/<id>/ (0700, owner = invoking user), where <id> is
`YYYYmmdd-HHMMSS-<6 hex>`, containing job.json and, when --brief is given, the
brief copied to brief.txt. Prints the job id. Unless --no-start, runs
`systemctl start seat@<id>` (check=False, as lane-submit.py does) and -- for
headless mode -- waits (poll every 2 s, up to --timeout default 10800 s) until
the unit's result.txt appears, then copies stdout.txt to its own stdout and
exits with the code in exit_code.txt. If the unit ends before result.txt
appears (ActiveState failed/inactive with a non-success Result), seat-submit
dumps the unit's journalctl tail to stderr and exits 3 at once, not after the
timeout. If --timeout expires first, the unit is stopped (`systemctl stop`)
and the exit code is 124. Refuses a --workspace that is not a directory or a
--brief that is unreadable (exit 2).

--no-start (SD6) spools instead of starting: it writes an empty 0600 marker at
<--spool-dir>/<id> (the default spool dir is the sibling of --jobs-dir, e.g.
/var/lib/seat/spool) and returns -- seat-spool.path starts the unit, never
seat-submit via systemctl. --wait (headless, with --no-start) polls result.txt
and streams stdout.txt exactly as the started path does, but never calls
systemctl: on timeout it exits 124 and names the still-running seat@<id>
instead of stopping it. --wait without --no-start, or with a web job, is exit
2 (usage).

The unit (SB1's seat-run.py) writes stdout.txt, stderr.txt, exit_code.txt and
result.txt into the job directory; the --jobs-dir default is /var/lib/seat/jobs
(tests pass a tmp dir and --no-start).
"""

import argparse
import datetime
import json
import os
import secrets
import shutil
import subprocess
import sys
import time

DEFAULT_JOBS_DIR = "/var/lib/seat/jobs"
DEFAULT_TIMEOUT = 10800
POLL_INTERVAL = 2

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
                return 3
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
    if os.path.exists(stdout_path):
        with open(stdout_path, encoding="utf-8") as f:
            sys.stdout.write(f.read())

    exit_code = 0
    exit_path = os.path.join(job_dir, "exit_code.txt")
    if os.path.exists(exit_path):
        with open(exit_path, encoding="utf-8") as f:
            raw = f.read().strip()
        try:
            exit_code = int(raw)
        except ValueError:
            exit_code = 0
    return exit_code


def cmd_submit(argv):
    p = argparse.ArgumentParser(prog="seat-submit")
    p.add_argument("--jobs-dir", default=DEFAULT_JOBS_DIR)
    p.add_argument("--no-start", action="store_true")
    p.add_argument("--wait", action="store_true")
    p.add_argument("--spool-dir", default=None)
    p.add_argument("mode", choices=["headless", "web", "drive"])
    p.add_argument("--workspace", required=True)
    p.add_argument("--dsh-home", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--effort", required=True)
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
    # so it needs a web port (an int 1024-65535), refuses the headless brief,
    # and requires the driver's skill set in --dsh-home -- the isolated home is
    # seeded by the caller (seat-drive.sh), never from the operator's shared
    # one (nothing automated inherits the saved selection, addendum rule 1).
    if args.mode == "drive":
        if args.port is None or not (1024 <= args.port <= 65535):
            print("drive needs --port", file=sys.stderr)
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
        # The job directory stays behind (the operator may start it by hand);
        # the marker is created with O_CREAT|O_EXCL so a collision is a clean
        # exit 2, never a silent overwrite of a marker the spool is about to
        # consume.
        try:
            os.makedirs(args.spool_dir, exist_ok=True)
        except OSError as e:
            print(
                f"seat-submit: could not create spool directory {args.spool_dir}: {e}",
                file=sys.stderr,
            )
            return 2
        marker = os.path.join(args.spool_dir, job_id)
        try:
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except OSError as e:
            print(f"seat-submit: could not spool {job_id}: {e}", file=sys.stderr)
            return 2
        if args.wait:
            return _poll(job_dir, job_id, args.timeout, started=False)
        return 0

    # check=False, deliberately (the same reasoning as lane-submit.py): a
    # `systemctl start` on this unit waits for the unit to reach its terminal
    # state and reports the unit's own exit code, which reads identically to a
    # real failure to start. The valid outcome -- result included -- is always
    # in the job directory for the caller to read.
    subprocess.run(["systemctl", "start", f"seat@{job_id}"], check=False)

    if args.mode != "headless":
        return 0

    return _poll(job_dir, job_id, args.timeout, started=True)


def main():
    return cmd_submit(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
