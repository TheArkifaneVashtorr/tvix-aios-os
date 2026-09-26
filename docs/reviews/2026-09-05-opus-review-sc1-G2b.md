---
reviewer: opus
majors: null
minors: null
mutants_total: 16
mutants_killed: 15
---
# Opus gate — seat run sc1, task G2b — APPROVED

Branch head `a294665047ef` (`~/factory/ws/sc1/G2b`, `task/G2b`, base `7b23aa1`). Reviewer: Opus, high effort, throwaway clone; checks re-run by ref; the sibling `G2` workspace and the live repo were only read.

## Summary

APPROVED. Both majors from `docs/reviews/2026-09-05-opus-review-sc1-G2.md` are closed and every minor with it. The single commit's subject is now byte-identical to the plan's G2 **commit subject** (`diff` against a literal copy: no output). The 8-space indent anchor is load-bearing: the `FLAKE` fixture gained `nested = { inner-child = 1; }` inside the checks block, and relaxing the regex to any indent now fails two tests — against the real `flake.nix` that same relaxation still yields **86** names instead of 38, so the guard the review measured is the one the fixture now protects. The block-terminating `break` is load-bearing too (`other = 3;` became `other-block = { zzz = 1; }`, so removing the break leaks `zzz`). The plan's Step-3 layout is adopted verbatim (`## NixOS modules`, `## Checks (nix build .#checks.x86_64-linux.<name>)`, `` - `tests/unit` — 2 files ``) and each of the six headings plus the test-line format is pinned by its own assertion; the stale message is now the plan's exact string, asserted by equality rather than substring. Package-description precedence is pinned by a `pkgs/broker` fixture with disagreeing tiers. 16 mutations run, 15 killed; the one survivor is section *order*, which the plan never asked to pin (observation, not a finding). `evidence-unit` (31 passed), `lint` and `githooks/pre-commit` are green by ref; `docs/MAP.md` is byte-identical to `repomap.py --root . print`, its Checks section is the same 38 names in `flake.nix` order, and `check` exits 0 both clean and with `__pycache__`/`.pytest_cache` present. Touches respected exactly (3 files), stdlib only, `Co-Authored-By` present, tree clean.

## Checks

