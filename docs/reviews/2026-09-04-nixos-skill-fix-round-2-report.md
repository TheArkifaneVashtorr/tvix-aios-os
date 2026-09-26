# Skill fix round 2 — outcome

Date 2026-09-04. Base: `/home/dalhaka/flakes/nixos-skill` master `a525b1a` (untouched throughout;
all work in worktrees under `.../scratchpad/skill-wt2/<key>`).

## Per task

| Key | Branch | Fix commit(s) | Verdict | Checks named |
|-----|--------|---------------|---------|--------------|
| S3 | `task/S3-r2` | `0a6bfad` (on rebased `05df67b`, `3582c4c`) | approve | doctests-self, doctests-bash-self, doctests, citations, budget, lint |
| S8 | `task/S8-r2` | `9ad7bcf` (on rebased `399da94`, `494598e`) | approve | runner-unit, report-unit, router, lint |
| S12 | `task/S12-r2` | `13b64a8` | approve | lint, budget, doctests, citations, pin-renames, pin-renames-self |
| S10 | `task/S10` | `cc91231`, `4cbd664` | approve | gotchas, citations, doctests, budget, lint |
| S13 | `task/S13` | `754695e`, `26bf215` | approve | auto-propose-spec (new), lint, + full suite |
| S14 | `task/S14` | `6597ed5`, `c90a528` | approve | lint |

All six approved; six merges landed on `integ/skill-fr2`. Nothing was dropped.

## Notable findings (all reviews were mutation-backed)

- **S3** — the round-2 `--offline` sentence was still false; the reviewer re-measured it himself on a
  loopback server (`builtins.fetchurl` **does** fetch under `--offline` at nix 2.28.5) and the claim is
  now narrowed to substitution + re-resolution. Residual minors: the sandbox/non-FOD half is stated
  unconditionally though it holds only while `sandbox = true`; and — third round running — reverse-applying
  the whole prose fix leaves all six checks green. Prose corrections in `refresh.md` /
  `docs/runbooks/nixos-skill.md` are gated by nothing. Candidate: a `gotchas`-style refusal grep over the
  two strings that were wrong twice.
- **S8** — the blocker (grader-wiring helper missing from `export -f`, so the gate silently no-oped under
  the xargs matrix) is closed, with a paired positive/negative test that goes red when the export is removed.
  Residual: the wiring gate is a `grep -F` over the agent-writable `flake.nix`, so a token in a **comment**
  still passes — measured live, `grade_pass=true` on a substituted grader. Debt, disclosed, not regressed.
  Also: `runner-unit`'s live-nix regression proofs are **skipped in CI**; they hold only under
  `nix develop -c bash tests/test_runner.sh` (green 2026-09-04).
- **S12** — the vacuous missing-snapshot assertion is repointed at the retitle fixture and is now red for
  its own reason (MUT6 caught). Residual: a release-notes-only fallback still survives (MUT8 green).
  Open for the operator: `b08fc34`'s subject names a non-check phrase (`host build pin-renames`) and the
  branch mixes Sonnet/Fable trailers — the implementer escalated rather than rewriting history.
- **S10** — the read-only-cache entry now names the real SQLite caches and the correct user registry
  (`~/.config/nix/registry.json`, re-measured on the host). Residual: the awk section anchor is unguarded
  (renaming the heading silently disarms the refusal), and the `verified:` stamp is pinned to one literal
  date, so the next legitimate re-verification goes red with a misleading message.
- **S13** — auto-propose spec, plus a new `auto-propose-spec` content check with six grep pairs, each shown
  red first. Key correction: `nix flake update nixpkgs` alone is a **no-op** at this pin; the rev literal
  must be edited first. Residual minors: `refresh.md` §1 itself still names the command before the edits
  (follow-on task), and the "three spots" count mislocates the literal (it is `flake.nix:148`, not
  `checks/lock-guard.nix`) and omits the `gotchas.md` stamp.
- **S14** — the fix-round-1 outcome record: 16 review rounds, 71 findings (2 blockers, 12 majors,
  57 minors); 26 minors carried as disclosed debt, 2 declined on record. Residual: S3's round-1 commits are
  still labelled by their rebase hashes, the tally caveat is worded backwards, and the commit body's
  "no check reads these files" is false — `lint` reads all of `docs/` (measured).

## Integration head

`integ/skill-fr2` = `962849d` ("merge: task/S14 into integ/skill-fr2"). Measured here, this round:
`nix flake check -L` **exit 0, 18/18 green** — auto-propose-spec, budget, budget-unit, citations,
citations-unit, doctests, doctests-bash-self, doctests-self, gotchas, lint, lock-guard, pin-renames,
pin-renames-self, report-unit, router, router-unit, runner-unit, upstream-manifest. `master` is an ancestor
of the head, so the merge is a fast-forward. Not measured: any VM-level check (this repo has none).

Fast-forward when you are ready:

```
git -C /home/dalhaka/flakes/nixos-skill merge --ff-only integ/skill-fr2
```
