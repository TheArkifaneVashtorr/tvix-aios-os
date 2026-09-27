=== M1 cmd ===
date: 2026-09-27T02:14:44Z
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check > check.out 2> check.err ; echo exit=$?
exit=0
--- check.out ---
--- check.err ---

=== M2 ===
time: 2026-09-27T02:14:47Z
$ nix develop -c python3 pkgs/evidence/tasks.py --root . brief
# Task brief (generated 2026-09-27T02:14:47Z)

| repo | landed | approved | rejected | ran | running | recorded | ready | blocked | deferred-to-brief | withdrawn | parked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 0 | 199 | 16 | 0 | 0 | 0 | 31 | 42 | 0 | 7 | 0 | 0 | 0 |
| media | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gaming | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| nixos-skill | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dsh-harness | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 |
| codex | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| openai-lab | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 |

**Next wave** — nixos-agent-env: EV1(nix-module) EV10(docs-runbook) EV11(python-evidence) EV12(python-evidence) EV14(python-evidence) EV16(nix-check) EV17(python-evidence) EV5(python-evidence) FA10(docs-runbook) FA11(bash-driver) FA13(bash-driver) FA14(bash-driver) FA3(bash-driver) FIX5(bash-driver) FIX5b(bash-driver) FIX5c(bash-driver) FIX5d(bash-driver) FIX6(nix-module) FIX7(bash-driver) HH2(python-evidence) HH3(nix-module) IS2(docs-runbook) IS4(nix-module) N13(python-evidence) N14(bash-driver) N15(nix-check) N16(python-evidence) N17(bash-driver) N18(js-workflow) PL1(docs-runbook) UI1(bash-driver) · gaming: PB0(any) · dsh-harness: H1(any) H2b(any) (plan 2026-09-05-harness-router.md) · codex: CX2b(any) · openai-lab: OL1(any)
**Record (7 d):** 0 rej, 0 plan (vac 0, miss 0, under 0, fact 0)
**Seats (7 d):** none
**Running:** none
**Rejected, fix round owed:** nixos-agent-env/CR2 (CR2rb by cr17) · nixos-agent-env/CR2r2 (CR2r2b by cr19) · nixos-agent-env/P1flash (P1flash by mcf2) · nixos-agent-env/OG1 (OG1r by og3) · nixos-agent-env/P3A (P3Arb by pb3arb2) · nixos-agent-env/P3Ar2 (P3Ar2b by pb3ar2b)
**Escalated:** none
**Withdrawn/parked:** nixos-agent-env/PW1pro · nixos-agent-env/PW1glm · nixos-agent-env/PW1kimi · nixos-agent-env/SB5 · nixos-agent-env/SB6 · nixos-agent-env/BUG1 · nixos-agent-env/BUG1b
**Operator owns:** none
**Untracked plans (no typed headings, no plan-status row):** none

=== M3 ===
time: 2026-09-27T02:14:52Z
$ nix develop -c python3 pkgs/evidence/tasks.py --root . json > graph.json
exit=0
bytes: 2000706

=== M4 ===
time: 2026-09-27T02:14:55Z
$ nix develop -c python3 pkgs/evidence/tasks.py --root . waves --repo nixos-agent-env --json
[[["EV1", "EV10", "EV16", "EV5", "FA11", "FA13", "FA14", "FA3", "FIX5", "FIX5b", "FIX5c", "FIX5d", "FIX6", "FIX7", "HH2", "HH3", "IS4", "N13", "N14", "N15", "N17", "N18", "PL1", "UI1"], ["EV11", "EV12"], ["EV14"], ["EV17"], ["FA10"], ["IS2"], ["N16"]], [["EV13", "EV15"], ["FA12"], ["FA15"], ["FA18"], ["PL2"]], [["FA16"], ["PL3"]], [["FA17"], ["FA23", "PL4"], ["PL7"]], [["PL5"]], [["PL6"]]]

