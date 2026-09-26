# Telemetry store, sub-project 1 — the fence, the `tasks` and `gates` streams, the join (plan, 2026-09-06)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) reads the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and a commit subject. A seat sees only `## Global Constraints`, `## Assumptions` and its own section.

**Goal:** every row entering `/var/lib/evidence` passes one allowlist (`pkgs/evidence/streams.py`); every seat result and every gate review becomes a row (`derived/tasks`, `derived/gates`); a reader joins them on `(run_id, key)` behind an n-gate. This is the floor the seat-driver spec's ladder report stands on.

**Spec:** `docs/superpowers/specs/2026-09-06-telemetry-store-1-design.md` (M, 2,392 words; T1, T2, T3, T10a approved by the operator 2026-09-06 ~09:40 CDT). The parent design `docs/superpowers/specs/2026-09-05-telemetry-store-design.md` §3.3 (field tables), §3.4 (writers) and §3.5 (the fences and mutations (a)–(j)) is the record of *why*; where the two disagree the sub-project spec wins, and where the sub-project spec contradicts itself this plan says which side it takes (§Decisions).

**Packet:** `scratchpad/plan-telemetry-1/packet/{mechanical,record,field,operator,target}.md`, taken 2026-09-06T09:26 CDT at HEAD `02756e012f5e` (docs-only ahead of live `a53d2e5`); `tasks.py check` printed nothing. Every fact below carries the command that produced it; the spec's inventory is corrected in three places (map item 4).

**Invariants:** none of brief §3 is touched. The store stays operator-only, nothing new leaves the machine, no credential moves; no key, token or `/var/lib/secrets` path appears in any fixture (the secret-shape fence refuses them by construction).

## Questions for the operator

Two questions, each answerable in one word. A third is not needed: every other open point is a plan decision (§Decisions).

1. **The migration of 137 gate-review files.** The spec recommends landing it as T3's second commit. This plan types it as its own docs task **T3M** (S), `dependsOn` T3, one commit, gated on the script's `--check` output (byte-identical second run) and a sample of the diff — because the landing recipe resets every task branch to *one* named commit (§Dispatch A1) and the gate judges one commit. **Recommendation:** T3M as typed here. **Default if unanswered:** as recommended.
2. **T10a without T6.** The join's live inputs are the rows T2's loop and T3's ingest produce; T6 (runs without results, the activity export, transcripts, audit rollups) stays a later task. **Recommendation:** accept. **Default:** as recommended.

## Spec-to-task map

Spec items are numbered as the target packet numbers them (§"Full numbered content"); sub-items as the spec's own lists.

