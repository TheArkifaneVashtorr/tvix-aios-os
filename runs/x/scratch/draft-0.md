# Plan 2026-09-11 — Generation (`GN`): media on core, the manifest row, the probe's egress, and the contract for the media-side work

**Spec (context block):** `docs/context/generation.md` — §1 ownership, §2 the code, §3 what binds, §4 the record, §5 the eight open questions the plan must answer, §6 out of scope. `wc -w docs/context/generation.md` → `3636` (M; `target.md`).
**Charter:** `docs/concepts/2026-09-09a-redesign-charter.md` — the Generation row (`sed -n '52p'`: "`~/flakes/media` (ComfyUI worlds, the feed, Caddy sites, the lab repo), the prompt mutator | generation, Sonnet gate | GN | 14–17"), increment 3 (`sed -n '175,181p'`: "comfy-worlds sub-projects 2 and 3, the on-demand units and Caddy on core, the rules mutator, media absorbed (`GN`)"), increment 4 (`sed -n '183,186p'`: "LAN access with per-site auth and the amended brief §10 and loopback assertion").
**Decisions:** `docs/decisions/2026-09-09-redesign-answers.md` — 14c, 15a, 16b, 17c (`grep -n '^| 1[4-7] ' …`), 18b, 20b, 31a, 35b, 43b, 44, 48a; `docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md` ("The media flake stays brokered").
**Program constraints:** the binding subset of G1–G12 quoted verbatim in `## Global Constraints` (`factory-brief` reads that H2 from this file: `global_constraints=$(factory_extract_h2 "$plan" '## Global Constraints')`); the area word is `generation:`.
**Manifest row:** `awk '/name = "Generation"/,/^depends/' docs/ledger/subsystems.toml` → `name = "Generation"`, `prefix = "GN"`, `area = "generation"`, `gate = "sonnet"`, `owns = []`, `plans = [ "docs/superpowers/plans/2026-09-02-media-flake.md", "docs/superpowers/plans/2026-09-11-generation.md", ]`, `depends = ["Platform"]`.
**Plan file at dispatch:** `docs/superpowers/plans/2026-09-11-generation.md` — the name the row carries; any other basename is refused by the reserved-prefix guard (measured: `check --draft /tmp/draft-scratch/draft-0.md` prints `tasks: draft-0.md/GN1: prefix GN is reserved for Generation, whose plans are …` for every key; the same file copied to `2026-09-11-generation.md` passes — Assumption 19).
**Anchor:** every fact below was measured on 2026-09-27 in this checkout at `git log -1 --format='%h %ci %s'` → `c9c5bd7 2026-09-26 14:15:03 -0500 snapshot`. The sibling is not readable here: `ls /home/dalhaka/flakes` → `No such file or directory`. Every media-side fact is therefore quoted from the context block's own measurement (2026-09-10, media HEAD `1618638`) or from a judgement file in this tree, is marked so, and is re-measured by the seat at Base (G11). This checkout's `nix` is a shim (Assumption 24), so every `nix eval` and `nix build` in this plan is the seat's on `core`; lock-file facts were measured with `jq`.
**Author:** Fable 5.1, `draft-packet` workflow, effort max.
**Status:** DRAFT under `/tmp/draft-scratch/`; nothing under `docs/superpowers/plans/`; nothing dispatched.

**What this plan is, in one paragraph.** Decision 16b puts the worlds' on-demand units on `core`; the measured house shape for that is a read-only flake input with a lock-parity assertion (`gaming`). The sibling's tree is not readable from a nixos-agent-env checkout, so this plan types only what it can prove from this tree plus one media-side task whose facts are a rev and a check list: the manifest row (GN1), media's nixpkgs onto the host pin (GN2, in media), media on core with no LAN face and no probe timer (GN3), and the probe's egress decision recorded (GN4). Sub-projects 2 and 3 and the rules mutator are media code; they are typed against the tree that holds them (31a) with the contract this plan fixes in `## Not in this plan`, and the absorption is the operator's question 1.

## Operator questions

Three (rubric row 14), each decidable in one letter, each with a recommendation and the default that applies in silence; the last sentence of each names what the other answer changes.

- **Q1 — when media is absorbed** (spec §5.6; decisions 35b "one sibling per task, each with its own build gate and switch", 44, 48a "subtree-style merge"; charter increment 3 lists "media absorbed"). (a) now, before anything else — the subtree lands under `media/`, GN3 wires the module from that path and this plan gains the flake re-plumb; (b) after sub-projects 2 and 3 — this plan wires media through a pinned flake input (the `gaming` shape, `flake.nix`: `gaming.url = "git+file:///home/dalhaka/flakes/gaming?ref=main";`), the media-side work lands in the sibling's own tree where its 21 checks and fixtures are, and one subtree act closes the increment; (c) keep the split. **Recommend (b); default (b).** Reasons: the input shape is measured and gated (`core-gaming-wiring`); a subtree absorbed first sits inert under `lint` for the whole increment (Platform anticipated exactly that with PL8); the re-plumb of a 892-line `flake.nix` (block §1) is planned against the tree it lands in (31a). Effect: (a) is a re-draft — GN3's input becomes the path `./media`, GN1's row gains `"media/*"`, and the landing act is Platform's Q6(b) recipe with `--prefix=media` and the tag `absorbed/media-<rev>`; (c) makes the absorption bullet of `## Not in this plan` permanent and changes nothing else.
- **Q2 — the upstream probe's egress** (spec §5.3; brief §3 invariant 3; the 2026-09-02 decision's conclusion "The media flake stays brokered (it is closer to an agent than to an app)"; the media design's `:252-255` claims a carve-out the decision does not grant). (a) record an explicit exception: the probe (no model, no key, six public read-only hosts, weekly) may fetch directly and its timer may be enabled on core; (b) no exception: the timer stays off core — GN3 sets `systemd.user.timers."comfy-upstream-probe".enable = false` and `host-core` asserts it — until a media-side task runs the probe inside the `media` broker namespace; a hand run from `~/flakes/media` is the operator's own act under the 2026-09-02 reading. **Recommend (b); default (b).** Reasons: the decision of record grants exceptions to the operator's desktop apps only; the probe proposes dependency bumps to a tree agents execute; and "broker it" cannot mean "set `HTTPS_PROXY` on a user timer" — a broker's listener answers only from inside its namespace (`nixosModules/egressBroker.nix`: `ip daddr ${i.hostAddress} tcp dport ${toString i.listenPort} iifname != "veb-${name}" drop`; redesign-answers §6: "`curl -x` against either from the host returns `http=000`"), so the closing task is a unit in the namespace, typed on the media side. Effect: (a) flips one line of GN3's stanza (the `enable = false` line goes), one `host-core` assertion (the timer must exist and be enabled) and GN4's text (an exception with its bound); nothing else.
- **Q3 — Caddy's LAN face in this plan** (decisions 14c "Caddy fronts the worlds as designed", 16b "host-level Caddy wired into core", 20b "LAN now … brief §10 and the loopback assertion amended in the operator's words"; charter increment 4 carries "LAN access with per-site auth and the amended brief §10 and loopback assertion"; `docs/context/isolation.md`: "`docs/brief.md` has no §10", "The loopback assertion itself lives in `nixosModules/helm.nix`, a Helm-owned file"; `nixosModules/helm.nix`: `"services.helm.listen must be loopback … Helm is localhost-only until Phase 10"`). (a) `services.comfyui-worlds.lan.enable = false` now; Caddy, the two site names and the password files come with the increment-4 amendment; (b) `lan.enable = true` now. **Recommend (a); default (a).** Reasons: 20b's own text ties LAN to the amendment; the amendment is Helm's and Isolation's, not this plan's; the feed is reachable on the operator's own desktop at `127.0.0.1:<feedPort>` meanwhile (Helm links it, 15a). Effect: (b) is a re-draft, not a switch — the stanza gains `lan.enable = true` and two `worlds.<w>.host` names (DNS names are the operator's), the two `/var/lib/comfy-secrets/comfy-<w>.users` files become A3 items, 443 opens and assertion four of GN3 flips, and the amendment must land first.

## Spec-to-task map

| Spec item | Where it lands |
|---|---|
| §5.1 the plan file the manifest names — a precondition; "tidying: the superseded `2026-09-02-media-flake.md` entry still stands" | precondition met (`plans` names this file); the tidy → **GN1** |
| §5.2 WH1 and WH2 are typed but invisible to the queue | WH1 (host wiring) superseded by **GN3**, typed under `HEADING_RE` in this repo with `areas:`; WH2 (the Helm tile) → `out:` Helm's — `pkgs/helm/collect.py` is Helm-owned (`docs/ledger/subsystems.toml` Helm `owns = [ "pkgs/helm/*", …`) and the spec's §6 assigns the tile to `HM` |
| §5.3 the probe's egress carve-out | **Q2**; the decision recorded by **GN4**; the interim enforced by **GN3** (the disabled timer, asserted) |
| §5.4 what "rules" means for the mutator | decided in `## Decisions this plan makes`; the code → `out:` media-side (the contract in `## Not in this plan`) |
| §5.5 where the feed's state lives | decided (`worlds/<world>/feed.sqlite`, the design's reservation); sub-projects 2/3 → `out:` media-side with the contract |
| §5.6 how far "media absorbed" goes | **Q1**; under the default the absorption follows sub-projects 2/3 (`## Not in this plan`) |
| §5.7 UNVERIFIABLE: media's `nix flake check -L` green at `1618638` | **Assumption 15**; measured by **GN2** Step 0 |
| §5.8 UNVERIFIABLE: the live state of `comfy-upstream-probe.timer` | **Assumption 16**; **GN3** disables it by option and asserts; `## Operator` step 5 reads it after the switch |
| §1 consequence 1: what this plan creates here is added to a row's `owns` in the same landing | **GN1** pre-declares the one new path this plan creates outside a covered glob (`docs/decisions/…`); `hosts/core/media-worlds.nix` is covered by Platform's `"hosts/*"` |
| §1 consequence 2: never assume a green `subsystems-manifest` baseline | **GN1** `dependsOn: EV10` (the task that turns it green, `ready` today) |
| charter: "the on-demand units … on core" (16b) | **GN3** (after **GN2**, the parity rule) |
| charter: "and Caddy on core" (14c/16b) | **Q3**; `out:` under (a) — Helm/Isolation's amendment first |
| charter: "comfy-worlds sub-projects 2 and 3", "the rules mutator" (15a, 17c) | `out:` — media code; typed against the media tree with this plan's contract (`## Not in this plan`); reason: the sibling is unreadable from this checkout, so a section typed here would be a topic list or invented facts |
| charter: "media absorbed" (35b, 44, 48a) | **Q1**; `out:` under (b) until sub-projects 2/3 land |
| decision 18b, the engagement counts (board: "GN8 … POSTs HM8's body to `http://127.0.0.1:7710/v1/engage`") | `out:` — the feed-side POST is part of sub-project 2 (media); the contract is fixed below |
| §4 open claim `aimdo-native-load-unmeasured` | `## Operator` step 6 (A8) |
| §6 out-of-scope items (Helm's tile, the `proposals` stream, the parser, `factory-review`'s trailer, local weights, netns confinement of a world, the generation lab) | `out:` as the spec assigns them (`## Not in this plan`) |

Not in the map: nothing this plan types lacks a spec row above.

## Decisions this plan makes

Each with its reason and the alternative refused; none is the operator's (those are Q1–Q3).

