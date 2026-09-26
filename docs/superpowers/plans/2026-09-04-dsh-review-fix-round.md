# dsh review fix round — the plumbing around the models — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Executor for the `N*` tasks: `tools/factory/dark-factory.js` in this repo (host `core`, build-only) — the `args` block is in §A. Executor for the `S*` task: the same script with `repo=~/flakes/nixos-skill`, `host=null`. The `X*`/`F*` tasks belong to the DeepSeek seat's own repo (`~/flakes/dsh-harness`) — `args.tasks` block in §B; **X0 must land by hand or as a reviewed diff first**, because the handoff those tasks would travel through is the thing that is broken.

**Goal:** every failure the 24-hour review found was in the wiring around the models, not the models. Close the five verified findings, act on the observations the verifiers upheld even where the headline claim was refuted, and turn each of the ten dated-debt items into either a measurement an agent can run or an operator action with a named artifact.

**Architecture:** three repos, three lanes. `nixos-agent-env` owns the seat wrapper, the broker, Helm and the ledger (Claude agents, `tools/factory/dark-factory.js`). `~/flakes/nixos-skill` owns the canonical `nixos` skill (its own flake and checks). `~/flakes/dsh-harness` owns the DeepSeek factory and the skill payload and is edited **only** by the DeepSeek seat or as a reviewed diff — per `claude-dsh-separation` (separate gits, separate flakes; crossings are diffs, never two writers on one tree).

**Tech Stack:** Nix flakes + NixOS modules, bash + bats, Python (mitmproxy addon, Helm server, ledger) + pytest + ruff, JavaScript (Workflow sandbox scripts, `node --check`).

**Spec:** `docs/reviews/2026-09-04-dsh-harness-review.md` (§5 H9/H4, §6 U7/U2/U6, §7 D1–D10, §9 the refuted thirteen); numbers in `docs/reviews/2026-09-04-dsh-metrics.md`; the three-lens votes, corrections and operative directives in `docs/reviews/2026-09-04-dsh-harness-review-verification.json`; and, for N10 and F3/F8/F9, `docs/decisions/2026-09-04-parallel-agent-workflows.md`. **Where a proposed fix and a verifier's feasibility note disagree, the verifier wins**; each such case is called out inline as `VERIFIER:`. **Where a verifier and the operator's decision disagree, the decision wins** — that happens once, on U1: the verifiers refuted *linked worktrees* under dsh's sandbox, which the decision accepts and routes around with clones, and it overrules only the conclusion this plan had drawn from it ("keep implementers sequential").

## Global Constraints

- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown, no reading `/var/lib/secrets/*`. The operator switches (§C).
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null` a gated command.
- Each task's spec names its own commit subject; use that subject's prefix, not `args.prefix`, when they differ. Trailer exactly `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- TDD: the failing check first, shown red, then green. A load-bearing test counts only once it has been shown to fail.
- Claude agents **never** write inside `~/flakes/dsh-harness`. Claude agents may write in `~/flakes/nixos-skill` (S1 only), in its own factory run.
- Every measurement names what it stands in for and the gap (`docs/decisions/2026-09-03-test-based-reality-amendments.md`).
- **One writer per tree.** After N10, an implementer works only in the isolated worktree it was started in, on exactly one branch named by its task key; it never merges, never moves another branch, and never writes in `${REPO}`'s own checkout. A task's `touches` list is a contract: if the work turns out to need a file outside it, stop and report a deviation rather than write it — another agent may hold that file in the same wave.

## Assumptions (stated, not verified here)

