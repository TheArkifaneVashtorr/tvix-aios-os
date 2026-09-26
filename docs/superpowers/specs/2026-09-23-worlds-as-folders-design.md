# Worlds as folders — design

**Status:** draft, 2026-09-23. Measured on core at generation 85.

## 1. The direction, and what is already true

Operator, 2026-09-23: "NSFW and SFW need to be condensed. Folders that
generate from the folder content are the way to go." Asked for a shape, the
operator chose **template units, instanced per folder**: Nix declares the
templates and the rules, a world comes into existence when its folder does, and
everything that makes one world different from another lives in the folder.

Most of that is already true, which is why this is a modest change rather than
a rewrite:

- **There is already one module, not two copies.**
  `media/nixosModules/comfyui-worlds.nix` declares `worlds` as an
  `attrsOf submodule`, and `genUnit`, `mutateUnit`, `runUnit` and `targetUnit`
  are all functions of the world name. The only per-world Nix setting in use is
  the port (`hosts/core/media-worlds.nix:21-24`: `sfw.comfyPort = 8188`,
  `nsfw.comfyPort = 8189`).
- **The real differences are already folder content.** Under
  `~/comfyui/worlds/<world>/`: `lab/manifest.toml` (its own git repository)
  carries the model roster with its LoRA cards, the `[author]` brief with its
  required and banned terms, and the `[mutate]` rules; `lab/prompts/` holds
  every authored batch; `models/` symlinks into the shared hash-addressed
  `~/comfyui/store/`; `feed.sqlite` holds renders, likes and jobs. The sfw and
  nsfw worlds differ in exactly these files and nowhere else of substance.

**What is not yet folder-driven** — the four things this design moves:

1. **Whether a world exists.** A world is an entry in a Nix attrset; adding one
   means editing `hosts/core/media-worlds.nix` and switching. Nothing scans
   `~/comfyui/worlds/*`.
2. **Its port** — rendered into the unit's argv at build time
   (`comfyui-worlds.nix:84`).
3. **Its authoring knobs** — `author.{promptsPerBatch, verdictWindow,
   variantsPerPrompt, lowWater, tickSeconds}` and `deck.lowWater` — rendered
   into `/etc/comfy-worlds.json` (`comfyui-worlds.nix:519-526`), though
   currently left at their module defaults for both worlds.
4. **The feed's list of worlds** — `worldsOrder` in that same JSON, derived
   from the Nix attrset.

## 2. The line between Nix and the folder

Brief invariant 5 keeps declarative policy in Nix, never in a runtime-editable
file. A folder that can create a world sounds like it crosses that line; it
does not, provided the line is drawn by kind:

- **Anything that is a limit or a permission stays in Nix.** Which ports the
  worlds may use, the resource slice and its weights, what the author model may
  read, classification, the systemd hardening, how many worlds may run at once.
- **Anything that is *what to generate* lives in the folder.** The roster, the
  brief, the mutation rules, the authoring cadence, the deck's low-water mark.

Under that rule a world's folder can no more grant itself a capability than a
document can grant its editor root. The templates are declared; the instances
are data.

## 3. The design

**Templates.** `comfyui@`, `comfy-run@`, `comfy-mutate@` and a
`comfy-world@.target`, each parameterised by the world name (`%i`). They carry
everything the current per-world units carry except what moves to the folder.
The feed stays one process serving every world.

**A reconciler instantiates them.** It scans `~/comfyui/worlds/*`, treats a
folder as a world when it holds a valid `lab/manifest.toml`, and enables the
instances for it. A folder removed or invalidated has its instances stopped,
never its data touched. This is the same reconciler shape as the
[job reconciler](2026-09-23-job-reconciler-design.md): durable state on disk,
converged on every tick, a reboot being an ordinary tick.

**Ports** come from a range declared in Nix. The first time a world is seen,
the reconciler assigns the lowest free port in the range and writes it into the
folder, so a world keeps its port across restarts and a folder moved elsewhere
carries it. Two folders claiming one port is a refusal, not a race.

**The feed** reads its world list from the reconciler's view rather than from
`/etc/comfy-worlds.json`, and each world's knobs from its manifest.

**The author model stays host-wide.** There is one GPU and one author model; it
serves whichever world is authoring. Making it per-folder would multiply a 20 GB
model by the number of worlds for no gain.

### 3.1 Model separation

Operator, 2026-09-24: the design carries a separation check. Today nothing
enforces one. A model lives once in the content-addressed store,
`~/comfyui/store/<sha256>/<file>` (`media/pkgs/media-fetch/fetch.py:171-172`),
shared by every world; each world has its own `models/` symlinks and its own
git-tracked `lab/manifest.toml` (`fetch.py:175-191`,
`media/pkgs/comfy-worlds/init.sh:123-132`). Adopting a file whose bytes are
already stored links the existing cell without a word (`fetch.py:235-238`).
The generators' `Conflicts=` (`media/nixosModules/comfyui-worlds.nix:111`) is
runtime exclusivity, not content separation; `comfy-world-guard`, their
`ExecStartPre`, checks only that the tree exists
(`media/pkgs/comfy-worlds/default.nix:41-51`); the
`comfy-worlds-assertion-negative-*` checks (`media/checks.nix:1250-1365`) cover
ports, listen address, name and the cards' egress, not roster content. One
store file can be linked into two worlds and nothing notices.

**The guarantee.** A world may link only store entries its own manifest
claims. Refused:

- a store entry claimed by more than one world's manifest, unless every
  claiming manifest marks that row `shared = true` — a deliberate, reviewable
  cross-world share, such as a VAE;
