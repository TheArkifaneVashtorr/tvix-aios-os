---
plan_defect: none
mutants_total: 7
mutants_killed: 7
mutants_outside_named: 0
model: sonnet
---
# Opus gate — seat run ol2, task OL3 — APPROVED

## Summary

The runbook is exactly what plan section OL3 (`docs/superpowers/plans/2026-09-08-openai-lab.md:355-397`)
specifies: three byte-exact `## ` headings, three fenced commands matching the Interfaces text
verbatim, and a `checks.unit` gate (heading count, three `grep -Fxq`, then `bats
tests/runbook.bats`) that fails on every named mutant and passes clean. I ran every command the
runbook documents against this host's real paths (`~/nixos-agent-env`, `~/factory/runs`,
`tools/factory/seat/factory-wave`) and all four work as written. The orchestrator's
`flake-check=pass`/`not-run:absent` question is the same naming mismatch established at OL1's
gate: I re-ran `nix flake check -L` myself in the clone and it printed `all checks passed!`
(pasted below); the driver's own `error_class=checks-unverifiable` is a field-name gap, not a
false claim, and it does not touch OL3's acceptance (`unit, lint` only — `plan:395`). No MAJORs.
APPROVED.

## Contract items

Plan Interfaces (`plan:364-374`), each checked against `docs/runbook.md`, `flake.nix`,
`tests/runbook.bats` at `fc578cd`:

1. **Exactly three `## ` headings, byte-exact.** `grep -n '^## ' docs/runbook.md` →
   `3:## Bumping the pin`, `14:## Dispatching a task`, `29:## Where the gate record lives`. Met.
2. **`## Bumping the pin` fence: `$ nix flake lock --update-input nixos-agent-env` then
   `$ nix flake check -L`.** `docs/runbook.md:9-12`:
   ```
   $ nix flake lock --update-input nixos-agent-env
   $ nix flake check -L
   ```
   Byte-identical to `plan:368`. Met.
3. **`## Dispatching a task` states `factory-dispatch` cannot be used here, then the exact
   `FACTORY_SEAT=codex …` fence.** `docs/runbook.md:16-17`: "`factory-dispatch` cannot be used
   here: it requires `<repo-path>/docs/ledger/repos.toml`, which this lab does not have." —
   matches Assumption 9. Fence at `docs/runbook.md:22-24` is byte-identical to `plan:369`. Met.
4. **`## Where the gate record lives` states reviews are committed in `~/nixos-agent-env`'s
   `docs/reviews/`, never the lab, then the exact `git -C …` fence.** `docs/runbook.md:31-32`:
   "Every gate review is committed in `~/nixos-agent-env`'s `docs/reviews/`, never in the lab." —
   matches `plan:370`. Fence at `docs/runbook.md:34-36` byte-identical. Met.
5. **`flake.nix`'s `checks.unit` gains, after pytest, the count check, three `grep -Fxq`, then
   `bats tests/runbook.bats`.** `flake.nix:38-43` (diff), in that exact order, matching `plan:372`
   verbatim. Met.
6. **`tests/runbook.bats` extracts every `$ `-prefixed line via the named `awk` and asserts a
   documented verb.** `tests/runbook.bats:2` uses the identical `awk` expression from `plan:374`;
   the `case` block enumerates the four commands. Met.

All six items met, no gaps.

## Red before green

Base `999de984a86d6f2ea216093d62e669aafed67eab` has no `docs/runbook.md`, no `tests/runbook.bats`,
and `flake.nix`'s `checks` attrset has no `unit` member at all (only `lint`, `lab-vm`):

```
$ git checkout 999de984… -- flake.nix && nix build .#checks.x86_64-linux.unit -L --no-link
error: flake … does not provide attribute … 'checks.x86_64-linux.unit' …
```

This is the "initial missing-runbook build also failed" the commit body claims. Restoring
`flake.nix` to HEAD and building green:

```
$ nix build .#checks.x86_64-linux.unit -L --no-link --rebuild
openai-lab-unit> 1..1
openai-lab-unit> ok 1 every fenced command starts with a documented verb
```

Green confirmed (also `lint`, see Checks below).

## Mutants

All seven mutants named across R1–R3 applied to a scratch copy of `docs/runbook.md`, one at a
time, each rebuilt with `nix build .#checks.x86_64-linux.unit -L --no-link`, then reverted
(`diff` against the pre-mutation file confirmed clean restoration each time; final tree
`git status --short` empty).

| row | mutant | result |
|---|---|---|
| R1 | insert a stray fourth `## ` heading | `error: … builder failed with exit code 1` (count check trips) — red |
| R1 | delete `## Bumping the pin` | same — count drops to 2 — red |
| R2 | reword `## Bumping the pin` → `## Bumping the Pin` (count stays 3) | red (its own `grep -Fxq` fails) |
| R2 | delete `## Dispatching a task` | red |
| R2 | delete `## Where the gate record lives` | red |
| R3 | drop `-L` from `nix flake check -L` (verb list untouched) | Bats: `not ok 1 …` / `# Undocumented command: nix flake check` — red |
| R3 | replace the gate-record command with `$ echo undocumented` (count unchanged) | Bats: `not ok 1 …` / `# Undocumented command: echo undocumented` — red |

`mutants_total: 7`, `mutants_killed: 7`, `mutants_outside_named: 0` (I tried no mutant the section
did not name).

## Checks

- `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` → `ok 1 every fenced command
  starts with a documented verb`. Pass.
- `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` → `formatted 2 files (0 changed)`,
  `All checks passed!` (ruff prints "No Python files found" — expected, no `.py` touched). Pass.
