---
plan_defect: none
mutants_total: 27
mutants_killed: 26
mutants_outside_named: 2
reviewer: opus
majors: null
minors: 9
---
# Opus gate — seat run pb2, task P2b — APPROVED

## Summary

All three pa6 MAJORs are answered, each by direct observation rather than by argument.

1. **Streams.** Every command-backed part now captures stdout alone into its fence; the part's
   stderr goes to a separate file, is stripped of nix's two noise shapes, and appears — only when
   something survives the strip — under a second fence headed `stderr:`. On the **live tree, on the
   default `nix develop -c python3` path, with the tree dirty**, M3 prints `592251 bytes` and
   `nix develop -c python3 pkgs/evidence/tasks.py --root . json 2>/dev/null | wc -c` prints `592251`
   — equal, trailing newline included (pa6's off-by-one is gone too, because the count is
   `wc -c <file`, not `${#var}`). M7 prints `silent (exit 0)`. `grep -c 'is dirty'` over the
   169,338-byte live packet: `0`.
2. **Whole or nothing.** The packet is composed inside `{ … } >"$packet"` and `cat`-ed once at
   line 489. Across eleven failure fixtures — a missing `factory-integrate`, a missing
   `docs/OPERATIONS.md`, an unreadable-at-use routing table, spec and `factory-integrate`, an M1
   refusal, a mid-packet `tasks.py json` failure, a missing Appendix A, four path/date refusals —
   **stdout was 0 bytes every time**. The temp directory was removed on every path, SIGTERM
   included.
3. **The commit body** carries `| wc -c : 162348`, `| grep -c '^## M' : 13` and
   `M7 renders: silent (exit 0)`.

Checks are green (unit 385 ok, lint, the hook as the seat ran it, MAP reproduces, `bats-and-chain`),
the subject is byte-identical to P2's, the red is real, and 26 of 27 mutants die. Nine minors, none
of them a MAJOR by this gate's list.

## Streams

Fixture: the bats tree rebuilt under `<scratch>/fix1`, driven with four interpreters.

| case | expected | observed | exit | stdout bytes |
|---|---|---|---|---|
| `FACTORY_PYTHON3_CMD=<devShell python3>` | baseline | M3 `827 bytes`; M7 `silent (exit 0)`; `stderr:` fences `0` | 0 | 9,333 |
| wrapper printing `warning: Git tree '/x' is dirty`, `evaluation warning: …` **and** `real tool line` on stderr | count unchanged, noise gone, real line kept | M3 `827 bytes`; M7 `silent (exit 0)`; `grep -c 'is dirty'` = **0**; five `stderr:` fences (M2–M5, M7), each holding exactly `real tool line` | 0 | — |
| wrapper printing **only** nix-shaped noise on stderr | no `stderr:` fence at all | `grep -c '^stderr:$'` = **0** | 0 | 9,571 |
| wrapper printing the same noise on **stdout** | it lands in the fence (the contract filters stderr only) | M3 `859 bytes` (827 + 32); M2's fence opens with `warning: Git tree '/x' is dirty` | 0 | 9,685 |
| truth | `… json \| wc -c` | `827` — equal to M3 in all three stderr cases | — | — |

The last row is the contract read literally and is right: a tool that writes its own noise to
**stdout** is indistinguishable from output, and the packet must not silently edit a tool's stdout.

M2/M4/M5's fences hold only the tool's stdout in every case:

```
## M2 — <noisy wrapper> pkgs/evidence/tasks.py --root . brief
TS: 2026-09-06T09:10:01Z
~~~
# Task brief (generated 2026-09-06T09:10:01Z)
…
~~~
stderr:
~~~
real tool line
~~~
```

M7, same run — the pa6 failure, inverted:

```
## M7 — <noisy wrapper> pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06 --repo-root .
TS: 2026-09-06T09:10:01Z
silent (exit 0)
stderr:
~~~
real tool line
~~~
```

`filter_noise` (`factory-plan-brief.sh:165-169`) is anchored (`^warning: Git tree .* is dirty$`,
`^evaluation warning:`), so a tool line merely *containing* those words survives.

## Whole or nothing

`TMPDIR` listed before and after each run; `probe()` records stdout bytes separately from stderr.

