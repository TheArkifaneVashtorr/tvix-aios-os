---
plan_defect: none
mutants_total: 12
mutants_killed: 9
mutants_outside_named: 3
---
# Opus gate — seat run ca1, task CA3 — APPROVED

## Summary

The section's contract is met literally. `ROUTE_IMPL_RE` is the plan's exact
literal with the non-capturing family group, the `task-result` fence's `route`
pattern is the plan's exact literal (ruff-wrapped, allowed), the SCHEMA sentence
is the plan's sentence, and `tests/evidence/fixtures/results/codex.result` is
byte-identical to the plan's fixture block (no trailing newline — the house
shape: `tests/evidence/fixtures/results/done.result` has none either). Five test
rows land, I1–I2 and P1–P3, all with the section's assertions. Red was shown
against the base implementation and the two lines the commit body pastes are the
two lines pytest prints. `evidence-unit` and `lint` are green in a fresh clone
under `--rebuild`, `githooks/pre-commit` green and idempotent, `ruff check` /
`ruff format --check` clean, `repomap write` leaves `docs/MAP.md` unchanged,
`tasks.py … check` silent at exit 0. One commit, subject byte-identical,
trailers correct, plan file untouched, the diff inside `touches` plus the two
by-rule exemptions.

Of the nine mutants the section names, eight die. One survives — I2's `re.match
instead of fullmatch` — and it survives because it is an **equivalent** mutant:
`ROUTE_IMPL_RE` carries a `$` anchor, so switching `fullmatch` to `match` changes
no behaviour. I applied the mutant the plan meant (`re.match` **and** the `$`
dropped) and it dies on the `codex/code/XS/x` row, so the assertion is
load-bearing and the implementation is stronger, not weaker, than the plan
assumed. I record that as a plan-text MINOR rather than a MAJOR: rejecting on it
would reject a correct change for the plan's own false premise. Three MINORs
total, none gating.

The driver's own record is confirmed against the tree: `touches_extra: 0` holds
(§Touches), and `checks_scope: dirty` here means only that the branch diff
touches `tests/` — `factory-task:318` computes it from
`git diff --name-only "$base_sha..task/$key"`, i.e. from the **committed**
branch, not from a dirty worktree. The three names it lists are exactly the
three test-tree files of the commit. So yes: the committed tests are what the
driver's checks ran against, and my own `--rebuild` runs in a fresh clone of the
same commit reproduce them independently.

## Contract items

Line numbers are in the fresh clone at `49ca535`.

1. **`ROUTE_IMPL_RE` literal, non-capturing family group.**
   `pkgs/evidence/ingest_result.py:37`:
   `ROUTE_IMPL_RE = re.compile(r"^(?:implement|codex)/(code|docs)/(XS|S|M|L)$")`
   — byte-identical to the Interfaces line. `_route_fields`
   (`pkgs/evidence/ingest_result.py:87-95`) is untouched, so it still returns
   `(route_line, m.group(1), m.group(2))`. **Met.**

2. **`codex/code/XS` → `("codex/code/XS", "code", "XS")`.** Asserted end-to-end
   through the CLI at `tests/evidence/test_ingest_result.py:237-239`; the
   `codex/docs/M` arm at `:284-286`. **Met.**

3. **`codex/any/any`, `codex/code/XL`, `Codex/code/XS`, `codex/code/XS/x` →
   `unknown`/`unknown`/`unknown`, never a refusal.**
   `tests/evidence/test_ingest_result.py:264-278` loops one payload per rule and
   asserts all three fields `unknown` after `assert r.returncode == 0`. The
   "never a refusal" half is carried by the exit code, not by a separate
   message assertion — and it is real: under mutant M4 the refusal path raises
   the CLI's exit to 1 and the same assertion fires. **Met.**

4. **`seat: codex <uuid>` matches neither `SEAT_UNIT_RE` nor `SUBMIT_FAILED_RE`.**
   Both constants are unchanged (`pkgs/evidence/ingest_result.py:33-36`). The
   `seat_unit is None` half is asserted at
   `tests/evidence/test_ingest_result.py:252` and is load-bearing (mutant M3
   kills it). The `submit_failed False` half has no discriminating assertion —
   MINOR-2. **Met in the code, half-tested.**

5. **The fence pattern.** `pkgs/evidence/streams.py:286-289`:
   `"route": (\n "re",\n r"^(explicit|unknown|(implement|codex)/(code|docs)/(XS|S|M|L))$",\n )`
   — the plan's literal, rewrapped by `ruff format` (Global Constraints allow
   it). The refusal message `route: not a re` comes from the untouched `re`-class
   arm of `streams.validate` and is asserted at
   `tests/evidence/test_streams_policy.py:382-384`. **Met.**

6. **The SCHEMA row.** `pkgs/evidence/SCHEMA.md:15`:
   `` `route` in `explicit|unknown|implement/<kind>/<size>|codex/<kind>/<size>` (`<kind>` in `code|docs`, `<size>` in `XS|S|M|L`), ``
   — the plan's sentence, inserted between the `status` clause and the `derived`
   clause of the `derived/tasks` sentence. No test pins it (MINOR-3). **Met.**

7. **The fixture.** `tests/evidence/fixtures/results/codex.result`, 30 lines.
   Extracted the plan's fenced block and diffed: lines 1–30 identical, the only
   difference the absent trailing newline, which matches `done.result`. Made-up
   UUID `0f1e2d3c-…`, no key material, gone workspace. **Met.**

8. **Row I1's full assertion set.** `tests/evidence/test_ingest_result.py:221-255`
   asserts `route`, `task_kind`, `size`, `model`, `effort`, `commits`,
   `commits_declared`, the six-key `usage` dict, `seat_unit is None`,
   `error_class`, `repo is None`, `files_changed == 15`, `returncode == 0` and
   `"ingested 1 rows into derived/tasks (0 refused)" in r.stdout`. Every item the
   section names is present. **Met.**

9. **Rows P1–P3.** `test_route_accepts_every_supported_family_and_arm`
   (`tests/evidence/test_streams_policy.py:367-373`) parametrized over the
   section's five values; `test_route_refuses_outside_the_fence` (`:376-384`)
   over the section's four; `test_route_regex_is_the_literal_pin` (`:387-390`)
   pins the pattern string. **Met.**

10. **Nothing else in the tree pins the old pattern.**
    `grep -rn 'implement/(code' --include='*.py' --include='*.sh' --include='*.nix' .`
    → no hit outside `docs/`. `tools/factory/seat/factory-task:112` still writes
    `route_label="implement/$kind/$size"`, which is CA1's line, not CA3's.
    **Met.**

## Red before green

Base implementation files checked out over the branch's tests
(`git checkout b440969 -- pkgs/evidence/ingest_result.py pkgs/evidence/streams.py`),
then restored.

`nix develop -c pytest tests/evidence/test_ingest_result.py -q -k codex`:

```
E       AssertionError: assert 'unknown' == 'codex/code/XS'
E       AssertionError: assert 'unknown' == 'codex/docs/M'
FAILED tests/evidence/test_ingest_result.py::test_codex_result_ingests_one_full_row
FAILED tests/evidence/test_ingest_result.py::test_codex_route_family_arms
2 failed, 19 deselected in 0.42s
```

`nix develop -c pytest tests/evidence/test_streams_policy.py -q -k route`:

```
E       AssertionError: assert ['route: not a re'] == []
E       AssertionError: assert '^(explicit|u.../(XS|S|M|L))$' == '^(explicit|u.../(XS|S|M|L))$'
E         - ^(explicit|unknown|(implement|codex)/(code|docs)/(XS|S|M|L))$
E         + ^(explicit|unknown|implement/(code|docs)/(XS|S|M|L))$
FAILED …::test_route_accepts_every_supported_family_and_arm[codex/docs/M]
FAILED …::test_route_accepts_every_supported_family_and_arm[codex/code/XS]
FAILED …::test_route_regex_is_the_literal_pin
3 failed, 11 passed, 186 deselected in 0.06s
```

The two lines the commit body pastes — `assert 'unknown' == 'codex/code/XS'` and
`assert ['route: not a re'] == []` — are verbatim what pytest prints. Restored,
`221 passed in 5.71s`.

`test_route_refuses_outside_the_fence` passes at base, as it must (the base fence
refuses the whole `codex/` family); its red is its named mutant M8, below.

Note on the section's Step 2 command: `-k 'codex or route_literal'` selects the
two parametrized-`codex` ids but **not** `test_route_regex_is_the_literal_pin`
(no `route_literal` substring in the name). I used `-k route`, which selects all
three. A plan-text slip only; the row is red at base either way.

## Mutants

12 applied, 9 killed. Every mutant was applied in the clone, the killing test
run, then `git checkout HEAD -- pkgs/evidence`.

| # | named? | mutant | test that must kill it | result |
|---|---|---|---|---|
| M1 | I1 | `ROUTE_IMPL_RE` left at `^implement/(code\|docs)/(XS\|S\|M\|L)$` | `test_codex_result_ingests_one_full_row` | **killed** |
| M2 | I1 | capturing family group `^(implement\|codex)/…` | same | **killed** |
| M3 | I1 | `SEAT_UNIT_RE` widened to `^seat: (?:unit seat@\|codex )([0-9a-f-]{6,})$` | same | **killed** |
| M4 | I2 | `([a-z]+)` for the kind, `(XS\|S\|M\|L\|[a-z]+)` for the size | `test_codex_route_family_arms` | **killed** |
| M5 | I2 | `re.match` instead of `fullmatch` | `test_codex_route_family_arms` | **survived (equivalent)** |
| M6 | I2 | `re.IGNORECASE` | `test_codex_route_family_arms` | **killed** |
| M7 | P1 | streams regex left at `^(explicit\|unknown\|implement/…)$` | `test_route_accepts_every_supported_family_and_arm` | **killed** |
| M8 | P2 | `…\|codex/[a-z]+/[a-zA-Z]+)$` | `test_route_refuses_outside_the_fence` | **killed** |
| M9 | P3 | any drift of the pattern | `test_route_regex_is_the_literal_pin` | **killed** (fired under both M7 and M8) |
| M5b | outside | the `$` anchor dropped, `fullmatch` kept | `test_codex_route_family_arms` | **survived (equivalent)** |
| M5c | outside | `re.match` **and** the `$` dropped — the mutant I2 meant | `test_codex_route_family_arms` | **killed** |
| M10 | outside | `SUBMIT_FAILED_RE` widened to `^seat: (?:submit failed\|codex )` | whole `tests/evidence` suite | **survived** |

Killing lines, pasted.

M1: `E AssertionError: assert 'unknown' == 'codex/code/XS'`.

M2 (`ROUTE_IMPL_RE = re.compile(r"^(implement|codex)/(code|docs)/(XS|S|M|L)$")` —
`m.group(1)` becomes the family):

```
E  AssertionError: evidence: ingest result: …/cx1b/CX1b.result: task_kind: not in enum (code|docs|unknown)
E    evidence: ingest result: …/cx1b/CX1b.result: size: not in enum (XS|S|M|L|unknown)
E  assert 1 == 0
```

M3:

```
E  AssertionError: evidence: ingest result: …/cx1b/CX1b.result: seat_unit: not a re
E  assert 1 == 0
FAILED tests/evidence/test_ingest_result.py::test_codex_result_ingests_one_full_row
```

M4:

```
E  AssertionError: evidence: ingest result: …/cx1b/CX2.result: task_kind: not in enum (code|docs|unknown)
E    … size: not in enum (XS|S|M|L|unknown)
E    … route: not a re
FAILED tests/evidence/test_ingest_result.py::test_codex_route_family_arms
```

M6:

```
E  AssertionError: evidence: ingest result: …/cx1b/CX2.result: route: not a re
FAILED tests/evidence/test_ingest_result.py::test_codex_route_family_arms
```

M7: `E AssertionError: assert ['route: not a re'] == []` (twice, the two `codex`
params) plus the literal-pin failure.

M8: `E AssertionError: assert [] == ['route: not a re']` (twice) plus
`assert '^(explicit|u...+/[a-zA-Z]+)$' == '^(explicit|u.../(XS|S|M|L))$'`.

M5 and M5b, both surviving — `2 passed, 19 deselected`. Cause: the pattern is
`^…$`-anchored, so `match` and `fullmatch` agree on every input, and dropping `$`
under `fullmatch` also changes nothing. The two edits combined (M5c) do change
behaviour and die:

```
E  AssertionError: evidence: ingest result: …/cx1b/CX2.result: route: not a re
E  assert 1 == 0
FAILED tests/evidence/test_ingest_result.py::test_codex_route_family_arms
1 failed, 1 passed, 19 deselected in 0.33s
```

So the `codex/code/XS/x` row of I2 is load-bearing against the weakening the plan
was aiming at; only the plan's one-line spelling of it is inert. MINOR-1.

M10 survived the entire suite (`453 passed, 1 skipped`) — MINOR-2.

## Checks

All run in the fresh clone at `49ca535`, worktree clean, `XDG_CACHE_HOME` under
the session scratchpad.

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | `454 passed in 12.62s`, exit 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | exit 0 |
| `nix develop -c githooks/pre-commit` | exit 0; `git status --porcelain` empty after it (the queue block is already current) |
| `nix develop -c pytest tests/evidence -q` | `453 passed, 1 skipped in 12.00s` |
| `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | both exit 0 — MAP is current |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . --runs-dir /nonexistent --store /nonexistent check` | silent, exit 0 |

No red check.

## Touches and commit

Diff `b440969..49ca535`, 8 files:

```
 docs/MAP.md                                  |  2 +-
 docs/OPERATIONS.md                           |  2 +-
 pkgs/evidence/SCHEMA.md                      |  1 +
 pkgs/evidence/ingest_result.py               |  2 +-
 pkgs/evidence/streams.py                     |  5 +-
 tests/evidence/fixtures/results/codex.result | 30 ++++++++++++
 tests/evidence/test_ingest_result.py         | 68 ++++++++++++++++++++++++++++
 tests/evidence/test_streams_policy.py        | 27 +++++++++++
 8 files changed, 133 insertions(+), 4 deletions(-)
