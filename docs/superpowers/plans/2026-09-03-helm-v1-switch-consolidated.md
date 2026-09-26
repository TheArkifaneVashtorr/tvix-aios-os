# Helm v1 — "the switch" — Consolidated Technical Plan

*Author: DeepSeek V4 Pro (technical consolidator). This is the final
technical consolidation across the architecture (DeepSeek), product/UX
(Kimi), and feasibility (GLM) passes. It amends — does not replace — the
six-task plan at `docs/superpowers/plans/2026-09-03-helm-v1-switch.md`;
where the two disagree, this document wins. Objective tests (rule 1) were
re-run against the live tree and the host pin and are cited inline. Copy,
visual direction, and page layout stay with Kimi; workflow sequencing stays
with GLM; the decisions below are the technical layer they all consume.*

**Spec:** `docs/superpowers/specs/2026-09-02-helm-v1-switch-design.md` (rev 2).
**Plan (six tasks):** `docs/superpowers/plans/2026-09-03-helm-v1-switch.md`.
**Research:** `docs/research-2026-09-02-helm-v1-switch.md`.

---

## 0. What the objective tests settled (rule 1, re-verified this session)

1. **Specialisations do not nest.** `nix eval
   .#nixosConfigurations.core.config.specialisation.gaming.configuration.specialisation
   --apply builtins.attrNames` → `[ ]`, while base's `config.specialisation`
   → `[ "gaming" ]`. GLM's blocker B1 is **confirmed**. Any module logic
   derived from `config.specialisation` yields different values in the base
   eval versus inside a specialisation's own eval.
2. **`switch-to-configuration` at the host pin is the Rust rewrite, not the
   Perl script.** `system.switch.enableNg` defaults true at `nixpkgs-host
   ac62194c`; the binary is `switch-to-configuration-ng`
   (`pkgs/by-name/sw/switch-to-configuration-ng`, built as
   `switch-to-configuration-0.1.0`). It populates user managers and
   reloads/restarts changed **user** units after system units. The spec's and
   research's "`switch-to-configuration` manages system units only" and every
   `switch-to-configuration.pl:<line>` citation are **wrong at this pin**.
   GLM's M3 is **confirmed**. The *observable* contract (`test` = activate
   without touching the bootloader or boot default) still holds and is gated
   by VM test + acceptance, not by source line numbers.
3. **`tests/unit/70-dsh-openrouter.bats` already exists.** The plan's
   `70-helm-switch.bats` / `71-helm-open-workspace.bats` collides. Use
   `80-` / `81-`.
4. **Core already carries a live `gaming` specialisation with the marker**
   (`hosts/core/default.nix:37-41`), guarded by `checks.core-gaming-wiring`.
   `media` does **not** exist yet (round 2). Cowork is **parked off**
   (`hosts/core/default.nix:102`). Acceptance must be scoped accordingly
   (decision D6).
5. **`hosts/core/firefox.nix` is policy-based and explicitly exempts loopback
   from HTTPS-upgrade** (`dom.security.https_only_mode.upgrade_local=false`).
   It strips no Fetch-Metadata/Origin headers. Firefox will send
   `Sec-Fetch-Site: same-origin` (and an `Origin`) on a same-origin form
   POST; this is still re-proven from the real browser in acceptance
   (decision D5), not assumed.

---

## 1. Consolidated architecture (system shape)

