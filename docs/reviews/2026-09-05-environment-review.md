# Environment, plans and documentation review — 2026-09-05

Eleven readers went over the repo, the live host and the runbooks: board, Helm
code, Helm runbooks, lane runbooks, CLAUDE.md, invariants, tests, plans/debt,
process, hygiene, flake inputs, Helm Home. A critic round then tried to refute
every finding on three lenses (facts, materiality, actionability); a keep needed
at least one lens to survive. 78 raw findings, 67 after dedup, 60 confirmed in
round 1, 29 in round 2, 10 refuted.

Three conclusions. First, Helm's two revision tiles grade the machine by commit
id in a repo that takes 27-112 commits a day, so both are structurally non-green
and the operator has stopped reading them. Second, the runbooks are one to two
days behind the machine in at least six places, and every one of those places is
load-bearing (tile colours, broker coverage, backup paths, the model picker, the
profile switch). Third, the code itself is in good shape: the invariants hold,
the negative checks are real, and the test suite killed most of a mutation
battery — the debt is in documentation and in two bad proxies, not in the build.

Your question, answered directly. Right now drift is **red** and flake-check is
**orange**, the opposite of what you reported. Three things make that hard to
see: the status page never prints the word "warn" or "fail" anywhere, only a
0.4 rem coloured stripe (`pkgs/helm/collect.py:621-627`); `docs/runbooks/helm.md:104`
and `docs/runbooks/switch-helm-gaming.md:67` both tell you flake-check reads red
after a switch, which the code never does; and the red drift tile sits next to
the orange one. Underneath, both tiles are non-green for the same reason: they
compare commit ids. `git diff --quiet a9ab362 de51f89 -- . ':!docs'` exits 0 —
every line of code the nightly check verified is still what is in the tree, and
every line the live system runs is still what is in the tree. Both tiles are
telling you the board was updated.

## Findings by area

### Helm

| Sev | Finding | Evidence | Fix | Test | Effort |
|---|---|---|---|---|---|
| major | flake-check tile can only be green ~20-45 min a day: `rev == HEAD` is the wrong proxy | `pkgs/helm/collect.py:496-500`; `/var/lib/helm/flake-check.json` rev a9ab362 | grade against a non-docs delta and against the live rev, not HEAD | `tests/helm/test_collect.py::test_flake_check_docs_only_delta_is_ok` | S |
| major | drift tile goes red on every docs-only board commit; the toplevel-outPath alternative cannot work (`configurationRevision = self.rev`) | `pkgs/helm/collect.py:479`; `flake.nix:631` | `git diff --quiet <live rev> HEAD -- . ':!docs'` first; clean → ok | new rows in `test_drift_branches` | S |
| minor | the page encodes every verdict as colour alone — no tile prints "warn" or "fail" | `pkgs/helm/collect.py:621-627`, `:561-568`; `pkgs/helm/render.py:186-187` | print the verdict word in the tile header, keep colour as reinforcement | `test_render_html_names_each_verdict_in_text` | XS |
| note | the page shows ten tile-shaped cards; helm.md, the drill and the switch runbook say nine | `pkgs/helm/render.py:187`; `docs/runbooks/helm.md:6,44,128`; `tests/acceptance/helm.sh:98,111` | say "nine health tiles plus the Profile card"; style control cards differently | count assertion in `test_render_control.py` | XS |

### Runbooks

| Sev | Finding | Evidence | Fix | Test | Effort |
|---|---|---|---|---|---|
| major | both runbooks say flake-check reads RED after a switch; the code returns WARN — helm.md contradicts itself in one paragraph | `docs/runbooks/helm.md:99-107`; `docs/runbooks/switch-helm-gaming.md:67` | list the code's three branches in order (fail: missing/unreadable/failed; warn: behind or ≥26 h; ok) | `tests/helm/test_docs_match_code.py` | XS |
| major | runbooks still say the broker tile is grey "no broker instance configured"; core has the openrouter instance and the tile is green | `/etc/helm/config.json`; `docs/runbooks/helm.md:74-78`; `switch-helm-gaming.md:72-74` | green with 24 h counts is normal; grey now means the audit log is unreadable — a fault | broker summary names the instance | XS |
| major | backup.md's "what is backed up" list names 6 of the 11 paths restic walks | `docs/runbooks/backup.md:14-19`; `hosts/core/proton-backup.nix:29-41` | enumerate all eleven (or the four groups), incl. `~/flakes` and `~/strategy` | extend `checks.core-backup-wiring` to require each path in the doc | S |
| major | lanes.md describes the picker as Pro plus Flash; the wrapper offers three more, none of them DeepSeek | `docs/runbooks/lanes.md:294-298`; `pkgs/dsh-openrouter/dsh-openrouter.sh:178` | list all four defaults and roles; say what the account ZDR group covers, or record it as an open check | grep each default id in lanes.md | S |
| minor | switch-helm-gaming.md still teaches the pre-v1 manual profile switch while Helm v1 control is live | `docs/runbooks/switch-helm-gaming.md:7-10,91,268-270`; `hosts/core/helm.nix` | mark it the record of the 2026-09-03 switch; point at `docs/runbooks/helm-v1.md` | assert `runbooks/helm-v1.md` appears in it | XS |
| minor | lanes.md's ledger contract ("only a successful job appends a line") is false for `--kind dsh`, and the dsh line carries no `usage` at all | `pkgs/lane/lane-run.py:446-470` vs `docs/runbooks/lanes.md:190-202` | describe all three kinds, or gate the dsh append on exit 0 | ledger assertion in `test_dsh_kind_nonzero_exit_records_error` | S |
| minor | seat README and lanes.md give contradictory DeepSeek Pro prices for the same day (0.55/2.19 vs 1.02/2.05) | `tools/factory/seat/README.md:134-135`; `docs/runbooks/lanes.md:297-298` | one dated price table (`tools/ledger/schema.md` already defines the format); both docs point at it | assert the pairs match across the two files | S |
| minor | lanes.md's ZDR gate still reads "not yet confirmed" with a blank date; the board recorded it done 2026-09-04 | `docs/runbooks/lanes.md:119-130`; `docs/OPERATIONS.md:105` | fill the date, drop the "not yet confirmed" sentence | no unfilled `_____` placeholders under `docs/runbooks/` | XS |
| minor | push.sh permanently deletes `/trash/<basename>`, weaker than backup.md's "only ever deletes the objects it itself trashed" | `pkgs/proton-backup/push.sh:86-91`; `docs/runbooks/backup.md:86-87` | soften the runbook to what the CLI allows, name the content-address assumption | seed an unrelated same-named trash item; assert it survives | M |
| minor | seat README says the XDG_CACHE_HOME workaround has not landed in the wrapper; it has | `tools/factory/seat/README.md:210-215`; `pkgs/dsh-openrouter/dsh-openrouter.sh:340` | say the wrapper sets it and the driver only honours an override | whitespace-insensitive grep in the lint gate | XS |
| note | `hosts/core/lanes.nix:7-8` still calls the lane's ExecStart "T2's stub"; it is the real runner and spends money | `hosts/core/lanes.nix:7-10`; `pkgs/lane/lane-run.nix:10-16` | delete the clause, keep the accurate half | grep assertion | XS |

