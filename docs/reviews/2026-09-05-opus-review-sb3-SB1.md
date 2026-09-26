---
reviewer: opus
majors: null
minors: 6
---
# Opus gate — seat run sb3, task SB1 — APPROVED

Branch `task/SB1` in `/home/dalhaka/factory/ws/sb3/SB1`, base `3d03caa`, head `1253e6c`, one commit.
Reviewed in a fresh clone at `/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-sb3-SB1`
(base tree for red-before-green at `.../scratchpad/base-sb3`). Nothing on the host was changed; the only
host-state reads were `ls` of `/var/lib/egress-broker`, `id dalhaka`, and `nix store diff-closures /run/current-system`.

## Summary

SB1 lands `nixosModules/seatLane.nix` (229 lines), `hosts/core/seat.nix`, `pkgs/seat/seat-run.py`,
`tests/seat/test_seat_run.py`, the `pkgs/seat` attrset split, and three flake checks. The security
contract holds under every probe I could construct: the OpenRouter key exists only in
`/var/lib/secrets/openrouter-key`, which the unit's mount namespace makes ENOENT; the unit environment
carries the placeholder `injected-by-broker` and nothing key-shaped; the netns has exactly one route out
(the broker); the one new firewall opening is exactly the plan's amendment-1 output rule for the web UI's
port range and nothing else.

Five acceptance checks green, ten of the eleven prescribed mutations die on the named check, red-before-green
proven on the base tree, commit subject byte-identical to the plan, both trailers present, one commit.
Six MINORs, no MAJOR. **Approved.**

The one row that must reach the operator before a switch: SB1 adds a **host-side nftables base chain with a
trailing `drop` on the `output` hook** (`output-seat`). No check in this tree evaluates the rendered ruleset
(mutation M-G survives), so SB4's VM is the gate for it, exactly as the plan's Global Constraints anticipate.

## Invariants

**The key never reaches a Nix expression, a unit environment, or a file the unit can read.**
The rendered unit (`.../etc/systemd/system/seat@.service`) carries fourteen `Environment=` lines; the
credential one is `Environment="OPENROUTER_API_KEY=injected-by-broker"`. `grep -rIl "sk-or-"` over the built
toplevel's whole `etc/systemd/system/` matches nothing. The key path appears only as
`InaccessiblePaths=/var/lib/secrets` (the plan mandates it) and inside the root-owned broker policy JSON as
`"value_file": "/var/lib/secrets/openrouter-key"` — a path, never a value. `InaccessiblePaths` is applied to
the unit's own mount namespace by PID 1 before the `User=dalhaka` drop, so it holds regardless of the user's
credentials: the directory is over-mounted with an empty, inaccessible node and the unit sees ENOENT, not a
permission error it could route around. Independently, `id dalhaka` shows `users wheel networkmanager kvm
lane helm` — **not** `egress-broker` — so the 0440 root:egress-broker key file would be unreadable even
without the mount hiding, and `NoNewPrivileges=true` blocks the `wheel` membership from being cashed in via
setuid `sudo`.

**The only route is the broker.** `egress-netns-seat` gives the namespace a single default route
`via 10.100.4.1`. On the host, `forward-seat` drops both directions on `veb-seat`; `input-seat` accepts only
`tcp dport 3141` from `10.100.4.2`, plus established/related, then drops. An nftables `drop` in any base chain
is terminal for the packet, so nixos-fw's accepts on other base chains at priority 0 cannot rescue it (the
module's own comment states this and the rendered chains bear it out). A packet from the namespace to anything
but `10.100.4.1:3141` therefore meets `forward-seat`'s `iifname "veb-seat" drop` (off-host destinations) or
`input-seat`'s trailing `iifname "veb-seat" drop` (host destinations). Brief §3 invariant 3 holds.

**Allowlist.** `services.egress-broker.instances.seat.allow == [ "openrouter.ai" ]`, one host, no widening.
`denyPaths` and `bodyPatch` are byte-identical to the openrouter lane's (diffed below), so `/api/v1/messages`
fails closed *before* injection and every chat body gets ZDR + training opt-out at the chokepoint.

