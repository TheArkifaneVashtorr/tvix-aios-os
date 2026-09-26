# LoRA cards and the coupled draw — a LoRA that fires only when the prompt asks for it (2026-09-21)

**Status:** approved by the operator 2026-09-21 in session 32, from the
complaint "terrible variety" and the diagnosis that followed it.
**Subsystem:** Generation (GN), gate `sonnet`, `owns = [ "media/*" ]`
(`docs/ledger/subsystems.toml:248`). One broker line lands in Isolation.
**Size:** M.

## 1 The numbers

Measured on the live NSFW world, 2026-09-21, read-only.

- **A contradiction the design said must be refused is instead resolved
  silently.** The world's `lab/manifest.toml` sets `[mutate] stripLoras =
  true` and, four lines later, `[mutate.loraStack] enable = true`, `count =
  [ 1, 3 ]`, `strength = [ 0.5, 0.9 ]`. `stripLoras` is not a stray default:
  it landed at `b054e54` on the operator's own ask for no act LoRAs, and
  `2026-09-20-lora-mutation-design.md` §3b records it. That same §3b, rule 2,
  required this exact pair to be **refused at load, by name**, "and resolving
  it by implementation order is how silent behaviour gets born." The refusal
  never landed. Implementation order resolved it instead, and `mutate.py`
  now documents the outcome as supported — the docstring at the `_substitute`
  seam reads "`stripLoras`, the interim control, is applied by the loops
  AFTER this returns … so it dominates the drawn stack", and the comments at
  the two call sites read "a world that sets both keeps". The predicted
  silent behaviour is the behaviour. No render carries the stack the draw
  produced: the newest 10 NSFW renders carry no LoRA loader at all, and the
  290 before them carry the same inherited pair.
- **`stripLoras` never did the job it was set for.** The operator's word,
  2026-09-21: "striploras was a temp fix and it never worked." The
  measurement agrees — the flag was true in the manifest while 290 of the
  last 300 renders still carried the inherited pair, and only the 10 rendered
  after the 2026-09-21 switch to generation 79 carry no loader at all. Which
  of the two explains it — a running binary older than `_strip_loras`, or a
  strip the graph re-inherits downstream — is **not established here**, and
  the plan must establish it before reusing `_strip_loras` for anything
  (§3b rule 1 assumes its chain walk is sound). Either way this spec treats
  `stripLoras` as a stopgap that failed, not as a design element to preserve.
- **Every LoRA that does render is inherited, not chosen.** `_scaffold`
  takes "the newest LIKED render's graph" and `_substitute` rewrites only
  positive text, `sampler_name` and `seed`. Whatever LoRAs that old graph
  carried are copied forward onto every later prompt. This is the operator's
  symptom exactly: "I can tell the deepthroat lora is on when that isn't
  what is being described, causing the head to be in the wrong position,
  tons of images with no sexual act of any kind occurring."
- **Everything else is constant for the same reason.** Across the newest 300
  renders: checkpoint `redcraftHybridH3A2A_30Krea2` 300/300, steps 8, cfg
  1.0, 1024×1024. `_substitute` never writes any of them.
- **There are no cards.** The manifest's 58 `[[model]]` rows carry `name`,
  `sha256`, `dest`, `size`, `source`, `enabled` — integrity only.
  `grep -c category` over the manifest returns **0**, although
  `_lora_stack` already validates `category` and `incompatible` per row.
- **A third of the trigger words are recoverable offline.** Of the 55
  `*.safetensors` under `models/loras`: 20 carry `modelspec.title`, and for
  the `K_`/`k_` family that title *is* the trigger token — `p0v,` `gr4b,`
  `bd5m,` `n3lson,` `b0lld0g,` `f1lledmouth,` `4fter0ral,`. 6 carry a
  non-empty `ss_tag_frequency`; 31 were trained on blank captions; 18 carry
  none; 4 have no `__metadata__` block at all; 2 carry a description.
- **The brief is a ceiling.** `[author].brief` hard-codes the LLM's entire
  subject space as a five-item list: `the sexual act [Deepthroat, Anal with
  legs above head, handjob, titfuck, Anal with woman bent over looking back
  over shoulder]`.
- **Dedup is three batches.** `author.py` defaults `--history 3` and
  `run.py:_author_argv` never overrides it, against 226 batches / 1805
  distinct prompts on disk.

## 2 What exists

GN38–GN42 (`2026-09-20-lora-mutation.md`) all landed: the manifest grammar,
the weighted draw, the graph rewiring, verdict weighting, the runbook. The
judge panel flagged the `stripLoras` defect at rows 4, 25 and 35 of
`docs/reviews/plan-judgements/2026-09-20-lora-mutation.md` and no task
resolved it. So the machinery below is mostly *already here and unused*:

- `_lora_stack` derives the pool by rule — every `[[model]]` row whose `dest`
  begins `loras/` and whose `enabled` is true — and validates a per-row
  `category` (string) and `incompatible` (list of names).
- `_draw_stack` already refuses a member that shares a category with one
  already drawn, or is incompatible with one in either direction, and
  already supports per-name `weights`.

Three rules are already settled by `2026-09-20-lora-mutation-design.md` §3b
and this spec inherits them rather than re-deciding:

1. `loraStack` supersedes `stripLoras`; `_strip_loras` is reused, not
   replaced — its chain walk already solves the source-and-consumer problem.
2. Enabling both in one world is refused at load, by name. `loraStack` with
   `count = [ 0, 0 ]` is the supported way to say "no LoRAs", which is what
   `stripLoras` means today. **This rule is the one that did not land**, and
   §3.4 lands it.
3. The signature is settled: `_substitute(graph, positive_text, variant,
   strip_loras=False, lora_stack=None)` — the fourth parameter keeps its name
   because four existing tests call it by keyword.

Nothing in the tree connects a LoRA to the words of the prompt it renders.

## 3 Design

### 3.1 The card

A card is three typed fields added to an existing `[[model]]` row:

- `category` — one of `position`, `act`, `body`, `style`, `detail`. Already
  validated; today always absent. Populating it alone buys the same-category
  exclusion `_draw_stack` already enforces, which is what stops two position
  LoRAs fighting inside one image.
- `trigger` — the token the LoRA was trained to answer to, verbatim
  including punctuation (`n3lson,`). Optional: a LoRA with no trigger is not
  broken, only unanchored.
- `requires` — the words that must appear in the prompt for this LoRA to be
  legal in a stack. **Only `position` and `act` cards carry `requires`.** A
  `detail` card like `Face_Details` needs no position in the description;
  forcing one on it would be the same error in the other direction.

A row with no card is not in the pool. `unmatched = true` marks a row the
card tool could not resolve, so the honest state is visible rather than
silently empty.

### 3.2 The card tool

`comfy-cards`, one shot, never at generation time. It reads the world
manifest, and for each `[[model]]` row looks the model up **by the `sha256`
the row already carries** — exact, and immune to the filename lying about
what a LoRA does. It writes back only typed scalars: `category`, `trigger`,
`requires`, the upstream version id, or `unmatched = true`.

The trust boundary is the point of the tool. Free text written by strangers
— descriptions, example prompts, comments — is saved to a sidecar
`lab/cards/<name>.json` for the operator to read and **never enters the
manifest, the author's context or a prompt**. Every scalar that does cross
is length-capped and character-checked at the boundary. Uploaders get to
name a trigger token; they do not get to write a sentence the prompt model
sees.

Network egress goes through the media broker with a literal host allowlist,
the shape `2026-09-15-media-allowlist-huggingface.md` set for the fetch unit
(`[ "huggingface.co" "us.aws.cdn.hf.co" ]`). The host list is §9's open
operator question, not this spec's to assume.

Offline, before any network: the header pass already measured in §1 fills
`trigger` for the 20 rows carrying `modelspec.title` and seeds `requires`
from the 6 non-empty vocabularies. The card tool starts from that, so a
refused allowlist still leaves a third of the pool carded.

### 3.3 The coupled draw

Today `comfy-run` calls `comfy-author`, then `comfy-mutate`, and each draws
blind. The coupling inverts the order: **the draw happens first and the
author is told.**

For each prompt slot in a batch the supervisor draws a target stack from the
carded pool under the existing count, strength, category and incompatible
rules. It passes that stack's `requires` words to `comfy-author`, which
writes a prompt that describes that act in those words. `comfy-mutate` then
**binds that same stack** to that prompt instead of drawing its own.

Two consequences, both wanted. A position LoRA can no longer fire on a
prompt that does not describe its position, because the prompt was written
to it. And rotation across all 55 comes free, because the draw is now per
prompt slot rather than per graph — the pool is sampled every batch instead
of being inherited once.

`trigger` is prepended to the bound prompt at enqueue, not written by the
author: a trigger token is graph plumbing, not English, and the author
should not be asked to reproduce `f1lledmouth,` correctly.

### 3.4 The graph is written, never inherited

Two changes, and the first is the one §3b rule 2 already specified.

**Land the refusal.** `load_rules` refuses a manifest that enables both
`stripLoras` and `loraStack`, by name, at load — never at draw. A world says
"no LoRAs" with `count = [ 0, 0 ]`, which is the supported spelling; the
failed stopgap stops being a second way to say it. This is the rule the
lora-mutation plan was supposed to land and did not, and it is why today's
world runs a contradiction quietly.

**Write the models.** `_substitute` writes the LoRA loaders from the bound
stack, keeping the settled signature (§2 rule 3). The scaffold stays the
source of the graph's *shape*; it stops being the source of its *models*.
Whether `_strip_loras`' chain walk can be reused for the delete-then-insert
pass (§3b rule 1 assumes it can) depends on the §1 question about why the
inherited pair survived a true flag — the first task here answers that with
a test before anything is built on it.

Until this lands nothing else in this spec is visible, so it sequences first.

### 3.5 Base models

The same card treatment for `[[model]]` rows under `diffusion_models/`, and
`_substitute` writes the checkpoint node from a pool draw. The pool is
correct at N=1 and becomes real the moment a second checkpoint is adopted.
Acquiring models stays the operator's act; this spec ships the mechanism.

### 3.6 The brief

With the act carried by the drawn card, `[author].brief`'s five-item list is
both redundant and the ceiling §1 measured. It comes out; the brief returns
to describing the world. `--history` is raised and passed by the supervisor
in the same task — three batches of memory against 226 on disk is not a
dedup.

## 4 Failure modes

- **No carded member fits.** `_draw_stack` already returns `None` and the
  candidate is respun under the shared `_MAX_DRAWS` budget. With an empty
  carded pool the world must render *without* LoRAs rather than fall back to
  the inherited stack — the fallback is the bug.
- **The author ignores `requires`.** The bound stack is dropped for that
  prompt and the render proceeds unanchored; the miss is counted. Silent
  mis-binding is worse than a plain image.
- **A card is wrong.** A `position` card whose `requires` words do not match
  what the LoRA does produces exactly today's symptom against a prompt that
  claims otherwise. The sidecar keeps the upstream text so the operator can
  adjudicate, and `unmatched` rows never enter the pool.
- **The allowlist is refused.** The offline header pass still cards ~20 rows;
  the rest stay `unmatched` and out of the pool. The world renders with a
  smaller, correct pool rather than a large, wrong one.

## 5 Where it lands

`media/pkgs/comfy-worlds/mutate.py` (the write path, the binding),
`author.py` (the `requires` constraint), `run.py` (the draw moves here, and
`--history`), a new `cards.py`, `media/pkgs/comfy-worlds/default.nix` (the
`comfy-cards` application), `media/nixosModules/comfyui-worlds.nix` (the
card unit), the media broker's allowlist, and `media/tests/`. The world
manifests are operator state outside git and are edited by the operator, not
by a task.

## 6 Red before green

Every task shows its check failing first. The named checks:
`comfy-worlds-unit` for the grammar, the draw and the binding;
`comfy-worlds-eval` and `comfy-worlds-assertion-negative-*` for the module
and its refusals; `comfy-worlds-vm` for the unit; `lint` throughout. The
card tool's network arm is tested against a recorded fixture, never a live
fetch.

## 7 Sequencing

§3.4 first — it lands the refusal that was already specified and settles why
the stopgap failed, and until the graph's models are written rather than
inherited nothing else here is visible. Then §3.1 and §3.2 (the cards,
offline arm before the network arm), then §3.3 (the coupling, which needs
cards to draw from), then §3.5 and §3.6.

## 8 Risks, named

- **The golden fixtures break.** `mutate.py` pins draw order against goldens
  — "the position the second golden freezes". Moving the draw out of
  `mutate` and into the supervisor moves every downstream value in the
  stream. Regenerating goldens must be its own task with its own review, not
  a line inside another change.
- **Untrusted text one hop from the prompt model.** Mitigated by §3.2's
  typed-scalar boundary; the residual is that a `trigger` token is still
  attacker-chosen text, which is why it is length-capped and
  character-checked and never concatenated into instructions.
- **The operator's words.** ~35 rows will need adjudication even after a
  successful fetch. That cost is real and belongs in the plan as an operator
  step, not hidden in a task.

## 9 Open operator questions

1. **The broker allowlist.** Which literal hosts may the card unit reach?
   This is the decision already sitting on the operator's list as "decide
   the civitai.red broker allowlist". Default if unanswered: the card tool
   ships with its offline arm only and the network arm stays behind the
   flag.
2. **What happens to an `unmatched` row.** Recommendation: out of the pool
   until carded. Default if unanswered: out of the pool.

## 10 Out of scope

The feed UI (measured the same session: no viewport meta tag, GN28's rail
labels, `object-fit: contain` letterboxing, zero media queries) — its own
spec. The search loop's judge and theme (`2026-09-21-search-loop-design.md`)
— it consumes this spec's cards but does not depend on them landing first.
Acquiring new checkpoints or LoRAs. Steps, cfg and resolution as mutation
axes.