1. The seat is relaunched after N1/N7 land — `OPENROUTER_MODELS`, `XDG_CACHE_HOME` and the hook config are all consumed at launch (H7's refutation), so nothing in N1/N7 affects a running session. Operator action O9.
2. `dsh` stays pinned at `0.1.2-rc.1`; the hooks-bridge package name, the `- insert:` patch shape and the `hookSpecificOutput.permissionDecision` contract were read from that pin (see N7) and must be re-read if the pin moves.
3. Whether OpenRouter honours a `provider` block on `/api/v1/messages` is **unknown** (O3). N3 therefore ships the *mechanism* and leaves the `/api/v1/messages` prefix switched off in `hosts/core` behind an option, defaulting false.
4. The dsh transcripts the ledger reads are the durable ones under `$DSH_HOME/sessions/<slug>/<uuid>/session.jsonl.zstd` — the review's flat `transcripts/*.jsonl` corpus was a scratch export (H10 vote 3 corrected the glob).
5. The dsh factory's `args.tasks` contract is `{key,title,role,kind,spec,dependsOn}` with `role ∈ {deepseekPro, deepseekFlash, kimi, glm, glmFlash}` and `kind ∈ {backend, frontend, structured, routine}` (`factory/dark-factory.js:40-62`). F9 adds `touches` and `parallelSafe`; the §B list below already carries them, so **X0's entry validation must ignore unknown extra fields rather than reject them**, or §B cannot be dispatched.
6. Parallel implementers are a decision, not a preference: `docs/decisions/2026-09-04-parallel-agent-workflows.md` (operator, 2026-09-04) overrules this plan's earlier "keep implementers sequential" call. N10 lands it here; F3/F8/F9 land it on the dsh side.

---

## Tasks — `nixos-agent-env`

**Scheduling.** `dependsOn` and `touches` are declared per task in §A and the
scheduler N10 builds reads them. The waves that task list produces (N11 added
2026-09-04, resolving O11 — see its task below and the decision doc):

| wave | concurrent groups (a group runs sequentially inside itself) | why the group is a group |
|---|---|---|
| 1 | `{N1}` `{N2}` `{N10}` `{N11→N3→N6}` `{N5→N8}` | N3, N6 and N11 all write `flake.nix` (N11 extends the `host-core` eval check); N5 and N8 both write `docs/OPERATIONS.md` — the group's own key order (`groupWave` sorts lexicographically) is N11, then N3, then N6, since `"N11" < "N3"` as strings |
| 2 | `{N4→N7}` | both write `tests/unit/70-dsh-openrouter.bats`; both depend on N1 |
| 3 | `{N9}` | depends on every other task |

Five groups still run at once in wave 1 — N11 joins N3 and N6's group rather
than adding a new one, since it also writes `flake.nix` — so the implement
phase is bounded by the slowest group (now the three-task chain
`N11→N3→N6`), not by the sum of eleven tasks. **The run that lands
N10 is executed by whichever copy of the script the operator pastes**, so this
schedule is what N10 *computes*; it is exercised for real on the next factory
run (operator action O10).

### N1 (code, M, Sonnet impl / Opus review) — the seat wrapper: a writable cache, the factory's model set, and a skills assertion

Covers **H4**, the `OPENROUTER_MODELS` observation, and **U6 step 1** — three ~10-line changes to one script and one bats file, one commit, one reviewer.

**Files:** `pkgs/dsh-openrouter/dsh-openrouter.sh`, `tests/unit/70-dsh-openrouter.bats`.

- [ ] **Red first**, three cases appended to `70-dsh-openrouter.bats` (each must fail at HEAD, for the stated reason):
  - `"a writable XDG_CACHE_HOME is pre-set under a temp root"` — `make_key; OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config; [ "$status" -eq 0 ]`; then assert `/tmp/dsh-openrouter-cache-$(id -u)` exists, is a directory, mode `700`, owned by `$(id -u)`. **Red today:** the wrapper never creates it. Second case: with `XDG_CACHE_HOME=$TMPHOME/mine` exported, that dir is used and the `/tmp` one is not created. Third case: pre-create the `/tmp` path as a **symlink** → exit 5 and the message names it (a world-writable `/tmp` is shared with Firefox and Claude Code's own scratch — H5 vote 2).
  - `"the default model list covers the factory's five models"` — `--dump-config` with `OPENROUTER_MODELS` unset lists `moonshotai/kimi-k3`, `z-ai/glm-5.3`, `z-ai/glm-5.3-flash` and `deepseek/deepseek-v4-flash` exactly once each, and the default `deepseek/deepseek-v4-pro-0813` is not listed twice. **Red today:** the default at `:146` is `deepseek/deepseek-v4-flash` alone, which is why the 19:31 three-model probe died `UNKNOWN_MODEL` and cost a relaunch.
  - `"a missing or empty $DSH_HOME/skills warns on stderr"` — run `--dump-config` with no `skills` under `$XDG_DATA_HOME/dsh-openrouter`: stderr carries a line naming `$DSH_HOME/skills` and the README's `ln -s` recipe; repeat with a dangling symlink, and with an empty directory. With a non-empty directory present, stderr carries no such line. **Red today:** neither the wrapper nor the 295-line bats file mentions `skills/` or `AGENTS.md`.
- [ ] **Implement.** After `chmod 700 -- "$DSH_HOME"` (`:202`):
  ```sh
  # H4 (review 2026-09-04): the harness sandbox makes $HOME read-only for
  # model-run commands, so nix cannot write its fetcher cache. 14 of 29
  # sessions hit "attempt to write a readonly database"; each invented its
  # own workaround and 20+ distinct paths appear across the corpus, one
  # session using $(mktemp -d) per call (a cold cache every command).
  # writableRoots under workspace-write is exactly {workspaceRoot, /tmp,
  # os.tmpdir()}: a state dir under $HOME or $DSH_HOME is blocked
  # identically. The launcher is the only lever -- dsh refuses XDG_* from
  # $DSH_HOME/.env and its shell tool has no env knob.
  export XDG_CACHE_HOME=${XDG_CACHE_HOME:-/tmp/dsh-openrouter-cache-$(id -u)}
  [ -L "$XDG_CACHE_HOME" ] && die 5 "$XDG_CACHE_HOME is a symlink; refusing (/tmp is world-writable)"
  mkdir -p -m 700 -- "$XDG_CACHE_HOME"
  [ "$(stat -c %u -- "$XDG_CACHE_HOME")" = "$(id -u)" ] || die 5 "$XDG_CACHE_HOME is not owned by you"
  ```
  Change the `:146` default to `'deepseek/deepseek-v4-flash moonshotai/kimi-k3 z-ai/glm-5.3 z-ai/glm-5.3-flash'` with a comment naming the factory's role→model map as the reason. Add the skills check next to the `DSH_HOME` block: warn on stderr (`dsh-openrouter: …`) when `$DSH_HOME/skills` is absent, dangling or empty, and the same for `$DSH_HOME/AGENTS.md`.
  **VERIFIER (U6 vote 2):** warn, do not refuse, and do not add either proposed catalog check — 15/15 skills have valid frontmatter and 10/10 names resolve, so an existence check finds nothing. A refusal would also lock the operator out of the seat exactly when the payload is what is broken. `DSH_HOME` ownership stays in the wrapper; home-manager is not an input here.
- [ ] **Acceptance:** `nix develop -c bats tests/unit/70-dsh-openrouter.bats` green; `nix build .#checks.x86_64-linux.unit -L --no-link`; `…#checks.x86_64-linux.host-core`; lint gate. Commit `dsh: seat wrapper — a writable cache under a temp root, the factory's model set by default, a skills warning (test: unit, host-core, lint)`.
- **Docs to update:** none in this task (N5 carries the gotcha lines).

### N2 (code, S, Sonnet impl / Opus review) — Helm control surface: anti-framing headers, a refresh with a target, and the argv contract asserted against config

Covers **U2** and, as its third bullet, U3's surviving kernel (the defect that made the live acceptance fail: two green checks pinned opposite contracts).

**Files:** `pkgs/helm/serve.py` (`_send` ~`:415`, `_FALLBACK_PAGE` `:80`), `pkgs/helm/collect.py` (`:624`), `tests/helm/test_serve.py`.

- [ ] **Red first:**
  - `test_send_carries_anti_framing_headers` — drive the in-process live server already used at `test_serve.py:138-152`; assert on both a 200 page and a denial page: `Content-Security-Policy: frame-ancestors 'none'`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`. **Red today:** `_send` sets exactly three headers.
  - `test_action_response_refresh_has_a_target` — **VERIFIER (U2 vote 1/2):** the suite cannot see this today because the fixture `PAGE` has no refresh meta, so *first add `<meta http-equiv="refresh" content="60">` to the fixture*, then assert the rendered action response's meta is `content="60; url=/"`. **Red today:** `collect.py:624` and `_FALLBACK_PAGE` emit a bare `content="60"`, and `do_GET` 404s every path but `/` and `/status.json` (pinned at `:792`), so an action response turns itself into a bare "not found" after a minute.
  - `test_open_argv_matches_the_configured_path` — rebuild the expected argv from the config dict the test feeds the server rather than from a literal, and assert equality. **Red today:** `test_serve.py:373` pins a bare name while `flake.nix:1049` pins the absolute path; the two were free to diverge and did.
- [ ] **Implement:** the four headers in `_send` (one comment: the framed document *is* `localhost:7700` and its form carries the real token, so every CSRF layer passes inside a frame — clickjacking is the remaining browser-side path, not the last path to root); `content="60; url=/"` in both places. **VERIFIER (U2 vote 2/3):** do **not** build a POST/redirect/GET state machine (it contradicts the K5 full-page-with-banner contract) and do **not** blank the token on denial pages (a cross-origin POST response is opaque, and a token-less denial page hands the legitimate operator dead buttons — `test_serve.py:844-849`).
- [ ] **Acceptance:** `nix build .#checks.x86_64-linux.helm-unit -L --no-link`, `…helm-control-vm`, `…host-core`, lint. Commit `helm: anti-framing and no-store headers, the 60 s refresh targets "/", and the open argv is asserted against the configured path (test: helm-unit, helm-control-vm, host-core, lint)`.
- **Settles:** D2's mechanical half (the self-404 is now a red-then-green test, not a claim). Residual: a real browser navigation — operator O4.

### N3 (code, M, Sonnet impl / Opus review) — the broker's data policy covers the lane's own agent jobs and fails closed on streamed bodies

Covers **U7**. Two halves the verifiers asked to keep separate: (a) confirmed **and observed** — three credential-injected, unpatched POSTs to `/api/v1/messages` in the audit log; (b) confirmed in code, **latent** — the >1 MiB streaming hole (295 audited requests, max 563,603 bytes).

**Files:** `pkgs/broker/policy.py`, `nixosModules/egressBroker.nix` (options ~`:14-70`), `nixosModules/modelLane.nix` (`:159-171`), `tests/broker/test_policy.py`, `tests/integration/lane-vm.nix`, `flake.nix` if a check's file list changes.

- [ ] **Red first**, in `tests/broker/test_policy.py` (check `addon`):
  - `test_body_patch_applies_to_every_configured_prefix` — a spec with `path_prefixes = ["/api/v1/chat/completions", "/api/v1/messages"]`; a JSON POST to each is patched. **Red today:** `_patch_body` reads a single `path_prefix` and returns early on any other path.
  - `test_streamed_body_on_a_patched_path_is_killed_and_audited` — POST a >1 MiB JSON body to a `bodyPatch` host/path through `requestheaders()`; assert `flow.killed` and one audit record with `verdict: "deny"`, `reason: "zdr-unpatchable-streamed-body"`. **Red today:** `_patch_body` runs only from `request()` (`:238`), which fires at end-of-body — with `--set stream_large_bodies=1m` (`egressBroker.nix:257`) mitmproxy marks the body for streaming *before* the headers hook and every chunk is already on the wire.
  - `test_inject_honours_its_own_path_allowlist` — with `inject.<host>.paths = ["/api/v1/messages"]`, the header is set on that path and absent on `/api/v1/chat/completions`; with `paths` unset the header is set on every path (back-compatible default).
- [ ] **Implement.** `egressBroker.nix`: `bodyPatch.<host>.pathPrefixes` — a **list** of strings, default `[ "/" ]`, replacing `pathPrefix` (update `modelLane.nix:165` in the same commit); `inject.<host>.paths` — a list of allowed path prefixes, default `[ "/" ]`. `policy.py`: `_patch_body` matches any prefix; `_inject` checks the path list; `requestheaders()` gains, after `_check` and before `_inject`, a kill for any flow whose host has a `bodyPatch` spec matching this path and for which `_request_body_might_stream(flow)` (`:77-105`, already written and already wired into `_deny_request`) is true.
  **VERIFIER (U7 votes 2/3):** use `flow.kill()` with the audited reason — **never** `flow.request.stream = False`, because `state_consume_request_body` re-runs `check_body_size` per chunk and flips it back. Do **not** scope `inject` to `bodyPatch`'s prefix: that strips the credential and breaks the agent lane. Under streaming `raw_content` is `None`, so the audit body would also be corrupt — the kill is the only correct outcome.
- [ ] **The `/api/v1/messages` prefix stays off until O3 answers.** `modelLane.nix` gains `patchMessagesPath` (bool, default `false`) whose comment states the open question and cites the three audit records; when true it appends `"/api/v1/messages"` to `pathPrefixes`. If O3 says OpenRouter ignores a provider block on that path, the follow-up is to **deny** the path instead of patching it — a one-line change to the same option, not a redesign.
- [ ] **Acceptance:** `nix develop -c pytest tests/broker -q` red→green; `nix build .#checks.x86_64-linux.addon -L --no-link`, `…integration`, `…lane-eval`, `…lane-vm`, `…host-core`, lint. Commit `broker: bodyPatch takes a prefix list, inject gets its own path allowlist, and a streamed body on a patched path is killed and audited (test: addon, integration, lane-eval, lane-vm, host-core, lint)`.
- **Settles:** D3 (the >1 MiB bypass is now exercised by a test instead of read from mitmproxy's source). **Docs:** N9 corrects `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md:12,:42` — "Every request carries `provider: {zdr:true, data_collection:'deny'}`" is false today for agent jobs.

### N4 (code, S, Sonnet impl / Opus review) — D6 measurement: does a reasoning-effort setting reach the provider?

**Files:** `tests/unit/70-dsh-openrouter.bats`, `tests/mocks/openai-fake.py` only if the capture lacks a field. Depends on N1 (same bats file).

- [ ] **Red first:** `"the outgoing request body records whether reasoning effort is sent"` — reuse `start_fake` + `FAKE_CAPTURE`; run `dsh-openrouter --headless` against the fake upstream with the default (hand-declared) model, then assert on the captured body **the fact as measured**: either a `reasoning`/`effort` key is present (assert its value) or it is absent (assert absence). Write the assertion for the branch that is true after running it once by hand; the test then pins the finding so a pin bump that changes it goes red. **Red today:** no test looks at that field at all.
- [ ] **Acceptance:** `…#checks.x86_64-linux.unit` green. Commit `dsh: pin whether reasoning effort reaches the provider for a hand-declared OpenRouter model (test: unit, lint)`.
- **Proxy statement (required):** the fake upstream stands in for OpenRouter's `/api/v1/chat/completions`; it measures what the harness *sends*, not what the provider *does* with it. The residual gap — whether OpenRouter's DeepSeek route acts on it — stays dated debt.
- **Docs:** N9 records the result against D6.

### N5 (docs, S, Sonnet impl / Sonnet review) — the two gotchas that cost fourteen sessions and a dozen detours

**Files:** `CLAUDE.md` (Gotchas paragraph), `docs/OPERATIONS.md`.

- [ ] Add to CLAUDE.md's Gotchas, in the existing one-clause-each style: (1) **the read-only cache** — under an agent harness's sandbox `$HOME` is read-only, so `nix` cannot write `~/.cache/nix`; fetcher-cache writes are **fatal** while eval-cache writes only print `error (ignored)`; set a stable `XDG_CACHE_HOME` under `/tmp` (the seat wrapper now does), never `$(mktemp -d)` per command; (2) **the `/tmp` split** — an agent's shell tool and its file tools may see *different* `/tmp` (dsh gives the shell a fresh tmpfs per confined command while the file tools reach the host's), so a path written by one tool can be missing to the other; name a per-session scratch directory and use it for both. **VERIFIER (H5 votes 1/2):** documentation only — do **not** unify the namespaces; that removes the containment for model-authored shell commands, and the measured cost is ~30-80 s per instance with no scratch file ever committed.
- [ ] Board: a START HERE line for this round with the task keys and their state.
- [ ] **Acceptance:** lint gate green; the two new clauses each name a concrete symptom string an agent can grep for (`attempt to write a readonly database`; `ENOENT` on a path the other tool just wrote). Commit `docs: CLAUDE.md gotchas — the read-only nix cache under an agent sandbox, and the bash-vs-file-tool /tmp split (test: lint)`.

### N6 (code, L, Sonnet impl / Opus review) — the ledger extractor, extended to dsh usage events

**This extends the existing, still-open T1 of `docs/superpowers/plans/2026-09-03-lane-l-round1.md`** (`tools/ledger/factory.py`, `checks.ledger-unit`) — it does not duplicate it. Build T1 exactly as specified there, then add the dsh reader in the same task; T1's line in that plan is updated to point here.

**Files:** `tools/ledger/factory.py`, `tools/ledger/schema.md`, `tests/ledger/test_factory.py` (+ fixtures), `flake.nix` (`checks.ledger-unit`; ruff scope `+= tools/ledger tests/ledger`), `docs/superpowers/plans/2026-09-03-lane-l-round1.md` (one line: T1 lands here).

- [ ] **Red first:** `tests/ledger/test_factory.py::test_dsh_session_usage_rollup` against a committed two-session fixture (one plain `.jsonl`, one `.jsonl.zstd`, three steps each): exact input, output, cache-read and reasoning token totals per session; `role` and `model` joined from `manifest.json`; wall clock from first/last event; tool-call count. Plus `test_extract_is_idempotent` (keyed by session id) and `test_no_cost_field_is_invented`. **Red today:** `tools/ledger/` does not exist.
- [ ] **Implement:** `factory.py extract-dsh <sessions-dir>` walking `<dir>/<slug>/<uuid>/session.jsonl.zstd` (**VERIFIER, H10 vote 3:** that is the real layout; `$DSH_HOME/sessions/*.jsonl` matches zero files — decompress with `zstd -dc`), summing `assistant/message.data.usage` across steps, writing `dsh-sessions.jsonl` `{v:1, src, session_id, slug, role, model, started, turns, steps, tools, in, out, cache_read, reasoning, wall_s}` (`started` — epoch ms of `min(createdAt, first event time)`, the one field beyond the shorthand list — is what `rollup --costs` joins on for date+model).
- [ ] **No dollars in the extractor.** **VERIFIER (H10 votes 1/2):** dsh's `TokenUsage` declares only token counts — `cost` is null in all 21 sessions carrying usage — and a Nix-pinned price table goes stale and is wrong for the sessions that used another provider. Dollars enter through `factory.py rollup --costs <openrouter-activity.csv>`, joined by date and model, from the operator's export (O2). With no CSV the rollup prints tokens and the string `cost: unknown (no provider export)`.
- [ ] **Acceptance:** `nix build .#checks.x86_64-linux.ledger-unit -L --no-link`, lint (ruff must cover the new dirs — a new language surface lands with its linter in the same task). Commit `ledger: factory runs, agents and findings from the workflow transcripts; dsh session usage; backfill and weekly rollup, dollars only from a provider export (test: ledger-unit, lint)`.
- **Settles:** the token half of D5. The dollar half is operator O2.

### N7 (code, M, Sonnet impl / Opus review) — a minimal deterministic "protect the model" hook set for the seat

The bridge dsh ships **works** and is unused: a `PreToolUse` deny was verified end to end against the pin, held under `DSH_PERMISSION_MODE=danger-full-access`, and cost **zero** context (turn-1 request body 32,822 bytes with and without). H8 was refuted as a *security* claim — the incidents it cited were already stopped by file mode and PAM — so this ships as **deny-only defence-in-depth with an audit trail**, which is exactly what the verifiers left standing. Depends on N1.

**Files:** `pkgs/dsh-openrouter/hook-guard.py` (new), `pkgs/dsh-openrouter/default.nix`, `pkgs/dsh-openrouter/dsh-openrouter.sh`, `tests/unit/70-dsh-openrouter.bats`.

- [ ] **Red first**, driving `hook-guard.py` directly with crafted stdin payloads (a hook is a pure stdin→stdout process, so this needs no harness):
  - bash denials: `sudo …`, `nixos-rebuild switch …`, `systemctl --user start helm-serve`, `systemctl restart …`, and a command reading `~/.config/openrouter/key` → stdout parses as JSON with `hookSpecificOutput.hookEventName == "PreToolUse"`, `permissionDecision == "deny"`, a non-empty `permissionDecisionReason`, exit 0.
  - bash allowed: `nix build .#checks…`, `git status`, `systemctl status helm-serve`, `systemctl --user show-environment` → **no** decision emitted (exit 0, empty stdout).
  - edit/write denials: a `file_path` outside `CLAUDE_PROJECT_DIR`; one under `~/.claude`, `~/.config/openrouter`, `~/strategy`, `/run/baskets`, `/var/lib/{baskets,helm,egress-broker,lanes,secrets}`; a symlink inside the workspace resolving outside it. Allowed: a path inside the workspace.
  - every denial appends one JSON line to `$DSH_HOOK_DENIAL_LOG` with `{ts, event, tool, reason, subject}`; the file is created 0600.
  - wrapper wiring: `--dump-config` shows the bridge entry with `configPath` pointing at the generated `$DSH_HOME/hooks.json`, and that file's matchers are `bash` and `edit|write`.
  **Red today:** none of these files exist and the composed profile carries no hooks entry.
- [ ] **Implement.** `hook-guard.py`: reads the payload on stdin, dispatches on `hook_event_name` + `tool_name`, emits `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}` on stdout and exits 0. Packaged with `writers.writePython3Bin`; `default.nix` exposes it as `runtimeEnv.DSH_HOOK_GUARD`. The wrapper writes `$DSH_HOME/hooks.json` (umask 077, regenerated each launch, same discipline as the route overlay) and appends to the overlay:
  ```yaml
  - insert:
      - name: '@deepseek-ai/dsh-hooks-claude-code'
        config:
          configPath: <DSH_HOME>/hooks.json
          projectDir: <workspace>
  ```
  **Two traps, both verified against the pin and both worth a comment in the file:** (1) a bare top-level `- name:` composes nothing — a patch that adds an entry **must** be wrapped in `- insert:` (`dsh-app-boot/lib/index.js:71-90`: `id` is required for non-insert patches); (2) dsh's tool is **`bash`**, not Claude Code's `Bash` — a verbatim Claude Code `hooks.json` matches nothing and fails silently.
  **VERIFIER (H3 vote 3, H6 vote 3, H8 votes 1/2):** deny-only. `{"continue": false}` is recorded but **not applied**, and `updatedInput` is logged but not honoured — a hook can only deny with a reason, so do not attempt a step budget, a rewrite, or an allowlist to shorten approvals (`allow` does not pre-approve). A top-level `{"decision":"deny"}` is invalid and ignored; only `hookSpecificOutput.permissionDecision` works. The comment must say plainly that a deny-list over shell command strings is a heuristic and an audit trail, **not** a boundary — the boundaries remain file mode, PAM, the wrapper's refusal list and the lane's netns.
- [ ] **Acceptance:** `nix build .#checks.x86_64-linux.unit -L --no-link`, `…host-core`, lint (ruff must cover `pkgs/dsh-openrouter/hook-guard.py`). Commit `dsh: a deny-only hook set for the seat — no sudo/nixos-rebuild/systemctl start-stop-restart, no edits outside the workspace or to protected paths, every denial logged (test: unit, host-core, lint)`.

### N8 (measurement, S, Sonnet impl / Sonnet review) — D9: red-before-green for the eight Helm commits

**Files:** `docs/reviews/2026-09-04-dsh-debt-measurements.md` (new — the one record file every measurement task appends to), `docs/OPERATIONS.md`.

- [ ] For each of the eight commits `420a3b7, 7f5c329, b678875, 5c0c44d, 54b1c4d, 667f25d, 18d7a17, cf21507`: in a throwaway `git worktree`-free checkout under the scratch dir (`git archive` at the commit, or `git stash`-free `git show`-driven patching — **never** rewrite the live tree), reverse-apply only that commit's *test* hunks on top of the commit and run the checks the subject names. Record per commit: `red` (the check fails without the test's change), `already-green` (it passes — the test is a change-detector), or `n/a` (docs-only). `cf21507` was mutation-checked in the review and `b678875` is covered by its four negative fixtures (`flake.nix:1056-1109`) — reproduce both rather than assuming them.
- [ ] **Acceptance:** the record file carries one row per commit with the exact command and the decisive output line; no repo file other than the two docs changes. Commit `docs: D9 measured — red-before-green per Helm commit, reverse-applied (test: lint)`.

### N9 (docs, S, Sonnet impl / Sonnet review) — the decision, the runbooks and the board

Runs last, after N1–N8 report.

**Files:** `docs/decisions/2026-09-04-dsh-review-fix-round.md` (new, append-only style), `docs/runbooks/helm-v1.md` (`:124`), `docs/runbooks/lanes.md`, `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md` (correction note, appended — the file is append-only), `docs/OPERATIONS.md`, `README.md` status line, `docs/concepts/2026-09-04b-*.md` (one concept: "the wiring around the models is the failure surface").
- [ ] Decision doc records: deny-only hooks (and why not a boundary); warn-not-refuse on missing skills; no pre-commit commit-body gate (**VERIFIER, U4:** one empty body in 187 commits, and that commit's red evidence is executable in its own negative fixtures — the trailer becomes a machine-set fact in the dsh factory instead, F4); dollars from the provider export, never a local price table; `/api/v1/messages` patched only once O3 answers.
- [ ] `helm-v1.md:124` — "the page is gone" currently scopes only to ":7700 refuses"; add the action-response case and what the refresh now does. `lanes.md` — the agent-kind job's path and what the broker does about it after N3.
- [ ] **Acceptance:** every command quoted in the changed docs exists and runs from the stated directory; lint gate green. Commit `docs: dsh review fix round — decision, runbook corrections, board (test: lint)`.

### N10 (code, L, Sonnet impl / Opus review) — the Claude factory gets a deterministic dependency scheduler, isolated per-task worktrees and deterministic integration

Implements `docs/decisions/2026-09-04-parallel-agent-workflows.md` on the Claude side. Today `tools/factory/dark-factory.js:172` is `for (const t of A.tasks)` — strictly sequential — and `:69` of the hard rules forbids branches and worktrees, so nine tasks cost the sum of nine wall clocks and a task list with a cycle or a dangling `dependsOn` is accepted silently.

**Files:**
- Modify: `tools/factory/dark-factory.js` (header comment `:1-31`; `RULES` `:69`; `IMPL_SCHEMA` `:97-110`; the implement loop `:171-231`; the Verify spawn `:233-236`; the return `:250-258`)
- Modify: `tests/factory/render.test.mjs`
- Create: `tests/factory/fixtures/args-parallel.json`
- No `flake.nix` change: `checks.factory-unit` already does `cp -r ${self}/tests/factory/fixtures tests/factory/fixtures`, so a new fixture file is picked up. **Do not touch `flake.nix`** — N3 and N6 are writing it in the same wave.

**Interfaces:**
- Consumes: nothing from other tasks. The Workflow `agent(prompt, opts)` contract, whose `opts.isolation: 'worktree'` runs the agent in a fresh git worktree (auto-removed if unchanged); `spawn()` at `:133` already forwards `opts` verbatim, so no plumbing is needed to reach it.
- Produces, for later factory runs and for the §A/§B task lists: `tasks[].dependsOn` (array of task keys), `tasks[].touches` (array of repo-relative paths or globs the task writes), `tasks[].parallelSafe` (optional bool), `args.concurrency` (int, default 4), `args.judge` (bool, default true), `args.integrationBranch` (string, default `factory/<prefix>-integration`); return value gains `schedule`, `integrationBranch`, `delivered`, and per task `wave`, `branch`, `workspace`, `blockedBy`.

- [ ] **Step 1: write the failing tests.** Create `tests/factory/fixtures/args-parallel.json`:

```json
{
  "plan": "docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md",
  "prefix": "sched",
  "scratch": "/tmp/factory-sched-scratch",
  "concurrency": 4,
  "tasks": [
    { "key": "A", "title": "A writes pkgs/a", "kind": "code", "checks": ["unit"], "spec": "A spec.", "touches": ["pkgs/a/a.sh"], "dependsOn": [] },
    { "key": "B", "title": "B writes pkgs/b", "kind": "code", "checks": ["unit"], "spec": "B spec.", "touches": ["pkgs/b/b.sh"], "dependsOn": [] },
    { "key": "C", "title": "C also writes pkgs/a", "kind": "code", "checks": ["unit"], "spec": "C spec.", "touches": ["pkgs/a/*.sh"], "dependsOn": [] },
    { "key": "D", "title": "D depends on A", "kind": "docs", "checks": ["lint"], "spec": "D spec.", "touches": ["docs/d.md"], "dependsOn": ["A"] }
  ]
}
```

Then append these scenarios to `tests/factory/render.test.mjs`. First extend `makeStubs()` so concurrency and ordering are observable — replace its `agentFn` preamble and add three trackers:

```js
  // --- concurrency instrumentation (N10) ---------------------------------
  const seq = []          // labels in dispatch order
  const overlaps = new Set() // "L1|L2" for every pair in flight together
  const inFlight = new Set()
  let logsBeforeFirstAgent = 0
  const track = async (label, body) => {
    if (!seq.length) logsBeforeFirstAgent = logs.length
    seq.push(label)
    for (const other of inFlight) overlaps.add([label, other].sort().join('|'))
    inFlight.add(label)
    await Promise.resolve(); await Promise.resolve()   // yield twice
    inFlight.delete(label)
    return body()
  }
```

and wrap the existing body: `const agentFn = async (prompt, opts) => track((opts && opts.label) || '', () => { calls.push({ prompt, opts }); ...existing dispatch... })`. Add `seq, overlaps, logsBeforeFirstAgent: () => logsBeforeFirstAgent` to the returned object, and teach the stub two new labels:

```js
    if (label.startsWith('integrate:') || label.startsWith('integfix:')) {
      return { merged: ['A'], conflict: '', checks_green: true, head: 'def5678', output: 'ok' }
    }
    if (label.startsWith('judge:')) {
      return { touches: ['pkgs/guessed'], reasoning: 'guessed from the spec text' }
    }
```

Scenario 7 — **a malformed graph refuses before any agent is spawned:**

```js
  {
    for (const [mutate, needle] of [
      [(a) => { a.tasks[0].dependsOn = ['ZZ'] }, /unknown task ZZ/],
      [(a) => { a.tasks[0].dependsOn = ['B']; a.tasks[1].dependsOn = ['A'] }, /cycle/],
      [(a) => { a.tasks.push({ ...a.tasks[0] }) }, /duplicate task key A/],
      [(a) => { a.tasks[0].kind = 'prose' }, /unknown kind prose/],
      [(a) => { a.tasks[0].spec = '' }, /empty spec/],
    ]) {
      const bad = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
      mutate(bad)
      const stubs = makeStubs('ok')
      await assert.rejects(
        () => runScript(stubs.agentFn, stubs.parallel, stubs.pipeline, stubs.phase, stubs.logFn, stubs.workflow, stubs.budget, bad),
        needle,
      )
      assert.equal(stubs.calls.length, 0, 'no agent is spawned when the task graph is malformed')
    }
  }
```

Scenario 8 — **waves, groups, and real concurrency:**

```js
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const result = await runScript(stubs.agentFn, stubs.parallel, stubs.pipeline, stubs.phase, stubs.logFn, stubs.workflow, stubs.budget, args)
    assert.deepEqual(result.schedule.waves, [['A', 'B', 'C'], ['D']], 'Kahn waves, keys sorted')
    assert.deepEqual(result.schedule.groups[0], [['A', 'C'], ['B']], 'A and C share pkgs/a and serialise; B runs alongside them')
    assert.ok(stubs.overlaps.has('impl:A|impl:B'), 'A and B are in flight at the same time')
    assert.ok(!stubs.overlaps.has('impl:A|impl:C'), 'A and C never overlap — their touches collide')
    assert.equal(stubs.seq.indexOf('impl:C') > stubs.seq.indexOf('impl:A'), true, 'C follows A inside the group, in key order')
    assert.ok(stubs.seq.indexOf('impl:D') > stubs.seq.indexOf('integrate:w1'), 'wave 2 starts only after wave 1 is integrated')
    // sorted: results are pushed in group-completion order (A,C then B), not key order
    assert.deepEqual(result.tasks.map((t) => [t.key, t.wave]).sort(), [['A', 1], ['B', 1], ['C', 1], ['D', 2]])
    assert.ok(stubs.logsBeforeFirstAgent() > 0, 'the schedule is logged before the first agent is dispatched')
    assert.ok(stubs.logs.some((l) => l.includes('serialised: A, C (touches overlap)')), 'the overlap note is printed')
  }
```

Scenario 9 — **isolation, branches and integration:**

```js
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const result = await runScript(stubs.agentFn, stubs.parallel, stubs.pipeline, stubs.phase, stubs.logFn, stubs.workflow, stubs.budget, args)
    for (const c of stubs.calls) {
      const l = (c.opts && c.opts.label) || ''
      if (/^(impl|fix|review|integrate|integfix):/.test(l) || l === 'verify') {
        assert.equal(c.opts.isolation, 'worktree', `${l} runs in an isolated worktree`)
      }
      if (l === 'baseline' || l === 'deliver' || l.startsWith('judge:')) {
        assert.equal(c.opts.isolation, undefined, `${l} needs no worktree of its own`)
      }
    }
    const implA = byLabel(stubs.calls, 'impl:A')
    assert.match(implA.prompt, /git checkout -B A factory\/sched-integration/, 'the implementer starts from the integration tip on its own branch')
    assert.ok(!implA.prompt.includes('Do not create branches or worktrees'), 'the old single-writer rule is gone')
    assert.match(implA.prompt, /work only in the isolated worktree you were started in/i)
    const integ = byLabel(stubs.calls, 'integrate:w1')
    assert.match(integ.prompt, /git merge --no-ff/, 'integration merges are --no-ff')
    assert.match(integ.prompt, /A, B, C/, 'branches are merged in topological, then key, order')
    assert.equal(result.integrationBranch, 'factory/sched-integration')
    assert.equal(result.delivered, true, 'verify passed, so the integration branch was fast-forwarded into the current branch')
    assert.match(byLabel(stubs.calls, 'deliver').prompt, /git merge --ff-only factory\/sched-integration/)
  }
```

Scenario 10 — **a failed dependency blocks, never runs; and a red integration stops one chain after exactly one fix:**

```js
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    const stubs = makeStubs('ok')
    const inner = stubs.agentFn
    stubs.agentFn = async (p, o) => {
      const l = (o && o.label) || ''
      if (l === 'impl:A') return { commit: '', summary: '', tests_run: [], test_results: '', deviations: '', blocked: true, blocked_reason: 'spec impossible' }
      if (l === 'integrate:w1') return { merged: [], conflict: 'C', checks_green: false, head: '', output: 'unit FAILED' }
      if (l === 'integfix:w1') return { merged: [], conflict: 'C', checks_green: false, head: '', output: 'still red' }
      return inner(p, o)
    }
    const result = await runScript(stubs.agentFn, stubs.parallel, stubs.pipeline, stubs.phase, stubs.logFn, stubs.workflow, stubs.budget, args)
    const d = result.tasks.find((t) => t.key === 'D')
    assert.equal(d.status, 'blocked')
    assert.deepEqual(d.blockedBy, ['A'])
    assert.equal(byLabel(stubs.calls, 'impl:D'), undefined, 'a blocked task is never dispatched')
    assert.equal(stubs.calls.filter((c) => c.opts.label === 'integfix:w1').length, 1, 'exactly one bounded integration fix, no loop')
    assert.equal(byLabel(stubs.calls, 'integfix:w1').opts.model, 'opus', 'the integration fix runs on the technical authority')
    assert.match(byLabel(stubs.calls, 'integfix:w1').prompt, /unit FAILED/, 'the fix agent is given the check output')
    assert.equal(result.delivered, false, 'nothing is delivered while the merged tree is red')
    assert.equal(byLabel(stubs.calls, 'deliver'), undefined)
  }
```

Scenario 11 — **the judge is consulted only for un-annotated tasks, is recorded, and is switchable:**

```js
  {
    const args = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'args-parallel.json'), 'utf8'))
    delete args.tasks[1].touches                       // B is now un-annotated
    const stubs = makeStubs('ok')
    const result = await runScript(stubs.agentFn, stubs.parallel, stubs.pipeline, stubs.phase, stubs.logFn, stubs.workflow, stubs.budget, args)
    assert.ok(byLabel(stubs.calls, 'judge:B'), 'the un-annotated task is judged')
    assert.equal(byLabel(stubs.calls, 'judge:A'), undefined, 'an annotated task is never judged')
    assert.deepEqual(result.schedule.judged, [{ key: 'B', touches: ['pkgs/guessed'], reasoning: 'guessed from the spec text' }])
    assert.ok(stubs.logs.some((l) => l.includes('judge: B touches pkgs/guessed')), 'the judge answer is printed, never silent')

    const off = JSON.parse(JSON.stringify(args)); off.judge = false
    const s2 = makeStubs('ok')
    const r2 = await runScript(s2.agentFn, s2.parallel, s2.pipeline, s2.phase, s2.logFn, s2.workflow, s2.budget, off)
    assert.equal(byLabel(s2.calls, 'judge:B'), undefined, 'args.judge=false consults no judge')
    assert.deepEqual(r2.schedule.groups[0], [['A', 'B', 'C']], 'with no annotation and no judge, B serialises with everything')
  }
```

- [ ] **Step 2: run them red.** `nix build .#checks.x86_64-linux.factory-unit -L --no-link`. Expected: fails in scenario 7 with `AssertionError [ERR_ASSERTION]: Missing expected rejection` — HEAD validates nothing and dispatches the baseline agent. Record the decisive line.

- [ ] **Step 3: implement the scheduler.** Insert after the `skillLines()` function and before `phase('Baseline')`:

```js
// ---- N10: deterministic dependency scheduler -------------------------------
// Decision: docs/decisions/2026-09-04-parallel-agent-workflows.md. Sequential
// execution is no longer the design; it is what the scheduler *chooses* when
// the graph or the file overlap says so. Everything here is a pure function of
// args.tasks: the same task list produces the same waves, the same groups and
// the same order on any machine (the cap is args.concurrency, NOT the host's
// CPU count, which the harness's own cap would otherwise leak into).
const KINDS = ['code', 'docs']
const CONCURRENCY = Number.isInteger(A.concurrency) ? A.concurrency : 4
const INT_BRANCH = A.integrationBranch || `factory/${A.prefix}-integration`
const USE_JUDGE = A.judge !== false

function validateGraph(tasks) {
  const keys = new Set()
  for (const t of tasks) {
    if (!t || typeof t.key !== 'string' || !t.key.trim()) throw new Error('dark-factory: every task needs a non-empty key')
    if (keys.has(t.key)) throw new Error(`dark-factory: duplicate task key ${t.key}`)
    keys.add(t.key)
    if (typeof t.title !== 'string' || !t.title.trim()) throw new Error(`dark-factory: task ${t.key} has no title`)
    if (typeof t.spec !== 'string' || !t.spec.trim()) throw new Error(`dark-factory: task ${t.key} has an empty spec`)
    if (t.kind !== undefined && !KINDS.includes(t.kind)) throw new Error(`dark-factory: task ${t.key} has unknown kind ${t.kind}`)
    for (const f of ['dependsOn', 'touches', 'checks']) {
      if (t[f] !== undefined && !Array.isArray(t[f])) throw new Error(`dark-factory: task ${t.key} ${f} must be an array`)
    }
  }
  for (const t of tasks) {
    for (const d of t.dependsOn || []) {
      if (d === t.key) throw new Error(`dark-factory: task ${t.key} dependsOn itself`)
      if (!keys.has(d)) throw new Error(`dark-factory: task ${t.key} dependsOn unknown task ${d}`)
    }
  }
}

// Kahn's algorithm. Sorting the ready set makes the wave order reproducible.
function computeWaves(tasks) {
  const byKey = new Map(tasks.map((t) => [t.key, t]))
  const pending = new Set(tasks.map((t) => t.key))
  const done = new Set()
  const waves = []
  while (pending.size) {
    const ready = [...pending].filter((k) => (byKey.get(k).dependsOn || []).every((d) => done.has(d))).sort()
    if (!ready.length) throw new Error(`dark-factory: dependsOn cycle among ${[...pending].sort().join(', ')}`)
    waves.push(ready)
    for (const k of ready) { pending.delete(k); done.add(k) }
  }
  return waves
}

// Overlap is decided on the literal prefix of each `touches` entry (everything
// before the first glob metacharacter), compared at a path boundary. '*' is the
// "unknown, assume everything" sentinel an un-annotated task carries.
function literalPrefix(p) {
  const s = String(p).replace(/^\.\//, '')
  const i = s.search(/[*?[]/)
  return i === -1 ? s : s.slice(0, i)
}
function pathsOverlap(a, b) {
  const x = literalPrefix(a); const y = literalPrefix(b)
  const [s, l] = x.length <= y.length ? [x, y] : [y, x]
  if (s === '') return true
  return l === s || l.startsWith(s.endsWith('/') ? s : s + '/')
}
function effectiveTouches(t, judged) {
  if (Array.isArray(t.touches) && t.touches.length) return t.touches
  const j = judged.get(t.key)
  if (j && j.length) return j
  if (t.parallelSafe === true) return []
  return ['*']
}
function tasksOverlap(a, b, judged) {
  if (a.parallelSafe === false || b.parallelSafe === false) return true
  const ta = effectiveTouches(a, judged); const tb = effectiveTouches(b, judged)
  if (!ta.length || !tb.length) return false
  return ta.some((x) => tb.some((y) => pathsOverlap(x, y)))
}

// Connected components of the overlap graph: a component runs sequentially in
// key order, components run concurrently. Components, NOT graph colouring --
// colouring would pack non-conflicting tasks into one sequential lane, which is
// the opposite of what we want.
function groupWave(waveTasks, judged) {
  const ts = [...waveTasks].sort((a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0))
  const parent = ts.map((_, i) => i)
  const find = (i) => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i] } return i }
  for (let i = 0; i < ts.length; i++) {
    for (let j = i + 1; j < ts.length; j++) {
      if (tasksOverlap(ts[i], ts[j], judged)) {
        const a = find(i); const b = find(j)
        if (a !== b) parent[Math.max(a, b)] = Math.min(a, b)
      }
    }
  }
  const byRoot = new Map()
  ts.forEach((t, i) => { const r = find(i); if (!byRoot.has(r)) byRoot.set(r, []); byRoot.get(r).push(t) })
  return [...byRoot.keys()].sort((a, b) => a - b).map((r) => byRoot.get(r))
}

validateGraph(A.tasks)
const WAVES = computeWaves(A.tasks)
```

- [ ] **Step 4: implement the judge, then print the schedule.** Still before `phase('Baseline')` — the judge runs first because its answers change the groups, and the whole schedule must be printed before the first implementer:

```js
const judged = new Map()
const judgeRecords = []
const unannotated = A.tasks.filter((t) => !(Array.isArray(t.touches) && t.touches.length) && t.parallelSafe !== true)
if (USE_JUDGE && unannotated.length) {
  phase('Schedule')
  const answers = await parallel(unannotated.map((t) => () => spawn(
    `You are the parallel-safety judge for task ${t.key} ("${t.title}") of a dark-factory run in ${REPO}. The task carries no "touches" annotation, so the scheduler cannot tell whether it may run beside its siblings. Read ${REPO}/${A.plan} (this task's section) and the spec below, then answer ONLY with the repo-relative paths or globs this task will WRITE — not the ones it reads. Be generous: a missed path means two agents writing one file. Do not modify anything.
TASK SPEC: ${t.spec}`,
    { label: `judge:${t.key}`, phase: 'Schedule', model: M.reviewCode, effort: 'low', schema: {
      type: 'object', required: ['touches', 'reasoning'],
      properties: { touches: { type: 'array', items: { type: 'string' } }, reasoning: { type: 'string' } },
    } })))
  unannotated.forEach((t, i) => {
    const a = answers[i]
    if (!a || !Array.isArray(a.touches) || !a.touches.length) { log(`judge: ${t.key} gave no answer — serialising it`); return }
    judged.set(t.key, a.touches)
    judgeRecords.push({ key: t.key, touches: a.touches, reasoning: a.reasoning })
    // Recorded, printed and returned -- never silently applied.
    log(`judge: ${t.key} touches ${a.touches.join(', ')} — ${a.reasoning}`)
  })
}

const GROUPS = WAVES.map((w) => groupWave(w.map((k) => A.tasks.find((t) => t.key === k)), judged))
log(`schedule: ${A.tasks.length} tasks, ${WAVES.length} wave(s), concurrency ${CONCURRENCY}, integration branch ${INT_BRANCH}`)
GROUPS.forEach((groups, i) => {
  log(`  wave ${i + 1}: ${groups.map((g) => g.map((t) => t.key).join('→')).join('  |  ')}`)
  for (const g of groups) if (g.length > 1) log(`    serialised: ${g.map((t) => t.key).join(', ')} (touches overlap)`)
})
const SCHEDULE = { waves: WAVES, groups: GROUPS.map((gs) => gs.map((g) => g.map((t) => t.key))), judged: judgeRecords, concurrency: CONCURRENCY }
```

- [ ] **Step 5: change the hard rules and the implementer prompt.** Replace `RULES` line `:69` (`- Work only in ${REPO} on the current branch (plain git repo, no remote). Do not create branches or worktrees.`) with:

```js
- Work only in the isolated worktree you were started in (run \`git rev-parse --show-toplevel\` and report it) and in ${SCRATCH}. It is a linked worktree of ${REPO}, so it shares the object database and every branch. Create exactly ONE branch, named by your task key, and commit only there. NEVER merge, NEVER move or delete another branch, NEVER run git worktree/clone/push yourself, and NEVER write inside ${REPO}'s own checkout — a separate integrator merges your branch after your wave.
```

and change the `NEVER write outside ${REPO} and ${SCRATCH}` line to `NEVER write outside your worktree and ${SCRATCH}`. Prefix the implementer's `TASK SPEC:` line with the workspace preamble:

```js
WORKSPACE: run \`git checkout -B ${t.key} ${INT_BRANCH}\` first — that puts you on your own branch at the integration branch's current tip, which already contains every dependency's merged work. Report the worktree path in \`workspace\` and the branch in \`branch\`.
```

Add `workspace` and `branch` (both `{ type: 'string' }`) to `IMPL_SCHEMA.properties` and to its `required` list. Pass `isolation: 'worktree'` in the `impl:`, `fix:` and `review:` spawn options — the reviewer needs one too, because it re-runs the named checks and must do that on the task's branch, not on the live tree: its prompt's first instruction becomes `git checkout --detach <the branch the implementer reported>` (detached, so it never contends with the implementer's own checkout of that branch). The judge, the baseline and the delivery agent get **no** worktree: the first two read, the last one is the only agent that may write in `${REPO}`. Fix agents branch from the previous branch instead of reusing it — the implementer's worktree still holds that branch checked out, and git refuses a second checkout of the same branch: the fix prompt says `git checkout -B ${t.key}-fix${round + 1} <the branch the implementer reported>`, and the integrator merges the last branch in the chain (a fix branch is a descendant, so merging it subsumes the original).

- [ ] **Step 6: replace the implement loop's driver.** Keep the whole per-task body (implement → review → fix rounds → status) exactly as it is today; lift it into `async function runTask(t, wave)` and drive it with:

```js
const results = []
const statusOf = new Map()
const branchOf = new Map()
for (let w = 0; w < GROUPS.length; w++) {
  phase('Implement')
  const groups = GROUPS[w]
  // Chunking by CONCURRENCY is a barrier per chunk: simple, deterministic, and
  // the harness caps concurrent agents anyway (min(16, CPUs-2)). A group runs
  // sequentially inside itself because its members write the same paths.
  for (let i = 0; i < groups.length; i += CONCURRENCY) {
    const slice = groups.slice(i, i + CONCURRENCY)
    const done = await parallel(slice.map((g) => async () => {
      const out = []
      for (const t of g) {
        const failed = (t.dependsOn || []).filter((d) => statusOf.get(d) !== 'approved')
        if (failed.length) {
          log(`${t.key} blocked — dependency ${failed.join(', ')} did not finish green`)
          out.push({ key: t.key, title: t.title, kind: t.kind === 'docs' ? 'docs' : 'code', status: 'blocked', wave: w + 1, blockedBy: failed })
        } else {
          out.push(await runTask(t, w + 1))
        }
      }
      return out
    }))
    // parallel() swallows a thrown thunk to null; runTask never throws, so a
    // null here is an infrastructure failure and must not vanish.
    done.forEach((rs, k) => {
      if (!rs) { log(`wave ${w + 1}: a task group returned null — ${slice[k].map((t) => t.key).join(',')} unreported`); return }
      for (const r of rs) { results.push(r); statusOf.set(r.key, r.status); if (r.branch) branchOf.set(r.key, r.branch) }
    })
  }
  await integrateWave(w + 1, GROUPS[w])
}
```

`runTask` sets `r.wave`, `r.branch = impl && impl.branch`, `r.workspace = impl && impl.workspace`, `r.blockedBy = []`, and is otherwise byte-identical to today's loop body.

- [ ] **Step 7: implement `integrateWave`.** Define it above the driver:

```js
const INTEGRATE_SCHEMA = {
  type: 'object', required: ['merged', 'conflict', 'checks_green', 'head', 'output'],
  properties: {
    merged: { type: 'array', items: { type: 'string' } },
    conflict: { type: 'string', description: 'the branch whose merge conflicted, or empty' },
    checks_green: { type: 'boolean' },
    head: { type: 'string' },
    output: { type: 'string', description: 'the decisive conflict or check-failure lines, trimmed' },
  },
}
const integrations = []
async function integrateWave(n, groups) {
  // Topological, then key, order: the wave's own groups are already key-sorted
  // and a group's members are ordered by key, so this is reproducible.
  const branches = groups.flat().map((t) => branchOf.get(t.key)).filter(Boolean)
  if (!branches.length) { log(`wave ${n}: nothing to integrate`); return }
  const checks = [...new Set(groups.flat().flatMap((t) => t.checks || []))].join(', ') || '(none named)'
  phase('Integrate')
  const merge = `In your worktree (it is a linked worktree of ${REPO}, so every task branch is already visible — this repo has no remote and nothing needs fetching): git checkout --detach ${INT_BRANCH} (detached, so ${INT_BRANCH} is never checked out anywhere and can be moved). Then merge these branches IN THIS EXACT ORDER, each with git merge --no-ff -m "factory: integrate <branch> (wave ${n})": ${branches.join(', ')}. If a merge conflicts, stop at that branch, run git merge --abort, and report it in "conflict" with the conflicting paths in "output". After all merges succeed, run these checks on the merged tree: ${checks}, each as nix build .#checks.x86_64-linux.<name> -L --no-link, then the lint gate nix develop -c githooks/pre-commit. Only if every one is green: git branch -f ${INT_BRANCH} HEAD, and report that SHA as "head".`
  let r = await spawn(`You are the wave-${n} integrator for a dark-factory run in ${REPO}. You do not write code; you merge and you check.
${RULES}
${merge}`, { label: `integrate:w${n}`, phase: 'Integrate', model: M.verify, effort: 'medium', isolation: 'worktree', schema: INTEGRATE_SCHEMA })
  if (!r || r.conflict || !r.checks_green) {
    // Exactly ONE bounded fix, on the technical authority, mirroring the
    // existing retry-once rule. If it is still red the chain stops: no loop.
    log(`wave ${n}: integration ${r && r.conflict ? 'conflicted on ' + r.conflict : 'checks red'} — one bounded fix`)
    const fix = await spawn(`You are the integration fix agent for wave ${n} of a dark-factory run in ${REPO}. The wave's branches did not merge clean, or the merged tree is red. Fix it in ONE pass; there is no second attempt.
${RULES}
Do: git checkout -B integfix-w${n} ${INT_BRANCH} in your worktree, then redo the merges in this order: ${branches.join(', ')}. Resolve conflicts by keeping BOTH sides' intent (read both commits with git show before deciding); never drop a task's change to make a merge easy. Then run ${checks} plus the lint gate. Only if every one is green: git branch -f ${INT_BRANCH} HEAD and report that SHA.
WHAT WENT WRONG: ${(r && r.conflict) ? 'conflict on branch ' + r.conflict : 'checks failed'}
OUTPUT: ${(r && r.output) || '(the integrator returned nothing)'}`,
      { label: `integfix:w${n}`, phase: 'Integrate', model: M.reviewCode, effort: 'high', isolation: 'worktree', schema: INTEGRATE_SCHEMA })
    if (!fix || fix.conflict || !fix.checks_green) {
      log(`wave ${n}: integration still red after one fix — this chain stops here`)
      for (const t of groups.flat()) if (statusOf.get(t.key) === 'approved') statusOf.set(t.key, 'integration-failed')
      integrations.push({ wave: n, ok: false, branches, output: (fix && fix.output) || (r && r.output) || '' })
      return
    }
    r = fix
  }
  integrations.push({ wave: n, ok: true, branches, head: r.head })
  log(`wave ${n} integrated into ${INT_BRANCH} at ${r.head}`)
}
```

Statuses set to `integration-failed` propagate through the driver's `statusOf.get(d) !== 'approved'` test, so every dependent in a later wave is `blocked` without another line of code.

- [ ] **Step 8: verify on the integration branch, then deliver.** Change the Verify spawn to carry `isolation: 'worktree'` and to start `Do, in order: 0) git checkout --detach ${INT_BRANCH}. 1) git log --oneline ${baseline.head}..HEAD.` (the rest unchanged), and add the delivery step after it:

```js
const allOk = integrations.every((i) => i.ok) && results.every((r) => r.status === 'approved')
let delivered = false
if (verify && verify.verdict === 'pass' && allOk) {
  phase('Deliver')
  const d = await spawn(`You are the delivery agent for a dark-factory run in ${REPO}. Every task is approved, every wave integrated, and the whole-run verify passed on ${INT_BRANCH}.
${RULES}
Do exactly this and nothing else: cd ${REPO}; git status --porcelain must be empty (if it is not, STOP and report ok=false with the output); git merge --ff-only ${INT_BRANCH}; git log --oneline -1. Report ok and the new HEAD. Do not delete any branch or worktree — the operator reads them for the post-mortem.`,
    { label: 'deliver', phase: 'Deliver', model: M.verify, effort: 'low', schema: {
      type: 'object', required: ['ok', 'head'], properties: { ok: { type: 'boolean' }, head: { type: 'string' } } } })
  delivered = !!(d && d.ok)
  log(delivered ? `delivered: ${INT_BRANCH} fast-forwarded into the current branch at ${d.head}` : `NOT delivered — ${INT_BRANCH} is left for the operator`)
} else {
  log(`NOT delivered — ${INT_BRANCH} holds the work; fast-forward it by hand with: cd ${REPO} && git merge --ff-only ${INT_BRANCH}`)
}
```

The baseline agent gains one instruction — `4) git branch -f ${INT_BRANCH} HEAD (do not check it out)` — so wave 1's implementers have a tip to branch from. Add `schedule: SCHEDULE, integrationBranch: INT_BRANCH, integrations, delivered` to the return, and `wave`, `branch`, `workspace`, `blockedBy` to each entry of `tasks:`.

- [ ] **Step 9: update the header comment** (`:5-31`), which `factory-unit` scenario 6 already asserts on: document `tasks[].dependsOn`, `tasks[].touches`, `tasks[].parallelSafe`, `concurrency`, `judge`, `integrationBranch`, and one sentence naming `docs/decisions/2026-09-04-parallel-agent-workflows.md`. Update `meta.phases` with the `Schedule`, `Integrate` and `Deliver` entries so the progress display groups them (a `phase()` call with no `meta` entry gets its own box, which is legal but reads as a bug).

- [ ] **Step 10: run the tests green.** `nix build .#checks.x86_64-linux.factory-unit -L --no-link` then the lint gate `nix develop -c githooks/pre-commit`.

