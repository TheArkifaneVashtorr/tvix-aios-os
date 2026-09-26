# The DeepSeek failure corpus — harness study (2026-09-07)

**Operator, 2026-09-07 (verbatim):** "the failures of the deepseek agents are
data points we need to redesign the harness around in order to improve their
performance."

**Corpus:** 95 seat runs — every ledger rejection (66), every hard failure
(9), and 20 approved controls — each read by a reader from the gate review,
the `.result` file and slices of the seat log. **Synthesis:** Fable 5.1, from
the readers' records only (no log was opened for the taxonomy or the
per-run table). **Skeptic round:** the draft spec's ten changes were each
read by three skeptics against the gate reviews, the harness source, the
`.result` files and log slices; their verdicts are §4 below. **Product:**
the spec `docs/superpowers/specs/2026-09-07-seat-harness-redesign-design.md`
— ten candidate changes drafted, three surviving the panel (2, 5, 9) — and
this report.

## 1. The taxonomy

Counts are runs (a tag appearing twice in one run counts once). A tag the
controls also show is a behaviour, not a cause; the last column says what the
control occurrences were.

| tag | rejected | failed | control | what the control occurrences are |
|---|---|---|---|---|
| untested-stated-arm | 45 | 0 | 3 | MINOR-level coverage gaps the gate recorded as not owed (T3b ×3, P3A, P11r) |
| guessed-an-ambiguity | 16 | 1 | 3 | resolved correctly and disclosed (T1b, P12) or a narrower-than-prose regex (P11r) |
| never-ran-named-mutants | 16 | 0 | 0 | — |
| followed-a-wrong-fact | 14 | 0 | 5 | a plan-dictated sentence the gate pinned on the plan (P4b, P3Ar3, P3Ar, P10b, P12) |
| out-of-touches-edit | 13 | 1 | 5 | sanctioned: `docs/MAP.md`, a prescribed cherry-pick, a disclosed forced file (T10a, P6b, P3Ar, P10b, P12) |
| fabricated-claim | 13 | 1 | 0 | — |
| one-arm-per-enum | 13 | 0 | 0 | — |
| test-cannot-fail | 11 | 0 | 1 | one dead assertion beside a live one (P2b MINOR-8) |
| ignored-section-item | 11 | 0 | 0 | — |
| checks-not-run-locally | 9 | 1 | 0 | — |
| no-red-green-in-body | 6 | 2 | 6 | readers used the tag both ways; in controls it marks an incomplete paste (T10a, P6b, T1b) or a positive note (P4b, P3Ar, CR2r3b) |
| ran-mutants-partially | 5 | 0 | 2 | VM mutants skipped for cost with a reason (SB4b); inference for legacy mutants the gate re-ran and confirmed (P4b) |
| misparsed-result-block | 3 | 0 | 0 | — |
| weakened-existing-assertion | 2 | 0 | 0 | — |
| board-or-plan-edit | 1 | 0 | 0 | — |
| provider-error | 0 | 5 | 0 | — |
| budget-or-timeout | 0 | 4 | 0 | — |
| other | 16 | 5 | 15 | in controls: positive process notes (self-caught staging, empirical probing, byte-exact subject extraction) |

**Zero-on-controls tags** (the causes): never-ran-named-mutants (16),
one-arm-per-enum (13), fabricated-claim (13), ignored-section-item (11),
checks-not-run-locally (9), misparsed-result-block (3),
weakened-existing-assertion (2). test-cannot-fail (11 vs 1) is next to them.

**Shared tags** (behaviours, not causes): followed-a-wrong-fact and
out-of-touches-edit each appear in 5 controls — in every control case the
fact came from the plan and the gate charged the plan, or the file was
sanctioned and disclosed. What separates the rejected occurrences is not
the behaviour but the *disclosure*: the rejected seats resolved the conflict
silently; the control seats wrote it into the commit body or the notes.

### The one process fact that separates the two populations

