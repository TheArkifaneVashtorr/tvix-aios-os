# Mechanical packet (M1–M13)

Repo root: /home/user/tvix-aios-os

## M1 — tasks.py check (verdict command; exit is the only signal)

Command:
```
nix develop -c python3 pkgs/evidence/tasks.py --root . check > /tmp/draft-scratch/packet/check.out 2> /tmp/draft-scratch/packet/check.err ; echo "exit=$?"
```

Output:
```
exit=0
```

check.out (verbatim, 0 bytes):
```
```

check.err (verbatim, 0 bytes):
```
```

## M2 — tasks.py brief

Command: `nix develop -c python3 pkgs/evidence/tasks.py --root . brief`

```
# Task brief (generated 2026-09-27T00:45:39Z)

| repo | landed | approved | rejected | ran | running | recorded | ready | blocked | deferred-to-brief | withdrawn | parked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 0 | 108 | 14 | 0 | 0 | 0 | 11 | 7 | 0 | 0 | 0 | 1 | 0 |
| media | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gaming | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| nixos-skill | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dsh-harness | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 |

**Next wave** — nixos-agent-env: N13 N14 N15 N16 N17 N18 PW1glm PW1kimi PW1pro SB6 T1 · gaming: PB0 · dsh-harness: H1 H2b (plan 2026-09-05-harness-router.md)
**Record (7 d):** 0 rej, 0 plan (vac 0, miss 0, under 0, fact 0)
**Running:** none
**Rejected, fix round owed:** nixos-agent-env/CR2 (CR2rb by cr17) · nixos-agent-env/CR2r2 (CR2r2b by cr19) · nixos-agent-env/P1flash (P1flash by mcf2) · nixos-agent-env/OG1 (OG1r by og3) · nixos-agent-env/P3Ab (P3Ab by pb3a) · nixos-agent-env/P3Arb (P3Arb by pb3arb2) · nixos-agent-env/P3Ar2 (P3Ar2b by pb3ar2b)
**Withdrawn/parked:** none
**Operator owns:** none
**Untracked plans (no typed headings, no plan-status row):** none
```

## M3 — tasks.py json (byte count only)

Command: `nix develop -c python3 pkgs/evidence/tasks.py --root . json > /tmp/draft-scratch/packet/graph.json`

```
642052 /tmp/draft-scratch/packet/graph.json
```

## M4 — tasks.py waves

Command: `nix develop -c python3 pkgs/evidence/tasks.py --root . waves --repo nixos-agent-env --json`

```
[[["N13", "N14", "N15", "N17", "N18", "SB6", "T1"], ["N16"], ["PW1glm"], ["PW1kimi"], ["PW1pro"]], [["T1W"], ["T2"], ["T3"]], [["T10a"], ["T3M"]]]
```

## M5 — tasks.py conflicts

Command: `nix develop -c python3 pkgs/evidence/tasks.py --root . conflicts`

