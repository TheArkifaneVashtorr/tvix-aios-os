---
plan_defect: underspecified
mutants_total: 24
mutants_killed: 23
mutants_outside_named: 7
model: opus
---
# Opus gate — seat run ol2f, task OL2b — APPROVED

## Summary

Both MAJORs of `docs/reviews/2026-09-08-opus-review-ol2-OL2.md` are closed, and both its
MINORs with them. The extractor now reads the shape that real rollouts carry, and I
proved it against the operator's own file rather than against the plan's prose: the
delivered tool emits **20 rows, exit 0, empty stderr** for the named rollout, and an
independent count of that file gives **20** `event_msg`/`token_count` carriers, all nine
measured keys on every one, **20 non-null `primary`**, **0 non-null `secondary`** — so
20 rows is exactly the number the "one row per non-null window" rule demands. The
orchestrator's supplied measurement holds in every particular (its "empty stderr" is
also right: the 98 bytes my first run showed on fd 2 were `nix develop`'s own
`nixfmt-rfc-style` evaluation warning, not the tool's).

All 17 named mutant arms die, plus 6 of 7 I invented. Red before green reproduces the
seat's pasted failure list byte for byte (`11 failed, 3 passed, 4 subtests passed`).
`unit` and `lint` are green on `--rebuild`, `nix flake check -L` prints `all checks
passed!`, ruff is clean, touches are exactly the two contracted files, one commit,
subject byte-identical, trailers correct.

The one thing that is *not* satisfiable is the section's own restated closing condition
for `codex-rate-limits-shape-unmeasured`: "**with the row count asserted by
`checks.unit`**". `checks.unit` is a `pkgs.runCommand` in a Nix sandbox with no `$HOME`
and no `~/.codex`, and §Global Constraints separately forbid fixturing anything from the
real file — so no check can ever assert a row count against the operator's rollout, and
no seat could have written one. That is a plan/ledger defect (`underspecified`), recorded
here against the plan, not against this commit; nothing the seat did or omitted turns on
it, and it is not grounds for a rejection. **The claim should close** — see Contract item
C8 for the substitute I accept and the exact ledger amendment I recommend.

The seat's FACTORY-NOTES line ("Synthetic fixtures only; operator rollout row count
remains a manual measurement") is accurate and is the correct disclosure. As at OL2, the
seat's conduct is exemplary: it reproduced red before green, killed every named mutant,
declined to fixture the real file, restored the transient `flake.nix` mutant before
committing, and said plainly in the commit body which arm of the closing condition it
could not perform.

## Contract items

The section's **Interfaces** 1–7, plus the carried items OL2b says "stand exactly as
written", each taken literally.

