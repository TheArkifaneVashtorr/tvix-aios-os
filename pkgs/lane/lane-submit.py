"""Operator/orchestrator CLI for the model lanes (Lane L round 1 plan,
Task 3): writes a job file for `lane-run` (pkgs/lane/lane-run.py) and starts
the unit that runs it, or polls for that unit's result.

One file backs two binaries, `lane-submit` and `lane-wait`
(nixosModules/modelLane.nix wraps this file twice, each wrapper setting
LANE_MODE before exec -- mirrors pkgs/helm/collect.py's own --print dispatch
for helm-status). Direct invocation (as in tests) defaults to submit mode.

  lane-submit <lane> --kind chat|agent --class permitted --model M
      [--schema file.json] [--repo dir] [--max-turns N] [--max-tokens N]
      [--keep-snapshot]
      < prompt-or-messages.json
    Chat kind reads a JSON array of {role, content} messages from stdin (or
    an object {"messages": [...]});  agent kind reads {"prompt": "..."} or
    falls back to the raw stdin text as the prompt. Prints the new job id.
    --keep-snapshot tells lane-run.py not to delete the agent job's repo
    snapshot after writing its result (the default is to delete it).

  lane-wait <lane> <job-id> [--timeout S] [--poll-interval S]
    Polls results/<job-id>.json, prints it once it exists, and exits
    non-zero if the result itself carries an "error" key.
"""

import argparse
import grp
import json
import os
import shutil
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path

# Refused as --repo sources for the "agent" kind: an agent job's repo
# snapshot is copied into the world its lane can read (and its
# network-capable process runs against), and none of these belong there --
# Claude memory, decrypted basket contents (both the tmpfs mount point and
# the blessed store), Helm's own collected state, the broker's audit trail
# and CA private key, other lanes' job/result spools, provider secrets, and
# the operator's own strategy/economics tree are all local-only (brief §3,
# data-and-models spec §5; T3 fix round -- the original list only had three
# of these eight, so a --repo under e.g. /run/baskets or /var/lib/secrets
# was silently accepted and copied straight into a network-capable job).
# This set must stay identical to the two copies in
# pkgs/dsh-openrouter/hook-guard.py (PROTECTED_ABSOLUTE + the HOME-relative
# literals) and the `forbidden=(…)` array in pkgs/dsh-openrouter/dsh-openrouter.sh;
# tests/lane/test_forbidden_lists_agree.py proves the three agree. Generating
# the list from a single Nix source is still a gap (claim `forbidden-list-single-source`).
FORBIDDEN_REPO_PREFIXES = (
    "~/.claude",
    "~/.config/openrouter",
    "~/strategy",
    "/run/baskets",
    "/var/lib/baskets",
    "/var/lib/helm",
    "/var/lib/egress-broker",
    "/var/lib/lanes",
    "/var/lib/secrets",
)


def _lane_paths(lane):
    base = os.environ.get("LANE_STATE_DIR", "/var/lib/lanes")
    lane_dir = os.path.join(base, lane)
    return {
        "lane_dir": lane_dir,
        "jobs_dir": os.path.join(lane_dir, "jobs"),
        "results_dir": os.path.join(lane_dir, "results"),
    }


def _refused_repo_prefix(repo_path):
    resolved = repo_path.expanduser().resolve()
    for raw in FORBIDDEN_REPO_PREFIXES:
        prefix = Path(raw).expanduser().resolve()
        try:
            resolved.relative_to(prefix)
        except ValueError:
            continue
        return prefix
    return None


