# Opus gate — seat run sc3, task G7b — APPROVED

Reviewer: Sonnet (docs gate)

## Summary

- One commit on base (`84222fe`, "integrate G10b into integ/sc3"), stat
  exactly `CLAUDE.md | 138 ++...` (1 file changed), subject byte-identical to
  the plan's, `Co-Authored-By` present alongside an extra `Generated-By` line
  (fine per the brief), size 4130 bytes (≤ 4500), lint gate and `lint` check
  both green.
- G7's rejected commit is not in this branch's history at all: the base is
  `84222fe`, not G7's `7e897bf`/`7e897bf`-line commit, and `7e897bf` does not
  even resolve to an object in this clone (it was never fetched from G7's
  workspace) — confirms the fix round started clean from main, not from
  G7's branch.
- Both blocking findings from the G7 rejection are fixed: the `## Where
  things are` block is present and byte-identical to the plan's fenced text
  (diffed, zero difference), and all seven gotchas are back, including the
  two that were previously dropped (the "shell tool vs. file tool see
  different `/tmp`" gotcha and the `git add` before `nix build` gotcha —
  both present in substance). Zero hits for leaked harness text
  (`WORKSPACE RULES`, `task/G7`, `FACTORY-RESULT`, `Generated-By` as a
  content grep target — the actual `Generated-By:` trailer lives in the
  commit message, not the file, so the file-content grep correctly returns
  0).

## Checks

- Clone/branch: throwaway clone of `/home/dalhaka/factory/ws/sc3/G7b`,
  `task/G7b` checked out, head `62474bf023a299219a1d562ae5fb58df16741d8c` —
  matches `G7b.result` exactly (`head:` and `base: 84222fe...` both match).
- `git show --stat HEAD`: `CLAUDE.md | 138 +++++++++++++-------------------------------------------------` (1 file changed, 29 insertions, 109 deletions) — pass, CLAUDE.md only.
- Subject: `docs: CLAUDE.md shrinks to rules, commands and pointers; the map
  and the hook carry the rest (test: lint)` — byte-identical to both G7's and
  G7b's plan `commit subject:` (fix rounds keep the original subject) — pass.
  Trailers: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813
  (seat headless, factory run sc3)` then `Co-Authored-By: Claude Fable 5.1
  <noreply@anthropic.com>` — pass.
- `wc -c CLAUDE.md` → 4130 — pass (≤ 4500).
- `grep -c 'WORKSPACE RULES\|task/G7\|FACTORY-RESULT\|Generated-By' CLAUDE.md`
  → 0 — pass.
- `## Where things are` block: present, and a line-for-line diff against the
  plan's fenced text (`docs/superpowers/plans/2026-09-05-session-context.md`
  lines 1518–1525) shows zero differences — pass, byte-identical.
- All seven gotchas, checked against the plan's explicit list: `git add`
  new files before `nix build` — present; statix rejects `{ ... }:` headers,
  write `_:` — present; never `2>/dev/null` a gated command — present;
  `hosts/core/hardware-configuration.nix` verbatim/exempt — present; a
  switch does not start newly enabled user timers — present; `$HOME`
  read-only under a harness sandbox, set `XDG_CACHE_HOME` under `/tmp` —
  present; shell tool vs. file tool see different `/tmp`, name one scratch
  directory for both — present. All seven pass.
- The one rule (host runs live, build-only, never
  sudo/nixos-rebuild/systemctl/basket mount-teardown, `docs/brief.md` §3
  invariants pointer, `docs/OPERATIONS.md` board pointer) — kept in
  substance, pass.
- Commands block: present, plus both required new lines —
  `nix develop -c python3 pkgs/evidence/tasks.py --root . brief` and
  `python3 pkgs/evidence/repomap.py --root . write` — pass.
- "How work is done here": kept in substance plus the required derived-queue
  sentence, present verbatim as "The queue is derived by `evidence tasks`,
  never typed into the board." — pass.
