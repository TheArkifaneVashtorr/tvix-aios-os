---
plan_defect: wrong-fact
plan_defect_secondary: underspecified
mutants_total: 16
mutants_killed: 16
mutants_outside_named: 4
model: opus
---
# Opus gate — seat run ol2, task OL2 — REJECTED

## Summary

The delivered code is **correct against the contract as written** and its test suite is
strong: all 12 mutants the section names die, plus 4 I invented; red-before-green
reproduces; `unit`, `lint` and `nix flake check -L` are green; the subject is
byte-identical and the touches list is exact. On compliance alone this would be an
approval.

It is rejected on **fitness**. The extractor keeps exactly one record kind —
`"type" == "rate_limits"` at the top level of a rollout line — and that kind does not
exist. I scanned every Codex rollout on this machine (`~/.codex/sessions/**/rollout-*.jsonl`,
242 files): **0 top-level `rate_limits` records, 2,569 nested ones**, every single one
under `event_msg` → `payload.type == "token_count"` → `payload.rate_limits`, and every
single one carrying the same nine-key object whose windows live one level deeper still,
under `primary`/`secondary`. Run against the operator's named rollout the tool prints
nothing and **exits 0** — indistinguishable from success. The seat's FACTORY-NOTES claim
is exact and I reproduce it in full below.

