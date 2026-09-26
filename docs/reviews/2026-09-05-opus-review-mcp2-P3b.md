---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run mcp2, task P3b — APPROVED

## Summary

The fix round does exactly what the P3 rejection asked and nothing else. The
wrapper is byte-identical to P3's (`git diff HEAD cc76c59 -- pkgs/dsh-openrouter/dsh-openrouter.sh`
is empty, and the two bases carry the same file), so this is a pure test-only
round; only `tests/unit/70-dsh-openrouter.bats` moved, in one commit on top of
`3f21ba82`, with the plan's subject byte-identical and the `Co-Authored-By`
trailer present.

Both surviving mutants are now dead, and I killed them myself rather than
taking the transcript's word. M2 (`model_explicit=1` forced at line 83) fails
the rewritten "left intact" test: the saved `z-ai/glm-5.3` selection is
clobbered and the wrapper announces `deepseek/deepseek-v4-pro-0813` on the
wire. M1 (drop `model_explicit=1` from the `--model` case) fails the new
`--model` test with the exact field error,
`dsh: UNKNOWN_MODEL: pi-ai provider "openrouter" has no configured model
"deepseek/deepseek-v4-pro-0813"`.

The red for the fix round itself is shown two ways: with the base's bats file
(`HEAD~1`) both mutants survive 58/58 green, and — the sharper one — with
*P3's own* defective bats file over HEAD's wrapper both mutants still survive
60/60 green. Swap in HEAD's tests and each dies. That is the defect measured
and then removed.

P3's four already-killed mutants (M3 indent, M4 headless skip, M5 effort
dropped, M6 env var ignored) were re-run and all still die, so the fix round
did not weaken the existing net. All acceptance runs are green: `unit` 133/133,
`host-core`, `lint`, the pre-commit gate, shellcheck, and the file alone at
61/61 including every pre-existing N21 test.

## Checks

Throwaway clone of `/home/dalhaka/factory/ws/mcp2/P3b` at `af9d66d`, branch
`task/P3b`, base `3f21ba82`. `XDG_CACHE_HOME` pinned under the session
scratchpad; all tooling via `nix develop -c`. Nothing was run against the live
host; the implementer workspace was never written to.

