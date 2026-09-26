---
plan_defect: missing-case
plan_defect_secondary: implementer
mutants_total: 35
mutants_killed: 30
mutants_outside_named: 10
reviewer: opus
majors: 1
minors: 5
---
# Opus gate — seat run pb3ar2b, task P3Ar2b — REJECTED

## Summary

Everything P3Ar2's gate asked for as a *minor* is fixed and provably so. The
span walk is by `ast.walk` over `FunctionDef`/`AsyncFunctionDef` (methods
included), `FSTRING_MIDDLE` tokens are scanned, a module-level literal is
attributed to `<module>`, the self-exclusion is `path == HERE` **and** the
function name, and the regex is `[0-9]+\s+rej(?:ections)?\b` (the double-space
evasion is caught). Every shape the matrix names — a, b, c, d1, d1′, d2, d3,
e1, i, j, k, l, m — fails the guard naming file, function and line; f does not
fire; g and h (spelled so the seed is named in the body) pass. All seven of
this round's named mutants and all nine of P3Ar2's die. Every check is green,
the seed is byte-identical, the scratch row leaves nothing behind, and the
commit is one commit with P3A's subject and both trailers. The red-on-main
paste in the commit body is now the real artefact — main's own `test_tasks.py`
copied beside the branch, one hit at `test_brief_record_line_over_seeded_ledger:2636`.

The MAJOR is that the **positive rule is still not the rule.** Contract item 1
says a count literal "must sit in a function whose body references
`plan-defects-seed.toml`", and that "the live-path blacklist may stay as a
second reason but **decides nothing**". The implementation
(`tests/evidence/test_tasks.py:2510-2513`) is

```python
            if _reads_live_ledger(body) or not (
                _reads_frozen_seed(body) or "tmp_path" in body
            ):
```

— an unnamed second alternative, `or "tmp_path" in body`, that the contract
never granted. With it the rule is not total, and the blacklist is back in
charge of the very defect this line has been chasing for five rounds. Two runs
prove it. (1) Delete the blacklist (`_reads_live_ledger` → `return False`) and
attack (a) — **main's own defective test body, verbatim** — passes the guard:
the blacklist, not the positive rule, is what catches main. (2) Leave the guard
exactly as shipped and hoist main's path expression out of the function into a
module constant not named `LIVE_LEDGER` — one line moved, nothing else changed
— and main's defect passes. That is the same class of hole that rejected
P3Arb (identifier-keyed) and P3Ar2 (spelling-keyed), narrowed but alive.

The plan is the first cause. Item 1 as literally worded is unimplementable on
this tree: applied verbatim (`_reads_frozen_seed(body)` alone) the guard is red
against the branch's **own** file on eight legitimate synthetic tests that
build a ledger from inline strings under `tmp_path` and assert `"7 rej, 6
plan"`, `"1 rej"`, `"0 rej, 0 plan"` and friends. The plan never enumerated
that case, so the seat had to invent an escape; it chose the widest one and
disclosed it honestly in the docstring and the commit body. Hence
`plan_defect: missing-case`, secondary `implementer`.

## The attack table (a–n)

All runs are `nix develop -c pytest tests/evidence/test_tasks.py -q -k
no_literal` from the fresh clone
`…/scratchpad/gate-pb3ar2b-P3Ar2b` (branch `task/P3Ar2b`, head `028a05d`, base
`69e58b3`). Every scratch file was removed and every edit reverted;
`git status --porcelain` is empty after each and at the end.

