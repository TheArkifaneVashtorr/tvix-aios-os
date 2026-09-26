# factory-dispatch — one command from plan to launched wave (plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox syntax. The seat driver reads the `### KEY (kind, size) — title` sections below.

**Goal:** `factory-dispatch <run> <repo-path> <plan-file> [--dry-run] [--all]` asks the derived task graph for the plan's next wave, launches it through `factory-wave` (each task's model and effort come from `docs/ledger/routing.toml` via `factory-task`, RT1), waits, and prints the task brief — replacing hand-typed wave groups. Decision: `docs/decisions/2026-09-05-dsh-harness-factory-parked.md`.

**Facts (2026-09-05):** `nix develop -c python3 pkgs/evidence/tasks.py --root <repo> waves --repo <name> --plan <basename>` prints one line per remaining wave, each line the seat driver's quoted groups (e.g. `"G1 G4" "G2" "G3"`); the first line is the next wave; no output when nothing is schedulable. `<name>` is the repo's `name` in `docs/ledger/repos.toml`, matched by `path`. `factory-wave <run> <repo-path> "<group>"…` exits non-zero when any task did not reach `status=done`. `checks.unit` runs `bats tests/unit` (every file) and copies `tools/factory/seat` into its sandbox. The seat's host PATH has no python: the graph is queried through `factory_python3` (the toolbox devShell, `factory-lib.sh`).

## Global Constraints

- Build-only; never `sudo`, `nixos-rebuild`, `systemctl`. Checks via `nix build .#checks.x86_64-linux.<name> -L --no-link`; lint gate `nix develop -c githooks/pre-commit`; commits via `nix develop -c git commit -F <msgfile>` with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer. TDD, red first. Bash, shellcheck clean.
- Do not edit `tests/unit/80-seat-driver.bats`, `tools/factory/seat/factory-lib.sh`, `flake.nix`, `githooks/pre-commit` (RT2b is editing them now): new script, new bats file, README section only.
- Never launch a real seat in tests: `factory-wave` is faked on PATH.

## Tasks

### FD1 (code, S) — `factory-dispatch`: plan → next wave → routed launch → brief

**dependsOn:** none

**Files:**
- Create: `tools/factory/seat/factory-dispatch` (executable), `tests/unit/82-factory-dispatch.bats`
- Modify: `tools/factory/seat/README.md` (a "Dispatching a plan" section replacing the hand-typed `factory-wave` example as the primary way; `factory-wave` stays documented as the low-level tool)

**Interfaces:**
- `factory-dispatch <run> <repo-path> <plan-file> [--dry-run] [--all] [--repo-name NAME]`. Resolves `<repo-path>` to its `name` in `<repo-path>/docs/ledger/repos.toml` when `--repo-name` is absent (match on the expanded `path`; die 2 with a message when no row matches — the graph must know the repo). Runs `factory_python3 "$FACTORY_TOOLBOX_REPO/pkgs/evidence/tasks.py" --root "<repo-path>" waves --repo NAME --plan "$(basename <plan-file>)"`; takes the FIRST line as the wave; no line → prints `factory-dispatch: nothing schedulable in <plan> (all landed, in flight, or blocked)` and exits 0. Splits the line into groups exactly as the seat's quoting means (a shell `eval "set -- $line"` on a line that only ever contains `"KEY KEY" "KEY"` tokens — validate the line against `^("[A-Za-z0-9 -]+" ?)+$` first and die 5 otherwise). `--dry-run` prints `would run: factory-wave <run> <repo-path> "<group>" …` and exits 0 without launching. Otherwise runs `FACTORY_PLAN=<plan-file> factory-wave <run> <repo-path> "<group>"…` (the `factory-wave` beside this script, `$here/factory-wave`, so a fake on PATH in tests must be reached via `FACTORY_WAVE_CMD` override: `${FACTORY_WAVE_CMD:-$here/factory-wave}`), propagates its exit code, then prints the brief (`factory_python3 … tasks.py --root <repo-path> brief`). `--all`: after a wave exits 0, recompute and launch the next until none remains; stop at the first non-zero exit with the summary of that wave. Every launched wave is logged to stderr with its groups and to `~/factory/runs/<run>/dispatch.log`.
- The README section shows: `tools/factory/seat/factory-dispatch sc5 ~/nixos-agent-env docs/superpowers/plans/<plan>.md --dry-run` then without `--dry-run`; the gate and integration steps that remain manual (`factory-review`/Opus, `factory-integrate`, the fast-forward).

