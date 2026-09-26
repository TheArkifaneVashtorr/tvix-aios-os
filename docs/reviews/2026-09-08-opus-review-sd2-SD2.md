---
plan_defect: none
mutants_total: 17
mutants_killed: 16
mutants_outside_named: 5
---
# Opus gate — seat run sd2, task SD2 — APPROVED

## Summary

The section's contract is met. `docs/ledger/task-classes.toml` carries the plan's
first table verbatim and in order; `tasks.py` gained `load_class_rules`,
`file_class` and `task_class`, every task dict a `"class"`, `factory_args` a
`class` field, `check` the four refusals and the brief's Next-wave line the
`KEY(class)` form; `factory_task_class` is a pure-bash line walk built on the
existing `factory_task_touches` (Assumption 24 — no second parser); `factory-task`
computes the class right after `kind_size`, passes `--class` into
`factory_route implement` and prints `class:` immediately after `route:`;
`factory-review` passes `--class` too.

Both red arms reproduce (pytest `AttributeError: module 'tasks' has no attribute
'task_class'`; all five bats cases `not ok`). All **twelve** mutants the section
names die, plus four of five I invented. `evidence-unit` (478 passed, 474 before),
`unit` (631/631) and `lint` are green under `--rebuild`; ruff, shellcheck, repomap
and `tasks.py check` are clean. One commit, subject byte-identical, both trailers
in order, the plan file untouched.

Nine MINORs, none gating. Two are literal readings of interface sentences the code
takes differently (the malformed-rules degrade; the rules file read per repo rather
than from `<root>`); both are defensible, both are undisclosed, neither changes the
operative behaviour of the driver's routing path.

## Contract items

**Interface 1 — the rules file.** `docs/ledger/task-classes.toml:1-182`: a header
comment, then 44 `[[rule]]` blocks. The class/glob pairs and their order are the
section's first table verbatim: `nix-module` ← `nixosModules/*`, `hosts/*`, `lib/*`
(`:8-18`); `vm-test` ← `tests/integration/*` (`:20-22`); `nix-check` ← `flake.nix`,
`treefmt.toml`, `pkgs/*/default.nix`, `pkgs/*/*.nix` (`:24-38`); `bash-driver` ←
`tools/factory/seat/*`, `tools/*.sh`, `githooks/*`, `pkgs/*/*.sh`, `tests/*/*.sh`
(`:40-58`); `bats-test` ← `tests/unit/*` (`:60-62`); `js-workflow` (`:64-74`);
`python-evidence` (`:76-134`, all fourteen globs); `docs-plan` (`:136-138`);
`docs-board` (`:140-154`); `docs-runbook` (`:156-182`). Every glob is inside
`[A-Za-z0-9._/*?-]`; no `[`, no `**`. **Met.**

**Interface 2 — classification, python.** `load_class_rules` (`pkgs/evidence/tasks.py:351-392`),
`file_class` (`:395-400`, first matching rule), `task_class` (`:403-421`, most files,
tie to the earliest rule, `any` on empty). `parse_plan` seeds `"class": "any"`
(`:246`); `scan_repo` sets it (`:959`); `factory_args` carries it (`:1183`);
`render_brief` prints `KEY(class)` (`:1816`); `check` appends the prefixed errors
(`:1510-1515`). The four refusal strings are exact — measured:

```
unknown -> ['tasks: task-classes: rule 1: unknown class typo']
badglob -> ['tasks: task-classes: rule 1: glob docs/[a] is not a plain pattern']
noglob  -> ['tasks: task-classes: rule 1: missing glob']
noclass -> ['tasks: task-classes: rule 1: missing class']
table   -> ['tasks: task-classes: not a [[rule]] table']
```

`waves --factory-args` carries `class` on the live tree
(`[('SD9', 'any'), ('SD10', 'any')]` — see MINOR-2 for the `any`). **Met**, with
MINOR-2 on "read from `<root>` … applied to every repo".

