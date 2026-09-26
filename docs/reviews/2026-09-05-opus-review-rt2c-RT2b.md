---
reviewer: opus
majors: null
minors: null
mutants_killed: 24
---
# Opus gate — seat run rt2c, task RT2b — APPROVED

## Summary

The fix round closes all three blockers with evidence this gate reproduced by
hand. The two mutants that survived RT2 now die; the sandbox change is real —
a table-only drift now fails `checks.factory-unit`, and the two formerly
skipped tests run for real inside `checks.unit`.

- One commit on `04a3eb9`, exactly the nine planned touches (RT2's seven plus
  `flake.nix` and `githooks/pre-commit`), subject byte-identical to RT2's,
  `Co-Authored-By` present (plus a `Generated-By` line).
- **Blocker 1 closed.** New bats test 131 (`factory_route and route.py agree
  on a discriminating tie`) is fail-closed and load-bearing: flipping
  `route.py`'s `spec > best_spec` to `>=` fails it locally *and* fails
  `nix build .#checks.x86_64-linux.unit`.
- **Blocker 2 closed.** New bats test 132 drives five missing-key fixtures,
  `route = "other"` and a bad effort; replacing the key check with
  `setdefault`s kills the suite.
- **Blocker 3 closed.** `flake.nix` copies `route.py` + `routing.toml` into
  both the `unit` and `factory-unit` sandboxes (and adds `python3` to
  `factory-unit`); the claude `review/code` `opus → sonnet` drift with the
  scripts untouched now makes `factory-unit` **fail**. The build log shows
  `ok 125` and `ok 130` with no `# skip`. `route.py` is in the `ruff check`
  and `ruff format --check` lists in both `githooks/pre-commit` and the `lint`
  runCommand; an injected `F401` fails both.
- Minors from RT2 closed: the duplicate `// Scenario 26` is gone (the new
  block is `Scenario 27`), and `factory_route_check`'s comment now describes
  the two-route probe it actually performs.
- All five acceptance commands green; 24 mutants applied, **24 killed, 0
  survived**; real-data lookups exact; `route.py models` equals
  `dark-factory.js:98` key-for-key; six cross-check tuples identical.

## Checks

Throwaway clone of `/home/dalhaka/factory/ws/rt2c/RT2b` at `task/RT2b`
(`0f5606973927`), `XDG_CACHE_HOME` under the session scratchpad, tooling only
via `nix develop -c`.

| command | result |
| --- | --- |
| `git show --stat HEAD` | 9 files, exactly RT2b's `touches` |
| subject byte-diff vs the plan (line 226) | identical (`diff` empty) |
| parents / commits on base | one commit, parent `04a3eb9358e9` |
| trailers | `Generated-By: dsh 0.1.2-rc.1 / …` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass (also `--rebuild`, for the log) |
| `nix build .#checks.x86_64-linux.factory-unit -L --no-link --rebuild` | pass |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | pass (`render.test.mjs: all assertions passed`) |
| `nix develop -c shellcheck tools/factory/seat/factory-lib.sh` | clean |
| `nix develop -c ruff check tools/factory/route.py` | `All checks passed!` |
| `nix develop -c ruff format --check tools/factory/route.py` | `1 file already formatted` |
| `nix develop -c bats tests/unit/80-seat-driver.bats` | 21/21 ok |
| stdlib scan of `route.py` | `import json`, `import sys` only |
| seat launched? | no — the transcript's only `dsh-openrouter` line is the driver's own banner; zero hits for `sudo`/`nixos-rebuild`/`systemctl` |
| working tree after every experiment | `git status --porcelain` empty |

**The sandbox un-skip (blocker 3, first half).** From the `unit` check's own
rebuild log:

```
unit-tests> ok 125 factory_route_check validates the committed routing table
unit-tests> ok 130 route.py validates the committed table and cross-checks factory_route's lookup, when route.py is present
unit-tests> ok 131 factory_route and route.py agree on a discriminating tie (earliest row wins)
unit-tests> ok 132 route.py check rejects a row missing any required key, a bad route, or a bad effort
```

No `# skip` on any of them; the only six `# skip` lines in the whole log are
the pre-existing basket mount tests (17–22).

**`flake.nix`, reviewed line by line.** Three hunks, nothing else:

1. `lint` runCommand — `tools/factory/route.py` inserted into the `ruff check`
   and the `ruff format --check` argument lists (after `tools/factory/seat`).
2. `factory-unit` — `nativeBuildInputs` gains `pkgs.python3` (with a comment
   saying why); `mkdir -p` gains `docs/ledger`; two `cp` lines add
   `tools/factory/route.py` and `docs/ledger/routing.toml`.
3. `unit` — two `cp` lines plus `mkdir -p docs/ledger`, commented.

