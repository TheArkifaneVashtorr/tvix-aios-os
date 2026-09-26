---
plan_defect: none
plan_defect_secondary: wrong-fact
mutants_total: 9
mutants_killed: 8
mutants_outside_named: 3
---
# Opus gate — seat run sh4f, task SH5b — APPROVED

## Summary

Branch `task/SH5b` at `66981d4dea7d4814c9d28e314ddffe2914ed61a2` (base
`27556aa53c1a80e762e1911d37a7f93acfeb710e`), one commit, 14 files, every file
inside the section's `touches` plus the exempt `docs/MAP.md`. The diff against
base carries the whole of SH5 (cherry-picked in uncommitted at Step 1) plus the
six closures; the SH5b-over-SH5 delta is exactly four files —
`tools/factory/seat/factory-{brief,lib.sh,task}` and
`tests/unit/94-seat-harness.bats` (`git diff refs/gate/SH5..HEAD --stat`, the
other rows being docs main moved on).

All five MAJORs of `docs/reviews/2026-09-07-opus-review-sh4-SH5.md` are closed,
and both its owed MINORs (9 and 10). The section's own acceptance checks are
green at the committed rev under a real rebuild: `unit` **567/567 ok, 0 not ok**
— including `ok 224`, `ok 225` and `ok 503`, the three tests MAJOR-1 turned red
— `evidence-unit` 442 passed, `lint` 0 warnings/0 errors. The driver's own
`.result` (`touches_extra: 0`, `checks_verified: unit=pass evidence-unit=pass
lint=pass`, `verify_s: 18`) is confirmed on every name by my own runs.

Nine mutants applied; the six the section names all die, and two of the three I
added outside the section die too. No MAJOR.

One plan defect, disclosed by the seat and confirmed by me: contract item 4's
`le 8000 10000` → **pass** is arithmetically wrong (10000 ≤ 8000 is false). The
seat asserted `fail`, which is both the numeric truth and the value that reddens
the string-compare mutant. `plan_defect_secondary: wrong-fact` records it; the
implementation is right.

## Contract items

Each numbered item of `### SH5b`, taken literally, against the code in the
clone.

**1 — MAJOR-1: the brief's pinned phrase kept contiguous. MET.**

`git diff 27556aa..HEAD -- tools/factory/seat/factory-brief` is three added
lines and nothing removed — the base paragraph is restored byte for byte, and
the probe sentence is its own bullet above the "End your final reply…" bullet
(`tools/factory/seat/factory-brief:92-94`):

```
- Never `git push`.
- Before those four lines, print one line `FACTORY-PROBE <name>=<value>` per
  probe the task section names (none when it names none), the value being
  your own run's last output line.
- End your final reply with a summary in exactly this format, each item on
  its own line and nothing after it. The first line is exactly the result
  line, one space, status=done|partial|failed — no colon, no markdown; any
  other spelling is recorded as failed:
```

`grep -n 'no colon, no markdown' tools/factory/seat/factory-brief` → `97:`, one
hit, contiguous. The three named tests, from the `unit` build log:

```
ok 224 factory-brief quotes the exact FACTORY-RESULT grammar in its WORKSPACE RULES summary
ok 225 factory-brief states the grammar in prose before the template, without the literal label
ok 503 factory-brief's re-print sentence does not carry the literal label or repeat the phrase
```

**2 — MAJOR-2: three arguments always, defaults on every positional, an `empty`
probe end to end. MET.**

`tools/factory/seat/factory-task:374` → `cmpv=$(factory_probe_compare "$pop"
"$pvalue" "$pdiver")` — the operator branch on `empty`/`nonempty` at the call
site is gone. `tools/factory/seat/factory-lib.sh:772` → `local op=${1-}
bound=${2-} value=${3-} verdict`, and `:800` → the comment and code now read the
**third** argument. The new bats row
(`tests/unit/94-seat-harness.bats:2302-2372`) drives the plan's own
`checks-current: \`git status --porcelain docs/MAP.md\` :: empty :: the lint
gate` shape through `factory-task`; `.result` exists, `${lines[0]}` is
`FACTORY-RESULT status=done exit_code=0`, `probes_verified: checks-current=pass`,
`task_rc` 0. `nonempty` on `printf x` → `pass`; on `printf ''` → `fail` with
`task_rc` 1. Green in the clone and inside `checks.unit` (`ok 567 an empty or
nonempty probe runs end to end through factory-task with its command intact`).