| case | expected | observed | exit | stdout bytes | tmp leftovers |
|---|---|---|---|---|---|
| `factory-integrate` removed | exit 3, stdout empty, named on stderr | `factory-plan-brief: no such command: tools/factory/seat/factory-integrate` | **3** | **0** | 0 |
| `docs/OPERATIONS.md` removed | same | `factory-plan-brief: no such command: docs/OPERATIONS.md` | **3** | **0** | 0 |
| M1 refusal (`**dependsOn:** Q9`) | exit 2, stdout empty | `refusing — the graph is not sound:` / `tasks: nixos-agent-env/E1 dependsOn Q9: unknown key` | **2** | **0** | 0 |
| `tasks.py json` fails mid-packet | exit 3, the part named | `factory-plan-brief: part M3 failed` | **3** | **0** | 0 |
| design spec without `## Appendix A` | exit 3, never `unavailable:` | `factory-plan-brief: no Appendix A in docs/superpowers/specs/2026-09-05-planning-agent-design.md` | **3** | **0** | 0 |
| `<spec>` / `<out>` traversal, absolute, symlinked out of prefix (5 cases) | exit 2, stdout empty | the two prefix messages | **2** | **0** | 0 |
| happy path | exit 0 | full packet | 0 | 9,333 | 0 |
| SIGTERM mid-run | temp dir reaped by the trap | rc 143; `$TMPDIR` empty | 143 | — | **0** |
| `factory-integrate` replaced by a **directory** (passes `[ -r ]`, fails at use) | exit 3, part named | `sed: read error … Is a directory`; **exit 4**, part not named | 4 | **0** | 0 |
| `docs/ledger/routing.toml` a directory | same | `cat: … Is a directory`; **exit 1** | 1 | **0** | 0 |
| the spec a directory (vanishes between check and TARGET) | same | `wc: 'standard input': Is a directory`; **exit 1** | 1 | **0** | 0 |
| `docs/OPERATIONS.md` a directory | — | awk warns on the script's stderr; the packet **prints** with an empty START HERE block | **0** | 9,294 | 0 |
| `docs/MAP.md` a directory | — | same shape, empty Checks block | **0** | 9,295 | 0 |

The MAJOR the plan aimed at is closed: **no case put a byte on stdout at a non-zero exit**, and no
temp file survived any exit path. The last five rows are MINOR-2 and MINOR-3 below: three
after-the-check failures leave with the *tool's* exit code and no part name instead of the
contracted exit 3, and two `awk` targets fail open at exit 0.

## Guards and scoping

| case | expected | observed | exit | stdout bytes |
|---|---|---|---|---|
| `docs/superpowers/specs/../../../etc/passwd` | exit 2 | `spec must be under docs/superpowers/specs/` | 2 | 0 |
| `docs/reviews/plan-drafts/../../../etc/passwd` | exit 2 | `out must be under docs/reviews/plan-drafts/` | 2 | 0 |
| absolute `/etc/passwd` as spec; `/tmp/x.md` as out | exit 2 | both messages | 2 | 0 |
| `<out>` through a **symlink** in plan-drafts pointing at `/tmp` | exit 2 | `out must be under …` | 2 | 0 |
| `<spec>` through a symlinked specs subdirectory pointing outside | exit 2 | `spec must be under …` | 2 | 0 |
| `--date notadate` | exit 2 + message | `factory-plan-brief: --date must be YYYY-MM-DD: notadate` | 2 | 0 |
| `--since notadate` | exit 2 + message | `factory-plan-brief: --since must be YYYY-MM-DD: notadate` | 2 | 0 |
| **`--date 2026-13-99`** | exit 2 + message | `date: invalid date ‘2026-13-99 - 7 days’` | **1** | 0 |
| **`--since 2026-13-99`** | exit 2 + message | packet prints; `## M12 — git log --since=2026-13-99 …`, board-log block empty | **0** | 9,229 |
| `--since 2026-09-30 --date 2026-09-06` | say | accepted; `board log paragraphs dated >= 2026-09-30` prints nothing, no notice | 0 | 9,229 |

`realpath -m` is doing real work: dropping it (mutant E) turns the two traversal cases green and
kills the test. The last three rows are MINOR-1: `is_date` (`:76-78`) checks the *shape*, not the
calendar.

RUBRIC/CHECKLIST, now exercised:

| case | observed | exit |
|---|---|---|
| `tools/factory/plan/rubric.md` present | that file, verbatim, in a `~~~` fence; the 5.1 fallback not used | 0 |
| absent | the design's `### 5.1 The rubric (14 rows)` block; CHECKLIST holds `## Appendix A — the eight questions` | 0 |
| design spec without Appendix A | `factory-plan-brief: no Appendix A in …`, stdout empty | 3 |
| design spec absent entirely | RUBRIC would degrade, but CHECKLIST refuses first — same message | 3 |

