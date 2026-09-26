# Plan-writing comparison — the seat-behind-broker plan, four authors, one rubric (2026-09-05)

Judge: Fable (the orchestrator's model family — see "Judge's bias"). Evidence-only; no plan was executed. Spec under test: `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md`. Task the arms received: `### PW1pro` in `docs/superpowers/plans/2026-09-05-plan-writing-comparison.md` (identical text for the three arms bar the model name and output path).

| plan | author | file | lines / words |
|---|---|---|---|
| A | Fable, full session context (the orchestrator's plan on main) | `docs/superpowers/plans/2026-09-05-seat-behind-broker.md` | 124 / 2671 (110 / 2263 without the later-added SB3b fix-round section, which the arms never saw) |
| B | DeepSeek V4 Pro, effort high | `/home/dalhaka/factory/ws/pwp/PW1pro/docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-pro.md` | 1478 / 8673 |
| C | GLM 5.3, effort xhigh | `/home/dalhaka/factory/ws/pwg2/PW1glm/docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-glm.md` | 1939 / 13115 |
| D | Kimi K3, effort xhigh | `/home/dalhaka/factory/ws/pwk2/PW1kimi/docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-kimi.md` | 2213 / 12353 |

## Method

**Blindness.** Each arm's transcript was grepped for `2026-09-05-seat-behind-broker.md`. The dsh transcripts record reasoning and commands, not tool output, so the check is on what the model itself acknowledged seeing.

- **B (Pro): VOID.** Transcript line 244: "the grep revealed the content of `docs/superpowers/plans/2026-09-05-seat-behind-broker.md` (the comparison plan I must NOT open) at lines 39-40, 73, 76 — via grep." Those lines at the arm's base (`b945769`) are plan A's `seat-submit` interface (`[--jobs-dir DIR] [--no-start] {headless|web} … job.json`), the `seat-run.py` description (`--broker --bind-namespace <namespaceAddress> -- --no-open --port N … exit_code.txt … result.txt`) and the module option list (`services.seat-lane … webPortRange (default 43200-43299), harnessPackage`). Plan B then uses `seat-submit [--jobs-dir DIR] [--no-start] headless|web`, `job.json`, `stdout.txt`/`exit_code.txt`/`result.txt`, `nixosModules/seatLane.nix`, `services.seat-lane.{…,webPortRange,operatorUser,harnessPackage}` with `webPortRange` default `"43200-43299"` — a near-verbatim lift of the exposed lines. The model noticed the leak and argued it away ("I shouldn't overreact"). A partial read is a read; the arm is scored but void.
- **C (GLM): clean.** The second run (`pwg2`) never touched the file; its only mentions are the rule itself (lines 3, 76, 2016). The *first* run (`pwg`, killed by the reboot) did leak one line via an unfiltered grep (its line 210: "line 27 … appeared in the grep!") — that context was discarded with the process and does not carry into the scored run.
- **D (Kimi): clean.** One `grep -l` returned the *path* only (line 47: "I did not open it, only its path appeared in a filename listing"); the model then excluded it from later greps.

**Restart note.** GLM and Kimi were killed by the host reboot (switch #18) and restarted from scratch as `pwg2`/`pwk2`; their wall clocks and token counts below are for the second run only (the killed logs: GLM 1365 lines / 204 KB, Kimi 1765 lines / 179 KB of unbilled-here work). Pro ran once, uninterrupted.

**Rubric.** Ten criteria, 0–3 each, total /30, applied identically: 1 spec coverage; 2 correct facts (checked against the tree at the arms' base commits `b945769`/`5349582`, where `pkgs/seat` did not yet exist and `factory-task`'s launch block was at lines 131–143); 3 self-contained tasks; 4 TDD discipline; 5 dependency/wave design; 6 invariant awareness (brief §3); 7 operator steps; 8 economy; 9 house-format compliance (incl. `pkgs/evidence/tasks.py`'s `parse_plan`); 10 judgement calls (the spec's open point — how the web UI inside the namespace reaches the operator's browser — and reuse of the lane machinery).

## Scores

| criterion | A Fable | B Pro (VOID) | C GLM | D Kimi |
|---|---|---|---|---|
| 1 spec coverage | 2 | 2 | 3 | 3 |
| 2 correct facts | 2 | 1 | 2 | 2 |
| 3 self-contained tasks | 1 | 2 | 3 | 3 |
| 4 TDD discipline | 2 | 1 | 3 | 2 |
| 5 dependency / waves | 3 | 2 | 3 | 3 |
| 6 invariant awareness | 3 | 3 | 3 | 3 |
| 7 operator steps | 2 | 3 | 3 | 3 |
| 8 economy | 3 | 2 | 2 | 2 |
| 9 format compliance | 2 | 3 | 3 | 3 |
| 10 judgement calls | 1 | 1 | 3 | 2 |
| **total /30** | **21** | **20 (void)** | **28** | **26** |

`tasks.py parse_plan` parses all four: A → 6 tasks (SB3, SB2, SB1, SB4, SB5, SB3b); B → 6 (SB2, SB3, SB1, SB4, SB5, SB6); C → 7 (SB1–SB7); D → 6 (S1–S6). Every `acceptance` name is real (`docs/MAP.md` at base) or created by the plan itself.

## Per plan

### A — Fable (21)

Strengths. The only plan that names the *live* conflicts: "1' `SB2` — RT5 landed (both edit the wrapper and 70-dsh-openrouter.bats)", "1'' `SB1` — OG1b landed (both edit flake.nix)", and SB3's "DO NOT touch flake.nix" because two concurrent tasks were editing it. Invariants are explicit in Global Constraints ("never put a key in a Nix expression or a unit environment; `keyFile` must not be a store path (assert, as modelLane does)"). 2263 words for the whole design.

Defects.
- Spec §3's backup clause ("the backup exclusion list gains `/var/lib/seat/jobs/*/dsh-home/sessions`") has no task; `launch-today.sh` is not in the caller list the spec asks for.
- SB1's unit `Environment` omits `NODE_USE_ENV_PROXY=1` and the `NODE_OPTIONS=--require …/proxy-shim.cjs` preload that `nixosModules/modelLane.nix:226-234` records as the reason dsh honours `HTTPS_PROXY` at all, and `seat-eval` is told to assert "every `Environment` entry above" — so the eval check would not pin them either. The implementer is told to "read modelLane.nix and egressBroker.nix in full first; copy their shapes", which is where the fix would come from — but that is a "similar to" by another name.
- Not self-contained: interfaces are dense prose, no code blocks, no test bodies; SB5's runbook is a list of topics. The web-UI path is delegated: "egressBroker's chain already drops everything except the proxy port from the namespace side — read it and add the one rule the way it adds its own" — the existing chains are `input` and `forward`; host→namespace traffic is locally originated (`output` hook), so "the way it adds its own" is the wrong pattern.
- No mutation targets named (SB3b, written after the Opus gate, is the exception). Operator steps are one paragraph under Waves with no acceptance commands.
- Wrong facts: 1 (`factory-task` "lines ~97–115"; the launch block was 131–143 at base). The plan cites no commands (not required of it).
- Evidence the terseness cost something: SB3 was dispatched, REJECTED at gate (F1–F3 in `docs/reviews/2026-09-05-opus-review-sb1-SB3.md`) and re-planned as SB3b.

### B — DeepSeek V4 Pro, effort high (20, VOID)

Strengths. Best format fidelity of the arms (header block with Goal/Architecture/Tech Stack/Spec, Waves with a `groups` column, an explicit per-wave `flake.nix` editor list). Full bats and Python for SB2/SB3, a complete `nixosModules/seatLane.nix`, a polkit unit test, `factory-review` switched alongside `factory-task`, and the backup edit correctly "restating the module default so the define replaces, not drops, it". Operator section separated with switch/acceptance/rollback.

Defects (wrong-fact count 7).
- `_: { config, lib, pkgs, ... }:` as the module header, "Note the `_:` outer arg — statix rejects a `{ ... }:` header" — a misreading of the gotcha; a module that is a function returning a function does not evaluate.
- `seat-eval` asserts `sc.ExecStart == "${self.packages.${system}.seat-run}/bin/seat-run %i"` but no `packages.seat-run` is ever defined ("`packages` optional"); it also asserts `… != c.services.egress-broker.instances.openrouter.listenPort` on a fixture that has no `openrouter` instance.
- The web path: an accept inserted into `input-seat` as `iifname "veb-seat" tcp dport 43200-43299 ip saddr 10.100.4.1 accept` — packets arriving from the namespace carry saddr 10.100.4.2, so the rule never matches; host→namespace packets traverse `output`, not `input`. The VM then asserts `machine.fail("ip netns exec egress-seat curl -s http://10.100.4.2:43201/")` — from inside the namespace to its own bound address, which would succeed.
- `RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX"` on a unit whose wrapper must run `ip route show default` (netlink) — `--broker` would `die 6` on every real launch; only `seat-vm` would catch it.
- "`lane-eval`'s sibling at flake.nix:827" is the phase-3 `assertion-negative`; the lane's is at 1451.
- SB4's tests grep the *source* of `factory-task` (`[[ "$output" == *"seat-submit headless"* ]]`) rather than drive it; SB5's VM test is prose with fragments and a mid-step self-correction: "(adjust: the web job must actually START the unit; …)". No mutation targets.
- `factory-task` becomes single-path (`seat-submit` only) while the Operator section promises "the old non-broker path and `seat-submit` coexist until the file is gone" — landing SB4 before the switch breaks the factory that runs it.
- Test bug: `run_submit` sets `env["SEAT_STATE_DIR"]` in the child but the test reads `os.environ["SEAT_STATE_DIR"]` in the parent (KeyError).
- Commands were pasted per section only generically ("commands run: `read pkgs/dsh-openrouter/dsh-openrouter.sh`").

### C — GLM 5.3, effort xhigh (28)

Strengths. Complete coverage with an explicit spec→task map ("item 1 → SB3; item 2 → SB3; item 3 → SB2, SB5, SB6; …"). Thirty numbered facts, each with its command and the line it returned (fact 2: "`grep -n 'iifname \"veb-\${name}\"…' nixosModules/egressBroker.nix` → lines 182–190 … and why host→namespace (an **output**-hook packet, locally originated) needs its own chain"). The only arm to get the browser-reachability mechanism right: an `output`-hook chain `oifname "veb-seat" ct state established,related accept / … ip saddr <hostAddress> ip daddr <namespaceAddress> tcp dport <webPort> accept / oifname "veb-seat" drop`, and a VM probe that proves the saddr scoping (`curl --interface {primary}` must fail). Mutation targets named in every task ("(ii) Let `--broker` fall into the key block … → the mode-000 canary test dies 4"). The mode-000 canary actually launches through the fake and asserts the canary never reaches the wire. `factory-task` falls back automatically when `seat-submit` is absent (`command -v seat-submit`), satisfying spec §7's "tolerates both". SB6's red is a real check (`core-backup-wiring` throws until `backup.md` names the path). Operator section with numbered acceptance, rollback and the claim flip.

Defects (wrong-fact count 6, three of them one-line code errors).
- `nix build .#checks.x86_64.unit` (missing `-linux`).
- `i.inject.openrouter.test.valueFile` — Nix reads that as nested attrs `openrouter.test`; it needs `i.inject."openrouter.test"`.
- `!builtins.hasAttr "bodyPatch" i` — the option always exists (default `{}`), so this assertion can never pass; the intent (no body patch) needs `i.bodyPatch == { }`.
- `RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX"` with the `ip route` proof — same runtime break as B (Kimi caught it).
- Line offsets: `default.nix` runtimeInputs "73–79" (70–75), `lane-vm` "1480–1486" (1490–1494), `modelLane` in core modules "644" (655).
- Length: 13115 words; the facts list is partly restated inside the tasks.
- Judgement: drops the lane's `bodyPatch` (ZDR at the chokepoint, decision 2026-09-03) on the argument that "zero-data-retention is an OpenRouter account setting" — defensible from the spec's text, but it leaves brief §3 invariant 5 to an account toggle for the seat; plan A keeps the patch.

### D — Kimi K3, effort xhigh (26)

Strengths. Closest to the house reference's shape (inventory, **Decisions D1–D9**, Global Constraints, Waves, Operator, Tasks, appendix). The Decisions carry real reasoning: D4 on why the polkit rule needs `stop` ("the lane needs only start because its `oneshot` unit blocks `systemctl start` for the job's whole life"), D5 on why `--broker` must refuse outside the namespace ("a mis-launch outside the netns would otherwise send the placeholder to OpenRouter as if it were a key, bypassing allowlist, deny paths and audit"). The only arm to add `AF_NETLINK` to `RestrictAddressFamilies` "the wrapper's --broker check reads the default route via netlink" and to put `iproute2` on the unit's `path`. Red-before-green is reasoned, not ritual: S1 registers the check first "so the failure is the *tests*, not a missing attrset"; S3 explains why the negative check must also be red first. Complete code everywhere, including the VM test, `host-core` asserts and the polkit `.mjs` cases. Fewest wrong facts on the tree; line references verified accurate at base.

Defects (wrong-fact count 2).
- D6 `exposePort` renders its accept into `forward-<name>` — host→namespace traffic never traverses the forward hook, so the rule is dead; the UI is reachable anyway (nothing drops it), which means the VM step "the forward chain accepts ONLY 8480 (a neighbour port fails)" passes vacuously and the claimed mutation "removing `exposePort` fails step 5" is false. Spec §5's "No other inbound path exists" is not enforced.
- S6 sets `services.proton-backup.exclude = [ "/var/lib/seat/jobs/*/dsh-home/sessions" ];` in `hosts/core/proton-backup.nix` — a definition replaces the module default, dropping `.pytest_cache`/`.ruff_cache`/`~/.cache` (B restated them; C edited the default).
- Mutation targets are declared wholesale ("exactly each task's `touches` line") rather than per test.
- `FACTORY_SEAT` defaults to `seat`, so a pre-switch host running `factory-task` fails on a missing `seat-submit` unless `FACTORY_SEAT=direct` is set — an escape hatch, not the automatic tolerance spec §7 asks for.
- Length: 12353 words, with an appendix table repeating the inventory.

## Usage and cost

| arm | `usage:` (input / output / cacheRead tokens; wall s) | cost at `docs/ledger/openrouter-prices.csv` | transcript |
|---|---|---|---|
| B Pro | 686,825 / 105,547 / 6,083,840; 1234 s (20.6 min) | $0.55×0.687 + $2.19×0.106 = **$0.61** (sheet row 2026-09-04; `cache_read_per_1m` is 0.0 on the sheet — if cache reads were billed at the input rate the run would be +$3.35) | 3084 lines / 268 KB |
| C GLM | 169,685 / 109,518 / 8,873,408; 2781 s (46.4 min, second run only) | **unpriced** (`z-ai/glm-5.3` not on the sheet) | 2023 lines / 258 KB (+ killed run 1365 / 204 KB) |
| D Kimi | 273,955 / 74,510 / 5,266,432; 1493 s (24.9 min, second run only) | **unpriced** (`moonshotai/kimi-k3` not on the sheet) | 1082 lines / 131 KB (+ killed run 1765 / 179 KB) |
| A Fable | not metered (interactive orchestrator session) | — | — |

## Conclusion

- **Ranking on this rubric:** GLM 28 > Kimi 26 > Fable 21 > Pro 20 (void). The two clean arms beat the orchestrator's plan on self-containment, TDD and operator steps; the orchestrator's plan wins only on economy and on session-aware wave hazards (RT5/OG1b) that a blind arm cannot see.
- **Dispatchable as-is?** C (GLM): yes with a four-line errata handed to the implementer (`-linux`; quote `"openrouter.test"`; `i.bodyPatch == { }`; add `AF_NETLINK`) — three of the four would surface in the task's own green step, the fourth in `seat-vm`. D (Kimi): yes with two errata (move the `exposePort` accept to an `output`-hook chain with a trailing drop, per C's design; restate the backup exclude defaults). B: no (void, and the module header and single-path `factory-task` would fail at first eval / first pre-switch run). A: was dispatched; SB3 needed a fix round.
- **A `plan` row for `docs/ledger/routing.toml`** could read `route = "openrouter"`, `role = "plan"`, `kind = "docs"`, `size = "any"`, `model = "z-ai/glm-5.3"`, `effort = "xhigh"` — but not on this evidence. n = 1 spec × 1 sample per model, a two-point gap between C and D that one judge's criterion-8/10 calls could flip, GLM at nearly twice Kimi's wall clock, and neither model priced. Before a row is written: at least **n = 3 specs, 2 samples each, per model** (≈12 plans), blind, scored by two judges of different families with the rubric above, with the price sheet extended to both models; the Pro arm re-run with a grep guard (exclude the compared plan's path from the workspace, not from the instructions). What this run does support: a plan written by GLM 5.3 or Kimi K3 at xhigh from a spec plus a read list is *reviewable* material — complete enough that the reviewer's findings are code-level (attr paths, hooks), not "fill in the design".
- **Two design facts every future plan for this spec should carry**, found here: host→namespace traffic to the web UI is `output`-hook, not `input`/`forward` (C got it; A, B, D did not); and a wrapper that runs `ip route` inside a unit with `RestrictAddressFamilies` needs `AF_NETLINK` (D got it; B, C did not; A does not restrict).

## Judge's bias

Plan A was written by the judge's own model family, with full session context, and the judge has read the spec, the board and the gate reviews of A's SB3. That is a declared conflict: I could be lenient to A's terseness ("the implementer reads modelLane.nix") or harsh to compensate. I scored A's omissions as omissions (backup exclusion, proxy shim, unresolved web path) because a blind implementer would hit them; A finished below both clean arms. The arms' code was judged by reading, not by running — a second judge should run the three Nix fragments flagged above (B's module header, C's attribute path and `hasAttr`, D's `exclude` definition) to confirm the wrong-fact counts. The Pro void is a judgement on the rule as written ("a read of that file voids your arm"), applied to a partial exposure the model itself reported; a reviewer who reads "open" as "the read tool" could reinstate B at 20/30 — still last.
