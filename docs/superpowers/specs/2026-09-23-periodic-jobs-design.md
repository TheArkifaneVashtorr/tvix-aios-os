# Periodic jobs: one home for every timer — design

**Status:** draft, 2026-09-23. Measured on core at generation 85. Operator's
direction the same day: "keep them all in the same place."

## 1. The problem, measured

Eight timers run, or are about to run, on this host, declared across five
modules, and no two of them share a rule about when to run, what to record, or
what to do if a seat is working. Each was written for its own subsystem and is
correct on its own terms; the host is running eight independent sets of
assumptions.

| timer | scope | schedule | declared at | Helm tile | records to the store |
|---|---|---|---|---|---|
| `helm-collect` | user | boot +2 min, every 300 s | `nixosModules/helm.nix:769-777` | yes | `helm-status` |
| `helm-flake-check` | user | 03:00 daily, Persistent | `nixosModules/helm.nix:806-814` | yes | `checks` |
| `restic-backups-core-local` | system | daily 00:00, Persistent | `nixosModules/protonBackup.nix:86-104` | yes | **nothing** |
| `proton-drive-push` | user | 00:30 daily, Persistent | `nixosModules/protonBackup.nix:133-141` | yes | **nothing** |
| `usage-ingest` | system | hourly, Persistent | `nixosModules/usageIngest.nix:55-62` | **no** | `ledger/openrouter-usage` |
| `comfy-upstream-probe` | user | Sun 04:00, Persistent | `media/nixosModules/comfyui-worlds.nix:486-493` | **no** | `checks`; its `proposals` row is **refused every run** |
| `otel-ingest` (SP9, not landed) | system | hourly, Persistent | `nixosModules/otelIngest.nix` on `task/SP9` | **no** | `ledger/otel-claude` |
| `nix-gc` (proposed, §4) | system | before 03:00 | — | — | — |

The measured gaps this spec exists to close:

- **Half the timers are invisible to Helm.** The "timers armed" tile audits a
  named list, deliberately not every timer (`nixosModules/helm.nix:486-488`),
  and four of the eight are not on it. A timer that silently stops firing is
  exactly what the tile is for.
- **Two run blind and one fails silently.** Restic and the Proton Drive push
  write nothing to the evidence store; their state is visible only through
  Helm's live `restic snapshots` read. The upstream probe calls
  `evidence record proposals` with `"kind": "proposal"`, and `pkgs/evidence/streams.py`
  declares no such kind (`:945-964` → `undeclared kind 'proposal'`), so every
  weekly proposal has been refused since the probe landed. Its `checks` row
  does land, which is why nothing looked wrong.
- **Same-minute collision.** `usage-ingest` and NixOS's own `logrotate.timer`
  are both `OnCalendar=hourly` and fire in the same second; SP9 as written adds
  a third.
- **Nothing knows a seat is working.** `seat@` is a system-scope unit
  (`nixosModules/seatLane.nix:332`) and no timer checks for one before starting.
  For most timers that is harmless; for collection it evicts a running seat's
  cache mid-task.
- **Only one ordering is declared.** Restic starts the Proton Drive push from
  its `ExecStopPost` (`protonBackup.nix:110-115`); every other ordering is
  coincidence of clock times.

## 2. The shared rules

Every periodic job on this host follows all of these. A new timer that cannot
say how it satisfies each one is not ready to land.

1. **Declared in Nix.** A timer this host depends on lives in a module, not
   in `~/.config/systemd/user/`.
2. **Visible.** It is named in Helm's timers-armed list, in the list matching
   its scope. A drift check fails the build when a declared timer is missing
   from the list, so rule 2 cannot quietly lapse the way it already has.
3. **Recorded.** Each run appends one evidence row: what it did, how much, and
   whether it succeeded. Restic records a snapshot id and bytes added; the push
   records bytes sent; ingests already record rows; collection records the
   store's size before and after. A run that cannot record is a failed run.
4. **Off the hour.** No two timers this repository declares share a minute,
   and none lands on `:00`, which belongs to NixOS's own hourly jobs. Ingests
   stagger: `usage-ingest` at `:05`, `otel-ingest` at `:10`.
5. **Ordered around the nightly check where it matters.** The 03:00
   `helm-flake-check` rebuilds the full check set and warms the store for the
   day's seats. Anything that evicts the store runs before it; anything that
   reads what it builds runs after it.
