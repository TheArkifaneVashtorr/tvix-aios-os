---
reviewer: opus
majors: null
minors: null
mutants_total: 14
mutants_killed: 11
---
# Opus gate — seat run sc1, task G6 — APPROVED

Workspace `/home/dalhaka/factory/ws/sc1/G6`, branch `task/G6`, head `973024e22e7d`,
base `e5e0061`. Reviewed from a throwaway clone; the workspace was not touched.

## Summary

One commit on base. `tools/session-start.sh` is byte-for-byte the script the plan
section specifies, executable, shellcheck-clean, `set -u` only, never invokes
`nix`. `.claude/settings.json` carries the `startup|clear|resume|compact` matcher,
the `$CLAUDE_PROJECT_DIR` command and a 10 s timeout. The bats file is the
section's, with the last test's `[ a ] && [ b ]` split into two statements (a
strict improvement) and the fake `evidence` binary given the sandbox bash's
absolute path as its shebang. Runbook covers every item the section lists. All
five acceptance commands pass, red-before-green is real (5/5 fail with the script
removed), and 11 of 14 mutations are killed — including all six the gate demanded.

Deviation: the commit also edits `flake.nix` (a fifth file, outside `touches`) to
copy the hook into the `unit` check's sandbox. Necessary, minimal, and verified to
be what makes the new tests actually run there.

## Checks

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass |
| — 90-session-start.bats ran in the sandbox | yes: build log lines `ok 134`–`ok 138`, all five test names |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass (84 formatted, 0 changed; statix/deadnix/ruff clean) |
| `nix develop -c githooks/pre-commit` | pass |
| `nix develop -c shellcheck tools/session-start.sh` | exit 0, no output |
| `nix develop -c bats tests/unit/90-session-start.bats` | 5/5 ok |

Commit hygiene: subject byte-identical to the section's `commit subject`;
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present (plus a
`Generated-By:` line, allowed). `tools/session-start.sh` mode `100755`.
Hard-rules scan of the diff: no `sudo`, `nixos-rebuild`, `systemctl`, mount or
teardown, and no `2>/dev/null` anywhere (the script uses `2>&1` throughout).
Nothing written outside the repo.

Behaviour verified against the section and spec §1:

- order — board block header, the `## START HERE` block only (the `## Log`
  section is excluded; test 1 asserts `output != *"old"*`), then
  `evidence bundle --markdown`, then `evidence tasks --root <repo> brief`, then
  `Where everything is: docs/runbooks/session.md`;
- guards — missing/failing `evidence` yields `unavailable: …` and the board still
  prints; every fallible command carries a `||`;
- `SESSION_START_EVIDENCE` honoured — confirmed directly with a working alternate
  binary, which received `bundle --markdown` and `tasks --root . brief` in order;
- silent under `FACTORY_RUN`; silent in a linked worktree
  (`git rev-parse --git-common-dir` ≠ `.git` / `$repo/.git`); trailing-slash and
  non-git-directory paths both still print, correctly;
- cap `SESSION_START_CAP` default 6000 with the `…truncated` line; exit 0 always;
- wall time 0.156 s against the live repo, well inside the spec's 2 s target.

The FACTORY-NOTES "real-bash-shebang trick" is the fake `evidence` binary carrying
`#!<abs path to bash>` instead of `#!/usr/bin/env bash`, because the `unit` check's
sandbox has no `/usr/bin/env`. Precedent is `tests/unit/80-seat-driver.bats:18`
(and its lines 114, 143). It does not weaken the test: the fake is still found on
`PATH` by `command -v` and behaves identically, and mutations M3, M6 and M9 all die
through it, proving it genuinely drives the assertions.

## Red before green

`tools/session-start.sh` moved aside, `nix develop -c bats
tests/unit/90-session-start.bats`:

```
1..5
not ok 1 prints START HERE, bundle, brief and the runbook pointer, in order
not ok 2 without evidence on PATH the board still prints and each missing part says unavailable
not ok 3 silent when FACTORY_RUN is set
not ok 4 silent in a linked worktree
not ok 5 output over the cap ends with a truncation line
```