- [ ] **Step 11: commit.**

```bash
cd /home/dalhaka/nixos-agent-env
nix develop -c git commit -F /tmp/claude-factory-dsh-review/n10.msg
```

with subject `factory: a deterministic dependency scheduler, isolated per-task worktrees and deterministic integration (test: factory-unit, lint)`.

- **Proxy statement (required):** `factory-unit` runs the script against stub globals, so it measures *what the script schedules and what it puts in each prompt* — not that two real agents wrote two real worktrees without colliding. The residual gap is closed only by operator action O10 (one real run, wall clock vs the sum of single-task wall clocks). Until then the wall-clock gain is dated debt.
- **Docs:** N9 records the decision doc in the round's decision entry; the decision file itself is written by hand with this plan, not by N10.
- **Workspaces:** N10 does not touch `~/factory` — its per-task isolation is the Workflow tool's own worktree (`opts.isolation: 'worktree'`), a mechanism the declared factory root (N11, dsh-harness side F8) has no bearing on. The return value already lists each: `tasks[].workspace` (and `tasks[].branch`) carries the implementer's reported path, unchanged by N11.

### N11 (code, S, Sonnet impl / Opus review) — declare the factory root in the host config

Resolves **O11** (operator, 2026-09-04, option 1): the dsh factory root is a
declared directory outside every git repo — `~/factory`
(`/home/dalhaka/factory`), created by the host config — not a gitignored
`.factory/ws/` inside `~/flakes/dsh-harness`. Three reasons carried into the
decision doc's workspaces mechanism: a clone inside a checkout is a nested
repo git cannot track cleanly; flakes copy every tracked file into the store
on each evaluation; untracked files break the clean-tree assertion (F2) — so
hiding workspaces in a repo forces a gitignore, and a declared root removes
all three and gives workspaces ownership and retention the operator controls.

