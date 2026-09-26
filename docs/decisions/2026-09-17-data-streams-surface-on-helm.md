# Data streams surface on the Helm (2026-09-17)

Taken by the orchestrator on the operator's word in session 30 — "any data streams need to be on the helm, thats the dashboard" — answering the standalone spend-dashboard the orchestrator had offered an hour earlier. The offer is withdrawn by this decision.

## Decision 1 — the Helm is the only dashboard

A stream under `/var/lib/evidence` reaches the operator through the Helm: a collector tile (`GET /v1/status`), a Home section fed by its own route (`GET /`), or both. No standalone HTML page, no `data:build-dashboard` artifact, no generated report file stands in for that. A chart written to answer a question in a session is scratch and dies with the session; anything worth looking at twice is a Helm surface.

Why: the Helm is already the one screen with the host's state on it, it is reachable at 7710 without a session, and it is where the operator looks. A second dashboard would be a second place to look, stale the day after it was generated, and outside every check that holds the Helm's contract.

This binds the `evidence-store` skill (`.claude/skills/evidence-store/`): its chart section names the Helm as the destination and `data:build-dashboard` as out of scope for anything durable.

## Decision 2 — the measured gap, and what it means

Six streams exist on disk. Their Helm face today, measured 2026-09-17:

| stream | Helm face |
|---|---|
| `helm-status` | it *is* the tile stream — written by `collect.py`, read back for `change` vs `heartbeat` |
| `derived/tasks` | `GET /v1/tasks` via `pkgs/evidence/tasks.py`, rendered in Home |
| `ledger/engagement` | Helm writes it (`POST /v1/engage`); read by the orchestrator, not rendered — see Amendment 1 |
| `checks` | indirect only — the `flake-check` tile reads the head/file seam, never the stream |
| `derived/gates` | **none** |
| `ledger/openrouter-usage` | **none** |

So the two streams carrying the answers the operator asks for most — what it cost, and what the reviews actually caught — have no Helm face at all. The nine collector tiles are all host probes; not one is fed by an evidence stream.

That is the gap this decision opens as work. It does not schedule it: no key is dispatched here, and the implementation hold from `docs/decisions/2026-09-17-session-effort-medium.md` stands.

## Decision 3 — a spend surface needs its number first

A spend tile is not specified by this decision, because a tile states a verdict — `ok|warn|fail` — and nothing in the record says what makes spend `warn`. The measured facts are $722.76 on the OpenRouter lane since 2026-09-09, one instance, 56 % of it in one model; the missing facts are the budget line and the period it runs over. The number comes from the operator before the tile is planned.

Why: a tile with an invented threshold makes an arbitrary number look measured — the failure the operator named as the root cause on 2026-09-16, choices without measurable goals. (That is the operator's spoken word, recorded in the orchestrator's memory; it has no document in `docs/concepts/`, and an earlier revision of this line cited one that does not exist.) Until then the spend question is answered by query, through the `evidence-store` skill.

Open, for the operator: the budget line and its period (monthly cap? per-run burn?), and whether Claude-side spend must be in the same number — `ledger/otel-claude` is declared in `pkgs/evidence/SCHEMA.md` but absent on disk, so any total today is the OpenRouter lane only.

## Amendment 1 — a stream has a reader, and it is not always the operator (2026-09-17)

On the operator's correction the same session: "engagement is more for you to analyze not me". Decision 1 said a stream reaches *the operator* through the Helm; that is the rule for one class of stream, not all of them. Streams split by reader:

- **Operator-facing** — `helm-status`, `checks`, `derived/tasks`, `derived/gates`, `ledger/openrouter-usage`. The operator acts on these, so Decision 1 binds: a tile or a Home section, never a separate page.
- **Orchestrator-facing** — `ledger/engagement`. Its reader is the orchestrator, analysing whether what gets built is used. It is written by the surfaces and read at planning time; it is **not** a tile, and its absence from the Helm is correct, not a gap. Rendering it back would put the operator in the position of watching their own usage, which measures nothing.

The frame this sits in, in the operator's words: Claude Code is the backend of an operating system that is built as its user needs it. Engagement is how that loop is measured — "having the user engaged is important, it means that we are making things people like". It is the product-fitness signal for the Helm Home program, so it is planning input, not a dashboard tile.

**What it is worth today, measured 2026-09-17:** two rows, both `surface='feed'` — `opens` 2 on 09-16 and 7 on 09-17, with `dwell_s` and `feed_likes` **0 in both**. Three facts follow, and all three are about emitters, not about the stream:

1. `surface='home'` has never been written, though `pkgs/helm/api_home.py` posts exactly that on load. The route accepts `text/plain` and would have taken it, and the feed's rows prove the path works — so Helm Home has not been opened in a browser since HM8 landed, or its beacon does not reach the route. Worth one probe before any conclusion.
2. `dwell_s` has no emitter but Home's `pagehide` handler, so no dwell has ever been recorded anywhere.
3. `feed_likes` has no emitter at all — no like affordance is wired to the feed.

So the signal is 9 opens on one surface. That is not yet analysable, and the orchestrator will not infer product fitness from it. What would make it analysable is emitters, not schema: Home reaching a browser, dwell landing, and a like affordance on the feed. Those are Helm-program work, not evidence work.
