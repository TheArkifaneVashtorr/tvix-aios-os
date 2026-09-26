---
plan_defect: none
mutants_total: 17
mutants_killed: 16
mutants_outside_named: 5
---
# Opus gate — seat run sd7f, task SD7b — APPROVED

## Summary

SD7b carries SD7's commit as a cherry-pick onto main and closes both MAJORs and all
three named MINORs of `docs/reviews/2026-09-08-opus-review-sd2-SD7.md`, each one
measured in a fresh clone:

1. **MAJOR-1 (the isolation assertion).** `tests/unit/88-seat-drive.bats:115-116` is now
   `run grep -q 'saved/one' "$dsh_home/settings.yaml"` followed by `[ "$status" -eq 1 ]`,
   and `grep -c '^ *!' tests/unit/88-seat-drive.bats` → `0`. The prior review's own leak
   probe (mutant **B**: a `cp` of the shared `settings.yaml` after the seed, which used to
   pass 632 unit tests) now turns `88-seat-drive.bats` itself red, and so does mutant **A**
   (`cp` for `factory_copy_settings_without_selection` in `factory-lib.sh:898`).
2. **MAJOR-2 (the untested wait).** `SEAT_DRIVE_JOBS_DIR` and `SEAT_DRIVE_URL_TIMEOUT`
   are seams (`tools/factory/seat/seat-drive.sh:137-138`, both named in the header comment
   `:15-18`, production defaults `/var/lib/seat/jobs` and `60` unchanged), and cases (g)
   and (h) pin the URL line and the timeout message. Mutants **C** and **D** die; so do two
   mutants of my own that ignore either seam.
3. The three skill-set fixtures are parametrised (mutant **E** kills two of the three
   cases), the VM's `/tmp/drive-home/settings.yaml` pre-holds `some/other` with a
   `machine.fail` after the job (mutant **F** dies in a real `seat-vm` build), and the two
   override lines carry the `seat-drive:` prefix (mutant **G** dies).

Twelve named mutants (SD7b's A–G plus SD7's five still-distinct ones), twelve dead. Five
mutants outside the named set, four dead. Every acceptance check green under `--rebuild`
in the fresh clone, including `seat-vm`. One commit, subject byte-identical (277 bytes
both ways), `touches` clean, the plan file untouched.

One survivor, non-gating and inherited from SD7, is recorded as MINOR-1: `seat-submit
drive`'s port **range** arm has no test (only the missing-port arm does).

## Contract items

Clone: `…/scratchpad/SD7b/gate-sd7f-SD7b`, branch `task/SD7b`, HEAD
`5a256f3be7185d25a5c65902e5e8d9e55d7d328e`, base `28db2d6`.

### Item 1 — the isolation assertion (closes MAJOR-1)

| clause | verdict | evidence |
| --- | --- | --- |
| `run grep -q …` on one line, `[ "$status" -eq 1 ]` on the next | met, literal | `tests/unit/88-seat-drive.bats:115-116` |
| no `!`-prefixed command left in the file | met | `grep -c '^ *!' tests/unit/88-seat-drive.bats` → `0` (exit 1); the only two `!` hits are a comment at `:114` and `[ ! -e … ]` at `:157`, which is a `test` operator, not an inverted command |
| mutant A red in `88-seat-drive.bats` itself | met | see **Mutants** |
| mutant B (the leak line after the seed) red | met | see **Mutants** |

### Item 2 — the wait's seams and two cases (closes MAJOR-2)

| clause | verdict | evidence |
| --- | --- | --- |
| `SEAT_DRIVE_JOBS_DIR` (default `/var/lib/seat/jobs`) for the `url.txt` path | met | `tools/factory/seat/seat-drive.sh:137`, `:139` |
| `SEAT_DRIVE_URL_TIMEOUT` (whole seconds, default 60), poll every 2 s | met | `:138`, `:142-150` (`sleep 2`, `elapsed=$((elapsed + 2))`) |
| both named in the header comment | met | `:15-18` (the section cited `:7-13`; the header comment block is `:2-18`) |
| production defaults unchanged | met | `:137-138` |
| the stderr message names the configured seconds | met, literal | `:152-153` `printf 'seat-drive: no url.txt after %s s — journalctl -u seat@%s\n' "$url_timeout" "$job_id" >&2` |
| case (g): delayed `url.txt`, `SEAT_DRIVE_URL_TIMEOUT=6`, status 0, last stdout line is the URL | met | `:176-191` — the backgrounded `( sleep 1; printf … ) &`, `[ "$status" -eq 0 ]`, `[ "$(tail -n 1 <<<"$output")" = "http://10.100.4.2:43210" ]` |
| case (h): no `url.txt`, timeout 2, `run --separate-stderr`, status 0, message on `$stderr`, stdout has the id and no `http://` | met | `:193-203` (`[ "$status" -eq 0 ]`, `[[ "$stderr" == *"no url.txt after 2 s — journalctl -u seat@20260908-120000-abcdef"* ]]`, `[[ "$output" != *"http://"* ]]`) |
| mutants C and D red on (g) and (h) | met | see **Mutants** |