**Interface 3 — bash.** `factory_task_touches` is reused unchanged
(`tools/factory/seat/factory-lib.sh:908-909`, Assumption 24); `factory_task_class`
(`:924-1041`) is `mapfile` + a `[[rule]]`/`class = `/`glob = ` line walk +
`case "$path" in ${globs[j]})`, default RULES `$FACTORY_TOOLBOX_REPO/docs/ledger/task-classes.toml`
(`:926`), `any` for a missing rules file (`:1005-1008`), section or plan
(`:1012`, `:1029-1032`). Measured against the section's six rows:
`C1 bats-test  C2 nix-module  C3 python-evidence  C4 bats-test  C5 any  C6 any`.
**Met**, with MINOR-1 on the malformed-file wording.

**Interface 4 — `factory-task` / `factory-review`.**
`tools/factory/seat/factory-task:154` `class=$(factory_task_class "$plan" "$key")`
immediately after the `kind_size` read (`:152-153`); `:173`
`route_line=$(factory_route --class "$class" implement "$kind" "$size" || true)`;
`:837` `printf 'class: %s\n' "$class"` between `route:` (`:836`) and the optional
`prior:` (`:838-840`) — the SD4 item-2 placement.
`tools/factory/seat/factory-review:79-80` the same two lines for role `review`.
Proven end to end by `tests/unit/85-task-class.bats:123-193`: the `.result` carries
`class: bats-test`, `model: m/x` (the class-specific routing row won over the plain
default) and `route: implement/docs/XS` unchanged. **Met**, with MINOR-3
(`factory-review`'s arm is not pinned by any test).

## Red before green

**(a) pytest.** Base `pkgs/evidence/tasks.py` against the branch's tests
(`git checkout <base> -- pkgs/evidence/tasks.py`;
`nix develop -c pytest tests/evidence/test_tasks.py -q -k 'class'`):

```
E       AttributeError: module 'tasks' has no attribute 'task_class'
tests/evidence/test_tasks.py:613: AttributeError
...
FAILED tests/evidence/test_tasks.py::test_task_class_majority_tie_and_first_rule
FAILED tests/evidence/test_tasks.py::test_class_rules_file_validation
FAILED tests/evidence/test_tasks.py::test_json_and_factory_args_carry_class
FAILED tests/evidence/test_tasks.py::test_brief_next_wave_prints_class
4 failed, 1 passed, 140 deselected
```

the exact red the section predicts. Restored: `5 passed`.

**(b) bats.** Base `factory-lib.sh`, `factory-task`, `factory-review` against
`tests/unit/85-task-class.bats`:

```
1..5
not ok 1 factory_task_class prints the six classifying answers
not ok 2 factory_task_class degrades a malformed rules table to any with a warning
not ok 3 factory_task_class yields any for a missing rules file, section, or plan
not ok 4 factory_task_class agrees with tasks.py task_class on every section
#   bash_cls=$(...) failed with status 127
#   bash: line 1: factory_task_class: command not found
not ok 5 factory-task passes --class into factory_route and records class: in the .result
#   `[[ "$output" == *"model=m/x"* ]]' failed
```

(the section predicts the `class: bats-test` line as test 5's first failure; the
earlier `model=m/x` assertion in the same test fires first — same test, same cause.)
Restored: `ok 1..5`.

**(c) the disclosed file.** Base `tests/unit/87-prior-attempt.bats` against the
branch's `factory-task`:

```
not ok 11 factory-task --prior composes the block into the brief and records prior:
#   `[ "${lines[1]}" = "prior: r1/K1" ]' failed
```

— the adjustment is forced, not cosmetic.

## Mutants

Named by the section — **12/12 killed**. Each applied in a scratch copy of the
branch, the killing test run, then reverted.

| # | mutant | killed by | first failing line |
|---|---|---|---|
| 1 | majority → return the first matching class (`tasks.py:411` → `return klass`) | pytest `-k class` | `AssertionError: assert 'nix-module' == 'bats-test'` (`test_tasks.py:612`) |
| 2 | tie → `>=` in the max (`:419`) | pytest `-k class` | `AssertionError: assert 'bats-test' == 'nix-module'` (`:619`) |
| 3 | first-rule-wins → last matching rule wins (`file_class`, `:397-400`) | pytest `-k class` | `AssertionError: assert 'python-evidence' == 'bats-test'` (`:612`) |
| 4 | `any` arm → the first rule's class for an empty list (`:412-413`) | pytest `-k class` | `AssertionError: assert 'nix-module' == 'any'` (`:628`); also `test_json_and_factory_args_carry_class` |
| 5a | delete the `unknown class` rule (`:381-383`) | `test_class_rules_file_validation` | `assert False … = any(<generator …>)` |
| 5b | delete the `not a plain pattern` rule (`:387-389`) | same | `assert False` |
| 5c | delete the `missing class` rule (`:378-380`) | same | `assert False` |
| 5d | delete the `missing glob` rule (`:384-386`) | same | `TypeError: expected str, bytes or os.PathLike object, not NoneType` |
| 5e | delete the top-level `not a [[rule]] table` rule (`:367-369`) | same | `assert False` |
| 6 | drop `--class` from `factory-task`'s lookup (`factory-task:173`) | bats 85 | `not ok 5 … `[[ "$output" == *"model=m/x"* ]]' failed` |
| 7 | bash iterates rules in reverse (`factory-lib.sh:1016`) | bats 85 | `not ok 4 … `[ "$bash_cls" = "$py_cls" ]' failed` (and `not ok 1`) |
| 8 | the brief prints `KEY` without the class (`tasks.py:1816`) | pytest | `assert '**Next wave** — nixos-agent-env: E3(js-workflow) E7(bash-driver)' in …`; also the two amended legacy assertions |

Outside the named set — **4/5 killed**:

| # | mutant | result |
|---|---|---|
| E1 | bash tie-break `-gt` → `-ge` (`factory-lib.sh:1035`) | KILLED — `not ok 1`, `not ok 4` (the cross-check diverges) |
| E2 | drop `--class` from `factory-review`'s lookup (`factory-review:80`) | **SURVIVED** — 86/86 of `80-seat-driver.bats` + `85-task-class.bats` still `ok` (MINOR-3) |
| E3 | print `class:` before `route:` (`factory-task:836-837`) | KILLED — `not ok 11 … `[ "${lines[1]}" = "class: any" ]' failed` (the disclosed file) |
| E4 | `scan_repo` classifies with `[]` rules (`tasks.py:959`) | KILLED — `test_json_and_factory_args_carry_class`, `test_brief_next_wave_prints_class` |
| E5 | `factory_args` drops `"class"` (`tasks.py:1183`) | KILLED — `test_factory_args_shape`, `test_json_and_factory_args_carry_class` |

`mutants_total: 17`, `mutants_killed: 16`, `mutants_outside_named: 5`. No named
mutant survives.

## Checks

All in the fresh clone of `task/SD2` at `6010cb1`.

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | `478 passed in 13.30s`, exit 0 (474 before — Assumption 24 item 2) |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | exit 0, 631 `ok`, zero `not ok`; 318–322 are SD2's five |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | exit 0 |
| `nix develop -c githooks/pre-commit` | exit 1 — queue block stale (MINOR-8; exit **0** at commit time, proved below) |
| `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| `nix develop -c shellcheck factory-lib.sh factory-task factory-review` | exit 0 |
| `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0 (clean) |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

Note, not a finding: `tasks.py --root . json` raises
`TypeError: keys must be str, int, float, bool or None, not tuple … 'task_status'`
on the live tree. Reproduced identically with the **base** `tasks.py` — pre-existing,
outside SD2.

## Touches and commit

The diff touches ten files. Seven are the section's `touches` list;
`docs/MAP.md` is in it by rule (regenerated, and the regeneration is a no-op —
`git diff --exit-code` clean); `docs/OPERATIONS.md` changes only inside
`<!-- tasks:begin -->…<!-- tasks:end -->`, the one edit the lint gate itself makes
and the Global Constraints allow. The tenth,
`tests/unit/87-prior-attempt.bats`, is outside `touches` and **disclosed** in the
commit body ("Deviation: …"); the change is three assertion lines and a comment
(`grep -A1` → `-A2`, plus `[ "${lines[1]}" = "class: any" ]`), it is forced by the
new `class:` line, and I reproduced the failure it repairs. MINOR-6.

Commit: exactly one (`git rev-list --count base..HEAD` → `1`). Subject compared
byte-for-byte against `docs/superpowers/plans/2026-09-06-seat-driver.md:145` →
`SUBJECT BYTE-IDENTICAL`. Body states the why and the deviation; the two trailers
follow a blank line in the WORKSPACE RULES order:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sd2)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

