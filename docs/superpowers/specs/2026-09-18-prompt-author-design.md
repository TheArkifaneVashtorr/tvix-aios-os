# The prompt author — design (spec for review)

**Date:** 2026-09-18. **Authority:** the operator's brainstorm answers of
2026-09-18 (this session): the model is the prompt author and the operator is
the visual judge; the loop is closed (likes steer prompts); the author is a new
stage upstream of the existing grammar, which is kept; the author and the
renderer take turns on the GPU (batch and sleep); an authoring batch is
triggered when the job queue runs dry; the steering signal is likes plus a new
dislike verb; the flake owns the model unit with the weights left out of the
nix store; the model server is its own module inside `media/`.
**Context:** the generation plan `docs/superpowers/plans/2026-09-11-generation.md`
(decision 17c at `:425`, its acceptance probe at `:534`); the board's search-loop
note in `docs/board/log-2026-09.md`; the worlds design
`media/docs/superpowers/specs/2026-09-05-comfy-worlds-design.md`.
**Subsystem:** Generation (`GN`), area `generation`, gate `sonnet`
(`docs/ledger/subsystems.toml:235-247`).

**Approved by the operator: 2026-09-18 (design approved in brainstorm; spec
review pending).**

---

## §1 Header — what this spec describes

A small harness that puts a locally served, ablated language model at the head
of the ComfyUI worlds' generation loop. The model writes base prompts; the
landed deterministic grammar expands each into variants; the world renders
them; the operator likes or dislikes what he sees; the next batch is authored
from those verdicts. The model and the renderer never hold the GPU at the same
time — systemd `Conflicts=` hands the card back and forth.

Five pieces, all inside `media/`:

1. `media/nixosModules/local-model.nix` — a user unit serving one GGUF on
   loopback, with its weights declared by path and digest rather than stored.
2. `media/pkgs/comfy-worlds/author.py` (`comfy-author`) — reads the verdicts,
   asks the model, validates the reply, writes a batch file.
3. `comfy-mutate --seed-file` — a small extension so the grammar can expand
   authored prompts, not only liked renders.
4. `POST /dislike` in `media/pkgs/comfy-worlds/feed.py` — the negative verdict.
5. `media/pkgs/comfy-worlds/run.py` (`comfy-run`) — the per-world supervisor
   that owns the turn-taking and the halt condition.

Plus host wiring in `hosts/core/media-worlds.nix`, the runbook, and one owed
fix folded into this key range on the operator's word of 2026-09-18: the
missing `media-fetch-models` on core's PATH (§4 Change 7).

### §1.1 What it is not

- **Not a vision judge.** The model never sees an image. The operator is the
  only judge in this design. A local vision judge remains a future phase
  (`docs/concepts/2026-09-06a-generation-lab.md`).
- **Not a content classifier.** The SFW/NSFW split stays what the worlds design
  made it: two instances, two directory trees, two lab repos, two model
  rosters. Nothing in this spec inspects an image and routes it.
- **Not a fetcher.** The GGUF is an operator-managed file declared by path and
  digest. Three already exist under `~/models`. Acquiring weights is out of
  scope.
- **Not a change to Hermes.** `hermes-model.service` on `127.0.0.1:8765` is
  untouched and unreferenced. The worlds get their own unit on their own port.
- **Not a LAN change.** `lan.enable = false` and its build assertion
  (`flake.nix:2002-2003`) stand.
- **Not a replacement for the grammar.** Decision 17c holds: `mutate.py`
  remains model-free, and its acceptance probe
  (`docs/superpowers/plans/2026-09-11-generation.md:534`, which greps that file
  for `openrouter|anthropic|llama|ollama` and requires zero hits) stays green.

### §1.2 Invariants kept

- **Loopback only.** The model server binds `127.0.0.1`; `comfy-author` refuses
  any model URL that is not loopback, the same guard `queue.py:1-18` already
  applies to the ComfyUI base URL.
- **Weights never enter the store.** The module refuses a `modelPath` under
  `/nix/store`, the shape `modelLane.nix:133-136` already uses for `keyFile`.
