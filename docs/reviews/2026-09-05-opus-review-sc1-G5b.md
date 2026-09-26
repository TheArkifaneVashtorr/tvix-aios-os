---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run sc1, task G5b — APPROVED

Reviewed 2026-09-05 from a throwaway clone of `/home/dalhaka/factory/ws/sc1/G5b`
(branch `task/G5b`, head `548eb2333e0d`, one commit on base `0879294`). Plan
sections: `docs/superpowers/plans/2026-09-05-session-context.md` `### G5 (code, S)`,
"## Fix round after the wave-1 gates", `### G5b (code, S)`. Prior gate:
`docs/reviews/2026-09-05-opus-review-sc1-G5.md` (REJECTED).

## Summary

The MAJOR is fixed, and fixed at the right place. Both copies of the task-graph
guard now write a one-repo TOML naming `$PWD` and pass it as `--repos`, so the
checker scans the tree under test instead of resolving `~/nixos-agent-env` out of
`docs/ledger/repos.toml`. `tasks.py` is untouched, as the section required — the
`--repos` option already existed from G1/G3. I planted `**dependsOn:** ZZZ` on E1
of `docs/superpowers/plans/2026-09-05-evidence-store.md` in my own clone (the live
repo's plan was and stayed clean, so a pass could only have come from reading the
wrong tree): the commit hook exits 1 with
`tasks: nixos-agent-env/E1 dependsOn ZZZ: unknown key`, and `nix build
.#checks.x86_64-linux.lint` fails with that same line in the builder log. Deleting
only the `--repos` argument from each copy restores the old vacuity — hook exit 0,
lint exit 0 with the plan still broken — which pins the repos file as the
load-bearing part of the fix rather than incidental.

The MINOR is fixed too: the new `test_cli_tasks_store_forwarded_to_tasks_main`
dies under the `forwarded = rest[1:]` mutation with exactly `assert 'ready' ==
'recorded'`. It is an end-to-end subprocess test rather than the in-process
`split_global` unit the rejection sketched — stronger, not weaker: it drives the
real `evidence` binary and reads the state `tasks.main` derives from the store.
Its fixture run row matches `read_recorded`'s real schema (`plan`,
`tasks[].key`), so it is not testing a fiction.

The delta against G5's `412076d` is exactly the three things it should be: the
guard rewiring in `githooks/pre-commit` and `flake.nix`, the forwarding test
appended to `test_evidence.py`, and two extra `docs/MAP.md` lines. `evidence.py`
and `repomap.py` are byte-identical patches to G5's. All six touched files are in
G5b's declared `touches`. Everything G5 proved still holds.

## Checks

| gate | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | exit 0; builder log `57 passed in 3.41s` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | exit 0 |
| commit gate | `nix develop -c githooks/pre-commit` | exit 0 |
| pytest | `pytest tests/evidence -q -p no:cacheprovider` | 21 passed in `test_evidence.py`, 57 passed across `tests/evidence` |

Commit shape: exactly one commit on `0879294`; `git show --stat HEAD` touches only
`docs/MAP.md`, `flake.nix`, `githooks/pre-commit`, `pkgs/evidence/evidence.py`,
`pkgs/evidence/repomap.py`, `tests/evidence/test_evidence.py` — a subset of G5b's
`touches`. Subject byte-identical to G5's `412076d` **and** to the plan's
`**commit subject:**` (all three md5 `b246da6b…`). `Co-Authored-By: Claude Fable
5.1` present, `Generated-By:` extra. Clone left clean after every mutation
(`git status --porcelain` empty each time).

The guard lines, read rather than trusted — both name the tree, not `$HOME`:

```bash
# githooks/pre-commit
repos_file="$(mktemp)"
printf '[[repo]]\nname = "nixos-agent-env"\npath = "%s"\n' "$PWD" >"$repos_file"
python3 pkgs/evidence/tasks.py --root . --repos "$repos_file" --runs-dir /nonexistent --store /nonexistent check
rm -f "$repos_file"
python3 pkgs/evidence/repomap.py --root . check
```

`flake.nix`'s `lint` copy is the same four lines (after `cp -r ${self} src && cd
src`, so `$PWD` is the sandbox's copy of the tree), followed unchanged by the
check-name assertion and `repomap.py --root . check`. `--runs-dir /nonexistent
--store /nonexistent` are retained in both: status sources still cannot influence
commit admissibility. `nativeBuildInputs = lintTools ++ [ pkgs.python3 ]` as in G5.

`repomap check` is green on the tree, and `docs/MAP.md` is byte-identical to
`repomap.py --root . print`. The MAP.md delta against base is four lines: G5's two
(`tests/evidence` 3 → 7, `tests/lint` added) plus exactly two G6 effects —
`tests/unit` 11 → 12 (G6 added `tests/unit/90-session-start.bats`) and
`tools/session-start.sh` (present at base `0879294`, absent from base's map because
G6 landed before this `repomap check` gate existed). Nothing else moved.

Stdlib only; no new `2>/dev/null` on a gated command, no `--no-verify`, no writes
outside the repo (the guards' only out-of-tree write is a `mktemp` file under
`TMPDIR`). ruff and treefmt clean via the hook.

## Red before green

- **(c) planted dependency — hook.** `**dependsOn:** ZZZ` on E1 of
  `docs/superpowers/plans/2026-09-05-evidence-store.md`;
  `nix develop -c githooks/pre-commit` → `tasks: nixos-agent-env/E1 dependsOn ZZZ:
  unknown key`, exit **1**. This is the red the G5 gate could not reproduce.
- **(c) planted dependency — lint.** Same plant, `git add`ed;
  `nix build .#checks.x86_64-linux.lint -L --no-link` → exit **1**, builder log
  line `lint> tasks: nixos-agent-env/E1 dependsOn ZZZ: unknown key`. Reverted;
  tree clean.