The defect is the plan's, not the seat's. §Decisions D1 and Operator question Q1 chose to
type OL2's shape from the spike's own name and land on synthetic fixtures with a gap
claim; Assumption 7 recorded that no `rate_limits` line had ever been seen. That typed
shape is now measured and wrong. The seat was additionally forbidden by §Global
Constraints from fixturing anything from the real file ("every fixture is hand-built
JSONL … never fixtured"), and its own Interfaces block pins the flat six-key row and the
`type == "rate_limits"` predicate, so it had no authority to correct the shape once it
found the mismatch. It did the one thing left open to it — measure, report the mismatch
in FACTORY-NOTES and in the commit body, and write the mismatch into the module docstring
(`tools/codex_limits.py:1-3`) rather than hide it behind green synthetic tests. **That is
the correct behaviour and should be recorded as such**; a seat that had quietly shipped
the same code with no note would be the worse outcome by a wide margin.

The gap claim `codex-rate-limits-shape-unmeasured` therefore does not close: its
`closes_by` requires the finding reported **and** "fixtures corrected if the shape
differs". The shape differs; the fixtures were not corrected. Landing OL2 as it stands
puts a permanently dead tool in the lab tree and marks a task done whose own gap claim
stays open with nothing queued to close it.

## Contract items

Every numbered item of the section's **Interfaces**, taken literally.

| # | contract item | met | evidence |
|---|---|---|---|
| 1 | stdlib only (`json`, `sys`, `pathlib`); never a default path under `~/.codex` | yes | `tools/codex_limits.py:7-9` — the only imports; no `~/.codex` string anywhere in the file |
| 2 | zero argv paths → `usage: codex_limits.py <path> [<path> ...]` on stderr, exit 2, before opening anything | yes | `tools/codex_limits.py:73-75`, the guard is the first statement of `main`; test `test_z5_no_paths` (`tests/test_codex_limits.py:102-103`) |
| 3 | nonexistent path → `codex_limits: <path>: No such file or directory`, exit 2; earlier flushed rows stay printed | yes | `tools/codex_limits.py:80-82`; tests `test_z7_missing_path` (`:117-121`) and the third arm of `test_z9_…` (`:144-148`) |
| 4 | per path in argv order, session resolved once: first `session_meta`'s `payload.id`, else the `<uuid>` of `rollout-<ts>-<uuid>.jsonl`, else the stem, never the literal `unknown` | yes, with one untested edge | `tools/codex_limits.py:15-28` (fallback), `:45-49` (meta), `:67-68` (applied per file); tests `test_z3_…` (`:88-94`), `test_z8_stem_fallback` (`:123-127`), `test_z8_rollout_uuid_fallback` (`:129-131`). No literal `"unknown"` appears in the file. Edge: MINOR-1 below |
| 5 | not valid JSON, or zero valid lines → `codex_limits: <path> is not JSONL`, exit 2, nothing flushed for this file | yes | `tools/codex_limits.py:38-41` (per line) and `:65-66` (zero lines); test `test_z2_invalid_and_empty_are_atomic` (`:81-86`) covers a truncated tail, `""`, `"\n"` and `"not json"` |
| 6 | `"type" == "rate_limits"` is the only kind kept, others skipped | yes as written — **and this is the fitness defect** | `tools/codex_limits.py:50-51`. See MAJOR-1 |
| 7 | `payload` must carry all four of `limit_id`, `used_percent`, `window_minutes`, `resets_at`; missing one → `codex_limits: <path> is missing "<key>" on a rate_limits record`, exit 2, nothing flushed, no further path processed | yes | `tools/codex_limits.py:12`, `:52-57`, `:86-88`; test `test_z6_…` (`:105-115`) subtests each of the three non-`limit_id` keys and passes a second, later path to prove it is never opened |
| 8 | emitted row: six keys in order `ts`, `session`, then the four verbatim — nothing else reaches stdout | yes | `tools/codex_limits.py:58-64` builds the six named keys only; `:67-68` fills `session` in place, preserving order; tests `test_z1_…` asserts `list(row) == KEYS` (`:75`) and `test_z4_payload_extra_does_not_leak` (`:96-100`) |
| 9 | flush-then-continue: a clean path's rows flush before the next opens; a later failure does not un-print earlier ones; all clean → exit 0, rows grouped by path in argv order | yes | `tools/codex_limits.py:76-91` — the print loop is inside the per-path loop, `flush=True` on `:90`; test `test_z9_…` (`:133-148`) covers both the clean pair and both later-failure kinds |
| 10 | `checks.unit` = `pkgs.runCommand "openai-lab-unit"` with `python3` + `pytest` in `nativeBuildInputs`, copying `${self}`, `chmod -R u+w`, `pytest tests/test_codex_limits.py -q`, `touch "$out"`; no `\|\| true` | yes | `flake.nix:39-51`. The delivered form splits the section's `&&` chain across lines and relies on Nix's implicit `set -e`, which §Global Constraints states as the governing rule; I proved failure still propagates (Z10 below). No `\|\| true` in the tree |

**Files** — `Create: tools/codex_limits.py, tests/test_codex_limits.py`; `Modify: flake.nix`.
All three present, nothing else. **Facts** — the section warns that
`factory-codex-usage.py`'s `except …: continue` idiom is a *different* contract; the
delivered code does not copy it (`tools/codex_limits.py:40-41` raises where the idiom
would `continue`), so that trap was avoided.

### The measurement the section's Step 1 demanded

```
$ nix develop -c python3 tools/codex_limits.py \
    /home/dalhaka/.codex/sessions/2026/09/08/rollout-2026-09-08T21-31-07-01a08401-3981-7922-9a04-00906416df84.jsonl
EXIT=0
stdout lines: 0
--- stderr ---
(empty)
```

The file is 588,991 bytes, 151 lines, all 151 valid JSON. Its own histogram:

```
top-level types: {'session_meta': 1, 'event_msg': 65, 'response_item': 63,
                  'world_state': 1, 'turn_context': 1, 'token_usage_record': 20}
unparseable lines: 0
event_msg payload types: {'task_started': 1, 'item_completed': 43,
                          'token_count': 20, 'task_complete': 1}
top-level type == rate_limits: 0
payloads carrying rate_limits: 20
first nested sample:
["event_msg", "token_count", {
  "limit_id": "codex", "limit_name": null,
  "primary": {"used_percent": 1.0, "window_minutes": 10080, "resets_at": 1789460350},
  "secondary": null,
  "credits": {"has_credits": false, "unlimited": false, "balance": "0"},
  "individual_limit": null, "spend_control_reached": null,
  "plan_type": "prolite", "rate_limit_reached_type": null}]
```

Widened to the whole machine (type histogram only, no payload content read out):

```
rollout files scanned: 242
top-level type == 'rate_limits': 0
payloads carrying a rate_limits object: 2569
  nested key set x2569: ('credits', 'individual_limit', 'limit_id', 'limit_name',
                         'plan_type', 'primary', 'rate_limit_reached_type',
                         'secondary', 'spend_control_reached')
```

One key set, 2,569 records, zero exceptions. The seat's FACTORY-NOTES claim holds
exactly. Note what the shape actually implies for the contract, beyond the nesting:
`limit_id` is a *plan* id (`"codex"`), not a window name, and `used_percent`,
`window_minutes` and `resets_at` live inside `primary` and (when non-null) `secondary` —
so the section's six-key flat row cannot represent one real record without a window
discriminator it does not have. This is not a one-line path fix.

## Red before green

The section's Step 1 is "write the failing tests and run them red". The base
`999de984a86d6f2ea216093d62e669aafed67eab` has neither `tools/codex_limits.py` nor
`tests/`, so the base implementation state is simply the script's absence. Branch tests
against that state, in a scratch copy of the clone:

```
=== RED: base state (implementation absent, as at 999de98) ===
FAILED tests/test_codex_limits.py::LimitsTests::test_z7_missing_path - Assert...
FAILED tests/test_codex_limits.py::LimitsTests::test_z8_rollout_uuid_fallback
FAILED tests/test_codex_limits.py::LimitsTests::test_z8_stem_fallback - Asser...
FAILED tests/test_codex_limits.py::LimitsTests::test_z9_paths_flush_in_order_and_survive_later_failure
17 failed, 2 passed in 0.24s
=== RESTORED ===
11 passed, 8 subtests passed in 0.36s
```

The two nominally "passed" at red are `test_z2_…` and `test_z6_…`, whose parent nodes
pytest reports PASSED while their subtests are counted separately — both contribute
SUBFAILED lines to the 17. No test in the file is vacuous: every one of the eleven is
covered by at least one killed mutant below.

## Mutants

`mutants_total: 16`, `mutants_killed: 16`, `mutants_outside_named: 4`. Each was applied
to a scratch copy, the killing test run, and the file restored from a byte copy before
the next. The section names twelve (Z1 and Z9 each name two).

| mutant | mutation applied | killed by | failing line |
|---|---|---|---|
| Z1a | delete the `if record.get("type") != "rate_limits": continue` filter (`:50-51`) | `test_z1_…` | `AssertionError: 2 != 0 : codex_limits: …/mixed.jsonl is missing "limit_id" on a rate_limits record` |
| Z1b | emit `{key: payload[key] for key in FIELDS if key != "resets_at"}` (`:62`) | `test_z1_…` | `tests/test_codex_limits.py:75: AssertionError` (the `list(row) == KEYS` assertion) |
| Z2 | `except (ValueError, RecursionError): continue` instead of raising (`:40-41`) | `test_z2_…` | `AssertionError: 0 != 2` — `SUBFAILED(text='…rate_limits…}\n{"type":')` |
| Z3 | cache the first file's resolved session module-wide and reuse it for every later path | `test_z3_…` | `tests/test_codex_limits.py:91: AssertionError` |
| Z4 | `**payload,` instead of the six named keys (`:62`) | `test_z4_…` | `tests/test_codex_limits.py:100: AssertionError` (`"raw"` leaks) |
| Z5 | replace the argv guard with `_ = paths[0]` (`:73-75`) | `test_z5_no_paths` | `AssertionError: 1 != 2` (an `IndexError` traceback, not the documented line) |
| Z6 | skip `window_minutes` in the validation loop and switch the emit to `payload.get(key)` (`:53-57`, `:62`) | `test_z6_…` | `AssertionError: 0 != 2` — `SUBFAILED(key='window_minutes')` |
| Z7 | delete the `except FileNotFoundError` arm (`:80-82`) | `test_z7_missing_path` | `AssertionError: 1 != 2` (uncaught traceback) |
| Z8 | `return "unknown"` in place of `return stem` (`:28`) | `test_z8_stem_fallback` | `tests/test_codex_limits.py:125: AssertionError` |
| Z9a | `for name in reversed(paths)` (`:76`) | `test_z9_…` | `tests/test_codex_limits.py:136: AssertionError` |
| Z9b | accumulate every path's rows and print once after the loop (`:89-91`) | `test_z9_…` | `+ {"ts": …, "session": "a", "limit_id": "a2", …}` — A's rows lost from the expected prefix |
| Z10 | `pytest tests/test_codex_limits.py -q \|\| true` in `flake.nix:49`, with `test_z1_…`'s expected count changed 2 → 3 | `checks.unit` itself | as delivered: `EXIT=1`, `> FAILED … test_z1_… - AssertionError: 2 != 3` in the build log. With `\|\| true`: **`EXIT=0`** on the identical break. Both arms reproduced |

Four mutants the section does not name, all killed:

| mutant | mutation | killed by |
|---|---|---|
| O1 | drop the `and not found_session` guard, so the *last* `session_meta` wins (`:45`) | `test_z3_…` |
| O2 | drop the `if not isinstance(record, dict): continue` guard (`:43-44`) | `test_valid_unrelated_json_produces_no_rows` |
| O3 | drop the `if not valid_lines:` empty-file check (`:65-66`) | `test_z2_…`, `SUBFAILED(text='')` |
| O4 | `return 1` instead of `return 2` on the usage path (`:75`) | `test_z5_no_paths` |

One further confirmation, because Z2's and Z6's discriminating rows live inside
`subTest` blocks and a pytest without subtest support could swallow them: the Z6 mutant
was also run under `nix build .#checks.x86_64-linux.unit` and the build failed —
`SUBFAILED(key='window_minutes') … AssertionError: 0 != 2`, `EXIT=1`. Subtest failures
do reach the check.

## Checks

All run in a fresh clone of `task/OL2` (`git clone -q --branch task/OL2 …`), head
`9db7f5be90090c07320eca549d26f85c77670aef`.

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **exit 0** — `openai-lab-unit> 11 passed, 8 subtests passed in 0.36s` |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **exit 0** — `formatted 4 files (0 changed)`, `All checks passed!`, `2 files already formatted` |
| `nix flake check -L` | **exit 0** — `all checks passed!` (includes `lab-vm`) |
| `nix develop -c ruff check tools tests` | `All checks passed!` |
| `nix develop -c ruff format --check tools tests` | `2 files already formatted` |
| `nix develop -c githooks/pre-commit` | **N/A** — no `githooks/` in this repo; §Decisions D6 states OL1 ships no hook |
| `repomap.py write` + `git diff --exit-code docs/MAP.md` | **N/A** — `openai-lab` has no `docs/MAP.md` and no `pkgs/evidence`; §Decisions D2 fixes the lab's own `checks.${system}` names as the acceptance names for a repo attributed elsewhere |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` (in `~/nixos-agent-env`) | **silent, exit 0**; the live repo's `git status --short` stayed empty |

No red check. Both acceptance names the section gives (`unit`, `lint`) are green on
`--rebuild`.

## Touches and commit

**touches:** `tools/codex_limits.py, tests/test_codex_limits.py, flake.nix`.

```
$ git diff 999de984a86d6f2ea216093d62e669aafed67eab..HEAD --stat
 flake.nix                  |  13 ++++
 tests/test_codex_limits.py | 156 +++++++++++++++++++++++++++++++++++++++++++++
 tools/codex_limits.py      |  95 +++++++++++++++++++++++++++
 3 files changed, 264 insertions(+)
```

Three files, all inside `touches`, nothing outside, no deviation to explain. No fixture
files were left behind (`tests/` holds only `test_codex_limits.py`; every fixture is
built into a `tempfile.TemporaryDirectory` at run time, `tests/test_codex_limits.py:35-42`).
No secret, no key, no `/var/lib/secrets` path, no real `~/.codex` session id: the two
fixture UUIDs are `11111111-2222-4333-8444-555555555555` and
`aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee` (`:13-14`), plainly invented. The plan file is in
`nixos-agent-env` and is untouched. No board commit.

**Commit:** exactly one, `9db7f5b`. Subject verified byte-identical against the
section's `commit subject` with `cmp` — `SUBJECT BYTE-IDENTICAL`. Body states the why,
pastes the red and the green, and lists the mutant per Z row as §Global Constraints
requires. Trailers after a blank line, in order:

```
Generated-By: codex-cli 0.153.4 / gpt-6-astra (codex exec, factory run ol2)
Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>
```

The body also carries the Operator-item-3 measurement in full, unprompted and
unflattering to its own deliverable. Credit where it is due.

## Findings

### MAJOR-1 — the extractor matches nothing that exists; it exits 0 with an empty stream against every real Codex rollout

`tools/codex_limits.py:50-51`

```python
            if record.get("type") != "rate_limits":
                continue
```

There is no rollout line with `"type": "rate_limits"`. Measured across
`~/.codex/sessions/**/rollout-*.jsonl`, 242 files: **0** such records, **2,569** records
where the rate-limit object is nested at `event_msg` → `payload.rate_limits`, all with
one nine-key shape whose windows are a further level down under `primary`/`secondary`.
Against the operator's named path the tool produces `EXIT=0`, `stdout lines: 0`, empty
stderr — a silent success that is byte-identical to "this rollout had no limits", so a
caller cannot tell a dead tool from an idle session.

This is a fitness failure, not a compliance failure. §Interfaces item 6 says exactly what
the code does, and the code does it well. But OL2 exists to turn Codex rate limits into
JSONL, and the delivered tool cannot read one. Landing it puts a permanently dead script
in the lab tree with green tests standing over it — the worst kind of green.

The shape error is the **plan's**: §Decisions D1 and Operator question Q1 elected to type
the shape from the spike's own name rather than measure it, Assumption 7 recorded that no
`rate_limits` line had ever been seen anywhere, and the section's Interfaces then pinned
that guess as a contract. `plan_defect: wrong-fact`. The seat could not have fixed it
inside its brief: §Global Constraints forbid fixturing from the real file, the Interfaces
block pins the flat six-key row, and Z1–Z9 all assert it. It measured, it reported, and it
wrote the mismatch into the module's own docstring (`tools/codex_limits.py:1-3`:
"Real nested event_msg/token_count rate limits are outside this interface") instead of
letting synthetic green tests speak for it. That is the right call and the reason this
review can be written at all.

