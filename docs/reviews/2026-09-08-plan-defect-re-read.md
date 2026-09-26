# plan_defect re-read — the audit's plan→implementer rows, three readers each (2026-09-08)

## What this is

The 2026-09-08 label-consistency audit
(`docs/reviews/2026-09-08-plan-defect-audit.md`) classified every row of
`docs/ledger/plan-defects.toml` with the row's own label hidden. Sixteen rows
the ledger calls a **plan** class (`vacuous`, `missing-case`,
`underspecified`) came back `implementer`, every one of them carrying the same
rationale: *the plan named the requirement, the seat failed it*. Those sixteen
are re-read here, with **sb4 · SB2 as a control** (ledger `vacuous`,
classifier `vacuous`) — seventeen rows in all.

**The decisive question, per row:** did the plan section name the **mutant** —
a concrete one-line change the test must go red on — or only the
**requirement**? If the plan named the mutant and the seat still shipped a
test that does not kill it, or the seat violated a contract stated in the
section it was given, the class is `implementer`. If the plan named only the
requirement, or only a proof shape, the ledger's plan class stands, and which
plan class is the second question. This is the house rule filed 2026-09-07
(`1b8d126`; spec §3 Tests, rubric row 5 in both copies, Appendix A Q1, the
judge lens; concept `docs/concepts/2026-09-07a-a-named-proof-shape-is-not-a-mutant.md`):
**a named proof shape is not a mutant.**

**The precedent** is bk3 · B1b (`f86ccde`): the ledger said `vacuous`, an
independent classifier said `implementer`, three readers re-read it, the
ledger held and an `implementer` **secondary** was added. That shape — plan at
fault for the gate, the seat still culpable for something of its own — is what
a secondary records.

**The panel, per row:** three independent readers — **A** and **B**, two
Sonnet advocates each asked to steelman the classifier's `implementer` reading
before deciding, and **C**, an Opus decider. Each returns a plan quote, a
review quote, a primary (and optional secondary), a confidence, and the rule
it applied (`requirement-only` when the plan named the requirement without the
mutant; `other` otherwise).

**The convergence rule** (mechanical, applied to the votes; nothing here is
applied to the ledger by this file):

- **relabel-primary** — all three readers agree on a primary other than the
  ledger's;
- **add-secondary** — two or more readers name the same class the ledger's row
  lacks, and the row has no secondary;
- **hold-note-secondary** — the same, but the row already carries a secondary;
- **hold** — otherwise.

**No relabel is applied by this file.** The orchestrator applies the changes in
the "Ledger changes" section by a commit citing this file; nothing else changes.

## Results

| run · key | ledger | classifier | A | B | C | rule_applied (C) | outcome |
|---|---|---|---|---|---|---|---|
| cr8 · CR2 | missing-case | implementer (0.90) | missing-case +impl (0.62) | missing-case +impl (0.72) | missing-case +impl (0.85) | requirement-only | **add-secondary** `implementer` |
| cr15 · CR2r | missing-case (+implementer) | implementer (0.94) | missing-case +impl (0.78) | missing-case +impl (0.82) | missing-case +impl (0.87) | requirement-only | hold (secondary already filed) |
| ev1 · R5 | missing-case (+wrong-fact) | implementer (+wrong-fact) (0.99) | missing-case +wrong-fact (0.85) | missing-case +wrong-fact (0.72) | missing-case +wrong-fact (0.85) | requirement-only | hold |
| og1 · OG1 | missing-case | implementer (0.99) | missing-case (0.83) | missing-case (0.72) | missing-case +impl (0.82) | requirement-only | hold |
| og1 · OG1b | underspecified | implementer (0.98) | underspecified +impl (0.62) | underspecified +impl (0.68) | underspecified +impl (0.76) | requirement-only | **add-secondary** `implementer` |
| og3 · OG1r | underspecified | implementer (+missing-case) (0.99) | underspecified +impl (0.72) | underspecified +missing-case (0.85) | underspecified +impl (0.79) | requirement-only | **add-secondary** `implementer` |
| og4 · OG1r2 | missing-case | implementer (+missing-case) (0.99) | missing-case (0.78) | missing-case +impl (0.68) | missing-case +impl (0.72) | requirement-only | **add-secondary** `implementer` |
| rt1 · RT1 | vacuous | implementer (0.96) | vacuous +impl (0.75) | vacuous (0.85) | vacuous +impl (0.83) | requirement-only | **add-secondary** `implementer` |
| rt2c · RT2 | vacuous | implementer (+underspecified) (0.90) | vacuous +impl (0.78) | vacuous +underspecified (0.85) | vacuous +impl (0.86) | requirement-only | **add-secondary** `implementer` |
| rt5 · RT5 | missing-case | implementer (0.96) | missing-case (0.82) | missing-case (0.90) | missing-case +vacuous (0.86) | requirement-only | hold |
| rt5 · RT5b | underspecified | implementer (0.98) | underspecified (0.83) | underspecified (0.82) | underspecified +impl (0.82) | requirement-only | hold |
| sb5 · SB2b | missing-case | implementer (0.98) | missing-case (0.85) | missing-case (0.85) | **implementer** +missing-case (0.66) | other | hold |
| sc4 · G8b | underspecified | implementer (0.98) | underspecified +missing-case (0.85) | underspecified (0.85) | underspecified +impl (0.85) | requirement-only | hold |
| sc5 · G11 | missing-case | implementer (0.98) | missing-case +impl (0.72) | **implementer** +missing-case (0.72) | missing-case +impl (0.83) | requirement-only | **add-secondary** `implementer` |
| cr17 · CR2rb | missing-case | implementer (0.87) | missing-case +impl (0.78) | missing-case (0.78) | missing-case +impl (0.82) | requirement-only | **add-secondary** `implementer` |
| bk3 · B1b | vacuous (+implementer) | implementer (+wrong-fact) (0.99) | vacuous +impl (0.85) | vacuous +impl (0.90) | vacuous +impl (0.82) | requirement-only | hold (secondary already filed) |
| sb4 · SB2 *(control)* | vacuous | vacuous (0.96) | vacuous (0.90) | vacuous (0.95) | vacuous (0.93) | requirement-only | hold |

Tally: **0 relabels, 8 secondaries added, 9 holds.** 49 of the 51 reader
primaries match the ledger's primary; the two that do not (sc5 · G11 · B,
sb5 · SB2b · C) are each outvoted two to one on their own row.

---

## Row by row

### 1. cr8 · CR2 — ledger `missing-case` · classifier `implementer` (0.90)

Review: `docs/reviews/2026-09-05-opus-review-cr8-CR2.md`.
Classifier rationale: *"The plan prescribed protected-prefix handling. The implementer substituted an exact-file rule, losing ancestor semantics: `rm -rf .claude` and `git clean -fd` still ALLOW. The review explicitly identifies that substitution as the source of the hole."*

**Reader A (Sonnet, advocate)** — `missing-case` +`implementer`, conf 0.62, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-context-reset-ritual.md:42-44: "Add the destination path to the protected prefixes (Bash) and to the Edit/Write/MultiEdit path rule; §5's guard tests red first; OG1r's tests and killed mutants still hold." — and §5's own acceptance bar, docs/superpowers/specs/2026-09-05-context-reset-ritual-design.md:299-300: "guard (`91-orchestrator-guard.bats`, on OG1r): DENY `touch`, `echo x >`, `rm` and the Write tool on `.claude/ritual-override`; ALLOW `cat` of it."
- *Review:* docs/reviews/2026-09-05-opus-review-cr8-CR2.md:344-345: "The plan rule solves this with a second flag `dir_ancestor_seen` fed by `is_plans_dir_or_ancestor` (`:389-400`, `:471`, `:481`); the override rule has no equivalent arm." (MAJOR-1, line 330)
- *Reasoning:* The strongest implementer case: plan/spec §3.4 says the destination "gains" OG1r's existing protected-prefix rule rather than a new mechanism, and review MAJOR-1 shows the implementer built a separate exact-file-match `override_verdict` instead of reusing the ancestor-aware plan rule, which the review calls the "source of the hole." But this is weaker than it looks: the review itself calls the substitution "defensible" (PROTECTED is a fixed absolute-host-path array pinned to another test, so the literal instruction was impossible to satisfy as written), and — decisively — spec §5's actual testing contract for CR2 enumerates only four exact-file spellings (touch/echo/rm/Write) plus one ALLOW case, with zero mention of ancestor/directory-level deletion (`rm -rf .claude`, `git clean -fd`). No CR2 mutation anywhere in the plan or spec names the directory-level case either explicitly or as a mutant. The plan never even named this as a requirement, let alone a mutant, so the seat's test suite (which matches §5 exactly) cannot be faulted for not killing an unrequested case. That is missing-case, not implementer — though the "reuse the existing rule" instruction is real enough to warrant a secondary implementer flag.

**Reader B (Sonnet, advocate)** — `missing-case` +`implementer`, conf 0.72, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-context-reset-ritual.md:42-43 — "Add the destination path to the protected prefixes (Bash) and to the Edit/Write/MultiEdit path rule; §5's guard tests red first; OG1r's tests and killed mutants still hold."
- *Review:* docs/reviews/2026-09-05-opus-review-cr8-CR2.md:275-279 — "The implementer did not touch PROTECTED (:75-82, still the six absolute host prefixes) and wrote a separate override_verdict rule instead. That is defensible — PROTECTED is kept byte-identical to hook-guard.py and lane-submit by tests/lane/test_forbidden_lists_agree.py (see the comment at :73-74), so a project-relative path could not go there. But the substitution is what lost the prefix/ancestor semantics that rm -rf .claude needs." — and :45, on MAJOR-1: "The plan rule solves this with a second flag dir_ancestor_seen fed by is_plans_dir_or_ancestor (:389-400, :471, :481); the override rule has no equivalent arm."
- *Reasoning:* CR2's whole technical content is one sentence naming a mechanism ("protected prefixes") that the review itself shows was structurally unusable for a project-relative path (pinned byte-identical to hook-guard.py by a cross-file test) — and calls the implementer's substitution "defensible," not a finding. No Interfaces/Tests subsection names any mutant, fixture, or even the ancestor/directory case; the section never says "rm -rf .claude", "git clean", or "ancestor" at all. The review's own root-cause framing borrows the plan-rule analogy (is_plans_dir_or_ancestor) to show the override rule lacks an arm nothing in this plan ever asked for — a case never named, not a named mutant an implementer failed to satisfy. The classifier's "substitution" story reads "protected prefixes" as if it self-evidently demanded ancestor semantics, but the review shows that specific mechanism was off-limits, making the deviation forced rather than a plan-mutant violation. Secondary implementer reflects MAJOR-3, a genuinely dead `dd` arm unrelated to any plan gap.

**Reader C (Opus, decider)** — `missing-case` +`implementer`, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-context-reset-ritual.md:42-44 — "Add the destination path to the protected prefixes (Bash) and to the / Edit/Write/MultiEdit path rule; §5's guard tests red first; OG1r's tests and / killed mutants still hold." (the referenced §5 list, spec line 300, is: "guard (`91-orchestrator-guard.bats`, on OG1r): DENY `touch`, `echo x >`, `rm` and the Write tool on `.claude/ritual-override`; ALLOW `cat` of it." — no mutation clause, unlike its neighbouring bullets)
- *Review:* docs/reviews/2026-09-05-opus-review-cr8-CR2.md:276-280 — "One deviation from the plan's literal wording worth recording, not a finding: the plan says \"add the destination path to the protected prefixes (Bash)\". The implementer did **not** touch `PROTECTED` (`:75-82`, still the six absolute host prefixes) and wrote a separate `override_verdict` rule instead. That is defensible — `PROTECTED` is kept byte-identical to `hook-guard.py` and lane-submit by `tests/lane/test_forbidden_lists_agree.py` (see the comment at `:73-74`), so a project-relative path could not go there. But the substitution is what lost the prefix/ancestor semantics that `rm -rf .claude` needs."
- *Reasoning:* Decisive question: the plan named a requirement ("protected prefixes") and a five-row proof shape; it named no mutant — §5's guard bullet is the only one in the list with no "(mutation: …)" clause, and no directory/ancestor, glob, git-clean, dd or python-removal spelling is named anywhere. The reviewer explicitly rules the PROTECTED substitution "not a finding" and defensible, since a lane test pins PROTECTED byte-identical, making the plan's literal instruction infeasible. Ledger holds. Secondary implementer: the seat shipped a second commit outside touches where the plan gives one, and a dead dd arm.

**Outcome — add-secondary `implementer`.** All three readers hold the ledger's
`missing-case` and all three name `implementer` as the secondary the row lacks.

### 2. cr15 · CR2r — ledger `missing-case` (+`implementer`) · classifier `implementer` (0.94)

