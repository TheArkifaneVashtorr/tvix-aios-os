---
reviewer: opus
majors: 3
minors: 5
mutants_killed: 16
---
# Opus gate — seat run sc7, task G11r — APPROVED

Task: `G11r` (code, S) — re-plan of G11 (rule A1): one notion of "landed" for status and
scheduling; the board says what it omits. Plan
`docs/superpowers/plans/2026-09-05-session-context.md` §`G11r`; spec amendment 6; rejections
it answers `docs/reviews/2026-09-05-opus-review-sc5-G11.md` and `…-G11b.md`. Workspace
`/home/dalhaka/factory/ws/sc7/G11r`, branch `task/G11r`, head `2cbcc10a1a10`, base
`5349582`. Reviewed in a throwaway clone; the workspace was not touched (still clean at
`2cbcc10`).

## Summary

All four contract points of the re-plan are implemented, and I verified each one with my own
fixtures on **real `git init` repositories with real `git log`** — never the implementer's
`fake_git`. The G11b defect is dead: on the live-shaped `PB1 → PB0(repo gaming)` fixture with
gaming's history actually carrying PB0's subject, `derive_status(PB1) == ready`,
`waves(g) == [["PB1"]]` (filtered and unfiltered), `seat_groups → ['"PB1"']`, `factory_args →
['PB1']` and the brief reads `**Next wave** — nixos-agent-env: PB1`; drop the union in `waves`
and the waves assertion fails at line 1217 while the status assertion above it still passes —
the exact defect, now pinned. The board's tree-only graph defers such a task and its header
carries the new sentence byte-for-byte; `check` refuses an unconfigured `**repo:**`;
`defined_roots` is **renamed** `resolvable_roots` and pinned; the `conflicts` fixture is
two-plan and its mutation now dies. Every G11b rule clause still holds — I re-derived them by
hand. Eighteen mutations applied, **eighteen killed**, including G11b's only survivor and
G11's M7b. `evidence-unit` (84), `lint` and the hook are green.

One thing is wrong and must be corrected on landing: **`docs/ledger/task-status.toml` does not
end with a newline** (MAJOR 1). Mode is right (0644), the header is OG1b's plus the required
sentence, it parses — but the plan says "mode 0644, trailing newline", G11b's rule says "File
ends with a newline", and the previous gate named this exact byte. It is one byte, no code
change, and nothing else in the commit is affected, so it is an approval with a correction
rather than a fourth round on G11's lineage — the substance of the re-plan is delivered and
independently verified.

## Contract (four points verified)

Every row is my own fixture (`git init`, real commits, real `git log`) run against the
delivered `pkgs/evidence/tasks.py`.

### 1. One notion of "landed": `resolved_elsewhere` published and consumed

Fixture: `nixos-agent-env` and `gaming` as two real repos; `nixos-agent-env`'s
`2026-09-05-operator-items.md` defines `PB0 (**repo:** gaming)` and `PB1 (dependsOn PB0)`.

| gaming's log | PB1 state | `resolved_elsewhere` | `waves` | `waves(plan=)` | `seat_groups` | `factory_args` | brief |
|---|---|---|---|---|---|---|---|
| no PB0 subject | `blocked \| PB0` | `[]` | `[]` | `[]` | — | `[]` | `**Next wave** — none` |
| carries `gaming: nixpkgs relock (test: flake-check)` | `ready` | `['PB0']` | `[['PB1']]` | `[['PB1']]` | `['"PB1"']` | `['PB1']` | `**Next wave** — nixos-agent-env: PB1` |

All four dispatch surfaces agree with the state. **Mutation** (drop
`landed |= set(repo_graph.get("resolved_elsewhere", ()))` from `waves`): the test fails at
`tests/evidence/test_tasks.py:1217`, `assert [] == [['PB1']]`, **after** the
`by["PB1"]["state"] == "ready"` assertion on line 1216 has passed — the G11b defect
reproduced and killed. A second mutation (`scan_repo` returns `"resolved_elsewhere": []`)
also dies. **PASS.**

### 2. The board defers, and says so

Fixture: one real tree whose plan holds `PB0 (**repo:** gaming)`, `PB1 (dependsOn PB0)` and a
plain local `TA`.