| # | shape | expected | observed |
|---|---|---|---|
| a | main's `test_brief_record_line_over_seeded_ledger` body (`git show 69e58b3:…`) pasted into `test_scratch_a.py` | FAILS | **FAILS** — `['test_scratch_a.py:test_brief_record_line_over_seeded_ledger:33']` |
| b | `assert "60 rej" in line` added inside `test_live_record_line_shape_only` | FAILS | **FAILS** — `['test_tasks.py:test_live_record_line_shape_only:2773']` |
| c | new file, `"60 rejections"` over `HERE.parents[2] / "docs" / "ledger" / "plan-defects.toml"` | FAILS | **FAILS** — `['test_scratch_c.py:test_scratch_hardcoded_live_count:10']` |
| d1 | `os.path.join(str(root), "docs", "ledger", "plan-defects.toml")`, `root = HERE.parents[2]` | FAILS | **FAILS** — `['test_scratch_d1.py:test_scratch_joined_live_count:12']` |
| d1′ | same, but `root = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))` — no `parents[` anywhere | FAILS | **FAILS** — `['test_scratch_d1b.py:test_scratch_joined_live_count_no_parents:12']` |
| d2 | `open(os.environ["LEDGER_PATH"])` | FAILS | **FAILS** — `['test_scratch_d2.py:test_scratch_env_live_count:8']` |
| d3 | `HERE.parent.parent.parent / "docs" / "ledger" / "plan-defects.toml"` | FAILS | **FAILS** — `['test_scratch_d3.py:test_scratch_parent_chain_live_count:11']` |
| e1 | `assert f"60 rej" in line` over a live path (`FSTRING_MIDDLE`) | FAILS | **FAILS** — `['test_scratch_e1.py:test_scratch_fstring_live_count:10']` |
| e2 | `assert "%d rej" % N in line` over a live path | say | **PASSES** — `1 passed, 119 deselected`; computed, outside the contract's literal-first wording. MINOR + pin |
| f | `# The live ledger is at 60 rej today` inside a live-reading function | must NOT fire | **does not fire** — `1 passed` |
| g | the frozen-seed test itself | passes | **passes** — baseline `1 passed, 119 deselected`; full suite `175 passed` |
| h | new file, literal count over `fixtures/ledger/plan-defects-seed.toml` | passes | **passes when the body names the seed** — path spelled inside the function (h2) `1 passed`; module constant named `FROZEN_SEED` (h3) `1 passed`. **FAILS** when the same file names it `SEED` — `['test_scratch_h.py:test_scratch_literal_over_seed:12']`. Within the contract's letter ("whose body references"), but see the MINOR: the whitelist is by identifier text |
| i | `async def` test with a live literal | FAILS | **FAILS** — `['test_scratch_i.py:test_scratch_async_live_count:10']` |
| j | class with a test method holding a live literal | FAILS | **FAILS** — `['test_scratch_j.py:test_method_live_count:11']` |
| k | module-level assert with a live literal | FAILS, `<module>` | **FAILS** — `['test_scratch_k.py:<module>:7']` |
| l | scratch file defining a function named exactly like the guard | FAILS | **FAILS** — `['test_scratch_l.py:test_no_literal_record_count_against_live_ledger:10']` |
| m | seed named only in a comment **and** a docstring; literal over `parents[2]` live path | say | **FAILS** — `['test_scratch_m.py:test_scratch_comment_mentions_seed:12']`, but only because the blacklist sees `parents[`. See m2 |
| m2 | seed named only in a comment; live path via `os.environ["LEDGER_PATH"]` | (my addition) | **PASSES** — `1 passed`. "References" does mean any occurrence, comments included. MINOR + pin |
| n | one function that references the seed **and** reads the live ledger, one literal each | say | **FAILS** — `['…:test_scratch_seed_and_live:12', '…:test_scratch_seed_and_live:13']`. Stricter than the contract's letter (which would allow it). Correct behaviour; not a finding |

Evasions outside the named matrix — the MAJOR's evidence. All three hold
against the guard exactly as shipped:

```python
# tests/evidence/test_scratch_x3.py — main's defect, path hoisted one line up
HERE = pathlib.Path(__file__).resolve()
LEDGER = HERE.parents[2] / "docs" / "ledger" / "plan-defects.toml"


def test_brief_record_line_over_seeded_ledger(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs" / "ledger").mkdir(parents=True)
    (repo / "docs" / "ledger" / "plan-defects.toml").write_bytes(LEDGER.read_bytes())
    …
    assert "59 rej, 52 plan (vac 15, miss 20, under 9, fact 8)" in line
```

```
=== x3 main's defect, live path hoisted to a module constant ===
1 passed, 119 deselected in 0.07s
=== x1 tmp_path + env-var live path ===
1 passed, 119 deselected in 0.07s
=== x2 tmp_path + helper-returned live path ===
1 passed, 119 deselected in 0.07s
```

