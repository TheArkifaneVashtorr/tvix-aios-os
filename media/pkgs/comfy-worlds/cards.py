r"""comfy-cards — the card tool: the offline safetensors header pass (GN48)
and, behind a flag whose default is off, the network lookup arm (GN49).

Spec §3.2 and §4: one shot over a world's installed LoRA rows, never at
generation time. The tool reads each row's safetensors header, decides the
three typed card scalars — `trigger` from `modelspec.title` when the title
is the single-token shape, `requires` from the `ss_tag_frequency`
vocabularies on a position or act row, `unmatched` for a bare row — and
writes them into `lab/manifest.toml` through `rewrite_rows`, a pure
text-level editor that preserves every other byte. The strangers' free
text (a title that is not a token, a description, the raw metadata) never
reaches the manifest: it goes to `lab/cards/<name>.json`, one sidecar per
considered row, for the operator to read.

The operator's value always wins: every decision is made only when the
row lacks the key. Every scalar that crosses is judged by GN47's
validators in mutate.py (`_card_token_ok`, `_card_word_ok`,
`CARD_REQUIRES_CATEGORIES`), and the rows considered are exactly those
`mutate._enabled_lora_row` accepts — the pool's installed-row rule, so
the card tool and the draw read the same world.

GN49 — the network arm, off unless `--lookup-url` names a template: the
rows looked up are the considered ones whose `sha256` is a 64-character
lowercase hex string and which carry no `version` yet — the hash the row
already carries, exact and immune to the filename. The template must
carry `{sha256}` exactly once and be https (http on 127.0.0.1 only, the
loopback carve-out author.py's `_check_model_url` uses — judged with
`urlparse`, never a prefix check). The request goes out through the
environment's broker (`HTTPS_PROXY` the proxy, `SSL_CERT_FILE` its CA —
media-fetch's `build_opener` shape, with this arm's own flagged timeout),
and only typed scalars cross: `version` from the response's id,
`trigger` from its first legal trained word, each judged by GN47's
validators. The whole response body, JSON-serialised and cut to 64 KiB,
lands in the sidecar under `lookup` with the host it came from — the
strangers' free text still never reaches the manifest. A 404 is an
answer (GN48's bare-row rule, re-applied); any other failure — another
HTTP status, a transport error, a non-JSON or non-object body, a body
over 1 MiB — is one stderr line, a counted failure and an exit 1. A
resolved row's `unmatched = true` line is deleted: `rewrite_rows`'s
`None` value is the delete arm. The offline pass runs first for every
row; the manifest is rewritten once, at the end, with both passes'
updates. Without the flag the arm opens no socket and the behaviour is
byte-identical to GN48's.

Seams (the FEED_INDEX_PY pattern): mutate.py is loaded by path for the
validators and the row rule — the comfy-cards wrapper exports
FEED_MUTATE_PY plus mutate.py's own FEED_INDEX_PY / FEED_QUEUE_PY, and
the sibling is the in-tree fallback for the unit tests.

Exit grammar, mirroring the author's (GN17's discipline):

- **0** — the pass ran; the last stdout line is
  `carded <k> of <n> rows in <W>: <t> triggers, <r> requires seeded,
  <u> unmatched` (`, <f> lookups failed` appended when the lookup arm
  is on). An unreadable header is one stderr line naming the row, never
  an exit — a refused allowlist still leaves this arm's cards (§4).
- **1** — the rewritten manifest does not round-trip: nothing is
  written, one stderr line names the path. Also: a lookup failed
  (`<f> > 0`, each already named on stderr).
- **2** — bad invocation: an unreadable manifest, a manifest that is
  not TOML, `model` present but not a list, or a `--lookup-url` that
  breaks its rules.

Stdlib only (`tomllib`, `json`, `struct`, `re`, `argparse`, `ssl`,
`urllib`); no network unless `--lookup-url` names one, no new job kind,
nothing at generation time.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import pathlib
import re
import ssl
import struct
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request

_HERE = pathlib.Path(__file__).resolve().parent

# mutate.py is a sibling in the source tree but a separate store path
# once packaged: the comfy-cards wrapper sets FEED_MUTATE_PY to that path,
# and the sibling is the fallback for the in-tree unit tests. mutate.py
# itself loads feed_index.py / queue.py at import through FEED_INDEX_PY /
# FEED_QUEUE_PY, so the wrapper exports all three.
_mutate_path = os.environ.get("FEED_MUTATE_PY") or str(_HERE / "mutate.py")
_mutate_spec = importlib.util.spec_from_file_location("cards_mutate", _mutate_path)
mutate = importlib.util.module_from_spec(_mutate_spec)
sys.modules[_mutate_spec.name] = mutate
_mutate_spec.loader.exec_module(mutate)

# The single-token trigger shape the spec measured on the live nsfw world
# (p0v, gr4b, n3lson, f1lledmouth, 4fter0ral — an optional trailing
# comma, never a space): a title with a space is a title, not a trigger.
TRIGGER_TOKEN_RE = re.compile(r"^[a-z0-9_]{2,16},?$")

# GN49: the lookup response's typed keys (Assumption 12 — no live body
# exists in this tree and no network is opened here; the recorded-shape
# fixture beside the tests is hand-written to this shape and says so in
# its first key). `id` is the upstream version id, `trainedWords` the
# trigger candidates.
LOOKUP_ID_KEY = "id"
LOOKUP_WORDS_KEY = "trainedWords"

_KEY_LINE_RE = re.compile(r"^[ \t]*[A-Za-z_][A-Za-z0-9_-]*[ \t]*=")
_NAME_VALUE_RE = re.compile(r"^[ \t]*name[ \t]*=[ \t]*\"([^\"]*)\"")


def _read_header(path):
    """(metadata, reason) for one safetensors file: the string-valued
    `__metadata__` map, `{}` when the key is absent, or `(None, reason)`
    for every unreadable shape — a short prefix, an oversized length, a
    truncated header, not JSON, not an object, a `__metadata__` that is
    not an object, or a file that cannot be opened."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(8)
            if len(head) < 8:
                return None, "short header"
            (n,) = struct.unpack("<Q", head)
            if n > 100 * 1024 * 1024:
                return None, "header too large"
            raw = fh.read(n)
            if len(raw) < n:
                return None, "truncated header"
    except OSError:
        return None, "open failed"
    try:
        obj = json.loads(raw)
    except ValueError:
        return None, "not JSON"
    if not isinstance(obj, dict):
        return None, "not an object"
    if "__metadata__" not in obj:
        return {}, None
    meta = obj["__metadata__"]
    if not isinstance(meta, dict):
        return None, "metadata is not an object"
    return {k: v for k, v in meta.items() if isinstance(v, str)}, None