```

Six are the section's `touches`, exactly. The two others are the Global
Constraints' standing exemptions:

- `docs/MAP.md` — one line, the `tests/evidence` file count `87 → 88`, i.e. the
  generator's output for the new fixture. `repomap.py write` reproduces it
  byte-for-byte (`git diff --exit-code` clean).
- `docs/OPERATIONS.md` — `git diff --numstat` is `1 1`, and `git diff -U0` shows
  the single changed line is **line 15**, with the fences at lines 14
  (`<!-- tasks:begin -->`) and 16 (`<!-- tasks:end -->`). The change is `CA3`
  dropping out of the derived Queued list. No other line of the board moved.
  Expected, not a finding.

`touches_extra: 0` in `~/factory/runs/ca1/CA3.result` is therefore correct.

Commit: `git rev-list --count b440969..HEAD` → `1`. Subject compared byte-for-byte
with `cmp` against the section's `commit subject` — identical, em dash and all.
Body states the why, pastes both red lines, and carries the two trailers on their
own lines after a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run ca1)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

No board-only commit; the plan file is not in the diff; no `Deviation:` line was
owed.

## Findings

**MINOR-1 — the section's I2 mutant `re.match instead of fullmatch` is an
equivalent mutant (plan text, wrong-fact).**
`docs/superpowers/plans/2026-09-08-codex-driver-arm.md:786` (the I2 row):
"`re.match` instead of `fullmatch` → the `/x` suffix accepted". It is not
accepted: `pkgs/evidence/ingest_result.py:37` ends the pattern with `$`, so
`ROUTE_IMPL_RE.match("codex/code/XS/x")` is `None` exactly as `fullmatch` is.
Measured — mutant applied, `2 passed, 19 deselected`; the same for dropping `$`
alone. The mutant the row means is both edits at once, and that one dies
(`route: not a re`, `1 failed`). No action owed on the branch; the plan's mutant
sentence should say "`re.match` **and** the `$` anchor dropped".

**MINOR-2 — the Interfaces' `submit_failed` `False` clause has no discriminating
test.** `pkgs/evidence/ingest_result.py:308` computes `submit_failed`, and its
only consumer is `fallback_error_class` (`:249`), which the ingest calls **only**
when the file carries no `error_class:` line
(`pkgs/evidence/ingest_result.py:310-315`). The fixture carries
`error_class: none` (`tests/evidence/fixtures/results/codex.result:18`), so the
`error_class == "none"` assertion at
`tests/evidence/test_ingest_result.py:253` would hold whatever `submit_failed`
were. Measured: widening `SUBMIT_FAILED_RE` to `^seat: (?:submit failed|codex )`
leaves the whole suite green — `453 passed, 1 skipped`. The code is right (the
literal `seat: submit failed` prefix cannot match `seat: codex …`); only the
stated contract is unpinned. A fixture variant with the `seat: codex` line and
no `error_class:` line, asserting `error_class == "none"` rather than
`"submit-failed"`, would close it.

**MINOR-3 — the SCHEMA.md contract has no test.** `pkgs/evidence/SCHEMA.md:15` is
the section's stated interface, and nothing under `tests/evidence` reads
`SCHEMA.md` (`grep -rn 'SCHEMA' tests/evidence/*.py` → no hit). The doc can drift
from `streams.KINDS` with every check green. This is the house's pre-existing
state, not something CA3 introduced, and the section named no test for the row;
recorded because rule 7 asks for it.

No MAJORs.

## Verdict

**APPROVED.** Every numbered contract item is met at the literal level, the tests
are red at base and green at head with the commit body's pasted lines matching
pytest's, both acceptance checks and every ancillary gate are green in a fresh
clone under `--rebuild`, the diff is inside `touches` plus the two by-rule
exemptions (the `docs/OPERATIONS.md` hunk is line 15 only, strictly inside the
queue fences), and the commit is one, with a byte-identical subject and both
trailers. Eight of the nine named mutants die; the ninth is provably equivalent
and the assertion behind it kills the weakening the plan was aiming at, which I
record as a plan-text MINOR rather than a MAJOR — rejecting on it would reject a
correct change for the plan's own arithmetic. Three MINORs, none gating, none
owed on the branch.
