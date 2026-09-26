---
plan_defect: none
mutants_total: 8
mutants_killed: 8
mutants_outside_named: 2
---
# Opus gate — seat run sb9f, task SB7b — APPROVED
## Summary

The fix round closes the MAJOR that rejected SB7 and all three of its MINORs.
The new bats case
`hook-guard denies a write under ~/.codex with the protected-path reason`
(`tests/unit/70-dsh-openrouter.bats:729-742`) pins the guard's third refusal by
its **deny reason**, not its decision: it is red on the base's implementation
files, red when the guard's `.codex` prefix is deleted, and — the point of the
whole round — red on the previous review's surviving mutant 8 (a guard that
protects `~/.codex` only when `XDG_CONFIG_HOME` is unset), which shipped fully
green under SB7. The lane refusal test now creates `fake_home/.codex` and
`fake_home/.codex/sessions` before submitting, so its `rc == 1` and
no-`systemctl` assertions discriminate the prefix rule from "not a directory" —
proved by mutating `lane-submit.py` alone and watching the test fail at
`assert rc == 1`, not at the `refusing` line. The two runbook lines are
re-wrapped under 76 columns with the word stream unchanged apart from the
inserted `` `~/.codex`, ``. The commit body pastes the red and the green, and
the red reproduces byte-for-byte in a fresh clone, down to `2 failed in 0.03s`.

All four mutants the section names go red, and SB7's five kills still die. Two
mutants I invented beyond the named set (the inverse `XDG_CONFIG_HOME` gate, and
the guard prefix narrowed to `~/.codex/sessions`) also die. I found no mutant
that survives.

Every acceptance check is green in a fresh clone; the commit subject is
byte-identical; every file in the diff is inside the section's `touches`; the
plan file is untouched and there is no board commit.

No production-code behaviour changed in SB7b, exactly as the commit body states:
the three one-line additions are carried verbatim from SB7 and the diff against
main shows `pkgs/` at `1 +` per file.

The plan file has no `## Assumptions` section; I read `## Global Constraints`
and `### SB7b (` in full, plus `### SB7 (` for the carried contract and the five
kills.

Clone: `git clone -q --branch task/SB7b /home/dalhaka/factory/ws/sb9f/SB7b …/gate-sb9f-SB7b`,
base `33d64c5`, head `4657018`, one commit.

## Contract items

**Carried from SB7 ("stand as carried").** All present and unchanged from the
round the previous gate accepted:

- `pkgs/lane/lane-submit.py:54` — `    "~/.codex",` after `"~/.claude",`.
- `pkgs/dsh-openrouter/hook-guard.py:414` — `                os.path.join(home, ".codex"),` after the `.claude` join.
- `pkgs/dsh-openrouter/dsh-openrouter.sh:268` — `  "$HOME/.codex"` after `  "$HOME/.claude"`.
- `tests/lane/test_forbidden_lists_agree.py:40-42` — the three membership assertions.
- `tests/unit/70-dsh-openrouter.bats:107-117` — the wrapper's workspace refusal.
- `docs/runbooks/lanes.md:59` and `:184` — the two enumerating sentences.

**Item 1 — a bats test beside the protected-prefixes loop, denying
`"$TMPHOME/.codex/auth.json"` with the protected-path reason via
`guard_denies_reason`, the reason naming `.codex`.** MET.

`tests/unit/70-dsh-openrouter.bats:729-742`, placed immediately after the
decision-only loop (`:711-728`):

```
@test "hook-guard denies a write under ~/.codex with the protected-path reason" {
  local payload input
  input='{"file_path":"'"$TMPHOME"'/.codex/auth.json"}'
  payload="$(guard_payload write "$input")"
  guard_denies_reason "$payload" "under protected path"
  guard_denies_reason "$payload" "$TMPHOME/.codex"
}
```

The helper's semantics (`tests/unit/70-dsh-openrouter.bats:651-660`) are what the
orchestrator asked me to check. It runs the guard `--separate-stderr`, requires
exit 0, then requires the stdout JSON to carry
`permissionDecision == "deny"` **and** `sys.argv[1] in
h["permissionDecisionReason"]`:

```
  run python3 -c 'import json,sys; o=json.load(sys.stdin); h=o["hookSpecificOutput"]; assert h["hookEventName"]=="PreToolUse", o; assert h["permissionDecision"]=="deny", o; assert sys.argv[1] in h["permissionDecisionReason"], (h["permissionDecisionReason"], sys.argv[1])' "$reason" <<< "$output"
  [ "$status" -eq 0 ]
```

