---
plan_defect: none
mutants_total: 15
mutants_killed: 11
mutants_outside_named: 6
---
# Opus gate — seat run sd1, task SD8 — APPROVED

## Summary

Fresh clone of `task/SD8` at `0cb135c` (base `55753ba`). Five files, one commit, subject
byte-identical to the section's. The contract is met item by item: `hook-guard --house-guard
PATH --house-shell SHELL` hands every bash/edit/write payload to `tools/orchestrator-guard.sh`
after its own rules allow, with `cwd` rebased from `workdir`, `CLAUDE_PROJECT_DIR` in the child
env, a 10 s timeout, and every fault arm failing closed; the wrapper composes both flags with
`jq --arg` beside `--routing-table` and passes its own `$BASH` store path; the `fullmatch`
regex grew the two flags; `tests/unit/93-house-guard.bats` (12 tests) proves parity on all 442
sweep rows against `bash "$GUARD"` directly, plus the `workdir` pair, the edit/write heading
rule, every fault arm and the negative control.

Red reproduced: with the base's two implementation files under the branch's tests, 9 of the 12
tests in `93-house-guard.bats` fail and the `70-dsh-openrouter.bats` `fullmatch` test fails.
All nine mutants the section names die. `unit` (606 tests), `host-core` and `lint` are green
under `--rebuild`; `repomap.py write` leaves no further diff; `tasks.py check` is silent.
Eleven MINORs, none gating; no MAJOR.

Measured evidence that the hand-off is load-bearing rather than decorative: over the 442 sweep
rows hook-guard's OWN rules deny 6 and allow 436; of those 436, the house guard denies **265**
and lets **171** through — so the seat still runs the driver's own recipe commands and gains
265 house denies it did not have before.

```
rows=442 own_deny=6 own_allow=436 house_only_deny=265
```

## Contract items

**Item 1 — `hook-guard … --house-guard PATH --house-shell SHELL`.**

| clause | verdict | evidence |
|---|---|---|
| both read from argv like `--routing-table`; either may be `--flag=value` | met | `pkgs/dsh-openrouter/hook-guard.py:256-278` mirrors `_routing_table_path`; measured by hand: `--house-guard=<G> --house-shell=<bash>` on `git reset --hard HEAD~1` → `DENY: house: git reset --hard is refused (history rules of the house)` |
| fires for `bash`, `edit`, `write` after hook-guard's own rules allowed | met | `:690` (`elif house_guard:` under the bash arm's `if reason: … `) and `:705` (same shape under the edit/write arm) |
| `cwd` set first, from `tool_input.workdir` when a non-empty string, a relative one joined to the payload's `cwd`, else the payload's own `cwd` | met | `:558-583`; `os.path.isabs` / `os.path.join` at `:568-574`, `ordered = {"cwd": cwd}` then `ordered.update(handoff)` at `:581-582` |
| `ensure_ascii=False` | met | `:583`; mutating it to `True` kills test 4 (see Mutants, M13) |
| `[SHELL, PATH]` with the payload on stdin | met | `:599-607` `subprocess.run([shell, guard_path], input=handoff, text=True, …)` |
| `env` = process environment plus `CLAUDE_PROJECT_DIR=<project_dir>` (the value `_edit_verdict` uses) | met (untested — MINOR-4) | `:596-597`; `project_dir` hoisted to `:674` and passed to `_edit_verdict` at `:702` |
| `timeout=10`, `capture_output=True` | met | `:555` `_HOUSE_TIMEOUT = 10`, `:604-605` |
| stdout non-empty → JSON → `permissionDecision == "deny"` → `_deny(tool, "house: " + reason, subject)` | met | `:613-628`; test 12 asserts the record's `reason` starts `house: ` and `subject` is `git push` |
| stdout empty and exit 0 → allow | met | `:613-614`; the negative rows of the parity loop (171 allow rows) |
| non-zero exit → fault deny | met | `:611-612`; test 8 |
| timeout → fault deny | met | `:608-609`; test 10 |
| unparsable stdout → fault deny | met | `:615-618`; test 9 |
| stdout JSON without that key → fault deny | met (untested — MINOR-2) | `:619-624` |
| `PATH` not a readable file → `house guard unreadable at <PATH>` | met in substance (MINOR-1) | `:593-594` tests `os.path.isfile`, not readability; an existing mode-000 guard falls to the exit-code arm — measured `DENY: house guard fault: exit code 126`, still fail-closed |
| any exception in this path → deny `house guard could not be run: <ExceptionName>` | met (untested arm) | `:691-696` / `:706-711`; measured by hand: `--house-shell /nonexistent-shell` → `DENY: house guard could not be run: FileNotFoundError`; `--house-guard` with no `--house-shell` → `DENY: house guard could not be run: TypeError` |
| `main()` still returns 0 on every path | met | every test asserts `[ "$status" -eq 0 ]`, including the fault arms |
| without `--house-guard` nothing changes | met | `tests/unit/93-house-guard.bats:232-236` (test 11) |

**Item 2 — the wrapper.** Met. `pkgs/dsh-openrouter/dsh-openrouter.sh:695-696`:

```
house_guard=${FACTORY_HOUSE_GUARD:-$HOME/nixos-agent-env/tools/orchestrator-guard.sh}
house_shell=$BASH
```

and `:704-706` composes exactly the section's jq expression. Rendered `hooks.json` (measured,
`dsh-openrouter --dump-config`, all three matcher groups identical):

```
exec '/nix/store/5xd060qi…-hook-guard/bin/hook-guard' --routing-table '/home/dalhaka/nixos-agent-env/docs/ledger/routing.toml' --house-guard '/home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh' --house-shell '/nix/store/9ipfvwnq…-bash-5.3p15/bin/bash'
```

`$BASH` is the wrapper's own store bash, as the section requires. The `fullmatch` grew both
flags (`tests/unit/70-dsh-openrouter.bats:1211-1214`); the `--dump-config` substring assertion
at `:1182` is untouched; the file's test count is unchanged at 123 (Assumption 24 item 2).

**Item 3 — `tests/unit/93-house-guard.bats`.** Met. `GUARD` `:15`, `SWEEP` `:16`, `PROJECT`
with the `A1`/`B2` plan `:19-34`, `hook-guard` from PATH. Parity loop `:79-122`: both payload
shapes, `hook-guard … --house-guard "$GUARD" --house-shell "$(command -v bash)"` vs
`bash "$GUARD"`, a stderr-record assertion on every deny, and the row count pinned to the
sweep header (`data_rows -eq n`, 442). The `workdir` pair `:126-143`; the edit/write heading
rule `:147-179`; the four fault arms `:183-228`; the negative control `:232-236`; the stderr
record `:238-247`. One deviation from the section's wording: the routing table is the committed
`docs/ledger/routing.toml` (`:17`) rather than "a routing table fixture" — equivalent here (the
`unit` sandbox copies `docs/ledger`) and it is the table the seat actually runs with.

## Red before green

Base implementation (`git checkout 55753ba -- pkgs/dsh-openrouter/hook-guard.py
pkgs/dsh-openrouter/dsh-openrouter.sh`) against the branch's tests, in a scratch copy:

```
$ nix develop -c bats tests/unit/93-house-guard.bats
not ok 1 parity: hook-guard with the house guard matches the guard on every sweep row, one stderr record per deny
#   `return 1' failed
# row 1 diverges: house=deny hook=allow (cmd: rm -rf .claude/*)
not ok 2 a bash command whose workdir is a plans subdirectory is denied by the house guard
ok 3 a bash command whose workdir is an absolute /tmp path is allowed
not ok 4 an edit removing a typed task heading is denied by the house guard
ok 5 an edit of body text is allowed
not ok 6 a write dropping a typed task heading is denied by the house guard
not ok 7 an unreadable house guard denies every bash payload fail-closed
not ok 8 a house guard exiting non-zero is a fault deny
not ok 9 a house guard printing garbage is a fault deny
not ok 10 a house guard that hangs is a timeout fault within 11 seconds
ok 11 without --house-guard a bare git push is allowed (today's behaviour)
not ok 12 a house deny writes one stderr record naming the house reason and the command
```

Nine of twelve red. Tests 3, 5 and 11 are the allow-side controls and are green by design at
both ends — each is killed by a mutant of its own (M2a, M3, M7 below), so none is vacuous.

The wrapper's assertion, same scratch copy:

```
$ nix develop -c bats -f "hooks.json's hook commands carry no denial log path" tests/unit/70-dsh-openrouter.bats
not ok 1 hooks.json's hook commands carry no denial log path -- just the guard, its routing table and the house guard
# (in test file tests/unit/70-dsh-openrouter.bats, line 1217)
#   `[ "$status" -eq 0 ]' failed
```

Restored to `HEAD`, all twelve pass (`nix develop -c bats tests/unit/93-house-guard.bats`,
1 m 20 s wall) and the `fullmatch` test passes.

## Mutants

Nine named, all killed. Six more tried outside the named set; two killed, four survive (each a
MINOR below, none a behaviour the code gets wrong).

| # | mutant | named? | test run | result |
|---|---|---|---|---|
| M1 | skip the house call for `bash` (`elif house_guard:` → `elif False:`, `:690`) | yes | parity | KILLED — `row 1 diverges: house=deny hook=allow (cmd: rm -rf .claude/*)` |
| M2a | do not rebase `cwd` from `workdir` (`:567` guard → `if False:`) | yes | workdir pair | KILLED — test 2 `denied "$output"' failed`; test 3 still green (the discriminating pair) |
| M3 | hand only `bash` to the house guard (`:705` → `elif False:`) | yes | heading rules | KILLED — tests 4 and 6 both `denied "$output"' failed`; the four fault arms stay green |
| M4 | non-zero exit → allow (`:611-612` → `return None`) | yes | fault arms | KILLED — test 8 `denied "$output"' failed` |
| M5 | drop `timeout=_HOUSE_TIMEOUT` (`:604`) | yes | hangs | KILLED — test 10 red, wall 22.9 s (the stub's full 20 s slept through) |
| M6 | missing guard path → allow (`:593-594` → `return None`) | yes | unreadable | KILLED — test 7 `denied "$output"' failed` |
| M7 | call the house guard even without the flag (`:278` → `return guard_path or "/nonexistent", shell`) | yes | negative control | KILLED — test 11 `[ -z "$output" ]' failed` |
| M8 | wrapper omits `--house-shell` (`dsh-openrouter.sh:706`) | yes | 70 `fullmatch` | KILLED — `[ "$status" -eq 0 ]' failed` |
| M9 | print nothing on a house deny (`_deny`, `:546`) | yes | parity + record | KILLED — test 1 `return 1' failed` and test 12 red |
| M2b | serialise `cwd` LAST instead of first (`:581-582`) | no | full file | **SURVIVES** — MINOR-5 |
| M10 | stdout JSON without `hookSpecificOutput` → allow (`:620-621` → `return None`) | no | full file | **SURVIVES** — MINOR-2 |
| M11 | drop the `--house-guard=VALUE` branch (`:271-272`) | no | full file | **SURVIVES** — MINOR-3 |
| M12 | drop `env["CLAUDE_PROJECT_DIR"] = project_dir` (`:597`) | no | full file | **SURVIVES** — MINOR-4 |
| M13 | `ensure_ascii=True` (`:583`) | no | full file | KILLED — test 4 red (the heading's em-dash becomes `—`, the guard's `json_unescape` does not decode it, the edit no longer removes the heading) |
| M14 | `_HOUSE_TIMEOUT = 30` (`:555`) | no | full file | KILLED — test 10 red |

`mutants_total: 15`, `mutants_killed: 11`, `mutants_outside_named: 6`.

Note on M2: the section's second named mutant reads "pass the payload without `cwd` first".
The behavioural reading (M2a — do not derive `cwd` from `workdir`) dies on the section's own
discriminating pair. The literal ordering reading (M2b) survives, because the guard's
`json_string` (`tools/orchestrator-guard.sh:468-471`) is a greedy
`sed 's/.*"cwd"[[:space:]]*:[[:space:]]*"…' ` that takes the LAST occurrence, not the first,
and the handoff carries exactly one `cwd` either way. The code does what the contract says;
the contract's stated *reason* is wrong. MINOR-5, not gating.

## Checks

All in the fresh clone, all `--rebuild`.

| check | command | result | wall |
|---|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass**, 606 tests, `ok 502 parity: …` | 191 s |
| host-core | `nix build .#checks.x86_64-linux.host-core -L --no-link --rebuild` | **pass** | 11 s |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass** | 7 s |
| ruff check | `nix develop -c ruff check pkgs/dsh-openrouter` | `All checks passed!` | — |
| ruff format | `nix develop -c ruff format --check pkgs/dsh-openrouter` | `2 files already formatted` | — |
| MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0, no further diff | — |
| task graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 | — |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1, board queue block regenerated — MINOR-9 | — |

The parity loop is 884 guard invocations; the whole `unit` derivation rebuilt in 191 s, well
under the section's 120 s-per-loop split threshold for the loop itself (80 s measured
standalone), so no split is owed.

`githooks/pre-commit` at the **base** commit `55753ba`, same clone tooling: exit 0, tree clean.
On the branch tip it regenerates the board's queue block (`SD8` drops out of
`Queued …` once its own commit is in the log — `tasks.py brief` on the branch counts 157 landed
and `Next wave — nixos-agent-env: CR4 SD4`). That is the artifact the Global Constraints name
("it may regenerate the board's queue block once"), it is not attributable to the change's
content, and the house pattern is that task commits leave `docs/OPERATIONS.md` alone (SB6c's
`597262d` and VC1's `f08e963` do not touch it). MINOR, not a red check.

## Touches and commit

Diff against `55753ba`:

```
 docs/MAP.md                           |   2 +-
 pkgs/dsh-openrouter/dsh-openrouter.sh |  15 +-
 pkgs/dsh-openrouter/hook-guard.py     | 134 +++++++++++++++++-
 tests/unit/70-dsh-openrouter.bats     |  17 ++-
 tests/unit/93-house-guard.bats        | 248 ++++++++++++++++++++++++++++++++++
 5 files changed, 407 insertions(+), 9 deletions(-)
```

Four of five are the section's `touches` exactly. `docs/MAP.md` is the fifth: one line,
`tests/unit — 20 files` → `21 files`, required by `flake.nix:1067` (`repomap.py --root . check`
inside the `lint` check) and exempt by rule in the driver
(`tools/factory/seat/factory-lib.sh:881,888`). It is explained in the `.result`'s
`FACTORY-NOTES`, not in the commit body — MINOR-8. The plan file is untouched; no board commit.

One commit, `0cb135c`. Subject byte-identical to the section's `**commit subject:**` (257
chars, compared as bytes — `IDENTICAL`). Body states the why in four sentences; the two
trailers follow a blank line in the WORKSPACE RULES order (`Generated-By:` then
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`). The body does not paste the red
and the green the section's Step 1 asks for — MINOR-7.

The driver's record (`~/factory/runs/sd1/SD8.result`) confirms the orchestrator's summary:
`FACTORY-RESULT status=done`, `FACTORY-COMMITS 1`,
`checks_verified: unit=pass host-core=pass lint=pass`,
`checks_verified_src: unit=run host-core=run lint=run`, `touches_extra: 0`,
`touches_disclosed: 0`, `error_class: none`, `wall_s: 2531`, `verify_s: 225`.

## Findings

No MAJOR.

**MINOR-1** — `pkgs/dsh-openrouter/hook-guard.py:593` — the "not a readable file" arm tests
`os.path.isfile`, not readability. An existing but unreadable guard reaches the subprocess and
falls to the exit-code arm instead of the named message. Measured on a mode-000 file:
`DENY: house guard fault: exit code 126`. Fail-closed either way, so behaviour is safe; the
message differs from the contract's word.

**MINOR-2** — `pkgs/dsh-openrouter/hook-guard.py:619-624` — the "stdout JSON without
`hookSpecificOutput`" arm is a stated contract with no test. Mutant M10 (`return None` there)
leaves all twelve tests green. A stub printing `{"ok":1}` would be a good thirteenth case.

**MINOR-3** — `pkgs/dsh-openrouter/hook-guard.py:271-272,275-276` — the `--house-guard=VALUE` /
`--house-shell=VALUE` forms are a stated contract with no test. Mutant M11 leaves all twelve
green. Verified working by hand (`--house-guard=<G> --house-shell=<bash>` denies
`git reset --hard HEAD~1` with the house reason), so this is coverage, not a defect.

**MINOR-4** — `pkgs/dsh-openrouter/hook-guard.py:596-597` — `env["CLAUDE_PROJECT_DIR"] =
project_dir` is a stated contract with no discriminating test: every test already exports the
same value into the process environment, so mutant M12 (delete the line) leaves all twelve
green. A case with `CLAUDE_PROJECT_DIR` unset in the parent would discriminate.

**MINOR-5** — `pkgs/dsh-openrouter/hook-guard.py:581-582` vs
`tools/orchestrator-guard.sh:468-471` — the contract's rationale for putting `cwd` first
("`json_string`'s first-match") is wrong: that `sed` is greedy and takes the last occurrence.
The handoff carries exactly one top-level `cwd`, so the ordering is unobservable and mutant
M2b survives. Code correct, plan text wrong; nothing owed here beyond the note.

**MINOR-6** — `tests/unit/93-house-guard.bats:103` — the parity reference runs
`bash "$GUARD" … 2>/dev/null`. `tests/unit/91-orchestrator-guard.bats` uses no `2>/dev/null`
anywhere (`grep -c` → 0). A crash on the reference side cannot pass silently (hook-guard's own
call would see the non-zero exit and diverge), but the suppression is off the house style.

**MINOR-7** — commit `0cb135c` body — the section's Step 1 says "Paste both" (the red of
`93-house-guard.bats` and of the `70` `fullmatch` test) and Step 3 names the green; the body
states the why but pastes neither. The reds reproduce exactly as this review shows, so nothing
is in doubt.

**MINOR-8** — `docs/MAP.md:89` — outside the section's `touches`; explained in the `.result`'s
`FACTORY-NOTES` rather than in the commit body. Mandatory (the `lint` check runs
`repomap.py check`) and exempt by rule in `tools/factory/seat/factory-lib.sh:888`. Recorded,
not owed.

**MINOR-9** — `githooks/pre-commit` — exits 1 on the branch tip, regenerating the queue block
of `docs/OPERATIONS.md`; exit 0 at the base. Cause: the branch's own commit makes `SD8` landed
in the derived graph. Systemic to every task branch of this plan, anticipated by the Global
Constraints, and the named `lint` acceptance check is green. Process, not the change.

**MINOR-10** — `nixosModules/seatLane.nix:147-163` — the unit pins `FACTORY_ROUTING_TABLE`
explicitly but nothing pins `FACTORY_HOUSE_GUARD`; the new default resolves through `$HOME`.
It resolves correctly today (`serviceConfig.User = cfg.operatorUser`, so systemd sets
`HOME=/home/dalhaka`), and `seatLane.nix` is outside SD8's `touches`, so this is a note for SD5
rather than a defect: pinning the house guard beside the routing table would remove the
dependence on `$HOME`.

**MINOR-11** — `tools/orchestrator-guard.sh:159-162` — the house guard is read from the mutable
checkout (contract item 2's default) and its `PROTECTED_PATHS` do not include itself, so an
agent with Write access to the tree can neuter the house rules it is now subject to. The tree
path is the plan's own choice, and the guard predates this task; recorded for the plan's
attention, not against the implementer.

## Verdict

**APPROVED.** Every numbered contract item is met, taken literally; the red is real and
reproduced for both test files; all nine named mutants die on the tests the section names; the
three acceptance checks are green under `--rebuild`; the diff stays inside `touches` plus the
by-rule `docs/MAP.md`; one commit, byte-identical subject, both trailers. The eleven MINORs are
coverage gaps on already-correct arms, one wrong sentence in the plan's rationale, and two
process notes — none of them gating.

`plan_defect: none`.
