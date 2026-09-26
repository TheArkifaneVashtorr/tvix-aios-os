# Helm v1 — the switch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Executor: `tools/factory/dark-factory.js` in nixos-agent-env (host `core`), launched only AFTER the operator has passed the round-1 gate (Helm v0 live).

**Goal:** On http://localhost:7700 the operator clicks a profile (`base`, `gaming`, `media`, …) and the machine switches to it at runtime, or clicks a flake and a terminal opens in that flake's dev shell running `claude`. No code, no password, loopback only, no JavaScript.

**Architecture:** a root template unit `helm-switch@.service` with a generated allowlisted script; a polkit rule granting the operator `start` on exactly the enumerated instances; a Python stdlib user service `helm-serve` replacing static-web-server when `services.helm.control.enable`, serving v0's page plus forms, with Host/Origin/Fetch-Metadata/token checks and a held `flock`; a generated `helm-open-workspace` launcher; two new tiles injected at serve time.

**Spec:** `docs/superpowers/specs/2026-09-02-helm-v1-switch-design.md` (rev 2, approved). Research: `docs/research-2026-09-02-helm-v1-switch.md`.

## Global Constraints

- Build-only; never start units, never switch profiles on the live host; the VM test is the proof.
- The `test` action (`switch-to-configuration test`) everywhere — never `switch`/`boot`.
- `%i` validation: regex `^[a-z][a-z0-9-]{0,31}$` AND membership in `control.profiles`; polkit rule enumerates exact unit names and requires `action.lookup("verb") === "start"`; ES5 only (polkit 126 = duktape: no `includes`, `===`, `indexOf`); the rule returns `undefined` otherwise.
- Every route checks `Host` against the allowlist (`<alias>:<port>` for `control.hostAliases` + the bound address); every POST also needs `Sec-Fetch-Site: same-origin` or an allowed `Origin`, a valid per-boot token, an allowlisted target, and the free lock. Forms only; no `<script`, no `src=`, no `href="http`.
- Python stdlib only; ruff gate (already covers pkgs/helm tests/helm). Bash scripts shellcheck-clean, listed in the lint gate and pre-commit.
- Commit subjects `helm: … (test: …)` / `docs: …`.

---

### Task 1: `helm-serve` — the control backend

**Files:** `pkgs/helm/serve.py`, `tests/helm/test_serve.py`, `flake.nix` (`checks.helm-unit` already runs `tests/helm`; add `helmServe` package `writeShellApplication { runtimeInputs = [ python3 systemd ]; text = exec python3 ${./pkgs/helm/serve.py} "$@" }`).

**Interfaces (Produces):**
```python
# serve.py
def load_config(path) -> dict                     # /etc/helm/config.json + "control" section (Task 3 writes it)
def accepted_hosts(cfg) -> set[str]               # {"127.0.0.1:7700","localhost:7700", bound}
def accepted_origins(cfg) -> set[str]             # {"http://"+h for h in accepted_hosts}
def validate_post(headers: dict, form: dict, token: str, allow: set[str], key: str) -> tuple[int, str]  # (0,"") ok else (403|400, reason)
def run_switch(name) -> subprocess.CompletedProcess   # ["systemctl","start",f"helm-switch@{name}.service"], timeout 360
def spawn_open(name) -> None                          # Popen(["kgx","-e","helm-open-workspace",name], start_new_session=True)
def render_control(status_html: str, cfg, token) -> str   # injects the profile/workspaces tiles + forms before </main>
class Handler(http.server.BaseHTTPRequestHandler): GET / | /status.json ; POST /action/switch | /action/open
def main(argv) -> int   # --config PATH --token-file PATH --lock-file PATH --listen HOST:PORT
```
Lock: `fcntl.flock(fd, LOCK_EX | LOCK_NB)` on `--lock-file`, held for the duration of `run_switch`; busy → `409`. Token: 32 random bytes hex written `0600` to `--token-file` at start. Audit: one `helm-serve: <verb> <target> <result> from=<Host>` journal line per action (stderr → journal).

