---
plan_defect: underspecified
plan_defect_secondary: wrong-fact
mutants_total: 9
mutants_killed: 7
mutants_outside_named: 5
---
# Opus gate — seat run hg1, task OG3 — REJECTED

## Summary

The seat did what the section said, and did it cleanly: `PROTECTED_PATHS` gains
`'tools/orchestrator-guard.sh|file'` (`tools/orchestrator-guard.sh:165`), six bats
tests (a)–(f) land beside the ritual-override block (`tests/unit/91-orchestrator-guard.bats:770-834`),
the sweep gains its six rows and the header `# rows: 448`, and the `seat@` unit pins
`FACTORY_HOUSE_GUARD` to the tree path with a `seat-eval` assertion. All four acceptance
checks are green under `--rebuild`; the named mutants A–D all die; the red is real
(the base guard leaves (a)–(e) `not ok`, `seat-eval` errors on the missing attribute).
The +117/−31 refactor of the guard is verdict-preserving: the 442 pre-existing sweep rows
produce byte-identical verdict AND reason through the old and the new guard, and all 119
pre-existing tests in `91-orchestrator-guard.bats` stay green.

It is rejected on one thing, and it is the point of the task. `PROTECTED_PATHS` is
resolved against `CLAUDE_PROJECT_DIR`, and in a seat that is the *workspace*
(`pkgs/dsh-openrouter/dsh-openrouter.sh:656,738`: "CLAUDE_PROJECT_DIR is supplied by the
bridge from `projectDir` (== the workspace)"). So the new entry protects the workspace's
copy of the guard, not the live checkout the seat actually obeys. Measured against the
branch's guard with `CLAUDE_PROJECT_DIR` = a seat workspace:
`printf x > /home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh` → **ALLOW**.
MINOR-11 ("a seat can edit the rules it obeys") stays open, and contract item 1's clause
"the absolute checkout path … is denied" is false in the only environment contract item 4
exists for. The defect is the section's: it specified a project-relative mechanism ("no new
arm") for a cross-project threat, and named a spelling (`$HOME/…`) the arms do not in fact
normalise.

## Contract items

1. **`PROTECTED_PATHS` gains the entry, with the comment — MET (structurally); the stated
   spelling coverage — NOT MET in the seat (MAJOR-1).**
   `tools/orchestrator-guard.sh:162-165`:
   ```
     # OG3 (SD8's gate, MINOR-11): the guard the house runs is read from the
     # mutable checkout, so it must name itself — a seat must not be able to edit
     # the rules it obeys.
     'tools/orchestrator-guard.sh|file'
   ```
   Every write verb the section lists denies with the guard's own reason, and every read
   stays allowed (measured with `CLAUDE_PROJECT_DIR=/home/dalhaka/nixos-agent-env`):
   ```
   DENY   sed -i s/a/b/ tools/orchestrator-guard.sh        [orchestrator-guard.sh is the operator's; ask for it]
   DENY   sed -i s/a/b/ ./tools/orchestrator-guard.sh      [orchestrator-guard.sh is the operator's; ask for it]
   DENY   mv tools/orchestrator-guard.sh /tmp/x            [orchestrator-guard.sh is the operator's; ask for it]
   DENY   truncate -s 0 tools/orchestrator-guard.sh        [orchestrator-guard.sh is the operator's; ask for it]
   DENY   chmod 777 tools/orchestrator-guard.sh            [orchestrator-guard.sh is the operator's; ask for it]
   DENY   tee tools/orchestrator-guard.sh                  [orchestrator-guard.sh is the operator's; ask for it]
   DENY   install -m 755 /tmp/g tools/orchestrator-guard.sh[orchestrator-guard.sh is the operator's; ask for it]
   DENY   ln -sf /tmp/g tools/orchestrator-guard.sh        [orchestrator-guard.sh is the operator's; ask for it]
   DENY   dd of=tools/orchestrator-guard.sh                [orchestrator-guard.sh is the operator's; ask for it]
   DENY   touch tools/orchestrator-guard.sh                [orchestrator-guard.sh is the operator's; ask for it]
   DENY   git checkout -- tools/orchestrator-guard.sh      [orchestrator-guard.sh is the operator's; ask for it]
   DENY   git restore tools/orchestrator-guard.sh          [orchestrator-guard.sh is the operator's; ask for it]
   DENY   python3 -c "open('tools/orchestrator-guard.sh','w').write('x')"  [orchestrator-guard.sh is …]
   DENY   rm /home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh     [orchestrator-guard.sh is …]
   ALLOW  cat tools/orchestrator-guard.sh
   ALLOW  bash tools/orchestrator-guard.sh
   ALLOW  git diff -- tools/orchestrator-guard.sh
   ALLOW  cp tools/orchestrator-guard.sh /tmp/g.sh
   ```
   The same list with `CLAUDE_PROJECT_DIR` = a seat workspace flips the absolute spellings
   to ALLOW — see MAJOR-1. The `$HOME/…` spelling is allowed in **both** — see MINOR-1.
2. **Six bats tests (a)–(f) — MET.** `tests/unit/91-orchestrator-guard.bats:777, 785, 793,
   805, 813, 826`, placed directly after the ritual-override tests (`:767`), one `[ … ]`
   per line, each denial asserting `*"orchestrator-guard.sh"*`. File count 119 → 125
   (`nix develop -c bats --count …` = 125; with `93-house-guard.bats`, 137).
3. **Six sweep rows and the header — MET.** `tests/unit/91-orchestrator-guard-sweep.txt:1`
   `# rows: 448`; data rows counted = 448; the last six rows are exactly (a)–(d) plus
   (f)'s two. `nix develop -c bats tests/unit/91-orchestrator-guard.bats
   tests/unit/93-house-guard.bats` → 137 ok, 0 not ok, so SD8's parity test is green.
4. **`FACTORY_HOUSE_GUARD` in the `seat@` environment and the `seat-eval` assertion — MET,
   tree path not a store path.** `nixosModules/seatLane.nix:179`
   `FACTORY_HOUSE_GUARD = "/home/${cfg.operatorUser}/nixos-agent-env/tools/orchestrator-guard.sh";`
   beside `FACTORY_ROUTING_TABLE` (`:174`) with the comment the section asked for (`:175-178`);
   `flake.nix:1702-1704` asserts
   `unit.environment.FACTORY_HOUSE_GUARD == "/home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh"`
   with the exact message `seat-eval: seat@ must pin FACTORY_HOUSE_GUARD to the tree's guard`.
   The wrapper consumes it: `pkgs/dsh-openrouter/dsh-openrouter.sh:695`.

## Red before green

Base implementation file against the branch's tests
(`git checkout ee0b4c6 -- tools/orchestrator-guard.sh`):

```
$ nix develop -c bats --filter 'orchestrator-guard.sh' tests/unit/91-orchestrator-guard.bats
1..6
not ok 1 bash: sed -i on tools/orchestrator-guard.sh is denied
#   `denied "$output"' failed   (json.decoder.JSONDecodeError: the guard printed nothing)
not ok 2 bash: a redirect onto tools/orchestrator-guard.sh is denied
not ok 3 bash: cp onto tools/orchestrator-guard.sh is denied but reading from it is allowed
not ok 4 bash: rm tools/orchestrator-guard.sh is denied with the file reason
not ok 5 write/edit: the Write and Edit tools on tools/orchestrator-guard.sh are denied
ok 6 bash: reading tools/orchestrator-guard.sh is allowed
RED EXIT=1
```

Restored (`git checkout HEAD -- …`) → 125 ok, 0 not ok.

Base `nixosModules/seatLane.nix` against the branch's `flake.nix`:

```
$ nix build .#checks.x86_64-linux.seat-eval -L --no-link
       error: attribute 'FACTORY_HOUSE_GUARD' missing
       at …/flake.nix:1703:13
       … ) "seat-eval: seat@ must pin FACTORY_HOUSE_GUARD to the tree's guard";