so a guard whose reason is `outside the project directory` really does fail it.
Driven directly, HEAD vs. the guard with its `.codex` prefix deleted, same
payload, `XDG_CONFIG_HOME` set as `setup()` sets it:

```
HEAD:    "permissionDecisionReason": "refusing to edit/write /tmp/…/.codex/auth.json: under protected path /tmp/…/.codex"
mutated: "permissionDecisionReason": "refusing to edit/write /tmp/…/.codex/auth.json: outside the project directory"
```

The second assertion (`"$TMPHOME/.codex"`) satisfies "the reason names `.codex`";
`_edit_verdict` (`pkgs/dsh-openrouter/hook-guard.py:437-441`) runs the prefix loop
before the outside-the-project check, so the prefix arm is the one under test.

The decision-only entry SB7 added (`tests/unit/70-dsh-openrouter.bats:715`) stays,
as item 1 permits.

**Item 2 — `test_forbidden_prefix_home_codex` creates the directories and asserts
the stderr names the prefix.** MET.

`tests/lane/test_lane_submit.py:160-188`:

```
    (fake_home / ".codex").mkdir()
    (fake_home / ".codex" / "sessions").mkdir()
…
    rc = _submit(_agent_job_argv("~/.codex"), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []
…
    assert "refusing" in err
    assert ".codex" in err
```

The refusal message is `lane-submit: refusing --repo under {forbidden}`
(`pkgs/lane/lane-submit.py:308`), so `.codex` there names the *prefix*, and the
`rc == 1` assertion now discriminates: with the prefix removed from
`lane-submit.py` alone the test fails at `:178` with `assert 0 == 1` (the repo is
a real directory and is accepted), where under SB7 it failed only at the
`refusing` line. Evidence in ## Mutants, row 4.

**Item 3 — the two edited runbook lines re-wrapped to ≤ 76 columns, words
unchanged.** MET (with MINOR-1 on the fill).

Column widths after the change: `docs/runbooks/lanes.md:59-63` are 62, 52, 67,
44, 53; `:184-186` are 68, 64, 15. All ≤ 76 (SB7 left 82 and 87). Word streams of
both paragraphs against `33d64c5`, whitespace-normalised:

```
39a40
> `~/.codex`,
P1 diff rc=1
28a29
> `~/.codex`,
P2 diff rc=1
```

— the only word added is the one the change is about.

**Item 4 — the body pastes the red and the green, verbatim.** MET for the red and
the pytest green; the bats green is summarised (MINOR-2).

The body's red bats block is byte-for-byte what I reproduce:

```
not ok 1 hook-guard denies a write under ~/.codex with the protected-path reason
# (from function `guard_denies_reason' in file tests/unit/70-dsh-openrouter.bats, line 658,
#  in test file tests/unit/70-dsh-openrouter.bats, line 740)
#   `guard_denies_reason "$payload" "under protected path"' failed
```

and its red pytest block, run with the exact command the body quotes on the exact
base files it names (`git checkout 2c23cfc -- pkgs/lane/lane-submit.py
pkgs/dsh-openrouter/hook-guard.py pkgs/dsh-openrouter/dsh-openrouter.sh`):

```
FAILED tests/lane/test_forbidden_lists_agree.py::test_the_three_local_only_lists_agree
FAILED tests/lane/test_lane_submit.py::test_forbidden_prefix_home_codex - ass...
2 failed in 0.03s
```

including the `assert 0 == 1` at `tests/lane/test_lane_submit.py:178` and the
`AssertionError: assert '/home/x/.codex' in {…}` at
`tests/lane/test_forbidden_lists_agree.py:40`. `2c23cfc` is reachable in the
clone and its three implementation files are identical to `33d64c5`'s
(`git diff 2c23cfc 33d64c5 -- pkgs/…` empty), so the body's red command is
reproducible as written. The green `59 passed in 7.95s` reproduces (`59 passed in
7.96s`), and the bats count 118 is right (`grep -c '^ok '` → 118, no `not ok`).

**Previous review, item by item.**

| prior finding | closed? |
|---|---|
| MAJOR-1 — the guard's `~/.codex` refusal pinned by a test that cannot fail | CLOSED. `tests/unit/70-dsh-openrouter.bats:729` is red on the base, red on the deleted-prefix mutant, and red on the previous round's surviving mutant 8. |
| MINOR-1 — the body pastes no red and no green | CLOSED. Both pasted; the red reproduces exactly (MINOR-2 on the bats green's form). |
| MINOR-2 — two of four lane assertions non-discriminating | CLOSED. `tests/lane/test_lane_submit.py:171-173` creates the dirs; the lane-only mutant now dies at `assert rc == 1`. |
| MINOR-3 — the runbook lines not re-wrapped | CLOSED to the letter (≤ 76 columns), MINOR-1 on the ragged fill. |

## Red before green

Base implementation files against the branch's tests
(`git checkout 2c23cfc -- pkgs/lane/lane-submit.py pkgs/dsh-openrouter/hook-guard.py pkgs/dsh-openrouter/dsh-openrouter.sh`):

`nix develop -c pytest tests/lane -q`

```
        rc = _submit(_agent_job_argv("~/.codex"), "do the thing", monkeypatch)