- Every backticked path checked against the working tree, plus every path
  named in the fenced Commands block checked by hand (`githooks/pre-commit`,
  `tests/unit`, `tests/broker`, `pkgs/evidence/tasks.py`,
  `pkgs/evidence/repomap.py`, `pkgs/evidence/claims.py`,
  `docs/ledger/claims.toml`, `docs/runbooks/lanes.md`, `/tmp`,
  `docs/brief.md`, `docs/MAP.md`, `docs/OPERATIONS.md`,
  `docs/runbooks/session.md`, `hosts/core/hardware-configuration.nix`,
  `tools/factory/dark-factory.js`, `tools/session-start.sh`) — every one
  exists. Non-path backticked tokens (`bats`, `Co-Authored-By`, `core`,
  `factory-review`, `grep`, `jq`, `nixosConfigurations.core`,
  `nixos-rebuild`, `python3`, `sudo`, `XDG_CACHE_HOME`) are commands/flags/
  attrs, correctly not paths.
- `nix develop -c githooks/pre-commit` → all checks passed (treefmt,
  shellcheck/statix/deadnix implied by "All checks passed!", ruff,
  render.test.mjs) — pass.
- `nix build .#checks.x86_64-linux.lint -L --no-link` → succeeded (exit 0,
  no failure output) — pass.

## What was removed and where it now lives

- The full check-name list and the `## Architecture` section (baskets,
  broker, managed settings, cowork, backups, host, helm, model lanes, seat,
  ledger-and-evidence bullets): removed as the plan requires, replaced by
  the `## Where things are` pointer to `docs/MAP.md` (confirmed present,
  4539 bytes, generated) and the session-start hook / `docs/runbooks/
  session.md` (confirmed present, 3522 bytes) — this is exactly the intended
  trade and both pointer targets are real.
- The "Factory runs start `dsh-openrouter` from `~/factory`..." paragraph
  (the `base/`/`ws/` layout, 0700, `docs/runbooks/lanes.md` pointer):
  removed. Recoverable from `docs/runbooks/lanes.md` (lines ~403–410,
  grepped and confirmed present) — not one of the three sources the review
  brief names (`docs/MAP.md`, `docs/runbooks/session.md`, the board), but a
  real, current runbook; not a "cost real time" gotcha, so not blocking.
  Same disposition as the prior gate gave the Architecture bullets.
- The detailed mechanism text inside the `$HOME`/`XDG_CACHE_HOME` and
  shell-vs-file-tool gotchas (the exact `nix` error strings, "never
  `$(mktemp -d)` per command", "dsh gives the shell a fresh tmpfs..."):
  condensed to one sentence each per the plan's explicit instruction
  ("each one sentence"). The core lesson of both survives; not a finding.
- "How work is done here" specifics (plan/spec/decision/concept directory
  pointers, the model-policy document pointer, the "unmeasured claim is
  dated debt" sentence, the test-based-reality-amendments pointer, the
  research-digest rule, the "Project memory..." sentence, the "read tool
  names literally" framing): condensed out. Recoverable from
  `docs/OPERATIONS.md` (the board), which still names the model policy and
  factory tooling in its own text — acceptable tightening, consistent with
  the prior gate's treatment of the same paragraph.
- "read its START HERE block ... rewrite START HERE every turn, append to
  `docs/board/log-<month>.md`" procedural detail: removed from the one-rule
  paragraph, but this is board-maintenance procedure documented directly in
  `docs/OPERATIONS.md` itself (its own "Where things are" section, lines
  77/86–87) — recoverable from the board, not a finding.
- Both previously-dropped, time-costly gotchas (`git add` before `nix
  build`; shell-tool-vs-file-tool `/tmp` divergence): restored verbatim in
  substance — the G7 rejection's blocking Finding 2 is resolved.

## Findings

None blocking. No leaked harness text, no missing pointer block, no dropped
gotcha, no broken path, no failing check.

## Deviations

- None from the review procedure. Tooling only via `nix develop -c ...`;
  workspace was read-only (throwaway clone in scratch); no commit made; live
  host untouched.
