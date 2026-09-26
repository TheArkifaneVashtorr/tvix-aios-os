# tvix-aios — the OS owns the agent runtime

Design, 2026-09-22. Subsystem: Program (this spec, the brief), with the code it
names landing in Isolation (the guard, the VM runtime), Factory (the daemon's
workflow arm), Evidence (the stream grammar in Rust) and Generation (the worlds
under `aios.worlds`). Size M. Grounded in brief §2 as rewritten 2026-09-22,
`docs/decisions/2026-09-22-freeze-and-triage.md`, the two 2026-09-21 packets
(`docs/research-2026-09-21-tvix-aios-packet.md`, `-loose-ends.md`), the
operator's answers of 2026-09-21 (`docs/decisions/2026-09-21-public-repo-answers.md`)
and the notebook concept inventory
(`docs/research-2026-09-22-aios-notebook-concepts.md`). Decisions the operator
took in the 2026-09-22 brainstorm, in order: freeze and triage the queue; fold
the notebook concepts in by hand; **tvix as a library first**; **microvm.nix on
cloud-hypervisor** for VMs; **this repository is the OS's repository of record**,
the fork an untouched mirror.

## 1 Why

The operator, 2026-09-22: the goal is tvix-aios, a Rust-based NixOS-derived
AI-native operating system with the infrastructure to run VMs and agent
workflows built in, and much of what the system had been doing was churn. The
measured shape of the churn is in the decision file: 2279 commits in a month,
about half of them the factory writing about itself, two naming tvix.

