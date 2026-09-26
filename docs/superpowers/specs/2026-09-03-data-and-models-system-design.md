# Data and models — how this system gathers, analyzes, stores and uses its data (rev 1, assessment)

**Status:** planner's assessment for the operator (2026-09-03), written after a
read-only fan-out over the brief, the strategy program (`~/strategy`), the
telemetry actually on disk, and the model research. Fixed constraint from the
operator: **Fable stays the planner.** Decisions for the operator are listed
in §9. Upstream facts about OpenRouter and DeepSeek come from the dated
digest `docs/research-2026-09-03-openrouter-deepseek.md` (23/24 claims
re-verified by a skeptic); remaining unknowns are marked UNVERIFIED there.

## 1. What exists today (measured, not assumed)

**Designed but not live** (strategy Deliverable 3, 2026-09-02): a GPU
utilisation logger (60 s CSV → weekly rollup → Helm tile), ledgers
(`~/strategy/ledger/{tokens,tasks,income}.csv`), a weekly review written by
Sonnet from the rollups, a queue runner ("Forge") with lane tags
(`claude-sonnet | claude-opus-review | local | gpu-media`), local models under
llama-swap (Qwen3.8-27B Q6_K mechanical, Qwen3-Coder-30B-A3B bulk,
Hermes-4-14B small), Fable capped at ≤ 10 % of factory tokens. MEASURE.md's
ten operator measurements (M1–M10) are all unfilled. Phase 5 (the model
router: Bifrost over llama-swap) is not built. No cheap cloud model appears
anywhere in the corpus; the cheap lane was designed all-local.

**Live but unread** — the richest source on the machine:

| source | where | what it holds | state |
|---|---|---|---|
| factory agent transcripts | `~/.claude/projects/<slug>/<session>/subagents/workflows/<wf>/agent-*.jsonl` (mode 600) | per turn: exact model id, input / cache-write / cache-read / output / thinking tokens, timestamps, tool calls | kept forever, never aggregated |
| workflow journals | same dir, `journal.jsonl` | every agent's structured return: review findings with severity and file, verify results, fix rounds | kept forever, never indexed |
| dark-factory return value | Workflow tool output only | agents, output tokens, per-task rounds and status | ephemeral; hand-copied to the board as prose |
| broker audit | `/var/lib/egress-broker/<i>/audit.jsonl` (0644) | one line per flow: host, SNI, bytes, verdict, reason | append-only, no rotation, no rollup |
| Helm status | `/var/lib/helm/status.json` | nine tiles with detail | overwritten every 5 min, no history |
| backup parity | journald line from `push.sh` | OK/FAIL + counts | no structured state file |
| board economics | `docs/OPERATIONS.md` prose | "22 agents, ~2.05M tokens, 105 min, 2 rounds" | hand-transcribed after the fact |

Consequence: every economics number this project has quoted was written by
hand from a number that existed exactly once, in a tool result. The exact
figures are on disk for every run and have never been read.

## 2. Principles (derived from the brief, restated for data)

1. **Deterministic work is a script, not a model.** Collecting, joining,
   counting and rolling up are done by tested Python in a devShell. A model
   that does arithmetic on logs is waste and noise. Models get the work that
   is bounded but not deterministic: summarising, classifying, drafting,
   triaging.
2. **Raw stays local, rollups travel.** Raw transcripts, audit logs and Helm
   history never leave the machine. What a remote model may see is a rollup
   or a transcript excerpt whose classification allows it (§5).
3. **Append-only, one file per source per month, JSONL with a schema
   version.** No database until a question needs one; DuckDB over the JSONL
   in the devShell when it does. Volumes are small (a factory run is a few
   KB of ledger).
4. **The planner reads rollups, never raw data.** Fable's inputs are the
   weekly review, the ledgers' last lines and the board — a few thousand
   tokens. Decisions cite the metric they rest on and are appended to
   `docs/decisions/`.
5. **Policy is Nix** (invariant 5): which data class may reach which model
   is a table in the flake, enforced by the broker's allowlists and the
   classification assertions, not by a script's good behaviour.
6. **Credentials are injected at the chokepoint** (invariants 2 and 3): no
   agent, script or lane process holds a provider key; the broker adds the
   header for the exact host.

## 3. Gather — sources and the events they emit

