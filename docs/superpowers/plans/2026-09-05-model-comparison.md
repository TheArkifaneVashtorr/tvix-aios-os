# DeepSeek V4 Pro vs V4 Flash — a measured comparison (plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver reads the `### KEY (kind, size) — title` sections below.

**Goal:** the same two real tasks run once on `deepseek/deepseek-v4-pro-0813` and once on `deepseek/deepseek-v4-flash`, judged by the same Opus gate, so that "Pro is worth its price" becomes a measured claim (claims file row `pro-vs-flash-unmeasured`).

**Method** (precedent: `docs/reviews/2026-09-05-m2b-effort-measurement.md`): two seat runs from the same base, `mcp` (Pro) and `mcf` (Flash), effort `medium` in both arms; per arm the `.result` usage line (input, output, wall clock), the Opus verdict and the findings; one review doc `docs/reviews/2026-09-05-model-comparison.md`; only one arm of each pair is ever integrated (the approved one; Pro's when both are approved). The P1 pair is code XS, the P2 pair code S. Section texts within a pair are identical except the key.

**Spec:** none — an experiment the operator asked for on 2026-09-05; the decision it informs is `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md` (which names Flash) versus commit 835e454 (which made Pro the seat default).

## Global Constraints

- Build-only: never `sudo`, `nixos-rebuild`, `systemctl`. The host runs live from this repo.
- Checks run as `nix build .#checks.x86_64-linux.<name> -L --no-link`; the lint gate is `nix develop -c githooks/pre-commit`; commits through `nix develop -c git commit -F <msgfile>` (message file in the scratch directory, never `-m`).
- TDD: the failing check first, shown red before the change.
- Bash: shellcheck clean. Never `2>/dev/null` a gated command.
- Commit subjects: `<area>: summary (test: <checks>)` with the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Waves

| run | model | groups |
|---|---|---|
| `mcp` | `deepseek/deepseek-v4-pro-0813` | `"P1pro"` `"P2pro"` |
| `mcf` | `deepseek/deepseek-v4-flash` | `"P1flash"` `"P2flash"` |

Dispatch: `FACTORY_PLAN=$HOME/nixos-agent-env/docs/superpowers/plans/2026-09-05-model-comparison.md OPENROUTER_REASONING_EFFORT=medium nohup tools/factory/seat/factory-wave mcp "$HOME/nixos-agent-env" "P1pro" "P2pro" >"$HOME/factory/runs/mcp.wave.log" 2>&1 &` and the same with `OPENROUTER_MODEL=deepseek/deepseek-v4-flash … factory-wave mcf … "P1flash" "P2flash"`.

---

## Tasks

### P1pro (code, XS) — `launch-today.sh` dispatches from its own directory, not `~/factory/bin`

**dependsOn:** none

**Files:**
- Modify: `tools/factory/seat/launch-today.sh`

**Interfaces:** none. The seat scripts already resolve their helpers relative to their own directory (`here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)` in `factory-task`); this script is the last one naming the unversioned `~/factory/bin/` copy (Opus gate for R10, 2026-09-05: "launch-today.sh still names ~/factory/bin: plan gap for a tidy").

- [ ] **Step 1: Red.** `grep -n 'factory/bin' tools/factory/seat/launch-today.sh` prints three lines (9, 11, 13). That grep printing nothing is this task's green.
- [ ] **Step 2: Change.** After `set -euo pipefail` add `here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)`; replace every `"$HOME/factory/bin/factory-wave"` with `"$here/factory-wave"`. Rewrite the header comment (lines 2–3) to: `# launch-today.sh -- the 2026-09-04 fix-round launch, kept as the worked example of three concurrent seat runs. Dispatches through the versioned scripts beside it, never ~/factory/bin. Spends the operator's OpenRouter key.` (wrap at 80 columns).
- [ ] **Step 3: Green.** `grep -n 'factory/bin' tools/factory/seat/launch-today.sh` prints nothing; `nix develop -c shellcheck tools/factory/seat/launch-today.sh`; `nix develop -c githooks/pre-commit`; `nix build .#checks.x86_64-linux.lint -L --no-link`. Do not run the script.
- [ ] **Step 4: Commit.**

**touches:** tools/factory/seat/launch-today.sh
**acceptance:** lint
**commit subject:** `seat: launch-today.sh dispatches from its own directory, not ~/factory/bin (test: lint)`

### P1flash (code, XS) — `launch-today.sh` dispatches from its own directory, not `~/factory/bin`

**dependsOn:** none

**Files:**
- Modify: `tools/factory/seat/launch-today.sh`

**Interfaces:** none. The seat scripts already resolve their helpers relative to their own directory (`here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)` in `factory-task`); this script is the last one naming the unversioned `~/factory/bin/` copy (Opus gate for R10, 2026-09-05: "launch-today.sh still names ~/factory/bin: plan gap for a tidy").

- [ ] **Step 1: Red.** `grep -n 'factory/bin' tools/factory/seat/launch-today.sh` prints three lines (9, 11, 13). That grep printing nothing is this task's green.
- [ ] **Step 2: Change.** After `set -euo pipefail` add `here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)`; replace every `"$HOME/factory/bin/factory-wave"` with `"$here/factory-wave"`. Rewrite the header comment (lines 2–3) to: `# launch-today.sh -- the 2026-09-04 fix-round launch, kept as the worked example of three concurrent seat runs. Dispatches through the versioned scripts beside it, never ~/factory/bin. Spends the operator's OpenRouter key.` (wrap at 80 columns).
- [ ] **Step 3: Green.** `grep -n 'factory/bin' tools/factory/seat/launch-today.sh` prints nothing; `nix develop -c shellcheck tools/factory/seat/launch-today.sh`; `nix develop -c githooks/pre-commit`; `nix build .#checks.x86_64-linux.lint -L --no-link`. Do not run the script.
- [ ] **Step 4: Commit.**

**touches:** tools/factory/seat/launch-today.sh
**acceptance:** lint
**commit subject:** `seat: launch-today.sh dispatches from its own directory, not ~/factory/bin (test: lint)`

### P2pro (code, S) — the lint gate refuses `] && [` chains in bats tests

**dependsOn:** none

**Files:**
- Modify: `githooks/pre-commit` (after the ruff lines), `flake.nix` (the `lint` runCommand, before `touch $out`)
- Create: `tests/lint/bats-and-chain.sh` (the guard, so both enforcement points run the same code), `tests/lint/fixtures/and-chain.bats` (a fixture that must be refused)

**Interfaces:**
- Produces `tests/lint/bats-and-chain.sh [FILE...]`: exits 1 and names `file:line` for every line in the given `*.bats` files (default: `tests/unit/*.bats`) matching `\] && \[`; exits 0 otherwise. Fixture files under `tests/lint/fixtures/` are never scanned by default.

Why this is a defect and not style: inside a bats `@test`, bash's errexit ignores a failing command that is followed by `&&` (the shell exits only for the command after the final `&&`). So `[ "$a" -lt "$b" ] && [ "$b" -lt "$c" ]` on any line but the last passes silently when the first bracket is false — the assertion is vacuous (Opus gate for R3b, 2026-09-05, found exactly this). Two lines, `[ "$a" -lt "$b" ]` then `[ "$b" -lt "$c" ]`, each fail the test on their own.

- [ ] **Step 1: The guard and its fixture.** `tests/lint/fixtures/and-chain.bats`:

```bash
#!/usr/bin/env bats
# Fixture for tests/lint/bats-and-chain.sh: this file must be REFUSED.
@test "vacuous chain" {
  [ 1 -eq 2 ] && [ 2 -eq 2 ]
}
```

`tests/lint/bats-and-chain.sh`:

```bash
#!/usr/bin/env bash
# bats-and-chain.sh [FILE...] -- refuse `] && [` chains in bats tests.
# Inside a @test, bash's errexit ignores a failing command followed by `&&`,
# so `[ a ] && [ b ]` on any line but the last passes when `[ a ]` is false:
# the assertion is vacuous. Write the two brackets on two lines instead.
# Exit 1 and print file:line for every offender; exit 0 when clean.
set -euo pipefail
if [ $# -eq 0 ]; then
  set -- tests/unit/*.bats
fi
bad=0
for f in "$@"; do
  if grep -n '\] && \[' "$f"; then
    bad=1
  fi
done
if [ "$bad" -ne 0 ]; then
  echo "lint: '] && [' chain in a bats test is vacuous under errexit — split it onto two lines (tests/lint/bats-and-chain.sh)" >&2
  exit 1
fi
```

`chmod +x tests/lint/bats-and-chain.sh`; `git add tests/lint`.
- [ ] **Step 2: Red, both sides.** `nix develop -c tests/lint/bats-and-chain.sh tests/lint/fixtures/and-chain.bats; echo exit=$?` → prints `4:  [ 1 -eq 2 ] && [ 2 -eq 2 ]` and `exit=1`. `nix develop -c tests/lint/bats-and-chain.sh; echo exit=$?` → `exit=0`: `tests/unit/*.bats` is clean today (the chain the R3b gate found was in a task branch that never landed), so the fixture is the red and Step 4's mutation proves the wired gate.
- [ ] **Step 3: Wire it.** In `githooks/pre-commit` after the ruff lines: `# P2: no '] && [' chains in bats tests (vacuous under errexit).` then `tests/lint/bats-and-chain.sh`. In `flake.nix`'s `lint` runCommand before `touch $out`, the same two lines (the check runs in `${self}`, so `tests/lint/bats-and-chain.sh` resolves; `bash` and `grep` are in the sandbox's stdenv).
- [ ] **Step 4: Green.** `nix develop -c tests/lint/bats-and-chain.sh; echo exit=$?` → `exit=0`; `nix develop -c shellcheck tests/lint/bats-and-chain.sh`; `nix develop -c githooks/pre-commit`; `nix build .#checks.x86_64-linux.lint -L --no-link`; `nix build .#checks.x86_64-linux.unit -L --no-link`. Mutation (do it, record it): `printf '#!/usr/bin/env bats\n@test "m" {\n  [ 1 -eq 1 ] && [ 1 -eq 1 ]\n}\n' >tests/unit/00-mutant.bats; nix develop -c githooks/pre-commit; echo exit=$?` → the message above and `exit=1`; then `rm tests/unit/00-mutant.bats` and the gate is green again. Also `git add tests/unit/00-mutant.bats && nix build .#checks.x86_64-linux.lint -L --no-link` must fail the same way; `git rm -q --cached tests/unit/00-mutant.bats` afterwards (the file is already removed).
- [ ] **Step 5: Commit.**

