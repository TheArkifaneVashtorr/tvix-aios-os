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

**Spend gate (operator lesson 2026-09-26: an OpenRouter plan sweep cost
about $450 for six plans).** The pilot is the probe: its credit delta is
read before anything else is dispatched. The full run proceeds only if
pilot cost × remaining runs fits the remaining credit with 20% margin;
otherwise the design is cut, in this order: one repetition, then drop F3,
then drop F2. The fallback is decided here, not mid-run. Runs are dispatched
one at a time, and the balance is read after each; the experiment stops when
the next run would cross the remaining credit.

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

## 6a. Revision 2 (2026-09-26): draft-only, sized for a test

Supersedes D1's fixture count, D2's phases, D3.2, D4's pilot and §4. Taken
as the orchestrator's recommendation; the operator stated no preference.

**Why.** Twelve plans are six A/B pairs. A two-sided sign test on six pairs
is significant only on a clean sweep (p ≈ 0.03); one tie or loss gives
p ≥ 0.2. Counting the 24 graded defects per arm as trials overstates the
sample, since defects within one plan are not independent. A paired test at
α = 0.05 with 80% power needs roughly 8 pairs for d = 1.2, 14 for d = 0.8 and
33 for d = 0.5. At the OpenRouter rate the operator measured (about $75 per
plan) even 14 full pairs cost about $2,100.

**The unit becomes the first draft.** The hypothesis is about how the drafter
gets its information. Judge, Revise and Ship are identical in both arms, so
they add cost and noise but no contrast. Both arms stop after Draft:
- **A:** `plan.js`'s Packet and Draft phases, byte-identical, then return
  the draft path.
- **B:** `plan-byref.js`'s Draft phase, byte-identical, then return.

Both are derived by truncation into two new workflow scripts, so `plan.js`
and `plan-byref.js` stay untouched. D3.2 (the panel) is dropped. The primary
outcome per pair is B's first-draft defect recall minus A's, from the
blind grader (D3.1, `hit / recorded`).

**Fixtures: more specs, one pair each.** Spec-to-spec variance dominates, so
N pairs are N distinct fixtures (D1's three plus candidates from the defect
record: plan-side defects ≥ 2, cutoff before 2026-09-25). A second
repetition is used only if the candidates run out, and is analysed as a
cluster.

Measured 2026-09-26 (a Sonnet search of `tasks.py outcomes` joined to the
plans; word counts re-measured at each cutoff). `plan.js`'s target reader
refuses a spec above 4,000 words, so the factory (6,250), seat-harness
(5,554) and platform (4,795) context blocks are out, and so is the
16,062-word planning-agent spec. That leaves:

| Key | Drafted from (at the cutoff) | Words | Plan-side defects | Cutoff commit |
|---|---|---|---|---|
| F1 | `specs/2026-09-06-operator-seat-driver-design.md` | 2,289 | 3 | `5972dcc1^` |
| F2 | charter `concepts/2026-09-09a-redesign-charter.md` → isolation | 2,352 | 3 | `1bad85a9^` |
| F3 | same charter → defects | 2,352 | 6 | `fc3d66db^` |
| F4 | `context/generation.md` | 3,678 | 10 | `889727a` |
| F5 | `context/helm.md` | 3,509 | 7 | `c815981` |
| F6 | `specs/2026-09-21-publish-gate-design.md` | 2,290 | 3 | `b07f025` |
| F7 | `specs/2026-09-08-openai-lab-spike-design.md` | 940 | 2 | `1dbd233` |

