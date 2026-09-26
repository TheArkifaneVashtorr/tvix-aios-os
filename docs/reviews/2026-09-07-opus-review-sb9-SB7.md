---
plan_defect: vacuous
plan_defect_secondary: wrong-fact
mutants_total: 8
mutants_killed: 5
mutants_outside_named: 3
---
# Opus gate — seat run sb9, task SB7 — REJECTED

## Summary

The three one-line list additions and the two runbook sentences are all present,
correctly spelled, and correctly placed; every acceptance check is green in a
fresh clone; the commit subject is byte-identical to the section's. Two of the
three refusal contracts (lane-submit's `--repo`, the wrapper's workspace boot)
are pinned by tests that I showed red on the base and green on the branch.

The third is not. Contract item 3's hook-guard arm — `"$TMPHOME/.codex/auth.json"`
joining the path list of *"hook-guard denies writes under the protected
prefixes"* — is a test that **cannot fail**. That path lies outside
`CLAUDE_PROJECT_DIR` (`$TMPHOME/ws`), so `hook-guard`'s outside-the-project rule
denies it whether or not `_protected_prefixes()` names `~/.codex`, and
`guard_denies()` asserts only `permissionDecision == "deny"`, never the reason.
I proved it: deleting the guard's `.codex` prefix leaves that test green
(`ok 1 hook-guard denies writes under the protected prefixes`), and a guard that
protects `~/.codex` only when `XDG_CONFIG_HOME` is unset passes *every* test the
section names (`59 passed`, `117 ok`). The section's own mutation target —
"~/.codex dropped from all three lists at once → … each of item 3's refusal
tests fails" — is therefore false for the guard's test.

The shipped guard behaviour is right (the deny reason does name the protected
path); it is the pin that is missing, and the plan prescribed the shape that
cannot pin it ("joins the path list"), so the defect class is `vacuous` with
`wrong-fact` secondary for the mutation-target sentence.

