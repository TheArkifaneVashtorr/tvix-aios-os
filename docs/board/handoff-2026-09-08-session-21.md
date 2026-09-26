# Handoff — session 21 → the next session (2026-09-08 21:10 CDT; the session model moves from Fable 5.1 to Opus 5 high)

Paste to the next session: **"Read docs/board/handoff-2026-09-08-session-21.md, then the SessionStart facts; nothing launches without my word."**

## Why the swap

Fable's weekly limit reached 88 % at ~21:05; the operator: "don't start any
more tasks" and "make a prompt for the swap over". Everything the remaining
plans need from the orchestrator's chair runs on Opus 5 at high: the
mechanical loop (dispatch, read the `.result`, launch the gate workflow,
commit the review, integrate and fast-forward, keep the board), fix-round
sections typed from a rejecting review, the switch #23 surface after SP3, and
the board. Two caveats: (1) `.claude/workflows/plan.js` and its seeded copy
hard-code `model: 'fable'` for the drafter and reviser — a re-plan or a new
plan spends Fable whatever the session runs; do not run them until the
operator decides the drafter model (§Decisions); (2) the bill is calls ×
context on any model — memory `delegate-reads-to-agents`: reads, greps,
probes and drafts go to Sonnet or Haiku agents that return digests; the
session decides and commits.

## The state on main (b5ac8cc, clean tree)

- **Spend telemetry** (`docs/superpowers/plans/2026-09-08-spend-telemetry.md`,
  judged 37/42 dispatch — judgement `…-spend-telemetry-r1.md`; eight tasks).
  SP1 LANDED via SP1b (main 3c74757; SP1 rejected on one seat MAJOR, SP1b
  approved first time; reviews `2026-09-08-opus-review-sp1-SP1.md`,
  `…-sp1b-SP1b.md`). The operator took the plan's three recommendations:
  the exporter env route `managed`, no 0700 flip with switch #23, SP6 in
  scope. WAVE 2 IS READY AND HELD: `waves --plan 2026-09-08-spend-telemetry.md
  --next` → `"SP2" "SP3" "SP8"`. One MINOR carried to SP8's gate: the broker
  writes no `src` field; SP8's ingest synthesises it. SP3 owes switch #23
  (its section carries the surface prediction; measure on the landed tree
  before the switch line ships).
