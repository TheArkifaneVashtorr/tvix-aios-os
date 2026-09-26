---
reviewer: opus
majors: null
minors: null
mutants_killed: 3
---
# Opus gate — seat run mcf2, task P2flash — APPROVED

Plan: `docs/superpowers/plans/2026-09-05-model-comparison.md`, section `### P2flash (code, S)`.
Workspace (read-only): `/home/dalhaka/factory/ws/mcf2/P2flash`, branch `task/P2flash`, head `2ae584ec250d`, base `3f21ba82`.
Reviewed in a throwaway `--local` clone; the workspace was not touched and is clean.
Section text confirmed identical to `### P2pro` modulo the key, so the two reviews are comparable line by line.

## Summary

The task landed as specified. One commit, exactly the four named files, subject byte-identical to the
plan's `**commit subject:**`, `Co-Authored-By: Claude Fable 5.1` trailer present (plus the seat's
`Generated-By:` line above it). `tests/lint/bats-and-chain.sh` is **byte-identical** to the plan's
code block (`diff` clean). `tests/lint/fixtures/and-chain.bats` matches the plan's block except for a
missing final newline — the same single-byte deviation Pro produced.

Acceptance is green by ref: `lint`, `unit` and `nix develop -c githooks/pre-commit` all pass on the
branch head. The red is real and reproduced: the fixture is refused with exactly the line the plan
predicts, and the default run over `tests/unit/*.bats` is clean. Both enforcement points were proven
by an independent mutation — a `] && [` line in `tests/unit/00-mutant.bats` fails
`nix develop -c githooks/pre-commit` and fails the `lint` derivation with the same stderr message.
The fixture test itself was proven load-bearing by breaking the guard's regex: the fixture run then
exits 0.

The plan's parenthetical trap ("the check runs in `${self}`, so `tests/lint/bats-and-chain.sh`
resolves") is wrong, and Flash hit it, diagnosed it and fixed it correctly: `flake.nix` invokes the
guard as `bash tests/lint/bats-and-chain.sh`. I re-proved the necessity (M4): with the bare line the
`lint` derivation dies at `/usr/bin/env: bad interpreter: No such file or directory`, exit 126.
Flash disclosed the deviation in `FACTORY-NOTES`, in the commit body, **and in a comment beside the
line in `flake.nix`** — the comment Pro's F2 asked for and did not write. That is the one substantive
quality difference between the arms, and it is in Flash's favour.

Against that, Flash made a real process error Pro did not: its first commit contained only the two
new files, because `flake.nix` and `githooks/pre-commit` had been edited but never `git add`ed. It
caught this itself by reading the diffstat, staged the two files and amended (the amend re-ran the
hook, green). The final state is correct — one commit, four files — so this costs no verdict, but it
is a self-inflicted round trip. Approved.