**Files:** `hosts/core/agent-prereqs.nix`, `flake.nix` (`checks.host-core`), `docs/runbooks/lanes.md`.

- [ ] **Red first:** extend `checks.host-core` in `flake.nix`, next to its existing `systemd.tmpfiles.rules` assertions (the pattern is already in this same check for Helm's control wiring, and in `lane-eval` at `:1137-1152` — `nixpkgs.lib.any (r: nixpkgs.lib.hasInfix … r) c.systemd.tmpfiles.rules`), to assert three rules are present: `/home/dalhaka/factory`, `/home/dalhaka/factory/base`, `/home/dalhaka/factory/ws`, each `0700 dalhaka users`. **Red today:** none of those three paths appear anywhere in the module tree, so the new assertion fails against the live `hosts/core` config before the rule is added.
- [ ] **Implement.** In `hosts/core/agent-prereqs.nix` — the file that already owns `dsh-openrouter-pkg` and its `docs/runbooks/lanes.md` cross-reference — add:
  ```nix
  systemd.tmpfiles.rules = [
    "d /home/dalhaka/factory 0700 dalhaka users -"
    "d /home/dalhaka/factory/base 0700 dalhaka users -"
    "d /home/dalhaka/factory/ws 0700 dalhaka users -"
  ];
  ```
  with a comment naming `docs/decisions/2026-09-04-parallel-agent-workflows.md`'s workspaces mechanism and the three reasons above.
- [ ] **Backups:** `services.proton-backup.paths` (`hosts/core/proton-backup.nix:29-41`) is an **explicit include list**, not a home-wide include — `/home/dalhaka/factory` is not among the eleven paths already named there, so **nothing to add**: the factory root (transient clones, refreshed or discarded per run) is excluded simply by never being listed.
- [ ] **Docs:** add a section to `docs/runbooks/lanes.md` — "factory runs: start `dsh-openrouter` from `~/factory`; base clones are `git clone --local ~/nixos-agent-env ~/factory/base/nixos-agent-env` (one per repo a run touches); workspaces live under `ws/<run-id>/<task-key>`; retention is manual until a factory-gc exists."
- [ ] **Acceptance:** `nix build .#checks.x86_64-linux.host-core -L --no-link`; lint gate. Commit `hosts/core: declare the dsh factory root — /home/dalhaka/factory{,/base,/ws}, 0700 dalhaka:users (test: host-core, lint)`.
- **Needs the operator's switch** (folded into **O8**) before **F8** can clone against the real root.

---

## Task — `~/flakes/nixos-skill` (separate repo, its own factory run)

### S1 (docs, S, Sonnet impl / Sonnet review) — the nixos skill's gotchas gain the two entries

**Files:** `skills/nixos/references/gotchas.md`, plus whatever check in that flake reads the reference list.

- [ ] **Red first:** that repo's existing catalog/reference check (or a new one-line grep check if none covers `gotchas.md` content) asserts the file contains `attempt to write a readonly database` and a `/tmp` split entry; red before the edit. **Why it matters:** the review measured zero hits for cache/readonly/XDG across the 157-line `gotchas.md`, and dsh loads this skill.
- [ ] Same two entries as N5, written for an agent working under a sandbox rather than for this repo's operator.
- [ ] **Acceptance:** that flake's `nix flake check -L` green. Commit `nixos-skill: gotchas — the read-only nix cache under an agent sandbox and the bash-vs-file-tool /tmp split (test: <that flake's check names>)`.
- **Then:** F6 re-syncs dsh's vendored copy. Claude never edits the copy.

---

## Tasks — `~/flakes/dsh-harness` (the DeepSeek seat's repo)

### X0 (by hand or as a reviewed diff, S) — **do this before the dsh factory is used again**

Covers **H9**. The factory's documented plan→build round trip is broken at HEAD, so it cannot be the vehicle for its own repair.

**File:** `factory/dark-factory.js`.

- [ ] `:148` — put `spec` back in the projection: `tasks.map(t => ({ key: t.key, title: t.title, role: t.role, kind: t.kind, spec: t.spec, dependsOn: t.dependsOn }))`. `:131` makes `spec` the entire implementer payload and `:96` coerces a missing one to `''`, so today a plan→build round trip dispatches every implementer with an empty spec — a same-day regression: `dc2580a:140` had `spec: t.spec` and `f2018e7` removed it in the same commit that added `args.tasks`.
- [ ] Validate `args.tasks` **on entry**, before any dispatch, throwing a plain `Error` (**VERIFIER, H1 vote 3:** `WorkflowError` is not one of the sandbox's six globals; and a plain `Error` thrown inside a `parallel()` thunk is swallowed to `null`, so the guard must sit on the dispatch path, outside the combinators): reject a missing/empty `key`, a missing `title` (the observed run lost `title` and every implementer prompt read `task T4 "undefined"` — `norm():93`'s default now turns that loud abort into a *silent* completion, which is why the guard must move here), an empty `spec`, a `role` outside the five keys (`:94` defaults only a **missing** role; an unknown one is silently swapped for GLM at `:127`), a `kind` outside the four, and any `dependsOn` entry naming no task in the list. `args.tasks` bypasses `TASK_SCHEMA` entirely, so this is the only place it can be checked. **Ignore unknown extra fields** — §B's entries already carry `touches` and `parallelSafe`, which F9 formalises; rejecting them here would make §B undispatchable. Cycles and duplicate keys are F3's job, not X0's.
- [ ] Verification for the diff: paste the script into the workflow tool with a deliberately bad `args.tasks` (unknown role; missing title; dangling `dependsOn`) and confirm each throws before any agent is dispatched, then one good `mode: "plan"` run whose return value contains `spec` on every task.
- **Then and only then** run §B's task list.

### F1 (dsh factory, `glm`, S) — review verdicts are logged and summarised, not discarded

`:142` assembles the three verdicts and `:149` returns them; nothing counts blockers, and the completeness reviewer's `verdict: rework` (`+30:10`) never appears again — then the whole return died at `materializeResult` after 460.7 minutes and took all three with it. **VERIFIER (H2, all three lenses):** this is plumbing with an unmeasured payoff, **not** an auto-fix gate — the technical reviewer found the real defect unaided and graded it `minor`, which a blocker+major gate skips by construction, while `rework`/`major` verdicts elsewhere would have re-run implementers at $1.67–$6.02 each. So: **no branching, no fix rounds.** For each reviewer, `log()` one line per `blocker`/`major` finding (`severity — where — issue`) and one line per `rework` verdict; add `reviewSummary: { blockers, majors, minors, rework: [labels] }` to the return. `log()` is the durable channel — the workflow journal survives a return-value crash, which the return value did not.

### F2 (dsh factory, `deepseekPro`, S) — an implementer that dies is retried once, then it stops the run

T1 (Kimi) failed at `+08:07` on one upstream 500, `:132` swallowed the dead child into `String(out || '')`, and the run continued for 7.5 more hours before anyone noticed. Retry the implementer once on a `null` return; if the retry is also `null`, record `{key, status: 'failed'}` in `impls`, `log()` it, and throw a plain `Error` **when any later task lists it in `dependsOn`** — otherwise continue and report. Add U1's surviving kernel in the same loop: between tasks, assert the **session workspace's** tree is clean and `log()` a warning when it is not (the one observed cross-lane collision cost 24 s). This guard stays useful after F8: the session workspace is where the operator and the seat still share a checkout, and F8's per-task clones are elsewhere. What is *not* the fix is a **linked** worktree — `git worktree add` reproducibly fails under dsh's bwrap profile with `Read-only file system` because its `.git` pointer leaves the writable workspace (U1 vote 3, which noted in the same breath that "an ordinary clone commits fine"). F8 uses the clone.

### F3 (dsh factory, `glm`, M) — a deterministic dependency scheduler: waves, not array order

Today `dependsOn` is in the schema (`:55`), never read, and execution is array order (`:126`). Per `docs/decisions/2026-09-04-parallel-agent-workflows.md`, it becomes a real scheduler — the same design N10 lands on the Claude side, so read that task for the shape.

**VERIFIER (H9 vote 3):** `pipeline()` is a per-item multi-stage fan-out with **no barrier** and cannot topologically order anything — the scheduler must be hand-rolled, and every throw must sit on the dispatch path, **outside** any `parallel()` thunk (a plain `Error` inside one is swallowed to `null`).

Required: validate the graph on entry — duplicate keys, `dependsOn` naming no task, a task depending on itself, an unknown `role` or `kind` (X0 already rejects the dangling case; this is the cycle and duplicate half) — and throw **before any agent is dispatched**; compute waves with Kahn's algorithm, sorting the ready set at each step so the schedule is reproducible from the task list alone; run each wave's tasks concurrently under an explicit `args.concurrency` (default 4, never the host CPU count); mark a task whose dependency did not finish green `blocked` and never run it; carry a `wave` number on every result; and `log()` the entire schedule — waves, groups, concurrency, integration branch — before the first dispatch. Keep the three read-only cross-reviewers at `:136-141` under `parallel()` as well: they were already free concurrency.

**Falsifiable check for this task (hand-run, recorded in the commit body):** paste the script with a task list containing a cycle and confirm the run throws naming the cycle with **zero** agents dispatched; then the §B list itself, `mode: "plan"`, and confirm the printed schedule matches the wave table in this plan's §B preamble.

### F8 (dsh factory, `deepseekPro`, M) — a persistent isolated clone per task, and deterministic integration

The dsh sandbox is `workspace-write`: writes land only inside the session's
working directory and the platform temp roots. A **linked** worktree
therefore fails (`git worktree add` → `Read-only file system`, U1 vote 3) but
a **clone** does not — the same vote measured that "an ordinary clone commits
fine". **Resolved 2026-09-04 (O11, option 1):** the factory root is
`args.factoryRoot`, default `$HOME/factory` — a directory **declared by the
host config** (nixos-agent-env N11), not a gitignored path inside this repo.
No `.factory/` entry lands in `.gitignore`. So:

- **Refuse before any dispatch** if `${factoryRoot}` does not exist or the session's own working directory is not `${factoryRoot}` or a descendant of it (a sandbox write outside it would fail silently later instead of failing loud now). This check runs on the baseline agent — the first agent dispatched regardless, needed anyway to establish the integration branch tip — which reports `factoryRootOk`/`cwdUnderRoot` in its schema; the script throws on either being false **before dispatching any implementer**, mirroring X0/F3's dispatch-path discipline (zero *implementer* agents on a refusal, even though the one baseline check already ran).
- **Base clones**, one per repo the run touches, refreshed from that repo's real HEAD at run start: `git clone --local ~/flakes/dsh-harness ${factoryRoot}/base/dsh-harness` (or a `git fetch` + reset if it already exists — never re-clone over an existing one; a base clone is shared read-only state for the run, not a workspace).
- **Per-task workspaces** under `${factoryRoot}/ws/<run-id>/<taskKey>/` — `run-id` a timestamp the script generates once at start, so two factory runs sharing the same root never collide. Each task's implementer clones its own copy at the moment its wave starts, `git clone --local ${factoryRoot}/base/dsh-harness ${factoryRoot}/ws/<run-id>/<taskKey>`, then `git checkout -B <taskKey> <integrationBranch>` — a complete checkout, so `nix build` / `nix flake check` can run in it and the flake sees tracked files, so the clone is committed-state based. A dependent task's workspace already contains its dependencies' merged work. One branch per task key; the implementer commits only there.
- Workspaces **persist until the run ends** (nothing under `${factoryRoot}/ws/` is deleted by the script; retention past that is manual, per N11's runbook note) and every path is listed in the return value (`tasks[].workspace`, `tasks[].branch`) for post-mortems.
- After each wave, one integrator agent merges that wave's branches into the integration branch in topological, then key, order with `git merge --no-ff`, in a dedicated clone at `${factoryRoot}/ws/<run-id>/integration` created once; it pulls each branch with `git fetch ${factoryRoot}/ws/<run-id>/<taskKey> <taskKey>:<taskKey>` and then merges. It runs the wave's declared checks plus the lint gate on the merged tree. **`~/flakes/dsh-harness` has no flake, no githooks and no tests today** (F7), so today that check set is `node --check factory/dark-factory.js` and nothing more — say so plainly in the log line rather than printing a green that means little; the check surface widens the moment that repo grows one.
- On a merge conflict or a red check: **exactly one** bounded fix task, `deepseekPro` (the technical authority on this side), in a fresh clone under the same `ws/<run-id>/` tree, handed the conflict or check output verbatim. If it is still red, that chain stops — mark the wave's tasks `integration-failed` and every dependent `blocked`. No loop; this mirrors F2's retry-once rule.
- **Delivery differs from the Claude side by decision:** the dsh factory does **not** merge into `~/flakes/dsh-harness`'s own branch. It leaves the integration branch in place and prints the recipe for the orchestrator: `cd ~/flakes/dsh-harness && git merge --ff-only <integrationBranch>`. The crossing between the two lanes stays a reviewed diff (`claude-dsh-separation`).
- **Needs N11 switched first:** `${factoryRoot}` (default `~/factory`) must already exist — the operator switch that lands N11 (nixos-agent-env, folded into that repo's O8) creates it. Until then, launch `dsh-openrouter` from `~/factory` fails the refusal above by construction (the directory is not there to be a cwd).

### F9 (dsh factory, `glm`, S) — parallel-safety annotations, and a judge only where they are missing

`TASK_SCHEMA` (`:40-62`) gains `touches` (array of repo-relative paths or globs the task will **write**) and `parallelSafe` (optional bool). The task-planner prompt is told to emit `touches` for every task it plans, in one sentence, with the reason stated: a missed path means two agents writing one file.

The scheduler then applies a **deterministic** overlap check inside each wave: compare the literal prefix of each `touches` entry (everything before the first glob metacharacter) at a path boundary; tasks whose entries overlap are serialised in key order within the wave, and the reason is printed as a schedule note (`serialised: F1, F2 (touches overlap)`). Group by connected components of the overlap graph, **not** by graph colouring — colouring packs non-conflicting tasks into one sequential lane, the opposite of the goal.

The LLM judge (`deepseekPro`) is consulted **only** for a task with no `touches` and no `parallelSafe: true`. It is asked for the paths that task will write, its answer is recorded in the schedule output and `log()`ed next to the tasks it moved, and `args.judge = false` disables it — in which case an un-annotated task serialises with everything in its wave. The judge never overrides an explicit `touches` and never decides anything that is not printed.

### F4 (dsh factory, `glmFlash`, S) — the commit convention is stated, and the trailer is a machine-set fact

No implementer prompt mentioned a trailer at all: one session invented `Co-Authored-By: GLM 5.3 <noreply@z.ai>` from its own identity, five later commits copied it correctly, and one (`667f25d`, a Flash session) copied it from `git log` and misattributed itself. `b678875` — the commit that grants root — has a **one-byte body and no trailer**. The implementer prompt at `:129-131` gains the exact convention: subject `<prefix>: <summary> (test: <check names>)`, a body stating the WHY, and a trailer line built by the script from the model id it is dispatching (`Co-Authored-By: <model id> <noreply@openrouter>`), so no model has to know or guess what it is. **VERIFIER (U4):** do **not** add a pre-commit body gate — base rate is 1 empty body in 187 commits, a regex can only check that prose exists, and the right hook would be `commit-msg` anyway (`pre-commit` gets no args and sees the *previous* message).

### F5 (dsh factory, `glm`, S) — bound the planning essays in the prompt

The three planning lenses carry no length bound, and each is re-interpolated into two downstream prompts: consolidation prompts total **125,476 chars** against 9,644 for the planning prompts, and the plan-mode return overran the workflow tool's 50,000-byte inline cap at 49,481 chars, spilling to a file with specs clipped at 2,000 chars and costing three recovery reads. **VERIFIER (H9 votes 2/3):** the permitted schema subset is `type/properties/required/additionalProperties/items/enum/const/oneOf` only — it **cannot** express a length bound, so the cap must be prompt-side; and do **not** replace the consolidation essays with bullet objects, because they produced the plan the whole build ran on and the saving is cents. Add an explicit word cap to each of the three planning prompts and to the two consolidation prompts, and one sentence telling the task planner to keep each `spec` self-contained but under a stated length.

### F6 (dsh factory, `glmFlash`, S) — re-sync the vendored `nixos` skill, fix the unresolvable prefix

After S1 lands: re-run the README's re-sync recipe (`rm -rf skills/nixos; cp -R ~/flakes/nixos-skill/skills/nixos skills/nixos`). Then fix what actually dangles in the catalog — **VERIFIER (U6 votes 1/3):** all 15 `SKILL.md` files have valid frontmatter and the 26 `superpowers:`-prefixed references resolve to 10 present directories, so an existence check finds nothing; what dsh cannot resolve is the **`superpowers:` prefix itself** (its skill-name pattern forbids a colon), plus four Claude-plugin-relative paths inside skill bodies. Map `superpowers:X` → bare `X` at those 26 occurrences and rewrite the four plugin-relative paths.

### F7 (dsh factory, `glm`, M) — the repo that hosts the factory gets the discipline the factory enforces

`~/flakes/dsh-harness` has no flake, githooks, treefmt, tests or decisions, and three subject-only commits with empty bodies and no trailers. Minimum: `README.md` documents the `args.tasks` contract verbatim — **as it stands after F3/F8/F9**: `{key,title,role,kind,spec,dependsOn,touches,parallelSafe}`, the five roles, the four kinds, that a malformed graph (duplicate key, dangling or cyclic `dependsOn`, unknown role or kind) throws before any dispatch, that `args.concurrency` (default 4) and `args.judge` (default true) exist, that each task runs in its own clone under `args.factoryRoot` (default `$HOME/factory`, a directory declared by the host config, never a gitignored path in this repo — nixos-agent-env N11) and commits on a branch named by its key, that the run refuses before dispatch if that root is missing or its own cwd is not under it, and that the run leaves an integration branch for the orchestrator to fast-forward rather than merging it itself — records the launch requirement (launch the seat from `~/factory`, not from this repo), and states the commit convention for this repo; `AGENTS.md`'s ambiguous "dark-factory.js" bullet is disambiguated (there are two same-named scripts — the Claude-side one still uses `sonnet/opus/fable`, so the bullet is ambiguous rather than false). **Packaging the payload as a flake (U6 step 2) is explicitly deferred**: the measured gain is already taken by N1's warning, `flake.nix:26`'s `git+file://…?ref=main` pattern is the model to copy when it is done, and ownership belongs in the wrapper or the `--patch` overlay (`customSkillDirs`), not home-manager, which is not an input anywhere.

