---
reviewer: opus
majors: null
minors: 4
mutants_total: 8
mutants_killed: 4
---
# Opus gate — seat run pa2, task P12 — APPROVED

Branch `task/P12` in `/home/dalhaka/factory/ws/pa2/P12`, base `91dcc5f`, head `f5e561e`, one commit.
Reviewed in a fresh clone at `/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-pa2-P12`
(cloned with `git clone -q --branch task/P12`; every command run through that clone's own devShell, which carries
prettier 3.9.6, oxlint 1.79.0, treefmt 2.5.0, nodejs 24.19.0 — the pinned-nixpkgs versions of Assumption 9).

## Summary

The contract is met. The two arm literals `FORMATTER_ARM=A` / `LINTER_ARM=A` are what my own probe produces,
the self-test is non-vacuous and four of the plan's named mutants die on it, both reformatted JS files (and the
third the plan forgot) are byte-for-byte what `prettier --write` produces from the base revision — so no semantic
change can hide in them — and every check named or implicated is green. Two files fall outside `touches`:
`docs/MAP.md` (forced — `repomap.py check` refuses the tree without it) and `tests/lane/polkit.test.mjs` (forced —
the new gate itself refuses the tree without it). Both are proved forced below; the second is the plan's own
omission, and it is the dominant plan defect. No MAJOR. Four minors, none blocking.

## The probe and the arms

Reproduced on the ORIGINAL file (`git show 91dcc5f:tools/factory/dark-factory.js`), run from the clone root so the
committed `.prettierrc.json` and `.oxlintrc.json` are in effect:

```
$ nix develop -c prettier --check probe-tmp/dark-factory-orig.js
Checking formatting...
[warn] probe-tmp/dark-factory-orig.js
[warn] Code style issues found in the above file. Run Prettier with --write to fix.
prettier=1

$ nix develop -c oxlint --deny-warnings probe-tmp/dark-factory-orig.js
oxlint=0
```

prettier exits 1 with a *style diff*, not a parse error → arm A. oxlint exits 0, silent → arm A. The base file has
`export const meta = {` at line 68 and a top-level `return {` at line 673, so both tools were handed exactly the
shape the contract asks about. The commit body pastes these two outputs and the two literals verbatim; they match.

Workflow-shaped input probed directly (`export const meta = { name: 'x' }` + `const o = { k: 1, k: 2 }` + a
top-level `return o`):

```
$ oxlint --deny-warnings wf.js
wf.js:2:13: error eslint(no-dupe-keys): Duplicate key 'k' help: Consider removing the duplicated key   # exit 1
$ prettier --check wf.js
Checking formatting...
All matched files use Prettier code style!                                                              # exit 0
```

and with a top-level `await` as well, prettier exit 0 and oxlint exit 0. Neither tool refuses the shape: oxlint
parses it *and* its rules fire past the `return`, so arm A for the linter is not merely "no parse error" but a
real lint. `tests/lint/js-lint.sh:21-22` carries `FORMATTER_ARM=A` / `LINTER_ARM=A`. Nothing contradicts them.

## The script and the self-test

`tests/lint/js-lint.sh`, 197 lines, `set -euo pipefail` at line 14.

```
$ nix develop -c shellcheck tests/lint/js-lint.sh          → exit 0, silent
$ nix develop -c bash tests/lint/js-lint.sh --self-test
js-lint: workflow-script formatter arm A
js-lint: workflow-script linter arm A
tests/lint/fixtures/js/bad.mjs:1:7:  error eslint(no-unused-vars) …
tests/lint/fixtures/js/bad.mjs:1:13: error eslint(no-dupe-keys): Duplicate key 'k' …
tests/lint/fixtures/js/bad.mjs:2:1:  error eslint(no-debugger): `debugger` statement is not allowed …
Checking formatting...
[warn] tests/lint/fixtures/js/unformatted.mjs
tests/lint/fixtures/js/workflow-bad.js:2:13: error eslint(no-dupe-keys): Duplicate key 'k' …
selftest=0
$ nix develop -c bash tests/lint/js-lint.sh                → exit 0 (three files, all clean)
```