**3 — MAJOR-3: the tab-collapse. MET.**

`tools/factory/seat/factory-task:352-354`:

```
          line=${line//$'\t'/$'\x1f'}
          # shellcheck disable=SC2034
          IFS=$'\x1f' read -r pname pop pvalue pby pcmd <<<"$line"
```

The real subcommand still emits the empty column — run in the clone:

```
$ python3 pkgs/evidence/tasks.py probes <fixture> K1 | cat -A
env^I$
checks-current^Iempty^I^Ithe lint gate^Igit status --porcelain docs/MAP.md$
```

and the row proves the command actually runs, not that the outcome happens to
be `pass`: the fake `git` at `tests/unit/94-seat-harness.bats:2311-2316` appends
its argv to `$PROBE_GIT_REC` when `$*` is exactly `status --porcelain
docs/MAP.md`, and `:2341-2342` asserts the recorded argv. That assertion is what
kills the mutant (see M3) — the `pass` verdict alone does not.

**4 — MAJOR-4: the five discriminating pairs. MET in substance; one value
corrected against the plan.**

`tests/unit/94-seat-harness.bats:1858-1867` carries `le 100 99` → pass, `lt 10
9` → pass, `ge 10 9` → fail, `gt 9 10` → pass, `le 8000 10000` → **fail**. The
section's close text says the last should be `pass`; that is wrong — under the
numeric compare `10000 ≤ 8000` is false. Measured directly under the
string-compare mutant, every one of the five differs from the numeric truth:

```
le 100 99     -> fail   (numeric: pass)
lt 10 9       -> fail   (numeric: pass)
ge 10 9       -> pass   (numeric: fail)
gt 9 10       -> fail   (numeric: pass)
le 8000 10000 -> pass   (numeric: fail)
ge 2 2.5      -> pass   (numeric: pass — the SH5 row that could not discriminate)
```

The seat disclosed the correction in the commit body. Recorded as MINOR-1 and as
`plan_defect_secondary: wrong-fact`.

**5 — MAJOR-5: contiguity and position. MET.**

`tests/unit/94-seat-harness.bats:2285-2300` now asserts: exactly one
`FACTORY-PROBE <name>=<value>` in the output; the line carrying it starts `- `
(`:2289`); `probe_pos ≤ result_pos - 2`; `checks_pos == result_pos + 1`,
`commits_pos == result_pos + 2`, `notes_pos == result_pos + 3` (the four
template lines contiguous); and the line immediately above `FACTORY-RESULT` ends
`recorded as failed:` (`:2299`). Both named placements are red (M5a, M5b), and
so is a blank line inserted anywhere inside the template block (O2).

**6 — MINOR-9 and MINOR-10: the body. MET.**

The body carries a `Greens:` block naming `unit` (with `ok 224/225/503`),
`evidence-unit` (442 passed) and `lint`, and every one is true at this rev by my
own `--rebuild` runs. `git log -1 --format=%B | grep -c '^Deviation:'` → 0; no
Deviation line for the exempt `docs/MAP.md`.

**The prior review's items, one by one.** MAJOR-1 closed (item 1). MAJOR-2
closed (item 2). MAJOR-3 closed (item 3). MAJOR-4 closed (item 4; the mutant now
dies). MAJOR-5 closed (item 5; both placements die). MINOR-9 closed. MINOR-10
closed. MINOR-1 through MINOR-8 are explicitly *recorded, not owed* by the
section; MINOR-8 (`grep -v '<'`) I re-tested and it still survives — MINOR-3
below.

