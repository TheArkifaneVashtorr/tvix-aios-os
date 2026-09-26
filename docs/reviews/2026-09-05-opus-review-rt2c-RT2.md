# Opus gate — seat run rt2c, task RT2 — REJECTED

## Summary

The implementation is correct and the table is exactly what the plan
specifies. Rejection is on **evidence**, not on behaviour: two mutations
survive, one of them the cross-check mutant this gate was asked to kill, and
the commit message states a check property that this gate disproved.

- One commit on `49bffe7`, exactly the seven planned touches, subject
  byte-identical, `Co-Authored-By` present (plus a `Generated-By` line).
- `docs/ledger/routing.toml`: all 14 rows carry `route`; the eight new claude
  rows are byte-identical to the plan block; the claude default row is present
  and exact; RT1's five rows are unchanged apart from `route = "openrouter"`;
  the file ends with one newline.
- All five acceptance commands green; real-data lookups exact; nine
  `factory_route` / `route.py lookup` tuples identical; `route.py models`
  equals `dark-factory.js`'s built-in literal; stdlib only; no seat launched.
- **Blocker 1.** Flipping `route.py`'s tie-break (`spec > best_spec` →
  `spec >= best_spec`) survives every test. The divergence is real — on a
  three-row fixture with an observable tie, bash prints `m/first low` and
  python prints `m/second low` — but the cross-check runs only on the
  committed table, whose one genuine tie (`openrouter implement/docs/any` vs
  `implement/any/XS`) has the *same* model and effort in both rows, so no
  tuple can see it. The plan asked for the two implementations to be
  "cross-checked by a test that runs both on the same fixture"; a fixture that
  discriminates tie order is missing.
- **Blocker 2.** `route.py`'s missing-key validation is never exercised: the
  bad-table fixture only carries `route = "other"`. Replacing the whole
  `for key in (...)` block with `setdefault` calls leaves the suite green.
- **Blocker 3.** The commit body says "checks.factory-unit refuses any drift
  between the table and that map." It does not. A table-only drift (claude
  `review/code` `opus` → `sonnet`, scripts untouched) leaves
  `nix build .#checks.x86_64-linux.factory-unit` **green** — the sandbox
  copies neither `route.py` nor `docs/ledger/routing.toml`, so the assertion
  silently falls back to the `pinned` literal inside the test file. The drift
  is refused by `githooks/pre-commit` (which runs `render.test.mjs` on the
  full tree), not by `factory-unit`. `FACTORY-NOTES` in the `.result` says
  this correctly; the commit message contradicts it.

## Checks

Throwaway clone of `/home/dalhaka/factory/ws/rt2c/RT2` at `task/RT2`
(`5f27d25a7851`), `XDG_CACHE_HOME` under the session scratchpad, tooling via
`nix develop -c`.

| command | result |
| --- | --- |
| `git show --stat HEAD` | 7 files, exactly the plan's `touches` |
| subject byte-diff vs the plan | identical (`diff` empty) |
| parents / commits on base | one commit, parent `49bffe746972` |
| trailers | `Generated-By: dsh 0.1.2-rc.1 / …` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass |
| `nix build .#checks.x86_64-linux.factory-unit -L --no-link` | pass |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | pass (`render.test.mjs: all assertions passed`) |
| `nix develop -c shellcheck tools/factory/seat/factory-lib.sh` | clean |
| `nix develop -c ruff check tools/factory/route.py` | `All checks passed!` |
| `nix develop -c ruff format --check tools/factory/route.py` | already formatted |
| `nix develop -c bats tests/unit/80-seat-driver.bats` | 19/19 ok |
| stdlib scan | `import json`, `import sys` only |
| seat launched? | no; transcript's only `dsh-openrouter` hit is the implementer reading the lint gate's ruff argument list |