```
board states: {'PB1': ('deferred-to-brief', ''), 'TA': ('ready', '')}
block: '**Queued (derived from this tree; tasks whose dependencies run in other repos, and
        in-flight state, are in the session brief).** TA (op.md)\n'
```

`PB1` and `PB0` are absent from the block; the header matches the plan's string exactly
(`block.startswith(HEADER)` on the literal from the plan). **Mutation** (do not set
`deferred-to-brief`): `test_board_graph_defers_cross_repo_dependent` fails. A second mutation
reverting the header wording kills three tests. **PASS.**

### 3. `check` refuses an unconfigured `**repo:**`

Fixture: a real repo whose plan has `**repo:** dsh-harnes` (the typo from G11b MINOR 2) and a
dependent `T2`.

```
tasks: nixos-agent-env/T1 repo: dsh-harnes not in docs/ledger/repos.toml
```

Byte-for-byte the plan's message shape. The valid set comes from the ledger under `--root`
even when the graph was scanned against a `--repos` override (`main` reads
`<root>/docs/ledger/repos.toml` for `configured_repos`), so the lint check's one-repo override
does not turn the live `**repo:** dsh-harness` lines into errors — confirmed on real data
below. **Mutation** (drop the rule): `test_check_rejects_unconfigured_repo_value` fails.
**PASS.**

### 4. `conflicts` fixture, and `defined_roots`

- The `conflicts` assertion is no longer vacuous: `test_task_status_withdrawn_and_unknown_key`
  now writes a second plan `q.md` whose ready `T3` shares the withdrawn `T1`'s `a.py`. I
  reproduced it on real repos: `conflicts(g) == []` with `T1` withdrawn and `T3` ready in a
  different plan, and **mutation MU4** (G11b's lone survivor M6 — `conflicts` iterates
  `repo_graph["tasks"]` instead of `open_tasks`) now **fails** that test. **PASS.**
- `defined_roots` is **renamed**, not removed: `scan_repo`'s return is
  `['attributed', 'attributed_elsewhere', 'chains', 'legacy', 'name', 'path',
  'resolvable_roots', 'resolved_elsewhere', 'tasks', 'untracked_plans']` — `defined_roots` is
  gone and `resolvable_roots` carries its meaning. Load-bearing: **MU5** (drop it from
  `check`'s resolvable set — G11's M7b) kills
  `test_check_accepts_dep_redirected_to_other_repo`. **PASS (renamed).**
- MINOR 3 closed: the file's last line is
  `# For a task whose section names \`repo:\`, the row's \`repo\` is that attributed repo.`
  I confirmed the semantic on real repos — a row keyed `("repo-b", "a.md", "X1")` (the
  attributed repo, the defining plan's basename) withdraws `X1`; keyed by the defining repo it
  is refused as `tasks: task-status names unknown key repo-a/a.md/X1`.

### G11b's rule clauses, re-derived by hand

| clause | my evidence | verdict |
|---|---|---|
| per-repo `check` namespace | `tasks: repo-b/AA2 dependsOn ZZ9: unknown key`; MU8 (global union) kills `test_check_rejects_dep_defined_only_in_other_repo` | pass |
| attribution (status in the repo it runs in) | real data: H1/H2/H2b/H2c under `dsh-harness`, PB0 under `gaming`, none under `nixos-agent-env` | pass |
| satisfied only by the attributed repo's own landing | MU6 (always satisfied) and MU9 (resolve against **this** repo's log) both killed | pass |
| status rows validated | `withdrawnn` / `""` / `done` / `landed` → `tasks: task-status row repo/p.md/T1: unknown status …`, and the task stays `ready` (never silently withdrawn); unknown key → its own error | pass |
| `STATES` gains `withdrawn`, `parked`; brief columns; never scheduled; once in the brief | `STATES` ends `…, 'blocked', 'withdrawn', 'parked'`; header has 12 columns and 12 separators; row `\| repo \| 0 \| 0 \| 0 \| 0 \| 0 \| 2 \| 0 \| 1 \| 1 \| 0 \| 0 \|`; `waves → [['T2','T3']]`; `**Withdrawn/parked:** repo/T1 · repo/T4`; each named once | pass |
| `json` emits only `STATES` values | real data: states seen = `{blocked, landed, ran, ready, rejected}` ⊆ `STATES` | pass |
| `board_graph` carries `task_status`; `write-board` omits a withdrawn key | present; MU10/MU16 killed | pass |

