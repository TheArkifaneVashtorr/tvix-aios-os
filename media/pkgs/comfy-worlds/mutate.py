"""Prompt mutation from likes: the grammar plus the loop that drives it.

Two halves in one stdlib-only module:

- The *grammar* — `mutate` turns a world's lab `manifest.toml` `[mutate]` table
  into deterministic prompt variants. Pure, no ComfyUI, no model, no network, no
  filesystem I/O beyond `load_rules` reading the one manifest.
- The *loop* — `main` reads the world's liked renders, extracts each render's
  positive `CLIPTextEncode` text, runs it through the grammar, and enqueues one
  kind-`mutate` job per variant before driving `queue.run_once` once. That loop
  does the I/O and drives ComfyUI on loopback.
- The *authored batch* — `--seed-file <path>` replaces the like-reading step:
  each prompt in the author's JSON batch (`{"prompts": [str, …]}`) is expanded
  through the same grammar onto the one scaffold graph (the newest liked
  render's, else the newest render's), deterministically, and enqueued as
  kind-`mutate` jobs with an `authored:<file>` source. GN50's coupled draw:
  the batch may carry `stacks` — one `{loras, requires, triggers}` entry per
  prompt, absent or `null` meaning uncoupled — and each slot binds that
  stack instead of drawing its own; `requires` is checked per variant
  against the mutated prompt (a miss drops the stack for that variant and
  counts on the `bound`/`dropped` line), and the triggers are prepended at
  enqueue, never written by the author.
- The *coupled draw* — `--draw-stacks N` (mutually exclusive with
  `--seed-file`) draws N stacks from the enabled `[mutate.loraStack]` — the
  draw the author is told about — and writes them to
  `<root>/worlds/<world>/lab/prompts/stacks-<UTC>.json` as
  `{"ts", "world", "seed", "stacks"}`; the last stdout line is
  `drawn <N> <path>`.

Rules (TOML, under `[mutate]` in `manifest.toml`):

- `swaps = [["golden hour", "blue hour"], …]` — unordered token pairs; either
  direction fires.
- `lora = { "<name>" = [min, max] }` — a float strength range for
  `<lora:<name>:<strength>>` tags.
- `samplers = ["euler", "dpmpp_2m", …]` — sampler names.
- `seed = "derive" | "keep"` — derive a per-variant seed from the caller's seed,
  or carry the caller's seed into every variant (for A/B on text alone).
- `stripLoras = true | false` (default false) — drop the scaffold graph's LoRA
  loader chain from every variant, rewiring its consumers back to the chain's
  source. Not `lora` above: that rewrites inline `<lora:…>` tags in the prompt
  TEXT, this one deletes loader NODES. The interim control until the stack is
  chosen rather than inherited — `_scaffold` copies the newest liked render's
  graph, so today the stack is whatever the operator last tapped like on.
- `[mutate.loraStack]` — the stack axis's own table (GN38): `enable` (default
  false), `count = [lo, hi]`, `strength = [lo, hi]`, and a pool of LoRAs
  derived from the `[[model]]` entries — every enabled `loras/`-dest row that
  carries a card (GN47: `category` present and `unmatched` not true), in
  manifest order, never a second list of names; a row with no card is not in
  the pool. Absent or disabled the key is `None` and the module's behaviour
  is byte-identical to today. Enabled
  (GN39), the draw fills each variant's stack: `count` members at most,
  strengths inside `strength` rounded to three decimals, ordered (draw order
  is loader order), weighted per LoRA (a liked LoRA draws likelier — the
  world's own verdict history, `lora_stack_weights`, read from the feed at
  run time), and coherent by declaration — one `category` per
  stack, `incompatible` symmetric. Enabled, the graph half (GN40) then
  rebuilds each variant's scaffold loader chain to that stack: one
  `LoraLoaderModelOnly` per entry, the consumers repointed, a chain
  inserted where none existed, and a branched or forked chain refused
  by name (`LoraChainUnsupported` on stderr with the node ids, exit 2 —
  the `RuleNeverFires` discipline, never a guess). GN53: the same card
  treatment for base models — every enabled `diffusion_models/` row (a
  `checkpoints/`-dest row is not a base model here: the worlds' graphs
  load the model through `UNETLoader`) is a checkpoint in the pool
  (`checkpoints`), `trigger`/`version`/`unmatched` card-validated while
  `category`/`requires`/`incompatible` are refused as LoRA card fields;
  one checkpoint is drawn per variant (a pool of one takes no draw —
  correct at N = 1, real the moment a second is adopted) and written
  into every `UNETLoader` node's `unet_name` as the row's dest basename;
  a graph with no `UNETLoader` to write into is refused by name
  (`BaseModelUnsupported`, exit 2).

`mutate` applies exactly one rule per present category per variant, drawing from
a single `random.Random(seed)`, so the same `(prompt, rules, seed, n)` always
yields the byte-identical list. The stack's draws are appended to that one
stream after the seed, so an absent or inert `loraStack` leaves every prior
draw where it was. A category whose rules are present but cannot
fire on the prompt is an error (`RuleNeverFires`), never a silent skip. A
variant that collides with one already collected is redrawn from the same
stream, and `mutate` raises `VariantsExhausted` when `_MAX_DRAWS` draws cannot
produce `n` distinct variants, rather than returning a duplicated or short
list. A stack whose floor cannot be reached within the conflict rules fails
its candidate, and a pool whose floor is unreachable fails every candidate —
the same `_MAX_DRAWS` budget, the same `VariantsExhausted`, never a hang.
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime
import importlib.util
import json
import os
import pathlib
import random
import re
import sys
import tomllib

_HERE = pathlib.Path(__file__).resolve().parent
# feed_index.py and queue.py are siblings in the source tree but separate store
# paths once packaged: the comfy-mutate wrapper sets FEED_INDEX_PY / FEED_QUEUE_PY
# to those paths (the same seam feed.py reads), and the sibling is the fallback
# for the in-tree unit tests.
_index_path = os.environ.get("FEED_INDEX_PY") or str(_HERE / "feed_index.py")
_index_spec = importlib.util.spec_from_file_location("feed_index", _index_path)
feed_index = importlib.util.module_from_spec(_index_spec)
_index_spec.loader.exec_module(feed_index)

_queue_path = os.environ.get("FEED_QUEUE_PY") or str(_HERE / "queue.py")
_queue_spec = importlib.util.spec_from_file_location("queue", _queue_path)
queue = importlib.util.module_from_spec(_queue_spec)
_queue_spec.loader.exec_module(queue)


@dataclasses.dataclass(frozen=True)
class Variant:
    """One mutated prompt plus the sampler, seed and LoRA stack it renders
    with."""

    prompt: str
    sampler: str | None
    seed: int
    # The drawn LoRA stack in draw order (loader order is graph order, §6):
    # one `(name, strength)` pair per LoRA, `name` the manifest pool's own.
    # A tuple of tuples so the frozen dataclass stays hashable and the
    # `seen` set counts a stack that differs only in strength as distinct.
    loras: tuple[tuple[str, float], ...] = ()
    # GN53: the drawn base model — the checkpoint pool row's `name`, drawn
    # after the stack's draws (a pool of one takes no draw); `None` when the
    # world has no checkpoints or a bound slot names none. Written into every
    # `UNETLoader` node by `_substitute`, never inherited from the scaffold.
    checkpoint: str | None = None


class RuleNeverFires(Exception):
    """No rule in a category can fire on the prompt — an error, not silence."""

    def __init__(self, category: str, detail: str) -> None:
        self.category = category
        self.detail = detail
        super().__init__(f"no {category} rule can fire: {detail}")


class VariantsExhausted(Exception):
    """`mutate` could not collect `requested` distinct variants within its budget."""

    def __init__(self, requested: int, distinct: int, attempts: int) -> None:
        self.requested = requested
        self.distinct = distinct
        self.attempts = attempts
        super().__init__(
            f"could not collect {requested} distinct variants: "
            f"only {distinct} after {attempts} draws"
        )


class LoraChainUnsupported(Exception):
    """The graph's LoRA loaders are not a simple chain — a configuration
    error, refused by name, never rewired on a guess (the `RuleNeverFires`
    discipline)."""

    def __init__(self, node_ids, detail: str) -> None:
        self.node_ids = [str(node_id) for node_id in node_ids]
        self.detail = detail
        ids = ", ".join(self.node_ids)
        super().__init__(f"lora chain unsupported at nodes {ids}: {detail}")


class BaseModelUnsupported(Exception):
    """The graph has no node the drawn checkpoint can be written into —
    `LoraChainUnsupported`'s shape (node ids, detail), a configuration error
    refused by name, never a silent skip (the `RuleNeverFires`
    discipline)."""

    def __init__(self, node_ids, detail: str) -> None:
        self.node_ids = [str(node_id) for node_id in node_ids]
        self.detail = detail
        super().__init__(f"base model unsupported: {detail}")


LORA_TAG = re.compile(r"<lora:([^:>]+):([^>]+)>")

# GN47: the LoRA cards — the typed fields a `[[model]]` row may carry beside
# its name and dest. The three validators below are the ONLY place a card
# scalar is judged: the loader here and the card tool (GN48) both call them,
# so the grammar is written once (§8's boundary — length-capped and
# character-checked, once).
CARD_CATEGORIES = ("position", "act", "body", "style", "detail")
CARD_REQUIRES_CATEGORIES = ("position", "act")
TRIGGER_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.,:;!'() -]{0,63}$")
WORD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9' -]{0,47}$")
VERSION_RE = re.compile(r"^[A-Za-z0-9._-]{1,32}$")


def _card_token_ok(v):
    """A trigger token: the class above AND no edge space — a trailing
    space is inside the class, so the strip clause is its own rule."""
    return isinstance(v, str) and TRIGGER_RE.fullmatch(v) is not None and v == v.strip()


def _card_word_ok(v):
    """A requires word: the class above AND no edge space."""
    return isinstance(v, str) and WORD_RE.fullmatch(v) is not None and v == v.strip()


def _card_version_ok(v):
    """A version id: the class above (no space can occur in it)."""
    return isinstance(v, str) and VERSION_RE.fullmatch(v) is not None


def _enabled_lora_row(entry) -> bool:
    """An installed row: a dict with a non-empty string `name`, a `dest`
    beginning `loras/`, and `enabled` true — the rows the pool and the
    uncarded report both iterate (today's loop, extracted so the card tool
    reads the same rows)."""
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("name"), str)
        and bool(entry.get("name"))
        and isinstance(entry.get("dest"), str)
        and entry.get("dest").startswith("loras/")
        and entry.get("enabled") is True
    )


def _base_model_row(entry) -> bool:
    """An installed base-model row (GN53): a dict with a non-empty string
    `name`, a `dest` beginning `diffusion_models/`, and `enabled` true.
    A `checkpoints/`-dest row is not a base model here: the worlds' graphs
    load the model through `UNETLoader`, the `diffusion_models/` folder —
    the spec's word and the `_lora_chain_graph` fixture's `UNETLoader`
    node."""
    if not isinstance(entry, dict):
        return False
    name = entry.get("name")
    dest = entry.get("dest")
    return (
        isinstance(name, str)
        and bool(name)
        and isinstance(dest, str)
        and dest.startswith("diffusion_models/")
        and entry.get("enabled") is True
    )


# The redraw budget for `mutate`: the most candidate variants one call draws
# before giving up and raising `VariantsExhausted`.
_MAX_DRAWS = 50


def _lora_stack(table: dict, data: dict) -> dict | None:
    """Normalize `[mutate.loraStack]`: `None` unless enabled, else the bounds
    plus the LoRA pool derived from the `[[model]]` entries.

    The pool is a rule, never a name list: every installed row
    (`_enabled_lora_row`), in manifest order, that carries a CARD —
    `category` present and `unmatched` not true (GN47). The card's own typed
    fields are validated here, once, at load: `category` one of the five,
    `trigger` a token, `requires` 1-8 words and only on a position or act
    card, `unmatched` a bool, `version` an id. An installed row without a
    card is out of the pool — named once on stderr by `_report_uncarded`,
    never an exit. An inert table (absent, or `enable` false) validates
    nothing else — a parked world never refuses to load. Every violation of
    an enabled table is a named `ValueError` raised here: refused at load,
    never discovered at draw.
    """
    stack = table.get("loraStack")
    if stack is None:
        return None
    enable = stack.get("enable", False)
    if not isinstance(enable, bool):
        raise ValueError(f"loraStack: enable must be a boolean, got {enable!r}")
    if not enable:
        return None

    pool = []
    uncarded = []
    installed = []
    for entry in data.get("model", []):
        if not _enabled_lora_row(entry):
            continue
        name = entry["name"]
        dest = entry["dest"]
        category = entry.get("category")
        if category is not None and category not in CARD_CATEGORIES:
            raise ValueError(
                f"loraStack: {name}'s category must be one of position, act,"
                f" body, style, detail, got {category!r}"
            )
        trigger = entry.get("trigger")
        if trigger is not None and not _card_token_ok(trigger):
            raise ValueError(
                f"loraStack: {name}'s trigger is not a token (1-64 chars of"
                " letters, digits, _ . , : ; ! ' ( ) - and space, no edge"
                " space)"
            )
        requires = entry.get("requires")
        if requires is not None:
            if (
                not isinstance(requires, list)
                or not 1 <= len(requires) <= 8
                or any(not _card_word_ok(word) for word in requires)
            ):
                raise ValueError(
                    f"loraStack: {name}'s requires must be 1-8 words of"
                    " letters, digits, space, ' and - (48 chars each)"
                )
            if category not in CARD_REQUIRES_CATEGORIES:
                raise ValueError(
                    f"loraStack: {name} carries requires but its category is"
                    f" {category!r}; only position and act cards carry"
                    " requires"
                )
        unmatched = entry.get("unmatched")
        if unmatched is not None and not isinstance(unmatched, bool):
            raise ValueError(f"loraStack: {name}'s unmatched must be true or false")
        version = entry.get("version")
        if version is not None and not _card_version_ok(version):
            raise ValueError(
                f"loraStack: {name}'s version is not an id (1-32 chars of"
                " letters, digits, . _ -)"
            )
        incompatible = entry.get("incompatible", [])
        if not isinstance(incompatible, list) or any(
            not isinstance(other, str) for other in incompatible
        ):
            raise ValueError(f"loraStack: {name}'s incompatible must be names")
        installed.append((name, incompatible))
        if category is not None and entry.get("unmatched") is not True:
            pool.append(
                {
                    "name": name,
                    "dest": dest,
                    "category": category,
                    "incompatible": frozenset(incompatible),
                    "trigger": trigger,
                    "requires": tuple(requires) if requires is not None else (),
                    "version": version,
                }
            )
        else:
            uncarded.append(name)

    # incompatible names any installed row — pool or uncarded.
    names = {name for name, _ in installed}
    for name, incompatible in installed:
        for other in incompatible:
            if other == name:
                raise ValueError(f"loraStack: {name} names itself in incompatible")
            if other not in names:
                raise ValueError(
                    f"loraStack: {name}'s incompatible names {other!r},"
                    " not an enabled loras/ entry in the pool"
                )

    # GN53: the base-model pool — the same card treatment for
    # `diffusion_models/` rows. Manifest order; a row whose `unmatched` is
    # true is out of the pool (an unmatched base model is not drawn, the
    # operator's own declaration); `category`, `requires` and `incompatible`
    # are LoRA card fields and refused here, `trigger`, `version` and
    # `unmatched` are validated by the same rules as the LoRA pool's.
    checkpoints = []
    for entry in data.get("model", []):
        if not _base_model_row(entry):
            continue
        name = entry["name"]
        if any(k in entry for k in ("category", "requires", "incompatible")):
            raise ValueError(
                f"loraStack: {name} is a diffusion_models/ row; category,"
                " requires and incompatible are LoRA card fields"
            )
        trigger = entry.get("trigger")
        if trigger is not None and not _card_token_ok(trigger):
            raise ValueError(
                f"loraStack: {name}'s trigger is not a token (1-64 chars of"
                " letters, digits, _ . , : ; ! ' ( ) - and space, no edge"
                " space)"
            )
        version = entry.get("version")
        if version is not None and not _card_version_ok(version):
            raise ValueError(
                f"loraStack: {name}'s version is not an id (1-32 chars of"
                " letters, digits, . _ -)"
            )
        unmatched = entry.get("unmatched")
        if unmatched is not None and not isinstance(unmatched, bool):
            raise ValueError(f"loraStack: {name}'s unmatched must be true or false")
        # An unmatched base row is out of the pool — one clause held on
        # one line (fmt: off keeps it there), the pool rule's own shape.
        # fmt: off
        if entry.get("unmatched") is True: continue  # base  # noqa: E701
        # fmt: on
        checkpoints.append(
            {
                "name": name,
                "dest": entry["dest"],
                "trigger": trigger,
                "version": version,
            }
        )

    count = stack.get("count")
    if count is None:
        raise ValueError("loraStack: count is required when enable is true")
    if (
        not isinstance(count, list)
        or len(count) != 2
        or any(isinstance(v, bool) or not isinstance(v, int) for v in count)
    ):
        raise ValueError(
            f"loraStack: count must be a 2-element array of ints, got {count!r}"
        )
    lo, hi = count
    if lo < 0:
        raise ValueError(f"loraStack: count lo {lo} must not be negative")
    if lo > hi:
        raise ValueError(f"loraStack: count lo {lo} exceeds hi {hi}")
    if hi > len(pool) + len(uncarded):
        raise ValueError(
            f"loraStack: count hi {hi} exceeds the"
            f" {len(pool) + len(uncarded)} enabled loras/ rows"
        )

    strength = stack.get("strength")
    if strength is None:
        raise ValueError("loraStack: strength is required when enable is true")
    if (
        not isinstance(strength, list)
        or len(strength) != 2
        or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in strength)
    ):
        raise ValueError(
            f"loraStack: strength must be a 2-element array of numbers,"
            f" got {strength!r}"
        )
    s_lo, s_hi = float(strength[0]), float(strength[1])
    if s_lo <= 0:
        raise ValueError(f"loraStack: strength lo {strength[0]} must be positive")
    if s_lo > s_hi:
        raise ValueError(
            f"loraStack: strength lo {strength[0]} exceeds hi {strength[1]}"
        )

    return {
        "count": (lo, hi),
        "strength": (s_lo, s_hi),
        "pool": tuple(pool),
        # The loops fill this from the feed's verdict history
        # (lora_stack_weights, GN41); None is the uniform cold start.
        "weights": None,
        # GN47: the installed rows outside the carded pool, manifest order —
        # reported once per run by _report_uncarded, never an exit.
        "uncarded": tuple(uncarded),
        # GN53: the base-model pool — every enabled diffusion_models/ row
        # whose `unmatched` is not true, manifest order.
        "checkpoints": tuple(checkpoints),
    }


def load_rules(path: str) -> dict:
    """Read the `[mutate]` table from `path`, refusing a missing table.

    Returns a normalized dict with keys `swaps`, `lora`, `samplers`, `seed`,
    `stripLoras` and `loraStack`; an absent `seed` defaults to `"derive"`, and
    `loraStack` is `None` unless `[mutate.loraStack]` is present with
    `enable = true` (the axis is inert by default). `stripLoras = true`
    beside an enabled table is refused by name: a world that wants no LoRAs
    with the axis on spells it `count = [0, 0]`.
    """
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    table = data.get("mutate")
    if table is None:
        raise ValueError(f"no [mutate] table in {path}")
    stack = _lora_stack(table, data)
    strip = bool(table.get("stripLoras", False))
    if strip and stack is not None:
        # GN46: the fourth arm of the pair — a world saying "no LoRAs" and
        # "draw a stack" at once — is a configuration error, refused at
        # load, never silently resolved. Inert is inert: an absent or
        # `enable = false` table beside `stripLoras` loads as before.
        raise ValueError(
            f"[mutate] stripLoras = true and [mutate.loraStack] enable = true in"
            f" {path}: a world says no LoRAs with count = [0, 0]; remove stripLoras"
        )
    return {
        "swaps": [list(pair) for pair in table.get("swaps", [])],
        "lora": {name: list(rng) for name, rng in table.get("lora", {}).items()},
        "samplers": list(table.get("samplers", [])),
        "seed": table.get("seed", "derive"),
        # Not to be confused with `lora` above, which rewrites inline
        # <lora:NAME:strength> tags in the prompt TEXT. This one drops the
        # graph's loader nodes.
        "stripLoras": strip,
        # GN38: the stack axis's own table — written here, read by nobody in
        # this module yet (GN39 draws from it, GN40 threads it into
        # `_substitute`), so the module's behaviour is unchanged.
        "loraStack": stack,
    }


def _apply_swap(prompt: str, swaps: list, rng: random.Random) -> str:
    candidates = [pair for pair in swaps if pair[0] in prompt or pair[1] in prompt]
    if not candidates:
        raise RuleNeverFires("swaps", "no swap token occurs in the prompt")
    left, right = rng.choice(candidates)
    if left in prompt:
        return prompt.replace(left, right, 1)
    return prompt.replace(right, left, 1)


def _apply_lora(prompt: str, lora: dict, rng: random.Random) -> str:
    tags = []
    for match in LORA_TAG.finditer(prompt):
        if match.group(1) in lora:
            tags.append((match, match.group(1)))
    if not tags:
        raise RuleNeverFires("lora", "no lora tag occurs in the prompt")
    match, name = rng.choice(tags)
    low, high = lora[name]
    strength = rng.uniform(low, high)
    tag = f"<lora:{name}:{strength}>"
    return prompt[: match.start()] + tag + prompt[match.end() :]


def _next_seed(rng: random.Random, policy: str, caller_seed: int) -> int:
    if policy == "keep":
        return caller_seed
    return rng.randrange(2**32)


def _stack_compatible(entry: dict, drawn: list) -> bool:
    """True when `entry` may join `drawn`: it declares no category a drawn
    member already holds, and no `incompatible` pairing fires in either
    direction (the operator writes each pair once, §9's own rule)."""
    for other in drawn:
        if entry["category"] is not None and entry["category"] == other["category"]:
            return False
        if other["name"] in entry["incompatible"]:
            return False
        if entry["name"] in other["incompatible"]:
            return False
    return True


def _draw_stack(stack: dict | None, rng: random.Random):
    """The candidate's LoRA stack: `None` when the candidate fails, else a
    tuple of `(name, strength)` pairs in draw order.

    Count first (`rng.randint`, both bounds inclusive), then one member and
    one strength per slot, every draw from the caller's one stream. The
    count is drawn against the table's own bounds, then CLAMPED to the
    carded pool's size (GN47): a world whose count hi counts uncarded rows
    still renders — a pool of size 0 yields `()`, never an exhaustion — and
    the `randint` is always drawn, so the stream position of every later
    draw is unchanged. A member already drawn, sharing a category with one,
    or incompatible with one (either direction) is not a candidate; when no
    acceptable member remains before the target is reached the whole
    candidate fails — the caller's shared `_MAX_DRAWS` budget turns a
    persistently unreachable floor into `VariantsExhausted`, never a hang
    (the fill loop terminates by construction: a finite pool, a
    monotonically growing drawn set). The weights are joined to the pool
    HERE, never assumed congruent: a name absent from the weights draws at
    1.0, and `weights` of None is the uniform fallback (§8's cold start).
    """
    if stack is None:
        return ()
    count_lo, count_hi = stack["count"]
    strength_lo, strength_hi = stack["strength"]
    weights = stack["weights"]
    target = min(rng.randint(count_lo, count_hi), len(stack["pool"]))
    drawn: list[dict] = []
    entries: list[tuple[str, float]] = []
    for _ in range(target):
        taken = {entry["name"] for entry in drawn}
        candidates = [
            entry
            for entry in stack["pool"]
            if entry["name"] not in taken and _stack_compatible(entry, drawn)
        ]
        if not candidates:
            return None
        weighted = None
        if weights is not None:
            weighted = [weights.get(entry["name"], 1.0) for entry in candidates]
        member = rng.choices(candidates, weights=weighted)[0]
        strength = round(rng.uniform(strength_lo, strength_hi), 3)
        drawn.append(member)
        entries.append((member["name"], strength))
    return tuple(entries)


def _draw_checkpoint(stack: dict | None, rng: random.Random) -> str | None:
    """The variant's base model (GN53): `None` when the axis is off or the
    world has no checkpoints, the one name WITHOUT a draw when the pool is
    exactly one (correct at N = 1 — a stream position never moves), else
    `rng.choice` over the names — drawn after the stack's draws on the
    caller's one stream."""
    if stack is None:
        return None
    checkpoints = stack.get("checkpoints", ())
    if not checkpoints:
        return None
    names = [entry["name"] for entry in checkpoints]
    if len(names) == 1:
        return names[0]
    return rng.choice(names)


def draw_stacks(rules: dict, n: int, rng: random.Random) -> list[dict]:
    """The coupled draw's own half (GN50): `n` stacks drawn from the
    world's enabled `[mutate.loraStack]`, one `_draw_stack` result per
    slot — the draw the author is told about, and the shape the batch's
    `stacks` entries are written from.

    Each entry carries the bound graph's own facts, derived from the
    drawn members in stack order: `loras` the `[name, strength]` pairs,
    `requires` the members' requires words (stack order, then each
    member's own order, deduplicated case-insensitively), `triggers` the
    members' triggers that are not `None` — the drawn checkpoint's own
    trigger first, when it has one (GN53) — and `checkpoint` the drawn
    base model, `None` when the world has none. A `None` candidate — the
    conflict rules could not fill the slot — is redrawn up to
    `_MAX_DRAWS` times per slot; a slot that never fills raises the
    shared `VariantsExhausted` (`requested` n, `distinct` the slots
    filled, `attempts` `_MAX_DRAWS`), never a hang.
    """
    stack_axis = rules["loraStack"]
    by_name = {entry["name"]: entry for entry in stack_axis["pool"]}
    ckpt_by_name = {entry["name"]: entry for entry in stack_axis.get("checkpoints", ())}
    entries = []
    for _ in range(n):
        drawn = None
        for _ in range(_MAX_DRAWS):
            drawn = _draw_stack(stack_axis, rng)
            if drawn is not None:
                break
        if drawn is None:
            raise VariantsExhausted(
                requested=n, distinct=len(entries), attempts=_MAX_DRAWS
            )
        checkpoint = _draw_checkpoint(stack_axis, rng)
        requires = []
        seen_words = set()
        triggers = []
        if (
            checkpoint is not None
            and ckpt_by_name[checkpoint].get("trigger") is not None
        ):
            # The base model anchors the render before any LoRA does —
            # its trigger leads the list.
            triggers.append(ckpt_by_name[checkpoint]["trigger"])
        for name, _strength in drawn:
            member = by_name[name]
            for w in member.get("requires", ()):
                if w.lower() not in seen_words:
                    seen_words.add(w.lower())
                    requires.append(w)
            if member.get("trigger") is not None:
                triggers.append(member["trigger"])
        entries.append(
            {
                "loras": [[name, strength] for name, strength in drawn],
                "requires": requires,
                "triggers": triggers,
                "checkpoint": checkpoint,
            }
        )
    return entries


def _word_in(word: str, text: str) -> bool:
    """A whole-token match, case-insensitive: `word` occurs in `text`
    bounded by non-alphanumerics on both sides, so "anal" is not "analog"
    and "kneeling" is "kneeling," — the `requires` check's own rule (§4:
    a prompt that ignores `requires` renders unanchored, and the miss is
    counted)."""
    return (
        re.search(
            r"(?<![a-z0-9])" + re.escape(word.lower()) + r"(?![a-z0-9])",
            text.lower(),
        )
        is not None
    )


def mutate(
    prompt: str, rules: dict, seed: int, n: int, stack: tuple | None = None
) -> list[Variant]:
    """Return exactly `n` distinct variants, deterministic in `(prompt, rules, seed, n)`.

    Every candidate is drawn from the one `random.Random(seed)` stream. A
    candidate that collides with one already collected is redrawn, up to
    `_MAX_DRAWS` total draws across the call; when the budget is exhausted with
    fewer than `n` distinct variants collected, `VariantsExhausted` is raised.

    `stack` (GN50's coupled draw) binds the caller's stack — a tuple of
    `(name, strength)` pairs, possibly empty — instead of drawing one per
    candidate: no stack draw happens at all, the prompt, sampler and seed
    draws consume the stream exactly as with `loraStack` absent, and every
    variant carries `loras=stack` verbatim. GN53: the base model follows
    the same rule — a bound call takes its checkpoint from the bound
    entry (the binder's `dataclasses.replace`, never a draw here), an
    uncoupled candidate draws one after the stack's draws (a pool of one
    takes no draw), and a world with no checkpoints draws `None` and
    consumes nothing.
    """
    rng = random.Random(seed)
    swaps = rules["swaps"]
    lora = rules["lora"]
    samplers = rules["samplers"]
    policy = rules.get("seed", "derive")
    rules_stack = rules.get("loraStack")
    variants: list[Variant] = []
    seen: set[Variant] = set()
    attempts = 0
    while len(variants) < n and attempts < _MAX_DRAWS:
        attempts += 1
        text = prompt
        if swaps:
            text = _apply_swap(text, swaps, rng)
        if lora:
            text = _apply_lora(text, lora, rng)
        sampler = rng.choice(samplers) if samplers else None
        drawn_seed = _next_seed(rng, policy, seed)
        # Decision 3: the stack's draws sit after the seed and before the
        # candidate is assembled — the position the second golden freezes.
        # A bound stack (GN50) skips the draw entirely; `None` (the
        # default, both loops' uncoupled path) draws per candidate.
        loras = stack if stack is not None else _draw_stack(rules_stack, rng)
        if loras is None:
            # The candidate's stack could not be filled within the conflict
            # rules: this attempt is spent, the next iteration redraws the
            # whole candidate under the same shared _MAX_DRAWS budget.
            continue
        # GN53: the checkpoint draw sits after the stack's, only when the
        # stack was drawn — a bound call's checkpoint comes from the bound
        # entry, never the stream.
        checkpoint = None if stack is not None else _draw_checkpoint(rules_stack, rng)
        variant = Variant(
            prompt=text,
            sampler=sampler,
            seed=drawn_seed,
            loras=loras,
            checkpoint=checkpoint,
        )
        if variant not in seen:
            seen.add(variant)
            variants.append(variant)
    if len(variants) < n:
        raise VariantsExhausted(requested=n, distinct=len(variants), attempts=attempts)
    return variants


def _parse_graph(text):
    """The class_type graph of a `renders.prompt` value, or `None` when absent
    or not a JSON object."""
    if not text:
        return None
    try:
        graph = json.loads(text)
    except (ValueError, TypeError):
        return None
    return graph if isinstance(graph, dict) else None


def _positive_text(graph):
    """The stored positive prompt: `inputs.text` of the lowest-id
    `CLIPTextEncode` node whose `text` is non-empty and not the base (lowest-id)
    `KSampler`'s negative prompt."""
    best = None
    for node_id, node in graph.items():
        if not isinstance(node, dict) or node.get("class_type") != "KSampler":
            continue
        try:
            key = int(node_id)
        except (ValueError, TypeError):
            continue
        if best is None or key < best[0]:
            best = (key, node)
    negative_id = None
    if best is not None:
        negative = best[1].get("inputs", {}).get("negative")
        if isinstance(negative, (list, tuple)) and negative:
            negative_id = str(negative[0])
    candidates = []
    for node_id, node in graph.items():
        if not isinstance(node, dict) or node.get("class_type") != "CLIPTextEncode":
            continue
        text = node.get("inputs", {}).get("text")
        if not isinstance(text, str) or not text:
            continue
        if node_id == negative_id:
            continue
        try:
            key = int(node_id)
        except (ValueError, TypeError):
            continue
        candidates.append((key, text))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0])
    return candidates[0][1]


