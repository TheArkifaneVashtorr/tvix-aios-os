# Concept 2026-09-07b — a reused mechanism with no producer is a forward reference

**Class:** planning rule (a sharpening for plan review, in the spirit of
`docs/concepts/2026-09-07a-a-named-proof-shape-is-not-a-mutant.md`).
**Status:** proposed 2026-09-07, from the seat-harness-redesign plan's judge
panel (errata #4 and #8, `docs/reviews/plan-judgements/2026-09-07-seat-harness.md`).

**Origin (the seat-harness-redesign panel, 2026-09-07):** SH4's Interfaces
bullet declares `factory_verify_checks <ws> <rev> <budget-s> <name>…` — a
budget already in seconds — and then closes the same sentence with "the
caller passes the budget file SH5 reuses." No task in the plan creates that
file, names its path or format, or reads it back; SH5's own
`factory_run_probe <ws> <env-tokens> <remaining-s> <command>` also just takes
seconds, with nothing calling it "the file." All three judges read past the
phrase as an implementation detail on a first pass; the opus judge caught it
only when checking whether SH5's fixtures actually exercised the shared
budget (they didn't — errata #4) and traced the sentence back to find there
was nothing to reuse. The plan's own six tasks, each individually
self-contained and citation-backed, made the missing eleventh task load
enough to nod past.

**Idea:** a plan sentence that describes one task's output only by naming
what a *later* task will do with it ("the caller passes X", "Y reuses Z") is
a forward reference — and a forward reference across independently-dispatched
tasks is not a fact, it is an invented interface, because the first seat has
nothing to write and the second has nothing to read. This differs from a
same-task callback (fine: both halves are in the seat's own diff) and from a
genuinely shared *value* computed once and exported (fine: `verify_deadline`
computed before the block and read by name). The tell is grammatical: the
sentence names a noun ("the budget file", "the cache", "the queue") that no
Interfaces bullet in the plan ever introduces with its own path, schema, or
producer. A judge should flag any such noun the same way an undefined
variable is flagged in code review — not by re-deriving what it must mean,
but by asking "which task's Files or Interfaces section creates this."

**Payoff:** catches a class of gap that survives per-task self-containment
checks precisely because each task reads fine alone; only a cross-task grep
for "reuses", "the same X", "shares" or "the caller passes" surfaces it. Adds
one mechanical check to the judge's toolkit: for every such phrase, find the
task and line that defines the referenced noun, or flag it as unsatisfiable.

**Dependencies:** none landed; a natural home is the planning-agent spec's
judge rubric (`docs/superpowers/specs/2026-09-05-planning-agent-design.md`,
beside rubric row 6 "Interfaces and error contracts") or the judge prompt's
per-criterion checklist, next time either is revised.

**Earliest landing:** next planning-agent spec or judge-prompt revision;
until then, judges apply it by hand (as this panel did) when a plan's
Interfaces section names a mechanism as "reused" or "shared" across tasks.
