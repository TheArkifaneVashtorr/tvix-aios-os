# Seat driving authority and data-sharing stance (2026-09-09)

Decided by the operator on 2026-09-09, in-session, directly to the driving
seat. Recorded here so a reset does not lose it; the board keeps the day-to-day
queue.

## Decision 1 — the seat drives the factory

The operator delegated full driving authority to the seat: brief, dispatch,
gate and integrate the ready queue on the seat's own judgment, and prep each
switch (build, closure diff, acceptance lines). The operator alone executes
the physical switch to live and signs off acceptance ("test passed").

Boundaries that still hold: build-only (never `sudo`/`nixos-rebuild`/unit
start-stop); model and effort resolution stay with the driver scripts (never
`--model` by hand); rung 3 re-plans, pauses, spend decisions and routing-table
row changes remain the operator's.

## Decision 2 — data sharing is case-by-case, never to enemies

The standing invariant ("privacy outranks everything; nothing leaves the
machine") stands by default. Sharing corpus or token data with a research
partner (e.g. Hermes) is a case-by-case decision: each share needs the
operator's explicit per-case approval, and every proposal is screened first
against "would this help an adversary." Egress happens only through the
declared, classified lane/basket machinery.

## Context

Asked and answered 2026-09-09 after the session-23 handoff. Autonomy:
"drive everything; I only switch" (the recommended option). Sharing: answered
custom — "case by case, we are no looking to give data to enemies."