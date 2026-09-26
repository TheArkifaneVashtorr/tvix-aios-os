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
    helmApiPort = lib.mkOption {
      type = lib.types.nullOr lib.types.port;
      default = null;
      description = ''
        The host-side port the seat's namespace may additionally reach on
        `hostAddress` (answer 11: Helm's v2 API, 7710). `null` leaves the
        namespace's host reach unchanged (broker `listenPort` only). A
        non-null value is refused at eval if it is Helm's control page (7700,
        or whatever `services.helm.port` is) or the broker's own `listenPort`
        — a second accept at a dport `input-seat` already handles is
        unrepresentable (answer 11a). Written to `/etc/seat-lane/helm-api-port`
        when set.
      '';
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
    portRange = lib.mkOption {
      type = lib.types.str;
      default = "43210-43219";
      description = ''
        The `a-b` port range (inclusive) seat-spool allocates web/drive UI
        ports from (SA3, decision 13b; written to /etc/seat-lane/port-range).
        Must hold at least maxUnits ports and lie inside webPortRange
        (asserted below), or the UI is allocated a port the firewall drops or
        the last seat the cap admits is refused.
      '';
    };
    harnessPackage = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ../pkgs/dsh-openrouter { dsh = pkgs.callPackage ../pkgs/dsh { }; };
      description = "The harness on the seat unit's PATH (dsh-openrouter, bound to OpenRouter through the seat's broker).";
    };
    waveJobs = lib.mkOption {
      type = lib.types.int;
      default = 8;
      description = "How many groups one wave runs at once (the wave cap factory-wave enforces). Written to /etc/seat-lane/wave-jobs for factory-wave to read; the unit cap maxUnits derives from it (IS3).";
    };
    maxUnits = lib.mkOption {
      type = lib.types.int;
      default = cfg.waveJobs + 1;
      description = "Maximum number of active/activating seat@* units before seat-spool refuses a launch (IS1, decision 72a; enforced by the spool since IS1c) — seat-submit's started path keeps a second arm. Defaults to waveJobs + 1 because a drive seat is itself a seat@ unit, so a full wave of waveJobs job units plus the driver never meets the cap (IS3). Written to /etc/seat-lane/max-units for seat-spool and seat-submit to read; refused below 1 and at or below waveJobs (assertions).";
    };
    memoryDir = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/evidence/seat-memory";
      description = ''
        The seat's durable memory store (decision 59a): a machine-local
        directory under the evidence store, never a tracked file. Created by
        tmpfiles 0700 operator-only, granted to seat@ as its own explicit
        ReadWritePaths row, and exported to the unit as SEAT_MEMORY_DIR so
        the wrapper links `$DSH_HOME/memory` into it by workspace cwd-key.
        Refused at eval when it lies outside /var/lib/evidence/ (assertion).
      '';
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
      # IS1 (decision 72a): a cap of zero would make seat-submit refuse every
      # launch (fail closed), while a negative cap is meaningless -- refuse both
      # at eval so the operator can never land a broken running-unit cap.
      {
        assertion = cfg.maxUnits >= 1;
        message = "services.seat-lane.maxUnits must be at least 1, got ${toString cfg.maxUnits}";
      }
      # IS3b: a non-positive wave cap would pass this assertion set -- waveJobs
      # = 0 derives maxUnits to 1 and the strict maxUnits > waveJobs relation
      # (1 > 0) still holds -- yet factory-wave:139-141 rejects a non-positive
      # jobs cap at every dispatch, so the operator could land a configuration
      # that breaks every wave run. Refuse it at eval instead.
      {
        assertion = cfg.waveJobs >= 1;
        message = "services.seat-lane.waveJobs must be at least 1, got ${toString cfg.waveJobs} -- factory-wave refuses a non-positive jobs cap";
      }
      # IS3: the unit cap must strictly exceed the wave cap by the driver's own
      # slot. A drive seat is itself a seat@ unit, so a full wave of waveJobs
      # job units plus the driver is waveJobs + 1 units; maxUnits must be at
      # least that, or the cap would refuse the last job the wave cap allows.
      # maxUnits <= waveJobs is therefore unrepresentable at eval.
      {
        assertion = cfg.maxUnits > cfg.waveJobs;
        message = "services.seat-lane.maxUnits (${toString cfg.maxUnits}) must be greater than services.seat-lane.waveJobs (${toString cfg.waveJobs}) -- the unit cap is the wave cap plus the drive seat's own slot";
      }
      # IS20 (answer 11a): helmApiPort must never be Helm's control page (7700,
      # or whatever services.helm.port is) nor the broker's own listenPort — a
      # second accept at a dport input-seat already handles is unrepresentable,
      # and opening the control page would defeat R8's tool-layer refusal of
      # 7700 at the network half.
      {
        assertion =
          cfg.helmApiPort == null
          || (
            cfg.helmApiPort != 7700
            && cfg.helmApiPort != cfg.listenPort
            && cfg.helmApiPort != (config.services.helm.port or 7700)
          );
        message = "services.seat-lane.helmApiPort (${toString cfg.helmApiPort}) must not be Helm's control page (7700 or services.helm.port) nor the broker's listenPort (${toString cfg.listenPort}), answer 11a";
      }
      # SA7 (decision 59a): the seat's memory must be a machine-local store
      # under the evidence store -- never a tracked file, never a hand-made
      # directory anywhere else. Refuse a value outside the store at eval.
      {
        assertion = lib.hasPrefix "/var/lib/evidence/" cfg.memoryDir;
        message = "services.seat-lane.memoryDir must lie under /var/lib/evidence (decision 59a)";
      }
      # SA4: the port range seat-spool allocates from must hold at least
      # maxUnits ports, or the last seat the cap admits is refused the same
      # off-by-one shape IS3 fixed for the caps.
      {
        assertion =
          let
            p = lib.splitString "-" cfg.portRange;
          in
          (lib.toInt (lib.elemAt p 1)) - (lib.toInt (lib.elemAt p 0)) + 1 >= cfg.maxUnits;
        message = "services.seat-lane.portRange (${cfg.portRange}) must hold at least maxUnits (${toString cfg.maxUnits}) ports";
      }
      # SA4: the port range must lie inside webPortRange, or the UI is
      # allocated a port the output-seat firewall chain drops.
      {
        assertion =
          let
            p = lib.splitString "-" cfg.portRange;
            w = lib.splitString "-" cfg.webPortRange;
          in
          lib.toInt (lib.elemAt p 0) >= lib.toInt (lib.elemAt w 0)
          && lib.toInt (lib.elemAt p 1) <= lib.toInt (lib.elemAt w 1);
        message = "services.seat-lane.portRange must lie inside webPortRange (${cfg.webPortRange})";
      }
    ];

    # IS1 (decision 72a): the running-unit cap is published as a file for
    # seat-submit to read -- the mechanism, since no wrapper exists to pass the
    # value (`grep -rn 'wrapProgram\|makeWrapper'` is empty) and seat-submit is
    # a plain package on PATH. The file is the only runtime source besides the
    # SEAT_MAX_UNITS test override.
    #
    # IS3: the wave cap is published the same way for factory-wave to read, so
    # the driver no longer carries its own private literal -- both caps now come
    # from this one declaration and the +1 relation is asserted above.
    environment.etc = {
      "seat-lane/max-units" = {
        text = toString cfg.maxUnits;
      };
      "seat-lane/wave-jobs" = {
        text = toString cfg.waveJobs;
      };
      # SA4: the port range seat-spool allocates from is published the same way
      # as the two caps, so the spool reads a declared file (never a private
      # literal).
      "seat-lane/port-range" = {
        text = cfg.portRange;
      };
    }
    // lib.optionalAttrs (cfg.helmApiPort != null) {
      # IS20 (answer 11): the seat's second reachable host port is published as
      # a file beside the two caps, so a later consumer (Helm's api_seats) can
      # read it the same way seat-submit/factory-wave read the caps.
      "seat-lane/helm-api-port" = {
        text = toString cfg.helmApiPort;
      };
    };

    # FIX1 (part a): expose the submit CLI to the host. factory-task's unit arm
    # is reached only when `command -v seat-submit` succeeds on the host PATH,
    # and the seat@ unit's own path (below) is invisible from the host. Putting
    # seatSubmit in environment.systemPackages lands it on
    # /run/current-system/sw after the next switch, exactly as modelLane.nix
    # does for the lane's submit CLI.
    environment.systemPackages = [ seatSubmit ];

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
      # IS20 (answer 11): the seat's namespace additionally reaches Helm's v2
      # API port on the host-side address (null = unchanged). The rule is
      # scoped to the namespace address and rendered inside input-seat after
      # the broker accept, before its trailing drop.
      extraInputRules =
        lib.optional (cfg.helmApiPort != null)
          "iifname \"veb-seat\" ip saddr ${cfg.namespaceAddress} tcp dport ${toString cfg.helmApiPort} accept";
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
        # PL16: the seat's gh config dir (the unit's GH_CONFIG_DIR, above).
        # 0555 root:root -- the seat (operatorUser) can read and traverse it,
        # so gh's lookup finds an empty dir instead of failing on a missing
        # one, but can never write a real hosts.yml or a symlink into it: no
        # job can plant a credential gh would then trust.
        "d /var/lib/seat/gh-config-empty 0555 root root -"
        # SA7 (decision 59a): the seat's memory store, under the evidence store.
        # 0700 operator-only -- a machine-local store a job seat's own tools can
        # reach through $DSH_HOME/memory, never world-readable. Declared (brief
        # §3 invariant 4), never made by hand.
        "d ${cfg.memoryDir} 0700 ${cfg.operatorUser} users -"
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
        # IS26: starting a seat starts its shutdown inhibitor companion (the
        # seat-inhibit@ template below), so the lock's lifetime is the seat's
        # own -- never a separate command the operator forgets to run.
        wants = [ "seat-inhibit@%i.service" ];
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
          # PL16 (brief §2 goal 1): gh joins the devShell, so a job that
          # reaches `nix develop -c gh` inside this unit must not resolve the
          # OPERATOR's gh identity: gh's default config lookup walks
          # $HOME/.config/gh (the unit's HOME is the operator's real one, see
          # the /home comment below) and the Secret Service over the session
          # bus (hidden below). Pinning GH_CONFIG_DIR at a fresh root-owned dir
          # -- tmpfiles creates it 0555 root:root (rule above), so the seat
          # can read/traverse but never write a real hosts.yml or a symlink
          # into it -- makes gh discover no credential at all ("You are not
          # logged into any GitHub hosts.", measured). An env entry, never a
          # credential: the sk-or- assertion above stays true by construction.
          GH_CONFIG_DIR = "/var/lib/seat/gh-config-empty";
          # SA7 (decision 59a): the wrapper links $DSH_HOME/memory into this
          # store by workspace cwd-key, so a seat's durable memory lives under
          # the evidence store, never in the tree.
          SEAT_MEMORY_DIR = cfg.memoryDir;
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
          # SD12: the harness's spill store writes to an absolute
          # /tmp/dsh-spill-XXXXXX prefix -- a literal inside
          # @deepseek-ai/dsh-spill-local's privateRoot, so neither DSH_CACHE_ROOT
          # (SD5) nor TMPDIR can redirect it. ProtectSystem=strict makes the
          # real /tmp read-only, which killed the very first drive boot with
          # EROFS mkdtemp '/tmp/dsh-spill-XXXXXX'. A private instance /tmp
          # (mounted per unit, dies with the unit under KillMode=control-group)
          # is the only writable /tmp such a prefix can ever reach, and it keeps
          # one job from reading another job's spill. The cache, which must
          # outlive a job, stays at DSH_CACHE_ROOT=/var/lib/seat/cache.
          PrivateTmp = true;
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
            "-/var/lib/evidence"
            # SA7 (decision 59a): the seat's memory store is its own explicit
            # row, kept beside the broad -/var/lib/evidence row so the grant
            # stays visible even if the broad row is later narrowed. tmpfiles
            # creates it (0700 operator-only), so it is never absent on a
            # fresh machine.
            "${cfg.memoryDir}"
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
            # PL16: the operator's own session bus -- the transport the
            # Secret Service (the desktop keyring) is reached over, and gh's
            # fallback credential resolution when no hosts.yml answers. The
            # uid is computed from cfg.operatorUser, never %U: systemd.unit(5)
            # is explicit that %U resolves to the SERVICE MANAGER's own uid
            # ("0" for a system unit, not influenced by User=), so a %U
            # spelling would hide /run/user/0/bus (nothing) and leave the
            # real bus untouched -- silently inert (measured against the
            # installed man page, systemd 260). The "-" prefix tolerates a
            # machine where no session bus exists, exactly as the two
            # systemd sockets above; AF_UNIX is already admitted by
            # RestrictAddressFamilies (Base), so this hide is the one thing
            # that stands between a seat and its operator's keyring.
            "-/run/user/${toString config.users.users.${cfg.operatorUser}.uid}/bus"
          ];
          NoNewPrivileges = true;
          # AF_NETLINK: the wrapper's `--broker` route check (`ip route`) must
          # be able to inspect the namespace's default route on every launch
          # (plan amendment 2). AF_INET/AF_INET6/AF_UNIX mirror the lane.
          RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX AF_NETLINK";
        };
      };

      # IS26: a running seat holds a shutdown inhibitor -- measured
      # 2026-09-23: the operator rebooted with work in flight and nothing
      # warned. The lock cannot be taken from inside seat@ (above):
      # InaccessiblePaths hides the system bus, and logind's Inhibit() is a
      # system-bus call, so the job itself could never hold it -- that
      # hardening is correct and stays. Instead this unsandboxed companion
      # template holds the lock on the seat's behalf:
      #
      # - block, never delay: a delay lock holds shutdown for
      #   InhibitDelayMaxUSec (5 s compiled default) and shows nothing, which
      #   barely differs from the silent discard this fixes; a block lock
      #   stops a normal shutdown, GNOME's end-session dialog names the
      #   inhibiting unit, and the operator's emergency override is the
      #   dialog itself or `systemctl poweroff -i` through the existing
      #   wheel admin rule.
      # - systemd-inhibit wraps `sleep infinity`, so the wrapped child never
      #   exits on its own and the inhibitor fd stays open for the seat's
      #   whole life (a plain `true` would drop the lock at once).
      # - BindsTo + After make release structural, not a cleanup path: when
      #   seat@%i leaves the active state for ANY reason -- clean exit,
      #   failure, stop, an OOM kill of the job -- systemd stops the
      #   companion, the wrapped sleep dies with the cgroup, logind's
      #   inhibitor pipe closes, and the lock is released. No code runs for
      #   that to hold.
      # - The unit runs as the operator because a block lock is polkit-gated
      #   (inhibit-block-shutdown defaults to auth_admin_keep for `any`, so
      #   a session-less system unit cannot take one without an explicit
      #   grant); the grant lives in security.polkit.extraConfig below and
      #   names exactly this user. A missing or wrong grant makes
      #   systemd-inhibit exit immediately, the companion unit fails, and
      #   that is observable as its ActiveState -- never a silent
      #   degradation into the no-warning reboot this task fixes.
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

      services = {
        # IS26: a running seat holds a shutdown inhibitor -- measured
        # 2026-09-23: the operator rebooted with work in flight and nothing
        # warned. The lock cannot be taken from inside seat@ (above):
        # InaccessiblePaths hides the system bus, and logind's Inhibit() is a
        # system-bus call, so the job itself could never hold it -- that
        # hardening is correct and stays. Instead this unsandboxed companion
        # template holds the lock on the seat's behalf:
        #
        # - block, never delay: a delay lock holds shutdown for
        #   InhibitDelayMaxUSec (5 s compiled default) and shows nothing, which
        #   barely differs from the silent discard this fixes; a block lock
        #   stops a normal shutdown, GNOME's end-session dialog names the
        #   inhibiting unit, and the operator's emergency override is the
        #   dialog itself or `systemctl poweroff -i` through the existing
        #   wheel admin rule.
        # - systemd-inhibit wraps `sleep infinity`, so the wrapped child never
        #   exits on its own and the inhibitor fd stays open for the seat's
        #   whole life (a plain `true` would drop the lock at once).
        # - BindsTo + After make release structural, not a cleanup path: when
        #   seat@%i leaves the active state for ANY reason -- clean exit,
        #   failure, stop, an OOM kill of the job -- systemd stops the
        #   companion, the wrapped sleep dies with the cgroup, logind's
        #   inhibitor pipe closes, and the lock is released. No code runs for
        #   that to hold.
        # - The unit runs as the operator because a block lock is polkit-gated
        #   (inhibit-block-shutdown defaults to auth_admin_keep for `any`, so
        #   a session-less system unit cannot take one without an explicit
        #   grant); the grant lives in security.polkit.extraConfig below and
        #   names exactly this user. A missing or wrong grant makes
        #   systemd-inhibit exit immediately, the companion unit fails, and
        #   that is observable as its ActiveState -- never a silent
        #   degradation into the no-warning reboot this task fixes.
        "seat-inhibit@" = {
          description = "Shutdown inhibitor for seat job %i";
          after = [ "seat@%i.service" ];
          bindsTo = [ "seat@%i.service" ];
          serviceConfig = {
            User = cfg.operatorUser;
            ExecStart = ''${pkgs.systemd}/bin/systemd-inhibit --what=shutdown --mode=block --who=seat@%i --why="a seat job is running" ${pkgs.coreutils}/bin/sleep infinity'';
          };
        };

        # The validator: no shell, no User (runs as root so it may start seat@
        # units); a oneshot that starts exactly one seat@ instance per marker and
        # exits. --systemctl defaults to `systemctl` on root's PATH.
        seat-spool = {
          serviceConfig = {
            Type = "oneshot";
            ExecStart = "${seatSpool}/bin/seat-spool --jobs-dir /var/lib/seat/jobs --spool-dir /var/lib/seat/spool --owner ${cfg.operatorUser}";
          };
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

    # IS20 (answer 11): nixos-fw must allow the seat's namespace to reach the
    # helmApiPort (the input-seat accept is one base chain; nixos-fw's own
    # input chain, a separate base chain on the same hook, would otherwise
    # drop the SYN). Merges with egressBroker's `[ listenPort ]` allow.
    networking.firewall.interfaces."veb-seat".allowedTCPPorts = lib.optional (
      cfg.helmApiPort != null
    ) cfg.helmApiPort;

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
      // IS26: the seat-inhibit@ companion (as ${cfg.operatorUser}, above)
      // takes its block lock through logind's Inhibit() on the system bus.
      // inhibit-block-shutdown's implicit 'any' is auth_admin_keep, so a
      // session-less system unit can never acquire it without this grant --
      // scoped to the one action and the one operator user, never a
      // blanket YES.
      polkit.addRule(function(action, subject) {
        if (action.id == "org.freedesktop.login1.inhibit-block-shutdown" && subject.user == "${cfg.operatorUser}") {
          return polkit.Result.YES;
        }
      });
    '';
  };
}
