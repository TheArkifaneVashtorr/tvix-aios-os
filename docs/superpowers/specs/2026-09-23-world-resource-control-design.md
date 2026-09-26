# World resource control and a resource tile — design

**Status:** draft, 2026-09-23. Measured on core at generation 83.

## 1. The problem, measured

Authoring a world throttles the operator's interactive session. The obvious
explanation — the local author model and the generator fighting over the
5090 — is wrong. `Conflicts=` (`media/nixosModules/comfyui-worlds.nix:95`,
`media/nixosModules/local-model.nix:35`) does what it declares: measured over
the 05:13–05:20 window of 2026-09-23, `comfyui-nsfw` is fully `Stopped`
before `comfy-author-model` reaches `Started`, ~39 s later. The two never
co-hold GPU memory.

What reaches the desktop is CPU and host-RAM churn from the authoring
cadence. Per cycle, repeating every ~2 min 11 s for as long as a world
authors:

| unit | memory peak | CPU per cycle |
|---|---|---|
| `comfyui-<world>` | 23.2–25.6 GB | ~2 min 35 s (≈1.2 cores) |
| `comfy-author-model` | 0.7–2.1 GB | 2–4 min (≈1 core sustained) |
| `comfy-feed` | 2.4 GB | 3 min 9 s over 11 h 36 m |
| `comfy-run-<world>` | 101–124 MB | 1–4 min over hours |

The mechanical cause is that **every comfy unit is user-scope and lives in
`app.slice`** (measured: `systemctl --user show comfyui-sfw -p Slice`), the
same slice as every interactive application the operator runs. Nothing tells
the kernel that a batch render matters less than the window in front of the
user. Under that arrangement the throttling is not a bug; it is the declared
behaviour.

Two facts bound any fix. The host has **no swap** (`/proc/swaps` is empty,
131 GB total), so a 25 GB spike has headroom as its only protection —
`systemd-oomd` itself reports "No swap; memory pressure usage will be
degraded". And **`IOAccounting` is off** for these units (user-manager
default), so IO figures do not exist even in principle until accounting is
turned on.

## 2. What must not change

- **`Conflicts=` stays.** It is what makes GPU exclusivity true, and
  `BUG-world-target-supervisor-deadlock` (`docs/ledger/bugs.toml:188-196`)
  documents what reopens when turn-taking is expressed any other way. Limits
  govern how much a unit may use *while it runs*; they never decide *whether*
  it runs. Replacing serialization with limits would reintroduce the
  double-hold failure this project already measured.
- **Device-level gating is proven not to work here.**
  `comfyui-worlds.nix:11-18`: `DevicePolicy`/`DeviceAllow` are a silent no-op
  under the per-user manager, because BPF cgroup programs cannot attach
  there. No design may reach for them.
- **`contextSize = 16384` is the operator's sizing decision**
  (`hosts/core/media-worlds.nix:60-68`, 2026-09-22), and the direct cause of
  the large footprints above. It is a constraint to accommodate, never slack
  to reclaim.
- **Target membership is not the lever.** GN43's revert
  (`comfyui-worlds.nix:184-208`) is the precedent: a lifecycle problem fixed
  by changing `wants=` deadlocked. This change lives in the units'
  `serviceConfig`, or in a slice they are moved into.
- **Brief §3 invariant 8.** A monitor emits resource numbers only. Never
  prompt text, image content, or anything derived from what the user dwelt
  on — a world's learning signal is user data.

## 3. The design

### 3.1 A slice for generation

Declare a user slice — `comfy.slice` — and move every world unit into it
with `Slice=comfy.slice`: both generators, the feed, both supervisors, both
mutators, and the author model. One slice, so the *aggregate* of world work
is bounded rather than each unit separately; a per-unit cap cannot stop three
units summing to the whole machine.

On the slice:

- **`CPUWeight`** below the default 100, so world work yields to interactive
  work under contention and is otherwise unrestricted. A weight, not a
  `CPUQuota`: a quota wastes idle cores, and the machine is idle most of the
  time. The generator is not single-threaded (≈1.2 cores measured), so this
  is the axis that matters.
- **`MemoryHigh`** as soft backpressure — the kernel reclaims and throttles
  the slice past the threshold instead of killing it. With no swap and 25 GB
  spikes, `MemoryMax` would convert a slow cycle into an OOM kill mid-render.
  `MemoryMax` may sit far above `MemoryHigh` as a last-resort ceiling.
- **`IOWeight`**, and **`IOAccounting`, `CPUAccounting`, `MemoryAccounting`
  on**, which is also what makes §3.2 possible.

The existing precedent in this repo is the right shape applied to the wrong
module: `media/nixosModules/comfyui.nix:209,429-430` already surfaces a
`resources.memoryMax` option into `MemoryMax=` with `Nice = 5`, but that
module is not enabled on core — only `services.comfyui-worlds` is. This
design brings that shape to the units that actually run, as module options
with defaults, so the numbers are declared in Nix and wrong values fail the
build rather than being tuned at runtime (invariant 5).

### 3.2 A `comfy` tile

Helm already collects nine tiles every 300 s (`pkgs/helm/collect.py:29-39`),
including `gpu` and `host`, through a `@tile` decorator. A tenth tile reads
the slice's own cgroup accounting — CPU seconds, current and peak memory, IO
— plus which world units are active, and reports `ok`/`warn`/`fail` with the
numbers in `detail`. This is an emitter, not new infrastructure.

**Read-only, deliberately.** `helm-api` has no `--user` systemctl path at all
and runs as a dedicated system user with an empty capability bounding set
(`nixosModules/helm.nix:915-941`), and the Helm plan draws the boundary
explicitly: "the worlds … Generation; Helm only links"
(`docs/superpowers/plans/2026-09-11-helm.md:146`). Control over user-scope
world units belongs to the feed process, which already does it. A tile that
observes is in scope; a button that acts is a different change.

### 3.3 History: the one open decision

`status.json` is overwritten every cycle (`collect.py:1012`), and the durable
`helm-status` stream carries only per-tile `ok|warn|fail` plus a `change|
heartbeat` reason (`pkgs/evidence/SCHEMA.md:30`) — **no numeric detail is
retained anywhere today**. So "what did memory do during last night's
authoring run" is not answerable now and would not become answerable by
adding a tile.

The recommendation is to keep this change read-only-and-current, and treat a
numeric time series as its own task: the existing stream is change/heartbeat
shaped by design and widening it to carry samples changes what every consumer
reads. The journal already retains per-cycle accounting (that is where §1's
numbers came from), so nothing is lost meanwhile.

## 4. Acceptance

- The slice exists, every world unit reports `Slice=comfy.slice`, and a
  negative check fails the build if a world unit is added without one.
- A generator under sustained load leaves an interactive process's scheduling
  latency materially better than today — measured, not asserted, in the
  worlds VM check.
- `Conflicts=` behaviour is unchanged: the model and a generator still never
  co-hold the GPU, proven by the same transition assertion `comfy-worlds-vm`
  already makes.
- `MemoryHigh` throttles rather than kills: a unit driven past the threshold
  completes its cycle.
- The tile appears with numeric detail and no content of any kind.

## 5. Not in this design

Numeric history or trend (§3.3). Any Helm-side control of world units. GPU
partitioning or MPS. Changing `contextSize`, the authoring cadence, or the
supervisor's ordering — `BUG-world-target-supervisor-deadlock` is a separate
fix and this design must not be read as addressing it.
