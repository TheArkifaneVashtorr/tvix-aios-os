---
plan_defect: implementer
mutants_total: 2
mutants_killed: 2
mutants_outside_named: 0
reviewer: sonnet
majors: 3
minors: 4
---
# Opus gate — seat run tel3, task T3M — REJECTED

## Summary

T3M runs T3's `migrate_reviews.py` over `docs/reviews` and commits the output.
The migration itself is correct and idempotent (verified independently, not
just via the claimed summary lines), the diff is insertion-only and confined
to `docs/reviews`, the commit subject is byte-identical to the section's, and
the plan file and board are untouched — one commit, as required. But the
commit's two trailers are glued directly onto the last line of the body with
no blank line before them, so `git interpret-trailers --parse` recognizes
**zero** trailers in this commit; the section's own commit-convention contract
(the two trailers, Generated-By and Co-Authored-By) is not met as landed.
That is the one MAJOR and the reason for REJECTED.

## Contract items

Section T3M (docs/superpowers/plans/2026-09-06-telemetry-store-1.md:614-635),
taken literally:

1. **Files: modify every `docs/reviews/*opus-review*.md` T3's script changes.**
   MET. `git diff 5f22a92..HEAD --name-only | grep -v '^docs/reviews/'` →
   empty (no file outside `docs/reviews` touched). 145 files changed, all
   under `docs/reviews`.
2. **Interfaces: none new; no file outside `docs/reviews/` changes; no plan
   file touched.** MET. `git diff 5f22a92..HEAD --stat -- docs/superpowers/plans/2026-09-06-telemetry-store-1.md`
   → empty.
3. **Step 1 (the red).** MET, reproduced independently (see Red before green):
   on base 5f22a92, `migrate_reviews.py . --check` → `checked: 172; would
   change: 145`, exit 1 (the section's own 164/137 counts are stale — the
   task's brief correctly told me to trust the seat's own numbers, which
   check out arithmetically: 145 changed + 27 legacy = 172 total).
4. **Step 2 (run the migration).** MET. Re-run for real on a scratch copy of
   base: `migrated: blocks added 119, keys added 78, unchanged 0, skipped
   legacy 27` — exactly the seat's claimed numbers (119 blocks, 78 keys, 27
   legacy), confirmed by an independent `--numstat` cross-check: 119 files
   with 5/6/7 inserted lines (a prepended block) and 26 files with exactly 3
   inserted lines each (26×3 = 78, a keys-only splice).
