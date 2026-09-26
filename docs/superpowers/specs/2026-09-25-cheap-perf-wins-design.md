# Cheap performance wins: resource policy, host metrics, a statistical fence, flow metrics — design

**Status:** draft, 2026-09-25, measured at HEAD `b70c4f7c` on the live
generation (NixOS 26.05, systemd 260.2, Linux 6.18.49). Not yet judged.
Operator request the same day: "Write a spec for the cheap wins". The four
wins come from `docs/research-2026-09-25-os-building-and-perf-metrics-web.md`
("The cheap ones for a small NixOS project"; Findings A6, A7, A9, B3, B6).

## 1. Purpose, and where each win sits against the freeze

Four small changes, each built on something the pin or the store already
has:

- **W1, resource policy.** systemd-oomd watches the seat slice. Per-unit
  accounting is pinned on for both managers. zram is decided, and swap
  hygiene becomes a build assertion.
- **W2, host metrics in the evidence store.** One row per seat stop, derived
  from systemd's journal summary, plus a periodic PSI sample.
- **W3, statistical performance gating.** An interquartile-range fence over
  durations the store already records, plus two nightly `hyperfine`
  benchmarks.
- **W4, process metrics.** `evidence report flow` computes time to gate,
  time to land, approval, rework and change failure from the store and git.

**Against the decisions.** `docs/decisions/2026-09-22-freeze-and-triage.md`
tests every task with one question: does it become part of the OS image, or
a test of it? `docs/decisions/2026-09-23-fix-what-wastes-seats.md` lets fixes
that save seats proceed. Features of the bash scripts stay frozen.

- **W1 becomes part of the image.** Resource control is an OS primitive
  (brief §2 names VM lifecycle and scheduling as OS-owned). By measurement it
  is *not* a seat-saving fix, because no OOM has happened (§2.1).
- **W2 becomes part of the image.** Brief §2 says "The OS owns … evidence and
  telemetry". Its writers are `pkgs/evidence` and `pkgs/helm`, not the bash
  factory.
- **W3 is a test of the OS.** It stays report-only, because refusing
  integration would be a feature of the frozen integrator (D4).
- **W4 sits nearest the freeze line.** The 2026-09-22 triage withdrew EV20
  as "queue bookkeeping". W4's case is the goal metric the 2026-09-23
  decision set ("operator minutes per landed task"), which nothing computes
  today. The operator asked for W4 explicitly, which is their call to make.

## 2. What exists (measured)

### 2.1 Resource policy (W1)

**oomd runs and watches nothing.**
- `nix eval --json .#nixosConfigurations.core.config.systemd.oomd.<opt>`
  gives `enable` = `true`, `enableRootSlice`/`enableSystemSlice`/`enableUserSlices`
  = `false`, and `settings` = `{"OOM":{}}`.
- `oomctl` lists no cgroups under both "Swap Monitored CGroups" and "Memory
  Pressure Monitored CGroups". It shows the defaults "Memory Pressure Limit:
  60.00%" and "Duration: 30s".
- `journalctl -u systemd-oomd --since -30d` shows 15 lines of "No swap;
  memory pressure usage will be degraded" and no kill.
- The pinned `oomd.nix` (under `core.pkgs.path`) sets
  `ManagedOOMMemoryPressure = "kill"` with `mkDefault "80%"` only on the `-`,
  `system` and `user` slices, and only when their flags are on. This settles
  the research report's open question: the host pin's defaults match the
  `release-26.05` head.

**Seats live in `system-seat.slice`.**
- `systemctl show seat@<id>.service -p Slice` gives the template's implicit
  `Slice=system-seat.slice`.
- `nixosModules/seatLane.nix` sets no `Slice=`, `MemoryHigh`, `MemoryMax` or
  `CPUWeight`.
- On a live seat, `ManagedOOMMemoryPressure=auto` and `MemoryHigh=infinity`.

**There is plenty of headroom, and no OOM on record.**
- `/proc/meminfo` shows `MemTotal` 131031400 kB, `MemAvailable` 111551632
  kB and `SwapTotal` 0. `/proc/swaps` holds only its header.
