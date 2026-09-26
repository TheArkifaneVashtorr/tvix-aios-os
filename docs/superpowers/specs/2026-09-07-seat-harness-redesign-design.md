# The seat harness redesigned around the DeepSeek failure corpus — design (spec for review, 2026-09-07, revised on the skeptic panel)

## §1 Header

**Date:** 2026-09-07 (draft), revised the same day on the skeptic panel's
verdicts. **Authority:** the operator's direction of 2026-09-07, verbatim:
"the failures of the deepseek agents are data points we need to redesign the
harness around in order to improve their performance."
**Evidence:** the 95-run corpus read for this study — every ledger rejection
(66), every hard failure (9) and 20 approved controls — with its taxonomy,
per-run table and the panel's verdicts in
`docs/reviews/harness-study/2026-09-07-deepseek-failure-corpus.md`.
**The panel:** three Opus skeptics per drafted change — *would-have-caught*,
*implementable-and-honest*, *false-positives-and-cost* — with the bars,
the thirty verdicts and their evidence in the report's §4; two or three
refutations drop a change to §5, one keeps it amended.
**Result:** three of ten survive — changes 2, 5 and 9 (the draft's
numbers, kept so the report's tables read across).
**Approved by the operator 2026-09-07 ~15:35 ("approved"), with §7's
defaults.**
**Fits:** the seat-driver spec (`2026-09-06-operator-seat-driver-design.md`,
SD1–SD11); every surviving change is a mechanism the driver, the result
block or the seat's workspace carries. Where it and the seat-driver plan
disagree, a `<KEY>` section amends the plan.

## §2 Goal

A DeepSeek seat's rejection is caught in its own workspace, by a mechanism
the driver verifies from git and its own runs — never from the seat's
report — before the commit is offered to the Opus gate, and the mechanism
refuses nothing the 20 approved controls did. The corpus says where the
rejections come from: 41 of 66 rejected runs never executed a named mutant
(0 of 20 controls); 13 tested one arm of an enum (0 controls); 11 ignored a
stated section item (0 controls); 13 made a claim the gate could not
reproduce (0 controls); 9 reported a check they never ran or misreported
(0 controls). Those are harness gaps, not model gaps: the controls are the
same model at the same effort (19 of 20 Pro medium).

The panel's finding narrows what this spec can honestly claim. The three
surviving mechanisms reach the undisclosed-file, misreported-check and
lost-result-block classes — 16 of the 75 rejected or failed runs (11
refused or surfaced before the gate, 5 recorded honestly instead of as
failures). The largest class — the mutant never run, the arm never tested,
the section item silently resolved — is *not* reached by anything that
survived, because every draft mechanism for it either judged an artefact
the seat itself authored or demoted approved controls. That class is the
open item of §7 Q7, owed a second spec, not a weaker rule here.

## §3 Invariants kept

1. **Build-only.** Nothing here runs `sudo`, `nixos-rebuild`, `systemctl`
   or a basket action; the driver's new verification steps run `nix build`,
   `git` and the devShell's test runners in the task's clone only.
2. **One writer per tree.** Every new record is written by the driver into
   the run directory (`~/factory/runs/<run>/<KEY>.*`) or by the seat into its
   own branch; no host file gains a second writer; the board stays the
   orchestrator's.
3. **The store fence.** Every new `.result` field is an identifier, an enum,
   a number or a ≤ 200-char string; the fence (`streams.py`, T1) declares
   each before `ingest result` accepts it — including every new
   `error_class` arm named below, which today is a closed enum
   (`pkgs/evidence/streams.py:120-131`); no body, log tail or prompt enters
   the store.
4. **The gate as the judge.** The Opus gate keeps its brief and its verdict.
   The driver's new checks *demote* (`done` → `partial`, an `error_class`),
   they never approve; a task the driver demotes still reaches the gate
   when a commit exists, because the demotion is the gate's first finding,
   not a replacement for it.
5. **The driver believes git and its own runs, not the seat.** Every
   demotion below is keyed on a fact the driver computed (`git diff
   --name-only`, `nix build` at the committed rev, `git rev-list --count`);
   a seat-written line can add a disclosure to the record, never remove a
   finding from it (the precedent: `factory-task:286-309`).
6. **The routing table stays the one place a model is chosen.** No change
   here names a model or a tier; the draft's routing observation is out (§5,
   change 10) and lives on only as a note in the report.

## §4 The changes

