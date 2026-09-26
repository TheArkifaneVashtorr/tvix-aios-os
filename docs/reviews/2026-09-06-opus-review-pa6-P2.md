---
plan_defect: missing-case
plan_defect_secondary: implementer
mutants_total: 18
mutants_killed: 10
mutants_outside_named: 8
reviewer: opus
majors: 6
minors: 9
---
# Opus gate — seat run pa6, task P2 — REJECTED

## Summary

`factory-plan-brief.sh` composes the packet in the contracted order — thirteen `## M<n>` parts,
then FIELD, OPERATOR, TARGET, RUBRIC, CHECKLIST, RULES — refuses a broken graph with an empty
stdout and runs nothing past `check`, and the `factory_py` seam is defined exactly once. All
eight bats cases are load-bearing: every one of the nine plan-named mutants dies. The checks are
green (unit 368 ok, lint, the hook, MAP reproduces, `bats-and-chain`), the subject is
byte-identical, the red is real in both directions.

Three MAJORs stand against it.

**MAJOR-1 — the packet reports false facts on the default interpreter path.** Every `factory_py`
capture uses `2>&1`, and the default interpreter is `factory_python3` = `nix develop -c python3`,
whose stderr carries flake warnings. On a dirty tree M3's byte count counts those warning bytes as
graph JSON, M7 never prints the contracted `silent (exit 0)`, and M2/M4/M5 attribute a
`warning: Git tree … is dirty` line to the tool. The script's own M1 comment (lines 124–127) names
this exact hazard and defends M1 against it; the other five parts were left open. No test can catch
it: the fixture always sets `FACTORY_PYTHON3_CMD` to a bare python.

**MAJOR-2 — exit 2 with a partial packet on stdout.** FIELD's `sed -n '2,17p' factory-integrate`
(line 244) and its START HERE `awk` (line 253) carry no `|| true` and neither file is in the exit-3
mandatory list. A tree without one of them prints 12 KB of packet, an unterminated `~~~` fence and
no OPERATOR/TARGET/RUBRIC/CHECKLIST/RULES, then exits 2 — the code the contract reserves for
"a refusal with nothing on stdout". `~/flakes/dsh-harness` (Assumption 11: no `docs/`) is exactly
such a tree, and P8 runs a planning seat from this script.

**MAJOR-3 — commit-convention breach.** §P2 Step 3 requires both live-probe outputs pasted, and the
gate convention requires them in the commit body. The body carries neither.

## The packet (shape table)

Fixture: the bats pattern, rebuilt under `<scratch>/fix1` (real `tasks.py`/`claims.py`/`evidence.py`,
a one-task `E1` plan, fake `ritual.sh`/`session-start.sh`, a spec carrying **both** a three-backtick
fence and a `~~~` line). `FACTORY_PYTHON3_CMD=<devShell python>`.

| item | expected | observed | exit |
|---|---|---|---|
| header | dated once, at the top | `# Planning packet — 2026-09-06T08:28:37Z — spec docs/superpowers/specs/x-design.md — out docs/reviews/plan-drafts/x-probe.md` (line 1) | 0 |
| thirteen headings | once each, ascending | `grep -c '^## M'` = 13; `m_order` = M1…M13 | 0 |
| TS lines | RFC3339 Z | `TS: 2026-09-06T08:28:37Z` under every part | 0 |
| fences | `~~~`, unclosable by three backticks | spec's ```` ``` ```` line sits in TARGET (unfenced) and every `~~~` fence is intact | 0 |
| later sections | FIELD, OPERATOR, TARGET, RUBRIC, CHECKLIST, RULES | that order, once each | 0 |
| RULES | §P2's nine clauses | all nine present (lines 335–347); `write only <out>` and the plan-drafts restriction are merged into one bullet — a rendering of the plan's prose, not a byte-copy (the plan gives no literal block) | 0 |

Commands, diffed against §P2 (heading text after `## M<n> — `):

