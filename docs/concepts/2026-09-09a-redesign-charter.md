# Concept 2026-09-09a — the redesign charter (the program's fixed frame; never fed to `plan.js`)

**Class:** program charter (decision 62a: a charter under `docs/concepts`, plus
one spec of size M or smaller per subsystem; the charter itself is never a
`plan.js` input).

**Status:** approved 2026-09-09 by the operator ("Approved. Impress me."),
after all 80 loose ends were answered through the dialog. The answers are the
decisions of record: `docs/decisions/2026-09-09-redesign-answers.md`. The
measured state the charter rests on: `docs/research-2026-09-09-meta-planning-packet.md`.
The questions and their bounds: `docs/research-2026-09-09-redesign-loose-ends.md`.

**Origin:** the operator's asks of 2026-09-09 (restated as A–L in the
loose-ends document §0): subsystems like a software company; single-pass
custom agents; Helm as the DeepSeek harness's backend; a saved patch system;
graph-based decision-tree workflows; batched Fable plans, incremental; a bug
workflow with escalating single-shot rungs; Helm engagement with a Caddy-fronted
ComfyUI feed and a local prompt mutator; every flake collapsed; every rule
reconsidered; a plan that batch-plans the plans, run via the seat.

## 1. The program in one paragraph

Eight declared subsystems, each a directory with its own checks and a manifest
the build asserts (answers 1, 2, 4). Each subsystem gets one M-size spec
written by Fable and one plan drafted by Fable through `plan.js` (answers 64,
65), judged blind as today. One typed program plan carries the closeout keys,
the program-level code, the spec-writing keys and the `plan.js` keys; the seat
dispatches it (answers 61, 69), in staggered increments three subsystems wide
(answers 66, 67), each closed by one composed acceptance drill the operator
runs (answer 70). Fable is the re-planner and the escalation terminus; every
escalation is a design failure on the record (answers 28, 73). Model calls for
Fable go through the provider's batch API from a repo-side graph runner
(answers 22, 30). No budget ceiling until the ingest and OTel tasks land and one
increment has been measured (answer 71).

## 2. The eight subsystems

Granularity per answer 2 (medium, eight). "Owns today" is measured from the
tree; the owner is a routing area (answer 3), not a standing agent. Prefixes
are reserved here before any draft (answer 63); none of them appears in the
derived graph today (`HH SP SD W FIX UI BUG OL CX SB SH PB PW E A R N H OG` are
the prefixes in use).

| Subsystem | Owns today | Owner area, gate | Prefix | First spec answers |
|---|---|---|---|---|
| Isolation | baskets, the egress broker, lanes, the classification assertions, the seat unit hardening (`nixosModules/seatLane.nix`), the guard | `isolation`, Opus gate always (it carries the invariants) | `IS` | 11, 20, 44 (the OAuth/router spike), 57, 72 |
| Platform | `flake.nix`, `hosts/core`, pins, the patch system, the vendored upstreams (dsh, claude-code, ComfyUI), the absorption of the siblings, switches | `platform`, Opus gate | `PL` | 35–48 |
| Helm | `pkgs/helm`, `nixosModules/helm.nix`, `pkgs/helm-home`, the status page, the profile switch | `helm`, Opus gate for the API, Sonnet for the page | `HM` | 8–20 |
| Seat/Harness | `pkgs/seat`, `pkgs/dsh`, `pkgs/dsh-openrouter`, the drive and job modes, the harness payload (AGENTS.md, skills), the hooks and memory the seat gets | `seat`, Opus gate | `SA` | 13, 36, 57–60 |
| Factory | `tools/factory/seat/*`, `tools/factory/route.py`, the workflow scripts, the graph runner, the agent registry, `routing.toml` | `factory`, Opus gate | `FA` | 21–34 |
| Evidence | `pkgs/evidence/*`, `docs/ledger/*.toml`, the store under `/var/lib/evidence`, the ingests, the derived board block, the bug ledger, the engagement stream | `evidence`, Sonnet gate | `EV` | 6, 7, 18, 29, 46, 56 |
| Generation | `~/flakes/media` (ComfyUI worlds, the feed, Caddy sites, the lab repo), the prompt mutator | `generation`, Sonnet gate | `GN` | 14–17 |
| Knowledge | `docs/brief.md`, the board, handoffs, runbooks, concepts, the rules source that generates CLAUDE.md and AGENTS.md, the ritual | `knowledge`, Sonnet gate | `KN` | 49–55, 59, 60 |

Program-level keys (the closeout, the charter's own code, the manifest, the
spec and `plan.js` keys) use the prefix `PR`.

## 3. Retire and keep

- Retired: OpenClaw (answer 5, option d: Hermes stays as the named partner,
  OpenClaw was its fallback). `dark-factory.js` to the archive once the graph
  runner drives the bash tools (answer 33). The hand-written START HERE
  narrative, the log as a hand-written surface, and the Now paragraph (answers
  50, 51). The GTK Helm app, HH5–HH10 (answers 9, 10). The `~/flakes` sibling
  repos as working repos once absorbed (answers 35, 44, 48).
