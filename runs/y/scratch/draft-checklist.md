# Appendix A — the eight questions, answered per section (draft-0.md, 2026-09-06 seat-driver plan)

Q1 mutant per assertion · Q2 discriminating fixture rows · Q3 rules not spellings · Q4 interface reads/emits/consumers · Q5 facts with commands · Q6 no step whose output fails its own acceptance · Q7 fix-round/re-plan items · Q8 factory-brief is the whole contract.

## SD1 — the ladder
1. Yes: rows 1–11 each name the one-line mutant (print the rung-1 row for an unknown rung; count `class` as `any`; drop the route-change exemption; search all routes for a fallback; accept any integer rung; let `models` see rung-3 rows; strip `a`).
2. Yes: a rung-3 row on the other route; an equal-specificity `class` pair; two-variable and zero-variable adjacent pairs; a fallback on the `claude` route; `T10a` vs `SD1b`; `OG1r2` vs `SD1r`; the committed table itself (row 7).
3. Yes: the ladder is defined by resolution per rung (most-specific over four fields), not by row order; the one-variable rule is stated for every adjacent pair with the route-change exemption; the class vocabulary is one list pinned across three files.
4. Yes: reads `routing.toml` (or FILE / `FACTORY_ROUTING_TABLE`); emits `MODEL EFFORT` or the four-field line; exit 3 with the exact `ladder exhausted at rung N for …` text; consumers named (factory-task, seat-submit via `resolve`, `models` for the dark factory, hook-guard's model rule unchanged).
5. Yes: every fact pasted with its command (route.py's silent acceptance of `rung`, factory_route's `unknown key`, the 14 rows, the claims shape, the render test's `routePy`).
6. No step's output fails the acceptance: the committed table must pass both checks (row 7), and the rows written satisfy the D1 rule by construction.
7. Not a fix round.
8. Yes: `factory-brief draft SD1` reproduces the section whole (verified, 4/4 markers).

## SD2 — the class
1. Yes: five rows with mutants (first entry only; drop the tie rule; reorder `nix-check` before `vm-test`; omit the key; accept any name; drop the cap).
2. Yes: the one-each tie (C1), the 2-vs-1 majority (C2), the double-matching VM file (C3), the no-touches docs task (C4), the directory entry (C5), a 30-key wave for the cap.
3. Yes: the class is "most entries matched; tie → earliest rule; nothing → any" — a rule; the glob file is data with a validated vocabulary; the brief line is a new line so no existing spelling changes.
4. Yes: reads `<root>/docs/ledger/task-classes.toml`; emits the word or exit 1/2 with named messages; `check` rule (g); consumers: the brief, `json`, `factory-task` (SD3).
5. Yes: `grep class tasks.py` empty, `parse_plan` keys, the `Next wave` assertion and the 40-line budget, the fixture dir, the sandbox copy of `docs/ledger`.
6. No: the brief's new line is under the 40-line budget and the existing `Next wave` assertion is untouched.
7. n/a.
8. Yes (4/4 markers).

## SD3 — the driver
1. Yes: rows 1–10 (derive the rung from the run name; launch anyway; accept the exhausted default; ignore `--fallback`; die on the class failure; drop the block; count the inline sentence; drop the survivor filter; read the log; drop the branch; print after the rules).
2. Yes: `K1`/`K1b`/`K1r` from one root; rows with and without a fallback; the review with an inline "six minors" sentence vs line-initial markers; the survivor table row among other rows; the `chmod 000` log; the 400-line review for the cap; `--prior nonsense`.
3. Yes: the finding-line rule is stated as "first token after decoration is BLOCKER/MAJOR/MINOR" (T3's marker rule), the survivor rule as "table row containing surviv"; the rung from the key by the tokeniser rule; no list of review spellings.
4. Yes: reads the `.result`, the review file (two locations, precedence), never the log; emits the four-field route, the result lines, exit codes 0/1/2/3/4 with 4 named for `skipped`; the launch line's contents; the `FACTORY_PRIOR_BLOCK` env consumed by factory-brief; `FACTORY_SEAT_SPOOL` consumed here, produced by seat-run (SD4).
5. Yes: every anchor pasted (the route line, the seat-submit branch, the exit table, `FACTORY_BRIEF_EXTRA`, T2's planned lines, the review naming rule, dark-factory's required args, the bats idiom).
6. No: the escalate `.result` uses `status=skipped`, an arm of T2's enum and of factory-wave's summary.
7. n/a.
8. Yes (4/4; the `## Prior attempt` template is indented so the extractor keeps the section whole — verified line 48 of the brief).

## SD4 — the drive job
1. Yes: rows 1–11 (fall back silently; hard-code Pro medium; accept `--model`; compare strings; `os.path.exists`; call systemctl anyway; stop the unit; accept `--wait` on web; write the marker under `--no-start`; write into the final path; export for web).
2. Yes: a default row whose effort differs from the orchestrate row (`low`) so the resolve rule discriminates; the realpath-equal symlinked home; the dangling symlink; the `os.rename` recorder that checks `job.json` exists at rename time.
3. Yes: the shared-home rule is by realpath equality; the payload rule by "regular file after following symlinks"; the route resolved by the one implementation; the atomic directory by rename, not by a wait.
4. Yes: reads the table and `route.py` by path with named defaults; emits exit 2 with the exact messages, 124 on timeout without `systemctl`, `job.json`'s new `route` key (`null` for other modes); consumers: the spool (D7, the `started` marker), seat-run (`drive` branch), SD3 (`FACTORY_SEAT_SPOOL`).
5. Yes: the argparse anchors, seat-run's branches, the byte-exact `job.json` assertion, the package's `exec python3`, the sandbox copy lines, the decision addendum sentence, the wrapper's warn-not-refuse.
6. No: the existing `job.json` equality test is updated in the same task (`"route": None`), named as such.
7. n/a.
8. Yes (4/4).

## SD5 — the spool
1. Yes: rows 1–7 plus the seat-eval and VM mutants (start without `--no-block`; skip the marker; ignore the marker; drop any one rule; start `.tmp-` dirs; stop at the first refusal; exit 0 on a missing dir; ignore the range; `PathChanged`→`PathModified`; a `bash -c` in ExecStart; a sixth ReadWritePaths entry; a dropped package; `/tmp` admitted again).
2. Yes: one job per refusal reason (fifteen shapes); the three skipped names; the marker written by seat-submit vs by the spool; three jobs with one refused; the range flag; the VM's hand-written `port: 1` job and the `.tmp-x` dir.
3. Yes: validity is a closed rule set with fixed reason strings; "skip when `started` or `exit_code.txt`" is the idempotency rule; the name regex, not a list of names.
4. Yes: reads the jobs dir and each `job.json`; emits `started`/`refused` files and one log line per decision; exit 0/2; the unit's options asserted as literals; the VM steps' exact commands and expected strings; consumers: systemd (the path unit), the operator (journal), SD10.
5. Yes: the module anchors, the wrapper's cache lines and the VM's `/tmp` comment, seat-eval's shape, the VM's existing steps and the negative grep, the lane precedent, the interpreter fact.
6. No: the VM fixtures move under `/var/lib/seat/…`, which the unit may write, so every existing step still passes; the negative `grep -rq sk-or-vm-fixture /var/lib/seat/jobs` is honoured by every fixture.
7. n/a.
8. Yes (4/4).

## SD6 — the rule file
1. Yes: rows 1–7 (accept unknown kinds; keep last-wins; allow on a missing file; keep the literal arrays; drop the `home` kind; print a literal; any regression; a seventh prefix).
2. Yes: the file minus one row per table (verb, protected dir, git row); the `$HOME` edit; the malformed array line; the duplicate word; the committed file vs hook-guard's list as sets.
3. Yes: kinds and families are closed enums; the readers fail closed on anything outside them; the file's shape is one rule (blocks of scalar lines).
4. Yes: reads `<dir of $0>/../docs/ledger/guard-rules.toml` or `ORCHESTRATOR_GUARD_RULES`; emits a deny with `guard rules unreadable: <file>: <reason>` on every tool on failure; `--check-rules` exit 0/1; consumers: the two lint gates, SD7's reader, the operator (reason strings).
5. Yes: the function count and names, the two arrays' lines, the `case` arms, the header, the sweep test's assertion, the sandbox copies, the lint pair.
6. No: `--check-rules` on the committed file is an acceptance and the file is written from the literals verbatim.
7. n/a.
8. Yes (4/4).

## SD7 — hook-guard parity
1. Yes: rows 1–7 (allow on a missing file; any single family; port the heading rule instead; accept a bad kind; let the exception escape; drop the flag; any port defect — the test prints the differing rows).
2. Yes: the 442 sweep rows themselves (the reviews' quoted, continued, `cd`-based, python/perl, `xargs`, `tar -C`, glob and ancestor spellings), the malformed rules copy, the symlink loop, the 20,000-token path string, the recipe list.
3. Yes: parity with an oracle over the fixture is a rule, not a verdict list; the token scan has no command position; the families come from the file.
4. Yes: reads `--guard-rules` (or `FACTORY_GUARD_RULES`, or the default), the routing table as before; emits the orchestrator's own reason strings, `guard rules unreadable at <path>`, `bash rule could not be evaluated: <Exc>`; always exit 0; consumers: dsh's hook bridge, `dsh-openrouter --denials`, the lane agreement test.
5. Yes: hook-guard's anchors and its RT5r contract sentence, the wrapper's `hook_command`, the package's build-time embedding and flake8, the 70/91 bats idioms, the sweep rows of both kinds, the lane test's line.
6. No: the recipe-allow test guards the seat's own WORKSPACE RULES commands.
7. n/a.
8. Yes (4/4).

## SD8 — the record
1. Yes: widen the enum; drop the `re`; store the launch line; default the rung to 0; `>` for `>=`; count landed by status; unstable sort.
2. Yes: the 7/4/1 group sizes across the n=5 gate; the unknown head; the `launch:` line that must not land; `claude/plan` that must not; `prior: "r1"`/`"r1/K 1"`.
3. Yes: role from the route label's first segment; landed = head ∈ `rev-list HEAD` (a rule over git, not a status word); refusal by `n_gate`.
4. Yes: reads the store's derived streams through `join_tasks_gates`, the repo's `rev-list`; emits the header, one line per group in a fixed grammar, the trailer; exit 0/2; consumers: the operator (Operator step 6), the runbook.
5. Yes: `ls pkgs/evidence` (no streams/ingest), the plan's field lines, the duckdb column and count facts, report.py's structure, T10a's `n_gate`, evidence.py's `report` dispatch.
6. No — and Step 0 refuses to guess the landed field name.
7. n/a.
8. Yes (4/4).

## SD9 — the driving skill
1. The four gate commands are the assertions; mutants: `escalation` in the skill → gate (2); a second `drive` description → gate (4); no frontmatter → gate (3).
2. The second skill claiming `drive` is the discriminating fixture for gate (4).
3. Yes: the vocabulary rule (`rung`/`fallback`, no tier words) and the verbs-as-calls rule; the "decides alone" list is the spec's closed list.
4. Yes: each verb names its one command and acceptance; the gate commands' expected outputs are stated.
5. Degraded and said so: `unavailable:` for the harness tree; what is known is pasted from this repo (the symlink recipe, P13's shape, the spec sentence, the conflicts row).
6. No: the skill's text is checked by gate (2) for the words it must not contain.
7. n/a.
8. Yes (4/4) — the section carries the repo, the launch shape and the commit route.

## SD10 — the runbook
1. The command-count assertion with its mutant (a sentence where a command belongs).
2. n/a (docs).
3. Yes: "one command per step with its acceptance".
4. Yes: the runbook's sources (the Operator section), what it must not duplicate (SB5's `seat.md`).
5. Yes: `ls docs/runbooks`, SB5's touches, MAP's lack of a runbooks section.
6. No.
7. n/a.
8. Yes (4/4).

---

# Self-score (14 rubric rows; the reasons)

| # | criterion | score | reason |
|---|---|---|---|
| 1 | spec coverage | 3 | every Design item, test bullet, question, risk and not-in-spec item maps to a task or an `out:` in the map |
| 2 | correct facts | 3 | every fact carries its command (queries.log); two of my own wrong wordings were caught and fixed before shipping (argparse; `systemd-run -P`); three degraded inputs declared |
| 3 | self-contained sections | 2 | `factory-brief` reproduces every section whole; the two M-sized ports (SD1's bash validator, SD7's token scan) name the reference functions and the rule, not the code — a blind seat still has to write ~300 lines each from the named functions |
| 4 | TDD discipline | 3 | a red command with its expected output per task, green by check name, the commit body produced by a script |
| 5 | mutant per assertion; discriminating fixtures | 3 | one mutant per row in every table; the discriminating rows named per section |
| 6 | interfaces and error contracts | 3 | every producer, every enum arm, exit and stdout on each failure, which file each reader reads |
| 7 | rules, not enumerations | 3 | the ladder, the class, the spool's validity, the guard file and its parity oracle are rules; the deterministic guards are tasks |
| 8 | waves, touches, conflicts | 3 | waves from `check --draft` pasted; explicit `touches`; all 50 hits sequenced by cause |
| 9 | invariant awareness | 3 | §3.2/§3.3/§3.5 named where they bind; the one widening (the unit PATH) named, asserted and listed for the operator; no key in any expression |
| 10 | operator steps and rollback | 3 | seven steps, one command each with acceptance; the switch with its predicted delta and the rollback generation |
| 11 | anticipation | 3 | every A row with its trigger applied; the two A13 consumers named with their interpreters and trees; the A14 table |
| 12 | economy | 2 | 18.9k words for ten tasks — comparable to the house's typed plans per task, but the two guard tasks restate the family lists in prose |
| 13 | format and graph compliance | 3 | `check --draft` empty on the final draft; the dry run pasted; no typed heading under the plans glob |
| 14 | judgement calls | 3 | thirteen decisions with reason and alternative; three questions with recommendation and default and the row each answer moves |

Total: 40/42.
