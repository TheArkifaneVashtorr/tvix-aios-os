"""The seat unit's entry (plan 2026-09-05-seat-behind-broker, SB1).

    seat-run <job-id>

Reads /var/lib/seat/jobs/<job-id>/job.json (written by seat-submit, SB3),
exports the job's dsh_home as DSH_HOME and the job id as SEAT_JOB_ID, cd's to
the job's workspace, then runs the pinned harness through its own egress
broker:

* headless -- `dsh-openrouter --broker --model <model> --headless <brief>`
* web      -- `dsh-openrouter --broker --bind-namespace <namespaceAddress>
              -- --no-open --port <port>`
* drive    -- the web command plus `--model <model>` before the `--` (SD7)

stdout/stderr are teed to the job dir's stdout.txt/stderr.txt (and forwarded
to the unit's own journal); the process exit code goes to exit_code.txt; the
FACTORY-RESULT/CHECKS/COMMITS/NOTES block (or the literal `status=failed`)
goes to result.txt. A web job prints its URL to the journal and url.txt.

The unit (nixosModules/seatLane.nix) supplies the namespace address via
SEAT_NAMESPACE_ADDRESS and the harness (dsh-openrouter) and `ip` via PATH;
this script is stdlib-only.
"""

import json
import os
import subprocess
import sys

JOBS_DIR = "/var/lib/seat/jobs"

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

    # Per-job, not per-unit: DSH_HOME and the reasoning effort come from the
    # submitted job (seat-submit records them), never from the template unit.
    os.environ["DSH_HOME"] = job["dsh_home"]
    if job.get("effort"):
        os.environ["OPENROUTER_REASONING_EFFORT"] = job["effort"]
    # SD5: the environment fact factory-task (SD6) and factory-wave (SD3) read
    # to name their own run/result files -- exported before the harness starts
    # so every tool the harness spawns sees the same job id.
    os.environ["SEAT_JOB_ID"] = job_id

    os.chdir(job["workspace"])

    if job["mode"] == "headless":
        brief_path = os.path.join(job_dir, job["brief"])
        with open(brief_path, encoding="utf-8") as f:
            brief = f.read()
        cmd = [
            "dsh-openrouter",
            "--broker",
            "--model",
            job["model"],
            "--headless",
            brief,
        ]
    else:  # web or drive
        namespace = os.environ["SEAT_NAMESPACE_ADDRESS"]
        port = job["port"]
        # SD7: drive is the web command plus the routed model BEFORE the `--`
        # (the wrapper's explicit --model wins over the isolated home's saved
        # selection, Assumption 10); web has no --model (the saved picker
        # selection decides, Assumption 7).
        if job["mode"] == "drive":
            cmd = [
                "dsh-openrouter",
                "--broker",
                "--bind-namespace",
                namespace,
                "--model",
                job["model"],
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
        url = f"http://{namespace}:{port}"
        _write(os.path.join(job_dir, "url.txt"), url + "\n")
        # The operator opens this URL (runbook docs/runbooks/seat.md); print it
        # so it reaches the journal, and write it to url.txt for the web job.
        print(url, flush=True)

    # check=False: the harness's exit code is recorded to exit_code.txt and
    # returned as this unit's own, never treated as a Python exception.
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    stdout_text = proc.stdout or ""
    stderr_text = proc.stderr or ""

    # Tee: the job dir's files are what seat-submit streams back to the
    # caller; the unit's own journal keeps a parallel record.
    _write(os.path.join(job_dir, "stdout.txt"), stdout_text)
    _write(os.path.join(job_dir, "stderr.txt"), stderr_text)
    sys.stdout.write(stdout_text)
    sys.stderr.write(stderr_text)

    _write(os.path.join(job_dir, "exit_code.txt"), f"{proc.returncode}\n")
    _write(os.path.join(job_dir, "result.txt"), _extract_result(stdout_text) + "\n")

    return proc.returncode


def main():
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
