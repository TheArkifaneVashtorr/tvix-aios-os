# Concept 2026-09-02j — backup parity self-test

**Class:** nightly self-check unit atop Lane F. **Status:** proposed
(factory-originated, during Lane F Task 4).

**Origin (factory, 2026-09-02):** writing `tests/acceptance/backup.sh` as an
operator-run drill made the gap obvious — between operator runs, nothing on
the machine notices if the push silently stops working (keyring locked,
Proton account issue, a stale lock file) until someone remembers to run the
acceptance script by hand. "If you cannot measure it, it isn't real" (the
brief's own standing habit) argues for turning the four things the
acceptance drill checks into a number that gets emitted every night, not
just when someone asks.

**Idea:** a nightly `systemd --user` oneshot (`backup-self-test`, timed just
after `proton-drive-push`) that emits exactly one structured journal line
and nothing else:

- `basket doctor` verdict (pass/fail + which probe if it fails)
- age of the latest restic snapshot in the local repository (hours since
  `snapshots --latest`)
- remote parity: local snapshot count vs. `proton-drive filesystem list
  /my-files/backups/core/snapshots` count
- `nix flake check` result, cached from the last factory run rather than
  re-run nightly (it's minutes of build, not a fit for a nightly timer) —
  or, cheaper, whether `/run/current-system` matches the flake's last
  evaluated `core` derivation

That one line becomes a Helm dashboard tile: green when every field is
within bounds (snapshot age < ~26h, parity holds, doctor clean, config not
drifted), red the moment any one of them isn't — an at-a-glance answer to
"is the backup actually working right now" that doesn't require running the
acceptance script.

**Payoff:** closes the loop the acceptance drill opened but can't keep
closed by itself — a human-run PASS on gate day says nothing about day 40.
A single always-on green/red line is cheap to build (it's the acceptance
script's own checks, minus the interactive restore drill, minus sudo) and
turns "did the backup keep working" from an assumption into a measurement.

**Dependencies:** this plan (Lane F: the restic local repo, the push unit,
and the parity check logic the self-test reuses), Helm (the dashboard
surface the tile renders on — not yet built).

**Earliest landing:** after the Lane F operator gate passes (the self-test
needs a real push history to have anything meaningful to report) and after
Helm exists to host the tile; until then the acceptance script is the only
check, run by hand.