| # | contract item | met | evidence |
|---|---|---|---|
| I1 | kept only when `type == "event_msg"` AND `payload` is a dict AND `payload.type == "token_count"` AND `payload.rate_limits` is a dict; everything else skipped | yes | `tools/codex_limits.py:61-68` — all four conjuncts, `continue` otherwise. `tests/test_codex_limits.py:88-114` (`test_z1`) feeds `turn_context`, `response_item`, `world_state`, a top-level `"rate_limits"` record (the old flat shape) and an `event_msg`/`task_started` — all skipped; mutants Z1a, Z1b dead |
| I2 | the nine measured keys all required; missing one → `codex_limits: <path> is missing "<key>" on a rate_limits record`, exit 2, nothing flushed, no further path processed | yes | `tools/codex_limits.py:12-22` (the nine, in the measured order), `:70-74` raise, `:119-121` exit 2. `tests/test_codex_limits.py:143-152` loops over **all nine** keys and passes a second, later path proven never opened (stdout `""`); mutant Z6 dead |
| I3 | each window validated separately; `None` → no row; a dict must carry `used_percent`/`window_minutes`/`resets_at`, else `… on a rate_limits <window> window`, exit 2; a non-dict, non-None value is the same failure and the same message; both `None` is valid and yields zero rows | yes | `tools/codex_limits.py:75-84` — `values is None: continue`, then `not isinstance(values, dict) or key not in values` raises with `{window}` interpolated. `tests/test_codex_limits.py:154-171` covers both windows × three keys **and** the malformed values `42, [], "bad", False` (each expecting the `used_percent` message); `:173-178` (`test_z8`) covers `primary: null`; mutants Z7, Z8 dead, my O6 (hardcode `primary` in the message) dead |
| I4 | seven keys in this order — `ts`, `session`, `window`, `limit_id`, `used_percent`, `window_minutes`, `resets_at`; `window` literal; `limit_id` verbatim from the outer object; `primary` row before `secondary`; nothing else reaches stdout | yes | `tools/codex_limits.py:85-93` builds exactly the seven, `"session": None` reserving the slot and `:96-97` filling it in place so order survives. `tests/test_codex_limits.py:104` asserts `list(row) == KEYS` and `:105-114` asserts the whole row per window; `:131-138` (`test_z4`) proves `"raw"` on the outer object and `"extra"` inside `primary` are both dropped. Mutants Z1b, Z4 dead; my O3 (swap the window loop order) dead. Live: `{"ts": …, "session": "01a08401-…", "window": "primary", "limit_id": "codex", "used_percent": 1.0, "window_minutes": 10080, "resets_at": 1789460350}` |
| I5 | session: the first `session_meta` whose `payload` is a dict AND contains `"id"`, and **only** that one stops the search; else the rollout uuid; else the stem; never the literal `unknown` | yes — MINOR-1 closed | `tools/codex_limits.py:56-60` — `found_session = True` now sits *inside* the `"id" in payload` branch (the exact inversion the prior review quoted); `:26-39` the uuid/stem fallback; `grep -c 'unknown' tools/codex_limits.py` → `0`. `tests/test_codex_limits.py:205-217` (`test_z12`) runs a first meta with payload `{}`, `None` and `[]` and asserts the SECOND meta's id wins; `:192-203` (`test_z11`) covers stem and uuid. Mutants Z11, Z12 dead |
| I6 | a directory → `codex_limits: <path>: Is a directory`, stderr, exit 2, before any later path opens | yes — MINOR-2 closed | `tools/codex_limits.py:113-115`. `tests/test_codex_limits.py:186-190` passes the directory first and a clean file second, asserting stdout `""`. Probed live: `exit=2`, one stderr line, no traceback. Mutant Z10 dead |
| I7 | after every path processes cleanly with zero total rows → `codex_limits: 0 rate_limits rows found across <n> path(s)`, exit **3**, never 0; ≥1 row anywhere → exit 0; never fires when a path errored | yes — MAJOR-1 closed | `tools/codex_limits.py:105`, `:122`, `:125-131` — the guard is after the loop, and every error arm `return 2` before it. `tests/test_codex_limits.py:234-258` (`test_z14`) asserts exit 3 + the exact stderr for `<n>` = 1 and 3, then that one inserted worked example flips the same run to exit 0. Probed: idle → `exit=3`; idle+idle → `… across 2 path(s)`; idle+one → `exit=0`, one row; dir → `exit=2`; idle + nonexistent → `exit=2` (3 never pre-empts 2). Mutants Z14, my O1 and O7 dead |
| C-a | carried item 1 — stdlib only, no `~/.codex` default | yes | `tools/codex_limits.py:7-9`; `grep -rn '\.codex' tools tests` → no match |
| C-b | carried item 2 — zero argv → usage line, exit 2 | yes | `:102-104`; `test_z5` (`:140-141`); mutant Z5 dead |
| C-c | carried item 3 — nonexistent path → the documented line, exit 2 | yes | `:110-112`; `test_z9` (`:180-184`); mutant Z9 dead |
| C-d | carried item 5 — not JSON, or zero valid lines → `codex_limits: <path> is not JSONL`, exit 2, nothing flushed | yes | `:49-52` per line, `:94-95` zero lines; `test_z2` (`:116-121`) subtests a truncated tail, `""`, `"\n"`, `"not json"`; mutants Z2 and my O5 dead |
| C-e | carried item 9 — flush-then-continue, rows grouped by path in argv order, earlier rows survive a later failure | yes for the observable half; the *timing* half untested | `:106`, `:123-124` (`flush=True`, inside the per-path loop); `test_z13` (`:219-232`) asserts A-then-B grouping and that A's stdout is intact when B fails. Mutants Z13a, Z13b dead. But dropping `flush=True` alone (my O4) survives the whole suite — MINOR-3 |
| C-f | carried item 10 — `checks.unit` with no `\|\| true` | yes | `flake.nix:29-48`, unchanged by this commit; Z15 proved both arms below |
| C-g | §Global Constraints — no fixture copied from a real rollout, no real session id, no secret, no path under `/var/lib/secrets` | yes | `grep -rn '01a08401\|\.codex\|/var/lib/secrets\|dalhaka' tools tests` → no match. Fixture ids are `11111111-2222-4333-8444-555555555555` / `aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee` (`tests/test_codex_limits.py:20-21`), both invented |
| C8 | §Facts — the closing condition for `codex-rate-limits-shape-unmeasured`: an extractor on the measured key set that **emits rows for the operator's named rollout**, with **the row count asserted by `checks.unit`** | first clause met; second clause unsatisfiable by construction — see below | live run: 20 rows, exit 0; `checks.unit` cannot reach `~/.codex` |

