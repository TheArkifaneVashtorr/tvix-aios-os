# Seat/Harness subsystem spec — the drive launch at danger-full-access, the three hooks, the off-tree memory store, N seats with allocated ports, the payload seam (spec for PL's patch series)

**Date:** 2026-09-10 (drafted against the lane's resolved model). **Authority:** the operator's redesign decisions (`docs/decisions/2026-09-09-redesign-answers.md`, numbers 13b, 21c, 36a, 57a, 58a, 59a, 60a); the charter §2 Seat/Harness row (`docs/concepts/2026-09-09a-redesign-charter.md:49`); the seat-harness context block (`docs/context/seat-harness.md`); the seat-harness redesign spec (`docs/superpowers/specs/2026-09-07-seat-harness-redesign-design.md`) whose §4 changes 2, 5 and 9 are adopted; the program plan (`docs/superpowers/plans/2026-09-09-program.md`) §6 increment 2 (`:167-173`). **Fits:** the plan `PLAN-SA` (`docs/superpowers/plans/2026-09-10-seat-harness.md`) reads this spec; PL's patch series (`patches/dsh/`) implements the harness changes this spec names as "PL's work"; every hook and memory path this spec names is the contract PL's payload fills.

**Drafted on the lane** (decision 65a, as amended 2026-09-10 to "OpenRouter only"): the model the lane serves — `deepseek/deepseek-v4-pro-0813` when Fable's ZDR exception is not in effect, or `anthropic/claude-fable-5.1` when `IS4`'s per-model exception is active (`nixosModules/seatLane.nix:182`). At this writing the lane serves both; the model that produced this text is named in the commit body.

**Gate:** Opus (manifest row `docs/ledger/subsystems.toml:114-131`, `gate = "opus"`). **Area:** `seat`. **Bounded by:** decisions 13b, 21c, 36a, 57a, 58a, 59a, 60a; the packet's §2, §3, §5 (`docs/research-2026-09-09-bug-workflow-packet.md`); the charter's §2 Seat/Harness row. **Invariants:** §3 of the brief (`docs/brief.md:68-79`) — none breached at this anchor; the spec's own G12 bindings are stated in each section below.

---

## §1 What this spec decides (standalone summary)

A reader needs no other file. This spec names what each change patches — which are PL's harness-patch series (`patches/dsh/`) and which are SA's own payload files — and states the seven design points the charter assigns to SA:

1. **The drive launch preset** — `DSH_PERMISSION_MODE=danger-full-access` for `drive` jobs only; job seats keep `workspace-write`.
2. **N seats with allocated ports** — `seat-submit drive` allocates a port from `services.seat-lane.webPortRange` instead of the hard-coded 43210; Helm's session list reads `/var/lib/seat/jobs/*/job.json`.
3. **The three hooks** — SessionStart runs `tools/session-start.sh`, Stop runs `tools/ritual.sh stop`, PreCompact re-injects the derived facts. Each is a patch in PL's series against dsh-openrouter's hook table, or payload in `hooks.json`.
4. **The seat's memory** — a machine-local store under `/var/lib/evidence/seat-memory/<workspace>/` written by the Stop hook and read by SessionStart, never a tracked file.
5. **The payload** — `AGENTS.md` and `skills/` built into `/nix/store` by PL's task; this spec names what each file must contain once the rules source generates `AGENTS.md`.
6. **The driving inbox rule** — no agent-to-agent messages, no self-nudges; subagent output arrives as a file. A patch to the harness's inbox splicing.
7. **`services.seat-lane.maxUnits` from IS1** — read by both `drive` and `headless`; the concurrency cap is enforced by `seat-spool` (since IS1c).

Acceptance per item is a `seat-eval` assertion or a `seat-vm` step. The operator's drill is one drive launch that shows the preset mode, the allocated port and the SessionStart facts in the first turn.

---

## §2 Invariant bindings (G12)

Every task in PLAN-SA is written against the six invariants verbatim. This section states how each binds SA's changes — no task touches basket mounting (1), no task exposes a credential (2), every byte still crosses the broker (3), no imperative setup is introduced (4), every policy change is a Nix option (5), and no agent-authored code is promoted between baskets (6). Specific per-mechanism:

- **Invariant 1** (baskets in tmpfs only): no SA task mounts, tears down or reads a basket. The memory store (§6) is machine-local, never a basket.
- **Invariant 2** (no plaintext credential): `--broker` stays in all three `seat-run.py` modes (headless, web, drive). No SA task touches the key path or the broker module.
- **Invariant 3** (one chokepoint): the drive launch's `danger-full-access` preset widens the seat's *prompting* only (the PreToolUse guard, the kernel confinement and the broker are untouched). SA5 proves this with a bats case.
- **Invariant 4** (reproducible; imperative setup is a bug): the payload (§7) is built into `/nix/store` — replacing the two hand-made symlinks that are the one measured live violation in the seat path. The memory directory (§6) is `tmpfiles.d`-declared. The port range (§4) is an option with a default.
- **Invariant 5** (policy as Nix): the port range, the memory directory path, and the `maxUnits` cap are all Nix options written to `/etc` files. Never a runtime setting.
- **Invariant 6** (no promotion between baskets): the hooks (`seat-hooks.py`), the payload (`AGENTS.md`, `skills/`), and every script this spec names are repo-authored or store-built, never promoted from a basket.

**G8** (privacy): the memory store is machine-local under `/var/lib/evidence`; nothing sends a byte the broker does not already see. The memory store is deliberately excluded from `hook-guard.py`'s `PROTECTED_ABSOLUTE` paths (which protect baskets, broker, lanes, secrets — never the seat's own memory).