- a `models/` symlink that resolves outside the store, dangles, or points at a
  store hash no row of its world's manifest claims;
- a manifest row whose file's sha256 does not match its store path.

A refusal names every world involved and the hash.

**Where it runs.** Host-side, reading the off-repo folders: in the reconciler,
before it starts a world's instances — a world that fails does not start, the
others do, and a refused share fails every world that claims it — and as a
standalone `comfy-worlds check` verb the operator can run at any time, exiting
non-zero on any refusal. Re-hashing every cell is the costly rule: the verb
runs it in full; the reconciler runs it on a world's first start and whenever a
claimed cell's size or mtime changes. This keeps §6 by construction: rosters
are read where they live, refusal lines go to the journal and the terminal,
and any evidence row carries only world names and a refusal count.

**Tests.** Fixtures build a two-world tree over a scratch store of small byte
files, hashes computed at test time:

- two manifests claim one LoRA's hash, neither shared → refused, the message
  naming both worlds and the hash;
- the same with `shared = true` in both → passes, and both worlds start;
  in only one → refused;
- a symlink outside the store, and a dangling one → refused;
- a row whose cell hashes differently → refused.

The verb-level fixtures join `comfy-worlds-unit` (`media/checks.nix:1396`),
which today runs `bats tests/comfy-worlds` (`:1436`) and pytest over the same
directory (`:1557`). The start/no-start pair joins `comfy-worlds-vm`
(`media/checks.nix:1591`, `media/tests/integration/comfy-worlds-vm.nix`), the
family that already boots the worlds as a user. Each is shown red before the
check exists.

## 4. The hard part: one GPU, many instances

Today GPU exclusivity is `Conflicts=` between named units: each generator
conflicts with the other world's generator, and the author model conflicts with
both (`comfyui-worlds.nix:95`, `local-model.nix:35`). **A template cannot
enumerate its own siblings**, so `Conflicts=` cannot express "at most one
`comfyui@` instance at a time". Something else has to own that rule, and it is
the design's one genuinely open decision.

The candidates:

- **The reconciler owns it** — it starts at most one generator instance and
  stops the others before starting another. Keeps policy in one place, but the
  reconciler becomes a scheduler.
- **A lock around the GPU** — each generator takes a host-wide lock before
  starting. Simple, but a unit blocked on a lock sits in `activating`, and that
  is the shape of the `Type=oneshot` infinite-timeout hazard this project has
  already hit once.
- **The author model keeps its `Conflicts=`** against a single target that every
  generator instance is part of, and generators serialise through the reconciler.

Whatever is chosen must not reopen `BUG-world-target-supervisor-deadlock`
(`docs/ledger/bugs.toml`): a world's target must still not pull in its
supervisor, for the same measured reason as GN43's revert. This spec does not
choose; the plan's first task is the measurement that decides it.

## 5. What lands first

Two bugs are fixed ahead of this design, on the operator's word, because they
cost work daily and do not depend on how the redesign lands:

- **GN57** — jobs ComfyUI had accepted are orphaned forever when the generator
  restarts, because nothing resubmits a `submitted` job whose prompt the
  generator no longer knows. Measured in the nsfw world: 10,161 mutate, 410
  regenerate and 217 edit jobs stuck. Any future owner of the generator will
  still stop it, so this fix outlives the redesign.
- **GN58** — the generation off switch does not stay off, because the deck's
  low-water refill restarts the loop without checking it. Its durable "off"
  flag lives in the world folder, which is where this design wants every
  per-world fact.

The [resource-control design](2026-09-23-world-resource-control-design.md)
composes cleanly: every template instance takes `Slice=comfy.slice`, which is
simpler with templates than with per-world units.

## 6. Classification

The nsfw roster's names are outside the repository today — not by rule, but
because the folder is not in the tree the publish gate scans. This design keeps
all world content in folders under `~/comfyui/worlds/`, so that stays true, and
it must stay true by construction: the reconciler, the feed and any Helm tile
report worlds by name and count, never by roster content, and nothing about a
world's contents is written into a tracked file.

## 7. Acceptance

- Creating a folder with a valid manifest brings a world up without a rebuild
  or a switch; removing it stops its instances and leaves its data intact.
- sfw and nsfw migrate as two folders with their current state unchanged — the
  same rosters, briefs, feeds and history — and only their unit names change.
- A world keeps its port across restarts; two folders claiming one port is
  refused.
- No more than one generator instance holds the GPU at any moment, asserted in
  the worlds VM check.
- A folder cannot grant itself anything §2 keeps in Nix: a manifest naming a
  port outside the range, or a resource setting, is refused.
- No world's roster content appears in any tracked file, evidence row or tile.
- A store entry linked into two worlds is refused, naming both worlds and the
  hash, unless both manifests mark it `shared = true`; a symlink outside the
  store, dangling or at an unclaimed hash, and a hash mismatch, are refused; the
  failing world does not start and the others do (§3.1, asserted in
  `comfy-worlds-unit` and `comfy-worlds-vm`).

## 8. Not in this design

Changing what a world generates, the authoring cadence's defaults, or the
author model. Checkpoint rotation (GN53). The job queue's semantics beyond
GN57. Any change to the one-GPU rule itself.

## 9. Open questions

- GPU exclusivity under templates — §4; the plan's first task measures it.
- Does `shared = true` need every claiming world's manifest, or a separate
  top-level allowlist? **Recommended, and the default:** every claiming
  manifest, so each share is reviewable in each world's lab git. A runtime
  allowlist would be cross-world policy in an editable file, which §2 puts in
  Nix; an allowlist in Nix would name store hashes in the repository, against
  §6.
