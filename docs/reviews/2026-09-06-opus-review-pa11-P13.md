---
plan_defect: none
mutants_total: 6
mutants_killed: 4
mutants_outside_named: 2
reviewer: opus
majors: null
minors: 6
---
# Opus gate — seat run pa11, task P13 — APPROVED

## Summary

Fresh clone of `task/P13` at `2f9e8d1` (base `1790ba2`), one commit, twelve
files, `+383/-5`. All four of the implementer's claims hold under refutation:

- **The five extractions are byte-identical to the design.** I re-ran each
  contracted `awk` on `D` myself and `diff`ed against each file's body after
  its leading HTML comment. Four of five are byte-for-byte identical with zero
  diff lines; `rubric.md` differs by exactly **one blank line** at the seam
  between the two concatenated extractions and by nothing else (MINOR below).
  No paraphrase, no dropped row, no reflowed cell anywhere: 29 rows
  M1–M13/R1–R6/O1–O7/T1–T3 with the "if missing" column in four tables; 14
  rubric rows; 14 A-rows; Appendix A's 23 lines.
- **`planning` is the sole dual `spec`+`plan` claimant** and its frontmatter
  description is byte-identical to the plan's contract.
- **`writing-plans` is re-scoped** to the contracted sentence, byte-identical.
- **The archive suite passes 98/98 over 15 files.**

The role sentence is byte-identical in all four files (the diff is a
single-line replacement in each; the rest of every paragraph is untouched) and
the gate's before/after values match the plan's contracted red and green
exactly. All four named mutants change their gate's output as contracted.

Two mutants outside the named set survive every gate — the gate reads only the
role sentence, the frontmatter descriptions and the archive suite, so it is
structurally blind to the six new files' bodies. That is the plan's own
design (the plan assigns the byte-check of the extractions to this gate,
requirement 1), not an implementer defect; I performed that byte-check and it
passes. Recorded as `mutants_outside_named: 2`, not as a MAJOR.

No MAJORs. Six MINORs, none blocking.

## The extractions

`D=/home/dalhaka/nixos-agent-env/docs/superpowers/specs/2026-09-05-planning-agent-design.md`.
Method: `tail -n +5 <file> > got` (skipping the 3-line HTML comment and the
blank line after it) then `diff got <(the contracted awk on D)`.

| file | command I ran | byte-identical? |
|---|---|---|
| `skills/planning/references/inputs.md` | `awk '/^### 2.1/{s=1} /^## 3\. /{s=0} s' $D` | **yes** — `diff` empty (49 body lines) |
| `skills/planning/references/rubric.md` | `awk '/^### 5.1/{s=1} /^### 5.2/{s=0} s' $D` then `awk '/^### 5.3/{s=1} /^### 5.4/{s=0} s' $D` | **all content identical**; one extra blank line at the seam (`23d22 <`) — MINOR 1 |
| `skills/planning/references/anticipation.md` | `awk '/^## 4\. /{s=1} /^## 5\. /{s=0} s' $D` | **yes** — `diff` empty (47 body lines) |
| `skills/planning/references/section-checklist.md` | `awk '/^## Appendix A/{s=1} /^## Appendix B/{s=0} s' $D` | **yes** — `diff` empty (23 body lines, as contracted) |
| `skills/planning/judge-prompt.md` | derived from `awk '/^## Appendix D/{s=1} /^## Revision/{s=0} s' $D` | **yes, word-for-word** on all three lenses and both sentences — see below |

Inventory checks on the clone:

```
$ grep -c '^| [MROT][0-9]' skills/planning/references/inputs.md
29
$ grep -o '^| [MROT][0-9]*' skills/planning/references/inputs.md | tr '\n' ' '
| M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 | M13 | R1 | R2 | R3 | R4 | R5 | R6 | O1 | O2 | O3 | O4 | O5 | O6 | O7 | T1 | T2 | T3
$ grep -n 'if missing' skills/planning/references/inputs.md
7:| # | input | command or path | fresh when | stale or wrong when | if missing |
25:| # | input | path | fresh when | stale when | if missing |
36:| # | input | path | fresh when | stale when | if missing |
48:| # | input | path | fresh when | stale when | if missing |
$ grep -c '^| [0-9]* |' skills/planning/references/rubric.md
14
$ grep -o '^| A[0-9]*' skills/planning/references/anticipation.md | tr '\n' ' '
| A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 | A9 | A10 | A11 | A12 | A13 | A14
$ wc -l < skills/planning/references/section-checklist.md
27            # 4 (comment + blank) + 23
```

