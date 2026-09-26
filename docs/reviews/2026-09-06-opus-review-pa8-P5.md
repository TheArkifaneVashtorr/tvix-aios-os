---
plan_defect: wrong-fact
plan_defect_secondary: underspecified
mutants_total: 27
mutants_killed: 23
mutants_outside_named: 11
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run pa8, task P5 — APPROVED

## Summary

One task commit `7748ee9` on base `1d6d9ab`, eight files (+1,106/−4), subject
byte-identical to the plan's line 234 (compared with `diff` against the
extracted value: `SUBJECT BYTE-IDENTICAL`), both trailers in the WORKSPACE
RULES order, no board commit. Every file is inside `touches` except
`docs/MAP.md`, which the rule admits (`tests/factory` 3 → 5 entries).
`treefmt.toml` is untouched, correctly: `tests/lint/js-lint.sh:31` records
`FORMATTER_ARM=A`, so `plan.js` is swept in place rather than excluded.

The pinned script is what the plan says it is. I re-ran the one extraction
command on the design in the clone — 232 lines,
`a26123e146228433ce253c82cb6187bf599d96a28b847718d2c546b4863f8aae` — then
formatted that extraction with the repo's own `prettier` (arm A) and diffed it
against `.claude/workflows/plan.js`. The difference is fourteen hunks, and
every one of them is inside the four contracted changes. Nothing else moved.
`tools/factory/plan/rubric.md` is byte-identical (`sha256`
`174c54a9…` on both sides) to the concatenation of the design's §5.1 and §5.3
extractions. `judge-prompt.md` carries `judgePrompt`'s deleted second sentence
byte-identical and the three lens strings byte-identical to the *values* of
Appendix D's template literals.

All thirteen assertion groups pass, and all sixteen mutants the plan names die
on the assertion the plan names. The three post-extraction reds reproduce
exactly. `factory-unit`, `evidence-unit` (173 passed — P3Ar's repair, which the
merge brings in) and `lint` are green on the merged head, as are the js gate,
`treefmt --ci`, the MAP diff and `tasks.py check`.

The implementer's honest `FACTORY-CHECKS … evidence-unit=fail` with the note
naming the pre-existing `test_tasks.py` cause is a mark in the seat's favour:
the check is green here only because P3Ar landed on main between the two runs.

The plan defect is the gate's own record, not a rejection cause: §P5's
assertion (12) asserts the rubric's fourteen row names "equal `CRITERIA`", and
the design's two artefacts contradict that on rows 5 and 7 (evidence below).
The seat worked around it with a normalising comparison and said so in a
comment. Secondary: hunk (1)'s script-side change and the revision-path call of
hunk (2) have no assertion at all — both can be reverted with the suite still
green.

## The extraction and the four hunks

The extraction, run in the clone:

```
$ awk '/^## Appendix D/{s=1} /^## Revision/{s=0} s' docs/superpowers/specs/2026-09-05-planning-agent-design.md \
  | awk '/^```js$/{s=1;next} /^```$/{s=0} s' > appD.js
$ wc -l < appD.js
232
$ sha256sum appD.js
a26123e146228433ce253c82cb6187bf599d96a28b847718d2c546b4863f8aae  appD.js
```

`plan.js` is that file prettier-formatted (arm A) plus the hunks below. The
diff of *formatted* Appendix D against `.claude/workflows/plan.js` is exactly
these and nothing more; line numbers are Appendix D's own (every anchor in
Assumption 15 verified: `CRITERIA` 47, `FLOOR_ROWS` 54, `PACKET_SCHEMA` 66,
`DRAFT_SCHEMA` 76, target reader 121, `draftPrompt` 130, `LENSES` 133,
`judgePrompt` 141, `tally` 147, `packetPaths` 161, draft call 178, revise call
201, ship 218, `return` 231).

