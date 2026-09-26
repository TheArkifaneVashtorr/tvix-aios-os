---
plan_defect: underspecified
mutants_total: 4
mutants_killed: 4
mutants_outside_named: 2
model: opus
---
# Opus gate — seat run pr1e, task KN1b — APPROVED

## Summary

KN1's blocker and all four of its majors are closed, and each closure is
measured rather than read. `docs/brief.md` §8 now carries **nine** rows, one per
bullet of `docs/brief.md:312-332`, where it carried zero;
`docs/board/operator-model.md` carries **ten** rows against ten ranked
preferences, including all six lines the prior gate named; `docs/board/policies.md`
carries **four** rows against four policies, the documentation policy (`:3-9`)
and factory economics (`:20-28`) among them; every one of the 63 rows is
byte-verbatim in its source under the new `--verbatim` arm, which I ran myself
and then proved able to fail; and the fabricated `command -v jq python3 bats`
measurement is gone, replaced by the meta-planning packet's own §9.1 sentence
with a line cite, as are §9.2's and §9.3's. Only three rows in the file state a
measurement at all, and all three quote the packet.

The sandbox minor is closed in the way that matters: `evidence-unit`'s
derivation now copies the six cited repo files, and I proved the resolution is
real by pointing one row's `source` at a wrong line in a file that *does* resolve
— `test_shipped_inventory_validates` fails with `source line does not contain the
rule text`, which under KN1's sandbox would have been silently skipped.

All three `acceptance` checks are green in a fresh clone under `--rebuild`
(`550 passed`, `59 passed`, `lint` exit 0). Red before green is reproduced
independently and more sharply than the commit body's own: dropping KN1's actual
44-row `rules.toml` into KN1b's tests fails one test per guarantee — the verbatim
pass, the §8 coverage test and the fabricated-measurement test — `3 failed, 547
passed`. All four named mutants die. One commit, subject byte-identical, both
trailers in policy order with the model from `KN1b.result`, and all six changed
files inside the chain's `touches` union.

Two things are recorded and neither gates. The completeness guarantee is
coverage **by source**, not by rule: deleting the factory-economics policy row
leaves `evidence-unit` green (measured, mutant F). That is what the section's
Tests line asked for, so it is a plan defect of class `underspecified`, owed as
one line. And the seat wrote its result line as a markdown heading, so
`KN1b.result` reads `status=unreported` — a reporting defect with no substance
behind it.

The step-7 pass found one real consequence the acceptance checks do not name:
`evidence-unit` now reads six files it never read before, with line numbers, so
an unrelated edit that shifts lines in any of them turns it red. Measured, not
assumed.

**APPROVED.**

## Diff against the section

Fresh clone of `task/KN1b` at `73df313`, base `6596b1e` from `KN1b.result`.

```
$ git -C <clone> log --oneline -3
73df313 knowledge: KN1 fix round — brief §8, the missing preferences and policies, verbatim text enforced, the fabricated measurement removed (test: evidence-unit, ledger-unit, lint)
6596b1e docs: type KN1b; G5 exempts the forced MAP.md regeneration too (test: lint)
4972422 docs: type PR1b and give G5 the derived-queue-block exemption (test: lint)

$ git -C <clone> rev-list --count 6596b1e..HEAD
1

$ git -C <clone> diff --stat 6596b1e..HEAD
 docs/MAP.md                  |   2 +-
 docs/ledger/rules.toml       | 793 +++++++++++++++++++++++++++++++++++++++++++
 docs/runbooks/session.md     |  10 +
 flake.nix                    |  11 +
 pkgs/evidence/rules.py       | 229 +++++++++++++
 tests/evidence/test_rules.py | 231 +++++++++++++
 6 files changed, 1275 insertions(+), 1 deletion(-)
```

