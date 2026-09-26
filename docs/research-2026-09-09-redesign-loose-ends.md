# Redesign loose ends — questions with recommendations (2026-09-09)

## How to answer

**Answered 2026-09-09** through the multiple-choice dialog, all 80 items: `docs/decisions/2026-09-09-redesign-answers.md` (eleven departures from the recommendations listed in its §2). The defaults below no longer apply.

Reply with item numbers and letters (`3b, 17a, 41c`), or one word per item where the word is unambiguous.
Silence on an item takes the stated default; nothing waits on an unanswered item.
Every answer becomes a `docs/decisions/` entry before the batch drafts the plan it belongs to.

## Answer first

Sixteen items reverse a standing decision, read an ambiguous word, widen a boundary, or touch the live host; they need the operator’s word. Every other item takes its default unless overridden.

- **5** what the redesign retires (Hermes, OpenClaw, node2/3) · **8** what "Helm as backend" means · **10** web-first Helm, the GTK app dropped (reverses D-H1) · **13** one seat or many · **14** what "caddy" means · **17** the prompt mutator: rules now, local model later · **20** how far "accessible anywhere" reaches · **22** the graph engine as a repo-side runner outside Claude Code
- **35** the flakes absorbed in waves · **37** a numbered patch series as the rule · **44** the parked labs archived, not absorbed · **45** which "modes" collapse (seat modes; the specialisations stay) · **57** the drive seat launched at `danger-full-access` · **65** Opus drafts the subsystem specs, Fable signs (amends CLAUDE.md) · **66** staggered increments · **69** the seat drives the planning batch

## 0. The asks, restated

- **A.** "an overall redesign of the current system", broken "into sub systems like a real software company".
- **B.** "custom designed agents for each workflow that perform single pass only"; "I don't want my search to be a continually messaging board".
- **C.** "Helm needs to be reworked to work as backend for the DeepSeek harness, essentially a custom one"; "you are permitted to make changes to the actually files of the harness".
- **D.** "All changes should be deployable via a saved and managed patch system."
- **E.** "workflow based more in graph based decision trees that embody the understanding of the nuances of software development and how things can go wrong".
- **F.** "The planning phases using batched fable 5.1 plans should be incremental and part of the workflow."
- **G.** "Bug fixing should be a workflow as well with escalating effort/model single shot calls."
- **H.** "The helm needs design focus on keeping the user interested, take notes from Claude cowork".
- **I.** "add in the TikTok style caddy/comfyui picture generater with local prompt mutator, this should be part of DHS and accessable anywhere".
- **J.** "Collapse all the flakes/modes into a single mode/flake."
- **K.** "Ever rule needs to be residered for the current point in time"; "a refactor/replan if needed but the system needs to be a lot more unified".
- **L.** "you are writing a plan to batch plan all of these plans, including the incorporation of the planning process. This can be ran via the seat."

## 1. Subsystems

**1. What a subsystem is** (asks: A, K)
Context — `docs/MAP.md` groups artifacts by kind (10 modules, 10 packages, 44 checks, 13 test dirs, 34 tools) and `docs/ledger/task-classes.toml` maps 44 globs onto 10 technology classes, so no product axis exists in the tree. The only self-declaration shape already designed is the Helm Home spec's per-flake `helm` output with a build-time check that refuses a declaration the flake does not export (`docs/superpowers/specs/2026-09-04-helm-home-design.md:22,43`).
Question — what artifact IS a subsystem in the redesign?
a) a declared unit: one directory, one flake-output group, one `subsystem` declaration (name, owner role, offers, depends), its own checks, enforced by a build-time assertion.
b) a documentation-and-ownership layer only: a docs page per subsystem, no code boundary, no assertion.
c) reuse `task-classes.toml`'s 10 technology classes as the subsystem list.
d) one spec per subsystem under `docs/superpowers/specs/`, no manifest and no assertion.
**Recommend: a** — it reuses an approved declaration shape rather than inventing one, and the operator prefers failing the build over a runtime check or a docs page.
Default if silent: a, with the docs page generated from the manifest rather than typed.

**2. How many subsystems, on which axis** (asks: A, K)
Context — the two axes that exist are artifact kind (`docs/MAP.md`) and technology class (`docs/ledger/task-classes.toml`), while the actual products (baskets/broker/lanes, Helm, seat and harness, factory, evidence, media, docs) cut across both. The decomposition has to name owners for 765 tracked files here plus 521 across the six sibling repos (§10).
Question — which decomposition granularity does the program adopt?
a) coarse, 5: Isolation, Platform/Host, Surface (Helm), Agency (seat + factory + harness), Record (evidence + docs).
b) medium, 8: Isolation, Platform, Helm, Seat/Harness, Factory, Evidence, Generation (media/ComfyUI), Knowledge (brief/board/runbooks).
c) fine, one subsystem per nixosModule plus one per `pkgs/` entry (about 19).
d) keep the 10 technology classes and add an `area` field only where they disagree.
**Recommend: b** — eight matches the seams already in the tree without splitting Helm's 743-line module or evidence's 25 files across owners, and a real-company shape is capability-shaped rather than file-type-shaped.
Default if silent: b, with Generation and Knowledge named even though they own the least code today.

**3. What an owner is when engineers are agents** (asks: A, B)
Context — ownership today has two values only, `owner = "operator"` or `owner = "orchestrator"` in `docs/ledger/claims.toml`, and `docs/ledger/routing.toml` keys work on (route, role, kind, size, class, rung) with no component owner. Ask B forbids the obvious answer, since a single-pass agent cannot be a standing process.
Question — what does a subsystem "team" resolve to?
a) a declaration plus routing rows: each subsystem declares an owner role, and `routing.toml` gains an `area` column so its work draws the same model and effort ladder every time.
b) a standing agent identity: one long-lived seat per subsystem with its own bootstrap, memory and session.
c) a rotating assignment: the dispatcher picks any seat and ownership is recorded after the fact in the evidence store.
**Recommend: a** — `routing.toml` is already the single place model, effort and rung are decided per key, so one column reuses the most-specific-wins lookup, and b contradicts "single pass only" outright.
Default if silent: a, no agent outlives a call.

**4. How a boundary is enforced** (asks: A, E, K)
Context — all 44 checks are declared inline in one file: `flake.nix` is 2,513 lines and its `checks.${system}` block starts at `flake.nix:766`, so roughly 1,750 lines of check definitions belong to no subsystem. `nixosModules/helm.nix` (743 lines) reaches into brokers, baskets, `evidenceDir`, timers and every specialisation, making it the widest coupler in the tree.
Question — what makes a subsystem boundary real rather than nominal?
a) split `flake.nix` so each subsystem contributes its own checks file, and add a build-time assertion that a subsystem imports only what its manifest declares.
b) split `flake.nix` into per-subsystem check files, no dependency assertion.
c) leave `flake.nix` whole; boundaries live in docs and in review.
d) adopt flake-parts and let module composition be the boundary.
**Recommend: a** — a 1,750-line unowned check block is the measured reason nobody can say which subsystem a red belongs to, and an assertion beats documentation here.
Default if silent: a, with the split landing first and the assertion as its own increment so the refactor stays gradeable.

**5. What the redesign retires** (asks: A, K)
Context — `docs/brief.md:246-256` describes a layout that does not exist: no `modelRouter.nix`, no `agentSandbox.nix`, no `homeManagerModules/`, no `projects/`, and `lib/mkAgent.nix` is 11 lines. Phases 7 (Hermes) and 8 (OpenClaw) of brief §7 were never built and brief §9.3 still asks whether both should exist.
Question — which named-but-unbuilt pieces leave the program?
a) retire Hermes, OpenClaw and node2/node3 explicitly; keep Phase 5 (local weights on the 5090) as a named subsystem with no work scheduled.
b) retire nothing; carry all of them as future subsystems with stub manifests.
c) retire Hermes, OpenClaw and Phase 5 too, so every model call goes through the broker to a remote endpoint.
d) keep Hermes, retire OpenClaw as its fallback (brief §9.3's own framing).
**Recommend: a** — six brief-named artifacts are measurably absent after seven days of building, while local weights remain the only path to local-only data, and the operator would rather rewrite the spec than have agents route around it.
Default if silent: a, with the brief's §6 layout rewritten from the tree in the same increment.

**6. Where the record lives per subsystem** (asks: A, K)
Context — `docs/OPERATIONS.md` is 121,753 bytes in 57 lines and is rewritten whole every turn, while the queue block is derived by `evidence tasks` and gated at commit (CLAUDE.md, "the queue is derived, never typed into the board"). Ownership metadata stops at `claims.toml`'s two owner values.
Question — how does the record acquire a subsystem dimension?
a) add an `area` field to the derived graph and to claims and tasks, and render one derived section per subsystem inside the single board page.
b) one board file per subsystem, each rewritten by its own owner.
c) replace the board with Helm's UI once Helm Home lands; the board becomes a generated view.
**Recommend: a** — the board's measured failure mode is stale hand-typed "current state" text (§9.8), which per-file boards would multiply by eight, and derivation is already the rule for the queue.
Default if silent: a, nothing about areas typed by hand.

**7. Refusing cross-subsystem tasks** (asks: A, E)
Context — the graph's only hard refusal today is a duplicate key; cross-plan `touches` overlaps are reported by `conflicts()` and never refused (§7.6-7.7, §10.14). `task-classes.toml` already derives a task's class from its `touches` list, so the same first-match rule can derive its area.
Question — should the dispatcher refuse a task whose `touches` cross two subsystems?
a) yes, refuse at dispatch unless the task declares both areas explicitly in its section.
b) report only, as `conflicts()` does today; never refuse.
c) refuse only when the two areas have different owners in the manifest.
d) allow freely; areas are advisory and appear in reports only.
**Recommend: a** — the area is derivable from `touches` at no new metadata cost, and the operator prefers a refusal at dispatch over a report a human must read.
Default if silent: a, with the declaration a one-line `areas:` field the planner writes.

## 2. Helm and the harness

