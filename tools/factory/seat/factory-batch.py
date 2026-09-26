#!/usr/bin/env python3
"""factory-batch -- submit, poll and fetch a batch on the OpenRouter lane.

Three verbs over the batch endpoint FA2 measured in
docs/research-2026-09-11-batch-lane.md:84-131, reached only through the lane's
proxy (the environment's ``https_proxy``) and never carrying a credential --
this tool holds none, the lane injects the credential-bearing header:

    factory-batch submit REQUESTS.json --model ID [--window 24h]
    factory-batch poll ID [--until-terminal --interval S --timeout S]
    factory-batch fetch ID --out DIR

``submit`` posts ``{"requests": [...], "model": ID, "completion_window": W}``
to ``/api/beta/batches`` and prints ``<id> <status>`` on a 202; any other
status is refused (exit 2) with the response body's first 200 bytes. ``poll``
prints ``<status> <completed>/<total>`` and maps ``validating``/``in_progress``/
``completed`` to exit 0, ``failed``/``expired``/``cancelled`` to exit 3; a
non-2xx GET is not a batch status and exits 2 (a 5xx is retried up to three
times at ``--interval`` before that exit). ``fetch`` waits for a terminal batch
and writes one ``DIR/<custom_id>.json`` per 200 result (``response.body``) plus
``DIR/batch.json``, separating a non-200 result as ``DIR/<custom_id>.error.json``
and exiting 3 when any are present.

The base URL is ``$FACTORY_BATCH_BASE`` (default ``https://openrouter.ai``);
with the default base and no ``https_proxy`` the tool refuses before dialing
out untunnelled (invariant 3). Stdlib only (urllib.request, json, argparse).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import tomllib

DEFAULT_BASE = "https://openrouter.ai"
DEFAULT_WINDOW = "24h"
DEFAULT_INTERVAL = 30.0
DEFAULT_TIMEOUT = 86400.0
FETCH_POLL_INTERVAL = 0.5

SEAT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SEAT_DIR)))

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_BAD_BATCH = 3
EXIT_TIMEOUT = 4

TERMINAL = ("completed", "failed", "expired", "cancelled")
BAD_TERMINAL = ("failed", "expired", "cancelled")

# A server-chosen custom_id is untrusted: it must be one basename -- letters
# and digits first, then those plus `._-`, at most 128 characters, matched
# against the WHOLE id (`re.fullmatch`, so a trailing newline is refused too).
# This bars `/`, a leading `..`, an absolute path, and a stray newline from
# ever reaching os.path.join.
CUSTOM_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


def _proxy():
    return os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or ""


def _base_url():
    return os.environ.get("FACTORY_BATCH_BASE") or DEFAULT_BASE


def _ensure_lane():
    """Return None to proceed, else the exit code for the lane-only refusal."""
    if _base_url() == DEFAULT_BASE and not _proxy():
        sys.stderr.write(
            "factory-batch: refusing -- no lane proxy in the environment"
            " (invariant 3)\n"
        )
        return EXIT_USAGE
    return None


def _opener():
    proxy = _proxy()
    if not proxy:
        return urllib.request.build_opener()
    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    return urllib.request.build_opener(handler)


def _submit(args):
    refuse = _ensure_lane()
    if refuse is not None:
        return refuse
    with open(args.requests_json, encoding="utf-8") as f:
        requests = json.load(f)
    payload = {
        "requests": requests,
        "model": args.model,
        "completion_window": args.window,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _base_url() + "/api/beta/batches",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with _opener().open(req, timeout=60) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        sys.stderr.write(f"factory-batch: {e.reason}\n")
        return EXIT_USAGE
    if status != 202:
        sys.stderr.write(body[:200] + "\n")
        return EXIT_USAGE
    obj = json.loads(body)
    sys.stdout.write(f"{obj.get('id')} {obj.get('status')}\n")
    return EXIT_OK


def _get(url, interval):
    """One GET, returning (status_code, body_text); a 5xx retries up to three times."""
    req = urllib.request.Request(
        url, method="GET", headers={"Accept": "application/json"}
    )
    for attempt in range(4):
        try:
            with _opener().open(req, timeout=60) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            code = e.code
            body = e.read().decode("utf-8", "replace")
            if 500 <= code < 600 and attempt < 3:
                time.sleep(interval)
                continue
            return code, body
        except urllib.error.URLError as e:
            return 0, f"connection error: {e.reason}"
    return 0, "unreachable"


def _parse_status(body):
    obj = json.loads(body)
    counts = obj.get("request_counts") or {}
    return obj.get("status"), counts.get("completed", 0), counts.get("total", 0)


def _not_a_batch(batch_id, code, body):
    sys.stderr.write(f"factory-batch: GET /api/beta/batches/{batch_id} -> {code}\n")
    sys.stderr.write((body or "")[:200] + "\n")
    return EXIT_USAGE


def _poll(args):
    refuse = _ensure_lane()
    if refuse is not None:
        return refuse
    url = f"{_base_url()}/api/beta/batches/{args.id}"
    if not args.until_terminal:
        code, body = _get(url, args.interval)
        if not 200 <= code < 300:
            return _not_a_batch(args.id, code, body)
        status, completed, total = _parse_status(body)
        sys.stdout.write(f"{status} {completed}/{total}\n")
        return EXIT_BAD_BATCH if status in BAD_TERMINAL else EXIT_OK

    deadline = time.time() + args.timeout
    while True:
        code, body = _get(url, args.interval)
        if not 200 <= code < 300:
            return _not_a_batch(args.id, code, body)
        status, completed, total = _parse_status(body)
        if status in TERMINAL:
            sys.stdout.write(f"{status} {completed}/{total}\n")
            return EXIT_OK if status == "completed" else EXIT_BAD_BATCH
        if time.time() >= deadline:
            return EXIT_TIMEOUT
        time.sleep(args.interval)


def _result_path(custom_id, out_dir, suffix):
    """Return the write path for one result, or None after refusing the id.

    ``custom_id`` is server-chosen and therefore hostile by default: it must
    match ``CUSTOM_ID_RE`` over its whole length (one basename, no ``/``, no
    ``..``, not absolute, no trailing newline), and even then the joined
    path's realpath must begin with the realpath of ``--out`` (defends a
    symlink planted *inside* ``--out`` that points outside). On refusal the
    id is named on stderr and nothing is written.
    """
    if not CUSTOM_ID_RE.fullmatch(custom_id):
        sys.stderr.write(f"factory-batch: refusing result custom_id {custom_id!r}\n")
        return None
    path = os.path.join(out_dir, f"{custom_id}.{suffix}")
    if not os.path.realpath(path).startswith(os.path.realpath(out_dir) + os.sep):
        sys.stderr.write(f"factory-batch: refusing result custom_id {custom_id!r}\n")
        return None
    return path


def _fetch(args):
    refuse = _ensure_lane()
    if refuse is not None:
        return refuse
    url = f"{_base_url()}/api/beta/batches/{args.id}"
    while True:
        code, body = _get(url, FETCH_POLL_INTERVAL)
        if not 200 <= code < 300:
            return _not_a_batch(args.id, code, body)
        obj = json.loads(body)
        if obj.get("status") in TERMINAL:
            break
        time.sleep(FETCH_POLL_INTERVAL)

    # Refuse every hostile custom_id before creating --out or writing a byte.
    results = obj.get("results") or []
    paths = []
    error_count = 0
    for result in results:
        custom_id = result.get("custom_id") or "unknown"
        response = result.get("response") or {}
        if response.get("status_code") == 200:
            suffix = "json"
        else:
            error_count += 1
            suffix = "error.json"
        path = _result_path(custom_id, args.out, suffix)
        if path is None:
            return EXIT_BAD_BATCH
        paths.append(path)

    os.makedirs(args.out, exist_ok=True)
    for result, path in zip(results, paths):
        result_body = (result.get("response") or {}).get("body")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result_body, f)
    with open(os.path.join(args.out, "batch.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return EXIT_OK if error_count == 0 else EXIT_BAD_BATCH


def _build_parser():
    parser = argparse.ArgumentParser(prog="factory-batch")
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit", help="post a batch of requests")
    submit.add_argument("requests_json")
    submit.add_argument("--model", required=True)
    submit.add_argument("--window", default=DEFAULT_WINDOW)

    poll = sub.add_parser("poll", help="poll one batch")
    poll.add_argument("id")
    poll.add_argument("--until-terminal", action="store_true")
    poll.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    poll.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)

    fetch = sub.add_parser("fetch", help="fetch the results of a batch")
    fetch.add_argument("id")
    fetch.add_argument("--out", required=True)

    node = sub.add_parser(
        "node", help="one synchronous batch request (a graph tool node)"
    )
    node.add_argument("--role", required=True)
    node.add_argument("input")
    return parser


def _resolve_node_role(role):
    """The registry row for a node role: (model, prompt, schema) or (None,)*3.

    Model and effort come from `factory-registry.py resolve` (FA13.1), the
    prompt file and artifact schema from the registry row itself. An
    unresolvable role prints one line on stderr and returns None so the caller
    exits 2 before any request exists (Interface 7a).
    """
    proc = subprocess.run(
        [
            sys.executable,
            os.path.join(SEAT_DIR, "factory-registry.py"),
            "resolve",
            role,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    parts = proc.stdout.split()
    if len(parts) < 2:
        err = proc.stderr.strip() or f"registry: {role}: unresolvable"
        sys.stderr.write(f"factory-batch: {err}\n")
        return None, None, None
    model = parts[0]
    with open(os.path.join(REPO_ROOT, "tools", "factory", "agents.toml"), "rb") as fh:
        data = tomllib.load(fh)
    for row in data.get("agent", []):
        if row.get("name") == role:
            return model, row.get("prompt"), row.get("schema")
    sys.stderr.write(f"factory-batch: registry: {role}: no such role\n")
    return None, None, None


def _node_prompt(prompt_path, input_doc, schema, inputs):
    """The node brief: the prompt file verbatim, the input artifact fenced,
    every file the artifact's `inputs` names as a fenced block headed by its
    name (a fresh draft: block, spec; a revision: those plus the prior draft
    and the tally's errata), then the schema-kind sentence (FA16 Interface 3).
    """
    parts = []
    if prompt_path:
        p = os.path.join(REPO_ROOT, prompt_path)
        try:
            with open(p, encoding="utf-8") as fh:
                parts.append(fh.read())
        except OSError:
            pass
    parts.append("```json\n" + json.dumps(input_doc, sort_keys=True) + "\n```")
    for name, path in inputs.items():
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            content = ""
        parts.append(f"# {name}\n```\n{content}\n```")
    errata = input_doc.get("errata") if isinstance(input_doc, dict) else None
    if errata:
        parts.append("errata:\n" + json.dumps(errata, sort_keys=True))
    parts.append(
        f"Answer with one fenced JSON block of kind {schema} that "
        "factory-artifact.py check accepts, then the FACTORY-RESULT lines."
    )
    return "\n\n".join(parts)


def _broken_artifact(schema, key, node, rung, inputs, errata):
    """A broken artifact (verdict broken, exactly one erratum) that check accepts."""
    return {
        "kind": schema,
        "key": key,
        "node": node,
        "rung": rung,
        "claims": [],
        "repro": None,
        "errata": [errata],
        "verdict": "broken",
        "inputs": inputs,
        "scores": None,
        "wrong_facts": None,
    }


def _block_check(merged, run_dir):
    """The first fault from factory-artifact.py check on the merged artifact, or None."""
    fd, tmp = tempfile.mkstemp(prefix="node-", suffix=".json", dir=run_dir)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(merged, fh)
        fh.write("\n")
    proc = subprocess.run(
        [sys.executable, os.path.join(SEAT_DIR, "factory-artifact.py"), "check", tmp],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        os.unlink(tmp)
    except OSError:
        pass
    if proc.returncode == 0:
        return None
    out = proc.stdout.strip()
    return out.splitlines()[0] if out else "bad artifact"


def _node(args):
    """One synchronous batch request around the asynchronous endpoint (decision 30b).

    The wrapper a `tool` node needs: resolve the role, submit ONE request
    (`custom_id = <key>-<FACTORY_NODE>-<epoch>`), poll to a terminal status and
    fetch, then turn the completion body's first fenced JSON block into the
    artifact the way FA16 Interface 4 does. Every failure after a request
    exists is `verdict = "broken"` with exactly one erratum and exit 0 (the
    runner's verdict alone is `exhausted`, FA15 Interface 3); a non-zero exit
    happens only before a request exists (the registry refusal or FA20
    Interface 5's missing proxy), which FA16 Interface 5 turns into `broken`
    with the stderr tail.
    """
    role = args.role
    refuse = _ensure_lane()
    if refuse is not None:
        return refuse
    model, prompt_path, schema = _resolve_node_role(role)
    if model is None:
        return EXIT_USAGE

    node = os.environ.get("FACTORY_NODE", role)
    rung = int(os.environ.get("FACTORY_RUNG", "1"))
    run_dir = os.environ.get("FACTORY_RUN_DIR", ".")

    input_doc = {}
    try:
        with open(args.input, encoding="utf-8") as fh:
            input_doc = json.load(fh)
    except (OSError, json.JSONDecodeError):
        input_doc = {}
    if not isinstance(input_doc, dict):
        input_doc = {}
    key = input_doc.get("key", "plan")
    inputs = dict(input_doc.get("inputs") or {})

    def broken(errata):
        return json.dumps(
            _broken_artifact(schema, key, node, rung, inputs, errata),
            sort_keys=True,
        )

    prompt_text = _node_prompt(prompt_path, input_doc, schema, inputs)
    custom_id = f"{key}-{node}-{int(time.time())}"
    requests = [
        {
            "custom_id": custom_id,
            "body": {
                "model": model,
                "messages": [{"role": "user", "content": prompt_text}],
            },
        }
    ]

    # submit
    payload = {
        "requests": requests,
        "model": model,
        "completion_window": DEFAULT_WINDOW,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _base_url() + "/api/beta/batches",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with _opener().open(req, timeout=60) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        sys.stderr.write(f"factory-batch: {e.reason}\n")
        return EXIT_USAGE
    if status != 202:
        print(broken(f"batch submit: HTTP {status}"))
        return EXIT_OK
    obj = json.loads(body)
    batch_id = obj.get("id", "")

    # poll to a terminal status
    interval = float(os.environ.get("FACTORY_BATCH_INTERVAL", str(DEFAULT_INTERVAL)))
    timeout = float(os.environ.get("FACTORY_BATCH_TIMEOUT", str(DEFAULT_TIMEOUT)))
    deadline = time.time() + timeout
    url = f"{_base_url()}/api/beta/batches/{batch_id}"
    while True:
        code, body = _get(url, interval)
        if not 200 <= code < 300:
            print(broken(f"batch {batch_id}: HTTP {code}"))
            return EXIT_OK
        status, _, _ = _parse_status(body)
        if status in TERMINAL:
            obj = json.loads(body)
            if status != "completed":
                print(broken(f"batch {batch_id}: {status}"))
                return EXIT_OK
            break
        if time.time() >= deadline:
            print(broken(f"batch {batch_id}: timeout after {timeout:g} s"))
            return EXIT_OK
        time.sleep(interval)

    # fetch: write the single result and the batch object (FA22 reads batch.json)
    results = obj.get("results") or []
    if not results:
        print(broken("no artifact block in the batch result"))
        return EXIT_OK
    result = results[0]
    rid = result.get("custom_id") or "unknown"
    response = result.get("response") or {}
    status_code = response.get("status_code")
    if status_code != 200:
        print(broken(f"batch {batch_id}: {rid}: HTTP {status_code}"))
        return EXIT_OK
    out_dir = os.path.join(run_dir, f"batch-{custom_id}")
    path = _result_path(rid, out_dir, "json")
    if path is None:
        print(broken(f"batch {batch_id}: {rid}: HTTP {status_code}"))
        return EXIT_OK
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(response.get("body"), fh)
    with open(os.path.join(out_dir, "batch.json"), "w", encoding="utf-8") as fh:
        json.dump(obj, fh)
    first_body = response.get("body")

    # the completion body's content carries the model's answer
    content = ""
    if isinstance(first_body, dict):
        choices = first_body.get("choices")
        if isinstance(choices, list) and choices:
            content = choices[0].get("message", {}).get("content", "")

    match = re.search(r"```(?:json)?[ \t]*\n(.*?)\n```", content, re.DOTALL)
    doc = None
    if match:
        try:
            doc = json.loads(match.group(1))
        except json.JSONDecodeError:
            doc = None
    if not isinstance(doc, dict):
        print(broken("no artifact block in the batch result"))
        return EXIT_OK

    free_text = (content[: match.start()] + content[match.end() :]).strip()
    merged_inputs = dict(inputs)
    if schema == "attempt":
        draft_path = os.path.join(run_dir, f"{custom_id}.md")
        with open(draft_path, "w", encoding="utf-8") as fh:
            fh.write(free_text + "\n")
        merged_inputs["draft"] = draft_path

    if schema == "verdict" and (
        doc.get("scores") is None or doc.get("wrong_facts") is None
    ):
        print(broken("judge block lacks scores"))
        return EXIT_OK

    merged = {
        "kind": schema,
        "key": key,
        "node": node,
        "rung": rung,
        "claims": doc.get("claims", []) if isinstance(doc.get("claims"), list) else [],
        "repro": doc.get("repro"),
        "errata": doc.get("errata", []) if isinstance(doc.get("errata"), list) else [],
        "verdict": doc.get("verdict"),
        "inputs": merged_inputs,
        "scores": doc.get("scores"),
        "wrong_facts": doc.get("wrong_facts"),
    }

    fault = _block_check(merged, run_dir)
    if fault is not None:
        print(broken(f"batch result: {fault}"))
        return EXIT_OK

    print(json.dumps(merged, sort_keys=True))
    return EXIT_OK


def main(argv=None):
    args = _build_parser().parse_args(argv)
    if args.command == "submit":
        return _submit(args)
    if args.command == "poll":
        return _poll(args)
    if args.command == "fetch":
        return _fetch(args)
    if args.command == "node":
        return _node(args)
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