**touches:** githooks/pre-commit, flake.nix, tests/lint/bats-and-chain.sh, tests/lint/fixtures/and-chain.bats
**acceptance:** lint
**commit subject:** `lint: refuse '] && [' chains in bats tests (vacuous under errexit) (test: lint)`

### P2flash (code, S) — the lint gate refuses `] && [` chains in bats tests

**dependsOn:** none

**Files:**
- Modify: `githooks/pre-commit` (after the ruff lines), `flake.nix` (the `lint` runCommand, before `touch $out`)
- Create: `tests/lint/bats-and-chain.sh` (the guard, so both enforcement points run the same code), `tests/lint/fixtures/and-chain.bats` (a fixture that must be refused)

**Interfaces:**
- Produces `tests/lint/bats-and-chain.sh [FILE...]`: exits 1 and names `file:line` for every line in the given `*.bats` files (default: `tests/unit/*.bats`) matching `\] && \[`; exits 0 otherwise. Fixture files under `tests/lint/fixtures/` are never scanned by default.

Why this is a defect and not style: inside a bats `@test`, bash's errexit ignores a failing command that is followed by `&&` (the shell exits only for the command after the final `&&`). So `[ "$a" -lt "$b" ] && [ "$b" -lt "$c" ]` on any line but the last passes silently when the first bracket is false — the assertion is vacuous (Opus gate for R3b, 2026-09-05, found exactly this). Two lines, `[ "$a" -lt "$b" ]` then `[ "$b" -lt "$c" ]`, each fail the test on their own.

