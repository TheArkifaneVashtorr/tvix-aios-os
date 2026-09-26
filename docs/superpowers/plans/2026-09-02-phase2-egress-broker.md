# Phase 2 — Egress Broker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A per-netns, default-deny, TLS-terminating egress broker (mitmproxy + a pinned policy addon) with a JSONL audit log and credential injection, declared as a NixOS module, proven by an in-VM integration test and an on-host acceptance script.

**Architecture:** One mitmproxy (`mitmdump`) instance per network namespace, listening on the host side of that netns's veth pair, so every byte leaving the netns must cross it. All policy (allowlist, injection map, audit path) is a Nix-rendered JSON file consumed by one short pinned Python addon. Because the broker terminates TLS with its own local CA, allow/deny decisions and the audit log see the *real* inner request — a domain-fronted request (outer SNI allowed, inner Host not) is denied where a hostname-only allowlist would pass it. The NixOS module (`nixosModules/egressBroker.nix`) creates the netns, veth, nftables restrictions, and a hardened systemd service per instance. A NixOS VM test (`checks.integration`) runs the brief §7 Phase 2 test end-to-end in software; `tests/acceptance/phase2.sh` runs it on real hardware and real internet for the operator.

**Tech Stack:** mitmproxy 12.x (pinned nixpkgs `34ab9907`), Python 3 addon + pytest with `mitmproxy.test` helpers, NixOS module system, nftables, `pkgs.testers.runNixOSTest`, ruff (lint+format for Python).

**Spec:** `docs/superpowers/specs/2026-09-02-agent-environment-design.md` §2.3 (outer layer), `docs/brief.md` §5.3 + §7 Phase 2, decision Q4 in `docs/decisions/2026-09-02-section-9-answers.md`.

## Global Constraints

- Same repo, same rules as Phase 1's Global Constraints (nixpkgs pin `34ab99075ac4f7e40cf037eef32cb1c360bb85e9`, no new flake inputs, no secrets in repo, `set -euo pipefail`, shellcheck-clean, commits via `nix develop -c git commit` with the two trailer lines, never push, bash `set -e` discipline). Read `docs/superpowers/plans/2026-09-02-phase1-basket-crypto.md` Global Constraints — they all apply.
- Commit messages: `phase2: <task summary>` + the two trailers.
- Python: formatted by `ruff format`, lint-clean under `ruff check` (default rules). No type-checker this phase.
- The policy addon file is **policy-adjacent code**: keep it under ~150 lines, no feature not named here. The policy *data* (allowlist, inject map, paths) lives only in the JSON file Nix renders — never hardcoded in the addon.
- Secrets for injection are referenced by **absolute file path** in policy JSON; the addon reads them at startup into memory. No secret value ever appears in policy JSON, Nix store, repo, or audit log.
- Audit records are one JSON object per line with exactly the fields: `ts`, `instance`, `client`, `method`, `host`, `sni`, `path`, `bytes_out`, `bytes_in`, `verdict` (`allow`|`deny`|`error`), `reason`. Never log request/response headers or bodies.
- mitmproxy 12.x API details (test helper signatures, `Response.make`, `client_conn.sni`) may differ from the code below in small ways — adjust minimally and report the deviation, per the Phase 1 rules. The *behavior* asserted by the tests is not negotiable.
- Deny responses are HTTP 403 with body `egress-broker: denied\n`.

---

### Task 1: Python toolchain + addon core (default-deny + audit)

**Files:**
- Modify: `flake.nix` (python env, ruff, new checks)
- Modify: `treefmt.toml` (python formatter)
- Create: `pkgs/broker/policy.py`
- Create: `tests/broker/test_policy.py`

**Interfaces:**
- Produces: `EgressPolicy` addon class in `pkgs/broker/policy.py`, configured by env var `BROKER_POLICY` → path to JSON `{"instance": str, "allow": [str], "inject": {host: {"header": str, "prefix": str, "value_file": str}}, "audit_log": str}`. Hooks: `http_connect` (early deny on CONNECT host), `request` (deny/allow), `response`/`error` (audit close-out). Task 2 extends the same class; Tasks 3–5 consume the file and the JSON shape unchanged. Flake gains `checks.addon` (pytest) and python+ruff in devShell/lint.

- [ ] **Step 1: Flake + treefmt wiring**

In `flake.nix` `let`-block add:

