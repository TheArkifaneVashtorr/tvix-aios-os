# Helm v0 pre-switch fix round Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Executor: `tools/factory/dark-factory.js` in this repo (host `core`, build-only).

**Goal:** after `sudo nixos-rebuild switch` the Helm page and `helm-status` work in the operator's already-running session, the backup-snapshot tile reports, the drill passes as written, and the runbook's every command and claim is true on `core`.

**Architecture:** four small, independently testable changes — the module stops gating a secret-free config file on a group the running session cannot have; the collector reads restic without a lock and reports "no broker" honestly and drops a badge that could never render; the acceptance script and the factory script fix their own defects; the runbooks say what the switch, the rollback and the first minutes really do.

**Tech Stack:** NixOS 25.05 at `nixpkgs-host` ac62194c, Python 3 + pytest (`checks.helm-unit`), NixOS VM test (`checks.helm-vm`), bash + shellcheck, Node (syntax check only).

**Spec:** the pre-switch audit (2026-09-03, 49 Opus/Sonnet agents; findings recorded on `docs/OPERATIONS.md` under "Pre-switch audit"), every finding below verified on the live host: **F1** `/etc/helm/config.json` is installed `0640 root:helm` but a switch never re-credentials the running session or `user@1000.service` (X-RestartIfChanged=false), so `helm-collect`/`helm-status` die with PermissionError until relogin (`collect.py:643` reads the file outside every tile wrapper); **F5** `restic snapshots` takes a repo lock the read-only sandbox forbids → the tile is `unknown` after a 60 s timeout; **F8** the page 404s until the first collection; **F9** the "collector stale" badge is computed at collection time and can never render; **F17** restic's cache sits inside the served document root; **F20** an empty `broker_audit_paths` renders `ok 0/0` instead of `unknown`; **F25** `helm.sh` leaves `proton-drive-push.timer` stopped on interrupt; **F26** `BindReadOnlyPaths=/var/lib/helm` fails once if tmpfiles has not run; **F31/F33/F34** the runbook's rollback advice can overshoot to generation 21 (cowork + broker come back), the boot-menu pick is one-shot, and a rollback strands Helm's user timers until logout; **F11/F12/F13/F14/F15/F18/F19** runbook claims; **F6** the Helm spec's confidentiality sentence is false; **F16** a comment claims 0700 memory dirs match existing 0755 ones; **F32/F36/F35** dark-factory ignores `review.approved`, the invariant-audit agent omits its model, JavaScript has no syntax check in the lint gate.

## Global Constraints

- Build-only. Never sudo, nixos-rebuild, switch-to-configuration, systemctl start/stop, basket, restic against `/var/lib/restic`.
- No secrets in the repo; `/etc/helm/config.json` contains paths only (the restic password is referenced by path) — that is why it may become world-readable.
- Commit subjects `helm: … (test: …)` / `docs: …`; `git add` before `nix build`; commits through the devShell; never `--no-verify`, never `2>/dev/null` on a gated command.
- Loopback only, zero outbound: unchanged.

---

### Task 1: module + collector (F1, F5, F9, F17, F20, F26, F16)

**Files:**
- Modify: `nixosModules/helm.nix:231-235` (config.json), `:245` (server root unchanged), `:256-263` (tmpfiles), `:266-310` (user units: cache env + ReadWritePaths), the static-web-server drop-in (`BindReadOnlyPaths`)
- Modify: `pkgs/helm/collect.py:111` (restic argv), `:287-330` (broker tile), `:534`, `:572-585`, `:615` (stale badge)
- Modify: `tests/helm/test_collect.py`, `tests/integration/helm-vm.nix`
- Modify: `hosts/core/proton-backup.nix` (comment only, F16)

**Interfaces (Produces):** config key `restic_cache_dir` now `/var/lib/helm-cache`; `tile_broker` returns `("unknown", "no broker instance configured", {})` when `broker_audit_paths` is empty; the rendered page has no `collector stale` span and no `.stale` CSS.

