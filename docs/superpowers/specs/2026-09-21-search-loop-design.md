# The search loop — a night that never halts, a judge trained on the operator's votes, a blind morning of twenty (2026-09-21)

Design, 2026-09-21. Subsystem: Generation (GN, gate sonnet). Size M. The generation lab's first sub-project after the worlds landed, resumed on the operator's "go on the CivitAI search-loop brainstorm". The brainstorm of 2026-09-06 (`docs/decisions/2026-09-06-generation-lab-brainstorm.md`) fixed six answers this spec carries as constraints: competition-agnostic; three grading signals with the operator's picks as the truth that overrides them; search over the LoRAs on disk, with bins; SFW for competition work and the NSFW world local-only end to end; a lab table of parameters, scores and hashes in the store with prompt text only on the machine; models by hand, plus a LoRA value analysis and a disk budget. The four answers of 2026-09-21: the number is one entry, not judge agreement (the operator overrode the recommendation); with no competition open, the loop builds to the Community Challenge shape with judge agreement as the interim measurement; approach A, an embedding judge first and a vision-language judge later; the design sections as written here.

Grounded in `media/pkgs/comfy-worlds/{run,author,mutate,feed_index}.py`, `media/nixosModules/local-model.nix`, the two worlds' feed databases, the supervisor's journal, and a read of civitai.com on 2026-09-21.

## 1 The numbers

**Final.** One image entered in one CivitAI Community Challenge, uploaded by the operator through the web. Measured on 2026-09-21: the Community Challenges grid at `civitai.com/challenges` shows no active, upcoming or completed challenge; the only live event is the MiniMax H3 video and LoRA contest, which does not fit a local Krea 2 image pipeline; the retired daily challenge is a 404. The last observed cycle (`civitai.com/articles/33047`, "Life's a beach", ~2 weeks from 2026-07-25) set the shape this spec builds to: any model or checkpoint, SFW, up to 20 entries per participant at 50 Buzz each, entry by posting to the challenge's collection. Posting is web-only: the public API (`developer.civitai.com/site/reference/images`) is GET-only, so the upload is the operator's act by design as well as by rule.

**Interim, every morning.** The judge's top 20 renders per world are shown in the feed unlabeled; the operator votes as usual; their like rate must be at least twice the feed's baseline. Baseline on 2026-09-21: 718 likes over 2784 verdicts in the NSFW world, 19 %. The number is printed with its count and is "not measurable tonight" whenever fewer than 20 scored renders exist.

**Precondition.** One night unattended, at least 1000 renders, no halt. On 2026-09-20 the loop rendered 3776 in a day; on 2026-09-21 it halted after 10 because the author model replied with a 407-character prompt and then a non-JSON reply, two empty batches, exit 3 (`journalctl --user -u comfy-run-nsfw`, `run.py`'s halt rule).

## 2 What exists

| capability | today | file |
|---|---|---|
| supervisor | authors when the queue is at or below `--low-water 2`, trades the GPU with the author model through `Conflicts=`, mutates, renders, sleeps `--tick 120`; two empty batches → exit 3 | `media/pkgs/comfy-worlds/run.py`, `media/nixosModules/local-model.nix:6,30,117` |
| author | reads the newest K liked and disliked prompt texts (`--window 20`), asks the loopback model for M base prompts; no theme input | `author.py:3-9,103,178` |
| mutator | variants per liked render, `--seed-file` expansion, the weighted conflict-free LoRA draw (GN38–GN42, on main at `53ca85e`) | `mutate.py:951-975` |
| feed | renders, likes, dislikes, seen tables; multi-world UI on 8288; likes reach `ledger/engagement` (471 on 2026-09-21) | `feed_index.py:25-44`, `feed.py` |
| judge | none; no vision or embedding model on disk; `~/models` holds three text GGUFs | measured `ls ~/models`, `~/comfyui` |
| SFW world | text encoder and VAE only, no checkpoint, no LoRAs, 0 renders | `~/comfyui/worlds/sfw/models` |
| NSFW world | one checkpoint (a symlink into the shared `~/comfyui/store`, 35 GB), 55 LoRAs, 3786 renders, 5.4 GB | measured |
| lab table | none | — |
| model acquisition | huggingface.co allowed (decision 2026-09-15), civitai.com closed (`media/nixosModules/comfyui.nix:187-190`) | — |

## 3 Design

### 3.1 The theme

One text per world, `theme.txt` beside the world's database, set from the feed page (a field next to the world's name) or by hand. `comfy-author` gains `--theme <file>`: the theme is the batch's subject and the windows remain its taste. `comfy-judge` reads the same file for adherence. Empty theme: the author runs on windows alone, as today, and adherence is null.

### 3.2 The judge

