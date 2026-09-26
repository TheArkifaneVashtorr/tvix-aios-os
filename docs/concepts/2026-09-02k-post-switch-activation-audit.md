# Concept 2026-09-02k — post-switch activation audit

**Class:** acceptance check + Helm tile atop Lane F. **Status:** proposed
(orchestrator-originated, from a field observation).

**Origin (2026-09-02 20:07):** after the operator's switch onto the merged
build, `proton-drive-push.timer` showed `enabled` but `inactive (dead)`,
`Trigger: n/a`. A NixOS switch installs user units and reloads the user
manager, but it does not *start* a newly enabled user timer inside a desktop
session that was already logged in — that only happens at the next login.
The 19:54 push ran anyway, because the system restic job kicks the push unit
directly; the 00:30 fallback would not have fired. The acceptance drill
passed 7/7 without noticing: it checks that the push *ran*, not that the
timer is *armed*. The orchestrator started the timer by hand and added a
runbook step.

**Idea:** a declared-vs-live audit that runs after every switch and nightly:

- for every timer the flake declares (system and user), assert
  `ActiveState=active` and a non-empty `NextElapseUSecRealtime`;
- for every service with `wantedBy` that should be running, assert
  `active`;
- emit one journal line (`activation-audit: OK timers=N services=M` or the
  list of offenders) and, once Helm exists, a red/green tile.

The list of "declared" units comes from the flake itself (eval-time: the
module's `systemd.timers` / `systemd.user.timers` attribute names), so the
check can never drift from the config.

**Payoff:** closes the class of bug where a unit is correctly declared,
correctly installed, and never runs — invisible to `nix flake check`
(evaluation only) and to a drill that checks outcomes once. It is the
"enabled ≠ armed" cousin of concept 2026-09-02j (which checks that the
backup *kept* working).

**Dependencies:** Lane F (the first units it audits); Helm (the tile).

**Earliest landing:** as a factory task on the backup lane (extend
`tests/acceptance/backup.sh` with a "timer armed" check and add the nightly
audit unit), then as a Helm tile on Helm's first plan.