```nix
      brokerPython = pkgs.python3.withPackages (
        ps: with ps; [
          mitmproxy
          pytest
        ]
      );
```

Add `pkgs.ruff` to `lintTools`. Add `brokerPython` to the devShell `packages` list. In `checks` add:

```nix
        addon =
          pkgs.runCommand "broker-addon-tests"
            {
              nativeBuildInputs = [ brokerPython ];
            }
            ''
              cp -r ${self}/pkgs/broker broker
              cp -r ${self}/tests/broker tests-broker
              cd .
              pytest tests-broker -q
              touch $out
            '';
```

and extend the `lint` check with `ruff check pkgs/broker tests/broker` and `ruff format --check pkgs/broker tests/broker`.

In `treefmt.toml` add:

```toml
[formatter.python]
command = "ruff"
options = ["format"]
includes = ["*.py"]
```

- [ ] **Step 2: Write the failing tests** — `tests/broker/test_policy.py` (deny + audit only, this task):

```python
import importlib.util
import json
import pathlib
import sys

from mitmproxy import http
from mitmproxy.test import tflow


def load_addon(tmp_path, monkeypatch, policy):
    policy_file = tmp_path / "policy.json"
    policy.setdefault("audit_log", str(tmp_path / "audit.jsonl"))
    policy_file.write_text(json.dumps(policy))
    monkeypatch.setenv("BROKER_POLICY", str(policy_file))
    root = pathlib.Path(__file__).resolve().parents[2]
    candidates = [root / "pkgs" / "broker" / "policy.py", pathlib.Path("broker/policy.py")]
    src = next(p for p in candidates if p.exists())
    spec = importlib.util.spec_from_file_location("policy", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["policy"] = mod
    spec.loader.exec_module(mod)
    return mod.EgressPolicy(), policy["audit_log"]


def https_flow(host, path="/x", sni=None):
    f = tflow.tflow()
    f.request.scheme = "https"
    f.request.host = host
    f.request.port = 443
    f.request.path = path
    f.client_conn.sni = sni if sni is not None else host
    return f


def audit_lines(audit_path):
    p = pathlib.Path(audit_path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines()]


def test_denies_non_allowlisted_host(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    addon.request(f)
    assert f.response is not None
    assert f.response.status_code == 403
    recs = audit_lines(audit)
    assert len(recs) == 1
    assert recs[0]["verdict"] == "deny"
    assert recs[0]["host"] == "evil.test"
    assert recs[0]["instance"] == "t"


def test_allowlisted_host_passes_and_audits_on_response(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("allowed.test")
    addon.request(f)
    assert f.response is None
    f.response = http.Response.make(200, b"ok")
    addon.response(f)
    recs = audit_lines(audit)
    assert len(recs) == 1
    assert recs[0]["verdict"] == "allow"
    assert recs[0]["bytes_in"] == len(b"ok")


def test_no_double_audit_on_denied_flow(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": []}
    )
    f = https_flow("evil.test")
    addon.request(f)
    addon.response(f)
    assert len(audit_lines(audit)) == 1


def test_audit_record_has_exact_fields(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": []}
    )
    addon.request(https_flow("evil.test"))
    (rec,) = audit_lines(audit)
    assert sorted(rec) == sorted(
        [
            "ts",
            "instance",
            "client",
            "method",
            "host",
            "sni",
            "path",
            "bytes_out",
            "bytes_in",
            "verdict",
            "reason",
        ]
    )
```

- [ ] **Step 3: Run to verify failure** — `nix develop -c pytest tests/broker -q` → FAIL (no policy.py).

- [ ] **Step 4: Implement** — `pkgs/broker/policy.py`:

```python
"""Egress broker policy addon for mitmproxy.

Default-deny allowlist, JSONL audit log, credential injection at egress.
All policy comes from the JSON file named by $BROKER_POLICY; this file is
mechanism only. See docs/superpowers/specs 2.3 and brief 5.3.
"""

import json
import os
import time

from mitmproxy import http

DENY_BODY = b"egress-broker: denied\n"


class EgressPolicy:
    def __init__(self):
        with open(os.environ["BROKER_POLICY"], encoding="utf-8") as f:
            policy = json.load(f)
        self.instance = policy["instance"]
        self.allow = set(policy["allow"])
        self.inject = policy.get("inject", {})
        self.audit_log = policy["audit_log"]
        self.secrets = {}
        for host, spec in self.inject.items():
            with open(spec["value_file"], encoding="utf-8") as f:
                self.secrets[host] = f.read().strip()

    def _audit(self, flow, verdict, reason):
        if flow.metadata.get("egress_audited"):
            return
        flow.metadata["egress_audited"] = True
        peer = getattr(flow.client_conn, "peername", None)
        rec = {
            "ts": time.time(),
            "instance": self.instance,
            "client": peer[0] if peer else None,
            "method": flow.request.method,
            "host": flow.request.pretty_host,
            "sni": getattr(flow.client_conn, "sni", None),
            "path": flow.request.path,
            "bytes_out": len(flow.request.raw_content or b""),
            "bytes_in": len(flow.response.raw_content or b"") if flow.response else 0,
            "verdict": verdict,
            "reason": reason,
        }
        with open(self.audit_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def _deny(self, flow, reason):
        flow.response = http.Response.make(
            403, DENY_BODY, {"content-type": "text/plain"}
        )
        self._audit(flow, "deny", reason)

    def http_connect(self, flow):
        if flow.request.pretty_host not in self.allow:
            self._deny(flow, "connect-not-allowlisted")

    def request(self, flow):
        host = flow.request.pretty_host
        sni = getattr(flow.client_conn, "sni", None)
        if host not in self.allow:
            reason = "not-allowlisted"
            if sni and sni != host:
                reason = "host/sni mismatch: sni=%s host=%s" % (sni, host)
            self._deny(flow, reason)
            return
        if host in self.secrets:
            spec = self.inject[host]
            flow.request.headers[spec.get("header", "Authorization")] = (
                spec.get("prefix", "Bearer ") + self.secrets[host]
            )

    def response(self, flow):
        self._audit(flow, "allow", "ok")

    def error(self, flow):
        self._audit(flow, "error", "upstream or client error")


addons = [EgressPolicy()]
```

- [ ] **Step 5: Run tests to verify pass** — `nix develop -c pytest tests/broker -q` → all PASS. Then `nix flake check` (new `addon` check green, lint green after `nix develop -c treefmt`).

- [ ] **Step 6: Commit** — `phase2: broker addon core — default-deny + JSONL audit`

---

### Task 2: Injection + domain-fronting detection tests

**Files:**
- Modify: `tests/broker/test_policy.py` (append tests)
- Modify: `pkgs/broker/policy.py` (only if a test exposes a gap — the Task 1 code already implements both behaviors)

**Interfaces:**
- Consumes/Produces: unchanged from Task 1. This task exists so injection and fronting are *proven*, separately reviewable, not assumed.

- [ ] **Step 1: Write the failing/covering tests** — append to `tests/broker/test_policy.py`:

```python
def test_injects_credential_on_allowlisted_host(tmp_path, monkeypatch):
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value\n")
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "inject": {
                "api.test": {
                    "header": "Authorization",
                    "prefix": "Bearer ",
                    "value_file": str(secret),
                }
            },
        },
    )
    f = https_flow("api.test")
    f.request.headers["Authorization"] = "Bearer BASKET-SENTINEL"
    addon.request(f)
    assert f.response is None
    assert f.request.headers["Authorization"] == "Bearer s3cr3t-value"


def test_never_injects_on_non_inject_host(tmp_path, monkeypatch):
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value")
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["a.test", "b.test"],
            "inject": {"a.test": {"value_file": str(secret)}},
        },
    )
    f = https_flow("b.test")
    f.request.headers["Authorization"] = "Bearer BASKET-SENTINEL"
    addon.request(f)
    assert f.request.headers["Authorization"] == "Bearer BASKET-SENTINEL"


def test_domain_fronting_denied_and_flagged(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("denied.test", sni="allowed.test")
    addon.request(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert "mismatch" in rec["reason"]
    assert rec["sni"] == "allowed.test"
    assert rec["host"] == "denied.test"


def test_connect_denied_and_audited(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    addon.http_connect(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert rec["reason"] == "connect-not-allowlisted"


def test_secret_never_appears_in_audit(tmp_path, monkeypatch):
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value")
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "inject": {"api.test": {"value_file": str(secret)}},
        },
    )
    f = https_flow("api.test")
    addon.request(f)
    f.response = http.Response.make(200, b"ok")
    addon.response(f)
    assert "s3cr3t-value" not in pathlib.Path(audit).read_text()
```

