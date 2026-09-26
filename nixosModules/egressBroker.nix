{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.egress-broker;
  # The exact attrset serialized into each instance's $BROKER_POLICY JSON
  # file. This is the Nix->wire-format mapping: bodyPatch.pathPrefixes ->
  # body_patch.<host>.path_prefixes, inject.<host>.valueFile ->
  # inject.<host>.value_file, etc. Shared by policyFile (the on-disk
  # derivation) and the internal read-only `policy` option below so the wire
  # format is testable at eval time without reading the derivation (no IFD).
  renderPolicy = name: i: {
    instance = name;
    inherit (i) allow;
    inject = lib.mapAttrs (_: s: {
      inherit (s) header prefix paths;
      value_file = s.valueFile;
    }) i.inject;
    body_patch = lib.mapAttrs (_: b: {
      path_prefixes = b.pathPrefixes;
      inherit (b) merge;
    }) i.bodyPatch;
    deny_paths = lib.mapAttrs (_: d: {
      path_prefixes = d.pathPrefixes;
    }) i.denyPaths;
    audit_log = "/var/lib/egress-broker/${name}/audit.jsonl";
    usage_log = "/var/lib/egress-broker/${name}/usage.jsonl";
    usage_path_prefixes = i.usagePathPrefixes;
  };
  policyFile =
    name: i: (pkgs.formats.json { }).generate "egress-policy-${name}.json" (renderPolicy name i);
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
          usagePathPrefixes = lib.mkOption {
            type = lib.types.listOf lib.types.str;
            default = [ "/api/v1/chat/completions" ];
            description = ''
              Request path prefixes whose responses the policy addon records
              usage for (one JSONL line per flow beside the audit line). The
              completions path is the only place a usage frame appears; every
              other SSE path keeps the plain `True` stream behaviour.
            '';
          };
          bodyPatch = lib.mkOption {
            default = { };
            description = "Per host: a JSON object merged (policy keys win) into every JSON request body whose path starts with any of pathPrefixes -- the data policy enforced at the chokepoint for every client of this instance, e.g. OpenRouter zero-data-retention routing (brief §3 invariant 5).";
            type = lib.types.attrsOf (
              lib.types.submodule {
                options = {
                  pathPrefixes = lib.mkOption {
                    type = lib.types.listOf lib.types.str;
                    default = [ "/" ];
                    description = "Path prefixes this host's body patch is applied to; default [ \"/\" ] = every path.";
                  };
                  merge = lib.mkOption {
                    type = lib.types.attrs;
                    default = { };
                  };
                };
              }
            );
          };
          denyPaths = lib.mkOption {
            default = { };
            description = ''
              Per host: path prefixes this instance never forwards. A request
              whose path starts with any of a host's pathPrefixes is denied
              at requestheaders (before credential injection) with audit
              reason "path-not-permitted" and nothing reaches upstream. The
              fail-closed denylist for endpoints no client of this instance
              may use -- e.g. OpenRouter's Anthropic-style /api/v1/messages,
              which nothing consumes (the seat and the lane both use chat
              completions; O3 resolved: fail closed). Empty by default:
              only paths explicitly listed are denied.
            '';
            type = lib.types.attrsOf (
              lib.types.submodule {
                options = {
                  pathPrefixes = lib.mkOption {
                    type = lib.types.listOf lib.types.str;
                    default = [ ];
                    description = ''
                      Path prefixes denied on this host; default [ ] = deny
                      nothing. Match is prefix-based, the same startswith
                      semantics as bodyPatch's pathPrefixes.
                    '';
                  };
                };
              }
            );
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
                  paths = lib.mkOption {
                    type = lib.types.listOf lib.types.str;
                    default = [ "/" ];
                    description = "Path prefixes this host's credential is injected on; default [ \"/\" ] = every path. Independent of bodyPatch's prefix list: scoping injection to the patched path only would strip the credential from the agent lane's other calls.";
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

  options.services.egress-broker.policy = lib.mkOption {
    readOnly = true;
    internal = true;
    type = lib.types.attrsOf lib.types.attrs;
    description = ''
      The generated broker policy attrset, one entry per instance, exactly as
      policyFile serializes it to JSON. Read-only and internal: exposed so
      checks (e.g. checks.host-core) can assert the Nix->wire-format mapping
      (bodyPatch.pathPrefixes -> body_patch.<host>.path_prefixes,
      inject.<host>.paths, etc.) at eval time without importing the JSON
      derivation (IFD). Never set by users.
    '';
  };

  config = lib.mkIf (cfg.instances != { }) {
    services.egress-broker.policy = lib.mapAttrs renderPolicy cfg.instances;

    networking = {
      nftables.enable = true;
      # NixOS's own nixos-fw input chain (priority 0) is a separate base chain
      # on the same "input" hook as input-${name} below (priority -1): nftables
      # evaluates every base chain on a hook, so an accept in one chain does not
      # short-circuit a drop in another. Without this, nixos-fw's default-drop
      # policy silently drops the netns's own SYN to the broker port before it
      # ever reaches mitmproxy.
      firewall.interfaces = lib.mapAttrs' (
        name: i: lib.nameValuePair "veb-${name}" { allowedTCPPorts = [ i.listenPort ]; }
      ) cfg.instances;
      nftables.tables.egress-broker = {
        family = "inet";
        content = lib.concatStrings (
          lib.mapAttrsToList (name: i: ''
            chain input-${name} {
              type filter hook input priority filter - 1;
              # The broker injects a credential (inject.header, keyed only by
              # destination host) into any request that reaches it -- anything
              # that can complete the TCP handshake to hostAddress:listenPort
              # can spend it (brief §3 invariant 2's spirit). A process in the
              # HOST namespace connecting to this host's own address routes in
              # over "lo", not "veb-${name}" -- so the accept-only rules below
              # (scoped to iifname veb-${name}) never see it, and it would
              # otherwise fall through to nixos-fw's own input chain (priority
              # 0, same hook, a separate base chain this one does not
              # short-circuit), which accepts "lo" traffic in ITS chain. This
              # drop has to run first and in THIS chain, matched by
              # destination rather than by (absent) interface, to close that
              # gap. Binding mitmproxy's listener inside the netns instead of
              # `--listen-host ${i.hostAddress}` would remove the host-routable
              # address entirely, but moves the proxy's own network stack into
              # a namespace this module does not yet manage that way --
              # deferred, this drop is the backstop until then.
              ip daddr ${i.hostAddress} tcp dport ${toString i.listenPort} iifname != "veb-${name}" drop
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
            # Canonical CA export: mitmproxy's confdir filenames vary by
            # version (12.x emitted only .cer/.p12 here — field bug
            # 2026-09-02); consumers must reference ONLY ca.pem, which this
            # guarantees shortly after start. .cer content is PEM.
            ExecStartPost = pkgs.writeShellScript "egress-broker-export-ca" ''
              set -euo pipefail
              dir=/var/lib/egress-broker/${name}/ca
              # T2 fix round (Opus re-gate of 90d9e86): a consumer whose own
              # sandbox hides the whole /var/lib/egress-broker tree with
              # InaccessiblePaths (nixosModules/modelLane.nix does, so the
              # confdir's private key material is never stat()-able by a
              # network-capable process -- brief §3 invariant 2) still needs
              # to read this ONE public file to verify TLS through its own
              # broker. Publishing a second copy at a sibling top-level
              # directory -- not a subpath of /var/lib/egress-broker -- means
              # a consumer can hide the whole instance tree and still read
              # its CA bundle, with no BindReadOnlyPaths-through-an-
              # InaccessiblePaths-mount to reason about. publicDir is created
              # 0755 by this unit's own StateDirectory (default
              # StateDirectoryMode) -- world-traversable/readable, same as
              # the file itself below; it never holds anything but this
              # public bundle.
              publicDir=/var/lib/egress-broker-ca-bundle/${name}
              for _ in $(seq 1 30); do
                for src in mitmproxy-ca-cert.pem mitmproxy-ca-cert.cer; do
                  if [ -s "$dir/$src" ]; then
                    cp "$dir/$src" "$dir/ca.pem.tmp"
                    chmod 0644 "$dir/ca.pem.tmp"
                    mv "$dir/ca.pem.tmp" "$dir/ca.pem"
                    # Cowork's VM helper (readSystemCACertificates /
                    # installHostCACertificates, per
                    # docs/research-2026-09-02-cowork-sending-hang.md) reads
                    # the HOST file /etc/ssl/certs/ca-certificates.crt and
                    # pushes every cert in it into the guest's trust store
                    # (update-ca-certificates --fresh). The broker CA alone
                    # lives only in ca.pem above, so build the file
                    # cowork.nix's BindReadOnlyPaths overlays onto that exact
                    # host path inside cowork.service's own mount namespace:
                    # the system bundle the guest already expects, plus this
                    # broker's CA appended.
                    cat /etc/ssl/certs/ca-certificates.crt "$dir/ca.pem" > "$dir/ca-bundle.crt.tmp"
                    chmod 0644 "$dir/ca-bundle.crt.tmp"
                    mv "$dir/ca-bundle.crt.tmp" "$dir/ca-bundle.crt"
                    cp "$dir/ca-bundle.crt" "$publicDir/ca-bundle.crt.tmp"
                    chmod 0644 "$publicDir/ca-bundle.crt.tmp"
                    mv "$publicDir/ca-bundle.crt.tmp" "$publicDir/ca-bundle.crt"
                    exit 0
                  fi
                done
                sleep 1
              done
              echo "egress-broker(${name}): no CA certificate appeared in $dir" >&2
              exit 1
            '';
            ExecStart = lib.concatStringsSep " " [
              "${pkgs.mitmproxy}/bin/mitmdump"
              "--mode regular"
              "--listen-host ${i.hostAddress}"
              "--listen-port ${toString i.listenPort}"
              "--set confdir=/var/lib/egress-broker/${name}/ca"
              "--set connection_strategy=lazy"
              "--set ssl_verify_upstream_trusted_ca=/etc/ssl/certs/ca-certificates.crt"
              # mitmproxy buffers every body by default (stream_large_bodies
              # unset); Cowork's VM image download alone is 1.3 GB, so an
              # unbuffered body would sit at zero progress for its whole
              # duration and any streamed API response (SSE) would look
              # totally silent. Anything over 1 MiB streams instead of
              # buffering; SSE specifically is also forced to stream
              # regardless of size by the policy addon's responseheaders
              # hook (mitmproxy's own server_side_events addon only warns
              # about this, issue #4469 -- see
              # docs/research-2026-09-02-cowork-sending-hang.md). This
              # streams REQUEST bodies too (mitmproxy applies the same
              # threshold to both directions), which is why policy.py's
              # credential injection runs from requestheaders() rather than
              # request() (headers already left for a streamed body by the
              # time request() fires), and why its deny path kills a flow
              # whose request body might stream instead of answering it with
              # a 403: mitmproxy cannot both set a response and stream (or
              # even buffer-then-restream past this same 1m limit) a
              # request body, so a 403 is only safe for bodies policy.py can
              # bound at or under this threshold -- see policy.py's
              # _deny_request docstring.
              "--set stream_large_bodies=1m"
              "-s ${../pkgs/broker/policy.py}"
            ];
            StateDirectory = "egress-broker/${name} egress-broker/${name}/ca egress-broker-ca-bundle/${name}";
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