**8. What "Helm as backend" means** (asks: C, H) [merged: harness-helm, subsystems]
Context — Helm today is a stdlib forms-only loopback server with four routes, `GET /`, `GET /status.json`, `POST /action/switch`, `POST /action/open` (`pkgs/helm/serve.py:433`), over nine collector tiles (`pkgs/helm/collect.py:29`); the harness is a separate prebuilt Node app the seat launches as `node --expose-internals lib/bin.js --profile web --host 127.0.0.1` (`pkgs/dsh-openrouter/dsh-openrouter.sh:799-801`). The seat's own lifecycle machinery lives in `nixosModules/seatLane.nix` (355 lines), which also carries the guard pin at `:187`.
Question — which reading of "Helm reworked to work as backend for the DeepSeek harness" do we plan?
a) Helm owns the state and action API (jobs, seats, runs, spend, flakes, switches) that a patched dsh web UI calls; dsh keeps the chat surface and the seat units stay in the seat subsystem.
b) Helm absorbs the seat lane: seat units, spool and submit move into Helm, `seatLane.nix` is retired, dsh is reduced to a headless engine.
c) Helm stays read-only status and gains only a UI over the existing spool.
d) one HTTP service serves both the Helm home and the harness chat.
**Recommend: a** — read literally, "backend for the harness" makes Helm serve the harness rather than replace it, and moving `seatLane.nix` into a UI subsystem would move invariants 2 and 3 into the surface.
Default if silent: a, two subsystems with one declared dependency.

**9. Fate of the helm-home plan** (asks: C, H)
Context — `2026-09-08-helm-home-1.md` is typed with 0 of 10 keys landed: HH1 was gated `rework` on a real D-Bus arity defect and HH2 to HH4 were named in its dispatch group but never dispatched, with a six-key blocked cascade behind them (§6a). Its approved spec decides a native GTK4/libadwaita app with the 7700 page demoted to a read-only phone view (`docs/superpowers/specs/2026-09-04-helm-home-design.md:17-19`).
Question — does the redesign supersede helm-home-1, or land it first?
a) supersede: withdraw HH1 to HH10, re-spec Helm from the new asks, keep the D-H1/D-H2/D-H4 decisions that still hold.
b) land wave 1 (an HH1 fix plus HH2 to HH4) first because HH2 closes the switch-without-password hole, then supersede HH5 to HH10.
c) land all ten as written and treat the harness backend as sub-project 2.
**Recommend: b** — HH2 is the only work that closes `uid1000-can-switch-profile` (a gap with `review_by = 2026-09-19`), while HH5 to HH10 build the GTK app the new asks contradict.
Default if silent: b.

**10. Native GTK app vs web-first Helm** (asks: C, H, I)
Context — the approved spec commits to a native GNOME app in Python/GTK4/libadwaita with VTE terminals and makes the web page read-only once Helm Home lands, "no Switch, no token; decision D-H1" (`docs/superpowers/specs/2026-09-04-helm-home-design.md:17-19`). Both "accessible anywhere" and "backend for the harness" point at the web surface instead.
Question — which surface does the reworked Helm present?
a) web-first: one local HTTP app is the home screen and the harness frontend, D-H1's read-only demotion is reversed, and the GTK work is dropped.
b) both: a GTK shell on the desktop and the same backend serving a web view for the phone.
c) keep the spec: GTK app on core, web stays read-only status.
**Recommend: a** — a GTK app cannot be reachable from another device and cannot host the harness's own web UI, so keeping both surfaces doubles the build for one machine and one operator; D-H1 and spec §2.3 are wrong now and should be said to be wrong rather than routed around.
Default if silent: a.

**11. The guard refuses Helm to the seat** (asks: C)
Context — `hook-guard.py` refuses the seat any read of `(?:127\.0\.0\.1|localhost|\[::1\]|0\.0\.0\.0):7700` and of `/run/user/\d+/helm/token`, and `/var/lib/helm` sits in `PROTECTED_ABSOLUTE` (§3b, seat-only rules; the R8 tripwire). If Helm becomes the harness backend, the harness process must reach it.
Question — how does the harness reach its backend without gaining the switch?
a) a second port: a read and act API with no switch route, allowed to the seat, while 7700, its token and `/var/lib/helm` stay refused.
b) lift the R8 refusal and rely on the per-boot token plus HH2's `auth_admin_keep` password dialog.
c) a unix socket with peer credentials, seat uid allowed for non-switch verbs only.
**Recommend: a** — `uid1000-can-switch-profile` is still an open gap with no password wall in place, so a port that structurally cannot switch is a build-time separation rather than a runtime check, and switches are the operator's alone.
Default if silent: a, R8 kept verbatim.

**12. Backend scope and write surface** (asks: C, H)
Context — the state the operator named lives in four unconnected places: `/var/lib/seat/jobs/<id>/job.json` plus `seat@` units (§2a), `~/factory/runs/*/run.meta` (§2d), the evidence store at `/var/lib/evidence` (writable only since FIX6), and Helm's own `/var/lib/helm/status.json`. Helm's current POST posture is a per-boot token, a `Sec-Fetch-Site` check, a held flock and an allowlisted regex-clean target (`pkgs/helm/serve.py:12-21`).
Question — how much does the backend own in this batch?
a) all six domains behind one local JSON API, reads and writes.
b) read-only aggregation of all six, plus only the two write actions that exist today (switch, open).
c) reads of all six plus seat start, stop and attach; spend and switches stay out of the API.
**Recommend: c** — seat lifecycle is the one write the harness genuinely needs, since three of four drive launches died on mechanics no UI could see (§2a), and every other write route is a new privilege surface on a fail-closed server.
Default if silent: c.

**13. One seat or many** (asks: C, B)
Context — all four `drive` jobs hard-code `"port": 43210` in `job.json`, and the second launch died with `bind(...):43210: Address already in use`, so only one drive seat can exist at a time (§2a). 56.1% of the live drive session's clock was idle waiting for the operator (§2e.16).
Question — does the reworked backend host one conversation or many?
a) one seat and one port as today; the backend only makes it observable and restartable.
b) N seats with backend-allocated ports and a session list in Helm.
c) N seats but one interactive at a time; the rest stay headless jobs.
**Recommend: b** — a hard-coded port already cost one launch outright, more than half the driver's wall clock is idle time another conversation could use, and the standing rule is never to design parallelism out.
Default if silent: b.

**14. What "caddy" means** (asks: I)
Context — the comfy-worlds design already names Caddy as the host-level reverse proxy, serving `https://<host>` per world with `tls internal`, a per-world password file and `auto_https disable_redirects` (`~/flakes/media/docs/superpowers/specs/2026-09-05-comfy-worlds-design.md:140-152`); the two hosts are `sfw.core.lan` and `nsfw.core.lan`, named at `:54` and set in the `worlds` set at `:99-100` of the same file; implemented at `~/flakes/media/nixosModules/comfyui-worlds.nix:289-316`. No other meaning of "caddy" exists in either tree.
Question — in "TikTok style caddy/comfyui picture generater", is "caddy" the Caddy server?
a) yes, the ask is the comfy-worlds feed behind the Caddy sites already designed.
b) no, "caddy" names a swipe-feed UI component inside Helm and the server is incidental.
c) both: Caddy fronts it and the swipe view is the component.
**Recommend: c** — the ask pairs "TikTok style" with "caddy/comfyui": Caddy is the approved front for the worlds and the swipe view is sub-project 2’s "vertical feed" (item 15), so c is the reading that loses neither; tool names read literally, and the feed is the part Helm must reach.
Default if silent: c.

**15. New feed or comfy-worlds sub-projects 2 and 3** (asks: I)
Context — the worlds spec already scopes sub-project 2 (a job queue on ComfyUI's API, a per-world `feed.sqlite` index, "the feed app itself (vertical feed of renders, like, regenerate with a new seed, edit prompt)") and sub-project 3 (prompt mutation from likes) at `spec:321-323`, and a placeholder feed already serves both ports (`~/flakes/media/pkgs/comfy-worlds/feed_placeholder.py:1-14`). W6 is `rework` on 3 MAJOR with no fix round written (§6a).
Question — does the batch plan the existing sub-projects 2 and 3, or design a new feed?
a) plan sub-projects 2 and 3 as specified, with W6's fix round first; Helm links or embeds the feed rather than reimplementing it.
b) a new design that supersedes them, with the feed built inside Helm from scratch.
c) sub-project 2 only in this batch; mutation deferred to its own phase.
**Recommend: a** — "vertical feed, like, regenerate, edit prompt" is verbatim the TikTok-style feed just asked for and it is already an approved spec with ports, paths and a placeholder seam in place.
Default if silent: a.

**16. Getting the generator onto core** (asks: I, J)
Context — `~/flakes/media` is not an input of this flake (`flake.nix` inputs list nixpkgs, nixpkgs-host, llm-agents, claude-desktop, gaming only), and `hosts/core/helm.nix:12` records that "media stays OUT of profiles until round 2 wires specialisation.media", a plan that is `parked` (§6a). So no ComfyUI, no feed and no Caddy run on core today.
Question — how does the generator reach the live host?
a) wire media in as a NixOS specialisation the operator switches into (the parked round-2 shape).
b) wire the worlds' on-demand user units plus host-level Caddy into `core` directly, no specialisation, so the feed always answers and the generator starts on demand.
c) leave media off core; the feed is reachable only while a media profile is booted.
**Recommend: b** — the spec already makes the generators `wantedBy = []` on-demand user units on distinct loopback ports (`spec:282`), so a specialisation buys nothing and a specialisation-only feed cannot be reachable while the operator is working; the operator still owns the switch that lands it.
Default if silent: b.

**17. What the prompt mutator is** (asks: I)
Context — concept `2026-09-06a-generation-lab.md:5` defines mutation as thousands of prompt, LoRA, sampler and seed variations graded by a local vision-language judge that never shares the 32 GB card with the diffusion model. No local model runtime is deployed: a repo-wide grep for llama in `hosts/`, `nixosModules/` and `flake.nix` returns nothing, and llama.cpp is Phase 5 research (`docs/research-2026-09-02-derisk.md:36`).
Question — is the "local prompt mutator" a local model, or rules?
a) rules only: a mutation grammar over the world's lab repo (token swaps, LoRA strengths, samplers, seeds), shipping in this batch.
b) a local VLM or LLM under llama.cpp/llama-swap, packaged in this batch.
c) rules now; the local model arrives as its own phase once the llama.cpp stack lands.
**Recommend: c** — the mutator's payload is prompt text, which the data-class rules keep local-only, and no local inference stack exists yet to run it, so rules are the only version that ships this batch without a new GPU service.
Default if silent: c.