- [ ] **Step 2: Run** — `nix develop -c pytest tests/broker -q`. Expected: PASS against Task 1's implementation; any FAIL is a real gap — fix `policy.py` minimally and note it.

- [ ] **Step 3: Lint + commit** — `nix develop -c treefmt && nix flake check`, then commit `phase2: prove injection + domain-fronting denial`.

---

### Task 3: NixOS module — netns, veth, nftables, hardened service

**Files:**
- Create: `nixosModules/egressBroker.nix`
- Modify: `flake.nix` (export `nixosModules.egressBroker`; add `checks.module-eval`)

**Interfaces:**
- Produces: `services.egress-broker.instances.<name>` with options: `hostAddress` (str), `namespaceAddress` (str), `prefixLength` (int, default 30), `listenPort` (port, default 3128), `allow` (listOf str), `inject` (attrsOf submodule `{ header ? "Authorization", prefix ? "Bearer ", valueFile }`). Per instance the module creates: netns `egress-<name>`, veth pair `veb-<name>` (host) / `ven-<name>` (in netns), nftables rules restricting the netns to the broker port, and systemd service `egress-broker-<name>` running `mitmdump` with the Task 1 addon. CA cert for clients lands at `/var/lib/egress-broker/<name>/ca/mitmproxy-ca-cert.pem`; audit at `/var/lib/egress-broker/<name>/audit.jsonl`. Tasks 4–5 consume exactly these names and paths.

- [ ] **Step 1: Write the module** — `nixosModules/egressBroker.nix`:

```nix
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.egress-broker;
  policyFile =
    name: i:
    (pkgs.formats.json { }).generate "egress-policy-${name}.json" {
      instance = name;
      allow = i.allow;
      inject = lib.mapAttrs (_: s: {
        inherit (s) header prefix;
        value_file = s.valueFile;
      }) i.inject;
      audit_log = "/var/lib/egress-broker/${name}/audit.jsonl";
    };
in
{
  options.services.egress-broker.instances = lib.mkOption {
    default = { };
    description = "Per-netns TLS-terminating egress brokers.";
    type = lib.types.attrsOf (
      lib.types.submodule {
        options = {
          hostAddress = lib.mkOption { type = lib.types.str; };
          namespaceAddress = lib.mkOption { type = lib.types.str; };
          prefixLength = lib.mkOption {
            type = lib.types.int;
            default = 30;
          };
          listenPort = lib.mkOption {
            type = lib.types.port;
            default = 3128;
          };
          allow = lib.mkOption {
            type = lib.types.listOf lib.types.str;
            default = [ ];
          };
          inject = lib.mkOption {
            default = { };
            type = lib.types.attrsOf (
              lib.types.submodule {
                options = {
                  header = lib.mkOption {
                    type = lib.types.str;
                    default = "Authorization";
                  };
                  prefix = lib.mkOption {
                    type = lib.types.str;
                    default = "Bearer ";
                  };
                  valueFile = lib.mkOption { type = lib.types.str; };
                };
              }
            );
          };
        };
      }
    );
  };

  config = lib.mkIf (cfg.instances != { }) {
    networking.nftables.enable = true;
    networking.nftables.tables.egress-broker = {
      family = "inet";
      content = lib.concatStrings (
        lib.mapAttrsToList (name: i: ''
          chain input-${name} {
            type filter hook input priority filter - 1;
            iifname "veb-${name}" tcp dport ${toString i.listenPort} ip saddr ${i.namespaceAddress} accept
            iifname "veb-${name}" ct state established,related accept
            iifname "veb-${name}" drop
          }
          chain forward-${name} {
            type filter hook forward priority filter - 1;
            iifname "veb-${name}" drop
            oifname "veb-${name}" drop
          }
        '') cfg.instances
      );
    };

    systemd.services = lib.mkMerge (
      lib.mapAttrsToList (name: i: {
        "egress-netns-${name}" = {
          description = "Network namespace and veth for egress broker ${name}";
          wantedBy = [ "multi-user.target" ];
          before = [ "egress-broker-${name}.service" ];
          path = [ pkgs.iproute2 ];
          serviceConfig = {
            Type = "oneshot";
            RemainAfterExit = true;
          };
          script = ''
            ip netns add egress-${name}
            ip link add veb-${name} type veth peer name ven-${name}
            ip link set ven-${name} netns egress-${name}
            ip addr add ${i.hostAddress}/${toString i.prefixLength} dev veb-${name}
            ip link set veb-${name} up
            ip netns exec egress-${name} ip addr add ${i.namespaceAddress}/${toString i.prefixLength} dev ven-${name}
            ip netns exec egress-${name} ip link set ven-${name} up
            ip netns exec egress-${name} ip link set lo up
            ip netns exec egress-${name} ip route add default via ${i.hostAddress}
          '';
          preStop = ''
            ip link del veb-${name} || true
            ip netns del egress-${name} || true
          '';
        };
        "egress-broker-${name}" = {
          description = "TLS-terminating egress broker ${name}";
          wantedBy = [ "multi-user.target" ];
          requires = [ "egress-netns-${name}.service" ];
          after = [
            "egress-netns-${name}.service"
            "network.target"
          ];
          environment.BROKER_POLICY = policyFile name i;
          serviceConfig = {
            ExecStart = lib.concatStringsSep " " [
              "${pkgs.mitmproxy}/bin/mitmdump"
              "--mode regular"
              "--listen-host ${i.hostAddress}"
              "--listen-port ${toString i.listenPort}"
              "--set confdir=/var/lib/egress-broker/${name}/ca"
              "--set connection_strategy=lazy"
              "-s ${../pkgs/broker/policy.py}"
            ];
            StateDirectory = "egress-broker/${name} egress-broker/${name}/ca";
            User = "egress-broker";
            Group = "egress-broker";
            NoNewPrivileges = true;
            ProtectSystem = "strict";
            ProtectHome = true;
            PrivateTmp = true;
            RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX";
            CapabilityBoundingSet = "";
            AmbientCapabilities = "";
            LockPersonality = true;
            MemoryDenyWriteExecute = false;
            Restart = "on-failure";
          };
        };
      }) cfg.instances
    );

    users.users.egress-broker = {
      isSystemUser = true;
      group = "egress-broker";
    };
    users.groups.egress-broker = { };
  };
}
```

