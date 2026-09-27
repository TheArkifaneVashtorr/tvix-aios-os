# Redesign loose ends — the operator's answers (2026-09-09)

Decided by the operator on 2026-09-09, in-session, through the multiple-choice
dialog, one answer per item of
`docs/research-2026-09-09-redesign-loose-ends.md`. Recorded here so a reset
does not lose them; each answer is the decision the program plan cites. Where
the operator typed their own words, they are quoted verbatim. Eleven answers
depart from the document's recommendation; §2 lists them.

## 1. The answers

| # | Topic | Answer |
|---|---|---|
| 1 | What a subsystem is | a — a declared unit: one directory, one flake-output group, one declaration, its own checks, a build-time assertion |
| 2 | Granularity | b — medium, 8: Isolation, Platform, Helm, Seat/Harness, Factory, Evidence, Generation, Knowledge |
| 3 | What an owner is | a — a declaration plus an `area` column in `routing.toml`; no agent outlives a call |
| 4 | Boundary enforcement | a — split `flake.nix` per-subsystem checks, plus an import assertion (split first, assertion its own increment) |
| 5 | What the redesign retires | **d — keep Hermes, retire OpenClaw as its fallback** (brief §9.3's framing); node2/node3 not covered by this answer |
| 6 | Record per subsystem | a — an `area` field in the derived graph, claims and tasks; one derived section per subsystem in the single board page |
| 7 | Cross-subsystem tasks | a — refuse at dispatch unless the task declares both areas (`areas:` field) |
| 8 | "Helm as backend" | a — Helm owns the state and action API a patched dsh web UI calls; dsh keeps the chat surface; seat units stay in the seat subsystem |
| 9 | helm-home-1 | b — land wave 1 (HH1 fix, HH2–HH4), then supersede HH5–HH10 |
| 10 | Helm surface | a — web-first; D-H1 reversed; the GTK work dropped |
| 11 | Guard vs Helm | a — a second port with no switch route, allowed to the seat; 7700, its token and `/var/lib/helm` stay refused; R8 kept |
| 12 | Backend scope | c — reads of all six domains plus seat start, stop, attach; spend and switches stay out |
| 13 | Seats | b — N seats with backend-allocated ports and a session list in Helm |
| 14 | "caddy" | c — both: Caddy fronts the worlds as designed; the swipe view is the feed component Helm reaches |
| 15 | The feed | a — plan comfy-worlds sub-projects 2 and 3 as specified, W6's fix round first; Helm links or embeds the feed |
| 16 | Generator on core | b — the worlds' on-demand user units plus host-level Caddy wired into `core`, no specialisation |
| 17 | Prompt mutator | c — rules now; the local model as its own phase once a local inference stack lands |
| 18 | "Keeping the user interested" | **b — a local-only engagement stream in the evidence store** (opens, dwell seconds, feed likes per day; counts, never content) |
| 19 | Cowork | a — UX ideas only (task list as home, background work, artifacts, sessions that outlive the window); tier A stays parked |
| 20 | "Accessible anywhere" | b — LAN now (Caddy, internal CA, a password or WebAuthn per site); a declared private overlay as its own later gated phase; brief §10 and the loopback assertion amended in the operator's words |
| 21 | "Single pass" binds | **c — the driving session's inbox only**: no agent-to-agent messaging or self-nudges; subagent output arrives as an artifact the next node reads |
| 22 | Graph engine | a — a repo-side runner reads the declarative graph and calls `claude -p` or `dsh headless` per node |
| 23 | Agent definition | b — one pinned registry (role → model, effort, tools, schema, prompt file); `.md` shims generated and drift-checked |
| 24 | Workflow form | a — a declarative graph file per workflow (agent, tool, gate, refusal nodes; conditioned edges with attempt budgets), one runner, a build-time soundness check |
| 25 | Mechanical verification | b — the runner re-runs the named mutants and the named checks; the agent's own claim is never a signal |
| 26 | Rung | a — the graph node declares the rung; key suffixes stop being routing; a check refuses a contradicting suffix |
| 27 | Bug rung 1 | c — Flash first, with a mechanical citation-and-command re-resolver node before any paid gate |
| 28 | End of the ladder | **operator's words: "Escalate to me describing it in simple terms and a ready made command to launch it to fable. This allows it to be included into a batch for fable."** |
| 29 | Bug intake | a — a typed bug ledger (id, symptom, repro command, status, closing check) derived into the board's queue block |
| 30 | "Batched Fable plans" | **b — the provider's batch API for the model calls themselves** |
| 31 | Incremental planning | a — one plan node per increment; re-plan the next against the landed tree; keys namespaced per subsystem |
| 32 | Escalation payload | a — a machine-readable artifact from the prior node (claims with commands, the failing repro, the errata), passed by the runner |
| 33 | Executor | a — the seat's bash tools only, driven by the graph runner; `dark-factory.js` archived |
| 34 | Who writes graphs | a — the operator: the workflows directory and the agent registry join the guard's protected paths |
| 35 | "A single flake" | b — one repo, siblings absorbed in waves, one sibling per task, each with its own build gate and switch |
| 36 | Harness payload | a — AGENTS.md and the skills become part of the `dsh-openrouter` package in `/nix/store` |
| 37 | Patch unit | a — a numbered patch series under `patches/<pkg>/` applied in `postPatch`, a manifest, an apply check |
| 38 | Patch scope | b — every vendored upstream (dsh, claude-code, ComfyUI) |
| 39 | "Deployable" | b — build-time only, plus a Helm view listing the patches the next switch carries and the generation each landed in |
| 40 | Claude/dsh separation | a — code collapses; memory dirs and backup rows stay separate per subsystem |
| 41 | Task keys at absorption | a — live keys get a subsystem prefix; landed keys frozen as history |
| 42 | Base clone | a — unchanged: one clone, one refresh lock |
| 43 | nixpkgs pins | b — keep `nixpkgs` plus `nixpkgs-host`; absorbed subsystems move onto `nixpkgs-host`; llm-agents stays on its own |
| 44 | The parked labs | **operator's words: "Collapse it all into the system. We should test if we can add the oauth keys to the proton pass and do a redirect so everything can go to the router."** — all seven siblings absorbed |
| 45 | "Modes" | **d — neither**: "mode" means the flake variants, covered by item 35; the seat's three modes and the specialisations both stay |
| 46 | Patch provenance | a — `docs/ledger/patches.toml`, validated by a check that also proves every patch applies |
| 47 | Failed patch at a bump | a — the build fails hard; the bump is a task whose acceptance is a re-port of every patch |
| 48 | Sibling history | a — a subtree-style merge per sibling; every cited hash stays reachable |
| 49 | "Every rule reconsidered" | **d — full reopening, brief §3's invariants included** |
| 50 | The board's front door | a — a generated status page written whole by `evidence`; the START HERE narrative deleted, its prose moved to the log |
| 51 | Narrative | a — the per-session handoff is the only hand-written prose; the board and log are generated |
| 52 | The trailer | a — `policies.md` wins; AGENTS.md's commit section is generated from it; `factory-review` reads that one file |
| 53 | Plan-file rule | a — keep the denial and add `plan-append` / `plan-withdraw` verbs the workflow calls |
| 54 | Failed rules | a — every load-bearing rule gets a check; a rule with no check and no measurement is deleted at the audit |
| 55 | The brief | a — §3 re-ratified as the invariant set after the reopening of item 49; §4, §7, §9 superseded in place; phases renumbered 1..N; the "test passed" gate kept verbatim |
| 56 | "Landed" | a — an `integrated` state plus a refusal: approved and neither landed nor row-carrying after the wave closes fails the board check |
| 57 | Seat permission mode | a — the drive launch sets `danger-full-access`; kernel confinement plus the house guard remain the boundary; job seats keep the default |
| 58 | Seat ritual | a — all three hooks (SessionStart, PreCompact, Stop) running the same scripts, in the harness rework |
| 59 | Rules and seat memory | a — one rules source generates CLAUDE.md and AGENTS.md (drift fails lint); the seat's memory is a machine-local store under the evidence store |
| 60 | Ritual scope | a — the driver or orchestrator session only; a single-pass agent's close-out is its artifact |
| 61 | Plan-of-plans | a — one typed program plan whose keys are "write spec S_i" and "run plan.js on S_i"; plan.js keys resolve to a claude rung the seat prints |
| 62 | Spec size | a — a program charter never fed to plan.js, plus one M-or-smaller spec per subsystem |
| 63 | Key namespace | a — two-letter subsystem prefixes reserved in the program plan's Global Constraints before any draft |
| 64 | Plan drafter | a — Fable in plan.js for every subsystem plan |
| 65 | Spec drafter | **a — Fable writes each spec**, as CLAUDE.md says; the authorship rule stands |
| 66 | One increment | c — staggered: increment i plans subsystem i+1 while dispatching subsystem i's waves |
| 67 | Increment width | b — 3 subsystems |
| 68 | Closeout | c — split: UI1, SD11b/c, a W6 fix round and the broker-secret row closed now; helm-home-1 folded into the Helm plan; the comparison keys retired; the ingest timer plus backfill as task one |
| 69 | Seat drives the batch | a — yes, the whole batch; Claude Code is entered only for the plan.js runs the seat prints |
| 70 | Acceptance | b — one composed drill per increment, assembled from each subsystem's `## Operator` section |
| 71 | Budget ceiling | **b — no ceiling yet**: land the ingest and the OTel tasks, measure an increment, then set one |
| 72 | Concurrency cap | a — `seat-submit` refuses a launch above a configured running-unit count |
| 73 | Rejection mid-increment | **operator's words: "The replan should be Fable as well just like every batch. If something is being escalated it should considered a design failure."** |
| 74 | First tasks | a — closeout and ingest, then the charter, then the reserved namespace, then the subsystem manifest and assertion |
| 75 | UI1 | a — fast-forward `integ/ui1` after re-running its checks; the board's log line corrected in the same commit |
| 76 | SD11b / SD11c | a — integrate both; fall back to a status row if the diffs no longer apply |
| 77 | W6 | a — type a W6 fix round for the two standing findings, after item 52 settles the trailer rule |
| 78 | HH1–HH4 | a — fix HH1 first (its fix round writes the missing failing test), then HH2–HH4 as one wave |
| 79 | PW1 keys | a — close each with a status row citing the review file |
| 80 | broker-secret-ownership | a — one command confirms the secret's ownership on the live host, then the row is closed with that evidence |

## 2. Where the operator departed from the recommendation

- **5** Hermes stays (OpenClaw retired). node2/node3 are unaddressed by the chosen option: an open item for the charter.
- **18** "Interesting" is measured by a local-only engagement stream, not a property checklist. A counts-only data class (never content) must be declared before the stream exists.
- **21** "Single pass" binds the driving inbox, not every agent call: workflow scripts may still loop (gap rounds, revise rounds) as long as no agent messages another and no session nudges itself.
- **28 and 73** Fable is both the escalation terminus and the re-planner. A ladder that exhausts hands the operator a plain-language description plus a ready-made launch command, so escalations can be batched to Fable. Every escalation is recorded as a design failure and feeds the rules audit and the graph's failure catalogue.
- **30** "Batched" means the provider's batch API. The Fable draft, judge and re-plan calls move to the repo-side runner (item 22) and go through the Anthropic Message Batches API; the batch latency against the staggered increment (item 66) is a measurement the charter must schedule.
- **44** All seven siblings are absorbed, the labs included. New spike: can the OAuth keys (the Codex and ChatGPT sign-ins) live in Proton Pass, with a redirect so every provider call goes through the router. Privacy screen applies before anything is tested.
- **45** No seat-mode or specialisation collapse; "mode" meant the flake variants only.
- **49** The rules audit reopens brief §3 as well; item 55's re-ratification happens after that review, not instead of it.
- **65** Fable writes the subsystem specs; CLAUDE.md's authorship rule stands.
- **71** No budget ceiling until the ingest and OTel tasks land and one increment has been measured.

## 3. What the answers oblige next

1. The closeout tasks (items 68, 74–80) are the program's first wave, typed before any charter.
2. The charter (item 62) names the eight subsystems (item 2), their owners (item 3), the reserved key prefixes (item 63), the retire list (item 5, with node2/node3 decided), the rules-audit task (items 49, 54, 55), and the OAuth/Proton Pass/router spike (item 44).
3. The program plan (item 61) is typed by Fable and dispatched by the seat (item 69) in staggered 3-wide increments (items 66, 67) with one composed drill each (item 70) and no ceiling yet (item 71).

## 4. Amendment — OpenRouter only (2026-09-10)

Decided by the operator on 2026-09-10, in two messages. The first corrected the
program's batching design: it had been written to route batched Fable through
Anthropic's Message Batches, a second vendor, when the intent behind answer 30
("provider batch API") was **the OpenRouter lane that already exists**. The
second corrected a dialog answer taken minutes earlier — asked what should
happen if that lane serves no Fable id, the dialog recorded "no batching, keep
Claude Code", and the operator's own words replaced it: **"openrouter only."**

**What it means.** Every model call this program dispatches runs on the
OpenRouter lane. An Anthropic lane is excluded — a second broker instance, a
second key and a second ingest buy nothing, since OpenRouter documents the same
50 % batch discount and passes provider pricing through with no markup on
inference. Claude Code is not a fallback for a seat-dispatched call. The
operator's own interactive Claude Code session is not in scope: this
conversation, and a `plan.js` run the operator starts from it, are the
operator's acts, not the program's automated ones. A `claude` routing row
survives only as the rung-3 terminus of decision 28 — the ladder's end, which
hands the operator a launch line and never fires by itself.

**What it changes.**

- Answers 64a and 65a (Fable drafts the plans and the specs) are **conditional
  on the lane**: Fable drafts if the lane serves a `claude-fable` id, otherwise
  the drafter is the best model the lane does serve, named by FA2's
  measurement. The drafter may change; the lane never does.
- Answer 22a's two runner backends (`claude -p` and `dsh headless`) collapse to
  one. `SPEC-FA`'s heading still names both because a typed heading is
  append-only; its body records the supersession.
- `FA1`'s `docs-spec` and `docs-plan-run` claude rows move from rung 1 to
  **rung 3**. The rung-1 drafter row is `FA2`'s to write on the model it
  measures, so `SPEC-PL`, `SPEC-SA` and `SPEC-FA` now depend on `FA2` as well
  as on `FA1` and cannot be dispatched before that row exists.
- `FA2` no longer has a "write no row" outcome and no longer measures a
  Claude-side subscription baseline: the lane is decided, so a subscription
  figure would decide nothing. It measures what the lane serves and what the
  batch endpoint's shape and turnaround are, then writes the row either way.

**Open, and the operator's to close.** The `PLAN-*` keys still run `plan.js`,
which lives in Claude Code, because the lane-side runner is the very thing
increment 2 plans — planning it any other way is circular. Those three runs are
therefore the operator's own acts under the rule above. If the operator wants
even those on the lane, the Factory spec drafts the runner first and the three
plans wait for it.

## 5. Amendment — the lane drafts, because Fable is unavailable (2026-09-10)

**What happened.** The batched planning step ran and every one of its nine Fable
calls failed in thirty-six seconds with the same error: *"You've hit your
monthly spend limit. Switch to another model, or manage usage credits."* The
Sonnet audit in the same workflow succeeded and the orchestrator's own Opus
session was unaffected, so the limit binds Fable specifically — the most
expensive model, at $10/$50 per MTok against Opus's $5/$25. Nothing was wasted:
50,883 tokens, no drafts, and the nine context blocks (`docs/context/*.md`,
25,829 words) are unaffected and keep.

**The decision.** Asked to choose a drafter, the operator chose **the OpenRouter
lane**, having been told plainly that it is a build rather than a flag: the seat
drafting path `tools/factory/seat/factory-plan.sh` has never run end to end, no
`docs/reviews/plan-drafts/` directory exists, and no `PLAN-*` run appears under
`~/factory/runs`. Opus was available at half Fable's price and was declined. The
operator also declined, for now, a task to measure Claude-side spend, which the
evidence store still reports as `0.0000` — so the next such limit will arrive
the same way this one did.

**What it changes.** Answers 64a and 65a named Fable as the drafter of plans and
specs. Fable is unavailable, so they are amended by fact and by this choice: the
drafter is the best model the OpenRouter lane serves, which today's routing table
resolves as `deepseek/deepseek-v4-pro-0813`. This is the amendment §4 already
anticipated in principle — *the drafter changes, the lane never does* — arriving
sooner and for a different reason than expected.

## 6. Amendment — Fable through the lane, and the retention setting it costs (2026-09-10)

**What was measured.** `FA10` (run `fa10`, `docs/research-2026-09-11-lane-fable.md`)
asked the provider's catalogue from inside the namespace, which is the only
place it can be asked — the seat lane's proxy listens on `10.100.4.1:3141` and
the openrouter lane's on `10.100.3.1:3131`, and `curl -x` against either from
the host returns `http=000` even with the lane's own CA bundle. It found **five
`claude-fable` ids**: `anthropic/claude-fable-5.1` at $10.00/$50.00 per MTok
with cache reads at $0.25, `anthropic/claude-fable-5.1:batch` at exactly half,
$5.00/$25.00, and three further aliases. The 50 % batch discount assumed in
Assumption 15 is real and confirmed for every row.

**And it does not work.** A minimal completion against
`anthropic/claude-fable-5.1` returns `HTTP 404 — No endpoints found matching
your data policy (Zero data retention)`. The routing funnel found four
endpoints and filtered every one: Anthropic's endpoints on OpenRouter do not
offer ZDR, and this account runs it. The lane itself is healthy — the same
proxy returns `HTTP 200` for `deepseek/deepseek-v4-flash` — so this is an
entitlement, not a availability, problem. The `:batch` alias refuses for a
different reason (`only available through the Batch API, use
/api/beta/batches`), so the batch path is a separate and still **UNMEASURED**
question.

**The decision.** Told that Fable is reachable only by relaxing the account's
Zero-data-retention policy, and that this trades the operator's top-ranked
standing preference, the operator chose to **relax ZDR on OpenRouter**. The
alternatives declined were: keeping ZDR and letting the lane's best model draft
(`deepseek-v4-pro-0813` at $0.55/$2.19); Opus in Claude Code at $5/$25; and
measuring the batch endpoint first.

**What it costs, recorded so it is not rediscovered.** What would be retained is
the planning prompts — the nine context blocks, which are an inventory of this
machine: its subsystems, file paths and sizes, the broker's design, the seat's
hardening, the guard's rules and the spend figures. Anthropic requires 30-day
retention for Fable, which is a Covered Model unavailable under ZDR unless
expressly authorized. This is a narrower change than it sounds — the data
already crosses to OpenRouter under invariant 3's chokepoint, and invariant 5's
policy-as-Nix-configuration is untouched — but it is a real move away from
"nothing leaves the machine", made deliberately and by the operator alone. The
setting is at `openrouter.ai/settings/privacy` and only the operator can change
it; the orchestrator neither can nor did. The narrowest option admitting
Anthropic endpoints is the one to take: retention and training are separate
permissions.

**Order of operations.** Nothing is registered or spent until the setting is
changed and `FA10`'s request test is re-run and returns 200. Then Fable is
registered in the four places §5's order names, and the batch re-runs on Fable
through the lane, both passes, against the nine blocks that already exist.

**What it requires, in order.** The lane cannot draft a plan until a routing row
sends plan-drafting work to a model that can. `FA1` (ready, dispatched
2026-09-10 in run `pr2`) lands the `docs-spec` and `docs-plan-run` classes, the
`area` column and the cross-route winner search. A follow-on row then points
those classes at the lane's drafter at rung 1 — the work `FA2` was scoped for,
now needed for a reason `FA2` did not anticipate, since whether the lane serves
a `claude-fable` id has become moot for this purpose. Only then do the nine
drafting tasks dispatch, each reading one context block and writing one plan
draft. Mislabelling those tasks' `kind` to reach a better model, or launching
them at a rung that means "fix round", would both be the re-keying defect the
record already names in `FIX7`; neither is done here.

## 5. Revision (2026-09-27)

§4's rule is revised by
`docs/decisions/2026-09-27-claude-subscription-for-operator-launched-work.md`:
factory dispatch stays on the OpenRouter lane, and operator-launched work may
call Claude through the subscription. The operator does not recall the words
§4 quotes.