| `mutants_run` (from the readers' process block) | rejected (66) | failed (9) | control (20) |
|---|---|---|---|
| none | 41 | 6 | 0 |
| some | 15 | 2 | 6 |
| all-named | 8 | 1 | 13 |
| unknown | 2 | 0 | 1 |

No control ran zero mutants; 41 of 66 rejections did. `tests_first` and
`red_shown` do not separate them (61 of 66 rejected runs wrote tests first, 63 showed a red;
every control does): the rejected seats did TDD at the *module* level (the
red was often an ImportError) and never at the *assertion* level.

**Confound, stated:** the controls are almost all fix rounds (`b` suffix)
from plans written after P3A, whose sections carry named mutants; many
early rejected runs (a3–hr1, ev1–ev3, sc1) ran under sections that named
none. "Never ran named mutants" therefore mixes "the seat skipped them" with
"the section had none to run". The draft spec's change 1 proposed to make
them a committed artefact either way, which would have removed the confound
from the next measure; the panel refuted that change on all three lenses
(§4) and it is out. The confound stands until a mechanism for the mutant
class survives a panel (spec §7 Q7).

### Model and effort

| population | Pro medium | Pro high | Pro other/unknown | Flash off/n/a | unknown |
|---|---|---|---|---|---|
| rejected (66) | 38 | 11 | 9 | 6 | 2 |
| failed (9) | 5 | 0 | 1 | 3 | 0 |
| control (20) | 19 | 0 | 0 | 1 | 0 |

Flash: 6 rejected, 1 approved (pa11/P13, a docs task), 3 hard failures (two
UNKNOWN_MODEL launches, one truncated log). Pro high: 11 rejected, 0
controls — every one from the ev1/ev2/ev3/sc1 plans whose verbatim fixtures
were the gate's finding, so the effort is confounded with the plan era. Cost:
median wall 760 s (rejected) vs 912 s (control); median output tokens 63 k vs
89 k — the approved runs spent *more*, on mutants and pastes. The 66
rejections cost 18.3 h of seat wall and 4.76 M output tokens; the 9 failures
5.3 h and 0.87 M; the 20 controls 7.3 h and 1.88 M.

## 2. Method

- Each record was produced by a reader from three sources: the Opus gate
  review (`docs/reviews/*opus-review-<run>-<KEY>.md`), the `.result` file,
  and the seat log read in slices — the first 200 lines, a grep for process
  markers, the last 250 lines — never the whole log.
- Tags are the readers' vocabulary; the synthesis counted them per run and
  read the `detail` and `where` of every occurrence to classify control
  occurrences (the last column of the taxonomy table).
- The `process` block (tests_first, red_shown, mutants_run, checks_run,
  commit_count) is the readers' judgement from the same slices.
- Costs are the `.result`'s `wall_s` and `usage:` line; four runs have no
  cost (a4/N7c and b3/F9 have no result file; mcf's two launches died before
  a model call).
- **The skeptic round** (after the draft spec): each of the ten changes was
  given to three skeptics with one lens each. *Would-have-caught* took three
  of the change's claimed runs and re-read their gate reviews and log slices
  to ask whether the mechanism, as written, refuses or flags the run before
  the gate (bar: two of three uncaught refutes). *Implementable-and-honest*
  read the harness source (`tools/factory/seat/*`, `pkgs/evidence/*`) to ask
  whether the mechanism exists in bash without a model and whether its
  verdict rests on a driver-computed fact or on the seat's word.
  *False-positives-and-cost* replayed the rule over the 20 controls' landed
  commits (bar: more than two controls blocked, or seat work doubled for a
  class not caught). The skeptics did open logs, in the slices the study
  allows, and cite line numbers. Rules: two or three refutations drop the
  change; one keeps it with the amendment folded in; none keeps it.

### Gaps in the method

- **Slices, not logs.** A behaviour that lives in the middle of a 9,000-line
  log (a decision reversed, a mutant applied and reverted) is visible only
  when the marker grep hit it. `mutants_run` in particular is a lower
  bound: a seat that ran mutants without printing "mutant" reads as `none`.
- **Two runs had no log** (a4/N7c: no result, no log; b3/F9: no log, review
  only). Their process facts are inferred from the review and marked
  unknown. Five more logs are the seat's closing summary only (cr8/CR2 27
  lines, hr1/H2 29, pa4/P4 7, pa11/P13 22, tel3/T3M 28): every rule-related
  claim about them is from the review.
- **Tag drift between readers.** `no-red-green-in-body` was used for
  "no red shown", "red not pasted in the commit body", and (in three
  controls) as a positive note; `other` holds 36 distinct observations. The
  taxonomy's counts for those two tags are therefore soft; the zero-on-
  controls tags are not.
- **The plan-era confound** (above): rejected runs are spread over 2026-09-04
  to 09-07 and 20 plans; controls cluster on 09-06/07 fix rounds.
- **Rejection classes are the ledger's**, not re-derived: the readers'
  `outcome` field quotes the review's class where the review had one.
- **The gate is one reviewer.** Every "would have caught" in the records is
  the reader's judgement against what Opus in fact found; a mechanism scored
  as catching a run is one that refuses or surfaces the finding the review
  named, not a guarantee the seat would then have fixed it.

## 3. The change → runs matrix

Change numbers are the spec's §4 as drafted; they are kept as identifiers
after the panel so this table and the verdicts (§4) read across. The
"as drafted" column is the draft's claim; the "after the panel" column is
what the spec now claims — the corrected list for a surviving change, or
"dropped" with the refuting lenses for one in spec §5. A control listed
under "controls touched" gains a field or a first-commit refusal, never a
rejection.