`comfy-judge`, a new script in the worlds package. Weights: a SigLIP-class image-and-text embedding model, about one gigabyte, fetched from huggingface.co and pinned by hash in the media flake like every other model. Per render, once: the image embedding, stored in a new `embeddings` table keyed by render name. Nightly and on demand: a classifier head (logistic regression on the embedding) trained on every like (1) and dislike (0) across all worlds, since taste is the operator's and not the world's; the head's held-out accuracy is stored beside it. Per render: `taste` (the head's probability), `adherence` (cosine similarity between the theme's text embedding and the image embedding, null without a theme), `rank` (taste, then adherence). It runs as a user unit after each render batch, on the card beside the generator; if the card refuses, on the CPU, slower but scoring. A vision-language judge (Qwen3-VL class, 4-bit, served like the author model) is the third signal of the 2026-09-06 answer and is out of scope until the probe's agreement is measured.

### 3.3 The night

`run.py` changes in three places. Author replies are repaired before they are judged unusable: a prompt over 400 characters is cut at the last sentence boundary under 400; a reply that is not a JSON array gets one repair pass (extract the outermost array). After two empty batches the loop mutates the top-liked window (`comfy-mutate --seed-file` over the newest `--window` liked renders) instead of exiting; one journal line names the fallback. The loop ends on `--until <HH:MM>` or when the world's output directory reaches `--disk-budget <GB>`; never on the author.

### 3.4 The SFW world

The shared checkpoint is linked into the SFW world's models directory the way the NSFW world's is (a symlink into the store); the text encoder and VAE already resolve. The LoRA subset is chosen by the operator by hand and recorded as a list in the world's manifest; empty list means checkpoint only. The world's evaluation check asserts a checkpoint resolves.

### 3.5 The morning

The feed gains `/w/<world>/morning`: the top 20 by rank among renders scored since the last morning, shown with no score, rank or provenance, under the theme; votes there are ordinary likes and dislikes. A `mornings` table records each showing: date, world, the 20 names, the verdicts as they arrive, and the like rate against the baseline as of that morning. The number prints on the page and in `evidence report lab`.

### 3.6 The lab table

A new store kind `lab-render`, stream `ledger/lab`, one row per render: world, render hash, image sha256, seed, steps, sampler, checkpoint hash, LoRA stack with weights, taste, adherence, rank, verdict (like, dislike, unseen), morning (date or null). No prompt text; the validator refuses a `prompt` field, the 2026-09-06 rule made mechanical. Rows are written by the judge when it scores and updated by the feed when a verdict lands.

### 3.7 The LoRA value report

`evidence report lab`: per LoRA, renders, mean taste, like rate when present versus absent, and the morning appearances; per world, the last seven mornings' agreement numbers. The disk-budget eviction of the 2026-09-06 answer reads this report and is a later task.

### 3.8 Bins

`bins/<theme>/` per world: the morning's liked renders copied in with a manifest (name, hashes, parameters). A bin is a candidate LoRA training set; training is out of scope.

## 4 Failure modes

| arm | behaviour | trace |
|---|---|---|
| author unusable twice | mutate the top-liked window, keep running | one journal line per fallback |
| judge weights missing, card full and CPU too slow | renders stored `unscored` | morning says so; number "not measurable tonight" |
| theme empty | windows only, adherence null | morning shows "no theme" |
| disk budget reached | rendering stops, scoring finishes | journal line; morning runs |
| fewer than 20 scored | show what exists | number printed with its count |
| SFW LoRA list empty | checkpoint only | manifest shows the empty list |

## 5 Where it lands

| task | files |
|---|---|
| SFW model set | the world manifest, the link into the store, `comfy-worlds-eval` assertion |
| theme | `author.py`, `feed.py` (the field), `theme.txt` convention |
| night | `run.py`: repair, fallback, `--until`, `--disk-budget`; unit test with a mocked model |
| judge | `judge.py`, the weights in the media flake, the `embeddings` table, a user unit |
| lab stream | `pkgs/evidence/streams.py`, `SCHEMA.md`, the writer in `judge.py` and `feed.py` |
| morning | `feed.py` route and page, `mornings` table, the agreement number |
| report | `pkgs/evidence/report.py` `lab` subcommand |

Every path is inside Generation's or Evidence's `owns`; the lab stream task carries an EV co-owner note. No manifest row changes.

## 6 Red before green

- Night: with a model stub that returns garbage twice, the loop reaches a mutate batch and is still running; today it exits 3.
- Judge: on a fixture of embeddings with labels, held-out accuracy beats the same fixture with shuffled labels; the shuffled arm is the negative control; today no judge exists.
- Morning: the route returns exactly the top 20 by rank, the page contains no score or rank, every shown name is recorded; today the route is 404.
- Lab stream: `streams.validate("lab-render", row)` refuses a row carrying `prompt` and a row without `image_sha256`; today the kind is undeclared.
- SFW world: `comfy-worlds-eval` asserts a checkpoint resolves in the SFW models directory; today it does not.
- Acceptance: one night on core, at least 1000 renders, the next morning's like rate on the twenty, written as a `checks` row with `class = "operator"` (`pkgs/evidence/SCHEMA.md:27`, a class with zero rows today) carrying the rate and the count.

## 7 Sequencing

Wave 1: SFW model set ‖ theme ‖ night ‖ lab stream. Wave 2: judge. Wave 3: morning, then the report. The acceptance night follows wave 3 and a switch of core.

## 8 Risks, named

- **Taste is trained on one world's votes.** All 2784 verdicts are NSFW-world renders; the head may not transfer to SFW subjects. The morning view measures this per world from the first SFW night, and the number is per world.
- **The card during generation is unmeasured.** Krea 2's footprint beside a one-gigabyte encoder is assumed to fit on 32 GB; the CPU arm is the fallback, and the judge task measures it first.
- **The competition may not open.** The interim number stands on its own; the final number waits for a cycle, and a challenge created by the operator is the fallback the record names, with whether a host may enter unmeasured.
- **Lab rows at 3776 a day.** Small rows, append-only; the report reads by day. If the store's readers slow, the rows move to per-night files, a later decision.

## 9 Open operator questions

1. The SFW LoRA subset, by hand, from the 55 on disk. Default: empty, checkpoint only, until you choose.
2. The first theme. Default: the last observed cycle's, "life's a beach", as a stand-in until a real cycle opens.
3. `--until` and `--disk-budget` defaults. Default: 07:00 and 20 GB per world.

## 10 Out of scope

The vision-language judge. Model eviction. LoRA training from bins. Any automated contact with civitai.com. Polling the challenges page, which is the operator's or a later allowlist decision.
