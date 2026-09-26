---
plan_defect: implementer
plan_defect_secondary: wrong-fact
mutants_total: 21
mutants_killed: 18
mutants_outside_named: 3
---
# Opus gate — seat run sh4, task SH5 — REJECTED

## Summary

Branch `task/SH5` at `31a69a3b64a05866fd9cf7c7729adf7e4177c0bd` (base
`c8a63dcdbb92130f96b53f8fce2fdd9277b0ac59`), one commit, 14 files, every file
inside the section's `touches` plus the exempt `docs/MAP.md`. The probes graph,
the `probes` subcommand, the three shell functions, the fence arm, the ingest
and the README all land, and the `le`/`eq` happy paths verify end to end.

Five MAJORs. (1) The section's own acceptance check `unit` is **red** at the
committed rev: the seat rewrapped the brief's grammar sentence and split the
phrase `no colon, no markdown` across two lines, turning three landed tests red.
The driver's `checks_verified: unit=fail` is **confirmed**, not a budget
artefact — my own `nix build .#checks.x86_64-linux.unit` reproduces the same
three `not ok` lines, and the driver's other two verdicts (`evidence-unit=pass`,
`lint=pass`) match mine exactly. (2) and (3) The `empty`/`nonempty` operators —
declared in the Interfaces, documented in the README, and the plan's own row-1
fixture — are broken twice over: the driver's tab-split collapses the empty
value column, and it then calls `factory_probe_compare` with two arguments,
which under `factory-task`'s `set -u` aborts the driver with `$3: unbound
variable` **before any `.result` is written**. (4) and (5) Two of the section's
named mutants survive: row 4b's "string compare for numbers" changes no
assertion, and row 14's "put the line into the template" changes no test
outcome anywhere in `tests/unit`.

`plan_defect: implementer` — the seat edited a sentence the plan told it to add
to, and never ran its own named mutants (Step 2/3 discipline). Secondary
`wrong-fact` — row 4b's mutant sentence ("string compare for numbers → `2.5 ≥
2` red") is false: string comparison of `2.5` against `2` yields `pass`, so the
row cannot redden on that mutant as written.

## Contract items

Every numbered item of the section, taken literally.

**Grammar / `parse_plan`.**

1. `**probes:**` block, bullets `- <name>: `<command>` :: <op>[ <value>] :: <provenance>`, block ends at the first non-`- ` line — MET. `pkgs/evidence/tasks.py:225-236` (`if in_probes:` / `if line.startswith("- "):` … `in_probes = False`), block opened at `tasks.py:270-273`.
2. `name` matches `^[a-z][a-z0-9-]{0,31}$`, unique in the section — MET. `tasks.py:152` (`re.match(r"^([a-z][a-z0-9-]{0,31}):(.*)$", body)`), duplicate at `tasks.py:231-232`.
3. `command` is the text between the first and last backtick, may not contain a tab — MET. `tasks.py:156-162`. Discriminated by the `colon-cmd` row in `tests/evidence/test_tasks.py:96-101`.
4. `op ∈ le lt ge gt eq ne empty nonempty` — MET in the parser (`tasks.py:47-51`); **violated in the driver** for `empty`/`nonempty` (MAJOR-2, MAJOR-3).
5. value required for the first six, forbidden for the last two; decimal for `le lt ge gt`; non-numeric non-space string for `eq ne` — MET. `tasks.py:167-180`.
6. `provenance` non-empty — MET. `tasks.py:165-166`.
7. `**probe_env:** NAME=VALUE …`, each token `^[A-Z_][A-Z0-9_]*=[^ ]*$` — MET. `tasks.py:45` and `tasks.py:259-266`.
8. `FIELD_RE` gains `probe_env` — MET. `tasks.py:44`.
9. every task gets `"probes": [{name,cmd,op,value,by}…]` and `"probe_env"` — MET. `tasks.py:223-225`; asserted in `tests/evidence/test_tasks.py:79-108`.

**`tasks.py check` error strings.** All six MET and all six asserted in
`tests/evidence/test_tasks.py:2339-2376`: `probes: malformed: <line>`
(`tasks.py:154`), `probes: duplicate <name>` (`tasks.py:232`), `op <op> needs a
numeric value` (`tasks.py:174`), `op <op> takes no value` (`tasks.py:170`),
`eq/ne on a number — state a bound (le, ge)` (`tasks.py:180`), `probe_env:
malformed token <tok>` (`tasks.py:263-265`); prefixed `tasks: <key> ` at
`tasks.py:1386-1387`.

**`tasks.py probes <plan> <KEY>`.** MET. `cmd_probes` at `tasks.py:309-327`;
line 1 `env\t…` (`:322`), one row per probe with the command last (`:326`), exit
0 with only the env line for a no-probe section, exit 3 `tasks: probes: no
section <KEY> in <plan>` (`:319-320`), exit 2 on an unreadable plan
(`:315-317`), reads the plan only (dispatched before `--root` resolution,
`tasks.py:1866-1867`). All four exits asserted in
`tests/evidence/test_tasks.py:201-228`.

**`factory-brief`.** The sentence lands before the template and carries no
literal `FACTORY-RESULT` (`tools/factory/seat/factory-brief:93-95`), and the
four-line template is unchanged — but the seat also **rewrapped the pre-existing
sentence** on lines 96-97, which is MAJOR-1.

**`factory-lib.sh`.**

- `factory_task_probes <plan> <KEY>` — MET. `factory-lib.sh:756-765`; the "no contract" log and the propagated status are asserted by the row-13 test.
- `factory_probe_compare <op> <bound> <value>` — MET for `le lt ge gt eq ne` (`factory-lib.sh:771-812`); **the `empty`/`nonempty` arms read the *second* argument as the value** (`:799-807`), so the function's arity differs by operator and its 3-argument signature crashes when called with two under `set -u` (MAJOR-2).
- `factory_run_probe <ws> <env-tokens> <remaining-s> <command>` — MET. `factory-lib.sh:820-843`: `cd`, `timeout --`, `env -u FACTORY_RUN`, tokens after, stderr to `$log`, last non-empty line trimmed, `head -c 200`, `tr '[:cntrl:]' ' '`, 124 on timeout else 0.

**`factory-task`.**

- `probe_lines` = `^FACTORY-PROBE[[:space:]]+<name>=` without `<`, last per name — MET. `factory-task:363`.
- probes run in the seat's workspace at the seat's rev, under the same budget — MET. `factory-task:334-405`, `remaining` derived from SH4's `verify_budget`/`verify_start` at `:350`.
- outcome precedence `not-run` > `fail` > `missing` > `drift` > `pass` — MET. `factory-task:352-378`.
- `.result` lines `probes_verified:` / `probe_values:` / `probe_env:` after `checks_scope_*` — MET. `factory-task:695-699`.
- demotion after SH4's table and after SH3's `touches` (D5) — MET. `factory-task:596-608`; each earlier arm sets `status=partial`, so the `[ "$status" = "done" ]` guard at `:603` preserves the order. Verified by mutants M13/M14.
- `factory_error_class` gains `probe-mismatch)` / `probe-missing)` — MET. `factory-lib.sh:156-163`.

**`streams.py` / `ingest_result.py` / `SCHEMA.md`.** All MET.
`streams.py:134-135` (arms after `verify-timeout`, before `none`),
`streams.py:324-332` (the 32-cap map with the five-arm enum),
`ingest_result.py:160-179` + `:346-348` (`probes_verified` ingested,
`probe_values`/`probe_env` never), `SCHEMA.md:17-20`,
`tests/evidence/test_streams_policy.py:220-224` (`ENUM_ARMS`).

**Consumers.** `probe_values` is written for the gate and is not ingested —
asserted in `tests/evidence/test_ingest_result.py:688-690`.

## Red before green

Base implementation files (`pkgs/evidence/tasks.py`, `streams.py`,
`ingest_result.py`, `tools/factory/seat/factory-{task,lib.sh,brief}`) checked
out from `c8a63dc` against the branch's tests, in
`/tmp/…/scratchpad/gate-sh4-SH5/red`.

Pytest (rows 1, 2, 3, 16, 17):

```
FAILED tests/evidence/test_tasks.py::test_parse_plan_reads_probes_and_probe_env
FAILED tests/evidence/test_tasks.py::test_probes_subcommand_unions_nothing_and_prints_tab_rows
E       assert 2 == 0
E        ... invalid choice: 'probes' (choose from 'brief', 'json', 'waves', 'conflicts', 'check', 'write-board', 'touches')
FAILED tests/evidence/test_tasks.py::test_check_reports_probe_grammar_errors
FAILED tests/evidence/test_streams_policy.py::test_probes_verified_map_and_cap
E       AssertionError: assert ['probes_veri...clared field'] == []
FAILED tests/evidence/test_ingest_result.py::test_probes_verified_ingest
```

Bats (rows 4–13), all ten red:

```
not ok 1 factory_probe_compare applies each operator to its boundary values
#   `[ "$output" = "pass" ]' failed          (exit 127, command not found)
not ok 2 factory_run_probe unsets FACTORY_RUN, applies env tokens, trims to the last line, and times out
not ok 3 factory_error_class maps probe demotions
not ok 4 a probe the seat pastes correctly verifies pass and records the values
#   `[[ "$output" == *"probes_verified: readme-bytes=pass"* ]]' failed
not ok 5 a stale pasted number against the driver's demotes to probe-mismatch
not ok 6 a probe the seat never pasted demotes to probe-missing
not ok 7 probe_env tokens apply and FACTORY_RUN is unset inside the probe
not ok 8 a timed-out probe reads not-run with verify-timeout, and D5 precedence holds
not ok 9 a failed seat keeps its own status and still records the probe verdict
not ok 10 a toolbox without the probes graph is no contract and writes no probe lines
```

Row 14 (`--filter 'FACTORY-PROBE line inside the RULES'`) on the base brief:

```
not ok 1 factory-brief names the FACTORY-PROBE line inside the RULES bullet and keeps the four-line template
#   `[[ "$output" == *"FACTORY-PROBE <name>=<value>"* ]]' failed
```

Every named row is genuinely red before the change. Restored, all seventeen
rows are green (`nix develop -c bats tests/unit/94-seat-harness.bats --filter
probe` → 10 ok; `pytest tests/evidence -q` → all pass inside `evidence-unit`).
No vacuous test among the section's own rows — but see MAJOR-4 and MAJOR-5 for
two rows whose *named mutants* they cannot kill.

## Mutants

21 applied in a scratch copy (`/tmp/…/scratchpad/gate-sh4-SH5/mut`), each
reverted with `git checkout --` afterwards. 18 named by the section, 3 outside
it. **16 of the 18 named mutants killed; 2 survive.**

| # | row | mutant | verdict | evidence |
|---|---|---|---|---|
| M1 | 1a | split the line on `::` before extracting the command | killed | `FAILED test_parse_plan_reads_probes_and_probe_env` (`test_tasks.py:87`) |
| M2 | 1b | strip the bullets from `body` | killed | `FAILED test_parse_plan_reads_probes_and_probe_env` (`test_tasks.py:111`) |
| M3 | 2a | allow `eq` on a number | killed | `FAILED test_check_reports_probe_grammar_errors` (`test_tasks.py:2374`) |
| M4 | 2b | accept any `probe_env` token | killed | `FAILED test_check_reports_probe_grammar_errors` (`test_tasks.py:2375`) |
| M5 | 3 | put the command first in the `probes` output | killed | `FAILED test_probes_subcommand_…` (`test_tasks.py:218`) |
| M6 | 4a | `<` for `<=` in the `le` arm | killed | `not ok 1 factory_probe_compare …` line 1847 |
| M7 | 4b | string compare for numbers | **SURVIVES** | see MAJOR-4 |
| M8 | 5a/10 | drop `env -u FACTORY_RUN` | killed | `not ok 1 factory_run_probe …` line 1876; `not ok 2 probe_env tokens apply …` line 2072 |
| M9 | 5b | first line instead of last | killed | `not ok 1 factory_run_probe …` line 1881 |
| M10 | 7 | trust the seat's value | killed | `not ok 1 a stale pasted number …` line 1953 |
| M11 | 8 | pass on the driver's value alone | killed | `not ok 1 a probe the seat never pasted …` line 1984 |
| M12 | 9 | demote drift | killed | `not ok 1 a drifted paste is recorded …` line 2015 |
| M13 | 11 | let a probe demotion outrank the earlier D5 arms | killed | `not ok 1 … D5 precedence holds` line 2130 |
| M14 | 12 | demote every status | killed | `not ok 1 a failed seat keeps its own status …` line 2193 |
| M15 | 13 | write `probes_verified:` with no contract | killed | `not ok 1 a toolbox without the probes graph …` line 2252 |
| M16 | 14 | put the `FACTORY-PROBE` line into the template | **SURVIVES** | see MAJOR-5 |
| M17 | 16 | reuse the 64-cap checks map | killed | `FAILED test_probes_verified_map_and_cap` (`test_streams_policy.py:669`) |
| M18 | 17 | store `probe_values` in the ingested row | killed | `FAILED test_probes_verified_ingest` — `probe_values: undeclared field` |
| O1 | — | ingest returns a partial map instead of `None` on a bad verdict | killed | `FAILED test_probes_verified_ingest` (`test_ingest_result.py:703`) |
| O2 | — | drop `grep -v '<'` from the `FACTORY-PROBE` extraction | **survives** | no test changes outcome (MINOR-8) |
| O3 | — | `remaining -lt 1` → `-lt 0` | killed | `not ok 8 a timed-out probe reads not-run …` |

## Checks

Every command run from a fresh clone of `task/SH5` at
`/tmp/…/scratchpad/gate-sh4-SH5/gate-sh4-SH5`, inside the devShell,
`XDG_CACHE_HOME` under the scratchpad.

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link` | **FAIL (exit 1)** — 3 `not ok` (MAJOR-1) |
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | pass (exit 0) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass (exit 0) |
| `nix develop -c githooks/pre-commit` | exit 1 — only `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the single-line delta is inside `<!-- tasks:begin -->…<!-- tasks:end -->` (SH5 moving from queued to landed, plus CA1–CA3 from a plan that landed on main after the base). The block is exempt by the plan's Global Constraints and the hook rewrites it; not an SH5 defect. |
| `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| `python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | clean (exit 0) |
| `python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

