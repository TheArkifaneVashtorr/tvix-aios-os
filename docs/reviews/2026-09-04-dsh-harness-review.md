# dsh + dark factory: 24-hour review

**Window:** 2026-09-03 17:13 → 2026-09-04 10:03 CDT. **Corpus:** 29 dsh transcripts (7 interactive, 22 subagents), `scratchpad/metrics.md`, plus first-hand re-verification at `cf21507`.

**Under review:** *dsh* — the DeepSeek Harness, a coding-agent command-line tool — run through OpenRouter by the seat at `pkgs/dsh-openrouter`; and `~/flakes/dsh-harness/factory/dark-factory.js` ("the factory"), which drives dsh's built-in **workflow tool**, the thing that spawns several models at once and collects their answers.

Eighteen findings each went to three independent adversarial checks (evidence, value, feasibility). Five survived; the thirteen that did not are in the appendix, one line each.

---

## 1. Verdict

The models were not the problem. Ten agents across four vendors turned a plan into a working NixOS control surface overnight for an estimated **$23.73** and **19.07M tokens**, and the work holds: at `cf21507` I re-ran the checks and they pass. Every failure was in the wiring around the models. One 460-minute run threw its whole return value away over a missing field; three review verdicts — including one `rework` — were produced, paid for and discarded; fourteen sessions each rediscovered the same read-only cache defect; and the factory's documented plan→build handoff is broken at HEAD in a way that would dispatch every implementer with an empty task spec. Fix the plumbing before adding capability.

---

## 2. What happened

**17:13–18:38** Five interactive sessions; two produced nothing (aborted at `3a312871 +43:56`, `893bf6de +03:42`), and one flipped the seat's *and* the batch lane's default model when asked only to *add* one, never running the test suite it edited (`2e38f412`).

**18:38** Orchestrator `66bcfad1` starts; runs 14.92 h. **19:31** A three-model smoke probe: two die instantly with `UNKNOWN_MODEL`; after a relaunch with the model list set, the 19:43 recheck passes 3/3.

**19:55–21:03** Planning fan-out — three parallel leads, three consolidators, 68.2 min, all completed. It earned its money: it caught a specialisation-nesting hazard and, via a live `nix eval`, that the plan's own guard assertion self-trips on the unit that plan creates.

**21:18–04:58** Build fan-out (`65d4d545`), **sequential, not parallel**: T1 fails at +08:07 on an upstream 500, T2–T7 run back-to-back over 7.7 h, three reviewers follow, and the run ends `stopReason: error` — `workflow result.tasks[0].title: undefined is not JSON data` — discarding all three verdicts.

**08:43** The live `nixos-rebuild switch` partially fails; the orchestrator root-causes it read-only and lands `cf21507` in 16 min. **09:09** The drill fails on 1 of 34 steps. **10:03** `0e727ba` lands the fix.

---

## 3. Scorecard

| | |
|---|---|
| Sessions / tool calls | 29 (7 interactive, 22 subagents) / 1,247 |
| Tokens in + out | **19,067,180** (cache-read a further 168,985,536) |
| Estimated cost | **$23.73**; top 5 sessions $19.31 (81%). External price table — dsh records no cost (D5) |
| Spend shape | input ~$10.5, cache-read ~$10.0, output ~$3.8 → **~84% is re-sent context** |
| Tool-result text | 4,746,163 chars; `read` **71.6%**, `bash` 18.0% |
| Largest read slice | the run's own plans/specs/docs — 1,356,729 chars, **39.9%** |
| Within-session repeat reads | 362,592 chars — **10.7%** of read text |
| Build-only rule | **held, 29/29** — no `sudo`, `nixos-rebuild`, `systemctl start/stop/restart` on the host |
| Reliability | 5 retries, 8 error/aborted turns, 20 tool errors, **1 of 4 workflow runs errored** |
| Approvals | 3, all `danger-full-access`, allowed-once; the 3h35m one was operator sleep (05:03→08:39) |
| Factory wall-clock | 530.2 min dispatched; run 2 alone **460.7 min** |
| Outcome | 8 commits; all named checks green at `cf21507`; live acceptance **FAIL**, 1 of 34 |
| Findings | 18 raised → **5 survived** |

