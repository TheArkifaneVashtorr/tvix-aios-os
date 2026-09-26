---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run pb4, task P4b — APPROVED

Branch `task/P4b` in `/home/dalhaka/factory/ws/pb4/P4b`, base `a55b6b5` (main), head `8c995ea`, one
commit, four files (`docs/board/operator-model.md` +47, `docs/runbooks/session.md` +36/-2,
`tests/unit/90-session-start.bats` +144/-2, `tools/session-start.sh` +55/-21; 255 insertions,
27 deletions). Reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-pb4-P4b`.

## Summary

The P4 major is fixed and the fix is proven three ways, not one. The five defaults are exactly the
contracted 2,500 / 2,100 / 1,200 / 1,000 / 500; the measured worst case (every part at its cap,
every truncation line printed) is **7,702 characters / 7,713 bytes**, and the new all-overflow test
observes **7,700** — 300 characters of headroom under the 8,000 ceiling, with the pointer last. The
live probe reproduces from the clone at **7,354** bytes and, with the live board substituted, at
**7,352** bytes, both ending on the pointer, so the number the commit body pastes (7,580, measured
in the seat workspace at 02:16 against a different in-flight table) is the same measurement taken at
a different moment, not a fabrication — the seat log shows the probe actually being run and the
FACTORY_RUN discovery that forced `env -u FACTORY_RUN`. All eight mutants die (the three new ones on
exactly the contracted tests, P4's five still). `shellcheck`, `bats`, `unit`, `lint`,
`bats-and-chain` are green and `docs/MAP.md` is unchanged. No MAJOR. Four minors, one of them a
behavioural regression against P4 that the contract's own wording caused (the directory case).

## The arithmetic

Measured from the script's own `printf` formats, not from the plan. The truncation format is
`tools/session-start.sh:83-84`:

```
    printf '%s\n…%s truncated at %s chars (SESSION_START_CAP_%s)\n' \
      "${text:0:$limit}" "$part" "$limit" "$name"
```

| item | source | chars | bytes |
| --- | --- | --- | --- |
| board cap | `session-start.sh:182` `cap_part BOARD "$board" 2500` | 2500 | 2500 |
| bundle cap | `:184` `cap_part BUNDLE "$bundle" 2100` | 2100 | 2100 |
| brief cap | `:186` `cap_part BRIEF "$brief" 1200` | 1200 | 1200 |
| in-flight cap | `:188` `cap_part INFLIGHT "$ritual_text" 1000` | 1000 | 1000 |
| operator cap | `:191` `cap_part OPERATOR "$operator_model" 500` | 500 | 500 |
| **caps sum** | | **7300** | **7300** |
| `…board truncated at 2500 chars (SESSION_START_CAP_BOARD)` | `:83` | 56 | 58 |
| `…bundle truncated at 2100 chars (SESSION_START_CAP_BUNDLE)` | `:83` | 58 | 60 |
| `…brief truncated at 1200 chars (SESSION_START_CAP_BRIEF)` | `:83` | 56 | 58 |
| `…inflight truncated at 1000 chars (SESSION_START_CAP_INFLIGHT)` | `:83` | 62 | 64 |
| `…operator truncated at 500 chars (SESSION_START_CAP_OPERATOR)` | `:83` | 61 | 63 |
| `## Operator model (docs/board/operator-model.md)` | `:190` (the only heading printed outside a cap) | 48 | 48 |
| `Where everything is: docs/runbooks/session.md` | `:193` | 45 | 45 |
| newlines (5 blank `echo`s + 11 line terminators; `$( )` strips the last) | `:181-194` | 16 | 16 |
| **worst case** | | **7702** | **7712** (`wc -c` 7713 with the final newline) |

