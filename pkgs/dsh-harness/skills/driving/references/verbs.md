# verbs.md — the four driver commands

The four driver commands a driving seat runs, their exit codes (from the
scripts' own headers) and the one line each prints that the driver reads.
"Exit 0" is always the good outcome unless a line below says otherwise; any
driver that faults before acting exits non-zero and the seat does not proceed
as if it had.

## factory-task

`factory-task <run> <repo-path> <KEY> [--model ID] [--after KEY2] [--prior <run>/<KEY>] [--rung N] [--fallback]`

`--rung N` starts at rung N instead of the key's; `--fallback` takes the
row's fallback model when the row has one. Runs the headless seat on one
task's brief. Exit codes, the script's own mapping:

- `0` — `done`, and `unreported` (the seat exited without a result line; the
  driver wrote `status=unreported` — the driver's verdict is in the
  `.result`, not the code).
- `1` — `partial`.
- `2` — `failed` (a failed `seat-submit`, a result line with no commits, no
  usable result line, or the seat's own `status=failed`), and the same code
  for a refused input before any run (`factory_die 2`: a missing
  `FACTORY_PLAN`, a bad `--rung`, a `--prior` that is not a `<run>/<KEY>`
  pair, no such repo).
- `3` — an unrecognised status word, the fallthrough.
- `4` — escalated: the key's rung is a claude rung, the launch line was
  printed and recorded as `<KEY>.escalate` before any workspace or log
  existed.

A driver branches on 0 (advance) and 4 (escalate); 1, 2 and 3 are the three
ways a run did not land, and the `.result`'s `error_class:` line tells them
apart. The line the driver reads: the
`FACTORY-RESULT status=<done|partial|failed>` line of
`~/factory/runs/<run>/<KEY>.result`. Only `done` advances the task; a
`partial` or `failed` status routes the driver to the gate and the operator.

## factory-review

`factory-review <run> <repo> <KEY>`

A second headless session reviews the task branch against the plan section and
never fixes what it finds. Exit codes:

- `0` — verdict `approve`.
- `1` — verdict `rework`.
- `2` — verdict `reject`.
- `3` — no verdict line at all, or the review session failed.
- `4` — escalated: the review asks for a `claude` rung.

The line the driver reads: `FACTORY-REVIEW verdict=<approve|rework|reject>`
from `<KEY>.review.md`. On an exit `4` the line the driver reads is the
`launch:` line of `~/factory/runs/<run>/<KEY>.escalate` — printed to the
operator, never run.

## factory-integrate

`factory-integrate <run> <repo> KEY...`

Merges each `task/<KEY>` into `integ/<run>` and runs the named checks. Exit:
`0` when every merge landed and every check passed. Non-zero when any conflict,
refusal, skip or failed check happened — the exact value does not choose a
branch of the driver, the non-zero flag does.

The lines the driver reads: `CHECK <name> pass|fail` and `CONFLICT <KEY>`
from stdout. The driver runs `factory-integrate` only after the gate's review
says `approved` — the gate ran first; a `CHECK … fail` line means the pull
never runs.

## factory-dispatch

`factory-dispatch <run> <repo> <plan> [--dry-run] [--all] [--repo-name NAME]`

Asks the derived task graph for a plan's next wave and launches it. Exit codes:

- `0` — the wave launched (or, under `--dry-run`, nothing was touched).
- `2` — usage, a bad repo or plan path, or an unknown repo name.
- `5` — a malformed wave line from the graph query.
- `6` — the graph query failed.
- `7` — the launched wave failed, or `--all` made no progress.

The line the driver reads on a `--dry-run`: `would run: factory-wave <run>
<repo> "<group>"…` — the seat reads the group and the command it would run,
then reads the same line as the real dispatch when the operator says go.