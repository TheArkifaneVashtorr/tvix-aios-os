# The planning agent — design (draft for the operator)

**Date:** 2026-09-05. **Status:** draft for the operator's review, revised the
same night after two critiques (the Revision note at the end lists what
changed); nothing here is built. **Asked for by:** the operator ("planning is
so important we should do research and then make another Fable agent to plan
out exactly what a good planning agent does. The key factor in this dark
factory is intelligent design but automatically. It's the 4-star service of
software: predicting what the user will want or what the user would do. This
can be integrated in dsh and Claude Cowork with a pinned workflow. The core
value of the project is efficiency through information, planning and rigor.").
**Inputs:** five read-only research slices taken on core on 2026-09-05 (the
gate record, the superpowers skills and the seat's brief extractor, the
harness integration points, the operator's revealed preferences, the derived
task graph) plus the designer's own reads and measurements on the repo (§11
lists how each number was taken). No transcript, seat log, prompt body or
session file was opened.

**Vocabulary, once.** A *plan* is a Markdown file under `docs/superpowers/plans`
whose task sections carry a typed heading (key, kind, size), `dependsOn`,
`touches`, `acceptance` and a commit subject; `pkgs/evidence/tasks.py` reads
those headings into the task graph. A *gate* is the Opus review of one task
with its mutation table. A *fix round* is the one bounded retry (`<KEY>b`); a
*re-plan* (`<KEY>r`) is what rule A1 forces after that. A *packet* is the file
of facts the planner gathers before it writes. A *mutant* is the one-line code
change that must turn a named test red. A *wave* is one group of tasks that
can run together: take every task whose dependencies have all landed, then
repeat on what is left — one group per line is what `tasks.py waves` prints.
A *barrier* is a point where the workflow waits for every parallel agent
before it goes on.

## 0. The short version

- 132 gate reviews since 2026-09-04 (counted 23:20; 131 when the research
  slice and the telemetry spec counted); 59 rejected. 42 of the 59 (71 %)
  trace to the plan, not the implementer: an assertion no mutant could fail
  (14), a missing case (14), an under-specified interface or error contract
  (8), a wrong fact (6) — one row each in Appendix B, which is the count of
  record. The implementer was at fault in 14, the process in 3.
- Of 58 gated task chains in the ten typed plans of 2026-09-05, 28 landed first
  try (48 %), 19 after one fix round (33 %), 11 needed a re-plan (19 %). One
  task (OG1) took five gates and 3 h 58 min.
- A bad plan is paid for three times: a seat run (mean 673 s), a gate
  (64,589–181,844 Opus tokens each where itemised), and the operator's
  attention when the failure surfaces live. Effort and model comparisons found
  the plan defect constant across arms; only the recovery differed.
- Blind cheap models out-wrote the session-aware orchestrator on the one spec
  where it was measured (GLM 28, Kimi 26, Fable 21 of 30): the orchestrator's
  plan was terse and not self-contained; its one dispatched task was rejected.
- This design makes planning a gated product: a deterministic packet of inputs
  (mechanical facts, the record, the field — incidents and the driver's own
  contract — the operator model, the target), a fixed process with a check per
  step and a re-plan mode, an anticipation list with an acceptance per item
  and the date each becomes measurable, a 14-row rubric judged blind by a
  three-judge panel (two Sonnet, one Opus) before any dispatch, and a record
  that joins each plan's score to its tasks' gate outcomes. It is pinned as a
  Cowork workflow (`.claude/workflows/plan.js`) and as a dsh skill and profile,
  both judged by the same panel. Where the seat driver can refuse a known
  failure deterministically, the design proposes that guard as a task (P11)
  rather than a sentence told to a model. Nothing in it dispatches a seat,
  touches the network, or widens a guard.

## 1. What planning is here, and why it is the product

**The record.** `docs/reviews/` holds 132 Opus gate reviews dated 2026-09-04 or
later (24 and 108; 131 when the research slice counted, the 132nd — cr16 ·
CR3rb — is an approval). By verdict grep over the bodies, minus four approved
files that quote a prior round's rejection, 59 reject and 73 approve — a 45 %
rejection rate. (The first-line parse the graph uses — `REVIEW_RE` in
`pkgs/evidence/tasks.py` — reads 105 of the 132: 59 approved, 46 rejected,
27 whose verdict is only in the body; run at 23:20. The telemetry spec's T3
row counted 104 / 58 / 46 / 27 over 131 files earlier the same evening. The
body count is the one used.) The research pass classified each rejection from
the reviewer's own attribution sentence:

| primary cause | n | share | the canonical sentence from the reviews |
|---|---|---|---|
| (a1) plan: an assertion no mutant can fail | 14 | 24 % | sc1 G1: "The tests are verbatim from the plan, so this is a plan gap the implementer inherited rather than sloppiness" |
| (a2) plan: a case the plan should have named | 14 | 24 % | og1 OG1b: "The implementer kept the enumerate-the-flags shape the OG1 review called out and under-enumerated it" |
| (a3) plan: an interface or error contract left open | 8 | 14 % | sc1 G5: "the tasks.py check guard added to the lint runCommand is vacuous — it can never fail … prescribed verbatim by the section's Step 4" |
| (a4) plan: a wrong fact | 6 | 10 % | fd1 FD1: "The plan's Fact ('the first line is the next wave') is wrong — tasks.py waves prints one group per line across all waves" |
| (b) implementer, against a correct plan | 14 | 24 % | ev3 R3: "the plan's Step 1 explicitly told the implementer to key the fake on the (systemctl, --user, show) prefix … and the implementer … applied it only to the timer tests" |
| (c) process (commit subject, template echo, a leaked briefing block) | 3 | 5 % | sc3 G7: "the commit inserted a ## WORKSPACE RULES section that is leaked seat-harness task-briefing text" |