One commit, as Step 5 orders. KN1b is a fresh pass carrying KN1's whole
deliverable (Step 1's cherry-pick) plus this round's corrections, which is why
`rules.toml`, `rules.py` and `test_rules.py` appear as whole-file additions
against the base.

**Touches.** A fix round's contract is the chain's union:

```
$ nix develop -c python3 pkgs/evidence/tasks.py touches docs/superpowers/plans/2026-09-09-program.md KN1b
docs/ledger/rules.toml
pkgs/evidence/rules.py
tests/evidence/test_rules.py
docs/runbooks/session.md
flake.nix
docs/MAP.md

$ git -C <clone> diff --name-only 6596b1e..HEAD
docs/MAP.md
docs/ledger/rules.toml
docs/runbooks/session.md
flake.nix
pkgs/evidence/rules.py
tests/evidence/test_rules.py
```

Six changed files, six union members, set-equal. No undeclared touch.
`docs/OPERATIONS.md` does not appear at all, so G5's first standing exemption is
unused; `docs/MAP.md` is in the union on its own account (KN1b names it), so
G5's second exemption is not needed either, and the hunk is exactly what
`repomap.py write` produces for the one test file KN1 added
(`tests/evidence — 100 files` → `101 files`), with `lint` — which runs
`repomap.py --root . check` — green below.

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` line (`docs/superpowers/plans/2026-09-09-program.md:706`):

```
$ wc -c subj_commit.txt subj_plan.txt
178 subj_commit.txt
178 subj_plan.txt
$ md5sum subj_commit.txt subj_plan.txt
3c94830cfeea6e174d13bc0da7131555  subj_commit.txt
3c94830cfeea6e174d13bc0da7131555  subj_plan.txt
$ cmp subj_commit.txt subj_plan.txt && echo IDENTICAL
IDENTICAL
```

`(test: evidence-unit, ledger-unit, lint)` equals the `acceptance` list. Both
trailers, in policy order (`docs/board/policies.md:30-36`):

```
$ git -C <clone> log -1 --format=%B | grep -n "Generated-By\|Co-Authored-By"
61:Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pr1e)
62:Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `KN1b.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`), the run equal to `pr1e`. Correct.

**The blocker and the four majors, each by name.** The prior gate is `~/factory/runs/pr1b/KN1.review.md`
(`FACTORY-REVIEW verdict=rework`). Its findings are quoted and answered in order.
The per-source arithmetic behind every answer is one command:

```
$ grep '^source = ' <clone>/docs/ledger/rules.toml | sed 's/^source = "//; s/:[0-9]*"$//' | sort | uniq -c
     14 CLAUDE.md
     10 docs/board/operator-model.md
      4 docs/board/policies.md
     15 docs/brief.md
      4 docs/runbooks/session.md
      6 pkgs/dsh-openrouter/hook-guard.py
      6 tools/orchestrator-guard.sh
      4 ~/flakes/dsh-harness/AGENTS.md
$ grep -c '^\[\[rule\]\]' <clone>/docs/ledger/rules.toml
63
```

63 rows against KN1's 44 — the 19 the commit body claims (§8 ×9,
operator-model ×6, policies ×2, CLAUDE.md gotchas ×2), reproduced by
`git show FETCH_HEAD:docs/ledger/rules.toml | grep -c '^\[\[rule\]\]'` → `44` on
`task/KN1` fetched from `~/factory/ws/pr1b/KN1`. Every integer the body pastes
reproduces (G11).

**BLOCKER — "`docs/brief.md` §8 (`:312-332`) is entirely absent: zero rows cite
it".** Closed, and closed row-for-rule rather than by a token row. §8 is nine
bullets; the file carries nine rows, whose cited lines land one on each:

| brief §8 bullet | line | row |
|---|---|---|
| Terse. No preamble … | 314 | `R-practice-brief8-terse` |
| Do not write code before Section 9 is resolved. | 315 | `R-practice-brief8-no-code-before-9` |
| Pin every flake input to an exact rev … | 316 | `R-practice-brief8-pin-inputs` |
| No secret material in the repo, ever … | 317 | `R-practice-brief8-no-secrets` |
| When you take a package from `kissgyorgy/coding-agents` … enumerate … | 319 | `R-practice-brief8-enumerate-defaults` |
| If upstream has moved since Section 4, tell me … | 322 | `R-practice-brief8-upstream-moved` |
| Prefer failing the build over a runtime check … | 324 | `R-practice-brief8-fail-build` |
| One phase at a time. Commit at each phase boundary … | 326 | `R-practice-brief8-one-phase` |
| If something in this brief is wrong … say so. | 328 | `R-practice-brief8-brief-wrong` |