**18. What "keeping the user interested" has to prove** (asks: H)
Context — nothing in the tree measures engagement, and the operator model records "falsifiable, not merely tested; unmeasured is debt; proxies declared" (`docs/board/operator-model.md`). Helm's renderer already forbids `<script`, `src=` and external URLs by test (`pkgs/helm/serve.py:21-23`), which bounds how lively a page can be.
Question — what acceptance does "keeps the user interested" get?
a) none: a design brief the operator judges at the acceptance drill with "test passed".
b) a local-only engagement stream in the evidence store (opens, dwell seconds, feed likes per day, counts and never content).
c) a checklist of UI properties enforced as build-time checks (first paint under 1s, something new on every open, all three verbs one click from the home, the feed reachable without typing a URL).
**Recommend: c** — a property checklist is the only form of "interesting" that can fail a build rather than be argued about, and b would need a new content-adjacent data class for no design gain.
Default if silent: c, with the operator's drill still the final word.

**19. What from Cowork is wanted** (asks: H)
Context — the ask names Claude Cowork the product (a task list as the home, background work, artifacts, sessions that outlive the window); this repo’s "Cowork tier A" is an unrelated install plan, `parked` by decision on the board (`docs/OPERATIONS.md:48`), for the Claude Desktop app under its own UID with netns, broker and managed-settings lockdown (`docs/superpowers/plans/2026-09-02-phase4b-cowork.md:5`), with nothing about UI.
Question — what does "take notes from Claude cowork" import?
a) UX ideas only: a task list as the home, work that continues in the background, artifacts you can open, a session that survives you walking away; tier A stays parked.
b) un-park tier A so Cowork runs on core alongside Helm and the harness.
c) both: borrow the UX and un-park the install.
**Recommend: a** — tier A is parked by a standing decision and is an isolation build rather than a design source, and reopening a parked decision is the operator's act, not a plan's.
Default if silent: a.

**20. "Accessible anywhere" and the loopback assertion** (asks: I, C, K) [merged: harness-helm, subsystems, rules-board-record]
Context — `nixosModules/helm.nix:486-487` asserts the listener is `127.0.0.1:` or `[::1]:` with the message "Helm is localhost-only until Phase 10", and `docs/brief.md:353-356` puts remote access from outside the LAN and anything touching the Pixel out of scope. A grep for tailscale, wireguard or vpn across `*.nix` returns nothing; the only designed off-box path is Caddy on the LAN with an internal CA and a password per site (comfy-worlds spec:53-56).
Question — how far does "accessible anywhere" reach?
a) LAN only: Caddy, internal CA, a password (or WebAuthn) per site, brief §10 amended in the operator's own words in the same commit.
b) LAN now plus a declared private overlay (one wireguard or tailnet peer set) typed as its own later gated phase.
c) loopback only: "anywhere" means any workspace on this host, and nothing widens until §10 is amended.
d) LAN, read-only, unauthenticated.
**Recommend: b** — "anywhere" read literally reaches past the LAN, and a private overlay (one wireguard or tailnet peer set) keeps every byte on the operator’s own devices, so it does not contradict "nothing leaves the machine"; it does widen a listener, so it is typed as its own gated phase after LAN lands, with brief §10 and the loopback assertion amended in the operator’s words.
Default if silent: c, because nothing widens a listener without the operator’s word.

## 3. Workflows and agents

**21. What "single pass" forbids** (asks: B, E)
Context — every agent call in the tree is already one prompt with one structured return (`.claude/workflows/plan.js:295-301`); what loops is the script, since gather runs up to two Opus critic gap rounds that spawn new readers (`.claude/workflows/gather.js:9-10`), and the drive session's inbox took only 31 of 104 `user/message` events from the operator, the rest being plugin notices, agent-messages, subagent-settled and goal nudges (§2f.21).
Question — what does "single pass only, not a continually messaging board" bind?
a) every agent call everywhere: one prompt, one structured return, no agent-to-agent messaging, no in-agent multi-turn, with every loop an explicit graph node carrying a declared attempt budget.
b) only the research and search workflows: readers fan out once and critic gap rounds are removed.
c) only the driving session's inbox: no agent-to-agent messaging or self-nudges, and subagent output arrives as an artifact the next node reads.
**Recommend: a** — the agents are already single-call, so the ban only bites if it moves the loops into the graph, and b and c then follow as consequences.
Default if silent: a.

**22. Where the workflow engine runs** (asks: B, E, L)
Context — the three workflows are Claude Code Workflow scripts invoked as `Workflow({ name: 'plan', … })` (`.claude/workflows/plan.js:2`), and no seat-side runner exists: a grep for `Workflow(` over `tools/` and `pkgs/` returns nothing and the seat's surface is twelve bash tools (`ls tools/factory/seat/`).
Question — where does the new graph engine live, given the plan "can be ran via the seat"?
a) a repo-side runner (python or bash) reads the declarative graph and calls a model per node through `claude -p` (Claude Code headless, for Claude rungs) or `dsh headless` (for seat rungs): one engine, two model backends, both drivers.
b) keep Workflow scripts as the engine; the Claude session runs every workflow and the seat only dispatches tasks and gates.
c) port the engine to dsh subagents and keep Claude only for judge nodes.
**Recommend: a** — the seat drove all 15 headless dispatches of 2026-09-09 (§2d.12) but cannot invoke a Workflow script, `claude -p` runs already exist on this host (the OTel measurements), and `docs/ledger/routing.toml:1-13` already single-sources model choice for both machineries.
Default if silent: a.

**23. What a custom agent is, as a file** (asks: B, E)
Context — no `.claude/agents/` directory exists in the repo or under `~` (bug packet §8a); every agent is an inline `agent(prompt, { model, effort, schema })` call, with Fable pinned at six separate lines of one file (bug packet §8b). Whether `.md` frontmatter even accepts `model: fable` is UNMEASURED (bug packet §13).
Question — how is a per-workflow agent defined and pinned?
a) one `.claude/agents/<role>.md` per role (frontmatter model, tools, description), referenced by name from the graph.
b) one pinned registry in the repo (role to model, effort, tool allowlist, output schema, prompt file) from which any `.md` shim is generated, drift-checked the way `route.py` and `render.test.mjs` check routing today.
c) keep inline prompts and hoist only model and effort into `routing.toml` rows.
**Recommend: b** — Fable support in `.md` frontmatter is unmeasured, so betting the redesign on it is a guess, and the repo already has a generated-plus-drift-checked precedent for model pins.
Default if silent: b.

**24. The graph as an artifact** (asks: E)
Context — `plan.js`, `gather.js` and `loose-ends.js` each re-implement the same fan-out, verify, gate, revise shape in JS (`.claude/workflows/loose-ends.js:20-27` mirrors `.claude/workflows/gather.js:39-60`), and `plan.js` only throws on an unsound graph after its five paid reader agents have run (`.claude/workflows/plan.js:305-311`).
Question — what form does a workflow take?
a) a declarative graph file per workflow (nodes: agent, tool, gate, refusal; edges: condition plus attempt budget) executed by one runner, with a repo check that refuses an unsound or unreachable graph at build time.
b) JS scripts as today, factored onto a shared phase library.
c) a declarative graph for the decision structure with a JS escape hatch per node.
**Recommend: a** — today's soundness refusal fires only after five reader agents are paid for, and a saved graph is the only form the seat and Claude can both execute.
Default if silent: a.

**25. What the graph verifies mechanically** (asks: E, G)
Context — the one measured discriminator between rejected and control runs is whether the run executed the mutants its section named, since no control ever ran zero and 41 of 66 rejected did, while `tests_first` and `red_shown` separate nothing (61 and 63 of the 66 rejected had them) (§4c.16). The harness report's own control verdict on self-reported checks prints `revert` (§4b.14).
Question — which evidence does the graph re-run itself instead of reading from the agent's report?
a) the named mutants only: a node re-runs each and refuses the attempt if any survives.
b) the named mutants and the named checks, both re-run by the runner, with the agent's own claim never a signal.
c) keep self-reports and add a citation-resolver node in front of the gate.
**Recommend: b** — `mutants_run` is the only clean split in the record and the self-reported-checks control was overruled 2 of 5, so an unverifiable claim should fail the node rather than the gate reviewer's patience.
Default if silent: b.

**26. Escalation as declared state** (asks: E, G)
Context — `factory_rung_of_key` reads a trailing lowercase letter in a key as a rung climb (`tools/factory/seat/factory-lib.sh:799-810`), which sent BUG1a to Pro by accident and pushed FIX5d into an Opus rung, forcing a letterless re-key as FIX7 purely to dodge it (`docs/superpowers/plans/2026-09-09-bugs.md:575`; §2d.13).
Question — how does the new workflow decide a rung?
a) the graph node declares the rung and the attempt carries it; key names stop being routing, and a check refuses any key whose suffix implies a different rung than the node declares.
b) keep suffix-derived rungs and add the `--rung` flag `factory-review` is documented to accept but refuses (§7.14).
c) both: the declared rung wins and the suffix lint stays as a guard.
**Recommend: a** — the FIX5 lineage cost five dispatch rounds and 2h 27m of seat wall time, one round spent only on re-keying to escape a suffix-derived escalation, and a model choice hidden in a filename is the opposite of a diff-reviewable routing table.
Default if silent: a.

**27. Rung 1 of the bug workflow** (asks: G)
Context — both Flash rung-1 gather stages were rejected and both chains were approved only at rung 2 (bug packet §12.5), and 5 of 13 MAJORs in that chain were fabricated pastes or wrong citations (bug packet §12.7). Seven-day spend is Flash $0.14 against Pro $11.50 (§4a.5).
Question — what model and guard does the first, cheapest rung of a bug workflow use?
a) start at Pro (`off`/medium) and reserve Flash for XS docs only.
b) Flash first, exactly one attempt, then Pro: the status quo made explicit.
c) Flash first, with a mechanical citation-and-command re-resolver node before any paid gate.
**Recommend: c** — Flash is roughly 80x cheaper on the seven-day line but went 0 for 2 at rung 1, and both failures were measurement integrity, a class a script catches; spending an Opus gate to find a fabricated paste is the expensive way to learn it.
Default if silent: c.

**28. When escalation stops** (asks: G)
Context — a ladder-exhausted lookup exits 4 and `factory-task` writes `<KEY>.escalate` and never a `.result` (§7.13); rung-3 re-plans, pauses and spend decisions are the operator's, and model and effort are never hand-picked (§8.1; bug packet §9.15).
Question — what ends a bug's escalation ladder?
a) after rung 3 the workflow stops, writes its findings and hands the operator a decision: never a fourth attempt, never a hand-picked model.
b) escalate automatically onto a Claude (Opus) rung and keep going until green.
c) stop after two rungs; every third attempt is an operator decision.
**Recommend: a** — rung 3 is already the operator's boundary in the driving-authority decision and the escalate path already halts with a marker rather than a result.
Default if silent: a.

