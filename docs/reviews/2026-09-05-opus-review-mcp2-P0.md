---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run mcp2, task P0 — APPROVED

## Summary

P0 fixes the field bug that killed both Flash tasks at boot with zero tokens:
`factory_seed_dsh_home` symlinked the operator's shared `settings.yaml` — whose
saved `agent-default-model.model` is Pro — into every per-task `DSH_HOME`, so a
run that asked for any other model booted the saved selection against a route
that does not list it (`UNKNOWN_MODEL`).

The change is exactly what the plan's `### P0 (code, S)` specifies, character
for character: `settings.yaml` joins the symlink skip list, and a new
`factory_copy_settings_without_selection` copies it minus the whole
`agent-default-model:` block (key line plus every following whitespace-indented
or blank line, stopping at the next top-level key or EOF). Pure bash —
`mapfile` and a line walk, no `awk`/`sed`/`grep`/`python`, which matters because
the seat's host PATH is not the devShell. The copy is a regular file, mode 0600,
written under `umask 077` with the caller's mask restored; nothing is created
when the source has no `settings.yaml`; an existing destination file is not
overwritten. The commit touches exactly the two planned files, its subject is
byte-identical to the plan's, and it carries the `Co-Authored-By` trailer (plus
a `Generated-By` line, which is fine).

Red was reproduced at the exact assertion the plan named. Four load-bearing
mutations are killed. The end-to-end reproduction against the operator's real
shared home (read-only — checksum unchanged before and after) produces a seeded
`settings.yaml` with the block gone and `ui-onboarding` intact, and the installed
wrapper in `--dump-config` mode (no network, no spend) dumps
`agent-default-model → model: deepseek/deepseek-v4-flash`. Approved; the four
surviving mutations are test-coverage gaps outside the fixture's shape, not
defects in the shipped code.

## Checks

All run in a throwaway clone of `/home/dalhaka/factory/ws/mcp2/P0` at
`task/P0` head `7c0dd18`, base `6d59b8a`, tooling only via `nix develop -c`.

| command | result |
|---|---|
| `git show --stat HEAD` | exactly `tests/unit/80-seat-driver.bats` (+35) and `tools/factory/seat/factory-lib.sh` (+38 −2); no other paths |
| commit subject vs the plan's | `cmp` byte-identical |
| trailer | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present (`Generated-By: dsh …` also present, permitted) |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | pass (treefmt 0 changed, all checks passed) |
| `nix develop -c shellcheck tools/factory/seat/factory-lib.sh` | clean, exit 0 |
| `nix develop -c bats tests/unit/80-seat-driver.bats` | 10/10 ok |
| working tree after every experiment | `git status --porcelain` empty |

Interface audit of the new code, line by line:

- pure bash: the function uses only `mapfile`, `printf`, `case`, `umask`, and
  `chmod` (coreutils, always on a host PATH; the surrounding function already
  used `mkdir`/`ln`/`basename`). No `awk`, `sed`, `grep`, or `python`.
- `settings.yaml` is in the `case` skip list of the symlink loop, so no symlink
  is created for it.
- the copy runs only under `[ -f "$src/settings.yaml" ] && [ ! -e "$dst/settings.yaml" ]`
  — nothing created when the source has none, existing destination untouched.
- mode: `umask 077` around `: >"$dst"` plus an explicit `chmod 600 -- "$dst"`,
  then the caller's umask is restored (`old_umask=$(umask)` … `umask "$old_umask"`).
- block boundary: `[ "$line" = "agent-default-model:" ]` is an exact top-level
  match (an indented `agent-default-model:` nested elsewhere would not trigger
  it, which is correct); the skip ends at the first line that is neither blank
  nor whitespace-led, i.e. the next top-level key, and otherwise runs to EOF.
  The blank-line arm mirrors the wrapper's own block parser
  (`write_agent_reasoning_effort`: `[ -z "$line" ] && continue`), so the two
  agree on what "inside the block" means.
- the skip-list comment above `factory_seed_dsh_home` was updated to name
  `settings.yaml` and why, as Step 4 required.
- hard rules: `git show HEAD | grep -E 'sudo|nixos-rebuild|systemctl|2>/dev/null'`
  → nothing. No `] && [` chain in the new bats (the P2 guard would accept it).
- callers: `tools/factory/seat/factory-task:89` and
  `tools/factory/seat/factory-review:75`. Both want the model they asked for,
  so both are correctly served by the change.

## Red before green

