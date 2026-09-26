# Opus gate — seat run rt7, task RT5r — REJECTED

## Summary

Branch `task/RT5r` @ `3e77a8440d1efef392271297d70925a8a2f1472e`, base
`19c408a3f981bf7b4abcd04fcf6972865b7aa641`, one commit, subject byte-identical
to the plan, both trailers present, every touched file inside the plan's
`touches`. Reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-rt7-RT5r`.

RT5b's carried work is intact and correct: the nested walk, every bash
spelling, the claude-row exclusion, the fail-closed unreadable table. The two
equivalent mutants the RT5b gate flagged (N4 `(?:env\s+)?`, N5 the
`.replace("\t", " ")` pass) are **gone from the source** as the plan required
(`hook-guard.py:138`, `hook-guard.py:310` vs `rt5b:107-108`, `rt5b:247`), and
the two behaviours they covered are still pinned by tests 63 and 62. All three
acceptance checks are green, `ruff` and `shellcheck` are clean, the six new
tests are red on the RT5b guard and green on RT5r with no pre-existing test
disturbed, and the whole required matrix except one row behaves as the contract
says.

It is rejected on two MAJORs.

**MAJOR-1 is the RT5b MAJOR-1 bypass, relocated one line earlier and still
open.** The `try/except BaseException` starts at `hook-guard.py:457`, *after*
`payload = json.load(sys.stdin)` at `hook-guard.py:439`. A hostile `tool_input`
of ~52,000 nesting levels (~312 KB of JSON — a trivially sendable tool call)
makes the JSON decoder itself raise `RecursionError`; the process exits 1 with
an empty stdout, which the pinned harness reads as a non-blocking error and
runs the tool. Contract item 1 — "main() returns 0 on EVERY path" — is not met,
and the file's own header asserts it (`hook-guard.py:34`). RT5r moved the
crashing depth from 995 to ~52,031; it did not close the hole.

**MAJOR-2**: mutation M-D (audit subject = first id found instead of the
offending one) **survives** the full suite. Contract item 4 is implemented but
not pinned: `_walk_model_ids` is a LIFO stack walk, so in the only test payload
that carries two ids (`steps: [row, non-row]`, test 73) the offending id is
already the *first* one the walk yields — the test cannot tell the two apart.

## Rule behaviour

Every row driven by feeding the built `hook-guard` compact JSON
(`ensure_ascii=False`) on stdin, exactly as the bridge sends it, with
`--routing-table docs/ledger/routing.toml`. OpenRouter rows in that table are
`deepseek/deepseek-v4-flash` and `deepseek/deepseek-v4-pro-0813`; `z-ai/glm-5.3`,
`moonshotai/kimi-k3`, `opus` are non-rows.

| # | case | expected | observed | exit |
|---|------|----------|----------|------|
| 1 | depth-2000 subagent, top-level `model: z-ai/glm-5.3` | deny, exit 0 | deny `tool_input too deep/large to inspect` | 0 |
| 2 | non-UTF-8 table (`\xff\xfe\x00not-toml`) + explicit non-row model | deny "could not be evaluated", exit 0 | deny `model rule could not be evaluated: UnicodeDecodeError` | 0 |
| 2b | same table, bash `--model z-ai/glm-5.3` | deny, exit 0 | deny `… could not be evaluated: UnicodeDecodeError`, subject = the command | 0 |
| 2c | same table via `FACTORY_ROUTING_TABLE` env (wrapper also passes `--routing-table`) | deny, exit 0 | deny `… could not be evaluated: UnicodeDecodeError` | 0 |
| 3 | model at depth 69 (workflow) | deny (budget), exit 0 | deny `tool_input too deep/large to inspect` | 0 |
| 3b | model at depth 63, deepest level | deny by the MODEL rule | deny `sub-agent model z-ai/glm-5.3 is not a row of …`, subject `z-ai/glm-5.3` | 0 |
| 3c | model at depth 64 | (probe) | deny — but by the BUDGET rule, not the model rule (see MINOR-3) | 0 |
| 4 | 20,000-key flat `tool_input` | deny (budget), exit 0 | deny `tool_input too deep/large to inspect` | 0 |
| 4b | 9,000-key flat `tool_input`, no model | allow (budget must not fire) | allow (empty stdout) | 0 |
| 4c | 9,000 keys + non-row model | deny by the model rule | deny `… z-ai/glm-5.3 is not a row of …`, subject `z-ai/glm-5.3` | 0 |
| 5 | subagent, `deepseek/deepseek-v4-flash` (a row) | allow | allow (empty stdout) | 0 |
| 5b | `workflow`, `z-ai/glm-5.3` | deny | deny, subject `z-ai/glm-5.3` | 0 |
| 5c | `subagent_fork`, `moonshotai/kimi-k3` | deny | deny, subject `moonshotai/kimi-k3` | 0 |
| 6 | `steps:[row, non-row]` — subject names the offending id | subject `z-ai/glm-5.3` | subject `z-ai/glm-5.3` (but see MAJOR-2: LIFO makes this the first-found id too) | 0 |
| 6b | `steps:[non-row, row]` | subject `z-ai/glm-5.3` | subject `z-ai/glm-5.3` | 0 |
| 6c | top-level row + nested non-row (`{"model":"deepseek/deepseek-v4-flash","steps":[{"model":"z-ai/glm-5.3"}]}`) | subject `z-ai/glm-5.3` | subject `z-ai/glm-5.3` — correct, **untested** (this is the payload M-D breaks) | 0 |
| 7a | `--model z-ai/glm-5.3` | deny | deny | 0 |
| 7b | `--model=z-ai/glm-5.3` | deny | deny | 0 |
| 7c | `--model "z-ai/glm-5.3"` | deny | deny | 0 |
| 7d | `--model 'z-ai/glm-5.3'` | deny | deny | 0 |
| 7e | `--model="z-ai/glm-5.3"` | deny | deny | 0 |
| 7f | `env OPENROUTER_MODEL=z-ai/glm-5.3 …` | deny | deny | 0 |
| 7g | `OPENROUTER_MODEL="z-ai/glm-5.3" …` | deny | deny | 0 |
| 7h | `--model<TAB>z-ai/glm-5.3` | deny | deny | 0 |
| 7i | `--model \`+newline` continuation | deny | deny | 0 |
| 7j | `bash -c 'dsh-openrouter --model z-ai/glm-5.3 …'` | deny | deny | 0 |
| 9a | stdin is not JSON | exit 0 | allow (matches the documented allow-on-error asymmetry) | 0 |
| 9b | empty stdin | exit 0 | allow | 0 |
| 9c | `tool_input: null` | exit 0 | allow | 0 |
| 9d | `tool_input` is a JSON **array** carrying a non-row model | exit 0 | **allow** — MINOR-1: the model rule never runs | 0 |
| 9e | payload is a JSON array | exit 0 | allow | 0 |
| 9f | invalid UTF-8 bytes on stdin | exit 0 | allow (`UnicodeDecodeError` is a `ValueError`, caught at `:440`) | 0 |
| **X1** | **depth-52,031 subagent, top-level `model: z-ai/glm-5.3` (~312 KB)** | **deny, exit 0** | **ALLOW — MAJOR-1: exit 1, stdout 0 bytes, `RecursionError` traceback** | **1** |
| X2 | depth-51,875, same payload (the last good depth) | deny, exit 0 | deny `tool_input too deep/large to inspect` | 0 |
| X3 | depth-100,000 / depth-500,000 | deny, exit 0 | ALLOW — exit 1, stdout 0 bytes | 1 |

