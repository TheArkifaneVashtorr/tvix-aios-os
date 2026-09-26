---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run rt4, task RT4 — APPROVED

## Summary

RT4 asked for one thing: make `FACTORY_ROUTING_TABLE` real in both routing
lookups, with an explicit `FILE` / `--file` still winning. The commit does
exactly that and nothing else. `factory_route` and `factory_route_check` in
`tools/factory/seat/factory-lib.sh` both default to
`${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml}`;
`tools/factory/route.py` sets
`DEFAULT_FILE = os.environ.get("FACTORY_ROUTING_TABLE", "docs/ledger/routing.toml")`
— both literally the expressions the plan's Interfaces section names. Three
bats tests were added and all three are load-bearing: reverting the two
implementation files to the base commit while keeping HEAD's tests turns each
of them red. Nineteen mutations were applied to the working tree and all
nineteen died, including the five that target this change's exact
failure modes and fourteen previously-killed mutants from RT1 / RT1b / RT2b.
Real-data probes against the committed table return the production answers
through the env var and fail loudly (rc 3, named path) on a missing table, so
the harness prose the H2 gate rejected is now true. `unit`, `lint`, the
pre-commit gate, shellcheck and ruff are all green.

## Checks

| item | result |
| --- | --- |
| exactly one commit on base `9af2474` (`git rev-list --count HEAD ^9af2474` = 1, base is parent) | pass |
| `git show --stat HEAD` = exactly `tests/unit/80-seat-driver.bats`, `tools/factory/route.py`, `tools/factory/seat/README.md`, `tools/factory/seat/factory-lib.sh` (4 files, +134/−5) | pass |
| commit subject byte-identical to the plan's (`cmp` against a written-out copy) | pass |
| `Co-Authored-By: Claude Fable 5.1` trailer (plus a `Generated-By:` line) | pass |
| bash default `${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml}` in **both** `factory_route` (`:199`) and `factory_route_check` (`:352`) | pass |
| python `DEFAULT_FILE = os.environ.get("FACTORY_ROUTING_TABLE", "docs/ledger/routing.toml")` (`route.py:35`) | pass |
| explicit `FILE` / `--file` wins over the env var in both | pass (mutations N3, N4) |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass — 157/157, the three new tests run **for real** (`ok 130`, `ok 131`, `ok 135`; no `# skip`) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | pass (incl. `render.test.mjs: all assertions passed`) |
| `shellcheck tools/factory/seat/factory-lib.sh` | clean |
| `ruff check` + `ruff format --check tools/factory/route.py` | clean |
| hard rules: no `sudo` / `nixos-rebuild` / `systemctl` anywhere in the diff; no `flake.nix`, `githooks/pre-commit` or `pkgs/evidence` touched; no new language; working tree clean after every experiment | pass |
| the implementer workspace was not touched (all work in a throwaway clone) | pass |

## Red before green