| # | change (layer) | verdict | runs caught, as drafted | runs caught, after the panel | controls touched (no refusal) |
|---|---|---|---|---|---|
| 1 | named mutants as committed patches the driver executes (template · workspace · driver · result) | dropped — 3 of 3 refuted | ev2/E2, ev2/E2b, ev2/E7, ev3/E9, ev1/R1, sc1/G1, sc1/G10, pa5/P6, pa10/P10, rt1/RT1, rt2c/RT2, sb4/SB2, bk3/B1b, tel1b/T1, tel2/T2, tel2/T3, tel2/T1W, pb3arb2/P3Arb; plus the 16 never-ran runs by construction | — (four controls would demote: P3Ar3, P8b, P12, SB4b) | — |
| 2 | `touches` enforced by the driver; the commit hook as fast-fail (driver · workspace · integrator · result) | **kept** — 0 of 3 refuted | cr2/CR1, ev1/R5, cr20/CR2r3, tel1b/T1, tel2/T3, sb7/SB4 | cr2/CR1, ev1/R5, cr20/CR2r3, tel1b/T1, tel2/T3 (sb7/SB4 dropped: 0 commits, empty diff) | pa2/P12, pb10/P10b (clean under prefix matching and lenient disclosure); pb6/P6b, tel3/T10a, pb3ar/P3Ar inside the rule |
| 3 | one test per enum arm, grepped by the driver (template · driver) | dropped — 2 of 3 refuted | tel1b/T1, tel2/T2, ev2/E7b, sc1/G1, rt2c/RT2, sc5/G11b, cr8/CR2, cr15/CR2r, og3/OG1r, og4/OG1r2, cr19/CR2r2b, cr20/CR2r3 | — | — |
| 4 | `FACTORY-DEVIATION` lines; `partial` as the honest stop (rules text · result · driver · gate brief) | dropped — 3 of 3 refuted | b2/F6, fd1/FD1, pb3a/P3Ab, pb3ar2/P3Ar2, pb3ar2b/P3Ar2b, sc5/G11, sc1/G5, mcf2/P1flash, rt8/RT5rb, sb7/SB4, a3/W2-N6b, pa9/P8, cr20/CR2r3 | — (≥ 10 controls would demote) | — |
| 5 | the driver verifies checks and probes it can reproduce (driver · result · template · integrator) | **kept** — 1 of 3 refuted (would-have-caught), amended | pb11/P11b, hr1/H2, pa4/P4, pb3a/P3Ab, cr17/CR2rb, cr18/CR2r2, cr19/CR2r2b, og4/OG1r2, pa6/P2, cr2/CR1, rt1/RT1, b3/F9 | pb11/P11b (checks-misreported); hr1/H2 (checks-unverifiable, with the total table); pa4/P4, og4/OG1r2, pb3a/P3Ab, pa6/P2 (plan-stated bounds, under `env -u FACTORY_RUN`, with `probe-missing`) | pa8/P5 (honest fail, recorded), pb4/P4b (probe reproduces under the normalised env), pb3ar/P3Ar, pb10/P10b (`drift`) |
| 6 | green-on-base (driver · result) | dropped — 3 of 3 refuted | mcp2/P3, ev1/R8, pb3arb2/P3Arb, pa9/P8, sc1/G5, sc1/G10, ev2/E2 (in part) | — (P3A, P3Ar, P3Ar3 would demote) | — |
| 7 | guard/parser classes carry a sweep fixture that must grow (template · workspace check) | dropped — 2 of 3 refuted | og1/OG1, og1/OG1b, og3/OG1r, og4/OG1r2, cr8/CR2, cr15/CR2r, cr17/CR2rb, cr18/CR2r2, cr19/CR2r2b, rt5/RT5, rt5/RT5b, sb5/SB2b | — | — |
| 8 | the commit-msg hook: subject, trailers, the red paste (workspace) | dropped — 2 of 3 refuted | sc1/G2, tel3/T3M, tel2/T1W, pa6/P2 | — (seven controls would be refused on the paste arm) | — |
| 9 | a result block the driver can always complete: `unreported` (driver · rules text · wave · fence) | **kept** — 1 of 3 refuted (would-have-caught), re-titled a ledger fix | a2/N7, rt8/RT5rb, cr18/CR2r2, cr19/CR2r2b, cr15/CR2r, pb3ar2b/P3Ar2b | a2/N7, rt8/RT5rb (the absent line was the only defect; both later approved); cr15/CR2r, cr18/CR2r2, cr19/CR2r2b recorded honestly, their MAJORs still the gate's (pb3ar2b/P3Ar2b dropped: it emitted `status=done`) | — |
| 10 | routing: no row change (routing) | dropped — 2 of 3 refuted | (observation only: cr8/CR2, pa4/P4) | — (an observation catches nothing; guard-class n = 1) | — |

**Not caught by any surviving change** (and why): the mutant, enum-arm and
section-item classes in full — ev1/R1, ev2/E2, ev2/E2b, ev2/E7, ev2/E7b,
ev3/E6, ev3/E9, sc1/G1, sc1/G10, pa5/P6, pa10/P10, rt1/RT1, rt2c/RT2,
sb4/SB2, bk3/B1b, tel2/T2, tel2/T1W, pb3arb2/P3Arb, a7/N16 (draft change 1
and 3, refuted: the seat authored the artefact judged, the grep proved
presence not coverage); the silently-resolved ambiguities — b2/F6, fd1/FD1,
pb3ar2/P3Ar2, pb3ar2b/P3Ar2b, sc5/G11, sc1/G5, mcf2/P1flash, a3/W2-N6b,
pa9/P8 (draft change 4, refuted: no oracle for the seat's word and ≥ 10
controls demoted); the guard-spelling chain — og1/OG1, og1/OG1b, og3/OG1r,
og4/OG1r2 (probe only), cr8/CR2, cr15/CR2r, cr17/CR2rb, rt5/RT5, rt5/RT5b,
sb5/SB2b (draft change 7, refuted: the sweep asserts non-crash, not
verdicts); the message-shape runs — sc1/G2, tel3/T3M, tel2/T1W (draft
change 8, refuted on the paste arm; the subject and trailer arms are a
second-spec candidate as a driver check); mcp2/P3 (draft change 6); and,
as before, a9/N19 (a 404 URL cited as fact — a plan-side lint), a4/N7c (no
log), cr6/CR3, sc8/G12b, sc5/G12, oi1/DA1 (underspecified contracts the
gate alone judges), cr11/CR2b, mcf/P1flash, mcf/P2flash, pb3arb/P3Arb,
sc3/G8 (provider and launch errors — the telemetry relaunch table), cr10/CR2b
(a truncated log).

Distinct rejected/failed runs caught by at least one surviving change: 16
of 75 — 11 refused or surfaced before the gate (change 2: 5; change 5: 6),
5 recorded honestly instead of as `failed`/0 commits (change 9). The draft
claimed 60 of 75. The difference is the panel's finding: most of the
draft's reach rested on mechanisms whose verdict the seat could author or
that demoted approved controls.

## 4. The verdicts

