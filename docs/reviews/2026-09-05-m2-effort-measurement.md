# M2 — reasoning-effort measurement (2026-09-05)

**The measurement is void: both runs sent `medium`.**

| run | effort sent (wire) | input | output | reasoning tok | reasoning chunks | sec | verdict | notable |
|---|---|---|---|---|---|---|---|---|
| `task/M2off` (6827c29) | **medium** (not off) | 124061 | 8502 | 0 reported | 176 (37,237 ch) | 113 | **approve** | bold mini-heading matches file style; 16 lines; real commit body; demotes the `**Unmeasured (dated debt …)**` marker; drops the catalog URL |
| `task/M2med` (76c55df) | medium | 147983 | 11139 | 0 reported | 264 (57,346 ch) | 139 | **rework** | first-ever `###` in lanes.md (10 `##`, zero `###`; seat section uses `**Bold.**` leads); empty commit body; keeps the debt marker; better on *why* a saved pref wins |

## 1. Diffs

Both carry all five required facts (five levels, default medium, the env override, saved preference honoured, fake upstream proves only what the seat sends), both under 20 lines, both subject `docs: lanes runbook — reasoning effort levels (test: lint)` with the correct `Generated-By` trailer (the brief asks only for that one). Both dropped the OpenRouter catalog URL that ebfcb95 deliberately added.

- **M2off — approve.** Matches `lanes.md`'s real convention (`**Reading the denial audit.**`, `**One-time: the key file.**`, `**Using it.**`). Nits: swapped the house `**Unmeasured (dated debt 2026-09-04):**` marker for `**Proven only as sent:**`; lost the URL.
- **M2med — rework.** Two one-line fixes: use a bold lead-in instead of `###`, and give the commit a body. It is more accurate on the mechanism (every level declared so a saved `settings.yaml` choice validates).

## 2. What went on the wire

- `M2off/openrouter-route.yml` really says `reasoning: off` — the env var reached the profile.
- But **both** `DSH_HOME/settings.yaml` files carry `agent-default-model.reasoningEffort: medium`, written by dsh at launch (00:36:12.599, *before* the overlay at .663) even in a fresh isolated home — identical to the operator's shared seat.
- The one `request/header` event in each transcript records `config.reasoningEffort: "medium"` — **identical in both runs**.
- Per the seat script's own comment, `profile.reasoning` is only "the fallback used when the agent selection carries no effort". The selection carried `medium`, so `off` was never used.
- Corroboration: the M2off log prints `dsh: reasoning:` blocks, and 176 reasoning chunks / 37 KB of reasoning text came back. An `effort: none` request does not stream that.
- No event records the raw HTTP body, so the literal `reasoning: {effort: …}` object is not directly observable; the header config is the closest proxy.
- `reasoningTokens` appears in **zero** usage records in either transcript — that is why the ledger says `reasoning 0`. Reasoning *content* was streamed in both, so `0` is an accounting gap, not evidence of no reasoning.

## 3. Conclusion

**Did medium change quality, tokens or time? Unknown — nothing was compared.** Both runs asked for the same effort, so the spread (+19% input, +31% output, +23% wall clock, +50% reasoning chunks) is run-to-run variance at a *fixed* setting. That is the one useful number here: it sets the noise floor a real off-vs-medium comparison must beat, and it is wide.

**Is the provider visibly acting on effort?** Half-answered. DeepSeek via OpenRouter demonstrably reasons under `medium` — 37–57 KB of reasoning text came back. But reasoning *token counts* remain unmeasured (never reported), and the off-vs-medium contrast is entirely unmeasured. The runbook wording both commits shipped — "unmeasured (dated debt 2026-09-04)" — still stands, unchanged by this exercise.

**New finding, undocumented and load-bearing:** a saved `settings.yaml` preference silently overrides `OPENROUTER_REASONING_EFFORT`. The runbook says the env var "overrides the default"; in fact the saved agent selection beats it, and dsh writes `medium` into a *fresh* DSH_HOME unasked. This is what voided M2. To re-run: strip `reasoningEffort` from the run's `settings.yaml` after launch-time creation, or make the seat write the requested level into the agent selection rather than only the profile fallback.