Nine rules in the section, nine rows, no rule left over — I enumerated the
section's bullets from `sed -n '312,332p' docs/brief.md` before looking at the
inventory. The two the prior gate named explicitly read verbatim against their
own lines:

```
$ sed -n '316,318p' <clone>/docs/brief.md
- Pin every flake input to an exact rev. No `follows` chains you have not checked.
- No secret material in the repo, ever — not in comments, not in test fixtures, not in
  example configs. Use placeholders and tell me what to populate out of band.
```

against `text = "Pin every flake input to an exact rev. No \`follows\` chains you
have not checked."` and `text = "No secret material in the repo, ever — not in
comments, not in test fixtures, not in example configs. Use placeholders and tell
me what to populate out of band."` — byte for byte, em-dash and backticks
included. The blocker is closed.

**MAJOR — "`operator-model.md` is 4 of 10: six ranked preferences are
uninventoried (`:7, :8, :10, :11, :13, :14`)".** Closed. The file's ranked list
is `:5-14`, ten bullets; the inventory cites all ten lines, one row each:
`:5 R-practice-terse`, `:6 R-practice-privacy-first`,
**`:7 R-practice-tool-names-literally`**, **`:8 R-practice-tell-when-wrong`**,
`:9 R-practice-fail-build`, **`:10 R-practice-one-phase`**,
**`:11 R-practice-deterministic-first`**, `:12 R-practice-falsifiable`,
**`:13 R-practice-no-secrets`**, **`:14 R-practice-recommendations`** — the six
in bold are the six the gate named. Two spot-checked against their lines:

```
$ sed -n '7p;11p' <clone>/docs/board/operator-model.md
- tool names read literally, plain words for a softkey (`2026-09-02-amendment-softkey.md`)
- deterministic first, isolated workspaces second, judgement last; never design parallelism out (`2026-09-04-parallel-agent-workflows.md`)
```

The rows carry `tool names read literally, plain words for a softkey` and
`deterministic first, isolated workspaces second, judgement last; never design
parallelism out` — the bullet's own words, the list marker and the trailing
source citation dropped, which is the right cut and is a substring of the line.

**MAJOR — "`policies.md` is 2 of 4: the documentation policy (`:3-9`) and the
factory-economics policy (`:20-28`) are missing".** Closed. Four policies, four
rows: `:4 R-policy-documentation`, `:12 R-conv-lint-two-points`,
`:21 R-policy-factory-economics`, `:31 R-conv-commit-trailers`. Both previously
missing rows carry the whole policy body verbatim — the documentation row is the
entire `:4-9` paragraph down to "Memory (orchestrator-side) mirrors gate
status.", and the factory-economics row the entire `:21-28` paragraph down to
"Reference run before the policy: 21 agents, 1.96 M tokens, 2 h 09 m (Cowork
fix)." — checked with `sed -n '4,9p'` and `sed -n '21,28p'` against the row text.

**MAJOR — "`text` is not verbatim … `R-practice-build-only` (`:244`) drops 'you
do' and 'and runs the acceptance scripts'; `R-practice-hardware-config-verbatim`
(`:304`) rewrites 'exempt from formatting' as 'is never touched'".** Closed, and
now enforced by a check rather than by review. The two rows the gate named,
`sed -n` against their cited lines:

```
$ sed -n '10,12p' <clone>/CLAUDE.md
repo** (`nixosConfigurations.core`). Everything you do is build-only: never
`sudo`, `nixos-rebuild`, `systemctl start/stop/restart`, or basket
mount/teardown — the operator switches and runs the acceptance scripts.

R-practice-build-only.text =
  "Everything you do is build-only: never `sudo`, `nixos-rebuild`,
   `systemctl start/stop/restart`, or basket mount/teardown — the operator
   switches and runs the acceptance scripts."          ← "you do" and
                                                         "and runs the
                                                         acceptance scripts"
                                                         both restored

$ sed -n '42,43p' <clone>/CLAUDE.md
refusal); `hosts/core/hardware-configuration.nix` is verbatim generator output
and exempt from formatting; a NixOS switch does not start newly enabled *user*

R-practice-hardware-config-verbatim.text =
  "`hosts/core/hardware-configuration.nix` is verbatim generator output and
   exempt from formatting"                              ← the meaning change
                                                          ("is never touched")
                                                          is gone
```