No hard-rule breaches: no new `2>/dev/null` anywhere in the diff, shellcheck clean (directly and via
the `lint` check's `find tests -name '*.sh'` sweep), commits through the devShell hook.

## Usage

```json
{"model": "deepseek/deepseek-v4-flash", "events": 1104, "input": 105110, "output": 20048, "cacheRead": 1195776, "reasoning": 0, "duration_s": 373.514}
```

`wall_s: 374`, `exit_code: 0`, one commit, diffstat 4 files / 30 insertions / 0 deletions.

## Checks

| check | command | result |
|---|---|---|
| one commit on base | `git rev-list 3f21ba82..HEAD \| wc -l` | `1` |
| commit shape | `git show --stat HEAD` | exactly `flake.nix`, `githooks/pre-commit`, `tests/lint/bats-and-chain.sh`, `tests/lint/fixtures/and-chain.bats`; 30 insertions, 0 deletions |
| commit subject | `diff` vs the section's `**commit subject:**` | byte-identical |
| trailer | `git log -1 --format=%B` | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present; `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash …` above it (allowed) |
| guard vs plan text | `diff` plan code block vs `tests/lint/bats-and-chain.sh` | identical |
| fixture vs plan text | `diff` plan code block vs `tests/lint/fixtures/and-chain.bats` | identical except `\ No newline at end of file` |
| guard mode | `git ls-files -s tests/lint` | `100755` on the guard, `100644` on the fixture — correct |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | exit 0 |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 0 |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link` | exit 0 |
| unit did not eat the fixture | `nix log .#checks.x86_64-linux.unit` | `1..130`; no `and-chain`, no `fixtures`, no `vacuous chain` test name. The check does `cp -r ${self}/tests tests` (so the fixture *is* copied into the sandbox) but then runs `bats tests/unit` only, so the fixture is never executed |
| shellcheck | `nix develop -c shellcheck tests/lint/bats-and-chain.sh` | exit 0; also swept by the `lint` check's `find tests -name '*.sh'` line |
| no gated `2>/dev/null` | `git show HEAD \| grep '^+.*2>/dev/null'` | none |
| workspace untouched | `git status --porcelain` in `/home/dalhaka/factory/ws/mcf2/P2flash` | clean |
| clone restored | `git status --porcelain` after every mutation | clean |

Wiring placement matches the section: the guard lines sit immediately after the `ruff format --check`
line in `githooks/pre-commit`, and immediately before `touch $out` in the `lint` `runCommand`. The
flake side carries three lines rather than the section's two — the plan's comment verbatim, plus a
second comment explaining the `bash` prefix (see Deviations 2).

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

Both match the section verbatim, including the expected `4:  [ 1 -eq 2 ] && [ 2 -eq 2 ]` line and the
exact stderr message (em dash included). The default set is clean, and the fixture under
`tests/lint/fixtures/` is not scanned by the default run — confirmed by the second command exiting 0
while the fixture exists on disk.

The transcript (`/home/dalhaka/factory/runs/mcf2/P2flash.log`) shows the red was run **before** the
wiring edits: "Step 1 done. Now Step 2: red, both sides." at line 195, both red results recorded at
lines 202–210, "Now Step 3: wire into githooks/pre-commit … and flake.nix" at line 212. Not
reconstructed afterwards.

## Mutation table

Same five mutations as the P2pro gate, same order, same expectations.

| # | mutation | expected | observed | verdict |
|---|---|---|---|---|
| M1 | `tests/unit/00-mutant.bats` with `[ 1 -eq 1 ] && [ 1 -eq 1 ]`, run `nix develop -c githooks/pre-commit` | hook fails with the guard's message | `3:  [ 1 -eq 1 ] && [ 1 -eq 1 ]` then `lint: '] && [' chain … (tests/lint/bats-and-chain.sh)`, `exit=1` | killed — pre-commit enforcement is live |
| M2 | same file `git add`ed, `nix build .#checks.x86_64-linux.lint -L --no-link` | derivation fails identically | builder log shows the same two lines, `exit=1` | killed — flake enforcement is live |
| M3 | guard's regex `'\] && \['` → `'ZZZNEVERMATCHZZZ'`, rerun the fixture | fixture must now pass | `exit=0`, no output | killed — the fixture test is load-bearing, not decorative |
| M4 | `flake.nix`: drop the `bash ` prefix (i.e. the section's literal line), build `lint` | (probe of the deviation) | `tests/lint/bats-and-chain.sh: /usr/bin/env: bad interpreter: No such file or directory`, builder exit code 126 | the deviation is **necessary**; the plan's literal instruction cannot work |
| M5 | run the guard in a tree where `tests/unit/*.bats` matches nothing | (probe of a latent gap) | `grep: tests/unit/*.bats: No such file or directory` on stderr, **`exit=0`** | **surviving** — identical to Pro; see Findings F3 |

The tree was restored to a clean `git status --porcelain` after every mutation; final state verified
clean before writing this review.

## Findings

**F1 (minor, inherited from the plan) — the guard never prints the file name.** The `Interfaces`
bullet promises `file:line` for every offender. The guard calls `grep -n … "$f"` once per file inside
the loop, so GNU grep never prefixes the file name: the actual output is `LINE:content`. M1 and M2
show it concretely — with ~30 files in `tests/unit/` the operator gets a bare
`3:  [ 1 -eq 1 ] && [ 1 -eq 1 ]` and no way to tell which test file is at fault. A defect in the
plan's own code block (its Step 2 expected output shows no file name either, so the plan is
internally inconsistent), reproduced byte-for-byte as instructed. Not grounds for rejection; a
one-line follow-up (`grep -Hn`, or one `grep` over all files) fixes it. Identical to P2pro F1.

**F2 (minor, latent, inherited from the plan) — the guard passes silently if its default glob matches
nothing.** M5: with no `tests/unit/*.bats`, the unexpanded glob reaches `grep`, which errors; because
the call sits inside `if grep …; then`, errexit is suppressed, `bad` stays 0 and the guard exits 0.
A rename or move of `tests/unit/` would silently disarm both enforcement points while `lint` stays
green. `shopt -s nullglob` plus an explicit "nothing to scan" refusal would close it. This is P2pro's
F3 — the guard text is byte-identical in both arms, so the gap is identical.

**F3 (informational) — false positives are possible but harmless.** The guard is a line grep, so a
`] && [` inside a comment or a heredoc in a `.bats` file would be refused. Acceptable for a lint
guard of this shape; noted so nobody is surprised. (P2pro F4.)

**F4 (process, minor, Flash-only) — the first commit silently omitted the wiring.** Transcript lines
420–440: the model edited `flake.nix` and `githooks/pre-commit` with its file tool (which does not
stage), `git add`ed only `tests/lint`, and committed — producing a "2 files changed, 25 insertions"
commit with neither enforcement point in it. It caught this by reading the diffstat it had just been
shown, reasoned out the cause correctly ("`git commit` without `-a` only commits staged changes"),
staged the two files and amended with the same message file; the amend re-ran the hook green. The
delivered state is correct and I verified it independently (four files, one commit, both wirings
present and both proven live by M1/M2). Recorded because it is a real self-inflicted round trip that
the Pro arm did not have, and because a less careful reading of the diffstat would have shipped a
guard that enforced nothing.

**F5 (positive, Flash-only, recorded for the comparison) — the commit record is accurate.** P2pro's
F5 was that the model's commit body repeated the plan's false `file:line` claim. Flash's commit body
makes no such claim; every sentence in it is true of the code as landed, including the `bash`-prefix
explanation. Flash also matched house style by commenting the prefix in `flake.nix` — the same file
already documents this exact sandbox hazard in the `unit` check ("the build sandbox has no
/usr/bin/env, so patch it here the way stdenv would"), which is what P2pro's F2 pointed at.

Nothing found that breaks an invariant, touches the live host, or weakens an existing gate. The
change is additive: 30 insertions, 0 deletions, no existing check modified.

## Deviations

Every departure from the section's literal instructions, however small:

1. **`flake.nix` invokes `bash tests/lint/bats-and-chain.sh`, not the section's literal
   `tests/lint/bats-and-chain.sh`.** Proven necessary by M4: the literal line fails the `lint`
   derivation with `/usr/bin/env: bad interpreter`, exit 126. Disclosed in `FACTORY-NOTES`, in the
   commit body, and in the flake itself. Accepted — the plan's parenthetical justification was
   factually wrong about the sandbox. Same deviation as P2pro's #1.
2. **The flake side carries three lines, not the section's "same two lines".** The extra line is a
   second comment: `# Invoked via \`bash\`: the sandbox has no /usr/bin/env for the shebang.` This is
   a textual deviation from "the same two lines" and is why the diffstat is 30 insertions to Pro's
   29. It is also exactly the remediation P2pro's F2 recommended, so it is accepted as an
   improvement, not a defect.
3. **`tests/lint/fixtures/and-chain.bats` has no final newline.** The plan's block implies one;
   `*.bats` is outside treefmt's `includes`, so the fixture kept the model's output as written.
   Ungated, zero functional effect. Identical to P2pro's #2.
4. **The scratch commit-message file was written to `scratch/` inside the workspace**, not to a
   scratch directory outside it as the Global Constraints' "message file in the scratch directory"
   suggests. The model considered the risk, chose the in-workspace path deliberately, and removed the
   directory after committing; the workspace is clean and nothing stray was committed. Same class as
   P2pro's #3 (Pro used `.scratch/`).
5. **Process observation, not a rule breach — the commit had to be amended.** See Findings F4: the
   first commit carried only two of the four files. One extra commit/amend cycle and one extra hook
   run. The Pro arm staged correctly the first time.
6. **Process observation — transcript economy.** 490 lines to Pro's 296 for the same 30-line change,
   374 s to Pro's 231 s. The `bash`-prefix question is handled better than Pro's: Flash raised the
   shebang hazard *pre-emptively* at line 183–185, explicitly chose to settle it empirically ("I'll
   verify with the actual build") rather than theorize, hit the failure at line 247, and reached the
   correct fix by line 267 — roughly 50 lines of post-failure deliberation, with **zero reversals**
   of the answer (two alternatives, `patchShebangs` and changing the shared shebang, were raised and
   correctly rejected once each). It also decided correctly and once that `githooks/pre-commit` does
   *not* need the prefix. Pro spent ~200 of its 296 lines on the same one-word decision and reversed
   itself four times. Flash's extra length is spent elsewhere: 28 self-interrupting
   "Hmm/Wait/Actually" turns spread across the whole run, several of them re-litigating facts it had
   already observed (e.g. re-deriving twice whether `/usr/bin/env` exists on the host after its own
   Step 2 had proven it does), plus the amend recovery.

No other deviations. Steps 1–5 of the section were each performed, in order, with the prescribed
commands.

## Comparison with P2pro

| | P2pro | P2flash |
|---|---|---|
| verdict | APPROVED | APPROVED |
| mutations killed | M1, M2, M3 killed; M4 proved the deviation necessary; **M5 survives** | M1, M2, M3 killed; M4 proved the deviation necessary; **M5 survives** |
| deviations count | 4 (1 necessary, 1 whitespace, 1 scratch path, 1 process) | 6 (1 necessary, 1 extra comment line, 1 whitespace, 1 scratch path, 2 process) |
| `bash`-prefix handling | found only after the build failed; ~200 of 296 transcript lines, 4 reversals; no comment in the flake (F2) | hazard anticipated before the build, settled empirically; ~50 post-failure lines, 0 reversals; commented in `flake.nix` and in the commit body |
| commit record accuracy | body repeats the plan's false `file:line` claim (F5) | body accurate throughout |
| staging | correct first time | first commit omitted both wirings; self-caught and amended (F4) |
| usage input / output / wall | 157,761 / 11,454 / 231 s (cacheRead 614,144; 838 events) | 105,110 / 20,048 / 374 s (cacheRead 1,195,776; 1,104 events) |
| transcript lines | 296 | 490 |

Both arms produced a functionally equivalent, correct, gate-live change from the same section text,
and both inherited the plan's two latent defects (F1 file name, M5 empty glob) unchanged. On code
quality the Flash artifact is marginally the better of the two — it is the only one that documents
the necessary `bash` prefix at the point of use and the only one whose commit body contains no
unverified claim. On process Pro is the cleaner run: no staging blunder, 38% fewer transcript lines,
62% of the wall clock. Flash bought its better artifact with 62% more wall time, 75% more output
tokens and a recovery cycle; it consumed 33% fewer input tokens but nearly twice the cached read.