- [ ] **Step 2: Export + eval-check in `flake.nix`** — add at top level of outputs:

```nix
      nixosModules.egressBroker = import ./nixosModules/egressBroker.nix;
```

and a check that the module evaluates inside a minimal system:

```nix
        module-eval =
          (nixpkgs.lib.nixosSystem {
            inherit system;
            modules = [
              self.nixosModules.egressBroker
              (
                { ... }:
                {
                  boot.loader.grub.enable = false;
                  fileSystems."/".device = "none";
                  fileSystems."/".fsType = "tmpfs";
                  system.stateVersion = "25.11";
                  services.egress-broker.instances.smoke = {
                    hostAddress = "10.100.0.1";
                    namespaceAddress = "10.100.0.2";
                    allow = [ "example.com" ];
                  };
                }
              )
            ];
          }).config.system.build.toplevel;
```

- [ ] **Step 3: Verify red→green** — `nix flake check` must fail before the module exists (the check references it), pass after. Lint clean (`statix`, `deadnix`, `nixfmt` via treefmt).

- [ ] **Step 4: Commit** — `phase2: egressBroker NixOS module (netns, veth, nftables, hardened mitmdump)`

---

### Task 4: In-VM integration test (brief §7 Phase 2, automated)

**Files:**
- Create: `tests/integration/broker-vm.nix`
- Modify: `flake.nix` (`checks.integration`)

**Interfaces:**
- Consumes: `nixosModules.egressBroker`, addon behavior from Tasks 1–2.
- Produces: `checks.x86_64-linux.integration` — a `pkgs.testers.runNixOSTest` VM that proves: allowlisted curl succeeds through the broker; non-allowlisted fails 403; both appear in the audit log with correct verdicts; a domain-fronted request is denied; an injected credential reaches the upstream. Requires KVM on the builder (present on core).

- [ ] **Step 1: Write the test** — `tests/integration/broker-vm.nix`:

```nix
{
  pkgs,
  egressBrokerModule,
}:
let
  testCerts =
    pkgs.runCommand "test-certs"
      {
        nativeBuildInputs = [ pkgs.openssl ];
      }
      ''
        mkdir -p $out
        openssl req -x509 -newkey rsa:2048 -nodes -days 2 \
          -keyout $out/ca.key -out $out/ca.crt -subj "/CN=test-ca"
        for h in allowed.test denied.test; do
          openssl req -newkey rsa:2048 -nodes \
            -keyout $out/$h.key -out $out/$h.csr -subj "/CN=$h"
          openssl x509 -req -in $out/$h.csr -CA $out/ca.crt -CAkey $out/ca.key \
            -CAcreateserial -days 2 -out $out/$h.crt
        done
      '';
in
pkgs.testers.runNixOSTest {
  name = "egress-broker";
  nodes.machine =
    { pkgs, ... }:
    {
      imports = [ egressBrokerModule ];
      security.pki.certificateFiles = [ "${testCerts}/ca.crt" ];
      networking.hosts."127.0.0.1" = [
        "allowed.test"
        "denied.test"
      ];
      services.nginx = {
        enable = true;
        virtualHosts."allowed.test" = {
          onlySSL = true;
          sslCertificate = "${testCerts}/allowed.test.crt";
          sslCertificateKey = "${testCerts}/allowed.test.key";
          locations."/auth".extraConfig = ''
            default_type text/plain;
            return 200 "auth=$http_authorization";
          '';
          locations."/".extraConfig = ''
            default_type text/plain;
            return 200 "ok-allowed";
          '';
        };
        virtualHosts."denied.test" = {
          onlySSL = true;
          sslCertificate = "${testCerts}/denied.test.crt";
          sslCertificateKey = "${testCerts}/denied.test.key";
          locations."/".extraConfig = ''
            default_type text/plain;
            return 200 "should-never-be-reachable";
          '';
        };
      };
      services.egress-broker.instances.agent1 = {
        hostAddress = "10.100.0.1";
        namespaceAddress = "10.100.0.2";
        allow = [ "allowed.test" ];
        inject."allowed.test".valueFile = "/run/broker-secret";
      };
      systemd.services."egress-broker-agent1" = {
        after = [ "broker-secret.service" ];
        requires = [ "broker-secret.service" ];
      };
      systemd.services.broker-secret = {
        wantedBy = [ "multi-user.target" ];
        serviceConfig.Type = "oneshot";
        serviceConfig.RemainAfterExit = true;
        script = ''
          umask 037
          echo "vm-test-secret" > /run/broker-secret
          chown root:egress-broker /run/broker-secret
        '';
      };
      environment.systemPackages = [
        pkgs.curl
        pkgs.jq
      ];
    };
  testScript = ''
    machine.wait_for_unit("nginx.service")
    machine.wait_for_unit("egress-broker-agent1.service")
    machine.wait_until_succeeds(
        "test -f /var/lib/egress-broker/agent1/ca/mitmproxy-ca-cert.pem"
    )

    proxy = "-x http://10.100.0.1:3128 --cacert /var/lib/egress-broker/agent1/ca/mitmproxy-ca-cert.pem"
    curl = "ip netns exec egress-agent1 curl -s " + proxy

    # 1. allowlisted host succeeds through the broker
    out = machine.succeed(curl + " https://allowed.test/")
    assert "ok-allowed" in out, out

    # 2. credential injection reaches the upstream
    out = machine.succeed(curl + " https://allowed.test/auth")
    assert "auth=Bearer vm-test-secret" in out, out

    # 3. non-allowlisted host is denied at CONNECT (curl surfaces a proxy
    #    CONNECT 403 as an error message, not as an HTTP status code)
    out = machine.succeed(curl + " -S https://denied.test/ 2>&1 || true")
    assert "403" in out, out

    # 4. domain fronting: outer name allowed, inner Host denied -> 403
    out = machine.succeed(
        curl + " -H 'Host: denied.test' -o /dev/null -w '%{http_code}' https://allowed.test/ || true"
    )
    assert "403" in out, out

    # 5. audit log carries correct verdicts, and the fronting denial names the mismatch
    machine.succeed(
        "jq -es '[.[] | select(.verdict==\"allow\")] | length >= 2' /var/lib/egress-broker/agent1/audit.jsonl"
    )
    machine.succeed(
        "jq -es '[.[] | select(.verdict==\"deny\" and (.reason | test(\"mismatch\")))] | length >= 1' /var/lib/egress-broker/agent1/audit.jsonl"
    )

    # 6. the netns has no route around the broker: direct traffic fails
    machine.fail(
        "ip netns exec egress-agent1 curl -s --max-time 3 https://allowed.test/"
    )

    # 7. no secret material in the audit log
    machine.fail("grep -q vm-test-secret /var/lib/egress-broker/agent1/audit.jsonl")
  '';
}
```