`--rebuild` is not usable here: the derivation was not previously built in this
store, so `nix build … --rebuild` errors with *"some outputs … are not valid, so
checking is not possible"*. The plain build performed a real build and is the
evidence above.

The `unit` failure, verbatim from the build log:

```
not ok 224 factory-brief quotes the exact FACTORY-RESULT grammar in its WORKSPACE RULES summary
# (in test file tests/unit/80-seat-driver.bats, line 2537)
#   `[[ "$output" == *"no colon, no markdown"* ]]' failed
not ok 225 factory-brief states the grammar in prose before the template, without the literal label
# (in test file tests/unit/80-seat-driver.bats, line 2552)
#   `[[ "$output" == *"no colon, no markdown"* ]]' failed
not ok 503 factory-brief's re-print sentence does not carry the literal label or repeat the phrase
# (in test file tests/unit/94-seat-harness.bats, line 235)
#   `[ "$output" = "1" ]' failed
```

The driver's `.result` line `checks_verified: unit=fail evidence-unit=pass
lint=pass` with `verify_s: 122` is **confirmed on all three names**. This is not
a budget artefact: the driver's three verdicts equal mine, and the `unit`
failure is a deterministic assertion failure, not a timeout.

## Touches and commit

The 14-file diff against the section's `touches`:

| file | in `touches` |
|---|---|
| `pkgs/evidence/SCHEMA.md` | yes |
| `pkgs/evidence/ingest_result.py` | yes |
| `pkgs/evidence/streams.py` | yes |
| `pkgs/evidence/tasks.py` | yes |
| `tests/evidence/fixtures/results/probes.result` | yes |
| `tests/evidence/test_ingest_result.py` | yes |
| `tests/evidence/test_streams_policy.py` | yes |
| `tests/evidence/test_tasks.py` | yes |
| `tests/unit/94-seat-harness.bats` | yes |
| `tools/factory/seat/README.md` | yes |
| `tools/factory/seat/factory-brief` | yes |
| `tools/factory/seat/factory-lib.sh` | yes |
| `tools/factory/seat/factory-task` | yes |
| `docs/MAP.md` | exempt by rule; also disclosed in the body |

No file outside the contract. `docs/OPERATIONS.md` untouched; the plan file
untouched; no board commit.

Commit: exactly one, `31a69a3`. Subject byte-identical to the section's (209
bytes, compared programmatically — `MATCH True`). The two trailers follow a
blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sh4)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

The body states the why and pastes the reds. Its closing sentence — *"all are
green now"* — is false: `unit` is red at this rev (MINOR-9).

## Findings

### MAJOR-1 — the acceptance check `unit` is red: the brief rewrap splits `no colon, no markdown`

`tools/factory/seat/factory-brief:96-97`.

The section told the seat to add one sentence *before* "The first line is
exactly the result line". The seat instead re-flowed the whole paragraph, so the
phrase three landed tests pin is no longer contiguous:

base (`git show c8a63dc:tools/factory/seat/factory-brief`)
```
  its own line and nothing after it. The first line is exactly the result
  line, one space, status=done|partial|failed — no colon, no markdown; any
  other spelling is recorded as failed:
```

head (`factory-brief:93-97`)
```
  its own line and nothing after it. Before those four lines, print one line
  `FACTORY-PROBE <name>=<value>` per probe the task section names (none when
  it names none), the value being your own run's last output line. The first
  line is exactly the result line, one space, status=done|partial|failed — no
  colon, no markdown; any other spelling is recorded as failed:
```

`tests/unit/80-seat-driver.bats:2537` and `:2552` assert `[[ "$output" ==
*"no colon, no markdown"* ]]`; `tests/unit/94-seat-harness.bats:235` asserts
`grep -c 'no colon, no markdown'` equals `1`. All three go red (build log
pasted under ## Checks). `nix build .#checks.x86_64-linux.unit` exits 1.

### MAJOR-2 — an `empty`/`nonempty` probe aborts the driver with `$3: unbound variable` and writes no `.result` at all

`tools/factory/seat/factory-task:367` calls `factory_probe_compare "$pop"
"$pdiver"` with two arguments; `tools/factory/seat/factory-lib.sh:772` is
`local op=$1 bound=$2 value=$3 verdict`, and `factory-task:25` is `set -euo
pipefail`. The unbound `$3` kills the driver mid-verification.

Reproduced end to end with a scratch bats case using the plan's own `empty`
shape (the case was reverted; `git status --porcelain` clean afterwards):