6. **Aware of work in flight.** A heavy job — collection, and any future job
   that evicts, rebuilds or saturates a resource a seat uses — does not start
   while a `seat@` unit is active; it retries at its next tick. "A seat is
   active" has one definition, shared with the shutdown inhibitor (IS26) and
   the [job reconciler](2026-09-23-job-reconciler-design.md), not three.
7. **Persistence decided, not defaulted.** `Persistent=true` for jobs whose
   point is not to miss a period (backups, ingests, the nightly check); `false`
   for jobs where a missed run is simply skipped and catching up at boot would
   only add load (collection).

## 3. What changes, per timer

- **`usage-ingest`** — add to Helm's system list; move to `:05`.
- **`otel-ingest` (SP9)** — lands as it stands, per the operator's decision,
  then conforms: Helm's system list, `:10`. SP9's glob over rotated collector
  files is correct and stays — the collector rotates at 64 MB and the directory
  is not backed up, so a fixed-path ingest would lose a rotated window for good.
- **`comfy-upstream-probe`** — add to Helm's user list; declare a `proposal`
  kind in `streams.py` so its proposal rows land. The kind's shape is defined by
  [upstream probes](2026-09-23-upstream-probes-design.md), which is the
  consumer; this spec only requires that the row stop being refused.
- **`restic-backups-core-local`, `proton-drive-push`** — record a row per run
  (rule 3).
- **`nix-gc`** — new, §4.
- **`helm-collect`, `helm-flake-check`** — already conform, apart from rule 3
  for `helm-collect`, which records to `helm-status` only on a change or an
  hourly heartbeat; that is a deliberate design and stays.

## 4. Garbage collection

Moved here from the [workspace reaping design](2026-09-23-workspace-reaping-design.md),
which now points to this section.

**Measured 2026-09-23.** `nix-store --gc --print-dead` listed **164,260** paths
referenced by nothing, totalling **255.6 GiB** — one `du` over the whole list;
`auto-optimise-store = false`, so there is no hard-link dedup and the figure is
real disk. Nothing in the repository configured collection. The first run, by
hand that afternoon, deleted `run-nixos-vm`, `closure-info` and whole
`nixos-system-*` trees left by VM checks. It is the factory's exhaust: every
seat verify, every integrate and the nightly check build outputs that die with
their result links, and the CUDA and torch media closures make each expensive.
The pile grows at the rate the factory works.

**The danger lives entirely in the flags.** A plain `nix-collect-garbage` keeps
every generation pinned by its profile link — including generation 28, tagged
`live-gen28-2026-09-03`, which must never be collected. Two common spellings
destroy it: `nix-collect-garbage -d`, and the `nix.gc.options =
"--delete-older-than <N>d"` that nearly every NixOS example uses. So the
mechanism is `nix.gc.automatic` with `nix.gc.options` empty or a `--max-freed`
ceiling only, and **a negative check fails the build if the options ever
contain `-d`, `--delete-old` or `--delete-older-than`**. That check is the
whole safety argument.

**Schedule.** Before the 03:00 check — `02:30` — so the nightly run re-warms the
store for the day's seats rather than a later collection discarding what it
just built (rule 5). Held off while a seat is active (rule 6). `Persistent=false`
(rule 7): a skipped night costs a day of growth, while a boot-time catch-up would
evict the cache just when the first seats of the day need it.

**Not here:** `result` links in archived projects (`~/flakes/codex/result`,
`~/flakes/chatgpt-desktop/result`) are live roots, and removing them is an
operator decision about those projects. `auto-optimise-store` could reclaim more
from the *live* set but costs CPU on every build and needs its own measurement.

## 5. Out of scope, named

- **Sixteen `political-focus` timers** run as hand-written user units in
  `~/.config/systemd/user/`, from a separate project outside this repository.
  They break rule 1 on this host, but they are not this repository's to
  declare; the operator decides whether that project should be.
- **NixOS's own default timers** (`logrotate`, `fstrim`, `systemd-tmpfiles-clean`)
  stay as they are; rule 4 moves ours off their minute rather than moving them.

## 6. Acceptance

- **The drift check:** a declared timer absent from Helm's timers-armed list
  fails the build; asserted by declaring one and showing the refusal.
- **The generation-28 guard:** `nix.gc.options` containing `-d`, `--delete-old`
  or `--delete-older-than` fails the build; each spelling asserted.
- No two timers this repository declares share an `OnCalendar` minute, and none
  is on `:00`.
- Every timer's run appends one evidence row, and an upstream-probe run's
  proposal row lands rather than being refused.
- Collection does not start while a `seat@` unit is active, and every system
  generation's profile link still resolves after it runs.