SEAT-EVAL RED EXIT=1
```

Restored → `seat-eval` exit 0. Both reds match the section's Step 1 exactly, and the
commit body's pasted reds are truthful.

## Mutants

`mutants_total: 9`, `mutants_killed: 7`, `mutants_outside_named: 5`.

| id | mutation | killed by |
|---|---|---|
| A (named) | the `'tools/orchestrator-guard.sh\|file'` entry removed | (a)–(e) all `not ok`, (f) `ok` — the section's prediction verbatim |
| B (named) | the entry's kind `file` → `dir` | `not ok 4 … rm … is denied with the file reason` / `` `[[ "$output" == *"orchestrator-guard.sh"* ]]' failed `` (line 810) — the deny survives but prints the plan reason; (a),(b),(c),(e) also red |
| C (named) | header `448` → `442` | `not ok 1 the guard never raises …` / `sweep data-row count 448 does not match header 442` (line 1499) |
| D (named) | `nixosModules/seatLane.nix:179` removed | `seat-eval` red: `error: attribute 'FACTORY_HOUSE_GUARD' missing` |
| E (extra) | `file_reason`'s `'tools/orchestrator-guard.sh'` case deleted (falls to the override default) | (a)–(e) red |
| F (extra) | the delete-family arm's `_ret=$ovr_reason` → `_ret=$OVERRIDE_REASON` | `not ok 4` |
| G (extra) | `main`'s Edit/Write arm `file_reason "$rel"; deny "$_ret"` → `deny "$OVERRIDE_REASON"` | `not ok 5` |
| I (extra) | the `is_protected_dir_or_ancestor` branch no longer selects the entry's reason (`:918-924`) | **SURVIVES** — 125/125 ok |
| J (extra) | the raw-text fallback no longer selects the entry's reason (`:980-986`) | **SURVIVES** — 125/125 ok |

