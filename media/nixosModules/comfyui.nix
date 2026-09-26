# services.comfyui — ComfyUI (nix-native, no container) running as a
# hardened systemd service inside the egress broker's network namespace,
# reachable only on loopback via a socket proxy, with all outbound traffic
# (the model fetch unit) forced through that broker instance. Sharing the
# netns is a placement fact, not a grant: inference needs no egress, so the
# comfyui.service unit carries no HTTP(S)_PROXY and sets HF_HUB_OFFLINE=1
# (plus TRANSFORMERS_OFFLINE, HF_HUB_DISABLE_TELEMETRY) to keep it offline
# by construction even though huggingface.co is reachable from that netns —
# only comfyui-fetch-models proxies out. Design:
# docs/superpowers/specs/2026-09-02-media-flake-design-rev3.md (rev 3.1).
#
# Supersedes the rootless-podman-container version (rev 2.1, superseded
# 2026-09-02): the container boundary is replaced by systemd hardening on
# a service whose entire code is in the read-only Nix store
# (packages.comfyui — pkgs/comfyui/package.nix — built nix-native against
# the host's own torch-bin cu128 pin). No podman, no
# hardware.nvidia-container-toolkit, no subuid range, no ComfyUI-Manager,
# no custom nodes (`--disable-all-custom-nodes` always). There is
# deliberately no `extraArgs` option (rev 3.1): an open list appended to
# ExecStart could re-enable CORS or a listener the hardening above exists
# to prevent.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.comfyui;

  # Whether cfg.brokerInstance names a services.egress-broker.instances
  # entry that some OTHER module (the host's own broker wiring, or
  # checks/eval-harness.nix's stub instance) actually supplied
  # hostAddress/namespaceAddress for. This is NOT the same question as
  # `config.services.egress-broker.instances ? ${cfg.brokerInstance}`:
  # this module's own `config` below unconditionally sets
  # `instances.${cfg.brokerInstance} = { inject = ...; allow = ...; }`
  # whenever services.comfyui is enabled, so that key always exists in the
  # merged attrset — checking `?` would make the assertion below true
  # (and thus the whole comfyui-assertion-negative-broker check pass) no
  # matter what cfg.brokerInstance names, even "nope". hostAddress and
  # namespaceAddress have no default, so forcing them is what actually
  # distinguishes "some other module declared this instance for real"
  # from "only this module touched the key"; builtins.tryEval catches
  # both the "attribute missing" throw (key never touched by anyone) and
  # the "option accessed but has no value defined" throw (key touched
  # only by this module) uniformly, turning either into a clean `false`
  # instead of letting the raw error surface.
  brokerInstanceOk =
    let
      probe =
        attr:
        (builtins.tryEval config.services.egress-broker.instances.${cfg.brokerInstance}.${attr}).success;
    in
    probe "hostAddress" && probe "namespaceAddress";

  # Only forced after config.system.build.toplevel has decided NOT to
  # throw — see nixos/modules/system/activation/top-level.nix, which
  # computes `failedAssertions = map (x: x.message) (filter (x: !x.assertion)
  # config.assertions)` and throws before ever forcing the rest of config
  # when one fails. Note that `filter` forces EVERY assertion's `assertion`
  # field to build that list — including the listenAddress assertion below,
  # which is why that one is written `!brokerInstanceOk || ...` rather than
  # forcing `broker.namespaceAddress` unconditionally: an unguarded
  # comparison there would itself force this `broker` binding from INSIDE
  # assertion evaluation, before brokerInstanceOk had a chance to fail
  # closed, turning a bad brokerInstance into a raw "option accessed but
  # has no value defined" eval error instead of the intended
  # operator-facing assertion message (see checks.comfyui-assertion-negative-broker
  # and flake.nix's mkNegative, which reproduces top-level.nix's own
  # filter+map recipe specifically to catch this class of bug). With the
  # guard, config.assertions can always be fully filtered — including by
  # this binding below — without forcing `broker` on a bad instance name,
  # so by the time anything below (outside the assertions list) forces
  # `broker.hostAddress` etc., a real value is guaranteed to exist; no
  # dummy fallback is needed (or reachable).
  broker = config.services.egress-broker.instances.${cfg.brokerInstance};

  netns = "/run/netns/egress-${cfg.brokerInstance}";
  proxyUrl = "http://${broker.hostAddress}:${toString broker.listenPort}";
  caBundle = "/var/lib/egress-broker/${cfg.brokerInstance}/ca/ca-bundle.crt";

  listenAddress = if cfg.listen.address != null then cfg.listen.address else broker.namespaceAddress;

  # media-fetch-models is built from this repo's own checked-in source
  # (not from the flake's `self`) so the module stays self-contained for a
  # consumer that only imports nixosModules.default.
  mediaFetch = pkgs.writeShellApplication {
    name = "media-fetch-models";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 ${../pkgs/media-fetch/fetch.py} "$@"
    '';
  };
