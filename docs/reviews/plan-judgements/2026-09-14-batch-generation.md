---
plan: /home/dalhaka/factory/batch/2026-09-11/drafts-r2/2026-09-11-generation.md
spec: docs/concepts/2026-09-09a-redesign-charter.md
author: fable-workflow-revision
effort: high
words: 14530
tasks: 12
judges: [sonnet, sonnet, opus]
judges_dropped: []
scores: [3, 1, 2, 3, 2, 2, 2, 3, 3, 3, 3, 2, 2, 3]
total: 34
self_score: null
threshold: 34
decision: revise
revision: 0
---

## Errata

| # | Criterion | Task | Finding | Fix |
|---|---|---|---|---|
| 1 | 2 | Assumptions (Assumption 13) | `... json \| grep -c '"GN'` claimed to print 0, re-measured 2026-09-14; re-run at HEAD 662e87f returns 1 — the hit is the subsystems manifest's own `"prefix": "GN"` field, not a landed GN task key. | Tighten the grep to `grep -c '"key": "GN'` (returns 0) or note the manifest-field false positive explicitly. |
| 2 | 2 | Waves ("Edges the graph cannot resolve today") | Plan states `check --draft` at 662e87f prints two unknown-key lines. Re-run prints eight: the two claimed plus six unacknowledged `acceptance <check> not in docs/MAP.md` lines (GN10/GN11 core-media-wiring; GN12 comfy-worlds-unit, comfy-worlds-eval, media-fetch-unit, comfy-upstream-probe-unit). Also frames `--draft` as future work when it already works today. | Paste the actual full eight-line output; explain the six MAP.md lines as an expected pre-landing artifact, or confirm P1's landed state directly. |
| 3 | 3 | GN8 | Step 3's cross-repo proof runs a python check "in ~/nixos-agent-env" from inside the isolated media-repo task workspace, whose own WORKSPACE RULES forbid exactly that — no access mechanism named. | Name the exact access path (read-only mount, or a copy of the relevant repo) or replace the cross-repo shell-out with an inline literal of `streams.KINDS["engagement"]["fields"]`. |
| 4 | 5 | GN5 | Interface term 1 (`load_rules` raises `ValueError` when `[mutate]` missing) has a test but none of the six named mutants target it — a mutant returning `{}` instead of raising survives every listed check. | Add mutant M7 table-optional (`load_rules` returns `{}` instead of raising) and show it fails `test_missing_table_refused`. |
| 5 | 5 | GN8 | `flush()` "on SIGTERM and every 3600 s" has no mutant on the periodic/signal path — a build that never schedules a flush passes every named check. | Name the scheduling mechanism explicitly (daemon thread + 3600s timer, or `signal.signal(SIGTERM, ...)`) and add mutant "periodic-flush-never-scheduled" with its failing test. |
| 6 | 2 | Assumption 13 (dup) | Same false-zero grep claim re-measured at HEAD 4068f86, still returns 1 via the prefix-field match. | Use `grep -o '"key": "GN[^"]*"'` (prints nothing) or note the single-line-JSON caveat before pasting the number. |
| 7 | 5 | GN1, GN2 | `read_chunks`/`enqueue` both rely on sdxl.json trimmed to one KSampler node — a mutant reading/writing the last (or only-first) node survives every named test in both tasks. | Add a second KSampler node with a different seed to the fixture, plus tests asserting the correct node is read (GN1) and both nodes are written (GN2), matching GN4's two-CLIPTextEncode technique. |
| 8 | 6 | GN7 | `_open`'s error contract is untested for SSL_CERT_FILE naming a missing/unreadable path — undefined behavior. | Add `test_open_refuses_missing_ca_file` and state the exact error surfaced. |
| 9 | 6 | GN8 | `0..86400` dwell-seconds range only exercised at 10**9 (M3); no test at the boundary itself. | Add boundary tests: 0 and 86400 accepted, -1 and 86401 rejected. |
| 10 | 7 | GN11 | Base precondition is the seat's own self-report, which the charter says must never be the trusted signal; the plan doesn't say the commit-time re-assertion (Interfaces term 1) is what actually gates. | State explicitly that the commit-time git merge-base check is the enforced guard, or move the precondition into a scripted pre-dispatch check. |
| 11 | 13 | whole plan | `check --draft` prints 8 lines; plan's "Edges" section names only 2, leaving 6 `acceptance ... not in docs/MAP.md` lines unaccounted for. | Extend the "Edges" paragraph to name all six MAP.md-not-found lines and explain they resolve once GN10/GN12 land and docs/MAP.md regenerates. |
| 12 | 3 | GN3, GN10, GN11 | Several interfaces point at another file's shape ("as test_feed_placeholder.py:36-40 did", "core-gaming-wiring's pattern") rather than inlining it. | Inline the referenced lines (thread-start helper; lock-node equality assertion shape) directly in the task body. |
| 13 | 6 | GN8 | The feed unit is `ProtectSystem = "strict"` with `ReadWritePaths` excluding `/var/lib/evidence` (`~/flakes/media/nixosModules/comfyui-worlds.nix:81-89`), so the default `--engagement-path` can never be written on core; term 2's catch also misses OSError(EROFS). | Add `/var/lib/evidence/ledger` to the unit's ReadWritePaths (via GN8 or GN10); widen term 2's catch to OSError; add a drill step reading the ledger row. |
| 14 | 2 | Waves | Re-run at 662e87f prints eight lines, not two; six unmentioned MAP.md refusals from GN10-GN12's own new checks. | Paste the eight-line output and say when each clears; note plain `check` (Step-3 form) doesn't apply the draft acceptance rule the landed-tree claim relies on. |
| 15 | 2 | Assumptions (13) | Dup of #1/#6, third independent re-run confirming 1, not 0. | Same fix: correct grep pattern or note the manifest-field cause explicitly. |
| 16 | 2 | GN9 | Runbook claimed "eleven `## ` sections"; `grep -c '^## '` is actually 12, so the green count after GN9's two additions is 14, not 13. | Say twelve; set the green expectation to fourteen. |
| 17 | 8 | Waves | Claim "no GN group because the draft is not under the plans glob" is falsified — with the draft under the glob, waves still shows no GN group, because GN1-GN9 are `repo: media` and GN10-GN12 are `blocked`. | Replace the reason: this repo's waves only ever show GN10-GN12, once GN9 lands on media main and EV10 lands; add the media-repo waves run. |
| 18 | 5 | GN6 | Term 1's `inputs.sampler_name` substitution has no test and no mutant — dropping it entirely survives every named check. | Add `test_variant_sampler_lands_in_every_ksampler` and mutant M7 sampler-ignored. |
| 19 | 5 | GN8 | `flush()` on SIGTERM/3600s (dup of #5) — no test starts the server in a subprocess to exercise the signal path. | Add a subprocess SIGTERM test plus mutant M7 no-sigterm; name the scheduling mechanism in term 2. |
| 20 | 5 | GN1 | Term 5 ("writes nothing outside feed.sqlite; PNGs read-only") has no assertion and no mutant. | Add `test_rebuild_leaves_the_output_dir_byte_identical` and mutant M7 png-touched. |
| 21 | 6 | GN2 | No arm named for ComfyUI unreachable; URLError/timeout behavior on `submit`/`poll` unspecified, including whether `run_once` continues past a failed job. | Extend terms 3-5 to define the failure state and continuation behavior; add `test_submit_unreachable_leaves_job_queued` and mutant M7 error-swallowed. |
| 22 | 7 | GN3 | Zero-outbound rule misses `<meta http-equiv="refresh" content="0;url=...">` and `<button formaction="...">` — both reach the network without tripping the three-name check. | State rule (iii) as a value-based rule (any value with a scheme before the first `/`, or `//`-prefixed) and refuse `meta http-equiv` outright; name both as mutants M3d/M3e. |
| 23 | 1 | Assumption 20 / GN10 | Plan resolves a live conflict between decisions 14c/16b (Caddy fronts the worlds) and Assumption 9 (verified: `lan.enable = false` renders no Caddy) inside an assumption rather than a question, while a question slot went to a matter it also self-answers. | Promote to question 3 with the same bounds already written into Assumption 20, or cite charter :186-188 as explicitly superseding 14c/16b. |
| 24 | 14 | Operator questions | Questions numbered 1, 2, 4 (no 3); preamble's "fourth question... is Assumption 20" doesn't match the header's "(Q4, Q2, Q1)" ordering. | Renumber the retained questions 1-3; name the demoted one once by its fill number and what it became. |
| 25 | 3 | GN12 | `media/checks.nix` specified only as "the 21 check attrs, moved verbatim" with no attribute list, no `${self}`-path count, no `mkHarness`/`mkNegative` signatures, no `lintTools` list. | Paste the attribute-name list, the `${self}` occurrence count, and both helper signatures into the section body. |
| 26 | 2 | Global Constraints (G5) | "`lint` asserts it is current (`flake.nix:1081-1086`)" is wrong — that range is host-core's helm-control block; the real MAP-currency assertion is at `flake.nix:1388-1391`. | Correct the anchor in "Where they bind here" and in GN12 step 3. |

## Judge reasons

### Judge 1 (sonnet) — scores [3,1,2,3,2,2,2,3,3,3,3,2,2,3]

1. Charter-to-task map traces every charter §2/§5/§6 Generation item to a GN key or an explicit "Not in this plan" entry; spot-checked Phase-5 local weights lands correctly in the out-list.
2. Two re-run commands contradicted the plan's own pasted facts: Assumption 13's grep and the Waves section's `check --draft` claim (two lines vs. actual eight), and `check --draft` is misdescribed as a not-yet-landed capability.
3. Most sections are dense enough for a blind implementer, but GN8 Step 3 requires a cross-repo read its own workspace rules forbid, with no mechanism named.
4. Every task shows red output with cause explained, then scoped green tails; VM-cost exceptions (GN3, GN9) are explicitly justified.
5. Reviewer-lens mutants mostly land on the three sampled tasks, but GN5's missing-table refusal and GN8's periodic flush both surface as untested/unmutated.
6. Field-level contracts are exhaustive almost everywhere, but GN8 never states its flush-scheduling mechanism and its cross-repo step assumes forbidden filesystem access.
7. Boundaries read as rules throughout; the one literal list (six brokered hosts) is an intentional fixed allowlist, proven by a re-derivable pipeline.
8. Waves are derived and cited against live-tree tool output, reproduced exactly on re-run; touches are explicit paths; the three EV6×HH conflicts are named and sequenced.
9. No task names /var/lib/secrets; every privileged command sits inside "## Operator"; invariants 3 and 6 are matched by GN7/GN10 and GN8 respectively.
10. The drill is a numbered two-switch sequence with per-step acceptance and explicit rollback including the subtree-merge revert.
11. Anticipation names a concrete risk per task with the artifact that resolves it, tied to specific claims/questions.
12. Twelve substantial tasks each restate context (unavoidable given isolated-clone seat briefing); length tracks scope, not clearly past a 3x bound.
13. `check --draft` on the live tree does not reproduce as the plan states (eight lines vs. two, and the flag is misdescribed as unavailable).
14. Three bounded operator questions each carry a recommendation and per-answer deltas; the surviving list is numbered 1, 2, 4 — a stale "3" (Caddy's LAN face) was demoted to Assumption 20 without renumbering, a cosmetic defect.

### Judge 2 (sonnet) — same score vector, independent reasons

1. Charter §6 increment 3's five GN items all map; the on-demand-units-AND-Caddy item ships only half (no Caddy under `lan.enable=false`) while decisions 14c/16b are still cited as relied on.
2. ~30 anchors re-run and exact; four wrong facts found (Assumption 13's grep, `check --draft`'s claimed two-line output, GN9's "eleven" `## ` sections actually 12, and the "no GN group" waves claim being falsified for a different reason than stated) plus one inherited-wrong anchor (G5's flake.nix line range).
3. `factory-brief` output is generally self-contained with exact schemas/signatures, but real inventions remain unresolved (GN8's flush scheduler, GN2's unreachable-ComfyUI behavior, GN1's row type) and GN12 is the weakest section, with no attribute list.
4. Every task has an exact red command and expected red text, with GN3's VM step explicitly reasoned as not-run-red rather than silently skipped.
5. Mutant tables are unusually dense, but survivors remain on load-bearing terms: GN6's sampler substitution, GN8's SIGTERM/3600s flush, GN1's read-only-PNG invariant, GN2's ordering/return-count.
6. Interfaces are strong on enum arms and exit codes, but GN2 names no arm for ComfyUI unreachable and GN8 catches the wrong exception class for its actual sandboxed failure mode (EROFS).
7. The zero-outbound rule is genuine but incomplete: meta-refresh and formaction both reach the network outside the three checked attribute names.
8. Touches are explicit paths; conflicts and waves outputs reproduce byte for byte; but the "landed, stage 1 is the first group" derivation is hand-made and does not hold as stated.
9. Invariants are named where they bind and tightened rather than widened (GN7's broker refusal, GN10's six-host allow list, GN8's key-set-only counts); no sudo/systemctl outside the Operator section.
10. Twelve operator steps each have a command and acceptance, a closure diff, and rollback including subtree-merge revert; nothing in the drill actually reads an engagement row, so GN8's declared failure mode (dropping counts quietly) is unexercised by the composed drill.
11. Every applicable §4 trigger has its artifact; no hook/deny-rule table is triggered.
12. 14,530 words for twelve tasks; task bodies earn their length but Global Constraints repeats ~1,400 words verbatim with irrelevant matter, and the LAN-off decision is restated five times.
13. `parse_plan` reads all twelve tasks correctly and every check name is real, but `check` is not empty in either form — the live tree prints eight lines the plan doesn't disclose.
14. Three bounded questions with recommendations and per-answer task deltas; numbered 1, 2, 4 with no 3, and the plan's largest call (no Caddy against 14c/16b) was demoted out of the question list on its own authority.

### Judge 3 (opus) — same score vector, independent reasons

1. Spec coverage: charter §6 increment 3's five GN items map; Phase 5 is an explicit out. But the on-demand-units-plus-Caddy item ships only half (no Caddy at all under `lan.enable=false`) against two decisions of record the plan itself lists as relied on.
2. ~30 anchors re-run and exact; four wrong: the grep-zero claim, the two-vs-eight `check --draft` lines, GN9's eleven-vs-twelve `## ` sections, and the falsified "no GN group" waves reasoning; a fifth wrong anchor (G5's flake.nix line range) is inherited verbatim from another plan.
3. `factory-brief` returns full schemas and exact literals for most tasks; real inventions remain (GN8's flush scheduler and its evidence-import legality, GN2's unreachable-ComfyUI behavior, GN1's `newest` row type). GN12 is the weakest: no attribute list, no helper signatures.
4. TDD discipline strong across all twelve tasks; GN3's VM step is explicitly declared not-run-red with a standing reasoning rather than pretended.
5. Mutant density is high, but load-bearing survivors remain: GN6's sampler substitution, GN8's SIGTERM/3600s flush, GN1's read-only-PNG invariant, GN2's ordering/return-count untested.
6. Interfaces are strong on enums and exit codes; two real holes — GN2 has no unreachable-ComfyUI arm, and GN8 catches the wrong exception class for the sandbox's actual EROFS failure.
7. Rules are genuine (zero-outbound spellings named, "every" node language used correctly) but rule (iii) misses meta-refresh and formaction spellings.
8. Touches are explicit paths with no globs; conflicts were re-run and reproduced byte for byte; but the waves-derivation claim about the plans-glob is hand-made and wrong for a different reason than stated.
9. Invariants named where they bind and correctly tightened (GN7's broker refusal, GN10's six-host allow list with order/length equality, GN8's key-set assertion); no sudo/systemctl outside Operator.
10. Twelve numbered operator steps with acceptance, closure diff naming expected packages, rollback including subtree-merge revert; but nothing in the drill exercises GN8's declared failure mode (dropping engagement counts quietly).
11. Every applicable §4 trigger has an artifact — dispatch lines, the landing act, the prepared relaunch, the switch delta, the claim closure, pre-asked questions, and a ten-item Anticipation list; none triggered here.
12. 14,530 words for twelve tasks; task bodies earn their length, but Global Constraints repeats ~1,400 words verbatim with unrelated matter (EV/IS/PR/FA/KN references), and the LAN-off decision is restated five times across sections.
13. Format and graph parse correctly and every check name resolves, but `check` is not empty in either form — the scratch-copy form shows an unknown-key line and `check --draft` on the live tree shows eight lines, none disclosed.
14. Three bounded questions each with lettered options, a recommendation, and per-answer task deltas; numbered 1, 2, 4 with no 3, and the plan's single largest call (shipping no Caddy against 14c/16b, both cited as relied on) was demoted out of the question list on the plan's own authority.
