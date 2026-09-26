# `plan_defect` label-consistency audit — every ledger row, leave-one-out (2026-09-08)

**What this is.** One independent classification of every row of
`docs/ledger/plan-defects.toml` by a model that never saw the row's own
label, scored against the ledger. Every row where the two disagree is listed
below with the classifier's rationale as a **re-read candidate**. **No label
is changed by this file**; the ledger changes only by a commit that cites a
re-read (the precedent is bk3 · B1b, `f86ccde`: three adversarial readers,
the ledger held, a secondary was added).

**What it is not.** Not a second labeller of record. The 2026-09-07 probe
(`docs/reviews/2026-09-07-gpt6-plan-defect-classification.md` and its
addendum) found the same classifier at 6-way 16/20, plan-vs-implementer
19/20 on the sealed rows with implementer examples — good enough to flag
rows, not to relabel them.

## Method

- **Corpus:** all 66 rows of the ledger at `2c23cfc` (the board's count was
  65; the sixty-sixth, tel3 · T3M, was filed in `6ccabf5` after that count).
  Classes: missing-case 20, vacuous 15, implementer 12, wrong-fact 9,
  underspecified 9, process 1; 18 rows carry a secondary.
- **Classifier:** `codex exec -m gpt-6-astra`, `model_reasoning_effort=high`,
  `--sandbox read-only`, `--output-schema` (the six-class enum, an optional
  secondary, a ≤ 40-word rationale, a confidence), six in parallel. Harness
  preserved at `~/factory/probe/plan-defect-audit/` (`audit-build.py`,
  `audit-run.sh`, `audit-score.py`, `audit-prompt.txt`); every output,
  transcript and the leak manifest under `results/audit-2026-09-08/`.
- **Leave-one-out, three layers, per row:** (a) the review with its YAML
  front matter and every body line matching `^plan_defect(_secondary)?:`
  stripped (pa4 · P4, pa5 · P6 and pa3 · P11 carried one in the body);
  (b) a per-row copy of the design doc
  (`docs/superpowers/specs/2026-09-05-planning-agent-design.md`) with the
  row's own Appendix B row and every line naming the key beside a class word
  removed — one to five lines for the 45 rows Appendix B or §7 name, none for
  the 21 filed after it (the manifest lists each removed line); (c) the
  *other* implementer rows' review summaries as worked examples (eleven for
  an implementer row, twelve otherwise) — the configuration that scored best
  on 2026-09-07. The classifier's cwd held only the cleaned files.
- **Leak check after the run:** the 66 session records show three shell
  commands per classifier (four in three of them), every one a `sed` or
  `cat` over its own two files (§7 and Appendix B by line range, then the
  review); no command named the repo, the ledger, the factory or a review
  path. Cost: 1.56 M flat-rate tokens, mean 23.6 k per row.

## Result

| measure | value |
|---|---|
| 6-way agreement (primary = primary) | 44 / 66 = 67 % |
| primary matches the ledger's primary or secondary, or the classifier's secondary matches the ledger's primary | 48 / 66 = 73 % |
| plan-vs-implementer agreement | 50 / 66 = 76 % |
| classifier gave a secondary | 31 rows (ledger: 18) |
| confidence, median | 0.98 on agreeing rows, 0.98 on disagreeing rows — uninformative, as on 2026-09-07 |

Confusion (ledger → classifier):

| ledger \ classifier | vacuous | missing-case | underspecified | wrong-fact | implementer | process |
|---|---|---|---|---|---|---|
| vacuous (15) | **12** | — | — | — | 3 | — |
| missing-case (20) | 2 | **9** | — | — | 9 | — |
| underspecified (9) | 1 | 1 | **3** | — | 4 | — |
| wrong-fact (9) | — | 2 | — | **7** | — | — |
| implementer (12) | — | — | — | — | **12** | — |
| process (1) | — | — | — | — | — | **1** |

