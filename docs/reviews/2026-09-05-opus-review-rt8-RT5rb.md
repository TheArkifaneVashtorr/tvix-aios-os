---
reviewer: opus
majors: 1
minors: 4
mutants_total: 27
mutants_killed: 27
---
# Opus gate — seat run rt8, task RT5rb — APPROVED

## Summary

Branch `task/RT5rb` @ `7ea5e1664909fbec8a3faa256ec52031a467fce7`, base
`b6c5a220b0bc7cb659fc4138d08ebc36c5630fed`, **one** commit, subject
byte-identical to the plan (`cmp` against the plan's literal: identical), both
trailers present (`Generated-By:` ×1, `Co-Authored-By: Claude Fable 5.1
<noreply@anthropic.com>` ×1), and all five touched files inside the plan's
`touches`. Reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-rt8-RT5rb`.
(The base is the `integ/sc9` integrate commit, not RT5r's head, so the diff
carries RT5r's whole approved body as well as the fix round.)

Both rt7 MAJORs are closed and all three rt7 MINORs are fixed:

* **rt7 MAJOR-1 (json.load outside the fail-closed guard).** `main()` now
  reads stdin with a bound, pre-scans bracket nesting, and runs `json.loads`
  **inside** a `try/except BaseException` (`hook-guard.py:530-551`). Every one
  of the rt7 crash payloads now denies with exit 0: depth-100000 (600 KB),
  depth-52031 (312 KB, rt7's exact crash point), 5 MiB stdin, non-UTF-8 stdin,
  a top-level array, empty stdin. I additionally fuzzed 179 crafted payloads
  (tool names of every JSON type, `tool_input` of every JSON type, truncated
  JSON, NUL bytes, a 100,000-brace string, a 9,000-deep array chain): **zero
  non-zero exits**.
* **rt7 MAJOR-2 (M-D survives).** The audit-subject test payload is now a
  routing-table row at the top level with the offending id nested under it, and
  a second test pins the LIFO walk order. I confirmed the order independently
  by importing the guard and walking the payload: `['deepseek/deepseek-v4-flash',
  'z-ai/glm-5.3']` at depths `[0, 2]` — so `model_ids[0]` is the row, and the
  subject assertion discriminates. **M-D now dies** (test 73).
* rt7 MINOR-1 → a non-object `tool_input` on `subagent`/`subagent_fork`/
  `workflow` denies (`null`, `[]`, `"x"`, `5`, and the list-carrying-a-model
  shape that used to sail through); `bash`/`edit`/`write` keep the coercion.
* rt7 MINOR-2 → the depth budget is now exactly 64: a non-row model at depth 64
  is denied **by the model rule and named**, depth 65 is the budget overrun, a
  row at depth 64 is allowed.
* rt7 MINOR-3 → `hooks.json` is built with `jq -n --arg … @sh`; a path
  containing `"` and a space round-trips, and so does one containing `'` and
  `$`.

Every claim in the seat's prose was checked and holds: 89/89 bats; six tests
red on RT5r and green on RT5rb; the seven planned mutations die (I split the
depth off-by-one into both directions, so nine rows) and rt7's 18 other
mutations still die — **27/27 killed, no survivors**; unit, host-core, lint,
ruff and shellcheck all green.

No MAJORs. Four MINORs, all documentation or process.

## The deviation

**The plan's pre-scan bound `nesting > 64` was raised to `_MAX_PARSE_NESTING =
10_000` (`pkgs/dsh-openrouter/hook-guard.py:135`). ACCEPTED.**

The plan's item 1 ("nesting > 64") and item 4 ("a model at depth 64 is reached
by the model rule") are in direct conflict: the payload wrapper adds two
brackets before the walk's depth 0, so a literal 64-nesting pre-scan would
reject every payload whose model sits deeper than walk-depth 62 as "too deep"
and item 4's tests could never pass. The implementer's reading is right, and it
named the conflict.

Against the gate's acceptance conditions:

| condition | verdict |
|---|---|
| a small, bounded constant | `_MAX_PARSE_NESTING = 10_000` — `hook-guard.py:135` |
| documented with its reason | at the constant, `hook-guard.py:127-134`: "far above the model rule's 64-deep reach … and far below the ~52,000 nesting at which the decoder itself raises RecursionError". **The number itself is not repeated in the module docstring or the runbook — MINOR-1.** |
| depth-100000 denies with exit 0 | `deny "payload could not be parsed: too deep"`, exit 0, 600102 payload bytes, 0.10 s |
| 5 MiB denies with exit 0 | `deny "payload could not be parsed: too large"`, exit 0 |
| nesting just above the bound denies "too deep" | payload nesting **10001** → `too deep`, exit 0 |
| nesting just below the bound parses | payload nesting **10000** → parses, then denies `tool_input too deep/large to inspect` (the walk's own budget), exit 0. The boundary is exact in both directions. |
| `json.load` can never raise `RecursionError` below the bound | **it can — and it does not matter, which is the stronger result.** See below. |

I could not prove the last condition as literally written, and it turns out the
guard does not need it. Under the default 8 MiB stack, nesting 10000 parses
fine (measured above). Under a constrained stack it does not — and the guard
still returns 0:

```
ulimit -s 8192 -> rc=0 out={"…","reason":"tool_input too deep/large to inspect",…}
ulimit -s 2048 -> rc=0 out={"…","reason":"tool_input too deep/large to inspect",…}
ulimit -s 1024 -> rc=0 out={"…","tool":"","reason":"payload could not be parsed: RecursionError",…}
ulimit -s  512 -> rc=0 …RecursionError…
ulimit -s  256 -> rc=0 …RecursionError…
ulimit -s   64 -> rc=1, stdout 0 bytes   <- the Python interpreter itself cannot start
                 ("Fatal Python error: pycore_init_builtins", `python3 -c 'print(1)'` also rc=1)
```

So at every stack size at which CPython can run at all, a `RecursionError`
from `json.loads` inside the bound is caught by the `except BaseException` at
`hook-guard.py:545` and becomes a **deny at exit 0** — not the rt7 bypass
(exit 1, empty stdout). Mutation **M-B** (pre-scan removed) is the same
experiment from the other side: it leaves the exit-0 contract intact and only
changes the reason string from `too deep` to `RecursionError`, which is exactly
why it is caught by test 76 and by nothing else.

Two more probes on the bound's soundness. `sys.setrecursionlimit(50)` does not
make `json.loads` fail at nesting 10000 — CPython's C scanner uses the C-stack
check, not the Python recursion limit — and driving `main()` directly with a
recursion limit of 20 still returns `rc=0` with a deny. And the pre-scan is
string-aware for real: `_max_bracket_nesting('{"a":"{{{{{{{"}')` → 1, and a
payload carrying 100,000 `{` **inside a JSON string** parses normally rather
than tripping "too deep".

Cost: the pre-scan is a pure-Python per-character loop, 0.0 ms at 1 KiB, 2.1 ms
at 64 KiB, 98.7 ms at the 4 MiB worst case — negligible for real tool calls.

The bound is load-bearing in the sense the plan meant (mutation **M-H**, the
bound raised to 10⁶, dies on test 76), and it is defence in depth rather than
the safety property itself; the safety property is the `BaseException` region.
That is the right shape. Accepted.

## Rule behaviour

Every row driven by feeding the built `hook-guard` compact JSON
(`ensure_ascii=False`, `separators=(",",":")`) on stdin, exactly as the bridge
sends it, with `--routing-table docs/ledger/routing.toml` unless the row says
otherwise. OpenRouter rows in that table are `deepseek/deepseek-v4-flash` and
`deepseek/deepseek-v4-pro-0813`; `z-ai/glm-5.3`, `moonshotai/kimi-k3`, `opus`,
`sonnet`, `fable` are non-rows.

### 1 — deeply nested payloads

| case | expected | observed | exit |
|---|---|---|---|
| depth-100000 subagent, top-level non-row model (600102 B) | deny, "could not be parsed"/"too deep" | deny `payload could not be parsed: too deep` | 0 |
| depth-52031 (rt7's crash point, 312288 B) | deny | deny `payload could not be parsed: too deep` | 0 |
| depth-5000 (30102 B) | deny | deny `tool_input too deep/large to inspect` (parses; the walk's budget fires) | 0 |
| depth-1000 (6102 B) | deny | deny `tool_input too deep/large to inspect` | 0 |
| payload nesting 10000 (chain 9998) | parses | deny `tool_input too deep/large to inspect` | 0 |
| payload nesting 10001 (chain 9999) | "too deep" | deny `payload could not be parsed: too deep` | 0 |

### 2 — the size bound

| case | expected | observed | exit |
|---|---|---|---|
| 5 MiB valid JSON (one huge string field) | deny, "too large" | deny `payload could not be parsed: too large` | 0 |
| 5 MiB of raw `a` | deny | deny `… too large` | 0 |
| 3 MiB valid bash payload, benign command | parses, judged normally | ALLOW (empty stdout), 0.27 s | 0 |
| 3 MiB valid bash payload naming a non-row model | deny by the model rule | deny `sub-agent model z-ai/glm-5.3 is not a row of …` | 0 |
| exactly 4194304 B | parses | ALLOW (empty stdout) | 0 |
| 4194305 B | deny | deny `… too large` — the bound is off-by-one exact | 0 |

### 3 — unparsable payloads

| case | expected | observed | exit |
|---|---|---|---|
| top-level array | deny | deny `payload could not be parsed: ValueError` | 0 |
| bare string `"hello"` | deny | deny `… ValueError` | 0 |
| bare number `5`, bare `null` | deny | deny `… ValueError` | 0 |
| empty stdin | deny | deny `payload could not be parsed: JSONDecodeError` | 0 |
| invalid JSON bytes `{not json at all` | deny | deny `… JSONDecodeError` | 0 |
| non-UTF-8 stdin (`\xff\xfe\x00…`) | deny | deny `payload could not be parsed: UnicodeDecodeError` | 0 |
| valid JSON, `hook_event_name != PreToolUse` | allow | ALLOW (empty stdout) | 0 |

### 4 — the discriminating audit subject

| case | expected | observed | exit |
|---|---|---|---|
| `{"model":"deepseek/deepseek-v4-flash","steps":[{"model":"z-ai/glm-5.3"}]}` (workflow) | subject = the non-row id | reason `…z-ai/glm-5.3 is not a row of…`, **subject `z-ai/glm-5.3`** | 0 |
| the same payload, unreadable table (the implementer's walk-order helper) | subject = `model_ids[0]` = the ROW | subject `deepseek/deepseek-v4-flash` — so the walk yields the row first | 0 |
| independent instrumentation: `list(_walk_model_ids(payload))` | row first | `['deepseek/deepseek-v4-flash', 'z-ai/glm-5.3']`, depths `[0, 2]` | — |

### 5 — non-object `tool_input`

| case | expected | observed | exit |
|---|---|---|---|
| `workflow` / `subagent` / `subagent_fork` × `null`, `[]`, `"x"`, `5`, `[{"model":"z-ai/glm-5.3"}]` (15 rows) | deny "not an object" | all 15: deny `model rule could not be evaluated: tool_input is not an object`, subject `""` | 0 |
| `bash` × `null`, `[]`, `"x"`, `5` | today's coercion (allow-on-error) | ALLOW, empty stdout — `tool_input` coerced to `{}`, `command` absent, no rule fires | 0 |
| `edit` × `null` | coercion pinned | ALLOW, empty stdout | 0 |

### 6 — the depth budget is exactly 64

| case | expected | observed | exit |
|---|---|---|---|
| non-row model at walk depth 63 | model rule, id named | deny `sub-agent model z-ai/glm-5.3 is not a row of …`, subject `z-ai/glm-5.3` | 0 |
| **non-row model at walk depth 64** | **model rule, id named** | deny `sub-agent model z-ai/glm-5.3 is not a row of …`, subject `z-ai/glm-5.3` | 0 |
| **non-row model at walk depth 65** | **budget** | deny `tool_input too deep/large to inspect`, subject `""` | 0 |
| non-row model at depth 66 | budget | deny `tool_input too deep/large to inspect` | 0 |
| **ROW model at depth 64** | **allow** | ALLOW (empty stdout) | 0 |
| ROW model at depth 65 | budget | deny `tool_input too deep/large to inspect` | 0 |

`_DEPTH_BUDGET = 64` at `hook-guard.py:125`; the header comment says 64
(`:121-123`) and `docs/runbooks/lanes.md:263` says "a depth budget of exactly
**64** (a model at depth 64 is named in the reason, depth 65 is the budget
overrun)".

### 7 — the wrapper escapes the table path

Driven end-to-end: `FACTORY_ROUTING_TABLE='/tmp/a "b"/routing.toml'
dsh-openrouter --dump-config`, then `jq` over the written `hooks.json`.

```
$ jq -r '.hooks.PreToolUse[].hooks[].command' hooks.json
exec '/nix/store/…-hook-guard/bin/hook-guard' --routing-table '/tmp/a "b"/routing.toml'
… (all three matchers identical)

$ shlex.split → bash                              -> '/tmp/a "b"/routing.toml' MATCH
                edit|write                        -> '/tmp/a "b"/routing.toml' MATCH
                subagent|subagent_fork|workflow    -> '/tmp/a "b"/routing.toml' MATCH
```

Invoking the guard exactly as `hooks.json` says (`bash -c "$CMD"`) with a
non-row model denies naming that table, and with a row model allows — both
`rc=0`. A harder path (`/tmp/it's a $dir/routing.toml`) also round-trips:
`jq @sh` emits `'/tmp/it'\''s a $dir/routing.toml'` and the guard reads it
intact. `jq` is in the wrapper's `runtimeInputs` (`default.nix:77`).

### 8 — RT5r's matrix still holds

Every bash spelling denies (`--model ID`, `--model=ID`, `--model "ID"`,
`--model 'ID'`, `--model="ID"`, `env OPENROUTER_MODEL=ID`,
`OPENROUTER_MODEL="ID"`, `--model<TAB>ID`, `\`+newline continuation,
`bash -c '…'`), all exit 0. Row models allow (`--model
deepseek/deepseek-v4-flash`, `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813`,
no model at all). `opus`/`sonnet`/`fable` — claude rows — all deny. Structured:
row allows, no-model allows, `steps[*].model` non-row denies,
`subagent_fork` non-row denies, `provider` + claude model denies. Tables:
non-UTF-8 → `model rule could not be evaluated: UnicodeDecodeError` (structured
and bash), malformed and missing → `routing table unreadable at <path>`.
Budgets: 20,000 keys → deny (budget), 9,000 keys without a model → **allow**,
9,000 keys + a non-row model → deny by the model rule. The unrelated rules are
untouched: `sudo nixos-rebuild switch` → deny, `edit /etc/passwd` → deny.

All 10 `run … hook-guard` invocations in `tests/unit/70-dsh-openrouter.bats`
(lines 633, 644, 652, 738, 764, 804, 815, 827, 949, 1061) are immediately
followed by `[ "$status" -eq 0 ]`.

## Checks

Run in the clone on a clean tree (`git status --porcelain` empty).

| command | exit | wall |
|---|---|---|
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 0 — **89/89 ok** | 27 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 | 1 s (cached) |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0 — 189 tests ok | 31 s |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | 0 | 19 s |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 — "All checks passed!", 88 files formatted (0 changed) | 4 s |
| `nix develop -c ruff check pkgs/dsh-openrouter` | 0 — "All checks passed!" | 0.4 s |
| `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | 0 | 0.5 s |

No failures; no tail to paste.

## Red before green

`pkgs/dsh-openrouter/hook-guard.py` and `pkgs/dsh-openrouter/dsh-openrouter.sh`
replaced with `git -C /home/dalhaka/factory/ws/rt7/RT5r show task/RT5r:<path>`
(RT5rb's tests and `default.nix` kept), then `nix develop -c bats
tests/unit/70-dsh-openrouter.bats`:

```
not ok 76 hook-guard refuses a 100000-deep payload as unparsable: deny 'too deep', exit 0
not ok 77 hook-guard refuses a >4 MiB stdin as too large, exit 0
not ok 78 hook-guard denies a top-level JSON array (not an object), exit 0
not ok 79 a sub-agent tool whose tool_input is not an object is denied; bash keeps the coercion
not ok 80 a non-row model at depth exactly 64 is reached by the model rule; depth 65 is the budget overrun
not ok 83 hooks.json JSON-escapes the routing-table path: a quote and a space round-trip
```

Exactly six red — the plan's step-1 tests (1)–(3), (5), (6), (7) — and **no
pre-existing test went red**: 1–75, 81, 82 and 84–89 all stayed ok. Test 77
fails on `[ "$status" -eq 0 ]` itself, i.e. the RT5r guard *crashes* on it,
which is the rt7 bypass reproduced.

The plan's step-1 test (4) — the discriminating audit-subject payload and its
walk-order helper (tests 73, 74) — correctly does **not** go red here, and I
verified that is not a gap: rt7 MAJOR-2 was a *test* defect, not an
implementation defect (rt7's own matrix row 6c showed RT5r already produced the
right subject for this payload). What pins it is mutation M-D, which survived
in rt7 and dies here.

`git checkout --` restored the tree (`git status --porcelain` empty) and the
suite is 89/89 green again.

## Mutation table

Each row: `git checkout -- .` → apply → `git diff --stat` asserted non-empty →
`nix develop -c bats tests/unit/70-dsh-openrouter.bats` (a **fresh**
`nix develop` per row, so the flake rebuilds `hook-guard` from the dirty tree)
→ revert → `git status --porcelain` asserted empty.

Method note, recorded for honesty: my first pass ran all nine rows inside one
`nix develop` shell, whose `PATH` already pointed at the `hook-guard` built
from the *clean* tree — every row reported SURVIVED. Those nine runs were
**void**, not survivors; re-run with `nix develop -c` per row (which copies the
dirty tracked tree into the store) every row goes red. The numbers below are
from the re-run.

**The plan's seven (nine rows — the depth off-by-one run in both directions):**

| row | mutation | result | failing tests |
|---|---|---|---|
| M-A | `json.load` moved back outside the guard (the whole RT5r parse block restored) | RED | 76, 77, 78 |
| M-B | the nesting pre-scan removed | RED | 76 |
| M-C | the read bound removed (`sys.stdin.buffer.read()`) | RED | 77 |
| **M-D** | **audit subject → `model_ids[0]`** (rt7's survivor) | **RED** | **73** |
| M-E | the non-object coercion restored for sub-agent tools (`if not isinstance(tool_input, dict)`) | RED | 79 |
| M-F1 | depth check off by one, `depth >= _DEPTH_BUDGET` | RED | 80 |
| M-F2 | depth check off by one, `depth > _DEPTH_BUDGET + 1` | RED | 80 |
| M-G | the wrapper back to string interpolation | RED | 83 |
| M-H | the pre-scan bound raised to `10**6` | RED | 76 |

**rt7's 19 re-applied on the RT5rb tree** (M-D above is rt7's row of the same
name, so 18 further rows):

| row | mutation | result | failing tests |
|---|---|---|---|
| R-A | iterative walk replaced by a recursive one | RED | 69, 71, 72, 80 |
| R-B | the rule-level `except BaseException` narrowed to `_ToolInputBudgetExceeded` | RED | 70, 75 |
| R-C | `_NODE_BUDGET = 10**9`, `_DEPTH_BUDGET = 10**6` | RED | 69, 71, 72, 80 |
| R-E | model-rule exception handler resolves to allow | RED | 70, 75 |
| R-F | budget-exceeded branch returns `None` | RED | 69, 71, 72, 80 |
| R-M1 | `_MODEL_TOOLS = ()` | RED (15) | 54, 57, 58, 59, 65, 66, 67, 69, 70, 71, 72, 73, 74, 79, 80 |
| R-M2 | `route = "claude"` rows no longer skipped | RED | 57, 65 |
| R-M3 | unreadable table → allow | RED | 58, 67, 74 |
| R-M4 | `_bash_model_verdict` call removed from `main` | RED | 60, 62, 63, 75 |
| R-M5 | `--model(=|\s+)` → `--model(\s+)` | RED | 62 |
| R-M6 | denial record not written to stderr | RED | 52, 53, 73, 74, 80 |
| R-M7 | wrapper sub-agent matcher renamed | RED | 81 |
| R-M8 | guard ignores `--routing-table` | RED (15) | 54, 55, 57, 59, 60, 61, 62, 63, 64, 65, 66, 70, 73, 75, 80 |
| R-M9 | `_MODEL_TOOLS = ("subagent",)` | RED | 59, 66, 71, 73, 74, 79, 80 |
| R-M10 | `OPENROUTER_MODEL=` regex renamed so it matches nothing | RED | 63 |
| R-N1 | quote group `(['\"]?)` → `()` (both patterns) | RED | 62, 63 |
| R-N2 | backslash-newline continuation strip removed | RED | 62 |
| R-N3 | nested walk reduced to a flat `tool_input["model"]` read | RED | 66, 69, 71, 72, 73, 80 |

**27 rows applied, 27 killed, 0 survivors.** rt7's table was 18/19 with M-D
surviving; the whole table now dies.

## Findings

No MAJORs.

### MINOR-1 — the parse-nesting bound 10,000 is named only at its own constant; neither the module header nor the runbook prints the number

`pkgs/dsh-openrouter/hook-guard.py:135`, `:53-54`, `docs/runbooks/lanes.md:265`

```python
135 _MAX_PARSE_NESTING = 10_000
```

The reason *is* documented, at `hook-guard.py:127-134`. But the module
docstring's parse contract says only

```
54  the bound, nesting past the parse guard, or any parse failure
```

and the runbook says only

```
265   *cannot be parsed* — larger than 4 MiB, nested past the guard's parse-depth
266   limit, malformed JSON, or whose top level is not a JSON object — is denied
```

Both name 4 MiB and the runbook names 64, but neither prints 10,000, so an
operator reading the runbook (or the header) cannot tell how deep a payload may
be before it is refused, nor that the bound sits an order of magnitude under
the decoder's own limit. The plan asked the runbook to state "the numbers".
Fix: add "10,000 levels of bracket nesting (far under the ~52,000 at which the
JSON decoder itself gives up)" to `lanes.md:265` and to the header paragraph.

### MINOR-2 — the header's error-contract bullet still describes one `BaseException` region

`pkgs/dsh-openrouter/hook-guard.py:34-36`

```
34  * ``main()`` returns 0 on every path -- deny is expressed only through the
35    JSON on stdout, never through the exit code, and a top-level
36    ``try/except BaseException`` around the rule evaluation guarantees it.
```

RT5rb split the guarantee across **two** regions — the parse region at `:530`
and the rule region at `:564` — and it is the parse one that closes rt7
MAJOR-1. The bullet is RT5r's text left in place; the "Parse contract"
paragraph below (`:45-58`) supplies the missing half, so the file is not
misleading end to end, but read alone the bullet understates what guarantees
the promise. Fix: say "two `try/except BaseException` regions — one around the
payload read and parse, one around the rule evaluation".

### MINOR-3 — process: the seat ended without the machine-readable FACTORY-RESULT block

The driver recorded `status=failed` for a run whose commit is correct and whose
every claim verifies. Nothing in the tree is wrong; the board's status for rt8
is. Recorded here as the process deviation the gate was asked to note.

### MINOR-4 — the "walk-order helper" test (74) leans on the unreadable-table branch, which is a second implementation detail

`tests/unit/70-dsh-openrouter.bats:1022-1031`

Test 74 proves the walk yields the row first by asserting that the *unreadable
table* deny names the row as `subject` — i.e. it reads `model_ids[0]` through
`_model_verdict`'s `models is None` branch (`hook-guard.py:373`). That works
today (I confirmed the order independently by instrumenting `_walk_model_ids`,
and R-M3 kills the branch), but it couples the walk-order proof to a rule the
plan never tied to it: a future change that made an unreadable table report a
different subject would silently un-prove the walk order, leaving test 73's
discrimination resting on nothing. Fix (optional): assert the order directly,
e.g. a payload whose only ids are two non-rows and whose deny must name the
first-walked one.

## Verdict

**APPROVED.** Contract items 1–5 are all met and all are pinned: `main()`
returns 0 on every path I could reach (179 fuzz payloads, the rt7 crash
payloads, 5 MiB, non-UTF-8, empty, arrays — zero non-zero exits); the
audit-subject test discriminates and rt7's surviving mutant M-D now dies; a
non-object `tool_input` on a sub-agent tool denies while bash keeps its pinned
coercion; the depth budget is exactly 64 in behaviour, header and runbook; the
wrapper JSON-escapes the routing-table path through `jq @sh` and a path with a
quote, a space, an apostrophe and a `$` round-trips end to end. Six tests are
red on RT5r and green here with no pre-existing test disturbed; 27 mutation
rows all die; unit, host-core, lint, ruff and shellcheck are green; one commit,
byte-identical subject, both trailers, every touched file inside `touches`.

The deviation from the plan's literal "nesting > 64" is accepted: the plan's
two items were mutually unsatisfiable as written, the chosen bound is small,
bounded, documented with its reason at the definition, exact at both edges
(10000 parses, 10001 refuses), and — the point that matters — the exit-0
contract does not depend on it, because a `RecursionError` from `json.loads`
inside the bound is caught and denied at exit 0 (demonstrated at 1024, 512 and
256 KiB stacks).

The four MINORs are documentation and process only; MINOR-1 (print 10,000 in
the runbook and header) and MINOR-2 (the header's stale one-region sentence)
are worth folding into the next docs task on this file.