Also note what a corrected contract must decide, which the current one cannot express:
`limit_id` is a plan id (`"codex"`), and each record carries up to two windows
(`primary`, `secondary`) each with its own `used_percent`/`window_minutes`/`resets_at`.
A fit row needs a window discriminator. This is a re-spec, not a patch.

### MAJOR-2 — the gap claim `codex-rate-limits-shape-unmeasured` does not close, so landing would record a task done over an open, unowned gap

`docs/ledger/claims.toml` in `nixos-agent-env`, quoted from the plan's §Dispatch Step 0:

```
closes_by = "OL2's own task session reads the rollout path the operator names
(Operator item 3) and reports the finding in FACTORY-NOTES, with fixtures corrected
if the shape differs, or five Codex rate_limits lines read without a mismatch"
```

Two of the three arms fail. The shape differs (MAJOR-1), so the "five lines without a
mismatch" arm is out; the fixtures were **not** corrected — every one still asserts the
flat shape (`tests/test_codex_limits.py:17-27`, `rate()` emitting
`{"type": "rate_limits", "payload": {limit_id, used_percent, window_minutes, resets_at}}`).
Only the reporting arm is satisfied.

The seat had no route to the second arm: its brief is §Global Constraints + §Assumptions +
its own section, and the `closes_by` text lives in §Dispatch, which a seat never sees;
worse, its own Interfaces block forbids the shape it would have had to write. So this is
the plan's defect too — `underspecified` as the secondary class: the section's Step 1
orders the measurement but says nothing about what to do when it comes back different,
while the claim ledger silently expected a correction the section prohibited.