- green — `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`: exit 0; `nix log` → `31 passed in 3.12s`. `tests/evidence/test_repomap.py` alone: 4 passed.
- green — `nix build .#checks.x86_64-linux.lint -L --no-link`: exit 0.
- green — `nix develop -c githooks/pre-commit`: exit 0 (treefmt 80 files 0 changed, "All checks passed!", 28 files already formatted, `render.test.mjs: all assertions passed`).
- green — one commit: `git log --oneline 7b23aa1..HEAD` is exactly one line; `git show --stat HEAD` is exactly `docs/MAP.md`, `pkgs/evidence/repomap.py`, `tests/evidence/test_repomap.py` (525 insertions, 0 deletions). No strays.
- green — **subject** (G2's major 1): `git log -1 --format=%s` diffed against a literal copy of the plan's `commit subject` → identical, byte for byte (em dash included). Trailers: `Generated-By: dsh …` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- green — generated-artefact fidelity: `nix develop -c python3 pkgs/evidence/repomap.py --root . print` vs `docs/MAP.md` → `cmp` clean. `… --root . check` → exit 0.
- green — Checks section: 38 lines; extracted name-for-name from `flake.nix`'s `      checks.${system} = {` block (line 686) and diffed → identical, same order. `grep -c '^- ' docs/MAP.md` = 83 (plan floor 60).
- green — determinism: after pytest had created `pkgs/evidence/__pycache__`, `tests/evidence/__pycache__` and `.pytest_cache`, `check` still exits 0 (the accepted `_IGNORED_PARTS` deviation from G2 is unchanged).
- green — headings in `docs/MAP.md` are, in order: `## NixOS modules`, `## Packages`, `## Checks (nix build .#checks.x86_64-linux.<name>)`, `## Tests`, `## Hosts`, `## Tools` — the plan's Step-3 list exactly.
- green — hard rules: no `sudo`, `nixos-rebuild`, `systemctl`, `--no-verify`, `--allow-empty`, `git commit -m`, no newly added `2>/dev/null` in the diff or the transcript. Imports are `argparse`, `pathlib`, `re`, `sys` and `from __future__ import annotations` — stdlib only. No secrets. `git status --porcelain` empty. The sibling `~/factory/ws/sc1/G2` is clean and `~/nixos-agent-env` is clean: nothing was written outside the workspace.
- green — trailing newlines: `pkgs/evidence/repomap.py`, `tests/evidence/test_repomap.py` and `docs/MAP.md` all end in `\n` (there are no separate fixture files in this task; the fixture is inline).
- green — no assertion weakened: the full `git diff task/G2 → HEAD` of `tests/evidence/test_repomap.py` is additions and strengthenings only (substring `"## Checks"` → six exact-heading assertions; substring `"docs/MAP.md is stale"` → full-string equality). Nothing dropped.

## Red before green

Every fix is proven by its own mutation red, applied one at a time to `pkgs/evidence/repomap.py` in the clone, run with `pytest -p no:cacheprovider tests/evidence/test_repomap.py -q`, reverted with `git checkout --`, and the restore re-verified green after each (all 16 restores: `4 passed`).

- **Indent anchor** (G2's major 2). `r"^ {8}([a-z][a-z0-9-]*) ="` → `r"^ *([a-z][a-z0-9-]*) ="` → `2 failed, 2 passed`: `test_flake_check_names_reads_the_checks_block_only` and `test_build_and_render`. The fixture under the relaxed anchor returns `['host-core', 'lint', 'nested', 'inner-child', 'helm-control-assertion-negative-profiles']` — the new `inner-child` at 10 spaces is what kills it. Against the repo's real `flake.nix` the same relaxation returns **86** names where the committed extractor returns **38** (extras include `access`, `allow`, `alt`, `attempt`, `baskets`, `c`, `classification`, `demo`, `egress`, `failing`, `fw`, `hc`, `hidden`, `i`, `launcher`, `modules`, `mount`, `name`, `notes-local`, `p`, …). The number the previous review measured is exactly the number the new fixture now defends.
- **Block terminator.** `break` → `pass` → `2 failed, 2 passed`. Fixture without the break: `[…, 'zzz']`; the new `other-block = { zzz = 1; }` (8-space child after the closing `      };`) is what catches it, where the old `other = 3;` at 6 spaces could not. Against the real `flake.nix` the break is still inert today (38 names either way) — the guard is latent by design and now proven on the fixture.
- **Layout.** Each of the six headings and the test-line format was mutated separately; every one fails `test_build_and_render` (`1 failed, 3 passed`).
- **Stale message.** Reverting to G2's `docs/MAP.md is stale; regenerate with: …` fails `test_cli_write_then_check_then_drift` — the equality assertion, not a substring.
- **Package precedence.** `for ext in (".sh", ".py")` → `for ext in ()` fails `test_build_and_render`: `pkgs/broker` then describes as `B: default.nix is the second tier.` instead of `A: broker.sh wins over default.nix.`
- Three of the original review's killed mutants (M2 shebang skip, M3 `HEADER` dropped, M4 `check` blind to staleness) plus M5 (`modules = []`) were re-run: all four still killed. No regression.

Method note: the test loads `repomap.py` through `importlib`, so a write-then-restore inside the same second can leave a mutant's `__pycache__` entry valid and silently poison the *next* run. I hit that once, cleared the caches, and re-ran the entire table with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`, with a green restore verified between every mutant. All results below are from that clean run.

## Mutation table

| mutation | killed | by |
|---|---|---|
| A — indent anchor `^ {8}` → `^ *` | **yes** | `test_flake_check_names_reads_the_checks_block_only`, `test_build_and_render` (`inner-child`) |
| B — checks-block `break` → `pass` | **yes** | same two tests (`zzz`) |
| C1 — `## NixOS modules` → `## Modules` | yes | `test_build_and_render` |
| C2 — `## Checks (nix build …)` → `## Checks` | yes | `test_build_and_render` |
| C3 — `` — N files `` → `` (N files) `` | yes | `test_build_and_render` |
| C4 — `## Packages` → `## Pkgs` | yes | `test_build_and_render` |
| C5 — `## Tests` → `## Test dirs` | yes | `test_build_and_render` |
| C6 — `## Hosts` → `## Machines` | yes | `test_build_and_render` |
| C7 — `## Tools` → `## Toolz` | yes | `test_build_and_render` |
| D — stale message reverted to G2's wording | yes | `test_cli_write_then_check_then_drift` |
| E — package precedence: drop the `<name>.sh`/`<name>.py` tier | yes | `test_build_and_render` (`pkgs/broker`) |
| F — swap the order of the Hosts and Tools sections | **no** | survived. Section membership is pinned, section order is not. The plan's Step 3 asks to pin the headings, the test lines and the stale message — all three are pinned — and never asks for order; `docs/MAP.md` would simply regenerate reordered, so `check` would not notice either. Observation, not a finding. |
| R-M2 — `first_comment` returns the shebang | yes | `test_first_comment_handles_shebang_docstring_and_bare`, `test_build_and_render` |
| R-M3 — `render_map` drops `HEADER` | yes | `test_build_and_render`, `test_cli_write_then_check_then_drift` |
| R-M4 — `check` blind to staleness (`if existing != md` → `if False`) | yes | `test_cli_write_then_check_then_drift` |
| R-M5 — `build_map` skips `nixosModules` | yes | `test_build_and_render` |

15 of 16 killed. Both of G2's surviving load-bearing mutants (its M6 and M1) are now killed; its M7 (precedence) is killed.

## Findings

- **closed (was major)** commit subject — byte-identical to the plan's `evidence: repomap.py generates docs/MAP.md (modules, packages, checks, tests, hosts, tools) and refuses a stale map (test: evidence-unit, lint)`. One commit on `task/G2b` cut from base `7b23aa1`; no amend; the required trailer present. The derived graph will read the chain as landed.
- **closed (was major)** `pkgs/evidence/repomap.py:46` indent anchor — proven load-bearing (mutation A), with the 86-vs-38 gap on the real `flake.nix` re-measured at this HEAD.
- **closed (was minor)** `pkgs/evidence/repomap.py:44-45` block terminator — proven load-bearing (mutation B).
- **closed (was minor)** layout — the plan's three strings adopted verbatim and each heading pinned (C1-C7).
- **closed (was minor)** stale message — the plan's exact string, pinned by equality (D).
- **closed (was minor)** package-description precedence — pinned by the `pkgs/broker` fixture (E).
- **observation** section order is unpinned (mutation F). One assertion on the sequence of `^## ` lines would close it; not required by the plan, and `docs/MAP.md` in-repo is a generated artefact either way.
- **observation** the carry-forwards from the G2 review are unchanged and still stand: `first_comment`'s docstring branch returns `""` for a module opening with a bare `"""` (no file in the repo hits it); `.ruff_cache` is not in `_IGNORED_PARTS` (safe only because it lands at the repo root); `_count_files` counts untracked files, so a stray file under `tests/` will trip the hook G5 is about to wire — consider `git ls-files` there. Unchanged too: several `docs/MAP.md` descriptions are mid-sentence fragments of internal notes (`claudeManagedSettings.nix`, `egressBroker.nix`), which is the plan's "first comment line" rule working as written and remains an orchestrator question for G7.

## Deviations

The FACTORY-RESULT declares `status=done`, `evidence-unit=pass lint=pass`, 1 commit, and notes the subject, the three mutations and the pinned layout — all of which I reproduced independently. It declares no deviations, and I found none that matter.

- **Deviation from the letter of G2b Step 2, accepted:** the plan says to *add* `other-block = { zzz = 1; }` after the checks block; the implementer *replaced* the pre-existing `other = 3;` with it. Strictly stronger — `other = 3;` sat at 6 spaces and could catch nothing, which is exactly why the G2 review called the old test vacuous. Nothing is lost.
- The extra `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sc1)` trailer above the required one is the seat's attribution mechanism, as in G2. Not a violation.
- The G2 deviation accepted last round (`_IGNORED_PARTS` and the `.pyc` skip in `_count_files`) is carried through unchanged and still necessary; re-verified.