def _strip_loras(workflow):
    """Delete every LoRA loader node and rewire whatever consumed it.

    The scaffold's LoRA stack is inherited, never chosen: `_scaffold` takes the
    newest LIKED render's graph, so the stack is whatever the operator last
    tapped like on. Measured 2026-09-20: 1355 renders, one LoRA set, and no way
    to change it from the feed -- liking anything restores it within seconds.

    Deleting a loader is not enough; its consumers would dangle at a missing
    node. Each reference is walked back through the chain to the first
    non-loader output, so a chain of any length collapses to its source and a
    graph with no loaders is untouched.
    """
    loaders = {
        key: node
        for key, node in workflow.items()
        if isinstance(node, dict)
        and str(node.get("class_type", "")).startswith("LoraLoader")
    }
    if not loaders:
        return workflow

    def source(ref):
        node_id, slot = ref
        while node_id in loaders:
            inputs = loaders[node_id].get("inputs", {})
            # Slot 1 is CLIP on a full LoraLoader; LoraLoaderModelOnly has no
            # clip input and both slots resolve through `model`.
            key = "clip" if slot == 1 and "clip" in inputs else "model"
            node_id, slot = inputs[key]
        return [node_id, slot]

    for key, node in workflow.items():
        if key in loaders or not isinstance(node, dict):
            continue
        for name, value in node.get("inputs", {}).items():
            if isinstance(value, list) and len(value) == 2 and value[0] in loaders:
                node["inputs"][name] = source(value)
    for key in loaders:
        del workflow[key]
    return workflow