---

## 4. Top problems, with evidence

- **The plan→build handoff is broken at HEAD** — `dark-factory.js:148` drops `spec` while `:131` makes it the entire implementer payload; a same-day regression. See H9.
- **The return value crashed after 460.7 minutes** — `66bcfad1 +620:10`, `stopReason=error` at `materializeResult`, because the hand-written `args.tasks` carried no `title`; every implementer prompt read `task T4 "undefined"`. `norm():93` now defaults `title`, turning that abort into a *silent* completion — so the guard must move to the dispatch path.
- **Reviews are produced and read by nothing** — `:142` assembles the verdicts, `:149` returns them; nothing counts blockers or triggers a fix round, and the completeness reviewer's `verdict: rework` (`+30:10`) never appears again. **But** branching on verdicts would not have caught the field defect: the technical reviewer found it unaided (`6a1c4d0e +18:40`) and graded it `minor`/`pass`, which such a gate skips by construction.
- **A read-only cache defect cost fourteen sessions a detour each** — `1515b0e8 +03:20`: `touch ~/.cache/nix/.wtest` → "Read-only file system", as the file's own owner. See H4.
- **Cost is re-sent context, not thinking** — `fc45cd50`: 30,758 reasoning-chunks against 63 text-chunks, 577,031 output tokens, 2.54 h, **$6.02 = 25% of the day**, of which only $1.26 is output and $3.95 cache-read. Its first `edit` is at **+111:38, step 78 of 157**; the stall began when its decisive probe hit the cache defect at `+35:03`.
- **Green checks did not equal a working system** — everything passed, and the live acceptance failed on step 8, whose unit test had pinned the *wrong* argv as its contract.
- **The lane's data guarantee misses its own agent jobs** — three credential-injected, unpatched POSTs to `/api/v1/messages` sit in the broker audit log. See U7.
- **The seat's mind lives outside the OS** — the five sessions that started before the skills symlinks existed (2026-09-03 19:14:27) contain no skill names while carrying dsh's `skill` tool. See U6.

---

## 5. Harness improvements, ranked

### H9 — Restore `spec` to the plan-mode return; bound the planning outputs *(S; M with bounding)*

**Claim.** The round trip the script documents is broken, and the planning prose is re-sent six times.

**Evidence.** `:148` drops `spec`; `:131` makes it the whole implementer payload; `:96` coerces a missing one to `''`; `:7-9` prescribes that round trip. Regression dated to `f2018e7` (09-04 08:39) against `dc2580a:140`; never exercised, since the one build run supplied specs by hand, so the cost is projected. The three planning lenses carry no schema and no length bound (`:109-111`) and each is re-interpolated into two downstream prompts (`:115-117`): the consolidation prompts total **125,476 chars** against 9,644 for the planning prompts, and each consolidator being a different model and session, they buy no cross-model cache — and that return already overran the workflow tool's 50,000-byte inline cap (`web-default.yml:296-298`) at 49,481 chars, spilling to a file with specs clipped and three recovery reads. Two validation gaps: an *unknown* role survives `norm()` (`:94` defaults only a *missing* one) and is silently swapped for GLM at `:127`; `dependsOn` is in the schema (`:55`) and never read — execution is array order (`:126`).

**Gain.** Stops a re-run of the documented two-step wasting a whole build; the observed one cost ~6.5 h of implementer wall-clock. Token savings not measured.

**How-to.** Put `spec` back in the projection — one token. Cap the planning outputs in the *prompt*; dsh's schema subset cannot express length. Validate `args.tasks` on entry (unknown role, missing `title`, dangling `dependsOn`) instead of coercing — that path bypasses `TASK_SCHEMA` entirely. Either hand-roll a dependency scheduler or drop `dependsOn` — `pipeline()` is per-item fan-out, not a topological sort. Do **not** turn the consolidation essays into bullet objects: they produced the plan the whole build ran on, and the saving is cents.