### C8 in full — should the claim close?

**Yes, it should close.** The measurement, re-run by me from the clone:

```
$ nix develop -c python3 tools/codex_limits.py \
    /home/dalhaka/.codex/sessions/2026/09/08/rollout-2026-09-08T21-31-07-01a08401-3981-7922-9a04-00906416df84.jsonl
EXIT=0
stdout lines: 20
tool stderr: (empty)
```

and my own independent count of the same file, not using the tool:

```
carriers: 20  non-null primary: 20  non-null secondary: 0  expected rows: 20
keysets: Counter({('credits', 'individual_limit', 'limit_id', 'limit_name', 'plan_type',
  'primary', 'rate_limit_reached_type', 'secondary', 'spend_control_reached'): 20})
top-level 'rate_limits' type records: 0
```

20 emitted = 20 non-null `primary` + 0 non-null `secondary`. The nine-key set is exactly
the plan's. The shape the OL2 gate measured is the shape this tool reads.

The unmeetable half is "the row count asserted by `checks.unit`". `checks.unit` is
`pkgs.runCommand` (`flake.nix:29-48`): a Nix sandbox with `${self}` copied in and nothing
else. It has no `~/.codex`, and §Global Constraints forbid carrying that file's bytes into
a fixture, so the operator's row count is unreachable from any check — today and for any
future round of this task. Worse, a check that *did* read a live home file would make the
derivation impure and non-reproducible, which is a defect in its own right.

The right substitute, and what I accept:

1. **The number itself** is established by two independent measurements on the live host
   (the orchestrator's and mine), agreeing at 20, one of them not using the tool at all.
2. **The rule that produces the number** — one row per non-null window, `primary` first —
   *is* asserted by `checks.unit`: `test_z1` pins exactly 3 rows for 1 null-secondary +
   1 non-null-secondary carrier (the 1 + 2 arithmetic that scales to 20 + 0), `test_z8`
   pins the null-window zero-row arm, `test_z14` pins the zero-total arm, `test_z11` pins
   the session resolution the live run exercised. Mutating any of those turns `checks.unit`
   red (Z1a, Z1b, Z8, Z14 below), and `checks.unit` itself is proven to fail non-zero on a
   broken assertion (Z15).

Recommended ledger amendment for the orchestrator, at close: keep the key-set clause,
replace "with the count asserted by `checks.unit`" with "with the row count measured on
the live host at OL2b's gate (20 rows, exit 0, empty stderr, against 20 carriers with 20
non-null `primary` and 0 non-null `secondary`) and the row *rule* asserted by
`checks.unit`". Record the defect class `underspecified` against the plan, not the seat.

## Red before green

The section's Step 1 command, the branch's tests against the carried flat-shape
implementation (`git fetch /home/dalhaka/factory/ws/ol2/OL2 task/OL2` → `9db7f5b`, then
`git checkout FETCH_HEAD -- tools/codex_limits.py`):