x1 copies `open(os.environ["LEDGER_PATH"])` into `tmp_path`; x2 reads the live
ledger through a module-level `_live()` helper. In all three the function body
holds `tmp_path`, so the positive clause is satisfied without the seed, and the
body spells no blacklisted token, so the negative clause is silent. Note that
main's real defect is itself a `tmp_path` test — it copies the live ledger into
`tmp_path` and asserts over the copy — so the escape hatch is aimed squarely at
the defect class it is meant to catch.

Robustness, whole-tree: `tests/evidence` holds five `test_*.py`; the guard scans
all of them, `0.05s call` under `--durations`, no crash. Fed one file with a
module docstring, a docstring inside a helper, an `async def`, a class method
and a nested `def`, it reports all five with correct attribution:

```
E  assert not ['test_scratch_rob.py:<module>:1', 'test_scratch_rob.py:fixture_like:10',
               'test_scratch_rob.py:test_async_case:15', 'test_scratch_rob.py:test_method_case:20',
               'test_scratch_rob.py:inner:25']
```

## Red on main

Contract item 4, reproduced exactly as worded — main's own `test_tasks.py`
copied beside the branch, one hit:

```
$ git show 69e58b3:tests/evidence/test_tasks.py > tests/evidence/test_tasks_main.py
$ nix develop -c pytest tests/evidence/test_tasks.py -q -k no_literal
E   AssertionError: literal record counts not over a deterministic source in:
    ['test_tasks_main.py:test_brief_record_line_over_seeded_ledger:2636']
1 failed, 119 deselected in 0.22s
$ grep -n '56 rej' tests/evidence/test_tasks_main.py
2636:    assert "56 rej, 51 plan (vac 15, miss 19, under 9, fact 8)" in line
```

The commit body pastes this same artefact and this same single hit. P3Ar2's
minor on that point is closed.

**Red before green.** P3Ar2's guard (`git -C /home/dalhaka/factory/ws/pb3ar2/P3Ar2
show task/P3Ar2:tests/evidence/test_tasks.py`, copied over the branch's file),
each attack in isolation — all eight pass there, which is the contracted red
for this round's tests, and all eight fail on the branch (table above):

```
=== P3Ar2 guard, no attack ===        1 passed, 119 deselected in 0.13s
=== P3Ar2 guard + attack d1′ ===      1 passed, 119 deselected in 0.03s
=== P3Ar2 guard + attack d2 ===       1 passed, 119 deselected in 0.03s
=== P3Ar2 guard + attack d3 ===       1 passed, 119 deselected in 0.03s
=== P3Ar2 guard + attack e1 ===       1 passed, 119 deselected in 0.03s
=== P3Ar2 guard + attack i ===        1 passed, 119 deselected in 0.03s
=== P3Ar2 guard + attack j ===        1 passed, 119 deselected in 0.03s
=== P3Ar2 guard + attack k ===        1 passed, 119 deselected in 0.03s
=== P3Ar2 guard + attack l ===        1 passed, 119 deselected in 0.03s
```

## The seed, the shape test, the scratch row

```
$ git show 3937d98:docs/ledger/plan-defects.toml | cmp - tests/evidence/fixtures/ledger/plan-defects-seed.toml
IDENTICAL
$ sha256sum tests/evidence/fixtures/ledger/plan-defects-seed.toml
6b2f745d14be98c09071af1914673f47603f05aef1ddfcf4228c76ae4117ed34
$ grep -c '^\[\[rejection\]\]' tests/evidence/fixtures/ledger/plan-defects-seed.toml   -> 48
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml                           -> 59
```

The record test reads `FROZEN_SEED` only and asserts `48 rej, 45 plan (vac 15,
miss 16, under 8, fact 6)`; the shape test reads `LIVE_LEDGER` and asserts
`RECORD_SHAPE` plus `rej >= 48`, with the negative case
`RECORD_SHAPE.match("**Record: unavailable**") is None`. Both mutants below
kill.

Scratch row: a 60th `[[rejection]]` appended for
`docs/reviews/2026-09-06-opus-review-pb3ar-P3Ar.md` (exists, REJECTED, dated
before `front_matter_from`), `git add`ed so the flake sees it, then reverted:

```
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml      -> 60
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check    -> EXIT=0 (silent)
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link      -> EXIT=0
  evidence-unit> 175 passed in 4.52s
