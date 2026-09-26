# Reaping factory workspaces and the Nix store — design

**Status:** draft, 2026-09-23. Measured on core at generation 83; store
collection is specified in the periodic-jobs design (§4 here points to it).

## 1. The problem, measured

`~/factory/ws` holds **357 workspaces totalling 13 GB**, one per task key ever
dispatched, each a full `git clone` of this repository. `~/factory/runs` holds
**362 run directories**, and `/var/lib/seat/jobs` **355 job directories at 87
MB**. Nothing reaps any of them. The growth is monotonic and proportional to
task count, which is the one number this project deliberately scales.

At the current rate — 438 landed tasks since the factory began — the store
reaches 13 GB in three weeks of work. Nothing fails yet, and that is the
problem: the first symptom will be a full disk during a wave, at whatever hour
that happens to be.

The workspaces turned out to be the small pile. The same afternoon, the Nix
store held **255.6 GiB referenced by nothing** — twenty times `~/factory/ws`,
larger than `~/comfyui/store`, and thirteen times what pruning 78 of 85 system
generations would free. It is the factory's own exhaust, and
[periodic jobs](2026-09-23-periodic-jobs-design.md) §4 treats it.

## 2. What makes this harder than `rm -rf`

**A workspace is the recovery checkpoint.** The documented relaunch recipe
depends on it: when a seat dies to a provider failure, a credit exhaustion or
a reboot, "the dead seat's diff stays in `~/factory/ws/<run>/<KEY>`" and the
relaunch continues from it under a fresh run name. Reaping a workspace whose
key has not landed destroys the only copy of that work — the branch lives in
the clone, not in the base repository.

So the reaper's safety condition is not age. It is **whether the work is
recoverable from somewhere else**, and the derived task graph already knows:
a key that `tasks.py` reports as `landed` has its commit on `main`, and its
workspace holds nothing that the repository does not.

The same asymmetry applies to the other two stores, and they are not
equivalent:

- **Workspaces (13 GB)** — the bulk, and disposable once landed.
- **Run directories** — small, and they are the *record*: `.result` files,
  review markdown, probe verdicts, `run.meta`. The evidence store ingests
  from them, and `factory-task --prior <run>/<KEY>` reads them to compose a
  fix round. These are not reaped by this design.
- **Job directories (87 MB)** — hold `job.json` and `brief.txt` per seat job.
  Small, but they are the durable statement of intent that
  [the reconciler design](2026-09-23-job-reconciler-design.md) depends on.
  Reaping them is coupled to that design and is out of scope here.

## 3. The design

A `factory-reap` verb, run on a timer, that removes a workspace only when
every one of these holds:

1. **The key is `landed`** according to the derived graph on the live tree —
   not inferred from the branch, not from the run record, and never from a
   file's age alone. The graph is the same authority the dispatcher uses.
2. **The workspace has no commit absent from `main`.** A direct check against
   the base repository, because a landed key can still carry an extra commit
   the integrator did not take. Any such commit makes the workspace ineligible,
   loudly.
3. **The workspace is clean.** Uncommitted changes mean a seat was interrupted
   with work in the tree; that is exactly the state the relaunch recipe
   recovers from.
4. **A grace period has passed** since the run's last activity, so a key that
   landed minutes ago is still there when a gate turns out to need it.
5. **The most recent N runs are kept whole** regardless, so the working set a
   session is actively reasoning about is never reaped underneath it.

Anything failing a condition is skipped and *counted*, never deleted. A
`--dry-run` that prints what would go, and the byte total, is the default
posture for the first weeks.

Each reap appends one row to the evidence store — run, key, bytes reclaimed,
the conditions checked — so the reclaimed total is a measured number rather
than a claim, and so a workspace that vanishes can be accounted for.

## 4. The Nix store

Collection of the store's 255.6 GiB of dead paths lives in
[periodic jobs](2026-09-23-periodic-jobs-design.md) §4, with every other
timer on this host, on the operator's direction that timers be kept in one
place. The one fact this design needs from it: a plain collection never
touches a workspace — workspaces are not store paths — so the two reapers
are independent and neither's safety depends on the other.

## 5. What this does not do

**It does not shrink a clone.** Each workspace being a full clone is the
obvious other lever — `git clone --shared`, or worktrees off one bare
repository — and it would cut the 13 GB by most of its size without deleting
anything. It is deliberately not in this design: `factory-ws` is on the path
of every dispatch, the isolation between workspaces is load-bearing for
parallel seats, and a shared object store introduces a failure mode
(corruption or GC in the parent) that reaches every concurrent seat at once.
That is a separate change with its own risk, and it should be measured
against this one rather than bundled with it.

**It does not reap run directories or job directories** (§2).

**The workspace reaper does not free space on a schedule anyone depends on.**
Its timer is opportunistic — unlike store collection (periodic jobs §4), whose
schedule is load-bearing because the pile it clears grows with every task. If
the disk is genuinely near full, that is an alert, not a reaper's job — and
there is no disk-space alert today, which is worth its own row.

## 6. Acceptance

- A workspace whose key is `landed`, whose branch adds nothing to `main`,
  which is clean, and which is outside the grace window and the keep-N set, is
  removed; the reclaimed bytes are recorded.
- A workspace failing **any** condition survives a reap, and each such skip is
  counted by reason. This is the assertion that matters: the test that proves
  an unlanded, a dirty, and a recently-active workspace all survive is the one
  standing between this and data loss.
- `--dry-run` removes nothing and prints the same accounting.
- Reaping is idempotent: a second run over the same tree reclaims zero bytes
  and reports zero skips it did not report before.
- The relaunch recipe still works for an unlanded key after a reap has run.

Store collection's acceptance — including the generation-28 guard — is in
[periodic jobs](2026-09-23-periodic-jobs-design.md) §6.

## 7. Open question

The grace period and keep-N are policy numbers, not derivable from anything
measured here. Sensible starting values are conservative — a grace period of
days rather than hours, and enough recent runs to cover a working session —
because the cost of keeping a workspace too long is disk that is already
being spent, while the cost of reaping one too early is work that cannot be
recovered.
