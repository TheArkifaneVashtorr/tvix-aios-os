# The planning step, redesigned around the one thing that predicts (2026-09-21)

**Status:** design, approved in session by the operator 2026-09-21. Two plans
follow, one per subsystem: Evidence, then Factory.

**Research:** `docs/research-2026-09-17-planning-redesign-packet.md`. Read its
provenance note before citing it — sections 2 through 9 never passed the
independent verifier the house standard requires, and §4's headline figure is
marked superseded. Every number this spec relies on was re-measured on
2026-09-21 and is marked as such below.

## 1. The number

**First-try landing rate.** Today `47/116 = 41%` against a stated target of
70%, down from 48% (`evidence report plans --repo ~/nixos-agent-env`, run
2026-09-21).

Chosen over the three alternatives because it is the only one with a
demonstrated lever, and because the others are partly downstream of it. Plan-
caused share is a ratio that improves if seats get worse. Rework rounds move
more on one pathological task than on ten clean ones. Survivors-outside-the-
named-set measures reviewer thoroughness as much as plan quality.

Every future change to the planning step argues against this number.

## 2. What the measurements say, re-run today

**The 14-row rubric does not predict first-try landing.** Re-measured over the
current 17 scored plans (15 usable; `2026-09-11-evidence` and
`2026-09-11-knowledge` carry zero tasks and so no rate):

```
PEARSON r (total score vs first-try rate) = +0.249   t=+0.93, df=13
plans scoring >= 38 (n=8):  30/78 = 38%
plans scoring <  38 (n=7):  17/38 = 45%
```

Not significant — `t` would need ≈2.16 at 13 df. And at the granularity the
dispatch decision actually uses, the sign inverts: higher-scoring plans landed
*less*. The honest reading is "no signal", not "anti-predictive", but the gate
is certainly not earning a three-judge panel.

Two caveats, stated rather than buried. The score barely varies — range 29–41,
mean 37.2, with **eight of fifteen plans scoring exactly 38**; a near-constant
output cannot correlate with anything, which is a fact about the rubric as much
as about the sample. And n=15 is thin.

**`touches` does predict it.** 77% first-gate approval at ≤2 touches, 53% at
≥5, p = 0.001 (packet §6.2). Size label, brief length, kind and acceptance
count move it not at all. The middle — 3 and 4 — is not reported separately and
remains unmeasured.

**Line-numbered citations rot fast.** 16% stale after one day, 61% after two,
69% after three, against 561 commits and 539 files changed in seven days
(packet §5.2–5.3). `wrong-fact` is 19% of the rejection record (§3.2).

**The packet's central blocker is gone.** It states repeatedly that
`evidence report plans` reads `n=0, refused`, so no threshold or row rule can
fire. It now reads `n=17` (measured 2026-09-21). Its question 8 — "should the
judgement files be ingested?" — is answered by events, and question 5's
blocker with it.

## 3. What changes

Four changes. The planning step otherwise keeps its structure: subsystem plans
stay the unit, the three-judge panel stays, the packet and the
spec → plan → dispatch flow stay, typed task sections stay.

### 3.1 `total` stops gating dispatch

The panel's number is still computed, still recorded, still ingested. It stops
deciding. `decision` reports whether a **blocker** was found, rather than
whether `total` crossed 34.

"Blocker" is the existing review vocabulary, not a new term: reviews already
report blockers, majors and minors, and today's gates say so in those words
("no blockers, no majors" — the five LoRA gates, 2026-09-21). **A blocker
refuses dispatch; a major or a minor does not.** Majors are what fix rounds
exist for, and a plan held back for a major would simply be re-judged into the
same state. If the panel reports no severity at all, that is a `revise` — a
review that cannot say what it found has not reviewed.

The panel survives losing its gate because it catches what nothing else does.
On 2026-09-21 it disproved a mutant in a promoted plan: GN38's **M8** named
`test_lora_strength_within_range` as the discriminating control for a change to
the `lora` normalization line, but that test never calls `load_rules`, so the
mutant could not fail it. A seat caught it; a grammar check never would. That
is a semantic defect, and semantic defects are what the panel is for.

### 3.2 `touches` becomes the dispatch gate

A task section with **more than 3 touches** must carry a one-line reason naming
why the diff cannot be split. `check` refuses without it. Three or fewer passes
silently.

A soft cap rather than a hard one because a hard cap refuses legitimate work: on
2026-09-21 GN44 (4 touches) and GN45 (6) both landed first try, and a feed UI
change touching `feed.py`, `app.js`, `app.css` and its tests is irreducible.
The justification is the forcing function — most wide tasks have no good reason,
and get split once someone must write one down.

Three rather than 2 because 2 would have refused both of those, and rather than
4 because 4 sits in the unmeasured middle and would be chosen by feel. Three is
also in the unmeasured middle; it is chosen as the tightest bound that does not
refuse a task the record shows landing. **This is the spec's weakest number and
the plan should say so.**

### 3.3 Citations stop carrying line numbers

A plan cites a file plus a quoted string, checkable by grep, instead of
`file:line`. The rot is in the line number, not the fact: `file:42` dies when
anything above line 42 moves, while the claim it carries is still true.

This is the `rules-validate` pattern applied to plans — that check already
verifies a rule's text byte-for-byte against its cited source rather than
trusting the citation, and it works.

Both halves land or neither: the Factory half tells a planner how to cite, the
Evidence half refuses `file:NNN` in a plan. A convention that lives only in a
prompt is a convention that rots — `media/CLAUDE.md` spent four days telling
every seat to update a board that was not the board.

### 3.4 A task's acceptance must name the checks that exercise what it changes

Neither the panel nor the touches cap catches a task whose **acceptance list
omits the check that would have failed**. Both of the day's defects are this
shape, and both are in plans the orchestrator typed:

**GN43** changed what a systemd target starts — it added `comfy-run-<w>` to
`comfy-world-<w>.target`'s `wants` — and its acceptance was
`comfy-worlds-eval, comfy-worlds-unit, media-lint, lint`. None of those starts
a target. `comfy-worlds-vm` is the only check that does, it was not in the
list, and so the seat never ran it and the gate never saw it. It failed on the
full gate after landing: the supervisor starts the author model, the model's
`Conflicts=` stops the generator the target had just started, and in a VM with
no weights the model never becomes ready, so the generator never comes back —
`curl 127.0.0.1:8188/system_stats` timed out at 600 s. The plan had described
that exact sequence and called it "self-correcting churn". It is not.

**GN38** named `test_lora_strength_within_range` as the discriminating control
for mutant M8, a change to the `lora` normalization line. That test never calls
`load_rules`, so the mutant could not fail it. The seat disproved it and
substituted a byte-exact probe.

Neither would be caught by a score, by `touches` (GN43 touched two files), or
by any grammar check. The task named a verification that does not verify the
change.

**The rule.** For each file a task touches, the checks whose derivations depend
on that file are the *candidate* acceptance set. A task must either name each
candidate in `acceptance`, or name it with a one-line reason for excluding it.
`check` refuses a task that silently omits one.

This is deliberately the same shape as 3.2 — mechanical, derived from the plan
text plus the flake, refusable, with a justification as the escape hatch. It is
not a judgement call a panel makes; it is a relation the tree already knows.

**The honest limit, which the plan must solve before this is typed.** The naive
candidate set is too large: `lint` depends on nearly everything and every VM
test depends on a whole system closure, so "all dependent checks" would demand
a dozen entries per task and be ignored within a week. The plan must find the
narrow form — most likely the *module-and-package* layer only: a task touching
`media/nixosModules/comfyui-worlds.nix` owes the checks that instantiate that
module (`comfy-worlds-eval`, `comfy-worlds-vm`), not every check that
transitively reads the flake. **If that narrowing cannot be made mechanical,
this change does not ship** — a rule that fires a dozen false demands is worse
than the gap it closes.

### 3.5 The judgement front matter does not change

`scores`, `total`, `threshold` stay exactly as they are. The stream stays valid,
`evidence-unit` stays green, and the series keeps accumulating so the rubric
question can be revisited at n=30 or n=50 with evidence rather than reopened
from memory. Only what `decision` *means* changes.

This matters more than it looks: that ingest was repaired on 2026-09-21 (the
corpus re-pinned at 35 files / 34 rows), and changing the 14-field allowlist
days later would break the one series that could ever show the rubric working.

## 4. Where it lands

| change | file | subsystem |
|---|---|---|
| score stops gating | `.claude/workflows/plan.js` (`THRESHOLD`, the decision it writes) | Factory |
| touches cap | `pkgs/evidence/tasks.py` (the section parser's refusals) | Evidence |
| citation form, authoring half | the packet composer and the planner's checklist | Factory |
| citation form, enforcing half | `pkgs/evidence/tasks.py` | Evidence |
| the number | nothing — `evidence report plans` already prints it | — |

Measured 2026-09-21: `THRESHOLD` is a single constant in `plan.js` and
`judgements.py` only validates that `threshold` and `total` are integers — it
never enforces the comparison. The gate decision is made in one place, so 3.1
is a contained diff and the schema genuinely does not move.

`touches` is already a first-class parsed field in `tasks.py` and already drives
task classification, so 3.2 is a new refusal in the check that today refuses a
malformed probe.

## 5. Sequencing

**Evidence first, Factory second.** The touches cap is the only change that
moves the number; dropping a gate that does not predict while adding one that
does should land as one observable step.

The citation change goes last and spans both plans.

## 6. Red before green

| change | the red |
|---|---|
| touches cap | a fixture plan with a 4-touch task and no reason → `check` refuses; the same with a reason → passes |
| score stops gating | a judgement with `total` 30 and no blocking defect → `decision: dispatch`; today it says `revise` |
| citation form | a plan containing `foo.nix:42` → refused; `foo.nix` plus a quoted string → passes |

Each is a refusal shown failing while the old behaviour still stands.

## 7. Risks, named

**A leaky gate replaces a useless one.** Dropping the score means nothing blocks
a plan except a reported blocking defect, and the panel finds those
inconsistently — survivors outside the named set are nonzero in 197 of 230
gates, median 3 (packet §3.4). The mitigation is that the touches cap does real
work and the number says within weeks whether it does.

**The cap may refuse legitimate work.** Mitigated by the soft form; measured by
how often the justification line is written rather than the task split. If it is
written every time, the cap is theatre and should be removed.

**The measurement window is long.** At roughly 8 tasks per plan, moving 41% with
any confidence needs perhaps 50 tasks — five or six plans, which is weeks. The
plans must say so, or a two-plan wobble will be read as signal.

**n=15 with eight ties.** §2's correlation is measured twice, both times
pointing the same way, but it is thin. The spec does not delete the score for
this reason; it demotes it and keeps collecting.

## 8. Out of scope

The model questions — drafting model and effort, a `plan` routing row, tandem
substrate, a second judge family, local inference on the 5090 (packet axes E, F,
G, I and question 7).

Deferred deliberately, not forgotten: running a twelve-plan model comparison
while the process itself changes confounds the result by construction. Ship the
structural change, measure first-try landing against 41%, then compare models on
a stable process. Fable `max` vs `high` is already not significant at p = 0.21,
so the model is not the demonstrated problem.

Also out: `gate_tokens` and `wall_s`, null on all 521 gate rows, which makes the
cost of rejection unmeasurable. Owed before the model comparison, not before
this.