The counts are derived from Appendix B row by row (an earlier tally of
15 / 12 / 9 / 6 was the research slice's headline and did not match its own
rows; the appendix is the record of record and §7's backfill reads it). About
eight rows carry both a plan and an implementer cause; a different primary
rule moves at most 8 of 59 rows between (a) and (b). No rejection was caused
by a short `touches` list. Appendix B lists the 42 plan-primary rows with the
sentence the plan was missing, plus the one process-primary row (sc1 · G2)
that carries a plan secondary; it is the seed of the machine-readable record
§7 asks for.

**Per plan.** 58 gated chains across the ten typed 2026-09-05 plans: 28 landed
first try (48 %), 19 after one fix round (33 %), 11 after a re-plan or a third
round (19 %). Evidence-store 18 chains = 10 / 5 / 3; session-context 12 = 4 /
5 / 3; seat-routing 5 = 1 / 2 / 2; context-reset-ritual 4 = 1 / 1 / 2 (CR2 and
CR3 still open at the corpus end); effort-comparison 4 = 4 / 0 / 0. Every
chain that needed a re-plan (OG1, RT5, R3, CR2, CR3, E2, E7, G8, G11, G12,
SB2) sat on a parsing, error-contract or namespace seam where the plan
enumerated spellings instead of stating a rule.

**What one bad plan costs.** Measured on the OG1 chain from git: plan text
committed 15:40:06, rejected 16:13:54, OG1b rejected 16:52:56, OG1r rejected
17:38:41, OG1r2 rejected 18:29:04, OG1r2b approved 19:37:16, integrated
19:38:45 — 3 h 58 min, five seat runs, five gates, 17,232 words of gate prose,
39–66 min per round from plan text to verdict. In general terms, one extra
round is: a seat run (wall mean 673 s over 200 results; $0.10–0.19 of DeepSeek
Pro for an XS/S task at the 2026-09-04 rate), a gate (64,589–181,844 Opus
tokens in the eight gates the comparison reports itemise; at list prices $5 in
/ $25 out per million that is roughly $0.5–2 a gate, the in/out split being
unrecorded), the orchestrator's re-plan (Fable tokens, unmetered), and 14 min
median from seat finish to review commit. Across the corpus, 59 rejections are
59 extra gates: 3.8–10.7 M Opus tokens by the itemised range, 2.7–7.6 M of
them plan-caused. Operator attention is not a token: on 2026-09-05 evening
six things surfaced live that a plan could have prepared — two launches dead
at once because `FACTORY_PLAN` was unset (cr3, cr4), the guard refusing the
orchestrator's own `rm` (the operator ran it), the Stop hook blocking every
turn end for 35 min (the operator switched and placed an override), three
seats appending a fabricated board commit (dropped by hand at integration), a
finished task recorded `failed` because its result block carried a colon
(cr15), and an OpenRouter 402 that killed two seats mid-task (the operator
added credits). Interventions per plan are **unmeasured**; §7 defines the
number.

**The comparison's lesson.** One spec, four authors, one Fable judge, ten
criteria of 0–3 (`docs/reviews/2026-09-05-plan-writing-comparison.md`): GLM 5.3
xhigh 28, Kimi K3 xhigh 26, the orchestrator with full session context 21,
DeepSeek V4 Pro high 20 (void: it read the compared plan through a grep). The
orchestrator's plan scored 1 of 3 on self-contained tasks, 2 on TDD, 1 on
judgement calls, and 3 only on economy (2,263 words against 12–13k) and on
session-aware wave hazards a blind arm cannot see. Its one dispatched task, SB3,
was rejected at gate and re-planned. The two clean arms named a mutation
target per test; the house plan named none. The judge declared its bias (plan
A was its own model family) and set the bar for a routing row: n = 3 specs × 2
samples per model, two judge families, prices on the sheet.

**Effort and model do not rescue a plan.** Effort comparison (n = 2 per arm,
XS tasks): medium and xhigh both 2/2 approved, 0 fix rounds, identical code;
the one surviving mutant survived both arms "because the plan's test spec did
not name it"; xhigh cost +10 % money, +67 % wall clock, +11 % gate tokens.
Model comparison (n = 2 per arm): both Pro and Flash hit the same two plan
defects (a header wording that failed its own green grep; a wrong sandbox
fact); Pro recovered in one round, Flash lost one. The plan defect was the
constant.

**Why this is the product.** Seats and gates are metered and replaceable; the
plan is the one artefact every downstream cost multiplies. The operator's
words — efficiency through information, planning and rigor — name the three
parts of this design: the packet (§2), the process and its anticipation
(§3–4), the gate before dispatch (§5).

## 2. The planning agent's inputs

Everything below is gathered before a word of plan is written, in this order:
mechanical facts first, the record and the field second, the operator model
third, the target last. Each row names the command or path, when it is fresh,
when it is stale, and what the agent does when it is missing. "Refuse" means
the packet records the absence and the plan is not written; "degrade" means
the packet says `unavailable:` and the plan must not state a fact that only
that input could supply.

### 2.1 Mechanical (deterministic; the packet pastes the output verbatim)

| # | input | command or path | fresh when | stale or wrong when | if missing |
|---|---|---|---|---|---|
| M1 | graph soundness | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` (prints nothing when sound; today empty). The reader that runs it records `checkEmpty: true` only when the output is empty; the workflow gates on that field, not on prose | every run | a non-empty output: an unknown `repo:` attribution, a duplicate key, a cycle, a code task without acceptance | refuse: a plan written onto a broken graph inherits phantom states |
| M2 | the task brief | `… tasks.py --root . brief` (0.5–1.7 s measured; the same text the SessionStart hook injects, capped at 1,500 chars) | after `check` is empty | "running" over-reports until CR3r's `run.meta` lands (215 stale logs today beside 12 live); counts change with every landing | degrade; the plan may not claim what is queued |
| M3 | the full graph | `… tasks.py --root . json` (422 KB, saved to a file in the packet, not pasted; per task: body, `depends_on`, `touches`, `chain`, `dep_repo`, `state`) | with M2 | same as M2 | degrade |
| M4 | the next wave and the launcher's payload | `… tasks.py --root . waves --repo nixos-agent-env [--plan <file>] --next`, `--json`, `--factory-args` (today: `"B1"`) | with M2 | `--repo` is required; an untyped plan is invisible (`docs/ledger/plan-status.toml` carries it) | degrade |
| M5 | cross-plan file conflicts | `… tasks.py --root . conflicts` (today `CR4 × SB5: CLAUDE.md`) | with M2 | same-plan overlaps are not listed (they are sequenced inside the plan) | refuse for any plan that names `touches` |
| M6 | live facts | `evidence bundle --markdown` (0.19 s; live generation and revision, checks covering HEAD, sibling heads, Helm verdicts, open gaps — 16 today) | reads the store, not the tree | "WORKING TREE DIRTY" on HEAD; a check's row older than the last code commit; the Helm revision tiles are structurally warn/fail (environment review) | degrade; the plan may not name a check as green |
| M7 | claims | `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"` (silent on success) and the `[[claim]]` rows with `status = "gap"` (id, owner, review_by, closes_by) | every run | a gap past `review_by` fails validation | degrade |
| M8 | in flight | `bash tools/ritual.sh inflight ~/nixos-agent-env` | sub-second | over-reports (see M2) | degrade |
| M9 | the session view | `bash tools/session-start.sh` (board block ≤ 3,000 chars, bundle ≤ 2,500, brief ≤ 1,500, in-flight ≤ 1,200, total ≤ 8,000) | every run | the board's START HERE is prose and replaced every turn; its "Now" paragraph is judgement, not fact | degrade |
| M10 | the repo map and check names | `docs/MAP.md` (regenerate: `python3 pkgs/evidence/repomap.py --root . write`) | after regeneration | a check name not in the map is not a check; `(test: …)` lists hold check names only | refuse to name an acceptance the map does not list |
| M11 | model routing | `docs/ledger/routing.toml`; `factory_route [--route R] <role> <kind> <size>` → `MODEL EFFORT` | on commit | `ROLES` in `tools/factory/route.py:38` has no `plan`; a role outside the enum fails validation | degrade: the plan states the row it expects and names it as a proposal |
| M12 | landings and churn | `git log --since=<date> --format='%ci%x09%s'` (the packet records the count with the time it ran; the count is not a fact a plan states — it read 331, 329 and 328 at three times this evening) | every run | subjects are the derived graph's landing evidence; a subject that is not byte-identical to the plan's breaks `landed` | degrade |
| M13 | the seat's brief extractor | `tools/factory/seat/factory-brief <plan> <KEY>` (read-only, stdout only; prints exactly what a seat sees: `## Global Constraints`, `## Assumptions`, the one section, the WORKSPACE RULES block). The packet runs it against the format-reference plan (`2026-09-05-evidence-store.md`, `E1`) so the drafter sees the shape; Step 4 runs it against the draft | every run | a section amended elsewhere in the plan never reaches the seat; the extractor takes the FIRST `### KEY` match | refuse to ship a section the extractor does not reproduce whole |

### 2.2 The record and the field (what went wrong before, by class)

| # | input | path | fresh when | stale when | if missing |
|---|---|---|---|---|---|
| R1 | gate reviews | `docs/reviews/*opus-review*.md` (132 at 23:20; 105 parse under `REVIEW_RE`, 59 approved / 46 rejected, 27 unparsed; majors and mutation counts are prose) | every run | until §7's front matter lands, the class of each rejection is read from `docs/ledger/plan-defects.toml` (P3) or, before it, Appendix B | degrade; the packet says which similar tasks were never gated |
| R2 | the plan-defect table | Appendix B of this document, then `docs/ledger/plan-defects.toml` for the filed corpus and `plan_defect` front matter on every new review (task P3; filed reviews stay byte-unchanged) | on commit | a new review filed without the field | degrade |
| R3 | the three measurements | `docs/reviews/2026-09-05-{plan-writing,effort,model}-comparison.md` | on commit | n = 1–2; not a routing row | — |
| R4 | rules of record | `docs/decisions/2026-09-03-test-based-reality-amendments.md` (falsifiable; unmeasured is debt; proxies declared), `2026-09-04-parallel-agent-workflows.md` (deterministic first, isolated workspaces second, judgement last; parallel is required), `2026-09-02-factory-model-policy.md` (models per role), rule A1 in `docs/board/archive-2026-09-02-to-05.md` | append-only | — | refuse: these are the plan's constraints |
| R5 | the field: incidents and the driver | `docs/OPERATIONS.md`, `docs/board/log-2026-09.md` and the archive (incidents as prose) **and the driver itself**, read in full: `tools/factory/seat/factory-task`, `factory-wave`, `factory-dispatch`, `factory-integrate`, `factory-lib.sh`. The fifth packet part (`field.md`, Appendix D) writes them as a dated list of failure modes — what happened, what closed it, the board line it came from — and the driver's contract as one sentence each with the anchor text beside it (what `FACTORY_PLAN` defaults to when unset; the exact `FACTORY-RESULT` grammar the extractor accepts and what it synthesises otherwise; what `factory-integrate` merges and refuses; where `dispatch.log` is written and what it holds). Every sentence A5 prepares lives only here. The orchestrator's memory `field-lessons.md` is **not** readable by a planning subagent and is not an input | every turn | prose; an incident older than the fix that closed it (the board's "Ritual state" paragraph names CR5 as the fix for the 19:20 loop) | **refuse** for any plan whose tasks are dispatched to a seat; degrade otherwise |
| R6 | plan headers in force | the 37 plans: `## Global Constraints` in 33, `## Assumptions` in 5, `## Waves` in 4, `## Operator` in 3 (`factory-brief` warns "no Assumptions section" and omits it on most) | on commit | — | the new plan carries all four |

### 2.3 The operator model (preferences, ownership, pauses)

| # | input | path | fresh when | stale when | if missing |
|---|---|---|---|---|---|
| O1 | how to work | `docs/brief.md` §8 (terse; tell me when the brief is wrong rather than route around it; prefer failing the build; one phase at a time; no secrets in the repo) and §3 (the six invariants) | append-only | a decision file amends it | refuse |
| O2 | phase gates | `docs/brief.md` §7 ("Do not start the next phase until the previous phase's test passes and I have said so") | — | — | refuse |
| O3 | what the operator owns | `docs/OPERATIONS.md` START HERE, the "Operator owns:" sentence (switches, credentials, DNS names, password files, brainstorms owed, spec reviews, pauses, A/B/C decisions, physical moves) | every turn | prose only: the graph has no `paused` state and `task-status.toml` knows `withdrawn` and `parked` only | degrade; the plan asks instead of assuming |
| O4 | pauses and holds | the same block ("Media W3b/W5b fix rounds: paused by the operator"; "lift or keep the pause on B1") | every turn | a lifted pause is a board edit | refuse to schedule a paused task |
| O5 | the operator's words on design | `docs/decisions/*.md` (invariants bind agents not apps; media Nix-native no container; the softkey retraction — explain tool names in plain words; parallel workflows; helm buttons removed; driver 580 unparked) | append-only | — | degrade |
| O6 | standing encouragements | working-style memory, quoted on the board: "high levels of parallel development are encouraged"; "please feel encouraged to make recommendations for improvement … each with a measurable acceptance and an effort class" | — | — | the plan's Waves and its recommendations honour them |
| O7 | the operator-model file (proposed, P4) | `docs/board/operator-model.md`: the six invariants, the ten preferences ranked, what the operator owns by type, the open decisions, the current pauses — derived from O1–O5, no personal data beyond what the repo already holds | on commit | more than one turn behind the board | degrade to O1–O5 |

### 2.4 The target

| # | input | path | fresh when | stale when | if missing |
|---|---|---|---|---|---|
| T1 | the spec or the request | `docs/superpowers/specs/<date>-<name>-design.md` (approved in brainstorm), or the operator's words verbatim | on commit | a spec whose decisions the operator has not approved section by section | refuse: the plan waits for the spec gate (brief §7) |
| T2 | its size | `wc -w` of the spec: S ≤ 1,500 words, M ≤ 4,000, L above (measured today: seat-behind-broker 1,057; helm-home 1,682; session-context 2,037; ritual 3,768) | with T1 | an L spec is split into sub-project plans before any task is typed | — |
| T3 | the files it names | every path in the spec, read in full at planning time; every option, line number and check name pasted from a command | with T1 | a line number is stale the moment the file changes: cite the anchor text, not the number | refuse to cite a fact without its command |

## 3. The process

Each step has a check. A step whose check fails is repeated, not skipped. The
whole process runs inside one turn of the planning workflow (§6) and its
output is one plan file, one judgement file and one concept file.

**Step 0 — the packet.** Run §2.1 M1–M13 in order and paste outputs verbatim
into `<scratch>/packet/mechanical.md`, each under the command that produced it
and the time it ran (M3's 422 KB goes to `graph.json` beside it). Then four
readers write `record.md`, `field.md`, `operator.md` and `target.md` from
§2.2–2.4. *Check:* M1 is empty and the reader that ran it says so
(`checkEmpty: true` — the workflow refuses on anything else); every fact the
drafter later states is traceable to a line in the packet; the packet is
dated.

**Step 1 — clarify.** From the target, list every decision the spec leaves open
and sort it: (i) the operator's (anything under brief §3, an isolation grade, a
name, spend, a credential's home, anything that widens an agent's reach); (ii)
the plan's (a file layout, a test shape, an order). For (i) ask at most three
questions, each decidable in one word, each with a recommendation and the
default that applies if unanswered. The brainstorming questions the agent
asks itself, in order: what does the operator do the day after this lands;
which command will they run first; what will they have to type that a plan
could have written; which of their preferences (§2.3) does the obvious design
violate; what did the last similar task get rejected for. *Check:* every
question names the invariant or decision file it touches; a question without a
recommendation is not asked; the Helm Home plan (the first through this agent,
board 2026-09-05 ~23:30) asks exactly one — Discord's isolation grade — with a
recommendation.

**Step 2 — scope.** Write the spec-to-task map: every numbered spec item →
task key, or `out: <reason>`. Anything the request implies but the spec does
not say is listed under "Not in this plan" with the concept file as its
parking place; scope creep is refused by construction because a task without
a spec item cannot enter the map. *Check:* the map is complete in both
directions (every spec item mapped; every task traced); the "Not in this plan"
list is non-empty or says "none".

**Step 3 — decompose.** Typed sections, sizes XS/S/M only (an M that needs a
second commit is two tasks; L is refused). `dependsOn` names keys that exist
in the graph or in this plan; a dependency in another repo carries `repo:`
(satisfaction is keyed by repo and chain root, G12r). `touches` is explicit
paths, never a leading glob (F9: a leading glob disabled the overlap check).
Waves are the groups the graph falls into when you repeatedly peel off every
task with no unmet dependency — what `tasks.py waves --json` prints — computed
for a scratch copy of the tree that contains the draft. Until P1 lands, that
run is the lint check's own form: copy the tree with its `.git`, place the
draft under the copy's `docs/superpowers/plans/`, write a one-repo file
(`[[repo]] name = "nixos-agent-env" path = "<copy>"`) and run `tasks.py --root
<copy> --repos <that file> --runs-dir /nonexistent --store /nonexistent
check`, then `conflicts` and `waves` the same way. The `--root`-only form
re-reads the live tree through `docs/ledger/repos.toml` and cannot see the
draft (the sc1 · G5 shape); P1 folds the whole recipe into `tasks.py check
--draft <file>`. Two tasks in one wave that write the same file serialise in
key order, and the plan says so. Parallelism is designed in, not out: the
Waves table shows what runs together, and the plan states which sibling plans'
open tasks it must not collide with (`conflicts`). *Check:* `check` is empty
and `conflicts` shows no new cross-plan hit for the scratch copy; every wave
with more than one group is a measured chance to run in parallel, not a
coincidence.

**Step 4 — specify each task so a blind implementer lands it.** The seat sees
exactly `## Global Constraints`, `## Assumptions` and the task's own section
(M13); nothing else in the plan reaches it. Therefore every section carries,
in this order: **Files** (create/modify, exact paths); **Interfaces** (names
and signatures; every producer of every field; every enum arm; the error
contract — what exit code and what stdout on each internal failure; which tree
or file a derivation reads); **Facts** (each pasted from a command run at
planning time, the command beside it — `cmd | cat -A | head` for shapes);
**Steps** (the red command and its expected red output pasted; the change; the
green command; the checks by name; never an instruction for the seat itself to
merge main or to regenerate/restore the derived board block — landing is the
integrator's and the orchestrator's act, done outside the seat's own commit:
DF13's seat merged main because its own Steps said so and was refused at
integrate, and HM7c's fix round died mid-run on a board-restore step, both
2026-09-15); **Tests** (per assertion the one-line
mutant that turns it red; per fixture the row that makes it discriminate — a
second gap whose id sorts against its date, a flapping history `ok, fail, ok,
fail`, one payload per rule, every enum arm, the default branch not the
injectable one. **A named proof shape is not a mutant** (added 2026-09-07,
from the bk3 · B1b re-read): "a fixture listing, or an assertion over the
known layout" names *where* a proof might live, not *what turns it red*; a
contract item whose only falsifier is a proof shape — or an "or" between two
— is decoration as written, and a seat that satisfies every mutant the
section does name has met the section. The section names the mutant (for
B1b: a fourth lane child in the tmpfiles rules → `host-core` red naming it),
or the item is `vacuous` at the gate); **touches**, **acceptance** (names from `docs/MAP.md`),
**commit subject** (byte-exact; the `(test: …)` list holds check names only).
For a fix round or a re-plan the section also carries every item of the
rejection and, for every deleted test, the assertion that replaces it; a
re-plan is written in replan mode (§6.1): the existing plan and the rejecting
review are the drafter's inputs, the `<KEY>r` section is appended, and no
existing typed heading changes. The eight questions of Appendix A are
answered for every section before Step 5. *Check:* `tools/factory/seat/
factory-brief <draft> <KEY>` — read-only, stdout only, the one seat tool the
rules allow — reproduces the section whole; the eight questions have no "no"
answer; the section names at least one mutant per assertion and none of the
mutants is "delete the test".

**Step 5 — operator steps and rollback.** One command each, with its
acceptance command and the expected output, in a `## Operator` section that a
non-engineer can run top to bottom: the switch (`nix build
.#nixosConfigurations.core.config.system.build.toplevel` then `nix store
diff-closures /run/current-system ./result`, with the delta named as a
prediction — A2 — and measured on the landed tree before the switch line
ships), the user units to start by hand after a switch (a switch never starts
a newly enabled user timer in a logged-in session), the credentials, names and
top-ups the operator must supply (placeholders and where each goes), the
acceptance drill, the rollback (the recorded generation's own
`switch-to-configuration`, never a blind `--rollback`). *Check:* every command
in the section is pasted from a run in dry form (`--dry-run`, `nix build`
without switch) or quoted from the runbook it extends; nothing in it is a
sentence where a command would do.

**Step 6 — self-judge.** Score the draft against §5's rubric with reasons;
any row below 2 is revised before the panel sees it. *Check:* the self-score
is filed beside the panel's; a self-score more than 6 points above the panel's
median is recorded as a calibration finding against the author.

**Step 7 — record.** The concept-per-turn file (house format), the judgement
file (§5.4), one board line. *Check:* the concept file exists with the seven
fields; the judgement file parses.

## 4. Anticipation — the 4-star service

What the agent predicts and prepares before being asked. Each row has a
trigger, the prepared artefact, the acceptance that shows it worked, and the
date the acceptance becomes measurable (a row whose stream has not landed is
counted by the orchestrator on the board until then, and says so). Every
artefact is text in the plan or a file beside it; none is an action. Where a
failure can be refused deterministically by the driver, the artefact is a
guard task, not a sentence (the operator's ordering: deterministic first,
judgement last).

| # | trigger | prepared artefact | acceptance (how we know it worked) | measurable when |
|---|---|---|---|---|
| A1 | the plan is written | a `## Dispatch` section: the run name; per wave the `tools/factory/seat/factory-dispatch <run> ~/nixos-agent-env <plan> --dry-run` output pasted and the same line without `--dry-run` as the command to run; and per landing the recipe, in order: (1) in the workspace keep only the one commit the section names — `git -C ~/factory/ws/<run>/<KEY> log --format='%h %s' <base>..task/<KEY>`, then `git -C ~/factory/ws/<run>/<KEY> reset --hard <that sha>` (three seats appended a fabricated "landed" board commit on 2026-09-05 — CR5, CR2, FD1b — each dropped this way before its gate and integration); (2) if main moved under a file the task touches, merge it into the task branch first — `git -C ~/factory/ws/<run>/<KEY> fetch ~/nixos-agent-env main && git -C ~/factory/ws/<run>/<KEY> merge --no-edit FETCH_HEAD` (OG1r2b, SB1 and FD1b needed it: `settings.json`, `flake.nix`, the queue block, MAP); (3) commit the review; (4) `factory-integrate <run> ~/nixos-agent-env <KEY>` then `git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>`, gated on both exit codes; (5) dispatch what it unblocks (A7) | the run's keys appear as telemetry `tasks` rows under the prepared run name with the plan's `plan` field, or the board line that records the launch quotes the prepared line unchanged; the fast-forward follows the integration within one gate interval (median 14 min). No log is read: `dispatch.log` holds only the `run … plan … groups:` line, never the launch, and the rules forbid opening it | the board line now; the `tasks` rows with telemetry T2 |
| A2 | a task touches `nixosModules/`, `hosts/`, or `flake.nix`'s host config | the switch and its closure: the two build commands; the delta labelled a **prediction** — the packages and units the change is expected to add or drop, and why (no command can produce it before the code exists, so it is never written as a fact); the measured delta (`nix build .#nixosConfigurations.core.config.system.build.toplevel`, `nix store diff-closures /run/current-system ./result`, run on the landed tree) required under `## Operator` before the switch line ships; the user units to start by hand; the rollback generation command | the operator's "SWITCH #N DONE" board line quotes the prepared commands; the measured delta is recorded beside the prediction; a mismatch is a finding against the plan | now (the board line) |
| A3 | a task needs a credential, a DNS name, a password file, a reboot, a file the operator owns, or a top-up of OpenRouter credits before a wave that starts more than one seat (A9) | one command per item with a placeholder and the path it lands in (`umask 077; install -m600 /dev/stdin <path>` shapes), listed under `## Operator` and echoed in the board's "Operator owns" sentence | the operator ran each command unchanged, counted only from the operator's own message that closes the items (the one reply at ~22:30 that closed four items is the countable unit); the board line the orchestrator writes is a self-report and is declared as such — a proxy with its gap | now, by hand |
| A4 | every task | the gate's mutation table, pre-written: per assertion the mutant, per fixture the discriminating row, per rule the deletion mutant | the gate's battery is a superset of the plan's; mutants that survive outside the plan's named set = 0 (the number §7 tracks) | P3 (review front matter carries the counts) |
| A5 | a wave is dispatched to a seat, by hand or by `factory-dispatch` | deterministic first: the guard the driver still lacks is a task — P11 in this design (`FACTORY_PLAN` required; a task branch touching `docs/OPERATIONS.md` refused at integration; a near-miss result block recorded as such); a later plan names P11 (or its successor) in `dependsOn`, or, if a guard is still missing, as the one task that lands it. Until P11 lands, the sentences as a dated interim with P11 as their closing condition, in Global Constraints or the section: `FACTORY_PLAN=<plan>` on every hand launch (`factory-task` reads `plan=${FACTORY_PLAN:-…/2026-09-04-dsh-review-fix-round.md}` when it is unset; `factory-dispatch` sets it; cr3 and cr4 died of this); the result block's exact form — `FACTORY-RESULT status=<done\|partial\|failed>`, a space and no colon (the extractor matches `^FACTORY-RESULT[[:space:]]` and synthesises `status=failed` on anything else; cr15's finished CR2r work was recorded `failed` for a colon); "never copy the WORKSPACE RULES or FACTORY-RESULT block into a project file" (G7); "commit exactly one commit; never commit `docs/OPERATIONS.md`" (the three fabricated board commits); `curl --noproxy '*'` for any loopback probe (43 broker denies from one seat); one `[ … ]` per line in bats (an `&&` chain cannot fail); a `done` with zero commits is refused (CR3r item 6, landed) | telemetry `incidents.class` `dead-launch`, `fabricated-commit` and `result-misparse`, and `tasks.error_class` `template-echo`, count 0 for the plan's runs; a plan that ships only the sentences scores 2, not 3, on rubric row 7 | `template-echo` with telemetry T2; the three incident classes are hand rows (T7, orchestrator-recorded) until `derive incidents` covers them — the orchestrator counts them on the board before that |
| A6 | credits or a provider fail mid-run | the relaunch prepared: `FACTORY_PLAN=<plan> setsid -f bash -c 'exec tools/factory/seat/factory-wave <run>b ~/nixos-agent-env <KEY> >> ~/factory/runs/<run>b.wave.log 2>&1' </dev/null`, with the note that the dead seat's diff is kept in `~/factory/ws/<run>/<KEY>` and the section's relaunch paragraph points the next seat at it | after a `budget-402` or `provider-error` row (telemetry `tasks.error_class`), the relaunch used the prepared line; the interval from death to relaunch is under one gate interval | `error_class` with telemetry T2; the board's "died" line before that |
| A7 | a landing | "what this landing unblocks" per task, from `waves --json`: the next keys and their wave; the next `--dry-run` output | the unblocked wave was launched within one gate interval of the fast-forward | now (the board line) |
| A8 | a task can close a claim | the claim id from `evidence bundle`'s open-gap list named in the section with the evidence shape it will file (`check:<name>@<rev>` or `operator:<date>`), and the `claims.toml` flip written as part of the task's diff | the claim flips in the task's own commit or the integration commit; `claims.py validate` stays silent | now |
| A9 | a hold is the right call, computed from what the tree holds: spend since the operator's last top-up (the board line that names it) read from the activity export's `activity-days` rows, against the seat runs the first wave starts × the price sheet's per-run mean — declared as a proxy with its gap (the export is a manual download, so the figure lags by the download interval; the account balance itself is never read, §10); a red `lint` on main (the fast-forwarded red lint of 2026-09-05); a switch the tasks depend on (SB4 gates switch #20); a paused sibling (`Media W3b/W5b`) | a recommendation to hold the launch, with the reason and the resume condition; the top-up itself is the operator's item under A3 before any wave that starts more than one seat | the recommendation is on the board before the launch that would have died; deaths of class `budget-402` after a recommended hold = 0 | the spend proxy with telemetry T4; the lint, switch and pause facts now |
| A10 | the operator will be asked something | the question pre-asked in Step 1 with a recommendation and a default (Helm Home: Discord's isolation grade) | the operator answered in one word or one letter; questions per plan ≤ 3 | now |
| A11 | the session will reset | the plan is written in one turn; the handoff line for `docs/OPERATIONS.md` is prepared ("on the seat: …; in gate: …; next: …") | the next session's START HERE names the plan's state without re-reading the plan | now |
| A12 | a re-plan is needed (rule A1) | the re-plan is written in replan mode (§6.1) from the existing plan and the rejecting review: the `<KEY>r` section is appended with every rejection item, every deleted test's replacement, the fresh-workspace recipe (`git fetch -q ~/factory/ws/<run>/<KEY> task/<KEY> && git cherry-pick -n FETCH_HEAD`), and the rule that replaces the enumeration the gate rejected; every prior typed heading survives byte-intact (the guard's rule) | the re-plan's first gate approves (today: OG1r, OG1r2, R3r, CR2r, CR3r were each rejected once more) | now (the gate verdict); `round_kind` with telemetry T3 |
| A13 | a task adds or edits a hook (`.claude/settings.json`, `githooks/`, a seat hook), or adds a second reader of something the tree also derives (the queue block, `docs/MAP.md`, a `.review.md`) | for each consumer, which interpreter and which tree it resolves (the live generation's packaged `evidence`, or the tree's `pkgs/evidence/tasks.py`); the harness loop-guard field the hook must honour (`stop_hook_active`) and the degrade-to-allow behaviour on every internal failure — each with its named mutant (drop the field check → the loop fixture fails; exit non-zero on a missing interpreter → the degrade fixture fails) | `incidents.class` `ritual-block` = 0 for the plan's landings; no override file placed by the operator | the board now; the hand row with telemetry T7 |
| A14 | a task adds or tightens a deny rule (the orchestrator guard, the seat hook guard, the broker policy) | the commands the new rule will refuse, listed from the current runbooks (`docs/runbooks/session.md` "Guard — what the orchestrator refuses to do", `lanes.md`), the board's launch/integrate recipe and the plan's own Dispatch section — each with who runs it afterwards; any that fall to the operator written as one command under `## Operator` (the `rm .claude/ritual-override` of ~22:30) | guard denials of the orchestrator's or the operator's own recipe commands within one session of the landing = 0; operator commands not pre-written = 0 | the board now; `guard-denials` with telemetry T13 |

The six surprises of 2026-09-05 evening, each under the row whose trigger
could have fired at planning time: the dead launches cr3 and cr4 (A5 — the
`FACTORY_PLAN` sentence as the interim, P11's refusal of an unset plan as the
guard); the colon result block that recorded cr15's finished CR2r work as
`failed` (A5 — the exact block form, and P11's near-miss check); the three
fabricated board commits (A5's one-commit sentence as the interim, P11's
refusal of a commit touching `docs/OPERATIONS.md` as the guard, and A1's
branch reset in the landing recipe, which is what actually dropped them); the
Stop-hook loop of 19:20–19:55 (A13 — CR1 wired a second consumer, the Stop
hook running generation 43's packaged `evidence`, of a block pre-commit
regenerates from the tree's `tasks.py`; "a Stop hook allows on
`stop_hook_active`" became a field lesson only at 19:55, so no sentence row
could have held it); the guard refusing the orchestrator's own commands and
the `rm` of the override that fell to the operator at ~22:30 (A14 — OG1 added
a deny rule and no plan listed the recipe commands it would refuse; A3's
trigger names things a task needs, and a file that does not exist yet is not
observable from §2's inputs); the 402 deaths of cr10 and cr11 at 21:50 (A6 the
relaunch; A9 the spend proxy; A3 the top-up as the operator's item).

## 5. Rigor — the plan-quality gate before dispatch

### 5.1 The rubric (14 rows, 0–3 each, 42 points)

The comparison's ten rows, with two rows split and three added. Each row has
its anchor for 3 and the mutant or proxy that makes the score falsifiable.

| # | criterion | 3 means | 0 means | how a judge falsifies it |
|---|---|---|---|---|
| 1 | spec coverage | every spec item maps to a task or an explicit `out:` | items silently dropped | pick a spec item at random; find its task |
| 2 | correct facts | zero wrong facts; every fact carries its command | four or more wrong facts | re-run three cited commands; compare |
| 3 | self-contained sections | `factory-brief` output alone lands the task: paths, signatures, code or test bodies, no "similar to", no "read X and copy its shape" | the section is a list of topics | run `tools/factory/seat/factory-brief <draft> <KEY>` (read-only; the rules name it) and read that output with the rest of the plan hidden; list what is missing |
| 4 | TDD discipline | a red command and its expected red output per task, then green by check name | "add tests" | delete the red step; is anything lost? |
| 5 | mutant per assertion; discriminating fixtures | every assertion names its one-line mutant; every fixture has the row that makes it discriminate (second gap, flapping run, one payload per rule, every enum arm, the default branch) | fixtures of one row; no mutants; a contract item that names a proof shape ("a fixture listing or an assertion over the layout") but no mutant (bk3 · B1b) | pick two assertions; name a mutant that survives them; for every proof shape named without a mutant, write the mutant it needs — that is the survivor |
| 6 | interfaces and error contracts | every producer of every field; every enum arm; exit and stdout on every internal failure; which tree a derivation reads | a guard that can never fail; a stream with no id contract | ask "what happens when stdin is a terminal / the payload nests 1,000 deep / the file is absent" |
| 7 | rules, not enumerations | boundaries are stated as rules (tokenise, any token, every ancestor, every producer); a failure the driver can refuse is a guard task, not a sentence | a list of spellings; a warning where a guard belongs | write one spelling outside the list; a plan that ships a sentence where a driver guard belongs scores 2 |
| 8 | waves, touches, conflicts | waves derived from `dependsOn` (the peel-off groups `tasks.py waves` prints); explicit `touches`; `conflicts` run and its hits sequenced | no waves; globs in `touches` | run `conflicts` on the scratch copy (Step 3's form) |
| 9 | invariant awareness | brief §3 named where it binds; no key in a Nix expression; no widening of an agent's reach | an invariant silently touched | grep the plan for `/var/lib/secrets`, `sudo`, `systemctl` |
| 10 | operator steps and rollback | one command each with acceptance and expected output; the switch closure; the rollback generation | one paragraph of prose | run the dry forms |
| 11 | anticipation | §4's rows present where their trigger applies: dispatch lines, switch delta, prepared relaunch, claims to close, questions pre-asked, the hook and deny-rule tables | none | for each trigger in §4 that applies, find the artefact |
| 12 | economy | nothing restated; facts once; no appendix repeating the inventory | > 3× the shortest complete plan for the same spec | word count against the spec-to-task map |
| 13 | format and graph compliance | `parse_plan` reads every task; `check` empty; real check names; byte-exact subjects; no typed heading in the draft while it sits under the plans glob | the graph cannot read it | until P1: the scratch copy with the draft, a one-repo `--repos` file and `--runs-dir /nonexistent --store /nonexistent` (Step 3; the `--root`-only form cannot see the draft and scores 3 unconditionally); after P1: `tasks.py check --draft` |
| 14 | judgement calls | every open decision stated with the reason and the alternative; ≤ 3 operator questions each with a recommendation | decisions hidden in tasks | list the decisions; count the reasons |

### 5.2 The panel

Three judges, each blind to the author's transcript and to each other, each
receiving only the spec, the draft, read access to the tree, and the rubric:

| judge | model / effort | lens | route |
|---|---|---|---|
| J1 | Sonnet, high | the implementer: "land task N with only its section; list what you could not do" | claude (`role = review, kind = docs` row is Sonnet medium; high is set for this role) |
| J2 | Sonnet, high | the reviewer: "for each assertion, name a mutant that survives; for each rule, a spelling outside it" | claude |
| J3 | Opus, high | the whole plan: facts, invariants, waves, judgement (`role = review, kind = code` row) | claude |

Scores are the per-row **median** of the three. When the seat can run a judge
job through its unit (after seat-behind-broker lands), J2 becomes DeepSeek V4
Pro via `factory_route --route openrouter review docs <size>` — the second
model family the comparison asked for — and the judgement record says which
J2 ran; §9 Q1 states what that judge sends and over which route. Judges are
prompted to refute first ("default to the lower score when unsure"). A judge
that returns no score is asked once more; if the panel is still short of
three, the decision is `panel-short` — no dispatch, and no two-judge bar is
defined — and the record lists the judges that answered and the lens that did
not.

### 5.3 The threshold and what happens below it

Dispatch at **34 of 42** (81 %) *and* no median below 2 on rows 2, 3, 5, 6, 7
and 13 — the six rows that account for the 42 plan-caused rejections. Below
the threshold the draft is revised against the judges' errata (each erratum
names the row, the task, the finding and the fix) and re-judged; at most two
revisions, then the operator sees the scores and decides. A plan is never
dispatched on the author's word. The number 34 is a starting point and is
**unmeasured** (owner: the P10 report): the comparison's three plans were
scored on ten rows of 30 — 21, 26, 28 — and have not been rescored on the
fourteen rows; mapped proportionally (21/30 → 29, 26/30 → 36, 28/30 → 39 of
42) it falls between the rejected house plan and the two clean arms, a proxy
declared with its gap (the four new rows are unscored on them; a rescoring by
the designer alone would be one judge of the author's own model family, the
bias the comparison declared). After ten judged plans the P10 report proposes
the score that separates plans landing first try at ≥ 70 % from the rest; the
move lands as a commit that cites the report line, like a routing row, and the
record says when it moved. The threshold never moves itself.

Cost of the gate, at list prices and today's plan sizes: each judge reads
1–4k words of spec, 2–13k of plan and the touched files — of the order of
100–250k input tokens; Sonnet at $2 in / $10 out, Opus at $5 / $25: roughly
$1–3 per judging round for the three. One avoided rejection repays it (§1).

### 5.4 The record

One file per judged plan, `docs/reviews/plan-judgements/<date>-<name>.md`,
with a front-matter block between two `---` lines and prose below:

```
plan: docs/superpowers/plans/2026-09-06-helm-home.md
spec: docs/superpowers/specs/2026-09-04-helm-home-design.md
author: fable            # fable | dsh:<model> | hand
effort: max              # the drafter's effort; judgeOnly passes it in args
words: 6140
tasks: 9
judges: [sonnet, sonnet, opus]   # the judges that answered
judges_dropped: []                # the lens that stayed silent after one re-ask
scores: [3,2,3,3,2,3,3,3,3,3,2,2,3,3]   # rows 1–14, medians
total: 38
self_score: 40
threshold: 34
decision: dispatch      # dispatch | revise | revise-exhausted | panel-short
revision: 1
```

The telemetry store ingests it as a derived stream (§7). The body keeps the
errata list and each judge's reasons, so a later reader can see why a row
scored as it did. The judgement of a dsh-written draft is the same file with
`author: dsh:<model>`.

## 6. Integration

### 6.1 Claude Cowork — the pinned workflow `.claude/workflows/plan.js`

`.claude/workflows/` does not exist on this host today; the Workflow tool
resolves a named script from that directory (project scope) or from
`~/.claude/workflows/` (user scope), and `tools/factory/dark-factory.js`
already has the shape a pinned script needs (`export const meta = { name,
description, whenToUse, phases }` as a pure literal, then a body using
`agent()`, `parallel()`, `pipeline()`, `phase()`, `log()` and the `args`
global; no `Date.now`, no `Math.random`, no filesystem calls in the script
itself — agents do the reading and writing). Appendix D is the runnable
draft. Its shape:

1. **Packet** — five Sonnet readers in parallel; the drafter waits for all
   five: mechanical (§2.1, commands pasted), record (§2.2 R1–R4, R6: the
   classes of similar tasks' rejections), field (R5: incidents since the last
   plan and the driver's contract), operator (§2.3), target (§2.4). Each
   writes one file under `<scratch>/packet/`. The mechanical reader returns
   `checkEmpty`, set from `tasks.py check`'s own output; the script refuses to
   draft unless it is `true`.
2. **Draft** — one Fable agent at effort max writes the plan to
   `<scratch>/draft-0.md` (never under `docs/superpowers/plans` yet), answers
   Appendix A's eight questions per section in a sidecar, and returns the
   operator questions.
3. **Judge** — J1, J2, J3 in parallel with the schema of §5.4; the script
   computes medians in plain JavaScript, re-asks a silent lens once, and
   records `panel-short` rather than deciding on two.
4. **Revise** — while the total is under the threshold and rounds < 2: Fable
   revises against the errata; re-judge.
5. **Ship** — one Sonnet agent copies the passing draft to
   `docs/superpowers/plans/<out>` with the Write tool. The orchestrator
   guard's rule is that no typed heading may disappear from a plan file
   (`missing_headings` in `tools/orchestrator-guard.sh`): a new file has none
   to lose, and a whole-file Write that keeps every existing heading is
   allowed. It then runs `tasks.py check`, `conflicts`, `waves --plan <out>
   --next` and `factory-dispatch <run> ~/nixos-agent-env <out> --dry-run`,
   files the judgement record and the concept file, and returns the dispatch
   lines. It never launches; the operator or the orchestrator does, after
   reading.

**Replan mode.** `args.replan` (the existing plan's path) with `args.rejection`
(the rejecting review's path) hands the drafter the plan and the review; the
draft is the whole file with the new `<KEY>r` section appended and every prior
typed heading byte-intact. Before the Write, Ship runs the guard's own check —
the `### ` lines of the existing file must all be present in the draft, a
superset of the guard's typed-heading rule — and refuses otherwise. 11 of the
58 chains of 2026-09-05 took this path; without the mode the workflow could not
express it.

Invocation: `Workflow({ name: 'plan', args: { spec, out, name, date, since,
scratch } })`; `args.judgeOnly: true` with `args.draft` (and `author`,
`effort` for the record) runs stages 3–5 only, which is how a dsh-written
draft (§6.2) or a hand-written plan is judged by the same panel;
`args.replan` with `args.rejection` runs the re-plan. Models per role follow
the factory policy: Fable plans and revises, Sonnet reads and ships, the panel
is two Sonnet and one Opus; every `agent()` names its model (an omitted model
inherits the session's, which the policy calls a bug). Effort: readers `low`,
judges `high`, drafter `max`.

Where it lives once the per-flake Claude workspace lands (spec
2026-09-02-claude-workspaces): the same relative path inside that project's
`.claude/`, moved with it; nothing in this design depends on where
`CLAUDE_CONFIG_DIR` points.

### 6.2 dsh — a skill, a profile, a routing role

A seat runs the same process for a *draft*; the panel of §5.2 judges it.

- **Skill.** `~/flakes/dsh-harness/skills/planning/SKILL.md` (frontmatter
  `name: planning`, `description: write a typed implementation plan from an
  approved spec under docs/superpowers/specs for this house's dark factory;
  use when handed that spec path and an output path under
  docs/reviews/plan-drafts`), with `references/inputs.md` (§2 as commands),
  `rubric.md` (§5.1), `anticipation.md` (§4), `section-checklist.md`
  (Appendix A) and a `judge-prompt.md`. The catalog reaches a seat through the
  existing symlink (`ln -s ~/flakes/dsh-harness/skills
  ~/.local/share/dsh-openrouter/skills`; the wrapper warns, and does not
  refuse, when it dangles). Claude agents never write inside
  `~/flakes/dsh-harness`: the skill lands through that repo's own gate (grep
  gate plus `node --test`, as H2c did).
- **The catalog already has a plan skill.** `~/flakes/dsh-harness/skills/
  writing-plans` (description "Use when you have a spec or requirements for a
  multi-step task, before touching code") fires on the same trigger and
  mandates `### Task N: [Component Name]` — a heading the graph cannot read.
  `planning` supersedes it for house repos: P8 re-scopes `writing-plans`'
  description to repositories without a typed graph (no `docs/superpowers/
  plans`) and gives `planning` the house trigger above; the dsh-harness grep
  gate refuses two SKILL.md descriptions that both claim a spec and a plan.
  `subagent-driven-development` fires on execution ("executing implementation
  plans"), not on planning; its five-round fix loop contradicts rule A1 and is
  noted for the harness board, not changed here.
- **Profile.** A headless job: `DSH_HOME` per job as `factory-task` already
  does, `dsh-openrouter --headless "$(factory-plan-brief <spec> <out>)"`,
  where `factory-plan-brief` (new, beside `factory-brief`) prints the packet's
  mechanical part, the field part a script can produce (the driver's contract
  anchors by fixed grep — the `plan=${FACTORY_PLAN:-` line, the `extract_field`
  function and its `status=` pattern, `factory-integrate`'s header comment —
  and the board's START HERE block and the log's paragraphs since the given
  date, verbatim), the operator file, the spec, the rubric and the rules, and
  names the one output file `docs/reviews/plan-drafts/<date>-<name>-<model>.md`
  — outside the graph's glob, so a draft can never become a phantom task. The
  seat's hook guard applies unchanged; the seat reads the tree and writes one
  file. After seat-behind-broker lands, the same job runs as `seat@<id>` with
  the brief in the job directory; the job directory already carries `model`
  and `effort`, so nothing here changes with the migration.
- **Routing role.** `ROLES` in `tools/factory/route.py:38` and the role check
  in `tools/factory/seat/factory-lib.sh` gain `plan`; the four dsh-harness files
  that duplicate the role list (`AGENTS.md`, `skills/using-superpowers/
  references/dsh-tools.md`, `skills/subagent-driven-development/SKILL.md`,
  `README.md`) and its two prompt templates change in lockstep, or the H2c
  defect recurs. **No `plan` row is written**: until the measurement plan of
  §8 exists, a lookup for `plan docs <size>` falls through to the openrouter
  default (`deepseek-v4-pro-0813`, medium), and the judgement record's
  `author:` field says so. Kind is `docs`; size is §2.4 T2's rule by spec
  length. GLM 5.3 and Kimi K3 stay picker extras with no row ("do not select
  them by hand", AGENTS.md) until priced and measured.
- **Judged the same way.** `Workflow({ name: 'plan', args: { judgeOnly: true,
  draft: docs/reviews/plan-drafts/…, spec, name, date, scratch, author:
  'dsh:<model>', effort } })`. A draft at or above the threshold is promoted
  by the orchestrator with one Write into `docs/superpowers/plans/`; the
  judgement file carries `author: dsh:<model>`.

### 6.3 The SessionStart hook — what a planner should see

Today the hook injects the board block, the bundle, the brief and the in-flight
table with per-part caps (3,000 / 2,500 / 1,500 / 1,200 chars, total 8,000).
Missing for a planner: the record and the operator model. Cheaply:

- **The record, one line in the brief.** `tasks.py brief` gains a line
  `Record (7 d): N rejections, M plan-caused (vacuous a, missing-case b,
  underspecified c, wrong-fact d)` computed from `docs/ledger/
  plan-defects.toml` (the filed corpus) plus the front matter of reviews filed
  after P3 lands. Same renderer, same interpreter, under the existing
  1,500-char brief cap; a missing field degrades to `Record: unavailable`.
- **The operator model, one pointer.** A fifth part capped by
  `SESSION_START_CAP_OPERATOR` (default 600): the first lines of
  `docs/board/operator-model.md` — the pauses and the open decisions — and the
  path. The full file is read by the planner's operator reader, not injected.

Both are text the tree already holds or derives; neither reads a transcript or
the store's bodies; the hook stays under two seconds and never fails the
session.

## 7. Metrics

Aligned with `docs/superpowers/specs/2026-09-05-telemetry-store-design.md`
(read in full): its `gates` stream (verdict, majors, minors, `mutants_killed /
mutants_total`, `round_kind`) and `tasks` stream (kind, size, model, effort,
usage, `error_class`) already carry most of what planning quality needs. This
design adds two fields and one stream, all under that spec's policy check
(identifiers, enums, numbers, hashes, ≤ 200-char notes; no body text):

- **`gates.plan_defect`** — the primary cause, enum `none | vacuous |
  missing-case | underspecified | wrong-fact | implementer | process`, and the
  optional **`gates.plan_defect_secondary`** from the same enum (five corpus
  rows carry one: G2 vacuous, R5 wrong-fact, CR2r implementer, G12 and DA1
  missing-case). Written in every new review's front matter by the gate (task
  P3); the 59 rejections of the corpus are backfilled into `docs/ledger/
  plan-defects.toml`, and the filed reviews stay byte-unchanged.
  **Tie-break (2026-09-08, from the re-read
  `docs/reviews/2026-09-08-plan-defect-re-read.md`):** `implementer` is the
  primary only when the plan named the **mutant** for the requirement the
  seat missed, or the seat violated a contract stated verbatim in the section
  it was given and could have satisfied as written; when the plan named only
  the requirement or a proof shape, the primary is the plan class the gap
  fits — `vacuous` if the shipped test cannot fail on a named requirement,
  `missing-case` if the case is never named, `underspecified` if the contract
  is left open — and `implementer` is the secondary whenever the seat's own
  execution independently fell short.
- **`plans` stream** (kind `plan-judgement`, derived from
  `docs/reviews/plan-judgements/*.md`): `plan`, `spec`, `author`, `model`,
  `effort`, `words`, `tasks`, `judges`, `judges_dropped`, `scores[14]`,
  `total`, `self_score`, `threshold`, `decision`, `revision`, `judged_ts`. Key
  `plan`+`revision`.

The joins are by plan file name (`tasks.plan`, `gates` via `tasks.py`'s
`chain_root`). Reports (`evidence report plans`, after telemetry T10a — the
join and the n-gate — and T10b — the report surface):

| number | definition | today | first target |
|---|---|---|---|
| first-try landing rate | chains approved at their first gate ÷ chains gated, per plan and rolling 20 chains | 28 / 58 = 48 % | ≥ 70 % over the next 20 chains |
| plan-caused share of rejections | `plan_defect ∈ {vacuous, missing-case, underspecified, wrong-fact}` ÷ rejections | 42 / 59 = 71 % | < 40 % |
| re-plan rate | chains with a `replan` round ÷ chains | 11 / 58 = 19 % | < 10 % |
| survivors outside the named set | per gate, mutants that survived and were not in the plan's mutation table | **unmeasured** (19 reviews carried counts in a parseable form when the research slice counted 128) | 0 per gate, measured from P3 on |
| rubric score before dispatch | `plans.total` at `decision = dispatch` | none judged yet | every dispatched plan ≥ 34; the score's correlation with first-try landing reported at n ≥ 10 plans, per row |
| rework rounds per landed task | fix + re-plan rounds ÷ landings | 30 rounds / 58 chains (from the per-plan counts) | < 0.3 |
| tokens per landed task | seat `tasks.usage` + gate `gates.gate_tokens` for the chain | seat side measured (200 results); gate side **unmeasured** outside the eight itemised gates | −30 % against the 2026-09-05 baseline once the gate side is recorded (telemetry T3) |
| operator interventions per plan | commands the operator ran that the plan did not prepare, plus prepared commands the operator edited, counted only from the operator's own messages that close an item (the orchestrator transcribes them to the board: a self-reported proxy, gap declared) | **unmeasured** | ≤ 1 per plan |
| time in gate | seat finish → review commit, median | 14 min (telemetry §2.4) | unchanged — the target is fewer gates, not faster ones |
| questions per plan | operator questions asked at Step 1 | — | ≤ 3, each answered in one word |

A rubric row that does not predict landings after 20 plans is dropped from
the threshold rule (not from the record); a row that predicts strongly gains
weight only by a commit that cites the report line. Every number prints with
its n and refuses a conclusion under n = 5, as the telemetry spec's reports do.

## 8. Proposed tasks

Ordered by payoff per effort. "Depends on" is prose; nothing here is a typed
heading, and the task graph does not read this file. Acceptance names real
checks (`unit`, `lint`, `factory-unit`, `evidence-unit`, `host-core`). Two
items that were tasks in the first draft — the first plan through the agent
and the plan-writing measurement — are plans, not tasks, and sit below the
table.

| # | title | size | depends on | acceptance | what makes it falsifiable (mutant or proxy) |
|---|---|---|---|---|---|
| P1 | `tasks.py check --draft <file>`: parse a draft outside the plans glob, run every `check` rule against the live graph plus the draft, verify acceptance names against `docs/MAP.md`, byte-check commit subjects, and print the draft's waves and conflicts (folding Step 3's scratch-copy recipe into one command) | S | nothing | `evidence-unit` gains fixtures: a draft with a duplicate key, a dangling `dependsOn`, a fake check name and a leading-glob `touches` each fail; the four house plans of 2026-09-05 pass; `lint` | mutation: drop the MAP.md lookup → the fake-check fixture passes and the test fails; drop the glob rule → the F9 fixture passes |
| P12 | a JavaScript formatter and linter in treefmt and the `lint` check (closes claim `js-formatter-linter-missing`, owner orchestrator, review by 2026-09-19; the flip in the same diff, A8) | S | nothing | `lint` fails on a fixture `.mjs` with a deliberate lint error and passes on `tools/factory/dark-factory.js` and `tests/factory/*.mjs` as formatted; the claim's evidence is `check:lint@<rev>`; `claims.py validate` silent | mutation: drop the JS glob from treefmt → the fixture passes and the test fails |
| P11 | the driver guards behind A5, deterministic: `factory-task` and `factory-wave` exit 2 with a message naming `FACTORY_PLAN` when it is unset (the 2026-09-04 default goes); `factory-integrate` refuses to merge a task branch whose commits touch `docs/OPERATIONS.md` (logged `REFUSED <KEY>`, exit non-zero, like a conflict); `factory-task` records a near-miss result block (`^FACTORY-RESULT:` with a colon, or a `status=` outside `done\|partial\|failed`) verbatim in `FACTORY-NOTES` as `result-misparse: <line>` while the status stays `failed` (fail closed); the WORKSPACE RULES block quotes the grammar | S | nothing (no open task touches `tools/factory/seat` tonight) | `unit` (`tests/unit/80-seat-driver.bats`): the unset-plan fixture exits 2 and names the variable; the fabricated-commit fixture is refused and the sibling key still merges; the colon fixture's notes line carries the seat's line; `lint` | mutation: restore the default plan → the unset fixture passes and the test fails; drop the path check → the fabricated commit merges; drop the near-miss capture → the notes line reads "(none given)" |
| P2 | `factory-plan-brief <spec> <out>` and the packet script: run M1–M13 in order, paste outputs under their commands with a timestamp (M3 to a file), append the scripted field part (§6.2), the operator file and the spec, refuse when M1 is non-empty | S | P1 | `unit` (bats): a fake graph that fails `check` makes the brief exit 2 and print nothing; a sound fixture prints the thirteen parts in order; `lint` | mutation: run the parts in parallel → the order test fails; ignore `check` → the refusal test fails |
| P3 | `docs/ledger/plan-defects.toml` seeded from Appendix B (59 rejections: primary class, optional secondary, run, key, review path; filed reviews byte-unchanged); new reviews carry `plan_defect` (and `plan_defect_secondary`) in front matter; `tasks.py brief` prints the 7-day record line from the ledger plus front matter; the lint gate refuses a new review without the field | XS | telemetry T3 (the front-matter block) or its equivalent in this repo | `lint` refuses a review whose block lacks `plan_defect` or carries a value outside the enum; the brief line's counts are derived from the ledger and tested with a fixture whose class distribution differs from the corpus (3 / 1 / 2 / 0); on the corpus it prints 14 / 14 / 8 / 6 of 42; `unit` | mutation: accept `plan_defect: maybe` → the lint fixture fails; count only rows without a secondary → the fixture with two secondaries fails |
| P4 | `docs/board/operator-model.md` (derived from brief §3/§7/§8, the decisions, the board's Operator-owns and pauses; no personal data beyond the repo's) and the fifth SessionStart part with its cap | XS | nothing | `unit` (bats): the hook prints the part, capped at 600 chars with the truncation line; the file's pauses section matches the board's (a lint grep); `lint` | mutation: remove the cap → the 601-char fixture fails; let the hook fail when the file is absent → the missing-file test fails |
| P5 | the pinned workflow `.claude/workflows/plan.js` (Appendix D), the rubric and judge prompts as files under `tools/factory/plan/`, tests in `tests/factory/plan.test.mjs`, and the `factory-unit` copy list in `flake.nix` extended to them (it copies by name, no glob) | M | P1, P2, P12 (so `lint` covers its JavaScript); B1 (ready) and SB4 (running) both touch `flake.nix` — P5 waits for both to land | `factory-unit`: the script parses, `meta` is a pure literal, medians and the six-row floor behave on fixtures, `judgeOnly` skips the packet, a mechanical reader returning `checkEmpty: false` stops the run before any drafter, a silent lens yields `panel-short`, the replan heading check refuses a draft that lost a heading; a dry invocation against a fixture spec writes nothing under `docs/superpowers/plans`; `lint` | mutation: median → mean → the `[3,3,0]` fixture fails; drop the six-row floor → a 35-point draft with row 5 at 1 dispatches and the test fails; delete the `checkEmpty` gate → the refusal fixture drafts and the test fails |
| P6 | the judgement record: `docs/reviews/plan-judgements/` with the front-matter contract, `evidence ingest judgements` → the `plans` stream, the policy allowlist entry | S | telemetry T1; P5 | `evidence-unit`: a fixture judgement ingests to one row; a 201-char note is refused; a body never enters the row; `lint` | mutation: write the errata text into the row → the forbidden-name fence fails |
| P8 | the dsh skill `planning`, `factory-plan-brief` wired as the headless profile, `plan` in `ROLES` and the six harness files in lockstep, `writing-plans` re-scoped to repos without a typed graph, no row | S | P2; the dsh-harness gate | `factory-unit`: `route.py check` accepts role `plan` and `lookup --route openrouter plan docs S` returns the default row; in dsh-harness: the grep gate finds the role list identical in all six files and no two SKILL.md descriptions claiming a spec and a plan; `lint` | mutation: add the role to five files → the lockstep grep fails; leave `writing-plans`' description unchanged → the two-claimants grep fails |
| P10 | `evidence report plans`: rubric total and per-row score joined to first-gate outcome, survivors outside the named set, interventions per plan; after ten plans, the threshold proposal line | S | telemetry T10a (join, n-gate) and T10b (report surface); P3, P6 | reproduces §7's "today" column from the backfill; refuses n < 5; `evidence-unit` | mutation: lower the n gate to 2 → the refusal fixture fails |

P1 first: it turns the format-and-graph row of the rubric into one command
and closes the class of defect that cost G2, G5 and the FD1 dispatcher. P12,
P11 and P4 are independent of it and of each other and run as one wave beside
it; P2 and P3 follow P1. P5 is the product. The `touches` overlaps to watch:
P3 and P4 both edit `tools/session-start.sh` and its bats file; P1 and P3 both
edit `pkgs/evidence/tasks.py`; P5 and P12 both edit `flake.nix` and the
treefmt configuration, and B1 (ready) and SB4 (running) are on `flake.nix`
tonight (`conflicts` lists cross-plan hits only once this plan is typed — run
it then, before the table is final); P11 edits the driver, which no open task
touches (`tasks.py json` filtered on `tools/factory/seat`: none).

**Plans that follow, not tasks here.** (1) The first plan through the agent:
Helm Home sub-project 1 (spec `2026-09-04-helm-home-design.md`, board decision
2026-09-05 ~23:30), one operator question (Discord's isolation grade); its
measure is the judgement file with `decision: dispatch`, the `--dry-run`
first wave, and its first-try rate reported against the 48 % baseline as a
proxy (n = 1) until five plans have run. (2) The plan-writing measurement the
comparison asked for: 3 specs × 2 samples × 2 models (DeepSeek V4 Pro high;
GLM 5.3 or Kimi K3 xhigh once priced), blind, judged by the §5.2 panel — about
twelve seat runs and twelve panel judgements, of the order of $50, needing the
price sheet extended and the operator's spend approval (§9 Q3); a `plan` row
is proposed only from its report, with rubric score standing in for landings
until the plans are executed. Each is a run of several seats and gates, the
size of the model- and effort-comparison plans, and is typed as its own plan
when the operator answers §9.

## 9. Open questions for the operator

Three questions; the rest of the first draft's questions are decided in the
text (below).

1. **The second judge's family — a data-path question.** Today all three
   judges run on the Claude side. Making J2 DeepSeek V4 Pro means the judge's
   request goes through the OpenRouter lane behind the broker with the lane's
   standing posture (`provider.zdr = true`, `data_collection: deny`, decision
   2026-09-03) and carries the spec, the whole draft plan, and whichever tree
   files the judge reads — the same route and the same classes of text a
   DeepSeek implementer seat already receives when it lands a task from the
   same plan (a section, the constraints, the tree). No new route and no new
   class of data; the panel gains the second model family the comparison
   asked for. Recommended: two Sonnet judges now and DeepSeek as J2 once the
   seat unit can run a judge job (after seat-behind-broker), or a DeepSeek
   judge from day one through a direct headless seat run per judged plan.
2. **The first plan.** Helm Home sub-project 1 as decided on the board
   (recommended; one question: Discord's isolation grade — recommendation: the
   same grade as the seat, a broker instance with an allowlist of Discord's API
   hosts only and no basket), or the smaller backup-audit plan as a dry run.
3. **Spend on the measurement plan.** About twelve seat plan-writing runs at
   the comparison's rates (Pro $0.61 per plan; GLM and Kimi unpriced) plus
   twelve panel judgements at $1–3 each — of the order of $50 (recommended:
   run it after five real plans have gone through the gate, so the panel is
   calibrated first), or skip the row and keep planning on the Claude side
   only.

Decided in the text, for the operator to veto: the threshold starts at 34 of
42 with the six-row floor and moves only by a commit that cites a P10 report
line (§5.3) — it is the agent's calibration knob, not a choice to make blind;
the workflow prints launch lines it never runs (`factory-dispatch … --dry-run`
touches nothing; §10 already refuses autonomous dispatch, so the printed line
is the operator's or the orchestrator's); the operator model is a repo file
(`docs/board/operator-model.md`, P4) derived only from text the repo already
holds — it discloses nothing new, and a planning subagent or a dsh seat cannot
read the orchestrator's memory; withdrawing P4 keeps it memory-only.

## 10. What this design refuses

- **Content mining.** The planner reads specs, plans, reviews, decisions, the
  board, `docs/MAP.md`, the ledgers, the driver's source and the tree. It
  never opens a seat transcript, a session file, a `wave-group-*.log`, a
  `dispatch.log`, a `.dsh-home`, a Claude project directory or the store's
  bodies; the record it learns from is verdicts, classes and counts. The
  `record` and `field` readers are told this in their rules.
- **Autonomous dispatch.** No plan is dispatched without a judgement file at or
  above the threshold, and the workflow never launches a seat, a factory or a
  switch: it prints the dry-run line and stops. Rule A1 stays: one fix round,
  then a re-plan, and the re-plan goes through the same gate.
- **Network access.** The workflow's agents make no request; the only remote
  calls are the models' own, through their existing routes. No OpenRouter
  balance check (A9's spend figure is the activity export the tree already
  ingests, declared as a proxy), no fetch of a vendor page (N19's wrong fact
  came from a page that 404s; the vendored catalog is the fact). A dsh
  planning seat has the same allowlist as any seat.
- **Widening any guard.** The workflow's agents run under the orchestrator
  guard as it stands: no typed heading disappears from a plan file, no shell
  writes to plan files, no history rewrites, no host mutation. The dsh
  planning seat runs under the seat's hook guard and the routing rule.
  `routing.toml` changes only by a commit that cites a report line, and so
  does the threshold; this design adds a role, not a row.
- **A plan without an operator section.** A plan whose tasks need a switch, a
  credential, a name, a reboot or a top-up and does not write those as one
  command each is scored 0 on row 10 and cannot pass the floor.
- **Judging by the author.** The self-score is recorded and compared; it never
  substitutes for the panel.

## 11. How the numbers were taken (2026-09-05, ~22:00–23:20 CDT)

- Reviews: `ls docs/reviews/*opus-review*.md | wc -l` (132 at 23:20; 24 dated
  09-04, 108 dated 09-05; 131 when the research slice counted). The research
  slice's verdict grep over bodies minus four approved files quoting a prior
  round (59 / 72, the 132nd file cr16 · CR3rb approved → 59 / 73). The
  first-line parse: `REVIEW_RE` from `pkgs/evidence/tasks.py` run over the
  tracked files at 23:20 — 105 parsed, 59 approved, 46 rejected, 27 unparsed
  (the first draft carried three inconsistent figures for this one count;
  the telemetry spec's T3 row — 104 / 58 / 46 / 27 over 131 — is the same
  measurement one file earlier). Root-cause classes are Appendix B's rows,
  counted by class (14 / 14 / 8 / 6 plan-primary; the research slice's
  headline 15 / 12 / 9 / 6 did not match its own rows and is dropped); the
  per-plan chain counts are its tally of the ten typed 2026-09-05 plans.
- The OG1 chain: `git log --since=2026-09-04 --format='%ci %s' | grep -iE
  'OG1'`; review volume `wc -w docs/reviews/*OG1*.md` (17,232 words over the
  five files).
- Commits: `git log --since=2026-09-04 --oneline | wc -l` read 331, 329 and
  328 at three times this evening; the count is not load-bearing and no
  sentence depends on it.
- Mechanical inputs: each command in §2.1 run once, read-only; `brief` timed
  at 1.7 s here and 0.5 s in the research slice (the `nix develop` entry
  dominates); `evidence bundle` 0.19 s; `inflight` 12 live lines and 215 stale.
- Spec sizes: `wc -w` on the four specs named in §2.4.
- Seat and gate costs: the effort and model comparison reports (per-task
  tables), the telemetry spec §1 row 6 (wall mean 673 s over 200 results) and
  §2.4 (14 min median seat finish → review commit), `docs/ledger/
  openrouter-prices.csv`, and the Claude list prices cached in
  `docs/decisions/2026-09-02-factory-model-policy.md`. Token totals for the
  corpus are bounds computed from the itemised range, not measurements.
- Tooling facts, by anchor text: `tools/factory/seat/factory-brief` (read in
  full; reads one plan file, prints to stdout); `factory-task`'s
  `plan=${FACTORY_PLAN:-…}` default and its `extract_field` / `status=`
  extraction; `factory-dispatch`'s `printf 'factory-dispatch: run %s plan %s
  groups: %s\n' … >>"$dispatch_log"` (the only line it writes there);
  `factory-integrate`'s header (merges `task/<KEY>` fetched from the
  workspace; never touches the repo); `tools/orchestrator-guard.sh`
  `missing_headings` (refuses only a disappearing heading); the lint check's
  one-repo `--repos` file in `flake.nix` (the "G5" comment) and the
  `factory-unit` copy list beside it; `tools/factory/route.py:38–49`,
  `docs/ledger/routing.toml`, `docs/ledger/repos.toml` (host-absolute paths),
  `.claude/settings.json`, `tools/session-start.sh`, `pkgs/evidence/tasks.py`
  (`REVIEW_RE`, `--root`/`--repos` handling), `dark-factory.js` lines 1–120;
  `ls .claude` (no `workflows/`); `~/flakes/dsh-harness/skills/` (fifteen
  skills; `writing-plans` and `subagent-driven-development` read); the
  telemetry spec's `error_class` and `incidents.class` tables and its T-table
  (T10 split into T10a/T10b).
- Open-task overlaps: `tasks.py json` at 23:24 filtered for non-landed tasks
  touching `flake.nix`, `tools/factory/seat`, `tools/session-start.sh`,
  `pkgs/evidence/tasks.py`: B1 (ready) and SB4 (running) on `flake.nix`, CR4
  (blocked) on `githooks/pre-commit`, none on the driver.
- Everything else is quoted from the named repo files; where nothing measured a
  thing it is marked **unmeasured** in the text.

---

## Appendix A — the eight questions every section answers before it ships

Derived from the 42 plan-caused rejections; the number in brackets is how many
of them the question would have caught (Appendix B's classes).

1. For every assertion: which one-line change turns it red? [14] A proof
   shape is not an answer — "a fixture listing, or an assertion over the
   layout" says where a proof could live, not what kills it; if the section
   cannot name the mutant, the item is decoration (bk3 · B1b, added
   2026-09-07). [+1]
2. For every fixture: which row makes the assertion discriminate — a second
   gap whose id sorts against its date, a flapping run, one payload per rule,
   every enum arm, the default branch rather than the injectable one? [the
   mechanical cause behind most of the 14]
3. For every boundary: is it a rule (tokenise; any token; every ancestor;
   every producer; validate as an address, not a shape), never a list of
   spellings? [14]
4. For every interface: which tree or file does it read, what does it emit on
   each internal failure (exit code, stdout), and who consumes each field? [8]
5. For every fact: which command produced it, pasted beside it, with the
   anchor text rather than a line number? [6, plus the G12r copy error]
6. Does any step's mandated output fail the task's own acceptance grep? [1]
7. For a fix round or re-plan: does the section carry every item of the
   rejection, and does every deleted test name its replacement? [2]
8. Does the section carry everything the seat will see — is `factory-brief
   <plan> <KEY>` the whole contract? [the G5 amendments and R10's touches gap]

## Appendix B — the 42 plan-primary rejections and the sentence each plan was missing

Seed of the `plan_defect` backfill (task P3): 43 rows — 42 plan-primary
(vacuous 14, missing-case 14, underspecified 8, wrong-fact 6) and one
process-primary row, sc1 · G2, kept here for its plan secondary (it is one of
§1's three process rows). A row with two classes names the primary first; the
second becomes `plan_defect_secondary` in the ledger. Run and key as in
`docs/reviews/2026-09-05-opus-review-<run>-<key>.md` (09-04 rows under the
`2026-09-04-…` names).

| run · key | class | the reviewer's finding (short) | the sentence the plan needed |
|---|---|---|---|
| a3 · W2-N6b | missing-case | `rollup --week --costs` prints a lifetime total under a window header; M10 survives | name the composed command as a case; no date-relative assertion that expires |
| a4 · N7c | missing-case | the audit log sits inside the project dir, so the audited party can erase it | say where the audit record lives and that its subject cannot erase it |
| a7 · N16 | wrong-fact | the activity export is account-wide; the lane was double-counted | state the export is account-wide; require an unjoined-bucket case |
| a9 · N19 | wrong-fact | "OpenRouter accepts only low/medium/high" is false; the cited page 404s | check the vendored catalog before writing a vendor fact |
| b3 · F9/BFIX | missing-case | a leading-glob `touches` disables the overlap check | name the glob and `**` case in the parallel-safety contract |
| b2 · F6 | wrong-fact | dsh resolves a skill's relative paths against the skill's own directory | state the resolution rule; assert from the skill dir, not the repo root |
| cr2 · CR1 | missing-case ×4 | 170 dead logs listed and the live ones truncated; the Stop reason not JSON-escaped; stdin hangs on a terminal; missing `evidence` blocks | live-only in-flight; JSON-escaped reason; non-blocking stdin; degrade-to-allow |
| cr6 · CR3 | underspecified | `setsid` without `-w`; `base:` is a branch name; `groups:` flattened | write the `run.meta` field grammar; say `setsid -w` |
| cr8 · CR2 | missing-case | the rule keys on the exact path; every directory spelling allows | one protected-path mechanism shared with the plans rule |
| cr15 · CR2r | missing-case (+impl) | the `-m` prose exemption never ends at a newline | a prose exemption defines its terminator set, newline included, and is proven against the base guard |
| ev1 · R1 | vacuous | reverting `http_connect` or deleting the SNI branch leaves 49 tests green | name the CONNECT and SNI mutants |
| ev1 · R5 | missing-case + wrong-fact | the only Flash rate deleted and not moved; an untrue sentence dictated by the plan | a fact deleted from one file appears in its replacement; no dictated prose the tree contradicts |
| ev1 · R8 | vacuous | one payload names both the port and the token, so deleting the token rule is invisible | one payload per rule |
| ev2 · E2 | vacuous | the fixture holds one gap; a sort assertion on a one-element list | two gaps whose ids sort against their dates |
| ev2 · E2b | vacuous | three ids happen to sort as their dates do | a late-sorting id with an early date |
| ev2 · E7 | vacuous | only the injectable `FACTORY_CHECK_CMD` branch is driven | test the default branch |
| ev2 · E7b | vacuous | no test ever drives a `fail` verdict | every enum arm has a case |
| ev3 · E6 | vacuous | history `(ok, fail, fail)` cannot distinguish first-of-run from earliest | a flapping fixture `(ok, fail, ok, fail)` |
| ev3 · E9 | vacuous | `_docs_equivalent → return True` leaves 24 tests green | the return-True mutant for every predicate the store trusts |
| ev3 · R3r | missing-case | the re-plan deleted the only test that passed a status argument | a re-plan that deletes a test names its replacement |
| fd1 · FD1 | wrong-fact | "the first line is the next wave" is false; the dispatcher offers blocked tasks | paste the real output shape; forbid re-deriving graph logic in the consumer |
| hr1 · H2 | wrong-fact | `FACTORY_ROUTING_TABLE` is read nowhere; setting it changes nothing | do not paste a mechanism into four files before it exists |
| mcf2 · P1flash | wrong-fact | the mandated header contains the literal the green grep forbids | no step whose output fails the task's own acceptance |
| mcp2 · P3 | vacuous | the guard is never reached under `--dump-config` | name the launch mode under which the guard runs |
| og1 · OG1 | missing-case | `..`, `./` and symlink paths escape the heading guard | name the reference function to port, not the file to read |
| og1 · OG1b | underspecified | the flag list under-enumerated; `--work-tree=` in the plan's own pattern allowed | a rule (tokenise; any write verb), never a flag list |
| og3 · OG1r | underspecified | one enumeration replaced by two; `nix develop -c git commit --amend` allowed | no enumerated boundary set, no enumerated launcher set |
| og4 · OG1r2 | missing-case | `mv <plan> /tmp/x` allowed; the plans directory unrecognised; 907 ms against a 300 ms acceptance | destinations as well as sources; the directory itself; honour cwd; cost the design before stating a latency |
| rt1 · RT1 | vacuous | neither override path tested; `factory-review` required by Interfaces has no test | an Interfaces line without a named test is decoration |
| rt2c · RT2 | vacuous | the cross-check runs on the committed table whose one tie is symmetric | a fixture that discriminates, not the production table |
| rt5 · RT5 | missing-case | quoted and continued spellings allowed; the one env test asserts allow | enumerate quoting and continuation; never let a rule's only test be an allow |
| rt5 · RT5b | underspecified | nesting ≥ 995 raises, exit 1, empty stdout = allow | an error contract: exit and stdout on every internal failure |
| sb1 · SB3 | underspecified | the job id is `head -n1` of merged stdout+stderr; Python block-buffers | say how the id is returned and give it a format regex |
| sb4 · SB2 | vacuous | the CA requirement can be deleted; 95 tests stay green | a deletion mutant per contract item |
| sb5 · SB2b | missing-case | a dotted-quad shape check lets an out-of-range octet through | validate as an IPv4 address, not a shape |
| sc1 · G1 | vacuous | seven contract behaviours mutated, three died; tests verbatim from the plan | each precedence rule needs a fixture that is both landed and reviewed |
| sc1 · G2 | process + vacuous | the subject not byte-identical; the indent anchor relaxed with no test noticing | byte-exact subjects; an anchor mutant |
| sc1 · G5 | underspecified | the lint guard reads `repos.toml`, not `--root`: zero plans in the sandbox, exit 0 | say which tree the checker reads; prove the red inside the sandbox |
| sc1 · G10 | vacuous | the plan's own named mutation M3 shipped with no test | a named mutant gets its test in the same section |
| sc4 · G8b | underspecified | four different blocks from one commit depending on cwd | the block derives from the tree under commit, git-only |
| sc5 · G11 | missing-case | a cross-repo dependency never satisfied; the global namespace undisclosed | define cross-repo satisfaction before shipping `repo:` |
| sc5 · G11b | missing-case | the resolved edge not consumed by the scheduler; the rejection's item dropped | carry every rejection item into the fix round's contract |
| sc8 · G12b | underspecified | imported keys leak into a flat satisfied set | say how the satisfied set is keyed: (repo, chain root) |

Added 2026-09-07 after the re-read of bk3 · B1b (ledger: `vacuous`, secondary
`implementer`; three adversarial readers converged), outside the seed count
above:

| run · key | class | the reviewer's finding (short) | the sentence the plan needed |
|---|---|---|---|
| bk3 · B1b | vacuous (+ implementer) | the "only the ledger survives" assertion is `elem` over a list the line above pins by `==`; deletable with every check green; never reads the lane layout | name the mutant, not the proof shape: a fourth lane child in modelLane's tmpfiles → `host-core` red naming it (B1c) |

(sc5 · G12 and oi1 · DA1 are counted implementer-primary with a plan
secondary of missing-case: a one-task conflicts fixture, and a fixture
instruction that should have been per column.)

## Appendix C — the dsh skill, in outline

```
~/flakes/dsh-harness/skills/planning/
  SKILL.md                     name: planning; description: write a typed
                               implementation plan from an approved spec under
                               docs/superpowers/specs for the dark factory; use
                               when given that spec path and an output path
                               under docs/reviews/plan-drafts
  references/inputs.md         §2 as a command list, in order, with the
                               "if missing" column
  references/rubric.md         §5.1 verbatim; the six-row floor
  references/anticipation.md   §4 as a checklist keyed by trigger
  references/section-checklist.md   Appendix A
  judge-prompt.md              the refute-first judge prompt, one lens per call
```

The skill's process is §3 Steps 0–7 with the packet handed in by
`factory-plan-brief` (the seat does not compute the packet itself; the
mechanical part and the scripted field part are the operator's tree, pasted
by a script the repo tests). Rules the skill states in its own words: one
output file; no typed heading outside it; no read of transcripts or logs;
every fact beside its command; `factory-brief <draft> <KEY>` is the one seat
tool it may run (read-only) and `factory-dispatch` only with `--dry-run`; the
plan is a draft until the panel says otherwise. `writing-plans` in the same
catalog is re-scoped by P8 to repositories without a typed graph, so the two
never claim the same trigger.

## Appendix D — `.claude/workflows/plan.js` (runnable draft)

The script is no longer inlined here. The text of record is `draftPrompt` in
`.claude/workflows/plan.js` (and `HOUSE`/`GRAMMAR` in
`.claude/workflows/batch-plan.js`); this appendix's verbatim copy was removed
2026-09-15 because it had drifted from both — missing the DF8d generated-body
clause (`### DF8d`, `docs/superpowers/plans/2026-09-11-defects.md`) and the
DF13/HM7c landing clause ("Landing is never a Step", `0c2893c`). The guard
test `tests/factory/plan.test.mjs` pins the clauses that matter; read the
source, not a copy of it.

---

## Revision — 2026-09-05 late, after two critiques

**Folded in (majors).** A fifth packet part, the *field* (§2.2 R5, §3 Step 0,
§6.1, Appendix D): the board's incidents since the last plan and the driver's
own contract, read in full, with R5 now refusing for any plan dispatched to a
seat. A5 split into a deterministic driver-guard task (P11: `FACTORY_PLAN`
required, a `docs/OPERATIONS.md` commit refused at integration, a near-miss
result block recorded) and the sentences as a dated interim; rubric row 7
scores a sentence-only plan at 2. A1's acceptance no longer reads
`dispatch.log` (it holds only the run/plan/groups line, and the rules forbid
opening it): telemetry `tasks` rows or the board line. A1's landing recipe
gains the two steps every landing needed tonight — reset the task branch to
the one named commit, merge main into it when the base moved. Two new rows:
A13 (a hook, or a second consumer of a derived block — the Stop-hook loop) and
A14 (a deny rule and the commands it will refuse — the guard refusing the
orchestrator's `rm`); the closing paragraph restates the six incidents under
rows whose trigger could have fired. A9 keys on the activity export's spend
since the last top-up (a proxy, gap declared) and the first wave's seat count;
the desk clause is gone; the top-up is an A3 item. A replan mode (§6.1,
Appendix D) with the guard's real rule stated (`missing_headings`: no heading
may disappear; a whole-file Write that keeps them is allowed) and a pre-write
heading check. The review counts reconciled to one measurement with its time
(132 files, 105 / 59 / 46 / 27; the T3 row cited). Appendix B reconciled: 43
rows = 42 plan-primary (14 / 14 / 8 / 6) + sc1 · G2 process-primary; §0, §1,
§7, Appendix A and P3 now derive from it, and P3's counts come from the ledger
with a fixture whose distribution differs. The M1 refusal gate now fires on a
required `checkEmpty` field the mechanical reader sets from `check`'s output
(P5 carries the red fixture). Rubric row 13's falsifier is the lint check's
own one-repo `--repos` form on a scratch copy (the `--root`-only form cannot
see the draft). `factory-brief` is named as the second read-only exception in
the rules (J1's lens needed it). `writing-plans` in the harness catalog is
re-scoped by P8 with a grep-gate acceptance. P5 lists `flake.nix` (the
`factory-unit` copy list has no glob) and its overlap with B1 and SB4.

**Folded in (minors).** A "measurable when" column in §4; `template-echo` as
`tasks.error_class`, the three incident classes as hand rows until `derive
incidents`; the colon result block as an A5 sentence and a P11 guard; the
threshold moves only by a commit citing a report line and is marked
unmeasured (owner P10) with the proportional mapping declared as a proxy; §9
cut to three questions (Q1 the judge as a data-path question naming the lane's
ZDR posture; the first plan; spend) with the threshold, the printed launch
line and the operator-model file decided in the text; the Kahn/barrier jargon
glossed; A2's delta labelled a prediction with the measured delta required on
the landed tree; A3's and §7's intervention count taken from the operator's
own messages, declared a proxy; P3 backfills into `docs/ledger/
plan-defects.toml` and leaves filed reviews byte-unchanged; `judges` in the
record are the judges that answered plus `judges_dropped`, a silent lens is
re-asked once and a short panel is `panel-short`, never a two-judge bar; the
mechanical reader runs all of M1–M13 (M3 to a file, M9, M13 added) with a
separate `since`; the concept file joins the Ship phase's write exception,
`effort` and `author` are documented args; P7 and P9 are plans, not tasks;
`mixed` replaced by `plan_defect_secondary`; the commit count dropped as
non-load-bearing; task ids corrected (P7 → P1 for `check --draft`; T10 →
T10a/T10b); P12 closes `js-formatter-linter-missing` so P5's `lint` covers its
JavaScript.

**Rejected or narrowed, with the reason.** (1) "Row 13 is unscoreable until P1
lands" — narrowed: the lint check already points `tasks.py` at a copy of the
tree through a one-repo `--repos` file (the "G5" block in `flake.nix`), so the
scratch check is runnable today; the critic's underlying finding (the
`--root`-only form is vacuous) is accepted and the command is now written
out. (2) "`subagent-driven-development` fires on the planning trigger" —
narrowed: its description fires on executing a plan, not on writing one; the
catalog collision is `writing-plans`, which P8 re-scopes; the five-round loop
that contradicts rule A1 is noted for the harness board and not changed here.
(3) "A plan for a product adds a driver-guard task" — narrowed: Step 2 forbids
a task without a spec item, so the guard is a task of this design (P11) and a
later plan names it in `dependsOn`; only a plan whose spec is the driver lands
such a guard itself. (4) "Rescore the three comparison plans on 14 rows" — not
done: a rescoring by the designer alone would be one judge of the author's own
model family, the bias the comparison declared; 34 is marked unmeasured with
the P10 report as owner instead. (5) The question on where the operator model
lives was not in the critic's keep-list and is decided in the text (three
questions is the cap); the operator can veto it by withdrawing P4.