### CLAUDE.md and README

| Sev | Finding | Evidence | Fix | Test | Effort |
|---|---|---|---|---|---|
| major | "How work is done here" names dark-factory.js via the Workflow tool as the mechanism; two days of production work ran through `tools/factory/seat` | `CLAUDE.md:113-116`; `docs/OPERATIONS.md:29-37` | add the seat driver as the day-to-day path; keep dark-factory.js for nixos-skill fix rounds and the future scheduler | `grep -q tools/factory/seat CLAUDE.md` **and** `grep -q dark-factory.js` | S |
| minor | README's status paragraph is ~28 h stale — still "awaiting the operator gate", "Switch hand-off is next" | `README.md:11` (last touched 18d7a17, 2026-09-04 03:46) | replace with a pointer to `docs/OPERATIONS.md` START HERE; stop keeping a prose changelog | negative grep on status prose + positive grep on the pointer | S |
| minor | the Architecture section omits Helm, model lanes, the seat wrapper and the ledger — four of the largest subsystems | `CLAUDE.md` Architecture block vs `nixosModules/helm.nix`, `modelLane.nix`, `pkgs/{helm,lane,dsh-openrouter}`, `tools/ledger` | add one bullet each, same shape as the existing five | none proposed | S |

The check-name list in `CLAUDE.md:41-50` was diffed against `nix flake show`:
zero difference. Every command and gotcha in the Commands block resolves.

### Factory and seat driver

| Sev | Finding | Evidence | Fix | Test | Effort |
|---|---|---|---|---|---|
| minor | seat scripts exec their siblings from `~/factory/bin`, not from their own directory as the README claims — the repo copies are gated by lint and bats, the `~/factory/bin` copies are what run | `tools/factory/seat/factory-lib.sh:16,23`; `factory-task:79,99,178`; `factory-wave:71,73` | `FACTORY_BIN=$here` with a separately named override; then symlink or delete `~/factory/bin` | bats: stub sibling in a copied seat dir, assert dispatch reaches it | S |
| minor | the README's script list omits `factory-usage.py` and `launch-today.sh`; the latter is a dated one-shot that spends the key on three concurrent waves | `tools/factory/seat/README.md:46-81`; `launch-today.sh:5,9,11,13` | document factory-usage.py; delete or date-park launch-today.sh | bats: every executable in the dir is named in the README | S |

### Tests

From the tests reader's mutation battery (nine mutations against a scratch copy;
four killed, five survived). These are reader-reported with hard evidence; the
critic verdicts for this dimension did not reach the writer.

| Sev | Finding | Evidence | Fix | Test | Effort |
|---|---|---|---|---|---|
| note | `helm-control-assertion-negative-profiles` asserts a guard the module does not implement — the fixture evaluates to `assertions = []` | `flake.nix:1119` vs `nixosModules/helm.nix` | implement the profile-is-a-declared-specialisation assertion, or retire the check | evaluate the fixture, expect a non-empty assertion list | S |
| note | `render.py`'s `_hm` writes an unparsable timestamp into four interpolation sites unescaped, against its own docstring | `pkgs/helm/render.py:85`, `:9-12` | route it through the same escaping | feed a `<script>` timestamp, assert it is escaped | XS |
| note | three serve.py guards survive deletion: the 64 KB body cap, the bad-`Content-Length` branch, `X-Content-Type-Options` | `pkgs/helm/serve.py` | add one test per guard | three cases in `test_serve.py` | S |
| note | `helm-open-workspace`'s `basket` value reaches an interpolated sudo command with no module assertion and no bats case | `pkgs/helm/helm-open-workspace.sh:46,51`; `nixosModules/helm.nix:25-29` | assert the value shape in the module | bats negative case | S |
| note | `tests/run-mount-tests.sh` is wired into no check, and bats skips are invisible in a check result | `flake.nix` checks list | wire it in, or say on the board that it is operator-run only | n/a | S |

### Board, invariants, plans and hygiene

The confirmed-findings payload reached this writer truncated in the middle of the
CLAUDE.md dimension, so the board, invariants/security, plans-debt, process,
hygiene, flake-inputs and Helm Home findings are represented here only through
their readers' coverage notes and through cross-references in the findings that
did arrive. What those notes establish, with evidence:

- `docs/OPERATIONS.md` is 1029 lines and 106 KB with nine stacked START HERE
  blocks; the newest block carries one malformed heading and numbered sections
  that contradict the paragraphs above them (board reader). A fresh session
  reading top to bottom gets the right facts first and the wrong ones second.
- The six brief invariants hold. Spot-checked and sound: the broker's per-instance
  input-chain drop rule ahead of the veth accepts (`nixosModules/egressBroker.nix:182`),
  helm-serve's Host/Origin/Sec-Fetch-Site/token stack, `helm-switch.sh` failing
  closed on shape and allowlist, the polkit rule's scoping, the `/api/v1/messages`
  deny landing before credential injection.
- Not asserted anywhere: that the harness sandbox confines *reads*, and that a
  tool subprocess cannot read the key file. The second is a recorded, accepted
  residual (`docs/OPERATIONS.md:349-356`).
- `hosts/core/default.nix:84-86` defers the orchestrator's own confinement with
  no date, owner or board entry.

## Recommendations for the system

**1. Regrade the two revision tiles against work, not commit ids.** Compute a
non-docs delta and compare the checked revision against the live configuration
revision as well as HEAD. Acceptance: on a docs-only advance both tiles read ok
and name the state ("HEAD adds docs only"); a one-line change under `pkgs/` still
turns drift red and flake-check orange. Effort S. This is the whole of your
reported problem.