def _is_ref(value):
    """A `[node_id, slot]` input reference — the workflow API's own shape."""
    return isinstance(value, list) and len(value) == 2


def _refs_to(workflow, targets):
    """Every input in the graph referencing one of `targets`' outputs,
    recorded as `(node_id, input_key, reference)` — however many there
    are (§7 assumes no single consumer)."""
    refs = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        for input_key, value in node.get("inputs", {}).items():
            if _is_ref(value) and str(value[0]) in targets:
                refs.append((node_id, input_key, value))
    return refs


def _numeric_ids(workflow):
    """Every node id that parses as an integer, under any spelling ("07"
    and "7" are both 7) — the set fresh ids are allocated above."""
    ids = set()
    for key in workflow:
        try:
            ids.add(int(key))
        except (TypeError, ValueError):
            continue
    return ids


def _sorted_node_ids(node_ids):
    """Node ids sorted numerically when they parse, so a refusal's message
    is stable whatever the graph's key spelling."""

    def order(node_id):
        try:
            return (0, int(node_id), node_id)
        except (TypeError, ValueError):
            return (1, 0, node_id)

    return sorted((str(node_id) for node_id in node_ids), key=order)


def _chain_source_consumers(loaders, refs):
    """The chain case: the first loader's model reference (the source,
    verbatim) and every reference to the last loader's output — or the
    refusal. Exactly one root (its model comes from outside the loaders);
    walking model links from it must visit every loader exactly once, and
    no non-last loader may feed anything but the next one."""
    roots = [
        loader_id
        for loader_id in loaders
        if str(_loader_model_ref(loaders, loader_id)[0]) not in loaders
    ]
    if len(roots) != 1:
        raise LoraChainUnsupported(
            _sorted_node_ids(roots or loaders),
            f"expected one chain root, found {len(roots)}",
        )
    visited = {roots[0]}
    current = roots[0]
    while True:
        to_current = [ref for ref in refs if str(ref[2][0]) == current]
        next_loaders = [ref for ref in to_current if str(ref[0]) in loaders]
        others = [ref for ref in to_current if str(ref[0]) not in loaders]
        if next_loaders and others:
            raise LoraChainUnsupported(
                _sorted_node_ids([current, others[0][0]]),
                "a loader feeds two consumers",
            )
        if len(next_loaders) > 1:
            raise LoraChainUnsupported(
                _sorted_node_ids([current] + [ref[0] for ref in next_loaders]),
                "a loader feeds two consumers",
            )
        if not next_loaders:
            # The chain's end; whatever consumes it is the consumer set.
            break
        nxt = str(next_loaders[0][0])
        if nxt in visited:
            raise LoraChainUnsupported(
                _sorted_node_ids([current, nxt]), "the model links form a cycle"
            )
        visited.add(nxt)
        current = nxt
    if visited != set(loaders):
        raise LoraChainUnsupported(
            _sorted_node_ids(set(loaders) - visited),
            "an unreachable loader in the graph",
        )
    return list(_loader_model_ref(loaders, roots[0])), others