### H4 — Pre-set a writable `XDG_CACHE_HOME` in the seat *(S)*

**Claim.** The sandbox makes `$HOME` read-only, so nix cannot write its cache; sessions rediscover this individually and inconsistently.

**Evidence.** 12 of 29 digests carry `attempt to write a readonly database` verbatim, plus two more in the raw transcripts (`2ea13d37 +07:18`, `fc45cd50 +129:02`) — 14 of 29 hit it, of 18 that invoke nix at all. Fetcher-cache writes are fatal (`893bf6de` lost four consecutive nix calls, +01:50/+03:28/+03:32/+03:39); eval-cache writes only print `error (ignored)`. `b7e57c4e` lost its baseline test run at `+02:39` and spent ~108 s and 3 extra calls reaching a workaround at `+04:27`. It never sticks, because each shell call is a fresh shell: **20+ distinct** `XDG_CACHE_HOME` values appear across the corpus, `2714bacb +76:17` relapses mid-session, and `6a1c4d0e` uses `$(mktemp -d)` on *every* call — a cold cache per command. Nine of the twelve digest-confirmed sessions are subagents of one parent, so this is ~3 distinct launches, which strengthens the fix: one export inoculates a whole subagent tree.

**Gain.** 1–3 tool calls and ~1–2 min per affected launch plus the relapses, and it stops agents hardcoding store paths. Failures avoided, not tokens saved.

**How-to.** In `dsh-openrouter.sh`, after `DSH_HOME` is set: `export XDG_CACHE_HOME=${XDG_CACHE_HOME:-/tmp/dsh-openrouter-cache-$(id -u)}; mkdir -p -m 700 -- "$XDG_CACHE_HOME"`. It must sit under a platform temp root — a state dir under `$HOME` is blocked identically and would merely *look* configured — and be stable, not `mktemp -d`. The launcher is the only lever: dsh refuses `XDG_*` from `$DSH_HOME/.env`, its shell tool has no env knob, and its scrubber strips only `KEY|PASSWORD|SECRET|TOKEN` and `DSH_*`. Add the gotcha to `CLAUDE.md`'s Gotchas and the `nixos` skill's `gotchas.md`; dsh loads both. **Defer the lane half:** no lane session hit it, and `ProtectHome`/`PrivateTmp` would defeat a bare `Environment=`.

---

## 6. Product evaluation and upgrades, ranked

### What was built, verbatim

At `cf21507`, clean checkout: `lint> All checks passed!` — `helm-unit-tests> 111 passed in 9.22s` — `vm-test-run-helm-control> test script finished in 35.98s`; `helm-control-eval` and `host-core` green. Reverse-applying `cf21507`'s module hunk turns `helm-control-eval` red, so the guard is load-bearing.

```
== 8. open the gaming workspace (a Console window -- operator judgment)
   PASS: POST /action/open flake=gaming answered 200 with the open banner
   Did a Console window open in ~/flakes/gaming running claude? [y/N]
   FAIL: no Console window (or wrong contents) -- D3/D11.4
== Result: 31 passed, 1 failed, 2 skipped
HELM V1 ACCEPTANCE: FAIL
```

The mid-fix tree at 09:52, before `0e727ba`: `At index 5 diff: 'helm-open-workspace strategy' != '/run/current-system/sw/bin/helm-open-workspace strategy'` — `2 failed, 109 passed`.