- Kept: Hermes as a named research partner under the data-sharing decision of
  2026-09-09 (case by case, never to enemies). Phase 5 local weights as a named
  Generation concern, no work scheduled until the mutator's model phase
  (answer 17). The seat's three modes and the two specialisations (answer 45).
  The base clone and its one lock (answer 42). The documented nixpkgs pair
  (answer 43).
- Open: node2 and node3 (brief §6, never built) are not covered by answer 5's
  option; the Platform spec asks the operator in its own questions section.

## 4. The invariants are under review, not suspended

Answer 49 reopens brief §3 with every other rule; answer 55 re-ratifies §3 after
that review and marks §4, §7 and §9 superseded. Until the Knowledge
subsystem's rules audit lands, every one of the six §3 invariants holds
verbatim and every plan in this program is written against it: encrypted
baskets, the broker as the only egress, no operator key in a seat, environments
reproducible from the lock files, no imperative state, privacy over everything.
The audit's output (answers 49, 54, 59) is one dated ruleset file with a
verdict per rule, a check per load-bearing rule, and CLAUDE.md and AGENTS.md
generated from it; a rule with no check and no measurement is deleted, not
date-stamped.

## 5. Mechanics folded from the answers

- **One program plan, typed by Fable, dispatched by the seat** (61, 69). Keys
  "write spec S_i" are docs tasks Fable performs in Claude Code; keys "run
  `plan.js` on S_i" resolve to a claude rung the seat prints and Claude Code
  runs. The seat's own hooks, permission preset and memory store (57–59) are
  the Seat/Harness subsystem's first spec, so the batch is driven at first by
  the seat as it is today.
- **Increments** (31, 66, 67): staggered, three subsystems wide; increment i
  plans subsystem i+1's trio while dispatching increment i's waves; a plan is
  drafted only against the landed tree; keys are namespaced so the duplicate-key
  gate cannot fire.
- **Rejection and escalation** (28, 73): a rejected plan or task drops out of
  its increment and re-enters the next as a Fable re-plan, batched like every
  other Fable call. A ladder that exhausts hands the operator a plain-language
  description and a ready launch command; the escalation is logged as a design
  failure and feeds the rules audit and the graph's failure catalogue.
- **Batching** (30) — **corrected 2026-09-10 on the operator's word.** The
  Fable draft, judge and re-plan calls move to the repo-side runner (22) and go
  through **the existing OpenRouter lane's batch endpoint**, not through Claude
  Code and not through a second vendor. OpenRouter documents an asynchronous
  batch endpoint billed at 50 % of standard per-token pricing and passes
  provider pricing through without a markup on inference, so a batched Fable
  call there costs the same as Anthropic's own Message Batches while reusing
  the broker instance, the injected key, the policy and the usage ingest that
  already exist (`egress-broker-openrouter.service`; `host = "openrouter.ai"`,
  `nixosModules/seatLane.nix:33`). **OpenRouter only** (the operator, 2026-09-10,
  correcting a dialog answer of the same day): an Anthropic lane is excluded
  outright — a second broker instance, a second key and a second ingest for the
  same 50 % buys nothing — and Claude Code is not a fallback for any automated
  call in this program. One measurement gates the build, owed before the runner
  replaces `plan.js`'s inline calls: whether the lane's provider serves a
  `claude-fable` id, and at what price (answerable only from inside the netns,
  so it is a task step). If it does, Fable drafts, batched, as decisions 64a and
  65a say. If it does not, **the drafter is the best model the lane does serve**
  and those two decisions are amended to name it — the drafter changes, the lane
  never does. Batching changes the lane, never the model: at
  pass-through pricing a batched Fable call is still about ten times a
  `deepseek-v4-pro` seat call (`docs/ledger/claude-prices.csv`,
  `docs/ledger/openrouter-prices.csv`), which is decision 64a's price and the
  operator's to revisit, not this charter's.
- **Verification the runner does itself** (25, 26, 32): mutants and checks are
  re-run by the runner, the agent's claim is never a signal; the node declares
  the rung; the next rung receives a machine-readable artifact, never a retyped
  section.
- **The record** (6, 7, 29, 50, 51, 56): an `area` on every derived row; a
  refusal for undeclared cross-area touches; a typed bug ledger; a generated
  status page as the front door; the handoff as the only prose; an `integrated`
  state with a refusal for approved-but-unintegrated keys.
- **Acceptance and budget** (70, 71, 72): one composed drill per increment,
  assembled from each plan's `## Operator` section; no ceiling until the ingest
  and OTel tasks land and one increment is measured; `seat-submit` refuses a
  launch above a configured running-unit count.

## 6. The increments

Dependencies decide the order: the patch system and the Nix-built harness
payload come before any harness or Helm change can be deployed; the graph
runner and agent registry come before the bug workflow and the batch API; the
rules audit comes before the generated CLAUDE.md and AGENTS.md; the manifest
comes before the import assertion.