`git checkout 9af2474 -- tools/factory/seat/factory-lib.sh tools/factory/route.py`
(base implementation, HEAD's tests), then
`nix develop -c bats tests/unit/80-seat-driver.bats`:

```
not ok 18 factory_route honors FACTORY_ROUTING_TABLE as the default table and an explicit FILE still wins
#   `[ "$output" = "x/env-code high" ]' failed
not ok 19 factory_route_check honors FACTORY_ROUTING_TABLE as the default table
#   `[ "$status" -eq 3 ]' failed
not ok 23 route.py honors FACTORY_ROUTING_TABLE as the default table and an explicit --file still wins
#   `[ "$output" = "x/env-model high" ]' failed
```

Base confirmed to be the pre-change state:
`factory-lib.sh:197,348` = `${4:-$FACTORY_TOOLBOX_REPO/…}` / `${1:-$FACTORY_TOOLBOX_REPO/…}`,
`route.py:30` = `DEFAULT_FILE = "docs/ledger/routing.toml"`. All three new
tests are therefore genuinely red before the change. Restored; the file is
green again (`ok 22`, `ok 23`, `ok 24` tail) and `git status --porcelain` empty.

## Mutation table

Each mutation applied to the working tree of the throwaway clone,
`nix develop -c bats tests/unit/80-seat-driver.bats` **and**
`nix develop -c node tests/factory/render.test.mjs` run, then reverted
(`git status --porcelain` empty after each; a mutation that failed to apply
was reported as a no-op and reworked, never counted). **Nineteen mutants,
nineteen killed, none survived.** Test numbers are within
`tests/unit/80-seat-driver.bats` (they shift by the three tests this commit
inserts).

RT4-specific — the five failure modes this change must be pinned against:

| # | Mutation | Result | Killed by |
| --- | --- | --- | --- |
| N1 | **env var ignored in bash** (`factory_route` back to `${4:-$FACTORY_TOOLBOX_REPO/…}`) | KILLED | bats 18 |
| N2 | **env var ignored in python** (`DEFAULT_FILE` hard-coded again) | KILLED | bats 23 |
| N3 | **env var beats an explicit FILE (bash)** (`${FACTORY_ROUTING_TABLE:-${4:-…}}`) | KILLED | bats 18 |
| N4 | **env var beats `--file` (python)** (`path = os.environ.get("FACTORY_ROUTING_TABLE", args[1])` after parsing) | KILLED | bats 23 |
| N5 | **`factory_route_check` keeps the old default** while `factory_route` honours the env | KILLED | bats 19 |

Previously-killed mutants re-run on this tree — all still die:

| # | Mutation | Result | Killed by |
| --- | --- | --- | --- |
| R-M1 | bash tie goes to the LAST row (`-gt` → `-ge`) | KILLED | bats 11, 21 |
| R-M2 | bash `any` not matched for `kind` | KILLED | bats 11, 16, 18, 20, 24 |
| R-M3 | bash no-default-row check disabled (`-eq 1` → `-ge 0`) | KILLED | bats 12, 17, 19 |
| R-M4 | bash effort-value validation dropped | KILLED | bats 12 |
| Rb-e | bash unknown role word accepted | KILLED | bats 12 |
| Rb-f | bash `model = ""` accepted (`''` alternate dropped) | KILLED | bats 12 |
| M1 | bash `--route` flag ignored (`route=$2` → `: "$2"`) | KILLED | bats 16, 17, 19, 20 |
| M2 | bash row without `route` defaults to `claude` | KILLED | bats 11, 15, 16, 18, 21, 24 |
| M3 | bash accepts `route = "other"` | KILLED | bats 16 |
| M4a | `route.py` tie-break flipped (`spec > best_spec` → `>=`) | KILLED | bats 21 |
| M9 | `route.py` accepts `route = "other"` (added to `ROUTES`) | KILLED | bats 20, 22 |
| M10 | `route.py` missing-key validation dropped (`setdefault`s) | KILLED | bats 22 |
| Rb-a | `factory-task`: route clobbers `--model` (`if [ -n "$model" ]` → `if false`) | KILLED | bats 15 |
| Rb-c | `factory-review` looks up role `implement` | KILLED | bats 24 |

## Real data

From the clone, against the committed `docs/ledger/routing.toml`, with
`FACTORY_TOOLBOX_REPO` **unset** (so only the env var can find the table):

```
$ FACTORY_ROUTING_TABLE=docs/ledger/routing.toml bash -c '. tools/factory/seat/factory-lib.sh;
    factory_route --route claude review code any; factory_route implement docs XS'
opus high
deepseek/deepseek-v4-flash off                          rc=0

$ FACTORY_ROUTING_TABLE=/nonexistent bash -c '. tools/factory/seat/factory-lib.sh;
    factory_route implement docs XS'
factory_route: no routing table: /nonexistent           rc=3
```

Both production answers are exactly the expected ones, and the missing-table
case is loud: rc 3 with the offending path named on stderr — which is what the
harness prose relies on. Further probes:

| probe | result |
| --- | --- |
| `route.py lookup claude review code any` with the env var, cwd `/tmp` | `opus high`, rc 0 |
| `route.py models` with the env var, cwd `/tmp` | `{"baseline":"sonnet","impl":"sonnet","reviewCode":"opus","reviewDocs":"sonnet","verify":"sonnet","audit":"fable"}` |
| `route.py check`, no env var, cwd `/tmp` (relative default) | rc 1, `cannot read docs/ledger/routing.toml` — the fallback is unchanged |
| `route.py check` with `FACTORY_ROUTING_TABLE=/nonexistent` | rc 1, `cannot read /nonexistent` |
| bash with `FACTORY_ROUTING_TABLE=` (set but empty) + `FACTORY_TOOLBOX_REPO` | `deepseek/deepseek-v4-flash off` — falls back to the repo path (`:-` semantics), as the plan's literal expression specifies |
| bash with the env var unset + `FACTORY_TOOLBOX_REPO`: `factory_route --route claude orchestrate any any`; `factory_route_check` | `fable high`; rc 0 — no regression to the old default path |

## Findings

1. **(minor, non-blocking) The fallback warning now names the wrong table.**
   `tools/factory/seat/factory-task` (and the same shape in `factory-review`)
   still logs
   `warning: routing table unusable (docs/ledger/routing.toml); using built-in default …`
   when `factory_route` fails. Under a `FACTORY_ROUTING_TABLE` override that
   string names a table that was never read. Mitigated in practice:
   `factory_route`'s own stderr line does name the real path and is not
   swallowed (`$( … || true )` captures stdout only). Worth a one-word fix
   when RT5 next touches these two scripts; RT4's file list did not include
   them, so fixing it here would have been out of scope.
2. **(positive) The new `route.py` test cannot go vacuous.** Unlike RT2b's
   two cross-check tests, the new one has no `[ -f "$route_py" ] || skip`
   guard — if the `flake.nix` sandbox copy ever regresses this test fails
   rather than silently skipping. Confirmed it executes for real inside
   `checks.unit` (`ok 135`, not `# skip`).
3. **(minor) Half of the `factory_route_check` test is vacuous.** Its first
   assertion (`status -eq 0` on a valid two-route fixture) also passes with
   the env var ignored, because the committed table is valid. Only the second
   half (a fixture with no `claude` default → rc 3) discriminates. Mutation N5
   shows the test as a whole is load-bearing, so this is a note, not a defect.
4. **(note for RT5) Empty means unset.** `FACTORY_ROUTING_TABLE=` (set,
   empty) falls back to `$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml`
   rather than failing. That is precisely the `${…:-…}` expression RT4's
   Interfaces section prescribes, and it is measured above — but RT5 shares
   this default in the hook guard and its "table unreadable → deny" rule
   should be written knowing an empty env var silently means "the repo table".
5. **(no new hole) The drift check is immune to the env var.**
   `tests/factory/render.test.mjs:935` runs `route.py` with an explicit
   `--file`, so a stray `FACTORY_ROUTING_TABLE` in a developer's or a
   sandbox's environment cannot make `checks.factory-unit` compare
   `dark-factory.js` against some other table. Verified by reading the call
   and by `githooks/pre-commit` passing.

## Deviations

- **One test beyond the plan.** RT4 Step 1 asked for two bats tests per
  lookup (env honoured; explicit file wins). The implementer added a third,
  `factory_route_check honors FACTORY_ROUTING_TABLE as the default table`.
  It is inside a file the task already owns, and it is load-bearing (it is
  the only thing that kills N5, the "check still reads the old default"
  mutant). Accepted as an improvement, recorded here because it widens the
  diff over the plan's letter.
- **Commit body carries a `Generated-By:` line** in addition to the required
  `Co-Authored-By:` trailer. Permitted by the gate brief.
- **Plan heading vs commit subject wording.** The RT4 heading says "for every
  caller" while the plan's mandated commit subject says "for the bash and
  python lookups"; the commit uses the mandated subject byte-for-byte. In
  substance both are satisfied — `factory-task` and `factory-review` call
  `factory_route` with no FILE argument, so they inherit the override with no
  further change (verified by reading `factory-task:80` and
  `factory-review:69`).
- Nothing else. No files outside the four named were modified, and the
  implementer workspace was left untouched.
