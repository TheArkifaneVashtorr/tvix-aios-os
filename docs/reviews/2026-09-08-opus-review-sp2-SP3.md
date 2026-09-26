---
plan_defect: none
mutants_total: 25
mutants_killed: 25
mutants_outside_named: 5
model: opus
---
# Opus gate — seat run sp2, task SP3 — APPROVED

## Summary

Reviewed in a fresh clone of `task/SP3` at `c8c37ec`, base `e4258e0` (main).
Six files, one commit, subject byte-identical to the section's, both trailers
present, the plan file and the board untouched. Every numbered item of the
section's Interfaces is met literally; the two reds the commit body pastes were
reproduced verbatim; all four acceptance checks are green under `--rebuild`.
25 mutants applied, 25 killed — but one of them, the section's named mutant
**(G) `DynamicUser` not forced**, is *not* killed by the check the Tests table
names (`telemetry-vm` row 4 passes with `DynamicUser = true`); it is killed by
`telemetry-eval`, which is also the section's acceptance. Row 4's assertion is
itself load-bearing (`User = "root"` turns it red — measured). That is a plan
Tests-table erratum, recorded as MINOR-1, not a surviving mutant.

**Privacy (brief §3, the invariant here): held.** The allowlist is applied at
`resource` **and** `datapoint` for metrics and at `resource` **and** `log` for
logs — proven twice: in the rendered `config.yaml` of the built system, and by
mutant (A) (`datapoint` → `resource`), which turns `telemetry-vm` red with
`grep -q -F 'user.email' … unexpectedly succeeded`. `user.email`,
`user.id`, `user.account_uuid`, `organization.id` and the unlisted `user.name`
planted on the resource, on a `claude_code.token.usage` data point and on an
`api_request` log record reach neither file; the `user_prompt` record and its
`SECRET PROMPT CONTENT` body are dropped by `filter/events`.

**Switch #23 — the surface prediction holds, with one extra line and one
predicted line absent for a stated reason.** Measured from this branch
(`nix build .#nixosConfigurations.core.config.system.build.toplevel` then
`nix store diff-closures /run/current-system ./result`):

```
claude-code-telemetry-settings.json: ∅ → ε
config.yaml: ∅ → ε
otelcol-contrib: ∅ → 0.151.0, 360.1 MiB
unit-opentelemetry-collector.service: ∅ → ε
```

- `otelcol-contrib: ∅ → 0.151.0` and `unit-opentelemetry-collector.service:
  ∅ → ε` — exactly as §Operator step 2 predicts. The closure grows **360.1
  MiB**; the plan does not state that figure, so state it here.
