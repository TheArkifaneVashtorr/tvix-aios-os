# The surface area of control

Class: design principle, adopted. Status: recorded 2026-09-22 on the operator's
word; goal 5 in brief §2 measures it; the router and the retro loop are the first
spec items under it, planned after goal 1 lands.

## The operator's words

"MCP, CLI, testing infrastructure, factory etc. all serve the same purpose which is
to allow you to perform a complex task with low token overhead. I think that nix
shell is the eventual home of all of this and it should allow you to basically
control the operating system which is the factory. In the same sense the interaction
surface between you and I needs to be more limited. Humans are poor communicators so
reducing the surface area to a dashboard that you design would be optimal, using a
JEV-like model as router to know what model I need to talk to based on the complexity
of the prompt could also save tokens. I really like the design of worlds and how it
uses LLMs under the hood, isolates and protects user privacy; imagine more workflows
like this. The reduction of surface area also helps telemetry quite a bit and will
help with improvement loops: every time a dispatch fails you can take a turn to
improve the planning step based on what failed."

## The rule

A capability exists when it is a devShell command with a typed contract that prints
a digest. Everything else — an MCP server, a skill, a workflow script, a check — is a
wrapper around such a command or is not a capability. The token cost of a control
surface is never the call; it is the output the orchestrator has to read. So:

- every command prints a digest by default and a log only on request;
- a command that returns a file path to read is a defect in the command;
- the daemon of the tvix-aios spec (§5, `aiosd`) is the end state: the devShell
  command speaks to its socket, and the daemon is the operating system. The
  factory is not a tool installed on the OS; it is what the OS does.

The house already has the shape where it is cheap (`evidence bundle`, `evidence
tasks brief`, `factory-dispatch --dry-run`, `seat-submit`) and lacks it where it is
expensive (reading run logs, plan files and review files by hand).

## The operator surface

The chat is the most expensive channel: every decision costs a question, a wait and
a reply to parse. The evidence stream `ledger/operator` already records the surface
each decision came through (`chat` | `run-button` | `helm`) and whether the
recommended default was taken. The target is therefore measurable today:

- **goal 5a**: the share of operator decisions taken on the Helm with the
  recommended default preselected;
- **goal 5b**: chat questions per landed task.

The primitive is the one-command hand-off confirmed 2026-09-22 ("now I cannot mess
it up"): every ask is a card with a default and a button. The Helm is the only
dashboard (decision 2026-09-17); this is what it shows.

## The router

The notebook's complexity scorer and confidence cascade (concept inventory A2, B1,
A8) applied to the operator channel: a scorer in front of the chat routes a one-line
ask ("what landed?") to a cheap model reading the evidence store, and a design prompt
to Fable; the router picks the effort, not a session setting. The routing ledger
gains an `operator` role with rungs like every other role. The scorer is calibrated
from the `operator` stream, never hard-coded (A4/B6).

## Worlds as the template

A world is a declared loop — generator, judge, sink — with an LLM inside, privacy by
isolation, output as evidence rows, nothing through chat. Workflows of that shape,
each an `aios.worlds` entry:

- **planning retro**: after every gate rejection or escalation, a run reads the
  rejection and proposes one erratum to the plan skill's drafter prompt or rubric,
  judged before it lands (the 2026-09-07 "redesign from failures" ask, with a
  mechanism);
- **triage**: over the queue and the ledger, producing the morning brief on the Helm;
- **pre-review**: reads a landed branch against its plan section before the Opus gate
  spends anything;
- **research**: the gather step as a world, replacing ad-hoc packet runs;
- the media worlds, unchanged.

## Telemetry

Fewer surfaces means every row in the evidence store has one of a handful of
sources, so attribution stops being a guess (the OpenRouter ledger had 80% of its
spend unattributed on 2026-09-22). Each world's sink is a declared kind; each
operator decision is one row; each router decision is one row. The improvement loop
reads those rows and nothing else.

## What it is not

Not a reason to remove the chat: design conversations and corrections stay here.
Not a new subsystem: the Helm, the routing ledger, the operator stream and the worlds
module exist; this names how they fit.