- `nix flake check -L` (full) → `all checks passed!`, confirming `unit`, `lint`, `lab-vm`,
  `formatter` all evaluate and build clean. This directly reproduces the seat's own claim and
  settles the orchestrator's question: **the same explanation as OL1's gate holds.** The command
  is real and passes; `~/factory/runs/ol2/OL3.result` shows `checks_verified_src: unit=run
  lint=run flake-check=- lab-vm=run` — the driver's automated verifier has no `flake-check`
  flake attribute to build (there isn't one; it's a Step-3 *command*, not a `checks.<name>`), so
  it records `not-run:absent` for a field that was never a buildable attribute to begin with. Not
  a false claim, a field-name gap — exactly OL1's MINOR-1 pattern, reproduced independently here
  rather than assumed.
- `githooks/pre-commit`, `pkgs/evidence/repomap.py`, `pkgs/evidence/tasks.py check`: none of
  these exist in `~/flakes/openai-lab` — decisions D6 (no pre-commit hook ships with OL1) and D2
  (acceptance names are the lab's own `checks.${system}` names, never a `docs/MAP.md` name; no
  MAP.md tooling exists for this repo) both apply, exactly as OL1's approved gate already found.
  Not run, not applicable, not a gap.
- No `.py` file touched — `ruff check`/`ruff format --check` over touched packages: N/A.

## Touches and commit

`git diff 999de984a86d6f2ea216093d62e669aafed67eab..HEAD --stat`:
```
 docs/runbook.md    | 36 ++++++++++++++++++++++++++++++++++++
 flake.nix          | 20 ++++++++++++++++++++
 tests/runbook.bats | 15 +++++++++++++++
 3 files changed, 71 insertions(+)
```
Every file is inside `touches: docs/runbook.md, tests/runbook.bats, flake.nix` (`plan:394`). No
`docs/MAP.md` (D2, as above). No file outside touches. No deviation to record.

- Exactly one commit: `git log --oneline 999de984…..HEAD | wc -l` → `1`.
- Subject byte-identical to `plan:396`: `lab: the runbook — bumping the pin, dispatching a task
  under FACTORY_SEAT=codex, where the gate record lives, checks.unit gates it by heading and
  verb (test: unit, lint)` — confirmed by direct string comparison. SUBJECT BYTE-IDENTICAL.
- Body states the why (documents pin refresh, manual dispatch, gate-record location; gates three
  headings and fence commands only), names every R1–R3 mutant and its red result, and states the
  green (`unit and lint pass. nix flake check -L reports all checks passed.`) — the same
  narrative style OL1's approved gate accepted (that review's own words: "pastes the … red
  observations and the green commands").
- Trailers, `cat -A` on the last two non-blank lines, one blank line above them:
  `Generated-By: codex-cli 0.153.4 / gpt-6-astra (codex exec, factory run ol2)$` then
  `Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>$` — matches Global Constraints
  (`plan:39`); `<ver>` = `FACTORY_SEAT_VERSION` = `0.153.4`.
- No board commit; plan file untouched (it does not live in this repo at all — it lives in
  `~/nixos-agent-env`, confirmed absent from this diff's file list).

## Findings

No MAJORs.

**MINOR-1 — the `## Bumping the pin` fence's first command is a deprecated Nix alias.**
`docs/runbook.md:10`: `$ nix flake lock --update-input nixos-agent-env`. Running it here:
`warning: '--update-input' is a deprecated alias for 'flake update' and will be removed in a
future version.` (exit 0, `flake.lock` unchanged — it still does exactly what the runbook says).
This is not an implementer defect: the string is required byte-for-byte by `plan:368` and
Assumption 4 ("Bumping it: edit `rev=`, `nix flake lock --update-input nixos-agent-env`"), so the
seat had no discretion here. Recorded for the record only — a future Nix release removing the
alias would break this runbook command, not today's gate.

**MINOR-2 — the Interfaces' prose requirements (Assumption-9 statement, gate-record-location
statement) are unenforced by any test, by the section's own design.** Interfaces (`plan:366`)
states the prose beneath each heading is "free to reword — heading text and fenced commands are
the contract," so R1–R3 test only headings and fenced commands, never the prose sentences.
I hand-verified both required sentences are present and accurate (contract items 3 and 4 above)
but no `checks.unit` assertion would catch a future edit that silently dropped them. This is the
section's own explicit scope choice, not an implementer gap — recorded per review-matrix item 7
("a stated contract with no test is a MINOR") for completeness, not as grounds to reject.

Context items checked and found not to apply: OL2's rollout-shape finding (`rate_limits` nested
in `event_msg`/`token_count` envelopes) is irrelevant here — `docs/runbook.md`, `flake.nix`, and
`tests/runbook.bats` mention no extractor, no `rate_limits`, no rollout shape at all (`grep -n -i
'rate_limit\|extractor\|codex_limits\|token_count\|event_msg'` over all three touched files: no
match). OL3's contract never claims anything about the extractor's input shape, so there is
nothing for that fact to contradict.

## Verdict

**APPROVED.** Every numbered contract item is met; every named mutant killed with none tried
outside the section's list; `unit`, `lint`, and the full `nix flake check -L` are green; the
runbook's four documented commands were run against this host's real paths and all four work
exactly as written; the commit is a single byte-exact-subject commit with correct trailers and
no touches outside the section's list; the `flake-check` naming mismatch is independently
reconfirmed as the same non-fabrication already established at OL1's gate. Two MINORs recorded
(a plan-mandated deprecated flag; two prose contract lines the section itself scopes out of
testing) — neither blocks.