- **No off-box route for the model process.** The unit is sandboxed against the
  basket, secret and broker trees, mirroring `modelLane.nix:286-293`. Today no
  module-system assertion covers a *service* that reads local-only data — the
  gap is recorded at `docs/reviews/2026-09-05-environment-review.md:418` — so
  this is closed at the unit level, deliberately and visibly.
- **The lab is the backed-up half.** Authored batches are written inside
  `worlds/<w>/lab/`, which is in `services.proton-backup.paths`
  (`flake.nix:2006-2007`); `output/` is not.
- **Refusals are loud.** Every validation failure raises with a named cause, as
  the grammar's `RuleNeverFires` does (`media/pkgs/comfy-worlds/mutate.py`).
  Nothing is silently skipped.

---

## §2 What exists today (reused, not rebuilt)

- **The worlds.** `media/nixosModules/comfyui-worlds.nix` (386 lines) renders
  per-world generator, feed and mutator user units. The two generators already
  `Conflicts` each other (`:82`) so only one holds the GPU. All units are
  `wantedBy = [ ]`, started on demand.
- **The feed.** `media/pkgs/comfy-worlds/feed.py` serves the newest renders with
  `like`, `regenerate`, `edit` and `dwell` verbs; `do_POST` dispatches on path at
  `:301-323`, 400 on garbage bodies and 413 over 65536 bytes. Its index is
  rebuilt from the PNGs' `tEXt` chunks by `feed_index.py`.
- **The queue.** `media/pkgs/comfy-worlds/queue.py` holds jobs in
  `worlds/<w>/feed.sqlite`, submits to the world's ComfyUI and polls
  `/history`. It refuses any base URL that is not `127.0.0.1:<comfyPort>`.
- **The grammar.** `media/pkgs/comfy-worlds/mutate.py` expands a prompt through
  the world's `[mutate]` table into `n` deterministic variants; a repeat run
  with the same seed is byte-identical. Its pure core is
  `mutate(prompt, rules, seed, n)` at `:150`.
- **The digest-verifying fetcher.** `media/pkgs/media-fetch/fetch.py` streams
  and verifies files against manifest digests (`_sha256_file` at `:69`,
  `fetch_one` at `:102-161`, `--reverify` at `:91-95`). Its hashing is the
  template for the new start guard.
- **The guard shape.** `comfy-world-guard` and `comfy-caddy-guard`
  (`media/pkgs/comfy-worlds/default.nix:41-67`) are the established
  `ExecStartPre` pattern.
- **The out-of-store declaration convention.** Each world's
  `lab/manifest.toml` already declares large files as `[[model]]` rows carrying
  `sha256`, `dest` and `enabled`.
- **The check patterns.** `comfy-worlds-eval` (`media/checks.nix:505`) is a
  pure-eval assert chain over a `mkHarness`; `mkNegativeWith` (`:770` onward)
  proves a refusal by requiring both a failed build and a matching message;
  `comfy-worlds-unit` (`:878`) runs bats plus `pytest tests/comfy-worlds`;
  `comfy-worlds-vm` (`:997`) is the real-systemd test.

**What does not exist today, and the spec must supply:** any continuous render
loop at all. `comfy-mutate` enqueues variants and then drives `queue.run_once`
exactly once (`mutate.py:342`); the runbook records the polling loop as
"reserved for the `comfy-feed-<w>.service` unit"
(`media/docs/runbooks/media.md:275`), but that unit runs `serve`. The loop
advances today only when something pokes it.

---

## §3 The goal

An overnight run: the operator starts a world, goes to bed, and in the morning
the feed holds renders that were authored, expanded, queued and rendered
without him — steered by the likes and dislikes he left the evening before.
The run stops on its own if the author stops producing usable prompts, rather
than spinning.

The measurable outcome: **one unattended session produces N rendered variants
across at least two authoring batches, where batch 2's prompts demonstrably
read the verdicts left on batch 1's renders, and the GPU is held by exactly one
process at every instant.**

---

## §4 The changes

### Change 1 — The local model unit (`media/nixosModules/local-model.nix`)

