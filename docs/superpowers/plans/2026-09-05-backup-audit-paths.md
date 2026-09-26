# Backup the audit records — implementation plan (2026-09-05)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) reads the `### KEY (kind, size) — title` section. One task.

**Goal:** the lane ledgers and the broker audit logs are in the nightly restic backup (operator decision `docs/decisions/2026-09-05-audit-logs-backed-up.md`), with job payloads, results and the broker CAs excluded, proven by the host checks.

**Architecture:** two directories join `services.proton-backup.paths` in `hosts/core/proton-backup.nix`; the exclude list is restated with three new patterns (a module-option *definition* replaces the option's default list, so the three defaults are written out again); `host-core` asserts paths and excludes; `core-backup-wiring` already refuses a path the runbook does not name.

**Spec:** the decision file above. Facts measured 2026-09-05: `/var/lib/lanes/<lane>` is `2770 root:lane` holding `ledger.jsonl`, `jobs/`, `results/` (`nixosModules/modelLane.nix:205-210`); `/var/lib/egress-broker/<instance>/` holds `audit.jsonl` (0644) and `ca/` (the instance CA with its private key) for the instances `cowork` and `openrouter`; restic runs as root (system unit), so mode 2770 is readable; `services.proton-backup.exclude` (`nixosModules/protonBackup.nix:35-42`) defaults to `[ "**/.pytest_cache" "**/.ruff_cache" "/home/*/.cache" ]` and `core` does not define it today; `docs/runbooks/backup.md:15-34` lists the paths ("eleven of them") and a stale sentence says the evidence store "joins the list once `services.evidence-store` lands" — it landed (switch #15).

## Global Constraints

- Build-only: no `sudo`, `nixos-rebuild`, `systemctl start/stop/restart/enable`; never read `/var/lib/secrets/*`, `~/.config/openrouter/key`, `~/.config/restic/password`, or anything under `/var/lib/lanes` or `/var/lib/egress-broker/*/ca`.
- Commits through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` before `nix build`; never `--no-verify`; never `2>/dev/null` a gated command. Subject `<prefix>: summary (test: <check names only>)`, trailer exactly `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- TDD: the failing check first, shown red, then green. `touches` is a contract.

## Assumptions

1. Restic exclude patterns are matched against the full path and `*` does not cross `/`, so `/var/lib/lanes/*/jobs` excludes exactly each lane's `jobs` directory.
2. Backing up a directory that exists but is empty is fine; the exit-3 failure mode is a *missing* path only (`docs/runbooks/backup.md`).

## Tasks

### B1 (code, XS) — `/var/lib/lanes` and `/var/lib/egress-broker` join the restic paths; payloads, results and the CAs are excluded; the runbook names them

**dependsOn:** none

**Files:**
- Modify: `hosts/core/proton-backup.nix` (two paths; the `exclude` definition), `flake.nix` (`host-core` assertions next to the existing `/var/lib/evidence` one at `flake.nix:773`), `docs/runbooks/backup.md` (the path list and the exclude sentence; the stale evidence-store sentence)

**Interfaces:**
- `hosts/core/proton-backup.nix`: `paths` gains `"/var/lib/lanes"` and `"/var/lib/egress-broker"`, each with a one-line comment naming the decision; and

```nix
  # A definition replaces the module's default exclude list, so the three
  # defaults are restated. The three new patterns keep job payloads, model
  # output and every broker CA (private key included) out of the backup
  # (docs/decisions/2026-09-05-audit-logs-backed-up.md).
  services.proton-backup.exclude = [
    "**/.pytest_cache"
    "**/.ruff_cache"
    "/home/*/.cache"
    "/var/lib/lanes/*/jobs"
    "/var/lib/lanes/*/results"
    "/var/lib/egress-broker/*/ca"
  ];
```

- `host-core` asserts: `lib.elem "/var/lib/lanes" c.services.proton-backup.paths`, `lib.elem "/var/lib/egress-broker" c.services.proton-backup.paths`, and `lib.all (p: lib.elem p c.services.proton-backup.exclude) [ "**/.pytest_cache" "**/.ruff_cache" "/home/*/.cache" "/var/lib/lanes/*/jobs" "/var/lib/lanes/*/results" "/var/lib/egress-broker/*/ca" ]`, each with its own `assertMsg` naming what is missing.
- `docs/runbooks/backup.md`: the list says "thirteen of them"; a new bullet "the audit records — `/var/lib/lanes` (each lane's `ledger.jsonl`; its `jobs/` and `results/` are excluded) and `/var/lib/egress-broker` (each instance's `audit.jsonl`; its `ca/` — the CA and its private key — is excluded; decision 2026-09-05-audit-logs-backed-up)"; the exclude sentence lists all six patterns; the evidence-store bullet becomes "the evidence store `/var/lib/evidence` (landed with switch #15)".

- [ ] **Step 1: Red** — add the three `host-core` assertions first (after the `/var/lib/evidence` assertion at `flake.nix:773`), `git add flake.nix`, `nix build .#checks.x86_64-linux.host-core -L --no-link` → `host-core: /var/lib/lanes must be a restic path …` (the first new assertion fails).
- [ ] **Step 2: Implement** — the two paths and the exclude definition in `hosts/core/proton-backup.nix`; the runbook edits.
- [ ] **Step 3: Green** — `nix build .#checks.x86_64-linux.host-core -L --no-link`; `… core-backup-wiring` (it greps the runbook for every path — red if a path is undocumented; confirm that by temporarily removing the `/var/lib/lanes` bullet → red, restore); `… proton-backup-eval`; `nix develop -c githooks/pre-commit`. Then `nix build .#nixosConfigurations.core.config.system.build.toplevel --no-link` (evaluates the host).
- [ ] **Step 4: Commit.**

**touches:** hosts/core/proton-backup.nix, flake.nix, docs/runbooks/backup.md
**acceptance:** host-core, core-backup-wiring, proton-backup-eval, lint
**commit subject:** `core: the lane ledgers and the broker audit logs join the backup; payloads, results and the CAs excluded (test: host-core, core-backup-wiring, proton-backup-eval, lint)`

### B1b (code, XS) — B1 amended by the 23:50 decision: only the lane ledgers join the backup; the broker audit logs never leave the machine

**dependsOn:** none

B1 (run bk2, commit 9a547a0, all four checks green) was built to the original decision minutes before the operator reversed its broker half (`docs/decisions/2026-09-05-audit-logs-backed-up.md`, addendum; `2026-09-05-telemetry-store-decisions.md`, answer 5). Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/bk2/B1 task/B1 && git cherry-pick -n FETCH_HEAD`; apply the amendment; ONE commit with the subject below (B1's subject is withdrawn with the reversal).

**Contract:**
1. `services.proton-backup.paths` gains `/var/lib/lanes` only; `/var/lib/egress-broker` is NOT a path, and `host-core` asserts that no element of `paths` starts with `/var/lib/egress-broker` (mutation: the broker path added → `host-core` red).
2. `exclude` restates the module's three defaults plus `/var/lib/lanes/*/jobs` and `/var/lib/lanes/*/results` (five patterns; the CA pattern is unnecessary and dropped); `host-core` asserts the five and that no other entry under `/var/lib/lanes/*` survives the excludes except the ledger — state how it is proven (a fixture directory listing against the patterns in `proton-backup-eval`, or an assertion over the known lane layout).
3. The runbook names `/var/lib/lanes` (each lane's `ledger.jsonl`; `jobs/` and `results/` excluded) and states, in one sentence with the decision's name, that the broker audit logs are never backed up; `core-backup-wiring` stays green.
4. `docs/ledger/claims.toml`: `lane-ledger-and-broker-audit-unbacked` closes as verified with the text "ledger backed up; audit logs disposable by decision 2026-09-05 (addendum)"; `claims.py validate` green.

- [ ] **Step 1: Red** — the negative assertion first (`host-core` red on B1's tree, which carries the broker path). **Step 2: Implement.** **Step 3: Green** — `host-core`, `core-backup-wiring`, `proton-backup-eval`, lint gate, the toplevel evaluates; mutation: the broker path re-added → red; the `results` exclude dropped → red. **Step 4: One commit.**

**touches:** hosts/core/proton-backup.nix, flake.nix, docs/runbooks/backup.md, docs/ledger/claims.toml
**acceptance:** host-core, core-backup-wiring, proton-backup-eval, lint
**commit subject:** `core: the lane ledgers join the backup; payloads and results excluded; the broker audit logs stay on the machine by decision (test: host-core, core-backup-wiring, proton-backup-eval, lint)`

### B1c (code, XS) — B1b fix round: the "only the ledger survives" proof reads the lane layout, the runbook is pinned by the check, the path count is right

**dependsOn:** none

Gate `docs/reviews/2026-09-05-opus-review-bk3-B1b.md` — REJECTED on one major: the assertion meant to prove that nothing but the ledger survives under `/var/lib/lanes/*` is subsumed by the equality assertion above it (deletable with every check green) and never reads the lane layout, so a fourth lane child directory added to `nixosModules/modelLane.nix` joins the backup silently. Four minors. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/bk3/B1b task/B1b && git cherry-pick -n FETCH_HEAD`; ONE commit with B1b's subject.

**Contract:**
1. `host-core` derives the lane's child directories from the tmpfiles rules `nixosModules/modelLane.nix` renders for a lane (every `d /var/lib/lanes/<name>/<child> …` line) and asserts that each child except the ledger's parent is matched by an exclude pattern (`/var/lib/lanes/*/<child>`); the message names the unexcluded child (mutation: a fourth child `spool` added to modelLane's tmpfiles → `host-core` red naming `spool`; the assertion deleted → the same fixture stays red through a second assertion? no — pin it the other way: the fixture-with-spool case is the red proof; deleting the assertion makes THAT red case green, which the gate's mutation catches).
2. `core-backup-wiring` pins the runbook's lanes bullet by its own words (``each lane's `ledger.jsonl` ``) and the broker sentence (`/var/lib/egress-broker` … never backed up), each with a message; the path count sentence says thirteen (mutations: the bullet removed → red; the sentence removed → red).
3. The restic user note: the runbook states that restic runs as the operator, who reads the lane dirs through the `lane` group, and `docs/ledger/claims.toml` gains an open claim `backup-user-lane-group-unasserted` (owner orchestrator, review by 2026-09-19) for the missing assertion, which is outside this plan's touches.

- [ ] **Step 1: Red** — the `spool` fixture in `proton-backup-eval` (or a host-core eval fixture) is red on B1b's tree; the two runbook mutations are green on B1b's tree (that is the gap) and red after. **Step 2: Implement.** **Step 3: Green** — `host-core`, `core-backup-wiring`, `proton-backup-eval`, lint gate; `claims.py validate`. **Step 4: One commit.**

**touches:** flake.nix, docs/runbooks/backup.md, docs/ledger/claims.toml
**acceptance:** host-core, core-backup-wiring, proton-backup-eval, lint
**commit subject:** `core: the lane ledgers join the backup; payloads and results excluded; the broker audit logs stay on the machine by decision (test: host-core, core-backup-wiring, proton-backup-eval, lint)`