- [ ] **Step 1: The guard and its fixture.** `tests/lint/fixtures/and-chain.bats`:

```bash
#!/usr/bin/env bats
# Fixture for tests/lint/bats-and-chain.sh: this file must be REFUSED.
@test "vacuous chain" {
  [ 1 -eq 2 ] && [ 2 -eq 2 ]
}
```

`tests/lint/bats-and-chain.sh`:

```bash
#!/usr/bin/env bash
# bats-and-chain.sh [FILE...] -- refuse `] && [` chains in bats tests.
# Inside a @test, bash's errexit ignores a failing command followed by `&&`,
# so `[ a ] && [ b ]` on any line but the last passes when `[ a ]` is false:
# the assertion is vacuous. Write the two brackets on two lines instead.
# Exit 1 and print file:line for every offender; exit 0 when clean.
set -euo pipefail
if [ $# -eq 0 ]; then
  set -- tests/unit/*.bats
fi
bad=0
for f in "$@"; do
  if grep -n '\] && \[' "$f"; then
    bad=1
  fi
done
if [ "$bad" -ne 0 ]; then
  echo "lint: '] && [' chain in a bats test is vacuous under errexit — split it onto two lines (tests/lint/bats-and-chain.sh)" >&2
  exit 1
fi
```

`chmod +x tests/lint/bats-and-chain.sh`; `git add tests/lint`.
- [ ] **Step 2: Red, both sides.** `nix develop -c tests/lint/bats-and-chain.sh tests/lint/fixtures/and-chain.bats; echo exit=$?` → prints `4:  [ 1 -eq 2 ] && [ 2 -eq 2 ]` and `exit=1`. `nix develop -c tests/lint/bats-and-chain.sh; echo exit=$?` → `exit=0`: `tests/unit/*.bats` is clean today (the chain the R3b gate found was in a task branch that never landed), so the fixture is the red and Step 4's mutation proves the wired gate.
- [ ] **Step 3: Wire it.** In `githooks/pre-commit` after the ruff lines: `# P2: no '] && [' chains in bats tests (vacuous under errexit).` then `tests/lint/bats-and-chain.sh`. In `flake.nix`'s `lint` runCommand before `touch $out`, the same two lines (the check runs in `${self}`, so `tests/lint/bats-and-chain.sh` resolves; `bash` and `grep` are in the sandbox's stdenv).
- [ ] **Step 4: Green.** `nix develop -c tests/lint/bats-and-chain.sh; echo exit=$?` → `exit=0`; `nix develop -c shellcheck tests/lint/bats-and-chain.sh`; `nix develop -c githooks/pre-commit`; `nix build .#checks.x86_64-linux.lint -L --no-link`; `nix build .#checks.x86_64-linux.unit -L --no-link`. Mutation (do it, record it): `printf '#!/usr/bin/env bats\n@test "m" {\n  [ 1 -eq 1 ] && [ 1 -eq 1 ]\n}\n' >tests/unit/00-mutant.bats; nix develop -c githooks/pre-commit; echo exit=$?` → the message above and `exit=1`; then `rm tests/unit/00-mutant.bats` and the gate is green again. Also `git add tests/unit/00-mutant.bats && nix build .#checks.x86_64-linux.lint -L --no-link` must fail the same way; `git rm -q --cached tests/unit/00-mutant.bats` afterwards (the file is already removed).
- [ ] **Step 5: Commit.**

