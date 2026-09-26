# nixos-skill fix round 1 — outcome

## WIP assessment (measured, not judged from the diff)

`wip/skill-fix-round-1-partial` (dd2e5e8, forked at e85beb2) was **red**: `nix flake
check -L` exited 1 with `error: stack overflow (possible infinite recursion)` at
`checks.x86_64-linux.doctests-self`. Root cause isolated: the new `!throws <good
fixture>` pairing forced `builtins.deepSeq` over a derivation; a stack overflow is
not catchable by `tryEval`, so the whole attribute aborted. Every other check built
green individually at dd2e5e8 (lint, lock-guard, budget, router, budget-unit,
router-unit, report-unit, runner-unit, doctests, citations, citations-unit);
`gotchas` simply did not exist on that fork. `git cherry-pick --no-commit dd2e5e8`
onto master e76d2ef applied cleanly (one auto-merge in flake.nix). Substance:
plan Task 1 complete (all of skill-T1, most of skill-T2); half-done — doctests-self
aborting, the orphan `bad-bash-flag.md` fixture, a spacing-sensitive fetcher regex,
and the unrecorded `--offline` requirement. No concern mixing; landed as one task.

## Schedule

Wave 1: S2. Wave 2 (parallel, on S2): S3, S4, S5, S6, S7, S8. Wave 3: S9 (needs
S3+S8), S11 (needs S3). Wave 4: S12 (needs S11). S10, S13, S14 were never
dispatched. S7's declared dependency on S10 was not honoured — it ran in wave 2.

## Per task

| Task | Status | Commit | Verdict |
|---|---|---|---|
| S2 land WIP green | merged | 953fbef | approve (3 minors) |
| S3 T2 leftovers | **rework, not merged** | 4c84d55 | rework (1 major, 3 minors) |
| S4 language/flakes/module/cli | merged | 101ddcf | approve (4 minors) |
| S5 systemd/activation/security | merged | 9eceaa9 | approve (3 minors) |
| S6 packaging/cuda/vm/debugging | merged | b54cd9f | approve (6 minors) |
| S7 T6 + falsifiability item | merged | a3eea80 | approve (5 minors) |
| S8 eval graders | **rework, not merged** | 85b3c30 | rework (1 blocker, 4 minors) |
| S9 report.py exec bit | merged | de18acb | approve (2 minors) |
| S11 upstream manifest | merged | bc8bf49 | approve (4 minors) |
| S12 pin renames | **rework, not merged** | 164a5f4 | rework (1 major, 2 minors) |
| S10, S13, S14 | not started | — | — |

## Notable findings and mutations

- **S2**: red reproduced (stack overflow), fixed by `builtins.seq (runDoctests
  [file]).drvPath true`. Reviewer's mutations confirmed the T1 major was real: with a
  broken budget.sh, master's `test_budget.sh` exits 0 while the new one exits 1.
- **S3** (open): the `--offline` prose claimed the flag blocks eval-time
  `builtins.fetchurl`. Measured false against a loopback HTTP server at the pin — it
  still downloads. Also the tab branch of the loosened `hash[ \t]*=` regex is not
  falsifiable (deleting `[ \t]` leaves every check green).
- **S4/S5/S6**: prose facts are outside every gate — a reverse-apply of S6 left all
  five checks green. Re-measured at the pin instead: `path:` vs `git+file:` filtering
  inverted, `do_user_switch` does no unit diffing, `vendorHash = null` semantics,
  nix-ld default library list. A stray unmatched backtick at python-and-cuda.md:91
  silently disables `citations` for the rest of that file (still open).
- **S7**: the corrected renamed-option message re-derived independently —
  `evaluation warning: The option 'hardware.opengl.enable' … has been renamed …`,
  no "Obsolete option" trace on a definition. One SKILL.md guard mutation still survives.
- **S8** (open, blocker): `task_grader_wiring` is missing from run-evals.sh's
  `export -f` list, so the new gate is a no-op in the real xargs-parallel run — the
  substitution cheat still scores a false pass. Reproduced live.
- **S12** (open, major): the missing-snapshot assertion passes for the wrong reason;
  restoring the `[ ]` fallback leaves `pin-renames-self` green.
- **S11**: both red modes shown (missing path named; glob matched zero files). One
  mutation survived — commenting out a manifest entry keeps every check green.

## Integration head and checks

`integ/skill-fr1` = **a525b1a** (S2, S4, S5, S6, S7, S9, S11). I re-ran every check
the flake exposes at that head: budget, budget-unit, citations, citations-unit,
doctests, doctests-self, gotchas, lint, lock-guard, report-unit, router, router-unit,
runner-unit, upstream-manifest — **all 14 PASS**. Per-wave check runs were done by the
implementers and reviewers in their own worktrees; I did not re-run them wave by wave
(not measured). `nix flake check -L` in full was not run at the head (not measured).

## What did not land, and why

- **S3, S8, S12**: reviewer verdict `rework`, held out of the integration. S8's is a
  blocker (the gate never executes); S3's and S12's are majors.
- **S10** (read-only-cache gotcha names the wrong artefact): never dispatched.
  Confirmed still present — gotchas.md:170 still says "eval cache and flake registries
  in a SQLite database".
- **S13** (auto-propose spec) and **S14** (outcome record + board): never dispatched;
  `docs/superpowers/specs/2026-09-04-nixos-skill-auto-propose.md` and
  `docs/reviews/2026-09-04-fix-round-1-outcome.md` do not exist.
- Commit trailers on several branches name "Claude Fable 5.1" against the model policy;
  flagged repeatedly by reviewers, unresolved.

## Fast-forward

The last integration (S11 into a525b1a) is ok — all 14 checks green, master is an
ancestor. To land it:

```
git -C /home/dalhaka/flakes/nixos-skill merge --ff-only integ/skill-fr1
```

Master is untouched at e76d2ef and clean; `wip/skill-fix-round-1-partial` is untouched.
