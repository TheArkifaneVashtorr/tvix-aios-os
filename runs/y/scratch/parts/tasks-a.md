### SD1 (code, M) — the ladder in the routing table: rung and fallback rows, class in the key, factory_route and route.py in lockstep, the first rungs marked unmeasured

**dependsOn:** none

**Files:**
- Modify: `docs/ledger/routing.toml` (the header's key grammar; the new rows), `tools/factory/seat/factory-lib.sh` (`factory_route`, `factory_route_check`, new `factory_key_rung`), `tools/factory/route.py` (`CLASSES`, `resolve`, `check`, `lookup`), `tests/unit/80-seat-driver.bats`, `docs/ledger/claims.toml` (the gap rows)

**Interfaces:**

- A `[[route]]` row's keys are exactly `route`, `role`, `kind`, `size`, `model`, `effort` (as today) plus three optional keys: `rung` (an integer `1`–`9`, default `1`), `fallback` (a model id, no default), `class` (one of `nix-module | nix-check | bash-driver | python-evidence | js-workflow | bats-test | vm-test | docs-runbook | docs-plan | docs-board | any`, default `any`). Any other key stays a row error (`unknown key`, exit 3 / `RowError`, as today).
- `factory_route [--route R] [--rung N] [--class C] <role> <kind> <size> [FILE]` (bash) and `route.py [--file PATH] lookup ROUTE ROLE KIND SIZE [--rung N] [--class C]` (python), the same rule: candidates are the rows whose `rung` equals N (default 1) and whose `role`/`kind`/`size`/`class` each equal the request or `any`; specificity = the count of the four fields not `any`; the highest wins, ties go to the earliest row. Without `--rung`: only rows on route R (default `openrouter`) and the output is `MODEL EFFORT` — byte-identical to today. With `--rung N`: rows on route R when `--route` is given, else on **both** routes; the output is `MODEL EFFORT ROUTE FALLBACK` where `FALLBACK` is the row's `fallback` or `-`. `--rung 0`, a non-integer or `--rung` twice → `factory_route: bad --rung %q` exit 3 (`RowError`-free: `route.py` prints `route.py: bad --rung` exit 2, argparse's own code). No candidate at rung N → stderr `factory_route: ladder exhausted at rung N for ROLE/KIND/SIZE/CLASS` exit 3 (python: the same words, exit 3 — a new code, distinct from the table errors' 1). The route's `any/any/any` default row is still required (unchanged).
- `factory_route_check [FILE]` / `route.py check` validate every row as today plus: (1) `rung` outside `1`–`9` or not an integer → `row N: bad rung %q`; (2) `class` outside the eleven names → `row N: unknown class %q`; (3) a `fallback` whose model is not the `model` of some other row on the **same route** → `row N: fallback %q has no row on route %s`; (4) the ladder rule over every key a rung-≥2 row names exactly (its own `role/kind/size/class` tuple): resolving that key at rungs 1..max must find a row at every rung (`ladder ROLE/KIND/SIZE/CLASS: rung N missing`) and each adjacent pair either shares the route and differs in exactly one of {model, effort} (`ladder …: rung N→N+1 changes model and effort`; a pair that changes nothing: `… changes nothing`) or changes the route. Exit 3 (bash) / 1 (python) with the first error on stderr.
- `factory_key_rung <KEY>` (bash, factory-lib.sh; D3) prints `1`, `2` or `3`: strip trailing round tokens — `r` followed by optional digits, or exactly one of `b|c|d` — until none matches; any `r` token stripped → `3`; else any fix letter → `2`; else `1`. Pure bash, never fails, an empty key prints `1`.
- `route.py resolve(rows, route, role, kind, size, rung=1, cls="any", any_route=False) -> (model, effort, route, fallback)`: the extra positional-compatible keywords keep `resolve(rows, "openrouter", "orchestrate", "any", "any")` callable (SD4 imports it); `models` still derives the dark factory's map from the `claude` rung-1 rows only.
- The rows SD1 adds (each row's comment names its measurement or `unmeasured`, and the claims file carries one gap per unmeasured rung — the spec's rule):

```toml
[[route]]                       # rung 2 of implement/code/S — unmeasured (claim ladder-implement-code-S-rung2-unmeasured)
route = "openrouter"
role = "implement"
kind = "code"
size = "S"
rung = 2
model = "deepseek/deepseek-v4-pro-0813"
effort = "high"

[[route]]                       # rung 3 of implement/code/S — the claude route; printed by the driver, never run by it (unmeasured)
route = "claude"
role = "implement"
kind = "code"
size = "S"
rung = 3
model = "sonnet"
effort = "high"

[[route]]                       # rung 2 of implement/docs/any (D1: one variable — effort; unmeasured)
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
rung = 2
model = "deepseek/deepseek-v4-flash"
effort = "medium"

[[route]]                       # rung 3 of implement/docs/any (D1: one variable — model; unmeasured)
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
rung = 3
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]                       # rung 2 of review/any/any — the claude route (unmeasured)
route = "claude"
role = "review"
kind = "any"
size = "any"
rung = 2
model = "opus"
effort = "high"

[[route]]                       # the driver's own row (Question 1 default: Pro medium; unmeasured)
route = "openrouter"
role = "orchestrate"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]                       # rung 2 of orchestrate (Question 1's recommendation, measured against rung 1 by report ladder)
route = "openrouter"
role = "orchestrate"
kind = "any"
size = "any"
rung = 2
model = "deepseek/deepseek-v4-pro-0813"
effort = "high"

[[route]]                       # rung 3 of orchestrate — the claude route (unmeasured)
route = "claude"
role = "orchestrate"
kind = "any"
size = "any"
rung = 3
model = "fable"
effort = "high"
```

  and one `fallback = "deepseek/deepseek-v4-flash"` on the existing `implement/code/any` row (Flash approved 2/2 in `docs/reviews/2026-09-05-model-comparison.md`; as a sideways fallback it is unmeasured — claim `ladder-fallback-flash-unmeasured`). The header paragraph gains one sentence: "Optional per-row keys `rung` (1–9, default 1), `fallback` (a model with a row on the same route) and `class` (the `task-classes.toml` vocabulary, default any); rows with the same role/kind/size/class and rungs 1..n are that key's ladder; adjacent rungs on one route change exactly one of model/effort."
- Claims (`docs/ledger/claims.toml`, `status = "gap"`, `class = "unmeasured"`, `owner = "orchestrator"`, `opened = 2026-09-06`, `review_by = 2026-09-20`): `ladder-rung3-demand-unmeasured` (closes_by: `report ladder` shows an `escalate` count over five driver sessions, or the rung-3 rows are withdrawn), `ladder-implement-code-S-rung2-unmeasured`, `ladder-implement-docs-rung2-unmeasured`, `ladder-implement-docs-rung3-unmeasured`, `ladder-review-rung2-unmeasured`, `ladder-orchestrate-rung1-vs-rung2-unmeasured` (Question 1's measurement: five driver sessions per rung), `ladder-fallback-flash-unmeasured`, `driver-verbs-inside-seat-unit-unmeasured` (D8; closes_by: `operator:<date>` — one `factory-dispatch … --dry-run` and one real wave from a drive job's UI succeed).

**Facts (2026-09-27 on the tree, commands beside them):**

- `python3 tools/factory/route.py --file /tmp/draft-scratch/fx-rung.toml check; echo rc=$?` → `rc=0`, and `… lookup openrouter implement code S` → `deepseek/deepseek-v4-pro-0813 high`: `route.py` accepts an unknown key (`parse_table` stores any `key = value`, `cur[key] = val`) and treats the rung-2 row as an ordinary row, while `grep -n 'unknown key %q' tools/factory/seat/factory-lib.sh` → `printf 'factory_route: %s: row %d: unknown key %q\n'` — the bash walker refuses it. A table with a `rung` key makes the two implementations disagree today: that is this task's red.
- `grep -n 'Usage: factory_route\|implement | review | verify | baseline | research | audit | orchestrate | plan | any\|cur_spec=0' tools/factory/seat/factory-lib.sh` → `# Usage: factory_route [--route R] <role> <kind> <size> [FILE]`, the role arm (`orchestrate` and `plan` already accepted), `cur_spec=0` (specificity over three fields).
- `grep -n 'def resolve\|spec = (rrole\|MODEL_KEYS = (\|resolve(rows, "claude", role, kind, size)' tools/factory/route.py` → `def resolve(rows, route, role, kind, size):`, `spec = (rrole != "any") + (rkind != "any") + (rsize != "any")`, `MODEL_KEYS = (` and the `models` derivation from the `claude` rows.
- `grep -c '^\[\[route\]\]' docs/ledger/routing.toml` → `14`; `grep -n 'Change rows here, nowhere else' docs/ledger/routing.toml` → the header's last sentence. `cat docs/ledger/routing.toml`: the openrouter rows `implement/docs/any` Flash off, `implement/any/XS` Flash off, `implement/code/any` Pro medium, `review/any/any` Pro medium, the default Pro medium; the claude rows `orchestrate` fable high, `baseline` sonnet low, `implement` sonnet high, `review/code` opus high, `review/docs` sonnet medium, `verify`/`research` sonnet medium, `audit` fable high, the default sonnet medium. No `openrouter/orchestrate` row exists.
- `grep -n 'row.get("route") == "claude"\|model = row.get("model")' pkgs/dsh-openrouter/hook-guard.py` → the seat guard's model rule reads only `route` and `model` per row and ignores other keys: the new keys change nothing there, and a `fallback` must be a model with a row of its own, so the set of permitted models does not widen.
- `grep -n '@test' tests/unit/80-seat-driver.bats | grep -i 'route'` → the existing tests to keep green: `factory_route picks the most specific matching row, first row on ties`, `factory_route rejects a malformed or missing table`, `factory_route_check validates the committed routing table`, `factory_route --route claude picks the claude row, …`, `route.py validates the committed table and cross-checks factory_route's lookup, when route.py is present`, `factory_route and route.py agree on a discriminating tie (earliest row wins)`, `route.py check rejects a row missing any required key, a bad route, or a bad effort`, `route.py and factory_route accept the plan role and refuse the planner role`.
- `grep -n 'route.py' tests/factory/render.test.mjs` → `const routePy = path.join(__dirname, '..', '..', 'tools', 'factory', 'route.py')` and `'dark-factory.js default models must equal route.py models for the committed table'` — the built-in map is derived from `route.py models`, so the rung-1 `claude` rows must be the only ones `models` reads.
- `grep -n '^id = ' docs/ledger/claims.toml | tr '\n' ' '` → 30 ids; none begins `ladder-` or `driver-verbs-`. The gap-row shape: `id`, `text`, `status = "gap"`, `class = "unmeasured"`, `owner`, `opened`, `review_by`, `closes_by` (`sed -n '36,44p' docs/ledger/claims.toml`, the `effort-policy-n1` row).
- `CHAIN_RE = re.compile(r"^(?P<root>.*\d)(?P<suffix>[a-z]{1,2})$")` (`grep -n 'CHAIN_RE = ' pkgs/evidence/tasks.py`) — the graph's chain rule; `factory_key_rung` follows the telemetry plan's D7 tokeniser instead (`grep -n 'round_of' docs/superpowers/plans/2026-09-06-telemetry-store-1.md` → the rule and its table row 16), because `OG1r2` is its own chain root to the graph but rung 3 to the ladder.

- [ ] **Step 1: Write the failing tests** in `tests/unit/80-seat-driver.bats` (each row one `@test`; the fixture tables are heredocs in the test; `factory-lib.sh` is sourced with `. "$SEAT/factory-lib.sh"` the way the existing `factory_route` tests do):

| # | assertion | the one-line mutant that turns it red |
|---|---|---|
| 1 | on a fixture with `implement/code/any` Pro medium (rung 1), `implement/code/S rung=2` Pro high, `claude implement/code/S rung=3` sonnet high and both defaults: `factory_route implement code S` → `deepseek/deepseek-v4-pro-0813 medium` (unchanged shape); `factory_route --rung 2 implement code S` → `deepseek/deepseek-v4-pro-0813 high openrouter -`; `--rung 3` → `sonnet high claude -`; `--rung 4` → exit 3, stderr `ladder exhausted at rung 4 for implement/code/S/any`; `--route openrouter --rung 3` → exit 3 (the claude row is out of the requested route) | print the rung-1 row for an unknown rung; drop the route filter |
| 2 | `--class nix-module` picks a `class = "nix-module"` row over an equally specific `class = "any"` row; `--class any` and no `--class` pick the same row; a row with `class = "bogus"` → `unknown class` exit 3 | count `class` as `any` always |
| 3 | a `fallback` present → the fourth field prints it; `--rung 1` output for a row without one prints `-` | print an empty fourth field |
| 4 | `factory_route_check` on a fixture whose rungs 1→2 change model and effort together → exit 3 `changes model and effort`; rungs 1→2 identical → `changes nothing`; a rung-3 row with no rung-2 resolution → `rung 2 missing`; a route change with both fields changed → exit 0 | drop the route-change exemption → the good fixture fails; drop the gap check |
| 5 | `fallback = "x/y"` with no row → exit 3 `has no row on route openrouter`; a fallback naming a model that exists only on the `claude` route → the same refusal (same route rule) | search all routes |
| 6 | `rung = 0`, `rung = 10`, `rung = two` → `bad rung` exit 3; `rung = 1` explicit equals no `rung` | accept any integer |
| 7 | the committed `docs/ledger/routing.toml` passes `factory_route_check` and `route.py check` (extends the existing committed-table test); `factory_route --rung 3 orchestrate any any` on it → `fable high claude -`; `factory_route orchestrate any any` → `deepseek/deepseek-v4-pro-0813 medium` | any committed row breaking rule 4 |
| 8 | cross-check (extends `route.py … cross-checks factory_route's lookup`): for every fixture key in {implement/code/S, implement/docs/any, review/any/any, orchestrate/any/any} and every rung 1..4, `route.py lookup … --rung N` and `factory_route --rung N …` print the same line or both exit 3 with `ladder exhausted` | any divergence — e.g. python counts specificity over three fields |
| 9 | `route.py models` on the committed table equals the value before this change (pinned as the literal JSON the `factory-unit` test derives) | let `models` see rung-3 `claude` rows |
| 10 | `factory_key_rung`: `SD1`→1, `SD1b`→2, `N7c`→2, `W2-N6b`→2, `SD1r`→3, `SD1rb`→3, `OG1r2`→3, `CR2r3b`→3, `T10a`→1, `BFIX4`→1, `` (empty)→1 | strip `a`; treat `b` as a round letter only at the very end |
| 11 | `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06` prints nothing after the eight rows are added (run in Step 4; the assertion is the silent exit) | a row without `closes_by` |

- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/80-seat-driver.bats --filter 'rung|class|fallback|ladder|key_rung'` → every new test fails; the first failure line reads `factory_route: …/routing.toml: row 1: unknown key rung` (the walker refuses the fixture's key); the cross-check row 8 shows `route.py` printing `deepseek/deepseek-v4-pro-0813 high` where `factory_route` exits 3. Paste both.
- [ ] **Step 3: Make the change** — `factory_route`: parse `--rung`/`--class`; store `cur_rung` (default `1`) and `cur_fallback`, `cur_class` (default `any`) in `_factory_route_finish_row`; specificity over four fields; the route filter only without `--rung`; the exhausted message. `factory_route_check`: a second pass over the finished rows collecting `(route, role, kind, size, class, rung, model, effort, fallback)` tuples, then the three new rules (keep the row array in a bash array of `|`-joined fields; no subshell). `factory_key_rung`. `route.py`: `CLASSES`, the `resolve` signature, `check`'s rules, `lookup`'s flags, the exit code 3. The eight rows and the header sentence; the eight claims.
- [ ] **Step 4: Run green** — `nix develop -c treefmt`; `nix develop -c ruff format tools/factory/route.py`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix develop -c python3 tools/factory/route.py check`; `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `… factory-unit`; `… claims-validate`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the body from the script (Global Constraints), running Step 2's filter and Step 4's commands.

**Tests:** rows 1–11; the discriminating fixtures: a rung-3 row on the other route (rows 1, 4, 5), the equal-specificity `class` pair (row 2), the two-variable and zero-variable adjacent pairs (row 4), the four-key × four-rung cross-check (row 8), `T10a` against `SD1b` and `OG1r2` against `SD1r` (row 10).

**touches:** docs/ledger/routing.toml, tools/factory/seat/factory-lib.sh, tools/factory/route.py, tests/unit/80-seat-driver.bats, docs/ledger/claims.toml
**acceptance:** unit, factory-unit, claims-validate, lint
**commit subject:** `routing: the ladder — rung and fallback rows, class in the key, factory_route and route.py in lockstep, the first rungs marked unmeasured (test: unit, factory-unit, claims-validate, lint)`

### SD2 (code, S) — the technical class: task-classes.toml, one primary class per task from touches, the class in the brief and the json

**dependsOn:** none

**Files:**
- Create: `docs/ledger/task-classes.toml`, `tests/evidence/fixtures/plans/classes.md`
- Modify: `pkgs/evidence/tasks.py` (`load_task_classes`, `task_class`, the `class` field in `scan_repo`'s tasks and the `json` output, a `class` subcommand, one brief line), `tests/evidence/test_tasks.py`

**Interfaces:**

- `docs/ledger/task-classes.toml`: `[[rule]]` blocks, each `class = "<name>"` and `glob = "<fnmatch pattern>"`, in priority order (a tie goes to the earliest rule). The eleven names are the vocabulary SD1 pins: `nix-module`, `nix-check`, `bash-driver`, `python-evidence`, `js-workflow`, `bats-test`, `vm-test`, `docs-runbook`, `docs-plan`, `docs-board` (`any` is never a rule's class; it is the answer for no `touches`). First rules: `nix-module` ← `nixosModules/*`, `hosts/*`; `nix-check` ← `flake.nix`, `tests/integration/*.nix`; `vm-test` ← `tests/integration/*-vm.nix` (listed before `nix-check` so a VM file matches it first); `bash-driver` ← `tools/factory/seat/*`, `tools/*.sh`, `githooks/*`; `python-evidence` ← `pkgs/evidence/*`, `pkgs/seat/*`, `pkgs/helm/*`, `tools/ledger/*`, `tools/factory/route.py`, `tests/evidence/*`, `tests/seat/*`; `js-workflow` ← `tools/factory/*.js`, `.claude/workflows/*`, `tests/factory/*`; `bats-test` ← `tests/unit/*`; `docs-runbook` ← `docs/runbooks/*`, `CLAUDE.md`; `docs-plan` ← `docs/superpowers/*`, `docs/decisions/*`, `docs/reviews/*`, `docs/concepts/*`; `docs-board` ← `docs/OPERATIONS.md`, `docs/board/*`, `docs/ledger/*`. A `touches` entry is matched as a repo-relative path by `fnmatch.fnmatch(entry, glob)` and also against `entry + "/"`'s prefix for a directory entry (`docs/reviews` matches `docs/reviews/*`).
- `tasks.load_task_classes(root) -> list[dict]` reads `<root>/docs/ledger/task-classes.toml`; a missing file → `[]` (every class `any`); a rule whose `class` is outside the vocabulary or whose `glob` is empty → `ValueError("task-classes: rule N: …")`, which `check` reports as `tasks: task-classes.toml: …` and the brief degrades to `any`.
- `tasks.task_class(touches, rules) -> str`: for each entry the first rule that matches gives that entry's class; the task's class is the class with the most entries; a tie goes to the class of the earliest rule among the tied; no entry matched, or no `touches` → `any`.
- Every task dict from `scan_repo` gains `"class"`; `json` prints it; a new subcommand `tasks.py --root R class --plan <basename> <KEY>` prints the one word (exit 1 `tasks: unknown task <KEY> in <plan>` when absent; exit 2 on a broken rules file); `check` gains rule (g): a `task-classes.toml` error is an error. The brief gains, after `**Next wave**`, one line `**Classes (next wave):** <repo>: KEY=class KEY=class …` (only keys of the next wave; ≤ 200 chars, truncated with ` …`), so the existing `**Next wave** — …` line and its tests are untouched and the 40-line budget holds.

**Facts:**

- `grep -n 'class' pkgs/evidence/tasks.py` → nothing: no class derivation exists. `sed -n '114,160p' pkgs/evidence/tasks.py` (`parse_plan`) → the task dict's keys `key, kind, size, title, depends_on, touches, acceptance, repo, commit_subject, body, plan` and `cur["touches"] = parse_list(value)`.
- `grep -n 'Next wave\|len(md.splitlines()) <= 40' tests/evidence/test_tasks.py` → `assert "**Next wave** — nixos-agent-env: E7" in md` (line 485) and the 40-line budget assertion; `render_brief` writes the line as `lines.append("**Next wave** — " + …)`.
- `grep -n 'FIXTURES = ' tests/evidence/test_tasks.py` → `FIXTURES = HERE.parent / "fixtures" / "plans"`; `ls tests/evidence/fixtures/plans` → `legacy.md second.md typed.md`.
- `grep -n 'cp -r ${self}/docs/ledger docs/ledger' flake.nix` → both `evidence-unit` and `unit` copy the whole `docs/ledger`, so the new file reaches both sandboxes without a `flake.nix` change.
- The spec's tie fixture: `touches` under `nixosModules/` and `tests/` classify `nix-module` — with the rules above `tests/unit/x.bats` is `bats-test` and `nixosModules/x.nix` is `nix-module`, one entry each: the tie goes to the earliest rule, `nix-module` (the first block in the file).

- [ ] **Step 1: Write the failing tests** (`tests/evidence/test_tasks.py`; the fixture plan `classes.md` holds five typed tasks: `C1` touches `nixosModules/a.nix, tests/unit/a.bats` (tie → `nix-module`), `C2` touches `tests/unit/a.bats, tests/unit/b.bats, pkgs/evidence/x.py` (majority → `bats-test`), `C3` touches `tests/integration/x-vm.nix` (→ `vm-test`, not `nix-check`), `C4` (docs) with no `touches` (→ `any`), `C5` touches `docs/reviews` (a directory entry → `docs-plan`)):

| # | assertion | mutant |
|---|---|---|
| 1 | `task_class` over the five fixtures → `nix-module`, `bats-test`, `vm-test`, `any`, `docs-plan` | count the first entry only; drop the tie rule → `C1` becomes `bats-test`; reorder `nix-check` before `vm-test` → `C3` flips |
| 2 | `json` carries `"class"` for every task of the fixture repo (`repo_with(tmp_path, ["classes.md"])`) | omit the key |
| 3 | `tasks.py --root <fixture root> class --plan classes.md C2` prints `bats-test`; an unknown key exits 1 with `unknown task`; a rules file with `class = "bogus"` → `check` prints `tasks: task-classes.toml: rule 1: unknown class bogus` and `class` exits 2 | accept any name |
| 4 | the brief over the fixture prints `**Classes (next wave):** nixos-agent-env: C1=nix-module …` and the existing `**Next wave** — …` assertion still holds; a 30-key wave is truncated to ≤ 200 chars ending ` …` | drop the cap |
| 5 | the committed `docs/ledger/task-classes.toml` loads, every `class` is in the vocabulary, every glob is non-empty, and `task_class(["tools/factory/seat/factory-task"], rules)` → `bash-driver`, `task_class(["docs/ledger/routing.toml"], rules)` → `docs-board` | a committed rule with a typo |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence/test_tasks.py -q -k 'class'` → `AttributeError: module 'tasks' has no attribute 'task_class'` (paste the first line).
- [ ] **Step 3: Write** the table, the two functions, the field, the subcommand, the brief line; `nix develop -c ruff format pkgs/evidence tests/evidence`.
- [ ] **Step 4: Run green** — `nix develop -c pytest tests/evidence -q`; `git add` the new files; `python3 pkgs/evidence/repomap.py --root . write`; `nix develop -c python3 pkgs/evidence/tasks.py --root . check` (prints nothing); `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep Classes` (paste the line); `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–5; the discriminating fixtures: the one-each tie (`C1`), the 2-vs-1 majority (`C2`), the VM file that matches two globs (`C3`), the no-`touches` docs task (`C4`), the directory entry (`C5`).

**touches:** docs/ledger/task-classes.toml, tests/evidence/fixtures/plans/classes.md, pkgs/evidence/tasks.py, tests/evidence/test_tasks.py
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the technical class — task-classes.toml, one primary class per task from touches, the class in the brief and the json (test: evidence-unit, lint)`

### SD3 (code, M) — the driver climbs: the rung from the key, --prior carries the failed attempt, class and rung in the result, a claude rung prints its launch line

**dependsOn:** SD1, SD2

**Files:**
- Modify: `tools/factory/seat/factory-task` (`--rung`, `--fallback`, `--prior`; the class query; the ladder lookup; the escalate path; the new result lines), `tools/factory/seat/factory-brief` (`FACTORY_PRIOR_BLOCK`), `tools/factory/seat/factory-lib.sh` (`factory_prior_block`), `tests/unit/80-seat-driver.bats`

**Interfaces:**

- `factory-task <run> <repo-path> <KEY> [--model ID] [--after KEY2] [--rung N] [--fallback] [--prior <run>/<KEY>]`.
  - The rung: `--rung N` (an integer 1–9, else usage exit 2) or `factory_key_rung "$key"`. The class: `class=$(factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/tasks.py" --root "$repo_path" class --plan "$(basename -- "$plan")" "$key" 2>>"$log")` — a non-zero exit or an empty word → `class=any` and `factory_log "class: unavailable (tasks.py class exited N); using any"`. The lookup: `route_line=$(factory_route --rung "$rung" --class "$class" implement "$kind" "$size")` — four fields `MODEL EFFORT ROUTE FALLBACK`. An explicit `--model`/`OPENROUTER_MODEL` still wins over the row (`route: explicit`); `OPENROUTER_REASONING_EFFORT` still wins over the effort.
  - `--fallback`: the row's fourth field replaces the model (same effort); a row without one → `factory_die 2 "--fallback: the rung-N row for … has no fallback"`. Recorded as `fallback: <model>` (else the line is absent).
  - Ladder exhausted (`factory_route` exit 3 with `ladder exhausted`) → `factory_die 3 "<factory_route's message>"` before any workspace or run dir is created; a table error → the existing built-in default path with its warning (unchanged).
  - Escalate: when the row's `ROUTE` is `claude` and no explicit model was given, the task is not launched. The run dir is created, `<KEY>.result` is written with `FACTORY-RESULT status=skipped`, `FACTORY-CHECKS none=not-run`, `FACTORY-COMMITS 0`, `FACTORY-NOTES escalate: claude/implement — run the launch line in the operator's Claude Code session`, the usual `run:/key:/model:/effort:/route:` lines (`route: implement/<kind>/<size>`), then `rung: N`, `class: <c>`, `escalate: claude/implement`, `launch: Workflow({ scriptPath: 'tools/factory/dark-factory.js', args: { plan: 'docs/superpowers/plans/<basename>', prefix: '<run>', scratch: '<scratch>', tasks: <tasks.py --root <repo> waves --repo <name> --plan <basename> --factory-args, filtered to this key> } })` — the `tasks` value is the JSON the graph's own `--factory-args` prints for the plan, filtered to the one key (no graph logic re-derived; `factory_py` runs it), on one line. Exit 4 (a new code: `done` 0, `partial` 1, `failed` 2, `unknown` 3, `skipped` 4). No seat runs; no workspace is created.
  - `--prior <prun>/<pkey>`: `$FACTORY_RUNS/<prun>/<pkey>.result` must be readable (`factory_die 2 "no such prior result: …"`); the block is built by `factory_prior_block <result> <repo-path> <prun> <pkey> <runs-dir>` and handed to `factory-brief` through `FACTORY_PRIOR_BLOCK`; `prior: <prun>/<pkey>` joins the result lines. A malformed value (not `<run>/<KEY>`, either part empty) → usage exit 2.
- `factory_prior_block` prints, from the `.result` and the review file only:

```
## Prior attempt (<prun>/<pkey>)

- result: <the FACTORY-RESULT line, verbatim>
- error_class: <the value of the `error_class:` line, or unknown when the line is absent>
- route: <route:>; model: <model:>; effort: <effort:>; rung: <rung: or 1>
- usage: <the usage: line's JSON, verbatim>
- diffstat (the rejected commit):
<the lines between `diffstat:` and the next blank line, verbatim>
- review: <path or `none found`>
<the review's H1 (the first line beginning `# Opus gate`), then every finding line — a line whose first token after optional decoration (`#`, `-`, `*`, `N.`, `N)`, `**`) is BLOCKER, MAJOR or MINOR, case-insensitive — then every table row (a line beginning `|`) containing `surviv` case-insensitive, all verbatim>
```

  The review file: the last of `<repo-path>/docs/reviews/*-opus-review-<prun>-<pkey>.md` in name order, else `<runs-dir>/<prun>/<pkey>.review.md`, else none. The block is capped at 200 lines; when cut, the last line is `… (truncated to 200 lines)`. Never a `.log`, a `.dsh-home` or a transcript.
- `factory-brief`: when `FACTORY_PRIOR_BLOCK` is non-empty it is printed after the task section and before the WORKSPACE RULES as given (the block's own `## Prior attempt` heading); the seat's WORKSPACE RULES gain one sentence: "A `## Prior attempt` section, when present, is the record of the rejected attempt this task replaces: address every finding it lists; never copy it into a project file."
- `FACTORY_SEAT_SPOOL=1` (set by `seat-run` for a drive job — SD4): `factory-task` adds `--no-start --wait` to its `seat-submit headless` invocation; unset → today's invocation.

**Facts:**

- `grep -n 'route_line=$(factory_route\|route_label="implement\|kind_size=$(factory_task_kind_size\|brief=$(FACTORY_TASK_TEXT' tools/factory/seat/factory-task` → `route_line=$(factory_route implement "$kind" "$size" || true)`, `route_label="implement/$kind/$size"`, `kind_size=$(factory_task_kind_size "$plan" "$key")`, `brief=$(FACTORY_TASK_TEXT=${FACTORY_TASK_TEXT:-} "$FACTORY_BIN/factory-brief" "$plan" "$key")`.
- `grep -n 'command -v seat-submit\|seat-submit headless\|printf .route: %s\|printf .exit_code: %s\|printf .usage: %s\|result=$runs_dir/$key.result' tools/factory/seat/factory-task` → the seat-submit branch `if command -v seat-submit >/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then`, its `seat-submit headless \` call, and the result writer's `route:`, `exit_code:`, `usage:` lines around `result=$runs_dir/$key.result`. The exit-code table: `done) task_rc=0`, `partial) task_rc=1`, `failed) task_rc=2`, `*) … task_rc=3`.
- `grep -n 'FACTORY_BRIEF_EXTRA\|## REPO NOTES' tools/factory/seat/factory-brief` → `if [ -n "${FACTORY_BRIEF_EXTRA:-}" ]; then` and the `## REPO NOTES` heading — the pattern `FACTORY_PRIOR_BLOCK` copies (printed before the rules, not after).
- `grep -n 'error_class: %s\|plan: %s' docs/superpowers/plans/2026-09-06-telemetry-store-1.md` → T2 adds `printf 'plan: %s\n' "$plan"` after `route:` and `printf 'error_class: %s\n' "$error_class"` after `exit_code:`; SD3's lines go after `plan:` when it exists and after `route:` otherwise — the block reads `error_class:` when present and prints `unknown` when absent (T2 may land before or after SD3).
- `grep -n 'md=$runs_dir/$key.review.md' tools/factory/seat/factory-review` → the seat review's path; `ls docs/reviews | grep -c opus-review` → `164`, all named `<date>-opus-review-<run>-<KEY>.md` (T3's Facts: every name matches `^\d{4}-\d{2}-\d{2}-opus-review-(?P<run>[a-z0-9]+)-(?P<key>[A-Za-z0-9-]+)\.md$`).
- `grep -n 'const A = \|A\.plan\|A\.prefix\|A\.tasks\|Invoke' tools/factory/dark-factory.js` → `// Invoke:  Workflow({ scriptPath: 'tools/factory/dark-factory.js', args: {...} })` and `if (!A.plan || !A.prefix || !Array.isArray(A.tasks) || A.tasks.length === 0 || !A.scratch)` — the four required args the launch line carries; `sed -n '876,905p' pkgs/evidence/tasks.py` → `factory_args(repo_graph, plan)` builds the `tasks[]` JSON (`key, title, kind, checks, spec, dependsOn, touches`) that `waves --factory-args` prints.
- `sed -n '43,58p' tests/unit/80-seat-driver.bats` → `setup()` exports `FACTORY_PLAN`, `FACTORY_ROOT`, `FACTORY_RUNS` under `$BATS_TEST_TMPDIR`; the test at line 466 builds `seat_copy`, a fake `factory-ws`, a fixture toolbox and a fake `dsh-openrouter` that prints the four result lines — the idiom every new test copies; the fake-`seat-submit` idiom is at line 1118 (`The fake seat-submit records its argv, the --brief file's content …`).

- [ ] **Step 1: Write the failing tests** (`tests/unit/80-seat-driver.bats`; the fixture toolbox's `routing.toml` carries SD1's rows; `FACTORY_PYTHON3_CMD` points `factory_py` at the sandbox's `python3` so `tasks.py class` runs for real over a fixture repo with a `docs/ledger/task-classes.toml`):

| # | assertion | mutant |
|---|---|---|
| 1 | `factory-task r1 <repo> K1` (K1 `(code, S)`, touches `tools/factory/seat/x`) → the fake seat saw `--model deepseek/deepseek-v4-pro-0813` and effort `medium`; the result has `rung: 1`, `class: bash-driver`, `route: implement/code/S`, no `fallback:`/`prior:`/`escalate:` line | derive the rung from the run name; omit `class:` |
| 2 | `factory-task r1 <repo> K1b` → `rung: 2` and the fake seat saw effort `high` (the rung-2 row); `factory-task r1 <repo> K1r` → status `skipped`, exit 4, `escalate: claude/implement`, a `launch:` line containing `scriptPath: 'tools/factory/dark-factory.js'`, `prefix: 'r1'` and `"key": "K1r"`, and no fake seat ran (its marker file absent), no workspace created | launch anyway; derive rung 3 as 2 |
| 3 | `--rung 2` on `K1` → `rung: 2` and effort high; `--rung 9` → exit 3 `ladder exhausted`, no run dir; `--rung x` → exit 2 | accept the exhausted default |
| 4 | `--fallback` on a key whose rung-1 row carries `fallback = "deepseek/deepseek-v4-flash"` → the fake seat saw Flash, `fallback: deepseek/deepseek-v4-flash` in the result; on a row without → exit 2 | ignore the flag |
| 5 | the class query failing (a fixture repo without `task-classes.toml` → `tasks.py class` exits 2) → `class: any` in the result and `class: unavailable` in the log; the seat still runs | die on the failure |
| 6 | `--prior r0/K1` with a synthetic `r0/K1.result` (status failed, `error_class: provider-error`, `usage: {"input":1}`, a diffstat section of two lines) and a synthetic `docs/reviews/2026-09-06-opus-review-r0-K1.md` (an H1, `**MAJOR-1** x`, `- MINOR 2: y`, a table row `| M3 | survived |`, a body sentence mentioning "six minors" that is not line-initial) → the fake seat's brief holds `## Prior attempt (r0/K1)`, `- result: FACTORY-RESULT status=failed`, `- error_class: provider-error`, the two diffstat lines, the H1, the two finding lines, the survivor row, and not the sentence; the result has `prior: r0/K1` | drop the block → the brief assertion fails (the spec's mutant); count the inline sentence; drop the survivor filter |
| 7 | `--prior r0/K1` with no review anywhere → `- review: none found` and the block still present; a `.result` missing `error_class:` → `- error_class: unknown`; a 400-line review → the block ends `… (truncated to 200 lines)`; `--prior nonsense` → exit 2; `--prior r0/K9` (no such result) → exit 2 | cut nothing; accept a missing result |
| 8 | the fake seat's brief never contains the string `.log` from the prior run and `factory-task` never opens `r0/K1.log` (the fixture log is `chmod 000`) | read the log for the tail |
| 9 | `FACTORY_SEAT_SPOOL=1` with a fake `seat-submit` on PATH → its argv contains `--no-start` and `--wait`; unset → neither | drop the branch |
| 10 | `factory-brief` with `FACTORY_PRIOR_BLOCK` set prints it between the task section and `## WORKSPACE RULES`; unset → no `## Prior attempt` string | print it after the rules |

- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/80-seat-driver.bats --filter 'rung|prior|fallback|escalate|SPOOL|class:'` → the flags fail as `usage: factory-task …` exit 2 and the result files lack `rung:` (paste the first failure of rows 1, 2 and 6).
- [ ] **Step 3: Make the change** — the flags and their parsing; `factory_key_rung` (SD1) and the class query; the four-field route line; the escalate path with its `.result`; `factory_prior_block` in `factory-lib.sh`; `FACTORY_PRIOR_BLOCK` in `factory-brief`; the `--no-start --wait` branch; the result lines `rung:`, `class:`, `fallback:`, `prior:`, `escalate:`, `launch:` after `route:` (after `plan:` when that line exists).
- [ ] **Step 4: Run green** — `nix develop -c treefmt`; `nix develop -c shellcheck tools/factory/seat/factory-task tools/factory/seat/factory-brief tools/factory/seat/factory-lib.sh`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–10; the discriminating fixtures: `K1`/`K1b`/`K1r` (the three rungs from one root), the row with and without a fallback, the review with an inline "six minors" sentence against line-initial markers, the survivor table row against other table rows, the `chmod 000` log.

**touches:** tools/factory/seat/factory-task, tools/factory/seat/factory-brief, tools/factory/seat/factory-lib.sh, tests/unit/80-seat-driver.bats
**acceptance:** unit, lint
**commit subject:** `factory: the driver climbs — the rung from the key, --prior carries the failed attempt, class and rung in the result, a claude rung prints its launch line (test: unit, lint)`

### SD4 (code, S) — the drive job: seat-submit drive resolves the orchestrate row, refuses the shared home, --wait polls a spooled job; seat-run runs drive as web

**dependsOn:** none

**Files:**
- Modify: `pkgs/seat/seat-submit.py`, `pkgs/seat/seat-run.py`, `tests/seat/test_seat_submit.py`, `tests/seat/test_seat_run.py`, `flake.nix` (`seat-unit` copies `tools/factory/route.py`)

**Interfaces:**

- `seat-submit [--jobs-dir DIR] [--no-start] [--wait] [--routing-table PATH] [--route-py PATH] {headless|web|drive} --workspace PATH --dsh-home PATH [--model ID] [--effort LEVEL] [--brief FILE] [--port N] [--timeout S]`.
  - `headless`/`web`: unchanged, except that `--model`/`--effort` are now checked as required per mode in code (still required for both), and the job directory is built under `<jobs-dir>/.tmp-<id>/` (0700) and renamed to `<jobs-dir>/<id>` with `os.rename` once `job.json` (and `brief.txt`) are written — the directory appears whole (D7).
  - `drive`: `--model`/`--effort` given → stderr `seat-submit: drive takes its model and effort from the routing table` exit 2; `--port` required (exit 2 without it; an integer). The row: `sys.path.insert(0, dirname(route_py))`, `import route`, `rows = route.load_rows(table)`, `model, effort = route.resolve(rows, "openrouter", "orchestrate", "any", "any")[:2]` where `table = --routing-table` or `$FACTORY_ROUTING_TABLE` or `~/nixos-agent-env/docs/ledger/routing.toml`, and `route_py = --route-py` or `<table's repo root>/tools/factory/route.py` (the repo root is the table path with `/docs/ledger/routing.toml` removed). A missing `route.py` → exit 2 `seat-submit: no route.py at …`; `route.SchemaError`/`route.RowError` → exit 2 with the message. `job.json` gains `"route": "openrouter/orchestrate/any/any"` (`headless`/`web` write `"route": null`). The payload check: `os.path.realpath(dsh_home) == os.path.realpath(os.path.expanduser("~/.local/share/dsh-openrouter"))` → exit 2 `seat-submit: drive never runs on the operator's shared home (decision 2026-09-05 addendum, point 1)`; each of `skills/driving/SKILL.md`, `skills/planning/SKILL.md`, `AGENTS.md` under `dsh_home` must be a regular file after following symlinks (`os.path.isfile`) → else exit 2 `seat-submit: drive home lacks <path>`. `drive` starts the unit like `web` and returns 0 (no polling).
  - `--wait`: allowed with `headless` only (else exit 2 `--wait is for headless jobs`); with `--no-start` it polls `result.txt` exactly as the start path does, then streams `stdout.txt` and exits with `exit_code.txt`; on timeout it prints `seat-submit: timed out waiting for <result.txt>` and returns 124 **without** calling `systemctl` (there is no unit to stop from this side — the spool's unit is the operator's to stop). `--wait` without `--no-start` is accepted and changes nothing.
  - Whoever starts: after its own `systemctl start`, `seat-submit` writes `<id>/started` (`by=seat-submit <ISO ts>`, mode 0600) so the spool skips the job (SD5 reads it).
- `seat-run`: the `web` branch becomes `else:  # web or drive` and, for `mode == "drive"`, exports `FACTORY_SEAT_SPOOL=1` before the harness runs (the driver scripts inside read it — SD3). `url.txt` and the printed URL as for web.
- Error contract unchanged elsewhere: exit 2 on a bad workspace/brief/job dir, 124 on timeout, the unit's exit code otherwise.

**Facts:**

- `grep -n 'choices=\["headless", "web"\]\|--no-start\|--model", required=True\|--effort", required=True\|systemctl", "start"\|if args.no_start\|"mode": args.mode\|return 124' pkgs/seat/seat-submit.py` → `p.add_argument("mode", choices=["headless", "web"])`, `p.add_argument("--no-start", action="store_true")`, `--model`/`--effort` `required=True`, `subprocess.run(["systemctl", "start", f"seat@{job_id}"], check=False)`, `if args.no_start:` (returns 0 before the start), the job dict starting `"mode": args.mode,`, `return 124`.
- `grep -n 'job\["mode"\] == "headless"\|else:  # web\|os.environ\["DSH_HOME"\]\|runbook docs/runbooks/seat.md' pkgs/seat/seat-run.py` → the two-branch `if job["mode"] == "headless": … else:  # web`, `os.environ["DSH_HOME"] = job["dsh_home"]`, and a comment naming `docs/runbooks/seat.md` (a file that does not exist: `ls docs/runbooks` → no `seat.md`; SB5, held, creates it).
- `grep -n 'assert job == {\|def test_' tests/seat/test_seat_submit.py` → the byte-exact `job.json` assertion (`"mode","workspace","dsh_home","model","effort","brief","port"` plus `submitted`) that gains `"route": None`; the eight existing tests, driven in-process with `subprocess.run` monkeypatched (`_no_systemctl` records argv) — the idiom the new tests copy.
- `grep -n 'exec python3' pkgs/seat/default.nix` → `exec python3 ${./seat-submit.py} "$@"` — the package runs the file by path; `route.py` is imported from the checkout at run time, like the routing table itself (the unit's `FACTORY_ROUTING_TABLE = "/home/dalhaka/nixos-agent-env/docs/ledger/routing.toml"`, `grep -n FACTORY_ROUTING_TABLE nixosModules/seatLane.nix`).
- `grep -n 'cp -r ${self}/pkgs/seat pkgs/seat\|cp -r ${self}/tests/seat tests/seat' flake.nix` → the `seat-unit` sandbox holds only those two trees; the test's `--route-py <repo>/tools/factory/route.py` needs one more `cp`.
- `grep -n 'saved selection' docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md` → "Nothing automated changes the operator's saved selection: per-task homes no longer inherit it (P0, 2026-09-05)" — the rule the shared-home refusal enforces.
- `grep -n 'warn_missing_payload "$DSH_HOME' pkgs/dsh-openrouter/dsh-openrouter.sh` → the wrapper warns (never refuses) on a missing `skills/` or `AGENTS.md`; the drive mode refuses, because a driver without its skill set is exactly the seat the spec says must not run.

- [ ] **Step 1: Write the failing tests** (`tests/seat/test_seat_submit.py`, in-process as the file does; a fixture routing table under `tmp_path` with an `openrouter/orchestrate` row and the two defaults; `--route-py` pointing at `HERE.parents[2] / "tools" / "factory" / "route.py"`; a drive home built under `tmp_path` with the three payload files):

| # | assertion | mutant |
|---|---|---|
| 1 | `drive --no-start --port 43210` with a valid home → `job.json` `mode == "drive"`, `model == "deepseek/deepseek-v4-pro-0813"`, `effort == "medium"` (the fixture row), `route == "openrouter/orchestrate/any/any"`, `port == 43210`, `brief is None`; the id printed; no `systemctl` call | fall back to the openrouter default row silently (the fixture's default row carries a different effort, `low`, so the assertion discriminates) |
| 2 | the fixture table without an orchestrate row → the default row's values (`low`) — the resolve rule, not a hard-coded pair | hard-code Pro medium |
| 3 | `drive --model x` → exit 2 `takes its model and effort`; `drive` without `--port` → exit 2; `--route-py /nonexistent` → exit 2 `no route.py`; a table with a malformed row → exit 2 and the message | accept `--model` |
| 4 | a home whose realpath is `~/.local/share/dsh-openrouter` (monkeypatch `HOME` to `tmp_path` and create it) → exit 2 `never runs on the operator's shared home`; a symlink to it → the same | compare the strings, not the realpaths |
| 5 | a home missing `skills/driving/SKILL.md` → exit 2 naming it; `AGENTS.md` as a dangling symlink → exit 2; the three present as symlinks to real files → accepted | check with `os.path.exists` (a dangling symlink passes) |
| 6 | `headless --no-start --wait` with the poll patched to populate `result.txt`/`stdout.txt`/`exit_code.txt` → the stdout is streamed, the exit code propagated, and `_no_systemctl == []` | call `systemctl start` anyway |
| 7 | `headless --no-start --wait --timeout 1` with nothing arriving → 124, `timed out`, and `_no_systemctl == []` (no `stop`) | stop the unit |
| 8 | `--wait` with `web` or `drive` → exit 2 | accept |
| 9 | after the start path, `<id>/started` exists with `by=seat-submit`; under `--no-start` it does not exist | write it under `--no-start` |
| 10 | the job directory is renamed whole: `os.rename` is monkeypatched to record its source and destination — the source is `<jobs>/.tmp-<id>`, the destination `<jobs>/<id>`, and `job.json` already exists in the source at rename time (the recorder checks) | write into the final path directly |
| 11 | `test_seat_run.py`: a `drive` job runs the same argv as `web` (`--broker --bind-namespace <ns> -- --no-open --port <port>`), writes `url.txt`, and the fake harness sees `FACTORY_SEAT_SPOOL=1` in its environment; a `web` job does not | export it for web too |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/seat -q -k 'drive or wait or started or rename'` → `SystemExit: 2` from argparse on `drive` (`invalid choice: 'drive'`); paste the first line.
- [ ] **Step 3: Make the change**; add `cp ${self}/tools/factory/route.py tools/factory/route.py` (with `mkdir -p tools/factory`) to `seat-unit`; `nix develop -c ruff format pkgs/seat tests/seat`.
- [ ] **Step 4: Run green** — `nix develop -c pytest tests/seat -q`; `nix build .#checks.x86_64-linux.seat-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–11; the discriminating fixtures: a default row whose effort differs from the orchestrate row (rows 1–2), the realpath-equal symlinked home (row 4), the dangling symlink (row 5), the recorder on `os.rename` (row 10).

**touches:** pkgs/seat/seat-submit.py, pkgs/seat/seat-run.py, tests/seat/test_seat_submit.py, tests/seat/test_seat_run.py, flake.nix
**acceptance:** seat-unit, lint
**commit subject:** `seat: the drive job — seat-submit drive resolves the orchestrate row, refuses the shared home, --wait polls a spooled job; seat-run runs drive as web (test: seat-unit, lint)`

### SD5 (code, M) — the spool: seat-spool.path starts one seat@ per validated job, the drive job on the unit, the unit PATH for the driving verbs, asserted in seat-eval and seat-vm

**dependsOn:** SD4

**Files:**
- Create: `pkgs/seat/seat-spool.py`, `tests/seat/test_seat_spool.py`
- Modify: `pkgs/seat/default.nix` (`seat-spool`), `nixosModules/seatLane.nix` (the path and service units; the `seat@` PATH and `XDG_CACHE_HOME`; two tmpfiles rules), `flake.nix` (`seat-eval` assertions; `seatSpool` passed to `seat-vm`), `tests/integration/seat-vm.nix`

**Interfaces:**

- `seat-spool [--jobs-dir DIR] [--port-range A-B] [--systemctl CMD]` (stdlib; `--jobs-dir` default `/var/lib/seat/jobs`; `--port-range` default `43200-43299`; `--systemctl` default `systemctl`, tests pass a recorder). One pass, exit 0 always except an unusable jobs dir (exit 2). For every entry of the jobs dir whose name matches `^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$` (others — `.tmp-*` included — are skipped silently): skip when `started` or `exit_code.txt` exists in it; skip when `job.json` is absent (logged `spool: <id>: no job.json yet`); otherwise validate `job.json`: a JSON object whose keys are exactly `mode, workspace, dsh_home, model, effort, brief, port, submitted, route`; `mode ∈ {headless, web, drive}`; `workspace` and `dsh_home` absolute paths that are directories; `model` matches `^[A-Za-z0-9._:/-]+$`; `effort ∈ {off, low, medium, high, xhigh}`; `brief` is `null` or `"brief.txt"` with that file present; `port` is `null` for `headless` and an integer within the range for `web`/`drive`; `submitted` parses with `datetime.fromisoformat`; `route` is `null` or a string. Valid → write `started` (`by=seat-spool <ISO ts>`, mode 0644 — the one write the spool makes, so a job is never started twice) then `run([systemctl, "start", "--no-block", f"seat@{id}"], check=False)` and log `spool: <id>: started`. Invalid → write `refused` (one reason per line, 0644) and log `spool: <id>: refused: <first reason>`; never a start. Every reason is one of the fixed strings `keys: unexpected <k>` / `keys: missing <k>` / `mode: not in headless|web|drive` / `workspace: not a directory` / `dsh_home: not a directory` / `model: bad id` / `effort: not in enum` / `brief: <reason>` / `port: <reason>` / `submitted: not a timestamp` / `route: not a string`.
- `nixosModules/seatLane.nix` gains: `systemd.paths.seat-spool = { wantedBy = [ "multi-user.target" ]; pathConfig = { PathChanged = "/var/lib/seat/jobs"; Unit = "seat-spool.service"; }; }` and `systemd.services.seat-spool = { description = "start one seat@ unit per validated job in /var/lib/seat/jobs"; serviceConfig = { Type = "oneshot"; ExecStart = "${seatSpool}/bin/seat-spool --jobs-dir /var/lib/seat/jobs --port-range ${cfg.webPortRange}"; }; }` — root, no shell, one store path. The `seat@` unit: `path` becomes `[ cfg.harnessPackage pkgs.iproute2 seatTools.seat-submit pkgs.bash pkgs.coreutils pkgs.findutils pkgs.gnugrep pkgs.gnused pkgs.gawk pkgs.util-linux pkgs.procps pkgs.git pkgs.nix pkgs.zstd ]` (D8; `seatTools` is the `pkgs/seat` attrset the module already calls); `environment.XDG_CACHE_HOME = "/var/lib/seat/cache"`; `systemd.tmpfiles.rules` gains `"d /var/lib/seat/cache 0700 ${cfg.operatorUser} -"`. `ReadWritePaths`, `InaccessiblePaths`, `NoNewPrivileges`, `ProtectSystem`, `NetworkNamespacePath` and every other option are unchanged.
- `flake.nix` `seat-eval` gains: `c.systemd.paths.seat-spool.pathConfig.PathChanged == "/var/lib/seat/jobs"` and `.Unit == "seat-spool.service"`; the service's `ExecStart` matches `^/nix/store/[^ ]*/bin/seat-spool --jobs-dir /var/lib/seat/jobs --port-range 43200-43299$` (one string: no `sh`, no `bash`, no second command), `Type == "oneshot"`, no `User` set; `sc.ReadWritePaths == [ "/var/lib/seat" "-/home/dalhaka/factory" "-/home/dalhaka/nixos-agent-env" "-/home/dalhaka/flakes" "-/home/dalhaka/.local/share/dsh-openrouter" ]` (the literal list — the drive job inherits it unchanged); the unit's `path` renders every package of D8's list (`lib.all (p: lib.elem p unit.path) [ … ]`) and `unit.environment.XDG_CACHE_HOME == "/var/lib/seat/cache"`; `lib.elem "d /var/lib/seat/cache 0700 dalhaka -" c.systemd.tmpfiles.rules`.
- `tests/integration/seat-vm.nix`: `seatSpool` becomes an argument (`flake.nix` passes `seatTools.seat-spool`); the fixture's `serviceConfig.ReadWritePaths = [ "/tmp" ]` goes and the fixtures move to `/var/lib/seat/ws`, `/var/lib/seat/dsh` and `/var/lib/seat/brief` (the operator-owned tree the unit may write — D8: the production sandbox is what runs); the drive home fixture holds `skills/driving/SKILL.md`, `skills/planning/SKILL.md`, `AGENTS.md`. New steps: (8) `su - dalhaka -c 'seat-submit drive --workspace /var/lib/seat/ws --dsh-home /var/lib/seat/dsh --routing-table /var/lib/seat/routing.toml --route-py /var/lib/seat/route.py --port 43202'` (a fixture table with the orchestrate row and `route.py` copied in) → `url.txt` reads `http://10.100.4.2:43202` and the host reaches it; `jq -r .route /var/lib/seat/jobs/<id>/job.json` → `openrouter/orchestrate/any/any`; `systemctl show seat@<id> -p Environment --value` contains `XDG_CACHE_HOME=/var/lib/seat/cache` and, after the job, `ls /var/lib/seat/cache | wc -l` ≥ 1 (`FACTORY_SEAT_SPOOL` is set by `seat-run` in the harness's own environment, not the unit's, so it is not visible here — SD4's unit test pins it); (9) from inside a running job's user and mount view (`systemd-run --uid=dalhaka --property=NetworkNamespacePath=/run/netns/egress-seat -p ProtectSystem=strict -p ReadWritePaths=/var/lib/seat --wait seat-submit headless --no-start --wait --timeout 120 --workspace /var/lib/seat/ws --dsh-home /var/lib/seat/dsh --model deepseek/deepseek-v4-flash --effort off --brief /var/lib/seat/brief` — the unit's own sandbox options on a transient unit, since `systemctl` is unreachable from inside the seat by design) → exit 0, the printed output holds `vm-seat-answer`, `/var/lib/seat/jobs/<id>/started` reads `by=seat-spool`, `systemctl show seat-spool.service -p Result --value` is `success`, and the fake upstream's log gained a `Bearer sk-or-vm-fixture` line; (10) a job directory written by hand with `"mode": "drive", "port": 1` → within 10 s `refused` exists with `port: outside 43200-43299` and `systemctl list-units 'seat@*' --all` does not list it; a directory named `.tmp-x` with a valid `job.json` is never started; (11) the existing web step's assertions on `ss -ltn` and the probe namespace are unchanged.

**Facts:**

- `grep -n 'systemd.services."seat@" = {\|ExecStart = "${seatRun}/bin/seat-run %i"\|ReadWritePaths = \[\|path = \[\|cfg.harnessPackage\|pkgs.iproute2\|d /var/lib/seat/jobs\|ProtectSystem\|NetworkNamespacePath' nixosModules/seatLane.nix` → the template unit, `ExecStart = "${seatRun}/bin/seat-run %i";`, the five-entry `ReadWritePaths`, `path = [ cfg.harnessPackage pkgs.iproute2 ]`, `"d /var/lib/seat/jobs 0700 ${cfg.operatorUser} -"`, `ProtectSystem = "strict";`, `NetworkNamespacePath = netnsPath;`. `grep -rn 'systemd.paths\|PathChanged' nixosModules hosts` → nothing: no path unit exists in the tree yet.
- `grep -n 'cache_root=\|export XDG_CACHE_HOME=\|mkdir -p -- "$XDG_CACHE_HOME"' pkgs/dsh-openrouter/dsh-openrouter.sh` → `cache_root=${DSH_CACHE_ROOT:-/tmp}`, `export XDG_CACHE_HOME=${XDG_CACHE_HOME:-$cache_root/dsh-openrouter-cache-$(id -u)}`, `mkdir -p -- "$XDG_CACHE_HOME"` (the wrapper runs under `writeShellApplication`'s errexit); `grep -n 'serviceConfig.ReadWritePaths = \[ "/tmp" \]' tests/integration/seat-vm.nix` → the VM's fixture admits `/tmp` with the comment "ProtectSystem=strict makes /tmp read-only for the seat unit … The harness writes its DSH_HOME (/tmp/dsh) and its nix fetcher cache (XDG_CACHE_HOME under /tmp) on every launch". On core nothing admits `/tmp`: D8's prediction, measured by this task's VM.
- `grep -n 'unit = c.systemd.services."seat@"\|/bin/seat-run %i\|seat-eval-ok' flake.nix` → `seat-eval` asserts on the real `core` config and pins `ExecStart` by infix; `grep -n 'seatSubmit = seatTools.seat-submit' flake.nix` → the VM already takes the seat tools attrset's members as arguments.
- `grep -n 'su - dalhaka -c .seat-submit headless\|su - dalhaka -c .seat-submit web\|url.txt\|grep -rq sk-or-vm-fixture /var/lib/seat/jobs' tests/integration/seat-vm.nix` → the two existing submissions, the `url.txt` wait, and the negative `grep` over the jobs tree that every new fixture file must keep passing (no fixture may contain the key string).
- `grep -n 'current-system' nixosModules/modelLane.nix` → `"/run/current-system/sw"` on the lane's PATH: the precedent for a unit that shells out to profile binaries.
- `grep -n 'operatorUser = ' hosts/core/seat.nix` → `dalhaka`; `grep -n 'python3Minimal' flake.nix` → `host-core` asserts the dsh guard's interpreter only; `pkgs/seat` takes `python3` from `callPackage` (`sed -n '1,4p' pkgs/seat/default.nix`), so `seat-spool` adds no interpreter to the closure.

- [ ] **Step 1: Write the failing tests** — `tests/seat/test_seat_spool.py` (in-process, `--jobs-dir tmp_path`, `--systemctl` a recorder script or `subprocess.run` monkeypatched as `test_seat_submit.py` does):

| # | assertion | mutant |
|---|---|---|
| 1 | a valid headless job dir (from `seat-submit --no-start`'s own writer, imported by path, so the shape stays one) → one `["systemctl","start","--no-block","seat@<id>"]` call, `started` reads `by=seat-spool`, log `started` | start without `--no-block`; skip the marker |
| 2 | the same dir on a second pass → no call (the marker); a dir with `exit_code.txt` and no marker → no call; a dir with `started` by `seat-submit` → no call | ignore the marker |
| 3 | one job per reason: an extra key, a missing key, `mode: "batch"`, a relative `workspace`, a `dsh_home` that is a file, `model: "a b"`, `effort: "max"`, `brief: "brief.txt"` without the file, `brief: "x.txt"`, `port: 43199`, `port: 43300`, `port: null` on `web`, `port: 43201` on `headless`, `submitted: "yesterday"`, `route: 3` → each refused with its fixed string, `refused` written, no call | drop any one rule |
| 4 | names: `.tmp-20260906-101010-abcdef`, `20260906-101010-ABCDEF`, `README` → skipped silently, never started; a valid-name dir without `job.json` → logged `no job.json yet`, no marker, no `refused` | start `.tmp-` dirs |
| 5 | three valid jobs → three starts in name order; one refused among them → the other two start (a bad job never blocks the rest); exit 0 | stop at the first refusal |
| 6 | `--jobs-dir /nonexistent` → exit 2 and nothing else | exit 0 |
| 7 | the range: `--port-range 1-2` makes `port: 43201` refused with `outside 1-2` | ignore the flag |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/seat/test_seat_spool.py -q` → `FileNotFoundError` for `pkgs/seat/seat-spool.py` in the loader (paste); `nix build .#checks.x86_64-linux.seat-eval -L --no-link` after adding the assertions and before the module change → `seat-eval: seat-spool.path must watch /var/lib/seat/jobs` (paste the message).
- [ ] **Step 3: Make the change** — `seat-spool.py`; `default.nix`'s third `writeShellApplication`; the module's units, PATH, cache and tmpfiles; the `seat-eval` assertions; the VM's fixtures and steps 8–11.
- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/seat tests/seat`; `nix develop -c treefmt`; `nix develop -c pytest tests/seat -q`; `git add` the new files; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.seat-unit -L --no-link`; `… seat-eval`; `… seat-assertion-negative`; `… host-core`; `… seat-vm` (minutes; the VM proves the spool, the drive job and the production sandbox); `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–7, the `seat-eval` assertions (mutants: `PathChanged` → `PathModified`; a `bash -c` in `ExecStart`; a sixth `ReadWritePaths` entry; a dropped package → each assertion names the failing option), the VM steps 8–10 (mutants: `--no-block` dropped → step 9's transient unit blocks; the range check dropped → step 10 starts a unit; `/tmp` admitted again → step 8's cache assertion finds nothing under `/var/lib/seat/cache`).

**touches:** pkgs/seat/seat-spool.py, tests/seat/test_seat_spool.py, pkgs/seat/default.nix, nixosModules/seatLane.nix, flake.nix, tests/integration/seat-vm.nix
**acceptance:** seat-unit, seat-eval, seat-vm, host-core, lint
**commit subject:** `seat: the spool — seat-spool.path starts one seat@ per validated job, the drive job on the unit, the unit PATH for the driving verbs, asserted in seat-eval and seat-vm (test: seat-unit, seat-eval, seat-vm, host-core, lint)`