**29. Where a bug lives before a task** (asks: G, A)
Context — `docs/bugs/` is written by a typed gather task and read by nothing; `plan-defects.toml`'s enum has no regression arm and `claims.py`'s evidence regex accepts only `check:<name>@<rev>` or `operator:<date>` (bug packet §12.1). The board's queue block is regenerated whole-tree and gated at commit by G8c (§7.11).
Question — what is the durable intake record for a defect in landed code?
a) a typed ledger file (id, symptom, repro command, status, closing check) derived into the board's queue block like tasks.
b) keep `docs/bugs/*.md` findings files and add an index the board reads.
c) a plan heading only, as today.
d) a `claims.toml` row under a new evidence class.
**Recommend: a** — nothing in the tree reads `docs/bugs/`, so a defect is invisible to the brief until someone types a task, and the board block is already whole-tree derived and commit-gated.
Default if silent: a.

**30. What "batched Fable plans" means** (asks: F, L)
Context — `plan.js` plans one spec per invocation and re-gathers a five-Sonnet packet on every run (§7.2), and batching appears nowhere in any spec or plan text (§8.15). The operator's own turn that day was "Look into how batching works in openrouter. I am curious if we could batch workflows." (§2f.24).
Question — what is batched in "planning phases using batched fable 5.1 plans"?
a) N plans in one workflow run: one shared packet, one Fable draft node and one judge panel per plan, one dispatch per plan.
b) the provider's batch API (OpenRouter or Anthropic) for the model calls themselves.
c) one Fable draft covering N specs in a single plan file.
**Recommend: a** — the cost that repeats is the packet, since N plans today means 5N Sonnet readers, and provider batching can be measured later without changing the workflow's shape.
Default if silent: a.

**31. Incremental planning inside the graph** (asks: F, L)
Context — the task graph is built from every typed plan at once and a key defined in two plans is a hard failure that makes `plan.js` refuse to draft at all (§7.5, §7.6, §7.3), while the packet phase re-gathers live mechanical facts on every run (§7.2).
Question — how is planning made incremental and part of the workflow?
a) one plan node per increment: plan, dispatch, land, then re-plan the next increment against the landed tree, with keys namespaced per subsystem so the duplicate-key gate cannot fire.
b) draft every increment's plan up front and dispatch them in waves.
c) rolling: the next increment is planned while the current one is still running.
**Recommend: a** — a plan drafted before its predecessor lands is drafted against a tree that no longer exists, and the planner refuses to draft on an unsound whole-tree graph anyway.
Default if silent: a.

**32. What an escalated attempt reads** (asks: G, E)
Context — the fix seat never reads the gather's findings file, since the orchestrator retypes its facts into the plan section by hand (bug packet §12.2, §12.3), and `factory-wave` never passes `--prior`, so without it the seat never sees the rejecting review (`docs/superpowers/plans/2026-09-09-bugs.md:641`).
Question — what does the graph hand the next rung of a failed node?
a) a machine-readable artifact the prior node wrote (claims with their commands, the failing repro, the reviewer's errata), passed by the runner, with no hand retyping.
b) the prior review file, as `--prior` does today.
c) a freshly hand-typed task section, as today.
**Recommend: a** — retyping is where the record's cost went, since the FIX5 lineage took five rounds and a single fix attempt read 2.57M tokens (bug packet §3a), and an edge payload is the one thing a graph gives that a hand-off does not.
Default if silent: a, with b kept only while the bash driver still exists.

**33. Which executor survives** (asks: A, K, E)
Context — `tools/factory/dark-factory.js` last changed 2026-09-07 (`git log -1 --date=short` on that path) and no commit since 09-06 names it, while the seat's bash tools ran all 15 headless dispatches of 09-09 (§2d.12); both parse `routing.toml` through independent parsers kept in sync by `render.test.mjs` (bug packet §12.13).
Question — does the redesign keep two execution machineries?
a) one executor, the seat's bash tools, driven by the graph runner; `dark-factory.js` is retired to the archive.
b) one executor, a JS engine, with the bash tools reduced to its shell-out layer.
c) keep both, unified only by the routing table (status quo).
**Recommend: a** — the bash driver executed every dispatch of the last recorded day while the JS factory has been untouched for two days, and every feature it holds alone already exists seat-side (§7.8-9).
Default if silent: a.

**34. Who may write agents and graphs** (asks: B, E, K)
Context — the guard protects `docs/superpowers/plans`, `.claude/ritual-override` and its own file on the stated ground that "a seat must not be able to edit the rules it obeys" (`tools/orchestrator-guard.sh:176-182`); a grep for workflows in that file returns nothing, so `.claude/workflows/*.js` is agent-writable today.
Question — who owns agent definitions and workflow graphs once the graph encodes the refusals?
a) the operator: add the workflows directory and the agent registry to the guard's protected paths, so agents may propose a diff and never write one.
b) agents may write them under normal review, like any other code.
c) operator-owned graphs and refusal nodes, agent-writable prompt bodies.
**Recommend: a** — that exact argument already put the guard's own file into its protected list, and the graph will carry the mutant, check and rung refusals.
Default if silent: a, with c as the narrow version if agent-editable prompts are wanted.

## 4. Flakes and patches

**35. Scope of "collapse all the flakes"** (asks: J, A) [merged: flakes-patches, subsystems]
Context — seven sibling dirs exist under `~/flakes` but only six carry a `flake.nix`, since dsh-harness is AGENTS.md plus `skills/` and docs with no flake at all; gaming is already an input of this flake (`flake.nix:26`) while media deliberately is not. This repo's flake is 2,513 lines with 44 checks and builds the live host, and `chatgpt-work` appears in neither `repos.toml` nor the derived graph.
Question — what does "a single flake" mean: one repo containing everything, or one entry point with the siblings still separate repos?
a) one repo and one flake: every sibling's files move in as subdirectories in one absorption plan, and the `~/flakes` repos are archived.
b) one repo and one flake absorbed in waves, one sibling per task, each with its own build gate and switch.
c) keep the sibling repos and make this flake the single entry point by adding each as a pinned input (the gaming pattern).
d) collapse only the agent-harness family (dsh-harness, codex, openai-lab, chatgpt-work); media, gaming and nixos-skill stay separate.
**Recommend: b** — the host runs live from this repo, so every absorption step is a build the operator must switch, and the house rule is one phase at a time with an acceptance test per phase; c is the status quo dressed up and gives none of the asked-for unification.
Default if silent: b.

**36. The harness payload has no Nix at all** (asks: C, D, J)
Context — the seat's mind is deployed by two hand-made symlinks, `~/.local/share/dsh-openrouter/{AGENTS.md,skills}` pointing into `~/flakes/dsh-harness`, and the wrapper says so itself, "still deployed by two hand-made symlinks … (no flake yet)" (`pkgs/dsh-openrouter/dsh-openrouter.sh:532-533`, warn lines at `:555-556`). Invariant 4 says an environment is reproducible from `flake.lock` plus `baskets.lock` and "if a step requires imperative setup, it is a bug in the design" (`docs/brief.md:73-75`).
Question — does the collapse make the harness payload (AGENTS.md plus the 17 skills) a Nix-built store path?
a) yes: the payload becomes part of the `dsh-openrouter` package, symlinked from `/nix/store`, and a missing or handwritten payload fails the build.
b) yes for AGENTS.md only; skills stay a live directory the seat can edit between switches.
c) no: keep the symlinks and add a check that they exist and point where they should.
**Recommend: a** — this is the one measured live violation of invariant 4 in the seat path, and it turns the AGENTS.md trailer contradiction (§9.14) into a diff the gate can see.
Default if silent: a.

**37. What a "patch" is, mechanically** (asks: D, C) [merged: flakes-patches, subsystems, harness-helm]
Context — no patch machinery exists anywhere: a grep for `patches = [`, `postPatch`, `patchPhase` and `applyPatches` over `*.nix` returns zero hits and no `patches/` directory exists. dsh is a `buildNpmPackage` of the published 0.1.2-rc.1 tarball pinned by a lockfile whose upstream "takes no external pull requests: extend it with plugins, bump the pin deliberately, expect re-ports" (`pkgs/dsh/default.nix:5-8`).
Question — what is the saved unit of a harness change?
a) a numbered diff series `patches/dsh/NNNN-name.patch` applied in the derivation's `postPatch` against the unpacked tree, plus a manifest and a check that every patch applies cleanly.
b) whole-file overlays copied over the unpacked tree, no diff format and no apply step.
c) plugin first wherever the plugin API reaches, with the option-a patch series as the exception rather than the rule.
d) vendor the harness source into the repo, drop the npm pin, and edit it directly.
**Recommend: a** — the operator has just permitted changes to the harness’s actual files and asked for a saved, managed patch system, so the numbered series is the rule; a plugin is used only where it reaches the same behaviour with a smaller re-port surface, and the ledger (item 46) records which.
Default if silent: a.

**38. Does the patch system cover more than the harness** (asks: D)
Context — three vendored upstreams exist today, dsh (`pkgs/dsh`), claude-code via llm-agents (`flake.nix:21`) and ComfyUI in `~/flakes/media`, and none of the three is patched at all (zero `postPatch` hits repo-wide). The ask says "all changes should be deployable via a saved and managed patch system".
Question — does "all changes" mean every vendored upstream, or only the DeepSeek harness?
a) harness only (dsh plus its payload); everything else stays ordinary Nix code.
b) every vendored third-party upstream (dsh, claude-code, ComfyUI) uses the one mechanism.
c) repo-wide: every change of any kind becomes a named, saved, replayable patch unit, our own code included.
**Recommend: b** — only vendored upstreams have the re-port problem a patch series solves, and c would replace git with a second change system for code that already has one.
Default if silent: a.

**39. What "deployable" means when only the operator switches** (asks: D)
Context — a switch here takes three commands, `switch-to-configuration switch`, then `nix-env -p /nix/var/nix/profiles/system --set <toplevel>`, then `switch-to-configuration boot` (`docs/board/handoff-2026-09-09-session-22.md:18-22`), and Helm's own profile switch uses `switch-to-configuration test` and is per-boot (`nixosModules/helm.nix:697`).
Question — does a saved patch reach the running system only at the operator's next switch, or can it apply without one?
a) build-time only: a patch changes the store path, so it lands at the next operator switch and nowhere else.
b) build-time, plus a Helm view listing the patches the next switch will carry and the generation each one landed in.
c) a runtime overlay directory the harness reads, so a harness patch applies to the next seat launch with no switch.
**Recommend: b** — agents never switch and the switch recipe is three hand-run commands, so the store path is the only honest deploy boundary, and showing the queue makes "managed" something the operator can read before he switches; c reintroduces the imperative state invariant 5 forbids.
Default if silent: a.

