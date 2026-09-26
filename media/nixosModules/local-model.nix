# services.local-model — the local author model unit (GN14, spec §4 Change 1):
# one llama-server on loopback serving a single GGUF declared by path and
# digest (spec §1.2 — the 22 GB of weights never enter the store), guarded at
# EVERY start by comfy-model-guard (a wrong or drifted file fails the start
# loudly instead of serving quietly), and trading the GPU with the ComfyUI
# generators through systemd Conflicts= — turn-taking belongs to systemd,
# never to a script reading VRAM (spec §4, bold).
#
# The unit is a user service (ConditionUser = operatorUser) like the worlds'
# generators: it reads the model file under %h and must not be confined by a
# device filter — device filters are BPF cgroup programs the per-user manager
# cannot attach (comfyui-worlds.nix's measured note); PrivateDevices=false
# keeps /dev/nvidia* visible.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.local-model;

  # Every derivation the module uses comes from pkgs/comfy-worlds (imported
  # with the consuming host's pkgs — never self.packages), the same handle
  # nixosModules/comfyui-worlds.nix uses.
  worldsPkgs = import ../pkgs/comfy-worlds { inherit pkgs; };

  # The default conflicts list names every configured world's generator, so
  # starting the model hands the GPU back from whichever renderer holds it —
  # and, Conflicts= being symmetric, starting a renderer stops the model.
  # Guarded by module presence (config.services ? comfyui-worlds), not by the
  # worlds module's own enable: the ports and names exist either way.
  worldsConfigured =
    if config.services ? comfyui-worlds then config.services.comfyui-worlds.worlds else { };
  defaultConflicts = map (w: "comfyui-${w}.service") (builtins.attrNames worldsConfigured);

  # listenAddress is loopback: four integer octets 0–255 with the first byte
  # 127, or the literal ::1. Anything else (a LAN address, a hostname, empty)
  # is refused by assertion (d) — local inference, no broker instance.
  octets = builtins.match "^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$" cfg.listenAddress;
  octetOk =
    s:
    let
      n = lib.toInt s;
    in
    n >= 0 && n <= 255;
  listenLoopback =
    if octets != null then
      (lib.toInt (builtins.elemAt octets 0)) == 127 && lib.all octetOk octets
    else
      cfg.listenAddress == "::1";

  # Assertion (c): the model port must equal no configured world's
  # comfyPort and not the one feedPort — a collision would put the model
  # and a generator (or the feed) on one loopback port and the loser would
  # fail at bind time, far from the config that caused it. The feedPort is
  # read only when a world is configured: the option is required (GN22),
  # so an import of the worlds module with no worlds must not force it.
  worldsPorts =
    if config.services ? comfyui-worlds && config.services.comfyui-worlds.worlds != { } then
      (map (w: w.comfyPort) (builtins.attrValues config.services.comfyui-worlds.worlds))
      ++ [ config.services.comfyui-worlds.feedPort ]
    else
      [ ];
  portCollides = lib.elem cfg.port worldsPorts;