M6 scoping (`:266`): with a fake `evidence` **on** PATH and the toolbox pointed at a scratch
fixture, M6 prints `unavailable: evidence describes the live host, not this tree`; with the toolbox
pointed at `/home/dalhaka/nixos-agent-env` the bundle runs (see the live probe). With `evidence`
off PATH the `unavailable: evidence not on PATH` branch still stands (bats case P2 c).

Degradables, all four together (`ritual.sh`, `session-start.sh`, `operator-model.md` removed):
exit 0, and `unavailable: tools/ritual.sh not found`, `unavailable: tools/session-start.sh not
found`, `unavailable: docs/board/operator-model.md not found`.

`grep -n '2>/dev/null' tools/factory/seat/factory-plan-brief.sh` → no match (exit 1).

M13's heading, live and in fixture: `## M13 — bash tools/factory/seat/factory-brief
docs/superpowers/plans/2026-09-05-evidence-store.md E1`, and `README.md:179-182` says why
(`M13` runs `factory-brief` via `bash` … "its heading carries the command exactly as run").
`README.md:165-168` carries the M8 note: `tools/ritual.sh inflight` "shares the session hook's
stranded-marker reaping: it removes dead-pid, stale `.pid`/`.gate` files under the runs dir
(idempotent housekeeping), and writes nothing under the tree."

## Live probe

Read-only audit first. The script opens nothing for writing; its one write target is the `mktemp -d`
directory outside the tree. The single side effect named in the plan is M8/M9's shared reaping
(`tools/ritual.sh:279-289`, `rm -f -- "$pfile"` for a **dead** pid **and** mtime > 7,200 s). Before
the run: `find ~/factory/runs -maxdepth 2 \( -name '*.pid' -o -name '*.gate' \)` → **0 files**, so
the loop had nothing to act on and was inert by construction.

```
$ env -u FACTORY_PYTHON3_CMD FACTORY_TOOLBOX_REPO=/home/dalhaka/nixos-agent-env \
    bash <clone>/tools/factory/seat/factory-plan-brief.sh \
    docs/superpowers/specs/2026-09-04-helm-home-design.md \
    docs/reviews/plan-drafts/2026-09-07-helm-home-1-probe.md
exit=0
| wc -c            : 169338
| grep -c '^## M'  : 13
```

```
## M1 — nix develop -c python3 pkgs/evidence/tasks.py --root . check
## M3 — nix develop -c python3 pkgs/evidence/tasks.py --root . json
TS: 2026-09-06T09:16:16Z
592251 bytes
run it yourself in the workspace when you need the graph

## M7 — nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06 --repo-root .
TS: 2026-09-06T09:16:18Z
silent (exit 0)
```

Truth, same tree, same moment:
`nix develop -c python3 pkgs/evidence/tasks.py --root . json 2>/dev/null | wc -c` → **592251**.
Equal. The tree was dirty throughout (`evidence bundle` in the same packet says
`**HEAD:** 94206c3ba027 — WORKING TREE DIRTY.`), which is the condition pa6 failed under.
`grep -c 'is dirty'` over the packet: `0`. `grep -c '^stderr:$'`: `0`.

Nothing written: `git status --porcelain` before and after are byte-identical
(` M docs/superpowers/plans/2026-09-06-planning-agent.md`, the orchestrator's own edit); the
marker listing under `~/factory/runs` is unchanged (`diff` empty);
`/home/dalhaka/nixos-agent-env/docs/reviews/plan-drafts` still does not exist. `$TMPDIR` held twelve
entries afterwards, all of them `nix-develop-*` / `nix-shell.*` litter from nix itself — no
`factory-plan-brief.*` directory survived.

**Against the body's 162348.** A different number is expected and is not a discrepancy: the tree has
moved (HEAD is now `94206c3`, two docs commits past the seat's base, which lengthens M12 and M2),
and the ~7 KB gap matches M6 exactly — the M6 block in my run is **5,676 bytes** of `evidence
bundle`, which collapses to a one-line `unavailable: evidence describes the live host, not this
tree` whenever `FACTORY_TOOLBOX_REPO` is the workspace clone rather than the live repo. The three
facts the body asserts — the default `nix develop` interpreter path, thirteen `## M` headings, and
`M7 renders: silent (exit 0)` — I reproduced independently.

## Tests and mutants

