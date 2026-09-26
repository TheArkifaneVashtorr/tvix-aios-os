# services.comfyui-worlds — one definition renders, per world: the ComfyUI
# generator (a user unit) and the user target that starts it, plus — shared
# by every world — the ONE feed server (comfy-feed.service, GN22) whose
# routes are world-scoped under /w/<name>/. GN26: the module renders NO
# Caddy configuration at all — the LAN face is services.lan-access's (one
# site, one credential, declared by the host; see hosts/core/lan-access.nix).
# Design:
# docs/superpowers/specs/2026-09-05-comfy-worlds-design.md; the per-world
# tree the units guard is built by comfy-worlds-init (W2).
#
# Two worlds share one definition; only one generator runs at a time (their
# units conflict). The generator is a per-user service run as the operator
# (operatorUser), not a system service: it reads `~/comfyui` and talks to the
# GPU through the login session, and it must NOT be confined by a device
# filter — device filters are BPF cgroup programs the per-user manager cannot
# attach, so DevicePolicy/DeviceAllow would be a silent no-op that reads like a
# control (the GPU path is proven on `core` by the acceptance drill, W6, not
# asserted at eval). PrivateDevices=false keeps /dev/nvidia* visible.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.comfyui-worlds;

  # Every derivation the module uses comes from this file (W2's, extended in
  # W3), imported with the consuming host's pkgs — never self.packages.
  worldsPkgs = import ../pkgs/comfy-worlds { inherit pkgs; };

  worldNames = builtins.attrNames cfg.worlds;
  worldValues = builtins.attrValues cfg.worlds;

  # World names match ^[a-z][a-z0-9-]{0,15}$.
  nameOk = name: builtins.match "^[a-z][a-z0-9-]{0,15}$" name != null;

  comfyPorts = map (w: w.comfyPort) worldValues;
  # GN22 — one feed port: the comfyPorts must be pairwise distinct, and the
  # single feedPort must sit apart from all of them (two assertions, two
  # refusal messages).
  comfyPortsDistinct = lib.length (lib.unique comfyPorts) == lib.length comfyPorts;

  # feedListenAddress is loopback: four integer octets 0–255 with the first
  # byte 127, or the literal ::1 — the same rule local-model.nix applies (the
  # module's assertion is the build-time loopback refusal; the unit passes
  # whatever survives it).
  feedOctets = builtins.match "^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$" cfg.feedListenAddress;
  octetOk =
    s:
    let
      n = lib.toInt s;
    in
    n >= 0 && n <= 255;
  feedListenLoopback =
    if feedOctets != null then
      (lib.toInt (builtins.elemAt feedOctets 0)) == 127 && lib.all octetOk feedOctets
    else
      cfg.feedListenAddress == "::1";

  # The broker instance the probe's egress crosses (invariant 3). Existence is
  # asserted when refresh.enable; the proxy/CA strings are only forced once
  # that assertion has passed (lib.optionals guards the force), so a bad name
  # is a clean assertion, never a raw attribute-missing error.
  brokerInst = cfg.refresh.brokerInstance;
  brokerExists = config.services.egress-broker.instances ? ${brokerInst};
  probeProxy = "http://${config.services.egress-broker.instances.${brokerInst}.hostAddress}:${
    toString config.services.egress-broker.instances.${brokerInst}.listenPort
  }";
  probeCa = "/var/lib/egress-broker/${brokerInst}/ca/ca.pem";

  # GN52 — the card unit's broker instance: existence asserted when
  # cards.enable (the optionals guard keeps a bad name a clean assertion,
  # never a raw attribute-missing error — the refresh block's pattern).
  cardsBrokerInst = cfg.cards.brokerInstance;
  cardsBrokerExists = config.services.egress-broker.instances ? ${cardsBrokerInst};

  # GN52 — the lookup URL's host: the text after https:// up to the first
  # /, : or { — "" when the URL is not https://… at all (assertion (a)'s
  # message names that case first; the host rule's force is guarded by
  # (a) the same way).
  cardsLookupHost =
    let
      m = builtins.match "^https://([^/:{]+).*$" cfg.cards.lookupUrl;
    in
    if m == null then "" else builtins.head m;

  genUnit =
    w:
    let
      world = cfg.worlds.${w};
      others = lib.filter (o: o != w) worldNames;
      cpu = lib.optionalString cfg.cpuOnly " --cpu";
    in
    {
      description = "ComfyUI generator for world ${w}";
      unitConfig.ConditionUser = cfg.operatorUser;
      serviceConfig = {
        ExecStartPre = "${worldsPkgs.comfy-world-guard}/bin/comfy-world-guard ${cfg.root} ${w}";
        ExecStart = "${cfg.package}/bin/comfyui --listen 127.0.0.1 --port ${toString world.comfyPort} --base-directory ${cfg.root}/worlds/${w} --user-directory ${cfg.root}/worlds/${w}/lab/user --disable-auto-launch${cpu}";
        ProtectSystem = "strict";
        ProtectHome = "read-only";
        ReadWritePaths = [
          "${cfg.root}/worlds/${w}"
          "%h/.cache"
        ];
        NoNewPrivileges = true;
        PrivateTmp = true;
        PrivateDevices = false;
      };
      conflicts = map (o: "comfyui-${o}.service") others;
      wantedBy = [ ];
    };

  # GN22 — the ONE feed unit: a single comfy-feed.service serving every
  # configured world (world-scoped routes under /w/<name>/), reading the
  # world list from the /etc/comfy-worlds.json the module renders. The
  # sandbox names EVERY world dir plus %h/.cache, so the one process can
  # write each world's feed.sqlite and delete its PNGs.
  feedUnit = {
    description = "The feed server for every world (one server, world-scoped routes)";
    unitConfig.ConditionUser = cfg.operatorUser;
    serviceConfig = {
      ExecStart = "${worldsPkgs.comfy-feed}/bin/comfy-feed --root ${cfg.root} --port ${toString cfg.feedPort} --listen ${cfg.feedListenAddress} --worlds-file /etc/comfy-worlds.json";
      ProtectSystem = "strict";
      ProtectHome = "read-only";
      ReadWritePaths = map (w: "${cfg.root}/worlds/${w}") worldNames ++ [ "%h/.cache" ];
      NoNewPrivileges = true;
      PrivateTmp = true;
      PrivateDevices = false;
    };
    wantedBy = [ ];
  };

  mutateUnit =
    w:
    let
      world = cfg.worlds.${w};
    in
    {
      description = "Prompt mutator for world ${w}";
      unitConfig.ConditionUser = cfg.operatorUser;
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${worldsPkgs.comfy-mutate}/bin/comfy-mutate --world ${w} --root ${cfg.root} --n ${toString cfg.mutate.perLike} --comfy-url http://127.0.0.1:${toString world.comfyPort}";
        ProtectSystem = "strict";
        ProtectHome = "read-only";
        ReadWritePaths = [ "${cfg.root}/worlds/${w}" ];
        NoNewPrivileges = true;
        PrivateTmp = true;
        PrivateDevices = false;
      };
      wantedBy = [ ];
    };

  # GN17 — the per-world authoring supervisor, a oneshot user unit beside
  # the mutator. SuccessExitStatus = "3" (the STRING: the unit file must
  # render SuccessExitStatus=3 and comfy-worlds-eval compares against the
  # same "3") leaves the two-empty halt `inactive` rather than `failed`,
  # and there is deliberately NO Restart= of any value: a restart
  # directive would respin the loop forever and silently defeat the halt.
  # PrivateDevices = true: the supervisor touches no GPU — it starts and
  # stops units, systemd's Conflicts= does the trading. The three
  # binaries render absolute store paths (--systemctl/--author/--mutate),
  # never a PATH lookup.
  runUnit =
    w:
    let
      world = cfg.worlds.${w};
      provenance =
        lib.optionalString (cfg.author.modelPath != "") " --model-path ${cfg.author.modelPath}"
        + lib.optionalString (cfg.author.modelSha256 != "") " --model-sha256 ${cfg.author.modelSha256}";
    in
    {
      description = "comfy-run-${w}: the authoring supervisor (GN17)";
      unitConfig.ConditionUser = cfg.operatorUser;
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${worldsPkgs.comfy-run}/bin/comfy-run --world ${w} --root ${cfg.root} --n-prompts ${toString world.author.promptsPerBatch} --window ${toString world.author.verdictWindow} --n-variants ${toString world.author.variantsPerPrompt} --low-water ${toString world.author.lowWater} --tick ${toString world.author.tickSeconds} --model-wait ${toString world.author.modelWait} --model-timeout ${toString world.author.modelTimeout} --history ${toString world.author.historyBatches} --model-url ${cfg.author.modelUrl} --model-unit ${cfg.author.modelUnit} --generator-unit comfyui-${w}.service --comfy-url http://127.0.0.1:${toString world.comfyPort} --systemctl ${pkgs.systemd}/bin/systemctl --author ${worldsPkgs.comfy-author}/bin/comfy-author --mutate ${worldsPkgs.comfy-mutate}/bin/comfy-mutate${provenance}";
        ProtectSystem = "strict";
        ProtectHome = "read-only";
        ReadWritePaths = [ "${cfg.root}/worlds/${w}" ];
        NoNewPrivileges = true;
        PrivateTmp = true;
        PrivateDevices = true;
        SuccessExitStatus = "3";
      };
      wantedBy = [ ];
    };

  # GN52 — the per-world card unit: comfy-cards' network arm through the
  # media broker (invariant 3 — the unit's egress crosses the broker, and
  # the lookup host must be in the instance's allow, refused at eval by
  # assertions (a)–(d), never discovered as a runtime 403). The unit is
  # gated on cards.enable like the probe; the offline arm needs no unit
  # and no broker — it is the operator's hand tool on PATH.
  cardsUnit = w: {
    description = "comfy-cards-${w}: the LoRA card lookup through the media broker";
    unitConfig.ConditionUser = cfg.operatorUser;
    serviceConfig = {
      Type = "oneshot";
      ExecStart = "${worldsPkgs.comfy-cards}/bin/comfy-cards --world ${w} --root ${cfg.root} --lookup-url ${cfg.cards.lookupUrl} --timeout ${toString cfg.cards.timeoutSeconds}";
      Environment = lib.optionals cardsBrokerExists [
        "HTTPS_PROXY=http://${
          config.services.egress-broker.instances.${cfg.cards.brokerInstance}.hostAddress
        }:${toString config.services.egress-broker.instances.${cfg.cards.brokerInstance}.listenPort}"
        "SSL_CERT_FILE=/var/lib/egress-broker/${cfg.cards.brokerInstance}/ca/ca.pem"
      ];
      ProtectSystem = "strict";
      ProtectHome = "read-only";
      ReadWritePaths = [ "${cfg.root}/worlds/${w}" ];
      NoNewPrivileges = true;
      PrivateTmp = true;
      PrivateDevices = true;
    };
    wantedBy = [ ];
  };

  # GN43 — the target pulls in the authoring supervisor (comfy-run-<w>)
  # beside the generator and the feed: starting a world starts the
  # authoring loop, not just the generator (spec D4, "A world is one
  # composed unit"). Deliberately NO binding edge (Requires=/PartOf=/…
  # are absent): comfy-run is a oneshot with no Restart= whose normal
  # exit must not take the world down. The churn this accepts: run's
  # first act starts comfy-author-model, which Conflicts= the generator
  # the target just started; run then stops the model and restarts the
  # generator — one extra generator stop/start per world start.
  # GN43 is reverted here (2026-09-21). The target wants the generator and the
  # one feed, as it did before, and NOT the authoring supervisor.
  #
  # GN43 added comfy-run-<w> so that starting a world started its authoring
  # loop. Measured consequence, comfy-worlds-vm: the supervisor's first act is
  # to start comfy-author-model, whose Conflicts= names every generator.
  # systemd resolves Conflicts= inside the start *transaction* -- the generator
  # is stopped when the model is activated, not when it succeeds -- so a model
  # that then fails leaves the generator stopped with nothing to restart it.
  # In the VM the model cannot start at all (no weights):
  #
  #   comfy-author-model.service: Control process exited, status=1/FAILURE
  #   comfy-run: ... failed with exit 1 in world sfw; aborting
  #   comfy-run-sfw.service: Main process exited, status=4/NOPERMISSION
  #
  # and `curl 127.0.0.1:8188/system_stats` then timed out at 600 s. Dropping
  # the generator instead (wanting feed + supervisor) fails identically, for
  # the same reason: the supervisor dies before it reaches its own generator
  # start. Both arrangements were measured.
  #
  # The operator's ask -- "when I say one I want both" -- stands and is not
  # served by target membership: the GPU cannot hold the author model and a
  # generator at once, so an ordering that survives a model failure has to be
  # expressed in the supervisor, not in `wants`. See the bug row
  # BUG-world-target-supervisor-deadlock.
  targetUnit = w: {
    description = "ComfyUI world ${w} (generator + the one feed)";
    wants = [
      "comfyui-${w}.service"
      "comfy-feed.service"
    ];
  };