Landing as-is marks OL2 done and leaves the claim open with no task queued against it.

### MINOR-1 — a first `session_meta` carrying no `id` consumes the "first meta" slot, and a later one with an `id` is ignored

`tools/codex_limits.py:45-49`

```python
            if record.get("type") == "session_meta" and not found_session:
                found_session = True
                payload = record.get("payload")
                if isinstance(payload, dict) and "id" in payload:
                    session = payload["id"]
```

`found_session` is set on the first `session_meta` line whether or not it yields an id, so
a second `session_meta` that does carry one can never be reached. Probed:

```
--- P1: first session_meta has no id, second does ---
{"ts": "T", "session": "nometa", "limit_id": "x", ...}
exit=0
```

The row falls back to the stem while a real id sits in the file. §Interfaces says
"the first `session_meta`'s `payload.id`" and is silent on a first meta without one, so
this is a stated contract with an untested edge rather than a violation — recorded, not
counted against the verdict. Every real rollout I scanned has exactly one `session_meta`
per file and it carries an `id`, so nothing observable turns on it today.

### MINOR-2 — a directory argument produces an uncaught `IsADirectoryError` traceback, the exact failure class Z7 exists to prevent

`tools/codex_limits.py:36`, with the handlers at `:80-88` catching only
`FileNotFoundError`, `UnicodeError` and `ValueError`.