- **forwarding.** `forwarded = rest[1:]` → `pytest -k store_forwarded` fails with
  `AssertionError: assert 'ready' == 'recorded'`. Restored → 21 passed.
- **(a) pass-through (G5's red, re-run).** `git checkout 0879294 --
  pkgs/evidence/evidence.py`, `pytest -k pass_through` → `assert (2 == 0)` …
  `evidence: error: argument cmd: invalid choice: 'tasks' (choose from 'record',
  'record-check', 'latest-check', 'bundle')`. Restored.
- **(b) check-name assertion (G5's red, re-run).** Removed `- lane-polkit-unit`
  from `docs/MAP.md`'s Checks section → lint exit 1 with a `diff -u` showing
  `-lane-polkit-unit` and then `lint: docs/MAP.md Checks section differs from the
  flake's checks (regenerate: python3 pkgs/evidence/repomap.py write)`. Restored.

## Mutation table

| # | mutation | expected killer | outcome |
|---|---|---|---|
| 1 | `forwarded = rest[1:]` (drop `--store` forwarding) | `test_cli_tasks_store_forwarded_to_tasks_main` | **killed** — `assert 'ready' == 'recorded'`. G5's surviving mutant 1 is dead. |
| 2 | drop `--repos "$repos_file"` from the **lint** copy, plan still carrying `dependsOn: ZZZ` | the fix itself | **survives, as designed to show** — lint exit **0**. Proves the repos file is exactly what makes the guard bite; without it the guard is the vacuous one G5 shipped. |
| 3 | drop `--repos "$repos_file"` from the **hook** copy, same plant | the fix itself | **survives, as designed to show** — hook exit **0** while the tree's plan is broken and the live repo's is clean. Reproduces the original defect precisely. |
| 4 | revert `evidence.py` to base `0879294` | `test_cli_tasks_and_repomap_pass_through` | killed — `invalid choice: 'tasks'`. |
| 5 | remove `- lane-polkit-unit` from `docs/MAP.md` Checks | lint check-name assertion | killed — exit 1, specified message. |
| 6 | `elif False and tok.startswith("--store=")` (disable the `--store=X` spelling) | any test | **survives** — 57 passed. The `--store=` spelling is correct by inspection (probe below) but untested. Inherited from G5's dictated test; the rejection's finding 2 asked only that `--store` forwarding be pinned, and it now is. MINOR. |

Regression probe of G5's proven interfaces, run in-process against the shipped
`main` with `tasks`/`repomap` stubbed:

```
with --store  -> ['--store', '/S1', '--root', '.', 'brief']
with --store= -> ['--store', '/S2', 'brief']
no --store    -> ['brief']
repomap args  -> ['--root', '.', 'check']      # --store correctly dropped
split_global  -> ('/S', ['tasks', 'brief'])  and  (None, ['tasks', 'brief'])
```

`evidence --help` still lists `tasks` and `repomap` with their help strings.

## Findings

All MINOR; none blocks.

1. **The guard's scope narrows from five repos to one.** `docs/ledger/repos.toml`
   lists `nixos-agent-env`, `media`, `gaming`, `nixos-skill`, `dsh-harness`; the
   one-repo file passed to `--repos` drops the four siblings, so the hook no
   longer validates their plans. This is correct for a commit gate — a commit to
   *this* tree should not be blocked by a sibling's plan text — and `tasks.check`
   resolves `dependsOn` per repo (`keys`/`roots` are built inside the per-repo
   loop), so no cross-repo dependency can be broken by the narrowing. Worth
   knowing: sibling plan hygiene is now only checked by `evidence tasks check`
   run by hand.
2. **`--store=X` has no test** (mutation 6). Behaviour verified correct by probe.
3. **`rm -f "$repos_file"` is skipped when the checker fails.** Both copies run
   under `errexit`, so a red gate leaves a two-line temp file behind. Harmless;
   a `trap` would be tidier.
4. **The TOML is built by `printf` with an unquoted `$PWD`.** A repository path
   containing `"` or `\` would produce invalid TOML. No factory or host path does;
   noting it as a latent sharp edge, not a defect.
5. Carried forward from the G5 gate, unchanged and still not counted against this
   task: `repomap write` against a sparse `--root` writes a degraded map instead
   of crashing (`check` still fails loudly), and `_count_files` counts untracked
   files, so a stray scratch file under `tests/` will block a commit through the
   new `repomap check` line. Both belong to the plan's un-delivered amendments.

## Deviations

None. G5b's `touches` names all six files this commit changes; the commit is a
single one on the fresh base with the plan's byte-identical subject and the
required trailer; no `amend`; nothing written in the workspace by this review.
The fix-round rule's "prove it load-bearing by mutation" was satisfied for both
findings, and both reds were recorded in FACTORY-NOTES verbatim, matching what I
reproduced independently.