**Authorship.** T2 switch script + launcher → GLM 5.3 (`ee2739fc`) → `420a3b7`; T3 `serve.py` → GLM 5.3 (`661e7f48`) → `7f5c329`; T4 the `services.helm.control` module, polkit grant and agent-unit guard → DeepSeek V4 Pro (`fc45cd50`) → `b678875`; T5 render + VM test → GLM 5.3 (`2714bacb`) → `5c0c44d`, `54b1c4d`; T6 core wiring → GLM 5.3-Flash (`2ea13d37`) → `667f25d`; T7 docs/acceptance/runbook → GLM 5.3 (`e498fa18`) → `18d7a17`; both field fixes → the orchestrator, DeepSeek V4 Pro. T1 `render.py` (Kimi K3, `b7e57c4e`) died at +08:07 on an upstream 500 and committed nothing — the file entered as a red-phase stub inside `7f5c329` and was implemented by T5. Run task numbers are offset by one against the plan's (run T4 = plan Task 3). Six of eight commits carry `Co-Authored-By: GLM 5.3 <noreply@z.ai>` — five correctly, one (`667f25d`) copied from history by a Flash session; `b678875`, the root-privilege commit, has a **one-byte body and no trailer**.

### U7 — Cover the lane's agent jobs; fail the ZDR patch closed on streamed bodies *(M)*

**Claim.** The lane's stated data guarantee does not cover its own `agent` jobs, and fails open on large bodies.

**Evidence.** `policy.py:199-201` keys the body patch on `pathPrefix /api/v1/chat/completions` (`modelLane.nix:163-171`) while `_inject` (`:175-190`) keys on host alone. The `agent` job kind sets `ANTHROPIC_BASE_URL=https://<host>/api` and runs `claude -p` (`lane-run.py:239`), so its traffic goes to `/api/v1/messages` and is never patched — the three audit-log requests above. Only the `chat` kind carries ZDR, and it sets that itself client-side (`lane-run.py:98`), so the broker patch is redundant where it works and absent where it is the sole control. Separately, `_patch_body` runs only from `request()` (`:238`), and with `--set stream_large_bodies=1m` (`egressBroker.nix:257`) mitmproxy 12.1.1 marks a >1 MiB body for streaming *before* the headers hook, forwarding every chunk before `request()` fires — latent so far, since of 295 audited requests the largest is 563,603 bytes. So the decision doc's "Every request carries `provider: { zdr: true, data_collection: 'deny' }`" (`…lane-permitted-transcripts.md:12,:42`) is false today for agent jobs and silent above 1 MiB.

**Gain.** Makes the stated guarantee true for the job kind the lane exists to run, and turns a silent future bypass into an audited refusal.

**How-to.** Check whether OpenRouter honours a provider block on `/api/v1/messages`; if not, deny that path rather than patch it. Make `bodyPatch` take a **list** of prefixes covering it, and give `inject` its own per-instance allowed-path list — do **not** scope `inject` to `bodyPatch`'s prefix, which would strip the credential and break the agent lane. In `requestheaders()`, kill any flow to a `bodyPatch` host where `_request_body_might_stream()` (`:77-105`, already written, wired only into the deny path at `:149`) is true, audited as `zdr-unpatchable-streamed-body`; do **not** set `flow.request.stream = False`, since mitmproxy re-checks size per chunk and flips it back. Add a pytest posting a >1 MiB body, red first.

### U2 — Anti-framing headers on the control surface; fix the 60-second self-404 *(S)*

**Claim.** The control page can be framed, and every action response turns itself into a bare "not found" after a minute.

**Evidence.** `_send` (`serve.py:407-412` at `cf21507`) sets exactly three headers — no `X-Frame-Options`, `frame-ancestors`, `Cache-Control` or `Referrer-Policy` anywhere in the package, and no `Sec-Fetch-Dest` check. Every CSRF layer (Host allowlist, foreign-Origin rejection, `Sec-Fetch-Site`, per-boot token) passes inside a frame, because the framed document *is* `localhost:7700` and its form carries the real token. The attack is **clickjacking**: the attacker page can neither read nor submit that form, but it can overlay it so one operator click lands on a real profile button. Severity is bounded — the allowlist is the literal `["base","gaming"]` (`hosts/core/helm.nix:17-20`) and `docs/runbooks/helm-v1.md:136-144` already accepts that anything running as the user can call `systemctl start helm-switch@…` anyway — so this is the remaining browser-side path, not the last path to root. The self-404 is **measured**: rendering `collect.render_html` + `render.render_control` puts `<meta http-equiv="refresh" content="60">` (`collect.py:624`, mirrored in `_FALLBACK_PAGE`) in the action-response body, while `do_GET` 404s every path but `/` and `/status.json` (pinned at `test_serve.py:792`). No test sees it — `curl` ignores meta refresh — and the runbook (`:124`) scopes "the page is gone" to ":7700 refuses", steering the operator to `systemctl --user status helm-serve` on a healthy server.