F6 was then **dropped** (2026-09-26): its archived tree fails `tasks.py check`
under an isolated `HOME` (KN17 "lands own work", and the W1 and H1
cross-area touches with no `areas:` line). That is a real historical graph
fault, and arm A refuses to draft on it (§5's drop rule). That leaves **6
primary pairs** (F1–F5, F7), below the 8 a test needs for d ≈ 1.2. An
extended set adds the four fixtures with one plan-side defect each (codex
driver arm, LoRA cards, operator-and-collection, spend telemetry), whose
per-plan recall is 0 or 1, so many of those pairs will tie. The extended set
is run only if the pilot's cost leaves room, and is reported separately. With
7 to 11 pairs, the likely outcome is a **pilot signal with an effect-size
estimate**, not significance. Saying so now is part of the pre-registration.

**Pilot.** One F1 pair, draft-only, in two cloud runs. It gives the cost per
draft. Then N_max = floor(0.8 × remaining credit / cost per pair), capped by
the fixture count, and fixed before pair 2.

**Analysis, fixed before the run.**
- Two-sided exact sign test on the N_max pair differences (ties dropped),
  α = 0.05, with a Wilcoxon signed-rank test and the median difference with
  its 95% CI reported beside it.
- **One interim look, futility only**, at pair 8: stop if B is ahead in ≤ 3
  of the untied pairs. A futility-only stop does not inflate the type I
  error.
- **Cost per draft** is the Workflow completion notification's usage line
  (`subagent_tokens`, `agent_count`, `duration_ms`) plus the credit delta per
  run. It is never the scripts' `outputTokensByPhase`, which counts output
  only, and whose phases differ between the arms.
- The report states the effect size the achieved N could detect. If N_max is
  below 8, the result is labelled a pilot signal, not a test.

Pass (B significantly better) → arm C gets a spec.

**Practical arm-C rule for the 2-pair pilot** (set 2026-09-27, while pair 2
on F4 was running and before its result existed; the budget caps the run at
F1 + F4). Grader noise on F1 was 1 disagreement in 6 verdicts, so on F4's 10
defects a gap of 1 is noise, 2 is borderline and 3 or more is real. With a
and b = arm A's and arm B's hits on F4:
- **b ≥ a − 1, and B's tokens ≤ 0.7 × A's** → write arm C's spec.
- **b = a − 2** → decided by attribution. For each defect A caught and B
  missed, check whether the catching fact is in A's packet files or in A's
  drafter's own command output. If it came from the packet: no arm C. If it
  came from the drafter's own lookups: arm C.
- **b ≤ a − 3** → no arm C.

A B loss does not refute JAZ, since arm B used no recursion, REPL or
in-memory history. It only removes the case for spending on arm C. Otherwise the record says
so and nothing changes.

## 6b. Revision 3 (2026-09-27): arm C, JAZ on this machine through the subscription

The pilot's rule fired (F1 + F4: arm B 9/13, arm A 4/13, B at 0.56× the
tokens; `docs/research-2026-09-27-jaz-pilot-F1-results.md`). The operator then
chose: this machine only, no cloud, no API billing, Claude through the
subscription, and a **full JAZ replication**: the real framework drafting our
fixtures, comparable to arms A and B. The automated subscription calls rest on
the revised rule `docs/decisions/2026-09-27-claude-subscription-for-operator-launched-work.md`.
Facts are from a measuring agent's notes (jaz v0.2.0a4 source, this repo's pin)
and the Claude Code headless docs.

**What stays stock.** `jaz-lang` v0.2.0a4, unmodified: the code-mode REPL,
`invoke` with tail calls, history as a REPL variable, and its hooks. The hooks
use the paper's long-horizon (StuLife) settings,
`ContextWindowWarning(warn_fraction=0.7, …)`, plus
`RecursionLimit(max_depth=2)` from the AppWorld config, so recursion is allowed
but bounded. `BudgetPool` counts **calls** (`calls_budget`), because a
subscription has no authoritative per-call cost; the ceiling is fixed from the
smoke run.

**What is ours, and is the whole deviation.**
1. **The backend.** A `BaseLLM` subclass (`complete(model, messages) →
   LLMResponse`) passed straight to `Config(llm=…)`, so LiteLLM is installed
   (a hard dependency) but never called. Each JAZ agent maps to one
   Claude Code session:
   - The first call opens it with `--system-prompt` set to JAZ's own system
     text, which replaces Claude Code's.
   - Later calls `--resume` it and send only the new turn, so JAZ's history is
     the session's native history and prompt caching carries over.
   - If JAZ ever rewrites earlier turns rather than appending, the backend
     opens a fresh session with the transcript and records that it did.