The measured cause is structural. Every subsystem on `core` is real and
running — the TLS-terminating broker (`nixosModules/egressBroker.nix`), the
seat lane with its namespace and hardening (`nixosModules/seatLane.nix:391-465`),
the baskets (`nixosModules/basketStore.nix`, `pkgs/basket/basket.sh:132-172`),
the evidence store with its schema fence (`pkgs/evidence/streams.py`), the
routing ledger (`docs/ledger/routing.toml`), the worlds
(`media/nixosModules/comfyui-worlds.nix`) — but each is wired to the host by
hand-written units and shell drivers. Nothing on `core` runs in a VM of ours;
every VM test is a `runNixOSTest`. And no declaration surface exists: there is
no NixOS option under which a workflow, a seat, a VM or a world is declared and
checked. The notebook prototype had the same hole (concepts doc, "the one
structural finding"): both of its architecture families wired every engine as
a plain systemd service.

An operating system that owns the agent runtime is exactly that missing
surface plus one process that owns lifecycle beneath it. This spec names both.

## 2 The numbers this spec serves

Brief §2's four goals. Each has one acceptance check in this flake, red before
its plan lands:

| goal | check | green when |
|---|---|---|
| 1 It builds in public | `aios-public-build` | a clean clone of the publish-gate export evaluates the flake and `cargo build` of the workspace (guard + `aiosd`) succeeds against the fork's crates as a flake input |
| 2 One workflow end to end | `aios-workflow-vm` | a `runNixOSTest` boots the image, `aiosd` starts an `aios.vms` guest, a stub seat inside it reaches only the broker over vsock, lands a branch, the gate verdict line is read, and the evidence store holds the `factory-run`, `task-result` and `gate-verdict` rows for it |
| 3 A stranger takes a task | `public-task-list` | the filtered render of `evidence tasks` (field allowlist, decision 2026-09-21 #18) is produced at build time and a planted withheld field fails it |
| 4 A world as an OS function | `aios-world-service` | an `aios.worlds` entry renders to units that boot in a `runNixOSTest`, its loop runs one round against a stub generator, and one `world-pick` row lands in the evidence store |
| 6 No AI on user data | `aios-classification-negative` | a fixture that binds a path outside its declared `aios.data` classes into a world or a seat fails evaluation with the classification assertion's message; the positive fixture with the class declared evaluates (added 2026-09-22 night, invariant 8) |

The differential check `aiosd-dispatch-differential` (the IS22 shape: same
corpus, old driver and new daemon, zero divergence in `.result` grammar and
verdict) gates goal 2's daemon before it replaces `factory-task`.

## 3 Scope

In: the `aios` option tree; the `aiosd` crate and its Unix socket; the guard
crate beside it (IS23–IS25 as released); microvm.nix as a flake input with the
cloud-hypervisor backend; the evidence stream grammar as Rust types; the four
checks above and the differential; the brief amendments §1 (the GitHub
constraint) and §7 (the phases); the subsystem rows every new path needs.

Out, as later specs: tvix as the system evaluator or store (the fork lacks
castore, store, build and nix-daemon: packet §1.1 fact 12); GPU passthrough
into a guest (unmeasured on `core`); KV paging and prefix sharing for the
worlds (concepts A11, A12, B5, B9 — the worlds' own plan); the export tool
and CI on the public repository (publish-gate phases 2–3); any change to the
fork's tree; multi-node placement (`node2`, `node3`).

## 4 The declaration surface

One module, `nixosModules/aios.nix`, declares `options.aios`. Existing modules
are re-exported beneath it, not rewritten: the option tree is the interface,
the modules stay the implementation until the daemon absorbs them.

```
aios.vms.<name>        = { config; shares = [ { source; mountPoint; } ]; vsock.cid;
                           baskets = [ ]; egress = "<aios.egress name>"; }
aios.seats.<name>      = { harness = "claude-code" | "dsh" | "codex"; role;
                           baskets = [ ]; egress; placement = { vm = "<name>" } | { unit = { }; } }
aios.workflows.<name>  = { source = { plan; keys = [ ]; }; ladder = "<routing role>";
                           gates = [ "review" ]; cap = <int>; }
aios.worlds.<name>     = { generator; loop = { rounds; judge; }; sink = "<evidence kind>";
                           placement = { unit = { }; }; }
aios.egress.<name>     = services.egress-broker.instances.<name>   (alias)
aios.policy.guard      = services.orchestrator-guard.rules         (alias, IS23)
aios.data.<class>      = services.baskets.definitions.<class>       (alias; the data classes:
                           classification, mount, access — invariants 1 and 8)
aios.models.<name>     = { server = "llama-server"; weights = { path; sha256; };
                           reads = [ "<aios.data class>" ]; vram = <MiB>; listen = "127.0.0.1:<port>"; }
```

`aios.models` (operator, 2026-09-22 night: local LLMs performing isolated,
controlled tasks in the background) declares a local model server: the weights by
digest outside the store (today's `services.local-model` shape,
`hosts/core/media-worlds.nix`), the `aios.data` classes it may read, its VRAM
budget, and a loopback listener. A local model is the only kind invariant 8 lets
read a declared user data class, so it is what a world's judge, a world's embedder
(the retrieval memory of the LoRA-routing goal area), the complexity router in
front of the chat, and pre-review run on. The VRAM budget is a hard scheduler
constraint (§5): a model and a world that together exceed the card do not start
together; on a contributor's machine the budget is theirs to declare. The first
model is a measured fit on the 5090 beside the image generator, chosen in the
goal-4 plan; the 27B author model's 22 GB are freed by the seed-data change.
DeepSeek V4 Flash is a candidate, corrected 2026-09-22 night after the operator
sent the orchestrator back to the research: 284B total, 13B active, six of 256
routed experts per token (model card), so the GPU holds the working set, not the
model; the Q4 GGUF (~163 GB) exceeds the card plus RAM, the 2-bit GGUFs (~81–100
GB) fit with routed experts offloaded to RAM (`-cmoe`); the only primary
throughput figure (20+ tok/s on one 5090, ktransformers) needs 200 GB RAM this
host lacks, so tokens/s at 2-bit on `core` is a spike to run, not a fact.
V4.1 Flash's Engram conditional memory (196B, disk-resident by design, never
preloaded) is the notebook's paging idea shipped; its 552B backbone does not fit
this class of machine by any source read.

`aios.data` is not an alias of convenience (operator, 2026-09-22 night: "baskets and
classification are OS features, not scaffolding"). A basket is how a user declares
the one subset of their data a model may read; the classification assertion
(`assertion-negative` today) is how the build refuses anything else. Every
`baskets = [ ]` list on a VM, seat or world names `aios.data` classes and nothing
else; a world's learning telemetry (goal 4's picks, dwell, ratings) is declared as a
class here or the world does not learn from it. This is the enforcement of invariant
8, and the goal-6 check `aios-classification-negative` (an undeclared path bound
into a world or seat fails the build) lands with the goal-2 plan.

Rules, all at evaluation time, in the style of the existing `host-core`
assertions:

- a seat's `egress` names a declared broker instance, and a seat with an
  off-box egress cannot see a `local-only` basket (today's basketStore
  assertion, kept);
- a `placement.vm` names a declared `aios.vms` entry, and that guest's
  `egress` equals the seat's;
- a workflow's `ladder` resolves to at least one `[[route]]` row in
  `docs/ledger/routing.toml` for `role = implement` and one for `review`;
- a world's `sink` is a kind `streams.py` knows;
- the rendered declaration (`aios.json`, a store path) is the only thing the
  daemon reads. Invariant 5: policy is Nix, reviewable in a diff.

`aios.vms` renders to microvm.nix's `microvm.vms.<name>` with
`hypervisor = "cloud-hypervisor"`, a virtiofs share per entry, and a vsock
CID. The guest's NixOS configuration gets the broker's CA bundle
(`/var/lib/egress-broker-ca-bundle/<name>/ca.pem`) as a read-only share and
an `HTTPS_PROXY` pointed at the broker over vsock; it gets no other route.
Invariant 3 holds inside a guest exactly as it holds in a namespace today.

## 5 The daemon

`aiosd`, one Rust binary in `pkgs/aiosd/`, in the same Cargo workspace as the
guard (`pkgs/guard/`, IS23). `#![forbid(unsafe_code)]`. Dependencies from the
fork: `nix-compat` (store paths, NAR hashes, derivation JSON) and `tvix-eval`
(evaluating the declaration in tests without a Nix daemon). The fork is a
flake input pinned in `flake.lock`; Cargo sees it as a path dependency the
flake provides. rustfmt and clippy land in `lint` with the crate (rule: a new
language brings its formatter and linter).

Responsibilities, each a module with one owner type:

- **declaration**: parse `aios.json`, refuse it on any unknown field, expose
  typed views. The daemon starts from nothing else.
- **vm**: start, stop and observe `aios.vms` guests through the microvm.nix
  units (`microvm@<name>.service`) — lifecycle, not hypervisor API. States
  `Declared → Booting → Running → Contained → Stopped`; `Contained` is entered
  when the guard or the broker refuses a seat inside the guest, and the guest
  is frozen for the operator, not killed (concept B16's `ContainedAttack`,
  kept as a state, not a claim).
- **workflow**: the seat driver's contract, unchanged. Input a plan file and
  key; output `~/factory/runs/<run>/<KEY>.log`, `<KEY>.result` with the
  `FACTORY-RESULT status=`, `FACTORY-CHECKS`, `FACTORY-COMMITS`, `FACTORY-NOTES`
  lines, `<KEY>.escalate` on ladder exhaustion, a `task/<KEY>` branch, a
  workspace. The verdict is the last `FACTORY-REVIEW-SUMMARY key= verdict=`
  line. The differential check holds the daemon to this grammar byte for byte.
- **scheduler**: a hard gate then a rank (concepts A14/B19). The gate refuses
  a task whose routing row is missing, whose cap is reached (`SEAT_MAX_UNITS`
  semantics, counted from the units the daemon itself started), whose
  workflow is held, or — for a world or an `aios.models` server — whose VRAM
  budget plus the budgets already running would exceed the card's declared
  total. The rank is the routing ladder's rung order. A session mid
  tool-loop keeps its route until the loop ends (A7/B2, the hysteresis idea,
  without the entropy arithmetic). Thresholds — the rung to start at per
  kind/size — are read from the evidence store's `gate-verdict` history, not
  hard-coded (A4/B6): the first version reads them, a later one tunes them.
- **evidence**: `streams.py`'s `KINDS` ported to Rust types with the same
  envelope (`v`, `ts`, `kind`), the same name fence and secret scanner, and
  a test that renders every kind from both implementations and diffs them.
  New kinds: `vm-state`, `world-pick`.
- **api**: a Unix socket at `/run/aiosd.sock`, JSON lines, read-only queries
  plus the three seat verbs Helm already exposes (start, stop, attach). Helm
  becomes a client of this socket; `api_seats.py` is its first caller.

The daemon observes basket state — which `aios.data` classes are mounted, for
whom, until when — and refuses to start a seat or world whose declared classes
are not mounted; a `data-state` row records each transition.

What the daemon does not do in this spec: terminate TLS (the broker does),
mount baskets (root-only `basket mount` under the operator's YubiKey stays,
invariant 4, until a later spec moves it),
replace `factory-review` (the gate is a workflow step the daemon invokes),
speak to cloud-hypervisor directly (later, when a measurement asks for it).

## 6 Data flow: the goal-2 path

1. `nixos-rebuild switch` (operator) activates a system whose `aios.json`
   declares one VM, one seat placed in it, one workflow, one egress instance.
2. `aiosd.service` starts after the broker, reads `aios.json`, registers the
   guest as `Declared`.
3. A workflow task arrives (today: `factory-task`'s inputs; the daemon takes
   the same environment). The scheduler gates and ranks it; the `vm` module
   starts the guest; `Booting → Running`, a `vm-state` row.
4. The seat starts inside the guest with the clone bound in over virtiofs and
   the broker as its only route. Every request carries `x-factory-task:
   <run>/<KEY>`; the broker injects the credential from `valueFile`, refuses
   deny-listed paths, and appends `audit.jsonl` and `usage.jsonl`.
5. The seat lands `task/<KEY>`; the daemon reads `.result`, invokes the gate,
   reads the verdict line, integrates on approve. `factory-run`,
   `task-result`, `gate-verdict` rows land with the same fields as today.
6. The guest stops (`Stopped`), or freezes (`Contained`) if the guard refused
   a write or the broker refused a request during the run.

No new mechanism on this path. It is today's path with the daemon in place of
three shell scripts and a VM in place of a network namespace.

## 7 What is adopted from the notebook, and what is not

Adopted, as stated above: gate-then-rank (A14/B19), session-locked routing
(A7/B2), a first-class contained state (B16), thresholds from ground truth
(A4/B6, B21's timer as the tuning cadence later), one zero-copy IPC choice
deferred until the daemon's socket measures as a bottleneck (A13 vs B13).

Not adopted, with the reason on record: eBPF pre-TLS interception (A15/B10)
because the broker terminates TLS and already sees plaintext; AF_XDP and the
SIMD classifier (A16/B11), unbuilt and unmotivated on one host; Mamba-2 (A10)
and speculative trajectory drafting (A9), benchmark theatre; the self-seeding
dashboard (A20); the compliance suite (A23); CXL and SPDK (B7/B8), hardware
the host lacks. Every number the notebook attached stays UNVERIFIED and none is
cited here.

## 8 Migration order

By goal, one plan per step, each gated on its check going red then green:

1. **Goal 1.** The Cargo workspace (guard crate as IS23 typed it plus an
   `aiosd` that parses `aios.json` and exits), the fork as a flake input,
   `aios-public-build` on the publish-gate export. Brief §1's "nothing goes to
   GitHub" amended to name the public remote as the one exception, through
   the gate.
2. **The guard cutover.** IS22, IS24, IS25 as released 2026-09-22.
3. **The daemon dispatches.** `workflow` + `scheduler` + `evidence` modules,
   `aiosd-dispatch-differential` red then green, the bash driver kept as the
   reference until the differential has held for a fortnight of runs.
4. **Goal 2.** `aios.vms` + `aios.seats` with `placement.vm`, microvm.nix,
   `aios-workflow-vm`. The lane placement stays for dsh.
5. **Goal 4.** `aios.worlds` over the ComfyUI module, unit placement,
   `aios-world-service`, the `world-pick` kind; with it `aios.models` and the
   first local model (a measured fit beside the generator) as the world's judge
   and embedder, the VRAM gate in the scheduler, and goal 6's
   `aios-classification-negative` over the world's declared inputs.
6. **Goal 3.** The public task-list render and its check; the export; one
   invited person; the first outside landing.

**Planning scope (operator, 2026-09-22): the first plan covers step 1 alone** — the
Cargo workspace (guard crate as IS23 typed it, an `aiosd` that parses `aios.json`
and exits), the fork as a flake input, the `aios-public-build` check on the
publish-gate export, the brief §1 amendment, and the subsystem rows those paths
need. Steps 2–6 are later plans, each typed only after the previous step's check
is green. A plan that types a step-2+ task is out of scope.

**Planning scope, goal 2 (operator, 2026-09-22 ~18:00, "begin goal 2 planning";
decision `docs/decisions/2026-09-22-goal-2-planning.md`).** Goal 2 is typed as two
plans, in this section's order. **Plan A**, `2026-09-22-aios-daemon-dispatch.md`, covers
step 3 — the daemon's `workflow`, `scheduler` and `evidence` modules,
`aiosd-dispatch-differential` red then green, the bash driver kept as the reference — and
two things step 4 needs before its own plan is typed: (a) the measurement §9 demands,
whether microvm.nix's cloud-hypervisor backend gives virtiofs and vsock on `core`'s
kernel, landed as claim rows in `docs/ledger/claims.toml` (the qemu backend is the
fallback, same declaration); (b) `aios-classification-negative` over a seat's declared
inputs (goal 6; the addendum of `docs/decisions/2026-09-22-freeze-and-triage.md` put it in
the goal-2 plan). Plan A types no guest: `aios.vms`, `aios.seats.<name>.placement.vm`,
microvm.nix as an input and `aios-workflow-vm` are plan B's. Plan A is typed before
step 2's check is green, on the operator's word; its tasks carry `dependsOn` on the step-2
keys (IS22, IS24, IS25) wherever the daemon's modules read what the guard cutover lands,
so nothing dispatches early. **Plan B**, step 4, is typed once
`aiosd-dispatch-differential` has gone red then green and the claim rows of (a) are filed
— not after the fortnight, which retires the bash driver, not the typing. The routing of
plan A's seats is open: the operator's word of 2026-09-22 unpins the OpenRouter models
("anything openrouter has available is free to use"); plan A's routing question recommends
one model per role from the numbers in the decision file, and the answer lands as
`docs/ledger/routing.toml` rows before wave 1 dispatches.

Helm, the board scripts, the review-ladder shell and the bash factory are
scaffolding: each is retired in the step whose daemon module makes it
redundant, never before.

## 9 Failure modes

- The fork's crates fail to build outside the depot: `shell.nix` provides a
  depot-less fallback (`~/flakes/tvix-aios/shell.nix:1-9`); if `nix-compat`
  or `tvix-eval` cannot be built as a flake output from that shim, step 1
  pins them by Cargo git dependency to the fork's commit instead and records
  the deviation.
- microvm.nix's cloud-hypervisor backend refuses virtiofs or vsock on this
  kernel: the goal-2 plan measures both on `core` before typing the seat
  guest; the fallback is the qemu backend, same declaration.
- The daemon's `.result` grammar drifts from the bash driver's: the
  differential check fails and the daemon does not replace the driver.
- A guest can reach anything but the broker: `aios-workflow-vm` includes a
  negative arm that curls a LAN address from inside the guest and expects
  refusal.
- `aios.json` carries a private literal into the public snapshot: it is a
  store path, not a tracked file; the publish gate's deny scan covers the
  Nix that renders it.

## 10 Open operator questions

None blocking. Two to answer before step 6: the project name on the public
README (loose-ends item 11 recommended a distinct name; "tvix-aios" is in use
and promises an evaluator this spec makes a library), and whether goal 4's
acceptance — a world boots as a service, runs one loop round, lands a pick —
is what "functional part of the operating system" means.

## 11 Governance and contribution (added 2026-09-22 evening, decision `docs/decisions/2026-09-22-public-project.md`)

The operator, after §1–10 were approved: the project is public, open-source, easy to
use, memory-safe, AI-native with generation as OS functions (image, video, audio,
text, code); decisions are democratic; contributors donate tokens — their own
subscription LLM allowance — and the project controls the plan, the distribution of
work and the ledger. Confirmed reading: each contributor's seat runs on their own
machine under their own subscription, takes tasks they accept from the public queue,
and the project reviews, merges and credits.

What this adds to the design, each a later plan:

- **The public queue.** The task-list render (goal 3's check) is the queue contributors
  read; a task carries key, title, size, acceptance check names, and a claim state.
  Claiming is a signed ledger row, not an assignment by a person.
- **The contributor seat.** `aios.seats.<name>` gains `login = "subscription"`: the seat
  authenticates with the contributor's own provider login inside the guest; the broker
  on their machine injects nothing and only logs. The project's broker never sees a
  contributor's credential. This is the provider-terms line: their machine, their
  login, tasks they accepted.
- **The vote.** A proposal is a plan section; the electorate is every ledger identity
  with one landed contribution; a vote is a ledger row; the tally is derived by
  `evidence`, never typed. The operator holds a veto for invariants §3 only.
- **The ledger.** Streams `contribution` (key, contributor, tokens reported by the seat,
  verdict, landed commit) and `vote` join the evidence store; the public export renders
  both. The operator's own behaviour streams (`operator`, `engagement`) stay local.
- **Generation as OS functions.** `aios.worlds` generalises from the ComfyUI worlds to
  image, video, audio, text and code generators with the same shape (generator, loop,
  judge, sink). Goal 4's first world stays image.

Publish posture flips: plans, reviews, research, decisions and the routing, task-status,
plan-status and rules ledgers move to `publish` (after the deny scan clears each); keys,
host hardware identity, credentials, `.claude/`, the board and the operator streams stay
withheld. Brief §1's self-hosted-only constraint is removed. Typed as a PG-family task
after the goal-1 plan lands; not a hand edit to the manifest.