| part | §P2 | script | verdict |
|---|---|---|---|
| M1–M5 | `<py> pkgs/evidence/tasks.py --root . check\|brief\|json\|waves --repo nixos-agent-env --json\|conflicts` | identical, `<py>` expanded to the interpreter | ok |
| M6 | `evidence bundle --markdown` | identical | ok |
| M7 | `<py> pkgs/evidence/claims.py validate docs/ledger/claims.toml --today <date> --repo-root .` | identical | ok |
| M8 | `bash tools/ritual.sh inflight <tree>` | identical | ok |
| M9 | `bash tools/session-start.sh <tree>` | identical | ok |
| M10 | the `## Checks` section of `docs/MAP.md` | `the ## Checks section of docs/MAP.md` | ok |
| M11 | `cat docs/ledger/routing.toml` | identical | ok |
| M12 | `git log --since=<since> --format='%ci%x09%s' \| head -80` | identical | ok |
| M13 | `tools/factory/seat/factory-brief …/2026-09-05-evidence-store.md E1` | `bash tools/factory/seat/factory-brief …` (line 222) | MINOR-7 |

M3's rendering is `826 bytes` where `… json \| wc -c` is `827` — `$( )` strips the trailing newline
and `printf '%s'` does not restore it. Independent of MAJOR-1, and in the same direction as it.

## The refusal

| case | expected | observed | exit |
|---|---|---|---|
| dangling `**dependsOn:** Q9` | exit 2, stdout empty, contracted stderr + M1's output, recorder saw only `check` | `stdout bytes: 0`; stderr `factory-plan-brief: refusing — the graph is not sound:` / `tasks: nixos-agent-env/E1 dependsOn Q9: unknown key`; recorder file holds exactly one line, `pkgs/evidence/tasks.py --root . check` | 2 |
| `FACTORY_PYTHON3_CMD=false` (tasks.py unrunnable) | must not print a partial packet as if sound | fails **closed**: exit 2, stdout 0 bytes — but the diagnosis is blank (`refusing — the graph is not sound:` followed by an empty line), so an operator is told the graph is broken when the interpreter is | 2 |
| M7 non-silent (a claim past `review_by`) | contract: only M1 refuses | packet prints in full, 13 M-headings, M7's six `claims: …` lines in a fence | 0 |
| `<out>` outside plan-drafts / absolute | exit 2, stdout empty | both: `factory-plan-brief: out must be under docs/reviews/plan-drafts/`, 0 bytes | 2 |
| `<spec>` outside specs/ | exit 2, stdout empty | `factory-plan-brief: spec must be under docs/superpowers/specs/`, 0 bytes | 2 |
| `docs/MAP.md` missing | exit 3, stdout empty | `factory-plan-brief: no such command: docs/MAP.md`, 0 bytes | 3 |
| **`factory-integrate` missing** | exit 2 ⇒ nothing on stdout | **12,192 bytes on stdout**, 13 M-headings, FIELD's fence opened and never closed, six sections absent; stderr `sed: can't read tools/factory/seat/factory-integrate` | **2 (MAJOR-2)** |
| `docs/OPERATIONS.md` missing | same | 13,537 bytes on stdout, same shape; `awk: fatal: cannot open file 'docs/OPERATIONS.md'` | **2 (MAJOR-2)** |
| `--date notadate` | contract has 0/2/3 | `date: invalid date 'notadate - 7 days'`, stdout empty, **exit 1** (undocumented; `set -e` on the substitution) | 1 |

## FIELD and the live anchors

Against the live tree, each anchor found with its `grep -n` line:

```
plan=       tools/factory/seat/factory-task:70:plan=${FACTORY_PLAN:-$repo_path/docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md}
REFUSED     tools/factory/seat/factory-integrate — (no match; P11 has not landed)
dispatch    tools/factory/seat/factory-dispatch:198:  printf 'factory-dispatch: run %s plan %s groups: %s\n' …
START HERE  38 lines
```

The script greps **neither** P11's form nor main's: it greps the bare string `plan=` (line 235), so
it prints whatever the file holds. P11 rule 1 replaces the default with `plan=$FACTORY_PLAN`, which
the same grep still matches, and adds the `REFUSED` line the currently-empty grep will then fill in.
No stale anchor is possible either way; both greps carry `|| true`, so the empty `REFUSED` result is
printed as an empty result rather than dying. This is the right shape.

## TARGET, the log filter, the seam

TARGET (`wc -w`, boundaries at 1,500/4,000):

| words | expected | observed |
|---|---|---|
| 1500 | `words: 1500`, `size: S` | as expected |
| 1501 | `size: M` | as expected |
| 4000 | `size: M` | as expected (`-le 4000`) |
| 4001 | `size: L` + `refuse: an L spec is split into sub-project plans before any task is typed` | as expected |
| live spec | — | `words: 1682`, `size: M` (matches Assumption 13's 1,682) |

The log filter (`awk RS=""`, line 256–265): a paragraph is printed when its **first line** matches
`[0-9]{4}-[0-9]{2}-[0-9]{2}` anywhere and that date sorts `>= --since`. A first line whose date sits
mid-line is therefore **included** (my fixture's `midline paragraph with a date 2026-09-05 after the
first word` printed) — which is what §P2 says ("whose first line carries a date"), not what a
stricter reading would give. A paragraph whose date is on a later line is excluded. A malformed
`--since` is silent: `git log --since=notadate` in M12's heading, and the string comparison
`"2026-09-05" >= "notadate"` is false for every paragraph, so the board-log block empties with no
warning (MINOR-4).

The seam: `grep -rn 'factory_py()' tools/factory/seat/` → exactly one hit,
`tools/factory/seat/factory-lib.sh:59`. `factory-dispatch` keeps a comment where the old copy was
(lines 86–88) and calls the shared one at :135 and :208. `FACTORY_PYTHON3_CMD` honoured: every
fixture run above used it. Without it: the live probe's M1 heading reads
`## M1 — nix develop -c python3 pkgs/evidence/tasks.py --root . check`, i.e. `factory_python3`.
`tests/unit/82-factory-dispatch.bats` — 15/15 ok.