| what | result |
|---|---|
| commits on top of base | exactly one (`af9d66d`) |
| `git show --name-only HEAD` | `pkgs/dsh-openrouter/dsh-openrouter.sh`, `tests/unit/70-dsh-openrouter.bats` — nothing else (⊆ the allowed set) |
| wrapper diff vs P3 | `git diff HEAD cc76c59 -- pkgs/dsh-openrouter/dsh-openrouter.sh` empty; `git diff 3f21ba82 cc76c59~1 -- <both files>` empty, so the bases agree and the wrapper is P3's cherry-pick verbatim. **No code change beyond it.** |
| commit subject vs plan | byte-identical (`cmp` against the plan string) |
| trailers | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; `Generated-By: dsh …` extra, allowed |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass — `133 ok, 0 not ok`, incl. `ok 98/99/100` (the three model tests) and the N21 set `ok 57, 58, 61, 62, 64` |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | pass (core toplevel built) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | pass — "All checks passed!" |
| `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | pass, silent |
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 61/61 ok, incl. `ok 59` / `ok 60` / `ok 61` |
| hard-rules scan over `3f21ba82..HEAD` | no `sudo`, `nixos-rebuild`, `systemctl`, `2>/dev/null`, `mount --move`; no added line naming `/home`, `/etc`, `/var`, `/run` |

Diff walk of the test change, against the rejection's terms:

- **F1 fixed.** `without an explicit model the saved model selection is left
  intact` is now a `--headless` launch against `start_fake` over a saved
  *non-default* `z-ai/glm-5.3` selection, asserting exit 0, `FAKE-OK`, the
  `settings.yaml` read-back (`grep -c 'model: z-ai/glm-5.3' -eq 1`) **and** the
  captured request body's `model`. The `--dump-config` masking guard is gone
  and the seed is no longer the wrapper's own default, so the explicitness half
  of the condition is genuinely under test.
- **F2 fixed.** `an explicit --model overrides a saved model selection` added:
  `write_settings medium` (a saved Pro selection), `--model fake/model
  --headless`, asserting exit 0, no `UNKNOWN_MODEL`, the settings rewrite, and
  the wire model.
- The pre-existing `OPENROUTER_MODEL` test was refactored only cosmetically
  (a `dsh_home` local replacing the repeated `$XDG_DATA_HOME/dsh-openrouter`);
  its assertions are unchanged.
- Both new tests assert on `$FAKE_CAPTURE`, so the settings rewrite is checked
  end to end (file *and* wire), not just on disk.

## Red before green

The fix round's own red — the mutants must survive under the *old* tests and
die under the new ones. Wrapper held at `HEAD` throughout; only the bats file
was swapped.

| tests used | mutant | result |
|---|---|---|
| base `HEAD~1` (no model tests at all) | M2 | **SURVIVED** — 58 ok, 0 not ok |
| base `HEAD~1` | M1 | **SURVIVED** — 58 ok, 0 not ok |
| P3's defective file (`cc76c59`) | M2 | **SURVIVED** — 60 ok, 0 not ok |
| P3's defective file (`cc76c59`) | M1 | **SURVIVED** — 60 ok, 0 not ok |
| `HEAD` (this round) | M2 | **KILLED** — `not ok 60`, 60 ok / 1 not ok |
| `HEAD` (this round) | M1 | **KILLED** — `not ok 61`, 60 ok / 1 not ok |

The P3-file rows are the load-bearing ones: same wrapper, same mutants, only
the test text differs, and the survival flips to a kill. The `HEAD~1` rows are
the literal base comparison and survive trivially (the base has no model tests).

Kill detail, captured verbatim:

M2 (`sed -i '83s/model_explicit=0/model_explicit=1/'`):

```
not ok 60 without an explicit model the saved model selection is left intact
#   `[ "$(grep -c 'model: z-ai/glm-5.3' "$XDG_DATA_HOME/dsh-openrouter/settings.yaml")" -eq 1 ]' failed
# Last output:
# dsh-openrouter: deepseek/deepseek-v4-pro-0813 via http://127.0.0.1:45779/api/v1, …
# FAKE-OK
```

The saved selection is gone and the launch has silently switched models —
exactly the harm the rejection named.

M1 (`sed -i '97d'`):

```
not ok 61 an explicit --model overrides a saved model selection
#   `[ "$status" -eq 0 ]' failed
# Last output:
# dsh-openrouter: fake/model via http://127.0.0.1:45773/api/v1, …
# dsh: UNKNOWN_MODEL: pi-ai provider "openrouter" has no configured model "deepseek/deepseek-v4-pro-0813"
```

The original field error, reproduced by the mutant and caught by the new test.

## Mutation table

Each mutation applied to the clone's working tree, whole file run, then
reverted (`git status --porcelain` empty after each; the tracked tree is clean
at `af9d66d`).

| # | mutation | result | killed by |
|---|---|---|---|
| M1 | delete `model_explicit=1` from the `--model` case (line 97) | **killed** (60 ok / 1 not ok) | `an explicit --model overrides a saved model selection` — `UNKNOWN_MODEL`, status ≠ 0 |
| M2 | `model_explicit=0` → `model_explicit=1` (line 83) — rewrite applied with no explicit model | **killed** (60 ok / 1 not ok) | `without an explicit model the saved model selection is left intact` — saved `z-ai/glm-5.3` clobbered |
| M3 | model line written without its captured indent (`printf 'model: %s\n'`, line 329) | killed (59/2) | `an explicit OPENROUTER_MODEL overrides…` and `an explicit --model overrides…` |
| M4 | `[ "$mode" != dump ]` → `[ "$mode" = web ]` (line 356) — skip in headless | killed (58/3) | the two model tests plus N21's `…=off overrides a saved medium selection` |
| M5 | pass `""` as the level at the call site (line 357) — effort never written | killed (58/3) | three N21 tests (`overrides the default…`, `…=xhigh reaches the wire…`, `…=off overrides a saved medium…`) |
| M6 | delete `[ -n "${OPENROUTER_MODEL:-}" ] && model_explicit=1` (line 84) | killed (60/1) | `an explicit OPENROUTER_MODEL overrides a saved model selection…` |

Every branch of `model_explicit` — the two setters, the guard, and the two
write paths — is now pinned by a test that has been shown to fail.

## Findings

**F1 (P3) — closed.** The "left intact" guard is now load-bearing: non-default
seed, headless mode, file *and* wire read-back. Proven by M2's kill above.

**F2 (P3) — closed.** `--model` has a test, and it is the one that kills M1
with the original field error.

**F3 (P3) — still a board fact, unchanged.** This wrapper fix reaches the seat
only at the next `nixos-rebuild switch`; the running seat uses the installed
wrapper from the current generation. Until the operator switches, P0 (the
per-task dsh home dropping the saved model selection) is the operative fix.
Nothing in P3b changes that.

**F4 (nit, carried).** The block scan still matches `*model:*` as a substring,
so a future nested key ending in `model:` (e.g. `fallback-model:`) would be
rewritten as `model:`. Pre-existing looseness from N21; no change requested,
worth a line if that YAML grows.

**F5 (nit, carried).** Insert-when-missing still uses a hard-coded two-space
indent while a rewrite reuses the line's own indent. Pre-existing N21 pattern,
harmless for the file dsh writes.

**F6 (nit, carried, not adopted).** No test asserts 0600 after a *model-only*
rewrite; N21 asserts it after an effort rewrite, and it is the same
`chmod`/`mv` pair in one function. The rejection marked this optional and the
fix round did not take it. Coverage tidiness, not risk — leave it.

**F7 (new, cosmetic).** The pre-existing `OPENROUTER_MODEL` test was refactored
to a `dsh_home` local while the new "left intact" test spells the path out in
full four times. Inconsistent within twenty lines of each other; no behavioural
difference.

## Deviations

- Plan P3b Step 1/2 asked for the reds to be recorded in `FACTORY-NOTES`; they
  are (`P3b.result` names both, with the clobber and the `UNKNOWN_MODEL`
  reproduction). This gate re-measured both independently rather than relying
  on that note.
- Plan P3b Step 3 lists `bats`, `unit`, `host-core` and "lint gate". I ran the
  `lint` nix check *and* `githooks/pre-commit` (both pass) plus shellcheck, so
  either reading of "lint" is covered. The implementer ran the pre-commit gate;
  the transcript shows it reasoning about which one "lint" meant and choosing
  the gate — correct per CLAUDE.md, and the extra check confirms it either way.
- The plan's `touches` for P3b lists the wrapper as possibly modified ("no code
  change expected"). It was not modified beyond P3's cherry-pick — verified by
  an empty diff against `cc76c59`, which is the stronger claim.
- The implementer workspace carries one untracked leftover,
  `scratch/commit-msg.txt`, not covered by `.gitignore` and not in the commit.
  Cosmetic; nothing to fix in the branch, but it will show as untracked if the
  branch is used as a base.
- The gate wrote nothing outside its throwaway clone, the pinned nix cache
  directory and this file. The clone is clean at `af9d66d`; the implementer
  workspace was read only.
