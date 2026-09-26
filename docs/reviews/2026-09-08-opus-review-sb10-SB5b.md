---
plan_defect: none
mutants_total: 0
mutants_killed: 0
mutants_outside_named: 0
---
# Opus gate — seat run sb10, task SB5b — APPROVED

## Summary

SB5b is a docs-only task: five files must match nine measured Facts (F1–F9)
and five numbered contract items. Working in a fresh clone of
`/home/dalhaka/factory/ws/sb10/SB5b` at `task/SB5b` (base `b932735`, head
`0443648`), I re-ran every command the section's Facts name and read every
cited line in `pkgs/seat/seat-submit.py`, `pkgs/seat/seat-run.py`,
`nixosModules/seatLane.nix`, `nixosModules/egressBroker.nix`,
`pkgs/broker/policy.py`, `pkgs/dsh-openrouter/dsh-openrouter.sh`,
`hosts/core/proton-backup.nix`, `hosts/core/seat.nix` and
`docs/runbooks/switch-helm-gaming.md`. Every command, path, unit name, exit
code and line citation the new runbook and the other four files state agrees
with what is actually in the tree. `lint` passes under `--rebuild`,
`githooks/pre-commit` exits 0, `claims.py validate` and `tasks.py check` are
silent, and `docs/MAP.md` is untouched. One commit, subject byte-identical to
the contract, trailers in place, plan file untouched. One unexplained
collateral file (`docs/OPERATIONS.md`'s queue block) is a MINOR, not a MAJOR:
it is the pre-commit hook's routine board regeneration (permitted by Global
Constraints), not a hand-edit, and it does not affect any of the section's
five files or the `lint` acceptance check.

## Contract items

**Item 1 — `docs/runbooks/seat.md` (new, ≤ 150 lines, H1 + eight `##` sections in order, one fenced command + one sentence each).**

- File is 103 lines (`wc -l docs/runbooks/seat.md` → 103). MET.
- H1 line 1: `# The seat behind its broker — the operator's runbook` — byte match to the contract. MET.
- Section order (`grep -n '^## ' docs/runbooks/seat.md`): `What runs where` (10), `Before the first job` (27), `Start a web seat and open it` (38), `Run a headless job by hand` (50), `Watch the audit` (61), `Stop a job` (72), `Delete the key file after the first successful jobs` (82), `Roll back` (96) — exactly the contract's (a)–(h) in order. MET.
- Fence count: `grep -c '^```' docs/runbooks/seat.md` → 16 (8 sections × open/close), and an `awk` pass confirms each section owns exactly one pair between its heading and the next. MET.
- (a) *What runs where*: covers the broker instance `seat` 10.100.4.1→10.100.4.2:3141, allowlist — verified `host` defaults to `"openrouter.ai"` alone (`nixosModules/seatLane.nix:25`), `hostAddress`/`namespaceAddress` documented at `:39,43`, `listenPort = 3141` at `hosts/core/seat.nix:15`; the unit, job dir and file list (`job.json brief stdout.txt stderr.txt exit_code.txt result.txt url.txt`); the two key files (F5, verified below); "not backed up" (F8, verified below). MET.
- (b) *Before the first job*: `systemctl show -p ActiveState,Result seat@<id> && journalctl -u seat@<id>.service`; text matches the section's own "Why SB5 cannot be landed" paragraph — confirmed `pkgs/seat/seat-run.py:38` opens `job.json` unconditionally in `_load_job`, and `pkgs/dsh-openrouter/dsh-openrouter.sh:506-511` `mkdir`/`chmod 700`s `${DSH_CACHE_ROOT:-/tmp}` on every launch. MET.
- (c) *Start a web seat*: command byte-identical to the commit body's pasted block; text states `seat-submit web` prints the job id, starts the unit, returns 0, and passes no `--model` — confirmed at `pkgs/seat/seat-run.py:92-95` (web branch's `cmd` has no `--model`) while `--model` is `required=True` at `pkgs/seat/seat-submit.py:47` (so the parser still demands it, only unused for web) — the runbook's own wording ("the web mode passes no `--model`, so your saved picker selection decides") reads correctly against this. URL command/print at `seat-run.py:105-109` (`url = f"http://{namespace}:{port}"` → `_write(.../url.txt)` → `print(url, flush=True)`), matching F2. MET.
- (d) *Run a headless job*: command matches; polling interval/timeout confirmed at `pkgs/seat/seat-submit.py:36` (`DEFAULT_TIMEOUT = 10800`) and `:127` (`time.sleep(POLL_INTERVAL)`). MET.
- (e) *Watch the audit*: `jq -c 'select(.verdict=="allow")' /var/lib/egress-broker/seat/audit.jsonl` and the separate `dsh-openrouter --denials 20` line — audit path confirmed at `nixosModules/egressBroker.nix:29` (`audit_log = "/var/lib/egress-broker/${name}/audit.jsonl"`), field order confirmed at `pkgs/broker/policy.py:91-109` (`ts instance client method host host_header sni path bytes_out bytes_in verdict reason`), append-without-chmod confirmed at `policy.py:110`. MET.
- (f) *Stop a job*: `systemctl stop seat@<id>`; polkit grant confirmed at `nixosModules/seatLane.nix:229-244` (verbs `start`/`stop`/`restart` on `seat@*.service` for `subject.user == cfg.operatorUser`, no sudo); absence of `KillMode`/`ExecStop` confirmed by `grep` over lines 160-203 (no hit). MET.
- (g) *Delete the key file*: `rm ~/.config/openrouter/key`; deprecation print and `die 4` message text byte-match `pkgs/dsh-openrouter/dsh-openrouter.sh:309` and `:330`; the claim-row flip language matches item 4. MET.
- (h) *Roll back*: rollback command byte-identical to `docs/runbooks/switch-helm-gaming.md:216-234`'s house form (`sudo /nix/var/nix/profiles/system-<N>-link/bin/switch-to-configuration switch`), and "46 live today, 45 its rollback" matches `docs/OPERATIONS.md`'s live-generation line. MET.

