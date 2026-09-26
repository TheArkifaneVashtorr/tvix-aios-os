# Handoff — session 23 → the next session (2026-09-09 ~14:00 CDT; Fable 5.1, then Opus 5)

Paste to the next session: **"Read docs/board/handoff-2026-09-09-session-23.md, then the SessionStart facts. Nothing launches without my word."**

## Why the reset

Context, not a limit. The session ran 04:53 → ~14:00 CDT: four bugs found and
fixed, two switches, sixteen seat runs, twelve Opus gates. Nothing is
mid-flight. The board, `evidence bundle` and the task brief carry the state;
this file carries what they cannot — why things are the way they are, and what
the next session should not have to rediscover.

## The state on main (`1bfe87a`, live gen 51)

**Both switches landed and were verified.** #25 → gen 50 (11:49 CDT), FIX1 +
FIX2 + FIX3b. #26 → gen 51 (~13:30), FIX4. Live = HEAD, `systemctl --failed`
0. Rollback for the live system is `system-50-link`. The three-command switch
recipe (activate, register, boot) is in the session-22 handoff and was used
unchanged both times; a switch still needs all three.

**Four bugs closed today, each gathered, gated and switched:**

- **BUG1 — the broker bypass (FIX1).** `factory-task:378` reached the `seat@`
  unit only when `command -v seat-submit` succeeded, and `seat-submit` lived on
  the unit's own PATH alone, so the host always fell into the direct arm and
  exported the operator's key: a live breach of `docs/brief.md`'s invariants 2
  and 3 on every seat run since the lane was built. The lane module now puts
  `seat-submit` on `environment.systemPackages` (as `modelLane.nix` already did
  for its CLI), `seat-eval` asserts it, and `factory-task` resolves
  `$SEAT_SUBMIT` then PATH and **refuses with exit 2** rather than degrading
  into the direct arm; the direct arm runs only under `FACTORY_SEAT_UNIT=0` and
  names itself in the run log.
- **BUG2 — the drive seat's URL (FIX2).** `seat-run` constructed
  `http://<namespace>:<port>` and buffered the harness with
  `capture_output=True`, so dsh's real token URL never left the process. It now
  streams the harness through `Popen`, writes `stdout.txt` and the journal per
  line, and publishes dsh's own line with `127.0.0.1` replaced by the namespace
  address. The VM asserts the token, the 303 with its cookie, the 200 through a
  cookie jar and the 401 without — never a constructed string against itself.
- **BUG3 — the board's repo key (FIX3b).** `board_graph` named the repo by the
  directory basename, so in any clone not called `nixos-agent-env` the
  withdrawn/parked rows stopped matching and `write-board` re-queued withdrawn
  tasks; it had reached `main` twice (`0443648`, a seat commit; `4ec8951`, a
  landing-run merge). `docs/ledger/repos.toml` now carries `ledger = true` on
  its own entry, `load_repos` refuses two flagged entries everywhere, and the
  block is byte-identical across clone names.
- **BUG4 — the drive seat's API 403 (FIX4).** Found by the operator minutes
  after switch #25: the page loaded, `directoryPicker/list` answered 403.
  dsh's `isTrustedApiRequest` runs *before* authentication and accepts only a
  loopback Host header or an authority given by `--trusted-host`; the browser
  reaches dsh through the socat relay, so its Host header is the namespace
  authority, and the wrapper never passed the flag. The web exec now passes
  `--trusted-host "${bind_namespace}:${web_port}"` under `--bind-namespace`.
  Verified on the live host after #26: the API path answers `401 unauthorized`.

**The seat lane is now the default route.** Every factory task goes through
`seat@` and its broker. The journal shows `credential: placeholder (broker
injects)`, the `.result` carries `seat: unit seat@<id>`, and
`/var/lib/egress-broker/seat/usage.jsonl` records cost, provider, the cache
split and a generation id per request. One Pro fix run measured **$4.36**
(12.5 M prompt tokens, 9.9 M cached, CoreWeave).

## The one gap this session leaves