The three further rows the gate's fourth major named are corrected too:
`R-invariant-no-promotion` now carries "(Hermes skills, dsh plugins, OpenClaw
automations)" (`brief.md:78-79`), `R-conv-new-language-formatter` is the literal
"New language ⇒ its formatter and linter land in the same task."
(`CLAUDE.md:65`, `⇒` and all), and `R-practice-statix-header` is "statix rejects
`{ ... }:` module headers — write `_:`" (`CLAUDE.md:40`) with the fabricated
"instead" gone. Two more spot-checks outside the gate's list, one of them the
gate's own separate minor:

```
$ sed -n '19p' <clone>/CLAUDE.md
is on the host PATH. `grep` on this host is ugrep.
$ sed -n '775p' <clone>/tools/orchestrator-guard.sh
  plan_reason='plan files change only through the Edit and Write tools (append-only headings) — see docs/runbooks/session.md'
```

matching `R-practice-grep-ugrep` and `R-guard-plan-write-tools` exactly. That is
seven rows spot-checked by hand against their cited lines, including the two the
prior gate named.

The machine agrees, and I ran it myself rather than trusting the body:

```
$ cd <clone> && nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . --verbatim
owed: 16 load-bearing rules without a check
EXIT=0
```

The arm is proved able to fail — mutant **A** below.

**MAJOR — "Interface 3 is violated … `R-practice-devshell-path` (`:261`)
fabricates a measurement — a `command -v jq python3 bats` result the packet never
produced".** Closed. The row's `measured` now reads

```
`command -v jq` → /run/current-system/sw/bin/jq; `command -v python3` fails.
The rule holds for `python3` and `bats`, not for `jq`
(packet §9.1 docs/research-2026-09-09-meta-planning-packet.md:398)
```

against the packet's own §9.1 at `:398`:

```
$ sed -n '398p' docs/research-2026-09-09-meta-planning-packet.md
1. **CLAUDE.md vs the host PATH.** … **measured**: `command -v jq` → `/run/current-system/sw/bin/jq`; `command -v python3` fails. The rule holds for `python3` and `bats`, not for `jq`.
```