- [ ] **Step 2: Wire into flake** — in `checks`:

```nix
        integration = import ./tests/integration/broker-vm.nix {
          inherit pkgs;
          egressBrokerModule = self.nixosModules.egressBroker;
        };
```

- [ ] **Step 3: Run** — `nix build .#checks.x86_64-linux.integration -L` (first run also proves red→green if run before Task 3 is merged; here it validates the whole stack). Fix real failures minimally; report every deviation. Then full `nix flake check`.

- [ ] **Step 4: Commit** — `phase2: VM integration test — allow/deny/audit/fronting/injection/no-bypass`

---

### Task 5: Operator acceptance script + runbook

**Files:**
- Create: `tests/acceptance/phase2.sh`
- Create: `docs/runbooks/phase2-acceptance.md`
- Modify: `README.md` (status paragraph)

**Interfaces:**
- Consumes: `pkgs/broker/policy.py`, devShell (mitmproxy via `brokerPython`), iproute2 on host.
- Produces: the brief §7 Phase 2 acceptance, on real hardware and real internet, transient (nothing persists): creates a throwaway netns + veth, runs `mitmdump` with the addon and a policy allowing exactly `example.com`, then from inside the netns proves allow / deny / fronting-denial / audit verdicts, and tears everything down.

- [ ] **Step 1: Write `tests/acceptance/phase2.sh`**

```bash
#!/usr/bin/env bash
# Phase 2 acceptance (brief §7): from inside a netns, an allowlisted host
# succeeds via the broker, a non-allowlisted host fails, both appear in the
# audit log with correct verdicts, and a domain-fronted request is caught by
# TLS termination. Transient: netns, veth, broker and logs are all torn down.
# Run from the repo root: nix develop -c tests/acceptance/phase2.sh
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo --preserve-env=PATH "$0" "$@"
fi

ns=basket-accept
work=$(mktemp -d)
broker_pid=""
cleanup() {
  if [[ -n "$broker_pid" ]]; then kill "$broker_pid" 2>/dev/null || true; fi
  ip link del veb-accept 2>/dev/null || true
  ip netns del "$ns" 2>/dev/null || true
  rm -rf "$work"
}
trap cleanup EXIT
pass=0
fail=0
ok() {
  echo "   PASS: $1"
  pass=$((pass + 1))
}
bad() {
  echo "   FAIL: $1"
  fail=$((fail + 1))
}

echo "== setup: throwaway netns + veth + broker (allow: example.com only)"
ip netns add "$ns"
ip link add veb-accept type veth peer name ven-accept
ip link set ven-accept netns "$ns"
ip addr add 10.200.0.1/30 dev veb-accept
ip link set veb-accept up
ip netns exec "$ns" ip addr add 10.200.0.2/30 dev ven-accept
ip netns exec "$ns" ip link set ven-accept up
ip netns exec "$ns" ip link set lo up
ip netns exec "$ns" ip route add default via 10.200.0.1

cat >"$work/policy.json" <<EOF
{ "instance": "acceptance", "allow": ["example.com"],
  "inject": {}, "audit_log": "$work/audit.jsonl" }
EOF
BROKER_POLICY="$work/policy.json" mitmdump --mode regular \
  --listen-host 10.200.0.1 --listen-port 3128 \
  --set "confdir=$work/ca" -s pkgs/broker/policy.py \
  >"$work/mitmdump.log" 2>&1 &
broker_pid=$!
for _ in $(seq 1 50); do
  if [[ -f "$work/ca/mitmproxy-ca-cert.pem" ]]; then break; fi
  sleep 0.2
done
[[ -f "$work/ca/mitmproxy-ca-cert.pem" ]] || {
  echo "broker failed to start:" >&2
  cat "$work/mitmdump.log" >&2
  exit 1
}

curl_ns() {
  ip netns exec "$ns" curl -s -x http://10.200.0.1:3128 \
    --cacert "$work/ca/mitmproxy-ca-cert.pem" "$@"
}

echo
echo "== 1. allowlisted host succeeds from inside the netns"
if curl_ns -o /dev/null -w '%{http_code}' https://example.com/ | grep -q 200; then
  ok "https://example.com reachable via broker"
else
  bad "allowlisted request failed"
fi

echo
echo "== 2. non-allowlisted host is refused"
# a proxy CONNECT 403 surfaces as a curl error message, not an HTTP code
out=$(curl_ns -S https://github.com/ 2>&1 || true)
if [[ "$out" == *"403"* ]]; then
  ok "https://github.com refused (CONNECT 403 from broker)"
else
  bad "expected CONNECT 403, got: $out"
fi

echo
echo "== 3. domain-fronted request is caught by TLS termination"
code=$(curl_ns -H "Host: github.com" -o /dev/null -w '%{http_code}' https://example.com/ || true)
if [[ "$code" == "403" ]]; then
  ok "fronted request (outer example.com, inner github.com) refused"
else
  bad "fronted request not refused (got: $code)"
fi

echo
echo "== 4. no route around the broker exists"
if ip netns exec "$ns" curl -s --max-time 3 https://example.com/ >/dev/null 2>&1; then
  bad "direct internet access from netns should be impossible"
else
  ok "direct (non-broker) egress from the netns fails"
fi

echo
echo "== 5. audit log verdicts"
allow_n=$(jq -s '[.[] | select(.verdict=="allow")] | length' "$work/audit.jsonl")
deny_n=$(jq -s '[.[] | select(.verdict=="deny")] | length' "$work/audit.jsonl")
mismatch_n=$(jq -s '[.[] | select(.reason | test("mismatch"))] | length' "$work/audit.jsonl")
if [[ "$allow_n" -ge 1 && "$deny_n" -ge 2 && "$mismatch_n" -ge 1 ]]; then
  ok "audit shows $allow_n allow, $deny_n deny (incl. $mismatch_n fronting mismatch)"
else
  bad "audit verdicts wrong: allow=$allow_n deny=$deny_n mismatch=$mismatch_n"
fi
echo
echo "--- audit log (for your review):"
jq -c '{host, sni, verdict, reason}' "$work/audit.jsonl" || true

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "PHASE 2 ACCEPTANCE: PASS"
else
  echo "PHASE 2 ACCEPTANCE: FAIL"
  exit 1
fi
```