The orchestrator's question about the third mutant resolves in the section's
favour: the spelling `"~/.codex"` fails `shellcheck` SC2088 at the wrapper's
build (the seat's account is true — the `unit` check goes red before bats runs),
**and** with SC2088 suppressed the bats workspace-refusal test still fails on
its own. The section's sentence is a correct fact, merely not the first killer.

The plan file has no `## Assumptions` section; I read `## Global Constraints`
and `### SB7 (` in full.

Clone: `git clone -q --branch task/SB7 /home/dalhaka/factory/ws/sb9/SB7 …/gate-sb9-SB7`,
base `2c23cfc`, head `020e564`.

## Contract items

**Item 1 — the three list additions, each in its list's spelling shape, beside `~/.claude`.** MET.

- `pkgs/lane/lane-submit.py:54` — `    "~/.codex",`, directly after `"~/.claude",` (line 53).
- `pkgs/dsh-openrouter/hook-guard.py:414` — `                os.path.join(home, ".codex"),`, directly after the `.claude` join (413).
- `pkgs/dsh-openrouter/dsh-openrouter.sh:268` — `  "$HOME/.codex"`, directly after `  "$HOME/.claude"` (267).

**Item 2 — the agreement test names `~/.codex` explicitly.** MET.

`tests/lane/test_forbidden_lists_agree.py:40-42`:

```
    assert "/home/x/.codex" in lane_list
    assert "/home/x/.codex" in guard_list
    assert "/home/x/.codex" in bash_list
```

Placed after the three-way equality (line 31), so it fires on the drop-from-all-three
mutant. Red on base — see Red before green.

Normalisation still agrees: the test monkeypatches `HOME=/home/x` and deletes
`XDG_CONFIG_HOME` (`:22-23`), and `_protected_prefixes()`
(`pkgs/dsh-openrouter/hook-guard.py:406-423`) appends the XDG entry only when
that variable is set, so the new `.codex` entry lands in the HOME-relative block
and `norm()` maps all three spellings (`~/.codex`, `/home/x/.codex`,
`$HOME/.codex`) onto `/home/x/.codex`. `nix build .#checks.x86_64-linux.lane-unit --rebuild` → `59 passed`.

**Item 3 — one refusal test per list.**

- lane-submit: MET. `tests/lane/test_lane_submit.py:160-181`,
  `test_forbidden_prefix_home_codex` — `_agent_job_argv("~/.codex")` and
  `_agent_job_argv("~/.codex/sessions")`, `rc == 1`, `calls == []`,
  `"refusing" in err`, the same assertions as
  `test_forbidden_prefix_home_claude_and_strategy` (`:136-157`). Red on base.
  (Only the `refusing` assertion discriminates — MINOR-2.)
- the wrapper: MET. `tests/unit/70-dsh-openrouter.bats:107-117`, an exact mirror
  of `"refuses a workspace under ~/.claude before looking for a key"`
  (`:95-105`): status 3, `local-only` present, `no key` absent. Red on base.
- the hook guard: NOT MET in substance (MAJOR-1). The path
  `"$TMPHOME/.codex/auth.json"` is present at `tests/unit/70-dsh-openrouter.bats:715`,
  so the item is met to the letter, but the assertion cannot fail for any
  mutation of the guard's `~/.codex` protection.

**Item 4 — the two runbook sentences, nothing else.** MET.

`docs/runbooks/lanes.md:59` and `:183` are the only two hunks in the file
(`git diff --stat`: `docs/runbooks/lanes.md | 4 ++--`). Both now read `~/.claude`,
`~/.codex`, …. Neither line was re-wrapped (MINOR-3).

## Red before green

Base implementation files against the branch's tests
(`git checkout 2c23cfc -- pkgs/lane/lane-submit.py pkgs/dsh-openrouter/hook-guard.py pkgs/dsh-openrouter/dsh-openrouter.sh`),
then `nix develop -c pytest tests/lane -q`:

```
>       assert "/home/x/.codex" in lane_list
E       AssertionError: assert '/home/x/.codex' in {'/home/x/.claude', '/home/x/.config/openrouter', …}
tests/lane/test_forbidden_lists_agree.py:40: AssertionError
…
>       assert "refusing" in err
E       AssertionError: assert 'refusing' in 'lane-submit: --repo ~/.codex is not a directory\nlane-submit: --repo ~/.codex/sessions is not a directory\n'
tests/lane/test_lane_submit.py:180: AssertionError
=========================== short test summary info ============================
FAILED tests/lane/test_forbidden_lists_agree.py::test_the_three_local_only_lists_agree
FAILED tests/lane/test_lane_submit.py::test_forbidden_prefix_home_codex
2 failed, 57 passed in 7.98s
```

`nix develop -c bats tests/unit/70-dsh-openrouter.bats` on the same reverted tree:

```
not ok 6 refuses a workspace under ~/.codex before looking for a key
# (in test file tests/unit/70-dsh-openrouter.bats, line 111)
#   `[ "$status" -eq 3 ]' failed
ok 50 hook-guard denies writes under the protected prefixes
```

Note the last line: with `~/.codex` gone from **all three** lists, the guard's
refusal test is still green. That is the MAJOR.

Restored (`git checkout HEAD -- pkgs/`): `59 passed`, and bats `117 ok`, no `not ok`.

## Mutants

| # | mutation | named? | test that must kill | result |
|---|---|---|---|---|
| 1 | `"~/.codex"` dropped from `FORBIDDEN_REPO_PREFIXES` only | yes | agreement test | KILLED |
| 2 | `os.path.join(home, ".codex")` dropped from `_protected_prefixes()` only | yes | agreement test | KILLED |
| 3 | `"$HOME/.codex"` dropped from `forbidden=(…)` only | yes | agreement test (+ bats workspace) | KILLED |
| 4 | dropped from all three at once | yes | agreement membership + all three refusal tests | KILLED, but **not** by the guard's refusal test |
| 5 | bash entry spelled `"~/.codex"` | yes | bats workspace refusal | KILLED (shellcheck first; bats alone also kills it) |
| 6 | mutation 2, judged by the guard refusal test alone | no | `hook-guard denies writes under the protected prefixes` | **SURVIVED** |
| 7 | lane entry `"~/.codex/"` (trailing slash) | no | agreement + lane refusal | survived — equivalent mutant, no finding |
| 8 | guard appends `~/.codex` only when `XDG_CONFIG_HOME` is unset | no | every test the section names | **SURVIVED** |

Totals: 8 applied, 5 killed, 3 outside the named set.

**1** — `pytest tests/lane/test_forbidden_lists_agree.py`:

```
E       AssertionError: {'lane': [… no '/home/x/.codex' …], …}
E         Extra items in the right set:
E         '/home/x/.codex'
tests/lane/test_forbidden_lists_agree.py:31: AssertionError
```

**2** — same test, `Extra items in the left set: '/home/x/.codex'`. Reverted.

**3** — same test red, and `bats -f 'refuses a workspace under ~/.codex'`:

```
not ok 1 refuses a workspace under ~/.codex before looking for a key
#   `[ "$status" -eq 3 ]' failed
```

**4** — see Red before green: three of the four named killers fire; the guard's
does not (`ok 50`).

**5** — applied as `"~/.codex"` in `forbidden=(…)`. Raw, the devShell build fails:

```
> In /nix/store/…-dsh-openrouter/bin/dsh-openrouter line 280:
>   "~/.codex"
>    ^------^ SC2088 (warning): Tilde does not expand in quotes. Use $HOME.
error: Cannot build '/nix/store/…-dsh-openrouter.drv'.
```

so the seat's account is correct: `unit` (and any devShell command) goes red at
the wrapper's build, before bats runs. With `# shellcheck disable=SC2088` placed
before `forbidden=(` so the package builds, the bats test alone still kills it:

```
1..1
not ok 1 refuses a workspace under ~/.codex before looking for a key
# (in test file tests/unit/70-dsh-openrouter.bats, line 111)
#   `[ "$status" -eq 3 ]' failed
```

The section's sentence is a true fact — `realpath -m` does not expand the quoted
tilde — merely not the first killer. Nothing to correct in the section here.

**6** — guard's `.codex` line deleted, `bats -f 'hook-guard denies writes under the protected prefixes'`:

```
1..1
ok 1 hook-guard denies writes under the protected prefixes
```

**7** — `"~/.codex/"`: `Path(raw).expanduser().resolve()`
(`pkgs/lane/lane-submit.py:79`) normalises the trailing slash away, so the
refusal is unchanged and the agreement test's `norm()` rstrips `/`. Equivalent
mutant; `59 passed`. No finding.

**8** — `_protected_prefixes()` patched to
`if home and not os.environ.get("XDG_CONFIG_HOME", ""): prefixes.append(os.path.join(home, ".codex"))`
(the `.codex` entry removed from the unconditional block). The agreement test
deletes `XDG_CONFIG_HOME` (`:23`) so it still sees the prefix; the bats guard
loop is vacuous. Both suites green:

```
=== pytest lane ===  59 passed in 7.96s
=== bats 70 ===      117            (count of '^ok ' lines; no 'not ok')
```

A hook guard that stops protecting `~/.codex` in exactly the environment dsh
runs in ships fully green. Reverted.

## Checks

All in the fresh clone, `XDG_CACHE_HOME` under the scratchpad.

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.lane-unit -L --no-link --rebuild` | green — `lane-unit-tests> 59 passed in 7.83s` |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | green — `ok 494 …`, 1m27s |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | green |
| `nix develop -c githooks/pre-commit` | rc 1 on its one-shot board regeneration (`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`); after `git add docs/OPERATIONS.md`, rc 0. Anticipated by `## Global Constraints`; the drift is only SB7 leaving the derived queue, and the section forbids a board commit — the orchestrator's step, not a finding. |
| `nix develop -c ruff check pkgs/lane pkgs/dsh-openrouter tests/lane` | `All checks passed!` |
| `nix develop -c ruff format --check …` | `7 files already formatted` |
| `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc 0, no diff |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, rc 0 |
| `nix develop -c pytest tests/lane -q` | `59 passed` |
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 117 ok, 0 not ok |

## Touches and commit

Diff (`2c23cfc..020e564`), 7 files, 47 insertions / 2 deletions — every one inside
the section's list; nothing outside it, and `docs/MAP.md` needed no regeneration:

```
 docs/runbooks/lanes.md                   |  4 ++--
 pkgs/dsh-openrouter/dsh-openrouter.sh    |  1 +
 pkgs/dsh-openrouter/hook-guard.py        |  1 +
 pkgs/lane/lane-submit.py                 |  1 +
 tests/lane/test_forbidden_lists_agree.py |  7 +++++++
 tests/lane/test_lane_submit.py           | 23 +++++++++++++++++++++++
 tests/unit/70-dsh-openrouter.bats        | 12 ++++++++++++
```

The plan file is untouched; there is no board commit.

Exactly one commit, `020e564`. Subject byte-identical to the section's
(`cmp` against the literal: `SUBJECT BYTE-IDENTICAL`). The two trailers follow a
blank line and close the message:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run sb9)$
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>$
```

The body states the why in full but pastes neither the red nor the green output —
MINOR-1.

## Findings

**MAJOR-1 — the hook-guard refusal for `~/.codex` is pinned by a test that cannot fail.**
`tests/unit/70-dsh-openrouter.bats:715` (the added path) with
`tests/unit/70-dsh-openrouter.bats:638-648` (`guard_denies`) and `:27`
(`CLAUDE_PROJECT_DIR="$TMPHOME/ws"`).

The loop feeds `"$TMPHOME/.codex/auth.json"` while the project directory is
`$TMPHOME/ws`. `_edit_verdict` (`pkgs/dsh-openrouter/hook-guard.py:438-452`) has
two independent deny paths — the protected-prefix loop and the
resolves-outside-the-project check — and this path trips the second one on its
own. `guard_denies` asserts only `permissionDecision == "deny"`
(`:646`); the sibling helper that would discriminate, `guard_denies_reason`
(`:653-660`), is not used here. Evidence, guard's `.codex` prefix deleted:

```
$ nix develop -c bats -f 'hook-guard denies writes under the protected prefixes' tests/unit/70-dsh-openrouter.bats
1..1
ok 1 hook-guard denies writes under the protected prefixes
```

and with the whole change reverted in all three lists, the same test is `ok 50`
while the other two refusal tests go red. Mutant 8 shows the hole is reachable
by a plausible edit: a guard that protects `~/.codex` only when
`XDG_CONFIG_HOME` is unset passes `59 passed` / `117 ok`.

The shipped code is correct — driven directly, the guard denies with
`"refusing to edit/write …/.codex/auth.json: under protected path …/.codex"` —
so this is an unpinned contract, not a broken one. But the section's mutation
target ("dropped from all three lists at once → … each of item 3's refusal tests
fails") is false as written, and item 3's guard arm buys nothing.
Smallest fix: `guard_denies_reason "$(guard_payload write …)" "under protected path"`
for the codex path, or a case whose project dir is inside `~/.codex`.

Class: the plan authored the vacuous shape ("joins the path list"), so
`plan_defect: vacuous`, secondary `wrong-fact` for the mutation-target sentence.
The seat followed item 3 literally and is not at fault here.

**MINOR-1 — the commit body pastes no red and no green.**
`020e564` body. It claims `TDD: every new test shown red first`, which cannot be
true of the hook-guard path entry (MAJOR-1); no `pytest`/`bats` output is quoted,
as the convention requires.

**MINOR-2 — two of the four assertions in the new lane refusal test are non-discriminating.**
`tests/lane/test_lane_submit.py:172-178`. `~/.codex` is never created under the
fake `HOME`, so on the base tree `_submit` already returns 1 with no `systemctl`
call — `lane-submit: --repo ~/.codex is not a directory`. Only
`assert "refusing" in err` (`:180`) separates refused-by-prefix from
not-a-directory. This mirrors `test_forbidden_prefix_home_claude_and_strategy`
(`:136-157`) exactly, which is what item 3 asked for, so it is the plan's shape
rather than the seat's invention; the test does go red on the base.

**MINOR-3 — the two edited runbook lines were not re-wrapped.**
`docs/runbooks/lanes.md:59` (82 columns) and `:183` (87 columns), in paragraphs
whose other lines are 53-75 columns. Cosmetic; the `lint` check is green.

## Verdict

REJECTED on MAJOR-1. Everything else in the section is met and every named check
is green; the change is three correct one-line additions. What is missing is the
pin on the third of the three refusal contracts the section set out to establish
— and the section's own mutation ledger records a killer that does not exist.
Re-plan item 3's guard arm to assert the deny *reason* (or to put the project
directory inside `~/.codex`), and correct the mutation target. Record the third
mutant's fact as confirmed, with the note that `shellcheck` SC2088 fails the
wrapper's build before bats ever runs.