No board commit, no "landed" commit; `git diff base..HEAD -- docs/superpowers/`
is empty (the plan file untouched).

## Findings

**MINOR-1 — a malformed rules file yields a class, not `any`.**
`tools/factory/seat/factory-lib.sh:938-971` validates each `[[rule]]` and, when it
fails, warns and *skips that rule*, then classifies with the survivors
(`:968-971`). Interface 3 says "a malformed rules file → `any` plus one stderr
warning". Measured with a file whose first rule is bad and second is good:

```
$ factory_task_class plan.md C1 rules-mixed.toml
factory_task_class: …/rules-mixed.toml: rule 1: unknown class typo
bats-test
```

`any` was expected. The bats arm passes only because its fixture's *only* rule is
malformed (`85-task-class.bats:52-56`), so the empty-rules→`any` path answers for
it. Two mitigations: the behaviour matches `tasks.py`'s `load_class_rules`, which
also skips bad rules and returns the good ones — so the bash/python cross-check
invariant is preserved, and the section's literal reading would have *broken* it —
and `check` refuses a malformed rules file in the lint gate, so one cannot land.
The warning count also differs (one per defect, not one per file). Undisclosed.

**MINOR-2 — the rules are read per scanned repo, not once from `<root>`.**
`pkgs/evidence/tasks.py:779-781` loads them from
`os.path.join(repo_path, "docs", "ledger", "task-classes.toml")` inside `scan_repo`
(and `:1512` likewise in `check`). Interface 2 says "The rules are read from
`<root>/docs/ledger/task-classes.toml` and applied to every repo the graph scans".
Consequence measured from the clone, where `docs/ledger/repos.toml` resolves
`nixos-agent-env` to `~/nixos-agent-env`:

```
$ tasks.py --root . brief | grep -i 'next wave'
**Next wave** — nixos-agent-env: CR4(any) (plan 2026-09-05-context-reset-ritual.md)
$ tasks.py --root . waves … --factory-args   →  [('SD9','any'), ('SD10','any')]
```

whereas `task_class` over CR4's own touches with the committed rules is
`docs-runbook`:

```
CR4 file classes: [('githooks/pre-commit','bash-driver'),
                   ('docs/runbooks/session.md','docs-runbook'),
                   ('CLAUDE.md','docs-runbook')]
CR4 class: docs-runbook
```

(`board_graph(".")`, which uses the tree itself, does print `CR4 class= docs-runbook`.)
Once SD2 lands on main this self-heals for `nixos-agent-env`; the residual is that
every task in the five sibling repos of `repos.toml` (`media`, `gaming`,
`nixos-skill`, `dsh-harness`, `codex`) will classify `any` forever, because those
trees have no rules file of their own — the plan wanted one shared vocabulary
applied to all of them. The driver's own routing path is unaffected:
`factory_task_class` defaults to `$FACTORY_TOOLBOX_REPO`'s file
(`factory-lib.sh:926`). Undisclosed.

**MINOR-3 — `factory-review`'s `--class` is unpinned.**
`tools/factory/seat/factory-review:80` is correct code with no test behind it:
dropping `--class "$class"` there leaves all 86 tests of `tests/unit/80-seat-driver.bats`
and `tests/unit/85-task-class.bats` green (mutant E2 survives). The only
`factory-review` routing test (`80-seat-driver.bats:1391-1449`) uses a fixture with
no class-carrying row and a plan section with no `touches`, so it exercises
`--class any` and cannot discriminate. The section's Tests block names no
`factory-review` mutant, so this is a plan-level gap, not a seat one.

