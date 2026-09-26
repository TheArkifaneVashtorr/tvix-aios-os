---
reviewer: opus
majors: null
minors: 1
---
# Opus gate — seat run rt1, task RT1b — APPROVED

Gate: Opus, adversarial, evidence-only. Reviewed in a throwaway clone of
`/home/dalhaka/factory/ws/rt1/RT1b` at `817e4e9` on base `d0521db`, with
RT1's `4ef92e2` fetched read-only from `/home/dalhaka/factory/ws/rt1/RT1` for
the diff. Neither implementer workspace was touched; nothing was written
outside the clone, the nix cache dir and this file.

## Summary

The fix round does exactly what the rejection asked and nothing else. All three
MAJORs are closed by test, proven by my own mutations: `--model` beating the
route, a NON-empty `OPENROUTER_REASONING_EFFORT` beating the route's effort,
and a `factory-review` test whose fixture table deliberately gives `review` a
different model from `implement` so the role lookup and the launch-env effort
are both pinned. Two of the minors are closed by one-line code fixes
(`model = ""` now exits 3; the `2>/dev/null` is gone from both `factory_route`
call sites, so a bad row's message is visible again) and one by a byte
(`routing.toml` now carries its trailing newline and is byte-identical to the
plan's block, 1131 bytes).

Six required mutants applied by hand: **all six die**. RT1's seven previously
killed mutants: **all seven still dead**. Red before green for the round is
genuine and shown both ways — under RT1's own bats file every one of the six
survives; under HEAD's bats every one fails, on the exact new assertion.

Every acceptance check passes, the diff against RT1 is confined to the five
lines the plan allowed, and the commit subject is byte-identical to RT1's.

## Checks

All run from the clone, `XDG_CACHE_HOME` pinned under the scratchpad, tooling
via `nix develop -c`.

| Check | Result |
| --- | --- |
| one commit on base | `817e4e9` only, on `d0521db` (`git log d0521db..task/RT1b` = 1) |
| `git show --stat HEAD` | the six files: `docs/ledger/routing.toml`, `tests/unit/80-seat-driver.bats`, `tools/factory/seat/{README.md,factory-lib.sh,factory-review,factory-task}` — ⊆ RT1b's touches plus RT1's README carried unchanged |
| commit subject | byte-identical to the plan's `commit subject:` line AND to RT1's `4ef92e2` subject (`diff` clean on both) |
| trailers | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present, preceded by the allowed `Generated-By: dsh …` line |
| diff vs RT1 `4ef92e2`, scripts | exactly two hunks: `factory-lib.sh` `*[!A-Za-z0-9._:/-]*)` → `'' \| *[!A-Za-z0-9._:/-]*)`; `2>/dev/null` removed from the `factory_route` call in `factory-task:80` and `factory-review:69`. Nothing else. |
| diff vs RT1, `routing.toml` | one hunk: the missing final newline added. Content otherwise unchanged. |
| diff vs RT1, `README.md` | empty — carried verbatim |
| `routing.toml` vs the plan's verbatim block | **byte-identical, 1131 = 1131** (RT1's Deviation 1 closed) |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass; the routing tests are 123–128 in the log, **including the new `ok 128 factory-review resolves role review …`**; 125 still `# skip` (see Deviations) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass (formatted 84 files, 0 changed; all checks passed) |
| `nix develop -c githooks/pre-commit` | pass (treefmt 84/0, statix/deadnix/ruff clean, `render.test.mjs` ok) |
| `nix develop -c shellcheck` on the three seat scripts | clean, exit 0 |
| `nix develop -c bats tests/unit/80-seat-driver.bats` | 16/16 pass |
| remaining `2>/dev/null` in the three scripts | 7, all pre-existing (`git rev-parse`, `git log`, `find`, `zstd`, `git config`), none on a gated command and none on a routing call |
| hard rules | no `sudo`, `nixos-rebuild`, `systemctl start/stop/restart`, `--no-verify`, `git push` on any added line or anywhere in the transcript (all five greps = 0 hits); working tree clean after every mutation |
| no seat launched | the transcript's only real `dsh-openrouter` line is the harness's own banner (line 1); every other mention is the fake in the tests or quoted source |

## Red before green

Two states, same six mutations, run by me.

**State 1 — RT1's bats file (`git checkout 4ef92e2 -- tests/unit/80-seat-driver.bats`)
over HEAD's scripts.** Unmutated: 15/15 green. Then each mutant, `bats` after
each, revert after each:

```
### a (old tests): SURVIVED (bats rc=0)
### b (old tests): SURVIVED (bats rc=0)
### c (old tests): SURVIVED (bats rc=0)
### d (old tests): SURVIVED (bats rc=0)
### e (old tests): SURVIVED (bats rc=0)
### f (old tests): SURVIVED (bats rc=0)
```

All six survive the old suite — reproducing the rejection exactly, and adding
(e)/(f) which RT1 also failed to catch.

**State 2 — HEAD's bats file over HEAD's scripts.** Same six mutants, each one
fails, and on the *new* assertion, not incidentally:

```
mutant a -> line 559  `[[ "$output" == *"model=x/y"* ]]' failed
mutant b -> line 574  `[[ "$output" == *"effort=high"* ]]' failed
mutant c -> line 637  `[[ "$output" == *"model=deepseek/deepseek-v4-flash"* ]]' failed
mutant d -> line 638  `[[ "$output" == *"effort=high"* ]]' failed
mutant e -> line 380  `[ "$status" -eq 3 ]' failed
mutant f -> line 395  `[ "$status" -eq 3 ]' failed
```

Red is genuine for the whole round. Tree clean after each revert
(`git status --porcelain` empty).

## Mutation table

Each mutation applied to the working tree by hand,
`nix develop -c bats tests/unit/80-seat-driver.bats` run, then reverted.
Thirteen mutations, **thirteen killed, zero survived**.

| # | Mutation | Result | Killed by |
| --- | --- | --- | --- |
| a | route clobbers `--model` (`if [ -n "$model" ]` → `if false`, `factory-task:85`) | KILLED | 15, at `model=x/y` (:559) |
| b | `effort=${OPENROUTER_REASONING_EFFORT:-$route_effort}` → `effort=$route_effort` (`factory-task:83`) | KILLED | 15, at `effort=high` (:574) |
| c | `factory-review` looks up role `implement` (`factory-review:69`) | KILLED | 16, at `model=…-flash` (:637) |
| d | `factory-review`'s seat launched without `OPENROUTER_REASONING_EFFORT` (`factory-review:162`) | KILLED | 16, at `effort=high` (:638) |
| e | unknown role word accepted (`implement \| review \| any)` → `… \| *)`) | KILLED | 12, at `status -eq 3` (:380) |
| f | `model = ""` accepted (the `'' \|` alternate removed) | KILLED | 12, at `status -eq 3` (:395) |
| M1 | specificity ties go to the **last** row (`-gt` → `-ge`) | KILLED | 11 |
| M2 | `any` treated as a literal for `kind` | KILLED | 11 **and 16** |
| M3 | the no-default-row check disabled (`-eq 1` → `-ge 0`) | KILLED | 12 |
| M4 | effort value validation dropped | KILLED | 12 |
| M7 | `factory-task`'s seat launched without the effort in its env | KILLED | 15 |
| M8 | `route:` says `explicit` for a routed pick | KILLED | 15 |
| M9 | `effort:` line dropped from the `.result` | KILLED | 15 |

Why (c) and (d) are not vacuous: the `factory-review` test's fixture table
gives `review/any/any` → `flash`/`high` while `implement/any/any` → `pro`/`off`,
so the two roles are distinguishable on the wire, and the fake
`dsh-openrouter` records both `$2` (the `--model` argument) and
`$OPENROUTER_REASONING_EFFORT`. Note M2 now also trips test 16, i.e. the new
review test independently pins the `any` match.

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
$ factory_route implement docs L docs/ledger/routing.toml
deepseek/deepseek-v4-flash off
$ factory_route_check docs/ledger/routing.toml; echo rc=$?
rc=0
$ factory_task_kind_size docs/superpowers/plans/2026-09-05-session-context.md G7
docs S
```

Every value from RT1's gate is unchanged and exact.

The two code fixes, probed directly:

```
$ factory_route any any any <table with model = "">
factory_route: …/em.toml: row 1: bad value ''
rc=3                                  # was rc=0 printing " off" (MINOR 2 closed)

$ factory_route any any any <table with effort = "max">
factory_route: …/be.toml: row 1: bad effort max
rc=3                                  # this message now reaches the caller's
                                      # stderr from factory-task/-review, since
                                      # the 2>/dev/null is gone (MINOR 4 closed)
```

`docs/ledger/routing.toml`: 1131 bytes, ends `…medium"\n` (`od -c` confirmed),
byte-identical to the plan's block.

## Findings

**All three MAJORs from `2026-09-05-opus-review-rt1-RT1.md` are closed.** MAJOR 1
by the new `--model x/y` case (`tests/unit/80-seat-driver.bats:549-561`, asserting
both the fake's `model=x/y` and `route: explicit` in the `.result`); MAJOR 2 by
the new `OPENROUTER_REASONING_EFFORT=high` case (:563-577, asserting the model
still comes from the route while the effort does not); MAJOR 3 by the new
`factory-review` test (:580-639). MINOR 1 by the unknown-`role` fixture (:360-381),
MINOR 2 by the `'' |` alternate in `factory-lib.sh:217`, MINOR 4 by dropping the
`2>/dev/null` at `factory-task:80` and `factory-review:69`, and Deviation 1 by
the trailing newline.

No regression: the seven mutants RT1 already killed are still dead, the four
`factory_route` probe values and `factory_task_kind_size` are unchanged, and
the local suite went 15/15 → 16/16.

**Carry-forward minors** (not in RT1b's scope; recorded, no action asked of this
task):

1. **The misleading comment on the skipped test is unchanged.**
   `tests/unit/80-seat-driver.bats:341-346` still says the committed table is
   reachable "from the lint check, which copies the whole tree". The `lint`
   check does not run bats. Cosmetic, but it will mislead whoever touches this
   next — fold it into RT2, which moves the pin into the flake anyway.
2. **`factory-review`'s own override paths are still untested.** The new test
   pins role, model-from-route and launch-env effort, but `--model` /
   `OPENROUTER_MODEL` against `factory-review` (`factory-review:73-77`) has no
   case. The code is a byte-for-byte copy of `factory-task`'s ladder, which is
   now pinned, so the risk is drift, not a present bug.
3. **The "table unusable → built-in default + warning" fallback is untested** in
   both scripts (`factory-task:93-95`, `factory-review:78-80`). Nothing asserts
   the warning is logged or that the fallback model is the Pro default.
4. RT1's MINOR 3 stands as recorded: the parser still rejects any table header
   other than `[[route]]` and still lets a duplicate key in a row silently win.
   Worth knowing before RT2 grows the schema.

Nothing else: no `sudo`/`systemctl`/`nixos-rebuild`, no `--no-verify`, no
`git push`, no write outside the workspace, no seat launched during the run,
and the lookup is still pure bash.

## Deviations

1. **The committed-table pin still skips under the `unit` check.** `ok 125
   factory_route_check validates the committed routing table # skip
   docs/ledger/routing.toml not copied into the unit-check sandbox`. Unchanged
   from RT1 and explicitly out of scope here — the plan's RT1b file list does
   not include `flake.nix`, and the implementer flagged it in FACTORY-NOTES as
   instructed by RT1b step 2. RT2 moves the check into the flake. The table is
   still validated on every local `nix develop -c bats` run.
2. The commit carries `tools/factory/seat/README.md` even though RT1b's file
   list does not name it. It is RT1's file, carried through the cherry-pick
   with a zero-byte diff (`git diff 4ef92e2 HEAD -- …/README.md` is empty), so
   this is the cherry-pick working as the plan's setup line instructed, not an
   extra touch.