Commit hygiene: **one** commit on `5349582`. Files touched are exactly G11r's `touches`
(six, no extras). The plan diffs are **four added `**repo:**` lines only** (H1, H2, H2b in
`2026-09-05-harness-router.md`; PB0 in `2026-09-05-operator-items.md`) — no removed lines, no
heading touched, H2c's line correctly left alone because it was already on base.
`docs/OPERATIONS.md` changes only the generated block. Subject `cmp`-identical to G11's plan
line (174 bytes, both files). `Generated-By: dsh …` and `Co-Authored-By: Claude Fable 5.1`
both present; the body discloses `resolved_elsewhere`, the deferral, the `check` rule, the
rename and the fixture change.

## Checks

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | **pass** — 84 passed |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **pass** — treefmt 85 files 0 changed, statix/deadnix/ruff all clean |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 (`docs/OPERATIONS.md queue block was stale and has been regenerated`) → `git add` → exit 0, `render.test.mjs: all assertions passed`. **One** regenerate-and-re-add, exactly the allowance |
| pytest | `pytest tests/evidence -q -p no:cacheprovider` | 84 passed |

The hook's single regenerate is G8c's known staleness tax: the commit's own key leaves the
queue only once its subject is in `git log`, so the block moves `B1 G11r OG1r …` →
`B1 G12 OG1r …`. Same as on G11 and G11b. Not a fault. Note that `lint` does **not** catch
MAJOR 1: treefmt does not format `.toml`, so nothing in the gate enforces the newline clause.

## Red before green

G11b's `pkgs/evidence/tasks.py` (fetched from `/home/dalhaka/factory/ws/sc5/G11b`, `f10636c`)
restored under HEAD's tests: **5 failed, 79 passed**. All five fail behaviourally — no
signature `TypeError`s this round.

| test | failure on G11b's tasks.py |
|---|---|
| `test_resolved_elsewhere_feeds_waves_and_brief` | `assert [] == [['PB1']]` at line 1217 — the **scheduling** half, after the state assertion passed |
| `test_board_graph_defers_cross_repo_dependent` | `assert 'blocked' == 'deferred-to-brief'` |
| `test_check_rejects_unconfigured_repo_value` | `assert False` — no `repo: … not in docs/ledger/repos.toml` error emitted |
| `test_render_board_block_header_and_ready_blocked_only` | `assert False` — old header wording |
| `test_board_block_roundtrip_and_drift` | old header wording in the round-tripped block |

The fourth contract point (the two-plan `conflicts` fixture) is correctly **not** red on
G11b — it is a fixture strengthening, and its red is mutation MU4, which G11b's single-plan
fixture survived and this one kills. `tasks.py` restored; the clone verified byte-identical
and `git status --porcelain` empty afterwards.

## Mutation table

Each mutation applied to the delivered tree, full `tests/evidence` run, then reverted; the
file was confirmed SHA-256 identical at the end (`5ff735f24618538b…`).