>       assert rc == 1
E       assert 0 == 1
tests/lane/test_lane_submit.py:178: AssertionError
=========================== short test summary info ============================
FAILED tests/lane/test_forbidden_lists_agree.py::test_the_three_local_only_lists_agree
FAILED tests/lane/test_lane_submit.py::test_forbidden_prefix_home_codex - ass...
2 failed, 57 passed in 7.98s
```

`nix develop -c bats -f 'hook-guard denies a write under ~/.codex' tests/unit/70-dsh-openrouter.bats`

```
1..1
not ok 1 hook-guard denies a write under ~/.codex with the protected-path reason
# (from function `guard_denies_reason' in file tests/unit/70-dsh-openrouter.bats, line 658,
#  in test file tests/unit/70-dsh-openrouter.bats, line 740)
#   `guard_denies_reason "$payload" "under protected path"' failed
```

`nix develop -c bats -f 'refuses a workspace under ~/.codex' …` (carried, still red on the base)

```
1..1
not ok 1 refuses a workspace under ~/.codex before looking for a key
#   `[ "$status" -eq 3 ]' failed
```

and the same reverted tree run against the *old* decision-only loop, to show the
previous round's hole is real and is the one being closed:

```
$ nix develop -c bats -f 'hook-guard denies writes under the protected prefixes' …
1..1
ok 1 hook-guard denies writes under the protected prefixes
```

Restored (`git checkout HEAD -- pkgs/`): `59 passed in 7.96s`, and

```
1..2
ok 1 refuses a workspace under ~/.codex before looking for a key
ok 2 hook-guard denies a write under ~/.codex with the protected-path reason
```

## Mutants

| # | mutation | named by | test that must kill | result |
|---|---|---|---|---|
| 1 | `os.path.join(home, ".codex")` deleted from `_protected_prefixes()` | SB7b #1, SB7 #2 | reason test + agreement | KILLED |
| 2 | guard appends `.codex` only when `XDG_CONFIG_HOME` is **unset** (the review's mutant 8) | SB7b #2 | reason test | KILLED |
| 3 | dropped from all three lists at once | SB7b #3, SB7 #4 | membership + lane + wrapper + reason | KILLED, all four |
| 4 | `"~/.codex"` dropped from `FORBIDDEN_REPO_PREFIXES` alone | SB7b #4, SB7 #1 | lane refusal + agreement | KILLED |
| 5 | `"$HOME/.codex"` dropped from `forbidden=(…)` alone | SB7 #3 | agreement + bats workspace | KILLED |
| 6 | bash entry spelled `"~/.codex"` | SB7 #5 | shellcheck SC2088 at build; bats workspace with SC2088 suppressed | KILLED |
| 7 | guard gate inverted — `.codex` appended only when `XDG_CONFIG_HOME` **is** set | no | agreement test | KILLED |
| 8 | guard prefix narrowed to `os.path.join(home, ".codex", "sessions")` | no | reason test + agreement | KILLED |

Totals: 8 applied, 8 killed, 2 outside the named set. No survivor.

**1** — reason test:

```
not ok 1 hook-guard denies a write under ~/.codex with the protected-path reason
#   `guard_denies_reason "$payload" "under protected path"' failed
```

and agreement test:

```
E         Extra items in the left set:
E         '/home/x/.codex'
tests/lane/test_forbidden_lists_agree.py:31: AssertionError
```

**2** — the mutant that shipped green under SB7. Applied as
`if home and not os.environ.get("XDG_CONFIG_HOME", ""): prefixes.append(os.path.join(home, ".codex"))`
with the entry removed from the unconditional block; `setup()` exports
`XDG_CONFIG_HOME="$TMPHOME/.config"` (`tests/unit/70-dsh-openrouter.bats:20`), so
the guard loses the prefix in exactly the environment dsh runs in:

```
1..1
not ok 1 hook-guard denies a write under ~/.codex with the protected-path reason
# (from function `guard_denies_reason' in file tests/unit/70-dsh-openrouter.bats, line 658,
#  in test file tests/unit/70-dsh-openrouter.bats, line 740)
#   `guard_denies_reason "$payload" "under protected path"' failed
```

(the agreement test, which deletes `XDG_CONFIG_HOME`, still passes — the reason
test is the sole killer, which is what item 1 was for.)

**3** — `nix develop -c pytest tests/lane -q`:

```
FAILED tests/lane/test_forbidden_lists_agree.py::test_the_three_local_only_lists_agree
FAILED tests/lane/test_lane_submit.py::test_forbidden_prefix_home_codex - ass...
2 failed, 57 passed in 7.99s
```

`nix develop -c bats -f 'codex' …`:

```
1..2
not ok 1 refuses a workspace under ~/.codex before looking for a key
#   `[ "$status" -eq 3 ]' failed
not ok 2 hook-guard denies a write under ~/.codex with the protected-path reason
#   `guard_denies_reason "$payload" "under protected path"' failed
```

SB7's false sentence is now true: all four named tests fire.

**4** — the discrimination fix, proved:

```
        rc = _submit(_agent_job_argv("~/.codex"), "do the thing", monkeypatch)