Thirty verdicts, three lenses per change. One line of evidence each; the
full text with every citation is the panel's JSON, held with the spec's
review record. Line numbers are into the gate review named by run unless a
file is given.

| change | lens | refuted | evidence (one line) |
|---|---|---|---|
| 1 | would-have-caught | yes | pb11/P11b's 22 named mutants all died (review :18) yet two MAJORs rejected it, one hidden by the devShell-not-nix runner (:304,312-314); cr2/CR1 was rejected on real-data defects (:18); a7/N16's majors need fixtures never written — 3 of 3 uncaught. |
| 1 | implementable-and-honest | yes | The driver checks that *a* patch dies, not that it is the named mutant — pb3arb2/P3Arb's self-authored red (P3Arb.log:714-720); the `FACTORY-DEVIATION` escape lifts the demotion on the seat's word; "≤ 20 per task" against tel1b/T1's 54 named. |
| 1 | false-positives-and-cost | yes | Four approved controls demote: pb3ar3/P3Ar3 M3 survived (:288), pb8/P8b 1 of 20 (:276), pa2/P12 4 of 8 killed (:217), sb8/SB4b's VM mutants unrunnable by the devShell runner (:266-269; one VM kill took 900 s). |
| 2 | would-have-caught | no | cr2/CR1, ev1/R5, cr20/CR2r3: each one commit with one undisclosed extra file, refused by a `--cached --name-only` hook hours before the gate; sb7/SB4 has no commit (SB4.result:18-22) and is unreachable. |
| 2 | implementable-and-honest | no | `tasks.py:44,173` parses touches; `factory-task:284-309` already recomputes over `base..task/<KEY>` and demotes; `factory-integrate:93-98` already refuses by path; `touches-violation` missing from `ERROR_CLASSES` (`streams.py:120-131`). |
| 2 | false-positives-and-cost | no | Replayed over 20 landed commits: 18 clean; pa2/P12 (prose disclosure, not the literal token) and pb10/P10b (a directory entry over nine files) refused only under strict matching — both fixed by wording; cost ms. |
| 3 | would-have-caught | yes | ev2/E7b's test delta holds the literal `fail` in a test name and a comment while no test drives the arm (:38,48); sc1/G1's arm literals are all present and the defect is rule interaction; cr8/CR2's arms are spellings the section never knew. |
| 3 | implementable-and-honest | yes | A substring check (`80-seat-driver.bats` has `fail` 11×, `ok` 31×); the teeth are change 1's seat-authored patches; og3, og4, cr20, sc5/G11b and sc1/G1's defects have no arm literal to grep. |
| 3 | false-positives-and-cost | no | 0 of 20 controls blocked; but tel3/T10a passes the grep with both `task-result`/`gate-verdict` arms untested (review MINOR-2) — presence is not coverage. |
| 4 | would-have-caught | yes | a3/W2-N6b fires no trigger (log:845: all three files in touches); rt8/RT5rb wrote the deviation in prose, emitted no block (0 of 8,372 lines) and was APPROVED; sc1/G5 fires on a forced edit the gate accepted (:140,180) and misses the vacuous guard (:25-27). |
| 4 | implementable-and-honest | yes | The rule already stands in every plan's Global Constraints (`seat-driver.md:28`); pa9/P8 recited it and reported one deviation of two (:310); no oracle for `fact`/`unreachable`/`scope`; the driver has no machine-readable touches parser. |
| 4 | false-positives-and-cost | yes | ≥ 10 controls demote — pa1/P1 (:195-196), pb8/P8b (:389-397), pb6/P6b (:487), pb4/P4b, pa7/P3A, cr21/CR2r3b, pa8/P5 and the four the draft conceded; `docs/MAP.md` and the queue block are outside touches on nearly every commit. |
| 5 | would-have-caught | yes | pb11/P11b caught (unit red at the rev, :314); pa4/P4's probe prints 0 under `FACTORY_RUN` (`session-start.sh:18`) so the driver would pass it; hr1/H2's `pre-commit=pass` is `not-run`, which the draft did not demote. |
| 5 | implementable-and-honest | no | `factory-integrate:126-176` already runs checks by rev and records via `factory_record_check`; `factory-task:286-300` already demotes a mismatched claim; cr2/CR1 shows a seat can edit the check itself (`flake.nix`) — hence `checks_scope`. |
| 5 | false-positives-and-cost | no | 0 of 20 controls demote on checks (every pass re-run green by the gate); pb4/P4b's honest probe reads 0 under `FACTORY_RUN` (P4b.log:3260-3276) — fixed by `env -u`; VM checks 15–40 min (SB4b.log:1991) — deferred. |
| 6 | would-have-caught | yes | mcp2/P3 caught (:110); sc1/G5's vacuous guard is a `flake.nix` shell line with no test to list; ev1/R8's deny test was red on base and its masked regex arm (:43) is invisible. |
| 6 | implementable-and-honest | yes | Four of seven claimed catches are red on base by their own reviews (E2 `StopIteration`, R8, G1, G10); "fork point" undefined for cherry-pick fix rounds — tel2f2/T2b's test-only round is green on base by construction (:20-21); `runCommand` checks have no per-test rows. |
| 6 | false-positives-and-cost | yes | Three approved controls demote — pa7/P3A (:289-291), pb3ar/P3Ar (:348-354), pb3ar3/P3Ar3 (:358-362, a skip); no `.result` has ever carried `FACTORY-DEVIATION`; a `seat-vm` base run is 15–40 min. |
| 7 | would-have-caught | yes | The sweep carries no verdicts — `91-orchestrator-guard.bats:1405` asserts stderr-silence only; six of cr8/CR2's ALLOWed spellings are already rows; og1/OG1b dropped the `--work-tree` row the task named (:168-172); sb5/SB2b is an octet range. |
| 7 | implementable-and-honest | yes | `91-orchestrator-guard-sweep.txt` has 0 `deny`/`allow` rows and stdout is discarded (:1425-1426); row-count growth is satisfiable by filler; rt5/RT5b (RecursionError), cr19/CR2r2b (injected fault), sb5/SB2b are not spellings. |
| 7 | false-positives-and-cost | no | One control in the class (cr21/CR2r3b, `3939c87`, created the fixture whole); 442 rows run in ~9 s; a class-wide "must grow" forces fault-containment rounds to manufacture rows. |
| 8 | would-have-caught | no | sc1/G2 (:58), tel3/T3M (:169-174), tel2/T1W (:303-308) fire; pa6/P2's MAJOR-3 is two probe numbers no arm tests (:305-309); only T3M's rejection is averted outright. |
| 8 | implementable-and-honest | yes | The hook lives in the seat's writable clone (`flake.nix:760`; `--no-verify`) with no driver re-check; the paste arm checks the shape of seat-authored text — T1b, P11r, T3b pasted wrong numbers in the right shape. |
| 8 | false-positives-and-cost | yes | 0 of 22 seat commits are fenced; six approved controls have prose-only bodies (`0acdb9d`, `3939c87`, `aa7cf18`, `f068ca5`, `7748ee9`, `d26333f`) plus T10a — seven refusals against a bar of two. |
| 9 | would-have-caught | yes | pb3ar2b/P3Ar2b emitted `status=done` (log:3888; result:1-3) — the arm cannot fire; cr15/CR2r is relabelled on a run rejected on four MAJORs; rt8/RT5rb is a real ledger fix but was gated and APPROVED anyway. |
| 9 | implementable-and-honest | no | One `if` in `factory-task` (repo :254-272; live :134-139) with `base_sha` computed below it; five `.result` files assert 0 commits on line 3 and name the commit on line 18-19; `task_rc` for `unreported` unspecified. |
| 9 | false-positives-and-cost | no | Every control emitted a parseable block, so the arm never fires; ~40 tokens; part (a) is a wrong fact — the rule is already last (`factory-brief:96-100`), REPO NOTES follows it (:114-115). |
| 10 | would-have-caught | yes | "Mechanism: none in this spec"; cr8/CR2 and pa4/P4 reach the gate byte-identically; pa4/P4 is a hook/budget task, so guard-class Flash-off is n = 1. |
| 10 | implementable-and-honest | yes | `routing.toml`'s header carries no "commit citing a report line" rule; `report ladder` does not exist (`report.py:263-268` has only `plans`); both runs' own `harness_gaps` credit other layers. |
| 10 | false-positives-and-cost | no | 0 controls touched, 0 seat cost; pa11/P13 (the one approved Flash-off control) is spared by the restraint the change takes. |

