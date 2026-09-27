# Target: docs/context/generation.md

## Size
- Word count: `wc -w /home/user/tvix-aios-os/docs/context/generation.md` → **3636**
- Rule: S ≤ 1500, M ≤ 4000, L above → **M** (3636 ≤ 4000). Not refused.

## Numbered items
The spec is not written as a flat numbered list; its only explicit numbered
list is §5 "Open questions the plan must answer" (8 items, 1–8). Numbering
them here as found in the file:

1. Which plan file the manifest names for GN (answered at `1ae7328`) — precondition, not open.
2. WH1 and WH2 are typed but invisible to the queue.
3. The upstream probe's egress carve-out.
4. What "rules" means for the mutator.
5. Where the feed's state lives.
6. How far "media absorbed" goes in this batch.
7. UNVERIFIABLE: whether `nix flake check -L` is green in `~/flakes/media` at HEAD `1618638`.
8. UNVERIFIABLE: live state of `comfy-upstream-probe.timer` on `core`.

(Sections themselves are numbered §1–§7: §1 ownership, §2 code as it stands,
§3 what binds it, §4 the record, §5 open questions, §6 out of scope, §7 sources.)

## Files, options, checks and commands the spec names, each read with its anchor

### Ledger / manifest files (this repo)
- `docs/ledger/subsystems.toml` — Generation row.
  Command run: `grep -n "^name = \"Generation\"" docs/ledger/subsystems.toml`
  Anchor: `213:name = "Generation"`
- `docs/ledger/subsystems.toml:218-221` — Generation's `plans` list, includes
  `docs/superpowers/plans/2026-09-11-generation.md`.
  Command run: `grep -rn "generation.md" docs/ledger/subsystems.toml`
  Anchor: `220:  "docs/superpowers/plans/2026-09-11-generation.md",`
- `docs/context/*.md` — the nine context blocks the spec says landed alongside
  this file.
  Command run: `ls docs/context/`
  Anchor: `defects.md evidence.md factory.md generation.md helm.md isolation.md
  knowledge.md platform.md seat-harness.md` (9 files, this file among them)
- `flake.nix` — checked for any reference wiring `docs/context/*` into the
  `subsystems-manifest` check's ownership globs.
  Command run: `grep -n "docs/context" flake.nix`
  Anchor: no hits — confirms the spec's claim that no row's `owns` glob covers
  `docs/context/*`.

