---
plan_defect: implementer
plan_defect_secondary: wrong-fact
mutants_total: 10
mutants_killed: 7
mutants_outside_named: 2
---
# Opus gate — seat run sd2, task SD7 — REJECTED

## Summary

The code meets the section's interfaces almost exactly: `seat-submit drive` requires a port
and the driver's three-file skill set with the section's literal messages, `seat-run` puts
`--model` before the `--`, `seat-drive.sh` resolves the orchestrate row through
`factory_route --rung 1`, seeds `$FACTORY_ROOT/drive/<stamp>.dsh-home` with
`factory_seed_dsh_home`, submits and prints the id, and the VM's step 12 proves a real drive
seat answers on 43202 with the wrapper's explicit model in the isolated home's
`settings.yaml`. Every acceptance check is green in a fresh clone, including `seat-vm`
under `--rebuild`; the script is shellcheck-clean and the lint gate's
`find tools -name '*.sh'` arm (`githooks/pre-commit:19`, `flake.nix:1012`) does gate it.

Two MAJORs stop it, both about tests that cannot fail:

1. `tests/unit/88-seat-drive.bats:111` — `! grep -q 'saved/one' …` is exempt from `errexit`,
   so the one assertion that pins the section's central guarantee (judgement call 10: the
   operator's saved selection never reaches a drive job) can never turn the test red. The
   section's named mutant for it survives its named test, and a one-line leak inside
   `seat-drive.sh` itself survives the whole `unit` suite — measured, not argued.
2. `tools/factory/seat/seat-drive.sh:132-148` — the 60-second `url.txt` wait, and the
   `seat-drive: no url.txt after 60 s …` refusal, have no test at all. The section says
   this mutant is "covered by the VM (the URL line)", but the VM's step 12 (interface 4)
   never invokes `seat-drive.sh`; deleting the whole wait block leaves every test green.
   That one is the plan's fact, not the seat's.

## Contract items

Interface 1 — `seat-submit drive`:

| item | verdict | evidence |
| --- | --- | --- |
| `mode` choices become `headless\|web\|drive` | met | `pkgs/seat/seat-submit.py:171` `p.add_argument("mode", choices=["headless", "web", "drive"])` |
| `--port` required, int 1024–65535, else exit 2 `drive needs --port` | met | `:205-207` `if args.port is None or not (1024 <= args.port <= 65535): print("drive needs --port", …); return 2` |
| `--brief` refused (exit 2) | met | `:208-210`; test `tests/seat/test_seat_submit.py:814` |
| `--dsh-home` must hold the three entries, message names the first missing one | met, literal | `:53-57` `DRIVE_SKILLS`, `:60-66` `_missing_drive_skill`, `:211-219` prints `seat-submit: --dsh-home {path} lacks {missing} — the driver's skill set (ln -s ~/flakes/dsh-harness/skills <dsh-home>/skills)` |
| files or symlinks to files | met | `os.path.isfile` follows symlinks (`:64`) |
| refusal before any job dir | met | the drive block is at `:204`, `os.makedirs` at `:234`; VM asserts the job count is unchanged (`tests/integration/seat-vm.nix:545-547`) |
| `job.json` today's shape with `"mode": "drive"` | met | `:245-254`; pinned at `tests/seat/test_seat_submit.py:805-808` |
| `web` unchanged, its port still optional | met | the whole block is under `if args.mode == "drive"`; the pre-existing web tests stay green (47 passed) |

Interface 2 — `seat-run` for `mode == "drive"`:

| item | verdict | evidence |
| --- | --- | --- |
| the web command plus `--model <job.model>` before the `--` | met | `pkgs/seat/seat-run.py:105-117` |
| `url.txt` and the printed URL as for web | met | `:129-133` (shared with the web arm) |
| web keeps no `--model` | met | `:118-128` |

Interface 3 — `tools/factory/seat/seat-drive.sh`:

| item | verdict | evidence |
| --- | --- | --- |
| bash, sources `factory-lib.sh` | met | `:16-21` |
| `--port` default 43210, `--workspace` default `$FACTORY_TOOLBOX_REPO` | met | `:29-30` |
| `factory_route --rung 1 orchestrate any any`, exit 3 → `die 3` | met | `:75-77`; the live table resolves it: `nix develop -c … factory_route --rung 1 orchestrate any any` → `deepseek/deepseek-v4-pro-0813 medium` |
| the two env overrides, each printing an `(override)` line | met in substance | `:85-92`; prefix deviates — MINOR-3 |
| prints `seat-drive: orchestrate/any/any rung 1 → <model> <effort>` | met | `:94` |
| seeds `$FACTORY_ROOT/drive/<UTC %Y%m%d-%H%M%S>.dsh-home` via `factory_seed_dsh_home`, prints `seat-drive: DSH_HOME <path>` | met | `:99-104` |
| never the shared home | met in code, **untested** | `:99-104`; see MAJOR-1 |
| `${SEAT_SUBMIT:-seat-submit}`, else `nix run "$FACTORY_TOOLBOX_REPO#seat-submit" --` | met | `:108-114` |
| the submit argv and `[--no-start]` | met | `:116-124`; pinned word-by-word at `tests/unit/88-seat-drive.bats:93-104` |
| prints the job id, exit 0 | met | `:126-127` |
| waits up to 60 s for `/var/lib/seat/jobs/<id>/url.txt`, prints its line, else the refusal on stderr | met in code, **no test** | `:132-148`; see MAJOR-2 |

Interface 4 — `seat-vm` step 12: every clause met, and green under `--rebuild` (log
excerpts under **Checks**): the three-file fixture (`tests/integration/seat-vm.nix:510-514`),
`url.txt == http://10.100.4.2:43202` (`:526-528` and the run log
`machine # [ 32.838248] seat-run[1392]: http://10.100.4.2:43202`), the host's `curl`
(`:530-532`), the `ss -ltn` triple with `0.0.0.0` and `[::]` both negative (`:535-539`),
`grep -q 'model: deepseek/deepseek-v4-flash' /tmp/drive-home/settings.yaml` (`:541-543`), and
the skill-less refusal with no new job dir (`:545-553`). The step number is 12, i.e. it
follows SD6's 10 and 11, as Assumption 24 requires.

## Red before green