```
nixos-agent-env: N13 (2026-09-04-loose-ends-wave-a7.md) × SB5 (2026-09-05-seat-behind-broker.md): docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md ~ docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md
nixos-agent-env: N13 (2026-09-04-loose-ends-wave-a7.md) × SB5 (2026-09-05-seat-behind-broker.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: N13 (2026-09-04-loose-ends-wave-a7.md) × T1 (2026-09-06-telemetry-store-1.md): flake.nix ~ flake.nix
nixos-agent-env: N13 (2026-09-04-loose-ends-wave-a7.md) × T1W (2026-09-06-telemetry-store-1.md): flake.nix ~ flake.nix
nixos-agent-env: N14 (2026-09-04-loose-ends-wave-a7.md) × SB5 (2026-09-05-seat-behind-broker.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: N14 (2026-09-04-loose-ends-wave-a7.md) × SB6 (2026-09-05-seat-behind-broker.md): pkgs/dsh-openrouter/dsh-openrouter.sh ~ pkgs/dsh-openrouter/dsh-openrouter.sh
nixos-agent-env: N14 (2026-09-04-loose-ends-wave-a7.md) × SB6 (2026-09-05-seat-behind-broker.md): tests/unit/70-dsh-openrouter.bats ~ tests/unit/70-dsh-openrouter.bats
nixos-agent-env: N15 (2026-09-04-loose-ends-wave-a7.md) × SB6 (2026-09-05-seat-behind-broker.md): pkgs/dsh-openrouter/default.nix ~ pkgs/dsh-openrouter/default.nix
nixos-agent-env: N15 (2026-09-04-loose-ends-wave-a7.md) × T1 (2026-09-06-telemetry-store-1.md): flake.nix ~ flake.nix
nixos-agent-env: N15 (2026-09-04-loose-ends-wave-a7.md) × T1W (2026-09-06-telemetry-store-1.md): flake.nix ~ flake.nix
nixos-agent-env: N16 (2026-09-04-loose-ends-wave-a7.md) × T1W (2026-09-06-telemetry-store-1.md): tools/ledger/factory.py ~ tools/ledger/factory.py
nixos-agent-env: N16 (2026-09-04-loose-ends-wave-a7.md) × T1W (2026-09-06-telemetry-store-1.md): tests/ledger/test_factory.py ~ tests/ledger/test_factory.py
nixos-agent-env: N16 (2026-09-04-loose-ends-wave-a7.md) × T1W (2026-09-06-telemetry-store-1.md): tools/ledger/schema.md ~ tools/ledger/schema.md
nixos-agent-env: CR4 (2026-09-05-context-reset-ritual.md) × N17 (2026-09-04-loose-ends-wave-a7.md): githooks/pre-commit ~ githooks/pre-commit
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × SB5 (2026-09-05-seat-behind-broker.md): docs/runbooks/lanes.md ~ docs/runbooks/lanes.md
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × T1 (2026-09-06-telemetry-store-1.md): tools/factory/seat/ ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × T1 (2026-09-06-telemetry-store-1.md): flake.nix ~ flake.nix
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × T1W (2026-09-06-telemetry-store-1.md): githooks/pre-commit ~ githooks/pre-commit
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × T1W (2026-09-06-telemetry-store-1.md): flake.nix ~ flake.nix
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × T2 (2026-09-06-telemetry-store-1.md): tools/factory/seat/ ~ tools/factory/seat/factory-lib.sh
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × T2 (2026-09-06-telemetry-store-1.md): tools/factory/seat/ ~ tools/factory/seat/factory-task
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × T2 (2026-09-06-telemetry-store-1.md): tests/unit/80-seat-driver.bats ~ tests/unit/80-seat-driver.bats
nixos-agent-env: N17 (2026-09-04-loose-ends-wave-a7.md) × T3 (2026-09-06-telemetry-store-1.md): tools/factory/seat/ ~ tools/factory/seat/factory-integrate
nixos-agent-env: CR4 (2026-09-05-context-reset-ritual.md) × N18 (2026-09-04-loose-ends-wave-a7.md): CLAUDE.md ~ CLAUDE.md
nixos-agent-env: N18 (2026-09-04-loose-ends-wave-a7.md) × SB5 (2026-09-05-seat-behind-broker.md): CLAUDE.md ~ CLAUDE.md
nixos-agent-env: N18 (2026-09-04-loose-ends-wave-a7.md) × SB6 (2026-09-05-seat-behind-broker.md): tests/unit/70-dsh-openrouter.bats ~ tests/unit/70-dsh-openrouter.bats
nixos-agent-env: N18 (2026-09-04-loose-ends-wave-a7.md) × T1W (2026-09-06-telemetry-store-1.md): tools/factory/dark-factory.js ~ tools/factory/dark-factory.js
nixos-agent-env: N18 (2026-09-04-loose-ends-wave-a7.md) × T1W (2026-09-06-telemetry-store-1.md): tests/factory/render.test.mjs ~ tests/factory/render.test.mjs
nixos-agent-env: CR4 (2026-09-05-context-reset-ritual.md) × SB5 (2026-09-05-seat-behind-broker.md): CLAUDE.md ~ CLAUDE.md
nixos-agent-env: CR4 (2026-09-05-context-reset-ritual.md) × T1W (2026-09-06-telemetry-store-1.md): githooks/pre-commit ~ githooks/pre-commit
nixos-agent-env: PW1pro (2026-09-05-plan-writing-comparison.md) × T3M (2026-09-06-telemetry-store-1.md): docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-pro.md ~ docs/reviews
nixos-agent-env: PW1glm (2026-09-05-plan-writing-comparison.md) × T3M (2026-09-06-telemetry-store-1.md): docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-glm.md ~ docs/reviews
nixos-agent-env: PW1kimi (2026-09-05-plan-writing-comparison.md) × T3M (2026-09-06-telemetry-store-1.md): docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-kimi.md ~ docs/reviews
dsh-harness: H1 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): README.md ~ README.md
dsh-harness: H1 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): CHANGELOG.md ~ CHANGELOG.md
dsh-harness: H2 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/using-superpowers/references/dsh-tools.md ~ skills/using-superpowers/references/dsh-tools.md
dsh-harness: H2 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/subagent-driven-development/SKILL.md ~ skills/subagent-driven-development/SKILL.md
dsh-harness: H2 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): AGENTS.md ~ AGENTS.md
dsh-harness: H2 (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): README.md ~ README.md
dsh-harness: H2b (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/using-superpowers/references/dsh-tools.md ~ skills/using-superpowers/references/dsh-tools.md
dsh-harness: H2b (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/subagent-driven-development/SKILL.md ~ skills/subagent-driven-development/SKILL.md
dsh-harness: H2b (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): AGENTS.md ~ AGENTS.md
dsh-harness: H2b (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): README.md ~ README.md
dsh-harness: H2c (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): skills/subagent-driven-development/SKILL.md ~ skills/subagent-driven-development/SKILL.md
dsh-harness: H2c (2026-09-05-harness-router.md) × P13 (2026-09-06-planning-agent.md): README.md ~ README.md
```