Matrix item 8: every one of the 35 `@test`s that runs `hook-guard`
(`tests/unit/70-dsh-openrouter.bats:657`–`:1021`) asserts `[ "$status" -eq 0 ]`.
There are exactly nine `run … hook-guard` invocations in the file — lines 633,
644, 652 (the `guard_denies` / `guard_denies_reason` / `guard_allows` helpers),
738, 764 (the two inline stderr-record tests), 804, 815, 827 (the
`guard_denies_table` / `…_subject` / `guard_allows_table` helpers) and 949 (the
empty-`FACTORY_ROUTING_TABLE` test) — and each is immediately followed by a
status-0 assertion at 634, 645, 653, 739, 765, 805, 816, 828 and 950. None is
missing.

## Checks

Run in the clone on a clean tree (`git status --porcelain` empty).

| command | exit | wall |
|---|---|---|
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 0 — **82/82 ok** | 23 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 | cached; forced `--rebuild`: 0, 182 tests ok |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | 0 | 13 s (cached closure) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 | cached |
| `nix develop -c ruff check pkgs/dsh-openrouter` | 0 — "All checks passed!" | <1 s |
| `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | 0 | <1 s |

No failures; no tail to paste. The implementer's claim (unit/host-core/lint
pass) is confirmed. Note that `pkgs/dsh-openrouter/default.nix` lints
`hook-guard.py` inside its own derivation, so a mutation that trips ruff fails
the *build* rather than a test — see the M-E note in the mutation table.

## Red before green

`pkgs/dsh-openrouter/hook-guard.py` replaced with
`git -C /home/dalhaka/factory/ws/rt5/RT5b show task/RT5b:pkgs/dsh-openrouter/hook-guard.py`
(411 lines; RT5r's tests and wrapper kept), then
`nix develop -c bats tests/unit/70-dsh-openrouter.bats`:

```
not ok 69 hook-guard fails closed (not crashed) on a 2000-deep tool_input: deny 'too deep/large', exit 0
not ok 70 hook-guard fails closed (not crashed) on a non-UTF-8 routing table: deny 'could not be evaluated', exit 0
not ok 71 hook-guard denies a model nested beyond the depth budget as too deep (not silently missed), exit 0
not ok 72 hook-guard denies a tool_input with more keys than the node budget as too large, exit 0
not ok 73 the audit subject names the OFFENDING model id, not the first id found
not ok 74 a bash --model nested-seat launch also fails closed on a non-UTF-8 routing table, exit 0
```

Exactly the six new tests, and **no pre-existing test went red** — tests 1–68
and 75–82 all stayed ok, so RT5r's guard is a strict superset of RT5b's
behaviour on everything RT5b already pinned. `git checkout --
pkgs/dsh-openrouter/hook-guard.py` restored the tree (`git status --porcelain`
empty) and the suite is 82/82 green again.

Caveat on test 73's redness: it goes red on RT5b for the *subject* assertion,
which is real, but MAJOR-2 shows the same test does not discriminate the RT5r
implementation from a first-id-found one.

## Mutation table

Each row: apply → `git diff --stat` asserted non-empty → `nix develop -c bats
tests/unit/70-dsh-openrouter.bats` → `git checkout --` → `git status
--porcelain` asserted empty. 19 rows applied, 18 red, **1 survivor**.

| row | mutation | result | failing tests |
|---|---|---|---|
| M-A | iterative walk replaced by a recursive one (explicit stack removed) | RED | 69, 71, 72 |
| M-B | top-level `except BaseException` narrowed to `except _ToolInputBudgetExceeded` (catch-all removed) | RED | 70, 74 |
| M-C | `_NODE_BUDGET = 10**9`, `_DEPTH_BUDGET = 10**6` | RED | 69, 71, 72 |
| **M-D** | **audit subject = `model_ids[0]` (first id found) instead of the offending `model`** | **SURVIVED** | — (82/82 ok) |
| M-E | model-rule exception handler resolves to allow (`_deny(...)` dropped from the `except`) | RED | 70, 74 |
| M-F | budget-exceeded branch returns `None` (allow) instead of the deny reason | RED | 69, 71, 72 |
| M1 | `_MODEL_TOOLS = ()` (branch removed) | RED (12) | 54, 57, 58, 59, 65, 66, 67, 69, … |
| M2 | `route = "claude"` rows no longer skipped | RED | 57, 65 |
| M3 | unreadable table → allow (`_model_verdict` returns `None`) | RED | 58, 67 |
| M4 | `_bash_model_verdict` call removed from `main` | RED | 60, 62, 63, 74 |
| M5 | `--model(=|\s+)` → `--model(\s+)` (equals form unmatched) | RED | 62 |
| M6 | denial record not written to stderr | RED | 52, 53, 73 |
| M7 | wrapper matcher `subagent\|subagent_fork\|workflow` renamed | RED | 75 |
| M8 | guard ignores `--routing-table` (argv loop removed) | RED (14) | 54, 55, 57, 59, 60, 61, 62, 63, … |
| M9 | `_MODEL_TOOLS = ("subagent",)` | RED | 59, 66, 71, 73 |
| M10 | `OPENROUTER_MODEL=` regex renamed so it matches nothing | RED | 63 |
| N1 | quote group `(['\"]?)` → `()` (empty-only) | RED | 62, 63 |
| N2 | backslash-newline continuation strip removed | RED | 62 |
| N3 | nested walk reduced to a flat `node["model"]` read | RED | 66, 69, 71, 72, 73 |

RT5b's 13 named mutants (M1–M10, N1–N3) are all still killed on the RT5r tree.

Void-row note, recorded for honesty: my first spelling of M-E deleted only the
`_deny(...)` call and left `except BaseException as exc:` intact, which makes
`exc` unused; `pkgs/dsh-openrouter/default.nix` lints the script inside its
derivation, so the *package build* failed with
`F841 local variable 'exc' is assigned to but never used` and `bats` never ran.
That row was void, not a survivor. Re-spelled as `except BaseException:` +
`return 0`, the package builds, the non-UTF-8 probe returns exit 0 with empty
stdout (allow), and tests 70 and 74 go red — M-E dies.

N4 and N5 (the RT5b gate's two equivalent mutants) are not rows here: the plan
required the fragments be deleted as dead code and they are —
`hook-guard.py:138` is `_OPENROUTER_MODEL_ENV = re.compile(r"OPENROUTER_MODEL=(['\"]?)([A-Za-z0-9._:/-]+)\1")`
with no `(?:env\s+)?`, and `hook-guard.py:310` is
`command = command.replace("\\\n", "")` with no `.replace("\t", " ")`. Tests 63
(`env OPENROUTER_MODEL=…`) and 62 (tab separator) still pass, so the removal
lost no coverage.

## Findings

### MAJOR-1 — `json.load` sits outside the fail-closed guard; a ~312 KB deeply nested `tool_input` still exits non-zero with empty stdout, which the harness ALLOWS

`pkgs/dsh-openrouter/hook-guard.py:437-441` and `:457`

```python
437 def main(argv):
438     try:
439         payload = json.load(sys.stdin)
440     except ValueError:
441         return 0
...
456     subject = ""
457     try:                       # <- the BaseException guard starts HERE
```

The `try/except BaseException` (`:480`) wraps only the rule evaluation, as the
plan's item 1 literally phrased it — but item 1's normative sentence is
"**main() returns 0 on EVERY path**", and the header repeats the promise at
`hook-guard.py:34` ("`main()` returns 0 on every path"). It does not.
`json.load` is fed attacker-controlled bytes and raises `RecursionError`, which
is not a `ValueError`, on a sufficiently nested document. Bisected in the
clone against the built `hook-guard`:

```
depth=51875 exit=0 stdout=deny "tool_input too deep/large to inspect"
depth=52031 exit=1 stdout_bytes=0     payload bytes: 312288
depth=100000 exit=1 stdout_bytes=0
depth=500000 exit=1 stdout_bytes=0
```

```
Traceback (most recent call last):
  File ".../bin/hook-guard", line 496, in <module>
    sys.exit(main(sys.argv[1:]))
  File ".../bin/hook-guard", line 440, in main
    payload = json.load(sys.stdin)
  ...
RecursionError: Stack overflow (used 8132 kB) while decoding a JSON object from a unicode string
```

The payload used is exactly the shape the RT5b gate named, only deeper:
`{"model":"z-ai/glm-5.3","deep":{"a":{"a": … }}}` inside a `subagent`
`tool_input`. Had it parsed, the guard would have denied. Instead the process
exits 1 having written nothing to stdout, and by the protocol this round was
written to fix — `@deepseek-ai/dsh-hook-protocol`: "exit 2 blocks … every other
exit is a non-blocking error"; `dsh-hooks-claude-code` blocks only on
`merged.decision === "deny"|"ask"` (quoted in
`docs/reviews/2026-09-05-opus-review-rt5-RT5b.md:20-25`) — the tool runs. This
is RT5b's MAJOR-1 with the crash site moved from `_walk_model_ids` to
`json.load` and the threshold moved from 995 to ~52,031; 312 KB is an ordinary
tool-call size, and the model composing the `subagent` call controls it
entirely.

**Fix.** Read stdin and parse it *inside* the fail-closed region: hoist the
`try:` above `payload = json.load(sys.stdin)` (keeping the `except ValueError:
return 0` allow-on-error arm for genuinely malformed input) so that any other
exception lands in the `except BaseException` handler; a JSON document too deep
for the decoder is the same hostile shape the walk's depth budget already
denies, so the right resolution is a deny, not an allow — reason
`tool_input too deep/large to inspect` or
`model rule could not be evaluated: RecursionError`, with `tool` unknown. Add a
red-first test at a depth past the decoder's limit (the RT5r tests stop at
2000, three orders of magnitude short) asserting deny **and** `status -eq 0`.

### MAJOR-2 — contract item 4 is unpinned: mutating the audit subject to the first id found leaves the whole suite green

`pkgs/dsh-openrouter/hook-guard.py:292-294`, `tests/unit/70-dsh-openrouter.bats:1009-1014`

```python
292     for model in model_ids:
293         if model not in models:
294             return _model_deny_reason(model, table_path), model
```

Mutating `:294` to `return _model_deny_reason(model, table_path), model_ids[0]`
— literally "the first id found" — builds clean and passes **82/82**, test 73
included:

```
ok 73 the audit subject names the OFFENDING model id, not the first id found
```

The cause is `_walk_model_ids` (`:251-265`): it is a LIFO stack
(`current, depth = stack.pop()`), so a list is visited back-to-front. Test 73's
payload is
`{"steps":[{"model":"deepseek/deepseek-v4-flash",…},{"model":"z-ai/glm-5.3",…}]}`,
whose walk order is `["z-ai/glm-5.3", "deepseek/deepseek-v4-flash"]` — the
offending id is *already* `model_ids[0]`, so the assertion cannot distinguish
the two implementations. The plan's Step 1 names this mutation explicitly
("Audit subject names the offending id (mutation: first id → fails)") and it
does not fail.

A payload that does discriminate — a row at the top level, the non-row nested
under it — run against both trees:

```
payload: {"model":"deepseek/deepseek-v4-flash","steps":[{"model":"z-ai/glm-5.3"}]}
M-D applied : {"…","reason":"sub-agent model z-ai/glm-5.3 is not a row of …","subject":"deepseek/deepseek-v4-flash"}
RT5r (clean): {"…","reason":"sub-agent model z-ai/glm-5.3 is not a row of …","subject":"z-ai/glm-5.3"}
```

So the implementation is right and the audit trail is right; only the test is
vacuous. That still fails the round: contract item 4 is what the transcript's
`subject` — the thing `dsh-openrouter --denials` shows an operator — rests on,
and nothing in the suite holds it.

**Fix.** Add the payload above to test 73 (a top-level `model` that IS a row
plus a nested `model` that is not), asserting `subject == "z-ai/glm-5.3"`. It
is one more `guard_denies_table_subject` line, and it kills M-D.

### MINOR-1 — a non-dict `tool_input` on a sub-agent tool is silently allowed, against the fail-closed asymmetry

`pkgs/dsh-openrouter/hook-guard.py:447-449`

```python
447     tool_input = payload.get("tool_input")
448     if not isinstance(tool_input, dict):
449         tool_input = {}
```

`{"hook_event_name":"PreToolUse","tool_name":"subagent","tool_input":[{"model":"z-ai/glm-5.3"}]}`
→ allow, exit 0 (matrix row 9d). The walk handles lists everywhere else, so the
only reason a list `tool_input` escapes is this coercion. Carried from before
RT5r, but RT5r is the commit that declares the model rule fails closed on an
unexpected shape; a `_MODEL_TOOLS` call whose `tool_input` is not an object is
exactly such a shape. Fix: pass the raw `tool_input` to `_model_verdict` (it
already walks lists), or deny when `tool` is in `_MODEL_TOOLS` and `tool_input`
is neither dict nor list.

### MINOR-2 — a model found at depth 64 is reported as a budget overrun, not by the model rule; the effective depth budget is 63

`pkgs/dsh-openrouter/hook-guard.py:256`, `:284`

`_walk_model_ids` yields the id at depth 64, then pushes its *string value* at
depth 65, which trips `depth > _DEPTH_BUDGET`; because `_model_verdict` drains
the generator with `list(...)` (`:284`), the exception discards the id already
yielded. Observed (matrix 3b/3c): a model at depth 63 denies with
`sub-agent model z-ai/glm-5.3 is not a row of …` and `subject: "z-ai/glm-5.3"`,
while the same model one level deeper denies with
`tool_input too deep/large to inspect` and `subject: ""`. Both are denies, so
the direction is safe — but the header and the plan both say the depth budget
is 64, and the deepest level a model is actually *named* from is 63. Either
document it or stop pushing scalars onto the stack.

### MINOR-3 — the wrapper interpolates the routing-table path into `hooks.json` unquoted-for-JSON

`pkgs/dsh-openrouter/dsh-openrouter.sh:536`, `:547`, `:553`, `:559`

```sh
routing_table=${FACTORY_ROUTING_TABLE:-$HOME/nixos-agent-env/docs/ledger/routing.toml}
...
{ "type": "command", "command": "exec '$hook_guard' --routing-table '$routing_table'" }
```

A path containing `'` or `"` produces a broken command string or invalid JSON.
The value is operator-set, and `$hook_guard` was already interpolated the same
way before this commit, so this is cosmetic — but the new variable doubles the
exposure. Consider a `printf '%s'`-through-`jq`-style escape, or refuse a path
containing a quote at the point it is resolved.

## Verdict

**REJECTED.** Two MAJORs: contract item 1 is not met — the guard still exits
non-zero with empty stdout on an attacker-shaped `tool_input`, which the
harness reads as ALLOW, so the exact bypass this round was re-planned to close
remains open at a slightly larger payload (MAJOR-1); and contract item 4 is not
pinned by any test — the "first id found" mutation the plan says must die
survives the full suite (MAJOR-2).

Everything else is in order and should be kept as-is on the next round: the
iterative bounded walk, the fail-closed model rule, the exit-0 contract for
every path the `try` does cover, the six new tests, the removal of the two
equivalent fragments, the runbook's statement of the heuristic's limits, the
header's statement of the asymmetry, the commit shape, and all three checks.
The re-plan is small: hoist the stdin parse inside the `BaseException` region
with a test at a decoder-breaking depth, and add one discriminating payload to
test 73.