| source | mechanism | event (one JSONL line) | owner |
|---|---|---|---|
| factory runs | `tools/ledger/factory.py` parses a workflow dir after each run (and backfills every past run on disk) | run: plan, tasks, per-task status/rounds/commit; agent: role, model id, tokens by kind, wall clock, tool calls; finding: severity, class, file, task, round | this repo (T1 below) |
| Helm | `collect.py` appends each collection's tiles to `/var/lib/helm/history.jsonl` (monthly rotation) | tile: name, status, summary, checked_at | Helm v1 factory (one task) |
| broker | nightly `broker-rollup` script over `audit.jsonl`; monthly rotation of the raw file | day × instance × host × verdict → count, bytes | wiring round 2 (one task) |
| backups | `push.sh` writes `/var/lib/proton-backup/state.jsonl` (OK/FAIL, counts, rail trips) | run: verdict, local/remote counts, reason | small Lane F follow-up |
| GPU | `gpu-log.timer` (Deliverable 3) — 60 s CSV | ts, util, mem, power | strategy build |
| evals | `evals/results/<date>.json` (NixOS-skill spec §9) | run: task, arm, model, pass, tokens, time | nixos-skill factory |
| operator | MEASURE.md answers; weekly `ledger/income.csv` row | as designed | operator |

The factory ledger comes first: it is deterministic, its data already exists
for every run since 2026-09-02, and it answers the questions the board keeps
asking (tokens per role, fix rounds per defect class, wall clock per task).
It also makes MEASURE.md's M7 (Claude plan usage) measurable from our side.

## 4. Store

`~/strategy/ledger/` (already designated by Deliverable 3, already in the
nightly restic paths): `factory-runs.jsonl`, `factory-agents.jsonl`,
`factory-findings.jsonl`, `helm-history/`, `broker-rollups/`, `evals/`,
`gpu/`. Not git-tracked (they are data, not source); the schemas and the
scripts are tracked in this repo under `tools/ledger/` with unit tests. Each
line carries `v` (schema version) and `src` (path of the raw artifact it was
derived from) so any number can be traced back.

## 5. Classification of the data itself (proposed; decision §9.2)

The brief classifies baskets; the telemetry needs the same treatment because
it will be the input to remote models.