- `journalctl -k --since -30d | grep -ciE 'out of memory|oom-kill'` gives 0.
- `oom_kill` is 0 in `memory.events` for `system.slice`, `user.slice` and
  `system-seat.slice`.
- `/proc/pressure/memory` shows `full … total=33443497` µs. That is 33.4 s
  of full stall over an uptime of 196766 s (2.3 days).

**Seat footprints run large at the tail.**
- The journal summary (§2.2) gives `MEMORY_PEAK` for 419 `seat@` stops in 30
  days: p50 749 MB, p90 2.86 GB, max 33.9 GB. Seven stops exceeded 8 GB.
- The slice's `memory.peak` is 29.4 GB.

**Accounting is already on for system units.**
- `systemctl show -p DefaultIOAccounting -p DefaultIPAccounting -p DefaultMemoryAccounting -p DefaultTasksAccounting`
  prints `yes` four times.
- The source is nixpkgs, not this repo: `systemd.nix:742-743` holds
  `lib.mkDefault true` for IO and IP accounting.
  `nix eval …config.systemd.settings.Manager` shows both as `true`.
- CPU accounting is always on under cgroup v2 (research A6).
- **The user manager is the gap.** `systemctl --user show -p DefaultIOAccounting`
  prints `no`, and `systemd.user.extraConfig` evaluates to `""`. This is the
  hole `docs/superpowers/specs/2026-09-23-world-resource-control-design.md`
  (WR) §1 found for the comfy units.

**zram and zswap are both off.**
- `nix eval` gives `zramSwap.enable` = `false`, `memoryPercent` = `50`,
  `algorithm` = `"zstd"`, `writebackDevice` = `null` and `swapDevices` =
  `[]`.
- `/sys/module/zswap/parameters/enabled` reads `N`.

**Swap is refused twice, on purpose.**
- `pkgs/basket/basket.sh:350-351` fails the basket doctor on any `/proc/swaps`
  entry, with "tmpfs pages could reach disk (invariant 1)".
- `collect.py`'s `tile_host` returns `fail, "swap in use"`.
- Both are pinned by tests: `tests/unit/50-doctor.bats:18` and
  `tests/helm/test_collect.py:770`.

**PSI, BTF, THP, KSM and delayacct.** `/proc/pressure/{cpu,memory,io,irq}`
and `/sys/kernel/btf/vmlinux` exist. THP is `[madvise]`, KSM `run` is `0`
and `kernel.task_delayacct` is `0`.

### 2.2 Host metrics (W2)

- **No kind carries host resources.** In `pkgs/evidence`,
  `python3 -c 'import streams; print(len(streams.KINDS))'` prints 19, and
  none of the 19 does. `tests/evidence/test_engagement.py:65` pins the
  count at 19.