**7,702 ≤ 8,000**, headroom 298 characters. The overhead above the caps is 402 characters, inside
the 700 the plan reserved and the structural test asserts, so the "700" is not merely nominal — it
is 74 % slack over the real figure. The all-overflow test measured live agrees: instrumenting
`tests/unit/90-session-start.bats:331` printed `LEN=7700` (two below the hand figure because the
board heading's em dash is one character in the bats shell's UTF-8 locale and three bytes in the
hook's `env -i` C locale).

## The tests and mutants

`tests/unit/90-session-start.bats:281-297` (structural sum) and `:299-342` (all-overflow) are the
two new load-bearing tests, `:344-355` the `abc` fallback.

The all-overflow test really overflows all six parts — I did not take the fixture on trust, the test
asserts every cut:

```
329	  [[ "$output" == *"## In flight"* ]]                       # in-flight precondition
330	  [[ "$output" == *"aa00 K - running"* ]]                    # …non-empty, 50 fake runs
331	  [ "${#output}" -le 8000 ]
332	  [ "$(printf '%s\n' "$output" | tail -n1)" = "Where everything is: docs/runbooks/session.md" ]
333-336	  the four remaining headings (Board — START HERE, # Evidence bundle, # Task brief, ## Operator model)
337-341	  …board/…bundle/…brief/…inflight/…operator truncated at 2500/2100/1200/1000/500
```

Mutants applied to the clone one at a time, run, reverted (`git status --porcelain` empty after
each). Eight of eight killed:

| # | mutant | applied at | killed by |
| --- | --- | --- | --- |
| A | old defaults 3000/2500/1500/1200/600 restored | `:182,184,186,188,191` | `not ok 22` — ``[ "${#output}" -le 8000 ]' failed`` (plus 6, 7, 11, 17, 21, 23) |
| B | one default raised by 700 (`INFLIGHT` → 1700) | `:188` | `not ok 21` — ``[ "$sum" -le "$((total - 700))" ]' failed`` (plus 22 on the ceiling) |
| C | `cap_part`'s numeric fallback removed (`case $limit in '' \| *[!0-9]*)` deleted) | `:78-80` | `not ok 23` — ``[[ "$output" == *"…board truncated at 2500 chars (SESSION_START_CAP_BOARD)"* ]]' failed`` — and *only* 23 |
| D1 | operator cap removed (`printf '%s\n' "$operator_model"`) | `:191` | `not ok 17`, `not ok 20`, `not ok 21`, `not ok 22` |
| D2 | the part's absence skips the pointer (`if [ -r … ]` wrapped around `:190-193`) | `:190-193` | `not ok 18` — ``[[ "$output" == *"unavailable: …not readable"* ]]' failed`` (plus 1, 6, 11) |
| D3 | exit 1 on a missing file (`exit 1` in the subshell **and** `) \|\| exit 1`) | `:113-120` | `not ok 18` on `[ "$status" -eq 0 ]` (and 14 others) |
| D4 | the part printed before the brief | `:181-193` | `not ok 19` — ``[ "$brief" -lt "$model" ]' failed`` — and *only* 19 |
| D5 | the env var ignored (`limit=$default`) | `:77` | `not ok 20` — ``[[ "$output" == *"…operator truncated at 100 chars (…)"* ]]' failed`` — and *only* 20 |

Note on D3: the weaker form (`exit 1` inside the `operator_model=$( … )` subshell only) survives,
but it is an *equivalent* mutant — the subshell exit does not change the hook's status or its output,
which is still the contracted unavailable line. The faithful mutant (the one the pa4 review applied,
failing the hook) is killed.

`bash tests/lint/bats-and-chain.sh` → rc=0 on the new tests (one `[ … ]` per line, no `&&` chains).

## Live

From the clone, which is the tree that lands:

```
$ bash tools/session-start.sh | wc -c
7354
$ bash tools/session-start.sh | tail -n 1
Where everything is: docs/runbooks/session.md
$ bash tools/session-start.sh | grep -c '^## Operator model'
1
```

Identical inside and outside `nix develop`. Structure (`grep -n` on the captured output): board cut
at line 11, bundle cut at 65, brief 67, `## In flight` 84, `## Operator model` 101, operator cut at
112, pointer at 114 — the last line.

With the live host's board substituted (`cp /home/dalhaka/nixos-agent-env/docs/OPERATIONS.md` over
the clone's, then reverted):

```
$ bash tools/session-start.sh | wc -c
7352
$ bash tools/session-start.sh | tail -n 1
Where everything is: docs/runbooks/session.md
```

Both under 8,000, pointer last. Against the commit body's pasted `7580`: the difference is live
drift, not fabrication. The in-flight part is the volatile one — at my measurement it is ~900 chars
listing eleven running seats, and at 02:16 the seat measured a different set; the brief's counts and
the bundle's timestamps also move. The seat log
(`/home/dalhaka/factory/runs/pb4/P4b.log:2855-2890`) records the probe being run, the discovery that
`FACTORY_RUN=pb4` made the bare command print 0 chars, and the decision to paste
`env -u FACTORY_RUN …` with that deviation stated in the commit body. The plan asked for
`bash tools/session-start.sh | wc -c`; running it verbatim inside a factory run measures nothing, so
the deviation is the correct reading of the acceptance, and it is declared.

## Minors

1. **A directory in place is a behavioural regression against P4, and it leaks stderr.**
   `tools/session-start.sh:113-119`. `[ -r "$f" ]` is **true** for a directory, so `cat` runs, fails,
   and `operator_model` is empty:

   ```
   --- case: dir ---
   cat: …/gate-pb4-P4b/docs/board/operator-model.md: Is a directory     (stderr, unswallowed)

   ## Operator model (docs/board/operator-model.md)

   Where everything is: docs/runbooks/session.md
   exit=0
   ```

   P4's `cat … 2>/dev/null || echo "unavailable: …"` printed the contracted line here (pa4 review,
   "case: directory in place"). Missing and mode-000 are both exact and exit 0, as contracted:

   ```
   --- case: missing ---                        --- case: mode000 ---
   ## Operator model (docs/board/operator-model.md)
   unavailable: docs/board/operator-model.md not readable
   Where everything is: docs/runbooks/session.md
   exit=0                                       exit=0
   ```

   No test covers the directory case, and the contract's item 4 ("the unreadable-file arm tests
   `[ -r "$f" ]`, never `2>/dev/null`") is what removed the arm that handled it. Not realistic input;
   recorded as the plan defect below.