**2. Print the verdict word on the page.** Colour is the only channel today.
Acceptance: `curl localhost:7700 | grep -c '>WARN<'` is non-zero when a tile
warns; the zero-outbound assertions stay green. Effort XS.

**3. Fix the five stale runbook paragraphs in one pass** — flake-check colours,
the broker tile, the profile switch, the backup path list, the model picker.
Acceptance: a new `tests/helm/test_docs_match_code.py` plus one Nix docs check
go from red to green, and stay red whenever code and prose diverge again.
Effort S. Do it after (1) so the text describes the new rule.

**4. Point CLAUDE.md at the seat driver and drop README's status prose.**
Acceptance: `grep -q tools/factory/seat CLAUDE.md` passes while
`grep -q dark-factory.js` still passes; README has no dated status sentences and
one pointer to the board. Effort XS. Highest value per keystroke in the report:
these two files are what a fresh session reads first.

**5. Split `docs/OPERATIONS.md`.** One START HERE at the top, the day log moved
to `docs/board-log-2026-09.md`, older START HERE blocks deleted rather than
stacked. Acceptance: the board is under ~200 lines and contains exactly one
START HERE heading; a fresh session's first 100 lines contain no statement that
contradicts a later one. Effort S.

**6. Make the existing debt registers reachable.** A register already exists —
`docs/reviews/2026-09-04-dsh-harness-review.md` §7 (D1-D10) and the fix-round
plan §C (O1-O11) — and closures are appended to
`docs/reviews/2026-09-04-dsh-debt-measurements.md`. What is missing is a pointer
from the board and the newer 2026-09-04/05 debt (lanes.md:328,333) being added
to it. Acceptance: every "dated debt" sentence on the board cites a D- or O-id;
each id has an owner and a closing measurement. Effort S.

**7. One authoritative price table.** `tools/ledger/schema.md` already defines the
CSV. Acceptance: no per-million price literal appears in `docs/runbooks/lanes.md`
or `tools/factory/seat/README.md`; both point at the dated table. Effort S.

**8. Fix seat sibling dispatch and retire `~/factory/bin`.** Acceptance: with
`FACTORY_ROOT` pointing at a directory with no `bin/`, `tools/factory/seat/factory-task`
dispatches to its own directory; `~/factory/bin` is a symlink or gone. Effort S.
The two trees are byte-identical today, so this is cheap now and expensive later.

**9. Generate the CLAUDE.md check list.** It is accurate today (zero diff against
`nix flake show`), so this is prevention only: a lint step that diffs the prose
list against the flake's check names. Effort S, low priority.

**10. Pin refresh cadence.** Not measured this round — no reader reported on
`flake.lock` input ages. Recommend a dated board item to check the three pins and
`llm-agents` monthly, with the research-digest rule already in CLAUDE.md as the
gate. Effort XS to record.

## Helm: what to do first

### Task H1 — regrade the drift and flake-check tiles

Red-first tests, in `tests/helm/test_collect.py`, using the existing table-driven
`fake_run` dispatcher (extend it to answer a `git diff --quiet` argv; today an
unmatched argv raises `FileNotFoundError`, so an un-extended stub errors rather
than fails):

1. `test_flake_check_docs_only_delta_is_ok` — flake-check.json rev "abc", HEAD
   "def", `git diff --quiet … ':!docs'` returns 0 → assert `status == "ok"` and
   `"docs" in summary`. Red today: the sibling case pins warn for this input.
2. Same fixture, diff returncode 1 → assert `warn`, both revs still in the
   summary. Stops the fix degenerating into always-ok.
3. Diff returncode 128 (live rev not an object after a rebase or GC) → assert
   `warn`/`fail`, never a raise: `collect_all` is contractually never-raises.
4. `test_drift_docs_only_behind_is_ok` — live "abc", HEAD "def", clean tree,
   diff 0 → `ok`; diff 1 → `fail`. Assert the argv actually issued names the
   live base rev with any `-dirty` suffix stripped.
5. Checked rev == live configuration revision but != HEAD → `ok`, with a summary
   that separates "what I run is checked" from "HEAD is checked". This is the
   assertion that encodes the tile's real question.

Files: `pkgs/helm/collect.py` (`tile_drift` 431-480, `tile_flake_check` 482-504),
`tests/helm/test_collect.py`. Checks: `helm-unit`, then `lint`. No module or host
change, so no switch is needed to land it; the tile changes appear at the next
collection after the operator's next switch.

Do **not** compare toplevel outPaths: `flake.nix:631` bakes the commit id into
the system, so they never match, and it costs a full eval every five minutes.
The git test costs 1 ms against the nightly check's 105 s and 13.8 GB.

Optional follow-up: a systemd path unit on `<repo>/.git/logs/HEAD` with a ~10 min
debounce that starts `helm-flake-check.service` only when the non-docs delta is
non-empty. Unconditional per-commit triggering is not affordable (~51 non-docs
commits a day × 105 s).

### Task H2 — print the verdict

`pkgs/helm/collect.py` render_html tile header and `pkgs/helm/render.py:186-187`
Profile section. Test: strip class attributes and the `<style>` block, then
assert each of ok/warn/fail/unknown survives as page text; keep the zero-outbound
assertion in the same test. Check: `helm-unit`.

### Task H3 — runbook pass

`docs/runbooks/helm.md` (flake-check branches, broker paragraph, add a Profile
section), `docs/runbooks/switch-helm-gaming.md` (amber not red; supersede the
manual profile switch; point at helm-v1.md), plus the tile count. New
`tests/helm/test_docs_match_code.py` with whitespace-normalised assertions —
several of the offending sentences wrap across lines, so naive substring checks
pass vacuously. Check: `helm-unit`.

### Helm Home prerequisites

The spec is more settled than it looks. Tiles versus windows is already decided
(`docs/superpowers/specs/2026-09-04-helm-home-design.md:14,26,74-75`: terminals
and journal views render as tiles inside Helm, anything unembeddable opens over
it, tiles pop out to windows). "Work here" is not the Console flow you removed —
that decision names popping kgx from the *web page*, and explicitly says the Helm
Home verbs replace it. Two real prerequisites remain:

- The `auth_admin_keep` polkit flip is mechanically fine (polkit resolves a
  session-less user unit through `sd_uid_get_display`, and gnome-shell's agent is
  registered for session 2), but it invalidates `flake.nix:1092`'s grep for
  `polkit.Result.YES` and the v1 contract line "journalctl -u polkit shows no
  prompt for the allowed start". Plan that as a contract change, not a side
  effect. And decide what a Switch pressed from the phone view does when the
  dialog can only be answered at the machine — today it would block to
  `serve.py`'s 360 s timeout.