A new module file, imported beside `comfyui-worlds.nix`. Covered by the
Generation subsystem's existing `owns = [ "media/*" ]` glob, whose `*` spans
`/` (`docs/ledger/subsystems.toml:235-247`, and the header comment at `:1-10`)
— so no manifest row changes and `docs/subsystems.md` need not be regenerated.

Options under `services.local-model`:

| option | type | note |
|---|---|---|
| `enable` | bool | |
| `modelPath` | `str` | absolute; **not** `path`, so the GGUF cannot enter the store |
| `sha256` | `str` | 64 hex, verified at start |
| `port` | `port` | loopback; default 8790 (proposal — see §9) |
| `contextSize` | `int` | |
| `gpuLayers` | `int` | corrected 2026-09-18: this spec typed `str`; `-ngl` takes an integer and a `str` admits `"all"`, which llama-server refuses at *start*. A build-time type refusal is cheaper than a runtime one, so the plan overrode the spec here and the spec follows it. |
| `idleSleepSeconds` | `int` | |
| `conflicts` | `listOf str` | unit names that must not run concurrently |
| `operatorUser` | `str` | `ConditionUser`, as the worlds module does |

The unit, `comfy-author-model.service`, is a systemd **user** service,
`wantedBy = [ ]`, started on demand:

- `ExecStartPre = comfy-model-guard <modelPath> <sha256>` — a new guard in
  `media/pkgs/comfy-worlds/`, following the `comfy-world-guard` shape and
  reusing the hashing from `media/pkgs/media-fetch/fetch.py`. Swapped or
  truncated weights fail the start loudly.
- `ExecStart = llama-server --model <modelPath> --host 127.0.0.1 --port <port>
  --no-webui …` with the context, GPU-layer and idle-sleep options.
- `Conflicts = <conflicts>` — set to both `comfyui-sfw.service` and
  `comfyui-nsfw.service`. Starting the model stops the renderer; starting the
  renderer stops the model. **The turn-taking is systemd's, not a script's.**
- Sandbox: `ProtectSystem = "strict"`, `ProtectHome = "read-only"`,
  `ReadWritePaths` limited to what llama-server needs, and `InaccessiblePaths`
  over `/run/baskets`, `/var/lib/baskets`, `/var/lib/helm`,
  `/var/lib/egress-broker`, `/var/lib/secrets`, mirroring
  `modelLane.nix:286-293`.
- Address restriction per §6 probe 1.

Build-time assertions, each with a negative check:

1. `modelPath` is absolute and not under `/nix/store`.
2. `sha256` is exactly 64 hexadecimal characters.
3. `port` equals no world's `comfyPort` or `feedPort`
   (`hosts/core/media-worlds.nix:13-22` holds 8188/8288/8189/8289).
4. The listen address is `127.0.0.1`.

### Change 2 — `comfy-author`

`media/pkgs/comfy-worlds/author.py`, exposed as
`comfy-author --world <w> --root <r> --n <M> --model-url <url> [--dry-run]`.

**Reads**, and nothing else: the newest `K` liked prompts (the
`renders.prompt` join through `likes` that `mutate.py` already uses), the
newest `K` disliked prompts (inline text, see Change 4), and the world's
`[author]` table from `lab/manifest.toml` — the world's brief, plus optional
`required` and `banned` token lists and length bounds. **Both verdict windows
are bounded**: over thousands of rounds an unbounded history would outgrow the
context and be silently trimmed at whichever end the server chooses.

**Refuses** any `--model-url` that is not loopback, restating the guard
`queue.py:1-18` applies to ComfyUI.

**Validates** the reply — a JSON array of `M` strings — and refuses rather than
skips: exact count; non-empty; within length bounds; no duplicate inside the
batch; no duplicate against the last `N` batch files; no `banned` token; every
`required` token present. One retry with the validator's complaint appended,
then zero prompts returned. Zero is a legitimate result and feeds the halt rule
in Change 5.

**Writes** `lab/prompts/authored-<ts>.json`: the prompts, plus provenance — the
model path and digest, the request, the raw reply, and the verdict ids seen.
`--dry-run` prints and writes nothing.