- [ ] **Failing tests** (`tests/helm/test_serve.py`, load by path like `test_collect.py`):
```python
GOOD = {"Host": "localhost:7700", "Sec-Fetch-Site": "same-origin"}
ALLOW = {"base", "gaming"}

def test_validate_happy():
    assert serve.validate_post(GOOD, {"profile": "gaming", "token": "t"}, "t", ALLOW, "profile") == (0, "")

def test_validate_rejects_wrong_host():
    assert serve.validate_post({"Host": "evil.example:7700", "Sec-Fetch-Site": "same-origin"}, {"profile": "gaming", "token": "t"}, "t", ALLOW, "profile")[0] == 403

def test_validate_accepts_ip_host_alias():
    assert serve.validate_post({"Host": "127.0.0.1:7700", "Sec-Fetch-Site": "same-origin"}, {"profile": "gaming", "token": "t"}, "t", ALLOW, "profile") == (0, "")

def test_validate_rejects_cross_site():
    assert serve.validate_post({"Host": "localhost:7700", "Sec-Fetch-Site": "cross-site"}, {"profile": "gaming", "token": "t"}, "t", ALLOW, "profile")[0] == 403

def test_validate_origin_fallback():
    assert serve.validate_post({"Host": "localhost:7700", "Origin": "http://localhost:7700"}, {"profile": "gaming", "token": "t"}, "t", ALLOW, "profile") == (0, "")
    assert serve.validate_post({"Host": "localhost:7700", "Origin": "http://evil.example"}, {"profile": "gaming", "token": "t"}, "t", ALLOW, "profile")[0] == 403
    assert serve.validate_post({"Host": "localhost:7700"}, {"profile": "gaming", "token": "t"}, "t", ALLOW, "profile")[0] == 403  # no Sec-Fetch-Site, no Origin

def test_validate_rejects_bad_token_and_unknown_target():
    assert serve.validate_post(GOOD, {"profile": "gaming", "token": "x"}, "t", ALLOW, "profile")[0] == 403
    assert serve.validate_post(GOOD, {"profile": "nope", "token": "t"}, "t", ALLOW, "profile")[0] == 403
    assert serve.validate_post(GOOD, {"profile": "../x", "token": "t"}, "t", ALLOW, "profile")[0] == 403

def test_switch_calls_systemctl_exactly(monkeypatch):
    seen = {}
    monkeypatch.setattr(serve.subprocess, "run", lambda argv, **kw: seen.setdefault("argv", argv) or subprocess.CompletedProcess(argv, 0, "", ""))
    serve.run_switch("gaming")
    assert seen["argv"] == ["systemctl", "start", "helm-switch@gaming.service"]

def test_open_spawns_launcher(monkeypatch):
    seen = {}
    monkeypatch.setattr(serve.subprocess, "Popen", lambda argv, **kw: seen.setdefault("argv", argv))
    serve.spawn_open("gaming")
    assert seen["argv"] == ["kgx", "-e", "helm-open-workspace", "gaming"]

def test_render_control_forms_and_no_script():
    cfg = {"control": {"profiles": ["base", "gaming"], "workspaces": {"gaming": {"path": "/home/x/flakes/gaming"}}, "active_profile": "base"}}
    html = serve.render_control("<html><body><main class=\"grid\"></main></body></html>", cfg, "tok")
    assert html.count('action="/action/switch"') == 2 and html.count('action="/action/open"') == 1
    assert 'value="tok"' in html and "<script" not in html and "src=" not in html

def test_lock_gives_409(tmp_path):
    lock = tmp_path / "l"
    with serve.switch_lock(lock) as ok:
        assert ok
        with serve.switch_lock(lock) as ok2:
            assert not ok2
```
Plus an end-to-end test that starts `Handler` on an ephemeral loopback port in a thread with a fake `run_switch`, POSTs with `http.client` and asserts 403/409/200 and that the fake was called once.
- [ ] Implement; run `nix develop -c pytest tests/helm -q`; lint gate. Commit `helm: helm-serve — loopback control backend with Host/Origin/Fetch-Metadata/token checks, held lock, forms only (test: helm-unit, lint)`.

---

### Task 2: the switch script and the workspace launcher

**Files:** `pkgs/helm/helm-switch.sh` (template; the module substitutes `@PROFILES@` and `@MARKER@`), `pkgs/helm/helm-open-workspace.sh` (template; `@WORKSPACES_JSON@`), `tests/unit/70-helm-switch.bats`, `tests/unit/71-helm-open-workspace.bats`, `flake.nix` + `githooks/pre-commit` (shellcheck the two scripts; bats already runs `tests/unit`).