in
{
  options.services.local-model = {
    enable = lib.mkEnableOption "the local author model unit (llama-server on loopback, digest-guarded weights)";

    modelPath = lib.mkOption {
      type = lib.types.str;
      default = "";
      description = "Absolute path of the GGUF served (asserted outside /nix/store — the weights never enter the store, spec §1.2).";
    };

    sha256 = lib.mkOption {
      type = lib.types.str;
      default = "";
      description = "The GGUF's sha256 (64 lowercase hex); comfy-model-guard re-hashes the file on every unit start and refuses on mismatch.";
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 8790;
      description = "Loopback port llama-server binds (asserted distinct from every world's comfyPort and from the one feedPort).";
    };

    listenAddress = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1";
      description = "Bind address (asserted loopback: 127.x.x.x or ::1 — local inference, no broker instance).";
    };

    contextSize = lib.mkOption {
      type = lib.types.int;
      default = 8192;
      description = "llama-server context size (-c).";
    };

    gpuLayers = lib.mkOption {
      type = lib.types.int;
      default = 999;
      description = "Layers to store in VRAM (-ngl); an integer, never \"all\" — a str would admit it and be refused only at start.";
    };

    idleSleepSeconds = lib.mkOption {
      type = lib.types.int;
      default = 600;
      description = "Seconds of idleness after which llama-server sleeps (--sleep-idle-seconds; present in the built server's --help at the pin, GN14 step 1).";
    };

    conflicts = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = defaultConflicts;
      defaultText = lib.literalExpression "every comfyui-<w>.service of the configured worlds, else [ ]";
      description = "Units the model unit Conflicts= (default: both generators, so the GPU trades hands).";
    };

    operatorUser = lib.mkOption {
      type = lib.types.str;
      default = "operator";
      description = "The user the user-scope unit runs as (its ConditionUser); owns the model file.";
    };

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.llama-cpp;
      defaultText = lib.literalExpression "pkgs.llama-cpp";
      description = "The llama-cpp package (bin/llama-server) the unit runs.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = lib.hasPrefix "/" cfg.modelPath && !(lib.hasPrefix "/nix/store" cfg.modelPath);
        message = "services.local-model.modelPath must be an absolute path outside /nix/store (the GGUF is declared by path and digest, never copied into the store), got '${cfg.modelPath}'";
      }
      {
        assertion = builtins.match "[0-9a-f]{64}" cfg.sha256 != null;
        message = "services.local-model.sha256 must be 64 lowercase hex characters ([0-9a-f]{64}), got '${cfg.sha256}'";
      }
      {
        assertion = !portCollides;
        message = "services.local-model.port ${toString cfg.port} collides with a services.comfyui-worlds port (a world's comfyPort or the one feedPort)";
      }
      {
        assertion = listenLoopback;
        message = "services.local-model.listenAddress must be loopback (127.x.x.x or ::1 — local inference, no broker instance), got '${cfg.listenAddress}'";
      }
    ];

    systemd.user.services.comfy-author-model = {
      description = "Local author model (llama-server on loopback)";
      unitConfig.ConditionUser = cfg.operatorUser;
      inherit (cfg) conflicts;
      wantedBy = [ ];
      serviceConfig = {
        ExecStartPre = "${worldsPkgs.comfy-model-guard}/bin/comfy-model-guard ${cfg.modelPath} ${cfg.sha256}";
        ExecStart = "${cfg.package}/bin/llama-server --model ${cfg.modelPath} --host ${cfg.listenAddress} --port ${toString cfg.port} --no-webui -c ${toString cfg.contextSize} -ngl ${toString cfg.gpuLayers} --sleep-idle-seconds ${toString cfg.idleSleepSeconds}";
        ProtectSystem = "strict";
        ProtectHome = "read-only";
        ReadWritePaths = [ "%h/.cache" ];
        # Assumption 8's list minus -/home (ProtectHome covers it, and the
        # model file itself lives under %h): the baskets, Helm's state, the
        # broker's credentials/audit trail, and the provider key files are
        # ENOENT to the model server (invariant 2). A leading '-' keeps a
        # missing path from failing the start.
        InaccessiblePaths = [
          "-/run/baskets"
          "-/var/lib/baskets"
          "-/var/lib/helm"
          "-/var/lib/egress-broker"
          "-/var/lib/secrets"
        ];
        NoNewPrivileges = true;
        PrivateTmp = true;
        # The GPU: /dev/nvidia* must stay visible.
        PrivateDevices = false;
        # GN14 probe 1 (measured on this pin's test VM, systemd 261 user
        # manager): a user unit carrying IPAddressDeny=/IPAddressAllow=
        # starts, `systemctl --user show -p IPAddressDeny` renders the
        # value, and the journal records only the warning "unit configures
        # an IP firewall, but not running as root" — the per-user manager
        # cannot attach the cgroup BPF program, so the directives would be
        # a silent no-op that reads like a control (the same shape the
        # worlds module refuses for device filters). The fallback the plan
        # names is applied: the two directives are omitted, the no-egress
        # property rests on the loopback bind address (assertion (d)), and
        # the comfy-worlds-vm step pins the omitted state.
        # IPAddressDeny / IPAddressAllow deliberately absent.
      };
    };
  };
}