---

## §A — machine-readable `args` for `tools/factory/dark-factory.js` (nixos-agent-env)

```json
{
  "plan": "docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md",
  "prefix": "dsh",
  "scratch": "/tmp/claude-factory-dsh-review",
  "repo": "/home/dalhaka/nixos-agent-env",
  "host": "core",
  "research": "docs/reviews/2026-09-04-dsh-harness-review.md, docs/reviews/2026-09-04-dsh-harness-review-verification.json, docs/reviews/2026-09-04-dsh-metrics.md",
  "skills": { "nixos": "/home/dalhaka/flakes/nixos-skill/skills/nixos" },
  "fixRounds": 2,
  "concurrency": 4,
  "judge": true,
  "integrationBranch": "factory/dsh-review-integration",
  "extraRules": "Each task spec names its exact commit subject; use that subject's prefix when it differs from args.prefix. Where this plan marks a VERIFIER note, the verifier's directive overrides the review's how-to and overrides your own judgement. Never write inside /home/dalhaka/flakes/dsh-harness. Your `touches` list is a contract: if the task turns out to need a file outside it, STOP and report that in deviations rather than writing it — another agent may hold that file in this wave.",
  "tasks": [
    { "key": "N1", "title": "seat wrapper: writable cache, factory model set, skills warning", "kind": "code",
      "checks": ["unit", "host-core", "lint"], "skillRefs": ["gotchas", "packaging"],
      "dependsOn": [], "touches": ["pkgs/dsh-openrouter/dsh-openrouter.sh", "tests/unit/70-dsh-openrouter.bats"],
      "spec": "Plan task N1. Three changes to pkgs/dsh-openrouter/dsh-openrouter.sh with three red-first bats cases in tests/unit/70-dsh-openrouter.bats: (1) export XDG_CACHE_HOME defaulting to /tmp/dsh-openrouter-cache-$(id -u), refuse a symlink or foreign owner, mkdir -p -m 700, honour a pre-set value; (2) change the OPENROUTER_MODELS default at :146 to 'deepseek/deepseek-v4-flash moonshotai/kimi-k3 z-ai/glm-5.3 z-ai/glm-5.3-flash'; (3) warn on stderr when $DSH_HOME/skills is missing, dangling or empty, and likewise for $DSH_HOME/AGENTS.md. WARN, do not refuse. Read the plan task for the exact comments and the verifier notes." },
    { "key": "N2", "title": "helm: anti-framing headers, refresh target, argv asserted against config", "kind": "code",
      "checks": ["helm-unit", "helm-control-vm", "host-core", "lint"], "skillRefs": ["review-checklist"],
      "dependsOn": [], "touches": ["pkgs/helm/serve.py", "pkgs/helm/collect.py", "tests/helm/test_serve.py"],
      "spec": "Plan task N2. pkgs/helm/serve.py _send gains Content-Security-Policy: frame-ancestors 'none', X-Frame-Options: DENY, Referrer-Policy: no-referrer, Cache-Control: no-store. collect.py:624 and serve.py:80's _FALLBACK_PAGE emit content=\"60; url=/\". tests/helm/test_serve.py: add the refresh meta to the fixture PAGE FIRST so the assertion can go red, then assert the target; assert the four headers on a 200 and on a denial page; rebuild the expected open-workspace argv from the config the test feeds the server instead of a literal. Do NOT build POST/redirect/GET and do NOT blank the token on denial pages." },
    { "key": "N3", "title": "broker: bodyPatch prefix list, inject path allowlist, streamed bodies killed", "kind": "code",
      "checks": ["addon", "integration", "lane-eval", "lane-vm", "host-core", "lint"], "skillRefs": ["security", "review-checklist"],
      "dependsOn": [], "touches": ["pkgs/broker/policy.py", "nixosModules/egressBroker.nix", "nixosModules/modelLane.nix", "tests/broker/test_policy.py", "tests/integration/lane-vm.nix", "flake.nix"],
      "spec": "Plan task N3. egressBroker.nix: bodyPatch.<host>.pathPrefixes (list, default [\"/\"]) replacing pathPrefix, and inject.<host>.paths (list, default [\"/\"]). policy.py: _patch_body matches any prefix; _inject honours its path list; requestheaders() kills (flow.kill(), NEVER flow.request.stream = False) any flow on a bodyPatch host+path for which _request_body_might_stream is true, audited 'zdr-unpatchable-streamed-body'. modelLane.nix: update to pathPrefixes and add patchMessagesPath (bool, default false) with a comment citing the three unpatched /api/v1/messages audit records. Red-first pytest cases in tests/broker/test_policy.py including a >1 MiB body. Do NOT scope inject to bodyPatch's prefix." },
    { "key": "N4", "title": "D6 measurement: does reasoning effort reach the provider", "kind": "code",
      "checks": ["unit", "lint"],
      "dependsOn": ["N1"], "touches": ["tests/unit/70-dsh-openrouter.bats", "tests/mocks/openai-fake.py", "docs/reviews/2026-09-04-dsh-debt-measurements.md"],
      "spec": "Plan task N4. Add a bats case to tests/unit/70-dsh-openrouter.bats using start_fake/FAKE_CAPTURE that runs dsh-openrouter --headless against the fake upstream and pins, as measured, whether the outgoing chat/completions body carries a reasoning/effort field. Run it once to learn the truth, then write the assertion for that branch so a pin bump that changes it goes red. Record the result and the proxy statement (the fake stands in for OpenRouter; it measures what the harness sends, not what the provider does) in docs/reviews/2026-09-04-dsh-debt-measurements.md." },
    { "key": "N5", "title": "CLAUDE.md gotchas: the read-only nix cache and the /tmp split", "kind": "docs",
      "checks": ["lint"],
      "dependsOn": [], "touches": ["CLAUDE.md", "docs/OPERATIONS.md"],
      "spec": "Plan task N5. Two clauses in CLAUDE.md's Gotchas paragraph, in the existing style, each naming a greppable symptom: 'attempt to write a readonly database' (fetcher-cache writes fatal, eval-cache writes only 'error (ignored)'; set a stable XDG_CACHE_HOME under /tmp, never mktemp -d per command) and the bash-vs-file-tool /tmp split (a path one tool writes can be missing to the other; use a named per-session scratch dir). Documentation only: do NOT unify the namespaces. Add a START HERE line to docs/OPERATIONS.md for this round." },
    { "key": "N6", "title": "ledger extractor + dsh session usage", "kind": "code",
      "checks": ["ledger-unit", "lint"], "skillRefs": ["packaging", "flakes"],
      "dependsOn": [], "touches": ["tools/ledger/", "tests/ledger/", "flake.nix", "docs/superpowers/plans/2026-09-03-lane-l-round1.md"],
      "spec": "Plan task N6. Build T1 of docs/superpowers/plans/2026-09-03-lane-l-round1.md exactly as specified (tools/ledger/factory.py, schema.md, tests/ledger/test_factory.py, checks.ledger-unit, ruff scope) AND add 'extract-dsh <sessions-dir>' walking <dir>/<slug>/<uuid>/session.jsonl.zstd (zstd -dc), summing assistant/message.data.usage into dsh-sessions.jsonl. Invent NO cost field: dollars enter only via 'rollup --costs <openrouter-activity.csv>'; with no CSV print 'cost: unknown (no provider export)'. Update the one line in the lane-l plan saying T1 lands here." },
    { "key": "N7", "title": "deny-only hook set for the seat", "kind": "code",
      "checks": ["unit", "host-core", "lint"], "skillRefs": ["security", "packaging"],
      "dependsOn": ["N1"], "touches": ["pkgs/dsh-openrouter/", "tests/unit/70-dsh-openrouter.bats"],
      "spec": "Plan task N7. pkgs/dsh-openrouter/hook-guard.py (writers.writePython3Bin, exposed as runtimeEnv.DSH_HOOK_GUARD) emitting hookSpecificOutput.permissionDecision deny + reason on stdout, exit 0; deny sudo/nixos-rebuild/systemctl start|stop|restart|reload|enable, reads of the key file, and edit/write whose resolved target is outside CLAUDE_PROJECT_DIR or under a protected prefix; append one JSON line per denial to $DSH_HOOK_DENIAL_LOG (0600). The wrapper generates $DSH_HOME/hooks.json each launch (umask 077) with matchers 'bash' and 'edit|write' and appends a '- insert:' entry mounting @deepseek-ai/dsh-hooks-claude-code. TWO TRAPS, comment both: a bare top-level '- name:' composes nothing (must be '- insert:'), and dsh's tool is 'bash', not Claude Code's 'Bash'. Deny-only: {\"continue\": false} and updatedInput are not honoured, and a top-level {\"decision\":\"deny\"} is ignored. Say in the comment that a shell deny-list is a heuristic and an audit trail, not a boundary." },
    { "key": "N8", "title": "D9 measured: red-before-green per Helm commit", "kind": "docs",
      "checks": ["lint"],
      "dependsOn": [], "touches": ["docs/reviews/2026-09-04-dsh-debt-measurements.md", "docs/OPERATIONS.md"],
      "spec": "Plan task N8. For 420a3b7, 7f5c329, b678875, 5c0c44d, 54b1c4d, 667f25d, 18d7a17, cf21507: in a throwaway checkout under the scratch dir (never the live tree), reverse-apply only that commit's test hunks on top of the commit and run the checks its subject names. Record red / already-green / n/a per commit with the exact command and the decisive output line in docs/reviews/2026-09-04-dsh-debt-measurements.md, and one board line." },
    { "key": "N10", "title": "factory: dependency scheduler, isolated worktrees, deterministic integration", "kind": "code",
      "checks": ["factory-unit", "lint"], "skillRefs": ["review-checklist"],
      "dependsOn": [], "touches": ["tools/factory/dark-factory.js", "tests/factory/"],
      "spec": "Plan task N10, implementing docs/decisions/2026-09-04-parallel-agent-workflows.md. tools/factory/dark-factory.js gains: validateGraph (duplicate keys, dangling or self dependsOn, unknown kind, empty spec/title — throwing BEFORE any agent is spawned); computeWaves (Kahn, ready set sorted, cycle throws naming the keys); a touches-based overlap check grouped by CONNECTED COMPONENTS (not graph colouring) so a component runs sequentially in key order and components run concurrently under args.concurrency (default 4, never the host CPU count); an optional judge (model reviewCode, label judge:<key>) consulted ONLY for tasks with no touches and no parallelSafe:true, whose answer is logged and returned, disabled by args.judge=false; isolation:'worktree' on every impl/fix/review/integrate/verify spawn, each implementer running `git checkout -B <key> <integrationBranch>` first and reporting workspace+branch; one integrator agent per wave merging that wave's branches --no-ff in topological-then-key order into the integration branch and re-running the wave's checks plus lint, with EXACTLY ONE bounded fix agent (model reviewCode) on a conflict or red check and then the chain stops; a deliver agent that does `git merge --ff-only <integrationBranch>` in the repo only when verify passed and every task is approved. Replace the hard rule 'Do not create branches or worktrees'. Red-first in tests/factory/render.test.mjs with a new fixture tests/factory/fixtures/args-parallel.json — five scenarios: refusal with zero agents spawned, waves+groups+observed concurrency, isolation+branch+integration prompts, blocked propagation with exactly one integfix, and the judge on/off. Do NOT touch flake.nix: factory-unit already copies the whole fixtures dir, and N3 and N6 are writing flake.nix in this wave." },
    { "key": "N11", "title": "declare the factory root in the host config", "kind": "code",
      "checks": ["host-core", "lint"],
      "dependsOn": [], "touches": ["hosts/core/agent-prereqs.nix", "flake.nix", "docs/runbooks/lanes.md"],
      "spec": "Plan task N11, resolving O11 (operator, 2026-09-04, option 1). Add systemd.tmpfiles.rules to hosts/core/agent-prereqs.nix creating /home/dalhaka/factory, /home/dalhaka/factory/base and /home/dalhaka/factory/ws, each '0700 dalhaka users -', with a comment naming docs/decisions/2026-09-04-parallel-agent-workflows.md and the three reasons a declared root replaces a gitignored .factory/ws/ inside ~/flakes/dsh-harness: a clone inside a checkout is a nested repo git cannot track cleanly, flakes copy every tracked file into the store on each evaluation, and untracked files break the clean-tree assertion (F2). Extend checks.host-core in flake.nix (pattern: the tmpfiles assertions already in this check for Helm and in lane-eval at :1137-1152) to assert all three rules are present — red today because none of the three exist anywhere in the module tree. Confirm services.proton-backup.paths (hosts/core/proton-backup.nix:29-41) is an explicit include list that does not name /home/dalhaka/factory, so nothing changes there — say so plainly rather than leaving it unaddressed. Add a section to docs/runbooks/lanes.md: factory runs start dsh-openrouter from ~/factory; base clones are git clone --local ~/nixos-agent-env ~/factory/base/nixos-agent-env (one per repo a run touches); workspaces live under ws/<run-id>/<task-key>; retention is manual until a factory-gc exists. Needs the operator's switch (O8) before F8 (dsh-harness side) can clone against the real root." },
    { "key": "N9", "title": "decision doc, runbook corrections, board", "kind": "docs",
      "checks": ["lint"],
      "dependsOn": ["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N10"],
      "touches": ["docs/decisions/", "docs/runbooks/", "docs/concepts/", "docs/OPERATIONS.md", "README.md"],
      "spec": "Plan task N9. Create docs/decisions/2026-09-04-dsh-review-fix-round.md recording: deny-only hooks and why they are not a boundary; warn-not-refuse on missing skills; no pre-commit commit-body gate (the trailer becomes a machine-set fact in the dsh factory instead); dollars from the provider export, never a local price table; /api/v1/messages patched only once the operator's check answers. Append a correction note to docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md (:12,:42 overclaim). Fix docs/runbooks/helm-v1.md:124 (the action-response case) and docs/runbooks/lanes.md (the agent-kind path). Update docs/OPERATIONS.md, README.md's status line, and write one concept doc. docs/decisions/2026-09-04-parallel-agent-workflows.md ALREADY EXISTS (hand-written with this plan): reference it from the round's decision doc and from the board, never rewrite or edit it — that directory is append-only." }
  ]
}
```

