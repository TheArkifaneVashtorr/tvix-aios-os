# Opus gate — seat run ev1, task R7 — APPROVED

Branch head `377466f3f3c8` (`~/factory/ws/ev1/R7`, `task/R7`). Reviewer: Opus, high effort, throwaway clone; checks re-run by ref.

## Summary

APPROVED. R7 lands exactly what the plan specifies and the tests are real.

Spec compliance: one commit, only the two files in `touches`, subject byte-identical to the plan, both mandated trailers in the mandated order, `run-mount-tests.sh` both-modes result recorded in the body. `cmd_teardown` now accepts either mountpoint, unmounts each stacked layer in a loop bounded at 8 with `umount -l` only as a loudly-warned last resort, removes both directories and dies naming whichever path survives; `cmd_mount` installs the `EXIT INT TERM` trap and the old explicit decrypt branch collapses to `(cmd_decrypt ...) || die`. Every Interfaces bullet is present.

Red-before-green: proven. With `pkgs/basket/basket.sh` reverse-applied to HEAD~1 and the tests at HEAD, case 4 dies on `rmdir: failed to remove 'run/demo': Device or resource busy` and case 5 on `[ \"$status\" -eq 0 ]' failed` — the two failure modes the plan predicts verbatim. Case 6 passes on old code, which the plan explicitly declares a regression pin rather than a red-first case; I discharged the plan's own reviewer obligation by deleting the trap (MUT1), which turns case 6 red with the tmpfs still mounted.

Mutation table: 5 mutations, 4 killed. Every load-bearing behaviour has a test that dies when it is broken — the trap (case 6), the unmount loop (case 4), the two-mountpoint entry guard (case 5), and the directory removal (cases 4 and 5 independently). No vacuous test found: I aimed each mutation where a green-by-accident test would hide, and each was caught. The one survivor (MUT5, `mount_done` constant) is unreachable code the plan itself specifies alongside the `trap -` that disarms it — a redundancy, not an untested behaviour, and recorded as minor.

Checks: `unit` green (and its build log proves it ran the new file, with the three new cases skipping per Assumption 8, so it is not a stale cache), `lint` green on a fresh build, `githooks/pre-commit` green, `tests/run-mount-tests.sh` 6/6 under both private and shared propagation. No blockers, no majors. Two minors, both tracing to the plan's own text rather than the implementer: the abort message claims a teardown it does not verify, and the `mount_done` flag is dead on the success path. Neither blocks the merge; the first is worth a follow-up if the orchestrator wants the abort path to fail loudly when the tmpfs is busy.

Throwaway clone deleted; nothing written inside the repo, the workspace, or any ~/factory path.

## Checks

