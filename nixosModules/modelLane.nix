{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.model-lanes;
  laneRun = pkgs.callPackage ../pkgs/lane/lane-run.nix { };
  # One file (pkgs/lane/lane-submit.py) backs both operator binaries: the
  # wrapper sets LANE_MODE before exec, mirroring pkgs/helm/collect.py's own
  # --print dispatch for helm-status.
  laneSubmit = pkgs.writeShellApplication {
    name = "lane-submit";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      export LANE_MODE=submit
      exec python3 ${../pkgs/lane/lane-submit.py} "$@"
    '';
  };
  laneWait = pkgs.writeShellApplication {
    name = "lane-wait";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      export LANE_MODE=wait
      exec python3 ${../pkgs/lane/lane-submit.py} "$@"
    '';
  };
  operatorUsers = lib.unique (lib.mapAttrsToList (_: i: i.operatorUser) cfg);
  # T2 (plan Task 2): this module used to carry a `brokerInstance` option
  # (default = the lane's own name) naming the services.egress-broker.instances
  # entry to wire up. Nothing ever needed two lanes sharing one instance --
  # the option was pure indirection, keyed by `lib.mapAttrs` below onto
  # `cfg`'s own keys regardless of what brokerInstance said, so setting it to
  # anything but the lane's name silently did nothing (a real bug: it looked
  # configurable but wasn't). Removed; every reference below uses the lane's
  # own attrset name directly -- the instance name IS the lane name, always.
  # T2 fix round (Opus re-gate of 90d9e86, blocker): InaccessiblePaths below
  # hides the whole /var/lib/egress-broker tree from this unit (the confdir
  # under it holds the CA's PRIVATE key, plus the broker's audit log --
  # neither may be visible to a network-capable process, brief §3 invariant
  # 2), but SSL_CERT_FILE/NIX_SSL_CERT_FILE/NODE_EXTRA_CA_CERTS below must
  # still resolve to a real, readable file or this unit cannot verify TLS
  # through its own broker at all. egressBroker.nix's ExecStartPost publishes
  # a second, public-only copy of ca-bundle.crt (no private key material) at
  # this sibling path -- NOT a subpath of /var/lib/egress-broker -- so hiding
  # the instance tree does not also cut off the one file every consumer's
  # process needs. Proven by checks.lane-vm (chat job completes through TLS)
  # and lane-eval's InaccessiblePaths/SSL_CERT_FILE cross-check below.
  caBundle = name: "/var/lib/egress-broker-ca-bundle/${name}/ca-bundle.crt";
  netnsPath = name: "/run/netns/egress-${name}";
  laneModule =
    # T2: `name` (the submodule's own attrset key) was used only by the
    # removed brokerInstance option's `default = name;` -- nothing in this
    # submodule needs it any more (module-level uses of the lane's name, e.g.
    # the tmpfiles/systemd/polkit blocks below, come from the outer
    # `lib.mapAttrsToList`/`lib.mapAttrs'` key instead, not from in here).
    _: {
      options = {
        host = lib.mkOption {
          type = lib.types.str;
          description = "The single upstream hostname this lane's broker instance allows.";
        };
        harnessPackage = lib.mkOption {
          type = lib.types.package;
          default = pkgs.callPackage ../pkgs/dsh { };
          description = "The agent harness on the lane unit's PATH for `dsh` jobs (DeepSeek Harness, pinned by pkgs/dsh/package-lock.json). Prototype 2026-09-03: replaces `claude -p`, which returned empty results through OpenRouter's Anthropic surface.";
        };
        model = lib.mkOption {
          type = lib.types.str;
          description = "Model identifier passed to the client as LANE_MODEL (e.g. deepseek/deepseek-v4-flash).";
        };
        keyFile = lib.mkOption {
          type = lib.types.str;
          description = ''
            Path to the API key file the broker injects for `host`. Must be
            outside /nix/store — a store path would copy the secret into the
            world-readable store (asserted below). Never read by this
            module; consumed only by
            services.egress-broker.instances.<name>.inject, where <name> is
            this lane's own name (see the module-level comment above on
            brokerInstance's removal).
          '';
        };
        hostAddress = lib.mkOption {
          type = lib.types.str;
          description = "Host-side veth address for this lane's broker instance.";
        };
        namespaceAddress = lib.mkOption {
          type = lib.types.str;
          description = "Netns-side veth address for this lane's broker instance.";
        };
        listenPort = lib.mkOption {
          type = lib.types.port;
          description = "Port the broker listens on inside this lane's netns.";
        };
        allowedClasses = lib.mkOption {
          type = lib.types.listOf (
            lib.types.enum [
              "local-only"
              "redacted"
              "permitted"
            ]
          );
          default = [ "permitted" ];
          description = ''
            Data classifications this lane may accept. Currently only
            "permitted" may be enabled (asserted below) — a lane is an
            agent with an egress class, and brief §3 invariants 2/3 forbid
            local-only or redacted data reaching a network-capable process.
          '';
        };
        operatorUser = lib.mkOption {
          type = lib.types.str;
          default = config.services.helm.operatorUser or "operator";
          description = "Human user allowed (via polkit) to start lane-<name>@<job> and added to group \"lane\".";
        };
      };
    };
in
{
  options.services.model-lanes = lib.mkOption {
    default = { };
    description = "Broker-injected remote-model lanes: one egress-broker instance + one job/result spool + one systemd template unit per lane.";
    type = lib.types.attrsOf (lib.types.submodule laneModule);
  };

  config = lib.mkIf (cfg != { }) {
    assertions =
      # keyFile must never be a store path — a types.path value, or a
      # literal starting with /nix/store, would copy the secret into the
      # world-readable Nix store.
      lib.mapAttrsToList (name: i: {
        assertion = !(lib.hasPrefix "/nix/store" i.keyFile);
        message = "services.model-lanes.${name}.keyFile must be a path outside /nix/store, got '${i.keyFile}'";
      }) cfg
      # allowedClasses is currently permitted-only: a lane is an agent with
      # an egress class, and the same assertion shape as lib/mkAgent.nix
      # forbids local-only/redacted data reaching a network-capable process.
      ++ lib.mapAttrsToList (name: i: {
        assertion = lib.all (c: c == "permitted") i.allowedClasses;
        message = "services.model-lanes.${name}.allowedClasses must be a subset of [ \"permitted\" ], got [ ${
          lib.concatStringsSep ", " (map (c: "\"${c}\"") i.allowedClasses)
        } ] — a lane may not accept local-only or redacted data (brief §3 invariants 2/3)";
      }) cfg
      # Some other consumer (not this module) declaring its own
      # services.egress-broker.instances.<name> at this same lane name would
      # otherwise merge `allow` lists (it's a plain listOf str option); this
      # lane module's contract is one host per instance, one instance per
      # lane, name-for-name.
      ++ lib.mapAttrsToList (name: i: {
        assertion = config.services.egress-broker.instances.${name}.allow == [ i.host ];
        message = "services.model-lanes.${name}: egress-broker instance '${name}' allow list must be exactly [ \"${i.host}\" ] — check for another consumer declaring an egress-broker instance under this lane's name";
      }) cfg;

    services.egress-broker.instances = lib.mapAttrs (_: i: {
      inherit (i) hostAddress namespaceAddress listenPort;
      allow = [ i.host ];
      inject.${i.host}.valueFile = i.keyFile;
      # Data policy at the chokepoint: every chat request to this host gets
      # zero-data-retention routing and the training opt-out, whatever the
      # client (lane-run, dsh, anything) put in its body. Decision
      # docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md.
      bodyPatch.${i.host} = {
        pathPrefixes = [
          "/api/v1/chat/completions"
        ];
        merge.provider = {
          zdr = true;
          data_collection = "deny";
        };
      };
      # O3 resolved: fail closed. Nothing consumes OpenRouter's
      # Anthropic-style /api/v1/messages path (the seat and the lane both use
      # chat completions), so instead of leaving it half-patched behind the
      # old patchMessagesPath option it is DENIED at the broker -- before the
      # key is injected, audited reason "path-not-permitted" -- so no
      # credential-injected, unpatched request to that path can leave the
      # instance (the three U7 audit records that motivated this). The chat
      # prefix list above is unchanged.
      denyPaths.${i.host} = {
        pathPrefixes = [ "/api/v1/messages" ];
      };
    }) cfg;

    users.groups.lane = { };
    users.users = lib.genAttrs operatorUsers (_: {
      extraGroups = [ "lane" ];
    });

    # lane-submit/lane-wait: the operator's own CLI (T3). jq: the job
    # templates under tools/lane/jobs/*.sh build job JSON/schema payloads
    # with it, same convention pkgs/helm/collect.py's own jq calls use.
    environment.systemPackages = [
      laneSubmit
      laneWait
      pkgs.jq
    ];

    systemd.tmpfiles.rules = lib.flatten (
      lib.mapAttrsToList (name: i: [
        "z ${i.keyFile} 0440 root egress-broker -"
        # 2770, not 2750 (T3 fix, found by checks.lane-vm: the ledger
        # DynamicUser lane-run.py appends to lives directly in this
        # directory -- /var/lib/lanes/<name>/ledger.jsonl, one line per
        # completed job -- so group "lane" needs write here too, not just
        # in jobs/ and results/ below).
        "d /var/lib/lanes/${name} 2770 root lane -"
        "d /var/lib/lanes/${name}/jobs 2770 root lane -"
        "d /var/lib/lanes/${name}/results 2770 root lane -"
      ]) cfg
    );

    systemd.services = lib.mapAttrs' (
      name: i:
      lib.nameValuePair "lane-${name}@" {
        description = "Model lane ${name}: run one %i job through its own broker instance";
        requires = [ "egress-broker-${name}.service" ];
        after = [ "egress-broker-${name}.service" ];
        environment = {
          HTTPS_PROXY = "http://${i.hostAddress}:${toString i.listenPort}";
          HTTP_PROXY = "http://${i.hostAddress}:${toString i.listenPort}";
          SSL_CERT_FILE = caBundle name;
          NIX_SSL_CERT_FILE = caBundle name;
          NODE_EXTRA_CA_CERTS = caBundle name;
          # dsh (Node) ignores HTTPS_PROXY on its own -- verified 2026-09-03
          # against a logging proxy: no CONNECT without this, seven with it.
          # Node 22.20 honours NODE_USE_ENV_PROXY (undici EnvHttpProxyAgent for
          # global fetch), so the harness's model calls tunnel through the
          # broker like every other client in this namespace.
          NODE_USE_ENV_PROXY = "1";
          # ...and for the host pin's Node 22.20, which lacks that switch, the
          # undici preload shipped in pkgs/dsh does the same job.
          NODE_OPTIONS = "--require ${i.harnessPackage}/lib/proxy-shim.cjs";
          LANE_NAME = name;
          LANE_HOST = i.host;
          LANE_MODEL = i.model;
          LANE_CLASSES = lib.concatStringsSep "," i.allowedClasses;
        };
        # T3's "agent" job kind shells out to `claude` (subprocess.run in
        # lane-run.py). The claude binary is deliberately NOT a Nix runtime
        # input of the lane-run package -- the operator's own system
        # profile provides it, same as any interactive shell would find it
        # -- but a systemd unit's default PATH (systemd.nix's own
        # coreutils/findutils/gnugrep/gnused/systemd baseline) does not
        # include /run/current-system/sw/bin the way a login shell's does,
        # so the "chat"-only lane would otherwise work fine while an
        # "agent" job failed with FileNotFoundError. `path` (not a direct
        # `environment.PATH =`, which conflicts with that same
        # systemd.nix-supplied default at equal priority -- confirmed by
        # `nix build .#checks.lane-eval` before this fix) appends this one
        # missing directory to it, the same idiom systemd.nix itself uses
        # for e.g. systemd-fsck@'s path.
        path = [
          "/run/current-system/sw"
          i.harnessPackage
        ];
        serviceConfig = {
          Type = "oneshot";
          TimeoutStartSec = "30min";
          NetworkNamespacePath = netnsPath name;
          DynamicUser = true;
          SupplementaryGroups = [ "lane" ];
          ExecStart = "${laneRun}/bin/lane-run ${name} %i";
          ReadWritePaths = [ "/var/lib/lanes/${name}" ];
          NoNewPrivileges = true;
          ProtectSystem = "strict";
          ProtectHome = true;
          PrivateTmp = true;
          CapabilityBoundingSet = "";
          RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX";
          # T2 (plan Task 2, brief §3 invariants 1/2): ProtectSystem=strict
          # and ProtectHome=true make these paths read-only or empty, not
          # invisible -- a lane job runs agent-authored/model-authored code
          # (T3's "agent" job kind), and a process that can list a path can
          # probe what exists on it even if it can't write there.
          # InaccessiblePaths makes each of these ENOENT instead: decrypted
          # basket contents must exist only for the mounting agent's own
          # lifetime, never be stat()-able by an unrelated process (invariant
          # 1); the broker's injected credentials and audit trail, Helm's
          # collected state, and provider key files must never be visible to
          # a network-capable process (invariant 2); /home is already
          # emptied by ProtectHome but is listed explicitly so this list
          # reads as the complete contract, not "whatever ProtectHome
          # happens to also cover".
          InaccessiblePaths = [
            "-/run/baskets"
            "-/var/lib/baskets"
            "-/var/lib/helm"
            "-/var/lib/egress-broker"
            "-/var/lib/secrets"
            "-/home"
          ];
          # Ledger (/var/lib/lanes/<name>/ledger.jsonl) and job results are
          # written by this unit under the "lane" group (2770 dirs, tmpfiles
          # rule above) -- 0027 keeps files it creates group-readable only,
          # not world-readable, matching helm.nix's own user units.
          UMask = "0027";
        };
      }
    ) cfg;

    security.polkit.enable = lib.mkDefault true;
    # ES5 (duktape, no template literals / arrow functions): the operator
    # may start any job on their own lane's template unit; every other
    # subject and every other unit is left to polkit's normal (implicit
    # deny for manage-units, admin-authenticated otherwise) fallthrough.
    security.polkit.extraConfig = lib.concatStrings (
      lib.mapAttrsToList (name: i: ''
        polkit.addRule(function(action, subject) {
          if (action.id == "org.freedesktop.systemd1.manage-units") {
            var verb = action.lookup("verb");
            var unit = action.lookup("unit");
            var prefix = "lane-${name}@";
            var suffix = ".service";
            if (verb == "start" &&
                unit.indexOf(prefix) === 0 &&
                unit.indexOf(suffix, unit.length - suffix.length) !== -1 &&
                subject.user == "${i.operatorUser}") {
              return polkit.Result.YES;
            }
          }
        });
      '') cfg
    );
  };
}
