---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run fd1, task FD1 — REJECTED

## Summary

`factory-dispatch` is well built in most respects: one commit on `437da0a` with the
byte-identical subject and both trailers, the script executable, no forbidden file
touched, `unit`/`lint`/the gate/shellcheck/`bats` all green, red proven, and the
injection guard genuinely sound (nine crafted lines probed: `$(`, backtick, `;`, `\`,
`$IFS` all refused; nothing that passes the class can escape `eval "set -- …"`).

It is rejected for one defect in the primary launch path. The plan's Fact ("the first
line is the next wave") is wrong — `tasks.py waves` prints **one group per line across
all waves** with no wave separator (`pkgs/evidence/tasks.py:660-662`), so the
implementer silently re-derived the wave boundary in bash (`first_wave_groups`,
`dep_roots`, `chain_root`) by re-parsing `**dependsOn:**` out of the plan file. That
re-derivation reads `<plan-file>` resolved **relative to the caller's cwd**, never
joined to `<repo-path>`, and when the file is not readable it does not fail: `awk`
prints an error, `dep_roots` yields nothing, every open task is treated as
dependency-free, and the dispatcher emits a wave containing **blocked** tasks and
exits 0. Reproduced below: `"A1" "A2"` offered as one wave with A1 unlanded. Without
`--dry-run` that launches a seat for a task whose dependency has not landed — the
exact failure the feature exists to prevent — and the factory's own documented shape
(seats run from `~/factory/ws/…`, base clones under `~/factory/base/…`, `<repo-path>`
elsewhere) makes the wrong-cwd case ordinary, not exotic.

Secondary: the deviation itself is undisclosed in `FACTORY-RESULT`/`FACTORY-NOTES`
(it appears only in a script comment and the transcript's closing prose), and two
explicit interface requirements — the `dispatch.log` write and the stderr wave log —
have no test at all (both mutations survived the full suite).

## Checks

Throwaway clone of `/home/dalhaka/factory/ws/fd1/FD1` at `task/FD1` (`837a59b`),
`XDG_CACHE_HOME` under the session scratchpad, tooling only via `nix develop -c`.

| Check | Result |
| --- | --- |
| one commit on base `437da0a` | pass — `837a59b` only |
| subject byte-identical to the plan | pass |
| `Co-Authored-By: Claude Fable 5.1` trailer | pass (plus `Generated-By:`) |
| `tools/factory/seat/factory-dispatch` mode | pass — `100755` |
| Global Constraints (no `80-seat-driver.bats`, `factory-lib.sh`, `flake.nix`, `githooks/pre-commit`) | pass |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass (rc 0) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass (rc 0) |
| `nix develop -c githooks/pre-commit` | pass (rc 0) |
| `nix develop -c shellcheck tools/factory/seat/factory-dispatch` | pass (rc 0) |
| `nix develop -c bats tests/unit/82-factory-dispatch.bats` | pass — 7/7 |
| hard-rule scan of the diff (`sudo`, `nixos-rebuild`, `systemctl`, network) | clean |

Fourth file (the stat names four; the plan names three touches): **`docs/MAP.md`**,
one line, `tests/unit — 12 files` → `13 files`. Forced by the section's own acceptance
check: `lint` runs `python3 pkgs/evidence/repomap.py --root . check` (`flake.nix:925`),
which fails on a stale MAP. Acceptable — but disclosed only in the transcript's closing
prose, not in `FACTORY-NOTES`.

Named acceptance coverage, from the `unit` derivation log
(`/nix/store/bjrk6xpaa29ss7qw6wcdnzkwgw6m1kr1-unit-tests.drv`, tests 140–146): **five
of the seven FD1 tests skip** under `checks.unit` (a, b, c, d, g), leaving only (e) and
(f). The skip is real and forced — the `unit` sandbox copies `tests/`, `pkgs/helm`,
`tools/factory/seat`, `tools/session-start.sh` and no `pkgs/evidence` (`flake.nix:1748-1770`),
and FD1 may not edit `flake.nix`. It is disclosed in the bats header. But it means the
plan's own acceptance gate proves almost nothing about this feature; all real evidence
below comes from `nix develop -c bats`.

## Red before green

`tools/factory/seat/factory-dispatch` moved aside, `nix develop -c bats tests/unit/82-factory-dispatch.bats`:

```
1..7
not ok 1 … (FD1 a)   not ok 2 … (FD1 b)   not ok 3 … (FD1 c)   not ok 4 … (FD1 d)
not ok 5 … (FD1 e)   not ok 6 … (FD1 f)   not ok 7 … (FD1 g)
```

All seven fail with the script absent; restored, tree clean.

## Mutation table

Applied to the script, whole file (or the named `-f` filter) run under
`nix develop -c bats`, reverted with `git checkout --` after each.

| # | Mutation | Expected catcher | Result |
| --- | --- | --- | --- |
| M1 | regex validation replaced by `if false` (injection guard dropped) | f | **caught** — `not ok 6 … (FD1 f)` |
| M2 | `--dry-run` prints but no longer `exit 0` (dry run still launches) | a | **caught** — `not ok 1 … (FD1 a)` |
| M3b | wave failure captured but `exit 0` returned (code not propagated) | g | **caught** — `not ok 1 … (FD1 g)` |
| M4 | failure swallowed, `--all` continues past it | g | **caught** — never green; rc 124 (the loop never terminates: see finding F6) |
| M5 | `FACTORY_PLAN=` prefix removed from the launch | b | **caught** — `not ok 1 … (FD1 b)` |
| M6 | second raw waves line taken instead of the derived first wave | a | **caught** — `not ok 1 … (FD1 a)` |
| M7 | `resolve_repo_name` returns the first row regardless of path | e | **caught** — `not ok 1 … (FD1 e)` |
| M8 | `dispatch.log` append replaced by `: "$dispatch_log"` | — | **SURVIVED** — 7/7 still ok |
| M9 | trailing `brief` query replaced by `:` | b | **caught** — `not ok 1 … (FD1 b)` |
| M10 | `factory_log` wave line replaced by `:` (stderr log dropped) | — | **SURVIVED** — 7/7 still ok |

Injection-guard probe, the regex evaluated directly on nine lines:

```
PASS-REGEX: "A1" "B1"          PASS-REGEX: "A1 A2" "B1"
REFUSED:    rm -rf /           REFUSED:    "$(touch /tmp/pwn)"
REFUSED:    "`touch /tmp/pwn`" REFUSED:    "A1"; touch /tmp/pwn
REFUSED:    "A1" "B1" $IFS     PASS-REGEX: "--x" "-rf"     PASS-REGEX: "A1""B1"
```

`"` is outside the class, so quotes are always balanced and `eval "set -- $line"`
cannot break out; `$`, backtick, `;`, `\`, newline are all excluded. The guard holds.
`"-rf"` passes the class, but `set --` makes it positional and it only ever reaches
`factory-wave` as a group word — a hardening nit, not a hole.

## Real data

From the clone, read-only, `FACTORY_ROOT` pointed at the scratchpad:

```
$ tools/factory/seat/factory-dispatch fdx /home/dalhaka/nixos-agent-env \
    docs/superpowers/plans/2026-09-05-session-context.md --dry-run
evaluation warning: nixfmt-rfc-style is now the same as pkgs.nixfmt which should be used instead.
would run: factory-wave fdx /home/dalhaka/nixos-agent-env "G11"
RC=0
```

No wave launched: `pgrep -f 'factory-wave fdx'` is empty (the one PID the first probe
returned was the probing shell's own command line; `ps` on it after exit shows nothing).
`~/factory/runs/fdx` does not exist and the scratch `FACTORY_ROOT` was never created —
the dry-run path returns before the runs directory is made. Unrelated `factory-wave`
processes for runs `og1` and `sc5` were already running on the host and were not touched.

Note for the board: that same `sc5` wave is currently running **G11**, and the
dispatcher still offers G11 as schedulable — `tasks.py` derives "ran" from a `.result`
file, which does not exist until a seat finishes, so an in-flight task reads `ready`.
Pre-existing in `tasks.py`, not introduced here, but the message this task ships
("all landed, in flight, or blocked") now asserts an exclusion the graph does not make,
and `factory-dispatch` is the tool that will be re-run in a loop.

## Findings

**F1 (blocking) — a wrong or unreadable `<plan-file>` silently produces an over-broad
wave containing blocked tasks, exit 0.** `plan_file` (line 65) is resolved against the
caller's cwd and never joined to `<repo-path>`; `dep_roots` (line 129) feeds it to
`factory_extract_task`. When the file is not there, `awk` errors to stderr, `dep_roots`
returns nothing, every open task passes the `open_dep` test, and `first_wave_groups`
emits every group. Reproduced with a two-task fixture (`A1`, then `A2 dependsOn A1`,
nothing landed):

```
$ # cwd = the toolbox clone, plan given repo-relative (the README's own shape)
$ factory-dispatch r1 <fixrepo> docs/superpowers/plans/plan.md --dry-run
awk: … fatal: cannot open file `<clone>/docs/superpowers/plans/plan.md' …
would run: factory-wave r1 <fixrepo> "A1" "A2"
exit=0
```

and identically with `/no/such/dir/plan.md`. Correct path gives `"A1"` alone. Without
`--dry-run` this launches a seat for A2 while A1 is unlanded, and hands `FACTORY_PLAN`
a path that does not exist. `set -euo pipefail` does not catch it: the failing `cd` at
line 65 is one of two command substitutions in the assignment, so the assignment's
status is `basename`'s. Fix: resolve `<plan-file>` against `<repo-path>` when it is
relative, and `factory_die` when the resolved plan is not a readable file — with a test
that a bad plan path refuses rather than launching.

**F2 (blocking, process) — the plan's algorithm was replaced without disclosure.** The
plan's Fact and Interfaces both say "take the FIRST line as the wave". The real
`tasks.py` prints one group per line over all waves, so the literal reading would have
launched one group of the wave. Choosing correctness over the letter is right; doing it
by re-implementing `chain_root` and `dependsOn` parsing in bash — a second, weaker copy
of graph semantics that can disagree with `tasks.py` (F1 is exactly that disagreement) —
is a design change that belonged in the result line and a plan/decision correction, not
only in a code comment (lines 148-152). `FACTORY-NOTES` mentions neither this nor the
`docs/MAP.md` touch.

**F3 (major) — two spec'd interface requirements have no test.** "Every launched wave is
logged to stderr with its groups and to `~/factory/runs/<run>/dispatch.log`." M8 and M10
both survived the full suite: delete either write and all 7 tests stay green. Add
assertions on `$FACTORY_RUNS/<run>/dispatch.log` content and on the stderr line.

**F4 (minor) — dead code around exit propagation.** Lines 251-255 (`wave_rc=$?`,
`if … exit "$wave_rc"`) are unreachable: `set -e` already exits at line 250 with the
wave's status, which is why propagation works. M3b had to neutralise `set -e` to expose
it. Either drop the block or make the launch explicitly tolerant (`|| wave_rc=$?`) so
the written control flow is the real one.

**F5 (minor) — a failing graph query is indistinguishable from "nothing schedulable".**
`wave_line=$(next_wave_line) || wave_line=` (line 214) turns any `tasks.py` crash,
missing repo, or python failure into the reassuring "nothing schedulable … (all landed,
in flight, or blocked)" line and exit 0.