def _loader_model_ref(loaders, loader_id):
    """The loader's `model` input, which must be a `[src, slot]`
    reference — a loader without one is refused by name."""
    ref = loaders[loader_id].get("inputs", {}).get("model")
    if not _is_ref(ref):
        raise LoraChainUnsupported([loader_id], "loader has no model source reference")
    return ref


def _sampler_source_consumers(workflow):
    """The no-loader case (Decision 6): the source is the one node every
    `KSampler`'s model input references — exactly one, else the refusal —
    and the consumers are every reference to it, any class (the
    base-plus-refiner shape rewires cleanly)."""
    sources = {}
    for node_id, node in workflow.items():
        if not isinstance(node, dict) or node.get("class_type") != "KSampler":
            continue
        ref = node.get("inputs", {}).get("model")
        if not _is_ref(ref):
            raise LoraChainUnsupported(
                [node_id], "KSampler has no model source reference"
            )
        sources.setdefault(str(ref[0]), ref)
    if len(sources) != 1:
        raise LoraChainUnsupported(
            _sorted_node_ids(sources),
            "the KSamplers take model from more than one source",
        )
    source_id, source = next(iter(sources.items()))
    return list(source), _refs_to(workflow, {source_id})


def _rebuild_lora_chain(workflow, variant, lora_stack):
    """Spec §7's pass: rebuild `workflow`'s model chain to `variant.loras`.

    The chain case: the scaffold's `LoraLoaderModelOnly` nodes must form
    one simple chain — its source is the first loader's model reference,
    and whatever consumed its last loader is repointed at the new chain's
    end. The no-loader case: a chain is inserted where none existed, from
    the one node every `KSampler` models from. An empty draw deletes the
    loaders and leaves the consumers at the source (§7's own empty arm).
    Fresh ids are successive integers above the graph's largest numeric
    key, each skipped when the graph already carries it in any spelling.
    A graph whose loaders are not a simple chain — a branch, a fork, two
    roots, a cycle — is refused by name, never rewired on a guess; a
    graph with no `KSampler` at all is a stated no-op (nothing consumes a
    model chain, and the live loops never scaffold from one).
    """
    if not any(
        isinstance(node, dict) and node.get("class_type") == "KSampler"
        for node in workflow.values()
    ):
        return
    loaders = {
        str(key): node
        for key, node in workflow.items()
        if isinstance(node, dict) and node.get("class_type") == "LoraLoaderModelOnly"
    }
    if loaders:
        refs = _refs_to(workflow, set(loaders))
        source, consumers = _chain_source_consumers(loaders, refs)
    else:
        source, consumers = _sampler_source_consumers(workflow)
    for key in list(workflow):
        if str(key) in loaders:
            del workflow[key]
    if not variant.loras:
        for node_id, input_key, _ in consumers:
            workflow[node_id]["inputs"][input_key] = list(source)
        return
    dest_by_name = {entry["name"]: entry["dest"] for entry in lora_stack["pool"]}
    taken = _numeric_ids(workflow)
    counter = max(taken) + 1 if taken else 0
    prev_ref = list(source)
    for name, strength in variant.loras:
        while counter in taken:
            # The collision belt: a "03" beside a "3" never overwritten.
            counter += 1
        taken.add(counter)
        loader_id = str(counter)
        counter += 1
        workflow[loader_id] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "lora_name": pathlib.PurePosixPath(dest_by_name[name]).name,
                "strength_model": strength,
                "model": list(prev_ref),
            },
        }
        prev_ref = [loader_id, 0]
    for node_id, input_key, _ in consumers:
        workflow[node_id]["inputs"][input_key] = list(prev_ref)