## Live probe

Read-only audit first: the script opens nothing for writing; it `cd`s into the tree and runs only
`factory_py tasks.py|claims.py`, `evidence bundle --markdown`, `bash tools/ritual.sh inflight`,
`env -u FACTORY_RUN bash tools/session-start.sh`, `awk`/`sed`/`grep`/`cat`/`wc`, `git log`, and
`bash tools/factory/seat/factory-brief`. One caveat, reported as MINOR-3: `tools/ritual.sh` line 285
`rm -f -- "$pfile"` reaps stranded `.pid`/`.gate` markers under `$FACTORY_ROOT/runs` (dead pid **and**
mtime older than 7,200 s). I checked before running: the only markers present held **live** pids
aged 734 s, so neither condition could fire, and the after-diff proves nothing was removed.

```
$ env -u FACTORY_PYTHON3_CMD FACTORY_TOOLBOX_REPO=/home/dalhaka/nixos-agent-env \
    bash <clone>/tools/factory/seat/factory-plan-brief.sh \
    docs/superpowers/specs/2026-09-04-helm-home-design.md \
    docs/reviews/plan-drafts/2026-09-07-helm-home-1-probe.md
exit=0   elapsed ≈ 8 s (TS M1 08:40:26 → RULES 08:40:33)
wc -c            : 168611
grep -c '^## M'  : 13
```

```
# Planning packet — 2026-09-06T08:40:25Z — spec docs/superpowers/specs/2026-09-04-helm-home-design.md — out docs/reviews/plan-drafts/2026-09-07-helm-home-1-probe.md
## M1 — nix develop -c python3 pkgs/evidence/tasks.py --root . check
TS: 2026-09-06T08:40:26Z
checkEmpty: true
```

M7, on the same run — **not** the contracted `silent (exit 0)`:

```
## M7 — nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06 --repo-root .
TS: 2026-09-06T08:40:28Z
~~~
warning: Git tree '/home/dalhaka/nixos-agent-env' is dirty
~~~
```

RUBRIC and CHECKLIST do extract on the real tree (`### 5.1 The rubric (14 rows, 0–3 each, 42 points)`
and `## Appendix A — the eight questions every section answers before it ships`) — a path no test
covers (MINOR-2).

Nothing written: `git -C /home/dalhaka/nixos-agent-env status --porcelain` before/after differs only
by three staged files the **orchestrator** committed mid-probe (HEAD moved off `3937d98`), and the
`.pid`/`.gate` listing under `~/factory/runs` differs only by one **addition**
(`pa10`/`pb3a` launches) — no deletion, no modification. `docs/reviews/plan-drafts/` still does not
exist; no `2026-09-07-helm-home-1-probe.md` anywhere.

