---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run mcp, task P2pro — APPROVED

Plan: `docs/superpowers/plans/2026-09-05-model-comparison.md`, section `### P2pro (code, S)`.
Workspace (read-only): `/home/dalhaka/factory/ws/mcp/P2pro`, branch `task/P2pro`, head `3323ad481e37`, base `ec4f8285`.
Reviewed in a throwaway `--local` clone; the workspace was not touched and is clean.

## Summary

The task landed as specified. One commit, exactly the four named files, subject byte-identical to
the plan's `**commit subject:**`, `Co-Authored-By: Claude Fable 5.1` trailer present (plus the
seat's `Generated-By:` line). `tests/lint/bats-and-chain.sh` is **byte-identical** to the plan's
code block (`diff` clean). `tests/lint/fixtures/and-chain.bats` matches the plan's block except for
a missing final newline.

Acceptance is green by ref: `lint`, `unit` and `nix develop -c githooks/pre-commit` all pass on the
branch head. The red is real and reproduced: the fixture is refused with exactly the line the plan
predicts, and the default run over `tests/unit/*.bats` is clean. Both enforcement points were proven
by an independent mutation — a `] && [` line in `tests/unit/00-mutant.bats` fails `githooks/pre-commit`
and fails the `lint` derivation with the same stderr message. The fixture test itself was proven
load-bearing by breaking the guard's regex: the fixture run then exits 0.

One deviation from the section's literal text: `flake.nix` invokes the guard as
`bash tests/lint/bats-and-chain.sh`, not bare. I verified this is **necessary, not cosmetic** — with
the bare invocation the `lint` derivation fails `/usr/bin/env: bad interpreter: No such file or
directory`, because the build sandbox has no `/usr/bin/env`. The plan's parenthetical ("the check
runs in `${self}`, so `tests/lint/bats-and-chain.sh` resolves") was wrong on this point. The
implementer found it, reasoned to the right fix, and disclosed it in `FACTORY-NOTES`. Approved.