def _refuse_no_unetloader(workflow):
    """GN53's refusal arm, isolated so the raise is the whole statement:
    the graph has no `UNETLoader` node — its model comes from a
    `CheckpointLoaderSimple` or similar — so the drawn checkpoint has
    nowhere to be written. A configuration error, refused by name, never
    a silent skip (the `RuleNeverFires` discipline); `workflow` is the
    copy the write pass was about to walk."""
    raise BaseModelUnsupported([], "no UNETLoader node to write the checkpoint into")


def _write_checkpoint(workflow, variant, lora_stack) -> None:
    """GN53's write pass: every `UNETLoader` node in the copied graph takes
    the drawn checkpoint row's dest BASENAME as its `unet_name` — the same
    join key the loader chain's `lora_name` uses (the dest basename, never
    the dest, never the manifest name). A checkpoint name outside the pool
    is the binder's own refusal, never this pass's (the draw only produces
    pool names); a graph with no `UNETLoader` is refused by name."""
    by_name = {entry["name"]: entry for entry in lora_stack.get("checkpoints", ())}
    row = by_name[variant.checkpoint]
    basename = pathlib.PurePosixPath(row["dest"]).name
    unet_nodes = [
        node
        for node in workflow.values()
        if isinstance(node, dict) and node.get("class_type") == "UNETLoader"
    ]
    if not unet_nodes:
        _refuse_no_unetloader(workflow)
    for node in unet_nodes:
        inputs = node.setdefault("inputs", {})
        inputs["unet_name"] = basename


