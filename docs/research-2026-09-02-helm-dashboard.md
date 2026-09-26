# Research digest 2026-09-02 — Helm status dashboard — data sources and zero-outbound serving

*Read-only research by a Sonnet agent (factory model policy), 2026-09-02 evening, against the host pin nixpkgs ac62194c and the flake pin 34ab9907. Evidence lines are the agent's own command outputs and cited URLs; "unverified" means exactly that. Feeds the Lanes G/H/I design in docs/OPERATIONS.md.*

## Data sources — table

| Source | Command (verified, no sudo) | Needs sudo? | Verified output snippet |
|---|---|---|---|
| **basket doctor** | `basket doctor` — `pkgs/basket/basket.sh` `cmd_doctor` (L314-365) | No | Prints `%-4s %-12s %s` lines (verdict/name/detail) for swap, pcscd, age-plugin, kvm, vsock, stale-mounts; exit 1 if any `FAIL`, else 0. **No JSON option exists today** — text only. Tested via `tests/unit/50-doctor.bats` with `--root` fixture override, asserting on substrings like `*"FAIL"*"swap"*`. |
| **restic local repo** | `RESTIC_REPOSITORY=/var/lib/restic/core RESTIC_PASSWORD_FILE=~/.config/restic/password restic snapshots --json` | No | Repo is `drwx------ dalhaka:users` (config `-r--------`) — owned by the operator, not root. Live output: `[{"time":"2026-09-02T19:54:34...","paths":[...],"hostname":"nixos","summary":{...},"short_id":"16e29ff5"}]`. |
| **Proton push result** | `journalctl --user -u proton-drive-push -o short-iso \| grep "proton-backup-push:"` | No | `2026-09-02T20:07:21-05:00 nixos proton-backup-push[291127]: proton-backup-push: OK snapshots=1 remote=1`. `-o json` works too but is verbose (no `jq` on PATH by default — use the vendored Python or `-o short-iso`+grep). |
| **systemd timers/services** | `systemctl show -p ActiveState,Result,NextElapseUSecRealtime,LastTriggerUSec restic-backups-core-local.timer restic-backups-core-local.service` and `systemctl --user show -p ... proton-drive-push.timer proton-drive-push.service` | No | Both timers `ActiveState=active`, `Result=success`; `NextElapseUSecRealtime` populated (00:00 / 00:30 CDT). **`LastTriggerUSec` came back empty for both** in this session — flag as unverified until a real automatic trigger is observed. |
| **egress broker audit log** | `nixosModules/egressBroker.nix:18` → `audit_log = "/var/lib/egress-broker/${name}/audit.jsonl"` | No | Live: `-rw-r--r-- 1 990 987 ... audit.jsonl`, dir `drwxr-xr-x` — world-readable, confirmed. Line shape: `{"ts":1788396627.24,"instance":"cowork","client":"10.100.1.2","method":"POST","host":"api.anthropic.com","sni":...,"path":...,"bytes_out":2,"bytes_in":547,"verdict":"allow","reason":"ok"}`. Counted with a stdlib Python one-liner (no sudo, no jq): total lines 4636, `allow_24h=3407`, `deny_24h=1203`. |
| **nix flake check result** | none exists on disk | — | Only leftover `result`/`result-1..3` symlinks in repo root (gitignored) from the last manual run, pointing at store paths (`lint`, `unit-tests`, `broker-addon-tests`, `nixos-system-core-...`) — **no timestamp or pass/fail record file**. Proposal: a daily user timer that runs `nix flake check` in the repo (read-only access, no sudo needed) and writes `/var/lib/helm/flake-check-result.json` `{timestamp, exit_code}` atomically. |
| **GPU** | `nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader` | No | `NVIDIA GeForce RTX 5090, 2 %, 1428 MiB, 32607 MiB, 39, 36.86 W` |
| **CPU/RAM/disk** | `nproc`, `free -h`, `df -h /` | No | 24 cores; Mem 124Gi total / 8.0Gi used / 116Gi available; Swap 0B (matches doctor's swap-off invariant); `/` (also covers `/home`, `/var/lib/restic` — single filesystem on this host) 3.6T size, 74G used, 3% use. |
| **Running system vs repo HEAD** | `readlink -f /run/current-system`; `nixos-version`; `nix flake metadata --offline` | No | `/run/current-system` → `...-nixos-system-core-25.05.20260102.ac62194`; `nixos-version` → `25.05.20260102.ac62194 (Warbler)`. This derivation name encodes only the nixpkgs short-rev, **not the repo's own git rev** (`nix flake metadata` shows `Revision: 325b5049...`), so there is currently **no cheap way** to tell if the live system is behind repo HEAD without a full `nixos-rebuild build`. Cheapest fix (matches concept doc `2026-09-02j`'s own suggestion): have the switch step write a marker file (e.g. `/var/lib/helm/switched-rev`) with the locked flake rev at activation time; Helm's tile then just diffs that against `nix flake metadata`'s current rev — no build required. |

## Serving recommendation