**Item 2 — `docs/runbooks/lanes.md` paragraph before `## The key file and the tmpfiles rule`.**

- Base file's line 103 is exactly `## The key file and the tmpfiles rule` (`git show b932735:docs/runbooks/lanes.md | sed -n '103p'`). The diff inserts a new `## The operator's seat is a lane too` section (10 lines) immediately before it, naming `services.seat-lane`, `nixosModules/seatLane.nix`, the broker instance `seat`, 10.100.4.x, `seat@<id>` as the operator, "the key never in the unit", `docs/runbooks/seat.md`, and distinguishes it from `tools/factory/seat/` — confirmed that heading exists at base line 445 (`## The seat driver is versioned at \`tools/factory/seat/\``) and already uses "seat" for the driver, matching F9. MET (the content is delivered as its own `##` subsection rather than a bare paragraph dropped into prose; this reads as a faithful, better-structured rendering of the same content and is not a defect).

**Item 3 — CLAUDE.md: exactly one line after the `dsh-openrouter --denials [N]` line (32), no `systemctl start` line anywhere.**

- `nl -ba CLAUDE.md` confirms line 32 is unchanged (`dsh-openrouter --denials [N]  # read back...`) and line 33 is the new one: the item-1(c) command with comment `# OPERATOR ONLY — a web seat behind the broker; the URL: journalctl -u seat@<id>.service (docs/runbooks/seat.md)` — byte-identical to the contract text. `git diff` for CLAUDE.md shows exactly one line (`+1` in stat). `grep -n "systemctl start" CLAUDE.md` matches only the pre-existing prohibition sentence at line 11, no new occurrence. MET.

**Item 4 — `docs/ledger/claims.toml` row `seat-key-exception-undecided`: only `closes_by` changes; `claims.py validate` silent.**

- `git diff` for the file is a single-line replacement of `closes_by`; `status`, `class`, `owner`, `opened`, `review_by` are unchanged in the surrounding context. New `closes_by` value is byte-identical to the contract's stated path. `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-08` → exit 0, no output. MET.

**Item 5 — decision file addendum appended at the end.**