```
$ nix develop -c python3 -m pytest tests/test_codex_limits.py -q
FAILED tests/test_codex_limits.py::LimitsTests::test_z10_directory
FAILED tests/test_codex_limits.py::LimitsTests::test_z11_fallback
FAILED tests/test_codex_limits.py::LimitsTests::test_z12_later_valid_meta
FAILED tests/test_codex_limits.py::LimitsTests::test_z13_order_and_flush
FAILED tests/test_codex_limits.py::LimitsTests::test_z14_empty_total
FAILED tests/test_codex_limits.py::LimitsTests::test_z1_mixed_kinds_and_exact_fields
FAILED tests/test_codex_limits.py::LimitsTests::test_z3_session_is_per_file_and_first_meta_wins
FAILED tests/test_codex_limits.py::LimitsTests::test_z4_extras_do_not_leak
FAILED tests/test_codex_limits.py::LimitsTests::test_z6_required_keys
FAILED tests/test_codex_limits.py::LimitsTests::test_z7_windows
FAILED tests/test_codex_limits.py::LimitsTests::test_z8_null_windows
11 failed, 3 passed, 4 subtests passed in 0.34s
```

Identical to the list the commit body pastes, including the three that pass (Z2, Z5, Z9 —
the section says these keep OL2's originals nearly verbatim, so they *must* pass against
the old implementation; that is not a vacuous test, it is the carried scaffold). Restoring
`HEAD`'s implementation:

```
$ nix develop -c python3 -m pytest tests/test_codex_limits.py -q
14 passed, 4 subtests passed in 0.80s
```

Nothing in the tree after either step: `git status --porcelain` clean.

## Mutants

Every arm applied alone to a scratch copy of `tools/codex_limits.py` (or `flake.nix` for
Z15), the section's own targeted command run, the file restored before the next. Named
arms first.

