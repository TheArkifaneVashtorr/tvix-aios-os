---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run sc1, task G5 — REJECTED

Reviewed 2026-09-05 from a throwaway clone of `/home/dalhaka/factory/ws/sc1/G5`
(branch `task/G5`, head `412076d43241`, one commit on base `e5e0061`). Plan
section: `docs/superpowers/plans/2026-09-05-session-context.md` `### G5 (code, S)`.
The plan's trailing "Wave 1 landed … amendments to G5" block was outside the
section and is not judged here.

## Summary

The CLI half of G5 is good work: `evidence tasks …` / `evidence repomap …` pass
argv through exactly as specified, `--store` is forwarded only when given (both
`--store X` and `--store=X`), `evidence --help` lists both, all three acceptance
gates pass, and the `docs/MAP.md` check-name assertion is genuinely load-bearing
— it compares against the flake's **real** `builtins.attrNames self.checks.${system}`
and kills a mutant that `repomap.py`'s own regex parser cannot see. Both files
outside the section's `touches` were forced by the section's own tests, are
minimal, and were disclosed.

The rejection is one thing: **the `tasks.py check` guard added to the `lint`
runCommand is vacuous — it can never fail.** `tasks.py` resolves repos from
`docs/ledger/repos.toml` (`path = "~/nixos-agent-env"`, `os.path.expanduser`),
not from `--root`; `--root` only locates `repos.toml`/`plan-status.toml`/`claims.toml`.
Inside the nix sandbox that path does not exist, so the checker finds zero plans
and exits 0 unconditionally. Proven: a `**dependsOn:** ZZZ` planted in the tree's
own plan file left `nix build .#checks.x86_64-linux.lint` at exit 0. The same
wiring in `githooks/pre-commit` reads the operator's live `~/nixos-agent-env`
rather than the tree being committed — in this very workspace the hook passed
while the workspace's plan was broken. The commit subject's claim "the hook and
lint check the task graph" is therefore half untrue, and the gate's required red
demonstration (c) cannot be reproduced.

The wiring was prescribed verbatim by the section's Step 4, so this is an
inherited design defect rather than invention — but a guard shipped into `lint`
that structurally cannot fail is exactly the vacuity this gate rejected in ev3 E9,
and the fix is small and stays inside G5's four files.

## Checks

| gate | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | exit 0 |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | exit 0 |
| commit gate | `nix develop -c githooks/pre-commit` | exit 0 |
| ruff | `nix develop -c ruff check` + `ruff format --check pkgs/evidence tests/evidence` | clean, 12 files already formatted |

Commit shape: one commit on `e5e0061`; subject `diff`s byte-identical to the
section's `**commit subject:**`; `Co-Authored-By: Claude Fable 5.1` present
(plus an allowed `Generated-By:`). Clone left clean after every mutation.

Interfaces, verified in-process against the shipped `main`:

```
with --store  -> ['--store', '/S1', '--root', '.', 'brief']
with --store= -> ['--store', '/S2', 'brief']
no --store    -> ['brief']
repomap args  -> ['--root', '.', 'check']      # --store correctly dropped
```

`evidence --help` lists `tasks` and `repomap` with their help strings. Hook lines
sit immediately after the `claims.py validate` line and use
`--runs-dir /nonexistent --store /nonexistent` as specified; the lint copy uses
the identical arguments plus the check-name assertion, placed before `touch $out`.
`nativeBuildInputs = lintTools ++ [ pkgs.python3 ]` (python3 was not previously
in `lintTools`; adding it was correct per Step 4).

The Nix assertion was read, not taken on trust:

```nix
checkNamesFile = pkgs.writeText "check-names" (
  nixpkgs.lib.concatMapStrings (n: n + "\n") (builtins.attrNames self.checks.${system})
);
```

Real attribute names, not a hand list. `attrNames` does not force the check
values, so `lint` referring to the set that contains it does not recurse — the
build confirms this.

Stdlib only (`argparse, os, sys, pathlib, re` and the pre-existing set). No new
`2>/dev/null` on a gated command, no `--no-verify`, nothing written outside the
repo.

## Red before green

- **(a) pass-through** — `git checkout e5e0061 -- pkgs/evidence/evidence.py`,
  then `pytest -k pass_through`:
  `assert (2 == 0)` … `evidence: error: argument cmd: invalid choice: 'tasks'
  (choose from 'record', 'record-check', 'latest-check', 'bundle')`. Restored.
  Red reproduces exactly as the section's Step 2 predicts.