```
git checkout HEAD~1 -- tools/factory/seat/factory-lib.sh
nix develop -c bats tests/unit/80-seat-driver.bats
```

```
not ok 8 factory_seed_dsh_home copies settings.yaml without the saved model selection and symlinks the rest
# (in test file tests/unit/80-seat-driver.bats, line 224)
#   `[ ! -L "$dst/settings.yaml" ]' failed
```

Exactly the assertion the plan's Step 2 predicted. Test 9 (no `settings.yaml`
in the source) passes both before and after — it is a guard against a future
regression, not a red. File restored; tree clean.

## Mutation table

Nine mutations of the shipped implementation, each run against
`tests/unit/80-seat-driver.bats` and reverted.

| # | mutation | result | killed by |
|---|---|---|---|
| M1 | block skip stops at the first indented line (`'' \| [[:space:]]*) skipping=0; continue ;;`) — keeps `model:` and `reasoningEffort:` | **killed** | test 8, line 226 `[ "$output" = "0" ]` (the `agent-default-model\|deepseek-v4-pro\|reasoningEffort\|provider: openrouter` count) |
| M2b | the skip swallows the next top-level key too (`*) skipping=0; continue ;;`) — drops `other-key: 1` | **killed** | test 8, line 230 `[ "$output" = "1" ]` (`^other-key: 1$`) |
| M3 | mode left default (`umask 022`, `chmod 600` deleted) | **killed** | test 8, line 235 `[ "$output" = "600" ]` |
| M4 | `settings.yaml` removed from the skip list, so it is symlinked again (the original bug) | **killed** | test 8, line 224 `[ ! -L "$dst/settings.yaml" ]` |
| M2 | the `skipping` flag is never reset (`*) : ;;`) — lines are still emitted, but a *later* top-level key's indented children would be dropped | survived | — |
| M5 | blank line inside the block ends the skip early (`''` arm removed) | survived | — |
| M6b | surviving lines lose their two-space indent (`printf '%s\n' "${line#  }"`) | survived | — |
| M9 | the do-not-clobber guard `[ ! -e "$dst/settings.yaml" ]` removed | survived | — |
| M6 | `skipping` initialised to 1 | survived — **degenerate**: the first line is a top-level key, which immediately resets the flag, so this is a no-op, not a real mutation |

The four kills cover the whole of what P0 is for: the block is removed, only the
block is removed, the copy is a regular file, and it is 0600. The four genuine
survivors are all shapes the fixture does not contain (a second top-level key
with children *after* the block; a blank line *inside* the block; indentation
byte-identity of surviving lines; a pre-existing destination file). See Findings.

## Reproduction

Read-only against the operator's shared home; MD5 of
`/home/dalhaka/.local/share/dsh-openrouter/settings.yaml` identical before and
after (`c59fc734e69bda23e7a8632acb3271d7`).

```
bash -c '. tools/factory/seat/factory-lib.sh; \
  FACTORY_SHARED_DSH_HOME_SRC=/home/dalhaka/.local/share/dsh-openrouter \
  factory_seed_dsh_home <scratch>/gate-mcp2-P0-home'
```

The shared source is (the block is last, i.e. the EOF branch the fixture does
not exercise — the fixture covers the next-top-level-key branch, so between them
both boundaries are now covered):

```
ui-onboarding:
  welcomeNoticeVersion: 2026-08-13.1
agent-default-model:
  provider: openrouter
  model: deepseek/deepseek-v4-pro-0813
  reasoningEffort: medium
```

The seeded home:

```
-rw-------  settings.yaml                       (regular file, 0600, not a symlink)
lrwxrwxrwx  AGENTS.md -> …/dsh-openrouter/AGENTS.md
lrwxrwxrwx  profiles, skills, storages -> …
lrwxrwxrwx  settings.yaml.bak-2026-09-04-xhigh -> …
(no sessions, no openrouter-route.yml, no hooks.json)
```

`cat -A` of the seeded `settings.yaml` — the block is gone, `ui-onboarding`
survives byte for byte, indentation and all:

```
ui-onboarding:$
  welcomeNoticeVersion: 2026-08-13.1$
```

Then, with the installed wrapper on the host PATH and no network call and no
spend:

```
DSH_HOME=<that home> OPENROUTER_MODEL=deepseek/deepseek-v4-flash \
OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 dsh-openrouter --dump-config
```

```
# == @deepseek-ai/dsh-base, patched by <that home>/openrouter-route.yml
- id: agent-default-model
  name: '@deepseek-ai/dsh-agent-default-model'
  config:
    provider: openrouter
    model: deepseek/deepseek-v4-flash
