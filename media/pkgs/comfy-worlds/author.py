r"""comfy-author: verdicts to the loopback model, validated batches to lab/prompts.

Spec §4 Change 2. The author reads the world's two verdict windows (the
newest K liked prompt texts, extracted from the renders' graphs exactly as
the feed page extracts them, and the newest K disliked texts, stored inline
by GN13's POST /dislike), asks the loopback model for M new base prompts,
validates the reply against the world's `[author]` table in
`lab/manifest.toml`, and writes one batch file under `lab/prompts/` for
GN15's `comfy-mutate --seed-file` to expand.

Seams (the FEED_INDEX_PY pattern): `feed_index.py` is loaded by path for
`open_db` and `feed.py` for the graph helpers `_parse_graph` /
`_positive_text` — the comfy-author wrapper exports FEED_INDEX_PY and
FEED_SERVE_PY (feed.py's own module) and the siblings are the in-tree
fallbacks for the unit tests. Neither is inferred from a sibling path at
runtime; the wrapper states both.

Exit grammar, total and disjoint (GN17 depends on it):

- **0** — a batch was written; the last stdout line is
  `authored <n> <path>` with `n >= 1` (an exit 0 never carries zero
  prompts).
- **3** — every empty outcome: the model never became available within
  `--model-wait` (a refused/reset connection, or a retryable HTTP status
  — 408, 429, any 5xx: a llama-server still loading its weights answers
  503 `{"message":"Loading model"}`), one request's read timeout
  expired while a live model was still generating (`--model-timeout`,
  default 300 s — TERMINAL, never retried: retrying discards the
  generating task and starts a new one; measured on core, 2026-09-18,
  six discarded tasks in one 120 s window at 60 tok/s), a fatal HTTP
  status (any other 4xx), a reply that was not a JSON array of strings,
  or 0 prompts survived validation after the one retry. The cause is one
  named stderr line; the last stdout line is
  `authored 0 prompts in <world>`.
- **2** — bad invocation: a non-loopback `--model-url` (the model is
  local inference on loopback, never a broker instance), a missing
  `[author]` table or brief, an unreadable world root.

Stdlib only (`urllib.request`, `json`, `sqlite3` via feed_index,
`tomllib`); the one socket opened is the POST to the loopback model URL.

Two budgets, kept apart (GN21): `--model-wait` is how long to wait for
a server that does not EXIST yet (refused/reset, retryable statuses);
`--model-timeout` is how long a LIVE server may think per request. The
first is retried; the second is terminal.

GN51: `--stacks-file` hands the supervisor's coupled draw (GN50's
`--draw-stacks` output) to the author — the ask names each slot's
`requires` words, a reply that misses one is retried once and then
accepted with the miss recorded in the batch (`misses` — a miss is
never an exit; spec §4), the liked window's leading `[[model]]`
triggers are scrubbed (§3.3: the author should not be asked to
reproduce `f1lson,`), and the batch carries the verbatim `stacks`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import re
import sys
import time
import tomllib
import urllib.error
import urllib.request
from urllib.parse import urlparse

_HERE = pathlib.Path(__file__).resolve().parent

# feed_index.py is a sibling in the source tree but a separate store path
# once packaged: the wrapper sets FEED_INDEX_PY (the seam comfy-feed and
# comfy-mutate already read), and the sibling is the fallback for the
# in-tree unit tests. author.py loads it for `open_db`.
_index_path = os.environ.get("FEED_INDEX_PY") or str(_HERE / "feed_index.py")
_index_spec = importlib.util.spec_from_file_location("feed_index", _index_path)
feed_index = importlib.util.module_from_spec(_index_spec)
_index_spec.loader.exec_module(feed_index)

# The graph helpers live in feed.py (also a sibling / separate store path):
# the wrapper additionally exports FEED_SERVE_PY pointing at it, and
# author.py loads it for `_parse_graph` / `_positive_text` — the same pair
# the feed page uses to show a render's positive prompt text.
_feed_path = os.environ.get("FEED_SERVE_PY") or str(_HERE / "feed.py")
_feed_spec = importlib.util.spec_from_file_location("feed_serve", _feed_path)
feed_serve = importlib.util.module_from_spec(_feed_spec)
_feed_spec.loader.exec_module(feed_serve)

# The transport retry interval: a refused/reset connection is retried every
# 2 s until --model-wait elapses (the model unit may still be waking).
_RETRY_SECONDS = 2.0

_OUTPUT_CONTRACT = (
    "Reply with only a JSON array of exactly the requested number of"
    " prompt strings — no prose, no explanation, no code fence."
)


def _parse_args(argv):
    parser = argparse.ArgumentParser(prog="comfy-author")
    parser.add_argument("--world", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--n", type=int, required=True, help="prompts per batch (M)")
    parser.add_argument(
        "--model-url",
        required=True,
        help="the loopback model URL (http://127.0.0.1:<port>)",
    )
    parser.add_argument(
        "--window", type=int, default=20, help="verdict window K (likes + dislikes)"
    )
    parser.add_argument(
        "--history",
        type=int,
        default=3,
        help="prior authored batches checked for duplicate prompts",
    )
    parser.add_argument(
        "--model-wait",
        type=int,
        default=120,
        help="seconds to keep retrying a server that does not exist yet"
        " (refused/reset connection, retryable status) before exiting 3",
    )
    parser.add_argument(
        "--model-timeout",
        type=int,
        default=300,
        help="per-request read timeout: a live model may think this long"
        " before the request is abandoned (terminal, never retried)",
    )
    parser.add_argument("--model-path", default=None, help="recorded in the batch file")
    parser.add_argument("--model-sha256", default=None, help="recorded in the batch")
    parser.add_argument(
        "--stacks-file",
        default=None,
        help="GN50's coupled draw output: the stacks this batch is"
        " written for (each slot's requires words reach the ask)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the prompts, write no file"
    )
    return parser.parse_args(argv)


def _check_model_url(url):
    """The model is loopback-only (invariant 3): scheme http, host 127.0.0.1."""
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        print(
            f"comfy-author: the model URL must be loopback"
            f" (http://127.0.0.1:<port>), got {url}",
            file=sys.stderr,
        )
        sys.exit(2)


def _load_author_table(path):
    """The `[author]` table of the world's lab manifest: brief (required),
    required / banned substrings, minLen / maxLen — plus (GN51) `triggers`,
    the set of `trigger` values of every `[[model]]` row that carries one.
    A missing table or brief exits 2 naming the file — the operator pastes
    this table (G13's second declared exception); a silent default brief
    would hide that."""
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print(f"comfy-author: cannot read {path}: {exc.strerror}", file=sys.stderr)
        sys.exit(2)
    except tomllib.TOMLDecodeError as exc:
        print(f"comfy-author: {path}: not valid TOML ({exc})", file=sys.stderr)
        sys.exit(2)
    table = data.get("author")
    if (
        not isinstance(table, dict)
        or not isinstance(table.get("brief"), str)
        or not table["brief"]
    ):
        print(
            f"comfy-author: no [author] table with a brief in {path}", file=sys.stderr
        )
        sys.exit(2)
    models = data.get("model")
    if not isinstance(models, list):
        models = []
    triggers = {
        row["trigger"]
        for row in models
        if isinstance(row, dict) and isinstance(row.get("trigger"), str)
    }
    return {
        "brief": table["brief"],
        "required": list(table.get("required", [])),
        "banned": list(table.get("banned", [])),
        "minLen": int(table.get("minLen", 20)),
        "maxLen": int(table.get("maxLen", 1000)),
        "triggers": triggers,
    }


def _load_stacks(path, n):
    """GN50's stacks file (`--stacks-file`): the draw the author is told
    about. Not that shape, or a count that disagrees with `--n`, is a bad
    invocation (exit 2) — a draw made for a different batch size is never
    a POST."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        print(f"comfy-author: {path} is not a stacks file", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict) or not isinstance(data.get("stacks"), list):
        print(f"comfy-author: {path} is not a stacks file", file=sys.stderr)
        sys.exit(2)
    if len(data["stacks"]) != n:
        print(
            f"comfy-author: {path} carries {len(data['stacks'])} stacks for --n {n}",
            file=sys.stderr,
        )
        sys.exit(2)
    return data["stacks"]


def _scrub_triggers(text, triggers):
    """Drop every leading trigger (GN51, §3.3: the author should not be
    asked to reproduce `f1lson,`): while the text starts with some
    manifest `[[model]]` trigger followed by a space — or equals it —
    drop that prefix and left-strip. A text with no trigger prefix is
    verbatim."""
    while True:
        for trigger in triggers:
            if text == trigger:
                return ""
            if text.startswith(trigger + " "):
                text = text[len(trigger) :].lstrip()
                break
        else:
            return text


def _liked_window(conn, window, triggers):
    """`(names, texts)` of the newest `window` liked renders, each text the
    render's positive prompt extracted exactly as the feed page extracts
    it, minus its leading triggers (GN51: the model never reads a
    trigger). A liked render that yields no text is skipped with one
    stderr line."""
    names, texts = [], []
    rows = conn.execute(
        "SELECT r.name, r.prompt FROM likes l"
        " JOIN renders r ON l.name = r.name"
        " ORDER BY l.liked_at DESC LIMIT ?",
        (window,),
    )
    for row in rows:
        graph = feed_serve._parse_graph(row["prompt"])
        text = feed_serve._positive_text(graph) if graph is not None else None
        if text is None:
            print(
                f"comfy-author: {row['name']}: skipped (no positive text)",
                file=sys.stderr,
            )
            continue
        text = _scrub_triggers(text, triggers)
        names.append(row["name"])
        texts.append(text)
    return names, texts


def _disliked_window(conn, window):
    """`(names, texts)` of the newest `window` dislikes — the inline prompt
    text GN13 recorded, no join needed."""
    names, texts = [], []
    rows = conn.execute(
        "SELECT name, prompt FROM dislikes ORDER BY disliked_at DESC LIMIT ?",
        (window,),
    )
    for row in rows:
        names.append(row["name"])
        texts.append(row["prompt"])
    return names, texts


def _user_message(liked, disliked, n, slot_requires=None):
    """The ask: the two verdict windows, the exact count, then (GN51) one
    line per slot whose drawn stack carries `requires` words — the words
    the reply is written in (spec §3.3). Slots without requires add no
    line."""
    lines = ["liked prompts, newest first:"]
    lines += [f"- {text}" for text in liked]
    lines.append("")
    lines.append("disliked prompts, newest first:")
    lines += [f"- {text}" for text in disliked]
    lines.append("")
    lines.append(f"Write exactly {n} new base prompts for this world's generator.")
    if slot_requires is not None:
        for i, requires in enumerate(slot_requires):
            if requires:
                words = "; ".join(requires)
                lines.append(f"Prompt {i + 1} must contain the words: {words}")
    return "\n".join(lines)


def _post(model_url, payload, timeout):
    """One POST to the model's OpenAI-compatible chat route. `timeout` is
    the per-request READ timeout (GN21): the model's thinking budget, not
    the wait budget — a live server may think this long before the
    request is abandoned."""
    request = urllib.request.Request(
        model_url + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def _fail3(args, message):
    print(message, file=sys.stderr)
    print(f"authored 0 prompts in {args.world}")
    sys.exit(3)


def _post_with_wait(args, payload):
    """One POST, with the two GN21 budgets kept apart.

    `--model-wait` is the WAIT budget — how long to keep retrying when
    the server does not exist yet. Two stalls fall under it: a
    refused/reset connection (the model unit may still be waking) and a
    retryable HTTP status — 408, 429 or any 5xx, because a llama-server
    still loading its weights answers 503 `{"message":"Loading model"}`
    (measured on core, 2026-09-18), which is exactly the wake the wait
    exists for. Every other 4xx is a bad request, not a stall: no retry,
    the status and the first 200 bytes of the body go to stderr, exit 3.

    `--model-timeout` is the READ timeout — how long a LIVE server may
    think per request. A `TimeoutError` raised after the connection
    succeeded is TERMINAL, never retried: retrying a generating request
    discards its work and starts a new task (measured on core,
    2026-09-18: the server was generating at 60 tok/s when the
    supervisor tore it down, six discarded tasks in one 120 s window).
    A connect-phase timeout stays under the wait budget — it arrives
    wrapped in `URLError`, which keeps the retry arm below.
    """
    deadline = time.monotonic() + args.model_wait
    while True:
        try:
            return _post(args.model_url, payload, args.model_timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 408 or exc.code == 429 or 500 <= exc.code < 600:
                if time.monotonic() >= deadline:
                    _fail3(
                        args,
                        f"comfy-author: the model at {args.model_url} was"
                        f" still unavailable after {args.model_wait}s"
                        f" (last status {exc.code})",
                    )
                time.sleep(min(_RETRY_SECONDS, max(0.0, deadline - time.monotonic())))
                continue
            body = exc.read().decode("utf-8", "replace")
            _fail3(
                args,
                f"comfy-author: the model answered {exc.code} at"
                f" {args.model_url}: {body[:200]}",
            )
        except TimeoutError:
            # The connection succeeded and the model may still be
            # generating this batch. Retrying would throw its work away
            # and start a new task — the defect GN21 exists to close.
            _fail3(
                args,
                f"comfy-author: the model at {args.model_url} did not"
                f" answer within {args.model_timeout}s (it may still be"
                " generating; raise author.modelTimeout)",
            )
        except (urllib.error.URLError, ConnectionError, OSError):
            if time.monotonic() >= deadline:
                _fail3(
                    args,
                    f"comfy-author: no answer from the model at {args.model_url}"
                    f" within {args.model_wait}s",
                )
            time.sleep(min(_RETRY_SECONDS, max(0.0, deadline - time.monotonic())))


def _reply_content(body_text):
    """`choices[0].message.content` of the reply body, or `None` when the
    body is not that shape."""
    try:
        body = json.loads(body_text)
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    if not isinstance(choices[0], dict):
        return None
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return content if isinstance(content, str) else None


def _strip_fence(text):
    """The reply minus one leading/trailing code fence, if present."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped
    lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


def _parse_prompts(content):
    """The reply as a list of prompt strings, or `None` when it is not a
    JSON array of strings (after fence stripping)."""
    try:
        data = json.loads(_strip_fence(content))
    except ValueError:
        return None
    if not isinstance(data, list) or any(not isinstance(p, str) for p in data):
        return None
    return data


def _prior_prompts(prompts_dir, history):
    """Every prompt of the newest `history` authored batch files."""
    if not prompts_dir.is_dir():
        return set()
    prior = set()
    for path in sorted(prompts_dir.glob("authored-*.json"), reverse=True)[:history]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get("prompts"), list):
            prior.update(p for p in data["prompts"] if isinstance(p, str))
    return prior


def _word_in(word: str, text: str) -> bool:
    """A whole-token match, case-insensitive — mutate.py's own rule
    (Decision 5), copied so the author and the mutator judge the same
    words the same way: `word` occurs in `text` bounded by
    non-alphanumerics on both sides, so "anal" is not "analog" and
    "kneeling" is "kneeling,"."""
    return (
        re.search(
            r"(?<![a-z0-9])" + re.escape(word.lower()) + r"(?![a-z0-9])",
            text.lower(),
        )
        is not None
    )


def _validate(prompts, cfg, prior, want, slot_requires=None):
    """Every rule the `[author]` table states, each failure a named cause —
    never a silent skip. Returns `(errors, misses)`: `errors` refuse the
    batch; `misses` (GN51) are the slots whose prompt, by index, lacks a
    required word of its drawn stack — soft, recorded in the batch, never
    an exit."""
    errors = []
    if len(prompts) != want:
        errors.append(f"expected exactly {want} prompts, got {len(prompts)}")
    for prompt in prompts:
        if not prompt:
            errors.append("an empty prompt")
            continue
        if not (cfg["minLen"] <= len(prompt) <= cfg["maxLen"]):
            errors.append(
                f"prompt length {len(prompt)} outside"
                f" {cfg['minLen']}..{cfg['maxLen']}: {prompt[:60]}"
            )
        for banned in cfg["banned"]:
            if banned in prompt:
                errors.append(f"banned substring {banned!r}: {prompt[:60]}")
        for required in cfg["required"]:
            if required not in prompt:
                errors.append(f"missing required substring {required!r}: {prompt[:60]}")
    if len(set(prompts)) != len(prompts):
        errors.append("duplicate prompts in the batch")
    for prompt in prompts:
        if prompt in prior:
            errors.append(f"prompt repeats a prior batch: {prompt[:60]}")
    misses = []
    if slot_requires is not None:
        for i, requires in enumerate(slot_requires):
            if i >= len(prompts):
                break
            missing = [w for w in requires if not _word_in(w, prompts[i])]
            if missing:
                misses.append([i, missing])
    return errors, misses


def _author_with_model(args, cfg, liked_texts, disliked_texts, slot_requires=None):
    """The round-trip: one POST, one retry carrying the complaint. Returns
    `(prompts, request payload, raw reply content, misses)` on success;
    exits 3 on every empty outcome. A requires miss is soft (GN51): the
    retry carries it back phrased `prompt <i+1> must contain: <w1>; <w2>`,
    and a miss that survives the retry is accepted and recorded — never
    an exit; an error beside it still refuses the batch."""
    prompts_dir = pathlib.Path(args.root) / "worlds" / args.world / "lab" / "prompts"
    prior = _prior_prompts(prompts_dir, args.history)
    base_user = _user_message(liked_texts, disliked_texts, args.n, slot_requires)
    system = cfg["brief"] + "\n\n" + _OUTPUT_CONTRACT
    complaint = None
    last_was_parse = False
    misses = []
    for attempt in (1, 2):
        user = base_user
        if complaint is not None:
            user = f"{base_user}\n\nYour previous reply was rejected:\n{complaint}"
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        }
        body = _post_with_wait(args, payload)
        content = _reply_content(body)
        prompts = _parse_prompts(content) if content is not None else None
        if content is None or prompts is None:
            print(
                f"comfy-author: attempt {attempt}: the model's reply was not"
                " a JSON array of strings",
                file=sys.stderr,
            )
            complaint = "the reply was not a JSON array of strings"
            last_was_parse = True
            continue
        errors, misses = _validate(prompts, cfg, prior, args.n, slot_requires)
        if not errors and not misses:
            return prompts, payload, content, misses
        for error in errors[:10]:
            print(f"comfy-author: attempt {attempt}: {error}", file=sys.stderr)
        for i, missing in misses:
            print(
                f"comfy-author: attempt {attempt}: prompt {i + 1} must"
                f" contain: {'; '.join(missing)}",
                file=sys.stderr,
            )
        if not errors and attempt == 2:
            # The retry still misses but breaks no rule: accepted, the
            # miss recorded in the batch (GN51 — a miss is never an exit).
            return prompts, payload, content, misses
        complaints = [
            f"prompt {i + 1} must contain: {'; '.join(missing)}"
            for i, missing in misses
        ]
        complaint = "; ".join(errors[:10] + complaints)
        last_was_parse = False
    if last_was_parse:
        _fail3(
            args,
            "comfy-author: the model's reply was not a JSON array of strings"
            " (2 attempts)",
        )
    _fail3(args, "comfy-author: 0 prompts survived validation (2 attempts)")


def main(argv=None):
    args = _parse_args(argv)
    _check_model_url(args.model_url)
    manifest = pathlib.Path(args.root) / "worlds" / args.world / "lab" / "manifest.toml"
    cfg = _load_author_table(str(manifest))
    stacks = None
    if args.stacks_file is not None:
        stacks = _load_stacks(args.stacks_file, args.n)
    try:
        conn = feed_index.open_db(args.root, args.world)
    except OSError as exc:
        print(
            f"comfy-author: cannot open the world {args.world} under"
            f" {args.root}: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)
    liked_names, liked_texts = _liked_window(conn, args.window, cfg["triggers"])
    disliked_names, disliked_texts = _disliked_window(conn, args.window)
    slot_requires = None
    if stacks is not None:
        slot_requires = [
            list(entry.get("requires", [])) if isinstance(entry, dict) else []
            for entry in stacks
        ]
    prompts, payload, content, misses = _author_with_model(
        args, cfg, liked_texts, disliked_texts, slot_requires
    )
    if args.dry_run:
        for prompt in prompts:
            print(prompt)
        print(f"authored {len(prompts)} prompts (dry run)")
        return
    prompts_dir = pathlib.Path(args.root) / "worlds" / args.world / "lab" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = prompts_dir / f"authored-{ts}.json"
    batch = {
        "ts": ts,
        "world": args.world,
        "model": {
            "url": args.model_url,
            "path": args.model_path,
            "sha256": args.model_sha256,
        },
        "request": payload,
        "reply": content,
        "verdicts": {"liked": liked_names, "disliked": disliked_names},
        "stacks": stacks,
        "misses": misses,
        "prompts": prompts,
    }
    path.write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")
    print(f"authored {len(prompts)} {path}")


if __name__ == "__main__":
    main()
