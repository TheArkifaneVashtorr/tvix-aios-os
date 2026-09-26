# The OpenAI lab spike — plan (2026-09-08)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) or superpowers:executing-plans, task-by-task. Steps use checkbox (`- [ ]`) syntax. The seat driver and `dark-factory.js` both read the `### KEY (kind, size) — title` sections below; every section carries `dependsOn` (where it has one), `repo`, `touches`, `acceptance`, `commit subject`. A seat sees only `## Global Constraints`, `## Assumptions` and its own section (`factory-brief <plan> <KEY>` is the whole contract).

**Goal:** three small, Opus-gated tasks on a fresh flake (`~/flakes/openai-lab`, pinned to `nixos-agent-env` by exact revision) built end to end by the `codex` arm of the seat driver, so its gate record — first-try yield, named mutants dead, rounds to land, the `evidence report ladder` row for `route = codex/<kind>/<size>` — gets three more entries beside CX2/CX2b's two, on work Codex did not already half-own.

**Spec:** `docs/superpowers/specs/2026-09-08-openai-lab-spike-design.md` (940 words, size S; the operator's word 2026-09-08 ~18:55 per the board's START HERE). Two places this plan goes past the spec's wording: OL2's shape is typed from the spike's own name, not measured (Open decision 1); Assumption 10 corrects the spec's claim about how the ladder groups a codex row.