**40. Reversing the Claude/dsh separation** (asks: J, K)
Context — no decision file for a Claude/dsh code separation exists (`ls docs/decisions/` shows 22 files and none names it); the nearest recorded decision is `2026-09-02-memory-per-flake`, one memory dir per folder, "none is linked, copied or symlinked into another", and the host hard-codes those per-flake memory dirs in the backup set (`hosts/core/proton-backup.nix:38-39,:71-74`).
Question — does the collapse reverse the separation for code only, or for memory and backups too?
a) code collapses into one repo; memory dirs and their backup rows stay separate per subsystem (a directory-keyed memory, not a repo-keyed one).
b) everything collapses: one repo, one memory dir, one backup row.
c) no reversal: the separation stands and the collapse stops at the flake boundary.
**Recommend: a** — the separation the operator actually recorded is about memory rather than gits and is enforced today in the backup config, so collapsing folders would silently merge those dirs.
Default if silent: a, with the decision file written before the first absorption commit.

**41. One repo, one task-key namespace** (asks: J, L)
Context — the derived task graph is keyed by `(repo, chain_root)` pairs "so `derive_status` and `waves` can key satisfaction without leaking one repo's landed root into another repo's" (`pkgs/evidence/tasks.py:4-16`), and a duplicate key is a hard refusal on the whole tree (§7.6). Six plans are still open across the siblings (§10.12).
Question — when seven repos become one, what happens to the existing task keys?
a) live keys get a subsystem prefix at absorption (W6 to MEDIA-W6, HH1 to HELM-HH1); landed keys are frozen as history and never re-derived.
b) all keys keep their names; the absorption plan proves no collision first and refuses to merge if one exists.
c) keep `repos.toml` semantics inside the one repo, so "repo" becomes a subdirectory and the (repo, root) pair survives.
**Recommend: a** — the sibling roots were never chosen to be globally unique and a duplicate refuses the whole tree, which would block every dispatch on day one; prefixing is a one-time rename the graph check can verify.
Default if silent: b.

**42. The factory's base clone becomes one lock** (asks: J)
Context — `factory-ws` derives the base clone from the repo's basename and serialises refresh with a per-repo flock, "two refreshes at once collide on .git/index.lock", then resets hard to the source HEAD (`tools/factory/seat/factory-ws:46-52,:67-70`); seven base clones and seven lock files exist today and a wave runs up to five groups concurrently (§10.1).
Question — with one repo, do all concurrent tasks share the single base clone and its single lock?
a) yes, unchanged: the lock guards only the refresh, and five groups serialising on a local clone refresh is acceptable.
b) shard the base clone by subsystem path so the lock granularity survives the collapse.
c) drop base clones for git worktrees per run, removing the lock entirely.
**Recommend: a** — the lock covers the refresh and not the run, and observed max concurrency is 5 on a 24-CPU host nowhere near saturated (§4f.24, §4f.22), so b and c redesign machinery not yet shown to be the bottleneck.
Default if silent: a.

**43. Which nixpkgs the single flake pins** (asks: J)
Context — three distinct nixpkgs revs are live across the eight repos, and this flake carries two on purpose, `nixpkgs` 34ab99075 and `nixpkgs-host` a5cc6f2c, with a 15-line comment explaining why llm-agents cannot follow the host pin (`flake.nix:5-20`); gaming, codex and chatgpt-work pin a5cc6f2c while media and nixos-skill pin ac62194c.
Question — what is the pin policy for the collapsed flake?
a) one nixpkgs for everything, so absorbing media and nixos-skill means moving them off ac62194c in the same task.
b) keep the documented nixpkgs plus nixpkgs-host pair, move every absorbed subsystem onto nixpkgs-host, and leave llm-agents on its own.
c) allow a per-subsystem pin as an extra input wherever a subsystem needs one.
**Recommend: b** — the dual pin exists for a measured build failure rather than taste, and c would let the collapse re-fragment the pins it was meant to unify.
Default if silent: b.

**44. The parked agent labs** (asks: J, A)
Context — three of the seven siblings are arms the operator already ruled on: Codex "stays an operator app" and is parked on core (§8.6), the dsh-harness three-model planning factory is parked (§8.7), and openai-lab pins THIS repo by rev (`nixos-agent-env.url = git+file:///home/dalhaka/nixos-agent-env?ref=main&rev=d2ad5c79…`), which becomes self-referential on absorption; `chatgpt-work` is in neither `repos.toml` nor the task graph.
Question — do the parked labs (codex, openai-lab, chatgpt-work) get absorbed, or archived?
a) archive all three read-only under `~/factory/archive`; absorb only dsh-harness, media, gaming and nixos-skill.
b) absorb all seven as subdirectories, since parked means dormant rather than deleted.
c) absorb openai-lab (it has landed work, OL1 to OL3) and archive codex plus chatgpt-work.
**Recommend: a** — absorbing openai-lab is measurably self-referential and the Codex arm is decision-parked with nothing of Codex in the tree, so carrying dead arms into the one flake enlarges the evaluation the live host depends on for no live use.
Default if silent: a.

**45. Which "modes" are being collapsed** (asks: J) [merged: flakes-patches, subsystems]
Context — at least four things here are called a mode: seat job modes `headless|web|drive` (`pkgs/seat/seat-submit.py:171`), dsh permission modes reached only by `DSH_PERMISSION_MODE` (§3a.1-3), NixOS specialisations base and gaming (`hosts/core/default.nix:40`) which Helm switches with `switch-to-configuration test` (`nixosModules/helm.nix:697`), and the lane/basket instances. `nixosModules/helm.nix:426` pins the control profile list to the literal `[ "base" ]`.
Question — which of these is the "single mode" the operator wants?
a) the seat modes: drive, web and headless become one launch path with flags, while specialisations and Helm's profile switch stay.
b) the specialisations: one profile, gaming always present, the seat keeps its three modes.
c) both: one seat launch path and one profile.
d) neither: "mode" means only the flake variants and item 35 already covers it.
**Recommend: a** — three of the seat's four launches produced no conversation and two died on mode-specific mechanics (a held port 43210, a read-only `/tmp`), while the specialisations are exactly what Helm exists to switch and what the same ask wants to grow.
Default if silent: a, with `[ "base" ]` becoming a derived and asserted list.

**46. Where the patch metadata lives** (asks: D)
Context — the house pattern for managed state is a validated ledger, since `docs/ledger/claims.toml` has its own validator command in CLAUDE.md and `repos.toml` and `routing.toml` follow it; there is no ledger for patches because there are no patches (zero `postPatch` hits repo-wide).
Question — where does a patch's provenance live?
a) `docs/ledger/patches.toml` (file, target package, reason, upstream status, date added, review-by) validated by a check that also proves every listed patch applies.
b) front matter inside each `.patch` file, parsed at build time.
c) both: front matter for the human reading the diff, the ledger as the authority the check reads.
**Recommend: a** — every other managed list here is a TOML ledger with a validator, and a patch with no recorded reason is the thing that survives three pin bumps unexamined.
Default if silent: a.

**47. What a failed patch does at the next pin bump** (asks: D)
Context — dsh is a developer preview that "promises breaking changes and takes no external pull requests: … bump the pin deliberately, expect re-ports" (`pkgs/dsh/default.nix:5-8`), and the lockfile plus `npmDepsHash` mean any bump invalidates the fixed-output hash.
Question — when a saved patch stops applying after a pin bump, what happens?
a) the build fails hard, and the bump is a task whose acceptance is a re-port of every patch in the ledger.
b) patches may be marked optional and skipped with a warning so the bump lands without the re-port.
c) apply with fuzz or a 3-way merge and warn.
**Recommend: a** — a silently skipped patch is a behaviour change that reaches the seat at the operator's next switch with nothing in the diff to show it.
Default if silent: a.

**48. Sibling history under absorption** (asks: J)
Context — every sibling head is an integrate commit the board and evidence store cite by hash (media `74f7341`, dsh-harness `d1b5f85`, gaming `a4088d7`, codex `3f96d7a`, openai-lab `4b1c48e`), and the derived graph judges "landed" against the repo a task is attributed to (`pkgs/evidence/tasks.py:4-16`).
Question — how does each absorbed sibling's git history reach the single repo?
a) a subtree-style merge per sibling (`--allow-unrelated-histories`) so every commit stays reachable under its new subdirectory.
b) one import commit per sibling with the files only; the old repos are archived read-only and remain the place to look up a hash.
c) no import: vendor a read-only copy and leave the sibling repos as the working ones.
**Recommend: a** — task status and the board's landing record are hash-citations into those repos, so a files-only import turns every prior citation into a dangling hash the graph cannot verify.
Default if silent: b.

## 5. Rules, board and record

**49. Scope of "every rule reconsidered"** (asks: K)
Context — rule text lives in six places with six origin dates: `docs/brief.md` §3 (first and last commit 2026-09-02), `CLAUDE.md` (2026-09-02, last touched 2026-09-09), `docs/board/policies.md` (2026-09-05), `docs/board/operator-model.md` (2026-09-06, one commit), `tools/orchestrator-guard.sh` (2026-09-05), and `~/flakes/dsh-harness/AGENTS.md` in a different git (`docs/ledger/repos.toml:23-24`).
Question — what does "every rule reconsidered for the current point in time" produce?
a) one dated ruleset task: every rule re-stated in a single source file with its origin date and a verdict (keep, amend, retire), from which CLAUDE.md and AGENTS.md are generated, with the six brief §3 invariants copied in verbatim and marked confirmed rather than reopened.
b) a per-rule row in a new `docs/ledger/rules.toml` with a status each, no single prose file.
c) only the rules the packet measured as broken get touched (the trailer, the plan-file denial, the ritual); the rest stand.
d) full reopening, brief §3 invariants included.
**Recommend: a** — brief §3's own header says "These are not negotiable" (`docs/brief.md:64-66`) while every other rule file was written on a different day by a different session, so the audit must separate the two classes.
Default if silent: a, the six invariants re-stated verbatim and untouched.