```
# TASK-RC=1
# TASK-OUT-BEGIN
# factory-task: seat exited 0 after 0s
# …/seat/factory-lib.sh: line 772: $3: unbound variable
# TASK-OUT-END
# RESULT-FILE-BEGIN
# cat: …/factory/runs/r1/K1.result: No such file or directory
# RESULT-FILE-END
```

The run loses its `.result` entirely — no status, no checks, no telemetry row —
for any section that uses an operator the Interfaces declare, the README
documents (`tools/factory/seat/README.md:384-386`) and the plan's own row-1
fixture uses (`- checks-current: … :: empty :: the lint gate`). `factory_probe_compare
empty ''` is green in isolation only because `tests/unit/94-seat-harness.bats:1860`
sources the library under a shell with no `set -u`; no test drives an
`empty`/`nonempty` probe through `factory-task`.

### MAJOR-3 — the driver's tab-split collapses the empty value column, so an `empty`/`nonempty` probe's command is lost

`tools/factory/seat/factory-task:348`: `while IFS=$'\t' read -r pname pop pvalue
pby pcmd`. Tab is IFS whitespace, so bash collapses a run of tabs into one
delimiter and the empty `<value>` column disappears.

`pkgs/evidence/tasks.py:326` emits exactly that shape for a no-value op —
verified against the real subcommand (`cat -A`):