**Table.** A byte-comparison script against the plan's two TOML blocks
reported `CLAUDE-ROWS: MATCH` (the eight rows plus the claude default row,
in the plan's order) and `RT1-ROWS: UNCHANGED except route="openrouter"
prepended` (5/5). `rows total=14, rows with route key=14`; the file ends
`effort = "medium"\n` (single trailing newline).

**Interfaces.** `factory_route [--route R] ROLE KIND SIZE [FILE]` defaults to
`openrouter`; `_factory_route_finish_row` defaults a row without `route` to
`openrouter`; `route ∈ {openrouter, claude}` is enumerated and rejected
otherwise; the role words are widened to
`implement|review|verify|baseline|research|audit|orchestrate|any`.
`route.py check|lookup|models` all present, `--file` honoured.
README documents the orchestrator rule ("on every `claude/review/<kind>` gate
the dark factory uses that row's model. The `models` argument handed to the
Workflow is `route.py models` output").

**Coverage gap found while reading the checks (evidence, not prose).** Of the
three acceptance checks, neither `unit` nor `factory-unit` reads `route.py` or
the committed table. Proof from the `unit` check's own log
(`nix build … .unit --rebuild`):

```
unit-tests> ok 125 factory_route_check validates the committed routing table # skip docs/ledger/routing.toml not copied into the unit-check sandbox
unit-tests> ok 130 route.py validates the committed table and cross-checks factory_route's lookup, when route.py is present # skip tools/factory/route.py not copied into the unit-check sandbox
```

and `flake.nix`'s `factory-unit` copies only `dark-factory.js`, `fixtures/`
and `render.test.mjs`. The only gated command that runs `route.py` against the
real table is `githooks/pre-commit`, and only for `models` — never `lookup`,
never `check`, never the bash/python cross-check. This is a consequence of the
plan's "do not touch `flake.nix`" constraint (RT1b's gate had already noted
"RT2 moves that check into the flake"), so it is a deviation to hand back to
the orchestrator, not a fault of the implementation — but it is why blockers 1
and 2 matter: those tests run nowhere but a local `bats` invocation.

## Red before green

| experiment | result |
| --- | --- |
| base `factory-lib.sh` (HEAD~1) + HEAD's bats | **red**: 4 failures — 13 `factory_route_check validates the committed routing table`, 16 `--route claude …`, 17 `no claude default row`, 18 `route.py … cross-checks`. Message confirms the flag is unknown at base: `factory_route: no routing table: code` (`--route` consumed as ROLE, `code` as FILE). |
| `route.py` removed + HEAD's bats | **not red — SKIP**: `ok 18 … # skip tools/factory/route.py not copied into the unit-check sandbox`. |
| `route.py` removed + HEAD's `render.test.mjs` | **not red — PASS**: `render.test.mjs: all assertions passed` (the `pinned` fallback). |
| base `dark-factory.js` + HEAD's `render.test.mjs` | passes — the diff to `dark-factory.js` is header comment only; the `models` literal is unchanged at base, so the new assertion could not have been red on that file. |

So the bash half has a genuine red; the `factory-unit` half is a pin (green
from the moment it was written), which is defensible for a drift check — but
its load-bearing-ness then rests entirely on mutation, see M8 below.

## Mutation table

Each applied to the working tree, `nix develop -c bats
tests/unit/80-seat-driver.bats` **and** `nix develop -c node
tests/factory/render.test.mjs` run (full tree), then reverted. Twenty-four
mutations: **twenty-two killed, two survived**.

| # | Mutation | Result | Killed by |
| --- | --- | --- | --- |
| M1 | `--route` flag ignored (`route=$2` → `: "$2"`) | KILLED | bats 16, 17, 18 |
| M2 | row without `route` defaults to `claude` | KILLED | bats 11, 15, 16, 19 |
| M3 | bash accepts `route = "other"` (`openrouter \| claude \| other`) | KILLED | bats 16 |
| M4a | **`route.py` tie order flipped (`spec > best_spec` → `>=`)** | **SURVIVED** | — |
| M4b | `route.py` specificity inverted (least specific wins) | KILLED | bats 18 + render (`must equal route.py models`) |
| M5 | `route.py models` maps `reviewCode` from the **docs** row | KILLED | render (`must equal route.py models`); bats green |
| M6 | `dark-factory.js` default `reviewCode: 'opus'` → `'sonnet'` | KILLED | render + sandboxed `factory-unit` — but by the **pre-existing** assertion `the integration fix runs on the technical authority`, which trips before scenario 26 |
| M7 | claude default (`any/any/any`) row deleted from the table | KILLED | bats 13, 18; `route.py check` → `no default (any/any/any) row for route 'claude'` rc=1; `factory_route_check` rc=3 |
| M8 | **table-only drift**: claude `review/code` `opus` → `sonnet`, scripts untouched | KILLED **only by the lint gate** (`render.test.mjs` on the full tree). `nix build .#checks.x86_64-linux.factory-unit` → **green** | render (`dark-factory.js default models must equal route.py models for the committed table`) |
| M9 | `route.py` accepts `route = "other"` (added to `ROUTES`) | KILLED | bats 18 |
| M10 | **`route.py` missing-key validation dropped** (block → `setdefault`s) | **SURVIVED** | — |
| R-M1 | ties go to the LAST row (`-gt` → `-ge`, bash) | KILLED | bats 11 |
| R-M2 | `any` not matched for `kind` | KILLED | bats 11, 16, 18, 19 |
| R-M3 | no-default-row check disabled (`-eq 1` → `-ge 0`) | KILLED | bats 12, 17 |
| R-M4 | effort value validation dropped | KILLED | bats 12 |
| R-M7 | `factory-task` seat launched without the effort | KILLED | bats 15 |
| R-M8 | `route:` line always says `explicit` | KILLED | bats 15 |
| R-M9 | `effort:` line dropped from the `.result` | KILLED | bats 15 |
| Rb-a | route clobbers `--model` (`if [ -n "$model" ]` → `if false`) | KILLED | bats 15 |
| Rb-b | `effort=$route_effort` (env override lost) | KILLED | bats 15 |
| Rb-c | `factory-review` looks up role `implement` | KILLED | bats 19 |
| Rb-d | `factory-review` seat launched without the effort | KILLED | bats 19 |
| Rb-e | unknown role word accepted | KILLED | bats 12 |
| Rb-f | `model = ""` accepted | KILLED | bats 12 |

RT1's seven killed mutants and RT1b's six all still die (R-M1…R-M9, Rb-a…Rb-f
above): **13/13**.

**M4a is a real divergence, not a no-op.** On a fixture with an observable tie
(claude default; `implement/docs/any → m/first`; `implement/any/XS →
m/second`), looking up `claude implement docs XS`:

```
=== HEAD ===            bash: m/first low     py:   m/first low
=== M4a applied ===     bash: m/first low     py:   m/second low
```

The committed cross-check cannot see it: its only real tie
(`openrouter implement/docs/any` vs `implement/any/XS`) prints
`deepseek/deepseek-v4-flash off` from either row.

## Real data

From the clone, read-only:

```
$ bash -c '. tools/factory/seat/factory-lib.sh; factory_route --route claude review code any docs/ledger/routing.toml; \
           factory_route --route claude review docs S docs/ledger/routing.toml; \
           factory_route implement docs XS docs/ledger/routing.toml; \
           factory_route_check docs/ledger/routing.toml; echo rc=$?'
opus high
sonnet medium
deepseek/deepseek-v4-flash off
rc=0

$ nix develop -c python3 tools/factory/route.py models
{"baseline": "sonnet", "impl": "sonnet", "reviewCode": "opus", "reviewDocs": "sonnet", "verify": "sonnet", "audit": "fable"}

$ nix develop -c python3 tools/factory/route.py check; echo rc=$?
rc=0
```

`tools/factory/dark-factory.js:98`:
`{ baseline: 'sonnet', impl: 'sonnet', reviewCode: 'opus', reviewDocs: 'sonnet', verify: 'sonnet', audit: 'fable' }`
— key-for-key equal to the `models` output above, and equal to the model
policy's table (`docs/decisions/2026-09-02-factory-model-policy.md`: baseline
Sonnet low, implement Sonnet high, review-code Opus high, review-docs Sonnet
medium, verify Sonnet medium, audit Fable high — efforts match the claude rows
too).