- **The OpenAI lab spike** (`~/flakes/openai-lab`, first commit d3789ab;
  `repos.toml` row 3f1ca1a; spec
  `docs/superpowers/specs/2026-09-08-openai-lab-spike-design.md` and the
  judgement `…/plan-judgements/2026-09-08-openai-lab.md` at 4d3c851 — 35/42,
  dispatch, 29 errata). The plan file LANDED at the session's close as
  `docs/superpowers/plans/2026-09-08-openai-lab.md` (5,980 words; the Sonnet
  reviser applied all 29 errata; the three `### ` headings byte-identical to
  the judged draft; `tasks.py check` empty; waves `OL1`, then `OL2 OL3`;
  `conflicts: none` since 81ae876). The 29 applied edits were NOT judged: before
  OL1 launches, a Sonnet verifier diffs the judged draft
  (`~/factory/archive/session-21-2026-09-08/openai-lab/draft-0.md`, 6,000
  words — the in-place revision as of 21:08, close to but not exactly the
  judged text) against the landed plan and re-runs every cited command (the
  spend plan's ship step needed three body fixes after the same check).
  The reviser also found that `evidence report ladder` does not group codex
  rows as `codex/<kind>/<size>` (`_route_kind_size` in `pkgs/evidence/report.py`)
  — the plan's Assumption 10 and Operator item 6 read the gate reviews by
  hand; a tooling chip for the next session. OL1's launch through the codex
  arm (`FACTORY_SEAT=codex`, the line in the plan's Dispatch section) waits
  for the operator's word.
- **Landed tooling this session:** c3dc548 `tasks.py json` serialises the
  task-status map; 8045b2f repomap scrubs a linked worktree's git env;
  b520783 + 5ea2491 the brief's fix-round line closes on a landed chain
  successor and a chain root may end in a capital letter; 81ae876
  `conflicts` compares `(repo, path)`. Chips the operator started elsewhere
  for two of these exist as branch `claude/sleepy-ptolemy-de4372`; if a
  duplicate lands, drop it.
- **Memory (the next session's, under `~/.claude/projects/…/memory/`):**
  `spend-telemetry`, `openai-lab-spike`, `otel-claude-code-measured`,
  `delegate-reads-to-agents` — all current as of 21:10.

## The recipes (verbatim, from this session's runs)

- **Dispatch a wave** (background, never a foreground call):
  `tools/factory/seat/factory-dispatch <run> ~/nixos-agent-env docs/superpowers/plans/2026-09-08-spend-telemetry.md --dry-run`
  first (prints `would run: factory-wave <run> … "<KEYS>"`), then the same
  without `--dry-run` with `run_in_background: true`. Run names: `sp2` for
  wave 2 (one run per wave; groups run concurrently under it).
- **A fix round** (rule A1, once per root): type `### <KEY>b (code, S) — …`
  from the review (a Sonnet agent drafts it; the `dependsOn` clause in
  parentheses), append it with the Edit tool before the next `### `, run
  `tasks.py check` (empty), `write-board`, commit; launch
  `FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-08-spend-telemetry.md tools/factory/seat/factory-task <run>b ~/nixos-agent-env <KEY>b --prior <run>/<KEY>`
  in the background (rung 2, Pro high).
- **The gate:** `Workflow({ scriptPath: '/home/dalhaka/factory/bin/opus-gate.js', args: { run, key, plan: '2026-09-08-spend-telemetry.md', date, scratch: <a fresh dir>, base, head, subject, acceptance, touches, prior: '' or the rejecting review's repo path, model: 'opus', effort: 'high', repo: '/home/dalhaka/nixos-agent-env', ws: '/home/dalhaka/factory/ws/<run>/<KEY>', note } })`
  — `base`/`head` from `~/factory/runs/<run>/<KEY>.result`, `subject`/
  `acceptance`/`touches` from the section (byte-exact); `docs` tasks use
  `model: 'sonnet'`. The review lands at
  `docs/reviews/<date>-opus-review-<run>-<KEY>.md`.
- **Landing** (the order matters): `write-board`, commit the review by
  pathspec (`nix develop -c git commit -q -F <msg> -- <review> docs/OPERATIONS.md`);
  `tools/factory/seat/factory-integrate <run> ~/nixos-agent-env <KEY>` in the
  background (it runs the checks; exit 0 required), then
  `git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>`;
  then `tasks.py check` (empty) and `waves … --next` for what it unblocks.
  If main moved under a touched file, merge main into the task branch first
  (`git -C ~/factory/ws/<run>/<KEY> fetch ~/nixos-agent-env main && git -C … merge --no-edit FETCH_HEAD`).
- **Never:** `sed -i`/redirects beside a plan path (the guard), a foreground
  seat launch, a commit sweeping a peer's staged files, a Fable drafter run
  before the decision below.

## Decisions for the operator (one word each)

1. **Wave 2 (SP2 SP3 SP8): go or hold.** Three DeepSeek seats and up to
   six Opus gates. Recommendation: go when the Claude pool has room; SP3 is
   the switch task.
2. **The pinned planning workflow's drafter model:** patch `plan.js` (and
   the seeded copy) to take the drafter/reviser model from an argument,
   default `opus` while Fable is scarce (a Sonnet implementer, TDD on
   `tests/factory/plan.test.mjs`). Recommendation: yes; the Sonnet-drafted lab
   plan scored 35, the Fable-seeded revision 37, both above 34.
3. **The lab: land the plan and launch OL1, or park.** Codex credits per task;
   the answer is the gate record. Recommendation: land the plan; launch when
   the operator wants the measurement.
4. **The first drive session** (`tools/factory/seat/seat-drive.sh --port 43210`)
   — the operator's, whenever; wave 2's verbs are a fitting first session.

Nothing needs to be RUN before the next session starts: no switch is
pending, no seat is running, no gate is open, the tree is clean.
