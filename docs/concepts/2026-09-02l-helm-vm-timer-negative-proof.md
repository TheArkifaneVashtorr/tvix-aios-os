# Concept 2026-09-02l — Helm VM test should stop a timer, not just start one

**Class:** build-time test coverage gap on Lane G (Helm). **Status:**
proposed (Helm factory Task 6, from writing the acceptance drill).

**Origin (2026-09-02, Helm Task 6):** `tests/acceptance/helm.sh`'s step 5
is the drill's negative proof — it stops `proton-drive-push.timer`, runs a
fresh `helm-collect`, and asserts the `timers` tile reads `fail`; then it
restarts the timer, collects again, and asserts `ok`. That's the only place
in the whole Helm stack this ever gets checked. `checks.helm-vm`
(`tests/integration/helm-vm.nix:64-65`) only asserts `tiles["timers"]["status"]
== "ok"` with `helm-collect.timer` left running the whole time — it never
stops a timer and checks for `fail`. `pkgs/helm/tests/helm/test_collect.py`
does cover the parsing logic (`test_timers_inactive_is_fail`), but that's a
unit test against a hand-built `systemctl show` fixture, not a real systemd
unit actually being down. So the one thing the acceptance drill's own
Section 5 exists to prove — that the tile's red state is reachable, not
just its green one, against a real timer — is unverified anywhere in `nix
flake check`. If a future refactor of `tile_timers`'s parsing broke the
fail branch specifically (say, a regex that always matches "active" loosely
enough), CI would stay green and the bug would surface for the first time
during the operator's live acceptance run — exactly the kind of gap
concept 2026-09-02j closed for backup parity and 2026-09-02k closed for
timer arming after a switch.

**Idea:** add a second scenario (or extend the existing one) to
`tests/integration/helm-vm.nix` that stops a real user timer inside the VM
before the final collection and asserts the tile flips:

```python
machine.succeed("systemctl --user -M alice@ stop helm-collect.timer")
machine.succeed("su - alice -c 'helm-collect --config /etc/helm/config.json --out /var/lib/helm'")
st = json.loads(machine.succeed("cat /var/lib/helm/status.json"))
assert {t["name"]: t["status"] for t in st["tiles"]}["timers"] == "fail"
```

placed after the existing `assert tiles["timers"]["status"] == "ok"` so the
same VM proves both branches in one boot (no second machine needed — the
timer only needs to be part of `services.helm.timers.user` in the test
fixture, which `helm-collect.timer` already is). The VM test's `alice`
fixture user and `helm-collect` binary are already wired for exactly this;
the change is additive to an existing check, not a new one.

**Payoff:** moves the acceptance drill's negative proof from "the operator
discovers a broken fail-path live" to "CI catches a broken fail-path before
any factory task claiming `helm-vm` green can land." It's the same shape of
fix as 2026-09-02j (prove the failure detector detects, at build time, not
just the happy path) applied to Helm's own timers tile instead of the
backup push. It also shortens the acceptance drill itself over time: once
the negative proof is build-time-verified, Section 5 of
`tests/acceptance/helm.sh` becomes a live confirmation rather than the only
place the logic is ever exercised — worth keeping for the real-systemd
sanity check, but no longer the sole line of defense.

**Dependencies:** `checks.helm-vm` (`tests/integration/helm-vm.nix`,
Helm Task 4) and `pkgs/helm/collect.py`'s `tile_timers` (Helm Task 1) — no
new modules, no new packages.

**Earliest landing:** a small follow-up factory task against this repo,
scoped to `tests/integration/helm-vm.nix` alone (extend the existing test,
re-run `checks.helm-vm`) — does not block the pending Helm operator gate.
