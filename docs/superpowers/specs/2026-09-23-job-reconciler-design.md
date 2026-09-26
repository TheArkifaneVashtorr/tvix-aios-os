# The job reconciler — design

**Status:** draft, 2026-09-23. Measured on core at generation 83.

## 1. The problem, measured

A reboot loses every running seat, silently. There is no `Restart=` on the
`seat@` template, nothing starts a job at boot, and nothing tells the operator
that work was in flight when the machine went down — measured 2026-09-23,
when a restart killed the comfy units and the operator learned of it by
noticing a failed generator an hour later. The factory happened to be idle
that time. It will not always be.

What survives a reboot is enough to recover from: `/var/lib/seat/jobs` holds
**355 job directories** (`job.json` at 278 bytes, plus `brief.txt`), and
`~/factory/ws/<run>/<KEY>` holds whatever the seat committed. What does not
survive is anyone's knowledge that the job existed. The recovery is entirely
manual today: notice, diagnose, pick a fresh run name, relaunch by hand.

The goal this serves is a seamless experience, and the number it should move
is **operator actions to recover from an interrupted run** — today three
steps and an unbounded delay, because it waits until someone notices.

## 2. A reconciler, not a watcher

The instinct is a file watcher that reacts when a job dies. That cannot work
for the case that matters: the event is the machine going down, and a watcher
is not running when it happens.

A reconciler instead reads durable state every tick and converges toward it:
jobs declared on one side, units running on the other, start what is missing.
A reboot is then not a special case at all — it is a tick where nothing is
running yet. inotify remains useful as a latency optimisation on top, never as
the mechanism.

This belongs in `aiosd`, whose declared modules already include `schedule.rs`
and `workflow.rs`. It is the daemon's job, arriving before the daemon does.

## 3. The hard part is resume semantics

Detection is cheap. The response is where every real cost sits, and the two
halves of a seat's state do not resume the same way:

- **The conversation cannot be resumed.** Restarting means re-running from the
  brief — real tokens and real wall clock. Measured: seats this morning ran
  1,771 s and 2,599 s; PT3 ran 5,177 s; the record puts glm-5.3 at **$2.70 per
  completed task**. A reconciler that restarts blindly turns one lost run into
  an expensive loop.
- **The branch is the checkpoint.** A killed seat's commits survive in its
  workspace, and the relaunch recipe already exploits this. Resume must mean
  *continue from the branch*, not *start over* — the same mechanism a fix
  round uses.
- **A crash and a deliberate stop are indistinguishable from the exit alone.**
  Without a recorded intent, an operator's Ctrl-C becomes a restart loop.

So the rule is: re-dispatch a job whose unit is gone but whose intent is still
`running`, continuing from the surviving workspace, under a bounded attempt
count, and never for a job whose record says it was stopped.

## 4. The design

**Intent becomes durable.** The job record gains a lifecycle the daemon owns —
declared, running, finished, stopped, failed — written at each transition.
This is what distinguishes a crash from a stop, and it is the one thing
missing today; everything else already persists.

**The loop reconciles.** Every tick: read the job records, ask systemd which
`seat@` units are active, and for each job whose intent is `running` with no
unit, decide. Start it if it has never run; continue it from its workspace if
it has; refuse and mark it failed if it has exhausted its attempts. Jobs whose
intent is terminal are ignored.

**At boot it does the same thing.** No special path, no replay log — the first
tick after boot simply observes zero running units and converges. This is the
entire reason for choosing a reconciler.

**Cost.** The working set is 355 records under 100 KB total, page-cached after
the first tick, plus one D-Bus query for unit states: roughly 5 ms a tick. At
a ten-second interval that is **0.05% of one core**, against `helm-collect`'s
measured 1.06 CPU-seconds per 300-second cycle (~0.35%). About four CPU-hours
a year. **One unnecessary restart costs more than a year of the loop**, which
is the whole argument for conservative policy.

**Visibility.** The reconciler's view — what is running, for how long, what it
has restarted — is what a Helm tile should show, sharing the emitter with the
resource tile in
[the world resource-control design](2026-09-23-world-resource-control-design.md).
Live log tailing is deliberately excluded: `journalctl --user -u 'seat@*' -f`
already does it better than a 300-second dashboard, and a seat log carries the
brief and the model's output verbatim, which is content a status surface
should not hold.

## 5. Prevention beats recovery

A reconciler recovers from an interrupted run. It does not stop the interrupt.
For the case measured — an operator rebooting without remembering work was in
flight — the cheaper instrument is a **shutdown inhibitor** held while a seat
runs, so a reboot warns or waits instead of silently discarding. It is a few
lines on the unit, it needs none of this design, and it should land first.

The two compose: the inhibitor prevents the common case, the reconciler
handles the ones it cannot (a crash, a power loss, an OOM kill).

## 6. Acceptance

- A job whose unit is killed while its intent is `running` is re-dispatched,
  continuing from its workspace, and the commits already in that workspace are
  not redone.
- A job stopped deliberately is **not** restarted — asserted directly, because
  this is the failure that would make the feature worse than nothing.
- A reboot with jobs in flight results in those jobs running again, with no
  operator action, and the recovery is recorded.
- Attempts are capped: a job that fails repeatedly ends `failed`, never loops.
- With no jobs in flight, the loop's measured CPU stays within the budget in
  §4 — a number, in a test, not an assurance.

## 7. Not in this design

Resuming a model conversation (not possible). Reaping job directories — that
is coupled to this lifecycle and belongs with
[workspace reaping](2026-09-23-workspace-reaping-design.md) once intent is
durable. Any restart policy for the comfy world units, whose interruptions are
a different problem with a documented deadlock of their own. Live log
streaming (§4).