Cross-check, nine tuples (six required plus three), `factory_route --route R`
vs `route.py lookup R`, on the committed table — **all identical**:

| route | role | kind | size | both print |
| --- | --- | --- | --- | --- |
| claude | review | code | S | `opus high` |
| claude | review | docs | XS | `sonnet medium` |
| claude | implement | code | M | `sonnet high` |
| claude | verify | code | L | `sonnet medium` |
| claude | audit | any | any | `fable high` |
| claude | orchestrate | any | any | `fable high` |
| openrouter | implement | docs | XS | `deepseek/deepseek-v4-flash off` |
| openrouter | review | code | S | `deepseek/deepseek-v4-pro-0813 medium` |
| openrouter | implement | any | XS | `deepseek/deepseek-v4-flash off` |

## Findings

1. **(blocker) The two lookup implementations' tie rule is unverified.**
   M4a survives. Fix: give the cross-check a fixture with a discriminating
   tie (two claude rows at specificity 2 with *different* models) and assert
   `factory_route` and `route.py lookup` agree there, in addition to the
   committed-table tuples. The plan's wording ("on the same fixture") already
   asks for this.
2. **(blocker) `route.py`'s missing-key validation is dead code under test.**
   M10 survives. Fix: add a bad-table fixture whose second row omits `effort`
   and assert `route.py check` exits 1 naming row 2 (the `route = "other"`
   fixture already proves the row-number reporting works, so this is one more
   heredoc).
