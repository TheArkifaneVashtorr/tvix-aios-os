{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.claude-managed-settings;
  jsonFormat = pkgs.formats.json { };

  # NOT guarded by cfg.enable: settingsFile (below) must render regardless of
  # enable, so a consumer like cowork.nix can use it as a per-user
  # ~/.claude/settings.json without turning on the machine-wide
  # /etc/claude-code/managed-settings.json write. This stays lazy exactly
  # like before -- nothing here is forced unless something reads
  # cfg.settingsFile (or the mkIf cfg.enable environment.etc block below), so
  # an unset/invalid brokerInstance on a host that never consumes either one
  # still never forces evaluation. A consumer that DOES read cfg.settingsFile
  # is responsible for having brokerInstance point at a real instance --
  # cowork.nix's own assertion (services.cowork.brokerInstance must exist)
  # already covers its consumption path.
  brokerExists = config.services.egress-broker.instances ? ${cfg.brokerInstance};
  broker =
    if brokerExists then config.services.egress-broker.instances.${cfg.brokerInstance} else null;
  proxyUrl =
    if broker == null then null else "http://${broker.hostAddress}:${toString broker.listenPort}";
  # ca.pem is the canonical export the broker's ExecStartPost guarantees
  # (mitmproxy's own confdir filenames vary by version).
  caPath = "/var/lib/egress-broker/${cfg.brokerInstance}/ca/ca.pem";

  # Base lockdown skeleton (docs/research-2026-09-02-derisk.md → managed-settings
  # section; verified field-level against the schema captured there). The three
  # lock keys — allowManagedDomainsOnly, sandbox.filesystem.allowManagedReadPathsOnly,
  # allowManagedPermissionRulesOnly — are load-bearing: array-type settings merge
  # across scopes without them, which would let an unmanaged settings.json widen
  # the allowlist.
  baseSettings = {
    permissions = {
      disableBypassPermissionsMode = "disable";
      defaultMode = "default";
    };
    allowManagedPermissionRulesOnly = true;
    allowManagedHooksOnly = true;
    allowManagedMcpServersOnly = true;
    allowedMcpServers = [ ];
    sandbox = {
      enabled = true;
      failIfUnavailable = true;
      allowUnsandboxedCommands = false;
      network = {
        inherit (cfg) allowedDomains;
        allowManagedDomainsOnly = true;
        strictAllowlist = true;
      };
      filesystem = {
        allowManagedReadPathsOnly = true;
      };
    };
    env = {
      HTTPS_PROXY = proxyUrl;
      HTTP_PROXY = proxyUrl;
      NODE_EXTRA_CA_CERTS = caPath;
    };
  };

  renderedSettings = jsonFormat.generate "claude-code-managed-settings.json" (
    lib.recursiveUpdate baseSettings cfg.extraSettings
  );
in
{
  options.services.claude-managed-settings = {
    enable = lib.mkEnableOption "the generated /etc/claude-code/managed-settings.json lockdown";

    brokerInstance = lib.mkOption {
      type = lib.types.str;
      description = ''
        Name of a services.egress-broker instance. Its hostAddress/listenPort
        become the HTTPS_PROXY/HTTP_PROXY env values, and its CA cert path
        becomes NODE_EXTRA_CA_CERTS. Must name an existing instance (asserted).
      '';
    };

    allowedDomains = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [
        "api.anthropic.com"
        "claude.ai"
        "statsig.anthropic.com"
        "assets-proxy.anthropic.com"
        "claude.com"
        # Cowork VM image (rootfs.img ~1.3 GB) + Claude Code harness bundle;
        # from audit-log denies 2026-09-02 (96 CONNECT denies at every
        # session start -- see docs/research-2026-09-02-cowork-sending-hang.md).
        "downloads.claude.ai"
      ];
      description = ''
        sandbox.network.allowedDomains — the managed-settings allowlist. Start
        minimal; grow ONLY from broker audit-log denies, one domain per commit
        (plan Task 1 known-unknowns / Task 2 telemetry note).
      '';
    };

    extraSettings = lib.mkOption {
      type = lib.types.attrsOf lib.types.anything;
      default = { };
      description = ''
        Extra managed-settings fields, deep-merged on top of the generated
        lockdown via lib.recursiveUpdate (this wins on any leaf conflict).
        Must never weaken the three lock keys or disableBypassPermissionsMode.
      '';
    };

    settingsFile = lib.mkOption {
      type = lib.types.path;
      readOnly = true;
      description = ''
        The rendered managed-settings JSON (same generator as the
        machine-wide /etc/claude-code/managed-settings.json this module
        writes when enable = true), exposed as a reusable store path.
        Available regardless of enable, so a consumer can provision it at a
        narrower scope instead -- e.g. nixosModules/cowork.nix symlinks it in
        as claude-app's user-scope ~/.claude/settings.json, confining the
        lockdown (and the proxy env it carries) to Cowork instead of
        applying it machine-wide.
      '';
    };
  };

  config = lib.mkMerge [
    { services.claude-managed-settings.settingsFile = renderedSettings; }

    (lib.mkIf cfg.enable {
      assertions = [
        {
          assertion = config.services.egress-broker.instances ? ${cfg.brokerInstance};
          message = "services.claude-managed-settings.brokerInstance '${cfg.brokerInstance}' has no matching services.egress-broker.instances entry";
        }
      ];

      environment.etc."claude-code/managed-settings.json".source = cfg.settingsFile;
    })
  ];
}
