"""Model-lane job runner (Lane L round 1 plan, Task 3).

Invoked by nixosModules/modelLane.nix's `lane-<name>@.service` template as
`lane-run <lane> <job-id>` (stdlib only -- no packages.systemPackages needed
beyond python3). Reads one job file, refuses anything not classed
"permitted" for this lane (belt-and-braces: the module already rejects any
`allowedClasses` other than "permitted" at eval time -- see
nixosModules/modelLane.nix), runs it, and writes one result file plus one
ledger line.

Two job kinds:

  chat  -- an OpenAI-compatible chat-completions POST to the lane's host
           through the broker's HTTPS_PROXY (the unit sets it; the broker
           injects the Authorization header for us -- this script never
           holds, reads, or sends any credential). Retries 429/5xx.

  agent -- runs `claude -p` from PATH (see nixosModules/modelLane.nix for
           why the unit's PATH carries /run/current-system/sw/bin: the
           claude binary is the operator's own system profile, not a Nix
           runtime input of this package) against ANTHROPIC_BASE_URL =
           https://<lane host>/api with a dummy auth token the broker
           overwrites, same non-custody guarantee as the chat path.

Environment (set by nixosModules/modelLane.nix's unit, or by tests):
  LANE_HOST      -- the single upstream host this lane's broker allows.
  LANE_CLASSES   -- comma-separated classes this lane accepts (currently
                    always "permitted"; read at runtime rather than assumed,
                    so a future module change can't silently widen this).
  LANE_STATE_DIR -- overrides the /var/lib/lanes spool root (tests only).
  LANE_SCHEME    -- overrides "https" for the chat POST (tests only, to hit
                    a plain fake HTTP server without a TLS/proxy rig -- the
                    VM check (checks.lane-vm) is what proves the real
                    HTTPS_PROXY + broker-injected-credential path).
  LANE_RETRY_BACKOFF_S -- comma-separated seconds between chat retries
                    (default "2,4,8"; tests set "0,0,0" to run fast).
  LANE_HTTP_TIMEOUT_S -- per-attempt urlopen() timeout in seconds (default
                    "600"; tests lower this to exercise a stalled read
                    without an actual ten-minute wait; job field
                    "timeout_s" takes precedence when present).
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_REFUSED = 3


def _lane_paths(lane):
    base = os.environ.get("LANE_STATE_DIR", "/var/lib/lanes")
    lane_dir = os.path.join(base, lane)
    return {
        "lane_dir": lane_dir,
        "jobs_dir": os.path.join(lane_dir, "jobs"),
        "results_dir": os.path.join(lane_dir, "results"),
        "ledger_path": os.path.join(lane_dir, "ledger.jsonl"),
    }


def _write_result(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _append_ledger(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _refuse(result_path, reason):
    _write_result(result_path, {"error": reason, "ts": time.time()})
    return EXIT_REFUSED


def _fail(result_path, reason):
    _write_result(result_path, {"error": reason, "ts": time.time()})
    return EXIT_ERROR


def run_chat(job, job_id, paths):
    host = os.environ["LANE_HOST"]
    scheme = os.environ.get("LANE_SCHEME", "https")
    url = f"{scheme}://{host}/api/v1/chat/completions"

    provider = {"zdr": True, "data_collection": "deny"}
    if job.get("providers"):
        provider["order"] = job["providers"]
    body = {
        "model": job["model"],
        "messages": job["messages"],
        "max_tokens": job["max_tokens"],
        "provider": provider,
    }
    if job.get("schema"):
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "lane_job_schema",
                "strict": True,
                "schema": job["schema"],
            },
        }
    payload = json.dumps(body).encode("utf-8")

    backoffs = [
        float(x) for x in os.environ.get("LANE_RETRY_BACKOFF_S", "2,4,8").split(",")
    ]
    # Long generations timed out at 120 s on 2026-09-03; default is now 600.
    http_timeout = float(
        job.get("timeout_s", os.environ.get("LANE_HTTP_TIMEOUT_S", "600"))
    )
    max_attempts = 3
    last_error = "no attempt made"
    response_json = None
    start = time.time()
    for attempt in range(max_attempts):
        # A fresh Request every attempt: urllib.request.Request objects are
        # not meant to be replayed after a failed urlopen().
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            # No Authorization header, ever -- see the module docstring
            # above. The broker injects it for LANE_HOST from a key file
            # this process never opens.
        )
        # Both the read and the parse of the response live inside this
        # try, not just the urlopen() call: a response that stalls after
        # headers arrive raises TimeoutError (socket.timeout is an alias)
        # from resp.read() -- not wrapped by urllib into URLError, since
        # that wrapping only covers the connect/header phase inside
        # urlopen() itself -- and a 200 whose body isn't
        # valid JSON raises json.JSONDecodeError from json.loads() -- both
        # are attempt-level failures the retry loop must see and act on
        # the same as an HTTP error, not an unhandled crash out of
        # run_chat entirely (T3 fix round).
        try:
            with urllib.request.urlopen(req, timeout=http_timeout) as resp:
                response_json = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            last_error = f"HTTP {e.code}: {detail}"
            retryable = e.code == 429 or 500 <= e.code < 600
        except urllib.error.URLError as e:
            last_error = f"connection error: {e.reason}"
            retryable = True
        except TimeoutError as e:
            last_error = f"read timed out: {e}"
            retryable = True
        except json.JSONDecodeError as e:
            last_error = f"invalid JSON response: {e}"
            retryable = True
        if not retryable or attempt == max_attempts - 1:
            break
        time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
    wall_s = time.time() - start

    if response_json is None:
        return _fail(paths["results_dir"] + f"/{job_id}.json", last_error)

    choices = response_json.get("choices") or [{}]
    output = (choices[0].get("message") or {}).get("content", "")
    usage = response_json.get("usage", {})
    model = response_json.get("model", job["model"])
    resp_provider = response_json.get("provider")
    ts = time.time()
    result_path = os.path.join(paths["results_dir"], f"{job_id}.json")
    _write_result(
        result_path,
        {
            "output": output,
            "usage": usage,
            "model": model,
            "provider": resp_provider,
            "ts": ts,
        },
    )
    _append_ledger(
        paths["ledger_path"],
        {
            "ts": ts,
            "job": job_id,
            "kind": "chat",
            "model": model,
            "provider": resp_provider,
            "usage": usage,
            "wall_s": wall_s,
        },
    )
    return EXIT_OK


def run_agent(job, job_id, paths):
    result_path = os.path.join(paths["results_dir"], f"{job_id}.json")
    repo = job.get("repo")
    if not repo:
        return _fail(result_path, "agent job is missing 'repo'")

    # lane-submit.py lays a fresh per-job directory at
    # <jobs_dir>/<job-id>/ holding repo/ (the snapshot) and, from here,
    # config/ (a fresh CLAUDE_CONFIG_DIR) as siblings -- job["repo"] is
    # already the absolute "<jobdir>/repo" path lane-submit wrote, so the
    # job directory is just its parent.
    repo = os.path.normpath(repo)
    jobdir = os.path.dirname(repo)
    config_dir = os.path.join(jobdir, "config")
    os.makedirs(config_dir, exist_ok=True)
    # T3 fix round: lane-submit.py's --keep-snapshot (default off) is
    # carried on the job itself, not read from the environment, because
    # the decision belongs to whoever submitted the job, not to this
    # unit's config. Every branch below (success, claude failure, bad
    # output) reaches the `finally` -- a repo snapshot is job-specific
    # working state, not an audit artifact, so the default is to remove
    # it once the result is written rather than accumulate one per job
    # forever under /var/lib/lanes/<name>/jobs.
    keep_snapshot = bool(job.get("keep_snapshot"))

    try:
        host = os.environ["LANE_HOST"]
        env = dict(os.environ)
        env["ANTHROPIC_BASE_URL"] = f"https://{host}/api"
        # Dummy on purpose: the broker overwrites the Authorization header
        # for this host the same way it does for the chat path, so this
        # token is never actually presented anywhere.
        env["ANTHROPIC_AUTH_TOKEN"] = "lane-dummy-token"
        env.pop("ANTHROPIC_API_KEY", None)
        env["CLAUDE_CONFIG_DIR"] = config_dir

        max_turns = job.get("max_turns", 40)
        prompt = job.get("prompt", "")
        args = [
            "claude",
            "-p",
            prompt,
            "--model",
            job["model"],
            "--output-format",
            "json",
            "--max-turns",
            str(max_turns),
            "--permission-mode",
            "acceptEdits",
        ]

        start = time.time()
        try:
            proc = subprocess.run(
                args,
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return _fail(result_path, f"claude invocation failed: {e}")
        wall_s = time.time() - start

        if proc.returncode != 0:
            return _fail(
                result_path,
                f"claude exited {proc.returncode}: {proc.stderr[:2000]}",
            )

        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            return _fail(result_path, f"claude output was not JSON: {e}")

        output = parsed.get("result", parsed)
        usage = parsed.get("usage", {})
        model = job["model"]
        ts = time.time()
        _write_result(
            result_path,
            {
                "output": output,
                "usage": usage,
                "model": model,
                "provider": host,
                "ts": ts,
            },
        )
        _append_ledger(
            paths["ledger_path"],
            {
                "ts": ts,
                "job": job_id,
                "kind": "agent",
                "model": model,
                "provider": host,
                "usage": usage,
                "wall_s": wall_s,
            },
        )
        return EXIT_OK
    finally:
        if not keep_snapshot and os.path.isdir(repo):
            shutil.rmtree(repo, ignore_errors=True)


def _share_with_group(root):
    """Files the harness created belong to the DynamicUser (often 0600);
    give group `lane` read/write on everything we own so the submitter
    can read the outcome and apply the diff (directories keep setgid)."""
    me = os.getuid()
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames:
            p = os.path.join(dirpath, name)
            try:
                if os.lstat(p).st_uid == me and not os.path.islink(p):
                    os.chmod(p, 0o2770)
            except OSError:
                pass
        for name in filenames:
            p = os.path.join(dirpath, name)
            try:
                if os.lstat(p).st_uid == me and not os.path.islink(p):
                    os.chmod(p, 0o660)
            except OSError:
                pass


def _git_diff(repo):
    """Unified diff of the snapshot plus its untracked files, for the result."""
    try:
        diff = subprocess.run(
            ["git", "-C", repo, "diff"], capture_output=True, text=True, check=False
        ).stdout
        untracked = subprocess.run(
            ["git", "-C", repo, "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError as e:
        return f"(git unavailable: {e})"
    return diff + "\n## untracked\n" + untracked


def run_dsh(job, job_id, paths):
    """Run the DeepSeek Harness (dsh, pkgs/dsh) headless on the repo snapshot.

    Prototype (operator, 2026-09-03): the harness's own sandbox is switched
    off (DSH_PERMISSION_MODE=danger-full-access) because the systemd unit
    this runs in IS the sandbox -- own netns with the broker as the only
    route, DynamicUser, read-only filesystem, local-only trees inaccessible.
    dsh's approval seam would otherwise deny every tool in headless mode.
    The model route is a per-job --patch overlay: an OpenAI-compatible
    provider at https://<lane host>/api/v1 whose credential reference is
    an env var holding a dummy value -- the broker injects the real key.
    """
    result_path = os.path.join(paths["results_dir"], f"{job_id}.json")
    repo = job.get("repo")
    if not repo:
        return _fail(result_path, "dsh job is missing 'repo'")
    repo = os.path.normpath(repo)
    jobdir = os.path.dirname(repo)
    dsh_home = os.path.join(jobdir, "dsh-home")
    os.makedirs(dsh_home, exist_ok=True)
    keep_snapshot = bool(job.get("keep_snapshot"))
    model = job["model"]
    host = os.environ["LANE_HOST"]
    key_env = job.get("api_key_env", "OPENROUTER_API_KEY")
    overlay_path = os.path.join(jobdir, "lane-provider.yml")
    overlay = (
        "- id: llm-pi-ai\n"
        "  config:\n"
        "    providers:\n"
        "      lane:\n"
        "        api: openai-completions\n"
        f"        baseURL: https://{host}/api/v1\n"
        f"        apiKeyEnv: {key_env}\n"
        "        models:\n"
        f"          - id: {model}\n"
        f"            contextWindow: {int(job.get('context_window', 262144))}\n"
        "- id: agent-default-model\n"
        "  config:\n"
        "    provider: lane\n"
        f"    model: {model}\n"
        "- id: tool-web\n"
        "  disabled: true\n"
    )
    with open(overlay_path, "w", encoding="utf-8") as f:
        f.write(overlay)

    try:
        env = dict(os.environ)
        env["DSH_HOME"] = dsh_home
        # The unit runs as a DynamicUser with no usable HOME; git and nix want
        # one, and the snapshot is owned by the submitter, which git 2.35+
        # refuses ("dubious ownership") unless told otherwise -- scoped to
        # this process tree, never written to any config file.
        home = os.path.join(jobdir, "home")
        os.makedirs(home, exist_ok=True)
        env["HOME"] = home
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "safe.directory"
        env["GIT_CONFIG_VALUE_0"] = "*"
        os.environ.update(
            {
                k: env[k]
                for k in ("GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0")
            }
        )
        env["DSH_TELEMETRY_MODE"] = "DISABLED"
        env["DSH_PERMISSION_MODE"] = "danger-full-access"
        env[key_env] = "lane-dummy-key"  # overwritten by the broker for this host
        prompt = job.get("prompt", "")
        args = ["dsh", "--profile", "headless", "--patch", overlay_path, prompt]
        start = time.time()
        try:
            proc = subprocess.run(
                args,
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=int(job.get("timeout_s", 1800)),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return _fail(result_path, f"dsh invocation failed: {e}")
        wall_s = time.time() - start
        ts = time.time()
        _share_with_group(repo)
        record = {
            "output": proc.stdout,
            "exit": proc.returncode,
            "log": proc.stderr[-4000:],
            "diff": _git_diff(repo),
            "model": model,
            "provider": host,
            "ts": ts,
        }
        if proc.returncode != 0:
            record["error"] = f"dsh exited {proc.returncode}"
        _write_result(result_path, record)
        _append_ledger(
            paths["ledger_path"],
            {
                "ts": ts,
                "job": job_id,
                "kind": "dsh",
                "model": model,
                "provider": host,
                "exit": proc.returncode,
                "wall_s": wall_s,
            },
        )
        return EXIT_OK if proc.returncode == 0 else EXIT_ERROR
    finally:
        if not keep_snapshot and os.path.isdir(repo):
            shutil.rmtree(repo, ignore_errors=True)


def main(argv):
    if len(argv) != 3:
        print("usage: lane-run <lane> <job-id>", file=sys.stderr)
        return EXIT_USAGE
    lane, job_id = argv[1], argv[2]
    paths = _lane_paths(lane)
    job_path = os.path.join(paths["jobs_dir"], f"{job_id}.json")
    result_path = os.path.join(paths["results_dir"], f"{job_id}.json")

    try:
        with open(job_path, encoding="utf-8") as f:
            job = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return _fail(result_path, f"cannot read job {job_path}: {e}")

    # Belt-and-braces class check (nixosModules/modelLane.nix already
    # refuses allowedClasses outside ["permitted"] at build time -- this is
    # the runtime backstop, checked two ways: the job's own class must be
    # exactly "permitted", AND it must be one this lane was actually
    # configured to accept).
    job_class = job.get("class")
    allowed_classes = {c for c in os.environ.get("LANE_CLASSES", "").split(",") if c}
    if job_class != "permitted" or job_class not in allowed_classes:
        return _refuse(
            result_path,
            f"class '{job_class}' is not permitted for lane '{lane}'",
        )

    kind = job.get("kind")
    try:
        if kind == "chat":
            return run_chat(job, job_id, paths)
        if kind == "dsh":
            return run_dsh(job, job_id, paths)
        if kind == "agent":
            return run_agent(job, job_id, paths)
        return _fail(result_path, f"unknown job kind '{kind}'")
    except Exception as e:  # noqa: BLE001 - every outcome must leave a result
        # Last-resort backstop (T3 fix round; brief §7's acceptance
        # contract: every terminal outcome writes a result). A crash
        # inside dispatch -- a job file missing a field run_chat/run_agent
        # assumes is present, an exception type neither retry loop
        # anticipates -- used to leave the operator with nothing but a
        # bare traceback in the unit's journal and no results/<id>.json
        # for lane-wait to ever find; caught here instead, so the crash is
        # still a normal (if unhappy) result.
        return _fail(result_path, f"crash in {kind} dispatch: {type(e).__name__}: {e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