3. **(blocker) The commit message overstates what `factory-unit` proves.**
   M8 shows a table-only drift leaves `factory-unit` green. Either reword the
   body to name the lint gate as the drift refusal (matching the accurate
   `FACTORY-NOTES`), or — if the orchestrator lifts the `flake.nix` freeze —
   copy `tools/factory/route.py` and `docs/ledger/routing.toml` into the
   `factory-unit` and `unit` sandboxes, which would also un-skip tests 125 and
   130 and make the claim true as written. The `pinned` fallback in
   `render.test.mjs` is a third copy of the same truth; it is fail-closed (a
   table change forces edits in three places) but it is why the sandbox
   assertion cannot see M8.
4. **(minor) `tools/factory/route.py` is not linted by the gate.** `treefmt`
   formats it (`[formatter.python]` includes `*.py`), but the `ruff check`
   argument list in `githooks/pre-commit:25` and `flake.nix:889` names
   `tools/factory/seat`, not `tools/factory`. `ruff check` on the file passes
   when run by hand, but nothing gates it. The implementer spotted this
   (transcript line 1895) and could not act — both files are frozen for this
   task — but it did not reach `FACTORY-NOTES`. Add `tools/factory` to both
   lists in whichever task owns those files.
5. **(minor) Duplicate scenario number.** `tests/factory/render.test.mjs` now
   has two `// Scenario 26` comments — the pre-existing `(E3)` block at :864
   and the new `(RT2)` block at :918. Renumber the new one.
6. **(minor) `factory_route_check`'s comment overstates the implementation.**
   It says "every route present in the table has a default", but the body
   hard-codes an `openrouter` then a `claude` probe. Equivalent today because
   the route word list is closed; the comment should say so, or the function
   should derive the route set.

Nothing else: no `sudo`, no `nixos-rebuild`, no `systemctl`, no seat launched,
no writes outside the workspace, no third-party imports in `route.py`, no
secrets.

## Deviations

- **From the plan, forced:** RT2's step 4 lists `unit` and `factory-unit` as
  acceptance, but the plan also freezes `flake.nix`; with those sandboxes
  unchanged the two new real-table tests skip and the drift assertion falls
  back to a literal. RT1b's gate had already recorded "RT2 moves that check
  into the flake" — that never happened, and it cannot happen under RT2's
  constraints. The orchestrator needs to decide who lands the `flake.nix`
  sandbox change (also finding 4's `ruff check` list).
- **From this gate's script:** the plan's mutation "`route.py lookup`
  specificity differs from `factory_route` … the cross-check test fails" was
  run and the mutant **survived**; it is blocker 1 rather than a killed row.
- Nine cross-check tuples were run rather than six (the extra three probe the
  `orchestrate` row and the openrouter tie).
- The `.result` `FACTORY-NOTES` line is accurate about the sandbox gap; the
  commit message body is not. That contradiction is blocker 3.