Ordered by the driver task that lands them (§6). "Catches" = corpus runs
the mechanism refuses or surfaces before the gate; "Controls" = its effect
on the 20 approved runs; "Verdicts" = what the panel found and folded in.

### 2. `touches` is enforced by the driver; the workspace's commit hook is the fast-fail

**Layer:** driver + seat workspace (commit hook) + integrator + result block.
**Mechanism:**
- *The enforcing arm is the driver's, after the seat exits.* `factory-task`
  parses the section's `**touches:**` line (the parser exists:
  `pkgs/evidence/tasks.py:44,173-174`; globs are already refused by the
  task-graph check, `tasks.py:1426-1432`), unions it over the chain root's
  sections for a fix round (`chain_root`, `tasks.py:117-119`), adds the two
  standing exemptions, and diffs `git diff --name-only base..task/<KEY>`
  against it — the same range `factory-task:284,293,340` already computes.
  It writes `touches_extra:` (count) and `touches_disclosed:` (count). An
  extra file with no disclosure demotes `done` to `partial`,
  `error_class: touches-violation` (a new arm of `ERROR_CLASSES`,
  `streams.py:120-131`, declared in the same task). The demotion is never
  conditional on the hook having run.
- *Path matching:* a `touches` entry that names a directory matches every
  file under it as a path prefix (pb10/P10b's
  `tests/evidence/fixtures/report/repo` covers nine staged files).
- *Exemptions, unconditional at both layers:* `docs/MAP.md` (any change —
  15 of 17 control commits regenerate it; whether the regeneration rule
  applied stays a review matter) and the `docs/OPERATIONS.md` queue block,
  cut with the awk the integrator already uses
  (`factory-integrate:94-95`), never the whole file.
- *Disclosure:* satisfied by any commit-body line naming the extra path;
  `Deviation: <file> — <reason>` is the form the refusal prints verbatim for
  the seat to paste. A disclosed extra file is an *accepted* deviation for
  the gate, not merely a disclosure: the gate scores the reason, and the
  orchestrator folds the file into the section's `touches` on the next
  round rather than the seat re-litigating it (cr20/CR2r3's "the plan never
  authorised it" is settled by the line, not re-found).
- *The hook, a convenience:* `factory-ws` sets `core.hooksPath` in the
  fresh clone (beside `factory_set_identity` and the `info/exclude` write,
  `factory-ws:106-114`) to a `commit-msg` hook that runs the same diff over
  `git diff --cached --name-only` and refuses the commit naming every extra
  file, hours before the gate. When the extra file is one an acceptance
  check needs (a nix-sandbox `cp` in `flake.nix`, a fixture in a bats file)
  the message says so. The hookspath **chains** `githooks/pre-commit` (the
  lint gate and the queue-block writer) — a hooks directory that replaced
  it would silently remove the gate from every task. The seat can bypass
  the hook (`--no-verify`, resetting `core.hooksPath`); the driver's
  recompute is the backstop and is the record.
- *Integrator:* `factory-integrate` (which today refuses only a board change
  outside the queue block, `:93-98`) reads `touches_extra`/`touches_disclosed`
  from the `.result` and refuses to land an undisclosed extra.
**Catches:** cr2/CR1 (`flake.nix`, review Deviations :314-320), ev1/R5
(`tools/ledger/schema.md`, review :38,42), cr20/CR2r3 (`flake.nix`, review
:53-59), tel1b/T1 (`83-plan-brief.bats`, disclosed only in chat), tel2/T3
(`80-seat-driver.bats`, log:9541 "So I'm NOT supposed to modify it"). In all
five the file is in the branch diff, so the driver sees it without believing
anything. **Dropped from the draft's list:** sb7/SB4 (no commit — head == base,
`SB4.result:3`; nothing for the hook or the recompute to see; change 9's
class).
**Controls (replayed over all 20 landed commits):** 18 clean by `touches`,
the chain-root union or the exemptions; pa2/P12 (a prose disclosure) and
pb10/P10b (a directory entry) are clean under the wording above. Zero
refusals.
**Cost:** seat: nothing when it stays inside touches; driver: one
`git diff --name-only` (ms); orchestrator: fix-round sections inherit the
root's touches automatically; one enum arm in the fence.
**Verdicts:** 0 of 3 refuted; the three amendments (sb7/SB4 dropped, the
hook demoted to fast-fail, prefix matching, the awk-cut exemptions, lenient
disclosure, the disclosed line as accepted, the chained pre-commit hook,
the new enum arm) are folded in above. "Zero refusals" is forward-looking:
no historical body carries the literal `Deviation:` token.