**touches:** githooks/pre-commit, flake.nix, tests/lint/bats-and-chain.sh, tests/lint/fixtures/and-chain.bats
**acceptance:** lint
**commit subject:** `lint: refuse '] && [' chains in bats tests (vacuous under errexit) (test: lint)`

## Field bug found at launch (2026-09-05 ~12:20) and the fix tasks

The Flash arm died at boot in both tasks, zero tokens: `dsh: UNKNOWN_MODEL: pi-ai provider "openrouter" has no configured model "deepseek/deepseek-v4-pro-0813"`. Root cause, traced: `factory_seed_dsh_home` (`tools/factory/seat/factory-lib.sh`) symlinks every entry of the operator's shared home into the per-task home except `sessions`, the route file and `hooks.json` — so `settings.yaml`, whose saved `agent-default-model.model` is Pro, comes along. The wrapper's `write_agent_reasoning_effort` (N21) rewrites only `reasoningEffort` in that file and leaves `model:` intact by design ("a saved preference is the operator's choice"), while the route it generates lists only the requested model and the picker extras. dsh then boots with the saved selection (Pro) against a route that has no Pro → UNKNOWN_MODEL. Any seat run that asks for a model other than the operator's saved one fails the same way; every run so far asked for Pro, which is why it never showed. Reproduced without a seat: seeding a fresh home from the shared one yields `settings.yaml -> ~/.local/share/dsh-openrouter/settings.yaml` with `model: deepseek/deepseek-v4-pro-0813`.

