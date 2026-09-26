---
plan_defect: implementer
plan_defect_secondary: missing-case
mutants_total: 54
mutants_killed: 44
mutants_outside_named: 4
reviewer: opus
majors: 7
minors: 7
---
# Opus gate — seat run tel1b, task T1 — REJECTED

## Summary

The fence is real and mostly well built: `pkgs/evidence/streams.py` declares every kind
of the section's table, `append` validates before the lock, `replace_stream` merges by key
under one flock with a tmp+fsync+`os.replace` swap, `judgements` delegates, the ingest
table dispatches, and the four acceptance checks are green on a fresh clone with
`--rebuild` (evidence-unit 240 passed, factory-unit, unit 486 ok, lint). 44 of the 54
mutants I applied die.

It is rejected on the test side, not the code side. Four mutants the section itself names
survive the committed suite: deleting an arm from `round_kind`, `reviewer`, `effort`
(row 13's "delete an arm from the tuple"), removing the `ts`-preservation rule for an
equal row (rows 20 and 21), dropping the enum-key exemption at its map site (row 7), and
removing `task-result`'s declared `kind` field (row 1). The first three are the
implementer's: row 13 asks for *every* arm parametrised and got one arm per enum; the
`replace_stream` equal-row rule is asserted on a row that is not in the replacement set
and on a byte-comparison that only holds because `now_iso()` has second resolution; the
name fence exempts every `enum`-classed field, which is broader than the section's stated
exemption and makes the map-site guard dead code. The fourth is the plan's: `ENVELOPE`
declares `kind` unvalidatable while `task-result` declares a *field* called `kind`, so
that field can never be reached — a collision T2 will walk into. Finally the diff touches
`tests/unit/83-plan-brief.bats`, outside the section's `touches`, and the commit body does
not say why.

## Contract items

Numbered as the section's Interfaces states them.

1. **`streams.py` stdlib only, no sibling imports** — met. `pkgs/evidence/streams.py:13-17`
   imports `json`, `os`, `re` only.
2. **The class grammar** (`id`, `model-id`, `key`, `rev`, `ts`, `hash`, `int`,
   `("int",lo,hi)`, `num`, `bool`, `enum`, `path`, `text`, `re`, `null`, `obj`, `list`,
   `map`) — met, `streams.py:21-26` and `streams.py:543-604`; every regex is byte-identical
   to the section's.
3. **`FORBIDDEN` verbatim, compared by `name.lower().replace("-","_")`, at every depth** —
   met: `streams.py:33-92` (55 names, the design §3.5 list), `streams.py:490-491`, walked at
   `streams.py:607-621` (obj), `635-648` (map), `682-694` (row). Exemptions diverge — see
   MAJOR-3.
4. **`SECRET_RE`, one alternation, scanned in every string value and every map key at every
   depth** — met: `streams.py:94-97`, applied in `_check` (`streams.py:655-656`) which every
   value and every map key passes through (`streams.py:647`).
5. **`ENVELOPE`, `MAX_BYTES = 16384`, `MAX_DEPTH = 8`** — met literally (`streams.py:28-30`,
   `684`, `708`, `652`); the `kind` arm of `ENVELOPE` collides with a declared field — see
   MAJOR-4.
6. **`KINDS[kind] = {stream, v, key, fields}`; `factory-run` carries `shapes` chosen by
   `driver`** — met: `streams.py:147-475`; every kind, field and class of the section's
   table is present, in the section's order; `_fields_for` (`streams.py:670-679`) returns A
   when `driver` is absent, B on `"seat"`, and `validate` returns exactly
   `["driver: not in enum (seat)"]` otherwise (`streams.py:704-705`).
7. **`validate(kind,row) -> list[str]`, never raises, exact strings** — met for the strings a
   test exercises (`undeclared kind`, `undeclared field`, `forbidden name`, `not in enum`,
   `not a id`, `not a re`, `not a map`, `over cap`, `outside root`, `'..' segment`,
   `newline`, `secret shape`, `null not allowed`, `row over 16384 bytes`, `depth over 8`).
   Eleven of the stated `not a {class}` strings have no test — MINOR-2.
8. **An undeclared subtree is not descended; a declared deep obj reports `depth over 8`** —
   met: `streams.py:688-691` short-circuits, `652-654` caps; pinned at
   `tests/evidence/test_streams_policy.py:452-465` (1,000-deep payloads, no `RecursionError`).
9. **`stream_of`, `key_of`, `StreamRefused(.errors, "; ".join)`** — `stream_of`
   (`streams.py:714`) and `StreamRefused` (`streams.py:478-484`) met and used; `key_of`
   (`streams.py:719-724`) is dead and untested — MINOR-1.
10. **`STREAM_RE` = closed set of two subdirectories** — met: `evidence.py:32`; pinned at
    `test_streams_policy.py:733-741` (`other/tasks`, `derived/../x`, `derived/Tasks` all
    `ValueError`).
11. **`append`: `stream_path` first, then validate, then the stream binding, then the lock;
    `v` from the kind** — met and correctly ordered: `evidence.py:68-78`; refusal raises
    before `os.open` (`evidence.py:78`). Pinned at `test_streams_policy.py:544-556`.
12. **`replace_stream`: all-or-nothing with `row {i}: ` prefixes, key required, one flock,
    torn lines dropped, equal row keeps `ts`, changed row restamped, new key appended,
    0640+fsync tmp, `os.replace`, directory fsync, parent 0750, returns the row count** —
    all met in code (`evidence.py:115-193`) but the equal-row `ts` rule has no test that can
    fail — MAJOR-2. The parent chmod is unconditional — MINOR-5.
13. **CLI `record` / `record-check` exit 2 with `evidence: refused: {reason}` and no file** —
    met: `evidence.py:511-517`, `533-539`; pinned at `test_streams_policy.py:684-731`
    (returncode 2, stderr text, `checks.jsonl` absent).
14. **`INGEST_MODULES` and the two error strings** — met: `evidence.py:34-38`, `430-449`;
    both messages byte-exact and exit 2 (`test_streams_policy.py:772-816`). The target name
    is also forwarded as a positional — MINOR-3; `except ImportError` is too wide — MINOR-4.
15. **`DEFAULT_STORE` the one literal; `tasks.py`/`judgements.py`/`report.py` take
    `EVIDENCE_STORE or evidence.DEFAULT_STORE`** — met: `grep -rn '/var/lib/evidence'
    pkgs/evidence/` returns only `evidence.py:31` (plus SCHEMA.md prose); `tasks.py:1596,1609`
    (lazy `import evidence` inside `main`), `judgements.py:330`, `report.py:265`. The removed
    global `VERSION` has no remaining consumer (`grep -rn '\bVERSION\b' pkgs tests tools` →
    only `tools/ledger/factory.py`).
16. **`judgements.FIELDS = streams.judgement_fields()`, literal deleted, delegation only on a
    clean row, existing messages byte-identical** — met: `judgements.py:35`,
    `judgements.py:208-217`; the literal tuple is gone (the test greps the source, and the
    independent 14-name literal in `tests/evidence/test_judgements.py:38-53` still pins the
    set). MINOR-6 on the tautological half of the assertion.
17. **`factory-lib.sh` passes `--store` only when `EVIDENCE_STORE` is set** — met:
    `tools/factory/seat/factory-lib.sh:92,95`, the `local store=` line gone.
18. **`flake.nix` `factory-unit` copies `streams.py`** — met: `flake.nix:1106`.
19. **`SCHEMA.md`: the rule, the subdirectories, the two derived streams** — met:
    `pkgs/evidence/SCHEMA.md:6-15`.
20. **Three `test_evidence.py` fixtures use declared kinds** — met: `test_evidence.py:59,65,68`
    (`prefix` instead of `n`), `:262-264` (`record runs`), `:300-302` (the concurrency
    subprocess declares `t`).

## Red before green

The section's Step 2 red, run in a second clone with `pkgs/evidence/{evidence,judgements,tasks,report}.py`
checked out at the base `4a334c2` and `streams.py` removed:

```
$ nix develop -c pytest tests/evidence/test_streams_policy.py -q -p no:cacheprovider
tests/evidence/test_streams_policy.py:29: in _load
    src = next(p for p in candidates if p.exists())
E   StopIteration
ERROR tests/evidence/test_streams_policy.py - StopIteration
1 error in 0.10s
```

That is the `StopIteration` reading of Step 2 (errata 19 notes the section names its red two
ways; the loader raises `StopIteration`, never `ModuleNotFoundError`).

A collection error alone does not show any assertion failing, so I ran the stronger red:
`streams.py` restored, `evidence.py`/`judgements.py` still at the base —

```
12 failed, 38 passed in 2.31s
FAILED test_append_refuses_before_writing            FAILED test_replace_stream_atomic
FAILED test_stream_re_allows_subdirectories          FAILED test_replace_stream_drops_torn_line_and_creates_derived
FAILED test_replace_stream_replaces_by_key_preserving_ts  FAILED test_replace_stream_no_key_kind_refused
FAILED test_replace_stream_idempotent                FAILED test_cli_record_refuses_and_exits_2
FAILED test_replace_stream_all_or_nothing            FAILED test_cli_record_check_refused_on_secret
FAILED test_ingest_table                             FAILED test_judgements_delegate
```

Green at the head, in the clone: `nix develop -c pytest tests/evidence -q` → `239 passed,
1 skipped in 7.03s`, matching the commit body.

Two of the section's rows cannot fail as written, whatever the implementation does — rows 20
and 21's equal-row `ts` rule (MAJOR-2) and row 13's unvisited enum arms (MAJOR-1).

## Mutants

54 applied, 44 killed, 10 survived; 4 were outside the section's named set.

Killed (named, one line each, reverted after): row 1 remove `check.src`
(`src: undeclared field`); row 2 `value not in cls[1] or True`; row 3 unknown kind returns
`[]`; row 4 drop the `path` arm of `_name_fence` (`assert True is False` on
`_name_fence('file', ('path', ('',), 200))`) and add `"output": "int"` to `check`
(`AssertionError: output`); row 5 drop the `forbidden name` reason; row 6 both halves
(allowlist, name fence); row 7 skip the `obj` walk (`'usage.output: forbidden name' in []`);
row 8 admit `/` and `@` in `ID_RE`; row 9 `SECRET_RE.search` → `None`, and dropping the two
`\b` anchors (`age1` then fires on `stage1qxyz`); row 11 `n > MAX_BYTES` → `>=`
(`row over 16384 bytes (16384)`); row 12 remove the depth cap (`RecursionError`); row 13
deleting `provider-error`, `killed`, `boot-failure` from `ERROR_CLASSES` (the misspelling
assertion pins the joined arm list byte-exactly); row 14 map cap `>` → `>=` and dropping the
key check; row 15 each of the four path rules separately (`'..'`, newline, cap, root); row 16
make every class nullable; row 17 both halves (validate after the write, drop the stream
binding); row 19 widen the subdirectory regex to `[a-z]+/`; row 20 replace by position
(`assert 2 == 3`) and restamp every carried-over row; row 22 skip the pre-write refusal;
row 23 write in place (`open(path, "w")`); row 24 keep torn bytes (`KeyError: 'i'`) and drop
the 0750 chmod (`assert 493 == 488`); row 25 default the key to `()`; row 26 and row 27 catch
nothing (`assert 1 == 2`); row 28 drop the table lookup (`KeyError: 'bogus'`); row 29 restore
the literal tuple and delegate before the raw checks; row 30 make an absent `driver` select
shape B (`run_id: null not allowed`).

Survivors:

| mutant | the row that names it | result |
|---|---|---|
| delete `"replan"` from `round_kind` | 13 | `239 passed, 1 skipped` |
| delete `"fable"` from `reviewer` | 13 | `239 passed, 1 skipped` |
| delete `"low"` from `task-result.effort` | 13 | `239 passed, 1 skipped` |
| delete `"openrouter"` from `gate-verdict.route` | 13 | `239 passed, 1 skipped` |
| delete `"missing"` from `checks_parse` | 13 | `239 passed, 1 skipped` |
| delete `"process"` from `PLAN_DEFECTS` | 13 | `239 passed, 1 skipped` |
| `if k in merged and _strip_env(...) == _strip_env(row)` → `if False` (restamp an equal row) | 20, 21 | `239 passed, 1 skipped` |
| drop `not enum_keys and` at `evidence`'s map site (`streams.py:645`) | 7 | `239 passed, 1 skipped` |
| remove `"kind": ("enum", ("code","docs","unknown"))` from `task-result` | 1 | `239 passed, 1 skipped` |
| declare a second `("text", 200)` field on `check` | — (outside; errata 12) | `239 passed, 1 skipped` |

Outside the named set (4): dropping the `text` cap check (killed — row 10 names no mutant);
renaming the `tiles` field (killed, 4 tests); declaring a second `text` field (survived,
errata 12); giving `check` a `key` (killed by row 25's test — errata 16's proposed assertion
is incidentally covered for this kind, though the append/replace lock interaction it names
is still unstated and untested).

## Checks

Every command run inside the fresh clone
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/2e56f544-dc33-4c36-836e-c2b840c3e5fc/scratchpad/gate-tel1b-T1/gate-tel1b-T1`
(cloned from `/home/dalhaka/factory/ws/tel1b/T1`, branch `task/T1`, head `a8c2e34`).

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | exit 0 — `240 passed in 7.06s` |
| factory-unit | same, `factory-unit` | exit 0 — `plan.test.mjs: all assertions passed` |
| unit | same, `unit` | exit 0 — `ok 486 …` |
| lint | same, `lint` | exit 0 — `Found 0 warnings and 0 errors.` |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 **only** on the derived board block: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. The regeneration is the mechanical consequence of T1 landing (`… SB6 T1` → `… SB6 T1W T2 T3`), it is one of the Global Constraints' two never-a-deviation exceptions, and the branch correctly carries no board commit. With the regenerated board staged the hook exits 0. |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | exit 0 — `All checks passed!` |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | exit 0 — `62 files already formatted` |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0 — no drift |
| task graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | exit 0, silent |

No check is red. The orchestrator's fact (1) is confirmed independently: the four acceptance
checks build clean on `task/T1`, so the driver's `status=failed` came from the malformed
result block alone, not from the work.

## Touches and commit

Diff against `4a334c2`: 12 files. Ten are the section's `touches`; `docs/MAP.md` is the
by-rule exception. The twelfth, `tests/unit/83-plan-brief.bats:166`, is outside the list and
unexplained — MAJOR-5.

Commit convention: exactly one commit (`a8c2e34`). The subject is byte-identical to the
section's `commit subject` (verified by comparison against the plan file's line). The body
states the why, pastes the red (`StopIteration` at
`tests/evidence/test_streams_policy.py:29`) and the green (`239 passed, 1 skipped`; the four
checks), and carries the two trailers after a blank line
(`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 …`,
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`). No board commit; the plan file is
untouched (`git diff … -- docs/superpowers/plans/` is empty). The body never mentions
`tests/unit/83-plan-brief.bats`.

