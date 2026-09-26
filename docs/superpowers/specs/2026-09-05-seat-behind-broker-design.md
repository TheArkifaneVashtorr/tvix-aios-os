# The seat behind a broker — design (approved in approach, 2026-09-05 evening; spec for review)

Operator's decision: the seat gets its OpenRouter key the way the lanes do — injected by an egress broker from the root-only `/var/lib/secrets/openrouter-key`; no agent process ever holds it; the plaintext file in the operator's home goes away; Proton Pass stays the vault of record for the human copy. Closes claim `seat-key-exception-undecided`. Invariants touched: brief §3 (broker as the only route; credentials never in agent hands) — so the VM test is the gate and the operator switches.

## What exists (reused, not rebuilt)

- `nixosModules/egressBroker.nix`: one mitmproxy instance per `services.egress-broker.instances.<name>` in a persistent netns `/run/netns/egress-<name>`, veth `veb-<name>`/`ven-<name>`, `--mode regular` proxy at `hostAddress:listenPort` reachable only from the namespace side, credential injection per host from a key file, audit JSONL, CA bundle published at `/var/lib/egress-broker-ca-bundle/<name>/ca-bundle.crt`.
- `nixosModules/modelLane.nix`: a system unit template joins that netns (`NetworkNamespacePath`), sets `NODE_EXTRA_CA_CERTS`/`SSL_CERT_FILE` to the bundle and a placeholder credential the broker overwrites, runs `lane-run` on a job directory, and a polkit rule lets the operator user start `lane-<name>@<job>`. Address block 10.100.3.x is the openrouter lane's, 10.100.2.x media's.
- `pkgs/dsh-openrouter`: the wrapper (key checks, route overlay, hooks.json with the deny-only guard), `--headless` and web modes, UI bound to 127.0.0.1.
- Concept 2026-09-03b: "the operator seat is the lane harness minus the lane." This design puts the lane back.

## Design

1. **A broker instance `seat`** — `services.egress-broker.instances.seat`: allowlist `openrouter.ai` only, inject `Authorization: Bearer <key>` for that host from `/var/lib/secrets/openrouter-key` (the same file the lane uses), address block **10.100.4.x** (host 10.100.4.1, namespace 10.100.4.2), its own audit log `/var/lib/egress-broker/seat/audit.jsonl`. Deny paths as the lane (`/api/v1/messages` refused before injection).
2. **Seat units run as the operator, in the namespace.** A system unit template `seat@<job>` with `User = dalhaka` (not DynamicUser — the seat edits the operator's clones under `~/factory/ws` and, interactively, the checkout), `NetworkNamespacePath = /run/netns/egress-seat`, `HTTPS_PROXY`/`HTTP_PROXY` = `http://10.100.4.1:<listenPort>`, `NODE_EXTRA_CA_CERTS`/`SSL_CERT_FILE` = the seat's public CA bundle, `OPENROUTER_API_KEY = injected-by-broker` (placeholder; the broker replaces the header; a request the broker refuses never carries a real key). The polkit rule from the lane module, generalised, lets the operator start and stop `seat@*`. Everything else about the unit (hardening, `ReadWritePaths` = `/home/dalhaka/factory`, `/home/dalhaka/nixos-agent-env`, the sibling flakes, `/var/lib/seat`) is declared in Nix and asserted by an eval check.
3. **Jobs, not arguments.** `seat-submit` writes a job directory `/var/lib/seat/jobs/<id>/` (0700, operator): `workspace`, `dsh-home`, `mode` (`headless` | `web`), `brief` (file), `model`, `effort`, then starts `seat@<id>`; the unit runs `dsh-openrouter --broker --model … --headless "$(cat brief)"` (or the web mode) with `DSH_HOME` from the job; stdout/stderr and the `FACTORY-RESULT` block land in the job dir; `factory-task` calls `seat-submit` instead of `dsh-openrouter` directly and reads the result from the job dir (its `.result` format unchanged). Job payloads (briefs, transcripts) are the operator's data: the backup exclusion list gains `/var/lib/seat/jobs/*/dsh-home/sessions` as the lane's did.
4. **The wrapper gains `--broker`.** It skips the key file entirely (no read, no mode check), keeps `OPENROUTER_API_KEY` as the placeholder if set by the unit, honours the proxy environment, and refuses to run `--broker` outside a namespace whose default route is the broker (it checks `ip route` shows the veth gateway) so a mis-launch cannot leak the placeholder as if it were a key. Without `--broker` the wrapper behaves as today but prints a deprecation line pointing at the seat unit; after the migration the key file is deleted and the old path dies with the existing "no key" message.
5. **The web seat reaches the browser.** Inside the namespace the UI binds `10.100.4.2:<port>` (the unit passes an internal `--bind-namespace` the wrapper accepts only under `--broker`; the operator-facing `--host` rejection stays); nftables on `veb-seat` accepts `hostAddress → 10.100.4.2:<port>` from the host side only; the operator opens `http://10.100.4.2:<port>` (the unit prints the URL to the journal and the job dir). No other inbound path exists.
6. **Guard unchanged.** `hook-guard.py`'s rules keep working inside the unit (it is the same wrapper writing the same hooks.json); the key-file spelling rule becomes moot and stays.
7. **Migration.** Switch N: the instance, the netns, the template, polkit, `seat-submit`, the wrapper's `--broker`. Then the operator runs one headless job and one web job through the units, confirms the audit log shows injected requests, and deletes `~/.config/openrouter/key` (the runbook's one command). `factory-task` switches to `seat-submit` in the same switch (it tolerates both until the file is gone).

## Tests (red first, VM as the gate)

- **Eval check `seat-eval`**: the instance exists with the allowlist and inject entry; the template joins `/run/netns/egress-seat`, runs as the operator, has the proxy and CA environment, the placeholder key, no `/var/lib/secrets` in its paths; polkit renders the operator rule; 10.100.4.x does not collide with 10.100.2.x/3.x (assertion).
- **VM check `seat-vm`** (like `lane-vm`, a fake `openrouter.ai`): a job submitted via `seat-submit` reaches the fake with the real `Authorization` header injected while the job's environment holds only the placeholder; a `POST /api/v1/messages` is refused before injection; a request to any other host is dropped by the namespace; the web job's UI answers on `10.100.4.2:<port>` from the host side and not from anywhere else; the audit log carries both requests.
- **Unit (bats)**: the wrapper under `--broker` never opens the key file (strace-free: a fake key file with mode 000 must not be touched); `--broker` outside a namespace refuses; `factory-task` calls `seat-submit` and reads the job result into the same `.result` shape.
- **Negative assertion**: a seat unit with a real key in its environment fails eval (`assertion-negative` style).

## Risks weighed

- The operator's interactive seat becomes a systemd job: startup is a `systemctl start` behind polkit instead of a shell command. The runbook gives one command each way.
- Running as the operator user inside a namespace grants the unit the operator's files by design (that is the point of the seat); hardening is `NoNewPrivileges`, `ProtectSystem=strict` with the explicit `ReadWritePaths`, no `/var/lib/secrets`.
- Anything on the host that expects `~/.config/openrouter/key` (the seat's current launch paths, `launch-today.sh`) stops working the day the file is deleted; the plan lists every caller.
- The broker adds latency per request; the lane measured none worth noting.
- A gap to name: the placeholder-in-environment is still a string an agent can print, but it authenticates nothing.

## Not in this spec

Anthropic models on OpenRouter (operator: hold). Fronting the Claude Code session itself (the orchestrator) with a broker — a separate decision.