Every mutant the section names dies. Two branches of the refactor the section did not ask
for are untested (MINOR-3).

## Checks

In a fresh clone of `task/OG3` (`git clone -q --branch task/OG3 …`), all with `--rebuild`:

| check | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass (`ok 632 …`, exit 0) |
| `… seat-eval …` | pass (exit 0) |
| `… host-core …` | pass (exit 0) |
| `… lint …` | pass (exit 0) |
| `nix develop -c bats tests/unit/91-orchestrator-guard.bats tests/unit/93-house-guard.bats` | 137 ok, 0 not ok |
| `nix develop -c shellcheck tools/orchestrator-guard.sh` | exit 0 |
| `python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | clean (no MAP change owed) |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |
| `nix develop -c githooks/pre-commit` | exit 1 — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` |

No python changed, so no ruff run is owed.

The `pre-commit` exit 1 is **not** a defect of this branch: `pkgs/evidence/tasks.py:372
landed_subjects()` judges a task landed from the git log's commit subjects, so once
`fc97e47` exists on the branch the derived queue drops OG3 (`-… CR4 OG3 PW1glm …` →
`+… CR4 PW1glm …`). At commit time the hook was green; the regeneration is the artefact of
running it on the task branch after the commit, and the board is correctly left uncommitted
(matrix item 6's "no board commit"). Verdict-neutral, recorded for the record.

**The refactor's regression evidence** (the orchestrator's standing question about
+117/−31): all 442 pre-existing sweep rows were driven through the base guard
(`git show ee0b4c6:tools/orchestrator-guard.sh`) and the branch guard with the same fixture
project, capturing decision *and* reason per row:

```
$ diff old.out new.out && echo "IDENTICAL (verdict+reason) over 442 rows"
IDENTICAL (verdict+reason) over 442 rows
   171 ALLOW / 271 DENY;  stderr captured over both runs: 0 bytes
```

So no pre-existing rule changed its verdict or its wording. The refactor is a per-entry
deny reason (`file_reason`, `file_reasons[]`, `ovr_reason`/`ovr_reason_chosen`) — a MINOR
to record, not a MAJOR.

## Touches and commit

`git diff ee0b4c6..HEAD --name-only` → `flake.nix`, `nixosModules/seatLane.nix`,
`tests/unit/91-orchestrator-guard-sweep.txt`, `tests/unit/91-orchestrator-guard.bats`,
`tools/orchestrator-guard.sh` — five files, every one inside the section's `touches`.
Nothing outside; the plan file is untouched; no board commit; `docs/MAP.md` correctly
unchanged.

One commit, `fc97e47`. Subject byte-identical to the section's `commit subject`
(219 bytes, compared programmatically against the plan's line: `IDENTICAL`). The body
states the why, pastes the reds and the greens and the four mutants; the two trailers
follow a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run hg1)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

Driver record `/home/dalhaka/factory/runs/hg1/OG3.result` confirmed:
`checks_verified: unit=pass seat-eval=pass host-core=pass lint=pass`,
`checks_verified_src: unit=run seat-eval=run host-core=run lint=run`, `touches_extra 0`,
`touches_disclosed 0`, `FACTORY-COMMITS 1`, head `fc97e47`, base `ee0b4c6`.

