---
plan_defect: none
mutants_total: 16
mutants_killed: 10
mutants_outside_named: 9
model: opus
---
# Opus gate — seat run sp2, task SP8 — APPROVED

## Summary

In a fresh clone of `task/SP8` (`9ea240f`, base `e4258e0`) every numbered clause
of the section's `Interfaces` block is implemented literally and exercised, and
both acceptance checks are green under `--rebuild` (`evidence-unit` **503
passed**, `lint` ok — the same number the commit body pastes), plus `ruff
check`, `ruff format --check`, the `repomap` round-trip and `tasks check`.
Six of the seven named mutants die; the seventh (row 6) cannot be realised —
`evidence.replace_stream` has returned early on an empty batch since `91c6b8c`,
long before this plan, and the `if rows:` guard the seat wrote is verbatim the
house idiom the section told it to copy (`ingest_result.py:453-455`). I proved
the row-6 test is nevertheless discriminating by killing it with an outside
mutant (O6). Nine outside mutants applied, four killed.

The item carried from SP1's gate is closed: the broker writes no `src`, and this
ingest synthesises it — `ingest_openrouter_usage.py:78`, asserted on every row
by test 1, killed by mutant 1a, and visible in a live end-to-end run.

The driver's `touches_extra=1` is the disclosed edit to
`tests/evidence/test_streams_policy.py`. It was necessary (SP8's own
`evidence.py` change turns that test red — pasted below), it belongs to SP8 and
not to SP2 (SP2 has no reason to touch `test_ingest_table`), it is
order-independent (it passes against the base's `evidence.py` too), and it
merges with the peer's branch without a conflict: `git merge-tree` on
`task/SP8` × run sp2's `SP2` head (`2d40f41`) reports only `Auto-merging`, and
`pytest tests/evidence -q` on the merged tree is **506 passed, 1 skipped**.

Seven MINORs, none gating. No MAJOR.

## Contract items

Every clause of the `### SP8 (` section, taken literally. Line numbers are
`pkgs/evidence/ingest_openrouter_usage.py` unless stated.

| # | clause | met | evidence |
|---|---|---|---|
| 1 | `evidence ingest openrouter-usage [--root DIR] <path>…`, `main(argv)`, `prog="evidence ingest"`, `--store` as `ingest_result.py` | yes | `:102-115`; `--store` default `os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE` (`:106`) |
| 2 | the subparser with `--root` default `/var/lib/egress-broker`, `paths` `nargs="+"` | yes | `:113-114` |
| 3 | `ingest(store, paths, root) -> (n, refused, torn)` | yes | `:32`, `:99` `return len(rows), refused, torn` |
| 4 | every path realpath-fenced under `root` **before any read** | yes | `:38-44` builds the whole fenced list before the read loop at `:49`; probe A: a sibling directory `…/broker-evil/usage.jsonl` against root `…/broker` → `OutsideRoot (fenced) OK` |
| 5 | `OutsideRoot` → stderr `evidence: ingest openrouter-usage: {p} is outside {root}`, exit 2, nothing written | yes | `:120-125`; live: `evidence: ingest openrouter-usage: tests/evidence/fixtures/openrouter-usage/usage.jsonl is outside /var/lib/egress-broker` / `OUTSIDE_EXIT=2`; test asserts `not (store / "ledger" / "openrouter-usage.jsonl").exists()` (`test_ingest_openrouter_usage.py:94`) |
| 6 | an unreadable path → `…: {p}: not a usage file`, refused | yes | `:50-58`; probe C (a directory inside the root): `evidence: ingest openrouter-usage: …/broker/sub: not a usage file` and `ingest` returned `(0, 1, 0)`. No test — MINOR-3 |
| 7 | a last line with no trailing `\n` is torn — stderr `…: {p}: last line torn (the broker is writing); skipped`, **not** counted refused | yes | `:59-62`, `:89-95`; live: `… torn.jsonl: last line torn (the broker is writing); skipped` with exit 0 in test 3 |
| 8 | any other non-object line → refused `…: {p}:{lineno}: not JSON` | yes | `:67-77`; the ordering (torn stripped at `:62` before the parse at `:68`) means a torn fragment is never reclassified — mutant 3 pastes the counterfactual `torn.jsonl:3: not JSON` |
| 9 | a row = the object plus `kind: "openrouter-usage"`, `v: 1`, `src: "broker"` | yes | `:78`; live stream row: `…,"kind":"openrouter-usage","model":"deepseek/deepseek-v4-flash",…,"src":"broker",…,"v":1}` |
| 10 | `streams.validate` refusals printed one per reason `…: {p}:{lineno}: {reason}` | yes | `:79-87`; live: `…/usage.jsonl:4: model: not a model-id` |
| 11 | one `evidence.replace_stream(store, "ledger/openrouter-usage", rows)` | yes | `:97-98`, guarded `if rows:` exactly as `pkgs/evidence/ingest_result.py:453-455` |
| 12 | stdout `ingested {n} rows into ledger/openrouter-usage ({refused} refused)` | yes | `:126`; live `ingested 3 rows into ledger/openrouter-usage (1 refused)` (see MINOR-5 on `n` when two files collide by key) |
| 13 | exit `0` when `refused == 0`, else `1` | yes | `:127`; torn alone keeps exit 0 (test 3) |
| 14 | `evidence ingest bogus` → stderr ends `(judgements\|result\|reviews\|openrouter-usage)`, exit 2 | yes | `evidence.py:511-516`; live: `evidence: ingest: unknown target bogus (judgements\|result\|reviews\|openrouter-usage)` |
| 15 | `INGEST_MODULES["openrouter-usage"] = "ingest_openrouter_usage"`; the two parenthetical lists become `"\|".join(INGEST_MODULES)` | yes | `evidence.py:38`, `:40` `INGEST_TARGETS = "\|".join(INGEST_MODULES)`, used at `:509` and `:513`; live no-target arm: `evidence: error: ingest requires a target (judgements\|result\|reviews\|openrouter-usage)` / exit 2 |
| 16 | `SCHEMA.md` gains a `ledger/openrouter-usage` row (kind, key, fields, writer) | yes | `pkgs/evidence/SCHEMA.md:31` — field-for-field identical to `streams.py:520-545`, `key (instance, request_id)`, writer `evidence ingest openrouter-usage (SP8)` |
| 17 | the fixture `torn.jsonl`: two good lines, then `{"ts_epoch": 1788906` with no newline | yes | `tests/evidence/fixtures/openrouter-usage/torn.jsonl:1-3`, `\ No newline at end of file` in the diff |
| 18 | Step 2 — `pytest tests/evidence -q` green including the existing `test_ingest_table` | yes | `502 passed, 1 skipped` in the clone; `503 passed` inside `evidence-unit` |

Carried from SP1's gate: **the `src` synthesis lands here.** The broker's record
(`pkgs/broker/policy.py:203-204`) writes no `src`; the fixture rows carry none;
`:78` adds it, `test_four_line_file_three_rows_one_refused:61` asserts
`all(r["src"] == "broker" for r in rows)`, and mutant 1a kills that assertion.
`src` is declared `("enum", ("broker",))` at `streams.py:525`.

## Red before green

The section's stated red (Step 1) is the loader's `StopIteration`. Reproduced by
checking the base's implementation against the branch's tests — `git checkout
e4258e0 -- pkgs/evidence/evidence.py` and `rm
pkgs/evidence/ingest_openrouter_usage.py`, then the section's command:

```
$ nix develop -c pytest tests/evidence/test_ingest_openrouter_usage.py -q
tests/evidence/test_ingest_openrouter_usage.py:36: in <module>
    mod = _load()
tests/evidence/test_ingest_openrouter_usage.py:26: in _load
    src = next(p for p in candidates if p.exists())
E   StopIteration
ERROR tests/evidence/test_ingest_openrouter_usage.py - StopIteration
1 error in 0.06s
```

Restored (`git checkout HEAD -- …`): `502 passed, 1 skipped in 12.83s`, and
`evidence-unit` `503 passed`. This is a collection error, so it proves all six
tests red at once rather than one per assertion; the per-assertion discrimination
is the mutant table below, and each of the six tests is killed there by at least
one mutant (1a/1b → test 1, 2 → test 2, 3 → test 3, 4 → test 4, 5 → test 5,
O6 → test 6).

The deviation's own red, which the section did not ask for but which decides
whether the edit was necessary — the **base's** `test_ingest_table` against the
**branch's** `evidence.py`:

```
>       assert (
            "evidence: ingest: unknown target bogus (judgements|result|reviews)" in r.stderr
        )
E       AssertionError: assert '…(judgements|result|reviews)' in
E         'evidence: ingest: unknown target bogus (judgements|result|reviews|openrouter-usage)\n'
tests/evidence/test_streams_policy.py:1069: AssertionError
1 failed, 204 deselected
```

and the **branch's** `test_ingest_table` against the **base's** `evidence.py`:
`1 passed, 204 deselected` — the edit is order-independent.

## Mutants

**Named by the section: 7 applied** (row 1 names two: `src` not added, and the
exit code always 0), **6 killed, 1 survived.**

| mutant | test that must kill it | failing line |
|---|---|---|
| M1a — `"src": "broker"` dropped from the row at `:78` | `test_four_line_file_three_rows_one_refused` | `assert all(r["src"] == "broker" for r in rows)` → `KeyError: 'src'` — `1 failed` |
| M1b — `return 0 if refused == 0 else 1` → `return 0` (`:127`) | the same | `assert code == 1` → `assert 0 == 1` — `1 failed` |
| M2 — `replace_stream` → a per-row `evidence.append` loop (`:97-98`) | `test_second_run_same_three_rows` | `AssertionError: assert 6 == 3` — `1 failed` |
| M3 — the torn rule dropped (`torn_last = False`, `:59`) | `test_torn_last_line_reported_not_refused` | `assert _run_ingest(...) == 0` → `assert 1 == 0`, stderr `torn.jsonl:3: not JSON` — `1 failed` |
| M4 — the fence removed (`raise OutsideRoot` → `pass`, `:43`) | `test_outside_root_exits_two_and_symlink_root_accepted` | `assert 0 == 2`, stdout `ingested 1 rows …` — `1 failed` |
| M5 — `"openrouter-usage"` removed from `INGEST_MODULES` (`evidence.py:38`) | `test_help_and_bogus` | `AssertionError: evidence: ingest: unknown target openrouter-usage (judgements\|result\|reviews)` / `assert 2 == 0` — `1 failed` |
| M6 — `if rows:` → `if True:` (i.e. `replace_stream([])` on a missing path) | `test_empty_file_zero_rows` | **survives** — `1 passed` |

M6 cannot be realised. `evidence.replace_stream` short-circuits an empty batch
before it ever touches the path (`pkgs/evidence/evidence.py:151-152`:
`if not rows: return len(read(store, stream))`, and `read` returns `[]` when the
parent does not exist, `:115-116`); that guard landed in `91c6b8c`, well before
this plan was written, and `ingest_result.py:453-455` — the idiom the section
names as the model — carries the same `if rows:`. So the section's row-6 mutant
describes a bug the store API forbids. The test is not thereby vacuous: outside
mutant **O6** (the `ingested …` line moved inside `if n:`) kills it,
`1 failed, 5 passed`.

**Outside the named set: 9 applied, 4 killed, 5 survived.**

Killed:

- **O2** — `enumerate(lines, start=1)` → `start=0`: `test_four_line_file…` at
  `:57` (`"usage.jsonl:4:" in captured.err`) — `1 failed, 5 passed`.
- **O3** — the `refused += 1` dropped from the validate arm: `3 failed, 3
  passed` (tests 1, 2 and 4).
- **O6** — the `ingested {n} rows …` line printed only when `n`:
  `test_empty_file_zero_rows` at `:132` — `1 failed, 5 passed`.
- **O9** — a torn last line counted `refused` instead of `torn`:
  `test_torn_last_line_reported_not_refused` — `1 failed, 5 passed`.

Survived (each a coverage gap, not a defect in the shipped code):

- **O1** — `rp.startswith(real_root + os.sep)` → `rp.startswith(real_root)`:
  `6 passed`. The shipped fence is correct (probe A fences
  `…/broker-evil/usage.jsonl` against root `…/broker`); no test pins the
  sibling-prefix arm. MINOR-4.
- **O4** — the unreadable-path text `not a usage file` → `unreadable`: `6
  passed`. MINOR-3.
- **O5** — `--root` default `/var/lib/egress-broker` → `/`: `6 passed`.
  MINOR-3.
- **O7** — the row's `"v": 1` → `"v": 2`: `6 passed`; harmless, since
  `replace_stream` stamps `v` from the declared kind (`evidence.py:184`).
- **O8** — the `OutsideRoot` stderr text `is outside {root}` → `rejected`: `6
  passed`. MINOR-3.

## Checks

All run in the fresh clone at `9ea240f`, `--rebuild` on both acceptance checks.

| check | how | result |
|---|---|---|
| `evidence-unit` | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **pass** — `503 passed in 13.53s`, exit 0 |
| `lint` | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass** — exit 0 (the `no-dupe-keys` / `no-debugger` lines in the log are the deliberate negative fixtures `tests/lint/fixtures/js/*`) |
| `githooks/pre-commit` | `nix develop -c githooks/pre-commit` | treefmt `All checks passed!`, `106 files already formatted`, shellcheck/statix/deadnix/ruff/js arms all clean; **exit 1** on the last line only: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` — see MINOR-7 |
| `ruff check` | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| `ruff format --check` | same paths | `82 files already formatted` |
| repomap round-trip | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | clean, exit 0 (the committed `docs/MAP.md` delta is the `tests/evidence` count `89 → 91`; the generator does not list modules inside `pkgs/evidence`) |
| `tasks check` | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |
| peer merge | `git merge-tree --write-tree --messages HEAD <sp2 head 2d40f41>` | exit 0, only `Auto-merging docs/MAP.md` / `Auto-merging tests/evidence/test_streams_policy.py`; `pytest tests/evidence -q` on the merged tree: `506 passed, 1 skipped` |

Live end-to-end through the real dispatch (a scratch store; `/var/lib/evidence`
untouched):

```
$ python3 pkgs/evidence/evidence.py --store $S ingest openrouter-usage \
    --root $F $F/usage.jsonl $F/torn.jsonl
evidence: ingest openrouter-usage: …/usage.jsonl:4: model: not a model-id
evidence: ingest openrouter-usage: …/torn.jsonl: last line torn (the broker is writing); skipped
ingested 5 rows into ledger/openrouter-usage (1 refused)
E2E_EXIT=1
```

## Touches and commit

The section's list is `pkgs/evidence/ingest_openrouter_usage.py`,
`pkgs/evidence/evidence.py`, `pkgs/evidence/SCHEMA.md`,
`tests/evidence/test_ingest_openrouter_usage.py`,
`tests/evidence/fixtures/openrouter-usage/torn.jsonl`, plus `docs/MAP.md` by
rule. The diff is those six files and one more:

```
 docs/MAP.md                                        |   2 +-
 pkgs/evidence/SCHEMA.md                            |   1 +
 pkgs/evidence/evidence.py                          |   6 +-
 pkgs/evidence/ingest_openrouter_usage.py           | 131 ++++++++++++++++++++
 .../evidence/fixtures/openrouter-usage/torn.jsonl  |   3 +
 tests/evidence/test_ingest_openrouter_usage.py     | 135 +++++++++++++++++++++
 tests/evidence/test_streams_policy.py              |   3 +-
```

`tests/evidence/test_streams_policy.py` is outside the list and is disclosed in
the body with its reason (`Deviation: …`) — MINOR-2, with the peer-overlap
judgement there. `docs/OPERATIONS.md` and the plan file are untouched.

Commit: exactly one (`9ea240f`). The subject is byte-identical to the section's
— 187 bytes each, compared programmatically:

```
SUBJECT: "evidence: ingest openrouter-usage — the broker's usage.jsonl fenced to /var/lib/egress-broker and merged by request id, a torn last line reported not refused (test: evidence-unit, lint)"
WANT   : "evidence: ingest openrouter-usage — the broker's usage.jsonl fenced to /var/lib/egress-broker and merged by request id, a torn last line reported not refused (test: evidence-unit, lint)"
IDENTICAL: True | bytes 187 187
```

The body states the why (the fence-before-read and torn-before-parse ordering,
and why the two parenthetical lists became dynamic), pastes the red
(`StopIteration` from the loader) and the green (`evidence-unit 503 passed` —
the number I measured), discloses the deviation, and ends with the two trailers
after a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sp2)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

— the same shape as SP1b's landed `0eb7666`.

## Findings

No MAJOR.

**MINOR-1 — the section's row-6 mutant cannot be realised, so it survives.**
`pkgs/evidence/ingest_openrouter_usage.py:97` — the `if rows:` guard removed
(`if True:`) leaves `test_empty_file_zero_rows` green (`1 passed`), because
`pkgs/evidence/evidence.py:151-152` already returns before touching the path:

```
    if not rows:
        return len(read(store, stream))
```

That line predates the plan (`git log -S '    if not rows:'` → `91c6b8c`), and
the guard the seat wrote is copied verbatim from the idiom the section names,
`pkgs/evidence/ingest_result.py:453-455`. The test still discriminates (outside
mutant O6 kills it), so this is a defect in the plan's mutant sentence, not a
vacuous test and not a seat fault. Nothing owed of the seat; worth a line in the
plan's errata if the section is ever re-issued.

**MINOR-2 — the deviation `tests/evidence/test_streams_policy.py`, on its merits
and against the peer.** `tests/evidence/test_streams_policy.py:1069-1072`. It
was **necessary**: SP8's own `evidence.py:513` change makes the base's literal
assertion fail (`assert '…(judgements|result|reviews)' in '…|openrouter-usage)\n'`,
pasted above). It **belongs to SP8, not SP2**: the breakage is caused by SP8's
edit, and SP2 has no reason to touch `test_ingest_table` — its 69 added lines in
that file sit in three hunks at `@@ -361`, `@@ -379` and `@@ -433`, nowhere near
line 1067. It **integrates after SP2 without a conflict**: `git merge-tree` of
`task/SP8` with run sp2's `SP2` head `2d40f41` returns exit 0 with only
`Auto-merging` messages, and `pytest tests/evidence -q` on the merged tree is
`506 passed, 1 skipped`. The edit is also order-independent (it passes against
the base's `evidence.py`), so a landing in either order is safe. The plan defect
behind it: SP8's `touches` omits the file although the section's own Step 2
demands that `test_ingest_table` stay green — record it as `missing-case`
against the section if the ledger wants a row; it did not gate here because the
body discloses it.

**MINOR-3 — three stated contracts with no test.** Outside mutants O4, O5 and O8
each survive `6 passed`: the unreadable-path message
(`ingest_openrouter_usage.py:54`, `not a usage file`), the `--root` default
`/var/lib/egress-broker` (`:113`) and the `OutsideRoot` stderr text
(`:122`, `is outside {root}`) are all named in the section's Interfaces block
and none is asserted. Test 4 checks only the exit code 2, not the line the
operator will read. The behaviours are correct — probe C over a directory prints
`evidence: ingest openrouter-usage: …/broker/sub: not a usage file` and returns
`(0, 1, 0)` — but nothing pins them.

**MINOR-4 — the fence's sibling-prefix arm is untested.**
`ingest_openrouter_usage.py:42` — weakening `rp.startswith(real_root + os.sep)`
to `rp.startswith(real_root)` leaves all six tests green (`6 passed`). The
shipped code is right (probe A: root `…/broker`, path `…/broker-evil/usage.jsonl`
→ `OutsideRoot (fenced) OK`); the test only covers a path in a wholly unrelated
directory.

**MINOR-5 — `ingested {n} rows` counts accepted lines, not rows written.**
`ingest_openrouter_usage.py:99` returns `len(rows)` and `:126` prints it, while
`replace_stream` returns the true post-merge count and is discarded. Measured:
ingesting `usage.jsonl` and `torn.jsonl` together prints `ingested 5 rows into
ledger/openrouter-usage (1 refused)` while the stream file holds **3** rows —
the two fixtures reuse request ids `…0001` and `…0002`, and the merge collapses
them. Not reachable from the declared producer (one file per instance, one line
per request, and the key is `(instance, request_id)`), and
`ingest_result.py:455` prints the same way, so this is the house idiom rather
than a regression; noted because the operator's runbook line globs
`/var/lib/egress-broker/*/usage.jsonl` and will read that number.

**MINOR-6 — a non-UTF-8 file inside the root crashes instead of refusing.**
`ingest_openrouter_usage.py:51` uses `pathlib.Path(rp).read_text()` under
`except OSError`; a `UnicodeDecodeError` is a `ValueError`, so probe B (bytes
`\xff\xfe\x00binary\n` written inside the root) raises
`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0` out of
`ingest` instead of the contracted `not a usage file`. Unreachable from the
broker, which writes `json.dumps(rec)` with the default `ensure_ascii`
(`pkgs/broker/policy.py:204`) — so even a mid-write torn line is pure ASCII —
and `ingest_result.py:435-437` has the identical hole. Recorded, not owed.

**MINOR-7 (process) — `githooks/pre-commit` exits 1 on a task branch after the
commit.** Every lint arm passes; the failure is the last line, `tasks:
docs/OPERATIONS.md queue block was stale and has been regenerated`. The
regeneration's whole content is the removal of this very task from the queue
(`… CR4 PW1glm PW1kimi PW1pro SP2 SP3 SP8 …` → `… SP2 SP3 …`), i.e. an artifact
of running the hook *after* `9ea240f` exists; at commit time the block matched,
which is why no `docs/OPERATIONS.md` change is in the diff and why no
`--no-verify` was needed. I restored the file; the clone ends clean. Nothing
owed of the seat — flagged so the next gate does not read this exit 1 as red.

## Verdict

**APPROVED.** Eighteen contract clauses met literally, both acceptance checks
green under `--rebuild`, the red reproduced as the section states it, six of
seven named mutants dead and the seventh unrealisable by the store API rather
than by a weak test (proved with an outside kill), and the one `touches`
deviation necessary, correctly attributed to SP8, disclosed, and demonstrated to
merge with its wave peer with the whole `tests/evidence` suite green. The
carried SP1 item — the missing `src` — lands here and is pinned by an assertion
and a mutant. Seven MINORs, none gating, none owed of the seat.