### Item 3 — three skill-set fixtures (closes MINOR-1)

| clause | verdict | evidence |
| --- | --- | --- |
| parametrised over the three entries of `DRIVE_SKILLS` | met | `tests/seat/test_seat_submit.py:758-761` `@pytest.mark.parametrize("missing", ["skills/driving/SKILL.md", "skills/planning/SKILL.md", "AGENTS.md"])`, `:762` `test_drive_lacks_one_skill_is_refused`, `:720-730` `_drive_home` builds the complete home and `:765` removes exactly one |
| exit 2 and the message names the missing one | met | `:787-788` `assert rc == 2`, `assert f"lacks {missing}" in err` |
| mutant E red on the two other cases | met | see **Mutants** |

### Item 4 — the VM's pre-held selection (closes MINOR-2)

| clause | verdict | evidence |
| --- | --- | --- |
| `/tmp/drive-home/settings.yaml` pre-holds `agent-default-model:` / `  model: some/other`, owned by dalhaka | met | `tests/integration/seat-vm.nix:517-521` |
| after `url.txt`, `grep -q 'model: deepseek/deepseek-v4-flash'` succeeds | met | `:527-529` (the wait), `:544-546` |
| `machine.fail("grep -q 'some/other' …")` | met | `:547` |
| green in a real build | met | `seat-vm` log `machine: (finished: must fail: grep -q 'some/other' /tmp/drive-home/settings.yaml, in 0.02 seconds)` |
| mutant F red in the VM | met | see **Mutants** |

### Item 5 — the `seat-drive:` prefix (closes MINOR-3)

| clause | verdict | evidence |
| --- | --- | --- |
| the two override lines are `printf 'seat-drive: explicit <model\|effort> (override)\n' >&2`, not `factory_log` | met, literal | `tools/factory/seat/seat-drive.sh:90`, `:94` |
| the bats cases match the full prefixed string on `$stderr` with `run --separate-stderr` | met | `tests/unit/88-seat-drive.bats:128-134` and `:138-144` |
| mutant G red | met | see **Mutants** |

### Item 6 — the commit body (closes MINOR-4)