## M6 — evidence bundle --markdown

Command: `evidence bundle --markdown`

```
# Evidence bundle — 2026-09-27T00:45:43Z

**Live:** unknown generation at none. **HEAD:** 4a7374ca4842 — WORKING TREE DIRTY.

## Checks covering HEAD and the live system

- comfy-worlds-unit: HEAD —; live —
- comfyui-cliploader-krea2: HEAD —; live —
- comfyui-eval: HEAD —; live —
- comfyui-package: HEAD —; live —
- comfyui-startup-clean: HEAD —; live —
- comfyui-vm: HEAD —; live —
- core-backup-wiring: HEAD —; live —
- core-gaming-wiring: HEAD —; live —
- custom: HEAD —; live —
- evidence-unit: HEAD —; live —
- factory-unit: HEAD —; live —
- flake-check: HEAD —; live —
- helm-unit: HEAD —; live —
- host-core: HEAD —; live —
- ledger-unit: HEAD —; live —
- lint: HEAD —; live —
- media-fetch-bats: HEAD —; live —
- media-fetch-unit: HEAD —; live —
- proton-backup-eval: HEAD —; live —
- seat-assertion-negative: HEAD —; live —
- seat-eval: HEAD —; live —
- seat-unit: HEAD —; live —
- seat-vm: HEAD —; live —
- unit: HEAD —; live —

## Repo heads


## Helm now

- backup-parity: ok since 2026-09-05T17:41:51Z
- backup-snapshot: ok since 2026-09-05T17:41:51Z
- basket-doctor: ok since 2026-09-05T17:41:51Z
- broker: ok since 2026-09-05T17:41:51Z
- drift: ok since 2026-09-06T15:39:03Z
- flake-check: warn since 2026-09-06T08:20:22Z
- gpu: ok since 2026-09-05T17:41:51Z
- host: ok since 2026-09-05T17:41:51Z
- timers: ok since 2026-09-05T17:41:51Z

## Claims: 12 verified, 3 parked, 15 open gaps

- STALE aimdo-native-load-unmeasured (owner orchestrator, opened 2026-09-05, review by 2026-09-19): the media acceptance drill on core imports comfy_aimdo's native module and reports OK (ComfyUI worlds plan, W6), or the startup log at a GPU start names aimdo as loaded
- STALE backup-user-lane-group-unasserted (owner orchestrator, opened 2026-09-05, review by 2026-09-19): one host-core assertion that services.proton-backup.user is a member of the `lane` group (the group that owns the 2770 lane dirs the ledger lives in)
- STALE basket-verify-cannot-bind-payload (owner orchestrator, opened 2026-09-05, review by 2026-09-19): encrypt packs once (hash and ciphertext from the same bytes), or verify states that payload↔content binding needs the identity
- STALE declared-agents-zero (owner orchestrator, opened 2026-09-05, review by 2026-09-19): services.baskets.agents on core names the harnesses that actually run, or a decision records that A1–A4 have no live instance
- STALE drift-exact-measure (owner orchestrator, opened 2026-09-05, review by 2026-09-19): nix store diff-closures between the live system and the toplevel built at HEAD lists only the nixos-version file; the docs-only rule is the proxy (store paths cannot match: the toplevel bakes the commit id)
- STALE effort-policy-n1 (owner orchestrator, opened 2026-09-05, review by 2026-09-12): n ≥ 5 per arm off vs medium through the seat driver, Opus verdicts equal, tokens in the ledger
- evidence-flock-effect-unmeasured (owner orchestrator, opened 2026-09-05, review by 2026-10-03): a test that fails without the flock, or a note that Linux O_APPEND makes it belt-and-braces
- STALE factory-run-report-persisted (owner orchestrator, opened 2026-09-05, review by 2026-09-12): runs.jsonl holds one factory-run row per dark-factory run (E3)
- STALE fake-upstream-proves-what-seat-sends (owner orchestrator, opened 2026-09-05, review by 2026-09-19): one live probe per effort level against OpenRouter with the response's reasoning field recorded
- STALE forbidden-list-single-source (owner orchestrator, opened 2026-09-05, review by 2026-09-19): the local-only path list is generated from Nix and the three copies are proven identical (R9 first proves they agree)
- STALE ledger-attribution (owner orchestrator, opened 2026-09-05, review by 2026-09-12): factory-findings.jsonl rows carry task, round and label for a real run (E3+E4)
- STALE nixpkgs-host-pin-age (owner orchestrator, opened 2026-09-05, review by 2026-09-19): plan 2026-09-05-operator-items PB0 (gaming → nixos-26.05 a5cc6f2c37) then PB1 (nixpkgs-host → same rev; nix flake check -L incl. VM tests; toplevel; closure diff in docs/reviews/2026-09-05-release-upgrade-26.05.md); the operator switches; a release-age item on the board
- STALE reasoning-tokens-not-itemised (owner orchestrator, opened 2026-09-05, review by 2026-09-19): a usage record for the openrouter route carries reasoning tokens, or the ledger documents that the route never will
- STALE seat-key-exception-undecided (owner orchestrator, opened 2026-09-05, review by 2026-09-19): spec docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md (operator chose the broker-fronted seat 2026-09-05) → plan → seat-vm green → switch → the operator runs one headless and one web job through seat@ and deletes ~/.config/openrouter/key
- STALE uid1000-can-switch-profile (owner orchestrator, opened 2026-09-05, review by 2026-09-19): the switch needs a desktop password (polkit auth_admin_keep, Helm Home HH2); until then the seat guard refuses the control port (R8)
```

