# Plan 2026-09-11 — Knowledge (KN): the audit's second half, CLAUDE.md and AGENTS.md generated, the board a derived page, the brief re-ratified

**File:** `docs/superpowers/plans/2026-09-11-knowledge.md` — the path `docs/ledger/subsystems.toml:262` pre-seeds (a `KN` key elsewhere is refused, `pkgs/evidence/tasks.py:1835-1849`). Keys KN11–KN20; KN10 withdrawn by the audit (5b) — EV10 writes its two manifest lines, so no `### KN10` heading exists and nothing here touches `docs/ledger/subsystems.toml`.

**Charter:** `docs/concepts/2026-09-09a-redesign-charter.md` §2 row Knowledge (`:53`), §4 the invariants under review (`:75-86`), §5 mechanics (`:88-140`), §6 increment 1 "the rules audit (KN, docs then code)" (`:158-165`) and increment 4 (`:183-189`).

**Decisions:** `docs/decisions/2026-09-09-redesign-answers.md` 49d, 50a, 51a, 52a, 53a, 54a, 55a, 59a, 60a (`:62-73`, the row's own list); the departure note on 49 (`:104`); §4 OpenRouter-only (`:114-158`); §5 the lane drafts (`:160-185`); §6 Fable through the lane and the ZDR trade (`:187-246`, the rule text that crossed the chokepoint to draft this plan is the operator's recorded trade, `:210-229`). Relied on beside them: 53a deferred (A22); 7a/G9 — `**areas:**` on every cross-area task; 63a/G7 — the `KN` prefix and the pre-seeded file; 36a — AGENTS.md in-tree; 35b, 44, 48a — the absorption KN16 waits on (A26); 58a — SA5's marker is KN12's (A24); 70b — `## Operator` composes into the increment's drill.

**Context block:** `docs/context/knowledge.md` §1–§6 and its 2026-09-11 delta. Every figure below carries its command; re-run at `920ef3e` by the fill and at `662e87f` by the 2026-09-14 revision (two had moved: Assumptions 9 and 12).

**Program plan:** `docs/superpowers/plans/2026-09-09-program.md` — G1–G12 quoted verbatim in `## Global Constraints` below, because `factory-brief` reads that section from the plan file itself (`tools/factory/seat/factory-brief:51-52`).

**Author:** Fable 5.1 — outline 2026-09-11, fill on the OpenRouter lane (seat `knowledge-again`), revision 2026-09-14 against `docs/reviews/plan-judgements/2026-09-12-batch-knowledge.md` (32/42; errata table `~/factory/batch/2026-09-11/drafts-r2/knowledge.errata.md`).

**Status:** revised draft — every task body typed; nothing dispatched; the operator lands this file under `docs/superpowers/plans/` deliberately, then `nix develop -c python3 pkgs/evidence/tasks.py --root . check`.

**Increment:** KN11–KN14, KN19, KN20 are increment 1 ("docs then code"); KN15–KN18 are increment 4 and dispatch against the landed tree, as charter §5 requires.

## Operator questions

Three. Each carries its bound, its recommendation and what changes in which task on each answer; a question unanswered at dispatch takes its recommendation. Every other question the outline raised is an Assumption below (A20–A32), applied as the draft itself recommended and open to veto there — none was resolved silently.

- **Q1 — The verdicts (§5.3).** All 63 `verdict` fields are empty by design (`docs/ledger/rules.toml:11`); only the operator fills them. *Bound:* `keep | amend | retire` per row, batched by class (invariant 6, guard 14, convention 12, practice 28, ritual 3); an `amend` carries its text. *Recommendation:* answer the six `invariant` rows and the 16 owed-check rows (22 answers), the other 41 default to `keep`; recorded as `docs/decisions/<date>-rules-verdicts.md` before kn2. *On all `keep`:* KN14 writes `keep` everywhere and deletes only A27's rows plus KN13's (c) row. *On an `amend`:* the source's owner applies the text — KN15 (`CLAUDE.md`), KN18 (§3, A21), KN16 (AGENTS rows). *On a `retire`:* KN14 deletes the row and re-pins. *Holds:* KN14, KN16, KN18.
- **Q4 — Where the generator lives and where AGENTS.md is written (§5.4, §5.7).** *Bound:* (a) `pkgs/evidence/rules.py generate` — one schema, one file, the same `--root`, `areas: knowledge, evidence` — or (b) a Knowledge-owned `tools/rules-gen.py` with its own `owns` row and a second TOML reader; AGENTS.md in-tree at the payload's path after the absorption (36a), never in the sibling git. *Recommendation:* (a), and `pkgs/dsh-openrouter/AGENTS.md`. *On (b):* KN15/KN16 swap the touch for `tools/rules-gen.py`, drop `evidence` from `areas`, and an `owns` line is owed to EV10's file — a cross-plan row bought, not saved. *A different AGENTS.md path* changes KN16's created file and its `lint` line only. *Holds:* KN15, KN16.
- **Q5 — When the board freezes (§5.6).** KN17 reduces the file to a fixed header plus the derived block; every later landing changes only the block. *Bound:* first wave (before the other eight plans land) or last (after every KN key). *Recommendation:* first — what 50a asks for, and it removes the source of G5's twice-flagged undeclared-touch confusion. *On "first":* `dependsOn: none`, wave 1 as derived. *On "last":* KN17's `dependsOn` becomes every other KN key at landing and it forms a fifth wave. *Holds:* KN17.

## Charter-to-task map

| Charter clause | Task |
|---|---|
| §4 "one dated ruleset file with a verdict per rule" (`:83-84`) | KN14 (verdicts applied), KN11 (completeness tripwire) |
| §4 "a check per load-bearing rule" (`:84`), 54a | KN13 |
| §4 "a rule with no check and no measurement is deleted, not date-stamped" (`:85-86`), 54a | KN14 |
| §4 "CLAUDE.md and AGENTS.md generated from it" (`:84-85`), 59a; §6 increment 4 (`:186-187`) | KN15 (CLAUDE.md), KN16 (AGENTS.md, its commit section from `policies.md` per 52a) |
| §6 increment 4 "the handoff-only narrative" (`:187`), 50a, 51a | KN17 |
| §6 increment 4 "the renumbered phases" (`:187`), 55a, the departure note on 49 | KN18 |
| §2 row "the ritual" (`:53`), 60a | KN12 |
| §4 "every one of the six §3 invariants holds verbatim … until the audit lands" (`:78-80`) | KN18 re-ratifies only after KN14; nothing before KN18 edits §3 |
| §5 "The record" (`:133-136`): an area on every row, refusals for undeclared touches | KN19 (the wiring file under test), KN20 (the missing rejection row); the manifest rows are EV10's |

## Global Constraints