At the pinned nixpkgs rev (`ac62194c3917d5f474c1a844b6fd6da2db95077d`), confirmed via `nix eval --offline`:
- `static-web-server` **2.39.0**, `services.static-web-server` module present.
- `nginx` **1.28.0**, `services.nginx` module present.
- `glance` **0.8.4**, `services.glance` module present.
- `homepage-dashboard` **1.2.0**, `services.homepage-dashboard` module present.
- `dashy` — **not packaged at this pin** (`nix eval` fails: "does not provide attribute ... dashy"); excluded.

**Recommendation: option (a) — static-web-server serving a single self-contained HTML file regenerated by a systemd timer, bound to `127.0.0.1`.** Reasoning for zero-outbound: static-web-server's own code path never makes outbound calls — it only reads a directory and serves files, giving the smallest audit surface for the hard zero-outbound requirement. glance and homepage-dashboard are both full dashboard apps (custom-api widgets can point at a local `http://127.0.0.1` endpoint with no internet, satisfying the letter of the requirement) but I could not verify within budget whether their *default* behavior (update/version checks, default-enabled widgets such as weather/RSS/search bars) makes any startup network calls — that needs a source read I didn't do. Treat glance/homepage-dashboard as **plausible but unverified** for zero-outbound; static-web-server + hand-written HTML is the only option confirmed safe by construction. nginx is an equally valid substitute for static-web-server, just a larger binary/config surface for the same job.

## Collector design

- `pkgs/helm/collect.py` — stdlib only (`json`, `subprocess`, `time`, `pathlib`). One function per source: `collect_basket_doctor()`, `collect_restic()`, `collect_proton_push()`, `collect_systemd(units)`, `collect_broker_audit(paths)`, `collect_flake_check()`, `collect_gpu()`, `collect_host()`. Each returns `{name, status: ok|warn|fail|unknown, detail, checked_at}`, wrapped in try/except so a missing binary (e.g. no `nvidia-smi` on a non-GPU box) degrades to `unknown` rather than crashing the whole run.
- Writes `/var/lib/helm/status.json` atomically (tmp file + rename — same pattern already used for `ca.pem.tmp` in `nixosModules/egressBroker.nix`), then renders `/var/lib/helm/index.html` with inline `<style>`, no external fonts/scripts/JS frameworks — satisfies zero-outbound for the page content itself, not just the server.
- Runs as its own unprivileged systemd user (`DynamicUser` or a dedicated `helm` system user) with read-only paths to `/var/lib/restic/core`, `/var/lib/egress-broker/*/audit.jsonl`, the repo checkout, and permission to invoke `basket doctor`, `restic`, `nvidia-smi`, `systemctl`, `journalctl` as subprocesses (`subprocess.run` with explicit argv, timeouts, no shell).
- **Tests**: `tests/helm/` mirroring `tests/broker/test_policy.py`'s pattern — load `pkgs/helm/collect.py` directly via `importlib.util.spec_from_file_location` (no packaging needed), then fixture per source: a tmp-path restic repo stub or monkeypatched `subprocess.run` returning canned `restic snapshots --json`; a tmp `audit.jsonl` with a few allow/deny lines (schema verified above); monkeypatched `systemctl show` output; a canned PASS/WARN/FAIL text blob to test the `basket doctor` parser; a missing-binary case for `nvidia-smi` to verify graceful `unknown`. Reuse `tests/mocks/proton-drive-mock.sh`'s style (a fake executable early on `PATH`) for bats-level acceptance mocking. New Python is automatically covered by the repo's existing `ruff check`/`ruff format` gate in `nix flake check` once added.

## Risks / unknowns

- `basket doctor` has no machine-readable output today; Helm must parse the fixed-width text format, which is stable in practice but not a guaranteed contract — consider proposing a `--format json` flag as separate follow-up work (not done here; read-only agent).
- `LastTriggerUSec` was empty for both the system restic timer and the user proton-drive-push timer in this session's query — re-verify after an actual unattended trigger before trusting that field in a tile.
- No on-disk `nix flake check` result exists; the design above is a proposal, not something implemented/tested yet.
- glance/homepage-dashboard's zero-outbound behavior (telemetry, default widgets) is **unverified at the source level** — don't treat them as pre-cleared; only the static-web-server + hand-written-HTML path is confirmed safe by construction.
- `df` shows `/`, `/home`, and `/var/lib/restic` on one filesystem on this host — fine for a single "disk" tile here, but host-specific, don't hard-code the assumption elsewhere.
- Only tested `journalctl --user` as `dalhaka` itself (uid 1000, the unit's own owner); did not test as a separate unprivileged user.

## Commands to verify the top 3 claims

```bash
# 1. Egress broker audit log is world-readable, no sudo
ls -la /var/lib/egress-broker/*/audit.jsonl && tail -3 /var/lib/egress-broker/cowork/audit.jsonl

# 2. restic repo readable by dalhaka without sudo
RESTIC_REPOSITORY=/var/lib/restic/core RESTIC_PASSWORD_FILE=~/.config/restic/password \
  restic snapshots --json | head -c 400

# 3. static-web-server and nginx both exist at the pinned nixpkgs rev
nix eval --offline github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d#static-web-server.version \
                    github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d#nginx.version
```
