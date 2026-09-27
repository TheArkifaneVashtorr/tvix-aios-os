# 2026-09-27 — the OpenRouter-only rule revised: operator-launched work may call Claude through the subscription

## The operator's words

In the session of 2026-09-27: "Ok we are moving to local machine only now with anthropic calls
and no cloud. I want a full JAZ replication this time." Then: "I don't want to use the API. I
was to use the Claude subscription." Shown the 2026-09-10 amendment, which quotes them as
saying "openrouter only.": "I don't recall saying those words by the way, unless it was a time
I was out of Claude tokens." Asked how to handle that rule, they chose to revise it.

## What it revises

`docs/decisions/2026-09-09-redesign-answers.md` §4, the 2026-09-10 amendment, which said every
model call this program dispatches runs on the OpenRouter lane, and that Claude Code is not a
fallback for a seat-dispatched call. The operator does not recall the quoted words, and they
may date from a day their Claude usage was exhausted. The rule is therefore re-decided here
rather than treated as standing intent.

## The rule from now on

1. **Factory dispatch stays on the OpenRouter lane.** Seats, `factory-dispatch`, waves and the
   routing ladder are unchanged, and so is `docs/ledger/routing.toml`. Its `claude` rows remain
   the rung-3 terminus that hands the operator a launch line.
2. **Operator-launched work may make automated Claude calls through the operator's
   subscription.** That is a run the operator starts by hand, such as an experiment arm, a
   probe or a smoke run; the first case is arm C of
   `docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md`. Nothing dispatches
   such a run: no factory-dispatch, routine, timer or seat.
3. **Conditions for any such call:**
   - It goes through headless `claude -p` or the Agent SDK, signed in with the subscription.
   - `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` and `apiKeyHelper` are unset, so no call can
     fall back to API billing.
   - The login (`~/.claude/.credentials.json`) never enters a process that runs model-written
     code, or any process with network other than `claude` itself. A sandboxed runner reaches
     Claude only through a host-side gateway on one socket.
   - Runs go one at a time, and stop on the subscription's usage-limit signal.
   - Every call is logged (tokens, cache reads, the client-side cost estimate), and the log is
     kept with the run.

Using the subscription for dispatched factory work would need its own decision.