- **(b) check-name assertion** — deleted `- lane-polkit-unit` from `docs/MAP.md`'s
  Checks section; `nix build .#checks.x86_64-linux.lint` failed with a `diff -u`
  showing `-lane-polkit-unit` and then, verbatim:
  `lint: docs/MAP.md Checks section differs from the flake's checks (regenerate:
  python3 pkgs/evidence/repomap.py write)`. Restored.
- **(c) task graph** — **DID NOT REPRODUCE.** `**dependsOn:** G4, G2, G3, ZZZ`
  planted in `docs/superpowers/plans/2026-09-05-session-context.md`:
  `nix develop -c githooks/pre-commit` → exit **0**;
  `nix build .#checks.x86_64-linux.lint -L --no-link` → exit **0**.
  Root cause isolated, not guessed:
  - with a one-repo `--repos` file pointing at the clone →
    `tasks: nixos-agent-env/G5 dependsOn ZZZ: unknown key`, exit 1 (the checker
    itself is fine);
  - with `HOME` pointed at an empty directory (the sandbox's situation) →
    exit 0, no output, zero plans scanned.
  Restored.

## Mutation table

| # | mutation | expected killer | outcome |
|---|---|---|---|
| 1 | `forwarded = rest[1:]` (drop `--store` forwarding) | `test_cli_tasks_and_repomap_pass_through` | **SURVIVES** — 1 passed. The store path is a nonexistent tmp dir either way, so the assertion cannot see the difference. Forwarding is correct by inspection but untested. |
| 2 | add `"zz-probe" = pkgs.runCommand …;` to `checks.${system}` — a name `repomap.flake_check_names` cannot parse (it sees 38 names; the flake really has 39) | check-name assertion (and *not* `repomap check`) | killed — lint fails with `-zz-probe` in the diff and the specified message. Proves the assertion uses real `attrNames` and is **not** redundant with `repomap check`. |
| 3 | `docs/MAP.md`: `tests/evidence — 7 files` → `6 files` (outside the Checks section) | `repomap.py --root . check` in lint | killed — `repomap: docs/MAP.md is stale …`, lint exit 1. |
| 4 | same staleness, hook path | `repomap.py --root . check` in `githooks/pre-commit` | killed — hook exit 1 with the same message. So dropping the hook's repomap line still leaves lint as a real backstop. |
| 5 | broken task graph in the tree (red (c)) with the hook's `tasks.py` line removed | "the flake lint copy must" catch it | **SURVIVES** — lint never catches it, because lint's copy is itself vacuous. Nothing gates the task graph of the tree being committed. |
| 6 | sparse-tree tolerance: `build_map` on an empty root, and on a full repo copy with `flake.nix` removed | should not mask a defect | acceptable — empty root yields all-empty sections, `check` still exits 1 with `docs/MAP.md is stale`; the flake-less copy yields `checks: []` and `check` exit 1. The tolerance converts a crash into "stale", it does not turn a broken tree into a pass. The one degraded path is `repomap write` against a wrong/sparse `--root`, which now silently writes a near-empty map instead of crashing; on the real repo the check-name assertion would then fail loudly. Minor. |

## Extra touches

Two files outside the section's `touches` list.

- **`pkgs/evidence/repomap.py`** (9 lines: three `iterdir()` → `glob("*")`, one
  guarded `flake.nix` read). **Forced** — the section's own Step 1 test runs
  `repomap --root <tmp_path> check` on a bare tmp dir and asserts exit 1 with
  `"docs/MAP.md is stale"` in stderr; at base, `(root / "pkgs").iterdir()` raises
  `FileNotFoundError` and the test sees a traceback instead. **Minimal** — the
  smallest idiomatic change that makes a missing directory an empty listing.
  **Disclosed** in FACTORY-NOTES and in the commit body. Behaviour verified above
  (mutation 6): it does not mask a real error in `check` mode. Accepted.
- **`docs/MAP.md`** (2 lines: `tests/evidence` 3 → 7, `tests/lint` added).
  **Forced** — the commit adds `repomap.py --root . check` to the pre-commit hook
  and to `lint`; the map was stale from the `tests/` tree that landed after G2, so
  the gate the task itself installs would refuse the commit. **Minimal** — the file
  is byte-identical to `repomap.py print` for this tree (the hook's own
  `repomap check` passes). **Disclosed**. Accepted.

Both are forced, minimal and disclosed; neither is a rejection reason.

## Findings

1. **MAJOR — the `tasks.py check` guard in `lint` is vacuous, and in
   `githooks/pre-commit` it checks the wrong tree.** `flake.nix` and
   `githooks/pre-commit` both run `python3 pkgs/evidence/tasks.py --root .
   --runs-dir /nonexistent --store /nonexistent check`, but `--root` only locates
   `docs/ledger/repos.toml`; the repos it then scans come from that file's
   `path = "~/nixos-agent-env"` (expanded through `$HOME`). Consequences, all
   measured:
   - in the `lint` sandbox the path does not exist → zero plans → **always exit 0**;
     a plan with `dependsOn: ZZZ` in the copied source passes lint;
   - run from a factory workspace, the commit gate silently validates the
     operator's live repo instead of the tree being committed — a false pass for a
     broken workspace plan, and a false *failure* if the live repo happens to be
     mid-edit;
   - only when the hook runs from `~/nixos-agent-env` itself do the two paths
     coincide and the guard bite.
   The wiring is verbatim from the section's Step 4, so this is inherited, not
   invented — but the commit subject and body assert that the hook and lint
   "check the task graph", and for lint that is not true at any input.
2. **MINOR — `--store` forwarding has no load-bearing test** (mutation 1 survives).
   The section dictated the test verbatim, so this too is inherited; the behaviour
   itself is correct.
3. **MINOR (note, no fix required) — `repomap write` against a sparse or mistyped
   `--root` now writes a degraded map instead of crashing.** Only the `write` path
   is affected; `check` still fails loudly. Worth a line in the runbook rather than
   a code change.
4. Not counted against G5 (out of section, per the gate brief): `_count_files`
   ignores `__pycache__`/`.pytest_cache` but not `.ruff_cache`, and counts
   untracked files rather than `git ls-files` — so a stray scratch file under
   `tests/` will now block a commit through the new `repomap check` line. This is
   one of the plan's un-delivered amendments; flagging it only because the hook
   line lands in this commit and the operator will feel it first.

## Deviations

- Two files outside `touches` (`pkgs/evidence/repomap.py`, `docs/MAP.md`) — both
  forced by the section's own tests, minimal, disclosed. Accepted, see above.
- No other deviation: commit shape, subject, trailers, stdlib-only, ruff, the
  `2>/dev/null` and `--no-verify` bans, and the "nothing outside the repo" rule
  are all clean.

### What a fix round G5b must contain

Bounded, and it stays inside G5's four files.

1. Make both copies of the task-graph guard inspect **the tree at `--root .`**,
   not `$HOME`. Simplest within `touches`: have `githooks/pre-commit` and the
   `lint` runCommand write a one-repo repos file for the tree and pass it, e.g.

   ```bash
   repos=$(mktemp); printf '[[repo]]\nname = "nixos-agent-env"\npath = "%s"\n' "$PWD" >"$repos"
   python3 pkgs/evidence/tasks.py --root . --repos "$repos" --runs-dir /nonexistent --store /nonexistent check
   ```

   (do not change `tasks.py` — its `--root`/`repos.toml` semantics are G1/G3's and
   belong in the re-plan). Keep `--runs-dir /nonexistent --store /nonexistent`.
2. Prove it red, and record both outputs in FACTORY-NOTES: plant
   `**dependsOn:** ZZZ` on a typed task in a plan file, then show
   `nix develop -c githooks/pre-commit` **and**
   `nix build .#checks.x86_64-linux.lint -L --no-link` both failing with
   `tasks: nixos-agent-env/G5 dependsOn ZZZ: unknown key`; restore.
3. Kill mutation 1: add a load-bearing assertion that `--store` is forwarded —
   an in-process test of `evidence.split_global` (`("--store", "/S", "tasks",
   "brief") -> ("/S", ["tasks", "brief"])`, and `("tasks", "brief") -> (None, …)`)
   plus a capture of what `tasks.main` receives. Show it red against
   `forwarded = rest[1:]`.
4. Re-run all three gates; nothing else in the commit changes. Keep the same
   commit subject.