5. **Step 3 (prove it), on HEAD:**
   - `migrate_reviews.py . --check; echo exit=$?` → `checked: 172; would
     change: 0`, `exit=0`. MET.
   - `tasks.py --root . check` → silent, exit 0. MET, with a caveat: see
     Checks — this command resolves the `nixos-agent-env` repo path via
     `docs/ledger/repos.toml`'s `path = "~/nixos-agent-env"`
     (`os.path.expanduser`d in `load_repos`, tasks.py:194), which is the real
     `/home/dalhaka/nixos-agent-env`, **not** `--root`'s value. Run from any
     clone, this command always inspects the live tree, never the clone. It
     is not something T3M's diff controls and I do not fault the seat for it,
     but it means this particular assertion is not actually exercising the
     branch under review.
   - `git diff --stat | tail -1` → `145 files changed, 718 insertions(+)`,
     only insertions. MET (the section said 137; superseded, per the task
     brief, by the seat's actual corpus size).
   - `git diff -- docs/reviews | grep '^-' | grep -v '^---' | wc -l` → `0`.
     MET.
   - `grep -L '^reviewer:' docs/reviews/*opus-review*.md | wc -l` → `27`. MET.
6. **Step 4 (commit): `git add docs/reviews`, the byte-exact subject.** Subject
   MET (byte-identical, diffed against the section's string). `git add -A`
   was not used — the board is absent from the diff. But see Findings:
   MAJOR-1 on the trailers.
7. **Tests: the two named mutants.** Both killed — see Mutants.
8. **touches: docs/reviews.** MET (confirmed above).
9. **acceptance: lint.** MET — see Checks.

## Red before green

On base `5f22a92d6875405f7469f046bfe7be99db26f602` (worktree copy), before
any migration:
```
$ nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check; echo exit=$?
...
checked: 172; would change: 145
exit=1
```
Then, on HEAD (the seat's branch):
```
$ nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check; echo exit=$?
checked: 172; would change: 0
exit=0
```
Red confirmed, then green confirmed, independently reproduced (not just
trusted from the commit body, which pastes no red/green — see Findings
MINOR-1).

## Mutants

Both mutants the section names, run in scratch copies (never in
`/home/dalhaka/factory` or the real `/home/dalhaka/nixos-agent-env`):

1. **Hand-edit `majors: 1` → `majors: one`** in
   `docs/reviews/2026-09-05-opus-review-bk3-B1b.md` (via the Edit tool, in a
   scratch copy of HEAD). Running the literal instructed command
   (`nix develop -c python3 pkgs/evidence/tasks.py --root . check`) does
   **not** go red — because, as noted above, this command always resolves
   `nixos-agent-env`'s path through `repos.toml`'s `~/nixos-agent-env`
   regardless of `--root`, so it inspected the real live repo, not my mutant
   copy. To test the actual code path, I pointed `--repos` at a throwaway
   `repos.toml` naming the mutant scratch directory as `nixos-agent-env`'s
   path:
   ```
   $ nix develop -c python3 pkgs/evidence/tasks.py --root . --repos <scratch>/repos-mutant.toml check
   tasks: review 2026-09-05-opus-review-bk3-B1b.md: majors must be an integer or null
   exit=1
   ```
   Killed. Reverted (the mutant copy was discarded, nothing under
   `/home/dalhaka/nixos-agent-env` or `/home/dalhaka/factory` was touched).
2. **Run the migration a second time** on HEAD's own tree:
   ```
   $ nix develop -c python3 pkgs/evidence/migrate_reviews.py .
   migrated: blocks added 0, keys added 0, unchanged 145, skipped legacy 27
   ```
   `git status --porcelain` → empty (no diff produced), and `--check` above
   already showed `exit=0`. Killed.

mutants_total: 2, mutants_killed: 2, mutants_outside_named: 0 (I did not try
mutants beyond the two the section names).

## Checks

- `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` → exit 0 (the
  eslint/prettier warnings in the transcript are the lint check's own bad-code
  test fixtures under `tests/lint/fixtures/`, pre-existing and unrelated to
  this diff).
- `nix develop -c githooks/pre-commit` → real exit 1, but only because it
  regenerated `docs/OPERATIONS.md`'s queue block (the derived `<!--
  tasks:begin/end -->` block, stale simply because real time has passed and
  other tasks have landed since this branch's base — the Global Constraints
  section explicitly exempts this block: "the board's queue block (regenerated
  by the pre-commit hook)" is never a deviation). Not a defect of this task's
  diff; `docs/OPERATIONS.md` does not appear in `git diff 5f22a92..HEAD`.
- Python change: none — T3M's `touches` is `docs/reviews` only, no `.py` file
  in the diff, so `ruff check`/`ruff format --check` do not apply.
- `python3 pkgs/evidence/repomap.py --root . write` then
  `git diff --exit-code docs/MAP.md` → exit 0 (no drift).
- `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → silent,
  exit 0 (see the repos.toml caveat under Contract item 5).

## Touches and commit

Every one of the 145 changed files is under `docs/reviews`; nothing else in
the diff (`git diff --name-only | grep -v '^docs/reviews/'` → empty). One
commit only (`git log 5f22a92..HEAD --oneline` → 1 line). Subject
byte-identical to the section's string (diffed byte-for-byte). No board
commit, plan file untouched. Body states the why but pastes no red/green
terminal output (unlike sibling code tasks in this same plan, e.g. T3b's
044f284 commit) — the T3M section's own title does not literally demand
"the reds and greens in the body" the way T3b's does, so I record this as
MINOR-1 rather than a MAJOR. The trailers are present as text but not as
proper git trailers — see MAJOR-1.

## Findings

**MAJOR-1** — `docs/reviews/2026-09-07-opus-review-tel3-T3M-commit` (HEAD
commit `6e57a0013e2d87cdc410fa21ea1a3efafb23f551`, message body, last two
lines): the two required trailers (`Generated-By`, `Co-Authored-By`) are
appended directly after the body's final sentence with no blank line
separating them, so they are not git trailers at all.
Evidence:
```
$ git log -1 --format='%B' HEAD | git interpret-trailers --parse
(no output)
$ git log -1 --format='%B' HEAD | awk '/^Generated-By:/{print ""} {print}' | git interpret-trailers --parse
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run tel3)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```
`git interpret-trailers` recognizes zero trailers on the commit exactly as it
was landed, and recognizes both as soon as a blank line is inserted before
them — proving the missing blank line, not the key names or values, is the
defect. This is exactly what the required commit convention names ("the two
trailers after a blank line") and it is exactly the pattern every sibling
landing commit in this same plan follows (e.g. `044f284`'s body ends its
green-output block, then a blank line, then `Generated-By:`/`Co-Authored-By:`).
`plan_defect: implementer` — the section and the house convention both state
the trailer shape; the seat produced a body that runs its prose straight into
the trailer lines.

**MINOR-1** — commit body (HEAD `6e57a00`): no red or green terminal output is
pasted into the body, only a narrative description of the migration's effect.
The section's own Steps ask the seat to "paste" the `--check` red line
(Step 1) and the real migration line (Step 2), and every comparable task in
this plan (T1b, T1Wb, T3b, T2b) pastes its reds and greens into the commit
body; T3M's own section title, unlike T3b's, does not explicitly demand "the
reds and greens in the body," so I record this as a MINOR rather than a
MAJOR — worth closing in a fix round for consistency with the rest of the
plan's commits.

**MINOR-2** — `docs/ledger/repos.toml:6` / `pkgs/evidence/tasks.py:194`
(pre-existing, not introduced by this task): `tasks.py --root . check`,
run from any clone including this gate's, always resolves the
`nixos-agent-env` repo through `repos.toml`'s `path = "~/nixos-agent-env"`
(`os.path.expanduser`d), i.e. the real live repo, never the clone passed via
`--root`. Every gate review that cites this command as an acceptance check
against "the branch" is, as literally run, actually checking the operator's
live tree. It happens to be harmless for T3M specifically (T3M's own contract
doesn't depend on `tasks.py check` validating anything about its own diff —
the review lint's real target is the `docs/reviews` front-matter shape, which
I verified directly), but it is worth the orchestrator's attention as a
gap in how every gate in this plan is instructed to verify this line.

## Verdict

REJECTED — one MAJOR (the commit's two trailers are not recognized as git
trailers because of a missing blank line before them; `git interpret-trailers`
proves it empirically). Every substantive claim about the migration itself
(the numbers, the idempotency, the touches, the diff shape, the subject, the
block-shape rule on the eight 2026-09-07 review files touched — plan_defect
first, H1 immediately after the closing fence, all eight checked) held up
under independent re-derivation, not just re-reading the seat's own summary
lines. A fix round need only re-commit with a blank line before the trailers
(and, to close MINOR-1 for consistency, paste the Step 1/Step 3 command
output into the body) — no code or migration-output change is required.
