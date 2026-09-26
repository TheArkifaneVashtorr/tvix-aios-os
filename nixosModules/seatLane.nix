{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.seat-lane;
  seatRun = (pkgs.callPackage ../pkgs/seat { }).seat-run;
  # The seat's public CA bundle: the same sibling-path (not a subpath of
  # /var/lib/egress-broker) that modelLane.nix reads, published by
  # egressBroker.nix's ExecStartPost so InaccessiblePaths can hide the whole
  # instance tree (its private CA key + audit log) without cutting off the one
  # file the seat's network-capable process still needs to verify TLS through
  # its own broker (brief §3 invariant 2). See modelLane.nix's caBundle
  # comment for the full reasoning -- copied verbatim here.
  caBundle = "/var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt";
  netnsPath = "/run/netns/egress-seat";
  # SD5: seat-submit joins seat-run on the unit's PATH so a job can submit a
  # follow-on job from inside the sandbox (the spool, SD6, is the one host
  # actor the seat may reach -- never systemd).
  seatSubmit = (pkgs.callPackage ../pkgs/seat { }).seat-submit;
  # SD6: the spool validator -- the one host-side actor the seat may reach.
  # seat-spool.service runs it as root (no User=) so it may start seat@ units;
  # seat-spool.path watches /var/lib/seat/spool and fires it per marker.
  seatSpool = (pkgs.callPackage ../pkgs/seat { }).seat-spool;
in
{
  options.services.seat-lane = {
    enable = lib.mkEnableOption "the operator's DeepSeek seat behind its own egress broker (instance 'seat', netns egress-seat, seat@<job> units)";
    host = lib.mkOption {
      type = lib.types.str;
      default = "openrouter.ai";
      description = "The single upstream hostname the seat's broker instance allows.";
    };
    keyFile = lib.mkOption {
      type = lib.types.str;
      description = ''
        Path to the API key file the broker injects for `host`. Must be
        outside /nix/store -- a store path would copy the secret into the
        world-readable store (asserted below). Never read by this module;
        consumed only by services.egress-broker.instances.seat.inject.
      '';
    };
    hostAddress = lib.mkOption {
      type = lib.types.str;
      description = "Host-side veth address for the seat's broker instance (10.100.4.1).";
    };
    namespaceAddress = lib.mkOption {
      type = lib.types.str;
      description = "Netns-side veth address for the seat's broker instance (10.100.4.2) -- where the web UI binds.";
    };
    listenPort = lib.mkOption {
      type = lib.types.port;
      description = "Port the broker listens on inside the seat's netns.";
    };
    operatorUser = lib.mkOption {
      type = lib.types.str;
      description = "The human operator the seat units run as (and who may start/stop seat@* via polkit).";
    };
    webPortRange = lib.mkOption {
      type = lib.types.str;
      default = "43200-43299";
      description = "The `tcp dport` range (a-b) the web UI may bind, allowed host -> namespace.";
    };
    harnessPackage = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ../pkgs/dsh-openrouter { dsh = pkgs.callPackage ../pkgs/dsh { }; };
      description = "The harness on the seat unit's PATH (dsh-openrouter, bound to OpenRouter through the seat's broker).";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      # keyFile must never be a store path -- a types.path value, or a literal
      # starting with /nix/store, would copy the secret into the world-readable
      # Nix store (copied from modelLane.nix, applied to the single seat).
      {
        assertion = !(lib.hasPrefix "/nix/store" cfg.keyFile);
        message = "services.seat-lane.keyFile must be a path outside /nix/store, got '${cfg.keyFile}'";
      }
      # Another consumer declaring its own services.egress-broker.instances.seat
      # would merge `allow` lists; the seat's contract is one host, one
      # instance, so pin it exactly.
      {
        assertion = config.services.egress-broker.instances.seat.allow == [ cfg.host ];
        message = "services.seat-lane: egress-broker instance 'seat' allow list must be exactly [ \"${cfg.host}\" ] -- check for another consumer declaring an egress-broker instance named 'seat'";
      }
      # No seat or agent process may ever hold a key in its environment: the
      # placeholder OPENROUTER_API_KEY=injected-by-broker is the only
      # credential-shaped value allowed (the broker replaces the header). This
      # catches a config (or a merge) that sneaks a real key into any of the
      # unit's environment entries.
      {
        assertion =
          !(lib.any (v: lib.hasInfix "sk-or-" v) (
            lib.attrValues config.systemd.services."seat@".environment
          ));
        message = "services.seat-lane: the seat@ unit environment must never contain an API key (regex sk-or-) -- the broker injects the credential at egress";
      }
    ];

    services.egress-broker.instances.seat = {
      inherit (cfg) hostAddress namespaceAddress listenPort;
      allow = [ cfg.host ];
      inject.${cfg.host}.valueFile = cfg.keyFile;
      # Data policy at the chokepoint (decision
      # docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md,
      # copied verbatim from modelLane.nix): every chat request to this host
      # gets zero-data-retention routing and the training opt-out, whatever the
      # client put in its body.
      bodyPatch.${cfg.host} = {
        pathPrefixes = [ "/api/v1/chat/completions" ];
        merge.provider = {
          zdr = true;
          data_collection = "deny";
        };
      };
      # Fail closed (O3 resolved): deny OpenRouter's Anthropic-style
      # /api/v1/messages before the key is injected -- same as the lane.
      denyPaths.${cfg.host} = {
        pathPrefixes = [ "/api/v1/messages" ];
      };
    };

    systemd = {
      tmpfiles.rules = [
        # The spool: seat-submit (the operator) writes jobs, seat-run (the unit,
        # also the operator) writes results back under the job dir. 0750 for the
        # root so the operator can reach it; 0700 jobs/ keeps payloads
        # operator-only.
        "d /var/lib/seat 0750 ${cfg.operatorUser} users -"
        "d /var/lib/seat/jobs 0700 ${cfg.operatorUser} -"
        # SD5: the wrapper's writable cache root (DSH_CACHE_ROOT). 0700
        # operator-only: the harness's and nix's fetch caches (code the seat may
        # execute) are never world-readable. It must exist before the first job
        # (the wrapper's mkdir runs under set -e, so a missing/unwritable root
        # would kill the launch -- Assumption 10).
        "d /var/lib/seat/cache 0700 ${cfg.operatorUser} users -"
        # SD6: the spool. 0730 root:users -- the operator (group users) may
        # create a marker but cannot list; seat-spool (root) removes markers.
        "d /var/lib/seat/spool 0730 root users -"
        # SB4b (module bug 2): the broker (egress-broker) reads the injected
        # key at cfg.keyFile on every startup. The file itself is 0440
        # root:egress-broker (the lane module's own tmpfiles rule, shared key
        # file); but the directory that holds it must also be traversable by
        # the broker or mitmproxy crash-loops on PermissionError. Root owns it,
        # group egress-broker may traverse (reach a known file, never list its
        # siblings) -- never 0700 root-only. The seat module declares this so a
        # fresh machine has a traversable secrets dir without the operator's
        # one-time hand step.
        "d /var/lib/secrets 0710 root egress-broker -"
      ];

      services."seat@" = {
        description = "Operator seat job %i behind its own egress broker";
        requires = [
          "egress-netns-seat.service"
          "egress-broker-seat.service"
        ];
        after = [
          "egress-netns-seat.service"
          "egress-broker-seat.service"
        ];
        environment = {
          HTTPS_PROXY = "http://${cfg.hostAddress}:${toString cfg.listenPort}";
          HTTP_PROXY = "http://${cfg.hostAddress}:${toString cfg.listenPort}";
          NO_PROXY = "127.0.0.1,${cfg.namespaceAddress}";
          NODE_EXTRA_CA_CERTS = caBundle;
          SSL_CERT_FILE = caBundle;
          # The broker replaces the Authorization header at egress; this
          # placeholder is what reaches the wrapper (never a real key).
          OPENROUTER_API_KEY = "injected-by-broker";
          FACTORY_ROUTING_TABLE = "/home/${cfg.operatorUser}/nixos-agent-env/docs/ledger/routing.toml";
          # The wrapper's house-guard default resolves through $HOME
          # (dsh-openrouter.sh: house_guard=${FACTORY_HOUSE_GUARD:-$HOME/...}).
          # The unit pins the tree's copy explicitly so a job's HOME cannot
          # move it — the guard must be the checkout the unit's rules protect.
          FACTORY_HOUSE_GUARD = "/home/${cfg.operatorUser}/nixos-agent-env/tools/orchestrator-guard.sh";
          # Node >= 24 honours HTTPS_PROXY only with this (undici
          # EnvHttpProxyAgent), so the harness's model calls tunnel through the
          # broker like every other client in this namespace (plan amendment 3).
          NODE_USE_ENV_PROXY = "1";
          # seat-run reads this to bind the web UI and print/file its URL.
          SEAT_NAMESPACE_ADDRESS = cfg.namespaceAddress;
          # SD5: the wrapper's cache root (dsh-openrouter.sh's DSH_CACHE_ROOT,
          # default /tmp). /tmp is read-only under ProtectSystem=strict, so the
          # harness's and nix's caches must land in a directory the unit may
          # write; tmpfiles creates it 0700 operator-only (rule above).
          DSH_CACHE_ROOT = "/var/lib/seat/cache";
        };
        # SD5: the seat unit can act. /run/current-system/sw (the operator's
        # live profile) gives the unit bash, git, nix and the python3-less
        # driver scripts (factory-task, factory-wave ...) by name -- the lane's
        # same idiom (modelLane.nix puts sw first). `ip` is the wrapper's
        # --broker default-route check (af_netlink, route inspection), and
        # seat-submit lets a job submit the next one into the spool (SD6).
        # (Previously "sw is not needed here": the seat shelled out only to the
        # harness and `ip`; SD5 makes the seat's dsh bash tool spawn `bash` --
        # Assumption 13 -- plus git/nix for a driver job, so the full profile is
        # needed.)
        path = [
          "/run/current-system/sw"
          cfg.harnessPackage
          pkgs.iproute2
          seatSubmit
        ];
        serviceConfig = {
          Type = "simple";
          User = cfg.operatorUser;
          NetworkNamespacePath = netnsPath;
          ExecStart = "${seatRun}/bin/seat-run %i";
          # SB6b: the web forwarder is a background child of the wrapper
          # (dsh-openrouter.sh spawns `socat ... &` before exec'ing node), so it
          # must die with the unit. KillMode=control-group ends every process in
          # the unit's cgroup on stop -- the default `control-group` is the same
          # value, but it is pinned here (seat-eval) because a `process` mode
          # would signal only the main PID and leave the socat forwarder holding
          # the namespace port after the unit stops (proven by seat-vm).
          KillMode = "control-group";
          ProtectSystem = "strict";
          # SB4b (module bug 1): every path below may be ABSENT on a fresh
          # machine (the operator's ~/factory, ~/nixos-agent-env, ~/flakes and
          # ~/.local/share/dsh-openrouter are created by other tooling, not
          # this module). ReadWritePaths= fails the unit at NAMESPACE setup
          # (status 226) when a listed path is missing; the "-" prefix makes
          # systemd tolerate an absent path, so seat@ starts on a machine
          # without any of them.
          ReadWritePaths = [
            "/var/lib/seat"
            "-/home/${cfg.operatorUser}/factory"
            "-/home/${cfg.operatorUser}/nixos-agent-env"
            "-/home/${cfg.operatorUser}/flakes"
            "-/home/${cfg.operatorUser}/.local/share/dsh-openrouter"
          ];
          # OG3r: the file the seat's hook runs as the house guard
          # (FACTORY_HOUSE_GUARD, above) is mounted read-only into every job by
          # a kernel mount — no process in the unit can write it, unlink it, or
          # rename over it (EBUSY), however a command spells its path. The "-"
          # prefix tolerates an absent checkout, exactly as the ReadWritePaths
          # entries do, and the copies under ~/factory/ws (the workspace) are
          # untouched.
          ReadOnlyPaths = [
            "-/home/${cfg.operatorUser}/nixos-agent-env/tools/orchestrator-guard.sh"
          ];
          # brief §3 invariant 2: the broker's injected credentials are never
          # visible to the network-capable seat process. (Unlike the lane, the
          # seat deliberately runs in the operator's own home -- it edits the
          # operator's clones -- so /home is NOT hidden here.)
          #
          # SD5: systemd's two control sockets are ALSO hidden, each mounted
          # over with an inaccessible node (the "-" prefix tolerates absence).
          # They make `systemctl` and any direct systemd control impossible from
          # inside a job -- the spool (SD6) is the one host actor the seat may
          # reach, never the service manager. Proven from inside the template by
          # seat-vm step 9's `systemctl=1`/`dbus=1` probes.
          InaccessiblePaths = [
            "/var/lib/secrets"
            "-/run/systemd/private"
            "-/run/dbus/system_bus_socket"
          ];
          NoNewPrivileges = true;
          # AF_NETLINK: the wrapper's `--broker` route check (`ip route`) must
          # be able to inspect the namespace's default route on every launch
          # (plan amendment 2). AF_INET/AF_INET6/AF_UNIX mirror the lane.
          RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX AF_NETLINK";
        };
      };

      # SD6: the spool is the one host-side actor the seat may reach. A
      # seat-submit --no-start inside a job writes one empty marker into
      # /var/lib/seat/spool; this path unit fires seat-spool.service (root,
      # oneshot) for each. It is a *path* unit (never a template) so a marker --
      # not a job -- is what wakes it, and DirectoryNotEmpty re-arms it for the
      # next marker once this run unlinks the last one.
      paths.seat-spool = {
        wantedBy = [ "paths.target" ];
        pathConfig = {
          DirectoryNotEmpty = "/var/lib/seat/spool";
          Unit = "seat-spool.service";
        };
      };

      # The validator: no shell, no User (runs as root so it may start seat@
      # units); a oneshot that starts exactly one seat@ instance per marker and
      # exits. --systemctl defaults to `systemctl` on root's PATH.
      services.seat-spool = {
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${seatSpool}/bin/seat-spool --jobs-dir /var/lib/seat/jobs --spool-dir /var/lib/seat/spool --owner ${cfg.operatorUser}";
        };
      };
    };

    # The seat's UI reachability rule (plan amendment 1 -- an OUTPUT-hook
    # rule, not input/forward): host-originated traffic out the veb-seat
    # interface may reach the namespace only on the web UI's port range
    # (the operator's browser to 10.100.4.2:<port>), plus the established/
    # related return traffic of the namespace's own connections to the
    # broker. Everything else host -> namespace is dropped here (the
    # namespace -> host direction is already gated by egressBroker's
    # input-<name>/forward-<name> chains). types.lines concatenates this with
    # the chains egressBroker.nix renders for the same table.
    networking.nftables.tables.egress-broker.content = ''
      chain output-seat {
        type filter hook output priority filter - 1;
        oifname "veb-seat" ct state established,related accept
        oifname "veb-seat" ip daddr ${cfg.namespaceAddress} tcp dport ${cfg.webPortRange} accept
        oifname "veb-seat" drop
      }
    '';

    security.polkit.enable = lib.mkDefault true;
    # ES5 (duktape, no template literals / arrow functions): the operator may
    # start, stop and restart seat@<job> units -- unlike the lane (start-only),
    # a web seat must be stoppable and an interrupted job restarted. Every
    # other subject and unit is left to polkit's normal fallthrough.
    security.polkit.extraConfig = ''
      polkit.addRule(function(action, subject) {
        if (action.id == "org.freedesktop.systemd1.manage-units") {
          var verb = action.lookup("verb");
          var unit = action.lookup("unit");
          var prefix = "seat@";
          var suffix = ".service";
          if ((verb == "start" || verb == "stop" || verb == "restart") &&
              unit.indexOf(prefix) === 0 &&
              unit.indexOf(suffix, unit.length - suffix.length) !== -1 &&
              subject.user == "${cfg.operatorUser}") {
            return polkit.Result.YES;
          }
        }
      });
    '';
  };
}