24 bats cases in `tests/unit/83-plan-brief.bats` (8 from P2, 16 new), all green;
`82-factory-dispatch.bats` 15, `80-seat-driver.bats` 45 — 84 ok.

27 mutants applied to `factory-plan-brief.sh`, bats run, reverted. **26 killed, 1 survived.**

| # | mutant | result | killed by |
|---|---|---|---|
| A | `2>&1` restored on M3 | KILLED | mid-packet-failure case |
| B | the noise filter dropped | KILLED | P2b streams |
| C | the up-front check dropped | KILLED | P2b missing source |
| D | compose-then-print dropped | KILLED | 19 cases |
| E | the `realpath -m` guard dropped | KILLED | P2b traversal |
| F | the Appendix A exit-3 dropped | KILLED | P2b no-Appendix-A |
| G | the M6 scoping dropped | KILLED | P2b M6 scope |
| 1 | M13 emitted before M12 | KILLED | P2 a |
| 2 | M1's exit ignored | KILLED | P2 b |
| 3 | M2 run before deciding | KILLED | P2 b (the recorder) |
| 4 | die on missing `evidence` | KILLED | 16 cases |
| 5 | `-le 1500` → `-lt 1500` | KILLED | P2 d |
| 6 | accept any `<out>` path | KILLED | P2 e, P2b traversal |
| 7 | print the whole board log | KILLED | P2 f |
| 8 | RULES' `factory-brief <draft> <KEY>` sentence dropped | KILLED | P2 h |
| 11 | M13 pointed at a key without `E1` | KILLED | P2 g |
| 19 | `## OPERATOR` renamed | KILLED | P2 a, pin TS |
| 9 | `~~~` → three backticks | KILLED | pin fences |
| 10 | header date dropped | KILLED | pin header |
| 12 | every `TS:` line dropped | KILLED | pin TS |
| 13 | M4 `--repo` → `WRONGREPO` (**call**) | KILLED | 17 cases (`waves` dies → exit 3) |
| 13h | M4 `--repo` → `WRONGREPO` (**heading**) | KILLED | pin M4 |
| 14 | M7 `--today "$today"` dropped (**call**) | **SURVIVED** | — |
| 14h | M7 `--today "$today"` dropped (**heading**) | KILLED | pin M7 |
| 15 | M9's `env -u FACTORY_RUN` dropped | KILLED | pin M9 |
| 17 | M10 emits nothing | KILLED | pin M10 |
| 18 | FIELD's START HERE block dropped | KILLED | pin FIELD |

The four mutations the plan names (A–D) all die, as do the three the gate named (E–G), P2's ten
kills, and seven of the eight new pins. Rows 13h and 14h are mine, added to split each pin's
heading form from its call form; that split is what exposes the one survivor.

**On the survivor.** `pin M7` (`83-plan-brief.bats:462-466`) asserts on the *heading string*
`## M7 — … --today `, which is `printf`-ed at `:281`; the flag actually handed to `claims.py` is at
`:282`. Deleting it from `:282` alone leaves all 24 cases green while the heading keeps claiming
the flag. I did **not** score this a vacuous-test MAJOR: the test does bite (14h kills it), and the
pa6 review's own MINOR-1 prescribed exactly this pin — "M4's heading contains `--repo
nixos-agent-env`; M7's contains `--today <date>`" — which the plan then told the implementer to
follow one-for-one. It is recorded as MINOR-4: the clause "M7 is dated by `--date`" is still
unpinned, and a one-line case (a claims file with a `review_by` row, run under two `--date` values)
would close it.

## Checks

| check | result |
|---|---|
| `shellcheck factory-plan-brief.sh factory-lib.sh factory-dispatch` | clean |
| `shfmt -d -i 2 -ci factory-plan-brief.sh` | no diff |
| `bats 83-plan-brief.bats 82-factory-dispatch.bats 80-seat-driver.bats` | 24 + 15 + 45 = **84 ok** |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | ok 1..385, exit 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link` (clean tree) | exit 0 |
| `githooks/pre-commit` (delivered tree, post-commit) | exit 1 — regenerates the board queue block |
| `githooks/pre-commit` (base `6be624f` + this change **staged**, as the seat ran it) | **exit 0** |
| `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | reproduces exactly |
| `bash tests/lint/bats-and-chain.sh` | exit 0 |
| `tasks.py --root . check` | silent, exit 0 |
| `grep -n '2>/dev/null' factory-plan-brief.sh` | no match |

The post-commit board staleness is the landing's own effect, exactly as at pa6: staged on the base,
the gate is green, and no board commit is owed.

