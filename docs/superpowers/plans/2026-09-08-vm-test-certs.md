# The VM tests' fixture certificates outlive the store cache — plan (2026-09-08)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) reads the `### KEY (kind, size) — title` section below; it carries `dependsOn`, `touches`, `acceptance` and `commit subject`. A seat sees only `## Global Constraints`, `## Assumptions` and its own section (`tools/factory/seat/factory-brief <plan> <KEY>` is the whole contract).

**Goal:** the three NixOS VM tests stop failing on the calendar. Their fixture certificates are generated inside a `runCommand` with `-days 2`; Nix caches that derivation by its inputs, so from the third day after its first build every VM test reuses an expired certificate and fails with `Certificate verify failed: certificate has expired` — the nightly `flake-check` of 2026-09-08 03:00 CDT (`helm-flake-check`, rev d8263db, 85 s) failed exactly so in `lane-vm`, with no code change behind it.

**Spec:** none — a one-fact bug in test fixtures, typed by the orchestrator from the nightly's own log line. The mechanism it fixes was introduced with each VM test (2026-09-03 to 2026-09-05) and has been latent since; the certs happened to be fresh on every earlier nightly.

**Packet of record:** the tree at 5de1aae; `journalctl --user -u helm-flake-check.service --since -6h -o cat | grep log_tail` → `{"class": "nix-check", "duration_s": 85, … "name": "flake-check", "ok": false, "rev": "d8263db…", "src": "helm-nightly"}` whose `log_tail` ends `AssertionError: {"error": "HTTP 502: <html>… <p>Certificate verify failed: certificate has expired</p>…"}` under `vm-test-run-lane-openrouter`; `grep -n 'days 2' tests/integration/*.nix` → six lines (two per file: the CA and the leaf) in `broker-vm.nix:13,20`, `lane-vm.nix:17,23`, `seat-vm.nix:18,24`.

## Operator questions (each answerable in one word; the default applies if unanswered)

None.

## Spec-to-task map

| item | task |
|---|---|
| the six `-days 2` become long-lived | VC1 |
| a build-time guard that fails a short-lived fixture at once, so the mutant dies today and not in two days | VC1 |

## Decisions (judgement calls, each with the reason and the alternative)

- **D1 `-days 3650`, not "generate at VM boot".** Reason: the fixture is a test CA and leaf inside a throwaway VM; a ten-year validity removes the calendar from the test with a one-token change per line, and the store cache stays a feature. Alternative rejected: generating the certs in the VM's activation script — more code in three tests for the same effect.
- **D2 The guard is `openssl x509 -checkend`, inside the same `runCommand`.** Reason: with the guard, `-days 2` fails the derivation immediately (`Certificate will expire`), so the section's mutant is discriminating on any day; without it the mutant is only caught two days later. Alternative rejected: a unit test that parses the Nix — it cannot see the certificate.

## Global Constraints

- The host `core` runs LIVE from this repo (`nixosConfigurations.core`). Everything you do is build-only: never `sudo`, `nixos-rebuild`, `systemctl start|stop|restart`, basket mount/teardown, or any seat launch.
- Work only in your workspace clone; `git add` new files before any `nix build`; commit exactly one commit with the section's byte-exact subject; never commit `docs/OPERATIONS.md`; never edit the plan file.
- The result block's exact form: `FACTORY-RESULT status=<done|partial|failed>` — a space after the label, never a colon.
- The three VM checks each take 5–40 minutes on this host (KVM); run them one at a time and paste each one's last lines.
- TDD: the red first (today it exists by the calendar — the cached fixture is expired), then the change, then the green; the mutant of item 2 shown red and reverted.

## Assumptions

1. The store still holds the expired fixture derivations today (the nightly failed on them at 03:00 CDT; nothing garbage-collected since). If `nix build .#checks.x86_64-linux.lane-vm` is green before any change, the cache has been rebuilt: say so in the commit body and take the red from the mutant of item 2 instead.
2. `pkgs.openssl` in the `runCommand`'s `nativeBuildInputs` (already there) provides `openssl x509 -checkend`.
3. `nix build .#checks.x86_64-linux.integration` is the broker VM test (`flake.nix`: `integration = import ./tests/integration/broker-vm.nix`); it is run as a check but is not in `docs/MAP.md`'s check list, so it is named in the section's steps, not in `acceptance`.

## Waves

| wave | groups | dependsOn |
|---|---|---|
| 1 | VC1 | — |

## Operator

No switch, no unit, no key. After the landing the next nightly `helm-flake-check` (03:00 CDT) should return `ok` at the new rev; the Helm `flake-check` tile turns from `warn`/`fail` to `ok` then.

## Dispatch

Run: `vc1`. `tools/factory/seat/factory-dispatch vc1 ~/nixos-agent-env docs/superpowers/plans/2026-09-08-vm-test-certs.md --dry-run` → `would run: factory-wave vc1 /home/dalhaka/nixos-agent-env "VC1"`; then the same without `--dry-run`, in the background. The routing table's code/XS row (Flash, effort off) applies. Gate: the session copy of `~/factory/bin/opus-gate.js`, `plan: 2026-09-08-vm-test-certs.md`; the reviewer may run the three VM checks (minutes each) and must apply the mutant of item 2. Landing: main merged into the workspace first, then `factory-integrate vc1 ~/nixos-agent-env VC1 && git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/vc1` (the integrator runs `lane-vm`, `seat-vm` and `lint`).