def _substitute(graph, positive_text, variant, lora_stack=None):
    """A deep copy of `graph` with the variant written in: `variant.sampler` (when
    not `None`) into every `KSampler`'s `inputs.sampler_name`, `variant.prompt`
    into every `CLIPTextEncode` whose text equals `positive_text`, and
    `variant.seed` into every `KSampler`'s `inputs.seed`.

    With `lora_stack` (the world's enabled `[mutate.loraStack]` table), the
    copy's loader chain is also rebuilt to `variant.loras`
    (`_rebuild_lora_chain`, which refuses a branched chain by name) and, when
    the variant carries a checkpoint (GN53), every `UNETLoader` node's
    `unet_name` is written from the drawn row (`_write_checkpoint`, which
    refuses a graph with no `UNETLoader` by name). `None`
    — the default at both call sites — is today's behaviour, byte for
    byte: the guard GN38's byte-identity test holds and mutant M8 drops.
    (`stripLoras` beside an enabled `loraStack` never reaches this function:
    `load_rules` refuses the pair by name. `stripLoras` alone — no
    `loraStack` table, or `enable = false` — is applied by the loops after
    this returns.)
    """
    workflow = copy.deepcopy(graph)
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        cls = node.get("class_type")
        inputs = node.setdefault("inputs", {})
        if cls == "KSampler":
            if variant.sampler is not None:
                inputs["sampler_name"] = variant.sampler
            inputs["seed"] = variant.seed
        elif cls == "CLIPTextEncode":
            if inputs.get("text") == positive_text:
                inputs["text"] = variant.prompt
    if lora_stack is None:
        # The axis is off: no loader is touched — today's bytes. The
        # guard GN38's byte-identity test holds; drop it (M8) and the
        # pass fires on untagged worlds the same day.
        return workflow
    if variant.checkpoint is not None:
        # GN53: the checkpoint is drawn from its pool and written, never
        # inherited from the scaffold's stored `unet_name`.
        _write_checkpoint(workflow, variant, lora_stack)
    _rebuild_lora_chain(workflow, variant, lora_stack)
    return workflow


def _stack_entry_ok(entry) -> bool:
    """One `stacks` entry: `loras` a list of two-element `[str, number]`
    lists, `requires` and `triggers` lists of strings, `checkpoint` a
    string or null (absent reads as null)."""
    if not isinstance(entry, dict):
        return False
    loras = entry.get("loras")
    if not isinstance(loras, list) or any(
        not isinstance(pair, list)
        or len(pair) != 2
        or not isinstance(pair[0], str)
        or isinstance(pair[1], bool)
        or not isinstance(pair[1], (int, float))
        for pair in loras
    ):
        return False
    requires = entry.get("requires")
    if not isinstance(requires, list) or any(
        not isinstance(word, str) for word in requires
    ):
        return False
    triggers = entry.get("triggers")
    if not isinstance(triggers, list) or any(
        not isinstance(token, str) for token in triggers
    ):
        return False
    checkpoint = entry.get("checkpoint")
    return checkpoint is None or isinstance(checkpoint, str)


def _load_seed_prompts(path: str) -> tuple[list[str], list | None]:
    """The author's batch file: an object with a non-empty `prompts` array
    of non-empty strings, plus (GN50) an optional `stacks` array of exactly
    one `{loras, requires, triggers}` entry per prompt — absent or `null`
    means uncoupled, the branch's today path. Any other shape exits 2 with
    a named cause."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        print(
            f"mutate: seed file {path}: cannot read ({exc.strerror})", file=sys.stderr
        )
        sys.exit(2)
    except ValueError as exc:
        print(f"mutate: seed file {path}: not JSON ({exc})", file=sys.stderr)
        sys.exit(2)
    bad_shape = (
        not isinstance(data, dict)
        or not isinstance(data.get("prompts"), list)
        or not data["prompts"]
        or any(not isinstance(p, str) or not p for p in data["prompts"])
    )
    if bad_shape:
        print(
            f'mutate: seed file {path}: no "prompts" array of non-empty strings',
            file=sys.stderr,
        )
        sys.exit(2)
    prompts = data["prompts"]
    stacks = data.get("stacks")
    if stacks is not None and (
        not isinstance(stacks, list)
        or len(stacks) != len(prompts)
        or any(not _stack_entry_ok(entry) for entry in stacks)
    ):
        print(
            f'mutate: seed file {path}: "stacks" must be one'
            " {loras, requires, triggers} entry per prompt",
            file=sys.stderr,
        )
        sys.exit(2)
    return prompts, stacks


def _scaffold(conn, world: str):
    """The render row authored prompts expand from: the newest liked render's
    graph, else the newest render's. Neither exits 2 naming the world."""
    row = conn.execute(
        "SELECT r.name, r.prompt, r.seed FROM likes l"
        " JOIN renders r ON l.name = r.name"
        " ORDER BY l.liked_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT name, prompt, seed FROM renders ORDER BY mtime DESC LIMIT 1"
        ).fetchone()
    if row is None:
        print(
            f"mutate: no renders to scaffold authored prompts from in {world}",
            file=sys.stderr,
        )
        sys.exit(2)
    return row