### 5. The driver verifies every claim it can reproduce: checks and probes

**Layer:** driver + result block + section template + integrator.
**Mechanism:**
- *Checks.* After the seat exits, `factory-task` slices its own section with
  `factory_extract_task` (`factory-lib.sh:213`) and reads the
  `**acceptance:**` line — never the seat's commit subject `(test: …)` (the
  derivation `factory-integrate:128-136` uses today) and never the seat's
  `FACTORY-CHECKS` names. For each check it runs
  `nix build .#checks.x86_64-linux.<name> --no-link` at the committed rev
  in the workspace, reusing the seat's nix store (no `--rebuild`), skipping
  any verdict already recorded for that rev, and writes
  `checks_verified: <name>=<pass|fail|not-run:<why>> …`. Verdicts are
  recorded with their rev through `factory_record_check`
  (`factory-lib.sh:81-99`), the writer the integrator already uses.
- *The demotion table is total.* `claimed pass + driver fail` →
  `partial`, `error_class: checks-misreported`. `claimed pass + not-run:
  absent` (no such check in the flake, no such hook in the repo — hr1/H2's
  `pre-commit=pass`) → `partial`, `error_class: checks-unverifiable`; a
  claimed pass is never silently accepted. `claimed fail + driver fail` →
  recorded, not penalised (pa8/P5 stays approved-eligible). `not-run:
  cache-miss` — a VM-bearing check (`seat-vm`, `helm-vm`, `host-core`)
  with no cached verdict at the rev — is recorded and never demotes: the
  driver does not spend a 15–40 min VM build inline (sb8/SB4b.log:1991)
  and leaves that check to the integrator, which already runs it.
- *Check integrity.* The driver writes `checks_scope: <clean|dirty>` by
  diffing `base..task/<KEY>` for files that define the checks (`flake.nix`,
  `tests/`, `githooks/`) and lists them, so a green earned by editing the
  check itself is visible to the gate (cr2/CR1's undeclared `flake.nix`
  edit; tel2/T2's weakened bats file).
- *Probes.* A section may name `**probes:**` entries. Each carries the
  command, a **bound or a deterministic byte-exact class** (never a bare
  equality on a measured number — the gate's own seven medians spread
  94.3–96.9 ms, cr19 review :512-519), and the bound's provenance (who
  measured it, when, in what environment), so a plan-authored number cannot
  be both the claim under test and the reference (hr1/H2's phantom fact
  came from the plan). The driver runs the section's command itself,
  whether or not the seat pasted `FACTORY-PROBE <name>=<value>` — no
  seat-supplied string is executed — at the seat's rev and cwd, under a
  normalised environment: at minimum `env -u FACTORY_RUN` (the precedent
  `factory-plan-brief.sh:305`; `tools/session-start.sh:18` exits silently
  under `FACTORY_RUN`, which is what pb4/P4b had to discover by hand,
  P4b.log:3260-3276), or the section's explicit `probe_env:`. Outcomes:
  `pass`, `fail` (bound missed → `partial`, `error_class: probe-mismatch`),
  `missing` (the section names a probe, the seat pasted none → `partial`,
  `error_class: probe-missing` — pa4/P4's shape), `not-run`, and `drift` (a
  live-corpus value that moved between the seat's rev and the driver's run,
  pb10/P10b's 47/59 against the plan's 46/58 — recorded, never demoting).
  A probe whose command short-circuits under the driver's environment is
  rejected at plan-judge time, not measured to 0 and passed.
- *Integrator.* `factory-integrate` keeps its own run against the merged
  `integ/<run>` rev and reuses `checks_verified` only when that rev equals
  the single task head. A wave of N tasks costs N revs × the acceptance
  set; the rev cache and a skip for tasks that produced no commit are the
  mitigations. `checks.jsonl` exists today only in the seat-driver spec's
  text; until it lands, nix's own store is the cache.