def read_safetensors_metadata(path):
    """The string-valued `__metadata__` map of a safetensors file, `{}`
    when the header carries no `__metadata__` at all, `None` when the
    header is unreadable (the caller names the row on stderr)."""
    meta, _reason = _read_header(path)
    return meta


def _tag_vocabulary(value):
    """`ss_tag_frequency`'s value — a JSON-encoded `{dataset: {tag:
    count}}` — as `(tag, count)` pairs: every pair across datasets,
    integer counts only, sorted by count descending then tag, cut to 32.
    Not JSON or not that shape: `[]`."""
    if not isinstance(value, str):
        return []
    try:
        obj = json.loads(value)
    except ValueError:
        return []
    if not isinstance(obj, dict):
        return []
    pairs = []
    for tags in obj.values():
        if not isinstance(tags, dict):
            return []
        for tag, count in tags.items():
            if isinstance(count, int) and not isinstance(count, bool):
                pairs.append((tag, count))
    pairs.sort(key=lambda pair: (-pair[1], pair[0]))
    return pairs[:32]


def _title_is_token(title):
    """`modelspec.title` is the trigger shape: the single-token class
    above AND GN47's token validator, judged once."""
    return (
        title is not None
        and TRIGGER_TOKEN_RE.fullmatch(title) is not None
        and mutate._card_token_ok(title)
    )


def _requires_words(tags, trigger):
    """The first three vocabulary tags with `count >= 2` that pass GN47's
    word validator and are not the trigger stripped of its comma
    (case-insensitive) — `None` when not even one exists."""
    avoid = trigger.rstrip(",").lower() if isinstance(trigger, str) else None
    words = [
        tag
        for tag, count in tags
        if count >= 2 and mutate._card_word_ok(tag) and tag.lower() != avoid
    ]
    if not words:
        return None
    return words[:3]