```

and the provider block lists `deepseek/deepseek-v4-flash` first, so there is no
model in the boot path that the route does not carry. `--dump-config` exits 0
and leaves the seeded `settings.yaml` untouched (still the two `ui-onboarding`
lines, still 0600), confirming dump mode skips the settings write.

What the wrapper would write at boot given the absent block, read from the
installed script (`/nix/store/jvlv9b0dhwi1i92n263x4vnal2h7fxz8-dsh-openrouter/bin/dsh-openrouter`):
`write_agent_reasoning_effort` scans for a line exactly equal to
`agent-default-model:`; with the block stripped it finds none, `agent_idx` stays
`-1`, and the `agent_idx -lt 0` branch appends

```
agent-default-model:
  provider: openrouter
  model: $model
  reasoningEffort: $level
```

where `model=${OPENROUTER_MODEL:-deepseek/deepseek-v4-pro-0813}` (or `--model`)
— i.e. the model this task asked for, Flash. Two further notes from that read,
both in the fix's favour: the write only happens at all when
`OPENROUTER_REASONING_EFFORT` is set and the mode is not `dump` (line 336), and
even when it does not happen the route's own patched `agent-default-model`
config carries the requested model, as the dump above shows. So P0 fixes the
boot with or without an effort set. The factory wave sets `medium`, so the
written block will be the Flash one.

## Findings

None blocking. Four test-coverage gaps and two cosmetics, all deferrable:

1. **(minor, coverage) The `skipping=0` reset arm is untested (M2 survived).**
   The fixture's `ui-onboarding:` block comes *before* `agent-default-model:`,
   so no indented line follows the block-terminating key. If the operator's
   `settings.yaml` ever grew a top-level key with children after the block, a
   regression that failed to reset the flag would silently delete those
   children and no test would notice. The shipped code is correct; only the
   coverage is thin. Today's real file has the block last, so the field is safe.

2. **(minor, coverage) The blank-line arm is untested (M5 survived).** Removing
   `'' |` from the `case` leaves all tests green, because neither the fixture nor
   the real file has a blank line inside the block. The arm is nonetheless the
   right behaviour — it matches the wrapper's own parser — so this is a missing
   fixture, not a wrong branch. A one-line fixture change (a blank line between
   `provider:` and `model:`) would close both this and the fact that a blank
   line trailing the block is silently dropped from the copy, a harmless but
   real deviation from "everything else survives byte for byte".

3. **(minor, coverage) Byte-identity of surviving lines is only half asserted
   (M6b survived).** `grep -c 'welcomeNoticeVersion: 2026-08-13.1'` is
   unanchored, so a mutation that strips the two-space indent from every
   surviving line passes. Only the top-level `^other-key: 1$` is anchored. A
   `diff` of the copy against an expected-file heredoc would assert the
   interface's actual claim.

4. **(minor, coverage) The do-not-clobber guard is untested (M9 survived).**
   `[ ! -e "$dst/settings.yaml" ]` matters on a re-seed of a home the wrapper
   has already written (it would otherwise throw away the block the wrapper just
   wrote with the right model). It is present and correct, and mirrors the
   symlink loop's `[ -e "$dst/$name" ]` idiom, but nothing pins it.

5. **(cosmetic) `printf '%s\n'` newline-terminates the copy** even if the source
   lacks a final newline. Not reachable from anything dsh writes.

6. **(cosmetic, pre-existing) `settings.yaml.bak-2026-09-04-xhigh` is symlinked
   into every seeded home.** The skip list matches exact names, and the glob is
   `"$src"/*`, so stray backups come along. dsh does not read them. Unrelated to
   P0; worth a tidy if the shared home accumulates more.

Points 1–4 are one small edit to the same bats file and would be a reasonable
follow-up task; none of them changes the shipped behaviour, and the fix's own
purpose is proven by four killed mutations plus the end-to-end dump.

## Deviations

None. The implementation is the plan's Step 3 snippet verbatim (function body,
call site, and skip-list entry); the tests are the plan's Step 1 snippet
verbatim; the Step 4 comment update was made; the commit subject is
byte-identical to the plan's and carries the required trailer; the touched files
are exactly the two the plan names. No seat was run, no host state was touched,
and the operator's shared dsh home was read but not modified.