**50. The board's front door** (asks: K, A)
Context — `docs/OPERATIONS.md`'s START HERE block is 121,176 chars and its heading line alone is 20,294 chars, while `SESSION_START_CAP_BOARD` defaults to 2,300 (`docs/runbooks/session.md:58`), so 1.9% survives and the cut lands mid-sentence inside line 10; the board's real current paragraph sits at line 40 and never reaches a session.
Question — what does a session read first, once the board stops being a narrative?
a) a generated status page (the derived graph, the bundle, the newest handoff pointer) written whole by `evidence`, with the hand-written START HERE narrative deleted and its prose moved to the log.
b) keep START HERE but hard-cap the whole block by lint, not just the `**OPEN` paragraph, and move everything above the cap into the log each turn.
c) keep it as is and raise `SESSION_START_CAP_BOARD` to fit.
**Recommend: a** — the lint that exists (`tests/lint/now-paragraph.sh`) measures only a paragraph starting `**OPEN`, so the 20,294-char heading grew uncapped while the capped paragraph is the one part a session never sees; a generated board cannot drift and a hand-written one has, three layers deep (§9.8).
Default if silent: a, START HERE keeping at most the derived queue plus one Now line.

**51. Where the "why" lives after the board is generated** (asks: K)
Context — three handoff files already exist (7.6 to 9.9 KB each) and session 23's own words are that the board and bundle carry the state while "this file carries what they cannot, why things are the way they are" (`docs/board/handoff-2026-09-09-session-23.md:8-11`), yet ritual step 7 still requires rewriting START HERE's Now paragraph every turn (`docs/runbooks/session.md:145-148`).
Question — is the per-session handoff the only hand-written narrative in the record?
a) yes: the handoff is the single prose artefact, ritual steps 6 and 7 collapse into writing it, and the board and log become generated.
b) keep the log entry as well (newest-first, 12 lines or fewer) and drop only the Now paragraph.
c) keep all three (handoff, log, Now paragraph).
**Recommend: a** — the handoff already states the division of labour correctly while the log has grown to 269 lines whose longest single line is 17,493 chars, and three overlapping prose surfaces defeat "a stranger can continue".
Default if silent: a.

**52. The trailer contradiction** (asks: K, C)
Context — `docs/board/policies.md:30-36` requires both a machine `Generated-By:` trailer and the plan's `Co-Authored-By:`, while `~/flakes/dsh-harness/AGENTS.md:45-46` requires "exactly ONE machine-set trailer and no `Co-Authored-By` line" (§9.14); the same mismatch produced a W6 MAJOR and the whole FIX5 to FIX7 chain, five rounds inside `factory-review`.
Question — which text is authoritative, and how does the machine learn it?
a) policies.md wins; AGENTS.md's commit section is generated from it, and `factory-review`'s trailer check reads that one file rather than a regex it carries.
b) AGENTS.md wins; drop `Co-Authored-By` from policy, CLAUDE.md and the plan templates.
c) both stay and the gate accepts either shape.
**Recommend: a** — the rule is stated in two repos with a third copy in the gate, which is why five fix rounds went on a one-line convention; one source the gate reads makes the contradiction unrepresentable.
Default if silent: a.

**53. The plan-file denial class** (asks: K, B)
Context — `house: plan-files` is the largest house denial in the record, 98 events over 32 distinct (run, key) pairs with one run hitting it 13 times (§3c), because guard rule 2 refuses any Bash command naming a path under `docs/superpowers/plans/` with a write verb (`tools/orchestrator-guard.sh:12-20`). The supported alternative is now genuinely read by the graph (`pkgs/evidence/tasks.py:1100-1104`), but the file's own header still says "Until OG2 lands, this file is documentation of intent" (`docs/ledger/task-status.toml:6-8`).
Question — does the redesign keep the plan-file rule as a denial, or give agents a supported verb instead?
a) keep the rule and add a verb (`plan-append`, `plan-withdraw`) the workflow calls, so the denial stops being the interface an agent discovers by retrying.
b) narrow rule 2 to deletions and heading edits, letting appends through bash.
c) keep it exactly as it is and fix only the stale header comment.
**Recommend: a** — 98 denials concentrated in a minority of runs is an agent guessing at a missing interface rather than a rule doing its job, and a named verb is discoverable where a refusal reason is not.
Default if silent: a, with the stale header fixed in the same task.

**54. Rules that disagree with the machine** (asks: K)
Context — three CLAUDE.md rules failed re-measurement: `CLAUDE.md:18-19` says nothing including `jq` is on the host PATH but `command -v jq` resolves; `CLAUDE.md:45` says `$HOME` is read-only under a harness sandbox but a subagent measured it writable; and the heredoc field lesson has no episode anywhere in the drive corpus (§9.1-9.3). The guard's rule count is stated three ways, three in `docs/runbooks/session.md:235`, four in its own list, five in the script header (§9.4).
Question — what happens to a rule whose re-measurement fails?
a) every load-bearing rule gets a check that fails the build when it stops being true, and a rule with no check and no measurement is deleted at the audit rather than date-stamped.
b) each rule carries a `measured: <date>` stamp and is re-verified at each program phase, none deleted.
c) fix these four by hand now and leave the general question open.
**Recommend: a** — four rule statements were measured false or unsupported in one gather and one disagrees with itself in the same file, and the standing preference is failing the build over documentation (`docs/brief.md:323-324`).
Default if silent: a, with the guard runbook section generated from the script header.

**55. The brief's standing and the phase numbering** (asks: K, A) [merged: rules-board-record, subsystems]
Context — `docs/brief.md` has exactly one commit, 2026-09-02, yet §4 instructs "Verify anything in Section 4 against the actual repo or docs before you write code that depends on it" (`:12-15`) and §9 lists six items to resolve before Phase 1; §7 requires each phase to end with a test the operator runs, phases 7 to 9 were never built, and `nixosModules/helm.nix:486-487` already invents a "Phase 10" the brief never defines.
Question — what is the brief's role in the redesign, and how is the new sequence numbered against §7?
a) §3 is re-ratified verbatim as the invariant set, §4, §7 and §9 are marked superseded in place, and the redesign's phases are numbered 1..N afresh with the delivered work recorded as history; the one-phase-at-a-time gate is kept verbatim.
b) continue the existing numbering as Phase 10+ and leave §7's unbuilt phases in place.
c) drop global numbering: each subsystem carries its own phases and acceptance tests, sequenced only by declared dependencies.
d) rewrite the brief whole as the redesign's spec.
**Recommend: a** — a seven-day-old §4 that demands its own re-verification and a §7 the program is about to replace cannot govern a redesign, while §3 has never been reopened and is the part called non-negotiable; the "test passed" gate is the part the operator owns and it survives unchanged.
Default if silent: a.

**56. What "landed" means** (asks: K, L)
Context — the graph calls a task landed iff its commit subject is in main's landed set or its chain root is (`pkgs/evidence/tasks.py:849-856`), with no state between `ran` and `landed`; three keys are `ran` with an approve verdict and no commit on main, SD11b and SD11c are approved and never integrated (§10 axis 10), and the board's log claims UI1 landed against a commit `git cat-file -t` cannot resolve (§9.6).
Question — how does the record learn that work landed?
a) add an `integrated` state plus a refusal: an approved key that is neither landed nor carrying a `task-status.toml` row after the wave closes fails the board check.
b) make `factory-integrate` run automatically on approve, so approved and landed cannot diverge.
c) leave the states as they are and close the three open keys by hand.
**Recommend: a** — the one measured divergence was written onto the board as "landed" and stood for days, and b moves a step toward the machine that the operator has kept.
Default if silent: a.

**57. The seat's permission mode** (asks: C, B)
Context — `DSH_PERMISSION_MODE` is the only lever and nothing in the seat path sets it, so every root session is born `workspace-write`/`ask`; one escalation cost four `allowed-once` prompts over 11m46s and did not survive a restart (§3a.1-5). The seat is meanwhile the more confined process on every kernel axis, `ProtectSystem=strict` with a six-entry allowlist, systemd and D-Bus sockets `InaccessiblePaths`, the guard mounted read-only (§3b).
Question — should the drive launch preset the seat's permission mode?
a) yes: the drive launch sets `danger-full-access`, and the kernel confinement plus the house guard remain the boundary.
b) yes but to `workspace-write` with a seat-side allowlist matching `.claude/settings.local.json`'s four entries.
c) no: leave the compiled-in default and pay the prompts.
**Recommend: a** — the prompts buy nothing a mount does not already enforce and cost up to twelve minutes of operator attention per restart while 56.1% of the drive session's clock was already idle.
Default if silent: a, job seats keeping the default.

**58. The seat's session ritual** (asks: C, K)
Context — none of the three Claude hooks has a seat counterpart, no SessionStart, no PreCompact, no Stop (§3b), so the board, evidence bundle and task brief reach the seat only when it fetches them, which it did at turn 2 and turn 17 of a 49-turn session. The operator has explicitly permitted changes to the harness files this program.
Question — does the seat get the session ritual?
a) all three hooks, running the same `tools/session-start.sh` and `tools/ritual.sh` scripts, as part of the harness rework.
b) SessionStart only: facts in, no Stop hook blocking a seat.
c) none: the driver script injects the facts at launch and the ritual stays orchestrator-side.
**Recommend: a** — the seat drives the factory and lands commits (14 in one day) yet is the only actor whose turn can end with an uncommitted review or a stale board, and the Stop hook is exactly that refusal.
Default if silent: a.

**59. Where the rules live after the flakes collapse** (asks: K, J)
Context — rule text is split across two gits, `CLAUDE.md` here and `AGENTS.md` in `~/flakes/dsh-harness` (`docs/ledger/repos.toml:23-24`), and AGENTS.md omits eight CLAUDE.md rules while contradicting a ninth (§3b); the seat has no memory surface at all and AGENTS.md forbids copying Claude's 20 memory files into a repo (`AGENTS.md:20-23`).
Question — after the collapse, where do the rules and the seat's durable memory live?
a) one rules source in this repo generates both CLAUDE.md and AGENTS.md (drift fails lint), and the seat's memory is a machine-local store outside every repo (under the evidence store), never a tracked file.
b) one rules file both harnesses read directly, no generation, and no seat memory.
c) keep the two files hand-maintained and reconcile them once at the audit.
**Recommend: a** — the two-file split produced the trailer contradiction and the eight missing rules and already survived one hand reconciliation, while a memory store off the tree keeps privacy first.
Default if silent: a.

