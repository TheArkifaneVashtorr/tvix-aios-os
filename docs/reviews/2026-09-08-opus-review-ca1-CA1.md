---
plan_defect: implementer
plan_defect_secondary: vacuous
mutants_total: 52
mutants_killed: 45
mutants_outside_named: 8
---
# Opus gate — seat run ca1, task CA1 — REJECTED

## Summary

The arm itself is right. Every interface CA1 names is present and behaves as the
section states: the three-way `FACTORY_SEAT` select, the byte-exact `codex exec`
argv, the banner window and its config fallbacks, the rollout lookup by session
id and by marker, the classifier's agent-output-only copy, the codex trailer
pair, and the usage script. 45 of 52 mutants die; the `unit` and `lint` checks
are green in the build sandbox (585 bats tests, 18 of them CA1's); the dsh arm
is untouched — `80-seat-driver.bats:94-97`'s trailer pins and all 152 tests of
`80`+`94` stay green; `ruff`, `shellcheck`, `repomap` and `tasks.py check` are
clean; the commit subject is byte-identical and the body pastes the red.

Two MAJORs stop it.

1. **Row 2's test is red on this host and it launches the real Codex.**
   `NO_CODEX=1` only omits the fake from `$BIN`; `PATH="$BIN:$PATH"` leaves the
   operator's own `/home/dalhaka/.local/bin/codex` reachable, which the plan's
   Assumption 3 records by name. `nix develop -c bats tests/unit/95-codex-arm.bats`
   — the section's own Step 4 command — fails on core, and the driver goes on to
   run `codex exec … --sandbox danger-full-access --color never -` with the brief
   on stdin. That is a real seat launch, which the plan's Global Constraints
   forbid outright.
2. **Row 8's "no `seat:` line at all" assertion cannot fail.** It is written
   `! grep -q …`, and `set -e` ignores a command whose status is inverted with
   `!`; it is not the test's last command, so its result is discarded. The
   section's own named mutant survives and writes `seat: codex ` — a `seat:` line
   with an empty id — into the `.result` that the ingest reads. The plan's Tests
   table prescribed that exact assertion, so the vacuity is the plan's.

Three named mutants survive (8t above; 6o and 14ag are ill-posed — see
## Mutants). Six MINORs follow: four contracts the section states with no test
behind them, and the two ill-posed mutants.

## Contract items

Taken literally, item by item, against `git diff b440969..758b604`.

| # | contract (CA1 §Interfaces) | met | evidence |
|---|---|---|---|
| 1 | arm select: exactly `codex`; unset/empty = today; anything else exit 2 + one stderr line, before the run dir / pid file / `factory-ws` | yes | `tools/factory/seat/factory-task:123-131`; the case block sits above `mkdir -p -- "$runs_dir"` (`:188`) and `pid_file=` (`:194`); rows 1 and 3 green, mutants 1a/1b/3d killed |
| 2 | `codex` with no `codex` on PATH refuses the same way, nothing written | code yes, **test broken** | `factory-task:128` `command -v codex >/dev/null 2>&1 \|\| factory_die 2 …`; mutant 2c dies **only** on a PATH without the host's codex — MAJOR-1 |
| 3 | `factory_route` not called; `OPENROUTER_MODEL` / `OPENROUTER_REASONING_EFFORT` ignored, one warning line each | yes | `factory-task:146-147`; row 13 asserts `grep -c … = 1` for both and no `routing table unusable` line; 13ad/13ae/13af killed |
| 4 | `route_label` = `explicit` with `--model`, else `codex/$kind/$size` | yes | `factory-task:149`; rows 4 (`route: codex/code/M`) and 5 (`route: explicit`); 4j/5m killed |
| 5 | `FACTORY_SEAT_VERSION` = last token of `codex --version`'s first line when it matches the version regex, else unset + warning | yes | `factory-task:151-157`; row 15's three `FAKE_VERSION` outputs; 15ah killed |
| 6 | `FACTORY_MODEL` (the brief's `<model>`) = `--model`, else config `model`, else `unknown` | yes | `factory-task:158-160`, `export FACTORY_MODEL=$brief_model` (`:220`); row 7's four config fixtures |
| 7 | `factory_codex_config_value`: first **top-level** `<key> = "<value>"`, stop at the first `[`, nothing on absent/unreadable/absent-key, `model_reasoning_effort` never matches `model`, exit 0 | yes | `factory-task:92-117`; row 7's profile-table and effort-first files; 7q/7r killed |
| 8 | no `DSH_HOME` under codex; no `<KEY>.dsh-home` | yes | `factory-task:204-216` guarded by `if [ "$seat_arm" != codex ]`; row 4 `[ ! -e "$FACTORY_RUNS/r1/K1.dsh-home" ]`; 4i killed |
| 9 | launch: from `cd -- "$ws"`, brief on stdin, never `--ephemeral`/`--json`, `-m` only with `--model`, argv exactly `exec -c features.plugins=false -c otel.metrics_exporter="none" --sandbox danger-full-access --color never [-m …] -`, tee'd, `exit_code` codex's | yes | `factory-task:239-252`; row 4's `grep -Fxq` on the whole argv line and `cwd=$WS`; 4e/4f/4g/4h/5l and the outside mutant O5 (`--skip-git-repo-check`) all killed; row 14 pins 124 |
| 10 | tested before `command -v seat-submit` | yes | `factory-task:238` `if [ "$seat_arm" = codex ]; then` … `:254` `elif command -v seat-submit …` |
| 11 | banner window = between the first two `--------`; `model:` / `reasoning effort:` / `session id:` read only inside it; fallbacks banner → config → `unknown`; session id only when 36 hex-and-dash | yes (regex untested) | `factory-task:320-329`; row 6's decoys and disagreeing config; 6n/6p killed, 6o survives ill-posed, the 36-char class has no fixture (MINOR-1) |
| 12 | usage: by session id, else newest-by-name newer than the marker; missing file logs and keeps `{}`; runs through `factory_py`; `events` read as today | yes | `factory-task:752-764`; rows 9, 10, 11; 9u/10v/11w killed and the outside mutant O7 (`factory_py`→`factory_python3`) killed |
| 13 | classifier's copy: skip the banner, the `user` line and `wc -l` brief lines, then the first `codex`; empty when absent; `mktemp .agent-$key.XXXXXX` (no `.log`), removed after the call | behaviour yes; two clauses untested | `factory-task:791-803`; row 12(a)(b)(c); 11x/12y/12z/12aa/12ab/12ac and the outside mutant O8 killed; the `.log`-suffix and removal clauses survive mutation (MINOR-2, MINOR-3) |
| 14 | `.result`: `seat: codex <session id>` where `seat: unit …` goes, only when the id is non-empty; everything else as today | code yes, **assertion vacuous** | `factory-task:816-817`; MAJOR-2 |
| 15 | `factory-brief`: `FACTORY_SEAT`=`codex` swaps the trailer pair; any other value or unset byte-identical; `FACTORY_SEAT_VERSION` defaults to the literal `<version>` | yes | `factory-brief:70-77,122-123`; row 17 `cmp`s the three non-codex spellings and greps the dsh pair; 17aj/17ak/17al killed |
| 16 | `factory-wave`/`factory-dispatch` unchanged, `FACTORY_SEAT` reaches every task | yes | neither file is in the diff; row 16 pins the pass-through, 16ai killed |
| 17 | `factory-codex-usage.py`: the `factory-usage.py` shape, model from the last `turn_context`, `events` = parsed objects, totals from the last non-null `token_count`, `input` net of cache, `duration_s` first→last timestamp, exit 0 always | yes | `tools/factory/seat/factory-codex-usage.py:44-101`; row 18 (a)–(d); 18am/18an/18ao/18ap/18aq/18ar and the outside mutant O1 all killed |
| 18 | README: the `FACTORY_SEAT` bullet, a `## Codex arm` section, the trailer pair with `<ver>` | yes | `tools/factory/seat/README.md:97-100`, `:559-576`, `:634-641` |

One deliberate deviation from the section's pasted code, and it is an
improvement: the script reads `sys.stdin.buffer` and decodes with `errors=
"replace"` (`factory-codex-usage.py:50-53`) instead of the plan's `for line in
sys.stdin`. I applied the plan's own version as mutant **O1** and row 18(c) —
2 000 bytes of `/dev/urandom` — exits 1 on it (`UnicodeDecodeError` from the
text-mode reader, before any `try`). The plan's snippet could not have passed
its own row 18(c); the seat noticed and closed it.

## Red before green

Base implementation files (`factory-task`, `factory-brief` from b440969,
`factory-codex-usage.py` deleted) against the branch's tests, in a scratch copy:

```
1..18
not ok 1 FACTORY_SEAT outside the rule refuses at exit 2 before a run dir or workspace
#   `[ "$status" -eq 2 ]' failed
not ok 2 FACTORY_SEAT=codex with no codex on PATH refuses at exit 2 before a run dir
ok   3 empty or unset FACTORY_SEAT keeps today's dsh arm
not ok 4 the codex launch: …            #   `grep -Fxq "$args" "$REC"' failed with status 2
not ok 5 --model is passed as -m …      not ok 6 the banner window wins …
not ok 7 trailer-time model …           not ok 8 no banner: the .result falls back …
not ok 9 usage reads the rollout named by the session id …
not ok 10 usage reads the newest rollout since the marker …
not ok 11 no rollout keeps {} …         not ok 12 the classifier sees only …
not ok 13 OPENROUTER_MODEL/REASONING_EFFORT …
not ok 14 a codex run that times out …  not ok 15 FACTORY_SEAT_VERSION …
ok   16 factory-wave passes FACTORY_SEAT through to every factory-task
not ok 17 factory-brief prints the codex trailer pair …
not ok 18 factory-codex-usage.py summarises a rollout …
#   `[ "$status" -eq 0 ]' failed
```

16 of 18 red, matching the two reds the commit body pastes (row 1's
`[ "$status" -eq 2 ]` and row 18's missing script). Rows 3 and 16 pin
behaviour the base already has — neither is vacuous: row 3's mutant 3d and row
16's mutant 16ai both kill them (below).

Green, at HEAD, on a PATH without the host's codex (the build sandbox's shape):
18/18 `ok`. Through the flake: `nix build .#checks.x86_64-linux.unit -L
--no-link --rebuild` → `ok 568`…`ok 585` and exit 0.

## Mutants

52 applied — 44 named by the section, 8 outside it. 45 killed.

**Named, killed (41):** 1a drop the `*)` arm · 1b match `codex*` · 2c drop
`command -v codex` (killed only on a codex-free PATH — MAJOR-1) · 3d treat empty
as codex · 4e `-` dropped · 4f `--ephemeral` added · 4g `--json` added · 4h `-m`
always · 4i the DSH_HOME seed kept · 4j `route_label` left `implement/…` · 4k
`seat:` omitted · 5l `-m` after `-` · 5m `route_label` kept `codex/…` · 6n the
whole-log last match · 6p the config read before the banner · 7q read the whole
file · 7r `$key*` without the `=` test · 8s skip the config fallback · 9u the
newest rollout instead of the session id · 10v drop `-newer "$marker"` · 11w
`events` defaulted to 50 · 11x / 12y the raw log handed to the classifier · 12z
the first `codex` line anywhere · 12aa copy from the first `--------` · 12ab copy
from `user` · 12ac an empty copy always · 13ad honour `OPENROUTER_MODEL` · 13ae
call `factory_route` · 13af the warning logged twice · 15ah `codex --version`
unvalidated · 16ai `env -u FACTORY_SEAT` in `factory-wave` · 17aj a
case-insensitive `FACTORY_SEAT` match · 17ak drop the `<version>` fallback · 17al
swap the trailer order · 18am `input = input_tokens` · 18an the last
`token_count` regardless of null `info` · 18ao raw lines counted · 18ap raise on
a decode error · 18aq the narrow `except (json.JSONDecodeError, ValueError)` ·
18ar first/last from `token_count` lines only.

Sample kills, verbatim:

```
12z  not ok 1 the classifier sees only the agent's output, never the brief or the banner
     # (in test file tests/unit/95-codex-arm.bats, line 466)
     #   `[[ "$output" == *"error_class: none"* ]]' failed
18aq not ok 1 factory-codex-usage.py summarises a rollout and is robust to torn and deep lines
     # (in test file tests/unit/95-codex-arm.bats, line 644)
     #   `[ "$status" -eq 0 ]' failed
18am not ok 1 … #   `[ "$output" = '{"model": "gpt-6-astra", "events": 61, "input": 68620, …}' ]' failed
```

**Named, survived (3):**

- **8t** — `factory-task:816`, `[ "$seat_arm" = codex ] && [ -n "$session_id" ]`
  → `[ "$seat_arm" = codex ]`. Row 8 stays `ok`. The `.result` it wrote under the
  mutant, captured:
  `run: r1 / key: K1 / model: cfg-model / effort: high / route: codex/code/M /
  … / seat: codex ` — the empty-id line the row exists to forbid. **MAJOR-2.**
- **6o** — the banner window widened to "first `--------` to EOF"
  (`awk '$0 == "--------" { n++; next } n >= 1 { print }'`). Row 6 stays `ok`.
  The mutant is not killable by row 6's fixture: the widened window still holds
  the banner's own `model:` line first, and the reader is `… | head -n1`, so the
  echoed decoy `model: decoy/model` never wins. The plan's mutant sentence ("a
  window from the first `--------` to EOF → the decoys win") is false; the code
  implements the section's `awk` verbatim and is correct. Plan-side — MINOR-4.
- **14ag** — `exit_code=${PIPESTATUS[0]}` → `exit_code=$?` (`factory-task:249`).
  Row 14 stays `ok`, and no test can kill it: `factory-task` runs with `set -o
  pipefail` (`:25`), so `$?` of `( … ) 2>&1 | tee -a -- "$log"` is the last
  non-zero status of the pipeline — codex's 124 — exactly what `PIPESTATUS[0]`
  holds whenever the launch is the failing member. The section's own Assumption 6
  states that equivalence. An equivalent mutant, not a hole — MINOR-5.

**Outside the named set (8 tried, 4 killed):** O1 the plan's own text-mode stdin
loop → row 18(c) exits 1 (**killed**, and it justifies the seat's deviation) ·
O5 `--skip-git-repo-check` added to the argv → row 4's `grep -Fxq` (**killed**) ·
O7 `factory_py` → `factory_python3` → rows 4/9/10 (**killed**, the sandbox seam
is pinned) · O8 `brief_lines=0` → row 12(b) (**killed**). Survivors: O2 the
class_log copy never removed (`factory-task:803`) · O3 the class_log given a
`.log` suffix (`factory-task:793`) · O4 the session id read with `tail -n1` ·
O6 the session-id regex loosened from `([0-9a-fA-F-]{36})` to `(.+)`.

## Checks

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass** — `ok 585 factory-codex-usage.py summarises a rollout …`, exit 0 |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass**, exit 0 |
| 95-codex-arm on core | `nix develop -c bats tests/unit/95-codex-arm.bats` | **FAIL** — `not ok 2 … [ "$status" -eq 2 ]' failed` (MAJOR-1) |
| 95-codex-arm, codex-free PATH | same, `~/.local/bin` dropped | pass, 18/18 |
| dsh arm | `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/94-seat-harness.bats` | pass, `1..152`, no `not ok`; the trailer pins at `80-seat-driver.bats:94-97` green |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1, on the queue block only: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. Structural, not this diff's: the hook's own comment says "a landed key leaves the queue, so staleness is by design", and at b440969 the same command exits 0. Every step before it passed. |
| ruff | `nix develop -c ruff check tools/factory/seat` / `ruff format --check` | `All checks passed!` / `3 files already formatted` |
| shellcheck | `shellcheck -x tools/factory/seat/factory-task tools/factory/seat/factory-brief` | exit 0 |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0, no drift; `repomap.py check` exit 0 |
| task graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

One flake to record, not a finding: the first combined run of `80`+`94` gave
`not ok 148 a timed-out probe reads not-run with verify-timeout` at
`94-seat-harness.bats:2118`. It passes at b440969, passes three times in
isolation at HEAD, and passes on a repeat of the combined run — a timing-
sensitive pre-existing test under load, untouched by this diff.

## Touches and commit

`git diff --stat b440969..758b604`: `docs/MAP.md` (2 lines — generator output,
exempt by rule), `tests/unit/95-codex-arm.bats` (+647), `tools/factory/seat/
README.md` (+31), `factory-brief` (+23/-4), `factory-codex-usage.py` (+105),
`factory-task` (+240/-48). Every file is inside the section's `touches` plus the
exempt `docs/MAP.md`. Nothing outside; no `Deviation:` line owed.

One commit (`git rev-list --count b440969..HEAD` → `1`). Subject `cmp`-identical
to the section's:

```
seat: the codex arm of the driver — FACTORY_SEAT=codex selects codex exec in the workspace clone, the .result from the banner and the rollout, the classifier fed the agent's output only, the codex trailers in the brief (test: unit, lint)
```

The body states the why and pastes both reds (row 1's `[ "$status" -eq 2 ]`,
row 18's `python3: can't open file '…/factory-codex-usage.py'`) — both match
what I measured. The two trailers follow a blank line, in order:
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless,
factory run ca1)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
— the dsh pair, correct for a DeepSeek seat. No board commit; the plan file is
untouched.

## Findings

### MAJOR-1 — row 2's test is red on core and reaches a real `codex exec`

`tests/unit/95-codex-arm.bats:242-250` (the assertion at `:246`), with
`run_codex_task`'s `PATH="$BIN:$PATH"` at `:222`.

`NO_CODEX=1` only skips writing the fake into `$BIN`; the rest of the inherited
PATH survives, and this host has `/home/dalhaka/.local/bin/codex` — the fact the
section's own Assumption 3 records (`command -v codex` inside the devShell →
`/home/dalhaka/.local/bin/codex`). So `command -v codex` in `factory-task:128`
succeeds, the refusal never fires, and the run continues:

```
$ nix develop -c bats tests/unit/95-codex-arm.bats
not ok 2 FACTORY_SEAT=codex with no codex on PATH refuses at exit 2 before a run dir
# (in test file tests/unit/95-codex-arm.bats, line 246)
#   `[ "$status" -eq 2 ]' failed
```

Worse than red. I put a recording shim earlier on PATH — so the real binary was
never reached a second time — and it caught what the driver goes on to do:

```
GUARD-SHIM: the driver invoked codex with argv: --version
GUARD-SHIM: the driver invoked codex with argv: exec -c features.plugins=false \
  -c otel.metrics_exporter="none" --sandbox danger-full-access --color never -
```

That is the launch of record, with the brief on stdin and the operator's rights,
from a unit test. The section's Global Constraints say it in one line: "Never
launch a seat (`tools/factory/seat/factory-task`, …, a real `codex exec`): every
driver behaviour in this plan is tested with fakes on `PATH`." The section's own
Step 4 green command is `nix develop -c bats tests/unit/95-codex-arm.bats`, so
anyone following the plan on core fires it. The fix is one line in
`run_codex_task` — scrub the ambient PATH for the `NO_CODEX=1` row (e.g.
`PATH="$BIN"` plus the coreutils dir, or filter `~/.local/bin`) — but the test as
committed cannot be run here.

### MAJOR-2 — row 8's `no seat: line` assertion cannot fail, and its mutant survives

`tests/unit/95-codex-arm.bats:381`:

```bash
  ! grep -q '^seat:' "$FACTORY_RUNS/r1/K1.result"
```

Bash's `set -e` — which is how bats fails a test body — explicitly ignores a
command "if the command's return value is being inverted with `!`", and this is
not the test's last command (the second fixture follows at `:383`), so its status
is discarded. Proven directly:

```
$ cat probe.bats
@test "negated assertion mid-test is inert" { echo hello > f; ! grep -q hello f; true; }
@test "negated assertion as the last command does fail" { echo hello > f; ! grep -q hello f; }
ok 1 negated assertion mid-test is inert
not ok 2 negated assertion as the last command does fail
```

The section's named mutant for that row — "print `seat: codex ` with an empty
id" — therefore survives. Applied to `factory-task:816`
(`[ "$seat_arm" = codex ] && [ -n "$session_id" ]` → `[ "$seat_arm" = codex ]`):

```
$ bats -f "no banner: the .result" tests/unit/95-codex-arm.bats
ok 1 no banner: the .result falls back to the config, else unknown, and no seat: line
```

while the `.result` it wrote reads:

```
model: cfg-model
effort: high
route: codex/code/M
plan: …/plan.md
workspace: …/ws
seat: codex
branch: task/K1
```

(the `seat:` line is `seat: codex ` with a trailing space). The contract "only
when `session_id` is non-empty" is unguarded by any test, and the ingest would
be handed a `seat:` line with no id. The plan's Tests table prescribed the
`! grep -q '^seat:'` form verbatim, so the vacuity is the section's — hence
`plan_defect_secondary: vacuous`. The repo's bats lint
(`tests/lint/bats-and-chain.sh`) only bans `] && [`, so nothing caught it; the
same shape exists at `60-proton-push.bats:36,39,40`,
`81-helm-open-workspace.bats:180` and `91-orchestrator-guard.bats:1545` and is
worth a separate sweep.

### MINOR-1 — the 36-character session-id rule has no fixture

`tools/factory/seat/factory-task:324` requires `([0-9a-fA-F-]{36})`. Loosening it
to `(.+)` (outside mutant O6) leaves all 18 tests `ok`: no fixture ever presents
a malformed `session id:` in the banner, so "else empty" is unexercised.

### MINOR-2 — the classifier copy's `.log`-free name is untested

`factory-task:793` uses `mktemp -p "$runs_dir" ".agent-$key.XXXXXX"`, and the
section states the reason ("no `.log` suffix, so `tasks.py`'s `*.log` glob never
sees it"). Appending `.log` to the template (outside mutant O3) leaves row 12
`ok`.

### MINOR-3 — the classifier copy's removal is untested

`factory-task:803` `[ "$class_log" = "$log" ] || rm -f -- "$class_log"`.
Replacing it with `:` (outside mutant O2) leaves row 12 `ok`; nothing asserts the
run dir is free of `.agent-K1.*` afterwards.

### MINOR-4 — row 6's second mutant sentence is false

The section names "a window from the first `--------` to EOF → the decoys win".
It does not: the reader is `sed -nE … | head -n1` (`factory-task:322-324`), so
the banner's own `model:` still comes first and row 6 stays `ok` under the
widened window. The code is correct; the mutant as written is unkillable by the
stated fixture. A discriminating fixture would need a banner without a `model:`
line and a body that has one.

### MINOR-5 — row 14's mutant is equivalent under `pipefail`

`exit_code=$?` and `exit_code=${PIPESTATUS[0]}` agree for every case the tests can
produce, because `factory-task:25` sets `pipefail` and `tee` never fails: the
pipeline's own status is already codex's non-zero. The section's Assumption 6
says exactly this, so the mutant contradicts the assumption it was drawn from.

### MINOR-6 — the marker-branch refusal message has no assertion

`factory-task:759` `factory_log "no banner and no rollout newer than the launch
marker under $codex_home/sessions"` appears in no test — `grep -c 'no banner and
no rollout' tests/unit/95-codex-arm.bats` → `0`, and the same for `usage source`
(`:762`). Row 11 pins only the by-id message; the banner-less, rollout-less path
is reachable (`FAKE_NO_BANNER=1 FAKE_NO_ROLLOUT=1`) and unexercised.

## Verdict

**REJECTED.** Two MAJORs: a unit test that is red on this host and launches the
real Codex CLI with `--sandbox danger-full-access` (MAJOR-1), and a vacuous
assertion whose named mutant survives, letting an empty-id `seat:` line into the
`.result` (MAJOR-2). Both are small edits — scrub the ambient PATH in
`run_codex_task`'s `NO_CODEX=1` path, and rewrite `:381` as
`run grep -c '^seat:' …` / `[ "$status" -ne 0 ]` (or `refute_output`) — and the
rest of the section is met and well pinned: 45 of 52 mutants dead, the two
acceptance checks green, and the dsh arm byte-for-byte intact.