**Catches:** pb11/P11b (`FACTORY-CHECKS unit=pass`, P11b.log:3810, against
`not ok 222 … DBGSTATUS=126` at the committed rev, review :314,330-341 —
`checks-misreported`); hr1/H2 (`pre-commit=pass` for a hook that does not
exist, H2.result:2 — `checks-unverifiable`, with the total table); and, on
bounds the plan itself stated, run under the normalised environment: pa4/P4
(`wc -c` < 8,000 never run, `grep -c 'wc -c' P4.log` → 0, real value 8,176
— `probe-missing`), og4/OG1r2 (< 300 ms/call on 200 distinct tokens; the
seat's 50×-repeated-token benchmark read 2.7 ms, the gate's 907 ms),
pb3a/P3Ab (≥ 200 chars headroom, actual 103), pa6/P2 (the two live-probe
numbers, held at P2.log:4491-4493 and omitted). **Dropped from the draft's
list:** cr17/CR2rb, cr18/CR2r2, cr19/CR2r2b (checks honestly green; the
copied timings are MINORs), cr2/CR1 and rt1/RT1 (green; rejected on
defects this change does not reach), b3/F9 (no log, no result).
**Controls:** pa8/P5's honest `evidence-unit=fail` is recorded, not
demoted; pb4/P4b's probe reproduces under `env -u FACTORY_RUN`; pb10/P10b's
moved count is `drift`; every control's `pass` was re-run green by its
gate. Zero refusals (one would have been penalised without the environment
clause).
**Cost:** driver: the acceptance checks once more per task at the seat's rev
(a store hit for an honest run — seconds; minutes on a miss; VM checks
deferred); probes are seconds; seat: one paste line per probe; orchestrator:
a bound and its provenance per probe.
**Risk (the refuting verdict, would-have-caught — report §4, change 5):**
as first drafted, the driver's probe re-run under `FACTORY_RUN` measured
pa4/P4's `session-start.sh` at 0 bytes and would have passed it, and a
claimed pass the driver could not run (hr1/H2) demoted nothing. The
mechanism above folds that amendment (the normalised environment, the
total demotion table, `probe-missing`, bound provenance, the trimmed catch
list) and the two non-refuting lenses' (the acceptance line as the only
source of check names, `checks_scope`, the integrator clause, `drift`, the
asymmetric demotion, the VM cache-miss rule). After the fold the checks
half catches pb11/P11b outright and hr1/H2 by the table; the probe half
catches four, only because their plans stated a bound. Missing-case and
wrong-fact MAJORs are outside this change's reach and not claimed.

### 9. A result block the driver can always complete (`unreported`)

**Layer:** driver + WORKSPACE RULES text + wave + fence.
**Mechanism:**
- *The brief.* The draft claimed the result-block rule "moves to the last
  line of the rules block"; it is already there (`factory-brief:96-100`,
  `RULES` closes right after the template). What actually follows it is the
  optional REPO NOTES block whenever `FACTORY_BRIEF_EXTRA` is set
  (`factory-brief:114-115`, live through `launch-today.sh`). The change is
  therefore: re-print the four-line template after REPO NOTES as the
  brief's final line. The a2/N7 record scores that repetition
  `would_have_caught: false`; the driver arm below, not the prompt text, is
  what earns the change.