`git diff 04a3eb9..HEAD -- flake.nix` contains those and only those; `unit`
already had `pkgs.python3` on its `nativeBuildInputs`. No other flake change.

**Files carried unchanged from RT2** (so the RT2 gate's byte-level table
verification stands): `git diff` between RT2's head (`5f27d25a7851`) and this
head is empty for `docs/ledger/routing.toml`, `tools/factory/dark-factory.js`,
`tools/factory/route.py` and `tools/factory/seat/README.md`. RT2b's own diff is
`flake.nix`, `githooks/pre-commit`, `tests/unit/80-seat-driver.bats` (+184),
`tests/factory/render.test.mjs` (net -0, renumber + comment), and a three-line
comment fix in `factory-lib.sh`. Re-confirmed independently here: 14 rows, 14
carry `route`, file ends with a single `\n`.

## Red before green

`route.py` and the table are byte-identical to RT2's, so the fix round is
test/infrastructure only — there is no "code was wrong, now right" red to
show, and the plan says so (its reds are mutations). Each is reproduced below
with my own hands, and each new test is fail-closed:

| experiment | result |
| --- | --- |
| `route.py` tie-break `>` → `>=` | **red**: `not ok 19` (local) / `not ok 131` (inside `nix build … .unit`); revert → green |
| `route.py` missing-key block → `setdefault`s | **red**: `not ok 20 route.py check rejects a row missing any required key…`; revert → green |
| table-only drift (`claude review/code` `opus → sonnet`, scripts untouched) | **red**: `nix build .#checks.x86_64-linux.factory-unit` fails with `ERR_ASSERTION … deepStrictEqual` at `render.test.mjs:936`; revert → green |
| `import os` (unused) added to `route.py` | **red**: `lint` check and `githooks/pre-commit` both fail with `F401 [*] 'os' imported but unused --> tools/factory/route.py` |
| the three `cp` lines removed from `flake.nix`'s `unit` block | **red**: `unit` fails — 125/130 fall back to their defensive skips but `not ok 131`, `not ok 132` (they reference `route.py` unconditionally), so the sandbox wiring is itself pinned, not fail-open |

## Mutation table

Each applied to the working tree, `nix develop -c bats
tests/unit/80-seat-driver.bats` **and** `node tests/factory/render.test.mjs`
run on the full tree, then reverted (`git status --porcelain` empty after
each). Twenty-four mutants: **twenty-four killed, none survived.** RT2's 22
killed mutants were all re-run (9 RT2-specific + RT1's 7 + RT1b's 6) and all
still die; the two that survived RT2 now die.

| # | Mutation | Result | Killed by |
| --- | --- | --- | --- |
| M4a | **`route.py` tie order flipped (`spec > best_spec` → `>=`)** | **KILLED** (was SURVIVED) | bats 19 (`… discriminating tie`); also `not ok 131` inside `checks.unit` |
| M10 | **`route.py` missing-key validation dropped (block → `setdefault`s)** | **KILLED** (was SURVIVED) | bats 20 (`route.py check rejects a row missing any required key…`) |
| M8 | **table-only drift**: claude `review/code` `opus → sonnet` | **KILLED by `checks.factory-unit`** (was green there) | render + `nix build …factory-unit` |
| M1 | `--route` flag ignored (`route=$2` → `: "$2"`) | KILLED | bats 16, 17, 18 |
| M2 | row without `route` defaults to `claude` | KILLED | bats 11, 15, 16, … (5 failures) |
| M3 | bash accepts `route = "other"` | KILLED | bats 16 |
| M4b | `route.py` specificity inverted (least specific wins) | KILLED | bats 18, 19 + render |
| M5 | `route.py models` maps `reviewCode` from the **docs** row | KILLED | render |
| M6 | `dark-factory.js` default `reviewCode: 'opus'` → `'sonnet'` | KILLED | render |
| M7 | claude default (`any/any/any`) row deleted from the table | KILLED | bats 13, 18; render; `route.py check` → `no default (any/any/any) row for route 'claude'` rc=1 |
| M9 | `route.py` accepts `route = "other"` (added to `ROUTES`) | KILLED | bats 18, 20 |
| RUFF | unused `import os` in `route.py` | KILLED | `lint` check **and** `githooks/pre-commit` (`F401`) |
| R-M1 | ties go to the LAST row (`-gt` → `-ge`, bash) | KILLED | bats 11, 19 |
| R-M2 | `any` not matched for `kind` | KILLED | bats 11, 16, 18, … |
| R-M3 | no-default-row check disabled (`-eq 1` → `-ge 0`) | KILLED | bats 12, 17 |
| R-M4 | effort value validation dropped | KILLED | bats 12 |
| R-M7 | `factory-task` seat launched without the effort | KILLED | bats 15 |
| R-M8 | `route:` line always says `explicit` | KILLED | bats 15 |
| R-M9 | `effort:` line dropped from the `.result` | KILLED | bats 15 |
| Rb-a | route clobbers `--model` (`if [ -n "$model" ]` → `if false`) | KILLED | bats 15 |
| Rb-b | `effort=$route_effort` (env override lost) | KILLED | bats 15 |
| Rb-c | `factory-review` looks up role `implement` | KILLED | bats 21 |
| Rb-d | `factory-review` seat launched without the effort | KILLED | bats 21 |
| Rb-e | unknown role word accepted | KILLED | bats 12 |
| Rb-f | `model = ""` accepted | KILLED | bats 12 |