The body pastes the reds of (g) and (h) against the carried script and says the carried
script ignored the seam ("the carried script ignored the seam and the assertions could not
fail"); the reds of A/B (`not ok 1 … [ "$status" -eq 1 ]' failed`), of G (`not ok 2`/`not
ok 3`) and of E (`2 failed, 49 passed`); the greens after the last edit (bats `ok 8`,
`pytest … 51 passed`, `seat-unit`, `unit` `ok 634`, `seat-vm`, `lint`, `githooks/pre-commit`);
and the A–G table with the killing line for each, F from the VM build. The one list entry
not in the body is the FACTORY-RESULT block — it is in the driver's record in the grammar
(`/home/dalhaka/factory/runs/sd7f/SD7b.result:1` `FACTORY-RESULT status=done`); recorded as
MINOR-2.

### SD7's own interfaces, re-checked (the section says "SD7's contract stands")

Interface 1: `choices=["headless", "web", "drive"]` (`pkgs/seat/seat-submit.py:171`); the
drive block at `:204-219` — port (`:205-207`), `--brief` refused (`:208-210`), the skill set
(`:211-219`, message literal), all before `os.makedirs`; `job.json` carries `"mode":
"drive"` (pinned `tests/seat/test_seat_submit.py:792-823`); `web` untouched (mutant O3
proves the web argv would notice). Interface 2: `pkgs/seat/seat-run.py:105-117` puts
`--model` before the `--`, `:118-128` keeps web without it, `url.txt`/print shared at
`:129-133`. Interface 3: `seat-drive.sh` as before plus the two seams. Interface 4: VM step
12, still numbered 12 after SD6's 10 and 11.

## Red before green

| test | red command | evidence |
| --- | --- | --- |
| the seven seat tests (`test_drive_requires_port`, the three parametrised skill cases, `test_drive_writes_job_with_full_skill_set`, `test_drive_refuses_brief`, `test_drive_passes_the_model_before_the_dashes`) | base implementation (`git checkout 28db2d6 -- pkgs/seat/seat-submit.py pkgs/seat/seat-run.py`) + branch tests, `nix develop -c pytest tests/seat -q` | `7 failed, 44 passed in 0.85s`; e.g. `SystemExit: 2` from `argparse` (`invalid choice: 'drive'`) |
| `88-seat-drive.bats` cases (g), (h) and the two override cases | the carried SD7 script (`cp /home/dalhaka/factory/ws/sd2/SD7/tools/factory/seat/seat-drive.sh …`, which hardcodes the jobs dir and the 60 s wait and logs through `factory_log`) + the branch's bats file | `not ok 2` `[[ "$stderr" == *"seat-drive: explicit effort (override)"* ]]' failed`; `not ok 3` (model); `not ok 7` `[ "$(tail -n 1 <<<"$output")" = "http://10.100.4.2:43210" ]' failed`; `not ok 8` `[[ "$stderr" == *"no url.txt after 2 s — journalctl -u seat@20260908-120000-abcdef"* ]]' failed` |
| the isolation assertion (`:115-116`) | has no red of its own by construction; its reds are mutants A and B, both applied and both red in this file | below |

Restored: `bats tests/unit/88-seat-drive.bats` → `ok 1 … ok 8`; `pytest tests/seat -q` →
`51 passed in 0.07s`, working tree clean at `5a256f3`.

## Mutants

Named by the section (A–G) and by SD7's Tests block (its five that are not already A, C or F)
— 12, all dead.

| # | mutant | killer | died? | evidence |
| --- | --- | --- | --- | --- |
| A | `factory-lib.sh:898` → `cp -- "$src/settings.yaml" "$dst/settings.yaml"` | 88 t1 | yes | `not ok 1 …` `(line 116) [ "$status" -eq 1 ]' failed` |
| B | `seat-drive.sh:105` + `cp -- "${FACTORY_SHARED_DSH_HOME_SRC:-…}/settings.yaml" "$dsh_home/settings.yaml"` (the prior review's own leak probe) | 88 t1 | yes | `not ok 1 …` `(line 116) [ "$status" -eq 1 ]' failed` |
| C | the wait loop (`:142-150`) replaced by `:` | 88 (g) | yes | `not ok 7 …` `(line 190) [ "$(tail -n 1 <<<"$output")" = "http://10.100.4.2:43210" ]' failed` |
| D | the timeout `printf` (`:152-153`) dropped | 88 (h) | yes | `not ok 8 …` `(line 200) [[ "$stderr" == *"no url.txt after 2 s — journalctl -u seat@20260908-120000-abcdef"* ]]' failed` |
| E | `DRIVE_SKILLS = ("skills/driving/SKILL.md",)` | pytest | yes | `FAILED …::test_drive_lacks_one_skill_is_refused[skills/planning/SKILL.md]`, `…[AGENTS.md]`, `2 failed, 49 passed` |
| F | `seat-run.py:105` → `if False:  # job["mode"] == "drive"` | `seat-vm` | yes | `!!! RequestedAssertionFailed: command \`grep -q 'model: deepseek/deepseek-v4-flash' /tmp/drive-home/settings.yaml\` failed (exit code 1)`; `error: Cannot build '…-vm-test-run-seat-behind-broker.drv'`, exit 1 (one full VM build). Also `FAILED …::test_drive_passes_the_model_before_the_dashes` |
| G | both override lines back to `factory_log` | 88 t2/t3 | yes | `not ok 2 …` `(line 134)`, `not ok 3 …` `(line 144)`, each `[[ "$stderr" == *"seat-drive: explicit … (override)"* ]]' failed` |
| SD7-1 | `seat-submit.py:205` → `if args.port is not None and not (1024 <= args.port <= 65535)` | pytest | yes | `tests/seat/test_seat_submit.py:754: AssertionError` `assert 0 == 2` |
| SD7-2 | `DRIVE_SKILLS = ("AGENTS.md",)` | pytest | yes | `FAILED …[skills/driving/SKILL.md]`, `…[skills/planning/SKILL.md]`, `2 failed, 49 passed` |
| SD7-3 | `seat-run.py` `--model` moved after the `--` | pytest | yes | `tests/seat/test_seat_run.py:249: AssertionError`, `1 failed, 50 passed` |
| SD7-4 | `seat-drive.sh:102-107` → `dsh_home=${FACTORY_SHARED_DSH_HOME_SRC:-…}`, no seeding | 88 t1 | yes | `not ok 1 …` `(line 98) [[ "${argv[4]}" == "$FACTORY_ROOT/drive/"*".dsh-home" ]]' failed` |
| SD7-6 | `seat-drive.sh:92` → `if false; then` (ignore `OPENROUTER_REASONING_EFFORT`) | 88 t2 | yes | `not ok 2 …` `(line 133) [ "${argv[8]}" = "medium" ]' failed` |

Outside the named set — 5, four dead:

| # | mutant | died? | evidence |
| --- | --- | --- | --- |
| O1 | `seat-submit.py:205` → `if args.port is None:` (keep the missing-port arm, drop the 1024–65535 range) | **SURVIVES** | `nix develop -c pytest tests/seat -q` → `51 passed in 0.07s`; see MINOR-1 |
| O2 | `seat-submit.py:208` → `if False:` (drive stops refusing `--brief`) | yes | `FAILED …::test_drive_refuses_brief - assert 0 == 2` |
| O3 | `seat-run.py:105` → `if True:` (web also gets `--model`) | yes | `FAILED …::test_web_binds_namespace_and_writes_url` — the "web unchanged" clause is pinned |
| O4 | `seat-drive.sh:137` → `jobs_dir=/var/lib/seat/jobs` (the jobs-dir seam ignored) | yes | `not ok 1 seat-drive waits for url.txt and prints its line` `(line 190)` |
| O5 | `seat-drive.sh:138` → `url_timeout=60` (the timeout seam ignored) | yes | `not ok 1 seat-drive reports a missing url.txt after the timeout` `(line 200)` |

`mutants_total 17, mutants_killed 16, mutants_outside_named 5.` Every mutant was reverted
(`git status --porcelain` empty, HEAD `5a256f3…`) before the next was applied.

## Checks

In the fresh clone, `--rebuild` on each named check:

- `nix build .#checks.x86_64-linux.seat-unit -L --no-link --rebuild` → `seat-unit-tests> 51 passed in 0.09s`, exit 0
- `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` → `unit-tests> ok 634 …`, exit 0
- `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` → `lint> Found 0 warnings and 0 errors.`, exit 0
- `nix build .#checks.x86_64-linux.seat-vm -L --no-link --rebuild` → exit 0; step 12 in the log:
  `machine: (finished: must succeed: su - dalhaka -c 'seat-submit drive --workspace /tmp/ws --dsh-home /tmp/drive-home --model deepseek/deepseek-v4-flash --effort off --port 43202', in 0.16 seconds)`,
  `machine # [ 34.026866] seat-run[1394]: http://10.100.4.2:43202`,
  `machine: (finished: waiting for success: curl -s --max-time 5 -o /dev/null http://10.100.4.2:43202/, in 1.29 seconds)`,
  `machine: (finished: must succeed: grep -q 'model: deepseek/deepseek-v4-flash' /tmp/drive-home/settings.yaml, in 0.02 seconds)`,
  `machine: (finished: must fail: grep -q 'some/other' /tmp/drive-home/settings.yaml, in 0.02 seconds)`
- `nix develop -c ruff check pkgs/seat tests/seat` → `All checks passed!`;
  `ruff format --check pkgs/seat tests/seat` → `6 files already formatted`
- `nix develop -c shellcheck tools/factory/seat/seat-drive.sh` → clean
- `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then
  `git diff --exit-code docs/MAP.md` → exit 0 (the committed count line reproduces byte for byte)
- `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → silent, exit 0
- `nix develop -c githooks/pre-commit` → exit 1 with
  `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` — the hook derives
  the queue from the LIVE `~/factory/runs`, which now records SD7b as run, so it drops `SD7b`
  from the queued list; the gated `lint` check, which sees only the tree, reproduces the
  committed block exactly and is green. Environment state, not a defect of this branch (the
  same note was made for SD7). Reverted; no other file was touched by the hook.

No red check.

## Touches and commit

Eight files. Seven are the section's `touches`: `pkgs/seat/seat-submit.py`,
`pkgs/seat/seat-run.py`, `tests/seat/test_seat_submit.py`, `tests/seat/test_seat_run.py`,
`tests/integration/seat-vm.nix`, `tools/factory/seat/seat-drive.sh`,
`tests/unit/88-seat-drive.bats`. The eighth is `docs/MAP.md` — the count line alone
(`- tests/unit — 23 files` → `24 files`), mandatory for the new bats file and exempt by rule;
regeneration reproduces it. Nothing else: no `docs/OPERATIONS.md` hunk this round, the plan
file untouched, no board or "landed" commit.

Commit: exactly one (`git rev-list --count 28db2d6..HEAD` → `1`), `5a256f3`. Subject
byte-identical to the section's `**commit subject:**` (277 bytes each, compared
programmatically → `identical: True`). Trailers after a blank line in the WORKSPACE RULES
order: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory
run sd7f)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