## Findings

### MAJOR-1 — row 13's named mutant survives for three of the six enums it names

`tests/evidence/test_streams_policy.py:466-477`. The section's row 13 reads "every arm of
`task-result.status`, `error_class`, `effort`, `gate-verdict.verdict`, `round_kind`,
`reviewer` accepted (parametrised)". The committed parametrisation carries **one** arm per
enum:

```python
        ("task-result", TASK_RESULT, "status", "partial"),
        ("task-result", TASK_RESULT, "error_class", "provider-error"),
        ("task-result", TASK_RESULT, "effort", "xhigh"),
        ("gate-verdict", GATE_VERDICT, "verdict", "rejected"),
        ("gate-verdict", GATE_VERDICT, "round_kind", "fix"),
        ("gate-verdict", GATE_VERDICT, "reviewer", "deepseek"),
```

`status`, `error_class` and `verdict` survive by luck — their misspelling assertions
(`:481-495`) pin the whole joined arm list, so deleting any arm is caught. `round_kind`,
`reviewer` and `effort` have no such pin. Each deletion below was applied to
`pkgs/evidence/streams.py` in a scratch clone and reverted; the full suite is silent:

```
--- arm-round_kind-replan  -> SURVIVED    239 passed, 1 skipped in 7.98s
--- arm-reviewer-fable     -> SURVIVED    239 passed, 1 skipped in 7.30s
--- arm-effort-low         -> SURVIVED    239 passed, 1 skipped in 7.31s
--- arm-route-openrouter   -> SURVIVED    239 passed, 1 skipped in 7.27s
--- arm-checks_parse-missing -> SURVIVED  239 passed, 1 skipped in 7.25s
--- arm-plan_defects-process -> SURVIVED  239 passed, 1 skipped in 7.87s
```