**The pull is one-directional.** All twelve ledger-implementer rows come
back implementer; every plan-vs-implementer disagreement (16 of the 22) is a
ledger plan class the classifier calls implementer. The rationales share one
sentence: *the plan named the requirement, the seat failed it, therefore the
implementer*. The ledger's labels follow the design's rule instead — a
requirement the plan named without a test that could fail on it is still the
plan's defect (the 2026-09-07 rule "a named proof shape is not a mutant",
`1b8d126`; §3, rubric row 5). So the re-read question for those sixteen is
exactly that rule, row by row: *did the plan name the mutant, or only the
requirement?* The other six disagreements are inside the plan side (which
plan class) and are the cheaper re-reads.

## Re-read candidates (22)

The classifier's rationale is quoted verbatim; "conf" is its own number.

### A. Ledger plan class → classifier `implementer` (16)

| run · key | ledger | classifier | conf | rationale |
|---|---|---|---|---|
| cr8 · CR2 | missing-case | implementer | 0.90 | The plan prescribed protected-prefix handling. The implementer substituted an exact-file rule, losing ancestor semantics: `rm -rf .claude` and `git clean -fd` still ALLOW. The review explicitly identifies that substitution as the source of the hole. |
| cr15 · CR2r | missing-case (+implementer) | implementer | 0.94 | MAJOR-2 violates the explicit contract requiring force detection with or without -d/-x; MAJOR-4 allows cpio in .claude despite a required DENY matrix row. These are implementation deviations from specified behavior. |
| ev1 · R5 | missing-case (+wrong-fact) | implementer (+wrong-fact) | 0.99 | The sole major is the omitted Flash price row, which Step 3 explicitly required. The implementer deviated from an adequate requirement. Separately, the plan dictated the false claim that the driver only honours inherited XDG_CACHE_HOME. |
| og1 · OG1 | missing-case | implementer | 0.99 | The review explicitly says all MAJOR bypasses were named in the task brief. The implementation omitted path normalization supplied by the referenced guard and allowed git global-option spellings; its tests exercised none of these required cases. |
| og1 · OG1b | underspecified | implementer | 0.98 | OG1b step 1(b) explicitly required `--work-tree=…` support. The implementation omitted it, allowing a verified `git --work-tree=. commit --amend` bypass—the review's expressly unaccepted MAJOR deviation. |
| og3 · OG1r | underspecified | implementer (+missing-case) | 0.99 | The Deviations section explicitly says the plan required newline boundaries and any write-capable verb with a plan path; implementation violated both. Separately, MINOR 13 attributes omitted ordinary writers to the plan's enumerated verb list. |
| og4 · OG1r2 | missing-case | implementer (+missing-case) | 0.99 | MAJOR 14 explicitly says the plan's unconditional `mv` contract was not followed; MAJOR 18 violates its stated timing budget. MINOR 18 separately identifies write verbs omitted by the plan, supporting a missing-case secondary. |
| rt1 · RT1 | vacuous | implementer | 0.96 | The plan's Interfaces section explicitly requires both override rules and factory-review's role/effort behavior. The implementer left these requirements untested, allowing M5, M6, M11, and M12 to survive. |
| rt2c · RT2 | vacuous | implementer (+underspecified) | 0.90 | The plan explicitly required the cross-check mutant to fail, but M4a survived; finding 1 says the plan already requested the needed fixture. Separately, freezing flake.nix left the sandbox coverage contract unresolved. |
| rt5 · RT5 | missing-case | implementer | 0.96 | MAJOR-1 says the plan required the "same rule for shell commands," but quoting and line continuations bypass enforcement. The continuation was explicitly listed as must-deny; the implementation failed the stated requirement. |
| rt5 · RT5b | underspecified | implementer | 0.98 | MAJOR-1 violates explicit plan requirements: Step 3 says "never raise," and unparsable routing tables must DENY. The implementation instead raises uncaught RecursionError and UnicodeDecodeError, causing the harness to allow. |
| sb5 · SB2b | missing-case | implementer | 0.98 | MAJOR-1: contract item (3) explicitly permits only dotted IPv4 addresses and requires die 2 otherwise, but the implementation accepts 256.1.1.1 and passes it to --host. The stated contract was adequate; the regex violated it. |
| sc4 · G8b | underspecified | implementer | 0.98 | MAJOR-2 repeats the host-local dependency explicitly forbidden by the task brief. The implementation also violates Step 4's requirement that the committed block match the hook's derivation, and Step 3's pre-commit acceptance fails. |
| sc5 · G11 | missing-case | implementer | 0.98 | The declared G11 plan was delivered and well tested. Rejection centers on an undeclared, unallowed change: widening check to a global namespace contradicted G4's pinned per-repo rule while leaving cross-repo dependencies permanently blocked and untested. |
| cr17 · CR2rb | missing-case | implementer | 0.87 | MAJOR-1 is a regression introduced by the implementer's tokenizer rewrite: quoted separators become clause boundaries, contradicting its documented contract and allowing previously denied plan writes. The review says CR2rb fulfills its planned fixes. |
| bk3 · B1b | vacuous (+implementer) | implementer (+wrong-fact) | 0.99 | Contract item 2 required a layout-based assertion or fixture; the implementation supplied redundant membership checks that never read the layout, allowing M-H to survive. Separately, MINOR 4 identifies the plan's false assertion that restic runs as root. |