The driver's record (`/home/dalhaka/factory/runs/sd7f/SD7b.result`) agrees:
`FACTORY-RESULT status=done`, `FACTORY-CHECKS seat-unit=pass seat-vm=pass unit=pass lint=pass`,
`FACTORY-COMMITS 1`, `checks_verified: seat-unit=pass seat-vm=pass unit=pass lint=pass`,
`checks_verified_src: seat-unit=run seat-vm=run unit=run lint=run`, `touches_extra: 0`,
`head: 5a256f3be7185d25a5c65902e5e8d9e55d7d328e`, `base: 28db2d61…`, `error_class: none`.
Confirmed against the tree.

## Findings

No MAJOR.

**MINOR-1 — `pkgs/seat/seat-submit.py:205`: the port *range* arm of interface 1 has no test.**
Mutant O1 turns

```
        if args.port is None or not (1024 <= args.port <= 65535):
```

into `if args.port is None:` and the whole seat suite stays green
(`nix develop -c pytest tests/seat -q` → `51 passed in 0.07s`): `test_drive_requires_port`
covers only the missing port, and both the VM (43202/43203) and `88-seat-drive.bats`'s
`--port 80` case exercise other code — the bats case hits `seat-drive.sh:66-73`, the script's
own range check, not `seat-submit`'s. The clause "an int 1024–65535, else exit 2" is SD7's
interface 1, inherited unchanged into SD7b (which named no mutant for it), so this is not
gating; one more `_submit(... "--port", "80")` case asserting `rc == 2` closes it.