- [ ] `helm-switch.sh` behaviour (bats first): arg `$1` = profile; exit 2 unless it matches `^[a-z][a-z0-9-]{0,31}$` AND is in `@PROFILES@` (space-separated); `ROOT=/nix/var/nix/profiles/system` if `$ROOT/bin/switch-to-configuration` exists else `/run/booted-system`; `from=$(cat @MARKER@ 2>/dev/null || echo unknown)`; `echo "helm-switch: begin $from -> $1 root=$ROOT"`; `base` → `$ROOT/bin/switch-to-configuration test`; else `$ROOT/specialisation/$1/bin/switch-to-configuration test`; `echo "helm-switch: end $1 exit=$?"`; exit with that code. bats: stub the two binaries on a fake `ROOT` via `HELM_SWITCH_ROOT_OVERRIDE` env (test seam), assert rejections run nothing (`../x`, `gaming;reboot`, `nope`), the mapping for `base` and `alt`, the fallback when the profile root lacks the binary, and the two audit lines.
- [ ] `helm-open-workspace.sh` (bats first): reads `@WORKSPACES_JSON@` (`{"name": {"path": "...", "devShell": "default"|null, "basket": null|"id"}}`) with `jq`; unknown name → exit 2; if `basket` set and `/run/baskets/<id>` not a mountpoint → print the exact `sudo basket mount …` line and `read -r` (wait for Enter); `cd "$path"`; `devShell` null → `exec bash -ic claude`; else `exec nix develop ".#$devShell" -c bash -ic claude`. bats: stub `nix`, `bash`, `mountpoint` on PATH; assert argv per case, the wait prompt when a basket is not mounted (feed Enter), exit 2 for unknown.
- [ ] Lint (`shellcheck pkgs/helm/*.sh` added to the gate + pre-commit), `unit` check; commit `helm: switch script (allowlisted, test action, profile-root fallback, audit lines) and workspace launcher (test: unit, lint)`.

---

### Task 3: module — `services.helm.control`

**Files:** `nixosModules/helm.nix`, `flake.nix` (`helmControlSystem`, `helmControlBadSystem*`, checks `helm-control-eval`, `helm-control-assertion-negative-{profiles,enable,agentunit,workspace}`).

- [ ] Options: `control.enable` (false), `control.profiles` (default: `[ "base" ] ++ lib.attrNames config.specialisation`), `control.workspaces` (`attrsOf (submodule { path (str); devShell (nullOr str, "default"); basket (nullOr str) })`), `control.hostAliases` (`[ "localhost" "127.0.0.1" ]`).
- [ ] Config when `control.enable`:
  - `services.static-web-server.enable = lib.mkForce false` (and drop its SupplementaryGroups line under this branch).
  - `systemd.services."helm-switch@"`: `Type=oneshot`, `TimeoutStartSec=5min`, `ExecStart=${switchScript}/bin/helm-switch %i`, `ProtectHome=yes`, `PrivateTmp=yes`, `Environment=` empty (no passthrough).
  - `security.polkit.extraConfig` = generated JS:
    ```js
    polkit.addRule(function (action, subject) {
      if (action.id !== "org.freedesktop.systemd1.manage-units") { return undefined; }
      if (action.lookup("verb") !== "start") { return undefined; }
      if (subject.user !== "<operatorUser>") { return undefined; }
      var unit = action.lookup("unit");
      var allowed = ["helm-switch@base.service", "helm-switch@gaming.service", ...];
      if (allowed.indexOf(unit) !== -1) { return polkit.Result.YES; }
      return undefined;
    });
    ```
  - `systemd.user.services.helm-serve`: `ConditionUser`, `WantedBy=default.target`, `Restart=on-failure`, `ExecStart=${helmServe}/bin/helm-serve --config /etc/helm/config.json --token-file %t/helm/token --lock-file %t/helm/switch.lock --listen ${cfg.listen}`, `RuntimeDirectory=helm`, hardening as the v0 units (`ProtectHome=read-only`, `ReadWritePaths=/var/lib/helm`, `NoNewPrivileges`, `UMask=0077` for the token).
  - `/etc/helm/config.json` gains `"control": { profiles, workspaces, host_aliases, listen, marker: "/etc/helm/profile" }`.
  - `helm-open-workspace` package generated with the workspaces JSON substituted; `environment.systemPackages` += it.
  - Assertions: `control.enable -> cfg.enable`; every profile ≠ base is in `config.specialisation`; `environment.etc."helm/profile"` is set in the base and every specialisation; workspace names match the regex and paths are absolute; **profiles never touch agent units**: for each specialisation `s`, `diffUnits = filter (n: (config.systemd.units.${n}.text or null) != (s.configuration.systemd.units.${n}.text or null)) (attrNames (config.systemd.units // s.configuration.systemd.units))`; assert no `n` in `diffUnits` matches `^(egress-|cowork|basket|restic-backups-|helm-)` unless `n` ends with `-<profileName>.service` (or `.timer`). Message names the offending unit.
