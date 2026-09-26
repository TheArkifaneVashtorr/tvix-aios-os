# AGENTS.md — directions for ZCode working in this repository

You are ZCode, run by the operator directly on the host (no lane, no broker,
no seat: your traffic is the operator's own). Read `CLAUDE.md` now — it holds
the house rules and binds you exactly as it binds Claude Code. This file adds
only what differs for your harness. Landed 2026-09-19 (`86cb0b1`); the hook
wiring and the skill port below came the same day. If this file and
`CLAUDE.md` ever disagree, `CLAUDE.md` wins; fix this file.

## This repo's hooks, wired for ZCode

`.zcode/config.json` runs the same gates Claude Code gets, through
`tools/zcode-hooks.sh` (the adapter: ZCode parses hook stdout as strict
JSON and takes a deny from exit code 2, so the Claude decision objects are
translated). SessionStart injects the brief — board queue, evidence
bundle, task brief, in-flight seats, operator model. PreToolUse runs
`orchestrator-guard.sh`: append-only plan headings, the ritual override and
the guard file are the operator's, the host rules (sudo, nixos-rebuild,
mutating systemctl) and the git-history rules. Stop runs the reset ritual's
derived half.

Two gaps to know. ZCode has no PreCompact event: before a reset, write the
handoff yourself — `bash tools/ritual.sh precompact "$PWD"` — and know the
SessionStart `compact` arm still re-injects the brief after a compaction.
`ORCHESTRATOR_GUARD=off` lifts the guard only from ZCode's own launch
environment, never from a session shell. If a hook does not fire (the ZCode
log records every run), the manual steps are the contract:

- **At session start:** `bash tools/session-start.sh </dev/null` (always
  close stdin; the reasons are in `docs/runbooks/session.md`). Read the
  newest `docs/board/handoff-*.md` and the top of `docs/board/log-2026-09.md`
  before proposing work.
- **Before you end a turn that touched the tree:** the reset ritual's
  derived half (`docs/runbooks/session.md`): reviews filed and committed,
  staged work landed or parked, the board block regenerated
  (`evidence tasks --root . write-board`), the turn's log entry appended.
- **Commits:** only through the devShell (`nix develop -c git commit -F
  <msgfile>`) so the lint gate has its tools; subjects follow the house
  convention. `git add` any new file before a `nix build` sees it.

## Facts specific to you

- The evidence-store skill is ported for you at `.agents/skills/
  evidence-store/` (same bytes as `.claude/skills/`); the packaged
  `evidence bundle --markdown` remains the live-facts command.
- Model choices for sub-agents and workflows are rows in
  `docs/ledger/routing.toml` (resolve with `factory_route`), never
  hardcoded ids — the table's header says why.
- Data classes (brief §3) bind you even without a broker: nothing marked
  `local-only` — baskets, `~/.claude`/`~/.codex`/`~/.hermes` state,
  `~/strategy`, broker audit logs, the `unrelated/` political files that
  travel with the Downloads survey workspaces — is pasted into a web search
  or any prompt that leaves the machine. No secrets in the repo, and none in
  your memory files.
- You have no seat in the factory: day-to-day tasks run through the seat
  driver (`tools/factory/seat/`, runbook `docs/runbooks/lanes.md`). Work the
  operator hands you directly is the exception, and it follows the same
  gates: the failing check first, acceptance measured, the operator says
  "test passed".

## How to report

Short. What you ran, what happened, the exact error text when something
failed, what you propose next. An unmeasured claim is not a result.
