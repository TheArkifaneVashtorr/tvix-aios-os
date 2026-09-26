---
plan_defect: implementer
mutants_total: 18
mutants_killed: 9
mutants_outside_named: 11
reviewer: opus
majors: 1
minors: 5
---
# Opus gate — seat run pb3ar2, task P3Ar2 — REJECTED

## Summary

The headline defect of P3Arb is gone. The guard is now literal-first and
repo-wide, it is **red against main's own `test_tasks.py`** (contract item 3,
reproduced below, naming `test_brief_record_line_over_seeded_ledger` at line
2636), and shapes (a), (b) and (c) of the required matrix all fail it, naming
file, function and line. Items 1, 2 and 4 of P3Arb still stand: the fixture is
byte-identical to `git show 3937d98:docs/ledger/plan-defects.toml`, the record
test reads it and asserts `48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)`,
the shape test carries its negative case, and `evidence-unit` is green on the
58-row tree and stays green with a scratch 59th row appended (then reverted).
Every check is green. The commit is one commit with P3A's subject and both
trailers.

Item 2 is still not met. The contract has **two** conjuncts — the enclosing
function's body "must reference the frozen seed fixture path … **and** must NOT
reference `docs/ledger/plan-defects.toml` in any spelling (a joined path, a
string literal, a `parents[2] / "docs" / "ledger"` chain)". The implementation
(`tests/evidence/test_tasks.py:2453-2464`) drops the first conjunct entirely and
implements the second as a three-alternative blacklist: the identifier
`LIVE_LEDGER`, the regex `parents\s*\[`, or the bare string
`"docs/ledger/plan-defects.toml"`. Consequence, proven by running it: **a joined
path — the first spelling the contract's own parenthetical enumerates — is
invisible.** Main's defective test with `parents[2]` rewritten as
`.parent.parent.parent` passes the guard; so does `os.path.join(str(root),
"docs", "ledger", "plan-defects.toml")`. The named mutant "the seed-fixture
requirement dropped" therefore survives as a no-op, because the requirement was
never there. That is the MAJOR.

The implementer's own docstring shows the tension was seen and resolved the
wrong way: "The fixture's tmp-path spelling `(repo / "docs" / "ledger" /
"plan-defects.toml")` is none of these." A joined path had to be made invisible
precisely because the whitelist conjunct — "the function must reference
`fixtures/ledger/plan-defects-seed.toml`" — was omitted. With that conjunct the
tmp-path spelling is safe (the frozen test names `FROZEN_SEED`) and every joined
live path is caught.

## The guard under attack (table a–h)

All runs are `nix develop -c pytest tests/evidence/test_tasks.py -q -k
no_literal` from the clone; every scratch file was removed and every mutation
reverted (`git status --porcelain` empty after each, verified).

| # | shape | expected | observed |
|---|---|---|---|
| a | main's `test_brief_record_line_over_seeded_ledger` body pasted into `tests/evidence/test_scratch_a.py` | fails, naming file/function/line | **FAILS** — `['test_scratch_a.py:test_brief_record_line_over_seeded_ledger:33']` |
| b | `assert "59 rej" in line` added to `test_live_record_line_shape_only` | fails | **FAILS** — `['test_tasks.py:test_live_record_line_shape_only:2747']` |
| c | new file, `"59 rejections"` against `HERE.parents[2] / "docs" / "ledger" / "plan-defects.toml"` | fails | **FAILS** — `['test_scratch_c.py:test_scratch_hardcoded_live_count:9']` |
| d1 | same count against `os.path.join(str(root), "docs", "ledger", "plan-defects.toml")` | "say" | **PASSES the guard — not seen** (`1 passed, 119 deselected`) |
| d2 | same count against `open(os.environ["LEDGER_PATH"])` | "say" | **PASSES the guard — not seen** |
| d3 | same count against `HERE.parent.parent.parent / "docs" / "ledger" / "plan-defects.toml"` | (my addition) | **PASSES the guard — not seen** |
| e1 | `assert f"59 rej" in line` over the live ledger (a *literal*, not a computed count) | "say" | **PASSES the guard — not seen** |
| e2 | `assert "%d rej" % n in line` over the live ledger | "say" | **PASSES the guard — not seen** |
| f | `# The live ledger is at 59 rej today` inside a live-reading function | must NOT fire | **does not fire** — `1 passed` |
| g | the frozen-seed test itself | passes | **passes** (175 passed, baseline) |
| h | new file, `text.count("[[rejection]]") == 48` plus `"48 rej, 45 plan"` over `fixtures/ledger/plan-defects-seed.toml` | passes | **passes** — `1 passed` |