- `claude-code-telemetry-settings.json: ∅ → ε` is the predicted "`etc` gaining
  `claude-code/managed-settings.json`": `etc` itself is name-identical between
  the two closures, so `diff-closures` prints no `etc` line; the file's content
  in the built toplevel was read directly and is the eight variables under one
  `env` key (pasted under ## Contract items).
- `config.yaml: ∅ → ε` is the **one measured line outside the prediction** —
  the collector's own generated settings file, SP3's declared output, not a
  new package.
- The predicted "two broker units rebuilt" prints no `diff-closures` line for
  the same name-identity reason, but it *is* real and was verified directly:
  `egress-broker-openrouter.service` `ExecStart … -s /nix/store/f5azl4d1…-policy.py`
  (live) → `-s /nix/store/4jy9nhh…-policy.py` (branch). SP1's addon does reach
  the live broker at this switch.
- The predicted `evidence: … KiB → …` line does **not** appear: neither SP1
  (the broker) nor SP3 touches `pkgs/evidence`. It will appear only if SP2 or
  SP8 land before the switch.

§Operator step 3's acceptance lines will hold: the rendered unit carries
`User=dalhaka`, `ProtectHome=true`, `IPAddressDeny=any` (pasted below), and the
VM proves `ss -ltnH` shows `127.0.0.1:4318` and nothing on `0.0.0.0` or `:4317`.

## Contract items

Section `### SP3 (code, M)`, taken literally.

1. **Files — create `nixosModules/claudeTelemetry.nix`, `hosts/core/telemetry.nix`,
   `tests/integration/telemetry-vm.nix`; modify `hosts/core/default.nix`,
   `flake.nix`; then `repomap.py write`.** Met. `git diff --stat e4258e0..HEAD`
   is exactly those five plus `docs/MAP.md`.
2. **`./telemetry.nix` after `./seat.nix` in `imports`.** Met —
   `hosts/core/default.nix:14` `    ./telemetry.nix` directly after `./seat.nix`
   (line 13).
3. **`flake.nix` wiring.** Met — `flake.nix:698`
   `claudeTelemetry = import ./nixosModules/claudeTelemetry.nix;`; `flake.nix:731`
   `self.nixosModules.claudeTelemetry` in `nixosConfigurations.core.modules`;
   `checks.telemetry-eval` at `flake.nix:1847`; `flake.nix:1997`
   `telemetry-vm = import ./tests/integration/telemetry-vm.nix { inherit pkgs;
   claudeTelemetryModule = self.nixosModules.claudeTelemetry; evidenceStoreModule
   = self.nixosModules.evidenceStore; }` — the section's expression verbatim.
4. **Options `enable`, `port` (`types.port`, default `4318`), `user`
   (`types.str`, default `config.services.evidence-store.owner`), read-only
   `env` and `settingsFile`.** Met — `nixosModules/claudeTelemetry.nix:132-187`;
   `port` `lib.types.port` default `4318` (:135-137), `user` `lib.types.str`
   default `config.services.evidence-store.owner` (:145-147), `env`
   `readOnly = true` (:154-156), `settingsFile` `readOnly = true` with
   `(pkgs.formats.json { }).generate "claude-code-telemetry-settings.json"
   { inherit (cfg) env; }` (:175-180).
5. **`env` — exactly the eight names, no `OTEL_LOG_*`.** Met —
   `nixosModules/claudeTelemetry.nix:158-165`. The rendered
   `/etc/claude-code/managed-settings.json` in the built toplevel:

   ```json
   { "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
     "OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:4318",
     "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json", "OTEL_LOGS_EXPORTER": "otlp",
     "OTEL_LOGS_EXPORT_INTERVAL": "5000", "OTEL_METRICS_EXPORTER": "otlp",
     "OTEL_METRICS_INCLUDE_ACCOUNT_UUID": "false",
     "OTEL_METRIC_EXPORT_INTERVAL": "5000" } }
   ```

   One top-level key, eight variables, no `OTEL_LOG_*`.
6. **The D6 assertion under `mkIf cfg.enable`.** Met in substance —
   `nixosModules/claudeTelemetry.nix:190-195`, message byte-identical to the
   section's. The predicate is `!(config.services.claude-managed-settings.enable
   or false)` rather than the section's `!config.services.claude-managed-settings.enable`
   (MINOR-2). It is not decorative: flipping `hosts/core/default.nix:97`
   `enable = false;` → `true;` makes the toplevel refuse with
   `- services.claude-telemetry and services.claude-managed-settings both write
   /etc/claude-code/managed-settings.json; enable one` (outside-named mutant).
7. **`environment.etc."claude-code/managed-settings.json".source = cfg.settingsFile`.**
   Met — `nixosModules/claudeTelemetry.nix:197`.
8. **`services.opentelemetry-collector = { enable; package =
   pkgs.opentelemetry-collector-contrib; validateConfigFile = true; settings = … }`.**
   Met — `nixosModules/claudeTelemetry.nix:199-204`; `ExecStart=/nix/store/968kwjxv…-otelcol-contrib-0.151.0/bin/otelcol-contrib
   --config=file:/nix/store/c8bvbs48…-config.yaml` in the built unit.
9. **The `settings` block — receivers, `transform/allowlist` at the four
   contexts, `filter/events`, the two file exporters, `service.telemetry.metrics.level
   = "none"`, the two pipelines.** Met — `nixosModules/claudeTelemetry.nix:60-129`.
   The rendered `/nix/store/c8bvbs48…-config.yaml` matches the section line for
   line: `receivers.otlp.protocols.http.endpoint: 127.0.0.1:4318`;
   `transform/allowlist` `metric_statements` `[resource, datapoint]` and
   `log_statements` `[resource, log]`, each a single
   `keep_keys(attributes, [...])`; `filter/events.logs.log_record:
   ['attributes["event.name"] != "api_request" and attributes["event.name"] !=
   "api_error"]`; `file/metrics` → `/var/lib/opentelemetry-collector/claude-metrics.jsonl`
   and `file/logs` → `…/claude-logs.jsonl`, both `flush_interval: 1s`,
   `rotation: {max_backups: 8, max_megabytes: 64}`; `service.telemetry.metrics.level:
   none`; `pipelines.metrics.processors: [transform/allowlist]`,
   `pipelines.logs.processors: [transform/allowlist, filter/events]`.
10. **`keepResource` / `keepPoint` / `keepLog` exactly the section's lists,
    `prompt.id` not kept.** Met — `nixosModules/claudeTelemetry.nix:22-58`; the
    three rendered lists in `config.yaml` are the section's, in the section's
    order; no `prompt`-shaped key anywhere.
11. **`systemd.services.opentelemetry-collector.serviceConfig` — the eleven
    hardening lines, the module's `StateDirectory`, `WorkingDirectory`,
    `Restart`, `DevicePolicy` kept.** Met — `nixosModules/claudeTelemetry.nix:206-219`.
    The rendered unit:

    ```
    CapabilityBoundingSet=
    DevicePolicy=closed
    DynamicUser=false
    IPAddressAllow=localhost
    IPAddressDeny=any
    InaccessiblePaths=-/var/lib/evidence
    NoNewPrivileges=true
    PrivateTmp=true
    ProtectHome=true
    ProtectSystem=strict
    ReadWritePaths=/var/lib/opentelemetry-collector
    Restart=always
    RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
    StateDirectory=opentelemetry-collector
    User=dalhaka
    WorkingDirectory=%S/opentelemetry-collector
    ```

    No `SupplementaryGroups=` line (forced empty — the module's
    `systemd-journal` is gone), `DevicePolicy`/`Restart`/`StateDirectory`/
    `WorkingDirectory` kept.
12. **`hosts/core/telemetry.nix`: `_:` with a comment naming the plan and
    switch #23.** Met — `hosts/core/telemetry.nix:1-9` (`_:`, then
    "SP3 (plan 2026-09-08-spend-telemetry) … only reach the live broker here at
    switch #23", then `services.claude-telemetry.enable = true;`).
13. **`checks.telemetry-eval` — the `seat-eval` shape, ten assertions each with
    a `telemetry-eval: …` message.** Met — `flake.nix:1847-1996`; ten
    `assertMsg` chains, all ten messages prefixed `telemetry-eval:`, terminating
    in `builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand
    "telemetry-eval-ok" { } "touch $out")` (`flake.nix:1996`) — the same
    terminal as `seat-eval` (`flake.nix:1812`). Assertions 1–10 match the
    section's numbered list, including the independent re-render of the four
    `keep_keys` strings from the spec (`flake.nix:1857-1895`) so a module-side
    list edit fails the `==`.
14. **`tests/integration/telemetry-vm.nix` — the signature, the node, the probe,
    the testScript.** Met — signature `{ pkgs, claudeTelemetryModule,
    evidenceStoreModule }` (:1-5); node imports both modules,
    `services.claude-telemetry.enable = true`, `users.users.dalhaka =
    { isNormalUser = true; uid = 1000; }` (:135-146); the probe plants all five
    identity keys on the resource (:33-39), on the `claude_code.token.usage`
    data point with `type: cacheRead`, `model: claude-fable-5-1`,
    `session.id: sess-x`, `asDouble: 1234.0` (:54-88) and on the `api_request`
    record with `model`, `cost_usd`, `input_tokens "2"`, `request_id: req_x`,
    `session.id` (:93-100), plus the `user_prompt` record carrying
    `prompt: "SECRET PROMPT CONTENT"` (:115-123); the testScript (:152-167) is
    the section's sixteen lines verbatim. The one addition is
    `environment.systemPackages = [ pkgs.iproute2 ]` (:147-150) for `ss`
    (MINOR-3, benign).
15. **Steps 1–4.** Step 1's red and Step 3's red reproduced verbatim (## Red
    before green). Step 2's `nix build
    .#nixosConfigurations.core.config.system.build.toplevel` builds (exit 0).
    Step 4: `host-core` and `lint` green, `docs/MAP.md` regenerated and current,
    one commit whose body pastes both reds and names the two new checks.