**Interfaces and error contracts.** SH5's declared interfaces are unchanged by
this commit except the three sites above; the sh4 gate found every one of them
MET, and `evidence-unit` (which covers the grammar, the `check` strings, the
`probes` subcommand exits, the fence arms and the ingest) is green at this rev.
One stated contract moved: SH5's `missing` arm now tests the *line's presence*
(`factory-task:377`, `elif [ -z "$pseat_line" ]`) rather than the extracted
value's emptiness. That is closer to the Interfaces' own words ("the seat pasted
no line for the name"), it is disclosed in the body, and it is pinned — mutant
O1 (revert to `[ -z "$pseat" ]`) reddens the new row.

## Red before green

`refs/gate/SH5` (SH5's one commit, `31a69a3`) fetched into the scratch clone;
`tools/factory/seat/factory-{brief,lib.sh,task}` checked out from it against the
branch's tests, in
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/2e56f544-dc33-4c36-836e-c2b840c3e5fc/scratchpad/gate-sh4f-SH5b/mut`.
This is the section's own Step 2 red command set (the cherry-picked tree).

```
$ bats tests/unit/94-seat-harness.bats --filter probe
1..11
not ok 1 factory_probe_compare applies each operator to its boundary values
# (in test file tests/unit/94-seat-harness.bats, line 1875)
#   `[ "$output" = "fail" ]' failed
...
not ok 11 an empty or nonempty probe runs end to end through factory-task with its command intact
# (in test file tests/unit/94-seat-harness.bats, line 2338)
#   `[ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]' failed
```

(line 1875 is `factory_probe_compare empty '' x` → `fail`: SH5's two-argument
arity read `''` as the value and answered `pass`.)

```
$ bats tests/unit/94-seat-harness.bats --filter "RULES bullet"
not ok 1 factory-brief names the FACTORY-PROBE line inside the RULES bullet and keeps the four-line template
# (in test file tests/unit/94-seat-harness.bats, line 2289)
#   `[[ "$probe_line" == "- "* ]]' failed

$ bats tests/unit/94-seat-harness.bats --filter "re-print sentence"
not ok 1 factory-brief's re-print sentence does not carry the literal label or repeat the phrase
# (in test file tests/unit/94-seat-harness.bats, line 235)
#   `[ "$output" = "1" ]' failed

$ bats tests/unit/80-seat-driver.bats --filter grammar
1..2
not ok 1 factory-brief quotes the exact FACTORY-RESULT grammar in its WORKSPACE RULES summary
# (in test file tests/unit/80-seat-driver.bats, line 2537)
#   `[[ "$output" == *"no colon, no markdown"* ]]' failed
not ok 2 factory-brief states the grammar in prose before the template, without the literal label
# (in test file tests/unit/80-seat-driver.bats, line 2552)
#   `[[ "$output" == *"no colon, no markdown"* ]]' failed
```

Restored (`git checkout HEAD -- tools/factory/seat/`, tree clean), all six go
green:

```
1..11  ok 1 … ok 11   (--filter probe)
ok 1 factory-brief names the FACTORY-PROBE line inside the RULES bullet …
ok 1 factory-brief's re-print sentence …
1..2 ok 1 … ok 2      (80-seat-driver --filter grammar)
```

The two numeric-pair additions of item 4 are not red against SH5 (SH5's awk
compare was already correct); their load is carried by the mutant, which now
dies (M4). No test in the delta is vacuous.

## Mutants

Nine applied in
`/tmp/…/scratchpad/gate-sh4f-SH5b/mut`, each reverted with `git checkout HEAD --`
afterwards (tree clean, verified). **Six named by the section, all six killed;
three outside, two killed.**

| # | item | mutant | verdict | evidence |
|---|---|---|---|---|
| M1 | 1 | re-flow the paragraph (SH5's `factory-brief`) | killed | `not ok 1/2 … 80-seat-driver.bats:2537,2552` `no colon, no markdown`; `not ok 1 … 94-seat-harness.bats:235`; `not ok 1 … 94-seat-harness.bats:2289` |
| M2 | 2 | drop the third argument at the call site (`factory_probe_compare "$pop" "$pdiver"`) | killed | `not ok 1 an empty or nonempty probe … (line 2365) [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]' failed` — the `nonempty-ok` subcase |
| M3 | 3 | `IFS=$'\t'` put back (the `\x1f` translation neutralised) | killed | `not ok 1 … (line 2342) [ "$output" = "status --porcelain docs/MAP.md" ]' failed` — the command lost, the fake's argv never recorded |
| M4 | 4 | the awk numeric block replaced by `[ "$value" \> "$bound" ]` string compares | killed | `not ok 1 factory_probe_compare applies each operator to its boundary values (line 1859)` — `le 100 99` reads `fail` |
| M5a | 5 | `FACTORY-PROBE` moved into the template, directly above `FACTORY-RESULT` | killed | `not ok 1 … (line 2289) [[ "$probe_line" == "- "* ]]' failed` |
| M5b | 5 | `FACTORY-PROBE` moved directly below `FACTORY-NOTES` | killed | `not ok 1 … (line 2289) [[ "$probe_line" == "- "* ]]' failed` |
| O1 | — | `elif [ -z "$pseat_line" ]` reverted to `[ -z "$pseat" ]` | killed | `not ok 1 an empty or nonempty probe … (line 2338)` — the empty probe reads `missing`, the status `partial` |
| O2 | — | a blank line inserted between `FACTORY-RESULT` and `FACTORY-CHECKS` in the template | killed | `not ok 1 … (line 2295) [ "$checks_pos" -eq $((result_pos + 1)) ]' failed` |
| O3 | — | `grep -v '<'` dropped from the `FACTORY-PROBE` extraction (`factory-task:371`) | **survives** | `--filter probe` 11/11 ok, `--filter "end to end"` ok — the sh4 gate's MINOR-8, unchanged |

## Checks

Every command run from the fresh clone of `task/SH5b` at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/2e56f544-dc33-4c36-836e-c2b840c3e5fc/scratchpad/gate-sh4f-SH5b/gate-sh4f-SH5b`,
inside the devShell, `XDG_CACHE_HOME` under the scratchpad. Unlike the sh4 gate,
`--rebuild` **was** usable here (the derivations were valid in the store), so
all three acceptance checks were genuinely re-executed.

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass (exit 0)** — `1..567`, 0 `not ok` |
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | pass (exit 0) — `442 passed in 11.84s` |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | pass (exit 0) — `Found 0 warnings and 0 errors.` |
| `nix develop -c githooks/pre-commit` | exit 1 — only `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. The whole delta is the single line inside `<!-- tasks:begin -->…<!-- tasks:end -->` (SH5b queued → landed, SH6 arriving, CA1–CA3 from a plan that landed on main after the base). Exempt by the Global Constraints; reverted after the run. Not an SH5b defect. |
| `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| `nix develop -c shellcheck tools/factory/seat/factory-{lib.sh,task,brief}` | exit 0 |
| `python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | clean (exit 0) |
| `python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

The three tests MAJOR-1 reddened, verbatim from the `unit` build log
(`nix log .#checks.x86_64-linux.unit`, lines 228/229/507):

```
ok 224 factory-brief quotes the exact FACTORY-RESULT grammar in its WORKSPACE RULES summary
ok 225 factory-brief states the grammar in prose before the template, without the literal label
ok 503 factory-brief's re-print sentence does not carry the literal label or repeat the phrase
```

**The driver's own record, confirmed not believed.** `/home/dalhaka/factory/runs/sh4f/SH5b.result`
claims `touches_extra: 0`, `touches_disclosed: 0`, `checks_verified: unit=pass
evidence-unit=pass lint=pass`, `checks_verified_src: unit=run evidence-unit=run
lint=run`, `verify_s: 18`, `error_class: none`, `checks_scope: dirty` with 5
files. All three check verdicts match my own `--rebuild` runs exactly;
`touches_extra: 0` matches my own file-by-file comparison below; `checks_scope:
dirty` with those five files matches the diff (the tests and the fixture).

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
| `docs/MAP.md` | exempt by the Global Constraints (and correctly **not** disclosed) |

No file outside the contract. `docs/OPERATIONS.md` untouched; the plan file
untouched; no board commit; no `docs/ledger` or `docs/reviews` edit.

Step 3 said "nothing else unless a red of Step 2 demands it": the SH5b-over-SH5
delta is exactly `factory-brief`, `factory-lib.sh`, `factory-task` and
`94-seat-harness.bats` — no other source line moved.

Commit: exactly one, `66981d4`. Subject byte-identical to the section's (221
bytes, compared programmatically — `SUBJECT_MATCH True`). The two trailers
follow a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sh4f)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