Both arm lines print. Each fixture fails the tool the contract names, and each failure is a *rule* firing, not a
parse accident: `bad.mjs` catches no-unused-vars + no-dupe-keys + no-debugger from oxlint, `unformatted.mjs`
catches prettier's style check, `workflow-bad.js` catches no-dupe-keys *through* a top-level `return` — that last
one is what makes the linter arm non-vacuous.

Shape rule (`is_workflow`, line 43, `grep -q '^export const meta = {'`) over the six tracked JS files:

| file | classified |
|---|---|
| `tests/factory/render.test.mjs` | module |
| `tests/lane/polkit.test.mjs` | module |
| `tests/lint/fixtures/js/bad.mjs` | module |
| `tests/lint/fixtures/js/unformatted.mjs` | module |
| `tests/lint/fixtures/js/workflow-bad.js` | **Workflow** |
| `tools/factory/dark-factory.js` | **Workflow** |

That is the whole tracked JS set (`git ls-files | grep -E '\.(cjs|jsx|ts|tsx|mts|cts)$'` is empty), so no tracked
JavaScript file escapes the gate. The three fixtures are excluded from the project run by
`':!tests/lint/fixtures/js/*'` (line 106) and are the self-test's own probes; nothing else in the tree sweeps them
(`grep -rn 'tests/lint'` over `flake.nix`, `githooks/`, `tests/`, `tools/`, `pkgs/` shows only the two gate call
sites; `bats-and-chain.sh` globs `tests/unit/*.bats`; `factory-unit` and `lane-polkit-unit` copy named files only).

Fixture exclusion is load-bearing — removing it turns the project run red on the fixture (mutant 3 below).

Exit codes: 0 clean, 1 with the tool's own output (proved by reverting `polkit.test.mjs` to base — the run printed
prettier's `[warn] tests/lane/polkit.test.mjs` and exited 1), 2 on a missing tool (Red before green), 3 when no arm
parses. Exit 3 is only reachable under `LINTER_ARM=B`, as §P12 says ("one the probe cannot select"); I forced it in
a scratch copy with both arms flipped to B and a Workflow-shaped file `const x = (((`:

```
js-lint: tools/probe/unparsable.js: no arm parses this Workflow script
/tmp/nix-shell.30r3Tz/tmp.6wMDFe4f8c/unparsable.js:5:1: error: Unexpected token
exit=3
```

Lockstep, both ways, in scratch copies (reverted after each):

```
FORMATTER_ARM=B, dark-factory.js absent from excludes:
  js-lint: self-test: tools/factory/dark-factory.js is a Workflow script the treefmt js formatter would still format   exit 1
FORMATTER_ARM=A, dark-factory.js added to excludes:
  js-lint: self-test: tools/factory/dark-factory.js is excluded from the formatter although it parses                   exit 1
```

## The reformat

`git diff -w --ignore-blank-lines 91dcc5f..HEAD` on the three JS files leaves only prettier-shaped hunks: single
quotes kept, semicolons absent, trailing commas added, long object literals and argument lists wrapped at 120,
one redundant parenthesis pair dropped (`const HOST = (A.host === null || A.host === false) ? null : (A.host || 'core')`
→ `… ? null : A.host || 'core'`, identical by `||`-over-`?:` precedence).

Stronger than reading hunks — I regenerated the reformat from the base revision:

```
git show 91dcc5f:<file> > $R/<file>; prettier --write $R/<file>   (with the committed .prettierrc.json)
diff -q $R/dark-factory.js tools/factory/dark-factory.js   → dark-factory.js IDENTICAL
diff -q $R/render.test.mjs tests/factory/render.test.mjs   → render.test.mjs IDENTICAL
diff -q $R/polkit.test.mjs tests/lane/polkit.test.mjs      → polkit.test.mjs IDENTICAL
```

All three committed files are byte-for-byte prettier 3.9.6's output from base. No hand edit is possible in them, so
no semantic change is possible in them.

Harness shape survives: `export const meta = {` still at line start (line 68) and the first later line that is
exactly `}` is line 96 — the two anchors `stripMeta` in `render.test.mjs:38-50` looks for. Proved by the test:

```
nix build .#checks.x86_64-linux.factory-unit -L --no-link --rebuild  → factory-unit> render.test.mjs: all assertions passed
nix build .#checks.x86_64-linux.lane-polkit-unit -L --no-link --rebuild → polkit.test.mjs: all assertions passed
nix develop -c node --check tests/factory/render.test.mjs   → ok
nix develop -c node --check tests/lane/polkit.test.mjs      → ok
```

`prettier --check` over the whole tracked set is clean, and `treefmt --ci --config-file treefmt.toml --tree-root .`
reports `formatted 98 files (0 changed)`.

## Deviations

**(a) `tests/lane/polkit.test.mjs` — outside `touches`; forced; plan defect, not a seat fault.** It is a tracked
`.mjs` file, so the gate this very task installs must reach it. Proof it is forced:

```
$ git checkout 91dcc5f -- tests/lane/polkit.test.mjs
$ nix develop -c bash tests/lint/js-lint.sh
[warn] tests/lane/polkit.test.mjs
[warn] Code style issues found in the above file. Run Prettier with --write to fix.
exit=1
```

The change is style only — one object literal expanded (`{ user: user, isInGroup: function () { return false } }`
over five lines) — and byte-identical to prettier's own output (above). §P12's **Files** and `touches` list
`dark-factory.js` and `render.test.mjs` and stop; the plan missed the third tracked JS file. `wrong-file`.

**(b) `docs/MAP.md` — outside `touches`; forced by rule.** `tests/lint` goes 2 files → 6.

```
$ git checkout 91dcc5f -- docs/MAP.md
$ nix develop -c python3 pkgs/evidence/repomap.py --root . check
repomap: docs/MAP.md is stale — run: python3 pkgs/evidence/repomap.py write
exit=1
```

`repomap.py check` runs in both `githooks/pre-commit:64` and the flake's lint block, so the commit could not exist
without it. Reproduced byte for byte: `python3 pkgs/evidence/repomap.py --root . write` leaves the tree clean
(`git status --porcelain` empty).

**(c) `--deny-warnings` is redundant in oxlint 1.79.0 — plan wrong-fact, disclosed by the implementer.** Under
`"categories": {"correctness": "error"}` both offending rules are already hard errors, so the plan's mutant cannot
turn red:

```
$ sed -i 's/oxlint --deny-warnings/oxlint/g' tests/lint/js-lint.sh
$ nix develop -c bash tests/lint/js-lint.sh --self-test
tests/lint/fixtures/js/bad.mjs:2:1: error eslint(no-debugger): `debugger` statement is not allowed …
exit=0        # the self-test still passes: the mutant survives
```

Which fixture line each tool catches, exactly: oxlint catches `bad.mjs:1:13` no-dupe-keys, `bad.mjs:1:7`
no-unused-vars and `bad.mjs:2:1` no-debugger — all three at *error* level with or without the flag; prettier
catches `unformatted.mjs` whole-file; oxlint catches `workflow-bad.js:2:13` no-dupe-keys. The self-test is
therefore still non-vacuous through the duplicate key even with the flag deleted. Keeping the flag is harmless and
version-independent; the seat kept it and said why. Not a fault.

## Tests and mutants

Applied → run → reverted (`git status --porcelain` empty after each; the clone is clean at the end).

| # | mutant | result |
|---|---|---|
| 1 | drop `[formatter.js]` from `treefmt.toml` | **KILLED** — `js-lint: self-test: treefmt has no js formatter`, exit 1; and the whole lint check goes red (below) |
| 2 | delete `--deny-warnings` | **survives** — plan wrong-fact (Deviations c), disclosed; the gate stays non-vacuous |
| 3 | remove `':!tests/lint/fixtures/js/*'` | **KILLED** — project run exits 1 on `[warn] tests/lint/fixtures/js/bad.mjs` |
| 4 | `FORMATTER_ARM=B`, excludes unchanged | **KILLED** — `… is a Workflow script the treefmt js formatter would still format`, exit 1 |
| 5 | `FORMATTER_ARM=A`, `dark-factory.js` added to excludes | **KILLED** — `… is excluded from the formatter although it parses`, exit 1 |
| 6 | drop the `workflow-bad.js` assertion from `self_check` | survives — inherent (a self-test cannot detect its own deletion); §P12 designates this the review-caught `vacuous-test` major, and the assertion **is** present, so no fault |
| 7 | `is_workflow` grep changed to `'^__never_matches__'` | survives — MINOR 2 |
| 8 | `.oxlintrc.json` `globals` removed | survives — MINOR 1 |