Deterministic reproduction of MAJOR-1 (a scratch clone of this branch, one whitespace change to make
the tree dirty, `FACTORY_PYTHON3_CMD` unset):

```
## M3 — nix develop -c python3 pkgs/evidence/tasks.py --root . json
575709 bytes                      <- true: `… json | wc -c` = 575582  (127 bytes of nix stderr)
## M7 — … claims.py validate …
~~~
warning: Git tree '…/red' is dirty
~~~                               <- contract: `silent (exit 0)`
```

The same warning line is folded into M2's brief, M4's waves JSON and M5's conflicts, inside their
fences, presented as the tool's output.

## Tests and mutants

Eight cases, all green; each is load-bearing (every one is killed by at least one mutant below).
18 mutants applied → bats → reverted; 10 killed, 8 survived.

| # | mutant | result | killed by |
|---|---|---|---|
| 1 | M13 emitted before M12 | KILLED | 1 (order) |
| 2 | M1's exit ignored (`if true`) | KILLED | 2 (refusal) |
| 3 | M2 run before deciding | KILLED | 2 (recorder saw `brief`) |
| 4 | die on missing `evidence` | KILLED | 1, 3 |
| 5 | `-le 1500` → `-lt 1500` | KILLED | 4 |
| 6 | accept any `<out>` path | KILLED | 5 |
| 7 | print the whole board log | KILLED | 6 |
| 8 | RULES `factory-brief <draft> <KEY>` sentence dropped | KILLED | 8 |
| 11 | M13 pointed at a key without `E1` | KILLED | 7 |
| 19 | `## OPERATOR` heading renamed | KILLED | 1 |
| 9 | `~~~` fences → three backticks | **SURVIVED** | — |
| 10 | header date dropped | **SURVIVED** | — |
| 12 | every `TS:` line dropped | **SURVIVED** | — |
| 13 | M4's `--repo nixos-agent-env` → `--repo WRONGREPO` | **SURVIVED** | — |
| 14 | M7's `--today "$today"` dropped | **SURVIVED** | — |
| 15 | M9's `env -u FACTORY_RUN` dropped | **SURVIVED** | — |
| 17 | M10 emits nothing for the Checks section | **SURVIVED** | — |
| 18 | FIELD's START HERE block dropped | **SURVIVED** | — |

All nine plan-named mutants die. The eight survivors are contract clauses the plan's eight cases
never asked to be pinned; I verified each behaviour is in fact **correct** in the artifact by direct
observation (header line 1; `TS:` under every part; `--repo nixos-agent-env` in M4's heading;
`--today 2026-09-06` in M7's; `FACTORY_RUN=[unset]` printed by a fake session-start.sh run with
`FACTORY_RUN=pa6zzz` in the environment; M10's three check names; the 38-line START HERE block;
`~~~` throughout). So: not vacuous tests, but unpinned contract — MINOR-1, with the pins named.

## Checks

