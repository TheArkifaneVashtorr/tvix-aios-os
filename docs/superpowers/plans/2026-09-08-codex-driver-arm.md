# The `codex` arm of the seat driver — plan (2026-09-08)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) and `tools/factory/dark-factory.js` both read the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and `commit subject`. A seat sees only `## Global Constraints`, `## Assumptions` and its own section (`tools/factory/seat/factory-brief <plan> <KEY>` is the whole contract).

**Goal:** a Codex run is a row in `derived/tasks` like every seat's — the same brief, the same `FACTORY-RESULT` grammar and demotions, a `.result` the ingest reads unchanged, the session's own token counters — so `evidence tasks brief` shows DeepSeek and Codex side by side, and the first Codex task on `~/flakes/codex` lands through the driver, not around it.

**Spec:** `docs/superpowers/specs/2026-09-08-codex-driver-arm-design.md` (1,499 words, size S; the operator's word 2026-09-07 ~18:55 and `docs/decisions/2026-09-07-codex-stays-an-operator-app.md` point 4). Where this plan's mechanism differs from the spec's wording, the section says so and pastes the fact that forced it (three places: the usage script's tests, the repos row, the fence as its own task — §Decisions D1–D3).

**Packet of record:** `plan-codex-arm/packet/{mechanical,record,field,operator,target}.md` (2026-09-07 19:42 CDT); the tree at `c8ee24475ebf4c9c651165b51b699dd59261a277` (`git log -1 --format='%H %s'` → `… docs: spec — the codex arm of the seat driver (FACTORY_SEAT=codex, the launch of record, the .result and usage from the rollout, the fence, the trailer, the brief's Seats line) (test: lint)`); `tasks.py --root . check` empty (M1, `EXIT:0`, `checkEmpty: true`); live generation 45 = a53d2e5, HEAD c8ee244 (M6).

## Operator questions (each answerable in one word; the default applies if unanswered)

1. **`Co-Authored-By: Codex CLI <ver> <noreply@openai.com>` on Codex commits (spec item 7, spec Q1)?** Fact: CX1b's five commits already carry it — `git -C ~/flakes/codex log -5 --format='%(trailers:only)' | sort -u` → `Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>`; `CLAUDE.md`'s Fable trailer is this repo's rule, and every Codex commit lands in `~/flakes/codex`. **Recommendation: yes** — the trailer names the author and the flake's history stays uniform. **Default: yes.** A naming convention (`docs/board/operator-model.md`: names are the operator's); no invariant.
2. **`route: codex/<kind>/<size>` rather than the bare `codex` (spec items 1, 3, 6, spec Q2)?** Fact: the ingest derives `task_kind` and `size` from the route line — `sed -n '74,84p' pkgs/evidence/ingest_result.py` → `def _route_fields(route_line):` … `m = ROUTE_IMPL_RE.fullmatch(route_line)` / `if m:` / `return route_line, m.group(1), m.group(2)` / `return "unknown", "unknown", "unknown"` — so a bare `codex` would leave every Codex row `unknown/unknown` in each `report harness` group. **Recommendation: yes.** **Default: yes.** An A/B on a data shape; no invariant.

Decided in the plan (§Decisions), for the operator to veto: the spec's CA1 split into CA1 (the driver) and CA3 (the fence); the usage script's tests in bats; the `repos.toml` row in the plan's own commit; no dependency on SD2–SD4; the brief-time `<model>`; the banner window; the Seats line's plural and median; CX2's probes and its size S.

## Spec-to-task map

| spec item | task or `out:` |
|---|---|
| 1 Selection — `FACTORY_SEAT=codex` before the `seat-submit` test; unset/empty byte-identical; any other value exit 2 before a workspace or run dir; `factory-wave`/`factory-dispatch` pass the environment through; `factory_route` not called | CA1 (the `case` guard; the pass-through pinned by a `factory-wave` row; `FACTORY_ROUTING_TABLE=/nonexistent` proves the lookup is skipped) |
| 2 The launch — the exact `codex exec` line, cwd the clone, the brief on stdin, `timeout`, `--model` → `-m` and `route: explicit`, the two `OPENROUTER_*` warnings, no `DSH_HOME`, exit 124 → `timeout` | CA1 |
| 3 The `.result` — `model:`/`effort:` from the banner, then `~/.codex/config.toml`, then `unknown`; `route: codex/<kind>/<size>`; `seat: codex <session id>` | CA1 |
| 4 Usage — `factory-codex-usage.py`, the rollout by session id, else newest-since-marker, else `{}` | CA1; its tests are bats rows in `tests/unit/95-codex-arm.bats`, not `tests/evidence/test_codex_usage.py` (D1: `checks.evidence-unit` copies `pkgs/evidence` and `tests/evidence` only) |
| 5 Error class — `factory_error_class` unchanged, fed the agent's output only | CA1 (the copy from the first line exactly `codex`, else after the banner's second `--------`); Codex's own failure strings: `out:` unmeasured — the gap row `codex-failure-strings-unmeasured` opens in the plan's commit (§Dispatch step 0; A8) |
| 6 The fence — `ROUTE_IMPL_RE`, the stream regex, `SCHEMA.md`, the CX1b-shaped fixture | CA3 (its own task: no file shared with CA1, so it runs beside it — D2) |
| 7 The trailer — `Generated-By: codex-cli <ver> / <model> (codex exec, factory run <RUN>)`, `Co-Authored-By: Codex CLI <ver> <noreply@openai.com>`, `<ver>` from `FACTORY_SEAT_VERSION`, byte-identical without `FACTORY_SEAT` | CA1 (`factory-brief`; `FACTORY_SEAT_VERSION` from `codex --version` in `factory-task`) |
| 8 Side by side — the `**Seats (7 d):**` line | CA2 |
| 8 Side by side — `docs/ledger/repos.toml` gains the `codex` row | the plan's own commit, not CA2 (D3: `tasks.py check` refuses a `**repo:** codex` section until the row exists, and this plan's CX2 carries that line) |
| Tasks: CA1 (items 1–7) | CA1 + CA3 (D2) |
| Tasks: CA2 (item 8) | CA2 |
| Tasks: CX2 (`repo: codex`, dependsOn CA1; MINOR-1, -3, -4, -5; run through `factory-wave`; gated by `~/factory/bin/opus-gate.js`; landed by `factory-integrate`) | CX2 (dependsOn CA1, CA3 — the row it writes must pass the fence) |
| Invariants touched — brief §3 binds agents; `danger-full-access` accepted by the operator; no key moves; no Nix expression change; the closure diff stays one line | §Global Constraints (where §3 binds), §Operator step 3 (the closure line as a prediction, measured on the landed tree) |
| Waves, touches, conflicts — [CA1 ‖ CA2] → [CX2]; conflicts with SH4/SH5 and SD2–SD4; dispatched after SH6 | §Waves (computed on the scratch copy; the SH edges are `dependsOn`, so the dispatcher itself holds the wave — D4) |
| Operator steps: none | §Operator (no switch, no unit, no key; the acceptance and rollback commands) |
| Questions 1–2 | §Operator questions |
| Risks — `danger-full-access`; a run editing outside the workspace; the rollout format drifting | §Anticipation A5/A9; CA1 rows 10, 17c (events 0 → `boot-failure`; the script never raises) |
| Not in this spec — a `route = "codex"` row, per-task mixing, the ladder, Codex under the lane or broker, Codex on core | §Not in this plan |

Every task traces back: CA1 → items 1–5, 7; CA2 → item 8; CA3 → item 6; CX2 → the spec's CX2 paragraph.

## Decisions (judgement calls, each with the reason and the alternative)