4 of 8 killed; of the four survivors, one is a plan wrong-fact, one is inherent and named by the plan, two are the
minors below. No mutant the plan names as *test-detectable* survived.

Wiring proof — a failing self-test must fail the check, not just the shell:

```
$ sed -i '/^\[formatter\.js\]/,$d' treefmt.toml
$ nix build .#checks.x86_64-linux.lint -L --no-link
lint> js-lint: self-test: treefmt has no js formatter
lint_exit=1
```

`githooks/pre-commit:33-34` and `flake.nix:1045-1046` both run `--self-test` then the sweep, after
`tests/lint/bats-and-chain.sh` as contracted. Nothing in the tree asserts the hook's list and the flake's list stay
in lockstep — but that gap is pre-existing (`bats-and-chain.sh` has it too) and outside P12's scope.

## Checks

| command | expected | observed | exit |
|---|---|---|---|
| `nix develop -c shellcheck tests/lint/js-lint.sh` | silent | silent | 0 |
| `nix develop -c bash tests/lint/js-lint.sh --self-test` | both arm lines, three fixture failures | as quoted above | 0 |
| `nix develop -c bash tests/lint/js-lint.sh` | three files clean | three `All matched files use Prettier code style!` | 0 |
| `nix develop -c treefmt --ci --config-file treefmt.toml --tree-root .` | no change | `formatted 98 files (0 changed)` | 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | green | green (js-lint output visible in the log) | 0 |
| `nix build .#checks.x86_64-linux.factory-unit -L --no-link --rebuild` | green | `render.test.mjs: all assertions passed` | 0 |
| `nix build .#checks.x86_64-linux.lane-polkit-unit -L --no-link --rebuild` | green | `polkit.test.mjs: all assertions passed` | 0 |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | green | 353 bats tests ok | 0 |
| `nix develop -c githooks/pre-commit` | passes, then the queue block | all gates green, then `tasks: docs/OPERATIONS.md queue block was stale …` | 1 |
| `python3 pkgs/evidence/repomap.py --root . write` | no diff | tree clean | 0 |
| `python3 pkgs/evidence/tasks.py --root . check` | silent | silent | 0 |
| `python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06` | silent | silent | 0 |

The hook's exit 1 is the by-design board staleness, not a defect: on the task branch HEAD now carries P12's exact
subject, so `tasks.py` counts P12 landed and drops it from the queue block. At `91dcc5f` the same regeneration
leaves the board unchanged (`git diff --stat -- docs/OPERATIONS.md` empty), which is the state the seat committed
in. `docs/OPERATIONS.md` is correctly **not** in the commit — no board commit.

`docs/ledger/claims.toml` is untouched by this commit (`git diff --name-only 91dcc5f..HEAD -- docs/ledger/claims.toml`
is empty), as §P12 requires; the `js-formatter-linter-missing` flip is owed to the landing's docs commit.

## Red before green

Reproduced (1): main's tool set has no prettier — `git show 91dcc5f:flake.nix` shows `lintTools` ending at `nodejs`
with no `prettier`/`oxlint`. Running the branch's script with a PATH lacking them:

```
$ PATH=/run/current-system/sw/bin bash tests/lint/js-lint.sh --self-test
js-lint: prettier not on PATH
exit=2
```

Reproduced (2): the contracted vacuous line. I copied the script to scratch and emptied the two gate bodies
(`prettier --check "$f"` → `true`, `oxlint --deny-warnings "$f"` → `true`), i.e. the "script body empty" state of
Step 1, and ran `--self-test`:

```
js-lint: workflow-script formatter arm A
js-lint: workflow-script linter arm A
js-lint: self-test: bad.mjs passed; the gate is vacuous
exit=1
```

