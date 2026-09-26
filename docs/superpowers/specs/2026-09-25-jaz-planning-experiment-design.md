# JAZ-style planning: a three-fixture experiment on the cloud credit — design

**Status:** draft, 2026-09-25, measured at HEAD `5f7de6b2`. Not yet judged.
Operator request the same day: test the "Harness as a Language" claim against
this workflow, with the $250 Claude Code cloud credit; arms chosen "both,
cloud first". Sources: `docs/research-2026-09-25-jazz-harness-preprint-web.md`
(the preprint, arXiv:2609.26891, verified) and a measuring agent's notes at
HEAD `5f7de6b2`.

## 1. Purpose

JAZ's thesis: fixed harness structure does not buy capability; a model that
queries raw state by code and delegates recursively, with history passed by
reference, does at least as well for less. Its evidence is GPT-5.4 nano on
StuLife and AppWorld [research §3]; nothing transfers to Claude or to
planning by default.

This workflow's measurable weak point is planning: about 65% of rejections
are plan-side defects. The question this experiment answers, and only this
one: **does a planner that queries raw sources on demand avoid more of the
defects that actually happened than `plan.js`'s fixed reader packet, at equal
or lower token spend?**

## 2. What exists (measured)

- `plan.js` already passes by reference at the Packet→Draft seam: five
  Sonnet readers each write a packet file (`plan.js:157-231`), and the Fable
  drafter receives their **paths** and reads them in full (`plan.js:238`,
  `:332`). There is no packet-writer hop in `plan.js`; the Opus synthesis
  hop belongs to `gather.js` (`gather.js:56-58`). The remaining difference
  from JAZ is **who decides what to look at**: five fixed reader dimensions,
  written as prose before drafting, against the drafter querying the tree
  and the store itself, as it drafts.
- The evidence tooling a cloud VM needs is stdlib-only: `tasks.py`,
  `streams.py`, `evidence.py` (`tasks.py:33-50`); the store path is
  overridable (`EVIDENCE_STORE`). A committed JSONL snapshot replaces
  `/var/lib/evidence`.