def _set_lane_group(path):
    """Best-effort os.chown(path, -1, "lane" gid). Returns True when
    there's nothing to report -- either the "lane" group doesn't exist at
    all (expected in a test/dev sandbox with no such group; every other
    caller here already treats that as a no-op) or the chown succeeded --
    and False only in the one case that must NOT be swallowed: the group
    EXISTS but the chown itself failed. That specific failure is EPERM
    for a non-root caller who is not (yet) a member of "lane" -- which is
    exactly the operator's own shell in the login session that predates a
    switch that just created the group (T3 review, blocker B follow-up:
    this repo's own field lesson that a switch doesn't retroactively
    update an already-logged-in session's groups applies here the same
    way it does to user timers). Silently continuing in that case used to
    leave job_root group "users" -- the DynamicUser unit
    (SupplementaryGroups = ["lane"]) then gets EACCES creating its own
    config dir, and the operator gets an opaque PermissionError result
    instead of an actionable one. Callers on paths the unit MUST reach
    (job_root, the job file) check this return value and refuse the
    submit outright rather than write a job that can never run.
    """
    try:
        gid = grp.getgrnam("lane").gr_gid
    except KeyError:
        return True
    try:
        os.chown(path, -1, gid)
        return True
    except (PermissionError, OSError):
        return False


def _refuse_group_failure(path):
    print(
        f'lane-submit: cannot set group "lane" on {path} -- you are not in '
        "group lane yet; log out and back in after the switch",
        file=sys.stderr,
    )
    return 1


def _chmod_dir_setgid(path):
    """chmod 2770 (rwxrws---): SGID on a directory makes files later
    created inside it inherit group "lane" automatically, belt-and-braces
    alongside the explicit _set_lane_group calls this module already makes
    on everything it creates itself. Falls back to plain 0770 if the
    environment refuses to set SGID -- a real EPERM here, not a
    permissions-appropriate no-op: some sandboxes (including this repo's
    own `nix build` sandbox, which seccomp-filters chmod calls that would
    set S_ISUID/S_ISGID as a hardening measure -- see checks.lane-unit,
    which runs pytest inside exactly such a sandbox) refuse it outright.
    The real host's systemd-tmpfiles rule (root, unsandboxed) already sets
    SGID on the three top-level /var/lib/lanes/<name> directories, so
    group inheritance still works end to end there even on a fallback
    here.
    """
    try:
        os.chmod(path, 0o2770)
    except PermissionError:
        os.chmod(path, 0o770)


def _escaping_symlink(repo_root):
    """Returns the first symlink under `repo_root` (already resolved,
    absolute) that cannot safely survive being copied into the snapshot,
    or None.

    Runs before shutil.copytree(..., symlinks=True) below: keeping a
    symlink as a symlink (rather than dereferencing it) is only safe once
    we know two things -- its target lives inside the same tree being
    snapshotted, AND the link itself is relative, not absolute. A
    relative link's target is resolved against the directory that holds
    it wherever that directory ends up, so copying one verbatim into
    <jobdir>/repo still resolves inside the snapshot. An ABSOLUTE link
    does not have that property: os.walk + os.path.relative_to below can
    only check where an absolute link's target resolves right NOW, in the
    source tree -- copytree(symlinks=True) then copies the link's raw
    (absolute) text verbatim, so even one whose target currently lives
    inside repo_root still names the SOURCE tree's own path once copied,
    not the equivalent path under the snapshot. That reopens exactly the
    hole this function exists to close (T3 review: a repo containing
    `link -> /<repo>/sub/real.txt` passed the old target-only check, then
    the copied link in the snapshot still pointed at the live source
    tree, readable and writable through the "isolated" snapshot). So
    every absolute symlink is refused outright, regardless of where it
    points -- not just ones whose target resolves outside repo_root.
    followlinks=False so a symlinked directory is checked itself but
    never descended into as if it were real content.
    """
    for dirpath, dirnames, filenames in os.walk(repo_root, followlinks=False):
        for name in list(dirnames) + filenames:
            candidate = Path(dirpath) / name
            if not candidate.is_symlink():
                continue
            try:
                raw_target = os.readlink(candidate)
            except OSError:
                return candidate
            if os.path.isabs(raw_target):
                return candidate
            try:
                target = candidate.resolve()
            except OSError:
                return candidate
            try:
                target.relative_to(repo_root)
            except ValueError:
                return candidate
    return None


