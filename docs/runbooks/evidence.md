# The evidence store and the claims file

Two different things share the word ledger. The **claims file**
(`docs/ledger/claims.toml`) is the list of what we believe about this system
and whether each belief is proven. The **ledger** (`/var/lib/evidence/ledger/`)
is the token and cost record. This page is about the store and the claims file.

## The store

The evidence store is one directory of append-only JSONL files, one per
stream. It lives at `/var/lib/evidence` and is backed up nightly with the
rest of the host. Every row in it records an *observation* — a fact that a
named check actually happened at some revision with some result — never a
belief or a plan. Nothing is ever edited in place: a correction is a new row.

Four writers append to it:

- the nightly flake check (`helm-flake-check`) records the whole stack green
  or red at a revision;
- the seat integrator records a check after each factory integration;
- the factory's verify step records a check after it runs the flake check;
- Helm's collector records a `helm-status` row whenever a tile changes
  verdict (or an hour passes).

Read it with one command:

```
evidence bundle --markdown
```

That prints the live generation and revision, `HEAD`, which checks cover
each, the sibling heads, what Helm has been showing since when, and the open
gaps. For one check at one revision there is a narrower command:

```
evidence latest-check --name flake-check --rev $(git rev-parse HEAD)
```

and the raw stream is just JSONL, so `tail` works too:

```
tail -n 3 /var/lib/evidence/checks.jsonl
```

A plan file that has not landed yet can be judged before it is committed:
`python3 pkgs/evidence/tasks.py --root . check --draft FILE` parses `FILE`
wherever it lives outside the plans directory, attaches its tasks to this
tree's graph, and holds it to the same rules as a landed plan — its
`acceptance` names must each be `lint` or a name in `docs/MAP.md`'s Checks
section, its `touches` must be explicit paths, its commit subjects byte-exact
and matching their acceptance, and the file must carry the four house sections
(`## Global Constraints`, `## Assumptions`, `## Waves`, `## Operator`). On
success it prints the draft's `waves:` and `conflicts:` rows; the exit code is
`0` when clean, `1` when any rule fails, and `2` for a usage error (the file is
unreadable, already under the plans directory, or no configured repo matches
`--root`).

## The claims file

A **verified** claim means a named check was green at a revision and the row
records how it was checked (`check:<name>@<rev>`); an operator-judged drill
keeps class `operator` (`operator:<date>`). Prose is never evidence.

**Open a gap** by adding a `[[claim]]` row with `status = "gap"`, an `owner`,
a `review_by` date and a `closes_by` that says what would close it. The hook
refuses two things: a gap past its `review_by` date (extend it with a reason
or close it), and evidence that is prose instead of `check:<name>@<rev>` or
`operator:<date>`.

**Close a gap** by flipping the row to `status = "verified"` and giving it
`evidence` of one of those two shapes. Validate the file with:

```
nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"
```

## The plan-defect ledger

`docs/ledger/plan-defects.toml` records every Opus-gate rejection that names a
plan defect, one `[[rejection]]` row per review: the repo-relative `review`
path (which must exist), its `run` and `key`, the filing `date` (the review
basename's prefix) and a `plan_defect` class drawn from the seven-value enum
`none | vacuous | missing-case | underspecified | wrong-fact | implementer |
process`. A row with two classes names the primary first and the second as
`plan_defect_secondary`. `[meta] front_matter_from` is the date from which a
gate review must carry the front-matter block; earlier files stay byte-unchanged
and are classified by these rows. `tasks.py check` reads the ledger, and the
brief's `Record (7 d)` line counts its rows: `**Record (7 d):** N rej, M plan
(vac a, miss b, under c, fact d)` — N the seven-day rejection total (blocks and
ledger rows; a block on an APPROVED review never counts), M the plan-caused
subset (vacuous/missing-case/underspecified/wrong-fact) and one `vac`/`miss`/
`under`/`fact` tally each. The line is display only: P10 reads the ledger, never
this line.

From `front_matter_from` on, every gate review carries a block — line 1 `---`,
then `key: value` lines, then `---`, with the `# Opus gate — seat run …` header
immediately on the next line (a blank line or prose between the closing `---`
and the header is a shape error). This task's check reads `plan_defect`, the
optional `plan_defect_secondary`, and the optional `mutants_total` /
`mutants_killed` / `mutants_outside_named`, each an ASCII-digits-only
non-negative integer — the rule is `^[0-9]+$`, so a sign, an underscore or a
non-ASCII digit is refused (other keys are ignored). The graph check enforces
the block: a review dated on or after `front_matter_from` must carry one, the
header must follow the block, `plan_defect` must be present and in the enum, a
REJECTED review may not name `plan_defect: none`, a mutant count that is not an
integer is refused, and a ledger row whose review file carries an APPROVED
block is a contradiction (`… a ledger row contradicts an APPROVED block`).
Both the check rule and the graph's `read_reviews` glob `*opus-review*.md`, so
a review whose basename lacks "opus" supplies no verdict and is never block-
validated. The evidence-unit sandbox pins the ledger to the frozen seed:
`flake.nix` copies `tests/evidence/fixtures/ledger/plan-defects-seed.toml` over
`docs/ledger/plan-defects.toml` and sets `EVIDENCE_UNIT_SANDBOX=1`, so the
sandbox never sees the live, growing ledger. A test that hard-codes the live
count passes in the devShell (which reads the live ledger) but fails in the
sandbox — the sandbox is the truth, the devShell run is not. This pin replaced
P3Ar2b's text-scanning guard and its helpers (deleted): rather than scan test
code for literal counts over the live ledger, the environment itself can no
longer reach it. P3Ar's `M11`/`M11b`
(live-ledger class flips) are no longer killable since P3Arb, the frozen-fixture
flips standing in for them — so the gate counts P3Ar's remaining kills, not the
original 42.

## The planning report

`evidence report plans` reproduces the design §7 planning metrics from the
tree, joined to first-gate outcomes, each number with its n and no conclusion
under five chains:

```
nix develop -c python3 pkgs/evidence/evidence.py \
  --store /var/lib/evidence report plans --repo .
```

The four core lines are first-try landing rate (chains approved at their own
first gate ÷ chains gated), plan-caused share of rejections (primary
`plan_defect` in the four plan classes ÷ all rejection rows — every ledger row
plus every REJECTED block, no seven-day window and an APPROVED block never
counts), re-plan rate (chains with a `r`-member ÷ chains gated), and rework
rounds per landed task (members beyond the root ÷ landed chains — rounds are
counted over landed chains only). The rubric join, survivors-outside-the-named-set
and the threshold proposal follow once enough plans are judged. The whole report
is a proxy until telemetry T10a/T10b land.

The design §7 "today" column is superseded by this report's numbers: §7 used
landed chains (58) as its denominator for every row, its rounds figure (30)
matches neither the gated (52) nor the landed (46) reading of the same tree, and
it said "ten typed 2026-09-05 plans" where twelve are typed.
On this tree, over `--plan '2026-09-05-*.md'`, the report prints first-try
28/63, re-plan 10/63 and rework rounds 47/59 = 0.80 — not the design's 28/58,
11/58, 30/58.

## The two tile rules that changed

Docs-only commits no longer turn the Helm board red:

- the **flake-check** tile is green when a recorded check covers a revision
  that differs from `HEAD` only in docs;
- the **drift** tile is green when `HEAD` is ahead of live only in docs.