# Upstream probes: one runner, four feeds — design

**Status:** draft, 2026-09-23. Measured on core at generation 83.

## 1. The premise, corrected

This project already has an upstream probe, and it works. `comfy-upstream-probe`
runs weekly on core (`Sun 04:00`, `media/nixosModules/comfyui-worlds.nix:487`),
reads the pinned ComfyUI version and thirteen wheel pins, diffs them against the
newest upstream tag's own `requirements.txt` — never PyPI latest — rewrites the
pin literals in a **throwaway clone** under `~/factory/ws/comfy-refresh`,
re-derives hashes, runs `nix flake check -L` there, and writes a brief on red.
It never touches the live repository.

**One correction, measured the same day:** the probe *tries* to record a
`proposals` row and has never once succeeded. It calls `evidence record
proposals` with `"kind": "proposal"`, and `pkgs/evidence/streams.py` declares
no such kind (`:945-964` → `undeclared kind 'proposal'`), so every weekly
proposal has been refused since the probe landed. Its `checks` row does land,
which is why nothing looked wrong. So the proposal row this spec builds on does
not exist yet: declaring the kind is a prerequisite, owned by
[periodic jobs](2026-09-23-periodic-jobs-design.md) §3, and its shape is
defined here as the proposal's consumer.

So this is not new machinery. It is the same machinery with three more feeds,
and the existing probe becomes the first feed rather than the odd one out.

**Propose only.** Operator's decision, 2026-09-23: a probe commits in a
throwaway clone, runs the checks there, records a row, and stops. No probe
lands anything. That is what the ComfyUI probe already does.

## 2. The shape

A **feed** answers exactly two questions: *what is pinned* and *what is
upstream*. Everything after that is shared: rewrite in a clone, check, record,
brief on red. A feed that cannot answer both is not ready to be written.

Two things every proposal carries beyond pass/fail, because a green check is
not the same as a safe update:

- **The closure diff** against the live system, so the reviewer sees what
  actually moves. Measured today: a claude-code bump showed
  `claude-code 2.1.258 → 2.1.280` plus `bubblewrap`, `openssl` and `pcre2`
  arriving — a new sandbox runtime in the closure, which no version number
  announced.
- **The restart set** — the units a switch would restart, from
  `switch-to-configuration dry-activate`. A green tree says nothing about
  whether activating it is free. Today's claude-code change restarted nothing;
  the generation it shipped in would have restarted `seat@` and killed a live
  seat, because unrelated work rode along.

A proposal whose restart set is empty, or contains nothing with work in
flight, is safe to apply at any moment. Everything else waits for a quiet
lane. That distinction is the spec's main contribution over "the checks
passed".

## 3. Feed: nixpackages and program updates

**What is pinned.** Six flake inputs, each rev-pinned *in `flake.nix` itself*:
`nixpkgs`, `nixpkgs-host`, `llm-agents`, `claude-desktop`, `gaming`,
`tvix-aios`. Plus hand-maintained pins outside the lock: `pkgs/dsh`
(`@deepseek-ai/dsh` with a 580-entry `package-lock.json` and an `npmDepsHash`),
`pkgs/proton-drive-cli` (a `fetchFromGitHub` rev plus a fixed-output hash for
its node_modules), and the root `Cargo.lock`.

**The trap, measured twice today.** Because every input names its commit in the
URL, `nix flake update <input>` is a **no-op by construction** — the lock cannot
move an input whose URL pins the rev. The update is a rev edit in `flake.nix`;
the lock follows on the next build. `docs/runbooks/upstream-bump.md` documents
the `--update-input` verb, which cannot bump a pinned input, and that is wrong
for this tree. The feed must edit the rev, not call update.

**What is upstream** is `nix flake metadata <url>` for each input's unpinned
URL, compared on rev and `lastModified`.

## 4. Feed: the model roster

**What is pinned.** `docs/ledger/routing.toml`. Seven other model ids appear
in the tree, and measured site by site none is a routing decision — UI defaults
for the operator's own picker, option defaults for hand-triggered launches, a
doc-string example, a data-policy allowlist and model-capability metadata (see
[model cards](2026-09-23-model-cards-design.md) §1). The feed reads the router
only; the others are out of scope by kind.