| run | model | groups | when |
|---|---|---|---|
| `mcp2` | Pro | `"P0"` `"P3"` | now |
| `mcf` (relaunch) | Flash | `"P1flash"` `"P2flash"` | after P0 is gated, integrated and fast-forwarded to main (the seat runs from the checkout) |

P3 is defence in depth: it lands with the next switch and makes the wrapper itself honour an explicit model.

### P0 (code, S) — the per-task seat home never inherits a saved model selection

**dependsOn:** none

**Files:**
- Modify: `tools/factory/seat/factory-lib.sh` (`factory_seed_dsh_home`), `tests/unit/80-seat-driver.bats` (append)

**Interfaces:**
- Produces: `factory_seed_dsh_home DST` still symlinks every entry of `${FACTORY_SHARED_DSH_HOME_SRC:-~/.local/share/dsh-openrouter}` except `sessions`, `openrouter-route.yml`, `hooks.json` — and now also except `settings.yaml`, which is instead **copied** with the whole `agent-default-model:` block removed (the key line and every following line that starts with whitespace, up to the next top-level key or end of file). Everything else in the file (`ui-onboarding:` and its lines) survives byte for byte. The copy is a regular file, mode 0600. When the source has no `settings.yaml`, none is created. Pure bash (the seat's host PATH is not the devShell): `mapfile` + a line walk, the same style as the wrapper's `write_agent_reasoning_effort`.

Why: the wrapper writes a fresh `agent-default-model:` block with the requested model when the block is absent (`pkgs/dsh-openrouter/dsh-openrouter.sh`, the `agent_idx -lt 0` branch), so removing the block is what lets `--model` / `OPENROUTER_MODEL` take effect in a seeded home.

- [ ] **Step 1: Failing test** (append to `tests/unit/80-seat-driver.bats`; the file already defines `SEAT` and `REAL_BASH`):

```bash
@test "factory_seed_dsh_home copies settings.yaml without the saved model selection and symlinks the rest" {
  src="$BATS_TEST_TMPDIR/shared"
  mkdir -p "$src/sessions"
  printf 'ui-onboarding:\n  welcomeNoticeVersion: 2026-08-13.1\nagent-default-model:\n  provider: openrouter\n  model: deepseek/deepseek-v4-pro-0813\n  reasoningEffort: medium\nother-key: 1\n' >"$src/settings.yaml"
  printf 'x' >"$src/some-other-file"
  printf 'route' >"$src/openrouter-route.yml"
  dst="$BATS_TEST_TMPDIR/task-home"
  FACTORY_SHARED_DSH_HOME_SRC="$src" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_seed_dsh_home '$dst'"
  [ "$status" -eq 0 ]
  [ -f "$dst/settings.yaml" ]
  [ ! -L "$dst/settings.yaml" ]
  run grep -c 'agent-default-model\|deepseek-v4-pro\|reasoningEffort\|provider: openrouter' "$dst/settings.yaml"
  [ "$output" = "0" ]
  run grep -c 'welcomeNoticeVersion: 2026-08-13.1' "$dst/settings.yaml"
  [ "$output" = "1" ]
  run grep -c '^other-key: 1$' "$dst/settings.yaml"
  [ "$output" = "1" ]
  [ -L "$dst/some-other-file" ]
  [ ! -e "$dst/sessions" ]
  [ ! -e "$dst/openrouter-route.yml" ]
  run stat -c %a "$dst/settings.yaml"
  [ "$output" = "600" ]
}

@test "factory_seed_dsh_home with no settings.yaml in the source creates none" {
  src="$BATS_TEST_TMPDIR/shared2"
  mkdir -p "$src"
  printf 'x' >"$src/some-other-file"
  dst="$BATS_TEST_TMPDIR/task-home2"
  FACTORY_SHARED_DSH_HOME_SRC="$src" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_seed_dsh_home '$dst'"
  [ "$status" -eq 0 ]
  [ ! -e "$dst/settings.yaml" ]
  [ -L "$dst/some-other-file" ]
}
```

- [ ] **Step 2: Red** — `nix develop -c bats tests/unit/80-seat-driver.bats` → the first new test fails at `[ ! -L "$dst/settings.yaml" ]` (today it is a symlink). Record the failing line.
- [ ] **Step 3: Implement** in `factory_seed_dsh_home`: add `settings.yaml` to the `case` skip list, then after the loop:

```bash
  if [ -f "$src/settings.yaml" ] && [ ! -e "$dst/settings.yaml" ]; then
    factory_copy_settings_without_selection "$src/settings.yaml" "$dst/settings.yaml"
  fi
```

and a new function above it:

```bash
# Copy a dsh settings.yaml minus its `agent-default-model:` block, so the
# wrapper writes a fresh selection with the model this task asked for
# (field bug 2026-09-05: a symlinked settings.yaml carried the operator's
# saved Pro selection into a Flash run -> UNKNOWN_MODEL at boot).
factory_copy_settings_without_selection() {
  local src=$1 dst=$2
  local -a lines=()
  local line skipping=0 old_umask
  mapfile -t lines <"$src"
  old_umask=$(umask)
  umask 077
  : >"$dst"
  for line in "${lines[@]}"; do
    if [ "$line" = "agent-default-model:" ]; then
      skipping=1
      continue
    fi
    if [ "$skipping" -eq 1 ]; then
      case "$line" in
        '' | [[:space:]]*) continue ;;
        *) skipping=0 ;;
      esac
    fi
    printf '%s\n' "$line" >>"$dst"
  done
  chmod 600 -- "$dst"
  umask "$old_umask"
}
```

- [ ] **Step 4: Green** — `nix develop -c shellcheck tools/factory/seat/factory-lib.sh`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix develop -c githooks/pre-commit`. Also update the two-line comment above the skip list to name `settings.yaml` and why. Do not run any seat.
- [ ] **Step 5: Commit.**

**touches:** tools/factory/seat/factory-lib.sh, tests/unit/80-seat-driver.bats
**acceptance:** unit, lint
**commit subject:** `seat: the per-task dsh home copies settings.yaml without the saved model selection, so --model and OPENROUTER_MODEL take effect (test: unit, lint)`

### P3 (code, S) — the wrapper makes an explicit model win over a saved selection

**dependsOn:** none

**Files:**
- Modify: `pkgs/dsh-openrouter/dsh-openrouter.sh` (`write_agent_reasoning_effort` and the call site after it), `tests/unit/70-dsh-openrouter.bats` (append)

**Interfaces:**
- Produces: when the model was given explicitly (`--model ID` or a non-empty `OPENROUTER_MODEL`) and the mode is not `dump`, the saved `agent-default-model.model` in `$DSH_HOME/settings.yaml` is rewritten to that model before dsh boots — the N21 rule (env beats saved) extended from effort to model. Without an explicit model the saved selection is left alone, as today. Same pure-bash line walk, same atomic write and 0600.

- [ ] **Step 1: Failing test** (append to `tests/unit/70-dsh-openrouter.bats`; `make_key`, `start_fake`, `FAKE_PORT`, `FAKE_CAPTURE`, `TMPHOME` and `write_settings` already exist there — read `write_settings` first and write the file directly if it only sets the effort):

```bash
@test "an explicit OPENROUTER_MODEL overrides a saved model selection instead of dying UNKNOWN_MODEL" {
  make_key
  mkdir -p "$DSH_HOME"
  printf 'ui-onboarding:\n  welcomeNoticeVersion: 2026-08-13.1\nagent-default-model:\n  provider: openrouter\n  model: deepseek/deepseek-v4-pro-0813\n  reasoningEffort: medium\n' >"$DSH_HOME/settings.yaml"
  chmod 600 "$DSH_HOME/settings.yaml"
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" OPENROUTER_MODEL=fake/model run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  [[ "$output" != *"UNKNOWN_MODEL"* ]]
  run grep -c 'model: fake/model' "$DSH_HOME/settings.yaml"
  [ "$output" = "1" ]
  run grep -c 'deepseek-v4-pro' "$DSH_HOME/settings.yaml"
  [ "$output" = "0" ]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat and all(r["body"]["model"] == "fake/model" for r in chat), [r["body"].get("model") for r in chat]
PY
}

@test "without an explicit model the saved model selection is left intact" {
  make_key
  mkdir -p "$DSH_HOME"
  printf 'agent-default-model:\n  provider: openrouter\n  model: deepseek/deepseek-v4-pro-0813\n  reasoningEffort: medium\n' >"$DSH_HOME/settings.yaml"
  chmod 600 "$DSH_HOME/settings.yaml"
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  run grep -c 'model: deepseek/deepseek-v4-pro-0813' "$DSH_HOME/settings.yaml"
  [ "$output" = "1" ]
}
```

(If `DSH_HOME` is not the variable the file's helpers use for the temp home, use the one `write_settings` writes into — read the helper; do not invent a second home.)
- [ ] **Step 2: Red** — `nix develop -c bats tests/unit/70-dsh-openrouter.bats -f 'explicit OPENROUTER_MODEL'` → fails: status 1 and `UNKNOWN_MODEL` in the output (the exact failure the seat hit). Record it.
- [ ] **Step 3: Implement.** Track explicitness: after the arg loop, `model_explicit=0; [ -n "${OPENROUTER_MODEL:-}" ] && model_explicit=1;` and set `model_explicit=1` in the `--model` case. Generalise the line walk: rename `write_agent_reasoning_effort` to `write_agent_selection LEVEL_OR_EMPTY MODEL_OR_EMPTY` (keep the old name as a one-line wrapper if other call sites exist — `grep -n write_agent_reasoning_effort` first), finding both `reasoningEffort:` and `model:` under `agent-default-model:` and rewriting whichever argument is non-empty; when the block is absent write it with the current `$model` and the level (or the route default `medium` when no level was given). Call site: `if { [ -n "${OPENROUTER_REASONING_EFFORT:-}" ] || [ "$model_explicit" -eq 1 ]; } && [ "$mode" != dump ]; then write_agent_selection "${OPENROUTER_REASONING_EFFORT:+$reasoning}" "$( [ "$model_explicit" -eq 1 ] && printf %s "$model" )"; fi`. Update the N21 comment block to say the rule now covers the model too.
- [ ] **Step 4: Green** — `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh`; `nix develop -c bats tests/unit/70-dsh-openrouter.bats` (every existing N21 test must still pass — they pin the effort behaviour); `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix build .#checks.x86_64-linux.host-core -L --no-link` (the wrapper is a host package); lint gate.
- [ ] **Step 5: Commit.**

**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: an explicit --model or OPENROUTER_MODEL rewrites the saved agent-default-model selection before boot, as N21 does for effort (test: unit, host-core, lint)`

### P3b (code, S) — P3 fix round: the two untested triggers pinned (test-only)

**dependsOn:** none

Gate: `docs/reviews/2026-09-05-opus-review-mcp2-P3.md` — REJECTED. The wrapper change is correct; two mutants survived because P3's Step 1 prescribed a test that cannot fail (`--dump-config` skips the write by the *other* half of the guard, and it seeded the wrapper's own default model). P3's Step 1 is superseded by this section.

**Files:** the same as P3 — `pkgs/dsh-openrouter/dsh-openrouter.sh` (no code change expected), `tests/unit/70-dsh-openrouter.bats`. Original: `/home/dalhaka/factory/ws/mcp2/P3`, branch `task/P3` (commit cc76c59): `git fetch -q /home/dalhaka/factory/ws/mcp2/P3 task/P3 && git cherry-pick -n FETCH_HEAD`, then read the review in full — its Findings section contains the replacement test text the reviewer ran green at HEAD and red under the mutation.

- [ ] **Step 1** Replace the test `without an explicit model the saved model selection is left intact` with a **headless** launch against the fake upstream (`start_fake`) over a saved selection of a **non-default** model (e.g. `z-ai/glm-5.3`, which is in the picker extras so the route knows it) and no `--model`/`OPENROUTER_MODEL`: assert exit 0, the request body's `model` is `z-ai/glm-5.3`, and `settings.yaml` still says `model: z-ai/glm-5.3`. Red: force `model_explicit=1` in the wrapper → the test must fail (the saved selection is overwritten with the default); revert.
- [ ] **Step 2** Add `an explicit --model overrides a saved model selection`: saved Pro selection, `run dsh-openrouter --model fake/model --headless "Reply with the word ok."` against the fake: exit 0, no `UNKNOWN_MODEL`, request `model == fake/model`, `settings.yaml` has `model: fake/model`. Red: delete the `model_explicit=1` line in the `--model` case → fails with `UNKNOWN_MODEL`; revert.
- [ ] **Step 3** Green: `nix develop -c bats tests/unit/70-dsh-openrouter.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix build .#checks.x86_64-linux.host-core -L --no-link`; lint gate. Record both reds in FACTORY-NOTES.
- [ ] **Step 4** One commit, subject byte-identical to P3's.

**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: an explicit --model or OPENROUTER_MODEL rewrites the saved agent-default-model selection before boot, as N21 does for effort (test: unit, host-core, lint)`

### P1flashb (code, XS) — P1flash fix round: the machine check wins over the quoted prose

**dependsOn:** none

Gate: `docs/reviews/2026-09-05-opus-review-mcf2-P1flash.md` — REJECTED on one point: `grep -n 'factory/bin' tools/factory/seat/launch-today.sh` still prints line 4 (the header comment quotes `~/factory/bin`). The plan's Step 2 wording and Step 3's green contradict each other; in this repo the checkable claim outranks prose (the Pro arm resolved it the same way). Everything else in the commit was correct — keep it.

**Files:** `tools/factory/seat/launch-today.sh` only. Original: `/home/dalhaka/factory/ws/mcf2/P1flash`, branch `task/P1flash` (commit c9db99e): `git fetch -q /home/dalhaka/factory/ws/mcf2/P1flash task/P1flash && git cherry-pick -n FETCH_HEAD`.

- [ ] **Step 1** In the header comment replace the clause `never ~/factory/bin.` with `never the unversioned bin under ~/factory.` and re-wrap so every line is ≤ 80 columns (measure each line with `awk '{ if (length($0) > 80) print NR": "length($0) }'` — it must print nothing).
- [ ] **Step 2** Green: `grep -n 'factory/bin' tools/factory/seat/launch-today.sh` prints nothing; `nix develop -c shellcheck tools/factory/seat/launch-today.sh`; `nix develop -c githooks/pre-commit`; `nix build .#checks.x86_64-linux.lint -L --no-link`. Do not run the script.
- [ ] **Step 3** One commit, subject byte-identical to P1flash's.

**touches:** tools/factory/seat/launch-today.sh
**acceptance:** lint
**commit subject:** `seat: launch-today.sh dispatches from its own directory, not ~/factory/bin (test: lint)`