— the packet's sentence, unaltered, with the citation appended. §9.2 and §9.3
are the same story: `R-practice-home-readonly` now carries the packet's
"`test -w \"$HOME\"` true and `systemctl --failed` exit 0, with no namespace
markers" (the two details the gate said were dropped) and `R-ritual-heredoc-lesson`
the packet's "exactly one denial with reasoning attached, and it is on `git reset
--soft HEAD~1`, not a heredoc", both cited to `:399` and `:400`. All three carry
the packet's own words.

**"no other row states a measurement that was not made"** — verified over the
whole file, not sampled. Every `measured` field is one of three shapes:

```
$ python3 -c "…"   # classify all 63 measured fields
Counter({'UNMEASURED': 43, 'check': 17, 'other': 3})
```

The 43 `UNMEASURED: <why>` rows claim nothing. The 17 `check <name>: nix build …`
rows claim a check covers the rule, and the named test files exist and cover the
named subject (`tests/unit/70-dsh-openrouter.bats`, 123 `@test`s, 18 lines
mentioning `sudo`/`nixos-rebuild`/`systemctl`; `tests/unit/91-orchestrator-guard.bats`,
141 `@test`s; `tests/unit/92-ritual.bats` for the Stop-hook row). The remaining
**three** are exactly the packet rows above. No fourth row states a measurement.

**MINOR (void) — "`docs/MAP.md:98` regenerated outside `touches`".** Correctly
void, and doubly so: `docs/MAP.md` is now named in KN1b's own `touches`, so
G5's second exemption is not even reached.

**MINOR — "`test_shipped_inventory_validates` cannot exercise source-line
resolution … the check silently skips".** Closed, and I proved the resolution is
real rather than reading the `cp` lines. `flake.nix:1380-1390` adds the copies
(`CLAUDE.md`, `docs/brief.md`, `docs/board/`, `docs/runbooks/session.md`,
`tools/orchestrator-guard.sh`, `pkgs/dsh-openrouter/hook-guard.py`), and the test
now asserts `rules.unresolved_sources(...)` is empty but for the harness
`AGENTS.md`. The proof the section asked for — make one row's `source` wrong and
show the test fails — is mutant **E**: pointing `R-policy-factory-economics` at
`docs/board/policies.md:2`, a line that exists in a file that resolves, gives

```
evidence-unit> E         Left contains one more item: 'rules: R-policy-factory-economics: source line does not contain the rule text'
evidence-unit> FAILED tests/evidence/test_rules.py::test_shipped_inventory_validates
evidence-unit> 1 failed, 549 passed in 14.32s
```

Under KN1's sandbox that row was unresolvable and the line check was skipped
silently; under KN1b's it fails the build. That is the guarantee the minor was
about, now load-bearing.

**The section's Interfaces, each with its command.**

*Interface 1 — `validate` exits 0 and prints the `owed:` count; `--verbatim`
additionally refuses a row whose text is not byte-for-byte in its source.* Both
forms run above, exit 0, `owed: 16`. The count is arithmetically re-derived:
63 rows, 33 `load_bearing = true`, 16 of those with `check = ""` — matching the
body's `owed: 16`. The increment-1 drill's exact command form (no `--root`, which
falls back to `parents[2]` of the file) also exits 0 with the same line, so the
Operator step will work as written. All 63 `verdict` fields are `""`, as the
drill requires.

*Interface 2 — every named source has at least one row.* `docs/brief.md` §3 (six
rows, `:68-78`) **and** §8 (nine rows, `:314-328`); `CLAUDE.md` 14;
`~/flakes/dsh-harness/AGENTS.md` 4; `tools/orchestrator-guard.sh` 6; the hook-guard
table `pkgs/dsh-openrouter/hook-guard.py` 6; `docs/board/policies.md` 4 of 4;
`docs/board/operator-model.md` 10 of 10; `docs/runbooks/session.md` 4. The data
satisfies the interface in full. What the *test* pins is weaker — see MINOR-1.

*Interface 3 — the three packet rows carry the packet's own words; no unmeasured
measurement.* Verified above, over all 63 rows.

## Red before green

Reproduced in the clone, and deliberately not by re-running the commit body's
recipe. The sharpest available red is the prior round's own artifact: KN1's
actual 44-row `rules.toml`, fetched from its workspace, dropped into KN1b's tree
with KN1b's validator, tests and sandbox intact.

```
$ git -C <clone> fetch /home/dalhaka/factory/ws/pr1b/KN1 task/KN1
$ git -C <clone> show FETCH_HEAD:docs/ledger/rules.toml > <clone>/docs/ledger/rules.toml
$ nix build <clone>#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> >       assert rules.validate(rows, repo_root=ROOT, verbatim=True) == []
evidence-unit> E       assert ["rules: R-in...ter 's'", ...] == []
evidence-unit> E       AssertionError: brief §8 must be inventoried
evidence-unit> E       AssertionError: assert 'command -v jq python3 bats' not in 'command -v ...bats, not jq'
evidence-unit> FAILED tests/evidence/test_rules.py::test_shipped_inventory_validates
evidence-unit> FAILED tests/evidence/test_rules.py::test_every_named_source_has_a_row - AssertionError: brief §8 must be inventoried
evidence-unit> FAILED tests/evidence/test_rules.py::test_no_unmeasured_measurement
evidence-unit> 3 failed, 547 passed in 15.69s
error: builder failed with exit code 1.
```

Three failures, one per guarantee this round adds, and each names the defect the
prior gate named: paraphrase, absent §8, fabricated `bats`. The tests are
therefore discriminating against the exact artifact that was rejected, which is a
stronger statement than the body's own reds — and `3 + 547 = 550` reconciles the
green count below (G11). The body's two reds are internally consistent with the
same total (`6 + 544` and `5 + 545`), and its `550` is KN1's `545` plus the five
tests this round adds.

Restored from a pristine copy; `git -C <clone> status --porcelain` is empty after
every mutation in this review.

## Checks

Fresh clone, `--rebuild` on every acceptance check so none is a cached echo of
the seat's own run. (Mutant runs drop `--rebuild`: a mutated source is a new
derivation, and `--rebuild` refuses one that was never built.)

| check | command | result |
|---|---|---|
| evidence-unit | `nix build <clone>#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **PASS** — `550 passed in 14.02s`, `EXIT=0` |
| ledger-unit | `… ledger-unit -L --no-link --rebuild` | **PASS** — `59 passed in 1.15s`, `EXIT=0` |
| lint | `… lint -L --no-link --rebuild` | **PASS** — `EXIT=0`; every formatter and linter arm zero, `repomap check` silent |
| unit (not in `acceptance`) | `… unit -L --no-link` | **PASS** — `1..687`, `ok 687 now-paragraph accepts the real board's Now paragraph`, `EXIT=0` |
| factory-unit (not in `acceptance`) | `… factory-unit -L --no-link` | **PASS** — `plan.test.mjs: all assertions passed`, `EXIT=0` |