| check | result |
|---|---|
| `shellcheck factory-plan-brief.sh factory-lib.sh factory-dispatch` | clean |
| `shfmt -d -i 2 -ci factory-plan-brief.sh` | no diff |
| `bats tests/unit/83-plan-brief.bats 82-factory-dispatch.bats 80-seat-driver.bats` | 8 + 15 + 45 = 68 ok |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | ok 1..368, 57 s |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | exit 0 |
| `githooks/pre-commit` (delivered tree, post-commit) | exit 1 — regenerates the board queue block |
| `githooks/pre-commit` (base + this change **staged**, as the seat ran it) | **exit 0** |
| `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | reproduces exactly |
| `bash tests/lint/bats-and-chain.sh` | exit 0 |
| `tasks.py --root . check` | silent, exit 0 |

The post-commit board staleness is not a defect of this branch: `tasks.py check --board` is clean at
the base `be43169`, and it is the P2 commit's own landing that moves the derived queue. Run as the
seat ran it — the change staged, the commit not yet made — the gate is green. No board commit is
owed by the task.

## Red before green

```
$ git checkout be43169 && git show task/P2:tests/unit/83-plan-brief.bats > tests/unit/83-plan-brief.bats
$ nix develop -c bats tests/unit/83-plan-brief.bats
1..8
not ok 1 factory-plan-brief composes the packet in order (P2 a)
#   `[ "$status" -eq 0 ]' failed
… all eight not ok; BW01: exited with code 127, indicating 'Command not found'
```

The seam, separately: base `factory-lib.sh` (no `factory_py`) + branch `factory-dispatch` →
`tests/unit/82-factory-dispatch.bats` 8 of 15 fail (`ok 5, 6, 9, 10, 11` are the arms that die before
reaching python). Restoring the full branch tree: 8 + 15 ok.

## Findings

**MAJOR-1 — nix's stderr is folded into five mechanical parts; M3's byte count and M7's rendering are
wrong on the default path.** `tools/factory/seat/factory-plan-brief.sh:139,145,151,157,173` — every
capture is `$(factory_py … 2>&1 || true)`, and the default interpreter is
`factory-lib.sh:51` `factory_python3() { (cd "$FACTORY_TOOLBOX_REPO" && nix develop -c python3 "$@"); }`.
Reproduced on a dirty clone of this branch:

```
## M3 — nix develop -c python3 pkgs/evidence/tasks.py --root . json
575709 bytes      # `nix develop -c python3 pkgs/evidence/tasks.py --root . json 2>/dev/null | wc -c` = 575582
## M7 — nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06 --repo-root .
~~~
warning: Git tree '…' is dirty
~~~
```

and on the live tree in the probe above. §P2: M3 is "the byte count only (`wc -c`)", M7 is
"(silent → `silent (exit 0)`)". The script's own M1 comment (lines 124–127) identifies the hazard —
"its diagnostics go to stderr, which nix develop also uses for its own 'dirty'/'nixfmt' warnings" —
and defends M1 alone. The fix is to capture stdout only (or to split streams and label stderr as
`interpreter noise:`) for M2–M5 and M7, keeping M1's exit-code gate as it is. This is the packet the
planner reads as fact; M3's number is silently wrong and M7 reports a clean validator as noisy.

**MAJOR-2 — exit 2 can carry a partial packet on stdout.**
`tools/factory/seat/factory-plan-brief.sh:244` (`sed -n '2,17p' tools/factory/seat/factory-integrate`)
and `:253` (the START HERE `awk`) have no `|| true`, and neither file is in the exit-3 mandatory list
at lines 90–93. Observed, `factory-integrate` removed from the fixture tree:

```
missing factory-integrate: exit=2  stdout_bytes=12192  M-headings=13
… last stdout lines:
$ sed -n "2,17p" tools/factory/seat/factory-integrate
(stderr) sed: can't read tools/factory/seat/factory-integrate: No such file or directory
```

The FIELD fence opened at line 232 is never closed and OPERATOR/TARGET/RUBRIC/CHECKLIST/RULES are
absent, yet the exit code is the one §P2 reserves for "a refusal with nothing on stdout". Removing
`docs/OPERATIONS.md` gives the same shape (13,537 bytes). This is reachable, not theoretical:
`~/flakes/dsh-harness` has no `docs/` at all (Assumption 11), and P8 runs a planning seat from this
script.

**MAJOR-3 — the commit body carries neither live-probe output.** `git log -1 --format=%b` on
`fa94a4a` runs from "factory-plan-brief <spec> <out> composes …" to the two trailers with no `wc -c`
number and no `grep -c '^## M'` = 13. §P2 Step 3: "prints a number and … prints 13 — paste both".
The gate convention: "the commit body carries the two live probe outputs". Both numbers exist (I
measured 168611 and 13 above), so nothing but the record is missing — but for the task whose whole
product is a truthful record, the record is the deliverable.

**MINOR-1 — eight contract clauses are unpinned** (mutants 9, 10, 12, 13, 14, 15, 17, 18 above).
Pins, one line each: the header line matches `^# Planning packet — [0-9]{4}-…Z — spec `; every
`## ` part heading is followed by a `TS: …Z` line; M4's heading contains `--repo nixos-agent-env`;
M7's contains `--today <date>`; a fake `session-start.sh` echoing `${FACTORY_RUN:-unset}` prints
`unset` when the caller exports it; M10's fence contains the fixture's check names; FIELD contains
the fixture's START HERE line; the packet contains `~~~` and no ```` ``` ```` fence of its own.

