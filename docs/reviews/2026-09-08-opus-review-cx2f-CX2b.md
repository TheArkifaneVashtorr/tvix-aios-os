---
plan_defect: none
mutants_total: 10
mutants_killed: 9
mutants_outside_named: 2
---
# Opus gate — seat run cx2f, task CX2b — APPROVED

## Summary

Branch `task/CX2b` in a fresh clone of `/home/dalhaka/factory/ws/cx2f/CX2b`
(base `a58b3aa` of the separate flake `~/flakes/codex`, head `68411f7`).
One commit, seven files, all inside the section's `touches`. Every one of the
eight numbered contract items is met literally. All five acceptance checks are
green with `--rebuild` in the clone, `nix flake check -L` ends `all checks
passed!`, and the flake's own `githooks/pre-commit` exits 0.

Nine of ten mutants die. The one survivor is the `-x` of `tests/map.sh`'s
membership grep, which cannot fire against the repository's own file set (no
tracked path is a substring of another) — it is a carried X1 detail the seat was
never shown, and the assertion it belongs to is independently killed twice. That
is MINOR-1, not a MAJOR.

The headline claim of the section — that CX1b's MINOR-5 mutant M3b now dies at
runtime rather than only in `module-eval` — is confirmed: with
`features.plugins = lib.mkDefault true` in the module, `config-precedence`
exits 1 on `plugins ... stable ... true`. It was green with that mutant before.

## Contract items

| # | item | verdict | evidence |
|---|---|---|---|
| 1 | No check dials `api.openai.com`; a loopback `loop` provider in each script's fresh user config; `provider: loop` and the absent host asserted; `test "$status" -ne 0` stays; typo mode keeps the unknown-field assertion | MET | `tests/config.sh:11-14` writes `model_provider = "loop"` + the managed bytes + `[model_providers.loop] name/base_url = "http://127.0.0.1:9"/wire_api = "responses"`; `tests/config.sh:25` `if grep -Fq 'api.openai.com' … exit 1`, `:26` `test "$status" -ne 0`, `:36` `grep -q '^provider: loop'` (valid mode), `:31` the typo assertion. `tests/precedence.sh:15-18` the same provider block, `:33` the host assertion, `:34` the status assertion, `:35` `grep -q '^provider: loop'` (both modes), `:46` the host assertion on the features probe. Build log: `codex-config-valid> provider: loop` / `ERROR: Reconnecting... waiting for network`, zero `api.openai.com` lines. |
| 2 | `features.plugins` precedence at runtime; the pinned `plugins` line; the user-mode negative control printing `true` | MET | `tests/precedence.sh:51` `grep -Fx -- 'plugins<34sp>stable<13sp>false'` (managed), `:48` the same line ending `true` (user); `flake.nix:101` re-greps the `true` line out of the user report. Green log: `plugins                                  stable             false` (managed, line 154 of the build log) and `… true` (user, lines 306-308). The literal is byte-identical to the plan's own literal (34 spaces / 13 spaces; the section's prose "33 spaces" miscounts its own string — see Findings note). |
| 3 | `network_access` precedence with VALID values only; no bogus type, no `[otel]` in the user config; managed vs user observations | MET | `tests/precedence.sh:15-18` writes only `network_access = true` and `plugins = true` beside the provider block — no bogus-typed value, no `[otel]` table. `:36` no `Error loading config.toml`, `:37` `^model:`, `:38` `^sandbox: workspace-write`, `:54` no `network access enabled`; `:49` user mode requires `network access enabled`. `flake.nix:96-99` runs the inverted control and then proves the failure was the right one (`grep -F 'network access enabled'`, `grep -q '^provider: loop'`, no `api.openai.com`). Green log line 162: `sandbox: workspace-write [workdir, /tmp, $TMPDIR] (network access enabled)` in user mode only. |
| 4 | The otel gap documented in one sentence each; nothing claims a runtime proof | MET | `README.md:56-58` "OTel precedence is asserted only by Nix `module-eval`; no CLI runtime observable exposes those exporter values." `docs/VALIDATION.md:135-140` fact 3, with `invalid type: unit variant, expected struct variant`. `grep -in otel README.md` returns only that bullet and the pre-existing defaults sentence at `:36`; no runtime claim anywhere. |
| 5 | X1 (MAP currency) and X3 (skip arm, negative control, `pkgs.util-linux`) carried unchanged | MET | `tests/map.sh` (new, 29 lines) is byte-for-byte the plan's Interfaces block plus a `# shellcheck disable=SC2016` pair; `flake.nix:73-76` the `map` check; `flake.nix:82-85` `pkgs.util-linux`; `flake.nix:88-92` the fake-`unshare` skip arm; `tests/precedence.sh:7-10` the probe. Their reds re-pasted in the commit body and in `docs/VALIDATION.md:167-215`. |
| 6 | The trust write: fresh user config per run, never asserted on afterwards, said in a comment above the `printf` | MET | `tests/config.sh:10` and `tests/precedence.sh:14`, identical: `# Fresh per run: exec may append project trust; never compare bytes after it.` No assertion in either script reads `$work_dir/codex/config.toml` after the run — every post-run grep targets `$work_dir/report` or `$work_dir/features` (`config.sh:25,31,32,34,35,36`; `precedence.sh:33,35,36,37,38,46,48,49,51,54`). |
| 7 | `docs/VALIDATION.md` "CX2b: measured mechanisms" — the four corrected facts, the reds of items 1–3, the M3b red, the greens | MET | `docs/VALIDATION.md:105-307`: the four facts at `:112-146`, X1 at `:167-200`, X3 at `:202-215`, X2 at `:217-231`, X4/X5 at `:233-283`, the greens at `:296-307`. No "partial, assumptions falsified" text remains (`grep` returns nothing). |
| 8 | One commit, the stated subject, the two trailers after a blank line, every check green before the commit | MET | `git rev-list --count a58b3aa..HEAD` → `1`; `cmp` of `git log -1 --format=%s` against the section's subject → identical; `git log -1 --format=%B | tail -4 | cat -A` shows a blank line then `Generated-By: codex-cli 0.153.4 / gpt-6-astra (codex exec, factory run cx2f)$` and `Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>$`. `./githooks/pre-commit` → exit 0. |