No hard-rule breaches: no new `2>/dev/null` anywhere in the diff, shellcheck clean (directly and via
the `lint` check's `find tests -name '*.sh'` sweep), commits through the devShell hook.

## Usage

```json
{"model": "deepseek/deepseek-v4-pro-0813", "events": 838, "input": 157761, "output": 11454, "cacheRead": 614144, "reasoning": 0, "duration_s": 231.068}
```

`wall_s: 232`, `exit_code: 0`, one commit, diffstat 4 files / 29 insertions / 0 deletions.

## Checks

| check | command | result |
|---|---|---|
| commit shape | `git show --stat HEAD` | exactly `flake.nix`, `githooks/pre-commit`, `tests/lint/bats-and-chain.sh`, `tests/lint/fixtures/and-chain.bats`; 29 insertions, 0 deletions |
| commit subject | `diff` vs the section's `**commit subject:**` | byte-identical |
| trailer | `git log -1 --format=%B` | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present; `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 …` above it (allowed) |
| guard vs plan text | `diff` plan code block vs `tests/lint/bats-and-chain.sh` | identical |
| fixture vs plan text | `diff` plan code block vs `tests/lint/fixtures/and-chain.bats` | identical except `\ No newline at end of file` |
| guard mode | `git ls-files -s tests/lint` | `100755` on the guard, `100644` on the fixture — correct |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | exit 0 |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 0 |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link` | exit 0 |
| unit did not eat the fixture | `nix log .#checks.x86_64-linux.unit` | `1..128`; no `and-chain`, no `fixtures`, no `vacuous chain` test name. `unit` runs `bats tests/unit` only, so `tests/lint/fixtures/` is out of its reach by construction as well as in fact |
| shellcheck | `nix develop -c shellcheck tests/lint/bats-and-chain.sh` | exit 0; also swept by the `lint` check's `find tests -name '*.sh'` line |
| no gated `2>/dev/null` | `git show HEAD \| grep '^+.*2>/dev/null'` | none |
| workspace untouched | `git status --porcelain` in `/home/dalhaka/factory/ws/mcp/P2pro` | clean |

Wiring placement matches the section: the two lines sit immediately after the `ruff format --check`
line in `githooks/pre-commit`, and immediately before `touch $out` in the `lint` `runCommand`.

## Red before green

Run in the clone at branch head, exactly as the section's Step 2 prescribes.

```
$ nix develop -c tests/lint/bats-and-chain.sh tests/lint/fixtures/and-chain.bats; echo exit=$?
4:  [ 1 -eq 2 ] && [ 2 -eq 2 ]
lint: '] && [' chain in a bats test is vacuous under errexit — split it onto two lines (tests/lint/bats-and-chain.sh)
exit=1

$ nix develop -c tests/lint/bats-and-chain.sh; echo exit=$?
exit=0
```

Both match the section verbatim, including the expected `4:  [ 1 -eq 2 ] && [ 2 -eq 2 ]` line and
the exact stderr message (em dash included). The default set is clean, and the fixture under
`tests/lint/fixtures/` is not scanned by the default run — confirmed by the second command exiting 0
while the fixture exists on disk.

The transcript (`/home/dalhaka/factory/runs/mcp/P2pro.log`) shows the red was run **before** the
wiring edits, not reconstructed afterwards.

## Mutation table

| # | mutation | expected | observed | verdict |
|---|---|---|---|---|
| M1 | `tests/unit/00-mutant.bats` with `[ 1 -eq 1 ] && [ 1 -eq 1 ]`, run `nix develop -c githooks/pre-commit` | hook fails with the guard's message | `3:  [ 1 -eq 1 ] && [ 1 -eq 1 ]` then `lint: '] && [' chain … (tests/lint/bats-and-chain.sh)`, `exit=1` | killed — pre-commit enforcement is live |
| M2 | same file `git add`ed, `nix build .#checks.x86_64-linux.lint -L --no-link` | derivation fails identically | builder log shows the same two lines, `exit=1` | killed — flake enforcement is live |
| M3 | guard's regex `'\] && \['` → `'ZZZNEVERMATCHZZZ'`, rerun the fixture | fixture must now pass | `exit=0`, no output | killed — the fixture test is load-bearing, not decorative |
| M4 | `flake.nix`: drop the `bash ` prefix (i.e. the section's literal line), `git add`, build `lint` | (probe of the deviation) | `tests/lint/bats-and-chain.sh: /usr/bin/env: bad interpreter: No such file or directory`, `exit=1` | the deviation is **necessary**; the plan's literal instruction cannot work |
| M5 | run the guard in a tree where `tests/unit/*.bats` matches nothing | (probe of a latent gap) | `grep: tests/unit/*.bats: No such file or directory` on stderr, **`exit=0`** | **surviving** — see Findings F3 |

The tree was restored to a clean `git status --porcelain` after every mutation; final state verified
clean before writing this review.

## Findings

**F1 (minor, inherited from the plan) — the guard never prints the file name.** The `Interfaces`
bullet and the commit message body both promise `file:line` for every offender. The guard calls
`grep -n … "$f"` once per file inside the loop, so GNU grep never prefixes the file name: the actual
output is `LINE:content`. M1 and M2 show this concretely — with ~30 files in `tests/unit/` the
operator gets a bare `3:  [ 1 -eq 1 ] && [ 1 -eq 1 ]` and no way to tell which test file is at fault.
This is a defect in the plan's own code block (its Step 2 expected output, `4:  [ 1 -eq 2 ] …`, also
shows no file name, so the plan is internally inconsistent), and the implementer reproduced that
block byte-for-byte as instructed. Not grounds for rejection; worth a one-line follow-up
(`grep -Hn`, or pass all files to a single `grep`).

**F2 (minor) — the necessary `bash` prefix in `flake.nix` carries no comment.** A reader now sees
`bash tests/lint/bats-and-chain.sh` in the flake next to a bare `tests/lint/bats-and-chain.sh` in
`githooks/pre-commit` with nothing explaining the asymmetry. This repo documents exactly this
hazard elsewhere — `flake.nix`'s `unit` check already says "scripts run via bash, so no
`/usr/bin/env` patch is needed" — so house style is a comment. The implementer explicitly considered
adding one and chose "keep minimal". One sentence would have paid for itself the next time someone
"tidies" the prefix away.

**F3 (minor, latent, inherited from the plan) — the guard passes silently if its default glob
matches nothing.** M5: with no `tests/unit/*.bats`, the unexpanded glob reaches `grep`, which errors;
because the call sits inside `if grep …; then`, errexit is suppressed, `bad` stays 0 and the guard
exits 0. So a rename or move of `tests/unit/` would silently disarm both enforcement points while
`lint` stays green. `shopt -s nullglob` plus an explicit "nothing to scan" refusal would close it.
Again the plan's code, faithfully copied.

**F4 (informational) — false positives are possible but harmless.** The guard is a line grep, so a
`] && [` inside a comment or a heredoc in a `.bats` file would be refused. Acceptable for a lint
guard of this shape; noted so nobody is surprised.

**F5 (process, for the comparison) — the model's own summary repeats the plan's inaccurate
`file:line` claim.** The commit body says the guard "names file:line", which F1 shows it does not.
The implementer trusted the plan's prose over the behaviour it had just observed in its own red run
(where no file name appeared). Minor, but it is an unverified claim shipped in the commit record.

Nothing found that breaks an invariant, touches the live host, or weakens an existing gate. The
change is additive: 29 insertions, 0 deletions, no existing check modified.

## Deviations

Every departure from the section's literal instructions, however small:

1. **`flake.nix` invokes `bash tests/lint/bats-and-chain.sh`, not the section's literal
   `tests/lint/bats-and-chain.sh`.** The section says "the same two lines" for both enforcement
   points. Proven necessary by M4: the literal line fails the `lint` derivation with
   `/usr/bin/env: bad interpreter`. Disclosed in `FACTORY-NOTES`. Accepted — the plan's parenthetical
   justification was factually wrong about the sandbox. (The comment line above it *is* verbatim, and
   `githooks/pre-commit` *is* verbatim, so the divergence is one word in one of the four lines.)
2. **`tests/lint/fixtures/and-chain.bats` has no final newline.** The plan's block implies one; the
   guard's own file got its trailing newline back from `shfmt` via treefmt (the transcript records
   this), but `*.bats` is outside treefmt's `includes`, so the fixture kept the model's output as
   written. Ungated, zero functional effect, but it is a deviation from the given text.
3. **The scratch commit-message file was written to `.scratch/` inside the workspace**, not to a
   scratch directory outside it as the Global Constraints' "message file in the scratch directory"
   suggests. The implementer noticed the risk unprompted and cleaned up; the workspace is clean and
   nothing stray was committed. Noted for completeness only.
4. **Process observation, not a rule breach:** the transcript spends roughly 200 of its 296 lines
   circling the one-word `bash`-prefix decision, re-reading the same sentence more than a dozen times
   and reversing itself several times ("use `bash` in both" → "flake only" → "both" → "flake only")
   before landing on the correct minimal answer. Cost is visible in the usage line (838 events,
   157,761 input tokens, 614,144 cached-read, 231 s wall) for a 29-line additive change. The
   conclusion was right and the evidence was gathered honestly; the route to it was not economical.

No other deviations. Steps 1–5 of the section were each performed, in order, with the prescribed
commands.