## §B — machine-readable `args.tasks` for the dsh-harness factory

**Precondition: X0 has landed, and N11 (nixos-agent-env) has been switched** — the declared factory root `~/factory` must already exist, because F8 refuses before dispatch if it does not. Launch the seat from `~/factory` itself, not from `~/flakes/dsh-harness` (the sandbox's `workspace-write` scope is the launch directory, and F8's base/workspace clones live under `~/factory`): `cd ~/factory && OPENROUTER_MODELS='deepseek/deepseek-v4-flash moonshotai/kimi-k3 z-ai/glm-5.3 z-ai/glm-5.3-flash' dsh-openrouter` (or, after N1, plain `dsh-openrouter`), pasting `factory/dark-factory.js` (from `~/flakes/dsh-harness`) into the `workflow` tool's `script` param with `mode: "build"`. The running instance is the pasted copy, so editing the file on disk is safe.

**Scheduling.** `dependsOn` now carries only *semantic* dependencies; the same-file serialisation that used to be faked with `dependsOn` is `touches`'s job. The waves this list produces once F3/F9 exist:

| wave | concurrent groups | why |
|---|---|---|
| 1 | `{F1→F2→F3→F4→F5}` `{F6}` | all five write `factory/dark-factory.js`; F6 writes only `skills/` |
| 2 | `{F8→F9}` | both write `factory/dark-factory.js`; both need F3's scheduler |
| 3 | `{F7}` | documents the contract F3/F4/F8/F9 define |