in
{
  options.services.comfyui = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Run ComfyUI as a hardened systemd service inside the egress broker's namespace, reachable only on loopback.";
    };

    package = lib.mkOption {
      type = lib.types.package;
      default = import ../pkgs/comfyui/package.nix { inherit pkgs; };
      defaultText = lib.literalExpression "pkgs/comfyui/package.nix (this flake's own ComfyUI build)";
      description = "The ComfyUI package (bin/comfyui) to run. Built nix-native against the host's own nixpkgs torch-bin pin — see pkgs/comfyui/package.nix.";
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = "comfyui";
      description = "System user the service runs as. No shell, no subuid range — this is a plain systemd service, not a container.";
    };

    group = lib.mkOption {
      type = lib.types.str;
      default = "comfyui";
      description = "System group for `user` and `dataDir`.";
    };

    dataDir = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/comfyui";
      description = ''
        Base directory for `user`, ComfyUI's `--base-directory` and the
        service's HOME: holds `models/ input/ output/ user/ temp/ cache/`
        (created by tmpfiles, 0750 `user group`). `models/` is read-only to
        the serving process (`ReadOnlyPaths`) — only the fetch unit writes
        there.
      '';
    };

    listen.address = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Address ComfyUI binds inside the namespace. Defaults to the broker instance's namespaceAddress — never a host interface.";
    };

    proxy.listen = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1:8188";
      description = "Host-side loopback listener (systemd-socket-proxyd) that forwards to ComfyUI inside the broker namespace. Must be loopback.";
    };

    gpu.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = ''
        Allow the service compute access to the NVIDIA GPU via
        `DevicePolicy=closed` + `DeviceAllow` on the device-GROUP names
        `char-nvidiactl`, `char-nvidia-frontend`, `char-nvidia-uvm`,
        `char-nvidia-caps` (the same set nixpkgs' own `services.ollama`
        uses; no modeset device — compute only). `DeviceAllow` does not
        glob `/dev` paths (systemd.resource-control(5)), so these are
        group names, not `/dev/nvidia*` literals. Requires
        `hardware.nvidia.package` to be set. `false` passes `--cpu`
        instead (used by the VM test, which has no GPU).
      '';
    };

    brokerInstance = lib.mkOption {
      type = lib.types.str;
      default = "media";
      description = "Name of the services.egress-broker.instances entry ComfyUI's netns, egress and (optionally) credential injection are wired to.";
    };

    models = {
      manifest = lib.mkOption {
        type = lib.types.path;
        default = ../models/manifest.toml;
        description = "Manifest consumed by media-fetch-models.";
      };

      hfTokenFile = lib.mkOption {
        # Deliberately `str`, not `path`: a Nix path literal would copy the
        # secret into the world-readable Nix store. This must be a plain
        # string naming a file outside the store, read at broker-service
        # start time by the broker itself — never by this module, the
        # fetch tool, or the comfyui service.
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Path to a file holding a Hugging Face token, outside the Nix store. When set, the broker injects it as `Authorization: Bearer <token>` on requests to huggingface.co; no other process ever sees it — never `HF_TOKEN` in any unit environment.";
      };

      civitai.enable = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Add civitai.com to the broker instance's allowlist.";
      };

      only = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        description = ''
          When non-empty, restrict the fetch unit to these manifest entry
          names: each name is passed as its own `--only <name>` to
          media-fetch-models (the tool appends the flag, one per name, not
          comma-separated). The default (`[ ]`) passes no `--only` at all,
          so every enabled manifest entry is fetched.
        '';
      };
    };

    resources.memoryMax = lib.mkOption {
      type = lib.types.str;
      default = "96G";
      description = "MemoryMax for comfyui.service.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = brokerInstanceOk;
        message = "services.comfyui.brokerInstance '${cfg.brokerInstance}' names no services.egress-broker.instances entry with hostAddress and namespaceAddress defined — declare that instance elsewhere in the configuration (e.g. the host's egress-broker wiring); enabling services.comfyui does not create it";
      }
      {
        assertion = lib.hasPrefix "127.0.0.1:" cfg.proxy.listen;
        message = "services.comfyui.proxy.listen must be loopback (127.0.0.1:<port>), got '${cfg.proxy.listen}'";
      }
      {
        assertion = cfg.models.hfTokenFile == null || !(lib.hasPrefix "/nix/store" cfg.models.hfTokenFile);
        message = "services.comfyui.models.hfTokenFile must be a path outside the Nix store (a Nix path literal would copy the secret into the store), got '${toString cfg.models.hfTokenFile}'";
      }
      {
        # DeviceAllow on the nvidia device-group names is meaningless
        # (and the service would fail to find the GPU) without an actual
        # driver configured on the host — catch that at eval time rather
        # than at service-start time. `hardware.nvidia.package` is NOT a
        # usable signal here: nixos/modules/hardware/video/nvidia.nix
        # gives it a non-null default (currently
        # config.boot.kernelPackages.nvidiaPackages.stable) regardless of
        # whether any driver was actually configured, so `!= null` can
        # never be false and the assertion would be a no-op. Check the
        # same condition hardware.nvidia-container-toolkit's own assertion
        # used to enforce for free before the container boundary was
        # dropped (see checks/eval-harness.nix's note on this): either
        # "nvidia" is in videoDrivers, or datacenter mode is on.
        assertion =
          !cfg.gpu.enable
          || (
            lib.elem "nvidia" config.services.xserver.videoDrivers || config.hardware.nvidia.datacenter.enable
          );
        message = "services.comfyui.gpu.enable requires an NVIDIA driver configured on the host (services.xserver.videoDrivers = [ \"nvidia\" ] or hardware.nvidia.datacenter.enable = true) or set services.comfyui.gpu.enable = false";
      }
      {
        # Guarded with `!brokerInstanceOk ||` so this assertion's own
        # condition never forces `broker.namespaceAddress` (and thus never
        # forces the `broker` binding above) when brokerInstance names no
        # real instance: NixOS's top-level.nix filters config.assertions by
        # forcing EVERY entry's `assertion` field to decide which failed
        # (see the WHY comment on `broker` above), so an unguarded
        # comparison here would blow up on a raw "has no value defined"
        # eval error for a bad brokerInstance before the brokerInstanceOk
        # assertion's own friendly message ever gets a chance to surface —
        # short-circuiting to `true` here when brokerInstanceOk is already
        # false lets that assertion (and only that one) report the failure,
        # exactly as checks.comfyui-assertion-negative-broker proves.
        assertion = !brokerInstanceOk || listenAddress == broker.namespaceAddress;
        message = "services.comfyui.listen.address must equal the broker instance's namespaceAddress (${broker.namespaceAddress}), got '${listenAddress}' — binding anything else exposes ComfyUI beyond the namespace's own address";
      }
    ];

    users.groups.${cfg.group} = { };
    users.users.${cfg.user} = {
      inherit (cfg) group;
      isSystemUser = true;
      home = cfg.dataDir;
    };

    services.egress-broker.instances.${cfg.brokerInstance} = {
      inject = lib.mkIf (cfg.models.hfTokenFile != null) (
        lib.mkDefault {
          "huggingface.co" = {
            header = "Authorization";
            prefix = "Bearer ";
            valueFile = cfg.models.hfTokenFile;
          };
        }
      );
      allow = lib.mkIf cfg.models.civitai.enable (lib.mkAfter [ "civitai.com" ]);
    };

    systemd = {
      tmpfiles.rules = [
        "d ${cfg.dataDir} 0750 ${cfg.user} ${cfg.group} -"
      ]
      ++ map (d: "d ${cfg.dataDir}/${d} 0750 ${cfg.user} ${cfg.group} -") [
        "models"
        "input"
        "output"
        "user"
        "temp"
        "cache"
      ]
      # ComfyUI's current split-file model folders (the ones the native
      # UNETLoader/CLIPLoader/VAELoader/LoraLoader/ControlNetLoader/
      # CLIPVisionLoader/UpscaleModelLoader and CheckpointLoaderSimple nodes
      # read from — models/manifest.toml's own dest-path comment names the
      # first four; the fetch unit's `install` refuses to create a
      # subfolder it lands a file into on demand, so every folder a
      # manifest `dest` can name must exist up front).
      ++ map (d: "d ${cfg.dataDir}/models/${d} 0750 ${cfg.user} ${cfg.group} -") [
        "checkpoints"
        "diffusion_models"
        "text_encoders"
        "vae"
        "loras"
        "clip_vision"
        "controlnet"
        "upscale_models"
      ];

      sockets.comfyui-proxy = {
        wantedBy = [ "sockets.target" ];
        listenStreams = [ cfg.proxy.listen ];
      };

      services = {
        comfyui = {
          description = "ComfyUI (nix-native, broker namespace, loopback via socket proxy)";
          wantedBy = [ "multi-user.target" ];
          requires = [
            "egress-netns-${cfg.brokerInstance}.service"
            "egress-broker-${cfg.brokerInstance}.service"
          ];
          after = [
            "egress-netns-${cfg.brokerInstance}.service"
            "egress-broker-${cfg.brokerInstance}.service"
            "systemd-tmpfiles-setup.service"
          ];
          environment = {
            HOME = cfg.dataDir;
            XDG_CACHE_HOME = "${cfg.dataDir}/cache";
            HF_HOME = "${cfg.dataDir}/cache/huggingface";
            TMPDIR = "${cfg.dataDir}/temp";
            NO_PROXY = "${broker.namespaceAddress},127.0.0.1,localhost";
            SSL_CERT_FILE = caBundle;
            # Offline by construction: the inference process shares the
            # broker's netns (huggingface.co is allowed there for the fetch
            # unit) but needs no egress of its own — no HTTP(S)_PROXY, and
            # these three vars keep the HF/transformers libraries from ever
            # attempting a network call even if some code path forgets to
            # pass local_files_only itself.
            HF_HUB_OFFLINE = "1";
            TRANSFORMERS_OFFLINE = "1";
            HF_HUB_DISABLE_TELEMETRY = "1";
          };
          serviceConfig = {
            User = cfg.user;
            Group = cfg.group;
            WorkingDirectory = cfg.dataDir;
            NetworkNamespacePath = netns;
            ExecStart = lib.escapeShellArgs (
              [
                "${cfg.package}/bin/comfyui"
                "--base-directory"
                cfg.dataDir
                "--listen"
                listenAddress
                "--port"
                "8188"
                "--disable-all-custom-nodes"
                "--dont-print-server"
                # comfy/cli_args.py computes database_default_path from
                # os.path.dirname(__file__) at import time — an
                # os.path.abspath(..., "..", "user", "comfyui.db") relative
                # to the package's own location inside the read-only Nix
                # store — and uses that as --database-url's default.
                # --base-directory does NOT redirect it: folder_paths.py
                # only rewrites base_path for models/input/output/user at
                # runtime, after cli_args has already computed the DB URL.
                # Without this flag the service starts but SQLite can never
                # open (or create) the database file, permanently
                # (`unable to open database file`), on every deployment,
                # VM test included. Point it at dataDir explicitly.
                "--database-url"
                "sqlite:///${cfg.dataDir}/user/comfyui.db"
              ]
              ++ lib.optional (!cfg.gpu.enable) "--cpu"
            );
            ProtectSystem = "strict";
            ProtectHome = true;
            ReadWritePaths = [ cfg.dataDir ];
            PrivateTmp = true;
            NoNewPrivileges = true;
            CapabilityBoundingSet = "";
            AmbientCapabilities = "";
            # AF_UNIX: libcuda opens an AF_UNIX socket during
            # cudaGetDeviceCount() init; without it the driver call fails
            # with "Error 304: OS call failed or operation not supported
            # on this OS" (bisected on core 2026-09-15 with systemd-run
            # --user throwaways running this unit's own python env — every
            # other directive passes alone, only RestrictAddressFamilies
            # without AF_UNIX reproduces it). AF_INET/AF_INET6 stay for the
            # in-namespace listener and the broker proxy.
            RestrictAddressFamilies = [
              "AF_INET"
              "AF_INET6"
              "AF_UNIX"
            ];
            RestrictNamespaces = true;
            LockPersonality = true;
            SystemCallFilter = [ "@system-service" ];
            SystemCallErrorNumber = "EPERM";
            # CUDA/torch JIT need executable memory; stated in the spec.
            MemoryDenyWriteExecute = false;
            PrivateDevices = false;
            DevicePolicy = "closed";
            # Device-GROUP names: DeviceAllow does not glob /dev paths
            # (systemd.resource-control(5)); the same set nixpkgs' own
            # services.ollama uses. Compute only — no modeset.
            DeviceAllow = lib.optionals cfg.gpu.enable [
              "char-nvidiactl rw"
              "char-nvidia-frontend rw"
              "char-nvidia-uvm rw"
              "char-nvidia-caps rw"
            ];
            InaccessiblePaths = [
              "/dev/shm"
              "-/run/dbus"
              "-/run/user"
            ];
            # The serving process never writes weights; only the fetch
            # unit does. The more specific path wins over ReadWritePaths.
            ReadOnlyPaths = [ "${cfg.dataDir}/models" ];
            MemoryMax = cfg.resources.memoryMax;
            Nice = 5;
            Restart = "on-failure";
            RestartSec = 10;
            TimeoutStartSec = "10min";
          };
        };

        comfyui-proxy = {
          description = "Loopback proxy to ComfyUI inside the broker namespace";
          requires = [ "comfyui-proxy.socket" ];
          after = [ "comfyui-proxy.socket" ];
          serviceConfig = {
            ExecStart = "${pkgs.systemd}/lib/systemd/systemd-socket-proxyd ${listenAddress}:8188";
            DynamicUser = true;
            PrivateTmp = true;
            NoNewPrivileges = true;
          };
        };

        comfyui-fetch-models = {
          description = "Fetch models from the manifest through the egress broker (run by hand)";
          requires = [
            "egress-netns-${cfg.brokerInstance}.service"
            "egress-broker-${cfg.brokerInstance}.service"
          ];
          after = [ "egress-broker-${cfg.brokerInstance}.service" ];
          environment = {
            HTTPS_PROXY = proxyUrl;
            HTTP_PROXY = proxyUrl;
          };
          serviceConfig = {
            Type = "oneshot";
            User = cfg.user;
            Group = cfg.group;
            NetworkNamespacePath = netns;
            ExecStart = lib.escapeShellArgs (
              [
                "${mediaFetch}/bin/media-fetch-models"
                "--manifest"
                "${cfg.models.manifest}"
                "--dest"
                "${cfg.dataDir}/models"
                "--cafile"
                caBundle
              ]
              ++ lib.concatMap (n: [
                "--only"
                n
              ]) cfg.models.only
            );
            NoNewPrivileges = true;
            ProtectSystem = "strict";
            ReadWritePaths = [ "${cfg.dataDir}/models" ];
            PrivateTmp = true;
          };
        };
      };
    };

    environment.systemPackages = [ mediaFetch ];
  };
}