This is not cosmetic: `round_kind: "replan"` and `reviewer: "fable"` are arms T3 will write,
and a missing arm refuses the whole `gate-verdict` row at ingest time with nothing in T1's
suite to catch the loss.

### MAJOR-2 — the `replace_stream` equal-row `ts` rule has no test that can fail

`pkgs/evidence/evidence.py:166-168` implements the section's rule ("an incoming row equal to
the existing one ignoring `v`/`ts` keeps the existing `ts`"). Rows 20 and 21 both name
"restamp `ts` on an equal row" as the mutant. It survives:

```
--- M20a (if k in merged and _strip_env(...) == _strip_env(row):  ->  if False:) -> SURVIVED
    239 passed, 1 skipped in 7.30s
```

Two independent reasons. (a) `test_replace_stream_replaces_by_key_preserving_ts:579-607`
asserts `rows[0]["ts"] == "2026-09-05T12:00:00Z"` for the `(1,1)` row — but `(1,1)` is not in
the replacement list (`(1,2)` and `(2,1)` are), so it is a carried-over row whose `ts` no
implementation would touch. The section's own discriminating fixture, "the equal-row `ts` in
`replace_stream`", is never built. (b) `test_replace_stream_idempotent:610-628` compares file
bytes across two back-to-back calls, and `now_iso()` (`evidence.py:51-52`) has one-second
resolution, so the restamped `ts` is identical anyway. Proof, in the scratch clone, with a
1.1 s gap inserted between the two calls:

