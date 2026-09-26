# Opus gate — seat run mcp2, task P3 — REJECTED

## Summary

The implementation is right and I proved it: the wrapper now tracks whether the
model came from the operator (`--model` or a non-empty `OPENROUTER_MODEL`), and
on a non-`dump` launch it rewrites the saved `agent-default-model.model` before
dsh boots. The red is the real field failure — I re-ran it against the previous
wrapper and captured
`dsh: UNKNOWN_MODEL: pi-ai provider "openrouter" has no configured model
"deepseek/deepseek-v4-pro-0813"` verbatim. All five acceptance runs are green
(unit 130/130, host-core, lint, pre-commit, shellcheck), the effort behaviour
(N21) is untouched, and every pre-existing N21 test still passes. Scope, subject
line and trailer are exactly as the plan specifies.

The rejection is about evidence, not code. Two of the two behaviours the task
claims are unguarded by any test in the suite, and I proved both with mutants
that the whole file swallows:

1. **The "left intact" test cannot fail.** It launches `--dump-config`, and the
   write is skipped in `dump` mode by a *different* guard, so the explicitness
   guard is never exercised. It also seeds the model the wrapper would write
   anyway (`deepseek/deepseek-v4-pro-0813`), so even a headless run could not
   see a clobber. Forcing `model_explicit=1` at line 83 — i.e. deleting the
   "leave a saved preference alone" rule entirely — leaves all 60 tests green.
   The harm is real: with that mutant a saved `z-ai/glm-5.3` selection is
   silently overwritten with the wrapper default on an ordinary launch. This is
   the same trap the N21 author called out five tests above in the same file
   ("a `medium` seed could not [prove preservation]: medium equals the route
   default the wrapper would write") — the model half repeats it.

2. **`--model` is untested.** It is the first trigger named in the commit
   subject and in the plan's Interfaces, and deleting `model_explicit=1` from
   the `--model` case (line 97) leaves all 60 tests green — while a saved
   selection plus `--model fake/model` then dies with the exact field error
   again.

Both fixes are test-only, about a dozen lines, and I have already run the
replacements red and green (texts below). The wrapper source needs no change.

## Checks

Throwaway clone of `/home/dalhaka/factory/ws/mcp2/P3` at `cc76c59`, branch
`task/P3`, parent `6d59b8a`. Nothing was run against the live host.

| what | result |
|---|---|
| `git show --stat HEAD` | exactly `pkgs/dsh-openrouter/dsh-openrouter.sh` (+46/−14) and `tests/unit/70-dsh-openrouter.bats` (+44), one commit on top of the base |
| commit subject vs plan | byte-identical (`cmp` on the two strings) |
| trailers | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present; `Generated-By: dsh …` extra, allowed |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass — `1..130`, 130 ok, including `ok 98 an explicit OPENROUTER_MODEL overrides…` and `ok 99 without an explicit model…`; every N21 test still ok (`ok 64 without the env var a saved reasoningEffort high is left intact`) |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | pass (built the core toplevel) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | pass |
| `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | pass, silent |
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 60/60 ok, 17s |

Diff walk, against the task's terms:

- Explicitness tracked for both triggers: `model_explicit=0` then
  `[ -n "${OPENROUTER_MODEL:-}" ] && model_explicit=1` at init (safe under
  `set -e`: the failing `[` is not the last command of the `&&` list — proven
  by the 40-odd tests that run with the var unset), and `model_explicit=1` in
  the `--model` case.
- Call site: `if { [ -n "${OPENROUTER_REASONING_EFFORT:-}" ] || [ "$model_explicit" -eq 1 ]; } && [ "$mode" != dump ]`,
  passing `""` for a key that must not move. So with an explicit model and
  `mode != dump` the saved `model:` is rewritten; without one it is left intact.
- Effort behaviour unchanged: the `reasoningEffort` branch is the same walk with
  an added `[ -n "$level" ]`; the missing-block branch now defaults the level to
  `medium` so a model-only rewrite cannot write an empty effort.
- Pure bash throughout (`mapfile` + line walk, no awk/sed/grep — the wrapper's
  runtime PATH still has none), atomic write kept (`settings.yaml.tmp.$$`
  truncated first, `chmod 600`, `mv -f`, `chmod 600` again), N21b's stale-temp
  fix untouched.
- The N21 comment block gains a P3 paragraph that states the extended rule and
  the field failure; the "pure bash" paragraph now names three keys.
- Hard rules: no `sudo`, `nixos-rebuild`, `systemctl`, no `2>/dev/null`, no new
  language, nothing outside the two files.
- Web (UI) mode: no change beyond the documented one. `--denials` `exec`s at
  line 136, far above the write, so a denials read still writes nothing; `dump`
  still writes nothing; the route composition, port handling and `--host`
  refusal are untouched, and the two browser-UI tests pass. The one real
  consequence to note: an explicit `--model` on a UI launch now *persists* into
  the operator's saved picker selection and is not restored on exit — the same
  contract N21 set for effort, but worth knowing.

## Red before green

`git checkout HEAD~1 -- pkgs/dsh-openrouter/dsh-openrouter.sh`, then
`nix develop -c bats --print-output-on-failure tests/unit/70-dsh-openrouter.bats -f 'explicit OPENROUTER_MODEL'`:

```
not ok 1 an explicit OPENROUTER_MODEL overrides a saved model selection instead of dying UNKNOWN_MODEL
# (in test file tests/unit/70-dsh-openrouter.bats, line 930)
#   `[ "$status" -eq 0 ]' failed
# Last output:
# dsh-openrouter: fake/model via http://127.0.0.1:39211/api/v1, workspace-write, …
# dsh: UNKNOWN_MODEL: pi-ai provider "openrouter" has no configured model "deepseek/deepseek-v4-pro-0813"
```

Non-zero status and the exact field error. Restored afterwards; the same test is
`ok` at `HEAD`. Note for the record: the implementer's transcript records the red
only as "status != 0" and reasons the rest from the plan; the `UNKNOWN_MODEL`
line above is the gate's own capture, so the red is measured, not asserted.

The second new test is not red at `HEAD~1` — see the mutation table for why that
matters.

## Mutation table

Each mutation applied to the clone's working tree, whole file run, then
reverted.

| # | mutation | result | killed by |
|---|---|---|---|
| M1 | drop `model_explicit=1` from the `--model` case (line 97) — the explicit flag is ignored | **SURVIVED** (60/60 ok) | nothing |
| M2 | `model_explicit=0` → `model_explicit=1` (line 83) — the rewrite is applied even without an explicit model | **SURVIVED** (60/60 ok) | nothing; the "left intact" test cannot see it |
| M3 | write the model line without its captured indent (`printf 'model: %s\n'`) | killed | `an explicit OPENROUTER_MODEL overrides a saved model selection…` — dsh refuses the file: `invalid document … BLOCK_AS_IMPLICIT_KEY at line 5` |
| M4 | `[ "$mode" != dump ]` → `[ "$mode" = web ]` — rewrite skipped in headless mode | killed | `an explicit OPENROUTER_MODEL overrides…` and the N21 test `an explicit OPENROUTER_REASONING_EFFORT=off overrides a saved medium selection` |
| M5 | pass `""` as the level at the call site — effort never written | killed | three N21 tests: `OPENROUTER_REASONING_EFFORT overrides the default…`, `…=xhigh reaches the wire as xhigh`, `…=off overrides a saved medium selection` |
| M6 | drop `[ -n "${OPENROUTER_MODEL:-}" ] && model_explicit=1` (line 84) — the env var is ignored | killed | `an explicit OPENROUTER_MODEL overrides a saved model selection…` |

Proof that M1 and M2 are real defects and not equivalent mutants — two probe
tests written by the gate (both `ok` at `HEAD`, each red under its mutant, both
removed afterwards; the workspace and the clone's tracked tree are unchanged):

- `--model fake/model --headless` over a saved Pro selection: `ok` at `HEAD`;
  under M1 it dies with the same `UNKNOWN_MODEL` line as the original field bug.
- a saved `z-ai/glm-5.3` selection, plain headless launch, no explicit model:
  `ok` at `HEAD`; under M2 the assertion
  `grep -c 'model: z-ai/glm-5.3' … -eq 1` fails — the saved choice has been
  overwritten with `deepseek/deepseek-v4-pro-0813`.

## Findings

**F1 (blocking). The "left intact" guard is proven by nothing.** The test
`without an explicit model the saved model selection is left intact` runs
`--dump-config`; the rewrite is already skipped for every `dump` launch by the
`[ "$mode" != dump ]` half of the condition, so the `model_explicit` half is
never under test. It also seeds the wrapper's own default model, so it could not
detect a clobber even in headless mode. Fix (run red and green by the gate —
replace the test body with this):

```bash
@test "without an explicit model the saved model selection is left intact" {
  make_key
  mkdir -p "$XDG_DATA_HOME/dsh-openrouter"
  printf 'ui-onboarding:\n  welcomeNoticeVersion: 2026-08-13.1\nagent-default-model:\n  provider: openrouter\n  model: z-ai/glm-5.3\n  reasoningEffort: high\n' >"$XDG_DATA_HOME/dsh-openrouter/settings.yaml"
  chmod 600 "$XDG_DATA_HOME/dsh-openrouter/settings.yaml"
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  [ "$(grep -c 'model: z-ai/glm-5.3' "$XDG_DATA_HOME/dsh-openrouter/settings.yaml")" -eq 1 ]
}
```

A non-default saved model (`z-ai/glm-5.3` is in the default picker list, so the
route accepts it and the launch is clean) is what makes the read-back
load-bearing — exactly the reasoning the N21 comment already gives for seeding
`high` rather than `medium` on the effort side. Show it red with
`sed -i '83s/model_explicit=0/model_explicit=1/'` and record that.

**F2 (blocking). `--model` has no test.** The flag is the first trigger the
commit subject names, and M1 shows the suite is blind to it. Add (green at
`HEAD`, red with `sed -i '97d'`):

```bash
@test "an explicit --model overrides a saved model selection" {
  make_key
  write_settings medium
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --model fake/model --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" != *"UNKNOWN_MODEL"* ]]
  [ "$(grep -c 'model: fake/model' "$XDG_DATA_HOME/dsh-openrouter/settings.yaml")" -eq 1 ]
}
```

**F3 (board fact, not a defect).** This fix reaches the host only at the next
`nixos-rebuild switch`: the seat runs the *installed* wrapper from the current
system generation, not the checkout. Until the operator switches, P0 (the
per-task dsh home no longer inheriting a saved model selection) is the operative
fix for the Flash relaunch; P3 is defence in depth that starts defending after
the switch.

**F4 (nit).** The block scan matches `*model:*` and `*reasoningEffort:*` as
substrings, so a future nested key whose name ends in `model:` (say
`fallback-model:`) would be rewritten as `model:` and lost. Same looseness the
N21 effort scan already had; not worth a change now, worth a line if that YAML
ever grows.

**F5 (nit).** When the block exists but lacks the key, the insert uses a
hard-coded two-space indent (`printf '  model: %s\n'`) while a rewrite reuses
the line's own indent. Pre-existing pattern from N21, harmless for the file dsh
writes.

**F6 (nit).** No new test asserts 0600 after a *model-only* rewrite; the N21
test asserts it after an effort rewrite. It is the same `chmod`/`mv` lines in
one function, so this is coverage tidiness, not risk. Cheap to add to the F2
test if the fix round wants it.

## Deviations

- Plan Step 4 for P3 asks that "every existing N21 test must still pass" —
  verified: `unit` is 130/130 and the four N21 tests are named `ok` in the log.
- The plan prescribed both new tests verbatim, and the implementer transcribed
  them faithfully (adapting only the home variable, correctly, to
  `$XDG_DATA_HOME/dsh-openrouter` after reading `write_settings`). F1 is
  therefore a plan defect the implementer inherited rather than one it
  introduced — but the gate scores tests by whether they can fail, and this one
  cannot, so it blocks either way. The plan's P3 Step 1 text should be corrected
  in the same fix round so a re-run does not reproduce it.
- The gate wrote two probe tests into a scratch copy of the bats file to
  distinguish surviving mutants from equivalent ones; the file was deleted and
  the clone's tracked tree is clean (`git status --porcelain` empty). The
  implementer workspace was never touched.
