# The mutator varies the LoRA stack

Design, 2026-09-20. Subsystem: the ComfyUI generation worlds
(`media/pkgs/comfy-worlds/mutate.py`, `queue.py`, each world's
`lab/manifest.toml`). Successor to the GN series, which built the authoring
loop but left one axis of the search space frozen.

## 1. Why

Measured on the live nsfw world, 2026-09-19:

```
1280 renders, 1 distinct LoRA set:
  1280x  BBC_Deepthroat_Krea_2_epoch_17@0.8,
         bdsm_machine-behind_head-steps_4800-epochs_800@0.6
```

Fifty-five LoRAs are installed and enabled in that world's manifest. Two have
ever been used. The other fifty-three are inert weight on disk.

The cause is structural, not a misconfiguration. `mutate._substitute` writes
exactly three things into a copied graph — `sampler_name` and `seed` on every
`KSampler`, and the prompt `text` on the `CLIPTextEncode` whose text matches.
Every other node, the `LoraLoaderModelOnly` chain included, is deep-copied
verbatim. And `_scaffold` builds each job from the newest liked render's graph
(else the newest render's), so whatever LoRA set seeded the chain propagates
forever. There is no mechanism to vary it.

Worse, the surviving pair is arbitrary. The world's seed workflows
(`lab/workflows/redcraftHybridH3A2A_30Krea2_lora0..5.api.json`) are cumulative
prefixes of the alphabetically-sorted LoRA list, and the live chain descends
from `lora2` because that file was picked by hand when the scaffold was
re-seeded after a directory wipe. Nothing chose those two LoRAs for what they
do.

The operator's standing goal is an unattended search — thousands of rounds, a
local vision judge, morning picks, entries into CivitAI competitions. A search
that cannot reach 96% of its own space is not a search.

## 2. Decisions taken before design

Four questions were put to the operator on 2026-09-20. Their answers are
load-bearing and the plan does not reopen them.

| # | Question | Answer |
|---|----------|--------|
| 1 | How is a render's LoRA set chosen? | Weighted by the operator's verdicts — uniform at first, then biased by likes and dislikes. |
| 2 | How many LoRAs, at what strengths? | Vary both, within bounds the manifest carries. |
| 3 | How are conflicting LoRAs handled? | Manifest tags: a category and an optional incompatible-with list; the mutator respects them. |
| 4 | What happens on rollout? | Every enabled LoRA joins the pool at once; existing renders keep the graphs they were made with. |

## 3. A naming collision, resolved first

`[mutate].lora` **already exists and means something else.** `load_rules`
normalizes it, and `_apply_lora` uses it to rewrite inline
`<lora:NAME:strength>` tags *inside the prompt text* — the A1111 convention —
raising `RuleNeverFires` when no such tag occurs. It is unused in practice
(ComfyUI API graphs carry LoRAs as loader nodes, not as prompt tags) and is
empty in both live manifests, but the key is taken and its failure mode is
wired into the grammar.

This spec does **not** repurpose it. The new mechanic is `[mutate].loraStack`,
a distinct table. `[mutate].lora` keeps its meaning, its tests and its
`RuleNeverFires` arm untouched; a plan that silently merged the two would
change an existing rule's semantics while adding a feature.

## 3b. `stripLoras` already landed, and this spec must say how it relates

**Added 2026-09-20 after the first planning round, which this omission wrecked.**
`[mutate].stripLoras` and `_strip_loras` landed at `b054e54`, thirty-one
minutes after the commit this spec was measured at — on the operator's ask for
no act LoRAs, and directly on the `_substitute` seam and the loader-chain
rewiring §7 describes. The planner drafted against the older tree, never saw
it, and produced a plan whose citations and central judgement call were both
invalid. The panel scored criterion 2 at zero. The fault is the spec's for not
recording it, not the planner's.

What exists at HEAD:

- `_substitute(graph, positive_text, variant, strip_loras=False)` — a fourth
  parameter, already.
- `_strip_loras(workflow)` — deletes every node whose `class_type` starts
  `LoraLoader` (so a full `LoraLoader`, not only `LoraLoaderModelOnly`) and
  walks each reference back through the chain to its first non-loader output,
  resolving a full loader's CLIP slot through `clip`. Six tests cover it.
- `load_rules` returns **five** keys, `stripLoras` among them.

The three rules that follow, so no plan has to guess them:

1. **`loraStack` supersedes `stripLoras`; `_strip_loras` is reused, not
   replaced.** Its chain walk is exactly §7's source-and-consumer problem
   already solved and tested. §7's pass *deletes the chain with
   `_strip_loras`, then inserts the drawn one* — it does not rebuild the walk.
2. **Enabling both in one world is refused at load**, by name, the way a
   missing `[mutate]` table already is. `stripLoras = true` with
   `loraStack.enable = true` is a contradiction (strip everything / draw a
   stack), and resolving it by implementation order is how silent behaviour
   gets born. `loraStack` with `count = [0, 0]` is the supported way to say
   "no LoRAs", which is what `stripLoras` means today.
3. **The signature is settled here:** `_substitute(graph, positive_text,
   variant, strip_loras=False, lora_stack=None)`. Five parameters, the fourth
   keeping its name — four existing tests call it by keyword
   (`grep -c 'strip_loras=True' media/tests/comfy-worlds/test_mutate.py` → `4`)
   and renaming it would break them with a bare `TypeError`. Those tests, and
   the two `load_rules` ones beside them, are the negative control for the
   whole task.

`stripLoras` is not deprecated by this spec. It stays as the interim control
until a world's manifest carries real `loraStack` bounds, and the runbook says
which to use.

## 4. Goals and non-goals

Goals. Every enabled LoRA in a world's manifest is reachable by the mutator.
The count and the strengths vary within configured bounds. Sets that the
operator liked become more likely and sets they disliked less so. Incoherent
stacks are prevented by declaration rather than discovered by rendering.

Non-goals. No change to `[mutate].lora`, `swaps`, `samplers` or `seed`. No
re-rendering or rewriting of existing renders. No automatic LoRA downloading —
the pool is exactly what the manifest already declares. No vision judge: the
verdict signal here is the operator's own like and dislike, and the judge is a
later program.

## 5. The pool and its manifest shape

The pool is every `[[model]]` entry whose `dest` begins `loras/` and whose
`enabled` is true. No second list of LoRA names is introduced — a name that
had to be repeated in two places would drift.

Two optional keys join each such entry:

```toml
[[model]]
name = "k_doggyhairpull"
dest = "loras/k_doggyhairpull.safetensors"
enabled = true
category = "position"          # new, optional
incompatible = [ "k_piledriver" ]   # new, optional
```

`category` is a free string. `incompatible` is a list of other `name` values.
Both default to absent, and an entry with neither is a LoRA the mutator may
combine with anything — so the file works unchanged before the operator has
tagged a single row, and tagging is incremental.

The `[mutate].loraStack` table carries the bounds:

```toml
[mutate.loraStack]
enable = true
count = [ 1, 3 ]         # inclusive range of LoRAs per render
strength = [ 0.5, 0.9 ]  # inclusive range, sampled per LoRA
```

`enable = false` (the default when the table is absent) is today's behaviour
exactly: the scaffold's own loader chain is copied verbatim. This is what
makes the change safe to land before the operator has decided the bounds, and
what the sfw world keeps until it wants otherwise.

## 6. Variant gains a stack

`Variant` today is `(prompt, sampler, seed)` and is hashed into a `seen` set
for distinctness. It gains `loras: tuple[tuple[str, float], ...]` — ordered,
because loader order is graph order and two orderings are two different
renders. Being a tuple of tuples it stays hashable, so `VariantsExhausted`
keeps counting distinct variants correctly and a stack that differs only in
strength counts as distinct.

Strengths are rounded to three decimals before they enter the tuple, so
distinctness is not defeated by float noise and the recorded graph is
readable.

## 7. Rewiring the graph — the core mechanic

This is the part that is not a field assignment, and the plan should treat it
as the task's whole risk.

A world's graph today is a chain:

```
1  UNETLoader            → 10 LoraLoaderModelOnly (BBC_Deepthroat, 0.8)
                         → 11 LoraLoaderModelOnly (bdsm_machine, 0.6)
                         →  6 KSampler.model
```

Each loader takes `model` from the previous node and the `KSampler` takes
`model` from the last loader. Changing the *count* means rebuilding that chain
and rewiring whatever consumed its end.

`_substitute` gains a pass that, when `loraStack.enable`:

1. Finds every `LoraLoaderModelOnly` node in the copied graph and records the
   node id each one takes `model` from, and every node input that references a
   loader's output.
2. Identifies the chain's **source** (the first loader's `model` input — the
   `UNETLoader`, or whatever precedes it) and its **consumers** (every input
   referencing the last loader's output; in today's graph the `KSampler`'s
   `model`, but the spec does not assume only one).