```
env^I$
dirt^Iempty^I^Ithe lint gate^Igit status --porcelain docs/MAP.md$
```

Fed to the driver's own read:

```
$ printf 'dirt\tempty\t\tthe lint gate\tgit status --porcelain docs/MAP.md\n' \
    | { IFS=$'\t' read -r pname pop pvalue pby pcmd; … }
pname=[dirt]
pop=[empty]
pvalue=[the lint gate]
pby=[git status --porcelain docs/MAP.md]
pcmd=[]
```

The command is empty and the provenance has become the bound. Were MAJOR-2
fixed, the probe would run the empty string, measure nothing, and record `pass`
unconditionally — a probe that can never fail. This is precisely the shape the
spec's change 5 forbids (a probe that short-circuits under the driver's
environment). Untested: no bats row drives `empty`/`nonempty` through the driver.

### MAJOR-4 — the section's named mutant for row 4b survives

`tools/factory/seat/factory-lib.sh:777-785`; assertions
`tests/unit/94-seat-harness.bats:1844-1866`.

The section names the mutant "string compare for numbers → `2.5 ≥ 2` red". I
replaced the whole `awk` numeric block with string comparisons (`[ "$value" \>
"$bound" ]` etc.) and the row stayed green:

```
1..1
ok 1 factory_probe_compare applies each operator to its boundary values
```