$ nix develop -c pytest tests/evidence -q                         -> 175 passed in 4.46s
--- revert ---
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml      -> 59
$ git status --porcelain                                          -> (empty)
$ git diff 69e58b3..HEAD -- docs/ledger                           -> (empty)
```

(`--rebuild` cannot be used on the scratch-row build: the mutated derivation
was never built, so nix refuses with "some outputs … are not valid". The plain
build is the equivalent evidence; the un-mutated tree was built with
`--rebuild`, below.)

Runbook, `docs/runbooks/evidence.md:110-114`, unchanged from P3Ar2 and still
accurate: P3Ar's `M11`/`M11b` live-ledger class flips are unobservable by
design since P3Arb, the frozen-fixture flips standing in, "so the gate counts
P3Ar's remaining kills, not the original 42."

## Mutants

35 applied, 30 killed, 5 survived. A code mutation counts as KILLED when
removing the clause demonstrably breaks a contracted behaviour (an attack gets
through, a required pass turns red, or the required file/**function**/line
attribution is lost).

| # | mutant | result |
|---|---|---|
| M1a | **named:** the seed requirement dropped (`_reads_frozen_seed` → `False`) | KILLED — but **not** by d1/d2/d3, which still fail (the blacklist and the missing `tmp_path` catch them). Killed by (h): `test_scratch_h2.py:test_scratch_literal_over_seed_inline:12` now fails though the contract requires it to pass. Full suite still `175 passed` — the clause is not load-bearing for the shipped tests |
| M1b | the whole positive clause dropped (condition = `_reads_live_ledger(body)`) | KILLED — d1′ `1 passed`, d2 `1 passed`, k `1 passed`; **d3 still fails**, caught by the blacklist |
| M2 | **named:** `FSTRING_MIDDLE` dropped | KILLED — e1 `1 passed` |
| M3 | **named:** `AsyncFunctionDef` dropped | KILLED — i still fails but is misattributed `['test_scratch_i.py:<module>:10']`, losing the contracted function name; and the legitimate async-over-seed control i2 turns red (`['test_scratch_i2.py:<module>:10']`) |
| M4 | **named:** `ClassDef` methods dropped (methods filtered out of the walk) | KILLED — j misattributed `['test_scratch_j.py:<module>:11']`; legitimate method-over-seed control j2 turns red |
| M5 | **named:** module-level attribution dropped (`if span is None: continue`) | KILLED — k `1 passed` |
| M6 | **named:** the path half of the exclusion dropped | KILLED — l `1 passed` |
| M7 | **named:** the regex's `\s+` → a single space | KILLED — `"60  rej"` (double space) `1 passed`; on the branch it fails at `test_scratch_g2.py:test_scratch_double_space:10` |
| MBL | the blacklist dropped (`_reads_live_ledger` → `False`) — *outside the named set* | KILLED — **attack (a), main's own body, `1 passed`**; c, d3, e1 still fail; full suite `175 passed`. This is the MAJOR's proof that the blacklist decides main's defect |
| N1 | P3Ar2: regex → `[0-9]+\s+rejections\b`; attack b | KILLED — b `1 passed` |
| N2 | P3Ar2: `_reads_live_ledger` → `False`; attack b | KILLED — b `1 passed` |
| N4 | P3Ar2: glob narrowed to `[HERE]`; attack c | KILLED — c `1 passed` |
| N5 | P3Ar2: frozen test's `FROZEN_SEED` → `LIVE_LEDGER` | KILLED — `assert '48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)' in '**Record (7 d):** 59 rej, 52 plan (vac 15, miss 20, under 9, fact 8)'`, and the guard catches it too |
| N6 | P3Ar2: `RECORD_SHAPE` → `(.*)` | KILLED — the negative case: `assert <re.Match … match='**Record: unavailable**'> is None` |
| N7 | P3Ar2: attack b | KILLED (table row b) |
| O1 | P3Ar2: attack a | KILLED (table row a) |
| O2 | P3Ar2: attack c | KILLED (table row c) |
| O8 | P3Ar2: one class flipped in the FROZEN fixture | KILLED — `'48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)' in '… 48 rej, 45 plan (vac 14, miss 16, under 8, fact 7)'`; fixture restored, `cmp` identical |
| A1–A16 | attack shapes a, b, c, d1, d1′, d2, d3, e1, g2, i, j, k, l, m, n, rob | KILLED (all caught; table above) |
| S1 | attack e2 (`"%d rej" % N`) | **SURVIVED** — computed, outside the contract |
| S2 | attack m2 (seed in a comment + env-var live path) | **SURVIVED** |
| S3 | attack x1 (`tmp_path` + env-var live path) | **SURVIVED** |
| S4 | attack x2 (`tmp_path` + helper-returned live path) | **SURVIVED** |
| S5 | attack x3 (main's defect, live path hoisted to a module constant) | **SURVIVED** |

No *named* mutant survives. The four survivors that matter (S2–S5) are all the
same hole: the positive clause can be satisfied without the seed.

Probe, not a mutant — contract item 1 applied to the letter
(`_reads_frozen_seed(body)` as the only positive alternative), no attack file
present:

```
E  assert not ['test_tasks.py:test_brief_record_line_counts_and_classifies:2678',
               'test_tasks.py:test_record_window_is_inclusive:269…16',
               'test_tasks.py:test_main_accepts_today_global:2847',
               'test_tasks.py:test_record_ignores_approved_block:2866', …]