Quoted verbatim from `docs/superpowers/plans/2026-09-09-program.md:35-46` (that file's order): `tools/factory/seat/factory-brief:51-52` extracts this H2 from the plan file alone. G10 does not bind (no Nix module, no new language; KN13 reads `hosts/core/hardware-configuration.nix`, never edits it) and is not quoted. G4's area word is `knowledge:` throughout; G5's exemptions are why KN11, KN13, KN15 and KN16 regenerate `docs/MAP.md` unnamed.

- G1 (`program.md:35`): **G1 Build-only.** Never `sudo`, `nixos-rebuild`, `systemctl start|stop|restart|enable|kill`, basket mount or teardown. The operator switches; a task that needs the live system to change says so in its `## Operator` line and stops.
- G2 (`program.md:36`): **G2 Red first.** Every check or test a task adds is shown failing before the change that makes it pass, and the red output is pasted in the commit body. A load-bearing test counts only once it has failed (CLAUDE.md).
- G3 (`program.md:37`): **G3 Trailers.** Both trailers, in this order: the machine-set `Generated-By:` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` (`docs/board/policies.md:30-36`, decision 52a). A gate reads the implement model from the task's own `.result` (FIX7, `6a84fae`).
- G4 (`program.md:38`): **G4 Subject.** `<area>: summary (test: <check names>)`, the area being the subsystem's prefix in lower case once PR1 lands (`evidence:`, `factory:`, `isolation:`, `knowledge:`, `program:`), the check names being exactly the task's `acceptance` list. Guarded twice: the workspace's `commit-msg` hook that `factory-ws` installs (`tools/factory/seat/factory-ws:131-136`, `factory-commit-msg.sh`) and the gate's convention section, which compares the subject byte for byte with the section's `commit subject` line.
- G5 (`program.md:39`): **G5 Touches.** Edit only the files the task's `touches` names; a new file is named there too. An undeclared touch demotes the result (`factory-task:857-861`). `git add` every new file before any `nix build` (flakes see tracked files only). **One standing exemption, added 2026-09-10 after it was flagged twice:** the *derived queue block* of `docs/OPERATIONS.md`, and nothing else in that file, when the pre-commit's G8c forces its regeneration — G6 orders that regeneration, so listing the file in every task's `touches` would be noise and omitting it made the gate read a forced, derived, machine-written hunk as an undeclared touch (HH3's minor, PR1's MAJOR). A gate treats a queue-block-only diff there as declared; any other hunk in that file is an undeclared touch as before, and board prose stays the orchestrator's (the rule that refused W6b at the integrator). **`docs/MAP.md` is exempt on the same ground and for the same reason** (KN1's minor): `lint` asserts it is current (`flake.nix:1081-1086`), so any task that adds or renames a module, package, check or test must run `python3 pkgs/evidence/repomap.py --root . write` and commit the result whether or not its `touches` names the file. Both exemptions cover *derived* files a check or hook forces; neither excuses a hand edit.
- G6 (`program.md:40`): **G6 Commit route.** `nix develop -c git commit -F <msgfile>` on `task/<KEY>`; one commit per task. **A fix round that starts by cherry-picking its predecessor folds that cherry-pick into its own single commit** (`git cherry-pick -n`, or `git reset --soft` back to the base before committing) — added 2026-09-10 after the instruction proved ambiguous: PR1b's seat folded and PR1c's did not, and `factory-task:757` demoted the second for claiming one commit where the branch carried two. The chain's history lives in the plan and the reviews, not in a stack of replayed commits on one task branch. If the pre-commit refuses only on G8c (a stale board queue block), regenerate with `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board` and include the block in the same commit; never `--no-verify`.
- G7 (`program.md:41`): **G7 Reserved prefixes** (decision 63a): `IS PL HM SA FA EV GN KN PR` and the two-part keys `SPEC-<XX>`, `PLAN-<XX>`. No other plan may define a key under them. **EV2 landed this guard on 2026-09-10 (`f31b8bb`, integrated `776b492`); it is live and no longer a sentence a reviewer enforces by reading the key.** `tasks.py check` refuses a key whose leading letters match a manifest prefix when its plan file matches none of that subsystem's `plans` globs (`pkgs/evidence/tasks.py:1835-1849`), beside the older refusal of a key defined in more than one plan (now `:1758-1766`). `reserved_prefix` reads the letters before the first digit or hyphen, so `SPEC-<XX>` and `PLAN-<XX>` resolve to `SPEC`/`PLAN`, match no manifest row, and pass. The practical consequence, paid for on 2026-09-10: a subsystem's `plans` list must name a plan file BEFORE that plan may hold keys under its prefix — the eight `2026-09-11-*.md` batch outputs were added to `docs/ledger/subsystems.toml` for exactly this reason. Fix rounds add a lower-case letter (`EV1b`); a re-key never reuses a landed key.
- G12 (`program.md:42`): **G12 Invariants** (brief §3, Assumption 13, re-ratified after the audit per decision 55a): every task here is written against the six verbatim. Where they bind: EV1 reads the broker's usage log locally and writes only the local store (3: nothing leaves the machine; 5: the timer is Nix configuration); EV5 changes a validator, never a credential field (2); IS1 changes no lane boundary and injects nothing (2, 3); IS2 reads and writes documents only, stores and redirects nothing (2, 3, 6); PR1, EV2, EV3, EV4, EV6, FA1, KN1 are configuration and ledgers reviewable in a diff (5); no task promotes agent-authored code between baskets (6); no task touches basket mounting (1) or adds imperative setup (4).
- G8 (`program.md:43`): **G8 Privacy.** Nothing leaves the machine. IS2 reads and writes nothing outside `docs/`; no credential, token or key is copied, moved, printed or redirected by any task in this plan.
- G9 (`program.md:44`): **G9 Areas.** From EV2 on, a task whose `touches` fall in two subsystems declares `**areas:**` with both; `tasks.py check` refuses it otherwise. **EV2 landed this on 2026-09-10 (`f31b8bb`); it is enforced in code, not by hand** (`pkgs/evidence/tasks.py:1823-1834`). The refusal fires only while a task's derived state is `ready`, `blocked`, `ran` or `running`, so a landed key is never refused retroactively, and it exempts exactly the twenty-five keys in `docs/ledger/areas-grandfather.toml` — a list frozen at `dbedfe9`, so a key typed later is refused like any other. Note the grandfather ledger is read from the repo's live path rather than the tree under `--root`, so inside a workspace it exempts nothing (`BUG-ledger-read-from-live-path`): declare `**areas:**` rather than relying on the exemption.
- G11 (`program.md:46`): **G11 Numbers.** Every integer a task pastes (row counts, line numbers, test counts) is re-run at commit time, not copied from this plan (concept 2026-09-08g). Guarded by the gate: the review rubric's "correct facts" row re-runs the commit body's commands, and a pasted integer that does not reproduce is a MAJOR (the record's `wrong-fact` class in `docs/ledger/plan-defects.toml`).

G12 here: every task is configuration, tests or documents reviewable in a diff (5); KN16 copies no key (2, 3); no basket, lane or promotion (1, 6).

## Assumptions

Measured by the context block, re-measured at `920ef3e` and at `662e87f` (2026-09-14); each re-run at commit time (G11). Items 20–32 are the outline's demoted questions and veto bullets, each with its cite, its bound and the surface where the operator changes it.

1. Only `KN1` and `KN1b` exist, both `landed`: `nix develop -c python3 pkgs/evidence/tasks.py --root . json` filtered by key prefix → `[('KN1','landed'), ('KN1b','landed')]`. KN11–KN20 collide with nothing (audit check 1: clean).
2. The manifest pre-seeds this plan's path and nothing else may hold a `KN` key: `sed -n '260,263p' docs/ledger/subsystems.toml`; `ls docs/superpowers/plans/2026-09-11-knowledge.md` → `No such file`.
3. 63 rules rows: `grep -c '^\[\[rule\]\]' docs/ledger/rules.toml` → `63`; per source `grep '^source' docs/ledger/rules.toml | sed 's/.*= "//;s/:[0-9]*"$//' | sort | uniq -c` → `docs/brief.md` 15, `CLAUDE.md` 14, `docs/board/operator-model.md` 10, `tools/orchestrator-guard.sh` 6, `pkgs/dsh-openrouter/hook-guard.py` 6, `~/flakes/dsh-harness/AGENTS.md` 4, `docs/runbooks/session.md` 4, `docs/board/policies.md` 4; classes `grep '^class' docs/ledger/rules.toml | sort | uniq -c` → practice 28, guard 14, convention 12, invariant 6, ritual 3. `check` values: `grep '^check = ' docs/ledger/rules.toml | sort | uniq -c` → `""` 46, `"unit"` 14, `"lint"` 3.
4. `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root .` → `owed: 16 load-bearing rules without a check`, `EXIT=0`; `rules.py --help` → `usage: rules [-h] {validate} ...` (no `generate`). `owed()` is `pkgs/evidence/rules.py:104-107`; `main` prints the count at `:224` and returns `1 if errs else 0` at `:225`. Verbatim is `--verbatim` (`docs/ledger/rules.toml:14`); the row's `source` is `path:line`, and `validate` asserts the cited line contains a word of the text (`rules.py:196-205`), so an edit that shifts a sourced line is a ledger edit too.
5. Every `verdict` is empty by design: `sed -n '11p' docs/ledger/rules.toml`. The enum is `'' | keep | amend | retire` (`rules.py:180`).
6. Mutant F survived — deleting one row leaves `evidence-unit` at `550 passed`: `sed -n '444p' docs/reviews/2026-09-10-opus-review-pr1e-KN1b.md`. The only completeness test is `test_every_named_source_has_a_row` (`tests/evidence/test_rules.py:193-219`), per source.
7. `subsystems-manifest` is red for ten paths and `flake.nix:1532` is its only caller; EV10 turns it green. No KN task names it in `acceptance`.
8. `docs/ledger/rules.toml` is Evidence's (`docs/ledger/subsystems.toml:202`); no Knowledge `owns` row names `docs/ledger/*` (`:230-258`); `grep -c KN docs/ledger/areas-grandfather.toml` → `0`. Areas of the other touched paths, from the manifest: `flake.nix` platform (`:60`), `githooks/*` platform (`:65`), `tests/lint/*` platform (`:81`), `tests/evidence/*` evidence (`:184`), `docs/reviews/*` evidence (`:192`), `pkgs/dsh-openrouter/*` seat (`:128`), `tests/unit/90-session-start.bats` knowledge (`:256`).
9. Four checks copy or assert Knowledge paths — `lint` (`flake.nix:1313`; one `## START HERE` and ≤160 lines at `:1352-1359`; the Now paragraph at `:1363-1364`; `tasks.py … check` at `:1386`; `repomap.py --root . check` at `:1393`), `unit` (`:2876`; copies at `:2932-2947`), `evidence-unit` (`:1473`; copies at `:1505-1511`, `pytest tests/evidence -q` at `:1512`; it copies `tests/evidence` whole at `:1488` and `docs/ledger` whole at `:1491`, so `rules.toml` is in its sandbox), `claims-validate` (`:1589`), `ledger-unit` (`:1605`; copies `docs/ledger` to `docs-ledger` and runs `pytest tests-ledger -q`): `grep -nE '^ *(lint|unit|evidence-unit|claims-validate|ledger-unit) =' flake.nix`.
10. No check parses the repo's `.claude/settings.json`: `grep -rn "\.claude/settings\.json" flake.nix tests/` → prose plus `managed-settings-user-scope` (`flake.nix:2820-2849`, a different file). The file wires four events: `sed -n '5,9p;17,21p;32p;40,54p' .claude/settings.json`.
11. `tools/ritual.sh` exits 0 under `FACTORY_RUN` at `:15`, dispatches at `:472-475`; `tools/session-start.sh:18` has the same exit; `wc -l tools/ritual.sh` → 480; `wc -l tests/unit/92-ritual.bats` → 918; the existing silent case is `tests/unit/90-session-start.bats:63-67` (`env -i … FACTORY_RUN=ev3`).
12. The board: `wc -c docs/OPERATIONS.md` → two orders of magnitude above `SESSION_START_CAP_BOARD` (2300) and different at every landing (126,320 at `920ef3e`, 111,847 at `662e87f` — never quoted as a fact, only bounded by KN17's probe), `wc -l` → 70; markers `<!-- tasks:begin -->` at `:26`, `<!-- tasks:end -->` at `:37` (`BEGIN, END` at `pkgs/evidence/tasks.py:141`); `## START HERE` at `:10`, `## Log` at `:67`; `SESSION_START_CAP_BOARD` 2300 (`docs/runbooks/session.md:58`); `render_board_block` (`tasks.py:2307`) buckets only `ready`, `blocked`, `running`, `rejected`; `write_board` (`:2363`) replaces only the marked block. `session-start.sh:91-92` prints the START HERE section by `awk`.
13. The trailer texts contradict: `sed -n '31,35p' docs/board/policies.md` (two trailers) vs `sed -n '45,46p' ~/flakes/dsh-harness/AGENTS.md` (one, no `Co-Authored-By`).
14. The brief: `grep -n superseded docs/brief.md` → one hit at `:95`, unrelated; headings `grep -n '^## ' docs/brief.md` → §0 `:8`, §1 `:20`, §2 `:52`, §3 `:64`, §4 `:83`, §5 `:181`, §6 `:242`, §7 `:263`, §8 `:312`, §9 `:333`, §10 `:353`. `test_every_named_source_has_a_row` reads those `## N.` headings for §3/§8 bounds (`tests/evidence/test_rules.py:183-190`). `grep -c 'docs/brief.md' docs/ledger/claims.toml` → 0.
15. MINOR-3: `grep -n verbatim docs/runbooks/session.md` → no hits; `grep -n 'rules.py' docs/runbooks/evidence.md` → no hits; the runbook's sections are `grep -n '^## ' docs/runbooks/evidence.md` (`## Task areas` at `:87`, `## The plan-defect ledger` at `:110`).
16. The defect ledger: `grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml` → 82; last row at `:627` (`sd11b/SD11b`, `date = 2026-09-08`); `grep -n "KN1\|Knowledge"` → none. The validator is `pkgs/evidence/tasks.py:1655-1665` (`review missing` / `no such review`), run by `lint` at `flake.nix:1386`; the review H1 grammar is `REVIEW_RE` (`tasks.py:96-98`), the front-matter keys `REVIEW_BLOCK_KEYS` (`:117-127`), the class enum `PLAN_DEFECT_ENUM` (`:99-107`). `evidence-unit` pins the seed ledger (`flake.nix:1497-1498`), so a new live row is invisible to it and visible to `lint` and `ledger-unit`.
17. The rework review `~/factory/runs/pr1b/KN1.review.md`: 126,082 bytes, mtime Sep 10 12:45; `grep -n 'FACTORY-REVIEW'` → `:1331 FACTORY-REVIEW verdict=rework`; the review proper `:1266-1331` (`grep -n '^## '`), its defect list `:1313-1330` → one blocker, four majors, three minors; 24 `dsh: reasoning:` lines precede it.
18. The blast radius: 95 non-`KN` keys in this repo touch Knowledge-owned paths, so every touch on `CLAUDE.md`, `docs/OPERATIONS.md`, `docs/runbooks/*`, `tools/ritual.sh`, `tools/session-start.sh` is declared exactly.
19. `docs/MAP.md` `## Tests` lists `tests/evidence — 102 files` and `tests/unit — 28 files` (`sed -n '98,113p' docs/MAP.md`); `repomap.py` counts tracked files (`pkgs/evidence/repomap.py:139-150`), so a task adding a test file regenerates the map under G5's exemption.
20. (was Q2) The 16 owed checks take KN13's table — per id (a) an existing check, (b) one `lint` assertion, (c) retire — and `owed > 0` becomes the `rules-owed` check, never a validator exit change (`rules.py:225`, Evidence's). The draft's recommendation, unopposed; veto surface: by id in KN13's table before kn1.
21. (was Q3) All six §3 invariants `keep`: the operator chose full reopening (49d) over keeping them (`docs/research-2026-09-09-redesign-loose-ends.md:493-494`), and the reopening *is* the review — KN18's line is its record; an `amend` is applied in §3 in place with the row's `text` updated. Veto surface: a Q1 answer naming an invariant `amend`.
22. (was Q6) `plan-append` / `plan-withdraw` (53a) out: the denial is Isolation's, the caller Factory's, neither draft carries the verbs — recorded under Not in this plan. Veto surface: type `KN21`, `areas: knowledge, isolation`.
23. (was Q7) KN20 files KN1's rejection here (audit item 7: Evidence's outline never names `KN1` or `pr1b`). Veto surface: a withdrawn-status row for KN20.
24. (was Q8, and the marker veto bullet) The discriminator is `SEAT_MODE`, which SA5 exports for every seat (`outline-seat-harness.md:20`; SA5 Interface 1: `{headless, web, drive}`): unset or `drive` runs the ritual, anything else exits 0, `FACTORY_RUN` keeps `:15`; nothing reads it today (`grep -rn SEAT_MODE pkgs tools` → none). Veto surface: a Knowledge-named variable — one name in KN12.
25. (was Q9) (b): KN17 keeps `## START HERE` as the header's second line and rewrites `tests/lint/now-paragraph.sh` in place, so `githooks/pre-commit:43-54` (Platform's twin of `lint`'s three board assertions) is untouched and its `grep -c '^## START HERE'` stays 1. Veto surface: (a) adds `githooks/pre-commit` to KN17's `touches`.
26. (was Q10) `PL5` is in KN16's `dependsOn` — the recommendation "add at landing", applied now because the nine land in dependency order; Step 0's precondition stays as the seat's own check. Veto surface: remove `PL5`.
27. (was Q11) 54a read literally (charter `:85-86`, "deleted, not date-stamped"): KN14 deletes the 27 rows with `check = ""`, `load_bearing = false` and `measured` starting `UNMEASURED` (`tomllib` at `662e87f`: 43 `UNMEASURED`, 27 in the intersection — seven brief §8, five CLAUDE.md, four AGENTS.md, two policies, nine operator-model preferences); a preference wanted as a rule gets a `keep` with a measurement (Q1); `operator-model.md` itself keeps its text. Veto surface: (b) delete only `retire` rows — drops KN14's Interface 2 and its test.
28. Per-rule completeness (§5.1): a pinned count per source in KN11's file, re-pinned by KN14 and KN18; EV17 pins per rule in `tests/evidence/test_rules.py` — no collision, whichever lands second finds mutant F dead (KN11 Step 1 records which). Veto surface: withdraw KN11 if EV17 lands first.
29. Renumbering is not its own task (§5.8): markers and renumbering shift the same `docs/brief.md` lines; KN18 re-anchors once.
30. "Generated, not written" (§5.6) is `lint` refusing any byte outside header and block (KN17); the pre-commit's G8c keeps the block current; G5's exemption becomes total by construction.
31. Manifest horizon (§5.14): nothing — EV10 claims `docs/context/*`, the grandfather ledger and `docs/superpowers/plans/*`; KN11–KN20 create files only under owned globs (`tests/evidence/*`, `docs/reviews/*`, `pkgs/dsh-openrouter/*`); `docs/research-*` is Knowledge's (`:238`).
32. Uncovered docs (§5.13): review stays the only gate on the 34 concepts, 16 research files and ten runbooks; no docs lint this increment.

## Waves

Derived, not intended: `tasks.py waves --json` with this draft attached to the live graph (2026-09-14) → `[[["KN11"], ["KN12","KN13","KN17","KN19"], ["KN20"]], [["KN14"]], [["KN15","KN18"]], [["KN16"]]]`. Wave 1 is three groups — KN11 alone, KN20 alone, KN12/KN13/KN17/KN19 serialised by touch overlap (`flake.nix`, `docs/runbooks/session.md`, `tests/unit/90-session-start.bats`, `docs/ledger/rules.toml`); KN14, KN15/KN18 and KN16 are separated by `dependsOn`, not overlap. KN17 is wave 1 under Q5. KN16's `PL5` edge (A26) *resolves when the Platform plan lands*; a one-plan `check` reports it as an unknown key until then. The verbatim anchor makes every source-file edit a `rules.toml` edit too; the wave-1 serialisation is that cost, accepted rather than loosening Evidence's validator.

## Cross-plan

**Live hits** — `tasks.py conflicts` with this draft attached (2026-09-14): `flake.nix` — HH6, HH8, HH9 (`2026-09-08-helm-home-1.md`) and EV6 (`2026-09-09-program.md`) × KN13, KN15, KN16, KN17, KN19; `docs/runbooks/evidence.md` — EV3, EV4, EV6 × KN15 (IS5b, state `ran`, appears only under `--runs-dir /nonexistent` and lands first). Order: **HH6 → KN19 → KN13 → KN17** — HH6 is `ready` and shares wave 1's overlap group; attribute additions and one `cp` line against `helm-home` checks, textual only, the later rebases. **EV6 and HH8 before KN15, HH9 before KN16** — same derived waves, earlier-ready; KN15/KN16 each add one `lint` line. **EV3 → EV4 → EV6 → KN15 on `docs/runbooks/evidence.md`** — each adds its own H2 (KN15's `## The rules inventory` after `## Task areas`, `:87-109`); KN15 is wave 3 by `dependsOn` and lands last regardless.

**Sibling drafts** (keys exist only under `~/factory/batch/2026-09-11/drafts-r2/`; the nine land in dependency order):
- `flake.nix` — EV16 (`rules-validate`) **before KN13**: KN13 places `rules-owed` after it when it exists, else after `claims-validate` (`:1589`) and EV16 rebases; attribute additions only. KN19 before IS11/IS12/IS18/IS19/IS20, SA1/SA4/SA8, HM3, FA23, GN10–GN12, PL2–PL5 (attributes elsewhere; KN19's `cp` line inside `unit`, `:2932-2947`, is a block nobody else edits); KN17 after KN19 (same block).
- `docs/ledger/subsystems.toml` — no KN task touches it (KN10 withdrawn, audit 5b); EV10's `docs/superpowers/plans/*` glob makes this file and Q1's decision file Knowledge-owned.
- `docs/brief.md` — **KN18 before IS14** (Isolation's own recommendation, its draft `:103`): KN18 shifts every line after `:83`; IS14 rewrites §10 (`:353-357`) and rebases; if IS14 lands first KN18's Step 1 re-measures the headings.
- `docs/ledger/plan-defects.toml` — DF5, EV18, KN20 append rows; **KN20 first** (XS; `date` 2026-09-10 keeps the file chronological); the derivation groups the three.
- `tests/evidence/test_rules.py` — EV17 (`touches: tests/evidence`) and KN11 (A28): no file overlap.
- EV13 replaces the block's renderer, not the shape KN17 fixes; EV4 (`BUG-ledger-read-from-live-path`): KN14's ledger edits are proven on the integrated tree, where the gate re-runs; PL5 → KN16 (A26); SA5/SA6 export and read `SEAT_MODE`, SA6 calls the workspace's `tools/ritual.sh` — KN12 keeps path and verbs; SA9 (`docs/runbooks/seat.md`) and IS5/IS5b (`docs/runbooks/lanes.md`) touch nothing a KN task does.

## Operator

**Drill** (composed into the increment's drill per 70b; every command build-only, G1):

1. `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . --verbatim` — `owed: 0`, every row carries a verdict, the row count equals 63 minus the deletions KN14's commit body lists; `nix build .#checks.x86_64-linux.rules-owed -L --no-link` green.
2. Drift: change one rule's `text` in `docs/ledger/rules.toml`, run `nix build .#checks.x86_64-linux.lint -L --no-link` — red naming `CLAUDE.md` (and `pkgs/dsh-openrouter/AGENTS.md` after KN16); `git checkout docs/ledger/rules.toml`; green again.
3. `sed -n '64,82p' docs/brief.md` shows the re-ratification line with its date; `grep -n superseded docs/brief.md` → §4, §7, §9 marked; the phases read 1..N; the "test passed" gate verbatim.
4. `wc -c docs/OPERATIONS.md` under 2300; `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board && git diff --exit-code docs/OPERATIONS.md` clean; a hand-typed line outside the block turns `lint` red.
5. `FACTORY_RUN=1 tools/ritual.sh stop` exits 0 silently; `SEAT_MODE=job tools/ritual.sh stop` exits 0 silently; with `SEAT_MODE=drive` the Stop check runs; `nix develop -c bats tests/unit/92-ritual.bats` green.
6. `nix develop -c bats tests/unit/90-session-start.bats` green; point `Stop` in `.claude/settings.json` at a missing script → `unit` red; revert.
7. `ls docs/reviews/ | grep -i pr1b-KN1` and `grep -n 'key = "KN1"' docs/ledger/plan-defects.toml` — one file, one row.

**Rollback:** every task is one commit on `task/<KEY>` integrated by fast-forward; `git revert` of the integrate commit restores the previous board, `CLAUDE.md`, `docs/brief.md` and ledger, and the next landing regenerates the block. No task touches `nixosModules/*`, `hosts/*` or a basket: no switch, the live generation untouched; a bad `CLAUDE.md` generation is read only by the next session and undone by revert plus regenerate.

## Dispatch

Run names `kn1`–`kn4`; none exists under `~/factory/runs` (`ls ~/factory/runs | grep -x 'kn1\|kn2\|kn3\|kn4'` → empty, 2026-09-14; `BUG-run-name-reuse`, `program.md:122`). Preconditions: this file landed with `tasks.py check` clean before kn1; Q1's decision file before kn2 (else KN14 says `default: keep`); PL5 landed before kn4. Groups are the derived ones (`## Waves`); kn1's second group queues behind HH6 if it is running. Commit the regenerated board block before every dispatch (G6).

```
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-knowledge.md tools/factory/seat/factory-wave kn1 /home/dalhaka/nixos-agent-env "KN11" "KN12 KN13 KN17 KN19" "KN20" --then "gate each, integrate and fast-forward each"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-knowledge.md tools/factory/seat/factory-wave kn2 /home/dalhaka/nixos-agent-env "KN14" --then "gate KN14, integrate and fast-forward"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-knowledge.md tools/factory/seat/factory-wave kn3 /home/dalhaka/nixos-agent-env "KN15 KN18" --then "gate KN15 and KN18, integrate and fast-forward each"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-knowledge.md tools/factory/seat/factory-wave kn4 /home/dalhaka/nixos-agent-env "KN16" --then "gate KN16, integrate and fast-forward"
```

Per landing: fast-forward, `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board`, commit the block, `… waves --repo nixos-agent-env --next`. Gates at Sonnet (the manifest's `gate` for Knowledge), except KN13 and KN14 at Opus by the orchestrator's special case for a ledger whose contents are a contract for later code (`program.md:132`).

## Anticipation

- **What each landing unblocks** (`waves --json`): KN11 and KN13 → KN14; KN14 → KN15 and KN18; KN15 with PL5 → KN16; KN12, KN17, KN19, KN20 unblock nothing here.
- **The prepared relaunch**: a dead seat's diff stays in `~/factory/ws/kn<n>/<KEY>`; `FACTORY_PLAN=<plan> setsid -f bash -c 'exec tools/factory/seat/factory-wave kn<n>b /home/dalhaka/nixos-agent-env <KEY> >> ~/factory/runs/kn<n>b.wave.log 2>&1' </dev/null`, the fix round keyed `<KEY>b`.
- **No switch delta, no claim to close, no deny-rule table**: nothing touches `nixosModules/*`, `hosts/*`, a guard or a policy; `grep -c 'docs/brief.md' docs/ledger/claims.toml` → 0.
- **Hooks (A13)**: KN12 and KN19 carry their consumer tables with mutants. **Questions pre-asked**: Q1, Q4, Q5; none blocks kn1.
- **KN13 meets IS19 late**: IS19's `invariant-*` names replace today's when it lands (each `note` says so) — no fix round owed. **Numbers drift** (G11): KN14's counts and KN17's byte count are re-run; every probe is a bound, KN17's assertion a shape and a cap.
- **kn4 before PL5 lands**: `waves` refuses the unresolved edge first; a seat past that stops at Step 0, exit 4, naming PL5.

## Not in this plan

- KN10, withdrawn by the audit (5b): its two manifest lines are EV10's; if Evidence's Q1 is answered (b), the operator re-types KN10 (`**areas:** knowledge, evidence`) and EV10 drops the lines.
- `rules.py`'s validator semantics, `tasks.py`, `claims.py`, `docs/MAP.md`, the `evidence` binary, the status page and log: **Evidence** — KN13 wraps `owed` in a check; KN15/KN16 add `generate` under `areas: knowledge, evidence` and nothing else there.
- The guard and the `plan-append` / `plan-withdraw` verbs (53a): **Isolation** with **Factory** (A22); unowned after this batch, recorded so the omission is visible.
- `factory-review` reading `policies.md` (52a), the runner, the agent registry: **Factory**. The seat's hooks running the ritual scripts (58a), `SEAT_MODE`'s export, the seat's memory store, the payload build (36a), `hook-guard.py`: **Seat/Harness**. The dsh-harness absorption (PL5) and the sibling `AGENTS.md` before it: **Platform** — the trailer contradiction stands there until KN16.
- The other subsystems' compliance with the six invariants (G12): theirs; only the re-ratification is here (KN18).
- A docs lint over the 34 concepts, 16 research files and ten unreferenced runbooks; a `docs/context/*` content check; wider concept and decision globs (EV10's Q1). The Opus gate reviews' cost (UNMEASURED): Evidence's spend telemetry. `docs/research-2026-09-09-bug-workflow-packet.md`: covered by `docs/research-*` (`:238`).

---

### KN11 (code, S) — The rules inventory pins its per-source counts

**dependsOn:** none
**touches:** `tests/evidence/test_rules_completeness.py`
**acceptance:** evidence-unit
**commit subject:** knowledge: the rules inventory pins its per-source counts, so a deleted row is red (test: evidence-unit)

**Why.** Mutant F survived (Assumption 6): the only completeness test is per source (`test_every_named_source_has_a_row`, `tests/evidence/test_rules.py:193-219`), so deleting `R-policy-factory-economics` (63 → 62, `policies.md` 4 → 3) leaves `evidence-unit` at `550 passed`. Filed as MINOR-1, Knowledge's (`program.md:698`). Until a row deletion is red, KN14's deletions (54a) cannot be shown to be exactly the ones its commit body lists.

**Files.**
- Create `tests/evidence/test_rules_completeness.py`, opening with the shim `tests/evidence/test_rules.py:18-26` uses, pasted:
  ```python
  import pathlib
  import sys
  from collections import Counter

  HERE = pathlib.Path(__file__).resolve()
  sys.path.insert(0, str(HERE.parents[2] / "pkgs" / "evidence"))

  import rules

  ROOT = HERE.parents[2]
  ```
  then a module constant `EXPECTED_PER_SOURCE`, the eight measured counts keyed by source path with the `AGENTS.md` key matched by suffix as `test_rules.py:216-218` does; `EXPECTED_TOTAL = 63`; a helper `_assert_pinned(rows)` that builds `Counter(rules._source_parts(r["source"])[0] for r in rows)` and asserts it equals the pin; two tests (Interfaces 1–2) plus one fixture test (Interface 3). No other file changes: `evidence-unit` already copies `tests/evidence` whole (`flake.nix:1488`) and `docs/ledger` whole (`:1491`), so the new file runs under `pytest tests/evidence -q` (`:1512`) with the shipped ledger in the sandbox. `docs/MAP.md` regenerated under G5's exemption (`tests/evidence` 102 → 103 files).

**Interfaces.**
1. `test_per_source_counts_are_pinned`: the `Counter` of `_source_parts(row["source"])[0]` over the shipped ledger equals `EXPECTED_PER_SOURCE` exactly — a row added, deleted or re-sourced to another file fails with the two dicts in the assertion message.
2. `test_total_is_pinned`: `len(rows) == EXPECTED_TOTAL` and `sum(EXPECTED_PER_SOURCE.values()) == EXPECTED_TOTAL`, so the pin cannot drift from itself.
3. `test_pin_discriminates_on_a_fixture` (the negative control): a copy of the shipped ledger written to `tmp_path` with the `R-policy-factory-economics` block removed yields a `Counter` whose `docs/board/policies.md` entry is 3, and the assertion helper the two tests share raises `AssertionError` on it while accepting the untouched copy.
4. Re-pinning is a one-line edit of the two constants from Assumption 3's `uniq -c` command; KN14 and KN18 do this.

**Steps.**
1. **Red — reproduce mutant F, then show the new file's red.** `S=$(mktemp -d) && cp -r tests pkgs docs "$S"/ && cd "$S"`; delete the block with a `python3 - <<'EOF'` that splits `docs/ledger/rules.toml` on `\n[[rule]]\n`, drops the chunk containing `id = "R-policy-factory-economics"` and writes back; `grep -c '^\[\[rule\]\]' docs/ledger/rules.toml` → `62`; `EVIDENCE_UNIT_SANDBOX=1 nix develop ~/nixos-agent-env -c pytest tests/evidence/test_rules.py -q` → the `passed` line with **no failure** — paste it: the survived mutant. Still in `$S`, write the new file (Step 2) and run the same for `test_rules_completeness.py` → `FAILED …::test_per_source_counts_are_pinned - AssertionError: … 'docs/board/policies.md': 3 … expected 4`, `FAILED …::test_total_is_pinned - assert 62 == 63`; `2 failed, 1 passed`. Paste both. Record the EV17 pre-state (A28): `grep -c 'EXPECTED_PER_SOURCE\|per_source' tests/evidence/test_rules.py` in the real tree (`0` today; non-zero means EV17 landed first — the commit body says so).
2. **Write the file** in the real tree per Files, with `EXPECTED_PER_SOURCE` from the `uniq -c` command run at commit time (G11), not from this plan.
3. **Green.** `git add tests/evidence/test_rules_completeness.py`; `EVIDENCE_UNIT_SANDBOX=1 nix develop -c pytest tests/evidence/test_rules_completeness.py -q` → `3 passed`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` → builds, and the log's `passed` count is the Step-1 count plus 3 — paste it. `python3 pkgs/evidence/repomap.py --root . write` then `nix build .#checks.x86_64-linux.lint -L --no-link` → builds (the map is current). Acceptance: **evidence-unit** pasted.
4. **Mutants** (each on a scratch copy of the tree; kill = the named test fails):
   - **M1 — delete one row** (mutant F itself): the Step-1 deletion → `test_per_source_counts_are_pinned` fails naming `policies.md: 3`; `test_total_is_pinned` fails `62 == 63`.
   - **M2 — move a row between sources**: `sed -i '0,/^source = "CLAUDE.md:10"/s//source = "docs\/brief.md:10"/' docs/ledger/rules.toml` → `test_per_source_counts_are_pinned` fails (`CLAUDE.md: 13`, `docs/brief.md: 16`) while `test_total_is_pinned` passes — the two tests are independent.
   - **M3 — duplicate a row under a new id**: append a copy of the last `[[rule]]` block with `id = "R-dup"` → `test_total_is_pinned` fails `64 == 63`.
   - **M4 — break the pin's self-consistency**: set `EXPECTED_TOTAL = 64` in the new file → `test_total_is_pinned` fails on `sum(...) == EXPECTED_TOTAL`.
   - **M5 — control mutant**: in the fixture test, drop the deletion (write the copy untouched) → `test_pin_discriminates_on_a_fixture` fails with `DID NOT RAISE AssertionError`, proving the control discriminates.
5. **Commit** with the subject above; body: the Step-1 survived line, both red lines, the green `passed` count, and the five mutant outcomes.

**Tests (assertion → mutant; fixture → discriminating row).** per-source Counter equals pin → M1, M2; total equals 63 → M1, M3; pin self-consistent → M4; fixture (deleted-row ledger must fail, untouched copy must pass) → M5.

**probes:**
- rows: `grep -c '^\[\[rule\]\]' docs/ledger/rules.toml` :: ge 63 :: Assumption 3, measured 2026-09-14
- rows-exact: `grep -c '^\[\[rule\]\]' docs/ledger/rules.toml` :: le 63 :: exact count until KN14 lands, Assumption 3
- policies-rows: `grep -c '^source = "docs/board/policies.md' docs/ledger/rules.toml` :: ge 4 :: Assumption 3
- policies-rows-exact: `grep -c '^source = "docs/board/policies.md' docs/ledger/rules.toml` :: le 4 :: exact count, Assumption 3
- new-file-absent: `git ls-files tests/evidence/test_rules_completeness.py | wc -l` :: le 0 :: pre-state, G5 names the file as a new touch

### KN12 (code, S) — The ritual runs for the driver or orchestrator session only

**dependsOn:** none
**touches:** `tools/ritual.sh`, `tests/unit/92-ritual.bats`, `docs/runbooks/session.md`, `docs/ledger/rules.toml`
**acceptance:** unit, ledger-unit, evidence-unit, lint
**areas:** knowledge, evidence
**commit subject:** knowledge: the ritual runs for the driver or orchestrator session only, silent for a single-pass agent (test: unit, ledger-unit, evidence-unit, lint)

**Why.** Decision 60a (`docs/decisions/2026-09-09-redesign-answers.md:73`): "the driver or orchestrator session only; a single-pass agent's close-out is its artifact". Today `tools/ritual.sh` knows one non-session caller (`FACTORY_RUN`, `:15`); a seat launched without it — a judge, a drafter — gets the full Stop block on uncommitted reviews, noise a single-pass agent cannot act on. Nothing says *which* session this is (`grep -n 'SEAT_MODE\|FACTORY_RUN' tools/ritual.sh` → one hit, `:15`); SA5 exports `SEAT_MODE` for every seat (A24), so the discriminator exists on the launcher side only. The runbook's ritual section (`docs/runbooks/session.md:112-211`) does not say who the ritual is for, and four rows anchor to it (`:114`, `:127`, `:184`, `:442`; Assumption 3), so an inserted paragraph is a ledger edit.

**Files.**
- Modify `tools/ritual.sh`: after `:15`, one line — `case ${SEAT_MODE:-drive} in drive) ;; *) exit 0 ;; esac` — and the header comment `:6-7` says "silent for factory agents (`FACTORY_RUN`), single-pass seats (`SEAT_MODE` other than `drive`) and linked worktrees"; the dispatch at `:472-475` is unchanged, so SA6's call keeps working.
- Modify `tests/unit/92-ritual.bats`: four cases after `:158` (Interfaces 2–4), pasted — the `setup` at `:19-62` provides `$REPO`, `$__stdin`, `$XDG_STATE_HOME`, `$FACTORY_ROOT`; `env -i` is the same shape as the factory-agent case at `:150-158`:
  ```bash
  seat() { # seat MODE VERB... -- the ritual under SEAT_MODE=MODE, feeding $__stdin
    local mode=$1; shift
    run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
      XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
      RITUAL_EVIDENCE="$BATS_TEST_TMPDIR/bin/evidence" SEAT_MODE="$mode" \
      bash "$SCRIPT" "$@" <<< "$__stdin"
  }

  @test "stop is silent for a single-pass seat (SEAT_MODE=job)" {
    touch "$REPO/docs/reviews/x.md"
    seat job stop "$REPO"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  }

  @test "precompact is silent for SEAT_MODE=job" {
    seat job precompact "$REPO"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  }

  @test "stop still blocks for SEAT_MODE=drive on an untracked review" {
    touch "$REPO/docs/reviews/x.md"
    seat drive stop "$REPO"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"decision":"block"'* ]]
    [[ "$output" == *"docs/reviews/x.md"* ]]
  }

  @test "SEAT_MODE=job exits 0 with no verb, before the usage check" {
    seat job
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  }
  ```
- Modify `docs/runbooks/session.md`: one paragraph after `:119` (the end of the `## The reset ritual` intro, before `### The ten ordered steps`), a blank line after it, verbatim: `**Who the ritual is for (decision 60a).** The driver or orchestrator session only — a single-pass agent's close-out is its artifact. \`tools/ritual.sh\` exits 0 silently when \`FACTORY_RUN\` is set (a factory agent) or when \`SEAT_MODE\` is set to anything but \`drive\` (a job, judge or drafting seat); unset or \`drive\` runs it in full.` The insertion shifts `:127`, `:184` and `:442`.
- Modify `docs/ledger/rules.toml`: the three `source = "docs/runbooks/session.md:<n>"` values at `:762`, `:774`, `:786` re-anchored by the shift; `:750` (`:114`) is above the insertion and stays. `check` fields untouched (KN13's).

**Interfaces.**
1. `FACTORY_RUN` set → exit 0, no output, for every verb (unchanged, `:15`).
2. `SEAT_MODE` unset or `drive` → the verb runs as today (the orchestrator session and the driver seat).
3. `SEAT_MODE` set to any other value (`job`, `judge`, `draft`, …) → exit 0, no output, before any repo read; the untracked review that would block a drive session does not block.
4. The precedence is `FACTORY_RUN` first, then `SEAT_MODE`, then usage (`:16-19`): `SEAT_MODE=job bash tools/ritual.sh` with no verb exits 0, not 2.
5. `rules.py validate … --verbatim` passes with the four `session.md` rows resolving to the moved lines.

**Hook consumers (A13)** — consumer | interpreter and tree | `stop_hook_active` | degrade-to-allow | mutant. (1) `.claude/settings.json` `Stop`/`PreCompact` → the checkout's `tools/ritual.sh` under the session's `bash`, the board check running the tree's `pkgs/evidence/tasks.py` (`ritual.sh:145-157`) | honoured at `:174-179`, read *after* the new `case` line — a job seat exits before any input is parsed, a drive seat keeps the once-per-turn guard (`92-ritual.bats:799`) | `:148`, `:150`, `:157`, `:171`, unchanged | drop the `stop_hook_active` check → `:799` fails; `exit 1` on the new line → the job case fails on `$status`. (2) SA6's packaged seat hook → the workspace's `tools/ritual.sh`, same verbs and tree, `SEAT_MODE` from the unit environment SA5 exports | as (1) | as (1) | M2, the inverted match: a drive seat never sees the block.

**Steps.**
1. **Red.** Add the four bats cases first; `nix develop -c bats tests/unit/92-ritual.bats -f 'SEAT_MODE'` → `not ok … stop is silent for a single-pass seat (SEAT_MODE=job)` with `[ -z "$output" ]` failing (the Stop JSON block for `docs/reviews/x.md` is printed), `not ok … precompact is silent for SEAT_MODE=job` and `not ok … SEAT_MODE=job exits 0 with no verb` (status 2 from the usage check at `:16-19`); the `SEAT_MODE=drive` case passes already (Interface 2 is today's behaviour — the negative control; M3 shows it discriminates). Paste the three `not ok` lines. Then the runbook red: insert the paragraph, run `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root .` → `rules: R-ritual-file-commit-reviews: source line does not contain the rule text` (and the `:184`, `:442` rows likewise), `EXIT=1`. Paste.
2. Edit `tools/ritual.sh` per Files.
3. Re-anchor the three rows: for each, `grep -n '<first six words of text>' docs/runbooks/session.md` gives the new line; write it into `source`.
4. **Green.** `nix develop -c bats tests/unit/92-ritual.bats` → all `ok` (count = today's count + 4; today `grep -c '^@test' tests/unit/92-ritual.bats` → 51); `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . --verbatim` → `owed: 16 …`, `EXIT=0`; `nix build .#checks.x86_64-linux.{unit,ledger-unit,evidence-unit,lint} -L --no-link` → four builds. Acceptance: **unit, ledger-unit, evidence-unit, lint** pasted.
5. **Mutants:**
   - **M1 — drop the new `case` line** in `ritual.sh` → `bats … -f 'SEAT_MODE=job'` → `not ok`, output non-empty (the block JSON).
   - **M2 — invert the match** (`drive) exit 0 ;; *) ;;`) → the `SEAT_MODE=drive` case fails (`[ -n "$output" ]` on a repo with an untracked review — the drive case asserts the block IS printed) and the `job` case passes: kills the inversion.
   - **M3 — control**: in the `SEAT_MODE=drive` case, remove the `touch "$REPO/docs/reviews/x.md"` line → the case fails (`-n "$output"` false), proving the control depends on the fixture.
   - **M4 — wrong precedence**: move the `case` below the usage check at `:16-19` → the Interface-4 case (`SEAT_MODE=job`, no verb) fails with status 2.
   - **M5 — un-anchor a row**: revert one `source` in `rules.toml` to its old line → `evidence-unit`'s `test_shipped_inventory_validates` fails with `source line does not contain the rule text`; `rules.py validate` exits 1.
6. **Commit** with the subject above; body: the two `not ok` lines, the validator red, the green counts, M1–M5.

**Tests (assertion → mutant; fixture → discriminating row).** job-seat silent → M1; drive runs → M2; drive fixture discriminates → M3; precedence → M4; rows re-anchored → M5.

**probes:**
- marker-unread: `grep -c 'SEAT_MODE' tools/ritual.sh` :: le 0 :: pre-state, A24 (ge 1 after)
- factory-exit-kept: `sed -n '15p' tools/ritual.sh | grep -c FACTORY_RUN` :: ge 1 :: Assumption 11
- session-rows: `grep -c '^source = "docs/runbooks/session.md' docs/ledger/rules.toml` :: ge 4 :: Assumption 3
- session-rows-exact: `grep -c '^source = "docs/runbooks/session.md' docs/ledger/rules.toml` :: le 4 :: exact count, Assumption 3
- bats-cases: `grep -c '^@test' tests/unit/92-ritual.bats` :: ge 51 :: measured 2026-09-14 (55 after)

**Added context (2026-09-14, operator-dispatched worktree, not a replan).** A parallel session (chip task_f383579e) fixes tools/session-start.sh:175-177, which replays `tail -n 3` of a ritual.log last written 2026-09-08 — the three 'ritual:' lines at every session start are stale — with a bats case in tests/unit that seeds a stale line and asserts the hook omits it. Re-measure the script's line numbers and the bats file's case count at dispatch; merge that branch first if it has landed, and keep its test green.

### KN13 (code, M) — Every load-bearing rule names its check

**dependsOn:** none
**touches:** `docs/ledger/rules.toml`, `flake.nix`
**acceptance:** rules-owed, ledger-unit, evidence-unit, lint
**areas:** evidence, platform
**commit subject:** knowledge: every load-bearing rule names its check, and rules-owed refuses a non-zero owed count (test: rules-owed, ledger-unit, evidence-unit, lint)

**Why.** Decision 54a: every load-bearing rule gets a check. `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root .` → `owed: 16 load-bearing rules without a check`, `EXIT=0` — a count printed at `rules.py:224` and never a failure (`:225` returns 1 only on `errs`). The 16 ids (`python3 -c` over `tomllib`, rows with `load_bearing` and empty `check`): `R-invariant-basket-tmpfs`, `-credential-plaintext`, `-egress-chokepoint`, `-reproducible`, `-policy-nix`, `-no-promotion`, `R-practice-brief8-pin-inputs`, `R-practice-brief8-no-secrets`, `R-practice-hardware-config-verbatim`, `R-practice-tdd-red-first`, `R-conv-commit-subject`, `R-conv-queue-derived`, `R-conv-commit-trailers`, `R-practice-privacy-first`, `R-ritual-ten-steps`, `R-ritual-file-commit-reviews`. Only 17 rows name a check at all (`unit` 14, `lint` 3; Assumption 3). The validator's exit code is Evidence's (Not in this plan), so the refusal is a flake check that reads the printed count.

**Files.**
- Modify `docs/ledger/rules.toml`: the `check` field of 15 rows and the `load_bearing` field of one, per the disposition table below; `note` on each says `KN13: <a|b|c> — <why this check>`. No `text`, `source` or `verdict` changes.
- Modify `flake.nix`: one attribute `rules-owed` placed after `rules-validate` if EV16 has landed (`grep -n 'rules-validate =' flake.nix`), else after `claims-validate` (`:1589-1604`), pasted (`report`, not `out`: `$out` is the derivation's output path; the validator's exit is captured, since `runCommand`'s errexit would otherwise abort on `errs`):
  ```nix
  rules-owed = pkgs.runCommand "rules-owed" { nativeBuildInputs = [ ledgerPython ]; } ''
    mkdir -p pkgs docs
    cp -r ${self}/pkgs/evidence pkgs/evidence
    cp -r ${self}/docs/ledger docs/ledger
    report=$(python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . || true)
    owed=$(printf '%s\n' "$report" | sed -n 's/^owed: \([0-9][0-9]*\) .*/\1/p')
    [ -n "$owed" ] || { echo "rules-owed: the validator printed no owed: line" >&2; exit 1; }
    [ "$owed" = 0 ] || { echo "rules-owed: $owed load-bearing rules without a check (decision 54a)" >&2; exit 1; }
    touch $out
  '';
  ```
  Three `lint` additions. After `:1338`, the (b) rows: the pinned hash — `echo "<sha256>  hosts/core/hardware-configuration.nix" | sha256sum -c --quiet` (hash measured at commit: `sha256sum hosts/core/hardware-configuration.nix`) — and the secrets sweep as a rule with arms, not one vendor's spelling: `if grep -rEn -e 'sk-or-v[0-9]+-[A-Za-z0-9]{16}' -e 'sk-ant-api[0-9]{2}-[A-Za-z0-9_-]{16}' -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' -e 'AGE-SECRET-KEY-1[A-Z0-9]{16}' --exclude-dir=.git .; then echo "lint: secret material in the tree (brief §8): the lines above" >&2; exit 1; fi` — the arms mirror `pkgs/evidence/streams.py:100-102`'s `SECRET_RE` minus its prose-prone tokens (`Bearer `, `\beyJ`, `\bage1`); a new prefix goes into both in one commit; zero hits today (the fixtures at `flake.nix:779` and `test_streams_policy.py:727` are shorter than 16 alphanumerics after the prefix). After `:1390` (`sort ${checkNamesFile} >flake-checks`), Interface 3: `grep '^check = "' docs/ledger/rules.toml | sed 's/^check = "//;s/"$//' | grep -v '^$' | sort -u >rule-checks` then `if comm -23 rule-checks flake-checks | grep -q .; then echo "lint: docs/ledger/rules.toml names a check the flake does not define: $(comm -23 rule-checks flake-checks | tr '\n' ' ')" >&2; exit 1; fi`. `docs/MAP.md` regenerated (`repomap.py --root . write`) under G5's exemption — `lint` diffs the Checks section (`:1388-1391`).

**Disposition (A20; the operator vetoes by id):** (a) name an existing check — six `invariant` rows → `unit` (basket-tmpfs: `tests/unit/30-mount.bats`), `managed-settings` (credential-plaintext), `integration` (egress-chokepoint), `host-core` (reproducible), `assertion-negative` (policy-nix; no-promotion), each `note` saying IS19's `invariant-*` aggregate replaces the name when it lands; `brief8-pin-inputs` → `host-core`; `conv-commit-subject` → `unit` (`grep -c commit-msg tests/unit/94-seat-harness.bats` ≥ 1); `conv-queue-derived` → `lint` (`tasks.py … check` at `flake.nix:1386` refuses a stale block); `conv-commit-trailers` → `unit` (`tests/unit/80-seat-driver.bats:94-97`); `practice-privacy-first` → `integration`; `ritual-ten-steps`, `ritual-file-commit-reviews` → `unit` (`tests/unit/92-ritual.bats:78`). (b) one `lint` assertion — `hardware-config-verbatim` (the pinned hash), `brief8-no-secrets` (the key-shape sweep) → `lint`. (c) retire proposed — `practice-tdd-red-first`: review-gated, unmeasured, no check; KN13 sets `load_bearing = false` with `note = "KN13: (c) retire proposed — a keep verdict at KN14 must name a check"`, and KN14 deletes it under 54a unless Q1 says `keep` with a check. 13 + 2 + 1 = 16.

**Interfaces.**
1. `rules-owed` builds iff the validator's `owed:` line reads `0`; its failure text names the count and 54a.
2. `rules-owed` does not run `--verbatim` and does not fail on `errs` or on a validator exit of 1 (those are EV16's `rules-validate`); it fails on exactly two things — a non-zero count, or no `owed:` line at all (the vacuous arm).
3. `lint` fails when any non-empty `check` value in the ledger is not in the flake's check set — the same `checkNamesFile` list `lint` already diffs against `docs/MAP.md`.
4. `lint` fails if `hosts/core/hardware-configuration.nix` changes byte-wise or any of the four secret shapes appears in any tracked file.

**Steps.**
1. **Red.** Add the `rules-owed` attribute before editing the ledger: `nix build .#checks.x86_64-linux.rules-owed -L --no-link` → fails, log `rules-owed: 16 load-bearing rules without a check (decision 54a)`, exit 1. Paste. For the (b) assertions: apply them to `lint` and, on a scratch copy, `echo '# x' >> hosts/core/hardware-configuration.nix` then `nix build .#checks.x86_64-linux.lint` → `sha256sum: WARNING: 1 computed checksum did NOT match`; `echo 'sk-or-v1-abcdefghijklmnop0000' > tests/lint/fixtures/x.txt; git add` → `lint: secret material in the tree`; `sed -i '0,/^check = "unit"/s//check = "nonesuch"/' docs/ledger/rules.toml` → `lint: docs/ledger/rules.toml names a check the flake does not define: nonesuch`. Paste all three; discard the scratch.
2. Edit the 16 rows per the table; `python3 pkgs/evidence/repomap.py --root . write`.
3. **Green.** `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . --verbatim` → `owed: 0 …`, `EXIT=0`; `nix build .#checks.x86_64-linux.{rules-owed,ledger-unit,evidence-unit,lint} -L --no-link` → four builds. Acceptance: **rules-owed, ledger-unit, evidence-unit, lint** pasted.
4. **Mutants:**
   - **M1 — blank one check** (`sed -i '0,/^check = "integration"/s//check = ""/' docs/ledger/rules.toml`) → `rules-owed` fails `1 load-bearing rules without a check`.
   - **M2 — flip the (c) row back to `load_bearing = true`** → `rules-owed` fails with `1`.
   - **M3 — break the count parser** (`s/^owed: /owed:/` in the check's `sed`) → `owed` is empty → `the validator printed no owed: line`: the check cannot pass vacuously.
   - **M4 — control**: with the tree green, `rules-owed` builds; then M1 — the same check goes red, so the green is not a constant.
   - **M5 — hardware file edited**: Step-1's append → `lint` red on the checksum; **M6 — an OpenRouter key shape in a fixture** → `lint` red on the sweep; **M8 — a rotated prefix** (`sk-or-v2-` + 16 alphanumerics) → the same red; **M9 — a PEM header** (`-----BEGIN OPENSSH PRIVATE KEY-----` in a fixture) → the same red: the sweep is a rule, not a spelling.
   - **M7 — a `check` naming no attribute** (`check = "nonesuch"`) → `lint` red naming `nonesuch`; `rules-owed` still builds — the two checks divide the work: count here, resolution in `lint`.
   - **M10 — the validator exits 1 with `owed: 0`** (on a scratch copy, break one row's `origin` to a non-date) → `rules-owed` still builds; `rules-validate` (EV16) is where that red belongs.
5. **Commit** with the subject above; body: the disposition table, the Step-1 reds, the green outputs, M1–M10.

**Tests (assertion → mutant; fixture → discriminating row).** owed == 0 → M1, M2; parser non-vacuous → M3; control → M4; hardware verbatim → M5; no secret shape → M6, M8, M9; check names resolve → M7; errs ignored → M10.

**probes:**
- owed-now: `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . | sed -n 's/^owed: \([0-9]*\).*/\1/p'` :: ge 16 :: Assumption 4, pre-state (0 after)
- owed-now-exact: `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . | sed -n 's/^owed: \([0-9]*\).*/\1/p'` :: le 16 :: exact count, Assumption 4
- checks-blank: `grep -c '^check = ""' docs/ledger/rules.toml` :: ge 46 :: Assumption 3, pre-state (31 after: 46 minus 15)
- checks-blank-exact: `grep -c '^check = ""' docs/ledger/rules.toml` :: le 46 :: exact count, Assumption 3
- attr-absent: `nix eval .#checks.x86_64-linux --apply builtins.attrNames --json | grep -c rules-owed` :: le 0 :: pre-state
- secret-arms-clean: `grep -rEln -e 'sk-or-v[0-9]+-[A-Za-z0-9]{16}' -e 'sk-ant-api[0-9]{2}-[A-Za-z0-9_-]{16}' -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' -e 'AGE-SECRET-KEY-1[A-Z0-9]{16}' --exclude-dir=.git . | wc -l` :: le 0 :: measured 2026-09-14, the sweep's pre-state

### KN14 (code, M) — The audit's verdicts applied

**dependsOn:** KN11, KN13
**touches:** `docs/ledger/rules.toml`, `tests/evidence/test_rules_completeness.py`
**acceptance:** rules-owed, ledger-unit, evidence-unit, lint
**commit subject:** knowledge: the rules audit's verdicts applied — every row keep, amend or retire, the uncheckable unmeasured rows deleted, the counts re-pinned (test: rules-owed, ledger-unit, evidence-unit, lint)

**Why.** Charter §4 (`docs/concepts/2026-09-09a-redesign-charter.md:83-86`): the audit's output is "one dated ruleset file with a verdict per rule … a rule with no check and no measurement is deleted, not date-stamped". Today every verdict is `""` (Assumption 5) and the header's last bracket reads `verdicts left empty` (`:19`); the deletion population is the 27 rows A27 counts, once KN13 has given the 16 load-bearing rows their checks.

**Files.**
- Modify `docs/ledger/rules.toml`: every surviving row's `verdict` from `docs/decisions/<date>-rules-verdicts.md` (Q1); an `amend` row takes the replacement `text` and `note = "amended <date>: <cite>"`, and because `text` must stay verbatim in `source`, the owning key applies the source edit (KN15 `CLAUDE.md`, KN18 `docs/brief.md`) — KN14 records `amend` only where that edit is queued, naming the key; `retire` rows deleted; rows with `check = ""` and `measured` starting `UNMEASURED` deleted (A27), each listed in the commit body by id; the header `:19` gains `[audited <date> by KN14: N kept, A amended, R retired, D deleted under 54a; verdicts from docs/decisions/<date>-rules-verdicts.md]`.
- Modify `tests/evidence/test_rules_completeness.py`: `EXPECTED_PER_SOURCE` and `EXPECTED_TOTAL` re-pinned to the post-audit counts; a new `test_every_row_has_a_verdict` (Interface 3) and `test_no_row_is_unchecked_and_unmeasured` (Interface 4).

**Interfaces.**
1. After KN14, `verdict` is never `""` in the shipped ledger; the enum stays `rules.py:180`'s.
2. No shipped row has both `check = ""` and a `measured` value beginning `UNMEASURED` (54a's deletion clause, made a test).
3. `test_every_row_has_a_verdict` fails naming the first row whose verdict is empty.
4. `test_no_row_is_unchecked_and_unmeasured` fails naming every row in that intersection.
5. The per-source pin equals the post-audit `uniq -c`; the total equals `63 − R − D`.
6. `rules-owed` stays at 0 and `rules.py validate --verbatim` exits 0 — deletion never touches a source file, so no anchor moves.

**Steps.**
1. **Red.** Write the two new tests first and run them against the unedited ledger: `EVIDENCE_UNIT_SANDBOX=1 nix develop -c pytest tests/evidence/test_rules_completeness.py -q` → `FAILED …::test_every_row_has_a_verdict - AssertionError: R-invariant-basket-tmpfs has no verdict` (the first row) and `FAILED …::test_no_row_is_unchecked_and_unmeasured - AssertionError: 27 rows: R-practice-brief8-terse, …` (the count re-measured at commit, G11). Paste both. Precondition for the verdict source: `ls docs/decisions/*rules-verdicts.md` → one file, or Q1's default applies and the commit body says `default: keep`.
2. Apply the verdicts; delete the `retire` and the unchecked-unmeasured rows with the same `tomllib`-free block splitter KN11 used (split on `\n[[rule]]\n`, drop by id, write back); update the header.
3. Re-pin: `grep '^source' docs/ledger/rules.toml | sed 's/.*= "//;s/:[0-9]*"$//' | sort | uniq -c` → write into `EXPECTED_PER_SOURCE`; `grep -c '^\[\[rule\]\]'` → `EXPECTED_TOTAL`. The pin's red is the tripwire itself: before re-pinning, `pytest … -q` → `FAILED …::test_total_is_pinned - assert <new> == 63` — paste it; this is KN11's tripwire proving it catches the audit's own deletions.
4. **Green.** `pytest tests/evidence/test_rules_completeness.py -q` → `5 passed`; `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . --verbatim` → `owed: 0`, `EXIT=0`; `nix build .#checks.x86_64-linux.{rules-owed,ledger-unit,evidence-unit,lint} -L --no-link` → four builds. Acceptance: **rules-owed, ledger-unit, evidence-unit, lint** pasted.
5. **Mutants:**
   - **M1 — blank one verdict** → `test_every_row_has_a_verdict` fails naming it.
   - **M2 — restore one deleted row** (paste `R-practice-brief8-terse` back) → `test_no_row_is_unchecked_and_unmeasured` fails naming it and `test_total_is_pinned` fails `+1`.
   - **M3 — a verdict outside the enum** (`verdict = "maybe"`) → `evidence-unit`'s `test_shipped_inventory_validates` fails `verdict must be one of '', keep, amend, retire`; `rules.py validate` exits 1.
   - **M4 — blank a `check` on a kept load-bearing row** → `rules-owed` red `1 load-bearing rules without a check`.
   - **M5 — control**: the Interface-4 test passes on a two-row fixture (measured-unchecked, unmeasured-checked); a third unmeasured-unchecked row → fails: it discriminates on exactly the intersection.
6. **Commit** with the subject above; body: the Step-1 and Step-3 reds, the ids deleted with the clause each fell under, the amended ids and the key that applies each source edit, the green outputs, M1–M5.

**Tests (assertion → mutant; fixture → discriminating row).** every verdict set → M1; intersection empty → M2, M5; enum → M3; owed 0 → M4; pin → M2 (total), Step-3 red.

**probes:**
- verdicts-empty: `grep -c '^verdict = ""' docs/ledger/rules.toml` :: ge 63 :: Assumption 5, pre-state (0 after)
- verdicts-empty-exact: `grep -c '^verdict = ""' docs/ledger/rules.toml` :: le 63 :: exact count, Assumption 5
- unmeasured: `grep -c '^measured = """UNMEASURED\|^measured = "UNMEASURED' docs/ledger/rules.toml` :: ge 1 :: this task's Why (43 at 662e87f; re-measure)
- header-undated: `grep -c 'audited 2026' docs/ledger/rules.toml` :: le 0 :: pre-state (1 after)

### KN15 (code, M) — CLAUDE.md's rules block is generated from the ledger

**dependsOn:** KN14
**touches:** `pkgs/evidence/rules.py`, `tests/evidence/test_rules_generate.py`, `CLAUDE.md`, `docs/ledger/rules.toml`, `flake.nix`, `docs/runbooks/evidence.md`
**acceptance:** evidence-unit, ledger-unit, lint
**areas:** knowledge, evidence, platform
**commit subject:** knowledge: rules.py generate renders CLAUDE.md's rules block from the ledger, and lint fails on drift (test: evidence-unit, ledger-unit, lint)

**Why.** Decision 59a: "one rules source generates CLAUDE.md and AGENTS.md (drift fails lint)". Today the direction is reversed: 14 rows cite `CLAUDE.md:<line>` as `source` (Assumption 3) and the validator holds the ledger to the file, so editing `CLAUDE.md` is what changes a rule; no `generate` (Assumption 4), no markers (`grep -c '<!-- rules:' CLAUDE.md` → 0); MINOR-3 of KN1b's gate (`docs/reviews/2026-09-10-opus-review-pr1e-KN1b.md:487`, Assumption 15) stands. After KN14 the audited rows are the ones to render.

**Files.**
- Modify `pkgs/evidence/rules.py`: a `generate` subcommand — `rules.py generate <rules.toml> --target claude --out CLAUDE.md [--check] --root <r>` — rendering, for rows whose `origin_target = "claude"` (a new optional field; absent → not rendered), one bullet per row in ledger order between `<!-- rules:begin -->` and `<!-- rules:end -->`, replacing the marked block and nothing else — the shape of `tasks.py`'s `_splice_board`/`write_board` (`:2355-2377`), pasted here as the module's new functions:
  ```python
  BEGIN, END = "<!-- rules:begin -->", "<!-- rules:end -->"
  TARGETS = ("claude",)  # KN16 adds "agents", "agents-commit"

  def splice(text: str, block: str) -> str | None:
      """Replace the marked block; None when a marker is missing or misordered."""
      ib, ie = text.find(BEGIN), text.find(END)
      if ib < 0 or ie < 0 or ie < ib:
          return None
      return text[:ib] + BEGIN + "\n" + block + END + text[ie + len(END):]

  def render(rows: list[dict], target: str) -> str:
      return "".join(f"- {r['text']}\n" for r in rows if r.get("origin_target") == target)

  def generate(path, rows: list[dict], target: str, check: bool = False) -> int:
      p = pathlib.Path(path)
      try:
          text = p.read_text()
      except OSError:
          print(f"rules: generate: cannot read {path}", file=sys.stderr)
          return 1
      new = splice(text, render(rows, target))
      if new is None:
          print(f"rules: generate: {path}: missing markers {BEGIN} … {END}", file=sys.stderr)
          return 1
      if check:
          if new == text:
              return 0
          sys.stdout.writelines(difflib.unified_diff(
              text.splitlines(True), new.splitlines(True), f"{path} (file)", f"{path} (ledger)"))
          return 1
      p.write_text(new)
      return 0
  ```
  `main` gains the `generate` subparser (`<rules.toml>`, `--target` from `TARGETS`, `--out`, `--check`, `--root`) and `validate` refuses an `origin_target` outside `TARGETS` (`rules: <id>: origin_target must be one of claude`). `validate` also learns that a row sourced `docs/ledger/rules.toml:<line>` is verbatim-checked against the ledger itself — the 14 rows' text lives there now and `CLAUDE.md` is its rendering.
- Modify `docs/ledger/rules.toml`: the 14 `CLAUDE.md` rows get `origin_target = "claude"` and `source = "docs/ledger/rules.toml:<their own text line>"`; the header schema comment gains `origin_target`.
- Modify `CLAUDE.md`: the rule sentences at `:10-12`, `:18-19`, `:39-46`, `:63-67` move inside one marked block under `## How work is done here`, rendered by the generator; the prose that is not a rule (`:1-9`, `## Commands`, `## Where things are`) stays hand-written.
- Create `tests/evidence/test_rules_generate.py` — KN11's import shim, then a two-row fixture ledger whose rows *differ* (so order is observable) and the tests, skeleton pasted:
  ```python
  ROW = '[[rule]]\nid = "R-{i}"\ntext = "{t}"\nsource = "docs/ledger/rules.toml:3"\norigin = "2026-09-14"\nclass = "practice"\nload_bearing = false\nmeasured = "fixture"\ncheck = ""\nverdict = "keep"\n{extra}\n'
  LEDGER = ROW.format(i="a", t="Never sudo.", extra='origin_target = "claude"') + ROW.format(i="b", t="Red first.", extra='origin_target = "claude"') + ROW.format(i="c", t="Unrendered.", extra="")
  FILE = "# Title\nprose before\n<!-- rules:begin -->\nstale\n<!-- rules:end -->\nprose after\n"

  def _fixture(tmp_path, body=FILE):
      (tmp_path / "rules.toml").write_text(LEDGER)
      f = tmp_path / "CLAUDE.md"; f.write_text(body)
      return f, rules.load(tmp_path / "rules.toml")

  def test_generate_replaces_only_the_block(tmp_path):
      f, rows = _fixture(tmp_path); assert rules.generate(f, rows, "claude") == 0
      t = f.read_text(); assert t.startswith("# Title\nprose before\n") and t.endswith("prose after\n")
  def test_rows_render_in_ledger_order_verbatim(tmp_path):
      f, rows = _fixture(tmp_path); rules.generate(f, rows, "claude")
      assert "<!-- rules:begin -->\n- Never sudo.\n- Red first.\n<!-- rules:end -->" in f.read_text()
  def test_unmarked_rows_are_not_rendered(tmp_path):
      f, rows = _fixture(tmp_path); rules.generate(f, rows, "claude"); assert "Unrendered." not in f.read_text()
  def test_check_is_0_when_current_and_1_with_a_diff_when_not(tmp_path, capsys):
      f, rows = _fixture(tmp_path); rules.generate(f, rows, "claude"); assert rules.generate(f, rows, "claude", check=True) == 0
      f.write_text(f.read_text().replace("- Red first.\n", "")); assert rules.generate(f, rows, "claude", check=True) == 1
      assert "CLAUDE.md" in capsys.readouterr().out
  def test_missing_markers_and_missing_file_exit_1(tmp_path, capsys):
      f, rows = _fixture(tmp_path, body="no markers\n"); assert rules.generate(f, rows, "claude", check=True) == 1
      assert "missing markers" in capsys.readouterr().err
      assert rules.generate(tmp_path / "absent.md", rows, "claude") == 1
  def test_deleting_a_rendered_row_turns_check_red(tmp_path):
      f, rows = _fixture(tmp_path); rules.generate(f, rows, "claude"); assert rules.generate(f, rows[1:], "claude", check=True) == 1
  def test_shipped_claude_md_is_current():
      assert rules.generate(ROOT / "CLAUDE.md", rules.load(ROOT / "docs/ledger/rules.toml"), "claude", check=True) == 0
  ```
- Modify `flake.nix`: `lint` (after `:1393`) runs `python3 pkgs/evidence/rules.py generate docs/ledger/rules.toml --target claude --out CLAUDE.md --check --root .` — drift fails lint; `evidence-unit` needs no change (it copies `docs/ledger` and `CLAUDE.md`, `:1491,:1505`).
- Modify `docs/runbooks/evidence.md`: a `## The rules inventory` section after `## Task areas` (`:87-109`) documenting `validate`, `--verbatim` (MINOR-3), `generate --check`, and "edit the ledger, regenerate, never edit the block".
- `docs/MAP.md`: `tests/evidence` count +1, regenerated under G5.

**Interfaces.**
1. `generate` writes exactly the marked block; bytes outside the markers are unchanged byte-for-byte (asserted on a fixture with prose before and after).
2. `generate --check` exits 0 when the block is current and 1 with a diff naming the file when not; a file without markers exits 1 with `missing markers`.
3. Rows without `origin_target = "claude"` are not rendered; rows are rendered in ledger order, one line each, `text` verbatim.
4. Deleting a rendered row from the ledger makes `--check` red (per-rule completeness reaches the generated target, §5.1).
5. `validate --verbatim` on the shipped ledger exits 0 with the 14 rows sourced to the ledger.
6. Failure arms: an absent `--out` file → exit 1 `cannot read <path>`; an `origin_target` outside `TARGETS` → `validate` error naming the id; zero rows for a target → an empty block between the markers, and `--check` compares exactly that (a marked file with no bullets is current, not an error).

**Steps.**
1. **Red.** Write the tests; `EVIDENCE_UNIT_SANDBOX=1 nix develop -c pytest tests/evidence/test_rules_generate.py -q` → every test errors `AttributeError: module 'rules' has no attribute 'generate'`; `7 failed`. Paste the summary line. Then the lint red before wiring: add the marker block to `CLAUDE.md` with one bullet deliberately paraphrased, add the `lint` line, `nix build .#checks.x86_64-linux.lint -L --no-link` → red with the diff line naming `CLAUDE.md`. Paste.
2. Implement `generate` and the ledger-sourced verbatim arm; re-source the 14 rows; run `nix develop -c python3 pkgs/evidence/rules.py generate docs/ledger/rules.toml --target claude --out CLAUDE.md --root .`; write the runbook section; `repomap.py --root . write`.
3. **Green.** `pytest tests/evidence/test_rules_generate.py -q` → all passed (count pasted); `rules.py validate … --verbatim` → `owed: 0`, `EXIT=0`; `rules.py generate … --check` → exit 0; `nix build .#checks.x86_64-linux.{evidence-unit,ledger-unit,lint} -L --no-link` → three builds. Acceptance: **evidence-unit, ledger-unit, lint** pasted.
4. **Mutants:**
   - **M1 — edit one word inside the block in `CLAUDE.md`** → `lint` red (`--check` diff); `git checkout CLAUDE.md`.
   - **M2 — edit one rendered row's `text` in the ledger without regenerating** → `lint` red on the same diff, in the other direction (Drill 2).
   - **M3 — delete one rendered row** → `--check` red (the bullet is now extra), and `test_total_is_pinned` from KN11/KN14 red too.
   - **M4 — make the splice rewrite the whole file** (return the block alone) → Interface-1 test fails: prose outside the markers lost.
   - **M5 — control**: the fixture test with a current block passes; append one character to its block → fails: the check discriminates.
   - **M6 — drop `--check` from the `lint` line** (run `generate` writing in place) → `lint` passes on drift and M1 no longer kills; recorded as why `--check`, not `generate`, is the lint verb.
   - **M7 — reverse the render order** (`reversed(rows)` in `render`) → `test_rows_render_in_ledger_order_verbatim` fails: the two fixture rows differ, so a swap is visible; **M8 — render `r["id"]` instead of `r["text"]`** → the same test fails on the bullet text.
5. **Commit** with the subject above; body: the reds, the green counts, M1–M8.

**Tests (assertion → mutant; fixture → discriminating row).** block current → M1, M2; deletion visible → M3; splice preserves prose → M4; control → M5; lint verb → M6; ledger order and verbatim text → M7, M8 (fixture: two differing rows plus one unmarked).

**probes:**
- claude-rows: `grep -c '^source = "CLAUDE.md' docs/ledger/rules.toml` :: ge 14 :: Assumption 3, pre-state (0 after)
- claude-rows-exact: `grep -c '^source = "CLAUDE.md' docs/ledger/rules.toml` :: le 14 :: exact count, Assumption 3
- markers: `grep -c '<!-- rules:' CLAUDE.md` :: le 0 :: pre-state (2 after)
- subcommands: `nix develop -c python3 pkgs/evidence/rules.py --help | grep -c generate` :: le 0 :: Assumption 4, pre-state
- runbook: `grep -c verbatim docs/runbooks/evidence.md` :: le 0 :: Assumption 15, pre-state

### KN16 (code, S) — AGENTS.md generated in-tree, its commit section from policies.md

**dependsOn:** KN15, PL5
**touches:** `pkgs/evidence/rules.py`, `tests/evidence/test_rules_generate.py`, `pkgs/dsh-openrouter/AGENTS.md`, `docs/ledger/rules.toml`, `flake.nix`
**acceptance:** evidence-unit, ledger-unit, lint
**areas:** knowledge, evidence, seat, platform
**commit subject:** knowledge: AGENTS.md is generated from the ledger, its commit section from policies.md, drift fails lint (test: evidence-unit, ledger-unit, lint)

**Why.** Decisions 52a and 59a. The two live trailer texts contradict (Assumption 13: `policies.md:31-35` "two trailers, in this order … neither replaces the other" against the sibling `AGENTS.md:45-46` "exactly ONE machine-set trailer and no `Co-Authored-By` line") and the ledger carries both as rows, `R-conv-commit-trailers` (`policies.md:31`) and `R-conv-seat-one-trailer` (`AGENTS.md:45`). Four rows cite the sibling git (`grep -c '^source = "~/flakes' docs/ledger/rules.toml` → 4), the one source the validator can only warn on (`flake.nix:1501-1504`); no `AGENTS.md` exists in this repo (`git ls-files | grep -c AGENTS.md` → 0); `dsh-openrouter.sh:558` still tells the operator to symlink the sibling's copy. 52a: `policies.md` wins and the commit section is generated from it; 36a and Q4: `pkgs/dsh-openrouter/AGENTS.md`.

**Files.**
- Modify `pkgs/evidence/rules.py`: `--target agents` for `generate`; rows with `origin_target = "agents"` render as in KN15, and rows with `origin_target = "agents-commit"` render into a second marked block `<!-- rules:commit:begin -->…end -->` headed `## Commits` — the `policies.md`-sourced commit rows rendered from their `policies.md` text, so the section is generated from `policies.md` as 52a says.
- Modify `docs/ledger/rules.toml`: the three `AGENTS.md` rows that survive KN14 (`:13`, `:23`, `:29` — if kept) re-sourced to `docs/ledger/rules.toml:<own line>` with `origin_target = "agents"`; `R-conv-seat-one-trailer` deleted (it contradicts 52a; if KN14 already deleted it under A27, nothing to do — the commit body says which); `R-conv-commit-trailers` gains `origin_target = "agents-commit"` with its `source` staying `docs/board/policies.md:31`.
- Create `pkgs/dsh-openrouter/AGENTS.md`: the sibling's non-rule prose copied once by hand (the operator's act at PL5 lands the sibling; this file is the *generated* successor) with the two marked blocks, then `generate --target agents` run over it.
- Modify `tests/evidence/test_rules_generate.py`: Interfaces 1–3 below.
- Modify `flake.nix`: `lint` gains `… generate … --target agents --out pkgs/dsh-openrouter/AGENTS.md --check --root .` beside KN15's line; `evidence-unit` copies `pkgs/dsh-openrouter/AGENTS.md` (after `:1511`) so the shipped-tree check runs there too.

**Interfaces.**
1. `generate --target agents` renders two blocks; the commit block's text is byte-for-byte the `policies.md` rows' `text` — asserted by reading `docs/board/policies.md` at the row's cited line.
2. A row with `origin_target = "agents-commit"` whose `source` is not under `docs/board/policies.md` is refused by `validate` (`rules: <id>: agents-commit rows are sourced from policies.md (52a)`).
3. No shipped row's `source` starts with `~/` after this task (`unresolved_sources` returns `[]` and the test asserts it without the `AGENTS.md` exemption of `test_rules.py:160-163`).
4. Step 0 precondition (A26): `git ls-files pkgs/dsh-harness | wc -l` → non-zero (PL5 landed). If zero, stop with exit 4 and an escalation naming PL5.

**Steps.**
1. **Red.** Step 0 first (paste the count). Write the tests; `pytest tests/evidence/test_rules_generate.py -q -k agents` → `FAILED … invalid choice: 'agents'` and `FAILED …::test_no_external_source - AssertionError: ['rules: R-conv-skill-catalog: source not found at ~/flakes/dsh-harness/AGENTS.md:13', …]`. Paste. Wire the `lint` line pointing at the not-yet-created file: `nix build .#checks.x86_64-linux.lint -L --no-link` → red `No such file: pkgs/dsh-openrouter/AGENTS.md`. Paste.
2. Implement; create the file; re-source the rows; delete the contradicting row; `git add pkgs/dsh-openrouter/AGENTS.md`; run `generate --target agents`.
3. **Green.** `pytest tests/evidence/test_rules_generate.py -q` → all passed; `rules.py validate … --verbatim` → `owed: 0`, `EXIT=0`, and no `source not found` warning on stderr; `nix build .#checks.x86_64-linux.{evidence-unit,ledger-unit,lint} -L --no-link` → three builds. Acceptance: **evidence-unit, ledger-unit, lint** pasted.
4. **Mutants:**
   - **M1 — re-type the sibling's one-trailer sentence into the commit block by hand** → `lint` red (`--check` diff on `pkgs/dsh-openrouter/AGENTS.md`).
   - **M2 — change `policies.md:31`'s text** → `evidence-unit` red (`R-conv-commit-trailers` not verbatim) and `--check` red once regenerated; `git checkout`.
   - **M3 — give `R-conv-commit-trailers` a `CLAUDE.md` source** → Interface-2 refusal.
   - **M4 — restore one `~/flakes` source** → Interface-3 test red.
   - **M5 — control**: the agents fixture with both blocks current passes `--check`; flip one byte in the commit block → red.
5. **Commit** with the subject above; body: the Step-0 count, the reds, the greens, M1–M5, and that `dsh-openrouter.sh:558`'s symlink hint is Seat/Harness's to retire (SA8).

**Tests (assertion → mutant; fixture → discriminating row).** commit block from policies.md → M1, M2; source rule → M3; no external source → M4; control → M5.

**probes:**
- sibling-rows: `grep -c '^source = "~/flakes' docs/ledger/rules.toml` :: ge 4 :: Assumption 3, pre-state (0 after)
- sibling-rows-exact: `grep -c '^source = "~/flakes' docs/ledger/rules.toml` :: le 4 :: exact count, Assumption 3
- in-tree-agents: `git ls-files pkgs/dsh-openrouter/AGENTS.md | wc -l` :: le 0 :: pre-state (1 after)
- absorbed: `git ls-files pkgs/dsh-harness | wc -l` :: ge 1 :: A26 precondition, measured at dispatch (0 today)

### KN17 (code, M) — The board is the derived page and nothing else

**dependsOn:** none
**touches:** `docs/OPERATIONS.md`, `docs/board/log-2026-09.md`, `tools/session-start.sh`, `tests/unit/90-session-start.bats`, `tests/unit/96-now-paragraph.bats`, `tests/lint/now-paragraph.sh`, `flake.nix`, `docs/runbooks/session.md`, `docs/ledger/rules.toml`
**acceptance:** unit, ledger-unit, evidence-unit, lint
**areas:** knowledge, evidence, platform
**commit subject:** knowledge: the board is the derived page and nothing else — the START HERE narrative moved to the log, the Now paragraph retired, lint refuses bytes outside the block (test: unit, ledger-unit, evidence-unit, lint)

**Why.** Decisions 50a and 51a: the START HERE narrative deleted, its prose moved to the log; the per-session handoff is the only hand-written prose. `wc -c docs/OPERATIONS.md` is two orders of magnitude above `SESSION_START_CAP_BOARD` 2300 (`docs/runbooks/session.md:58`; Assumption 12, re-measured at commit) in 70 lines — the front door is cut at about two per cent of itself every session. `lint` bounds only the shape (`flake.nix:1352-1359`: one `## START HERE`, ≤160 lines) and the Now paragraph's fold (`:1363-1364`, `tests/lint/now-paragraph.sh`); nothing refuses prose. The derived block is `:26-37` between the markers (`tasks.py:141`), the hand-written part `:1-25` and `:38-70`. `githooks/pre-commit:43-54` repeats `lint`'s three assertions (A25), so the shape it expects must survive or the hook is a touch.

**Files.**
- Modify `docs/OPERATIONS.md`: reduced to a fixed header — `# Operations board — nixos-agent-env`, a blank, `## START HERE` followed by one line `Facts: \`evidence bundle --markdown\`. Narrative: the newest \`docs/board/handoff-*.md\` and \`docs/board/log-2026-09.md\`. Below is derived by \`evidence tasks write-board\`; nothing here is typed.`, a blank — then the marked block. Everything else deleted.
- Modify `docs/board/log-2026-09.md`: a new top entry `## Log 2026-09-<date> (newest first)` whose body is today's START HERE text (`sed -n '10,25p;38,66p' docs/OPERATIONS.md` at commit time) verbatim under `### The last hand-written START HERE (moved by KN17, 50a)`.
- Modify `tests/lint/now-paragraph.sh`: rewritten in place as the board-shape checker under the same name and CLI (`FILE | --self-test`): exit 0 iff the file is exactly header (the four fixed lines) + one marked block + nothing after `<!-- tasks:end -->` but a trailing newline, **and** the block (markers inclusive) is at most `${SESSION_START_CAP_BOARD:-2300}` bytes — the cap `session-start.sh:182` cuts at, so growth is red here before it is silently truncated there (`board-shape: block is N bytes, cap 2300`); `--self-test` builds four fixtures (clean → 0; a line after the end marker → 1; a second paragraph before the block → 1; a 2,301-byte block → 1). The header comment says what it now checks.
- Modify `tests/unit/96-now-paragraph.bats`: the two cases become "self-test passes" and "the real board passes the shape check", plus "a board with a hand-typed line after the block fails".
- Modify `flake.nix`: `lint` `:1352-1364` keeps the `## START HERE` count, the ≤160 lines and the two `now-paragraph.sh` lines (the script now checks the shape); only the CR4b comment changes; no attribute added.
- Modify `tools/session-start.sh`: `:91-92` prints the block (`awk '/^<!-- tasks:begin -->/{s=1;next} /^<!-- tasks:end -->/{exit} s'`) under `## Board — derived queue (docs/OPERATIONS.md)`; the header comment `:3` says so.
- Modify `tests/unit/90-session-start.bats`: fixtures at `:25`, `:79`, `:104` gain the markers and a block line; the order test `:40-55` looks for the block's first line; a new case "the START HERE prose is not printed, the block is".
- Modify `docs/runbooks/session.md`: the ritual section's board sentences (`grep -n 'START HERE\|Now paragraph' docs/runbooks/session.md`) say the board is derived and the handoff is the narrative; the four sourced rows (`rules.toml:750,:762,:774,:786`) re-anchored if lines shift.
- Modify `docs/ledger/rules.toml`: the re-anchors only.

**Interfaces.**
1. After KN17, `docs/OPERATIONS.md` = fixed header + derived block; `write-board` leaves it byte-identical when the graph is unchanged (`git diff --exit-code`).
2. `lint` (via `now-paragraph.sh`) exits 1 on any byte outside the header and the block, naming the first offending line number.
3. `session-start.sh` prints the block within `SESSION_START_CAP_BOARD` without truncation: `lint` (via `now-paragraph.sh`) exits 1 naming the byte count when the block exceeds 2300, so the cap is a standing check, not a commit-time measurement.
4. The pre-commit's `grep -c '^## START HERE'` is still 1 and `wc -l` ≤ 160.
5. The moved prose is byte-identical in the log (`diff <(sed -n '<range>p' <old board>) <(sed -n '<range>p' docs/board/log-2026-09.md)` → empty).

**Steps.**
1. **Red.** Rewrite `now-paragraph.sh` first and run it on the live board: `bash tests/lint/now-paragraph.sh docs/OPERATIONS.md` → `now-paragraph: docs/OPERATIONS.md:10: prose outside the derived block`, exit 1; `nix build .#checks.x86_64-linux.lint -L --no-link` → red with that line. The new bats case: `nix develop -c bats tests/unit/90-session-start.bats -f 'prose is not printed'` → `not ok`. Paste all three.
2. Move the prose to the log (Interface 5 diff pasted); reduce the board; `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board` → `git diff --exit-code docs/OPERATIONS.md` clean; edit `session-start.sh`, the fixtures, the runbook; re-anchor rows.
3. **Green.** `bash tests/lint/now-paragraph.sh --self-test && bash tests/lint/now-paragraph.sh docs/OPERATIONS.md` → exit 0; `wc -c docs/OPERATIONS.md` (paste; expected well under 2300); `nix develop -c bats tests/unit/90-session-start.bats tests/unit/96-now-paragraph.bats` → all ok; `rules.py validate … --verbatim` → `EXIT=0`; `nix build .#checks.x86_64-linux.{unit,ledger-unit,evidence-unit,lint} -L --no-link` → four builds. Acceptance: **unit, ledger-unit, evidence-unit, lint** pasted.
4. **Mutants:**
   - **M1 — type one line after `<!-- tasks:end -->`** → `lint` red naming the line; `git checkout`.
   - **M2 — add a second paragraph between the header and `<!-- tasks:begin -->`** → `lint` red.
   - **M3 — delete the `## START HERE` line** → `lint` red on the existing count assertion (`must have exactly one`) — the pre-commit's twin stays live.
   - **M4 — control**: the `--self-test` clean fixture passes; append one byte → fails (a hand edit *inside* the block is M5's, caught by `tasks.py check` at `flake.nix:1386`).
   - **M5 — edit one key inside the block** → `lint` red from `tasks.py … check` (`board block is stale`).
   - **M6 — revert `session-start.sh:92` to the START HERE awk** → the new bats case red (prose printed, block absent).
   - **M7 — pad the block** (one 2,300-byte line inside the markers on a scratch copy) → `lint` red `block is N bytes, cap 2300`; the `--self-test`'s fourth fixture is the same arm without the scratch.
5. **Commit** with the subject above; body: the reds, the byte count, the Interface-5 diff, M1–M7.

**Tests (assertion → mutant; fixture → discriminating row).** nothing after block → M1; nothing before but header → M2; one START HERE → M3; control → M4; block current → M5; hook prints block → M6; block within cap → M7.

**probes:**
- board-bytes: `wc -c < docs/OPERATIONS.md` :: gt 2300 :: Assumption 12, pre-state (lt 2300 after)
- markers: `grep -c '<!-- tasks:' docs/OPERATIONS.md` :: ge 2 :: Assumption 12
- markers-exact: `grep -c '<!-- tasks:' docs/OPERATIONS.md` :: le 2 :: exact count, Assumption 12
- precommit-twin: `grep -c 'START HERE' githooks/pre-commit` :: ge 1 :: A25

**Added context (2026-09-14, operator-dispatched worktree, not a replan).** A parallel session (chip task_f383579e) fixes tools/session-start.sh:175-177, which replays `tail -n 3` of a ritual.log last written 2026-09-08 — the three 'ritual:' lines at every session start are stale — with a bats case in tests/unit that seeds a stale line and asserts the hook omits it. Re-measure the script's line numbers and the bats file's case count at dispatch; merge that branch first if it has landed, and keep its test green.

### KN18 (docs, M) — Brief §3 re-ratified after the audit, §4 §7 §9 superseded, phases renumbered

**dependsOn:** KN14
**touches:** `docs/brief.md`, `docs/ledger/rules.toml`, `tests/evidence/test_rules_completeness.py`
**acceptance:** ledger-unit, evidence-unit, claims-validate, lint
**areas:** knowledge, evidence
**commit subject:** knowledge: brief §3 re-ratified after the audit, §4 §7 §9 superseded in place, phases renumbered 1..N, the test-passed gate verbatim (test: ledger-unit, evidence-unit, claims-validate, lint)

**Why.** Decision 55a (`:68`): "§3 re-ratified as the invariant set after the reopening of item 49; §4, §7, §9 superseded in place; phases renumbered 1..N; the 'test passed' gate kept verbatim", conditioned by the departure note (`:104`): the re-ratification happens *after* the audit's review, not instead of it — hence `dependsOn: KN14`. At HEAD nothing of this exists (Assumption 14): the one `superseded` is `:95`, unrelated; §3 carries no date or cite; §4 (`:83-180`) presents 2026-09-02 upstream facts as current; §7 lists nine `**Phase N —**` paragraphs (`grep -c '^\*\*Phase [0-9]' docs/brief.md` → 9) the charter's increments replaced; §9 asks questions `docs/decisions/` answered. Fifteen rows anchor to `docs/brief.md` (`:68-78` the six invariants, `:314-328` nine §8 practices), so every insertion above `:328` is a ledger edit. Charter §4 (`:78-80`) holds the six verbatim until the audit lands; KN14 is the landing.

**Files.**
- Modify `docs/brief.md`: (i) §3: after the six invariants (`:79`) one dated line — `Re-ratified <date> after the rules audit (decision 55a, docs/decisions/2026-09-09-redesign-answers.md:68; verdicts docs/ledger/rules.toml, KN14): all six kept verbatim.` — or, per A21, `… invariant <n> amended: <replacement>` with the invariant's text replaced in place; (ii) §4, §7, §9: a first line under each heading — `> Superseded in place <date> (55a). §4 → \`docs/upstream-verification-2026-09-02.md\` and each subsystem's context block; §7 → the charter's increments (\`docs/concepts/2026-09-09a-redesign-charter.md\` §6) and \`docs/superpowers/plans/\`; §9 → \`docs/decisions/\`. The text below is kept for the record.`; (iii) phases: a new list `**Phase 1 — …**` … `**Phase N — …**` from the charter's increments 0–4 (N = 5, pasted at commit), the nine originals kept below under `Original phases (superseded)`; (iv) the gate sentence `:265-266` ("Each phase ends with a test I can run. Do not start the next phase until the previous phase's test passes and I have said so.") stays byte-identical.
- Modify `docs/ledger/rules.toml`: the six invariant rows' `source` (`:68-78` shift by the §3 line only if inserted above them — insert *after* `:79`, so they do not move) and the nine §8 rows (`:314-328`) re-anchored by the §4/§7 insertions' line count; an amended invariant's `text` updated (A21). Two rows **added**, so both prose facts are watched by the existing verbatim validator (`test_shipped_inventory_validates`, `test_rules.py:155-158`; `_flat` collapses line wrapping, `rules.py:79-88`): `R-conv-brief3-re-ratified` (`convention`, `text` = the new §3 line verbatim, `source = "docs/brief.md:<its line>"`, `check = "evidence-unit"`, `load_bearing = true`, `measured` = the `sed -n` that shows it, `verdict = "keep"`) and `R-practice-test-passed-gate` (`practice`, `text = "Do not start the next phase until the previous phase's test passes and I have said so."`, `source = "docs/brief.md:265"` re-measured after the §4 insertion, same `check`, `load_bearing`, `verdict`).
- Modify `tests/evidence/test_rules_completeness.py`: `EXPECTED_PER_SOURCE["docs/brief.md"]` and `EXPECTED_TOTAL` each +2 (KN11's pin, re-pinned by KN14; the red is the pin itself).

**Interfaces.**
1. `sed -n '64,82p' docs/brief.md` shows the six invariants and, after them, one line beginning `Re-ratified` with a date and `55a`; its row makes deleting or rewording it an `evidence-unit` red.
2. `grep -n '^> Superseded in place' docs/brief.md` → exactly three hits, one under each of §4, §7, §9 (the line after each `## N.` heading).
3. `grep -c '^\*\*Phase [0-9]* —' docs/brief.md` → N + 9 (the new list plus the kept originals); the new list's numbers are contiguous from 1.
4. `grep -c 'Do not start the next phase until the previous' docs/brief.md` → 1 and the sentence is byte-identical: its row's `text` is verbatim-checked by `evidence-unit`, so one changed word is `text is not byte-for-byte in docs/brief.md`.
5. `rules.py validate … --verbatim` exits 0; `test_every_named_source_has_a_row`'s §3/§8 bounds (`test_rules.py:183-190`, from `## N.` headings) still resolve — headings are not renumbered, only phases.
6. `claims-validate` stays green: `grep -c 'docs/brief.md' docs/ledger/claims.toml` → 0 today, so it is a regression guard, not a witness; the body says so.

**Steps.**
1. **Red.** Re-measure the anchors (IS14 may have landed): `grep -n '^## ' docs/brief.md` — paste. Insert the three supersession lines and the §3 line, then `nix develop -c python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root .` → `rules: R-practice-brief8-terse: source line does not contain the rule text` (and the other eight §8 rows), `EXIT=1`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` → red on `test_shipped_inventory_validates`. Paste. The six invariant rows still resolve (inserted after `:79`) — the negative control; M4 shows the validator would have caught a move.
2. Renumber; keep the originals; re-anchor the nine rows (`grep -n '<first words>' docs/brief.md` each); add the two rows; apply A21's amendment if any. The pin's red: `EVIDENCE_UNIT_SANDBOX=1 nix develop -c pytest tests/evidence/test_rules_completeness.py -q` → `FAILED …::test_per_source_counts_are_pinned … 'docs/brief.md': <n+2> … expected <n>` — paste, then re-pin.
3. **Green.** Interfaces 1–4 commands with output pasted; `rules.py validate … --verbatim` → `EXIT=0`; `nix build .#checks.x86_64-linux.{ledger-unit,evidence-unit,claims-validate,lint} -L --no-link` → four builds. Acceptance: **ledger-unit, evidence-unit, claims-validate, lint** pasted.
4. **Mutants:**
   - **M1 — delete the `Re-ratified` line** → `evidence-unit` red: `R-conv-brief3-re-ratified: source line does not contain the rule text`; the commit body's `grep -c '^Re-ratified' docs/brief.md` → 0 is the human-readable twin.
   - **M2 — drop one supersession marker** → Interface 2 count 2, not 3.
   - **M3 — change one word of the gate sentence** → `evidence-unit` red: `R-practice-test-passed-gate: text is not byte-for-byte in docs/brief.md`; Interface 4's diff count 1 is the twin.
   - **M4 — shift an invariant** (insert a blank line at `:67`) → `evidence-unit` red: six `source line does not contain the rule text` errors — the ledger is the check on §3's text, which is why §3 is not moved.
   - **M5 — leave one §8 row un-anchored** → `evidence-unit` red naming it.
   - **M6 — control**: the untouched six rows resolve before and after (`rules.py validate` prints no `R-invariant-*` line) — and M4 turns that silence into six errors.
5. **Commit** with the subject above; body: the heading table, N, the reds, the greens, M1–M6, and A21's answer or default.

**Tests (assertion → mutant; fixture → discriminating row).** re-ratified line → M1 (its ledger row); three markers → M2; gate verbatim → M3 (its ledger row); §3 unmoved → M4, M6; §8 re-anchored → M5; pin → Step 2's red.

**probes:**
- superseded: `grep -c '^> Superseded in place' docs/brief.md` :: le 0 :: Assumption 14, pre-state (3 after)
- phases: `grep -c '^\*\*Phase [0-9]' docs/brief.md` :: ge 9 :: this Why, pre-state (measured 2026-09-14)
- phases-exact: `grep -c '^\*\*Phase [0-9]' docs/brief.md` :: le 9 :: exact count, this Why
- brief-rows: `grep -c '^source = "docs/brief.md' docs/ledger/rules.toml` :: ge 6 :: Assumption 3 (15 today; KN14 may delete the seven unmeasured §8 rows, never the six invariants)
- gate: `grep -c 'Do not start the next phase until the previous' docs/brief.md` :: ge 1 :: docs/brief.md:265-266, measured 2026-09-14
- gate-once: `grep -c 'Do not start the next phase until the previous' docs/brief.md` :: le 1 :: the sentence occurs once, this Files (iv)

### KN19 (code, S) — The repo's hook wiring file is under unit

**dependsOn:** none
**touches:** `flake.nix`, `tests/unit/90-session-start.bats`
**acceptance:** unit
**areas:** knowledge, platform
**commit subject:** knowledge: the repo's .claude/settings.json is under unit — four events, two scripts, asserted (test: unit)

**Why.** The three scripts `.claude/settings.json` wires are unit-tested (`90-session-start.bats`, `92-ritual.bats`, `91-orchestrator-guard.bats`); the wiring is tested by nothing (Assumption 10) and `unit`'s copy block (`:2925-2960`) never copies the settings file. So `Stop` pointed at a missing script, `PreCompact`'s matcher dropped or the guard removed from `Bash` has no red available, while KN12's `SEAT_MODE` gate and SA6's packaged hook assume the four events as measured (Assumption 10; the Interfaces below name each matcher and command, every command `bash "$CLAUDE_PROJECT_DIR/<script>" …`).

**Files.**
- Modify `flake.nix`: in `unit`'s copy block, after `:2932` (`cp ${self}/docs/OPERATIONS.md …`), two lines: `mkdir -p .claude` and `cp ${self}/.claude/settings.json .claude/settings.json`, with a comment naming the bats file that reads it; and `pkgs.jq` added to `unit`'s `nativeBuildInputs` (`sed -n '2876,2925p' flake.nix | grep -c 'pkgs.jq'` → 0 at `662e87f`; re-measure — if it is there by then, nothing to add).
- Modify `tests/unit/90-session-start.bats`: a `SETTINGS="$BATS_TEST_DIRNAME/../../.claude/settings.json"` line beside `:8`'s `SCRIPT`, and five cases (Interfaces 1–5) using `jq -r` (both files Knowledge's, `docs/ledger/subsystems.toml:232,:256`).

**Interfaces.**
1. `jq -r '.hooks.SessionStart[0].matcher' $SETTINGS` → `startup|clear|resume|compact`, and `.hooks.SessionStart[0].hooks[0].command` contains `tools/session-start.sh`.
2. `.hooks.PreCompact[0].matcher` → `manual|auto`; its command contains `tools/ritual.sh" precompact`.
3. `.hooks.Stop[0].hooks[0].command` contains `tools/ritual.sh" stop`.
4. `.hooks.PreToolUse[].matcher` → exactly the set `{Edit|Write|MultiEdit, Bash}`, and every `PreToolUse` command contains `tools/orchestrator-guard.sh`.
5. Every hook command's script exists: for each `command`, extract the path after `$CLAUDE_PROJECT_DIR/` up to the closing quote and `test -f "$BATS_TEST_DIRNAME/../../$path"` — the missing-script red. (`unit` copies `tools/session-start.sh`, `tools/ritual.sh` and `tools/orchestrator-guard.sh` at `:2935-2942`, so the paths resolve in the sandbox.)
6. The file is one JSON document: `jq empty $SETTINGS` exits 0.

**Hook consumers (A13** — a second reader of the wiring file, no hook body changes**)** — consumer | interpreter and tree | `stop_hook_active` | degrade-to-allow | mutant. (1) Claude Code in the orchestrator session → the checkout's `.claude/settings.json`, each command under the session's `bash` with `$CLAUDE_PROJECT_DIR` = the checkout | inside `tools/ritual.sh:174-179`, unchanged (`92-ritual.bats:799`) | the scripts' own arms (`ritual.sh:8`, `session-start.sh:5`), unchanged | M1, a missing script, is the failure the live consumer would meet silently. (2) The new bats cases → `jq` from `unit`'s `nativeBuildInputs` over the sandbox copy, the tree under test | not applicable | none by design: a missing `jq` or file is a loud `unit` red (a skip proves nothing, P8b) | M5 (`{}`) proves the cases read the file.

**Steps.**
1. **Red.** Add the five cases first, without the `cp`: `nix build .#checks.x86_64-linux.unit -L --no-link` → red, five `not ok` lines each with `jq: error: Could not open file …/.claude/settings.json: No such file or directory`. Paste. Locally the cases pass against the real tree (`nix develop -c bats tests/unit/90-session-start.bats -f settings` → 5 ok) — that is the control, and mutant M5 shows it discriminates.
2. Add the two `cp` lines.
3. **Green.** `nix build .#checks.x86_64-linux.unit -L --no-link` → builds; log count = today's `unit` count + 5 (paste). Acceptance: **unit** pasted.
4. **Mutants** (each on a scratch copy of the settings file, `git checkout .claude/settings.json` after):
   - **M1 — point `Stop` at `tools/ritual-missing.sh`** → Interface-5 case `not ok`: `no such script tools/ritual-missing.sh` (Drill 6).
   - **M2 — delete the `Bash` PreToolUse entry** → Interface-4 case `not ok` (matcher set is `{Edit|Write|MultiEdit}`).
   - **M3 — change SessionStart's matcher to `startup`** → Interface-1 `not ok`.
   - **M4 — swap `precompact` for `stop` in PreCompact's command** → Interface-2 `not ok`.
   - **M5 — control**: `echo '{}' > .claude/settings.json` → all five `not ok` (`null` matchers, no commands), proving the passes read the file and not a constant.
   - **M6 — trailing comma** (invalid JSON) → Interface-6 `not ok`: `jq: error … parse error`.
5. **Commit** with the subject above; body: the five red lines, the green count, M1–M6.

**Tests (assertion → mutant; fixture → discriminating row).** SessionStart wired → M3; PreCompact wired → M4; Stop wired → M1 (via script existence); guard on both matchers → M2; scripts exist → M1; valid JSON → M6; control (real file passes) → M5.

**probes:**
- copied: `sed -n '2925,2960p' flake.nix | grep -c 'settings.json'` :: le 0 :: Assumption 10, pre-state (1 after)
- events: `jq -r '.hooks | keys[]' .claude/settings.json | wc -l` :: ge 4 :: Assumption 10
- events-exact: `jq -r '.hooks | keys[]' .claude/settings.json | wc -l` :: le 4 :: exact count, Assumption 10
- guard-matchers: `jq -r '.hooks.PreToolUse[].matcher' .claude/settings.json | wc -l` :: ge 2 :: Assumption 10
- guard-matchers-exact: `jq -r '.hooks.PreToolUse[].matcher' .claude/settings.json | wc -l` :: le 2 :: exact count, Assumption 10
- jq-in-unit: `sed -n '2876,2925p' flake.nix | grep -c 'pkgs.jq'` :: le 0 :: measured 2026-09-14, this Files

### KN20 (docs, XS) — KN1's rework review filed with its rejection row

**dependsOn:** none
**touches:** `docs/reviews/2026-09-10-opus-review-pr1b-KN1.md`, `docs/ledger/plan-defects.toml`
**acceptance:** ledger-unit, lint
**areas:** evidence, factory
**commit subject:** knowledge: KN1's rework review filed under docs/reviews with its rejection row (test: ledger-unit, lint)

**Why.** KN1's first gate rejected it — `FACTORY-REVIEW verdict=rework`, one blocker, four majors (`program.md:679`) — and the verdict exists only in the transcript `~/factory/runs/pr1b/KN1.review.md` (Assumption 17; the review proper at `:1266-1331`); `docs/reviews/` holds only the approval `2026-09-10-opus-review-pr1e-KN1b.md`, and the ledger has no `KN1` row (Assumption 16). The ledger's rule (`:5`) — `review` is a repo-relative path that exists — is enforced by `_review_defect_errors` (`tasks.py:1552`, `no such review` at `:1660-1664`) under `lint` (`flake.nix:1386`), so the rejection is un-fileable without the file and the record undercounts Knowledge's defects by one.

**Files.**
- Create `docs/reviews/2026-09-10-opus-review-pr1b-KN1.md`: the front-matter block, its keys from the allowlist `REVIEW_BLOCK_KEYS` (`tasks.py:117-127`), pasted:
  ```
  ---
  plan_defect: missing-case
  plan_defect_secondary: implementer
  mutants_total: <from the transcript's ## 2. Red-before-green, :1272-1303, or null>
  mutants_killed: <same>
  mutants_outside_named: <same>
  reviewer: deepseek
  majors: 4
  minors: 3
  model: deepseek
  ---
  ```
  — `missing-case` for the blocker (brief §8 "a named source with ~7 rules, none inventoried", a case the plan named and the seat missed), `implementer` for the four majors (verbatim and coverage failures against a stated interface), `reviewer` from `REVIEWER_ENUM` (`:128`; the run header `:2` names `deepseek/deepseek-v4-pro-0813`), the counts from `sed -n '1313,1331p'` — then the H1 `# Opus gate — seat run pr1b, task KN1 — REJECTED` (`REVIEW_RE`, `tasks.py:96-98`, has no `rework`; the body's first line records `verdict as written: rework`), then `sed -n '1266,1331p' ~/factory/runs/pr1b/KN1.review.md` verbatim — the four numbered sections and the `FACTORY-REVIEW` line, not the reasoning transcript.
- Modify `docs/ledger/plan-defects.toml`: one `[[rejection]]` appended after `:633`, the six keys every existing row carries (`sed -n '627,633p'` → `review`, `run`, `key`, `date`, `plan_defect`, `plan_defect_secondary`; re-run at commit): `review = "docs/reviews/2026-09-10-opus-review-pr1b-KN1.md"`, `run = "pr1b"`, `key = "KN1"`, `date = 2026-09-10`, `plan_defect = "missing-case"`, `plan_defect_secondary = "implementer"`.

**Interfaces.**
1. `python3 pkgs/evidence/tasks.py --root . check` prints no `plan-defects row pr1b/KN1` line and no `review 2026-09-10-opus-review-pr1b-KN1.md:` line.
2. The front-matter keys are a subset of `REVIEW_BLOCK_KEYS` (`tasks.py:117-127`); both classes are in `PLAN_DEFECT_ENUM` (`:99-107`) and differ.
3. The H1 verdict is `REJECTED` and `plan_defect` is not `none` (`:1631-1636`: "a rejection names its cause").
4. The row's `date` equals the basename's prefix (`plan-defects.toml:5-6`).
5. `grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml` → 83.

**Steps.**
1. **Red.** Append the row first, without the file: `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → `tasks: plan-defects row pr1b/KN1: no such review docs/reviews/2026-09-10-opus-review-pr1b-KN1.md`, exit 1; `nix build .#checks.x86_64-linux.lint -L --no-link` → red with the same line. Paste.
2. Create the file per Files; `git add` it.
3. **Green.** `tasks.py --root . check` → exit 0, no `pr1b/KN1` line; `nix build .#checks.x86_64-linux.{ledger-unit,lint} -L --no-link` → two builds; Interface 5 pasted. Acceptance: **ledger-unit, lint** pasted. (`evidence-unit` pins the seed ledger at `flake.nix:1497-1498` and is unaffected — stated, not claimed.)
4. **Mutants:**
   - **M1 — misspell the `review` path in the row** → `lint` red `no such review`.
   - **M2 — `plan_defect: none` in the front matter** → `lint` red `a rejection names its cause`.
   - **M3 — `plan_defect_secondary` equal to `plan_defect`** → `lint` red `plan_defect_secondary equals plan_defect`.
   - **M4 — H1 verdict `APPROVED`** → `lint` red `a ledger row contradicts an APPROVED block` (`:1642-1647`).
   - **M5 — control**: file present, row correct → `check` silent; remove the row → still silent (an unfiled review is no error: the row, not the file, is the record); restore it and M1 → red: the check reads the row.
   - **M6 — an unknown front-matter key** (`verdict: rework`) → `lint` red `unknown key verdict`.
5. **Commit** with the subject above; body: the red line, the green outputs, the 83 count, M1–M6, and the `sed -n '1266,1331p'` range copied.

**Tests (assertion → mutant; fixture → discriminating row).** review exists → M1; cause named → M2; classes differ → M3; verdict consistent → M4; unknown keys refused → M6; control → M5.

**probes:**
- rows: `grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml` :: ge 82 :: Assumption 16, pre-state (DF5 and EV18 also append; this task adds exactly one)
- unfiled: `ls docs/reviews | grep -c 'pr1b-KN1'` :: le 0 :: Assumption 17, pre-state (1 after)
- source-present: `test -f ~/factory/runs/pr1b/KN1.review.md && echo present` :: eq present :: Assumption 17
- verdict-line: `grep -c '^FACTORY-REVIEW verdict=rework' ~/factory/runs/pr1b/KN1.review.md` :: ge 1 :: Assumption 17
- verdict-line-once: `grep -c '^FACTORY-REVIEW verdict=rework' ~/factory/runs/pr1b/KN1.review.md` :: le 1 :: exact count, Assumption 17
