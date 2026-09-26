"""The seat unit's entry (plan 2026-09-05-seat-behind-broker, SB1).

    seat-run <job-id>

Reads /var/lib/seat/jobs/<job-id>/job.json (written by seat-submit, SB3),
exports the job's dsh_home as DSH_HOME, the job id as SEAT_JOB_ID, the
job's mode as SEAT_MODE and -- when the job names one -- its task address
as SEAT_TASK (OC9: seat-submit's --task, sent on as the broker's
x-factory-task header); the job's allow-listed `env` is exported beside
DSH_HOME and the effort, an alien name or a non-string value refuses the
job (exit 2) before the harness starts, and an allow-listed name the job
does not carry is popped; then cd's to the job's workspace, then runs the
pinned harness through its own egress broker:

* headless -- `dsh-openrouter --broker --model <model> --headless @<brief path>`
              (FA31: the brief reaches the wrapper as @<absolute path> to
              the job's own brief.txt -- FA30's form, read by the wrapper --
              never as one argv element, so a brief over the kernel's
              per-argument cap still launches)
* web      -- `dsh-openrouter --broker --bind-namespace <namespaceAddress>
              -- --no-open --port <port>`
* drive    -- the web command plus `--model <model>` and the full-access
              permission preset before the `--` (SD7, 57a)

stdout is streamed line by line to the job dir's stdout.txt and the unit's own
journal (stderr goes straight to stderr.txt); the process exit code goes to
exit_code.txt; the FACTORY-RESULT/CHECKS/COMMITS/NOTES block (or the literal
`status=failed`) goes to result.txt. A web/drive job rewrites dsh's token URL
from loopback to the namespace address for url.txt and prints it.

SA3 (decision 13b): a web/drive job's port is allocated by seat-spool and
written back into job.json before .spooled. A directly started unit whose port
is still null (seat-spool never ran) refuses with `seat-run: job <id> has no
allocated port (seat-spool did not run)` and exits 2, never binding a random
port.

The unit (nixosModules/seatLane.nix) supplies the namespace address via
SEAT_NAMESPACE_ADDRESS and the harness (dsh-openrouter) and `ip` via PATH;
this script is stdlib-only.
"""

import json
import os
import subprocess
import sys

JOBS_DIR = "/var/lib/seat/jobs"

# PT3 (plan 2026-09-22-planning-patterns): the job's environment allow-list --
# the names seat-submit may record into job.json and this unit may export. The
# same tuple is defined in seat-submit.py (which validates the values); a test
# asserts the two are equal. A job carrying any other name is refused here, so
# a hand-edited job.json cannot widen the unit's environment.
SEAT_JOB_ENV = ("OPENROUTER_CONTEXT_WINDOW",)

RESULT_FIELDS = ("FACTORY-RESULT", "FACTORY-CHECKS", "FACTORY-COMMITS", "FACTORY-NOTES")


def _job_dir(job_id):
    return os.path.join(JOBS_DIR, job_id)


def _load_job(job_id):
    with open(os.path.join(_job_dir(job_id), "job.json"), encoding="utf-8") as f:
        return json.load(f)


