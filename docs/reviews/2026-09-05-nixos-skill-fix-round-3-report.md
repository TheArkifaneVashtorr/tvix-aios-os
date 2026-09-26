# Skill fix round 3 — outcome

Four tasks, four approvals. Every review was mutation-backed; every implementation showed red first.

## Per task

| Task | Branch | Head | Verdict | Checks named |
| --- | --- | --- | --- | --- |
| S15 — gate `refresh.md`'s prose | `task/S15` | `7488897` (impl `39beb12`) | approve | doctests, citations, gotchas, lint, doctests-self |
| S16 — grader-wiring gate | `task/S16` | `647b9c7` (impl `e142de4`) | approve | router, router-unit, runner-unit, lint |
| S17 — live-nix proofs skip loudly | `task/S17` | `a4f0a90` (impl `ef21bcc`) | approve | runner-unit, lint |
| S19 — auto-propose (S13's spec) | `task/S19` | `1e169a9` (impl `6ef2eda`) | approve | auto-propose, pin-renames(-self), upstream-manifest, citations, doctests, budget, lint |

## Notable findings

- **S15** — new `bash verify` doc-test row: blocks are shellchecked, citation-scanned *and executed*, so a
  stale value fails the check. Measured correction to the old prose: inside a Nix sandbox `nix config show`
  and `nix config show --offline` are byte-identical (`!haveInternet()` already forced `useNet=false`), so
  the doc's original "this demonstrates the flag" claim was false; it now asserts the identity and the
  `!settings.X.overridden` guard instead. Residual: three prose-only claims still invert green (the "In short"
  gloss, the `src/nix/main.cc` attribution, `!settings.X.overridden`), the ` --offline` token is not
  load-bearing in either block, `refresh.md` is at exactly 250/250 lines, and the commit subject omits
  `doctests-self` — the one check gating its own headline fix.
- **S16** — the real false pass is closed: `grade_task`'s wiring gate was a raw `grep -F`, so an agent could
  comment out the real `checks.${system} = import ./check.nix …` line, leave a trivially-passing stand-in,
  and still score a pass. Now stripped of Nix block comments, line comments and string bodies before
  matching, exported to the parallel `xargs` path, and reverse-apply proved red. Residual: the `''…''`
  blanking stage has no test (deleting it leaves the suite green), and string blanking runs before the `#`
  strip, so a contrived unbalanced quote in a comment can blank the real wiring line — a false *negative*,
  unreachable on anything shipped (all seeds re-measured MATCH).
- **S17** — the six live-nix regression proofs now skip by name with a count, the self-check is anchored to
  the real guard (not a probe entry point) and the count is cross-checked against source, so drift in either
  direction goes red. `tools/run-live-proofs.sh` is the operator's way to run them for real; measured end to
  end: 68 `ok:` lines, none skipped. Residual: the no-nix fixture derives its PATH from `dirname $(command -v
  bash)`, which on this host resolves to a directory that *does* carry nix — fragile, though unreachable
  via either documented invocation.
- **S19** — S13's spec implemented as §6 artefact (2): an uncommitted Markdown proposal under `proposals/`,
  never touching `skills/nixos/references/` (mutation-proved). Honest disclosure landed for the real gap: a
  `mkRemovedOptionModule` removal produces **no** proposal line — verified directly against the fixture —
  and `citations` is what still catches a reference citing a removed option. Residual: the documentation
  half is gated by nothing (reverting all of `refresh.md` leaves five checks green — the standing S3-era
  debt, now on its fourth round), and "decision item 3" is not resolvable from inside this repo.

## Integration head

`integ/skill-fr3` = `19a443a` ("merge: task/S19 into integ/skill-fr3"); its tree equals `task/S19`'s, and
`master` (`962849d`) is an ancestor, so the merge is a fast-forward. Measured here, this round:
`nix flake check -L` **exit 0, 19/19 green** (round 2's 18 plus the new `auto-propose`), and a re-run
confirmed `nix flake check` exit status 0 directly. Not measured: any VM-level check (this repo has none);
`auto-propose`'s live `nix eval`-backed mode, which no check exercises (disclosed in its docstring).

Nothing failed to land. S18 was not part of this round.

Fast-forward when you are ready:

```
git -C /home/dalhaka/flakes/nixos-skill merge --ff-only integ/skill-fr3
```