Two extra table probes, run against the built checks rather than bats:

| probe | result |
| --- | --- |
| openrouter default (`any/any/any`) row deleted | `route.py check` rc=1 (`no default … for route 'openrouter'`); `checks.unit` **fails** (`not ok 125`, `not ok 130`); `githooks/pre-commit` **passes** — see finding 1 |
| `flake.nix` `unit` copies removed | `checks.unit` **fails** (`not ok 131`, `not ok 132`) |

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
policy table in `docs/decisions/2026-09-02-factory-model-policy.md`.

Cross-check, the six required tuples, `factory_route --route R` vs
`route.py lookup R`, on the committed table — **all identical**:

| route | role | kind | size | both print |
| --- | --- | --- | --- | --- |
| claude | review | code | S | `opus high` |
| claude | review | docs | XS | `sonnet medium` |
| claude | implement | code | M | `sonnet high` |
| claude | verify | code | L | `sonnet medium` |
| claude | audit | any | any | `fable high` |
| openrouter | implement | docs | XS | `deepseek/deepseek-v4-flash off` |

The committed test itself runs seven such tuples (the six above plus
`openrouter review code S`) and, separately, the discriminating-tie fixture.

## Findings

1. **(minor) One clause of the commit body is slightly wider than the hook.**
   The body says "`githooks/pre-commit` refuses a table that fails
   `route.py check`: its `render.test.mjs` derives the map via `route.py
   models`, which validates every row the same way `check` does." The
   *row* validation claim is exact — `resolve()` validates every row on any
   lookup — but `models` only probes the **claude** default row, while `check`
   probes both. Measured counter-example: delete the `openrouter`
   `any/any/any` row → `route.py check` exits 1, and `nix develop -c
   githooks/pre-commit` still **passes**. That failure mode is caught by
   `checks.unit` (`not ok 125 factory_route_check validates the committed
   routing table`), which the body's third bullet names, so the three bullets
   together are honest and no drift goes unrefused. Not a blocker: the wording
   is the plan's own Step 4 text, and the gap is one probe, not the whole
   claim. Worth one word ("a malformed row") on any later edit.
2. **(minor) A stale count in a test comment.** Test 130 says "Six fixed
   tuples: the bash lookup and the python lookup print identical lines" above
   a heredoc listing **seven**. Cosmetic; the test is correct.
3. **(nit) The two defensive `skip` guards.** Tests 125 and 130 still skip if
   the table / `route.py` are absent. Probed: this is not fail-open in
   aggregate — removing the `flake.nix` copies makes `checks.unit` fail on
   131/132, which have no guard. The comments say the guards are defensive.
   No action needed.

Nothing else: no `sudo`, no `nixos-rebuild`, no `systemctl`, no seat launched,
no writes outside the clone/scratchpad, no third-party imports in `route.py`,
no secrets, `flake.nix` touched only in the three reviewed hunks.

## Deviations

- **From the plan, deliberate and defensible:** Step 2 asks for missing-key
  fixtures for **six** keys including `route`; the implementation validates
  **five** (`role`/`kind`/`size`/`model`/`effort`) because `route` is optional
  and defaults to `openrouter` — in `route.py` *and* in bash
  (`_factory_route_finish_row`), which is RT2's own contract ("rows without
  `route` default to `openrouter`", pinned by bats test 16 and by the
  `check-no-route.toml` fixture in test 132). Requiring `route` would have
  broken that contract. The two implementations agree, the tests pin all five
  plus the optional-`route` case, so I accept it. The `.result`
  `FACTORY-NOTES` states this accurately.
- **From this gate's script:** 24 mutants were run rather than the requested
  ≥10 regressions (RT2's full 22, plus M4a and M10 which had survived), plus
  the `RUFF` mutant and two extra probes (openrouter-default deletion, and
  removing the `flake.nix` copies) that the script did not ask for.
- Six cross-check tuples were run as specified; the committed test runs seven.
