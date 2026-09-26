"""Operator/orchestrator CLI for the seat lane (plan 2026-09-05-seat-behind-broker,
SB3): writes a job directory for `seat-run` (SB1's unit entry) and starts the
unit that runs it, or -- in headless mode -- polls for that unit's result and
streams it back.

    seat-submit [--jobs-dir DIR] [--no-start] {headless|web}
        --workspace PATH --dsh-home PATH --model ID --effort LEVEL
        [--brief FILE] [--port N] [--timeout S]

Writes /var/lib/seat/jobs/<id>/ (0700, owner = invoking user), where <id> is
`YYYYmmdd-HHMMSS-<6 hex>`, containing job.json and, when --brief is given, the
brief copied to brief.txt. Prints the job id. Unless --no-start, runs
`systemctl start seat@<id>` (check=False, as lane-submit.py does) and -- for
headless mode -- waits (poll every 2 s, up to --timeout default 10800 s) until
the unit's result.txt appears, then copies stdout.txt to its own stdout and
exits with the code in exit_code.txt. If --timeout expires first, the unit is
stopped (`systemctl stop`) and the exit code is 124. Refuses a --workspace that
is not a directory or a --brief that is unreadable (exit 2).

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


def cmd_submit(argv):
    p = argparse.ArgumentParser(prog="seat-submit")
    p.add_argument("--jobs-dir", default=DEFAULT_JOBS_DIR)
    p.add_argument("--no-start", action="store_true")
    p.add_argument("mode", choices=["headless", "web"])
    p.add_argument("--workspace", required=True)
    p.add_argument("--dsh-home", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--effort", required=True)
    p.add_argument("--brief")
    p.add_argument("--port", type=int)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = p.parse_args(argv)

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
        return 0

    # check=False, deliberately (the same reasoning as lane-submit.py): a
    # `systemctl start` on this unit waits for the unit to reach its terminal
    # state and reports the unit's own exit code, which reads identically to a
    # real failure to start. The valid outcome -- result included -- is always
    # in the job directory for the caller to read.
    subprocess.run(["systemctl", "start", f"seat@{job_id}"], check=False)

    if args.mode != "headless":
        return 0

    result_path = os.path.join(job_dir, "result.txt")
    deadline = time.time() + args.timeout
    while not os.path.exists(result_path):
        if time.time() >= deadline:
            print(f"seat-submit: timed out waiting for {result_path}", file=sys.stderr)
            # A timed-out headless job must not be orphaned: stop the unit and
            # report 124 (the conventional timeout exit) so the caller can tell
            # a timeout apart from a task that merely failed.
            subprocess.run(["systemctl", "stop", f"seat@{job_id}"], check=False)
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


def main():
    return cmd_submit(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