- **The stop-time summary is structured.**
  `journalctl MESSAGE_ID=ae8f7b866b0347b9af31fe1c80b127c0 -o json` on a seat
  stop carries these fields:
  - `CPU_USAGE_NSEC`, `MEMORY_PEAK` and `MEMORY_SWAP_PEAK`;
  - `IO_METRIC_{READ,WRITE}_{BYTES,OPERATIONS}`;
  - `IP_METRIC_{INGRESS,EGRESS}_{BYTES,PACKETS}`;
  - `UNIT` and `INVOCATION_ID`.

  Wall-clock time appears only in the `MESSAGE` text ("over 32min 16.769s
  wall clock time").
- **Volume and history.** There were 75 seat lines in 2 days and 419 in 30
  days, the first on 2026-09-08. The journal holds 843.7M.
- **The live properties populate.** `systemctl show` on a running seat gave
  `CPUUsageNSec=144108489000`, `MemoryPeak=816181248`,
  `IOReadBytes=65540096`, `IPIngressBytes=99819081` and `TasksCurrent=37`.
- **The join key exists.** `task-result.seat_unit`
  (`^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$`) is the `seat@` instance name. It is set
  on 372 of 692 `derived/tasks` rows.
- **Per-cgroup PSI exists.** `system-seat.slice` carries `{cpu,memory,io}.pressure`,
  `cpu.stat` and `memory.peak`. Its `cgroup.subtree_control` is
  `io memory pids`. `nix-daemon.service`, `user.slice` and `machine.slice`
  all carry `memory.pressure`.
- **Helm already samples every 300 s.** `helm-collect.timer` is
  `{"OnBootSec":"2min","OnUnitActiveSec":"300s"}`. `collect.py` imports
  `evidence` and writes `helm-status`, but keeps no numeric history. WR §3.3
  left "a numeric time series as its own task", and W2 is that task.
- **No microVM runs as a host unit yet.** SG1 is gated and approved. SG2–SG5
  build the guest as a check-time runner and wire no `microvm@` unit on
  core (plan `2026-09-24-strict-user-spaces-1a.md`, SG2 item 1).
- **Store size.** `du -sh` on the store gives 156M, of which
  `ledger/otel-claude.jsonl` is 137 MB.

### 2.3 Durations already recorded (W3)

Read with `nix develop -c python3` over the store:

| field | rows | populated | shape |
|---|---|---|---|
| `checks.duration_s` | 3951 (09-05 → 09-25) | 3943 | **2649 are `0`** (cached; no built/substituted flag), max 2819 |
| `derived/tasks.wall_s` | 692 | 692 | median 1144 s, p75 2250 |
| `derived/tasks.verify_s` | 692 | 433 | median 21 s |
| `derived/gates.wall_s` | 666 | **0** | never written |
| nightly `flake-check` | 24 | 24 | 12 red; green 90 → 415 s, rising as checks were added |

The fence's inputs are built green rows: `duration_s ≥ 2`, `ok`, and not
nightly.
- Eleven check names have at least 12 such rows. The largest are `lint`
  (n 364, median 9 s), `unit` (n 125, median 222 s), `evidence-unit` (n 121,
  median 16 s) and `host-core` (n 84, median 11.5 s).
- A whole-history fence at Q3 + 3×IQR flags none of those four.
- It flags 1 `ledger-unit` row and 2 `seat-vm` rows. Both are 1–3 s series
  where IQR = 0 makes the fence degenerate.

**Tools.**
- The pin carries `hyperfine` 1.20.0 and `pyperf` 2.10.0
  (`nix eval --raw …pkgs.hyperfine.version`).
- `hyperfine` is not in the devShell.
- One `nix eval --no-eval-cache --raw …toplevel.drvPath` took 14.8 s, and
  `tasks brief` via `nix develop` took 4.0 s.

### 2.4 Process data (W4)

Computed from `derived/tasks`, `derived/gates`, `checks.jsonl` and
`git log --first-parent main`:

- **First-gate approval:** 319 of 490 (65.1%).
- **Rework:** 109 of 416 chains (26.2%) have a `fix` or `replan` round.
- **Time to gate (filed):** `result_mtime` → `review_commit_ts`, n 396,
  median 0.29 h, p90 1.0 h.
- **Time to land:** `result_mtime` → the `integrate <KEY> into …` commit.
  There are 328 such commits since 09-04, no key twice, 319 joined. Median
  0.5 h, p90 3.46 h.
- **Change failure:** the nightly check went green→red 4 times in 24
  nights, and was red on 12 of them.
- **Operator wait:** `ledger/operator` totals 938 min of `latency_s` over
  165 answers since 09-22, against 73 landings.

## 3. Decisions

### D1 — W1: a resource-policy module, asserted at eval

`nixosModules/resourcePolicy.nix` (`aios.resources.*`, imported by core and
the future image) declares three things.

**1. oomd on the seat slice.**
`systemd.slices.system-seat.sliceConfig = { ManagedOOMMemoryPressure = "kill"; ManagedOOMMemoryPressureLimit = "80%"; }`,
with oomd's 30 s duration.
- It is a drop-in on the implicit template slice, so cgroup paths and their
  readers stay unchanged.
- oomd acts on *full* pressure ("all tasks … delayed", `oomd.conf(5)`), not
  on size. A 34 GB seat alone is never a candidate.
- In a thrash across heavy seats, oomd kills the one with the most reclaim.
  The other seats and the desktop live.

**2. User-manager accounting.** `systemd.user.extraConfig = "DefaultIOAccounting=yes"`.
The system manager's `DefaultIOAccounting` and `DefaultIPAccounting` are
restated as plain values. A nixpkgs bump that drops its `mkDefault` then
fails A1, instead of silently emptying W2's IO fields.

**3. Assertions.**
- (a) With `services.seat-lane` enabled, the `system-seat` slice carries
  `kill`, and `seat@` sets no `Slice=`.
- (b) `zramSwap.enable -> zramSwap.writebackDevice == null`. zram keeps
  pages in RAM, but a writeback device would spill tmpfs pages to disk,
  against invariant 1.
- (c) `swapDevices == [ ]`. This makes the basket doctor's runtime refusal
  of disk swap a build fact.

**zswap is rejected.** It caches in front of a *real* swap device (research
A6), and that is what invariant 1 forbids.

**zram is Q2. The recommendation for core is no.**
- The host has 125 GiB with 18.5 GiB used (`oomctl`), no OOM in 30 days and
  33 s of full stall in 2.3 days.
- Turning it on means amending the basket doctor and the host tile to tell
  `/dev/zram*` from a partition, and changing both pinning tests.
- The option and assertion (b) land regardless, so the image can turn zram
  on for a small contributor machine, where it pays.

**Rejected alternatives.**
- `enableSystemSlice` would bring the broker, nix-daemon and Helm into
  scope.
- `enableUserSlices` (Q3) would bring the desktop and the 25 GB world
  renders into scope before WR's `comfy.slice` exists.
- A per-seat `MemoryMax` would kill legitimate 34 GB seats.
- A seat `MemoryHigh` has no measurement to size it.
- The v260 oomd prekill hook is synchronous and privileged, and the kill is
  already in the journal.
- sched_ext, KSM, THP and delayacct were not asked for.

### D2 — W2a: `unit-resources`, derived from the journal

A new kind `unit-resources`, stream `derived/unit-resources`, key
`(unit, invocation)`. It is written with `replace_stream`, an idempotent
upsert: re-runs change nothing, and rows outlive the journal.

| field | class |
|---|---|
| `unit` | `re ^(seat@[0-9]{8}-[0-9]{6}-[0-9a-f]{6}\|microvm@[a-z0-9][a-z0-9-]{0,62})\.service$` |
| `seat_unit` | null or the `task-result.seat_unit` regex (the join) |
| `invocation` | `re ^[0-9a-f]{32}$` |
| `stopped` | `ts` (from `__REALTIME_TIMESTAMP`) |
| `cpu_nsec`, `memory_peak`, `memory_swap_peak`, `io_read_bytes`, `io_write_bytes`, `io_read_ops`, `io_write_ops`, `ip_in_bytes`, `ip_out_bytes` | null or `int` (null = field absent) |

**Writer.** `evidence ingest unit-resources [--since]`, a new
`INGEST_MODULES` entry.
- It reads `journalctl -o json MESSAGE_ID=ae8f7b86… --since …` and keeps
  units matching the regex. It **never reads `MESSAGE`**. Wall time comes
  from the `task-result` join.
- It runs each `helm-collect` cycle with `--since -1h`. The operator runs
  one backfill with `--since 2026-09-08` (419 rows).
- The regex already admits `microvm@`. That arm is fixture-tested until a
  host unit exists.

**Data class.** Counts only, like engagement. There is no path and no cgroup
path (which would carry a uid). The name fence already refuses `path`,
`host` and `cmd`.

**Rejected alternatives.**
- **`ExecStopPost=` on `seat@`.** `InaccessiblePaths` hides the system bus,
  so `systemctl show` cannot run there. It would also give the seat
  sandbox a store writer, and the summary is logged after ExecStopPost.
- **Polling `systemctl show`.** Properties vanish when the instance unloads.
- **Parsing `MESSAGE`.** It holds nothing the fields lack except wall time.
- **A new timer.** `helm-collect` runs anyway, and the `timers` tile audits
  it.

### D3 — W2b: `pressure`, sampled by Helm

A new keyless kind `pressure-sample`, stream `pressure`. `helm-collect`
appends one row per cycle.

| field | class |
|---|---|
| `scopes` | `map`, key `enum (host, seats, nix-daemon, users, machines)`, value `obj {cpu_some_us, mem_some_us, mem_full_us, io_some_us, io_full_us}` (`int`: the PSI `total=` counters) |
| `mem_available_kb` | `int` |
| `seats_running` | `int` (child `seat@*` cgroups) |

**Totals, not averages.** The difference between two rows gives the exact
stall for any window. A negative difference marks a reboot and is dropped.

**Scopes.** Each scope maps to a fixed file, and no row carries the path:
- `host` → `/proc/pressure/*`
- `seats` → `system-seat.slice`
- `nix-daemon` → `nix-daemon.service`
- `users` → `user.slice`
- `machines` → `machine.slice`

A missing file drops that scope from the row.

**Tile (Q5).** A `pressure` tile goes into `streams.TILES`. It turns `warn`
when memory-full or io-full stall over the last interval exceeds
`services.helm.pressure.*` (Nix, invariant 5; defaults 1% and 10%). WR's
proposed `comfy` tile would read the same stream.

**Growth.**
- Unit rows: about 25 a day (419 in 17 days) at about 500 B, so about 12
  KB/day.
- Pressure rows: 288 a day at about 800 B, so about 230 KB/day, or about
  7 MB/month.
- The store is 156 MB today. The monthly-partition reader (`SCHEMA.md`)
  already handles rotation.

**Rejected alternatives.**
- `node_exporter` is a listener on port 9100 that needs Prometheus, and its
  data never reaches the store.
- PCP has no NixOS module (research A7).
- The OTel `hostmetricsreceiver` through `otelIngest.nix` means a contrib
  collector for five files.
- PSI triggers need a resident poller.
- Widening `helm-status` breaks the change/heartbeat shape WR §3.3 kept.

### D4 — W3: an IQR fence, report-only, and two nightly benchmarks

**Detector: rustc-perf's fence (research B3, [111]).**
- The newest point of each series is judged against a trailing window of
  the previous 20 points (refused under 12).
- It is flagged *slower* above Q3 + 3×IQR and *faster* below Q1 − 3×IQR.
- IQR is floored at 1 s (the recorder's resolution), and a flag needs an
  absolute delta of at least 5 s. The degenerate series in §2.3 need both
  floors.
- The source contradicts itself (prose 1.5×, code 3×). This spec takes 3×,
  as one tested constant.

**Why this detector.**
- Perfherder's 3-of-5 vote needs a 12-point forward window. On the nightly
  series that means 12 days late, and it brings scipy into a verdict path
  that is stdlib today (`report.py` uses `statistics`).
- Change-point detection explains a history. It does not judge today's
  point, so it is a later analysis over the same rows.
- Fixed thresholds are what MongoDB abandoned.

**Series.**
1. Each check name, over `ok` rows with `duration_s ≥ 2` that are not
   `helm-nightly`. The 2 s cut is a heuristic that stands in for the
   built/substituted flag the frozen recorder lacks.
2. The nightly `flake-check`, green rows only.
3. Each benchmark.

**Benchmarks.** A `helm-bench` user timer (default `*-*-* 04:30:00`, after
the 03:00 flake check) runs `hyperfine --warmup 1 --runs 10 --export-json`
on two targets:
- `eval-core`: the uncached toplevel `drvPath` eval, 14.8 s once. It is the
  baseline the tvix evaluator will be measured against.
- `tasks-brief`: the SessionStart brief, 4.0 s once.

**The `bench` kind.** A new keyless kind, stream `bench`, with fields:
- `name` (`enum (eval-core, tasks-brief)`), `rev`, `tool` (`enum (hyperfine)`)
  and `runs`;
- `median_ms`, `q1_ms`, `q3_ms`, `min_ms` and `max_ms` (`int`);
- `cpu_some_us` and `seats_running`, context from D3, so a reader can
  discount a run taken while seats were busy.

pyperf is rejected. It benchmarks Python functions, while ours are
commands, and `pyperf system tune` rewrites the CPU governor host-wide.

**Output.**
- `evidence report perf` prints each series with its n, window, fence and
  verdict.
- `evidence bundle` gains `perf: <k> series over fence`.
- **There is no integration refusal (Q7).** The integrator is frozen, and
  the nightly series rose from 90 to 415 s because checks were *added*.

### D5 — W4: `evidence report flow`, derived, no new stream

A `report.py` verb prints overall and ISO-week figures with n beside each,
and refuses cells under 5 (as `report plans` does):

| metric | definition | today |
|---|---|---|
| throughput | first-parent `integrate <KEY> into` commits per day (git) | 328 since 09-04 |
| time to gate (filed) | `result_mtime` → first `review_commit_ts`, same `(run_id, key)` | median 0.29 h |
| time to land | latest `result_mtime` before landing → landing commit | median 0.5 h, p90 3.46 h |
| first-gate approval | approved ÷ decided, `round_kind=first` | 65.1% (319/490) |
| rework rate | chains with `fix`/`replan` ÷ chains (DORA [142]) | 26.2% (109/416) |
| change failure | nightly green→red transitions ÷ nights; recovery = red → next green | 4 of 24 |
| operator wait per landing | Σ `latency_s` ÷ landings, labelled *wait* | 938 min / 73 |

There is no stored kind: every figure re-derives from existing rows, and a
`derived/flow` stream would only be a copy that goes stale. A `flow` tile renders
`report flow` each collect cycle (Q6 = yes: the operator's rule of 2026-09-25 — a
Helm-linked figure the GUI does not show is waste).

## 4. Acceptance

Each row is red before its change.

| id | check | red when |
|---|---|---|
| A1 | `resource-policy-eval` (new; `runCommand` over core's evaluated values) | any of: the `system-seat` slice lacks `ManagedOOMMemoryPressure=kill`; the user manager lacks `DefaultIOAccounting=yes`; system `Default{IO,IP}Accounting` is not `true` |
| A2 | `resource-policy-assertion-negative` | a config with `zramSwap.writebackDevice` set, or a disk `swapDevices` entry, evaluates |
| A3 | `oomd-seat-vm` (new VM test, 1 GiB guest, no swap) | a memory hog in a `seat@` instance is not killed by oomd within 90 s, oomd's journal line does not name its cgroup, or an idle sibling `seat@` dies. The test also records the hog's `Result=` |
| A4 | `evidence-unit` | the new kinds accept a `path` field, an off-regex unit or an unknown scope; the ingest over a fixture journal misses rows or reads `MESSAGE`; the fence misses a planted slow point or flags the real series shapes. Mutants: 3×→1.5×, no 1 s floor, and all-parent git history each flip a fixture verdict. `test_engagement.py:65` moves 19 → 22 (a hidden touch) |
| A5 | `helm-unit` | the emitter writes other than one row per cycle from a fixture `/proc` and cgroup tree, or the tile misses a threshold. If Q2 is yes, `test_collect.py:770` splits into zram-ok and partition-fail |
| A6 | `unit` (bats) | only if Q2 is yes: `50-doctor.bats` lacks "zram swap passes" beside the disk-swap failure |
| A7 | operator, after switch | `oomctl` does not list `system-seat.slice`, or the backfill yields fewer than 419 rows |

## 5. Risks

- **oomd kills a seat mid-task.** The driver records `killed`, and the median
  task wall time is 1144 s. The trigger is sustained full pressure (80% for
  30 s), which has not occurred in 30 days. The alternative, a thrash,
  stalls every seat, the broker and the desktop together.
- **The drop-in might not reach instances of an implicit template slice.**
  A3 proves it. If it fails, the fallback is an explicit
  `Slice=system-seat.slice`, which keeps the same path.
- **zram, if chosen, relaxes an invariant-1 probe.** Assertion (b) makes RAM
  residency a build fact first.
- **Benchmark noise from night seats.** The context fields are recorded and
  the verdict stays report-only.
- **Legitimate growth trips the fence.** Checks grow as tests are added,
  which is why the fence only reports.
- **The store grows by about 0.25 MB/day**, all of it into the backup set.
- **`helm-collect`'s journal access is unmeasured.** If its hardened user
  unit cannot read the system journal, the ingest moves to a small sibling
  oneshot on the same timer. It is R1's first measurement.

## 6. Phasing

| phase | task | size | depends on |
|---|---|---|---|
| 1 | F1 `report flow` and the `flow` tile (D5, Q6) | S | — |
| 1 | R1 `unit-resources` kind and ingest, per-seat figures in the seats tile's detail (D2) | S | — |
| 1 | B1 the fence, `report perf` series 1–2, and a `perf` tile listing flagged series (D4) | S | — |
| 2 | P1 `resourcePolicy.nix`, A1, A2 (D1) | S | — |
| 2 | P2 `oomd-seat-vm` (A3) | M | P1 |
| 2 | R2 `pressure-sample`, the emitter, and the tile if Q5 (D3) | S | R1 (shared wiring) |
| 2 | Z1 zram with the probe and tile amendments (only if Q2) | S | P1 |
| 3 | B2 `helm-bench` and the `bench` kind (D4) | M | R2, B1 |

That is seven tasks (zram is out, Q2): five S and two M. **The Helm rule (operator,
2026-09-25): every figure this spec stores or derives is rendered on the Helm by the
task that produces it; a kind with no tile or detail line is not done.**
- **Phase 1** uses data already on disk and needs no switch.
- **Phase 2** is one operator switch.
- Every task that adds a kind lists `test_engagement.py` in its touches.

## 7. Not in this design

- Per-seat limits and CPU or IO weights. WR owns `comfy.slice`.
- oomd on the system or user slices.
- cloud-hypervisor `vm.counters` and KVM stats, until a `microvm@` host unit
  exists.
- sched_ext, KSM, THP and delay accounting.
- A `built` flag on `check` rows. That is a frozen recorder change, owed to
  the Rust port.
- A gate `wall_s` writer.
- Any perf-based integration refusal.
- Change-point analysis.
- Exporting these rows. They are local counts, and the public ledger is a
  separate decision.

## 8. Not measured

- `Result=` after an oomd kill (A3 measures it).
- Whether `helm-collect`'s sandbox can read the system journal. The
  operator's shell can, and every journal fact above was read that way.
- Whether a slice drop-in reaches template instances (A3).
- zram's compression ratio on this workload.
- The error of the ≥ 2 s filter: how many of the 2649 zero rows were
  substitutions and how many were sub-second builds.
- **Operator effort per landing.** `latency_s` is waiting time, so the
  2026-09-23 goal metric stays unmeasured until an effort emitter exists.
- **Time in review.** `gates.wall_s` is populated on 0 of 666 rows.
- `microvm@` rows. No such unit exists on core.

## 9. Operator questions — answered 2026-09-25

1. **oomd on the seat slice** — `kill` (80%, 30 s).
2. **zram on core** — `no`; the option and its invariant-1 assertion still land for the image.
3. **oomd on user slices** — `no` (default), until WR's `comfy.slice` exists.
4. **Detector** — `iqr`.
5. **A `pressure` tile** — `yes`.
6. **Flow metrics on the Helm** — `yes`, now rather than after two weeks: the operator's
   rule that a Helm-linked figure the GUI does not show is waste (D5, the phasing table).
7. **Fence teeth** — `report`; revisit `refuse` after two weeks of rows.