**Nothing ingests the broker's usage file.** No timer, no unit, no driver step
(`grep -rn 'openrouter-usage' nixosModules hosts tools` finds none). The
orchestrator ran `evidence ingest openrouter-usage
/var/lib/egress-broker/seat/usage.jsonl` once by hand at 07:39, so
`ledger/openrouter-usage` holds 108 rows against the broker's 266, and the gap
grows with every seat run. **SP4 reads that stream**, so this is owed before
SP4 means anything. Two shapes, neither typed yet: a systemd timer beside the
evidence store, or the seat driver ingesting after each run exactly as it
already ingests checks and results. The second is cheaper and keeps the store
in step with the runs that produced it.

## Recipes, corrected by this session

- **Commit the board's regenerated block BEFORE every dispatch.** A seat clones
  `main` at launch; a block that is stale at that commit makes the hook's G8c
  check refuse a commit for drift that is the orchestrator's. FIX3 committed
  the board because of it and was rejected.
- **A pathspec commit does NOT quiet G8c.** Measured by the FIX2 gate on git
  2.54: `git commit -F <msg> -- <files>` builds a temporary index and the hook
  diffs against *that*, so staging the board never helps. The route this plan
  named for two hours was a wrong fact. If a seat sees G8c drift now, it is the
  orchestrator's: the seat stops with `status=partial` and the diff.
- **A fix STAGE is its own root (`FIX<n>`), never `BUG<n>b`.**
  `pkgs/evidence/tasks.py:59` (`CHAIN_RE`) reads any trailing lowercase letters
  as a fix round of the same chain, so `BUG1b` would derive as landed the
  moment the gather chain landed and never schedule. `implement/code` routes to
  Pro at rung 1 already, so a fresh root needs no suffix.
- **`factory-wave` never passes `--prior`.** A fix round must be dispatched
  with `factory-task <run> <repo> <KEY> --prior <prior run>/<prior KEY>`, or
  the seat never sees the rejecting review.
- **Launch lines need nothing special now.** Before switch #25 they needed
  `SEAT_SUBMIT=<toplevel>/sw/bin/seat-submit` (the unit route) or
  `FACTORY_SEAT_UNIT=0`; after it, `seat-submit` is on the host PATH and the
  unit arm wins on its own.
- **Under the agent harness's auto mode**, the classifier refuses `setsid -f
  bash -c '…'` wrappers and chained `git … && factory-…` commands. One bare
  command per call with `run_in_background: true`; `factory-wave` wraps itself
  in `setsid -w` already.
- **Two integrates cannot overlap.** The fast-forward pull refuses once `main`
  moves, so land the first before committing anything for the second.

## Decisions for the operator

1. **The usage ingest** (above) — a timer, or a step in the seat driver.
2. **SP4, go or hold.** Its stream has real rows now, which was the objection
   last session; the ingest gap is the remaining caveat.
3. **Helm Home 1's three questions**, each with a default (two switches vs one
   → two; the refresh payload class → the spec's; dsh-harness seats → DeepSeek
   only).
4. **W4 and W6** in media, ready and never worded.

## The pattern this session, which is the thing worth carrying

Twelve gates, six rejections. **Three gather chains were each rejected for the
same defect: a pasted command output that the pasted command does not
produce** — a filter that filters nothing while the document reports six lines
instead of 337; a hunk line that does not exist in the commit it claims; a
`grep -n` block containing two line numbers its own pattern cannot match. Every
conclusion was right each time. The gates caught all three by re-running the
commands, which is the only reason the fix stages were typed from measurements
rather than from confident prose.

**The lever not pulled:** all nine gather runs ran at effort `off`. The
`implement/docs` rows keep Pro at `off` through rung 2 and only reach `medium`
at rung 3, and a key earns rung 3 by carrying an `r` in its suffix
(`factory_rung_of_key`). My fix rounds were keyed `b` and `c`, so three
consecutive rounds of the same chain all ran at the cheapest effort. A third
round is exactly the case the ladder exists for; the next session should key it
`<KEY>rb` and see whether medium effort ends the invented pastes.

**Three of the six rejections were the orchestrator's plan text**, not any
seat's work: two wrong facts (a "the answer will still be zero" carried from a
gate, and the pathspec commit route) and one vacuous mutant (a test that
asserted the key but not the name the mutant changed). The seats disclosed
every deviation and one of them found a defect in the section it was given.