**MINOR-4 — the bash line walk misparses a TOML inline comment.**
`factory-lib.sh:975-990` strips quotes only when the whole trimmed value is quoted,
so a comment after a value poisons the rule and the two implementations diverge on
a file `check` accepts:

```
rules-comment.toml:  class = "bats-test"  # the bats rule
bash   → factory_task_class: …: rule 1: unknown class "bats-test"  # the bats rule
         any
python → rules [('bats-test','tests/unit/*')] errors []   class bats-test
```

Interface 3 prescribes exactly this line walk, so the seat followed the contract;
the hazard is that the cross-check fixture (`85-task-class.bats:34-50`) carries no
inline comment, so nothing guards the rules file against acquiring one. Worth a
line in SD10's runbook: whole-line `#` comments only in `task-classes.toml`.

**MINOR-5 — interface 1's "no leading `/`, no `..`" is unenforced.**
`pkgs/evidence/tasks.py:78` `CLASS_GLOB_RE = ^[A-Za-z0-9._/*?-]+$` (and the same
character set in `factory-lib.sh:962-967`) accepts both:

```
'/etc/*'        accepted
'../secrets/*'  accepted
'a[b]'          refused
```

Only the character-set half of interface 1 is checked. The committed file uses
neither form, so nothing is wrong today.

**MINOR-6 — one file outside `touches`.** `tests/unit/87-prior-attempt.bats:397-407`
(SD4b's). Disclosed in the commit body, forced by the `class:` line now sitting
between `route:` and `prior:`, and minimal — I reproduced the red it repairs and
confirmed the adjusted assertion is load-bearing (mutant E3 dies on it). Recorded,
not owed.

**MINOR-7 — the commit body does not paste the red and the green.** The section
does not demand it (unlike SD1b's and SD4b's, whose titles do), and the approved
SD5 commit `9dfa151` omits it likewise; the body does state the why and the
deviation. Recorded for the ledger only.

**MINOR-8 — `githooks/pre-commit` exits 1 on the committed tree.**
`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` — the
regeneration drops `SD2` from `Queued`, because SD2's own commit subject is now in
the log and the key reads as landed. This is a tooling artifact, not the seat's
error: with the same tree staged and the commit not yet made (soft reset to the
base, tree unchanged), `nix develop -c githooks/pre-commit` exits **0** and leaves
`docs/OPERATIONS.md` untouched — the committed block is exactly what the hook
derives at commit time. Any task that is itself in the queue block has this
property. Nothing owed; the orchestrator's board commit re-derives the block after
the merge.

**MINOR-9 — `2>/dev/null` on the touches call.**
`tools/factory/seat/factory-lib.sh:1012`
`touches=$(factory_task_touches "$plan" "$key" 2>/dev/null) || touches=`
silences every diagnosis from `tasks.py touches` — a missing toolbox python, an
unreadable plan and a missing section all degrade silently to `any`, where the
section's degrade-and-warn shape (and `factory_route`'s precedent) would warn once
on stderr. Contract 3 does require `any` for all three, so the value is right; only
the diagnosis is lost.

## Verdict

**APPROVED.** Every numbered contract item is met at the file and line cited; both
reds reproduce with the section's predicted output; all twelve named mutants die
and four of five extra ones; `evidence-unit` (478), `unit` (631) and `lint` are
green under `--rebuild`, with ruff, shellcheck, repomap and `tasks.py check` clean;
one commit, subject byte-identical, trailers in order, plan untouched, one
disclosed and minimal file outside `touches`. Nine MINORs, none gating; MINOR-1
and MINOR-2 are the two worth a plan-text decision before SD3 and SD9 build on
this field.
