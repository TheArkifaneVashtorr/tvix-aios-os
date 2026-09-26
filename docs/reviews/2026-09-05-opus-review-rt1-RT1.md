# Opus gate — seat run rt1, task RT1 — REJECTED

Gate: Opus, adversarial, evidence-only. Reviewed in a throwaway clone of
`/home/dalhaka/factory/ws/rt1/RT1` at `4ef92e2` on base `55c3629`. The
implementer workspace was never touched; nothing was written outside the clone,
the nix cache dir and this file.

## Summary

The feature is real and works. `factory_route` / `factory_route_check` /
`factory_task_kind_size` are pure bash, shellcheck-clean, and produce exactly
the right answers on the committed table; `factory-task` records `effort:` and
`route:`; red-before-green is genuine (five tests fail on the base library).
Every acceptance check passes.

It is rejected on evidence, not on prose: **five of twelve mutations survive**,
including two of the eight this gate is required to try. The whole point of the
routing table is that the operator can still override it — and *neither
override path is tested*. `--model` no longer beating the route, and
`OPENROUTER_REASONING_EFFORT` no longer beating the route's effort, both pass
the full suite silently. `factory-review`, which the task's Interfaces section
requires to resolve with role `review` and launch its seat with the effort, has
**no test at all**: pointing it at role `implement`, or dropping the effort from
its launch environment, is invisible to the suite.

These are not hypothetical. Direct probes (Real data, below) show HEAD behaving
correctly and the mutants behaving wrongly, with `bats` green in both cases.
The fix is small — three assertions and one `factory-review` test — and the
implementation itself needs no change for the two majors.

## Checks

All run from the clone, `XDG_CACHE_HOME` pinned under the scratchpad, tooling
via `nix develop -c`.

| Check | Result |
| --- | --- |
| `git show --stat HEAD` | exactly the six files the task names (`docs/ledger/routing.toml`, `tests/unit/80-seat-driver.bats`, `tools/factory/seat/{README.md,factory-lib.sh,factory-review,factory-task}`); one commit on `55c3629` |
| commit subject | byte-identical to the plan's `commit subject:` line (`diff` clean) |
| trailer | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present; extra `Generated-By: dsh …` line, allowed |
| `routing.toml` vs the plan's block | content identical, **but 1130 bytes vs 1131 — the file has no trailing newline** (see Deviations) |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass; new tests visible in the log as 123–127 — **125 reported `# skip`** (see Deviations) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | pass (treefmt 83 files 0 changed, statix/deadnix/ruff clean, render.test.mjs ok) |
| `nix develop -c shellcheck` on the three seat scripts | clean, exit 0 |
| `nix develop -c bats tests/unit/80-seat-driver.bats` | 15/15 pass locally (13 runs here, does not skip) |
| pure bash in the lookup | confirmed — no `awk`/`sed`/`grep`/`python`/`perl`/`jq`/`cut`/`tr` on any added line of the three scripts |
| hard rules | no `sudo`, `systemctl`, `nixos-rebuild`, `--no-verify`, `git push` anywhere in the diff; working tree clean after review; transcript shows exactly one `dsh-openrouter` session, the harness's own |
| `2>/dev/null` | two new occurrences, both on `factory_route` (not on a gated command) — allowed, but see Findings |

## Red before green

Base (`55c3629`) `factory-lib.sh`, `factory-task` and `factory-review` restored
over HEAD's tests, then `nix develop -c bats tests/unit/80-seat-driver.bats`:

```
not ok 11 factory_route picks the most specific matching row, first row on ties
not ok 12 factory_route rejects a malformed or missing table
not ok 13 factory_route_check validates the committed routing table
not ok 14 factory_task_kind_size parses (kind, size) from the heading, any any otherwise
not ok 15 factory-task resolves model and effort through routing.toml and records the route
```

Tests 11–14 fail with exit 127 (`factory_route: command not found`,
`factory_task_kind_size: command not found` — bats `BW01` warnings name them
explicitly). Test 15 fails on
`[[ "$output" == *"model=deepseek/deepseek-v4-flash"* ]]`: the base driver hands
the seat the built-in Pro default, exactly as the plan's step 2 predicted. Red
is genuine. Scripts restored with `git checkout -- tools/factory/seat/`; the
suite returns 15/15 green.

## Mutation table

Twelve mutations, each applied to the working tree, `bats
tests/unit/80-seat-driver.bats` run, then reverted. Seven killed, five
survived.