- green — unit (nix build .#checks.x86_64-linux.unit -L --no-link): exit 0; out path /nix/store/wv1jra21kxqbkmg9qcv9qnhi05lr9siq-unit-tests. Build log confirms the derivation ran the NEW test file: 'ok 20 teardown removes every stacked mount layer...# skip', 'ok 21 teardown cleans a staging tmpfs...# skip', 'ok 22 a mount whose decryption fails...# skip' — the three new cases are present and skipped per Assumption 8, so the check is not stale.
- green — lint (nix build .#checks.x86_64-linux.lint -L --no-link): built fresh (i3sviffzyja2xbqnw3qkrx4xzkh3cvj1-lint.drv); 'formatted 72 files (0 changed)', 'All checks passed!', '20 files already formatted'. shellcheck/statix/deadnix/ruff/treefmt clean.
- green — lint gate (nix develop -c githooks/pre-commit): exit 0; ends 'All checks passed!' + 'render.test.mjs: all assertions passed'.
- green — tests/run-mount-tests.sh (both propagation modes): nix develop -c tests/run-mount-tests.sh: 6/6 ok under private propagation and 6/6 ok under shared propagation at HEAD. This is the acceptance line's 'run by the implementer and the reviewer' item; it is recorded in the commit body.

## Red before green

Reverse-applied the implementation only, keeping the tests at HEAD: `git checkout HEAD~1 -- pkgs/basket/basket.sh`, then `nix develop -c unshare --user --map-root-user --mount --propagation shared bats tests/unit/30-mount.bats`. Result matches the plan's Step 2 prediction exactly — two of the three new cases go red and the third is the stated regression pin:

  not ok 4 teardown removes every stacked mount layer and leaves no plaintext readable
  #   `basket teardown demo --runtime-dir run' failed
  # rmdir: failed to remove 'run/demo': Device or resource busy

  not ok 5 teardown cleans a staging tmpfs left behind by an interrupted mount
  #   `[ "$status" -eq 0 ]' failed        (teardown died: not mounted)

  ok 6 a mount whose decryption fails leaves no staging tmpfs and no directories

Case 6 passing on the old code is exactly what the plan declares ("The decrypt-failure case passes today through the explicit branch: it is the regression pin for Step 3's trap, and the reviewer proves it by deleting the `trap` line"). I proved it as instructed — see mutation MUT1 below, which turns case 6 red. Restored with `git checkout HEAD -- pkgs/basket/basket.sh` (working tree verified clean) before every subsequent run.

## Mutation table

| mutation | killed | by |
|---|---|---|
| MUT1 — comment out `trap cleanup_mount EXIT INT TERM` in cmd_mount (pkgs/basket/basket.sh:185). This is the plan's own required reviewer mutation and the proof that the regression-pin case is not vacuous. | yes | test 6 'a mount whose decryption fails leaves no staging tmpfs and no directories' — `[ ! -d run/.basket-tmpfs-demo ]' failed`, plus `rm: cannot remove '.../test/6/run/.basket-tmpfs-demo': Device or resource busy` (the tmpfs is still mounted). Cases 1-5 stayed green, so case 6 is the sole guard on the trap. |
| MUT2 — turn the multi-layer loop into a single pass: `while mountpoint -q "$p"...; do` → `if ...; then` (and matching `done` → `fi`) in `unmount_all` (basket.sh:220,227). Tests only one unmount round per path. | yes | test 4 'teardown removes every stacked mount layer...' — `basket teardown demo --runtime-dir run' failed`, `rmdir: failed to remove 'run/demo': Device or resource busy`. The stacked-bind case genuinely exercises the loop; it is not passing by accident. |
| MUT3 — drop the staging half of the entry guard: `if ! mountpoint -q "$mnt" 2>/dev/null && ! mountpoint -q "$staging" 2>/dev/null` → `if ! mountpoint -q "$mnt" 2>/dev/null` (basket.sh:213), i.e. restore the old 'only $mnt counts' precondition. | yes | test 5 'teardown cleans a staging tmpfs left behind by an interrupted mount' — `[ "$status" -eq 0 ]' failed` (teardown dies again on the interrupted-mount shape). Test 3 ('teardown fails loudly on unknown id') stayed green, so the loosened guard did not silently weaken the loud-failure path. |
| MUT4 — delete the staging directory removal `[[ -d "$staging" ]] && rmdir "$staging"` (basket.sh:232), replaced by `true`. Distinguishes 'unmounted' from 'left no directory behind'. | yes | two tests independently: test 4 line 47 `[ ! -d run/.basket-tmpfs-demo ]' failed` and test 5 line 57 `[ ! -d run/.basket-tmpfs-demo ]' failed`. The 'no trace' assertions are load-bearing, not decoration. |
| MUT5 — constant flip `mount_done=1` → `mount_done=0` on the success path (basket.sh:194). | NO | SURVIVED — all 6 cases green. Not a test defect: `trap - EXIT INT TERM` on the very next line disarms the trap unconditionally, so the `mount_done` guard inside `cleanup_mount` is unreachable on the success path. This is the plan's own belt-and-braces text (both lines are specified verbatim in R7 Step 3), so the implementer is faithful; recorded as a minor finding for the orchestrator, not a defect in this task. |

## Findings

- **minor** `pkgs/basket/basket.sh:178-186` — `cleanup_mount` prints `mount: aborted; staging tmpfs torn down` unconditionally, but every step that could fail is silenced (`umount "$mnt" 2>/dev/null || true`, `umount "$staging" 2>/dev/null || true`, `rmdir ... 2>/dev/null || true`). If the staging tmpfs is busy (an open handle, a stray bind from a concurrent process), the message asserts a teardown that did not happen and plaintext stays mounted at run/.basket-tmpfs-<id>. The code this replaced (`umount "$staging"` bare, under set -e) failed loudly instead. Not an implementer defect: this is the plan's R7 Step 3 text verbatim, and the failure path is outside the three specified cases. **Fix:** Follow-up (orchestrator's call, outside R7's touches): after the umounts, re-check `mountpoint -q` on both paths and print `mount: aborted; $staging is STILL MOUNTED — tear it down by hand` on stderr instead of the success wording. Cheap and testable with a bind-holder in the bats suite.
- **minor** `pkgs/basket/basket.sh:179,194` — The `mount_done` flag is dead on the success path: `mount_done=1` is immediately followed by `trap - EXIT INT TERM`, so `[[ $mount_done -eq 1 ]] && return 0` inside `cleanup_mount` can never be reached by a normal completion. Proven by MUT5, which flips the constant to 0 and leaves all six cases green. Plan-specified redundancy (both lines appear in R7 Step 3), so the implementer transcribed correctly. **Fix:** No change in R7. If the orchestrator wants the flag to earn its place, drop either the flag or the `trap -` line in a later cleanup task, or keep both and note in a comment that the flag is only the guard for a signal arriving between the two statements.

## Deviations

The FACTORY-RESULT declares no deviations, and I found none. Verified independently: (1) `git show --stat 377466f` touches exactly `pkgs/basket/basket.sh` and `tests/unit/30-mount.bats` — the plan's `touches` contract, nothing outside it; single commit, base 6c4d4ba..HEAD. (2) Commit subject is byte-identical to the plan's `commit subject` line: `basket: teardown removes every mount layer and cleans an interrupted mount; mount tears its staging tmpfs down on any failure (test: unit, lint; run-mount-tests both modes)`. (3) The commit body records `run-mount-tests.sh` green in both propagation modes, as the acceptance line requires. (4) Trailers: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run ev1)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. The extra Generated-By trailer is NOT a deviation — `tools/factory/seat/factory-brief:83-90` mandates BOTH trailers in exactly that order, and the seat README (:240) reconciles it with the plan's Global Constraint. The `Co-Authored-By` line is exact. (5) The implementer's transcript claim of a trap mutation proof is corroborated: I reproduced it independently (MUT1). (6) Implementation and tests are the plan's Step 1/Step 3 blocks essentially verbatim (only the plan's own inline comments carried through); no placeholder text, no bypass flags, no `--no-verify`, no secrets, no reads of gated paths. The `2>/dev/null` occurrences are on `mountpoint`/`umount`/`age-keygen` inside the specified code and the existing bats setup idiom, not on a gated command. Implementer workspace `/home/dalhaka/factory/ws/ev1/R7` is clean at 377466f (no stray scratch files committed or left).
