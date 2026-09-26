"""The spool -- the one host-side actor the seat may reach (plan
2026-09-06-seat-driver, SD6).

    seat-spool --jobs-dir D --spool-dir S --owner USER [--systemctl PATH]

Watches the marker directory S (seat-submit --no-start writes one empty marker
per job at S/<id>). For every marker, in sorted order: validate the job
directory D/<id> against the contract seat-submit wrote (an id-shaped name, a
0700 non-symlink directory owned by USER, a regular job.json holding a valid
headless/web/drive object, and no .spooled/exit_code.txt yet), then ALWAYS
unlink the marker (valid or not, so DirectoryNotEmpty never re-fires on a bad
marker), and either refuse (`seat-spool: refused <id>: <code>` on stderr) or
write D/<id>/.spooled (0600, the id inside) and start exactly one `seat@<id>`
instance (`systemctl start --no-block seat@<id>`).

A refusal is not the spool's failure: the exit code is 0 always. An unreadable
spool dir is exit 1 (`seat-spool: cannot read <S>`). The only subprocess the
program ever runs is that one `start`; every validation is a filesystem read.
"""

import argparse
import json
import os
import pwd
import re
import subprocess
import sys

ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")
MODEL_RE = re.compile(r"^[A-Za-z0-9._:/-]+$")
MODES = ("headless", "web", "drive")
EFFORTS = ("off", "low", "medium", "high", "xhigh")


def _refusal(jobs_dir, mid, uid):
    """The first contract break for marker `mid`, or None when valid. The
    order mirrors the interface: id, job dir (symlink/absence, owner, mode),
    job.json (regular file, JSON object, mode, workspace, dsh_home, model,
    effort, port), brief, .spooled, exit_code.txt."""
    if not ID_RE.match(mid):
        return "bad-id"
    d = os.path.join(jobs_dir, mid)
    if os.path.islink(d):
        return "job-dir-symlink"
    if not os.path.isdir(d):
        return "no-job-dir"
    st = os.stat(d)
    if st.st_uid != uid:
        return "job-dir-owner"
    if (st.st_mode & 0o777) != 0o700:
        return "job-dir-mode"
    job_path = os.path.join(d, "job.json")
    if os.path.islink(job_path) or not os.path.isfile(job_path):
        return "no-job-json"
    try:
        with open(job_path, encoding="utf-8") as f:
            job = json.load(f)
    except (OSError, ValueError):
        return "bad-json"
    if not isinstance(job, dict):
        return "bad-json"
    mode = job.get("mode")
    if mode not in MODES:
        return "bad-mode"
    for key, code in (("workspace", "bad-workspace"), ("dsh_home", "bad-dsh-home")):
        path = job.get(key)
        if (
            not isinstance(path, str)
            or not os.path.isabs(path)
            or not os.path.isdir(path)
        ):
            return code
        try:
            if os.stat(path).st_uid != uid:
                return code
        except OSError:
            return code
    model = job.get("model")
    if not isinstance(model, str) or not MODEL_RE.match(model):
        return "bad-model"
    if job.get("effort") not in EFFORTS:
        return "bad-effort"
    port = job.get("port")
    if mode == "headless":
        if port is not None:
            # A headless job must carry port = null; any int (even one in
            # range) is bad-port -- the row that kills a `port in 1024..65535`
            # shortcut.
            return "bad-port"
    elif (
        not isinstance(port, int)
        or isinstance(port, bool)
        or not (1024 <= port <= 65535)
    ):
        return "bad-port"
    brief = job.get("brief")
    if mode == "headless":
        if brief != "brief.txt":
            return "no-brief"
        brief_path = os.path.join(d, "brief.txt")
        if os.path.islink(brief_path) or not os.path.isfile(brief_path):
            return "no-brief"
    elif brief is not None:
        return "no-brief"
    if os.path.exists(os.path.join(d, ".spooled")):
        return "already-started"
    if os.path.exists(os.path.join(d, "exit_code.txt")):
        return "finished"
    return None


def main(argv):
    p = argparse.ArgumentParser(prog="seat-spool")
    p.add_argument("--jobs-dir", required=True)
    p.add_argument("--spool-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--systemctl", default="systemctl")
    args = p.parse_args(argv)

    try:
        uid = pwd.getpwnam(args.owner).pw_uid
    except KeyError:
        print(f"seat-spool: unknown user {args.owner}", file=sys.stderr)
        return 1

    try:
        entries = sorted(os.listdir(args.spool_dir))
    except OSError:
        print(f"seat-spool: cannot read {args.spool_dir}", file=sys.stderr)
        return 1

    for mid in entries:
        code = _refusal(args.jobs_dir, mid, uid)
        marker = os.path.join(args.spool_dir, mid)
        try:
            os.unlink(marker)
        except OSError:
            pass
        if code is not None:
            print(f"seat-spool: refused {mid}: {code}", file=sys.stderr)
            continue
        spooled = os.path.join(args.jobs_dir, mid, ".spooled")
        fd = os.open(spooled, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            os.write(fd, mid.encode("utf-8"))
        finally:
            os.close(fd)
        proc = subprocess.run(
            [args.systemctl, "start", "--no-block", f"seat@{mid}"], check=False
        )
        if proc.returncode == 0:
            print(f"seat-spool: started seat@{mid}")
        else:
            print(f"seat-spool: start failed for {mid}: rc={proc.returncode}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