```
A) unmutated code + 1.1s between the two calls: PASS
B) mutant 'restamp ts on an equal row' + 1.1s between the calls: FAIL
E         At index 58 diff: b'3' != b'2'
tests/evidence/test_streams_policy.py:631: AssertionError
```

The rule is correct in the code and passes on the clock, not on the assertion. A row equal to
its stored copy is exactly what the T2/T3 ingestors will hand `replace_stream` on every rerun.

### MAJOR-3 — the name-fence exemption is wider than the stated contract, and its map-site guard is dead

`pkgs/evidence/streams.py:494-500`:

```python
def _name_fence(name, cls=None):
    if isinstance(cls, tuple) and cls[0] in ("path", "enum"):
        return False
    return _forbidden_name(name)
```

The section states two exemptions and only two: "except a map whose key class is a closed
enum … and except a declared field of class `path`". The code adds a third — any declared
field whose class is an `enum` is exempt from the name fence — which is not stated anywhere
and is the same class of over-broadening the panel already recorded for `path` (errata 13).
Because `_name_fence` already exempts enum-classed keys, the map-site guard at
`streams.py:645` is dead code, and the mutant row 7 names ("drop the enum-key exemption")
does nothing:

```
--- M7a (if not enum_keys and _name_fence(k, kcls):  ->  if _name_fence(k, kcls):) -> SURVIVED
    239 passed, 1 skipped in 7.32s
```

