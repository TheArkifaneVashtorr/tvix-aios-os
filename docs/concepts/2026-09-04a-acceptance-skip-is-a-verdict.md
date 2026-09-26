# Concept 2026-09-04a — acceptance SKIP is a verdict, not a shrug

**Class:** testing process / operator gates.
**Status:** landed (`tests/acceptance/helm-v1.sh`, the D6 re-scope of the
Helm v1 gate).

**Origin (2026-09-04, Helm v1 Task 6):** the v1 acceptance drill was
specified against a machine that does not exist yet. The original plan
wanted a `media` switch round trip and a cowork broker audit — but the
`media` specialisation is round 2's wiring, and cowork has been parked off
on `core` by decision since 2026-09-02. Written naively, the gate faces two
bad choices: **FAIL** the steps (a gate that reports a healthy system as
broken every run until unrelated wiring lands — noise that trains the
operator to ignore red), or quietly **omit** them (a gate that silently
covers less than it claims, the vacuous-test failure mode the board already
rejects). The consolidated plan resolved it as decision D6: a third
outcome, logged and counted, "SKIP — precondition absent".

**Idea:** a conditional acceptance step must announce, as a first-class
verdict, *exactly which precondition was absent* — never fail on it, never
pass it silently, never edit it out of the script. Concretely, in
`helm-v1.sh`: the media round trip probes its own precondition
(`media` in the live config's `control.profiles` **and** the
`specialisation/media` activation binary present under the system profile
root) and prints `SKIP: media round trip: specialisation.media is not
wired yet (round 2)`; the cowork audit prints its SKIP naming the
replacement (the agent-prefix sweep + `restic-backups-core-local`, the
armed agent unit of the same class). SKIPs appear in the result line
(`N passed, N failed, N skipped`) and never affect the exit code. The
probe must test the *live* system, not the repo — the gate judges what is
running, so the precondition check reads `/etc/helm/config.json` and
`/nix/var/nix/profiles/system`, not `hosts/core/helm.nix`.

**Why it is a verdict and not a TODO marker:** a SKIP carries information
a reviewer can act on — it is the difference between "the system lacks
this" and "the drill can't tell". The falsifiable form: when round 2 wires
`specialisation.media`, the *same, unedited* script must flip that step
from SKIP to executed (and to PASS/FAIL on its own merits); if it stays
SKIP after the wiring lands, that is itself a finding against the probe.
That is what makes the SKIP honest — it is pinned to a named, checkable
precondition, not to a date or a mood.

**Payoff:** operator gates survive across wiring rounds without edits or
re-approval, and the result line stays a truthful coverage statement:
`12 passed, 0 failed, 2 skipped` says exactly what was and was not
exercised on this machine today. The alternative — a gate rewritten per
round — silently re-baselines itself every time, which is how acceptance
scripts rot into ceremony.

**Dependencies:** consolidated plan D6 (`media` conditional, `cowork`→
`restic` replacement, SKIP≠FAIL); the general test-based-reality rule that
an unmeasured claim is dated debt, not a non-fact (SKIP is the
measurement; silence would be the debt).

**Earliest landing:** landed 2026-09-04 with the Helm v1 acceptance drill;
worth applying to any future gate whose subject arrives in instalments
(the media rework's own drill, and any phase 10 web-portal gate gated on
hardware that may not be plugged in).