The shape is unchanged from the architecture pass and is correct. The single
most consequential fact remains: `helm-serve` is a **user** unit deliberately
straddling two trust domains — it must reach the operator's Wayland/D-Bus
session (to spawn a terminal) *and* call the system bus as the operator (so
polkit's `subject.user` matches). One change hardens that shape (§2/B2).

```
"no code, no password, loopback-only, JS-free"   (operator's Firefox)
          │  http://127.0.0.1:7700
          ▼
┌────────────────────────────── USER SCOPE (operator UID) ────────────────────────┐
│  helm-serve.service — Python stdlib, ThreadingHTTPServer, full sandbox          │
│    GET /            render v0 page + inject control section + tiles             │
│    GET /status.json marker + journal-derived switch state                       │
│    POST /action/switch  → systemctl start helm-switch@<name>.service (blocking) │
│    POST /action/open    → systemd-run --user … kgx -e "helm-open-workspace <n>" │
└───────┬───────────────────────────────────┬─────────────────────────────────────┘
        │ systemctl (system bus, as operator)│ systemd-run --user (user manager)
        ▼                                    ▼  → terminal OUTSIDE the sandbox
   polkit (duktape, ES5, verb-scoped)        helm-open-workspace.sh (generated)
        │ grants YES only: verb=="start",       → cd + nix develop → claude
        │ subject.user==operator, enumer.       → /run/baskets/<id> mount gate
        ▼
┌────────────────────────── SYSTEM SCOPE (root) ──────────────────────────────────┐
│  helm-switch@<name>.service — oneshot, 5min, ProtectHome/PrivateTmp, empty env │
│     ExecStart = helm-switch <name>  (allowlist + regex baked in, stable)        │
│        → $ROOT/{,specialisation/<name>/}bin/switch-to-configuration test         │
└──────────────────────────────────────────────────────────────────────────────────┘
```

The **allowlist (`control.profiles`) is now an explicit, closed, literal in
the host config** — identical in every toplevel — so the switch script, the
polkit rule, and the config.json `control` section are byte-identical in the
base and inside every specialisation. This is the single correction that
resolves both B1 and M4 (decision D1).

---

## 2. Key technical decisions

### D1 — Explicit, stable profile allowlist (resolves B1 *and* M4)

**The plan's default `control.profiles = [ "base" ] ++ attrNames
config.specialisation` is wrong** and must not ship. Because specialisations
don't nest (fact #1), that default yields `["base","gaming",…]` at base eval
but `["base"]` inside every specialisation eval. Consequences, all real:

- `@PROFILES@` in the switch script differs base-vs-specialisation → the
  `helm-switch@.service` `ExecStart` text differs → the agent-unit guard
  (prefix `helm-`) self-trips on its own unit. **B1.**
- Inside the `gaming` toplevel the polkit rule allows only
  `helm-switch@base.service`, and config.json lists only `base` → from
  `gaming` the page cannot reach `media` without passing through `base`. **M4.**

**Decision:**

1. `services.helm.control.profiles` defaults to `[ "base" ]` (a fixed
   literal) and the host sets it explicitly and completely —
   `hosts/core/helm.nix` lists `[ "base" "gaming" ]` now, and round 2 appends
   `"media"`. No derivation from `config.specialisation` anywhere.
2. Because `specialisation.<name>.configuration` extends the *parent's*
   module set, the host's literal `control.profiles` inherits identically
   into every specialisation. Therefore `@PROFILES@`, the polkit
   enumeration, and config.json `control.profiles` are byte-identical in
   every toplevel. **B1 self-trip gone; M4 narrowing gone.**
3. Enforcement of "no impossible profile" (G1) and "no omitted
   specialisation" (G2) is split by *where it can be evaluated safely*:
   - **Module `assertions`** (run in every toplevel, must be
     specialisation-agnostic — anything that reads `config.specialisation`
     is NOT safe here): `control.enable → services.helm.enable`;
     `"base" ∈ control.profiles`; every profile and workspace name matches
     `^[a-z][a-z0-9-]{0,31}$`; workspace `path` is absolute; the marker is
     set and regex-valid. (The existing loopback-`listen` assertion is
     unchanged.)
   - **`flake.nix` checks, base-eval only** (safe to read
     `config.specialisation`): G1/G2 equality
     `control.profiles \ { "base" } == attrNames config.specialisation`,
     plus its negative (`profiles = ["base" "nope"]` refuses).

**Hard safety is retained even before any check runs:** the switch script
re-validates `%i` against the baked `@PROFILES@` and against membership in
the generated unit set; a name pointing at no `specialisation/<name>/bin/
switch-to-configuration` fails closed at the script's root-selection step
(no arbitrary root exec). G1/G2 are correctness hygiene; the fail-closed path
is the security boundary and is tested by bats (Task 2) + the VM (Task 4).

### D2 — Agent-unit guard: presence/value-aware, system **and** user scope (resolves B1, M3, §4.5)

The "profiles never touch agent units" guard is the reason Helm dares to run
a root unit off an unauthenticated loopback POST. It must actually fire.

**Decision (semantics):** for each specialisation `s` (with profile name
`p == s`), classify every unit in the name-universe
`attrNames (base.units // s.units)`:

- `changed` — present in both, differing text (or one side attrset-defined
  with no `.text`: treat "present-but-attrset" ≠ "present-with-text" as a
  real difference; see the null trap below) →
  **forbidden if name matches the agent prefix, regardless of suffix.**
- `removed` — present in base, absent in specialisation →
  **forbidden if name matches the agent prefix.** A specialisation removing
  an agent unit is "touching" it.
- `new` — absent in base, present in specialisation →
  **allowed only if it ends in `-<p>.service` or `-<p>.timer`** (the
  profile-scoped new-unit exemption, anchored to the exact profile name).

Agent prefix: `^(egress-|cowork|basket|restic-backups-|helm-)`.

**Scope:** apply the same classification to `systemd.units` **and**
`systemd.user.units` (fact #2 means user units are reloaded/restarted by the
Rust switch just as system units are). `helm-collect`, `helm-flake-check`,
`helm-serve`, and `proton-drive-push` are all user units today. This closes
the gap the spec's "system units only" claim left open, while remaining a
no-op in practice because those user units' text is byte-identical across
base and specialisation.

**Placement:** `systemd.units` scope lives as a module `assertion` (it must
fire at every `nixos-rebuild`, protecting the live system; it is child-safe
because in a specialisation's own eval `config.specialisation == {}` and the
guard iterates zero specialisations — vacuously true). The `systemd.user`
scope lives in the same assertion.

**The null-collapse trap (§4.5, GLM-confirmed):** the plan's
`(a.text or null) != (b.text or null)` silently treats "absent" and
"present-but-attrset-defined" as the same (`null == null`), so an attrset-only
unit change is missed. The guard must compare **presence first**
(`lib.hasAttr`), then compare `.text` only within "both present". No `or
null` collapsing. This is the one correctness subtlety a reviewer must be
able to reject on; Task 3 writes it red-first with an attrset-defined unit in
the negative fixture.

### D3 — helm-serve sandbox vs the terminal it spawns (resolves B2)

GLM is right: v0's hardening set (`ProtectSystem=strict`,
`ProtectHome=read-only`, `NoNewPrivileges`, `PrivateTmp`) is inherited by
every child, so a `Popen(["kgx",…])` from inside `helm-serve` would open a
terminal that cannot write `~/.claude`, `~/.cache`, or the flake dir — and no
existing test touches `/action/open`.

**Decision:**

1. **The terminal escapes the sandbox, not the other way around.** `spawn_open`
   launches via `systemd-run --user` (a transient **user** unit — not
   `--scope`, which would tie it to the server's lifetime), forwarding
   `WAYLAND_DISPLAY`, `DISPLAY`, and `DBUS_SESSION_BUS_ADDRESS` explicitly.
   The terminal then runs in the user manager, outside `helm-serve`'s mount
   namespace, fully writable, detached from the server. The research's own
   verify suggestion (`systemd-run --user … kgx`) is the same mechanism.
2. **`helm-serve` keeps the full v0 hardening** — it needs no writes beyond
   `%t/helm/{token,switch.lock}` (`XDG_RUNTIME_DIR`), and it only *reads*
   `/etc/helm/{config.json,profile}` and `/var/lib/helm/*`. Its target
   surface is "answer loopback + call systemctl / systemd-run", not files.
3. **`kgx -e` takes one command string, not command+args.** The plan's
   `["kgx","-e","helm-open-workspace","gaming"]` is three argv elements
   where GNOME Console's `-e/--command` consumes one. Correct form:
   `kgx -e "helm-open-workspace gaming"` (a single shell string).
   **Verify-first (operator):** `kgx --help` on core to pin the exact argv
   (`--command` vs `-e`, whether `--wait` is wanted); probing `--help` has a
   GUI side effect, so this is operator-run, and Task 1's spawn test pins
   whatever argv the probe returns.
4. Two config additions (mirroring the existing `nixos_version_bin` /
   `nvidia_smi_bin` absolute-path pattern, since a `--user` unit's PATH lacks
   `/run/current-system/sw/bin`): `kgx_bin = "/run/current-system/sw/bin/kgx"`
   and `helm_open_workspace_bin = "/run/current-system/sw/bin/helm-open-workspace"`.
   `spawn_open` uses the absolute paths; the launcher inside the terminal
   then runs in the operator's interactive session with a full PATH.

### D4 — The `test` action is proven by observable outcome, not source lines

The deployed artifact is the Rust `switch-to-configuration-ng` (fact #2), so
the research digest's `switch-to-configuration.pl:<line>` citations do not
exist at runtime. We do not lean on them. The acceptance gate (and VM test)
assert **observable outcomes** only:

- bootloader/boot-default untouched across switches (booted system identity
  and `/nix/var/nix/profiles/system` default unchanged);
- only changed units restarted; no agent-prefixed unit restarted (the
  guard's observable consequence);
- marker flipped; `/run/current-system` repointed (secondary, VM-only).

Root selection remains: `$ROOT = /nix/var/nix/profiles/system` when
`$ROOT/bin/switch-to-configuration` exists, else `/run/booted-system`
(stage-2, the VM path). This indirection is what makes "back to base"
correct from inside any specialisation.

### D5 — Firefox Fetch-Metadata: the acceptance gate runs it from the real browser (Kimi flag #2)

`hosts/core/firefox.nix` (fact #5) is policy-locked and strips nothing, so
Firefox will send `Sec-Fetch-Site: same-origin` and an `Origin` on a
same-origin form POST. The spec's rejection rule (accept `same-origin`; else
accept an allowed `Origin`; reject a POST with neither) is therefore expected
to hold. **But the failure mode is silent and total** (every button 403s), so
it is not assumed: Task 6's acceptance must click-equivalent from Firefox
itself (real form submit), and if the observed headers contradict the spec,
the fallback order is re-derived from the observation (rule 1). The Origin
fallback already covers "Sec-Fetch-Site absent"; the only brick scenario is
"both absent", which requires a header-stripping profile that core does not
ship. VM test #10 keeps the "neither header → 403" negative regardless.

### D6 — Acceptance re-scope: cowork→restic, media conditional, SKIP≠FAIL (M6)

- **Cowork broker audit step is replaced.** Cowork is parked off on core
  (`hosts/core/default.nix:102`), so "the cowork broker audit shows no
  restart" cannot run. Replace it with the *real* armed agent unit:
  `restic-backups-core-local` (`systemctl show -p NRestarts` / journal) must
  show **no restart across the three switches**, and no `egress-|cowork|
  basket|restic-backups-|helm-` unit restarts. This keeps the guard's
  observable consequence testable today.
- **`media` steps are conditional on round 2** having wired
  `specialisation.media`. The acceptance script emits **`SKIP`** (a distinct,
  logged outcome — not `PASS`, not `FAIL`) for media and for the cowork step
  when their preconditions are absent, so the operator gate is never judged
  against steps that cannot run.
- The four workspaces in Task 5 remain (nixos-agent-env, gaming, media,
  strategy); the `media` and `gaming` flake dirs are the operator's existing
  paths and the acceptance opening step is scoped to whichever flake dirs
  actually exist at gate time.

### D7 — Live-host transition is a runbook item, not a test gap (M5)

Confirmed by fact #2's corollary: a NixOS switch does **not** start a newly
enabled *user* unit in an already-logged-in session. On core's first
`nixos-rebuild switch` that enables `services.helm.control`, `helm-serve`
will NOT auto-start, and `static-web-server.socket` goes away in the same
switch — a page outage until the server is started. The Task 6 runbook must
state, verbatim:

1. `systemctl --user start helm-serve.service` (or log out and back in) after
   the enabling switch;
2. the `:7700` page is briefly down between `static-web-server` stopping and
   `helm-serve` starting.

The VM (Task 4) does not hit M5 because its testScript starts `helm-serve`
explicitly; only the live host does.

### D8 — Lock, timeout asymmetry, and the journal state machine (confirm §4.4)

- `flock(LOCK_EX|LOCK_NB)` on `%t/helm/switch.lock`, held for the whole
  `run_switch`; busy → `409` (a fully-rendered page — Kimi's call, already
  agreed). Context manager self-releases on crash (crash ⇒ unlock, never
  deadlock).
- **360 s client timeout > 300 s `TimeoutStartSec`**, deliberately
  asymmetric: a slow-but-legitimate switch must not return an HTTP error
  while the unit is still running. The audit line records both the HTTP
  result and the eventual unit result so a timeout is observably distinct
  from a denial.
- **No sidecar state file.** The in-flight state is the journal
  `helm-switch: begin`/`end` pair, so a server restart mid-switch does not
  forget the switch. `status.json` derives ok/switching/fail from those pairs
  + the marker.

### D9 — Accepted-host set is built from the *parsed* address (confirm §4.7)

`accepted_hosts` = `{alias:port for alias in hostAliases} ∪ {bound}`, built
from the **parsed** `listen` (`[::1]` bracketed form preserved), and
`accepted_origins` = `http://` + each, preserving brackets. One pytest case
with an IPv6 bound/alias closes this otherwise-silent IPv6 failure.

### D10 — Config/interface contract corrections

- `control.profiles`, `workspaces`, `host_aliases`, `listen`, `marker`
  (path `/etc/helm/profile`), `kgx_bin`, `helm_open_workspace_bin` are the
  `control` section. **`active_profile` is NOT config** — the active profile
  is the marker read from disk at render time, never cached from config.json.
  `load_config` runs once at startup (static); marker + journal are re-read
  per request. (The plan's `"active_profile": "base"` test fixture is wrong.)
- `validate_post(headers, form, token, allow, key)` stays the pure, I/O-free
  security decision point (§2.1 of the architecture pass) — that purity is
  what makes the CSRF/rebinding surface a unit-test table.
- GET routes check Host too (no token on GET): the page is readable by any
  local process; the residual-risk wording (§ "D11/e") says that plainly.

### D11 — Residual risks (statement, not fix)

1. **Same-UID bypass is real and accepted.** Any process running as the
   operator reads the token or calls `systemctl start helm-switch@…` directly
   and passes polkit by identity. The *real* boundary is the root unit's
   allowlist + polkit verb/user/unit triple, not anything the server does.
   This stays in the runbook; the token is not claimed as privilege
   separation.
2. **GET `/` is token-free**: any local process can read the page and thus
   the embedded token. Blast radius of a leak = "allowlisted profile switches
   only, agent units protected by the assertion" — not "the operator's
   processes".
3. **`test`-vs-`switch` is settled by VM + acceptance, not by citation**
   (D4). The built artifact is a binary; the digest's `.pl` line numbers are
   not greppable in it.
4. **`kgx -e` argv and the live `systemd-run --user` window are operator-run
   verify-first items** — build-only roles cannot probe them without GUI side
   effects.

---

## 3. Cross-role flags, resolved

| Flag | Owner | Resolution (technical side) |
|---|---|---|
| Disable the active-profile button (render-time) | Kimi → GLM concurrence | Backend allowlist stays **complete** (a self-switch POST remains accepted; it's an idempotent re-`test` of the current config). Disabling is pure render layer (Kimi) and does not change the POST surface; VM round-trip `base↔alt` is unaffected. **DeepSeek agrees with render-disable + complete-allowlist.** |
| Firefox `Sec-Fetch-Site` on loopback form POST | Kimi → DeepSeek | D5: expectation holds (firefox.nix strips nothing); proven from the real browser in acceptance; fallback re-derived if observation contradicts the spec. |
| "no self-switch button" is cross-domain | 2-of-3 | The button is a render concern; the allowlist stays complete; no backend change. Agreed (DeepSeek). |
| B1 assertion semantics | DeepSeek + GLM | D1: explicit stable allowlist; G1/G2 in flake.nix checks, G3 (agent-unit guard) in module assertions. |
| B2 spawn/sandbox mechanism | GLM + DeepSeek (+ operator kgx probe) | D3: `systemd-run --user` escape + full server hardening; operator pins `kgx` argv. |
| M3 user-unit guard scope | DeepSeek | D2: extend guard to `systemd.user.units`; correct the spec's false "system units only" claim. |
| M4 in-specialisation behaviour | DeepSeek + GLM | D1: allowlist/polkit/config identical in every toplevel; add a check that base and `gaming` polkit/allowlist are **equal**. |
| M6 acceptance scoping | operator + GLM | D6: cowork→restic, media conditional, SKIP≠FAIL. |

---

## 4. Task-impact map (what changes in the existing six-task plan)

| Task | Unchanged | **Consolidated changes to fold in** |
|---|---|---|
| **T1 helm-serve** | serve.py, pytest matrix, `helm-unit` check, pure `validate_post` | D3 spawn: `systemd-run --user` + absolute `kgx_bin`/`helm_open_workspace_bin`; `kgx -e "<cmd> <name>"` single-string argv (pin to operator's `kgx --help`); D10 config contract (no `active_profile` in config; `kgx_bin`/`helm_open_workspace_bin`/`marker` keys); D8 360s>300s; D9 Guard:: IPv6 test. |
| **T2 scripts** | bats discipline, `$ROOT` + fallback, audit lines, launcher exec | bats `80-helm-switch.bats` / `81-helm-open-workspace.bats` (**80/81, not 70/71**); add `removed`-unit and attrset-null fixtures are T3's job, but the switch script's `@PROFILES@` default is now explicit (D1) — no change to the script's own gate logic. |
| **T3 module** | options, polkit rule shape, assertions, 5 checks | **D1** (explicit profiles, split assertions vs checks, polkit eq base-vs-specialisation check), **D2** (presence-aware + user-scope guard), **D3** (helm-serve hardening + `systemd-run` spawn; no write-blocks cascading), **D4** (root selection unchanged). |
| **T4 VM test** | real `test`-action switch, negative matrix, polkit denials | set `control.profiles = ["base" "alt"]` explicitly; add assertion that the `alt` toplevel's polkit/allowlist/`helm-switch@` text equals base's (B1/M4 regression guard); assert **no agent/user unit restarts** across the switch (D4 observable). |
| **T5 core wiring** | `hosts/core/helm.nix` four workspaces + `host-core` | add explicit `control.profiles = ["base" "gaming"]`; closure diff now expects **stable** `helm-switch@` across base/gaming. |
| **T6 docs/acceptance** | runbook, board, concept | D5 (real-Firefox form submit), D6 (cowork→restic, media conditional, SKIP≠FAIL), D7 (manual `helm-serve` start + outage window verbatim), D11 residual risks. |

---

## 5. Acceptance tests — final, load-bearing list

The happy paths are table stakes; the load-bearing tests are the ones that
prove a claim that was contested. Each names the invariant it closes.

| # | Test | Invariant |
|---|---|---|
| 1 | `validate_post` matrix (`pytest tests/helm`) | Wrong Host / `cross-site` / foreign Origin / missing-Origin-no-Fetch-Metadata / wrong-token / unknown+`../` target → 403; happy + IP-alias + IPv6-alias → (0,""). The whole CSRF/rebinding surface as a table. |
| 2 | `test_lock_gives_409` | Held flock ⇒ second switch 409; release works; context manager self-releases. |
| 3 | `test_switch_calls_systemctl_exactly` | argv `["systemctl","start","helm-switch@gaming.service"]`, no shell, correct instance. |
| 4 | `test_spawn_open_via_systemd_run` | argv is `["systemd-run","--user",…,"kgx","-e","helm-open-workspace gaming"]`-shaped (no shell interpolation, absolute `kgx_bin`), detach semantics. |
| 5 | `test_render_control_forms_and_no_script` | one form per profile + workspace; token embedded; **no `<script`, no `src=`, no `href="http`**. |
| 6 | end-to-end over a live `Handler` (thread + `http.client`) | 403/409/200 wiring; fake `run_switch` called exactly once — the *handler* enforces gates, not only the pure function. |
| 7 | `80-helm-switch.bats` | rejects `../x` / `gaming;reboot` / unlisted name with exit 2 and stubbed binaries untouched; `$ROOT` preference + fallback; `base` vs named both end in ` test`; `begin`/`end` lines. |
| 8 | `81-helm-open-workspace.bats` | unknown name → exit 2; devShell-null vs default argv; basket-wait prompt on unmounted basket (Enter fed); `exec` replaces the shell. |
| 9 | `helm-control-eval` | rendered polkit = exactly the enumerated unit names + verb guard + operator user; **base polkit text == `gaming`-specialisation polkit text** (B1/M4 regression guard); `helm-switch@` exists; static-web-server off; config.json has the `control` section; completeness G2 holds. |
| 10 | `helm-control-assertion-negative-{profiles,enable,agentunit,workspace}` | profiles=`["base","nope"]` fails (G1); `control.enable` without `services.helm.enable` fails; a specialisation changing an agent unit fails **for the right reason** (the agent-unit guard, not the `helm-switch@` self-trip — this one proves B1 is actually resolved, not masked); bad workspace name fails. |
| 11 | `helm-control-vm` | Real `test`-action switch: POST → marker `alt` + `/run/current-system` relink → back to `base`; full negative matrix over curl (foreign Origin, wrong Host, no token, unknown profile, missing Origin) → 403 with marker **unchanged each**; `systemctl start helm-switch@nope` / `kill` / `set-property` as alice → polkit denies (verb/user/unit scoping live); **no `egress-|cowork|basket|restic-backups-|helm-` unit restarted** across the switch (system *or* user scope); `journalctl -u 'helm-switch@*'` shows `begin`/`end`; page has no `<script` and the `alt` toplevel allowlist == base's. **Objective proof that overrides every model's claim about `test` semantics.** |
| 12 | `host-core` + closure diff | Core toplevel gains {polkit rule, `helm-switch@`, `helm-serve`, `helm-open-workspace`}; static-web-server gone; `helm-switch@` text identical across base and `gaming`. |
| 13 | `tests/acceptance/helm-v1.sh` (operator gate) | Click `gaming` → Steam in app grid within a minute + marker `gaming` + drift still green; click `base` → gone; **boot default unchanged across the switches**; **`restic-backups-core-local` `NRestarts == 0`** across the switches (D6, replaces the parked cowork broker); open `gaming` workspace → Console window running `claude` in the flake; `media` + cowork are explicit **SKIP** until round 2 / re-enable. Real Firefox form submit (D5). |

---

## 6. Sequencing (GLM's, endorsed)

Freeze **before** T3 launches: D1 (assertion semantics), D2 (guard scope),
D3 (`kgx` argv via the one operator probe + `systemd-run` mechanism),
D6 (acceptance scope), and the D10 config contract. Then
**T1 ∥ T2 → T3 → T4 ∥ T5 → T6**, with T3 as the critical path and T4 as the
long wall-clock pole. Serialize against wiring round 2 (both touch flake.nix
/ `hosts/core`); if Helm v1 lands first, T6's media steps stay conditional
(D6).