## Red before green

**Step 1 — `telemetry-eval` before the host file is imported.** In a scratch
copy, `hosts/core/default.nix:14` (`./telemetry.nix`) deleted; the branch's
`flake.nix` check unchanged:

```
$ nix build .#checks.x86_64-linux.telemetry-eval -L --no-link --rebuild
       error: telemetry-eval: services.claude-telemetry must be enabled on core (hosts/core/telemetry.nix imported by hosts/core/default.nix)
EXIT=1
```

Restored → `telemetry-eval` green (`checking outputs of
'/nix/store/7qlaa54f…-telemetry-eval-ok.drv'…`, exit 0). This is byte-identical
to the red the commit body pastes.

**Step 3 — `telemetry-vm` with the transform contexts reduced to `resource`.**
In a scratch copy, the metrics `datapoint` context changed to `resource`:

```
$ nix build .#checks.x86_64-linux.telemetry-vm -L --no-link
vm-test-run-claude-telemetry-loopback-collector> !!! RequestedAssertionFailed: command `grep -q -F 'user.email' /var/lib/opentelemetry-collector/claude-metrics.jsonl /var/lib/opentelemetry-collector/claude-logs.jsonl` unexpectedly succeeded
EXIT=1
```

Restored → `telemetry-vm` green (test script finished in 10.52 s; every
`must fail:` on the five identity keys, `SECRET PROMPT` and `user_prompt`
finished in 0.01 s, the three `ss` assertions and the `systemctl show` assertion
passed). Byte-identical to the red the commit body pastes.

