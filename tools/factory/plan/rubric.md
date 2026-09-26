### 5.1 The rubric (14 rows, 0–3 each, 42 points)

The comparison's ten rows, with two rows split and three added. Each row has
its anchor for 3 and the mutant or proxy that makes the score falsifiable.

| # | criterion | 3 means | 0 means | how a judge falsifies it |
|---|---|---|---|---|
| 1 | spec coverage | every spec item maps to a task or an explicit `out:` | items silently dropped | pick a spec item at random; find its task |
| 2 | correct facts | zero wrong facts; every fact carries its command | four or more wrong facts | re-run three cited commands; compare |
| 3 | self-contained sections | `factory-brief` output alone lands the task: paths, signatures, code or test bodies, no "similar to", no "read X and copy its shape" | the section is a list of topics | run `tools/factory/seat/factory-brief <draft> <KEY>` (read-only; the rules name it) and read that output with the rest of the plan hidden; list what is missing |
| 4 | TDD discipline | a red command and its expected red output per task, then green by check name | "add tests" | delete the red step; is anything lost? |
| 5 | mutant per assertion; discriminating fixtures | every assertion names its one-line mutant; every fixture has the row that makes it discriminate (second gap, flapping run, one payload per rule, every enum arm, the default branch) | fixtures of one row; no mutants | pick two assertions; name a mutant that survives them |
| 6 | interfaces and error contracts | every producer of every field; every enum arm; exit and stdout on every internal failure; which tree a derivation reads | a guard that can never fail; a stream with no id contract | ask "what happens when stdin is a terminal / the payload nests 1,000 deep / the file is absent" |
| 7 | rules, not enumerations | boundaries are stated as rules (tokenise, any token, every ancestor, every producer); a failure the driver can refuse is a guard task, not a sentence | a list of spellings; a warning where a guard belongs | write one spelling outside the list; a plan that ships a sentence where a driver guard belongs scores 2 |
| 8 | waves, touches, conflicts | waves derived from `dependsOn` (the peel-off groups `tasks.py waves` prints); explicit `touches`; `conflicts` run and its hits sequenced | no waves; globs in `touches` | run `conflicts` on the scratch copy (Step 3's form) |
| 9 | invariant awareness | brief §3 named where it binds; no key in a Nix expression; no widening of an agent's reach | an invariant silently touched | grep the plan for `/var/lib/secrets`, `sudo`, `systemctl` |
| 10 | operator steps and rollback | one command each with acceptance and expected output; the switch closure; the rollback generation | one paragraph of prose | run the dry forms |
| 11 | anticipation | §4's rows present where their trigger applies: dispatch lines, switch delta, prepared relaunch, claims to close, questions pre-asked, the hook and deny-rule tables | none | for each trigger in §4 that applies, find the artefact |
| 12 | economy | nothing restated; facts once; no appendix repeating the inventory | > 3× the shortest complete plan for the same spec | word count against the spec-to-task map |
| 13 | format and graph compliance | `parse_plan` reads every task; `check` empty; real check names; byte-exact subjects; no typed heading in the draft while it sits under the plans glob | the graph cannot read it | until P1: the scratch copy with the draft, a one-repo `--repos` file and `--runs-dir /nonexistent --store /nonexistent` (Step 3; the `--root`-only form cannot see the draft and scores 3 unconditionally); after P1: `tasks.py check --draft` |
| 14 | judgement calls | every open decision stated with the reason and the alternative; ≤ 3 operator questions each with a recommendation | decisions hidden in tasks | list the decisions; count the reasons |

### 5.3 The threshold and what happens below it

Dispatch at **34 of 42** (81 %) *and* no median below 2 on rows 2, 3, 5, 6, 7
and 13 — the six rows that account for the 42 plan-caused rejections. Below
the threshold the draft is revised against the judges' errata (each erratum
names the row, the task, the finding and the fix) and re-judged; at most two
revisions, then the operator sees the scores and decides. A plan is never
dispatched on the author's word. The number 34 is a starting point and is
**unmeasured** (owner: the P10 report): the comparison's three plans were
scored on ten rows of 30 — 21, 26, 28 — and have not been rescored on the
fourteen rows; mapped proportionally (21/30 → 29, 26/30 → 36, 28/30 → 39 of
42) it falls between the rejected house plan and the two clean arms, a proxy
declared with its gap (the four new rows are unscored on them; a rescoring by
the designer alone would be one judge of the author's own model family, the
bias the comparison declared). After ten judged plans the P10 report proposes
the score that separates plans landing first try at ≥ 70 % from the rest; the
move lands as a commit that cites the report line, like a routing row, and the
record says when it moved. The threshold never moves itself.

Cost of the gate, at list prices and today's plan sizes: each judge reads
1–4k words of spec, 2–13k of plan and the touched files — of the order of
100–250k input tokens; Sonnet at $2 in / $10 out, Opus at $5 / $25: roughly
$1–3 per judging round for the three. One avoided rejection repays it (§1).