1 failed, 119 deselected in 0.20s
```

Eight legitimate synthetic tests. They build their ledger from inline string
literals under `tmp_path` and never read a file — which is exactly the shape a
total rule can key on.

## Checks

All from the fresh clone (`028a05d`, base `69e58b3`, tree clean).

```
$ nix develop -c ruff check pkgs/evidence tests/evidence
All checks passed!                                   EXIT=0
$ nix develop -c ruff format --check pkgs/evidence tests/evidence
49 files already formatted                           EXIT=0
$ nix develop -c pytest tests/evidence -q
175 passed in 4.64s
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild
evidence-unit> 175 passed in 4.54s                   EXIT=0
$ nix build .#checks.x86_64-linux.lint -L --no-link                    EXIT=0
$ nix develop -c githooks/pre-commit
render.test.mjs: all assertions passed               EXIT=0
$ nix develop -c python3 pkgs/evidence/repomap.py --root . write && git diff --exit-code docs/MAP.md
MAP-CLEAN
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check
EXIT=0        (silent, 0 bytes on stdout)
$ git diff 69e58b3..HEAD -- docs/ledger
(empty)
$ git status --porcelain
(empty)
```

Commit convention: `git rev-list --count 69e58b3..HEAD` → `1`; the subject
`cmp`s byte-identical to the plan's `commit subject` for P3A/P3Ar2b;
`Generated-By:` and `Co-Authored-By:` follow a blank line at the end of the
body; the four touched files are `tests/evidence/test_tasks.py`,
`tests/evidence/fixtures/ledger/plan-defects-seed.toml`,
`docs/runbooks/evidence.md` (all in `touches`) plus `docs/MAP.md` by rule; no
board commit; the body pastes both `evidence-unit` runs (59 rows; a scratch
60th row, reverted) and the real red-on-main hit. The body also states the
`tmp_path` alternative plainly — the deviation was disclosed, not hidden.

## Findings

**MAJOR — the positive rule is widened by an unnamed `or "tmp_path" in body`
alternative, so the rule is not total; the live-path blacklist consequently
decides main's own defect, and main's defect passes once its path expression is
hoisted to a module constant** (`tests/evidence/test_tasks.py:2510-2513`).

Contract item 1: a count literal "must sit in a function whose body references
`plan-defects-seed.toml`", and "the live-path blacklist may stay as a second
reason but **decides nothing**." Shipped:

```python
            if _reads_live_ledger(body) or not (
                _reads_frozen_seed(body) or "tmp_path" in body
            ):