| spec item | where it lands |
|---|---|
| 1 header, 2 goal, 3 invariants | this header; row 9: no invariant touched, no `sudo`/`systemctl`/secret path in any task |
| 4 "what exists" | the Facts blocks below re-verify every anchor; three corrections: (a) `nixosModules/helm.nix`'s `evidenceCli` embeds `pkgs/evidence` for the **`evidence` CLI** that `helm-flake-check` calls — the collector wrapper `helmCollect` runs the lone file `${../pkgs/helm/collect.py}` with no `pkgs/evidence` on its path, so "collect.py imports evidence" needs a `PYTHONPATH` line in two wrappers (T1W); (b) 18 review files open with the block, not 25 (the other 7 carry `plan_defect:` as prose in their body); 146 have no block: 119 with a parseable H1, 27 with a legacy H1 (T3, T3M); (c) `usage.output` and `seat@<id>` cannot pass the spec's own fences (`output` is a forbidden name; `@` is outside the id class) — T2 stores `usage.out` and the job id (§Decisions) |
| 5.1 kinds and the version map | T1 |
| 5.2 string classes | T1 (plus one pattern class, `re`, that the spec's own `route` field and the recorder's `integration_branch` need — §Decisions) |
| 5.3 `append` validates before the lock; `validate`; `replace_stream` | T1 |
| 5.4 forbidden names, declared exceptions | T1 |
| 5.5 secret shapes | T1 |
| 5.6 writers migrate (`collect.py`, `factory.py`) | T1W |
| 5.7 the lint grep and the direct-open unit test | T1W (the grep, the two direct-open tests under `helm-unit` and `ledger-unit`); the literal `/var/lib/evidence` in `pkgs/evidence/{tasks,judgements,report}.py` and `tools/factory/seat/factory-lib.sh` is removed in T1 so wave 2's three tasks stay disjoint |
| 5 tests (a)–(j) | (a)(b)(c)(d)(e)(h)(i) T1; (f) T1W; (g) T2; (j) out: T17's audit (the spec says so) |
| 5 acceptance | T1 (`evidence record` refuses; `test_judgements.py` passes unchanged; the shape-A literal validates) |
| 6.1 `ingest result`, 6.2 `error_class`, 6.3 the line in `factory-task` | T2 (6.3 also writes a `plan:` line into the result, so A1's acceptance — `tasks` rows carrying the plan — is measurable; §Decisions) |
| 6 tests, 6 acceptance on core | T2; Operator step 3 |
| 7.1 one block, the lint rules | T3 |
| 7.2 the migration script | T3 (the script and its fixtures); T3M (the commit over `docs/reviews/`) |
| 7.3 `ingest reviews`, 7.4 the line in `factory-integrate` | T3 |
| 7 tests, 7 acceptance | T3; Operator steps 4–5 |
| 8.1 `read()` learns `derived/` and monthly globs | T1 (the closed `derived/`, `ledger/` subdirectory rule in `stream_path`, needed by T2/T3's writers) and T10a (monthly globs) |
| 8.2 `join_tasks_gates`, 8.3 `n_gate` | T10a |
| 8 tests, 8 acceptance | T10a; Operator step 6 |
| 9 waves, touches, the CLI subcommand ownership | §Waves; decided: T1 lands the `ingest` dispatch table in `evidence.py` naming `result` and `reviews`; T2 and T3 only add their modules (§Decisions) |
| 10 operator steps, rollback | §Operator |
| 11 the two questions | above |
| 12 risks (a)–(d) | (a) T1's declared-field walk and the delegation test; (b) T2's fixture table pins every class and precedence pair; (c) T3M's `touches` is `docs/reviews` — no plan path, so the orchestrator guard's plan rules never fire; (d) T3's rules are scoped by `front_matter_from`, older reviews are read as they are |
| 13 not in this sub-project | §Not in this plan |

## Decisions

Each with the reason and the alternative; the operator can veto any by a word.

- **D1 T1 split.** The spec's T1 (M) carries the library, three fences, two writer migrations, a lint gate wired into two places, a Nix wrapper change in two files and a judgements refactor. An M that needs a second commit is two tasks (design §3 Step 3), so the writers and the lint gate are **T1W (S)**, `dependsOn` T1. Alternative: one M task — refused as over the size ceiling for one commit.
- **D2 The `ingest` table.** T1 lands `INGEST_MODULES = {"judgements": "judgements", "result": "ingest_result", "reviews": "ingest_reviews"}` in `evidence.py`; a name whose module is absent exits 2 `ingest <name>: not available in this tree`. T2 creates `ingest_result.py`, T3 `ingest_reviews.py`; neither edits `evidence.py`, so they run in one wave. Alternative: sequence T2 then T3 — slower, no gain.
- **D3 Two ledger names the fence forbids.** `factory-findings.title` becomes `title_sha256` (the parent design §3.3 says so; the dedup key keeps working) and `dsh-sessions.slug` is dropped (a prompt-derived directory name is free text; no reader uses it: `grep -n slug tools/ledger/factory.py` shows only the extractor). The ledger has never held real data on core (the evidence-store plan's inventory: the directory did not exist). Alternative: declare both as exceptions — refused, they are exactly what the fence exists for.
- **D4 `task-result.usage` field names.** `{in, out, cache_read, reasoning, events, duration_s}` — the spec's `output` is on its own forbidden list; `in`/`out` are the ledger's existing names (`dsh-sessions`). `seat_unit` stores the job id `YYYYmmdd-HHMMSS-<6 hex>` (the unit name is `seat@` + id by construction; `@` is outside the id class).
- **D5 One pattern class.** `re(<regex>)` is added to the eight string classes for fields the spec itself defines by pattern (`task-result.route`) or that must validate unchanged (`factory-run.integration_branch` is the git ref `factory/<prefix>-integration`; `plan-judgement.author` is `dsh:<model-id>`). It is never used for a field the eight classes can express.
- **D6 `error_class` precedence and the `done` guard.** The spec's table is unordered; the driver evaluates exit-code facts first (`submit-failed`, `timeout`), tail patterns only when the task did not reach `done` (a finished task whose last 4,000 bytes contain the word `provider` is `none`, not `provider-error`), then the synthesised-block classes, then `boot-failure`, then `none`. Each precedence pair has a fixture (T2 Tests).
- **D7 `round_kind`/`round` from the key.** A rule, not a list: trailing round tokens are stripped from the key's end — `r` with optional digits (a numbered re-plan) or one fix letter `b`/`c`/`d` — until none matches; any `r` token → `replan`, else any fix letter → `fix`, else `first`; `round` = 1 + Σ weights (`b`1 `c`2 `d`3 `r`1 `r<n>` n). `chain_root` stays `tasks.chain_root()` as the spec says, even where it differs from the stripped base (`OG1r2` is its own graph root today; the join is on `(run_id, key)` and never on the root).
- **D8 `rework` → `rejected`.** The DeepSeek `.review.md` grammar is `approve|rework|reject` (6 of 23 files say `rework`); the gates enum has no `rework`; `rework` means "fixable defects found", the closest arm is `rejected`. Alternative: `unknown` — hides six real verdicts.
- **D9 The review lint's date scope.** `plan_defect` is required in a block only for reviews dated on or after `front_matter_from` (2026-09-07); the migration adds blocks without it to 119 older files and the ledger carries their class. Today's rule (`plan_defect missing` on any block) would turn the gate red on the migration commit. Unknown keys, non-integer counts, an unknown reviewer and a duplicate key are refused on every block whatever the date (the migration never writes them).
- **D10 Legacy H1 files keep no block.** 27 reviews open with a pre-`REVIEW_RE` H1 (`# Opus gate round 2 — …`, `# Opus gate — N16 round 3 …`); `tasks.py check` requires the H1 to follow a block, so the migration skips them (counted, printed); their gates rows carry `verdict: unknown`, run and key from the file name.
- **D11 `plan:` in the result.** `factory-task` writes `plan: <absolute path>` beside `route:`; the ingest maps it to `docs/superpowers/plans/<name>` (null on the 237 existing results). Design §4 A1's acceptance ("`tasks` rows under the prepared run name with the plan's `plan` field") is unmeasurable without it.
- **D12 `derived/` is created by the writer** (`replace_stream` makes the directory 0750); no tmpfiles rule is added to `evidenceStore.nix` in this plan (T8's timer task may add it). Nothing in this plan needs a switch to be tested.
- **D13 Generated files are not `touches`.** `docs/MAP.md` (every task that adds a file must regenerate it for `lint`) and the board's queue block are regenerated by the seat as part of its one commit and merged at landing (recipe step 2); listing MAP in every `touches` would fold wave 2 into one serial group for no safety gain.

## Global Constraints

- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown, no reading `/var/lib/secrets/*`, `~/.config/openrouter/key` or `~/.config/restic/password`. The operator switches (§Operator). Never write under `/var/lib/evidence`: every test sets `EVIDENCE_STORE` to a temp dir; every writer honours it.
- **Never open a seat log, a transcript, a session file or a store body** (`~/factory/runs/*/*.log`, `*.dsh-home`, `~/.claude/projects`, `/var/lib/evidence/*.jsonl`). T2's driver tests use synthetic logs written by the test. The `.result` and `.review.md` files under `~/factory/runs/` are read only by the ingest code under test, from fixtures.
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null` a gated command. One commit per task; the subject is the section's byte-exact `commit subject`; the trailers are the WORKSPACE RULES' two lines.
- TDD: the failing check first, shown red with its output, then green. A load-bearing test counts only once it has been shown to fail; a test that cannot fail is a `vacuous-test` major finding. Every proxy names what it stands in for and its gap (`docs/decisions/2026-09-03-test-based-reality-amendments.md`).
- **The Python and shell blocks below are specifications, not byte-exact files.** After writing each block run `nix develop -c ruff format <paths>` (88 columns) and, for shell, `nix develop -c treefmt`; a reformatting-only difference is not a deviation. Python is stdlib only in `pkgs/`; tests may use pytest.
- **One writer per tree.** Work only in the isolated worktree the task was started in, on `task/<KEY>`; `touches` is a contract — a file outside it is a deviation to report, not to write. Two exceptions, never a deviation: `docs/MAP.md` (regenerate with `python3 pkgs/evidence/repomap.py --root . write` whenever a file is added or removed — `lint` checks it) and the board's queue block (regenerated by the pre-commit hook).
- **Every row enters the store through `evidence.append()` or `evidence.replace_stream()`**; both validate against `pkgs/evidence/streams.py` before taking the lock. No other code opens a store path for writing; the literal `/var/lib/evidence` lives only in `pkgs/evidence/evidence.py` (`DEFAULT_STORE`). A recording problem is logged and never fails the caller (a check verdict, a task, a hook stand); an ingest that takes a path binds it to a declared root and exits 2 outside it before any write.
- Bats: one `[ … ]` per line (an `&&` chain cannot fail); every driver script is invoked as `"$REAL_BASH" <script>` (the build sandbox has no `/usr/bin/env`); `FACTORY_ROOT` under `$BATS_TEST_TMPDIR`, never the real `~/factory` (the file's `teardown_file` proves it).
- Nix style: statix rejects `{ ... }:` headers (write `_:` or name the args); shell pasted into `flake.nix` strings and `githooks/pre-commit` is what shfmt/treefmt left it.
- No secrets in the repo: no fixture may contain a real key shape; the secret-shape tests use the prefixes with a three-character tail (`sk-or-v1-abc`), never a full token.
- The seat's final reply ends with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them; never copy the WORKSPACE RULES or the result block into a project file.

## Assumptions

1. The devShell's `python3` is 3.14.7 (`nix develop -c python3 --version`, 2026-09-06); the host pin's is ≥ 3.11 (`tomllib`). Python 3.14's `multiprocessing` default is `forkserver`, so concurrency tests spawn subprocesses.
2. `EVIDENCE_STORE` overrides the store root everywhere; `--store` still wins when given. After T1, the shell writers pass `--store` only when `EVIDENCE_STORE` is set (the CLI's own default is the same directory).
3. `/var/lib/evidence` exists on core (generation 45, `evidence bundle` reads it); `derived/` does not and is created 0750 by the first `replace_stream`. Nothing in this plan needs a switch to be tested; until the operator switches, the live collector keeps writing `helm-status` through its old unfenced path and the live `evidence` CLI lacks `ingest result`/`reviews` — the operator steps use the tree's CLI (`nix run .#evidence --`).
4. `factory-task` runs on the host as the wave's child, outside the seat unit, and reaches `pkgs/evidence/evidence.py` through `FACTORY_TOOLBOX_REPO` (`factory_py`), never the host's packaged `evidence`; `FACTORY_EVIDENCE_CMD` is the test seam, as for `factory_record_check`.
5. The Nix build sandbox has no `.git` (the lint check copies `${self}`), so the store-writer lint enumerates files with `find`, never `git ls-files`; it has no `nix develop`, so bats tests reach python through `FACTORY_PYTHON3_CMD` (as `82-factory-dispatch.bats` does) and the ingest through `FACTORY_EVIDENCE_CMD`.
6. `helm-vm` (a NixOS VM test) runs on core with KVM; it starts `helm-collect.service` for real (`machine.succeed("systemctl --user -M alice@ start helm-collect.service")`), so a broken `import evidence` in the collector turns it red — the build-time proof of T1W's wrapper change.
7. The 237 `.result` files under `~/factory/runs/*/` (`ls ~/factory/runs/*/*.result | wc -l`, 09:26) are read by the operator's loop through the ingest; 234 of them still have their workspace clone (`.git/config` present), so `repo` resolves for those and is null for 3.
8. The orchestrator guard treats `docs/reviews/*.md` as ordinary files (its protected families are typed plan headings and `docs/superpowers/plans`); T3M's 137-file diff names no plan path.
9. `tests/unit/91-orchestrator-guard.bats` reads the cr17/cr18 review files by parsing their markdown tables (`tables(path)` in the test), not by byte comparison; a block prepended above the H1 leaves every table row intact.

## Waves

Peel-off groups from the graph's own code over the draft attached to the live tree — P1's form, which the design names as the post-P1 replacement for the scratch copy (the scratch copy's `cp` of a draft into a `docs/superpowers/plans` path is refused by the orchestrator guard from a shell; a judge who wants it writes the file with the Write tool). Every draft rule passed (check names against `docs/MAP.md`, explicit `touches`, the four house sections, the byte-exact subjects against `acceptance`, sizes):

```
$ nix develop -c python3 pkgs/evidence/tasks.py --root . --runs-dir /nonexistent --store /nonexistent check --draft <scratch>/draft-0.md
waves: [[["T1"]], [["T1W"], ["T2"], ["T3"]], [["T10a"], ["T3M"]]]
conflicts: CR4 (2026-09-05-context-reset-ritual.md) × T1W (draft-0.md): githooks/pre-commit ~ githooks/pre-commit
conflicts: PW1pro (2026-09-05-plan-writing-comparison.md) × T3M (draft-0.md): docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-pro.md ~ docs/reviews
conflicts: PW1glm (2026-09-05-plan-writing-comparison.md) × T3M (draft-0.md): docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-glm.md ~ docs/reviews
conflicts: PW1kimi (2026-09-05-plan-writing-comparison.md) × T3M (draft-0.md): docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-kimi.md ~ docs/reviews
exit=0
```

| wave | tasks | dependsOn | notes |
|---|---|---|---|
| 1 | T1 | — | the library; alone because everything reads it |
| 2 | T1W ‖ T2 ‖ T3 | each: [T1] | three seats at once; `touches` disjoint (T1 removed the store literals from the files T2/T3 own) |
| 3 | T10a ‖ T3M | T10a: [T2, T3]; T3M: [T3] | T3M is a docs seat (Flash, off) running the migration script |

The cross-plan hits, sequenced: **T1W × CR4** on `githooks/pre-commit` (both append lines; CR4 is ready and unheld) — whichever lands second merges main into its branch first (recipe step 2) and the two additions coexist. **T3M × PW1glm/kimi/pro** is a directory-prefix overlap only: PW1* write under `docs/reviews/plan-comparison/` (the hits appear because `--runs-dir /nonexistent` hides their `ran` state; on the live graph they are `ran` and held by decision Q3), the migration edits only `docs/reviews/*opus-review*.md` — no file in common, no order to impose. The held SB5/SB6 and the other siblings share no path with this plan.

## Operator

Every command is pasted from a dry run or quoted from the runbook; nothing here is a sentence where a command would do. Steps 3–6 use the tree's CLI, not the live generation's.

1. **Launch wave 1** — §Dispatch's first line without `--dry-run`. Acceptance: `nix develop -c python3 pkgs/evidence/tasks.py --root . brief` shows `nixos-agent-env/T1` under **Running**.
2. **After T1W lands — the switch (optional, when convenient; A2).** Build and diff:
   ```
   nix build .#nixosConfigurations.core.config.system.build.toplevel
   nix store diff-closures /run/current-system ./result
   ```
   **Predicted delta** (a prediction, measured on the landed tree before the switch line ships): the `helm-collect` and `helm-status` wrappers change (one `PYTHONPATH=` line, the `pkgs/helm` file), the `evidence` CLI wrapper and its `pkgs/evidence` directory change (`streams.py`, `ingest_result.py`, `ingest_reviews.py`, `migrate_reviews.py`, the edited modules), `helm-flake-check` follows `evidence`; no unit is added or removed; `python3-minimal` and everything else unchanged. Then `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core` (the operator's command, never the seat's). Acceptance: `systemctl --user start helm-collect.service && systemctl --user status helm-collect.service | head -3` shows `inactive (dead)` with exit `SUCCESS`; `evidence bundle --markdown | sed -n '1,3p'` prints the new generation. Rollback: `sudo /nix/var/nix/profiles/system-45-link/bin/switch-to-configuration switch` (generation 45 = `a53d2e5`).
3. **After T2 lands — the loop over every existing result** (one command; the ingest accepts many paths):
   ```
   nix run .#evidence -- ingest result ~/factory/runs/*/*.result
   ```
   Expected: `ingested 237 rows into derived/tasks (0 refused)` (237 at 09:26; recount with `ls ~/factory/runs/*/*.result | wc -l`). Then `nix run .#evidence -- ingest result ~/factory/runs/*/*.result` again: the same line and `derived/tasks.jsonl` byte-identical (`sha256sum /var/lib/evidence/derived/tasks.jsonl` before and after). A count that proves the failed results classified without a log: `grep -c '"error_class":"none"' /var/lib/evidence/derived/tasks.jsonl` (the operator may read the store; the orchestrator may not) — expected 223 + 1 (`done` and `partial`) with the 13 others in `submit-failed|no-result-line|template-echo|boot-failure|timeout`.
4. **After T3 lands — dispatch T3M** (§Dispatch wave 3) or run its two commands by hand: `nix develop -c python3 pkgs/evidence/migrate_reviews.py .` then `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check` (expected `unchanged: 164; would change: 0`, exit 0) then `nix develop -c python3 pkgs/evidence/tasks.py --root . check` (prints nothing), then the docs commit with T3M's subject.
5. **After T3M lands — the gates ingest:**
   ```
   nix run .#evidence -- ingest reviews ~/nixos-agent-env ~/factory/runs
   ```
   Expected: `ingested 187 gate rows (docs/reviews: 164, H1 parsed 137, blocks 137, legacy 27; runs: 23)` — the automatic parse count the spec asks for (104 at the design's sample; 137 at 09:26; recount at landing).
6. **After T10a lands — the join line:** `nix run .#evidence -- bundle --markdown | grep '^## Join'` → `## Join: 237 task rows, 142 with a gate verdict, 0 with activity` (142 = results whose `(run, key)` has a matching review — 137 from a parseable H1, 5 more from the legacy-H1 files' name-derived keys, at 09:26; recount at landing).
7. **Rollback per task:** `git -C ~/nixos-agent-env revert <the task's commit>` through the devShell; the derived streams are rebuilt by re-running steps 3 and 5 (a re-ingest replaces by key); a bad row is fixed the same way.
8. **Before wave 2 (three seats at once, A3/A9):** the OpenRouter balance is the operator's item — one look at the account page; the spend since the 2026-09-05 22:20 top-up is unmeasured in the tree (no activity-export rows), declared as such.

## Dispatch

Runs: `tel1` (wave 1), `tel2` (wave 2), `tel3` (wave 3); none exists under `~/factory/runs` (`ls ~/factory/runs | grep -c '^tel'` → 0). Plan path after the Ship phase: `docs/superpowers/plans/2026-09-06-telemetry-store-1.md`.

Dry run over the draft (not yet under the plans directory, so the dispatcher's graph query is supplied through its own `FACTORY_WAVES_CMD` seam by a five-line script that calls `tasks.scan_repo`, `tasks.load_draft` and `tasks.wave_lines` — the graph's own functions, no logic re-derived — and prints the draft's next wave exactly as `waves --next` would):

```
$ FACTORY_WAVES_CMD=<scratch>/waves-next.sh tools/factory/seat/factory-dispatch tel1 . <scratch>/draft-0.md --dry-run
would run: factory-wave tel1 /home/dalhaka/nixos-agent-env "T1"
exit=0
```

(`<scratch>/waves-next.sh` printed `"T1"`; nothing was written under `~/factory/runs` — a dry run touches nothing.)

Per wave, the command to run (after the plan file exists on main):

```
tools/factory/seat/factory-dispatch tel1 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-telemetry-store-1.md --dry-run
tools/factory/seat/factory-dispatch tel1 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-telemetry-store-1.md
tools/factory/seat/factory-dispatch tel2 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-telemetry-store-1.md      # after T1 landed; prints "T1W" "T2" "T3"
tools/factory/seat/factory-dispatch tel3 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-telemetry-store-1.md      # after T2 and T3 landed; prints "T10a" "T3M"
```

**Landing recipe, per key (A1), in order:**

1. Keep only the one commit the section names: `git -C ~/factory/ws/<run>/<KEY> log --format='%h %s' <base>..task/<KEY>` (base from `~/factory/ws/<run>/<KEY>/.factory-meta`); if more than one line, `git -C ~/factory/ws/<run>/<KEY> reset --hard <that sha>` (three seats appended a fabricated board commit on 2026-09-05).
2. If main moved under a file the task touches (or under `docs/MAP.md`): `git -C ~/factory/ws/<run>/<KEY> fetch ~/nixos-agent-env main && git -C ~/factory/ws/<run>/<KEY> merge --no-edit FETCH_HEAD`, then `python3 pkgs/evidence/repomap.py --root . write` in the workspace and a merge commit `merge: main into task/<KEY> (board block and MAP regenerated) (test: lint)`.
3. Commit the gate review (`docs: gate review — <run> <KEY> …`), with the P3A front-matter block (and, after T3 lands, `reviewer`, `majors`, `minors`).
4. `tools/factory/seat/factory-integrate <run> ~/nixos-agent-env <KEY> && git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>` — gated on both exit codes; never pull after a `CHECK … fail` line.
5. Dispatch what it unblocks (A7): T1 → `tel2` (T1W, T2, T3); T2 and T3 → `tel3` (T10a, T3M); T1W → nothing (T2/T3 do not depend on it).

**Relaunch after a seat death (A6):** the dead seat's diff stays in `~/factory/ws/<run>/<KEY>`; relaunch the one key as `FACTORY_PLAN=docs/superpowers/plans/2026-09-06-telemetry-store-1.md setsid -f bash -c 'exec tools/factory/seat/factory-wave <run>b ~/nixos-agent-env "<KEY>" >> ~/factory/runs/<run>b.wave.log 2>&1' </dev/null` (or the `launch.sh` shape the runbook's sweep fixture allows), after the `error_class` of the dead result is read: `budget-402` waits for the top-up, `provider-error` relaunches at once, `unknown-model`/`template-echo`/`no-result-line` never relaunch blind.

## Anticipation

| row | applies? | artefact |
|---|---|---|
| A1 dispatch | yes | §Dispatch: run names, the dry-run line, the five-step landing recipe |
| A2 switch | yes (T1W touches `nixosModules/helm.nix`; `pkgs/helm` and `pkgs/evidence` are embedded in the closure) | Operator step 2: the two build commands, the delta as a prediction, the rollback generation |
| A3 credentials, names, top-ups | top-up check only | Operator step 8 (three seats in wave 2) |
| A4 mutation tables | yes | every task's Tests table |
| A5 driver guards | the field packet shows the driver **has** them: `FACTORY_PLAN` unset → `factory_die 2 "FACTORY_PLAN is unset — name the plan …"` in both `factory-task` and `factory-wave`; a board rewrite outside the queue block → `REFUSED <KEY>: docs/OPERATIONS.md changed outside the queue block` in `factory-integrate`; a near-miss result block → `FACTORY-NOTES result-misparse: …` recorded as failed; a `done` with zero commits demoted (CR3r). No sentence stands in for a guard; T2 adds the next deterministic piece, `error_class` in the driver | `dependsOn` P11 is not needed (P11r landed 04:51: "the driver line is closed") |
| A6 seat death | yes | the relaunch line under §Dispatch, keyed on `error_class` once T2 lands |
| A7 what a landing unblocks | yes | recipe step 5 |
| A8 claims | none flips in a diff here; T1 makes `factory-run-report-persisted` recordable (shape A validates) and T2's loop makes `reasoning-tokens-not-itemised` checkable (`usage.reasoning` per row) | the flips are the orchestrator's after the runs, with `check:evidence-unit@<rev>`/`operator:<date>` evidence |
| A9 hold? | no: `lint`, `evidence-unit`, `host-core` green at HEAD (bundle M6); no switch on the critical path; SB5/SB6 held but disjoint; spend unmeasured (declared) | — |
| A10 questions | yes | two, with recommendation and default |
| A11 handoff line | prepared: "telemetry-1: on the seat: tel1 T1; in gate: —; next: tel2 (T1W T2 T3) after T1 lands; plan docs/superpowers/plans/2026-09-06-telemetry-store-1.md, judgement docs/reviews/plan-judgements/2026-09-06-telemetry-1.md" | for the board's START HERE |
| A12 re-plan | not a re-plan | — |
| A13 hooks / second consumers | yes: T1W edits `githooks/pre-commit` (a hook) and adds a lint script two consumers run — the hook (the devShell's tools, the tree under commit, `$PWD`) and `checks.lint` (the sandbox copy of `${self}`, the same script); on a missing tool the script exits 2 and the gate fails closed (a lint gate, not a Stop hook: failing closed is right); no `stop_hook_active` field applies | T1W Interfaces |
| A14 deny rules | none added: the store-writer lint refuses commits, not commands; no recipe command in `docs/runbooks/session.md`'s sweep list contains `O_APPEND`, `open(…, "a")` or the literal | — |

## Not in this plan

T4–T9 and T10b–T18 of the parent design (the activity export, host metrics, the migration proper — `ingest runs`, `rebuild --derived` —, incidents, rollups and the rollup timer, access modes, the reports, the Helm tiles, denials, sessions, the relaunch table, shape-B writers, the audit and quarantine — mutation (j) —, `checks` v2 with `log_tail` hashing); the seat-driver ladder and `report ladder`; `report.py` calling `n_gate` (T10b); `record_metrics` (T5; mutation (h) is tested here as the tile status object handed to `append`); the `incidents`, `host-metrics`, `broker-lane`, `guard-denials`, `sessions` kinds (declared by their own tasks); `lane-jobs` derived from `ledger.jsonl`; a tmpfiles rule for `derived/`; a `plan` routing row; any change to what a review says. Parked in the concept file: `factory-wave` writing the shape-B start/end rows (T16, XS once T1 lands).

---

## Tasks

### T1 (code, M) — the fence: streams.py, validate before the lock, replace_stream, the delegation, the ingest table

**dependsOn:** none

**Files:**
- Create: `pkgs/evidence/streams.py`, `tests/evidence/test_streams_policy.py`
- Modify: `pkgs/evidence/evidence.py` (`STREAM_RE` subdirs, `append` validates, `replace_stream`, `record`/`record-check` exit 2 on refusal, the `ingest` table), `pkgs/evidence/judgements.py` (`FIELDS` from `streams`, `validate_judgement` delegates), `pkgs/evidence/tasks.py`, `pkgs/evidence/report.py` (the `--store` default literal → `evidence.DEFAULT_STORE`), `pkgs/evidence/SCHEMA.md` (the rule, the two derived streams, the subdirectories), `tests/evidence/test_evidence.py` (three fixtures use declared kinds), `tools/factory/seat/factory-lib.sh` (`factory_record_check` passes `--store` only when `EVIDENCE_STORE` is set), `flake.nix` (`factory-unit` copies `streams.py` beside `judgements.py`)

**Interfaces:**

- `pkgs/evidence/streams.py` — stdlib only, imports nothing from the sibling modules (evidence.py imports it; judgements.py imports it).
  - Classes (strings and tuples): `"id"` `^[A-Za-z0-9._:+-]{1,120}$`; `"model-id"` `^[a-z0-9][a-z0-9._-]{0,63}(/[a-z0-9][a-z0-9._-]{0,63})?$`; `"key"` `^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$`; `"rev"` `^[0-9a-f]{40}$`; `"ts"` `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$`; `"hash"` `^[0-9a-f]{64}$`; `"int"` (a Python `int`, not `bool`), `("int", lo, hi)`; `"num"` (`int` or `float`, not `bool`); `"bool"`; `("enum", (words…))`; `("path", (roots…), cap)` — a root ending in `/`: a root beginning `~/` or `/` is `os.path.expanduser`-ed and the value's `os.path.realpath` must start with it; a relative root (`docs/reviews/`) or the empty root `""` (repo-relative, `factory-finding.file`) requires the value to start with it, contain no `..` segment, no leading `/`; every path value: no `\n`, length ≤ cap; `("text", cap)` — the one free-text class, declared only for `check.log_tail` (v1) and test kinds; `("re", pattern)` (D5); `("null", cls)` — `None` or `cls`; `("obj", {field: cls})`; `("list", elem, cap)`; `("map", key_cls, cap, value_cls)` where `key_cls` is `("enum", …)` or `("re", …)`.
  - `FORBIDDEN`: the design §3.5 list verbatim (`prompt … slug`), compared by `name.lower().replace("-", "_")` exact match, over every object key at every depth — declared fields, `obj` fields and map keys — except a map whose key class is a closed enum (its keys are declared words, e.g. the `host` tile) and except a declared field of class `path` (the declared exception: `factory-finding.file`). `SECRET_RE` = one alternation of `sk-or-v1-`, `sk-ant-`, `Bearer `, `-----BEGIN`, `AKIA[0-9A-Z]{16}`, `ghp_`, `xox[bp]-`, `AGE-SECRET-KEY-`, `\bage1`, `\beyJ`, searched in every string value and every map key at every depth.
  - `ENVELOPE = ("v", "ts", "kind")` — never validated as fields (the writer adds `v`, `ts`; `kind` selects the entry). `MAX_BYTES = 16384`, `MAX_DEPTH = 8`.
  - `KINDS[kind] = {"stream": "<name>", "v": int, "key": (fields…) | None, "fields": {...}}`; `factory-run` carries `"shapes": {"A": {...}, "B": {...}}` chosen by `driver`: absent → A, `"seat"` → B, anything else → `driver: not in enum (seat)`.
  - `validate(kind, row) -> list[str]` — every reason, never raises, exact strings: `undeclared kind {kind!r}`; `{path}: undeclared field`; `{path}: forbidden name`; `{path}: not in enum ({a}|{b}…)`; `{path}: not a {class}` (`id`, `model-id`, `key`, `rev`, `ts`, `hash`, `int`, `num`, `bool`, `object`, `list`, `map`, `string`); `{path}: over cap {n}`; `{path}: outside root {root}`; `{path}: '..' segment`; `{path}: newline`; `{path}: secret shape {matched}`; `{path}: null not allowed`; `row over 16384 bytes ({n})`; `depth over 8 at {path}`. `{path}` is dotted from the row root (`usage.out`, `tiles.host`, `tasks[3].commit`). A subtree under an undeclared field is not descended (so a 1,000-deep payload under an unknown key reports one `undeclared field` and no `RecursionError`; a 1,000-deep payload under a declared `obj` reports `depth over 8`).
  - `stream_of(kind, row) -> str` — the declared stream; `key_of(kind, row) -> tuple`.
  - `class StreamRefused(ValueError)` with `.errors: list[str]`, `str()` = `"; ".join(errors)`.
- `pkgs/evidence/evidence.py`
  - `STREAM_RE = ^(?:(?:derived|ledger)/)?[a-z][a-z0-9-]{0,31}$` (a closed set of two subdirectories; `stream_path` unchanged otherwise; `../etc`, `Checks`, `other/x` refused with `ValueError` as today).
  - `append(store, stream, row, ts=None)`: `stream_path` first (ValueError on a bad name), then `errors = streams.validate(row.get("kind"), row)`, plus `kind {k} does not write stream {s}` when `streams.stream_of` ≠ `stream`; any error → `raise streams.StreamRefused(errors)` before the lock, nothing written; otherwise as today (envelope `v` from `streams.KINDS[kind]["v"]`, `ts`, flock, fsync).
  - `replace_stream(store, stream, rows) -> int`: every row validated first (all-or-nothing; `StreamRefused` lists every reason of every row prefixed `row {i}: `); the kind must declare a `key` (else `StreamRefused(["kind {k}: no key; use append"])`); under the same `flock` on the stream file: read the existing parseable rows (torn lines dropped — a rewrite), replace by key in place (an incoming row equal to the existing one ignoring `v`/`ts` keeps the existing `ts`; a changed row gets `ts=now`; a new key appends), write `<path>.tmp` in the same directory (0640, fsync), `os.replace` over the stream, directory fsync; the parent (`derived/`) is created 0750. Returns the number of rows in the file.
  - CLI: `record` and `record-check` catch `StreamRefused`, print each reason on stderr as `evidence: refused: {reason}`, return 2 with no file written. `ingest`: `INGEST_MODULES = {"judgements": "judgements", "result": "ingest_result", "reviews": "ingest_reviews"}`; `evidence [--store S] ingest <name> …` imports `INGEST_MODULES[name]` from the sibling directory and calls its `main(["--store", S] + rest)` (the `--store` global forwarded exactly as for `tasks`); an unknown name → stderr `evidence: ingest: unknown target {name} (judgements|result|reviews)`, exit 2; a known name whose module is absent → `evidence: ingest {name}: not available in this tree`, exit 2.
  - `DEFAULT_STORE` stays the one literal; `tasks.py`, `judgements.py`, `report.py` take `os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE` (a lazy `import evidence` inside `main`, next to the existing sibling imports).
- `pkgs/evidence/judgements.py`: `FIELDS = streams.judgement_fields()` (the 14 names in the entry's order; the literal tuple is deleted); `ROW_KEYS = set(FIELDS) | {"kind", "judged_ts", "judgement_path"}` unchanged in meaning; `validate_judgement(fields)` runs today's checks first and, only when they produced no error, extends the list with `streams.validate("plan-judgement", typed)` where `typed = {"kind": "plan-judgement", **_row_fields(fields)}` plus `judged_ts`/`judgement_path` when present and not `None`. Every existing message stays byte-identical; `evidence.append(` stays the one writer call after the row-level validate.
- `tools/factory/seat/factory-lib.sh` `factory_record_check`: the two `--store "$store"` become `${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"}` and the `local store=` line goes (the bats assertion `--store $BATS_TEST_TMPDIR/ev record-check …` still holds because the tests export `EVIDENCE_STORE`).
- The declared kinds (streams.py is the contract; SCHEMA.md quotes this table):

```python
CLASSES_CHECK = ("unit", "eval", "vm", "nix-check", "curl", "browser", "operator", "unmeasured")
TILES = ("backup-parity", "backup-snapshot", "basket-doctor", "broker", "drift", "flake-check", "gpu", "host", "timers")
ERROR_CLASSES = ("budget-402", "provider-error", "unknown-model", "boot-failure", "no-result-line",
                 "template-echo", "timeout", "submit-failed", "killed", "none")
PLAN_DEFECTS = ("none", "vacuous", "missing-case", "underspecified", "wrong-fact", "implementer", "process")
REF = ("re", r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$")     # a git ref; no '..' by the path rule below
PLAN = ("path", ("docs/superpowers/plans/",), 120)
KINDS = {
  "check": {"stream": "checks", "v": 1, "key": None, "fields": {
      "name": "id", "rev": "rev", "ok": "bool", "class": ("enum", CLASSES_CHECK), "src": "id",
      "duration_s": "int", "log_tail": ("text", 4000)}},
  "helm-status": {"stream": "helm-status", "v": 1, "key": None, "fields": {
      "tiles": ("map", ("enum", TILES), 16, ("enum", ("ok", "warn", "fail", "unknown"))),
      "reason": ("enum", ("change", "heartbeat"))}},
  "factory-run": {"stream": "runs", "v": 1, "key": None, "shapes": {
      "A": {"run_id": ("null", "id"), "plan": PLAN, "prefix": "id", "baseline": "rev",
            "integration_branch": REF,
            "tasks": ("list", ("obj", {"key": "key", "status": "id", "commit": ("null", "rev"), "fixRounds": "int"}), 64),
            "verify": ("enum", ("pass", "fail", "skipped", "none")), "delivered": "int", "agents": "int", "output_tokens": "int"},
      "B": {"run_id": "id", "driver": ("enum", ("seat",)), "event": ("enum", ("start", "end")), "repo": "id",
            "plan": ("null", PLAN), "base": ("null", "rev"), "groups": ("list", ("list", "key", 32), 32),
            "pid": ("null", "int"), "status": ("enum", ("done", "partial", "failed", "killed", "unknown")),
            "tasks": ("list", ("obj", {"key": "key", "status": ("enum", ("done", "partial", "failed", "skipped", "unknown")),
                                        "commit": ("null", "rev"), "fix_rounds": "int"}), 64)}}},
  "plan-judgement": {"stream": "plans", "v": 1, "key": ("plan", "revision"), "fields": {
      "plan": ("path", ("docs/",), 190), "spec": ("path", ("docs/",), 190),
      "author": ("re", r"^(fable|hand|dsh:[a-z0-9./-]{1,64})$"),
      "effort": ("enum", ("off", "low", "medium", "high", "xhigh", "max", "unknown")),
      "words": "int", "tasks": "int",
      "judges": ("list", ("enum", ("sonnet", "opus", "deepseek", "fable")), 3),
      "judges_dropped": ("list", ("enum", ("implementer", "reviewer", "whole")), 3),
      "scores": ("list", ("int", 0, 3), 14), "total": "int", "self_score": ("null", ("int", 0, 42)),
      "threshold": "int", "decision": ("enum", ("dispatch", "revise", "revise-exhausted", "panel-short")),
      "revision": "int", "judged_ts": "ts", "judgement_path": ("path", ("docs/reviews/plan-judgements/",), 200)}},
  "task-result": {"stream": "derived/tasks", "v": 1, "key": ("run_id", "key"), "fields": {
      "run_id": "id", "key": "key", "repo": ("null", "id"), "plan": ("null", PLAN),
      "kind": ("enum", ("code", "docs", "unknown")), "size": ("enum", ("XS", "S", "M", "L", "unknown")),
      "model": "model-id", "effort": ("enum", ("off", "low", "medium", "high", "xhigh", "unknown")),
      "route": ("re", r"^(explicit|unknown|implement/(code|docs)/(XS|S|M|L))$"),
      "status": ("enum", ("done", "partial", "failed", "skipped", "unknown")),
      "exit_code": ("null", "int"), "wall_s": ("null", "int"), "commits": "int", "commits_declared": ("null", "int"),
      "checks": ("map", ("re", r"^[a-z][a-z0-9-]{0,63}$"), 64, ("enum", ("pass", "fail", "not-run"))),
      "checks_parse": ("enum", ("ok", "refused", "missing")),
      "head": ("null", "rev"), "base": ("null", "rev"), "files_changed": "int", "insertions": "int", "deletions": "int",
      "usage": ("obj", {"in": "int", "out": "int", "cache_read": "int", "reasoning": "int", "events": "int",
                        "duration_s": ("null", "num")}),
      "error_class": ("enum", ERROR_CLASSES),
      "seat_unit": ("null", ("re", r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")),
      "result_path": ("path", ("~/factory/runs/",), 200), "result_mtime": "ts"}},
  "gate-verdict": {"stream": "derived/gates", "v": 1, "key": ("review_path",), "fields": {
      "run_id": "id", "key": "key", "chain_root": "key",
      "round_kind": ("enum", ("first", "fix", "replan", "unknown")), "round": "int",
      "reviewer": ("enum", ("opus", "sonnet", "deepseek", "fable", "unknown")), "route": ("enum", ("claude", "openrouter")),
      "model": ("null", "model-id"), "verdict": ("enum", ("approved", "rejected", "unknown", "none")),
      "majors": ("null", "int"), "minors": ("null", "int"), "mutants_total": ("null", "int"), "mutants_killed": ("null", "int"),
      "mutants_outside_named": ("null", "int"),
      "plan_defect": ("null", ("enum", PLAN_DEFECTS)), "plan_defect_secondary": ("null", ("enum", PLAN_DEFECTS)),
      "gate_tokens": ("null", "int"), "wall_s": ("null", "int"),
      "review_path": ("path", ("docs/reviews/", "~/factory/runs/"), 200), "review_sha256": "hash",
      "review_commit": ("null", "rev"), "review_commit_ts": ("null", "ts")}},
  "activity-day": {"stream": "ledger/activity-days", "v": 1, "key": ("date", "model"), "fields": {
      "date": ("re", r"^\d{4}-\d{2}-\d{2}$"), "model": "model-id", "requests": "int", "cost_usd": "num",
      "tokens_prompt": "int", "tokens_completion": "int", "tokens_reasoning": "int", "tokens_cached": "int",
      "cancelled": "int", "finish": ("obj", {"tool_calls": "int", "stop": "int", "length": "int", "other": "int"}),
      "generation_ms_mean": ("null", "num"), "providers": "int"}},
  # the five ledger files of tools/ledger/schema.md, each row gaining `kind` (T1W writes it); `src` stays
  "factory-run-usage": {"stream": "ledger/factory-runs", "v": 1, "key": ("run_id",), "fields": {
      "src": ("enum", ("factory",)), "run_id": "id", "started": ("null", "ts"), "ended": ("null", "ts"),
      "plan": ("null", PLAN), "prefix": ("null", "id"), "repo": ("null", "id"),
      "tasks": ("list", ("obj", {"key": "key", "status": ("null", "id"), "commit": ("null", "rev"), "fix_rounds": "int"}), 64),
      "agents": "int", "output_tokens": "int", "input_tokens": "int", "cache_read": "int", "cache_write": "int",
      "thinking": "int", "wall_s": "num"}},
  "factory-agent": {"stream": "ledger/factory-agents", "v": 1, "key": ("run_id", "agent_id"), "fields": {
      "src": ("enum", ("factory",)), "run_id": "id", "agent_id": "id", "label": ("null", "id"),
      "role_model": ("null", "model-id"), "model_id": ("null", "model-id"),
      "tokens": ("obj", {"in": "int", "out": "int", "cache_read": "int", "cache_write": "int", "thinking": "int"}),
      "wall_s": "num", "tool_uses": "int"}},
  "factory-finding": {"stream": "ledger/factory-findings", "v": 1, "key": ("run_id", "file", "title_sha256"), "fields": {
      "src": ("enum", ("factory",)), "run_id": "id", "task": ("null", "key"), "round": ("null", "int"),
      "label": ("null", "id"), "severity": "id", "file": ("path", ("",), 200), "title_sha256": "hash", "class": ("null", "id")}},
  "dsh-session": {"stream": "ledger/dsh-sessions", "v": 1, "key": ("session_id",), "fields": {
      "src": ("enum", ("dsh",)), "session_id": "id", "role": ("null", "id"), "model": ("null", "model-id"),
      "started": ("null", "int"), "turns": "int", "steps": "int", "tools": "int",
      "in": "int", "out": "int", "cache_read": "int", "reasoning": "int", "wall_s": "num"}},
  "lane-job": {"stream": "ledger/lane-jobs", "v": 1, "key": ("lane", "job_id"), "fields": {
      "src": ("enum", ("lane",)), "lane": "id", "job_id": "id", "model": ("null", "model-id"),
      "provider": ("null", "id"), "ts": "num", "cost_usd": ("null", "num")}},
}
```

A missing declared field is not an error (the fence refuses what is present and undeclared; required-ness is the writer's). `judgement_fields()` returns the `plan-judgement` field names minus `judged_ts` and `judgement_path`, in order.

**Facts (2026-09-06, commands run from the repo):**

- `grep -hn 'STREAM_RE = \|^def append\|^def read\|rest\[0\] == "ingest"' pkgs/evidence/evidence.py` → `STREAM_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")`, `def append(store: str, stream: str, row: dict, ts: str | None = None) -> dict:` (the envelope is `{**row, "v": VERSION, "ts": …}`, written after the row), `def read(store: str, stream: str) -> list[dict]:`, `if rest and rest[0] == "ingest":` (forwards `rest[1:]` to `judgements.main` with the `--store` global).
- `grep -n 'FIELDS = (\|ROW_KEYS = \|def validate_judgement\|evidence.append(' pkgs/evidence/judgements.py` → the 14-name literal tuple `FIELDS = (`, `ROW_KEYS = set(FIELDS) | {"kind", "judged_ts", "judgement_path"}`, `def validate_judgement(fields):`, exactly one `evidence.append(` (the test `test_append_is_only_after_the_row_level_validate` counts it).
- Existing rows that the allowlist must keep accepting or that use undeclared kinds — `grep -n '"kind"' tests/evidence/test_evidence.py`: `{"kind": "factory-run", "n": 1}` (append-order test), `'kind': 't', 'i': i, 'j': j, 'pad': 'x' * 2000` (the subprocess concurrency program), `{"kind": "factory-run", "plan": "p"}` (`test_cli_record_requires_kind`), `{"kind": "check", "v": 99, "ts": …}` (`test_envelope_wins_over_row_v_and_ts`: `v`/`ts` in a row are envelope keys, not fields), `{"kind": "helm-status", "tiles": {"drift": status}, "reason": "change"}`.
- The tile names, from `evidence bundle --markdown` (packet M6): `backup-parity backup-snapshot basket-doctor broker drift flake-check gpu host timers` — `host` is on the forbidden list, hence the enum-keyed-map rule.
- `grep -n '"input"\|"output"\|"cacheRead"\|"reasoning"\|"events"\|"duration_s"' tools/factory/seat/factory-usage.py` → the usage line's keys are `model, events, input, output, cacheRead, reasoning, duration_s` — `output` is forbidden, hence D4.
- `grep -n 'integration_branch\|INT_BRANCH =' tools/factory/dark-factory.js` → `const INT_BRANCH = A.integrationBranch || \`factory/${A.prefix}-integration\`` and the recorder's literal `integration_branch: INT_BRANCH` (a ref with one slash); `plan: A.plan` (repo-relative `docs/superpowers/plans/…`); `commit: r.commit || null`; `fixRounds: r.fixRounds`.
- `grep -n 'judgements.py\|evidence.py' flake.nix | grep 'cp '` → `factory-unit` copies `pkgs/evidence/judgements.py` and `pkgs/evidence/evidence.py` by name (no glob) — `streams.py` must join them or `judgements --fields` fails there.
- The store literal outside `evidence.py` under `pkgs/evidence` — `grep -n '/var/lib/evidence' pkgs/evidence/*.py | grep -v evidence.py` → `tasks.py: "--store", default=os.environ.get("EVIDENCE_STORE", "/var/lib/evidence")`, the same line in `judgements.py` and `report.py`; and `grep -n 'var/lib/evidence' tools/factory/seat/factory-lib.sh` → `local store=${EVIDENCE_STORE:-/var/lib/evidence}`.
- The forbidden list, design §3.5 fence 2, verbatim: `prompt, prompts, completion, response, content, text, message, messages, body, transcript, reasoning_text, stdout, stderr, log, output, brief, diff, patch, note, notes, title, summary, snippet, excerpt, path, file, file_path, log_path, cwd, host, hostname, host_header, sni, url, query, client, ip, addr, peer, top_denied, subject, command, cmd, argv, args, env, basket, recipient, user, api_key, key_name, token, secret, password, email, slug`.

- [ ] **Step 1: Write the failing tests** — `tests/evidence/test_streams_policy.py` (load `streams`, `evidence`, `judgements` from `pkgs/evidence` the way `test_evidence.py`'s `load()` does; `EVIDENCE_STORE` is never set to the host path). A fixture kind for the tests that need one, declared in the test and restored after:

```python
@pytest.fixture
def t_kind(monkeypatch):
    monkeypatch.setitem(streams.KINDS, "t", {"stream": "runs", "v": 1, "key": ("i", "j"),
        "fields": {"i": "int", "j": "int", "pad": ("text", 20000), "deep": ("obj", {"a": ("obj", {"b": "int"})})}})
```

The table below is the test list; each row is one test function (name it after the row), one assertion, one mutant, one discriminating fixture.

| # | assertion (fixture → expected) | the one-line mutant that turns it red |
|---|---|---|
| 1 | `validate("check", {"kind":"check","name":"lint","rev":REV_A,"ok":True,"class":"unit","src":"x","duration_s":3,"log_tail":"t"})` → `[]`; and one valid row per kind and shape (A, B) from the Interfaces table, parametrised | remove any one field from the entry → its valid row reports `undeclared field` |
| 2 | one invalid row per kind: `check` with `class: "guess"` → `['class: not in enum (unit|eval|vm|nix-check|curl|browser|operator|unmeasured)']`; `task-result` with `status: "pass"` (the one stray in the corpus) → `status: not in enum (…)`; `gate-verdict` with `verdict: "rework"` → refused; `factory-run` with `driver: "dark-factory"` → `driver: not in enum (seat)` | `words` check → `if value not in words or True` |
| 3 | `validate("nope", {"kind":"nope"})` → `["undeclared kind 'nope'"]` | return `[]` for an unknown kind |
| 4 | the declared-field walk: every field name of every kind, shape, `obj` and enum-keyed map, run through the name fence, is either not forbidden or path-classed — asserts the walk visits `factory-finding.file` (path) and would refuse it were it `id` (call the fence directly on `("file", "id")` → forbidden; on `("file", ("path", ("",), 200))` → allowed) | drop the path exemption → `file` refuses → the test fails; add `output` to any entry → the walk fails |
| 5 | (a) `{"kind":"check","name":"lint","prompt":"x"}` → both `prompt: undeclared field` and `prompt: forbidden name` | drop either reason |
| 6 | (e) with `monkeypatch.setattr(streams, "FORBIDDEN", frozenset())` row 5 still fails (`undeclared field`); with `monkeypatch.setitem(KINDS["check"]["fields"], "prompt", "id")` it still fails (`forbidden name`) | remove the allowlist check / remove the name fence |
| 7 | name fence at depth and on map keys: `task-result` with `usage: {"output": 1}` → `usage.output: forbidden name` (and undeclared); `helm-status` with `tiles: {"host": "ok"}` → `[]` (enum-keyed map keys are exempt) | drop the enum-key exemption → `tiles.host: forbidden name` → the fixture fails; drop the depth walk → `usage.output` passes |
| 8 | (b)(i) a 120-char id-legal string in `check.src` → ok; 121 chars → `src: not a id`; `"two words"` → `not a id`; `/home/x/baskets/a.md` → `not a id`; `a@b.c` → `not a id` | relax the id regex to admit `/` or `@` |
| 9 | (c) `sk-or-v1-abc` in `check.src` → `src: secret shape sk-or-v1-`; `skor-v1-abc` → `[]`; `age1qxyz` → refused; `stage1qxyz` → ok; `eyJabc` → refused; `keyJabc` → ok; a map key `"ghp_x"` in `task-result.checks` → refused by the secret scan even though it matches the key pattern | drop the scan / drop the `\b` |
| 10 | (d) `check` with `log_tail` of 4000 chars → ok; 4001 → `log_tail: over cap 4000`; removing the `log_tail` entry from `KINDS["check"]` (monkeypatch) makes the 4000-char row fail with `undeclared field` (the allowlist is load-bearing) | — (the monkeypatch is the mutant; the assertion pins that it bites) |
| 11 | row cap: `t` row with `pad` of 16,300 chars → ok; 16,400 → `row over 16384 bytes (…)` | `>` → `>=` at the boundary (use a row whose serialised size is exactly 16384: pinned by computing `len(json.dumps(full))` in the test) |
| 12 | depth: `t` row with `deep` nested 1,000 dicts → refused with `depth over 8 at deep.a…` and no exception; a 1,000-deep dict under an undeclared key → exactly one `… undeclared field` | remove `MAX_DEPTH` → `RecursionError` |
| 13 | enum arms: every arm of `task-result.status`, `error_class`, `effort`, `gate-verdict.verdict`, `round_kind`, `reviewer` accepted (parametrised), each arm's misspelling with one letter changed refused | delete an arm from the tuple |
| 14 | map cap and key pattern: `task-result.checks` with 64 entries → ok; 65 → `checks: over cap 64`; key `Unit` → `checks.Unit: not a re`; value `ok` → `checks.unit: not in enum (pass|fail|not-run)` | `>` → `>=`; drop the key check |
| 15 | path class: `task-result.plan` `docs/superpowers/plans/x.md` → ok; `docs/superpowers/plans/../x.md` → `plan: '..' segment`; `/etc/passwd` → `outside root`; `result_path` under `$HOME/factory/runs/r/K.result` (the test sets `HOME` to `tmp_path`) → ok, `/tmp/x` → `outside root`; a value with `\n` → `newline`; 201 chars → `over cap 200` | drop any one of the four rules |
| 16 | null: `task-result.exit_code: None` → ok; `task-result.model: None` → `model: null not allowed` | make every class nullable |
| 17 | `append` refuses before writing: `append(store, "checks", {"kind":"check","name":"lint","prompt":"x"})` raises `StreamRefused` and `checks.jsonl` does not exist; `append(store, "runs", {"kind":"check","name":"lint"})` raises with `kind check does not write stream runs` | validate after the write / drop the stream binding |
| 18 | `append` still writes a valid row with `v` from the kind and the envelope after the row (`test_envelope_wins_over_row_v_and_ts` stays green) | — (regression pin) |
| 19 | `STREAM_RE`: `stream_path(s, "derived/tasks")` → `<s>/derived/tasks.jsonl`; `ledger/factory-runs` ok; `other/tasks`, `derived/../x`, `derived/Tasks` → `ValueError` | widen the subdirectory set |
| 20 | `replace_stream` keyed: write `t` rows `(1,1,"a")`, `(1,2,"b")`; replace with `(1,2,"B")`, `(2,1,"c")` → file order `(1,1,"a") (1,2,"B") (2,1,"c")`, 3 rows; the `(1,1)` row keeps its original `ts` byte-for-byte | replace by position; restamp every `ts` |
| 21 | `replace_stream` idempotent: the same rows twice → the file bytes are identical after the second call | restamp `ts` on an equal row |
| 22 | `replace_stream` all-or-nothing: rows `[valid, {"kind":"t","i":1,"j":1,"prompt":"x"}]` → `StreamRefused` whose message starts `row 1: prompt: forbidden name`; the file is untouched (compare bytes) | validate row by row while writing |
| 23 | `replace_stream` atomic: `monkeypatch.setattr(os, "replace", raising OSError)` → the old file's bytes are intact and `<path>.tmp` is removed or ignored by `read` | write in place with `open(path, "w")` |
| 24 | `replace_stream` drops a torn line (pre-existing torn line + one valid row → after replace, 1 row + the new rows; the torn text is gone) and creates `derived/` 0750 (`stat.S_IMODE`) | keep torn bytes; `mkdir` without the mode |
| 25 | `replace_stream` on a kind without a key (`check`) → `StreamRefused(["kind check: no key; use append"])` | default the key to `()` |
| 26 | CLI `record checks --json '{"kind":"check","name":"lint","prompt":"x"}'` → exit 2, stderr contains `evidence: refused: prompt: forbidden name`, no `checks.jsonl`; `record runs --json '{"kind":"factory-run","prefix":"p"}'` → exit 0 and the printed row has `"prefix": "p"` | catch nothing → a traceback and exit 1 (the test asserts exactly 2) |
| 27 | CLI `record-check --name lint --rev <40 hex> --ok --class unit --src 'sk-or-v1-abc'` → exit 2 with `secret shape`; the existing `record-check` tests stay green | — |
| 28 | `ingest` table: `evidence ingest bogus x` → exit 2, stderr `unknown target bogus (judgements|result|reviews)`; with `monkeypatch.setitem(evidence.INGEST_MODULES, "zz", "ingest_zz")` (via `main([...])` in-process) `ingest zz` → exit 2 `not available in this tree`; `ingest judgements <repo>` still reaches `judgements.main` (a fake repo dir with no judgements → stdout `no judgements under …`, exit 0) | drop the table lookup |
| 29 | delegation: `judgements.FIELDS == streams.judgement_fields()`; the source of `judgements.py` no longer contains the line `    "judges_dropped",` (the literal is gone); `monkeypatch.setattr(streams, "validate", lambda k, r: ["boom"])` makes `validate_judgement(GOOD)` return `["boom"]` while `validate_judgement({**GOOD, "decision": "maybe"})` returns exactly today's one message (raw checks first, delegation only on a clean row) | keep a second literal; delegate before the raw checks |
| 30 | the shape-A literal: the row built exactly as `dark-factory.js`'s `report` object with representative values (`run_id: None`, `plan: "docs/superpowers/plans/2026-09-05-evidence-store.md"`, `prefix: "ev"`, `baseline: REV_A`, `integration_branch: "factory/ev-integration"`, `tasks: [{"key":"E1","status":"landed","commit":REV_B,"fixRounds":0}]`, `verify: "pass"`, `delivered: 1`, `agents: 3`, `output_tokens: 12}`) → `validate("factory-run", …) == []`; the same with `driver: "seat"` → refused (`prefix: undeclared field` under shape B) | drop shape A |
| 31 | (h) the collector's status object handed to `append("helm-status", {"kind":"helm-status", **status})` where `status = {"schema": 1, "generated_at": "…", "hostname": "core", "tiles": [{"name": "broker", "status": "ok", "detail": {"stderr": "x"}, "top_denied": ["h"]}]}` → refused with `hostname: forbidden name` and `tiles: not a map` among the reasons | — (a regression pin against T5's `record_metrics` mistake) |
| 32 | concurrency (the existing `test_concurrent_appends_keep_every_line_parseable`, rewritten): the subprocess program declares kind `t` itself (`import streams; streams.KINDS["t"] = {…}`) before appending; 8 × 50 rows all parse | — (the proxy stays declared as in the existing test's comment) |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence/test_streams_policy.py -q` → collection error `StopIteration` from the `load()` helper's `next(p for p in candidates if p.exists())` (no `pkgs/evidence/streams.py`). Then `nix develop -c pytest tests/evidence -q` → the three `test_evidence.py` fixtures named in Facts still pass (nothing validates yet): that is the red for rows 17 and 26 — paste both outputs into the commit body.

- [ ] **Step 3: Write `pkgs/evidence/streams.py`** — the constants and `KINDS` above; `validate` as a recursive walk `_check(cls, value, path, depth, errors)` over the class grammar; `_name_fence(key, exempt)`; `_scan_secret(value, path, errors)`; `stream_of`, `key_of`, `judgement_fields`, `StreamRefused`.

- [ ] **Step 4: Change `evidence.py`** — `STREAM_RE`, `append` (validate → `StreamRefused` → lock), `replace_stream`, the CLI's exit-2 path, `INGEST_MODULES` and the dispatcher, `VERSION` per stream from the kind. Then `judgements.py` (`FIELDS = streams.judgement_fields()`, the delegation), `tasks.py`/`report.py`/`judgements.py` `--store` defaults, `factory-lib.sh`'s `${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"}`, `flake.nix`'s `factory-unit` copy line for `streams.py`, `SCHEMA.md` (the rule paragraph: "every row is validated against `pkgs/evidence/streams.py` before the lock; streams may live under `derived/` or `ledger/`; `derived/tasks` (kind `task-result`, key `(run_id, key)`) and `derived/gates` (kind `gate-verdict`, key `review_path`) are declared here and written by `evidence ingest result` / `ingest reviews`"). Adjust the three `test_evidence.py` fixtures: the append-order test and the CLI `record runs` test use `{"kind": "factory-run", "prefix": "p"}` (asserting `["prefix"] == "p"`), the concurrency program declares `t`.

- [ ] **Step 5: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q` (every test green, including `test_judgements.py` unchanged); `git add` the new files; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `… factory-unit`; `… unit`; `nix develop -c githooks/pre-commit`.

- [ ] **Step 6: Commit** with the subject below and the two trailers.

**Tests:** the table in Step 1 (32 rows; one mutant per assertion; the discriminating fixtures: the corpus's `status=pass`, the `host` tile, `usage.output`, the 120/121 boundary, the exact-16,384-byte row, `sk-or-v1-abc` against `skor-v1-abc`, `age1` against `stage1`, the equal-row `ts` in `replace_stream`, shape A against shape B).

**touches:** pkgs/evidence/streams.py, tests/evidence/test_streams_policy.py, pkgs/evidence/evidence.py, pkgs/evidence/judgements.py, pkgs/evidence/tasks.py, pkgs/evidence/report.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_evidence.py, tools/factory/seat/factory-lib.sh, flake.nix
**acceptance:** evidence-unit, factory-unit, unit, lint
**commit subject:** `evidence: the fence — streams.py declares every kind, append validates before the lock, replace_stream rewrites by key, judgements delegate, the ingest table (test: evidence-unit, factory-unit, unit, lint)`

### T1W (code, S) — every writer through append: the collector and the ledger fenced, the store-writer lint gate, the collector's import path

**dependsOn:** T1

**Files:**
- Create: `tests/lint/store-writers.sh`, `tests/lint/fixtures/store/bad-append.py`, `tests/lint/fixtures/store/bad-open.py`, `tests/lint/fixtures/store/bad-literal.sh`, `tests/lint/fixtures/store/clean.py`
- Modify: `pkgs/helm/collect.py`, `tests/helm/test_collect.py`, `tools/ledger/factory.py`, `tools/ledger/schema.md`, `tests/ledger/test_factory.py`, `nixosModules/helm.nix`, `flake.nix` (`helmCollect`, `helm-unit`, `ledger-unit`, `lint`), `githooks/pre-commit`, `tools/factory/dark-factory.js`, `tests/factory/render.test.mjs`

**Interfaces:**

- `pkgs/helm/collect.py`: `import evidence` at module top (after the stdlib imports; the wrappers and the tests put `pkgs/evidence` on the path). `_append_status_row` and its `import fcntl` are deleted. `record_status(cfg, status, now)` builds `{"kind": "helm-status", "tiles": current, "reason": reason}` and returns `evidence.append(_store(cfg), "helm-status", row, ts=now.strftime("%Y-%m-%dT%H:%M:%SZ"))` (the returned row carries the same `reason`/`tiles`/`ts` the tests read). `_status_rows(cfg)` → `[r for r in evidence.read(_store(cfg), "helm-status") if r.get("kind") == "helm-status"]`. `_store(cfg) = cfg.get("evidence_dir") or evidence.DEFAULT_STORE`; the three `"/var/lib/evidence"` literals in `collect.py` go (`_store` is also what the `checks.jsonl` reader at `tile_flake_check`'s helper uses: `pathlib.Path(_store(cfg)) / "checks.jsonl"`). A recording problem never fails the collector: `record_status` wraps the `append` in `try/except (OSError, ValueError) as e: print(f"helm-collect: evidence: {e}", file=sys.stderr); return None` — `streams.StreamRefused` is a `ValueError`.
- `nixosModules/helm.nix` `helmCollect.text` and `flake.nix`'s duplicate `helmCollect.text` gain, before the `exec`, `export PYTHONPATH=${../pkgs/evidence}''${PYTHONPATH:+:$PYTHONPATH}` (in `flake.nix`: `${./pkgs/evidence}`); the two texts stay otherwise identical. `helm-unit` copies `${self}/pkgs/evidence` to `pkgs/evidence`; `ledger-unit` copies it to `pkgs/evidence` beside `ledger`.
- `tools/ledger/factory.py`: `import evidence` after a two-candidate `sys.path` insertion (`Path(__file__).resolve().parents[2] / "pkgs" / "evidence"` — the repo layout — then `parents[1] / "pkgs" / "evidence"` — the `ledger-unit` sandbox layout, where the file sits at `ledger/factory.py`); a failed import raises `ImportError("tools/ledger/factory.py needs pkgs/evidence on sys.path")`. `_write_jsonl` is deleted. `_merge_jsonl(path, records)` (the `key` argument goes; the key is the kind's): `store, stream = _stream_of(path)`; `evidence.replace_stream(str(store), stream, records)`. `_stream_of(path)`: `path.parent.name` must be `ledger` (else `SystemExit(2)` with `ledger dir must be named ledger: <path>`), `store = path.parent.parent`, `stream = f"ledger/{path.stem}"`. Every record the readers build gains `"kind"`: `factory-run-usage` (`extract_run`), `factory-agent` (`_read_agent`), `factory-finding` (`_read_findings`: `"title_sha256": hashlib.sha256(title.encode()).hexdigest()` replaces `"title"`), `dsh-session` (`_extract_dsh_session`, without `slug`), `lane-job` (`extract_lane`). (Corrected by the T1b gate, 2026-09-07: `lane-job`'s epoch field is declared **`ts_epoch`** (`num`) in `streams.py`, not `ts` — `ts` is the envelope's and no declared field may carry an envelope name; `extract_lane` writes `ts_epoch` where it wrote `ts`, and `tools/ledger/schema.md`'s `lane-jobs` example follows.) `_read_jsonl` stays for reading (rollup); the `--ledger-dir` defaults keep `DEFAULT_LEDGER = os.path.join(os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE, "ledger")`.
- `tools/ledger/schema.md`: every example row gains `"kind"`; `factory-findings.title` → `title_sha256` (64 hex of the finding's `issue`/`title` text; the dedup key is `(run_id, file, title_sha256)`); `dsh-sessions` loses `slug`; a paragraph: "every ledger file is written by `evidence.replace_stream` and validated against `pkgs/evidence/streams.py`".
- `tools/factory/dark-factory.js`: the two prompt strings drop `--store "\${EVIDENCE_STORE:-/var/lib/evidence}" ` (the CLI defaults to `$EVIDENCE_STORE`, then the same directory); `tests/factory/render.test.mjs`'s two regexes drop the same text.
- `tests/lint/store-writers.sh [--self-test]`: roots `pkgs/evidence pkgs/helm tools/ledger tools/factory tools/session-start.sh tools/ritual.sh`; files enumerated with `find <roots> -type f ! -name '*.md' ! -path '*/__pycache__/*'` (no git in the lint sandbox); `pkgs/evidence/evidence.py` excluded; three rules as `grep -nE` patterns: `O_APPEND`, `open\([^)]*['"]a[bt+]*['"]`, `/var/lib/evidence`; any hit → each printed as `store-writers: <file>:<line>: <pattern>` and exit 1; none → exit 0; `grep`/`find` missing → exit 2. `--self-test`: runs the rule over `tests/lint/fixtures/store/` and exits 0 only if `bad-append.py`, `bad-open.py`, `bad-literal.sh` each produce exactly one hit of their own pattern and `clean.py` none; otherwise exit 1 naming the fixture. Wired as two lines in `flake.nix`'s `lint` and in `githooks/pre-commit`, next to the `js-lint.sh` pair: `bash tests/lint/store-writers.sh --self-test` then `bash tests/lint/store-writers.sh` (two lines, never `&&`).
- The direct-open tests (mutation (f)): in `tests/helm/test_collect.py` a test wraps `os.open` and `builtins.open` with recorders (`monkeypatch`) that note every path under `cfg["evidence_dir"]` opened with a write flag/mode and the function name two frames up; after `collect.record_status(...)` the recorded openers are exactly `{"append"}` (from module `evidence`). In `tests/ledger/test_factory.py` the same wrapper around `factory.extract(WORKFLOW_FIXTURE, out)` records exactly `{"replace_stream"}` (`_write_atomic` counts as `replace_stream` when it is the helper's name — the assertion is on the set of `co_name` values in `{"append", "replace_stream", "_write_atomic"}` and that no frame belongs to `collect`/`factory`).

**Facts:**

- `bash -c 'grep -rnE "O_APPEND|open\([^)]*[\"'"'"']a[bt+]*[\"'"'"']|/var/lib/evidence" pkgs/evidence pkgs/helm tools/ledger tools/factory tools/session-start.sh tools/ritual.sh | grep -v "^pkgs/evidence/evidence.py" | grep -v "\.md:"'` (2026-09-06) → 13 hits: `pkgs/evidence/judgements.py … "--store", default=os.environ.get("EVIDENCE_STORE", "/var/lib/evidence")`, `pkgs/evidence/tasks.py … (same)`, `pkgs/evidence/report.py … (same)` (the three T1 removes), `pkgs/helm/collect.py: path = pathlib.Path(cfg.get("evidence_dir", "/var/lib/evidence")) / "checks.jsonl"`, `… fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)`, `… with os.fdopen(fd, "a") as fh:`, `… / "helm-status.jsonl"` (twice), `tools/factory/dark-factory.js: … --store "\${EVIDENCE_STORE:-/var/lib/evidence}" record-check …` and `… record runs --json`, `tools/ledger/factory.py` twice — the module docstring's ``(``/var/lib/evidence/ledger/``, overridable via ``EVIDENCE_STORE``)`` and `os.environ.get("EVIDENCE_STORE", "/var/lib/evidence"), "ledger"` (the lint reads docstrings too: the docstring is reworded to "the store's `ledger/` directory, `evidence.DEFAULT_STORE`") —, `tools/factory/seat/factory-lib.sh: local store=${EVIDENCE_STORE:-/var/lib/evidence}` (T1 removes). This is the red the lint script must reproduce on the tree before Step 3 (minus T1's four).
- `sed -n '/helmCollect = pkgs.writeShellApplication/,/^  };/p' nixosModules/helm.nix` → the wrapper's text is `export PATH="$PATH:/run/current-system/sw/bin"` then `exec python3 ${../pkgs/helm/collect.py} "$@"` — the lone file; `flake.nix` carries the same wrapper (`exec python3 ${./pkgs/helm/collect.py} "$@"`). The `evidenceCli` wrapper (`exec python3 ${../pkgs/evidence}/evidence.py "$@"`) is a different derivation, used by `helm-flake-check`.
- `grep -n 'cp -r \${self}/pkgs' flake.nix` → `helm-unit`, `evidence-unit` and `unit` copy `pkgs/helm` and `pkgs/evidence`.
- `sed -n '1169,1183p' flake.nix` → `ledger-unit` copies `tools/ledger` as `ledger` and `tests/ledger` as `tests-ledger` (`cp -r ${self}/tools/ledger ledger`, `cp -r ${self}/tests/ledger tests-ledger`).
- `grep -n 'evidence_dir' tests/helm/test_collect.py | head -2` → `base_cfg` sets `"evidence_dir": str(tmp_path / "evidence")`; the record tests read `tmp_path / "evidence" / "helm-status.jsonl"` directly and pin its mode `0o640`.
- `grep -n 'out = tmp_path' tests/ledger/test_factory.py | head -3` → every ledger test writes to `tmp_path / "ledger"` (the `ledger` name `_stream_of` requires); `grep -n '"title"' tests/ledger/test_factory.py` → `by_file_title = {(f["file"], f["title"]): f for f in findings}` and the idempotency-key test — both become `title_sha256` (`hashlib.sha256(b"X does Y").hexdigest()` in the test).
- `grep -n 'var/lib/evidence' tests/factory/render.test.mjs` → two regexes pin the prompt text `pkgs/evidence/evidence.py --store "${EVIDENCE_STORE:-/var/lib/evidence}" record-check …` and `… record runs --json`.
- `grep -n 'helm-collect' tests/integration/helm-vm.nix` → `machine.succeed("systemctl --user -M alice@ start helm-collect.service")` — the VM runs the collector through the module's wrapper.

- [ ] **Step 1: Write the failing tests** — (1) `tests/lint/store-writers.sh` with its fixtures (the `.py` fixtures ruff-formatted — treefmt's python formatter includes every `*.py` — and `bad-literal.sh` shellcheck-clean: the `find tests -name '*.sh'` sweep reaches it); run `bash tests/lint/store-writers.sh` on the tree → exit 1 listing the nine remaining hits (paste). (2) In `tests/helm/test_collect.py`: `test_record_status_writes_only_through_evidence_append` (the direct-open recorder) and `test_record_status_refusal_is_logged_not_raised` (monkeypatch `evidence.append` to raise `ValueError("x")` → `record_status` returns `None`, stderr carries `helm-collect: evidence: x`). (3) In `tests/ledger/test_factory.py`: `test_extract_writes_only_through_replace_stream`, `test_records_carry_kind_and_title_sha256` (every written row has `kind`; findings have `title_sha256` and no `title`; sessions have no `slug`), `test_ledger_dir_must_be_named_ledger` (`out = tmp_path / "x"` → `SystemExit(2)`), and the two `title` assertions rewritten to `title_sha256` (named replacements of `by_file_title` and the idempotency-key set).

- [ ] **Step 2: Run it red** — `bash tests/lint/store-writers.sh; echo exit=$?` → the hit list and `exit=1`; `bash tests/lint/store-writers.sh --self-test` → exit 0 (the fixtures are detected — this must be green before the tree is fixed, or the gate is vacuous). `nix develop -c pytest tests/helm -q` → `AttributeError`/`AssertionError` on the three new helm tests (paste the first line of each). `nix develop -c pytest tests/ledger -q` → `KeyError: 'kind'` and the `title_sha256` `KeyError` (paste).

- [ ] **Step 3: Make the change** — `collect.py`, `factory.py`, `schema.md`, `helm.nix` and the flake's `helmCollect`, the two sandbox copy lists, the two gate wirings, `dark-factory.js` and `render.test.mjs`. In `tests/helm/test_collect.py` add `sys.path.insert(0, <repo>/pkgs/evidence)` before the `spec_from_file_location("collect", SRC)` line (the `unit` sandbox layout is `pkgs/helm` + `pkgs/evidence`, same relative shape).

- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/helm tests/helm tools/ledger tests/ledger`; `nix develop -c treefmt`; `bash tests/lint/store-writers.sh` → exit 0; `nix develop -c pytest tests/helm tests/ledger -q`; `node tests/factory/render.test.mjs`; `git add` the new files; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.helm-unit -L --no-link`; `… ledger-unit`; `… factory-unit`; `… helm-vm` (minutes; the collector starts under the module's wrapper — the proof of the `PYTHONPATH` line); `nix develop -c githooks/pre-commit`.

- [ ] **Step 5: Commit.**

**Tests (mutants):**

| assertion | mutant |
|---|---|
| the lint script exits 1 on the tree before Step 3 and 0 after; `--self-test` exits 0 | drop the `find`'s `pkgs/helm` root → `--self-test` still passes but the tree-run misses collect.py: pinned by a fixture copy of the old `_append_status_row` in `bad-append.py` |
| `--self-test` fails when a fixture stops being detected: temporarily rename `bad-open.py`'s `"a"` to `"w"` → exit 1 naming it (asserted in the bats-free way: the script's own `--self-test` is the assertion; the commit body pastes the run with the fixture edited and restored) | make `--self-test` skip the per-fixture count |
| `record_status` opens the store only via `append` | write the row with `open(path, "a")` → the recorder sees `record_status` |
| `record_status` returns `None` and logs on a refusal | let the exception propagate |
| every ledger row has `kind`; findings `title_sha256`; sessions no `slug` | keep `title` |
| `_stream_of` refuses a non-`ledger` dir | derive the store as `path.parent` |
| `render.test.mjs`: the prompt sites no longer carry the literal | leave one `--store "…"` |
| `helm-vm` green with the wrapper change | drop the `PYTHONPATH` line → the unit fails to import `evidence` → the VM test fails |

**touches:** tests/lint/store-writers.sh, tests/lint/fixtures/store/bad-append.py, tests/lint/fixtures/store/bad-open.py, tests/lint/fixtures/store/bad-literal.sh, tests/lint/fixtures/store/clean.py, pkgs/helm/collect.py, tests/helm/test_collect.py, tools/ledger/factory.py, tools/ledger/schema.md, tests/ledger/test_factory.py, nixosModules/helm.nix, flake.nix, githooks/pre-commit, tools/factory/dark-factory.js, tests/factory/render.test.mjs
**acceptance:** helm-unit, ledger-unit, factory-unit, helm-vm, lint
**commit subject:** `evidence: every writer through append — the collector and the ledger fenced, the store-writer lint gate, the collector's import path (test: helm-unit, ledger-unit, factory-unit, helm-vm, lint)`

### T2 (code, S) — the tasks stream: ingest result rooted at ~/factory/runs, error_class in the driver, one line in factory-task

**dependsOn:** T1

**Files:**
- Create: `pkgs/evidence/ingest_result.py`, `tests/evidence/test_ingest_result.py`, `tests/evidence/fixtures/results/done.result`, `tests/evidence/fixtures/results/status-pass.result`, `tests/evidence/fixtures/results/hostile-checks.result`, `tests/evidence/fixtures/results/template-echo.result`, `tests/evidence/fixtures/results/timeout.result`, `tests/evidence/fixtures/results/submit-failed.result`, `tests/evidence/fixtures/results/no-result-line.result`, `tests/evidence/fixtures/results/classified.result`
- Modify: `tools/factory/seat/factory-lib.sh` (`factory_error_class`, `factory_ingest_result`), `tools/factory/seat/factory-task` (`error_class:` and `plan:` lines, the call after the result), `tests/unit/80-seat-driver.bats`

**Interfaces:**

- CLI `evidence [--store S] ingest result [--runs-root DIR] <path>...` (`ingest_result.main`, subparser `result`; `--runs-root` defaults to `~/factory/runs`, expanded; tests pass a temp root). Before any write, every path is `os.path.realpath`-ed and must start with `<root>/`; the first outside path → stderr `evidence: ingest result: <path> is outside <root>`, exit 2, nothing written. A file that does not parse (no `FACTORY-RESULT status=` line, or no `run:`/`key:` line) → stderr `evidence: ingest result: <path>: not a result file`, counted refused. A path that resolves inside the root but does not exist on disk → the same `not a result file` stderr line and counted refused (no unhandled `FileNotFoundError`). Rows are validated by `replace_stream` (a refused row → its reasons on stderr prefixed with the path, counted refused; the other rows still land). stdout: `ingested {n} rows into derived/tasks ({m} refused)`; exit 0 when `m == 0`, else 1. The log beside the result is never opened.
- Row producers (`kind: task-result`, stream `derived/tasks`, key `(run_id, key)`), each field from one line of the `.result` file as `factory-task` writes it:
  - `run_id` ← `run:`; `key` ← `key:`; `repo` ← `tasks._repo_from_workspace(<workspace: line>)` or `None` when the clone is gone; `plan` ← `plan:` line (absolute), mapped to `docs/superpowers/plans/<basename>` when the path contains `/docs/superpowers/plans/`, else `None`; absent line → `None`.
  - `route` ← `route:` if it matches the route pattern else `unknown`; `kind`/`size` ← the `implement/<kind>/<size>` parts, `unknown` otherwise (`implement/any/any` → both `unknown`); `model` ← `model:`; `effort` ← `effort:` when in the enum else `unknown`; absent → `unknown`. (Corrected by T1b, 2026-09-07: the declared field for the `<kind>` part is **`task_kind`**, not `kind` — `kind` is the envelope's and always `task-result`; the producer writes `task_kind` with the same `code|docs|unknown` arms.)
  - `status` ← the last `FACTORY-RESULT status=<word>` line's word when in `done|partial|failed|skipped`, else `unknown` (the corpus has one `pass`); `exit_code` ← `exit_code:` int or `None`; `wall_s` ← `wall_s:` int or `None`.
  - `commits` ← the number of lines between `commits (base..task/<key>):` and the next blank line that match `^[0-9a-f]{7,40} `; `commits_declared` ← the `FACTORY-COMMITS N` integer or `None`.
  - `checks`/`checks_parse` ← the `FACTORY-CHECKS` line: tokens split on whitespace; each must be `<name>=<verdict>` with `name` matching `^[a-z][a-z0-9-]{0,63}$` and `verdict` in `pass|fail|not-run`, at most 64 tokens; a token whose name is in `streams.FORBIDDEN` (after the same case-fold/hyphen-normalise the fence applies) is a violation like any other; any violation → `{}` and `refused`; no line → `{}` and `missing`; `FACTORY-CHECKS none` (bare, 5 files) → `refused`.
  - `head`/`base` ← the 40-hex value or `None` (`unknown` → `None`); `files_changed`/`insertions`/`deletions` ← the diffstat summary `^ (\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?$`, absent parts 0, no summary 0/0/0.
  - `usage` ← the `usage:` JSON: `{"in": input, "out": output, "cache_read": cacheRead, "reasoning": reasoning, "events": events, "duration_s": duration_s}` with `0` for a missing integer and `None` for a missing `duration_s`; `usage: {}` → zeros and `None`.
  - `error_class` ← the `error_class:` line when present (new results); else the metadata-only fallback, in this order: `submit-failed` (a line `seat: submit failed`); `timeout` (`exit_code` 124); `no-result-line` (`FACTORY-NOTES` begins `result-misparse:` or `the seat produced no usable FACTORY-RESULT line`); `template-echo` (`FACTORY-NOTES` is `status=done but the branch has no commits` or `a bare result was echoed, not a real completion`, or `status` is `done` and `commits` is 0); `boot-failure` (`wall_s` < 10 and `usage.events` < 50 and `status` ≠ `done`); `none`. `FACTORY-NOTES` is read for this decision only and never stored.
  - `seat_unit` ← `seat: unit seat@<id>` → `<id>`, else `None`; `result_path` ← the real path; `result_mtime` ← the file's mtime as `ts`.
- `tools/factory/seat/factory-lib.sh`:
  - `factory_error_class <log> <status> <exit_code> <wall_s> <events> <synth> <demoted>` prints one enum word. `synth` is `submit`, `nearmiss`, `none` or empty (which branch synthesised the block); `demoted` is `zero-commits`, `echo`, `mismatch` or empty (the CR3r arm that demoted a `done`). Rule, in order: `submit` → `submit-failed`; `exit_code` = 124 → `timeout`; `status` = `done` → `none`; the last 4,000 bytes of the log (`tail -c 4000`) matching both `402` and `budget_exhausted` → `budget-402`; matching `\b(502|503|529)\b|upstream|provider` → `provider-error`; matching `UNKNOWN_MODEL` → `unknown-model`; `synth` in `nearmiss|none` → `no-result-line`; `demoted` in `zero-commits|echo` → `template-echo`; `wall_s` < 10 and `events` < 50 → `boot-failure`; otherwise `none`. An empty `wall_s`/`events` counts as 0. Never fails: an unreadable log reads as empty.
  - `factory_ingest_result <result>`: `"$FACTORY_EVIDENCE_CMD"` when set, else `factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py"`, with `${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} ingest result "$result"`, stdout+stderr appended to `$log`; returns the command's status.
- `tools/factory/seat/factory-task`: (1) `synth` is set in the three synthesising branches (`submit`, `nearmiss`, `none`); `demoted` in the three CR3r arms; `events` parsed from `$usage_json` with `[[ $usage_json =~ \"events\":\ *([0-9]+) ]]`; `error_class=$(factory_error_class "$log" "$status" "$exit_code" "$wall_s" "$events" "$synth" "$demoted")` computed after the CR3r block; (2) the result gains `printf 'plan: %s\n' "$plan"` after `route:` and `printf 'error_class: %s\n' "$error_class"` after `exit_code:`; (3) after `} >"$result"`: `factory_ingest_result "$result" || factory_log "evidence: could not record $key"`; `exit "$task_rc"` unchanged.

**Facts:**

- `sed -n '/^result=\$runs_dir/,/^} >"\$result"/p' tools/factory/seat/factory-task` → the writer: the four `FACTORY-*` lines, a blank, `run:`, `key:`, `model:`, `effort:`, `route:`, `workspace:`, optional `seat: unit seat@%s` or `seat: submit failed (no job id)`, `branch:`, `head:`, `base:`, `wall_s:`, `exit_code:`, blank, `commits (base..task/$key):`, the `git log --oneline` lines or `(no commits)`/`(none)`/`(base commit unknown -- .factory-meta missing)`, blank, `diffstat:`, the `git diff --stat` text, blank, `usage: <json>`. The three synthesising branches set `notes_line` to `FACTORY-NOTES seat-submit produced no valid job id; see $log`, `FACTORY-NOTES result-misparse: $near_note`, `FACTORY-NOTES the seat produced no usable FACTORY-RESULT line; see $log`; the CR3r arms set `status=failed` with notes `…; claimed N commits, found M`, `status=done but the branch has no commits`, `a bare result was echoed, not a real completion`.
- `factory_record_check`'s seam (`factory-lib.sh`): `if [ -n "${FACTORY_EVIDENCE_CMD:-}" ]; then "$FACTORY_EVIDENCE_CMD" … record-check … >>"${log:-/dev/null}" || factory_log …` — the shape `factory_ingest_result` copies; `factory_py` honours `FACTORY_PYTHON3_CMD` (the sandbox seam `82-factory-dispatch.bats` uses).
- Counts over `~/factory/runs/*/*.result` (2026-09-06 09:26; `grep -h '^<field>:' … | sort | uniq -c`, values only): 237 files; `effort:` present in 86 (`medium` 72, `off` 11, `xhigh` 2, `high` 1); `route:` in 86 (`implement/code/S` 57, `explicit` 12, `implement/code/XS` 7, `implement/code/M` 5, `implement/docs/S` 3, `implement/docs/XS` 1, `implement/any/any` 1); `model:` `deepseek/deepseek-v4-pro-0813` 219, `deepseek/deepseek-v4-flash` 16, `z-ai/glm-5.3` 1, `moonshotai/kimi-k3` 1; `FACTORY-RESULT status=` `done` 223, `failed` 12, `partial` 1, `pass` 1; `exit_code:` `0` 231, `1` 6 (no 124 yet); `head: unknown` 0; `FACTORY-CHECKS none` (bare) 5; `usage: {}` 0; the usage keys `cacheRead duration_s events input model output reasoning`; diffstat summaries in seven shapes (`N file changed, N insertion(+)` … `N files changed, N insertions(+), N deletions(-)`); `(no commits)` 13; `FACTORY-NOTES the seat produced no usable` 12; `result-misparse:` 0; `wall_s` < 10 in 2; 234 of 237 `workspace:` clones still have `.git/config` (`url = …/base/nixos-agent-env`, the shape `_repo_from_workspace` matches with `/base/([^/\s]+)$`).
- `tests/unit/80-seat-driver.bats` `setup()`: `REAL_BASH`, `FACTORY_PLAN` exported to an empty plan, `FACTORY_ROOT`/`FACTORY_RUNS` under `$BATS_TEST_TMPDIR`; the test `factory-task resolves model and effort through routing.toml and records the route` builds `seat_copy` (shebang repointed), a fake `factory-ws` printing a workspace path, a fixture toolbox with `docs/ledger/routing.toml`, and a fake `dsh-openrouter` on PATH that prints the four result lines — the idiom every new test copies.

- [ ] **Step 1: Write the failing tests.** Pytest (`tests/evidence/test_ingest_result.py`, fixtures under `tests/evidence/fixtures/results/`, copied into a temp `runs/<run>/` tree so `--runs-root` binds them):

| # | assertion (fixture → expected) | mutant |
|---|---|---|
| 1 | `done.result` (status done, `FACTORY-CHECKS unit=pass lint=pass`, `FACTORY-COMMITS 1`, one `abc1234 subject` commit line, `route: implement/code/S`, `effort: medium`, diffstat `2 files changed, 10 insertions(+), 3 deletions(-)`, `usage: {"input":10,"output":5,"cacheRead":1,"reasoning":2,"events":40,"duration_s":12.5}`) → one row: `kind code`, `size S`, `commits 1`, `commits_declared 1`, `checks {"unit":"pass","lint":"pass"}`, `checks_parse ok`, `files_changed 2`, `insertions 10`, `deletions 3`, `usage {"in":10,"out":5,"cache_read":1,"reasoning":2,"events":40,"duration_s":12.5}`, `error_class none`, `seat_unit None`, `plan None` | any one field's producer |
| 2 | `status-pass.result` → `status unknown`; a file without any `FACTORY-RESULT` line → refused `not a result file` | accept any word |
| 3 | (g) `hostile-checks.result` (a `FACTORY-CHECKS` line whose one key is 4,096 chars) → `checks {}`, `checks_parse refused`, the row lands; `grep -c` of any key over 64 chars in `derived/tasks.jsonl` is 0; a `FACTORY-CHECKS` line reading `log=pass unit=pass` (`log` is a forbidden name) → `checks {}`, `checks_parse refused`, the row lands; `FACTORY-CHECKS none` → `refused`; no line → `missing`; 64 good tokens → `ok`; 65 → `refused` | store the map anyway; `>` vs `>=`; keep the forbidden-named key |
| 4 | `template-echo.result` (status done, `(no commits)`, notes `ok`) → `error_class template-echo`, `commits 0`; the same with `FACTORY-NOTES status=done but the branch has no commits` and status failed → `template-echo`; a `demoted=echo` result whose log tail contains the word `provider` → `template-echo`, not `provider-error` (the demoted rule wins over the tail-pattern rule) | drop the zero-commit rule; reorder the demoted check after the tail-pattern checks |
| 5 | `timeout.result` (`exit_code: 124`, status failed) → `timeout`; with also `seat: submit failed (no job id)` → `submit-failed` (precedence); a `synth=nearmiss` result whose log tail contains `503` → `no-result-line`, not `provider-error` (the synth-branch rule wins over the tail-pattern rule) | drop the exit-124 rule → `none`; reorder the synth check after the tail-pattern checks |
| 6 | `submit-failed.result` → `submit-failed`, `seat_unit None`; `no-result-line.result` (notes `the seat produced no usable …`) → `no-result-line`; a result with `wall_s: 3` and `"events": 10` and status failed → `boot-failure`; the same with status done → `none` | each rule |
| 7 | `classified.result` carrying `error_class: provider-error` → `provider-error` (the line wins over the fallback) | ignore the line |
| 8 | `plan: /home/x/nixos-agent-env/docs/superpowers/plans/p.md` → `plan docs/superpowers/plans/p.md`; `plan: /tmp/p.md` → `None`; `seat: unit seat@20260906-101010-abcdef` → `seat_unit 20260906-101010-abcdef` | keep the absolute path (the fence then refuses it — the test asserts the row landed) |
| 9 | `ingest result /etc/passwd` → exit 2, stderr `is outside`, no `derived/tasks.jsonl`; `[<good>, /etc/passwd]` → exit 2 and nothing written (all paths checked first); a path inside `--runs-root` that does not exist on disk → stderr `not a result file`, counted refused, exit 1 (no traceback) | check paths while writing; let the missing-file case raise |
| 10 | re-ingest of the same file → one row, bytes identical; two files with the same `(run, key)` in different dirs are two paths but one key → the later replaces | replace by path |
| 11 | `effort: max` → `unknown`; `route: bogus` → `route unknown`, `kind unknown`, `size unknown`; a missing `route:` → the same; `model: Bad/Model` → the row refused (`model: not a model-id`) and counted, exit 1, the others written | map an unknown effort through |
| 12 | `repo`: a fixture workspace with `.git/config` `url = /x/base/nixos-agent-env` → `repo nixos-agent-env`; no clone → `None` | — |
| 13 | the log is never read: a `<key>.log` beside the fixture is `chmod 000` (skipped as root) and the ingest still succeeds | open the log for the tail |

Bats (`tests/unit/80-seat-driver.bats`), sourcing `factory-lib.sh` for the function tests:

| # | assertion | mutant |
|---|---|---|
| 14 | `factory_error_class` table: one synthetic log per class (`… 402 … budget_exhausted …` → `budget-402`; `… 503 …` → `provider-error`; `UNKNOWN_MODEL` → `unknown-model`); the precedence pairs: 402-tail + exit 124 → `timeout`; 402-tail + status done → `none`; a log whose last line is `provider: DeepInfra` with status done → `none`, with status failed → `provider-error`; `synth=nearmiss` → `no-result-line`; `demoted=zero-commits` → `template-echo`; wall 3 events 10 status failed → `boot-failure`; empty log, status failed → `none` | any rule; the `done` guard |
| 15 | the 4,000-byte bound: a 1 MB log whose only `402 budget_exhausted` sits in its first 100 bytes → `none`; the same marker in the last 100 bytes → `budget-402` | drop `tail -c 4000` |
| 16 | `factory-task` (the fake-seat idiom) writes `error_class: none` and `plan: <the absolute plan path>` into the result, and calls `FACTORY_EVIDENCE_CMD` once with `ingest result <the result path>` after the file exists (the fake records `[ -f "$3" ]`); a fake seat printing a near-miss `FACTORY-RESULT: status=done` → `error_class: no-result-line` | write the line before the file; skip the call |
| 17 | a failing `FACTORY_EVIDENCE_CMD` (exit 1) leaves `factory-task`'s exit code unchanged (0 for done) and logs `evidence: could not record K1` | `set -e` on the call |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence/test_ingest_result.py -q` → `StopIteration` from the loader (no `pkgs/evidence/ingest_result.py`); `nix develop -c bats tests/unit/80-seat-driver.bats --filter error_class` → `factory_error_class: command not found` (paste both).

- [ ] **Step 3: Write `pkgs/evidence/ingest_result.py`** (`parse_result(text, path, runs_root) -> dict | None`, `fallback_error_class(fields) -> str`, `ingest(store, paths, runs_root) -> (n, refused)`, `main(argv)`), the two shell functions, the three `factory-task` edits.

- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c treefmt`; `nix develop -c pytest tests/evidence -q`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `git add` the new files; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `… unit`; `nix develop -c githooks/pre-commit`.

- [ ] **Step 5: Commit.**

**Tests:** rows 1–17 above; the discriminating fixtures are the corpus's own shapes: `status=pass`, `FACTORY-CHECKS none`, the seven diffstat forms (one fixture each in row 1's parametrisation), `usage: {}`, a `(no commits)` section, the 12 "no usable" notes, the 2 sub-10-second results.

**touches:** pkgs/evidence/ingest_result.py, tests/evidence/test_ingest_result.py, tests/evidence/fixtures/results/done.result, tests/evidence/fixtures/results/status-pass.result, tests/evidence/fixtures/results/hostile-checks.result, tests/evidence/fixtures/results/template-echo.result, tests/evidence/fixtures/results/timeout.result, tests/evidence/fixtures/results/submit-failed.result, tests/evidence/fixtures/results/no-result-line.result, tests/evidence/fixtures/results/classified.result, tools/factory/seat/factory-lib.sh, tools/factory/seat/factory-task, tests/unit/80-seat-driver.bats
**acceptance:** evidence-unit, unit, lint
**commit subject:** `evidence: the tasks stream — ingest result rooted at ~/factory/runs, error_class in the driver, one line in factory-task (test: evidence-unit, unit, lint)`

### T3 (code, M) — the gates stream: the review block completed, ingest reviews, the review lint, one line in factory-integrate

**dependsOn:** T1

**Files:**
- Create: `pkgs/evidence/ingest_reviews.py`, `pkgs/evidence/migrate_reviews.py`, `tests/evidence/test_ingest_reviews.py`, `tests/evidence/test_migrate_reviews.py`, `tests/evidence/fixtures/reviews-migrate/h1-markers.md`, `tests/evidence/fixtures/reviews-migrate/h1-no-markers.md`, `tests/evidence/fixtures/reviews-migrate/block-five-keys.md`, `tests/evidence/fixtures/reviews-migrate/legacy-h1.md`, `tests/evidence/fixtures/reviews-migrate/migrated.md`, `tests/evidence/fixtures/reviews-migrate/majors-none.md`, `tests/evidence/fixtures/runs/r1/K1.review.md`, `tests/evidence/fixtures/runs/r1/K2.review.md`, `tests/evidence/fixtures/runs/r1/K3.review.md`, `tests/evidence/fixtures/runs/r1/K4.review.md`, `tests/unit/84-factory-integrate-reviews.bats`
- Modify: `pkgs/evidence/tasks.py` (`_review_defect_errors`, a duplicate-key helper), `tests/evidence/test_tasks.py`, `tools/factory/seat/factory-integrate`

**Interfaces:**

- The block (one, never two): keys allowed in a review's front matter are exactly `plan_defect`, `plan_defect_secondary`, `mutants_total`, `mutants_killed`, `mutants_outside_named`, `reviewer`, `majors`, `minors`, `model`. `run`, `key` and the verdict stay in the H1 (`REVIEW_RE` unchanged); the block never carries a verdict.
- `tasks.py` `_review_defect_errors` (the lint the gate already runs) on every file with a block, whatever its date: an unknown key → `tasks: review {name}: unknown key {k}`; a key appearing twice → `tasks: review {name}: duplicate key {k}` (a helper re-reads the block's lines; `_split_front_matter`'s tuple API is unchanged); `majors`/`minors`/`mutants_total`/`mutants_killed`/`mutants_outside_named` must be a non-negative integer or the literal `null` → else `{k} must be an integer or null`; `reviewer` outside `opus|sonnet|deepseek|fable|unknown` → `reviewer {v} not in …`; the H1 must follow the block (unchanged) and, on any file dated on or after `front_matter_from` whose H1 has the `# Opus gate — seat run R, task K — WORD` shape with `WORD` outside `APPROVED|REJECTED` → `tasks: review {name}: H1 verdict {WORD} not in APPROVED | REJECTED`; `plan_defect` is required only for files dated on or after `front_matter_from` (D9); `plan_defect`'s enum, the rejection-names-its-cause rule and the ledger-contradiction rule are unchanged. Files dated before `front_matter_from` without a block stay silent (unchanged).
- `pkgs/evidence/migrate_reviews.py <repo> [--check]`: over `<repo>/docs/reviews/*opus-review*.md` in name order. A file whose first line is `---` (a block): missing `reviewer` → `reviewer: opus`; missing `majors`/`minors` → the parsed count or `null`; missing `mutants_total`/`mutants_killed` → added only when parsed; existing keys and their order untouched; the H1 and body untouched. A file whose first line matches `REVIEW_RE`: a block is prepended — `---`, `reviewer: opus`, `majors: <n|null>`, `minors: <n|null>`, `mutants_total: <n>` and `mutants_killed: <n>` only when parsed, `---`, then the file unchanged (the H1 stays the first line after the block). Any other first line (a legacy H1) → skipped, counted. The script never writes `plan_defect` or `plan_defect_secondary`. Counting rules over the body (the lines after the block): a *marker line* is a line, allowing up to three leading spaces of indentation, whose first token after optional decoration (`#`s, `-`, `*`, `N.`, `N)`, `**`) is `MAJOR` or `MINOR` case-insensitively, optionally followed by `-` or a space and digits, and not followed by a letter (so `## Majors` is not a marker); `majors` = the number of MAJOR marker lines, `minors` likewise; when a class has no marker line and the body has a heading line whose text is `Major`/`Majors`/`Minor`/`Minors` followed within two lines by a line that is `none`, `(none)` or `None.` → 0; no marker and no such heading → `null`. Mutation counts: the first match of `(\d+)\s*(?:/|of)\s*(\d+)\s*(?:named\s+)?(?:mutants?\s+)?(?:killed|mutants?|mutations)` → killed, total; else the first `(\d+)\s+killed` → killed only (total omitted). Output: per file, `would change: <file>` (under `--check`) or nothing (a real run); a summary line `checked: <total>; would change: <N>`; `--check` exits 1 when `N > 0`, 0 when `N == 0`; a real run always exits 0 and prints `migrated: blocks added A, keys added K, unchanged U, skipped legacy L` instead of the summary line.
- CLI `evidence [--store S] ingest reviews [--runs-root DIR] <repo> <runs-dir>` (`ingest_reviews.main`, subparser `reviews`): `<repo>/docs/reviews/` must exist; `<runs-dir>` must resolve under `--runs-root` (default `~/factory/runs`) or equal it, else exit 2 before any write; one `gate-verdict` row per `<repo>/docs/reviews/*opus-review*.md` and per `<runs-dir>/*/*.review.md`, written with `replace_stream` to `derived/gates`; stdout `ingested {n} gate rows (docs/reviews: {r}, H1 parsed {h}, blocks {b}, legacy {l}; runs: {d})`; exit 1 when any row was refused. The body of a review is never stored: only the block, the H1, the file name, the file's hash and `git log` are read.
- Row producers for `docs/reviews/<name>`: `run_id`, `key` ← the H1 (`_review_h1` over the block-aware tuple) or, when it does not match, the file name rule `^\d{4}-\d{2}-\d{2}-opus-review-(?P<run>[a-z0-9]+)-(?P<key>[A-Za-z0-9-]+)\.md$` (all 164 names match it); `chain_root` ← `tasks.chain_root(key)`; `round_kind`, `round` ← D7's tokeniser (`round_of(key) -> (kind, n)`); `reviewer` ← block `reviewer` else `unknown`; `route` ← `claude`; `model` ← block `model` else `None`; `verdict` ← H1 `APPROVED`→`approved`, `REJECTED`→`rejected`, no match → `unknown`; `majors`, `minors`, `mutants_total`, `mutants_killed`, `mutants_outside_named` ← block ints or `None` (`null` → `None`); `plan_defect`, `plan_defect_secondary` ← block or `None`; `gate_tokens`, `wall_s` ← `None`; `review_path` ← `docs/reviews/<name>`; `review_sha256` ← sha256 of the bytes; `review_commit`, `review_commit_ts` ← the last line of `git -C <repo> log --diff-filter=A --format=%H%x09%cI -- docs/reviews/<name>` (the add commit; `%cI` converted to UTC `Z`), `None` when git prints nothing. For `<runs-dir>/<run>/<KEY>.review.md`: `run_id` ← the directory, `key` ← the stem before `.review`, `reviewer deepseek`, `route openrouter`, `model None`, `verdict` ← the last `^FACTORY-REVIEW verdict=(approve|rework|reject)` line: `approve`→`approved`, `reject`→`rejected`, `rework`→`rejected` (D8), none → `none`; counts `None`; `review_path` ← the real path; `review_commit(_ts)` `None`; `round_kind`/`round`/`chain_root` are computed the same way as for a `docs/reviews` row, via `round_of(key)`/`tasks.chain_root(key)` on the stem key.
- `tools/factory/seat/factory-integrate`: after the summary block and before the fast-forward recipe print, a local function `ingest_reviews()` — `"$FACTORY_EVIDENCE_CMD"` when set, else `factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py"`, with `${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} ingest reviews "$repo_path" "$FACTORY_RUNS" >>"$log" 2>&1` — called as `ingest_reviews || logboth "evidence: could not record reviews"`; `overall_rc` unchanged by it.

**Facts:**

- `grep -n 'REVIEW_RE = \|def _split_front_matter\|def _review_defect_errors\|plan_defect missing\|the H1 must follow the block\|must be an integer' pkgs/evidence/tasks.py` → `REVIEW_RE = re.compile(r"^# Opus gate — seat run (?P<run>\S+), task (?P<key>\S+) — (?P<verdict>APPROVED|REJECTED)")`; `_split_front_matter` keeps the last value of a repeated key (`block[key.strip()] = value.strip()` in a loop — no duplicate detection); `_review_defect_errors` errors on `plan_defect missing` for *any* block, on `the H1 must follow the block`, on `{key} must be an integer` for the three mutants keys.
- Corpus counts (2026-09-06 09:26; `for f in docs/reviews/*opus-review*.md; do head -1 "$f"; done | … | sort | uniq -c` and the H1 loop in the packet): 164 files; 18 open with `---` (keys present: `plan_defect` 18, `mutants_total` 18, `mutants_killed` 18, `mutants_outside_named` 18, `plan_defect_secondary` 9 — nothing else); 119 open with a `REVIEW_RE` H1 (`APPROVED` 65 + `REJECTED` 54); 27 open with a legacy H1 (e.g. `# Opus gate round 2 — W2-N10c (…)`, `# Opus gate — N16 round 3 (…)`); 137 H1s parse in all (`_review_h1` over block and blockless). 7 files carry a `plan_defect:` line in their body (lines 274–482), not a block — the block parser reads line 1 only. `grep -l '^plan_defect:' … | wc -l` → 25 is where the spec's "25 files" came from.
- Marker and mutation forms in the corpus (`grep -ho … | sort | uniq -c`): bare `MAJOR` 317 and `MINOR` 562 mentions; line-initial forms `**MAJOR-N**` 13, `**MINOR-N**` 5, `**MINOR N**` 5, `### MINOR-N — …` 4, `**major (reject)**` 2, `**Minor.**` 4, headings `## Majors` 5, `## Minors` 11, `### Minors` 1; mutation forms `N killed` 30, `N/N killed` 4, `N of N killed` 3, `N/N mutants` 2, `N of N mutants killed` 1, `N/N mutations` 1. Files with at least one line-initial MAJOR marker (leading whitespace allowed, case-insensitive): 62; MINOR: 108; with a mutation form: 43 — most blocks will carry `null` counts; the counts are a proxy for the reviewer's tally (gap: prose the regexes do not read), declared as such in the ingest's docstring.
- `ls ~/factory/runs/*/*.review.md | wc -l` → 23; `grep -ho '^FACTORY-REVIEW verdict=[a-z]*' … | sort | uniq -c` → `approve` 17, `rework` 6; `factory-review` writes `md=$runs_dir/$key.review.md` as `cp -- "$log" "$md"` and reads `grep -oE '^FACTORY-REVIEW verdict=[a-z]+' … | tail -n1` (`approve|rework|reject`, else `none`).
- `git log --diff-filter=A --format='%H%x09%cI' -- docs/reviews/2026-09-04-opus-review-a3-N10.md` → `123128a3e4650238fd2f998356d831b1eb175d32	2026-09-04T16:42:42-05:00` (one line; the add commit). `git log --format=%s | grep -c '^docs: gate review'` → 97 (reviews were also added in board commits — hence "the add commit", not "the gate-review commit").
- `ls docs/reviews/*opus-review*.md | xargs -n1 basename | grep -vcE '^[0-9]{4}-[0-9]{2}-[0-9]{2}-opus-review-[a-z0-9]+-[A-Za-z0-9-]+\.md$'` → 0 (every one of the 164 names matches the file-name rule, so the join's name-derived fallback covers all 27 legacy-H1 files too: 137 H1-parsed + 5 more distinct-from-H1 name pairs = 142 results matched at Operator step 6, not 137 — see the T10a Facts).
- `grep -n 'front_matter_from' docs/ledger/plan-defects.toml` → `front_matter_from = 2026-09-07`; `tests/evidence/test_tasks.py`'s `test_check_plan_defect_missing` uses a review dated `2026-09-07` (stays red-on-missing under D9); `FMF_LEDGER = "[meta]\nfront_matter_from = 2026-09-07\n"` is the fixture ledger.
- `tests/unit/91-orchestrator-guard.bats` `the sweep holds every command in the cr17 and cr18 review tables` parses the two files' markdown tables (`tables(path)`), so a prepended block is invisible to it.

- [ ] **Step 1: Write the failing tests.** `tests/evidence/test_tasks.py` (new tests beside the P3A ones, using `_defect_repo`/`_defect_graph`):

| # | assertion | mutant |
|---|---|---|
| 1 | a 2026-09-07 block review whose H1 says `— REWORK` → an error containing `H1 verdict REWORK not in APPROVED | REJECTED` | accept REWORK (`APPROVED|REJECTED|REWORK` in the shape regex) |
| 2 | a block with `majors: 3` and `minors: null` → no error; `majors: three` → `majors must be an integer or null`; `minors: -1` → error | accept any string |
| 3 | `reviewer: opus` ok; `reviewer: claude` → `reviewer claude not in …`; `unknown` ok | accept any |
| 4 | a block with `plan_defect: vacuous` twice → `duplicate key plan_defect` | keep last-wins |
| 5 | a block with `verdict: rejected` → `unknown key verdict` | accept unknown keys |
| 6 | a 2026-09-05 file with a block lacking `plan_defect` (only `reviewer`, `majors`, `minors`) and a REJECTED H1 → no error (D9); the same dated 2026-09-08 → `plan_defect missing` (the existing test stays) | drop the date condition |
| 7 | `read_reviews` still parses the H1 after a five-line block (`reviewer`, `majors`, `minors`, `mutants_total`, `mutants_killed`) | — (regression pin) |

`tests/evidence/test_migrate_reviews.py` (the fixture corpus copied into a temp `docs/reviews/`):

| # | assertion | mutant |
|---|---|---|
| 8 | `h1-markers.md` (H1 + body with `**MAJOR-1**`, `**MAJOR-2**`, `### MINOR-1 — x`, `- MINOR 2: y`, `MINOR-3`, a sentence "six minors" that is not line-initial, and `12/14 mutants killed`) → prepended block `reviewer: opus`, `majors: 2`, `minors: 3`, `mutants_total: 14`, `mutants_killed: 12`, H1 unchanged on the line after `---`; an indented fixture line `  - MINOR 4: indented` is counted as a fourth minor when present; the corpus's lowercase form `**major (reject)** x` is counted as a major | count inline mentions; swap killed/total; anchor the regex at column 0; drop `re.I` |
| 9 | `h1-no-markers.md` → `majors: null`, `minors: null`, no mutants keys; `majors-none.md` (`## Majors` then `none`, `## Minors` with two markers) → `majors: 0`, `minors: 2` | write `0` for no markers |
| 10 | `block-five-keys.md` (the P3A block) → the five keys unchanged in place, then `reviewer: opus`, `majors: …`, `minors: …` appended before `---`; `plan_defect` never added to `h1-markers.md` | overwrite; add `plan_defect: none` |
| 11 | `legacy-h1.md` (`# Opus gate round 2 — X (y)`) → untouched, `skipped legacy 1` | migrate it (the lint test 7 above would then fail on `the H1 must follow the block`) |
| 12 | second run over the migrated corpus → every file byte-identical and `--check` exits 0; `--check` on the unmigrated corpus exits 1 listing the files and writes nothing | restamp; write under `--check` |
| 13 | after a run, `tasks.check` over the fixture repo (with `FMF_LEDGER`) prints nothing | any rule the migration violates |

`tests/evidence/test_ingest_reviews.py` (a temp repo with a git history holding two reviews, plus the four `.review.md` fixtures under a temp runs root):

| # | assertion | mutant |
|---|---|---|
| 14 | a block review `2026-09-06-opus-review-r1-K1.md` (block `plan_defect: vacuous`, `reviewer: opus`, `majors: 1`, `minors: null`, `mutants_total: 4`, `mutants_killed: 3`) with a REJECTED H1 → row `run_id r1`, `key K1`, `chain_root K1`, `round_kind first`, `round 1`, `reviewer opus`, `route claude`, `verdict rejected`, `majors 1`, `minors None`, `mutants_total 4`, `mutants_killed 3`, `plan_defect vacuous`, `review_path docs/reviews/…`, `review_sha256` = hashlib of the bytes, `review_commit` = the add commit's sha, `review_commit_ts` ending `Z` | each producer |
| 15 | a blockless review → `reviewer unknown`, counts `None`; a legacy H1 `2026-09-05-opus-review-r2-K2b.md` → `run_id r2`, `key K2b` from the name, `verdict unknown`, `round_kind fix`, `round 2` | use the H1 only |
| 16 | `round_of`: `SB4b`→(fix,2), `CR2r`→(replan,2), `RT5rb`→(replan,3), `CR2r3b`→(replan,5), `OG1r2`→(replan,3), `N7c`→(fix,3), `BFIX4`→(first,1), `T10a`→(first,1), `W2-N6b`→(fix,2), `T10b`→(first,1) with `chain_root` `T10` (a variant letter after a digit is a chain sibling to the graph but not a fix round to the gates stream — it disagrees with `chain_root`, deliberately: D7); `chain_root("OG1r2") == "OG1r2"` (the graph's rule, kept) | any weight; strip `a`; treat `b` as a fix letter unconditionally |
| 17 | `.review.md`: `K1` approve → `approved`; `K2` rework → `rejected`; `K3` reject → `rejected`; `K4` no verdict line → `none`; each `reviewer deepseek`, `route openrouter`, `model None`, `review_path` the real path, and each carries `round_kind`/`round`/`chain_root` computed from the stem key via `round_of`/`chain_root` | map rework to `unknown`; skip the round/chain_root computation for `.review.md` rows |
| 18 | roots: `<runs-dir>` outside `--runs-root` → exit 2, nothing written; a repo without `docs/reviews` → exit 2 | check after writing |
| 19 | idempotent: two runs → identical bytes; a changed review (its sha changes) → one row replaced | key on `(run_id, key)` — the two-rounds fixture (`K1` and `K1b` files) must yield two rows |
| 20 | the stdout line's five counts equal the fixture's (`docs/reviews: 4, H1 parsed 3, blocks 2, legacy 1; runs: 4`) | miscount |
| 21 | the body never enters the row: a review whose body contains `sk-or-v1-abc` still ingests (nothing scans the body) and no row value equals any body line | store `first` |

`tests/unit/84-factory-integrate-reviews.bats` (the `records one check observation` idiom with the fake recorder):

| # | assertion | mutant |
|---|---|---|
| 22 | after a successful integration the recorder log's last line is `ingest reviews <src> <FACTORY_RUNS>` (with `--store … ` first when `EVIDENCE_STORE` is exported) | drop the call |
| 23 | a recorder that exits 1 leaves `factory-integrate`'s exit 0 and prints `evidence: could not record reviews` | `set -e` |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence/test_tasks.py -q -k 'rework or integer_or_null or duplicate_key or unknown_key or plan_defect_scope'` → the seven fail (paste the assertion lines); `nix develop -c pytest tests/evidence/test_migrate_reviews.py tests/evidence/test_ingest_reviews.py -q` → `StopIteration` from the loader (no modules); `nix develop -c bats tests/unit/84-factory-integrate-reviews.bats` → the recorder log lacks the line (paste).

- [ ] **Step 3: Write the code** — `tasks.py`'s rules (`_block_keys(lines)` helper returning the ordered keys with duplicates; the allowed-key set as a module constant `REVIEW_BLOCK_KEYS`), `migrate_reviews.py`, `ingest_reviews.py` (`round_of`, `parse_review(path, repo)`, `parse_seat_review(path)`, `ingest(store, repo, runs_dir, runs_root)`, `main`), the `factory-integrate` function and call.

- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c treefmt`; `nix develop -c pytest tests/evidence -q`; `nix develop -c bats tests/unit/84-factory-integrate-reviews.bats`; `git add` the new files; `python3 pkgs/evidence/repomap.py --root . write`; `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check` → exit 1, the summary line `checked: 164; would change: 137` (the live corpus is not migrated by this task — T3M does it; paste the summary line); `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `… unit`; `nix develop -c githooks/pre-commit`.

- [ ] **Step 5: Commit** (one commit; the migration of `docs/reviews/` is T3M).

**Tests:** rows 1–23; discriminating fixtures: `REWORK` in an H1, `null` against `three`, a duplicate key, a 2026-09-05 block without `plan_defect` against a 2026-09-08 one, the legacy H1, the indented marker and the lowercase `major (reject)` form against line-initial uppercase markers, the inline "six minors" sentence against line-initial markers, `rework` in a `.review.md`, the `K1`/`K1b` pair for the key rule, the `T10b` chain-sibling-vs-fix-round pair.

**touches:** pkgs/evidence/ingest_reviews.py, pkgs/evidence/migrate_reviews.py, tests/evidence/test_ingest_reviews.py, tests/evidence/test_migrate_reviews.py, tests/evidence/fixtures/reviews-migrate/h1-markers.md, tests/evidence/fixtures/reviews-migrate/h1-no-markers.md, tests/evidence/fixtures/reviews-migrate/block-five-keys.md, tests/evidence/fixtures/reviews-migrate/legacy-h1.md, tests/evidence/fixtures/reviews-migrate/migrated.md, tests/evidence/fixtures/reviews-migrate/majors-none.md, tests/evidence/fixtures/runs/r1/K1.review.md, tests/evidence/fixtures/runs/r1/K2.review.md, tests/evidence/fixtures/runs/r1/K3.review.md, tests/evidence/fixtures/runs/r1/K4.review.md, tests/unit/84-factory-integrate-reviews.bats, pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, tools/factory/seat/factory-integrate
**acceptance:** evidence-unit, unit, lint
**commit subject:** `evidence: the gates stream — the review block completed, ingest reviews, the review lint, one line in factory-integrate (test: evidence-unit, unit, lint)`

### T3M (docs, S) — the migration commit: reviewer and counts in every gate review's block

**dependsOn:** T3

**Files:**
- Modify: every `docs/reviews/*opus-review*.md` that T3's script changes (137 at 09:26: 119 blocks prepended, 18 blocks extended; the 27 legacy-H1 files are untouched)

**Interfaces:** none new. The task runs the script T3 landed and commits its output; no file outside `docs/reviews/` changes; no plan file is touched.

**Facts:** the corpus counts under T3's Facts; `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check` on main after T3 → exit 1, the summary line `checked: 164; would change: 137` (recount at landing — every gate review committed between T3's landing and this task's run adds one).

- [ ] **Step 1: The red** — `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check; echo exit=$?` → the file list and `exit=1` (paste the last three lines).
- [ ] **Step 2: Run the migration** — `nix develop -c python3 pkgs/evidence/migrate_reviews.py .` → `migrated: blocks added 119, keys added 18, unchanged 0, skipped legacy 27` (the numbers at 09:26; paste the real line).
- [ ] **Step 3: Prove it** — `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check; echo exit=$?` → `exit=0`, summary line `checked: 164; would change: 0`; `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → prints nothing; `git diff --stat | tail -1` → `137 files changed` with only insertions; `git diff -- docs/reviews | grep '^-' | grep -v '^---' | wc -l` → 0 (nothing removed, nothing rewritten); `grep -L '^reviewer:' docs/reviews/*opus-review*.md | wc -l` → 27 (the legacy files).
- [ ] **Step 4: Commit** — `git add docs/reviews` (never `-A`; the queue block does not change), the subject below.

**Tests:** the three commands of Step 3 are the assertions; mutants: a hand edit to one migrated file (`majors: 1` → `majors: one`) turns `tasks.py check` red; a second run producing a diff turns `--check` red.

**touches:** docs/reviews
**acceptance:** lint
**commit subject:** `docs: reviews — reviewer and counts in every gate review's front-matter block, by migrate_reviews (test: lint)`

### T10a (code, S) — the reader learns derived and monthly streams, join_tasks_gates on (run_id, key), the n-gate, the bundle's join line

**dependsOn:** T2, T3

**Files:**
- Create: `tests/evidence/test_join.py`
- Modify: `pkgs/evidence/evidence.py` (`read`, `join_tasks_gates`, `n_gate`, `bundle`, `render_bundle_markdown`), `pkgs/evidence/SCHEMA.md` (the monthly file rule)

**Interfaces:**

- `read(store, stream) -> list[dict]`: the rows of `<stream>.jsonl` followed by those of every sibling `<stream>-YYYY-MM.jsonl` (the `^<name>-\d{4}-\d{2}\.jsonl$` pattern, in name order; any other sibling ignored), torn lines skipped as today; `[]` when nothing exists. `stream_path` unchanged (writers still name one file).
- `join_tasks_gates(store) -> list[dict]`: one entry per `derived/tasks` row (`kind task-result`) in file order: `{"run_id", "key", "task": <the row>, "gate": <the newest derived/gates row with the same (run_id, key)> | None, "activity": <the ledger/activity-days row for (result_mtime[:10], model)> | None}`. A `derived/gates` row's `(run_id, key)` is taken from its own `run_id`/`key` fields (populated for both `docs/reviews` and `.review.md` rows by T3's ingest — including the file-name fallback for a legacy H1 — so a task whose only review is a legacy-H1 file still joins). "Newest" = max by `(review_commit_ts or "", ts)`; a gate row whose `(run_id, key)` matches no task is not returned. A missing stream reads as `[]` (the activity stream does not exist until T4).
- `n_gate(rows, n=5)`: `rows` when `len(rows) >= n`, else the string `insufficient (n={len(rows)})`. Exported for T10b and the ladder report.
- `bundle()` gains `"join": {"tasks": t, "with_gate": g, "with_activity": a}` (counts from `join_tasks_gates`; `{"tasks": 0, …}` when the streams are absent); `render_bundle_markdown` prints, after the Helm section, `## Join: {t} task rows, {g} with a gate verdict, {a} with activity` (one line; the section heading is what Operator step 6 greps).

**Facts:**

- `sed -n '/^def read(/,/^    return rows/p' pkgs/evidence/evidence.py` → reads `stream_path(store, stream)` only, returns `[]` when absent, skips `json.JSONDecodeError` lines.
- `grep -n '"helm": helm,\|lines += \["", "## Helm now", ""\]' pkgs/evidence/evidence.py` → the `bundle()` return dict and the markdown renderer's Helm section, where the join line goes after.
- The expected live numbers (2026-09-06 09:26): 237 tasks; 142 with a verdict — 137 from a parseable review H1 plus 5 more matched only through the legacy-H1 files' name-derived `(run_id, key)` (T3's ingest gives every one of the 164 `docs/reviews` files a `run_id`/`key`, by H1 when it parses and by file name otherwise, and all 164 names parse: `ls docs/reviews/*opus-review*.md | xargs -n1 basename | grep -vcE '^[0-9]{4}-[0-9]{2}-[0-9]{2}-opus-review-[a-z0-9]+-[A-Za-z0-9-]+\.md$'` → 0); 0 with activity.
- `grep -n 'refused: n=' pkgs/evidence/report.py` → `report.py` prints its own `refused: n={n} < {min_n} (no conclusion under {min_n})`; T10b folds it onto `n_gate` (not here; `test_report.py` pins the string).

- [ ] **Step 1: Write the failing tests** — `tests/evidence/test_join.py` (rows written with `evidence.replace_stream`/`append` under the declared kinds; a helper builds a minimal valid `task-result` and `gate-verdict` row):

| # | assertion | mutant |
|---|---|---|
| 1 | two runs sharing key `K1` (`r1/K1` rejected, `r2/K1` approved) → each task's `gate.verdict` is its own run's | join on `key` alone → both read the newest → red |
| 2 | two gate rows for `r1/K1` (`review_commit_ts` `…T10:00:00Z` and `…T12:00:00Z`) → the 12:00 row; with equal `review_commit_ts` the later `ts` wins | take the first |
| 3 | a task with no gate → `gate None`; a gate with no task → not in the output; the activity stream absent → `activity None` for all, no exception | `KeyError` on the missing stream |
| 4 | `read`: `derived/tasks.jsonl` (2 rows, one torn line) + `derived/tasks-2026-09.jsonl` (1 row) + `derived/tasks-notamonth.jsonl` (1 row) → 3 rows in file-then-month order | drop the glob (→ 2); admit any sibling (→ 4) |
| 5 | `n_gate` at 4 rows → `insufficient (n=4)`; at 5 → the same list object; `n=3` at 3 rows → rows | `>` for `>=` |
| 6 | `bundle()` on a store with 3 tasks, 2 gates → `join == {"tasks": 3, "with_gate": 2, "with_activity": 0}` and the markdown holds the line `## Join: 3 task rows, 2 with a gate verdict, 0 with activity`; an empty store → `0, 0, 0` and the line still prints | drop the line |
| 7 | (regression) the existing `read` tests in `test_evidence.py` stay green; `latest_check` unchanged | — |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence/test_join.py -q` → `AttributeError: module 'evidence' has no attribute 'join_tasks_gates'` (paste), and row 4's count `2 != 3`.

- [ ] **Step 3: Write the code**, then `nix develop -c ruff format pkgs/evidence tests/evidence`.

- [ ] **Step 4: Run green** — `nix develop -c pytest tests/evidence -q`; `git add tests/evidence/test_join.py`; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix develop -c githooks/pre-commit`.

- [ ] **Step 5: Commit.**

**Tests:** rows 1–7; the discriminating fixtures: the shared-key pair, the two-gate pair with equal and unequal timestamps, the `notamonth` sibling, the 4/5 boundary.

**touches:** tests/evidence/test_join.py, pkgs/evidence/evidence.py, pkgs/evidence/SCHEMA.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the reader learns derived and monthly streams, join_tasks_gates on (run_id, key), the n-gate, the bundle's join line (test: evidence-unit, lint)`

### T1b (code, S) — T1 fix round: every enum arm pinned by a literal in the test, the equal-row ts rule tested under a fixed clock, the name fence's enum exemption confined to map keys, task-result's shadowed kind renamed task_kind, the bats fixture in touches and explained

**dependsOn:** (T1)

Typed by the orchestrator on 2026-09-07 from the tel1b gate, `docs/reviews/2026-09-07-opus-review-tel1b-T1.md` (REJECTED; plan_defect implementer, secondary missing-case; 54 mutants, 44 killed). The code on `task/T1` is sound and all four acceptance checks were green on a fresh clone; what is owed is tests that can fail and two contract corrections. Rule A1: this is T1's one fix round; a second rejection re-plans.

**Fresh workspace, step 1 (before anything else):** the workspace is a fresh clone of main; bring T1's commit in uncommitted with `git fetch -q /home/dalhaka/factory/ws/tel1b/T1 task/T1 && git cherry-pick -n FETCH_HEAD` (the branch's one commit a8c2e34; `git status --short` then lists T1's twelve files staged). Everything below is edited on top of that; ONE commit at the end with this section's subject — T1's subject is never reused.

**Contract — every item of the review carried verbatim, each closed as stated:**

1. **MAJOR-1 (`tests/evidence/test_streams_policy.py:466-477`) — "row 13's named mutant \"delete an arm from the tuple\" survives for round_kind, reviewer and effort (and route, checks_parse, plan_defect)":** the section's row 13 requires every arm of the six enums accepted (parametrised); the committed parametrisation carries one arm per enum, and the arm deletions `arm-round_kind-replan`, `arm-reviewer-fable`, `arm-effort-low`, `arm-route-openrouter`, `arm-checks_parse-missing`, `arm-plan_defects-process` each SURVIVED (`239 passed, 1 skipped`). Close: the test module holds a LITERAL `ENUM_ARMS` dict — `{(kind, dotted field): (arm, …)}` for every enum-classed field of `task-result` and `gate-verdict` (`status`, `error_class`, `effort`, `route`, `checks_parse`, `verdict`, `round_kind`, `reviewer`, `plan_defect`, `plan_defect_secondary`, and any other enum-classed field the two entries declare), copied from T1's Interfaces table, never derived from `streams.KINDS` — and three assertions: (a) for each entry, the declared arms in `streams.KINDS` equal the literal exactly (a deleted, added or renamed arm → red); (b) every arm of every entry validates in the kind's valid fixture row (parametrised over `(kind, field, arm)`); (c) every arm's one-letter misspelling is refused with `not in enum`. Mutant: delete any one arm from any enum tuple in `streams.py` → (a) red; re-add it under another spelling → (a) and (c) red.
2. **MAJOR-2 (`pkgs/evidence/evidence.py:166-168`) — "the replace_stream equal-row ts rule has no test that can fail (rows 20 and 21's named mutant survives)":** the mutant `if k in merged and _strip_env(merged[k]) == _strip_env(row):` → `if False:` SURVIVED because `test_replace_stream_replaces_by_key_preserving_ts` asserts the `ts` of a carried-over row no implementation touches, and `test_replace_stream_idempotent` compares bytes across two calls inside one second of `now_iso()`. Close: both tests are rewritten under a monkeypatched clock — the seam is `evidence.now_iso` (if `replace_stream` stamps through another name, monkeypatch that name and say which in the commit body). Row 20 becomes: with `now_iso` → `2026-09-05T12:00:00Z` write `t` rows `(1,1,"a")`, `(1,2,"b")`; with `now_iso` → `2026-09-06T00:00:00Z` replace with `[(1,1,"a"), (1,2,"B"), (2,1,"c")]` → file order `(1,1,"a") (1,2,"B") (2,1,"c")`, 3 rows; the `(1,1)` row (equal ignoring `v`/`ts`) keeps `ts` `2026-09-05T12:00:00Z` byte-for-byte; the `(1,2)` row (changed) carries `2026-09-06T00:00:00Z`; the `(2,1)` row (new) carries `2026-09-06T00:00:00Z`. Row 21 becomes: the same rows twice with `now_iso` advanced by a day between the calls → the file bytes identical after the second call. Mutants: `if False:` (restamp every equal row) → row 20's `(1,1)` assertion and row 21 red; "never restamp" (keep the stored `ts` for a changed row too) → row 20's `(1,2)` assertion red. The review's proof (a 1.1 s gap turns the byte comparison red under the mutant) is the shape these tests pin without sleeping.
3. **MAJOR-3 (`pkgs/evidence/streams.py:494-500`) — "the name fence exempts every enum-classed declared field — wider than the stated contract — and its map-site guard is dead code (row 7's named mutant survives)":** `_name_fence(name, cls)` returns False for `cls[0] in ("path", "enum")`; the section states exactly two exemptions — a map whose key class is a closed enum, and a declared field of class `path` — so the map-site guard `if not enum_keys and _name_fence(k, kcls)` at `streams.py:645` is unreachable and its mutant (`if _name_fence(k, kcls):`) SURVIVED. Close: `_name_fence` exempts `path`-classed declared fields only; the enum-key exemption lives at the map site alone. Tests: row 7 unchanged (its map-site mutant now goes red: `tiles.host: forbidden name`); a new unit assertion `_name_fence("host", ("enum", ("ok",)))` is True and `_name_fence("file", ("path", ("docs",), 200))` is False (mutant: put `enum` back in `_name_fence`'s exemption → red); the existing declared-field walk (`test_declared_field_walk_none_forbidden_but_path`) stays and still passes — no declared field is forbidden-named and enum-classed today, and the walk is what keeps it so.
4. **MAJOR-4 (`pkgs/evidence/streams.py:276`) — "task-result's declared `kind` field is unreachable — ENVELOPE shadows it, so row 1's named mutant survives (plan-side collision)":** `"kind": ("enum", ("code", "docs", "unknown"))` is declared as a field of `task-result` while `ENVELOPE = ("v", "ts", "kind")` is skipped before the field walk, so the enum can never be evaluated and deleting the entry SURVIVED. Close: the field is renamed `task_kind` (`("enum", ("code", "docs", "unknown"))`, the same arms, same position) in `streams.py`, in `SCHEMA.md`'s `derived/tasks` description, and in the `TASK_RESULT` fixture (which gains `"task_kind": "code"`); `ENVELOPE` is unchanged; a new assertion pins that no declared field of any kind is named `v`, `ts` or `kind` (walk `KINDS`; mutant: declare `"kind"` again on any kind → red), and row 1's mutant for the renamed field now goes red (`task_kind: undeclared field` on the fixture). T2's producer writes `task_kind` — T2's section says `kind` at its `route`/`kind`/`size` bullet; T1b corrects that bullet in T2's Interfaces (one parenthesised sentence, this commit of the plan) so the T2 seat writes `task_kind` from `implement/<kind>/<size>`.
5. **MAJOR-5 (`tests/unit/83-plan-brief.bats:166`) — "a file outside the section's touches, unexplained in the commit body":** the added line `cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/streams.py" "$REPO/pkgs/evidence/streams.py"` is necessary (`evidence.py:29` imports `streams` at module top, so the fixture repo that copies `evidence.py` must copy its sibling or the `unit` check goes red) but the commit body never mentions it. Close: `tests/unit/83-plan-brief.bats` is in this section's `touches`, the line stays as T1 wrote it, and the commit body carries one sentence naming the file, the line and the reason.

The seven MINORs of the review (`key_of` dead, eleven `not a {class}` strings untested, the `ingest` positional, the wide `except ImportError`, the unconditional `chmod`, row 29's tautological half, the errata 7/12/13/16 confirmations) are recorded, not owed here; the errata items stay the plan's.

- [ ] **Step 1: Fresh workspace** — the cherry-pick line above; `git status --short` shows T1's files staged and nothing else.
- [ ] **Step 2: Write the failing tests** — items 1–4's assertions in `tests/evidence/test_streams_policy.py` (the `ENUM_ARMS` literal; the two rewritten `replace_stream` tests; the `_name_fence` unit assertion; the no-envelope-name walk; `task_kind` in `TASK_RESULT`). **Run red** on the cherry-picked tree: `nix develop -c pytest tests/evidence/test_streams_policy.py -q` → at least item 3's `_name_fence` assertion, item 4's walk (`kind` is declared on `task-result`) and the `task_kind` fixture assertions fail; paste the failing lines into the commit body. Then prove item 1 and item 2 red the review's way: apply the mutant `arm-round_kind-replan` (delete `"replan"` from `round_kind`'s tuple) → the `ENUM_ARMS` equality fails; apply `if False:` on the equal-row branch → row 20's `(1,1)` assertion fails; revert both; paste both failing lines.
- [ ] **Step 3: Change the code** — `streams.py` (`_name_fence` exempts `path` only; `task_kind`), `SCHEMA.md` (`task_kind`), nothing else in the code unless a test of Step 2 demands it (say what and why in the body).
- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q` (every test green); `python3 pkgs/evidence/repomap.py --root . write` (no change expected); `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `… factory-unit`; `… unit`; `nix develop -c githooks/pre-commit`; then the six arm-deletion mutants of item 1, the two mutants of item 2, the map-site mutant of item 3 and the field-deletion mutant of item 4, each applied, shown red with its failing line, reverted — pasted in the commit body.
- [ ] **Step 5: One commit** with the subject below, the two trailers, the body carrying the reds, the greens, the mutant lines and item 5's sentence; end the reply with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them.

**Tests:** T1's 32 rows unchanged except rows 20 and 21 (rewritten as item 2 states) plus the four new assertions of items 1, 3 and 4 (`ENUM_ARMS` equality/arms/misspellings; `_name_fence` on enum vs path; no declared field named `v`/`ts`/`kind`; `task_kind` declared and its deletion caught by row 1).

**touches:** pkgs/evidence/streams.py, tests/evidence/test_streams_policy.py, pkgs/evidence/evidence.py, pkgs/evidence/judgements.py, pkgs/evidence/tasks.py, pkgs/evidence/report.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_evidence.py, tools/factory/seat/factory-lib.sh, flake.nix, tests/unit/83-plan-brief.bats
**acceptance:** evidence-unit, factory-unit, unit, lint
**commit subject:** `evidence: the fence, fix round — every enum arm pinned, the equal-row ts rule under a fixed clock, the enum exemption on map keys only, task_kind, the bats fixture explained (test: evidence-unit, factory-unit, unit, lint)`

### T1Wb (code, S) — T1W fix round: the self-test's clean arm can fail, the root list pinned by one planted hit per declared root, every red and green pasted in the body

**dependsOn:** (T1W)

Typed by the orchestrator on 2026-09-07 from the tel2 gate, `docs/reviews/2026-09-07-opus-review-tel2-T1W.md` (REJECTED; plan_defect implementer, secondary vacuous; 11 mutants, 9 killed; all five acceptance checks green on a fresh clone, helm-vm included; the four reds reproduced by the reviewer). The fence, the collector, the ledger and the wrapper are sound; what is owed is a self-test that can fail, a repeatable pin on the root list, and the record. Rule A1: this is T1W's one fix round; a second rejection re-plans.

**Fresh workspace, step 1 (before anything else):** the workspace is a fresh clone of main; bring T1W's commit in uncommitted with `git fetch -q /home/dalhaka/factory/ws/tel2/T1W task/T1W && git cherry-pick -n FETCH_HEAD` (the branch's one commit be8fc0a). Main has moved under `docs/OPERATIONS.md` and `docs/MAP.md` since that commit's base: if the cherry-pick stops on either, take main's copy (`git checkout HEAD -- docs/OPERATIONS.md docs/MAP.md`, then `git add` them) — the pre-commit hook regenerates the queue block and `python3 pkgs/evidence/repomap.py --root . write` regenerates the map at Step 4. Everything below is edited on top of that; ONE commit at the end with this section's subject — T1W's subject is never reused.

**Contract — every item of the review carried verbatim, each closed as stated:**

1. **MAJOR-1 (`tests/lint/store-writers.sh:92`) — "The --self-test's clean.py arm cannot fail: `\|` is a literal pipe under grep -E, so the combined pattern matches nothing":** `c="$(count_hits "$FIXTURES/clean.py" "$P_APPEND\|$P_OPEN\|$P_LITERAL")"` — `count_hits` runs `grep -cE`, and in an ERE `\|` is an escaped (literal) pipe, not alternation; a `clean.py` with `STORE = "/var/lib/evidence"`, `F = os.O_APPEND` and `fh = open("x", "a")` appended still gave `selftest_with_dirty_clean=0`. Close: the clean arm counts each of the three patterns on its own (three `count_hits` calls, as the bad-fixture arms do — no combined pattern anywhere in the script) and fails naming `clean.py` and the pattern on any hit; the commit body pastes three runs, each with one escape hatch appended to `clean.py` (`O_APPEND`, `open("x", "a")`, `/var/lib/evidence`) → `--self-test` exit 1 naming `clean.py`, and the run with `clean.py` restored → exit 0. Mutant: put the combined `\|` pattern back → the three dirtied runs exit 0 (the paste shows they exit 1).
2. **MAJOR-2 (`tests/lint/store-writers.sh:19`) — "Named mutant survives: dropping the pkgs/helm root from ROOTS is pinned by nothing, and hides the pre-T1W _append_status_row":** `ROOTS` without `pkgs/helm` → `tree_exit=0`, `selftest_exit=0`, and with the base `collect.py` restored underneath (`os.open(…, os.O_APPEND, 0o640)`, `os.fdopen(fd, "a")`, three literals) still `tree_exit_with_regression=0`; the section's stated pin ("a fixture copy of the old `_append_status_row` in `bad-append.py`") pins the pattern, never the root list. Close: the sweep takes its base directory from one variable (`TREE`, default `.`; the self-test sets it), and `--self-test` gains a planted-root assertion — it builds a temporary tree carrying the six declared roots (`pkgs/evidence pkgs/helm tools/ledger tools/factory tools/session-start.sh tools/ritual.sh`, this list written a second time inside the self-test as its own literal), plants exactly one `O_APPEND` hit per root (a file `_planted.py` inside each directory root; one line appended to a copy of each file root), runs the sweep over that tree with `TREE` pointing at it, and requires exactly one hit per root — a root without a hit → exit 1 `store-writers: self-test: root <root> not swept`; the `pkgs/evidence/evidence.py` exclusion stays and is asserted too (a planted `pkgs/evidence/evidence.py` produces no hit). Mutant: drop `pkgs/helm` from `ROOTS` → `--self-test` exit 1 naming `pkgs/helm` (pasted in the body, then restored); drop the exclusion → the planted `evidence.py` hit turns the count to seven → exit 1.
3. **MAJOR-3 (commit be8fc0a's body) — "The commit body pastes neither the red nor the green, so the only assertion the section offers for --self-test is unrecorded":** the body was seventeen lines of prose and the two trailers. Close: this commit's body pastes, each under its command line — the nine-hit `bash tests/lint/store-writers.sh` red on the pre-T1W tree (`git stash`-free: run it on the cherry-picked tree with `pkgs/helm/collect.py` and `tools/ledger/factory.py` temporarily checked out from e0b80e2, then restored), the two pytest red summaries (`tests/helm`: 2 failed; `tests/ledger`: 10 failed) the same way, the `--self-test` fixture-edit run (`bad-open.py`'s `"a"` → `"w"` → exit 1 naming it, restored → exit 0), the three dirtied-`clean.py` runs of item 1, the root-drop run of item 2, and the green counterparts (`store-writers.sh` exit 0, `--self-test` exit 0, the five checks' last lines).

The seven MINORs of the review (`_stream_of`'s message unpinned, the exit-2 path and the `ImportError` message untested, a finding without `issue`/`title` crashing, two ledger fixtures narrowed, the queue-block pre-commit exit, a dead `<=` assertion) are recorded, not owed here.

- [ ] **Step 1: Fresh workspace** — the cherry-pick line above; `git status --short` shows T1W's files staged.
- [ ] **Step 2: Write the failing self-test first** — the three-pattern clean arm and the planted-root assertion in `tests/lint/store-writers.sh`; **run red**: on the cherry-picked script with the old combined pattern still in place, the dirtied-`clean.py` runs exit 0 (paste one); with `pkgs/helm` dropped from `ROOTS` and the new assertion in place, `--self-test` exits 1 naming `pkgs/helm` (paste); restore `ROOTS`.
- [ ] **Step 3: Change the script** — the three separate counts, `TREE`, the planted-root assertion; nothing else in the code unless a run of Step 4 demands it (say what and why in the body).
- [ ] **Step 4: Run green** — `nix develop -c treefmt`; `nix develop -c shellcheck tests/lint/store-writers.sh`; `bash tests/lint/store-writers.sh` → exit 0; `bash tests/lint/store-writers.sh --self-test` → exit 0; `nix develop -c pytest tests/helm tests/ledger -q`; `node tests/factory/render.test.mjs`; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.helm-unit -L --no-link`; `… ledger-unit`; `… factory-unit`; `… helm-vm` (minutes); `… lint`; `nix develop -c githooks/pre-commit`; then the mutants of items 1 and 2 applied, shown red with their lines, reverted — pasted.
- [ ] **Step 5: One commit** with the subject below, the two trailers, the body carrying every paste of item 3; end the reply with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them.

**Tests:** T1W's mutant table unchanged except its first row, whose kill mechanism is now the planted-root assertion of item 2 (mutant: drop the `pkgs/helm` root → `--self-test` exit 1 naming it), plus the dirtied-`clean.py` assertion of item 1 (mutant: the combined `\|` pattern → the dirtied runs exit 0).

**touches:** tests/lint/store-writers.sh, tests/lint/fixtures/store/bad-append.py, tests/lint/fixtures/store/bad-open.py, tests/lint/fixtures/store/bad-literal.sh, tests/lint/fixtures/store/clean.py, pkgs/helm/collect.py, tests/helm/test_collect.py, tools/ledger/factory.py, tools/ledger/schema.md, tests/ledger/test_factory.py, nixosModules/helm.nix, flake.nix, githooks/pre-commit, tools/factory/dark-factory.js, tests/factory/render.test.mjs
**acceptance:** helm-unit, ledger-unit, factory-unit, helm-vm, lint
**commit subject:** `evidence: every writer through append, fix round — the self-test's clean arm can fail, the root list pinned by planted hits, the reds and greens in the body (test: helm-unit, ledger-unit, factory-unit, helm-vm, lint)`

### T3b (code, S) — T3 fix round: T2's bats file taken from main and its pins strengthened not truncated, the migration keeps every body byte and the final newline, the gates key discriminated, the add-commit rule under two add commits, headings at any level, the reds and greens in the body

**dependsOn:** (T3)

Typed by the orchestrator on 2026-09-07 from the tel2 gate, `docs/reviews/2026-09-07-opus-review-tel2-T3.md` (REJECTED; plan_defect implementer, secondary vacuous; 39 mutants, 33 killed; the three acceptance checks green on a fresh clone with `--rebuild`; the live-corpus smoke `ingested 170 gate rows (docs/reviews: 166, H1 parsed 139, blocks 20, legacy 27; runs: 4)` and `--check` → `checked: 166; would change: 139`, exit 1). The substance works end to end; what is owed is five closures and the record. Rule A1: this is T3's one fix round; a second rejection re-plans.

**Fresh workspace, step 1 (before anything else):** the workspace is a fresh clone of main; bring T3's commit in uncommitted with `git fetch -q /home/dalhaka/factory/ws/tel2/T3 task/T3 && git cherry-pick -n FETCH_HEAD` (the branch's one commit 072491a). Then, unconditionally, take main's copies of the three files T3 must not carry its own version of: `git checkout HEAD -- tests/unit/80-seat-driver.bats docs/OPERATIONS.md docs/MAP.md && git add tests/unit/80-seat-driver.bats docs/OPERATIONS.md docs/MAP.md` (the pre-commit hook regenerates the queue block; `python3 pkgs/evidence/repomap.py --root . write` regenerates the map at Step 4; T2 — which owns the bats file — may or may not have landed on main by then; either way main's copy is the base for item 1). Everything below is edited on top of that; ONE commit at the end with this section's subject — T3's subject is never reused.

**Contract — every item of the review carried verbatim, each closed as stated:**

1. **MAJOR-1 (`tests/unit/80-seat-driver.bats:226`) — "tests/unit/80-seat-driver.bats edited outside touches, unexplained, and the edit disarms two existing observation pins":** `run sort "$log"` became `run head -n 2 "$log"` (and `run cat` → `run head -n 1` at :159 and :190), leaving `[ "${#lines[@]}" -eq 2 ]` and `[ "${#lines[@]}" -eq 1 ]` unable to fail; mutant O6 (a spurious third `factory_record_check "zzz" "$head" ok 0` in `factory-integrate`'s checks loop) SURVIVED. The cause: T3's `ingest_reviews` in `factory-integrate` calls the same `FACTORY_EVIDENCE_CMD` seam, so the fake recorder's log gains one `… ingest reviews <repo> <runs>` line after the check observations. Close: `tests/unit/80-seat-driver.bats` is in this section's `touches` for this one purpose; starting from main's copy, the three affected tests read the observations exactly — `run grep -- ' record-check ' "$log"` (or the equivalent `grep -c`) with `[ "${#lines[@]}" -eq N ]` kept as the count of check observations (N = 1, 1, 2 as before; the `sort` stays where it was so lint precedes unit) — and each additionally asserts exactly one trailing line matching `^--store $BATS_TEST_TMPDIR/ev ingest reviews <repo path> <runs dir>$` (the ingest call, pinned as its own observation). Mutant O6 (a third `factory_record_check` in the loop) → the count assertion goes red; mutant "drop the `ingest_reviews` call" → the trailing-line assertion goes red. The commit body names the file, the reason and both mutant runs.
2. **MAJOR-2 (`pkgs/evidence/migrate_reviews.py:129`) — "The migration changes the body: every already-blocked review loses its final newline":** `new_lines = lines[:close] + additions + lines[close:]` / `return "\n".join(new_lines), "keys", len(additions)` — `splitlines()` drops the trailing newline and the join never restores it, against the section's "the H1 and body untouched"; 20 live files would lose it; row 12's idempotence test cannot see it because every fixture under `tests/evidence/fixtures/reviews-migrate/` is itself written without a final newline. Close: the migration works on the text, not on a line list — the block is spliced into the original string and every byte after the block (the body) is returned unchanged, the original's trailing newline included (and a file without one stays without one); the six fixtures end with a newline like the corpus (the git diff of the fixtures shows only the added byte); row 12 gains the assertion that for every fixture the bytes after the closing `---` line are identical before and after a run, and a blocked fixture's total length grows by exactly the added key lines. Mutant: rejoin through `"\n".join(splitlines())` → the trailing-newline assertion goes red.
3. **MAJOR-3 (`pkgs/evidence/streams.py:318`) — "Named mutant of row 19 survives: keying derived/gates on (run_id, key) silently drops a row":** repointing the `gate-verdict` key from `("review_path",)` to `("run_id", "key")` leaves all seven ingest tests green; a docs review for `(r1, K1)` plus the four `runs/r1/K*.review.md` fixtures ingested five rows but read back four — the docs row gone; the section's named discriminator (the `K1`/`K1b` pair) yields two rows under both keyings. Close: row 19's fixture becomes the discriminating one — a docs review for `(r1, K1)` AND a seat `runs/r1/K1.review.md` for the same `(r1, K1)` → two rows in `derived/gates`, one per `review_path`; the `K1`/`K1b` pair stays as a second case. Mutant: key on `(run_id, key)` → one row → red (pasted).
4. **MAJOR-4 (`pkgs/evidence/ingest_reviews.py:119`) — "Named mutant of row 14's review_commit producer survives: the 'last line' add-commit rule is untested":** `sha, _, ts = lines[-1].partition("\t")` mutated to `lines[0]` survives because `_git_repo` (the test fixture) always makes exactly one commit. Close: the fixture repo makes three commits on the review file — add, delete, re-add — so `git log --diff-filter=A` prints two lines (the re-add first, the original add last); row 14 asserts `review_commit` is the original add's sha and `review_commit_ts` its time (UTC `Z`). Mutant: `lines[0]` → the re-add's sha → red (pasted).
5. **MAJOR-5 (`pkgs/evidence/migrate_reviews.py:60`) — "The 'none' heading rule reads only ##-level headings, missing the corpus's ### Minors":** `if ln.strip().lower() not in {f"## {w}" for w in headings}:` restricts the section's "a heading line whose text is Major/Majors/Minor/Minors" to two hashes; the section's own Facts count `### Minors` once in the corpus, so T3M would write `minors: null` where the contract says 0. Close: a heading is `^#{1,6}\s+(major|majors|minor|minors)\s*$` case-insensitively; `majors-none.md` gains a `### Minors` heading followed by `None.` (and the `## Majors` + `none` it has) → `majors: 0`, `minors: 0`. Mutant: restrict to `##` → `minors: null` → red; drop `re.I` → red.
6. **MINOR-7 of the review, carried because the Global Constraints require it — "The commit body states the why but pastes neither the red nor the green":** this commit's body pastes, under its command line, the red of each new or changed assertion of items 1–5 on the cherry-picked tree (the bats count with T3's weakening reverted, the trailing-newline assertion, the two-`review_path` fixture, the three-commit fixture, the `### Minors` fixture), the five mutant runs, and the green counterparts (`pytest tests/evidence -q`, `bats tests/unit/80-seat-driver.bats tests/unit/84-factory-integrate-reviews.bats`, the three checks' last lines, `migrate_reviews.py . --check`'s summary line on the clone's live `docs/reviews`).

The review's other six MINORs (`review_path` synthesised for seat rows, the section's function names not used, the bare `N killed` fallback and the `(none)`/`None.` forms untested, `realpath` untested, the H1-verdict rule nested under `has_block`) are recorded, not owed here.

- [ ] **Step 1: Fresh workspace** — the cherry-pick and the three `git checkout HEAD --` files above; `git status --short` shows T3's files staged, the bats file at main's version.
- [ ] **Step 2: Write the failing tests** — items 1–5's assertions and fixtures; **run red**: `nix develop -c bats tests/unit/80-seat-driver.bats` (the three tests fail on the extra ingest line until item 1's assertions are in; then pass — paste both), `nix develop -c pytest tests/evidence/test_migrate_reviews.py tests/evidence/test_ingest_reviews.py -q` → the four new assertions red with their lines (paste).
- [ ] **Step 3: Change the code** — `migrate_reviews.py` (the text splice; the heading regex), `ingest_reviews.py` only if item 4's assertion demands it (the rule is already `lines[-1]`; say so), nothing else unless a run of Step 4 demands it (say what and why in the body).
- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c treefmt`; `nix develop -c pytest tests/evidence -q`; `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/84-factory-integrate-reviews.bats`; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `… unit`; `… lint`; `nix develop -c githooks/pre-commit`; `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check; echo exit=$?` (lists the files, exit 1, tree unchanged — paste the summary line); then the five mutants applied, shown red with their lines, reverted — pasted.
- [ ] **Step 5: One commit** with the subject below, the two trailers, the body carrying every paste of item 6; end the reply with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them.

**Tests:** T3's table unchanged except rows 12, 14 and 19 (rewritten as items 2, 4 and 3 state) plus item 1's two bats assertions and item 5's heading fixture.

**touches:** pkgs/evidence/ingest_reviews.py, pkgs/evidence/migrate_reviews.py, tests/evidence/test_ingest_reviews.py, tests/evidence/test_migrate_reviews.py, tests/evidence/fixtures/reviews-migrate/h1-markers.md, tests/evidence/fixtures/reviews-migrate/h1-no-markers.md, tests/evidence/fixtures/reviews-migrate/block-five-keys.md, tests/evidence/fixtures/reviews-migrate/legacy-h1.md, tests/evidence/fixtures/reviews-migrate/migrated.md, tests/evidence/fixtures/reviews-migrate/majors-none.md, tests/evidence/fixtures/runs/r1/K1.review.md, tests/evidence/fixtures/runs/r1/K2.review.md, tests/evidence/fixtures/runs/r1/K3.review.md, tests/evidence/fixtures/runs/r1/K4.review.md, tests/unit/84-factory-integrate-reviews.bats, pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, tools/factory/seat/factory-integrate, tests/unit/80-seat-driver.bats
**acceptance:** evidence-unit, unit, lint
**commit subject:** `evidence: the gates stream, fix round — T2's bats pins strengthened, the migration keeps every body byte, the gates key discriminated, the add-commit rule under two adds, headings at any level (test: evidence-unit, unit, lint)`

### T2b (code, S) — T2 fix round: the submit-failed arm tested with its precedence, the error_class order stated once on the tests' side, the last status line and the run/key refusal pinned, the reds and greens in the body

**dependsOn:** (T2)

Typed by the orchestrator on 2026-09-07 from the tel2 gate, `docs/reviews/2026-09-07-opus-review-tel2-T2.md` (REJECTED; plan_defect implementer, secondary missing-case; 38 mutants, 30 killed; the three acceptance checks green on a fresh clone and with `--rebuild`; all 18 new tests shown red before green). One MAJOR and a plan defect the review recorded without charging the seat. Rule A1: this is T2's one fix round; a second rejection re-plans.

**Fresh workspace, step 1 (before anything else):** the workspace is a fresh clone of main; bring T2's commit in uncommitted with `git fetch -q /home/dalhaka/factory/ws/tel2/T2 task/T2 && git cherry-pick -n FETCH_HEAD` (the branch's one commit cc224a7), then take main's copies of the two generated files: `git checkout HEAD -- docs/OPERATIONS.md docs/MAP.md && git add docs/OPERATIONS.md docs/MAP.md` (the pre-commit hook regenerates the queue block; `python3 pkgs/evidence/repomap.py --root . write` regenerates the map at Step 4). Everything below is edited on top of that; ONE commit at the end with this section's subject — T2's subject is never reused.

**Contract — the review's items carried verbatim, each closed as stated:**

1. **MAJOR-1 (`tools/factory/seat/factory-lib.sh:110-115`) — "The synth=submit -> submit-failed arm of factory_error_class has no test; the row-14 named mutant survives":** deleting `case $synth in submit) printf 'submit-failed\n'; return 0;; esac` leaves all 80 tests in `tests/unit/80-seat-driver.bats` green; the fourteen `factory_error_class` invocations pass `''`, `nearmiss`, `none`, `zero-commits` or `echo` as `synth`, never `submit`; the stated precedence pair (`submit` beating `exit_code` 124) is unasserted. Close: two bats assertions in the `error_class` group — `factory_error_class '$log' failed 124 100 100 submit ''` → `submit-failed` (the pair: `submit` beats exit 124) and `factory_error_class '$log' done 0 100 100 submit ''` → `submit-failed` (`submit` beats the `done` guard). Mutants: delete the arm → both red; move the arm below the exit-124 rule → the first red (pasted).
2. **The plan defect the review recorded (the section's Interfaces order contradicts rows 4, 5 and 14) — stated once, on the side the tests demand and the code implements:** the rule of `factory_error_class`, in order, is `synth` = `submit` → `submit-failed`; `exit_code` = 124 → `timeout`; `status` = `done` → `none`; `synth` in `nearmiss|none` → `no-result-line`; `demoted` in `zero-commits|echo` → `template-echo`; then the last 4,000 bytes of the log — both `402` and `budget_exhausted` → `budget-402`, `\b(502|503|529)\b|upstream|provider` → `provider-error`, `UNKNOWN_MODEL` → `unknown-model`; `wall_s` < 10 and `events` < 50 → `boot-failure`; otherwise `none`. This supersedes the Interfaces bullet at T2's `factory_error_class` line for the two rules it moved (the synth and demoted rules precede the tail patterns). The body pastes the function's branch sequence as `grep -n` prints it and the two reorder mutants of rows 4 and 5 going red (the demoted check after the tail patterns → row 4's `provider`-tail case red; the synth check after the tail patterns → row 5's `503`-tail case red).
3. **MINOR-3 (`pkgs/evidence/ingest_result.py:233`) — "'the LAST FACTORY-RESULT status= line' is not pinned; mutant O3 ([-1] -> [0]) survives":** close: a fixture `.result` with two `FACTORY-RESULT status=` lines (`failed` first, `done` last) → `status done`; mutant `[0]` → red (pasted).
4. **MINOR-6 (`pkgs/evidence/ingest_result.py:231-232`) — "The 'no run:/key: line' refusal arm has no test; mutant O6 (delete the guard) survives":** close: a fixture without a `run:` line and one without a `key:` line → each refused (stderr as the section states, counted refused, nothing written); mutant: delete the guard → red (pasted).
5. **MINOR-7 — "The commit body states the why and carries both trailers but pastes neither the red nor the green":** this commit's body pastes, under its command line, each new assertion of items 1, 3 and 4 red on the cherry-picked tree and green after, the four mutant runs of items 1–4, the two reorder runs of item 2, and the green counterparts (`pytest tests/evidence/test_ingest_result.py -q`, `bats tests/unit/80-seat-driver.bats --filter error_class`, the three checks' last lines).

The review's MINORs 1, 2, 4 and 5 (the seven diffstat forms unparametrised, `usage: {}` unfixtured, `route: explicit` unfixtured, the `factory_py` branch unexercised) are recorded, not owed here.

- [ ] **Step 1: Fresh workspace** — the cherry-pick and the two `git checkout HEAD --` files above; `git status --short` shows T2's files staged.
- [ ] **Step 2: Write the failing tests** — the two bats assertions of item 1, the fixtures of items 3 and 4; **run red** on the cherry-picked tree with the submit arm temporarily deleted (item 1's assertions fail; paste), then restored; the `[0]` and guard-deletion mutants likewise (paste).
- [ ] **Step 3: Change the code** — nothing is expected to change in `factory-lib.sh` or `ingest_result.py` beyond what a red of Step 2 demands (say what and why in the body); the Interfaces order of item 2 is already what the code does — prove it with the `grep -n` paste.
- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c treefmt`; `nix develop -c pytest tests/evidence -q`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `… unit`; `… lint`; `nix develop -c githooks/pre-commit`; then every mutant of items 1–4 applied, shown red with its line, reverted — pasted.
- [ ] **Step 5: One commit** with the subject below, the two trailers, the body carrying every paste of item 5; end the reply with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them.

**Tests:** T2's table unchanged; row 14 gains the two `submit` cases of item 1; rows 3 and 8's fixtures gain the two-status-line and the missing-`run:`/`key:` cases of items 3 and 4.

**touches:** pkgs/evidence/ingest_result.py, tests/evidence/test_ingest_result.py, tests/evidence/fixtures/results/done.result, tests/evidence/fixtures/results/status-pass.result, tests/evidence/fixtures/results/hostile-checks.result, tests/evidence/fixtures/results/template-echo.result, tests/evidence/fixtures/results/timeout.result, tests/evidence/fixtures/results/submit-failed.result, tests/evidence/fixtures/results/no-result-line.result, tests/evidence/fixtures/results/classified.result, tests/evidence/fixtures/results/two-status-lines.result, tests/evidence/fixtures/results/no-run-line.result, tests/evidence/fixtures/results/no-key-line.result, tools/factory/seat/factory-lib.sh, tools/factory/seat/factory-task, tests/unit/80-seat-driver.bats
**acceptance:** evidence-unit, unit, lint
**commit subject:** `evidence: the tasks stream, fix round — the submit-failed arm tested with its precedence, the error_class order stated once, the last status line and the run/key refusal pinned (test: evidence-unit, unit, lint)`

### T3Mb (docs, S) — T3M fix round: the migration re-run on current main and committed with the two trailers after a blank line, Step 3's outputs in the body

**dependsOn:** (T3M)

Typed by the orchestrator on 2026-09-07 from the tel3 gate, `docs/reviews/2026-09-07-opus-review-tel3-T3M.md` (REJECTED, Sonnet — the docs route; plan_defect implementer). The migration output was correct, idempotent and confined to `docs/reviews` (re-derived by the reviewer: `checked: 172; would change: 145` on base, `0` on HEAD; `migrated: blocks added 119, keys added 78, unchanged 0, skipped legacy 27`; 145 files, 718 insertions, nothing removed; both mutants killed); the one MAJOR is the commit's shape. Rule A1: this is T3M's one fix round.

**Fresh workspace, step 1 (before anything else):** the workspace is a fresh clone of main; bring T3M's commit in uncommitted with `git fetch -q /home/dalhaka/factory/ws/tel3/T3M task/T3M && git cherry-pick -n FETCH_HEAD` (the branch's one commit 6e57a00; only `docs/reviews` files, no conflict expected — if one appears on a review file, take main's copy with `git checkout HEAD -- <file>`; the re-run below rewrites it anyway). Main has gained gate reviews since that commit's base (at least `2026-09-07-opus-review-tel3-T3M.md`, and possibly `…-tel3-T10a.md`), which lack the migrated keys.

**Contract — the review's items carried verbatim, each closed as stated:**

1. **MAJOR-1 (commit 6e57a00's message) — "Commit's two trailers are not recognized as git trailers — no blank line before them":** `git log -1 --format='%B' HEAD | git interpret-trailers --parse` printed nothing; the body's last prose line ran directly into `Generated-By:`. Close: this commit's message is the subject, a blank line, the body, a blank line, then the two trailer lines (`Generated-By: …` and `Co-Authored-By: …`) as the WORKSPACE RULES state them. After committing, run `git log -1 --format='%B' | git interpret-trailers --parse` and confirm it prints exactly the two trailer lines; if it prints fewer, amend the message once (`git commit --amend` on your own unpushed commit is allowed for this purpose) and re-check; the parse output cannot live in the message it parses, so the FACTORY-NOTES line of the reply names the two trailers as parsed.
2. **MINOR-1 — "Commit body pastes no red/green terminal output (narrative only)":** the body pastes, each under its command line, the outputs of Step 1 (the `--check` list's last three lines and `exit=1` before the run), Step 2 (the `migrated:` line) and Step 3 (`--check` → `checked: N; would change: 0`, `exit=0`; `tasks.py check` silent; `git diff --cached --stat | tail -1`; the removed-lines count `0`; the legacy count `27`).
3. **The re-run on current main:** after the cherry-pick, run `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check; echo exit=$?` (it names the reviews added since T3M's base — expected one or two files, `exit=1`), then `nix develop -c python3 pkgs/evidence/migrate_reviews.py .` (the `migrated:` line; the counts are what they are today), then Step 3 again: `--check` → `would change: 0`, `exit=0`. Every changed file is under `docs/reviews`; nothing else in the diff; `git add docs/reviews` only (never `-A`).

- [ ] **Step 1: Fresh workspace** — the cherry-pick line above; then the `--check` of item 3 (red: the newer reviews listed).
- [ ] **Step 2: Run the migration** — item 3's real run.
- [ ] **Step 3: Prove it** — `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check; echo exit=$?` → `exit=0`, `checked: N; would change: 0`; `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → prints nothing; `git diff --cached --stat | tail -1` → only insertions; `git diff --cached -- docs/reviews | grep '^-' | grep -v '^---' | wc -l` → 0; `grep -L '^reviewer:' docs/reviews/*opus-review*.md | wc -l` → 27; `nix develop -c githooks/pre-commit` (the queue block may regenerate — `git add docs/OPERATIONS.md` is NOT done: the block does not belong to this task; if the hook regenerates it, leave the file unstaged and say so in the body).
- [ ] **Step 4: Commit** — `git add docs/reviews`; the subject below; the message shape of item 1; the parse check of item 1; end the reply with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them.

**Tests:** Step 3's commands are the assertions; mutants as T3M's: a hand edit to one migrated file (`majors: 1` → `majors: one`) turns `tasks.py check` red; a second run producing a diff turns `--check` red.

**touches:** docs/reviews
**acceptance:** lint
**commit subject:** `docs: reviews — reviewer and counts in every gate review's front-matter block, by migrate_reviews, fix round: the trailers after a blank line (test: lint)`