>       assert rc == 1
E       assert 0 == 1
tests/lane/test_lane_submit.py:178: AssertionError
```

plus the agreement test naming the lane (`Extra items in the right set:
'/home/x/.codex'`).

**5** —

```
1..2
not ok 1 refuses a workspace under ~/.codex before looking for a key
#   `[ "$status" -eq 3 ]' failed
ok 2 hook-guard denies a write under ~/.codex with the protected-path reason
```

and the agreement test red (`Extra items in the left set: '/home/x/.codex'`).

**6** — raw, the devShell build fails before any test runs:

```
> https://www.shellcheck.net/wiki/SC2088 -- Tilde does not expand in quotes. ...
error: Cannot build '/nix/store/…-dsh-openrouter.drv'.
```

With `# shellcheck disable=SC2088` inserted so the package builds, the bats test
alone still kills it:

```
1..1
not ok 1 refuses a workspace under ~/.codex before looking for a key
# (in test file tests/unit/70-dsh-openrouter.bats, line 111)
#   `[ "$status" -eq 3 ]' failed
```

confirming the previous review's record of SB7's third mutation-target fact.

**7** — the inverse of mutant 2, tried because the section's own sentence reads
the gate the other way round (see MINOR-3). Killed by the agreement test
(`Extra items in the left set: '/home/x/.codex'`), which deletes
`XDG_CONFIG_HOME`; the reason test stays `ok`. So both directions of an
XDG-conditional guard die — the hole the previous round left is closed from both
sides.

**8** — narrowing the guard's protection to `~/.codex/sessions`:

```
not ok 1 hook-guard denies a write under ~/.codex with the protected-path reason
#   `guard_denies_reason "$payload" "under protected path"' failed
FAILED tests/lane/test_forbidden_lists_agree.py::test_the_three_local_only_lists_agree
```

All mutations reverted (`git checkout HEAD -- pkgs/`; `git status --porcelain`
empty) before the checks below.

## Checks

Fresh clone, `XDG_CACHE_HOME` under the scratchpad, working tree clean at
`4657018`.

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.lane-unit -L --no-link --rebuild` | green — `lane-unit-tests> 59 passed in 7.83s` |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | green — `unit-tests> ok 495 …` |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | green — `Found 0 warnings and 0 errors.` |
| `nix develop -c githooks/pre-commit` | rc 1 on the one-shot board regeneration (`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`); after `git add docs/OPERATIONS.md`, rc 0. The drift is exactly SB7b leaving the derived queue (`git diff docs/OPERATIONS.md`: one line, `… SB5 SB6 SB7b SD1 …` → `… SB5 SB6 SD1 …`), the section forbids a board commit — the orchestrator's step, not a finding. Reverted. |
| `nix develop -c ruff check pkgs/lane pkgs/dsh-openrouter tests/lane` | `All checks passed!` |
| `nix develop -c ruff format --check pkgs/lane pkgs/dsh-openrouter tests/lane` | `7 files already formatted` |
| `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc 0, no diff |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, rc 0 |
| `nix develop -c pytest tests/lane -q` | `59 passed in 8.03s` |
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 118 `ok`, 0 `not ok` |

## Touches and commit

`git diff 33d64c5..HEAD --stat` — 7 files, 74 insertions / 5 deletions, every one
inside the section's `touches` list; nothing outside it:

```
 docs/runbooks/lanes.md                   | 12 +++++++-----
 pkgs/dsh-openrouter/dsh-openrouter.sh    |  1 +
 pkgs/dsh-openrouter/hook-guard.py        |  1 +
 pkgs/lane/lane-submit.py                 |  1 +
 tests/lane/test_forbidden_lists_agree.py |  7 +++++++
 tests/lane/test_lane_submit.py           | 30 ++++++++++++++++++++++++++++++
 tests/unit/70-dsh-openrouter.bats        | 27 +++++++++++++++++++++++++++