- [ ] Checks: `helm-control-eval` (a harness with `specialisation.alt` marker-only + `control.enable`): polkit text contains exactly `helm-switch@base.service` and `helm-switch@alt.service`, the verb guard and the user; `helm-switch@` exists with the `test`-action script; static-web-server off; `helm-serve` present; config.json has the control section. Negatives: `profiles = [ "base" "nope" ]`; `control.enable` without `services.helm.enable`; a specialisation that sets `systemd.services.egress-broker-cowork.serviceConfig.Nice = 1` (the agent-unit guard); `workspaces."Bad Name" = …`.
- [ ] Commit `helm: services.helm.control — allowlisted root switch unit, verb-scoped polkit grant, helm-serve user service, profiles-never-touch-agent-units assertion (test: helm-control-eval, helm-control-assertion-negative-profiles/enable/agentunit/workspace, lint)`.

---

### Task 4: VM test — a real runtime profile switch through the page

**Files:** `tests/integration/helm-control-vm.nix`, `flake.nix` (`checks.helm-control-vm`).

- [ ] Node: `helmModule`, alice (uid 1000, linger), `system.configurationRevision = "deadbeef"`, `specialisation.alt.configuration.environment.etc."helm/profile".text = lib.mkForce "alt"`, `environment.etc."helm/profile".text = "base"`, `services.helm = { enable; control.enable = true; operatorUser = "alice"; … v0 test settings … control.workspaces.demo = { path = "/var/lib/fake-repo"; devShell = null; }; }`, `security.polkit.enable = true`, `environment.systemPackages = [ curl jq ]`.
- [ ] testScript (as alice via `su alice -c` / `systemctl --user -M alice@`): wait for `helm-serve` (`curl -fsS -H 'Host: localhost:7700' http://127.0.0.1:7700/` contains `action="/action/switch"`); `TOKEN=$(cat /run/user/1000/helm/token)`; POST switch to `alt` with `Host: localhost:7700`, `Sec-Fetch-Site: same-origin` → 200 and `cat /etc/helm/profile` == `alt` and `readlink /run/current-system` changed; POST switch to `base` → marker `base`; negatives: foreign `Origin` → 403, wrong `Host` → 403, no token → 403, unknown profile → 403, no `Sec-Fetch-Site` and no `Origin` → 403 — marker unchanged after each; `su alice -c 'systemctl start helm-switch@nope.service'` fails (polkit); `su alice -c 'systemctl kill helm-switch@alt.service'` fails; `su alice -c 'systemctl set-property helm-switch@alt.service Nice=1'` fails; `journalctl -u 'helm-switch@*'` has `begin`/`end` lines; the page contains one form per profile and per workspace and no `<script`.
- [ ] Run to green (long); commit `helm: VM test — a real specialisation switch through the loopback page; negatives and polkit denials (test: helm-control-vm)`.

---

### Task 5: core wiring

**Files:** `hosts/core/helm.nix` (`services.helm.control = { enable = true; workspaces = { nixos-agent-env = { path = "/home/dalhaka/nixos-agent-env"; }; gaming = { path = "/home/dalhaka/flakes/gaming"; }; media = { path = "/home/dalhaka/flakes/media"; }; strategy = { path = "/home/dalhaka/strategy"; devShell = null; }; }; }`), `flake.nix` if `host-core` needs a new assertion (polkit text present).

- [ ] `host-core`, `helm-control-eval`; toplevel build + closure diff (polkit rule, helm-switch@ unit, helm-serve, helm-open-workspace; static-web-server gone). Commit `helm: core enables the control surface with four workspaces (test: host-core, helm-control-eval)`.

---

### Task 6 (docs): acceptance, runbook, board, concept

**Files:** `tests/acceptance/helm-v1.sh` (page shows the profile tile with `base`; click-equivalents via curl with the token: switch to `gaming` → marker + Steam present within a minute → `base`; `media` if wired; open `gaming` workspace → a Console window (operator judgment); the cowork broker audit shows no restart across switches), `docs/runbooks/helm-v1.md` (what each button does, what it never does — boot default, baskets), `README.md`, `docs/OPERATIONS.md` Lane G → v1 OPERATOR GATE, one concept.

- [ ] Lint; commit `docs: helm v1 — acceptance, runbook, board (test: lint)`.

## Self-review (orchestrator)

Coverage vs spec rev 2: backend + validation + lock + tiles (T1), switch script + launcher (T2), module + polkit + assertions incl. agent-unit guard (T3), VM proof incl. negatives and polkit denials (T4), core wiring (T5), acceptance (T6). The residual risk statement and the v0 hand-over (helm group kept, static-web-server off) are in T3. Type consistency: config key `control` shape identical in T1 tests, T1 code and T3; unit names `helm-switch@<name>.service` identical across T1, T2, T3, T4.