def lora_stack_weights(conn, pool) -> dict[str, float]:
    """The pool's draw weights (GN41): the world's own verdict history,
    read through `conn` — pure in the connection, no file I/O of its own.

    Likes and dislikes are counted per LoRA, never per render: each row's
    graph is walked, and every `LoraLoaderModelOnly` node whose
    `lora_name` is a pool entry's dest BASENAME (Assumption 8's join key)
    gains that pool name one verdict — a LoRA that appears in liked
    renders becomes likelier everywhere, not only in the set it was seen
    in (§8). The dislikes arm is the same walk over `dislikes JOIN
    renders`: the JOIN is the whole point — `dislikes.prompt` is the
    extracted TEXT, never a graph, and a dislike whose renders row the
    rebuild dropped (the PNG deleted, the rebuild run — Assumption 9's
    lifecycle) contributes nothing: the stated limit, not papered over.
    An unparseable graph is skipped, never raised (the module's own
    tolerance), and a loader carrying a file outside the pool is not a
    verdict for anyone. The weight is Beta(2, 2) — `(likes + 2) /
    (likes + dislikes + 4)` — a fixed prior in code, never a manifest
    knob: no history is exactly 0.5, the uniform fallback, so a cold
    world draws the GN39 draw.
    """
    by_basename = {
        pathlib.PurePosixPath(entry["dest"]).name: entry["name"] for entry in pool
    }
    liked = {entry["name"]: 0 for entry in pool}
    disliked = {entry["name"]: 0 for entry in pool}

    def count(query, verdicts):
        for row in conn.execute(query):
            graph = _parse_graph(row["prompt"])
            if graph is None:
                continue
            for node in graph.values():
                if not isinstance(node, dict):
                    continue
                if node.get("class_type") != "LoraLoaderModelOnly":
                    continue
                inputs = node.get("inputs")
                if not isinstance(inputs, dict):
                    continue
                lora_name = inputs.get("lora_name")
                if not isinstance(lora_name, str):
                    continue
                name = by_basename.get(lora_name)
                if name is not None:
                    verdicts[name] += 1

    # _scaffold's own JOIN shape, without its ORDER BY ... LIMIT 1 habit:
    # the weights read the WHOLE history, and the dislikes arm reads
    # graphs, never the text column.
    count("SELECT r.prompt FROM likes l JOIN renders r ON l.name = r.name", liked)
    count(
        "SELECT r.prompt FROM dislikes d JOIN renders r ON d.name = r.name",
        disliked,
    )
    weights = {}
    for entry in pool:
        likes = liked[entry["name"]]
        dislikes = disliked[entry["name"]]
        # Beta(2, 2) — Decision 2's constants, in code not in a manifest.
        weights[entry["name"]] = (likes + 2) / (likes + dislikes + 4)
    return weights


def _report_uncarded(rules: dict, world: str) -> None:
    """One stderr line when enabled LoRAs sit outside the carded pool:
    how many, the world, and the first three names in manifest order —
    a report, never an exit (the uncarded rows still render, just
    LoRA-less, out of the pool)."""
    stack = rules.get("loraStack")
    if stack is None or not stack["uncarded"]:
        return
    uncarded = stack["uncarded"]
    names = ", ".join(uncarded[:3])
    more = ", …" if len(uncarded) > 3 else ""
    line = (
        f"mutate: {len(uncarded)} enabled LoRAs in {world}"
        " have no card and are out of the pool: "
        f"{names}{more}"
    )
    print(line, file=sys.stderr)


def _run_seed_file(args, conn) -> None:
    """The `--seed-file` branch: expand every authored base prompt through the
    grammar onto the one scaffold graph and enqueue the variants as
    kind-`mutate` jobs with an `authored:` source.

    With `stacks` (GN50's coupled draw, one entry per prompt) each slot
    binds its entry's stack instead of drawing its own: `requires` is
    checked per variant against the mutated prompt — a miss drops the
    stack for that variant (no loader, no trigger) and counts on the
    `bound`/`dropped` line printed before the final tally — and the
    triggers are prepended at enqueue, the graph rebuilt to the bound
    stack. GN53: the slot's `checkpoint` rides the same entry (absent or
    null is the draw's own), is validated against the base-model pool
    before any job, and survives a dropped stack — the base model is not
    a `requires` question. Without `stacks` the branch is today's, byte
    for byte.
    """
    prompts, stacks = _load_seed_prompts(args.seed_file)
    row = _scaffold(conn, args.world)
    graph = _parse_graph(row["prompt"])
    if graph is None:
        print(
            f"mutate: {row['name']}: cannot scaffold (unparseable graph)",
            file=sys.stderr,
        )
        sys.exit(2)
    positive_text = _positive_text(graph)
    if positive_text is None:
        print(
            f"mutate: {row['name']}: cannot scaffold (no positive text)",
            file=sys.stderr,
        )
        sys.exit(2)
    base = args.seed if args.seed is not None else row["seed"]
    if base is None:
        print(
            f"mutate: {row['name']}: no scaffold seed (pass --seed)",
            file=sys.stderr,
        )
        sys.exit(2)

    manifest = pathlib.Path(args.root) / "worlds" / args.world / "lab" / "manifest.toml"
    try:
        rules = load_rules(str(manifest))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    _report_uncarded(rules, args.world)
    if rules["loraStack"] is not None:
        # GN41: the world's own verdict history weights the draw, read
        # from the feed at run time — never a manifest knob. The live
        # path is this branch (the supervisor's --seed-file run).
        weights = lora_stack_weights(conn, rules["loraStack"]["pool"])
        rules["loraStack"]["weights"] = weights
    if stacks is not None:
        if rules["loraStack"] is None:
            print(
                f"mutate: seed file {args.seed_file} carries stacks but"
                f" {args.world} has no enabled [mutate.loraStack]",
                file=sys.stderr,
            )
            sys.exit(2)
        # Refused before any job, by slot and name — the bound stack is
        # written from the carded pool or not at all. GN53: the slot's
        # checkpoint is held to the same rule — a name outside the
        # base-model pool is refused before any job too.
        pool_names = {entry["name"] for entry in rules["loraStack"]["pool"]}
        checkpoint_names = {
            entry["name"] for entry in rules["loraStack"].get("checkpoints", ())
        }
        for i, entry in enumerate(stacks):
            for name, _strength in entry["loras"]:
                if name not in pool_names:
                    print(
                        f"mutate: seed file {args.seed_file}: slot {i}"
                        f" names {name}, not in the carded pool",
                        file=sys.stderr,
                    )
                    sys.exit(2)
            checkpoint = entry.get("checkpoint")
            if checkpoint is not None and checkpoint not in checkpoint_names:
                print(
                    f"mutate: seed file {args.seed_file}: slot {i}"
                    f" names checkpoint {checkpoint}, not in the pool",
                    file=sys.stderr,
                )
                sys.exit(2)

    source = f"authored:{pathlib.Path(args.seed_file).name}"
    mutated = 0
    bound = 0
    dropped = 0
    for index, prompt in enumerate(prompts):
        seed = base + index
        stack = None
        requires: list[str] = []
        triggers: list[str] = []
        checkpoint = None
        if stacks is not None:
            entry = stacks[index]
            stack = tuple((name, float(strength)) for name, strength in entry["loras"])
            requires = entry["requires"]
            triggers = entry["triggers"]
            # GN53: absent or null reads as None — the slot's own checkpoint,
            # validated against the pool before any job.
            checkpoint = entry.get("checkpoint")
        try:
            variants = mutate(prompt, rules, seed, args.n, stack=stack)
            mutated += 1
            for j, variant in enumerate(variants):
                if stack is None:
                    effective = variant
                else:
                    # §4: a prompt that ignores `requires` renders
                    # unanchored and the miss is counted — the stack is
                    # dropped for THIS variant, the slot's others may
                    # still bind.
                    missing = [w for w in requires if not _word_in(w, variant.prompt)]
                    met = not missing
                    if met:
                        bound += 1
                    else:
                        print(
                            f"mutate: slot {index} variant {j}: requires"
                            f" unmet ({', '.join(missing)}): stack dropped",
                            file=sys.stderr,
                        )
                        dropped += 1
                    bound_stack = stack if met else ()
                    if met and triggers:
                        # §3.3: the trigger is prepended at enqueue,
                        # never written by the author.
                        text = " ".join(triggers) + " " + variant.prompt
                    else:
                        text = variant.prompt
                    # GN53: a dropped stack keeps its checkpoint — the
                    # base model is not a `requires` question.
                    effective = dataclasses.replace(
                        variant,
                        prompt=text,
                        loras=bound_stack,
                        checkpoint=checkpoint,
                    )
                workflow = _substitute(
                    graph, positive_text, effective, rules.get("loraStack")
                )
                if rules["stripLoras"]:
                    # The interim control threads here, beside but never
                    # inside the axis's own seam (the call line above);
                    # reachable only with `loraStack` absent or inert —
                    # the pair is refused at load.
                    _strip_loras(workflow)
                if args.dry_run:
                    loras = ",".join(f"{n}@{s}" for n, s in effective.loras) or "-"
                    print(
                        f"{row['name']} loras={loras} {variant.seed}"
                        f" {variant.sampler} {effective.prompt}"
                    )
                else:
                    queue.enqueue(
                        conn, "mutate", source, json.dumps(workflow), variant.seed
                    )
        except (RuleNeverFires, LoraChainUnsupported, BaseModelUnsupported) as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(2)
        except VariantsExhausted as exc:
            print(
                f"mutate: seed file {args.seed_file}: prompt {index}:"
                f" {exc.requested} requested, {exc.distinct} distinct"
                f" after {exc.attempts} draws",
                file=sys.stderr,
            )
            continue

    if mutated == 0:
        print(f"no prompt mutated from {args.seed_file}")
        sys.exit(3)

    if not args.dry_run:
        queue.run_once(conn, args.comfy_url)
        if stacks is not None:
            print(f"bound {bound} stacks, dropped {dropped}")
        print(f"authored {mutated} prompts into {mutated * args.n} jobs")