The `host` tile that motivates the exemption is protected twice, so the guard that
`test_name_fence_at_depth_and_enum_key_exemption:379-389` is written to defend cannot be
broken by the one-line change. Today no declared field is both forbidden-named and
enum-classed, so no row validates differently — but the fence has silently acquired a
category of names it will let through, and the section's mutant can no longer detect the
loss of the exemption that is real.

### MAJOR-4 — `task-result`'s declared `kind` field is unreachable (plan-side collision)

`pkgs/evidence/streams.py:276` declares `"kind": ("enum", ("code", "docs", "unknown"))` as a
field of `task-result`, while `streams.py:28` declares `ENVELOPE = ("v", "ts", "kind")` and
`streams.py:684` skips every envelope key before the field walk:

```python
    for key, value in row.items():
        if key in ENVELOPE:
            continue
```

A `task-result` row carries exactly one `kind` in JSON and it is always the string
`"task-result"`, so the declared enum can never be evaluated, and row 1's named mutant
("remove any one field from the entry → its valid row reports `undeclared field`") survives
for this field:

```
--- M1b (delete "kind": ("enum", ("code","docs","unknown")) from task-result) -> SURVIVED
    239 passed, 1 skipped in 7.30s
```

`tests/evidence/test_streams_policy.py:83-117`'s `TASK_RESULT` fixture shows the collision
directly: it carries `"kind": "task-result"` and no `code`/`docs`/`unknown` value anywhere.
The section as written cannot be satisfied — the implementation follows it literally — so
this is the plan's defect, but it ships a declared field that is inert and a T2 producer that
has nowhere to put the task's code/docs classification. It needs a rename (`task_kind`) in
the plan before T2 runs.