**What is upstream** is the provider's model list. This feed differs from the
others in kind: there is no "newer version of the pinned thing", so it proposes
a **candidate**, not a patch, and its output is a question rather than a diff.
It feeds [model cards](2026-09-23-model-cards-design.md), which is where
adoption is decided.

**It must carry tier, not just price and context.** On 2026-09-23 a model was
selected for a judge panel on the two fields the pricing endpoint exposes —
cheapest on the board, 1.05M context — and its vendor's own description called
it a classification tier, two steps below its stack's reasoning models. Price
and context ranked it first; positioning disqualified it. A feed built on the
pricing table alone reproduces that error on every pick, so the description
string is part of the payload.

Two refusals belong here rather than in a report: a routing row naming a model
the roster no longer carries, and one violating its route's declared floor.

## 5. Feed: CivitAI (`civitai.com` / `civitai.red`)

This feed is the least ready and the spec says so rather than pretending
otherwise.

**What is pinned is not in the repository.** The flake-declared catalog
(`media/models/manifest.toml`, 12 rows, `publish`-classified) is a starter set
for the single-service module. The roster the worlds actually load is
`~/comfyui/worlds/<w>/lab/manifest.toml` — outside git, outside the store,
hand-edited. Behind it, `~/comfyui/store` holds **170 GB across 71
hash-addressed cells**, with the nsfw world alone symlinking 59 LoRAs and 9
base checkpoints.

**What is upstream is unmeasured.** No CivitAI response body exists in this
tree; GN49's own plan states it opens no network and tests against a
hand-written fixture, assuming response keys `id` and `trainedWords`. The
per-world allowlist is decided (`docs/decisions/2026-09-21-civitai-allowlist-per-world.md`
— `civitai.com` for sfw, `civitai.red` for nsfw, neither a wildcard) but not
wired: `models.civitai.enable` still defaults false. **The API shape must be
measured before this feed can be planned**, and that measurement is its own
task.

**Three consequences the other feeds do not have:**

1. **Discovery is out of scope for the cards spec.** The LoRA cards design
   (§10) explicitly excludes acquiring new assets; it labels what is already
   adopted. This feed extends it — reusing its card grammar and its sidecar
   trust boundary — rather than deferring to it.
2. **A proposal has a disk consequence.** Nothing reaps `~/comfyui/store`: no
   quota, no GC, no eviction when a manifest row is disabled. One `flux1-dev`
   row is 23.8 GB. 2.4 TB is free today, and nothing enforces a ceiling.
3. **Names are a classification question, and the current safety is
   incidental.** No rule names model assets; the nsfw roster is simply not in
   the tree the publish gate scans. A probe writing an nsfw asset's filename
   into a tracked evidence row or a Helm tile would move that name into
   `publish`-classified territory for the first time. That must be decided
   deliberately, not discovered.

**Adoption does not equal use.** `GN53` is queued and unimplemented, and the
measured consequence is that the checkpoint never rotates — one checkpoint on
300 of the last 300 nsfw renders. A feed that proposes new checkpoints into a
world that cannot draw them is proposing shelf-ware; this feed's value depends
on GN53 landing.

## 6. Acceptance

- A feed's two answers — pinned, upstream — are separately testable, with a
  fixture standing in for the network.
- A proposal carries the closure diff and the restart set; one with a
  non-empty restart set naming a unit with work in flight is marked as
  waiting, not applied.
- No probe writes to the live tree. Asserted by running one against a dirty
  repository and showing the tree byte-identical afterwards.
- A probe that cannot reach its upstream records a row saying so and exits
  clean — silence and success must be distinguishable.
- The ComfyUI probe's behaviour is unchanged by becoming a feed: the same
  proposals, byte for byte, on the same fixtures.

## 7. Not in this design

Landing anything (propose-only). The CivitAI API measurement, which precedes
its feed. Ingesting `class` (EV22) and `GN53` — prerequisites with their own
tasks. Reaping `~/comfyui/store`, which
is a sibling of [workspace reaping](2026-09-23-workspace-reaping-design.md) and
shares none of its safety conditions.