Commit convention: exactly one commit (`git rev-list --count 6be624f..task/P2b` → `1`); the subject
is byte-identical to P2's *and* to §P2b's (`cmp` on both, no output); six files —
`factory-plan-brief.sh`, `factory-lib.sh`, `83-plan-brief.bats`, `README.md` are §P2b's `touches`,
`factory-dispatch` is P2's prescribed seam move carried by the cherry-pick, `docs/MAP.md` is the
`tests/unit — 15 → 16 files` line the repomap rule requires; both trailers, `Generated-By` then
`Co-Authored-By`; no board commit.

## Red before green

P2's script (`git -C ~/factory/ws/pa6/P2 show task/P2:tools/factory/seat/factory-plan-brief.sh`,
349 lines) dropped into a clean clone of this branch, P2b's tests run against it:

```
1..24
ok 1..8                                   (P2's own eight)
not ok  9 keeps nix noise out of M3 and M7 (P2b streams)
#   `[ "$(m3_byte_count "$output")" = "$clean_bytes" ]' failed
not ok 10 refuses up front when a packet source is missing (P2b)   # `[ "$status" -eq 3 ]' failed
not ok 11 names a part that fails mid-packet (P2b)                 # `[ "$status" -eq 3 ]' failed
not ok 13 refuses a design spec without Appendix A (P2b)           # `[ "$status" -eq 3 ]' failed
not ok 14 refuses a traversing spec or out path (P2b)              # `[ "$status" -eq 2 ]' failed
not ok 15 refuses a malformed --date or --since (P2b)              # `[ "$status" -eq 2 ]' failed
not ok 24 scopes M6 to the live toolbox repo (P2b M6 scope)
ok 12, 16..23                             (RUBRIC/CHECKLIST + the eight pins)
```

Seven of the sixteen new cases are red on P2 — the noisy interpreter, the up-front refusal, the
mid-packet failure, the missing Appendix A, the traversal, the dates, the M6 scope. Restoring
P2b's script: 24 ok. Cases 12 and 16–23 are green on P2 by design: the eight pins fix nothing, they
fence behaviour pa6 verified was already correct, and their red is the mutant, not the old script —
which is what the table above shows.

## Findings

**MINOR-1 — a well-shaped but impossible date is not refused; `--date` still exits 1.**
`factory-plan-brief.sh:76-88`. `is_date()` is `^[0-9]{4}-[0-9]{2}-[0-9]{2}$`, a shape test, so
`2026-13-99` passes it. `--date 2026-13-99` then dies on `set -e` at `:88`:

```
=== date-bad   rc=1 stdout_bytes=0 stderr=date: invalid date ‘2026-13-99 - 7 days’
```

exit 1 is not among the codes the header (`:23-26`) or the README document. `--since 2026-13-99` is
worse-behaved and quieter: it is never handed to `date`, so the packet prints at exit 0 with
`## M12 — git log --since=2026-13-99 …` and an empty board-log block —

```
=== since-bad  rc=0 stdout_bytes=9229
218:$ board log paragraphs dated >= 2026-13-99
```

§P2b contract 4 asks for "exit 2 with a message" on a malformed `--since`/`--date`. `notadate` is
covered (and tested); a calendar-invalid date is not. `--since` after `--date` is likewise accepted
silently with an empty board log.

**MINOR-2 — an after-the-check failure exits with the tool's code, not 3, and does not name the
part.** `run_hard` (`:203-211`) covers M2–M5 only. Everything else runs bare under `set -e`, so a
source that passes `[ -r "$f" ]` at `:133` and then fails at use leaves with the tool's status:

```
=== integrate-is-dir  rc=4 stdout_bytes=0 stderr=sed: read error on tools/factory/seat/factory-integrate: Is a directory
=== routing-is-dir    rc=1 stdout_bytes=0 stderr=cat: docs/ledger/routing.toml: Is a directory
=== spec-is-dir       rc=1 stdout_bytes=0 stderr=wc: 'standard input': Is a directory
```

§P2b contract 2: "a part that still fails after that → exit 3, the part named, nothing on stdout."
Two of the three clauses hold — stdout is empty and the tool's own message identifies the file — but
the code is undocumented and, at exit 2 (`cat` on a directory can give 1, `sed` 2), would be
indistinguishable from M1's refusal. `sed -n '2,17p'` (`:364`), the START HERE `awk` (`:373`),
`cat docs/ledger/routing.toml` (`:323`), `wc -w <"$spec"` (`:408`) and `cat -- "$spec"` (`:423`) are
the reachable sites.