=== M5 ===
time: 2026-09-27T02:14:59Z
$ nix develop -c python3 pkgs/evidence/tasks.py --root . conflicts
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: N13 (2026-09-04-loose-ends-wave-a7.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: FA2 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: IS4 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): pkgs/broker ~ pkgs/broker/policy.py
nixos-agent-env: IS4 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): tests/broker/test_policy.py ~ tests/broker/test_policy.py
nixos-agent-env: IS4 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: IS4 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: IS5 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): pkgs/broker/policy.py ~ pkgs/broker/policy.py
nixos-agent-env: IS5 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): tests/broker/test_policy.py ~ tests/broker/test_policy.py
nixos-agent-env: IS5 (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: IS5b (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): pkgs/broker/policy.py ~ pkgs/broker/policy.py
nixos-agent-env: IS5b (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): tests/broker/test_policy.py ~ tests/broker/test_policy.py
nixos-agent-env: IS5b (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: IS5b (2026-09-09-program.md) × N13 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × N13 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: N13 (2026-09-04-loose-ends-wave-a7.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: N13 (2026-09-04-loose-ends-wave-a7.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: N13 (2026-09-04-loose-ends-wave-a7.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: N13 (2026-09-04-loose-ends-wave-a7.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FA2 (2026-09-09-program.md) × N14 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: FA11 (2026-09-09-program.md) × N14 (2026-09-04-loose-ends-wave-a7.md): pkgs/dsh-openrouter/dsh-openrouter.sh ~ pkgs/dsh-openrouter/dsh-openrouter.sh
nixos-agent-env: FA11 (2026-09-09-program.md) × N14 (2026-09-04-loose-ends-wave-a7.md): tests/unit ~ tests/unit/70-dsh-openrouter.bats
nixos-agent-env: IS4 (2026-09-09-program.md) × N14 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: IS5 (2026-09-09-program.md) × N14 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: IS5b (2026-09-09-program.md) × N14 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: N15 (2026-09-04-loose-ends-wave-a7.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: IS4 (2026-09-09-program.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: IS5b (2026-09-09-program.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × N15 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: N15 (2026-09-04-loose-ends-wave-a7.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: N15 (2026-09-04-loose-ends-wave-a7.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: N15 (2026-09-04-loose-ends-wave-a7.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: N15 (2026-09-04-loose-ends-wave-a7.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × UI1 (2026-09-09-bugs.md): tools/factory/seat/ ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × UI1 (2026-09-09-bugs.md): tools/factory/seat/ ~ tools/factory/seat/factory-task
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × UI1 (2026-09-09-bugs.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FIX5 (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-review ~ tools/factory/seat/
nixos-agent-env: FIX5 (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FIX5b (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-review ~ tools/factory/seat/
nixos-agent-env: FIX5b (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FIX5d (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-review ~ tools/factory/seat/
nixos-agent-env: FIX5d (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FIX7 (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-review ~ tools/factory/seat/
nixos-agent-env: FIX7 (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FIX5c (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-review ~ tools/factory/seat/
nixos-agent-env: FIX5c (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: FA1 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/
nixos-agent-env: FA1 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-task ~ tools/factory/seat/
nixos-agent-env: FA1 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/README.md ~ tools/factory/seat/
nixos-agent-env: EV6 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: FA2 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/
nixos-agent-env: FA2 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: FA11 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tests/unit ~ tests/unit/80-seat-driver.bats
nixos-agent-env: IS4 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: IS4 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: FA3 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-review ~ tools/factory/seat/
nixos-agent-env: FA3 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: IS5 (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: IS5b (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: IS5b (2026-09-09-program.md) × N17 (2026-09-04-loose-ends-wave-a7.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: FA12 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/
nixos-agent-env: FA12 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-task ~ tools/factory/seat/
nixos-agent-env: FA12 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-wave ~ tools/factory/seat/
nixos-agent-env: FA12 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-artifact.py ~ tools/factory/seat/
nixos-agent-env: FA13 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-registry.py ~ tools/factory/seat/
nixos-agent-env: FA14 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-graph.py ~ tools/factory/seat/
nixos-agent-env: FA14 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-artifact.py ~ tools/factory/seat/
nixos-agent-env: FA15 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-run.py ~ tools/factory/seat/
nixos-agent-env: FA15 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/README.md ~ tools/factory/seat/
nixos-agent-env: FA16 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-run.py ~ tools/factory/seat/
nixos-agent-env: FA16 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-task ~ tools/factory/seat/
nixos-agent-env: FA16 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/
nixos-agent-env: FA16 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/README.md ~ tools/factory/seat/
nixos-agent-env: FA17 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-run.py ~ tools/factory/seat/
nixos-agent-env: FA17 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-review ~ tools/factory/seat/
nixos-agent-env: FA18 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-reresolve.py ~ tools/factory/seat/
nixos-agent-env: FA19 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/README.md ~ tools/factory/seat/
nixos-agent-env: FA20 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-batch.py ~ tools/factory/seat/
nixos-agent-env: FA21 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-batch.py ~ tools/factory/seat/
nixos-agent-env: FA21 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/factory-artifact.py ~ tools/factory/seat/
nixos-agent-env: FA21 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/README.md ~ tools/factory/seat/
nixos-agent-env: FA23 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): flake.nix ~ flake.nix
nixos-agent-env: FA24 (2026-09-11-factory.md) × N17 (2026-09-04-loose-ends-wave-a7.md): tools/factory/seat/README.md ~ tools/factory/seat/
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FA1 (2026-09-09-program.md) × N18 (2026-09-04-loose-ends-wave-a7.md): tests/factory/render.test.mjs ~ tests/factory/render.test.mjs
nixos-agent-env: FA2 (2026-09-09-program.md) × N18 (2026-09-04-loose-ends-wave-a7.md): tests/factory/render.test.mjs ~ tests/factory/render.test.mjs
nixos-agent-env: FA11 (2026-09-09-program.md) × N18 (2026-09-04-loose-ends-wave-a7.md): tests/unit ~ tests/unit/70-dsh-openrouter.bats
nixos-agent-env: FA23 (2026-09-11-factory.md) × N18 (2026-09-04-loose-ends-wave-a7.md): tools/factory/dark-factory.js ~ tools/factory/dark-factory.js
nixos-agent-env: FA23 (2026-09-11-factory.md) × N18 (2026-09-04-loose-ends-wave-a7.md): tests/factory/render.test.mjs ~ tests/factory/render.test.mjs
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × SP5 (2026-09-08-spend-telemetry.md): docs/ledger/claims.toml ~ docs/ledger/claims.toml
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × HH2 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × HH2 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × HH2 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × IS4 (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × IS5b (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × HH2 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × HH2 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH2 (2026-09-08-helm-home-1.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × HH3 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × HH3 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × HH3 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × IS4 (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × IS5b (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × HH3 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × HH3 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH3 (2026-09-08-helm-home-1.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × HH6 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × HH6 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × HH6 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × IS4 (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × IS5b (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × HH6 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × HH6 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH6 (2026-09-08-helm-home-1.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × HH8 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × HH8 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × HH8 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × IS4 (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × IS5b (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × HH8 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × HH8 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH8 (2026-09-08-helm-home-1.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × HH9 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × HH9 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × HH9 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × IS4 (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × IS5b (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × HH9 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × HH9 (2026-09-08-helm-home-1.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: HH9 (2026-09-08-helm-home-1.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV2 (2026-09-09-program.md) × SP4 (2026-09-08-spend-telemetry.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV2 (2026-09-09-program.md) × SP4 (2026-09-08-spend-telemetry.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV3 (2026-09-09-program.md) × SP4 (2026-09-08-spend-telemetry.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV3 (2026-09-09-program.md) × SP4 (2026-09-08-spend-telemetry.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV4 (2026-09-09-program.md) × SP4 (2026-09-08-spend-telemetry.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV4 (2026-09-09-program.md) × SP4 (2026-09-08-spend-telemetry.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV11 (2026-09-11-evidence.md) × SP4 (2026-09-08-spend-telemetry.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV11 (2026-09-11-evidence.md) × SP4 (2026-09-08-spend-telemetry.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV12 (2026-09-11-evidence.md) × SP4 (2026-09-08-spend-telemetry.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV12 (2026-09-11-evidence.md) × SP4 (2026-09-08-spend-telemetry.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV18 (2026-09-11-evidence.md) × SP4 (2026-09-08-spend-telemetry.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV18 (2026-09-11-evidence.md) × SP4 (2026-09-08-spend-telemetry.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): docs/runbooks/evidence.md ~ docs/runbooks/evidence.md
nixos-agent-env: EV1 (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: EV2 (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): docs/runbooks/evidence.md ~ docs/runbooks/evidence.md
nixos-agent-env: EV3 (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): docs/runbooks/evidence.md ~ docs/runbooks/evidence.md
nixos-agent-env: EV4 (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): docs/runbooks/evidence.md ~ docs/runbooks/evidence.md
nixos-agent-env: EV6 (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): docs/runbooks/evidence.md ~ docs/runbooks/evidence.md
nixos-agent-env: EV6 (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: FA11 (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): tests/unit ~ tests/unit/96-evidence-runbook.bats
nixos-agent-env: IS4 (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: IS5b (2026-09-09-program.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: PL2 (2026-09-11-platform.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: PL3 (2026-09-11-platform.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: PL4 (2026-09-11-platform.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: PL5 (2026-09-11-platform.md) × SP5 (2026-09-08-spend-telemetry.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × UI1 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA1 (2026-09-09-program.md) × UI1 (2026-09-09-bugs.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: FA1 (2026-09-09-program.md) × UI1 (2026-09-09-bugs.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: EV6 (2026-09-09-program.md) × UI1 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA2 (2026-09-09-program.md) × UI1 (2026-09-09-bugs.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: FA11 (2026-09-09-program.md) × UI1 (2026-09-09-bugs.md): tests/unit ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FA3 (2026-09-09-program.md) × UI1 (2026-09-09-bugs.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: EV13 (2026-09-11-evidence.md) × UI1 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV15 (2026-09-11-evidence.md) × UI1 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × UI1 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA12 (2026-09-11-factory.md) × UI1 (2026-09-09-bugs.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: FA12 (2026-09-11-factory.md) × UI1 (2026-09-09-bugs.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: FA16 (2026-09-11-factory.md) × UI1 (2026-09-09-bugs.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: FA16 (2026-09-11-factory.md) × UI1 (2026-09-09-bugs.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: FA23 (2026-09-11-factory.md) × UI1 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × FIX5 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV6 (2026-09-09-program.md) × FIX5 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA11 (2026-09-09-program.md) × FIX5 (2026-09-09-bugs.md): tests/unit ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX5 (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX5 (2026-09-09-bugs.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: EV13 (2026-09-11-evidence.md) × FIX5 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV15 (2026-09-11-evidence.md) × FIX5 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × FIX5 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA17 (2026-09-11-factory.md) × FIX5 (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA23 (2026-09-11-factory.md) × FIX5 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × FIX5b (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV6 (2026-09-09-program.md) × FIX5b (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA11 (2026-09-09-program.md) × FIX5b (2026-09-09-bugs.md): tests/unit ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX5b (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX5b (2026-09-09-bugs.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: EV13 (2026-09-11-evidence.md) × FIX5b (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV15 (2026-09-11-evidence.md) × FIX5b (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × FIX5b (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA17 (2026-09-11-factory.md) × FIX5b (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA23 (2026-09-11-factory.md) × FIX5b (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × FIX5d (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV6 (2026-09-09-program.md) × FIX5d (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA11 (2026-09-09-program.md) × FIX5d (2026-09-09-bugs.md): tests/unit ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX5d (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX5d (2026-09-09-bugs.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: EV13 (2026-09-11-evidence.md) × FIX5d (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV15 (2026-09-11-evidence.md) × FIX5d (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × FIX5d (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA17 (2026-09-11-factory.md) × FIX5d (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA23 (2026-09-11-factory.md) × FIX5d (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × FIX7 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV6 (2026-09-09-program.md) × FIX7 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA11 (2026-09-09-program.md) × FIX7 (2026-09-09-bugs.md): tests/unit ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX7 (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX7 (2026-09-09-bugs.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: EV13 (2026-09-11-evidence.md) × FIX7 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV15 (2026-09-11-evidence.md) × FIX7 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × FIX7 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA17 (2026-09-11-factory.md) × FIX7 (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA23 (2026-09-11-factory.md) × FIX7 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × FIX5c (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV6 (2026-09-09-program.md) × FIX5c (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA11 (2026-09-09-program.md) × FIX5c (2026-09-09-bugs.md): tests/unit ~ tests/unit/80-seat-driver.bats
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX5c (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA3 (2026-09-09-program.md) × FIX5c (2026-09-09-bugs.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: EV13 (2026-09-11-evidence.md) × FIX5c (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV15 (2026-09-11-evidence.md) × FIX5c (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × FIX5c (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA17 (2026-09-11-factory.md) × FIX5c (2026-09-09-bugs.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: FA23 (2026-09-11-factory.md) × FIX5c (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × FIX6 (2026-09-09-bugs.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × FIX6 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV6 (2026-09-09-program.md) × FIX6 (2026-09-09-bugs.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × FIX6 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × IS4 (2026-09-09-program.md): nixosModules/seatLane.nix ~ nixosModules/seatLane.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × IS4 (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × IS5 (2026-09-09-program.md): nixosModules/seatLane.nix ~ nixosModules/seatLane.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × IS5b (2026-09-09-program.md): nixosModules/seatLane.nix ~ nixosModules/seatLane.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × IS5b (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: EV13 (2026-09-11-evidence.md) × FIX6 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV15 (2026-09-11-evidence.md) × FIX6 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × FIX6 (2026-09-09-bugs.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × FIX6 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FA23 (2026-09-11-factory.md) × FIX6 (2026-09-09-bugs.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × FIX6 (2026-09-09-bugs.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FIX6 (2026-09-09-bugs.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × EV13 (2026-09-11-evidence.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × EV15 (2026-09-11-evidence.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × EV16 (2026-09-11-evidence.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × EV16 (2026-09-11-evidence.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × FA23 (2026-09-11-factory.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × FA23 (2026-09-11-factory.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV1 (2026-09-09-program.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × PL4 (2026-09-11-platform.md): hosts/core/default.nix ~ hosts/core/default.nix
nixos-agent-env: EV1 (2026-09-09-program.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV15 (2026-09-11-evidence.md) × EV5 (2026-09-09-program.md): pkgs/evidence/streams.py ~ pkgs/evidence/streams.py
nixos-agent-env: EV11 (2026-09-11-evidence.md) × EV2 (2026-09-09-program.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV11 (2026-09-11-evidence.md) × EV2 (2026-09-09-program.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV12 (2026-09-11-evidence.md) × EV2 (2026-09-09-program.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV12 (2026-09-11-evidence.md) × EV2 (2026-09-09-program.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV18 (2026-09-11-evidence.md) × EV2 (2026-09-09-program.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV18 (2026-09-11-evidence.md) × EV2 (2026-09-09-program.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: FA1 (2026-09-09-program.md) × FA12 (2026-09-11-factory.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: FA1 (2026-09-09-program.md) × FA12 (2026-09-11-factory.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: FA1 (2026-09-09-program.md) × FA15 (2026-09-11-factory.md): tools/factory/seat/README.md ~ tools/factory/seat/README.md
nixos-agent-env: FA1 (2026-09-09-program.md) × FA16 (2026-09-11-factory.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: FA1 (2026-09-09-program.md) × FA16 (2026-09-11-factory.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: FA1 (2026-09-09-program.md) × FA16 (2026-09-11-factory.md): tools/factory/seat/README.md ~ tools/factory/seat/README.md
nixos-agent-env: FA1 (2026-09-09-program.md) × FA19 (2026-09-11-factory.md): tools/factory/seat/README.md ~ tools/factory/seat/README.md
nixos-agent-env: FA1 (2026-09-09-program.md) × FA21 (2026-09-11-factory.md): tools/factory/seat/README.md ~ tools/factory/seat/README.md
nixos-agent-env: FA1 (2026-09-09-program.md) × FA23 (2026-09-11-factory.md): tests/factory/render.test.mjs ~ tests/factory/render.test.mjs
nixos-agent-env: FA1 (2026-09-09-program.md) × FA24 (2026-09-11-factory.md): tools/factory/seat/README.md ~ tools/factory/seat/README.md
nixos-agent-env: EV11 (2026-09-11-evidence.md) × EV3 (2026-09-09-program.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV11 (2026-09-11-evidence.md) × EV3 (2026-09-09-program.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV12 (2026-09-11-evidence.md) × EV3 (2026-09-09-program.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV12 (2026-09-11-evidence.md) × EV3 (2026-09-09-program.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV18 (2026-09-11-evidence.md) × EV3 (2026-09-09-program.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV18 (2026-09-11-evidence.md) × EV3 (2026-09-09-program.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV11 (2026-09-11-evidence.md) × EV4 (2026-09-09-program.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV11 (2026-09-11-evidence.md) × EV4 (2026-09-09-program.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV12 (2026-09-11-evidence.md) × EV4 (2026-09-09-program.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV12 (2026-09-11-evidence.md) × EV4 (2026-09-09-program.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV18 (2026-09-11-evidence.md) × EV4 (2026-09-09-program.md): docs/ledger/bugs.toml ~ docs/ledger/bugs.toml
nixos-agent-env: EV18 (2026-09-11-evidence.md) × EV4 (2026-09-09-program.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: EV18 (2026-09-11-evidence.md) × EV4 (2026-09-09-program.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: EV13 (2026-09-11-evidence.md) × EV6 (2026-09-09-program.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV15 (2026-09-11-evidence.md) × EV6 (2026-09-09-program.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × EV6 (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × EV6 (2026-09-09-program.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV6 (2026-09-09-program.md) × FA23 (2026-09-11-factory.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × FA23 (2026-09-11-factory.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV6 (2026-09-09-program.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV6 (2026-09-09-program.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FA12 (2026-09-11-factory.md) × FA2 (2026-09-09-program.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: FA16 (2026-09-11-factory.md) × FA2 (2026-09-09-program.md): tools/factory/seat/factory-lib.sh ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: FA2 (2026-09-09-program.md) × FA23 (2026-09-11-factory.md): tests/factory/render.test.mjs ~ tests/factory/render.test.mjs
nixos-agent-env: FA11 (2026-09-09-program.md) × FA12 (2026-09-11-factory.md): tests/unit ~ tests/unit/86-rung-and-escalate.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA12 (2026-09-11-factory.md): tests/unit ~ tests/unit/87-prior-attempt.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA13 (2026-09-11-factory.md): tests/unit ~ tests/unit/89-agent-registry.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA14 (2026-09-11-factory.md): tests/unit ~ tests/unit/88-graph-and-artifact.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA15 (2026-09-11-factory.md): tests/unit ~ tests/unit/90-graph-runner.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA16 (2026-09-11-factory.md): tests/unit ~ tests/unit/91-node-executors.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA17 (2026-09-11-factory.md): tests/unit ~ tests/unit/92-gate-and-refusal.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA18 (2026-09-11-factory.md): tests/unit ~ tests/unit/93-reresolver.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA19 (2026-09-11-factory.md): tests/unit ~ tests/unit/94-bug-graph.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA19 (2026-09-11-factory.md): tests/unit ~ tests/unit/fixtures/fa19-bug-row.json
nixos-agent-env: FA11 (2026-09-09-program.md) × FA20 (2026-09-11-factory.md): tests/unit ~ tests/unit/95-batch-tool.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA20 (2026-09-11-factory.md): tests/unit ~ tests/unit/fixtures/fa20-batch-server.py
nixos-agent-env: FA11 (2026-09-09-program.md) × FA21 (2026-09-11-factory.md): tests/unit ~ tests/unit/96-plan-graph.bats
nixos-agent-env: FA11 (2026-09-09-program.md) × FA24 (2026-09-11-factory.md): tests/unit ~ tests/unit/97-guard-factory-paths.bats
nixos-agent-env: EV16 (2026-09-11-evidence.md) × IS4 (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × IS4 (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: IS4 (2026-09-09-program.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: IS4 (2026-09-09-program.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: IS4 (2026-09-09-program.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: IS4 (2026-09-09-program.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FA17 (2026-09-11-factory.md) × FA3 (2026-09-09-program.md): tools/factory/seat/factory-review ~ tools/factory/seat/factory-review
nixos-agent-env: EV16 (2026-09-11-evidence.md) × IS5b (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × IS5b (2026-09-09-program.md): flake.nix ~ flake.nix
nixos-agent-env: IS5b (2026-09-09-program.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: IS5b (2026-09-09-program.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: IS5b (2026-09-09-program.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: IS5b (2026-09-09-program.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV10 (2026-09-11-evidence.md) × FA13 (2026-09-11-factory.md): docs/ledger/subsystems.toml ~ docs/ledger/subsystems.toml
nixos-agent-env: EV10 (2026-09-11-evidence.md) × PL1 (2026-09-11-platform.md): docs/ledger/subsystems.toml ~ docs/ledger/subsystems.toml
nixos-agent-env: EV10 (2026-09-11-evidence.md) × PL1 (2026-09-11-platform.md): docs/subsystems.md ~ docs/subsystems.md
nixos-agent-env: EV13 (2026-09-11-evidence.md) × FA23 (2026-09-11-factory.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV15 (2026-09-11-evidence.md) × FA23 (2026-09-11-factory.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × FA23 (2026-09-11-factory.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × FA23 (2026-09-11-factory.md): docs/MAP.md ~ docs/MAP.md
nixos-agent-env: EV16 (2026-09-11-evidence.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: EV16 (2026-09-11-evidence.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FA13 (2026-09-11-factory.md) × PL1 (2026-09-11-platform.md): docs/ledger/subsystems.toml ~ docs/ledger/subsystems.toml
nixos-agent-env: FA23 (2026-09-11-factory.md) × PL2 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × PL3 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × PL4 (2026-09-11-platform.md): flake.nix ~ flake.nix
nixos-agent-env: FA23 (2026-09-11-factory.md) × PL5 (2026-09-11-platform.md): flake.nix ~ flake.nix
dsh-harness: H1 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): README.md ~ README.md
dsh-harness: H1 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): CHANGELOG.md ~ CHANGELOG.md
dsh-harness: H1 (2026-09-05-harness-router.md) × SD11 (2026-09-06-seat-driver.md): README.md ~ README.md
dsh-harness: H1 (2026-09-05-harness-router.md) × SD11 (2026-09-06-seat-driver.md): CHANGELOG.md ~ CHANGELOG.md
dsh-harness: H2 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/using-superpowers/references/dsh-tools.md ~ skills/using-superpowers/references/dsh-tools.md
dsh-harness: H2 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/subagent-driven-development/SKILL.md ~ skills/subagent-driven-development/SKILL.md
dsh-harness: H2 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): AGENTS.md ~ AGENTS.md
dsh-harness: H2 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): README.md ~ README.md
dsh-harness: H2 (2026-09-05-harness-router.md) × SD11 (2026-09-06-seat-driver.md): AGENTS.md ~ AGENTS.md
dsh-harness: H2 (2026-09-05-harness-router.md) × SD11 (2026-09-06-seat-driver.md): README.md ~ README.md
dsh-harness: H2b (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/using-superpowers/references/dsh-tools.md ~ skills/using-superpowers/references/dsh-tools.md
dsh-harness: H2b (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/subagent-driven-development/SKILL.md ~ skills/subagent-driven-development/SKILL.md
dsh-harness: H2b (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): AGENTS.md ~ AGENTS.md
dsh-harness: H2b (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): README.md ~ README.md
dsh-harness: H2b (2026-09-05-harness-router.md) × SD11 (2026-09-06-seat-driver.md): AGENTS.md ~ AGENTS.md
dsh-harness: H2b (2026-09-05-harness-router.md) × SD11 (2026-09-06-seat-driver.md): README.md ~ README.md
dsh-harness: H2c (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/subagent-driven-development/SKILL.md ~ skills/subagent-driven-development/SKILL.md
dsh-harness: H2c (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): README.md ~ README.md
dsh-harness: H2c (2026-09-05-harness-router.md) × SD11 (2026-09-06-seat-driver.md): README.md ~ README.md
dsh-harness: P13 (2026-09-06-planning-agent.md) × SD11 (2026-09-06-seat-driver.md): AGENTS.md ~ AGENTS.md
dsh-harness: P13 (2026-09-06-planning-agent.md) × SD11 (2026-09-06-seat-driver.md): README.md ~ README.md
dsh-harness: P13 (2026-09-06-planning-agent.md) × SD11 (2026-09-06-seat-driver.md): CHANGELOG.md ~ CHANGELOG.md

=== M6 ===
time: 2026-09-27T02:15:02Z
$ evidence bundle --markdown
# Evidence bundle — 2026-09-27T02:15:02Z

**Live:** unknown generation at none. **HEAD:** c9c5bd7c0494 — WORKING TREE DIRTY.

## Checks covering HEAD and the live system

- addon: HEAD —; live —
- comfy-upstream-probe-unit: HEAD —; live —
- comfy-worlds-assertion-negative-hosts: HEAD —; live —
- comfy-worlds-assertion-negative-name: HEAD —; live —
- comfy-worlds-assertion-negative-password-path: HEAD —; live —
- comfy-worlds-assertion-negative-ports: HEAD —; live —
- comfy-worlds-eval: HEAD —; live —
- comfy-worlds-unit: HEAD —; live —
- comfyui-cliploader-krea2: HEAD —; live —
- comfyui-eval: HEAD —; live —
- comfyui-package: HEAD —; live —
- comfyui-startup-clean: HEAD —; live —
- comfyui-vm: HEAD —; live —
- config: HEAD —; live —
- config-precedence: HEAD —; live —
- config-rejects-typo: HEAD —; live —
- core-backup-wiring: HEAD —; live —
- core-gaming-wiring: HEAD —; live —
- custom: HEAD —; live —
- evidence-unit: HEAD —; live —
- factory-unit: HEAD —; live —
- flake-check: HEAD —; live —
- helm-control-eval: HEAD —; live —
- helm-control-vm: HEAD —; live —
- helm-declaration: HEAD —; live —
- helm-declaration-negative-block: HEAD —; live —
- helm-declaration-negative-field: HEAD —; live —
- helm-declaration-negative-profile: HEAD —; live —
- helm-declaration-negative-program: HEAD —; live —
- helm-declaration-negative-seat: HEAD —; live —
- helm-home-assertion-negative-duplicate: HEAD —; live —
- helm-home-assertion-negative-enable: HEAD —; live —
- helm-home-assertion-negative-path: HEAD —; live —
- helm-home-assertion-negative-profile: HEAD —; live —
- helm-home-assertion-negative-seats: HEAD —; live —
- helm-home-eval: HEAD —; live —
- helm-home-package: HEAD —; live —
- helm-home-reversible: HEAD —; live —
- helm-home-unit: HEAD —; live —
- helm-unit: HEAD —; live —
- helm-vm: HEAD —; live —
- host-core: HEAD —; live —
- integration: HEAD —; live —
- lab-vm: HEAD —; live —
- lane-unit: HEAD —; live —
- lane-vm: HEAD —; live —
- ledger-unit: HEAD —; live —
- lint: HEAD —; live —
- map: HEAD —; live —
- media-fetch-bats: HEAD —; live —
- media-fetch-unit: HEAD —; live —
- proton-backup-eval: HEAD —; live —
- seat-assertion-negative: HEAD —; live —
- seat-eval: HEAD —; live —
- seat-unit: HEAD —; live —
- seat-vm: HEAD —; live —
- subsystems-manifest: HEAD —; live —
- telemetry-eval: HEAD —; live —
- telemetry-vm: HEAD —; live —
- unit: HEAD —; live —
- usage-ingest-wiring: HEAD —; live —
- zzz: HEAD —; live —

## Repo heads


## Helm now

- backup-parity: ok since 2026-09-07T13:06:41Z
- backup-snapshot: ok since 2026-09-05T17:41:51Z
- basket-doctor: ok since 2026-09-05T17:41:51Z
- broker: ok since 2026-09-05T17:41:51Z
- drift: fail since 2026-09-11T01:54:44Z
- flake-check: fail since 2026-09-11T08:05:28Z
- gpu: ok since 2026-09-05T17:41:51Z
- host: ok since 2026-09-05T17:41:51Z
- timers: ok since 2026-09-05T17:41:51Z

## Join: 360 task rows, 243 with a gate verdict, 0 with activity


## Claims: 14 verified, 3 parked, 26 open gaps

- STALE aimdo-native-load-unmeasured (owner orchestrator, opened 2026-09-05, review by 2026-09-19): the media acceptance drill on core imports comfy_aimdo's native module and reports OK (ComfyUI worlds plan, W6), or the startup log at a GPU start names aimdo as loaded
- STALE backup-user-lane-group-unasserted (owner orchestrator, opened 2026-09-05, review by 2026-09-19): one host-core assertion that services.proton-backup.user is a member of the `lane` group (the group that owns the 2770 lane dirs the ledger lives in)
- STALE basket-verify-cannot-bind-payload (owner orchestrator, opened 2026-09-05, review by 2026-09-19): encrypt packs once (hash and ciphertext from the same bytes), or verify states that payload↔content binding needs the identity
- STALE declared-agents-zero (owner orchestrator, opened 2026-09-05, review by 2026-09-19): services.baskets.agents on core names the harnesses that actually run, or a decision records that A1–A4 have no live instance
- STALE drift-exact-measure (owner orchestrator, opened 2026-09-05, review by 2026-09-19): nix store diff-closures between the live system and the toplevel built at HEAD lists only the nixos-version file; the docs-only rule is the proxy (store paths cannot match: the toplevel bakes the commit id)
- STALE effort-policy-n1 (owner orchestrator, opened 2026-09-05, review by 2026-09-19): n ≥ 5 per arm off vs medium through the seat driver, Opus verdicts equal, tokens in the ledger
- evidence-flock-effect-unmeasured (owner orchestrator, opened 2026-09-05, review by 2026-10-03): a test that fails without the flock, or a note that Linux O_APPEND makes it belt-and-braces
- STALE factory-run-report-persisted (owner orchestrator, opened 2026-09-05, review by 2026-09-19): runs.jsonl holds one factory-run row per dark-factory run (E3)
- STALE fake-upstream-proves-what-seat-sends (owner orchestrator, opened 2026-09-05, review by 2026-09-19): one live probe per effort level against OpenRouter with the response's reasoning field recorded
- STALE forbidden-list-single-source (owner orchestrator, opened 2026-09-05, review by 2026-09-19): the local-only path list is generated from Nix and the three copies are proven identical (R9 first proves they agree)
- STALE ledger-attribution (owner orchestrator, opened 2026-09-05, review by 2026-09-19): factory-findings.jsonl rows carry task, round and label for a real run (E3+E4)
- STALE nixpkgs-host-pin-age (owner orchestrator, opened 2026-09-05, review by 2026-09-19): plan 2026-09-05-operator-items PB0 (gaming → nixos-26.05 a5cc6f2c37) then PB1 (nixpkgs-host → same rev; nix flake check -L incl. VM tests; toplevel; closure diff in docs/reviews/2026-09-05-release-upgrade-26.05.md); the operator switches; a release-age item on the board
- STALE seat-key-exception-undecided (owner orchestrator, opened 2026-09-05, review by 2026-09-19): SD5 landed (seat@ gets a writable cache root) → switch #22 → docs/runbooks/seat.md §(c) one web job and §(d) one headless job → /var/lib/egress-broker/seat/audit.jsonl shows an allow row for openrouter.ai → rm ~/.config/openrouter/key → this row becomes status = "verified", class = "operator", evidence = "operator:<date> …"
- uid1000-can-switch-profile (owner orchestrator, opened 2026-09-05, review by 2026-10-03): switch #24 activates AUTH_ADMIN_KEEP; then operator:<date> — systemctl start helm-switch@gaming.service from a GNOME terminal asked for the password and the 7700 page carried no form and no token — flips this row to verified, class operator; until then the seat guard's tripwire (R8) stands
- STALE driver-row-unmeasured (owner orchestrator, opened 2026-09-06, review by 2026-09-20): report ladder's orchestrate section at n ≥ 5 sessions per arm
- STALE ladder-implement-code-rung2-unmeasured (owner orchestrator, opened 2026-09-06, review by 2026-09-20): evidence report ladder prints the implement/code/any rung-2 line at n ≥ 5 with its first-gate fraction beside rung 1's
- STALE ladder-implement-docs-rung2-unmeasured (owner orchestrator, opened 2026-09-06, review by 2026-09-20): evidence report ladder prints the implement/docs/any rung-2 line at n ≥ 5 with its first-gate fraction beside rung 1's
- STALE ladder-implement-docs-rung3-unmeasured (owner orchestrator, opened 2026-09-06, review by 2026-09-20): evidence report ladder prints the implement/docs/any rung-3 line at n ≥ 5 with its first-gate fraction beside rung 1's
- STALE ladder-implement-xs-rung2-unmeasured (owner orchestrator, opened 2026-09-06, review by 2026-09-20): evidence report ladder prints the implement/any/XS rung-2 line at n ≥ 5 with its first-gate fraction beside rung 1's
- STALE ladder-implement-xs-rung3-unmeasured (owner orchestrator, opened 2026-09-06, review by 2026-09-20): evidence report ladder prints the implement/any/XS rung-3 line at n ≥ 5 with its first-gate fraction beside rung 1's
- STALE ladder-rung3-demand-unmeasured (owner orchestrator, opened 2026-09-06, review by 2026-09-20): five `.escalate` records, or a note that none was needed in a month
- STALE codex-failure-strings-unmeasured (owner orchestrator, opened 2026-09-08, review by 2026-09-22): the first failed Codex run's agent output (never a log body) classified by hand and its pattern added to factory_error_class with a bats row, or five Codex runs without a failure
- claude-weekly-limit-unmeasured (owner orchestrator, opened 2026-09-09, review by 2026-10-06): a persisted source for the weekly percentage is found, or the reset probe's boolean is recorded as a limit-event row
- STALE openrouter-cost-at-the-broker-live (owner orchestrator, opened 2026-09-09, review by 2026-09-22): the first evidence ingest openrouter-usage after switch #23 reports ≥ 1 row with status ok and a non-null cost_usd
- STALE otel-desktop-harness-unmeasured (owner orchestrator, opened 2026-09-09, review by 2026-09-22): a desktop Code-tab session's debug log carries isTelemetryEnabled=true, or SP3b moves the variables to environment.sessionVariables
- STALE otel-identity-drop-live (owner orchestrator, opened 2026-09-09, review by 2026-09-22): after one real session the runbook's identity grep prints 0 for every collector file

=== M7 ===
time: 2026-09-27T02:15:06Z
$ nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-14

=== M8 ===
time: 2026-09-27T02:15:09Z
$ bash tools/ritual.sh inflight /home/user/tvix-aios-os

=== M9 ===
time: 2026-09-27T02:15:12Z
$ bash tools/session-start.sh
## Board — START HERE (docs/OPERATIONS.md)
## START HERE (2026-09-14 18:40 CDT, session 23 — THE REVISION ROUND IS COMPLETE: ALL NINE BATCH PLANS ARE DISPATCHABLE. Sequential run `wf_7758dead-e5e` (62 agents, no errors, 14:16–18:30, after the morning's parallel run was cut by the 5-hour limit): seat-harness 36 (morning run), helm 38, generation 34→38 (second round), isolation 36, knowledge 38, platform 41, evidence 38, factory 34→38 (second round), defects 38 — all `dispatch`, no judge dropped; judgements `docs/reviews/plan-judgements/2026-09-14-batch-<key>[-r2].md`, all committed. The revised drafts: `~/factory/batch/2026-09-11/drafts-r2/2026-09-11-<key>.md` with `<key>.errata.md` (one row per erratum: applied / refuted with the command / folded) — NOT in the plans directory: the operator lands them. SET-CHECK of the nine together in a `cp -a` scratch tree: `tasks.py check` EXIT 0 with zero lines (the per-draft `acceptance … not in docs/MAP.md` and sibling-key lines were artefacts of checking one draft alone), no key collision against 327 live keys; `drafts-r2/LANDING.md` carries the outputs, the edges and the recipe.
LANDING ORDER (forced by cross-plan `dependsOn`, acyclic): evidence → factory → platform → generation → helm → knowledge → isolation → seat-harness → defects (edges KN16→PL5, GN8/GN11→EV10/EV15, HM8→EV15, IS13→HM3, SA1/SA7→IS10, DF1→IS10). Each plan: Write tool into `docs/superpowers/plans/2026-09-11-<key>.md` (names per `docs/ledger/subsystems.toml`; the guard refuses `cp` there), `tasks.py check`, `write-board`, commit `<area>: … (test: …)`. PREREQUISITES (operator): HH5–HH10 have no withdrawn rows in `docs/ledger/task-status.toml` though decision 9b (`docs/decisions/2026-09-09-redesign-answers.md:22`) supersedes them; EV6 × HH6/HH8/HH9 collide on flake.nix (live, pre-existing); EV3 then EV4 gate DF1/DF3/DF4/DF6/FA19/EV18.
READ TOGETHER BEFORE LANDING: GN8 was redesigned in generation's second round — the feed no longer writes the evidence store; it POSTs HM8's body to `http://127.0.0.1:7710/v1/engage` (loopback-only, drops on error) because the evidence draft's EV14 makes keyed `replace_stream` the stream's only verb and the helm draft assigns the feed-side POST to GN; helm's judgement flag
…board truncated at 2300 chars (SESSION_START_CAP_BOARD)

# Evidence bundle — 2026-09-27T02:15:12Z

**Live:** unknown generation at none. **HEAD:** c9c5bd7c0494 — WORKING TREE DIRTY.

## Checks covering HEAD and the live system

- addon: HEAD —; live —
- comfy-upstream-probe-unit: HEAD —; live —
- comfy-worlds-assertion-negative-hosts: HEAD —; live —
- comfy-worlds-assertion-negative-name: HEAD —; live —
- comfy-worlds-assertion-negative-password-path: HEAD —; live —
- comfy-worlds-assertion-negative-ports: HEAD —; live —
- comfy-worlds-eval: HEAD —; live —
- comfy-worlds-unit: HEAD —; live —
- comfyui-cliploader-krea2: HEAD —; live —
- comfyui-eval: HEAD —; live —
- comfyui-package: HEAD —; live —
- comfyui-startup-clean: HEAD —; live —
- comfyui-vm: HEAD —; live —
- config: HEAD —; live —
- config-precedence: HEAD —; live —
- config-rejects-typo: HEAD —; live —
- core-backup-wiring: HEAD —; live —
- core-gaming-wiring: HEAD —; live —
- custom: HEAD —; live —
- evidence-unit: HEAD —; live —
- factory-unit: HEAD —; live —
- flake-check: HEAD —; live —
- helm-control-eval: HEAD —; live —
- helm-control-vm: HEAD —; live —
- helm-declaration: HEAD —; live —
- helm-declaration-negative-block: HEAD —; live —
- helm-declaration-negative-field: HEAD —; live —
- helm-declaration-negative-profile: HEAD —; live —
- helm-declaration-negative-program: HEAD —; live —
- helm-declaration-negative-seat: HEAD —; live —
- helm-home-assertion-negative-duplicate: HEAD —; live —
- helm-home-assertion-negative-enable: HEAD —; live —
- helm-home-assertion-negative-path: HEAD —; live —
- helm-home-assertion-negative-profile: HEAD —; live —
- helm-home-assertion-negative-seats: HEAD —; live —
- helm-home-eval: HEAD —; live —
- helm-home-package: HEAD —; live —
- helm-home-reversible: HEAD —; live —
- helm-home-unit: HEAD —; live —
- helm-unit: HEAD —; live —
- helm-vm: HEAD —; live —
- host-core: HEAD —; live —
- integration: HEAD —; live —
- lab-vm: HEAD —; live —
- l
…bundle truncated at 2100 chars (SESSION_START_CAP_BUNDLE)

# Task brief (generated 2026-09-27T02:15:13Z)

| repo | landed | approved | rejected | ran | running | recorded | ready | blocked | deferred-to-brief | withdrawn | parked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 0 | 199 | 16 | 0 | 0 | 0 | 31 | 42 | 0 | 7 | 0 | 0 | 0 |
| media | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gaming | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| nixos-skill | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dsh-harness | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 |
| codex | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| openai-lab | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 |

**Next wave** — nixos-agent-env: EV1(nix-module) EV10(docs-runbook) EV11(python-evidence) EV12(python-evidence) EV14(python-evidence) EV16(nix-check) EV17(python-evidence) EV5(python-evidence) FA10(docs-runbook) FA11(bash-driver) FA13(bash-driver) FA14(bash-driver) FA3(bash-driver) FIX5(bash-driver) FIX5b(bash-driver) FIX5c(bash-driver) FIX5d(bash-driver) FIX6(nix-module) FIX7(bash-driver) HH2(python-evidence) HH3(nix-module) IS2(docs-runbook) IS4(nix-module) N13(python-evidence) N14(bash-driver) N15(nix-check) N16(python-evidence) N17(bash-driver) N18(js-workflow) PL1(docs-runbook) UI1(bash-driver) · gaming: PB0(any) · dsh-harness: H1(any) H2b(any) (plan 2026-09
…brief truncated at 1400 chars (SESSION_START_CAP_BRIEF)

ritual: the board's queue block is stale - evidence tasks --root . write-board, then commit

## Operator model (docs/board/operator-model.md)
# Operator model (derived; the board holds pauses and open items — this file never lists them)

## Preferences, ranked

- terse, no preamble (§8)
- privacy outranks everything, nothing leaves the machine (`2026-09-05-telemetry-store-decisions.md`)
- tool names read literally, plain words for a softkey (`2026-09-02-amendment-softkey.md`)
- tell me when the brief is wrong rather than route around it (§8)
- prefer failing the build over a runtime check (§8)
- one phase at a time, the operator 
…operator truncated at 500 chars (SESSION_START_CAP_OPERATOR)

Where everything is: docs/runbooks/session.md

=== M10 ===
time: 2026-09-27T02:15:18Z
$ grep -n '^## \|^### ' docs/MAP.md | head -120
5:## NixOS modules
20:## Packages
34:## Checks (nix build .#checks.x86_64-linux.<name>)
98:## Tests
115:## Hosts
130:## Tools

CHECKS
- host-core
- proton-drive-cli
- assertion-positive
- assertion-negative
- manifests-validate
- lint
- addon
- factory-unit
- helm-unit
- helm-home-unit
- helm-home-package
- evidence-unit
- subsystems-manifest
- usage-ingest-wiring
- claims-validate
- ledger-unit
- helm-eval
- evidence-eval
- helm-assertion-negative
- helm-control-eval
- helm-control-assertion-negative-profiles
- helm-control-assertion-negative-enable
- helm-control-assertion-negative-agentunit
- helm-control-assertion-negative-workspace
- helm-home-eval
- helm-home-assertion-negative-enable
- helm-home-assertion-negative-path
- helm-home-assertion-negative-profile
- helm-home-assertion-negative-seats
- helm-home-assertion-negative-duplicate
- helm-home-reversible
- lane-eval
- lane-assertion-negative
- lane-unit
- lane-polkit-unit
- seat-eval
- seat-assertion-negative
- seat-unit
- lane-vm
- seat-vm
- telemetry-eval
- telemetry-vm
- integration
- proton-backup-vm
- helm-vm
- helm-control-vm
- managed-settings
- cowork-eval
- managed-settings-user-scope
- managed-settings-assertion-negative
- module-eval
- unit
- proton-backup-eval
- core-backup-wiring
- core-gaming-wiring
- helm-declaration
- helm-declaration-negative-profile
- helm-declaration-negative-program
- helm-declaration-negative-seat
- helm-declaration-negative-block
- helm-declaration-negative-field

=== M11 ===
time: 2026-09-27T02:15:39Z
$ cat docs/ledger/routing.toml
# Model routing for the whole factory: the HEADLESS seat driver
# (tools/factory/seat) reads the openrouter rows; tools/factory/route.py
# derives the dark factory's models map from the claude rows. The interactive
# seat the operator opens on core is not governed by this file.
# Lookup: factory_route [--route R] <role> <kind> <size>. Each row carries a
# route (openrouter = DeepSeek via OpenRouter, claude = the dark factory's
# Anthropic models); a row without a route key defaults to openrouter. The
# most specific matching row wins (fewest "any" fields); ties go to the first
# row; a row with all three "any" is the default for its route and must exist.
# Explicit --model, OPENROUTER_MODEL and OPENROUTER_REASONING_EFFORT always
# override. `area` is a specificity field only (no --area flag): an area-keyed
# row matches any request and beats an area-"any" row. Evidence for the rows:
# docs/reviews/2026-09-05-m2b-effort-measurement.md,
# docs/reviews/2026-09-05-model-comparison.md. Change rows here, nowhere else.
# A `rung` climbs within one (route, role, kind, size, class, area) key: the
# fix round is rung 2 and the re-plan rung 3 (rule A1), a `fallback` is a
# sideways relaunch (the three relaunch classes); a row above rung 1 exists
# only with a claims row until the report justifies it. `class` and `area`
# default to "any"; `rung` defaults to 1; `fallback` names a model that is
# another row's model. A claude row that carries a class is the operator
# terminus (see the docs-spec/docs-plan-run rows below): the rung-1 winner
# search also considers those claude rows, and a claude win escalates.

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
area = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

# unmeasured: ladder-implement-docs-rung2-unmeasured
[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
area = "any"
rung = 2
model = "deepseek/deepseek-v4-pro-0813"
effort = "off"

# unmeasured: ladder-implement-docs-rung3-unmeasured
[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
area = "any"
rung = 3
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "openrouter"
role = "implement"
kind = "any"
size = "XS"
area = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

# unmeasured: ladder-implement-xs-rung2-unmeasured
[[route]]
route = "openrouter"
role = "implement"
kind = "any"
size = "XS"
area = "any"
rung = 2
model = "deepseek/deepseek-v4-pro-0813"
effort = "off"

# unmeasured: ladder-implement-xs-rung3-unmeasured
[[route]]
route = "openrouter"
role = "implement"
kind = "any"
size = "XS"
area = "any"
rung = 3
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
area = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

# unmeasured: ladder-implement-code-rung2-unmeasured
[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
area = "any"
rung = 2
model = "deepseek/deepseek-v4-pro-0813"
effort = "high"

[[route]]
route = "openrouter"
role = "review"
kind = "any"
size = "any"
area = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

# unmeasured: driver-row-unmeasured
[[route]]
route = "openrouter"
role = "orchestrate"
kind = "any"
size = "any"
area = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
area = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "claude"
role = "orchestrate"
kind = "any"
size = "any"
area = "any"
model = "fable"
effort = "high"

[[route]]
route = "claude"
role = "baseline"
kind = "any"
size = "any"
area = "any"
model = "sonnet"
effort = "low"

[[route]]
route = "claude"
role = "implement"
kind = "any"
size = "any"
area = "any"
model = "sonnet"
effort = "high"

[[route]]
route = "claude"
role = "review"
kind = "code"
size = "any"
area = "any"
model = "opus"
effort = "high"

[[route]]
route = "claude"
role = "review"
kind = "docs"
size = "any"
area = "any"
model = "sonnet"
effort = "medium"

[[route]]
route = "claude"
role = "verify"
kind = "any"
size = "any"
area = "any"
model = "sonnet"
effort = "medium"

[[route]]
route = "claude"
role = "research"
kind = "any"
size = "any"
area = "any"
model = "sonnet"
effort = "medium"

[[route]]
route = "claude"
role = "audit"
kind = "any"
size = "any"
area = "any"
model = "fable"
effort = "high"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
area = "any"
model = "sonnet"
effort = "medium"

# FA1 (amendment 2026-09-10, decision 28 — OpenRouter only): the docs-spec and
# docs-plan-run classes are the operator terminus. Their claude row sits alone
# at rung 3 (no rung 1/2 — the ladder check exempts class-scoped claude keys),
# so a rung-3 lookup for either class beats the openrouter docs/any row and
# escalates (exit 4, the fable launch line printed); the operator pastes that
# line. Source: docs/decisions/2026-09-09-redesign-answers.md:114-157.
[[route]]
route = "claude"
role = "implement"
kind = "docs"
size = "any"
class = "docs-spec"
area = "any"
rung = 3
model = "fable"
effort = "high"

[[route]]
route = "claude"
role = "implement"
kind = "docs"
size = "any"
class = "docs-plan-run"
area = "any"
rung = 3
model = "fable"
effort = "high"

# FA2 (decision 30b, 2026-09-10 correction — OpenRouter only): the batched
# path for the same two drafting classes, beside FA1's interactive terminus.
# The batch runs on the OpenRouter lane's async endpoint (POST
# /api/beta/batches) at 50 % of standard pricing, measured live in
# docs/research-2026-09-11-batch-lane.md. It wins only when the caller asks
# for it (--route openrouter-batch): the default openrouter caller keeps the
# Flash ladder, and the FA1 rung-3 claude rows above keep the operator-watched
# interactive path, so a batch row never captures an interactive call. The
# route carries its own any/any/any default row (both parsers require one).
[[route]]
route = "openrouter-batch"
role = "implement"
kind = "docs"
size = "any"
class = "docs-spec"
area = "any"
model = "anthropic/claude-fable-5.1:batch"
effort = "high"

[[route]]
route = "openrouter-batch"
role = "implement"
kind = "docs"
size = "any"
class = "docs-plan-run"
area = "any"
model = "anthropic/claude-fable-5.1:batch"
effort = "high"

[[route]]
route = "openrouter-batch"
role = "any"
kind = "any"
size = "any"
area = "any"
model = "anthropic/claude-fable-5.1:batch"
effort = "high"
=== M12 ===
time: 2026-09-27T02:15:42Z
$ git log --since=2026-09-04 --format='%ci%x09%s' | head -80
2026-09-26 14:15:03 -0500	snapshot

=== M13 ===
time: 2026-09-27T02:15:46Z
$ tools/factory/seat/factory-brief docs/superpowers/plans/2026-09-05-evidence-store.md E1
## Global Constraints


- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown outside `tests/run-mount-tests.sh`, no reading `/var/lib/secrets/*`, `~/.config/openrouter/key` or `~/.config/restic/password`. The operator switches (§"Operator" below).
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null` a gated command.
- Each task's spec names its own commit subject; the trailer is exactly `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- TDD: the failing check first, shown red, then green. A load-bearing test counts only once it has been shown to fail; a test that cannot fail is a `vacuous-test` major finding. Every proxy names what it stands in for and its gap (`docs/decisions/2026-09-03-test-based-reality-amendments.md`).
- **The Python blocks below are specifications, not byte-exact files.** The repo has no ruff config, so `ruff format` (88 columns, via treefmt and `checks.lint`) rewraps most of them. After writing each block run `nix develop -c ruff format <the paths this task created or changed>`, re-run the task's tests, then the lint gate. A reformatting-only difference from the plan text is not a deviation.
- Python is stdlib only in `pkgs/evidence`, `pkgs/helm`, `pkgs/broker` (mitmproxy is the one runtime dependency the broker already has). Tests may use pytest.
- **One writer per tree.** An implementer works only in the isolated worktree it was started in, on exactly one branch named by its task key; `touches` is a contract — a file outside it is a deviation to report, not to write.
- Claude agents never write inside `~/flakes/dsh-harness`; this plan touches only `~/nixos-agent-env`.
- Nix style: statix rejects `{ ... }:` headers (write `_:` or name the args); `hosts/core/hardware-configuration.nix` is exempt from formatting. Shell pasted into `githooks/pre-commit` is reformatted by shfmt: paste, run treefmt, then copy the formatted text into any Nix string that must stay identical.
- No secrets in the repo; no example row in `claims.toml` may quote a key, token or path under `/var/lib/secrets`.

## Assumptions


1. The host pin's `python3` is ≥ 3.11 (`tomllib` in the stdlib); the devShell has 3.14.7, whose `multiprocessing` default is `forkserver` (tests spawn subprocesses instead). `pyyaml` is **not** available, hence TOML.
2. `EVIDENCE_STORE` (a directory path) is honoured by every writer; tests set it to a temp dir and never touch `/var/lib/evidence`. Every writer passes `--store "${EVIDENCE_STORE:-/var/lib/evidence}"` explicitly.
3. Until the operator switches after wave 2, `/var/lib/evidence` does not exist on the host: recorders report "not recorded" and carry on (never a failure), and the Helm tiles fall back to today's file-based rule when `checks.jsonl` is absent (E5). Nothing in this plan needs the switch to be tested.
4. E1 and E3 integrate in the same wave: E3's prompt text names `pkgs/evidence/evidence.py`, which E1 creates. Their unit tests are text-only and do not execute it.
5. `git diff --quiet A B -- . ':!docs' ':!*.md'` exits 0 for docs-equivalent, 1 for different, 128 for an unknown revision (treated as different). Verified 2026-09-05.
6. The operator re-syncs `~/factory/bin` from `tools/factory/seat` after E7 and R10 land (R10 makes the copy unnecessary).
7. The Nix build sandbox has no zoneinfo and no `/usr/bin/env`: local-time tests use a POSIX `TZ` string (`CST6CDT,M3.2.0,M11.1.0`), bats stubs use the `$REAL_BASH` the file already resolves.
8. `checks.unit` skips the basket mount tests (they need namespace root); R7's red-first proof runs under `nix develop -c tests/run-mount-tests.sh`.

### E1 (code, M) — the evidence store: module, CLI, schema, checks

**dependsOn:** none

**Files:**
- Create: `nixosModules/evidenceStore.nix`, `pkgs/evidence/evidence.py`, `pkgs/evidence/SCHEMA.md`, `tests/evidence/test_evidence.py`
- Modify: `flake.nix` (nixosModules export; `packages.evidence`; `checks.evidence-unit`, `checks.evidence-eval`; `host-core` assertions; the `lint` ruff lists; `nixosConfigurations.core.modules`), `hosts/core/default.nix` (enable), `hosts/core/proton-backup.nix` (restic path), `githooks/pre-commit` (ruff lists)

**Interfaces:**
- Produces the CLI `evidence` (installed on the host by the module; runnable pre-switch as `nix develop -c python3 pkgs/evidence/evidence.py …` or `nix run .#evidence --`):
  - `evidence [--store DIR] record <stream> --json '<object with "kind">'` → appends `{"v":1,"ts":"<UTC Z>", …object}`, prints the row.
  - `evidence [--store DIR] record-check --name N --rev <40 hex> (--ok|--fail) --class C --src S [--duration SECONDS] [--log-tail-file F]` → appends to `checks.jsonl` a row `{"kind":"check","name":N,"rev":…,"ok":bool,"class":C,"src":S,"duration_s":…,"log_tail":…}`.
  - `evidence [--store DIR] latest-check --name N --rev SHA` → prints the newest matching row, exit 0; exit 1 when none.
  - `--store` defaults to `$EVIDENCE_STORE`, then `/var/lib/evidence`.
- Produces the Python API in `pkgs/evidence/evidence.py`: `append(store, stream, row, ts=None) -> dict`, `read(store, stream) -> list[dict]`, `latest_check(store, name, rev) -> dict | None`, constants `VERSION = 1`, `CLASSES`, `STREAM_RE`, `REV_RE`.
- Produces the NixOS options `services.evidence-store.{enable, path (default "/var/lib/evidence"), owner (default "dalhaka"), group (default "users"), package}`; the module installs the CLI and the tmpfiles rules `d <path> 0750 <owner> <group> -` and `d <path>/ledger 0750 <owner> <group> -`. The wrapper embeds the **directory** `pkgs/evidence` (E9's `bundle` imports the sibling `claims.py`), never the lone file.
- `pkgs/evidence/SCHEMA.md` is the contract every other task writes against.

- [ ] **Step 1: Write the failing tests** — `tests/evidence/test_evidence.py`:

```python
"""Evidence store unit tests (plan 2026-09-05-evidence-store, E1)."""

import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "evidence.py",
        pathlib.Path("pkgs/evidence/evidence.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))  # bundle() imports the sibling claims.py
    spec = importlib.util.spec_from_file_location("evidence", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["evidence"] = mod
    spec.loader.exec_module(mod)
    return mod, src


ev, SRC = load()
REV_A = "a" * 40
REV_B = "b" * 40


def test_append_creates_stream_with_envelope_and_mode(tmp_path):
    row = ev.append(str(tmp_path), "checks", {"kind": "check", "name": "lint"}, ts="2026-09-05T12:00:00Z")
    path = tmp_path / "checks.jsonl"
    assert row == {"v": 1, "ts": "2026-09-05T12:00:00Z", "kind": "check", "name": "lint"}
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    lines = path.read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0]) == row


def test_append_is_append_only_and_ordered(tmp_path):
    ev.append(str(tmp_path), "runs", {"kind": "factory-run", "n": 1}, ts="2026-09-05T12:00:00Z")
    ev.append(str(tmp_path), "runs", {"kind": "factory-run", "n": 2}, ts="2026-09-05T12:00:01Z")
    assert [r["n"] for r in ev.read(str(tmp_path), "runs")] == [1, 2]


def test_bad_stream_name_is_refused(tmp_path):
    with pytest.raises(ValueError):
        ev.append(str(tmp_path), "../etc", {"kind": "x"})
    with pytest.raises(ValueError):
        ev.append(str(tmp_path), "Checks", {"kind": "x"})


def test_read_missing_stream_is_empty(tmp_path):
    assert ev.read(str(tmp_path), "checks") == []


def test_read_skips_a_torn_line(tmp_path):
    ev.append(str(tmp_path), "checks", {"kind": "check", "name": "a"}, ts="2026-09-05T12:00:00Z")
    with open(tmp_path / "checks.jsonl", "a") as fh:
        fh.write('{"v":1,"ts":"2026-09-05T12:00:01Z","kind":"che')
    assert [r["name"] for r in ev.read(str(tmp_path), "checks")] == ["a"]


def test_latest_check_picks_newest_for_name_and_rev(tmp_path):
    s = str(tmp_path)
    ev.append(s, "checks", {"kind": "check", "name": "flake-check", "rev": REV_A, "ok": False}, ts="2026-09-05T01:00:00Z")
    ev.append(s, "checks", {"kind": "check", "name": "flake-check", "rev": REV_A, "ok": True}, ts="2026-09-05T03:00:00Z")
    ev.append(s, "checks", {"kind": "check", "name": "flake-check", "rev": REV_B, "ok": False}, ts="2026-09-05T04:00:00Z")
    ev.append(s, "checks", {"kind": "check", "name": "lint", "rev": REV_A, "ok": False}, ts="2026-09-05T05:00:00Z")
    assert ev.latest_check(s, "flake-check", REV_A)["ok"] is True
    assert ev.latest_check(s, "flake-check", REV_B)["ok"] is False
    assert ev.latest_check(s, "unit", REV_A) is None


def cli(tmp_path, *args):
    env = dict(os.environ, EVIDENCE_STORE=str(tmp_path))
    return subprocess.run([sys.executable, str(SRC), *args], capture_output=True, text=True, env=env, check=False)


def test_cli_record_check_ok_and_fail(tmp_path):
    tail = tmp_path / "tail.txt"
    tail.write_text("last lines\n")
    r = cli(tmp_path, "record-check", "--name", "flake-check", "--rev", REV_A, "--ok", "--class", "nix-check", "--src", "helm-nightly", "--duration", "105", "--log-tail-file", str(tail))
    assert r.returncode == 0, r.stderr
    printed = json.loads(r.stdout)
    assert printed["ok"] is True and printed["duration_s"] == 105 and printed["log_tail"] == "last lines\n"
    r = cli(tmp_path, "record-check", "--name", "flake-check", "--rev", REV_A, "--fail", "--class", "nix-check", "--src", "seat-integrate")
    assert r.returncode == 0 and json.loads(r.stdout)["ok"] is False
    assert [row["ok"] for row in ev.read(str(tmp_path), "checks")] == [True, False]


def test_cli_record_check_rejects_short_rev_and_unknown_class(tmp_path):
    r = cli(tmp_path, "record-check", "--name", "lint", "--rev", "abc1234", "--ok", "--class", "nix-check", "--src", "x")
    assert r.returncode == 2 and not (tmp_path / "checks.jsonl").exists()
    r = cli(tmp_path, "record-check", "--name", "lint", "--rev", REV_A, "--ok", "--class", "guess", "--src", "x")
    assert r.returncode == 2


def test_cli_record_requires_kind(tmp_path):
    r = cli(tmp_path, "record", "runs", "--json", '{"plan": "p"}')
    assert r.returncode == 2 and not (tmp_path / "runs.jsonl").exists()
    r = cli(tmp_path, "record", "runs", "--json", '{"kind": "factory-run", "plan": "p"}')
    assert r.returncode == 0 and json.loads(r.stdout)["plan"] == "p"


def test_cli_latest_check_exit_codes(tmp_path):
    assert cli(tmp_path, "latest-check", "--name", "lint", "--rev", REV_A).returncode == 1
    cli(tmp_path, "record-check", "--name", "lint", "--rev", REV_A, "--ok", "--class", "nix-check", "--src", "x")
    r = cli(tmp_path, "latest-check", "--name", "lint", "--rev", REV_A)
    assert r.returncode == 0 and json.loads(r.stdout)["name"] == "lint"


def test_concurrent_appends_keep_every_line_parseable(tmp_path):
    # PROXY, stated per the amendments: Linux serialises O_APPEND writes of
    # this size on a local filesystem even without the flock, so this test
    # cannot turn red by removing the lock. It proves N processes leave
    # N*M parseable rows; the lock's own effect is a recorded gap
    # (claims.toml: evidence-flock-effect-unmeasured, E2).
    # Subprocesses, not multiprocessing: Python 3.14 defaults to forkserver
    # on Linux, which pickles the target and cannot carry a function defined
    # inside a test.
    prog = (
        "import sys;"
        "sys.path.insert(0, sys.argv[1]);"
        "import evidence as ev;"
        "i = int(sys.argv[3]);"
        "[ev.append(sys.argv[2], 'runs', {'kind': 't', 'i': i, 'j': j, 'pad': 'x' * 2000}) for j in range(50)]"
    )
    procs = [subprocess.Popen([sys.executable, "-c", prog, str(SRC.parent), str(tmp_path), str(i)]) for i in range(8)]
    for p in procs:
        assert p.wait() == 0
    rows = ev.read(str(tmp_path), "runs")
    assert len(rows) == 400
    assert {(r["i"], r["j"]) for r in rows} == {(i, j) for i in range(8) for j in range(50)}
```

- [ ] **Step 2: Run it red** — `cd ~/nixos-agent-env && nix develop -c pytest tests/evidence -q` → collection error, `StopIteration` from `load()` (no `pkgs/evidence/evidence.py`).

- [ ] **Step 3: Write `pkgs/evidence/evidence.py`**

```python
"""evidence — the append-only evidence store.

Plan: docs/superpowers/plans/2026-09-05-evidence-store.md. Python 3 stdlib
only: this file runs inside hardened systemd --user units (Helm) with the
bare pkgs.python3, in the seat driver, and in dark-factory agents.

Streams are JSONL files under one directory. Every row carries v (schema
version), ts (UTC, RFC3339 with 'Z') and kind. Appends hold an exclusive
flock on the stream file so the Helm units, the seat driver and several
factory agents can write at the same time without interleaving lines.
Rows are never rewritten in place (the token/cost ledger under <store>/ledger
is the one exception and is owned by tools/ledger/factory.py).
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
import pathlib
import re
import sys

VERSION = 1
DEFAULT_STORE = "/var/lib/evidence"
STREAM_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
CLASSES = ("unit", "eval", "vm", "nix-check", "curl", "browser", "operator", "unmeasured")


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stream_path(store: str, stream: str) -> pathlib.Path:
    if not STREAM_RE.match(stream):
        raise ValueError(f"bad stream name: {stream!r}")
    return pathlib.Path(store) / f"{stream}.jsonl"


def append(store: str, stream: str, row: dict, ts: str | None = None) -> dict:
    """Append one row (envelope added) under an exclusive lock; return it."""
    full = {"v": VERSION, "ts": ts or now_iso(), **row}
    line = json.dumps(full, sort_keys=True, separators=(",", ":")) + "\n"
    path = stream_path(store, stream)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    try:
        os.fchmod(fd, 0o640)  # the umask must not widen or narrow the group bit
        fcntl.flock(fd, fcntl.LOCK_EX)
        with os.fdopen(fd, "a") as fh:  # takes ownership of fd; close releases the lock
            fd = None
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
    finally:
        if fd is not None:
            os.close(fd)
    return full


def read(store: str, stream: str) -> list[dict]:
    """Every parseable row of a stream, in file order; [] when absent."""
    path = stream_path(store, stream)
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a torn line never hides the rows around it
    return rows


def latest_check(store: str, name: str, rev: str) -> dict | None:
    rows = [
        r
        for r in read(store, "checks")
        if r.get("kind") == "check" and r.get("name") == name and r.get("rev") == rev
    ]
    return max(rows, key=lambda r: r["ts"]) if rows else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evidence")
    parser.add_argument("--store", default=os.environ.get("EVIDENCE_STORE", DEFAULT_STORE))
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rec = sub.add_parser("record", help="append one row to a stream")
    p_rec.add_argument("stream")
    p_rec.add_argument("--json", required=True, help='a JSON object with a "kind"')

    p_chk = sub.add_parser("record-check", help="append one check observation")
    p_chk.add_argument("--name", required=True)
    p_chk.add_argument("--rev", required=True)
    grp = p_chk.add_mutually_exclusive_group(required=True)
    grp.add_argument("--ok", action="store_true")
    grp.add_argument("--fail", action="store_true")
    p_chk.add_argument("--class", dest="cls", required=True, choices=CLASSES)
    p_chk.add_argument("--src", required=True)
    p_chk.add_argument("--duration", type=int)
    p_chk.add_argument("--log-tail-file")

    p_lat = sub.add_parser("latest-check", help="newest observation for a check at a revision")
    p_lat.add_argument("--name", required=True)
    p_lat.add_argument("--rev", required=True)

    a = parser.parse_args(argv)
    if a.cmd == "record":
        try:
            row = json.loads(a.json)
        except json.JSONDecodeError as e:
            parser.error(f"--json is not valid JSON: {e}")
        if not isinstance(row, dict) or "kind" not in row:
            parser.error('--json must be an object with a "kind"')
        print(json.dumps(append(a.store, a.stream, row), sort_keys=True))
        return 0
    if a.cmd == "record-check":
        if not REV_RE.match(a.rev):
            parser.error("--rev must be a full 40-hex commit id")
        row: dict = {"kind": "check", "name": a.name, "rev": a.rev, "ok": bool(a.ok), "class": a.cls, "src": a.src}
        if a.duration is not None:
            row["duration_s"] = a.duration
        if a.log_tail_file:
            row["log_tail"] = pathlib.Path(a.log_tail_file).read_text()[-4000:]
        print(json.dumps(append(a.store, "checks", row), sort_keys=True))
        return 0
    if a.cmd == "latest-check":
        row = latest_check(a.store, a.name, a.rev)
        if row is None:
            return 1
        print(json.dumps(row, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Write `pkgs/evidence/SCHEMA.md`** (the contract; other tasks quote it):

```markdown
# Evidence store — streams and row shapes (v1)

Directory: `services.evidence-store.path`, default `/var/lib/evidence` (env `EVIDENCE_STORE`
overrides for tests and pre-switch use; every writer also passes `--store` explicitly). One JSONL
file per stream; append-only under flock; every row: `{"v":1,"ts":"2026-09-05T12:00:00Z","kind":"<kind>", ...}`.
Stream names match `^[a-z][a-z0-9-]{0,31}$`.

| stream | kind | fields | writers |
|---|---|---|---|
| `checks` | `check` | `name` (check name; `flake-check` = the whole `nix flake check`), `rev` (40 hex), `ok` (bool), `class` (`unit|eval|vm|nix-check|curl|browser|operator|unmeasured`), `src` (`helm-nightly`, `seat-integrate`, `dark-factory-verify`, …), `duration_s`?, `log_tail`? (≤ 4000 chars) | helm-flake-check (E5), factory-integrate (E7), dark-factory verify (E3) |
| `helm-status` | `helm-status` | `tiles` (name → `ok|warn|fail|unknown`), `reason` (`change|heartbeat`) | helm-collect (E6) |
| `runs` | `factory-run` | `plan`, `prefix`, `baseline`, `integration_branch`, `tasks[]{key,status,commit,fixRounds}`, `verify` (`pass|fail|skipped|none`), `delivered`, `agents`, `output_tokens`, `run_id`? | dark-factory recorder (E3) |
| `ledger/*.jsonl` | per `tools/ledger/schema.md` | the token/cost ledger; unchanged shapes; idempotent merge, the one non-append-only area | `tools/ledger/factory.py` (E4) |

Readers: `pkgs/helm/collect.py` (tiles), `evidence bundle` (E9), `tools/ledger/factory.py`.
A reader skips a torn line and never fails the whole read on one bad row.
The claims file `docs/ledger/claims.toml` is NOT a stream: it is policy, in the repo (E2).
```

- [ ] **Step 5: Write `nixosModules/evidenceStore.nix`**

```nix
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.evidence-store;
  # The whole directory, not the lone file: evidence.py imports its sibling
  # claims.py at run time (E9's bundle), and a file-valued path would copy
  # only evidence.py into the store.
  evidenceSrc = ../pkgs/evidence;
  evidenceCli = pkgs.writeShellApplication {
    name = "evidence";
    runtimeInputs = [
      pkgs.python3
      pkgs.git
    ];
    text = ''
      export EVIDENCE_STORE="''${EVIDENCE_STORE:-${cfg.path}}"
      exec python3 ${evidenceSrc}/evidence.py "$@"
    '';
  };
in
{
  options.services.evidence-store = {
    enable = lib.mkEnableOption "the append-only evidence store (JSONL streams; docs/superpowers/plans/2026-09-05-evidence-store.md)";
    path = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/evidence";
      description = "Directory holding the streams. Must be absolute; added to the backup paths by the host.";
    };
    owner = lib.mkOption {
      type = lib.types.str;
      default = "dalhaka";
      description = "Owner of the store; every writer runs as this user.";
    };
    group = lib.mkOption {
      type = lib.types.str;
      default = "users";
      description = "Group of the store directory (0750).";
    };
    package = lib.mkOption {
      type = lib.types.package;
      default = evidenceCli;
      defaultText = "the evidence CLI wrapping pkgs/evidence/evidence.py";
      description = "The evidence CLI other modules may reference.";
    };
  };
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = lib.hasPrefix "/" cfg.path;
        message = "services.evidence-store.path must be absolute";
      }
    ];
    systemd.tmpfiles.rules = [
      "d ${cfg.path} 0750 ${cfg.owner} ${cfg.group} -"
      "d ${cfg.path}/ledger 0750 ${cfg.owner} ${cfg.group} -"
    ];
    environment.systemPackages = [ cfg.package ];
  };
}
```

- [ ] **Step 6: Wire the flake and the host.** In `flake.nix`: add `evidenceStore = import ./nixosModules/evidenceStore.nix;` to `nixosModules`; add `self.nixosModules.evidenceStore` to `nixosConfigurations.core`'s module list next to `self.nixosModules.helm`; add `packages.${system}.evidence = pkgs.writeShellApplication { name = "evidence"; runtimeInputs = [ pkgs.python3 pkgs.git ]; text = ''exec python3 ${./pkgs/evidence}/evidence.py "$@"''; };`; add the checks below; extend both `ruff check` and `ruff format --check` lists (in `lint` and in `githooks/pre-commit`) with `pkgs/evidence tests/evidence`. In `hosts/core/default.nix` set `services.evidence-store.enable = true;` inside the existing `services = { … }` block. In `hosts/core/proton-backup.nix` append `"/var/lib/evidence"` to `paths`.

```nix
        evidence-unit =
          pkgs.runCommand "evidence-unit"
            {
              nativeBuildInputs = [
                helmPython
                # E9's bundle tests build a throwaway repo and run git diff.
                pkgs.git
              ];
            }
            ''
              export HOME=$TMPDIR
              export GIT_CONFIG_GLOBAL=$TMPDIR/.gitconfig
              mkdir -p pkgs tests docs
              cp -r ${self}/pkgs/evidence pkgs/evidence
              cp -r ${self}/tests/evidence tests/evidence
              # E2's validator resolves parked claims' decision files.
              cp -r ${self}/docs/decisions docs/decisions
              pytest tests/evidence -q
              touch $out
            '';
        evidence-eval =
          let
            c = evidenceEvalSystem.config;
          in
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.elem "d /var/lib/evidence 0750 dalhaka users -" c.systemd.tmpfiles.rules
            && nixpkgs.lib.elem "d /var/lib/evidence/ledger 0750 dalhaka users -" c.systemd.tmpfiles.rules
          ) "evidence-eval: the store and its ledger dir must be created 0750 dalhaka:users";
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.any (p: (p.pname or p.name or "") == "evidence") c.environment.systemPackages
          ) "evidence-eval: the evidence CLI must be installed";
          builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "evidence-eval-ok" { } "touch $out");
```

with, in the flake's `let`, beside `helmEvalSystem`:

```nix
      evidenceEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.evidenceStore
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            # NixOS requires every users.users entry to resolve isNormalUser
            # xor isSystemUser (same reason as helmEvalSystem).
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            services.evidence-store.enable = true;
          })
        ];
      };
```

In `host-core`, next to the Helm assertions:

```nix
          assert nixpkgs.lib.assertMsg c.services.evidence-store.enable
            "host-core: services.evidence-store must be enabled on core";
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.elem "/var/lib/evidence" c.services.proton-backup.paths
          ) "host-core: /var/lib/evidence must be a restic path (the store is the record)";
```

- [ ] **Step 7: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q` (11 passed); `git add` the new files; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `… evidence-eval`; `… host-core`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 8: Commit.**

**touches:** nixosModules/evidenceStore.nix, pkgs/evidence/evidence.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_evidence.py, flake.nix, hosts/core/default.nix, hosts/core/proton-backup.nix, githooks/pre-commit
**acceptance:** evidence-unit, evidence-eval, host-core, lint
**commit subject:** `evidence: append-only store on the host — module, CLI, schema, restic path (test: evidence-unit, evidence-eval, host-core, lint)`

## WORKSPACE RULES

- Work only inside the current directory. This is an isolated clone made
  for this task; the real repository lives elsewhere and nothing you do
  here touches it.
- Keep every temporary file inside this workspace. Your bash tool's /tmp and
  your file-editing tools' /tmp are two different views of the filesystem --
  a path one tool writes under /tmp may not exist for the other. Make and
  use a directory inside this workspace for scratch files instead.
- Never run `sudo`, `nixos-rebuild`, or `systemctl start|stop|restart`.
  Those are the operator's actions only, never yours.
- `git add` any new file before running `nix build` on it -- a Nix flake
  only sees files git already tracks.
- Practice TDD: show the failing check first (red), say in your own words
  what failed and why, then make the change and show the check passing
  (green). A load-bearing test only counts once it has been shown to fail.
- Run every check named in this task's acceptance criteria with:
    nix build .#checks.x86_64-linux.<name> -L --no-link
- Commit ONLY through:
    nix develop -c git commit -F <msgfile>
  on the branch `task/E1` (already checked out for you). The commit
  subject follows this repo's convention: `<area>: summary (test: <check
  names>)`. The commit carries BOTH of these trailers, each on its own line,
  in this exact order:
    Generated-By: dsh 0.1.2-rc.1 / <model> (seat headless, factory run <RUN>)
    Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
- Never `git push`.
- Before those four lines, print one line `FACTORY-PROBE <name>=<value>` per
  probe the task section names (none when it names none), the value being
  your own run's last output line.
- End your final reply with a summary in exactly this format, each item on
  its own line and nothing after it. The first line is exactly the result
  line, one space, status=done|partial|failed — no colon, no markdown; any
  other spelling is recorded as failed:
FACTORY-RESULT status=<done|partial|failed>
FACTORY-CHECKS <name>=<pass|fail|not-run> ...
FACTORY-COMMITS <n>
FACTORY-NOTES <one line>
exit=0