**The author emits prose only.** LoRA tags, sampler choice and seed policy
remain the grammar's, where they already live and are already tested. The model
never learns the world's model roster and so can never emit a `<lora:…>` tag
that fails to resolve.

### Change 3 — `comfy-mutate --seed-file`

The grammar gains one input: a JSON file of base prompts, expanded exactly as a
liked render's prompt is. No model string enters `mutate.py`, so decision 17c's
probe stays green. Determinism is unchanged: the same seed file with the same
`--seed` yields byte-identical variants.

### Change 4 — `POST /dislike`

A new verb in `feed.py`'s `do_POST` dispatch (`:301-323`) and a button beside
`like` in the rendered article. It does two things **in this order: record,
then delete.**

The negative row stores **the positive prompt text verbatim**, not a foreign
key to `renders`. Deleting the PNG means the next index rebuild drops that
`renders` row, and an FK-only negative would dangle. Likes may stay FK-joined
as they are; dislikes may not. The ordering is pinned by a test, not by a
comment.

Semantics match `like`: 303 with a `Location` back to the anchor, idempotent on
repeat, 404 on an unknown name with nothing deleted.

### Change 5 — `comfy-run`, the supervisor

`media/pkgs/comfy-worlds/run.py`, a per-world user service that owns the loop:

```
loop:
  if queued <= lowWater:
      systemctl --user start comfy-author-model   # Conflicts stops comfyui-<w>
      comfy-author  --world <w> --n <M>           # -> lab/prompts/authored-<ts>.json
      systemctl --user stop  comfy-author-model
      systemctl --user start comfyui-<w>
      comfy-mutate --seed-file <that file> --n <N>
  queue.run_once()
  sleep <tick>
```

**Halt condition:** two consecutive batches yielding zero valid prompts stop the
supervisor with one journal line naming the cause. An unattended loop that
cannot author must stop, not spin. One empty batch is not enough — a single
malformed reply is ordinary.

The supervisor never reasons about VRAM. It starts a unit and systemd stops the
other.

**Where its settings live.** The unit `comfy-run-<w>.service` is rendered by
`comfyui-worlds.nix` beside the existing generator, feed and mutator units, and
its settings — `M` (prompts per batch), `K` (verdict window), `N` (variants per
prompt), `lowWater`, `tick` — are options on that module's per-world submodule,
beside the existing `mutate.perLike` (`media/nixosModules/comfyui-worlds.nix:199-204`).
So this change touches `comfyui-worlds.nix` as well as adding `run.py`. Only
`local-model.nix` is a new module file.

### Change 6 — Host wiring and runbook

`hosts/core/media-worlds.nix` gains the `services.local-model` block (path,
digest, port, conflicts) and the per-world author settings (`M`, `K`, `N`,
`lowWater`, `tick`). `media/docs/runbooks/media.md` gains a section covering the
unattended run: how to start it, how to read its journal, how to stop it, and
what a halt line means.

### Change 7 — `media-fetch-models` on core's PATH (the owed fix, folded in)

Recorded on the board as owed "under the next free GN number" and folded into
this plan's key range by the operator on 2026-09-18.

`environment.systemPackages` in `media/nixosModules/comfyui-worlds.nix:354-359`
installs `media-comfy`, `comfy-worlds-init`, `comfy-mutate` and — only when
`refresh.enable` — `comfy-upstream-probe`. It does **not** install
`media-fetch-models`. The fetcher reached core only through the retired
`media/nixosModules/comfyui.nix:467`, so since the worlds module took over it
has not been on core's PATH at all.

**The wrinkle the plan must solve:** the fetcher is a `writeShellApplication`
defined at `media/packages.nix:10-11` and built inline again at
`comfyui.nix:85-92`. It is not a member of `worldsPkgs`, so the worlds module
has no handle on it today. The fix must give it one — expose it through
`media/pkgs/comfy-worlds/default.nix` alongside the other tools, or pass it in
— rather than adding a third inline copy of the same builder.

This change lands beside the same list that must gain `comfy-author` and
`comfy-run`, so it is one edit to one list rather than a separate errand.