**Increment 0 — closeout (now, answers 68, 74–80).** Mechanical: UI1
fast-forwarded, SD11b and SD11c integrated, the broker-secret row closed on one
command's evidence, the PW1 keys closed with rows, the usage backfill run.
Typed: the usage-ingest timer plus backfill (`EV`), the W6 fix round in the
media plan, HH1's fix round then HH2–HH4 from the helm-home-1 plan (answers 9,
78). Acceptance: the derived brief shows no legacy-open row, no approved-not-
integrated key, and the store's dollar line covers the whole broker log.

**Increment 1 — the frame.** The subsystem manifest and its assertion
(`PR`, code, the first code increment that lands without a switch); the rules
audit (`KN`, docs then code); the reserved namespace (this charter and the
program plan's Global Constraints); the routing `area` column and the runner's
rung declaration (`FA`); the `integrated` state and refusal, the bug ledger and
the patches ledger validator (`EV`); the unit cap in `seat-submit` (`IS`); the
OAuth/Proton Pass/router spike (`IS`, docs, privacy-screened). Specs written
for the trio of increment 2.

**Increment 2 — Platform, Seat/Harness, Factory.** The patch series and
ledger, the Nix-built harness payload, the dsh-harness absorption as the first
sibling (`PL`); the drive launch at `danger-full-access`, the three hooks, the
off-tree memory store, N seats with allocated ports (`SA`); the graph runner,
the agent registry with generated shims, the bash executor under the runner,
the bug workflow's rungs and re-resolver node, the batch-API draft node
measured against `plan.js` (`FA`). Specs written for the trio of increment 3.

**Increment 3 — Helm, Evidence, Generation.** Helm's state-and-action API on a
second port, web-first, seat lifecycle writes only, the engagement stream, the
patch queue view (`HM`); the `area` field everywhere, the generated status page,
the engagement store and its counts-only data class, the ingest under a timer
(`EV`); comfy-worlds sub-projects 2 and 3, the on-demand units and Caddy on
core, the rules mutator, media absorbed (`GN`). Specs written for the pair of
increment 4.

**Increment 4 — Isolation, Knowledge, and the remaining absorptions.** LAN
access with per-site auth and the amended brief §10 and loopback assertion,
the private-overlay phase typed but not built, the OAuth/router outcome, the
re-ratified invariants (`IS`); the generated CLAUDE.md and AGENTS.md from the
one rules source, the handoff-only narrative, the renumbered phases (`KN`);
gaming, nixos-skill, codex, openai-lab and chatgpt-work absorbed by subtree
merge with prefixed live keys (`PL`).

Each increment ends with the operator's composed drill and, where a switch is
in it, the operator's switch. Nothing in an increment is dispatched before the
previous increment's drill has passed, except the next trio's spec writing,
which is docs work and runs during the previous increment's waves.

## 7. The operator's acts

The operator switches (never an agent), signs each increment's drill with
"test passed", sets the budget ceiling when the ingest and OTel tasks make one
measurable, answers each spec's own questions section, and takes the
escalations that exhaust a ladder (each arriving as a plain-language paragraph
plus a launch command). Everything else the seat drives on its own judgment
under the driving-authority decision of 2026-09-09, and Fable plans.

## 8. Open items the charter carries forward

1. node2 and node3 (answer 5 leaves them undecided): the Platform spec asks.
2. The engagement stream's data class (answer 18): counts only, never content;
   the Evidence spec declares it before the stream exists.
3. The OAuth keys in Proton Pass with a redirect through the router (answer
   44): a docs spike in increment 1, screened against "would this help an
   adversary" before any test runs; nothing is stored or redirected until the
   operator reads the spike.
4. The batch lane (answer 30, amended to **OpenRouter only** on 2026-09-10),
   two measurements owed before the runner replaces inline calls, both in
   increment 2's Factory work: does the OpenRouter lane serve a `claude-fable`
   id and at what price, and what is the batch endpoint's shape and turnaround
   against the staggered cadence. `plan.js` stays the drafter until both are
   answered. No Anthropic lane, and no Claude Code fallback for an automated
   call; if the lane serves no Fable id the drafter becomes the best model it
   does serve.
5. The dsh upstream pin policy under the hard-fail rule (answer 47): each bump
   is a task whose acceptance is a re-port of every patch; the Platform spec
   sets the cadence.
6. The ceiling (answer 71): set by the operator after one measured increment.

## 9. Sources

`docs/decisions/2026-09-09-redesign-answers.md` (the 80 answers);
`docs/research-2026-09-09-redesign-loose-ends.md` (the questions, bounds and
cites); `docs/research-2026-09-09-meta-planning-packet.md` (the measured
state); `docs/decisions/2026-09-09-seat-driving-authority.md` (who drives, who
switches, the data-sharing stance); `docs/brief.md` §3 (the invariants under
review).