def _harden_snapshot(root):
    """2770 on every directory (root included), 0770 on every executable
    file, 0660 on every non-executable file, group "lane" throughout --
    the DynamicUser unit that later runs this job
    (SupplementaryGroups = [ "lane" ], an ephemeral uid it does not share
    with the operator) must be able to read the snapshot and write into it
    (an agent job may edit files in its own cwd), and nothing else on the
    host should be able to read a permitted-but-still-sensitive job's
    source tree. A file whose SOURCE mode has any execute bit keeps it
    (0770 rather than 0660) so that scripts and binaries in the snapshot
    remain runnable (the previous unconditional 0660 stripped executable
    bits from githooks, test scripts, etc.). Symlinks are left alone --
    cmd_submit's _escaping_symlink check above already refused anything
    absolute, and anything relative whose target resolves outside `root`,
    so every remaining symlink is relative and its target is itself
    somewhere under `root` -- true post-copy as well as pre-copy, since a
    relative link resolves against wherever its containing directory ends
    up -- and gets its own entry hardened when the walk reaches it.
    """
    _chmod_dir_setgid(root)
    _set_lane_group(root)
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames:
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                continue
            _chmod_dir_setgid(path)
            _set_lane_group(path)
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                continue
            st = os.stat(path)
            if st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                os.chmod(path, 0o770)
            else:
                os.chmod(path, 0o660)
            _set_lane_group(path)