def _run_draw_stacks(args, conn) -> None:
    """The `--draw-stacks` branch (GN50): draw `args.draw_stacks` stacks
    from the world's enabled `[mutate.loraStack]` — the draw the author
    is told about — and write them to
    `<root>/worlds/<world>/lab/prompts/stacks-<UTC>.json` as
    `{"ts", "world", "seed", "stacks"}`.

    The axis off is the grammar's empty arm (one stderr line, stdout
    `drawn 0 stacks in <world>`, exit 3); a pool that cannot fill the
    request within the shared `_MAX_DRAWS` budget per slot is exit 3
    naming the attempts. `--dry-run` prints the JSON and writes nothing.
    The seed is `--seed` else the scaffold row's own (the seed-file
    branch's rule: no renders to scaffold from is exit 2).
    """
    manifest = pathlib.Path(args.root) / "worlds" / args.world / "lab" / "manifest.toml"
    try:
        rules = load_rules(str(manifest))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    if rules["loraStack"] is None:
        print(
            f"mutate: world {args.world} has no enabled [mutate.loraStack];"
            " nothing to draw",
            file=sys.stderr,
        )
        print(f"drawn 0 stacks in {args.world}")
        sys.exit(3)
    _report_uncarded(rules, args.world)
    # The same threading as both loops: the world's own verdict history
    # weights the draw, read from the feed at run time.
    weights = lora_stack_weights(conn, rules["loraStack"]["pool"])
    rules["loraStack"]["weights"] = weights
    if args.seed is not None:
        seed = args.seed
    else:
        row = _scaffold(conn, args.world)
        if row["seed"] is None:
            print(
                f"mutate: {row['name']}: no scaffold seed (pass --seed)",
                file=sys.stderr,
            )
            sys.exit(2)
        seed = row["seed"]
    rng = random.Random(seed)
    n = args.draw_stacks
    try:
        stacks = draw_stacks(rules, n, rng)
    except VariantsExhausted as exc:
        print(
            f"mutate: cannot fill {n} stacks from the carded pool after"
            f" {exc.attempts} draws",
            file=sys.stderr,
        )
        sys.exit(3)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {"ts": ts, "world": args.world, "seed": seed, "stacks": stacks}
    if args.dry_run:
        print(json.dumps(payload))
        return
    prompts_dir = pathlib.Path(args.root) / "worlds" / args.world / "lab" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    path = prompts_dir / f"stacks-{ts}.json"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    print(f"drawn {n} {path}")


def _positive_int(value: str) -> int:
    """An int >= 1 for `--draw-stacks`: anything else is the parser's own
    exit 2."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {value!r}") from None
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be an integer >= 1, got {value!r}")
    return number


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="comfy-mutate")
    parser.add_argument("--world", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--n", type=int, default=3, help="variants per liked render")
    parser.add_argument(
        "--dry-run", action="store_true", help="print variants, write nothing"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="override the render's seed"
    )
    batch_or_draw = parser.add_mutually_exclusive_group()
    batch_or_draw.add_argument(
        "--seed-file",
        default=None,
        help="a JSON file of authored base prompts to expand instead of the likes",
    )
    batch_or_draw.add_argument(
        "--draw-stacks",
        type=_positive_int,
        default=None,
        metavar="N",
        help="draw N stacks from [mutate.loraStack] into lab/prompts, the"
        " coupled draw the author is told about",
    )
    parser.add_argument(
        "--comfy-url",
        required=True,
        help="the generator's loopback base URL",
    )
    args = parser.parse_args(argv)

    conn = queue.open_db(args.root, args.world)

    if args.seed_file is not None:
        _run_seed_file(args, conn)
        return

    if args.draw_stacks is not None:
        _run_draw_stacks(args, conn)
        return

    liked = conn.execute(
        "SELECT r.name, r.prompt, r.seed FROM likes l"
        " JOIN renders r ON l.name = r.name ORDER BY l.liked_at"
    ).fetchall()
    if not liked:
        print(f"no likes in {args.world}")
        sys.exit(3)

    manifest = pathlib.Path(args.root) / "worlds" / args.world / "lab" / "manifest.toml"
    try:
        rules = load_rules(str(manifest))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    _report_uncarded(rules, args.world)
    if rules["loraStack"] is not None:
        # GN41: the same threading as _run_seed_file — both call sites
        # weight the draw from the feed, `mutate()` itself stays pure.
        weights = lora_stack_weights(conn, rules["loraStack"]["pool"])
        rules["loraStack"]["weights"] = weights

    mutated = 0
    for row in liked:
        graph = _parse_graph(row["prompt"])
        if graph is None:
            print(
                f"mutate: {row['name']}: skipped (unparseable graph)",
                file=sys.stderr,
            )
            continue
        text = _positive_text(graph)
        if text is None:
            print(
                f"mutate: {row['name']}: skipped (no positive text)",
                file=sys.stderr,
            )
            continue
        seed = args.seed if args.seed is not None else row["seed"]
        if seed is None:
            print(f"mutate: {row['name']}: skipped (no seed)", file=sys.stderr)
            continue
        try:
            variants = mutate(text, rules, seed, args.n)
            mutated += 1
            for variant in variants:
                workflow = _substitute(graph, text, variant, rules.get("loraStack"))
                if rules["stripLoras"]:
                    # The interim control threads here, beside but never
                    # inside the axis's own seam (the call line above);
                    # reachable only with `loraStack` absent or inert —
                    # the pair is refused at load.
                    _strip_loras(workflow)
                if args.dry_run:
                    loras = ",".join(f"{n}@{s}" for n, s in variant.loras) or "-"
                    print(
                        f"{row['name']} loras={loras} {variant.seed}"
                        f" {variant.sampler} {variant.prompt}"
                    )
                else:
                    queue.enqueue(
                        conn, "mutate", row["name"], json.dumps(workflow), variant.seed
                    )
        except (RuleNeverFires, LoraChainUnsupported, BaseModelUnsupported) as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(2)
        except VariantsExhausted as exc:
            print(
                f"mutate: {row['name']}: {exc.requested} requested,"
                f" {exc.distinct} distinct after {exc.attempts} draws",
                file=sys.stderr,
            )
            continue

    if mutated == 0:
        print(f"no like mutated in {args.world}")
        sys.exit(3)

    if not args.dry_run:
        queue.run_once(conn, args.comfy_url)
        print(f"mutated {mutated} likes into {mutated * args.n} jobs")


if __name__ == "__main__":
    main()