---

## §5 What stays unchanged

`mutate.py`'s grammar and determinism; the feed's existing four verbs and its
body limits; the queue's loopback guard; the two worlds' mutual `Conflicts`;
`wantedBy = [ ]` on every unit; `lan.enable = false` and its assertion; the
model store and each world's `lab/manifest.toml` `[[model]]` rows; the
engagement beacon's counts-only contract; `hermes-model.service` and port 8765;
the basket invariants and the broker.

---

## §6 Probes — measured, not assumed

These are measurable on core and are written as probes because guessing them
wrong would be expensive.

1. ~~**`IPAddressDeny=any` / `IPAddressAllow=localhost` on a systemd *user*
   unit.**~~ **MEASURED 2026-09-18 (GN14's VM probe): it does not hold, and it
   does not fail loudly.** The per-user manager cannot attach the cgroup BPF
   program, and systemd does not error — it silently ignores both directives,
   the same mechanism this repo already documents for device filters at
   `media/nixosModules/comfyui-worlds.nix:12-15`. The fallback is therefore the
   real design, not a contingency: **both directives are omitted**, and the
   model unit's no-egress property rests on llama-server's bind address alone.
   GN14 pins their *absence* with an eval assertion so they cannot be re-added
   later by someone who believes they bind — a filter that appears present and
   does nothing is worse than no filter, because it invites exactly that
   belief. Anything else on this host that is loopback-only as a *user* unit
   inherits this finding.
2. **Does `--sleep-idle-seconds` release VRAM, or only idle?** If it only
   idles, `Conflicts=` stop/start is the entire mechanism and idle-sleep is
   decoration. This determines whether the supervisor's explicit `stop` is
   required or merely tidy.
3. **Cost of one model up/down cycle against a loaded Krea2.** This number sets
   `lowWater`. Too low and the loop thrashes the card instead of rendering.

The arithmetic that forces the turn-taking:
`Qwen3.6-27B-abliterated.i1-Q6_K.gguf` is 22.1 GB of weights before its KV
cache; the Krea2 checkpoint is 12.24 GiB; the card is 32 GB. They cannot
co-reside.

---

## §7 Order of operations

1. Change 4 (`/dislike`) — independent, and the author needs the negative set.
2. Change 1 (the model unit) with its four negative checks.
3. Change 3 (`--seed-file`) — independent of 1 and 2.
4. Change 2 (`comfy-author`) — depends on 1 and 4.
5. Change 5 (`comfy-run`) — depends on 2, 3, 4.
6. Change 7 (`media-fetch-models` on the PATH) — independent of everything
   above, but sequenced here because it edits the same `systemPackages` list
   that must gain `comfy-author` and `comfy-run`.
7. Change 6 (host wiring, runbook) — last; the switch is the operator's.

Probe 1 precedes Change 1; probes 2 and 3 precede Change 5.

---

## §8 Tests and checks

Every item lands red first.

**Eval (pure Nix, no VM):**

- `local-model-eval` — an assert chain over `mkHarness (import
  ./nixosModules/local-model.nix)`: `--host 127.0.0.1`, the port, `--no-webui`,
  the `comfy-model-guard` ExecStartPre carrying path and digest, `Conflicts=`
  naming both generator units, `wantedBy == [ ]`, `ProtectSystem`,
  `ProtectHome`, `InaccessiblePaths`, `ConditionUser`, and the address rules
  probe 1 settles.
- `local-model-assertion-negative-store-path`, `-digest`, `-port-collision`,
  `-listen-address` — four `mkNegativeWith` checks, each requiring the build to
  fail *and* the message to carry the expected infix.
- `comfy-worlds-eval` gains three names in its existing `systemPackages`
  assertion — `comfy-author`, `comfy-run` and `media-fetch-models` (Change 7).
  That assertion is red before the fix and green after, which is the whole test
  the PATH gap needs.

**Unit (pytest, inside `comfy-worlds-unit`; fake model server shaped like
`FakeComfy` in `media/tests/comfy-worlds/test_queue.py`):**

- `test_author.py` — non-loopback model URL refused; a valid reply writes `M`
  prompts and a well-formed batch file; wrong count, in-batch duplicate, repeat
  of a prior batch, banned token and oversize each refused with a named cause;
  one retry then zero; with 500 likes in the database the request carries
  exactly `K`; the batch file holds the model digest and the raw reply;
  `--dry-run` writes and enqueues nothing.
- `test_feed.py` additions, following `test_like_writes_one_row_idempotent`
  (`media/tests/comfy-worlds/test_feed.py:329`) and using the `post` helper at
  `:295-308` — dislike returns 303 and writes the prompt text inline with the
  PNG gone; a second post is idempotent; an unknown name is 404 with nothing
  deleted; a percent-encoded name works (precedent at `:499`); and **with
  deletion forced to fail, the negative row still exists**, pinning
  record-before-delete.
- `test_mutate.py` — `--seed-file` expands file prompts; a repeat run is
  `cmp`-identical; decision 17c's grep probe still returns zero.
- `test_run.py` — with `systemctl` and both CLIs faked: below `lowWater`
  triggers authoring and above it does not; the sequence is model-up → author →
  model-down → comfy-up → mutate; two consecutive empty batches halt with the
  journal line; one does not.

**Bats (bare PATH, extending `comfy-worlds-unit`):** the built `comfy-author`
and `comfy-run` run under `env -i PATH=/no-such-dir` and print usage rather
than crash, the contract the other CLIs already hold.

**VM (`comfy-worlds-vm`):** starting `comfy-author-model.service` actually
stops the world's generator, and starting the generator actually stops the
model. Eval can prove the `Conflicts=` string is present; only real systemd
proves it fires. It is the most load-bearing behaviour here and earns the VM
cost.

---

## §9 Open questions for the operator

1. **Which GGUF.** Recommendation: `Qwen3.6-27B-abliterated.i1-Q6_K.gguf`,
   already on disk and already digest-verified. `Hermes-4-14B-Q6_K.gguf` is the
   smaller alternative. The path is an option, so this is reversible.
2. **Default port.** 8790 is a proposal, asserted distinct from 8188/8288/8189/
   8289 and chosen away from Hermes' 8765. Any free loopback port serves.
**Settled 2026-09-18:** the owed `media-fetch-models` PATH fix folds into this
plan's key range, as Change 7.

---

## §10 Sources

- `docs/superpowers/plans/2026-09-11-generation.md` — GN1–GN12; decision 17c
  (`:425`) and its probe (`:534`).
- `media/docs/superpowers/specs/2026-09-05-comfy-worlds-design.md` — the
  two-worlds rationale.
- `media/nixosModules/comfyui-worlds.nix` — units, `Conflicts` (`:82`),
  options (`:148-252`), assertions (`:255-287`).
- `media/pkgs/comfy-worlds/{feed.py,queue.py,mutate.py,default.nix}`.
- `media/pkgs/media-fetch/fetch.py:69,91-95,102-161` — digest verification.
- `media/checks.nix:505,770,878,997` — the four check patterns.
- `media/tests/comfy-worlds/test_feed.py:295-308,329,341,499`.
- `nixosModules/modelLane.nix:133-136,286-293` — the non-store assertion shape
  and the sandbox path list.
- `nixosModules/basketStore.nix:98-105` — invariant A2.
- `docs/reviews/2026-09-05-environment-review.md:418` — the recorded gap for
  processes reading local-only trees.
- `docs/ledger/subsystems.toml:235-247` — the Generation row.
- `hosts/core/media-worlds.nix:13-22` — the live ports.
- `flake.nix:2002-2003` (LAN off), `:2006-2007` (backup paths).
- `docs/brief.md:227-228` — local weights on core's 5090 as a stated direction.
- Host facts measured 2026-09-18: `~/models/` holds
  `Qwen3.6-27B-abliterated.i1-Q6_K.gguf` (22.1 GB),
  `DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf` (19.9 GB) and
  `Hermes-4-14B-Q6_K.gguf` (12.1 GB); `hermes-model.service` serves the first
  on `127.0.0.1:8765` and is unmanaged by this flake.