Tally: 1 (3), 3 (2), 4 (3), 6 (3), 7 (2), 8 (2), 10 (2) dropped; 5 (1) and
9 (1) kept and amended; 2 (0) kept with its wrong fact (sb7/SB4) corrected.
Twelve of the thirty verdicts rest on a control the draft had not replayed;
the second spec (spec §7 Q6) makes the 20-control replay part of the draft.

## 5. The per-run table

| run | key | kind | model | effort | outcome | tags | mutants | wall_s | in | out |
|---|---|---|---|---|---|---|---|---|---|---|
| a3 | W2-N6b | rejected | pro | medium | REJECTED missing-case | untested-stated-arm, out-of-touches-edit, other | none | 754 | 155248 | 43661 |
| a4 | N7c | rejected | unknown | unknown | REJECTED missing-case | other×2, out-of-touches-edit, untested-stated-arm | unknown | 0 | 0 | 0 |
| a7 | N16 | rejected | pro | n/a | REJECTED wrong-fact | followed-a-wrong-fact, untested-stated-arm, never-ran-named-mutants | some | 742 | 910805 | 73654 |
| a9 | N19 | rejected | pro | unknown | REJECTED wrong-fact | fabricated-claim, followed-a-wrong-fact | none | 515 | 435750 | 42817 |
| b3 | F9/BFIX | rejected | pro | unknown | REJECTED missing-case | untested-stated-arm, ran-mutants-partially, other×3, out-of-touches-edit, checks-not-run-locally | all-named | 0 | 0 | 0 |
| b2 | F6 | rejected | pro | S | REJECTED wrong-fact | followed-a-wrong-fact, test-cannot-fail, guessed-an-ambiguity | none | 1845 | 652776 | 115030 |
| cr2 | CR1 | rejected | pro | medium | REJECTED missing-case | untested-stated-arm, other×2, ignored-section-item×2, out-of-touches-edit, never-ran-named-mutants | none | 892 | 393158 | 85631 |
| cr6 | CR3 | rejected | pro | medium | REJECTED underspecified | untested-stated-arm, other, guessed-an-ambiguity, test-cannot-fail, out-of-touches-edit | none | 562 | 200960 | 50345 |
| cr8 | CR2 | rejected | flash | off | REJECTED missing-case | one-arm-per-enum, fabricated-claim, untested-stated-arm, board-or-plan-edit | none | 498 | 176439 | 23303 |
| cr15 | CR2r | rejected | pro | medium | REJECTED missing-case | untested-stated-arm×4, one-arm-per-enum, misparsed-result-block, other | some | 1678 | 883674 | 163640 |
| ev1 | R1 | rejected | pro | high | REJECTED vacuous | untested-stated-arm×2 | none | 772 | 622227 | 43679 |
| ev1 | R5 | rejected | pro | high | REJECTED missing-case | ignored-section-item, followed-a-wrong-fact, out-of-touches-edit | none | 950 | 871683 | 41238 |
| ev1 | R8 | rejected | pro | high | REJECTED vacuous | untested-stated-arm×3, no-red-green-in-body | none | 432 | 272024 | 17684 |
| ev2 | E2 | rejected | pro | high | REJECTED vacuous | test-cannot-fail, guessed-an-ambiguity, ignored-section-item, other | none | 214 | 239349 | 17178 |
| ev2 | E2b | rejected | pro | high | REJECTED vacuous | followed-a-wrong-fact×2, ran-mutants-partially | some | 240 | 313157 | 15772 |
| ev2 | E7 | rejected | pro | high | REJECTED vacuous | one-arm-per-enum, untested-stated-arm, checks-not-run-locally | none | 137 | 108181 | 8670 |
| ev2 | E7b | rejected | pro | high | REJECTED vacuous | one-arm-per-enum, untested-stated-arm×2 | some | 361 | 198377 | 34251 |
| ev3 | E6 | rejected | pro | medium | REJECTED vacuous | followed-a-wrong-fact, never-ran-named-mutants | none | 220 | 323277 | 14319 |
| ev3 | E9 | rejected | pro | high | REJECTED vacuous | test-cannot-fail, never-ran-named-mutants, untested-stated-arm, guessed-an-ambiguity | none | 370 | 538061 | 28427 |
| ev3 | R3r | rejected | pro | high | REJECTED missing-case | untested-stated-arm, fabricated-claim | all-named | 264 | 221074 | 10248 |
| fd1 | FD1 | rejected | pro | medium | REJECTED wrong-fact | followed-a-wrong-fact, other, untested-stated-arm, checks-not-run-locally | none | 1504 | 981579 | 138023 |
| hr1 | H2 | rejected | flash | off | REJECTED wrong-fact | followed-a-wrong-fact, fabricated-claim, other, checks-not-run-locally | none | 234 | 148126 | 19919 |
| mcf2 | P1flash | rejected | flash | off | REJECTED wrong-fact | guessed-an-ambiguity, ignored-section-item, other | none | 180 | 71951 | 13504 |
| mcp2 | P3 | rejected | pro | n/a | REJECTED vacuous | test-cannot-fail, untested-stated-arm, no-red-green-in-body | none | 469 | 197631 | 31435 |
| og1 | OG1 | rejected | pro | medium | REJECTED missing-case | guessed-an-ambiguity, untested-stated-arm, never-ran-named-mutants | none | 1458 | 1162272 | 126817 |
| og1 | OG1b | rejected | pro | medium | REJECTED underspecified | ignored-section-item, untested-stated-arm, fabricated-claim | some | 1375 | 1079961 | 91583 |
| og3 | OG1r | rejected | pro | medium | REJECTED underspecified | untested-stated-arm, one-arm-per-enum, ignored-section-item, other | some | 981 | 1017479 | 101838 |
| og4 | OG1r2 | rejected | unknown | medium | REJECTED missing-case | untested-stated-arm, one-arm-per-enum, guessed-an-ambiguity, fabricated-claim, test-cannot-fail | all-named | 1389 | 687368 | 140152 |
| rt1 | RT1 | rejected | pro | unknown | REJECTED vacuous | untested-stated-arm×3, checks-not-run-locally | none | 1456 | 567493 | 142283 |
| rt2c | RT2 | rejected | pro | medium | REJECTED vacuous | untested-stated-arm, one-arm-per-enum, fabricated-claim | some | 556 | 343979 | 58020 |
| rt5 | RT5 | rejected | pro | medium | REJECTED missing-case | untested-stated-arm×2 | none | 742 | 511428 | 44569 |
| rt5 | RT5b | rejected | pro | medium | REJECTED underspecified | untested-stated-arm, ran-mutants-partially | some | 1007 | 534268 | 61578 |
| sb1 | SB3 | rejected | pro | medium | REJECTED underspecified | untested-stated-arm×2, ran-mutants-partially | some | 846 | 565206 | 42135 |
| sb4 | SB2 | rejected | pro | medium | REJECTED vacuous | untested-stated-arm, guessed-an-ambiguity | some | 852 | 464887 | 79276 |
| sb5 | SB2b | rejected | pro | medium | REJECTED missing-case | untested-stated-arm | all-named | 1147 | 770555 | 84555 |
| sc1 | G1 | rejected | pro | high | REJECTED vacuous | one-arm-per-enum, untested-stated-arm, ignored-section-item, never-ran-named-mutants | none | 492 | 324916 | 37601 |
| sc1 | G2 | rejected | pro | high | REJECTED process/vacuous | guessed-an-ambiguity, untested-stated-arm | none | 266 | 192988 | 23268 |
| sc1 | G5 | rejected | pro | n/a | REJECTED underspecified | followed-a-wrong-fact, untested-stated-arm, no-red-green-in-body | none | 557 | 438160 | 37855 |
| sc1 | G10 | rejected | pro | n/a | REJECTED vacuous | untested-stated-arm, never-ran-named-mutants | none | 685 | 209102 | 26932 |
| sc4 | G8b | rejected | pro | medium | REJECTED underspecified | fabricated-claim, untested-stated-arm×2 | none | 688 | 368700 | 65385 |
| sc5 | G11 | rejected | pro | medium | REJECTED missing-case | untested-stated-arm, out-of-touches-edit, weakened-existing-assertion, fabricated-claim | none | 785 | 643279 | 55905 |
| sc5 | G11b | rejected | pro | medium | REJECTED missing-case | untested-stated-arm, one-arm-per-enum, followed-a-wrong-fact | some | 1193 | 745543 | 103210 |
| sc8 | G12b | rejected | pro | medium | REJECTED underspecified | guessed-an-ambiguity | none | 718 | 546635 | 70147 |
| sc5 | G12 | rejected | pro | medium | REJECTED missing-case | guessed-an-ambiguity, test-cannot-fail, other | all-named | 607 | 625816 | 66328 |
| oi1 | DA1 | rejected | pro | unknown | REJECTED missing-case (privacy) | guessed-an-ambiguity | none | 252 | 264046 | 19738 |
| cr17 | CR2rb | rejected | pro | medium | REJECTED missing-case | untested-stated-arm, fabricated-claim, never-ran-named-mutants | none | 2086 | 1256159 | 214196 |
| bk3 | B1b | rejected | flash | off | REJECTED vacuous | test-cannot-fail, fabricated-claim | some | 335 | 134193 | 18750 |
| cr18 | CR2r2 | rejected | pro | medium | REJECTED missing-case | untested-stated-arm, never-ran-named-mutants, fabricated-claim, other | none | 2235 | 995804 | 221102 |
| cr19 | CR2r2b | rejected | pro | medium | REJECTED implementer | one-arm-per-enum, ran-mutants-partially, misparsed-result-block, other | some | 1548 | 949580 | 138901 |
| pa4 | P4 | rejected | flash | off | REJECTED wrong-size | checks-not-run-locally, followed-a-wrong-fact | unknown | 325 | 154064 | 19786 |
| pa5 | P6 | rejected | pro | medium | REJECTED missing-case | never-ran-named-mutants, other | none | 508 | 330865 | 61227 |
| pa3 | P11 | rejected | pro | medium | REJECTED missing-case | out-of-touches-edit, guessed-an-ambiguity, checks-not-run-locally | none | 919 | 554392 | 98184 |
| cr20 | CR2r3 | rejected | pro | medium | REJECTED missing-case | untested-stated-arm, out-of-touches-edit, one-arm-per-enum | all-named | 1472 | 1284106 | 124527 |
| pa6 | P2 | rejected | pro | medium | REJECTED missing-case | ignored-section-item, untested-stated-arm, out-of-touches-edit, checks-not-run-locally | none | 1345 | 704576 | 129916 |
| pa10 | P10 | rejected | pro | medium | REJECTED implementer/wrong-fact | untested-stated-arm×2, never-ran-named-mutants | none | 831 | 552401 | 113586 |
| pb3a | P3Ab | rejected | pro | medium | REJECTED wrong-fact | followed-a-wrong-fact, fabricated-claim, never-ran-named-mutants | none | 793 | 360756 | 94900 |
| pa9 | P8 | rejected | pro | medium | REJECTED missing-case | test-cannot-fail, never-ran-named-mutants, ignored-section-item | none | 767 | 434030 | 76527 |
| pb3arb2 | P3Arb | rejected | pro | medium | REJECTED wrong-fact | test-cannot-fail, no-red-green-in-body, never-ran-named-mutants | none | 540 | 315423 | 51018 |
| pb3ar2 | P3Ar2 | rejected | pro | medium | REJECTED implementer | guessed-an-ambiguity, untested-stated-arm, other | some | 655 | 602222 | 80355 |
| pb3ar2b | P3Ar2b | rejected | pro | medium | REJECTED wrong-fact | guessed-an-ambiguity, untested-stated-arm, misparsed-result-block | all-named | 803 | 602002 | 93991 |
| pb11 | P11b | rejected | pro | medium | REJECTED implementer | checks-not-run-locally, out-of-touches-edit, untested-stated-arm, never-ran-named-mutants | none | 769 | 477584 | 89839 |
| tel1b | T1 | rejected | pro | medium | REJECTED missing-case | one-arm-per-enum, test-cannot-fail, guessed-an-ambiguity, followed-a-wrong-fact, out-of-touches-edit | none | 1512 | 1091340 | 167755 |
| tel2 | T1W | rejected | pro | medium | REJECTED implementer/vacuous | untested-stated-arm, followed-a-wrong-fact, no-red-green-in-body | none | 4285 | 3909505 | 91643 |
| tel2 | T3 | rejected | pro | medium | REJECTED implementer/vacuous | out-of-touches-edit, weakened-existing-assertion, never-ran-named-mutants, untested-stated-arm | none | 7590 | 4004859 | 237613 |
| tel2 | T2 | rejected | pro | medium | REJECTED missing-case | untested-stated-arm, ignored-section-item, one-arm-per-enum | some | 4572 | 2587249 | 117402 |
| tel3 | T3M | rejected | flash | off | REJECTED implementer | ignored-section-item, no-red-green-in-body | all-named | 125 | 73940 | 5834 |
| a2 | N7 | failed | pro | medium | failed no-result-line (real commit) | other | none | 2188 | 609663 | 129663 |
| cr10 | CR2b | failed | flash | off | failed no-result-line, 0 commits | fabricated-claim, budget-or-timeout, no-red-green-in-body | none | 1340 | 313541 | 76538 |
| cr11 | CR2b | failed | pro | medium | failed provider 402 | provider-error, budget-or-timeout | all-named | 980 | 502639 | 95367 |
| mcf | P1flash | failed | flash | n/a | failed UNKNOWN_MODEL | provider-error | none | 1 | 0 | 0 |
| mcf | P2flash | failed | flash | n/a | failed UNKNOWN_MODEL | provider-error | none | 0 | 0 | 0 |
| pb3arb | P3Arb | failed | pro | medium | failed provider error | provider-error, other | some | 425 | 262202 | 51145 |
| rt8 | RT5rb | failed | pro | medium | failed no-result-line (real commit) | other, guessed-an-ambiguity, budget-or-timeout | some | 2189 | 1074584 | 186684 |
| sb7 | SB4 | failed | pro | medium | failed no-result-line, 0 commits | out-of-touches-edit, budget-or-timeout, other, no-red-green-in-body | none | 10404 | 4062114 | 170084 |
| sc3 | G8 | failed | pro | n/a | failed provider error, 0 commits | other, checks-not-run-locally, provider-error | none | 1382 | 587213 | 158909 |
| tel3 | T10a | control | pro | medium | APPROVED | out-of-touches-edit, other, no-red-green-in-body | all-named | 817 | 638383 | 29689 |
| tel2f2 | T2b | control | pro | medium | APPROVED | (none) | all-named | 1125 | 96421 | 25308 |
| tel2f | T3b | control | pro | medium | APPROVED | other×2, untested-stated-arm×3 | all-named | 3954 | 238007 | 88185 |
| tel2f | T1Wb | control | pro | medium | APPROVED | other×3 | all-named | 2740 | 158633 | 66104 |
| tel1bf | T1b | control | pro | medium | APPROVED | guessed-an-ambiguity, no-red-green-in-body, other | all-named | 3604 | 226350 | 92420 |
| sb8 | SB4b | control | pro | medium | APPROVED | ran-mutants-partially, other | some | 707 | 544158 | 73892 |
| pb8 | P8b | control | pro | medium | APPROVED | other×2 | some | 859 | 761808 | 78348 |
| pb6 | P6b | control | pro | medium | APPROVED | out-of-touches-edit, other, no-red-green-in-body | all-named | 798 | 544163 | 79782 |
| pb4 | P4b | control | pro | medium | APPROVED | ran-mutants-partially, followed-a-wrong-fact, no-red-green-in-body | some | 733 | 366976 | 79491 |
| pb3ar3 | P3Ar3 | control | pro | medium | APPROVED | followed-a-wrong-fact, other×2 | some | 341 | 256408 | 39131 |
| pb3ar | P3Ar | control | pro | medium | APPROVED | no-red-green-in-body, followed-a-wrong-fact, out-of-touches-edit, other | all-named | 846 | 427491 | 89185 |
| pb2 | P2b | control | pro | medium | APPROVED | test-cannot-fail, other×2 | some | 965 | 369804 | 104217 |
| pb11r | P11r | control | pro | medium | APPROVED | other×4, guessed-an-ambiguity, untested-stated-arm | all-named | 1042 | 423322 | 101941 |
| pb10 | P10b | control | pro | medium | APPROVED | out-of-touches-edit, followed-a-wrong-fact, other | all-named | 828 | 645807 | 100747 |
| pa8 | P5 | control | pro | medium | APPROVED | (none) | all-named | 1101 | 776895 | 141646 |
| pa7 | P3A | control | pro | medium | APPROVED | untested-stated-arm, other×3 | all-named | 725 | 138812 | 100868 |
| pa2 | P12 | control | pro | medium | APPROVED | out-of-touches-edit, guessed-an-ambiguity, followed-a-wrong-fact, other×2 | some | 1284 | 368413 | 141376 |
| pa11 | P13 | control | flash | off | APPROVED | (none) | unknown | 349 | 156789 | 24622 |
| pa1 | P1 | control | pro | medium | APPROVED | (none) | all-named | 1081 | 577957 | 140521 |
| cr21 | CR2r3b | control | pro | medium | APPROVED | no-red-green-in-body, other×3 | all-named | 2240 | 1292841 | 283691 |