The mutant is genuinely wrong — with it,

```
le 100 99 -> fail          (must be pass)
ge 2 2.5 -> pass           (the plan predicted red)
le 8000 8000 -> pass
```

— but every fixture in the row (`7999/8000/8001`, `5/5`, `2/2.5`, `2/abc`)
happens to agree with a lexicographic compare, because no pair mixes digit
counts in the direction that discriminates. The row has no fixture that can
redden on the mutant its own table names. (A `le 100 99` row would kill it.)

### MAJOR-5 — the section's named mutant for row 14 survives and changes no test outcome anywhere

`tests/unit/94-seat-harness.bats:2262-2273`.

The section names "put the line into the template → SH2 row 6 red". I moved
`FACTORY-PROBE <name>=<value>` out of the prose and into the template block,
directly above `FACTORY-RESULT status=<done|partial|failed>`. Row 14 stayed
green: its `probe_pos < result_pos` assertion is still satisfied (the line is
still above the result line), and its `template_lines` regex at
`94-seat-harness.bats:2271` counts only the four known lines, so the count stays
`4`. SH2's own re-print test (`:220-221`) counts the same four and is likewise
unmoved.

Failure-set diff over `tests/unit/94-seat-harness.bats tests/unit/80-seat-driver.bats`,
clean HEAD vs the mutant:

```
$ diff base-fails.txt m16-fails.txt ; echo "DIFF=$?"
DIFF=0
```

Both runs fail exactly the same three tests (the MAJOR-1 ones) and no others.
The mutant is invisible to the whole suite.

## Findings — MINOR

