---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run sc3, task G7 — REJECTED

Reviewer: Sonnet (docs gate)

## Summary

- One commit on base, stat = CLAUDE.md only, subject byte-identical to the
  plan's, `Co-Authored-By` present, size 4492 bytes (≤ 4500), lint gate and
  `lint` check both green.
- But the task's one explicit content requirement — replace the Architecture
  section and the check-name paragraph with a `## Where things are` block
  pointing at `docs/MAP.md` and the session-start hook — was not done. In its
  place the commit inserted a `## WORKSPACE RULES` section that is leaked
  seat-harness task-briefing text (branch `task/G7`, this run's
  `Generated-By` line, the `FACTORY-RESULT` reporting format), not project
  content.
- Two of the base's six gotchas explicitly flagged as having "cost real
  time" were dropped and are not recoverable from `docs/MAP.md`,
  `docs/runbooks/session.md`, or `docs/OPERATIONS.md`.

## Checks

- Clone/branch: `/tmp/.../scratchpad/gate-sc3-G7`, `task/G7`; head
  `7e897bf` / base `2867b98` match the `.result` file exactly.
- `git show --stat HEAD`: exactly `CLAUDE.md | 191 ++++...` (1 file changed) — pass.
- Subject byte-identical to the plan's `commit subject:` for G7 — pass.
  Trailers: `Generated-By: ...` then `Co-Authored-By: Claude Fable 5.1
  <noreply@anthropic.com>` — pass (Generated-By extra is fine per the gate brief).
- `wc -c CLAUDE.md` → 4492 — pass (≤ 4500).
- Every backticked token that looks like a path exists, with one exception:
  `task/G7` (a branch name from the leaked section, not a real path — see
  Findings). All real paths (`docs/brief.md`, `docs/OPERATIONS.md`,
  `hosts/core/hardware-configuration.nix`) exist.
- `nix develop -c githooks/pre-commit` → all checks passed (treefmt, ruff,
  render.test.mjs).
- `nix build .#checks.x86_64-linux.lint -L --no-link` → succeeded, no output.
- Content against the section, item by item:
  - Title — kept.
  - "What this is, and the one rule" — kept in substance: the host runs
    live, build-only, never sudo/nixos-rebuild/systemctl/basket
    mount-teardown, spec pointer `docs/brief.md` (§3), board pointer
    `docs/OPERATIONS.md` — pass.
  - Commands — kept, and both required additions present: `evidence tasks
    --root . brief` and `python3 pkgs/evidence/repomap.py write` — pass.
  - Gotchas, one sentence each — 5 of 6 kept; 2 of the original 6 dropped
    with no replacement (see Findings; one of the "kept" — `$HOME`
    read-only/`XDG_CACHE_HOME` — is fine as a single condensed sentence).
  - "How work is done here" plus the required derived-queue sentence — the
    exact required sentence is present verbatim: "The queue is derived:
    `evidence tasks` — never type task status into the board." Other
    specifics (model-policy pointer, dark-factory.js/seat driver, the
    test-based-reality-amendments pointer, research-digest rule) were
    condensed away but are recoverable from `docs/OPERATIONS.md` — acceptable
    tightening, not a finding.
  - Architecture + check-name paragraph replaced by `## Where things are`
    pointing at `docs/MAP.md` and the hook — **not done** (blocking; see
    Findings).

## What was removed and where it now lives

- The nixpkgs-pins note, baskets/broker/managed-settings/cowork/backups/host/
  helm/model-lanes/seat/ledger-and-evidence bullets, and the full check-name
  list: removed as intended by the plan. Recoverable from `docs/MAP.md`
  (generated: modules, packages, every check name, tests, hosts, tools) —
  fine, this is exactly what G2/G7 intend, **except CLAUDE.md never actually
  points the reader at `docs/MAP.md` for this purpose** (see Findings).
- Model-policy / dark-factory.js / seat-driver detail, the
  test-based-reality-amendments pointer, research-digest rule: condensed out
  of "How work is done here"; recoverable from `docs/OPERATIONS.md` (grep
  confirms `factory-model-policy`/`dark-factory` mentions there).
- The "git add new files before nix build" gotcha: **removed, not
  recoverable** from `docs/MAP.md`, `docs/runbooks/session.md`, or
  `docs/OPERATIONS.md` (grepped all three; no hit).
- The shell-tool-vs-file-tool `/tmp` split gotcha (dsh gives the shell a
  fresh tmpfs per confined command while file tools reach the host's, so a
  path one tool writes raises `ENOENT` in the other): **removed, not
  recoverable** from the same three locations (grepped; no hit).
- The session-start hook / `docs/runbooks/session.md` pointer that Step 1
  explicitly requires as the replacement content: **never written at all** —
  it is not merely condensed, it is absent, and the space where it should be
  is occupied by unrelated leaked harness text.

## Findings

1. **Blocking — the required "Where things are" block is missing.** Step 1
   of the G7 section is explicit: replace the Architecture section and the
   check-names paragraph with a `## Where things are` block naming
   `docs/MAP.md` and the session-start hook (`tools/session-start.sh`,
   `docs/runbooks/session.md`). The committed file has no such heading and
   no mention of `docs/runbooks/session.md` or the hook anywhere. Instead,
   in the same place, the commit inserts a `## WORKSPACE RULES` section
   (lines 49–81 of the new file) that is verbatim seat-harness task-briefing
   text: "This is an isolated clone made for this task; the real repository
   lives elsewhere", "on the branch `task/G7` (already checked out for
   you)", the exact `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813
   (seat headless, factory run sc3)` line, and the `FACTORY-RESULT
   status=<done|partial|failed>` reporting format. None of this is project
   guidance — it is this run's own ephemeral instructions, copied into the
   repository's permanent CLAUDE.md. It would mislead every future session
   (wrong branch name, references a one-off run) and duplicates the "one
   rule" section's sudo/nixos-rebuild/systemctl prohibition badly. This is
   the single content requirement the task names explicitly, and it was not
   met — grounds alone for rejection.
2. **Blocking — two time-costly gotchas dropped with no replacement.** The
   base's gotcha list is introduced as "Gotchas that have cost real time";
   two of its six items vanished with no trace in `docs/MAP.md`,
   `docs/runbooks/session.md`, or `docs/OPERATIONS.md`: (a) `git add` new
   files before any `nix build` (flakes only see tracked files) — this
   exact gotcha bit the seat driver on this very sc3 run per the
   `CLAUDE.md`'s own Global Constraints reminder line, so losing it is not
   theoretical; (b) the shell-tool-vs-file-tool `/tmp` divergence (dsh gives
   the shell a fresh tmpfs per confined command while file tools reach the
   host's, causing `ENOENT`) — also independently listed as a live gotcha in
   this plan's own "Gotchas that have cost real time" prose. Per the review
   brief, a dropped gotcha that cost real time is a finding on its own; two
   of them, unrecoverable, is blocking.
3. **Minor.** `task/G7` appears as a backticked token inside the leaked
   WORKSPACE RULES section; it is not a real path (it is this run's branch
   name) and would be stale/wrong text even if the section were otherwise
   legitimate. Resolves itself once Finding 1 is fixed.

## Deviations

- None from the review procedure. Tooling only via `nix develop -c ...`;
  workspace was read-only (throwaway clone in scratch); no commit made; live
  host untouched.
