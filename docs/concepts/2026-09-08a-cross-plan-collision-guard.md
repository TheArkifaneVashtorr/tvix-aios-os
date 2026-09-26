# Concept 2026-09-08a — a driver guard against two in-flight seats sharing a file across plans

**Class:** driver/harness feature (a P11-class task with no spec item of its
own).

**Status:** proposed 2026-09-08, from the codex-driver-arm plan
(`docs/superpowers/plans/2026-09-08-codex-driver-arm.md`, D4 and "Not in this
plan"), drafted against the judge panel that scored it
(`docs/reviews/plan-judgements/2026-09-08-codex-arm.md`).

**Origin:** the codex-driver-arm plan's CA1 and CA3 both name SD2–SD4 (the
seat-driver plan's ladder tasks) as file-overlap conflicts on
`tools/factory/seat/factory-task` and `tools/factory/seat/factory-brief`, but
those conflicts sit *outside* `dependsOn` — SD2–SD4 are `out` of the codex
spec and held behind SD1, so the plan cannot make the codex arm wait on them
without waiting on a plan the spec explicitly excludes (D4). The fix the plan
adopts instead is a sentence: a launch pre-check reads
`tasks.py --root . brief | grep -F '**Running:**'` before wave 1 and holds if
SD2, SD3 or SD4 is running, and "whichever lands second merges main first" is
a rule for the human landing the wave, not a mechanism `factory-dispatch`
enforces. That sentence works today because one operator reads it before
every launch — but the driver itself has no notion of "two in-flight keys,
across different plans, whose `touches` overlap," so nothing stops a second
wave from being dispatched onto a colliding file while the first is still on
the seat.

**Idea:** teach `factory-dispatch` (or the `factory-wave` it launches) to read
the *currently running* keys across every plan in the graph — the same
`read_results`/`**Running:**` computation `tasks.py brief` already does — and
refuse to launch a group whose `touches` intersect a running key's `touches`,
with a stderr line naming the two keys and the shared path (the same shape
`conflicts` already prints for two draft-time tasks, but checked at dispatch
time against live seat state instead of only at plan-authoring time). This
turns D4's "the pre-check is a sentence a human runs" into a refusal the
dispatcher itself makes, closing the exact gap this plan's own §Dispatch
pre-check names as its residual: a human who forgets to run the grep, or runs
it and misreads an empty `**Running:**` block, currently has no second
backstop.

**Payoff:** removes one class of "two seats corrupted the same file" incident
before it can happen, without asking the plan author to encode inter-plan
`dependsOn` edges the spec forbids (D4's rejected alternative). Generalizes
beyond this plan: any pair of concurrently-dispatchable plans that touch a
shared file (SD2–SD4 vs. CA1/CA3 today; any future pair tomorrow) gets the
same protection for free, rather than each plan re-deriving its own
launch-pre-check sentence and trusting the operator to run it.

**Dependencies:** none landed; a natural home is `tools/factory/seat/factory-dispatch`
beside its existing graph query (`tasks.py … waves --repo … --next`), reusing
`read_results`'s glob-over-`.result` scan that already powers `**Running:**`;
needs no new ledger row and no spec of its own — it is infrastructure the
codex-driver-arm plan benefits from but does not require to land.

**Earliest landing:** after the seat-driver and seat-harness plans currently
in flight (SD1–SD10, SH4–SH6) land, since the guard's natural test fixture is
two real `dependsOn`-free plans with overlapping `touches` — exactly the
SD2–SD4 vs. CA1/CA3 pair this plan's §Waves section documents by hand today.