```

`docs/MAP.md` needed no regeneration; the plan file is untouched
(`git diff --name-only | grep -c superpowers/plans` → 0); there is no board
commit.

Exactly one commit, `4657018` (`git rev-list --count 33d64c5..HEAD` → 1). Subject
byte-identical to the section's (`cmp` against the literal: `SUBJECT
BYTE-IDENTICAL`). The two trailers follow a blank line and close the message:

```
$
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run sb9f)$
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>$
```

The body states the why (the local-only classification of `~/.codex`), states the
SB7b correction and why the old entry could not fail, states that no production
behaviour changed, pastes the red and the green, and carries a four-row mutation
ledger.

## Findings

**MINOR-1 — the re-wrapped runbook lines are ragged, not filled to the
paragraph's width.** `docs/runbooks/lanes.md:59-63`.

Item 3 asks for the lines "re-wrapped to the paragraph's width (≤ 76 columns)".
They are all ≤ 76, but three of them are far short of the fill the surrounding
lines use (67-75 columns):

```
59(62):   under (or equal to) `~/.claude`, `~/.codex`, `/run/baskets`,
60(52):   `/var/lib/baskets`, `~/strategy`, `/var/lib/helm`,
61(67):   `/var/lib/egress-broker`, `/var/lib/lanes` and `/var/lib/secrets`
62(44):   outright, and refuses any symlink inside a
63(53):   permitted `--repo` whose target resolves outside it
```

Cosmetic; `lint` is green and the word stream is unchanged.

**MINOR-2 — the commit body's bats green is summarised, not verbatim.**
`4657018` body.

Item 4 says "verbatim". The red bats block and both pytest blocks are verbatim
and reproduce exactly; the bats green is prose:

```
$ bats tests/unit/70-dsh-openrouter.bats
118 ok, not ok 0 (incl. ok 1 hook-guard denies a write under ~/.codex
with the protected-path reason; the decision-only loop stays green)
```

The counts are true (118 `ok`, no `not ok`), so nothing is misreported.

**MINOR-3 — the section's second mutation target is self-contradictory (plan
text, not the seat).**
`docs/superpowers/plans/2026-09-05-seat-behind-broker.md:254`:

> the guard protecting `~/.codex` only under `XDG_CONFIG_HOME` (the review's
> mutant 8) → item 1's reason test fails with `XDG_CONFIG_HOME` unset.

The review's mutant 8 is the *opposite* gate (protect only when
`XDG_CONFIG_HOME` is **unset**), and the killer fires with `XDG_CONFIG_HOME`
**set**, which is what `setup()` does. I applied both readings: mutant 2 (the
review's, and the one the body claims) dies on the reason test; mutant 7 (the
sentence's literal reading) dies on the agreement test. The contract is met
either way, but the sentence as written names the wrong environment for the
wrong mutant and should be corrected before it is copied into another section.

## Verdict

APPROVED. No MAJOR. The one MAJOR that rejected SB7 — a refusal contract pinned
by an assertion that could not fail — is closed by a reason-level assertion that
I showed red on the base, red on the deleted prefix, and red on the exact mutant
that previously shipped green. All four named mutants and all five of SB7's
carried kills die; the two extra mutants I invented die too; every acceptance
check is green; the diff is inside `touches`; one commit, byte-identical subject,
both trailers, red and green in the body. The three MINORs are cosmetic
(line fill), presentational (a summarised green block), and a wording defect in
the plan section's own mutation ledger.
