---
reviewer: opus
majors: 1
minors: 6
mutants_total: 5
mutants_killed: 5
---
# Opus gate — seat run pa4, task P4 — REJECTED

Branch `task/P4` in `/home/dalhaka/factory/ws/pa4/P4`, base `91dcc5f`, head `ae97c42`, one commit,
four files (`docs/board/operator-model.md` NEW +47, `docs/runbooks/session.md` +10/-2,
`tests/unit/90-session-start.bats` +54, `tools/session-start.sh` +17/-3).
Reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-pa4-P4`.

## Summary

The file is well sourced, the part sits where the plan says, the cap goes through the existing
`cap_part`, red-before-green reproduces exactly, all five named mutants die, and every named check
is green. One MAJOR: on the real repository the assembled output is **8,176 characters**, so the
total ceiling `SESSION_START_CAP` fires and the runbook pointer — the very line this commit's own
runbook edit calls part 5 "so you always know where the map to all of this lives", and which the
plan's interface says "stays last" — is truncated away, together with most of the new operator part.
The plan's Step-3 live acceptance (`| wc -c` under 8,000) was never run: the seat's log contains no
`wc -c` at all, and the result block claims only `unit=pass lint=pass`.

## The file (sources cited)

`docs/board/operator-model.md`, 2,284 characters, five sections in the contracted order:
`# Operator model (derived; …)` → `## Preferences, ranked` → `## What the operator owns, by type` →
`## The six invariants` → `## Where the live items are`.

First 600 characters (measured with Python, character slice, the same unit the hook cuts on) —
heading plus the start of the ranked list, as contracted:

```
# Operator model (derived; the board holds pauses and open items — this file never lists them)

## Preferences, ranked

- terse, no preamble (§8)
- privacy outranks everything, nothing leaves the machine (`2026-09-02-invariants-bind-agents-not-operator-apps.md`, `2026-09-05-telemetry-store-decisions.md`)
- tool names read literally, plain words for a softkey (`2026-09-02-amendment-softkey.md`)
- tell me when the brief is wrong rather than route around it (§8)
- prefer failing the build over a runtime check (§8)
- one phase at a time, the operator says "test passed" (§7)
- deterministic first, 
```

Every one of the ten preference lines resolves to repo text:

| file:line | claim | source in the clone |
| --- | --- | --- |
| operator-model.md:5 | terse, no preamble | `docs/brief.md:314` "Terse. No preamble, no summaries of what you are about to do, no encouragement." |
| :6 | privacy outranks everything, nothing leaves the machine | `docs/decisions/2026-09-05-telemetry-store-decisions.md:26-28` "the broker audit logs … do not leave the machine, not even as ciphertext"; `docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md:7-9` quotes invariant 3 (see minor 5) |
| :7 | tool names read literally, plain words for a softkey | `docs/decisions/2026-09-02-amendment-softkey.md:3-10` — the "age" terminology collision, "Lesson recorded: explain tool names in plain language" |
| :8 | tell me when the brief is wrong rather than route around it | `docs/brief.md:329-330` "If something in this brief is wrong … I would rather rewrite the spec than have you route around it." |
| :9 | prefer failing the build over a runtime check | `docs/brief.md:325` "Prefer failing the build over a runtime check." |
| :10 | one phase at a time, the operator says "test passed" | `docs/brief.md:327` "One phase at a time."; `docs/brief.md:265-266` "Do not start the next phase until the previous phase's test passes and I have said so." |
| :11 | deterministic first, isolated workspaces second, judgement last; never design parallelism out | `docs/decisions/2026-09-04-parallel-agent-workflows.md:1` (title), `:25` "deterministic first, judgement last", `:35` "Persistent isolated workspaces per task" |
| :12 | falsifiable, not merely tested; unmeasured is debt; proxies declared | `docs/decisions/2026-09-03-test-based-reality-amendments.md:12,17,22` — the three numbered amendments verbatim in substance |
| :13 | no secrets in the repo, placeholders out of band | `docs/brief.md:317-318` "No secret material in the repo, ever … Use placeholders and tell me what to populate out of band." |
| :14 | recommendations welcome, each with a measurable acceptance and an effort class | `docs/superpowers/specs/2026-09-05-planning-agent-design.md:202` quotes the working-style memory "…each with a measurable acceptance and an effort class" (see minor 6 on the attribution) |