The rubric seam, the only difference in the whole set (`cat -A`, file body
lines 21–24 against the concatenated reference lines 21–23):

```
| 14 | judgement calls | … |$
$
$          <-- present only in the file
### 5.3 The threshold and what happens below it$
```

**judge-prompt.md.** Word-stream diff (backticks and `> ` stripped, whitespace
collapsed) against the three `lens:` strings of `const LENSES`:

```
== lens 1 ==  WORD-IDENTICAL
== lens 2 ==  WORD-IDENTICAL
== lens 3 ==  47c47 < '[[repo]]\nname  ---  > '[[repo]]\\nname   (and 2 more)
```

The only lens-3 differences are `\\n` → `\n`: the design's `\\n` is a JS
template-literal escape whose *value* is `\n`, so the file holds the string
the shell would actually see. That is the contracted de-JavaScripting, not a
paraphrase. The two `judgePrompt` sentences differ only by interpolation
removal: `${l.name}` → `<name>`, and `the spec ${REPO}/${A.spec}` → `the
spec`, `the draft ${draft}` → `the draft` (MINOR 2). `grep -c '```'` on the
file prints `0` — no JavaScript, one `##` heading per lens plus one for the
two fixed sentences, all quoted as blockquote prose.

Each of the five files starts with an HTML comment holding its command
(lines 1–3, `<!--` / `command: …` / `-->`).

## The skill body

`skills/planning/SKILL.md`, 158 lines. Frontmatter (`diff` against the plan's
contract string): **byte-identical**.

```
name: planning
description: Write a typed implementation plan from an approved spec under docs/superpowers/specs for this house's dark factory; use when handed that spec path and an output path under docs/reviews/plan-drafts
```

Every rule the plan's Interfaces block requires, present in the skill's own
words:

| required rule | where | verdict |
|---|---|---|
| one output file | L35–36 "**One output file.** The whole plan is one file under `docs/reviews/plan-drafts/`." | present |
| no typed heading outside it | L36 "No typed heading exists outside it."; also L30 | present |
| never read transcripts, seat logs, `dispatch.log`, `.dsh-home`, store bodies | L37–39, all five named | present |
| every fact beside its command; anchor text not line numbers | L40–43 "Cite the anchor text, never a line number" | present |
| `factory-brief <draft> <KEY>` the one seat tool; `factory-dispatch` only `--dry-run` | L44–47 | present |
| a draft until the panel says so | L12–14, L30–31, L51–53, L157 | present (three times) |
| the eight questions of `section-checklist.md` per section | L48–50, and again in Step 4's check L127–129 | present |
| the packet is handed in, never computed | L18–22 ("`tools/factory/seat/factory-plan-brief.sh` composes it"; "**you never compute the packet yourself**"), Step 0 L79 | present |

Steps 0–7 are all present as `###` headings (L77–150) and each carries its
*Check*, matching design §3's step-by-step contract; L73 carries §3's own
"A step whose check fails is repeated, not skipped."

**Nothing in the skill tells a seat to do what the design forbids.** I checked
the design's `RULES` constant (Appendix D) arm by arm: no write outside the
named output, no launch (L44–47 names `factory-brief` as *the one* seat tool
and `factory-dispatch` as `--dry-run` only), no transcript/log/store read
(L37–39), no dispatch and no switch (L157–158: "You do not dispatch, you do
not switch, you do not touch the operator's items"). L74–75's "one plan file,
one judgement file and one concept file" is design §3's own sentence
verbatim in substance, and is the design's sole write exception; it does not
contradict the "one output file" rule, which scopes the *plan*.

## The role sentence and the re-scope

All four hunks are single-line replacements; every surrounding line in each
paragraph is byte-unchanged (`git diff 1790ba2 HEAD`):

```
-prints `MODEL EFFORT`. Roles: implement | review | verify | research | baseline | audit; kind: code | docs;
+prints `MODEL EFFORT`. Roles: implement | review | verify | research | baseline | audit | plan; kind: code | docs;
```

identical hunk in `AGENTS.md` (2-space indented, as Assumption 11 predicts),
`README.md`, `skills/using-superpowers/references/dsh-tools.md`,
`skills/subagent-driven-development/SKILL.md`. The sentence itself —
`Roles: implement | review | verify | research | baseline | audit | plan; kind: code | docs;`
— is byte-identical in all four, which gate (1) confirms by printing one line.

README's new "Model routing" paragraph (`README.md`, after the routing
paragraph) names all four contracted facts:

> The `plan` role routes kind `docs`, sized by the spec's word count
> (the S/M/L boundary from the `wc -w` of the spec); it has no row in the table
> yet, so its lookup falls through to the openrouter default. It is added to
> `~/nixos-agent-env/docs/ledger/routing.toml` when the operator decides a row
> for it.

`skills/writing-plans/SKILL.md` line 3, `diff` against the contract:
**byte-identical**, the description only, name and body untouched.

## The four gates (before/after)

Run by me on the clone (after) and on a scratch checkout of `1790ba2` (before).

**Before, on `1790ba2` — the contracted red, matched exactly:**

```
=== GATE 1 (before) ===
Roles: implement | review | verify | research | baseline | audit; kind: code | docs;
-- count --
0
=== GATE 2 (before) ===
(loop exit 1)                     # nothing printed
=== GATE 3 (before) ===
0
```

**After, on `2f9e8d1`:**

```
=== GATE 1 ===
Roles: implement | review | verify | research | baseline | audit | plan; kind: code | docs;
-- count --
1
=== GATE 2 ===
skills/planning/SKILL.md
=== GATE 3 ===
1
=== GATE 4 ===
$ ls archive/2026-09-05-planning-factory/tests/*.test.mjs | wc -l
15
$ nix develop /home/dalhaka/nixos-agent-env -c node --test archive/2026-09-05-planning-factory/tests/*.test.mjs
ℹ tests 98
ℹ pass 98
ℹ fail 0
ℹ duration_ms 90.350095
```

Gate (2) is genuinely discriminating on this tree: auditing every
`skills/*/SKILL.md` frontmatter description whole-word, `executing-plans` has
`plan` but not `spec`, `writing-skills` has neither (its `specific`/`explains`
substrings are body text, excluded by the frontmatter-only + `-w` form), and
`planning` is the only file with both.

## Mutants

Six run: the four the plan names, plus two outside the named set.

| # | mutant | gate | expected | observed | killed |
|---|---|---|---|---|---|
| 1 | revert the role sentence in three of the four files (`AGENTS.md`, `README.md`, `dsh-tools.md`) | (1) | two lines | two lines (`… audit;` and `… audit \| plan;`) | **yes** |
| 2 | drop the word `spec` from the planning description (`under docs/superpowers/specs` → `requirements document`, `that spec path` → `that path`) | (2) | nothing | 0 lines printed | **yes** |
| 3 | append `Also for a spec-to-plan pass.` to `writing-skills`' frontmatter description | (2) | two lines | `skills/planning/SKILL.md` + `skills/writing-skills/SKILL.md` | **yes** |
| 4 | `git checkout 1790ba2 -- skills/writing-plans/SKILL.md` | (3) | `0` | `0` | **yes** |
| 5 | *(outside)* delete row `M7` from `references/inputs.md` (28 rows, not 29) | (1)–(4) | — | all four gates unchanged: 1 line, `skills/planning/SKILL.md`, `1`, `pass 98` | **no — survivor** |
| 6 | *(outside)* rewrite the SKILL rule to `` `factory-dispatch` you may run in full.`` | (1)–(4) | — | all four gates unchanged | **no — survivor** |

Note on mutant 2: dropping `spec` from *one* of its two occurrences leaves the
gate printing `skills/planning/SKILL.md` (`that spec path` still matches
`-w spec`). The mutant only fires when the word is gone from the whole
description — which is what the plan's wording means, and what the gate
correctly enforces.