```

Two runs refute the second sentence and the first. Delete the blacklist and
attack (a) — main's own body, verbatim — passes (`MBL`, `1 passed, 119
deselected`): the blacklist is the only thing catching main. Keep the guard as
shipped and move main's `seed = HERE.parents[2] / …` out of the function to a
module constant named anything but `LIVE_LEDGER` (`x3`) and it passes
(`1 passed, 119 deselected`) — the very idiom this file uses for `FROZEN_SEED`
and `LIVE_LEDGER`. Two further shapes pass the same way: `tmp_path` plus an
env-var path (x1), `tmp_path` plus a helper-returned path (x2). Main's real
defect *is* a `tmp_path` test — it copies the live ledger into `tmp_path` — so
the escape hatch is open on precisely the defect class the guard exists for.
This is the P3Arb/P3Ar2 hole again: identifier- and spelling-keyed, narrower,
not closed.

Pin for the re-plan (the rule can be made total without touching the eight
synthetic tests, which read no file at all): a function holding a count literal
is clean iff **every** read it performs is of the frozen seed or a
`fixtures/` path — i.e. walk the function's AST and reject any
`.read_text()` / `.read_bytes()` / `open(…)` whose receiver is not
`FROZEN_SEED` or a `fixtures` path, instead of text-matching path spellings.
Under that rule: the eight synthetic tests (no reads) pass; the frozen-seed
test (reads `FROZEN_SEED`) passes; a, c, d1–d3, e1, i–l, x1, x2, x3 all fail,
whatever the path is spelled or wherever it is hoisted.

**MINOR — the plan's item 1 is unimplementable as worded** (plan
`docs/superpowers/plans/2026-09-06-planning-agent.md` §P3Ar2b, contract 1).
Applied to the letter it turns `evidence-unit` red against the branch's own
file on eight synthetic `tmp_path` tests (paste above). The plan never named
the synthetic-fixture case, which is why this is `plan_defect: missing-case`;
the seat's choice of the widest possible escape, unflagged as a conflict with
"the blacklist decides nothing", is the secondary `implementer` half.

**MINOR — "references the seed" is satisfied by a comment**
(`tests/evidence/test_tasks.py:2464`, `_reads_frozen_seed` matches raw body
text). Attack m2 — a function whose only mention of the seed is
`# plan-defects-seed.toml`, reading the live ledger through
`os.environ["LEDGER_PATH"]` — passes (`1 passed`). Attack m (the same trick with
a `parents[2]` path) only fails because the blacklist sees it. Pin: match the
seed reference in the AST (a `Name`/`Constant` actually used in a read), not in
the body text.

**MINOR — the whitelist is by identifier text, so it both over- and
under-fires.** A new file whose module constant is named `SEED` rather than
`FROZEN_SEED`, reading `fixtures/ledger/plan-defects-seed.toml`, is a **false
positive**: `['test_scratch_h.py:test_scratch_literal_over_seed:12']`. Spelled
`FROZEN_SEED` or with the path inside the function it passes. Same root cause
as the MAJOR: names, not data flow.

**MINOR — a computed count is invisible** (`e2`, `assert "%d rej" % N in line`
over a live path, `1 passed`). Outside the contract's literal-first wording;
worth a sentence in the next round rather than a code change.

**Note, not a finding — the guard is stricter than the contract on (n).** A
function that references the seed *and* reads the live ledger fails
(`['…:test_scratch_seed_and_live:12', '…:13']`). The contract's letter would
allow it; failing is the right behaviour and I would keep it.

**Note — the self-exclusion is dead code on today's tree.** The guard's own
function holds no string literal matching `[0-9]+\s+rej…` (its message
f-string and comments carry no digits), so neither half of `path == HERE and
name == …` ever fires in the shipped suite. It is still correct and still
required by contract item 3, and mutant M6 dies on attack l.

## Verdict

**REJECTED.** One MAJOR: contract item 1 is not implemented as the round's
whole point requires — the positive rule carries an unnamed `or "tmp_path" in
body` alternative, so it is not total, and the live-path blacklist (which the
contract says must decide nothing) is the only clause catching main's own
defect; hoisting main's path expression one line up to a module constant, or
reaching the ledger through an env var or a helper, walks past the guard.
Everything else is met: a–e1 and i–l all fail, f is silent, g/h pass, the
red-on-main paste is the real artefact, the seed is byte-identical, the scratch
row is clean, all sixteen named mutants die, and every check is green. The fix
is one function and needs no change to the eight synthetic tests: decide by the
reads a function performs (AST), not by the path spellings and identifier names
in its text. Because the plan's item 1 as worded turns the check red on the
branch's own file, this wants a re-plan (rule A1), not a bare implementer
round.