- Base file is 97 lines (`git show b932735:… | wc -l` → 97). New file is 101 lines; the last five lines are the new `## Addendum 2026-09-08 (SB5b): the seat's key exception closes by design` heading (matches the format of the file's other addenda: `## Addendum <date> (<who>): <title>` at lines 37/57/87) followed by the four sentences the contract specifies (the one open exception; since generation 45 the seat runs behind its own broker with the key injected at egress; the plaintext file is deleted after the first two live jobs, which wait for SD5 and switch #22; until then the deprecation line and the dated claim row). MET.

## Red before green

N/A — docs task, no test named. (Confirmed with the orchestrator's own framing: the section's contract is "five files match nine measured facts", not code with a red/green test.)

## Mutants

None named in the section for a docs task. `mutants_total: 0`, `mutants_killed: 0`, `mutants_outside_named: 0` — none attempted, per the orchestrator's instruction not to invent mutants for a docs task.

## Checks

- `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` → exit 0 (js-lint, treefmt/nixfmt, shellcheck, ruff, etc. all green; the two intentional-bad fixture files under `tests/lint/fixtures/` still report their expected errors, which is the fixture's job, not a build failure).
- `nix develop -c githooks/pre-commit` → exit 0. It printed `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again` and rewrote the queue line to drop `SB5b` (now landed) while keeping `SB5 SB6 SB6b`. This means the `docs/OPERATIONS.md` queue block *as committed* in `0443648` is already one step stale immediately after landing (it still lists `SB5b` as queued) — see Findings MINOR-1.
- `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-08` → exit 0, silent.
- `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → exit 0, silent.
- `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` → exit 0, no diff (runbooks are not tracked by MAP.md, as stated by the task).
- No Python source under the section's touches, so `ruff check`/`ruff format --check` are not applicable.

## Touches and commit

- Diff stat: `CLAUDE.md` (+1), `docs/OPERATIONS.md` (+1/-1), `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md` (+4), `docs/ledger/claims.toml` (+1/-1), `docs/runbooks/lanes.md` (+10), `docs/runbooks/seat.md` (+104, new). All five contracted files are present and correct; `docs/OPERATIONS.md` is the one file outside the stated touch list and outside the "docs/MAP.md by rule" carve-out, and the commit body does not mention it. It is the pre-commit hook's own board-queue regeneration (permitted generically by the plan's Global Constraints: "it may regenerate the board block once: `git add docs/OPERATIONS.md` and commit again"), not a hand-edit, and it does not touch `lint`'s pass/fail. Recorded as MINOR-1, not a MAJOR, because it is process-permitted collateral rather than an unexplained substantive change — but the committed content is stale (see Checks).
- One commit (`0443648`) on top of base `b932735`; `git log --oneline b932735..HEAD` shows only this commit.
- Subject is byte-identical to the contract (`diff` against a hand-typed copy showed no difference).
- Body states the why (SB5's brief-recipe failure, in three clauses matching the section's own "Why" paragraph) and pastes both `seat-submit --help`'s real output and the runbook's own commands, matching Step 2's instruction to paste `--help` "beside the runbook's commands".
- Two trailers after a blank line: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run sb10)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- No board commit (the board regeneration is folded into this same commit, not a separate one — matching "one commit").
- `docs/superpowers/plans/2026-09-05-seat-behind-broker.md` is untouched (`git diff b932735..HEAD -- <plan path>` is empty).

## Findings

**MINOR-1** — `docs/OPERATIONS.md:15` (the `<!-- tasks:begin -->…<!-- tasks:end -->` queue line). The line committed in `0443648` reads `… SB5 SB5b SB6 SB6b …`, still listing `SB5b` as queued even though this very commit lands it. Re-running `nix develop -c githooks/pre-commit` on a clean checkout of `HEAD` regenerates the block again and drops `SB5b`, producing `… SB5 SB6 SB6b …` — proof the committed board is stale by one step. This is a structural property of the process (a commit's own regeneration necessarily can't see itself land) rather than a mistake specific to this implementer, and it does not affect `lint` or any of the section's five contracted files. Worth a follow-up commit to re-true the board, but not gating.

## Verdict

APPROVED. All five contract items are met with file:line evidence; every Fact (F1–F9) the section cites was re-verified against the live source; `lint` passes under `--rebuild`; `claims.py validate` and `tasks.py check` are silent; `docs/MAP.md` is untouched; the commit is a single commit with the exact contracted subject, the required trailers, and a body that states the why and pastes the `--help` red/green-equivalent evidence the Step asked for. One MINOR (stale `docs/OPERATIONS.md` queue line, process-caused, non-gating) is recorded; no MAJORs found.