| data | class | may be processed by |
|---|---|---|
| factory transcripts and journals of **this** repo and the flakes (contain source and docs already sent to Anthropic) | `permitted` for Anthropic today; **`permitted` for OpenRouter/DeepSeek only if the operator says so (§9.2)** | scripts; Claude; the OpenRouter lane if permitted |
| rollups (counts, token totals, pass rates, durations) | `permitted` | anything, through the broker |
| Helm history, broker audit, backup state (hostnames, paths, denied hosts: the machine's operational fingerprint) | `local-only` | scripts; local models only |
| Claude memory directories, baskets, `~/strategy` income and economics | `local-only` (already decided) | scripts; local models only |
| eval seeds and results | `permitted` | anything |

## 6. Analyze — two tiers

**Tier A, deterministic (scripts, tested, offline):** the ledger extractor;
weekly rollups (tokens per role and lane, fix rounds per defect class, Opus
finding classes, eval deltas, GPU idle %, broker denies by host); the
proving-grounds report; Helm's history tile. This is most of "data
collection and deterministic task work". No model is involved, and the
operator's plan to spend a cheap model on it would be spending on the wrong
thing: the model belongs in Tier B.

**Tier B, bounded non-deterministic (cheap model):** summarise a run's
transcripts into a narrative the board can quote; classify findings into
defect classes (PATH-in-unit, merge semantics, hardening gap, test strength,
docs) for the rollups; draft the weekly review from the rollups; triage a
failing check's log to a one-line cause; caption and keyword media output;
first-pass docs drafts for the docs reviewer. Executor by data class: a
remote cheap model for `permitted` inputs (the operator's OpenRouter choice),
a local model under llama-swap for `local-only` inputs. Every Tier B output
is checked by a Tier A rule where one exists (a summary must cite run ids
that exist; a classification must be one of the enumerated classes) and is
labelled with the model that produced it.

**Tier C, judgement (fixed):** Fable plans, specifies, judges gates and
writes decisions; Opus holds the code-review gate; Sonnet implements. Any
change to Tier C assignments is made only on proving-grounds evidence
(`concept-2026-09-02h`), never on price.

## 7. Use — the loops that consume the data

- **Session start:** the planner reads the last weekly review and the ledger
  tails through memory and the board (≤ 3k tokens), not the transcripts.
- **Factory close:** the ledger extractor runs; the board's economics line is
  generated from it, not typed.
- **Weekly (Sun 09:30, Deliverable 3):** Tier A rollups → Tier B review draft
  → operator reads → planner appends any decision with its metric.
- **Routing feedback (Deliverable 3 §10, kept):** lane pass rates and token
  shares adjust queue depth and lane assignment; Fable's share > 10 % of
  factory tokens is a policy breach the ledger now detects automatically.
- **Experiments:** any "would X help" question becomes a proving-grounds
  matrix on identical seeds (the NixOS skill is the first; code graph vs RAG
  is queued).

## 8. The OpenRouter lane (operator decision 2026-09-03; facts from `docs/research-2026-09-03-openrouter-deepseek.md`)

The operator holds an OpenRouter API key and will run DeepSeek V4 Flash
(`deepseek/deepseek-v4-flash`, the dated 0423 snapshot; $0.0679 in /
$0.168 out per million tokens on OpenRouter, 1M context, tools and JSON-
schema outputs) for Tier B work. Design, consistent with the invariants:

- **Egress:** a broker instance `openrouter` with `allow = [ "openrouter.ai" ]`
  (the only host both API surfaces use); every request audited; nothing else
  reachable from that namespace. A live capture at bring-up confirms no side
  connections.
- **Credential:** the key lives in Proton Pass (vault of record). On the
  machine: one file `/var/lib/secrets/openrouter-key`, created root-only by
  the operator (procedure given 2026-09-03), set to `0440 root:egress-broker`
  by the lane module's tmpfiles rule at switch time, outside every repo and
  backup path, read only by the broker, which injects `Authorization: Bearer`
  for the exact host and overwrites whatever the client sent. No lane
  process, script or agent ever sees the key; the audit and the ledger show
  which lane spent what.
- **Data policy:** every request body carries
  `provider: { zdr: true, data_collection: "deny" }` and, once read from
  `GET /api/v1/endpoints/zdr` at bring-up, an explicit provider allowlist;
  the account-level zero-data-retention toggle for the Non-frontier group
  and the training opt-out are set by the operator and recorded in the
  runbook with the date. OpenRouter itself does not train on or retain text
  beyond routing (policy dated 2026-08-31); the provider's copy is governed
  by ZDR.
- **Classification:** the lane accepts only inputs classed `permitted` under
  §5; `local-only` inputs are refused at build time by the same assertion
  shape as `mkAgent` (a lane is an agent with an egress class).
- **Client:** a small tested CLI in this repo (`tools/lane/openrouter.py`,
  OpenAI-compatible chat completions at `/api/v1/chat/completions`,
  JSON-schema outputs, retries, cost accounting into the ledger) used by Tier
  B jobs through the broker (`HTTPS_PROXY` + the broker CA). Claude Code can
  also be pointed at OpenRouter's Anthropic-compatible surface
  (`ANTHROPIC_BASE_URL=https://openrouter.ai/api`, a dummy
  `ANTHROPIC_AUTH_TOKEN` the broker overwrites) when a proving-grounds
  experiment wants DeepSeek as an implementer; that is an experiment, not a
  requirement. Bifrost is not in nixpkgs; when Phase 5 lands, the lane moves
  behind it unchanged.
- **Measurement before trust:** the first Tier B jobs (findings
  classification, run summaries) run in shadow for two weeks: outputs are
  stored and compared with Tier A truth where it exists and with a Sonnet
  sample; the lane graduates on measured agreement, logged on the board.
- **Cost bound:** a per-key spend cap set on OpenRouter (`GET /api/v1/key`
  exposes it) plus the ledger's per-lane accounting.

## 9. Decisions for the operator

1. **Build order** (proposed): T1 factory ledger extractor + backfill (this
   repo, deterministic, one factory task) → T2 OpenRouter lane (broker
   instance, key file, client, shadow jobs) once the key exists and the
   digest is in → T3 Helm history / broker rollup / backup state (folded into
   Helm v1 and wiring round 2 as one task each) → T4 GPU logger + weekly
   review timer (Deliverable 3's deterministic parts) → Phase 5 router.
2. **Classification of this repo's transcripts for OpenRouter/DeepSeek**
   (§5): permitted, or Anthropic-only? The brief forbids GitHub, Google and
   Microsoft by name and routes `permitted` data to "the frontier endpoint";
   a second remote endpoint is within the design but is a new recipient of
   source code and docs. My recommendation: permitted, with ZDR routing, for
   this repo and the flakes; never for memory, baskets, strategy economics or
   operational telemetry.
3. **Secrets of record:** Proton Pass for every provider key and the restic
   password (already there); on-machine copies only as root-owned files read
   by the broker; the runbook lists each file, its mode and its consumer.
4. **Fable's inputs:** rollups and reviews only; raw transcripts are read by
   Tier B or by a Sonnet Explore agent on request.
5. **What the cheap model is for:** Tier B only. Deterministic work stays
   scripts. Agree?

## 10. Costs and risks

- T1 is small (one script, tests, backfill) and pays immediately: the next
  board line is generated, and M7 becomes measurable.
- The OpenRouter lane's cost is bounded by the ledger (per-lane token
  accounting) and by the broker (only that host); its risk is the data
  recipient, which is why §9.2 is an explicit decision and shadow mode comes
  first.
- Local-only telemetry needs a local model for Tier B work on it, which
  needs Phase 5 (or a llama-swap slot without the router first). Until then,
  Tier B on local-only data is Sonnet-by-request or nothing.
- Raw audit logs grow unbounded today; rotation is part of T3.