Review: `docs/reviews/2026-09-05-opus-review-cr15-CR2r.md`.
Classifier rationale: *"MAJOR-2 violates the explicit contract requiring force detection with or without -d/-x; MAJOR-4 allows cpio in .claude despite a required DENY matrix row. These are implementation deviations from specified behavior."*

**Reader A** — `missing-case` +`implementer`, conf 0.78, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-context-reset-ritual.md:172-173: "4. ... git clean denies only with -f (with or without -d/-x) and no path or a path naming a protected dir/ancestor ... 3. The delete family gains git stash with -u/--include-untracked/-a, tar/unzip/cpio extracting into a protected directory (-C <protected> or an output path under it), ..." — neither item 3 nor item 4 carries a "(mutation: ... → ... fails)" clause, unlike items 1, 2, 5 and 6 in the same contract, which all do.
- *Review:* docs/reviews/2026-09-05-opus-review-cr15-CR2r.md:462-467 (MAJOR-2): "The plan's contract item 4 is explicit: '`git clean` denies only with `-f` (**with or without `-d`/`-x`**)'. `-df` is `-f` with `-d`; the guard reads the cluster positionally instead of by character." And line 516-531 (MAJOR-4): "`cpio -idm` extracts into the current directory and names no path at all... Fix: when an extract verb is present and no `-C`/`-d` destination is given, judge the *bases* themselves against the protected dirs" — i.e. a case the contract text never described.
- *Reasoning:* Per the house rule (design doc lines 284-305, 391: "the section names the mutant ... or the item is decoration"), items 3 and 4 name only requirements, no mutant — unlike items 1/2/5/6 in the same section, which all carry explicit "(mutation: ...)" clauses. CR2rb's re-plan then adds exactly the missing mutants (cluster-anchoring mutant, cwd-check-removed mutant) that CR2r lacked — direct proof the mutant was absent, not violated. MAJOR-4's cwd-as-destination scenario isn't even in CR2r's requirement text, a clean missing-case; MAJOR-2/3 are requirement-named-mutant-absent, borderline but the same side of the line. MAJOR-1 (item 5, which does have a mutation clause) is the implementer-leaning piece: the named mutant (exemption removed) differs from the actual defect (exemption over-extends across a newline), so it's not a clean implementer hit either — supports the secondary rather than flipping primary.

**Reader B** — `missing-case` +`implementer`, conf 0.82, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-context-reset-ritual.md:172 — "4. The pathless git over-denials are narrowed: `git clean` denies only with `-f` (with or without `-d`/`-x`) and no path or a path naming a protected dir/ancestor — ..." (no "mutation:" clause, unlike items 1/2/5/6); and line 171 (item 3): "tar/unzip/cpio extracting into a protected directory (`-C <protected>` or an output path under it)" — never covers an implicit-cwd destination, and no mutation clause either. Step 1's own test enumeration at line 177 lists only "`git clean -n` allow, `git clean -f` deny" and "`tar -C .claude -xf x.tar`" — never a compound-flag clean case or a no-flag/cwd-implicit extract case.
- *Review:* docs/reviews/2026-09-05-opus-review-cr15-CR2r.md:462 — "The plan's contract item 4 is explicit: \"`git clean` denies only with `-f` (**with or without `-d`/`-x`**)\". `-df` is `-f` with `-d`; the guard reads the cluster positionally instead of by character." And line 504-524 (MAJOR-4): "`tools/orchestrator-guard.sh:730-737` denies `tar`/`unzip`/`cpio` only when a **token** names the protected directory ... `cpio -idm` extracts into the current directory and names no path at all" — the ALLOW/DENY table at lines 126-138 showing the cwd-implicit cases is the *review's own* matrix, not a table the plan itself specified.
- *Reasoning:* Item 4 states the -d/-x requirement in prose but names no mutant and Step 1 never lists a compound-flag test — exactly the pattern the house rule calls missing-case. Item 3 for MAJOR-4 is narrower still: it only covers -C/output-path extraction; "cwd already inside .claude, no destination flag" is a case the contract never names at all, and the classifier's "required DENY matrix row" is the review's own table, not the plan's. Both majors are requirement-named/mutant-unnamed, matching the design doc's own pre-existing tag "missing-case (+impl)" for this row. Design doc's Appendix B (line 883) independently corroborates missing-case+implementer from before the house rule existed, for MAJOR-1 (the newline case) — same shape: prose requirement, no boundary/mutant pinned.

**Reader C** — `missing-case` +`implementer`, conf 0.87, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-context-reset-ritual.md:173 — "5. `git commit -m \"<text>\"` and `-F <file>`: the quoted message after `-m` is not scanned for verbs or paths (a commit message is prose; the deny-only over-denial on it is withdrawn) — mutation: the exemption removed → a test with a message naming `.claude` and a delete word fails; `-F` unaffected." (Step 1, :177, asks only for "the `-m` prose case allow"; the narrowed-git list names "`git clean -n` allow, `git clean -f` deny", never `-df`/`-xdf`; :171 defines extracts as "`-C <protected>` or an output path under it".)
- *Review:* docs/reviews/2026-09-05-opus-review-cr15-CR2r.md:381 — "### MAJOR-1 — the `git commit -m` exemption swallows every following line; a plans-dir regression"; and :430 "The commit body's claim that \"a `git commit -m` message is prose and is no longer scanned\" is true; what is not true is that the scan resumes after the message."
- *Reasoning:* Decisive question: the plan named requirements and one reverse mutant ("the exemption removed"), never the terminator mutant — no newline case, no `-df`/`push -u` spelling, and its extract clause defines the case as `-C`/output path, excluding a cwd-based extract. The seat satisfied every named mutant and enumerated spelling. MAJOR-1, the serious one and a plans regression, is unnamed ground. Implementer secondary stands: "with or without `-d`/`-x`" was explicit, plus MINOR-6's hard-coded path and MINOR-8's malformed result block.

**Outcome — hold.** The ledger's `missing-case` holds; the `implementer`
secondary all three readers name is already on the row.

### 3. ev1 · R5 — ledger `missing-case` (+`wrong-fact`) · classifier `implementer` (+`wrong-fact`) (0.99)

Review: `docs/reviews/2026-09-05-opus-review-ev1-R5.md`.
Classifier rationale: *"The sole major is the omitted Flash price row, which Step 3 explicitly required. The implementer deviated from an adequate requirement. Separately, the plan dictated the false claim that the driver only honours inherited XDG_CACHE_HOME."*

**Reader A** — `missing-case` +`wrong-fact`, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-evidence-store.md:2234: "`docs/ledger/openrouter-prices.csv`: header plus two dated rows for DeepSeek V4 Pro and Flash carrying the figures the two documents disagreed on, each with its source date (`2026-09-03,deepseek/deepseek-v4-pro-0813,1.02,2.05,` from lanes.md and `2026-09-04,deepseek/deepseek-v4-pro-0813,0.55,2.19,` from the seat README — both kept, dated, so the ledger's date join picks the right one...)." Step 4's test (line 2237): "add a one-line test that `docs/ledger/openrouter-prices.csv` loads through the existing price-table reader" — no per-model assertion named.
- *Review:* docs/reviews/2026-09-05-opus-review-ev1-R5.md, Findings/major: "**Fix:** Add the dated Flash row... and extend test_openrouter_prices_csv_loads_through_price_reader in tests/ledger/test_factory.py to assert it loads, so the fact is pinned the way the Pro rows are"
- *Reasoning:* Step 3 names Flash as a requirement but only gives literal content for the two conflicting Pro rows; Step 4's acceptance test is a generic "loads through the reader" check with no assertion pinning any model row. Git history confirms the shipped test lacked a Flash assertion until fix round R5b (7f08857). Instruction present, mutant absent — plan fault per the house rule, matching the ledger's missing-case. The XDG_CACHE_HOME secondary is independently confirmed plan-dictated wrong-fact.

**Reader B** — `missing-case` +`wrong-fact`, conf 0.72, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-evidence-store.md:2234 — "`docs/ledger/openrouter-prices.csv`: header plus two dated rows for DeepSeek V4 Pro and Flash carrying the figures the two documents disagreed on, each with its source date (`2026-09-03,deepseek/deepseek-v4-pro-0813,1.02,2.05,` from lanes.md and `2026-09-04,deepseek/deepseek-v4-pro-0813,0.55,2.19,` from the seat README — both kept, dated, so the ledger's date join picks the right one …)"
- *Review:* docs/reviews/2026-09-05-opus-review-ev1-R5.md:36 — "The plan's Step 3 CSV bullet says \"header plus two dated rows for DeepSeek V4 Pro and Flash\". … A doc-truth task that deletes a fact without rehoming it is the defect this task exists to remove. **Fix:** Add the dated Flash row … and extend test_openrouter_prices_csv_loads_through_price_reader … to assert it loads, so the fact is pinned the way the Pro rows are."
- *Reasoning:* The plan's summary word "Flash" is not backed by a mutant: its only literal, backtick-quoted content is two Pro rows (the pair the two docs disagreed on), and Step 4's acceptance test only asserts the CSV "loads through the reader" — a proof shape no removed/absent row could ever turn red. Opus's own fix is "extend the test … so the fact is pinned," i.e. the plan built no mutant for Flash's presence. Requirement named, case never instantiated or tested → plan fault, not deviation from an adequate spec. Secondary wrong-fact matches both readers' XDG_CACHE_HOME finding.

**Reader C** — `missing-case` +`wrong-fact`, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-evidence-store.md:2234 — "- `docs/ledger/openrouter-prices.csv`: header plus two dated rows for DeepSeek V4 Pro and Flash carrying the figures the two documents disagreed on, each with its source date (`2026-09-03,deepseek/deepseek-v4-pro-0813,1.02,2.05,` from lanes.md and `2026-09-04,deepseek/deepseek-v4-pro-0813,0.55,2.19,` from the seat README — both kept, dated, so the ledger's date join picks the right one; a comment line is not allowed in CSV, so the provenance goes in `tools/ledger/schema.md` one sentence)." — and :2237 "add a one-line test that `docs/ledger/openrouter-prices.csv` loads through the existing price-table reader"
- *Review:* docs/reviews/2026-09-05-opus-review-ev1-R5.md:36 — "**major** `docs/ledger/openrouter-prices.csv` — The \"one price table\" has no DeepSeek Flash row, while the same commit deleted the only Flash rate the repo held. … The plan's Step 3 CSV bullet says \"header plus two dated rows for DeepSeek V4 Pro and Flash\"."
- *Reasoning:* Step 3's prose says Pro and Flash, but both literal rows it dictates are pro-0813 — no Flash figure, no source line, no mutant. Step 4 names only a proof shape ("loads through the price-table reader"), which no missing-row mutant can turn red. Requirement named, mutant not: the plan class stands. Missing-case (a deleted fact's rehoming never named as a case) + wrong-fact (the dictated untrue XDG_CACHE_HOME sentence). Appendix B:885 agrees; the seat's undeclared schema.md edit is a third-order implementer minor the plan's own touches line caused.

**Outcome — hold.** Unanimous for the ledger's primary and its filed secondary;
no reader names `implementer` at all.

### 4. og1 · OG1 — ledger `missing-case` · classifier `implementer` (0.99)

Review: `docs/reviews/2026-09-05-opus-review-og1-OG1.md`.
Classifier rationale: *"The review explicitly says all MAJOR bypasses were named in the task brief. The implementation omitted path normalization supplied by the referenced guard and allowed git global-option spellings; its tests exercised none of these required cases."*

**Reader A** — `missing-case`, no secondary, conf 0.83, rule `requirement-only`.

- *Plan:* "Edit/Write/MultiEdit on `docs/superpowers/plans/*.md`: compute the set of typed headings (`^### KEY (kind, size) — title$` lines) before and after; if any existing typed heading is removed or altered → deny: `typed task headings are append-only — withdraw a task with a status row in docs/ledger/task-status.toml, not by editing docs/superpowers/plans/…`." — docs/superpowers/plans/2026-09-05-seat-routing.md:281 (git rule, same section, line 282: "Also `git commit --amend`, `git push`, `git rebase`, `git reset --hard` on this checkout → deny (history rules of the house).")
- *Review:* "The plan's interface spec says the heading rule applies to \"`Edit/Write/MultiEdit` on `docs/superpowers/plans/*.md`\". A path-text comparison does not implement that predicate; the plan also pointed the implementer at `hook-guard.py`, which contains the resolution code. MAJOR 1." — docs/reviews/2026-09-05-opus-review-og1-OG1.md:222-225
- *Reasoning:* Strongest case for implementer: the review itself says both bypasses were "named in the task brief" and that the plan "pointed the implementer at hook-guard.py, which contains the resolution code" — a stated reference the seat ignored. But checking OG1's own section (lines 272-291), the only hook-guard.py reference (line 282) is scoped to Bash-rule *wording* (sudo/nixos-rebuild/protected paths), not to path-canonicalization for the heading rule or to git's tokenization — no `.., ./, symlink`, or `-c/-C` mutant is named anywhere. The plan states a glob predicate and an unconditional git-subcommand ban — requirements, not falsifiers — and its own Step-1 test list (line 286) omits every bypass shape later found. The spec's own Appendix B entry for this exact row confirms: "missing-case … name the reference function to port, not the file to read" — the plan named a file generically, not the specific mutant/function. The reviewer's "named in advance" is rhetorical emphasis on intent/scope, not textual naming of the mutant — exactly the conflation the house rule targets. Ledger stands.