The body states the why, pastes the reds, names every mutant, and pastes the
greens.

## Findings

No MAJOR.

- **MINOR-1** — `docs/superpowers/plans/2026-09-07-seat-harness-redesign.md`
  (SH5b contract item 4): the pair `le 8000 10000` → `pass` is arithmetically
  wrong; `10000 ≤ 8000` is false. `tests/unit/94-seat-harness.bats:1866-1867`
  asserts `fail`, which is the numeric truth *and* the value that reddens the
  string-compare mutant (measured: the mutant answers `pass`). The seat
  disclosed the correction in the commit body ("the correct numeric verdict is
  fail because 10000 > 8000"). A plan wrong-fact, not an implementation defect.
- **MINOR-2** — commit body, the mutant paste for MAJOR-2: "drop the third
  argument -> row 15 red (abort, no .result)". The reason is stale — with
  `local value=${3-}` at `tools/factory/seat/factory-lib.sh:772` there is no
  longer an abort. Applied, the mutant dies instead in the `nonempty-ok`
  subcase (`tests/unit/94-seat-harness.bats:2365`, `[ "${lines[0]}" =
  "FACTORY-RESULT status=done exit_code=0" ]` failed), because with two
  arguments `nonempty` reads the empty third positional. The mutant is killed;
  only the body's stated reason is wrong.
- **MINOR-3** — `tools/factory/seat/factory-task:371`: dropping `grep -v '<'`
  from the seat-value extraction still changes no test outcome (mutant O3;
  `--filter probe` stays 11/11 ok). Unchanged from the sh4 gate's MINOR-8, which
  the section explicitly records as not owed here.
- **MINOR-4** — `tools/factory/seat/factory-brief:92`: the new bullet opens
  "Before those four lines…" but sits *above* the bullet that first mentions
  those four lines, so the seat reads a forward reference. The placement is what
  contract item 1 mandates ("its OWN bullet line above the 'End your final
  reply…' bullet"), so this is the plan's wording to revisit, not the seat's.
- **MINOR-5** — the sh4 gate's MINOR-1 through MINOR-7 remain open exactly as
  recorded there (the probe-name grammar refusal, the exit-status rule, the
  `ne`/`nonempty` true arms — partly closed, `nonempty '' x` → `pass` was added
  at `tests/unit/94-seat-harness.bats:1878-1879` — the space folding, "the last
  per name", the driver's own 124 arm, the fail-and-missing arm). The section
  records them as not owed; carrying them to SH6 or a follow-up is the
  orchestrator's call.
- **MINOR-6** — `nix develop -c githooks/pre-commit` exits 1 in a clone of this
  branch. The sole cause is the hook regenerating the exempt
  `<!-- tasks:begin -->` block of `docs/OPERATIONS.md` (SH5b landed, SH6 queued,
  CA1–CA3 from `2026-09-08-codex-driver-arm.md` arriving on main after the
  base). Process noise for the gate, not a branch defect; recorded so the next
  reviewer does not re-litigate it.

## Verdict

**APPROVED.** Every one of the five MAJORs and both owed MINORs of the sh4 gate
is closed and pinned by a test that I showed red on SH5's own tree and green on
this one. The section's three acceptance checks are green at the committed rev
under a genuine `--rebuild`, confirming the driver's `checks_verified` line on
all three names. All six mutants the section names die, and two of three I added
outside it die as well; the one survivor is the sh4 gate's already-recorded
MINOR-8, which this section explicitly does not owe.

`plan_defect: none`. `plan_defect_secondary: wrong-fact` — contract item 4's
`le 8000 10000 → pass` is false arithmetic; the seat caught it, corrected it to
`fail`, disclosed it in the body, and the corrected value is the one that
discriminates.
