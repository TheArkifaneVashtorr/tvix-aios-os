# Handoff — session 22 → the next session (2026-09-09 ~10:00 CDT; Opus 5, reset for context length)

Paste to the next session: **"Read docs/board/handoff-2026-09-09-session-22.md, then the SessionStart facts. Nothing launches without my word."**

## Why the reset

Context, not a limit or a failure. The session ran from 21:20 on 2026-09-08 to
~10:00 on 2026-09-09: two switches, sixteen seat runs, fifteen Opus gates, five
rejections and four fix rounds. Nothing is mid-flight that a fresh session
cannot pick up from the tree, which is the point of the board, `evidence
bundle` and the task brief.

## The state on main (`791521f`, plus CR4b integrating)

- **Two switches landed.** #23 → gen 48 (2026-09-08 22:56), SP3's telemetry
  collector and SP8's ingest. #24 → gen 49 (2026-09-09 09:31), SD12c's
  seat-drive boot fix. Rollback for the live system is `system-48-link`.
  **A switch needs THREE commands, not one** — `switch-to-configuration switch`
  activates without registering a generation, so add
  `sudo nix-env -p /nix/var/nix/profiles/system --set <toplevel>` then
  `sudo <toplevel>/bin/switch-to-configuration boot`, and verify with
  `readlink /nix/var/nix/profiles/system`. #23 was left unregistered for a
  while; a reboot would have silently reverted it.
- **Spend telemetry**: SP1, SP2 (via SP2b), SP3, SP6, SP7, SP8 landed. Only SP4
  (`evidence report spend`) and SP5 (the runbook) remain, SP4 ready and held on
  the operator's word. SP4 was amended before dispatch with a fact SP7's gate
  measured: otel `token.usage` rows are CUMULATIVE, one per 5-second export
  (17584 then 31000 observed), so SP4 takes **MAX per (session_id, model,
  model_suffix, token_type)**, never SUM — and its fixture needs two rows per
  key with different values or the rule is untested.
- **The OpenAI lab spike is COMPLETE**: OL1 the pinned flake, OL3 the runbook,
  OL2b the extractor after OL2 was rejected. The gap claim
  `codex-rate-limits-shape-unmeasured` is closed as `verified`: real Codex
  rollouts carry `rate_limits` only nested under `event_msg`/`token_count`,
  nine keys, windows one level deeper — 242 of 242 files, 0 top-level, 2569
  nested. The extractor emits 20 rows against the operator's named rollout.
- **media**: W3b and W5b landed, the rejected column is zero for the first time
  since 2026-09-05. W5b closed a real blocker — `_prefetch` wrote raw nix32
  into a `hash =` slot, which nix refuses at eval, so the weekly probe would
  have failed in exactly the week upstream moved. W4 and W6 are ready and have
  never had the operator's word.