**Reader B** — `missing-case`, no secondary, conf 0.72, rule `requirement-only`.

- *Plan:* "docs/superpowers/plans/2026-09-05-seat-routing.md:286 — [ ] **Step 1: Failing tests** (bats, feeding JSON payloads to the guard): removing a typed heading → deny; rewriting one → deny; appending a new section → allow; editing body text under a heading → allow; a Bash `sudo nixos-rebuild switch` → deny; `git commit --amend` → deny; `git status` → allow; malformed JSON → allow with a stderr warning."
- *Review:* "docs/reviews/2026-09-05-opus-review-og1-OG1.md:15 — It is rejected on **three MAJOR bypasses**, all of which the task brief named in advance and none of which the bats file exercises: a plan-heading edit escapes the guard entirely if the path carries a `..` or `./` segment or is a symlink into the plans directory, and `git -c … commit --amend` (and `git -C … push`) escapes the history rules."
- *Reasoning:* OG1's Interfaces bullets state the behaviors ("deny on docs/superpowers/plans/*.md"; "git commit --amend/push/rebase/reset --hard … deny") but never name the bypass shapes (non-canonical path, symlink, git -c/-C global options) as required cases; Step 1's test list enumerates only literal-form cases. The review's "task brief named it in advance" is an overstatement — the OG1 section text (lines 278-286) contains no mention of realpath/normpath/symlink/global-option tokenization; that language first appears in OG1b, written after this rejection. hook-guard.py is cited only for Bash-rule wording, not for the Edit/Write path predicate. Plan named the requirement, not the mutant.

**Reader C** — `missing-case` +`implementer`, conf 0.82, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:286 — "- [ ] **Step 1: Failing tests** (bats, feeding JSON payloads to the guard): removing a typed heading → deny; rewriting one → deny; appending a new section → allow; editing body text under a heading → allow; a Bash `sudo nixos-rebuild switch` → deny; `git commit --amend` → deny; `git status` → allow; malformed JSON → allow with a stderr warning. Wall time per call < 300 ms (measure; state the interpreter chosen)." (with :281 "Edit/Write/MultiEdit on `docs/superpowers/plans/*.md`" and :282 "Also `git commit --amend`, `git push`, `git rebase`, `git reset --hard` on this checkout → deny")
- *Review:* docs/reviews/2026-09-05-opus-review-og1-OG1.md:222-225 — "- The plan's interface spec says the heading rule applies to \"`Edit/Write/MultiEdit` on `docs/superpowers/plans/*.md`\". A path-text comparison does not implement that predicate; the plan also pointed the implementer at `hook-guard.py`, which contains the resolution code. MAJOR 1."
- *Reasoning:* Decisive question: the plan named only requirements — a `plans/*.md` predicate, a git-verb list — and an enumerated Step 1 case list holding neither `..`/`./`/symlink paths nor `git -c`/`-C` spellings; no mutation table, and hook-guard.py is cited for wording, not `_resolve`. Requirement-only, so the plan class holds; omitted cases make it missing-case (Appendix B: "name the reference function to port, not the file to read"). The classifier's "task brief named in advance" is the gate brief (OG1b:297), not the plan. Implementer secondary: MINOR 3 changed hook-guard.py's `sudo` anchors the plan told it to reuse.

**Outcome — hold.** All three hold `missing-case`; only one reader names an
`implementer` secondary, below the two-reader bar.

### 5. og1 · OG1b — ledger `underspecified` · classifier `implementer` (0.98)

Review: `docs/reviews/2026-09-05-opus-review-og1-OG1b.md`.
Classifier rationale: *"OG1b step 1(b) explicitly required `--work-tree=…` support. The implementation omitted it, allowing a verified `git --work-tree=. commit --amend` bypass—the review's expressly unaccepted MAJOR deviation."*

**Reader A** — `underspecified` +`implementer`, conf 0.62, rule `requirement-only`.

- *Plan:* Pattern: `git` followed by any number of `-c k=v`, `-C path`, `--no-pager`, `--git-dir=…`, `--work-tree=…` tokens, then the subcommand. (docs/superpowers/plans/2026-09-05-seat-routing.md:301)
- *Review:* The plan's OG1b step 1(b) spells the git pattern with `--work-tree=…` in it. The implementation omits it, and the omission is a working `--amend` bypass. MAJOR. (docs/reviews/2026-09-05-opus-review-og1-OG1b.md:254-255)
- *Reasoning:* The plan named one literal token (`--work-tree=…`) but its own required-test list (step 1b) never tested it, and the plan named zero of the other six verified bypasses (-P, --literal-pathspecs, --exec-path=, --no-replace-objects, --namespace=, --icase-pathspecs) that made the enumeration fail regardless. The review's own remedy — "stop specifying the git rule as a flag enumeration, that is what failed twice" — re-plans the approach itself (OG1r: tokeniser), diagnosing an incomplete proof shape, not a mechanical omission a faithful implementer could have fully cured. This mirrors the bk3/B1b precedent: ledger class stands, implementer added as secondary for the one token that was in fact named and dropped.

**Reader B** — `underspecified` +`implementer`, conf 0.68, rule `other`.

- *Plan:* Pattern: `git` followed by any number of `-c k=v`, `-C path`, `--no-pager`, `--git-dir=…`, `--work-tree=…` tokens, then the subcommand. (docs/superpowers/plans/2026-09-05-seat-routing.md:301)
- *Review:* The plan's OG1b step 1(b) spells the git pattern with `--work-tree=…` in it. The implementation omits it, and the omission is a working `--amend`. MAJOR. (docs/reviews/2026-09-05-opus-review-og1-OG1b.md:254-255); and separately: "Stop specifying the git rule as a flag enumeration — that is what failed twice." (same file, "The design change for the re-plan")
- *Reasoning:* Not a test-vacuity case: the plan's Step 1(b) test list never exercised `--work-tree=`/`--git-dir=` at all, and the "Pattern" line is a prose enumeration, not a mutant. The review's own fix — replace enumeration with a tokeniser — and Appendix B's contemporaneous note ("a rule…never a flag list") both diagnose an open-ended contract, matching og3·OG1r's identical repeat failure. But the review's "Not accepted" section singles out `--work-tree=` as an explicitly spelled, dropped token — a genuine narrow deviation, not just design incompleteness — earning an implementer secondary, as with bk3·B1b.

**Reader C** — `underspecified` +`implementer`, conf 0.76, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:301 — "(b) MAJOR 2: `git -c core.editor=true commit --amend`, `git -C /home/x push`, `git --no-pager rebase -i`, `git -c a=b -C . reset --hard` → DENIED; `git -c a=b status`, `git -C . log` → allowed. Pattern: `git` followed by any number of `-c k=v`, `-C path`, `--no-pager`, `--git-dir=…`, `--work-tree=…` tokens, then the subcommand."
- *Review:* line 179-181 — "An enumeration will keep leaking; git ships more global options than a regex will ever carry, and a guard that is *for* banning `--amend` must not be defeated by `-P`." (and line 254-256: "The plan's OG1b step 1(b) spells the git pattern with `--work-tree=…` in it. The implementation omits it, and the omission is a working `--amend`. MAJOR.")
- *Reasoning:* The plan prescribed a closed flag enumeration for an open requirement ("no surviving --amend bypass"). Its four named deny cases contain no --work-tree probe, so no named mutant dies on the omission; and exact compliance would still have allowed -P, --literal-pathspecs, --exec-path=, --no-replace-objects — MAJORs anyway. Contract shape, not mutant: plan class holds. The seat did drop an expressly spelled token, so implementer secondary is warranted.

**Outcome — add-secondary `implementer`.** All three hold `underspecified` and
all three name the `implementer` secondary the row lacks.

### 6. og3 · OG1r — ledger `underspecified` · classifier `implementer` (+`missing-case`) (0.99)

Review: `docs/reviews/2026-09-05-opus-review-og3-OG1r.md`.
Classifier rationale: *"The Deviations section explicitly says the plan required newline boundaries and any write-capable verb with a plan path; implementation violated both. Separately, MINOR 13 attributes omitted ordinary writers to the plan's enumerated verb list."*

**Reader A** — `underspecified` +`implementer`, conf 0.72, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:331 — "Find every `git` WORD: at a command boundary (start, `;`, `&&`, `||`, `|`, `(`, newline), after `env`, `command`, `\`, or `VAR=value` prefixes, or as the basename of a path token ending in `/git`."
- *Review:* MAJOR 13 (docs/reviews/2026-09-05-opus-review-og3-OG1r.md): "only `env`, `command` and a `VAR=value`-shaped token keep `cmd_pos=1`... Verified ALLOWED: **`nix develop -c git commit --amend`**... `nix develop -c …` is the house prefix CLAUDE.md prescribes for *everything*... so the guard is defeated by the repo's own documented invocation style with zero intent to evade."
- *Reasoning:* The strongest case for implementer: design change 1 literally names "newline" as a boundary token and design change 2 says "Any" write-capable verb, yet the shipped code omits both. But MAJOR 13 — the larger, house-relevant defect (nix develop -c bypassing everything) — traces exactly to the plan's own enumerated transparent-prefix list (env, command, \, VAR=value); the implementer built precisely that list and nothing more. Appendix B (spec:900) independently calls OG1r "underspecified... no enumerated boundary set, no enumerated launcher set" — the fix is a plan-level rule change, not an implementer fix. The mutation table's four plan-named mutants all die (implementer met every mutant the plan named), and the review itself concedes MINOR 13 "is not a deviation" because "the plan enumerated the verbs." The newline clause is text in the design paragraph but Step 1's red list never contains a genuine bare-newline two-command test (only backslash-continuation) — a named requirement without a named mutant, the house rule's own definition of a plan gap. Design change 2's implicit "command position" restriction is a mild implementer-added narrowing beyond the plan's unconditional "Any," supporting a secondary implementer tag, but the dominant, spec-endorsed reading (Appendix B) is underspecified.

**Reader B** — `underspecified` +`missing-case`, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:331 — "Find every `git` WORD: at a command boundary (start, `;`, `&&`, `||`, `|`, `(`, newline), after `env`, `command`, `\`, or `VAR=value` prefixes, or as the basename of a path token ending in `/git`."
- *Review:* docs/reviews/2026-09-05-opus-review-og3-OG1r.md:308-311 — "The plan's design change 1 says ... The newline is in the spec and absent from the implementation ... Design change 2 says '**Any** Bash command whose normalised text contains a path ...' The implementation restricts the verb to command position and then loses command position after any launcher, so `nix develop -c rm <plan>` deletes a plan. MAJOR."
- *Reasoning:* The plan named requirements (newline as a boundary char; a fixed transparent-prefix list; an enumerated verb list) but never named the killing mutants: Step 4's mutation list has only two entries (value-skip, path-rule-removed), none for dropping newline or a launcher prefix. Appendix B's own row (design-doc line ~900) says the fault is "no enumerated boundary set, no enumerated launcher set" — an incomplete plan enumeration, not an implementer deviation. MINOR 13 is explicitly "not a deviation": the plan enumerated the verbs and simply left ordinary writers out. Design change 2's "any... together with" reads as position-agnostic, so the implementer's command-position walker is a plausible but debatable overreach — the only piece pulling toward implementer — which is why confidence isn't higher.

**Reader C** — `underspecified` +`implementer`, conf 0.79, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:331 — "Find every `git` WORD: at a command boundary (start, `;`, `&&`, `||`, `|`, `(`, newline), after `env`, `command`, `\`, or `VAR=value` prefixes, or as the basename of a path token ending in `/git`." (Step 4 mutations, line 336: "mutations: tokeniser skips no values (`-c a=b commit` misread → must fail a test); path rule removed → fails." — no boundary or launcher mutant named.)
- *Review:* line 215 — "**MAJOR 13 — the walk stops at the first non-transparent word, so any launcher prefix hides everything after it.**"; line 232 — "Both MAJORs share one root, and it is the root OG1 and OG1b were rejected for: **an enumeration standing in for a rule.**"
- *Reasoning:* Decisive finding MAJOR 13: the transparent-prefix set is the plan's own enumeration (`env`, `command`, `\`, `VAR=`), which omits `nix develop -c`, `timeout`, `nohup`, `xargs`. The seat implemented that list faithfully; the plan named no launcher or boundary mutant (only value-skipping and path-rule-off, both killed). Contract left open ⇒ underspecified, matching Appendix B's "no enumerated boundary set, no enumerated launcher set". Implementer secondary: the plan did enumerate newline and the seat dropped it (MAJOR 12).

