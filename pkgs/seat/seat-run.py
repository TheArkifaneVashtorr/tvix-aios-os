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

stdout is streamed line by line to the job dir's stdout.txt and the unit's own
journal (stderr goes straight to stderr.txt); the process exit code goes to
exit_code.txt; the FACTORY-RESULT/CHECKS/COMMITS/NOTES block (or the literal
`status=failed`) goes to result.txt. A web/drive job rewrites dsh's token URL
from loopback to the namespace address for url.txt and prints it.

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

    namespace = None
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