2. **The gateway.** A small host-side process that alone holds `claude`. It
   runs `claude -p --output-format json` in an empty directory with tools off
   and no MCP servers. `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` and
   `apiKeyHelper` are unset. Auto-compaction is off, so JAZ's 70% warning, not
   Claude Code, manages context. The model is `claude-fable-5-1`, the drafter
   of arms A and B. `--bare` is out, because it never reads the subscription
   login. The gateway serves one Unix socket, logs every call (tokens, cache
   reads, the client-side cost estimate, the usage-limit signal), and stops
   the run on that signal.
3. **The tools.** JAZ's REPL fails closed: no imports and no file paths by
   default. The drafter's access to the snapshot is therefore explicit
   callables bound as REPL variables: `read_file`, `grep`, `tasks_py`,
   `duckdb_query` over the evidence snapshot, and `git_log`. Each is confined
   to the fixture checkout, and every call is logged as arm B's
   `queries.log` was.
4. **The task.** `invoke` receives arm B's drafting instructions
   (`draft-byref.js`'s `draftPrompt` text, output format unchanged), the spec
   path and the tools. It returns the draft, which is written to
   `draft-0.md`.

**Isolation.** The runner (JAZ, the backend and the tools) runs in a basket:
the fixture checkout read-only, a scratch directory writable, no network, and
the gateway's socket bind-mounted as its only way out. The login and `claude`
never enter the basket. The operator mounts and launches; the build is
build-only. It adds a package, an app and a devShell output, and **no**
`checks.x86_64-linux` entry (the public flake's eval heap, per the goal-1
session). Every new file gets its `publish.toml` and `subsystems.toml` rows.

**Probe result (2026-09-27, `claude` 2.1.280, run on the operator's go).**
Two Fable calls, one fresh and one resumed, from an empty directory with
the API variables unset, using `--tools "" --strict-mcp-config
--setting-sources "" --system-prompt …`. The startup report showed
`apiKeySource: "none"` (the subscription), `tools: []`, `mcp_servers: []`,
and no hook events. Resume carried the history across (turn 2 recalled turn
1's word). Every call emits a `rate_limit_event` with the 5-hour and 7-day
window utilisation (0.07 and 0.65 at the probe). **That utilisation, logged
before and after each call, is arm C's spend measure,** and the gateway stops
the run when the 7-day window reaches 0.90. Compaction is disabled per call
with `--settings '{"autoCompactEnabled": false}'`. The resumed turn read no
cache at about 600 tokens; the smoke run checks caching at realistic sizes.

**Confinement.** The runner uses the bubblewrap placement this repo already
uses (`lib/mkAgent.nix`, `pkgs/dsh-openrouter`): no network, the fixture
read-only, scratch writable, and the gateway socket bound in. It is launched
by the operator.

**Order.**
1. **Probe (operator, host, no basket).** One gateway call and one two-turn
   resume. These pin the headless flags (tools off, compaction off, system
   prompt replaced) and the shape of the usage-limit signal.
2. **Smoke.** JAZ with the gateway on a toy task, to check that hooks fire,
   recursion is bounded and the trajectory is recorded.
3. **Arm C on F1, then F4,** one at a time, graded by the same blind
   grader against arms A and B's existing drafts. Then F2, F3, F5 and F7
   (and, for those, arms A and B locally through the same gateway if the
   operator wants the pairs).

**What arm C answers.** Given the same inputs and drafter model, does the
real JAZ mechanism (the REPL, recursion and by-reference history) catch
more recorded defects than arm B's plain self-directed lookup, and at what
subscription usage? Arm C against arm B isolates JAZ's machinery. Arm C
against arm A repeats the pilot's question.

**Known departures from the paper**, stated rather than hidden:
- the model (Fable, not GPT-5.4 nano);
- the transport (headless Claude Code sessions, not an API client);
- the task (planning, not StuLife or AppWorld);
- the budget unit (calls, not dollars).

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