## Not in this plan

- `comfyui-vm` and `helm-vm` (no fixture certificate); the media flake's own VM tests (its repo).
- Any change to the broker, lane or seat modules: the fixture is the tests' only.

## Tasks

### VC1 (code, XS) — the VM tests' fixture certificates outlive the store cache: `-days 3650` on the six `openssl` lines and a build-time expiry guard in each `testCerts` derivation

**dependsOn:** —

**Files:**
- Modify: `tests/integration/broker-vm.nix`, `tests/integration/lane-vm.nix`, `tests/integration/seat-vm.nix`

**Interfaces:**

- In each file's `testCerts = pkgs.runCommand … ''…''` block: every `-days 2` becomes `-days 3650` (the CA's `openssl req -x509 … -days 3650` and the leaf's `openssl x509 -req … -CAcreateserial -days 3650`); after the last certificate is written, one guard line per certificate the block produces: `openssl x509 -in $out/<name>.crt -noout -checkend 31536000` (exit 1 with `Certificate will expire` when fewer than 365 days remain — the build then fails at once). In `broker-vm.nix` the leaf certs are written in a loop over hosts (`$out/$h.crt`): put the guard inside the loop after each leaf, plus one for `$out/ca.crt`. Nothing else in the three files changes; the VM scripts, the CA bundle wiring and every assertion stay byte for byte.

**Facts:**

- `sed -n '10,24p' tests/integration/lane-vm.nix` → `testCerts =` / `pkgs.runCommand "lane-vm-test-certs"` … `nativeBuildInputs = [ pkgs.openssl ];` … `openssl req -x509 -newkey rsa:2048 -nodes -days 2 \` … `openssl x509 -req -in $out/openrouter.test.csr -CA $out/ca.crt -CAkey $out/ca.key \` / `-CAcreateserial -days 2 -copy_extensions copy -out $out/openrouter.test.crt` — the two lines; `seat-vm.nix:18,24` the same shape; `broker-vm.nix:13,20` the same with `$out/$h.crt` in a loop.
- The nightly's failure line (2026-09-08 08:01Z, rev d8263db): `AssertionError: {"error": "HTTP 502: <html>\n<head>\n    <title>502 Bad Gateway</title>\n</head>\n<body>\n    <h1>502 Bad Gateway</h1>\n    <p>Certificate verify failed: certificate has expired</p>\n</body>\n</html>", …}` under `vm-test-run-lane-openrouter`; the flake-check before it (2026-09-07 12:53Z, rev 277d022) was `ok` — the certs were younger than two days then.
- `flake.nix:1750` → `lane-vm = import ./tests/integration/lane-vm.nix {`; `:1755` → `seat-vm = import ./tests/integration/seat-vm.nix {`; `:1761` → `integration = import ./tests/integration/broker-vm.nix {`.

- [ ] **Step 1: Run it red** — `nix build .#checks.x86_64-linux.lane-vm -L --no-link` at the workspace's base: red with `certificate has expired` in the driver's `AssertionError` (Assumption 1; if green, the mutant of Step 4 supplies the red). Paste the failing line.
- [ ] **Step 2: The edits** — the six `-days 3650` and the guard lines, as the Interfaces state.
- [ ] **Step 3: Run green** — `nix build .#checks.x86_64-linux.lane-vm -L --no-link`; `… seat-vm`; `… integration`; `nix develop -c githooks/pre-commit`. Paste each check's last three lines.
- [ ] **Step 4: The mutant** — in a scratch copy, restore `-days 2` on the leaf line of `lane-vm.nix` only: `nix build .#checks.x86_64-linux.lane-vm -L --no-link` must fail in the `lane-vm-test-certs` derivation with `Certificate will expire` (the guard), before any VM starts; paste the line; revert.
- [ ] **Step 5: Commit** — one commit, the subject below, the two trailers; the body carries the red of Step 1, the greens of Step 3 and the mutant's red of Step 4.

| # | assertion | discriminating fixture | mutant |
|---|---|---|---|
| 1 | each of the three checks is green after the change | the expired store fixture (today) | `-days 2` left on any one of the six lines → the guard fails that derivation at once (`Certificate will expire`) |
| 2 | the guard sits after the certificate it checks and names the right file | the loop in `broker-vm.nix` | the guard placed before the leaf is written → `No such file`; the guard pointed at `ca.crt` only → a short-lived leaf passes (row 1's mutant on the leaf line) |

**Tests:** rows 1–2; the discriminating fixture is the calendar itself, replaced by the guard so the mutant dies on any day.

**Relaunch:** `vc1b` with `"VC1"`; the diff stays in `~/factory/ws/vc1/VC1`.

**touches:** tests/integration/broker-vm.nix, tests/integration/lane-vm.nix, tests/integration/seat-vm.nix
**acceptance:** lane-vm, seat-vm
**commit subject:** `tests: the VM fixture certificates outlive the store cache — -days 3650 on the six openssl lines and a build-time expiry guard in each testCerts derivation (test: lane-vm, seat-vm)`
