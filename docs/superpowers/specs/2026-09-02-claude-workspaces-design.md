# Design draft — per-flake Claude workspaces (the "familiar" layer)

Status: FINAL (exam wf_7abbce6f-06c verified all open questions, 2026-09-02).
Commit to docs/superpowers/specs/ when the Phase 4a factory releases the tree.

## Problem

One global `~/.claude` means every project shares memory, history, and settings,
unencrypted in the operator home. The brief demands per-environment injected
context; the operator directive (2026-09-02): each separated nix flake keeps its
own Claude context window and memory files, stored in that project's userdata.

## Evidence (local, verified)

- `~/.claude/projects/<escaped-cwd>/` holds per-directory transcripts AND the
  auto-memory dir — project identity is the working directory, escaped
  (`/home/dalhaka/nixos-agent-env` → `-home-dalhaka-nixos-agent-env`). Soft
  per-project separation already exists.
- Global remainder shared: settings.json, history.jsonl, sessions/, plugins,
  file-history — cross-project leakage surface, plaintext at rest.
- Pending docs verification: CLAUDE_CONFIG_DIR relocation coverage; credential
  resolution relative to it; session-start hooks; any official profiles feature.

## Design: one Claude home per project, inside a basket

Each project declares a `claude-home` **basket** (rw). At launch, the basket
mounts to tmpfs and the entire Claude config universe points at it:

    claude-in <project>:
      1. basket mount  <store>/<proj>-claude-home  → /run/baskets/<proj>-claude-home
      2. export CLAUDE_CONFIG_DIR=/run/baskets/<proj>-claude-home/config
      3. inject projects/<proj>/CLAUDE.md (+AGENTS.md) into the workspace root
      4. cd <project workspace>; exec claude
      5. on exit (trap): basket seal   ← NEW CLI subcommand (see below)

Result per project: its own memory files, its own MEMORY.md index, its own
session/resume history, its own settings-below-managed — all AES^Wage-encrypted
at rest inside the project's basket, tmpfs-only when live, torn down after, and
picked up by restic backups as ciphertext automatically.

Shared across ALL workspaces (explicitly, nothing else):
- `/etc/claude-code/managed-settings.json` — the security floor; applies
  regardless of CLAUDE_CONFIG_DIR (verification pending, expected to hold).
- Credentials — injected at runtime (env/apiKeyHelper per docs verification),
  NEVER stored inside any claude-home basket (invariant 2 spirit: one
  subscription, zero credential copies at rest in project data).
- Nothing else. The orchestrator's own host-level memory (this session) is not
  reachable from any project workspace.

## Consequences the module must enforce (assertions)

1. `claude-home` baskets must be `access = "rw"` (memory must persist via seal).
2. A frontier-Claude workspace requires project egress != none → the Phase 3
   assertion already forbids pairing it with `local-only` classification. Stated
   fallout: a local-only project's workspace Claude must target the local model
   class via the Phase 5 router instead — same launcher, different endpoint.
3. Mount path collision + stale-mount checks via existing basket CLI/doctor.

## New capability required: `basket seal`

Inverse of `mount` for rw baskets: deterministically pack the live tmpfs
content, re-encrypt to the current recipient set, replace payload in the store,
update content/payload hashes in `baskets.lock`, then teardown. Refused for ro
baskets. TDD: mount→modify→seal→hash-delta verified→remount shows changes;
crash-safety: seal writes to a temp entry then atomically renames.

## Implementation shape (post-4a mini-phase "workspaces")

Task 1: `basket seal` + bats suite. Task 2: module options
(`services.baskets.projects.<name>.claudeWorkspace`) + launcher generation +
assertions + generated per-project CLAUDE.md injection. Task 3: acceptance —
two demo projects; write a memory in A; prove absent in B; prove sealed at rest
(strings of payload show nothing); prove teardown leaves no plaintext; prove
managed settings still bind inside a workspace.

## Verified mechanics (exam results, 2026-09-02)

1. **CLAUDE_CONFIG_DIR moves everything** — settings, transcripts, auto-memory,
   `.claude.json` (incl. per-project trust state), plugins, AND credentials;
   documented for running multiple accounts side by side. The design's central
   assumption holds.
2. **`CLAUDE_CODE_PROJECT_DIR_NAME`** (≥ v2.1.234; installed 2.1.245): honored
   only when CLAUDE_CONFIG_DIR is set; pins transcripts + auto-memory to a
   stable project name regardless of cwd. Launcher sets it to the project name —
   kills two discovered footguns: the "/"→"-" path escaping collides for
   hyphenated siblings, and auto-memory normally keys by git repo (worktrees
   share memory). One project per config dir, one name, no ambiguity.
3. **Credentials**: `claude setup-token` → long-lived OAuth token, injected as
   `CLAUDE_CODE_OAUTH_TOKEN` at launch. Stored age-encrypted at
   /var/lib/claude-workspaces/oauth-token.age (recipients = the YubiKeys),
   decrypted straight into the launcher's env — one subscription across all
   workspaces, zero credential files at rest in any basket or config dir.
   Token expires eventually → rotation runbook (re-run setup-token, re-encrypt);
   a doctor probe warns when auth starts failing.
4. **Per-env instructions**: `<config>/CLAUDE.md` (user-level, travels with the
   basket) + repo-level projects/<name>/CLAUDE.md; a SessionStart hook in
   `<config>/settings.json` injects dynamic context (phase status, basket list).
5. **Managed settings** (/etc/claude-code/) are outside every config dir and
   apply across all of them — very likely but not letter-verified in docs; the
   mini-phase acceptance MUST test it live (managed deny rule binds inside a
   workspace) before this is treated as real.
6. `--bare` exists for memory-free throwaway runs; `claude config` subcommand is
   gone (scripted config = write settings.json directly).

## Amendment 2026-09-02 (operator) — host memory is out of scope

Claude memory directories under `~/.claude/projects/<slug>/memory` are per
folder, separated by construction, and are never mounted, copied or linked
by a workspace (docs/decisions/2026-09-02-memory-per-flake.md). A workspace
launched for a flake gets that flake's own memory because it opens that
folder; nothing else. Helm v1's launcher is the front door for this design.