## Findings

### MAJOR-1 — the guard protects the *workspace's* copy, not the checkout it is read from: a seat can still rewrite the live guard by absolute path

`tools/orchestrator-guard.sh:152-165` — `PROTECTED_PATHS` entries are "relative to
`CLAUDE_PROJECT_DIR`" (the file's own comment). For a seat, `CLAUDE_PROJECT_DIR` is the
workspace, not the checkout the guard is read from:
`pkgs/dsh-openrouter/dsh-openrouter.sh:656` "CLAUDE_PROJECT_DIR is supplied by the bridge
from `projectDir` (== the workspace)", `:738` `projectDir: $workspace`;
`pkgs/dsh-openrouter/hook-guard.py:597` `env["CLAUDE_PROJECT_DIR"] = project_dir` and
`:674` `project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "") or os.getcwd()`.
The guard the seat obeys is `FACTORY_HOUSE_GUARD` = `/home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh`
(`nixosModules/seatLane.nix:179`), and that path is writable from the unit
(`nixosModules/seatLane.nix:229-235`, `-/home/${cfg.operatorUser}/nixos-agent-env`, `User =
cfg.operatorUser` at `:210`).

Measured against the branch's guard, `CLAUDE_PROJECT_DIR` = a seat workspace:

```
== PROJECT = a seat workspace (the deployed case) ==
DENY   cd /home/dalhaka/nixos-agent-env && sed -i s/deny/allow/ tools/orchestrator-guard.sh   [orchestrator-guard.sh is the operator's; ask for it]
ALLOW  printf x > /home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  cp /tmp/g.sh /home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  rm -f /home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  sed -i s/a/b/ /home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh
```

(The same five with `CLAUDE_PROJECT_DIR` = the checkout deny with the guard's reason, which
is why the section's tests — whose fixture project *is* the tree under test — are all
green.) Contract item 1 states "any spelling the arms already normalise: relative, `./`,
`$HOME/nixos-agent-env/…`, the absolute checkout path … is denied"; the absolute checkout
path is not denied where it matters, so the task's stated goal ("a seat must not be able to
edit the rules it obeys", the plan's Goal paragraph and the comment at
`tools/orchestrator-guard.sh:162-164`) is not reached and SD8's MINOR-11 stays open.

The gap is the section's, not the seat's: item 1 forbade a new arm and prescribed the
`file` kind "like the ritual override", which carries the same project-relative limit. Note
that the existing mechanism already has a kind that does not: a `dir` entry denies the live
checkout's path from a seat workspace, because the plan arm also matches the relative
spelling textually —

```
== NEW guard, PROJECT = a seat workspace ==
ALLOW  rm -f $HOME/nixos-agent-env/.claude/ritual-override
ALLOW  rm -f ~/nixos-agent-env/tools/orchestrator-guard.sh
DENY   rm -f $HOME/nixos-agent-env/docs/superpowers/plans/x.md   [plan files change only through the Edit and Write tools …]
```

— so a re-typed section can close it without inventing an arm (an absolute-path entry, or
the guard resolving `FACTORY_HOUSE_GUARD`/its own `$0` as a protected path in addition to
the project-relative one).

### MINOR-1 — the `$HOME/…` spelling in contract item 1 is not a spelling the arms normalise

`tools/orchestrator-guard.sh:165`. Measured, `CLAUDE_PROJECT_DIR` = the checkout, on both
the base and the branch guard:

```
NEW: ALLOW  rm -f $HOME/nixos-agent-env/.claude/ritual-override
NEW: DENY   rm -f ~/nixos-agent-env/.claude/ritual-override   [the ritual override is the operator's; ask for it]
NEW: ALLOW  rm -f $HOME/nixos-agent-env/tools/orchestrator-guard.sh
NEW: DENY   rm -f ~/nixos-agent-env/tools/orchestrator-guard.sh   [orchestrator-guard.sh is the operator's; ask for it]
```

`~` is collapsed, `$HOME` is not (the guard never expands variables). The new entry behaves
exactly like the ritual override, so this is inherited, not introduced — but the section
asserted a coverage the arms do not have, and no test covers any absolute spelling.

### MINOR-2 — the entry silently makes `tools/` a protected ancestor directory; six pre-existing command shapes flip ALLOW → DENY, none of them tested or mentioned in the commit body