Both red states are exactly the strings §P12 contracts.

## Findings

No MAJOR.

**MINOR 1 — `.oxlintrc.json` `globals` is inert; deleting it changes nothing.** `.oxlintrc.json:1`. oxlint 1.79.0's
`correctness` category does not enable `no-undef`, so undefined identifiers are never reported with or without the
eight Workflow globals:

```
$ printf 'totallyUndefinedThing(1)\n' > probe-tmp/undef.mjs
$ nix develop -c oxlint --deny-warnings probe-tmp/undef.mjs   → exit 0, silent
```

and the project sweep stays green with `"globals"` deleted entirely. The block is the plan's verbatim text and the
seat wrote it as instructed, so this is not a seat fault — but nothing pins it. Pin I would add: turn `no-undef` on
explicitly in a `rules` block, and add a fourth self-test assertion that a fixture calling a bare `agent(...)`
passes only with the globals present.

**MINOR 2 — the shape rule is unpinned under arm A.** `tests/lint/js-lint.sh:43`. Changing the grep to match
nothing (every file a module) leaves both `--self-test` and the project run at exit 0: under A/A the classification
has no observable consequence, because both tools accept both shapes in place. Pin I would add: a self-test
assertion over `tracked_js_files` that `is_workflow` is true for `tools/factory/dark-factory.js` and false for
`tests/factory/render.test.mjs` / `tests/lane/polkit.test.mjs`, plus true for `tests/lint/fixtures/js/workflow-bad.js` —
one line each, and the rule stops being free.

**MINOR 3 — the arm B linter fallback cannot pass as written.** `tests/lint/js-lint.sh:74-98`. The wrapper rewrites
`export const meta` to `const meta`, which is then an unused variable inside `__wf`, so oxlint's no-unused-vars
fires on every Workflow script. Flipping the literals to B in a scratch copy:

```
/tmp/nix-shell.pL8CYt/tmp.7qBZNT1YWJ/dark-factory.js:69:7: error eslint(no-unused-vars): Variable 'meta' is declared but never used …
js-lint: a reported line number above is the file's line plus one (harness wrapper)
exit=1
```

The arm is not selected, and the contract requires the wrapper be byte-identical to `darkFactorySyntaxCheckSrc`
(which only feeds `node --check`, so it never met this rule), so the seat is inside its instructions. But whoever
takes arm B — P5's `.claude/workflows/plan.js` may force it on a future oxlint — inherits a false positive.
Worth a line in the script's header, or an appended `void meta` in the wrapper with the note becoming "+1 line".

**MINOR 4 — cosmetic.** The exit-3 path prints only oxlint's output on stderr, not "both tools' output" as §P12
words it (under `FORMATTER_ARM=B` prettier is skipped entirely, so there is nothing to print — the wording, not the
code, is at fault). The lint block and hook use two lines rather than the contracted
`--self-test && …`; behaviourally identical or safer, though the justifying comment's errexit claim is inaccurate
(`a && b` under `set -e` does fail the list when `a` fails). `.prettierrc.json`, `.oxlintrc.json` and all three
fixtures end without a trailing newline.

Commit convention: exactly one commit; subject byte-identical to §P12's (`diff` against the plan line is empty);
`Generated-By:` then `Co-Authored-By: Claude Fable 5.1` trailers present; the commit body pastes both probe outputs
and both arm literals verbatim and discloses both extra files and the redundant flag; no board commit; the result
block form is not in scope of the tree. Thirteen files touched: the eleven of `touches` plus the two justified
above.

## Verdict

**APPROVED.** Every claim in the implementer's report survives refutation: the arms are what the tools actually do,
the reformat is provably mechanical, the self-test is non-vacuous and kills four of the plan's five test-detectable
mutants (the fifth is a plan wrong-fact the implementer named), and lint, factory-unit, unit and lane-polkit-unit
are all green. The two files outside `touches` are each forced by a gate in this repo and each proved forced. Four
minors, all non-blocking; MINOR 2's pin is the one I would fold into the next JS task.

plan_defect: wrong-file — touches omitted tests/lane/polkit.test.mjs, a tracked JS file