| test | red | evidence |
| --- | --- | --- |
| `tests/seat/test_seat_submit.py::test_drive_requires_port_and_skill_set`, `::test_drive_refuses_brief` | yes | base `pkgs/seat/seat-submit.py` + branch tests → `seat-submit: error: argument mode: invalid choice: 'drive' (choose from 'headless', 'web')` / `SystemExit: 2` |
| `tests/seat/test_seat_run.py::test_drive_passes_the_model_before_the_dashes` | yes | base `pkgs/seat/seat-run.py` + branch tests → `assert seen["cmd"] == [ …, "--model", …]` fails (the base's web argv has none) |
| `tests/unit/88-seat-drive.bats` (all six) | yes | with `tools/factory/seat/seat-drive.sh` moved away: `not ok 1 …` through `not ok 6 …`, each `[ "$status" -eq 0 ]' failed` (127) and `[ "$status" -eq 2 ]' failed` for the port case |
| `tests/integration/seat-vm.nix` step 12 | yes | see mutant M8: with `seat-run`'s drive arm disabled the VM dies at `grep -q 'model: deepseek/deepseek-v4-flash' /tmp/drive-home/settings.yaml` |

Combined red run (base implementation, branch tests):

```
FAILED tests/seat/test_seat_run.py::test_drive_passes_the_model_before_the_dashes
FAILED tests/seat/test_seat_submit.py::test_drive_requires_port_and_skill_set
FAILED tests/seat/test_seat_submit.py::test_drive_refuses_brief - SystemExit: 2
3 failed, 44 passed in 0.35s
```

Restored: `47 passed in 0.07s`; `bats tests/unit/88-seat-drive.bats` → `ok 1 … ok 6`.

**One assertion has no red of its own:** the selection strip (MAJOR-1). Making it red is
impossible without editing the line.

## Mutants

Named by the section — 8; killed 6 by the test the section names, 1 (M5) only by another
file in the same acceptance check, 1 (M7) not at all.

| # | mutant | killer named | result | evidence |
| --- | --- | --- | --- | --- |
| M1 | `seat-submit.py:205` → `if args.port is not None and not (1024 <= args.port <= 65535)` | the port rule | KILLED | `tests/seat/test_seat_submit.py:754: AssertionError` `assert 0 == 2` |
| M2 | `DRIVE_SKILLS = ("AGENTS.md",)` | the skill-set fixture | KILLED | `tests/seat/test_seat_submit.py:781: AssertionError` `assert 0 == 2` |
| M3 | `seat-run.py` `--model` moved after `--` | argv equality | KILLED | `tests/seat/test_seat_run.py:249: AssertionError` `At index 4 diff: '--' != '--model'` |
| M4 | `seat-drive.sh:99-104` → `dsh_home=$FACTORY_SHARED_DSH_HOME_SRC`, no seeding | the recorder's path | KILLED | `88-seat-drive.bats, line 97` `[[ "${argv[4]}" == "$FACTORY_ROOT/drive/"*".dsh-home" ]]' failed` |
| M5 | `factory-lib.sh:898` → `cp -- "$src/settings.yaml" "$dst/settings.yaml"` | `saved/one` present in `88-seat-drive.bats` | **survives its named test**; killed by `tests/unit/80-seat-driver.bats:278` in the same `unit` check | `bats tests/unit/88-seat-drive.bats` → `ok 1 … ok 6` (all six green with the strip removed); `bats tests/unit/80-seat-driver.bats` → `not ok 9 factory_seed_dsh_home copies settings.yaml without the saved model selection and symlinks the rest` |
| M6 | `seat-drive.sh:89` → `if false; then` (ignore `OPENROUTER_REASONING_EFFORT`) | `--effort high` | KILLED | `88-seat-drive.bats, line 128` `[ "${argv[8]}" = "medium" ]' failed` |
| M7 | `seat-drive.sh:132-148` deleted (never wait, never print `url.txt`) | "covered by the VM (the URL line)" | **SURVIVES** | `bats tests/unit/88-seat-drive.bats` → `ok 1 … ok 6`; `pytest tests/seat -q` → `47 passed`; `shellcheck` clean; `grep -n 'seat-drive' tests/integration/seat-vm.nix` prints nothing (exit 1) — the VM cannot execute the script |
| M8 | `seat-run.py:105` → `if False:` (drive drops `--model`) | the VM's `settings.yaml` line | KILLED | `!!! RequestedAssertionFailed: command 'grep -q 'model: deepseek/deepseek-v4-flash' /tmp/drive-home/settings.yaml' failed (exit code 1)`; `error: Cannot build '…-vm-test-run-seat-behind-broker.drv'` |

Outside the named set — 2, both survive:

| # | mutant | result | evidence |
| --- | --- | --- | --- |
| O1 | `DRIVE_SKILLS = ("skills/driving/SKILL.md",)` (drop the planning and AGENTS checks) | SURVIVES | `pytest tests/seat -q` → `47 passed`; the VM's negative case uses `/tmp/dsh`, which also lacks `skills/driving/SKILL.md`, so it still prints the expected message |
| O2 | `seat-drive.sh:102` + `cp -- "$FACTORY_SHARED_DSH_HOME_SRC/settings.yaml" "$dsh_home/settings.yaml"` — the operator's saved selection leaks into the drive job | SURVIVES | `bats tests/unit/88-seat-drive.bats tests/unit/80-seat-driver.bats` → 87 `ok`, zero `not ok`; the full `bats tests/unit` (632 tests) shows no `not ok` attributable to it |

`mutants_total 10, mutants_killed 7, mutants_outside_named 2.`

## Checks

All in the fresh clone `…/scratchpad/SD7/gate-sd2-SD7` (branch `task/SD7`, HEAD `eff8ed7`),
each with `--rebuild`:

- `nix build .#checks.x86_64-linux.seat-unit -L --no-link --rebuild` → `seat-unit-tests> 47 passed in 0.09s`, exit 0
- `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` → `unit-tests> ok 632 …`, exit 0
- `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` → `lint> Found 0 warnings and 0 errors.`, exit 0
- `nix build .#checks.x86_64-linux.seat-vm -L --no-link --rebuild` → exit 0; step 12 in the log:
  `machine: (finished: must succeed: su - dalhaka -c 'seat-submit drive --workspace /tmp/ws --dsh-home /tmp/drive-home --model deepseek/deepseek-v4-flash --effort off --port 43202', in 0.16 seconds)`,
  `machine # [ 32.838248] seat-run[1392]: http://10.100.4.2:43202`,
  `machine: (finished: waiting for success: curl -s --max-time 5 -o /dev/null http://10.100.4.2:43202/, in 1.39 seconds)`,
  `machine: (finished: must succeed: grep -q 'model: deepseek/deepseek-v4-flash' /tmp/drive-home/settings.yaml, in 0.02 seconds)`
- `nix develop -c githooks/pre-commit` → exit 0 (it re-derived the board's queue block from the
  live `~/factory/runs` state, which now records SD7 as run; the gated `lint` check, which sees
  only the tree, reproduces the committed block exactly — the committed hunk is correct)
- `nix develop -c ruff check pkgs/seat tests/seat` → `All checks passed!`;
  `ruff format --check pkgs/seat tests/seat` → `6 files already formatted`
- `nix develop -c shellcheck tools/factory/seat/seat-drive.sh` → clean;
  `find tools -name '*.sh' -print | grep seat-drive` → `tools/factory/seat/seat-drive.sh`, so
  `githooks/pre-commit:19` and `flake.nix:1012` do gate it (no list edit was owed)
- `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` → exit 0
- `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → silent, exit 0

No red check.

## Touches and commit

Nine files; seven are the section's `touches`, two are exempt by rule:

- `pkgs/seat/seat-submit.py`, `pkgs/seat/seat-run.py`, `tests/seat/test_seat_submit.py`,
  `tests/seat/test_seat_run.py`, `tests/integration/seat-vm.nix`,
  `tools/factory/seat/seat-drive.sh`, `tests/unit/88-seat-drive.bats` — in `touches`.
- `docs/MAP.md` — the count line only (`- tests/unit — 23 files` → `24 files`), mandatory for
  the new bats file and exempt by rule; regeneration reproduces it byte-for-byte.
- `docs/OPERATIONS.md` — one line, entirely inside `<!-- tasks:begin -->…<!-- tasks:end -->`
  (`SD2 SD3 SD7` and the plan basename added to the derived queue); exempt by rule.

Commit: exactly one (`git rev-list --count 0853f10..HEAD` → `1`), `eff8ed7`. The subject is
byte-identical to the section's (278 bytes each, `diff` of the extracted strings is empty).
Trailers after a blank line, in the WORKSPACE RULES order:
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sd2)`
then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. The plan file is untouched;
no board or "landed" commit. The driver's record
(`/home/dalhaka/factory/runs/sd2/SD7.result`) agrees: `FACTORY-RESULT status=done`,
`checks_verified: seat-unit=pass seat-vm=pass unit=pass lint=pass`,
`checks_verified_src: seat-unit=run seat-vm=run unit=run lint=run`, `touches_extra: 0`,
`FACTORY-COMMITS 1`, head `eff8ed7…`.

## Findings

### MAJOR-1 — `tests/unit/88-seat-drive.bats:111`: the isolation assertion cannot fail, and the section's own mutant survives it

```
111:  ! grep -q 'saved/one' "$dsh_home/settings.yaml"
```

A command whose return value is inverted with `!` is exempt from `errexit` (bash manual:
"…or if the command's return value is being inverted with `!`"), so when `grep` *finds*
`saved/one` the line yields 1, the shell does not exit, and the test walks on to its next
assertion and passes. Demonstrated directly:

```
$ cat demo.sh
set -e
printf 'saved/one\n' >demo.txt
! grep -q 'saved/one' demo.txt
echo "REACHED: the ! assertion did not stop the script"
$ bash demo.sh; echo "script exit=$?"
REACHED: the ! assertion did not stop the script
script exit=0
```

Consequences, both measured:

- The section's named mutant for this assertion (`cp` instead of
  `factory_copy_settings_without_selection`, `tools/factory/seat/factory-lib.sh:898`) leaves
  all six cases of `88-seat-drive.bats` green. It is caught only by a *pre-existing* test from
  an earlier plan, `tests/unit/80-seat-driver.bats:278`
  (`not ok 9 factory_seed_dsh_home copies settings.yaml without the saved model selection…`).