## M7 — claims.py validate

Command: `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06`

```
exit=0
```
(No stdout/stderr output was produced; the process exited 0.)

## M8 — tools/ritual.sh inflight

Command: `bash tools/ritual.sh inflight /home/user/tvix-aios-os`

```
(no output)
```

## M9 — tools/session-start.sh

Command: `bash tools/session-start.sh`

```
## Board — START HERE (docs/OPERATIONS.md)
## START HERE (2026-09-06 ~10:45 CDT — switch #20 live; the telemetry-1 plan dispatched (tel1b running); the seat-driver plan in the panel; the operator's holds)

**Live: generation 45 = a53d2e5 (switch #20, 2026-09-06 ~09:15 CDT; `egress-broker-seat` and `egress-netns-seat` active, `veb-seat` at 10.100.4.1/30, `seat@` linked; host-core recorded green at a2667bc, whose code is identical). ROLLBACK gen 44 = 7d20da1. HEAD is live plus this turn's docs.** The session hook shows this block's first 2,300 chars, the bundle, the brief and the in-flight list — act only on landed events.

<!-- tasks:begin -->
**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** CR4 PW1glm PW1kimi PW1pro SB5 SB6 T1 (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-06-telemetry-store-1.md)
<!-- tasks:end -->

**RUNNING: the planning workflow `plan-seat-driver`** (launched 09:11 CDT, run wf_6e43a6a3-d46; packet by 09:15, the Fable draft done 10:18 at 145 KB, three judges back by 10:30, its last phase alive at 11:01). **T1 (`tel1b`) RAN 10:42–11:07 CDT and needs its Opus gate after the Claude reset:** one commit a8c2e34 on `task/T1` (twelve files: `streams.py` 734 lines, `test_streams_policy.py` 875 lines), the four acceptance checks run by the orchestrator on that branch at 11:15 and recorded green in the store (lint, evidence-unit 240 passed, factory-unit, unit). The seat's result block was a near miss — `FACTORY-RESULT status=done` without the CHECKS/COMMITS/NOTES lines, plus three invented `FACTORY-STATUS/TASK/COMMIT` lines found nowhere in either repo — so the driver recorded `status=failed, claimed 0 commits, found 1` (P11r's rule); the seat also edited `tests/unit/83-plan-brief.bats` outside T1's `touches` (its reason: the fixture runs the real `tasks.py`, which now imports `streams.py`). Both are the gate's to judge; no fix round is launched on a near miss (telemetry design §4.3). `tel1`, the first launch at 10:37 through `factory-dispatch` in a foreground call, DIED at 10:40 (the dispatcher waits on `setsid -w`; the tool timeout killed the tree; logs `.killed-by-foreground-timeout-2026-0
…board truncated at 2300 chars (SESSION_START_CAP_BOARD)

