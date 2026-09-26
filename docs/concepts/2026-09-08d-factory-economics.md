# Rate of development and token economics — what the files say (2026-09-08)

The operator at 16:40: "rate of development should also be derived from this;
I run out of tokens and switch services and tasks a lot; I want an indicator
of token usage by the number of tries; the OpenRouter page says tokens went
down but that is a vibe." Sources: the 289 `~/factory/runs/*/*.result` files
(every one carries a `usage:` block: input, output, cacheRead, wall), the 213
gate reviews, the OpenRouter activity export (`~/strategy/ledger/
openrouter-activity.csv`, ends 2026-09-05 18:52 UTC), the Claude transcripts
under `~/.claude/projects/-home-dalhaka-nixos-agent-env/`, and the board log.
Two scripts of mine and four independent readers (Workflow `wf_ddfda270-094`:
seat side, Claude side, the operator's switching record, an Opus skeptic);
the load-bearing claims re-derived by hand (`verify-econ.py`).

## 1. Tokens went down — the volume did; the cost per result did not

| local day | seat runs | seat in+out Mtok | cacheRead Mtok | span h | in+out Mtok per span h |
|---|---|---|---|---|---|
| 09-04 | 67 | 21 | 239 | 10.5 | 2.0 |
| 09-05 | 138 | 65 | 603 | 23.1 | 2.8 |
| 09-06 | 33 | 25 | 331 | 12.8 | 2.0 |
| 09-07 | 19 | 24 | 174 | 15.0 | 1.6 |
| 09-08 (to 15:33) | 33 | 42 | 270 | 16.2 | 2.6 |

The OpenRouter page charts volume, and volume fell 138 → 19–33 runs a day
after 09-05. Per hour the factory ran, the burn is flat (2.0–2.8 Mtok per span
hour); the days after 09-05 are shorter, not cheaper. The page cannot show
cost either: on the two days with dollar ground truth the DeepSeek Pro rows
moved from StreamLake (09-04, 2849 generations, $0.076 per M prompt token) to
CoreWeave (09-05, 3738 generations, $0.240 per M prompt token) — per FRESH
token 12 % dearer ($1.60 → $1.80 per M), per prompt token 3× because 87–93 %
of prompt tokens are cache reads and the providers price those differently.
09-05's partial-day bill ($66.61) exceeded 09-04's whole day ($62.28) on 35 %
fewer prompt tokens.

## 2. Cost per landed root roughly doubled, and tries are not why

Seat tokens per landed root, all rounds summed, by the day of the root's first
gate (median Mtok in+out): 09-05 0.59 → 09-06 1.16 → 09-07 1.74 → 09-08 1.27
(means 1.02 / 1.52 / 2.33 / 1.77). Tasks grew (median landed insertions per
root 228 → 926 → 958 → 542) and a regression over the landed roots gives
+0.70 Mtok per 1000 insertions and +0.29 Mtok per try, with day effects of
+0.85 (09-07) and +0.79 (09-08) Mtok surviving both controls. Tries per landed
root FELL (1.90 / 1.90 / 2.07 / 1.73 / 1.56). What rose is input per attempt:
the seats' input:output ratio went 5.5 / 8.5 / 6.4 / 14.5 / 17.8 by day and
the median input per run 0.17 / 0.31 / 0.54 / 0.46 / 0.85 Mtok, median
cacheRead per run 2.9 / 2.2 / 10.5 / 9.4 / 8.6 Mtok, median wall 12 / 8 / 14 /
33 / 28 min. Each attempt now re-reads about eighteen tokens of context for
every token it writes, against eight on 09-05: bigger briefs (facts, the
prior attempt, the harness contract), a bigger tree, longer runs. Effort and
route mix are stable, so neither is the cause.

## 3. The tries indicator

Seat tokens per root are linear in tries with a near-zero intercept: Mtok ≈
0.76 × tries − 0.24 over 177 roots; by rounds to land (landed roots):

| rounds to land | roots | median Mtok | mean | median per round | median wall min |
|---|---|---|---|---|---|
| 1 | 48 | 0.49 | 0.79 | 0.36 | 9 |
| 2 | 39 | 1.05 | 1.63 | 0.51 | 27 |
| 3+ | 13 | 1.80 | 2.83 | 0.60 | 46 |

Restricted to roots first gated on 09-07/09-08 (the driver's verify and the
prior attempt exist): 1 round 0.85 median, 2 rounds 2.71, per round 0.85 vs
1.36. Paired inside the same root, round 2 costs what round 1 cost (median
ratio 0.99, n = 71): carrying the prior attempt (SD4b) has not made the fix
round cheaper. So the expected seat cost of a root is about 0.6 Mtok × E[tries]
with E[tries] ≈ 1.85 for roots that land, and first-try yield is the only
lever — flat at 44–56 % (concept 2026-09-08c). 72 of 177 roots never landed
and consumed 43 of 177 Mtok (22 %); CR2 alone eight tries and 6.9 Mtok, OG3
three tries and 6.8 Mtok still in flight.

## 4. The Claude side is the expensive side, and it is not on the board

**Corrected 17:05 (the first figures here were wrong by my dedup rule).** A
transcript repeats an assistant message once per content block: in the main
sessions the repeats carry identical usage (62 % of lines are repeats), in
the subagent transcripts the usage grows across the blocks (50 % repeats). The
one rule right on both is MAX per field per `message.id` per file; naive
summing inflates the main side 3.5×, first-wins understates the gates up to
13×. Under that rule, per day 09-03..09-08: main-session output 1.21 / 0.47 /
1.88 / 0.78 / 0.96 / 0.89 M; workflow agents' output 4.64 / 4.03 / 5.47 /
3.55 / 4.38 / 2.51 M; cache writes (main + workflows) 24 / 17 / 29 / 20 / 27 /
12 M; cache reads 0.89 / 0.66 / 1.11 / 0.65 / 0.65 / 0.55 B. The gates are
three to five times the orchestrator's own output every day. A gate's own
cost is of the order of 50 k output and 300 k cache-write tokens on 10 M cache
reads; at 1.6–1.8 gates per landed root that is roughly 0.5 M
output-plus-cache-write tokens per landing on the Claude side against ~1.3 M
seat tokens, at a per-token list price about ten times the seat's. The
list-price dollar total first written here ($4,900) was computed on the
inflated series and is withdrawn; the order of magnitude stands — the cache
reads alone, 0.5–1.1 B a day, cost more at list than the whole OpenRouter
bill — and the subscription pays it, so the operator's binding constraint is
the weekly rate limit, and the felt signal (depletion, resets, service
switches) tracks the side the board does not measure. How to capture this
side, and the OpenRouter side, is concept 2026-09-08e.

## 5. The operator's own record (from the transcripts and the board log)

Main sessions per day 5 / 1 / 4 / 3 / 4 / 3 with coverage of roughly 12–18
hours and up to three or four concurrent; the switching and depletion events
the board records: the Claude budget exhausted 09-04 midday (the wave landed
on the DeepSeek seat instead), OpenRouter credits out 09-05 21:50 for thirty
minutes, four gates dead on the Claude session limit 09-06 00:30, the weekly
limits at 90–96 % on 09-06 with the planning workflow launched at the edge on
purpose, two Codex/GPT-6 detours (09-06 morning: "a week of credits" for no
flake; 09-06 12:40 → 09-07: CX1/CX1b), the driving model switched to Fable
09-06 14:20, the scheduled reset-probe missed 09-07 because the app was
closed. Landed roots per operator-active hour 0.7 / 2.8 / 1.1 / 0.7 / 1.1 —
the 09-05 peak is the small-task day. The switching costs hours, not tokens:
seat concurrency (summed wall over span) fell 1.36 → 0.8–1.1.

## 6. What the board measures wrongly today

- `billed` in the brief (`tasks.py` `seat_stats`) is input + output only:
  177 M tokens against 1,624 M cache reads in the same seven-day set — 9.8 %
  of the tokens consumed. In money the cache reads are a smaller share (about
  $0.035–0.044 per M for Pro against $1.0–1.3 per M input), but they are what
  drove the 09-07/09-08 regression, and the brief cannot see them.
- `docs/ledger/openrouter-prices.csv` has three rows, the newest 09-04, with
  cache reads at $0 and Pro input at $0.55 per M where the export measured
  $1.0–1.35 per M; on the overlap window the table says $34 where OpenRouter
  charged $84.
- The `.result` usage is a ~90 % proxy for the export's volume on a UTC-aligned
  window (441.6 of 482.0 M prompt-equivalent tokens); the export has no rows
  after 09-05, so every later dollar is an extrapolation.
- The ledger extractor (`tools/ledger/factory.py backfill`) crashes on today's
  transcript shape (`_read_findings` on a string finding), so the Claude side
  has never been rolled up on this host.

## 7. The indicators to keep, one line each

- **Cost per landed root, seat side:** 0.6 Mtok per try × tries per landed
  root (1.56–2.07) → 1.1–2.4 Mtok; by plan, not by day.
- **Burn per span hour** (in+out Mtok over the factory's active hours), not per
  calendar day: flat at 1.6–2.8.
- **Input per attempt** (median input and cacheRead per run, the in:out
  ratio): the quantity that actually rose; the first lever to pull is the
  brief and the tree the seat reads, not the retry count.
- **First-try yield** by plan (concept 2026-09-08c): the only lever on tries.
- **Unlanded share** of seat tokens (22 % this window; the CR2/OG3 tails).
- **Claude output + cache-write per landed root** (gates and planning
  separately), with the dedup rule stated; and the weekly-limit share per
  session if the rate limit can be read from the app.

## Owed

A fresh OpenRouter activity export (operator: the page's CSV) to price
09-06..09-08; `billed` to carry cacheRead and the table's cache-read column
to be real; the price table refreshed from the export by provider; the ledger
extractor fixed for the current transcript shape; the ladder report (SD9,
landed today) to gain the per-try and per-span-hour lines. None typed —
nothing else is owed this session; listed for the operator.