def _render_value(value):
    """One TOML right-hand side: `true`/`false`, a basic string (`"` and
    `\\` escaped), or an inline array of basic strings."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, list):
        if not value:
            return "[ ]"
        return "[ " + ", ".join(_render_value(item) for item in value) + " ]"
    raise ValueError(f"cannot render a {type(value).__name__} into the manifest")


def _model_blocks(lines):
    """`(start, end, name)` per `[[model]]` block: a block runs from its
    `[[model]]` line to the line before the next line whose first
    non-blank character is `[`, or the end; `name` comes from the block's
    first `name = "…"` key line (`None` when the block has none)."""
    blocks = []
    current = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("["):
            if current is not None:
                blocks.append((current[0], i, current[1]))
                current = None
            if line.lstrip().startswith("[[model]]"):
                current = (i, None)
        elif current is not None and current[1] is None:
            m = _NAME_VALUE_RE.match(line)
            if m:
                current = (current[0], m.group(1))
    if current is not None:
        blocks.append((current[0], len(lines), current[1]))
    return blocks


def rewrite_rows(text, updates):
    """The typed write-back, pure over the manifest TEXT: `updates` maps a
    row name to `{key: value}`. A row's block is the one whose first
    `name = "…"` key line equals the name; a key line inside the block
    (`^\\s*<key>\\s*=`) is replaced in place, else the new line is
    appended after the block's last key line; a value of `None` is the
    delete arm — the key's line inside the block is removed, nothing
    rendered (a resolved row's `unmatched = true` line); every other
    byte of the file is preserved."""
    if not updates:
        return text
    lines = text.splitlines(keepends=True)
    # Blocks are edited last-to-first: an insertion lengthens the line
    # list, so every block BEFORE the edited one keeps its (start, end)
    # — the spans were computed against the original list once.
    for start, end, name in reversed(_model_blocks(lines)):
        if name is None or name not in updates:
            continue
        block = lines[start + 1 : end]
        for key, value in updates[name].items():
            pattern = re.compile(rf"^[ \t]*{re.escape(key)}[ \t]*=")
            if value is None:
                # the delete arm: the key's line is removed, nothing
                # rendered — a resolved row's `unmatched = true` line
                block = [line for line in block if not pattern.match(line)]
                continue
            rendered = f"{key} = {_render_value(value)}"
            for j, line in enumerate(block):
                if pattern.match(line):
                    newline = "\n" if line.endswith("\n") else ""
                    block[j] = rendered + newline
                    break
            else:
                last = max(
                    j for j, line in enumerate(block) if _KEY_LINE_RE.match(line)
                )
                if not block[last].endswith("\n"):
                    block[last] += "\n"
                block.insert(last + 1, rendered + "\n")
        lines[start + 1 : end] = block
    return "".join(lines)


def _round_trip_reason(new_text, updates):
    """`None` when the rewritten manifest parses and every written key
    reads back equal — else the reason the write is refused."""
    try:
        parsed = tomllib.loads(new_text)
    except ValueError as exc:
        return f"not valid TOML: {exc}"
    rows = {}
    for entry in parsed.get("model", []):
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            rows[entry["name"]] = entry
    for name, keyvals in updates.items():
        row = rows.get(name)
        if row is None:
            return f"the row {name} vanished from the rewritten manifest"
        for key, value in keyvals.items():
            if row.get(key) != value:
                return f"{name}'s {key} reads back {row.get(key)!r}, wanted {value!r}"
    return None


def _now_rfc3339():
    """UTC RFC3339, second precision — the sidecar's timestamp."""
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _sha256_hex_ok(value):
    """The lookup's key: a 64-character lowercase hex string — the sha256
    the row already carries, exact and immune to the filename."""
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _lookup_template_reason(template):
    """`None` when the template obeys both rules, else the broken rule's
    stderr line (an exit 2): `{sha256}` exactly once, and https — or http
    on 127.0.0.1 only, the loopback carve-out author.py's
    `_check_model_url` uses — judged with `urlparse`, never a prefix
    check."""
    if template.count("{sha256}") != 1:
        return "the --lookup-url template must contain {sha256} exactly once"
    parsed = urllib.parse.urlparse(template)
    allowed = parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname == "127.0.0.1")  # fmt: skip
    if not allowed:
        return (
            "the --lookup-url must be https (or http on 127.0.0.1, the"
            " loopback carve-out)"
        )
    return None