# Evidence bundle — 2026-09-27T00:45:50Z

**Live:** unknown generation at none. **HEAD:** 4a7374ca4842 — WORKING TREE DIRTY.

## Checks covering HEAD and the live system

- comfy-worlds-unit: HEAD —; live —
- comfyui-cliploader-krea2: HEAD —; live —
- comfyui-eval: HEAD —; live —
- comfyui-package: HEAD —; live —
- comfyui-startup-clean: HEAD —; live —
- comfyui-vm: HEAD —; live —
- core-backup-wiring: HEAD —; live —
- core-gaming-wiring: HEAD —; live —
- custom: HEAD —; live —
- evidence-unit: HEAD —; live —
- factory-unit: HEAD —; live —
- flake-check: HEAD —; live —
- helm-unit: HEAD —; live —
- host-core: HEAD —; live —
- ledger-unit: HEAD —; live —
- lint: HEAD —; live —
- media-fetch-bats: HEAD —; live —
- media-fetch-unit: HEAD —; live —
- proton-backup-eval: HEAD —; live —
- seat-assertion-negative: HEAD —; live —
- seat-eval: HEAD —; live —
- seat-unit: HEAD —; live —
- seat-vm: HEAD —; live —
- unit: HEAD —; live —

## Repo heads


## Helm now

- backup-parity: ok since 2026-09-05T17:41:51Z
- backup-snapshot: ok since 2026-09-05T17:41:51Z
- basket-doctor: ok since 2026-09-05T17:41:51Z
- broker: ok since 2026-09-05T17:41:51Z
- drift: ok since 2026-09-06T15:39:03Z
- flake-check: warn since 2026-09-06T08:20:22Z
- gpu: ok since 2026-09-05T17:41:51Z
- host: ok since 2026-09-05T17:41:51Z
- timers: ok since 2026-09-05T17:41:51Z

## Claims: 12 verified, 3 parked, 15 open gaps

