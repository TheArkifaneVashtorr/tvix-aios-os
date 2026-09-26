# Decision 2026-09-21 — session 31 ran on Fable 5.1 in the desktop productivity session; the driver goes back to Opus

**Status:** adopted by the orchestrator on the operator's word at the close of
session 31 (2026-09-21, ~16:15 CDT): "ok we are exiting this phase, I will be
switching back to opus for driver. Please update any documentation needed."
Append-only; supersede with a dated entry if it changes. Extends
`2026-09-17-session-effort-medium.md` (session 29: Fable 5.1, medium) and the
session-30 close entry in `docs/board/log-2026-09.md` (Fable 5.1, ultracode on
for two pre-planning runs then off, effort not set by word). Session 31 ran
beside session 30 on the same day: it began 14:07 CDT in the desktop app
(the `/productivity:start` session) while session 30 was still committing on
main (`1479dd2` … `45259a3`, 14:19–14:22 CDT).

## What changes

| axis | session 31 (this file's session) | session 32 onward |
|---|---|---|
| main seat driver (the Claude Code context window) | Fable 5.1 on the Anthropic login, desktop app; the ultracode reminder read ON at the start and OFF from the `workflow-authoring` load onward; effort not set by word | **Opus**, effort as the operator states it at the next session start; the session stamp is this file until a newer one |
| reads, greps, probes, digests | Sonnet `Agent` calls returning digests (nine agents this session, the largest 168k tokens); Fable kept decisions, the board, the specs and the commits | unchanged |
| questions to the operator | every question through `superpowers:brainstorming` and `AskUserQuestion` with a "(Recommended)" default, per the operator's standing rule of this session; 10 asked, 9 took the recommended option, 1 did not (the search loop's number) | unchanged; the `ledger/operator` stream of the collection spec will record this instead of a hand count |
| planning runs | three `plan` Workflow runs: `wf_4196362e-f44` (operator-and-collection) in flight, packet phase complete, Fable drafter running since 15:46 CDT; portable-bootstrap and search-loop queued behind it on the operator's word | the in-flight run dies with this session; resume with `Workflow({scriptPath: "<session dir>/workflows/scripts/plan-wf_4196362e-f44.js", resumeFromRunId: "wf_4196362e-f44"})` — the five packet results are cached, the draft re-runs; the two queued runs launch sequentially after it, args `{spec, out, name, date, scratch}` |
| implementation keys | none launched; no seat ran; no task landed; the held state of PLAN-FA/PL/SA unchanged (held since 2026-09-16 on the operator's word) | unchanged |
| the operator as a variable | first data points recorded by hand: switch latency 3 h 22 m (drift fail 16:19Z → ok 19:41Z), PLAN-* held 5 days, Phase 10 awaiting the word since 13:03 CDT | measured by the collection spec's tasks once they land |

Nothing else moves: the factory role table (`docs/ledger/routing.toml`, GLM2b),
the seat driver's own effort axis, and the review ladder are untouched.

## Baseline at the moment of the decision

Live generation 79 (`45259a3`, the operator's switch at ~14:45 CDT; `nix store
diff-closures` empty, the switch replaced comfy-author, comfy-run, comfy-feed
and restarted `comfy-feed.service`), HEAD `e5975c7` docs-only ahead (three
specs). Helm: drift `fail` until its next tick, flake-check `warn` since
11:31Z, no check run recorded at HEAD. Queue: ready GN28, KN14, PLAN-FA/PL/SA;
FA24 rejected, fix round owed; 30 escalations at rung 2; no seat running.
Fable spend this session: unmeasured (`ledger/otel-claude` is declared and
absent), which the collection spec names.

## What the session produced

- `docs/superpowers/specs/2026-09-21-operator-and-collection-design.md` (`1df1881`): six Evidence tasks — a `held` state with a since-date, an operator-latency report from helm-status drift rows, a text-free `ledger/operator` stream via a PostToolUse hook, usage rows attributed to (run, key) by header or window, gate rows naming reviewer model and rung, task rows always carrying effort, size and area.
- `docs/superpowers/specs/2026-09-21-portable-bootstrap-design.md` (`1a3b380`): tvix-aios and the portable OS are one product; a second account `wayfarer` runs the operator's evaluated user units re-rooted user-side from a signed source tarball on Proton Drive; new subsystem Portable (PO), gate opus. The fork's workspace lacks castore, store, build, nar-bridge and nix-daemon.
- `docs/superpowers/specs/2026-09-21-search-loop-design.md` (`e5975c7`): the number is one CivitAI Community Challenge entry (the operator's choice over judge agreement); no image challenge was open on 2026-09-21; an embedding judge retrained nightly on the votes, a night that never halts on the author, the SFW world sharing the checkpoint, a blind morning of twenty.
- The seat verdict from the store: keep glm-5.3 high at rung 1 (18/21 approved, 1 seat-side rejection of 3, n = 34 runs); the finding was the six collection gaps, not the model.
- The productivity plugin's `TASKS.md`, `dashboard.html` and `memory/` at the repo root, listed in `.git/info/exclude`; the project `CLAUDE.md` untouched.

## How an audit measures it

The same table as the prior decisions, over session 32's first day on Opus against session 31: specs written and their plan-run scores, tasks landed and first-pass gate rate, fix rounds, Workflow launches, questions asked and the share that took the recommended option (from `ledger/operator` once it lands, by hand until then), and the operator's decision latency per owed word.

## Reading at close (appended 2026-09-21 ~17:00 CDT)

The planning-runs row above is superseded: `wf_4196362e-f44` finished after the close — dispatch, 40/42, first draft, no revision; the plan (OC1–OC10) and the concept `2026-09-21c` landed with the session-31 correction commit; no resume needed. The two queued runs are the next session's, sequential, behind its own lora-cards run.