`550 passed` reproduces the commit body exactly. The direct command Step 3 also
requires is pasted under Interface 1: `validate … --root . --verbatim` → exit 0,
`owed: 16 load-bearing rules without a check`.

The result-line note: `KN1b.result` reads `status=unreported` because the seat
emitted `## FACTORY-RESULT` — a markdown heading — where `factory-task:516-518`
greps `^FACTORY-RESULT[[:space:]]+status=(done|partial|failed)` at column one and
classifies anything else mentioning the label as a near-miss. The driver's own
`checks_verified: evidence-unit=pass ledger-unit=pass lint=pass` with
`checks_verified_src: …=run` and `touches_extra: 0` were derived, not reported,
and my independent runs above agree with all three. Recorded as MINOR-2.

## Mutants

Applied in the clone, run, restored from a pristine copy; the tree ends
`git status --porcelain` empty after each. `mutants_total: 4` counts the
section's Step 4 set; two more were applied outside it.

| # | mutant | named? | outcome |
|---|---|---|---|
| **A** | paraphrase `R-practice-build-only`'s `text` — drop "you do" and "and runs the acceptance scripts", the prior round's own defect | yes (Step 4) | **KILLED** — `validate --verbatim` → `rules: R-practice-build-only: text is not byte-for-byte in CLAUDE.md (near line 10); first differing character 'i'`, `EXIT=1`; `evidence-unit` red at `FAILED …::test_shipped_inventory_validates`, `1 failed, 549 passed` |
| **B** | delete the nine brief §8 rows | yes (Step 4) | **KILLED** — `evidence-unit` red: `FAILED …::test_every_named_source_has_a_row - AssertionError: brief §8 must be inventoried`, and `False = has_line('docs/brief.md', 312, 333 - 1)`, `1 failed, 549 passed` |
| **C** | revert the whole sandbox-copy block from `flake.nix` | yes (Step 4) | **KILLED** — `evidence-unit` red twice: `test_shipped_inventory_validates - AssertionError: repo-local sources must resolve in the sandbox: [… 59 items …]` and `test_every_named_source_has_a_row - FileNotFoundError: '/build/docs/brief.md'`. The skip is what fails, exactly as Step 4 asks |
| **D** | restore the fabricated `command -v jq python3 bats` measurement | yes (Step 4) | **KILLED** — `evidence-unit` red: `FAILED …::test_no_unmeasured_measurement - AssertionError: assert 'command -v jq python3 bats' not in …`, `1 failed, 549 passed` |
| E | point `R-policy-factory-economics`'s `source` at `docs/board/policies.md:2` — a real file, the wrong line | OUTSIDE | **KILLED** — `evidence-unit` red: `'rules: R-policy-factory-economics: source line does not contain the rule text'`, `1 failed, 549 passed`. This is the section's demanded proof that the sandbox now *resolves* rather than skips: under KN1's sandbox this mutation was invisible |
| F | delete the `R-policy-factory-economics` row entirely (63 → 62 rows; `policies.md` 4 → 3) | OUTSIDE | **SURVIVED** — `evidence-unit` `550 passed`, `EXIT=0`. The coverage test asserts only that `docs/board/policies.md` appears among the sources, never that all four policies do. MINOR-1 |

