# Plan 2026-09-11 — Generation (`GN`): the feed, the job queue, the rules mutator, the brokered probe, the worlds on core, media absorbed

**Spec:** `docs/context/generation.md` (§1–§6; its eight §5 questions are answered in `## Operator questions` and `## Assumptions`). **Decisions:** `docs/decisions/2026-09-09-redesign-answers.md` rows 14c, 15a, 16b, 17c (the Generation row), 18b (engagement counts), 20b (the LAN face later), 35b, 41a, 43b, 48a (absorption), 63a (prefixes), 70b (one composed drill); `docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md` ("The media flake stays brokered (it is closer to an agent than to an app)"). **Charter:** `docs/concepts/2026-09-09a-redesign-charter.md`, the Generation row and "Increment 3 — Helm, Evidence, Generation". **Program plan:** the binding subset of G1–G12, quoted in `## Global Constraints`.
**Author:** Fable 5.1, workflow `draft-byref`, 2026-09-14 (the workflow's `date`), drafted on the F4 snapshot at HEAD `c9c5bd7` (`git log -1 --format=%H` → `c9c5bd7c04940631a1fb6d2878eab0eadb537cc4`) — a checkout whose history is one `snapshot` commit and which holds no `~/flakes/media` (Assumptions 1–3). Every media-tree fact below is a quotation from the record in this tree with its source beside it, and the seat re-measures it before acting (Global Constraint GN-A). The previous drafts of this plan (33 → 34 → 38 of 42, `docs/reviews/plan-judgements/2026-09-1{2,4}-batch-generation*.md`) are not in this tree; their 26 + 15 errata are folded in and named where they bite.
**File name:** `docs/superpowers/plans/2026-09-11-generation.md` — the second `plans` entry of the Generation row (`grep -n -A 9 '^name = "Generation"' docs/ledger/subsystems.toml` → `"docs/superpowers/plans/2026-09-11-generation.md"`), so `GN` keys pass the G7 guard here and nowhere else; under any other basename every section below is refused (`prefix GN is reserved for Generation, whose plans are …`). The `--draft` check in `## Waves` was run under this basename.
**Status:** DRAFT — nothing dispatched; no typed heading sits under `docs/superpowers/plans/` until the Ship phase writes this file. After landing: `nix develop -c python3 pkgs/evidence/tasks.py --root . check` (the lines `## Waves` predicts clear as named there), then `… waves --repo nixos-agent-env --next`.

## Operator questions

Three, each with a recommendation and the default that applies if unanswered; every other open decision is applied as a recommendation in Assumptions 29–35 with its veto surface.

1. **The upstream probe's egress** (spec §5 Q3; brief §3 invariant 3; the standing decision: "The media flake stays brokered"). The probe's design text claims direct HTTPS to GitHub and PyPI "as an operator tool"; the decision it cites grants no such carve-out (spec §5 Q3 quotes both). **(a)** broker it: GN7 makes `probe.py` open every URL through `HTTPS_PROXY` with `SSL_CERT_FILE` and refuse, before any socket, when either is unset or unreadable, and moves the probe from a user timer to a system service and timer that join the `egress-media` namespace as the operator (a user unit outside the namespace cannot reach the proxy: the broker drops host-side traffic to it, Assumption 10); GN10 declares the `media` broker instance on `core` with an `allow` list of exactly the six hosts the probe names and no `inject`. **(b)** record an exception: a decision file (Knowledge's) naming the probe as operator tooling; GN7 is withdrawn and GN10's instance carries no probe hosts. **Recommend (a)** — the decision's own words, and invariant 3 has no "deterministic tooling" arm; **default (a)**. On (b): a `withdrawn` row for GN7 in `docs/ledger/task-status.toml`; GN10 drops the `allow` list and the probe `Environment`; Operator steps 15 and 16 go.

2. **How far "media absorbed" goes in this batch** (spec §5 Q6; charter: "The `~/flakes` sibling repos as working repos once absorbed (answers 35, 44, 48)"; 35b "one sibling per task, each with its own build gate and switch"; 48a "a subtree-style merge per sibling; every cited hash stays reachable"). **(a)** absorb after the media-side work lands: the orchestrator's landing act merges `~/flakes/media` as the subtree `media/` (the Platform plan's Q6(b) shape: branch `absorb/media`, tag `absorbed/media-<rev>`, `git subtree add --prefix=media --no-squash`, one merge commit, a board line); GN11 records it; GN12 moves the flake's outputs into this flake on `nixpkgs-host` (43b) and deletes the inner flake. **(b)** keep the split this increment: GN10's `media.url` input stays, GN12 is withdrawn, GN11 keeps the manifest and plan-status tidy-up only. **Recommend (a)** — the charter puts "media absorbed" in this increment and PL6 has the row shape; **default (a)**. On (b): a `withdrawn` row for GN12; GN11 drops its `repos.toml` hunk and says so in its commit body; switch #N+1 and Operator steps 19–22 go.

3. **Caddy and the LAN face** (spec §3 rows 14c "Caddy fronts the worlds as designed" and 16b "host-level Caddy wired into `core`"; decision 20b "LAN now (Caddy, internal CA, a password or WebAuthn per site); a declared private overlay as its own later gated phase"; the charter's Increment 4 reads "LAN access with per-site auth … (`IS`)"; the module renders Caddy only under `lan.enable`, which needs the password files under `/var/lib/comfy-secrets/` and the host names the operator owns). **(a)** wire the worlds with `lan.enable = false` now — loopback only, no 443, no password file, the feed reached from the desktop browser at `http://127.0.0.1:<feedPort>` and by Helm's link (14c's "the feed component Helm reaches"); the LAN face is Isolation's increment-4 task, which flips one option and supplies the files. **(b)** `lan.enable = true` in GN10: the operator supplies `/var/lib/comfy-secrets/comfy-<w>.users` and the two host names before switch #N (A3 items) and `core-media-wiring` asserts 443 is the only opened port. **Recommend (a)** — 20b and the charter's increment order; "Caddy fronts the worlds as designed" is the module as designed, enabled when its inputs exist; **default (a)**. On (b): GN10 gains three A3 items and two assertions; the drill gains a `curl -k https://<host>/healthz` step.

## Spec-to-task map

| Spec item (`docs/context/generation.md`) | Where it lands |
|---|---|
| §1 the manifest row: `owns = []`, this file its second `plans` entry; "whatever it creates in this repo must be added to some row's `owns` in the same landing"; no green `subsystems-manifest` baseline | **GN11** (`media/*` under the GN row; the plan file itself is EV10's `docs/superpowers/plans/*` glob — Cross-plan); Assumptions 7, 12 |
| §1 `~/flakes/media` is Generation's code, no `ledger = true`; "the lab repo" is `worlds/<w>/lab/` at runtime | GN1–GN9 carry `**repo:** media`; GN5 reads `<root>/worlds/<w>/lab/manifest.toml` |
| §2 `feed_placeholder.py`: "no like, regenerate or edit-prompt loop exists" | **GN1** (the index), **GN2** (the queue), **GN3** (the feed replaces the placeholder), **GN4** (the three verbs) |
| §2 `probe.py` "runs no model, spends no key" — and its direct HTTPS | **GN7** (question 1) |
| §2 "Host integration does not exist" | **GN10** (question 3) |
| §3 14c Caddy; the swipe view is Helm's | GN10 (the worlds; Caddy per question 3); Helm's link or embed: `out:` Helm (`HM`) |
| §3 15a sub-projects 2 and 3 as specified, W6's fix round first (landed, spec §3) | GN1–GN4 (sub-project 2), GN5–GN6 (sub-project 3) |
| §3 16b on-demand user units on core, no specialisation | **GN10** |
| §3 17c rules now; the local model its own phase | **GN5**, **GN6**; the model: `out:` Not in this plan |
| §3 invariants 2 and 3 through "the media flake stays brokered" | GN7 (the probe), GN10 (the `media` instance; nothing on core reaches out except through it), GN8 (loopback only) |
| §3 G7 prefix rule, G9 area rule | keys only in this file; `**areas:**` on GN10, GN11, GN12 (Assumption 8) |
| §3 increment placement: sub-projects 2/3, the units and Caddy on core, the rules mutator, media absorbed | GN1–GN6; GN10; GN5/GN6; GN11–GN12 (question 2) |
| §4 defect classes seen: an `&&` chain in bats (W2), vacuous assertions (W3), an undeclared runtime binary (W2b), a bare nix32 hash (W5), a false-MAJOR trailer class (FIX7, closed) | Global Constraints GN-B, GN-C, GN-D; every section's mutants and negative control |
| §4 W6b refused at integrate for board prose | Global Constraint GN-E |
| §4 the open claim `aimdo-native-load-unmeasured` (`review_by = 2026-09-19`, closed by "the media acceptance drill on core") | Operator steps 8 and 23 — the journal line and the prepared flip (A8) |
| §5 Q1 the plan file's name is a precondition; the superseded `2026-09-02-media-flake.md` entry stands | this file's name (Assumption 29); **GN11** removes the superseded entry |
| §5 Q2 WH1 and WH2 are typed but invisible | superseded: WH1 → **GN10**, WH2 → `out:` Helm (Assumption 30) |
| §5 Q3 the probe's carve-out | question 1 → **GN7**, **GN10** |
| §5 Q4 what "rules" means for the mutator | **GN5** (the grammar in the lab's `manifest.toml`), **GN6** (the unit); Assumption 31 |
| §5 Q5 where the feed's state lives | **GN1** (`worlds/<w>/feed.sqlite`, rebuildable); Assumption 32 |
| §5 Q6 how far absorption goes | question 2 → **GN11**, **GN12** |
| §5 Q7 `nix flake check` in media: UNVERIFIABLE | Assumption 5; every task builds its acceptance checks by name |
| §5 Q8 the probe timer's live state: UNVERIFIABLE | Operator step 4 measures it (a system timer after GN7, started by the switch) |
| §6 out of scope: Helm's tile, the `proposals` stream and its schema, the parser and prefix guard, `factory-review`'s trailer class, local inference, netns confinement, the generation lab | `## Not in this plan` |
| decision 18b engagement counts (charter §8 item 2); the board's GN8 redesign (Assumption 4) | **GN8** — the feed POSTs counts to Helm's loopback endpoint; Assumption 33 |

## Decisions relied on

14c → GN10 (the worlds on core; Caddy per question 3). 15a → GN1–GN6. 16b → GN10 (user units, no specialisation). 17c → GN5/GN6 (rules); the model phase is out. 18b → GN8 (counts only, EV14's five fields). 20b → question 3(a). 35b, 41a, 43b, 48a → GN11/GN12 (question 2; 41a: the nine `GN` keys are the live keys, already prefixed; media's landed W keys freeze as history). 63a → keys only here. 70b → `## Operator` feeds the increment's composed drill. "The media flake stays brokered" → GN7, GN10. WH1/WH2 superseded → Assumption 30.

## Global Constraints

Quoted verbatim from `docs/superpowers/plans/2026-09-09-program.md` (the `**G1 Build-only.**` … `**G11 Numbers.**` bullets), the subset that binds a seat here: `factory-brief` hands this section, `## Assumptions` and the task's own section to the seat and nothing else, so nothing here is a reference. Not quoted: G3 (the trailers ride in the driver's WORKSPACE RULES block), G7 (enforced by `tasks.py check` before dispatch), G10 (no new language; module headers here are `_:` or named args). Then this plan's own GN-A–GN-H.

- **G1 Build-only.** Never `sudo`, `nixos-rebuild`, `systemctl start|stop|restart|enable|kill`, basket mount or teardown. The operator switches; a task that needs the live system to change says so in its `## Operator` line and stops.
- **G2 Red first.** Every check or test a task adds is shown failing before the change that makes it pass, and the red output is pasted in the commit body. A load-bearing test counts only once it has failed (CLAUDE.md).
- **G4 Subject.** `<area>: summary (test: <check names>)`, the area being the subsystem's prefix in lower case once PR1 lands (`evidence:`, `factory:`, `isolation:`, `knowledge:`, `program:`), the check names being exactly the task's `acceptance` list. Guarded twice: the workspace's `commit-msg` hook that `factory-ws` installs (`tools/factory/seat/factory-ws:131-136`, `factory-commit-msg.sh`) and the gate's convention section, which compares the subject byte for byte with the section's `commit subject` line. — Here the area is `generation:` for every key, in both repos.
- **G5 Touches.** Edit only the files the task's `touches` names; a new file is named there too. An undeclared touch demotes the result (`factory-task:857-861`). `git add` every new file before any `nix build` (flakes see tracked files only). **One standing exemption, added 2026-09-10 after it was flagged twice:** the *derived queue block* of `docs/OPERATIONS.md`, and nothing else in that file, when the pre-commit's G8c forces its regeneration — G6 orders that regeneration, so listing the file in every task's `touches` would be noise and omitting it made the gate read a forced, derived, machine-written hunk as an undeclared touch (HH3's minor, PR1's MAJOR). A gate treats a queue-block-only diff there as declared; any other hunk in that file is an undeclared touch as before, and board prose stays the orchestrator's (the rule that refused W6b at the integrator). **`docs/MAP.md` is exempt on the same ground and for the same reason** (KN1's minor): `lint` asserts it is current (`flake.nix:1081-1086`), so any task that adds or renames a module, package, check or test must run `python3 pkgs/evidence/repomap.py --root . write` and commit the result whether or not its `touches` names the file. Both exemptions cover *derived* files a check or hook forces; neither excuses a hand edit. — The MAP-currency assertion's anchor text is `lint: docs/MAP.md Checks section differs from the flake's checks` (`grep -n 'docs/MAP.md Checks section differs' flake.nix`); the cited line range is stale (the 2026-09-14 erratum 26).
- **G6 Commit route.** `nix develop -c git commit -F <msgfile>` on `task/<KEY>`; one commit per task. **A fix round that starts by cherry-picking its predecessor folds that cherry-pick into its own single commit** (`git cherry-pick -n`, or `git reset --soft` back to the base before committing) — added 2026-09-10 after the instruction proved ambiguous: PR1b's seat folded and PR1c's did not, and `factory-task:757` demoted the second for claiming one commit where the branch carried two. The chain's history lives in the plan and the reviews, not in a stack of replayed commits on one task branch. If the pre-commit refuses only on G8c (a stale board queue block), regenerate with `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board` and include the block in the same commit; never `--no-verify`.
- **G12 Invariants** (brief §3, re-ratified after the audit per decision 55a): every task here is written against the six verbatim. Where they bind here: GN7 and GN10 route the probe's only egress through the `media` broker instance with a six-host `allow` and no credential (2, 3); GN8 sends counts, never content, to a loopback endpoint and drops on any error (3, 6); GN1–GN6 read and write only `<root>/worlds/<w>/` (feed.sqlite, the job rows) and never a credential, a basket or a lane (1, 2, 4); GN10–GN12 are Nix configuration and ledgers reviewable in a diff (5); no task promotes agent-authored code between baskets (6); no task adds imperative setup — the worlds' tree is built by `comfy-worlds-init` as before (4).
- **G8 Privacy.** Nothing leaves the machine. No credential, token or key is copied, moved, printed or redirected by any task in this plan; the feed's page carries no external URL (GN3 Interfaces 5); the engagement body carries counts only (GN8 Interfaces 2).
- **G9 Areas.** From EV2 on, a task whose `touches` fall in two subsystems declares `**areas:**` with both; `tasks.py check` refuses it otherwise. **EV2 landed this on 2026-09-10 (`f31b8bb`); it is enforced in code, not by hand** (`pkgs/evidence/tasks.py:1823-1834`). The refusal fires only while a task's derived state is `ready`, `blocked`, `ran` or `running`, so a landed key is never refused retroactively, and it exempts exactly the twenty-five keys in `docs/ledger/areas-grandfather.toml` — a list frozen at `dbedfe9`, so a key typed later is refused like any other. Note the grandfather ledger is read from the repo's live path rather than the tree under `--root`, so inside a workspace it exempts nothing (`BUG-ledger-read-from-live-path`): declare `**areas:**` rather than relying on the exemption.
- **G11 Numbers.** Every integer a task pastes (row counts, line numbers, test counts) is re-run at commit time, not copied from this plan (concept 2026-09-08g). Guarded by the gate: the review rubric's "correct facts" row re-runs the commit body's commands, and a pasted integer that does not reproduce is a MAJOR (the record's `wrong-fact` class in `docs/ledger/plan-defects.toml`).
- **GN-A Re-measure before acting.** This plan was drafted without the media tree (Assumption 1). Every fact a section quotes about `~/flakes/media` names its source; the task's Step 0 re-runs the command the fact names, in the workspace, and pastes the output into the commit body. A fact that does not reproduce stops the task before any edit — `FACTORY-RESULT status=failed` and `FACTORY-NOTES fact drift: <the fact>` — never a silent adaptation and never a guess.
- **GN-B Tests that can fail.** One `[ … ]` or `run` per line in bats (W2's `&&` chain could not fail); every assertion a section names has the one-line mutant that turns it red, and the seat runs each mutant (revert, run, restore) and pastes the red line; a test that passes both with and without the change is `vacuous` at the gate.
- **GN-C Runtime inputs.** Every binary a script calls is in its wrapper's `runtimeInputs` (W2b's `find` was not); the proof is the packaged wrapper run on a bare `PATH` — `env -i PATH=/nonexistent <wrapper> --help` exits 0 — and the test runs the packaged binary, never only the pytest-copied tree.
- **GN-D Hashes.** Every hash handed to Nix is SRI (`nix hash convert --hash-algo sha256 --to sri <nix32>`); a bare nix32 hash broke eval at W5.
- **GN-E The board is not the seat's.** Never commit a change to `docs/OPERATIONS.md` in either repo (W6b was refused at integrate for board prose; `factory-integrate` refuses `docs/OPERATIONS.md changed outside the queue block`); never merge `main` into the task branch and never regenerate or restore the derived queue block by hand — the integrator merges and the orchestrator regenerates, outside the seat's commit.
- **GN-F One commit, one result line, a scripted body.** The result line is exactly `FACTORY-RESULT status=done|partial|failed` in column one (`factory-task` matches `^FACTORY-RESULT[[:space:]]+status=(done|partial|failed)` and records anything else as `result-misparse`, status `failed`). The commit body is produced by the section's commit script: the commands the section names run, and their output is appended under each command; nothing in the body is typed from memory. The trailer lines are the two the WORKSPACE RULES block prints, appended last.
- **GN-G Loopback.** Every probe of a local port uses `curl --noproxy '*'`; every URL the feed, the queue or the mutator opens is refused with `ValueError` unless its host is `127.0.0.1` or `localhost` (the broker denies everything else; 43 denials from one seat were the record).
- **GN-H Python.** Stdlib only in `pkgs/comfy-worlds` and `pkgs/comfy-upstream-probe` (`sqlite3`, `json`, `zlib`, `struct`, `http.server`, `urllib`, `tomllib`, `ssl`, `html`, `secrets`); pytest in tests; the formatter media's `lint` runs rewraps the blocks below — a reformatting-only difference from the plan text is not a deviation.

## Assumptions

Measured at HEAD `c9c5bd7` on 2026-09-27 (this snapshot's clock) unless a line says otherwise; the command is beside each fact. Items 29–35 are applied recommendations with their veto surface; item 36 lists defects found while drafting.

**The drafting environment**

1. `git log --format='%ci%x09%h%x09%s' | wc -l` → `1` (`snapshot`): no key derives `landed` here (`python3 pkgs/evidence/tasks.py --root . brief` → `nixos-agent-env | 0 | 199 | 16 | … ready 31 | blocked 42`), `conflicts` prints 411 rows dominated by `approved` keys, and `git log --since` history is empty. `ls /home/dalhaka/flakes/ ~/flakes/media` → `No such file or directory` for both; `readlink -f "$(command -v nix)"` → `tools/cloud/nix`, a shim that only execs `nix develop -c CMD`, so no check was built while drafting. `python3 -c "import duckdb; print(duckdb.__version__)"` → `1.5.5` (the store queries below).
2. The record this draft reads for the media tree: `docs/context/generation.md` (measured 2026-09-10 at media `1618638`) and the three judgements of this plan's previous drafts — `docs/reviews/plan-judgements/2026-09-12-batch-generation.md` (33/42, revise), `2026-09-14-batch-generation.md` (34, revise), `2026-09-14-batch-generation-r2.md` (38, dispatch) — whose judges re-ran commands against media `1618638` on 2026-09-14. The drafts themselves are outside this tree (`plan:` front matter → `/home/dalhaka/factory/batch/2026-09-11/drafts-r2/2026-09-11-generation.md`). The landed siblings cite this plan's keys — `grep -n 'GN8\|GN10\|GN11\|GN12' docs/superpowers/plans/2026-09-11-evidence.md docs/superpowers/plans/2026-09-11-platform.md docs/superpowers/plans/2026-09-11-factory.md` → GN8 `dependsOn: GN4, EV15`; GN11 `dependsOn: EV10`, `areas: platform, evidence, generation`; GN10–GN12 on `flake.nix`; GN10 on `hosts/core/default.nix` after PL4 and `hosts/core/proton-backup.nix` beside PL6; GN11 on `plan-status.toml`/`repos.toml` after PL6 — and this file keeps every one of those references true.
3. Two inputs the drafting rules name are absent: `ls docs/superpowers/plans/2026-09-11-defects.md tools/debug/bug-note` → both `No such file or directory`. The commit-body recipe is therefore written out in full in every section (GN-F), and defects found while drafting are listed in Assumption 36 rather than filed.
4. The board at HEAD (`sed -n '10,12p' docs/OPERATIONS.md`): all nine batch plans dispatchable; landing order "evidence → factory → platform → generation → helm → knowledge → isolation → seat-harness → defects (edges … GN8/GN11→EV10/EV15 …)"; "GN8 was redesigned in generation's second round — the feed no longer writes the evidence store; it POSTs HM8's body to `http://127.0.0.1:7710/v1/engage` (loopback-only, drops on error) because the evidence draft's EV14 makes keyed `replace_stream` the stream's only verb and the helm draft assigns the feed-side POST to GN". Batch files in the tree: `git ls-files 'docs/superpowers/plans/*' | grep 2026-09-1` → evidence, factory, platform. Helm's is not, so HM8's endpoint is a contract from that board line plus EV14's row shape, not from a file (Assumption 33).
5. UNVERIFIABLE here as on 2026-09-10 (spec §5 Q7): `nix flake check` in `~/flakes/media`. Every media task builds its acceptance checks by name (`nix build .#checks.x86_64-linux.<name> -L --no-link`) and pastes the tail. The last recorded verifications (`evidence/derived/tasks.jsonl`, duckdb: `select key, checks_verified from … where key like 'W%'`): W3b 2026-09-09 `comfy-worlds-unit`, `comfy-worlds-eval`, the four `comfy-worlds-assertion-negative-*`, `lint` all `pass`; W5b `comfy-upstream-probe-unit`, `comfy-worlds-eval`, `comfyui-package`, `comfyui-startup-clean`, `lint` all `pass`; W6b/W6c (2026-09-10) `lint` `pass`.

**This repo**

6. `python3 pkgs/evidence/tasks.py --root . check` → empty, exit 0. `… json | grep -o '"key": "GN[^"]*"' | wc -l` → `0`; `… json | grep -c '"prefix": "GN"'` → `1` (the manifest field, not a key — the 2026-09-14 erratum 1's false positive).
7. `git ls-files | python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --files /dev/stdin` → exit 1, 27 `uncovered:` lines: `SNAPSHOT.md`, nine `docs/context/*.md`, `docs/ledger/areas-grandfather.toml`, `docs/superpowers/plans/2026-09-11-{evidence,factory,platform}.md`, ten `evidence/*` files and three `tools/cloud/*` (the last fourteen are this snapshot's own). `subsystems-manifest` is red on this tree for reasons outside this plan; EV10 (`ready`) turns it green — GN11 lands after it (`dependsOn`).
8. `tasks.file_area(p, manifest)` (`python3 -c` over `pkgs/evidence/tasks.py`): `hosts/core/media-worlds.nix` → `platform`, `hosts/core/lanes.nix` → `platform`, `flake.nix` → `platform`, `hosts/core/proton-backup.nix` → `platform`, `docs/ledger/subsystems.toml`, `docs/ledger/repos.toml`, `docs/ledger/plan-status.toml` → `evidence`, `docs/runbooks/backup.md` → `knowledge`, `docs/superpowers/plans/2026-09-11-generation.md` → `None`, `media/flake.nix` → `None`; `reserved_prefix("GN1")` → `GN`. Hence `**areas:**` on GN10 (`platform, knowledge, evidence`), GN11 and GN12 (`platform, evidence, generation`).
9. `python3 -c "import sys; sys.path.insert(0,'pkgs/evidence'); import streams; print(len(streams.KINDS), 'engagement' in streams.KINDS)"` → `16 False`: EV15 has not landed. The row shape GN8 sends is EV14's declaration (`docs/superpowers/plans/2026-09-11-evidence.md`, the EV14 `**Interfaces**` terms 1–5): key `(day, surface)`; `day` matching `^\d{4}-\d{2}-\d{2}$`; `surface` in `("home", "feed", "seats")`; `opens`, `dwell_s`, `feed_likes` integers in `0 ≤ n ≤ 10_000_000`; "No other field".
10. Broker instances on core (`grep -rn "hostAddress = \|listenPort = " hosts/ nixosModules/cowork.nix`): cowork `10.100.1.1`/3129 (`nixosModules/cowork.nix`, `mkDefault`), openrouter `10.100.3.1`/3131 (`hosts/core/lanes.nix`), seat `10.100.4.1`/3141 (`hosts/core/seat.nix`); both host files reserve `10.100.2.x` for media ("10.100.2.x is reserved for the media instance"). The instance submodule (`nixosModules/egressBroker.nix`, `options.services.egress-broker.instances`) has `hostAddress`, `namespaceAddress`, `prefixLength` (default 30), `listenPort` (default 3128), `allow` (`listOf str`, default `[ ]`), `usagePathPrefixes`, `bodyPatch`, `denyPaths`, `inject`; the public CA bundle is published at `/var/lib/egress-broker-ca-bundle/<name>/ca-bundle.crt` (`publicDir=/var/lib/egress-broker-ca-bundle/${name}`; `StateDirectory = "egress-broker/${name} egress-broker/${name}/ca egress-broker-ca-bundle/${name}"`), the path `nixosModules/modelLane.nix` reads (`caBundle = name: "/var/lib/egress-broker-ca-bundle/${name}/ca-bundle.crt"`). The proxy URL a consumer builds is `http://${hostAddress}:${toString listenPort}` (`nixosModules/cowork.nix`, `proxyUrl`). An instance-existence assertion reads `services.cowork.brokerInstance '<name>' has no matching services.egress-broker.instances entry` (`nixosModules/cowork.nix`, `assertions`). The broker's nftables chain drops host-namespace traffic to the proxy — `ip daddr ${i.hostAddress} tcp dport ${toString i.listenPort} iifname != "veb-${name}" drop` (`nixosModules/egressBroker.nix`, the drop that "has to run first and in THIS chain") — so every brokered consumer is a system unit that joins the namespace: `nixosModules/seatLane.nix` `User = cfg.operatorUser; NetworkNamespacePath = netnsPath;` (`grep -n 'NetworkNamespacePath\|User = ' nixosModules/seatLane.nix nixosModules/cowork.nix`), ordered `after`/`requires` its `egress-broker-<name>.service`.
11. The checks GN10 copies are in `flake.nix`: `core-backup-wiring` (a `throw "core-backup-wiring: …"` chain over `self.nixosConfigurations.core.config`; its last arms `docs/runbooks/backup.md does not name these backup paths: ${toString undocumented}`, the lane-ledger bullet, the `/var/lib/egress-broker` sentence) and `core-gaming-wiring` (`lockData = builtins.fromJSON (builtins.readFile ./flake.lock)`, `gamingNixpkgsNodeName = lockData.nodes.gaming.inputs.nixpkgs`, `hostNixpkgsRev = lockData.nodes.nixpkgs-host.locked.rev`, direct equality). The inputs block pins `gaming.url = "git+file:///home/dalhaka/flakes/gaming?ref=main"` and `nixpkgs-host.url = "github:NixOS/nixpkgs/a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4"`; `outputs = { self, nixpkgs, nixpkgs-host, llm-agents, claude-desktop, gaming }`. `hosts/core/proton-backup.nix` lists thirteen `paths`, among them `/home/dalhaka/flakes` and `/home/dalhaka/.claude/projects/-home-dalhaka-flakes-media/memory`; `docs/runbooks/backup.md` names each ("thirteen of them (a check, `core-backup-wiring`, fails the build if any named path is missing from this list)"). `hosts/core/default.nix` `imports` twelve files ending `../../nixosModules/usageIngest.nix`; `hosts/core/graphics.nix` sets `services.xserver.videoDrivers = [ "nvidia" ]`. `checks.${system} = {` is one literal attrset in `flake.nix`.
12. Rows that own this plan's host-side files (`docs/ledger/subsystems.toml`): Platform `"flake.nix"`, `"flake.lock"`, `"hosts/*"`; Evidence `"docs/ledger/subsystems.toml"`, `"docs/ledger/repos.toml"`, `"docs/ledger/plan-status.toml"`, `"docs/MAP.md"`, `"docs/subsystems.md"`; Knowledge `"docs/runbooks/*"`; Generation `owns = []`, `plans` = `2026-09-02-media-flake.md` (`docs/ledger/plan-status.toml`: `status = "superseded"`, "executed as ~/flakes/media's own plan copy; media rework closed 2026-09-03") and this file. `docs/ledger/repos.toml`: `[[repo]] name = "media" path = "~/flakes/media"`, no `ledger` line. PL6 writes an absorbed sibling's row as `path = "~/nixos-agent-env"`, `plans = "docs/superpowers/plans/absorbed/dsh-harness/*.md"` plus a comment, and a `[[plan]]` row `status = "done"` for an untyped record file (`2026-09-11-platform.md`, PL6 `**Files.**`) — GN11 copies that shape with `media`.
13. The driver's A5 guards are in the tree (`tools/factory/seat/`, read): `factory-task` and `factory-wave` die 2 on an unset plan — `FACTORY_PLAN is unset — name the plan (FACTORY_PLAN=<plan.md> …) or launch through factory-dispatch`; `factory-integrate` refuses `REFUSED <key>: docs/OPERATIONS.md changed outside the queue block` and `REFUSED <key>: <n> undisclosed file(s) outside touches`; `factory-task` records a near-miss result line as `FACTORY-NOTES result-misparse: …`; `factory-commit-msg.sh` refuses a staged file outside `touches` unless the body carries `Deviation: <path> — <reason>`. No `dependsOn` on a guard task is needed; GN-E/GN-F state the seat's side.
14. `factory-dispatch <run> <repo-path> <plan>` resolves the repo name from `<repo-path>/docs/ledger/repos.toml` (`factory_die 2 "factory-dispatch: no repos.toml at $toml"`) and queries `tasks.py --root <repo-path> waves --repo NAME --plan <basename> --next`; `~/flakes/media` has no `docs/ledger/`, and `python3 pkgs/evidence/tasks.py --root /tmp/nonexistent-media waves --repo media --plan 2026-09-11-generation.md --next` → `tasks: unknown repo media`, exit 1 (`factory-dispatch: graph query failed`, die 6). Media waves therefore launch as hand `factory-wave` lines, the way the program plan's `## Dispatch` launched W6b (`FACTORY_PLAN=… tools/factory/seat/factory-task w46b /home/dalhaka/flakes/media W6b --prior w46/W6`); `factory-dispatch --dry-run` applies to GN10–GN12 (Dispatch).
15. The two incidents the drafting rules cite (DF13 and HM7c, 2026-09-15) appear in no tree file: `grep -rln 'DF13\|HM7c' docs/ tools/ .claude/` → the four `.claude/workflows/*.js` only; the board's log ends at session 23 (2026-09-14). GN-E carries both lessons regardless.
16. Cross-repo dependencies resolve by `(repo, chain root)`: `pkgs/evidence/tasks.py`, the comment "Satisfaction is keyed by (repo, chain root): a dependency whose chain root resolves locally (to this repo) is satisfied iff it is in `landed_keys`; one attributed to another repo is satisfied iff that (repo, root) pair is in `extra_landed`"; `check()` resolves a `dependsOn` against "every typed key in its own plan files (whatever `repo:` they name)". So GN10's `dependsOn: GN9` (a `**repo:** media` key typed in this file) is known to this repo and stays `blocked` until media's `main` carries GN9's commit subject — a graph edge, not a prose precondition.
17. Live keys on this plan's files, `ready`/`blocked` only (`tasks.py --root . json` filtered on `touches`; every other hit is `approved` without a landing commit, Assumption 1): `flake.nix` — N13, N15, N17, HH2, HH3, FIX6, EV1, IS4, EV16 (`ready`); HH6, HH8, HH9, SP5, EV6, IS5b, FA23, PL2, PL3, PL4, PL5 (`blocked`). `hosts/core/default.nix` — EV1 (`ready`), PL4 (`blocked`). `hosts/core/proton-backup.nix` — PL6 (`blocked`). `hosts/core/lanes.nix` — none. `docs/ledger/subsystems.toml` — EV10, FA13, PL1 (`ready`). `docs/ledger/repos.toml`, `docs/ledger/plan-status.toml` — PL6 (`blocked`). `docs/runbooks/backup.md` — none. `docs/MAP.md` — UI1, FIX5, FIX5b, FIX5c, FIX5d, FIX6, FIX7, EV1, EV16 (`ready`); EV13, EV15, EV6, FA23 (`blocked`).

**Media, quoted — each re-measured by the seat at Step 0 (GN-A)**

18. Public surface at `1618638` (spec §2, confirmed by the r2 judges: "media's checks/packages/nixosModules counts 21/5/3"): `nixosModules` `comfyui`, `comfyui-worlds`, `default`; `packages` `comfyui`, `comfy-worlds-init`, `media-comfy`, `media-fetch-models`, `comfy-upstream-probe`; 21 checks — `lint`; `comfyui-package`, `comfyui-eval`, `comfyui-cliploader-krea2`, `comfyui-startup-clean`, `comfyui-vm`, `comfyui-assertion-negative-{broker,gpu,listen,listen-address,token}`; `comfy-worlds-eval`, `comfy-worlds-unit`, `comfy-worlds-vm`, `comfy-worlds-assertion-negative-{hosts,name,password-path,ports}`; `media-fetch-unit`, `media-fetch-bats`; `comfy-upstream-probe-unit`. 97 tracked files; `flake.nix` 892 lines; `pkgs/comfy-worlds/` holds `feed_placeholder.py` (157), `init.sh` (137), `default.nix` (93), `media-comfy.sh` (61).
19. `services.comfyui-worlds` (spec §2): `operatorUser`, `root`, `package`, `cpuOnly`, `worlds` (per world `comfyPort`, `feedPort`, `host`), `lan`; two worlds `sfw` and `nsfw`; generators are `wantedBy = []` on-demand user units on distinct loopback ports; Caddy renders only under `lan.enable` (`mkIf cfg.lan.enable` at five sites, r2 judgement Judge 3 row 2); the probe unit sets `unitConfig.ConditionUser = cfg.operatorUser` (r2 erratum 11); the feed unit is `ProtectSystem = "strict"` with a `ReadWritePaths` list (2026-09-14 erratum 13). The worlds' ComfyUI ports are 8288 and 8289 (2026-09-12 Judge 3 row 5). Unit attribute names are measured at Step 0 (`grep -n 'services\.\|\.service\|\.timer' nixosModules/comfyui-worlds.nix`), never assumed.
20. `pkgs/comfy-worlds/default.nix` wraps every script as `${pkgs.python3}/bin/python3 ${./onefile.py} "$@"` — "each `${./x.py}` interpolation is Nix's own isolated single-file store path with no sibling files and no PYTHONPATH anywhere in the file" (r2 erratum 1, Judge 1 row 3); `comfy-worlds-init`'s `init.sh` carries `FETCH_PY=${../media-fetch/fetch.py}`. `worldsPkgs` exports `comfy-feed` and `comfy-world-guard` among others (2026-09-12 erratum 23). GN1 replaces the single-file interpolations with one directory derivation (GN1 Interfaces 5) so sibling imports resolve; a module named `queue.py` would shadow the stdlib (r2 erratum 2) — the queue is `job_queue.py`.
21. `feed_placeholder.py`: `GET /` (world name, generator `is-active`, 50 newest `*.png`), `GET /out/<name>` (basename only, no `/`, no `..`), `GET /healthz`; `comfy-worlds-unit` tests only the escape and basename guards (spec §2) in `tests/comfy-worlds/test_feed_placeholder.py` (2026-09-14 erratum 12 cites its thread-start helper); a `POST` answers `HTTP Error 501: Unsupported method ('POST')` (r2 Judge 3 row 4). `comfy-worlds-unit` copies its test tree into the sandbox by an explicit `cp -r` block (r2 Judge 1 row 2: "the comfy-worlds-unit cp -r block") — a directory outside that block is invisible to the check (r2 Anticipation: "GN2's check can't see tests/mocks").
22. ComfyUI's API graph, as `tests/acceptance/workflows/sdxl.json` shows it (2026-09-12 erratum 1: "sdxl.json, ace-step.json and video.json all show the exact class_type/inputs shape"; r2 Judge 1 row 2: "the exact class_type count 7 and one KSampler"): a JSON object keyed by node id (a string), each value `{"class_type": <str>, "inputs": {…}}`; a `KSampler` node's `inputs` carry `seed`, `sampler_name` and `positive` (a link `[<node id>, <slot>]`); a `CLIPTextEncode` node's `inputs` carry `text`. ComfyUI's `SaveImage` writes that graph into the PNG as the `prompt` text chunk and the UI graph as `workflow`.
23. `probe.py` opens URLs directly ("the probe's direct `urllib.request.urlopen` … becomes a proxied opener", r2 Judge 3 row 9); `grep -o 'https://[a-z.]*' pkgs/comfy-upstream-probe/probe.py | sort -u` prints seven lines, one of them the spurious `https://pypi` from a regex literal — the six hosts are `api.github.com`, `download.nvidia.com`, `github.com`, `pypi.org`, `raw.githubusercontent.com`, `www.nvidia.com` (2026-09-12 errata 7 and 20). `comfy-upstream-probe-unit` had 16 tests (r2 Judge 3 row 2); the timer is `comfy-upstream-probe.timer`, user scope, Sunday 04:00 (spec §2).
24. Media's own `flake.nix` asserts `services.egress-broker.instances.media.inject ? "huggingface.co"` for the single-service `services.comfyui` module, and `checks/eval-harness.nix` stubs instance `media` with a huggingface.co/docker allowlist (2026-09-12 erratum 12). Nothing in this plan enables `services.comfyui` on core: the worlds' generators run the `comfyui` package as user units, and model fetches stay the operator's act under media's runbook — so the `media` instance GN10 declares carries `allow` for the probe alone and no `inject`; widening it for `media-fetch-models` on core is a later task (Not in this plan).
25. Media's `nixpkgs` is `ac62194c…`, this flake's `nixpkgs-host` `a5cc6f2c…` (2026-09-12 Judge 3 row 2; here `grep -n 'nixpkgs-host.url' flake.nix`). 43b moves an absorbed subsystem onto `nixpkgs-host`; GN12's first `comfyui-package` build against it is the measurement (Anticipation).
26. `docs/runbooks/media.md` has twelve `## ` sections and `tests/acceptance/media-worlds.sh` eight drill steps with a `--self-test` mode (r2 Judge 3 row 2; the 2026-09-14 erratum 16 corrected eleven → twelve); `/healthz` answers `ok <world>` (r2 Judge 3 row 10).
27. Media's landed keys: W1, W2, W2r, W3, W3b, W4, W5, W5b, W6, W6b, W6c (spec §4). The store's gate rows (`evidence/derived/gates.jsonl`, `key like 'W%'`): W2, W2b, W3, W5 `rejected` with no class recorded; W3b `approved` 6/9 mutants opus; W5b 12/16 opus; W6b 3/3 sonnet; W6c 2/2 sonnet; `plan_defect: none` on the four approvals. The rejection classes are the spec's §4 list (GN-B–GN-D).
28. `~/flakes/media` has its own `docs/OPERATIONS.md` (spec §3: "board note `~/flakes/media/docs/OPERATIONS.md:5`"); GN-E applies there too.

**Applied recommendations (veto surface each)**

29. Plan file name: this file is `2026-09-11-generation.md` whatever the workflow's `date`, because the manifest's `plans` entry — read from `main`, not the branch, by every `--root`-only checker (spec §5 Q1) — names it. Veto: a manifest edit on `main` first.
30. (spec §5 Q2) WH1 and WH2 are superseded, not re-typed: WH1's host stanza is GN10 (with the wiring check and the backup paths), WH2 (the Helm tile reading `proposals.jsonl`) is Helm's (`HM`); the two `### WH…` headings stay in media's `2026-09-05-comfy-worlds.md` as history the parser skips (spec §5 Q2: `HEADING_RE` accepts only the typed shape). Veto: a re-key of either as a `GN` task at re-plan.
31. (spec §5 Q4) The mutation grammar lives in the lab's `manifest.toml` — `<root>/worlds/<w>/lab/manifest.toml`, the file `init.sh` creates — as a `[mutate]` table (GN5 Interfaces 1); the mutator reads the lab and never writes it. Veto: another path is a one-line change in GN5/GN6.
32. (spec §5 Q5) Feed state is `<root>/worlds/<w>/feed.sqlite` (design: "reserved for sub-project 2 (index, rebuildable)"), rebuilt from the PNGs' own chunks at every feed start; deleting it loses likes and queued jobs, nothing else. Veto: none needed — the design reserves the file.
33. Engagement: the feed POSTs `{"day", "surface": "feed", "opens", "dwell_s", "feed_likes"}` (EV14's five fields, Assumption 9) to `http://127.0.0.1:7710/v1/engage` (the board line, Assumption 4), the URL a module option with that default, loopback-only, dropped on any error, once an hour and at SIGTERM. Veto: the Helm plan's HM8 as landed changes the URL or the verb — a one-line option default and one test literal.
34. The feed's HTML rule copies Helm's ("the page composes no <script, no src=, no href="http", `pkgs/helm/serve.py`) and generalises it to every attribute value (GN3 Interfaces 5, the 2026-09-14 erratum 22). Veto: none.
35. The media-side seats run in `~/factory/ws/<run>/<KEY>` cloned from `~/factory/base/media` (`tools/factory/seat/factory-lib.sh`: `FACTORY_BASE=$FACTORY_ROOT/base`, `FACTORY_WS=$FACTORY_ROOT/ws`); the plan file is this repo's, read by path (`factory-brief <plan> <KEY>`); the gate is Sonnet (the GN row's `gate = "sonnet"`). Veto: none.
36. Defects found while drafting, for the bug ledger, not this plan's tasks: (i) `factory-dispatch` cannot drive a ledger-less sibling (Assumption 14; Factory's); (ii) the `draft-byref` workflow names two inputs absent from the tree (Assumption 3; Factory's); (iii) `subsystems-manifest` is red on the F4 snapshot for fourteen snapshot-only files (Assumption 7; the snapshot's, not the host's).

## Waves

Derived on the F4 snapshot by `tasks.py`'s own code, three ways, outputs pasted verbatim (`/tmp/draft-scratch/queries.log` holds every command with its exit code):

1. **The live-tree draft check** — `python3 pkgs/evidence/tasks.py --root . --runs-dir /nonexistent --store /nonexistent check --draft /tmp/draft-scratch/2026-09-11-generation.md` (the draft copied under this plan's basename, Assumption 29):
```
tasks: GN10 acceptance core-media-wiring not in docs/MAP.md
tasks: GN12 acceptance comfy-worlds-unit not in docs/MAP.md
tasks: GN12 acceptance comfy-worlds-eval not in docs/MAP.md
tasks: GN12 acceptance comfy-upstream-probe-unit not in docs/MAP.md
tasks: GN12 acceptance media-fetch-unit not in docs/MAP.md
tasks: GN12 acceptance core-media-wiring not in docs/MAP.md
exit 1
```
   Every line is a MAP-currency line for a check this plan creates or moves (`core-media-wiring` by GN10; media's checks by GN12), an artefact of checking before landing: `draft_rules` reads `docs/MAP.md`'s Checks section, which the task that adds the check regenerates in its own commit (G5's exemption). No unknown key: EV10 and EV15 are typed in the landed Evidence plan (Assumption 2), GN9 is typed here.
2. **The scratch-copy form** (rubric row 13; `cp -a` of the tree to `/tmp/draft-scratch/tree`, the draft placed as `docs/superpowers/plans/2026-09-11-generation.md`, a one-repo `--repos` file naming that copy): `check` →
```
(nothing printed)
exit 0
```
   `waves --repo nixos-agent-env --json` →
```
[[["EV1", "EV10", "EV16", "EV5", "FA11", "FA13", "FA14", "FA3", "FIX5", "FIX5b", "FIX5c", "FIX5d", "FIX6", "FIX7", "HH2", "HH3", "IS4", "N13", "N14", "N15", "N17", "N18", "PL1", "UI1"], ["EV11", "EV12"], ["EV14"], ["EV17"], ["FA10"], ["IS2"], ["N16"]], [["EV13", "EV15"], ["FA12"], ["FA15"], ["FA18"], ["PL2"]], [["FA16"], ["PL3"]], [["FA17"], ["FA23", "PL4"], ["PL7"]], [["PL5"]], [["PL6"]]]
```
   No `GN` group appears in this repo's waves: GN1–GN9 leave this repo's list on their `**repo:** media` line, GN10 is `blocked` on GN9 until media's `main` carries it (Assumption 16), GN11 on EV10 and GN10, GN12 on GN11. New `conflicts` rows the draft adds — the rows naming a `GN` key, summarised per file by a pipeline over the same output (the 411 pre-existing rows are Assumption 1's; every key listed is sequenced in `## Cross-plan`):
```
$ … conflicts | grep -E 'GN[0-9]+ ' | wc -l
76
$ … conflicts | grep -E 'GN[0-9]+ ' | <per file: the GN key, then the other keys>
docs/MAP.md GN10: EV1 EV13 EV15 EV16 EV6 FA23 FIX5 FIX5b FIX5c FIX5d FIX6 FIX7 UI1
docs/MAP.md GN12: EV1 EV13 EV15 EV16 EV6 FA23 FIX5 FIX5b FIX5c FIX5d FIX6 FIX7 UI1
docs/ledger/plan-status.toml GN11: PL6
docs/ledger/repos.toml GN11: PL6
docs/ledger/subsystems.toml GN11: EV10 FA13 PL1
docs/subsystems.md GN11: EV10 PL1
flake.nix GN10: EV1 EV16 EV6 FA23 FIX6 HH2 HH3 HH6 HH8 HH9 IS4 IS5b N13 N15 N17 PL2 PL3 PL4 PL5 SP5
flake.nix GN12: EV1 EV16 EV6 FA23 FIX6 HH2 HH3 HH6 HH8 HH9 IS4 IS5b N13 N15 N17 PL2 PL3 PL4 PL5 SP5
hosts/core/default.nix GN10: EV1 PL4
hosts/core/proton-backup.nix GN10: PL6
```
3. **The media-side waves** — `tasks.wave_structure` over the nine `repo: media` sections parsed from the draft with state `ready` (the media repo has no path here, so `waves --repo media` prints `[]`; the function is the tool's own peel-off, run by `python3 -c` over `parse_plan`). Alone, the nine stop at wave 3 because GN8's `EV15` edge is unknown to a graph that holds only them — the second run shows the schedule once EV15 has landed here:
```
$ tasks.wave_structure over the nine sections alone
[[["GN1", "GN7"]], [["GN2"], ["GN3"], ["GN5"]], [["GN4"], ["GN6"]]]
$ the same with a pseudo-task EV15 in state landed added to the graph (the cross-repo edge satisfied)
[[["GN1", "GN7"]], [["GN2"], ["GN3"], ["GN5"]], [["GN4"], ["GN6"]], [["GN8"]], [["GN9"]]]
```

Read as a schedule: **wave 1** `"GN1 GN7"` — one seat group (both touch media's `flake.nix`; GN1 first by key order); **wave 2** `"GN2" "GN3" "GN5"` — three seats in parallel; **wave 3** `"GN4" "GN6"` — two seats; **wave 4** `"GN8"` — after EV15 has landed here (the landing order puts Evidence first, Assumption 4); **wave 5** `"GN9"`; then, in this repo, **GN10** (switch #N), the landing act, **GN11**, **GN12** (switch #N+1). Two seats in one group serialise in key order inside one workspace; two groups in one wave run at once.

## Cross-plan

Ordering for every live overlap with this plan's `touches` (Assumption 17), who goes first and why:

- **`flake.nix` — GN10, GN12 × PL2–PL5 (`blocked`), EV16, FIX6, N13, N15, N17, HH2, HH3, IS4, EV1 (`ready`), HH6, HH8, HH9, SP5, EV6, IS5b, FA23 (`blocked`).** The published batch order (Platform's chain first, then single-attribute check additions — EV16, HM3, GN10, KN13 — then VM hunks, then GN11/GN12, KN15–KN19, FA23 last: `2026-09-11-evidence.md`, Cross-plan) stands; GN10 adds one input line, one module line and one check attribute — three hunks that rebase in minutes; GN12 restructures `checks.${system}` into a `let … in` and is last of its group. Before every GN launch on this file the orchestrator waits for any `running`/`ran` key sharing it (Dispatch).
- **`hosts/core/default.nix` — GN10 × PL4 (`blocked`), EV1 (`ready`).** Additive `imports`; PL4 first when it is `ready` before GN10, else GN10 first — either rebases one line.
- **`hosts/core/proton-backup.nix`, `docs/ledger/repos.toml`, `docs/ledger/plan-status.toml` — GN10/GN11 × PL6 (`blocked`).** PL6 first (increment 2; GN11 copies its row shape, Assumption 12); each is an additive row or path.
- **`docs/ledger/subsystems.toml` — GN11 × EV10, FA13, PL1 (`ready`).** EV10 first (it alone turns `subsystems-manifest` green and every later editor integrates against it — GN11 `dependsOn: EV10`); FA13 and PL1 append to their own rows; GN11 edits only the Generation row and re-runs `subsystems.py write`.
- **`docs/MAP.md` — GN10, GN12 × every key that regenerates it.** Regeneration only: whichever lands last re-runs `repomap.py --root . write`.
- **`docs/runbooks/backup.md` — GN10 × none open.**
- **Evidence (`EV`):** GN8 `dependsOn: EV15` (the `feed` surface and the five fields, Assumption 9); GN11 `dependsOn: EV10` (the plans-directory glob). **Helm (`HM`):** HM8's `/v1/engage` is the endpoint GN8 posts to (Assumption 33); the feed link or embed is Helm's; nothing here touches a Helm file. **Platform (`PL`):** the landing act copies PL Q6(b)'s shape; `pkgsHost` is introduced by GN12 unless Platform's chain has a binding of that name by then (Step 0 measures). **Isolation (`IS`):** the LAN face (question 3) is IS's increment-4 task; GN10's `lan.enable = false` is the assertion it flips. **Factory (`FA`):** `factory-dispatch` for a ledger-less sibling (Assumption 36 i).

## Operator

Every step is one command with its acceptance after the arrow; nothing here is a seat's act (G1). Unit names come from `docs/runbooks/media-worlds.md`, which GN10 writes from `nix eval` (its Interfaces 6); the ports below are GN10's literals (`sfw` 8288/8388, `nsfw` 8289/8389).

**Before any wave (A3, A9).**
0. `ls ~/factory/runs | grep -c '^gn'` → `0` (the run names of Dispatch are free); `git -C ~/flakes/media status --short` → empty. Wave 2 starts three seats: if the board's last top-up line is older than the activity export's last ingested day (`evidence bundle --markdown`, the spend row), top up first — a proxy: the export is a manual download and the balance itself is never read.

**After GN10 integrates — switch #N.**
1. `nix build .#checks.x86_64-linux.core-media-wiring -L --no-link && nix build .#checks.x86_64-linux.host-core -L --no-link && nix build .#checks.x86_64-linux.core-backup-wiring -L --no-link` → all three build.
2. `nix build .#nixosConfigurations.core.config.system.build.toplevel -o /tmp/gn10-result && nix store diff-closures /run/current-system /tmp/gn10-result` → **prediction** (A2): `+ comfyui-<version>` with its torch/CUDA closure (gigabytes), `+ comfy-worlds-init`, `+ media-comfy`, `+ comfy-upstream-probe`, `+ media-fetch-models`, `+ comfy-feed`, `+ comfy-feed-index`, `+ comfy-mutate`, a second `python3` from media's own nixpkgs pin (Assumption 25; gone after GN12), and the `egress-broker-media` and `comfy-upstream-probe` units in `etc`; **no `caddy` line** (question 3(a)). The measured delta in GN10's commit body is pasted beside this line before the switch; a mismatch is a finding against this plan.
3. `readlink /nix/var/nix/profiles/system` → `system-<N-1>-link` — the rollback target; it goes into the board line.
4. `sudo nix-env -p /nix/var/nix/profiles/system --set /tmp/gn10-result && sudo /tmp/gn10-result/bin/switch-to-configuration switch` → then `systemctl is-active egress-broker-media.service` → `active`; `ip netns list | grep -c egress-media` → `1`; `systemctl list-timers comfy-upstream-probe.timer --no-legend | wc -l` → `1` (spec §5 Q8 measured: a system timer, started by the switch).
5. `systemctl --user list-units 'comfy-*' --all --no-legend | awk '{print $1, $4}'` → every unit `inactive` (a switch starts no user unit), the names as the runbook lists them.
6. `ls /home/dalhaka/comfyui/models | wc -l` → above `0` (A3: the models the media drills fetched; if `0`, run media's runbook fetch first — the operator's act through media's own path, not this plan's).
7. `systemctl --user start <sfw generator unit>` then `curl --noproxy '*' -s http://127.0.0.1:8288/system_stats | head -c 120` → JSON beginning `{"system"` (ComfyUI up on the world's port).
8. `journalctl --user -u <sfw generator unit> --no-pager | grep -i aimdo` → paste; a line naming aimdo loaded and no `IMPORT FAILED` is the claim's evidence (step 23).
9. `systemctl --user start <sfw feed unit>` then `curl --noproxy '*' -s http://127.0.0.1:8388/healthz` → `ok sfw`.
10. `ls /home/dalhaka/comfyui/worlds/sfw/output | wc -l` → above `0` (the generator has rendered), then `curl --noproxy '*' -s http://127.0.0.1:8388/ | grep -c '<article'` → above `0`.
11. `N=$(curl --noproxy '*' -s http://127.0.0.1:8388/ | grep -o 'name="name" value="[^"]*"' | head -1 | cut -d'"' -f4); curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' -d "name=$N" http://127.0.0.1:8388/like` → `303`; `nix develop -c python3 -c "import sqlite3; print(sqlite3.connect('/home/dalhaka/comfyui/worlds/sfw/feed.sqlite').execute('select count(*) from likes').fetchone()[0])"` → `1`.
12. `curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' -d "name=$N" http://127.0.0.1:8388/regenerate` → `303`; within a minute `curl --noproxy '*' -s http://127.0.0.1:8388/jobs | nix develop -c python3 -c "import json,sys; print([(j['kind'], j['state']) for j in json.load(sys.stdin)])"` → `[('regenerate', 'done')]` (or `submitted` while ComfyUI renders), and one more PNG in `output/`.
13. `curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' -d "name=$N" -d "prompt=a red fox, drill" http://127.0.0.1:8388/edit` → `303`; the `/jobs` line → an `edit` row.
14. `systemctl --user start comfy-mutate-sfw.service; systemctl --user show -p Result --value comfy-mutate-sfw.service` → `success`; the `/jobs` line → eight `mutate` rows. Then determinism: `B=$(systemctl --user show -p ExecStart --value comfy-mutate-sfw.service | sed -n 's/.*path=\([^ ;]*\).*/\1/p'); "$B" --world sfw --root /home/dalhaka/comfyui --dry-run --seed 1 >/tmp/m1; "$B" --world sfw --root /home/dalhaka/comfyui --dry-run --seed 1 >/tmp/m2; cmp /tmp/m1 /tmp/m2 && echo identical` → `identical`.
15. `sudo systemctl start comfy-upstream-probe.service; systemctl show -p Result --value comfy-upstream-probe.service` → `success`; `journalctl -u comfy-upstream-probe.service --no-pager | tail -5` → the probe's proposal lines, no traceback; `sudo grep -c 'api.github.com' /var/lib/egress-broker/media/audit.jsonl` → above `0` (a count over a local audit log that never leaves the machine).
16. `P=$(systemctl show -p ExecStart --value comfy-upstream-probe.service | sed -n 's/.*path=\([^ ;]*\).*/\1/p'); env -u HTTPS_PROXY -u SSL_CERT_FILE "$P"; echo "exit $?"` → `exit 2` with `probe: HTTPS_PROXY is unset — invariant 3 …` on stderr — run as the operator outside the namespace, which is also the proof that the direct path is gone.
17. `journalctl --user -u <sfw feed unit> --no-pager | grep -c 'engage: dropped'` → above `0` after the first hour (the drop path is the measured behaviour until Helm's HM8 lands); after HM8: `grep -c '"surface": "feed"' /var/lib/evidence/ledger/engagement.jsonl` → above `0` (a count; no row opened).
18. `FEED_PORT=8388 ROOT=/home/dalhaka/comfyui PROBE_BIN="$P" MUTATE_BIN="$B" bash ~/flakes/media/tests/acceptance/media-worlds.sh; echo "exit $?"` → fourteen `PASS` lines, `exit 0` — the composed drill (70b).
   **Rollback #N:** `sudo /nix/var/nix/profiles/system-<N-1>-link/bin/switch-to-configuration switch` (step 3's generation); `/home/dalhaka/comfyui` is untouched by a generation change; `feed.sqlite` is rebuildable (`comfy-feed-index rebuild --root /home/dalhaka/comfyui --world sfw`).

**The landing act (question 2(a); the orchestrator's, after step 18 and the operator's "test passed"; no key).**
19. `R=$(git -C ~/flakes/media rev-parse HEAD); git fetch ~/flakes/media main && git tag "absorbed/media-$R" FETCH_HEAD && git checkout -b absorb/media main && git merge -s ours --no-commit --allow-unrelated-histories FETCH_HEAD && git read-tree --prefix=media/ -u FETCH_HEAD && nix develop -c treefmt && git add -A media && nix develop -c git commit -m "generation: media absorbed as media/ (landing act, tag absorbed/media-$R)"` → then `git cat-file -p HEAD | grep -c '^parent'` → `2`; `git merge-base --is-ancestor "$R" HEAD && echo reachable` → `reachable` (48a); `git ls-files media | wc -l` → `97`; `nix build .#checks.x86_64-linux.lint -L --no-link` → builds — if it does not (treefmt or statix over `media/`), a `GN13` (`plan-append`, 53a) is typed before GN11 dispatches, never a letter suffix; then `git checkout main && git merge --ff-only absorb/media`, and the board line names the tag.

**After GN12 integrates — switch #N+1.**
20. `nix build .#nixosConfigurations.core.config.system.build.toplevel -o /tmp/gn12-result && nix store diff-closures /run/current-system /tmp/gn12-result` → **prediction**: the ComfyUI closure moves to `nixpkgs-host`'s python and torch (one `comfyui-…` line with two versions, the second `python3` line gone), no unit added or removed, no `caddy`; GN12's measured delta beside it.
21. `readlink /nix/var/nix/profiles/system` → `system-<N>-link`; switch as in step 4 → steps 9 and 15 repeat green (`ok sfw`, `success`).
22. `mv ~/flakes/media ~/factory/archive/media-$R` → the operator's act (nothing in this plan deletes the clone); afterwards `evidence bundle --markdown` shows no `media` sibling head and `docs/ledger/repos.toml`'s `media` row already points here (GN11).
23. The claim (A8), in the board commit after step 8's line: `docs/ledger/claims.toml`, the `aimdo-native-load-unmeasured` row becomes `status = "verified"`, `class = "operator"`, `evidence = "operator:<date> media acceptance drill on core, step 8: the sfw generator's journal names aimdo loaded (plan 2026-09-11-generation.md)"`; `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"` → silent.
   **Rollback #N+1:** `sudo /nix/var/nix/profiles/system-<N>-link/bin/switch-to-configuration switch`; in the tree, in this order, `git revert <GN12 commit>` (the `media` input returns), `git revert <GN11 commit>`, `git revert -m 1 <landing merge>`; the archived clone comes back by `mv`.

## Dispatch

The run names must not exist under `~/factory/runs` (`BUG-run-name-reuse`; Operator step 0). Media waves launch by hand `factory-wave` lines — `factory-dispatch` cannot query a ledger-less sibling (Assumption 14) — from this repo's checkout, against the media clone, with this plan as `FACTORY_PLAN`; the gate is Sonnet (Assumption 35). Commit the regenerated board block before every dispatch (G6, the orchestrator's).

```
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw1 /home/dalhaka/flakes/media "GN1 GN7" --then "gate each, integrate and fast-forward each"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw2 /home/dalhaka/flakes/media "GN2" "GN3" "GN5" --then "gate each, integrate and fast-forward each"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw3 /home/dalhaka/flakes/media "GN4" "GN6" --then "gate each, integrate and fast-forward each"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw4 /home/dalhaka/flakes/media "GN8" --then "gate, integrate and fast-forward"      # after EV15 has landed on this repo's main
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw5 /home/dalhaka/flakes/media "GN9" --then "gate, integrate and fast-forward"
tools/factory/seat/factory-dispatch gnw6 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md --dry-run
tools/factory/seat/factory-dispatch gnw6 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md
tools/factory/seat/factory-dispatch gnw7 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md --dry-run      # after the landing act; prints GN11
tools/factory/seat/factory-dispatch gnw8 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md --dry-run      # prints GN12
```

The dry run on the scratch copy today (`FACTORY_PYTHON3_CMD=python3 FACTORY_TOOLBOX_REPO=/tmp/draft-scratch/tree tools/factory/seat/factory-dispatch gnw6 /tmp/draft-scratch/tree docs/superpowers/plans/2026-09-11-generation.md --dry-run --repo-name nixos-agent-env`, the copy's `repos.toml` row pointed at the copy):
```
factory-dispatch: nothing schedulable in 2026-09-11-generation.md (all landed, in flight, or blocked)
exit 0
```
— the expected answer while GN9 has not landed on media's `main`; once it has, the same line prints `would run: factory-wave gnw6 /home/dalhaka/nixos-agent-env "GN10"`.

**Landing recipe, per key (A1), in order:** (1) keep only the one commit the section names — `git -C ~/factory/ws/<run>/<KEY> log --format='%h %s' <base>..task/<KEY>` shows one line, else `git -C ~/factory/ws/<run>/<KEY> reset --hard <that sha>` (three seats appended a fabricated board commit on 2026-09-05); (2) if the base moved under a file the task touches, the **integrator** merges — `git -C ~/factory/ws/<run>/<KEY> fetch ~/flakes/media main && git -C ~/factory/ws/<run>/<KEY> merge --no-edit FETCH_HEAD` for a media key, `… fetch ~/nixos-agent-env main …` for GN10–GN12 — never the seat (GN-E); (3) `tools/factory/seat/factory-review <run> <repo> <KEY>` and commit the review; (4) `tools/factory/seat/factory-integrate <run> <repo> <KEY>` then `git -C ~/flakes/media pull --ff-only ~/factory/base/media integ/<run>` (media) or `git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>` (this repo), gated on both exit codes; (5) dispatch what it unblocks (A7): GN1 → GN2, GN3, GN5; GN7 with GN1 → nothing more; GN2 + GN3 → GN4; GN2 + GN5 → GN6; GN4 (+ EV15) → GN8; GN4, GN6, GN7, GN8 → GN9; GN9 → GN10 (then switch #N); GN10 (+ EV10, the landing act) → GN11; GN11 → GN12 (then switch #N+1). **Relaunch after a rejection** (A6): `FACTORY_PLAN=<this plan> tools/factory/seat/factory-task <run>b <repo> <KEY>b --prior <run>/<KEY>` — a media fix round carries `**repo:** media` in its own section, appended at re-plan; the dead seat's diff stays in `~/factory/ws/<run>/<KEY>`.

## Anticipation

- **The tree this draft could not read.** Every media section's Step 0 re-measures its quoted facts (GN-A); a drifted fact stops the task `failed` with `fact drift`, and the orchestrator re-plans that key rather than letting the seat improvise. Prepared: the Facts list per section is the exact command set.
- **The probe moves to system scope** (GN7): a system timer starts at switch #N (Operator step 4), where the old user timer did not; the probe's output directory must be writable from the unit (Interfaces 3's `ReadWritePaths`), and the VM check needs the `media` instance stub — GN7's Step 0 measures both.
- **The packaging fix lands first** (GN1) and its executable proof is GN3's `comfy-feed --help`; until GN3, M8 is killed by a probe only — said in GN1.
- **`comfy-worlds-unit` cannot see a test directory outside its copy block** (Assumption 21): GN1's copy-the-directory rule covers GN2–GN8's files; a task that still needs a `flake.nix` edit discloses it with a `Deviation:` line.
- **GN1's fixture PNG is not a ComfyUI render.** The chunk keyword `prompt` and the API-graph shape (Assumption 22) are what ComfyUI writes; the drill's step 12 (a real render regenerated) is the live proof, and a mismatch there is a `fact drift` against Assumption 22, not a seat's fault.
- **Two writers of `feed.sqlite`** (the feed's worker and `comfy-mutate-<w>.service`): WAL and a 5 s timeout (GN1), 503 `busy` on the page (GN3); the drill's step 14 is that path.
- **HM8's endpoint does not exist yet** — GN8 drops and keeps counts; Operator step 17 measures the drop line before HM8 and the row after; a changed URL or verb in HM8 as landed is a one-line option default (Assumption 33).
- **EV15 lands before GN8** by the published order; if Evidence stalls, GN8 stays `blocked` and waves 1–3 run regardless (GN9 waits).
- **GN10's lock may drift** if media's `main` moves between GN9's landing and GN10's launch — the seat's `nix flake lock` pins whatever `main` is then; the runbook's `media nixpkgs:` line and the check record it.
- **The `media` broker instance's `allow` is the probe's six hosts only** (Assumption 24): `media-fetch-models` on core would need its own widening — a later task, named in Not in this plan, never a silent edit to GN10's list (the check pins it by equality).
- **Switch #N's closure is large** (the ComfyUI/torch closure): Operator step 2's prediction names it so the diff-closures output is read, not feared; a `caddy` line there is a finding.
- **The landing act may not be lint-clean** (treefmt/statix over 97 files): a `GN13` `plan-append` before GN11 (Operator step 19), never a suffix.
- **`nixpkgs-host` may refuse the ComfyUI closure** (Assumption 25): GN12's Step 1 measures before any move and stops `failed` with the error; question 2(b) is the prepared fallback.
- **Name collisions on absorption**: `lint` → `media-lint` by rule, the `assert` refuses any other (GN12 M3).
- **Dispatch of a ledger-less sibling** (Assumption 36 i): the hand lines above; `factory-dispatch` for GN10–GN12 only.
- **Questions pre-asked:** the three above, each with a default; Assumptions 29–35 carry every other call with a veto surface. **Claims to close:** `aimdo-native-load-unmeasured` (Operator 23). **Switch deltas:** two, predicted (Operator 2, 20) and measured in GN10's and GN12's commit bodies. **Hooks, deny rules:** none added (A13, A14 do not fire). **Handoff line for the board (A11):** "generation: on the seat: <wave> (<keys>); in gate: <keys>; next: <the unblocked wave or the switch>; media main: `git -C ~/flakes/media log --oneline -1`".

## Not in this plan

- Helm's swipe view, the feed link or embed, and the `media-refresh` tile (WH2) — Helm (`HM`; 14c, 15a).
- The engagement kind and its validator (EV14, EV15), the `proposals` stream and `pkgs/evidence/SCHEMA.md` — Evidence (`EV`).
- The task-graph parser, the prefix guard, `--draft`, and `factory-dispatch` for ledger-less siblings — Evidence and Factory (Assumption 36).
- `factory-review`'s trailer comparison (the W6 false-MAJOR class) — Factory, closed by FIX7.
- The local inference stack and Phase 5 local weights — "no work scheduled until the mutator's model phase" (17c, charter).
- Network-namespace confinement of a world (design: out of scope); the driver-580 / CUDA 13 path stays the probe's to propose and the operator's to switch.
- The generation lab (`docs/concepts/2026-09-06a-generation-lab.md`, "brainstorm owed before a spec").
- The LAN face — Caddy, `tls internal`, `basic_auth`, the password files, the host names (question 3; Isolation's increment 4).
- Widening the `media` instance for `media-fetch-models` or `services.comfyui`'s `huggingface.co` injection (Assumption 24) — a later Generation task with its own `allow` and `inject` and an A3 item for the token.
- WH1 and WH2 as typed in media's plan — superseded (Assumption 30), left as history.
- The superseded `2026-09-02-media-flake.md` plan and media's own `docs/OPERATIONS.md` — frozen with the clone's history at absorption.
- The `seat-vm` eval red at HEAD (the board's HELD line) — Isolation/Seat; every check here is built by name.
- The Fable price row and `dsh-openrouter.sh` (FA11) the spec's cost note mentions — Factory.

## Tasks

Nine sections carry `**repo:** media` (their workspace is a clone of `~/flakes/media`; the plan file is this one); GN10–GN12 land here. Every section's Step 0 re-measures the facts it quotes (GN-A); every section's last step is the commit script (GN-F).

### GN1 (code, S) — the feed index: feed.sqlite rebuilt from the PNGs' own chunks, and the worlds' scripts packaged as one directory

**repo:** media
**dependsOn:** none
**touches:** `pkgs/comfy-worlds/feed_index.py`, `pkgs/comfy-worlds/default.nix`, `flake.nix`, `tests/comfy-worlds/conftest.py`, `tests/comfy-worlds/test_feed_index.py`
**acceptance:** comfy-worlds-unit, lint
**commit subject:** generation: the feed index rebuilds feed.sqlite from the PNGs' chunks and the worlds' scripts are one packaged directory (test: comfy-worlds-unit, lint)

**Why.** Sub-project 2's state is `<root>/worlds/<w>/feed.sqlite`, "index, rebuildable" (Assumption 32); nothing today reads a render's prompt or seed back out of the PNG, so no verb can regenerate or edit it. And every later module here (`job_queue.py`, `feed.py`, `mutate.py`) imports this one, which the wrappers as packaged cannot resolve — each is a single-file store path (Assumption 20, the r2 erratum 1). This task lands the module and the packaging rule first.

**Files.**
- Create `pkgs/comfy-worlds/feed_index.py` — `open_db`, `read_chunks`, `rebuild`, `newest`, `like`, `main` (Interfaces 1–5).
- Create `tests/comfy-worlds/conftest.py` — `write_png(path, prompt_graph, chunk="tEXt", mtime=None)`: writes a valid PNG — the signature `\x89PNG\r\n\x1a\n`, an `IHDR` for a 1×1 RGBA image, one text chunk `prompt` carrying `json.dumps(prompt_graph)` (as `tEXt`: keyword, `\0`, latin-1 text; as `iTXt`: keyword, `\0`, `\0` compression flag, `\0` method, `\0` language, `\0` translated keyword, utf-8 text), one `IDAT` (`zlib.compress(b"\x00\x00\x00\x00\xff")`), `IEND`; every chunk `struct.pack(">I", len) + type + data + struct.pack(">I", zlib.crc32(type + data) & 0xFFFFFFFF)`; `os.utime` to `mtime` when given. And the fixture `GRAPH`, inserted in this order: `"9": {"class_type": "KSampler", "inputs": {"seed": 99, "sampler_name": "euler", "positive": ["7", 0], "negative": ["8", 0]}}`, `"3": {"class_type": "KSampler", "inputs": {"seed": 42, "sampler_name": "euler", "positive": ["6", 0], "negative": ["8", 0]}}`, `"6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red fox"}}`, `"7": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red fox"}}`, `"8": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry"}}`, `"4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "x.safetensors"}}` — two samplers whose ids sort against their insertion order, two positive encoders with identical text, one negative with different text. GN2, GN4 and GN5 reuse it.
- Create `tests/comfy-worlds/test_feed_index.py` (Steps 1).
- Modify `pkgs/comfy-worlds/default.nix` — `worldsPy = pkgs.lib.fileset.toSource { root = ./.; fileset = pkgs.lib.fileset.fileFilter (f: f.hasExt "py") ./.; };` and every wrapper `exec ${pkgs.python3}/bin/python3 ${worldsPy}/<script>.py "$@"`; no `${./<x>.py}` interpolation remains; a new wrapper `comfy-feed-index` (`writeShellApplication`, `runtimeInputs = [ pkgs.python3 ]`, `text = ''exec ${pkgs.python3}/bin/python3 ${worldsPy}/feed_index.py "$@"''`) exported from the same attrset the other wrappers use.
- Modify `flake.nix` — in `comfy-worlds-unit`: the copy block copies `tests/comfy-worlds` as a directory (if it already does, no edit, said so in the commit body); after pytest, one line `env -i PATH=/nonexistent ${worldsPkgs.comfy-feed-index}/bin/comfy-feed-index --help >/dev/null` (the bare-PATH proof, GN-C).

**Interfaces.**
1. `open_db(path, timeout=5.0) -> sqlite3.Connection`: `sqlite3.connect(path, timeout=timeout)`, `PRAGMA journal_mode=WAL`, `row_factory = sqlite3.Row`; creates `renders(name TEXT PRIMARY KEY, mtime REAL NOT NULL, prompt TEXT NOT NULL DEFAULT '', seed INTEGER, graph TEXT NOT NULL DEFAULT '')` and `likes(name TEXT PRIMARY KEY, ts TEXT NOT NULL)` when absent. A parent directory that does not exist propagates `sqlite3.OperationalError: unable to open database file` — the world tree is `init.sh`'s to create, never this module's.
2. `read_chunks(png_path) -> (prompt_text, graph_json, seed)`: the file must start with the 8-byte PNG signature, else `ValueError("not a PNG: <path>")`; walks every chunk, collecting `tEXt` and `iTXt` (compressed `iTXt` inflated with `zlib.decompress`) whose keyword is `prompt`; `graph_json` is that chunk's text (`""` when absent); `seed` is `inputs.seed` of the KSampler-class node with the numerically lowest id (a node is KSampler-class when its `class_type` starts with `KSampler`), `None` when there is none or the chunk is absent or not JSON; `prompt_text` is `inputs.text` of the node named by that sampler's `inputs.positive[0]` when it is a `CLIPTextEncode`, else `""`. Every id comparison is numeric (`int(id)`); a non-numeric id sorts last.
3. `rebuild(conn, output_dir) -> int`: for every regular file directly under `output_dir` whose name ends `.png` (`os.scandir`, no recursion, sorted by name), upsert `renders` by `name` (`INSERT … ON CONFLICT(name) DO UPDATE SET mtime=excluded.mtime, prompt=…, seed=…, graph=…`) with `mtime = st_mtime`; a file `read_chunks` refuses gets a row with `prompt ''`, `graph ''`, `seed NULL`, never an exception; rows whose file is gone are deleted; returns `SELECT count(*) FROM renders`; `output_dir` absent → 0 and no exception; opens files read-only and writes nothing under `output_dir`.
4. `newest(conn, n=50) -> list[sqlite3.Row]`: `ORDER BY mtime DESC, name ASC LIMIT n`. `like(conn, name, ts) -> bool`: `INSERT OR IGNORE INTO likes` when `name` exists in `renders` (returns `True`), else returns `False` and writes nothing.
5. `main(argv)`: `rebuild --root R --world W` prints `rebuilt <n> rows` (exit 0), `newest --root R --world W [--n N]` prints one name per line; the world directory `R/worlds/W` absent → exit 2 and `feed-index: no such world dir: <path>` on stderr; the db is `R/worlds/W/feed.sqlite`, the output dir `R/worlds/W/output`.
6. Packaging: one store directory holds every `pkgs/comfy-worlds/*.py`; a script's `import feed_index` resolves because Python puts the script's own directory first on `sys.path`; `comfy-feed-index --help` on a bare `PATH` exits 0.

**Facts** (pasted at Step 0; the source of each is Assumption 20–22).
- `grep -n '\${\./' pkgs/comfy-worlds/default.nix` → the single-file interpolations (at least one line expected).
- `grep -n -B2 -A6 'cp -r' flake.nix` → the `comfy-worlds-unit` copy block.
- `ls tests/comfy-worlds/` → `test_feed_placeholder.py` among the entries.
- `grep -c class_type tests/acceptance/workflows/sdxl.json` → `7`; `grep -c '"KSampler"' tests/acceptance/workflows/sdxl.json` → `1`.
- `head -c 8 <any PNG under tests/ or the worlds tree> | od -c | head -1` when one exists, else skipped and said so — the signature `\211 P N G \r \n 032 \n`.

**Steps.**
0. Run the Facts commands; paste. A mismatch stops the task (GN-A).
1. **Red.** Write `conftest.py` and `test_feed_index.py` with these tests: `test_read_chunks_reads_prompt_graph_and_seed_from_text_chunk` (GRAPH as `tEXt` → `("a red fox", json.dumps(GRAPH), 42)`); `test_read_chunks_reads_itxt_chunk` (`chunk="iTXt"` → the same triple); `test_read_chunks_seed_from_lowest_id_ksampler` (`GRAPH` inserts `"9"` before `"3"`; seed must be 42); `test_read_chunks_refuses_non_png` (a file of `b"junk"` → `ValueError`); `test_read_chunks_without_prompt_chunk` (`write_png` with `prompt_graph=None` → `("", "", None)`); `test_rebuild_indexes_every_png_and_deletes_gone_rows` (three PNGs → 3; unlink one, rebuild → 2); `test_rebuild_missing_dir_returns_zero`; `test_rebuild_leaves_pngs_byte_identical_and_untouched` (sha256 and `st_mtime_ns` of each PNG equal before and after); `test_rebuild_tolerates_a_non_png` (`bad.png` holding `b"junk"` → a row with `prompt == ""`, no raise); `test_newest_orders_by_mtime_desc_then_name` (`b.png` then `a.png` written with the same `mtime=1000.0`, `c.png` with `2000.0` → names `["c.png", "a.png", "b.png"]`); `test_like_is_idempotent_and_refuses_unknown_name` (`like` twice → one row, `True`; an unknown name → `False`, no row); `test_open_db_sets_wal_and_timeout` (`PRAGMA journal_mode` → `wal`; a second connection holding `BEGIN IMMEDIATE`; `open_db(path, timeout=0.2).execute("INSERT INTO likes …")` raises `sqlite3.OperationalError` and the elapsed time is `< 1.0` s); `test_cli_rebuild_newest_and_missing_world` (`main([...rebuild...])` prints `rebuilt 3 rows`; `newest` prints the ordered names; a missing world dir → `SystemExit` with code 2 and the stderr line). `nix develop -c pytest tests/comfy-worlds/test_feed_index.py -q` → `ModuleNotFoundError: No module named 'feed_index'` on every test — paste the `N errors` line. Packaging red: `grep -c '\${\./[a-z_]*\.py}' pkgs/comfy-worlds/default.nix` → at least `1`; paste.
2. Write `feed_index.py`; rewrite `default.nix` as in Files; extend `flake.nix`.
3. **Green.** The Step-1 pytest → `13 passed`. `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` builds and its log carries the `comfy-feed-index --help` line's usage text; `nix build .#checks.x86_64-linux.lint -L --no-link` builds. `grep -c '\${\./[a-z_]*\.py}' pkgs/comfy-worlds/default.nix` → `0`. Paste all four.
4. **Mutants** (revert, run, restore; paste the red line of each):
   - **M1 seed-from-last** (`max` instead of `min` over sampler ids) → `test_read_chunks_seed_from_lowest_id_ksampler` fails (99).
   - **M1b seed-from-insertion-first** (take the first KSampler in dict order) → the same test fails (99, because `"9"` is inserted first).
   - **M2 ignore-iTXt** (collect `tEXt` only) → `test_read_chunks_reads_itxt_chunk` fails.
   - **M3 keep-gone-rows** (drop the delete) → `test_rebuild_indexes_every_png_and_deletes_gone_rows` fails (3 ≠ 2).
   - **M4 order-asc** → `test_newest_orders_by_mtime_desc_then_name` fails on `c.png`.
   - **M4b tiebreak-dropped** (`ORDER BY mtime DESC` alone) → the same test fails: with equal mtimes sqlite returns rowid order, and `b.png` was inserted before `a.png`.
   - **M5 png-touched** (`os.utime(path, None)` after reading) → the byte-identical test fails on `st_mtime_ns`.
   - **M6 raise-on-non-png** (let `ValueError` escape `rebuild`) → `test_rebuild_tolerates_a_non_png` fails.
   - **M7 timeout-dropped** (`sqlite3.connect(path)` without `timeout`) → `test_open_db_sets_wal_and_timeout` fails on the elapsed bound (sqlite's default is 5 s).
   - **M8 single-file-interpolation** (revert `default.nix`'s `worldsPy`) → the probe `no-single-file-interp` reads 1; the executable killer is GN3's `comfy-feed --help` through `feed.py`'s `import feed_index` — named here, landed there.
   - **Negative control** — `tests/comfy-worlds/test_feed_placeholder.py` passes before and after; make the placeholder's `/out/<name>` guard accept `..` → its basename test fails; restore. Proves the copied test tree runs in the sandbox.
5. **Commit.** `msg=$(mktemp); { printf '%s\n\n' 'generation: the feed index rebuilds feed.sqlite from the PNGs'"'"' chunks and the worlds'"'"' scripts are one packaged directory (test: comfy-worlds-unit, lint)'; for c in "nix develop -c pytest tests/comfy-worlds/test_feed_index.py -q 2>&1 | tail -n 3" "grep -c '\${\./[a-z_]*\.py}' pkgs/comfy-worlds/default.nix; true" "grep -n -A6 'cp -r' flake.nix" "grep -c class_type tests/acceptance/workflows/sdxl.json"; do printf '$ %s\n' "$c"; bash -c "$c" 2>&1 | head -n 40; printf '\n'; done; } > "$msg"` — then append the WORKSPACE RULES block's two trailer lines to `$msg` and `nix develop -c git commit -F "$msg"`. The subject line above is the commit subject byte for byte.

**Tests (assertion → mutant; fixture → discriminating row):** lowest-id sampler → M1, M1b (fixture: `"9"` inserted before `"3"`); both chunk types → M2; gone rows deleted → M3; order → M4, M4b (fixture: equal mtimes, `b` before `a`); PNGs untouched → M5; non-PNG tolerated → M6; timeout and WAL → M7; one packaged directory → M8 (probe) and GN3; sandbox runs the copied tests → negative control.

**probes:**
- feed-index-module: `test -f pkgs/comfy-worlds/feed_index.py && echo 1 || echo 0` :: ge 1 :: this task
- no-single-file-interp: `grep -c '\${\./[a-z_]*\.py}' pkgs/comfy-worlds/default.nix; true` :: le 0 :: Assumption 20, at least one line before this task
- wal-mode: `nix develop -c python3 -c "import sys,tempfile,os; sys.path.insert(0,'pkgs/comfy-worlds'); import feed_index; d=tempfile.mkdtemp(); c=feed_index.open_db(os.path.join(d,'f.sqlite')); print(c.execute('pragma journal_mode').fetchone()[0])"` :: eq wal :: Interfaces 1
- tests-copied: `grep -c 'tests/comfy-worlds' flake.nix` :: ge 1 :: Assumption 21, the copy block names the directory

### GN2 (code, S) — the job queue: enqueue with a seed, submit to ComfyUI, poll, never raise on the network

**repo:** media
**dependsOn:** GN1
**touches:** `pkgs/comfy-worlds/job_queue.py`, `tests/comfy-worlds/test_job_queue.py`
**acceptance:** comfy-worlds-unit, lint
**commit subject:** generation: the job queue enqueues a graph with a seed, submits it to ComfyUI and polls it without raising on the network (test: comfy-worlds-unit, lint)

**Why.** The design scopes "the job queue" as sub-project 2's first piece (spec §5 Q5); regenerate, edit and mutate are all one verb underneath — put a graph with a seed into the world's ComfyUI at `http://127.0.0.1:<comfyPort>/prompt` and read `/history` back. The module is named `job_queue.py` because `queue.py` would silently bind the stdlib module under a bare import (r2 erratum 2). Its error contract is enumerated to the last arm (r2 errata 5, 7, 8; 2026-09-12 errata 5, 11).

**Files.**
- Create `pkgs/comfy-worlds/job_queue.py` — `ensure_schema`, `enqueue`, `submit`, `poll`, `run_once` (Interfaces 1–5); imports `feed_index` (GN1's packaging).
- Create `tests/comfy-worlds/test_job_queue.py` — with a fake ComfyUI: `http.server.ThreadingHTTPServer` on `("127.0.0.1", 0)` in a daemon thread, whose handler answers `POST /prompt` and `GET /history/<id>` from two per-test tables (`fake.prompt_reply = (status, body)`, `fake.history[id] = body`), records every request body in `fake.seen`, and is closed in a fixture finaliser (the thread-start helper is written out in this file, not borrowed).

**Interfaces.**
1. `ensure_schema(conn)`: `jobs(id INTEGER PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('regenerate','edit','mutate')), source TEXT NOT NULL, graph TEXT NOT NULL, seed INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('queued','submitted','done','failed')), comfy_id TEXT, error TEXT NOT NULL DEFAULT '', created TEXT NOT NULL, updated TEXT NOT NULL)`; idempotent.
2. `enqueue(conn, kind, source, graph, seed) -> int`: `graph` is a dict of the Assumption-22 shape; sets `inputs.seed = seed` on every KSampler-class node (`class_type` starts with `KSampler`); no such node → `ValueError("no KSampler node in graph")` and no row; a `kind` outside the enum → `sqlite3.IntegrityError` from the CHECK (propagated); stores `json.dumps(graph, sort_keys=True)`, state `queued`; returns the row id.
3. `submit(conn, job_id, comfy_url) -> str`: `comfy_url`'s host must be `127.0.0.1` or `localhost`, else `ValueError("queue: ComfyUI is loopback-only: <url>")` before any socket (GN-G); POSTs `{"prompt": graph, "client_id": "comfy-feed"}` to `<comfy_url>/prompt` with `urllib.request` and a 10 s timeout. Arms: (a) `URLError`, `ConnectionError`, `TimeoutError`, or `HTTPError` with status ≥ 500 → the job stays `queued`, `error` = the exception's class name and text, returns `"queued"`; (b) `HTTPError` with status 400–499 → `failed`, `error` = the body's first 200 characters, returns `"failed"`; (c) 200 whose body is not JSON or has no `prompt_id` → `failed`, `error` = `invalid JSON from ComfyUI: <body[:200]>`, returns `"failed"`; (d) 200 with `prompt_id` → `submitted`, `comfy_id` set, returns `"submitted"`. `updated` is set on every arm.
4. `poll(conn, comfy_url) -> int`: for every `submitted` job in id order, GET `<comfy_url>/history/<comfy_id>`: a JSON object containing the id → `done`; an empty object → unchanged; a network arm as in 3(a) → that job unchanged and **the remaining jobs are still polled**; a body that is not JSON, or raises `RecursionError` while parsing → that job `failed`, `error` = the exception text. Returns the number of jobs that became `done` in this call.
5. `run_once(conn, comfy_url) -> tuple[int, int]`: `submit` every `queued` job in id order, then `poll`; returns `(submitted, done)`; never raises for a network condition (the loopback `ValueError` is the one exception it lets through — a configuration error, not a network one). Bodies above 1 MiB from `/history` are read to the cap and treated as arm 4's non-JSON.

**Facts** (Step 0): `ls pkgs/comfy-worlds/feed_index.py` (GN1 landed); `grep -n 'worldsPy' pkgs/comfy-worlds/default.nix` → the directory derivation; `python3 -c "import queue; print(queue.__file__)"` → the stdlib path (why the module is not named `queue`).

**Steps.**
1. **Red.** Write the fake and these tests: `test_enqueue_sets_seed_on_every_ksampler` (GRAPH → both `"3"` and `"9"` carry seed 7); `test_enqueue_refuses_graph_without_sampler` (`ValueError`, no row); `test_enqueue_refuses_unknown_kind` (`"bogus"` → `sqlite3.IntegrityError`); `test_submit_refuses_non_loopback` (`http://10.0.0.1:8188` → `ValueError`, `fake.seen == []`); `test_submit_marks_submitted_on_prompt_id` (200 `{"prompt_id": "abc"}` → `submitted`, `comfy_id == "abc"`, the POSTed body carries the seeded graph); `test_submit_4xx_marks_failed` (400 body `bad prompt` → `failed`, `error == "bad prompt"`); `test_submit_5xx_leaves_queued` (503 → `queued`, `error` names `HTTPError`); `test_submit_unreachable_leaves_job_queued` (a closed port → `queued`); `test_submit_non_json_200_marks_failed` (200 body `<html>` → `failed`, `error` starts `invalid JSON from ComfyUI:`); `test_poll_marks_done_when_history_has_id` (`fake.history["abc"] = {"abc": {"outputs": {}}}` → `done`, returns 1); `test_poll_leaves_submitted_when_history_empty` (`{}` → unchanged, returns 0); `test_poll_continues_after_unreachable` (two `submitted` jobs; the fake fails the first request with a 503 and answers the second with its id → the second is `done`, returns 1); `test_poll_malformed_history_marks_failed` (body `not json` → `failed`); `test_run_once_submits_then_polls_and_never_raises` (two queued jobs, the fake down → returns `(0, 0)`, both `queued`, no exception). `nix develop -c pytest tests/comfy-worlds/test_job_queue.py -q` → `ModuleNotFoundError: No module named 'job_queue'`; paste the count.
2. Write `job_queue.py`.
3. **Green.** `14 passed`; `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` and `… lint …` build; paste.
4. **Mutants** (revert, run, restore):
   - **M1 seed-first-only** (set the seed on the first sampler) → `test_enqueue_sets_seed_on_every_ksampler` fails on `"3"` (the fixture inserts `"9"` first, so "first" is the wrong one either way).
   - **M2 no-sampler-tolerated** (return a row anyway) → the `ValueError` test fails.
   - **M3 check-dropped** (no `CHECK(kind IN …)`) → `test_enqueue_refuses_unknown_kind` fails (row written).
   - **M4 loopback-rule-dropped** → `test_submit_refuses_non_loopback` fails (a request is attempted).
   - **M5 4xx-as-unreachable** (fold `HTTPError < 500` into arm (a)) → `test_submit_4xx_marks_failed` fails (`queued`).
   - **M6 json-error-escapes** (no `try` around `json.loads`) → `test_submit_non_json_200_marks_failed` fails (`JSONDecodeError` raised).
   - **M7 poll-aborts** (`return` on the first unreachable job) → `test_poll_continues_after_unreachable` fails (second job still `submitted`).
   - **M8 run-once-raises** (let `URLError` escape `run_once`) → `test_run_once_submits_then_polls_and_never_raises` fails.
   - **Negative control — the fake is not blind:** `test_submit_marks_submitted_on_prompt_id` asserts the POSTed body's `"3"` carries seed 7; set `fake.prompt_reply` to answer 200 for every body and drop the body assertion → a `submit` that posts `{}` passes; restore. Proves the body assertion is what discriminates.
5. **Commit.** As GN1's script, subject `generation: the job queue enqueues a graph with a seed, submits it to ComfyUI and polls it without raising on the network (test: comfy-worlds-unit, lint)`, commands: `nix develop -c pytest tests/comfy-worlds/test_job_queue.py -q 2>&1 | tail -n 3`, `grep -c 'CHECK(kind IN' pkgs/comfy-worlds/job_queue.py`, `grep -c 'loopback-only' pkgs/comfy-worlds/job_queue.py`; then the trailers; `nix develop -c git commit -F "$msg"`.

**Tests (assertion → mutant; fixture → discriminating row):** every sampler seeded → M1 (fixture: two samplers, `"9"` first); no sampler refused → M2; kind enum → M3 (fixture: `bogus`); loopback → M4; 4xx arm → M5 (fixture: 400 with a body); non-JSON 200 → M6; poll continues → M7 (fixture: two submitted jobs, the first failing); run_once never raises → M8; the fake discriminates → negative control.

**probes:**
- job-queue-module: `test -f pkgs/comfy-worlds/job_queue.py && echo 1 || echo 0` :: ge 1 :: this task
- no-stdlib-shadow: `test -e pkgs/comfy-worlds/queue.py && echo 1 || echo 0` :: le 0 :: r2 erratum 2
- kind-check: `grep -c "CHECK(kind IN ('regenerate','edit','mutate'))" pkgs/comfy-worlds/job_queue.py` :: ge 1 :: Interfaces 1
- four-arms: `grep -c 'invalid JSON from ComfyUI' pkgs/comfy-worlds/job_queue.py` :: ge 1 :: Interfaces 3 arm c

### GN3 (code, M) — the feed replaces the placeholder: a vertical page of the newest renders, forms only, zero outbound

**repo:** media
**dependsOn:** GN1
**touches:** `pkgs/comfy-worlds/feed.py`, `pkgs/comfy-worlds/feed_placeholder.py`, `pkgs/comfy-worlds/default.nix`, `nixosModules/comfyui-worlds.nix`, `tests/comfy-worlds/test_feed.py`, `tests/comfy-worlds/test_feed_placeholder.py`
**acceptance:** comfy-worlds-unit, comfy-worlds-eval, lint
**commit subject:** generation: the feed replaces the placeholder with a vertical page of the newest renders, forms only, zero outbound (test: comfy-worlds-unit, comfy-worlds-eval, lint)

**Why.** `feed_placeholder.py` is "a stdlib-only `http.server` that fronts the world's output directory while the real feed (sub-project 2) does not exist yet" (spec §2); decision 15a plans sub-project 2 as specified, and 14c makes this page "the feed component Helm reaches". The page is the surface the verbs of GN4 hang on, so it lands with the index (GN1) and before them. Its one invariant is Helm's (Assumption 34), restated as a rule over every attribute value, not a list of three spellings (the 2026-09-14 erratum 22).

**Files.**
- Create `pkgs/comfy-worlds/feed.py` — `build_server(world, root, port, comfy_url, n=50) -> ThreadingHTTPServer`, `render_page(world, rows, likes) -> str`, `check_html(text) -> list[str]`, `main(argv)`; imports `feed_index`.
- Delete `pkgs/comfy-worlds/feed_placeholder.py`; move its two guard tests from `tests/comfy-worlds/test_feed_placeholder.py` into `tests/comfy-worlds/test_feed.py` as `test_out_refuses_traversal` and `test_out_serves_basename_only` (their replacement, named here) and delete the old file.
- Modify `pkgs/comfy-worlds/default.nix` — the `comfy-feed` wrapper execs `${worldsPy}/feed.py` (GN1's directory); its `runtimeInputs` carry `pkgs.python3` only.
- Modify `nixosModules/comfyui-worlds.nix` — the per-world feed unit's `ExecStart` becomes `<comfy-feed> --world <w> --root <root> --port <feedPort> --comfy-url http://127.0.0.1:<comfyPort>`; `ReadWritePaths` carries `<root>/worlds/<w>` (feed.sqlite lives there); nothing else in the unit changes.
- Create `tests/comfy-worlds/test_feed.py`.

**Interfaces.**
1. CLI: `comfy-feed --world W --root R --port P [--comfy-url U] [--n N]`; `--port` binds `127.0.0.1` only; `U` defaults to `http://127.0.0.1:8188` and is refused unless loopback (`ValueError`, exit 2, GN-G); on start the server runs `feed_index.rebuild` over `R/worlds/W/output` and logs `feed: <world>: <n> renders indexed` to stderr; `R/worlds/W` absent → exit 2, `feed: no such world dir: <path>`.
2. `GET /` → 200 `text/html; charset=utf-8`: `<!doctype html><html><head><meta charset="utf-8"><title>… </title></head><body><main>` then one `<article>` per row of `feed_index.newest(conn, n)`, newest first, each with `<img src="/out/<name>" alt="">`, `<p>` the prompt through `html.escape`, and three forms (`POST /like`, `POST /regenerate`, `POST /edit` — GN4 wires the handlers; GN3 renders the forms and answers those routes 501 until GN4), and a liked marker `<p>liked</p>` when `likes` has the name. No render → `<p>no renders yet</p>`.
3. `GET /out/<name>` → the file `R/worlds/W/output/<name>` as `image/png` when `name` has no `/`, is not `..`, and exists; 404 otherwise (the placeholder's guard, kept). `GET /healthz` → `ok <world>`. `GET /jobs` → 200 `application/json`, the `jobs` rows as a list (empty until GN2's queue has rows; GN3 selects from the table when it exists and `[]` when it does not). Any other path → 404; any method other than GET on these paths → 405.
4. Every response carries `Cache-Control: no-store`; every handler catches `sqlite3.OperationalError` (database locked past the timeout) and answers 503 with `busy` — never 500 (r2 erratum 12).
5. **Zero outbound, as a rule.** `check_html(text)` parses the page with `html.parser.HTMLParser` and returns one string per violation: a tag outside the closed set `{html, head, meta, title, body, main, article, img, p, form, input, button, textarea, label}`; an attribute whose name starts with `on`; a `meta` with any attribute other than `charset`; any attribute value that matches `^[A-Za-z][A-Za-z0-9+.-]*:` (a scheme) or starts with `//`; a `form` whose `action` is not a path starting with `/` or whose `method` is not `post`. `render_page`'s output passes with `[]`, and the test asserts it on a page with real rows.

**Facts** (Step 0): `grep -n 'feed_placeholder\|comfy-feed' pkgs/comfy-worlds/default.nix nixosModules/comfyui-worlds.nix` → the wrapper and the unit's `ExecStart`; `grep -n 'ProtectSystem\|ReadWritePaths' nixosModules/comfyui-worlds.nix` (Assumption 19); `grep -n 'def test' tests/comfy-worlds/test_feed_placeholder.py` → the two guard tests to move; `grep -n 'no <script\|src=' pkgs/helm/serve.py` is this repo's rule (Assumption 34) — not in the media workspace, quoted here for the seat: "the page composes no <script, no src=, no href="http".

**Steps.**
1. **Red.** Write `test_feed.py`: the two moved guard tests; `test_healthz_names_the_world` (`ok sfw`); `test_index_lists_newest_first_with_forms` (three PNGs via `write_png`, one liked → three `<article>`, order by mtime, `liked` on the right one, three forms per article); `test_page_passes_check_html`; `test_check_html_refuses_script_tag`, `test_check_html_refuses_formaction_url` (`<button formaction="https://x">`), `test_check_html_refuses_meta_refresh` (`<meta http-equiv="refresh" content="0;url=//x">`), `test_check_html_refuses_on_handler` (`<img onerror="…">`), `test_check_html_refuses_protocol_relative` (`src="//x/y.png"`), `test_check_html_refuses_data_uri` (`src="data:…"`); `test_post_on_get_route_is_405`; `test_locked_db_answers_503` (a second connection holds `BEGIN IMMEDIATE`; `GET /` on a server built with `timeout=0.2` → 503 `busy`); `test_jobs_is_empty_list_without_table`; `test_non_loopback_comfy_url_refused` (`build_server(..., comfy_url="http://10.0.0.1:1")` → `ValueError`). `nix develop -c pytest tests/comfy-worlds/test_feed.py -q` → `ModuleNotFoundError: No module named 'feed'`; paste the count. Then the placeholder's POST red for the record: `python3 -c "…urllib POST to the placeholder…"` → `HTTP Error 501: Unsupported method ('POST')` (Assumption 21), pasted.
2. Write `feed.py`; delete the placeholder; repoint the wrapper and the unit.
3. **Green.** pytest → `16 passed`; `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` (its log shows `comfy-feed-index --help` from GN1 and now `comfy-feed --help` — add that line beside GN1's in `flake.nix` only if the copy block did not already run every wrapper; if a `flake.nix` edit is needed, disclose it with a `Deviation:` line, since `flake.nix` is not in this task's `touches`), `… comfy-worlds-eval …` (the unit's `ExecStart` assertion, whatever it asserts today, still holds — the seat pastes the eval's own output), `… lint …`; `ls pkgs/comfy-worlds/feed_placeholder.py` → `No such file`. Paste.
4. **Mutants** (revert, run, restore):
   - **M1 order-oldest-first** → `test_index_lists_newest_first_with_forms` fails.
   - **M2 forms-dropped** → the same test fails on the form count.
   - **M3a script-tag**, **M3b formaction-url**, **M3c meta-refresh**, **M3d on-handler**, **M3e protocol-relative**, **M3f data-uri** — each an added element or attribute in `render_page` → `test_page_passes_check_html` fails, and the matching `test_check_html_refuses_*` fails when the corresponding rule is deleted from `check_html`.
   - **M4 traversal-allowed** (drop the `..` refusal) → `test_out_refuses_traversal` fails.
   - **M5 500-on-lock** (drop the `OperationalError` catch) → `test_locked_db_answers_503` fails (500).
   - **M6 loopback-dropped** → `test_non_loopback_comfy_url_refused` fails.
   - **Negative control — `test_check_html_refuses_script_tag`** fails when `check_html` is replaced by `return []`; restore. The rule-checker is itself under test, not only the page.
5. **Commit.** As GN1's script; subject `generation: the feed replaces the placeholder with a vertical page of the newest renders, forms only, zero outbound (test: comfy-worlds-unit, comfy-worlds-eval, lint)`; commands: `nix develop -c pytest tests/comfy-worlds/test_feed.py -q 2>&1 | tail -n 3`, `ls pkgs/comfy-worlds/feed_placeholder.py 2>&1`, `grep -n 'comfy-feed' nixosModules/comfyui-worlds.nix`, `grep -c 'def check_html' pkgs/comfy-worlds/feed.py`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** newest first → M1 (fixture: three mtimes); forms present → M2; zero outbound as a rule → M3a–M3f (one payload per rule, each outside the old three-spelling list); basename guard kept → M4 (the moved tests); locked db → M5 (fixture: a held write lock); loopback → M6; the checker discriminates → negative control.

**probes:**
- placeholder-gone: `test -e pkgs/comfy-worlds/feed_placeholder.py && echo 1 || echo 0` :: le 0 :: spec section 2, the placeholder retired
- feed-module: `test -f pkgs/comfy-worlds/feed.py && echo 1 || echo 0` :: ge 1 :: this task
- html-rule: `grep -c 'def check_html' pkgs/comfy-worlds/feed.py` :: ge 1 :: Interfaces 5
- no-script-anywhere: `grep -c -i '<script' pkgs/comfy-worlds/feed.py; true` :: le 0 :: Assumption 34

### GN4 (code, S) — the three verbs: like, regenerate with a new seed, edit the prompt — each a form POST into the queue

**repo:** media
**dependsOn:** GN2, GN3
**touches:** `pkgs/comfy-worlds/feed.py`, `tests/comfy-worlds/test_feed.py`
**acceptance:** comfy-worlds-unit, lint
**commit subject:** generation: the feed's three verbs — like, regenerate with a new seed, edit the prompt — each a form POST into the queue (test: comfy-worlds-unit, lint)

**Why.** Design 15a's sub-project 2 is "the feed app (vertical feed, like, regenerate with a new seed, edit prompt)" (spec §5 Q5); GN3 rendered the forms and answers them 501; this task wires them to GN1's index and GN2's queue, and starts the worker that drains the queue into ComfyUI. The edit rule is over every matching node, with the negative-prompt node as the fixture that catches "replace everything" (r2 erratum 4); every POST has a body bound (r2 erratum 13).

**Files.**
- Modify `pkgs/comfy-worlds/feed.py` — the three POST handlers, `read_form(handler) -> dict`, `new_seed`, the worker thread in `build_server` (Interfaces 1–6); `build_server` gains `seed_fn=None` and `poll_interval=5.0`.
- Modify `tests/comfy-worlds/test_feed.py` — the tests of Step 1 (the fake ComfyUI is `test_job_queue.py`'s; import it from there: `from test_job_queue import FakeComfy` — both files sit in the copied `tests/comfy-worlds`).

**Interfaces.**
1. `POST /like` with form field `name`: `feed_index.like(conn, name, ts)` (`ts` = UTC RFC3339 `Z`); `True` → 303 `Location: /`; `False` → 404 `unknown render`; `name` empty or absent → 400 `name required`.
2. `POST /regenerate` with `name`: the render's `graph` from `renders`; `""` → 409 `no graph for <name>`; else `job_queue.enqueue(conn, "regenerate", name, json.loads(graph), new_seed())` → 303 `/`. `new_seed()` is `seed_fn()` when `build_server` was given one, else `secrets.randbelow(2**32)` — the default branch is under test (Step 1).
3. `POST /edit` with `name` and `prompt`: `prompt` empty → 400; the render's stored `prompt` (GN1 Interfaces 2) is `p`; in the render's graph replace `inputs.text` on **every** `CLIPTextEncode` node whose current `inputs.text == p` with the new text; zero nodes matched → 409 `prompt not found in graph`; else `enqueue(conn, "edit", name, graph2, new_seed())` → 303. Nodes whose text differs from `p` (the negative prompt) are never touched.
4. Body bound for every POST: `Content-Length` absent or not an integer → 411; above 65536 → 413 `body too large` and the body is not read; the body is `urllib.parse.parse_qs(body.decode("utf-8", "replace"))`, first value per field; a POST to a path other than the three → 404; a GET on the three → 405.
5. The worker: `threading.Thread(target=loop, daemon=True, name="comfy-feed-worker")` started by `build_server` when `poll_interval > 0`; `loop` opens its own connection with `feed_index.open_db`, and every `poll_interval` seconds calls `job_queue.run_once(conn, comfy_url)` inside `try/except Exception` that logs `feed: worker: <exc>` to stderr and continues — the thread never dies on an exception. `poll_interval=0` starts no thread (tests call `run_once` themselves).
6. `GET /jobs` → the `jobs` rows (`id, kind, source, seed, state, comfy_id, error, created, updated`) as a JSON list, newest first.

**Facts** (Step 0): `grep -n "501\|def do_POST\|def do_GET" pkgs/comfy-worlds/feed.py` → GN3's routes; `grep -n 'def enqueue\|def run_once' pkgs/comfy-worlds/job_queue.py` → GN2's signatures; `grep -n 'class FakeComfy' tests/comfy-worlds/test_job_queue.py`.

**Steps.**
1. **Red.** Add to `test_feed.py`: `test_like_writes_a_row_and_redirects` (303; `SELECT count(*) FROM likes` → 1; twice → still 1); `test_like_unknown_name_404`; `test_like_missing_name_400`; `test_regenerate_enqueues_with_fresh_seed` (render written from `GRAPH` with stored seed 42; `seed_fn=lambda: 777` → one `jobs` row, `kind regenerate`, both samplers in its `graph` carry 777, `state queued`); `test_regenerate_without_graph_409` (a render whose `graph` is `""`); `test_edit_replaces_prompt_text_and_enqueues` (`prompt=a blue fox` → the job's graph has `"6"` and `"7"` text `a blue fox` and `"8"` still `blurry`; `kind edit`); `test_edit_prompt_not_in_graph_409` (a render whose stored `prompt` is `zzz` — no node carries it); `test_edit_empty_prompt_400`; `test_post_body_over_cap_413` (`Content-Length: 70000`, the body never sent — the server answers before reading; the client's `send` of 70000 bytes may raise `BrokenPipeError`, which the test tolerates); `test_post_without_content_length_411`; `test_default_seed_fn_is_random_in_range` (`build_server` without `seed_fn`; three regenerates → three seeds, all `< 2**32`, not all equal); `test_worker_drains_the_queue` (`poll_interval=0.05`, `FakeComfy` answering `{"prompt_id": "j1"}`; after `time.sleep(0.5)` the job is `submitted`); `test_worker_survives_an_exception` (the fake's handler raises for the first request, then answers; after 0.5 s the job is still `submitted` and the thread `is_alive()`); `test_jobs_lists_rows_newest_first`. `nix develop -c pytest tests/comfy-worlds/test_feed.py -q` → the 13 new tests fail (501 answers, missing handlers); paste the count line.
2. Implement Interfaces 1–6.
3. **Green.** pytest → all pass (GN3's 16 + 13 = `29 passed`); `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` and `… lint …` build; paste.
4. **Mutants** (revert, run, restore):
   - **M1 like-without-check** (write the row whatever the name) → `test_like_unknown_name_404` fails.
   - **M2 regenerate-keeps-seed** (reuse the stored 42) → `test_regenerate_enqueues_with_fresh_seed` fails (42 ≠ 777).
   - **M3a edit-first-only** (replace the first matching node) → the edit test fails on `"7"`.
   - **M3c match-check-dropped** (replace every `CLIPTextEncode`) → the edit test fails on `"8"` (`blurry` overwritten) — the fixture's negative node is the discriminator.
   - **M4 cap-dropped** → `test_post_body_over_cap_413` fails (the body is read; 303 or 400).
   - **M5 constant-default-seed** (`new_seed` returns 1 without `seed_fn`) → `test_default_seed_fn_is_random_in_range` fails (all equal).
   - **M6 worker-not-started** → `test_worker_drains_the_queue` fails (`queued`).
   - **M7 worker-dies-on-exception** (no `try/except` in `loop`) → `test_worker_survives_an_exception` fails (`is_alive()` false, or `queued`).
   - **Negative control** — in `test_worker_drains_the_queue` set the fake to answer 503 → the job stays `queued` and the test fails; restore. The worker's state change comes from the fake's answer, not from time passing.
5. **Commit.** As GN1's script; subject `generation: the feed's three verbs — like, regenerate with a new seed, edit the prompt — each a form POST into the queue (test: comfy-worlds-unit, lint)`; commands: `nix develop -c pytest tests/comfy-worlds/test_feed.py -q 2>&1 | tail -n 3`, `grep -c '65536' pkgs/comfy-worlds/feed.py`, `grep -n 'CLIPTextEncode' pkgs/comfy-worlds/feed.py`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** like is checked and idempotent → M1 (fixture: an unknown name; the same name twice); fresh seed → M2 (fixture: stored 42, injected 777); every matching encoder, no other → M3a, M3c (fixture: two positives with identical text, one negative); body bound → M4 (fixture: 70000 bytes); default seed branch → M5; worker runs → M6; worker survives → M7 (fixture: a handler that raises once); the fake discriminates → negative control.

**probes:**
- verbs-present: `grep -c "'/like'\|'/regenerate'\|'/edit'" pkgs/comfy-worlds/feed.py` :: ge 3 :: Interfaces 1 to 3
- body-cap: `grep -c '65536' pkgs/comfy-worlds/feed.py` :: ge 1 :: Interfaces 4
- edit-rule-every-node: `grep -c 'CLIPTextEncode' pkgs/comfy-worlds/feed.py` :: ge 1 :: Interfaces 3
- worker-thread: `grep -c 'comfy-feed-worker' pkgs/comfy-worlds/feed.py` :: ge 1 :: Interfaces 5

### GN5 (code, S) — the rules mutator: a mutation grammar read from the lab's manifest, applied to a graph, deterministic under a seed

**repo:** media
**dependsOn:** GN1
**touches:** `pkgs/comfy-worlds/mutate.py`, `tests/comfy-worlds/test_mutate.py`
**acceptance:** comfy-worlds-unit, lint
**commit subject:** generation: the rules mutator — a mutation grammar read from the lab manifest, applied to every matching node, deterministic under a seed (test: comfy-worlds-unit, lint)

**Why.** Decision 17c: "rules now; the local model as its own phase". The loose-ends question framed the rules as "a mutation grammar over the world's lab repo (token swaps, LoRA strengths, samplers, seeds)" (spec §5 Q4), and the lab is `<root>/worlds/<w>/lab/` with its `manifest.toml` (spec §1, Assumption 31). This task is the library: read the grammar, apply it to a graph, every matching node, a category that can never fire is an error rather than a silent skip (r2 Judge 1 row 7). GN6 wraps it as the world-aware command and unit.

**Files.**
- Create `pkgs/comfy-worlds/mutate.py` — `RuleNeverFires(Exception)`, `load_rules`, `mutate`, `is_sampler`, `is_lora` (Interfaces 1–3); imports nothing from the siblings (GN6's CLI imports `feed_index` and `job_queue`).
- Create `tests/comfy-worlds/test_mutate.py` — uses `conftest.GRAPH` plus a `LoraLoader` node `"10": {"class_type": "LoraLoader", "inputs": {"strength_model": 1.0, "strength_clip": 1.0}}` added in the test.

**Interfaces.**
1. `load_rules(manifest_path) -> dict`: `tomllib.load`; the `[mutate]` table's keys — `tokens` (a list of `[from, to]` two-element string lists), `lora_strengths` (a list of floats), `samplers` (a list of strings), `seeds` (the string `"random"` or a list of ints); a key absent → `[]`; the table absent → `ValueError("mutate: no [mutate] table in <path>")`; the file absent → `FileNotFoundError` (propagated); a `tokens` entry that is not a two-string list → `ValueError("mutate: tokens entries are [from, to] pairs")`.
2. `mutate(graph, rules, rng) -> (graph2, applied)`: `graph2 = copy.deepcopy(graph)`; categories in this fixed order, each choosing one value with `rng.choice` (or `rng.randrange(2**32)` for `seeds == "random"`): **tokens** — for every `CLIPTextEncode` node, split `inputs.text` with `re.split(r"[,\s]+", text)`, replace every token equal to `from` with `to` (whole token, case-sensitive), rejoin with single spaces; **lora_strengths** — every node whose `class_type` starts with `LoraLoader` gets `inputs.strength_model` and `inputs.strength_clip` set to the value; **samplers** — every KSampler-class node gets `inputs.sampler_name`; **seeds** — every KSampler-class node gets `inputs.seed`. A category whose rule list is empty is skipped and absent from `applied`. A category with a non-empty list that changed no node (no encoder carried the token; no LoraLoader node; no KSampler node) raises `RuleNeverFires(category)`. `applied` is `["tokens=red->blue", "samplers=euler", …]` in order. The input graph is never modified.
3. `is_sampler(node)` ⇔ `node["class_type"].startswith("KSampler")`; `is_lora(node)` ⇔ `startswith("LoraLoader")` — the one definition GN1, GN2, GN4 and GN6 share by text.

**Facts** (Step 0): `grep -n 'manifest.toml\|lab' pkgs/comfy-worlds/init.sh` → where `init.sh` creates the lab and its manifest (spec §1: "holding `prompts/`, `manifest.toml` and the ComfyUI `user` dir"); `python3 -c "import tomllib"` → the stdlib parser is present in the devShell's python.

**Steps.**
1. **Red.** Write the tests: `test_load_rules_reads_every_key`; `test_missing_table_refused` (`ValueError`); `test_missing_file_raises` (`FileNotFoundError`); `test_bad_token_pair_refused`; `test_token_swap_every_encoder_whole_token` (`tokens=[["red","blue"]]`; a fourth encoder `"11"` with text `reddish fox, red` → `"6"`, `"7"` → `a blue fox`; `"11"` → `reddish fox blue`; `"8"` unchanged); `test_sampler_set_on_every_ksampler` (`"3"` and `"9"`); `test_lora_strength_set_on_every_loraloader`; `test_seed_random_from_rng_on_every_ksampler` (`random.Random(1)` → both samplers equal and equal to a second run's); `test_seed_list_choice`; `test_rule_never_fires_on_absent_token` (`[["zebra","x"]]` → `RuleNeverFires` whose `args[0] == "tokens"`); `test_rule_never_fires_on_graph_without_sampler`; `test_empty_category_skipped` (all lists empty → `graph2 == graph`, `applied == []`); `test_deterministic_under_seed` (two calls with `random.Random(5)` → equal `(graph2, applied)`); `test_input_graph_not_mutated_in_place`. `nix develop -c pytest tests/comfy-worlds/test_mutate.py -q` → `ModuleNotFoundError: No module named 'mutate'`; paste the count.
2. Write `mutate.py`.
3. **Green.** `14 passed`; `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` and `… lint …` build; paste.
4. **Mutants** (revert, run, restore):
   - **M1 tokens-first-encoder-only** → the whole-token test fails on `"7"`.
   - **M2 substring-swap** (`text.replace(frm, to)`) → the same test fails on `"11"` (`blueish`).
   - **M3 sampler-first-only** → `test_sampler_set_on_every_ksampler` fails on `"3"`.
   - **M4 rng-bypassed** (`random.randrange` instead of `rng.randrange`) → `test_deterministic_under_seed` fails.
   - **M5 never-fires-swallowed** (skip a category that matched nothing) → both `RuleNeverFires` tests fail.
   - **M6 table-optional** (`{}` when `[mutate]` is absent) → `test_missing_table_refused` fails (the 2026-09-14 erratum 4).
   - **M7 in-place** (drop the deepcopy) → `test_input_graph_not_mutated_in_place` fails.
   - **M8 lora-model-only** (set `strength_model` only) → the LoRA test fails on `strength_clip`.
   - **Negative control** — make `mutate` set a seed unconditionally → `test_empty_category_skipped` fails; restore. The skip rule is under test.
5. **Commit.** As GN1's script; subject `generation: the rules mutator — a mutation grammar read from the lab manifest, applied to every matching node, deterministic under a seed (test: comfy-worlds-unit, lint)`; commands: `nix develop -c pytest tests/comfy-worlds/test_mutate.py -q 2>&1 | tail -n 3`, `grep -c 'class RuleNeverFires' pkgs/comfy-worlds/mutate.py`, `grep -n 'manifest.toml' pkgs/comfy-worlds/init.sh`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** every encoder, whole token → M1, M2 (fixture: `reddish fox, red`); every sampler → M3 (fixture: two samplers); every LoRA node, both strengths → M8; deterministic → M4; never-fires is an error → M5 (fixture: a token no encoder carries; a graph without a sampler); missing table refused → M6; input untouched → M7; empty category skipped → negative control.

**probes:**
- mutate-module: `test -f pkgs/comfy-worlds/mutate.py && echo 1 || echo 0` :: ge 1 :: this task
- never-fires: `grep -c 'class RuleNeverFires' pkgs/comfy-worlds/mutate.py` :: ge 1 :: Interfaces 2
- no-table-refused: `grep -c 'no \[mutate\] table' pkgs/comfy-worlds/mutate.py` :: ge 1 :: Interfaces 1
- four-categories: `grep -c '"tokens"\|"lora_strengths"\|"samplers"\|"seeds"' pkgs/comfy-worlds/mutate.py` :: ge 4 :: Interfaces 1

### GN6 (code, S) — comfy-mutate: the world-aware command, its wrapper and the on-demand user unit

**repo:** media
**dependsOn:** GN2, GN5
**touches:** `pkgs/comfy-worlds/mutate.py`, `pkgs/comfy-worlds/default.nix`, `nixosModules/comfyui-worlds.nix`, `flake.nix`, `checks/eval-harness.nix`, `tests/comfy-worlds/test_mutate_cli.py`
**acceptance:** comfy-worlds-unit, comfy-worlds-eval, lint
**commit subject:** generation: comfy-mutate — the world-aware command, its wrapper and the on-demand user unit per world (test: comfy-worlds-unit, comfy-worlds-eval, lint)

**Why.** GN5's grammar needs a subject (the newest liked render — "learning from likes", the generation-lab concept's premise) and a way onto ComfyUI (GN2's queue); 16b makes it an on-demand user unit like the generators. The unit's hardening is asserted by equality in `comfy-worlds-eval`, not described (2026-09-12 erratum 10; r2 erratum 11); the dry run is byte-deterministic under a seed so the drill can `cmp` two runs.

**Files.**
- Modify `pkgs/comfy-worlds/mutate.py` — `main(argv)` (Interfaces 1); imports `feed_index`, `job_queue`.
- Modify `pkgs/comfy-worlds/default.nix` — wrapper `comfy-mutate` (`writeShellApplication`, `runtimeInputs = [ pkgs.python3 ]`, `exec ${pkgs.python3}/bin/python3 ${worldsPy}/mutate.py "$@"`), exported beside `comfy-feed`.
- Modify `nixosModules/comfyui-worlds.nix` — option `services.comfyui-worlds.mutate.n` (`lib.types.ints.positive`, default `8`, description "variants comfy-mutate enqueues per run"); per world the user unit `comfy-mutate-<w>.service` (Interfaces 3).
- Modify `flake.nix` and/or `checks/eval-harness.nix` — whichever holds `comfy-worlds-eval`'s assertions (`grep -ln 'comfy-worlds-eval' flake.nix checks/*.nix` at Step 0): the assertions of Interfaces 4; `comfy-worlds-unit` sets `COMFY_MUTATE_BIN=${worldsPkgs.comfy-mutate}/bin/comfy-mutate` for pytest.
- Create `tests/comfy-worlds/test_mutate_cli.py`.

**Interfaces.**
1. `comfy-mutate --world W --root R [--n N] [--dry-run] [--seed S] [--comfy-url U]`: rules from `R/worlds/W/lab/manifest.toml`; the subject is the newest liked render — `SELECT r.name, r.graph FROM likes l JOIN renders r USING(name) ORDER BY l.ts DESC, r.name LIMIT 1`; none → exit 3, stderr `mutate: no likes in <world>`; a subject whose `graph` is `""` → exit 3, `mutate: liked render has no graph: <name>`. `N` variants (default 8): variant `i` uses `random.Random(S + i)` when `--seed` is given, else `random.Random(secrets.randbits(64))`. `--dry-run` prints one line per variant, `json.dumps({"applied": applied, "graph": graph2}, sort_keys=True)`, enqueues nothing, exit 0; otherwise `job_queue.enqueue(conn, "mutate", name, graph2, graph2's sampler seed)` per variant and prints `enqueued <N> jobs for <name>`. `RuleNeverFires` or `load_rules`'s `ValueError` → exit 2, stderr `mutate: <message>`; `--comfy-url` present and not loopback → exit 2 (GN-G; the CLI never submits — the feed's worker does — so the flag only validates). No timestamp, pid or path appears on stdout.
2. The wrapper `comfy-mutate` answers `--help` with exit 0 on a bare `PATH`.
3. `comfy-mutate-<w>.service` (a `systemd.user.services` entry, one per world): `Type = "oneshot"`; `ExecStart = "<wrapper>/bin/comfy-mutate --world <w> --root <root> --n <n>"`; `wantedBy = [ ]`; `unitConfig.ConditionUser = cfg.operatorUser`; `serviceConfig.ProtectHome = "read-only"`, `ReadWritePaths = [ "<root>/worlds/<w>" ]`, `PrivateTmp = true`, `NoNewPrivileges = true`; `path = [ ]` (the wrapper carries its own python).
4. `comfy-worlds-eval` asserts per world, each with its own message: `systemd.user.services ? "comfy-mutate-<w>"`; `ExecStart` ends with `--world <w> --root <root> --n 8` (the default; the harness sets nothing else); `wantedBy == [ ]`; `unitConfig.ConditionUser == operatorUser`; `serviceConfig.ProtectHome == "read-only"`; `serviceConfig.ReadWritePaths == [ "<root>/worlds/<w>" ]` (list equality — a second path fails it).

**Facts** (Step 0): `grep -ln 'comfy-worlds-eval' flake.nix checks/*.nix`; `grep -n 'ConditionUser\|wantedBy\|ProtectHome\|ReadWritePaths' nixosModules/comfyui-worlds.nix` (Assumption 19 — the existing units' shape, quoted into the commit body); `grep -n 'comfy-feed = \|comfy-world-guard' pkgs/comfy-worlds/default.nix` (the wrapper attrset).

**Steps.**
1. **Red.** Write `test_mutate_cli.py` with a world tree built in `tmp_path` (`worlds/sfw/{output,lab}`, a `manifest.toml` with `[mutate]`, PNGs from `write_png`, a `feed.sqlite` rebuilt by `feed_index`, one `like`): `test_dry_run_is_deterministic_under_seed` (two `main([..., "--dry-run", "--seed", "1", "--n", "3"])` runs → identical stdout of three lines); `test_dry_run_enqueues_nothing` (`jobs` count 0); `test_run_enqueues_n_jobs_of_kind_mutate` (`--n 3` → three rows, `kind mutate`, three distinct seeds under `--seed 1`); `test_sampler_variant_lands_in_every_ksampler` (`samplers = ["dpmpp_2m"]` → both `"3"` and `"9"` in every enqueued graph carry it); `test_no_likes_exit_3`; `test_liked_render_without_graph_exit_3`; `test_missing_table_exit_2`; `test_rule_never_fires_exit_2` (`samplers` set, a graph without a sampler); `test_non_loopback_comfy_url_exit_2`; `test_packaged_wrapper_help` (`pytest.skip` unless `COMFY_MUTATE_BIN` is set; then `subprocess.run(["env", "-i", "PATH=/nonexistent", bin, "--help"])` returns 0 — the sandbox sets it). `nix develop -c pytest tests/comfy-worlds/test_mutate_cli.py -q` → `AttributeError: module 'mutate' has no attribute 'main'` on every test but the skipped one; paste. Eval red: add the Interfaces-4 assertions, `nix build .#checks.x86_64-linux.comfy-worlds-eval -L --no-link` → `error: attribute 'comfy-mutate-sfw' missing`; paste.
2. Implement `main`, the wrapper, the option and the units.
3. **Green.** pytest → `9 passed, 1 skipped` locally (the packaged test needs the sandbox's env); `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` builds and its log shows `test_packaged_wrapper_help PASSED` (the bare-`PATH` proof, GN-C); `… comfy-worlds-eval …` and `… lint …` build. Paste the pytest tail and the check-log line.
4. **Mutants** (revert, run, restore):
   - **M1 seed-ignored** (`random.Random()` even with `--seed`) → `test_dry_run_is_deterministic_under_seed` fails.
   - **M2 dry-run-enqueues** → `test_dry_run_enqueues_nothing` fails.
   - **M3 wrong-kind** (`"regenerate"`) → `test_run_enqueues_n_jobs_of_kind_mutate` fails.
   - **M4 exit-0-on-no-likes** → `test_no_likes_exit_3` fails.
   - **M5 sampler-first-only** (in `mutate`, GN5's M3 rerun here through the CLI) → `test_sampler_variant_lands_in_every_ksampler` fails on `"3"`.
   - **M6 time-in-output** (a timestamp on each dry-run line) → the determinism test fails — the negative control's counterpart, proving byte-identity is load-bearing.
   - **M7 unit-wanted** (`wantedBy = [ "default.target" ]`) → `comfy-worlds-eval` fails with its `wantedBy` message.
   - **M8 conditionuser-dropped** → `comfy-worlds-eval` fails with its `ConditionUser` message.
   - **M9 readwritepaths-widened** (`[ "<root>" ]`) → `comfy-worlds-eval` fails with its `ReadWritePaths` message (equality, not containment).
   - **M10 protecthome-dropped** → `comfy-worlds-eval` fails with its `ProtectHome` message.
   - **Negative control** — GN3's feed-unit `ExecStart` assertion in `comfy-worlds-eval` fails when `--world` is removed from the module's feed `ExecStart`; restore. The eval discriminates the existing units too.
5. **Commit.** As GN1's script; subject `generation: comfy-mutate — the world-aware command, its wrapper and the on-demand user unit per world (test: comfy-worlds-unit, comfy-worlds-eval, lint)`; commands: `nix develop -c pytest tests/comfy-worlds/test_mutate_cli.py -q 2>&1 | tail -n 3`, `grep -n 'comfy-mutate-' nixosModules/comfyui-worlds.nix`, `grep -c 'ConditionUser' nixosModules/comfyui-worlds.nix`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** deterministic dry run → M1, M6; dry run enqueues nothing → M2; kind → M3; exit codes → M4 (fixture: no likes; a liked render without a graph); every sampler → M5 (fixture: two samplers); unit shape by equality → M7–M10 (fixture: the harness config with one world); existing units discriminated → negative control.

**probes:**
- mutate-wrapper: `grep -c 'comfy-mutate' pkgs/comfy-worlds/default.nix` :: ge 1 :: Interfaces 2
- mutate-units: `grep -c 'comfy-mutate-' nixosModules/comfyui-worlds.nix` :: ge 1 :: Interfaces 3
- condition-user: `grep -c 'ConditionUser' nixosModules/comfyui-worlds.nix` :: ge 1 :: Interfaces 3, the mutate unit
- mutate-main: `grep -c 'def main' pkgs/comfy-worlds/mutate.py` :: ge 1 :: Interfaces 1

### GN7 (code, S) — the upstream probe goes through the broker: a proxied opener that refuses before any socket, and the unit moved inside the media namespace

**repo:** media
**dependsOn:** none
**touches:** `pkgs/comfy-upstream-probe/probe.py`, `nixosModules/comfyui-worlds.nix`, `flake.nix`, `checks/eval-harness.nix`, `tests/comfy-upstream-probe/test_egress.py`
**acceptance:** comfy-upstream-probe-unit, comfy-worlds-eval, lint
**commit subject:** generation: the upstream probe goes through the broker — a proxied opener that refuses before any socket, and the unit moved inside the media namespace (test: comfy-upstream-probe-unit, comfy-worlds-eval, lint)

**Why.** Question 1(a), the default: the probe opens `api.github.com`, `pypi.org` and four more directly (Assumption 23), and the decision it cites for that carve-out says the opposite (spec §5 Q3). Invariant 3 is satisfied by a rule the process enforces before it touches a socket — no `HTTPS_PROXY`, no fetch — and by where the process runs: the broker's own nftables chain drops host-namespace traffic to the proxy (Assumption 10), so a user timer outside `egress-media` could never reach it; every brokered consumer in this house is a system unit that joins the namespace with `NetworkNamespacePath` and runs as the operator (`nixosModules/seatLane.nix`, Assumption 10). The probe follows that pattern: a system service and timer, `User = operatorUser`, inside `egress-<instance>`. Its output directory and schedule are unchanged; GN10 supplies the instance on core; the eval pins the unit's environment by equality (r2 erratum 10).

**Files.**
- Modify `pkgs/comfy-upstream-probe/probe.py` — `_opener()` and `_open(url, timeout=30)` (Interfaces 1); every fetch goes through `_open`; the direct `urllib.request.urlopen` calls go.
- Modify `nixosModules/comfyui-worlds.nix` — options `services.comfyui-worlds.probe.brokerInstance` (`lib.types.str`, default `"media"`), `probe.proxyUrl` (`lib.types.str`, default `"http://10.100.2.1:3130"`), `probe.caBundle` (`lib.types.str`, default `"/var/lib/egress-broker-ca-bundle/media/ca-bundle.crt"`); the probe's user service and timer become the system units `systemd.services.comfy-upstream-probe` and `systemd.timers.comfy-upstream-probe` (Interfaces 3); an assertion `config.services.egress-broker.instances ? ${cfg.probe.brokerInstance}` with the message `services.comfyui-worlds.probe.brokerInstance '<name>' has no matching services.egress-broker.instances entry` (the `cowork.nix` wording, Assumption 10).
- Modify `flake.nix` and/or `checks/eval-harness.nix` — whichever holds `comfy-worlds-eval`'s assertions (`grep -ln 'comfy-worlds-eval' flake.nix checks/*.nix` at Step 0): the assertions of Interfaces 4; the eval harness's stub of instance `media` (Assumption 24) is what lets the assertion above hold in the sandbox — if the VM check's config lacks the stub, the same stub is added there (Step 0 measures; a `tests/*.nix` edit is disclosed with a `Deviation:` line).
- Create `tests/comfy-upstream-probe/test_egress.py`.

**Interfaces.**
1. `_open(url, timeout=30) -> bytes`: reads `HTTPS_PROXY` and `SSL_CERT_FILE` from the environment; `HTTPS_PROXY` unset or empty → `RuntimeError("probe: HTTPS_PROXY is unset — invariant 3: every byte leaving the machine crosses the broker")`; its host, from `urllib.parse.urlsplit`, must be a literal address for which `ipaddress.ip_address(host).is_loopback or .is_private` holds — a hostname → `RuntimeError("probe: HTTPS_PROXY must be a literal loopback or private address")`, a public literal → `RuntimeError("probe: HTTPS_PROXY must be a loopback or private address")`; `SSL_CERT_FILE` unset, or not a readable regular file → `RuntimeError("probe: SSL_CERT_FILE is unset or unreadable: <path>")`. All four refusals happen before any socket is opened. Then `urllib.request.build_opener(ProxyHandler({"https": proxy, "http": proxy}), HTTPSHandler(context=ssl.create_default_context(cafile=cert)))`, built once per process, `.open(url, timeout=timeout).read()`; network errors propagate as today.
2. The CLI maps a `RuntimeError` from `_open` to exit 2 with the message on stderr; every other behaviour of the probe is unchanged — its existing tests pass untouched.
3. `systemd.services.comfy-upstream-probe`: `Type = "oneshot"`; `ExecStart = <the probe's existing command line>`; `serviceConfig.User = cfg.operatorUser`; `serviceConfig.NetworkNamespacePath = "/var/run/netns/egress-${cfg.probe.brokerInstance}"`; `after = [ "egress-broker-${cfg.probe.brokerInstance}.service" ]` and `requires` the same; `environment = { HTTPS_PROXY = cfg.probe.proxyUrl; SSL_CERT_FILE = cfg.probe.caBundle; }` and nothing else; `ProtectSystem = "strict"`, `ReadWritePaths = [ <the probe's output directory, measured at Step 0> ]`, `ProtectHome = "read-only"` only when that directory is outside `/home`; `PrivateTmp = true`, `NoNewPrivileges = true`. `systemd.timers.comfy-upstream-probe`: the existing `OnCalendar` (Sunday 04:00), `Persistent = true`, `wantedBy = [ "timers.target" ]`. The user-scope units of the same name are removed. The defaults are the `media` instance's values GN10 pins on core (Assumption 10: `10.100.2.x` reserved for media; 3130 is free among cowork 3129, openrouter 3131, seat 3141).
4. `comfy-worlds-eval` asserts `builtins.sort builtins.lessThan (lib.mapAttrsToList (k: v: "${k}=${v}") config.systemd.services.comfy-upstream-probe.environment) == [ "HTTPS_PROXY=http://10.100.2.1:3130" "SSL_CERT_FILE=/var/lib/egress-broker-ca-bundle/media/ca-bundle.crt" ]` with the message `eval: probe unit environment must be exactly the proxy and the CA bundle` — list equality, so a third entry fails it; and `config.systemd.services.comfy-upstream-probe.serviceConfig.NetworkNamespacePath == "/var/run/netns/egress-media"` with `eval: probe unit must join egress-media`; and `!(config.systemd.user.services ? comfy-upstream-probe)` with `eval: the probe is no longer a user unit`.

**Facts** (Step 0): `grep -n 'urlopen(' pkgs/comfy-upstream-probe/probe.py` → the direct calls (Assumption 23); `grep -o 'https://[a-z.]*' pkgs/comfy-upstream-probe/probe.py | sort -u` → seven lines (six hosts and the `https://pypi` regex artefact); `grep -n 'comfy-upstream-probe\|OnCalendar' nixosModules/comfyui-worlds.nix` → the user units and their schedule; `grep -n 'proposals\|open(' pkgs/comfy-upstream-probe/probe.py | head` → the output directory the unit must be able to write; `grep -n 'instances.media\|egress-broker' checks/*.nix tests/*.nix flake.nix` → where the `media` stub lives (Assumption 24); `grep -c 'def test' tests/comfy-upstream-probe/test_*.py` → 16 (Assumption 23; re-count).

**Steps.**
1. **Red.** Write `test_egress.py`: `test_open_refuses_without_proxy` (`monkeypatch.delenv` both; `RuntimeError` naming `HTTPS_PROXY`; `socket.socket` monkeypatched to raise `AssertionError("socket opened")` and it did not); `test_open_refuses_missing_ca_file`; `test_open_refuses_unreadable_ca_file` (`chmod 0o000`; `pytest.skip` when running as root); `test_open_refuses_hostname_proxy` (`http://proxy.local:3128`); `test_open_refuses_public_proxy_address` (`http://8.8.8.8:3128`); `test_open_uses_the_proxy` (a fake proxy — `http.server` on `127.0.0.1:0` whose handler records the request line and answers 502; `SSL_CERT_FILE` pointing at any readable file; `_open("https://api.github.com/x")` raises `URLError`/`HTTPError` and the fake's recorded line contains `api.github.com`); `test_no_direct_urlopen_remains` (`"urlopen(" not in Path(probe.__file__).read_text()`); `test_cli_exit_2_without_proxy` (`subprocess.run([sys.executable, probe.py, <the probe's usual args on the fixture repo>], env={"PATH": os.environ["PATH"]})` → returncode 2, stderr contains `invariant 3`). `nix develop -c pytest tests/comfy-upstream-probe/test_egress.py -q` → `AttributeError: module 'probe' has no attribute '_open'` and the direct-call test failing; paste the count. Eval red: add the Interfaces-4 assertions, `nix build .#checks.x86_64-linux.comfy-worlds-eval -L --no-link` → `error: attribute 'comfy-upstream-probe' missing` (no system unit yet); paste.
2. Implement `_opener`/`_open`, route every fetch through it, add the options, move the units to system scope with the namespace.
3. **Green.** pytest → `8 passed` (or 7 and 1 skipped as root); the probe's existing tests still pass (`nix develop -c pytest tests/comfy-upstream-probe -q` → the Step-0 count plus 8); `nix build .#checks.x86_64-linux.comfy-upstream-probe-unit -L --no-link`, `… comfy-worlds-eval …`, `… lint …` build; `grep -c 'urlopen(' pkgs/comfy-upstream-probe/probe.py; true` → `0`. Paste.
4. **Mutants** (revert, run, restore):
   - **M1 fall-back-to-direct** (no proxy → `urlopen`) → `test_open_refuses_without_proxy` fails.
   - **M2 refusal-after-socket** (`socket.create_connection` before the check) → the same test fails on `socket opened`.
   - **M3 ca-unchecked** → `test_open_refuses_missing_ca_file` fails.
   - **M4 hostname-allowed** → `test_open_refuses_hostname_proxy` fails.
   - **M5 public-allowed** → `test_open_refuses_public_proxy_address` fails.
   - **M6 proxy-ignored** (`build_opener` without the `ProxyHandler`) → `test_open_uses_the_proxy` fails (the fake saw nothing).
   - **M7 one-direct-call-left** → `test_no_direct_urlopen_remains` fails.
   - **M8 env-extra** (a third `environment` entry in the module) → `comfy-worlds-eval` fails with the environment message.
   - **M9 containment-check** (the eval asserts `hasAttr` twice instead of equality) → M8 passes under it — the seat shows M8 green under M9, then restores equality (r2 erratum 10).
   - **M10 user-unit-kept** (leave the user-scope service beside the system one) → `comfy-worlds-eval` fails `the probe is no longer a user unit`.
   - **M11 namespace-dropped** → `comfy-worlds-eval` fails `probe unit must join egress-media`.
   - **Negative control** — the probe's existing fixture-repo test (`grep -l 'fixtures/repo' tests/comfy-upstream-probe/test_*.py`) fails when one file under `tests/comfy-upstream-probe/fixtures/repo/` is renamed; restore. The existing suite discriminates in the sandbox.
5. **Commit.** As GN1's script; subject `generation: the upstream probe goes through the broker — a proxied opener that refuses before any socket, and the unit moved inside the media namespace (test: comfy-upstream-probe-unit, comfy-worlds-eval, lint)`; commands: `nix develop -c pytest tests/comfy-upstream-probe -q 2>&1 | tail -n 3`, `grep -c 'urlopen(' pkgs/comfy-upstream-probe/probe.py; true`, `grep -o 'https://[a-z.]*' pkgs/comfy-upstream-probe/probe.py | sort -u`, `grep -n 'NetworkNamespacePath\|HTTPS_PROXY\|SSL_CERT_FILE' nixosModules/comfyui-worlds.nix`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** refusal before any socket → M1, M2 (fixture: a socket that raises); the CA file → M3; a literal private or loopback proxy → M4, M5 (fixture: a hostname; a public literal); the proxy is used → M6 (fixture: a recording fake); no direct call → M7; exactly two variables → M8, M9 (fixture: a third entry); a system unit inside the namespace, no user unit → M10, M11; the suite discriminates → negative control.

**probes:**
- no-urlopen: `grep -c 'urlopen(' pkgs/comfy-upstream-probe/probe.py; true` :: le 0 :: Assumption 23, at least one before this task
- refusal-text: `grep -c 'invariant 3' pkgs/comfy-upstream-probe/probe.py` :: ge 1 :: Interfaces 1
- unit-env: `grep -c 'HTTPS_PROXY\|SSL_CERT_FILE' nixosModules/comfyui-worlds.nix` :: ge 2 :: Interfaces 3
- unit-in-netns: `grep -c 'NetworkNamespacePath' nixosModules/comfyui-worlds.nix` :: ge 1 :: Interfaces 3
- six-hosts: `grep -o 'https://[a-z.]*' pkgs/comfy-upstream-probe/probe.py | sort -u | grep -v -x 'https://pypi' | wc -l` :: le 6 :: Assumption 23, the six hosts GN10 allows

### GN8 (code, S) — engagement: the feed counts opens, dwell and likes per UTC day and POSTs them to Helm's loopback endpoint

**repo:** media
**dependsOn:** GN4, EV15
**touches:** `pkgs/comfy-worlds/engage.py`, `pkgs/comfy-worlds/feed.py`, `nixosModules/comfyui-worlds.nix`, `flake.nix`, `checks/eval-harness.nix`, `tests/comfy-worlds/test_engage.py`
**acceptance:** comfy-worlds-unit, comfy-worlds-eval, lint
**commit subject:** generation: the feed counts opens, dwell and likes per UTC day and POSTs the counts to Helm's loopback endpoint (test: comfy-worlds-unit, comfy-worlds-eval, lint)

**Why.** Decision 18b: "a local-only engagement stream in the evidence store (opens, dwell seconds, feed likes per day; counts, never content)". The Evidence plan declares the class (EV14) and lands the kind (EV15) with `replace_stream` as the only verb, and the board records the redesign this section follows: the feed writes nothing to the store; it POSTs the five-field row to Helm's `/v1/engage` on loopback and drops on any error (Assumptions 4, 9, 33). `dependsOn: EV15` because the field set and the `feed` surface are EV15's enum; the seat cannot read this repo, so the five names are a literal here (2026-09-14 erratum 3) and the drill reads the row back once Helm's endpoint exists.

**Files.**
- Create `pkgs/comfy-worlds/engage.py` — `Counter`, `Sender` (Interfaces 1–3); imports nothing from the siblings.
- Modify `pkgs/comfy-worlds/feed.py` — `--engage-url` (default `""` = disabled), `--engage-interval` (default 3600), the `Counter` hooks on `GET /`, `/like` and the new `POST /dwell`, the SIGTERM handler in `main` (Interfaces 4–5).
- Modify `nixosModules/comfyui-worlds.nix` — option `services.comfyui-worlds.engage.url` (`lib.types.str`, default `"http://127.0.0.1:7710/v1/engage"`); the feed unit's `ExecStart` gains `--engage-url <url>`.
- Modify `flake.nix` and/or `checks/eval-harness.nix` — `comfy-worlds-eval` asserts the feed unit's `ExecStart` contains `--engage-url http://127.0.0.1:7710/v1/engage`.
- Create `tests/comfy-worlds/test_engage.py`.

**Interfaces.**
1. `Counter(day_fn=lambda: utc date)`: per-day counters `opens`, `dwell_s`, `feed_likes`, each `min(n, 10_000_000)`; `open()` +1; `dwell(seconds)` accepts an int in `0 ≤ s ≤ 86400` (else `ValueError`); `like()` +1; `snapshot() -> dict` = `{"day": "<YYYY-MM-DD>", "surface": "feed", "opens": int, "dwell_s": int, "feed_likes": int}` — exactly these five keys, the literal of EV14 terms 1–5 (Assumption 9) — and nothing that names a render, a prompt or a client. On a day change the previous day's snapshot is kept as `pending_previous` until one flush sends it, then discarded.
2. `Sender(url, counter, interval=3600.0)`: `url`'s host must be `127.0.0.1` or `localhost` at construction, else `ValueError("engage: endpoint is loopback-only: <url>")`; `flush()` POSTs `json.dumps(snapshot)` (plus the pending previous day first) as `application/json` with a 5 s timeout; every exception (`URLError`, `HTTPError`, `TimeoutError`, `ConnectionError`, `OSError`) is caught, logged once as `engage: dropped: <class name>` to stderr, and the counters are **kept** — the next flush resends the day's cumulative snapshot, which Helm's keyed replace makes idempotent; nothing is ever raised out of `flush()`.
3. `Sender.start()` runs a daemon thread `comfy-feed-engage` that sleeps `interval` and calls `flush()`, forever, inside `try/except Exception` (log and continue). `Sender.stop()` flushes once and stops the thread.
4. `feed.py`: `GET /` → `counter.open()`; a `/like` that answered 303 → `counter.like()`; `POST /dwell` with form `seconds` → `counter.dwell(int)` → 204; a non-integer or out-of-range value → 400; the body cap of GN4 applies. `--engage-url ""` disables the sender and the hooks are no-ops; `main` installs `signal.signal(SIGTERM, …)` that calls `sender.stop()` then exits 0.
5. The unit's `ExecStart` carries `--engage-url http://127.0.0.1:7710/v1/engage` from the option; `comfy-worlds-eval` asserts it with the message `eval: feed unit must carry --engage-url`.

**Facts** (Step 0): `grep -n 'def do_GET\|def do_POST\|def main' pkgs/comfy-worlds/feed.py` (GN4's shape); `grep -n 'ExecStart' nixosModules/comfyui-worlds.nix` → the feed unit line GN3 wrote; the five names, quoted from this repo's EV14 for the seat: `day`, `surface`, `opens`, `dwell_s`, `feed_likes`, and `surface`'s enum `("home", "feed", "seats")`.

**Steps.**
1. **Red.** Write `test_engage.py` with a fake endpoint (`http.server` on `127.0.0.1:0` recording every body; the thread-start helper written out): `test_snapshot_has_exactly_five_keys_and_counts` (`set(snap) == {"day","surface","opens","dwell_s","feed_likes"}`, `surface == "feed"`, values after 2 opens, 30 s dwell, 1 like); `test_dwell_bounds` (0 and 86400 accepted; -1 and 86401 → `ValueError`); `test_counter_caps_at_ten_million`; `test_flush_posts_json_to_loopback` (the fake's body parses to the snapshot; `Content-Type: application/json`); `test_flush_drops_on_error_and_keeps_counts` (a closed port → no exception; counts unchanged; one stderr line `engage: dropped:`); `test_sender_refuses_non_loopback`; `test_periodic_flush_is_scheduled` (`interval=0.05`; after 0.3 s the fake saw at least 2 POSTs); `test_day_rollover_sends_previous_day_once` (`day_fn` injected; two flushes after the change → the first carries two bodies, the second one); `test_sigterm_flushes` (subprocess `sys.executable feed.py --world sfw --root <tmp> --port 0 --engage-url <fake> --poll-interval 0`; `send_signal(SIGTERM)`; `returncode == 0`; the fake saw one POST); `test_dwell_route_204_and_400`; `test_open_and_like_hooks_count` (`GET /` twice, one successful `/like` → opens 2, feed_likes 1); `test_no_content_field_ever` (after likes on `fox.png`, `json.dumps(snapshot)` does not contain `fox`). `nix develop -c pytest tests/comfy-worlds/test_engage.py -q` → `ModuleNotFoundError: No module named 'engage'`; paste the count. Eval red as GN7's: the `--engage-url` assertion added, `nix build .#checks.x86_64-linux.comfy-worlds-eval` → `eval: feed unit must carry --engage-url`; paste.
2. Implement.
3. **Green.** `12 passed`; `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link`, `… comfy-worlds-eval …`, `… lint …` build; paste.
4. **Mutants** (revert, run, restore):
   - **M1 leak-prompt** (add `"prompt"` to the snapshot), **M2 leak-names** (add `"names": […]`) → `test_snapshot_has_exactly_five_keys_and_counts` fails on the key set; M2 also fails `test_no_content_field_ever`.
   - **M3 bounds-dropped** → `test_dwell_bounds` fails on -1 and 86401 (the fixture's four rows are 0, 86400, -1, 86401).
   - **M4 raise-on-error** (no `except` in `flush`) → `test_flush_drops_on_error_and_keeps_counts` fails (`URLError` raised).
   - **M5 reset-on-drop** → the same test fails on the counts.
   - **M6 no-periodic-thread** → `test_periodic_flush_is_scheduled` fails (0 POSTs).
   - **M7 no-sigterm-handler** → `test_sigterm_flushes` fails (returncode −15, no POST).
   - **M8 non-loopback-allowed** → `test_sender_refuses_non_loopback` fails.
   - **M9 execstart-without-flag** → `comfy-worlds-eval` fails with its message.
   - **M10 previous-day-resent-forever** → `test_day_rollover_sends_previous_day_once` fails (two bodies twice).
   - **Negative control** — set the fake to accept anything and drop the key-set assertion → a `Sender` posting `{}` passes `test_flush_posts_json_to_loopback`; restore. The key-set assertion is what discriminates.
5. **Commit.** As GN1's script; subject `generation: the feed counts opens, dwell and likes per UTC day and POSTs the counts to Helm's loopback endpoint (test: comfy-worlds-unit, comfy-worlds-eval, lint)`; commands: `nix develop -c pytest tests/comfy-worlds/test_engage.py -q 2>&1 | tail -n 3`, `grep -c '/var/lib/evidence' pkgs/comfy-worlds/engage.py pkgs/comfy-worlds/feed.py; true`, `grep -n 'engage' nixosModules/comfyui-worlds.nix`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** exactly five keys, counts only → M1, M2 (fixture: likes on a named render); dwell bounds → M3 (rows 0/86400/-1/86401); drop and keep → M4, M5; scheduled → M6; SIGTERM → M7; loopback → M8; unit flag → M9; day rollover once → M10; the fake discriminates → negative control.

**probes:**
- engage-module: `test -f pkgs/comfy-worlds/engage.py && echo 1 || echo 0` :: ge 1 :: this task
- five-keys: `grep -c '"feed_likes"' pkgs/comfy-worlds/engage.py` :: ge 1 :: Interfaces 1
- engage-url-default: `grep -c '127.0.0.1:7710/v1/engage' nixosModules/comfyui-worlds.nix` :: ge 1 :: Assumption 33
- no-store-write: `grep -c '/var/lib/evidence' pkgs/comfy-worlds/engage.py pkgs/comfy-worlds/feed.py; true` :: le 0 :: the board's redesign, Assumption 4

### GN9 (docs, S) — the runbook and the acceptance drill carry the feed, the verbs, the mutator and the brokered probe

**repo:** media
**dependsOn:** GN4, GN6, GN7, GN8
**touches:** `docs/runbooks/media.md`, `tests/acceptance/media-worlds.sh`
**acceptance:** lint
**commit subject:** generation: the media runbook and the acceptance drill carry the feed, the verbs, the mutator and the brokered probe (test: lint)

**Why.** Decision 70b: one composed drill per increment, assembled from each subsystem's `## Operator`; the media drill script and runbook exist (Assumption 26) and know nothing of the feed's verbs, the mutator or the probe's environment. GN10 depends on this key: the host wiring is dispatched only when the media side is documented and drillable. Every new step is literal shell here, with its helpers written out, so the seat reads no other file for the idiom (r2 erratum 3).

**Files.**
- Modify `docs/runbooks/media.md` — two new sections: `## The feed` (starting the feed unit; `curl --noproxy '*' -s http://127.0.0.1:<feedPort>/healthz` → `ok <world>`; the three verbs as `curl --noproxy '*' -d name=<png> http://127.0.0.1:<feedPort>/like` (and `/regenerate`, `/edit` with `-d prompt=…`); `/jobs`; `comfy-feed-index rebuild --root <root> --world <w>` and the sentence "`feed.sqlite` is an index: deleting it loses likes and queued jobs, nothing else"; the engage URL and the five counts it sends) and `## The mutator and the probe` (the `[mutate]` table with a four-key example; `comfy-mutate --world <w> --root <root> --dry-run --seed 1`; `systemctl --user start comfy-mutate-<w>.service`; the probe's `HTTPS_PROXY` and `SSL_CERT_FILE`, the exit-2 refusal without them, and the sentence "the probe reaches six hosts through the `media` broker instance and nothing else").
- Modify `tests/acceptance/media-worlds.sh` — steps 9–14 appended after the existing eight, in the block below; inputs `WORLD` (default `sfw`), `ROOT` (default `$HOME/comfyui`), `FEED_PORT` (required outside `--self-test`), `PROBE_BIN` (required outside `--self-test`), `MUTATE_BIN` (default `comfy-mutate`).

```
# --- GN9: steps 9-14 (helpers defined only if the script has none of that name) ---
type step >/dev/null 2>&1 || step() { printf '%s: ' "$1"; }
type pass >/dev/null 2>&1 || pass() { echo PASS; }
type fail >/dev/null 2>&1 || fail() { echo "FAIL: $*"; rc=1; }
type skip >/dev/null 2>&1 || skip() { echo "SKIP: $*"; }
WORLD=${WORLD:-sfw}; ROOT=${ROOT:-$HOME/comfyui}; MUTATE_BIN=${MUTATE_BIN:-comfy-mutate}
db="$ROOT/worlds/$WORLD/feed.sqlite"
py() { if command -v python3 >/dev/null 2>&1; then python3 "$@"; else nix develop -c python3 "$@"; fi; }
likes() { py -c "import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute('select count(*) from likes').fetchone()[0])" "$db"; }
jobs_of() { curl --noproxy '*' -fsS "http://127.0.0.1:$FEED_PORT/jobs" | py -c "import json,sys; print(sum(1 for j in json.load(sys.stdin) if j['kind']==sys.argv[1]))" "$1"; }
step "9 feed healthz"
if [ "${SELF_TEST:-0}" = 1 ]; then command -v curl >/dev/null 2>&1 && pass || fail "curl missing"
else out=$(curl --noproxy '*' -fsS "http://127.0.0.1:${FEED_PORT:?}/healthz"); [ "$out" = "ok $WORLD" ] && pass || fail "healthz: $out"; fi
step "10 like writes one likes row"
if [ "${SELF_TEST:-0}" = 1 ]; then { command -v python3 >/dev/null 2>&1 || command -v nix >/dev/null 2>&1; } && pass || fail "neither python3 nor nix on PATH"
else name=$(curl --noproxy '*' -fsS "http://127.0.0.1:$FEED_PORT/" | grep -o 'name="name" value="[^"]*"' | head -1 | cut -d'"' -f4); before=$(likes); curl --noproxy '*' -s -o /dev/null -d "name=$name" "http://127.0.0.1:$FEED_PORT/like"; [ "$(likes)" -eq $((before + 1)) ] && pass || fail "likes $(likes) after $before"; fi
step "11 regenerate enqueues a regenerate job"
if [ "${SELF_TEST:-0}" = 1 ]; then pass
else before=$(jobs_of regenerate); curl --noproxy '*' -s -o /dev/null -d "name=$name" "http://127.0.0.1:$FEED_PORT/regenerate"; [ "$(jobs_of regenerate)" -eq $((before + 1)) ] && pass || fail "no regenerate job"; fi
step "12 edit enqueues an edit job"
if [ "${SELF_TEST:-0}" = 1 ]; then pass
else before=$(jobs_of edit); curl --noproxy '*' -s -o /dev/null -d "name=$name" -d "prompt=a red fox, drill" "http://127.0.0.1:$FEED_PORT/edit"; [ "$(jobs_of edit)" -eq $((before + 1)) ] && pass || fail "no edit job"; fi
step "13 mutate dry run is byte-identical under a seed"
if [ "${SELF_TEST:-0}" = 1 ]; then command -v "$MUTATE_BIN" >/dev/null 2>&1 && pass || skip "$MUTATE_BIN not on PATH"
else "$MUTATE_BIN" --world "$WORLD" --root "$ROOT" --dry-run --seed 1 >/tmp/gn9-m1; "$MUTATE_BIN" --world "$WORLD" --root "$ROOT" --dry-run --seed 1 >/tmp/gn9-m2; cmp -s /tmp/gn9-m1 /tmp/gn9-m2 && [ -s /tmp/gn9-m1 ] && pass || fail "dry runs differ or are empty"; fi
step "14 probe refuses without the broker environment"
if [ "${SELF_TEST:-0}" = 1 ]; then pass
else env -u HTTPS_PROXY -u SSL_CERT_FILE "${PROBE_BIN:?}" >/dev/null 2>&1; [ $? -eq 2 ] && pass || fail "probe did not refuse with exit 2"; fi
```

The script's existing `--self-test` handling sets `SELF_TEST=1` (measured at Step 0; if the existing flag variable has another name, the six `if` lines read that name instead and the commit body says which).

**Interfaces.**
1. `docs/runbooks/media.md` has exactly fourteen `## ` sections (twelve + two), the two new headings verbatim `## The feed` and `## The mutator and the probe`.
2. `tests/acceptance/media-worlds.sh --self-test` exits 0 on a tree where `curl` and `python3` resolve, and step 9 prints `FAIL: curl missing` under `PATH=/nonexistent` (the self-test arm is a real check, 2026-09-12 erratum 28).
3. Outside `--self-test`, every step prints `PASS` or `FAIL: <reason>` and the script's exit code is 1 when any step failed; steps 9–14 need `FEED_PORT` and `PROBE_BIN` and stop with bash's `:?` message when unset.
4. `shellcheck` (inside media's `lint`) is clean on the file.

**Facts** (Step 0): `grep -c '^## ' docs/runbooks/media.md` → 12; `grep -n 'self-test\|SELF_TEST\|^step\|step()' tests/acceptance/media-worlds.sh` → the flag and the helper idiom; `grep -c '^step ' tests/acceptance/media-worlds.sh` (or the idiom's equivalent) → 8.

**Steps.**
1. **Red.** The two counts of Step 0 pasted: 12 sections, 8 steps. `SELF_TEST=1 bash tests/acceptance/media-worlds.sh --self-test | grep -c 'feed healthz'` → 0.
2. Add the sections and the block.
3. **Green.** `grep -c '^## ' docs/runbooks/media.md` → 14; the step count → 14; `bash tests/acceptance/media-worlds.sh --self-test; echo $?` → the six new lines print and `0`; `PATH=/nonexistent bash tests/acceptance/media-worlds.sh --self-test 2>&1 | grep -c 'FAIL: curl missing'` → 1 (with `bash` invoked by absolute path); `nix build .#checks.x86_64-linux.lint -L --no-link` builds (shellcheck). Paste all.
4. **Mutants** (revert, run, restore):
   - **M1 section-dropped** → the section count reads 13.
   - **M2 self-test-guard-dropped** (step 9's self-test arm becomes `pass`) → the `PATH=/nonexistent` count reads 0.
   - **M3 likes-not-counted** (step 10 compares `$(likes)` to itself) → not killable by `--self-test`; killed by the live drill (Operator step 11), stated as such.
   - **M4 wrong-exit** (step 14 accepts any non-zero) → killed live by Operator step 16 (a probe that exits 1 must FAIL); stated as such.
   - **Negative control** — `shellcheck tests/acceptance/media-worlds.sh` fails when one `"$FEED_PORT"` quote is removed (SC2086); restore.
5. **Commit.** As GN1's script; subject `generation: the media runbook and the acceptance drill carry the feed, the verbs, the mutator and the brokered probe (test: lint)`; commands: `grep -c '^## ' docs/runbooks/media.md`, `bash tests/acceptance/media-worlds.sh --self-test; echo exit=$?`, `PATH=/nonexistent /bin/sh -c 'bash tests/acceptance/media-worlds.sh --self-test' 2>&1 | grep -c 'FAIL: curl missing'`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** fourteen sections → M1; the self-test arm is real → M2 (fixture: an empty PATH); the live steps → M3, M4 (killed by the drill, Operator steps 11 and 16); shellcheck → negative control.

**probes:**
- runbook-sections: `grep -c '^## ' docs/runbooks/media.md` :: ge 14 :: Assumption 26, twelve plus two
- runbook-sections-exact: `grep -c '^## ' docs/runbooks/media.md` :: le 14 :: two sections added, no third
- drill-feed-step: `grep -c 'feed healthz' tests/acceptance/media-worlds.sh` :: ge 1 :: Interfaces 2
- self-test-exit: `bash tests/acceptance/media-worlds.sh --self-test >/dev/null 2>&1; echo $?` :: le 0 :: Interfaces 2

### GN10 (code, M) — the worlds on core: the media input, the media broker instance, the on-demand units, the backup paths and the wiring check

**dependsOn:** GN9
**areas:** platform, knowledge, evidence
**touches:** `flake.nix`, `flake.lock`, `hosts/core/media-worlds.nix`, `hosts/core/default.nix`, `hosts/core/proton-backup.nix`, `docs/runbooks/backup.md`, `docs/runbooks/media-worlds.md`, `docs/MAP.md`
**acceptance:** core-media-wiring, host-core, core-backup-wiring, lint
**commit subject:** generation: the worlds on core — the media input, the media broker instance, the on-demand units, the backup paths and the wiring check (test: core-media-wiring, host-core, core-backup-wiring, lint)

**Why.** Decision 16b: "the worlds' on-demand user units plus host-level Caddy wired into `core`, no specialisation"; "Host integration does not exist" (spec §2: `grep -n -i media flake.nix` → two hits, neither an input; `hosts/core/helm.nix`: "'media' stays OUT of profiles until round 2 wires specialisation.media"). This is WH1 re-typed under the parseable grammar (Assumption 30) with question 3's default (`lan.enable = false`, no Caddy) and question 1's default (the `media` broker instance with the probe's six hosts). The check is a `throw` chain shaped on `core-backup-wiring` and `core-gaming-wiring`, inlined below, whose rules are over "every world" and "every `comfy-` unit", not a name list. `dependsOn: GN9` keeps this key `blocked` until media's `main` carries the whole media side (Assumption 16); a switch follows (Operator, #N).

**Files.**
- Modify `flake.nix` — (i) `inputs.media.url = "git+file:///home/dalhaka/flakes/media?ref=main";` beside `gaming.url`, no `follows` (the gaming comment's reasoning); `media` in the `outputs` argument set after `gaming`; (ii) `media.nixosModules.comfyui-worlds` in `nixosConfigurations.core`'s module list beside `gaming.nixosModules.default` (`grep -n 'gaming.nixosModules.default' flake.nix`); (iii) the check `core-media-wiring` after `core-gaming-wiring`, the chain in Interfaces 4.
- Modify `flake.lock` — `nix flake lock` adds the `media` node and its transitive `nixpkgs` node; no other node changes (`git diff flake.lock | grep '^[-+] *"rev"'` → the added nodes only).
- Create `hosts/core/media-worlds.nix`:
```
_: {
  # Generation: the ComfyUI worlds on core (plan 2026-09-11-generation.md, GN10;
  # decision 16b: on-demand user units, no specialisation; question 3(a): no LAN
  # face, so no Caddy, no 443, no password file until Isolation's increment 4).
  services.comfyui-worlds = {
    operatorUser = "dalhaka";
    root = "/home/dalhaka/comfyui";
    lan.enable = false;
    probe = {
      proxyUrl = "http://10.100.2.1:3130";
      caBundle = "/var/lib/egress-broker-ca-bundle/media/ca-bundle.crt";
    };
    worlds = {
      sfw = { comfyPort = 8288; feedPort = 8388; };
      nsfw = { comfyPort = 8289; feedPort = 8389; };
    };
  };
  # The probe's egress and nothing else (question 1(a)): six read-only public
  # names, no credential injected; 10.100.2.x has been reserved for media since
  # the lanes landed (hosts/core/lanes.nix, hosts/core/seat.nix).
  services.egress-broker.instances.media = {
    hostAddress = "10.100.2.1";
    namespaceAddress = "10.100.2.2";
    listenPort = 3130;
    allow = [
      "api.github.com"
      "download.nvidia.com"
      "github.com"
      "pypi.org"
      "raw.githubusercontent.com"
      "www.nvidia.com"
    ];
  };
}
```
  If the module's per-world `host` option has no default, the seat sets `host = "sfw.core"` / `"nsfw.core"` and the runbook says both are unused until the LAN task (measured at Step 0; said in the commit body). If the module has an `enable` option, it is set `true` here.
- Modify `hosts/core/default.nix` — `./media-worlds.nix` appended to `imports` after `./telemetry.nix`.
- Modify `hosts/core/proton-backup.nix` — `paths` gains `"/home/dalhaka/comfyui/worlds"` after `"/var/lib/lanes"` with the comment `# the worlds' lab repos and feed.sqlite (renders excluded below; rebuildable)`; `exclude` gains `"/home/dalhaka/comfyui/worlds/*/output"`.
- Modify `docs/runbooks/backup.md` — one bullet after the lane-ledgers bullet: "- the ComfyUI worlds — `/home/dalhaka/comfyui/worlds` (each world's `lab/` repo and `feed.sqlite`; `worlds/*/output`, the renders, is excluded — a render is regenerated from its seed and prompt)."
- Create `docs/runbooks/media-worlds.md` — the core-side runbook, every value pasted from `nix eval` at Step 3, never typed: for every world, its generator unit, feed unit and mutate unit names (`systemctl --user start <unit>` lines) and its `comfyPort`/`feedPort`; the probe as a system unit inside `egress-media` (`sudo systemctl start comfy-upstream-probe.service`, `systemctl list-timers comfy-upstream-probe.timer`); the switch and rollback lines of `## Operator`; and the line `media nixpkgs: <rev>` carrying `lockData.nodes.<media's nixpkgs node>.locked.rev` beside `host nixpkgs: <rev>` (the two differ until GN12 — Assumption 25 — and the check keeps the line true).
- Modify `docs/MAP.md` — `python3 pkgs/evidence/repomap.py --root . write` (the Checks section gains `core-media-wiring`; the Hosts section gains `hosts/core/media-worlds.nix`).

**Interfaces.**
1. `nixosConfigurations.core` evaluates with `services.comfyui-worlds` as above and `services.egress-broker.instances.media` as above; `nix build .#nixosConfigurations.core.config.system.build.toplevel` builds.
2. Every `systemd.user.services` attribute whose name starts with `comfy-` has `wantedBy == [ ]` (the generators, the feeds, GN6's mutate units — on demand); `systemd.services.comfy-upstream-probe` (GN7's system unit) has `serviceConfig.NetworkNamespacePath == "/var/run/netns/egress-media"`, `serviceConfig.User == "dalhaka"`, and its `environment` attrset rendered `k=v` and sorted equal to `[ "HTTPS_PROXY=http://10.100.2.1:3130" "SSL_CERT_FILE=/var/lib/egress-broker-ca-bundle/media/ca-bundle.crt" ]`; `systemd.timers.comfy-upstream-probe` exists with a non-empty `timerConfig.OnCalendar`.
3. `services.egress-broker.instances.media.allow` equals the six-name list above, in that order and length (`==` on lists); `.inject == { }`; `lan.enable == false`; across all worlds the `comfyPort`s and `feedPort`s are pairwise distinct (`lib.unique` of the four keeps four).
4. `core-media-wiring` (`pkgs.runCommand "core-media-wiring-check" { } "touch $out"` after the chain), each arm its own message:
```
core-media-wiring =
  let
    coreCfg = self.nixosConfigurations.core.config;
    cw = coreCfg.services.comfyui-worlds;
    worldNames = builtins.attrNames cw.worlds;
    ports = builtins.concatMap (w: [ cw.worlds.${w}.comfyPort cw.worlds.${w}.feedPort ]) worldNames;
    userUnits = coreCfg.systemd.user.services;
    comfyUnits = builtins.filter (n: nixpkgs.lib.hasPrefix "comfy-" n) (builtins.attrNames userUnits);
    wanted = builtins.filter (n: userUnits.${n}.wantedBy != [ ]) comfyUnits;
    probe = coreCfg.systemd.services.comfy-upstream-probe;
    probeEnv = builtins.sort builtins.lessThan (nixpkgs.lib.mapAttrsToList (k: v: "${k}=${v}") probe.environment);
    sixHosts = [ "api.github.com" "download.nvidia.com" "github.com" "pypi.org" "raw.githubusercontent.com" "www.nvidia.com" ];
    inst = coreCfg.services.egress-broker.instances;
    runbook = builtins.readFile ./docs/runbooks/media-worlds.md;
    missingRunbook = builtins.filter (w: !(nixpkgs.lib.hasInfix "feedPort ${toString cw.worlds.${w}.feedPort}" runbook)) worldNames;
    lockData = builtins.fromJSON (builtins.readFile ./flake.lock);
    mediaNixpkgsRev = lockData.nodes.${lockData.nodes.media.inputs.nixpkgs}.locked.rev;
    backupPaths = coreCfg.services.proton-backup.paths;
    backupExcl = coreCfg.services.proton-backup.exclude;
  in
  if !(coreCfg.services ? comfyui-worlds) then throw "core-media-wiring: services.comfyui-worlds is not on core (the media module is not imported)"
  else if cw.operatorUser != "dalhaka" then throw "core-media-wiring: operatorUser must be dalhaka"
  else if cw.lan.enable then throw "core-media-wiring: lan.enable must be false until the LAN task (plan 2026-09-11-generation.md question 3)"
  else if builtins.length (nixpkgs.lib.unique ports) != builtins.length ports then throw "core-media-wiring: a comfyPort or feedPort is shared between worlds"
  else if wanted != [ ] then throw "core-media-wiring: comfy- user units must be on demand (wantedBy = []): ${toString wanted}"
  else if !(inst ? media) then throw "core-media-wiring: no egress-broker instance named media"
  else if inst.media.allow != sixHosts then throw "core-media-wiring: the media instance allow list must be exactly the probe's six hosts"
  else if inst.media.inject != { } then throw "core-media-wiring: the media instance injects a credential; the probe needs none"
  else if probe.serviceConfig.NetworkNamespacePath != "/var/run/netns/egress-media" then throw "core-media-wiring: the probe must run inside egress-media"
  else if probeEnv != [ "HTTPS_PROXY=http://10.100.2.1:3130" "SSL_CERT_FILE=/var/lib/egress-broker-ca-bundle/media/ca-bundle.crt" ] then throw "core-media-wiring: the probe's environment must be exactly the proxy and the CA bundle"
  else if coreCfg.systemd.timers.comfy-upstream-probe.timerConfig.OnCalendar == "" then throw "core-media-wiring: the probe timer has no OnCalendar"
  else if !(builtins.elem "/home/dalhaka/comfyui/worlds" backupPaths) then throw "core-media-wiring: the worlds are not in the backup paths"
  else if !(builtins.elem "/home/dalhaka/comfyui/worlds/*/output" backupExcl) then throw "core-media-wiring: the renders must be excluded from the backup"
  else if missingRunbook != [ ] then throw "core-media-wiring: docs/runbooks/media-worlds.md does not name the feed port of: ${toString missingRunbook}"
  else if !(nixpkgs.lib.hasInfix "media nixpkgs: ${mediaNixpkgsRev}" runbook) then throw "core-media-wiring: docs/runbooks/media-worlds.md must name media's nixpkgs rev ${mediaNixpkgsRev}"
  else pkgs.runCommand "core-media-wiring-check" { } "touch $out";
```
5. `core-backup-wiring` keeps passing: the new path is named in `docs/runbooks/backup.md` (its rule); `host-core` keeps passing (its `profiles` literal is untouched — no specialisation, 16b).
6. `docs/runbooks/media-worlds.md` is the contract `## Operator` steps 5–17 read their unit names and ports from.

**Facts** (Step 0): `grep -n -i media flake.nix` → two hits (spec §2); `grep -n 'gaming.nixosModules.default\|gaming.url' flake.nix`; `sed -n '/core-backup-wiring =/,/touch \$out/p' flake.nix` and the same for `core-gaming-wiring` (the shapes copied; pasted); `grep -n 'paths = \[' -A 16 hosts/core/proton-backup.nix`; `grep -n 'thirteen' docs/runbooks/backup.md`; `grep -rn "hostAddress = \|listenPort = " hosts/` (Assumption 10). In the media clone the workspace cannot see, the option names of Assumption 19 are re-measured through the lock: after `nix flake lock`, `nix eval --json .#nixosConfigurations.core.options.services.comfyui-worlds --apply builtins.attrNames` → the option set, pasted (this is what tells the seat whether `host` and `enable` exist).

**Steps.**
1. **Red.** `nix build .#checks.x86_64-linux.core-media-wiring -L --no-link; echo exit=$?` → `error: flake … does not provide attribute 'checks.x86_64-linux.core-media-wiring'`, `exit=1`. Add the input and the check alone (no host file, no import): the build → `core-media-wiring: services.comfyui-worlds is not on core (the media module is not imported)` (or `attribute 'comfyui-worlds' missing` if `?` is evaluated on an absent option set — paste whichever). Paste both.
2. Add the module to core's list, create `hosts/core/media-worlds.nix`, the import, the backup path and exclude, the runbook bullet, `docs/runbooks/media-worlds.md` with its values from `nix eval --json .#nixosConfigurations.core.config.services.comfyui-worlds.worlds`, `… config.systemd.user.services --apply builtins.attrNames` and `nix eval --raw --expr '(builtins.fromJSON (builtins.readFile ./flake.lock)).nodes.nixpkgs-host.locked.rev'` (and media's node); regenerate MAP.
3. **Green.** `nix build .#checks.x86_64-linux.core-media-wiring -L --no-link`, `… host-core …`, `… core-backup-wiring …`, `… lint …` build. `nix build .#nixosConfigurations.core.config.system.build.toplevel -o /tmp/gn10-result` builds; `nix store diff-closures /run/current-system /tmp/gn10-result | head -60` — the **measured** delta (A2), pasted into the commit body and into `docs/runbooks/media-worlds.md` beside the prediction of `## Operator` step 2. Paste.
4. **Mutants** (revert, run, restore; each shows the named arm's message):
   - **M1 import-dropped** (remove `./media-worlds.nix` from `imports`) → arm 1.
   - **M2 lan-on** → arm 3.
   - **M3 port-shared** (`nsfw.feedPort = 8388`) → arm 4.
   - **M4 unit-wanted** (in `media-worlds.nix`: `systemd.user.services.<one comfy- unit>.wantedBy = [ "default.target" ]`) → arm 5 naming the unit.
   - **M5 seventh-host** (append `huggingface.co`) and **M5b host-dropped** → arm 7 both ways (list equality).
   - **M6 inject-added** (`inject."huggingface.co" = { header = "Authorization"; valueFile = "/nonexistent"; }`) → arm 8.
   - **M7 probe-outside-netns** (override `NetworkNamespacePath` to `""`) → arm 9.
   - **M8 env-extra** (a third `environment` entry) → arm 10.
   - **M9 backup-path-dropped** → arm 12; **M9b exclude-dropped** → arm 13.
   - **M10 runbook-port-dropped** (delete the `feedPort 8389` text) → arm 14 naming `nsfw`.
   - **M11 runbook-rev-stale** (edit one hex digit of the `media nixpkgs:` line) → arm 15.
   - **Negative control** — delete the worlds bullet from `docs/runbooks/backup.md` → `core-backup-wiring: docs/runbooks/backup.md does not name these backup paths: /home/dalhaka/comfyui/worlds` (the existing check discriminates the new path); restore.
5. **Commit.** As GN1's script; subject `generation: the worlds on core — the media input, the media broker instance, the on-demand units, the backup paths and the wiring check (test: core-media-wiring, host-core, core-backup-wiring, lint)`; commands: `nix build .#checks.x86_64-linux.core-media-wiring -L --no-link 2>&1 | tail -n 3`, `git diff --cached flake.lock | grep -c '^+.*"rev"'`, `nix eval --json .#nixosConfigurations.core.config.services.egress-broker.instances.media.allow`, `nix store diff-closures /run/current-system /tmp/gn10-result | head -n 40`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** module on core → M1; no LAN face → M2; distinct ports → M3 (fixture: two worlds); every `comfy-` unit on demand → M4 (a rule over the set); exactly six hosts, no credential → M5, M5b, M6; the probe inside the netns with exactly two variables → M7, M8; backup path and exclude → M9, M9b; the runbook names every world's port and media's pin → M10, M11; the existing backup check discriminates → negative control.

**probes:**
- media-input: `grep -c 'media.url = "git+file:///home/dalhaka/flakes/media?ref=main"' flake.nix` :: ge 1 :: Files i
- media-host-file: `test -f hosts/core/media-worlds.nix && echo 1 || echo 0` :: ge 1 :: Files
- six-hosts-exact: `nix eval --json .#nixosConfigurations.core.config.services.egress-broker.instances.media.allow | tr ',' '\n' | wc -l` :: le 6 :: Interfaces 3
- no-inject: `nix eval --json .#nixosConfigurations.core.config.services.egress-broker.instances.media.inject` :: eq {} :: Interfaces 3
- lan-off: `nix eval .#nixosConfigurations.core.config.services.comfyui-worlds.lan.enable` :: eq false :: question 3 default
- backup-bullet: `grep -c '/home/dalhaka/comfyui/worlds' docs/runbooks/backup.md` :: ge 1 :: core-backup-wiring's rule
- runbook-present: `test -f docs/runbooks/media-worlds.md && echo 1 || echo 0` :: ge 1 :: Interfaces 6

### GN11 (code, S) — the absorption's record: the GN row owns media/, the media repo row, the plan-status rows and the untyped record file

**dependsOn:** EV10, GN10
**areas:** platform, evidence, generation
**touches:** `docs/ledger/subsystems.toml`, `docs/subsystems.md`, `docs/ledger/repos.toml`, `docs/ledger/plan-status.toml`, `docs/superpowers/plans/2026-09-11-media-absorbed.md`
**acceptance:** subsystems-manifest, lint
**commit subject:** generation: the media absorption recorded — the GN row owns media/, the media repo row, the plan-status rows and the record file (test: subsystems-manifest, lint)

**Why.** Question 2(a): after GN9 lands and switch #N passes, the orchestrator's landing act merges `~/flakes/media` as the subtree `media/` (the Platform plan's Q6(b) shape, `absorb/media`, tag `absorbed/media-<rev>`, `git subtree add --prefix=media --no-squash`, one merge commit); the act has no key (PL5's rule) and this task is its record, PL6's shape (Assumption 12): the manifest row gains `media/*` so `subsystems-manifest` stays green (spec §1: "whatever it creates in this repo must be added to some row's `owns` in the same landing"), the media repo row repoints at this repo so the nine `GN` keys keep resolving against this repo's `git log` (41a: the live keys already carry their prefix; the eleven W keys freeze as history), and the superseded `2026-09-02-media-flake.md` entry leaves the GN row (spec §5 Q1). `dependsOn: EV10` because EV10's `docs/superpowers/plans/*` glob is what covers the record file and this plan (Cross-plan); `dependsOn: GN10` because the record follows the wiring.

**Base (the seat's precondition, the landing act being the orchestrator's).** `git log --oneline -1 --merges -- media` names the landing merge; `git tag -l 'absorbed/media-*'` is non-empty; `git ls-files media | wc -l` → 97 (re-measure; Assumption 18); `test -f media/flake.nix` (still present until GN12). If any is missing the seat stops with `FACTORY-RESULT status=failed` and `FACTORY-NOTES landing not found` — it never merges anything itself (GN-E).

**Files.**
- Modify `docs/ledger/subsystems.toml`, the Generation row: `owns = [ "media/*" ]`; `plans = [ "docs/superpowers/plans/2026-09-11-generation.md" ]` (the superseded entry removed — `grep -c '^### GN' docs/superpowers/plans/2026-09-02-media-flake.md` → 0 at Step 0, so no key loses its guard).
- Modify `docs/subsystems.md` — regenerated by `subsystems.py write`, never by hand.
- Modify `docs/ledger/repos.toml`, the `media` row: `path = "~/nixos-agent-env"`, `plans = "docs/superpowers/plans/absorbed/media/*.md"` (a glob matching nothing: this repo's plans are read under the `nixos-agent-env` row, so GN1–GN9, typed there with `repo: media`, resolve against this repo's `git log`, which the subtree merge now carries), and the comment `# absorbed 2026-09-xx into media/ (GN11/GN12, tag absorbed/media-<rev>); the clone is archived by the operator (plan 2026-09-11-generation.md, Operator step 20)`.
- Modify `docs/ledger/plan-status.toml` — append `[[plan]] repo = "nixos-agent-env" file = "2026-09-11-media-absorbed.md" status = "done" note = "record of the media absorption (GN11, GN12); live keys GN1–GN9 are typed in 2026-09-11-generation.md with repo: media — see the file"`; the two `repo = "media"` rows stay (their files now sit under `media/docs/superpowers/plans/`, which no row reads).
- Create `docs/superpowers/plans/2026-09-11-media-absorbed.md` — an **untyped** record (no `### KEY (kind, size)` heading anywhere): the sibling head and tag, the landing merge hash (`git log --oneline -1 --merges -- media`), the eleven landed W keys with their file `media/docs/superpowers/plans/2026-09-05-comfy-worlds.md` (measured: `grep -o '^### W[0-9a-z]*' media/docs/superpowers/plans/2026-09-05-comfy-worlds.md`), the sentence "live keys at absorption: GN1–GN9, typed in `2026-09-11-generation.md` with `repo: media`, every one `landed` on media `main` before the merge (measured: `nix develop -c python3 pkgs/evidence/tasks.py --root . json` → every `media` task `landed`)", and a pointer to `media/docs/OPERATIONS.md` as the sibling's frozen board.

**Interfaces.**
1. `nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root .` exits 0 and prints nothing; every path under `media/` resolves to `generation` by exactly one row (no `ambiguous:`).
2. `nix develop -c python3 pkgs/evidence/tasks.py --root . check` prints nothing; `… json` shows the `media` repo's tasks as GN1–GN9 only (no `W` key: the media plan files are no longer read) with every state `landed`, and every `nixos-agent-env` key exactly once (the repointed row does not re-read this repo's plans).
3. `… brief` shows no `untracked` for the record file; `grep -c '2026-09-11-media-absorbed' docs/ledger/plan-status.toml` → 1; `tasks.parse_plan(<record>)["typed"]` → `False`.
4. `docs/subsystems.md` is byte-equal to `subsystems.py write --check`'s rendering.

**Facts** (Step 0, beside the Base lines): `grep -n -A 9 '^name = "Generation"' docs/ledger/subsystems.toml` → `owns = []` and the two `plans` entries; `grep -n -A 3 'name = "media"' docs/ledger/repos.toml`; `grep -n -A 4 'repo = "media"' docs/ledger/plan-status.toml` → the two rows; `sed -n '/^### PL6/,/^### PL7/p' docs/superpowers/plans/2026-09-11-platform.md | grep -n 'absorbed'` → PL6's row shape (Assumption 12).

**Steps.**
1. **Red.** `git ls-files | nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --files /dev/stdin; echo exit=$?` → 97 lines `uncovered: media/…` (the landing act's files, EV10 having covered the rest), `exit=1`; paste the count (`… | grep -c '^uncovered: media/'`). Then, before the repo row moves: `nix develop -c python3 pkgs/evidence/tasks.py --root . json | python3 -c "import json,sys; g=json.load(sys.stdin); r=[x for x in g['repos'] if x['name']=='media'][0]; print(sorted(t['key'] for t in r['tasks']))"` → the nine GN keys plus the eleven W keys (the media row still reads the clone) — paste. Create the record file: `… brief` → `untracked_plans` names it (paste).
2. Edit the three ledgers; write the record; `nix develop -c python3 pkgs/evidence/subsystems.py write docs/ledger/subsystems.toml --files <(git ls-files) --root .`.
3. **Green.** The Step-1 validator → exit 0, nothing printed; the `json` one-liner → the nine GN keys only, and `… | python3 -c "…print(sorted(set(t['state'] for t in r['tasks'])))"` → `['landed']`; `python3 -c "import collections,json,sys; g=json.load(sys.stdin); print([k for k,v in collections.Counter(t['key'] for x in g['repos'] for t in x['tasks']).items() if v>1])"` over `json` → `[]`; `… check; echo $?` → `0`; `untracked_plans` → `[]`; `nix build .#checks.x86_64-linux.subsystems-manifest -L --no-link` and `… lint …` build. Paste all.
4. **Mutants** (revert, run, restore):
   - **M1 owns-dropped** (`owns = []` again) → 97 `uncovered: media/…`, exit 1; `subsystems-manifest` fails.
   - **M2 plans-glob-default** (drop the `plans` line from the media row) → the duplicate-key one-liner prints every key twice; `… brief` doubles the counts — the row would re-read this repo's plans as media's.
   - **M3 no-status-row** → `untracked_plans` → `['2026-09-11-media-absorbed.md']`.
   - **M4 typed-record** (add `### GNX1 (docs, XS) — x` to the record) → `check` → `tasks: 2026-09-11-media-absorbed.md/GNX1: prefix GN is reserved for Generation, whose plans are …` (G7).
   - **M5 page-hand-edited** (one character of `docs/subsystems.md`) → `subsystems.py write --check docs/subsystems.md` exits 1; `subsystems-manifest` fails at its second command.
   - **M6 superseded-entry-kept** → no check fails (the validator has no unused-entry rule, Assumption 12's EV10 note); killed by the probe `gn-plans-one` only — said so.
   - **Negative control** — `tests/evidence/test_subsystems.py::test_clean_fixture_passes` passes; add an unowned path to its fixture → fails; restore.
5. **Commit.** As GN1's script; subject `generation: the media absorption recorded — the GN row owns media/, the media repo row, the plan-status rows and the record file (test: subsystems-manifest, lint)`; commands: `git ls-files | nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --files /dev/stdin; echo exit=$?`, `git log --oneline -1 --merges -- media`, `git tag -l 'absorbed/media-*'`, `nix develop -c python3 pkgs/evidence/tasks.py --root . check; echo exit=$?`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** `media/*` owned → M1; the repointed row reads no plans twice → M2 (fixture: the duplicate-key count); the record is tracked → M3; the record is untyped → M4; the page regenerated → M5; the superseded entry gone → M6 (probe); the fixture discriminates → negative control.

**probes:**
- gn-owns-media: `grep -c '"media/\*"' docs/ledger/subsystems.toml` :: ge 1 :: Files
- gn-plans-one: `sed -n '/^name = "Generation"/,/^depends/p' docs/ledger/subsystems.toml | grep -c 'docs/superpowers/plans/'` :: le 1 :: spec section 5 Q1, the superseded entry removed
- media-row-repointed: `sed -n '/name = "media"/,/^$/p' docs/ledger/repos.toml | grep -c 'nixos-agent-env'` :: ge 1 :: Files
- record-untyped: `grep -c '^### ' docs/superpowers/plans/2026-09-11-media-absorbed.md; true` :: le 0 :: Interfaces 3
- validator-clean: `git ls-files | nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --files /dev/stdin 2>&1 | grep -c 'uncovered\|ambiguous'; true` :: le 0 :: Interfaces 1

### GN12 (code, M) — media absorbed into this flake: the outputs move onto nixpkgs-host, the inner flake and the input go

**dependsOn:** GN11
**areas:** platform, evidence, generation
**touches:** `flake.nix`, `flake.lock`, `media/flake.nix`, `media/flake.lock`, `media/checks.nix`, `media/packages.nix`, `media/modules.nix`, `hosts/core/media-worlds.nix`, `docs/runbooks/media-worlds.md`, `docs/MAP.md`
**acceptance:** comfy-worlds-unit, comfy-worlds-eval, comfy-upstream-probe-unit, media-fetch-unit, core-media-wiring, host-core, lint
**commit subject:** generation: media absorbed into this flake — the outputs move onto nixpkgs-host, the inner flake and the media input go (test: comfy-worlds-unit, comfy-worlds-eval, comfy-upstream-probe-unit, media-fetch-unit, core-media-wiring, host-core, lint)

**Why.** Decision 35b's "one repo", 43b's "absorbed subsystems move onto `nixpkgs-host`" and 42a's one lock: after GN11 the tree holds `media/` with its own `flake.nix` and `flake.lock` and this flake still reads the clone through the `media` input. This task moves the five packages, the three modules and the twenty-one checks into this flake, built on `nixpkgs-host`, and deletes the inner flake and the input, so one lock pins everything (the `core-gaming-wiring` rule). The two rules that matter are written as rules: every `${self}/<path>` in a moved check gains the `media/` prefix, and a moved check whose name collides with a host check gains the `media-` prefix — with an `assert` that refuses a collision at eval time, because `//` would silently override (r2 Judge 3 row 5).

**Base.** GN11 landed: `git ls-files media | wc -l` → 97 (re-measure); `test -f media/flake.nix`; `grep -c '"media/\*"' docs/ledger/subsystems.toml` → 1; `grep -c 'media.url' flake.nix` → 1.

**Files.**
- Create `media/packages.nix` — `{ pkgs, lib }: { comfyui = …; comfy-worlds-init = …; media-comfy = …; media-fetch-models = …; comfy-upstream-probe = …; }` — the five bodies moved verbatim from `media/flake.nix`'s `packages.${system}` block (`sed -n '/packages.${system} = {/,/^      };/p' media/flake.nix` at Step 0, pasted), every relative path unchanged (they are relative to `media/`, where the file lives); any `let` helper the block uses moves with it.
- Create `media/modules.nix` — `{ comfyui = import ./nixosModules/comfyui.nix; comfyui-worlds = import ./nixosModules/comfyui-worlds.nix; default = { imports = [ ./nixosModules/comfyui.nix ./nixosModules/comfyui-worlds.nix ]; }; }` (the three names of Assumption 18).
- Create `media/checks.nix` — `{ self, pkgs, lib, system, mediaPkgs, mediaModules }: { … }`: the twenty-one check bodies moved verbatim from `media/flake.nix` with (i) every `${self}/<p>` rewritten `${self}/media/<p>` (Step 0 measures the count — the r2 judges counted nine), (ii) every `self.packages.${system}.<n>` → `mediaPkgs.<n>`, `self.nixosModules.<n>` → `mediaModules.<n>`, (iii) every check name that is also a host check name prefixed `media-` (Step 0: `comm -12 <(host names) <(media names)` → `lint`, so `lint` → `media-lint`; any other collision the measurement shows is prefixed the same way and named in the commit body); the `let` helpers the checks use (`mkHarness`, `mkNegative`, `lintTools`, whatever Step 0 lists: `grep -n '^      [a-zA-Z]* =' media/flake.nix`) move into this file's `let`.
- Modify `flake.nix` — remove `inputs.media` and the `media` outputs argument; add, in the outputs `let`, `pkgsHost = import nixpkgs-host { inherit system; config.allowUnfree = true; };` unless a binding of that name exists (`grep -n 'pkgsHost' flake.nix` → 0 today, Assumption 11's outputs block), `mediaPkgs = import ./media/packages.nix { pkgs = pkgsHost; inherit (nixpkgs) lib; }`, `mediaModules = import ./media/modules.nix`; `packages.${system}` gains the five names (`inherit (mediaPkgs) comfyui comfy-worlds-init media-comfy media-fetch-models comfy-upstream-probe;` — the collision check: none of the five exists in the host set, measured); `nixosModules` gains `comfyui = mediaModules.comfyui; comfyui-worlds = mediaModules.comfyui-worlds;`; `checks.${system}` becomes `let hostChecks = { <the existing literal> }; mediaChecks = import ./media/checks.nix { inherit self pkgs lib system mediaPkgs mediaModules; }; in assert builtins.intersectAttrs hostChecks mediaChecks == { }; hostChecks // mediaChecks` (the guard is an eval-time refusal with the message `assertion failed`; the collision set is printed by the probe below); `nixosConfigurations.core`'s module list uses `mediaModules.comfyui-worlds` in place of `media.nixosModules.comfyui-worlds`; `core-media-wiring`'s last arm becomes `!(lockData.nodes ? media)` with the message `core-media-wiring: flake.lock still carries a media node` and gains `!(builtins.pathExists ./media/flake.nix)` with `core-media-wiring: media/flake.nix must not exist (one flake, one lock)`; the `media nixpkgs:` runbook arm goes.
- Delete `media/flake.nix` and `media/flake.lock` (`git rm`).
- Modify `flake.lock` — `nix flake lock` removes the `media` node and its nixpkgs node; `nixpkgs-host`'s rev is unchanged (the gaming check's equality keeps proving it).
- Modify `hosts/core/media-worlds.nix` — no import change is needed (the module reaches core through `flake.nix`'s list); if the module's `package` option defaults to a path-relative derivation that no longer resolves, set `package = <the flake's comfyui>` through `specialArgs` (the seat measures at Step 0; the mechanism used is named in the commit body).
- Modify `docs/runbooks/media-worlds.md` — the `media nixpkgs:` line becomes `media builds on nixpkgs-host <rev>`; the operator's archive step (Operator 20) added.
- Modify `docs/MAP.md` — regenerated (the Checks section gains the twenty-one names; `lint` diffs it).

**Interfaces.**
1. `nix eval --json .#checks.x86_64-linux --apply builtins.attrNames` lists every host check plus the twenty-one media checks (with `media-lint` for `lint`); `nix eval --json .#packages.x86_64-linux --apply builtins.attrNames` gains exactly the five; `nix eval --json .#nixosModules --apply builtins.attrNames` gains `comfyui` and `comfyui-worlds`.
2. Every media package and check is built from `nixpkgs-host`: `nix derivation show .#packages.x86_64-linux.comfyui` names `pkgsHost.python3`'s derivation among its inputs and not `nixpkgs`'s (the two probes below).
3. `git ls-files media | grep -c '^media/flake\.'` → 0; `nix flake metadata --json | nix develop -c jq '.locks.nodes | has("media")'` → `false`.
4. A name collision between a host check and a media check is an eval error (the `assert`), never a silent override.
5. `nixosConfigurations.core` evaluates and builds as before GN12 with the same units and ports (`nix eval --json .#nixosConfigurations.core.config.services.comfyui-worlds.worlds` byte-equal before and after).

**Facts** (Step 0): `grep -n '\${self}' media/flake.nix` → the occurrences to rewrite (count pasted); `nix eval --json --impure --expr 'builtins.attrNames (builtins.getFlake (toString ./media)).checks.x86_64-linux' | tr ',' '\n' | wc -l` → 21 (from the still-present inner flake), and the same for `packages` → 5, `nixosModules` → 3; `comm -12 <(nix eval --json .#checks.x86_64-linux --apply builtins.attrNames | tr -d '[]"' | tr ',' '\n' | sort) <(nix eval --json --impure --expr 'builtins.attrNames (builtins.getFlake (toString ./media)).checks.x86_64-linux' | tr -d '[]"' | tr ',' '\n' | sort)` → `lint`; `grep -n 'pkgsHost\|allowUnfree' flake.nix` → 0 lines; `grep -n 'nixpkgs.url\|nixpkgs-host.url' flake.nix media/flake.nix` → the pins (Assumption 25).

**Steps.**
1. **Red.** `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link; echo exit=$?` → `does not provide attribute`, `exit=1`. The measurement 43b asks for, before any move: `nix build --impure --expr '(import ./media/packages.nix { pkgs = import (builtins.getFlake (toString ./.)).inputs.nixpkgs-host { system = "x86_64-linux"; config.allowUnfree = true; }; lib = (import (builtins.getFlake (toString ./.)).inputs.nixpkgs-host { system = "x86_64-linux"; }).lib; }).comfyui' --no-link -L 2>&1 | tail -n 20` after writing `media/packages.nix` — if the ComfyUI closure does not build on `nixpkgs-host` (a torch or CUDA version the pinned deps refuse), the task stops here with `FACTORY-RESULT status=failed` and `FACTORY-NOTES nixpkgs-host drift: <the last error line>` — question 2(b) then applies and the operator decides; nothing is patched to make it build. Paste the tail either way.
2. Write the three `media/*.nix` files; rewrite `flake.nix`; `git rm media/flake.nix media/flake.lock`; `nix flake lock`; regenerate MAP and the runbook line.
3. **Green.** The seven acceptance checks build by name; `nix eval --json .#checks.x86_64-linux --apply builtins.attrNames | tr ',' '\n' | wc -l` → the Step-0 host count + 21; `git ls-files media | grep -c '^media/flake\.'; true` → `0`; `nix flake metadata --json | nix develop -c jq '.locks.nodes | has("media")'` → `false`; the two derivation probes; `nix build .#nixosConfigurations.core.config.system.build.toplevel -o /tmp/gn12-result` and `nix store diff-closures /run/current-system /tmp/gn12-result | head -n 60` (the measured delta for switch #N+1, pasted). Paste all.
4. **Mutants** (revert, run, restore):
   - **M1 inner-lock-left** (`git add media/flake.lock` back) → the probe `no-inner-flake` reads 1 and `core-media-wiring` throws `media/flake.nix must not exist` only for the `.nix`; so this mutant restores both files → the check throws; the lone `.lock` is killed by the probe — said so (r2 erratum 6).
   - **M2 path-unrewritten** (one `${self}/tests/…` left) → that check fails `error: path '…/tests/…' does not exist`.
   - **M3 lint-not-renamed** → `nix flake show` → `error: assertion … failed` (the guard); with the `assert` removed the same mutant is silent — the seat shows both, restores the assert.
   - **M4 built-on-agent-pin** (`pkgs = pkgs` in place of `pkgsHost`) → the probe `built-on-host-pin` reads 0 and `not-on-agent-pin` reads ≥ 1.
   - **M5 package-dropped** (one of the five omitted) → `packages` attr count −1; `comfy-worlds-eval` (which builds the wrapper) fails on the missing attribute.
   - **M6 media-node-left** (skip `nix flake lock`) → `core-media-wiring: flake.lock still carries a media node`.
   - **Negative control** — `core-gaming-wiring` builds; edit `nixpkgs-host`'s `rev` in `flake.lock` by one digit → it fails its lock arm; restore.
5. **Commit.** As GN1's script; subject `generation: media absorbed into this flake — the outputs move onto nixpkgs-host, the inner flake and the media input go (test: comfy-worlds-unit, comfy-worlds-eval, comfy-upstream-probe-unit, media-fetch-unit, core-media-wiring, host-core, lint)`; commands: `git ls-files media | grep -c '^media/flake\.'; true`, `nix flake metadata --json | nix develop -c jq '.locks.nodes | has("media")'`, `nix eval --json .#checks.x86_64-linux --apply builtins.attrNames | tr ',' '\n' | wc -l`, `nix store diff-closures /run/current-system /tmp/gn12-result | head -n 40`; trailers; commit.

**Tests (assertion → mutant; fixture → discriminating row):** no inner flake → M1 (probe + check); every `${self}` path rewritten → M2; collisions refused → M3 (fixture: the one real collision, `lint`); built on `nixpkgs-host` → M4 (the two derivation probes); the five packages → M5; one lock → M6; the gaming lock rule still discriminates → negative control.

**probes:**
- no-inner-flake: `git ls-files media | grep -c '^media/flake\.'; true` :: le 0 :: Interfaces 3
- no-media-lock-node: `nix flake metadata --json | nix develop -c jq '.locks.nodes | has("media")'` :: eq false :: Interfaces 3
- media-lint-renamed: `nix eval --json .#checks.x86_64-linux --apply builtins.attrNames | grep -c '"media-lint"'` :: ge 1 :: Files, the collision rule
- built-on-host-pin: `nix derivation show .#packages.x86_64-linux.comfyui | grep -c "$(nix eval --raw --impure --expr '(import (builtins.getFlake (toString ./.)).inputs.nixpkgs-host { system = "x86_64-linux"; config.allowUnfree = true; }).python3.drvPath')"` :: ge 1 :: Interfaces 2, decision 43b
- not-on-agent-pin: `nix derivation show .#packages.x86_64-linux.comfyui | grep -c "$(nix eval --raw --impure --expr '(import (builtins.getFlake (toString ./.)).inputs.nixpkgs { system = "x86_64-linux"; }).python3.drvPath')"; true` :: le 0 :: Interfaces 2
- five-packages: `nix eval --json .#packages.x86_64-linux --apply builtins.attrNames | grep -o 'comfyui"\|comfy-worlds-init"\|media-comfy"\|media-fetch-models"\|comfy-upstream-probe"' | wc -l` :: ge 5 :: Interfaces 1
