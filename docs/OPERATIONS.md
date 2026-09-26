# Operations board — nixos-agent-env

Facts are not written here. At the start of a session run
`evidence bundle --markdown` (live generation and revision, repo heads, which
checks cover HEAD and the live system, Helm verdicts and since when, open gaps
from the claims file docs/ledger/claims.toml). This file carries the plan: what
is queued, what is parked, what the operator owns. It is replaced every turn,
never appended.

## START HERE (2026-09-14 18:40 CDT, session 23 — THE REVISION ROUND IS COMPLETE: ALL NINE BATCH PLANS ARE DISPATCHABLE. Sequential run `wf_7758dead-e5e` (62 agents, no errors, 14:16–18:30, after the morning's parallel run was cut by the 5-hour limit): seat-harness 36 (morning run), helm 38, generation 34→38 (second round), isolation 36, knowledge 38, platform 41, evidence 38, factory 34→38 (second round), defects 38 — all `dispatch`, no judge dropped; judgements `docs/reviews/plan-judgements/2026-09-14-batch-<key>[-r2].md`, all committed. The revised drafts: `~/factory/batch/2026-09-11/drafts-r2/2026-09-11-<key>.md` with `<key>.errata.md` (one row per erratum: applied / refuted with the command / folded) — NOT in the plans directory: the operator lands them. SET-CHECK of the nine together in a `cp -a` scratch tree: `tasks.py check` EXIT 0 with zero lines (the per-draft `acceptance … not in docs/MAP.md` and sibling-key lines were artefacts of checking one draft alone), no key collision against 327 live keys; `drafts-r2/LANDING.md` carries the outputs, the edges and the recipe.
LANDING ORDER (forced by cross-plan `dependsOn`, acyclic): evidence → factory → platform → generation → helm → knowledge → isolation → seat-harness → defects (edges KN16→PL5, GN8/GN11→EV10/EV15, HM8→EV15, IS13→HM3, SA1/SA7→IS10, DF1→IS10). Each plan: Write tool into `docs/superpowers/plans/2026-09-11-<key>.md` (names per `docs/ledger/subsystems.toml`; the guard refuses `cp` there), `tasks.py check`, `write-board`, commit `<area>: … (test: …)`. PREREQUISITES (operator): HH5–HH10 have no withdrawn rows in `docs/ledger/task-status.toml` though decision 9b (`docs/decisions/2026-09-09-redesign-answers.md:22`) supersedes them; EV6 × HH6/HH8/HH9 collide on flake.nix (live, pre-existing); EV3 then EV4 gate DF1/DF3/DF4/DF6/FA19/EV18.
READ TOGETHER BEFORE LANDING: GN8 was redesigned in generation's second round — the feed no longer writes the evidence store; it POSTs HM8's body to `http://127.0.0.1:7710/v1/engage` (loopback-only, drops on error) because the evidence draft's EV14 makes keyed `replace_stream` the stream's only verb and the helm draft assigns the feed-side POST to GN; helm's judgement flags HM5's `seat-submit` call missing `--dsh-home/--model/--effort` (exit 2 before a unit starts) and two stale counts in HM1/U4 — corrections at commit time. 27 operator questions remain (≤ 3 a plan, each with a recommendation); 55 were folded into numbered Assumptions with veto surfaces.
DONE TODAY: measurement pass (15 agents) → decision brief `~/factory/batch/2026-09-11/brief-2026-09-14.md` → the parallel run (cut: 51 agents, 26 dead) → the sequential run; the board trimmed to this paragraph with the derived block below; the bug-workflow packet committed with a drift note; leftovers archived by the operator (`tree/`, `AGENTS.md`, `.codex/`, `.msg-ui1.txt` → `~/factory/archive/`; `revise/` removed); chips: the stale ritual.log replay LANDED (`3d66efa`), the `batch-plan.js` typing still on its worktree (`claude/determined-gauss-687477`). HANDOFF: `~/factory/batch/2026-09-11/HANDOFF-2026-09-14.md`.
HELD: `flake-check` FAIL at HEAD — `seat-vm` (`tests/integration/seat-vm.nix:170` `maxUnits = 2` vs `waveJobs` default 8; IS10 fixes it); 13 rung-2 escalations await `claude/review` (FIX5d HH1b HH1c HH4b IS1b IS1c IS3b KN1b PR1b PR1c PR1d W6b W6c); the Claude spend ledgers were never ingested (no measured headroom; the 5-hour window is the binding limit — nine parallel Fable revisers burned it in 45 min; sequential is the rule); 486 stale run logs, no reaper; `batch-plan.js` still carries the fill defects until the chip lands.
NEXT (operator's word): land the nine in the order above, or name which first; then the rung-2 escalations and switch #30 planning.)

<!-- tasks:begin -->
**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** EV10 EV11 EV12 EV14 EV16 EV17 EV3 FA10 FA13 FA14 FA20 FIX5 FIX5b FIX5c HH5 HH6 IS5 PL1 SPEC-FA SPEC-PL SPEC-SA (2026-09-08-helm-home-1.md 2026-09-09-bugs.md 2026-09-09-program.md 2026-09-11-evidence.md 2026-09-11-factory.md 2026-09-11-platform.md)
Area: isolation — ready: IS5 · blocked: FA24 IS5b · running: none · rejected: none
Area: platform — ready: EV16 · blocked: GN12 HH8 HH9 PL3 PL4 PL5 · running: none · rejected: none
Area: helm — ready: HH5 HH6 · blocked: HH10 HH7 · running: none · rejected: none
Area: seat — ready: FIX5 FIX5b FIX5c · blocked: PL2 · running: none · rejected: none
Area: factory — ready: FA13 FA14 FA20 SPEC-FA SPEC-PL SPEC-SA · blocked: FA12 FA15 FA16 FA17 FA18 FA19 FA21 FA23 · running: none · rejected: none
Area: evidence — ready: EV10 EV11 EV12 EV14 EV17 EV3 PL1 · blocked: EV13 EV15 EV18 EV4 EV6 PL6 PLAN-FA PLAN-PL PLAN-SA · running: none · rejected: none
Area: generation — none open
Area: knowledge — ready: FA10 · blocked: FA22 PL7 · running: none · rejected: none
Area: program — none open
<!-- tasks:end -->

## Log

Every turn appends its block to `docs/board/log-2026-09.md` (newest first) and
rewrites START HERE above. A month rolls to a new log file.