def _extract_result(stdout_text):
    """The last usable line of each FACTORY-* label (factory-task's own
    extraction rule: skip any candidate still holding the '<...>' placeholder),
    or the literal `status=failed` when the harness printed no FACTORY-RESULT
    line at all."""
    picked = []
    for label in RESULT_FIELDS:
        matches = [
            line
            for line in stdout_text.splitlines()
            if (line == label or line.startswith(label + " ")) and "<" not in line
        ]
        if matches:
            picked.append(matches[-1])
    return "\n".join(picked) if picked else "status=failed"


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def run(argv):
    if not argv:
        print("seat-run: missing job id", file=sys.stderr)
        return 2
    job_id = argv[0]
    job_dir = _job_dir(job_id)
    job = _load_job(job_id)

    # SA3 (decision 13b): a web/drive job's port is allocated by seat-spool and
    # written back before .spooled. A directly started unit whose port is still
    # null (seat-spool never ran) must refuse rather than invent one -- exit 2.
    if job["mode"] in ("web", "drive") and job.get("port") is None:
        print(
            f"seat-run: job {job_id} has no allocated port (seat-spool did not run)",
            file=sys.stderr,
        )
        return 2

    # Per-job, not per-unit: DSH_HOME and the reasoning effort come from the
    # submitted job (seat-submit records them), never from the template unit.
    os.environ["DSH_HOME"] = job["dsh_home"]
    if job.get("effort"):
        os.environ["OPENROUTER_REASONING_EFFORT"] = job["effort"]
    # SD5: the environment fact factory-task (SD6) and factory-wave (SD3) read
    # to name their own run/result files -- exported before the harness starts
    # so every tool the harness spawns sees the same job id.
    os.environ["SEAT_JOB_ID"] = job_id
    # SA6's discriminator (60a): every job names its mode to the harness env
    # (headless | web | drive), exported beside SEAT_JOB_ID before the harness
    # starts so the session can tell the drive seat from an ordinary job seat.
    os.environ["SEAT_MODE"] = job["mode"]
    # OC9: the job's task address (<run>/<key>, seat-submit's --task) is
    # exported beside SEAT_JOB_ID so the wrapper can label every request
    # x-factory-task behind the broker. A job without one must not inherit a
    # stale SEAT_TASK from the enclosing environment -- a leaked label would
    # attribute this job's spend to another task -- so it is popped, never
    # passed through.
    if isinstance(job.get("task"), str) and job["task"]:
        os.environ["SEAT_TASK"] = job["task"]
    else:
        os.environ.pop("SEAT_TASK", None)

    # PT3: the allow-listed environment the submitting shell carried (job.json's
    # `env`, written by seat-submit) -- exported before the harness starts, the
    # way DSH_HOME and the effort are. A name outside the allow-list refuses the
    # job rather than widening this unit's environment; an allow-listed name the
    # job does not carry is popped, never inherited from the template unit (the
    # SEAT_TASK rule). An older job.json without `env` reads as {}.
    job_env = job.get("env") or {}
    for name in sorted(job_env):
        if name not in SEAT_JOB_ENV:
            print(
                f"seat-run: job {job_id} env carries {name}, not in the allow-list",
                file=sys.stderr,
            )
            return 2
        # PT3 [tester]: the value's FORMAT is the submitter's rule, but its TYPE
        # is this file's: a hand-edited job carrying an int or null would raise
        # TypeError inside the unit (a traceback, no result.txt), and "" would
        # export cleanly and kill the wrapper at launch (die 5).
        value = job_env[name]
        if not isinstance(value, str) or not value:
            print(
                f"seat-run: job {job_id} env value for {name} is not a non-empty string",
                file=sys.stderr,
            )
            return 2
    for name in SEAT_JOB_ENV:
        if name in job_env:
            os.environ[name] = job_env[name]
        else:
            os.environ.pop(name, None)

    os.chdir(job["workspace"])

    namespace = None
    if job["mode"] == "headless":
        # FA31 (BUG-seat-brief-argv-too-long, closed with FA30's form): the
        # brief is handed to the harness as @<absolute path> -- the wrapper
        # reads the file itself -- so a brief of any size is a short pointer,
        # never one execve argument: the 134383-byte OS5 brief died in execve
        # with `OSError: [Errno 7] Argument list too long` (the kernel's
        # per-argument cap, MAX_ARG_STRLEN 131072, not ARG_MAX) when it was
        # inlined here. Nothing is read into a variable; the path is the
        # job's own brief.txt (copied in 0600 by seat-submit, inside the
        # unit's ReadWritePaths), and only absolute paths expand in the
        # wrapper -- a relative token would stay literal and run the model
        # on the pointer, hence abspath.
        brief_path = os.path.abspath(os.path.join(job_dir, job["brief"]))
        cmd = [
            "dsh-openrouter",
            "--broker",
            "--model",
            job["model"],
            "--headless",
            "@" + brief_path,
        ]
    else:  # web or drive
        namespace = os.environ["SEAT_NAMESPACE_ADDRESS"]
        port = job["port"]
        # SD7: drive is the web command plus the routed model BEFORE the `--`
        # (the wrapper's explicit --model wins over the isolated home's saved
        # selection, Assumption 10); web has no --model (the saved picker
        # selection decides, Assumption 7).
        if job["mode"] == "drive":
            # 57a: the drive launch runs at the full-access preset (the session
            # that drives the whole batch is prompted on every write otherwise,
            # 69a). The preset is an argument, not the guard: the PreToolUse
            # hook is independent of the permission mode (SA5's bats case
            # proves it), so the preset never means "no guard".
            cmd = [
                "dsh-openrouter",
                "--broker",
                "--bind-namespace",
                namespace,
                "--model",
                job["model"],
                "--permission",
                "danger-full-access",
                "--",
                "--no-open",
                "--port",
                str(port),
            ]
        else:
            cmd = [
                "dsh-openrouter",
                "--broker",
                "--bind-namespace",
                namespace,
                "--",
                "--no-open",
                "--port",
                str(port),
            ]

    # check=False semantics: the harness's exit code is recorded to
    # exit_code.txt and returned as this unit's own, never treated as a Python
    # exception (a non-zero exit simply carries through Popen.wait()).
    stdout_path = os.path.join(job_dir, "stdout.txt")
    stderr_path = os.path.join(job_dir, "stderr.txt")
    is_web = job["mode"] in ("web", "drive")

    # Stream the harness's stdout line by line (never capture_output, which
    # buffers the whole of a long-lived web server's output until exit): each
    # line is teed to stdout.txt (flushed per line) and the unit's journal as it
    # arrives, and recorded for result.txt. For a web/drive job, dsh's printed
    # line carries the only copy of its per-process token and is always loopback
    # (the findings doc), so the first line matching it is rewritten to the
    # namespace address the operator's browser reaches through the transparent
    # socat forwarder, and becomes url.txt and one printed line while the child
    # is still running. Headless never constructs or writes url.txt.
    accumulated = []
    with open(stderr_path, "w", encoding="utf-8") as stderr_fh:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=stderr_fh, text=True
        )
        with open(stdout_path, "w", encoding="utf-8") as stdout_fh:
            url_written = False
            for line in proc.stdout:
                accumulated.append(line)
                stdout_fh.write(line)
                stdout_fh.flush()
                if (
                    is_web
                    and not url_written
                    and line.startswith("dsh web: http://127.0.0.1:")
                    and "/?token=" in line
                ):
                    rewritten = line.replace(
                        "dsh web: http://127.0.0.1:",
                        f"http://{namespace}:",
                        1,
                    )
                    _write(os.path.join(job_dir, "url.txt"), rewritten)
                    sys.stdout.write(rewritten)
                    url_written = True
                else:
                    sys.stdout.write(line)
                sys.stdout.flush()
        returncode = proc.wait()

    _write(os.path.join(job_dir, "exit_code.txt"), f"{returncode}\n")

    # result.txt: the last usable line of each FACTORY-* label over the COMPLETE
    # accumulated stdout, exactly as the buffered parse did before streaming.
    _write(
        os.path.join(job_dir, "result.txt"),
        _extract_result("".join(accumulated)) + "\n",
    )

    return returncode


def main():
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