| # | Mutation | Result | Killed by |
| --- | --- | --- | --- |
| M1 | specificity ties go to the **last** row (`-gt` → `-ge`) | KILLED | 11 `factory_route picks the most specific matching row, first row on ties` |
| M2 | `any` treated as a literal for `kind` (drop the `any` alternate in the match) | KILLED | 11 |
| M3 | the no-default-row check disabled (`have_default -eq 1` → `-ge 0`) | KILLED | 12 `factory_route rejects a malformed or missing table` |
| M4 | effort value validation dropped (`off\|low\|medium\|high\|xhigh` → accept anything) | KILLED | 12 |
| M5 | **`--model` no longer beats the route** | **SURVIVED** | — |
| M6 | **`OPENROUTER_REASONING_EFFORT` no longer beats the route's effort** | **SURVIVED** | — |
| M7 | the seat launched without `OPENROUTER_REASONING_EFFORT` in its env (`factory-task`) | KILLED | 15 `factory-task resolves model and effort through routing.toml and records the route` |
| M8 | `route:` line says `explicit` for a routed pick | KILLED | 15 |
| M9 | `effort:` line dropped from the `.result` | KILLED | 15 |
| M10 | unknown-`kind`-word validation dropped | **SURVIVED** | — |
| M11 | **`factory-review` looks up role `implement` instead of `review`** | **SURVIVED** | — |
| M12 | **`factory-review`'s seat launched without the effort in its env** | **SURVIVED** | — |

Why M5 and M6 survive is mechanical, not accidental: no test in the file ever
passes `--model` (`grep -n -- '--model' tests/unit/80-seat-driver.bats` matches
only a comment), and all three resolution cases set
`OPENROUTER_REASONING_EFFORT=` **empty**, which `${…:-…}` treats as unset. The
env-effort override is therefore never exercised with a value.

Why M11/M12 survive: `factory-review` appears in no test in the file.

## Real data

From the clone, read-only, no seat launched:

```
$ . tools/factory/seat/factory-lib.sh
$ factory_route implement docs XS docs/ledger/routing.toml
deepseek/deepseek-v4-flash off
$ factory_route implement code M docs/ledger/routing.toml
deepseek/deepseek-v4-pro-0813 medium
$ factory_route review code S docs/ledger/routing.toml
deepseek/deepseek-v4-pro-0813 medium
$ factory_route_check docs/ledger/routing.toml; echo rc=$?
rc=0
$ factory_task_kind_size docs/superpowers/plans/2026-09-05-session-context.md G7
docs S
```

All five expected values, exactly.

End-to-end probe of the two uncovered precedence rules, with a fake
`dsh-openrouter` recording what the seat actually receives (a `(docs, XS)`
plan heading, the committed table):

```
== HEAD ==
  --model z/z, no env      -> seat saw: model=z/z effort=[off]
                              result: model: z/z effort: off route: explicit
  OPENROUTER_REASONING_EFFORT=high
                           -> seat saw: model=…-flash effort=[high]
                              result: effort: high route: implement/docs/XS
== MUTANT M5 ==
  --model z/z, no env      -> seat saw: model=…-flash   (the flag was discarded)
                              result: route: implement/docs/XS
== MUTANT M6 ==
  OPENROUTER_REASONING_EFFORT=high
                           -> seat saw: effort=[off]    (the env var was ignored)
```

HEAD is correct on both. Both mutants are plainly wrong on the wire. `bats` is
green in all three states.

Edge probes on `factory_route` (evidence for the minors below):

```
model = ""            -> rc=0, prints " off"   (empty model accepted)
[meta] table present  -> rc=3 "malformed line \[meta\]"
duplicate effort key  -> rc=0, last value silently wins
```

## Findings

**MAJOR 1 — the `--model` override is unproven.**
`tools/factory/seat/factory-task:85-87` (`if [ -n "$model" ]; then explicit=1`).
The task's Interfaces section requires `--model` > `OPENROUTER_MODEL` > route.
Mutation M5 makes the route clobber an explicit `--model` and the entire suite
stays green; the probe above shows the seat then receiving the wrong model with
`route: implement/docs/XS` in the `.result`, i.e. a silent, unlogged override of
the operator's explicit choice. Fix: one more case in the resolution test
passing `--model z/z` and asserting the fake sees `z/z` and the `.result` says
`route: explicit`.

**MAJOR 2 — the `OPENROUTER_REASONING_EFFORT` override is unproven.**
`tools/factory/seat/factory-task:83` and `factory-review:72`
(`effort=${OPENROUTER_REASONING_EFFORT:-$route_effort}`). Required by the same
Interfaces section. All three resolution cases pass the variable **empty**,
which cannot distinguish `${…:-…}` from a bare `effort=$route_effort`; M6
proves it. Fix: one case with `OPENROUTER_REASONING_EFFORT=high` asserting the
fake sees `effort=high` while the model still comes from the route.