- *One follow-up turn.* When the seat's transcript ends with no line that
  parses as `FACTORY-RESULT status=<done|partial|failed>`, the driver
  issues one bounded follow-up turn ("reprint your last four lines in the
  exact grammar") before falling back — the step a2/N7's own
  `harness_gaps` proposed. If that turn also fails, the fallback below is
  the record.
- *The driver arm.* `factory-task` computes `base_sha` and `git rev-list
  --count base..task/<KEY>` **first** (today they sit ~30 lines below the
  synthesis arms: `factory-task:254-272` synthesise, `:284,293` compute; the
  live copy in `~/factory/bin` has the same order at `:134-139` vs `:158`).
  Then: if no usable line is found — absent, free-text (`FACTORY-RESULT:
  PASS`, cr15/CR2r.log:6582), fenced, or carrying a word outside the enum
  (today's `*)` arm, `:329-330`) — **and** the count is non-zero, it records
  `status=unreported`, `error_class: no-result-line`, `FACTORY-COMMITS`
  from the count, and `FACTORY-CHECKS` from change 5's `checks_verified`
  (or `none=not-run` until change 5 lands) **marked as derived** — never the
  seat's own checks line, which by construction is unverified here. With a
  zero count the record stays `failed`. `unreported` gets its own arm in the
  `case $status` block with `task_rc=0`, so `factory-wave:193`
  (`[ "$task_rc" -eq 0 ] || chain_ok=0`) does not skip the rest of a chain
  over a protocol slip; the wave line and the ledger print the word
  `unreported` so it is never read as `done`. The fence declares the arm.
**What it fixes, stated as ledger accuracy, not as a catch:** five `.result`
files assert `FACTORY-COMMITS 0` on line 3 and name the commit on line
18-19 — a2/N7, rt8/RT5rb, cr15/CR2r, cr18/CR2r2, cr19/CR2r2b. For a2/N7 and
rt8/RT5rb the absent line was the only defect (both gated and approved), so
the win is exactly "no green commit is filed as failed with 0 commits";
cr15, cr18 and cr19 are recorded honestly and their MAJORs stay the gate's.
**Dropped from the draft's list:** pb3ar2b/P3Ar2b (it emitted a parseable
`done`; the arm cannot fire); the "schedules the gate" benefit too — all
six were gated regardless.
**Controls:** every one of the 20 emitted a parseable block (pa8/P5's
`evidence-unit=fail` included), so the arm never fires; it sits beside the
existing `*) task_rc=3` fallback and cannot reclassify a `done`. Zero
refusals, zero seat work.
**Cost:** ~40 tokens of brief; two driver edits (hoist the git facts above
the synthesis arms; one `case` arm); one follow-up model turn on the runs
that lose the line; one enum arm in the fence.
**Risk (the refuting verdict, would-have-caught — report §4, change 9):**
of the draft's three examined runs one could not trigger the arm
(pb3ar2b/P3Ar2b emitted a parseable `done`), one gained only a ledger word
on a run rejected for unrelated MAJORs (cr15/CR2r), and one was a real but
bookkeeping-only fix (rt8/RT5rb). The fold: the change is re-titled as a
ledger fix, its list cut to the five mis-filed runs with two counted as
caught, the follow-up turn added, the derived checks line labelled.

## §5 Out

### Dropped on the panel (two or three refutations each)

The refuting evidence, one line per verdict with its citations, is the
report's §4 (`docs/reviews/harness-study/2026-09-07-deepseek-failure-corpus.md`);
the amendments the skeptics offered are the raw material of the second
spec (§7 Q6), judged again by the same three lenses before any plan is
drafted from them. The seven, with the lens that turned each:

| # | dropped change | refuted | the turning finding |
|---|---|---|---|
| 1 | named mutants as committed patches the driver executes | 3 of 3 | the seat authors the artefact judged; four controls demote; devShell green where the nix check is red (pb11/P11b) |
| 3 | one test per enum arm, grepped in the test delta | 2 of 3 | a substring check: literals present, no test drives the arm (ev2/E7b) |
| 4 | `FACTORY-DEVIATION` lines and `partial` as the honest stop | 3 of 3 | no oracle for `fact`/`unreachable`/`scope`; ≥ 10 controls demote; its verifiable half is change 2 |
| 6 | green-on-base | 3 of 3 | four of seven claimed catches red on base; no fork point for cherry-pick fix rounds; three controls demote |
| 7 | a sweep fixture that must grow | 2 of 3 | the sweep carries no verdicts; a count cannot see an absent row (og1/OG1b) |
| 8 | the commit-msg hook: subject, trailers, the red paste | 2 of 3 | seat-writable, no driver re-check; the paste arm judges seat-authored text; seven controls refuse |
| 10 | routing: no row change | 2 of 3 | no mechanism; Flash-off evidence n = 1; `report ladder` does not exist |

What the panel would keep from them — the driver-*derived* mutant (Q7), a
verdict-carrying sweep fixture with per-rule containment, the subject and
trailer arms as a *driver* check — is the second spec's starting list.

### Out by scope

Anything needing a stronger model (the ladder decides that); the DeepSeek
review seat's brief; the plan-side rubric (the planning agent's P10 report
owns plan defects); the telemetry streams' shape beyond the new `.result`
fields (declared through T1's fence, ingested by T2); `dark-factory.js`;
the harness repo's whole-tree gate; the interactive seat; any seat log or
transcript as an input to a mechanism (the panel read slices to judge;
nothing here reads one at run time).

## §6 Trial-and-error plan

Each surviving change is one task in a plan the planning agent drafts from
this spec (`plan-seat-harness`), lands through a seat and an Opus gate like
any other, and is measured before/after by the join `derived/gates ⋈
derived/tasks` (T10a) under the n-gate: no claim below n = 5 attempts per
cell.

1. **Baseline** (before the first change lands), per class and per rung:
   first-gate approved fraction (20/86 gated runs here), the §2 tag counts,
   median output tokens (rejected 63 k, control 89 k), median wall (760 s
   vs 912 s) — computed from the store by the plan's first driver task
   (`report harness` does not exist yet; `report.py` has only `plans`),
   never retyped.
2. **Order:** 9 → 2 (one driver task: the hoisted git facts, the
   `unreported` arm, the touches recompute and hook, the fence arms
   `touches-violation` and `no-result-line`) · 5 (a second driver task:
   `checks_verified`, `checks_scope`, `probes_verified`, the normalised
   probe environment, the integrator's reuse rule, the fence arms
   `checks-misreported`, `checks-unverifiable`, `probe-mismatch`,
   `probe-missing`; the section template gains `**probes:**` with bound and
   provenance, and `probe_env:`).
3. **Measure per change:** its new `.result` field is written on every
   task; after five tasks per class the report prints the demotion count,
   the gate's verdict on those demotions (agreed / overruled) and the
   control false-positive count. A change the gate overrules ≥ 2 of 5 is
   reverted by its own `<KEY>r` under rule A1; one with zero demotions in
   10 tasks is kept only if its target tag also fell to zero.
4. **Success:** first-gate approved fraction per class rises from the
   baseline at n ≥ 5 with output tokens per landing ≤ control median × 1.5;
   the targeted tags (undisclosed `out-of-touches-edit`,
   `checks-not-run-locally`, `fabricated-claim` on a plan-stated bound,
   `misparsed-result-block`) each below 2 in the next 20 rejections.
   **Stated honestly:** the three largest zero-on-controls causes
   (never-ran-named-mutants — 16 by tag, 41 by the process table —,
   one-arm-per-enum 13, ignored-section-item 11) are targeted by nothing in
   §4; the same report tracks them as the measure the second spec must move.
5. **The gate stays blind to the mechanism:** the `.result` fields are
   facts for the Opus brief to check, never verdicts to accept; a derived
   line is labelled derived.
6. **The dropped seven** are not re-drafted inside this plan; their
   amendments go to the second spec, judged by the same three lenses first.

## §7 Open questions for the operator (each with a default)

1. **Probe environment.** Default: the driver re-runs every probe under
   `env -u FACTORY_RUN` at the seat's rev and cwd; a section may override
   with `probe_env:`; a probe that prints nothing under both is a plan
   defect refused at judge time.
2. **Do the driver's verification runs (change 5) count against
   `FACTORY_TIMEOUT`?** Default: no — their own 30-minute bound; a bound hit
   is `error_class: verify-timeout`, never a demotion; VM-bearing checks are
   `not-run: cache-miss` and left to the integrator.
3. **Is a disclosed `Deviation:` line an accepted deviation or only a
   disclosure?** Default: accepted for the gate (which still scores the
   reason); the orchestrator folds the file into `touches` on the next
   round. Otherwise cr20/CR2r3's authorisation objection survives the hook
   unchanged and the seat re-litigates every forced file.
4. **The `unreported` follow-up turn.** Default: one bounded turn (a single
   model call, the four-line grammar quoted) before the fallback; its cost is
   recorded on the run. If the operator prefers no seat re-entry, the
   fallback alone stands and the record is still correct.
5. **`task_rc` for `unreported`.** Default: 0 — the chain continues, the
   word is printed by the wave and the ledger, and the gate is scheduled as
   for `done`. Rationale: a protocol slip over a real commit should not skip
   the tasks behind it; the gate is where the commit is judged.
6. **The second spec.** Default: `2026-09-xx-seat-harness-redesign-2`,
   drafted from the §5 amendments (changes 1, 3, 7, 8 in their amended
   forms; 4 and 6 only as driver-computed advisory fields), judged by the
   same three lenses with the 20-control replay mandatory in the draft, not
   left to the panel.
7. **The mutant class, unaddressed.** 41 of 66 rejections ran no mutant; the
   draft's change 1 was refuted on all three lenses. Default: the second
   spec's first candidate is the amended form — the driver *derives* one
   patch per new conditional branch and guard clause from the commit's diff
   (no seat-authored patch), runs it under the section's named runner
   including `nix build` when the section says so, records
   `mutants_total/killed/survived/not_run` as evidence for the gate, and
   demotes nothing on its own until five tasks show the gate agreeing with
   the field.