**60. The ritual and single-pass agents** (asks: B, K)
Context — the reset ritual is ten ordered steps with three hooks and is defined as "what you run before any reset, compaction, `/new`, or a pause" (`docs/runbooks/session.md:112-118`), which presumes a long multi-turn session, while ask B is for agents that perform a single pass.
Question — who does the ritual apply to in the redesigned system?
a) the driver or orchestrator session only; a single-pass workflow agent has no ritual, its close-out is the artefact it returns, and the workflow commits and updates the record.
b) every agent, including single-pass ones, runs the derived half.
c) the ritual is retired entirely once the board is generated.
**Recommend: a** — steps 1 to 5 are commits and board regeneration, which an agent that never resets cannot meaningfully perform, and concentrating record-writing in one place is the same rule as "the queue is derived, never typed".
Default if silent: a.

## 6. Planning mechanics

**61. Shape of the plan-of-plans** (asks: L, F)
Context — the ask is for "a plan to batch plan all of these plans … ran via the seat", but `plan.js` takes one spec per invocation and writes one plan file per run (`.claude/workflows/plan.js:60-61`) and no batch verb exists anywhere (§7.1); the seat cannot invoke a Workflow, yet `factory-task` already prints a claude-rung launch line, records `<KEY>.escalate` and exits 4 without running (`tools/factory/seat/README.md`, Escalation).
Question — what is this phase's deliverable?
a) one typed program plan whose keys are "write subsystem spec S_i" and "run plan.js on S_i", so planning becomes graph work the seat dispatches and each plan.js key resolves to a claude rung the seat prints and Claude Code runs.
b) a written schedule only: N plan.js invocations run by hand, nothing typed into the graph.
c) a typed program plan for spec-writing only, with every plan.js run left as an operator step in the plan's `## Operator` section.
**Recommend: a** — the escalation mechanism already gives exactly the seat-drives/Claude-runs handoff asked for, and the queue is derived by `evidence tasks`, so untyped planning is invisible to the board.
Default if silent: a.

**62. Program spec size against the L refusal** (asks: L, A)
Context — both sizers refuse an L: `plan.js`'s target reader sizes by "S ≤ 1500, M ≤ 4000, L above (an L is refused: say so)" (`.claude/workflows/plan.js:218`) and `factory-plan.sh` exits 2 on "an L spec that must be split before a plan is written" (`tools/factory/seat/factory-plan.sh:29-32`). Every spec that produced a good plan is M or smaller; helm-home-design is 1,682 words and its plan scored 37/42 (§6a).
Question — how does a whole-system redesign enter the planning agent without tripping the L refusal?
a) a program charter that is never fed to plan.js (under `docs/concepts` or the board), plus one spec of size M or smaller per subsystem.
b) one L program spec with the L refusal waived for this program.
c) an M-sized spec-of-specs that names each subsystem spec by path and is itself planned.
**Recommend: a** — the L refusal is a build-time refusal in two independent tools, and waiving it would be the first hand-waived refusal in the pipeline.
Default if silent: a.

**63. Key namespace before any drafting** (asks: L, A)
Context — `pkgs/evidence/tasks.py:1634-1642` refuses the same key defined in two plans and `plan.js`'s Packet phase throws unless `tasks.py check` printed nothing (`.claude/workflows/plan.js:308`), so one duplicate key in a batch stops every other plan in the batch from drafting (§7.6). Prefixes already in use are HH, SP, SD, W, FIX, UI, BUG, OL, CX.
Question — how are the program's task keys namespaced?
a) a two-letter subsystem prefix reserved in the program plan's `## Global Constraints` before any subsystem plan is drafted.
b) each subsystem plan picks its own prefix and `tasks.py check` catches collisions after the fact.
c) one program prefix with a numeric block per subsystem (R1 to R99, R100 to R199, and so on).
**Recommend: a** — a collision discovered after drafting fails the next Packet phase for the whole batch rather than one plan, so the cheapest place to refuse is before the first draft.
Default if silent: a. (See item 41 for the existing keys the collapse renames.)

**64. Who drafts the subsystem plans** (asks: L, F)
Context — `tools/factory/seat/factory-plan.sh` composes a packet and lands a seat-written draft at `docs/reviews/plan-drafts/<date>-<name>-<model>.md`, but that directory does not exist, no `PLAN-*` run exists under `~/factory/runs`, and all 9 judgement files read `author: fable` or `author: hand`, so the seat-drafting path has never been exercised end to end. The only seat-vs-Fable data is n=1 on a different /30 rubric, GLM 28 > Kimi 26 > Fable 21 > Pro 20 (VOID) (`docs/reviews/2026-09-05-plan-writing-comparison.md:106`), and the judge refused to write a routing row on it.
Question — who writes the subsystem plan drafts in this program?
a) Fable in plan.js for every subsystem plan.
b) the seat via `factory-plan.sh` for every subsystem plan, judged by `plan.js judgeOnly`.
c) an A/B on the program's first subsystem: one Fable draft and one seat draft of the same spec, both judged blind, then the winner drafts the rest.
**Recommend: a** — the ask says "batched fable 5.1 plans", read literally; the seat-drafting path is built and never run, so a seat-vs-Fable A/B is a measurement task the program can type later, not the path the program’s own plans wait on.
Default if silent: a.

**65. Who writes the subsystem specs** (asks: L, K)
Context — CLAUDE.md says "The orchestrator writes plans, specs, decisions, concepts and runbooks; agents write and review all code", which makes 8 to 10 subsystem specs a Fable-only workload, while the operator's 2026-09-08 direction was to push reads, probes and drafts to Sonnet/Haiku agents so Fable keeps decisions and commits. Spec review stays the operator's by type (`docs/board/operator-model.md`).
Question — who drafts the subsystem specs?
a) Fable writes each spec, as CLAUDE.md says today.
b) an Opus agent drafts each spec from the charter, Fable edits and signs, the operator reviews, with CLAUDE.md’s authorship rule amended for this program.
c) the seat drafts the specs the way `factory-plan.sh` drafts plans.
**Recommend: b** — every rule is being reconsidered and the measured cost of Fable authorship is context rather than quality (the packet’s 32 reader files were Sonnet-written); design drafting goes to Opus, the reviewing tier, and the CLAUDE.md amendment is named rather than implied.
Default if silent: b.

**66. What one increment is** (asks: F, L)
Context — the ask is for planning phases that are "incremental and part of the workflow"; today a plan lands as one dispatch of waves gated by the operator's "test passed" (brief §7), and only 43.9% of the drive session's 20,315s was turn-active compute, with 56.1% idle between turns (§2e.16).
Question — what is one increment of this program?
a) planning-only: an increment produces N specs and N plans, and code lands in later increments.
b) end-to-end: an increment is one subsystem's spec, plan, dispatch, land and operator acceptance.
c) staggered: increment i plans subsystem i+1 while dispatching subsystem i's waves.
**Recommend: c** — more than half the drive session's clock was idle waiting, so planning fits inside dispatch wall time at no extra elapsed cost while one operator sign-off per increment still holds the phase gate.
Default if silent: c.

**67. How wide an increment is** (asks: F, L)
Context — `FACTORY_JOBS` caps one wave at 5 (`tools/factory/seat/factory-wave:138`) and nothing caps two waves; maximum simultaneous seat units ever observed is 5, for 4m23s, against 24 uncapped CPUs and 125 GiB (§4f.24, §4f.22). First-gate approval is 80/160 (§4b.10), so roughly half of any wave returns a fix round.
Question — how many subsystems go into one increment?
a) 1. b) 3. c) 5. d) as many as the graph's waves allow.
**Recommend: b** — a 3-wide increment leaves headroom under the 5-job cap for the fix rounds a 50% first-gate rate guarantees, instead of a full wave that immediately oversubscribes on rework.
Default if silent: b.

**68. Increment 0: closing the record first** (asks: L, K) [merged: planning-mechanics, rules-board-record]
Context — six plans carry open work, each stuck differently (§6a), and beside them sit 9 orphan `.result` files and 1,673 un-ingested broker rows worth $42.48 (§4d.17, §4d.20); a repo-wide grep finds timers only for `helm-flake-check` and `protonBackup`, so nothing anywhere invokes `evidence ingest`, and the board's OPEN paragraph still describes this as "266 rows there against 108" (`docs/OPERATIONS.md:40`).
Question — does the program open with a closeout increment before it adds anything to the record?
a) yes, a full closeout: nothing new is drafted until the six plans are folded or closed and the ingest is run.
b) no: fold the six into the new subsystem plans as they are drafted.
c) split: close the four mechanical ones now (UI1 fast-forward, SD11b/c integrate, a W6 fix round, the broker-secret row), fold helm-home-1 into the Helm subsystem plan, retire the comparison keys with a `task-status.toml` row, and make the ingest timer plus backfill task one.
**Recommend: c** — four of the six are one command or one fix round from closed while helm-home-1's ten keys genuinely belong inside the reworked Helm plan, and a program whose purpose includes spend telemetry cannot measure itself against a store missing $42.48; hand-running the ingest has already been shown not to stick.
Default if silent: c.

**69. What the seat is allowed to run in the program** (asks: L)
Context — driving authority is already delegated for brief, dispatch, gate, integrate and switch-prep on the seat's own judgment, with rung-3 re-plans, pauses, spend and routing rows reserved to the operator (§8.1); the seat has no SessionStart, PreCompact or Stop hook and no memory (§3b) but fetched the board and the bundle by hand at turns 2 and 17.
Question — does the seat drive this program's planning batch: dispatching the spec-writing keys, printing the claude-rung plan.js lines, integrating the drafts?
a) yes, the whole batch; Claude Code is entered only for the plan.js runs the seat prints.
b) no: the seat drives code tasks only and Claude Code drives everything on the planning side.
c) yes, but only after the seat gets a SessionStart equivalent injecting the board, the bundle and the brief.
**Recommend: a** — the delegation decision already covers dispatch, gate and integrate, and the seat's measured failure mode was state that outlives a turn rather than planning judgement.
Default if silent: a. (Item 58 decides the hooks independently.)

**70. Acceptance per increment, and who signs it** (asks: L, F)
Context — the operator owns "test passed" and phases are gated one at a time (`docs/board/operator-model.md`; brief §7), while each plan already carries its own `## Operator` section with acceptance and rollback (planning-agent-design §3 Step 5), so a 3-wide increment would otherwise cost three separate sign-offs.
Question — what does the operator sign off per increment?
a) one acceptance drill per subsystem plan, run at the end of the increment.
b) one composed acceptance drill per increment, assembled by the program plan from each subsystem's `## Operator` section.
c) sign-off only at a switch boundary, not per increment.
**Recommend: b** — one drill per increment preserves one-phase-at-a-time without turning a 3-plan increment into three gates, and the composition is mechanical because each `## Operator` section is already one command per step.
Default if silent: b.