### MAJOR-5 — a file outside `touches`, unexplained in the commit body

`tests/unit/83-plan-brief.bats:166`:

```bash
  cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/streams.py" "$REPO/pkgs/evidence/streams.py"
```

The section's `touches` is ten files (plus `docs/MAP.md` by rule) and does not include
`tests/unit/83-plan-brief.bats`. The change itself is necessary and correct —
`pkgs/evidence/evidence.py:29` now does a module-top `import streams`, so the fixture repo
that copies `evidence.py` must copy its sibling or the `unit` check goes red — and it is the
same omission the section already makes for `flake.nix:1106`, which it *did* list. But the
Global Constraints say "`touches` is a contract — a file outside it is a deviation to report",
and the commit body reports nothing: it names `streams.py`, `append`, `replace_stream`, the
delegation, the `--store` default and the ingest table, and never mentions the bats fixture.
An orchestrator reading only the commit sees a silent edit to a test file in another suite.

## Findings (minor)

### MINOR-1 — `key_of` is dead and untested

`pkgs/evidence/streams.py:719-724` is named in the section's Interfaces but no caller exists:
`replace_stream` builds its own `keyed()` from `entry["key"]` (`pkgs/evidence/evidence.py:160-161`)
and no test references `streams.key_of`. A stated interface with no test and no consumer.

### MINOR-2 — eleven stated refusal strings have no test

The Interfaces list `not a {class}` for `model-id`, `key`, `rev`, `ts`, `hash`, `int`, `num`,
`bool`, `object`, `list`, `string`; `grep -n 'not a ' tests/evidence/test_streams_policy.py`
returns only `not a id` (`:394-399`), `not a re` (`:505`) and `not a map` (`:850`). The
bounded class `("int", 0, 3)` on `scores` — the one place a value outside its range matters —
is never given an out-of-range value.

### MINOR-3 — `ingest` forwards the target name as a positional

`pkgs/evidence/evidence.py:449`: `forwarded = (["--store", store] if store else []) + rest[1:]`
where `rest[1:]` begins with the target name, so `ingest judgements <repo>` calls
`judgements.main(["--store", S, "judgements", <repo>])`. It works only because
`judgements.py:337-341` happens to declare a subparser named `judgements`. Every future
ingest module (T2's `ingest_result`, T3's `ingest_reviews`) is now forced to declare a
subcommand named exactly as its `INGEST_MODULES` key, and neither `SCHEMA.md` nor the
docstring says so.