**Outcome — add-secondary `implementer`.** All three hold `underspecified`; two
(A, C) name `implementer` as the secondary.

### 7. og4 · OG1r2 — ledger `missing-case` · classifier `implementer` (+`missing-case`) (0.99)

Review: `docs/reviews/2026-09-05-opus-review-og4-OG1r2.md`.
Classifier rationale: *"MAJOR 14 explicitly says the plan's unconditional `mv` contract was not followed; MAJOR 18 violates its stated timing budget. MINOR 18 separately identifies write verbs omitted by the plan, supporting a missing-case secondary."*

**Reader A** — `missing-case`, no secondary, conf 0.78, rule `requirement-only`.

- *Plan:* "(b) any WRITE VERB token anywhere (`sed` with `-i*`, `rm`, `mv`, `cp`, `tee`, `truncate`, `install`, `dd`, `ed`, `ln`, ...) in a command that ALSO names a realpath-normalised plan path → deny; read verbs never deny." — docs/superpowers/plans/2026-09-05-seat-routing.md:370 (OG1r2's Contract). Required tests (line 372, "all OG1r deny/allow cases plus...") add `cp k <plan> && echo done`, `install -m644 k <plan>`, `dd of=<plan>`, `ln -sf k <plan>` — all plan-path-as-destination cases — and carry OG1r's `mv a docs/superpowers/plans/x.md` (also destination-only, plans/2026-09-05-seat-routing.md:335). No required test anywhere in the OG1→OG1b→OG1r→OG1r2 chain names `mv <plan> <elsewhere>` (plan-path-as-source).
- *Review:* "`mv <plan> y` (a bare destination with no `/`) denies, because the destination search only accepts `*/*` tokens and so falls back to the plan itself. The plan's contract is explicit and was not followed: 'any WRITE VERB token anywhere (`sed` with `-i*`, `rm`, `mv`, `cp`, …) in a command that ALSO names a realpath-normalised plan path → deny'." — docs/reviews/2026-09-05-opus-review-og4-OG1r2.md:230-232 (MAJOR 14)
- *Reasoning:* The best case for implementer is real: the contract prose is unconditional and the review calls it "explicit." But the decisive test is what the plan actually PINNED with a required test, not what its prose implied. Across OG1→OG1r2 every required mv/cp/install/dd/ln case is destination-only; a source-side plan-path case (`mv <plan> elsewhere`) was never named anywhere in the test lists, so no shipped test could have failed on this specific gap — it's an absent case, not a killable-but-unkilled one. Appendix B's own entry for this row ("destinations as well as sources...") and MINOR 18's explicit "the plan enumerates the verbs, so this is not a deviation" both read the same way: plan gap, not seat deviation. MAJOR 18's budget miss is the same pattern — Step 4 asked to "measure" wall time but never named the 200-path-token adversarial case; the shipped timing test used a short command and passed vacuously for a reason the plan, not the seat, created ("cost the design before stating a latency"). Ledger's missing-case, unchanged.

**Reader B** — `missing-case` +`implementer`, conf 0.68, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:370 — "(b) any WRITE VERB token anywhere (`sed` with `-i*`, `rm`, `mv`, `cp`, `tee`, `truncate`, `install`, `dd`, `ed`, `ln`, `perl`/`python*`/`python3 -`/`nix develop … -c python3` with `write_text|open\(.*[\"']w|>`, `>`/`>>` redirects, `git checkout --`, `git restore`) in a command that ALSO names a realpath-normalised plan path → deny; read verbs never deny."
- *Review:* docs/reviews/2026-09-05-opus-review-og4-OG1r2.md:237-245 — "MAJOR 15 — the plans *directory* is never recognised, so directory-level destruction is allowed. `plan_seen` is set only when a token realpath-resolves to a `*.md` file directly under the plans dir, or when the raw text contains the literal `superpowers/plans/` with its trailing slash. So the trailing slash decides the verdict: `rm -r docs/superpowers/plans/` denies, `rm -r docs/superpowers/plans` — every plan in the repo — is ALLOWED."
- *Reasoning:* The row's dominant findings (MAJOR15 directory/ancestor, MAJOR16 cwd rebasing, MINOR18 verb-list gaps — the last the review itself calls "not a deviation") were never named by the plan in any form, general or specific: the contract speaks only of "a realpath-normalised plan path" (a file), never a directory, never `cd`/cwd. That's requirement-absent, not a named-but-unpinned mutant — squarely missing-case, matching the ledger and Appendix B's own gloss ("destinations as well as sources; the directory itself; honour cwd"). MAJOR14 is the classifier's strongest card: the plan's clause is unqualified for `mv` ("any WRITE VERB token anywhere … in a command that ALSO names … a plan path → deny," no direction caveat, unlike the earlier draft's explicit "cp (as destination)"), and the review frames it as a violated contract, not an absent one — genuinely closer to named-mutant. MAJOR17 (`sed -i` anywhere) is similar: OG1r2's whole premise is "no command position," so scanning only the token after `sed` contradicts the plan's own stated method. These two support an implementer secondary, as does MINOR18's own text, but they don't outweigh the several majors that name nothing at all. Net: missing-case stands as primary, implementer as secondary — the B1b pattern (ledger class holds, implementer added) applies here too, just with primary/secondary reversed from the classifier's call.

**Reader C** — `missing-case` +`implementer`, conf 0.72, rule `requirement-only`.

- *Plan:* "(b) any WRITE VERB token anywhere (`sed` with `-i*`, `rm`, `mv`, `cp`, `tee`, `truncate`, `install`, `dd`, `ed`, `ln`, … `>`/`>>` redirects, `git checkout --`, `git restore`) in a command that ALSO names a realpath-normalised plan path → deny; read verbs never deny." — docs/superpowers/plans/2026-09-05-seat-routing.md:370; its Step 4 mutation list is "drop `\n` from the separator set → fails; skip tokens after a launcher → fails; basename rule off → fails; plan-path write rule off → fails" (same file:372), and Step 1's deny table names no `mv <plan> …`, no plans-directory, no `cd`, no `sed -e … -i` case.
- *Review:* "The contract says a command that \"ALSO names a realpath-normalised plan path\" denies. `rm -r docs/superpowers/plans` names the plans by naming their directory, and `cd docs/superpowers/plans && rm x.md` names one by relative path; both are ALLOWED. MAJOR 15, 16." — docs/reviews/2026-09-05-opus-review-og4-OG1r2.md:352-354
- *Reasoning:* Decisive question: the plan named a requirement (write verbs vs. "a plan path"), never the mutants. Three of the four rejection-causing holes — the plans directory, the `cd`/cwd base, `-i` after an operand — are cases the plan never named; MINOR 18 the reviewer explicitly absolves ("The plan enumerates the verbs, so this is not a deviation", :295). Missing-case stands. MAJOR 14 (`mv` made destination-only against an explicit contract) and MAJOR 18 (stated 300 ms budget missed at 907 ms) are real seat deviations: implementer secondary.

**Outcome — add-secondary `implementer`.** All three hold `missing-case`; two
(B, C) name `implementer` as the secondary.

### 8. rt1 · RT1 — ledger `vacuous` · classifier `implementer` (0.96)

Review: `docs/reviews/2026-09-05-opus-review-rt1-RT1.md`.
Classifier rationale: *"The plan's Interfaces section explicitly requires both override rules and factory-review's role/effort behavior. The implementer left these requirements untested, allowing M5, M6, M11, and M12 to survive."*

**Reader A** — `vacuous` +`implementer`, conf 0.75, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:80: "`factory-task`: resolution order for the model: `--model` > `OPENROUTER_MODEL` > `factory_route implement KIND SIZE` > the existing built-in default ... Effort: `OPENROUTER_REASONING_EFFORT` if set > the route's effort. ... `factory-review`: same with role `review` and `KIND SIZE` from the task heading." — contrast with the Step 1 Tests line, :87, which enumerates only "no overrides", "`OPENROUTER_MODEL=x/y`", and "`(code, M)` heading" cases: no `--model`-flag case, no non-empty `OPENROUTER_REASONING_EFFORT` case, and no `factory-review` case anywhere in Step 1.
- *Review:* docs/reviews/2026-09-05-opus-review-rt1-RT1.md, "MAJOR 3 — `factory-review` has no test." and, in the Mutation table discussion: "no test in the file ever passes `--model` (`grep -n -- '--model' tests/unit/80-seat-driver.bats` matches only a comment), and all three resolution cases set `OPENROUTER_REASONING_EFFORT=` **empty** ... The env-effort override is therefore never exercised with a value."
- *Reasoning:* Interfaces (line 80) states the override precedence and factory-review symmetry as prose requirements, not mutants. Step 1's Tests (line 87) never names a --model-flag case, a non-empty effort-override case, or any factory-review case — the seat satisfied every case the plan actually specified. M5/M6/M11/M12 were first named as mutants only in RT2's fix round (line 201), written after the gate — the same after-the-gate pattern as B1b, which the board already grouped RT1 under (log 2026-09-07: "Shape of sb4·SB2, ev1·R8, rt1·RT1").

**Reader B** — `vacuous`, no secondary, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:87 — "factory-task resolution: extend the existing dispatch test's pattern ... a fake `dsh-openrouter` on PATH that records its `--model` argument and `$OPENROUTER_REASONING_EFFORT` to a file ...: with a plan heading `(docs, XS)` and no overrides → the fake sees `deepseek/deepseek-v4-flash` and `off` ...; with `OPENROUTER_MODEL=x/y` → `x/y`, `route: explicit`; with a `(code, M)` heading → Pro and `medium`." (no case with `--model` set, no case with `OPENROUTER_REASONING_EFFORT` set to a value, and no `factory-review` test bullet at all, despite line 80's "`factory-review`: same with role `review`")
- *Review:* docs/reviews/2026-09-05-opus-review-rt1-RT1.md: "Why M5 and M6 survive is mechanical, not accidental: no test in the file ever passes `--model` ..., and all three resolution cases set `OPENROUTER_REASONING_EFFORT=` **empty**, which `${…:-…}` treats as unset. ... Why M11/M12 survive: `factory-review` appears in no test in the file."
- *Reasoning:* The Interfaces line (80) states the requirement (precedence order, factory-review "same"), but the plan's own Tests section (Step 1, line 87) is the section that must name mutants/cases per §3 Step 4 and rubric row 5 — and it never enumerates a `--model` case, a non-empty `OPENROUTER_REASONING_EFFORT` case, or any `factory-review` case. This is requirement-only, exactly the design doc's own Appendix B entry for rt1·RT1 ("an Interfaces line without a named test is decoration"), which the spec cites as its worked vacuous example. Classifier's rationale conflates "Interfaces requires X" with "plan named the mutant" — it doesn't; Step 1 never asks for these tests at all, so the seat built exactly what Step 1 specified. Ledger's vacuous holds.

**Reader C** — `vacuous` +`implementer`, conf 0.83, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:87 — "factory-task resolution: extend the existing dispatch test's pattern … with a plan heading `(docs, XS)` and no overrides → the fake sees `deepseek/deepseek-v4-flash` and `off`, and the `.result` has `route: implement/docs/XS`; with `OPENROUTER_MODEL=x/y` → `x/y`, `route: explicit`; with a `(code, M)` heading → Pro and `medium`." (Interfaces at :80 states the requirement: "resolution order for the model: `--model` > `OPENROUTER_MODEL` > `factory_route implement KIND SIZE` … `factory-review`: same with role `review`")
- *Review:* docs/reviews/2026-09-05-opus-review-rt1-RT1.md:171-172 — "All three resolution cases pass the variable **empty**, which cannot distinguish `${…:-…}` from a bare `effort=$route_effort`; M6 proves it." (and :190-191, MINOR 1: "The plan's Interfaces list this as an exit-3 condition; the plan's step-1 test list does not, so this is a gap rather than a broken promise")
- *Reasoning:* Interfaces named the requirement (precedence, factory-review role review); Step 1 named only three resolution cases and no mutant. As prescribed, those cases set the effort var empty — they cannot go red on M6 — and list no `--model` case and no factory-review test, so M5/M11/M12 were never reachable. Requirement without mutant: the plan's fault, vacuous. Same shape as B1b, sb4·SB2, ev1·R8. Implementer secondary: the seat broke the explicit "verbatim" contract (routing.toml missing its final newline, Deviation 1).

**Outcome — add-secondary `implementer`.** All three hold `vacuous`; two (A, C)
name `implementer` as the secondary.

### 9. rt2c · RT2 — ledger `vacuous` · classifier `implementer` (+`underspecified`) (0.90)

Review: `docs/reviews/2026-09-05-opus-review-rt2c-RT2.md`.
Classifier rationale: *"The plan explicitly required the cross-check mutant to fail, but M4a survived; finding 1 says the plan already requested the needed fixture. Separately, freezing flake.nix left the sandbox coverage contract unresolved."*

**Reader A** — `vacuous` +`implementer`, conf 0.78, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:179 — "`route.py lookup ROUTE ROLE KIND SIZE` prints `MODEL EFFORT` with the same specificity rule as `factory_route` (the two implementations are cross-checked by a test that runs both on the same fixture)."
- *Review:* docs/reviews/2026-09-05-opus-review-rt2c-RT2.md Finding 1: "The two lookup implementations' tie rule is unverified. M4a survives. Fix: give the cross-check a fixture with a discriminating tie... The plan's wording ("on the same fixture") already asks for this."
- *Reasoning:* Strongest implementer case: finding 1 itself says the plan "already asks for" a cross-check, so the seat's choice to reuse only the production table (whose one tie is symmetric) was its own shortcut, not compelled. But the plan text names a proof shape ("cross-checked by a test... on the same fixture"), never the falsifying mutant (flip route.py's tie-break spec>best_spec to >=) or the requirement that the fixture must contain a discriminating tie. Appendix B's own worked entry for this exact row (line 903) states the missing plan sentence as "a fixture that discriminates, not the production table" — i.e. the design doc's canon already treats this as the plan's gap, matching bk3·B1b's rule. Secondary implementer stands on Blocker 3: the commit body's false claim about factory-unit's coverage contradicts the seat's own accurate FACTORY-NOTES line, an unforced self-inconsistency the plan never asked for.