- Say in words whether `helm-open-workspace` and the kgx pin stay wired once
  Helm Home ships; the removal decision parks them but does not close them.

### Proposed decomposition (this report's proposal, not a reader's)

| Wave | Key | Touches | Checks |
|---|---|---|---|
| A | H1 tiles | `pkgs/helm/collect.py`, `tests/helm/test_collect.py` | helm-unit, lint |
| A | H2 verdict text | `pkgs/helm/collect.py`, `pkgs/helm/render.py`, tests | helm-unit |
| A | H3 runbooks | `docs/runbooks/*.md`, new docs test | helm-unit |
| A | C1 CLAUDE.md + README | `CLAUDE.md`, `README.md` | lint |
| B | HH1 declaration reader + card model | new `pkgs/helm/home/*`, unit tests | new helm-home-unit |
| B | HH2 polkit contract change | `nixosModules/helm.nix`, `flake.nix:1092` | helm-control-eval, helm-control-vm |
| B | HH3 GTK shell + tile embedding | new package | eval + VM |

Wave A is four independent keys with no shared file; run them in parallel. Wave B
depends only on H1/H2 landing, not on H3.

## Dated debt and operator items

Assembled from the board and the two registers; the plans-debt reader's own table
did not reach this writer.

| Item | First recorded | Owner | Closing measurement | Status |
|---|---|---|---|---|
| D1-D10 (harness review debt) | 2026-09-04 | unnamed | table's "what would settle it" column | D9 closed; rest open |
| O1 account ZDR + training opt-out | 2026-09-03 | operator | dashboard setting, date in lanes.md:130 | done on board 2026-09-04; runbook still blank |
| O4 cross-origin framing probe | 2026-09-04 | operator | real Firefox frame attempt | open, low value (headers shipped and probed) |
| O5 D5 OpenRouter activity export | 2026-09-04 | operator | `~/strategy/ledger/openrouter-activity.csv` | listed for 2026-09-05 |
| M2/M2b reasoning-token itemisation | 2026-09-04 | unnamed | a usage record carrying reasoningTokens | open; cost is *not* undercounted |
| Effort policy n=1 | 2026-09-04 | unnamed | more arms | open |
| Reasoning effort honoured upstream | 2026-09-04 | unnamed | provider-side evidence | open, unverifiable in-repo |
| Shadow-vs-truth lane agreement | 2026-09-03 | operator | any recorded comparison | open, no tool |
| Orchestrator confinement | undated | unnamed | none stated | deferred, no board entry |

## Unmeasured claims met during the review

- The harness sandbox confines tool-call *reads* to the working tree — asserted
  in three places, measured nowhere.
- `--offline` makes the nightly flake check network-free — asserted, never probed.
- helm.md's numeric thresholds (backup snapshot ~50 h, GPU 85 °C / 95 % memory)
  are prose only, not pinned against `collect.py`.
- The "flake check goes red after `nix-collect-garbage`" story: no occurrence in
  the journal, no test.
- Key-file properties (root:root 0400, 73 bytes) rest on a 2026-09-03 board line.
- OpenRouter honours each reasoning-effort level for DeepSeek; ZDR coverage of
  the Non-frontier group — unverifiable from this repo by construction.
- The lane shadow period's agreement rate: no diff tool, no measurement.
- Prices in lanes.md and the seat README: hand-transcribed, mutually inconsistent.
- The seat's shared-`DSH_HOME` race and the 2026-09-04 smoke test: narrative
  evidence, no regression test.
- restic exits 3 when a declared backup path is missing: described, untested.
- The push needs an unlocked keyring: described, never exercised (VM uses a fake CLI).
- "A NixOS switch does not start newly enabled user timers": stated gotcha, no test.
- Whether `checks.unit` runs as uid 0 (which would un-skip the mount tests):
  could not be determined without a build.

## Appendix: refuted or dropped

- *Seat model can read its key from the environment* — refuted. The harness scrubs
  `/KEY|PASSWORD|SECRET|TOKEN/i` from every child env; a live probe already showed
  the variable empty. The key *file* remains readable, which is recorded and accepted.
- *`render.py::_hm` unescaped* — dropped, no verifier reached it. Re-listed above
  as a tests-area note; the evidence is concrete.
- *Reasoning-token gap means costs are undercounted* — refuted. Reasoning is billed
  inside `outputTokens`, and the ledger takes dollars from result files and the
  activity export, not from token counts. Only the itemisation column is missing.
- *O4 is an untracked clickjacking exposure* — refuted. The headers shipped
  (`serve.py:425-427`), are tested, and were probed live at switch #9. O4 is a
  residual browser observation, open for ~18 h. Board hygiene at most.
- *Helm Home's polkit flip breaks the only caller* — refuted. polkit falls back to
  the user's display session; gnome-shell's agent is registered. Real residual:
  the phone view cannot answer a desktop dialog.
- *"Work here" re-introduces the removed Console flow* — refuted. The spec decides
  tiles-with-pop-out in three places, and the removal decision explicitly predicts
  the Helm Home verbs as its successor.
- *Dated debt has no ledger* — refuted. D1-D10 and O1-O11 tables exist, with an
  append-only closure record. Residual: the board does not point at them.
- *Two profile switches can run at once* — refuted. `switch-to-configuration` takes
  a root-owned exclusive flock on `/run/nixos/switch-to-configuration.lock` before
  doing anything; the second run fails closed with exit 11.
- *helm-serve's RuntimeDirectory wipe loses the switch lock and the token* —
  refuted. flock releases at process exit by design, and the token is regenerated
  unconditionally at every start. Residual: the docs call it "per-boot" when it is
  per-process.
- *Worktree-scoped memory dirs are unbacked* — refuted. The two worktree project
  dirs contain transcripts, not memory; transcripts are deliberately outside the
  backup list for every project.

## Method

Eleven readers, one dimension each, all read-only: no `sudo`, no switch, no unit
started, no secret read. Each finding then went to three critic lenses — factual
(try to refute the mechanism against the current tree and live host), materiality
(is this already a recorded decision or parked debt?), actionability (is the fix
build-only, and is the proposed test red today?). A finding survived if at least
one lens kept it; corrections and improved tests from the critics override the
original text, and several severities were revised down that way. Findings whose
mechanism was disproved are in the appendix rather than deleted.

