# Decision — telemetry store questions and two pauses (operator, 2026-09-05 late)

**Context.** The telemetry store design draft
(`docs/superpowers/specs/2026-09-05-telemetry-store-design.md`, committed
1473a22) closed with seven questions for the operator. Two paused items and
one Helm Home question were put beside them in the same status report. The
operator answered at ~23:50 CDT.

## Answers

1. **Store mode** — APPROVED at ~23:58 after the plain-words gloss below:
   operator-only (`0700`). The operator: "store mode actually makes sense.
   Approved."
2. **Usage-only extraction from this project's own Claude Code sessions** —
   APPROVED. Numbers only (token counts, timestamps, tool names, durations);
   message bodies are never read; the store's policy check applies to what is
   written.
3. **Automatic seat relaunch** — APPROVED for exactly three failure classes:
   a credit outage (once credits are recorded as restored), a provider error
   (once), a boot failure (once). Every other class waits for the orchestrator.
4. **The OpenRouter activity export** — APPROVED: keep the weekly manual
   download; no per-request egress pattern is added.
5. **Backups** — APPROVED as recommended: the run tree (`~/factory/runs`)
   stays unbacked and the derived rows are its durable copy; of the lanes
   only `/var/lib/lanes/*/ledger.jsonl` joins the restic paths (payloads,
   results and CAs never); the broker audit logs
   (`/var/lib/egress-broker/*/audit.jsonl`) do not leave the machine, not even
   as ciphertext — the derived daily rows are the durable numbers.
6. **The two pauses** — APPROVED to lift: B1 (backup paths, XS) relaunches
   now; the media worlds fix rounds W3b/W5b resume the next session.
7. **Discord's isolation grade** — decided beyond the recommendation: **total
   environment isolation, a basket** (the strongest grade this project has),
   not a lane. The operator's words: "Discord needs total environment
   isolation. It's basically malware that is useful." Helm Home's Discord card
   therefore runs a basket, and the basket's own egress rules are the only
   network it gets.

## What "store mode" means (for question 1)

The store is a directory, `/var/lib/evidence`. Its *mode* is the Unix
permission setting on that directory: who may read it. Today it is
`0750 root:users` — the owner may read and write, and every account in the
`users` group may read. The recommendation, `0700`, makes it readable by the
owner alone. Nothing the operator uses changes: the evidence tools, the Helm
collector, the seat and the hooks all run as the operator's own account, which
is the owner. What changes is that no other account on the machine — a future
service user, a container's user, a guest — can read the store's numbers.

## Consequences

- The telemetry plan (when written) carries answers 2–5 as fixed constraints
  and treats 1 as decided the day the operator says the word.
- Seat driver: the relaunch table of answer 3 is the contract for the
  proposed task T15.
- B1 dispatched as run `bk2`; the media board notes the resumption.
- The Helm Home plan (the first plan through the planning agent) declares
  Discord as a basket-hosted app; its card's Run verb starts the basket's
  unit.