2. **The structural test is coupled to the call-site syntax, not to the defaults.**
   `tests/unit/90-session-start.bats:289` greps `cap_part [A-Z_]+ "[^"]+" [0-9]+`. On P4's hook —
   which spells the same defaults as `"${SESSION_START_CAP_BOARD:-3000}"` — the grep matches nothing
   and the test goes red on `[ "$count" -eq 5 ]`, not on the sum. The sum line is still load-bearing
   (mutant B kills on `[ "$sum" -le "$((total - 700))" ]`), and the count guard is what stops the
   test going vacuous, so this is brittleness rather than a hole: a legitimate refactor back to the
   `${VAR:-N}` form would fail the test for the wrong reason. Plan-caused — the contract named the
   `${SESSION_START_CAP_<NAME>:-N}` literals, which the implementation deliberately no longer has.

3. **`SESSION_START_CAP` itself has no numeric fallback.** `tools/session-start.sh:16,195`. The new
   helper guards the five per-part caps only; the total still degrades to uncapped with a stderr
   line:

   ```
   $ SESSION_START_CAP=abc bash tools/session-start.sh 2>err >/dev/null; echo exit=$?
   exit=0
   $ cat err
   tools/session-start.sh: line 195: [: abc: integer expected
   ```

   Outside the contract (item 4 names `SESSION_START_CAP_<NAME>`), pre-existing, exit stays 0.

4. **"six headings" is off by one, twice.** `docs/runbooks/session.md:68` and
   `tests/unit/90-session-start.bats:284-285,304-305`. The hook prints five headings (four inside
   their own capped text, one — `:190` — outside) plus an unheaded pointer. The arithmetic is not
   affected: the real overhead is 402 characters against the 700 reserved. Plan wording, carried
   forward verbatim.

Also checked and clean: the runbook probe is one line (`docs/runbooks/session.md:83`
`grep -c '^## Operator model'`, verified → `1`); the runbook says six parts (`:5`) and lists all six
in order (`:8-40`); the Budgets block (`:58-65`) carries five caps, the pointer row and the total,
with the arithmetic spelled out at `:67-71`; every part goes through the one helper
(`grep -oE 'cap_part [A-Z_]+ "[^"]+" [0-9]+'` returns exactly the five call sites, no bypass); the
privacy line cites only `2026-09-05-telemetry-store-decisions.md`
(`docs/board/operator-model.md:6`), whose `:27` reads "do not leave the machine, not even" as
ciphertext; the tenth preference cites
`docs/superpowers/specs/2026-09-05-planning-agent-design.md` (`:14`), whose row O6 at `:202` carries
"each with a measurable acceptance and an effort class"; `docs/brief.md:68-79` and
`docs/board/operator-model.md:32-43` are byte-identical (`diff` empty); and
`grep -n -E '@|dalhaka|sk-|[0-9]{4,}'` over the operator file matches only the five decision-file
dates inside its own citations — no address, key, host name or path outside `docs/`.

The `2>/dev/null` sweep of `tools/session-start.sh` finds thirteen occurrences (lines 29, 52, 53,
54, 59, 125, 130, 131, 145, 154, 160, 176, 179) — all pre-existing, none introduced by this commit,
none on a gated command, and **none in the operator arm**, which is what the contract required.

## Checks

Run in the clone, `nix develop -c` throughout, `XDG_CACHE_HOME` under the session scratchpad.