Every test fails, including the two silence tests (`status` is non-zero without
the script). Restored; `git status --porcelain` clean afterwards.

## Mutation table

Fourteen mutations, each applied to `tools/session-start.sh`, bats run, then
reverted (`git status --porcelain` clean at the end).

| # | mutation | outcome | killed by |
|---|---|---|---|
| M1 | remove the `FACTORY_RUN` early exit | **killed** | T3 `silent when FACTORY_RUN is set` |
| M2 | remove the linked-worktree check (`--git-common-dir` + `case`) | **killed** | T4 `silent in a linked worktree` |
| M3 | awk prints the whole file (log included) | **killed** | T1 `prints START HERE, bundle, brief and the runbook pointer, in order` |
| M4 | drop the truncation branch entirely | **killed** | T5 `output over the cap ends with a truncation line` |
| M5 | drop the final `unavailable: evidence not on PATH` fallback | **killed** | T2 `without evidence on PATH the board still prints …` |
| M6 | reorder: brief printed before bundle | **killed** | T1 (ordering assertion `b < c`) |
| M7 | exit 0 when `evidence` is missing (board suppressed) | **killed** | T2 |
| M8 | truncation marker text changed from `…truncated at %s bytes` to `cut at %s` | **killed** | T5 |
| M9 | drop the runbook pointer line | **killed** | T1 |
| M10 | `set -u` → `set -eu` | survived | — (see Findings 5: equivalent mutant) |
| M11 | `\|\| echo "unavailable: evidence bundle failed"` → `\|\| true` | survived | — (Finding 4) |
| M12 | `\|\| echo "unavailable: evidence tasks failed"` → `\|\| true` | survived | — (Finding 4) |
| M13 | `\|\| echo "unavailable: docs/OPERATIONS.md not readable"` → `\|\| true` | survived | — (Finding 4) |
| M14 | final `exit 0` → `exit 3` | **killed** | T1, T2, T5 |

All six mutations the gate named (M1–M6) are killed. Note M6 had to be applied
with an exact-text replacement; a first regex attempt silently failed to match and
would have reported a false survivor — the corrected run kills it.

## Real run

From the clone, read-only, against the live repo:
`bash tools/session-start.sh /home/dalhaka/nixos-agent-env`.

- exit 0, wall time 0.156 s, **6115 bytes** printed.
- Prints the header line `## Board — START HERE (docs/OPERATIONS.md)`, then the
  whole live `## START HERE (2026-09-05, after wave 3 of the evidence plan)`
  block, then the start of `evidence bundle --markdown` (the coverage table),
  then the final line `…truncated at 6000 bytes (SESSION_START_CAP)`.
- Truncation fires, mid-bundle. Measured parts: START HERE block **5189 B**,
  `evidence bundle --markdown` **6032 B**, cap **6000**. So today the hook
  delivers spec §1 item 1 and roughly 800 bytes of item 2; **items 3 (the task
  brief) and 4 (the runbook pointer) never appear.**
- Separately confirmed that the live `evidence` (gen 41) has no `tasks`
  subcommand yet — `evidence tasks --root … brief` prints an argparse usage error
  and exits non-zero, which the script would render as that error plus
  `unavailable: evidence tasks failed`. Invisible today behind the truncation;
  G5 supplies the subcommand.

This is a spec question for the orchestrator, not a defect: the section's order
and guards are honoured exactly, and the spec's own budget table already plans for
START HERE to fall from 14 KB to ~3 KB (G7/G8). Until G8 lands, the hook is
board-only in practice. If the orchestrator wants the brief sooner, the cheapest
options are a per-part cap (board 2500, bundle 2000, brief 1000) or moving the
runbook pointer above the bundle so item 4 always survives.

First 15 lines of the real run:

```
## Board — START HERE (docs/OPERATIONS.md)
## START HERE (2026-09-05, after wave 3 of the evidence plan)

**SWITCH #16 DONE (2026-09-05 12:40 CDT): generation 41 = `b5c35abc6070` LIVE**
(the operator switched at the board commit, so live equals HEAD exactly). Verified
read-only afterwards: all nine tiles green, each printing its verdict word and
`since 12:41 CDT`; the verdict history stream `/var/lib/evidence/helm-status.jsonl`
holds its first row; `evidence bundle --markdown` reports Live = HEAD and the
Helm block; the full flake check recorded at `c5af84e` covers HEAD. What went
live: the wave-3 collector (verdict words, since-when, `--print` writes no
history, bad timestamps render), R3rb (backup-parity and timers read the unit's
own last result), `evidence bundle`, the seat scripts dispatching from their own
directory. ROLLBACK: generation 40. This closes the evidence plan.

**Queued, in order.** 0) backup of the audit records (operator decision
```

## Findings

1. **MINOR — `flake.nix` is a fifth touched file.** The commit adds three lines to
   the `unit` check's `runCommand` (`cp ${self}/tools/session-start.sh
   tools/session-start.sh`) with a comment matching the two adjacent precedents.
   It is necessary — the sandbox copies `tests/` only, so
   `$BATS_TEST_DIRNAME/../../tools/session-start.sh` would not resolve — and I
   confirmed it is load-bearing by finding all five test names in the `unit`
   build log. The section's `touches` list should record it; no code change asked.

2. **MINOR — wrong path in the runbook.** `docs/runbooks/session.md` names
   `docs/superpowers/reviews` as the reviews source. The real path is
   `docs/reviews` (as in G1's `read_reviews(repo_path)` and this file). One-word
   fix; roll into G7 or a later docs pass.

3. **MINOR — the cap is characters, not bytes.** `${out:0:$cap}` slices
   characters, while the emitted line says `…truncated at 6000 bytes`. The live
   run printed 6115 bytes under a 6000 cap. Harmless in practice (the block is
   mostly ASCII, and bash never splits a multibyte character), but the wording
   overstates the guarantee.

4. **MINOR — three guards survive mutation (M11, M12, M13).** The
   present-but-failing `evidence` and the unreadable-board paths are not exercised
   by any test; only the *missing-binary* guard the spec names is (killed by M5
   and M7). I did not raise this to MAJOR because the impact is diagnostic only:
   with `2>&1` the failing command's own error still reaches stdout, the hook
   still exits 0, and the board still prints — the invariants spec §1 states
   ("never fails the session", "the board still prints") survive all three
   mutants. The section's verbatim bats script does not test them either, so the
   implementer followed the contract. Suggested for a later round: one test with a
   fake `evidence` that exits 1, asserting both `unavailable:` lines and the board.

5. **Not a defect — M10 (`set -eu`) is an equivalent mutant.** Every fallible
   command in the script already carries a `||`, and bash does not exit on a
   failing left-hand side of an `&&` list, so `-e` changes nothing observable. The
   code itself complies with the section's "`set -u` only".

6. **Spec question, not a defect — the cap swallows the brief today.** See Real
   run. Stated there rather than repeated here.

No MAJORs. Nothing blocks integration.

## Deviations

- `flake.nix` touched beyond the section's four files (Finding 1) — accepted.
- The last bats test's `[ "$a" -lt "$b" ] && [ "$b" -lt "$c" ]` was split into two
  separate statements. This is a deliberate and correct improvement (the `] && [`
  form is the pattern the board already lists as a lint target); assertions are
  unchanged in strength.
- The fake `evidence` binary's shebang is built from `command -v bash` rather than
  the section's literal `#!/usr/bin/env bash`, with an explanatory comment.
  Required by the `unit` sandbox; matches `80-seat-driver.bats`. Does not weaken
  the test (M3/M6/M9 die through the fake).
- No other deviation. `.claude/settings.json` matches the section's JSON exactly;
  the live repo has no untracked `.claude/settings.json` to collide with.