1. **WH1 is superseded, not re-typed as `WH`.** GN3 carries the wiring under the parseable grammar with `**areas:** generation, platform, evidence` (measured at draft: `spanned_areas` of GN3's touches → `platform`, `evidence`; without the line `check` refuses). Alternative — re-type `WH1` in the media plan file with `**repo:** nixos-agent-env` — refused: the board would render a foreign key under Generation's area and the key would carry no `GN` prefix (G7).
2. **The mutator's "rules" are a `[mutate]` table in the world's lab `manifest.toml`**, the file the design already gives each world (`worlds/<world>/lab/` holds `prompts/`, `manifest.toml` and the ComfyUI `user` dir — block §1), read by a `comfy-mutate` command in `pkgs/comfy-worlds` that rewrites the four axes loose-ends Q17 names ("token swaps, LoRA strengths, samplers, seeds") into a copy of the world's workflow JSON and enqueues it; a rule that can never fire is an error, never a silent skip, and a dry run with a fixed seed is byte-identical twice. Alternative — the grammar in Nix configuration (invariant 5) — refused: prompt text is local-only data (Q17's own reasoning), not routing policy. Typed on the media side with this contract.
3. **The feed's state is `worlds/<world>/feed.sqlite`**, rebuildable from `out/*.png` (block §5.5: the design reserves it "for sub-project 2 (index, rebuildable)"). Alternative — the evidence store — refused: the store carries counts and verdicts (EV14: "counts, never content"); feed rows are prompts.
4. **The engagement counts leave the feed as a loopback POST to Helm and never touch the store.** The board's line of record (`docs/OPERATIONS.md` START HERE, 2026-09-14): "GN8 was redesigned … the feed no longer writes the evidence store; it POSTs HM8's body to `http://127.0.0.1:7710/v1/engage` (loopback-only, drops on error) because the evidence draft's EV14 makes keyed `replace_stream` the stream's only verb and the helm draft assigns the feed-side POST to GN". The body is EV14's row (`docs/superpowers/plans/2026-09-11-evidence.md`, EV14 Interfaces 1–5): `day` (`YYYY-MM-DD`), `surface` in `("home", "feed", "seats")`, `opens`, `dwell_s`, `feed_likes` non-negative ints, no other field; the feed sends `surface = "feed"`.
5. **Order.** GN2 before GN3 (the parity rule, Assumption 7); GN1 before GN4 (the row before the file); EV10 before GN1 (the green baseline). Two waves, two groups each.

## Global Constraints