Column notes: `model` is the `.result`'s model (pro = deepseek-v4-pro-0813,
flash = deepseek-v4-flash; unknown where no result exists or the reader
could not recover it); `effort` is the reader's field verbatim (n/a and
unknown where the result carried none); `tags` are the readers' behaviour
tags with a multiplier where one run carried the tag more than once;
`mutants` is the readers' `process.mutants_run`; `in`/`out` are input and
output tokens from `usage:`; a zero cost row is a run with no result file.

## 6. What the corpus says in one paragraph

The rejected seats are not lazy and not wrong about the code more often
than the approved ones: 63 of 66 showed a red, 59 ran every acceptance
check, 64 made exactly one commit. They are rejected for what happens
*between* the red and the commit — the arm they did not test, the mutant
they reasoned about instead of running, the claim they wrote instead of
measuring, the conflict they resolved instead of reporting. The draft spec
claimed every one of those is a step the driver can verify without a
stronger model. The panel tested that sentence clause by clause: the
touches list the driver diffs, the check it re-runs and the probe it
re-measures survived, because their verdict comes from git and the driver's
own runs; the mutant as a patch and the deviation line did not, because the
seat authored the artefact being judged and the driver could verify only
its shape — and both demoted approved controls. The spec now makes the
three verified steps the floor; the mutant class, 41 of 66 rejections,
is owed a mechanism whose patch the driver derives and whose verdict the
gate reads, drafted with the 20-control replay in hand (spec §7 Q6–Q7).