**F6 (minor) — `--all` has no progress guard.** If a wave exits 0 without changing any
task's state, the loop re-queries, gets the same wave, and relaunches forever. M4 turned
this into a hard hang (rc 124 at 90 s). A "same wave twice in a row → die" guard is cheap.

**F7 (nit) — `--repo-name NAME` is untested.** The override path (line 206) has no case
in the bats file; only the resolve-and-fail path (e) is covered.

## Deviations

- **Fourth file, `docs/MAP.md`** (one line, test count 12 → 13): forced by the `lint`
  acceptance check's `repomap.py check`. Acceptable; disclosure belonged in
  `FACTORY-NOTES` and was not there.
- **Wave derivation done in bash instead of "the first line"** (F2): forced by a wrong
  Fact in the plan, but undisclosed and the root of F1.
- **Five of seven tests skip under the named `unit` acceptance check**: forced by the
  sandbox's file set and the ban on editing `flake.nix`; disclosed in the bats header.
  The consequence — that `unit` is near-vacuous for this feature — should be carried on
  the board until `pkgs/evidence` is copied into the sandbox (RT2b owns `flake.nix`).
- **`2>/dev/null` in the diff**: two occurrences, both benign path/`git init` probes,
  neither on a gated command.

Gate work was confined to a throwaway clone, the session scratchpad and this file; the
implementer workspace was not touched, no wave was launched, and the clone's tree is
clean.