`## The six invariants` (operator-model.md:32-43) is byte-identical to `docs/brief.md:68-79`:

```
$ diff <(sed -n '68,79p' docs/brief.md) <(sed -n '32,43p' docs/board/operator-model.md)
SECTION3-VERBATIM-IDENTICAL
```

No personal data beyond the repo's own text. `grep -n -E '@|dalhaka|sk-|[0-9]{4,}'` over the file
matches only the four decision-file dates in the source parentheses (lines 6, 7, 11, 12) — no
address, e-mail, key, host name, or path outside `docs/`. No pause and no open item is listed;
`## Where the live items are` (line 47) points at the board and `evidence bundle` instead, as
contracted.

## The hook

Position, cap and the degraded path are all as the plan specifies.

- `tools/session-start.sh:170-175` — the part is printed after `cap_part INFLIGHT` and before the
  pointer; on the live-shaped run the heading is output line 103 and the pointer is the last line
  (when it survives — see the MAJOR).
- `tools/session-start.sh:173` — `cap_part OPERATOR "$operator_model" "${SESSION_START_CAP_OPERATOR:-600}"`:
  the existing `cap_part` (defined at `:65-77`), not a new truncation path. The truncation line is
  produced by `cap_part`'s own `printf` at `:72-73`.
- Default 600 and the env override both exercised live: with the file in place the output ends
  `…operator truncated at 600 chars (SESSION_START_CAP_OPERATOR)`; with
  `SESSION_START_CAP_OPERATOR=100` it ends `…operator truncated at 100 chars (…)`.
- Unreadable file — all three shapes give exactly the one contracted line and exit 0:

```
=== case: no file ===            === case: directory in place ===   === case: mode 000 ===
## Operator model (docs/board/operator-model.md)
unavailable: docs/board/operator-model.md not readable

Where everything is: docs/runbooks/session.md
exit=0                           exit=0                              exit=0
```

- `set -u` safety (`tools/session-start.sh:12`): `SESSION_START_CAP_OPERATOR` unset or empty both
  take the `:-600` default (verified). Non-numeric `abc` prints
  `tools/session-start.sh: line 71: [: abc: integer expected` on stderr, the `[ … -gt … ]` returns
  2, the `else` branch runs and the part prints **uncapped**; exit is still 0. Identical to the
  behaviour of the four pre-existing parts through the same `cap_part`, so not introduced here.
- Total ceiling: `SESSION_START_CAP` is still 8,000 (`:14`) and the pointer is still the last thing
  written inside the `out=$( … )` subshell (`:175`). In the plan's own worst case (board, bundle and
  brief overflowing, in-flight empty) the fifth part **filled** gives 7,529 characters, under the
  ceiling, ending on the pointer — so the existing test 11 keeps passing for the right reason. The
  problem is the case the plan's arithmetic left out; see Findings.

## Tests and mutants

`tests/unit/90-session-start.bats:226-279` — the four contracted tests exist, one `[ … ]` per line,
and `tests/lint/bats-and-chain.sh` accepts the file (`rc=0`). All four are non-vacuous: every mutant
the plan names was applied to the clone's hook, run, and reverted (`git status --porcelain` empty
after each).

| mutant | applied at | result |
| --- | --- | --- |
| remove the cap (`printf '%s\n' "$operator_model"`) | session-start.sh:173 | **killed** — `not ok 17` (`…operator truncated at 600 chars …` missing) and `not ok 20` |
| the part's absence skips the pointer (`if [ -r … ]` around 172-175) | session-start.sh:172-175 | **killed** — `not ok 18` plus pre-existing tests 1, 2 |
| exit 1 on a missing file (`… ) \|\| exit 1`) | session-start.sh:101 | **killed** — `not ok 18` on `[ "$status" -eq 0 ]` (and 13 other tests) |
| print the part before the brief | session-start.sh:168-175 | **killed** — `not ok 19` on `[ "$brief" -lt "$model" ]` |
| hard-code 600 (`cap_part OPERATOR "$operator_model" 600`) | session-start.sh:173 | **killed** — `not ok 20` |

5 of 5 mutants killed.