```
--- P2: a directory as the path ---
Traceback (most recent call last):
  ...
  File ".../tools/codex_limits.py", line 36, in read_rows
    with path.open(encoding="utf-8") as source:
IsADirectoryError: [Errno 21] Is a directory: '.../probe/adir.jsonl'
exit=1
```

§Interfaces names "a nonexistent path" and nothing wider, so no stated contract is
violated. But Z7's whole point is that an unreadable path must produce one documented
stderr line and exit 2, never a traceback — and the sibling `OSError` slips through.
A `PermissionError` would behave the same way. Untested, unnamed, cheap to close if OL2
is re-spec'd.

## Verdict

**REJECTED.**

Not for anything the seat did. Compliance is clean across the board: 16/16 mutants dead
(12 named, 4 mine), red-before-green reproduced, `unit`/`lint`/`nix flake check` green on
`--rebuild`, touches exact, subject byte-identical, trailers correct, no secret, no
deviation. On the section as written this is a good piece of work, and the honest
disclosure of a result that damns its own deliverable is the behaviour the harness is
supposed to produce. Record it that way in the gate record: the failure here is upstream
of the seat.

It is rejected because a contract-correct extractor that returns zero rows and exit 0
against 242 of 242 real rollouts is not fit to land, and because the gap claim that was
supposed to cover exactly this risk does not close.

Recommended next move — for the orchestrator, not the seat: re-spec OL2's Interfaces
against the measured shape (`event_msg` → `payload.type == "token_count"` →
`payload.rate_limits`, with `primary` and non-null `secondary` each yielding a row and a
window discriminator in the key set), keep the whole existing test scaffold — its
structure, its Z-row discipline and its per-file atomicity are all reusable — and relaunch
as `ol2b` with the corrected Interfaces and hand-built fixtures in the real shape. The
claim closes on that landing, not this one.