**This list gains almost nothing in wall clock, and that is the honest result:** eight of nine tasks write one file, so the overlap check correctly serialises them. What it gains is the printed schedule, the refusal on a malformed graph, and the guarantee that two writers never share a tree. The wall-clock case is §A's wave 1 (five concurrent groups). Note also that **this run is executed by the pre-F3 script**, which is array order — so the array below is written in a valid topological order (F1, F2, F3, F4, F5, F6, F8, F9, F7) and runs correctly either way.

```json
{
  "goal": "Fix the dark factory's plumbing per docs/reviews/2026-09-04-dsh-harness-review.md as corrected by the three-lens verification, and give it parallel implementers per the operator's decision (nixos-agent-env docs/decisions/2026-09-04-parallel-agent-workflows.md): verdicts logged and summarised, a dead implementer retried once then stopping the run, a deterministic dependency scheduler with waves instead of array order, a persistent isolated clone per task with deterministic integration, touches/parallelSafe annotations with a judge only where they are missing, the commit convention machine-set, planning essays bounded, the skill catalog re-synced, and the repo documented.",
  "mode": "build",
  "factoryRoot": "$HOME/factory",
  "context": "Edit only factory/dark-factory.js (and, in F7, README.md/AGENTS.md) in ~/flakes/dsh-harness. Claude's repos are off limits. Every task below carries a VERIFIER directive: where it disagrees with an instinct or with the review's own how-to, the verifier wins. The workflow sandbox has six globals (agent, parallel, pipeline, phase, log, args) and no filesystem or network; throw plain Error, never WorkflowError, and never inside a parallel() thunk — a plain Error thrown inside one is swallowed to null, so every guard sits on the dispatch path. The sandbox is workspace-write: writes land only inside the session's working directory and the platform temp roots, so a LINKED git worktree fails ('Read-only file system') and a full clone is the isolation that works. F8's clones live under args.factoryRoot (default $HOME/factory, declared by the host config outside every git repo — nixos-agent-env N11, resolving O11) — never a gitignored path inside this repo — so the seat for this run is launched from ~/factory, not from ~/flakes/dsh-harness. Commit with a subject, a body stating the WHY, and a Co-Authored-By trailer naming the model that wrote it.",
  "tasks": [
    { "key": "F1", "title": "log and summarise review verdicts", "role": "glm", "kind": "backend", "dependsOn": [], "touches": ["factory/dark-factory.js"],
      "spec": "In factory/dark-factory.js: after :142 assembles the three verdicts, log() one line per blocker/major finding ('severity — where — issue') and one per rework verdict, and add reviewSummary {blockers, majors, minors, rework:[labels]} to the return at :145-151. NO branching and NO fix rounds: the technical reviewer graded the one real defect 'minor', which a blocker+major gate skips by construction, while firing on verdicts elsewhere at $1.67-$6.02 per re-run implementer. log() is the point: the workflow journal survives a return-value crash, and the observed run's return did not." },
    { "key": "F2", "title": "retry a dead implementer once, then stop", "role": "deepseekPro", "kind": "backend", "dependsOn": [], "touches": ["factory/dark-factory.js"],
      "spec": "In the execution loop at :126-133: retry the implementer once when agent() returns null (T1 died on one upstream 500 at +08:07 and :132's String(out||'') hid it for 7.5 more hours). If the retry is also null, push {key, status:'failed'} into impls, log() it, and throw a plain Error when any later task lists that key in dependsOn; otherwise continue. Throw outside any parallel() thunk — a plain Error inside one is swallowed to null. Also, between tasks, assert the SESSION WORKSPACE's tree is clean and log() a warning if it is not — that guard survives F8, which puts each task's writes in its own clone elsewhere. Do NOT add a LINKED worktree: git worktree add fails under dsh's sandbox with 'Read-only file system' because its .git pointer leaves the writable workspace. F8 uses a full clone, which the same verifier measured as working." },
    { "key": "F3", "title": "deterministic dependency scheduler: waves, not array order", "role": "glm", "kind": "backend", "dependsOn": [], "touches": ["factory/dark-factory.js"],
      "spec": "Plan task F3, implementing nixos-agent-env docs/decisions/2026-09-04-parallel-agent-workflows.md on this side. dependsOn is in TASK_SCHEMA:55, never read, and execution at :126 is array order. Replace that with a hand-rolled scheduler: (1) validate the graph on entry and throw a plain Error BEFORE any dispatch on a duplicate key, a task depending on itself, a dependsOn naming no task, an unknown role or kind, or a cycle naming the keys involved (X0 already covers the dangling case; this adds cycles and duplicates); (2) compute waves with Kahn's algorithm, sorting the ready set at every step so the schedule is reproducible from the task list alone; (3) run each wave's tasks concurrently under args.concurrency (default 4 — NEVER the host CPU count, which would make the schedule machine-dependent); (4) a task whose dependency did not finish green is marked 'blocked' and NEVER run; (5) every result carries its wave number; (6) log() the entire schedule — waves, groups, concurrency, integration branch — before the first dispatch. pipeline() CANNOT do this: it is a per-item multi-stage fan-out with no barrier. Every throw sits on the dispatch path, outside any parallel() thunk. Also run the three read-only cross-reviewers at :136-141 under parallel() — that concurrency was always free. Record in the commit body a hand-run of a cyclic task list showing the throw with ZERO agents dispatched." },
    { "key": "F4", "title": "machine-set commit convention and trailer", "role": "glmFlash", "kind": "routine", "dependsOn": [], "touches": ["factory/dark-factory.js"],
      "spec": "The implementer prompt at :129-131 never mentions a commit convention: one session invented a Co-Authored-By trailer from its own identity, five copied it correctly and one (667f25d) copied it from git log and misattributed itself; b678875, the root-privilege commit, has a one-byte body and no trailer. Add to the prompt: subject '<prefix>: <summary> (test: <check names>)', a body stating the WHY, and a trailer line the script builds from the model id it is dispatching, so no model has to guess what it is. Do NOT add a commit-body gate anywhere — base rate is 1 empty body in 187 commits and pre-commit is the wrong hook (it gets no args and sees the previous message)." },
    { "key": "F5", "title": "bound the planning essays in the prompt", "role": "glm", "kind": "routine", "dependsOn": [], "touches": ["factory/dark-factory.js"],
      "spec": "The three planning prompts (:109-111) and two consolidation prompts (:115-117) carry no length bound; consolidation prompts total 125,476 chars against 9,644 for the planning prompts, and the plan-mode return overran the workflow tool's 50,000-byte inline cap at 49,481 chars, spilling to a file with specs clipped at 2,000 chars and three recovery reads. Add an explicit word cap to each of the five prompts and one sentence telling the task planner to keep each spec self-contained but under a stated length. The permitted JSON-schema subset (type/properties/required/additionalProperties/items/enum/const/oneOf) cannot express length, so this MUST be prompt-side. Do NOT replace the consolidation essays with bullet objects — they produced the plan the whole build ran on." },
    { "key": "F6", "title": "re-sync the nixos skill; fix the unresolvable prefix", "role": "glmFlash", "kind": "routine", "dependsOn": [], "touches": ["skills/"],
      "spec": "Run the README's re-sync recipe (rm -rf skills/nixos; cp -R ~/flakes/nixos-skill/skills/nixos skills/nixos) — only after that repo's gotchas task has landed. Then fix what actually dangles: the 26 'superpowers:'-prefixed references resolve to 10 present directories, but dsh's skill-name pattern forbids a colon, so map 'superpowers:X' to bare 'X' at all 26 occurrences; and rewrite the four Claude-plugin-relative paths inside skill bodies. Do NOT add a frontmatter or existence check: 15/15 files are valid and 10/10 names resolve, so such a check finds nothing." },
    { "key": "F8", "title": "a persistent isolated clone per task, and deterministic integration", "role": "deepseekPro", "kind": "backend", "dependsOn": ["F3"], "touches": ["factory/dark-factory.js"],
      "spec": "Plan task F8, resolved 2026-09-04 as O11 option 1. Per-task isolation the dsh sandbox allows: a factory root at args.factoryRoot (default $HOME/factory), a directory DECLARED BY THE HOST CONFIG outside every git repo (nixos-agent-env N11) — NOT a gitignored path inside this repo; add no .gitignore entry. Before any dispatch, the baseline agent (already run first, to set the integration tip) also verifies factoryRoot exists and its own cwd is factoryRoot or a descendant of it; the script throws on either failing, before any implementer is dispatched. One base clone per repo the run touches, refreshed from that repo's real HEAD at run start: git clone --local ~/flakes/dsh-harness <factoryRoot>/base/dsh-harness (fetch+reset if it already exists, never re-clone over it). Each task's implementer prompt tells it to run `git clone --local <factoryRoot>/base/dsh-harness <factoryRoot>/ws/<run-id>/<taskKey>` (run-id a timestamp the script generates once at start) and then `git checkout -B <taskKey> <integrationBranch>` — a full checkout (so nix build / nix flake check can run in it and the flake sees tracked files), created at the moment its wave starts, so a dependent task's workspace already holds its dependencies' merged work. One branch per task key; the implementer commits ONLY there and never merges. Workspaces PERSIST until the run ends and every path is listed in the return value as tasks[].workspace and tasks[].branch, for post-mortems; the script deletes nothing (retention past the run is manual, per N11's runbook note). After each wave, one integrator agent working in a dedicated clone at <factoryRoot>/ws/<run-id>/integration merges that wave's branches in topological-then-key order with `git merge --no-ff`, pulling each with `git fetch <factoryRoot>/ws/<run-id>/<taskKey> <taskKey>:<taskKey>`, then runs the wave's declared checks plus lint on the merged tree — TODAY that is only `node --check factory/dark-factory.js`, because this repo has no flake, githooks or tests (F7); say exactly that in the log line rather than printing a green that means little. On a merge conflict or a red check: EXACTLY ONE bounded fix agent (deepseekPro) in a fresh clone under the same ws/<run-id>/ tree, handed the conflict or check output verbatim; if it is still red the chain stops — mark that wave's tasks 'integration-failed' and every dependent 'blocked'. No loop; this mirrors F2's retry-once rule. DELIVERY: do NOT merge into ~/flakes/dsh-harness's own branch. Leave the integration branch and print the recipe `cd ~/flakes/dsh-harness && git merge --ff-only <integrationBranch>` for the orchestrator — the crossing between the two lanes stays a reviewed diff. A LINKED worktree is not an option here: git worktree add fails under this sandbox with 'Read-only file system'. Needs N11 switched first (nixos-agent-env, folded into that repo's O8) — factoryRoot must already exist." },
    { "key": "F9", "title": "touches/parallelSafe annotations, and a judge only where they are missing", "role": "glm", "kind": "backend", "dependsOn": ["F3"], "touches": ["factory/dark-factory.js"],
      "spec": "Plan task F9. TASK_SCHEMA (:40-62) gains `touches` (array of repo-relative paths or globs the task will WRITE) and optional `parallelSafe` (bool). The task-planner prompt is told, in one sentence, to emit touches for every task it plans, with the reason: a missed path means two agents writing one file. The scheduler then applies a DETERMINISTIC overlap check inside each wave — compare the literal prefix of each touches entry (everything before the first glob metacharacter) at a path boundary — and serialises overlapping tasks in key order within the wave, printing the reason as a schedule note ('serialised: F1, F2 (touches overlap)'). Group by CONNECTED COMPONENTS of the overlap graph, NOT by graph colouring: colouring packs non-conflicting tasks into one sequential lane, the opposite of the goal. The LLM judge (deepseekPro) is consulted ONLY for a task with no touches and no parallelSafe:true; ask it for the paths that task will write; record its answer in the schedule output and log() it next to the tasks it moved; args.judge=false disables it, and then an un-annotated task serialises with everything in its wave. The judge NEVER overrides an explicit touches and never decides anything that is not printed." },
    { "key": "F7", "title": "document the repo that hosts the factory", "role": "glm", "kind": "routine", "dependsOn": ["F3", "F4", "F8", "F9"], "touches": ["README.md", "AGENTS.md"],
      "spec": "README.md documents the args.tasks contract verbatim AS IT STANDS AFTER F3/F8/F9 ({key,title,role,kind,spec,dependsOn,touches,parallelSafe}; the five roles; the four kinds; that a malformed graph — duplicate key, dangling or cyclic dependsOn, unknown role or kind — throws before ANY dispatch; that args.concurrency defaults to 4 and args.judge to true; that each task runs in its own clone under args.factoryRoot, default $HOME/factory, a directory declared by the host config outside every git repo (nixos-agent-env N11) and never a gitignored path in this repo, and commits on a branch named by its key; that the run refuses before dispatch if factoryRoot is missing or its own cwd is not under it; and that the run leaves an integration branch for the orchestrator to fast-forward rather than merging it itself), the launch requirement (launch the seat from ~/factory), and a commit convention for this repo (subject, a body with the WHY, a trailer). Disambiguate AGENTS.md's 'dark-factory.js' bullet: there are two same-named scripts and the Claude-side one still uses sonnet/opus/fable roles, so the bullet is ambiguous rather than false. Do NOT package skills/ as a flake in this task — that is deferred by decision; note in the README that when it is done, ownership belongs in the wrapper or the --patch overlay's customSkillDirs, not home-manager." }
  ]
}
```