| arm | mutation | exit | killing line |
|---|---|---|---|
| Z1a | drop the `payload.type == "token_count"` conjunct | 1 | `E AssertionError: 4 != 3` — `test_z1_mixed_kinds_and_exact_fields` |
| Z1b | `"window": limits["limit_id"]` instead of the loop variable | 1 | `- 'window': 'codex'` / `+ 'window': 'primary'` — `test_z1_…` |
| Z2 | per-line `except (ValueError, RecursionError): continue` | 1 | `E AssertionError: 0 != 2` — `test_z2_invalid_and_empty_are_atomic` (truncated-line subtest) |
| Z3 | cache the first file's session module-wide and reuse it | 1 | `- ['1111…', '1111…']` / `+ ['1111…', 'aaaa…']` — `test_z3_session_is_per_file_and_first_meta_wins` |
| Z4 | `**values` instead of the three named window keys | 1 | `+ 'resets_at']` / `- 'extra']` — `test_z4_extras_do_not_leak` |
| Z5 | remove the no-argv guard | 1 | `E AssertionError: 3 != 2` — `test_z5_no_paths` |
| Z6 | skip `plan_type` in the required-key loop | 1 | `E AssertionError: 0 != 2` — `test_z6_required_keys` |
| Z7 | `values.get(key)` defaulting to `None` instead of requiring the key | 1 | `E AssertionError: 0 != 2` — `test_z7_windows` |
| Z8 | treat `primary is None` as a missing-key error | 1 | `E AssertionError: 2 != 0 : codex_limits: …/null.jsonl is missing "primary" on a rate_limits record` — `test_z8_null_windows` |
| Z9 | remove the `except FileNotFoundError` arm | 1 | `E AssertionError: 1 != 2` — `test_z9_missing_path` |
| Z10 | remove the `except IsADirectoryError` arm | 1 | `E AssertionError: 1 != 2` — `test_z10_directory` |
| Z11 | fall back to the literal `"unknown"` | 1 | `- ['unknown', 'unknown']` / `+ ['mixed', 'mixed']` — `test_z11_fallback` |
| Z12 | set `found_session = True` on any `session_meta` (today's OL2 code) | 1 | `E AssertionError: 'meta' != 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'` — `test_z12_later_valid_meta` |
| Z13a | `for name in reversed(paths)` | 1 | `- ['b1', 'b2', 'a1', 'a2']` / `+ ['a1', 'a2', 'b1', 'b2']` — `test_z13_order_and_flush` |
| Z13b | buffer every path's rows and print once at the end | 1 | `E AssertionError: '' != '{"ts": …[271 chars]0}\n'` — `test_z13_order_and_flush` |
| Z14 | remove the zero-total guard | 1 | `E AssertionError: 0 != 3` — `test_z14_empty_total` |
| Z15 | `pytest -q \|\| true` in `checks.unit`, with `test_z1`'s expected count broken to 999 | see below | both arms below |

Z15, run as two `nix build .#checks.x86_64-linux.unit -L --no-link` builds with the same
broken assertion:

```
intact flake.nix   → exit 1:  > E       AssertionError: 3 != 999
                              > FAILED …::test_z1_mixed_kinds_and_exact_fields
                              > 1 failed, 13 passed, 4 subtests passed in 0.81s
pytest -q || true  → exit 0   (the same break, silently green)
```

so the check's non-zero exit is load-bearing and the `|| true` ban is real. `flake.nix`
and the test file restored, `git status --porcelain` clean, `checks.unit` re-run green on
`--rebuild`.

Mutants I invented (outside the section's named set):

| arm | mutation | exit | result |
|---|---|---|---|
| O1 | fire the zero-total guard only when `len(paths) > 1` | 1 | dead — `test_z14` (`0 != 3`, the one-path arm) |
| O2 | set `"session": session` at row-build time, keeping the post-loop fix-up | 0 | **equivalent mutant** (the fix-up overwrites it); discarded, not counted |
| O2b | the same, with the post-loop fix-up removed | 1 | dead — `test_z3` and `test_z12` both (`- ['a', 'aaaa…']`) |
| O3 | iterate the windows `("secondary", "primary")` | 1 | dead — `test_z1` (`- 'window_minutes': 1440` / `+ … 10080`) |
| O4 | drop `flush=True` from the row print | 0 | **survives** — MINOR-3 |
| O5 | remove the zero-valid-lines guard | 1 | dead — `test_z2` (`3 != 2`: the empty file becomes exit 3, not exit 2) |
| O6 | hardcode `primary` in the window-missing-key message | 1 | dead — `test_z7` (`… secondary window` expected) |
| O7 | hardcode `1` for `<n>` in the zero-total message | 1 | dead — `test_z14` (`across 1` vs `across 3`) |

**mutants_total 24, mutants_killed 23, mutants_outside_named 7** (the 17 named arms all
dead; O2 excluded as semantically equivalent).

## Checks

Run from the fresh clone at `0b18bdf`, `XDG_CACHE_HOME` under the session scratch.

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass** — `14 passed, 4 subtests passed in 0.79s`; `ok 1 every fenced command starts with a documented verb` |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass** — `All checks passed!`, `2 files already formatted`, `formatted 4 files (0 changed)` |
| `nix flake check -L` | **pass** — `all checks passed!` (unit, lint, lab-vm, devShell, formatter all evaluate) |
| `nix develop -c ruff check tools tests` | **pass** — `All checks passed!` |
| `nix develop -c ruff format --check tools tests` | **pass** — `2 files already formatted` |
| `githooks/pre-commit` | **n/a** — `openai-lab` ships no hook (plan §Assumptions 5, D6); its four linters run inside `checks.lint` (`flake.nix:49-58`) and are green above |
| `repomap.py` / `tasks.py check` / `docs/MAP.md` | **n/a in this repo** — `openai-lab` has no `pkgs/evidence` and no `docs/MAP.md`. `tasks.py check` was run from `nixos-agent-env` against this review's front matter instead (below) |

## Touches and commit

`git diff 066a2e8..HEAD --stat`:

```
 tests/test_codex_limits.py | 262 +++++++++++++++++++++++++++++++++++++++++++++
 tools/codex_limits.py      | 135 +++++++++++++++++++++++
 2 files changed, 397 insertions(+)
```

Exactly the section's `touches: tools/codex_limits.py, tests/test_codex_limits.py`. Nothing
outside it. `flake.nix` is byte-identical to the base, as the section's Step 2 requires
("no change to `flake.nix`"), and the plan file lives in `nixos-agent-env` and is untouched
by construction.

One commit (`git rev-list --count 066a2e8..HEAD` → `1`). Subject compared byte for byte
against the section's `**commit subject:**` line with `cmp`: **identical**. Trailers, after
a blank line, in the order §Global Constraints names:

```
Generated-By: codex-cli 0.153.4 / gpt-6-astra (codex exec, factory run ol2f)
Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>
```

The body states the why, pastes the Step-1 red, the Step-3 green (unit, lint, `nix flake
check`), and the full mutant table, and says in one sentence that the landing closes
`codex-rate-limits-shape-unmeasured` — with the honest qualifier that the named rollout's
row count stays a manual measurement. It also carries `Deviation: flake.nix — temporary
required Z15 pytest error-swallowing mutant; restored to HEAD before final gates and
commit, with no landed change.` §Global Constraints explicitly exempt a transient mutant
file from the deviation rule, so this is an over-declaration, not a deviation; it names a
file that does not appear in the diff, and I record it only so a later reader of the
deviation ledger is not confused. No board commit, no `--no-verify`.

## Findings

### MAJOR — none.

Both MAJORs of the OL2 gate are closed, item by item:

- **OL2 MAJOR-1** ("the extractor matches nothing that exists; it exits 0 with an empty
  stream against every real rollout") — **closed twice over.** The predicate is now the
  measured nested one (`tools/codex_limits.py:61-68`), verified against the operator's own
  rollout: 20 rows, exit 0, empty stderr, matching an independent count of 20 carriers ×
  (20 non-null `primary` + 0 non-null `secondary`). And the silent-empty case itself is
  gone: a clean run with zero rows now prints `codex_limits: 0 rate_limits rows found
  across <n> path(s)` and exits 3 (`:125-131`), asserted for `<n>` = 1 and 3 by
  `tests/test_codex_limits.py:249-256` and probed live. It does **not** fire when rows
  exist — `tests/test_codex_limits.py:257-258` inserts one worked example into the last of
  three otherwise-empty paths and asserts exit 0 with one row; probed independently
  (`idle.jsonl one.jsonl` → `exit=0`, one row printed). It also never pre-empts an error
  arm: `idle.jsonl` + a nonexistent path → `exit=2`, and a directory → `exit=2`.
- **OL2 MAJOR-2** (the gap claim does not close) — **closed, with the caveat in C8.** The
  shape now matches; the fixtures are corrected to the nested nine-key shape
  (`tests/test_codex_limits.py:24-52`) and are hand-built, not copied; the tool emits rows
  for the operator's named rollout. The only unmet words are "asserted by `checks.unit`",
  which no check can satisfy. My judgement, stated plainly as asked: **the claim should
  close**, on the two measurements plus the fixture-level assertion of the row rule, and
  the ledger's `closes_by` should be amended as C8 recommends.
- **OL2 MINOR-1** (a first `session_meta` without an `id` consumes the slot) — **closed.**
  `tools/codex_limits.py:56-60` moves `found_session = True` inside the `"id" in payload`
  branch; `test_z12` (`:205-217`) covers payload `{}`, `None` and `[]` before a valid meta;
  mutant Z12 restores the old code and dies.
- **OL2 MINOR-2** (a directory raises an uncaught `IsADirectoryError`) — **closed.**
  `tools/codex_limits.py:113-115`; `test_z10` (`:186-190`) passes the directory first and a
  clean file second; mutant Z10 dies. Probed: one stderr line, exit 2, no traceback.
  (`PermissionError` remains out of scope, as the section says in Interfaces 6.)

### MINOR-1 — the `UnicodeError` arm has no test

`tools/codex_limits.py:116-118`

```python
        except UnicodeError:
            print(f"codex_limits: {path} is not JSONL", file=sys.stderr)
            return 2
```

Carried unchanged from OL2 and still the one refusal path with no test behind it: no
fixture writes invalid UTF-8, so nothing would notice if the arm were deleted or its
message drifted. I probed it by hand and it is correct —

```
$ printf '\xff\xfe{"type":"x"}\n' > probe/bad-utf8.jsonl
$ python3 tools/codex_limits.py probe/bad-utf8.jsonl
codex_limits: …/probe/bad-utf8.jsonl is not JSONL
exit=2
```

— so this is an untested stated behaviour, not a defect. Neither gate's section named it;
recorded for the next round that touches this file.

### MINOR-2 — the new exit code is documented only in the source

`tools/codex_limits.py:1-5` (the module docstring) describes the shape and the per-file
atomicity but names none of the three exit codes, and `grep -rn 'codex_limits' README.md
docs/ AGENTS.md` returns nothing — so a caller learns that 3 means "clean run, no rows"
only by reading `main`. `touches` forbids a docs file this round, but the docstring is in
`touches` and would have carried it in one line. Weigh with the design note below.

### MINOR-3 — the flush *timing* half of the carried item 9 is untested

`tools/codex_limits.py:124` — `print(json.dumps(row), flush=True)`. Dropping `flush=True`
(my mutant O4) leaves the whole suite green (`14 passed, 4 subtests passed`), because the
tests capture a finished subprocess's stdout, where CPython's exit-time flush hides the
difference. The *observable* half of the contract — earlier rows still on stdout after a
later path fails — is genuinely tested (`test_z13`, mutant Z13b dead), so nothing a caller
can see is unguarded; only the "flushes before the next path opens" wording is
unfalsifiable with this harness. Recorded, not counted against the verdict: making it
testable needs a streaming reader, which is out of proportion to the risk.

### Design note (asked for): is exit 3 for an idle session sound, or a trap?

The choice was the orchestrator's, not the seat's, and the seat implemented it exactly.
My assessment: **sound, with one caller-facing sharp edge worth documenting rather than
redesigning.**

For it: it removes precisely the failure mode that got OL2 rejected — a contract-correct
empty stream that is indistinguishable from success. It also degrades gracefully: it is a
per-*run* verdict, not per-path (three paths, one row in the last → exit 0, tested and
probed), so a batch caller is not punished for one quiet file; and it never pre-empts a
real error, since every exit-2 arm returns first (probed both ways). The stderr line names
the path count, so an operator seeing exit 3 is told what happened without reading the
source.

Against it: an idle session is a legitimate, expected state, and under `set -e`, `cmd ||
die`, or a `$(…)` capture, exit 3 now aborts a pipeline that should have carried on with
an empty result. Any consumer must write `|| [ "$?" = 3 ]`, and MINOR-2 means nothing tells
them to.

The balance favours keeping it: the alternative (exit 0 plus a stderr note) restores
exactly the ambiguity MAJOR-1 was about, since a caller checking only the status code
learns nothing. My recommendations, both cheap and neither blocking this landing:
document the three codes in the module docstring, and when a later task wires this into an
evidence writer, absorb 3 as "empty, not failed" at the call site (or add an explicit
`--allow-empty` flag) rather than changing the exit code again — three test arms now pin
it, and churning it would cost more than the sharp edge does.

## Verdict

**APPROVED.**

Both MAJORs closed and both MINORs with them; 17/17 named mutant arms dead plus 6 of 7 of
mine; red before green reproduced exactly as the body pastes it; `unit`, `lint` and `nix
flake check -L` green on `--rebuild`; ruff clean; touches exact; one commit with a
byte-identical subject and the two required trailers; no fixture copied from the operator's
file and no secret in the tree. The extractor does what the task was re-spec'd to make it
do, proven against the operator's own rollout: 20 rows where 20 is independently the right
answer.

The plan defect recorded in the front matter is the section's (and the ledger's) closing
condition "with the row count asserted by `checks.unit`", which is unsatisfiable inside a
Nix sandbox that cannot see `~/.codex` and under a constraint that forbids fixturing it.
It is recorded against the plan; it changes nothing about this commit, which is approved
on its own terms. The gap claim `codex-rate-limits-shape-unmeasured` should be closed on
this landing, with the amendment in C8.