**Reader B** — `vacuous` +`underspecified`, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:179 — "`route.py lookup ROUTE ROLE KIND SIZE` prints `MODEL EFFORT` with the same specificity rule as `factory_route` (the two implementations are cross-checked by a test that runs both on the same fixture)." / :183 — "cross-check: for 6 fixed tuples, `factory_route` and `route.py lookup` print identical lines."
- *Review:* 2026-09-05-opus-review-rt2c-RT2.md:28-32 — "the cross-check runs only on the committed table, whose one genuine tie … has the *same* model and effort in both rows, so no tuple can see it. The plan asked for the two implementations to be 'cross-checked by a test that runs both on the same fixture'; a fixture that discriminates tie order is missing."
- *Reasoning:* The plan names only the property ("cross-checked … same fixture") and prescribes the proof shape as "6 fixed tuples" — nowhere does it say the fixture must contain a discriminating tie, or name the tie-break comparator as a mutant to kill. Appendix B's own row (rt2c · RT2) agrees: "the cross-check runs on the committed table whose one tie is symmetric … a fixture that discriminates, not the production table" — i.e. the missing sentence was the plan's, not the seat's. The classifier's claim that the plan "explicitly required the cross-check mutant to fail" over-reads "on the same fixture" as if it specified fixture contents; it specified only that both implementations share one fixture, which they do (the committed table) — and that shared fixture happens to make the assertion untestable against M4a, textbook vacuous. Blocker 3 (commit body vs. FACTORY-NOTES) is a separate, real implementer misstatement, but it doesn't overturn blocker 1's plan-side root cause. Secondary underspecified because the plan's own factory-unit claim ("drift fails the check") is irreconcilable with its own flake.nix freeze in the same section — a contract the plan itself left open.

**Reader C** — `vacuous` +`implementer`, conf 0.86, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:183 — "cross-check: for 6 fixed tuples, `factory_route` and `route.py lookup` print identical lines." (and :179 "the two implementations are cross-checked by a test that runs both on the same fixture"). RT2's section contains no mutation list; the tie-fixture mutant "flip `route.py`'s tie-break to `>=` → the cross-check test fails" first appears in the FIX-round section RT2b (:217).
- *Review:* docs/reviews/2026-09-05-opus-review-rt2c-RT2.md:28-32 — "the cross-check runs only on the committed table, whose one genuine tie (`openrouter implement/docs/any` vs `implement/any/XS`) has the *same* model and effort in both rows, so no tuple can see it. The plan asked for the two implementations to be \"cross-checked by a test that runs both on the same fixture\"; a fixture that discriminates tie order is missing."
- *Reasoning:* Decisive question: RT2 named only a requirement and a proof shape — six fixed tuples, "the same fixture" — never the mutant. Its verbatim prescription runs on the committed table, whose only tie has identical model and effort, so no prescribed tuple can go red on the tie rule; M4a's survival was built into the plan. The named mutant appears only in RT2b, written after the gate. Implementer secondary: blocker 3, the commit body asserted a drift refusal FACTORY-NOTES correctly denied.

**Outcome — add-secondary `implementer`.** All three hold `vacuous`; two (A, C)
name `implementer` as the secondary.

### 10. rt5 · RT5 — ledger `missing-case` · classifier `implementer` (0.96)

Review: `docs/reviews/2026-09-05-opus-review-rt5-RT5.md`.
Classifier rationale: *"MAJOR-1 says the plan required the \"same rule for shell commands,\" but quoting and line continuations bypass enforcement. The continuation was explicitly listed as must-deny; the implementation failed the stated requirement."*