- STALE aimdo-native-load-unmeasured (owner orchestrator, opened 2026-09-05, review by 2026-09-19): the media acceptance drill on core imports comfy_aimdo's native module and reports OK (ComfyUI worlds plan, W6), or the startup log at a GPU start names aimdo as loaded
- STALE backup-user-lane-group-unasserted (owner orchestrator, opened 2026-09-05, review by 2026-09-19): one host-core assertion that services.proton-backup.user is a member of the `lane` group (the group that owns the 2770 lane dirs the ledger lives in)
- STALE basket-verify-cannot-bind-payload (owner orchestrator, opened 2026
…bundle truncated at 2100 chars (SESSION_START_CAP_BUNDLE)

# Task brief (generated 2026-09-27T00:45:51Z)

| repo | landed | approved | rejected | ran | running | recorded | ready | blocked | deferred-to-brief | withdrawn | parked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 0 | 108 | 14 | 0 | 0 | 0 | 11 | 7 | 0 | 0 | 0 | 1 | 0 |
| media | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gaming | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| nixos-skill | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dsh-harness | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 |

**Next wave** — nixos-agent-env: N13 N14 N15 N16 N17 N18 PW1glm PW1kimi PW1pro SB6 T1 · gaming: PB0 · dsh-harness: H1 H2b (plan 2026-09-05-harness-router.md)
**Record (7 d):** 0 rej, 0 plan (vac 0, miss 0, under 0, fact 0)
**Running:** none
**Rejected, fix round owed:** nixos-agent-env/CR2 (CR2rb by cr17) · nixos-agent-env/CR2r2 (CR2r2b by cr19) · nixos-agent-env/P1flash (P1flash by mcf2) · nixos-agent-env/OG1 (OG1r by og3) · nixos-agent-env/P3Ab (P3Ab by pb3a) · nixos-agent-env/P3Arb (P3Arb by pb3arb2) · nixos-agent-env/P3Ar2 (P3Ar2b by pb3ar2b)
**Withdrawn/parked:** none
**Operator owns:** none
**Untracked plans (no typed headings, no plan-status row):** none



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
```

## M10 — docs/MAP.md headings + check names

Command: `grep -n '^## \|^### ' docs/MAP.md | head -120`

```
5:## NixOS modules
17:## Packages
30:## Checks (nix build .#checks.x86_64-linux.<name>)
75:## Tests
91:## Hosts
105:## Tools
```

CHECKS
```
host-core
proton-drive-cli
assertion-positive
assertion-negative
manifests-validate
lint
addon
factory-unit
helm-unit
evidence-unit
claims-validate
ledger-unit
helm-eval
evidence-eval
helm-assertion-negative
helm-control-eval
helm-control-assertion-negative-profiles
helm-control-assertion-negative-enable
helm-control-assertion-negative-agentunit
helm-control-assertion-negative-workspace
lane-eval
lane-assertion-negative
lane-unit
lane-polkit-unit
seat-eval
seat-assertion-negative
seat-unit
lane-vm
seat-vm
integration
proton-backup-vm
helm-vm
helm-control-vm
managed-settings
cowork-eval
managed-settings-user-scope
managed-settings-assertion-negative
module-eval
unit
proton-backup-eval
core-backup-wiring
core-gaming-wiring
```

## M11 — docs/ledger/routing.toml

Command: `cat docs/ledger/routing.toml`

```
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
# override. Evidence for the rows:
# docs/reviews/2026-09-05-m2b-effort-measurement.md,
# docs/reviews/2026-09-05-model-comparison.md. Change rows here, nowhere else.

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
route = "openrouter"
role = "implement"
kind = "any"
size = "XS"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "openrouter"
role = "review"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "claude"
role = "orchestrate"
kind = "any"
size = "any"
model = "fable"
effort = "high"

[[route]]
route = "claude"
role = "baseline"
kind = "any"
size = "any"
model = "sonnet"
effort = "low"

[[route]]
route = "claude"
role = "implement"
kind = "any"
size = "any"
model = "sonnet"
effort = "high"

[[route]]
route = "claude"
role = "review"
kind = "code"
size = "any"
model = "opus"
effort = "high"

[[route]]
route = "claude"
role = "review"
kind = "docs"
size = "any"
model = "sonnet"
effort = "medium"

[[route]]
route = "claude"
role = "verify"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"

[[route]]
route = "claude"
role = "research"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"

[[route]]
route = "claude"
role = "audit"
kind = "any"
size = "any"
model = "fable"
effort = "high"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
```

## M12 — git log --since=2026-09-04

Command: `git log --since=2026-09-04 --format='%ci%x09%s' | head -80`

```
2026-09-26 14:14:45 -0500	snapshot
```

## M13 — factory-brief (read-only, plan docs/superpowers/plans/2026-09-05-evidence-store.md E1)

Command: `tools/factory/seat/factory-brief docs/superpowers/plans/2026-09-05-evidence-store.md E1`

Full output was pasted verbatim into the session log; length exceeded convenient inline duplication here. Summary of shape returned: a "## Global Constraints" section (build-only rules, commit/devShell rules, TDD rule, one-writer-per-tree, Nix style notes, no-secrets rule), an "## Assumptions" numbered list (1–8, covering Python version/tomllib, EVIDENCE_STORE env var, pre-switch state, E1/E3 integration, git diff exit codes, ~/factory/bin re-sync, no zoneinfo/env in sandbox, basket mount test exclusion), then the full "### E1 (code, M) — the evidence store: module, CLI, schema, checks" task block (dependsOn: none; Files to create/modify; Interfaces; 8 numbered Steps including full file contents for tests/evidence/test_evidence.py, pkgs/evidence/evidence.py, pkgs/evidence/SCHEMA.md, nixosModules/evidenceStore.nix, and flake.nix wiring snippets; touches list; acceptance list: evidence-unit, evidence-eval, host-core, lint; commit subject), followed by a "## WORKSPACE RULES" section (isolated worktree, scratch dir note, no sudo/nixos-rebuild/systemctl, git add before nix build, TDD practice, check command form, commit-only-via-devShell with trailers, never push, and the exact FACTORY-RESULT/FACTORY-CHECKS/FACTORY-COMMITS/FACTORY-NOTES reply format).

The command produced no errors; it read one plan file and printed to stdout as expected of the read-only exception.