**Gain.** Closes the clickjacking path and removes an operator-visible failure the runbook does not cover.

**How-to.** Add `Content-Security-Policy: frame-ancestors 'none'`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` to `_send`. Give the refresh a target — `content="60; url=/"` in `collect.py:624` and `_FALLBACK_PAGE` — or make `GET /action/*` answer 303 to `/`. Not a POST/redirect/GET state machine: it needs new banner state and contradicts the contract that an action response is the full page with a banner. Add the refresh meta to the test fixture so the assertion can go red. **Drop** the "empty token on denial pages" item: a cross-origin POST response is opaque so nothing leaks, and a token-less denial page would hand the legitimate operator dead buttons (`test_serve.py:844-849`).

### U6 — Assert the seat has its skills; then declare the harness payload as a flake *(S, then M)*

**Claim.** The seat is in the OS; the payload that gives it a mind is not, and nothing asserts the payload arrived.

**Evidence.** The seat is well wired — `pkgs/dsh-openrouter/{default.nix,dsh-openrouter.sh}`, `hosts/core/agent-prereqs.nix:19`, `githooks/pre-commit:13`, 21 bats cases in a 295-line `tests/unit/70-dsh-openrouter.bats`. Outside it is `~/flakes/dsh-harness`: no flake, githooks, treefmt, tests or decisions, and three subject-only commits (`af01427`, `dc2580a`, `f2018e7`) with empty bodies, no `(test: …)` marker and no trailers — the discipline the factory enforces on its agents, absent from the repo hosting the factory. `grep -rn dsh-harness` over `nixos-agent-env` returns nothing; deploy is two hand-made `ln -s`; and while the wrapper creates and locks down `$DSH_HOME` (`:200-202`), neither it nor the bats file ever mentions `skills/` or `AGENTS.md`.

**Gain.** A missing or broken symlink fails a check instead of manifesting as a model quietly having no skills; then the payload rolls back with a generation.

**How-to.** **Step 1, ~10 lines in this repo:** have `dsh-openrouter.sh` refuse or warn when `$DSH_HOME/skills` is missing, dangling or empty, plus one case in the bats file that already gates the seat — the whole measured gain, without touching dsh's tree, which the Claude/dsh separation forbids anyway. **Step 2:** ship `skills/` and `AGENTS.md` as a package. dsh resolves `$DSH_HOME/skills` as a first-class root and follows symlinks, so a `/nix/store` symlink loads; better still, it exposes `customSkillDirs`, which the wrapper's per-launch overlay can point at a store path, making drift structurally impossible. `flake.nix:26` already consumes a sibling repo as `git+file://…?ref=main` with a lock-node assertion to copy for the drift check; ownership belongs in the wrapper or overlay, since home-manager is not an input here. **Scope the catalog check to the real defect:** all 15 `SKILL.md` files have valid frontmatter and the 26 `superpowers:`-prefixed references resolve to 10 present directories, so a naive existence check finds nothing. What dangles is the `superpowers:` prefix itself, which dsh cannot resolve (its skill-name pattern forbids a colon), plus four Claude-plugin-relative paths inside skill bodies.

---

## 7. Dated debt — the reasoning stands, the number does not exist yet

| # | Claim | What would settle it |
|---|---|---|
| D1 | Clickjacking works in a real browser — never framed; nor is it known whether Firefox still lets a public page frame a loopback origin. | Frame `localhost:7700` cross-origin; click. |
| D2 | An operator actually lands on the bare 404 — the refresh and the 404 are measured, the navigation is not. | Load an action response; wait 60 s. |
| D3 | The >1 MiB ZDR bypass — read from mitmproxy's source; no such request sent (295 audited, max 563,603 bytes). | POST a >1 MiB body; inspect upstream. |
| D4 | Root cause of step 8. `0e727ba` blames the user manager's PATH, but a live probe shows `systemd --user` *does* carry `/run/current-system/sw/bin` and the journal shows `kgx` spawned a child. **Contested.** | Re-run step 8; capture the child's stderr. |
| D5 | Real dollar cost — dsh has no cost field; $23.73 is an external price table, and 3 sessions used another provider. | The OpenRouter activity export. |
| D6 | Whether reasoning effort reaches the provider — the seat is `xhigh`, but these hand-declared models may be treated as `off`-only. | Capture an outgoing request body. |
| D7 | Whether account-level ZDR / training opt-out is on — still OPEN on the board. | Check the account settings. |
| D8 | Quality effect of the factory's review gates — untested either way. | A paired run, same task list. |
| D9 | Red-before-green for 6 of 8 Helm commits — `cf21507` was mutation-checked here and `b678875` is covered by its four negative fixtures (`flake.nix:1056-1109`); the rest rest on commit bodies. | Reverse-apply each commit's test hunk. |
| D10 | H9's projected cost — the broken handoff has never been exercised. | Run plan→build once against the fixed script. |

---

## 8. Recommended next three actions

1. **Put `spec` back at `dark-factory.js:148` and validate `args.tasks` on entry.** One token plus a guard clause, before the next plan→build run — today that run would burn ~6.5 h of implementer time on empty specs.
2. **Close the broker's credential/data-policy gap.** Check whether `/api/v1/messages` honours a provider block, then give `inject` its own path allowlist and extend `bodyPatch` to a list of prefixes. The lane's own agent jobs are the uncovered ones, and three such requests are already in the audit log.
3. **Export `XDG_CACHE_HOME` in the seat wrapper and write the gotcha down.** One line in `dsh-openrouter.sh` plus one in `CLAUDE.md`'s Gotchas; it removes a detour fourteen sessions each paid separately.

---

## 9. Appendix — findings raised and refuted

- **H1 fail loud on `null`/`undefined`** — the `title` default is already committed; the cited crash was the engine failing *closed*.
- **H2 branch on review verdicts** — the reviewer graded the defect `minor`, which such a gate skips; it would instead re-run implementers costing $1.67–$6.02 each.
- **H3 step budget + repetition guard** — reasoning is ≤10% of spend, and a budget tight enough to trip would have cut the session before its first edit.
- **H5 unify `/tmp`** — the split is real, but unifying it removes containment for model-authored commands; cost is ~30–80 s per instance.
- **H6 inject a repo index** — the largest read slice is the run's own plan/spec prose (39.9%), which no derivation computes; repeats are 10.7%.
- **H7 preflight model routes** — `OPENROUTER_MODELS` is consumed at launch, so an in-session probe cannot fix it.
- **H8 mount the hooks bridge** — it does work (a `PreToolUse` deny fired, cost 0 context), but the cited incidents were already stopped by file mode and PAM.
- **H10 session index + cost ledger** — the index gives a search box, not agent recall; the ledger half is folded into D5.
- **U1 per-session git worktree** — no two writers overlapped, the one collision cost 24 s, and a *linked* worktree breaks under dsh's sandbox.
- **U3 mechanize the operator-judgment steps** — there are two such gates, not one, and the proposed dry-run would have passed the failing generation.
- **U4 gate empty commit bodies** — one empty body in 187 commits, and that commit carries red evidence in its own negative fixtures.
- **U5 store-back the policy surface** — the stale `AGENTS.md` bullet is ambiguous rather than false and no session acted on it; U6 carries the packaging argument.
- **U8 `lane-shell` inside the broker's netns** — the diagnosis holds but the mechanism fails open: `NetworkNamespacePath=` in a `systemd --user` unit starts fine and stays in the *host* namespace.