Four for four on the named set. Mutant **F** is the one worth naming: it is the
prior round's blocker in miniature — a source present but incompletely
inventoried — and nothing in the suite catches it.

## Defects

**MINOR-1 — the completeness guarantee is coverage by *source*, not by *rule*.**
Plan defect: `underspecified`. Non-gating.

Interface 2 reads "Every source the section names has at least one row: … 
`policies.md` (all four), `operator-model.md` (all ten)". The data satisfies it —
four of four, ten of ten, nine of nine for brief §8, all counted above. The test
does not: `test_every_named_source_has_a_row` asserts `p in sources` for each
path and, for the brief, that *some* row's line falls inside §3 and *some* inside
§8. Mutant **F** measures the consequence: drop one of the four policies and
`evidence-unit` stays green at `550 passed`. Delete eight of the nine §8 rows and
the §8 assertion still holds.

This is the plan's defect, not the seat's. The section's Tests line maps the
guarantee to exactly one mutant — "every named source has a row → B" — and B is
"delete the brief §8 rows", which the implementation kills. The seat built what
was asked. But the round exists *because* a source was present and incompletely
covered, so the natural discriminator is a count, not a presence.

*Owed*: one line from the orchestrator — either narrow Interface 2's wording to
presence, or type a follow-up that pins the three counts the section names
(4 policies, 10 preferences, 9 §8 bullets) so a dropped row is a red build. Not
worth a third round: the data is complete today and this gate counted it
row-by-rule.

**MINOR-2 — the seat's result line is a markdown heading, so the run reports
`status=unreported`.** Class `process`. Non-gating.

`KN1b.result` carries `FACTORY-RESULT status=unreported exit_code=0` and
`FACTORY-NOTES result-misparse: ## FACTORY-RESULT`. The grammar
(`factory-task:516-518`) accepts only a bare line at column one; a `##` prefix is
a near-miss. Nothing substantive is lost — the driver derived the commits and
re-ran all three checks itself (`checks_verified_src: …=run`), and my independent
runs agree — but in a wave the key would read as unreported, and a gate has to
reconcile by hand. Worth one line of harness or prompt work, not a fix round.

**MINOR-3 — the runbook paragraph does not mention `--verbatim`.** Non-gating.