**71. A ceiling for the program, and in what unit** (asks: L)
Context — dollars exist for six hours of one day and are 21.5% ingested, and every figure before 2026-09-09 11:53Z is unrecoverable because the broker did not log cost (§4d.17-19); token volume is complete for the whole window from each `.result`'s own `usage:` line, 200.7M in, 20.1M out, 1.92B cache-read over 334 runs (§4d.21), while the Claude-side "$35.59" traces to one board transcription (§11 Q9).
Question — does the program carry a per-increment budget ceiling, and in what unit?
a) a dollar ceiling per increment.
b) no ceiling: land the ingest and the OTel tasks first, measure an increment, then set one.
c) a token ceiling per increment now, tightened to dollars once the ingest lands.
**Recommend: c** — tokens are the only series measured across the whole record while a dollar ceiling today would be an invented number over a 21.5%-ingested stream, and spend is operator-owned, so the number is one the operator sets.
Default if silent: c.

**72. A refusal for two concurrent waves** (asks: L, E)
Context — `FACTORY_JOBS` caps one `factory-wave` call at 5 and there is no cross-wave or cross-plan cap anywhere (§7.9); `seat-submit.py` refuses only on argument and path validation, with no refusal keyed on how many units are already running (§4f.25), and the drive seat submitted FIX6 and HH1 0.53s apart (§2d.9).
Question — does the program add a deterministic cap on concurrent seat units?
a) yes: a typed task makes `seat-submit` refuse a launch above a configured running-unit count.
b) no: max observed concurrency is 5 against 24 uncapped CPUs and 125 GiB, so the ceiling is not binding.
c) yes, but in `factory-dispatch` rather than `seat-submit`, so hand launches stay unbounded.
**Recommend: a** — a batch of increments is the first workload that can plausibly fire two waves at once, and `seat-submit` is the one chokepoint every launch already crosses.
Default if silent: a.

**73. A rejected plan mid-increment** (asks: L, F, G)
Context — first-gate approval is 80/160 and re-plan approval is 16/29 (§4b.10); rule A1 makes a re-plan rung 3 and rung-3 re-plans are reserved to the operator (§8.1), while `plan.js`'s replan mode refuses any draft that loses a prior `### ` heading (`.claude/workflows/plan.js:411`).
Question — what happens when one subsystem's plan or task is rejected mid-increment?
a) the increment stalls until the operator dispatches the rung-3 re-plan.
b) the increment continues, the rejected subsystem drops out, and its re-plan is queued as its own item in the next increment.
c) the driver may run the re-plan itself at rung 2 without the operator.
**Recommend: b** — half of all first gates reject, so an increment that stalls on any rejection stalls about half the time, while c would take a decision the operator has explicitly reserved.
Default if silent: b.

**74. The program's first tasks, in order** (asks: L, A) [merged: planning-mechanics, subsystems]
Context — nothing can be drafted while the graph is unsound because `plan.js`'s Packet phase throws unless `tasks.py check` prints nothing (`.claude/workflows/plan.js:308`), and the record carries six open plans, 9 orphan results and 1,673 un-ingested broker rows (§6a, §4d); meanwhile the only increment whose acceptance is a build and an empty closure diff is the subsystem manifest plus its assertion, which touches no running unit.
Question — what are the program's first tasks and in what order?
a) closeout and ingest, then the program charter, then the reserved key namespace, then the subsystem manifest and assertion as the first code increment.
b) charter, subsystem spec 1, plan.js on it, with the record closed later.
c) the repo and flake collapse first, so everything after happens in one tree.
d) the Helm rework first, because it is the surface the operator sees.
**Recommend: a** — a duplicate key or an unsound graph refuses the whole batch's first Packet phase, so the namespace and the record must be clean before any drafting, and the manifest is the only code increment that lands without a switch.
Default if silent: a.

## 7. The six leftover plans

**75. UI1 sits on a branch main cannot see** (asks: L, K) [packet §11 Q1]
Context — UI1's implement run is `done`, its review `approve`, and its head commit `4bc3407` is not on `main`; it exists in `~/factory/base/nixos-agent-env` as `integ/ui1` and `task/UI1` only, while the board log says it landed and `git cat-file -t 4bc3407` finds no such object in the live repo (§6a).
Question — fast-forward it, re-run it, or withdraw it?
a) fast-forward `integ/ui1` into main after re-running its checks on the current HEAD.
b) re-run UI1 from its task section against today's tree.
c) withdraw it with a `task-status.toml` row and let the bug re-enter through the new bug ledger.
**Recommend: a** — the work is done and reviewed, only the integrate step is missing, which is the cheapest of the three and the one that makes the board's existing claim true.
Default if silent: a, with the board's log line corrected in the same commit.

**76. SD11b and SD11c approved and never integrated** (asks: L, J) [packet §11 Q2]
Context — SD11b and SD11c are the brief's `approved: 2`, while SD11's landing happened in `~/flakes/dsh-harness` (`d1b5f85`) where the key is literally named `SD11`, so the board's "SD11c in dsh-harness" phrasing matches neither repo's derived key names (§6a).
Question — integrate them, or mark them closed given SD11 landed in dsh-harness under a different key name?
a) integrate both into their repo and let the graph mark them landed.
b) close both with a `task-status.toml` row citing `d1b5f85` as the landing.
c) re-key them to match the dsh-harness name and re-derive.
**Recommend: a** — approved work that never integrates is the exact divergence item 56 adds a refusal for, and integrating costs one command each while a status row records a claim the graph cannot verify.
Default if silent: a, falling back to b if the diffs no longer apply.

**77. W6 is rework with no fix round** (asks: I, L) [packet §11 Q3]
Context — W6's implement run is `done` (commit `4be9ef1`) but its gate returned `rework` on 3 MAJOR and 2 minor, and no W6 fix round exists anywhere (`find ~/factory/runs -iname '*W6b*'` returns nothing); one of the three findings, the phantom `comfy-worlds-vm` check, has since become real via W4 (`74f7341` in `~/flakes/media`) (§6a).
Question — re-gate as-is, or type a W6 fix round?
a) type a W6 fix round covering the two findings that still stand (the trailer model name, the extra `Co-Authored-By`) and re-gate.
b) re-gate as-is and let the reviewer see that the phantom check is now real.
c) withdraw W6 and fold its content into the feed sub-project plan (item 15).
**Recommend: a** — one of three MAJORs has expired and the other two are one-line commit-message defects, so a fix round is cheap and it also unblocks the feed work item 15 recommends planning next.
Default if silent: a, gated after item 52 settles which trailer rule is authoritative.

**78. HH1 rework and HH2 to HH4 never dispatched** (asks: C, H, L) [packet §11 Q4]
Context — HH1 is `rework` on a real D-Bus arity defect no test catches (`pkgs/helm-home/probe.py:116`, a 1-arg signature while `BindShortcuts` is called with 4), and HH2, HH3 and HH4 were named in HH1's dispatch group but never dispatched, with no job id and no run dir for any of the three (§6a).
Question — re-dispatch wave 1 whole, or fix HH1 first?
a) fix HH1 first (its fix round writes the failing test the gate found missing), then dispatch HH2 to HH4 as one wave.
b) re-dispatch all four at once, HH1's fix included.
c) dispatch HH2 alone, since it is the key that closes `uid1000-can-switch-profile`, and hold the rest for the Helm re-spec.
**Recommend: a** — HH5 and HH6 both depend on HH1, so a wave dispatched over an unfixed HH1 rebuilds on a known defect; a is also what item 9's wave-1-then-supersede answer needs.
Default if silent: a.

**79. The plan-writing comparison keys read `ran` forever** (asks: L, K) [packet §11 Q5]
Context — the comparison did run and was judged, with a 113-line review plus three arm outputs and `.result` files for all three arms, but its keys stay `ran` because a read-only comparison arm never integrates and nothing marks it landed or withdrawn; the judge declined to write a `routing.toml` row on n=1 (§6a).
Question — add a `task-status.toml` row, or leave them?
a) add a withdrawn or closed row per key citing the review file, so the graph stops carrying three permanently open keys.
b) leave them; the state is honest because nothing landed.
c) re-run the comparison at n≥3 specs and 2 judges, as the judge asked, and close the keys with that result.
**Recommend: a** — three keys that can never change state are dead text in every derived brief, and item 64's A/B is the cheaper way to get the measurement the judge wanted.
Default if silent: a.

**80. `2026-09-03-broker-secret-ownership.md` open since 09-03** (asks: K, L) [packet §11 Q6]
Context — the row's own note is its only blocker, "field bug L1 plan filed 2026-09-03; closure not recorded on the board", and it is the graph's oldest open legacy row (§6a).
Question — close the row, or re-open the work?
a) close it with the closure evidence written into `plan-status.toml`, after one command confirms the broker secret's ownership on the live host.
b) close it on the note alone.
c) re-open the work as a task in the Isolation subsystem.
**Recommend: a** — the record's rule is that unmeasured is debt, and a one-command check is cheaper than either carrying the row another week or re-planning work that was probably done.
Default if silent: a.

## 8. Not asked

Packet §11 questions no finder refined; each still wants a word from the operator.

- **§11 Q8 [spend]** Is the fresh OpenRouter activity export to price 09-06..09-08 still wanted, given every dollar before 2026-09-09 11:53Z is unrecoverable?
- **§11 Q9 [unverifiable]** Should the Claude-side spend be measured before the batch sizes itself? Item 71 sets the unit; this asks whether to close `claude-weekly-limit-unmeasured` first.
- **§11 Q10 [unverifiable]** The `.msg-ui1.txt` guard refusal does not reproduce against the current tree's guard. Worth chasing with someone who can read the store-pinned guard the running unit loaded, or accept it as unexplained?
- **§11 Q13 [decision]** Should the dsh spill path be fixed before the seat drives a batch (a read-only `/tmp` killed one launch)?
- **§11 Q14 [decision]** The seat ran at `xhigh` for four hours against a saved `medium` and a `verified` claim naming medium. Pin it, measure it, or leave it self-selecting?
- **§11 Q15 [unverifiable]** ~9h 11m of the drive unit's life (04:35:39 to the first commit at 13:46:48) is not recoverable from any artefact. Accept the gap, or add the run-state record that would prevent the next one?
- **§11 Q16 [decision]** `docs/OPERATIONS.md`'s "Held for the operator" list still names switch #21 though switches #22 to #26 have run. Is it current, or dead text the rewrite discipline missed?
