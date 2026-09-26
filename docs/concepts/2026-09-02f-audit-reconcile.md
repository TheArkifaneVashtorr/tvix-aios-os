# Concept 2026-09-02f — audit reconciliation (`basket reconcile`)

**Class:** CLI tool + doctrine. **Status:** proposed (lands with Phase 6, useful from Phase 5).

**Origin data (today):** Phase 2 acceptance ended with the operator eyeballing
three audit lines. That works at three lines; it stops working the day two more
log sources exist — and brief §7 Phase 6's acceptance already demands it: "the
append-only event log reconciles with the broker log."

**Idea:** treat "the log is complete" as a measurable claim, not an assumption.
`basket reconcile --broker <audit.jsonl> --agent <source>` cross-matches
per-request records between independent observers (broker audit vs dsh event log
vs router request log) within a time window and reports three sets: matched,
broker-only (agent under-reporting — instrumentation gap), agent-only
(**requests that never crossed the broker — a bypass**, the alarm case). Exit
nonzero on any agent-only record. Phase 5's test ("local-only prompt never in
outbound traffic, verified from the broker log") gets stronger too: reconcile
router log against broker log so absence-of-evidence becomes
evidence-of-absence.

**Test:** fabricate the three logs with a known overlap + one planted bypass
record; reconcile must find exactly it.

**Earliest landing:** Phase 6 (dsh event log is the second source); consider a
thin router-vs-broker version in Phase 5.