- **Helm Home sub-project 1** is planned and cleared: 37/42, six-row floor
  passed, ten tasks HH1–HH10, judgement at
  `docs/reviews/plan-judgements/2026-09-08-helm-home-1.md`. It asks three
  questions, each with a default (two switches vs one → two; the refresh
  payload class → the spec's; dsh-harness seats → DeepSeek only).
- **A standing bugs plan exists** (`docs/superpowers/plans/2026-09-09-bugs.md`),
  on the operator's decision that bug context is gathered by DeepSeek Flash and
  the fix written by DeepSeek Pro. `plan-defects.toml` records defects in PLAN
  TEXT keyed on gate rejections; nothing tracked defects in landed, switched
  code, and this session found about ten.

## The two open bugs

- **BUG1 — the broker bypass. The most serious thing open, and it is live.**
  `factory-task` has two arms: `:378` submits through `seat-submit` to the
  `seat@` unit (behind the broker), `:429` launches `dsh-openrouter` directly
  with no `--broker`. `seat-submit` is not on the host PATH, so the direct arm
  ALWAYS wins and no seat request has ever crossed a broker. Measured
  consequences: no usage recorded (so the whole spend plan reads an empty
  stream); the egress policy never applied — the live seat policy carries
  `body_patch provider {data_collection: deny, zdr: true}`, `allow
  [openrouter.ai]` and `deny_paths /api/v1/messages`, none of which any seat
  request ever met; and **a live breach of `docs/brief.md:69-70`** ("No agent
  process holds a provider credential on disk or in its environment in
  plaintext") plus invariant 3, because `dsh-openrouter.sh:343` exports the
  operator's own key. BUG1a's gather was rejected for citing `:362` (the codex
  arm) instead of `:378`; BUG1ab is re-gathering with the corrections carried.
  **The orchestrator recommended pausing all seat dispatch until this is fixed;
  the operator has not ruled, and asked for other work meanwhile.**
  The likely fix only became possible this morning: the `seat@` route injects
  the broker's placeholder credential correctly but could not boot until switch
  #24. BUG1ab must establish what makes `:378` win AND what that breaks in the
  driver's `FACTORY-RESULT` parsing, since the direct arm pipes stdout while the
  unit route returns through the job dir.
- **BUG2 — the drive seat's URL.** After switch #24 the drive seat BOOTS
  (`seat@20260909-093102-22caa2` reached `active`), but the browser answers
  `dsh web authentication required`. `pkgs/seat/seat-run.py:129` CONSTRUCTS
  `f"http://{namespace}:{port}"` instead of reading dsh's printed token URL, and
  `:137` runs the harness with `capture_output=True`, so the real URL is
  buffered for the life of the server. Not recoverable from outside. SD7's VM
  step asserts `url.txt == http://10.100.4.2:43202` — the constructed string
  compared against itself, which is why nothing caught it.

## Recipes (verbatim, corrected by this session)

- **The gate**: `cp ~/factory/bin/opus-gate.js <session scratchpad>/` first —
  the Workflow tool refuses a `scriptPath` outside the working directory, and
  copying it beats re-sending the script inline. Then
  `Workflow({ scriptPath: '<scratchpad>/opus-gate.js', args: { run, key, plan,
  date, scratch: '<scratchpad>/gate/<run>-<KEY>', base, head, subject,
  acceptance, touches, prior, model: 'opus', effort: 'high', repo, ws, note } })`
  with `base`/`head` from `~/factory/runs/<run>/<KEY>.result` and
  `subject`/`acceptance`/`touches` byte-exact from the section. **A per-key
  scratch dir, always** — parallel gates sharing one corrupt each other.
- **Landing**: `write-board`, commit the review by pathspec (`git add` it first
  — an untracked file cannot be committed by pathspec), then
  `factory-integrate <run> <repo> <KEY>`, then
  `git -C <repo> pull --ff-only ~/factory/base/<repo> integ/<run>`. Merge main
  into the workspace FIRST, every time; main moves under you constantly and the
  ff will refuse.
- **`factory-integrate` REFUSES a task commit that changes `docs/OPERATIONS.md`
  outside the queue block.** This is written on the board and was rediscovered
  the hard way. Never write a section that asks a seat to edit the board.
- **The rung comes from the KEY, and it silently outranks the section's intent.**
  `factory_rung_of_key` (`factory-lib.sh:799-810`): `*[0-9][a-z]` → rung 2,
  a suffix with `r` → rung 3, no suffix → rung 1. A gather stage must be keyed
  unsuffixed to reach Flash. `BUG1a` climbed to rung 2 and ran on Pro because
  of one letter.
- **The guard's refusals, learned this session**: a heredoc and a plan path in
  one Bash command is refused (write the message file with the Write tool); a
  typed heading cannot be renamed or removed (withdraw it with a status row in
  `docs/ledger/task-status.toml`); `git checkout --` on a plan path is refused
  too. All three are the guard working correctly.
- **Never measure a row count through `head`** — it SIGPIPEs the writer and
  truncates. A "7 rows" measurement nearly became a false MAJOR against a
  correct fix round; the real count was 20.

## Decisions for the operator

1. **Pause seat dispatch until BUG1's fix lands?** Every seat run exports the
   key and drops the ZDR directive. Recommendation: pause. Not ruled.
2. **SP4, go or hold.** It will be correct and nearly empty until BUG1 is
   fixed: `openrouter-usage` has no rows at all.
3. **Helm Home 1's three questions**, each with a default (above).
4. **W4 and W6** in media, never worded.
5. **Should a gather RETRY stay on Flash?** BUG1ab is on Pro because a rejected
   task's retry climbs the ladder. That is defensible but departs from the
   stated shape; a one-line rule in the bugs plan settles it either way.

## The pattern this session, which is the thing worth carrying

Fifteen gates, five rejections. **Six of the defects were the orchestrator's
plan text, not any seat's work**: a lint guard that matched its own copied
source; a red procedure that could not go red because untracked fixtures are
excluded from `${self}`; a missing kind declaration that moved a crash instead
of fixing it; a record shape typed from a name instead of measured; and twice
in a row, an hour apart, a closing condition the actor could not satisfy — once
in a section a seat never sees, once demanding a check assert a file outside
its sandbox.

The mechanism behind most of them: **exit status cannot distinguish "fails"
from "fails usefully."** SD12 and SD12b both passed honest red-before-green
checks while the guard named no file; only a grep count over the failure output
told them apart. The same shape appears in `seat-vm` (a fixture that patched
the unit under test), in SD7's URL assertion (a constructed string compared
against itself), and in W5b's SRI test (a stubbed converter proving the call
happened, not the output).

The seats were not the weak link. They disclosed every deviation, and three
times a seat caught an error in the section it was given — SP2b found a third
site the plan denied existed, W5b found an unsatisfiable source count, SD12b's
own honesty about a blocked mutant is what exposed the guard defect. When two
seats failed on the same one-line fix, escalating to the Claude rung solved it
in one attempt; that was the operator's instruction and it was right.