| # | mutation | result |
|---|---|---|
| MU1 | **point 1** — `waves` drops the `resolved_elsewhere` union | **killed** — `…feeds_waves_and_brief` at the waves assertion |
| MU2 | **point 2** — `board_graph` does not defer the cross-repo dependent | **killed** — `…defers_cross_repo_dependent` |
| MU3 | **point 3** — `check` drops the unconfigured-repo rule | **killed** — `…rejects_unconfigured_repo_value` |
| MU4 | **point 4** (= G11b's surviving M6) — `conflicts` iterates all tasks, bypassing `open_tasks` | **killed** — `…withdrawn_and_unknown_key` |
| MU5 | **G11's M7b** — `check` drops `resolvable_roots` from the resolvable set | **killed** — `…accepts_dep_redirected_to_other_repo` |
| MU6 | G11b M1 — cross-repo edge always satisfied | **killed** |
| MU7 | G11b M2 — `extra_landed` never passed (G11's bug) | **killed** — 3 tests |
| MU8 | G11b M3 — global namespace in `check` | **killed** |
| MU9 | G11b M4 — resolve the landing against **this** repo's log | **killed** — 3 tests |
| MU10 | G11b M5 — withdrawn/parked still scheduled | **killed** — 2 tests |
| MU11 | G11b M7 — status validation dropped | **killed** |
| MU12 | G11b M10 — task-status unknown-key rule dropped | **killed** |
| MU13 | G11b M11 — `FIELD_RE` drops `repo` | **killed** — 7 tests |
| MU14 | G11b M12 — `own_plan_tasks` keeps foreign-repo tasks | **killed** — 3 tests |
| MU15 | G9-b — `conflicts` drops the different-plan condition | **killed** |
| MU16 | G8c-g — `board_graph` reads `repos.toml` | **killed** |
| MU17 | board block header reverts to the old wording | **killed** — 3 tests |
| MU18 | `scan_repo` stops publishing `resolved_elsewhere` | **killed** |

**18 applied, 18 killed.** Ten are G11b/G9/G8c re-runs (more than the eight asked for), and
both of G11b's outstanding survivors — M6 (vacuous `conflicts` fixture) and M7b — are now
dead.

## Real data

A temporary `repos.toml` in a scratch directory naming `nixos-agent-env` at the clone and the
four siblings at their real paths; `--root <clone>`, `--runs-dir /home/dalhaka/factory/runs`,
`--store /home/dalhaka/factory/store`. Read-only everywhere outside the clone.

```
| repo | landed | approved | rejected | ran | recorded | ready | blocked | withdrawn | parked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 65 | 0 | 1 | 9 | 0 | 5 | 3 | 0 | 0 | 1 | 0 |
| media | 3 | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| gaming | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nixos-skill | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dsh-harness | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
```

- `dsh-harness`: **H1, H2, H2b, H2c all `landed`**, each by that repo's own commit subject.
- `gaming`: **PB0 `landed`**.
- `nixos-agent-env`: **PB1 `landed`** (its subject is in the clone's history, which is live
  main) — the gate brief's expectation, met exactly; H1/H2/H2b/H2c/PB0 appear in no other
  repo's task list.
- `attributed` for `nixos-agent-env` = `[H1, H2, H2b, H2c → dsh-harness; PB0 → gaming]`;
  `resolved_elsewhere` = `['H1', 'H2', 'PB0']` (chain roots).
- `check`: **rc=0, no output.** `check --board`: rc=0. `configured_repos` = all five, read
  from the ledger under `--root`, so the `**repo:**` values validate even under the `--repos`
  override.
- `write-board` on the clone: no `H1/H2/H2b/H2c/PB0/PB1` in the block, the plan list drops
  `2026-09-05-harness-router.md` entirely, and the header carries the new sentence:
  `**Queued (derived from this tree; tasks whose dependencies run in other repos, and
  in-flight state, are in the session brief).** B1 G12 OG1r PW1glm PW1kimi PW1pro RT5b SB1 SB2
  SB3b (…)`. The committed block is the same line with `G11r` in place of `G12` — the G8c tax.
- Every emitted state on real data is in `STATES`.

## Findings

**MAJOR 1 — `docs/ledger/task-status.toml` has no trailing newline; fix it on landing.**
The file is 881 bytes, mode `0644`, OG1b's header verbatim plus the required sentence, and it
parses — but `git diff` reports `\ No newline at end of file`. The G11r plan says "mode 0644,
trailing newline"; G11b's "rule, exactly" says "File ends with a newline"; the G11b review
said in terms "fix the mode to `0644` and add the trailing newline". The mode was fixed, the
newline was not — the omission is inherited byte-for-byte from OG1b's file, which also lacks
it. Nothing catches this: `treefmt` does not format `.toml`, no test asserts it, and the hook
is green. It has no behavioural consequence. **Required amendment before this lands:** append
one newline (and, if OG1b lands first and wins the create/create resolution, do the same
there). Worth a follow-up: a lint assertion that every tracked text file ends with a newline
would have caught this twice now.

**MAJOR 2 (latent, inherited from G11b — for the next task, not a rejection ground) — an
attributed task cannot depend on a key local to the plan file that defines it.** Verified on
real repos: repo A's plan defines `L1` (A's own, landed) and `X1 (**repo:** repo-b,
dependsOn L1)`. `X1` is imported into repo B's graph, where the resolvable set is B's, so:

```
A tasks: [('L1', 'landed', 'x: l1 (test: unit)')]
B tasks: [('X1', 'blocked', 'L1')]
check  : ['tasks: repo-b/X1 dependsOn L1: unknown key']
```

`X1` is blocked forever **and** `check` emits a false error, on a graph that is correct. This
is the same failure class G11 was rejected for, in the mirror direction (today only the
"local task waits for a foreign one" direction is exercised — PB1→PB0, H2→H1 — and it works;
"foreign task waits for a local one" does not). G11b's rule says resolvable keys are decided
by *the plan file the task is defined in*, so the implementation diverges from the rule for
imported tasks; the previous gate declared G11b's body "sound … preserve verbatim" and did not
catch it, so it is not this round's regression. It is clean on the live tree (`check` rc=0).
Fix by resolving an imported task's `depends_on` against its **defining** repo's
`resolvable_roots`, and pin it.

**MINOR 3 — `check(board_graph(root))` emits a spurious unconfigured-repo error.** `check`
falls back to `[r["name"] for r in graph["repos"]]` when `configured_repos` is absent, and
`board_graph` never sets it and carries exactly one repo, so on the real tree shape:

```
check(board_graph(root)) → ['tasks: nixos-agent-env/PB0 repo: gaming not in docs/ledger/repos.toml']
```

`main` never does this (`check --board` only compares drift against the full graph, and that
path is rc=0), so it is latent — but the fallback is a trap for the next caller and for
hand-built test graphs. Either give `board_graph` a `configured_repos` read from the ledger,
or make the rule skip when the key is absent.

**MINOR 4 — `deferred-to-brief` is a state outside `STATES`.** G11b's rule says only `STATES`
values are emitted; the board graph emits a tenth. Nothing breaks today (`render_brief` guards
with `if t["state"] in counts`, so it does not raise — it silently drops the task from every
column, and `open_tasks` excludes it from scheduling, which is the intent). But a
board-graph brief would under-count silently, and the value is unpinned. Either add it to
`STATES` (and to the brief's columns) or name it in a `BOARD_STATES` constant and say in the
spec that the board graph's state vocabulary is a superset.

**MINOR 5 — one `git log` per redirected root per repo, still.** G11b's MINOR 6 is unchanged:
`landed_subjects(tgt["path"], run=run)` is called inside the resolution loop, so each repo's
scan spawns one `git log` per redirected chain root. Five roots × five repos today. Cache the
per-repo subject sets.

**MINOR 6 — G11b's MINOR 7 (a chain split across repos) is unchanged.**
`defined.setdefault(root, t["repo"])` still takes the first member's `repo` in file order.
No crash, no wrong state today; the spec should say whether the root's `repo` binds every
member.

**Note for the integrator — the create/create conflict on `docs/ledger/task-status.toml` is
still open.** OG1b was rejected and re-planned as OG1r; whichever lands first, the file must
end up with OG1b's header, the attributed-repo sentence, mode `0644` **and** a trailing
newline.

## Deviations

- **Recorded, not allowed, must be corrected on landing:** no trailing newline on
  `docs/ledger/task-status.toml`, against the plan's literal instruction and G11b's rule
  clause. Not disclosed in FACTORY-NOTES or the commit body. One byte, no code change, no
  behavioural effect — hence a correction on approval rather than a fourth round on G11's
  lineage. See MAJOR 1.
- **Recorded, allowed, correct:** `defined_roots` was **renamed** `resolvable_roots` rather
  than removed, and the choice is stated in FACTORY-NOTES and the commit body — the plan's
  point 4 explicitly asked for "renamed … or removed — state which". MU5 proves it
  load-bearing.
- **Recorded, allowed:** the hook needed one regenerate-and-re-add of `docs/OPERATIONS.md`
  (`G11r` → `G12`), exactly the plan's Step 4 allowance and G8c's known tax.
- **Not this round's fault:** MAJOR 2, MINOR 5 and MINOR 6 are inherited from G11b, which the
  previous gate directed be preserved verbatim. Carry them into the next task on this file.
- **Gate-brief expectations, all met as written:** PB1 `landed` under `nixos-agent-env` on
  real data (this clone's base is live main, which carries the subject — unlike G11b's older
  base, where it read `ran`).