**The firewall rule.** One new base chain, one new accept:

```
chain output-seat {
  type filter hook output priority filter - 1;
  oifname "veb-seat" ct state established,related accept
  oifname "veb-seat" ip daddr 10.100.4.2 tcp dport 43200-43299 accept
  oifname "veb-seat" drop
}
```

Same table (`inet egress-broker`), same priority idiom, same `type filter hook … priority filter - 1;` shape
as the chains `egressBroker.nix` renders for itself, appended through `content`'s `types.lines` merge — the
plan's "add the one rule the way it adds its own" is met. It is an `output` chain, which is amendment 1's
correction (Kimi's `forward` rule would be dead, Pro's `input` rule would have the wrong saddr). Ordering is
safe: the establish/related accept precedes the port accept, the drop is last, and no later drop can be
appended by another consumer without editing this module. Scoped to `oifname "veb-seat"`, so no other
interface is affected.

## Rule behaviour

Every row evaluated against the real host config in the clone with
`nix eval .#nixosConfigurations.core.config.<path> --json`.

| row | expected | observed |
|---|---|---|
| 1 instance `seat` — allow | `["openrouter.ai"]` | `["openrouter.ai"]` ✅ |
| 1 inject valueFile | `/var/lib/secrets/openrouter-key`, not a store path | `"valueFile":"/var/lib/secrets/openrouter-key"` ✅ |
| 1 denyPaths | identical to the openrouter lane's | both `{"openrouter.ai":{"pathPrefixes":["/api/v1/messages"]}}` — byte-identical ✅ |
| 1 bodyPatch | identical to modelLane's block | both `{"openrouter.ai":{"merge":{"provider":{"data_collection":"deny","zdr":true}},"pathPrefixes":["/api/v1/chat/completions"]}}` ✅ |
| 1 addresses / port | 10.100.4.1 / 10.100.4.2 / 3141 | exactly those ✅ |
| 1 no other 10.100.4.x | only instance `seat` | instances are `openrouter` (10.100.3.x:3131) and `seat` (10.100.4.x:3141); no collision ✅ |
| 1 collision assertion fires | mutating a fixture to collide fails eval | M-H (lane → 10.100.4.5) → `seat-eval` exit 1, `"10.100.4.x must be the seat's own block"` ✅ |
| 2 `User` | `dalhaka` | `dalhaka` ✅ |
| 2 `NetworkNamespacePath` | `/run/netns/egress-seat` | same ✅ |
| 2 Requires **and** After | both list `egress-netns-seat.service` and `egress-broker-seat.service` | `requires` and `after` are both `["egress-netns-seat.service","egress-broker-seat.service"]` ✅ |
| 2 Environment (all) | HTTPS_PROXY `http://10.100.4.1:3141`; HTTP_PROXY same; NO_PROXY `127.0.0.1,10.100.4.2`; NODE_EXTRA_CA_CERTS and SSL_CERT_FILE `/var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt`; OPENROUTER_API_KEY `injected-by-broker`; FACTORY_ROUTING_TABLE `/home/dalhaka/nixos-agent-env/docs/ledger/routing.toml` | all seven exact; plus `NODE_USE_ENV_PROXY=1` (plan amendment 3) and `SEAT_NAMESPACE_ADDRESS=10.100.4.2` (seat-run's web bind) ✅ |
| 2 no `sk-or-` anywhere in the unit | none | `grep -rIl "sk-or-"` over the toplevel's `etc/systemd/system/` → no match ✅ |
| 2 ExecStart | `seat-run` with `%i` | `/nix/store/r95d8…-seat-run/bin/seat-run %i` ✅ |
| 2 ProtectSystem | `strict` | `strict` ✅ |
| 2 ReadWritePaths | exactly the five | `/var/lib/seat`, `/home/dalhaka/factory`, `/home/dalhaka/nixos-agent-env`, `/home/dalhaka/flakes`, `/home/dalhaka/.local/share/dsh-openrouter` — exactly five, in order ✅ |
| 2 InaccessiblePaths | contains `/var/lib/secrets` | `["/var/lib/secrets"]` ✅ (see MINOR-2 on the missing `-` prefix and the un-hidden broker tree) |
| 2 NoNewPrivileges / Type / WorkingDirectory | true / simple / unset | `true`, `simple`, absent from the rendered unit ✅ |
| 3 nftables | exactly one new accept, web range only, host→namespace | as quoted above; one accept for `43200-43299` + established/related + drop, nothing else inbound ✅ |
| 3 same shape as egressBroker's own | same table/chain idiom | same `inet egress-broker` table, same `filter - 1` priority, merged via `content` (`types.lines`) ✅ |
| 4 polkit | `seat@*` start/stop/restart, `dalhaka` only | prefix `"seat@"`, suffix `".service"`, `verb == "start" \|\| "stop" \|\| "restart"`, `subject.user == "dalhaka"`; no wildcard beyond `seat@` ✅ |
| 5 tmpfiles | `/var/lib/seat 0750 <op> users`, `/var/lib/seat/jobs 0700 <op>` | `d /var/lib/seat 0750 dalhaka users -` and `d /var/lib/seat/jobs 0700 dalhaka -` (group field `-` = root; mode 0700 makes it moot; matches the plan's literal text) ✅ |
| 7 seat-run headless argv | `--broker --model M --headless <brief>` | `['dsh-openrouter','--broker','--model','m','--headless','<brief text>']` ✅ |
| 7 seat-run web argv | `--broker --bind-namespace 10.100.4.2 -- --no-open --port N` | exactly that ✅ |
| 7 DSH_HOME / cwd / files | job's dsh_home, workspace, stdout/stderr/exit_code/result | all four written; `result.txt` holds the FACTORY-* block or `status=failed` ✅ (buffered, not streamed — MINOR-3) |
| 7 url.txt + printed URL | `10.100.4.2:N` | `http://10.100.4.2:43210` printed and filed ✅ |
| 7 brief quoting | quotes and `$` survive | `subprocess.run` list form, `shell=False`; brief `say "hi" $HOME \`id\` \\ end` arrives as one argv element verbatim ✅ |
| 7 malformed job.json / missing dir | non-zero, message, no traceback | **raises** `JSONDecodeError` / `FileNotFoundError` with a traceback (MINOR-4) ⚠️ |
| 7 does seat-run pass the key | must not | it never reads, writes or forwards a credential ✅ |
| 8 host wiring | `seat.nix` values, imported, module exported, packages, checks | `hosts/core/default.nix:13` imports `./seat.nix`; values are enable/keyFile/10.100.4.1/10.100.4.2/3141/dalhaka; `nixosModules.seatLane` exported; `packages.seat-submit` and `packages.seat-run` build; all three checks exist ✅ |

## Checks

Run from inside the clone, `XDG_CACHE_HOME` under the scratchpad.

| command | exit | wall |
|---|---|---|
| `nix build .#checks.x86_64-linux.seat-eval -L --no-link` | 0 | 10.9 s |
| `nix build .#checks.x86_64-linux.seat-assertion-negative -L --no-link` | 0 | 2.8 s |
| `nix build .#checks.x86_64-linux.seat-unit -L --no-link` | 0 | 0.7 s — `13 passed in 0.04s` |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | 0 | 18.5 s |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 | 3.9 s — `formatted 94 files (0 changed)`, `All checks passed!` |
| `nix develop -c ruff check pkgs/seat tests/seat` | 0 | `All checks passed!` |
| `nix develop -c pytest tests/seat -q` | 0 | `13 passed in 0.04s` |
| `nix develop -c githooks/pre-commit` | 0 | `All checks passed!` + the sanctioned `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` line |
| `nix build .#nixosConfigurations.core.config.system.build.toplevel --no-link --print-out-paths` | 0 | 11.0 s → `/nix/store/zszphrk9cq1fhr4w23v4nx2wx7183sbz-nixos-system-core-…` |
| `nix build .#packages.x86_64-linux.seat-submit .#packages.x86_64-linux.seat-run --no-link` | 0 | both build |

No failures, so no failure tails to record. The pre-commit run left `docs/OPERATIONS.md` dirty in my clone
(it dropped `SB1` from the queue now that the commit exists); I reverted it and left the clone clean.

## Closure diff

`nix store diff-closures /run/current-system <toplevel>` and, to isolate SB1 from what the base already
carried, `nix store diff-closures <base toplevel> <head toplevel>` — both print the identical delta:

```
dsh: 33.4 KiB
egress-policy-seat.json: ∅ → ε
hook: 10.1 KiB
python3-minimal: ∅ → 3.13.15, 25.3 MiB
seat: ∅ → ε
seat-run.py: ∅ → ε
unit-egress-broker-seat.service: ∅ → ε
unit-egress-netns-seat.service: ∅ → ε
unit-script-egress-netns-seat: ∅ → ε
unit-script-egress-netns-seat-pre: ∅ → ε
unit-seat: ∅ → .service
```

Exactly what SB1 should add: one broker instance (its netns unit, its broker unit, its policy JSON), the
`seat@.service` template, and `seat-run`. No new daemon is `wantedBy` anything — `wantedBy` on `seat@` is
`[]`, so the switch installs the units without starting a job, matching `hosts/core/seat.nix`'s comment.
The `dsh`/`hook`/`python3-minimal` rows are the second `pkgs` instantiation described in MINOR-1, not new
software.

## Red before green

The base tree `3d03caa` in a separate clone, with **only** SB1's check definitions and its test file added
(`git checkout 1253e6c -- flake.nix tests/seat/test_seat_run.py`; `nixosModules/seatLane.nix` and
`pkgs/seat/seat-run.py` deliberately absent), then `git add -A` so the flake can see them:

- `seat-eval` → **exit 1**: `error: Path 'nixosModules/seatLane.nix' does not exist in Git repository …`,
  raised through `lib.assertMsg` at `flake.nix`'s check.
- `seat-assertion-negative` → **exit 1**: same missing-module error, raised from
  `builtins.tryEval seatBadKeySystem.config.system.build.toplevel.drvPath`.
- `seat-unit` → **exit 1**:
  `FileNotFoundError: [Errno 2] No such file or directory: '/build/pkgs/seat/seat-run.py'` /
  `ERROR tests/seat/test_seat_run.py` / `Interrupted: 1 error during collection`.

Honest caveat: the two Nix checks go red because the module file is missing, not because a specific
assertion fires — that is the only red available before the module exists. `seat-unit` is red for the
correct TDD reason (the test exists, the implementation does not); note that had SB1's test file *not* been
carried across, `seat-unit` would have passed on the base off SB3's `test_seat_submit.py` alone.

## Mutation table

Applied in the clone, `git add -A` before each run (flakes only see tracked files), `git diff` asserted
non-empty first, reverted after. Rows A–F and H–J die; G survives by design.

| row | mutation | check | result |
|---|---|---|---|
| M-A | `allow = [ cfg.host "example.com" ]` | seat-eval | **exit 1** — `seat-eval: egress-broker instance 'seat' must take the 10.100.4.x block … and allow == [ "openrouter.ai" ]` (the module's own `allow == [ cfg.host ]` assertion fires too) |
| M-B | `inject.${cfg.host}.valueFile` line deleted | seat-eval | **exit 1** — `seat-eval: … must inject from /var/lib/secrets/openrouter-key` |
| M-C | keyFile store-path assertion deleted | seat-assertion-negative | **exit 1** — `seat-assertion-negative: services.seat-lane.keyFile = a store path DID NOT FAIL the build` |
| M-D | `InaccessiblePaths` dropped | seat-eval | **exit 1** — `seat-eval: seat@ InaccessiblePaths must hide /var/lib/secrets` |
| M-E | `NetworkNamespacePath` dropped | seat-eval | **exit 1** — `seat-eval: seat@ must join /run/netns/egress-seat and run as the operator dalhaka` |
| M-F | `FACTORY_ROUTING_TABLE = "sk-or-fixture"` | seat-eval | **exit 1** — `seat-eval: seat@ must hold the placeholder credential (never a key)…`; the module's own `sk-or-` assertion fires as well |
| M-G | web rule widened to `oifname "veb-seat" accept` (all ports, any daddr) | seat-eval | **exit 0 — SURVIVES.** No check in this tree reads the rendered ruleset. Pre-authorised by the task brief; the rule as written is correct, so this is MINOR-5 and SB4's job |
| M-H | `hosts/core/lanes.nix` hostAddress → `10.100.4.5` (collision) | seat-eval | **exit 1** — `seat-eval: 10.100.4.x must be the seat's own block -- no other egress-broker instance may collide with it` |
| M-I | `--broker` removed from the headless argv | seat-unit | **exit 1** — `FAILED tests/seat/test_seat_run.py::test_headless_runs_broker_and_writes_result_files - AssertionError: assert ['dsh-openrou…'] == […]` |
| M-J | `exit_code.txt` write deleted | seat-unit | **exit 1** — `FAILED … FileNotFoundError: … exit_code.txt` |
| M-K (added) | `ReadWritePaths` gains `/home/dalhaka`; `ProtectSystem` and `NoNewPrivileges` dropped | seat-eval | **exit 0 — SURVIVES.** See MINOR-6 |

## Findings

No MAJORs.

**MINOR-1 — the seat runs a second, divergent build of the harness (closure duplication).**
`nixosModules/seatLane.nix:60` — `default = pkgs.callPackage ../pkgs/dsh-openrouter { dsh = pkgs.callPackage ../pkgs/dsh { }; }`.
The module's `pkgs` is `nixpkgs-host` (flake.nix:6, pin `a5cc6f2`), while `flake.nix:49–52`'s `dshHost`/
`dshOpenrouter` come from `nixpkgs` (pin `34ab990`). Evidence:

```
flake dsh-openrouter: /nix/store/4va93cxln3wp11d7bqqrz74anzrzyvah-dsh-openrouter
seat harness:         /nix/store/68jlydzjyfsv4gavpkiaynfd60b6fzjh-dsh-openrouter
```

Same source, two builds; this is what the closure diff's `dsh: 33.4 KiB` and `python3-minimal: 25.3 MiB`
rows are. `modelLane.nix:74` already does the same thing, so this is precedent, not regression — but the
unit runs a harness that `nix build .#dsh-openrouter` and the bats suite never exercise.
*Fix (follow-up, not this task):* pass the flake's `dshOpenrouter` in through a module arg the way
`proton-drive-cli-pkg` is passed, or accept and document the divergence.

**MINOR-2 — hardening list narrower than the lane's, and `InaccessiblePaths` lacks the `-` prefix.**
`nixosModules/seatLane.nix:180` — `InaccessiblePaths = [ "/var/lib/secrets" ];`. `modelLane.nix:281–288`
writes `"-/var/lib/secrets"` (and also hides `/var/lib/egress-broker`, `/var/lib/helm`, `/run/baskets`,
`/var/lib/baskets`). Two consequences:

1. Without the `-`, a host or VM node where `/var/lib/secrets` does not exist fails the unit's mount setup
   instead of ignoring the entry. On the live host the directory exists (`ls -la /var/lib/egress-broker`
   sibling check; `/var/lib/secrets` is present but mode-blocked to me), so this bites SB4's VM node and any
   fresh install, not the operator's next switch. Fail-closed, not fail-open.
2. `/var/lib/egress-broker` stays visible to the seat, which is a network-capable process running
   model-authored code. I verified what is actually exposed: the CA **private** key
   `mitmproxy-ca.pem` is `-rw------- egress-broker`, and `dalhaka` is not in `egress-broker`
   (`id dalhaka` → `users wheel networkmanager kvm lane helm`), so no key material is readable. What *is*
   readable is `audit.jsonl` (`-rw-r--r-- egress-broker`), and `pkgs/broker/policy.py:91–111` shows its
   records carry `ts/instance/client/method/host/host_header/sni/path/bytes_out/bytes_in/verdict/reason` —
   **no headers, no credential**. So this is metadata about the seat's own traffic, not a key leak, and it
   is not one of brief §3's six invariants; it is `modelLane.nix`'s stricter house style unapplied.
*Fix:* `InaccessiblePaths = [ "-/var/lib/secrets" "-/var/lib/egress-broker" ];`.

**MINOR-3 — `seat-run` buffers where the plan says "tees".**
`pkgs/seat/seat-run.py:113` — `subprocess.run(cmd, capture_output=True, text=True, check=False)`, then
`_write(... "stdout.txt" ...)` at lines 119–122. Nothing reaches `stdout.txt`, `stderr.txt` or the journal
until the child exits, and the whole transcript is held in RAM. For a long headless factory job the operator
watches a silent journal; for a web job (`Type=simple`, the UI runs until stopped) `stdout.txt`,
`exit_code.txt` and `result.txt` only appear at shutdown, and `result.txt` then reads `status=failed` because
a web session prints no `FACTORY-RESULT`. The observable contract SB3's `seat-submit` depends on (poll for
`result.txt`, stream `stdout.txt`, exit on `exit_code.txt`) is still met for headless jobs, which is why this
is minor. *Fix:* `Popen` with line-buffered pipes teed to the files and to `sys.stdout`/`sys.stderr`.

**MINOR-4 — a malformed or missing job dies with a traceback, not a message.**
`pkgs/seat/seat-run.py:37–39` — `_load_job` opens and `json.load`s with no guard; line 93 does
`os.environ["SEAT_NAMESPACE_ADDRESS"]`. Probed directly:

```
malformed RAISED: JSONDecodeError Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
missing   RAISED: FileNotFoundError [Errno 2] No such file or directory: '…/nope/job.json'
web-noenv RAISED: KeyError 'SEAT_NAMESPACE_ADDRESS'
```

The unit still fails (non-zero), so nothing runs unauthenticated — but the journal gets a Python traceback
instead of one line, and no test covers any of the three. Only `run([])` (missing job id) is handled, at
line 65–67. *Fix:* wrap `_load_job` and the env lookup, return 2 with a one-line message, add three cases to
`tests/seat/test_seat_run.py`.

**MINOR-5 — nothing in this tree tests the nftables rule (M-G survives).**
`nixosModules/seatLane.nix:198–205`. The rule as rendered is correct — I read the full evaluated
`networking.nftables.tables.egress-broker.content` and it contains exactly one new accept — but widening it
to `oifname "veb-seat" accept` leaves every check green. This is the plan's own expectation ("a VM test is
the gate for anything touching the broker or the firewall"). **This is the row the operator needs before a
switch:** SB1 adds a host-side `output`-hook base chain with a trailing `drop`, and SB4 must prove both
halves — the web-range curl from the host succeeds, and a curl to any other port on `10.100.4.2` (and from a
second namespace or a spoofed source) fails — before switch #N.

**MINOR-6 — `seat-eval` does not assert the hardening the spec says it asserts.**
`flake.nix:1558–1651`. The check covers the instance, addresses, namespace, user, environment, the `sk-or-`
regex, `InaccessiblePaths`, ExecStart, polkit and the address collision — but not `ProtectSystem`,
`ReadWritePaths`, `NoNewPrivileges`, `Type` or `RestrictAddressFamilies`. Mutation M-K (add `/home/dalhaka`
to `ReadWritePaths`, delete `ProtectSystem` and `NoNewPrivileges`) leaves `seat-eval` at **exit 0**. The
plan's Step-1 enumeration for `seat-eval` does not list them, so the task text is satisfied; the *spec*
§2 does — "Everything else about the unit (hardening, `ReadWritePaths` …) is declared in Nix and asserted by
an eval check". *Fix:* four more `assertMsg` lines pinning `sc.ProtectSystem == "strict"`,
`sc.ReadWritePaths == [ … the five … ]`, `sc.NoNewPrivileges`, and `sc.RestrictAddressFamilies`.

### Plan amendments — which apply to SB1, and the skip

Four amendments were folded into the plan after the tasks (amendment 5 is a plan-writing rule, not code).
Three apply to SB1 and all three landed:

- **#1 output-hook rule** — landed, `seatLane.nix:198–205`, and it is an `output` chain, not `input`/`forward`.
- **#2 `RestrictAddressFamilies` must include `AF_NETLINK`** — landed, `seatLane.nix:185`:
  `AF_INET AF_INET6 AF_UNIX AF_NETLINK`, with the reason (the wrapper's `--broker` `ip route` check) in the comment.
- **#3 `NODE_USE_ENV_PROXY=1`** — landed, `seatLane.nix:150`. Note the lane sets *both* this and
  `NODE_OPTIONS=--require …/proxy-shim.cjs` because "the host pin's Node 22.20 lacks that switch"
  (`modelLane.nix:236–241`); the seat sets only the env var. If the pinned Node needs the shim, the seat's
  model calls will not tunnel — they will simply fail (there is no other route), so this is a liveness risk,
  not a leak, and SB4's audit-line assertion is exactly the test that catches it. Worth SB4's attention.
- **#4 backup exclude — skipped, and the skip is justified.** I checked the premise. `hosts/core/proton-backup.nix`
  sets no `exclude` at all; the effective value is `nixosModules/protonBackup.nix:35`'s default
  `["**/.pytest_cache","**/.ruff_cache","/home/*/.cache"]`, confirmed by eval. There is **no lane exclusion in
  this tree** — `grep -rn "dsh-home\|/var/lib/lanes" --include=*.nix hosts/ nixosModules/` matches only
  `modelLane.nix`'s tmpfiles and `ReadWritePaths`, never a backup path. Nor is anything the seat writes in
  the backup set: `services.proton-backup.paths` contains neither `/var/lib/seat` nor `/home/dalhaka/factory`,
  so an exclude for `/var/lib/seat/jobs/*/dsh-home/sessions` would be a no-op on a path restic never visits.
  The amendment's own justification ("as the lane's are") is factually false, `hosts/core/proton-backup.nix`
  is in neither SB1's Files, touches nor acceptance, and a separate queued plan
  (`2026-09-05-backup-audit-paths.md`, task B1) owns the backup path set. The implementer disclosed the skip.
  Accepted; SB5 should carry it, or B1.

### Commit convention

Clean. One commit (`git rev-list --count 3d03caa..1253e6c` → `1`). Subject `cmp`'d byte-for-byte against the
plan's — identical, em dash and all. Both trailers present:
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sb3)` and
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

Seven of the nine changed files are inside `touches`. The two outside:

- **`docs/MAP.md`** — customary regeneration, and it is exactly a fresh write: I ran
  `nix develop -c python3 pkgs/evidence/repomap.py --root . write` over the committed tree and `diff -u`
  against the committed file produced no output. It adds `nixosModules/seatLane.nix`, `hosts/core/seat.nix`,
  the three checks, and bumps `tests/seat` from 1 to 2 files. No breach.
- **`docs/OPERATIONS.md`** — a one-line change, entirely inside the `<!-- tasks:begin -->` block, adding
  `CR2`, `FD1b` and `2026-09-05-factory-dispatch.md` to the derived queue. This is not a hand edit: the lint
  gate writes it. Running `nix develop -c githooks/pre-commit` in my clone printed
  `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and
  commit again` and rewrote the same line (this time dropping `SB1`, now that the commit exists). The plan's
  own Global Constraints sanction it verbatim: "it may regenerate the board block once: `git add
  docs/OPERATIONS.md` and commit again". The text is true for the tree at commit time, and the block is
  derived, never typed. **No breach.** Nothing outside that block changed — the prose paragraph still reads
  "the seat-behind-broker module (SB1, not started)", which is stale-by-one-commit board prose the next
  session's handoff will refresh; not SB1's to edit.

## Verdict

**APPROVED.** Every required row met, five acceptance checks green, ten of eleven mutations killed on the
named check, red proven on the base, one commit with the plan's exact subject and both trailers. No key
reaches a Nix expression, a unit environment, or any file the unit can read; the namespace's only route is
the broker; the allowlist is one host; the single new firewall opening is exactly the plan's amendment-1
rule and nothing more.

Six MINORs, none blocking. Two are worth carrying forward explicitly: **MINOR-5** — the new host-side
`output-seat` chain is untested in this tree and is SB4's gate before the operator switches; and **MINOR-2** —
`InaccessiblePaths` should gain the `-` prefix and `/var/lib/egress-broker` to match the lane's shape before
SB4's VM node runs on a host where `/var/lib/secrets` may not exist.