**MINOR-3 — two `awk` sources fail open at exit 0 with a silently empty block.**
`:315` (M10) and `:373` (FIELD's START HERE). A `docs/MAP.md` or `docs/OPERATIONS.md` that passes
`[ -r ]` but yields nothing prints an empty fence and the packet still exits 0:

```
=== operations-is-dir  rc=0 stdout_bytes=9294   (awk: warning: … is a directory: skipped)
=== map-no-checks      rc=0 stdout_bytes=9293
## M10 — the ## Checks section of docs/MAP.md
TS: …
~~~
                       <- one empty line
~~~
```

A `docs/MAP.md` with no `## Checks` heading is the realistic form. The planner reads an empty
Checks list as fact. A one-line `[ -n "$m10_out" ] || …` notice would close it, as CHECKLIST
already does.

**MINOR-4 — `pin M7` pins the heading, not the call.** `83-plan-brief.bats:462-466` matches
`*'## M7 — '*"--today "*`, which `:281` prints. Dropping `--today "$today"` from the invocation at
`:282` leaves all 24 cases green (the sole mutant survivor above). The pin follows the pa6 review's
own wording, so this is unfinished coverage rather than a vacuous test; a claims file with a
`review_by` row driven under two `--date` values would discriminate.

**MINOR-5 — `2>/dev/null` is gone in the letter, not in the effect.** `:265`
`if command -v evidence >/dev/null 2>&1; then`. The contract says "no `2>/dev/null` anywhere in the
script" and the literal string is absent (`grep` exit 1); the same suppression survives spelled
`>/dev/null 2>&1`. Harmless on `command -v` — recorded so the rule and the file agree.

**MINOR-6 — a failing M7 shows neither `silent` nor its exit code.** `:283-288`: with `CAP_RC != 0`
and empty stdout, neither branch fires, so the part renders as a heading, a `TS:` line and the
`stderr:` fence alone:

```
## M7 — … claims.py validate …
TS: 2026-09-06T09:20:14Z
stderr:
~~~
claims: boom
~~~
```

The diagnosis is present, but the packet never says the validator failed — an `exit <n>` line would.

**MINOR-7 — the live-host coupling is a hard-coded home path.** `:146`
`live_repo=/home/dalhaka/nixos-agent-env`. §P2b asks for exactly this, so it is contract, not
deviation; recorded because a tracked script now carries the operator's `$HOME` layout and any move
of the repo silently turns M6 into `unavailable:` everywhere.

**MINOR-8 — one assertion cannot fail.** `83-plan-brief.bats:402-403`: `[ -z "$output" ]` followed
by `[[ "$output" != *"unavailable:"* ]]`. The second is implied by the first. The clause it means to
pin ("never `unavailable:`") is genuinely pinned by the exit-3 assertion on `:401`; the line is
dead weight, not a false green.

**MINOR-9 — the RUBRIC/CHECKLIST case is coverage, not red.** Case 12 passes against P2's script
too (P2 already extracted both; only the fixture was missing). Correct as filed — pa6's MINOR-2 was
"never exercised", and it now is — but it is not part of this round's red, and no mutant in the
named list touches the two `awk` extractions at `:438` / `:457`.

## Verdict

APPROVED. Every MAJOR pa6 raised is closed by observation, not by argument: the byte count and M7's
rendering are exact on the live tree on the default `nix develop` path with the tree dirty, the
noise never reaches a fence, no failure path puts a byte on stdout, the temp directory never
survives, no traversal is accepted, the probes are in the body, and 26 of 27 mutants die. The one
survivor is the call-site twin of a pin the pa6 review itself specified as a heading check, and its
heading twin dies — unfinished coverage, not a test that cannot fail.

`plan_defect: none`. §P2b named the hazard, the mechanism and the four discriminating mutations
precisely enough that the implementer built the right thing; the nine minors are all narrower than
the contract's own clauses, and MINOR-1's calendar-validity gap is the only one where the plan's
word ("malformed") admitted the narrower reading the implementer took.

For the follow-up (no fix round owed — fold into P8 or a later touch of this file): route the
after-the-check failures through `run_hard`'s exit-3-and-name path (MINOR-2), notice an empty M10 or
START HERE block instead of printing an empty fence (MINOR-3), validate `--since`/`--date` as
calendar dates (MINOR-1), and pin M7's `--today` at the call (MINOR-4).