Mutants 5 and 6 are the classes this review exists to catch (a dropped
extraction row; a skill rule contradicting the design's `RULES`). The gate is
blind to both by construction; the byte-diff and the rule table above are the
check, and both pass on the real diff.

## Findings

No MAJORs.

**MINOR 1 — `references/rubric.md:23`: one blank line at the extraction seam.**
The file body is `§5.1` then `§5.3` with two blank lines between them where
the concatenated extractions have one. Every character of both extractions is
byte-identical; this is a separator, not a paraphrase or a reflow.

**MINOR 2 — `skills/planning/judge-prompt.md:26`: inconsistent placeholder
handling.** `${l.name}` became `<name>` but `${REPO}/${A.spec}` and `${draft}`
were deleted rather than replaced (`the spec ${REPO}/${A.spec},` → `the spec,`).
The prose meaning survives; a `<spec path>` / `<draft path>` placeholder would
have matched the file's own convention.

**MINOR 3 — `skills/planning/judge-prompt.md:2`: the HTML comment is a source
pointer, not the producing command.** Running it —
`awk '/^## Appendix D/…' ${D} | awk '/^```js$/{s=1;next} /^```$/{s=0} s'` —
prints 232 lines of JavaScript, not this 28-line prose file. Nothing else can:
the file is a transformation by contract ("quoted as prose, no JavaScript").
Wording only.

**MINOR 4 — `rubric.md:2` and `judge-prompt.md:2` leave `${D}` unexpanded**
while `inputs.md`, `anticipation.md` and `section-checklist.md` paste the full
absolute path. A reader who copies the first two gets nothing without setting
`D` first.

**MINOR 5 — `skills/planning/SKILL.md:124`: `**acceptance** (names from the
map)`.** Design §3 Step 4 says "names from `docs/MAP.md`". "the map" collides
with the spec-to-task map the skill itself names in Step 2 (L96).

**MINOR 6 — `skills/planning/SKILL.md` has no trailing newline** (last byte is
`.`); the other five new files end with `\n`. No linter or hook in this repo
checks it.

**Observation (not a finding against the implementer).** The gate cannot fail
on the content of the six new files beyond `SKILL.md`'s frontmatter
description — mutants 5 and 6 prove it. That is the plan's own allocation of
work (P13's requirement 1 hands the byte-check of the extractions to this
gate), so it is not a plan defect; it does mean any future edit to these files
lands with no automated check behind it.

## Verdict

**APPROVED.**

- **Extractions:** five files, five contracted commands re-run by me, all
  content byte-identical to `D`; one cosmetic blank line (MINOR 1).
- **Skill body:** eight required rules all present in the skill's own words;
  Steps 0–7 with their checks; nothing that tells a seat to write elsewhere,
  run a launch, or read a transcript.
- **Role sentence:** byte-identical across the four files, paragraphs
  otherwise unchanged; README's paragraph carries all four contracted facts.
- **Re-scope:** byte-identical.
- **Gates:** before `(one line, 0) / (nothing) / (0)`; after
  `(one line, 1) / (skills/planning/SKILL.md) / (1) / (98/98, 15 files)` —
  the contract, exactly.
- **Mutants:** 4 named, 4 killed; 2 outside the named set, both survivors, by
  the gate's design.

**Commit convention:** one commit `2f9e8d1` on `1790ba2`; subject `diff`ed
against the plan and **byte-identical**; a blank line then
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run pa11)`
and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`;
`git diff --name-only 1790ba2 HEAD` lists exactly the twelve files of
**touches** and nothing else; `grep -c '^archive/'` on that list prints `0`;
no board commit (this repo has no board); working tree clean.

**CHANGELOG:** one dated block, `## 2026-09-06` plus one line, appended above
`## 2026-09-05`; nothing else in the file changed.

**The catalog symlink.** Confirmed read-only (I did not touch it):

```
$ ls -l ~/.local/share/dsh-openrouter/skills
lrwxrwxrwx 1 dalhaka users 39 Sep  3 19:14 … -> /home/dalhaka/flakes/dsh-harness/skills
$ ls ~/flakes/dsh-harness/skills        # 15 skills, no `planning` yet
$ git -C ~/flakes/dsh-harness log --oneline -1
1790ba2 integrate H2c into integ/hr1
```

Because the symlink resolves to the working tree of `~/flakes/dsh-harness`,
`skills/planning` becomes visible to every seat the moment this branch is on
that repo's `main` — no install step. **Integration here means**, as H2c was:
`FACTORY_CHECK_CMD='nix develop /home/dalhaka/nixos-agent-env -c node --test archive/2026-09-05-planning-factory/tests/*.test.mjs' tools/factory/seat/factory-integrate pa11 ~/flakes/dsh-harness P13`,
then the orchestrator's fast-forward
`git -C ~/flakes/dsh-harness pull --ff-only ~/factory/base/dsh-harness integ/pa11`,
gated on both exit codes.
