# Deterministic model routing for the headless seat — plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver reads the `### KEY (kind, size) — title` section below.

**Goal:** the headless seat driver picks model and effort per task from one tweakable table in the repo, keyed on role × kind × size, instead of one hard-coded default for everything. The interactive seat the operator talks to on core is untouched (decision addendum in `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md`, 2026-09-05).

**Architecture:** `docs/ledger/routing.toml` holds `[[route]]` rows; `factory-lib.sh` gains a pure-bash lookup (the seat's host PATH has no python); `factory-task` (role implement) and `factory-review` (role review) resolve model and effort through it, with explicit `--model` / `OPENROUTER_MODEL` / `OPENROUTER_REASONING_EFFORT` still winning; the chosen route is recorded in the `.result` file. Tests in bats under the existing `unit` check; the real table is validated by a test that reads it.

**Evidence behind the first rows:** `docs/reviews/2026-09-05-m2b-effort-measurement.md` (effort off for XS docs) and `docs/reviews/2026-09-05-model-comparison.md` (Pro for code until n ≥ 5; Flash for docs/XS).

## Global Constraints

- Build-only; never `sudo`, `nixos-rebuild`, `systemctl`. Checks: `nix build .#checks.x86_64-linux.<name> -L --no-link`; lint gate `nix develop -c githooks/pre-commit`; commits via `nix develop -c git commit -F <msgfile>`.
- TDD, red first. Bash only in the seat scripts (no awk/sed/grep/python in the lookup — the seat runs on the bare host PATH; `mapfile` + `case` line walks, as `factory_copy_settings_without_selection` does). shellcheck clean.
- Do not touch `githooks/pre-commit`, `flake.nix`, `pkgs/evidence/*` (other tasks own them this afternoon).
- Commit subject as given, with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer.

## Tasks

### RT1 (code, S) — `routing.toml` and the driver's per-task model and effort

**dependsOn:** none

**Files:**
- Create: `docs/ledger/routing.toml`
- Modify: `tools/factory/seat/factory-lib.sh` (new `factory_route`, `factory_route_check`, `factory_task_kind_size`), `tools/factory/seat/factory-task` (model/effort resolution, `.result` line), `tools/factory/seat/factory-review` (same, role `review`), `tests/unit/80-seat-driver.bats` (append), `tools/factory/seat/README.md` (a "Routing" section)

**Interfaces:**
- `docs/ledger/routing.toml`, verbatim first contents:

```toml
# Model routing for the HEADLESS seat driver (tools/factory/seat). The
# interactive seat the operator opens on core is not governed by this file.
# Lookup: factory_route <role> <kind> <size>. The most specific matching row
# wins (fewest "any" fields); ties go to the first row; a row with all three
# "any" is the default and must exist. Explicit --model, OPENROUTER_MODEL and
# OPENROUTER_REASONING_EFFORT always override. Evidence for the rows:
# docs/reviews/2026-09-05-m2b-effort-measurement.md,
# docs/reviews/2026-09-05-model-comparison.md. Change rows here, nowhere else.

[[route]]
role = "implement"
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
role = "implement"
kind = "any"
size = "XS"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
role = "implement"
kind = "code"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
role = "review"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
```

- `factory_route ROLE KIND SIZE [FILE]` (FILE default `$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml`): prints one line `MODEL EFFORT` for the winning row; exit 3 with a message on stderr when the file is missing, malformed (a row lacking one of the five keys, a value not matching `[A-Za-z0-9._:/-]+`, an unknown role/kind/size word, an effort outside `off|low|medium|high|xhigh`), or has no default row. Specificity = number of fields not equal to `any` (0–3); highest wins; tie → earliest row.
- `factory_route_check [FILE]`: exit 0 when `factory_route any any any` succeeds and every row parses; otherwise exit 3 with the offending row number.
- `factory_task_kind_size PLAN KEY`: prints `KIND SIZE` parsed from the `### KEY (kind, size) — …` heading (via `factory_extract_task`'s first line); prints `any any` when the section is missing or untyped.
- `factory-task`: resolution order for the model: `--model` > `OPENROUTER_MODEL` > `factory_route implement KIND SIZE` > the existing built-in default (only if the table is unusable — log a warning). Effort: `OPENROUTER_REASONING_EFFORT` if set > the route's effort. The seat is launched with `OPENROUTER_REASONING_EFFORT=$effort` in its environment. The `.result` file gains two lines after `model:`: `effort: <effort>` and `route: <explicit|role/kind/size>` (`explicit` when a flag/env chose the model). `factory-review`: same with role `review` and `KIND SIZE` from the task heading.

- [ ] **Step 1: Failing tests** (append to `tests/unit/80-seat-driver.bats`; `SEAT` and `REAL_BASH` exist; write fixture TOML files into `$BATS_TEST_TMPDIR`):
  - specificity: rows `any/any/any → a`, `implement/any/any → b`, `implement/docs/any → c`, `implement/any/XS → d` (in that order): `factory_route implement docs XS` → `c` (tie at 2 fields, first wins); `implement code S` → `b`; `review code S` → `a`; `implement docs S` → `c`; and prints `MODEL EFFORT` exactly.
  - errors: no default row → exit 3; a row missing `effort` → exit 3 naming the row; `effort = "max"` → exit 3; missing file → exit 3.
  - `factory_route_check` on the REAL `$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml` → exit 0 (this pins the committed table's shape under the `unit` check).
  - `factory_task_kind_size` on a fixture plan with `### K1 (docs, XS) — t` → `docs XS`; on an untyped `### K2: thing` → `any any`; missing key → `any any`.
  - factory-task resolution: extend the existing dispatch test's pattern (tests/unit/80-seat-driver.bats, "factory-task dispatches to the seat directory it was run from") — a fake `dsh-openrouter` on PATH that records its `--model` argument and `$OPENROUTER_REASONING_EFFORT` to a file and prints a valid `FACTORY-RESULT status=done` block: with a plan heading `(docs, XS)` and no overrides → the fake sees `deepseek/deepseek-v4-flash` and `off`, and the `.result` has `route: implement/docs/XS`; with `OPENROUTER_MODEL=x/y` → `x/y`, `route: explicit`; with a `(code, M)` heading → Pro and `medium`.
- [ ] **Step 2: Red** — `nix develop -c bats tests/unit/80-seat-driver.bats` → the new tests fail (`factory_route: command not found`, and the dispatch test sees the built-in Pro default). Record the lines.
- [ ] **Step 3: Implement** the three functions in `factory-lib.sh` (pure bash line walk over `[[route]]` blocks; strip quotes; validate words), wire `factory-task` and `factory-review`, write the two `.result` lines, add the README section (what the table is, the precedence, how to add a row, that the interactive seat is untouched).
- [ ] **Step 4: Green** — shellcheck on the three scripts; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate. Do not launch a real seat.
- [ ] **Step 5: Commit.**

**touches:** docs/ledger/routing.toml, tools/factory/seat/factory-lib.sh, tools/factory/seat/factory-task, tools/factory/seat/factory-review, tests/unit/80-seat-driver.bats, tools/factory/seat/README.md
**acceptance:** unit, lint
**commit subject:** `seat: per-task model and effort from docs/ledger/routing.toml (role x kind x size, explicit overrides win, route recorded in the result) (test: unit, lint)`

## Correction (2026-09-05 ~15:30, operator): one factory, one table

"The entire thing is the dark factory." The seat driver, the Opus gates and the Workflow runs are one factory. RT1 (running) creates the table and wires the OpenRouter seat rows; RT2 extends the same table to every role on both routes so that model choice anywhere in the factory is one deterministic lookup the operator can tweak.

### RT2 (code, S) — the routing table covers both routes; the dark factory and the gates read it

**dependsOn:** RT1

**Files:**
- Modify: `docs/ledger/routing.toml` (a `route` key on every row, new rows), `tools/factory/seat/factory-lib.sh` (`factory_route` accepts and prints the route; rows without `route` default to `openrouter`), `tests/unit/80-seat-driver.bats` (append), `tools/factory/dark-factory.js` (the default `models` map is asserted equal to the table, not replaced — the Workflow harness cannot read files), `tests/factory/render.test.mjs` (or the existing factory test file the `factory-unit` check runs — read `flake.nix`'s `factory-unit` block to find it), `tools/factory/seat/README.md`
- Create: `tools/factory/route.py` (stdlib; the toolbox devShell has python3)

**Interfaces:**
- `routing.toml` row schema becomes `route, role, kind, size, model, effort`; `route ∈ {openrouter, claude}`; roles: `implement | review | verify | baseline | research | audit | orchestrate | any`; `factory_route ROLE KIND SIZE [FILE]` gains an optional leading `--route R` (default `openrouter`) and prints `MODEL EFFORT`. New rows, appended verbatim:

```toml
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
```

(Every existing RT1 row gains `route = "openrouter"`; the `any/any/any` default row is per route, so add `route = "claude"`'s default as the `implement` row above is not a default — add one: `route = "claude", role = "any", kind = "any", size = "any", model = "sonnet", effort = "medium"`.)
- `tools/factory/route.py [--file docs/ledger/routing.toml] models` prints the JSON object `{"baseline","impl","reviewCode","reviewDocs","verify","audit"}` derived from the claude rows (the exact shape `dark-factory.js` line ~92 defines); `route.py check` validates the schema (exit 1 with the row number); `route.py lookup ROUTE ROLE KIND SIZE` prints `MODEL EFFORT` with the same specificity rule as `factory_route` (the two implementations are cross-checked by a test that runs both on the same fixture).
- `dark-factory.js`: keeps its built-in default map (the harness cannot read files) but the `factory-unit` test asserts it equals `route.py models` output for the committed table, so the table is the single source and drift fails the check. The header comment names the table as the policy.
- Orchestrator rule (documented in README): every Agent-tool gate dispatched by Fable uses the `claude/review/<kind>` row's model; the `models` argument to the Workflow is `route.py models` output.

- [ ] **Step 1: Failing tests** — bats: `factory_route --route claude review code any` → `opus high`; a row without `route` still resolves under `openrouter`; `route = "other"` → exit 3. pytest-free python check via bats: `nix develop -c python3 tools/factory/route.py check` on the real table exits 0; `lookup claude review docs S` → `sonnet medium`; cross-check: for 6 fixed tuples, `factory_route` and `route.py lookup` print identical lines. factory-unit: assert `dark-factory.js`'s default `models` object equals `route.py models` (read the JS text with a regex or evaluate the object literal, as the existing render test loads the file).
- [ ] **Step 2: Red** — run the tests; record failures (`--route` unknown flag; `route.py` missing; factory-unit assertion missing).
- [ ] **Step 3: Implement**; keep RT1's tests green.
- [ ] **Step 4: Green** — shellcheck; `nix develop -c ruff format tools/factory/route.py && nix develop -c ruff check tools/factory/route.py`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix build .#checks.x86_64-linux.factory-unit -L --no-link`; lint gate.
- [ ] **Step 5: Commit.**

**touches:** docs/ledger/routing.toml, tools/factory/seat/factory-lib.sh, tests/unit/80-seat-driver.bats, tools/factory/dark-factory.js, tests/factory/render.test.mjs, tools/factory/route.py, tools/factory/seat/README.md
**acceptance:** unit, factory-unit, lint
**commit subject:** `factory: one routing table for both routes — claude rows for orchestrate/baseline/implement/review/verify/research/audit; route.py derives the dark factory's models map and the check refuses drift (test: unit, factory-unit, lint)`

### RT1b (code, S) — RT1 fix round: the override paths and factory-review pinned (test-only plus two one-line fixes)

**dependsOn:** none

Gate: `docs/reviews/2026-09-05-opus-review-rt1-RT1.md` — REJECTED on five surviving mutants; the implementation is correct. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/rt1/RT1 task/RT1 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with RT1's subject.

**Files:** `tests/unit/80-seat-driver.bats` (append), `docs/ledger/routing.toml` (trailing newline only), `tools/factory/seat/factory-lib.sh` (only: reject `model = ""`; drop the `2>/dev/null` on the `factory_route` call site in `factory-task`/`factory-review` so a bad row's message is seen), `tools/factory/seat/factory-task`, `tools/factory/seat/factory-review` (only that `2>/dev/null` removal)

- [ ] **Step 1: Tests, each red by the review's mutation then green** (use the existing fake-`dsh-openrouter` dispatch pattern from RT1's tests): (a) `factory-task … --model x/y` with a `(docs, XS)` heading → the fake sees `x/y`, `.result` says `route: explicit` (mutation: let the route clobber the flag → fails); (b) `OPENROUTER_REASONING_EFFORT=high` with a route effort `off` → the fake's env shows `high` (mutation: `effort=$route_effort` → fails) — set the variable to a NON-empty value, the review found the old tests set it empty; (c) `factory-review` dispatch: role `review` resolves the `review/any/any` row — make the fixture table give `review` a DIFFERENT model from `implement` so the mutant "role implement" fails; and the review seat is launched with the route's effort in its env (mutation: drop it → fails); (d) unknown `role = "builder"` in a row → exit 3 (mutation: drop word validation → fails); (e) `model = ""` → exit 3.
- [ ] **Step 2: Green** — shellcheck on the three scripts; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate. Note in FACTORY-NOTES that the committed-table pin still skips under `unit` (the sandbox copies no `docs/`) — RT2 moves that check into the flake.
- [ ] **Step 3** One commit, subject byte-identical to RT1's.

**touches:** tests/unit/80-seat-driver.bats, docs/ledger/routing.toml, tools/factory/seat/factory-lib.sh, tools/factory/seat/factory-task, tools/factory/seat/factory-review
**acceptance:** unit, lint
**commit subject:** `seat: per-task model and effort from docs/ledger/routing.toml (role x kind x size, explicit overrides win, route recorded in the result) (test: unit, lint)`

### RT2b (code, S) — RT2 fix round: the tie fixture, the validator tests, the sandbox carries the table, an honest commit body

**dependsOn:** none (RT1b is on main)

Gate: `docs/reviews/2026-09-05-opus-review-rt2c-RT2.md` — REJECTED on three blockers plus an orchestrator decision, taken: **`flake.nix` is in scope for this round** (the freeze that bound RT1/RT2 is lifted; no other running task touches it). Fresh workspace from `main`; `git fetch -q /home/dalhaka/factory/ws/rt2c/RT2 task/RT2 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with RT2's subject, and a commit BODY that states exactly which check refuses which drift (see Step 4).

**Files:** RT2's seven plus `flake.nix`.

- [ ] **Step 1: Tie fixture** (blocker 1) — a fixture table with two rows of equal specificity and DIFFERENT models (e.g. `implement/docs/any → m/first` then `implement/any/XS → m/second`): both `factory_route implement docs XS` and `route.py lookup openrouter implement docs XS` must print `m/first …` (earliest row wins). Red: flip `route.py`'s tie-break to `>=` → the cross-check test fails; revert.
- [ ] **Step 2: Validator tests** (blocker 2) — `route.py check` on fixtures missing each of the six keys (`route`, `role`, `kind`, `size`, `model`, `effort`) → exit 1 naming the row; `route = "other"` → exit 1; an effort outside the five words → exit 1. Red: replace the key check with `setdefault`s → tests fail; revert.
- [ ] **Step 3: The sandbox carries the table** — in `flake.nix`: the `unit` runCommand copies `docs/ledger/routing.toml` and `tools/factory/route.py` into its tree (so the two `# skip` tests at `ok 125`/`ok 130` run for real — confirm in the build log that they no longer skip); the `factory-unit` runCommand copies `docs/ledger/routing.toml` and `tools/factory/route.py` and its drift test compares `dark-factory.js`'s default map against `route.py models` run on the copied table (so a table-only edit fails `factory-unit`, not just the hook). Red: in the clone edit the claude `review/code` row `opus → sonnet` with the scripts untouched → `nix build .#checks.x86_64-linux.factory-unit -L --no-link` fails; revert. Add `tools/factory/route.py` to the `ruff check` list in both `githooks/pre-commit` and the `lint` runCommand.
- [ ] **Step 4: Honest body.** The commit message body names: `githooks/pre-commit` refuses a table that fails `route.py check`; `checks.factory-unit` refuses drift between the table and `dark-factory.js`'s map; `checks.unit` pins the bash lookup and the committed table's shape. Nothing the checks do not do.
- [ ] **Step 5: Minors** — remove the duplicate `// Scenario 26` label; fix `factory_route_check`'s comment to describe what it does (the two routes it knows).
- [ ] **Step 6: Green** — shellcheck; ruff; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix build .#checks.x86_64-linux.factory-unit -L --no-link`; `nix build .#checks.x86_64-linux.lint -L --no-link`; lint gate. RT1's and RT1b's tests unchanged and green.

**touches:** docs/ledger/routing.toml, tools/factory/seat/factory-lib.sh, tests/unit/80-seat-driver.bats, tools/factory/dark-factory.js, tests/factory/render.test.mjs, tools/factory/route.py, tools/factory/seat/README.md, flake.nix, githooks/pre-commit
**acceptance:** unit, factory-unit, lint
**commit subject:** `factory: one routing table for both routes — claude rows for orchestrate/baseline/implement/review/verify/research/audit; route.py derives the dark factory's models map and the check refuses drift (test: unit, factory-unit, lint)`

## RT3 (decision, then a task) — the harness's role map and this table

Fact found 2026-09-05 evening: `~/flakes/dsh-harness` routes its internal sub-agents by its own role→model map (`deepseekPro`, `deepseekFlash`, `kimi`, `glm`, `glmFlash`; README "roles"); the 2026-09-04 runs spent $28 on GLM and $1.7 on Kimi through it. `routing.toml` today governs only the seat driver's launch model/effort per task (RT1) and the Claude-side roles (RT2). Operator decision needed: (a) the harness reads `routing.toml` (cross-repo dependency; the harness repo gains a reader and the rows move here), or (b) `routing.toml` mirrors the harness's rows read-only for visibility and the harness map stays the source in its repo, or (c) leave as two documented sources. Until decided, no task is dispatched; the decision file records the two sources.

**RT3 closed (2026-09-05 evening, operator):** parked, not unified — `docs/decisions/2026-09-05-dsh-harness-factory-parked.md`. The dispatcher is `factory-dispatch` (plan `2026-09-05-factory-dispatch.md`).

### RT4 (code, XS) — `FACTORY_ROUTING_TABLE` names the table for every caller

**dependsOn:** none

Origin: the H2 gate (`docs/reviews/2026-09-05-opus-review-hr1-H2.md`) — the harness prose promises `FACTORY_ROUTING_TABLE` overrides the table path, but `factory_route` only takes an optional FILE argument and otherwise uses `$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml`. Make the promise true in both implementations.

**Files:** `tools/factory/seat/factory-lib.sh` (`factory_route`, `factory_route_check` default FILE), `tools/factory/route.py` (`--file` default), `tests/unit/80-seat-driver.bats` (append), `tools/factory/seat/README.md` (one sentence)

**Interfaces:** default table = `${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml}` in bash; `--file` default `os.environ.get("FACTORY_ROUTING_TABLE", "docs/ledger/routing.toml")` in python; an explicit FILE/`--file` still wins over the env var.

- [ ] **Step 1: Failing tests** — bats: with `FACTORY_ROUTING_TABLE` pointing at a fixture whose default row names `x/env-model`, `factory_route implement code S` (no FILE) prints `x/env-model …`; with both env and an explicit FILE, FILE wins. Same two for `route.py lookup` via `nix develop -c python3`. Red: today the env var is ignored (production answer).
- [ ] **Step 2: Implement**; shellcheck; ruff; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate. **Step 3: Commit.**

**touches:** tools/factory/seat/factory-lib.sh, tools/factory/route.py, tests/unit/80-seat-driver.bats, tools/factory/seat/README.md
**acceptance:** unit, lint
**commit subject:** `factory: FACTORY_ROUTING_TABLE names the routing table for the bash and python lookups; an explicit file still wins (test: unit, lint)`

### RT5 (code, S) — the seat's hook enforces the routing table for sub-agent models

**dependsOn:** RT4 (the `FACTORY_ROUTING_TABLE` default the hook shares)

Operator, 2026-09-05 evening: "enforce the router at the hook." The deny-only guard `pkgs/dsh-openrouter/hook-guard.py` gains a rule: a sub-agent launch whose `model` is not a row of the routing table's OpenRouter route is refused, so the table is applied by the OS, not followed by prose.

**Files:** `pkgs/dsh-openrouter/hook-guard.py`, `pkgs/dsh-openrouter/dsh-openrouter.sh` (the generated `hooks.json` gains a matcher for the sub-agent tools and passes the table path), the existing hook-guard tests (find them: `grep -ln hook-guard tests/unit/*.bats tests/*/*.py`), `docs/runbooks/lanes.md` (the guard's rule list)

**Interfaces:**
- New matcher in the wrapper's `hooks.json`: `subagent|subagent_fork|workflow` → the same `hook-guard` command with `--routing-table <path>` where `<path>` = `${FACTORY_ROUTING_TABLE:-$HOME/nixos-agent-env/docs/ledger/routing.toml}` resolved at seat launch (the wrapper also passes it to the existing bash/edit matchers so one guard sees one table).
- Rule (deny-only): if `tool_input.model` (or `tool_input.provider`+`model`) is present and is NOT the `model` of any row with `route = "openrouter"` (rows without `route` count as openrouter) → deny with `sub-agent model <id> is not a row of <table> (route openrouter); pick a role and let the table choose`. No `model` in the input → allow (the seat default applies). Table missing or unparsable → DENY any explicit model with `routing table unreadable at <path>` (fail closed for explicit choices; the default path stays allowed). `route = "claude"` rows never allow (they are unreachable from this seat).
- Same rule for shell commands: a bash command containing `--model <id>` or `OPENROUTER_MODEL=<id>` where `<id>` is not an openrouter row → deny (this is how a nested `dsh-openrouter` launch would bypass the sub-agent tools).
- Every denial is audited like the existing rules (`dsh-openrouter --denials` shows it).

- [ ] **Step 1: Failing tests** — in the existing hook-guard test file: a `subagent` PreToolUse payload with `model = "z-ai/glm-5.3"` against the real committed table → deny with the rule's message; `model = "deepseek/deepseek-v4-flash"` → allow; no `model` → allow; `model = "opus"` (a claude row) → deny; table path pointing at a missing file + explicit model → deny "unreadable"; bash `dsh-openrouter --model moonshotai/kimi-k3 --headless x` → deny; `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 …` → allow. Wrapper: `--dump-config` shows the new matcher and the `--routing-table` argument (extend the existing dump-config test).
- [ ] **Step 2: Red** — the payloads are allowed today (no rule). **Step 3: Implement** (stdlib `tomllib`; the guard already parses JSON on stdin — keep it deny-only; never raise: any exception → allow for non-model rules exactly as today, but the model rule fails closed as specified). **Step 4: Green** — ruff; shellcheck; `nix develop -c bats tests/unit/70-dsh-openrouter.bats` (or the file found); `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix build .#checks.x86_64-linux.host-core -L --no-link`; lint gate. Note in FACTORY-NOTES: this reaches the seat at the next switch (host package). **Step 5: Commit.**

**touches:** pkgs/dsh-openrouter/hook-guard.py, pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats, docs/runbooks/lanes.md
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: the hook guard refuses a sub-agent or nested-seat model that is not an OpenRouter row of the routing table; fails closed when the table is unreadable (test: unit, host-core, lint)`

### OG1 (code, S) — the orchestrator's own guard: typed plan headings are append-only; host mutations refused

**dependsOn:** none (G8c must be on main before dispatch: `.claude/settings.json` is shared with G6's hook, not with G8c, but `tasks.py` is — OG1 does NOT touch tasks.py)

Operator, 2026-09-05 evening: "Can you ban your ability to do that?" Yes: the same PreToolUse mechanism, for the Claude Code session in this checkout.

**Files:** `tools/orchestrator-guard.py` (new; stdlib), `.claude/settings.json` (a `PreToolUse` entry: matcher `Edit|Write|MultiEdit` and matcher `Bash`, command `python3 "$CLAUDE_PROJECT_DIR/tools/orchestrator-guard.py"` — NOTE: the bare host has no python3; the command must be `nix develop "$CLAUDE_PROJECT_DIR" -c python3 …` or a bash implementation; choose bash if the devShell startup (~2 s) is too slow for a per-edit hook — measure and state which), `tests/unit/91-orchestrator-guard.bats`, `docs/runbooks/session.md` (a "Guard" section)

**Interfaces (deny-only, Claude Code hook protocol: JSON on stdin with `tool_name`, `tool_input`; deny by printing `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}` — read the superpowers plugin's hook for the exact shape this version accepts):**
- Edit/Write/MultiEdit on `docs/superpowers/plans/*.md`: compute the set of typed headings (`^### KEY (kind, size) — title$` lines) before and after; if any existing typed heading is removed or altered → deny: `typed task headings are append-only — withdraw a task with a status row in docs/ledger/task-status.toml, not by editing docs/superpowers/plans/…`. Adding sections is allowed. (For `Edit`, apply `old_string`→`new_string` to the file's current text to compute "after"; for `Write`, the new content is "after".)
- Bash: the dsh guard's host rules for me too — `sudo`, `nixos-rebuild`, mutating `systemctl` verbs, writes under `/run/baskets`, `/var/lib/{baskets,helm,egress-broker,lanes,secrets}` → deny with the same wording as `hook-guard.py`. Also `git commit --amend`, `git push`, `git rebase`, `git reset --hard` on this checkout → deny (history rules of the house).
- Never raise; any internal error → allow (a broken guard must not lock the session) except that it prints a one-line warning to stderr.
- `docs/ledger/task-status.toml` is CREATED by this task as an empty, documented file (`# [[task]] repo, plan, key, status = withdrawn | parked, note, decided`), and the graph learns to read it in a follow-up task (OG2, after G8c: `tasks.py` marks such keys `withdrawn`, never schedules them, shows them in the brief once). Until OG2 lands the file is documentation of intent.

- [ ] **Step 1: Failing tests** (bats, feeding JSON payloads to the guard): removing a typed heading → deny; rewriting one → deny; appending a new section → allow; editing body text under a heading → allow; a Bash `sudo nixos-rebuild switch` → deny; `git commit --amend` → deny; `git status` → allow; malformed JSON → allow with a stderr warning. Wall time per call < 300 ms (measure; state the interpreter chosen).
- [ ] **Step 2: Red** — no guard: everything allowed. **Step 3: Implement**; register in `.claude/settings.json` (keep G6's SessionStart entry intact). **Step 4: Green** — shellcheck/ruff; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link` (confirm the sandbox copies the guard: G6 added a copy line for `tools/session-start.sh` — the plan allows a flake.nix touch ONLY for that one copy line, mirrored on G6's); lint gate. **Step 5: Commit.**

**touches:** tools/orchestrator-guard.py, .claude/settings.json, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md, docs/ledger/task-status.toml, flake.nix
**acceptance:** unit, lint
**commit subject:** `session: a deny-only PreToolUse guard for the orchestrator — typed plan headings are append-only, host mutations and history rewrites refused; task-status.toml is the way to withdraw a task (test: unit, lint)`

### OG1b (code, S) — OG1 fix round: paths normalised, git flags tolerated, sudo matched in command position, the rest of the minors

**dependsOn:** none

Gate: `docs/reviews/2026-09-05-opus-review-og1-OG1.md` — REJECTED on three bypasses (all named in the gate brief), guard otherwise sound. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/og1/OG1 task/OG1 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with OG1's subject. Disclose the regenerated `docs/MAP.md` in FACTORY-NOTES this time.

**Files:** `tools/orchestrator-guard.sh`, `tests/unit/91-orchestrator-guard.bats` (+ the carried OG1 files unchanged: `.claude/settings.json`, `docs/runbooks/session.md`, `docs/ledger/task-status.toml`, `flake.nix` copy line, `docs/MAP.md`)

- [ ] **Step 1: Tests first, each red on OG1's guard** — (a) MAJOR 1: heading deleted via `docs/superpowers/plans/../plans/x.md`, via `docs/superpowers/./plans/x.md`, and via a symlink `tests-tmp/link.md → docs/superpowers/plans/x.md` (create it in the test tmp repo) → all three DENIED; a path outside the plans dir that merely contains the string `plans/` (`docs/notes/plans/x.md`) → allowed. Implement by resolving `file_path` with `realpath -m` (coreutils; present on the host and in the sandbox) relative to `$CLAUDE_PROJECT_DIR`/cwd and comparing the resolved prefix — the same shape as `hook-guard.py`'s `_resolve`/`_is_within`. (b) MAJOR 2: `git -c core.editor=true commit --amend`, `git -C /home/x push`, `git --no-pager rebase -i`, `git -c a=b -C . reset --hard` → DENIED; `git -c a=b status`, `git -C . log` → allowed. Pattern: `git` followed by any number of `-c k=v`, `-C path`, `--no-pager`, `--git-dir=…`, `--work-tree=…` tokens, then the subcommand. (c) MINOR 3: `grep -rn sudo docs/brief.md`, `echo 'never sudo here'` → ALLOWED; `sudo x`, `x; sudo y`, `x && sudo y`, `(sudo y)` → denied — port `hook-guard.py`'s `_SUDO`/`_NIXOS_REBUILD` anchors exactly (`(?:^|[;&|\n()])\s*sudo(?=\s|$)`), no `[[:space:]]` in the leading class. (d) MINOR 4: `tee -a /var/lib/secrets/x`, `cp k /run/baskets/x`, `mv k /var/lib/lanes/x`, `install -m600 k /var/lib/secrets/x`, `>  /var/lib/helm/x` (two spaces) → denied. (e) MINOR 5: malformed JSON starting with `{` → allowed WITH a one-line stderr warning (assert stderr non-empty). (f) MINOR 6: a MultiEdit whose `old_string` contains an escaped quote and removes a heading → denied (parse JSON with a real parser: `jq` is not on the bare host — the guard runs in the Claude Code session where the devShell is NOT active; keep pure bash but parse `edits[]` robustly: extract each `old_string`/`new_string` with a small state machine over the JSON string escapes, or fall back to DENY-on-unparsable for MultiEdit only (fail closed for the one tool whose payload the guard cannot read — state which in the header)).
- [ ] **Step 2: Red** — run the bats file against the cherry-picked guard: the new tests fail. **Step 3: Implement.** **Step 4: Green** — shellcheck; bats; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate; wall time still < 300 ms/call (measure). Re-run OG1's 19 tests and the gate's six mutations — all still hold. **Step 5: One commit**, OG1's subject.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, .claude/settings.json, docs/runbooks/session.md, docs/ledger/task-status.toml, flake.nix, docs/MAP.md
**acceptance:** unit, lint
**commit subject:** `session: a deny-only PreToolUse guard for the orchestrator — typed plan headings are append-only, host mutations and history rewrites refused; task-status.toml is the way to withdraw a task (test: unit, lint)`

### RT5b (code, S) — RT5 fix round: the shell half of the rule catches every ordinary spelling, and its tests can fail

**dependsOn:** none

Gate: `docs/reviews/2026-09-05-opus-review-rt5-RT5.md` — REJECTED on two MAJORs in the bash-command half; the structured (`subagent`/`subagent_fork`/`workflow`) half and the wrapper wiring were approved. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/rt5/RT5 task/RT5 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with RT5's subject.

**Files:** `pkgs/dsh-openrouter/hook-guard.py`, `tests/unit/70-dsh-openrouter.bats` (+ carried: `pkgs/dsh-openrouter/dsh-openrouter.sh`, `docs/runbooks/lanes.md`, `pkgs/dsh-openrouter/default.nix` (the stdlib-imports comment gains `tomllib`))

- [ ] **Step 1: Tests first, each red on RT5's guard** — bash payloads that must DENY: `dsh-openrouter --model "z-ai/glm-5.3" …`, `--model 'z-ai/glm-5.3'`, `--model=z-ai/glm-5.3`, `--model="z-ai/glm-5.3"`, `OPENROUTER_MODEL="z-ai/glm-5.3" dsh-openrouter …`, `OPENROUTER_MODEL='z-ai/glm-5.3' …`, `env OPENROUTER_MODEL=z-ai/glm-5.3 dsh-openrouter …`, `--model \` + newline + `z-ai/glm-5.3` (strip backslash-newline before scanning), tab-separated `--model\tz-ai/glm-5.3`; must ALLOW: `--model deepseek/deepseek-v4-flash`, `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 …`, a command with no model at all. Structured: `tool_input.provider` present with a claude-row `model` → deny; a `workflow` payload whose `steps[*].model` names a non-row → deny (scan nested `model` keys anywhere in `tool_input`, not just the top level). Malformed table + explicit model → deny (this test exists; keep). Table path `""` (empty `FACTORY_ROUTING_TABLE` reaching the guard) → treat as the default path, not `""` — test it.
- [ ] **Step 2: Red** — the deny payloads above are ALLOWED by the cherry-picked guard (record which). **Step 3: Implement**: one normalisation pass (`\\\n` → ``, tabs → spaces), one regex for `--model(=|\s+)(['"]?)([A-Za-z0-9._:/-]+)\2`, one for `OPENROUTER_MODEL=(['"]?)([A-Za-z0-9._:/-]+)\1` with an optional leading `env `, a recursive walk for `model` keys in `tool_input`. **Step 4: Green** — ruff; `nix develop -c bats tests/unit/70-dsh-openrouter.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `host-core`; lint gate; re-run RT5's killed mutants + the two survivors (M5 `--model=` unmatched, M10 `OPENROUTER_MODEL=` dead) — all must now die. **Step 5: One commit**, RT5's subject.

**touches:** pkgs/dsh-openrouter/hook-guard.py, pkgs/dsh-openrouter/dsh-openrouter.sh, pkgs/dsh-openrouter/default.nix, tests/unit/70-dsh-openrouter.bats, docs/runbooks/lanes.md
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: the hook guard refuses a sub-agent or nested-seat model that is not an OpenRouter row of the routing table; fails closed when the table is unreadable (test: unit, host-core, lint)`

### OG1r (code, S) — re-plan of OG1 (rule A1): the git rule is a tokeniser; plan files are edited only through inspectable tools

**dependsOn:** none

OG1 and OG1b were rejected (`docs/reviews/2026-09-05-opus-review-og1-OG1.md`, `…-OG1b.md`); OG1b's other fixes (realpath normalisation, sudo anchors, protected prefixes, malformed-JSON warning, escape-aware MultiEdit) are correct and kept verbatim. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/og1/OG1b task/OG1b && git cherry-pick -n FETCH_HEAD`; ONE commit with OG1's subject. Disclose `docs/MAP.md` if regenerated.

**Files:** `tools/orchestrator-guard.sh`, `tests/unit/91-orchestrator-guard.bats`, `docs/runbooks/session.md` (+ carried OG1b files)

**Design change 1 — the git rule is a tokeniser, not a flag list.** Normalise the command (`\`+newline → space, tabs → spaces). Find every `git` WORD: at a command boundary (start, `;`, `&&`, `||`, `|`, `(`, newline), after `env`, `command`, `\`, or `VAR=value` prefixes, or as the basename of a path token ending in `/git`. From that word walk forward: skip every token beginning with `-`; when the token is one of `-c`, `-C`, `--git-dir`, `--work-tree`, `--exec-path`, `--namespace`, `--config-env`, `--super-prefix` WITHOUT `=`, also skip the next token (its value). The first remaining token is the subcommand. Deny when: subcommand `commit` and any later token is `--amend`; `push`; `rebase`; `reset` with `--hard`; `checkout`/`restore` with a path under `docs/superpowers/plans/` (see change 2). Positive controls that must stay allowed: `git --work-tree=. status`, `git -c a=b log -1`, `git -P diff`, `git --no-pager show`, `git commit -F msg` (no amend), `git push --dry-run`? (deny — `push` is denied outright; state it).
**Design change 2 — plan files change only through Edit/Write/MultiEdit.** Any Bash command whose normalised text contains a path under `docs/superpowers/plans/` (realpath-normalised: `..`, `./`, `//`, absolute) together with a write-capable verb — `sed -i`, `rm`, `mv`, `cp` (as destination), `tee`, `>`/`>>` redirect, `truncate`, `python3 -`/`python3 -c` with `write_text`/`open(…,"w")` on a plan path, `perl -i`, `git checkout --`/`git restore` — is DENIED with `plan files change only through the Edit and Write tools (append-only headings) — see docs/runbooks/session.md`. Read-only verbs (`cat`, `grep`, `sed -n`, `head`, `tail`, `diff`, `wc`, `git diff`, `git show`, `git log`) stay allowed. This binds the orchestrator's own habit of appending sections via python heredocs; the runbook says so and shows the Edit/Write way.
**Kept from OG1b:** everything else; MINOR 7 (absolute-path `git` is now covered by the tokeniser's basename rule); MINOR 9 (`cp /var/lib/secrets/x /tmp/y` must be ALLOWED — the protected-prefix rule applies to destinations/redirect targets, not the first path token: fix and test); MINOR 10 (symlinked `CLAUDE_PROJECT_DIR` test).

- [ ] **Step 1: Table-driven bats**, red on OG1b: DENY — `git --work-tree=. commit --amend`, `git -P commit --amend`, `git --literal-pathspecs commit --amend`, `git --exec-path=/x commit --amend`, `git --no-replace-objects push`, `git --namespace=n push`, `git --icase-pathspecs rebase -i`, `git -c a=b -C . reset --hard`, `/run/current-system/sw/bin/git commit --amend`, `command git commit --amend`, `\git commit --amend`, `GIT_EDITOR=true git commit --amend`, `git   commit   --amend`, `git commit \`+newline+`--amend`; `sed -i 's/x/y/' docs/superpowers/plans/x.md`, `rm docs/superpowers/plans/x.md`, `mv a docs/superpowers/plans/x.md`, `cat > docs/superpowers/plans/../plans/x.md`, `nix develop -c python3 - <<'PY' … open("docs/superpowers/plans/x.md","w")`, `git checkout -- docs/superpowers/plans/x.md`, `git restore docs/superpowers/plans/x.md`. ALLOW — the positive controls above, `cat docs/superpowers/plans/x.md`, `grep -n '^### ' docs/superpowers/plans/x.md`, `sed -n 1,5p docs/superpowers/plans/x.md`, `git diff -- docs/superpowers/plans/x.md`, `cp /var/lib/secrets/x /tmp/y`.
- [ ] **Step 2: Red** (record which deny cases pass through OG1b's guard). **Step 3: Implement.** **Step 4: Green** — shellcheck; bats; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate; wall time < 300 ms/call; OG1b's 30 tests and its 15 killed mutants still hold; mutations: tokeniser skips no values (`-c a=b commit` misread → must fail a test); path rule removed → fails. **Step 5: One commit**, OG1's subject. Runbook: the two rules in plain words and the Edit/Write way to append a section.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md, .claude/settings.json, docs/ledger/task-status.toml, flake.nix, docs/MAP.md
**acceptance:** unit, lint
**commit subject:** `session: a deny-only PreToolUse guard for the orchestrator — typed plan headings are append-only, host mutations and history rewrites refused; task-status.toml is the way to withdraw a task (test: unit, lint)`

### RT5r (code, S) — re-plan of RT5 (rule A1): the guard gets an error contract — the model rule fails closed and the process never exits non-zero

**dependsOn:** none

RT5 and RT5b were rejected (`docs/reviews/2026-09-05-opus-review-rt5-RT5.md`, `…-RT5b.md`); RT5b's spellings, nested walk and tests are correct and kept. The missing design: the dsh hook protocol treats a hook that exits non-zero with empty stdout as a NON-blocking error, so any exception inside the guard is an "allow". Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/rt5/RT5b task/RT5b && git cherry-pick -n FETCH_HEAD`; ONE commit with RT5's subject.

**Files:** `pkgs/dsh-openrouter/hook-guard.py`, `tests/unit/70-dsh-openrouter.bats`, `docs/runbooks/lanes.md` (+ carried RT5b files)

**Contract:**
1. `main()` returns 0 on EVERY path (deny is expressed only through the JSON on stdout; the exit code is never the signal). A top-level `try/except BaseException` around the rule evaluation guarantees it.
2. The model rule is fail-closed: any unexpected exception while evaluating it (walking `tool_input`, reading or parsing the table — including `UnicodeDecodeError`, `RecursionError`, `MemoryError`) resolves to DENY with reason `model rule could not be evaluated: <ExceptionName>`. The bash/edit rules keep today's allow-on-error (the deny-only heuristic) — the asymmetry is documented in the file header.
3. `_walk_model_ids` is iterative (an explicit stack), bounded by a node budget (10,000) and a depth budget (64); exceeding either → the rule DENIES with reason `tool_input too deep/large to inspect`.
4. The audit `subject` names the OFFENDING model id (the one not in the table), not the first found.
5. `docs/runbooks/lanes.md` states the known limits (shell substitution `$(…)`, `$X`, `$'…'`, `--mod''el`) and that the guard is a heuristic plus an audit trail, the netns being the wall.

- [ ] **Step 1: Tests, red on RT5b** — depth-2000 `subagent` payload with a top-level non-row `model` → deny AND exit 0 (today: exit 1, empty stdout); a non-UTF-8 routing table + explicit model → deny "could not be evaluated" AND exit 0; depth-70 payload with a non-row model at depth 69 → deny (budget) AND exit 0; 20,000-key payload → deny AND exit 0; every existing deny/allow test now ALSO asserts `[ "$status" -eq 0 ]`. Audit subject names the offending id (mutation: first id → fails).
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — ruff; `nix develop -c bats tests/unit/70-dsh-openrouter.bats`; `unit`; `host-core`; lint gate; RT5b's 13 killed mutants + the two equivalent ones removed as dead code (state it); new mutations: iterative walk made recursive → depth-2000 test fails; the BaseException guard removed → the non-UTF-8 test fails on status. **Step 5: One commit**, RT5's subject.

**touches:** pkgs/dsh-openrouter/hook-guard.py, pkgs/dsh-openrouter/dsh-openrouter.sh, pkgs/dsh-openrouter/default.nix, tests/unit/70-dsh-openrouter.bats, docs/runbooks/lanes.md
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: the hook guard refuses a sub-agent or nested-seat model that is not an OpenRouter row of the routing table; fails closed when the table is unreadable (test: unit, host-core, lint)`

### OG1r2 (code, S) — re-plan of OG1 (third): no command position — scan every token

**dependsOn:** none

Three rejections (`docs/reviews/2026-09-05-opus-review-og1-OG1.md`, `…-OG1b.md`, `…-og3-OG1r.md`) share one root: every notion of "command position" (flag lists, boundary characters, launcher prefixes) was short. Rule now: **there is no command position.** Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/og3/OG1r task/OG1r && git cherry-pick -n FETCH_HEAD`; keep everything except the two walkers; ONE commit with OG1's subject.

**Contract:** normalise (`\`+newline → space; tabs, `;`, `&&`, `||`, `|`, `(`, `)`, `{`, `}`, `&`, newlines → spaces; strip matching quotes around tokens), then over ALL tokens: (a) any token whose basename is `git` (or `git` itself) marks a git invocation; the subcommand = the first later token not starting with `-` and not the value of `-c/-C/--git-dir/--work-tree/--exec-path/--namespace/--config-env/--super-prefix` (space form); deny on `commit`+`--amend` anywhere after, `push`, `rebase`, `reset`+`--hard`, `checkout`/`restore` with a plan path; (b) any WRITE VERB token anywhere (`sed` with `-i*`, `rm`, `mv`, `cp`, `tee`, `truncate`, `install`, `dd`, `ed`, `ln`, `perl`/`python*`/`python3 -`/`nix develop … -c python3` with `write_text|open\(.*["']w|>` , `>`/`>>` redirects, `git checkout --`, `git restore`) in a command that ALSO names a realpath-normalised plan path → deny; read verbs never deny. Launchers (`nix develop -c`, `timeout`, `nohup`, `time`, `!`, `xargs`, `bash -c "…"`, backticks) are irrelevant because tokens are scanned regardless of position; quoted strings inside `bash -c` are scanned as tokens too. Accepted over-denial: `echo "git commit --amend"` and `rm /tmp/x && cat <plan>` deny (deny-only guard; the runbook says so plainly and stops over-promising).

- [ ] **Step 1: Table-driven bats, red on OG1r** — all OG1r deny/allow cases plus: `cd /x`⏎`git commit --amend`, `set -e`⏎`git push origin main`, `echo a`⏎`rm <plan>`, `nix develop -c git commit --amend`, `nix develop -c rm <plan>`, `timeout 5 git push`, `nohup git push`, `xargs rm <plan>`, `bash -c "git push"`, `` `git push` ``, `cp k <plan> && echo done`, `install -m644 k <plan>`, `dd of=<plan>`, `ln -sf k <plan>`, `git status; git push` → all DENIED; allows: `git status; git log`, `nix develop -c pytest tests/evidence -q`, `nix develop -c python3 pkgs/evidence/tasks.py --root . check`, `grep -rn amend docs/reviews`, `cat <plan> | wc -l`. **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; bats; `unit`; lint gate; < 300 ms/call on a 200-token command; mutations: drop `\n` from the separator set → fails; skip tokens after a launcher → fails; basename rule off → fails; plan-path write rule off → fails. **Step 5: One commit**, OG1's subject; runbook rewritten to the two sentences above.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md, .claude/settings.json, docs/ledger/task-status.toml, flake.nix, docs/MAP.md
**acceptance:** unit, lint
**commit subject:** `session: a deny-only PreToolUse guard for the orchestrator — typed plan headings are append-only, host mutations and history rewrites refused; task-status.toml is the way to withdraw a task (test: unit, lint)`

### OG1r2b (code, S) — OG1r2 fix round: `mv` writes, the plans directory names every plan, `cd` and the payload's cwd rebase relative paths, `-i` anywhere in a sed/perl invocation, no subprocess per token

**dependsOn:** none

Gate `docs/reviews/2026-09-05-opus-review-og4-OG1r2.md` — REJECTED (MAJORs 14–18); the token scan itself is judged complete and every og3 case passes — keep it untouched. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/og4/OG1r2 task/OG1r2 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with OG1's subject.

**Contract additions** (rules on top of OG1r2's token scan; deny-only, so an over-denial is accepted and an under-denial is a MAJOR):
1. `mv` joins the operand-writers (`rm`, `tee`, `truncate`, `ed`, `sed -i`, `perl -i`): a plan path in ANY operand position denies. `git mv`, `git rm`, `rsync`, `shred`, `unlink`, `rmdir`, `find … -delete`/`-exec`, `git clean` join the same list.
2. A token that normalises to the plans directory itself (with or without a trailing slash) or to ANY ancestor of it (`docs/superpowers`, `docs`, `.`, the project dir, `/`) counts as naming every plan for the delete family (`rm`, `mv`, `rsync`, `shred`, `rmdir`, `find`, `git clean`); read verbs never deny (`ls docs/superpowers/plans` and `find docs/superpowers/plans -name '*.md'` without `-delete`/`-exec` allow).
3. Relative paths rebase: the payload's `cwd` (Claude Code sends it) is the initial base instead of `CLAUDE_PROJECT_DIR` when present; every `cd <arg>` (and `pushd <arg>`) token pair adds a base (`~`, absolute and relative forms joined lexically onto the current base). A relative token is judged against the initial base AND every added base — deny if any resolution lands in the plans dir or on an ancestor per rule 2 (`cd docs/superpowers/plans && rm x.md`, `cd docs/superpowers/plans; rm x.md`, `cd docs/superpowers && rm plans/x.md` deny; `cd /tmp && rm x.md` allows).
4. `sed`/`perl` in place: a `-i*` or `--in-place*` token ANYWHERE in the command together with a `sed`/`perl` token and a plan path denies (`sed -e s/a/b/ -i <plan>`, `sed s/a/b/ -i <plan>`, `perl -pe s/a/b/ -i <plan>`).
5. No subprocess per token: path normalisation is lexical in bash (`~` expansion, join onto the base, collapse `.` and `..`); `realpath` runs once per command for the project and plans dirs, and once more only for a token whose lexical form is a symlink (`[ -L ]` is a syscall, not a fork) — the symlink-into-plans test keeps passing. Acceptance: a 200-path-token command (`ls <200 × docs/aN/bN.md>`) takes < 300 ms/call, measured in bats with `$EPOCHREALTIME` (three calls, the median).
6. Minors folded: quotes strip to nothing, not to a space (MINOR 17: `echo "a'b"` stays one word); `>|` is a redirect token (MINOR 19); the runbook's two sentences match the rules exactly — say what denies, name the accepted over-denials, drop "far over" (MINOR 20).

- [ ] **Step 1: Tests, red on OG1r2** — every row of the review's plan-write table as a DENY case: `mv <plan> /tmp/x`, `mv <plan> ./y`, `mv -f <plan> ../x.md`, `mv <plan> <plan>.bak`, `rm -r docs/superpowers/plans`, `rm -rf docs/superpowers`, `rm -rf docs`, `mv docs/superpowers/plans /tmp/`, `find docs/superpowers/plans -name "*.md" -delete`, `git clean -fdx docs/superpowers/plans`, `cd docs/superpowers/plans && rm x.md`, `cd docs/superpowers/plans; rm x.md`, `cd docs/superpowers && rm plans/x.md`, a payload whose `cwd` is the plans dir with command `rm x.md`, `sed -e s/a/b/ -i <plan>`, `sed s/a/b/ -i <plan>`, `perl -pe s/a/b/ -i <plan>`, `cat k >| <plan>`; ALLOW cases: `ls docs/superpowers/plans`, `find docs/superpowers/plans -name '*.md'`, `cd /tmp && rm x.md`, `cd docs/superpowers/plans && cat x.md`, `git diff -- docs/superpowers/plans/x.md`, `rm /tmp/plans-not-ours/x.md` (a directory merely named plans outside the project), and `echo "a'b"` pinned as ONE token (assert on the tokeniser's output through a test hook or on a deny reason that quotes the token). The timing test of rule 5. Every OG1r2 case stays exactly as it is.
- [ ] **Step 2: Red** (paste the failing test numbers into the log). **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `unit`; lint gate; mutations, each must fail at least one test: `mv` removed from the operand-writers; the directory/ancestor rule off; the `cd`/`cwd` rebase off; the `-i` search limited to the token right after `sed`; the lexical normaliser replaced by `realpath -m` per token (the timing test fails — report the measured ms); quote stripping back to a space. OG1r2's four mutations (M1–M4) still die. **Step 5: One commit**, OG1's subject.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md, .claude/settings.json, docs/ledger/task-status.toml, flake.nix, docs/MAP.md
**acceptance:** unit, lint
**commit subject:** `session: a deny-only PreToolUse guard for the orchestrator — typed plan headings are append-only, host mutations and history rewrites refused; task-status.toml is the way to withdraw a task (test: unit, lint)`

### RT5rb (code, S) — RT5r fix round: the JSON parse sits inside the fail-closed guard behind a nesting bound, the audit-subject test discriminates, a non-object tool_input on a sub-agent tool denies, the depth budget is exact, the wrapper escapes the table path

**dependsOn:** none

Gate `docs/reviews/2026-09-05-opus-review-rt7-RT5r.md` — REJECTED, two majors and three minors; everything else stands (six red-then-green tests, 82 bats, 18 of 19 mutants, runbook and header). Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/rt7/RT5r task/RT5r && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with RT5's subject.

**Contract additions:**
1. `main()` returns 0 on every path INCLUDING a payload that does not parse: `json.load` moves inside the `try/except BaseException`. Before parsing, stdin is read with a bound (4 MiB; more is "too large") and a linear, string-aware scan computes the maximum bracket nesting; nesting > 64, a read over the bound, or any parse failure (`RecursionError`, `MemoryError`, `ValueError`, a top level that is not an object) → DENY with reason `payload could not be parsed: <ExceptionName|too deep|too large>`, exit 0. The tool name is unknown when the payload does not parse, so the denial applies to every tool — an accepted over-denial the runbook states.
2. The audit-subject test discriminates: its payload's first-walked id is a table row and the offending id comes later under the implementation's walk order — `{"model": "<a routing-table OpenRouter row>", "steps": [{"model": "z-ai/glm-5.3"}]}` — a helper test asserts the walk yields the row first for that payload, and the subject test asserts the subject is the non-row id (mutation `model_ids[0]` → fails).
3. A sub-agent tool (`subagent`, `subagent_fork`, `workflow`) whose `tool_input` is not a JSON object (null, list, string, number) → DENY `model rule could not be evaluated: tool_input is not an object`; the bash/edit tools keep today's coercion (pinned).
4. The depth budget is exact: a model at depth 64 is reached by the model rule (its reason names the id), depth 65 is the budget overrun; the generator yields before it pushes (or checks the limit on push); the header and the runbook say 64.
5. The wrapper writes `hooks.json` with the routing-table path JSON-escaped (`jq --arg` or `python3 -c 'import json…'`, never string interpolation); a path containing `"` and a space round-trips.

- [ ] **Step 1: Tests, red on RT5r** — (1) a depth-100000 nested `tool_input` on a subagent payload (built by python, ~600 KB) → deny, exit 0, reason contains `could not be parsed`; (2) a 5 MiB stdin → deny, exit 0, `too large`; (3) a top-level JSON array → deny, exit 0; (4) the discriminating audit-subject payload of item 2 plus its walk-order helper; (5) `tool_input: null` and `tool_input: []` on a workflow payload → deny; the same on a bash payload → today's behaviour, pinned; (6) a non-row model at depth exactly 64 → denied by the model rule (reason names the id); at depth 65 → the budget reason; (7) wrapper: `--routing-table '/tmp/a "b"/routing.toml'` → `hooks.json` parses and its command carries the path intact. Every new test asserts `[ "$status" -eq 0 ]`.
- [ ] **Step 2: Red** (paste the failing test numbers into the log). **Step 3: Implement.** **Step 4: Green** — ruff; shellcheck; `nix develop -c bats tests/unit/70-dsh-openrouter.bats`; `unit`; `host-core`; lint gate; mutations, each must fail at least one test: `json.load` moved back outside the guard; the nesting pre-scan removed; the read bound removed; subject → `model_ids[0]`; the non-object coercion restored for sub-agent tools; the depth check off by one; the wrapper back to interpolation. RT5r's 18 kills still die. **Step 5: One commit**, RT5's subject.

**touches:** pkgs/dsh-openrouter/hook-guard.py, pkgs/dsh-openrouter/dsh-openrouter.sh, pkgs/dsh-openrouter/default.nix, tests/unit/70-dsh-openrouter.bats, docs/runbooks/lanes.md
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: the hook guard refuses a sub-agent or nested-seat model that is not an OpenRouter row of the routing table; fails closed when the table is unreadable (test: unit, host-core, lint)`