3. Deletes the loader nodes.
4. Inserts one new `LoraLoaderModelOnly` per LoRA in `variant.loras`, chained
   from the source, with fresh node ids that do not collide with existing keys.
5. Repoints every recorded consumer at the new chain's last node — or, when
   the stack is empty, directly at the source.

A graph with **no** loader nodes is a valid target: the source is then the
node the `KSampler` takes `model` from, and the pass inserts a chain where
none existed. A graph whose loaders are not a simple chain (a branch, a
loader feeding two consumers) is refused with a named error rather than
rewired on a guess — `LoraChainUnsupported`, carrying the node ids, in the
style of `RuleNeverFires`. The mutator already prefers a named failure to a
silent skip and this follows it.

## 8. The verdict weighting

Selection is a weighted draw over the pool, not over whole sets: sets are
built by drawing LoRAs, so a LoRA that appears in liked renders becomes more
likely everywhere rather than only in the exact set it was seen in. With 55
LoRAs the set space is far too large to score set-wise from 41 likes.

Each LoRA's score is derived at draw time from the world's own
`feed.sqlite`:

- For every `likes` row, read the render's graph from `renders` and extract
  its LoRA names; each name gains one like.
- For every `dislikes` row, do the same. The `dislikes` table stores the
  prompt inline but not the graph, and the `renders` row is gone once the PNG
  is deleted — so a disliked render whose row has been dropped contributes
  nothing. That is a real limit of today's schema and the spec states it
  rather than pretending the dislike signal is complete.