in
{
  options.services.comfyui-worlds = {
    enable = lib.mkEnableOption "the ComfyUI worlds (per-world generator, feed, target and Caddy site)";

    operatorUser = lib.mkOption {
      type = lib.types.str;
      default = "operator";
      description = "The user the user-scope units run as (their ConditionUser); owns `~/comfyui`.";
    };

    root = lib.mkOption {
      type = lib.types.str;
      default = "/home/${cfg.operatorUser}/comfyui";
      description = "Absolute path holding `store/` and `worlds/<w>/` (asserted absolute).";
    };

    package = lib.mkOption {
      type = lib.types.package;
      default = import ../pkgs/comfyui/package.nix { inherit pkgs; };
      defaultText = lib.literalExpression "pkgs/comfyui/package.nix (this flake's own ComfyUI build)";
      description = "The ComfyUI package (bin/comfyui) each generator runs.";
    };

    cpuOnly = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Append --cpu to the generator (VM tests only; asserted false on a GPU host).";
    };

    # GN22 — the one feed server's bind: a single port shared by every
    # world's world-scoped routes, on a loopback address only.
    feedPort = lib.mkOption {
      type = lib.types.port;
      description = "Loopback port the ONE feed server binds (every world's routes are world-scoped under /w/<name>/); must be pairwise distinct from every world's comfyPort.";
    };

    feedListenAddress = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1";
      description = "Bind address of the one feed server (asserted loopback: 127.x.x.x or ::1).";
    };

    # GN24 — the flip guard: POST /w/<world>/activate (the GPU handover)
    # refuses a second world flip inside this many seconds — one clock,
    # global across worlds, so a double-tap cannot thrash the card (0 =
    # never refuse). Rendered into /etc/comfy-worlds.json's top level as
    # flipGuardSeconds; the server reads the knob from the file, so no
    # unit argv changes with it.
    flipGuardSeconds = lib.mkOption {
      type = lib.types.int;
      default = 30;
      description = "Seconds POST /w/<w>/activate refuses a second world flip for (one flip clock, global across worlds; 0 = never refuse).";
    };

    worlds = lib.mkOption {
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            comfyPort = lib.mkOption {
              type = lib.types.port;
              description = "Loopback port the generator binds; distinct across worlds and from the one feedPort.";
            };
            # GN23 — the deck's demand signal: when a deck GET counts fewer
            # unseen renders than lowWater, the feed starts this world's
            # comfy-run oneshot (spec §5). Rendered into
            # /etc/comfy-worlds.json as deckLowWater; the server reads the
            # knob from the file, so no unit argv changes with it.
            deck = {
              lowWater = lib.mkOption {
                type = lib.types.int;
                default = 5;
                description = "Start the world's comfy-run supervisor when a deck GET counts fewer unseen renders than this (asserted >= 0).";
              };
            };
            # GN17 — the per-world authoring knobs the supervisor unit
            # renders. They ride these defaults until probe 3 (the cost
            # of one model up/down cycle) sets a measured lowWater; the
            # runbook's tuning table is where the operator changes them.
            author = {
              promptsPerBatch = lib.mkOption {
                type = lib.types.int;
                default = 8;
                description = "Base prompts the author asks the model for per batch (M, --n-prompts).";
              };
              verdictWindow = lib.mkOption {
                type = lib.types.int;
                default = 20;
                description = "Liked/disliked verdict window the author reads (K, --window).";
              };
              variantsPerPrompt = lib.mkOption {
                type = lib.types.int;
                default = 3;
                description = "Variants per authored prompt comfy-mutate enqueues (N, --n-variants).";
              };
              lowWater = lib.mkOption {
                type = lib.types.int;
                default = 2;
                description = "Author a batch when at most this many jobs are queued (--low-water).";
              };
              tickSeconds = lib.mkOption {
                type = lib.types.int;
                default = 120;
                description = "Seconds between supervisor iterations (--tick).";
              };
              # GN21 — the two model-facing budgets, kept apart: the wait
              # budget is for a server that does not exist yet; the read
              # timeout is how long a live, generating model may think per
              # request (terminal when exceeded, never retried).
              modelWait = lib.mkOption {
                type = lib.types.int;
                default = 120;
                description = "Seconds comfy-author keeps retrying a model that is not up yet: refused/reset connections and retryable statuses (--model-wait).";
              };
              modelTimeout = lib.mkOption {
                type = lib.types.int;
                default = 300;
                description = "Seconds one request may wait on a live, generating model before it is abandoned (--model-timeout; default from 8 prompts at ~60 tok/s, with room for a colder cache or a bigger model).";
              };
              # GN52 — the raised history (Decision 8): prior authored
              # batches the author checks for duplicate prompts.
              historyBatches = lib.mkOption {
                type = lib.types.int;
                default = 100;
                description = "Prior authored batches the author checks for duplicate prompts (--history).";
              };
            };
          };
        }
      );
      default = { };
      description = "Per-world definition (name matches ^[a-z][a-z0-9-]{0,15}$).";
    };

    mutate = {
      perLike = lib.mkOption {
        type = lib.types.int;
        default = 3;
        description = "Prompt variants per liked render the mutator enqueues (--n).";
      };
    };

    # GN17 — the authoring loop's model-facing settings, shared by every
    # world's comfy-run unit. modelPath/modelSha256 are provenance only
    # (forwarded to comfy-author for the batch file; empty = not
    # forwarded) — the digest the model unit itself verifies is
    # services.local-model's, wired on core by GN19.
    author = {
      modelUrl = lib.mkOption {
        type = lib.types.str;
        default = "http://127.0.0.1:8790";
        description = "The loopback model URL the supervisor forwards to comfy-author.";
      };
      modelUnit = lib.mkOption {
        type = lib.types.str;
        default = "comfy-author-model.service";
        description = "The model user unit (GN14) the supervisor starts and stops around each authoring batch.";
      };
      modelPath = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "The GGUF path forwarded to comfy-author for the batch file's provenance record (empty: not forwarded).";
      };
      modelSha256 = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "The GGUF sha256 forwarded to comfy-author for the batch file's provenance record (empty: not forwarded).";
      };
    };

    # GN52 — the per-world card unit (spec 2026-09-21-lora-cards §3.2):
    # the lookup template and its broker. The host named by lookupUrl
    # must be listed in the named instance's allow — refused at eval (the
    # allowlist is the operator's decision), never a runtime 403.
    cards = {
      enable = lib.mkEnableOption "the per-world card unit: comfy-cards' network arm through the media broker (spec 2026-09-21-lora-cards §3.2)";
      lookupUrl = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "The lookup template: https, one {sha256} placeholder, its host listed in the broker instance's allow.";
      };
      brokerInstance = lib.mkOption {
        type = lib.types.str;
        default = "media";
        description = "The services.egress-broker.instances entry the card unit's egress crosses; its hostAddress/listenPort render HTTPS_PROXY and its ca/ca.pem renders SSL_CERT_FILE. Asserted present when cards.enable.";
      };
      timeoutSeconds = lib.mkOption {
        type = lib.types.int;
        default = 30;
        description = "The lookup's socket timeout, in seconds (--timeout).";
      };
    };

    refresh = {
      enable = lib.mkEnableOption "the weekly comfy-upstream-probe user timer (proposes the latest ComfyUI pin; never runs a model and never touches the live system)";
      onCalendar = lib.mkOption {
        type = lib.types.str;
        default = "Sun *-*-* 04:00:00";
        description = "systemd OnCalendar for the weekly probe (default Sunday 04:00).";
      };
      repo = lib.mkOption {
        type = lib.types.str;
        default = "/home/${cfg.operatorUser}/flakes/media";
        description = "The media flake the probe reads pins from and — outside dry run — clones to propose against.";
      };
      hostDriver = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "The host's NVIDIA driver version to compare the production branch against; the host wiring sets it to config.hardware.nvidia.package.version (the module never evaluates the NVIDIA package itself).";
      };
      brokerInstance = lib.mkOption {
        type = lib.types.str;
        default = "media";
        description = "The services.egress-broker.instances entry the probe's egress crosses; its hostAddress/listenPort render HTTPS_PROXY and its ca/ca.pem renders SSL_CERT_FILE. Asserted present when refresh.enable.";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = lib.all nameOk worldNames;
        message = "services.comfyui-worlds.worlds has an invalid world name (must match ^[a-z][a-z0-9-]{0,15}$): ${
          toString (lib.filter (n: !(nameOk n)) worldNames)
        }";
      }
      {
        assertion = comfyPortsDistinct;
        message = "services.comfyui-worlds: comfyPort must be pairwise distinct across all worlds and apart from feedPort";
      }
      {
        assertion = !(lib.elem cfg.feedPort comfyPorts);
        message = "services.comfyui-worlds: feedPort must not collide with any world's comfyPort";
      }
      {
        assertion = feedListenLoopback;
        message = "services.comfyui-worlds.feedListenAddress must be loopback (127.x.x.x or ::1), got '${cfg.feedListenAddress}'";
      }
      {
        # GN23 — the deck's low-water knob is an int >= 0 (0 = never start
        # on demand; negative water is meaningless).
        assertion = lib.all (w: cfg.worlds.${w}.deck.lowWater >= 0) worldNames;
        message = "services.comfyui-worlds.worlds.<w>.deck.lowWater must be an integer >= 0: ${
          toString (lib.filter (w: cfg.worlds.${w}.deck.lowWater < 0) worldNames)
        }";
      }
      {
        # GN24 — the flip guard window is an int >= 0 (0 = the guard never
        # holds; negative seconds is meaningless).
        assertion = cfg.flipGuardSeconds >= 0;
        message = "services.comfyui-worlds.flipGuardSeconds must be an integer >= 0";
      }
      {
        assertion = lib.hasPrefix "/" cfg.root;
        message = "services.comfyui-worlds.root must be an absolute path";
      }
      {
        assertion = !cfg.refresh.enable || brokerExists;
        message = "services.comfyui-worlds.refresh.brokerInstance '${brokerInst}' has no matching services.egress-broker.instances entry";
      }
    ]
    ++ lib.optionals cfg.cards.enable [
      {
        # (a) the scheme — https only; the tool's own loopback
        # carve-out is for hand runs, never the unit.
        assertion = lib.hasPrefix "https://" cfg.cards.lookupUrl;
        message = "services.comfyui-worlds.cards.lookupUrl must be an https:// URL";
      }
      {
        # (b) the placeholder — exactly one {sha256}.
        assertion = builtins.length (lib.splitString "{sha256}" cfg.cards.lookupUrl) == 2;
        message = "services.comfyui-worlds.cards.lookupUrl must contain {sha256} exactly once";
      }
      {
        # (c) the broker instance must exist (the refresh pattern).
        assertion = cardsBrokerExists;
        message = "services.comfyui-worlds.cards.brokerInstance '${cardsBrokerInst}' has no matching services.egress-broker.instances entry";
      }
      {
        # (d) the host allowlist — the operator's decision, enforced at
        # eval, never a runtime 403. Guarded by (c) through || so a
        # missing instance is (c)'s clean message, never a raw attribute
        # error (the brokerExists pattern).
        assertion =
          !cardsBrokerExists
          || lib.elem cardsLookupHost config.services.egress-broker.instances.${cardsBrokerInst}.allow;
        message = "services.comfyui-worlds.cards.lookupUrl names host ${cardsLookupHost}, which services.egress-broker.instances.${cardsBrokerInst}.allow does not list — the allowlist is the operator's decision (docs/superpowers/specs/2026-09-21-lora-cards-and-coupling-design.md §9)";
      }
    ];

    systemd = {
      user = {
        services = lib.mkMerge [
          (lib.listToAttrs (map (w: lib.nameValuePair "comfyui-${w}" (genUnit w)) worldNames))
          { comfy-feed = feedUnit; }
          (lib.listToAttrs (map (w: lib.nameValuePair "comfy-mutate-${w}" (mutateUnit w)) worldNames))
          (lib.listToAttrs (map (w: lib.nameValuePair "comfy-run-${w}" (runUnit w)) worldNames))
          (lib.mkIf cfg.cards.enable (
            lib.listToAttrs (map (w: lib.nameValuePair "comfy-cards-${w}" (cardsUnit w)) worldNames)
          ))
          (lib.mkIf cfg.refresh.enable {
            comfy-upstream-probe = {
              description = "Weekly ComfyUI upstream probe (model-free proposal)";
              unitConfig.ConditionUser = cfg.operatorUser;
              serviceConfig = {
                ExecStart = "${worldsPkgs.comfy-upstream-probe}/bin/comfy-upstream-probe --repo ${cfg.refresh.repo}${
                  lib.optionalString (cfg.refresh.hostDriver != null) " --host-driver ${cfg.refresh.hostDriver}"
                }";
                Environment = lib.optionals brokerExists [
                  "HTTPS_PROXY=${probeProxy}"
                  "SSL_CERT_FILE=${probeCa}"
                ];
                ProtectHome = "read-only";
                # `nix flake check` writes the fetcher cache and nix's state dir
                # on every run; ProtectHome=read-only otherwise kills it with
                # "attempt to write a readonly database" (CLAUDE.md gotchas,
                # nixos-agent-env nixosModules/helm.nix helm-flake-check). The
                # evidence store and the probe's own workspace/reports are the
                # only other writable paths.
                ReadWritePaths = [
                  "-%h/factory/ws/comfy-refresh"
                  "-%h/factory/runs/comfy-refresh"
                  "-%h/.cache/nix"
                  "-%h/.local/state/nix"
                  "-/var/lib/evidence"
                ];
              };
            };
          })
        ];

        timers = lib.mkIf cfg.refresh.enable {
          comfy-upstream-probe = {
            wantedBy = [ "timers.target" ];
            timerConfig = {
              OnCalendar = cfg.refresh.onCalendar;
              Persistent = true;
            };
          };
        };

        targets = lib.listToAttrs (map (w: lib.nameValuePair "comfy-world-${w}" (targetUnit w)) worldNames);
      };
    };

    environment.systemPackages = [
      worldsPkgs.media-comfy
      worldsPkgs.comfy-worlds-init
      worldsPkgs.comfy-mutate
      worldsPkgs.comfy-author
      worldsPkgs.comfy-run
      # GN18 — the owed PATH fix (spec §4 Change 7): the one definition in
      # worldsPkgs, no inline copy.
      worldsPkgs.media-fetch-models
      # GN52 — the card tool's offline arm is the operator's hand tool:
      # on PATH unconditionally (the unit behind it needs cards.enable;
      # the tool itself does not).
      worldsPkgs.comfy-cards
    ]
    ++ lib.optional cfg.refresh.enable worldsPkgs.comfy-upstream-probe;

    environment.etc."comfy-worlds.json" = {
      # GN22: the one server's shape — the root, the one feedPort, the sorted
      # worldsOrder (the `/` redirect's fallback head) and every world's
      # comfyPort. No per-world feedPort: the port belongs to the server.
      # GN23: each world also carries deckLowWater (the deck's demand
      # signal; the server reads the knob from the file). GN24: the top
      # level carries flipGuardSeconds (the activate route's guard window).
      source = (pkgs.formats.json { }).generate "comfy-worlds.json" {
        inherit (cfg) root feedPort flipGuardSeconds;
        worldsOrder = lib.sort (a: b: a < b) worldNames;
        worlds = lib.mapAttrs (_: v: {
          inherit (v) comfyPort;
          deckLowWater = v.deck.lowWater;
        }) cfg.worlds;
      };
      mode = "0644";
    };
    # GN26 — nothing else: no users.groups, no services.caddy, no tmpfiles
    # rule and no firewall line. The LAN face (site, credential, listener)
    # is services.lan-access's, declared by the host; a harness evaluating
    # this module alone proves the silence (checks.comfy-worlds-eval).
  };
}