- **D1 The usage script's tests are bats rows, not `tests/evidence/test_codex_usage.py`.** Fact: `sed -n '1131,1150p' flake.nix` → `evidence-unit = pkgs.runCommand "evidence-unit"` … `cp -r ${self}/pkgs/evidence pkgs/evidence` / `cp -r ${self}/tests/evidence tests/evidence` / `cp -r ${self}/docs/decisions docs/decisions` — `tools/factory/seat` is never copied, so a pytest there could only skip (the P8b MAJOR-1 shape: a skip in the sandbox is a green that proves nothing). `checks.unit` has what the script needs: `sed -n '2000,2043p' flake.nix` → `nativeBuildInputs = [ pkgs.bats … pkgs.python3 … pkgs.git ]` and `cp -r ${self}/tools/factory/seat tools/factory/seat`. Alternative rejected: adding a copy line to `evidence-unit` — a `flake.nix` edit the spec forbids ("no Nix expression changes") and a collision with SB6/SD5/SD6.
- **D2 The fence is its own task (CA3).** It shares no file with CA1 (`streams.py`, `ingest_result.py`, `SCHEMA.md`, two pytest files, one fixture against `factory-task`, `factory-brief`, the usage script, one bats file, the README), so the two run in one wave; one gate per concern. Alternative: the spec's single CA1 — a rejection on either half sends both to a fix round.
- **D3 The `repos.toml` row rides the plan's own commit.** Fact: `sed -n '1214,1220p' pkgs/evidence/tasks.py` → `# a **repo:** naming a repo repos.toml does not configure is a silent` / `# disappearance (the task leaves every graph); refuse it here.` / `for key, value in repo.get("attributed", []):` / `if value not in configured:` / `errors.append(f"tasks: {name}/{key} repo: {value} not in docs/ledger/repos.toml")`, and `sed -n '60p' githooks/pre-commit` → `python3 pkgs/evidence/tasks.py --root . --repos "$repos_file" --runs-dir /nonexistent --store /nonexistent check` — the plan's commit carries `**repo:** codex` (CX2), so the hook refuses it until the row exists. The row is one `[[repo]]` block the orchestrator writes (`docs/ledger/repos.toml` is the orchestrator's ledger, landed by hand as G3). Alternative: CA2 adds the row as the spec says and CX2 is typed later by hand — the spec's "lands through the driver, not around it" loses its first task.
- **D4 Sequencing is `dependsOn`, not a sentence.** CA1 names SH4 and SH5 (both edit `factory-task`; SH5 edits `factory-brief`), CA3 names SH4 and SH5 (both edit the fence, the ingest, the schema and their tests), CA2 names SH5 (`tasks.py`, `test_tasks.py`); every task names P11 through that chain (SH2 → P11) — the deterministic guards of A5. `factory-dispatch` asks the graph for the next wave, so it prints `nothing schedulable` until SH4 and SH5 land: the spec's "dispatched only after SH6 lands" is held by the dispatcher (SH6 shares no file with this plan; if it runs beside CA1 nothing collides). SD2–SD4 (the ladder, `out` of this spec, `blocked`/`ready` behind SD1 — packet M2) are **not** in `dependsOn`: the driver has no cross-plan collision guard, so the rule is §Dispatch's launch pre-check and A1 step 2 (whichever lands second merges main first); the guard itself is parked in §Not in this plan. Alternative: `dependsOn` SD2–SD4 — the codex arm waits for a held plan the spec excludes.
- **D5 The brief's `<model>` under codex is the `--model` value, else the top-level `model` of `${CODEX_HOME:-$HOME/.codex}/config.toml`, else `unknown`.** The banner (spec item 3's first source) exists only after the launch; the brief is printed before it. Today: `grep -n '^model\|^model_reasoning_effort' ~/.codex/config.toml` → `1:model = "gpt-6-astra"` / `2:model_reasoning_effort = "medium"`, so the trailer reads `codex-cli 0.153.4 / gpt-6-astra`. The `.result`'s `model:` keeps the spec's order (banner → config → `unknown`).
- **D6 The banner is a window, not a grep.** The echoed brief follows the banner (`user` + the prompt), and a brief can contain `model:` or `session id:` lines (this plan's own sections do). The three fields are read only between the first two lines that are exactly `--------`. Alternative: the last match — the seat's own reply would win.
- **D7 The rollout is found by the banner's session id when there is one; only without an id by the newest file newer than the launch marker.** Two Codex tasks in one wave never share an id; a newest-file fallback beside a valid id could return a sibling's rollout. A valid id whose file is missing is logged and reports `{}` (events 0 → `boot-failure`), the spec's drift arm.
- **D8 The Seats line prints `1 run` / `2 runs`, the wall as `median_low` seconds rounded to minutes ((m + 30) // 60), `? min` when no `wall_s:` is an integer, `billed` as the sum of the `usage:` JSON's `input` + `output`.** The spec's `<n> runs` is a shape, not a byte; `median_low` keeps the value one real run had; integer arithmetic avoids Python's round-half-even. Alternative: the arithmetic mean — one killed run of 3 h would dominate.
- **D9 CX2's precedence proof is two probes.** (a) The overlay probe: the user file sets every hardened key to a value its type rejects (`plugins = "yes"`, the three `otel.*_exporter = "bogus"`); under the managed layer the run reaches the banner (the managed value replaces the user's before deserialisation); the same bytes at `/etc/codex/config.toml` (the layer that loses — the review's own measurement) print no banner. The negative control is wired into the check so the probe is shown to fail. (b) The effective-value probe for `features.plugins`: the `plugins` line of `codex features list` under the same environment, pinned to its measured text; the module mutant `features.plugins = lib.mkDefault true` (the review's surviving M3b) flips it. The otel keys have no runtime observable the CLI prints; their effective values stay Nix-asserted by `module-eval` and the gap is written into `docs/VALIDATION.md` (amendment 2: unmeasured is debt, declared). Alternative: one setting more of the network kind — the review's finding was the coverage class, not the count.
- **D10 No check dials `api.openai.com`: the provider base URL is redirected to a closed loopback port (`OPENAI_BASE_URL=http://127.0.0.1:9`) in every run the three scripts make, and each script asserts the string `api.openai.com` is absent from its report.** Assumption 8 names the override and its falsifier. Alternative: `bwrap --unshare-net` for all three — the URL still appears in the report (the review's log line), so nothing can assert it.
- **D11 `factory-lib.sh` is not touched.** The config reader is a function inside `factory-task`; SD1–SD4, SH4 and SH5 all edit `factory-lib.sh` (packet M5), and the arm needs nothing shared.
- **D12 CX2 is size S, not the spec's XS.** Four review items, one new test script, one new check, three edited scripts and three edited documents — one commit, one gate.

## Global Constraints

- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown, no reading `/var/lib/secrets/*`, `~/.config/openrouter/key`, `~/.config/restic/password`, and never `~/.codex/auth.json`. Never launch a seat (`tools/factory/seat/factory-task`, `factory-wave`, `factory-dispatch` without `--dry-run`, `seat-submit`, `dsh-openrouter`, a real `codex exec`): every driver behaviour in this plan is tested with fakes on `PATH` (a fake `codex`, a fake `dsh-openrouter`, `FACTORY_EVIDENCE_CMD`, `FACTORY_PYTHON3_CMD`), the idiom `tests/unit/80-seat-driver.bats` and `94-seat-harness.bats` use. Brief §3 invariants 2 and 3 bind agents; a Codex run under `--sandbox danger-full-access` runs on the host with the operator's rights outside the seat lane and the broker — accepted by the operator for Codex (decision 2026-09-07, point 4). No task here widens that: no key moves, no Nix expression on core changes, no new network path.
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`), exactly one commit on `task/<KEY>`; `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null` a gated command. The commit subject is the section's `commit subject` byte for byte; the trailers are the WORKSPACE RULES' two lines, each on its own line after a blank line.
- TDD: the failing check first, shown red, then green. A load-bearing test counts only once it has been shown to fail; a test that cannot fail is a `vacuous-test` major finding. Every table row below names the one-line mutant that turns it red; land the test, run it red, paste the red line in the commit body, then land the change. Where a behaviour already exists (CX2's precedence rows), the red is the named mutant, run and pasted. Every proxy names what it stands in for and its gap (`docs/decisions/2026-09-03-test-based-reality-amendments.md`).
- **`touches` is a contract.** A file outside the section's `touches` is a deviation: name it in the commit body on its own line as `Deviation: <path> — <reason>`; the driver recomputes the branch diff after you exit and the integrator refuses an undisclosed extra. Two files are always exempt in `~/nixos-agent-env`: `docs/MAP.md` (regenerate it with `python3 pkgs/evidence/repomap.py --root . write` whenever you add a file) and the `<!-- tasks:begin -->…<!-- tasks:end -->` queue block of `docs/OPERATIONS.md`, which the pre-commit hook rewrites; never edit `docs/OPERATIONS.md` outside that block.
- Bats: one `[ … ]` per line, never `] && [` (`tests/lint/bats-and-chain.sh` is part of `lint`); no test may exec a driver through its shebang — hand `"$REAL_BASH" "$SEAT/<script>"` as `80-seat-driver.bats` does (the sandbox has no `/usr/bin/env`); every test runs under `FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"` and never touches `~/factory`, `~/.codex` or the network. Bash in `tools/factory/seat/*` is shellchecked by name; a new Python file under `tools/factory/seat` is covered by the existing `ruff check tools/factory/seat` list — no list edit.
- Python is stdlib only in `pkgs/evidence` and `tools/factory/seat`; `ruff format` (88 columns) rewraps every block below — a reformatting-only difference from the plan text is not a deviation. Run `nix develop -c ruff format <the files you wrote>` after writing.
- The result block's exact form ends your final reply: `FACTORY-RESULT status=done|partial|failed` — a space and no colon; `FACTORY-CHECKS <name>=<pass|fail|not-run> …` naming exactly the section's acceptance checks; `FACTORY-COMMITS <n>` equal to `git rev-list --count <base>..task/<KEY>`; `FACTORY-NOTES` one line, never a bare `ok`. Never copy the WORKSPACE RULES or the result template into a project file.
- Nix style: statix rejects `{ ... }:` headers; nothing in CA1–CA3 edits a `.nix` file. CX2 edits `~/flakes/codex/flake.nix` only (its own flake; formatted by that flake's `nix fmt`). Claude agents never write inside `~/flakes/dsh-harness`.
- **CX2 works in its clone of `~/flakes/codex` only.** Its checks are that flake's (`nix build .#checks.x86_64-linux.<name> -L --no-link` works there); its devShell has no shellHook, so run `git config core.hooksPath githooks` once before the first commit (the hook runs `nix fmt -- --fail-on-change` and `nix flake check`); its Markdown is formatted by prettier and linted by markdownlint with MD013 off.
- No secrets in the repo; no fixture may quote a key, token or a path under `/var/lib/secrets`; every string the store ingests is fenced (`streams.SECRET_RE`); a fixture session id is a made-up UUID, never one from `~/.codex/sessions`.

## Assumptions

1. The unit sandbox (`checks.unit`, `sed -n '2000,2043p' flake.nix`: `pkgs.bats`, `dshOpenrouter`, `pkgs.python3`, `pkgs.zstd`, `pkgs.git`; no `nix`, no `codex`) copies `tests` whole (`cp -r ${self}/tests tests`, so a fixture under `tests/unit` needs no list edit), `tools/factory/seat`, `pkgs/evidence`, `docs/ledger`, and runs `bats tests/unit`; a new `tests/unit/95-codex-arm.bats` runs there with no `flake.nix` edit. `FACTORY_PYTHON3_CMD="$(command -v python3)"` is the sandbox seam for the usage script (`factory_py`, `sed -n '70,80p' tools/factory/seat/factory-lib.sh`); `FACTORY_EVIDENCE_CMD` stands in for the evidence CLI (`factory_ingest_result`, `sed -n '159,166p' tools/factory/seat/factory-lib.sh`). `timeout`, `find`, `awk`, `sed`, `realpath` and `sleep` are coreutils/gawk on the sandbox PATH.
2. The evidence sandbox (`checks.evidence-unit`) runs `pytest tests/evidence -q` over a copy of `pkgs/evidence`, `tests/evidence`, `docs/ledger` (the plan-defect ledger pinned to the frozen seed), `docs/superpowers/plans` and `docs/MAP.md`; `git` is on its PATH; `EVIDENCE_STORE` is honoured by every reader and writer and tests never touch `/var/lib/evidence`.
3. The Codex banner (spec, measured 2026-09-07 19:40 with `codex exec … --color never … -`, exit 0) is: `OpenAI Codex v0.153.4`, `--------`, `workdir: …`, `model: gpt-6-astra`, `provider: openai`, …, `reasoning effort: medium`, …, `session id: <uuid>`, `--------`, then `user` and the prompt echoed, `codex` and the reply, `tokens used`, a count. `codex --version` prints `codex-cli 0.153.4` (the CX1b review's Facts measured). `codex` on this host is `/home/dalhaka/.local/bin/codex` (`command -v codex`), the self-updating operator app.
4. The rollout (`${CODEX_HOME:-$HOME/.codex}/sessions/YYYY/MM/DD/rollout-<ts>-<session id>.jsonl`; on this host `find ~/.codex/sessions -maxdepth 3 -type d | head -3` → `…/sessions`, `…/sessions/2026`, `…/sessions/2026/09`; 237 files; a name is `2026/09/07/rollout-2026-09-07T14-56-54-<uuid>.jsonl`) is one JSON object per line, `{"timestamp": "<RFC3339>", "type": "<kind>", "payload": {…}}`: `session_meta` first; one `turn_context` whose payload carries `model` and `effort`; `event_msg` lines whose `payload.type` is `token_count` and whose `payload.info.total_token_usage` is the cumulative `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_output_tokens` — CX1b's last: `1710988, 1642368, 13584, 3631` over 239 lines (the spec's `jq 'select(.payload.type=="token_count") | .payload.info.total_token_usage' <rollout> | tail -1`); `payload.info` may be `null`. The seat cannot read `~/.codex` (SB7 put it in the three local-only refusal lists), so the fixture in CA1 is the contract; the first real run's `usage:` line (`events` > 0, `input` > 0) is the measurement, and a zero line on a run that reached the reply is the drift the field lesson names — re-check the key path with `jq -c 'select(.type=="turn_context") | .payload | keys' <rollout>` (the orchestrator's command, never the seat's).
5. `~/.codex/config.toml` is top-level TOML with `model = "gpt-6-astra"` and `model_reasoning_effort = "medium"` (`grep -n '^model\b\|^model_reasoning_effort' ~/.codex/config.toml`, 2026-09-07); `/etc/codex/managed_config.toml` is not rendered on core (decision point 1), so the driver reads the user file only. `CODEX_HOME` overrides the directory for both the config and the sessions (the CLI's own variable; tests set it under `$BATS_TEST_TMPDIR`).
6. `printf '%s\n' "$brief" | timeout -- "$timeout_s" codex …` inside `( cd -- "$ws" && … ) 2>&1 | tee -a -- "$log"`: `factory-task` runs `set -euo pipefail` (`sed -n '25p' tools/factory/seat/factory-task`) and switches `set +e` around the launch, so the outer `PIPESTATUS[0]` is the subshell's status = the inner pipeline's last non-zero status, i.e. `codex`'s (124 under `timeout`); `printf`'s own EPIPE status is masked whenever `codex` exits non-zero. Codex reads the whole prompt from stdin before replying (spec: "the prompt from stdin with `-`").
7. `tasks.py`'s `--runs-dir` defaults to `~/factory/runs` (`sed -n '104p' pkgs/evidence/tasks.py` → `DEFAULT_RUNS_DIR = os.path.expanduser("~/factory/runs")`); the lint check and the pre-commit hook pass `--runs-dir /nonexistent`, so the Seats line is `none` there and the board block never carries it (`render_board_block`, `sed -n '1589,1605p' pkgs/evidence/tasks.py`, prints only the next wave-1 keys and calls nothing in `render_brief`).
8. CX2 (Codex CLI 0.153.4) — **corrected 2026-09-08 ~03:40 by CX2's `partial` and the orchestrator's probes on core** (the original text assumed an `OPENAI_BASE_URL` override and a pre-deserialisation overlay; both were falsified — a wrong-fact of this plan, not the seat's): (a) `OPENAI_BASE_URL` is NOT honoured by the websocket endpoint (`url: wss://api.openai.com/v1/responses` with the env set), and the built-in `openai` provider cannot be overridden (`model_providers contains reserved built-in provider IDs: `openai``); a custom provider IS honoured — a user config with `model_provider = "loop"` and `[model_providers.loop] name = "loop"`, `base_url = "http://127.0.0.1:9"`, `wire_api = "responses"` prints `provider: loop` in the banner, then `ERROR: Reconnecting... waiting for network` until `timeout`, and the report never mentions `api.openai.com` (0 matches; without the provider ≥ 1). (b) The managed layer is applied after each file is parsed: under `exec`, a wrong-typed user value (`plugins = "yes"`) is `invalid type: string "yes", expected a boolean` whatever the managed file says; with VALID conflicting values the managed layer wins — `codex features list` under bwrap with a managed `plugins = false` against a user `plugins = true` prints `plugins                                  stable             false`, and the `exec` banner with a managed `network_access = false` against a user `true` prints `sandbox: workspace-write [workdir, /tmp, $TMPDIR]` without `network access enabled`. (c) The otel keys have no runtime observable and no valid bare-string alternative to `"none"` (`exporter = "otlp-http"` fails to load: `invalid type: unit variant, expected struct variant`) — their precedence is asserted at the Nix level by `module-eval` only, a gap the flake documents. (d) `codex exec` in a git worktree WRITES `[projects."<workdir>"] trust_level = "trusted"` into the user config it can write: a test's user config is created fresh per run and never asserted on after the run. `codex features list` exists and prints one line per feature (measured). Each fact has its falsifier in CX2b's Tests; a false assumption is reported as `partial` with the pasted report, never routed around.
9. `EVIDENCE_STORE` and `FACTORY_EVIDENCE_CMD` (nixos-agent-env) — as 2; `FACTORY_ROOT` under the tmpdir in every bats row; the sandbox's `HOME` is writable (`export HOME=$TMPDIR` is the house shape).

## Waves

Waves follow `dependsOn` (the groups `tasks.py waves` prints when every task with no unmet dependency is peeled off; two tasks in one wave that write the same file serialise in key order — none here do). Computed on the scratch copy of the tree (Step 3's form: `cp -a ~/nixos-agent-env <scratch>/tree`, the draft placed under the copy's `docs/superpowers/plans/`, the copy's `repos.toml` given the `codex` row of §Dispatch step 0, a two-repo `--repos` file, `--runs-dir /nonexistent --store /nonexistent`); the outputs are pasted in §Dispatch. **Re-run on the live tree before the plan's commit (the orchestrator, 2026-09-07 ~20:50 CDT, HEAD ae3029c with SH3r typed, this file and the `codex` row in place):** `check` empty (exit 0); `conflicts` prints the 28 pairs of §Dispatch and no other line naming CA1, CA2, CA3 or CX2 — no SH3r pair (it is in flight, chain-rooted under SH3, and SH4's `dependsOn: SH3` sequences it), no CX2 pair (its `touches` resolve in the `codex` repo); `waves … --json` → `[]` for both repos; `brief` gains `| codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |` (CX2 blocked) and its Next-wave line does not name codex.

| wave | groups | dependsOn | notes |
|---|---|---|---|
| 1 | CA1 ‖ CA2 ‖ CA3 | CA1: SH4, SH5, P11; CA2: SH5; CA3: SH4, SH5 | disjoint files: CA1 is the driver, the brief, the usage script, one bats file and the README; CA2 is `tasks.py` and its tests; CA3 is the fence, the ingest, the schema, their tests and one fixture. Runnable only once SH4 and SH5 have landed (today `blocked`: SH3 is `rejected` with SH3r in flight — packet M2/M9). |
| 2 | CX2 (repo `codex`) | CA1, CA3 | the first Codex run through the arm: its `.result` needs CA1's writer and CA3's fence |

**Sibling plans' open tasks this plan must not collide with** (from the scratch copy's `conflicts`, pasted in §Dispatch): the seat-harness plan's SH3/SH3b (rejected; SH3r pending), SH4, SH5 on `factory-task`, `factory-brief`, `streams.py`, `ingest_result.py`, `SCHEMA.md`, `test_streams_policy.py`, `test_ingest_result.py`, `tasks.py`, `test_tasks.py`, the README — sequenced by `dependsOn` (D4); the seat-driver plan's SD2–SD4 on `factory-task`/`factory-brief`, SD2/SD3/SD9 on `tasks.py`/`test_tasks.py`, SD10 on the README — held, not sequenced, §Dispatch's pre-check. No hit against CR4, SB5, SB6 or any `flake.nix`, `nixosModules/`, `hosts/`, `CLAUDE.md`, `claims.toml` task: this plan's `touches` hold none of those.

## Operator

No switch, no credential, no name, no reboot, no unit: nothing in this plan edits a NixOS module, a host file or this repo's `flake.nix`; the driver runs from the tree (`tools/factory/seat/*`), outside the host closure. Three DeepSeek seats and one Codex seat; three Opus gates through `factory-review` and one through `~/factory/bin/opus-gate.js`.

1. **Before wave 1 — the balance glance (A3/A9).** The board's last figure: `grep -o 'OpenRouter: \$[0-9]* at [^(]*' docs/OPERATIONS.md` → `OpenRouter: $111 at ~12:10`; the same board line prices four Pro seats at ~$18, so three seats (M, S, XS) are ≈ $6–15 with a fix round. Acceptance: the balance in the OpenRouter console is above $40; below that, hold wave 1 and top up (your call). Codex's quota is your ChatGPT plan's (a week of credits, the board's 2026-09-07 note): CX2 is one run of CX1b's size (~40 min, ~82 k billed tokens); if the Codex app shows the quota exhausted, hold CX2 — nothing programmatic reads either balance (design §10).
2. **After CA2 lands — the Seats line.** From `~/nixos-agent-env`: `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep -F '**Seats (7 d):**'`. Expected shape: `**Seats (7 d):** deepseek/deepseek-v4-pro-0813: <n> runs, <d> done, <m> min, <t> billed · deepseek/deepseek-v4-flash: …` (the numbers are the runs root's, never retyped; `none` if no `.result` under `~/factory/runs` is younger than seven days). Acceptance: exit 0 and one line beginning `**Seats (7 d):**`. The packaged `evidence` on PATH (generation 45) predates this plan: the session hook's brief gains the line only after a switch you choose to make (A13).
3. **The closure diff, as a prediction (A2's shape; no switch is owed by this plan).** After wave 1 lands: `nix build .#nixosConfigurations.core.config.system.build.toplevel && nix store diff-closures /run/current-system ./result`. Prediction: still ONE line, `evidence: 69.8 KiB → <a few KiB more>` — CA2 and CA3 change `pkgs/evidence`, which the `evidence` package embeds whole (`nixosModules/evidenceStore.nix`: the wrapper embeds the directory); no line names `tools/factory/seat` (CA1 is outside the closure), no unit, no other package. Acceptance: exactly one line, naming `evidence`; a second line is a finding against this plan. Switch #21 stays your step, unchanged by this plan.
4. **After CX2 lands — the first Codex row.** `nix develop -c python3 pkgs/evidence/tasks.py --root . brief` → the repo table gains a `| codex | 1 | …` row and the Seats line names `gpt-6-astra: 1 run, 1 done, <m> min, <t> billed`; `git -C ~/flakes/codex log -1 --format=%s` → `checks: MAP currency, precedence proven for features.plugins and the otel exporters, no check dials api.openai.com, config-precedence skipped without user namespaces (test: map, config, config-rejects-typo, config-precedence, lint)`; `cd ~/flakes/codex && nix flake check -L` → `all checks passed!`. Acceptance: all three.
5. **Rollback of any landing.** Each landing is a fast-forward of `main` to `integ/<run>`; the undo is a revert of that merge commit, through the devShell so the hooks run: `git -C ~/nixos-agent-env log --merges --oneline -3` (find `integrate <KEY> into integ/<run>`), then `cd ~/nixos-agent-env && nix develop -c git revert -m 1 --no-edit <that sha>`. For the codex flake: `git -C ~/flakes/codex log --merges --oneline -1`, then `cd ~/flakes/codex && nix develop -c git revert -m 1 --no-edit <that sha>` (its hook runs `nix fmt` and `nix flake check`). Acceptance: `git log -1 --format=%s` reads `Revert "integrate <KEY> into integ/<run>"`, and — for CA1 — `FACTORY_SEAT=codex … factory-task` refuses with `FACTORY_SEAT=codex is not a seat arm` (the arm is gone). No generation is involved; `/run/current-system` is untouched by this plan.

## Dispatch

Plan file after Ship: `docs/superpowers/plans/2026-09-08-codex-driver-arm.md` (the board's name for it, START HERE item 1). Runs: `ca1` (wave 1), `cx2` (wave 2, by hand); fix rounds `ca1f` / `cx2f`; a relaunch after a death `ca1b` / `cx2b`.

**Step 0 — the plan's commit carries two ledger rows (D3, A8).** In the same commit as the plan file:

`docs/ledger/repos.toml` (after the `dsh-harness` row; the graph's display order is the file's):

```toml
[[repo]]
name = "codex"
path = "~/flakes/codex"
```

`docs/ledger/claims.toml` (a `gap` row; `claims.py validate` stays silent — the four required keys plus `owner`, `review_by`, `closes_by`):

```toml
[[claim]]
id = "codex-failure-strings-unmeasured"
text = "factory_error_class knows Codex's own failure strings"
status = "gap"
class = "unmeasured"
owner = "orchestrator"
opened = 2026-09-08
review_by = 2026-09-22
closes_by = "the first failed Codex run's agent output (never a log body) classified by hand and its pattern added to factory_error_class with a bats row, or five Codex runs without a failure"
```

Then `nix develop -c python3 pkgs/evidence/tasks.py --root . check` (empty), `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"` (silent), `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board`, and the commit `docs: plan — the codex arm of the seat driver (CA1–CA3, CX2); repos.toml gains the codex row; the failure-strings gap opened (test: lint)`.

**The graph on the draft** (Step 3's scratch-copy form; run from `~/nixos-agent-env` with the draft at `<scratch>/tree/docs/superpowers/plans/2026-09-08-codex-driver-arm.md` and the codex row in `<scratch>/tree/docs/ledger/repos.toml`): `nix develop -c python3 pkgs/evidence/tasks.py --root <scratch>/tree --repos <scratch>/repos.toml --runs-dir /nonexistent --store /nonexistent check` →

```
(no output; exit 0 — the four sections parse, every `dependsOn` resolves, CX2's `repo: codex` is configured by the copy's row, every acceptance name is in `docs/MAP.md` or exempt as attributed elsewhere, every subject's `(test: …)` equals its acceptance)
```

The same `check` stays empty after the four landings simulated below (SH4, SH5, CA1, CA3 as empty commits carrying their subjects, in the copy only).

`… conflicts` (the same flags; only pairs naming a draft key are listed — every other line is the packet's M5 set, unchanged) →

```
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SD2 (2026-09-06-seat-driver.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: CA2 (2026-09-08-codex-driver-arm.md) × SD2 (2026-09-06-seat-driver.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: CA2 (2026-09-08-codex-driver-arm.md) × SD2 (2026-09-06-seat-driver.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SD3 (2026-09-06-seat-driver.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: CA2 (2026-09-08-codex-driver-arm.md) × SD3 (2026-09-06-seat-driver.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: CA2 (2026-09-08-codex-driver-arm.md) × SD3 (2026-09-06-seat-driver.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SD4 (2026-09-06-seat-driver.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SD4 (2026-09-06-seat-driver.md): tools/factory/seat/factory-brief ~ tools/factory/seat/factory-brief
nixos-agent-env: CA2 (2026-09-08-codex-driver-arm.md) × SD9 (2026-09-06-seat-driver.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: CA2 (2026-09-08-codex-driver-arm.md) × SD9 (2026-09-06-seat-driver.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SD10 (2026-09-06-seat-driver.md): tools/factory/seat/README.md ~ tools/factory/seat/README.md
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SH4 (2026-09-07-seat-harness-redesign.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SH4 (2026-09-07-seat-harness-redesign.md): tools/factory/seat/README.md ~ tools/factory/seat/README.md
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH4 (2026-09-07-seat-harness-redesign.md): pkgs/evidence/streams.py ~ pkgs/evidence/streams.py
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH4 (2026-09-07-seat-harness-redesign.md): pkgs/evidence/ingest_result.py ~ pkgs/evidence/ingest_result.py
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH4 (2026-09-07-seat-harness-redesign.md): pkgs/evidence/SCHEMA.md ~ pkgs/evidence/SCHEMA.md
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH4 (2026-09-07-seat-harness-redesign.md): tests/evidence/test_streams_policy.py ~ tests/evidence/test_streams_policy.py
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH4 (2026-09-07-seat-harness-redesign.md): tests/evidence/test_ingest_result.py ~ tests/evidence/test_ingest_result.py
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): tools/factory/seat/factory-task ~ tools/factory/seat/factory-task
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): tools/factory/seat/factory-brief ~ tools/factory/seat/factory-brief
nixos-agent-env: CA1 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): tools/factory/seat/README.md ~ tools/factory/seat/README.md
nixos-agent-env: CA2 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): pkgs/evidence/tasks.py ~ pkgs/evidence/tasks.py
nixos-agent-env: CA2 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): tests/evidence/test_tasks.py ~ tests/evidence/test_tasks.py
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): pkgs/evidence/streams.py ~ pkgs/evidence/streams.py
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): pkgs/evidence/ingest_result.py ~ pkgs/evidence/ingest_result.py
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): pkgs/evidence/SCHEMA.md ~ pkgs/evidence/SCHEMA.md
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): tests/evidence/test_streams_policy.py ~ tests/evidence/test_streams_policy.py
nixos-agent-env: CA3 (2026-09-08-codex-driver-arm.md) × SH5 (2026-09-07-seat-harness-redesign.md): tests/evidence/test_ingest_result.py ~ tests/evidence/test_ingest_result.py
```

Every SH4/SH5 pair is sequenced by `dependsOn` (D4); every SD pair is the held ladder plan's — the launch pre-check below and A1 step 2 cover it. No CA1 × CA2, CA1 × CA3 or CA2 × CA3 line: wave 1's three groups share no file. CX2 lives in the `codex` repo and shares nothing with any `nixos-agent-env` task.

`… waves --repo nixos-agent-env --plan 2026-09-08-codex-driver-arm.md --json` and `… waves --repo codex --plan 2026-09-08-codex-driver-arm.md --json` →

```
today (SH3 rejected, SH4/SH5 blocked):                 [] and []
with SH4 and SH5 simulated landed:                     [[["CA1"], ["CA2"], ["CA3"]]] and []
with CA1 and CA3 simulated landed as well:             [[["CA2"]]] (the dispatcher's next wave) and [[["CX2"]]]; `waves --repo codex … --next` → "CX2"
```

(`brief` on the same copy: the repo table gains `| codex | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |` and the Next-wave line ends `· codex: CX2` — the A7 pre-check line.)

**The dry-run lines.** The dispatcher prints `would run: factory-wave <run> <repo> "<group>"…` and exits 0 without touching anything (`sed -n '170,175p' tools/factory/seat/factory-dispatch` → `if [ "$dry_run" -eq 1 ]; then` / `printf 'would run: factory-wave %s %s' "$run" "$repo_path"` / `printf ' "%s"' "${groups[@]}"` / `printf '\n'` / `exit 0`); its graph query is `tasks.py --root <repo> waves --repo nixos-agent-env --plan <basename> --next`, which reads the plans under the configured repo only, so the live line exists once the plan file is in the tree (Ship's step 3 runs and pastes it). Run against the scratch copy (its `repos.toml` pointed at the copy), with SH4 and SH5 simulated landed:

```
$ tools/factory/seat/factory-dispatch ca1 <scratch>/tree docs/superpowers/plans/2026-09-08-codex-driver-arm.md --dry-run   # before SH4/SH5
factory-dispatch: nothing schedulable in 2026-09-08-codex-driver-arm.md (all landed, in flight, or blocked)      # exit 0
$ … --dry-run   # SH4 and SH5 simulated landed
would run: factory-wave ca1 <scratch>/tree "CA1" "CA2" "CA3"                                                    # exit 0
$ … --dry-run   # CA1 and CA3 simulated landed too, CA2 still open
would run: factory-wave ca1 <scratch>/tree "CA2"
```

(`ls ~/factory/runs/ca1` → `No such file or directory` after all three: a dry run writes nothing.)

| wave | dry run (Ship pastes the live line) | the command to run (from `~/nixos-agent-env`, in the background, never a foreground tool call) |
|---|---|---|
| 1 | `tools/factory/seat/factory-dispatch ca1 ~/nixos-agent-env docs/superpowers/plans/2026-09-08-codex-driver-arm.md --dry-run` → `would run: factory-wave ca1 /home/dalhaka/nixos-agent-env "CA1" "CA2" "CA3"`; until SH4 and SH5 land it prints `factory-dispatch: nothing schedulable in 2026-09-08-codex-driver-arm.md (all landed, in flight, or blocked)` — that line is the hold (D4) | `tools/factory/seat/factory-dispatch ca1 ~/nixos-agent-env docs/superpowers/plans/2026-09-08-codex-driver-arm.md` |
| 2 | no dispatcher line: `factory-dispatch` resolves the target repo through `<repo-path>/docs/ledger/repos.toml` (`sed -n '104,108p' tools/factory/seat/factory-dispatch` → `local toml=$rp/docs/ledger/repos.toml` / `[ -f "$toml" ] \|\| factory_die 2 "factory-dispatch: no repos.toml at $toml"`), and `~/flakes/codex` has none (`git -C ~/flakes/codex ls-files` → 15 files, no `docs/ledger`). The pre-check is the graph itself: `nix develop -c python3 pkgs/evidence/tasks.py --root . waves --repo codex --plan 2026-09-08-codex-driver-arm.md --next` prints `"CX2"` only once CA1 and CA3 have landed; launch only on that line | `FACTORY_SEAT=codex FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-08-codex-driver-arm.md setsid -f bash -c 'exec tools/factory/seat/factory-wave cx2 /home/dalhaka/flakes/codex "CX2" >> ~/factory/runs/cx2.wave.log 2>&1' </dev/null` |

**Before launching wave 1, the collision pre-check (D4):** `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep -F '**Running:**'` must not name SD2, SD3 or SD4 (they share `factory-task`, `factory-brief`, `tasks.py`); if one is running, wait for its landing, then merge main into the workspace before the gate (A1 step 2). The dispatcher sets `FACTORY_PLAN` itself; it passes `FACTORY_SEAT` through untouched (CA1 row 16 pins `factory-wave`'s pass-through) — wave 1 runs on the DeepSeek seat, so `FACTORY_SEAT` stays unset for it. A hand launch of one key is `FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-08-codex-driver-arm.md tools/factory/seat/factory-wave ca1 /home/dalhaka/nixos-agent-env "CA1"` (the driver refuses without the plan; it re-execs under `setsid -w`, so the launching tool call must be a background one — `tel1` died in a foreground call at the tool timeout on 2026-09-06).

**The landing recipe, per key (design §4 A1):**
1. Keep exactly the one commit the section names: `git -C ~/factory/ws/<run>/<KEY> log --format='%h %s' <base>..task/<KEY>` must print one line whose subject is the section's `commit subject`; otherwise `git -C ~/factory/ws/<run>/<KEY> reset --hard <that sha>` (three seats appended a fabricated "landed" board commit on 2026-09-05 — CR5, CR2, FD1b — dropped this way).
2. If `main` moved under a file the task touches, `docs/MAP.md` or the queue block: `git -C ~/factory/ws/<run>/<KEY> fetch ~/nixos-agent-env main && git -C ~/factory/ws/<run>/<KEY> merge --no-edit FETCH_HEAD` (a board conflict: `git show FETCH_HEAD:docs/OPERATIONS.md > docs/OPERATIONS.md`, then `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board`; a MAP conflict: `nix develop -c python3 pkgs/evidence/repomap.py --root . write`; then `git add <named files>` and `nix develop -c git commit -q --no-edit`). For CX2 the base is `~/flakes/codex` and its branch `main` (`git -C ~/flakes/codex branch --show-current` → `main`): `git -C ~/factory/ws/cx2/CX2 fetch ~/flakes/codex main && … merge --no-edit FETCH_HEAD`.
3. Gate (Opus, mutation table, red-before-green — CA1–CA3 through `factory-review`; CX2 through `~/factory/bin/opus-gate.js`, whose brief quotes this plan's CX2 section and the trailer pair of item 7) and commit the review in `~/nixos-agent-env`: `git add docs/reviews/<file> && nix develop -c git commit -q -F <msgfile>` — before the integration, `&&`-gated (the 2026-09-06 10:29 lesson).
4. `tools/factory/seat/factory-integrate <run> ~/nixos-agent-env <KEY> && git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>` — gated on both exit codes; never pull after a `CHECK … fail` or a `REFUSED` line. For CX2: `tools/factory/seat/factory-integrate cx2 ~/flakes/codex CX2 && git -C ~/flakes/codex pull --ff-only ~/factory/base/codex integ/cx2` (the integrator runs each `(test: …)` name plus `lint` as `nix build .#checks.x86_64-linux.<name>` in `~/factory/base/codex` — the flake has them; `~/factory/base/codex` does not exist yet, `ls ~/factory/base` → `dsh-harness gaming media nixos-agent-env nixos-skill` and their locks; `factory-ws` creates it on the first run).
5. Dispatch what it unblocks (A7): CA2 landing alone unblocks nothing; CA1 and CA3 both landed → wave 2 (`cx2`, CX2 — the pre-check line above prints `"CX2"`).

**Relaunch after a death (A6).** After a `budget-402`, `provider-error` or `boot-failure` row: from `~/nixos-agent-env`, `FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-08-codex-driver-arm.md setsid -f bash -c 'exec tools/factory/seat/factory-wave ca1b /home/dalhaka/nixos-agent-env "<KEY>" >> ~/factory/runs/ca1b.wave.log 2>&1' </dev/null` (for CX2: `FACTORY_SEAT=codex …factory-wave cx2b /home/dalhaka/flakes/codex "CX2"…`); the dead seat's diff stays in `~/factory/ws/<run>/<KEY>` and the section's relaunch paragraph points the next seat at it. A Codex death's classes are unmeasured (item 5): its first failed `.result` is read (the `.result`, never the log) and the pattern typed into a bats row under the gap of step 0.

**Fix rounds and re-plans (rule A1).** One bounded fix round `<KEY>b` typed as an appended section carrying every rejection item and every deleted test's replacement, run as `ca1f` (or `cx2f`); a second rejection closes the chain and the re-plan `<KEY>r` goes through the pinned planning workflow in replan mode (`args.replan`, `args.rejection`), never a third fix round.

**Handoff line for the board (A11):** "codex arm: plan `2026-09-08-codex-driver-arm.md` (CA1 CA2 CA3 → CX2; held by the graph behind SH4/SH5); on the seat: <keys>; in gate: <keys>; landed: <keys>; the first Codex row: <after CX2>; next: <the dispatcher line, or `waves --repo codex … --next` for CX2>."

## Anticipation (design §4 rows whose trigger applies)

| row | trigger here | artefact |
|---|---|---|
| A1 | the plan is written | §Dispatch: run names, the dry-run line and its hold text, the five-step landing recipe with the branch reset and the merge of main, the codex-flake variants of steps 2 and 4 |
| A2 | a task touches `nixosModules/`, `hosts/` or the host config | not triggered: no such file in any `touches`; the closure line is still predicted and measured (§Operator step 3), because `pkgs/evidence` is inside the `evidence` package |
| A3 | a credential, name, file or top-up before a wave that starts more than one seat | wave 1 starts three seats: the balance glance is §Operator step 1 with the board's last figure; Codex's quota named there; no credential, DNS name, password file or reboot anywhere in the plan (`~/.codex/auth.json` is never read; `~/.codex/config.toml` is read for two keys) |
| A4 | every task | each section's Tests table: the mutant per assertion, the discriminating fixture row, the deletion mutant per rule |
| A5 | a wave is dispatched to a seat | the deterministic guards P11 landed (`FACTORY_PLAN` required, board rewrites refused at integration, a near-miss recorded — packet field §2; `P11` is `landed`, packet graph) — every task names P11 through SH4/SH5 → SH3 → SH2 → P11, and CA1 names it directly; the one new refusal this arm needs is CA1's own guard (`FACTORY_SEAT` outside `{unset, codex}` → exit 2 before a workspace; `codex` absent → exit 2); the sentences that remain interim are in Global Constraints (the result block's form, one commit, never the board) |
| A6 | credits or a provider fail mid-run | the relaunch lines in §Dispatch; each section's "Relaunch" paragraph; Codex's failure classes as the open gap |
| A7 | a landing | "what this landing unblocks" in §Dispatch step 5 and the `waves --repo codex … --next` pre-check |
| A8 | a task can close a claim | none of the 15 open gaps in `evidence bundle`'s list (packet M6) is closed by a driver, fence or brief change; the plan **opens** one (`codex-failure-strings-unmeasured`, §Dispatch step 0) with its closing shape — item 5's own words |
| A9 | a hold is the right call | computed: spend — three Pro/flash seats ≈ $6–15 against $111 (board, 2026-09-07 12:10): no hold; `lint` on main — `ok @71763d90bcf5` at HEAD (packet M6): no hold; a switch the tasks depend on — none; a paused sibling — the seat-harness chain owns the driver files until SH5 lands: the graph holds wave 1 (D4, the dispatcher's `nothing schedulable` line); the seat-driver plan is held and SD2–SD4 are the pre-check of §Dispatch |
| A10 | the operator will be asked | two questions, one word each, in §Operator questions |
| A11 | the session will reset | the handoff line in §Dispatch |
| A12 | a re-plan is needed | §Dispatch's rule-A1 paragraph; the fresh-workspace cherry-pick recipe belongs to the `<KEY>r` section when it is typed |
| A13 | a task adds a hook, or a second reader of something the tree also derives | CA2 adds a second reader of the runs root beside the ingest: consumer = `render_brief` (the tree's `pkgs/evidence/tasks.py` under `nix develop`, or the packaged `evidence` of the live generation, which lacks the line until a switch); it reads `~/factory/runs/*/*.result` by mtime (never a `.log`, never the store); the pre-commit hook's `check` and the lint check run with `--runs-dir /nonexistent`, so the board block and the checks never see it (Assumption 7; CA2 row S5 pins the board block); degrade: an unreadable file or a bad `usage:` JSON is skipped, an absent runs root prints `none` (rows S3, S4); no harness hook is added, so the loop-guard field does not apply |
| A14 | a task adds or tightens a deny rule | one new refusal, in the driver: `factory-task` exits 2 for any `FACTORY_SEAT` value other than unset/empty or exactly `codex` (a rule, not a list — `Codex`, `dsh`, `1`, `codex ` all refuse), and for `codex` with no `codex` on PATH. The commands it will refuse: a hand launch or `factory-dispatch` run with such a value in its environment — the orchestrator's recipes set it only for CX2 (`FACTORY_SEAT=codex`); nothing in `docs/runbooks/session.md`'s recipes or the board's launch lines carries the variable. The way through: unset it, or spell it `codex`. Nothing falls to the operator |

## Not in this plan

- A `route = "codex"` row, `factory_route` under codex, per-task model mixing (spec item 1: "a later spec, after n ≥ 5 runs"); the ladder (SD1, SD3); Codex under the seat lane or the broker; Codex on core (parked, decision 2026-09-07).
- A driver guard against two in-flight seats sharing a file across plans (the SD2–SD4 collision, D4): `factory-dispatch` would refuse a group whose `touches` overlap a running key's; a P11-class task without a spec item — the concept file `docs/concepts/2026-09-08a-cross-plan-collision-guard.md` is its parking place.
- The ingest parsing `seat: codex <session id>` into a field: the spec keeps every `seat:` line but the unit's ignored (`SEAT_UNIT_RE`, `SUBMIT_FAILED_RE`); a `seat_session` field is a fence change for the second Codex spec.
- `factory-review`'s trailer sentence (`sed -n '139p' tools/factory/seat/factory-review` → `` `Generated-By: dsh 0.1.2-rc.1 / $model (seat headless, factory run $run)`. ``): CX2's gate is `~/factory/bin/opus-gate.js` (the spec); a codex-aware `factory-review` is a task to type with the second Codex task.
- `factory-lib.sh` (D11); `flake.nix`, `githooks/pre-commit` (no list edit is needed — Global Constraints).
- Codex's own failure strings in `factory_error_class` (the gap of §Dispatch step 0; the first is classified by hand, from a `.result` and the agent's output copy).
- The managed layer `/etc/codex/managed_config.toml` as a model/effort source (not rendered on core); the otel keys' runtime effective values (CX2 records the gap in `docs/VALIDATION.md`).
- Syncing `~/factory/bin`: launches use the tree's `tools/factory/seat/*`; the unversioned copy is not touched.

---

## Tasks

### CA1 (code, M) — the codex arm of the seat driver: `FACTORY_SEAT=codex` selects `codex exec` in the workspace clone, the `.result` from the banner, the usage from the rollout, the classifier fed the agent's output, the codex trailers in the brief

**dependsOn:** SH4, SH5, P11

**Files:**
- Create: `tools/factory/seat/factory-codex-usage.py`, `tests/unit/95-codex-arm.bats`
- Modify: `tools/factory/seat/factory-task`, `tools/factory/seat/factory-brief`, `tools/factory/seat/README.md`

**Interfaces:**

- **The arm select** (`factory-task`, after `export FACTORY_PLAN="$plan"` and before `kind_size=$(factory_task_kind_size "$plan" "$key")`): exactly `codex` selects the Codex arm; unset or empty is today's seat, byte for byte; any other value refuses with exit 2 and one stderr line `factory-task: FACTORY_SEAT=<value> is not a seat arm (unset it, or set it to codex)`, before `mkdir -p -- "$runs_dir"`, before the pid file, before `factory-ws` — nothing is written. `codex` with no `codex` on `PATH` refuses the same way (`factory-task: FACTORY_SEAT=codex but no codex on PATH`, exit 2, nothing written).

```bash
# CA1: the seat arm. Exactly `codex` selects the Codex arm; unset or empty is
# today's seat (seat-submit or dsh-openrouter), byte for byte; any other value
# refuses before a workspace or run dir exists (the FACTORY_PLAN guard's shape).
seat_arm=dsh
case ${FACTORY_SEAT:-} in
  '') ;;
  codex)
    seat_arm=codex
    command -v codex >/dev/null 2>&1 || factory_die 2 "FACTORY_SEAT=codex but no codex on PATH"
    ;;
  *) factory_die 2 "FACTORY_SEAT=${FACTORY_SEAT} is not a seat arm (unset it, or set it to codex)" ;;
esac
```

- **Model, effort, route, version and the brief's model under codex** (replacing the `route_line=$(factory_route …)` block for this arm only; the `else` branch is today's block, byte for byte). `factory_route` is not called; `OPENROUTER_MODEL` and `OPENROUTER_REASONING_EFFORT` are ignored, each with exactly one stderr line `factory-task: warning: OPENROUTER_MODEL is ignored under FACTORY_SEAT=codex` / `… OPENROUTER_REASONING_EFFORT …`; `route_label` is `explicit` with `--model`, else `codex/$kind/$size` (`factory_task_kind_size` prints `any any` for an untyped heading, so `codex/any/any` is possible and the fence maps it to `unknown` — CA3); `FACTORY_SEAT_VERSION` is the last whitespace token of `codex --version`'s first line when it matches `^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$` (`codex-cli 0.153.4` → `0.153.4`), else unset with the warning `codex --version printed no version; the brief's trailer keeps its <version> placeholder`; `FACTORY_MODEL` (the brief's `<model>`) is the `--model` value, else the top-level `model` of `${CODEX_HOME:-$HOME/.codex}/config.toml`, else `unknown` (D5).

```bash
if [ "$seat_arm" = codex ]; then
  [ -z "${OPENROUTER_MODEL:-}" ] || factory_log "warning: OPENROUTER_MODEL is ignored under FACTORY_SEAT=codex"
  [ -z "${OPENROUTER_REASONING_EFFORT:-}" ] || factory_log "warning: OPENROUTER_REASONING_EFFORT is ignored under FACTORY_SEAT=codex"
  codex_home=${CODEX_HOME:-$HOME/.codex}
  effort=
  if [ -n "$model" ]; then route_label=explicit; else route_label="codex/$kind/$size"; fi
  codex_version=$(codex --version 2>/dev/null | head -n1 || true)
  codex_version=${codex_version##* }
  if [[ $codex_version =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
    export FACTORY_SEAT_VERSION=$codex_version
  else
    unset FACTORY_SEAT_VERSION
    factory_log "warning: codex --version printed no version; the brief's trailer keeps its <version> placeholder"
  fi
  brief_model=$model
  [ -n "$brief_model" ] || brief_model=$(factory_codex_config_value "$codex_home/config.toml" model)
  brief_model=${brief_model:-unknown}
else
  # today's block: route_line=$(factory_route implement "$kind" "$size" || true) … route_label=…
  brief_model=$model
fi
```
  and the existing `export FACTORY_MODEL=$model` becomes `export FACTORY_MODEL=$brief_model`.

- **`factory_codex_config_value <file> <key>`** (a function in `factory-task`, pure bash — the seat runs on the bare host PATH): prints the value of the first **top-level** line `<key> = "<value>"` (spaces optional around `=`; only a double-quoted value), reading lines only until the first line whose first non-blank character is `[` (a table header); prints nothing for an absent or unreadable file, an absent key, or a key that appears only inside a table; exit 0 always. `model_reasoning_effort` never matches the key `model` (the line must continue with `=` after the key and optional blanks).

```bash
factory_codex_config_value() {
  local file=$1 key=$2 line rest
  [ -r "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    line=${line#"${line%%[![:space:]]*}"}
    case $line in
      '['*) return 0 ;;
      "$key"*)
        rest=${line#"$key"}
        rest=${rest#"${rest%%[![:space:]]*}"}
        case $rest in
          '='*)
            rest=${rest#=}
            rest=${rest#"${rest%%[![:space:]]*}"}
            case $rest in
              '"'*'"'*)
                rest=${rest#\"}
                printf '%s\n' "${rest%%\"*}"
                return 0
                ;;
            esac
            ;;
        esac
        ;;
    esac
  done <"$file"
}
```

- **No `DSH_HOME` under codex:** the `shared_dsh=…` / `factory_seed_dsh_home` block runs only for `seat_arm=dsh` (`if [ "$seat_arm" != codex ]; then … fi`); `dsh_home` stays unset and no `<KEY>.dsh-home` directory appears.

- **The launch** (a third arm, tested before `command -v seat-submit`): from the workspace clone (`cd -- "$ws"`, no `-C`, no `--skip-git-repo-check`), the brief on stdin, never `--ephemeral`, never `--json`; `-m "$model"` only with `--model`; the argv is exactly `exec -c features.plugins=false -c otel.metrics_exporter="none" --sandbox danger-full-access --color never [-m <model>] -`; stdout+stderr tee'd into `$log`; `exit_code` is `codex`'s (124 under `timeout`); `wall_s` as today.

```bash
if [ "$seat_arm" = codex ]; then
  factory_log "launching codex exec in $ws (timeout ${timeout_s}s, log $log)"
  codex_args=(exec -c features.plugins=false -c 'otel.metrics_exporter="none"' --sandbox danger-full-access --color never)
  [ -z "$model" ] || codex_args+=(-m "$model")
  codex_args+=(-)
  start_ts=$(date +%s)
  set +e
  (
    cd -- "$ws" &&
      printf '%s\n' "$brief" | timeout -- "$timeout_s" codex "${codex_args[@]}"
  ) 2>&1 | tee -a -- "$log"
  exit_code=${PIPESTATUS[0]}
  set -e
  end_ts=$(date +%s)
  wall_s=$((end_ts - start_ts))
  factory_log "codex exited $exit_code after ${wall_s}s"
elif command -v seat-submit >/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then
  # today's seat-submit arm, unchanged
else
  # today's dsh-openrouter arm, unchanged
fi
```

- **The banner window and the three fields** (after the seat exits, before the result-line extraction; codex only). The banner is the block between the first two lines that are exactly `--------`; `model:`, `reasoning effort:` and `session id:` are read only inside it (D6). `model` = the banner's, else the config file's top-level `model`, else `unknown`; `effort` = the banner's `reasoning effort`, else the config's `model_reasoning_effort`, else `unknown` (the ingest maps anything outside `off|low|medium|high|xhigh` to `unknown` — its rule, not the driver's); `session_id` = the banner's `session id` when it is 36 hex-and-dash characters, else empty.

```bash
if [ "$seat_arm" = codex ]; then
  banner=$(awk '$0 == "--------" { n++; if (n == 2) exit; next } n == 1 { print }' -- "$log")
  banner_model=$(printf '%s\n' "$banner" | sed -nE 's/^model:[[:space:]]+(.+)$/\1/p' | head -n1)
  banner_effort=$(printf '%s\n' "$banner" | sed -nE 's/^reasoning effort:[[:space:]]+(.+)$/\1/p' | head -n1)
  session_id=$(printf '%s\n' "$banner" | sed -nE 's/^session id:[[:space:]]+([0-9a-fA-F-]{36})[[:space:]]*$/\1/p' | head -n1)
  model=${banner_model:-$(factory_codex_config_value "$codex_home/config.toml" model)}
  model=${model:-unknown}
  effort=${banner_effort:-$(factory_codex_config_value "$codex_home/config.toml" model_reasoning_effort)}
  effort=${effort:-unknown}
fi
```

- **Usage under codex** (replacing the `sessions_dir=$dsh_home/sessions` block for this arm; `rm -f -- "$marker"` stays after both). With a session id: the one file `rollout-*-<id>.jsonl` under `$codex_home/sessions` (if several — impossible by construction — the last by name); a valid id whose file is missing logs `no rollout named by session id <id> under <dir>` and keeps `{}`. Without an id: the newest-by-name rollout whose mtime is newer than the launch marker; none logs `no banner and no rollout newer than the launch marker under <dir>` and keeps `{}`. The script runs through `factory_py` (so `FACTORY_PYTHON3_CMD` reaches it in the sandbox) with the rollout on stdin; any failure keeps `{}`. `events` is then read from the JSON exactly as today (`[[ $usage_json =~ \"events\":\ *([0-9]+) ]]`), so `{}` → `events=0` → the `boot-failure` arm when `wall_s < 10`.

```bash
if [ "$seat_arm" = codex ]; then
  usage_json='{}'
  rollout=
  if [ -n "$session_id" ]; then
    rollout=$(find "$codex_home/sessions" -type f -name "rollout-*-$session_id.jsonl" 2>/dev/null | sort | tail -n1 || true)
    [ -n "$rollout" ] || factory_log "no rollout named by session id $session_id under $codex_home/sessions"
  else
    rollout=$(find "$codex_home/sessions" -type f -name 'rollout-*.jsonl' -newer "$marker" 2>/dev/null | sort | tail -n1 || true)
    [ -n "$rollout" ] || factory_log "no banner and no rollout newer than the launch marker under $codex_home/sessions"
  fi
  if [ -n "$rollout" ]; then
    factory_log "usage source: $rollout"
    usage_json=$(factory_py "$FACTORY_BIN/factory-codex-usage.py" <"$rollout" 2>/dev/null || echo '{}')
  fi
else
  # today's dsh block, unchanged
fi
rm -f -- "$marker"
```

- **The classifier's copy** (codex only): `factory_error_class` is unchanged and receives a copy of the log holding the agent's output only — the lines after the first line that is exactly `codex` **which follows the echoed brief**: the banner (through its second `--------`), the line `user` and then as many lines as `$brief` has (`printf '%s\n' "$brief" | wc -l`; Codex echoes the prompt verbatim, measured 2026-09-07 19:40) are skipped before the marker is looked for, so a bare `codex` line inside the brief is never the marker. Without such a line (no banner, or no agent message) the copy is empty — a boot failure carries no agent output, and every tail keyword then reads `none`/`boot-failure` by `factory_error_class`'s own order. The copy is a `mktemp -p "$runs_dir" ".agent-$key.XXXXXX"` (no `.log` suffix, so `tasks.py`'s `*.log` glob never sees it) and is removed after the call.

```bash
class_log=$log
if [ "$seat_arm" = codex ]; then
  class_log=$(mktemp -p "$runs_dir" ".agent-$key.XXXXXX")
  brief_lines=$(printf '%s\n' "$brief" | wc -l)
  awk -v skip="$brief_lines" '
    !banner { if ($0 == "--------") n++; if (n == 2) banner = 1; next }
    !user { if ($0 == "user") { user = 1; left = skip }; next }
    left > 0 { left--; next }
    !on { if ($0 == "codex") on = 1; next }
    { print }' -- "$log" >"$class_log"
fi
error_class=$(factory_error_class "$class_log" "$status" "$exit_code" "$wall_s" "$events" "$synth" "$demoted")
[ "$class_log" = "$log" ] || rm -f -- "$class_log"
```

- **The `.result`** (codex only): `model:`, `effort:`, `route:` as computed above; `seat: codex <session id>` printed where `seat: unit seat@…` goes today, only when `session_id` is non-empty; everything else byte for byte as today (`run, key, plan, workspace, branch, head, base, wall_s, exit_code, error_class, [derived]`, the commit log, the diffstat, `usage:`). Consumers: the ingest (`route` → CA3's regex; `model` → `MODEL_ID_RE`, which `gpt-6-astra` and `unknown` match; `effort` → the enum; `seat:` other than the unit's is ignored — spec), `factory-wave`'s summary (`status`, `wall_s`, `usage`), CA2's Seats line (`model`, `wall_s`, `usage`, the status word).

- **`factory-brief`**: two new env vars. `FACTORY_SEAT` — exactly `codex` selects the codex trailer pair; any other value or unset leaves today's output byte-identical. `FACTORY_SEAT_VERSION` — the literal `<version>` when unset. The RULES block's two trailer lines become placeholders substituted before `<RUN>` and `<model>`:

```bash
seat_label=${FACTORY_SEAT:-}
ver_label=${FACTORY_SEAT_VERSION:-<version>}
if [ "$seat_label" = codex ]; then
  generated_by="Generated-By: codex-cli $ver_label / <model> (codex exec, factory run <RUN>)"
  co_authored="Co-Authored-By: Codex CLI $ver_label <noreply@openai.com>"
else
  generated_by='Generated-By: dsh 0.1.2-rc.1 / <model> (seat headless, factory run <RUN>)'
  co_authored='Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'
fi
# in the RULES heredoc, the two trailer lines read:
#     <GENERATED_BY>
#     <CO_AUTHORED_BY>
rules=${rules//<GENERATED_BY>/$generated_by}
rules=${rules//<CO_AUTHORED_BY>/$co_authored}
rules=${rules//<KEY>/$key}
rules=${rules//<RUN>/$run_label}
rules=${rules//<model>/$model_label}
```

- **`tools/factory/seat/factory-codex-usage.py`** (stdin = one rollout; stdout = one JSON object; exit 0 always; stdlib only): the shape `factory-usage.py` prints, so `factory-task`'s `usage:` line and the ingest (`input→in, output→out, cacheRead→cache_read, reasoning, events, duration_s`) read both alike. `model` = `payload.model` of the last `turn_context` line; `events` = the number of lines that parse as a JSON object (a torn line, a blank line or a non-object line is skipped and not counted); `input` = `input_tokens − cached_input_tokens`, `cacheRead` = `cached_input_tokens`, `output` = `output_tokens`, `reasoning` = `reasoning_output_tokens`, all from the last `token_count` event whose `payload.info` is a JSON object (a later `token_count` with `info: null` does not reset them; no such event → all four 0); `duration_s` = the last parsed `timestamp` minus the first, in seconds (fractional digits beyond six are truncated before parsing; no parsable timestamp → `null`). A key of the wrong type counts as absent. Empty stdin → `{"model": null, "events": 0, "input": 0, "output": 0, "cacheRead": 0, "reasoning": 0, "duration_s": null}`.

```python
#!/usr/bin/env python3
"""factory-codex-usage.py -- best-effort token-usage summary for one Codex rollout.

Reads one Codex CLI rollout (~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<session
id>.jsonl) on stdin and prints one JSON object on stdout in the shape
factory-usage.py prints for a dsh session, so factory-task's `usage:` line and
the ingest read both alike: {"model","events","input","output","cacheRead",
"reasoning","duration_s"}. Never raises: a line that is not a JSON object is
skipped; a field that never appears stays 0 (model, duration_s stay null).

Rollout lines (Codex 0.153.4, measured 2026-09-07): every line is
{"timestamp": "<RFC3339>", "type": "<kind>", "payload": {...}}. A `turn_context`
payload carries model and effort. An `event_msg` payload whose `type` is
"token_count" carries info.total_token_usage with the CUMULATIVE input_tokens,
cached_input_tokens, output_tokens and reasoning_output_tokens -- and `info`
may be null (the last such event often is). The totals reported are the last
non-null ones; `input` is net of the cache, which is what is billed. A line the
decoder cannot parse -- torn, or nested past the recursion limit -- is skipped.
Plan: docs/superpowers/plans/2026-09-08-codex-driver-arm.md (CA1).
"""

import datetime
import json
import re
import sys

FRACTION_RE = re.compile(r"\.(\d{6})\d+")


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _ts(value):
    if not isinstance(value, str):
        return None
    value = FRACTION_RE.sub(r".\1", value).replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None


def main() -> int:
    model = None
    events = 0
    first_ts = None
    last_ts = None
    totals = None
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except (json.JSONDecodeError, ValueError, RecursionError):
            # RecursionError: the C decoder's answer to a line nested deeper
            # than the interpreter's limit; the line is skipped like a torn one.
            continue
        if not isinstance(ev, dict):
            continue
        events += 1
        ts = _ts(ev.get("timestamp"))
        if ts is not None:
            if first_ts is None:
                first_ts = ts
            last_ts = ts
        payload = ev.get("payload")
        if not isinstance(payload, dict):
            continue
        if ev.get("type") == "turn_context":
            m = payload.get("model")
            if isinstance(m, str) and m:
                model = m
        elif ev.get("type") == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            if isinstance(info, dict) and isinstance(info.get("total_token_usage"), dict):
                totals = info["total_token_usage"]
    totals = totals or {}
    cached = _int(totals.get("cached_input_tokens"))
    duration_s = None
    if first_ts is not None and last_ts is not None:
        duration_s = (last_ts - first_ts).total_seconds()
    print(
        json.dumps(
            {
                "model": model,
                "events": events,
                "input": _int(totals.get("input_tokens")) - cached,
                "output": _int(totals.get("output_tokens")),
                "cacheRead": cached,
                "reasoning": _int(totals.get("reasoning_output_tokens")),
                "duration_s": duration_s,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- **`factory-wave` and `factory-dispatch`**: no change. Neither scrubs the environment (`grep -n 'env \|export\|FACTORY_SEAT' tools/factory/seat/factory-wave` → only `export FACTORY_PLAN="$plan_abs"`; the dispatcher launches `FACTORY_PLAN="$plan_file" "${FACTORY_WAVE_CMD:-$here/factory-wave}" …`), so `FACTORY_SEAT` reaches every `factory-task` of a wave — row 16 pins it.

- **`tools/factory/seat/README.md`**: the `factory-task` bullet gains `FACTORY_SEAT` (unset/empty: today; `codex`: the Codex arm; anything else: exit 2); a new `## Codex arm (FACTORY_SEAT=codex)` section after `## Seat unit (SB3)` stating the launch line, the `.result` sources (banner → config → `unknown`; the rollout by session id; the classifier's copy), the two ignored variables, and that no `DSH_HOME` is seeded; `## Commit trailers (the convention)` gains the codex pair with `<ver>` from `codex --version`.

**Facts:**

- `sed -n '73,78p' tools/factory/seat/factory-task` → `if [ -z "${FACTORY_PLAN:-}" ]; then` / `factory_die 2 "FACTORY_PLAN is unset — name the plan (FACTORY_PLAN=<plan.md> …) or launch through factory-dispatch"` / `fi` / `plan=$FACTORY_PLAN` / `factory_need_file "$plan"` — the guard shape, before `runs_dir=$FACTORY_RUNS/$run` / `mkdir -p -- "$runs_dir"` (`sed -n '116,117p'`) and before `ws=$("$FACTORY_BIN/factory-ws" "${ws_args[@]}")` (`sed -n '131p'`).
- `sed -n '91,112p' tools/factory/seat/factory-task` → `kind_size=$(factory_task_kind_size "$plan" "$key")` / `read -r kind size <<<"$kind_size"` / `route_line=$(factory_route implement "$kind" "$size" || true)` … `model=deepseek/deepseek-v4-pro-0813` / `factory_log "warning: routing table unusable (docs/ledger/routing.toml); using built-in default $model"` … `route_label="implement/$kind/$size"` — the block the codex branch replaces; the warning line row 12 asserts absent.
- `sed -n '133,145p' tools/factory/seat/factory-task` → `shared_dsh=${FACTORY_SHARED_DSH_HOME:-0}` … `dsh_home=$runs_dir/$key.dsh-home` / `factory_seed_dsh_home "$dsh_home"` … `export FACTORY_RUN=$run` / `export FACTORY_MODEL=$model` / `brief=$(FACTORY_TASK_TEXT=${FACTORY_TASK_TEXT:-} "$FACTORY_BIN/factory-brief" "$plan" "$key")` — the seed and the brief's env.
- `grep -n 'seat-submit headless\|dsh-openrouter --model' tools/factory/seat/factory-task` → `167:  factory_log "submitting seat job via seat-submit headless in $ws …"` / `173:      seat-submit headless \` / `205:  factory_log "launching dsh-openrouter --model $model --headless in $ws …"` / `212:        timeout -- "$timeout_s" dsh-openrouter --model "$model" --headless "$brief"`; `sed -n '162p'` → `if command -v seat-submit >/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then` — the two arms; `sed -n '208,215p'` → `( cd -- "$ws" && DSH_HOME=$dsh_home OPENROUTER_REASONING_EFFORT=$effort timeout -- "$timeout_s" dsh-openrouter … ) 2>&1 | tee -a -- "$log"` / `exit_code=${PIPESTATUS[0]}` — the launch idiom the codex arm copies.
- `sed -n '377,392p' tools/factory/seat/factory-task` → `usage_json='{}'` / `sessions_dir=$dsh_home/sessions` … `session_file=$(find "$sessions_dir" -type f -name 'session.jsonl.zstd' -newer "$marker" 2>/dev/null | sort | tail -n1 || true)` … `usage_json=$(zstd -dc -- "$session_file" 2>/dev/null | factory_python3 "$FACTORY_BIN/factory-usage.py" 2>/dev/null || echo '{}')` / `rm -f -- "$marker"` / `events=` / `if [[ $usage_json =~ \"events\":\ *([0-9]+) ]]; then` / `events=${BASH_REMATCH[1]}` — the marker (`marker=$(mktemp -p "$runs_dir" ".marker-$key.XXXXXX")`, `sed -n '149p'`), the newest-since-marker rule and the events regex.
- `sed -n '395p' tools/factory/seat/factory-task` → `error_class=$(factory_error_class "$log" "$status" "$exit_code" "$wall_s" "$events" "$synth" "$demoted")`; `sed -n '106,157p' tools/factory/seat/factory-lib.sh` → the order `submit-failed` → `timeout` (exit 124) → `none` (done) → `no-result-line` → `template-echo` → `budget-402` (`402` and `budget_exhausted` in the last 4000 bytes) → `provider-error` (`\b(502|503|529)\b|upstream|provider`) → `unknown-model` → `boot-failure` (`wall_s < 10 && events < 50`) → `none`. The banner's `provider: openai` is inside `tail -c 4000` of a short log.
- `sed -n '398,430p' tools/factory/seat/factory-task` → the `.result` writer: `printf 'model: %s\n' "$model"` / `printf 'effort: %s\n' "$effort"` / `printf 'route: %s\n' "$route_label"` … `if [ -n "$seat_id" ]; then` / `printf 'seat: unit seat@%s\n' "$seat_id"` / `elif [ "$submit_failed" -eq 1 ]; then` / `printf 'seat: submit failed (no job id)\n'` / `fi` — where `seat: codex <id>` joins; `sed -n '432p'` → `factory_ingest_result "$result" || factory_log "evidence: could not record $key"`.
- `sed -n '60,61p' tools/factory/seat/factory-brief` → `run_label=${FACTORY_RUN:-<RUN>}` / `model_label=${FACTORY_MODEL:-<model>}`; `sed -n '89,90p'` → `    Generated-By: dsh 0.1.2-rc.1 / <model> (seat headless, factory run <RUN>)` / `    Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; `sed -n '102,104p'` → `rules=${rules//<KEY>/$key}` / `rules=${rules//<RUN>/$run_label}` / `rules=${rules//<model>/$model_label}`.
- `sed -n '94,97p' tests/unit/80-seat-driver.bats` → `[[ "$output" == *"Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run run7)"* ]]` / `[[ "$output" == *"Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"* ]]` / `[[ "$output" == *"Generated-By: dsh 0.1.2-rc.1"*"Co-Authored-By: Claude Fable 5.1"* ]]` / `[[ "$output" != *"<RUN>"* ]]` — the dsh trailer pins that must stay green.
- `sed -n '62,80p' tools/factory/seat/factory-lib.sh` → `factory_python3() { (cd "$FACTORY_TOOLBOX_REPO" && nix develop -c python3 "$@") }` / `factory_py() { if [ -n "${FACTORY_PYTHON3_CMD:-}" ]; then (cd "$FACTORY_TOOLBOX_REPO" && $FACTORY_PYTHON3_CMD "$@") else factory_python3 "$@" fi }` — `factory_py` is the seam the usage call uses (the dsh arm's `factory_python3` cannot run in the sandbox, which is why no test pins its numbers).
- `sed -n '1,30p' tools/factory/seat/factory-usage.py` → the dsh script's docstring and `USAGE_FIELDS = {"inputTokens": "input", "outputTokens": "output", "cacheReadTokens": "cacheRead", "reasoningTokens": "reasoning"}`; its output keys `model, events, input, output, cacheRead, reasoning, duration_s` are the shape the new script keeps.
- `sed -n '1090,1188p' tests/unit/80-seat-driver.bats` → the fake-binary idiom: `seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"` / `sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"` / a fake `factory-ws` printing the ws path / a fixture toolbox with `docs/ledger/routing.toml` / a fake on `PATH` recording `$*` into `$REC` and printing a result block / `REC="$rec" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" … run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1` / `run cat "$root/runs/r1/K1.result"` and `[[ "$output" == *"seat: unit seat@20260905-120000-abcdef"* ]]`.
- `sed -n '50,126p' tests/unit/94-seat-harness.bats` → `mk_ws_with_commits <n> [meta]` (a real git workspace at `$WS` with `<n>` commits on `task/K1` and `.factory-meta` under `$FACTORY_ROOT/ws/r1/K1`), `fake_seat <payload>`, `run_task` (the seat copy, the fake `factory-ws`, `FX` with a one-row `routing.toml`, the plan `### K1 (code, M) — t`, `FACTORY_SEAT_UNIT=0`, `OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL=`).
- `sed -n '3414,3475p' tests/unit/80-seat-driver.bats` → `FACTORY_EVIDENCE_CMD="$evcmd"` with a fake that records `ingest result <path>` — the recorder seam.
- `command -v codex` → `/home/dalhaka/.local/bin/codex`; `grep -n '^model\b\|^model_reasoning_effort' ~/.codex/config.toml` → `1:model = "gpt-6-astra"` / `2:model_reasoning_effort = "medium"`.
- `grep -rn 'factory-usage' tests/` → no test pins the dsh usage script (its numbers are read through `nix develop`, Assumption 1); the codex script is pinned here through `factory_py`.

- [ ] **Step 1: Write the failing tests** — `tests/unit/95-codex-arm.bats`. Header, `setup_file`/`teardown_file` and `setup` as `94-seat-harness.bats` lines 1–48 (`SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"`, `REAL_BASH`, the empty `$PLAN` exported as `FACTORY_PLAN`, `FACTORY_ROOT`/`FACTORY_RUNS` under `$BATS_TEST_TMPDIR`, the `~/factory/runs` snapshot); `mk_ws_with_commits` as its lines 55–79. Three helpers of this file:

  - `fake_codex` writes `$BIN/codex` (`BIN="$BATS_TEST_TMPDIR/bin"`), `chmod +x`: with `$1` = `--version` it prints `${FAKE_VERSION:-codex-cli 0.153.4}` and exits 0; otherwise it appends `args=$*`, `cwd=$PWD`, `stdin_begin`, the whole stdin, `stdin_end` to `$REC`; unless `FAKE_NO_BANNER=1` it prints the banner — `OpenAI Codex v0.153.4`, `--------`, `workdir: $PWD`, `model: ${FAKE_MODEL:-gpt-6-astra}`, `provider: openai`, `approval: never`, `sandbox: danger-full-access`, `reasoning effort: ${FAKE_EFFORT:-medium}`, `reasoning summaries: auto`, `session id: $sid`, `--------` — then `user`, the stdin echoed, and `codex`; it prints `${FAKE_BODY}` (default the four lines `FACTORY-RESULT status=done` / `FACTORY-CHECKS unit=pass` / `FACTORY-COMMITS 1` / `FACTORY-NOTES the arm ran`), then `tokens used` and `${FAKE_TOKENS:-12345}`; unless `FAKE_NO_ROLLOUT=1` it writes `$CODEX_HOME/sessions/2026/09/08/rollout-2026-09-08T00-00-00-$sid.jsonl` with: a `session_meta` line at `2026-09-08T00:00:00.000Z`, a `turn_context` line at `00:00:01` whose payload is `{"model": "<FAKE_MODEL>", "effort": "<FAKE_EFFORT>"}`, `${FAKE_FILLER:-57}` `response_item` lines at `00:10:00`, and one `event_msg` line at `00:40:00` with `payload.type` `token_count` and `payload.info.total_token_usage` `{input_tokens: ${FAKE_IN:-1710988}, cached_input_tokens: ${FAKE_CACHED:-1642368}, output_tokens: ${FAKE_OUT:-13584}, reasoning_output_tokens: ${FAKE_REASON:-3631}}` (60 lines by default; `duration_s` 2400.0); then `sleep ${FAKE_SLEEP:-0}` and `exit ${FAKE_EXIT:-0}`. `sid=${FAKE_SID:-0f1e2d3c-4b5a-4c6d-8e9f-0a1b2c3d4e5f}`.
  - `fake_dsh` writes `$BIN/dsh-openrouter`: `: >"$DSH_CALLED"` then the four default result lines.
  - `run_codex_task [extra env]` — `run_task` of 94 with these differences: `PATH="$BIN:$PATH"`, `CODEX_HOME="$BATS_TEST_TMPDIR/codex-home"` holding a default `config.toml` of the host's shape (`model = "gpt-6-astra"` / `model_reasoning_effort = "medium"`; a row that names another config replaces or removes it), `REC="$BATS_TEST_TMPDIR/rec"`, `DSH_CALLED="$BATS_TEST_TMPDIR/dsh-called"`, `FACTORY_PYTHON3_CMD="$(command -v python3)"`, `FACTORY_EVIDENCE_CMD="$BATS_TEST_TMPDIR/ev.sh"` (a script that exits 0), `FACTORY_SEAT=codex` unless the row says otherwise; the plan `### K1 (code, M) — t` whose body carries the two decoy lines `model: decoy/model` and `session id: 00000000-0000-4000-8000-000000000000`.

| # | assertion | discriminating fixture | mutant |
|---|---|---|---|
| 1 | `FACTORY_SEAT=bogus` → exit 2; `$output` contains `FACTORY_SEAT=bogus is not a seat arm`; `[ ! -e "$FACTORY_RUNS/r1" ]`; the fake `factory-ws` was not called (it touches `$WS_CALLED` when it runs); the same for `FACTORY_SEAT=Codex` and `FACTORY_SEAT='codex '` | three spellings outside the rule | drop the `*)` arm → the run proceeds and `$FACTORY_RUNS/r1` exists; match `codex*` → `'codex '` accepted |
| 2 | `FACTORY_SEAT=codex` with `$BIN/codex` absent → exit 2, `no codex on PATH`, no run dir, no ws call | the fake removed | drop `command -v` → the launch fails later with a run dir present |
| 3 | `FACTORY_SEAT=` (empty) and `env -u FACTORY_SEAT` → `$DSH_CALLED` exists, `$REC` absent (the fake codex never ran), `.result` has `route: implement/code/M` and `model: deepseek/deepseek-v4-pro-0813`, `$FACTORY_RUNS/r1/K1.dsh-home` exists | empty vs unset | treat empty as codex → `$REC` exists |
| 4 | the launch: `$REC` line `args=exec -c features.plugins=false -c otel.metrics_exporter="none" --sandbox danger-full-access --color never -` (byte-exact, one line), `cwd=$WS`, the stdin block contains `### K1 (code, M) — t`, `## WORKSPACE RULES`, `Generated-By: codex-cli 0.153.4 / gpt-6-astra (codex exec, factory run r1)` and `Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>`; `$DSH_CALLED` absent; `[ ! -e "$FACTORY_RUNS/r1/K1.dsh-home" ]`; `.result`: `model: gpt-6-astra`, `effort: medium`, `route: codex/code/M`, `seat: codex 0f1e2d3c-4b5a-4c6d-8e9f-0a1b2c3d4e5f`, `usage:` contains `"input": 68620`, `"cacheRead": 1642368`, `"output": 13584`, `"reasoning": 3631`, `"events": 60`, `"model": "gpt-6-astra"`; `error_class: none`; exit 0 | the default fake and the default config (the trailer's `gpt-6-astra` is the config's; the `.result`'s is the banner's — row 6 separates them) | `-` dropped → the args line; `--ephemeral` or `--json` added → the args line; `-m` always → the args line; the seed kept → `K1.dsh-home` exists; `route_label` left `implement/…`; `seat:` omitted |
| 5 | `--model gpt-6-mini` with `FAKE_MODEL=gpt-6-mini`: `args=… --color never -m gpt-6-mini -`; `route: explicit`; the stdin trailer names `gpt-6-mini` | `--model` given | `-m` after `-` → the args line; `route_label` kept `codex/…` |
| 6 | the banner window and its precedence: the plan body's decoys are echoed after `user`, and `config.toml` says `model = "cfg-model"` / `model_reasoning_effort = "high"` while the banner says `gpt-6-astra` / `medium` → `.result` `model: gpt-6-astra`, `effort: medium`, `seat: codex 0f1e2d3c-4b5a-4c6d-8e9f-0a1b2c3d4e5f`, never `decoy/model`, `cfg-model` or `00000000-…`; the stdin trailer reads `codex-cli 0.153.4 / cfg-model` (the brief is printed before the banner exists) | the decoy lines; the config disagreeing with the banner | grep the whole log (last match) → the decoys win; a window from the first `--------` to EOF → the decoys win; the config read before the banner → `cfg-model` in the `.result` |
| 7 | trailer-time model: no `--model`, `$CODEX_HOME/config.toml` = `model = "cfg-model"` / `model_reasoning_effort = "high"` → the stdin trailer reads `codex-cli 0.153.4 / cfg-model`; with no config.toml → `codex-cli 0.153.4 / unknown`; a config.toml whose only `model =` line sits under `[profiles.fast]` → `unknown`; a line `model_reasoning_effort = "high"` above a `model = "cfg-model"` line → `cfg-model` | the profile-table file; the effort-first file | read the whole file → `table-model`; match `$key*` without the `=` test → `high` |
| 8 | `.result` fallback: `FAKE_NO_BANNER=1` with the config of row 7 → `model: cfg-model`, `effort: high`, no `seat:` line at all (`! grep -q '^seat:'`); `FAKE_NO_BANNER=1` with no config → `model: unknown`, `effort: unknown` | banner absent | skip the fallback → `unknown` where `cfg-model` is expected; print `seat: codex ` with an empty id |
| 9 | the rollout by id: a decoy `rollout-2026-09-09T00-00-00-11111111-2222-4333-8444-555555555555.jsonl` pre-created under the same day dir with `FAKE_IN`-shaped totals `input 999, cached 0` and `touch -d '+1 day'` (newer than the marker, later by name) → `usage:` still `"input": 68620` | the decoy newer and later-sorting | pick the newest instead of the id → `"input": 999` |
| 10 | no banner, newest since the marker: `FAKE_NO_BANNER=1`; a decoy with a later-sorting name and `touch -d 2020-01-01` (older than the marker), totals `input 999` → `usage:` `"input": 68620` | the old decoy | drop `-newer "$marker"` → the decoy (`sort \| tail -n1`) wins → `999` |
| 11 | no rollout: `FAKE_NO_ROLLOUT=1 FAKE_BODY=$'FACTORY-RESULT status=failed\nFACTORY-CHECKS unit=fail\nFACTORY-COMMITS 0\nFACTORY-NOTES it broke'` → `usage: {}`, `error_class: boot-failure`, `$output` contains `no rollout named by session id` | events 0, wall < 10 | default `events` to 50 → `none`; hand the raw log to the classifier → `provider-error` (the banner's `provider: openai` is in its tail) |
| 12 | the classifier's copy: the failed body of row 11 with the default rollout (60 events), the plan body carrying `502 upstream provider` → `error_class: none` (no keyword in the agent's output; events 60); the same with the plan body carrying a line that is exactly `codex` followed by the line `502 upstream provider` → still `none` (the decoy marker sits inside the echoed brief); with `FAKE_BODY` = the failed block plus a line `502 Bad Gateway from the provider` → `provider-error` | the keywords in the brief only vs in the reply; the bare `codex` line inside the brief | the raw log → `provider-error` in the first case; the first `codex` line anywhere → `provider-error` in the second case (the copy starts at the decoy and holds the rest of the brief); copy from the first `--------` → the banner's `provider` → `provider-error`; copy from `user` → the echoed `502`; an empty copy always → `none` in the third case |
| 13 | `OPENROUTER_MODEL=x OPENROUTER_REASONING_EFFORT=high FACTORY_ROUTING_TABLE=/nonexistent` → the args line has no `-m`; `model: gpt-6-astra`, `effort: medium`; `grep -c 'warning: OPENROUTER_MODEL is ignored under FACTORY_SEAT=codex'` over `$output` is 1 and the same for `OPENROUTER_REASONING_EFFORT`; `$output` has no `routing table unusable` line; exit 0 | both variables set, the table missing | honour `OPENROUTER_MODEL` → `-m x`; call `factory_route` → the `routing table unusable` line appears; log the warning per variable read → 2 |
| 14 | `FAKE_SLEEP=3 FACTORY_TIMEOUT=1` → `exit_code: 124`, `error_class: timeout`, `usage:` still parsed (`"input": 68620`), exit 2 | the sleep past the timeout | `exit_code=$?` of `tee` → `0` |
| 15 | `FACTORY_SEAT_VERSION`: `FAKE_VERSION='codex-cli 0.153.4'` → the stdin trailer `codex-cli 0.153.4`; `FAKE_VERSION=garbage` → `codex-cli <version>` and the warning `printed no version` once; `FAKE_VERSION='codex-cli 0.154.0-alpha.1'` → `0.154.0-alpha.1` | the three outputs | skip the validation → `codex-cli garbage` |
| 16 | `factory-wave` pass-through: `FACTORY_SEAT=codex FACTORY_BIN_OVERRIDE=$FAKE_BIN "$REAL_BASH" "$SEAT/factory-wave" r1 "$REPO" "K1"` with a fake `factory-task` that writes `$FACTORY_SEAT` to `$SEEN` and a `done` `.result` → `$SEEN` reads `codex` | the fake driver | `unset FACTORY_SEAT` (or `env -u`) in `factory-wave` → empty |
| 17 | `factory-brief`: `FACTORY_SEAT=codex FACTORY_SEAT_VERSION=0.153.4 FACTORY_MODEL=gpt-6-astra FACTORY_RUN=cx2` → the two lines `Generated-By: codex-cli 0.153.4 / gpt-6-astra (codex exec, factory run cx2)` then `Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>` (in that order, adjacent), no `Claude Fable`, no `dsh 0.1.2`; `FACTORY_SEAT=codex` without the version → `codex-cli <version>` in both lines; `env -u FACTORY_SEAT`, `FACTORY_SEAT=`, `FACTORY_SEAT=Codex` → three outputs `cmp`-identical to each other and containing the two dsh lines of `80-seat-driver.bats:94-95` | the three non-codex spellings against `codex` | case-insensitive match → `Codex` differs; drop the `<version>` fallback → an empty version; swap the order → the adjacency assertion |
| 18 | the usage script, `python3 "$SEAT/factory-codex-usage.py" < <fixture>`: (a) the default fake rollout (60 lines) plus a torn line `{"timestamp":"2026-09-08T00:41:00Z","type":"event_msg","payload":{"type":"token_cou`, a line `[]`, and a final `token_count` at `00:50:00.123456789Z` with `"info": null` → `{"model": "gpt-6-astra", "events": 61, "input": 68620, "output": 13584, "cacheRead": 1642368, "reasoning": 3631, "duration_s": 3000.123456}` (61: the torn line and the `[]` line are not objects and are not counted; the null-info event is); (b) empty stdin → `{"model": null, "events": 0, "input": 0, "output": 0, "cacheRead": 0, "reasoning": 0, "duration_s": null}`, exit 0; (c) `/dev/urandom | head -c 2000` on stdin → exit 0 and a JSON object with `"events": 0`; (d) the default rollout plus one line of 100,000 nested brackets (`python3 -c 'print("[" * 100000 + "]" * 100000)'`) → exit 0 and row 4's numbers with `"events": 60` (the C decoder raises `RecursionError` on that line; it is skipped like a torn one) | the null-info tail, the torn line, the nine-digit fraction, the deep line | `input = input_tokens` → `1710988`; the last `token_count` regardless of `info` → zeros; count raw lines → 63; `raise` on a decode error → exit 1; the narrow `except (json.JSONDecodeError, ValueError)` → (d) exits 1; `first`/`last` from `token_count` lines only → `600.0` |

- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/95-codex-arm.bats` → `not ok 1 …` with `[ "$status" -eq 2 ]` failing (today `FACTORY_SEAT=bogus` is read nowhere: the run proceeds and exits 0 on the fake `dsh-openrouter`), and row 18's first case `python3: can't open file '…/tools/factory/seat/factory-codex-usage.py'`. Paste both lines in the commit body.
- [ ] **Step 3: The edits** — `factory-task` (the arm select, the codex branch of the model block with `factory_codex_config_value`, the seed skipped, the launch arm, the banner window, the usage arm, the classifier's copy, the `seat: codex` line), `factory-brief` (the placeholders), `factory-codex-usage.py` (above), the README.
- [ ] **Step 4: Run green** — `nix develop -c ruff format tools/factory/seat/factory-codex-usage.py`; `nix develop -c treefmt`; `nix develop -c bats tests/unit/95-codex-arm.bats tests/unit/94-seat-harness.bats tests/unit/80-seat-driver.bats`; `git add tools/factory/seat/factory-codex-usage.py tests/unit/95-codex-arm.bats`; `python3 pkgs/evidence/repomap.py --root . write` (two new files); `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–18; the discriminating fixtures are the three spellings outside the rule, empty against unset, the decoy `model:`/`session id:` lines echoed after the banner, the profile-table config, the newer-and-later decoy rollout against the id, the older decoy against the marker, the no-rollout run (events 0), the keywords in the brief against the keywords in the reply, the three `--version` outputs, the null-info tail and the torn line.

**Relaunch:** `ca1b` with `"CA1"`; the diff stays in `~/factory/ws/ca1/CA1`.

**touches:** tools/factory/seat/factory-task, tools/factory/seat/factory-brief, tools/factory/seat/factory-codex-usage.py, tests/unit/95-codex-arm.bats, tools/factory/seat/README.md
**acceptance:** unit, lint
**commit subject:** `seat: the codex arm of the driver — FACTORY_SEAT=codex selects codex exec in the workspace clone, the .result from the banner and the rollout, the classifier fed the agent's output only, the codex trailers in the brief (test: unit, lint)`

### CA2 (code, XS) — the brief's `Seats (7 d)` line: per model, runs, done, median wall and billed tokens from the `.result` files of the last seven days

**dependsOn:** SH5

**Files:**
- Modify: `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`

**Interfaces:**

- `seat_stats(runs_dir, now=None, days=7) -> list[dict]` (new, `pkgs/evidence/tasks.py`): reads every `<runs_dir>/*/*.result` whose mtime is ≥ `now − days·86400` (`now` defaults to `time.time()`; a `.log`, a `.pid`, a dot-file or the store is never opened); a file that cannot be read, or has no `^FACTORY-RESULT status=` line, is skipped. Per file: `model` = the first `^model:` line's value, `unknown` when absent; `done` = the **last** `^FACTORY-RESULT status=(\S+)` word equals `done`; the wall sample = the `^wall_s:` line's value when it is an integer, else no sample; `billed` += `input` + `output` of the `^usage:` line's JSON when it parses to an object and each is an int (a `bool` is not an int; a missing key adds 0). Returns rows `{"model", "runs", "done", "wall": [ints], "billed"}` sorted by `runs` descending, then `model` ascending.
- `render_seats_line(stats) -> str` (new): `**Seats (7 d):** none` when empty, else `**Seats (7 d):** ` + rows joined by ` · `, each `<model>: <n> run|runs, <done> done, <wall> min, <billed> billed` with `run` for 1 and `runs` otherwise, `<wall>` = `(statistics.median_low(samples) + 30) // 60` or `?` with no sample.
- `render_brief(graph, claims_rows=None, today=None)`: after the `**Record (7 d):**` (or `**Record: unavailable**`) line, one line `render_seats_line(seat_stats(graph["runs_dir"], now=graph.get("now")))` when `graph.get("runs_dir")` is set, else `**Seats (7 d):** none`. `build()` and `main()` put `"runs_dir": <the runs dir they scanned>` into the graph dict (`main`: `args.runs_dir`); `render_board_block` is untouched (it never calls `render_brief`).
- Consumers: the operator and the orchestrator (the brief, `evidence tasks brief`); nothing parses the line. Imports added: `statistics` (`json`, `glob`, `os`, `re`, `time`, `pathlib` are already imported).

```python
SEATS_DAYS = 7


def seat_stats(runs_dir, now=None, days=SEATS_DAYS):
    """Per-model rows from the `.result` files under `runs_dir` whose mtime is
    within `days` days of `now` — a `.log` is never opened. model: the `model:`
    line (`unknown` when absent); runs; done: the last `FACTORY-RESULT status=`
    word is `done`; wall: the int `wall_s:` samples; billed: the `usage:` JSON's
    `input` + `output`. Sorted by runs descending, then model."""
    now = time.time() if now is None else now
    cutoff = now - days * 86400
    rows = {}
    for p in glob.glob(os.path.join(str(runs_dir), "*", "*.result")):
        try:
            if os.path.getmtime(p) < cutoff:
                continue
            text = pathlib.Path(p).read_text()
        except OSError:
            continue
        statuses = re.findall(r"^FACTORY-RESULT status=(\S+)", text, re.MULTILINE)
        if not statuses:
            continue
        model = _field(text, r"^model:[ \t]*(.+)$") or "unknown"
        row = rows.setdefault(
            model, {"model": model, "runs": 0, "done": 0, "wall": [], "billed": 0}
        )
        row["runs"] += 1
        if statuses[-1] == "done":
            row["done"] += 1
        wall = _field(text, r"^wall_s:[ \t]*(\d+)[ \t]*$")
        if wall is not None:
            row["wall"].append(int(wall))
        usage_line = _field(text, r"^usage:[ \t]*(.+)$")
        if usage_line:
            try:
                usage = json.loads(usage_line)
            except ValueError:
                usage = None
            if isinstance(usage, dict):
                for k in ("input", "output"):
                    v = usage.get(k)
                    if isinstance(v, int) and not isinstance(v, bool):
                        row["billed"] += v
    return sorted(rows.values(), key=lambda r: (-r["runs"], r["model"]))


def render_seats_line(stats):
    if not stats:
        return "**Seats (7 d):** none"
    parts = []
    for r in stats:
        runs = f"{r['runs']} run" if r["runs"] == 1 else f"{r['runs']} runs"
        wall = f"{(statistics.median_low(r['wall']) + 30) // 60} min" if r["wall"] else "? min"
        parts.append(f"{r['model']}: {runs}, {r['done']} done, {wall}, {r['billed']} billed")
    return "**Seats (7 d):** " + " · ".join(parts)
```

**Facts:**

- `sed -n '1503,1517p' pkgs/evidence/tasks.py` → `record = plan_defect_record(graph["repos"], today)` / `if record is None:` / `lines.append("**Record: unavailable**")` / `else:` … `lines.append(f"**Record (7 d):** {total} rej, {caused} plan ({parts})")` — the line the Seats line follows; `sed -n '1518,1519p'` → `running = []` / `for repo in graph["repos"]:` — the `**Running:**` block after it.
- `sed -n '354,360p' pkgs/evidence/tasks.py` → `def read_results(runs_dir, stale_after=DEFAULT_STALE_AFTER):` / `"""ONE entry per (repo, key): a .log counts as running only when …` — one entry per key, so it cannot count runs; `sed -n '374,382p'` → `for p in glob.glob(os.path.join(runs_root, "*", "*.result")):` … `status = _field(text, r"FACTORY-RESULT status=(\S+)")` — the glob and the field idiom `seat_stats` reuses; `sed -n '334,336p'` → `def _field(text, pattern):` / `m = re.search(pattern, text, re.MULTILINE)` / `return m.group(1).strip() if m else None`.
- `sed -n '745,772p' pkgs/evidence/tasks.py` → `def build(root, runs_dir, store, run=None, stale_after=DEFAULT_STALE_AFTER):` … `return {"generated": …, "repos": […], "configured_repos": […], "task_status": task_status}` — no `runs_dir` in the graph; `sed -n '1728,1745p'` → `graph = {"generated": …, "repos": [scan_repo(r, plan_status, args.runs_dir, args.store, …)], "configured_repos": configured_repos, "task_status": task_status}` — `main` builds its own dict; both gain `"runs_dir"`.
- `sed -n '1677p' pkgs/evidence/tasks.py` → `parser.add_argument("--runs-dir", default=DEFAULT_RUNS_DIR)`; `sed -n '60p' githooks/pre-commit` → `… --runs-dir /nonexistent --store /nonexistent check` — the hook never sees a runs root.
- `sed -n '1589,1605p' pkgs/evidence/tasks.py` → `def render_board_block(graph):` … `body = " · ".join(parts) if parts else "nothing queued"` / `return ("**Queued (derived from this tree; …" f"repos, and in-flight state, are in the session brief).** {body}\n")` — no call into `render_brief`.
- `sed -n '90,96p' tests/evidence/test_tasks.py` → `def write_result(runs_dir, run, key, status, workspace):` / `d = runs_dir / run` / `d.mkdir(parents=True, exist_ok=True)` / `(d / f"{key}.result").write_text(f"FACTORY-RESULT status={status}\nFACTORY-CHECKS lint=pass\n\nrun: {run}\nkey: {key}\nworkspace: {workspace}\nbranch: task/{key}\n")` — the fixture writer; `sed -n '464,489p'` → `test_brief_lists_counts_next_wave_and_operator_items` builds `g = repo_with(tmp_path, ["typed.md"], landed=[…], reviews=[…])` and calls `tk.render_brief({"generated": "2026-09-05T18:00:00Z", "repos": [g]}, claims)` with `assert len(md.splitlines()) <= 40` — the graph shape tests pass (no `runs_dir` → `none`).
- `cat tests/evidence/fixtures/results/done.result` → `model: deepseek/deepseek-v4-pro-0813` / `wall_s: 123` / `usage: {"input":10,"output":5,"cacheRead":1,"reasoning":2,"events":40,"duration_s":12.5}` — the line shapes.
- `sed -n '224,243p' tools/factory/seat/factory-wave` → `wall_s=$(grep -m1 '^wall_s:' "$resfile" | awk '{print $2}')` … `in_tok=$(printf '%s' "$usage_line" | sed -nE 's/.*"input": ?([0-9]+).*/\1/p')` — the same two fields the wave summary reads.

- [ ] **Step 1: Write the failing tests** — `tests/evidence/test_tasks.py`, with a helper `_seat_result(model, status, wall_s, usage)` returning `FACTORY-RESULT status=<status>\nFACTORY-CHECKS lint=pass\n\nrun: r\nkey: K\nmodel: <model>\nwall_s: <wall_s>\nworkspace: /gone\n\nusage: <usage>\n` (a line is dropped when its argument is `None`) and `_write_aged(runs, run, key, text, age_days, now)` that writes `<runs>/<run>/<key>.result` and `os.utime`s it to `now − age_days·86400`; `NOW = 1_800_000_000`:

| # | assertion | discriminating fixture | mutant |
|---|---|---|---|
| S1 | four results — `gpt-6-astra`, `done`, `2400`, `{"input": 68620, "output": 13584}` at 1 d; `deepseek/deepseek-v4-pro-0813`, `done`, `600`, `{"input": 100, "output": 50}` at 6 d; the same model, `failed`, `1200`, `{"input": 10, "output": 5}` at 2 d; `two-status-model` at 1 d whose block holds `FACTORY-RESULT status=failed` then `FACTORY-RESULT status=done` (the driver's demotion rewrite shape), no `wall_s:`, no `usage:` → `render_seats_line(seat_stats(runs, now=NOW))` == `**Seats (7 d):** deepseek/deepseek-v4-pro-0813: 2 runs, 1 done, 10 min, 165 billed · gpt-6-astra: 1 run, 1 done, 40 min, 82204 billed · two-status-model: 1 run, 1 done, ? min, 0 billed` | three models, one failed run, a 6-day-old file, the two-status file | `billed` = `input` only → `68620`; sort by name → `gpt-6-astra` first; `statistics.median` → `900` → `15 min`; the first status word instead of the last → `two-status-model: 1 run, 0 done`; `run` unpluralised → `2 run`; the samples' mean → `40 min` unchanged but `15 min` for deepseek |
| S2 | an 8-day-old result (`old-model`, done) beside the 6-day one, plus a `K2.log` in a run dir whose text is a valid result for `log-model`, plus a `.marker-K3.x` file → the line names neither `old-model` nor `log-model`; `len(seat_stats(runs, now=NOW)) == 1` | 6 d in, 8 d out; the log-shaped `.log` | drop the cutoff → `old-model`; glob `*` → `log-model` |
| S3 | an empty runs dir → `**Seats (7 d):** none`; `render_brief({"generated": "t", "repos": [g]})` (no `runs_dir`) contains `**Seats (7 d):** none`; a result without `model:` → `unknown: 1 run, …`; without `wall_s:` → `? min`; without `usage:` → `0 billed`; `usage: {"input": true, "output": "5"}` → `0 billed`; `usage: not-json` → `0 billed`; a file with `FACTORY-CHECKS` but no `FACTORY-RESULT` line → not counted | every absent or wrong-typed field | `str` default for `model` → `None: …`; `median_low([])` → `StatisticsError`; count `True` as 1 |
| S4 | the CLI: a root with `repos.toml` naming one repo (the `test_cli_check_and_json` shape), `--runs-dir <runs>` holding S1's files with a `workspace:` pointing at a `.git/config` whose origin is `…/base/nixos-agent-env` (the `make_workspace` helper) → `brief` output contains the S1 line right after the `**Record` line (`lines[i+1]` where `lines[i].startswith("**Record")`); with `--runs-dir /nonexistent` → `**Seats (7 d):** none` | the CLI path | `main` not setting `graph["runs_dir"]` → `none`; the line appended after `**Running:**` → the adjacency |
| S5 | `tk.render_board_block(g)` does not contain `Seats`; `tk.render_brief({"generated": "t", "repos": [g]})` still has ≤ 40 lines | the board block | add the line to the block → red |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence/test_tasks.py -q -k seats` → `AttributeError: module 'tasks' has no attribute 'seat_stats'`; paste the line in the commit body.
- [ ] **Step 3: The edits** — `seat_stats`, `render_seats_line`, the one line in `render_brief`, `"runs_dir"` in `build` and `main`, `import statistics`.
- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix develop -c githooks/pre-commit` (the hook's `check` runs with `--runs-dir /nonexistent`: the queue block is unchanged).
- [ ] **Step 5: Commit.**

**Tests:** rows S1–S5; the discriminating fixtures are the 6-day file against the 8-day one, the result-shaped `.log`, the two-status file, the wrong-typed usage, the CLI's `/nonexistent` runs root.

**Relaunch:** `ca1b` with `"CA2"`; the diff stays in `~/factory/ws/ca1/CA2`.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the brief's Seats line — per model, runs, done, median wall and billed tokens from the .result files of the last seven days (test: evidence-unit, lint)`

### CA3 (code, S) — the fence and the ingest accept `route: codex/<kind>/<size>`: `ROUTE_IMPL_RE`, the stream regex, the schema row, a CX1b-shaped fixture

**dependsOn:** SH4, SH5

**Files:**
- Create: `tests/evidence/fixtures/results/codex.result`
- Modify: `pkgs/evidence/ingest_result.py`, `pkgs/evidence/streams.py`, `pkgs/evidence/SCHEMA.md`, `tests/evidence/test_ingest_result.py`, `tests/evidence/test_streams_policy.py`

**Interfaces:**

- `pkgs/evidence/ingest_result.py`: `ROUTE_IMPL_RE = re.compile(r"^(?:implement|codex)/(code|docs)/(XS|S|M|L)$")` — the family group is non-capturing so `_route_fields` keeps returning `(route_line, m.group(1) = kind, m.group(2) = size)`; `codex/code/XS` → `("codex/code/XS", "code", "XS")`; `codex/any/any`, `codex/code/XL`, `Codex/code/XS`, `codex/code/XS/x` → `("unknown", "unknown", "unknown")` (the fence's `unknown` arm, never a refusal). The `seat: codex <uuid>` line matches neither `SEAT_UNIT_RE` nor `SUBMIT_FAILED_RE` and is ignored (`seat_unit` stays `None`, `submit_failed` `False`) — the spec's rule.
- `pkgs/evidence/streams.py`, `KINDS["task-result"]["fields"]["route"]` = `("re", r"^(explicit|unknown|(implement|codex)/(code|docs)/(XS|S|M|L))$")`; a value outside it is refused with `route: not a re` (the fence's message for a `re` class) and the row is counted refused.
- `pkgs/evidence/SCHEMA.md`: the `derived/tasks` sentence names `route` in `explicit|unknown|implement/<kind>/<size>|codex/<kind>/<size>` (`<kind>` in `code|docs`, `<size>` in `XS|S|M|L`).
- The fixture `tests/evidence/fixtures/results/codex.result` (CX1b's shape, a made-up session id, no key material):

```
FACTORY-RESULT status=done
FACTORY-CHECKS version=pass config=pass config-rejects-typo=pass config-precedence=pass wrapper-path=pass module-eval=pass lint=pass
FACTORY-COMMITS 5
FACTORY-NOTES the flake builds and its seven checks are green; MINORs 1, 3, 4 and 5 left for CX2

run: cx1b
key: CX1b
model: gpt-6-astra
effort: medium
route: codex/code/XS
workspace: /gone/base/ws/cx1b/CX1b
seat: codex 0f1e2d3c-4b5a-4c6d-8e9f-0a1b2c3d4e5f
branch: task/CX1b
head: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
base: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
wall_s: 2400
exit_code: 0
error_class: none

commits (base..task/CX1b):
a58b3aa docs: record precedence and red-green evidence with prose tooling (test: lint)
853a760 json: pin nixpkgs and validate lock formatting (test: lint)
305f6de nix: package pinned Codex and enforce managed settings (test: version, config, config-rejects-typo, config-precedence, wrapper-path, module-eval, lint)
dd3b2e4 shell: add strict config and wrapper probes with tooling (test: version, config, config-rejects-typo, config-precedence, wrapper-path, lint)
e12c468 toml: add formatting and lint gate (test: lint)

diffstat:
 15 files changed, 612 insertions(+), 0 deletions(-)

usage: {"model": "gpt-6-astra", "events": 239, "input": 68620, "output": 13584, "cacheRead": 1642368, "reasoning": 3631, "duration_s": 2400.0}
```

**Facts:**

- `grep -n 'ROUTE_IMPL_RE' pkgs/evidence/ingest_result.py` → `37:ROUTE_IMPL_RE = re.compile(r"^implement/(code|docs)/(XS|S|M|L)$")` / `80:    m = ROUTE_IMPL_RE.fullmatch(route_line)`; `sed -n '74,84p'` → `def _route_fields(route_line):` … `if route_line == "explicit":` / `return "explicit", "unknown", "unknown"` / `m = ROUTE_IMPL_RE.fullmatch(route_line)` / `if m:` / `return route_line, m.group(1), m.group(2)` / `return "unknown", "unknown", "unknown"` (the packet's target reader looked for the constant in `streams.py`; it lives in the ingest).
- `sed -n '33,36p' pkgs/evidence/ingest_result.py` → `SEAT_UNIT_RE = re.compile(r"^seat: unit seat@([0-9]{8}-[0-9]{6}-[0-9a-f]{6})$", re.MULTILINE)` / `SUBMIT_FAILED_RE = re.compile(r"^seat: submit failed", re.MULTILINE)`.
- `sed -n '280p' pkgs/evidence/streams.py` → `"route": ("re", r"^(explicit|unknown|implement/(code|docs)/(XS|S|M|L))$"),`; `sed -n '597,599p'` → `elif isinstance(cls, tuple) and cls[0] == "re":` / `if not (isinstance(value, str) and re.fullmatch(cls[1], value)):` / `errors.append(f"{path}: not a re")`; `sed -n '22p'` → `MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}(/[a-z0-9][a-z0-9._-]{0,63})?$")` (`gpt-6-astra` matches).
- `sed -n '12,15p' pkgs/evidence/SCHEMA.md` → `` `derived/` or `ledger/`; `derived/tasks` (kind `task-result`, key `(run_id, key)`, classification `` / `` field `task_kind` in `code|docs|unknown`, `status` in `done|partial|failed|skipped|unreported|unknown`, `` — the sentence that gains `route`.
- `sed -n '130,175p' tests/evidence/test_streams_policy.py` → `TASK_RESULT = {"kind": "task-result", … "route": "explicit", …}` — the valid row; `sed -n '355,358p'` → `def test_one_valid_row_per_kind_and_shape(kind, row):` / `assert streams.validate(kind, row) == []`; `grep -n 'implement/' tests/evidence/test_streams_policy.py` → nothing (no literal pins the route regex today).
- `sed -n '56,125p' tests/evidence/test_ingest_result.py` → `result_text(*, status=…, route="implement/code/S", … seat=None, …)` and `_write(tmp_path, run, key, text, fixture=None)` (`fixture` copies `FIXTURES / fixture`); `sed -n '177,192p'` → `test_done_result_produces_one_full_row` reads `done.result` and asserts `row["route"] == "implement/code/S"`; `sed -n '499,526p'` → `test_unknown_effort_route_and_refused_model`: `route="bogus"` → `row2["route"] == "unknown"`, `task_kind`/`size` `unknown` — the idiom the codex rows copy.
- `git -C ~/flakes/codex log -5 --format='%h %s'` → the five subjects in the fixture's commit block (a58b3aa … e12c468); `cat -n tests/evidence/fixtures/results/done.result` → `workspace: /gone/base/ws/tel2/T2` — a gone workspace yields `repo: None`, as in the fixture.

- [ ] **Step 1: Write the failing tests.** Pytest, `tests/evidence/test_ingest_result.py`:

| # | assertion | discriminating fixture | mutant |
|---|---|---|---|
| I1 | `codex.result` ingested → `route == "codex/code/XS"`, `task_kind == "code"`, `size == "XS"`, `model == "gpt-6-astra"`, `effort == "medium"`, `commits == 5`, `commits_declared == 5`, `usage == {"in": 68620, "out": 13584, "cache_read": 1642368, "reasoning": 3631, "events": 239, "duration_s": 2400.0}`, `seat_unit is None`, `error_class == "none"`, `repo is None`, `files_changed == 15`; exit 0, `ingested 1 rows into derived/tasks (0 refused)` | the CX1b shape | `ROUTE_IMPL_RE` unchanged → `unknown`; a capturing family group → `task_kind == "codex"`; `SEAT_UNIT_RE` widened to `seat: (unit seat@\|codex )…` → `seat_unit` not `None` |
| I2 | `result_text(route="codex/any/any")`, `route="codex/code/XL"`, `route="Codex/code/XS"`, `route="codex/code/XS/x"` → each `route`, `task_kind`, `size` all `"unknown"`, none refused; `route="codex/docs/M"` → `("codex/docs/M", "docs", "M")` | one payload per rule | `[a-z]+` for the kind → `codex/any/any` accepted; `re.match` instead of `fullmatch` → the `/x` suffix accepted; `re.IGNORECASE` → `Codex` accepted |

  `tests/evidence/test_streams_policy.py`:

| # | assertion | discriminating fixture | mutant |
|---|---|---|---|
| P1 | `streams.validate("task-result", {**TASK_RESULT, "route": "codex/docs/M"}) == []` and the same for `"codex/code/XS"`, `"implement/code/S"`, `"explicit"`, `"unknown"` | every family × one arm | leave the regex → `["route: not a re"]` |
| P2 | `{**TASK_RESULT, "route": "codex/any/any"}` → `["route: not a re"]`; `"codex"` → the same; `"Codex/code/XS"` → the same; `"codex/code/XL"` → the same | one payload per rule | `codex/[a-z]+/[a-z]+` → `codex/any/any` passes |
| P3 | `streams.KINDS["task-result"]["fields"]["route"][1] == r"^(explicit|unknown|(implement|codex)/(code|docs)/(XS|S|M|L))$"` — the literal pin | — | any drift of the pattern |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence/test_ingest_result.py -q -k codex` → `assert 'unknown' == 'codex/code/XS'`; `nix develop -c pytest tests/evidence/test_streams_policy.py -q -k 'codex or route_literal'` → `assert ['route: not a re'] == []`. Paste both lines in the commit body.
- [ ] **Step 3: The edits** — the two regexes, the SCHEMA sentence, the fixture.
- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q`; `git add tests/evidence/fixtures/results/codex.result`; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows I1–I2, P1–P3; the discriminating fixtures are the CX1b-shaped file, `codex/any/any` against `codex/docs/M`, the `/x` suffix, the capitalised family, the literal pin.

**Relaunch:** `ca1b` with `"CA3"`; the diff stays in `~/factory/ws/ca1/CA3`.

**touches:** pkgs/evidence/ingest_result.py, pkgs/evidence/streams.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_ingest_result.py, tests/evidence/test_streams_policy.py, tests/evidence/fixtures/results/codex.result
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the task-result fence and the ingest accept route codex/<kind>/<size> — a CX1b-shaped fixture (test: evidence-unit, lint)`

### CX2 (code, S) — the CX1b MINORs on `~/flakes/codex`: MAP currency checked, precedence proven for `features.plugins` and the otel exporters, no check dials `api.openai.com`, `config-precedence` skipped without user namespaces

**dependsOn:** CA1, CA3
**repo:** codex

**Files (in the workspace clone of `~/flakes/codex`):**
- Create: `tests/map.sh`
- Modify: `flake.nix` (a `map` check; `config-precedence` gains `pkgs.util-linux`, the skip probe and the negative control), `tests/config.sh`, `tests/precedence.sh`, `docs/MAP.md`, `README.md` (the Checks list), `docs/VALIDATION.md` (the reds, the mutant, the otel gap)

**Interfaces:**

- `tests/map.sh <source-root>` (bash, shellcheck-clean, shfmt-formatted): exit 0 iff the set of regular files under `<source-root>` (relative paths; `.git` excluded — the flake's `${self}` holds tracked files only, so `result` and the like are absent) equals the set of paths named by the lines of `docs/MAP.md` matching `` ^- `([^`]+)`: ``; each missing entry prints `map: missing from docs/MAP.md: <path>`, each stale entry `map: not in tree: <path>`, exit 1 with any. A `docs/MAP.md` that cannot be read → `map: no docs/MAP.md`, exit 1.

```bash
#!/usr/bin/env bash
# Assert docs/MAP.md names every file in the tree and nothing else.
set -euo pipefail
cd "$1"
map=docs/MAP.md
[ -r "$map" ] || {
  printf 'map: no %s\n' "$map"
  exit 1
}
tree_list=$(find . -type f ! -path './.git/*' | sed 's#^\./##' | LC_ALL=C sort)
map_list=$(sed -nE 's/^- `([^`]+)`:.*$/\1/p' "$map" | LC_ALL=C sort)
status=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if ! grep -qxF -- "$f" <<<"$map_list"; then
    printf 'map: missing from %s: %s\n' "$map" "$f"
    status=1
  fi
done <<<"$tree_list"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if [ ! -f "$f" ]; then
    printf 'map: not in tree: %s\n' "$f"
    status=1
  fi
done <<<"$map_list"
exit "$status"
```

- `flake.nix`: `checks.${system}.map = pkgs.runCommand "codex-map" { } ''bash ${./tests/map.sh} ${self}; touch "$out"''`; `config-precedence` becomes

```nix
        config-precedence =
          pkgs.runCommand "codex-config-precedence"
            {
              nativeBuildInputs = [
                pkgs.bubblewrap
                pkgs.util-linux
              ];
            }
            ''
              # the skip arm: a failing user-namespace probe prints the reason and exits 0
              mkdir -p "$TMPDIR/nouserns"
              printf '#!/bin/sh\nexit 1\n' >"$TMPDIR/nouserns/unshare"
              chmod +x "$TMPDIR/nouserns/unshare"
              PATH="$TMPDIR/nouserns:$PATH" bash ${./tests/precedence.sh} ${codex}/bin/codex ${renderedConfig} \
                | grep -F 'config-precedence: skipped'
              # the managed layer wins for every hardened key
              bash ${./tests/precedence.sh} ${codex}/bin/codex ${renderedConfig}
              # the negative control: the same bytes at /etc/codex/config.toml lose
              if bash ${./tests/precedence.sh} ${codex}/bin/codex ${renderedConfig} user; then exit 1; fi
              touch "$out"
            '';
```

- `tests/precedence.sh` (`<codex> <rendered managed config> [managed|user]`): (1) first, before `mktemp`: `if ! unshare -Ur true >/dev/null 2>&1; then printf 'config-precedence: skipped — unprivileged user namespaces unavailable (unshare -Ur true failed)\n'; exit 0; fi`. (2) The user config written to `$work_dir/codex/config.toml` sets every hardened key to a value its type rejects: `[sandbox_workspace_write]` `network_access = true` (kept), `[features]` `plugins = "yes"`, `[otel]` `exporter = "bogus"`, `trace_exporter = "bogus"`, `metrics_exporter = "bogus"`. (3) Every `codex` run inside `bwrap` carries `--setenv OPENAI_BASE_URL http://127.0.0.1:9`. (4) After `cat "$work_dir/report"`, the assertions by mode — `managed`: `test "$status" -ne 0` (no login); `grep -q '^model:'` (the banner: the managed values replaced the user's before deserialisation); `if grep -Fq 'Error loading config.toml' …; then exit 1; fi`; `grep -q '^sandbox: workspace-write'`; `! grep -Fq 'network access enabled'`; `if grep -Fq 'api.openai.com' "$work_dir/report"; then exit 1; fi`; then the effective-value probe: `bwrap … --setenv OPENAI_BASE_URL http://127.0.0.1:9 timeout 15 "$codex_bin" features list >"$work_dir/features" 2>&1 || true`, `cat "$work_dir/features"`, and `grep -Fx -- 'plugins                                  stable             false' "$work_dir/features"` — the line as measured 2026-09-07 19:55 on core with `codex -c features.plugins=false features list | grep '^plugins' | cat -A` → `plugins                                  stable             false$` (33 spaces after `plugins`, 13 after `stable`; the same binary in the check prints the same columns; with `features.plugins=true` the line ends `true`, so `-x` is what kills M3b); `user` (the same bytes at `$work_dir/etc/codex/config.toml`): `if grep -q '^model:' "$work_dir/report"; then exit 1; fi` (the bogus user values reach the deserialiser: no banner) and `if grep -Fq 'api.openai.com' …; then exit 1; fi`.
- `tests/config.sh`: the `env -i …` line gains `OPENAI_BASE_URL=http://127.0.0.1:9`; after `cat "$work_dir/report"` in both modes: `if grep -Fq 'api.openai.com' "$work_dir/report"; then exit 1; fi`.
- `docs/MAP.md`: entries for `README.md`, `.gitignore`, `docs/MAP.md`, `tests/map.sh`. The `tests/precedence.sh` and `tests/wrapper-path.sh` lines may move beside the other `tests/*.sh` entries for the reader's sake; `tests/map.sh` compares sets, not order, so their position is not an assertion of this task. `README.md` `## Checks`: a `map` bullet; `config-precedence`'s bullet gains "skipped, with a printed reason, when `unshare -Ur true` fails; also runs the negative control (the same bytes at `/etc/codex/config.toml` lose)"; a sentence "No check dials `api.openai.com`: every run redirects the provider base URL to a closed loopback port and asserts the host name is absent from its report." `docs/VALIDATION.md`: the reds below, the M3b mutant's red and green, and the stated gap "the otel exporters' effective values have no runtime observable the CLI prints; the overlay is proven by the bogus-value probe, the values are asserted at the Nix level by `module-eval`".

**Facts:**

- `sed -n '68,115p' ~/flakes/codex/flake.nix` → `checks.${system} = {` / `version = pkgs.runCommand "codex-version" { } ''` … `config = configCheck "valid";` / `config-rejects-typo = configCheck "typo";` / `config-precedence = pkgs.runCommand "codex-config-precedence" { nativeBuildInputs = [ pkgs.bubblewrap ]; } ''bash ${./tests/precedence.sh} ${codex}/bin/codex ${renderedConfig}` … `wrapper-path` … `module-eval = assert builtins.elem codex …; assert !testHost.config.programs.codex.settings.features.plugins; assert … otel.metrics_exporter == "none"; … otel.exporter == "none"; … otel.trace_exporter == "none"; …` / `lint = pkgs.runCommand "codex-lint" { nativeBuildInputs = [ formatter ]; } ''cp -R ${self} source … codex-treefmt --no-cache --tree-root . --walk filesystem --fail-on-change''`; `sed -n '43,58p'` → `configCheck = mode: pkgs.runCommand "codex-config-${mode}" { nativeBuildInputs = [ codex ]; } ''bash ${./tests/config.sh} ${codex}/bin/codex ${renderedConfig} ${mode}''`; `sed -n '26p'` → `renderedConfig = testHost.config.environment.etc."codex/managed_config.toml".source;`.
- `cat -n ~/flakes/codex/tests/precedence.sh` → `10  printf '[sandbox_workspace_write]\nnetwork_access = true\n' >"$work_dir/codex/config.toml"` / `11  if [[ $mode == managed ]]; then` / `12  cp "$config_file" "$work_dir/etc/codex/managed_config.toml"` / `13  else` / `14  cp "$config_file" "$work_dir/etc/codex/config.toml"` / `17  bwrap --unshare-net --die-with-parent --ro-bind /nix/store /nix/store \` … `20  --clearenv --setenv PATH "$PATH" --setenv HOME "$work_dir/home" \` / `21  --setenv CODEX_HOME "$work_dir/codex" \` / `22  timeout 15 "$codex_bin" --strict-config exec --sandbox workspace-write \` / `23  --skip-git-repo-check 'Reply OK.' >"$work_dir/report" 2>&1 || status=$?` / `26  test "$status" -ne 0` / `27  if grep -Fq 'Error loading config.toml' "$work_dir/report"; then exit 1; fi` / `28  grep -q '^model:' "$work_dir/report"` / `29  grep -q '^sandbox: workspace-write' "$work_dir/report"` / `30  ! grep -Fq 'network access enabled' "$work_dir/report"`.
- `cat -n ~/flakes/codex/tests/config.sh` → `17  env -i PATH="$PATH" HOME="$work_dir/home" CODEX_HOME="$work_dir/codex" \` / `18  timeout 15 "$codex_bin" --strict-config exec --sandbox read-only \` / `19  --skip-git-repo-check 'Reply OK.' >"$work_dir/report" 2>&1 || status=$?` / `25  grep -Fq 'unknown configuration field \`sandbox_workspace_write.network_acess\`' "$work_dir/report"` / `26  if grep -q '^model:' "$work_dir/report"; then exit 1; fi` (the typo mode: a config error prints no banner) / `28  if grep -Fq 'Error loading config.toml' "$work_dir/report"; then exit 1; fi` / `29  grep -q '^model:' "$work_dir/report"`.
- `git -C ~/flakes/codex ls-files` → 15 files: `.gitignore README.md docs/MAP.md docs/VALIDATION.md flake.lock flake.nix githooks/pre-commit nixosModules/default.nix pkgs/codex/default.nix tests/config.sh tests/lint-nix.sh tests/precedence.sh tests/version.sh tests/wrapper-path.sh treefmt.toml`; `cat ~/flakes/codex/docs/MAP.md` → 12 `- \`…\`:` entries; `README.md`, `.gitignore` and `docs/MAP.md` absent; `tests/precedence.sh` and `tests/wrapper-path.sh` are the last two lines, after `docs/VALIDATION.md` (the review's MINOR-1).
- `sed -n '43,56p' ~/flakes/codex/README.md` → `## Checks` … `- \`config-precedence\`: managed settings defeat a conflicting user config.` / `  Requires working unprivileged bubblewrap namespaces on the build machine.` … `Strict exec checks assert config loading, not exit 0: no login is available.` / `Runs are bounded to 15 seconds.`
- `sed -n '26,33p' ~/flakes/codex/nixosModules/default.nix` → `programs.codex.settings = {` / `features.plugins = lib.mkDefault false;` / `otel = { exporter = lib.mkDefault "none"; trace_exporter = lib.mkDefault "none"; metrics_exporter = lib.mkDefault "none"; };` / `sandbox_workspace_write.network_access = lib.mkDefault false;` — the four hardened keys the probe covers.
- `cat ~/flakes/codex/treefmt.toml` → `[formatter.shell] command = "shfmt" options = ["-i", "2", "-ci", "-w"] includes = ["*.sh", "githooks/pre-commit"]` / `[formatter.shellcheck] … includes = ["*.sh", …]` / `[formatter.markdown] command = "prettier"` / `[formatter.markdown-lint] command = "markdownlint" options = ["--disable", "MD013", "--"]` — a new `.sh` file and every `.md` edit are formatted and linted by `lint` with no list edit; `cat -n ~/flakes/codex/githooks/pre-commit` → `6  unset GIT_INDEX_FILE` / `7  nix fmt -- --fail-on-change` / `8  nix flake check`.
- `git -C ~/flakes/codex branch --show-current` → `main`; `git -C ~/flakes/codex config --get core.hooksPath` → `githooks` (local config, which a clone does not carry — `sed -n '170,178p' tools/factory/seat/factory-lib.sh`: "`git clone` never copies a source repo's *local* config"); `grep -c shellHook ~/flakes/codex/flake.nix` → `0` (the devShell sets no hook path — Global Constraints).
- `docs/reviews/2026-09-07-opus-review-cx1b-CX1b.md` (`sed -n '346,391p'`): MINOR-1 "It lists 12 entries for 15 tracked files … `README.md`, `.gitignore` and `docs/MAP.md` itself are absent … Nothing checks MAP currency"; MINOR-3 "The builder logs for `config`, `config-rejects-typo` and `config-precedence` all carry `ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket … url: wss://api.openai.com/v1/responses` … on a builder with sandboxing disabled these checks would make real egress attempts"; MINOR-4 "`config-precedence` needs nested unprivileged user namespaces … `README.md:52` discloses the requirement"; MINOR-5 "Setting `features.plugins = true` in the module leaves `config-precedence` green (measured: `MUT=M3b-plugins-true CHECK=config-precedence EXIT=0`)". Its `## Facts measured`: `Managed vs user config, by hand under bwrap | managed wins: no (network access enabled); the same bytes at /etc/codex/config.toml lose to the user file`; `Host nix sandbox | sandbox = true`.
- `ls ~/factory/base` → `dsh-harness … nixos-skill` and their `.lock` files, no `codex`: `factory-ws` creates `~/factory/base/codex` on this run (`sed -n '46,47p' tools/factory/seat/factory-ws` → `repo_name=$(basename -- "$repo_path")` / `base=$FACTORY_BASE/$repo_name`).

- [ ] **Step 0: The clone's hook path** — `git config core.hooksPath githooks` (the workspace is a fresh clone; the flake's devShell sets nothing).
- [ ] **Step 1: Write the failing tests and run them red.**

| # | assertion | discriminating fixture | mutant / red |
|---|---|---|---|
| X1 | `nix build .#checks.x86_64-linux.map -L --no-link` with `tests/map.sh` and the `map` check added and `docs/MAP.md` untouched → red: `map: missing from docs/MAP.md: .gitignore`, `… README.md`, `… docs/MAP.md`, `… tests/map.sh`, exit 1. Green after the MAP edit. | the four absent entries | delete the `README.md` line → red; add a line `` - `ghost.sh`: `` → `map: not in tree: ghost.sh`; drop `LC_ALL=C` and `-x` → a prefix (`tests/config.s`) passes |
| X2 | `config`, `config-rejects-typo`: with the `api.openai.com` assertion added before the env change → red on the review's own line (`url: wss://api.openai.com/v1/responses` in the report); green with `OPENAI_BASE_URL=http://127.0.0.1:9`, and the report then names `127.0.0.1:9` (assert `grep -Fq '127.0.0.1:9' "$work_dir/report"` in the valid mode) | the two modes | drop the env → red (Assumption 8's falsifier: if the URL still reads `api.openai.com` with the env set, the override is not honoured — report `partial` with the line pasted) |
| X3 | `config-precedence`, the skip arm: with the fake `unshare` invocation added to the check and no skip in the script → red (`grep -F 'config-precedence: skipped'` finds nothing: the script ran bwrap and passed); green with the probe | the fake `unshare` exiting 1 | drop the probe → red; print the reason but `exit 1` → red |
| X4 | `config-precedence`, the overlay probe: managed mode with the bogus user values → `^model:` present, no `Error loading config.toml`, `^sandbox: workspace-write`, no `network access enabled`, no `api.openai.com`; user mode → no `^model:` (the check's `if bash … user; then exit 1; fi` proves the probe can fail) | the same bytes at `/etc/codex/managed_config.toml` against `/etc/codex/config.toml` | the module renders no `[features]` (`features.plugins = lib.mkDefault false` deleted) → the user's `plugins = "yes"` reaches the deserialiser → no banner → red; the same for any one of the three otel keys deleted (Assumption 8's falsifier: a managed-mode run that prints no banner with the module intact means the overlay is post-deserialisation — report `partial` with the report pasted) |
| X5 | the effective-value probe: `codex features list` under the bwrap env, the `plugins` line pinned by its measured text; red by the mutant `features.plugins = lib.mkDefault true` in `nixosModules/default.nix` (the review's M3b: `config-precedence` was green with it) → the pinned line absent → red; restored → green | the module mutant | as stated; a `grep -F` without `-x` on a substring the enabled line also contains → M3b survives — pin the whole line |

- [ ] **Step 2: The edits** — `tests/map.sh`, `flake.nix`, `tests/precedence.sh`, `tests/config.sh`, `docs/MAP.md`, `README.md`, `docs/VALIDATION.md`.
- [ ] **Step 3: Run green** — `nix fmt -- --fail-on-change`; `nix build .#checks.x86_64-linux.map -L --no-link`; `… config`; `… config-rejects-typo`; `… config-precedence`; `… lint`; then `nix flake check -L` (`all checks passed!`).
- [ ] **Step 4: Commit** — one commit; the subject below; the trailers the WORKSPACE RULES state (`Generated-By: codex-cli <ver> / <model> (codex exec, factory run cx2)`, `Co-Authored-By: Codex CLI <ver> <noreply@openai.com>`); the hook runs `nix fmt` and `nix flake check`.

**Tests:** rows X1–X5; the discriminating fixtures are the four absent MAP entries and the ghost entry, the two config modes, the fake `unshare`, the managed file against the same bytes at the losing path, the module mutant.

**Relaunch:** `FACTORY_SEAT=codex … factory-wave cx2b /home/dalhaka/flakes/codex "CX2"`; the diff stays in `~/factory/ws/cx2/CX2`.

**touches:** tests/map.sh, flake.nix, tests/config.sh, tests/precedence.sh, docs/MAP.md, README.md, docs/VALIDATION.md
**acceptance:** map, config, config-rejects-typo, config-precedence, lint
**commit subject:** `checks: MAP currency, precedence proven for features.plugins and the otel exporters, no check dials api.openai.com, config-precedence skipped without user namespaces (test: map, config, config-rejects-typo, config-precedence, lint)`

### CA2b (code, XS) — CA2 fix round: the order pinned against a name-first fixture, the aged `.log` and `.pid` never opened, the unreadable file, the half-minute rounding, the first `model:` line and the missing usage key asserted, the green pasted

**dependsOn:** (CA2)

Typed by the orchestrator on 2026-09-08 from the ca1 gate, `docs/reviews/2026-09-08-opus-review-ca1-CA2.md` (REJECTED; plan_defect wrong-fact, secondary missing-case; 21 mutants tried, 14 killed; evidence-unit and lint green with `--rebuild`; the code correct against every probe — the tests the section specified do not discriminate: the S1 fixture's two orders coincide, the S2 `.log` was dropped by the cutoff, never by the glob). Rule A1: this is CA2's one fix round; a second rejection re-plans.

**Fresh workspace, step 1 (before anything else):** the workspace is a fresh clone of main; bring CA2's commit in uncommitted with `git fetch -q /home/dalhaka/factory/ws/ca1/CA2 task/CA2 && git cherry-pick -n FETCH_HEAD` (the branch's one commit 4ca0fe6), then take main's generated files: `git checkout HEAD -- docs/OPERATIONS.md docs/MAP.md && git add docs/OPERATIONS.md docs/MAP.md`. ONE commit at the end with this section's subject — CA2's subject is never reused.

**Contract — the review's items carried verbatim, each closed as stated:**

1. **MAJOR-1 (`pkgs/evidence/tasks.py:1663`) — "the section's S1 mutant 'sort by name' survives; 'sorted by `runs` descending' has no test":** on S1's fixture the two orders coincide — the 2-run model also sorts first by name. Close: S1's fixture renames the models so the 2-run model sorts LAST by name — `zeta-model` (2 runs: `done` / `600` / `{"input": 100, "output": 50}` at 6 d and `failed` / `1200` / `{"input": 10, "output": 5}` at 2 d) beside `alpha-model` (1 run, `done`, `2400`, `{"input": 68620, "output": 13584}` at 1 d) and `two-status-model` (as before) — and the assertion pins the whole line `**Seats (7 d):** zeta-model: 2 runs, 1 done, 10 min, 165 billed · alpha-model: 1 run, 1 done, 40 min, 82204 billed · two-status-model: 1 run, 1 done, ? min, 0 billed`. Mutants shown red and reverted: `key=lambda r: (r["model"],)` → `alpha-model` first; `key=lambda r: (r["runs"], r["model"])` → `alpha-model` first.
2. **MAJOR-2 (`tests/evidence/test_tasks.py:756-760`) — "the section's S2 mutant 'glob `*`' survives; 'a `.log` … is never opened' has no test":** the `.log` fixture was never aged, so at `NOW` the cutoff dropped it, not the glob. Close: a `K2.log` whose text is a valid result for `log-model`, a `K2.pid` whose text is a valid result for `pid-model`, and a dot-file `.marker-K3.x` whose text is a valid result for `dot-model`, each written with `_write_aged(…, age_days=1, now=NOW)` (`os.utime(p, (NOW - 86400, NOW - 86400))`) beside one aged-1-d result for `inside-model`; assert `[r["model"] for r in seat_stats(runs, now=NOW)] == ["inside-model"]`. Mutant: glob `*` → `log-model` and `pid-model` appear → red (the dot-file is never matched by Python's `glob` either way; it stays as the store-shaped decoy the Interfaces name).
3. **MINOR-1 (`pkgs/evidence/tasks.py:1636-1640`) — "the 'cannot be read' clause is untested":** a result file `chmod 000` (the row `pytest.skip`s when `os.geteuid() == 0`; the nix sandbox builds as a non-root user, so the row runs in `evidence-unit`) and a `<runs>/<run>` entry that is a regular file, beside one readable result → the line names only the readable model, no exception. Mutant: `except ValueError` in place of `OSError` → `PermissionError` propagates → red.
4. **MINOR-2 (`pkgs/evidence/tasks.py:1673`) — "the `+ 30` half-minute rounding is untested":** a result with `wall_s: 570` → `10 min`; another with `wall_s: 569` → `9 min`. Mutant: drop `+ 30` → `9 min` for 570 → red.
5. **MINOR-3 (`pkgs/evidence/tasks.py:1642`) — "the first `^model:` line is untested":** a result carrying `model: first-model` in its header and, after the diffstat, a second line `model: second-model` → counted under `first-model`, `second-model` absent. Mutant: take the last match → red.
6. **MINOR-4 (`pkgs/evidence/tasks.py:1731`) — "the `now=graph.get("now")` seam is inert":** delete the read — `render_seats_line(seat_stats(graph["runs_dir"]))` — no caller sets `now` in the graph; the tests call `seat_stats(…, now=NOW)` directly, as they do. Row S4 (the CLI adjacency) is unchanged.
7. **MINOR-6 (`pkgs/evidence/tasks.py:1658-1662`) — "'a missing key adds 0' is stated but never asserted":** `usage: {"input": 1}` → `1 billed`; `usage: {"output": 2}` → `2 billed`. Mutant: `usage["input"] + usage["output"]` (a `KeyError`) → red.
8. **MINOR-5 — "the commit body pastes the red but not the green":** this commit's body pastes, under its command line, each new assertion's red on the cherry-picked tree, every mutant of items 1–5 and 7 shown red and reverted, and the greens (`pytest tests/evidence -q`'s last line; `evidence-unit`'s and `lint`'s last lines).

MINOR-7 (process — the driver's `checks_scope: dirty` line named a difference that does not exist: the workspace blob equals `HEAD`'s) is the seat-harness plan's (SH4), recorded on the board for its owner, not owed here.

- [ ] **Step 1: Fresh workspace** — the cherry-pick and the two `git checkout HEAD --` files above.
- [ ] **Step 2: Write the failing tests** — items 1–5 and 7; **run red** on the cherry-picked tree (`nix develop -c pytest tests/evidence/test_tasks.py -q -k seats`): the new S1 line, the aged-`.log` row, the unreadable row, the 570 row, the two-`model:` row and the single-key row fail; paste.
- [ ] **Step 3: Change the code** — item 6 only; nothing else unless a red of Step 2 demands it (say what and why in the body).
- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `… lint`; `nix develop -c githooks/pre-commit`; then the mutants of items 1–5 and 7 applied, shown red, reverted — pasted.
- [ ] **Step 5: One commit** with the subject below, the two trailers, the body carrying every paste of item 8; end the reply with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them.

**Tests:** CA2's rows S1–S5 with S1 and S2 replaced as items 1–2 state, and rows S6–S9 added (the unreadable file and the file-shaped run dir; 570 and 569; the two `model:` lines; the single-key usages).

**Relaunch:** `ca1fb` with `"CA2b"`; the diff stays in `~/factory/ws/ca1f/CA2b`.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the brief's Seats line, fix round — the order pinned against a name-first fixture, the aged .log and .pid never opened, the unreadable file, the half-minute rounding, the first model line and the missing usage key asserted (test: evidence-unit, lint)`

### CA1b (code, S) — CA1 fix round: the tests' PATH holds no real `codex`, every negated assertion captures its status, the session-id rule, the copy's cleanup and the marker-branch message pinned, the green pasted

**dependsOn:** (CA1)

Typed by the orchestrator on 2026-09-08 from the ca1 gate, `docs/reviews/2026-09-08-opus-review-ca1-CA1.md` (REJECTED; plan_defect implementer, secondary vacuous; 52 mutants tried, 45 killed; unit and lint green with `--rebuild`; the dsh arm byte for byte intact — `80-seat-driver.bats` and `94-seat-harness.bats` 1..152 green). The arm is correct; two rows of its test file are not: one is red on core and reaches the real Codex CLI, one cannot fail. Rule A1: this is CA1's one fix round; a second rejection re-plans.

**Fresh workspace, step 1 (before anything else):** the workspace is a fresh clone of main; bring CA1's commit in uncommitted with `git fetch -q /home/dalhaka/factory/ws/ca1/CA1 task/CA1 && git cherry-pick -n FETCH_HEAD` (the branch's one commit 758b604), then take main's generated files: `git checkout HEAD -- docs/OPERATIONS.md docs/MAP.md && git add docs/OPERATIONS.md docs/MAP.md` (`python3 pkgs/evidence/repomap.py --root . write` regenerates the map at Step 4). ONE commit at the end with this section's subject — CA1's subject is never reused.

**Contract — the review's items carried verbatim, each closed as stated:**

1. **MAJOR-1 (`tests/unit/95-codex-arm.bats:246`, the helper's `PATH="$BIN:$PATH"` at `:222`) — "Row 2's test is red on this host and launches the real Codex CLI":** `NO_CODEX=1` only omits the fake from `$BIN`; the host's `/home/dalhaka/.local/bin/codex` stays reachable, `factory-task`'s `command -v codex` succeeds, and the driver goes on to `codex exec -c features.plugins=false -c otel.metrics_exporter="none" --sandbox danger-full-access --color never -` with the brief on stdin — a seat launch from a test (the gate proved it with a recording shim). Close: in `setup`, compute `SAFE_PATH` — the current `PATH` with every directory that holds an executable `codex` removed (`IFS=:` walk; `[ -x "$d/codex" ] || keep`) — and `run_codex_task` (and every other invocation of the driver in this file) passes `PATH="$BIN:$SAFE_PATH"`. Row 2 then exits 2 with `FACTORY_SEAT=codex but no codex on PATH` on core exactly as in the build sandbox, `$REC` absent, no run dir. A new row 19 pins the helper: with the fake absent, `command -v codex` under the helper's PATH prints nothing (assert on a probe script the helper runs, or on `$output` of a row that `run`s `command -v codex` through the same PATH). Mutant: `PATH="$BIN:$PATH"` restored → row 2 red on core (the gate runs on core; in a codex-free sandbox both spellings pass — say so in the body).
2. **MAJOR-2 (`tests/unit/95-codex-arm.bats:381`) — "Row 8's `no seat: line` assertion cannot fail":** `! grep -q '^seat:' …` mid-test is inert under bats (`set -e` ignores a negated command that is not the test's last command); the section's named mutant — `[ "$seat_arm" = codex ] && [ -n "$session_id" ]` → `[ "$seat_arm" = codex ]` — writes `seat: codex ` (an empty id) and the row stays green. Close: every negated assertion in the file becomes a status-capturing one — `[ "$(grep -c '^seat:' "$f" || true)" -eq 0 ]` (or `run grep -c … ; [ "$output" = 0 ]`); audit the file: `grep -n '^[[:space:]]*!' tests/unit/95-codex-arm.bats` must print nothing after the change. Mutant: the empty-id line → row 8 red.
3. **MINOR-1 (`tools/factory/seat/factory-task:324`) — "the 36-hex-and-dash session-id rule has no fixture":** a row with `FAKE_SID=not-a-uuid` → no `seat:` line (the status-capturing form), and — the fake having written its rollout under `rollout-…-not-a-uuid.jsonl` — the usage still parsed through the newest-since-marker fallback (`"input": 68620`), the log line `no banner and no rollout` absent. Mutant: the regex loosened to `(.+)` → `seat: codex not-a-uuid` appears → red.
4. **MINOR-2 and MINOR-3 (`factory-task:793`, `:803`) — "the classifier copy's `.log`-free template and its removal are untested":** after the default row, `ls "$FACTORY_RUNS/r1"` holds no entry matching `.agent-*` and no `*.log` other than `K1.log` and `wave-*.log` (list the directory into `$output` and assert with `[[ … ]]` or `grep -c`, never a negated command). Mutants: the `rm -f` replaced by `:` → `.agent-K1.*` present → red; the template given a `.log` suffix → a second `*.log` → red.
5. **MINOR-6 (`factory-task:759`) — "the marker-branch refusal message has no assertion":** a row with `FAKE_NO_BANNER=1 FAKE_NO_ROLLOUT=1` → `usage: {}`, `error_class: boot-failure` (events 0, wall < 10), `$output` contains `no banner and no rollout newer than the launch marker`. Mutant: the message dropped → red.
6. **MINOR-4 and MINOR-5 — the section's own mutants that cannot discriminate:** row 6's second mutant (the window widened to EOF) is ill-posed — the banner's line precedes every decoy, so `head -n1` wins whatever the window; row 14's mutant (`$?` for `${PIPESTATUS[0]}`) is equivalent under `set -o pipefail`. Both are struck from the Tests table by this section (the plan's, recorded here); the rows' other mutants stand. No test is deleted.
7. **Pasted:** this commit's body pastes, under its command line, row 2's red on the cherry-picked tree (`not ok 2 … [ "$status" -eq 2 ]' failed`) and the new rows' reds (items 2–5), every mutant of items 1–5 shown red and reverted, and the greens (`bats tests/unit/95-codex-arm.bats tests/unit/80-seat-driver.bats tests/unit/94-seat-harness.bats`'s last line; `unit`'s and `lint`'s last lines).

**Never run the real `codex`:** the fake in `$BIN` is the only `codex` any test may reach; a test that launches `/home/dalhaka/.local/bin/codex` is a seat launch and a MAJOR (Global Constraints). Item 1's `SAFE_PATH` is the mechanism; check it before Step 2 with `PATH="$BIN:$SAFE_PATH" command -v codex` printing `$BIN/codex`, and with the fake removed printing nothing.

- [ ] **Step 1: Fresh workspace** — the cherry-pick and the two `git checkout HEAD --` files above.
- [ ] **Step 2: Write the failing tests** — apply item 1 (`SAFE_PATH`) FIRST: never run the file while row 2 can reach the real binary. Then **run red** on the cherry-picked tree (`nix develop -c bats tests/unit/95-codex-arm.bats`): the new rows of items 2–5 red (row 8's status-capturing form against the cherry-picked driver is green — its red is the mutant of item 2, shown at Step 4); row 2's red is the mutant of item 1 (`PATH="$BIN:$PATH"` on a copy, on core: `not ok 2 … [ "$status" -eq 2 ]' failed`), shown at Step 4 too; paste.
- [ ] **Step 3: Change the code** — nothing in `factory-task` unless a red of Step 2 demands it (say what and why in the body); the test file only.
- [ ] **Step 4: Run green** — `nix develop -c treefmt`; `nix develop -c shellcheck tools/factory/seat/factory-task tools/factory/seat/factory-brief`; `nix develop -c bats tests/unit/95-codex-arm.bats tests/unit/80-seat-driver.bats tests/unit/94-seat-harness.bats`; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `… lint`; `nix develop -c githooks/pre-commit`; then the mutants of items 1–5 applied, shown red, reverted — pasted.
- [ ] **Step 5: One commit** with the subject below, the two trailers after a blank line, the body carrying every paste of item 7; end the reply with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them.

**Tests:** CA1's rows 1–18 with row 2 made host-independent (item 1), row 8 made falsifiable (item 2), rows 6 and 14 with one mutant each struck (item 6), and rows 19–22 added (the helper's PATH probe; the malformed session id; the run dir's cleanup; the no-banner-no-rollout message).

**Relaunch:** `ca1fab` with `"CA1b"`; the diff stays in `~/factory/ws/ca1fa/CA1b`.

**touches:** tools/factory/seat/factory-task, tools/factory/seat/factory-brief, tools/factory/seat/factory-codex-usage.py, tests/unit/95-codex-arm.bats, tools/factory/seat/README.md
**acceptance:** unit, lint
**commit subject:** `seat: the codex arm of the driver, fix round — the tests' PATH holds no real codex, every negated assertion captures its status, the session-id rule, the copy's cleanup and the marker-branch message pinned (test: unit, lint)`

### CX2b (code, S) — CX2 fix round on measured facts: no check dials `api.openai.com` through a loopback provider, precedence proven for `features.plugins` and `network_access` with valid conflicting values, the otel keys' gap documented, MAP currency and the skip arm carried

**dependsOn:** (CX2)
**repo:** codex

Typed by the orchestrator on 2026-09-08 from CX2's honest `partial` (`~/factory/runs/cx2/CX2.result`: `FACTORY-NOTES Assumption 8 falsified twice; evidence retained, no workaround or hook bypass`; the evidence in the workspace's `docs/VALIDATION.md` under "CX2: partial, assumptions falsified"; no commit, the work staged). The plan's Assumption 8 was wrong twice and is corrected above; this section carries the corrected mechanisms. Rule A1: this is CX2's one fix round; a second `partial` or a rejection re-plans.

**Fresh workspace, step 1 (before anything else):** the workspace is a fresh clone of `~/flakes/codex` at `main` (a58b3aa); bring CX2's staged work in with `git -C /home/dalhaka/factory/ws/cx2/CX2 diff --cached | git apply --index` (X1's `tests/map.sh` and the `map` check, X3's skip arm, the `docs/MAP.md`, `README.md` and `docs/VALIDATION.md` edits, and the abandoned X2/X4 edits this section replaces). Run `git config core.hooksPath githooks`. ONE commit at the end with this section's subject.

**Contract — each item closed as stated, every fact below measured on core 2026-09-08 03:25–03:35:**

1. **No check dials `api.openai.com` (replaces CX2's X2 and D10's `OPENAI_BASE_URL`):** `OPENAI_BASE_URL` is not honoured by the websocket endpoint and `[model_providers.openai]` is refused (`reserved built-in provider IDs`). Each test's USER config (the file the scripts write fresh per run under `$work_dir/codex/config.toml`) declares `model_provider = "loop"` and `[model_providers.loop]` with `name = "loop"`, `base_url = "http://127.0.0.1:9"`, `wire_api = "responses"`. `tests/config.sh` (both modes) and `tests/precedence.sh` (both modes) assert, after `cat "$work_dir/report"`: `grep -q '^provider: loop' "$work_dir/report"` and `if grep -Fq 'api.openai.com' "$work_dir/report"; then exit 1; fi`. The run ends by `timeout 15` (the binary prints `ERROR: Reconnecting... waiting for network` against the closed port) — `test "$status" -ne 0` stays. The typo mode keeps its `unknown configuration field` assertion (a config error prints no banner and dials nothing). Mutant: the four provider lines dropped from the user config → `provider: openai` and `wss://api.openai.com/v1/responses` in the report → red.
2. **Precedence for `features.plugins` at runtime (X5, the M3b killer):** in `tests/precedence.sh`'s managed mode, after the exec assertions, the effective-value probe `bwrap … --setenv CODEX_HOME "$work_dir/codex" "$codex_bin" features list >"$work_dir/features" 2>&1 || true`, `cat "$work_dir/features"`, `grep -Fx -- 'plugins                                  stable             false' "$work_dir/features"` (33 spaces after `plugins`, 13 after `stable`; the user config sets `plugins = true`). User mode (the same managed bytes at `$work_dir/etc/codex/config.toml`): the same probe must print the line ending `true` — assert `grep -Fx -- 'plugins                                  stable             true' "$work_dir/features"` — the negative control that proves the probe can fail. Mutant: `features.plugins = lib.mkDefault false` deleted from `nixosModules/default.nix` → managed mode prints `true` → red (the review's M3b dies at runtime).
3. **Precedence for `network_access` (X4 rewritten with VALID values):** the user config sets `[sandbox_workspace_write] network_access = true` (as today) and `[features] plugins = true`; NO bogus-typed value anywhere (a wrong-typed user value is a config error under `exec` whatever the managed file says — `invalid type: string "yes", expected a boolean` — CX2's measurement); no `[otel]` table in the user config (`exporter = "otlp-http"` is a struct variant and fails to load: `invalid type: unit variant, expected struct variant`). Managed mode: `^model:` present, no `Error loading config.toml`, `^sandbox: workspace-write`, no `network access enabled`; user mode: `network access enabled` present (measured: `sandbox: workspace-write [workdir, /tmp, $TMPDIR] (network access enabled)`), so `if bash … user; then exit 1; fi` in the check proves the probe can fail. Mutant: `sandbox_workspace_write.network_access = lib.mkDefault false` deleted from the module → managed mode prints `network access enabled` → red.
4. **The otel keys — the documented gap:** no runtime observable prints them (`codex features list` and `codex doctor` do not) and no valid bare-string alternative to `"none"` exists for a conflicting user value; their precedence is asserted at the Nix level by `module-eval` only. `README.md` (`## Checks`, the `config-precedence` bullet) and `docs/VALIDATION.md` say so in one sentence each; nothing claims a runtime proof for them.
5. **X1 (MAP currency) and X3 (the skip arm, the negative control, `pkgs.util-linux`) as CX2 staged them:** carried unchanged; their reds are already in `docs/VALIDATION.md` (CX2's section) and are pasted again in this commit's body.
6. **The trust write:** `codex exec` in a git worktree appends `[projects."<workdir>"] trust_level = "trusted"` to the user config it can write (measured); the scripts create the user config fresh per run and never assert on its bytes after a run — say so in a comment above the `printf` that writes it.
7. **`docs/VALIDATION.md`:** replace CX2's "partial, assumptions falsified" section with "CX2b: measured mechanisms" — the four facts of Assumption 8 (corrected), each with the command and the line it printed; the reds of items 1–3 and the M3b mutant's red; the greens.
8. **Commit:** one commit, the subject below, the trailers `Generated-By: codex-cli <ver> / <model> (codex exec, factory run cx2f)` and `Co-Authored-By: Codex CLI <ver> <noreply@openai.com>` after a blank line; the hook runs `nix fmt -- --fail-on-change` and `nix flake check` — every check green before the commit exists (`never ship a check you know is red`).

- [ ] **Step 1: Fresh workspace** — the staged-diff apply and the hook path above; `git status` shows the carried files staged.
- [ ] **Step 2: Run red** — with the provider lines absent: `nix build .#checks.x86_64-linux.config -L --no-link` red on `api.openai.com` in the report (item 1's mutant state, which is CX2's state); with the managed `[features]` deleted in a scratch copy: `config-precedence` red on the `true` line (item 2); paste both.
- [ ] **Step 3: The edits** — `tests/config.sh`, `tests/precedence.sh` (the provider block, the assertions, the probe, the comment of item 6), `flake.nix` (as CX2 staged it: the `map` check, `config-precedence`'s `util-linux`, skip arm and negative control), `README.md`, `docs/VALIDATION.md`.
- [ ] **Step 4: Run green** — `nix fmt -- --fail-on-change`; `nix build .#checks.x86_64-linux.map -L --no-link`; `… config`; `… config-rejects-typo`; `… config-precedence`; `… lint`; `nix flake check -L` → `all checks passed!`; then the mutants of items 1–3 applied in a scratch copy, shown red, reverted — pasted.
- [ ] **Step 5: One commit** with the subject below; end the reply with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them.

**Tests:** CX2's rows X1 and X3 as staged; X2, X4 and X5 replaced by items 1–3 (the loopback provider, the two valid-value precedence proofs with their negative controls); the discriminating fixtures are the provider lines present against absent, the managed file against the same bytes at the defaults path, the module with and without each `mkDefault`.

**Relaunch:** `cx2fb` with `"CX2b"` (`FACTORY_SEAT=codex`); the diff stays in `~/factory/ws/cx2f/CX2b`.

**touches:** tests/map.sh, flake.nix, tests/config.sh, tests/precedence.sh, docs/MAP.md, README.md, docs/VALIDATION.md
**acceptance:** map, config, config-rejects-typo, config-precedence, lint
**commit subject:** `checks: MAP currency, precedence proven at runtime for features.plugins and network_access, no check dials api.openai.com through a loopback provider, config-precedence skipped without user namespaces (test: map, config, config-rejects-typo, config-precedence, lint)`