`tools/orchestrator-guard.sh:165` with `file_dirs+=("${_lex%/*}")` (`:740`): a `file`
entry's parent directory names it for the delete family, so `tools` joins `.claude`.
Measured, base guard vs branch guard, `CLAUDE_PROJECT_DIR` = the checkout:

```
-ALLOW  rm -rf tools            +DENY  [orchestrator-guard.sh is the operator's; ask for it]
-ALLOW  mv tools /tmp/          +DENY  [orchestrator-guard.sh …]
-ALLOW  chmod -R 755 tools      +DENY  [orchestrator-guard.sh …]
-ALLOW  tar -xzf x.tgz -C tools +DENY  [orchestrator-guard.sh …]
-ALLOW  git checkout -- tools   +DENY  [orchestrator-guard.sh …]
-ALLOW  git restore tools       +DENY  [orchestrator-guard.sh …]
-ALLOW  find tools -name '*.sh' -delete   +DENY   -ALLOW rm -rf tools/*  +DENY
-ALLOW  rsync -a /tmp/x tools/  +DENY      -ALLOW rmdir tools   +DENY
-ALLOW  xargs rm < tools/list   +DENY  [the ritual override is the operator's; ask for it]
```

This follows from Assumption 1's stated `file` semantics, so it is intended-by-mechanism
and none of the 442 pre-existing sweep rows moved — but it is a real widening of the
orchestrator's own refusals, it has no test and no sweep row, and the commit body does not
name it.

### MINOR-3 — two branches of the new per-entry-reason machinery are untested (mutants I and J survive)

`tools/orchestrator-guard.sh:918-924` (the `is_protected_dir_or_ancestor` branch) and
`:980-986` / `:992-998` (the raw-text fallback). Deleting the reason-selection from either
leaves all 125 tests green:

```
mutant I applied (the ancestor branch no longer chooses the entry reason)
$ nix develop -c bats tests/unit/91-orchestrator-guard.bats | grep -c '^not ok'
0
mutant J applied (raw-text fallback no longer chooses the entry reason)
0
```

### MINOR-4 — the reason and the entry can disagree on the descendant path

`tools/orchestrator-guard.sh:925-927` (`ovr_desc_seen`) never sets `ovr_reason_chosen`, so a
`tools/` descendant denied through the xargs arm prints the ritual override's wording:

```
DENY   xargs rm < tools/list   [the ritual override is the operator's; ask for it]
```

Contract item 1 asks for "the reason the override arm prints for its file, with
`orchestrator-guard.sh` in place of the override's name"; on this path the substitution does
not happen. No test covers it.

### MINOR-5 — `ovr_reason` is declared `local` twice

`tools/orchestrator-guard.sh:703` (`local plan_reason ovr_reason`) and `:711`
(`local ovr_reason ovr_reason_chosen`). Harmless in bash and shellcheck-clean; leftover from
the rename of `override_reason`.

### MINOR-6 — the file's header contract was not updated

`tools/orchestrator-guard.sh:3-37` still enumerates four rules and names only
`.claude/ritual-override` as the protected file (rule 3), and `:51-52`'s "One PROTECTED
list" paragraph is unchanged. A reader of the header cannot learn that the guard now
protects itself; the only prose is the two comments at `:162-164` and `:179-186`. The
section asked for "a one-line comment", so this is a record, not an omission of a stated
requirement.

## Verdict

**REJECTED** on MAJOR-1. The mechanics of the section are met and the work is honest — reds
real, mutants A–D dead, four checks green, one commit with the exact subject, no file
outside `touches`, and a +117/−31 refactor proven verdict-identical on all 442 pre-existing
sweep rows and all 119 pre-existing tests. But the control does not hold where it was built
to hold: with `CLAUDE_PROJECT_DIR` set to a seat's workspace — the deployment contract item
4 exists for — `printf x > /home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh` is
allowed, so a seat can still edit the rules it obeys and MINOR-11 is not closed.
`plan_defect: underspecified` (a project-relative mechanism specified for a cross-project
threat, with "no new arm" ruling out the fix), secondary `wrong-fact` (contract item 1 names
the `$HOME/…` and absolute-checkout spellings as covered; measured, they are not). Re-type
OG3 with a protected path that is absolute (or resolved from `FACTORY_HOUSE_GUARD` / the
guard's own `$0`) plus a test whose fixture project is NOT the tree holding the guard —
that fixture is what would have caught this.