**MINOR-2 — RUBRIC and CHECKLIST are never exercised.** The fixture has no
`docs/superpowers/specs/2026-09-05-planning-agent-design.md`, so both render `unavailable: …` in all
eight tests (`factory-plan-brief.sh:310,323`). Both work live (shown above), but the two `awk`
extractions are unguarded by any assertion. Also: CHECKLIST is not in §P2's degradable list
(M6, M8, M9, OPERATOR, RUBRIC's file) yet degrades silently.

**MINOR-3 — "writes nothing" is not literally true.** `factory-plan-brief.sh:7-8` and
`tools/factory/seat/README.md` ("It **prints** the brief to stdout and writes nothing") — but M8 runs
`tools/ritual.sh inflight`, whose `inflight_stdout` reaps stranded markers
(`tools/ritual.sh:285` `rm -f -- "$pfile"`), and M9's `tools/session-start.sh:145` calls the same
function. The deletions are idempotent housekeeping on dead-pid, >2 h-old `.pid`/`.gate` files under
`$FACTORY_ROOT/runs`, and nothing was reaped in my probe — but the claim, and §P2's "read-only"
framing of M8/M9, should say so.

**MINOR-4 — a malformed `--since` degrades silently; `--date` exits 1.**
`--since notadate` → M12's heading reads `git log --since=notadate …` and the board-log filter
(line 262, `d >= since` as a string) drops every paragraph without a word. `--date notadate` →
`date: invalid date 'notadate - 7 days'` and exit 1 from `set -e` on line 67 — a code the contract
does not list.

**MINOR-5 — the path guards are prefix matches only.**
`docs/reviews/plan-drafts/../../../etc/x.md` is accepted (exit 0; the packet's header and RULES then
name it), as is a traversing `<spec>` that `cat`s a file outside the tree into TARGET.
`factory-plan-brief.sh:72-85`.

**MINOR-6 — `2>/dev/null` on three of the script's own extractions** (`:265` board log, `:310`
rubric, `:323` checklist) makes an unreadable file indistinguishable from an empty section.

**MINOR-7 — M13's heading is not the contracted string.** `factory-plan-brief.sh:222` prints
`M13 — bash tools/factory/seat/factory-brief …`; §P2 spells it without `bash`. The reason is sound
and documented at lines 219–221 (checks.unit's sandbox has no `/usr/bin/env`), the heading is exactly
the command that ran, and M8/M9 are contracted **with** `bash` — so it reads as an improvement, not a
lie. Recorded so the plan text and the script can be brought into line.

**MINOR-8 — M6 is not scoped to `FACTORY_TOOLBOX_REPO`.** `evidence bundle --markdown` reported the
live host's repo heads and Helm state while the packet's tree was a scratch fixture.

**MINOR-9 — M3's count is one byte short even without MAJOR-1** (`$( )` strips the trailing newline;
`printf '%s'` does not restore it): fixture observed `826 bytes`, `… json | wc -c` = `827`.

## Verdict

REJECTED. Three MAJORs: the packet misreports M3's byte count and M7's rendering (and pollutes
M2/M4/M5) whenever the tree is dirty on the default interpreter path — the very "lies to the
planner" failure this task exists to prevent, in the one part the author already knew how to defend;
an exit 2 that can carry 12 KB of partial packet with an unterminated fence when a FIELD source file
is absent, which is the shape of `~/flakes/dsh-harness` that P8 will point this script at; and a
commit body missing the two live-probe outputs the plan and the convention both require.

Everything else is sound and should be kept: the ordering, the refusal (empty stdout, only `check`
run), the single `factory_py` seam, the future-proof FIELD greps, the size rule, the fence choice,
and eight tests that all bite. `plan_defect: missing-case` — §P2's test list never asks for a case on
the default (`nix develop`) interpreter path, which is the only path the operator and the P8 seat
will use, nor for any assertion on M3's or M7's rendering; secondary `implementer`, because the M1
comment shows the hazard was seen and then applied to one part of six.

Fix round P2b: capture stdout only for M2–M5 and M7 (M1 keeps its exit-code gate), with a test that
drives the script through a wrapper that prints to stderr and asserts `silent (exit 0)` and an exact
byte count; guard FIELD's two unguarded commands so a missing source degrades under its own heading
instead of dying mid-packet, with a test that a tree lacking `docs/OPERATIONS.md` still ends in
`## RULES`; paste both live-probe outputs into the commit body; and fold MINOR-1's eight pins.