## Red before green

Every red the section's Step 2 names was reproduced independently in a scratch
copy of the branch, and the green restored.

**X1 — MAP currency (base map against the branch's check):**

```
$ git checkout a58b3aa -- docs/MAP.md
$ nix build .#checks.x86_64-linux.map -L --no-link          # EXIT=1
codex-map> map: missing from docs/MAP.md: .gitignore
codex-map> map: missing from docs/MAP.md: README.md
codex-map> map: missing from docs/MAP.md: docs/MAP.md
codex-map> map: missing from docs/MAP.md: tests/map.sh
       Reason: builder failed with exit code 1.
$ git checkout HEAD -- docs/MAP.md
$ nix build .#checks.x86_64-linux.map -L --no-link          # EXIT=0
```

Byte-identical to the four lines the commit body pastes.

**X3 — the skip arm (the probe removed from `tests/precedence.sh:7-10`):**

```
$ sed -i '7,10d' tests/precedence.sh
$ nix build .#checks.x86_64-linux.config-precedence -L --no-link   # EXIT=1
error: Cannot build '/nix/store/dqmcc8ij70c2rssx0r44kpk1lky5mp5r-codex-config-precedence.drv'.
       Reason: builder failed with exit code 1.
```

The `grep -F 'config-precedence: skipped'` of `flake.nix:91-92` finds nothing.
Restored, the same build prints at log line 2:
`config-precedence: skipped — unprivileged user namespaces unavailable (unshare -Ur true failed)`.

**Item 1 — the provider lines absent (this is CX2's state, the section's Step 2 red):**

```
$ nix build .#checks.x86_64-linux.config -L --no-link       # EXIT=1
codex-config-valid> provider: openai
codex-config-valid> 2026-09-08T08:49:12.541204Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: IO error: failed to lookup address information: Try again, url: wss://api.openai.com/v1/responses
       Reason: builder failed with exit code 1.
```

Restored: `provider: loop`, exit 0, zero `api.openai.com` lines.

**Item 2 — the managed `[features]` deleted:** red on `plugins … true` (below).
**Item 3 — the managed `network_access` deleted:** red on `network access enabled` (below).

**Vacuity guard.** `config-precedence` would pass trivially if `unshare -Ur true`
failed in the builder. It does not on this host: the green build log carries all
three arms — the skip line (log line 2), the managed run
(`provider: loop`, `sandbox: workspace-write [workdir, /tmp, $TMPDIR]`,
`plugins … false`), and the user run (`… (network access enabled)`,
`plugins … true`) — 309 log lines. The check is not skipping.

## Mutants

`mutants_total: 10` · `mutants_killed: 9` · `mutants_outside_named: 2`.
All applied in `…/scratchpad/gate/mut`, a copy of the clone, and reverted
(`git status --porcelain` empty after each).

| # | mutant | test | result | failing evidence |
|---|--------|------|--------|------------------|
| 1 | the four provider lines dropped from `tests/config.sh`'s user config | `config` | KILLED | `provider: openai` … `url: wss://api.openai.com/v1/responses`; `Reason: builder failed with exit code 1.` |
| 2 | `features.plugins = lib.mkDefault false` deleted from `nixosModules/default.nix:27` | `config-precedence` | KILLED | managed run printed `plugins                                  stable             true`; exit 1 |
| 3 | `sandbox_workspace_write.network_access = lib.mkDefault false` deleted (`:33`) | `config-precedence` | KILLED | managed run printed `sandbox: workspace-write [workdir, /tmp, $TMPDIR] (network access enabled)`; exit 1 |
| 4 | the skip probe dropped (`tests/precedence.sh:7-10`) | `config-precedence` | KILLED | the skip-message grep found nothing; exit 1 |
| 5 | `exit 1` on the skip path (`tests/precedence.sh:9`) | `config-precedence` | KILLED | the reason printed and the `pipefail` pipeline exited 1 |
| 6 | the `- \`README.md\`:` line deleted from `docs/MAP.md` | `map` | KILLED | `map: missing from docs/MAP.md: README.md` |
| 7 | a ghost entry `- \`ghost.sh\`: not a file.` appended | `map` | KILLED | `map: not in tree: ghost.sh` |
| 8 | `-x` dropped from `tests/map.sh:17` (`grep -qxF` → `grep -qF`) | `map` | **SURVIVED** | `map` exit 0 on the unmodified tree — see MINOR-1 |
| 9 | *(outside named)* `features.plugins = lib.mkDefault true` — CX1b's M3b verbatim | `config-precedence` | KILLED | `plugins                                  stable             true`; exit 1. This mutant left `config-precedence` **green** at CX1b (its MINOR-5); it now dies at runtime. |
| 10 | *(outside named)* the provider lines dropped from `tests/precedence.sh`'s user config | `config-precedence` | KILLED | `provider: openai` … `url: wss://api.openai.com/v1/responses`; exit 1 |

Mutant 8, isolated: with an unlisted tree file `tests/config.s` added (a strict
prefix of the listed `tests/map.sh`-style path `tests/config.sh`), `map` is
**green** with `-x` dropped and **red** with `-x` present
(`map: missing from docs/MAP.md: tests/config.s`). So `-x` is load-bearing in
principle; it simply has nothing to bite on in this repository.

## Checks

Run inside the clone, `git config core.hooksPath githooks` set:

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.map -L --no-link --rebuild` | exit 0 |
| `nix build .#checks.x86_64-linux.config -L --no-link --rebuild` | exit 0 — `provider: loop`, `ERROR: Reconnecting... waiting for network`, no `api.openai.com` |
| `nix build .#checks.x86_64-linux.config-rejects-typo -L --no-link --rebuild` | exit 0 — ``unknown configuration field `sandbox_workspace_write.network_acess` ``, no banner, no `api.openai.com` |
| `nix build .#checks.x86_64-linux.config-precedence -L --no-link --rebuild` | exit 0 — all three arms ran (see Red before green) |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | exit 0 — `traversed 16 files` / `formatted 15 files (0 changed)` |
| `nix flake check -L` | exit 0 — `all checks passed!` |
| `./githooks/pre-commit` (`nix fmt -- --fail-on-change`; `nix flake check`) | exit 0; tree clean afterwards |

`repomap.py`, `tasks.py check`, `ruff` and nixos-agent-env's `githooks/pre-commit`
do not apply: this branch is the separate `~/flakes/codex` repository. `docs/MAP.md`
currency is proven by the branch's own `map` check, verified red on the base map
and on both a deleted and a ghost entry.

## Touches and commit

Diff `a58b3aa..68411f7` — 7 files, 314 insertions, 9 deletions:
`README.md`, `docs/MAP.md`, `docs/VALIDATION.md`, `flake.nix`, `tests/config.sh`,
`tests/map.sh`, `tests/precedence.sh`. The section's list is
`tests/map.sh, flake.nix, tests/config.sh, tests/precedence.sh, docs/MAP.md,
README.md, docs/VALIDATION.md` — every file is inside it, none outside, no
`Deviation:` line needed and none present.

Commit: exactly one (`git rev-list --count` → 1). Subject `cmp`-identical to the
section's. Body states the why, pastes X1's and X3's carried reds, item 1's red
(`url: wss://api.openai.com/v1/responses`), item 2's red
(`plugins … stable … true`), item 3's red (`… (network access enabled)`), the
greens, and a proxy-gap paragraph. Trailers on their own lines after a blank
line. No board commit; the plan file lives in nixos-agent-env and is untouched;
`nixosModules/default.nix`, `pkgs/codex/default.nix` and `flake.lock` are
unchanged (mutated only in the scratch copy, reverted).

## Interfaces and error contracts

- `tests/map.sh <source-root>`: all three arms exercised — `map: missing from
  docs/MAP.md: <path>` (mutants 6 and 8-with-fixture), `map: not in tree: <path>`
  (mutant 7), and `map: no docs/MAP.md` (the seat's script-level red, pasted at
  `docs/VALIDATION.md:191`). Exit 1 on any.
- `tests/precedence.sh` mode enum: `managed` (default) and `user` — both arms run
  in the green build; the fake-`unshare` refusal path is the third arm. There is
  no fourth arm and no unknown-mode branch (an unknown third argument falls into
  the `managed`-style path; the plan specifies no refusal for it, and nothing
  passes one).
- `tests/config.sh` mode enum: `valid` and `typo` — both are acceptance checks.
- The refusal path `config-precedence: skipped — …` is exercised by
  `flake.nix:88-92` and is proven falsifiable by mutants 4 and 5.
- The negative control at `flake.nix:95-103` is guarded by a real `unshare -Ur
  true` so that a namespace-less builder does not turn the skip arm into a
  failure. This is one line beyond the plan's pinned snippet; it is a correctness
  requirement of combining X3's skip with X4's inversion, and it is disclosed in
  `docs/VALIDATION.md:277-280`.

## Findings

**MINOR-1 — `tests/map.sh:17`: the `-x` of the membership grep is not
discriminated by any landed fixture.**
`grep -qxF -- "$f" <<<"$map_list"`. Dropping `-x` leaves `map` green
(`EXIT=0`) because no tracked path is a substring of another. With an unlisted
`tests/config.s` in the tree the difference appears:

```
-x dropped, fixture present:  nix build .#checks…map  → EXIT=0   (false pass)
-x present,  fixture present:  nix build .#checks…map  → EXIT=1
                               map: missing from docs/MAP.md: tests/config.s
```

Why this is a MINOR and not a MAJOR: the mutant is named only in the plan's
**CX2** X1 row ("drop `LC_ALL=C` and `-x` → a prefix (`tests/config.s`) passes"),
which the CX2b seat never saw — its section says only "X1 … carried unchanged".
The assertion the `-x` belongs to is independently killed twice (mutants 6 and 7),
and the `map` check's only fixture is the repository itself, so killing this
mutant would require either a junk file in the tree or a fixture arm the plan's
pinned `map` snippet does not contain. The seat's own
`docs/VALIDATION.md:196-200` claim that "the prefix fixture distinguishes exact
membership from substring matching" is **not** demonstrated by the fixture it
pastes (a MAP entry `tests/config.s` against a tree file `tests/config.sh` is red
with or without `-x`); the discrimination runs the other way, as shown above.
For the orchestrator: if MAP currency should stay mutation-tight, X1's mutant
row needs a fixture arm inside the `map` runCommand, which is a plan edit, not a
seat failure.

**MINOR-2 — `docs/VALIDATION.md:112-146`: the four corrected Assumption-8 facts
are attributed, not re-measured, and their commands are elided.**
Item 7 asks for "each with the command and the line it printed"; the section
records `OPENAI_BASE_URL=http://127.0.0.1:9 codex exec …` and
`bwrap … codex features list` with ellipses, and states at `:148-151` that "the
ellipses above denote the orchestrator's supplied command summaries, not commands
re-executed on the host in CX2b". This is the correct behaviour under Global
Constraints (a seat may not run a real `codex exec`), and the seat disclosed it
rather than fabricating commands; recorded so the ledger carries the exactness
gap, not as a defect.

**Note (no finding) — the section's prose "33 spaces after `plugins`" is an
off-by-one against its own literal.** The plan's literal string at
`docs/superpowers/plans/2026-09-08-codex-driver-arm.md:999` has 34 spaces after
`plugins` and 13 after `stable`; `tests/precedence.sh:48,51` and `flake.nix:101`
carry 34/13, matching both the plan's literal and the CLI's real output
(`plugins                                  stable             false` in the green
build log). Nothing to fix in the branch; the prose counter is wrong.

No MAJOR findings.

## Verdict

**APPROVED.** Eight of eight contract items met literally; five of five
acceptance checks green with `--rebuild`, `nix flake check -L` green, the flake's
pre-commit hook green; every named red reproduced independently; nine of ten
mutants killed, including CX1b's M3b at runtime, which was the point of the
round. The single survivor is a carried X1 detail outside the section the seat
was given and cannot fire against this repository's file set. One commit, correct
subject and trailers, no file outside `touches`.