### Other files/options/checks/commands the spec itself names (read in the spec's own text, not independently re-verified here per the read-only remit of this phase)
These are enumerated as named by the spec; this phase's remit is to catalog
what the spec cites, not to re-run every one of the spec's own historical
measurements (the spec itself already carries its command+anchor pairs for
each, e.g. `sed -n '212,222p' docs/ledger/subsystems.toml`,
`pkgs/evidence/subsystems.py:219-221`, `flake.nix:1519-1535`,
`pkgs/evidence/tasks.py:476`, `pkgs/evidence/tasks.py:42-43`,
`pkgs/evidence/tasks.py:1817-1849`, `pkgs/evidence/tasks.py:1824-1834`,
`docs/ledger/repos.toml:11-12`, `docs/ledger/areas-grandfather.toml`,
`docs/ledger/rules.toml`, `docs/ledger/plan-status.toml:75-77,87-89,152-161`,
`docs/ledger/plan-defects.toml`, `docs/ledger/claims.toml:154-162`,
`docs/ledger/openrouter-prices.csv:3-4`, `docs/brief.md:68-79`,
`docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md:17-18`,
`docs/decisions/2026-09-09-redesign-answers.md:27-30`,
`docs/concepts/2026-09-09a-redesign-charter.md:52,65,67-68,173,175,179-180`,
`docs/concepts/2026-09-06a-generation-lab.md:1-3`,
`docs/research-2026-09-09-redesign-loose-ends.md:187-195`,
`docs/superpowers/plans/2026-09-09-program.md:41,44,348,899,909`,
`hosts/core/helm.nix:12-13`, `pkgs/helm/collect.py`, `pkgs/evidence/SCHEMA.md`.
- Sibling repo `~/flakes/media` files: `flake.nix` (892 lines),
  `nixosModules/comfyui.nix` (431), `nixosModules/comfyui-worlds.nix` (331),
  `pkgs/comfyui/package.nix` (128), `pkgs/comfyui/deps/` (17 files),
  `pkgs/comfy-upstream-probe/probe.py` (622), `pkgs/media-fetch/fetch.py`
  (341), `models/manifest.toml` (185), `pkgs/comfy-worlds/feed_placeholder.py`
  (157), `pkgs/comfy-worlds/init.sh` (137), `pkgs/comfy-worlds/media-comfy.sh`
  (61), `pkgs/comfy-worlds/default.nix` (93),
  `docs/superpowers/specs/2026-09-05-comfy-worlds-design.md` (339),
  `docs/runbooks/media.md` (405), `docs/OPERATIONS.md`, `docs/reviews/*.md`,
  `docs/superpowers/plans/2026-09-05-comfy-worlds.md`. These live outside this
  checkout (`/home/dalhaka/flakes/media`) and were not independently re-read
  in this phase — read-only remit is this repo's snapshot.

### Options named
- `services.comfyui.*`: `enable`, `package`, `user`, `group`, `dataDir`,
  `listen.*`, `proxy.*`, `gpu.enable`, `brokerInstance`, `models.*`,
  `resources.*` (no `extraArgs` — deliberately absent).
- `services.comfyui-worlds.*`: `operatorUser`, `root`, `package`, `cpuOnly`,
  `worlds` (`comfyPort`/`feedPort`/`host` per world), `lan`.

### Checks named
- This repo: `subsystems-manifest` (`flake.nix:1519-1535`), `lint`
  (`flake.nix:1386`, `githooks/pre-commit:64`).
- `~/flakes/media` (21 checks): `lint`; `comfyui-package`, `comfyui-eval`,
  `comfyui-cliploader-krea2`, `comfyui-startup-clean`, `comfyui-vm`,
  `comfyui-assertion-negative-{broker,gpu,listen,listen-address,token}`;
  `comfy-worlds-eval`, `comfy-worlds-unit`, `comfy-worlds-vm`,
  `comfy-worlds-assertion-negative-{hosts,name,password-path,ports}`;
  `media-fetch-unit`, `media-fetch-bats`; `comfy-upstream-probe-unit`.

### Commands named
- `nix develop -c python3 pkgs/evidence/subsystems.py validate --counts --root . docs/ledger/subsystems.toml`
- `nix develop -c python3 pkgs/evidence/subsystems.py validate --root . docs/ledger/subsystems.toml`
- `nix develop -c python3 pkgs/evidence/tasks.py --root . brief`
- `nix develop -c python3 pkgs/evidence/tasks.py --root . json`
- `git -C /home/dalhaka/nixos-agent-env log --oneline -1`
- `git -C /home/dalhaka/flakes/media log --oneline -1`
- `nix eval --raw --impure --expr 'builtins.attrNames (builtins.getFlake "git+file:///home/dalhaka/flakes/media").checks.x86_64-linux'` (and same for `packages`/`nixosModules`)
- `grep -n -i media flake.nix`
- `grep -c '^[[rule]]' docs/ledger/rules.toml`
- `grep -c -i 'generation\|comfy\|media\|caddy\|mutator\|swipe\|feed' docs/ledger/rules.toml`
- `grep -h '^usage:' ~/factory/runs/{cw1,cw2,w3b,w5b,w46,w46b,w46c}/*.result`
- `nix flake check -L` (in `~/flakes/media`, at HEAD `1618638`) — explicitly UNVERIFIABLE/not run.

## Decisions the spec leaves open
Per §5 (open questions the plan must answer), items 2–8 are open (item 1 is
resolved/a precondition already satisfied):
- WH1/WH2 re-typing: under the parseable `### KEY (code|docs, XS|S|M|L) —`
  grammar in whichever plan, or superseded by GN-prefixed tasks. No
  recommendation on record.
- The upstream probe's egress carve-out: broker the probe, or record an
  explicit exception decision. No recommendation on record.
- What "rules" means for the mutator: where the grammar lives, what it reads,
  what a red-before-green test looks like. Recommendation on record: rules
  only in this batch; default if silent: c.
- Where the feed's state lives / sub-projects 2 & 3: plan as already
  specified vs. new design. Recommendation on record (Q15): plan as already
  specified; default if silent: a.
- How far "media absorbed" goes in this batch: absorb now, absorb after
  sub-projects 2/3, or keep the split. No recommendation on record.
- Two UNVERIFIABLE items (7, 8) that a plan must treat as explicit assumptions
  rather than facts: media's own `nix flake check -L` greenness at HEAD
  `1618638`, and the live state of `comfy-upstream-probe.timer` on `core`.

## Provenance note
The spec's own header (§0 preamble) states every `path:line` anchor was
re-resolved against `/home/dalhaka/nixos-agent-env` and
`/home/dalhaka/flakes/media` on 2026-09-10 and warns line numbers drift; it
deliberately holds no live task-queue/HEAD snapshot and directs a drafter to
re-read live state via `evidence tasks brief`/`json` and the two repos' `git
log -1` at draft time rather than trust the frozen §4 record for anything but
history (gate verdicts, defect classes, costs).