## Checks

Run in the clone, `nix develop -c` throughout.

| check | result |
| --- | --- |
| `shellcheck tools/session-start.sh` | rc=0 |
| `bats tests/unit/90-session-start.bats` | `1..20`, 20 ok, rc=0 |
| `bash tests/lint/bats-and-chain.sh` | rc=0 |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | rc=0 (357 unit tests ok) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | rc=0 ("All checks passed!", 38 files already formatted) |
| `githooks/pre-commit` | **rc=1** — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. Structural, not a defect: the regeneration only drops `P4` from the derived queue line, base `91dcc5f` is rc=0, and staging the regenerated board makes HEAD rc=0 (`render.test.mjs: all assertions passed`). The task branch is forbidden a board commit; integration regenerates it. |
| `python3 pkgs/evidence/repomap.py --root . write` | `docs/MAP.md` unchanged (no diff) — correct, the task adds no package, module, check or top-level entry |

Live probe (matrix item 5). The live tree at `/home/dalhaka/nixos-agent-env` predates this branch,
so the plan's live command was run in the clone, which is exactly the tree that lands:

```
$ bash tools/session-start.sh | grep -n 'Operator model'
103:## Operator model (docs/board/operator-model.md)
104:# Operator model (derived; the board holds pauses and open items — this file never lists them)

$ bash tools/session-start.sh | wc -c
8176
```

For reference, the live tree itself (`/home/dalhaka/nixos-agent-env`, read-only): its own hook gives
7,781 characters ending on the pointer; the P4 hook pointed at the live tree gives 7,886 — but only
because the live tree has no `docs/board/operator-model.md` yet, so the part degrades to the 105-byte
unavailable line instead of the ~709 bytes it costs once the file is there.

## Red before green

`git show 91dcc5f:tools/session-start.sh` restored over the branch's hook, `docs/board/operator-model.md`
removed, branch tests kept:

```
1..20
ok 1 … ok 16 (unchanged)
not ok 17 the operator-model part prints after the brief, capped at 600 by default
# (in test file tests/unit/90-session-start.bats, line 234)
#   `[[ "$output" == *"## Operator model (docs/board/operator-model.md)"* ]]' failed
not ok 18 a missing operator model degrades to one unavailable line and the pointer stays last
# (in test file tests/unit/90-session-start.bats, line 248)
#   `[[ "$output" == *"unavailable: docs/board/operator-model.md not readable"* ]]' failed
not ok 19 the operator-model part prints between the brief and the pointer
# (in test file tests/unit/90-session-start.bats, line 263)
#   `[ -n "$model" ]' failed
not ok 20 SESSION_START_CAP_OPERATOR overrides the default 600
# (in test file tests/unit/90-session-start.bats, line 278)
#   `[[ "$output" == *"…operator truncated at 100 chars (SESSION_START_CAP_OPERATOR)"* ]]' failed
```

Exactly tests 17–20 red, with the assertions the plan quoted and the commit body pasted. Restoring
the branch's hook and file: 20/20 green, tree clean.

## Findings

### MAJOR 1 — on the real repository the total cap fires and the runbook pointer is truncated away

`tools/session-start.sh:170-181`, `docs/runbooks/session.md:34-35`.

The plan's interface says "the total `SESSION_START_CAP` stays 8,000 and the pointer stays last", and
Step 3's live acceptance is "the whole output is under 8,000 chars (`bash tools/session-start.sh | wc -c`)".
Measured on the clone (the exact tree that lands), same repo, same store, same `nix develop` PATH:

```
P4 hook  : 8176 chars; last=[…truncated at 8000 chars (SESSION_START_CAP)]
main hook: 7096 chars; last=[Where everything is: docs/runbooks/session.md]
```

and with the live tree's `docs/OPERATIONS.md` substituted into the clone: **8,182 chars**, same
truncated last line. The new part costs ~709 characters (47-char heading + 600 capped + the ~60-char
truncation line + a blank), which pushes an output that was 7,096 over the 8,000 ceiling. What is
lost is the tail: the operator model is cut mid-line at

```
- tool names read literally, plain words 
…truncated at 8000 chars (SESSION_START_CAP)
```

so the pointer never prints. The commit's own runbook edit (`docs/runbooks/session.md:34-35`) says
part 5 is "One pointer — `docs/runbooks/session.md` (this file), so you always know where the map to
all of this lives." After this change, on this host, it does not print at all.

The plan's **Facts (planning time)** paragraph did the arithmetic as "3,000 + 2,500 + 1,500 + 600 +
the truncation lines is under 8,000" — it omits the in-flight cap of 1,200 (`session-start.sh:170`),
which is empty in the bats fake but is 1,000+ characters on the real host (the ritual log's
`allowed after` lines and the in-flight table). The unit tests therefore cannot see this: test 11
deliberately keeps the in-flight part empty, and I confirmed it still passes for the right reason
(7,529 characters with the fifth part filled).

The step that would have caught it is the plan's Step-3 live probe, and it was never run:
`grep -c 'wc -c' /home/dalhaka/factory/runs/pa4/P4.log` → **0**, and the commit body's Green section
says only "all 20 tests pass, unit and lint check clean". `P4.result` reports
`FACTORY-CHECKS unit=pass lint=pass` and nothing about the live probe.

### MINOR 1 — the live probe prints two lines, not the contracted one

`docs/board/operator-model.md:1`, `tools/session-start.sh:172`. `grep -n 'Operator model'` matches
both the hook's heading (line 103) and the file's own H1 (line 104). The plan specified both strings
and then asked for "one line", so the acceptance as written was unachievable; plan-caused, cosmetic.

### MINOR 2 — the runbook now says "five parts" while the hook prints six

`docs/runbooks/session.md:5,29-35`. The in-flight part (`session-start.sh:170`) has never been in the
numbered list; the change carries the same off-by-one forward (four→five). Pre-existing, plan-dictated.

### MINOR 3 — `SESSION_START_CAP_OPERATOR=abc` prints the part uncapped

`tools/session-start.sh:71`. `[ 2284 -gt abc ]` errors (`[: abc: integer expected` on stderr), the
`if` is false, the whole file prints. Exit stays 0. Shared with the four existing parts through the
same `cap_part`, so not introduced here, but the fifth part inherits it.

### MINOR 4 — the "privacy" line's first citation says close to the opposite

`docs/board/operator-model.md:6` cites
`docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md`, whose holding is that the
egress invariant binds *agents*, not the operator's apps — lines 4-5 quote the operator: "I don't
care if apps talk to the internet, I just want better safeguards for Agents." The second citation
(`2026-09-05-telemetry-store-decisions.md:26-28`) does support "nothing leaves the machine". The
wording and both citations came from the plan verbatim.

### MINOR 5 — the tenth preference's attribution points at the wrong file

`docs/board/operator-model.md:14` says "(working-style, quoted on the board)". The quotation is not
in `docs/OPERATIONS.md`; it is in
`docs/superpowers/specs/2026-09-05-planning-agent-design.md:202` (row O6). Plan-dictated wording.

### MINOR 6 — the unavailable path swallows the read error

`tools/session-start.sh:101` — `cat … 2>/dev/null || echo "unavailable: …"`. Not a gated command, so
no house-rule breach, and the degraded line is the contracted one; but a mode-000 file and a missing
file are indistinguishable in the output.

## Verdict

**REJECTED** on MAJOR 1. Everything else in the matrix passes: the file is sourced and clean, the
part is in the contracted position through the existing `cap_part`, the degraded path is exact, the
four tests are non-vacuous against all five named mutants, red-before-green reproduces exactly, and
`unit`, `lint`, `shellcheck`, `bats-and-chain` and `MAP.md` are all green. The fix is a budget
decision, not a rewrite: either lower `SESSION_START_CAP_OPERATOR`, or raise `SESSION_START_CAP`, or
move the pointer above the operator part — and the fix round must re-run the plan's live probe and
paste `wc -c`.

Commit convention: one commit; subject byte-identical to the plan's (122 bytes, `diff` clean); both
trailers present (`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash …` and
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`, permitted by
`docs/decisions/2026-09-05-commit-metadata-mixed-trailers.md:1`); all four touched files inside
`touches`; no board commit; `P4.result` in the exact result-block form.

plan_defect: wrong-size — the budget arithmetic omitted the 1,200-char in-flight cap