- Claude Code has no persistent REPL and no shared in-memory history;
  by-reference means file paths and transcript paths. Nesting is capped
  (3 layers by default, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`), and cloud
  sessions set their own compaction threshold [research §6].
- JAZ reaches Claude only through LiteLLM with an API key [research
  "LLM backends"]; whether API calls from a cloud VM draw on the credit is
  unknown.
- **Planning spend has never been measured.** `plan.js` dollars and tokens
  are `UNMEASURED` (`docs/research-2026-09-11-batch-draft-vs-planjs.md:33`);
  `ledger/openrouter-usage` covers only the broker lane.
- The credit (secondary sources only): claim by 2026-10-07, expires
  2026-11-04, cloud sessions only, needs a connected GitHub account.

## 3. Decisions

### D1 — Three fixtures with known downstream defects

| Key | Spec | Plan landed | Recorded plan-side defects |
|---|---|---|---|
| F1 | `2026-09-06-operator-seat-driver-design.md` (M) | `5972dcc1` | SD1 wrong-fact, SD3 missing-case, SD4 missing-case |
| F2 | charter `docs/concepts/2026-09-09a-redesign-charter.md` §6 inc. 4 → `2026-09-11-isolation.md` | `1bad85a9` | IS12 vacuous, IS16 missing-case, IS21 underspecified |
| F3 | the same charter → `2026-09-11-defects.md` | `fc3d66db` | DF7/10/12 missing-case, DF11 wrong-fact, DF14/15 vacuous |

F2 and F3 were batch-plan outputs (`plan.js` was not their drafter), so for
them arm A's re-run is the only `plan.js` baseline; F1 alone has a
historical `plan.js` plan to compare the re-run against.

Each fixture's tree is the **parent of the plan-landing commit**, so no
review naming a defect is in the tree the planner sees. The defect review
files are the answer key and never leave the host.

### D2 — Arms

- **A (control, cloud):** `plan.js` unchanged, re-run on each fixture in a
  cloud session. Re-running rather than reusing the 09-06/09-11 plans holds
  the model, Claude Code version and environment equal to arm B.
- **B (by-reference, cloud):** a new script `.claude/workflows/plan-byref.js`
  — `plan.js` with the Packet phase removed. The drafter gets the spec path,
  the tree, the store snapshot, and the tool recipes (`tasks.py`, duckdb over
  the JSONL, grep); it queries as it drafts and may spawn sub-agents, handing
  them paths, never summaries. Judge, Revise and Ship phases are `plan.js`'s,
  unchanged. `plan.js` itself is not edited.
- **C (JAZ proper, host, conditional):** `pip install jaz` (Apache-2.0) in
  a basket behind the broker, Claude via LiteLLM, paid from API billing; the
  `invoke` body drafts the plan from the same inputs. Specified only as far
  as this paragraph; it gets its own spec **only if** arm B passes the §4
  rule.

### D3 — Scoring, blind

1. **Defect recall (primary):** an Opus grader on the host gets one plan
   (arm label stripped) and the fixture's defect reviews, and marks each
   recorded defect *avoided*, *covered* (the plan names the case or fact
   correctly) or *repeated*. Score = (avoided + covered) / recorded.
2. **Panel total /42:** `plan.js` `judgeOnly` on each output, arm label
   stripped.
3. **Spend:** subagent tokens per phase from each Workflow run's usage line
   and `journal.jsonl`; the credit balance before and after each session,
   read by the operator. This is the first measured planning spend.

### D4 — A pilot before the run

One cloud session, F1, arm A only. It answers what no source does: whether
the Workflow tool runs in a cloud session, whether `tasks.py` and duckdb run
from the snapshot, and what one `plan.js` run costs in credit. The full run
is sized from the pilot's number; if the Workflow tool is not available in
cloud, the experiment stops and this spec is revised.

### D5 — Where the fixtures live

Cloud sessions clone from GitHub. The public export cannot serve: it
withholds the plans, ledger and reviews the planner reads. The fixtures go
to a **private** experiment repository: three orphan branches (no history,
no commit messages), each a `git archive` of its D1 tree, with the
2026-09-09 captured session-token files (`docs/bugs/2026-09-09-drive-seat-url-token.md`
and two `docs/reviews/2026-09-09-opus-review-*.md`) deleted, a JSONL store
snapshot cut at the same date, and the export secret scan re-run on each
branch before any push. The push is the operator's.

## 4. Acceptance

- Pilot: one arm-A plan for F1 exists, its token and credit cost recorded.
- Full run: 3 fixtures × 2 arms × 2 repetitions = 12 plans, each scored on
  D3's three measures, in one results table under `docs/`.
- **Decision rule, fixed before the run:** arm B passes if its mean defect
  recall is higher than arm A's on at least 2 of 3 fixtures, its panel mean
  is not lower by more than 2, and its median tokens are not higher. Pass →
  arm C gets a spec. Fail → the record says so and nothing changes.

## 5. Risks

- **n is small.** Twelve plans detect a large effect, not a small one; the
  table reports per-run values, not only means.
- **The grader knows the answer key.** It is blind to the arm, not to the
  defects; that is the point, but a lenient grader inflates both arms alike.
- **Model drift.** The original plans were Fable-drafted in early September;
  arm A's re-run is the control, the historical plans are not.
- **Cloud unknowns** (compaction threshold, wall-clock limit, credit
  metering) are measured by the pilot, not assumed.
- **Today's `plan.js` already learned from these defects.** Its rules cite
  `2026-09-11-defects.md` and lessons from 09-15 (Opus review of
  `plan-byref.js`, 2026-09-25), and both arms carry them. That is fair
  between A and B but shrinks the measurable gap; a null result is weaker
  evidence than a positive one.
- **Arm A refuses to draft on an unsound graph** (`tasks.py check` non-zero);
  arm B has no such gate. Each fixture's `check` exit is recorded before any
  run, and a fixture that fails it is dropped for both arms.
- **F2 and F3 carry their batch judgements** (`plan-judgements/2026-09-12`
  and `-14-batch-{isolation,defects}.md`), which critique the very tasks
  that later failed. The original authors revised against them, so they
  stay; arm B browses freely and may find them more readily than arm A's
  readers. Whether each plan's Facts cite them is recorded from
  `queries.log` and the packet files. Other landed plans in those trees
  also name graded keys in passing (F2: `2026-09-11-knowledge.md:105`,
  `2026-09-11-platform.md:105,109`; F3: `2026-09-11-factory.md:116`); same
  treatment.
- **Blinding:** drafts are copied to opaque ids with author, status, path and
  arm words stripped (`tools/experiments/jaz/blind.sh`) before grading or
  judging; the drafter prompt never names the experiment.

## 6. Phasing

1. Build (agents, host, build-only): `plan-byref.js`, the fixture branches
   in a local scratch repo, the grader prompt.
2. Operator: create the private repo, push, claim the credit.
3. Pilot (D4). Operator reads the credit delta.
4. Full run, scoring on the host, results table, decision (§4).

## 7. Not in this design

Changing `plan.js`; arm C's implementation; the parent-respawn loop the
original summary described (it is in neither the paper nor the code
[research "Conflicts"]); any public artifact.

## 8. Not measured

Credit metering at list price; whether subagents inside a cloud session
spend the credit at the same rate as the main loop; a variance estimate for
`plan.js` itself (the pilot's second repetition is the first).

## 9. Operator questions — answered 2026-09-25

1. **Private experiment repo for the fixtures (D5)?** Moot: the operator
   had already created a private repository.
2. **Two repetitions per cell?** Approved: two, if the pilot's cost allows
   12 runs inside $250; otherwise one repetition and F3 dropped.
3. **Grader on the host (Opus, plan usage) rather than cloud?** Approved:
   host — the answer key never leaves the machine.