bk3 · B1b was re-read on 2026-09-07 and the ledger held; it stays in the
table because the audit is the record of what the classifier says, and its
new secondary (`wrong-fact`: "restic runs as root") is a sentence nobody has
checked yet. rt1 · RT1, rt2c · RT2 and sb4 · SB2 were named on 2026-09-07 as
the shape of B1b; the classifier splits them (SB2 agrees vacuous, RT1 and
RT2 do not) — a re-read of the three together tests whether the rule is
being applied consistently.

### B. Inside the plan side — which plan class (6)

| run · key | ledger | classifier | conf | rationale |
|---|---|---|---|---|
| a7 · N16 | wrong-fact | missing-case | 0.91 | Major A exposes an undocumented, untested overlap: account-wide activity already includes lane costs. Major B drops buckets without matching sessions. These require explicit overlap and unmatched-bucket cases; the review provides no evidence of an adequate plan being disobeyed. |
| ev3 · R3r | missing-case | vacuous | 0.99 | Step 3 ordered deletion of the status test without replacement. Deleting the entire ExecMainStatus guard (MG1) leaves all 145 tests passing. The reviewer explicitly attributes this untested contract to the plan, which the implementation followed correctly. |
| sc1 · G5 | underspecified | vacuous | 0.99 | Step 4 prescribed the wiring verbatim: lint scans zero plans in the sandbox and always exits 0, even with dependsOn ZZZ planted. The reviewer explicitly identifies this as an inherited design defect. |
| pa5 · P6 | missing-case | vacuous (+underspecified) | 0.92 | MAJOR 1 matches Appendix B's masked-rule example: the 13-score fixture fails on total mismatch, so deleting the count check stays green. Separately, the plan left judgement_path validation unspecified, allowing a 272-byte prose filename into storage. |
| cr20 · CR2r3 | underspecified (+missing-case) | missing-case | 0.82 | MAJOR-1: the plan targeted $(…) and seven named fault injections, omitting process substitutions and `headings`. The implementation satisfied those checks, but a `headings` fault inside <(…) silently allowed a heading-removing Edit. |
| pb3ar2b · P3Ar2b | wrong-fact (+implementer) | missing-case (+implementer) | 1.00 | Contract item 1 omitted eight legitimate synthetic-fixture tests, which fail under literal compliance. The implementer's overly broad `tmp_path` exception then allowed live-ledger counts through; the omitted case made the plan inadequate first. |