def cmd_submit(argv):
    p = argparse.ArgumentParser(prog="lane-submit")
    p.add_argument("lane")
    p.add_argument("--kind", choices=["chat", "agent", "dsh"], required=True)
    p.add_argument("--class", dest="class_", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--schema")
    p.add_argument("--repo")
    p.add_argument("--max-turns", type=int, default=40)
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument(
        "--keep-snapshot",
        action="store_true",
        help="don't delete the agent job's repo snapshot after the result is written",
    )
    args = p.parse_args(argv)

    if args.kind in ("agent", "dsh") and not args.repo:
        print("lane-submit: --repo is required for --kind agent/dsh", file=sys.stderr)
        return 1

    raw = sys.stdin.read()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    job = {
        "kind": args.kind,
        "class": args.class_,
        "model": args.model,
        "max_tokens": args.max_tokens,
    }

    if args.kind == "chat":
        if isinstance(parsed, list):
            messages = parsed
        elif isinstance(parsed, dict) and isinstance(parsed.get("messages"), list):
            messages = parsed["messages"]
        else:
            print(
                "lane-submit: --kind chat needs JSON messages on stdin "
                '(a list, or {"messages": [...]})',
                file=sys.stderr,
            )
            return 1
        job["messages"] = messages
    else:
        if isinstance(parsed, dict) and isinstance(parsed.get("prompt"), str):
            prompt = parsed["prompt"]
        else:
            prompt = raw.strip()
        if not prompt:
            print("lane-submit: --kind agent needs a prompt on stdin", file=sys.stderr)
            return 1
        job["prompt"] = prompt
        job["max_turns"] = args.max_turns

    if args.schema:
        with open(args.schema, encoding="utf-8") as f:
            job["schema"] = json.load(f)

    job_id = uuid.uuid4().hex[:12]
    paths = _lane_paths(args.lane)
    os.makedirs(paths["jobs_dir"], exist_ok=True)

    if args.kind in ("agent", "dsh"):
        repo_src = Path(args.repo)
        forbidden = _refused_repo_prefix(repo_src)
        if forbidden is not None:
            print(f"lane-submit: refusing --repo under {forbidden}", file=sys.stderr)
            return 1
        if not repo_src.expanduser().is_dir():
            print(
                f"lane-submit: --repo {args.repo} is not a directory", file=sys.stderr
            )
            return 1
        repo_resolved = repo_src.expanduser().resolve()
        escaping = _escaping_symlink(repo_resolved)
        if escaping is not None:
            print(
                f"lane-submit: refusing symlink escaping the repo: {escaping}",
                file=sys.stderr,
            )
            return 1
        job_root = os.path.join(paths["jobs_dir"], job_id)
        repo_dst = os.path.join(job_root, "repo")
        os.makedirs(job_root, exist_ok=True)
        # 2770 + group lane BEFORE copytree, not after: the DynamicUser
        # unit that runs this job later also creates a "config" sibling
        # directory (CLAUDE_CONFIG_DIR) directly inside job_root, so
        # job_root itself -- not just repo_dst below -- must already be
        # group-writable (T3 fix round blocker B: this used to stay
        # 0755-owned-by-operator, so that mkdir failed with
        # PermissionError and the job never produced a result). If the
        # "lane" group exists but this chown fails, don't silently write
        # a job the unit can never run -- refuse now, before copytree
        # does any work (T3 review follow-up to blocker B).
        _chmod_dir_setgid(job_root)
        if not _set_lane_group(job_root):
            return _refuse_group_failure(job_root)
        # Plain copytree, not an rsync-style --exclude .git: the point of
        # "with git metadata included" is that the snapshot keeps history
        # (blame, log) available to the agent, not that it gets stripped.
        # symlinks=True: a symlink inside the repo is copied AS a symlink,
        # not dereferenced -- the escape check above already refused
        # anything whose target resolves outside the repo, so what's left
        # is safe to keep as a link; the previous default (dereferencing)
        # would have silently copied whatever real file a same-repo
        # symlink's target names, which is not what "snapshot this repo"
        # should mean.
        shutil.copytree(repo_resolved, repo_dst, symlinks=True)
        _harden_snapshot(repo_dst)
        job["repo"] = repo_dst
        job["keep_snapshot"] = args.keep_snapshot

    job_path = os.path.join(paths["jobs_dir"], f"{job_id}.json")
    tmp_path = job_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(job, f)
    os.chmod(tmp_path, 0o660)
    if not _set_lane_group(tmp_path):
        os.remove(tmp_path)
        return _refuse_group_failure(job_path)
    os.replace(tmp_path, job_path)

    # check=False, deliberately: `systemctl start` on a oneshot unit blocks
    # until it finishes and reports the unit's own exit code as its own --
    # lane-run.py exits 3 for a refused job (a correct, expected outcome
    # that still writes a result file, not a crash), and a `systemctl
    # start` non-zero exit reads identically to a real failure to start.
    # Surfacing that here as a lane-submit crash (a raised
    # CalledProcessError) would be wrong either way: the job id is valid
    # and the result -- refusal included -- is always in results/<id>.json
    # for lane-wait to report.
    unit = f"lane-{args.lane}@{job_id}.service"
    proc = subprocess.run(["systemctl", "start", unit], check=False)
    # 0 is a normal completed run; 3 is lane-run.py's own EXIT_REFUSED (a
    # correct, expected outcome for a refused job, not a failure to
    # start -- see the comment above). Anything else means systemd itself
    # failed to run the unit at all (bad NetworkNamespacePath, DynamicUser
    # setup failure, ...), which the operator would otherwise only
    # discover by noticing the job never produces a result and going
    # digging -- warn here, naming the exact `journalctl` invocation that
    # explains it, while still printing the job id (it is valid regardless;
    # results/<id>.json is where lane-wait looks either way).
    if proc.returncode not in (0, 3):
        print(
            f"lane-submit: warning: systemctl start {unit} exited "
            f"{proc.returncode} -- check journalctl -u {unit}",
            file=sys.stderr,
        )
    print(job_id)
    return 0


def cmd_wait(argv):
    p = argparse.ArgumentParser(prog="lane-wait")
    p.add_argument("lane")
    p.add_argument("job_id")
    p.add_argument("--timeout", type=float, default=1800)
    p.add_argument("--poll-interval", type=float, default=1.0)
    args = p.parse_args(argv)

    paths = _lane_paths(args.lane)
    result_path = os.path.join(paths["results_dir"], f"{args.job_id}.json")

    deadline = time.time() + args.timeout
    while not os.path.exists(result_path):
        if time.time() >= deadline:
            print(f"lane-wait: timed out waiting for {result_path}", file=sys.stderr)
            return 1
        time.sleep(args.poll_interval)

    with open(result_path, encoding="utf-8") as f:
        raw = f.read()
    print(raw)
    return 1 if json.loads(raw).get("error") else 0


def main():
    mode = os.environ.get("LANE_MODE", "submit")
    argv = sys.argv[1:]
    if mode == "wait":
        return cmd_wait(argv)
    return cmd_submit(argv)


if __name__ == "__main__":
    sys.exit(main())