**Reader A** — `missing-case`, no secondary, conf 0.82, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:264 — "Same rule for shell commands: a bash command containing `--model <id>` or `OPENROUTER_MODEL=<id>` where `<id>` is not an openrouter row → deny (this is how a nested `dsh-openrouter` launch would bypass the sub-agent tools)." Step 1 (line 267) then names exactly one shell case to test: "bash `dsh-openrouter --model moonshotai/kimi-k3 --headless x` → deny; `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 …` → allow." No quoted, `--model=`, tab, or `\`+newline spelling appears anywhere in RT5's own section.
- *Review:* Appendix B, docs/superpowers/specs/2026-09-05-planning-agent-design.md — "rt5 · RT5 | missing-case | quoted and continued spellings allowed; the one env test asserts allow | enumerate quoting and continuation; never let a rule's only test be an allow"; and the gate review itself, MAJOR-1: "The continuation case is one the gate enumerated as must-deny" (the gate's own bypass table, not the plan's Step 1).
- *Reasoning:* Steelman for implementer: the Interfaces prose states a general rule — "a bash command containing --model <id>" — that on its face covers every shell spelling including quoted/continued ones, and MAJOR-2 shows the seat under-tested even the plainest cases (M5, M10 survive), suggesting sloppy execution rather than an unpinned plan. A reader could argue "containing --model <id>" already promises quote-tolerance, so a regex that structurally excludes quotes from the id charset breaks a stated contract regardless of what Step 1 happened to enumerate. But this doesn't survive: Step 1 is the plan's own operational definition of "pinned" (§3/Appendix A Q1), and it names only the bare unquoted spelling as a required test — exactly the pattern the house rule addresses (instruction present, mutant/case absent → plan fault). The classifier's rationale mistakes the *reviewer's* bypass-attempts table ("the gate enumerated as must-deny") for something the *plan* required; the plan itself never lists quoting or continuation. Appendix B's own worked row for this exact key says the plan needed to "enumerate quoting and continuation" — direct authorial confirmation, matching missing-case, no secondary in the filed ledger row.

**Reader B** — `missing-case`, no secondary, conf 0.90, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:260 — "Same rule for shell commands: a bash command containing `--model <id>` or `OPENROUTER_MODEL=<id>` where `<id>` is not an openrouter row → deny (this is how a nested `dsh-openrouter` launch would bypass the sub-agent tools)." Step 1 (line 262) enumerates only two concrete bash payloads: `dsh-openrouter --model moonshotai/kimi-k3 --headless x` → deny, and `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 …` → allow. No quoted, continuation, tab, or `=`-form spelling is named anywhere in the section.
- *Review:* 2026-09-05-opus-review-rt5-RT5.md, Bypass attempts table: `--model "z-ai/glm-5.3"` (double quotes) → ALLOWED — MAJOR-1; `--model \` + newline + `z-ai/glm-5.3` (continuation) → ALLOWED — MAJOR-1; and MAJOR-2: "M5 and M10 survive: no test fails when the `--model=` form stops matching, and none fails when the `OPENROUTER_MODEL=` pattern stops matching anything at all — the single `OPENROUTER_MODEL` test asserts allow."
- *Reasoning:* The plan's bash-rule sentence names only the abstract requirement (`--model <id>`/`OPENROUTER_MODEL=<id>` → deny) and its own Step 1 enumerates just two payloads, neither quoted nor continued nor `=`-form; it never says quoting/continuation is "must-deny" — that enumeration is the reviewer's own bypass-attempts table, which the classifier's rationale misreads as a plan requirement. The design doc's own Appendix B independently files rt5·RT5 as missing-case: "quoted and continued spellings allowed; the one env test asserts allow | enumerate quoting and continuation; never let a rule's only test be an allow" (spec line 904) — an authoritative worked example matching this exact row. No mutant for any quoted/continued/`=` spelling was named, so the plan did not pin the case; classifier's premise (continuation "explicitly listed as must-deny" by the plan) is a wrong-fact about the plan's content.

**Reader C** — `missing-case` +`vacuous`, conf 0.86, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:262: "- Same rule for shell commands: a bash command containing `--model <id>` or `OPENROUTER_MODEL=<id>` where `<id>` is not an openrouter row → deny (this is how a nested `dsh-openrouter` launch would bypass the sub-agent tools)." — and its whole test list, :265: "bash `dsh-openrouter --model moonshotai/kimi-k3 --headless x` → deny; `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 …` → allow." (Quoting, `--model=`, and the backslash-continuation appear first at :316, in the RT5b fix round.)
- *Review:* line 31: "The continuation case is one the gate enumerated as must-deny." — and line 202-207: "**MAJOR-2 — the nested-seat rule is vacuously tested.** M5 and M10 survive: no test fails when the `--model=` form stops matching, and none fails when the `OPENROUTER_MODEL=` pattern stops matching anything at all — the single `OPENROUTER_MODEL` test asserts *allow*"
- *Reasoning:* The plan named only the requirement ("same rule for shell commands") in one bare spelling, and prescribed one bash deny plus an allow-only OPENROUTER_MODEL test. No mutant: quoting, `--model=`, and the continuation are absent — they first appear in RT5b, after the gate. The classifier's "explicitly listed as must-deny" is the gate's own bypass table (review:31), not the plan. Ledger holds; the plan-prescribed allow-only test adds a vacuous secondary. Implementer secondary unwarranted: the seat shipped exactly the enumerated tests, touches matched, the one extra file disclosed.

**Outcome — hold.** All three hold `missing-case`; the one secondary named
(`vacuous`, by C alone) is below the two-reader bar.

### 11. rt5 · RT5b — ledger `underspecified` · classifier `implementer` (0.98)

Review: `docs/reviews/2026-09-05-opus-review-rt5-RT5b.md`.
Classifier rationale: *"MAJOR-1 violates explicit plan requirements: Step 3 says \"never raise,\" and unparsable routing tables must DENY. The implementation instead raises uncaught RecursionError and UnicodeDecodeError, causing the harness to allow."*

**Reader A** — `underspecified`, no secondary, conf 0.83, rule `requirement-only`.

- *Plan:* "never raise: any exception → allow for non-model rules exactly as today, but the model rule fails closed as specified" (docs/superpowers/plans/2026-09-05-seat-routing.md:266, RT5's Step 3, binding on RT5b as the fix round's governing contract)
- *Review:* "Not a regex tweak; the guard needs an error contract it currently lacks:" (docs/reviews/2026-09-05-opus-review-rt5-RT5b.md:238-239)
- *Reasoning:* The strongest case for implementer: RT5's Step 3 explicitly says "never raise" and "the model rule fails closed as specified" — plain prose the seat's uncaught RecursionError/UnicodeDecodeError violated, and RT5b's own Step 3 told the seat to add the unbounded recursive walk that caused it. But the plan never named the mutant: no exit-code/stdout contract, no depth/node bound, no exception-class list, no top-level try/except architecture — Step 1's test list (line 316) asks only for spelling/nesting-shape coverage, never a crash/exit-status test. The review itself concludes the fix isn't implementer error but a missing design element — "the guard needs an error contract it currently lacks" — and routes it to a re-plan (RT5c/RT5r) under rule A1, not another fix round. RT5r's Contract section (lines 350-355) then supplies exactly what was missing: main() returns 0 on every path, fail-closed on named exception classes, an iterative walk with explicit depth/node budgets — none of which RT5/RT5b's plan specified. This matches the design doc's own pre-existing Appendix B row 905 verbatim: "underspecified | nesting ≥ 995 raises, exit 1, empty stdout = allow | an error contract: exit and stdout on every internal failure" — a proof-shape/requirement ("never raise") named without the mutant (the error contract) that would pin it. Ledger stands.

**Reader B** — `underspecified`, no secondary, conf 0.82, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:266 — "**Step 3: Implement** (stdlib `tomllib`; the guard already parses JSON on stdin — keep it deny-only; never raise: any exception → allow for non-model rules exactly as today, but the model rule fails closed as specified)."
- *Review:* docs/reviews/2026-09-05-opus-review-rt5-RT5b.md:40-42 — "The same crash-to-allow shape reaches the fail-closed table rule: a routing table that is not valid UTF-8 raises `UnicodeDecodeError`, which `except (OSError, tomllib.TOMLDecodeError)` does not catch, so an explicit model is ALLOWED where the interface says an unparsable table must DENY. Root cause is one thing: nothing contains the guard's exceptions, and the plan's Step 3 says 'never raise.'"
- *Reasoning:* The strongest case for implementer: RT5's Interfaces line 261 explicitly says "unparsable → DENY," and Step 3 explicitly says "never raise... model rule fails closed as specified" — a stated contract the shipped code violates twice (RecursionError, UnicodeDecodeError). That reads like a named requirement being broken. But neither sentence names a mutant: no exception types to catch, no recursion/depth bound, no top-level try/except architecture, no "assert exit 0" test. RT5r's very next section had to invent all five as new Contract items 1-5 ("main() returns 0 on EVERY path... a top-level try/except BaseException... iterative... bounded by a node budget... every existing test now ALSO asserts exit 0") — proving these mechanisms were absent, not merely unimplemented. The reviewer itself treated this as a design point requiring rule A1 re-plan, not a fix round, and Appendix B independently records it as "underspecified: an error contract... missing." Requirement named, mutant absent → plan fault, matching the ledger.

**Reader C** — `underspecified` +`implementer`, conf 0.82, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-routing.md:317 — "**Step 3: Implement**: one normalisation pass (`\` + newline → ``, tabs → spaces), one regex for `--model(=|\s+)(['\"]?)([A-Za-z0-9._:/-]+)\2`, one for `OPENROUTER_MODEL=(['\"]?)([A-Za-z0-9._:/-]+)\1` with an optional leading `env `, a recursive walk for `model` keys in `tool_input`. **Step 4: Green** — … re-run RT5's killed mutants + the two survivors (M5 `--model=` unmatched, M10 `OPENROUTER_MODEL=` dead) — all must now die." (parent RT5, line 266: "keep it deny-only; never raise: any exception → allow for non-model rules exactly as today, but the model rule fails closed as specified")
- *Review:* docs/reviews/2026-09-05-opus-review-rt5-RT5b.md:41-42 — "Root cause is one thing: nothing contains the guard's exceptions, and the plan's Step 3 says \"never raise\"." (and :254 "both asserting **exit status 0** (today's tests never assert the status on these paths, which is why a crash is invisible to the suite)")
- *Reasoning:* The plan named the requirement ("never raise", unparsable table → DENY) and no mutant for it: no depth or node budget, no exit-status assertion, no non-UTF-8 case, and the only named mutants (M5, M10, spelling) the seat killed 13/15. Worse, Step 3 prescribed the very "recursive walk" that raises. The missing sentence is an error contract — exit and stdout on every internal failure — which RT5r then supplies. Ledger holds; the seat still shipped raising code against an explicit "never raise", so implementer secondary.

**Outcome — hold.** All three hold `underspecified`; only C names an
`implementer` secondary.

### 12. sb5 · SB2b — ledger `missing-case` · classifier `implementer` (0.98)

Review: `docs/reviews/2026-09-05-opus-review-sb5-SB2b.md`.
Classifier rationale: *"MAJOR-1: contract item (3) explicitly permits only dotted IPv4 addresses and requires die 2 otherwise, but the implementation accepts 256.1.1.1 and passes it to --host. The stated contract was adequate; the regex violated it."*

**Reader A** — `missing-case`, no secondary, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-behind-broker.md:120: "3. `--bind-namespace ADDR` accepts only a dotted IPv4 address that is not `0.0.0.0`, not loopback and not a flag-shaped string; anything else → `die 2` (mutation: validation removed → fails)." — and Step 1, line 147: "the four invalid addresses and the empty value" (no out-of-range octet listed); SB2r, line ~139-141 treats the octet range as a correction: "the bind address is a real IPv4 address (octet range)… mutation: octet range dropped → fails."
- *Review:* docs/reviews/2026-09-05-opus-review-sb5-SB2b.md, MAJOR-1: "`[0-9]{1,3}` accepts `256`–`999`… The gate's required matrix pre-committed `256.1.1.1 → 2`; observed `0`. Plan contract item (3) says the flag 'accepts only a dotted IPv4 address'… No test covers the octet range, so M-C (validation removed) is still killed by 100/101/102 and this gap is invisible to the suite."
- *Reasoning:* Item (3) names a requirement and a mutant, but the named mutant ("validation removed") is coarser than the defect (octet-range escape) and is fully killed by the shipped tests; Step 1's own case list never enumerates an out-of-range address. SB2r re-adds octet-range as a correction, and the design doc's Appendix B (line 908) independently calls this row missing-case: "validate as an IPv4 address, not a shape." Requirement named, specific mutant absent.

**Reader B** — `missing-case`, no secondary, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-behind-broker.md:120 — "3. `--bind-namespace ADDR` accepts only a dotted IPv4 address that is not `0.0.0.0`, not loopback and not a flag-shaped string; anything else → `die 2` (mutation: validation removed → fails)."
- *Review:* docs/reviews/2026-09-05-opus-review-sb5-SB2b.md:320 — "No test covers the octet range, so M-C (validation removed) is still killed by 100/101/102 and this gap is invisible to the suite."
- *Reasoning:* Item (3)'s only named mutant is "validation removed" — total absence of a check — which a shape-only regex still kills; it does not target the octet-range gap. Step 1's required test list (line 126) never names an out-of-range value either. SB2r later had to add a fresh mutant explicitly ("octet range dropped → fails", line 140) to cover this — proof SB2b never named it. Appendix B's pre-audit entry (line 908) independently reaches "validate as an IPv4 address, not a shape," matching the ledger. The classifier's "stated contract was adequate" reads the prose alone and ignores that the plan's own mutation/test list for item 3 could not have caught this.

**Reader C** — `implementer` +`missing-case`, conf 0.66, rule `other`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-behind-broker.md:120 — "3. `--bind-namespace ADDR` accepts only a dotted IPv4 address that is not `0.0.0.0`, not loopback and not a flag-shaped string; anything else → `die 2` (mutation: validation removed → fails)."
- *Review:* docs/reviews/2026-09-05-opus-review-sb5-SB2b.md:316-322 — "The gate's required matrix pre-committed `256.1.1.1 → 2`; observed `0`. Plan contract item (3) says the flag \"accepts only a dotted IPv4 address that is not `0.0.0.0`, not loopback and not a flag-shaped string; anything else → `die 2`\", and the wrapper's own message says \"must be a dotted IPv4 address\" while accepting a string that is not one."
- *Reasoning:* The finding is behaviour, not a vacuous test: 256.1.1.1 reaches the real `--host` argv. The plan states the rule affirmatively — only a dotted IPv4 address, anything else die 2 — and 256.1.1.1 is not one; the exclusions listed after it add to that rule, they do not shrink it. A violated explicit contract. Appendix B's "missing" sentence only restates the plan's words. Secondary missing-case: the named mutant (validation removed) never pinned the octet range, so the suite could not see it; SB2r supplies that mutant.

**Outcome — hold.** The decider reads a violated explicit contract and calls
`implementer`, but both advocates hold `missing-case`; two of three carry the
ledger, and the convergence rule requires all three for a relabel. This is the
one row of the seventeen where the panel split on the primary, and the closest
the classifier came to being right.

### 13. sc4 · G8b — ledger `underspecified` · classifier `implementer` (0.98)

Review: `docs/reviews/2026-09-05-opus-review-sc4-G8b.md`.
Classifier rationale: *"MAJOR-2 repeats the host-local dependency explicitly forbidden by the task brief. The implementation also violates Step 4's requirement that the committed block match the hook's derivation, and Step 3's pre-commit acceptance fails."*

**Reader A** — `underspecified` +`missing-case`, conf 0.85, rule `requirement-only`.

- *Plan:* "4. §3 amended (2026-09-05 evening, from the G8b gate): the board's generated queue block covers this repo only and is derived from this tree only (no `repos.toml`, no runs dir, no store)..." — docs/superpowers/specs/2026-09-05-session-context-and-task-graph-design.md:207
- *Review:* "MAJOR-2 — the block is not derived from the tree it is committed into." — docs/reviews/2026-09-05-opus-review-sc4-G8b.md:216 (with the review's own framing at line 26: "the task brief named: the block still depends on host-local state")
- *Reasoning:* Steelmanned implementer first: classifier says MAJOR-2 "repeats the host-local dependency explicitly forbidden by the task brief." But the plan's only host-local prohibition (spec:1080) is about runs-dir/store, which G8b genuinely fixed (M7 killed, review confirms). Repos.toml host-path independence was never named anywhere in G8's or G8b's section — the spec itself admits the rule barring it was "amended... from the G8b gate," i.e. written after this task, in G8c. So MAJOR-2 is a case the plan never named at all (below even "requirement-only"). MAJOR-1 (self-invalidating block once the commit's own subject lands) is likewise an unnamed edge case in the landed-status design from G1, not a deviation from a stated Step 4 contract — "the committed block matches the hook's derivation" is the reviewer's own gate-brief paraphrase, not literal plan text. No named mutant for either major; the ledger's underspecified (plus a missing-case flavor for the self-referential gap) stands.

**Reader B** — `underspecified`, no secondary, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-session-context.md:1555 — "the committed queue block covers THIS repo only and is derived from THIS tree only — no `repos.toml` (home paths differ per machine), no runs dir, no store; `write-board` and `check --board` both build the graph from a one-repo list … so they cannot disagree" (this sentence is G8c's, i.e. it does NOT exist in G8b's own section, lines 1534–1548, or in G8's original contract, lines 1283–1332)
- *Review:* docs/reviews/2026-09-05-opus-review-sc4-G8b.md, MAJOR-2 — "`write-board` reads `docs/ledger/repos.toml` … the hook overrides `--repos` to `$PWD` and one repo. The FACTORY-NOTES claim … is half true … the host-path dependency is not [gone]. Measured four different blocks from one commit … This is the failure mode the task brief called a MAJOR, and it is present."
- *Reasoning:* Neither G8's contract nor G8b's section ever states that write_board/check--board must derive from a tree-only, repos.toml-free graph — that sentence is first authored in G8c ("fixed by rule here (spec §3 amended)"), and Appendix B's own row for sc4·G8b records the missing sentence as exactly that rule, confirming the gap predates the audit. The classifier's "explicitly forbidden by the task brief" is not supported by the text; it also misattributes a "Step 4" condition ("committed block matches the hook's derivation") that appears only in the reviewer's own gate-brief checklist, not in G8b's plan Step 4 (which only requires a byte-identical commit subject). MAJOR-1 (self-invalidating block) traces to G8's block-generation design, which G8b inherited with no instruction for reconciling it with the Step-3 hook-pass requirement — also fixed only in G8c. No mutant, and for the decisive design rule not even a requirement, was named before the fix round; the plan class stands.

**Reader C** — `underspecified` +`implementer`, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-session-context.md:1296 — `def render_board_block(graph) -> str          # "**Queued (derived).** <repo>: <wave-1 keys> (<plan>) · …\n" — one line per repo with open work; "nothing queued" when none` (G8's contract, which G8b Step 2 tells the seat to verify against; the section never says which tree the graph is built from, and G8b's own text — file:1538-1545 — names no mutant on derivation source. The rule "the committed queue block covers THIS repo only and is derived from THIS tree only — no repos.toml (home paths differ per machine)" is first written in the FIX section G8c, file:1555.)
- *Review:* line 216-218: "**MAJOR-2 — the block is not derived from the tree it is committed into.** `write-board` reads `docs/ledger/repos.toml`, i.e. `~/nixos-agent-env` and four sibling `~/flakes/*` paths; the hook overrides `--repos` to `$PWD` and one repo."
- *Reasoning:* Decisive question: the plan named no mutant — and no requirement — for derivation source. Worse, G8's contract mandates a per-repo (repos.toml) graph; the $PWD override existed only on the hook's check side (G5b), and G8b never says write-board must match it. The seat implemented the plan's contract; the tree-only rule is authored afterwards in G8c. Appendix B agrees ("four different blocks from one commit depending on cwd"). Secondary implementer: minors m2/m5 — G8 Step 3 said move dropped queue sentences into Now; the seat lost them — plus a half-true FACTORY-NOTES claim.

**Outcome — hold.** All three hold `underspecified`; the two secondaries named
differ (`missing-case` by A, `implementer` by C), neither reaching two readers.

### 14. sc5 · G11 — ledger `missing-case` · classifier `implementer` (0.98)

Review: `docs/reviews/2026-09-05-opus-review-sc5-G11.md`.
Classifier rationale: *"The declared G11 plan was delivered and well tested. Rejection centers on an undeclared, unallowed change: widening check to a global namespace contradicted G4's pinned per-repo rule while leaving cross-repo dependencies permanently blocked and untested."*

**Reader A** — `missing-case` +`implementer`, conf 0.72, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-session-context.md:1575 — "**Files:** ... the plan sections of cross-repo tasks gain one field line each: ... `**repo:** gaming` under `### PB0` in `docs/superpowers/plans/2026-09-05-operator-items.md` (adding a field line is allowed; never touch a heading)" — G11's own Interfaces/Steps (1577-1582) say nothing about what happens to an existing same-repo `dependsOn` edge (PB1 → PB0) once PB0 is reattributed elsewhere, even though G4's already-pinned rule (line 457: "a `depends_on` key whose chain root is not a task in any typed plan of the same repo") makes that edge break the moment `**repo:**` ships.
- *Review:* Findings, MAJOR 2: "The gate's contract is that such a dependency is satisfied when that repo's graph has it landed. Widening `check` removed the only signal that the edge is dangling without making it resolvable"; and Deviations: "Behaviour the orchestrator should pin in the spec, whatever G11b does: a `dependsOn` naming a task attributed to another repo is satisfied only when that repo's graph reports the key `landed`... One sentence in docs/superpowers/specs/2026-09-05-session-context-and-task-graph-design.md §3."
- *Reasoning:* Strongest case FOR implementer: G4's per-repo `check` rule was already pinned text in this same plan document (line 457), and G11's Interfaces list only repo/attribution/board/task-status — never "modify check's namespace scoping." Widening it to a global namespace was thus a deviation from an explicit prior contract, undisclosed in the commit and only half-disclosed in NOTES — exactly what "other" (violated explicit contract, undisclosed change) describes, and the classifier's read is defensible on that finding alone. But the underlying cross-repo satisfaction semantic itself — what a dependsOn edge means once its target is reattributed to another repo — was never named anywhere before this gate: not in G11's plan, not in G4, not in the spec. The review's own Deviations section explicitly asks the orchestrator to add this "whatever G11b does," confirming it was new ground, not a restated rule the seat chose to ignore. G11's declared body (repo field, attribution, board exclusion, task-status rows) was delivered clean and well tested per the review's own Summary. The seat only touched `check` at all because the plan's Files section directs a change (`**repo:** gaming` on PB0) that, combined with the pre-existing real-tree edge PB1→PB0, makes the mandated `lint` acceptance criterion (Global Constraints) unsatisfiable without SOME resolution — a conflict the plan created and never resolved. That is a case the plan never named, textbook missing-case; the sloppy, undisclosed, rule-breaking way the seat filled that gap is real and earns an implementer secondary (same shape as bk3·B1b), but does not overturn the primary.

**Reader B** — `implementer` +`missing-case`, conf 0.72, rule `other`.

- *Plan:* docs/superpowers/plans/2026-09-05-session-context.md:1578 — "`FIELD_RE` accepts `repo`; `task[\"repo\"]` = the value or `None`. `scan_repo` for repo R includes: typed tasks from R's own plans whose `repo` is `None` or equals R, PLUS typed tasks from every OTHER configured repo's plans whose `repo` equals R … `board_graph` (repo-only mode) excludes tasks whose `repo` names another repo and cannot pull tasks from elsewhere (it has one repo) — so the board block never lists them." (no mention anywhere in the G11 section of `check`, `dependsOn` resolution, or the cross-repo edge)
- *Review:* docs/reviews/2026-09-05-opus-review-sc5-G11.md, Deviations — "Recorded, unallowed: `check`'s unknown-key rule changed from per-repo to a global namespace, and `scan_repo` gained a `defined_roots` return key. Disclosed in NOTES only as 'cross-repo dependsOn resolution added to keep lint green'; the semantics were not. Rejected above."
- *Reasoning:* Plan named neither the requirement nor a mutant for cross-repo dependsOn — it's silent, and the review confirms the declared scope "is delivered and well tested." All three MAJORs concern code the seat volunteered unprompted, half-disclosed, and that affirmatively violated G4's already-pinned same-repo rule — a contract violation/undisclosed change, not a vacuous test on a named case. The plan's silence on PB1's consequent breakage is a real but secondary gap; deferring it (as G11b/G11r then did) matches this plan's own normal iterative pattern.

**Reader C** — `missing-case` +`implementer`, conf 0.83, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-session-context.md:1582 — "Real data: `tasks.py --root . brief` shows H1 under dsh-harness (landed) and PB0 under gaming (ran/approved), none under nixos-agent-env." (The section's Interfaces, :1578–1579, define `repo:` attribution and `check`'s task-status rule; neither the section nor any Step names cross-repo `dependsOn` — no requirement, no proof shape, no mutant.)
- *Review:* docs/reviews/2026-09-05-opus-review-sc5-G11.md:277-279 — "**Behaviour the orchestrator should pin in the spec, whatever G11b does:** a `dependsOn` naming a task attributed to another repo is satisfied only when that repo's graph reports the key `landed`; it is never satisfied by absence, and `check` still refuses a key no plan defines."
- *Reasoning:* Decisive question: the plan named no mutant — and no requirement — for cross-repo `dependsOn`. Its own change (PB0 → gaming) dangles PB1's edge and reddens lint, a consequence the section never names; G4's per-repo rule lives outside the seat's packet (M13). The reviewer hands the semantic back to the orchestrator. Plan class stands: missing-case. The seat still shipped an unsound, untested, undisclosed widening rather than stopping — implementer secondary.

**Outcome — add-secondary `implementer`.** Two readers (A, C) hold
`missing-case` with an `implementer` secondary; B makes `implementer` the
primary. The primary is not unanimous, so no relabel; `implementer` is named by
all three in one position or the other, so it is added as the secondary.

### 15. cr17 · CR2rb — ledger `missing-case` · classifier `implementer` (0.87)

Review: `docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md`.
Classifier rationale: *"MAJOR-1 is a regression introduced by the implementer's tokenizer rewrite: quoted separators become clause boundaries, contradicting its documented contract and allowing previously denied plan writes. The review says CR2rb fulfills its planned fixes."*

**Reader A** — `missing-case` +`implementer`, conf 0.78, rule `requirement-only`.

- *Plan:* "Flag attribution is clause-local: the command is split on `;`, `&&`, `||`, `|`, newline into clauses BEFORE verbs and flags are attributed, so `rm -f result && git clean` and `ls -a && git stash` allow while each protected form still denies (mutation: whole-command attribution restored → the two allow cases fail)." — docs/superpowers/plans/2026-09-05-context-reset-ritual.md:194
- *Review:* "`tokenise_ctx` emits `;`, `&`, `|` and newline as clause boundaries even when they sit inside a quoted argument — contradicting its own header comment — and the new per-clause flag attribution then credits a trailing flag to the wrong clause." — docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md:586-589
- *Reasoning:* Strongest case for implementer: the review shows the implementer's OWN header comment for tokenise_ctx already states quoted newlines aren't boundaries, yet the code (and the sibling ;/&/| arms) contradicts it — an internal bug the implementer introduced against their own stated design, not new scope. But item 4's only named mutant is "whole-command attribution restored," testing that clauses split at all — never that quoted separators must not split them. Nothing in CR2rb (or any earlier section) states that requirement; it first appears as CR2r2 contract item 1, written only after this rejection. The plan never named this mutant or requirement, so missing-case stands; implementer as secondary because the contradiction was self-authored and plausibly foreseeable given quoted[] machinery already existed for -m.

**Reader B** — `missing-case`, no secondary, conf 0.78, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-context-reset-ritual.md:194 — "Flag attribution is clause-local: the command is split on `;`, `&&`, `||`, `|`, newline into clauses BEFORE verbs and flags are attributed, so `rm -f result && git clean` and `ls -a && git stash` allow while each protected form still denies (mutation: whole-command attribution restored → the two allow cases fail). Over-denial accepted only for a real protected form in any clause."
- *Review:* docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md:355-357 — "`tokenise_ctx` emits an operator token for `;`, `&`, `|`, `(`, `)`, `{`, `}`, `>` and for a newline **without ever consulting `$inq`**"
- *Reasoning:* Item 4 names the clause-split requirement and one mutant (whole-command attribution restored), which the seat killed (M-D/test 83). It never names "a quoted `;`/`&`/`|`/newline must not be a boundary" as a case; quote-tracking in the contract is scoped only to the `-m` exemption (item 1). CR2r2's very next plan introduces this as a brand-new contract item with its own mutant — proof it was absent here. The review's "contradicts its documented contract" refers to the implementer's own header comment, not the plan's contract; that distinction matters under the house rule. Matches design-doc precedent rt5·RT5 (quoting never enumerated → missing-case), and matches the ledger.

**Reader C** — `missing-case` +`implementer`, conf 0.82, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-context-reset-ritual.md:194 — "4. Flag attribution is clause-local: the command is split on `;`, `&&`, `||`, `|`, newline into clauses BEFORE verbs and flags are attributed, so `rm -f result && git clean` and `ls -a && git stash` allow while each protected form still denies (mutation: whole-command attribution restored → the two allow cases fail). Over-denial accepted only for a real protected form in any clause."
- *Review:* docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md:355-357 — "`tokenise_ctx` emits an operator token for `;`, `&`, `|`, `(`, `)`, `{`, `}`, `>` and for a newline **without ever consulting `$inq`** (`tools/orchestrator-guard.sh:234-305`)"
- *Reasoning:* Decisive question: the plan named item 4's mutant (whole-command attribution restored) — but that mutant is orthogonal to MAJOR-1. The plan told the seat to split on `;`, `&&`, `||`, `|`, newline with no quote caveat; the quoted-separator case is never named, and the successor CR2r2 has to add it as a new contract item. Requirement, not mutant, for the failing case: missing-case holds. Secondary implementer: the seat's own header contract was contradicted and the commit body's "timing figures are corrected" is false (MINOR-4).

**Outcome — add-secondary `implementer`.** All three hold `missing-case`; two
(A, C) name `implementer` as the secondary.

### 16. bk3 · B1b — ledger `vacuous` (+`implementer`) · classifier `implementer` (+`wrong-fact`) (0.99)

Review: `docs/reviews/2026-09-05-opus-review-bk3-B1b.md` (the precedent row, re-read once already on 2026-09-07, `f86ccde`).
Classifier rationale: *"Contract item 2 required a layout-based assertion or fixture; the implementation supplied redundant membership checks that never read the layout, allowing M-H to survive. Separately, MINOR 4 identifies the plan's false assertion that restic runs as root."*

**Reader A** — `vacuous` +`implementer`, conf 0.85, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-backup-audit-paths.md:69 — "`host-core` asserts the five and that no other entry under `/var/lib/lanes/*` survives the excludes except the ledger — state how it is proven (a fixture directory listing against the patterns in `proton-backup-eval`, or an assertion over the known lane layout)."
- *Review:* docs/reviews/2026-09-05-opus-review-bk3-B1b.md, MAJOR 1: "The plan named the two acceptable proofs: 'a fixture directory listing against the patterns in `proton-backup-eval`, or an assertion over the known lane layout'. What landed is neither... M-G — delete lines 870-880 outright: ... exit 0. A test that can be deleted without turning anything red is not a test."
- *Reasoning:* Strongest case for implementer: contract item 2 named two concrete proof shapes and the seat delivered neither, substituting a subsumed elem check — arguably a violated explicit instruction. But neither shape is a mutant; the plan's own Step 3 lists mutations only for items 1/2a (broker path, results-drop), none for 2b, so M-H (fourth lane child) was never named — it first appears in B1c, written after the gate. This is the design doc's own canonical exemplar of "a named proof shape is not a mutant" (spec Appendix B row, three adversarial reads converging 0.70-0.82). Requirement-only: plan class stands.

**Reader B** — `vacuous` +`implementer`, conf 0.90, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-backup-audit-paths.md:69 — "`host-core` asserts the five and that no other entry under `/var/lib/lanes/*` survives the excludes except the ledger — state how it is proven (a fixture directory listing against the patterns in `proton-backup-eval`, or an assertion over the known lane layout)." (Step-3 mutations at :73 name only items 1 and 2a: "the broker path re-added → red; the `results` exclude dropped → red" — no mutation is named for item 2's second half at all.)
- *Review:* docs/reviews/2026-09-05-opus-review-bk3-B1b.md, MAJOR 1: "The plan named the two acceptable proofs: 'a fixture directory listing against the patterns in `proton-backup-eval`, or an assertion over the known lane layout'. What landed is neither... M-G — delete lines 870-880 outright... exit 0. A test that can be deleted without turning anything red is not a test... M-H — Add one line to `nixosModules/modelLane.nix:210`... `host-core` exit 0, `core-backup-wiring` exit 0, `lane-eval` exit 0."
- *Reasoning:* Strongest case for the classifier: item 2 is a fully specified requirement naming two concrete mechanisms ("a fixture listing... or an assertion over the known lane layout"); implementing either literally (as B1c later did, deriving from tmpfiles rules) would have killed M-H, so the seat's choice to assert over the excludes list instead — the wrong data source — reads as a mechanism substitution, textbook implementer deviation, and 16 sibling rows were called implementer on identical "requirement named, seat failed it" reasoning. But the decisive test is mutant-vs-requirement, not requirement-vs-none: Step 3's own mutation list (line 73) names killing mutants only for items 1 and 2a ("broker path re-added → red", "results exclude dropped → red") and none for item 2's second half — the plan gives two proof *shapes* ("or" between a fixture and a layout assertion) but never the one-line change ("a fourth lane child added to modelLane's tmpfiles") that a correct implementation must go red on. This is exactly the rubric's own worked example (spec §3, Appendix B: "name the mutant, not the proof shape... a fourth lane child... (B1c)"), and the review's finding is structural, not behavioral: M-G shows the shipped assertion is deletable with everything green (a vacuous test by definition), independent of what the seat "should" have written. Because no mutant was named, "requirement present, mutant absent" resolves to the plan class under the house rule — vacuous stands as primary. Secondary implementer is still earned: the seat had a genuine, cheap path to compliance ("an assertion over the known lane layout") and instead wrote a check over the wrong list, so its execution independently fell short of even the proof-shape guidance given.

**Reader C** — `vacuous` +`implementer`, conf 0.82, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-backup-audit-paths.md:69 — "`host-core` asserts the five and that no other entry under `/var/lib/lanes/*` survives the excludes except the ledger — state how it is proven (a fixture directory listing against the patterns in `proton-backup-eval`, or an assertion over the known lane layout)." And :73 — "mutation: the broker path re-added → red; the `results` exclude dropped → red."
- *Review:* docs/reviews/2026-09-05-opus-review-bk3-B1b.md:213 — "**M-G** — delete lines 870-880 outright: `nix build .#checks.x86_64-linux.host-core -L --no-link` → **exit 0**. A test that can be deleted without turning anything red is not a test."
- *Reasoning:* Decisive question: for contract item 2b the plan named a requirement and two proof shapes ("a fixture directory listing… or an assertion over the known lane layout") and delegated the proof to the seat ("state how it is proven"). Its Step 3 mutants cover items 1 and 2a only; the exposing mutant (a fourth lane child → host-core red) first appears in B1c. Requirement-only, so the ledger's vacuous stands. Implementer secondary is warranted: the seat shipped neither offered proof, only a subsumed elem check.

**Outcome — hold.** The precedent row survives a second, independent panel
unchanged: `vacuous` primary, `implementer` secondary already filed. The
classifier's `wrong-fact` secondary (the restic-as-root sentence) is named by
no reader and is not added.

### 17. sb4 · SB2 — ledger `vacuous` · classifier `vacuous` (0.96) — **control**

Review: `docs/reviews/2026-09-05-opus-review-sb4-SB2.md`.
Classifier rationale: *"CONTROL ROW: the classifier agreed with the ledger; the CA requirement can be deleted with 95 tests green — a deletion mutant per contract item was the sentence the plan needed."*

**Reader A** — `vacuous`, no secondary, conf 0.90, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-behind-broker.md:57 — "(2) requires `HTTPS_PROXY` (or `https_proxy`) to be set to `http://<host>:<port>` and `NODE_EXTRA_CA_CERTS` to an existing file, else `die 5`" ; Step 1 test list, same file:61 — "`--broker` without `HTTPS_PROXY` → exit 5; with a default route via another gateway → exit 5" (no CA-side case named at all).
- *Review:* docs/reviews/2026-09-05-opus-review-sb4-SB2.md, Findings/MAJOR-1: "The plan's Interfaces line names `NODE_EXTRA_CA_CERTS` alongside `HTTPS_PROXY` in the same `die 5` clause; the Step-1 test list names only the `HTTPS_PROXY` case, which is how this got missed — the implementation itself is correct."
- *Reasoning:* Strongest case for implementer: Interfaces states a concrete input→die-5 mapping for CA, parallel in structure to the tested HTTPS_PROXY clause — arguably concrete enough to derive the deletion mutant without spelling it out, making the omission a test-authoring lapse under TDD, not a plan gap. But the review itself says "the implementation itself is correct" — nothing deviated from spec, a test simply doesn't exist — and Step 1, the plan's actual test-enumeration section, names only HTTPS_PROXY, never CA. Per §3's rule and the RT1 precedent ("an Interfaces line without a named test is decoration"), a requirement stated only in Interfaces without a per-item deletion mutant in Tests/Step 1 is requirement-only, not mutant-named. Appendix B's own line for this row confirms: "a deletion mutant per contract item was the sentence the plan needed."

**Reader B** — `vacuous`, no secondary, conf 0.95, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-behind-broker.md:57 — "(2) requires `HTTPS_PROXY` (or `https_proxy`) to be set to `http://<host>:<port>` and `NODE_EXTRA_CA_CERTS` to an existing file, else `die 5`"; and line 61's Step-1 "Failing tests" list, which enumerates the mode-000 key case, the missing-`HTTPS_PROXY` case, the wrong-gateway route case, the `--bind-namespace` cases and the deprecation line — and never mentions `NODE_EXTRA_CA_CERTS` at all.
- *Review:* docs/reviews/2026-09-05-opus-review-sb4-SB2.md — "MAJOR-1 — the `NODE_EXTRA_CA_CERTS` half of contract item (2) has no test... mutation M-C2 deletes both lines; `nix develop -c bats tests/unit/70-dsh-openrouter.bats` is 95/95 green with the guard gone... The plan's Interfaces line names `NODE_EXTRA_CA_CERTS` alongside `HTTPS_PROXY` in the same `die 5` clause; the Step-1 test list names only the `HTTPS_PROXY` case, which is how this got missed — the implementation itself is correct."
- *Reasoning:* The plan's Interfaces line states the requirement but Step 1's test enumeration — the section that must name mutants per M13 — omits NODE_EXTRA_CA_CERTS entirely, not even as a proof-shape phrase. That's requirement-only, weaker than B1b's case (which at least named a proof shape). The seat implemented the requirement correctly and shipped every test the plan asked for; nothing it did could have caught this. Appendix B's own worked row for sb4·SB2 records exactly this pattern as vacuous ("a deletion mutant per contract item" is the missing sentence), and the reviewer's own words ("the implementation itself is correct") rule out implementer. Control row confirmed.

**Reader C** — `vacuous`, no secondary, conf 0.93, rule `requirement-only`.

- *Plan:* docs/superpowers/plans/2026-09-05-seat-behind-broker.md:57 — "(2) requires `HTTPS_PROXY` (or `https_proxy`) to be set to `http://<host>:<port>` and `NODE_EXTRA_CA_CERTS` to an existing file, else `die 5`;" and, in the Step-1 test list, docs/superpowers/plans/2026-09-05-seat-behind-broker.md:61 — "`--broker` without `HTTPS_PROXY` → exit 5; with a default route via another gateway → exit 5;" (no CA case, no mutant, and the section carries no mutation table)
- *Review:* docs/reviews/2026-09-05-opus-review-sb4-SB2.md:250-253 — "The plan's Interfaces line names `NODE_EXTRA_CA_CERTS` alongside `HTTPS_PROXY` in the same `die 5` clause; the Step-1 test list names only the `HTTPS_PROXY` case, which is how this got missed — the implementation itself is correct."
- *Reasoning:* Decisive question: the section names the requirement (Interfaces item 2) and no mutant — it has no mutation table, and its Step-1 list enumerates tests, omitting the CA case entirely. Deleting the guard leaves 95/95 green, so the suite cannot fail on that contract item: vacuous, as ledger and control classifier agree. No implementer secondary: the seat implemented the guard correctly and shipped every test the plan enumerated; unlike B1b, it satisfied no named mutant it then evaded.

**Outcome — hold.** The control behaves: three readers, unanimous with the
ledger and with the classifier, no secondary. The panel is not simply
ledger-confirming by construction — on a row where the classifier agreed, it
agreed too, and on sb5 · SB2b its own decider broke from the ledger.

---

## Ledger changes

The convergence rule yields **no relabel** and **eight secondaries**. Each is
`plan_defect_secondary = "implementer"` added to a row that has none; every
primary is unchanged, and no other field of any row changes.

| # | row | change |
|---|---|---|
| 1 | cr8 · CR2 | add `plan_defect_secondary = "implementer"` |
| 2 | og1 · OG1b | add `plan_defect_secondary = "implementer"` |
| 3 | og3 · OG1r | add `plan_defect_secondary = "implementer"` |
| 4 | og4 · OG1r2 | add `plan_defect_secondary = "implementer"` |
| 5 | rt1 · RT1 | add `plan_defect_secondary = "implementer"` |
| 6 | rt2c · RT2 | add `plan_defect_secondary = "implementer"` |
| 7 | sc5 · G11 | add `plan_defect_secondary = "implementer"` |
| 8 | cr17 · CR2rb | add `plan_defect_secondary = "implementer"` |

Rows held unchanged: cr15 · CR2r and bk3 · B1b (both already carry the
`implementer` secondary the panel names), ev1 · R5, og1 · OG1, rt5 · RT5,
rt5 · RT5b, sb5 · SB2b, sc4 · G8b, and the control sb4 · SB2.

The orchestrator applies the eight by a commit citing this file. **Nothing else
changes** — not `plan_defect` on any row, not Appendix B, not the spec.

## What the re-read says about the rule

Sixteen of the seventeen rows turned on **requirement-only**: the decider found
a plan section that named the requirement — or, as in bk3 · B1b and rt2c · RT2,
a proof shape — and no mutant, no one-line change the shipped test had to go
red on. Not one row of the sixteen produced a plan section that named the
mutant for the requirement the seat then missed; in row after row the exposing
mutant is textually present only in the *next* section — B1c, RT2b, RT5b,
SB2r, CR2r2, G8c, OG1r — written after the gate that found it. The single
exception is sb5 · SB2b, where the Opus decider applied `other` and called the
octet-range escape a violated affirmative contract; both advocates read the
same clause as a requirement whose only named mutant ("validation removed")
the seat did kill, and the row holds two to one. So the classifier's
one-directional pull is a **taxonomy ambiguity, not a ledger error**: it scores
"the plan named the requirement, the seat failed it" as sufficient for
`implementer`, which is the pre-2026-09-07 reading of the enum — and the
ledger, written under the house rule, is right on 17 of 17 primaries by the
convergence rule and on 16 of 17 by every reader individually. What the
classifier *did* find, consistently, is real: eight rows were carrying a plan
class alone where the seat had also deviated on its own account, and those
eight now gain the secondary. The audit's value is that secondary, not the
primary it proposed.

**Proposed tie-break sentence for §7**, if the panel's readings are adopted:
*`implementer` is the primary only when the plan named the **mutant** for the
requirement the seat missed (or the seat violated a contract stated verbatim in
the section it was given, and could have satisfied it as written); when the
plan named only the requirement or a proof shape, the primary is the plan class
the gap fits — `vacuous` if the shipped test cannot fail on a named
requirement, `missing-case` if the case is never named, `underspecified` if the
contract is left open — and `implementer` is recorded as the secondary whenever
the seat's own execution independently fell short.*

## Cost

17 rows × 3 readers = **51 reader turns** (two Sonnet advocates and one Opus
decider per row, each reading the row's review, the plan section it names, and
the spec's §7 and Appendix B), plus **this synthesis** — 52 agent turns in all.
The upstream audit that produced the sixteen candidates cost 1.56 M flat-rate
tokens over 66 rows (`docs/reviews/2026-09-08-plan-defect-audit.md`); this
re-read is the reason eight of its rows change and nine do not.