def _lookup(url, timeout):
    """`(status, obj, reason)` for one GET. The opener honours the
    environment's proxy (`HTTPS_PROXY` — the broker, in the unit) and its
    CA (`SSL_CERT_FILE`), media-fetch's `build_opener` shape with this
    arm's own flagged timeout; the body read is capped at 1 MiB + 1 — a
    longer body is `too large`. `reason` is `None` only for a 200 with a
    JSON object, and for a 404 (an answer, not a failure); every other
    outcome carries its reason."""
    context = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(urllib.request.getproxies()),
        urllib.request.HTTPSHandler(context=context),
    )
    try:
        resp = opener.open(url, timeout=timeout)
        try:
            body = resp.read(1024 * 1024 + 1)
        finally:
            resp.close()
    except urllib.error.HTTPError as exc:
        return exc.code, None, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return "error", None, str(getattr(exc, "reason", exc)) or "error"
    except TimeoutError as exc:
        return "error", None, str(exc) or "timed out"
    except OSError as exc:
        return "error", None, str(exc) or "error"
    if len(body) > 1024 * 1024:
        return 200, None, "too large"
    try:
        obj = json.loads(body)
    except ValueError:
        return 200, None, "not JSON"
    if not isinstance(obj, dict):
        return 200, None, "not an object"
    return 200, obj, None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="comfy-cards",
        description=(
            "The card tool: read the world's safetensors headers, decide"
            " the typed card scalars, write them back; optionally look the"
            " rows up by sha256 through the broker."
        ),
    )
    parser.add_argument("--world", required=True, help="the world under <root>/worlds")
    parser.add_argument("--root", required=True, help="the worlds root")
    parser.add_argument(
        "--dry-run", action="store_true", help="decide and print, write nothing"
    )
    parser.add_argument(
        "--lookup-url",
        help=(
            "the network arm's request template: {sha256} exactly once,"
            " https (or http on 127.0.0.1); absent = no socket is opened"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="the lookup's socket timeout, in seconds",
    )
    args = parser.parse_args(argv)

    if args.lookup_url is not None:
        reason = _lookup_template_reason(args.lookup_url)
        if reason is not None:
            print(
                f"comfy-cards: {reason}: {args.lookup_url}",
                file=sys.stderr,
            )
            return 2

    lab = pathlib.Path(args.root) / "worlds" / args.world / "lab"
    manifest = lab / "manifest.toml"
    try:
        with open(manifest, "rb") as fh:
            data = tomllib.load(fh)
        text = manifest.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"comfy-cards: cannot read {manifest}: {exc}", file=sys.stderr)
        return 2
    except tomllib.TOMLDecodeError as exc:
        print(f"comfy-cards: {manifest} is not valid TOML: {exc}", file=sys.stderr)
        return 2
    models = data.get("model", [])
    if not isinstance(models, list):
        print(
            f"comfy-cards: {manifest}: model is present but not a list",
            file=sys.stderr,
        )
        return 2

    models_dir = pathlib.Path(args.root) / "worlds" / args.world / "models"
    updates = {}
    sidecars = []
    # GN49: the offline pass runs first for every considered row; the
    # lookup pass then reads each row's own state (never the manifest
    # again — it is not yet rewritten), and the manifest is rewritten
    # once, at the end, with both passes' updates.
    states = []
    n_considered = 0
    n_carded = 0
    n_trigger = 0
    n_seeded = 0
    n_unmatched = 0
    for row in models:
        if not mutate._enabled_lora_row(row):
            continue
        name = row["name"]
        dest = row["dest"]
        n_considered += 1
        meta, reason = _read_header(models_dir / dest)
        if meta is None:
            print(
                f"comfy-cards: {name}: unreadable header ({reason})",
                file=sys.stderr,
            )
        title = meta.get("modelspec.title") if meta is not None else None
        tags = _tag_vocabulary(meta.get("ss_tag_frequency")) if meta is not None else []

        # The typed decisions, each only when the row lacks the key — the
        # operator's value always wins.
        trigger = None
        if "trigger" not in row and _title_is_token(title):
            trigger = title
        effective_trigger = row.get("trigger", trigger)
        category = row.get("category")
        requires = None
        if "requires" not in row and category in mutate.CARD_REQUIRES_CATEGORIES:
            requires = _requires_words(tags, effective_trigger)
        unmatched = False
        if "unmatched" not in row and (
            effective_trigger is None
            and row.get("category") is None
            and (meta is None or (title is None and not tags))
        ):
            unmatched = True

        decided = {}
        decided["trigger"] = trigger
        decided["requires"] = requires
        decided["unmatched"] = unmatched
        row_updates = {}
        if trigger is not None:
            row_updates["trigger"] = trigger
        if requires is not None:
            row_updates["requires"] = requires
        if unmatched:
            row_updates["unmatched"] = True
        if row_updates:
            updates[name] = row_updates

        final_requires = row.get("requires", requires)
        final_unmatched = row.get("unmatched", unmatched)
        print(
            f"card {name}"
            f" trigger={effective_trigger if effective_trigger is not None else '-'}"
            f" requires={len(final_requires) if final_requires is not None else 0}"
            f" unmatched={'yes' if final_unmatched is True else 'no'}"
        )
        if effective_trigger is not None:
            n_trigger += 1
        if requires is not None:
            n_seeded += 1
        if final_unmatched is True:
            n_unmatched += 1
        if category is not None and final_unmatched is not True:
            n_carded += 1
        payload = {
            "name": name,
            "sha256": row.get("sha256"),
            "dest": dest,
            "readable": meta is not None,
            "title": title,
            "tags": [[tag, count] for tag, count in tags],
            "metadata": {k: v[:4096] for k, v in (meta or {}).items()},
            "decided": decided,
            "ts": _now_rfc3339(),
        }
        sidecars.append(payload)
        states.append(
            {
                "name": name,
                "row": row,
                "sidecar": payload,
                "offline_trigger": trigger,
                "effective_trigger": effective_trigger,
                "category": category,
            }
        )

    failed = 0
    if args.lookup_url is not None:
        for state in states:
            row = state["row"]
            name = state["name"]
            sha256 = row.get("sha256")
            if not _sha256_hex_ok(sha256):
                print(
                    f"comfy-cards: {name}: skipped the lookup"
                    " (sha256 is not a 64-character lowercase hex string)",
                    file=sys.stderr,
                )
                continue
            if row.get("version") is not None:
                continue  # the operator's version always wins
            entry = updates.setdefault(name, {})
            url = args.lookup_url.replace("{sha256}", sha256)
            status, obj, reason = _lookup(url, args.timeout)
            payload = state["sidecar"]
            if reason is None and status == 200:
                # a 200 with a JSON object: only the typed scalars cross
                wrote_version = False
                if LOOKUP_ID_KEY in obj:
                    version = str(obj[LOOKUP_ID_KEY])
                    if mutate._card_version_ok(version):
                        entry["version"] = version
                        wrote_version = True
                offline_trigger = state["offline_trigger"]
                lookup_trigger = None
                candidates = obj.get(LOOKUP_WORDS_KEY)
                if not isinstance(candidates, list):
                    candidates = []
                if row.get("trigger") is None and offline_trigger is None:
                    for word in candidates:
                        if mutate._card_token_ok(word):
                            lookup_trigger = word
                            break
                if lookup_trigger is not None:
                    entry["trigger"] = lookup_trigger
                if wrote_version or lookup_trigger is not None:
                    # a resolved row: this arm's own offline mark is undone
                    # and a written `unmatched = true` line is removed —
                    # the row is no longer unmatched
                    entry.pop("unmatched", None)
                    if row.get("unmatched") is True:
                        updates[name]["unmatched"] = None
                payload["lookup"] = {
                    "host": urllib.parse.urlparse(url).hostname,
                    "status": 200,
                    "body": json.dumps(obj)[: 64 * 1024],
                }
            elif status == 404:
                # an answer, not a failure: GN48's bare-row rule, re-applied
                # now that the lookup said there is nothing upstream
                payload["lookup"] = {"status": 404}
                if (
                    "unmatched" not in row
                    and state["effective_trigger"] is None
                    and state["category"] is None
                ):
                    entry["unmatched"] = True
            else:
                failed += 1
                print(
                    f"comfy-cards: {name}: lookup failed ({reason})",
                    file=sys.stderr,
                )
                payload["lookup"] = {"status": status, "reason": reason}

    if updates:
        new_text = rewrite_rows(text, updates)
        reason = _round_trip_reason(new_text, updates)
        if reason is not None:
            print(
                f"comfy-cards: refusing to write {manifest}:"
                f" the rewritten manifest does not round-trip ({reason})",
                file=sys.stderr,
            )
            return 1
        if not args.dry_run:
            tmp = pathlib.Path(str(manifest) + ".tmp")
            tmp.write_text(new_text, encoding="utf-8")
            os.replace(tmp, manifest)
    if not args.dry_run:
        cards_dir = lab / "cards"
        cards_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
        os.chmod(cards_dir, 0o755)
        for payload in sidecars:
            (cards_dir / f"{payload['name']}.json").write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
    summary = (
        f"carded {n_carded} of {n_considered} rows in {args.world}:"
        f" {n_trigger} triggers, {n_seeded} requires seeded, {n_unmatched} unmatched"
    )
    if args.lookup_url is not None:
        summary += f", {failed} lookups failed"
    print(summary)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