---

## §3 The drive launch preset (decision 57a)

**What.** Decision 57a: "the drive launch sets `danger-full-access`; kernel confinement plus the house guard remain the boundary; job seats keep the default."

**Today.** `seat-run.py` passes no `--permission` flag in any mode (`grep -n permission pkgs/seat/seat-run.py` → nothing; A6 in the context block). Every seat runs the wrapper's default `permission=${DSH_PERMISSION_MODE:-workspace-write}` (`dsh-openrouter.sh:93`), so the driving session — which drives the whole batch (69a) — is prompted on every write outside the tree. One escalation in the record cost four prompts and 11m46s.

**The change (SA's).** `pkgs/seat/seat-run.py`'s `drive` branch gains `"--permission", "danger-full-access"` before `"--"`. The `headless` and `web` branches stay unchanged (they carry no `--permission`). The wrapper already accepts `--permission MODE` (`:55`, `:115-117`, `:235-237` with validation of the three values), so no wrapper change is needed — only a confirmation that `DSH_PERMISSION_MODE` is exported before the exec line (`dsh-openrouter.sh:562` precedes `:762`).

**The guard is independent.** The PreToolUse hook (`hooks.json` at `dsh-openrouter.sh:709-733`) declares three matchers — `bash`, `edit|write`, `subagent|subagent_fork|workflow` — each pointing at `hook-guard.py`. The permission mode and the hook guard are orthogonal: `danger-full-access` removes the filesystem-write prompt, but every bash/edit/write/subagent call still passes through the guard. SA5 proves this with a bats case: `dsh-openrouter --permission danger-full-access --dump-config` still shows the `@deepseek-ai/dsh-hooks-claude-code` insert with a `configPath` pointing at a `hooks.json` whose PreToolUse matchers are exactly the three patterns.

**`SEAT_MODE` export.** `seat-run.py` exports `SEAT_MODE` ∈ {`headless`, `web`, `drive`} to the harness for every job. SA6 uses this to discriminate the driver session.

**What PL patches.** Nothing. The permission preset is entirely SA's — one argument in one branch of `seat-run.py`, plus the bats and pytest cases.

**Acceptance.**
- `seat-unit`: `test_drive_passes_danger_full_access_before_the_dashes` asserts `argv.index("--permission") < argv.index("--")` and the next element is `danger-full-access`.
- `unit`: `@test "danger-full-access keeps the PreToolUse guard wired"` — `dsh-openrouter --permission danger-full-access --dump-config` shows `configPath` and `hooks.json` with the three matchers.
- `seat-eval`: `SEAT_MODE` is exported.

---

## §4 N seats with allocated ports (decision 13b)

**What.** Decision 13b: "N seats with backend-allocated ports and a session list in Helm."

**Today.** `seat-submit` allocates a hard-coded port: every `job.json` of 2026-09-09 carries `"port": 43210` (`seat-submit.py` passes `--port` as-is from the CLI). The `webPortRange` option exists (`nixosModules/seatLane.nix:61-64`, default `43200-43299`) but no allocator reads it.

**The change (SA's).** A new option `services.seat-lane.portRange` (string `a-b`, default `43210-43219`), written to `/etc/seat-lane/port-range`. The allocator lives in `seat-spool.py` (not `seat-submit` — the spool is the one host actor the seat may reach, per SD6). On every job submission without an explicit `--port`:
1. Read the port range from the file, else use the default.
2. Parse the running jobs from `/var/lib/seat/jobs/` and collect their allocated ports.
3. Find the lowest unallocated port in the range.
4. If none is free, write `result.txt` with `status=failed` and `seat-spool: no free port in <range>`.
5. If the range is narrower than `maxUnits`, the allocator still works — the third seat is simply refused (the assertion catches this at eval, not at runtime).

Helm's session list (`docs/decisions/2026-09-09-redesign-answers.md:26`) reads `/var/lib/seat/jobs/*/job.json` directly — no API, no allocator call. The job directory contract (SA9) documents the JSON schema.

**Assertions (SA's).** Two new eval-time assertions on `services.seat-lane.portRange`:
- **Width assertion:** the range must be at least `maxUnits` ports wide. `a-b` → `b - a + 1 >= maxUnits`. This prevents the allocator from having fewer ports than concurrent jobs.
- **Containment assertion:** the range must lie inside `webPortRange`. The default `43210-43219` is inside `43200-43299`; a range like `44210-44219` is refused.

Both are added to `nixosModules/seatLane.nix` alongside the existing assertions (key file, egress-broker allowlist, credential in env, `maxUnits >= 1`, `waveJobs >= 1`, `maxUnits > waveJobs`).

**What PL patches.** Nothing. The port range option, its assertions, the `/etc` file, and the allocator logic are all SA's.

**Acceptance.**
- `seat-eval`: three new assertions (width, containment, the rendered `/etc` file) produce the expected `error:` lines.
- `seat-assertion-negative`: two new arms (range one port too narrow; range outside `webPortRange`) must each fail.
- `seat-vm`: step 14 proves two `--port`-less web seats bind two distinct ports inside the declared range, and a third is refused with the reason in `result.txt`.

---

## §5 The three hooks (decision 58a)

**What.** Decision 58a: "all three hooks (SessionStart, PreCompact, Stop) running the same scripts, in the harness rework." Decision 60a scopes them to the driver session. Decision 21c forbids self-nudges: subagent output arrives as a file, never as an agent-to-agent message.

**Today.** The generated `hooks.json` (`dsh-openrouter.sh:709-733`) declares `PreToolUse` only — three matchers pointing at `hook-guard.py`. SessionStart, PreCompact and Stop are not declared. The drive seat starts every session blind (no SessionStart facts), compacts without a ritual (no PreCompact re-injection), and stops without running `tools/ritual.sh stop`.

**Whether the bridge fires these events is UNMEASURED** (context block A2). SA6 measures it first: the `@deepseek-ai/dsh-hooks-claude-code` bridge (`dsh-openrouter.sh:641-643`) runs Claude Code command hooks on dsh's seams. If SessionStart or Stop do not fire, SA6 emulates them at the seat's own boundaries for `SEAT_MODE=drive` only. An unfired PreCompact is left to PL's patch series under `patches/dsh/` (A20).

**The hook script (SA's).** A new stdlib-only Python script `seat-hooks.py` packaged as `seat-hooks` in the dsh-openrouter derivation:
- Reads the hook payload from stdin **only if `not sys.stdin.isatty()`**, at most 1 MiB.
- Parses with `json.loads`. A terminal, empty read, non-JSON, non-object, or missing `hook_event_name` → one stderr line, exit 0, empty stdout.
- Reads `SEAT_MODE` from the environment (exported by SA5).
- If `SEAT_MODE` ≠ `drive` → exit 0, empty stdout in under 1 s, runs no script.
- If `SEAT_MODE=drive`:
  - **SessionStart:** runs `tools/session-start.sh` from `$PWD` (the workspace `seat-run.py` cd'd into). Prints `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":<stdout>}}`. 60 s timeout.
  - **PreCompact:** runs `tools/ritual.sh` from `$PWD`. Prints the same JSON shape. 60 s timeout.
  - **Stop:** runs `tools/ritual.sh stop` from `$PWD`. Prints plain stdout, **no decision field** — a Stop can never re-prompt the seat (21c). 60 s timeout.
- A missing or failing script → one stderr line, exit 0 (the guard's fail-open-on-exit contract, A11).
- Never emits a `decision` or `permissionDecision` field. Always exits 0.

**The hooks.json patch (SA's).** The `hooks.json` heredoc in `dsh-openrouter.sh` gains three new event arrays:
```json
"SessionStart": [
  { "type": "command", "command": <jq @sh of $seat_hooks> }
],
"PreCompact": [
  { "type": "command", "command": <jq @sh of $seat_hooks> }
],
"Stop": [
  { "type": "command", "command": <jq @sh of $seat_hooks> }
]
```

**Emulated events.** If the bridge does not fire SessionStart or Stop (measured in Step 1a), the wrapper emulates them for `SEAT_MODE=drive` only by calling `seat-hooks` directly at the appropriate lifecycle boundary:
- **SessionStart:** called right after the harness boots, before the first turn.
- **Stop:** called right before the wrapper exits, after the harness exits.
- **PreCompact:** if unfired, left to PL's patch series (A20).

**The stop-hook-active field.** The Stop payload's `stop_hook_active` (the harness's loop-guard field, true when the turn already continued from a Stop hook) is logged to stderr and changes nothing — the hook never blocks.

**What PL patches.** PreCompact if unfired (A20); the inbox splicing for 21c (see §8). The patch series `patches/dsh/` must:
1. Ensure the bridge fires all three events, or
2. Provide a mechanism for the wrapper to detect and emulate unfired events.

**Acceptance.**
- `unit`: `94-seat-harness.bats` cases covering `seat-hooks` behaviour — terminal on stdin, empty payload, non-JSON payload, missing `hook_event_name`, `SEAT_MODE` ≠ `drive` (pass-through), `SEAT_MODE=drive` with SessionStart/PreCompact/Stop, missing script (exit 0, stderr), timeout, `stop_hook_active` logging.
- `unit`: `70-dsh-openrouter.bats` case asserting the `hooks.json` shape — four event arrays, each pointing at `seat-hooks`.
- `lint`: `shellcheck` on any modified shell script, `ruff` on the new Python.
- `seat-vm`: drive launch shows SessionStart facts in the first turn's transcript.

---

## §6 The seat's memory store (decision 59a)

**What.** Decision 59a: "the seat's memory is a machine-local store under the evidence store." Decision 40a: per-subsystem memory and backup rows.

**The change (SA's).** A new option `services.seat-lane.memoryDir`, default `/var/lib/evidence/seat-memory`. It is:
- Declared as a `tmpfiles.d` rule (not a runtime `mkdir`) so the directory exists before the first job.
- Added to the `seat@` unit's `ReadWritePaths` as its own explicit row (`nixosModules/seatLane.nix`, the `ReadWritePaths` block at `:309-316`), so the grant is visible in a diff — the existing `-/var/lib/evidence` already covers it, but an explicit row makes the intent clear.
- Linked at `$DSH_HOME/memory` → `<memoryDir>/<cwd-key>` (the workspace's path digest), so the harness reads and writes memory through a well-known path.
- The Stop hook writes the seat's derived facts (session outcomes, per-task records, the ritual's state) into `<memoryDir>/<workspace>/stop.json`.
- The SessionStart hook reads from the same path and re-injects the facts as `additionalContext`.

**Backup row.** The memory store is backed up as part of `/var/lib/evidence` (the existing Proton Backup row, `hosts/core/proton-backup.nix`, already covers `/var/lib/evidence`). GN10 and PL6 may add a dedicated row; SA's own row is declared in the seat lane module.

**The directory is deliberately not in `PROTECTED_ABSOLUTE`** (`hook-guard.py:86-93`), which protects `/run/baskets` and `/var/lib/{baskets,helm,egress-broker,lanes,secrets}` — the memory store is the seat's own data, not a protected infrastructure path. The guard's job is to prevent the seat from reading/writing infrastructure secrets; the seat's own memory is the opposite.

**What PL patches.** Nothing. The option, its directory, the tmpfiles rule, the `ReadWritePaths` line, and the backup row are all SA's.

**Acceptance.**
- `seat-eval`: the `memoryDir` option exists, defaults to `/var/lib/evidence/seat-memory`, and the `ReadWritePaths` entry is present.
- `seat-vm`: step 15 — after a drive session ends, `cat /var/lib/evidence/seat-memory/<workspace>/stop.json` is non-empty and parseable JSON.

---

## §7 The payload (decision 36a)

**What.** Decision 36a: "AGENTS.md and the skills become part of the `dsh-openrouter` package in `/nix/store`."

**Today.** Two hand-made symlinks deploy the payload:
```bash
ln -s ~/flakes/dsh-harness/skills $DSH_HOME/skills
ln -sf ~/flakes/dsh-harness/AGENTS.md $DSH_HOME/AGENTS.md
```
(`dsh-openrouter.sh:557-558`). A missing, dangling or empty payload only **warns** (`warn_missing_payload`), because a refusal would lock the operator out "precisely when the payload is what is broken". This is the one measured live violation of invariant 4 (reproducible from lock files; imperative setup is a bug).

**The payload seam (SA's).** A new input `harnessPayload` in the dsh-openrouter derivation:
- Type: `nullOr (submodule { agentsMd = paackage; skills = package; })`.
- Default: `null`.
- Assertion: if `harnessPayload` is non-null, both `agentsMd` and `skills` must be non-null.
- Deployment: the wrapper reads `$DSH_HOME/AGENTS.md` and `$DSH_HOME/skills` from the store path instead of the hand-made symlinks. The symlink-and-warn path (`dsh-openrouter.sh:557-558`) is alive only while the input is null — a graceful degradation for development.
- When the payload is present: the wrapper deploys the store-built files (no symlink, no warn).
- When the payload is null: the existing warn path stays (the operator must still deploy by hand).

**What each file must contain (once KN's rules source generates AGENTS.md).**

`AGENTS.md` is the harness's bootstrap instruction file. Once the Knowledge subsystem's rules source (increment 4) generates it from `docs/ledger/rules.toml`, it must contain:
1. **Skills first (the superpowers bootstrap):** a statement that the skills in `skills/` are the first thing to load; before any response or action, check the session skill catalog and invoke every matching skill.
2. **Durable memory index:** a link to the operator's Claude memory (`~/nixos-agent-env` `CLAUDE.md`, `docs/OPERATIONS.md` START HERE, `~/.claude` memory) — never copy `~/.claude/projects/*/memory` into a repo.
3. **DSH-specific notes:** web tools disabled; model routing through `factory_route`; the commit convention (one `Generated-By:` trailer, no `Co-Authored-By` — this is the bootstrap's own rule, which decision 52a supersedes with the two-trailer policy in `docs/board/policies.md:30-36`; the rules source resolves the contradiction).

`skills/` is the skill catalog. Once generated, it must contain at minimum:
- `skills/using-superpowers/` — the skill that establishes how to find and use skills.
- `skills/driving/` — the driver seat's four verbs (brief, dispatch, gate, integrate).
- `skills/planning/` — plan writing.
- A `references/` directory with tool-name mappings for each harness (DSH, Codex, Pi, Antigravity, Hermes).
- A `SKILL.md` in each skill directory.

**The binding (PL's).** Platform's task absorbs `~/flakes/dsh-harness` into the repo and binds `harnessPayload` to the repo's own `AGENTS.md` and `skills/`. SA's seam is the input; PL fills it. Once PL lands, the `warn_missing_payload` path is deleted (next increment, SA's own task).

**Acceptance.**
- `seat-assertion-negative`: a fixture with `harnessPayload = { agentsMd = pkgs.writeText "AGENTS.md" ""; skills = null; }` — must fail the assertion.
- `nix build .#packages.x86_64-linux.dsh-openrouter` — with the default `null` input, builds clean (warn path present).
- `nix build .#packages.x86_64-linux.dsh-openrouter` with a non-null payload — builds clean, the wrapper's `$DSH_HOME/AGENTS.md` and `$DSH_HOME/skills` point at store paths.

---

## §8 The driving inbox rule (decision 21c)

**What.** Decision 21c: "**c — the driving session's inbox only**: no agent-to-agent messaging or self-nudges; subagent output arrives as an artifact the next node reads."

**Today.** The harness's inbox splicing (`dsh-openrouter`'s default inbox configuration) permits agent-to-agent messaging and self-nudges. The drive transcript measured 171 `agent/inbox/spliced` events — each a message the harness injected into the agent's inbox.

**The change (PL's patch).** A patch under `patches/dsh/` against the dsh harness's inbox configuration:
- Removes the agent-to-agent messaging channel.
- Disables self-nudges (the harness may not inject messages into its own inbox).
- Subagent output arrives as a file (the subagent writes to a known path; the parent reads it from there), never as an inbox event.

**SA's role.** SA6's `seat-hooks.py` must never block on Stop (21c: "a Stop can never re-prompt the seat"), which the spec enforces by never emitting a `decision` field from the Stop hook.

**Acceptance.**
- `unit`: a test in `70-dsh-openrouter.bats` or `94-seat-harness.bats` asserts that the Stop hook's output contains no `decision` field.
- `seat-vm`: the drive transcript (drill step 6) shows zero `agent/inbox/spliced` events after PL's patch.

---

## §9 The concurrency cap (decision 72a, IS1c)

**What.** Decision 72a: "`seat-submit` refuses a launch above a configured running-unit count." Corrected by IS1c: the spool, not `seat-submit`, is the enforcer.

**Today.** The cap is enforced by `seat-spool.py` (`seatLane.nix`-asserted maxUnits from `seat-lane`). `seat-submit` reads the cap for its started path (`_max_units_cap`, `seat-submit.py:116-131`), but the actual refusal fires in `seat-spool.py` before `systemctl start` (`seat-spool.py:127`). The cap is published as `/etc/seat-lane/max-units` (`seatLane.nix:148-150`).

**SA's change (cosmetic — IS1c minor 3).** The enforcer wording in three places still names `seat-submit` instead of `seat-spool`:
1. `nixosModules/seatLane.nix:79` — "before seat-submit refuses a launch (IS1, decision 72a)" → corrected to "before seat-spool refuses a launch".
2. `flake.nix:2424` — a `seat-eval` message naming `seat-submit`.
3. `flake.nix:2428` — another `seat-eval` message.

These are string-only changes in files that span areas (`seat, isolation, platform` — the lane module is isolation-owned, `flake.nix` is platform-owned). The spec declares `areas: seat, isolation, platform` for SA1.

**IS1c minor 1 (the refusal reason never reaches the record).** SA2 fixes this: `_oll` in `seat-submit.py` learns to read `result.txt` after the exit code, emitting the spool's refusal reason (`seat-spool.py:183-188` writes `FACTORY-RESULT status=failed` then `seat-spool: <note>`). When `_oll` reads `result.txt`, it includes that note in its output.

**IS1c minor 2 (the poll bound).** SA2 adds `SEAT_POLL_TIMEOUT` as an environment variable alongside `--timeout`, with a pytest fixture proving that a `>=` mutation on the start path reddens instead of hanging for 20 minutes.

**Acceptance.**
- `seat-eval`: the corrected messages appear in the assertion output.
- `seat-unit`: `test_timeout_exits_124_and_stops_the_unit` covers the bounded poll; a `>=` mutant on the start path fails within the pytest timeout (30 s) instead of hanging.
- `seat-unit`: `test_poll_reads_result_txt` — when `result.txt` carries a spool refusal, `_poll` includes the note in its output.

---

## §10 Harness files: which are PL's patch series and which are payload

**PL's patch series** (`patches/dsh/` — patches against the vendored `@deepseek-ai/dsh` and `@deepseek-ai/dsh-hooks-claude-code`):

| Patch | What it changes | Why it's a patch |
|---|---|---|
| 1 | Inbox splicing — remove agent-to-agent channel, disable self-nudges | §8, decision 21c |
| 2 | PreCompact hook event — ensure the bridge fires it, or provide a fallback | §5, A20 |
| 3 | SessionStart event — ensure the bridge fires it (if it doesn't) | §5, A20 (measured by SA6) |

These are patches because they modify vendored upstream code (`@deepseek-ai/dsh-hooks-claude-code` bridge and dsh's inbox module), which is outside SA's `owns` globs and follows the patch system (`docs/decisions/2026-09-09-redesign-answers.md:37-38`).

**SA's payload files** (repo-authored, store-built):

| File | What it is | Where it's declared |
|---|---|---|
| `pkgs/dsh-openrouter/seat-hooks.py` | The hook script for SessionStart, PreCompact, Stop | `pkgs/dsh-openrouter/default.nix` |
| `AGENTS.md` | The seat's bootstrap instruction file | Generated by KN's rules source (increment 4); until then, the repo's own file |
| `skills/` | The skill catalog | Generated by KN's rules source; until then, the repo's own directory |

**The generated `hooks.json`** (`dsh-openrouter.sh:709-733`) is neither a patch nor a payload file — it is a shell heredoc that composes the hook table at launch time. SA6 edits it to add the three new event arrays.

---

## §11 Acceptance drill

The operator's composed increment drill (from `PLAN-SA`'s `## Operator` section):

1. `nix flake check -L` — green, including `seat-vm` (IS10 closes the live `flake-check` red; SA1 keeps it green).
2. `seat-submit web --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter` twice, no `--port` — two job ids and two distinct ports inside `cat /etc/seat-lane/port-range`.
3. A third `seat-submit web` with no `--port` — refused: `no free port in 43210-43211` (range narrowed to 2 for the test).
4. `journalctl -u seat@<id>` shows `danger-full-access` in the launch log line for a `drive` job, and no `--permission` for a `web` job.
5. `cat /var/lib/evidence/seat-memory/<workspace>/stop.json` after a drive session is non-empty JSON.
6. The drive transcript shows SessionStart facts in the first turn and zero `agent/inbox/spliced` events.

---

## §12 Out of scope

- The absorption of `~/flakes/dsh-harness` into the repo (PL's task).
- The generation of `AGENTS.md` and `skills/` from the rules source (KN's task, increment 4).
- The PreCompact patch under `patches/dsh/` if the bridge does not fire it (PL's task, A20).
- The backup row in `hosts/core/proton-backup.nix` (GN10 or PL6).
- The manifest `owns` widening to include the payload paths (PR/EV row).
- The bug close-out of `docs/bugs/2026-09-09-broker-bypass.md` on `FIX1`'s evidence (EV's task).
- `FACTORY_SEAT_UNIT=0` opt-out in `factory-task` (FA's task).
- The contradictory rule `R-conv-seat-one-trailer` in `rules.toml:563-570` (the operator strikes it by hand; KN's rules source resolves it for good).