- `seat-drive.sh`'s own half of judgement call 10 is therefore unpinned. Mutant O2 — one line
  after `factory_seed_dsh_home "$dsh_home"` (`tools/factory/seat/seat-drive.sh:102`):

  ```
  cp -- "${FACTORY_SHARED_DSH_HOME_SRC:-$HOME/.local/share/dsh-openrouter}/settings.yaml" "$dsh_home/settings.yaml"
  ```

  puts the operator's saved picker selection into every drive job — exactly what the
  decision addendum forbids and what this section exists to prevent — and the entire
  `unit` suite stays green (`bats tests/unit/88-seat-drive.bats tests/unit/80-seat-driver.bats`
  → 87 `ok`, no `not ok`; the full `bats tests/unit`, 632 tests, likewise shows nothing).

The Global Constraints the seat was given name this trap by its sibling form
(`] && [` chains are vacuous under errexit) and require every assertion to have a mutant that
turns it red. `run ! grep …` with a `[ "$status" -ne 0 ]`, or `run grep -q …` plus
`[ "$status" -eq 1 ]`, would be killable.

### MAJOR-2 — `tools/factory/seat/seat-drive.sh:132-148`: the whole `url.txt` wait has no test that can fail; the section's stated coverage is false

The section's Tests block says: "the wait → mutant: never wait → covered by the VM (the URL
line)". The VM never runs this script:

```
$ grep -n 'seat-drive' tests/integration/seat-vm.nix
$ echo $?
1
```

and all six bats cases pass `--no-start`, which skips the branch. Deleting lines 132-148
outright (replacing them with `:`) leaves everything green:

```
$ nix develop -c bats tests/unit/88-seat-drive.bats
ok 1 seat-drive resolves the orchestrate row, seeds an isolated home, and submits drive
ok 2 OPENROUTER_REASONING_EFFORT overrides the routed effort and prints the override
ok 3 OPENROUTER_MODEL overrides the routed model and prints the override
ok 4 --dsh-home skips seeding and submits the given home
ok 5 a table without the orchestrate row routes to the any/any/any default
ok 6 --port 80 is refused
$ nix develop -c pytest tests/seat -q
47 passed in 0.07s
```

So interface 3's last clause — the 60-second wait, the printed URL line, and the
`seat-drive: no url.txt after 60 s — journalctl -u seat@<id>` refusal — is entirely
unmeasured, and the plan's claim that the VM covers it is wrong. This one is the plan's
defect, not the seat's: the seat implemented the clause as written and used the fixtures the
section listed. Killing it needs a seam the section never asked for (the jobs dir is
hardcoded at `:133`, so a bats case cannot point the wait at a tmpdir), or a VM step that
runs `seat-drive.sh` with `SEAT_SUBMIT` pointed at the real `seat-submit`.

## Verdict

**REJECTED.** Two MAJORs: the section's central isolation guarantee is pinned by an assertion
that cannot fail (`tests/unit/88-seat-drive.bats:111`), and the `url.txt` wait
(`tools/factory/seat/seat-drive.sh:132-148`) has no test at all while the section claims the
VM covers it. Everything else is met: every interface clause, all four acceptance checks green
under `--rebuild` including `seat-vm`, one commit with a byte-identical subject, `touches`
clean, and 7 of 10 mutants dead.

MINOR-1 — `tests/seat/test_seat_submit.py:758`: one skill-set fixture, not the three the
section asked for ("three fixtures, one missing file each"). Mutant O1
(`DRIVE_SKILLS = ("skills/driving/SKILL.md",)`) survives all 47 seat tests and the VM's
negative case, because both negative fixtures happen to lack `skills/driving/SKILL.md`; the
`skills/planning/SKILL.md` and `AGENTS.md` arms of the rule are untested.

MINOR-2 — `tests/integration/seat-vm.nix:510-514`: the discriminating fixture the section
named for the VM mutant ("a home whose `settings.yaml` pre-holds another model") is absent —
`/tmp/drive-home` carries no `settings.yaml` at all. The named mutant still dies (the grep
fails on a missing file), so it is not gating, but the assertion proves "the file mentions
the model" rather than "the wrapper overwrote another model".

MINOR-3 — `tools/factory/seat/seat-drive.sh:87,91`: the override lines go through
`factory_log`, which prefixes `basename "$0"` (`tools/factory/seat/factory-lib.sh:29-32`), so
they print `seat-drive.sh: explicit effort (override)` while the section specifies
`seat-drive: explicit <model|effort> (override)` and the script's own two `printf` lines
(`:94`, `:103`) hardcode `seat-drive:`. The bats cases match only `*"(override)"*`, so
nothing pins the prefix either way.

MINOR-4 — the commit body states the why but pastes neither the red command with its output
nor the green check names, which the gate's commit-convention item asks for.
