{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.evidence-store;
  # The whole directory, not the lone file: evidence.py imports its sibling
  # claims.py at run time (E9's bundle), and a file-valued path would copy
  # only evidence.py into the store.
  evidenceSrc = ../pkgs/evidence;
  evidenceCli = pkgs.writeShellApplication {
    name = "evidence";
    runtimeInputs = [
      pkgs.python3
      pkgs.git
    ];
    text = ''
      export EVIDENCE_STORE="''${EVIDENCE_STORE:-${cfg.path}}"
      exec python3 ${evidenceSrc}/evidence.py "$@"
    '';
  };
in
{
  options.services.evidence-store = {
    enable = lib.mkEnableOption "the append-only evidence store (JSONL streams; docs/superpowers/plans/2026-09-05-evidence-store.md)";
    path = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/evidence";
      description = "Directory holding the streams. Must be absolute; added to the backup paths by the host.";
    };
    owner = lib.mkOption {
      type = lib.types.str;
      default = "dalhaka";
      description = "Owner of the store; every writer runs as this user.";
    };
    group = lib.mkOption {
      type = lib.types.str;
      default = "users";
      description = "Group of the store directory (0750).";
    };
    package = lib.mkOption {
      type = lib.types.package;
      default = evidenceCli;
      defaultText = "the evidence CLI wrapping pkgs/evidence/evidence.py";
      description = "The evidence CLI other modules may reference.";
    };
  };
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = lib.hasPrefix "/" cfg.path;
        message = "services.evidence-store.path must be absolute";
      }
    ];
    systemd.tmpfiles.rules = [
      "d ${cfg.path} 0750 ${cfg.owner} ${cfg.group} -"
      "d ${cfg.path}/ledger 0750 ${cfg.owner} ${cfg.group} -"
    ];
    environment.systemPackages = [ cfg.package ];
  };
}