Two of these (R3r, G5) are the classifier reading "the plan dictated a test
that cannot fail" as `vacuous` where the ledger reads "the plan left the
replacement / the tree unnamed" as `missing-case` / `underspecified`; a
one-sentence tie-break in §7's enum text would settle that class boundary
for every future row. cr20 · CR2r3 and pb3ar2b · P3Ar2b are primary/secondary
swaps — the ledger already carries the classifier's class as the secondary.

## Notes for the re-read, not findings

- pa4 · P4's review body carries `plan_defect: wrong-size — the budget
  arithmetic omitted the 1,200-char in-flight cap` (a value outside the enum;
  the ledger and the front matter say `wrong-fact`, and the classifier
  agrees). The lint gate reads the front matter only; the body line is a
  stale draft of the label and can be left as filed.
- The classifier volunteers a secondary on 31 rows against the ledger's 18;
  the 13 new secondaries (a4 · N7c vacuous, b3 · F9/BFIX vacuous, cr2 · CR1
  implementer, cr6 · CR3 missing-case, ev1 · R1 underspecified, ev2 · E2b
  wrong-fact, fd1 · FD1 process, mcf2 · P1flash implementer, sb1 · SB3
  vacuous, sc1 · G1 missing-case, sc5 · G12 vacuous, pa4 · P4 implementer,
  pa3 · P11 wrong-fact, pb11 · P11b wrong-fact, tel1b · T1 wrong-fact) are
  not disagreements and are not listed above; the report line counts
  primaries only.
- The 2026-09-07 probe's sealed-set numbers (16/20, 19/20) do not carry to
  the whole ledger (44/66, 50/66): the sealed set was implementer-heavy (the
  rows filed after Appendix B), which is the class the classifier gets right
  every time.

## Appendix — all 66 rows

| run · key | ledger | secondary | classifier | classifier secondary | conf | agree |
|---|---|---|---|---|---|---|
| a3 · W2-N6b | missing-case | — | missing-case | — | 0.88 | yes |
| a4 · N7c | missing-case | — | missing-case | vacuous | 0.89 | yes |
| a7 · N16 | wrong-fact | — | missing-case | — | 0.91 | **no** |
| a9 · N19 | wrong-fact | — | wrong-fact | — | 0.99 | yes |
| b3 · F9/BFIX | missing-case | — | missing-case | vacuous | 0.92 | yes |
| b2 · F6 | wrong-fact | — | wrong-fact | — | 0.96 | yes |
| cr2 · CR1 | missing-case | — | missing-case | implementer | 0.95 | yes |
| cr6 · CR3 | underspecified | — | underspecified | missing-case | 0.86 | yes |
| cr8 · CR2 | missing-case | — | implementer | — | 0.90 | **no** |
| cr15 · CR2r | missing-case | implementer | implementer | — | 0.94 | **no** |
| ev1 · R1 | vacuous | — | vacuous | underspecified | 0.96 | yes |
| ev1 · R5 | missing-case | wrong-fact | implementer | wrong-fact | 0.99 | **no** |
| ev1 · R8 | vacuous | — | vacuous | — | 0.97 | yes |
| ev2 · E2 | vacuous | — | vacuous | — | 1.00 | yes |
| ev2 · E2b | vacuous | — | vacuous | wrong-fact | 0.99 | yes |
| ev2 · E7 | vacuous | — | vacuous | — | 0.94 | yes |
| ev2 · E7b | vacuous | — | vacuous | — | 0.93 | yes |
| ev3 · E6 | vacuous | — | vacuous | — | 0.99 | yes |
| ev3 · E9 | vacuous | — | vacuous | — | 0.99 | yes |
| ev3 · R3r | missing-case | — | vacuous | — | 0.99 | **no** |
| fd1 · FD1 | wrong-fact | — | wrong-fact | process | 1.00 | yes |
| hr1 · H2 | wrong-fact | — | wrong-fact | — | 0.99 | yes |
| mcf2 · P1flash | wrong-fact | — | wrong-fact | implementer | 0.96 | yes |
| mcp2 · P3 | vacuous | — | vacuous | — | 0.99 | yes |
| og1 · OG1 | missing-case | — | implementer | — | 0.99 | **no** |
| og1 · OG1b | underspecified | — | implementer | — | 0.98 | **no** |
| og3 · OG1r | underspecified | — | implementer | missing-case | 0.99 | **no** |
| og4 · OG1r2 | missing-case | — | implementer | missing-case | 0.99 | **no** |
| rt1 · RT1 | vacuous | — | implementer | — | 0.96 | **no** |
| rt2c · RT2 | vacuous | — | implementer | underspecified | 0.90 | **no** |
| rt5 · RT5 | missing-case | — | implementer | — | 0.96 | **no** |
| rt5 · RT5b | underspecified | — | implementer | — | 0.98 | **no** |
| sb1 · SB3 | underspecified | — | underspecified | vacuous | 0.85 | yes |
| sb4 · SB2 | vacuous | — | vacuous | — | 0.96 | yes |
| sb5 · SB2b | missing-case | — | implementer | — | 0.98 | **no** |
| sc1 · G1 | vacuous | — | vacuous | missing-case | 0.99 | yes |
| sc1 · G2 | process | vacuous | process | vacuous | 0.97 | yes |
| sc1 · G5 | underspecified | — | vacuous | — | 0.99 | **no** |
| sc1 · G10 | vacuous | — | vacuous | — | 0.96 | yes |
| sc4 · G8b | underspecified | — | implementer | — | 0.98 | **no** |
| sc5 · G11 | missing-case | — | implementer | — | 0.98 | **no** |
| sc5 · G11b | missing-case | — | missing-case | — | 0.99 | yes |
| sc8 · G12b | underspecified | — | underspecified | — | 0.98 | yes |
| sc5 · G12 | implementer | missing-case | implementer | vacuous | 0.97 | yes |
| oi1 · DA1 | implementer | missing-case | implementer | — | 0.99 | yes |
| cr17 · CR2rb | missing-case | — | implementer | — | 0.87 | **no** |
| bk3 · B1b | vacuous | implementer | implementer | wrong-fact | 0.99 | **no** |
| cr18 · CR2r2 | missing-case | implementer | missing-case | — | 0.85 | yes |
| cr19 · CR2r2b | implementer | — | implementer | — | 0.99 | yes |
| pa4 · P4 | wrong-fact | — | wrong-fact | implementer | 0.96 | yes |
| pa5 · P6 | missing-case | — | vacuous | underspecified | 0.92 | **no** |
| pa3 · P11 | missing-case | — | missing-case | wrong-fact | 0.99 | yes |
| cr20 · CR2r3 | underspecified | missing-case | missing-case | — | 0.82 | **no** |
| pa6 · P2 | missing-case | implementer | missing-case | implementer | 0.99 | yes |
| pa10 · P10 | implementer | wrong-fact | implementer | wrong-fact | 0.99 | yes |
| pb3a · P3Ab | wrong-fact | implementer | wrong-fact | implementer | 1.00 | yes |
| pa9 · P8 | missing-case | wrong-fact | missing-case | wrong-fact | 0.98 | yes |
| pb3arb2 · P3Arb | implementer | wrong-fact | implementer | wrong-fact | 0.99 | yes |
| pb3ar2 · P3Ar2 | implementer | — | implementer | — | 0.99 | yes |
| pb3ar2b · P3Ar2b | wrong-fact | implementer | missing-case | implementer | 1.00 | **no** |
| pb11 · P11b | implementer | — | implementer | wrong-fact | 0.98 | yes |
| tel1b · T1 | implementer | missing-case | implementer | wrong-fact | 0.97 | yes |
| tel2 · T1W | implementer | vacuous | implementer | vacuous | 1.00 | yes |
| tel2 · T3 | implementer | vacuous | implementer | vacuous | 1.00 | yes |
| tel2 · T2 | implementer | missing-case | implementer | missing-case | 0.99 | yes |
| tel3 · T3M | implementer | — | implementer | — | 0.99 | yes |