Quoted verbatim from `docs/superpowers/plans/2026-09-09-program.md` `## Global Constraints` (`sed -n '35,46p'`), the subset the seat needs; where a constraint enumerates Program's own tasks, this plan's binding follows in italics. Not quoted: G3 (the trailers ride in the driver's WORKSPACE RULES block), G7 (enforced by `tasks.py check` before dispatch), G8 (no task here copies, prints or redirects any credential), G10 (module headers here are `_:`; no new language).

- **G1 Build-only.** Never `sudo`, `nixos-rebuild`, `systemctl start|stop|restart|enable|kill`, basket mount or teardown. The operator switches; a task that needs the live system to change says so in its `## Operator` line and stops.
- **G2 Red first.** Every check or test a task adds is shown failing before the change that makes it pass, and the red output is pasted in the commit body. A load-bearing test counts only once it has failed (CLAUDE.md).
- **G4 Subject.** `<area>: summary (test: <check names>)`, the area being the subsystem's prefix in lower case once PR1 lands (`evidence:`, `factory:`, `isolation:`, `knowledge:`, `program:`), the check names being exactly the task's `acceptance` list. Guarded twice: the workspace's `commit-msg` hook that `factory-ws` installs (`tools/factory/seat/factory-ws:131-136`, `factory-commit-msg.sh`) and the gate's convention section, which compares the subject byte for byte with the section's `commit subject` line. *Here the area word is `generation:`.*
- **G5 Touches.** Edit only the files the task's `touches` names; a new file is named there too. An undeclared touch demotes the result (`factory-task:857-861`). `git add` every new file before any `nix build` (flakes see tracked files only). **One standing exemption, added 2026-09-10 after it was flagged twice:** the *derived queue block* of `docs/OPERATIONS.md`, and nothing else in that file, when the pre-commit's G8c forces its regeneration — G6 orders that regeneration, so listing the file in every task's `touches` would be noise and omitting it made the gate read a forced, derived, machine-written hunk as an undeclared touch (HH3's minor, PR1's MAJOR). A gate treats a queue-block-only diff there as declared; any other hunk in that file is an undeclared touch as before, and board prose stays the orchestrator's (the rule that refused W6b at the integrator). **`docs/MAP.md` is exempt on the same ground and for the same reason** (KN1's minor): `lint` asserts it is current (`flake.nix:1081-1086`), so any task that adds or renames a module, package, check or test must run `python3 pkgs/evidence/repomap.py --root . write` and commit the result whether or not its `touches` names the file. Both exemptions cover *derived* files a check or hook forces; neither excuses a hand edit. *Re-measured here: the MAP assertion is the lint block's `diff -u flake-checks map-checks || { echo "lint: docs/MAP.md Checks section differs …` line and `python3 pkgs/evidence/repomap.py --root . check`; MAP's `## Hosts` section lists every `hosts/core/*.nix` file, so GN3's new host file changes MAP and names it in `touches`.*
- **G6 Commit route.** `nix develop -c git commit -F <msgfile>` on `task/<KEY>`; one commit per task. **A fix round that starts by cherry-picking its predecessor folds that cherry-pick into its own single commit** (`git cherry-pick -n`, or `git reset --soft` back to the base before committing) — added 2026-09-10 after the instruction proved ambiguous: PR1b's seat folded and PR1c's did not, and `factory-task:757` demoted the second for claiming one commit where the branch carried two. The chain's history lives in the plan and the reviews, not in a stack of replayed commits on one task branch. If the pre-commit refuses only on G8c (a stale board queue block), regenerate with `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board` and include the block in the same commit; never `--no-verify`. *Amended for this plan (DF13, HM7c, 2026-09-15): the seat never runs `write-board` by hand, never edits `docs/OPERATIONS.md`, and never merges `main` into its branch. The pre-commit already regenerates the queue block itself (`githooks/pre-commit`: `python3 pkgs/evidence/tasks.py --root . write-board --board docs/OPERATIONS.md --quiet`) and G5 declares that hunk. A refusal that survives that regeneration is reported as `FACTORY-NOTES board-stale: <the hook's line>` with `status=partial`; the orchestrator regenerates at integration. Merging `main` is the integrator's step (`## Dispatch`, landing step 2), never the section's.*
- **G9 Areas.** From EV2 on, a task whose `touches` fall in two subsystems declares `**areas:**` with both; `tasks.py check` refuses it otherwise. **EV2 landed this on 2026-09-10 (`f31b8bb`); it is enforced in code, not by hand** (`pkgs/evidence/tasks.py:1823-1834`). The refusal fires only while a task's derived state is `ready`, `blocked`, `ran` or `running`, so a landed key is never refused retroactively, and it exempts exactly the twenty-five keys in `docs/ledger/areas-grandfather.toml` — a list frozen at `dbedfe9`, so a key typed later is refused like any other. Note the grandfather ledger is read from the repo's live path rather than the tree under `--root`, so inside a workspace it exempts nothing (`BUG-ledger-read-from-live-path`): declare `**areas:**` rather than relying on the exemption.
- **G11 Numbers.** Every integer a task pastes (row counts, line numbers, test counts) is re-run at commit time, not copied from this plan (concept 2026-09-08g). Guarded by the gate: the review rubric's "correct facts" row re-runs the commit body's commands, and a pasted integer that does not reproduce is a MAJOR (the record's `wrong-fact` class in `docs/ledger/plan-defects.toml`). *Here every media-side fact carries its date and rev and is re-measured at Base; a Base that contradicts the plan stops the task with the measurement pasted (`status=partial`), never an invented value.*
- **G12 Invariants** (brief §3, Assumption 13, re-ratified after the audit per decision 55a): every task here is written against the six verbatim. Where they bind: EV1 reads the broker's usage log locally and writes only the local store (3: nothing leaves the machine; 5: the timer is Nix configuration); EV5 changes a validator, never a credential field (2); IS1 changes no lane boundary and injects nothing (2, 3); IS2 reads and writes documents only, stores and redirects nothing (2, 3, 6); PR1, EV2, EV3, EV4, EV6, FA1, KN1 are configuration and ledgers reviewable in a diff (5); no task promotes agent-authored code between baskets (6); no task touches basket mounting (1) or adds imperative setup (4). *Here: GN3 opens no port, adds no broker instance and injects nothing (3: every world unit stays loopback-only and the probe's timer is off — Q2, Q3); GN2 changes a pin only (4: the closure stays reproducible from `flake.lock`; 5: reviewable in a diff); GN1 and GN4 are a ledger row and a decision text (5); no task touches a basket (1), a credential (2) or promotes code between baskets (6). The rule that binds the media-side work is quoted in `## Not in this plan` (invariant 3: the probe runs inside the namespace or not at all).*
- **The commit body is produced, never typed** (the recipe of DF8d; `docs/superpowers/plans/2026-09-11-defects.md` is absent from this tree — `ls docs/superpowers/plans/2026-09-11-defects.md` → `No such file or directory` — so the recipe is restated here). In the workspace create an untracked scratch directory `.factory-scratch/` (never `git add` it) holding `body.sh`:

  ```bash
  #!/usr/bin/env bash
  # body.sh <subject> <cmdfile> <trailerfile>: runs each command of <cmdfile>
  # in order and appends "$ <cmd>", its output and exit code; then the trailers.
  set -u
  printf '%s\n\n' "$1"
  while IFS= read -r cmd; do
    [ -n "$cmd" ] || continue
    printf '$ %s\n' "$cmd"
    out=$(bash -c "$cmd" 2>&1); rc=$?
    printf '%s\n(exit %s)\n\n' "$out" "$rc"
  done <"$2"
  cat "$3"
  ```

  `cmdfile` lists, one per line, exactly the commands the section's Steps name for the body (the red, the greens, each mutant's kill command with its revert, the probes); `trailerfile` holds the two trailer lines copied from the WORKSPACE RULES block. Commit with `nix develop -c git commit -F .factory-scratch/msg.txt` after `bash .factory-scratch/body.sh "<the section's commit subject>" .factory-scratch/cmds.txt .factory-scratch/trailers.txt > .factory-scratch/msg.txt`. A body line that is not a command's own output is a finding.
- **Media-side task (GN2).** The workspace is a clone of `~/flakes/media` on `task/GN2`; every command runs inside it; `nix flake check -L` there is the gate; the workspace's `commit-msg` hook applies; the seat never reads or writes `~/nixos-agent-env`, and no nixos-agent-env seat writes under `~/flakes/media`.
- **The media input is read-only from this repo:** `git+file://` pinned by ref, no `follows` (brief §8; the `gaming` precedent), the lock's rev asserted equal to `nixpkgs-host`'s (43b).
- No secrets in the repo; no `/var/lib/secrets` path, no key and no token in anything this plan adds; no password file is created (Q3(a)).
- **Every `nix eval` and `nix build` in this plan runs on `core`** (a seat workspace or the operator); none was run at draft time (Assumption 24).

## Assumptions

Measured on 2026-09-27 at `c9c5bd7` in this checkout unless the line says otherwise; re-run before dispatch and at commit (G11).

1. `git log -1 --format='%h %ci %s'` → `c9c5bd7 2026-09-26 14:15:03 -0500 snapshot`; `git log --since=2026-09-04 --format='%ci%x09%s' | wc -l` → `1` (the snapshot squashes history; `git show <sha>` of older commits is unavailable here).
2. `ls /home/dalhaka/flakes` → `No such file or directory`; `readlink -f /home/dalhaka/nixos-agent-env` → this checkout. `tasks.py --root . json` reads `media` as `0` tasks at `/root/flakes/media` (absent) — the brief's `| media | 0 | 0 |…` row. On core the row is `~/flakes/media` with the eleven landed W keys (block §4).
3. The manifest row — the header's `awk` — reads `owns = []` and two `plans` entries. `grep -c '^### ' docs/superpowers/plans/2026-09-02-media-flake.md` → `4`, all `### Task N…` (untyped); `grep -n -A3 'file = "2026-09-02-media-flake.md"' docs/ledger/plan-status.toml` → `status = "superseded"`, note "executed as ~/flakes/media's own plan copy; media rework closed 2026-09-03" (and the media-repo row, `status = "superseded"`, "by 2026-09-02-media-nix-native.md").
4. `nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root .; echo exit=$?` → 27 `uncovered:` lines, `exit=1`: nine `docs/context/*.md`, `docs/ledger/areas-grandfather.toml`, the three landed batch plans `docs/superpowers/plans/2026-09-11-{evidence,factory,platform}.md`, and fourteen artefacts of this snapshot only (`SNAPSHOT.md`, `evidence/*`, `tools/cloud/*`). The live tree carries the first thirteen; EV10's glob covers all thirteen (`docs/superpowers/plans/2026-09-11-evidence.md` EV10 Files (iii)–(iv)). `git ls-files | wc -l` → `855` here.
5. Media's surface, quoted from the block (§2, 2026-09-10 at `1618638`): nixosModules `comfyui`, `comfyui-worlds`, `default`; five packages; 21 checks — `lint`; `comfyui-package`, `comfyui-eval`, `comfyui-cliploader-krea2`, `comfyui-startup-clean`, `comfyui-vm`, `comfyui-assertion-negative-{broker,gpu,listen,listen-address,token}`; `comfy-worlds-eval`, `comfy-worlds-unit`, `comfy-worlds-vm`, `comfy-worlds-assertion-negative-{hosts,name,password-path,ports}`; `media-fetch-unit`, `media-fetch-bats`; `comfy-upstream-probe-unit`. `services.comfyui-worlds` options: `operatorUser`, `root`, `package`, `cpuOnly`, `worlds` (per world `comfyPort`/`feedPort`/`host`), `lan` — no `enable` in that list; `lan.enable` is the LAN switch (`docs/reviews/plan-judgements/2026-09-14-batch-generation.md`, erratum 23: "Assumption 9 (verified: `lan.enable = false` renders no Caddy)"). The probe runs from `comfy-upstream-probe.timer`, user scope, Sunday 04:00 (block §2). Media's nixpkgs rev at `1618638`: `ac62194c…` against the host's `a5cc6f2c…` (`docs/reviews/plan-judgements/2026-09-12-batch-generation.md`, Judge 3 row 2: "the two nixpkgs revs (`a5cc6f2c…` vs `ac62194c…`)"); the full old rev is the one `flake.nix`'s own comment names as the former host pin: `sed -n '12p' flake.nix` → `# nixpkgs-host pin (ac62194c3917, 2026-01-02; pnpmConfigHook landed in`.
6. `grep -n 'nixpkgs-host.url' flake.nix` → `6:    nixpkgs-host.url = "github:NixOS/nixpkgs/a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4";`; `nix develop -c jq -r '.nodes["nixpkgs-host"].locked.rev' flake.lock` → `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4`. `grep -n -i 'torch\|comfy\|cu128' docs/reviews/2026-09-05-release-upgrade-26.05.md` → no hits: ComfyUI's torch-bin at the host rev is unmeasured (GN2 measures it).
7. The input shape and the parity rule: `sed -n '22,26p' flake.nix` → the `gaming` comment ("pinned by ref so `nix flake lock` records the exact rev, no `follows` (the gaming flake's own nixpkgs is already the same rev as nixpkgs-host -- see checks.core-gaming-wiring's lock-node assertion)") and `gaming.url = "git+file:///home/dalhaka/flakes/gaming?ref=main";`; `grep -n 'gamingNixpkgsRev != hostNixpkgsRev' flake.nix` → the equality throw `"core-gaming-wiring: flake.lock's gaming-input nixpkgs (…) is not the same rev as nixpkgs-host (…) (a second nixpkgs entered the closure at a different rev)"`; `nix develop -c jq -r '.nodes[.nodes.gaming.inputs.nixpkgs].locked.rev == .nodes["nixpkgs-host"].locked.rev' flake.lock` → `true` (the lookup shape GN3 copies: a node id resolved through the input's own `inputs` map).
8. `grep -n 'gaming.nixosModules.default' flake.nix` → `964:        gaming.nixosModules.default` inside `coreModules = [ … ]`; `sed -n '4,16p' hosts/core/default.nix` → twelve `imports` entries, `./telemetry.nix` then `../../nixosModules/usageIngest.nix` last.
9. `grep -n '^- `hosts/core/' docs/MAP.md` → twelve lines (`agent-prereqs`, `claude-desktop`, `default`, `firefox`, `gaming`, `graphics`, `hardware-configuration`, `helm`, `lanes`, `proton-backup`, `seat`, `telemetry`), each "`path` — first comment line": a new `hosts/core/media-worlds.nix` changes MAP (`repomap.py`).
10. `host-core` is the home of host wiring assertions: `grep -n 'host-core: services.evidence-store must be enabled on core' flake.nix` → one line, inside the `assert nixpkgs.lib.assertMsg … ;` chain of `checks.${system}.host-core` whose `let` opens with `c = self.nixosConfigurations.core.config;`. `grep -n 'lockData = builtins.fromJSON (builtins.readFile ./flake.lock);' flake.nix` → one line, in `core-gaming-wiring`'s `let` (host-core's `let` has none yet; GN3 adds one).
11. `sed -n '6p' hosts/core/lanes.nix` → `# 10.100.2.x is reserved for the media instance; this lane's address block`; `hosts/core/seat.nix` → `# 10.100.2.x is media's, 10.100.3.x the openrouter lane's; the seat takes`. No `media` broker instance exists on core (`grep -n 'instances.media' flake.nix hosts/core/*.nix` → nothing); this plan adds none (Q2(b): the instance comes with the namespace task).
12. The loopback rule: `grep -n 'localhost-only until Phase 10' nixosModules/helm.nix` → the assertion message `"services.helm.listen must be loopback (127.0.0.1:<port> or [::1]:<port>), got '${cfg.listen}' -- Helm is localhost-only until Phase 10"`; `docs/context/isolation.md` (`grep -n 'loopback' …`): "The loopback assertion itself lives in `nixosModules/helm.nix`, a Helm-owned file, so the amendment crosses out of Isolation"; `grep -n '§10' docs/brief.md` → nothing (no §10 yet); charter `:183-186` places the amendment in increment 4.
13. Live open keys on this plan's files (`tasks.py --root . json`, states): `EV10` ready (`docs/ledger/subsystems.toml`, `docs/subsystems.md`); `PL1` ready and `FA13` ready (the same manifest, additive rows); `EV1` ready (`flake.nix`, `hosts/core/default.nix`, `docs/MAP.md`); `IS4`, `N13`, `N15`, `N17`, `HH2`, `HH3`, `FIX6`, `EV16` ready on `flake.nix`; `HH6`, `HH8`, `HH9`, `SP5`, `EV6`, `IS5b`, `FA23`, `PL2`–`PL5` blocked on it; `PL4` blocked on `hosts/core/default.nix`; the `FIX5` chain, `UI1`, `EV13`, `EV15` on `docs/MAP.md`. `M2`: running none; `Rejected, fix round owed` names no key on these files.
14. The driver guards A5 asks for are landed: `tasks.py --root . json` → `P11` and `P11r` `approved` (`docs/superpowers/plans/2026-09-06-planning-agent.md`); the field packet's anchors: `factory-task` — `if [ -z "${FACTORY_PLAN:-}" ]; then` / `factory_die 2 "FACTORY_PLAN is unset — name the plan …"`; the result grammar `grep -E '^FACTORY-RESULT[[:space:]]+status=(done|partial|failed)([[:space:]]|$)'`, a near miss with commits → `status=unreported`, none → `status=failed`; `factory-integrate` refuses `REFUSED $key: <n> undisclosed file(s) outside touches` and `REFUSED $key: no merge base`. No `dependsOn` on P11 is needed and no interim sentence stands in for a guard.
15. **§5.7 — media's `nix flake check -L` at `1618638` is unverifiable here** (no sibling, no build). GN2 Step 0 runs it at Base and pastes the tail; a red there stops GN2 with `status=partial` and the failing check named (Anticipation).
16. **§5.8 — the live state of `comfy-upstream-probe.timer` on core is unmeasured** and stays so until the switch: media is not wired (`grep -n -i media flake.nix` → two hits, neither an input: the `host-core` message "media joins only when round 2 wires specialisation.media" and a `.claude/projects/-home-dalhaka-flakes-media/memory` path). GN3 turns the unit off by option and asserts it; `## Operator` step 5 reads the unit after the switch.
17. `docs/subsystems.md` is a function of the manifest alone: `pkgs/evidence/subsystems.py` `render` — `del files  # the page is a function of the manifest, never the file list` — and it reads name, prefix, area, gate, depends only; on the scratch copy with GN1's edit applied, `subsystems.py write … --check docs/subsystems.md` → exit 0 (zero-byte diff).
18. The validator accepts an `owns` path absent from the tree (`subsystems.py validate`'s only glob-side rules are `uncovered` and `ambiguous` over the file list; evidence plan Assumption 11): on the scratch copy with GN1's edit and `docs/decisions/2026-09-14-generation-probe-egress.md` appended to the `--files` list, `grep -c 'generation-probe\|ambiguous'` over its output → `0`.
19. `check --draft` keys the prefix guard on the draft's basename (`load_draft`: `plan_name = draft["file"]`), so `/tmp/draft-scratch/draft-0.md` is refused for every `GN` key while a copy named `2026-09-11-generation.md` passes — the harness's required draft name and the guard disagree (a workflow defect noted in the report; every `check --draft` below ran on the copy).
20. The seat's wall-clock cap is `FACTORY_TIMEOUT`, default 10800 s (`tools/factory/seat/factory-task`: `# FACTORY_TIMEOUT wall-clock limit in seconds (default 10800)`). GN2 runs media's whole check set twice (VM tests, a torch rebuild): its launch line sets `FACTORY_TIMEOUT=28800`.
21. The probe's hosts, from the record (a fact of a tree file, re-measured on the media side): `docs/reviews/plan-judgements/2026-09-12-batch-generation.md` erratum 7 — `api.github.com`, `raw.githubusercontent.com`, `pypi.org`, `www.nvidia.com`, `download.nvidia.com`, `github.com`, six; the command's seventh line `https://pypi` is a regex literal.
22. The board's Generation area today: `docs/OPERATIONS.md` → `Area: generation — none open`; landing this file turns it into rows (the orchestrator's `write-board` at landing, never a seat's).
23. Word budget: the landed batch plans are 11,725 (platform), 12,937 (evidence), 19,144 (factory) words (`wc -w`); this plan types four tasks.
24. `nix` in this checkout is `tools/cloud/nix` (`head -5 tools/cloud/nix`: "a cloud-session shim for a host command written as `nix develop -c CMD ARGS...` … There is no real nix in the cloud session; this execs CMD directly"): `nix eval`, `nix build` and `nix flake lock` cannot run here. Lock-file facts were measured with `nix develop -c jq … flake.lock` (Assumptions 6, 7); the root inputs map reads `{"claude-desktop":"claude-desktop","gaming":"gaming","llm-agents":"llm-agents","nixpkgs":"nixpkgs_4","nixpkgs-host":"nixpkgs-host"}` (`nix develop -c jq -r '.nodes.root.inputs' flake.lock`) — the input name is the key, its node id the value, which is the shape GN2's Step 0 reads in media.

## Waves

Derived on the scratch copy (Step 3's form): `cp -a <checkout> /tmp/draft-scratch/tree`, the draft placed as `docs/superpowers/plans/2026-09-11-generation.md` there, a one-repo file `printf '[[repo]]\nname = "nixos-agent-env"\npath = "/tmp/draft-scratch/tree"\n' > /tmp/draft-scratch/repos.toml`, then from the checkout `nix develop -c python3 pkgs/evidence/tasks.py --root /tmp/draft-scratch/tree --repos /tmp/draft-scratch/repos.toml --runs-dir /nonexistent --store /nonexistent check` → empty, `exit=0`; `… conflicts` → 429 lines, 40 naming a `GN` key (`## Cross-plan`); `… waves --repo nixos-agent-env --json` →

```
[[["EV1", "EV10", "EV16", "EV5", "FA11", "FA13", "FA14", "FA3", "FIX5", "FIX5b", "FIX5c", "FIX5d", "FIX6", "FIX7", "HH2", "HH3", "IS4", "N13", "N14", "N15", "N17", "N18", "PL1", "UI1"], ["EV11", "EV12"], ["EV14"], ["EV17"], ["FA10"], ["IS2"], ["N16"]], [["EV13", "EV15"], ["FA12"], ["FA15"], ["FA18"], ["GN1"], ["PL2"]], [["FA16"], ["GN4"], ["PL3"]], [["FA17"], ["FA23", "PL4"], ["PL7"]], [["PL5"]], [["PL6"]]]
```

GN1 sits in the second wave (after EV10), GN4 in the third (after GN1); GN2 is `repo: media` and leaves this repo's list; GN3 is absent because its dependency is GN2 and the one-repo file has no media graph to resolve it through (`waves()`: "an unknown or blocked dep never schedules"). `… waves --repo nixos-agent-env --plan 2026-09-11-generation.md --json` → `[]` for the same reason (every task of this plan waits on a key outside it). The live-tree form on the copy, `nix develop -c python3 pkgs/evidence/tasks.py --root . --runs-dir /nonexistent --store /nonexistent check --draft /tmp/draft-scratch/2026-09-11-generation.md` → no error line, then `waves: [[["GN2"]], [["GN3"]]]` (the draft form stitches GN2 in and layers GN3 behind it; GN1 and GN4 wait on EV10, outside the plan filter) and the 40 `conflicts:` rows. Both forms agree with the table:

| wave | keys | dependsOn | notes |
|---|---|---|---|
| 0 | EV10 (Evidence's plan) | — | not this plan's; the green `subsystems-manifest` baseline (§1 consequence 2) |
| 1 | GN1 ‖ GN2 | GN1: EV10; GN2: none | two repos, disjoint files; GN2 in `~/flakes/media` (its own hand launch, `## Dispatch`) |
| 2 | GN3 ‖ GN4 | GN3: GN2 (resolved through media's git log, keyed (media, GN2)); GN4: GN1 | disjoint files; two groups in one `factory-wave` |

Two tasks never write one file in one wave. One switch, after GN3 lands.

## Cross-plan

Measured hits (`conflicts` on the scratch copy, the 40 `GN` rows), who goes first and why:

- **`docs/ledger/subsystems.toml` and `docs/subsystems.md` — EV10 ↔ PL1 ↔ FA13 ↔ GN1.** EV10 first (GN1's `dependsOn`); PL1 and FA13 are `ready`, additive rows in other subsystems' arrays; GN1 edits only the Generation row. Any order among the three after EV10; each re-runs `subsystems.py write` (the check's second command). If one of the three is `running` or `ran` on the file when GN1 launches, GN1 waits (the pre-launch rule in `## Dispatch`).
- **`flake.nix` — GN3 × N13, N15, N17, HH2, HH3, HH6, HH8, HH9, SP5, FIX6, EV1, EV6, IS4, IS5b, EV16, FA23, PL2, PL3, PL4, PL5.** GN3 adds one `inputs` line, one `coreModules` line and one `let`-plus-`assert` block inside `host-core` — three regions, each a closing-brace conflict the integrator resolves (Platform's cross-plan says the same of PL2–PL5). Order: Platform's chain first when it is in flight (PL2→PL5 export what siblings consume); otherwise GN3 rebases on whatever landed (landing step 2). HH6/HH8/HH9 are withdrawn before Platform's first `flake.nix` wave (Platform A28).
- **`hosts/core/default.nix` — GN3 × EV1 (ready), PL4 (blocked).** Additive `imports`; GN3 appends after `./telemetry.nix`; whichever lands second rebases the one-line hunk.
- **`docs/MAP.md` — GN3 × UI1, FIX5–FIX7, FIX6, EV1, EV6, EV13, EV15, EV16, FA23.** Regeneration only: whoever lands last re-runs `repomap.py --root . write`.
- **Evidence (`EV`):** EV14/EV15 declare and land the `engagement` kind the feed-side POST will carry (`## Decisions` 4); nothing here depends on them. **Helm (`HM`):** `/v1/engage` on 7710 and the feed link (14c/15a) are Helm's; WH2's tile is Helm's. **Isolation (`IS`) / Helm:** the loopback amendment (Q3) and the `media` broker instance for the probe's namespace (Q2). **Platform (`PL`):** the input line lives in `flake.nix`'s `inputs` beside `gaming`; the absorption (Q1) follows Platform's Q6(b) recipe when it comes. **Knowledge (`KN`):** nothing here writes a runbook; the drill is `## Operator`.
- **Foreign writes:** GN1 and GN3 declare `areas:`; every GN task keeps the Generation row's Sonnet gate.

## Operator

After GN3 has integrated and `main` is fast-forwarded (one switch; nothing before it):

1. `cd ~/nixos-agent-env && nix build .#nixosConfigurations.core.config.system.build.toplevel -o /tmp/gn3-result && nix store diff-closures /run/current-system /tmp/gn3-result > /tmp/gn3-delta.txt; wc -l /tmp/gn3-delta.txt; grep -i -c 'caddy' /tmp/gn3-delta.txt` → **prediction (A2):** lines naming `comfyui` and its python environment (torch-bin cu128, from the same nixpkgs rev as the host after GN2), the `comfy-worlds` wrappers (`comfy-worlds-init`, `media-comfy`, `comfy-upstream-probe`, `media-fetch-models`), the two worlds' user units; the `caddy` count is `0`. The measured list is pasted on the board beside this prediction before the switch line is run (GN3 Step 8 pastes the same command's output from the landed tree).
2. `nix build .#checks.x86_64-linux.{host-core,core-gaming-wiring,lint} -L --no-link` → exit 0 (host-core now carries the media assertions).
3. The switch: `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core`, then the two registration commands of the board's recipe (`docs/board/log-2026-09.md`, session 22: `nix-env -p … --set`, then `… switch-to-configuration boot`). Operator only (G1).
4. `systemctl --user list-units --all 'comfy*'` → the worlds' units listed (the generators `inactive`, on demand); `readlink /run/current-system` → the new generation. Paste the unit names on the board: they are the names step 5 and step 6 use.
5. `systemctl --user is-enabled comfy-upstream-probe.timer; echo rc=$?` → `disabled` (or `Failed to get unit file state … No such file or directory`), never `enabled` — Q2(b), §5.8 measured.
6. `systemctl --user start <the sfw generator unit from step 4>`, then `curl --noproxy '*' -s http://127.0.0.1:$(nix eval --raw .#nixosConfigurations.core.config.services.comfyui-worlds.worlds.sfw.feedPort)/healthz` → `ok sfw` (the placeholder's `/healthz`); then `journalctl --user -u <that unit> -b | grep -i aimdo` → the load line. That line is the evidence for claim `aimdo-native-load-unmeasured` (`docs/ledger/claims.toml`, `closes_by = "the media acceptance drill on core imports comfy_aimdo's native module and reports OK …, or the startup log at a GPU start names aimdo as loaded"`): the orchestrator flips the row to `status = "verified"`, `class = "operator"`, `evidence = "operator:<date> journalctl … names aimdo as loaded"` and `claims.py validate` stays silent (A8).
7. `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep -A1 '^Area: generation'` → GN1, GN3, GN4 landed, GN2 landed in media.

**Rollback.** The previous generation: `sudo /nix/var/nix/profiles/system-<N>-link/bin/switch-to-configuration switch` with `<N>` the generation `readlink /nix/var/nix/profiles/system` named before step 3 — never a blind `--rollback`. `git revert` of GN3's one commit removes the input, the module and the stanza; GN2's revert in media restores the old pin; `~/flakes/media` and the worlds root are touched by nothing here. No credential, DNS name, password file or top-up is needed (Q2(b), Q3(a)); under Q3(b) the two `/var/lib/comfy-secrets/comfy-<w>.users` files become items here (`umask 077; install -m640 -g comfy-secrets /dev/stdin /var/lib/comfy-secrets/comfy-sfw.users` shape).

## Dispatch

Preconditions: this file is under `docs/superpowers/plans/` and `tasks.py check` prints nothing; the orchestrator has run `write-board` and committed the block (never a seat); EV10 has landed (GN1's edge); the run names are free (`ls ~/factory/runs | grep -x gn1` empty — `BUG-run-name-reuse`); no key that shares a GN task's file is `running` or `ran` (Assumption 13; `tasks.py --root . json`).

The dry run, from `~/nixos-agent-env`:

```
tools/factory/seat/factory-dispatch gn1 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md --dry-run
```

Today it prints `factory-dispatch: nothing schedulable in 2026-09-11-generation.md (all landed, in flight, or blocked)` (measured on the scratch copy with its `docs/ledger/repos.toml` pointed at the copy and `--repo-name nixos-agent-env`: EV10 unlanded). With EV10's subject in the log it prints `would run: factory-wave gn1 /home/dalhaka/nixos-agent-env "GN1"` (measured the same way after an empty commit carrying EV10's exact subject: `would run: factory-wave gn1 /tmp/draft-scratch/tree "GN1"`). The launch is the same line without `--dry-run`.

The media half is a hand launch (the dispatcher's graph query is `tasks.py --root <repo-path> waves …`, and `~/flakes/media` has no `docs/ledger/repos.toml` for it to read):

```
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md FACTORY_TIMEOUT=28800 tools/factory/seat/factory-task gn2 /home/dalhaka/flakes/media GN2
```

Wave 2, after GN2's subject is in `git -C ~/flakes/media log` and GN1 is on `main` here:

```
tools/factory/seat/factory-dispatch gn3 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md --dry-run
```

→ predicted `would run: factory-wave gn3 /home/dalhaka/nixos-agent-env "GN3" "GN4"` (on the scratch copy, where media is absent and GN3 cannot resolve, it printed `would run: factory-wave gn2w /tmp/draft-scratch/tree "GN4"` after GN1's subject joined the log — measured). Gate: Sonnet (the row's `gate`). Relaunch after a rejection: `FACTORY_PLAN=… tools/factory/seat/factory-task gn3b /home/dalhaka/nixos-agent-env GN3b --prior gn3/GN3` (rung 2 by the key rule); a media fix round names `**repo:** media` in its own section.

**Landing recipe (A1), per key, in order:**

1. In the workspace keep only the one commit the section names — `git -C ~/factory/ws/<run>/<KEY> log --format='%h %s' <base>..task/<KEY>` prints one line; otherwise `git -C ~/factory/ws/<run>/<KEY> reset --hard <that sha>`.
2. If `main` moved under a file the task touches (GN3's `flake.nix` will have): `git -C ~/factory/ws/<run>/<KEY> fetch ~/nixos-agent-env main && git -C ~/factory/ws/<run>/<KEY> merge --no-edit FETCH_HEAD` — the integrator's act, never the seat's; a MAP or queue-block conflict is resolved by regeneration in the workspace (`repomap.py --root . write`, `tasks.py --root . write-board`), committed with `nix develop -c git -C <ws> commit --no-edit`.
3. Commit the review.
4. `tools/factory/seat/factory-integrate <run> ~/nixos-agent-env <KEY>` then `git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>`, gated on both exit codes. For GN2: `tools/factory/seat/factory-integrate gn2 ~/flakes/media GN2` then `git -C ~/flakes/media pull --ff-only ~/factory/base/media integ/gn2`.
5. Dispatch what it unblocks (A7): EV10 → GN1; GN1 → GN4; GN2 (media) → GN3; GN3 → the switch (`## Operator`).

## Anticipation

- **A1 dispatch and landing:** the lines above; the seat never merges `main` and never touches the board (G6 amendment).
- **A2 the switch delta:** `## Operator` step 1's prediction, measured on the landed tree before the switch line; a `caddy` line or a second `python3` (a second nixpkgs) is a finding against GN2/GN3.
- **A3 operator items:** none under the defaults; the `comfy-secrets` files under Q3(b).
- **A4 mutation tables:** one per task below; the gate's battery is a superset.
- **A5 driver guards:** present (Assumption 14: P11/P11r landed; the field packet's anchors); no interim sentence, no edge.
- **A6 relaunch:** the `--prior` line above; a dead seat's diff stays in `~/factory/ws/<run>/<KEY>`.
- **A7 what a landing unblocks:** landing step 5.
- **A8 claims:** `aimdo-native-load-unmeasured` — `## Operator` step 6; no other open gap names Generation.
- **A9 holds:** `flake-check` reads FAIL at HEAD for `seat-vm` (IS10's; per-check builds are unaffected — every acceptance here is built by name). GN2 is long (Assumption 20): the launch sets `FACTORY_TIMEOUT=28800`; if Base's own `nix flake check -L` is red (Assumption 15), GN2 reports `status=partial` with the failing check named and the orchestrator re-plans GN2 as GN2r — a red sibling is not this plan's to fix by a fix round. If Base already carries the host rev, GN2 has no diff: `status=partial`, `FACTORY-NOTES already-at-host-rev`, no commit; the orchestrator withdraws GN2 with a `docs/ledger/task-status.toml` row and edits GN3's `**dependsOn:**` line to `none` (a field line, not a heading).
- **A10 questions:** Q1–Q3, one letter each; silence applies the defaults.
- **A11 the handoff line** for the board: "generation: on the seat: GN2 in media (`gn2`), GN1 here (`gn1`); in gate: —; next: wave 2 (`gn3`) then the switch".
- **A12 re-plan:** replan mode, the `<KEY>r` section appended, every heading byte-intact.
- **A13 / A14:** no hook, no second consumer of a derived block, no deny rule is added — not triggered.
- **GN3's eval contract:** the option set is measured at Base (Step 0); a set that differs from Assumption 5's six names stops the task with the list pasted (`status=partial`), except that an `enable` option, if present, is set `true` in the stanza and reported.
- **GN2's input name:** media's nixpkgs input may not be called `nixpkgs`; Step 0 prints the root inputs and the seat uses the printed name in every later command — a substitution reported in `FACTORY-NOTES`, not a deviation.

## Not in this plan

- **Sub-projects 2 and 3 and the rules mutator** — typed against the tree that holds the code (31a): under Q1(b) a media-side plan (`~/flakes/media/docs/superpowers/plans/…`, W-series shape), under Q1(a) the next GN plan here. The contract they inherit: (i) the feed's state is `worlds/<world>/feed.sqlite`, rebuildable from `out/*.png`; (ii) the feed stays zero-outbound as a rule over values, not a list of spellings — a closed tag set, no attribute beginning `on`, no `<meta http-equiv>`, no `formaction`, and every `src`/`href`/`action` value with no scheme (`^[A-Za-z][A-Za-z0-9+.-]*:`) and no leading `//` — with one mutant per arm; (iii) the engagement counts leave the feed only as `POST http://127.0.0.1:7710/v1/engage` with EV14's body (`## Decisions` 4), dropped on any error, never a store write; (iv) the mutator is a `[mutate]` table in the lab `manifest.toml` over the four axes, `RuleNeverFires` is an error, a fixed-seed dry run is byte-identical twice, and the mutate unit is on demand (`wantedBy = []`, `ConditionUser` the operator); (v) the probe runs inside the `media` broker namespace or not at all — a system unit joining `egress-media` with `HTTPS_PROXY` and `SSL_CERT_FILE` from the instance, the instance's `allow` exactly the six hosts of Assumption 21 with no `inject`, and the probe refusing to open a socket when either variable is unset (exit 3, one line naming invariant 3).
- **The absorption** (Q1(b)): one subtree act after the media-side plan lands — Platform's Q6(b) recipe with `--prefix=media`, the tag `absorbed/media-<rev>`, `treefmt` inside the `--no-commit` merge, one merge commit, a board line — then a re-plumb task typed against the landed tree (the 21 checks under this flake's `checks.${system}`, the five packages, the input retired).
- **Caddy on core, the LAN face, the site names and the password files** (Q3(a)) — after the loopback amendment (Helm's `nixosModules/helm.nix`, Isolation's increment 4).
- **The `media` broker instance and model fetching on core** — the instance arrives with the probe's namespace task; an HF token for gated models is a credential (invariant 2) and the operator's; `media-fetch-models` on core waits for both.
- **WH2 — the Helm tile `media-refresh` reading `proposals.jsonl`** — Helm's (`pkgs/helm/collect.py`), and the `proposals` stream's schema is Evidence's (`pkgs/evidence/SCHEMA.md`); the spec's §6.
- **Backup paths for the worlds root** — the layout (`worlds/<w>/lab/`, `out/`) is measured on the media side; a path added to `hosts/core/proton-backup.nix` must also be named in `docs/runbooks/backup.md` (`core-backup-wiring`'s throw) — one S task after the drill shows the tree.
- **`evidence bundle` listing media's 21 checks under this repo's HEAD** (`M6`: `comfy-*` rows with `HEAD —; live —`) — Evidence's.
- **Phase 5 local weights, the generation lab, netns confinement of a world, the parser's `HEADING_RE`, `factory-review`'s trailer comparison** — as the spec's §6 assigns them.
- **The `2026-09-05-comfy-worlds.md` entry in the manifest's `plans`** — harmless (the media repo carries no manifest to check against, block §5.1); not added.

## Tasks

### GN1 (code, XS) — Generation's manifest row owns what this plan creates and drops the superseded plan entry

**dependsOn:** EV10
**areas:** generation, evidence
**touches:** `docs/ledger/subsystems.toml`, `docs/subsystems.md`
**acceptance:** subsystems-manifest, lint
**commit subject:** generation: the manifest row owns the probe decision and drops the superseded plan entry (test: subsystems-manifest, lint)

**Why.** The row reads `owns = []` (header) and GN4 creates `docs/decisions/2026-09-14-generation-probe-egress.md`, a path no glob covers: `nix develop -c python3 -c "import tomllib,fnmatch;d=tomllib.load(open('docs/ledger/subsystems.toml','rb'));print([r['name'] for r in d['subsystem'] for g in r['owns'] if fnmatch.fnmatch('docs/decisions/2026-09-14-generation-probe-egress.md',g)])"` → `[]` (Knowledge's decision globs stop at `2026-09-07*` plus one 09-09 file; Program owns two named files). Without this row `subsystems-manifest` goes red the moment GN4 lands (§1 consequence 1). The row's `plans` still names `2026-09-02-media-flake.md`, superseded (Assumption 3) and untyped, so a `GN` key typed into it today passes the reserved-prefix guard — measured with `check()` on a hand-built graph: `nix develop -c python3 -c "import sys; sys.path.insert(0,'pkgs/evidence'); import tasks; g={'repos':[{'name':'nixos-agent-env','path':'.','plans':'docs/superpowers/plans/*.md','tasks':[{'key':'GN99','kind':'docs','size':'XS','plan':'2026-09-02-media-flake.md','depends_on':[],'touches':[],'acceptance':[],'areas':[],'repo':None,'commit_subject':'x','probe_errors':[],'state':'ready'}]}],'configured_repos':['nixos-agent-env']}; print(tasks.check(g))"` → `[]`. After this task the same command prints the refusal (measured on the scratch copy with the edit applied: `['tasks: 2026-09-02-media-flake.md/GN99: prefix GN is reserved for Generation, whose plans are docs/superpowers/plans/2026-09-11-generation.md']`). The key `GN99` is the probe key because `reserved_prefix` reads the letters before the first digit (`GNX` would be prefix `GNX`).

**Files.**
- Modify `docs/ledger/subsystems.toml`, the Generation row only: `owns = []` becomes

  ```toml
  owns = [
    "docs/decisions/2026-09-14-generation-probe-egress.md",
  ]
  ```

  and `plans` loses the line `"docs/superpowers/plans/2026-09-02-media-flake.md",`, keeping `"docs/superpowers/plans/2026-09-11-generation.md",`. Two-space indent, trailing comma, one entry per line (the file's shape); no other row changes.
- Modify `docs/subsystems.md`: regenerated by `subsystems.py write`, never by hand; Assumption 17 predicts a zero-byte diff (the page renders name, prefix, area, gate, depends only) — the file is in `touches` because the tool is run against it and the seat pastes `git diff --stat docs/subsystems.md` (expected: nothing).

**Interfaces.**
1. `fnmatch` over the manifest resolves `docs/decisions/2026-09-14-generation-probe-egress.md` to exactly `['Generation']`.
2. `check()` refuses a `GN` key typed into `2026-09-02-media-flake.md` with the line quoted in **Why**, and accepts one in `2026-09-11-generation.md` (the row's remaining entry).
3. `subsystems.py validate` over `git ls-files` plus the new path prints no `uncovered:` line for that path and no `ambiguous:` line at all; every line of the manifest outside the Generation row is byte-identical (`git diff docs/ledger/subsystems.toml` shows `+  "docs/decisions/2026-09-14-generation-probe-egress.md",` and `-  "docs/superpowers/plans/2026-09-02-media-flake.md",` plus the `owns = []` → `owns = [` / `]` lines, nothing else).
4. `docs/subsystems.md` is byte-equal to `subsystems.py write … --check`'s rendering (exit 0).
5. Error contract of the tools this task relies on: `subsystems.py validate` prints one `uncovered: <path>` or `ambiguous: <path> (<rows>)` line per finding on stderr and exits 1, nothing on stdout; `write --check` exits 1 with `subsystems: docs/subsystems.md is stale (regenerate: …)`; `check()` returns a list of strings (empty is sound).

**Facts.** The manifest's comment: `sed -n '1,9p' docs/ledger/subsystems.toml` → "`owns` is a set of fnmatch globs over repo-relative tracked paths (`*` spans `/`, no `**` …); every tracked path must match exactly one row. `plans` is the plan files allowed to define keys under the prefix (the EV2 reservation guard reads it)". `subsystems-manifest` (`flake.nix`, `grep -n 'subsystems-manifest =' flake.nix`) runs `python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --files files.txt` then `… write … --check docs/subsystems.md` over `find ${self} -type f -printf '%P\n'`. EV10's own Files (i)–(iv) touch Factory's, Program's, Knowledge's and Evidence's rows, never Generation's, so the two edits are disjoint hunks of one file (the `dependsOn` orders them).

**Steps.**
1. **Red.** `printf '%s\n' docs/decisions/2026-09-14-generation-probe-egress.md > .factory-scratch/new.txt; git ls-files | cat - .factory-scratch/new.txt > .factory-scratch/files.txt; nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --files .factory-scratch/files.txt 2>&1 | grep 'generation-probe\|ambiguous'; echo rc=$?` → `uncovered: docs/decisions/2026-09-14-generation-probe-egress.md`, `rc=0`. Then the guard replay of **Why** → `[]`. Paste both.
2. Edit `docs/ledger/subsystems.toml` as **Files** says.
3. `nix develop -c python3 pkgs/evidence/subsystems.py write docs/ledger/subsystems.toml --root . --out docs/subsystems.md; git diff --stat docs/subsystems.md` → no output (Assumption 17).
4. **Green.** Step 1's validate line → no output, `rc=1`; the guard replay → the one refusal line; the fnmatch one-liner of **Why** → `['Generation']`; `nix develop -c python3 pkgs/evidence/subsystems.py write docs/ledger/subsystems.toml --root . --check docs/subsystems.md; echo rc=$?` → `rc=0`; `git add docs/ledger/subsystems.toml docs/subsystems.md; nix build .#checks.x86_64-linux.subsystems-manifest -L --no-link; nix build .#checks.x86_64-linux.lint -L --no-link` → both exit 0 (EV10 landed: the tree is otherwise covered).
5. **Mutants** — each applied, its kill command run and pasted, then reverted with `git checkout docs/ledger/subsystems.toml docs/subsystems.md`:
   - **M1 drop-owns-line** — delete the `docs/decisions/…` line. Kill: Step 1's validate → `uncovered: docs/decisions/2026-09-14-generation-probe-egress.md`.
   - **M2 keep-superseded-plan** — restore the `2026-09-02-media-flake.md` line in `plans`. Kill: the guard replay → `[]` instead of the refusal.
   - **M3 glob-not-path** — write `"docs/decisions/*"` instead of the exact path. Kill: Step 1's validate → `ambiguous: docs/decisions/2026-09-09-redesign-answers.md (Generation, Program)` and one `ambiguous:` line per Knowledge-owned decision file (`grep -c '^ambiguous:'` > 0).
   - **M4 stale-mirror** — append one blank line to `docs/subsystems.md`. Kill: `write … --check` → `subsystems: docs/subsystems.md is stale (regenerate: python3 pkgs/evidence/subsystems.py write docs/ledger/subsystems.toml --root .)`, `rc=1`.
   - **Negative control** — `EVIDENCE_UNIT_SANDBOX=1 nix develop -c pytest tests/evidence/test_subsystems.py -q -k test_clean_fixture_passes` passes; add an unowned path to that test's file list → it fails; restore. Proves the clean fixture discriminates.
6. **Commit** (G6): `.factory-scratch/cmds.txt` lists Step 1's two commands, Step 3's, Step 4's five, M1–M4's kill commands (each preceded by its edit and followed by the revert) and the control; `body.sh` produces the body; `nix develop -c git commit -F .factory-scratch/msg.txt`.

**Tests (assertion → mutant; fixture → discriminating row).** Interface 1 → M1; Interface 2 → M2 (the row: a `GN`-prefixed key whose plan is the superseded file, not `GNX`); Interface 3's no-`ambiguous:` → M3 (the row: a decision file another row already owns); Interface 4 → M4. Control: the clean fixture and its unowned-path mutant.

**probes:**
- generation-owns: `nix develop -c python3 -c "import tomllib;d=tomllib.load(open('docs/ledger/subsystems.toml','rb'));print(len([r for r in d['subsystem'] if r['name']=='Generation'][0]['owns']))"` :: ge 1 :: the row read owns = [] at c9c5bd7; M1 reads 0
- generation-plans: `nix develop -c python3 -c "import tomllib;d=tomllib.load(open('docs/ledger/subsystems.toml','rb'));print(len([r for r in d['subsystem'] if r['name']=='Generation'][0]['plans']))"` :: le 1 :: two entries at c9c5bd7; M2 reads 2
- decision-owned: `nix develop -c python3 -c "import tomllib,fnmatch;d=tomllib.load(open('docs/ledger/subsystems.toml','rb'));print(len([r['name'] for r in d['subsystem'] for g in r['owns'] if fnmatch.fnmatch('docs/decisions/2026-09-14-generation-probe-egress.md',g)]))"` :: ge 1 :: Interface 1; M1 reads 0
- decision-unambiguous: `nix develop -c python3 -c "import tomllib,fnmatch;d=tomllib.load(open('docs/ledger/subsystems.toml','rb'));print(len([r['name'] for r in d['subsystem'] for g in r['owns'] if fnmatch.fnmatch('docs/decisions/2026-09-14-generation-probe-egress.md',g)]))"` :: le 1 :: Interface 3; M3 reads 2
- mirror-current: `nix develop -c python3 pkgs/evidence/subsystems.py write docs/ledger/subsystems.toml --root . --check docs/subsystems.md; echo rc=$?` :: eq rc=0 :: Interface 4

### GN2 (code, S) — media pins nixpkgs to the host rev a5cc6f2c and proves its 21 checks there

**dependsOn:** none
**repo:** media
**touches:** `flake.nix`, `flake.lock`
**acceptance:** lint, comfyui-package, comfyui-eval, comfyui-cliploader-krea2, comfyui-startup-clean, comfyui-vm, comfyui-assertion-negative-broker, comfyui-assertion-negative-gpu, comfyui-assertion-negative-listen, comfyui-assertion-negative-listen-address, comfyui-assertion-negative-token, comfy-worlds-eval, comfy-worlds-unit, comfy-worlds-vm, comfy-worlds-assertion-negative-hosts, comfy-worlds-assertion-negative-name, comfy-worlds-assertion-negative-password-path, comfy-worlds-assertion-negative-ports, media-fetch-unit, media-fetch-bats, comfy-upstream-probe-unit
**commit subject:** generation: media pins nixpkgs to the host rev a5cc6f2c (test: lint, comfyui-package, comfyui-eval, comfyui-cliploader-krea2, comfyui-startup-clean, comfyui-vm, comfyui-assertion-negative-broker, comfyui-assertion-negative-gpu, comfyui-assertion-negative-listen, comfyui-assertion-negative-listen-address, comfyui-assertion-negative-token, comfy-worlds-eval, comfy-worlds-unit, comfy-worlds-vm, comfy-worlds-assertion-negative-hosts, comfy-worlds-assertion-negative-name, comfy-worlds-assertion-negative-password-path, comfy-worlds-assertion-negative-ports, media-fetch-unit, media-fetch-bats, comfy-upstream-probe-unit)

**Why.** GN3 wires media into `core` as a flake input, and the house rule for an input is lock parity with `nixpkgs-host` (Assumption 7: the `gaming` comment and `core-gaming-wiring`'s equality throw; decision 43b "absorbed subsystems move onto `nixpkgs-host`"; brief §8 "Pin every flake input to an exact rev"). Media's nixpkgs is the pre-upgrade host pin, `ac62194c3917…` (Assumption 5), while the host is `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` (Assumption 6): without this task GN3's parity assertion is red and a second nixpkgs enters the closure. Whether ComfyUI's torch-bin builds at the host rev is unmeasured (Assumption 6); this task measures it, and its Step 0 measures spec §5.7.

**Files.**
- Modify `flake.lock` (the `nixpkgs` node's `rev`, `narHash`, `lastModified`; nothing else).
- Modify `flake.nix` only if the input URL pins a rev (the house style: `github:NixOS/nixpkgs/<rev>`): that literal becomes `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4`. If the URL carries no rev, `flake.nix` is untouched (an untouched entry in `touches` is allowed; report it).

**Interfaces.**
1. The root input named `nixpkgs` (or the name Step 0 printed) locks to `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4`: `nix eval --raw --expr 'let l = builtins.fromJSON (builtins.readFile ./flake.lock); in l.nodes.${l.nodes.root.inputs.nixpkgs}.locked.rev'` prints that rev. The same lookup with `jq` (`nix develop -c jq -r '.nodes[.nodes.root.inputs.nixpkgs].locked.rev' flake.lock`) is what this plan measured on nixos-agent-env's own lock (→ `34ab99075ac4f7e40cf037eef32cb1c360bb85e9`, its non-host `nixpkgs`); the `nix eval` form is written for a workspace whose devShell may lack `jq` and was not run at draft time (Assumption 24).
2. `nix flake check -L` in the workspace exits 0 — all 21 checks of Assumption 5, the two VM checks included.
3. `git diff --unified=0 <base> -- flake.lock | grep -c '^+ *"rev"'` → `1`: exactly one node moved.
4. `nix flake check -L` refuses a lock that disagrees with a rev-pinned URL (`error: … flake input 'nixpkgs' … doesn't match`), so a `flake.nix` pin and the lock cannot drift apart.
5. Failure contract: a red at Step 0 (the old rev) → `FACTORY-RESULT status=partial`, `FACTORY-NOTES base-red: <check name>` — the seat changes nothing (a red sibling is re-planned, Anticipation A9); a red at Step 3 (the new rev) → the same form with `new-rev-red: <check name>` and the diff **not** committed; a Base already at the host rev → `status=partial`, `FACTORY-NOTES already-at-host-rev`, no commit.

**Facts.** The host rev and the old pin: Assumption 6 and `sed -n '12p' flake.nix` in nixos-agent-env (`# nixpkgs-host pin (ac62194c3917, 2026-01-02; …`). The check list and media HEAD: block §2/§4 (`1618638 integrate W6c…`), Assumption 5. The root-inputs shape a lock carries: Assumption 24's map (the input name is the key, its node id the value; here `nixpkgs` → `nixpkgs_4`).

**Steps.**
0. **Base.** `git log --oneline -1` (paste). `nix eval --json --expr '(builtins.fromJSON (builtins.readFile ./flake.lock)).nodes.root.inputs'` → the root inputs map (paste; the nixpkgs input is the key whose node's `locked.rev` begins `ac62194c`; use that key wherever the plan writes `nixpkgs`). Interface 1's command → the old rev (the red for Interface 1). `grep -n 'nixpkgs.*url' flake.nix` (paste — decides whether `flake.nix` changes). Then §5.7: `nix flake check -L 2>&1 | tail -20; echo rc=${PIPESTATUS[0]}` → `rc=0` expected; a non-zero here ends the task per Interface 5.
1. **Red.** Interface 1's command → `ac62194c3917…` (not the host rev); `grep -c 'a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4' flake.nix flake.lock` → `0`.
2. If `flake.nix` pins a rev: replace the old rev literal with `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` in the URL. Then `nix flake lock --override-input nixpkgs github:NixOS/nixpkgs/a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` (substitute the input name from Step 0), then `git diff --stat` → `flake.lock` (and `flake.nix`) only.
3. **Green.** Interface 1's command → `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4`; Interface 3's grep → `1`; `nix flake check -L 2>&1 | tail -20; echo rc=${PIPESTATUS[0]}` → `rc=0`; then each acceptance name by `nix build .#checks.x86_64-linux.<name> -L --no-link` (the driver verifies them by name).
4. **Mutants** (applied, killed, reverted with `git checkout flake.nix flake.lock` then Step 2 again):
   - **M1 wrong-rev** — lock to `34ab99075ac4f7e40cf037eef32cb1c360bb85e9` instead. Kill: Interface 1's command prints `34ab9907…`, not the host rev.
   - **M2 lock-only** — (only when `flake.nix` pins a rev) update the lock and leave the URL's old rev. Kill: `nix flake check -L` → the Interface 4 error, exit non-zero.
   - **M3 second-node** — also `--override-input <another input>` to any other rev. Kill: Interface 3's grep → `2`.
   - **Negative control** — Step 0's green at the old rev is the control: the same 21 checks pass on both sides of the pin, so a check that fails at Step 3 fails because of the rev, not the tree; discriminating row: M1's rev makes `comfyui-package` (a nixpkgs whose torch-bin differs) or Interface 1 red.
5. **Commit** (G6): `cmds.txt` = Step 0's four commands, Step 1's two, Step 3's three, M1–M3's kills, the checks by name; `body.sh` builds the body; the subject byte-exact.

**Tests (assertion → mutant; fixture → discriminating row).** Interface 1 → M1; Interface 4 → M2 (row: a URL rev that disagrees with the lock); Interface 3 → M3 (row: a second moved node); Interface 2 → Step 3's own run, with Step 0 as the control.

**probes:**
- media-nixpkgs-rev: `nix eval --raw --expr 'let l = builtins.fromJSON (builtins.readFile ./flake.lock); in l.nodes.${l.nodes.root.inputs.nixpkgs}.locked.rev'` :: eq a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4 :: Interface 1, the host pin
- lock-nodes-moved: `git diff --unified=0 HEAD~1 -- flake.lock | grep -c '^+ *"rev"'` :: le 1 :: Interface 3, one node; M3 reads 2

### GN3 (code, M) — media on core: the input, the worlds module, the host stanza and the host-core assertions

**dependsOn:** GN2
**areas:** generation, platform, evidence
**touches:** `flake.nix`, `flake.lock`, `hosts/core/default.nix`, `hosts/core/media-worlds.nix`, `docs/MAP.md`
**acceptance:** host-core, lint
**commit subject:** generation: media on core — the worlds module from the media input, no LAN, no probe timer (test: host-core, lint)

**Why.** Decision 16b: "the worlds' on-demand user units plus host-level Caddy wired into `core`, no specialisation". Host integration does not exist (Assumption 16: two `media` hits in `flake.nix`, neither an input). WH1 in the media plan is invisible to the queue (spec §5.2); this section is its typed successor. The measured shape is `gaming`'s: a `git+file://` input pinned by ref, its module in `coreModules`, a host file that sets the options, and eval-time assertions that pin the wiring (Assumptions 7, 8, 10). The Caddy half waits on Q3, the probe timer on Q2; both are asserted off so a later widening is a diff a check reads.

**Files.**
- Modify `flake.nix`: (i) in `inputs`, after the `gaming.url` line:

  ```nix
    # ~/flakes/media is a READ-ONLY sibling repo (plan 2026-09-11-generation, GN3;
    # decision 16b): pinned by ref, no `follows`; its nixpkgs is the host rev
    # after GN2 -- see host-core's media lock-node assertion.
    media.url = "git+file:///home/dalhaka/flakes/media?ref=main";
  ```

  (ii) `media,` added to the `outputs = { … }:` argument set beside `gaming,`; (iii) in `coreModules`, after `gaming.nixosModules.default`: `media.nixosModules.comfyui-worlds` (not `default`, which would also import the single-service `comfyui` module); (iv) in `checks.${system}.host-core`'s `let`, after `polkit = c.security.polkit.extraConfig;`:

  ```nix
            # GN3 (plan 2026-09-11-generation): media on core, decision 16b.
            mw = c.services.comfyui-worlds;
            worldPorts = nixpkgs.lib.concatMap (w: [
              w.comfyPort
              w.feedPort
            ]) (builtins.attrValues mw.worlds);
            comfyUserServices = nixpkgs.lib.filterAttrs (n: _: nixpkgs.lib.hasInfix "comfy" n) c.systemd.user.services;
            lockData = builtins.fromJSON (builtins.readFile ./flake.lock);
            mediaNixpkgsRev = lockData.nodes.${lockData.nodes.media.inputs.nixpkgs}.locked.rev;
            hostNixpkgsRev = lockData.nodes.nixpkgs-host.locked.rev;
  ```

  (`inputs.nixpkgs` is the name GN2's Step 0 printed; substitute if it differs) and, before that check's final `builtins.seq`/`runCommand`, the assertions:

  ```nix
          assert nixpkgs.lib.assertMsg (mw.lan.enable == false)
            "host-core: comfyui-worlds.lan must stay off until the loopback rule is amended (decision 20b, charter increment 4; plan 2026-09-11-generation Q3)";
          assert nixpkgs.lib.assertMsg (builtins.attrNames mw.worlds == [ "nsfw" "sfw" ])
            "host-core: comfyui-worlds must render exactly the two worlds nsfw and sfw (design: two worlds)";
          assert nixpkgs.lib.assertMsg (builtins.length (nixpkgs.lib.unique worldPorts) == 4)
            "host-core: the two worlds' comfyPort/feedPort must be four distinct loopback ports";
          assert nixpkgs.lib.assertMsg (
            !(builtins.elem 443 c.networking.firewall.allowedTCPPorts)
            && !(builtins.any (p: builtins.elem p c.networking.firewall.allowedTCPPorts) worldPorts)
          ) "host-core: no world port and not 443 may be opened in the firewall while comfyui-worlds.lan is off";
          assert nixpkgs.lib.assertMsg (
            (c.systemd.user.timers ? "comfy-upstream-probe") && !c.systemd.user.timers."comfy-upstream-probe".enable
          ) "host-core: the comfy-upstream-probe timer must be declared and disabled on core (decision 2026-09-14-generation-probe-egress: no egress exception)";
          assert nixpkgs.lib.assertMsg (mediaNixpkgsRev == hostNixpkgsRev)
            "host-core: flake.lock's media-input nixpkgs (${mediaNixpkgsRev}) is not the same rev as nixpkgs-host (${hostNixpkgsRev}) (a second nixpkgs entered the closure at a different rev)";
          assert nixpkgs.lib.assertMsg (mw.operatorUser == "dalhaka")
            "host-core: comfyui-worlds.operatorUser must be the operator (dalhaka)";
          assert nixpkgs.lib.assertMsg (
            builtins.length (builtins.attrNames comfyUserServices) >= 2
            && builtins.any (u: u.wantedBy == [ ]) (builtins.attrValues comfyUserServices)
          ) "host-core: at least two comfy user services must exist and at least one must be on demand (wantedBy = [ ])";
  ```

- Modify `flake.lock`: `nix flake lock` adds the `media` node and its transitive nodes.
- Create `hosts/core/media-worlds.nix` (the block is indented two spaces here for the brief extractor; the file's lines start at column 0):

  ```nix
  _: {
    # Media on core (plan 2026-09-11-generation, GN3; decision 16b): the worlds'
    # on-demand user units from the media input, no specialisation. LAN off until
    # the loopback rule is amended (Q3; charter increment 4); the upstream probe's
    # timer off until the probe runs inside the media broker namespace (Q2;
    # docs/decisions/2026-09-14-generation-probe-egress.md).
    services.comfyui-worlds = {
      operatorUser = "dalhaka";
      lan.enable = false;
    };
    systemd.user.timers."comfy-upstream-probe".enable = false;
  }
  ```

  If Step 0 shows an `enable` option, add `enable = true;` as the first line of the block and report it.
- Modify `hosts/core/default.nix`: `./media-worlds.nix` appended to `imports` after `./telemetry.nix`.
- Modify `docs/MAP.md`: `python3 pkgs/evidence/repomap.py --root . write` (the `## Hosts` section gains the new file with its first comment line).

**Interfaces.**
1. `nix eval .#nixosConfigurations.core.config.services.comfyui-worlds.lan.enable` → `false`; `… .systemd.user.timers.comfy-upstream-probe.enable` → `false`; `… .services.comfyui-worlds.operatorUser` → `"dalhaka"`.
2. `nix eval --json .#nixosConfigurations.core.config.services.comfyui-worlds.worlds --apply builtins.attrNames` → `["nsfw","sfw"]`; the four ports distinct (assertion three).
3. The eight `host-core` assertions above, each with its message; `nix build .#checks.x86_64-linux.host-core -L --no-link` exits 0 only when all hold.
4. The lock carries a `media` node whose transitive nixpkgs rev equals `nixpkgs-host`'s: `nix develop -c jq -r '.nodes[.nodes.media.inputs.nixpkgs].locked.rev == .nodes["nixpkgs-host"].locked.rev' flake.lock` → `true` (the same command over `gaming` reads `true` today, Assumption 7).
5. `docs/MAP.md`'s `## Hosts` section lists `hosts/core/media-worlds.nix` with the comment's first line; `repomap.py --root . check` exits 0.
6. Which tree each derivation reads: `host-core` evaluates `self.nixosConfigurations.core` from this checkout with the `media` input fetched from `/home/dalhaka/flakes/media` at the locked rev; nothing here builds ComfyUI (eval only) except Step 8's closure build.
7. Failure contract: an option set at Step 0 that is not Assumption 5's six names (plus an optional `enable`) → `status=partial`, `FACTORY-NOTES option-set: <the list>`, no stanza written; a module eval error naming a required option → the same form with the error's first line; a `media` fetch failure (`git+file` unreadable) → `status=failed` with the `nix flake lock` error pasted.

**Facts.** Assumptions 5–12, 24. `hosts/core/proton-backup.nix` already backs up `/home/dalhaka/.claude/projects/-home-dalhaka-flakes-media/memory` (`sed -n '39p'`): nothing to add there. `grep -n -i 'caddy' flake.nix hosts/core/*.nix` → nothing: no Caddy is configured on core today, so a `caddy` line in Step 8's delta is a finding.

**Steps.**
0. **Base.** `git log --oneline -1` here and `git -C /home/dalhaka/flakes/media log --format=%s -30 | grep -c '^generation: media pins nixpkgs to the host rev a5cc6f2c'` → `1` (GN2 landed; `0` stops the task). The option set: `nix eval --json --impure --expr 'let m = (builtins.getFlake "git+file:///home/dalhaka/flakes/media").nixosModules.comfyui-worlds; s = (builtins.getFlake (toString ./.)).inputs.nixpkgs-host.lib.nixosSystem { system = "x86_64-linux"; modules = [ m { fileSystems."/".device = "none"; fileSystems."/".fsType = "tmpfs"; boot.loader.grub.enable = false; system.stateVersion = "25.11"; } ]; }; in builtins.attrNames s.options.services.comfyui-worlds'` → `["cpuOnly","lan","operatorUser","package","root","worlds"]` expected (Interface 7 otherwise). Then the same expression with `s.config.services.comfyui-worlds.worlds` in place of the `attrNames` clause → the default worlds and their ports (paste; the values M3 uses).
1. **Red.** Write the `host-core` `let` bindings and the eight assertions (Files (iv)) with no input, no module and no stanza; `nix build .#checks.x86_64-linux.host-core -L --no-link 2>&1 | tail -5` → `error: attribute 'comfyui-worlds' missing` (`c.services.comfyui-worlds` does not exist). Paste.
2. Add the input (Files (i), (ii)); `nix flake lock 2>&1 | tail -5; git diff --stat flake.lock` → the `media` node added; `nix develop -c jq -r '.nodes.media.locked.rev' flake.lock` → media's HEAD rev (the one Step 0 counted).
3. Add the module to `coreModules` (Files (iii)); create `hosts/core/media-worlds.nix`; append the import (Files); `git add hosts/core/media-worlds.nix`.
4. `python3 pkgs/evidence/repomap.py --root . write; git diff --stat docs/MAP.md` → one line changed in `## Hosts`.
5. **Green.** `nix build .#checks.x86_64-linux.host-core -L --no-link` → exit 0; Interface 1's three evals and Interface 2's; Interface 4's `jq` → `true`; `nix build .#checks.x86_64-linux.lint -L --no-link` → exit 0; `nix build .#checks.x86_64-linux.core-gaming-wiring -L --no-link` → exit 0 (unchanged neighbour).
6. **Mutants** (each applied, killed, reverted with `git checkout flake.nix hosts/core/media-worlds.nix`):
   - **M1 lan-on** — `lan.enable = true;` in the stanza. Kill: `host-core` → the first assertion's message, or the module's own `lan` assertion (`comfy-worlds-assertion-negative-*` shapes) if it fires first — paste whichever; both are red.
   - **M2 module-dropped** — remove `media.nixosModules.comfyui-worlds` from `coreModules`. Kill: Step 1's red text.
   - **M3 port-collision** — `services.comfyui-worlds.worlds.sfw.comfyPort = <nsfw's comfyPort from Step 0>;` in the stanza. Kill: the third assertion's message.
   - **M4 port-opened** — `networking.firewall.allowedTCPPorts = [ 443 ];` in the stanza. Kill: the fourth assertion's message.
   - **M5 timer-line-dropped** — delete the `systemd.user.timers.…enable = false;` line. Kill: the fifth assertion's message (either the module defines the timer enabled, or nothing declares it — both arms are red).
   - **M6 lock-drift** — `nix flake lock --override-input media/nixpkgs github:NixOS/nixpkgs/34ab99075ac4f7e40cf037eef32cb1c360bb85e9` (the input path as Step 0 named it). Kill: the sixth assertion's message with both revs; revert with `git checkout flake.lock`.
   - **M7 wrong-user** — `operatorUser = "root";`. Kill: the seventh assertion's message.
   - **M8 map-stale** — skip Step 4. Kill: `lint` → `repomap.py --root . check` non-zero.
   - **Negative control** — `core-gaming-wiring` builds before and after; `nix flake lock --override-input gaming/nixpkgs github:NixOS/nixpkgs/34ab99075ac4f7e40cf037eef32cb1c360bb85e9` → its equality throw; `git checkout flake.lock`. Proves the parity shape is live on the neighbour this one copies.
7. Re-run Step 5 after the reverts.
8. **The closure** (A2, measured by the seat, repeated by the operator on the landed tree): `nix build .#nixosConfigurations.core.config.system.build.toplevel -o .factory-scratch/result 2>&1 | tail -3` then `nix store diff-closures /run/current-system .factory-scratch/result > .factory-scratch/delta.txt; wc -l < .factory-scratch/delta.txt; grep -i -c caddy .factory-scratch/delta.txt; grep -i 'comfy\|torch' .factory-scratch/delta.txt` → the line count, `0`, and the ComfyUI lines. Paste all three outputs.
9. **Commit** (G6): `cmds.txt` = Step 0's three, Step 1's, Step 2's two, Step 4's, Step 5's seven, M1–M8's kills with their reverts, the control, Step 8's three; `body.sh`; the subject byte-exact.

**Tests (assertion → mutant; fixture → discriminating row).** lan off → M1; module present → M2; four distinct ports → M3 (row: a duplicated port, not a missing world); firewall closed → M4 (row: 443 itself); timer declared-and-off → M5 (row: both arms — declared-enabled and undeclared — fail); parity → M6 (row: this repo's other nixpkgs rev, so the two revs differ but both exist); operator → M7; MAP current → M8. Control: the neighbour's parity throw.

**probes:**
- media-input-line: `grep -c 'media.url = "git+file:///home/dalhaka/flakes/media?ref=main";' flake.nix` :: ge 1 :: Files (i)
- media-module-line: `grep -c 'media.nixosModules.comfyui-worlds' flake.nix` :: ge 1 :: Files (iii); M2 reads 0
- lan-off: `nix eval .#nixosConfigurations.core.config.services.comfyui-worlds.lan.enable` :: eq false :: Interface 1, Q3(a)
- probe-timer-off: `nix eval .#nixosConfigurations.core.config.systemd.user.timers.comfy-upstream-probe.enable` :: eq false :: Interface 1, Q2(b)
- world-names: `nix eval --json .#nixosConfigurations.core.config.services.comfyui-worlds.worlds --apply builtins.attrNames` :: eq ["nsfw","sfw"] :: Interface 2
- media-parity: `nix develop -c jq -r '.nodes[.nodes.media.inputs.nixpkgs].locked.rev == .nodes["nixpkgs-host"].locked.rev' flake.lock` :: eq true :: Interface 4, decision 43b
- hosts-map-line: `grep -c 'hosts/core/media-worlds.nix' docs/MAP.md` :: ge 1 :: Interface 5; M8 reads 0

### GN4 (docs, XS) — the upstream probe keeps invariant 3: the decision recorded, no egress exception

**dependsOn:** GN1
**touches:** `docs/decisions/2026-09-14-generation-probe-egress.md`
**acceptance:** subsystems-manifest, lint
**commit subject:** generation: the upstream probe keeps invariant 3 — no egress exception, the timer stays off core (test: subsystems-manifest, lint)

**Why.** Spec §5.3: the media design claims the probe may use "direct HTTPS to GitHub and PyPI as an operator tool (the egress invariant binds agents …)" while the decision it cites concludes "The media flake stays brokered (it is closer to an agent than to an app)" (`docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md`, `grep -n 'stays brokered'`). Q2's answer must be written where decisions live, with its interim and its closing condition, so the next reader does not relitigate it; the file is the one path GN1 pre-owns.

**Files.**
- Create `docs/decisions/2026-09-14-generation-probe-egress.md`, verbatim (indented two spaces here for the brief extractor; the file's lines start at column 0):

  ```markdown
  # Decision 2026-09-14 — the upstream probe keeps invariant 3 (no egress exception)

  **Operator, plan 2026-09-11-generation question 2:** (b) — no exception.

  ## Decision

  `comfy-upstream-probe` (`~/flakes/media/pkgs/comfy-upstream-probe/probe.py`) is
  tooling that fetches from the network and proposes dependency bumps to a tree
  agents execute. Brief §3 invariant 3 binds it: every byte it sends crosses the
  broker chokepoint or is not sent. The media design's carve-out
  (`docs/superpowers/specs/2026-09-05-comfy-worlds-design.md:252-255` in
  `~/flakes/media`) is withdrawn; the decision it cited
  (`docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md`)
  grants exceptions to the operator's desktop apps only and concludes "The
  media flake stays brokered".

  ## Interim

  Until the probe runs inside the `media` broker namespace, its timer is
  disabled on `core` by `hosts/core/media-worlds.nix`
  (`systemd.user.timers."comfy-upstream-probe".enable = false`) and asserted so
  by `checks.host-core`. A hand run from `~/flakes/media` is the operator's own
  act under the 2026-09-02 reading, never a unit's.

  ## Closes when

  A media-side task lands the probe as a system unit joining `egress-media`
  (the instance reserved at `10.100.2.x`, `hosts/core/lanes.nix`), with
  `HTTPS_PROXY` and `SSL_CERT_FILE` from that instance, the instance's `allow`
  exactly the six hosts below and no `inject`, and the probe refusing to open a
  socket when either variable is unset (exit 3, one line naming invariant 3).
  Then the timer line is removed and the `host-core` assertion inverts.

  ## The hosts (measured 2026-09-12, judgement of the first generation draft)

  - `api.github.com`
  - `raw.githubusercontent.com`
  - `pypi.org`
  - `www.nvidia.com`
  - `download.nvidia.com`
  - `github.com`

  ## Sources

  `docs/context/generation.md` §5.3; `docs/brief.md` §3 invariant 3;
  `nixosModules/egressBroker.nix` (a broker listener answers only from inside
  its namespace: `iifname != "veb-${name}" drop`);
  `docs/decisions/2026-09-09-redesign-answers.md` §6 (`curl -x` from the host
  returns `http=000`).
  ```

**Interfaces.**
1. The file exists at the path GN1's row names and resolves to `['Generation']` (GN1 Interface 1), so `subsystems-manifest` stays green with the file in the tree.
2. Structure: one H1; `grep -c '^## ' <file>` → `5` (Decision, Interim, Closes when, The hosts, Sources); `grep -c '^- `[a-z0-9.]*`$' <file>` → `6`.
3. Nothing else in the tree changes; no runbook, no board prose (the orchestrator's).

**Facts.** GN1's fnmatch line and the guard replay (its **Why**); the broker's nft line (Q2); lanes.nix's reservation (Assumption 11); the six hosts (Assumption 21).

**Steps.**
1. **Red.** `ls docs/decisions/2026-09-14-generation-probe-egress.md` → `No such file or directory`; `git ls-files | nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --files /dev/stdin; echo rc=$?` → no line naming the file, `rc=0` (GN1 landed, the tree covered).
2. Write the file as **Files** says; `git add docs/decisions/2026-09-14-generation-probe-egress.md`.
3. **Green.** Interface 2's two counts → `5`, `6`; Step 1's validate → still silent, `rc=0` (the new path is owned); `nix build .#checks.x86_64-linux.subsystems-manifest -L --no-link; nix build .#checks.x86_64-linux.lint -L --no-link` → both exit 0.
4. **Mutants** (applied, killed, reverted):
   - **M1 wrong-path** — write the file as `docs/decisions/2026-09-14-probe-egress.md` instead. Kill: the validate → `uncovered: docs/decisions/2026-09-14-probe-egress.md`, `rc=1`.
   - **M2 no-closing-condition** — delete the `## Closes when` section. Kill: `grep -c '^## '` → `4`.
   - **M3 seventh-host** — add a `pypi` bullet to the list. Kill: the hosts count → `7`.
   - **Negative control** — `test_clean_fixture_passes` (GN1's control) passes; the unowned-path mutant fails it.
5. **Commit** (G6): `cmds.txt` = Step 1's two, Step 3's four, M1–M3's kills; `body.sh`; the subject byte-exact.

**Tests (assertion → mutant; fixture → discriminating row).** Interface 1 → M1 (row: a path off by one word, still under `docs/decisions/`); Interface 2's section count → M2; the hosts count → M3 (row: the regex literal the record names as the false seventh).

**probes:**
- decision-present: `test -f docs/decisions/2026-09-14-generation-probe-egress.md && echo 1 || echo 0` :: ge 1 :: Interface 1; M1 reads 0
- decision-sections: `grep -c '^## ' docs/decisions/2026-09-14-generation-probe-egress.md` :: ge 5 :: Interface 2; M2 reads 4
- decision-hosts: `grep -c '^- `[a-z0-9.]*`$' docs/decisions/2026-09-14-generation-probe-egress.md` :: ge 6 :: Interface 2, Assumption 21; a dropped host reads 5
- decision-hosts-exact: `grep -c '^- `[a-z0-9.]*`$' docs/decisions/2026-09-14-generation-probe-egress.md` :: le 6 :: Interface 2; M3 reads 7