- **MINOR-1** — `pkgs/evidence/tasks.py:152`: the probe-name pattern refuses an uppercase, leading-digit or over-length name, but `tests/evidence/test_tasks.py:2339-2376` has no such fixture. (Plan judgement 2026-09-07-seat-harness.md erratum 3, unaddressed.)
- **MINOR-2** — `tools/factory/seat/factory-lib.sh:838-842`: "the command's own exit status is not the verdict — the value is" has no test; no row runs a command that exits non-zero while printing a passing value. (Judgement erratum 10, unaddressed.)
- **MINOR-3** — `tools/factory/seat/factory-lib.sh:789-807`: the true arms of `ne` (unequal → `pass`) and `nonempty` (non-empty → `pass`) are never asserted; `94-seat-harness.bats:1858-1866` tests only their false arms.
- **MINOR-4** — `tools/factory/seat/factory-task:379-380`: the stated "values with spaces replaced by `_`" folding in `probe_values` has no fixture with a space in a value.
- **MINOR-5** — `tools/factory/seat/factory-task:363`: "the last per name" is unasserted; no fixture pastes two `FACTORY-PROBE` lines for one name.
- **MINOR-6** — `tools/factory/seat/factory-task:359-362`: the driver's own 124 arm (`prc -eq 124` → `not-run` plus `verify_flag=timeout`) is unreachable in the tests. Under `FACTORY_VERIFY_TIMEOUT=1` the checks consume the budget first, so the `remaining -lt 1` branch at `:352` fires and `sleep 60` never runs — proven by mutant O3, which reddens that row by touching only the `-lt 1` guard.
- **MINOR-7** — `tools/factory/seat/factory-task:390-394`: the `else any missing → probe-missing` arm is never exercised with a `fail` and a `missing` firing together; no fixture pins that `fail` wins.
- **MINOR-8** — `tools/factory/seat/factory-task:363`: removing `grep -v '<'` from the seat-value extraction changes no test outcome (mutant O2). The guard that keeps a brief's `FACTORY-PROBE <name>=<value>` literal from being read as a seat value is unpinned.
- **MINOR-9** — commit body: *"all are green now"* is false for `unit` at this rev; the body pastes reds but no green run.
- **MINOR-10** — commit body: `Deviation: docs/MAP.md — repomap regenerated`. `docs/MAP.md` is exempt by the Global Constraints, so the line is unnecessary; harmless, recorded only because the driver's `touches` arm counts it as disclosed rather than exempt.

## Verdict

**REJECTED.** Five MAJORs: the section's own `unit` acceptance check is red at
the committed rev (a landed-test regression the seat introduced by rewrapping a
sentence it was told to add to); the `empty`/`nonempty` operators — declared,
documented, and used by the plan's own fixture — abort the driver under `set -u`
and destroy the run's `.result`, and their contract row is misparsed even before
that; and two of the section's own named mutants survive, one because its
predicted red is a wrong fact and one because it is invisible to the entire
suite.

`plan_defect: implementer` (the brief regression and the untested
`empty`/`nonempty` path are the seat's; Step 2/3's mutant discipline was not
run), `plan_defect_secondary: wrong-fact` (row 4b's mutant sentence is false as
written — string comparison of `2.5` against `2` yields `pass`, not the red the
plan predicts).

Owed on the re-plan: restore the base's line-wrapping in `factory-brief` (insert
the new sentence without touching the pinned phrase); give `factory_probe_compare`
one arity (or pass the measured value in the third position for every operator)
and add an end-to-end `empty` row through `factory-task`; emit the `probes`
rows with a delimiter that survives an empty column, or read them with a split
that does not collapse (e.g. `IFS=$'\t' read -r … ` replaced by a per-field
parse, or a sentinel in the value column); replace row 4b's mutant sentence with
a `le 100 99` fixture; and give row 14 an assertion that a template line count
of five, or a `FACTORY-PROBE` line at column 0, is red.