**MAJOR 3 — `factory-review` has no test.**
`tools/factory/seat/factory-review:63-82,162`. The task requires it to resolve
with role `review`, the heading's kind/size, the same precedence, and to launch
its seat with `OPENROUTER_REASONING_EFFORT=$effort`. M11 (role `implement`
instead of `review`) and M12 (effort dropped from the launch env) both survive,
so none of that is pinned. Today the two roles happen to route to the same
model, which is exactly what makes the regression invisible when the table
changes — which is RT2's whole job. Fix: one test mirroring the `factory-task`
one against `factory-review` (fake `factory-ws`, fake `dsh-openrouter`, a
fixture table where `review` and `implement` differ).

**MINOR 1 — unknown role/kind/size words are validated but unproven.** M10
(dropping the unknown-`kind` check) survives. The plan's Interfaces list this as
an exit-3 condition; the plan's step-1 test list does not, so this is a gap
rather than a broken promise — but the enumeration is precisely what RT2 must
extend, and nothing will catch a botched extension.

**MINOR 2 — an empty value passes validation.** `factory-lib.sh:216-224` (the `for word in …` loop): the
`*[!A-Za-z0-9._:/-]*` test cannot match the empty string, so `model = ""` yields
rc=0 and the output `" off"`. The spec says values must match
`[A-Za-z0-9._:/-]+` (non-empty). It degrades safely — `route_model` comes out
empty and `factory-task` falls back to the built-in default with a logged
warning — but the exit-3 contract is not what it claims.

**MINOR 3 — the parser rejects otherwise-valid TOML.** `factory-lib.sh:307-312`:
any table header other than `[[route]]` (e.g. a `[meta]` block) is a "malformed
line" and exits 3, and duplicate keys inside a row silently take the last value
without complaint. Neither is wrong for today's file; both are worth knowing
before RT2 grows the schema.

**MINOR 4 — `2>/dev/null` hides why the table was rejected.**
`factory-task:80` / `factory-review:69`:
`route_line=$(factory_route … 2>/dev/null || true)`. This is not a gated
command so it breaks no hard rule, but it discards the one message that says
*which row* is bad (`row 3: bad effort "max"`), leaving only the generic
`warning: routing table unusable`. Consider `2>&1 | …` into the log, or
re-running `factory_route_check` on the failure path to log its message.

**MINOR 5 — the misleading comment on the skipped test.**
`tests/unit/80-seat-driver.bats:363-367` (the comment above the `skip` at :369) says the real table is "reachable …
from the lint check, which copies the whole tree". The `lint` check does not run
bats, so it does not exercise this test at all. The only place the committed
table is validated is the local `nix develop -c bats` run.

Nothing else: no `sudo`/`systemctl`/`nixos-rebuild`, no `--no-verify`, no write
outside the workspace, no seat launched during the run (the transcript's only
`dsh-openrouter` line is the harness's own banner), and the lookup is pure bash
as required.

## Deviations

1. **`docs/ledger/routing.toml` is not byte-identical to the plan's block** — it
   is missing the final newline (1130 bytes vs 1131; content otherwise
   identical, `diff` shows only `\ No newline at end of file`). Functionally
   harmless (`mapfile -t` reads the final partial line), and treefmt has no TOML
   formatter to catch it, but the task said "verbatim".
2. **The committed-table pin does not hold under the `unit` check.** The plan's
   step 1 says the `factory_route_check` test on the real
   `docs/ledger/routing.toml` "pins the committed table's shape under the `unit`
   check". It does not: `flake.nix:1731-1751` (the `unit-tests` derivation; the seat copy is at :1745) copies only `tests/`,
   `pkgs/helm/` and `tools/factory/seat/` into the sandbox, so the test reports
   `ok 125 … # skip docs/ledger/routing.toml not copied into the unit-check
   sandbox`. This one is *defensible* — extending the sandbox needs
   `flake.nix`, which the plan's Global Constraints put off-limits for this
   afternoon — and the implementer documented it in the test and in the
   `.result` notes. Recording it so the orchestrator can decide where the pin
   lands (RT2 already touches the factory test files, and adding
   `cp -r ${self}/docs/ledger docs/ledger` to the `unit` derivation is a
   one-line change once `flake.nix` is free).
3. `factory-review` writes no `.result` file, so it gains no `effort:`/`route:`
   lines. That matches the script as it stands and is not a deviation from the
   task, which scopes those two lines to `factory-task`. Noted only because the
   Interfaces line reads "same".