- [ ] **Step 1: Failing tests** (`tests/unit/82-factory-dispatch.bats`; follow `80-seat-driver.bats`'s conventions: `SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"`, scripts via `bash`, `FACTORY_ROOT` under the test tmpdir). Fixture repo: a git repo with `docs/ledger/repos.toml` naming it (`name = "fx"`, `path = "<tmp repo path>"`) and a typed plan with `A1 (code, S) dependsOn none`, `A2 (code, S) dependsOn A1`, `B1 (docs, XS) dependsOn none` (A1 and B1 disjoint touches). Fake `tasks.py`? No — the graph is real: set `FACTORY_TOOLBOX_REPO` to the real repo checkout (`$BATS_TEST_DIRNAME/../..`) so `factory_python3` runs the real `tasks.py` against the fixture repo (in the sandbox the devShell is unavailable — so ALSO allow `FACTORY_PYTHON3_CMD` to override the interpreter: `${FACTORY_PYTHON3_CMD:-…nix develop…}`; in tests set it to the sandbox's `python3`; document the override in the script header). Fake `factory-wave` on PATH via `FACTORY_WAVE_CMD` that records its arguments to a file and exits 0 (or 1 when `FAKE_WAVE_FAIL=1`). Tests: (a) `--dry-run` prints `would run: factory-wave r1 <repo> "A1" "B1"` (A1 and B1 are the first wave; A2 blocked) and the fake is NOT called; (b) without `--dry-run` the fake receives exactly `r1 <repo> "A1" "B1"` and `FACTORY_PLAN` set to the plan path, exit 0, and the output ends with a `# Task brief` block; (c) after marking A1 and B1 landed (commit their plan subjects into the fixture repo's history) the next wave is `"A2"`; (d) all landed → the "nothing schedulable" line, exit 0; (e) `--repo-name` absent and no matching row → exit 2 with a message; (f) a malformed waves line (inject via `FACTORY_WAVES_CMD` override that prints `rm -rf /`) → exit 5, nothing launched; (g) `FAKE_WAVE_FAIL=1` → exit non-zero propagated, `--all` stops after the first wave.
- [ ] **Step 2: Red** — `nix develop -c bats tests/unit/82-factory-dispatch.bats` → every test fails (`No such file`).
- [ ] **Step 3: Implement** (bash; `set -euo pipefail`; `here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)`; source `factory-lib.sh` for `factory_log`, `factory_die`, `factory_python3`, `FACTORY_TOOLBOX_REPO`, `FACTORY_RUNS`).
- [ ] **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/82-factory-dispatch.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link` (the new file's tests named in the log); lint gate. Real dry run from the checkout: `tools/factory/seat/factory-dispatch fdx "$HOME/nixos-agent-env" docs/superpowers/plans/2026-09-05-seat-routing.md --dry-run` prints a `would run:` line naming whatever is ready (or the nothing-schedulable line); paste it into FACTORY-NOTES. Never launch a real wave.
- [ ] **Step 5: Commit.**

**touches:** tools/factory/seat/factory-dispatch, tests/unit/82-factory-dispatch.bats, tools/factory/seat/README.md
**acceptance:** unit, lint
**commit subject:** `seat: factory-dispatch launches a plan's next wave from the derived graph with routed models, dry-run and --all (test: unit, lint)`

## After the first gate (2026-09-05 evening)

FD1 REJECTED (`docs/reviews/2026-09-05-opus-review-fd1-FD1.md`). The plan's Fact "the first line is the next wave" was wrong; the implementer re-derived dependencies in bash from a plan path resolved against the caller's cwd, which offered blocked tasks as ready. Corrected facts: after G12 (`2026-09-05-session-context.md`), `tasks.py … waves --repo NAME --plan <basename> --next` prints exactly the next wave's seat groups on one line, or nothing; in-flight tasks are state `running` and never offered. The `unit` sandbox does not copy `pkgs/evidence`, so 5 of FD1's 7 tests skipped there — FD1b adds that copy (flake.nix is in scope for FD1b, after OG1 lands).

### FD1b (code, S) — the dispatcher asks the graph and does no graph logic of its own

**dependsOn:** G12 (chained: `--next` and `running`), OG1 (its flake.nix copy line lands first)

**Files:** `tools/factory/seat/factory-dispatch`, `tests/unit/82-factory-dispatch.bats`, `tools/factory/seat/README.md`, `flake.nix` (the `unit` sandbox copies `pkgs/evidence` and `docs/ledger`, so the dispatcher's tests run for real — mirror how G6/OG1 added their copy lines; nothing else in flake.nix)

**Interfaces (replace FD1's):** the wave comes ONLY from `factory_python3 "$FACTORY_TOOLBOX_REPO/pkgs/evidence/tasks.py" --root "<repo-path>" waves --repo NAME --plan "$(basename <plan-file>)" --next` (override `FACTORY_WAVES_CMD` for tests); the dispatcher never reads `dependsOn`. `<plan-file>` is resolved against `<repo-path>` when relative and must exist and be readable — else die 2. A non-zero exit from the graph query → die 6 `factory-dispatch: graph query failed` (never "nothing schedulable"). Empty output → the nothing-schedulable line, exit 0. Line validated against `^("[A-Za-z0-9 -]+" ?)+$` before `eval` (keep). `--all`: a progress guard — if the same line repeats after a wave that exited 0, die 7 `no progress`. `wave_rc` captured without the `set -e` dead path (`if ! …; then rc=$?; fi`). Every launch logged to stderr AND `$FACTORY_RUNS/<run>/dispatch.log` — both tested (mutation: drop either → a test fails).
- Disclosure rule: any algorithm the section does not name goes in FACTORY-NOTES, or the round is rejected.

- [ ] **Step 1: Tests** — keep FD1's seven (adjusted to the `--next` fake), add: relative plan path resolved against repo-path (cwd elsewhere) still works; unreadable plan → exit 2; graph query exit 1 → exit 6, nothing launched; `--all` with a fake that never changes the wave → exit 7 after one launch; `dispatch.log` contains the wave line; stderr contains it; `--repo-name` override honoured; a `running` task (fake graph output omits it) is not launched. Under `unit`: all tests RUN (no skip) — confirm in the build log.
- [ ] **Step 2: Red** (fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/fd1/FD1 task/FD1 && git cherry-pick -n FETCH_HEAD`, then remove the bash dependency parsing). **Step 3: Implement.** **Step 4: Green** — shellcheck; bats; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate; real dry run against this repo (report verbatim; no launch). **Step 5: One commit**, FD1's subject.

**touches:** tools/factory/seat/factory-dispatch, tests/unit/82-factory-dispatch.bats, tools/factory/seat/README.md, flake.nix, docs/MAP.md
**acceptance:** unit, lint
**commit subject:** `seat: factory-dispatch launches a plan's next wave from the derived graph with routed models, dry-run and --all (test: unit, lint)`