d1/d2/d3 evidence, verbatim (d3 is main's defect with one token changed):

```python
# tests/evidence/test_scratch_d3.py
def test_scratch_parent_chain_live_count():
    root = HERE.parent.parent.parent
    seed = root / "docs" / "ledger" / "plan-defects.toml"
    line = seed.read_text()
    assert "59 rej" in line
```

```
$ nix develop -c pytest tests/evidence/test_tasks.py -q -k no_literal
=== (d3) .parent.parent.parent chain ===
.                                                                        [100%]
1 passed, 119 deselected in 0.03s
```

e1 is not a "computed count in disguise" — it is a plain literal in an
f-string, and on this devShell's Python it is unreachable by construction.
`tokenize` on 3.14 emits `FSTRING_MIDDLE`, not `STRING`, and the guard filters
`tok.type != tokenize.STRING` (`tests/evidence/test_tasks.py:2478`):

```
$ nix develop -c python3 - <<'PY'   # src = 'x = f"59 rej"\ny = "59 rej"\n'
FSTRING_MIDDLE '59 rej' (1, 6)
STRING '"59 rej"' (2, 4)
--- STRING-only hits ---
HIT '"59 rej"' (2, 4)
PY
$ nix develop -c python3 -c "import sys; print(sys.version)"
3.14.7 (main, Aug  5 2026, 10:29:49) [GCC 15.3.0]
```

## Red on main

Contract item 3 is met in substance. I ran the branch's guard against main's
`tests/evidence/test_tasks.py` verbatim (`git show
1a9f146:tests/evidence/test_tasks.py > tests/evidence/test_tasks_main.py`, the
guard globs `HERE.parent.glob("test_*.py")` so it reads it):

```
$ nix develop -c pytest tests/evidence/test_tasks.py -q -k no_literal
E       assert not ['test_tasks_main.py:test_brief_record_line_over_seeded_ledger:2636']
tests/evidence/test_tasks.py:2759: AssertionError
FAILED tests/evidence/test_tasks.py::test_no_literal_record_count_against_live_ledger
1 failed, 119 deselected in 0.08s

$ grep -n '56 rej' tests/evidence/test_tasks_main.py
2636:    assert "56 rej, 51 plan (vac 15, miss 19, under 9, fact 8)" in line
```

The commit body's paste is a different artefact: it runs the guard against a
scratch file (`test_scratch_defect.py:test_brief_record_line_over_seeded_ledger:16`
and `:17`) rather than against main's `test_tasks.py` as item 3 words it, and
its two hits at consecutive lines 16/17 are not reproducible — main's function
holds exactly one matching string literal, and my verbatim paste of that body
produced one hit (`:33`). MINOR: the claim is true, the paste does not show it.

## The frozen seed and the shape test

```
$ git show 3937d98:docs/ledger/plan-defects.toml | cmp - tests/evidence/fixtures/ledger/plan-defects-seed.toml && echo IDENTICAL
IDENTICAL
$ sha256sum tests/evidence/fixtures/ledger/plan-defects-seed.toml
6b2f745d14be98c09071af1914673f47603f05aef1ddfcf4228c76ae4117ed34
$ grep -c '^\[\[rejection\]\]' tests/evidence/fixtures/ledger/plan-defects-seed.toml
48
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml
58
```

The tree carries **58** ledger rows, not 59 (main is `1e079d9`, base `1a9f146`,
both 58); the commit body's "58-row tree" and "scratch 59th row" pastes match
what I see. `FROZEN_SEED` (line 2383) is read by
`test_brief_record_line_over_seeded_ledger` (line 2699) and the live path
`LIVE_LEDGER` (line 2384) only by `test_live_record_line_shape_only` (line
2729). Pointing the record test at the live ledger dies:

```
E   AssertionError: assert '48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)' in '**Record (7 d):** 58 rej, 52 plan (vac 15, miss 20, under 9, fact 8)'
FAILED tests/evidence/test_tasks.py::test_brief_record_line_over_seeded_ledger
```

The shape test's negative case holds; loosening `RECORD_SHAPE` to `(.*)` dies on
it, not on the shape match:

```
E   AssertionError: assert <re.Match object; span=(0, 23), match='**Record: unavailable**'> is None
FAILED tests/evidence/test_tasks.py::test_live_record_line_shape_only
1 failed, 174 passed in 5.19s
```

Runbook (contract item 4), `docs/runbooks/evidence.md:110-114`: "P3Ar's
`M11`/`M11b` (live-ledger class flips) are no longer killable since P3Arb, the
frozen-fixture flips standing in for them — so the gate counts P3Ar's remaining
kills, not the original 42." Accurate and confirmed by the flips below. No
stale sentence in the section; the paragraph does not spell out the seed/shape
split beyond "a test that moves off the live ledger to a frozen-seed fixture",
which I record without calling it a finding.

## The scratch-row proof

Appended a 59th row for `docs/reviews/2026-09-06-opus-review-pb11-P11b.md`
(exists, REJECTED, dated before `front_matter_from = 2026-09-07`), `git add`ed
it so the flake could see it, then reverted:

```
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml
59
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check ; echo EXIT=$?
EXIT=0
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> 175 passed in 5.09s
EXIT=0
$ nix develop -c pytest tests/evidence -q | tail -1
175 passed in 4.55s
```

After the revert: 58 rows, `git status --porcelain` empty, `git diff
1a9f146..HEAD -- docs/ledger` empty. No scratch row is left anywhere.

## Mutants

18 applied, 9 killed. A guard mutation counts as KILLED when removing the clause
demonstrably lets a contracted attack through (the clause is load-bearing).

| # | mutant | result |
|---|---|---|
| N1 | guard regex narrowed to `[0-9]+ rejections\b`; attack (b) re-run | KILLED — (b) now passes (`1 passed`), so the `rej` alternative is load-bearing |
| N2 | `_reads_live_ledger` → `return False`; attack (b) re-run | KILLED — (b) now passes |
| N3 | **the seed-fixture requirement dropped** | **SURVIVED — a no-op: the requirement is not implemented** |
| N4 | glob narrowed to `[HERE]`; attack (c) present | KILLED — (c) now passes |
| N5 | P3Arb-a: frozen test's `FROZEN_SEED` → `LIVE_LEDGER` | KILLED — `48 rej…` vs `58 rej…` |
| N6 | P3Arb-b: `RECORD_SHAPE` → `(.*)` | KILLED — the negative case, line 2742 |
| N7 | P3Arb-c: `assert "59 rej" in line` added to the shape test | KILLED — `test_tasks.py:test_live_record_line_shape_only:2747` |
| O1 | attack (a), main's body in a scratch file | KILLED |
| O2 | attack (c), `parents[2]` chain in a new file | KILLED |
| O3 | attack (d1), `os.path.join` joined path | **SURVIVED** |
| O4 | attack (d2), env-var path | **SURVIVED** |
| O5 | attack (d3), `.parent.parent.parent` joined path | **SURVIVED** |
| O6 | attack (e1), `f"59 rej"` literal | **SURVIVED** (`FSTRING_MIDDLE`, not `STRING`) |
| O7 | attack (e2), `"%d rej" % n` | **SURVIVED** (computed; contract targets literals) |
| O8 | one class flipped in the FROZEN fixture | KILLED — `1 failed, 174 passed` |
| O9 | one class flipped in the LIVE ledger (M11b) | SURVIVED — by design since P3Arb, now documented in the runbook |
| O10 | live literal inside an `async def` test | **SURVIVED** — `^def ` never matches; the body lands in no span |
| O11 | live literal inside a `class Test…` method | **SURVIVED** — same cause |
| O12 | live literal inside a function named `test_no_literal_record_count_against_live_ledger` in another file | **SURVIVED** — the self-exclusion (line 2485) is by bare name, repo-wide |

Robustness, matrix item 4: the tokeniser does not crash. Fed one file holding a
module docstring with "59 rejections", a decorated fixture, an `async def`, a
`class` with a method, and a nested `def`, it ran clean and reported only the
nested-def hit:

```
E   assert not ['test_scratch_rob.py:test_outer_with_nested:32']
$ grep -n '59 rej' tests/evidence/test_scratch_rob.py
1:"""Module docstring mentioning 59 rejections and rej."""
17:    """Docstring with 59 rej."""
19:    assert "59 rej" in seed.read_text()          <- async def, MISSED
25:        assert "59 rejections" in seed.read_text()  <- class method, MISSED
32:        return "59 rej" in seed.read_text()      <- caught
```

Runtime is not a concern: 5 files scanned, `0.01s call
test_no_literal_record_count_against_live_ledger` under `--durations`.

## Red before green

P3Arb's guard (`git -C /home/dalhaka/factory/ws/pb3arb2/P3Arb show
task/P3Arb:tests/evidence/test_tasks.py`, copied over the branch's file), each
attack in isolation:

```
--- P3Arb guard, attack (a) only ---   1 passed, 119 deselected in 0.12s
--- P3Arb guard, attack (c) only ---   1 passed, 119 deselected in 0.02s
--- P3Arb guard, attack (b) only ---   FAILED …test_no_literal_record_count_against_live_ledger
                                       1 failed, 119 deselected in 0.16s
```

(a) and (c) pass on P3Arb and fail on this branch — the contracted red. (b) as
the matrix words it ("a live-path literal inside the shape test") does **not**
pass on P3Arb, because the shape test spells `LIVE_LEDGER` and P3Arb's
identifier predicate catches exactly that; it was already killed as A3 in the
P3Arb gate. The P3Arb-evading form of (b) is the previous review's B1 (swap
`LIVE_LEDGER` for the inline path *and* add the literal). Correcting the
matrix's premise, not a finding against the seat. Restored, branch guard fails
(a) and (c) as tabled above.

## Checks

All from the fresh clone `…/scratchpad/gate-pb3ar2-P3Ar2` (branch `task/P3Ar2`,
head `5f3b2bd`, base `1a9f146`).

```
$ nix develop -c ruff check pkgs/evidence tests/evidence
All checks passed!                                   EXIT=0
$ nix develop -c ruff format --check pkgs/evidence tests/evidence
49 files already formatted                           EXIT=0
$ nix develop -c pytest tests/evidence -q
175 passed in 4.63s
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild
evidence-unit> 175 passed in 4.67s                   EXIT=0
$ nix build .#checks.x86_64-linux.lint -L --no-link
lint> Found 0 warnings and 0 errors.                 EXIT=0
$ nix develop -c githooks/pre-commit
render.test.mjs: all assertions passed               EXIT=0
$ nix develop -c python3 pkgs/evidence/repomap.py --root . write && git diff --exit-code docs/MAP.md
MAP-CLEAN
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check ; echo EXIT=$?
EXIT=0        (silent)
$ git diff 1a9f146..HEAD -- docs/ledger
(empty)
$ git status --porcelain
(clean)
```

Commit convention: `git rev-list --count 1a9f146..HEAD` → `1`; the subject is
byte-identical to the plan's `commit subject` line (`cmp` passes); `Generated-By:`
and `Co-Authored-By:` follow a blank line; the four touched files are
`tests/evidence/test_tasks.py`, `tests/evidence/fixtures/ledger/plan-defects-seed.toml`
and `docs/runbooks/evidence.md` (all in `touches`) plus `docs/MAP.md` by rule;
`flake.nix` correctly untouched (`evidence-unit` green proves the sandbox
already carries `tests/evidence/fixtures/ledger/`); no board commit. The body
pastes the two `evidence-unit` runs and a guard-red run (see the MINOR above on
which artefact it pastes).

## Findings

**MAJOR — contract item 2's first conjunct is missing, and the second does not
cover "any spelling"; the named mutant "the seed-fixture requirement dropped"
survives** (`tests/evidence/test_tasks.py:2453-2464`, used at 2487).

```python
def _reads_live_ledger(body):
    …
    if "LIVE_LEDGER" in body or re.search(r"parents\s*\[", body):
        return True
    return "docs/ledger/plan-defects.toml" in body
```

The contract requires the enclosing function's body to *reference the frozen
seed fixture path* **and** not reference the live ledger "in any spelling (a
joined path, a string literal, a `parents[2] / "docs" / "ledger"` chain)". Only
the negative half is implemented, and it is a three-alternative blacklist, so a
joined path — the first enumerated spelling — is not seen. Three runs, each
`1 passed, 119 deselected`: (d3) `root = HERE.parent.parent.parent; seed = root
/ "docs" / "ledger" / "plan-defects.toml"; assert "59 rej" in seed.read_text()`
— main's own defect with `parents[2]` respelled; (d1) the same via
`os.path.join(str(root), "docs", "ledger", "plan-defects.toml")`; (d2) the same
via `os.environ["LEDGER_PATH"]`. Because the whitelist conjunct is absent,
dropping "the seed-fixture requirement" is a no-op mutation and survives. Fix as
the contract words it: require
`"fixtures/ledger/plan-defects-seed.toml"` (or `FROZEN_SEED`) in the enclosing
body and reject otherwise — then the tmp-path spelling
`(repo / "docs" / "ledger" / "plan-defects.toml")` the docstring worries about
is safe for the right reason, and every joined live path is caught.

**MINOR — a literal count inside an f-string is invisible to the tokeniser**
(`tests/evidence/test_tasks.py:2478`, `if tok.type != tokenize.STRING`). On the
devShell's Python 3.14.7 `f"59 rej"` tokenises as `FSTRING_MIDDLE`; the probe
above shows the guard's STRING filter sees only the non-f literal. `assert
f"59 rej" in line` over the live ledger passes the guard. Pin: also accept
`tokenize.FSTRING_MIDDLE` (and keep `STRING`). The `"%d rej" % n` form (e2)
also passes; that one is a computed count and outside the contract's
literal-first wording — worth a sentence in the next plan round rather than a
code change now.

**MINOR — `async def` and class-method bodies are in no span**
(`tests/evidence/test_tasks.py:2428-2451`). `_test_function_spans` matches only
`^def NAME(`; an `async def` line, being non-blank and unindented, *closes* the
current span and starts none, and a `class` line does the same, so any literal
inside them has no enclosing function and is skipped. Proven above (lines 19 and
25 missed, line 32 caught). Latent — `tests/evidence` has no async or
class-based tests today. Pin: `^(?:async\s+)?def ` plus indented `def` handling,
or switch the span walk to `ast`.

**MINOR — the guard's self-exclusion is by bare function name, repo-wide**
(`tests/evidence/test_tasks.py:2485`). A function called
`test_no_literal_record_count_against_live_ledger` in *any* `test_*.py` is
skipped; a scratch file with that name holding `assert "59 rej" in
(HERE.parents[2] / "docs" / "ledger" / "plan-defects.toml").read_text()` gives
`1 passed, 119 deselected`. Pin the exclusion to `path == HERE` as well.

**MINOR — the commit body's "red on main" paste is of a scratch file, not
main's `test_tasks.py`.** Item 3 asks for "the run of the new guard against
main's `test_tasks.py` (checked out beside the branch)"; the body pastes
`test_scratch_defect.py:test_brief_record_line_over_seeded_ledger:16` and `:17`.
The claim is true — I reproduced the real run (`test_tasks_main.py:…:2636`) —
but the two-hit output at lines 16/17 is not reproducible from main's function,
which holds one matching literal.

**MINOR — the guard's regex requires exactly one space.** `[0-9]+ rej…`
(line 2474) is the contract's own wording, so this is not a deviation, but
`"57  rej"` or `"57 rej"` would evade. Recorded for the next round's
wording, not a defect against this seat.

## Verdict

**REJECTED.** One MAJOR: contract item 2 is half-implemented — the guard has no
positive requirement that the enclosing function read the frozen seed, and its
negative check misses the "joined path" spelling the contract names first, so
main's own defective test passes the guard once `parents[2]` is written
`.parent.parent.parent`, and the named mutant "the seed-fixture requirement
dropped" survives as a no-op. Everything else in the contract is met and every
check is green, so the fix round is one function: add the `FROZEN_SEED` /
`fixtures/ledger/plan-defects-seed.toml` whitelist conjunct, and prove it by
re-running shapes d1/d2/d3 above (all three must then fail). Fold in the
f-string token type, the `async def` / class-method spans, and the `path ==
HERE` self-exclusion while the file is open.
