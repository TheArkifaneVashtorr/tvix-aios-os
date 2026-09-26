# Phase 2 acceptance — what you run

One command from the repo root (it will ask for sudo once):

    nix develop -c tests/acceptance/phase2.sh

It builds a temporary isolated network bubble, starts the traffic chokepoint
for it, and proves from inside the bubble that: the one allowed website works,
everything else is refused, a disguised request (allowed name outside, banned
name inside) is caught, there is no way around the chokepoint, and every
attempt landed in the audit log with the right verdict. Everything is torn
down when it exits — nothing persists.

Expected final line: `PHASE 2 ACCEPTANCE: PASS`.