**Packet of record:** `scratchpad/openai-lab/facts.md` (this session's fact-gather); the lab repo's first commit `d3789ab91512b4753d4ab96aab1ac65eea1a7e81`; the pin `d2ad5c79dd4e6cdfa24e0ed20629ae1632908237` (Assumption 4 states how it is verified); `docs/ledger/repos.toml`'s `openai-lab` row already landed on `main` at `3f1ca1a` (Assumption 8) — this plan's own commit (§Dispatch Step 0) carries only the `claims.toml` gap row.

## Operator questions (each answerable in one word; the default applies if unanswered)

1. **Does OL2 block on a real `rate_limits` measurement before landing, or land on typed fixtures with a gap claim opened (as CA1 opened `codex-failure-strings-unmeasured`)?** Fact: no `rate_limits` line appears anywhere in this repo today (Assumption 7); confirming one means opening a file under `~/.codex`, forbidden to this fact-gather but not to Codex's own task session, running as the operator. **Recommendation: land on typed fixtures, open the gap claim, make OL2's Step 1 the first real measurement against a path the operator names (Operator item 3).** **Default: yes.** A sequencing call, not an invariant.

## Spec-to-task map

| spec item | task or `out:` |
|---|---|
| (1) OL1 the flake — the pin, `checks.lint`, `checks.lab-vm`, `devShells.default`, `flake.lock` | OL1 |
| (2) OL2 the extractor — `tools/codex_limits.py`, its tests, `checks.unit` | OL2 |
| (3) OL3 the runbook — `docs/runbook.md`, the grep/bats gates in `checks.unit` | OL3 |
| Constraints — brief §3; Codex unsandboxed as the operator; nothing leaves the machine but the model call; no key in the repo; everything stays in the lab | §Global Constraints |
| Not in scope — core/Helm wiring; the store's own `codex-limit` fence kind; a lab check reading `~/.codex` directly | §Not in this plan |
| Open decision 1 (OL2's shape unmeasured) | §Operator questions Q1; OL2 Step 1; the claim in §Dispatch step 0 |
| The Measurement paragraph (first-try yield, mutants dead/named, rounds to land, the `evidence report ladder` row) | Operator item 6; Assumption 10 (the ladder's actual route grouping, measured) |

## Decisions (judgement calls, each with the reason and the alternative)

- **D1 OL2's fixtures are typed from the spike's own named shape, not measured; the gap is a claim, not a silent assumption** (Assumption 7). Alternative rejected: block OL2 on a hand-read of a real rollout first — nothing schedules that, and this fact-gather's constraints do not bind Codex's task session.
- **D2 Acceptance names for all three tasks are the lab's own `checks.${system}` names (`lint`, `lab-vm`, `unit`), never a `docs/MAP.md` name.** `draft_rules` exempts a task attributed to another repo from both the MAP-membership and subject-match checks (`attributed_elsewhere`, ~1796) — the CX2/CX2b convention. Alternative rejected: a real MAP.md check as a stand-in — none exists for a repo that does not exist yet.
- **D3 OL2 and OL3 both `dependsOn` OL1 only, not each other, though both touch `flake.nix`.** `wave_structure`'s `seat_group_lists` unions same-wave keys whose `touches` overlap into one group (§Waves: `[["OL2","OL3"]]`). Alternative rejected: `dependsOn: OL1, OL2` on OL3 — a second `factory-wave` call for something the driver already merges for free.
- **D4 `docs/ledger/repos.toml`'s row already landed standalone at `3f1ca1a`, not by this plan's commit.** Re-run: `git status --short` clean, `git log --oneline -- docs/ledger/repos.toml` names `3f1ca1a` newest (Assumption 8); Step 0 carries only the `claims.toml` gap row. Alternative rejected: re-add the TOML block as the judged draft did — a byte-identical hunk `git commit` refuses.
- **D5 `devShells.default` (OL1's Step 2) lists `git`, so `nix develop -c git commit -F <msgfile>` already works for OL1's first commit.** No plain-`git` exception, no `FACTORY_BRIEF_EXTRA` override (closes the OL1-Step-4/`factory-brief` contradiction the judgement found). Alternative rejected: the judged draft's plain `git commit -F <msgfile>` for OL1 alone — true before Step 2, false after; one package name beats an exception told twice.
- **D6 No `githooks/pre-commit` ships with OL1.** Three S tasks is not a standing project; `AGENTS.md` carries the discipline, the Opus gate the enforcement. Alternative rejected: `~/flakes/codex`'s two-line hook from day one — every OL commit's Step 3 already runs the same checks by hand, so a hook would only duplicate it; parked if the lab outgrows three tasks.

## Global Constraints

- **Build-only.** No `sudo`, `nixos-rebuild`, `systemctl start/stop/restart/enable`, basket mount/teardown, reading `/var/lib/secrets/*`, `~/.config/openrouter/key`, `~/.config/restic/password`, or `~/.codex/auth.json`. Codex runs under `--sandbox danger-full-access` as the operator (decision point 4) — accepted, not widened: no key moves, no Nix expression on `core`, no new network path. OL2's script/tests never open `~/.codex`; every fixture is hand-built JSONL (the exception — Codex reading the operator's path, Operator item 3 — is a manual measurement in `FACTORY-NOTES`, never fixtured).
- Commits: exactly ONE per task, on `task/<KEY>`; `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null`. Subject byte for byte from the section; trailers `Generated-By: codex-cli <ver> / <model> (codex exec, factory run <RUN>)` then `Co-Authored-By: Codex CLI <ver> <noreply@openai.com>` (`<ver>` from `FACTORY_SEAT_VERSION`).
- TDD: the failing check first, shown red, then green; a test that cannot fail is `vacuous-test`. Every Tests row names the mutant that turns it red; paste it in the commit body. `pkgs.runCommand`'s shell runs under Nix's implicit `set -e` — no `|| true` anywhere in `checks.lint`/`checks.unit` (OL2's Z10 proves this is load-bearing).
- **`touches` is a contract.** A file outside it is a deviation, named `Deviation: <path> — <reason>`. `flake.nix` is the only file OL2 and OL3 both touch (D3). A transient fixture proving a mutant red, then removed before commit, is not a deviation (OL1's Y3, Y5, Y6, OL2/OL3's mutant rows).
- Python is stdlib only in `tools/codex_limits.py` and its tests, as for `pkgs/evidence`/`tools/factory/seat`; `ruff format` (88 cols) governs layout.
- Nix style: statix rejects `{ ... }:` headers with no real arguments — write `_:`.
- No secrets in the repo; no fixture may quote a key, token, or a path under `/var/lib/secrets`; a fixture `session` id is a made-up UUID, never a real `~/.codex/sessions` one.
- The result block ends every reply exactly: `FACTORY-RESULT status=done|partial|failed` (space, no colon); `FACTORY-CHECKS <name>=<pass|fail|not-run> …`; `FACTORY-COMMITS <n>`; `FACTORY-NOTES` one line. Never copy it into a project file.

## Assumptions

1. `flake.nix:697` exports `nixosModules.evidenceStore = import ./nixosModules/evidenceStore.nix;` — reachable as `nixos-agent-env.nixosModules.evidenceStore`. `options.services.evidence-store` (`:26-49`): `enable`, `path` (default `/var/lib/evidence`), `owner`/`group` (default `dalhaka`/`users`), `package`; `mkIf cfg.enable` creates `${cfg.path}`/`${cfg.path}/ledger` at 0750 via `systemd.tmpfiles.rules`, naming `cfg.owner`/`cfg.group` with no existence check. A bare `runNixOSTest` machine has neither. **Corrected at OL1's gate (2026-09-08): this reason is false.** The check exits 0 with the module defaults left alone — `systemd.tmpfiles.rules` names an owner without an existence check, so a user the VM lacks does not fail the boot, and `tests/lab-vm.nix:13-14`'s `root`/`root` override is inert. Keep the override as an explicit pin if OL2 or OL3 wants one, but never as a requirement, and never cite it as the reason a bare machine needs it.
2. `evidence.py:550-614`, `record-check`: `--name`, `--rev` (`REV_RE`, a full 40-hex id — an all-zero string is a valid non-git-object fixture), one of `--ok`/`--fail`, `--class` (`choices = ("unit","eval","vm","nix-check","curl","browser","operator","unmeasured")`, `:39`), `--src`, all required; `evidence.append()` (`evidence.py:61`) validates against `streams.validate`, adds the envelope (`v`, `ts`), and appends to `checks.jsonl` under `$EVIDENCE_STORE` (default `/var/lib/evidence`).
3. `flake.nix:5-6` pins `nixpkgs` (`34ab990…`) and `nixpkgs-host` (`a5cc6f2…`, the pin `core` builds against — `:702`). `checks.lab-vm` imports a module written for `core`, so the lab's `nixpkgs` follows `nixos-agent-env/nixpkgs-host`, never plain `nixpkgs`.
4. The pin `d2ad5c79dd4e6cdfa24e0ed20629ae1632908237` is the spec's own named revision, not `HEAD`: `git -C /home/dalhaka/nixos-agent-env rev-parse HEAD` → `1b35447cee4347e22380cb61b158e9e0b9e58817` this session (three docs commits ahead: the judgement/spec files, then this Ship commit). It IS an ancestor: `git merge-base --is-ancestor d2ad5c79dd4e6cdfa24e0ed20629ae1632908237 HEAD` exits 0, silent. Bumping it: edit `rev=`, `nix flake lock --update-input nixos-agent-env` (OL3 item 1) — never a bare `?ref=main` (OL1's Y4).
5. `~/flakes/codex/flake.nix` (`3f96d7a`) is the closest model for a small flake's `checks.${system}`: a flat attrset of `pkgs.runCommand` derivations, `devShells.${system}.default = pkgs.mkShell { packages = … ++ [ pkgs.jq ]; }`, a two-line `githooks/pre-commit` — OL1 ships no hook (D6).
6. `githooks/pre-commit` runs `treefmt --ci --config-file treefmt.toml --tree-root .`, `statix check .`, `deadnix --fail .`, `ruff check`/`ruff format --check`, plus `shellcheck`; the parent's own `checks.lint` mirrors the same four in a sandboxed copy. OL1's `checks.lint` mirrors them over the lab's tree with no shellcheck (no `.sh` file exists); its Interfaces give the derivation in full.
7. `factory-codex-usage.py`'s docstring documents Codex 0.153.4 rollout lines as `{"timestamp","type","payload"}`; `type` values `session_meta`, `turn_context`, `event_msg` (`token_count`) — no `rate_limits` type there or in the codex-arm plan's rollout survey. The spend-telemetry plan (`:39,179`, judgement row 28) names the same gap: "no task in the plan writes Codex `rate_limits` rows into any stream." `docs/OPERATIONS.md`'s START HERE names this task — the fact behind D1 and Q1.
8. `~/flakes/openai-lab` today: one commit `d3789ab91512b4753d4ab96aab1ac65eea1a7e81` (README, AGENTS.md, `.gitignore`); `git config user.name/user.email` → `dalhaka`/`operator@example.invalid` (set locally this session). `docs/ledger/repos.toml`'s `openai-lab` row is already on `main` at `3f1ca1a` (`git log -1 --format='%h %s' 3f1ca1a` → `3f1ca1a ledger: repos.toml gains the openai-lab row — the OpenAI lab spike's repo, built by Codex through the codex arm (test: lint)`) — corrected from an earlier draft's stale "uncommitted" claim (D4's re-run evidence).
9. `factory-dispatch` resolves its target repo through `<repo-path>/docs/ledger/repos.toml`, dying `no repos.toml at $toml` when absent (`:104-108`); `~/flakes/openai-lab` has none, as `~/flakes/codex` has none — every wave launches by hand through `factory-wave`. `ls ~/factory/base` → `codex codex.lock dsh-harness … nixos-skill nixos-skill.lock repo.lock`, no `openai-lab`: `factory-ws` creates the base clone on `ol1`'s first run, as it did for `cx2`.
10. `evidence report ladder` hardcodes `openrouter/implement` in its display and reads `kind`/`size` only from a `route:` shaped `implement/<kind>/<size>` (`report.py:664-670`, `_route_kind_size`). A Codex `.result`'s `route:` line is shaped `codex/<kind>/<size>` (measured: `docs/board/log-2026-09.md:35`, CX2's own line `route: codex/code/S`) — never matching `implement/…`, so every codex row groups under `kind=unknown, size=unknown` today, not `codex/<kind>/<size>` as the spec's Measurement paragraph names it. Fixing `_route_kind_size` is outside `touches` (`report.py`, not the lab) and this plan's scope; Operator item 6 reads the three gate reviews' front matter by hand instead, since at `n` under 5 the ladder prints only `insufficient (n=<n>)` regardless.

## Waves

Waves follow `dependsOn`; `wave_structure`'s `seat_group_lists` unions same-wave keys whose `touches` overlap into one dispatch group on its own (confirms D3). Run from `/home/dalhaka/nixos-agent-env`, `openai-lab` already configured (Assumption 8):

```
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check --draft <this file>
warning: Git tree '/home/dalhaka/nixos-agent-env' is dirty
evaluation warning: nixfmt-rfc-style is now the same as pkgs.nixfmt which should be used instead.
waves: [[["OL1"]], [["OL2", "OL3"]]]
conflicts: none
```

(exit 0; the `Git tree … is dirty` line is intermittent — this live repo's own untracked/modified files at call time, not this draft's; the `evaluation warning` line is `tasks.py`'s own, present even with no `--draft`. No `tasks: …` error either run.)

**No `flake.nix ~ flake.nix` rows against the spend-telemetry plan, unlike an earlier run this session.** That run's six rows were `touches_overlap()` (`:1188`) comparing bare path strings with no repo attribution, so `~/flakes/openai-lab`'s `flake.nix` string-matched `~/nixos-agent-env`'s. Commit `81ae876` (landed mid-session, `evidence: touches conflicts compare (repo, path)…`) fixed exactly this — the false positives are gone at the tool level, not worked around here.

| wave | groups | dependsOn | notes |
|---|---|---|---|
| 1 | OL1 | — | the flake: nothing else can build before it exists |
| 2 | OL2 ‖ OL3 (one group) | OL1 | `seat_group_lists` already unions them (D3) — one `factory-wave` call, two keys |

## Operator

No switch, no credential, no name, no reboot, no unit: nothing here edits a NixOS module, a host file, or `nixos-agent-env`'s own `flake.nix`. Three tasks on the `codex` arm; three Opus gates through `~/factory/bin/opus-gate.js` (CX2's mechanism for a foreign-repo task).

1. **Before wave 1 — the quota glance.** Codex's quota is the ChatGPT plan's weekly allowance; nothing programmatic reads it (design §10). If the Codex app shows it exhausted, hold `ol1`. Three S tasks are smaller than CX1b's M task (~40 min, ~82k billed), so a fresh week covers all three.
2. **After OL1.** `nix flake check -L` (in `~/flakes/openai-lab`) → `all checks passed!`.
3. **Before wave 2 — name OL2's real rollout path.** The operator points at one path under `~/.codex/sessions/…`, chosen at launch time, carried in the `ol2` launch line's `FACTORY_BRIEF_EXTRA` (§Dispatch) so OL2's tests/script never default to `~/.codex`. Acceptance: the launch line names a real, non-empty path; OL2's `FACTORY-NOTES` reports the shape found (matches the six fields, or names the mismatch) — `codex-rate-limits-shape-unmeasured`'s `closes_by` needs this (A3).
4. **After OL2.** `nix build .#checks.x86_64-linux.unit -L --no-link` → exit 0; `pytest tests/test_codex_limits.py -q` → all green (Z1–Z10).
5. **After OL3.** `… checks.x86_64-linux.unit` → exit 0 (pytest, the heading/verb assertions); `nix flake check -L` → `all checks passed!`. From `~/nixos-agent-env`: `tasks.py --root . brief | grep -F '| openai-lab |'` — today, all 13 count columns read `0`. Prediction after Ship: columns 7 (`ready`, OL1 has no `dependsOn`) and 8 (`blocked`, OL2/OL3 both `dependsOn: OL1`) become `1` and `2`, the rest stay `0` — a different pair is a finding, not the row's appearance (it already appears today).
6. **After all three land — the Measurement readback (Assumption 10).** `nix develop -c python3 pkgs/evidence/evidence.py report ladder --repo . --runs-dir ~/factory/runs --jobs-dir /var/lib/seat/jobs --min-n 5` (`docs/runbooks/evidence.md:160`) — expected: `insufficient (n=<n>)` for every codex-route group (n under 5; Assumption 10's mismatch would misname kind/size even past it). First-try yield, mutants dead/named and rounds to land come by hand from the three gate reviews' front matter (`mutants_total`, `mutants_killed`, `plan_defect`) instead.
7. **Rollback.** Each landing fast-forwards `main` to `integ/<run>`. `git reset --hard` is **refused by the orchestrator guard** (`tools/orchestrator-guard.sh:523`: `'git reset --hard is refused (history rules of the house)'`, per `seat-routing.md:282`) — rollback before landing is simply the branch not merged. After one: `git -C ~/flakes/openai-lab log --merges --oneline -3` (find `integrate <KEY> into integ/<run>`), then `nix develop -c git revert -m 1 --no-edit <that sha>`. Acceptance: `git log -1 --format=%s` reads `Revert "integrate <KEY> into integ/<run>"`.

## Dispatch

Plan file after Ship: `docs/superpowers/plans/2026-09-08-openai-lab.md`. Runs: `ol1` (wave 1), `ol2` (wave 2, both keys in one call — D3); fix rounds `ol1f`/`ol2f`; relaunch after a death `ol1b`/`ol2b`.

**Rubric row 3 (self-contained sections), re-measured at Ship:** `tools/factory/seat/factory-brief <draft> OL1 | wc -w` → 2033; `… OL2` → 2154; `… OL3` → 1729 — the whole contract each seat sees, self-contained (errata 2, 17).

**Step 0 — this plan's commit carries a gap claim for OL2's unmeasured shape (D4).** The `docs/ledger/repos.toml` row is already on `main` (`3f1ca1a`, Assumption 8) — nothing to add there. In the same commit as the plan file, `docs/ledger/claims.toml` gains:

```toml
[[claim]]
id = "codex-rate-limits-shape-unmeasured"
text = "tools/codex_limits.py's rate_limits record shape matches a real Codex rollout, not only the spike's named fixture shape"
status = "gap"
class = "unmeasured"
owner = "orchestrator"
opened = 2026-09-08
review_by = 2026-09-22
closes_by = "OL2's own task session reads the rollout path the operator names (Operator item 3) and reports the finding in FACTORY-NOTES, with fixtures corrected if the shape differs, or five Codex rate_limits lines read without a mismatch"
```

Then `check` (empty), `claims.py validate … --today "$(date +%F)"` (silent), `… write-board`, and commit `docs: plan — the OpenAI lab spike (OL1–OL3); the rate-limits-shape gap opened (test: lint)`.

**The dry-run lines.** `openai-lab` has no `docs/ledger/repos.toml` (Assumption 9), so `factory-dispatch` cannot resolve it. Pre-check, from `~/nixos-agent-env`: `… tasks.py --root . waves --repo openai-lab --plan 2026-09-08-openai-lab.md --next`, printing `"OL1"` until it lands, then the OL2/OL3 pair.

| wave | pre-check (launch only on this line) | the command (background, never a foreground tool call) |
|---|---|---|
| 1 | `… waves --repo openai-lab --plan 2026-09-08-openai-lab.md --next` → `"OL1"` | `FACTORY_SEAT=codex FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-08-openai-lab.md setsid -f bash -c 'exec tools/factory/seat/factory-wave ol1 /home/dalhaka/flakes/openai-lab "OL1" >> ~/factory/runs/ol1.wave.log 2>&1' </dev/null` |
| 2 | same command → `"OL2 OL3"` (once OL1 has landed) | `FACTORY_SEAT=codex FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-08-openai-lab.md FACTORY_BRIEF_EXTRA="OL2's real rollout path (Operator item 3): <path>. Read it first; report the shape found in FACTORY-NOTES; still never fixture from it." setsid -f bash -c 'exec tools/factory/seat/factory-wave ol2 /home/dalhaka/flakes/openai-lab "OL2" "OL3" >> ~/factory/runs/ol2.wave.log 2>&1' </dev/null` |

(Row 1 is the codex-arm plan's own recipe for a repo with no `repos.toml`, swapped; row 2 adds `FACTORY_BRIEF_EXTRA` as `launch-today.sh`'s `b1` line does for a different override, `factory-brief:145-152`.)

**The landing recipe, per key (codex-arm shape, repo swapped):** (1) keep exactly the one named commit, else `reset --hard <that sha>`; (2) if `main` moved under a touched file, `fetch ~/flakes/openai-lab main && merge --no-edit FETCH_HEAD`; (3) gate through `~/factory/bin/opus-gate.js`, commit the review in `~/nixos-agent-env`, `&&`-gated; (4) `factory-integrate <run> ~/flakes/openai-lab <KEY> && git -C ~/flakes/openai-lab pull --ff-only ~/factory/base/openai-lab integ/<run>`, gated on both exits; (5) dispatch what it unblocks (A7) — OL1 unblocks wave 2; OL2 and OL3 both landing closes the plan.

**Relaunch after a death.** Same shape as the wave lines above with `ol1b`/`ol2b` as the run and the dead key named; the diff stays in `~/factory/ws/<run>/<KEY>`. **Codex's failure classes are unmeasured** — `codex-failure-strings-unmeasured` stays open; a death here is classified by hand from the `.result`.

**Fix rounds and re-plans.** One bounded fix round `<KEY>b`, run as `ol1f`/`ol2f`; a second rejection re-plans as `<KEY>r`, never a third.

**Handoff line for the board (A11):** "openai lab spike: `2026-09-08-openai-lab.md` (OL1 → OL2 ‖ OL3); on the seat/in gate/landed: <keys>; the `codex`-route ladder row after all three (read by hand, Operator item 6, Assumption 10); next: the pre-check line above."

## Anticipation (design §4 rows whose trigger applies)

| row | trigger here | artefact |
|---|---|---|
| A1 | the plan is written | §Dispatch: run names, pre-check lines (no dispatcher — Assumption 9), launch lines from the codex arm's recipe, the landing recipe |
| A3 | a task needs a file the operator owns before a wave starts | Operator item 3: OL2's rollout path, carried in the `ol2` launch line's `FACTORY_BRIEF_EXTRA` |
| A4 | every task | each task's Tests table (Y1–Y6, Z1–Z10, R1–R3) is the pre-written mutation battery |
| A5 | a wave is dispatched to a seat | guards already landed (`FACTORY_PLAN` required, `FACTORY_SEAT` refusing before a workspace exists) bind this plan as CX2 — no new guard owed |
| A6 | a provider fail or quota runs out mid-run | the relaunch lines in §Dispatch; Codex's failure classes stay the codex-driver-arm plan's open gap |
| A7 | a landing | §Dispatch landing recipe item 5: what each landing unblocks |
| A8 | a task can close a claim | OL2 advances the spend-telemetry plan's "no producer" gap (Assumption 7); it opens the shape-measurement claim a later task closes |
| A9 | a hold is the right call | computed: quota (three S tasks under CX1b's M task), no red `lint` on `main`, no dependent switch, no paused sibling sharing a file |
| A10 | the operator will be asked something | §Operator questions Q1: one question, a recommendation, a default |
| A11 | the session will reset | §Dispatch's handoff line |

## Not in this plan

- Wiring `~/flakes/openai-lab` into `core`, Helm, or any host module; a `codex-limit` kind on the evidence store's fence (later, once OL2's shape is confirmed — §Dispatch's claim is its trigger).
- Anything reading `~/.codex` from a lab check or automated test: `tools/codex_limits.py` takes paths on argv; tests fixture the shape by hand. Operator item 3's manual read, by Codex's own task session, is not a lab check.
- A `githooks/pre-commit` for the lab (D6) — parked if it grows past three tasks.
- Closing `codex-failure-strings-unmeasured` (A6) — reused, not resolved.
- A `route = "codex"` row in `docs/ledger/routing.toml`.
- Any dollar figure for Codex spend — OL2 extracts a percentage, never a cost.
- Fixing `evidence report ladder`'s `_route_kind_size` (Assumption 10) — a `nixos-agent-env` task, not a lab one.

## Errata applied

Full detail from the 35/42 judgement lives in `docs/reviews/plan-judgements/2026-09-08-openai-lab.md`; this points at the Assumption/Decision/Task now carrying the content.

| # | change |
|---|---|
| 1, 5, 7, 14, 15 | repos.toml row already on `main` at `3f1ca1a`; D4 rewritten; Step 0 drops the TOML block |
| 2, 17 | `wc -w` re-measured on the final draft, pasted at the end |
| 3, 23 | `checks.lint` written in full; `outputs` stated; Y3's fixture is an unformatted `.nix` file, not a treefmt.toml mismatch |
| 4, 11, 24 | OL2 names every arm: zero argv (Z5), nonexistent path (Z7), missing key (Z6), no-`session_meta`+bad filename (Z8) |
| 6 | the pin, "no `repos.toml`", the codex-arm recipe stated once (Assumptions 4, 9), referenced elsewhere |
| 8 | resolved, not overridden: `devShells.default` gains `git` (D5) — no plain-`git` exception, no `FACTORY_BRIEF_EXTRA` |
| 9, 22 | one mutant per tool: Y3 nixfmt, Y5 statix+deadnix, Y6 ruff — transient fixtures |
| 10 | Y4 asserts the exact pinned sha, not just `&rev=`'s presence |
| 12 | flush-then-continue stated and fixtured (Z9) |
| 13 | OL3 rebuilt as rules: heading count (R1), one `grep -Fxq` per exact heading (R2), a bats verb-check (R3) |
| 16 | Assumption 4: the pin is an ancestor of `HEAD`, not `HEAD` |
| 18 | rollback cited to `seat-routing.md:282` and `orchestrator-guard.sh:523` |
| 19 | Assumption 2: `evidence.append()` (`evidence.py:61`), not `streams.append()` |
| 20 | `tests/lab-vm.nix` sets `owner`/`group` to `root`/`root` and asserts `systemctl is-system-running --wait` |
| 21 | Z10 (shared with OL3): a broken fixture must fail `checks.unit` itself — no `\|\| true` |
| 25 | Step 1 in three parts: pre-file red; `enable = false` bootstrap red (Y1); lint-tool mutants. Step 2 flips to `enable = true` |
| 26 | spec-map row and Operator item 6: the ladder invocation and the reviews' front matter, given Assumption 10's mismatch |
| 27 | Operator item 3: the operator names OL2's rollout path before wave 2 |
| 28 | D5, D6 each gained a rejected alternative |
| 29 | Operator item 5: today's row (already present, all zero) against the predicted post-Ship pair |

---

## Tasks

### OL1 (code, S) — the flake: pinned to `nixos-agent-env` by exact revision, `checks.lint` and `checks.lab-vm` proving the pinned evidence-store module boots, `devShells.default`

**repo:** openai-lab

**Files:**
- Create: `flake.nix`, `flake.lock`, `treefmt.toml`, `tests/lab-vm.nix`

**Interfaces:**

`flake.nix`'s `outputs = { self, nixos-agent-env, nixpkgs }:`. Inputs: `nixos-agent-env.url = "git+file:///home/dalhaka/nixos-agent-env?ref=main&rev=d2ad5c79dd4e6cdfa24e0ed20629ae1632908237";` and `nixpkgs.follows = "nixos-agent-env/nixpkgs-host";` (Assumption 3). `formatter.${system} = pkgs.treefmt;`.

`treefmt.toml` (nix now, python declared ahead of OL2 so it never touches this file):

```toml
[formatter.nix]
command = "nixfmt"
includes = ["*.nix"]

[formatter.python]
command = "ruff"
options = ["format"]
includes = ["*.py"]
```

`checks.${system}` and `devShells.${system}.default`:

```nix
let
  system = "x86_64-linux";
  pkgs = import nixpkgs { inherit system; };
  lintTools = with pkgs; [ treefmt nixfmt-rfc-style statix deadnix ruff ];
in
{
  checks.${system} = {
    lint =
      pkgs.runCommand "openai-lab-lint" { nativeBuildInputs = lintTools; } ''
        cp -r ${self} src && chmod -R u+w src && cd src
        treefmt --ci --config-file treefmt.toml --tree-root .
        statix check .
        deadnix --fail .
        ruff check .
        ruff format --check .
        grep -E '^[[:space:]]*nixos-agent-env\.url = ' flake.nix | grep -Fq '&rev=d2ad5c79dd4e6cdfa24e0ed20629ae1632908237'
        touch "$out"
      '';
    lab-vm = import ./tests/lab-vm.nix { inherit pkgs nixos-agent-env system; };
  };
  devShells.${system}.default = pkgs.mkShell {
    packages = lintTools ++ [ pkgs.python3 pkgs.python3Packages.pytest pkgs.git ];
  };
}
```

(`git` beyond the spec's literal "four linters, python3, pytest" list is D5's fix — a spec-wording deviation, not a `touches` one.)

`tests/lab-vm.nix`, `{ pkgs, nixos-agent-env, system }:` — a `pkgs.testers.runNixOSTest` whose one node imports `nixos-agent-env.nixosModules.evidenceStore`:

```nix
{ pkgs, nixos-agent-env, system }:
pkgs.testers.runNixOSTest {
  name = "openai-lab-vm";
  nodes.machine =
    _:
    {
      imports = [ nixos-agent-env.nixosModules.evidenceStore ];
      services.evidence-store = {
        enable = true;
        owner = "root";
        group = "root";
      };
    };
  testScript = ''
    machine.wait_for_unit("multi-user.target")
    machine.succeed("systemctl is-system-running --wait")
    machine.succeed(
        "evidence record-check --name lab --rev 0000000000000000000000000000000000000000 "
        "--ok --class unit --src lab"
    )
    out = machine.succeed("cat /var/lib/evidence/checks.jsonl")
    assert '"name":"lab"' in out
    assert '"class":"unit"' in out
  '';
}
```

(An all-zero 40-hex string is a valid, non-git-object `--rev` per `REV_RE` — Assumption 2. `owner`/`group` overridden to `root`/`root`: Assumption 1 states why.)

**Facts:** Assumptions 1–6.

- [ ] **Step 1: Write the failing checks and run them red, in order.**
  1. Before any file exists: `nix flake check` in the empty clone (measured this session, `git init`): `path "<dir>" does not contain a 'flake.nix', searching up` then `error: path "<dir>" is not part of a flake (neither it nor its parent directories contain a 'flake.nix' file)` — TDD's red before any file, no mutant needed.
  2. Write `flake.nix`, `treefmt.toml`, `tests/lab-vm.nix` with `services.evidence-store.enable = false;`; `git add -A`; `nix build .#checks.x86_64-linux.lab-vm -L --no-link` → red (Y1 below).
  3. On this same tree, prove Y3–Y6 with transient fixtures. **Corrected at OL1's gate (2026-09-08): the fixtures MUST be `git add`ed.** `checks.lint` copies `${self}`, and a flake's `self` carries only tracked files, so an untracked fixture is invisible to the check and every arm exits 0 — the stated procedure cannot produce a red. The recipe is: write the fixture, `git add` it, run the check (red), then `git rm --cached` and delete it. None of them appear in the commit, so `touches` is unaffected; the red is real because the check actually saw the file.

| # | assertion | discriminating fixture | mutant / red |
|---|---|---|---|
| Y1 | `nix build .#checks.x86_64-linux.lab-vm -L --no-link` proves the pinned module boots and installs `evidence` | the bootstrap state, `enable = false` (Step 1.2) | Step 1's own red: `evidence: command not found` in the VM's `record-check` call — fixed by Step 2's flip to `enable = true`, no separate mutant |
| Y2 | `testScript` asserts the written row carries `"name":"lab"` and `"class":"unit"` | `checks.jsonl` after one `record-check`, once `enable = true` | change the call to `--class vm`, leave the assertion → fails on real bytes → red; revert before Step 3 |
| Y3 | treefmt/nixfmt arm | a transient mis-indented copy of `tests/lab-vm.nix` | introduce → `treefmt --ci` fails → red; `treefmt` fixes → green; remove the copy |
| Y4 | pinned by the exact sha, never a bare `ref` or another 40-hex value | the input URL string | delete `&rev=…` → red; swap in another 40-hex value → still fails (exact-sha, not mere presence) → red |
| Y5 | statix and deadnix arms | transient `_fixture.nix` files: `{ ... }: 1` (empty-header refusal); `let unused = 1; in 2` | introduce each → `statix check .` / `deadnix --fail .` fails → red; remove → green |
| Y6 | ruff arm, both invocations | a transient `_fixture.py`: an unused import, badly spaced | introduce → `ruff check .` fails (F401) and `ruff format --check .` fails → red; remove → green |

- [ ] **Step 2: The edit** — flip `services.evidence-store.enable = true;` in `tests/lab-vm.nix`; Y2's mutant proven and reverted here.
- [ ] **Step 3: Run green** — `nix build .#checks.x86_64-linux.lint -L --no-link`; `… lab-vm`; `nix flake check -L` → `all checks passed!`.
- [ ] **Step 4: Commit** — one commit, subject below, `nix develop -c git commit -F <msgfile>` (`devShells.default` provides `git` — D5); trailers per Global Constraints, run `ol1`.

**Tests:** rows Y1–Y6.

**Relaunch:** `FACTORY_SEAT=codex … factory-wave ol1b /home/dalhaka/flakes/openai-lab "OL1"`; the diff stays in `~/factory/ws/ol1/OL1`.

**touches:** flake.nix, flake.lock, treefmt.toml, tests/lab-vm.nix
**acceptance:** lint, lab-vm
**commit subject:** `lab: the flake — pinned to nixos-agent-env by exact revision, checks.lint and checks.lab-vm proving the pinned evidence-store module boots, devShells.default (test: lint, lab-vm)`

### OL2 (code, S) — the extractor: `tools/codex_limits.py` turns Codex `rate_limits` rollout lines into JSONL, refusing anything that is not JSONL

**dependsOn:** OL1
**repo:** openai-lab

**Files:**
- Create: `tools/codex_limits.py`, `tests/test_codex_limits.py`
- Modify: `flake.nix` (a new `checks.unit` running pytest)

**Interfaces:**

`tools/codex_limits.py <path> [<path> ...]` (stdlib only — `json`, `sys`, `pathlib`; never a default path under `~/.codex`). Every internal failure named:

- **Zero argv paths:** `usage: codex_limits.py <path> [<path> ...]` to stderr, exit 2, before opening anything (Z5).
- **A nonexistent path:** `codex_limits: <path>: No such file or directory` to stderr, exit 2 immediately; earlier flushed rows stay printed (Z7, Z9).
- **Per path, in argv order:** buffer its `rate_limits` rows. Session, once per file: (1) the first `session_meta`'s `payload.id`; (2) else the `<uuid>` from `rollout-<ts>-<uuid>.jsonl`; (3) else the filename's own stem (`pathlib.Path(path).stem`) — `mixed.jsonl` → `"mixed"` — never the literal `unknown` (Z8).
- **Not valid JSON, or zero valid lines:** "not JSONL" — `codex_limits: <path> is not JSONL` to stderr, exit 2, nothing flushed for this file (Z2).
- **A `"type" == "rate_limits"` line** (the only kind kept, others skipped): `payload` must carry all four of `limit_id`, `used_percent`, `window_minutes`, `resets_at`; missing one — `codex_limits: <path> is missing "<key>" on a rate_limits record`, exit 2, nothing flushed, no further path processed (Z6).
- **Emitted row:** six keys, in order — `ts`, `session`, then `limit_id`/`used_percent`/`window_minutes`/`resets_at` verbatim from `payload` — nothing else reaches stdout (Z4).
- **Ordering (flush-then-continue, not all-or-nothing):** a clean path's rows flush before the next opens; a later failure does not un-print earlier ones; all clean → exit 0, rows grouped by path in argv order (Z9).

`checks.unit = pkgs.runCommand "openai-lab-unit" { nativeBuildInputs = [ python3 python3Packages.pytest ]; } ''cp -r ${self} src && chmod -R u+w src && cd src && pytest tests/test_codex_limits.py -q && touch "$out"'';` — no `|| true`; `set -e` fails the build on a failing `pytest` (Z10).

**Facts:** Assumption 7 (the rollout kinds, the spend gap, the board naming this task); `factory-codex-usage.py`'s idiom (`except (JSONDecodeError, ValueError, RecursionError): continue`) is a DIFFERENT contract (skip-and-continue vs. exit 2) — named so a task session never copies it by mistake. Shape stays UNMEASURED beyond the spike's named fields (D1); Operator item 3 supplies the first real path.

- [ ] **Step 1: Read the operator's named rollout path (Operator item 3), then write the failing tests and run them red.**

| # | assertion | discriminating fixture | mutant / red |
|---|---|---|---|
| Z1 | mixing four other kinds with two `rate_limits` lines (different `limit_id`s) yields exactly two JSONL lines, six keys each | the mixed-kind, two-`rate_limits` fixture | drop the type filter → every line echoed → red; keep the filter but omit one key → red |
| Z2 | one good line then a truncated line → exit 2, one stderr line, NOTHING on stdout | that fixture | `continue` per-line instead of buffering-per-file → the good line reaches stdout, exit 0 → red |
| Z3 | two argv paths process independently: file A's `session` never carries into file B's rows | two files, differing `session_meta` ids | read `session` once from `argv[1]` only, reuse for every path → red |
| Z4 | no key beyond the six ever reaches stdout | a `rate_limits` record with an extra `"raw": {...}` key | build via `**record["payload"]` instead of the six named keys → `"raw"` leaks → red |
| Z5 | zero argv paths → the usage line on stderr, exit 2, nothing on stdout | no arguments | drop the argv-length check → an `IndexError` traceback (not the documented message) → red |
| Z6 | a `rate_limits` payload missing `window_minutes` → the one-line stderr naming file and key, exit 2, nothing on stdout | that fixture, key deleted | `payload.get("window_minutes")` (defaults `None`) → row emits `null`, exit 0 → red |
| Z7 | a path that does not exist → the one-line stderr, exit 2 | `tests/fixtures/does-not-exist.jsonl` | an uncaught `FileNotFoundError` traceback instead of the documented line → red |
| Z8 | no `session_meta`, named `mixed.jsonl` (not `rollout-<ts>-<uuid>`) → every row's `session` is `"mixed"` | the mixed-kind fixture, renamed | fall back to the literal `"unknown"` instead of the stem → red |
| Z9 | two-path ordering: (a) both clean → exit 0, A's rows before B's; (b) A clean, B not JSONL → A's row ALREADY on stdout before B's exit-2 stderr line | (a) two clean files; (b) one clean, one bad | (a) reverse/interleave argv → red; (b) buffer globally, flush only at the end → A's row lost → red |
| Z10 | `checks.unit` itself fails non-zero, pytest's failure in the log, when a fixture assertion is broken | any Z-row's expected value changed | add `\|\| true` after `pytest` in `checks.unit` → the same break leaves exit 0 → red (a survivor a bare `pytest -q` can't show); revert before Step 3 |

- [ ] **Step 2: The edits** — `tools/codex_limits.py`, `tests/test_codex_limits.py`, `flake.nix` (`checks.unit`).
- [ ] **Step 3: Run green** — `nix build .#checks.x86_64-linux.unit -L --no-link`; `… lint` (ruff now covers the new file); `nix flake check -L` → `all checks passed!`.
- [ ] **Step 4: Commit** — one commit, subject below, `nix develop -c git commit -F <msgfile>`; trailers per Global Constraints, run `ol2`.

**Tests:** rows Z1–Z10.

**Relaunch:** `FACTORY_SEAT=codex … factory-wave ol2b /home/dalhaka/flakes/openai-lab "OL2"`; the diff stays in `~/factory/ws/ol2/OL2`.

**touches:** tools/codex_limits.py, tests/test_codex_limits.py, flake.nix
**acceptance:** unit, lint
**commit subject:** `lab: tools/codex_limits.py turns Codex rate_limits rollout lines into JSONL and refuses anything that is not JSONL, checks.unit runs its tests (test: unit, lint)`

### OL2b (code, M) — OL2 fix round: the extractor re-spec'd onto the measured nested shape (`event_msg`/`token_count`/`rate_limits`), one row per `primary`/`secondary` window with a window discriminator, a clean-but-empty run made distinguishable from success, the session_meta and directory MINORs closed, hand-built fixtures in the real key set; the body pastes red and green

**dependsOn:** OL1
**repo:** openai-lab

Gate `docs/reviews/2026-09-08-opus-review-ol2-OL2.md` — REJECTED on two MAJORs (`plan_defect: wrong-fact`, secondary `underspecified`), both the plan's fault, not the seat's: OL2's Interfaces pinned a record shape — top-level `"type" == "rate_limits"`, a flat four-field payload — that does not exist in any real Codex rollout. Measured at the gate across `~/.codex/sessions/**/rollout-*.jsonl`, 242 files: **0** top-level `rate_limits` records, **2,569** nested ones, every single one an `event_msg` record whose `payload.type == "token_count"` carries a `payload.rate_limits` object with exactly nine keys — `credits`, `individual_limit`, `limit_id`, `limit_name`, `plan_type`, `primary`, `rate_limit_reached_type`, `secondary`, `spend_control_reached` — and whose `used_percent`/`window_minutes`/`resets_at` live one level deeper still, inside `primary` and (when non-null) `secondary`. `limit_id` is a *plan* id (e.g. `"codex"`), not a window name — the old contract had no window discriminator and cannot express one record without inventing one. Against the operator's named rollout the delivered tool produced `EXIT=0`, zero stdout lines, empty stderr: a silent, contract-correct "success" indistinguishable from an idle session (MAJOR-1). Because the shape differs and the fixtures were never corrected, the gap claim `codex-rate-limits-shape-unmeasured` did not close (MAJOR-2) — its `closes_by` text lives in the plan's Dispatch section, which a seat's brief never includes, so OL2's seat had no way to see it. The seat's own conduct was exemplary throughout: 16/16 mutants dead, red-before-green reproduced, `unit`/`lint`/`nix flake check` green on `--rebuild`, touches exact, subject byte-identical, and it measured the mismatch unprompted and wrote it into its own module docstring rather than let green synthetic tests hide it. Nothing here is a correction of the seat's work; it is a re-spec of the contract the seat was correctly held to.

**This is a re-spec, not a patch** (the review's own recommendation): the CLI shape, the per-file atomicity, the flush-then-continue ordering and the whole test scaffold (subprocess-driven, `tempfile.TemporaryDirectory` fixtures, Z-row mutant discipline) carry forward unchanged in structure; the record-matching predicate, the required-key set, and the row shape are rewritten from measurement. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/ol2/OL2 task/OL2 && git cherry-pick -n FETCH_HEAD` carries OL2's commit `9db7f5b` as staged changes (`openai-lab` has no `docs/OPERATIONS.md`/`docs/MAP.md`, so neither conflict arm applies here). OL2's Interfaces items 1 ("stdlib only"), 2 (zero-argv usage), 3 (nonexistent path), 5 (not-JSONL / zero valid lines) and the `checks.unit` derivation (item 10) stand exactly as written and need no new test. Everything else changes.

**Files:**
- Modify: `tools/codex_limits.py`, `tests/test_codex_limits.py`

**Facts:** the closing condition for `docs/ledger/claims.toml`'s `codex-rate-limits-shape-unmeasured` gap claim, restated here because a seat's brief never includes the plan's Dispatch section where `closes_by` actually lives — **OL2b closes it by landing an extractor built on the measured key set above (the nine `rate_limits` keys; `used_percent`/`window_minutes`/`resets_at` nested under `primary` and `secondary`) that emits rows for the operator's named rollout, with the row count asserted by `checks.unit`.** §Global Constraints forbids fixturing from the real rollout file — every fixture here is hand-built JSONL matching the measured shape by *structure*, never copied from a real file's bytes. Two worked examples, both inventable outright, for the fixture builder to match (a made-up `resets_at`/`balance`/timestamp in each — no real session id, no real path):

```json
{"timestamp": "2026-01-01T00:00:00Z", "type": "event_msg", "payload": {"type": "token_count", "rate_limits": {"credits": {"has_credits": false, "unlimited": false, "balance": "0"}, "individual_limit": null, "limit_id": "codex", "limit_name": null, "plan_type": "prolite", "primary": {"used_percent": 1.0, "window_minutes": 10080, "resets_at": 1789460350}, "rate_limit_reached_type": null, "secondary": null, "spend_control_reached": null}}}
```
(a null `secondary` — one row, window `"primary"`)

```json
{"timestamp": "2026-01-01T00:05:00Z", "type": "event_msg", "payload": {"type": "token_count", "rate_limits": {"credits": {"has_credits": true, "unlimited": false, "balance": "500"}, "individual_limit": null, "limit_id": "codex", "limit_name": null, "plan_type": "prolite", "primary": {"used_percent": 42.5, "window_minutes": 10080, "resets_at": 1789460400}, "rate_limit_reached_type": null, "secondary": {"used_percent": 8.0, "window_minutes": 1440, "resets_at": 1767243600}, "spend_control_reached": null}}}
```
(a non-null `secondary` — two rows, windows `"primary"` and `"secondary"`)

**Interfaces:**

1. **The kept record kind (replaces item 6).** A record is kept only when `record.get("type") == "event_msg"` AND its `payload` is a dict with `payload.get("type") == "token_count"` AND `payload.get("rate_limits")` is a dict; everything else — `session_meta`, `turn_context`, `response_item`, `world_state`, any other `event_msg` payload type — is skipped, exactly as before.
2. **The rate_limits object's required keys (replaces item 7).** The kept object must carry all nine measured keys (Facts, above); missing one — `codex_limits: <path> is missing "<key>" on a rate_limits record`, exit 2, nothing flushed for this file, no further path processed.
3. **Each window, validated separately.** For each of `primary`, `secondary`: if its value is `None`, it contributes no row. If it is a dict, it must carry `used_percent`, `window_minutes`, `resets_at`; missing one — `codex_limits: <path> is missing "<key>" on a rate_limits <window> window` (`<window>` literally `primary` or `secondary`), exit 2, nothing flushed, no further path processed. Neither `None` nor a dict (a malformed record) is the same failure, same message. A record whose `primary` and `secondary` are both `None` is valid and simply contributes zero rows — not an error.
4. **Emitted row (replaces item 8).** Seven keys, in order: `ts`, `session`, `window`, `limit_id`, `used_percent`, `window_minutes`, `resets_at`. `window` is `"primary"` or `"secondary"`; `limit_id` is copied verbatim from the rate_limits object (a plan id, e.g. `"codex"` — no longer a window discriminator); `used_percent`/`window_minutes`/`resets_at` come from the window dict just validated. A `primary` and a non-null `secondary` on the same record each produce their own row, `primary` first. Nothing beyond these seven keys reaches stdout, from either the outer object or the window dict.
5. **Session resolution (replaces item 4, closes MINOR-1).** Per path: the first `session_meta` record whose `payload` is a dict AND contains `"id"` sets the session and stops the search — a `session_meta` with no `id` (or a non-dict `payload`) is skipped, not consumed, so a later `session_meta` that does carry an `id` is still reachable. Else the `<uuid>` of a `rollout-<ts>-<uuid>.jsonl` name. Else the stem. Never the literal `unknown`.
6. **A directory argument (closes MINOR-2).** `codex_limits: <path>: Is a directory`, stderr, exit 2, before opening any later path — the same failure class and shape as the existing "nonexistent path" arm (item 3), never an uncaught `IsADirectoryError` traceback. A `PermissionError` is out of scope for this round (untouched: still an uncaught traceback, unnamed by either gate).
7. **Silent-empty made observable (closes MAJOR-1).** After every path in argv has been processed with no fatal error, if the total number of rows emitted across *all* paths is zero, print `codex_limits: 0 rate_limits rows found across <n> path(s)` to stderr (`<n>` = the argv count) and exit **3** — never 0. If at least one row was emitted anywhere across the run, exit 0 as before (item 9's ordering and flush-then-continue are otherwise unchanged). This is the only new exit code; it never fires when any path errors (those keep their own exit-2 arms).

**Tests (assertion → mutant; fixture → discriminating row):**

| # | assertion | discriminating fixture | mutant / red |
|---|---|---|---|
| Z1 | mixing `session_meta`, `turn_context`, `event_msg`/`task_started`, `response_item` with one `event_msg`/`token_count` record carrying a null `secondary` and one carrying a non-null `secondary` yields exactly 3 rows (1 + 2), seven keys each, `window` correct on each | the mixed-kind fixture with the two worked examples above | drop the `payload.type == "token_count"` check → the `task_started` event_msg is read as a rate_limits carrier too → wrong count, red; keep the filter but emit `window` from `limit_id` instead of the loop variable → both rows show `window: "codex"`, red |
| Z2 | one good record then a truncated line → exit 2, one stderr line, nothing on stdout | a file with one valid record then `{"type":` | per-line `except (ValueError, RecursionError): continue` instead of raising → the good line reaches stdout, exit 0, red |
| Z3 | two argv paths process independently: file A's resolved session never carries into file B's rows | two files, each with its own valid `session_meta` | cache the first file's session module-wide and reuse it → red |
| Z4 | an extra unknown key inside the `rate_limits` object (e.g. `"raw": {...}`) is tolerated and never reaches the row; an extra key inside a window dict (e.g. `primary.extra`) is likewise dropped | the null-secondary worked example plus `"raw": {"synthetic": true}` on the outer object and `"extra": 1` inside `primary` | build the row via `**window, **{"limit_id": ...}` instead of the seven named keys → `"raw"` or `"extra"` leaks, red |
| Z5 | zero argv paths → usage line on stderr, exit 2, nothing on stdout | no arguments | drop the argv-length check → an `IndexError` traceback, red |
| Z6 | a `rate_limits` object missing `plan_type` → the one-line stderr naming the file and key, exit 2, nothing flushed, no further path processed | that object, key deleted, a second clean path after it | skip `plan_type` in the required-key loop → the second path is opened, red |
| Z7 | `primary` present but missing `resets_at` → `codex_limits: <path> is missing "resets_at" on a rate_limits primary window`, exit 2, nothing flushed, no further path processed | the null-secondary worked example, `resets_at` deleted from `primary` | validate the window dict with `.get(key)` defaulting to `None` instead of requiring the key → row emits `resets_at: null`, exit 0, red |
| Z8 | a record with `primary: null, secondary: null` contributes zero rows and is not an error; a sibling clean record elsewhere in the same file still emits its rows | one such record plus the null-secondary worked example in the same file | treat `primary is None` as a missing-key error → exit 2, red |
| Z9 | a nonexistent path → the documented stderr line, exit 2 | `tests/fixtures/does-not-exist.jsonl`-shaped tmp path | delete the `except FileNotFoundError` arm → uncaught traceback, red |
| Z10 | a directory path → `codex_limits: <path>: Is a directory`, exit 2, before any later path opens | `tmp_path.mkdir()`, plus a second clean path after it | catch only `FileNotFoundError` (today's code) → uncaught `IsADirectoryError` traceback, red |
| Z11 | no `session_meta` at all, filename `mixed.jsonl` → every row's session is `"mixed"`; a `rollout-<ts>-<uuid>.jsonl` name with no `session_meta` → session is the uuid | both filename shapes, no `session_meta` in either | fall back to the literal `"unknown"` instead of the stem/uuid, red |
| Z12 | MINOR-1: a file whose first `session_meta` has no `id` and whose second `session_meta` does → session resolves to the SECOND meta's id, not the stem | two `session_meta` records, first `{"type": "session_meta", "payload": {}}`, second carrying `"id"` | keep `found_session = True` on the first `session_meta` regardless of whether it yielded an id (today's code) → session falls back to the stem, red |
| Z13 | two-path ordering: (a) both clean, rows grouped A-then-B; (b) A clean, B not JSONL → A's rows are already on stdout before B's exit-2 stderr line, nothing further attempted | (a) two clean worked-example files; (b) one clean, one truncated | (a) reverse argv order before the print loop → red; (b) buffer every path's rows globally and flush once at the end → A's rows lost from the expected prefix, red |
| Z14 | MAJOR-1: every path processes cleanly but the total row count across all of them is zero → `codex_limits: 0 rate_limits rows found across <n> path(s)` on stderr, exit **3**, stdout empty; the same run with one matching record anywhere among the paths → exit 0 as before | (a) N clean files with no `event_msg`/`token_count` records at all; (b) the same plus one worked example inserted in the last file | drop the total-row-count check (today's code, extended to the new predicate) → exit 0 with empty stdout, indistinguishable from success, red |
| Z15 | `checks.unit` itself fails non-zero when a fixture assertion breaks (unchanged from OL2's Z10, re-verified against the new file) | any Z-row's expected value changed | add `\|\| true` after `pytest` in `checks.unit` → the same break leaves exit 0, red |

- [ ] **Step 1: The carried commit, then the tests.** Cherry-pick `9db7f5b` as staged changes. Write Z1–Z15 (Z2, Z5, Z9, Z15 keep OL2's originals nearly verbatim; every other test is new or materially rewritten for the nested shape) and run them red against the carried (flat-shape) implementation — `nix develop -c python3 -m pytest tests/test_codex_limits.py -q`, paste the failures.
- [ ] **Step 2: The edits** — rewrite `tools/codex_limits.py`'s record predicate, required-key validation, per-window validation, row assembly and the session_meta and directory handling (Interfaces 1–7); no change to `flake.nix`.
- [ ] **Step 3: Run green** — `nix build .#checks.x86_64-linux.unit -L --no-link`; `… lint`; `nix flake check -L` → `all checks passed!`.
- [ ] **Step 4: Mutants** — every row of the Tests table, one at a time, killing line pasted, file restored before the next.
- [ ] **Step 5: Commit** — one commit, subject below, `nix develop -c git commit -F <msgfile>`; trailers per Global Constraints; body pastes the Step-1 red, the Step-3 green, the mutant table, and states in one sentence that this landing closes `codex-rate-limits-shape-unmeasured`.

**touches:** tools/codex_limits.py, tests/test_codex_limits.py
**acceptance:** unit, lint
**commit subject:** `lab: tools/codex_limits.py reads the real nested event_msg/token_count rate_limits shape, emits one row per primary/secondary window with a window discriminator, and exits 3 rather than 0 when a clean run finds no rate_limits rows — closes codex-rate-limits-shape-unmeasured (test: unit, lint)`

### OL3 (docs, S) — the runbook: bumping the pin, dispatching a task under `FACTORY_SEAT=codex`, where the gate record lives

**dependsOn:** OL1
**repo:** openai-lab

**Files:**
- Create: `docs/runbook.md`, `tests/runbook.bats`
- Modify: `flake.nix` (`checks.unit` gains the heading and bats gates)

**Interfaces:**

`docs/runbook.md` carries exactly three `## ` headings, byte-exact (the prose beneath is free to reword — heading text and fenced commands are the contract):

- `## Bumping the pin` — one ` ```bash ` fence: `$ nix flake lock --update-input nixos-agent-env` then `$ nix flake check -L`.
- `## Dispatching a task` — states `factory-dispatch` cannot be used here (Assumption 9), then one fence: `$ FACTORY_SEAT=codex FACTORY_PLAN=<plan> setsid -f bash -c 'exec tools/factory/seat/factory-wave <run> /home/dalhaka/flakes/openai-lab "<KEY>" >> ~/factory/runs/<run>.wave.log 2>&1' </dev/null`.
- `## Where the gate record lives` — every review is committed in `~/nixos-agent-env`'s `docs/reviews/`, never the lab; one fence: `$ git -C ~/nixos-agent-env log -1 --format=%s -- docs/reviews`.

`flake.nix`'s `checks.unit` gains, after pytest: `[ "$(grep -c '^## ' docs/runbook.md)" = 3 ]`; one `grep -Fxq` per heading above; `bats tests/runbook.bats` (nativeBuildInputs gains `pkgs.bats`).

`tests/runbook.bats` extracts every `$ `-prefixed line inside a ` ```bash ` fence (`awk '/^```bash$/{f=1;next} /^```$/{f=0} f && /^\$ /{sub(/^\$ /,"");print}' docs/runbook.md`) and asserts each starts with a documented verb above — extracted commands, never surrounding prose.

**Facts:** the codex-arm plan's Dispatch section (launch-line shape; step 3, the review committed in `~/nixos-agent-env`); decision point 4; `factory-dispatch:104-108`; `~/flakes/codex`'s review lives at `docs/reviews/2026-09-07-opus-review-cx1b-CX1b.md`, not in `~/flakes/codex`. Z10 (OL2) proves `set -e` propagates, not repeated here.

- [ ] **Step 1: Write the failing check and run it red.**

| # | assertion | discriminating fixture | mutant / red |
|---|---|---|---|
| R1 | exactly 3 `## ` headings | with/without a stray fourth, or one deleted | add a fourth `## ` line → count 4 → red; delete one → count 2 → red |
| R2 | the three exact headings, each its own `grep -Fxq` | each heading present, reworded, or deleted in turn | reword `## Bumping the pin` → red; delete `## Dispatching a task` or `## Where the gate record lives` → red |
| R3 | every fenced `$ ` command matches a documented verb | as in Interfaces | drop `-L` from `nix flake check -L` without updating the verb list → red; an undocumented new command → red |

- [ ] **Step 2: The edits** — `docs/runbook.md`, `tests/runbook.bats`, `flake.nix` (the five new `checks.unit` lines).
- [ ] **Step 3: Run green** — `nix build .#checks.x86_64-linux.unit -L --no-link` (pytest plus R1–R3); `… lint`; `nix flake check -L` → `all checks passed!`.
- [ ] **Step 4: Commit** — one commit, subject below, `nix develop -c git commit -F <msgfile>`; trailers per Global Constraints, run `ol2`.

**Tests:** rows R1–R3.

**Relaunch:** `FACTORY_SEAT=codex … factory-wave ol2b /home/dalhaka/flakes/openai-lab "OL3"`; the diff stays in `~/factory/ws/ol2/OL3`.

**touches:** docs/runbook.md, tests/runbook.bats, flake.nix
**acceptance:** unit, lint
**commit subject:** `lab: the runbook — bumping the pin, dispatching a task under FACTORY_SEAT=codex, where the gate record lives, checks.unit gates it by heading and verb (test: unit, lint)`