Note: the script re-execs itself under sudo with PATH preserved so `mitmdump`, `jq`, `curl` come from the devShell.

- [ ] **Step 2: Static-verify** — `nix develop -c shellcheck tests/acceptance/phase2.sh` → clean.

- [ ] **Step 3: Write `docs/runbooks/phase2-acceptance.md`** — operator-facing:

```markdown
# Phase 2 acceptance — what you run

One command from the repo root (it will ask for sudo once):

    nix develop -c tests/acceptance/phase2.sh

It builds a temporary isolated network bubble, starts the traffic chokepoint
for it, and proves from inside the bubble that: the one allowed website works,
everything else is refused, a disguised request (allowed name outside, banned
name inside) is caught, there is no way around the chokepoint, and every
attempt landed in the audit log with the right verdict. Everything is torn
down when it exits — nothing persists.

Expected final line: `PHASE 2 ACCEPTANCE: PASS`.
```

- [ ] **Step 4: README status** — replace the status paragraph with: Phase 2 implemented (broker addon, NixOS module, VM integration test green); awaiting operator acceptance via `nix develop -c tests/acceptance/phase2.sh`.

- [ ] **Step 5: Full verification + commit** — `nix flake check` (lint, unit, addon, module-eval, integration all green), `nix develop -c bats tests/unit`, `nix develop -c tests/run-mount-tests.sh` (Phase 1 must stay green). Commit: `phase2: operator acceptance runbook (test: brief §7 Phase 2)`.

---

## Verification (whole phase)

1. `nix flake check` → lint, unit, addon, module-eval, integration all green.
2. `nix develop -c pytest tests/broker -q` → all addon tests pass.
3. `nix build .#checks.x86_64-linux.integration -L` → VM test passes (KVM).
4. Phase 1 suites still green (`bats tests/unit`, `tests/run-mount-tests.sh`).
5. Operator: `nix develop -c tests/acceptance/phase2.sh` → `PHASE 2 ACCEPTANCE: PASS`.