| # | Appendix D | the change | contract item |
|---|---|---|---|
| 1 | after 54 | `const RECORD_FIELDS = [ … ]`, the fourteen names in the plan's order | (3) |
| 2 | 67 | `PACKET_SCHEMA.required` gains `'headings'` | (2) |
| 3 | after 73 | `PACKET_SCHEMA.properties` gains `headings: { type: ['array','null'], items: { type: 'string' } }` | (2) |
| 4 | 77 | `DRAFT_SCHEMA.required` gains `'headings'` | (2) |
| 5 | after 86 | `DRAFT_SCHEMA.properties` gains `headings: { type: 'array', items: { type: 'string' } }` | (2) |
| 6 | 121 | the target reader's prompt gains the `In replan mode (${REPLAN \|\| 'not set'}) …` sentence, verbatim | (2) |
| 7 | 130 | `draftPrompt`'s last sentence ends `… selfScore, headings (every line of the draft that starts with "### ", verbatim).` | (2) |
| 8 | 143–144 | the rubric phrase becomes `the rubric ${REPO}/tools/factory/plan/rubric.md and the judge instructions ${REPO}/tools/factory/plan/judge-prompt.md`; line 144 deleted | (1) |
| 9 | after 159 | `function refuseDroppedHeadings(prior, d)`, body as contracted | (2) |
| 10 | after 161 | `let priorHeadings = null` beside `packetPaths` | (2) |
| 11 | after 174 | `priorHeadings = (parts.find((p) => p.part === 'target') \|\| {}).headings \|\| null` | (2) |
| 12 | after 180 | `refuseDroppedHeadings(priorHeadings, d)` after the draft, before `log(…)` | (2) |
| 13 | ~202 | the same call in the revise loop, after `if (!d) break` (the plan said "after 203"; see minors) | (2) |
| 14 | 220 | the Ship prompt's item 1 lists `${RECORD_FIELDS.join(', ')}` | (3) |
| — | 133–140, 169, 178, 201, 225 | models and efforts already explicit — asserted, not edited | (4) |

`CRITERIA` (47–53) and `FLOOR_ROWS` (54) are unchanged literals: the only
difference from Appendix D is prettier's one-string-per-line reflow.
`RULES`, the five readers, `LENSES`, `tally`, the judge loop and its one
re-ask, the decision expression, the Ship agent, the concept file, the dry-run
line and the final `return` are Appendix D verbatim.

## The rubric and the judge text

`tools/factory/plan/rubric.md` (46 lines) is the design's §5.1 extraction
concatenated with its §5.3 extraction, byte for byte:

```
$ cat s51.txt s53.txt > rubric-expected.md
$ diff -u rubric-expected.md tools/factory/plan/rubric.md && echo IDENTICAL
IDENTICAL
$ sha256sum rubric-expected.md tools/factory/plan/rubric.md
174c54a9a8dc3245fcb8887ebebf66cda2106366b94554dadd0ba003d1e6c836  rubric-expected.md
174c54a9a8dc3245fcb8887ebebf66cda2106366b94554dadd0ba003d1e6c836  tools/factory/plan/rubric.md
```

`tools/factory/plan/judge-prompt.md` carries, under one heading per lens:

- line 5 — Appendix D's deleted line 144, byte-identical (`diff` clean against
  the extraction).
- lines 9, 13, 17 — the three `lens:` strings of Appendix D 135, 137, 139.
  Lines 9 and 13 are byte-identical to the source. Line 17 differs from the
  *source* in one place only: `printf '[[repo]]\\nname = …'` is written
  `printf '[[repo]]\nname = …'`, which is the template literal's evaluated
  value — the string a judge would actually have received. I read that as
  correct rather than a deviation.

`judgePrompt` in the script (`.claude/workflows/plan.js:251-253`) references
both paths and no longer contains line 144:

```js
Blind judge, ${l.name} lens. Read only: the spec ${REPO}/${A.spec}, the draft ${draft}, the rubric ${REPO}/tools/factory/plan/rubric.md and the judge instructions ${REPO}/tools/factory/plan/judge-prompt.md and the tree. Do not read any other draft, packet, transcript or judgement. ${l.lens}
```

The three lens strings also remain inline in `LENSES` — as contracted
("everything else … `LENSES` … is Appendix D verbatim"), so the markdown is a
reference copy for a judge that reads the file, not the source of the prompt.

## The twelve assertions and their mutants

The plan names **thirteen** assertion groups, not twelve; the test implements
all thirteen. `nix develop -c node tests/factory/plan.test.mjs`:

```
ok - (1) the text parses in the harness shape
ok - (2) meta is a pure literal; every agent() carries model and effort
ok - (3) medians: [3,3,0] per row totals 42 and passes
ok - (4) the six-row floor gates a passing total
ok - (5) judgeOnly skips the readers and the drafter
ok - (6) the mechanical checkEmpty gate and the partial-packet refusal
ok - (7) a silent lens shortens the panel and never dispatches
ok - (8) the replan guard refuses a dropped or renamed heading
ok - (9) args validation refuses the four bad shapes
ok - (10) a never-passing panel stops after exactly two revisions
ok - (11) the ship prompt names the plan, judgement and RECORD_FIELDS
ok - (12) the rubric.md rows equal CRITERIA in order
ok - (13) the script never touches the filesystem and never writes the plan unless it dispatches
plan.test.mjs: all assertions passed
```

Every mutant was applied to the clone, the suite run, and the file restored.

**The sixteen mutants the plan names — all killed, each by its named group.**

| mutant | site | group that went red |
|---|---|---|
| `Date.now()` in `meta.description` | plan.js:23 | (2) |
| drop `effort:` from the ship call | plan.js:419 | (2) |
| mean for median | plan.js:259 | (3) |
| drop `floorOk` from `pass` | plan.js:273 | (4) |
| `if (!A.judgeOnly)` → `if (true)` | plan.js:289 | (5) |
| delete the `checkEmpty` gate | plan.js:307-310 | (6) |
| two-judge quorum (`js.length < 2`) | plan.js:270 | (7) |
| compare lengths, not membership | plan.js:279 | (8) |
| drop the `date/name/scratch/spec` throw | plan.js:59 | (9) |
| drop the `args.out` throw | plan.js:60 | (9) |
| drop the `judgeOnly needs args.draft` throw | plan.js:62 | (9) |
| drop the `replan and judgeOnly are exclusive` throw | plan.js:64 | (9) |
| `>` for `>=` on `ROUNDS` | plan.js:363 | (10) |
| drop `'revision'` from `RECORD_FIELDS` | plan.js:96 | (11) |
| drop `"revision"` from `FIELDS` | judgements.py:48 | (11) |
| rename a rubric row (`TDD discipline` → `TDD rigour`) | rubric.md:14 | (12) |

Sample:

```
### MUTANT: M3  (exit 1)
FAIL - (3) medians: [3,3,0] per row totals 42 and passes
### MUTANT: M6  (exit 1)
FAIL - (6) the mechanical checkEmpty gate and the partial-packet refusal
### MUTANT: M8  (exit 1)
FAIL - (8) the replan guard refuses a dropped or renamed heading
```

**Eleven mutants outside the named set — seven red, four survivors.**

Red: dropping `effort:` from the *draft* call (so the split-based scan in (2)
is not saved by a later occurrence); leaking `Copy the draft verbatim to` into
the non-dispatch Ship branch (red on both (7) and (13)); mapping `l.model`
instead of `l.name` into `dropped` (7); `ROUNDS` default 2 → 3 (10); dropping
`${A.date}-` from the judgement path (11); breaking the syntax
(`let packetPaths = [`) — red, though at module load rather than through (1);
renaming the ship label to `shipx` — red through the fixture guard, which is
the answer to "a label with no fixture answer": the stub throws
`plan.test.mjs: no fixture answer for label "shipx" (key "shipx")` and every
group that runs the script fails.

Survivors, all four of them gaps the *plan* leaves rather than the seat:

1. `tools/factory/plan/rubric.md:17` — rewording row 8 to
   `waves and touches and conflicts` keeps the suite green. Assertion (12)
   lowercases, splits on non-alphanumerics and drops the token `and`.
2. `.claude/workflows/plan.js:376` — deleting the revise-loop's
   `refuseDroppedHeadings(priorHeadings, d)` keeps the suite green. (8) only
   ever exercises the post-draft call; no scenario combines `replan` with a
   revision round.
3. `.claude/workflows/plan.js:252` — deleting
   ` and the judge instructions ${REPO}/tools/factory/plan/judge-prompt.md`
   keeps the suite green.