`docs/runbooks/session.md:494-502` (KN1's paragraph, carried unchanged) tells the
operator to run `rules.py validate docs/ledger/rules.toml --root .` and read the
`owed` count. It never mentions the arm this round adds, which is the guarantee
that makes the inventory trustworthy. The section did not ask for a runbook edit,
and `session.md` is in the union, so the seat could have and did not. One
sentence when someone next touches the file.

**Observation, not a defect — three rows cite a line the sentence *continues* on
rather than the line it starts on.** `R-practice-scratch-tmp` cites
`CLAUDE.md:46` for a sentence beginning on `:45`; `R-conv-commit-subject` cites
`:66` for one beginning on `:65`; `R-conv-never-copy-memory` cites `AGENTS.md:23`
for one beginning on `:22`. I found these by re-checking every row against a
window *starting at* its cited line, which is stricter than the validator: three
of 63 fail that and pass on the file. The cited line does carry the bulk of each
rule's words and the word check passes, so nothing is wrong; a future re-cite pass
may prefer the first line.

**Observation — `verbatim_errors` searches the whole file, not the cited line.**
`rules.py:147` tests `_flat(text) not in _flat(content)`, so a row can be verbatim
and mis-cited at the same time; only the weaker word check
(`rules.py:198-203`) guards the line number. This is what Interface 1 asks for
("byte-for-byte in its `source`"), and mutant **E** shows the word check does
catch a gross miscitation, so it is recorded rather than raised.

**Step 7 — what this could break that its checks do not cover.** One pass, four
questions, all measured.

*The new coupling, and it is real.* `evidence-unit`'s derivation now copies six
repo files it never read before, and the inventory's citations are line numbers.
So an edit anywhere in `CLAUDE.md`, `docs/brief.md`, `docs/board/policies.md`,
`docs/board/operator-model.md`, `docs/runbooks/session.md`,
`tools/orchestrator-guard.sh` or `pkgs/dsh-openrouter/hook-guard.py` that *shifts
lines* turns `evidence-unit` red in whatever unrelated task made the edit.
Measured rather than assumed — inserting two lines at the top of
`docs/board/policies.md` and rebuilding:

```
evidence-unit> E         Left contains 4 more items, first extra item: 'rules: R-policy-documentation: source line does not contain the rule text'
evidence-unit> FAILED tests/evidence/test_rules.py::test_shipped_inventory_validates
evidence-unit> 1 failed, 549 passed in 14.16s
```

All four `policies.md` rows go red at once. This is the guarantee working as
designed — a stale citation *should* be a red build, and the fix is to re-cite the
rows in the same commit — but it is a new standing obligation that no runbook line
states, and it lands on the orchestrator, who owns those files. Two mitigations
already limit the blast radius, and both are worth stating: the sandbox copies all
of `docs/board/` but the inventory cites only `policies.md` and
`operator-model.md`, so the everyday derived-queue-block regeneration of
`docs/OPERATIONS.md` and the board log can invalidate the derivation (a rebuild)
but cannot turn the check red; and a *wording* change that keeps the line number
fails just as loudly, which is the point. Recorded for the runbook, not gated.

*Anything else reading this data?* No. Outside the module, its test and the plan's
own prose, nothing in the tree names `rules.py` or `rules.toml` — `grep -rn` over
`*.py *.sh *.js *.nix *.bats *.md` finds only the plan sections, the runbook
paragraph and an unrelated `rules.toml` fixture inside
`tests/unit/85-task-class.bats`. There is no import to break and no consumer to
surprise; the increment-1 drill's command form is exercised above.

*The AGENTS.md hole.* Four rows cite `~/flakes/dsh-harness/AGENTS.md`, which is
outside the repo and therefore outside the sandbox; the test excludes it by name,
so those four rows are never verbatim-checked by any check. That is declared in
both the module docstring and the test comment, and it is the correct call — the
alternative is copying another flake's file into this one's build. On the host they
do resolve, and I checked all four are verbatim there. A named gap, not a defect.

*Checks outside the acceptance list.* `unit` (687 tests) and `factory-unit` are
green in the clone (table above) — `unit` being the check that has bitten this
factory before. `lint` covers the `flake.nix` edit's formatting and the `docs/MAP.md`
currency. Nothing in the diff touches a NixOS module, a service, a lane or a
credential path, so G1, G8 and G12 are untroubled: the change is a ledger, a
Python validator, its tests and eleven lines inside an existing check derivation,
all reviewable in the diff (invariant 5).

## Verdict

**APPROVED.**

KN1's blocker and all four majors are closed and each closure is counted, not
asserted: brief §8 is nine rows against nine bullets where it was zero,
`operator-model.md` is ten of ten with all six named lines present,
`policies.md` is four of four with the documentation and factory-economics
policies carried whole, every one of the 63 rows is byte-verbatim under an
`--verbatim` arm I ran and then broke (mutant **A**), and the fabricated
`command -v jq python3 bats` measurement is replaced by the packet's own §9.1
sentence with a line cite — with only three rows in the file stating a
measurement at all, all three the packet's. The sandbox minor is closed and
proved: a wrong `source` line now fails the build (mutant **E**) where it used to
be skipped. All three `acceptance` checks are green in a fresh clone under
`--rebuild` (`550 passed`, `59 passed`, `lint` exit 0), two further checks are
green, red before green reproduces independently and sharply — KN1's own rejected
data fails one test per guarantee at `3 failed, 547 passed` — all four named
mutants die, one commit, subject byte-identical at
`md5 3c94830cfeea6e174d13bc0da7131555`, both trailers in policy order with the
model from `KN1b.result`, and all six changed files sit inside the chain's
`touches` union.

It is approved with three recorded minors, none gating. The completeness
guarantee is pinned by source and not by rule, so a dropped policy row survives
the suite (mutant **F**) — the plan's `underspecified` defect, owed as one line.
The seat's result line was a markdown heading, so the run self-reported
`unreported`. And the runbook still does not mention the arm this round exists to
add.
