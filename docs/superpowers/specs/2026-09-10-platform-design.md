# Platform subsystem design

**Date:** 2026-09-10 (drafted by the OpenRouter lane's best model).
**Authority:** decisions 35b, 36a, 37a, 38b, 39b, 40a, 41a, 42a, 43b, 44 (all
seven absorbed), 47a, 48a; the charter's §2 Platform row; the program plan's
closeout decisions (68, 74–80). **Superseded:** the brief's §6 layout — the
tree no longer matches it. **Not superseded:** brief §3's six invariants,
re-ratified after the rules audit (answers 49, 55).

**What this spec covers:** the patch series mechanism, the pin policy, the first
absorbed sibling (dsh-harness), and the questions the charter leaves open for
the operator. It does not cover Helm's patch-queue view (Helm, increment 3), the
patch ledger (EV6), the harness payload's seat-side consumption (Seat/Harness),
or the five remaining siblings (increment 4).

**Size:** M (under 4000 words per plan.js's sizer).

---

## §1 What the Platform subsystem is

**Manifest row.** `docs/ledger/subsystems.toml` at `name = "Platform"`: `prefix = "PL"`,
`area = "platform"`, `gate = "opus"`, `depends = []`. It is
one of three subsystems with an empty `depends` (Program and Knowledge are the
other two); five others name Platform in theirs.
Owns `flake.nix`, `hosts/core`, pins, the patch system, the vendored upstreams
(dsh, claude-code, ComfyUI), the absorption of the siblings, and switches
(charter §2).

**What does not exist at spec time** (`ls patches docs/ledger/patches.toml
pkgs/claude-code pkgs/comfyui hosts/node2 hosts/node3` → all absent). Every
task in this spec creates what it names.

**The invariants that bind every task here (G12):**

1. Decrypted basket contents exist only in tmpfs for the agent's lifetime.
   No PL task touches basket mounting.
2. No agent process holds a provider credential in plaintext. No PL task
   touches a credential field.
3. Every byte leaving the machine crosses one chokepoint. No PL task touches
   the broker.
4. An environment is reproducible from `flake.lock` + `baskets.lock` +
   one YubiKey. PL5 lands what lets Seat/Harness retire the two hand-made
   symlinks (`~/.local/share/dsh-openrouter/{AGENTS.md,skills}`) — invariant
   4's one measured live violation (the `pkgs/dsh-openrouter/dsh-openrouter.sh`
   symlink deployment comment block).
5. Policy is Nix configuration reviewable in a diff. PL1–PL6 are
   configuration and ledgers reviewable in a diff.
6. No agent-authored code is promoted between baskets. No PL task touches
   this.

---

## §2 The patch series

Decisions 37a, 38b, 46a, 47a. The shape is fixed: numbered patches under
`patches/<pkg>/NNNN-<name>.patch` applied in `postPatch` of the vendored
upstream derivation. The mechanism covers every vendored third-party upstream:
dsh, claude-code, ComfyUI (decision 38b). A plugin is used only where it
reaches the same behaviour with a smaller re-port surface; the ledger records
which.

### §2.1 Directory layout

```
patches/
  README.md                 # on-disk contract
  dsh/
    0001-seat-hooks.patch
    0002-spill-path.patch
  claude-code/
    0001-managed-settings.patch
  comfyui/                  # when absorbed (increment 3)
    0001-worlds-feed.patch
```

Each directory holds `NNNN-<name>.patch` files (zero-padded, four digits) and
a `README.md` describing what the series does. Nothing else. `readSeries`
(`lib/patchSeries.nix`) throws on a stray file, a duplicate number, or a
subdirectory.

### §2.2 The mechanism

`lib/patchSeries.nix` exports three functions:

1. `readSeries dir` — returns the sorted paths of `NNNN-*.patch` files in
   `dir`. Throws on a duplicate number or a stray entry (only `NNNN-*.patch`
   and `README.md` are allowed). An empty directory or one holding only
   `README.md` returns `[ ]`.
2. `renderPostPatch dir` — returns the shell text applying each patch in
   order with `patch -p1 --no-backup-if-mismatch`. No `|| true` — a
   re-applied or failed patch exits 1 and fails the build.
3. `applySeries dir pkg` — if `readSeries` returns `[ ]`, returns `pkg`
   unchanged (same derivation). Otherwise returns
   `pkg.overrideAttrs (old: { postPatch = (old.postPatch or "") +
   renderPostPatch dir; })`.

`self.lib.patchSeries.applyTo "<pkg>"` is the one call site consumers use,
defined in `flake.nix`.

### §2.3 What is enforced

- **Patch-series-eval** check: the good fixture series applied to a test
  source produces exactly the expected output. An empty series returns the
  derivation unchanged.
- **Patch-series-negative** check: duplicate numbers, stray files, and
  non-applying patches are all refused. The good series under the same runner
  passes.
- **Core-patches-wiring** check (eval-time): `/etc/helm/patches.json` in the
  closure lists the patches the next switch carries, modelled after
  `core-gaming-wiring`.

### §2.4 When a pin bump breaks a patch

Decision 47a: the build fails hard. The pin bump is a typed task whose
acceptance is a re-port of every patch in the ledger (`docs/ledger/patches.toml`).
A silently skipped patch is a behaviour change that reaches the seat at the
operator's next switch with nothing in the diff to show it.

---

## §3 The pin policy

Decision 43b: keep the documented `nixpkgs` plus `nixpkgs-host` pair.
Absorbed subsystems move onto `nixpkgs-host`. `llm-agents` stays on its own
pin (the `pnpmConfigHook` incompatibility documented in `flake.nix:7-19`).

**Cadence** (A26, assumed): on need — only when a typed task needs an upstream
change, at most one per increment. Every bump costs a re-port of every patch.
The cadence is re-visited at each increment's re-plan.

**Pin bump procedure** (PL7):
1. Change the flake input's `url` or `ref` to point at the new rev.
2. Run `nix flake lock --update-input <name>`.
3. Attempt to build every check that depends on the bumped package.
4. For each patch that no longer applies: remove it, write a replacement,
   update `docs/ledger/patches.toml` with the new date and reason.
5. Commit the bump, the new patches, and the updated ledger as one task.

---

## §4 The first absorbed sibling: dsh-harness

Decisions 35b, 44, 48a, 36a, 40a, 41a, 43b. dsh-harness is the first
sibling absorbed because it carries no `flake.nix` (A20: `git ls-files | grep
-c 'flake\.\(nix\|lock\)'` → `0`), so no lock conflict, no flake eval
cost, and the payload it carries (AGENTS.md, 17 skills) is the one measured
live violation of invariant 4.

### §4.1 Landing

Decision 48a: a subtree-style merge with `--allow-unrelated-histories` so
every commit stays reachable under its new subdirectory. Every hash the board
and evidence store cite (dsh-harness's head `d1b5f85` at spec time) remains
resolvable.

The landing is a **human act** (Q6 recommendation b): the orchestrator merges
on a branch `absorb/dsh-harness` with `git subtree add --prefix=pkgs/dsh-harness … --no-squash`, runs `treefmt` inside the `--no-commit` merge, creates
one merge commit, and tags `absorbed/dsh-harness-<rev>`. The landing has no
key and is never a seat task; PL5 runs on top of it.

### §4.2 The source derivation (PL5)

The landed tree under `pkgs/dsh-harness` is not a flake (A20), so PL5 creates
`self.packages.x86_64-linux.dsh-harness-src` — a `runCommand` on `nixpkgs-host`
that copies the tree and asserts at build time that:
- Every `SKILL.md` has a `name:` and `description:` line (A20: 0 missing
  today).
- The file count is ≥ 99 (the count at absorption).
- No file is executable that should not be.

The derivation is consumed by SA8's `harnessPayload` input. When SA8 binds it
and retires the two hand-made symlinks, invariant 4's last measured violation
is closed.

---

## §5 The Flake change plan

All PL tasks modify `flake.nix` in three named regions:
the `inputs` binding (the `inputs = {` block in the flake's
attribute set), the `coreSpecialArgs` binding (in the `outputs`'s `let`
expression) and the `lib` attribute (of the attribute set `outputs`
returns, after the `in`), and the `checks.${system}` binding
(the attribute set of per-system checks).
No PL task adds a new NixOS module or touches broker wiring (IS4's assertions
bind, A10).

```
Region 1: inputs
Region 2: coreSpecialArgs + lib (within outputs' let)
Region 3: checks.${system}
```

### §5.1 PL2 — lib/patchSeries.nix + checks

Adds `self.lib.patchSeries` (four names: `readSeries`, `renderPostPatch`,
`applySeries`, `applyTo`), plus `patch-series-eval` and
`patch-series-negative` checks. Creates `patches/README.md` and thirteen
fixture files.

### §5.2 PL3 — first patch consumer (claude-code)

Applies `applyTo "claude-code"` on the `llm-agents` input's claude-code
package, setting its `postPatch` from the `patches/claude-code/` series.
Adds the `core-patches-wiring` check. The series is empty at this increment;
the check asserts it is empty and that `/etc/helm/patches.json` exists in the
closure.

### §5.3 PL4 — the patches wiring and closure view

Wires `etc/helm/patches.json` into the closure, listing every patch directory
and its file count (the list the next switch carries). Adds assertions to
`core-patches-wiring` that the file is present and well-formed. Adds the
`hosts/core` import if needed.

### §5.4 PL5 — dsh-harness source derivation

Adds `dsh-harness-src` to `packages.${system}`, consuming the landed subtree
at `pkgs/dsh-harness/`. Adds `dsh-harness-eval` check that builds it and
asserts the SKILL.md invariants. Runs only after the landing act (Q6) has
merged and tagged the subtree.

### §5.5 PL6 — the record

Adds a record file for the absorption (untyped, uncovered by
`docs/superpowers/plans/*` per EV10's glob). Updates
`docs/ledger/repos.toml` if the sibling repo row is no longer needed (once
the archive step in `## Operator` runs). No touch of
`docs/ledger/subsystems.toml` — PL1 already owns that.

### §5.6 PL7 — pin procedure document

Writes `docs/runbooks/pin-bump.md`, the procedure from §3. Named `areas:
platform, knowledge` because `docs/runbooks/*` is Knowledge's manifest
glob.

---

## §6 Questions for the operator

Two items the charter leaves open and one from the program plan's review.

### Q1 — node2 and node3 (charter §8 item 1)

**Bound.** The brief names node2 (RTX 3060, 31 GB) and node3 (RTX 4080 Super,
~32 GB, offline) as hardware nodes for portability (brief §6). Answer 5
retired OpenClaw and kept Hermes, but left "node2/node3 not covered by this
answer". The charter §3 lists them as open.

(a) Retire both: name them as hosts with no work scheduled, under
    Knowledge's rules audit. No `hosts/node2` or `hosts/node3` directory is
    ever created. Portability is demonstrated by a VM or by keeping the
    mainboard as the one target.
(b) Name them as future targets with no work this increment: create stub
    `hosts/node2/default.nix` and `hosts/node3/default.nix` that import
    `../core` and override hardware, but schedule no wiring checks and no
    build gate. This defers portability to a later increment.
(c) Build: absorb node2 into the increment as a build target. The operator
    runs `nix build .#nixosConfigurations.node2.config.system.build.toplevel`
    as one acceptance step. This requires the node2 hardware config to be
    written and a wiring check to pass.

**Recommendation:** (a) — every node that exists only in the brief and never
in the tree is a maintenance debt; the program should either commit to a
node or remove it. The rules audit (Knowledge, increment 1) is the right
place to make the call.

### Q2 — the dsh pin cadence (charter §8 item 5)

**Bound.** Decision 47a says a failed patch at a pin bump is a hard build
failure and a typed task. But it does not say how often a bump happens.
The draft of this spec assumes "on need" (A26); the operator may override.

(a) On need: only when a typed task requires an upstream change, at most
    one per increment. Every bump costs a re-port of every patch.
(b) Calendar: one bump per month regardless of need. The re-port cost is
    a standing maintenance task.
(c) Per increment: every increment opens with a pin bump and re-port.
    Patches that still apply are verified; those that do not are re-written.

**Recommendation:** (a) — a calendar bump with an empty series costs a build
and a review for zero benefit, and a per-increment bump compounds on
absorption increments.

### Q3 — the build-time half of the patch-queue view (from the program plan's review)

**Bound.** Decision 39b says the Helm view lists "the patches the next switch
carries and the generation each one landed in". The build-time half is
`/etc/helm/patches.json` in the closure (the file PL4 creates). The
question is whether PL4 renders this file into the closure directly (PL4's
task) or whether Helm's increment-3 task derives the list from the tree and
the store.

(a) PL4 renders `/etc/helm/patches.json` into the closure. PL4 as written.
(b) PL4 is withdrawn by a status row; PL3's `dependsOn` moves to PL3's
    successor; Helm derives the list from the tree and the store.
    Helm's plan gains the derivation.

**Recommendation:** (a) — "the patches the next switch carries" is a fact
about the built closure, not the tree; `/etc/helm/profile` under
`core-gaming-wiring` is the house model.

---

## §7 Operator

The Platform component of increment 2's composed drill, run after PL4, PL5
and PL6 have integrated:

1. `git -C ~/nixos-agent-env merge-base --is-ancestor $(git -C
   ~/flakes/dsh-harness rev-parse HEAD) HEAD && echo reachable` →
   `reachable` (48a); `git tag -l 'absorbed/dsh-harness-*'` lists the
   landing tag.
2. `nix build .#nixosConfigurations.core.config.system.build.toplevel &&
   nix store diff-closures /run/current-system ./result` → `etc` (the new
   `helm/patches.json`), the `claude-code` path only if a patch is in its
   series (none this increment), nothing beyond this plan.
3. `nix build .#checks.x86_64-linux.{patch-series-eval,patch-series-negative,
   core-patches-wiring,dsh-harness-eval,host-core,lint} -L
   --no-link` → all green.
4. The operator switches (G1; never an agent).
5. `cat /etc/helm/patches.json` → `{"claude-code":[]}` (and a `dsh` key once
   Seat/Harness's hook lands); `readlink /run/current-system` → the new
   generation.
6. `nix develop -c python3 pkgs/evidence/tasks.py --root . brief` →
   `Area: platform` shows PL1–PL7 landed; `… check` → exit 0.
7. Only then the operator archives `~/flakes/dsh-harness` (`mv
   ~/flakes/dsh-harness ~/factory/archive/dsh-harness-$(date +%F)`, the
   pattern `~/factory/archive/codex-2026-09-06` followed) — after
   Seat/Harness's task retires the two symlinks, which until then point
   into it. The operator retires the working repo, never an agent.

**Rollback.** A generation rollback by the operator undoes PL4's and PL5's
closure. `git revert -m 1 <landing merge>` plus plain reverts of PL5 and
PL6 undo the absorption; the tag keeps every hash reachable. PL2 and PL3
with an empty series revert as plain commits. `~/flakes/dsh-harness` is
untouched until step 7.

---

## §8 Not in this spec

- The five remaining siblings — gaming, nixos-skill, codex, openai-lab,
  chatgpt-work — increment 4, re-planned against the landed tree.
- The Nix-built harness payload and the symlink retirement — Seat/Harness
  (36a).
- `docs/ledger/patches.toml` and its validator — EV6 (46a).
- The Helm patch-queue view — Helm, increment 3 (39b's other half).
- The `applyTo "dsh"` and `applyTo "comfyui"` call sites — Seat/Harness
  and Generation.
- The per-subsystem split of `flake.nix`'s checks and the import assertion
  (answer 4a) — Program, increment 1.
- The OAuth / Proton Pass / router spike — Isolation, docs, increment 1.
- node2 and node3 — resolved by Q1 above.
- `nixosModules/cowork.nix` retirement — parked stays parked.
- Any pin bump — none this increment; PL7 writes the procedure only.
- Broker wiring of any kind — IS4's assertions bind.
- `hosts/core/hardware-configuration.nix` — never touched (G10).