4. `.claude/workflows/plan.js:252` — reverting the rubric reference to
   `the rubric (§5.1 of the design)` keeps the suite green. Deleting
   `judge-prompt.md` outright also keeps `node tests/factory/plan.test.mjs`
   green (the `factory-unit` derivation would still fail at its `cp`, so the
   file's existence is fenced by the flake, not the test).

**The stub harness.** `agent(prompt, opts)` records `{prompt, opts}` and keys
the fixture through `baseKey` (`tests/factory/plan.test.mjs:88-94`): a `read-*`
label maps to itself, `judge-<lens>-<round>[-retry]` to `judge-<lens>`,
`revise-*` to `revise`, anything else to itself. That honours the contracted
prefixes and is stricter for the readers (five keys rather than one). The
fixture supplies all eleven keys the script emits — `read-mechanical`,
`read-record`, `read-field`, `read-operator`, `read-target`, `draft`, `revise`,
`judge-implementer`, `judge-reviewer`, `judge-whole`, `ship` — so no label
falls through today. `parallel` is `Promise.all(fns.map(f => f()))` rather than
a serial loop; because `agent` pushes before its first `await`, call order is
still deterministic and (7)'s and (10)'s counts hold.

## The JS gate and the flake

```
$ nix develop -c bash tests/lint/js-lint.sh --self-test
js-lint: workflow-script linter arm A
… (the three fixtures fail as designed) …
SELFTEST OK
$ nix develop -c bash tests/lint/js-lint.sh
… All matched files use Prettier code style! (×5, incl. .claude/workflows/plan.js)
JSLINT OK
$ nix develop -c treefmt --ci --config-file treefmt.toml --tree-root .
traversed 517 files / emitted 104 files for processing / formatted 104 files (0 changed)
```

`.oxlintrc.json` declares `agent parallel pipeline phase log workflow budget
args` as readonly globals. They are **not** inert for `no-undef` — they are
simply not in the enabled `correctness` category. Forcing the rule:

```
$ nix develop -c oxlint --deny-warnings -D no-undef .claude/workflows/plan.js
rc=0
```

and the same file linted from outside the repo (no config, so no globals)
produces `'agent' is not defined`, `'log' is not defined`, `'phase' is not
defined`. So the answer to "would plan.js fail no-undef if the rule were
enforced" is no: it uses only `agent`, `parallel`, `phase`, `log`, `budget` and
`args`, all six covered (it never uses `pipeline` or `workflow`).

`flake.nix`'s `checks.factory-unit` diff is **+10/−1**, not the +9/−2 the gate
brief predicted. The single deletion is the old
`mkdir -p tools/factory tests/factory docs/ledger`, replaced by
`mkdir -p tools/factory/plan .claude/workflows tests/factory docs/ledger pkgs/evidence`;
the nine additions are the six files the plan names by name, plus
`pkgs/evidence/evidence.py` (with a comment: `judgements.py` imports it at
module top, so the `--fields` subprocess needs the sibling) and
`node tests/factory/plan.test.mjs` placed after `render.test.mjs`. Built:

```
$ nix build .#checks.x86_64-linux.factory-unit -L --no-link
factory-unit> render.test.mjs: all assertions passed
factory-unit> ok - (1) … ok - (13) …
factory-unit> plan.test.mjs: all assertions passed
```

`RECORD_FIELDS` equals the allowlist: `python3 pkgs/evidence/judgements.py
--fields` prints `plan spec author effort words tasks judges judges_dropped
scores total self_score threshold decision revision`, one per line, and
assertion (11) compares them programmatically (killed from both sides). The
flag does not disturb ingest: `evidence-unit` is 173 passed.

## The Ship phase

It cannot launch. `grep` over the whole script for driver commands returns four
hits and no fifth:

- `plan.js:101` (`RULES`, unchanged) — "NEVER run … any seat launch … Two
  read-only exceptions: factory-dispatch with --dry-run, and factory-brief".
- `plan.js:208` — the field reader *reads* the driver files.
- `plan.js:420` — the only invocation:
  `tools/factory/seat/factory-dispatch ${RUN} ${REPO} docs/superpowers/plans/${A.out} --dry-run.`
  followed by `Never run factory-dispatch without --dry-run.`
- `plan.js:228` — the drafter is told to *write* dry-run lines into the plan.

`factory-wave`, `factory-task` and `factory-integrate` are never invoked
anywhere. The write branch is gated on `decision === 'dispatch' && !A.judgeOnly`
(`plan.js:416-417`); every other decision gets
`2. Do not write under docs/superpowers/plans.` (`plan.js:422`), and assertions
(7) and (13) both hold that line. Item 4 files the concept file
(`docs/concepts/${A.date}-<letter>-<slug>.md`, house format). The judgement
record is written for every decision, with the fourteen `RECORD_FIELDS` names.

## Checks

All in the fresh clone at the merged head `7d7ee71`.

| command | result |
|---|---|
| `node tests/factory/plan.test.mjs` | 13/13 ok |
| `node tests/factory/render.test.mjs` | all assertions passed |
| `nix build .#checks…factory-unit -L --no-link` | green (both suites run) |
| `nix build .#checks…evidence-unit -L --no-link` | `173 passed in 4.56s` |
| `nix build .#checks…lint -L --no-link` | green |
| `js-lint.sh --self-test` then `js-lint.sh` | both green, arm A |
| `treefmt --ci --config-file treefmt.toml --tree-root .` | 104 files, 0 changed |
| `githooks/pre-commit` | exit 1 once — the board's queue block regenerated (see minors); everything else green |
| `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | clean |
| `tasks.py --root . check` | silent, exit 0 |
| `python3 pkgs/evidence/judgements.py --fields` | the 14 names in allowlist order |

`--rebuild` is not usable here: the derivations were never built in this store,
so nix answers `some outputs … are not valid, so checking is not possible`. The
plain builds above are therefore genuine fresh builds, not substitutions.

The merge commit `7d7ee71` (the orchestrator's, not the seat's): the merged
head differs from main by exactly P5's eight files, the MAP line
(`tests/factory — 3 files` → `5 files`, the conflict it resolved) and one more
thing — the board's queue block, rewritten to a third value that neither parent
holds. See minor 12.

## Red before green

The plan's step-1 sequence reproduces exactly. With `plan.js` removed:

```
===== RED 1: no plan.js =====
node:fs:484
    return binding.readFileUtf8(path, stringToFlags(options.flag));
rc=1
```

With the raw (unformatted, un-hunked) Appendix D extraction as `plan.js` and
`tools/factory/plan/` absent — the exact state the plan describes after the
extraction command:

```
ok - (1) the text parses in the harness shape
ok - (2) meta is a pure literal; every agent() carries model and effort
ok - (3) medians: [3,3,0] per row totals 42 and passes
ok - (4) the six-row floor gates a passing total
ok - (5) judgeOnly skips the readers and the drafter
ok - (6) the mechanical checkEmpty gate and the partial-packet refusal
ok - (7) a silent lens shortens the panel and never dispatches
FAIL - (8) the replan guard refuses a dropped or renamed heading
expected a rejection containing "replan drops heading: ### A2 (code, S) — b", but the run resolved
ok - (9) args validation refuses the four bad shapes
ok - (10) a never-passing panel stops after exactly two revisions
FAIL - (11) the ship prompt names the plan, judgement and RECORD_FIELDS
RECORD_FIELDS is not defined in plan.js
FAIL - (12) the rubric.md rows equal CRITERIA in order
ENOENT: no such file or directory, open '…/tools/factory/plan/rubric.md'
ok - (13) the script never touches the filesystem and never writes the plan unless it dispatches
plan.test.mjs: 3 assertion group(s) failed
rc=1
```

Restored: `plan.test.mjs: all assertions passed`, tree clean.

## Findings

**No MAJORs.**

The plan defect, for the record — `plan_defect: wrong-fact`. §P5's assertion
(12) states "the 14 row names of `tools/factory/plan/rubric.md`'s table, in
order, equal `CRITERIA`". Two of the fourteen do not, and cannot, because both
sides are pinned verbatim to the design:

```
ROW 5 DIFFERS: rubric="mutant per assertion; discriminating fixtures"  CRITERIA="mutant per assertion and discriminating fixtures"
ROW 7 DIFFERS: rubric="rules, not enumerations"  CRITERIA="rules not enumerations"
```

A byte-exact assertion would have been unsatisfiable. The seat normalised and
said so in a comment at `tests/factory/plan.test.mjs:425-426`. Secondary,
`underspecified`: the plan names no assertion for hunk (1)'s script-side change
and none for hunk (2)'s revision-path call, which is why survivors 2–4 exist.

**Minors** (none blocking; all for the next round or for the record).

1. `tools/factory/plan/judge-prompt.md:17` — no trailing newline
   (`\ No newline at end of file`).
2. `tools/factory/plan/judge-prompt.md:17` — the whole-lens line is
   half-rendered: `\\n` was unescaped to `\n` (correct, that is the string's
   value) but `${SCRATCH}` and `${REPO}` are left as literal placeholders, so a
   judge reading the file sees `cp -a ${REPO} ${SCRATCH}/tree`.
3. `.claude/workflows/plan.js:376` — the revise-loop call sits *before*
   `draft = d.path` where the plan said "after 203". Behaviourally identical
   (the function throws either way), but see survivor 2: nothing asserts it.
4. `.claude/workflows/plan.js:252` — hunk (1)'s script change is unasserted
   (survivors 3 and 4).
5. `tests/factory/plan.test.mjs:427-432` — the (12) comparison drops case,
   punctuation and the word `and`, so a connective-only rename survives
   (survivor 1).
6. `tests/factory/plan.test.mjs:218-228` — assertion (1) can never be the sole
   red: `makeRunner(body)` at line 70 throws at module load first, so a
   syntax fault surfaces as a stack trace instead of `FAIL - (1)`.
7. `pkgs/evidence/judgements.py:332` — `prog="ingest"` was renamed to
   `prog="judgements"`. Outside the contracted "one flag"; nothing asserts the
   prog, so harmless, but it changes every argparse error prefix.
8. `pkgs/evidence/judgements.py:341` — `add_subparsers(dest="command")` lost
   `required=True` (necessary for `--fields`), and the no-argument error is now
   the hand-written `parser.error("a command is required (judgements), or
   --fields")`. That new arm has no test.
9. `.claude/workflows/plan.js:418` — hunk (3) replaced the fourteen literal
   names *and* their two parentheticals, so the Ship agent is no longer told
   that `words` is `wc -w` of the draft and `tasks` the count of typed
   headings; it must infer both. Related, inherited from Appendix D and
   preserved by the hunk: the record JSON handed to that agent carries
   `selfScore` where `RECORD_FIELDS` names `self_score`, and `words`/`tasks`
   are in `RECORD_FIELDS` but not in the JSON.
10. The extraction's `sha256sum` line is pasted nowhere. The seat's log records
    only "The extraction works and matches the expected hash"; the commit body
    names Appendix D but carries neither the hash nor the reds. The three reds
    *are* in the seat's log. §P5 says "paste both" without naming the commit
    body, so this is a minor; the gate reproduced both independently above.
11. `flake.nix` — +10/−1, not the +9/−2 the brief predicted; the one deletion
    is the `mkdir -p` line.
12. The merge commit `7d7ee71` (the orchestrator's) rewrote
    `docs/OPERATIONS.md`'s queue block to a value neither parent holds — base
    `df0ff5d` reads `CR2r3b P10b P11r P5 P8 …`, main `3139087` reads
    `CR4 P10b P5 P8 …`, the merged head `e671511` reads `P10b P8 …`. It is a
    `write-board` regeneration, so it stays inside the `tasks:begin/end` block
    and P11's integration guard admits it; but it is stale again today, so
    `githooks/pre-commit` on this head exits 1 once with
    `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`.
    The same hook on main's parent `cf87659` is green, so the staleness is the
    merge's, not main's. The integrator will need the sanctioned
    `git add docs/OPERATIONS.md` and a second attempt (still one commit).

## Verdict

**APPROVED.** The script is Appendix D and exactly the four contracted changes,
verified by re-extraction, hash and a formatted diff. The rubric is
byte-identical to the design; the judge text carries the deleted sentence and
the three lenses byte-identical to their values. Thirteen assertion groups, all
green; sixteen named mutants, all sixteen killed by the group the plan names.
`RECORD_FIELDS` equals `judgements.py --fields` from both sides. The Ship phase
prints `--dry-run` lines and never launches. `factory-unit`, `evidence-unit`
and `lint` are green on the merged head, along with the js gate, `treefmt`, the
MAP diff and `tasks.py check`. One commit, subject byte-identical, both
trailers, every file inside `touches` or `docs/MAP.md` by the rule, no board
commit, and a result block whose honest `evidence-unit=fail` was right at the
time it was written.