- Weight is `(likes + a) / (likes + dislikes + a + b)` with small constants,
  so a LoRA with no history sits at a neutral prior and one bad render does
  not exile it. The plan fixes `a` and `b` and justifies them; they are not
  operator knobs.

Cold start — no likes and no dislikes — yields equal weights, which is the
uniform-random behaviour of answer 1's fallback. There is no separate cold
path to test.

The draw is seeded from the caller's seed through the existing
`random.Random` the mutator already threads, so a batch is reproducible from
its seed exactly as today.

## 9. Conflicts

After each draw, a candidate is rejected when it shares a `category` with an
already-drawn LoRA, or appears in any drawn LoRA's `incompatible` list, or
names one of them in its own. `incompatible` is treated as symmetric whichever
side declares it, so the operator only has to write each pair once.

Rejection re-draws within the existing `_MAX_DRAWS` budget; exhausting it
raises `VariantsExhausted` as it does today. A pool whose constraints make the
configured minimum count unreachable — every LoRA one category, `count` floor
of 2 — is that same named exhaustion, not a hang.

## 10. Testing

Every claim is testable without a GPU; graphs are fixtures.

- **Rewiring.** Chains of 0, 1 and 2 loaders rewritten to 0, 1 and 3; the
  `KSampler`'s `model` points at the new last node in each case; node ids do
  not collide; a branched loader graph raises `LoraChainUnsupported`.
- **Bounds.** Over many draws, counts stay inside `count` and every strength
  inside `strength`; a fixed seed reproduces a batch exactly.
- **Weighting.** Seeded `likes`/`dislikes`/`renders` rows make one LoRA
  strongly liked and another strongly disliked; over a large sample the first
  appears materially more often. Asserted as an ordering over a seeded run,
  never as a probability — a flaky statistical test is worse than none.
- **Conflicts.** Two LoRAs of one category never co-occur; a declared
  incompatible pair never co-occurs, asserted from both declaration
  directions; an over-constrained pool raises `VariantsExhausted`.
- **The default is today.** With `loraStack` absent, `_substitute`'s output is
  byte-identical to the current implementation's for the same inputs. This is
  the regression guard for all 1,280 existing renders' worth of behaviour and
  should be written first.
- **`[mutate].lora` untouched.** Its existing tests pass unchanged.

## 11. Files

Changed: `media/pkgs/comfy-worlds/mutate.py` (the rules loader, `Variant`, the
rewiring pass, the weighted draw); `media/tests/comfy-worlds/test_mutate.py`.
Possibly `queue.py`, only if recording the chosen stack on the job row proves
worthwhile — the graph already carries it, so the plan should justify any
column rather than assume one.

Untouched: `author.py`, `run.py`, `feed.py`, `feed_index.py`, `app.js`,
`app.css`, every nixosModule. Each world's `lab/manifest.toml` is operator
state outside the repo; the spec defines its shape and the runbook documents
it, but no task edits the live file.

## 12. Open operator question

**Should the sfw world get `loraStack` too, or does this land nsfw-only?**
The mechanism is per-world by construction — it reads each world's own
manifest. *Default applied absent an answer:* the code lands for both worlds
and only nsfw's manifest enables it, since sfw has no renders and no likes to
weight with.