Neither test can pass vacuously: row 4's assertion, the one the (G) mutant fails
to exercise, is independently load-bearing — `User = cfg.user` → `User = "root"`
gives
`RequestedAssertionFailed: command \`systemctl show opentelemetry-collector -p User --value | grep -qx dalhaka\` failed (exit code 1)`.

## Mutants

25 applied, 25 killed. 20 named by the section's Tests table, 5 outside it.
Each was applied in a scratch copy of the clone, the check run, then reverted.

| # | mutant | named | killing check | failing line |
|---|---|---|---|---|
| 1 | (A) metrics `context = "datapoint"` → `"resource"` | row 1 | telemetry-vm | `command \`grep -q -F 'user.email' …\` unexpectedly succeeded` |
| 2 | (H) `user.email` prepended to `keepPoint` | rows 1, 6 | telemetry-vm | same line as #1 |
| 3 | (B) filter names prefixed `claude_code.` | row 2 | telemetry-vm | `action timed out after 900.24 seconds (timeout=900.0)` (every record dropped, `claude-logs.jsonl` never written — MINOR-4) |
| 4 | (D) `endpoint = "0.0.0.0:${port}"` | rows 3, 6 | telemetry-vm | `command \`ss -ltnH \| grep -q '127.0.0.1:4318'\` failed (exit code 1)` |
| 5 | a `grpc` receiver added on `:4317` | row 3 | telemetry-vm | `command \`ss -ltnH \| grep -q ':4317'\` unexpectedly succeeded` |
| 6 | (G) `DynamicUser = lib.mkForce false` removed | row 4 | **telemetry-eval** (not telemetry-vm — MINOR-1) | `error: telemetry-eval: the collector must run as the evidence-store owner, loopback-only, with /var/lib/evidence inaccessible` |
| 7 | (E) `./telemetry.nix` removed from `imports` | row 5 | telemetry-eval | `error: telemetry-eval: services.claude-telemetry must be enabled on core …` |
| 8 | `package = pkgs.opentelemetry-collector` (core) | row 6 | telemetry-eval | `error: telemetry-eval: the collector must be opentelemetry-collector-contrib with the config validated at build time` |
| 9 | `validateConfigFile = false` | row 6 | telemetry-eval | same message as #8 |
| 10 | the `datapoint` statement block removed | row 6 | telemetry-eval | `error: telemetry-eval: the transform allowlist must keep exactly the spec lists at resource/datapoint (metrics) and resource/log (logs) contexts` |
| 11 | the `api_error` arm dropped from the filter | row 6 | telemetry-eval | `error: telemetry-eval: filter/events must drop every log record except api_request and api_error` |
| 12 | `file/metrics.path` → `/var/lib/evidence/claude-metrics.jsonl` | row 6 | telemetry-eval | `error: telemetry-eval: both file exporters must write under the collector StateDirectory and the pipelines must name the two processors` |
| 13 | (C) `IPAddressDeny` removed | row 7 | telemetry-eval | `error: attribute 'IPAddressDeny' missing … flake.nix:1971` (red, but not the check's own message — MINOR-5) |
| 14 | (J) `ProtectHome = false` | row 7 | telemetry-eval | `error: telemetry-eval: the collector must run as the evidence-store owner, loopback-only, with /var/lib/evidence inaccessible` |
| 15 | `InaccessiblePaths = [ ]` | row 7 | telemetry-eval | same message as #14 |
| 16 | `SupplementaryGroups = lib.mkForce [ ]` removed | row 7 | telemetry-eval | same message as #14 |
| 17 | (F) `OTEL_LOG_USER_PROMPTS = "1"` added to `env` | row 7 | telemetry-eval | `error: telemetry-eval: the managed-settings env must be exactly the eight exporter variables, none an OTEL_LOG_*` |
| 18 | `OTEL_METRICS_EXPORTER = "console"` | row 7 | telemetry-eval | same message as #17 |
| 19 | the etc source retargeted (`.text = "{}"`) | row 7 | telemetry-eval | `error: telemetry-eval: /etc/claude-code/managed-settings.json must be claude-telemetry's settingsFile and claude-managed-settings must be disabled` |
| 20 | the D6 assertion block removed | row 7 | telemetry-eval | red inside assertion 10's condition (`flake.nix:1993`), surfacing as `error: attribute 'cycle' missing` from nixpkgs `filesystems.nix:452` — MINOR-6 |
| 21 | `hosts/core/default.nix:97` `claude-managed-settings.enable = true` | outside | host toplevel eval | `- services.claude-telemetry and services.claude-managed-settings both write /etc/claude-code/managed-settings.json; enable one` |
| 22 | `pipelines.logs.processors = [ "transform/allowlist" ]` (filter dropped) | outside | telemetry-eval | `error: telemetry-eval: both file exporters must write under the collector StateDirectory and the pipelines must name the two processors` |
| 23 | `user.email` prepended to `keepLog` | outside | telemetry-eval | `error: telemetry-eval: the transform allowlist must keep exactly the spec lists …` |
| 24 | `filter/events.error_mode = "ignore"` | outside | telemetry-eval | `error: telemetry-eval: filter/events must drop every log record except api_request and api_error` |
| 25 | `User = "root"` | outside | telemetry-vm | `command \`systemctl show opentelemetry-collector -p User --value \| grep -qx dalhaka\` failed (exit code 1)` |

On #6, the evidence that the mutant really takes effect and the VM still passes:
`nix eval .#nixosConfigurations.core.config.systemd.services.opentelemetry-collector.serviceConfig.DynamicUser`
→ `true`, and `nix build .#checks.x86_64-linux.telemetry-vm` → `EXIT=0`.

## Checks

Run in the fresh clone at `c8c37ec` (`XDG_CACHE_HOME` under the session
scratchpad; every tool through `nix develop -c`).

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.telemetry-eval -L --no-link --rebuild` | pass (exit 0) |
| `nix build .#checks.x86_64-linux.telemetry-vm -L --no-link --rebuild` | pass (exit 0; test script 10.52 s) |
| `nix build .#checks.x86_64-linux.host-core -L --no-link --rebuild` | pass (exit 0) |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | pass (exit 0) |
| `nix build .#nixosConfigurations.core.config.system.build.toplevel` | pass (exit 0) |
| `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | clean (exit 0) |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent (exit 0) |
| `nix develop -c githooks/pre-commit` | exit 1 — **only** `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` (MINOR-7) |

`ruff check` / `ruff format --check` are not applicable: the diff contains no
`.py` file (the VM probe is a `pkgs.writeText` inside `tests/integration/telemetry-vm.nix`,
which `lint`'s treefmt/statix/deadnix arms cover and which is green).

On the pre-commit line: it is not caused by this change. A clean clone checked
out at the base `e4258e0` runs the same hook to exit 0; on the task branch the
queue derived from the tree no longer lists SP3 (the task's own commit marks it
done), so HEAD's board block is stale by construction. The gate forbids a board
commit and the section's `touches` does not include `docs/OPERATIONS.md`; the
integrator regenerates the block. Every treefmt / shellcheck / statix / deadnix
/ ruff / eslint arm of the hook is green.

## Touches and commit

`git diff --name-only e4258e0..HEAD`:

```
docs/MAP.md
flake.nix
hosts/core/default.nix
hosts/core/telemetry.nix
nixosModules/claudeTelemetry.nix
tests/integration/telemetry-vm.nix
```

Every file is inside the section's `touches` (`docs/MAP.md` by the Global
Constraints' exemption, and it is exactly what `repomap.py write` regenerates).
No file outside; no `Deviation:` line needed and none present.

Exactly one commit (`git rev-list --count e4258e0..HEAD` → 1). Subject
byte-identical to the section's `commit subject` (`cmp` against the section's
string → identical). Body states the why, pastes the eval red and the VM red
(both reproduced above) and names the two new checks. The two trailers follow a
blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sp2)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

— the same pair the previous seat landings use. No board commit; the plan file
`docs/superpowers/plans/2026-09-08-spend-telemetry.md` is untouched.

## Findings

**MINOR-1 — the section's named mutant (G) is killed by `telemetry-eval`, not by
the `telemetry-vm` row that names it.** `docs/superpowers/plans/2026-09-08-spend-telemetry.md`
Tests row 4 (`VM: the unit runs as dalhaka | systemctl show | (G) DynamicUser not
forced`). Measured: with `nixosModules/claudeTelemetry.nix:207`
(`DynamicUser = lib.mkForce false;`) deleted, `nix eval
.#nixosConfigurations.core.config.systemd.services.opentelemetry-collector.serviceConfig.DynamicUser`
→ `true`, and `nix build .#checks.x86_64-linux.telemetry-vm -L --no-link` →
`EXIT=0`: systemd starts the unit under the existing static `dalhaka`, and
`systemctl show … -p User --value` prints `dalhaka` either way, so the row's
command cannot discriminate `DynamicUser`. The mutant is killed by
`telemetry-eval` assertion 7 (`sc.DynamicUser == false`), which the section also
mandates, so nothing is unguarded; and row 4 is not vacuous (`User = "root"`
turns it red). This is a plan Tests-table erratum: the mutant that turns row 4
red is a wrong `User`, and (G) belongs in the eval-7 row. Not gating — no code
change is owed.

**MINOR-2 — the D6 assertion's predicate deviates from the section's literal
text.** `nixosModules/claudeTelemetry.nix:192`:
`assertion = !(config.services.claude-managed-settings.enable or false);` where
the section writes `!config.services.claude-managed-settings.enable`. The
`or false` is necessary, not defensive slack: the VM node imports only
`claudeTelemetryModule` and `evidenceStoreModule`, so the option does not exist
there and the literal form would fail evaluation. On core the option exists and
the guard is live (outside-named mutant #21 fires it). Undisclosed in the commit
body; record only.

**MINOR-3 — an addition to the VM node the section does not list.**
`tests/integration/telemetry-vm.nix:147-150` adds
`environment.systemPackages = [ pkgs.iproute2 ];` so the three `ss` assertions
have `ss`. Benign and load-bearing (mutants #4, #5 depend on it).

**MINOR-4 — a config that empties the log file costs 900 s to fail.**
`tests/integration/telemetry-vm.nix:157`
`machine.wait_until_succeeds("test -s /var/lib/opentelemetry-collector/claude-logs.jsonl")`
has no explicit timeout, so mutant (B) (the filter names prefixed
`claude_code.`, dropping every record) is killed by the framework's 900 s
default rather than by the `grep -q -F 'api_request'` line the row names:
`!!! RequestedAssertionFailed: action timed out after 900.24 seconds
(timeout=900.0)`. Correct red, slow and non-diagnostic.

**MINOR-5 — a hardening mutant dies with a Nix attribute error, not the check's
message.** `flake.nix:1971` `&& sc.IPAddressDeny == "any"`. With
`nixosModules/claudeTelemetry.nix:216` deleted the check goes red as
`error: attribute 'IPAddressDeny' missing at … flake.nix:1971`, so the operator
reading the failure does not see `telemetry-eval: the collector must run as the
evidence-store owner …`. Killed either way; a `sc.IPAddressDeny or null == "any"`
form would print the intended message.

**MINOR-6 — assertion 10 depends on `builtins.any`'s short-circuit and on
`c.assertions` ordering.** `flake.nix:1994`
`(nixpkgs.lib.any (a: nixpkgs.lib.hasInfix "enable one" a.message) c.assertions)`
forces `.message` on every assertion it walks. On the good tree it stops at the
telemetry assertion; when that assertion is removed (mutant #20) the walk
reaches nixpkgs' `filesystems.nix:452`, whose message evaluates
`fileSystems'.cycle` and throws, so the check dies with
`error: attribute 'cycle' missing` instead of its own message. Red is red, but
the same booby trap would fire on an *unmutated* tree if the assertion list
order ever changed. A `lib.any (a: lib.hasInfix … (a.message or ""))` over a
filtered list, or asserting on the module's own message string, is sturdier.

**MINOR-7 — `githooks/pre-commit` is red in the clone on the board's queue
block only.** `docs/OPERATIONS.md` `<!-- tasks:begin -->`. The hook regenerates
the block (dropping `SP3` from `CR4 PW1glm PW1kimi PW1pro SP2 SP3 SP8`) and
exits 1. A base-`e4258e0` clone runs the same hook to exit 0, so the branch's
own commit is the cause; committing the board is forbidden here. Record for the
integrator, not owed by the seat.

**MINOR-8 — one measured switch-surface line outside §Operator step 2's
prediction.** `config.yaml: ∅ → ε` in `nix store diff-closures
/run/current-system ./result` — the collector's generated settings file. Per
step 2 ("a measured line outside this is a finding against the plan") it is
recorded here; it is SP3's own declared output, and the two predicted lines that
print nothing (`etc` gaining the managed-settings file, the two broker units
rebuilt) are name-identical store paths that `diff-closures` cannot show — both
were verified directly (see ## Summary). The predicted `evidence: … KiB → …`
line is absent because neither SP1 nor SP3 touches `pkgs/evidence`.

No MAJORs.

## Verdict

**APPROVED.** The section's contract is met item by item; the privacy invariant
(brief §3) is enforced at the data-point and log-record contexts, not only at
the resource, and is proven both by the rendered collector config and by a
mutant that turns the VM red; both reds in the commit body reproduce verbatim;
all four acceptance checks are green under `--rebuild`; the touches list and the
commit convention hold exactly. 25 mutants applied, 25 killed. The eight MINORs
are recorded, none owed before landing; MINOR-1 is a correction owed to the
plan's Tests table, not to the code.

For switch #23: the surface is `otelcol-contrib 0.151.0` (+360.1 MiB), the new
`opentelemetry-collector` unit, the generated `config.yaml` and
`claude-code-telemetry-settings.json`, plus the two broker units rebuilt onto
SP1's addon (`policy.py` `f5azl4d1…` → `4jy9nhh…`) — the prediction holds.