| check | result |
| --- | --- |
| `shellcheck tools/session-start.sh` | rc=0 |
| `bats tests/unit/90-session-start.bats` | `1..23`, 23 ok, rc=0 |
| `bash tests/lint/bats-and-chain.sh` | rc=0 |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | rc=0 — 360 unit tests ok |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | rc=0 — "All checks passed!", 38 files already formatted |
| `githooks/pre-commit` | **rc=1** — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. Structural, not a defect: base `a55b6b5` is rc=0, the regeneration is a one-line diff dropping `P4b` from the derived queue, and staging that board makes HEAD rc=0 (`render.test.mjs: all assertions passed`). A task branch is forbidden a board commit; integration regenerates it. |
| `python3 pkgs/evidence/repomap.py --root . write` | `docs/MAP.md` unchanged (no diff) — correct, no package, module, check or tool added |

`--rebuild` on `unit` errors before it runs (`some outputs … are not valid, so checking is not
possible` — the derivation had never been built here), so the check was built fresh instead, which
is the same work.

## Red before green

`git -C /home/dalhaka/factory/ws/pa4/P4 show task/P4:tools/session-start.sh` written over the
branch's hook, the branch's tests kept:

```
1..23
ok 1 … ok 5
not ok 6 a bundle over its cap (2100) is cut and the brief and pointer still print
# (in test file tests/unit/90-session-start.bats, line 98)
#   `[[ "$output" == *"…bundle truncated at 2100 chars (SESSION_START_CAP_BUNDLE)"* ]]' failed
not ok 7 a board over its cap (2500) is cut and the bundle still follows
#   `[[ "$output" == *"…board truncated at 2500 chars (SESSION_START_CAP_BOARD)"* ]]' failed
not ok 11 with defaults the brief and the pointer print last even when all three parts overflow
#   `[[ "$output" == *"…board truncated at 2500 chars (SESSION_START_CAP_BOARD)"* ]]' failed
not ok 17 the operator-model part prints after the brief, capped at 500 by default
#   `[[ "$output" == *"…operator truncated at 500 chars (SESSION_START_CAP_OPERATOR)"* ]]' failed
not ok 21 the five part defaults sum to at most the total ceiling minus 700
# (in test file tests/unit/90-session-start.bats, line 295)
#   `[ "$count" -eq 5 ]' failed
not ok 22 with every part overflowing the output stays under 8000 and the pointer stays last
# (in test file tests/unit/90-session-start.bats, line 331)
#   `[ "${#output}" -le 8000 ]' failed
not ok 23 a non-numeric part cap falls back to that part's default
# (in test file tests/unit/90-session-start.bats, line 354)
#   `[[ "$output" == *"…board truncated at 2500 chars (SESSION_START_CAP_BOARD)"* ]]' failed
```

Exactly the seven the commit body pasted, with the same names and the same failing assertions.
The P4 hook's call sites are `cap_part BOARD "$board" "${SESSION_START_CAP_BOARD:-3000}"` … `:-600`
and it has no `case $limit in` fallback, which is why 21 and 23 are red. Restoring the branch's
hook: 23/23 green, `git status --porcelain` empty.

## Findings

No MAJOR. Minors 1–4 above; minor 1 is the only behavioural one and is the plan defect below.

Commit convention: exactly one commit; the subject is byte-identical to P4's (122 bytes with the
newline, `diff` against the string in the plan clean); both trailers present (`Generated-By: dsh
0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pb4)` and `Co-Authored-By:
Claude Fable 5.1 <noreply@anthropic.com>`); all four touched files inside `touches`; no board
commit; the commit body carries the red block and both live probe outputs; `P4b.result` is in the
exact form (`FACTORY-RESULT status=done`, `FACTORY-CHECKS unit=pass lint=pass`,
`FACTORY-COMMITS 1`, `FACTORY-NOTES …`).

## Verdict

**APPROVED.** The worst case is 7,702 characters against an 8,000 ceiling, proven by hand from the
script's own formats and observed at 7,700 by the all-overflow test; the live output is 7,354 bytes
from the clone and 7,352 with the live board, both ending on the pointer; eight of eight mutants
die, each on the contracted test; the red block reproduces exactly; and `shellcheck`, `bats`,
`unit`, `lint`, `bats-and-chain` and `MAP.md` are all clean. The one behavioural regression (a
directory at the operator-model path degrades to an empty part and a stderr line instead of the
contracted unavailable line) is unreachable input caused by the contract's own `[ -r "$f" ]`
wording, and is recorded as the plan defect rather than a blocker; fold it into the next task
touching this hook, together with minors 2–4.

plan_defect: missing-case — item 4 dropped the directory guard; cat leaks stderr
