# Research 2026-09-11 — the batch lane

This is FA2's measurement report. Decision 30b is "the provider's batch API",
and the operator corrected the reading on 2026-09-10: the batch runs on the
existing OpenRouter lane, not through Claude Code and not on a second vendor.
Every fact below was measured from inside the lane's network namespace (this
seat already runs there — `HTTPS_PROXY=http://10.100.4.1:3141`, the broker
injecting the key at egress). Nothing in this report prints a credential; the
commands carry no `Authorization` header because the broker adds it on the way
out.

Verdict up front, then the measurements that justify it:

- **`serves-fable`: yes.** The lane's catalogue returns `anthropic/claude-fable-5.1`
  (in $10.00 / out $50.00 / cache-read $0.25 per MTok) and a `:batch` variant
  (in $5.00 / out $25.00 / cache-read $0.125 per MTok), the batch id at exactly
  50 % of standard.
- **`batch-shape`: measured live.** `POST https://openrouter.ai/api/beta/batches`
  accepts an inline `requests` array, returns `202 Accepted` with `status:
  "validating"`, is polled at `GET /api/beta/batches/:id` until terminal, and
  returns results inline. A 1-request fable batch completed in 259 s and was
  billed $0.00039 for 26 tokens — exactly the 50 % rate.
- **§3 Claude-side baseline: UNMEASURED, and non-decisive.** This seat is on
  the OpenRouter lane; it has no Claude Code to meter. Interface 2 of the task
  is the operator's correction: an Anthropic lane is excluded and Claude Code
  is not a fallback for any automated call, so the subscription figure decides
  nothing (Step 2's table below deliberately carries no Claude-side column).

## §1 The provider's catalogue, as the lane returns it

Command (the key is injected by the broker; nothing is sent as a header):

```text
$ curl -sS -x http://10.100.4.1:3141 https://openrouter.ai/api/v1/models
```

The response is the full catalogue: `{"data": [...], "total_count": 437}` with
437 model entries. Filtered for an Anthropic or `fable` id (and its prices),
the rows that matter:

```text
anthropic/claude-fable-5.1         prompt 1.0e-5   completion 5.0e-5   cache_read 2.5e-7
anthropic/claude-fable-5.1:batch   prompt 5.0e-6   completion 2.5e-5   cache_read 1.25e-7
```

Per-MTok dollars (× 1,000,000): standard fable = **$10.00 in / $50.00 out /
$0.25 cache-read**; the `:batch` id = **$5.00 in / $25.00 out / $0.125
cache-read**. The standard id matches the ledger row already on file
(`docs/ledger/openrouter-prices.csv` → `2026-09-10,anthropic/claude-fable-5.1,
10.00,50.00,0.25`); the `:batch` id is new and is the 50 % batched price
OpenRouter documents.

**Verdict §1: `serves-fable` = yes** — `anthropic/claude-fable-5.1` is served
by the lane, provider Anthropic, and a `:batch` variant sits beside it at half
price.

## §2 The batch endpoint: request shape, poll, result grammar, turnaround

The documented endpoint is *not* `/api/v1/batches` (that path returns the
web app's 404 HTML page — measured). It is `POST /api/beta/batches`. The
submit body has three required top-level fields, serialised `endpoint` then
`model` then `requests` (the API stream-parses and refuses a `requests`-first
body):

```json
{
  "endpoint": "/v1/chat/completions",
  "model": "anthropic/claude-fable-5.1:batch",
  "requests": [
    {
      "custom_id": "fa2-probe-1",
      "body": {
        "messages": [{"role": "user", "content": "Say hello."}],
        "max_tokens": 16
      }
    }
  ]
}
```

Submit and its response:

```text
$ curl -sS -x http://10.100.4.1:3141 https://openrouter.ai/api/beta/batches \
    -H "Content-Type: application/json" -d @batch-submit.json
{"id":"batch-1789094338-KsxdGYx0U4WjU5j0W5La","object":"batch",
 "endpoint":"/v1/chat/completions","model":"anthropic/claude-fable-5.1-20260831",
 "completion_window":"24h","status":"validating","created_at":1789094338,
 "finalized_at":null,"request_counts":{"total":1,"completed":0,"failed":0},
 "usage":null,"results":null,"error":null}
[STATUS=202]
```

A successful submission is `202 Accepted` with `status: "validating"`: the
batch is persisted and queued, not yet run. The only completion window is
`24h`. Poll the same id:

```text
$ curl -sS -x http://10.100.4.1:3141 https://openrouter.ai/api/beta/batches/<id>
```

Status progression observed: `validating → in_progress → completed`. Terminal
statuses are `completed`, `failed`, `expired`, `cancelled` (plus the transient
`finalizing` and `cancelling`). `request_counts` carries `total` / `completed` /
`failed`; `results` is `null` until the batch is terminal. The completed object
for the probe:

```text
{"id":"batch-1789094338-KsxdGYx0U4WjU5j0W5La","object":"batch",
 "endpoint":"/v1/chat/completions","model":"anthropic/claude-fable-5.1-20260831",
 "completion_window":"24h","status":"completed","created_at":1789094338,
 "finalized_at":1789094597,"request_counts":{"total":1,"completed":1,"failed":0},
 "usage":{"prompt_tokens":13,"completion_tokens":13,"total_tokens":26,
          "cost":0.00039,"is_byok":false},"error":null,
 "results":[{"id":"msg_011Cevss1fFYRzEPdGsWZyYT","custom_id":"fa2-probe-1",
   "response":{"status_code":200,"request_id":null,
     "body":{"model":"anthropic/claude-fable-5.1:batch",
       "id":"gen-batch-1789094338-812ddd369b57b85dbb12",
       "object":"chat.completion","service_tier":"batch",
       "choices":[{"index":0,"message":{"role":"assistant",
         "content":"Hello! How can I help you today?"},
         "finish_reason":"stop"}],
       "provider":"Anthropic"}},"error":null}]}
```

Result grammar: each completed batch returns `results` inline (there is no
separate results-download endpoint). Each item maps back to its input by
`custom_id`, and carries exactly one of `response` or `error`; `response.body`
is the Chat Completions object (its `model` echoes the `:batch` id, `provider`
is `Anthropic`, `service_tier` is `"batch"`), and the per-request
`response.status_code` distinguishes a 200 completion from a rejected request
inside an otherwise-completed batch.

**Turnaround and cost.** `created_at 1789094338 → finalized_at 1789094597` is
259 s (~4 min 19 s) for a 1-request batch, dominated by the 24 h‑window queue
draining rather than the 16-token generation. The bill — `usage.cost 0.00039`
for 13 prompt + 13 completion tokens — is exactly `13 × $5/MTok + 13 ×
$25/MTok`, confirming the batch endpoint applies the 50 % rate: unbatched that
same 13/13 call metered $0.00078 in the ledger.
`grep -c 'claude-fable' /var/lib/evidence/ledger/openrouter-usage.jsonl` → 2
(the two probe rows); no planning-session token counts exist yet.

**Cancellation.** There is no cancel verb on the lane's API surface:
`DELETE https://openrouter.ai/api/beta/batches/<id>` returns `404 Not Found`
(measured), and the batch quickstart documents submit / list / poll only. A
batch that must not run is therefore not cancelled over the API — it is either
allowed to reach a terminal status or left to `expire` at the 24 h window. See
the runbook section in `docs/runbooks/lanes.md` ("The batch lane").

**Verdict §2: `batch-shape` = measured.** Endpoint `/api/beta/batches`, submit
`{endpoint, model, requests:[{custom_id, body}]}`, poll `GET
/api/beta/batches/:id`, inline `results[]` keyed by `custom_id`, 259 s
turnaround on a probe, 50 % pricing confirmed by the actual `usage.cost`.

## §3 The Claude-side baseline

**UNMEASURED.** Fable inside Claude Code is billed against the operator's
subscription; metering it would require a Claude Code seat, and this seat is
on the OpenRouter lane (netns-only, `10.100.4.2`). The record's §11 Q9 figure
traces to a board transcription, not a metered ledger row. It is non-decisive:
interface 2 excludes an Anthropic lane and excludes Claude Code as any
automated fallback, so the batch lane is the only path on the table and no
subscription figure changes the comparison. The arithmetic below therefore has
no Claude-side column, as the task's Step 2 directs.

## §4 The arithmetic for one planning increment

One planning increment = three specs + three plans (the `docs-spec` and
`docs-plan-run` drafts Fable writes). The token counts come from the two
judgements on file, which record the settled program plan's size:

- `docs/reviews/plan-judgements/2026-09-09-program.md` → `words: 7659`
- `docs/reviews/plan-judgements/2026-09-09-program-r1.md` → `words: 10753`

Converted at 1.3 tokens/word (a standard English-prose ratio, stated here so
the number carries its source): 7659 → 9,957 and 10753 → 13,979 output tokens.
I use the rev‑1 figure, 13,979, as the settled-draft size for the output half
of the increment (the plan's own SPEC-*/PLAN-* sections are a subset of those
words, so this is an upper bound, i.e. conservative).

The input half is **unmeasured** — the ledger holds only the two fable probe
rows (13/16 and 13/13 tokens) and no planning session, so any prompt-token
figure would be invented. It is deliberately left out of the column because
the 50 % batch rate applies to input *and* output alike: the input term scales
both columns by the same factor and cannot flip the verdict. The one input
fact that does bear on cost is cache: the charter/decisions context Fable
re-reads across six drafts is cache-hit at $0.25 (unbatched) vs $0.125
(batched) per MTok, which also halves.

| drafter (id §1 measured) | in $/MTok | out $/MTok | cache-read $/MTok | 13,979 out tokens | batched? |
|---|---|---|---|---|---|
| `anthropic/claude-fable-5.1` | 10.00 | 50.00 | 0.25 | $0.699 | no |
| `anthropic/claude-fable-5.1:batch` | 5.00 | 25.00 | 0.125 | $0.349 | **yes — 50 %** |

Batched Fable drafts the increment's output at **$0.349 vs $0.699 unbatched**,
and every cached input token halves as well. The batch id is the cheapest
drafter §1 found, on the lane, and the only candidate that matters (the lane
is decided; there is no other vendor).

## §5 The recommendation

**Write the row.** The two preconditions the task set are both met: §1 says
`serves-fable` = yes (the id exists and is served, provider Anthropic), and §2
proved the batch endpoint runs fable at exactly 50 % (`$0.00039` for 26
tokens). §3 is unmetered but non-decisive under interface 2's OpenRouter-only
ruling. The recommendation has arithmetic behind it (§4): the batch id halves
every token price, and the was it decides — unbatched $0.699 vs batched $0.349
on the measured output side — holds whatever the (unmeasured, equal-scaling)
input term turns out to be.

The row names `anthropic/claude-fable-5.1:batch` for `docs-spec` and
`docs-plan-run`, rung 1, effort high, winning **only** when the caller asks
for `--route openrouter-batch` — the default interactive caller keeps the
existing openrouter ladder, and the FA1 rung-3 claude terminus keeps the
operator-watched interactive path unchanged.

**Refusal case (for the record).** Had §1 said `serves-fable` = no, interface 2
would still require a row — naming the best model the lane *does* serve —
rather than landing as documentation only; that branch was not taken because
the id is present.