### MINOR-4 — `except ImportError` is wider than "not available in this tree"

`pkgs/evidence/evidence.py:443-448` reports `evidence: ingest {name}: not available in this
tree` for any `ImportError`, including one raised *inside* a module that is present (a broken
sibling import in `ingest_result.py`, say). A real bug in a landed ingest module will be
reported as a missing module.

### MINOR-5 — `replace_stream` chmods the stream's parent unconditionally

`pkgs/evidence/evidence.py:143`: `os.chmod(path.parent, 0o750)` runs on every call, so a
top-level keyed stream chmods the store root itself. Harmless today
(`nixosModules/evidenceStore.nix:58` declares `/var/lib/evidence` 0750), but the section says
only "the parent (`derived/`) is created 0750", and this narrows any parent an operator has
widened.

### MINOR-6 — half of row 29's delegation assertion is a tautology

`tests/evidence/test_streams_policy.py:817`: `assert judgements.FIELDS == streams.judgement_fields()`
cannot fail, because `pkgs/evidence/judgements.py:35` *is* `FIELDS = streams.judgement_fields()`.
The load-bearing half is the source grep on the next line and the independent 14-name literal
in `tests/evidence/test_judgements.py:38-53`; the section's row asked for both and got one
real one.

### MINOR-7 — plan defects the panel already recorded, confirmed live in this code

Recorded here because the implementation follows the section as written; they are the plan's,
not the seat's.

- **Errata 7** (`FORBIDDEN` is exact-match): `streams.py:490` normalises case and hyphens
  only, so a future field named `urls`, `hosts`, `emails` or `api_keys` passes a fence that
  blocks each singular. Undocumented as a deliberate choice and untested either way.
- **Errata 12** (`("text", cap)` confined by a sentence): confirmed by mutant — adding
  `"blurb": ("text", 200)` to `check` leaves the suite silent (`239 passed, 1 skipped`).
  `test_declared_field_walk_none_forbidden_but_path:343-359` walks field *names*, never
  classes, so the "one free-text class" rule has nothing that can fail.
- **Errata 13** (the exemption written as a class rule, not the design's five names):
  realised at `streams.py:498`, and widened further — see MAJOR-3.
- **Errata 16** (the append/replace lock interaction): `append` locks the inode
  (`evidence.py:78-84`) while `replace_stream` swaps it (`evidence.py:179`). No kind has both
  writers today and nothing states or tests that.
- **Errata 17** (the mis-quoted `grep` output in Facts) and **errata 19** (Step 2's red named
  two ways): cosmetic; the real red is `StopIteration`, as recorded above.

## Verdict

**REJECTED.** Five MAJORs: three named mutants that the committed suite cannot kill
(row 13's enum arms, rows 20/21's equal-row `ts`, row 7's enum-key exemption), one named
mutant that the section's own `ENVELOPE`/`task-result.kind` collision makes unkillable, and
one file edited outside `touches` with no word in the commit body. The code itself is sound
and every acceptance check is green; the fix is test work plus one plan correction, not a
rewrite:

1. Parametrise **every** arm of the six enums row 13 names (and pin `route`, `checks_parse`
   and `plan_defect` the same way), so deleting any arm goes red.
2. Add the equal-row fixture rows 20 and 21 actually describe: replace a keyed row with a
   byte-equal copy and assert its `ts` is unchanged, with a `now_iso` seam (or a stored `ts`
   from an earlier second) so the assertion does not depend on the clock.
3. Narrow `_name_fence` to the section's two exemptions (`path` on a declared field; a
   closed-enum map key at the map site only), so the map-site guard becomes load-bearing
   again; consider errata 13's explicit `NAME_EXEMPT = {("factory-finding", "file")}`.
4. Take `task-result`'s declared `kind` field back to the plan: rename it (`task_kind`) or
   state that the classification rides elsewhere, before T2 is dispatched.
5. Declare the `tests/unit/83-plan-brief.bats` copy — in the commit body and in the plan's
   `touches` for T1 — beside the `flake.nix` copy it mirrors.