Gaps in this review. The confirmed-findings payload reached the writer truncated
partway through the CLAUDE.md dimension, so the board, invariants, tests,
plans-debt, process, hygiene, flake-inputs and Helm Home dimensions are
represented through their coverage notes and cross-references rather than their
own finding text — the counts above (60 and 29 confirmed) are larger than the
tables here. Flake input ages were not examined by any reader. No `nix flake
check` or `nix build` was run, so every check cited is read from source, not
executed; the one exception is the test suites, which the tests reader ran
(`pytest tests/helm` 117 passed, `bats tests/unit/80-helm-switch.bats` 12 ok) and
mutated. The broker, lane and factory test suites were sampled, not audited —
treat "no findings there" as unmeasured.

## Addendum: every confirmed finding (generated from the workflow's confirmed list)

The writer above received the confirmed list truncated; this table is complete (89 rows) and machine-generated from the same run. Severities are the critics' corrected ones. Full claim, evidence, fix and test text per id: the run's `confirmed` payload (scratch `env-review-confirmed.json`, kept with the session).

| Sev | Area | Id | Effort | Finding | Fix (short) |
|---|---|---|---|---|---|
| blocker | board | process-1 | M | The board's START HERE block — the one text a fresh session must read — contradicts itself and is stale | Make START HERE an edited-in-place block, never a prepend target. Restructure docs/OPERATIONS.md as: (a) exactly one `## START HERE` section… |
| blocker | security | r2-1-1 | S | Broker allowlist and credential injection are keyed on the client-controlled Host header, not the destination … | Decide on the real destination: use `flow.request.host` (the address mitmproxy will connect to) for the allowlist, inject, deny_paths and bo… |
| major | claude-md | claude-md-2 | S | CLAUDE.md's 'How work is done here' describes dark-factory.js/Workflow tool as THE mechanism; actual work for … | Add a sentence: 'Day-to-day task dispatch now runs through the headless seat driver (tools/factory/seat/, README there) — see docs/OPERATION… |
| major | flake-inputs | hygiene-2 | L | nixpkgs-host pin is 8 months old and runs the live host | Bump nixpkgs-host to a current nixos-25.05 (or 25.11) channel head, run `nix flake check -L`, the VM tests, and `nix store diff-closures /ru… |
| major | helm | helm-code-1 | XS | serve.py reads the switch journal across all boots (no -b), so the page can report a previous boot's switch as… | Add `-b` to the argv in `_journal_switch_records` (pkgs/helm/serve.py:283). While there, add `-g '^helm-switch: (begin\|end) '`: the unit's … |
| major | helm | helm-code-5 | S | Under control.enable the page can serve arbitrarily stale tiles with a "live" stamp beside them | In `_page` (serve.py:451), read `/var/lib/helm/status.json`, compute `now - generated_at`, and when it exceeds 2x `interval_s` render a warn… |
| major | helm | helm-runbooks-1 | S | flake-check tile can only be green for ~20-45 min a day: "rev == HEAD" is the wrong proxy | Grade the tile against work, not against a commit id. (1) Compute a non-docs delta: `git -C <repo> diff --quiet <checked rev> HEAD -- . ':!d… |
| major | helm | helm-runbooks-2 | S | drift tile goes red on every docs-only board commit; the toplevel-outPath alternative cannot work as stated | Keep `live == HEAD` as the ok case, but when they differ run `git -C <repo> diff --quiet <live base rev> HEAD -- . ':!docs'` first: clean ->… |
| major | helm | invariants-3 | S | Any process running as uid 1000 — including the seat — can trigger a root profile switch through helm-serve; t… | Move plan D11 §1's residual-risk paragraph into docs/runbooks/helm.md verbatim, extended to name agent processes running as the operator, an… |
| major | helm | r2-3-1 | S | backup-parity tile cannot report a push failure: the regex matches only the success line | Make the tile read the unit result, not prose: prefer `systemctl --user show -p Result -p ExecMainStatus -p InactiveExitTimestamp proton-dri… |
| major | helm | r2-3-2 | S | Every clock on the Helm page is UTC printed as a bare HH:MM; the operator's clock is CDT | In render.py:_hm convert to the local zone before formatting (`datetime.fromisoformat(s).astimezone().strftime("%H:%M")`) and in collect.ren… |
| major | helm | r2-3-3 | M | No tile distinguishes "the nightly job never completed" from "it completed" | Extend `_TIMER_PROPS` to include `Result` and `ExecMainStatus` on the corresponding *.service and fail the timers tile when a unit's last re… |
| major | helm-home | helm-code-3 | M | Two different documents are both called status.json, and neither is versioned — the contract Helm Home is desi… | Version the collector document (`"schema": 1`) in collect.py:519-524 and add `active_profile` (read /etc/helm/profile) and the system genera… |
| major | helm-home | helm-home-2 | M | The "build-time check" on a flake's helm declaration cannot run: sibling flakes are not inputs of this repo | Export the checker from this repo as a pure library output (`lib.checkHelmDeclaration :: decl -> flakeOutputs -> derivation`) with its own n… |
| major | helm-home | helm-home-3 | M | "Nothing in GNOME changes" contradicts "Super+Home raises it" on a Wayland session | Decide the mechanism in the plan and amend line 35-36 accordingly: declare a gsettings custom keybinding through the host config (it is a GN… |
| major | helm-home | helm-home-9 | XS | Whether Super+Home is free and whether a keybinding-spawned raise wins focus is unmeasured | Before planning, run in the operator's own session: `gsettings list-recursively org.gnome.desktop.wm.keybindings org.gnome.shell.keybindings… |
| major | other | r2-2-1 | M | basket teardown can return with decrypted plaintext still mounted and readable | Make cmd_teardown a fully-ordered, failure-tolerant sequence rather than a `set -e` script: loop `umount` until `$mnt` is no longer a mountp… |
| major | other | r2-2-2 | M | No EXIT/ERR/signal trap in basket.sh, and teardown refuses to clean the state a failed mount leaves | Install `trap cleanup EXIT INT TERM` in cmd_mount that unmounts the staging tmpfs and removes both directories unless the mount completed su… |
| major | other | r2-2-5 | S | `basket verify` reports success for a store entry that can never be decrypted | Make cmd_encrypt pack once (to a temp file inside the store entry, or via `tee >(sha256sum)`) so the hash and the ciphertext are provably th… |
| major | runbooks | helm-runbooks-3 | XS | Both runbooks say flake-check reads RED after a switch; the code returns WARN — helm.md contradicts itself in … | Rewrite the flake-check paragraph in docs/runbooks/helm.md to list exactly the code's three branches (fail: missing/unreadable file or a fai… |
| major | runbooks | helm-runbooks-5 | XS | Runbooks still say the broker tile is grey "no broker instance configured" — core has the openrouter instance … | Rewrite the broker paragraph in docs/runbooks/helm.md and the expectation in docs/runbooks/switch-helm-gaming.md: on core today the tile is … |
| major | runbooks | lane-runbooks-1 | S | backup.md's "what is backed up" list is 5 of the 11 paths restic actually walks | Rewrite docs/runbooks/backup.md:14-19 to enumerate all eleven paths (or to name the four groups: this repo + /etc/nixos, ~/flakes, ~/strateg… |
| major | runbooks | lane-runbooks-3 | S | lanes.md describes the seat's picker as Pro plus Flash; the wrapper offers three more, non-DeepSeek models | Update lanes.md's picker paragraph to list all four defaults and their roles, state which of them the account ZDR group actually covers (or … |
| major | security | invariants-1 | S | The dsh seat holds the OpenRouter key in plaintext and bypasses the broker — invariants 2 and 3, with no decis… | Either (a) record a decision that scopes the exception explicitly — which agent, which data class, what compensating controls, and what clos… |
| major | security | invariants-6 | M | The classification model that invariants 1/4/5/6 rest on has zero instances on the live host, while every agen… | Either declare the harnesses that actually run as `services.baskets.agents` entries (even with `egress = "broker:openrouter"` and no baskets… |
| major | security | r2-1-3 | S | denyPaths is a raw startswith on the unnormalized path — %6d, //, /./ and /../ all forward the request with th… | Normalize once before matching — split off the query, percent-decode, collapse duplicate slashes, resolve `.`/`..`, casefold — and compare t… |
| major | security | tests-4 | S | Three serve.py hardening lines survive mutation: the 64 KB body cap, the bad-Content-Length branch, and nosnif… | Add three assertions: a POST with `Content-Length: 999999` (and a short body) returns 400 and never reaches run_switch; a POST with `Content… |
| major | tests | invariants-5 | M | The local-only path list — the only data-class control in force — is triplicated in three languages with no si… | Generate one list from Nix — a single attribute in nixosModules/modelLane.nix (or a small lib) rendered into a store JSON that the wrapper, … |
| major | tests | tests-1 | S | checks.helm-control-assertion-negative-profiles is vacuous: it supplies its own assert, the module has none | Add the missing assertion to nixosModules/helm.nix's control assertion list: `assertion = lib.all (p: p == "base" \|\| (config.specialisatio… |
| minor | board | process-2 | M | 106 KB board, 6 live START HERE headings, no archive rule, and no check in the repo reads it | Adopt a written move rule in the "Standing policy — documentation" section (:976): START HERE is rewritten in place; a superseded START HERE… |
| minor | claude-md | claude-md-1 | S | README.md status paragraph is ~2 days stale (last touched 2026-09-04 03:46, commit 18d7a17) | Replace the whole Status paragraph with a short pointer: 'Status: see docs/OPERATIONS.md START HERE for the current generation, switch, and … |
| minor | claude-md | claude-md-3 | M | Architecture section omits Helm, model lanes, the dsh-openrouter seat, and the ledger — all live subsystems wi… | Add bullets: '- **Helm** (nixosModules/helm.nix, pkgs/helm): localhost-only status dashboard + profile-switch/workspace-launch control plane… |
| minor | factory | lane-runbooks-2 | S | Seat driver scripts exec siblings from ~/factory/bin, not from their own directory as the README claims | Set FACTORY_BIN from the sourcing script's own directory (`FACTORY_BIN=${FACTORY_BIN:-$here}` in each script after factory-lib.sh is sourced… |
| minor | factory | lane-runbooks-9 | S | Seat README's script list omits factory-usage.py and launch-today.sh, and launch-today.sh is a dated one-shot … | Document factory-usage.py in the script list, and either delete launch-today.sh (its content is reproducible from the factory-wave examples)… |
| minor | factory | process-3 | S | The stated boundary between the two factory drivers is false: dark-factory.js grew its scheduler, the seat REA… | Write the boundary down once, in tools/factory/seat/README.md and CLAUDE.md's "How work is done here": dark-factory.js is the Claude-model f… |
| minor | factory | process-4 | S | An ungated second copy of the seat driver lives at ~/factory/bin, and the repo's own launch script still point… | Retire ~/factory/bin. Point launch-today.sh (and the README's "Running a wave" recipe, which already uses tools/factory/seat/) at the repo p… |
| minor | factory | r2-4-4 | M | ~/factory/ws clones are excluded from backup as 'transient... discarded per run', but nothing discards them --… | Either add a cleanup step to tools/factory/dark-factory.js / the seat driver that removes ws/<run>/<key> after a run merges or is abandoned,… |
| minor | flake-inputs | hygiene-1 | M | JS has no formatter/linter — only a parse-only node --check syntax gate | Add an ESLint (flat config, `eslint.config.js`) and Prettier pass for `tools/factory/dark-factory.js` and `tests/factory/*.mjs`, wired into … |
| minor | helm | helm-code-8 | XS | One odd line in a broker audit log blanks the whole broker tile, hiding every denial | In collect.py:333-346 skip records defensively rather than aborting the tile: `if not isinstance(rec, dict): continue`; `if not isinstance(t… |
| minor | helm | helm-runbooks-4 | XS | The status page encodes every verdict as colour alone — no tile ever prints "warn" or "fail" | Print the verdict word in the tile, e.g. `<h2>{name} <span class="verdict">{status}</span></h2>` with a muted uppercase style, keeping the b… |
| minor | helm | r2-3-4 | S | flake-check.json records HEAD, never whether the tree was dirty or whether HEAD moved during the run | In the flakeCheck script record `dirty` (`git status --porcelain` non-empty) and re-read HEAD after the check; write `rev_before`, `rev_afte… |
| minor | helm | r2-3-6 | S | The Proton mirror runs twice every night: the post-backup kick and the 00:30 timer both fire | Give the push unit a cheap idempotence gate: record the pushed snapshot-set fingerprint under $XDG_STATE_HOME after a successful run and exi… |
| minor | helm | tests-2 | XS | tile_flake_check reports green when `git rev-parse HEAD` fails; no test covers the degraded path | Return `"unknown", "git rev-parse HEAD failed", {**detail, "stderr": head_cp.stderr.strip()}` from tile_flake_check when head_cp.returncode … |
| minor | helm | tests-7 | S | A workspace's `basket` id is unvalidated in the module and untested in the launcher's quoting case | Extend the name-regex assertion in nixosModules/helm.nix:616-620 to include `lib.filter (b: b != null) (map (w: w.basket) (lib.attrValues cf… |
| minor | helm-home | helm-code-10 | M | Escaping, palette and page skeleton are duplicated across collect.py, render.py and serve.py — extract before … | Add `pkgs/helm/page.py` (single `esc`, `PALETTE`, tile markup, page skeleton) imported by collect.py, render.py and serve.py, and `pkgs/helm… |
| minor | helm-home | helm-home-4 | S | The list of flakes the home shows has no declared source, and the option it was to live beside is empty | Add `services.helm.home.flakes = attrsOf (submodule { path; declaration ? "<path>#helm"; profile ? null; seats ? []; })` in nixosModules/hel… |
| minor | helm-home | helm-home-7 | S | No test backs "disabling services.helm.home returns the machine to today's state" | Add an eval check that builds the drvPath of `nixosConfigurations.core.config.system.build.toplevel` with `services.helm.home.enable = false… |
| minor | helm-home | helm-home-8 | M | How the GTK app is tested headlessly is unspecified; the a11y-driven VM proof is unmeasured on this pin | Measure it first: a throwaway VM that boots GNOME, autostarts a five-line GTK4 window and asserts dogtail can find it by accessible name. Sp… |
| minor | other | r2-2-10 | S | doctor's leak detector hardcodes /run/baskets while mount and teardown both accept --runtime-dir | Have the probe enumerate actual mounts rather than one directory: scan `<root>/proc/self/mountinfo` for tmpfs sources matching `basket-*` (t… |
| minor | other | r2-2-4 | S | No mutual exclusion anywhere: mount's guards are check-then-act, and `basket lock` is a lockfile, not a lock | Take an exclusive `flock` on a per-id lock file (e.g. `$runtime_dir/.basket-lock-$id`, created before the staging directory) at the top of b… |
| minor | other | r2-2-6 | XS | basket doctor prints "PASS swap — no active swap" when it cannot read /proc/swaps at all | Add a third branch: when `$root/proc/swaps` is missing or unreadable, `probe WARN swap "cannot read /proc/swaps — swap state unknown"`. Appl… |
| minor | process | process-7 | S | The concept-per-turn ritual: 8 of 17 concepts are cited nowhere and changed nothing | Change the rule from a per-turn quota to a trigger: write a concept when a turn produced a reusable idea that a later plan or decision will … |
| minor | runbooks | helm-runbooks-6 | XS | switch-helm-gaming.md still teaches the pre-v1 manual profile switch while Helm v1 control is live on core | Mark docs/runbooks/switch-helm-gaming.md as the record of the 2026-09-03 switch and superseded for profile switching, with a one-line pointe… |
| minor | runbooks | lane-runbooks-4 | S | lanes.md's ledger contract ("only a successful job appends a line") is false for --kind dsh | Either make run_dsh match the documented contract (append only when returncode == 0), or — better, since a failed harness run still spent to… |
| minor | runbooks | lane-runbooks-5 | S | Seat README and lanes.md give contradictory DeepSeek V4 Pro prices for the same date | Keep one price table (tools/ledger/schema.md already defines a price-table CSV format) and have both runbooks point at it with the date it w… |
| minor | runbooks | lane-runbooks-6 | XS | lanes.md's ZDR gate still reads "not yet confirmed" with a blank date, months after the board recorded it done | Fill in "Date set: 2026-09-04" (or the exact date the operator confirms) at lanes.md:130 and delete the "Not yet confirmed done" sentence, c… |
| minor | runbooks | lane-runbooks-7 | M | push.sh permanently deletes /trash/<basename>, weaker than the runbook's "only ever deletes the objects it its… | Either address the deletion by the id the trash call returns (if the CLI reports one) and drop the basename path, or soften backup.md:86-87 … |
| minor | runbooks | lane-runbooks-8 | XS | Seat README still says the XDG_CACHE_HOME workaround has not landed in the wrapper; it has | Rewrite README.md:210-215 to say the wrapper sets XDG_CACHE_HOME and the driver only honours an inherited override, and cite dsh-openrouter.… |
| minor | runbooks | r2-4-1 | S | The only per-lane OpenRouter spend record (/var/lib/lanes/*/ledger.jsonl) is outside every backup path | Add /var/lib/lanes to services.proton-backup.paths in hosts/core/proton-backup.nix (needs root read access; add a group or ACL the backup us… |
| minor | security | helm-code-6 | S | helm-serve — the only network listener, and the only path to a root unit — has the thinnest sandbox in the mod… | Add to nixosModules/helm.nix:670-684: `RestrictAddressFamilies = [ "AF_UNIX" "AF_INET" "AF_INET6" ]` (AF_UNIX is required — systemctl/system… |
| minor | security | invariants-4 | S | Nothing stops the seat from reading local-only trees from a permitted workspace — only the cwd is checked | Extend hook-guard's protected-path check to bash commands (argument-path scan against the same prefix list) as a tripwire and audit record, … |
| minor | security | r2-1-2 | XS | The "SNI-mismatch check" is only a deny-reason string; a mismatched SNI on an allowlisted Host is allowed and … | Make the mismatch a denial, not a reason: after resolving the routed host, deny when `client_conn.sni` is set and differs from it (audit rea… |
| minor | security | r2-1-4 | S | The ZDR body patch is opt-out by the client: wrong-cased or absent content-type forwards the body unpatched, a… | Fail closed on a patched host+prefix: deny (audit reason e.g. `zdr-unpatchable-body`) when the body is absent, not decodable as a JSON objec… |
| minor | security | r2-1-6 | XS | audit.jsonl is world-readable, never rotated, and carries client IPs and full request paths including query st… | Set `UMask = "0027"` on egress-broker-<name>.service, add a tmpfiles/logrotate rule bounding audit.jsonl, and store the path with the query … |
| minor | security | r2-1-7 | XS | The lane's credential is injected on every openrouter.ai path, and host-core asserts it stays that way | Set `inject.<host>.paths = [ "/api/v1/chat/completions", "/api/v1/models" ]` (whatever the lane and dsh actually call — the live audit says … |
| minor | security | r2-2-3 | XS | `basket teardown <id>` never validates the id: root umount and rmdir of an arbitrary path | Apply the manifest id regex to the teardown argument (and to any id used to build a path) at the top of cmd_teardown, dying on anything that… |
| minor | security | r2-4-2 | S | Egress-broker audit.jsonl (the only record of what traffic was ever allowed/denied) is outside the backup path… | Add /var/lib/egress-broker to services.proton-backup.paths (the CA private-key subdirectory can stay excluded since mitmproxy regenerates it… |
| minor | tests | process-6 | M | The falsifiability decision promises a generated vacuous-test count; nothing in tools/ records one | Either implement it — have dark-factory.js's review phase emit a `findings[].class` and tools/ledger/factory.py aggregate `vacuous-test` per… |
| minor | tests | r2-2-7 | S | The determinism of the pack — what invariant 4 rests on — survives mutation of every flag that provides it | Replace the same-tree determinism test with a cross-tree one: build two directories with identical contents but different mtimes, ownership … |
| minor | tests | r2-2-9 | XS | "plaintext never lands outside the target dir" is vacuous and fails on unrelated /tmp contents | Assert the real property instead: that after a decrypt into `out`, no file outside `out` under the test's own temp dir contains the payload,… |
| minor | tests | tests-8 | M | The basket mount lifecycle has no coverage inside `nix flake check`, and bats skips are invisible in the check… | Either run 30-mount.bats inside a NixOS VM test (VM tests already run as root under `nix flake check`, the way checks.integration and checks… |
| note | claude-md | process-9 | S | CLAUDE.md's check-name list is hand-maintained and accurate today, but nothing keeps it that way | Generate the list instead of writing it: emit it from `nix flake show --json` into a checked-in file that the lint gate diffs against CLAUDE… |
| note | factory | r2-4-6 | M | cowork.nix carries 562 lines (391+125+46) and one synthetic eval-only check for a subsystem untouched since 20… | Either add a check that evaluates hosts/core with services.cowork.enable overridden to true (a `nixosSystem { modules = [ ./hosts/core ... ]… |
| note | flake-inputs | r2-4-3 | S | No automatic GC is configured anywhere; 39 unpruned system generations plus a stale GC-rooted `result` make he… | Either configure nix.gc (schedule + keep-generations bound) and update helm.md's scenario to reflect when it can actually fire, or drop the … |
| note | helm | r2-3-8 | XS | Every staleness threshold is measured from the job's start, not its completion | Record `finished` alongside `started` in the JSON and age the tile from `finished` (or from `started + duration_s`), keeping `started` for d… |
| note | helm-home | helm-home-10 | L | Proposed parallel decomposition for Helm Home sub-project 1 (waves H51-H59) | Wave 0 (orchestrator, not agents): decide D-H1 who calls polkit and what happens to the page's Switch; D-H2 where the declaration checker li… |
| note | hygiene | hygiene-4 | XS | One orphaned research digest: docs/research-2026-09-02-comfyui-tag-selection.md | Either add a citation from the media/ComfyUI plan or module that used this research, or note in the file itself that it was superseded (e.g.… |
| note | hygiene | hygiene-5 | XS | examples/manifest.json is orphaned — no current test or code references it | Either wire examples/manifest.json into a bats test via `basket validate-manifest examples/manifest.json` (cheap, closes the drift gap) or r… |
| note | hygiene | process-8 | S | 38 review reports with no index, and two docs are mode 0600 so another user or a stricter sandbox cannot read … | Generate docs/reviews/INDEX.md from the files themselves (date, wave, keys, verdict line, one-line finding) with a small script run in the l… |
| note | other | r2-2-8 | S | doctor's age-plugin probe can never warn: the package puts age-plugin-yubikey on its own PATH | Probe the host rather than the process: check for the plugin under `$root/run/current-system/sw/bin/age-plugin-yubikey` (or accept an overri… |
| note | plans-debt | plans-debt-1 | XS | Cleartext Proton credential in rclone.conf: 3-day-old operator TODO never closed | Either have the operator run the shred now, or add a build-time check (e.g. an acceptance-script assertion, or a `tests/acceptance/backup.sh… |
| note | plans-debt | plans-debt-4 | XS | S12 commit-metadata decision open since fix-round-2, still unresolved on today's board | Have the operator make the call (rewrite the commit message vs. accept as-is) and file a one-line docs/decisions/ entry so it stops reappear… |
| note | runbooks | helm-runbooks-7 | XS | The page shows ten tile-shaped sections; helm.md and the acceptance drill say nine | Say "nine health tiles, plus the Profile card above them" in docs/runbooks/helm.md and docs/runbooks/switch-helm-gaming.md, and give the con… |
| note | runbooks | lane-runbooks-10 | XS | hosts/core/lanes.nix comment still calls the lane's ExecStart "T2's stub" | Delete the "still T2's stub" clause from hosts/core/lanes.nix:7-8, keeping the accurate half (nothing is wantedBy anything; the operator sta… |
| note | security | invariants-7 | XS | Seat traffic carries no per-request ZDR/data-collection block — the belt the decision argued for is missing on… | Fill the date line in docs/runbooks/lanes.md from the board entry, and add one sentence to the runbook's seat section saying the per-request… |
| note | security | invariants-8 | XS | Decided and recorded: the desktop app's Claude Code runs unconfined on the host, and the machine-wide lockdown… | No change to the wiring. Give the deferral a dated debt line on the board with an owner, so "the orchestrator's own confinement is designed"… |
| note | security | r2-1-5 | XS | A forwarded request can end up with no audit line at all: mitmproxy swallows hook exceptions and _body_bytes d… | Wrap `_audit` in its own try/except that never propagates, parse Content-Length defensively (return None/0 on ValueError and record it as un… |
| note | security | r2-1-8 | S | The broker unit — a long-running parser of untrusted TLS and untrusted upstream bytes — has the thinnest sandb… | Add `SystemCallFilter = "@system-service"`, `SystemCallArchitectures = "native"`, `RestrictNamespaces = true`, `RestrictSUIDSGID = true`, `P… |
| note | tests | tests-6 | XS | validate_post's _TARGET_RE is dead code: removing it leaves the whole suite green | Keep the regex (cheap belt-and-braces) but make it falsifiable: assert in a test that validate_post rejects a target that IS in the allowlis… |