- [ ] **Step 1: failing unit tests** (`tests/helm/test_collect.py`, same monkeypatch style as the existing tests):
```python
def test_restic_snapshots_uses_no_lock(monkeypatch):
    seen = {}
    def fake_run(argv, timeout, env=None):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, "[]", "")
    monkeypatch.setattr(collect, "run", fake_run)
    collect.tile_backup_snapshot(CFG, NOW)
    assert "--no-lock" in seen["argv"] and seen["argv"][:2] == ["restic", "snapshots"]

def test_broker_tile_unknown_when_no_instances():
    status, summary, _ = collect.tile_broker({**CFG, "broker_audit_paths": []}, NOW)
    assert status == "unknown" and "no broker instance" in summary

def test_page_has_no_stale_badge():
    html = collect.render_html(STATUS_OLD, NOW)   # a status whose generated_at is 3 intervals old
    assert "collector stale" not in html and ".stale" not in html
    assert "generated" in html
```
  (Use the file's existing fixtures for `CFG`/`NOW`/a status dict; delete or invert the existing test that asserts the badge appears.) Run `nix develop -c pytest tests/helm -q` → red.
- [ ] **Step 2: collector** — `collect.py:111` argv `["restic", "snapshots", "--no-lock", "--json", "--latest", "1"]` (comment: snapshots is a pure read; the sandbox is read-only on the repo; `--no-lock` is restic's documented flag for that); `tile_broker`: `if not cfg.get("broker_audit_paths"): return "unknown", "no broker instance configured", {}` before the loop; remove the stale computation, span and CSS (the page is regenerated by the collector, so a viewer can never see a badge the collector would have to emit about itself; the `timers` tile already audits `helm-collect.timer`). Tests green; `ruff` clean.
- [ ] **Step 3: failing VM assertions** (`tests/integration/helm-vm.nix`, testScript): 
```python
machine.succeed("stat -c %a:%U /etc/helm/config.json | grep -qx '644:root'")
machine.succeed("su nobody -s /bin/sh -c 'cat /etc/helm/config.json >/dev/null'")
machine.fail("curl -fsS http://127.0.0.1:7700/cache/")
machine.succeed("stat -c %a:%U /var/lib/helm-cache | grep -qx '700:alice'")
assert tiles["broker"]["status"] == "unknown", tiles["broker"]
assert "collector stale" not in page
```
  Replace the existing `/var/lib/helm/cache` assertion. Run `nix build .#checks.x86_64-linux.helm-vm -L --no-link` → red.
- [ ] **Step 4: module** — `environment.etc."helm/config.json"` → `mode = "0644"` and no `group` (comment WHY: the file holds paths only, its bytes are already world-readable in the store, and a group gate is unreadable in any session that predates the group: a switch never re-credentials a running user manager — audit F1); `restic_cache_dir = "/var/lib/helm-cache"`; tmpfiles: replace the `/var/lib/helm/cache` line with `"d /var/lib/helm-cache 0700 ${cfg.operatorUser} ${cfg.operatorUser} -"` (comment: outside the served root — F17); `helm-collect.service`: `environment.RESTIC_CACHE_DIR` and `ReadWritePaths` += `/var/lib/helm-cache`; static-web-server drop-in `BindReadOnlyPaths = [ "-/var/lib/helm" ]` (comment: tolerate a first start before tmpfiles; the unit self-heals via Restart=always, but a red unit at switch time is noise — F26). `hosts/core/proton-backup.nix` comment: the new dirs are created 0700 deliberately (operator-only); the two pre-existing memory dirs are 0755 today and are left alone. Run `helm-vm`, `helm-eval`, `helm-assertion-negative`, `host-core`, `helm-unit` → green; lint gate.
- [ ] **Step 5: commit** `helm: config.json readable without a group the running session lacks; restic --no-lock; cache outside the served root; broker tile honest when unconfigured; stale badge removed (test: helm-unit, helm-eval, helm-vm, host-core, lint)`.

### Task 2: acceptance script and the factory script (F8, F18, F25, F32, F36, F35)

**Files:**
- Modify: `tests/acceptance/helm.sh`
- Modify: `tools/factory/dark-factory.js:160-175`, `:186-187`
- Modify: `githooks/pre-commit`, `flake.nix` (lint check: `node --check tools/factory/*.js`; `nodejs` in the devShell's lint tools)

- [ ] **Step 1: helm.sh** — at the top: `cd "$(dirname "$0")/../.."` (F18); `trap 'systemctl --user start proton-drive-push.timer || true' EXIT` installed before step 5 (F25, with a comment); step 1 retries `curl -fsS "$url/"` every 5 s for up to 60 s and, on the first attempt's 404, prints "waiting for the first collection" (F8); step 0 (new): `systemctl --user start helm-collect.service` synchronously before step 1 so a cold `/var/lib/helm` never reads as a failure. `shellcheck` clean. (No sudo anywhere: unchanged.)
- [ ] **Step 2: failing lint** — add `node --check tools/factory/dark-factory.js` to `githooks/pre-commit` and to `checks.lint` in `flake.nix` (add `pkgs.nodejs` to the lint tool list and the devShell). Introduce a deliberate syntax error in a scratch copy to prove the check catches it (do not commit the error). 
- [ ] **Step 3: dark-factory.js** — F32: after the review loop, if `review && review.approved === false && blocking.length === 0`, `log()` a warning naming the task and record `reviewNote: 'reviewer returned approved=false without blocking findings'` on the task result (status stays derived from blocking findings — the policy's rule). F36: the invariant-audit `spawn` gets `model: M.audit` with `audit: 'fable'` added to the `M` defaults (comment: policy says the audit is Fable, opt-in; an omitted model inherits the session's model by accident). `node --check` green; lint gate green.
- [ ] **Step 4: commit** `helm: acceptance drill waits for the first collection, restores the push timer on exit, runs from the repo root; factory records approved=false reviews and names the audit model; JS syntax check in the lint gate (test: lint)`.

### Task 3 (docs): runbooks, spec wording, board (F6, F8, F9, F11, F12, F13, F14, F15, F18, F19, F20, F31, F33, F34)

**Files:** `docs/runbooks/switch-helm-gaming.md`, `docs/runbooks/helm.md`, `docs/superpowers/specs/2026-09-02-helm-design.md`, `README.md`, `docs/OPERATIONS.md`.

- [ ] **switch-helm-gaming.md** — before the switch: `git -C ~/nixos-agent-env status --short` must be empty (a dirty tree builds a "dirty" revision and the drift tile reads amber); `readlink /nix/var/nix/profiles/system` and write the number down (that is the rollback target). After the switch, step 2 becomes: `systemctl --user start helm-collect.timer helm-flake-check.timer` (they are installed but not started in a logged-in session), then `systemctl --user start helm-collect.service && ls -l /var/lib/helm/index.html` (the page 404s until the first collection), then open the page, then `cd ~/nixos-agent-env && nix develop -c tests/acceptance/helm.sh`. Expected tiles right after the switch: **flake-check red** until the 03:00 run (or run `systemctl --user start helm-flake-check.service` once, minutes), **broker grey** ("no broker instance configured" — none is live with Cowork off), **backup-snapshot green** (restic read without a lock), **drift green**. Step 3 adds `systemctl --user start gamemoded.service` after entering gaming (a `test` activation starts no new user unit). Step 5 adds "quit Steam and every game first: leaving the profile removes `/run/opengl-driver-32`". Rollback section rewritten: never `nixos-rebuild switch --rollback` (it steps back one generation blindly and can land on 21, which re-enables Cowork, the broker and nftables); instead `sudo /nix/var/nix/profiles/system-<N>-link/bin/switch-to-configuration switch` with the number written down, idempotent; a boot-menu pick of an older generation is one-shot (the default entry stays the newest); after any rollback Helm's user timers stay loaded in the session until logout — `systemctl --user stop helm-collect.timer helm-flake-check.timer` or log out. Replace the sentence citing `checks.core-gaming-wiring` as proof about unit text with what is true: the audit's activation diff between the two profiles showed no `egress-*`/`cowork*`/`basket*`/`restic-*`/`helm-*` unit differs, and Helm v1's assertion will make that a build failure.
- [ ] **helm.md** — remove "there is nothing to start" (say: the timers start once by hand after the first switch in a logged-in session, then run on their own); remove the "collector stale" paragraph (the header's generated time plus `systemctl --user status helm-collect.timer` are the check); broker tile grey means no instance is configured; flake-check red before its first 03:00 run.
- [ ] **helm-design.md** — the confidentiality sentence becomes: file modes stop other UIDs reading `/var/lib/helm` directly, but the page and `status.json` are served to any local process over loopback without authentication (authentication arrives with the LAN portal phase); the restic cache is outside the served root.
- [ ] README status line; board: Pre-switch audit section → CLOSED with this round; START HERE step 1 restored to "OPERATOR GATE round 1". Commit `docs: runbooks tell the truth about the first minutes, the rollback and the profiles; Helm spec confidentiality wording; board (test: lint)`.

## Self-review

F1/F5/F9/F17/F20/F26/F16 → Task 1; F8/F18/F25/F32/F36/F35 → Task 2; the rest → Task 3. The relock of `~/flakes/gaming` (its own fix round) is a separate one-task run after both repos land: `nix flake lock --update-input gaming`, `core-gaming-wiring`, `host-core`, toplevel build + closure diff (expect `mesa-demos`, nothing else new). Names: `restic_cache_dir`, `/var/lib/helm-cache`, `tile_broker`, `render_html`, `nonloopback_listeners` (gaming repo).