## §C — Operator actions (not assigned to agents)

Each names the artifact that closes it. Nothing here is a task an agent can run: they need account access, a browser, a live switch, or a budget decision.

| # | Debt | Action | Artifact that settles it |
|---|---|---|---|
| O1 | **D7** | Open the OpenRouter account settings and confirm whether zero-data-retention and training opt-out are on; record the date. | A board line: "account ZDR = on/off, training opt-out = on/off, checked YYYY-MM-DD". Still OPEN on the board today. |
| O2 | **D5** | Export the OpenRouter activity for 2026-09-03 → 2026-09-04 and save it as `~/strategy/ledger/openrouter-activity-2026-09-04.csv`. | That CSV. It replaces the report's $23.73 price-table estimate and feeds `factory.py rollup --costs` (N6). Three sessions used another provider — note them. |
| O3 | — (gates N3's host half) | Determine whether OpenRouter honours a `provider` block on `/api/v1/messages` (docs, support, or one hand-sent request). | A board line: honoured → set `patchMessagesPath = true`; not honoured → deny that path instead of patching it. |
| O4 | **D1** | After N2 lands and the switch, frame `http://localhost:7700` from a cross-origin page in Firefox and try to click through; note whether Firefox lets a public page frame a loopback origin at all. | A board line: framed/blocked, before and after N2. |
| O5 | **D4 (contested)** | Re-run Helm acceptance step 8 and capture the spawned Console child's stderr (the fix `0e727ba` blames the user manager's PATH, but a live probe shows `systemd --user` *does* carry `/run/current-system/sw/bin` and the journal shows `kgx` spawned a child). | The child's stderr, pasted into the measurements record. A `--dry-run` will not do — it resolves the bare names fine and would have passed the failing generation. |
| O6 | **D10** | After X0 lands, run one plan→build against the fixed script and report agents, wall clock and tokens. | The run's journal plus a board line. The broken handoff has never been exercised, so H9's cost is projected, not measured. |
| O7 | **D8** | Decide whether to fund a paired factory run (same task list, review gate on and off). | A yes/no on the board. Until then the effect of the review gates is untested in both directions. |
| O8 | — | Switch after the round lands (this also brings up N11's `/home/dalhaka/factory{,/base,/ws}` tmpfiles rules — the declared dsh factory root F8 needs before its real run): `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core`, then re-run `tests/acceptance/helm-v1.sh`. | The acceptance verdict. |
| O9 | — | Relaunch the dsh seat after N1 and N7 land. | Nothing takes effect in a running session: `OPENROUTER_MODELS`, `XDG_CACHE_HOME` and the hook config are all consumed at launch. |
| O10 | **new — closes the parallel decision's acceptance 1** | After N10 lands, run one Claude factory run whose task list has ≥2 tasks with no `dependsOn` edge and no `touches` overlap, and read the per-agent start/end stamps from the run journal. | A board line: implement-phase wall clock vs the sum of those tasks' single-task wall clocks, plus "every declared check + lint green on the merged tree: yes/no". Both halves must hold. Until this exists, the wall-clock gain is dated debt, not a fact. |
| O11 | — | **Resolved 2026-09-04: declared root `~/factory`, N11.** | — |

## Deliberately left out, with reasons

- **H1, H2, H3, H5, H6, H7, H10, U1, U3, U4, U5, U8 as stated** — refuted 2-1 or 3-0. Their surviving kernels are carried where a verifier upheld them: H1→F2, H2→F1, H5→N5+S1, H7→F2 (a null child is a hard failure, not a preflight — `OPENROUTER_MODELS` is consumed at launch), H10→N6+O2, U1→F2's clean-tree assertion **and** F8 (its feasibility half — linked worktrees break under dsh's sandbox, ordinary clones commit fine — is exactly what F8 is built on), U3→N2's argv bullet, U4→F4's trailer, U5→F6+F7, U8→N7's deny-only guard.
- **A step budget or repetition guard (H3)** — reasoning is ~$2.34 of $23.73, a trip tight enough to fire would have cut the expensive session before its first edit at step 78 of 157 and forfeited the commit, and the workflow realm has no per-step seam.
- **Unifying the `/tmp` namespaces (H5)** — removes containment for model-authored shell commands; documented instead.
- **A repo index for agents (H6)** — the largest read slice is the run's own plan/spec prose (39.9%), which no derivation computes; H9's restored `spec` is the fix.
- **Packaging the dsh payload as a flake (U6 step 2)** — deferred by decision; N1's warning takes the measured gain, and the rollback half needs home-manager or activation scripts, neither of which exists here.
- **A *linked* git worktree on the dsh side (U1)** — `git worktree add` reproducibly fails under dsh's `workspace-write` sandbox with `Read-only file system`, because the worktree's `.git` pointer lands outside the writable workspace (U1 vote 3). That refutation is why F8 uses a **full clone** instead, under `args.factoryRoot` (default `~/factory`) — a directory declared by the host config outside every git repo (N11, resolving O11), not a gitignored path inside `~/flakes/dsh-harness`: a clone inside a checkout is a nested repo git cannot track cleanly, flakes copy every tracked file into the store on each evaluation, and untracked files break the clean-tree assertion — a declared root removes all three. The same U1 vote measured that "an ordinary clone commits fine". The clean-tree assertion (F2) stays as the cheap guard on the *interactive seat's* own checkout of `~/flakes/dsh-harness`, which remains the live tree by decision — F8's per-task clones are elsewhere, under `~/factory`.
- **`lane-shell` inside the broker netns (U8)** — measured fail-open: a `systemd --user` unit with `NetworkNamespacePath=` starts successfully and stays in the *host* namespace. Needs a system unit and a privileged entry path; out of scope.

## Self-review

Spec coverage: H9→X0; H4→N1; U7→N3; U2→N2; U6→N1(step 1)+F6/F7(step 2 deferred); hooks bridge→N7; discarded verdicts→F1; T1's unretried 500→F2; `OPENROUTER_MODELS` default→N1; commit hygiene→F4 (and the explicit refusal of a body gate, N9); the `/tmp` + cache gotchas→N5+S1; the cost ledger→N6 extending lane-l T1 (checked: that plan's T1 exists and is open — extended, not duplicated); D1→O4, D2→N2, D3→N3, D4→O5, D5→N6+O2, D6→N4, D7→O1, D8→O7, D9→N8, D10→O6.

Second spec, added 2026-09-04: `docs/decisions/2026-09-04-parallel-agent-workflows.md`. Its three mechanisms map to N10 (all three, Claude side) and F3 (scheduler) + F8 (workspaces and integration) + F9 (annotations and judge) on the dsh side; its acceptance 1 is O10 and its acceptance 2 is `factory-unit` scenario 7 here and F3's hand-run there; its "known cost" paragraph is the §B preamble's honest note that eight of nine dsh tasks write one file and gain no wall clock. The 7.7 h sequential fan-out now maps to F3+F8, not to F3 alone.

Names used consistently across tasks: `pathPrefixes`, `inject.<host>.paths`, `patchMessagesPath`, `hook-guard.py`, `DSH_HOOK_GUARD`, `DSH_HOOK_DENIAL_LOG`, `extract-dsh`, `dsh-sessions.jsonl`, `reviewSummary`, `docs/reviews/2026-09-04-dsh-debt-measurements.md`, and for the scheduler: `dependsOn`, `touches`, `parallelSafe`, `args.concurrency`, `args.judge`, `args.integrationBranch`, `validateGraph`, `computeWaves`, `groupWave`, `integrateWave`, `INT_BRANCH`, statuses `blocked` / `integration-failed`, labels `judge:<key>` / `integrate:w<N>` / `integfix:w<N>` / `deliver`, and the return keys `schedule` / `integrations` / `integrationBranch` / `delivered` / `tasks[].wave` / `tasks[].branch` / `tasks[].workspace` / `tasks[].blockedBy`. Every task names a red test that fails today and the reason it fails; the two that cannot have one (X0, which repairs the vehicle, and N8, which is a measurement) name a hand-run verification instead.

Type-consistency check on the new surface: `IMPL_SCHEMA` gains `workspace`/`branch` in N10 and F8 uses the same two names; `INTEGRATE_SCHEMA`'s `{merged, conflict, checks_green, head, output}` is produced by the wave integrator and consumed by the bounded fix agent in the same task; the judge's `{touches, reasoning}` is the same shape on both sides. `flake.nix` is written by N3 and N6 only — N10 is explicitly told not to touch it, which is what keeps wave 1's `{N3→N6}` group from becoming a three-way.