**MINOR-2 — the commit body does not paste a FACTORY-RESULT block**, which item 6 lists among
the body's contents. The block exists in the grammar where it is read
(`/home/dalhaka/factory/runs/sd7f/SD7b.result:1` `FACTORY-RESULT status=done`), and the
Global Constraints forbid copying the FACTORY-RESULT template into project files, so the
plan text is ambiguous here rather than the seat wrong. Recorded, not owed.

**MINOR-3 — `tools/factory/seat/seat-drive.sh:15-18`: the two seams are named in the header
comment at `:15-18`, not at the section's `:7-13`.** The requirement ("both named in the
header comment") is met — the header comment block runs `:2-18`; only the cited line numbers
moved. No action.

## Verdict

**APPROVED.** Both MAJORs of the SD7 gate are closed by tests that measurably fail: the
isolation assertion is now a status the test reads (`88-seat-drive.bats:115-116`,
`grep -c '^ *!'` → 0) and kills both the section's mutant A and the prior reviewer's own leak
probe B inside its own file; the `url.txt` wait has two seams
(`seat-drive.sh:137-138`) and two cases that kill C, D and two further seam mutants of my own.
The three MINORs are closed too (E, F, G all dead — F in a real `seat-vm` build). Twelve named
mutants, twelve dead; five outside the named set, four dead, the survivor an inherited,
non-gating gap in the port-range arm. `seat-unit` 51, `unit` 634, `lint` and `seat-vm` green
under `--rebuild`; one commit with a byte-identical subject and both trailers; `touches`
clean apart from the mandatory `docs/MAP.md` count line.
