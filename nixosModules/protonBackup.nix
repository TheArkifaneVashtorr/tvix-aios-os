{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.proton-backup;
  pushScript = pkgs.writeShellApplication {
    name = "proton-backup-push";
    runtimeInputs = with pkgs; [
      coreutils
      findutils
      gnugrep
      jq
      util-linux
    ];
    text = builtins.readFile ../pkgs/proton-backup/push.sh;
  };
  userUid = toString config.users.users.${cfg.user}.uid;
in
{
  options.services.proton-backup = {
    enable = lib.mkEnableOption "daily restic backup to a local repository, mirrored to Proton Drive by the official CLI";
    user = lib.mkOption {
      type = lib.types.str;
      default = "operator";
      description = "Runs the restic job and the push; owns the keyring that holds the Proton Drive CLI login.";
    };
    repositoryPath = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/restic/core";
    };
    paths = lib.mkOption { type = lib.types.listOf lib.types.str; };
    exclude = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [
        "**/.pytest_cache"
        "**/.ruff_cache"
        "/home/*/.cache"
      ];
    };
    passwordFile = lib.mkOption {
      type = lib.types.str;
      default = "/home/${cfg.user}/.config/restic/password";
    };
    remoteParent = lib.mkOption {
      type = lib.types.str;
      default = "/my-files/backups";
    };
    backupOnCalendar = lib.mkOption {
      type = lib.types.str;
      default = "daily";
    };
    pushOnCalendar = lib.mkOption {
      type = lib.types.str;
      default = "*-*-* 00:30:00";
    };
    cliPackage = lib.mkOption {
      type = lib.types.package;
      description = "The proton-drive-cli package (built from the SDK tag by this flake).";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = config.users.users ? ${cfg.user} && config.users.users.${cfg.user}.uid != null;
        message = "services.proton-backup.user '${cfg.user}' must be a declared user with a fixed uid (the push unit needs /run/user/<uid>)";
      }
    ];

    environment.systemPackages = [
      pkgs.restic
      cfg.cliPackage
      pushScript
    ];

    systemd.tmpfiles.rules = [
      "d /var/lib/restic 0755 root root -"
      "d ${cfg.repositoryPath} 0700 ${cfg.user} users -"
    ];

    # restic keeps encrypting locally exactly as before; only the transport
    # changed (rclone -> official CLI, see docs/runbooks/backup.md).
    services.restic.backups.core-local = {
      inherit (cfg)
        user
        paths
        exclude
        passwordFile
        ;
      repository = cfg.repositoryPath;
      initialize = true;
      timerConfig = {
        OnCalendar = cfg.backupOnCalendar;
        Persistent = true;
      };
      pruneOpts = [
        "--keep-daily 7"
        "--keep-weekly 4"
        "--keep-monthly 6"
      ];
      checkOpts = [ "--read-data-subset=10%" ];
      # Best-effort immediate push after a successful backup: the push is a
      # user unit (it needs the operator's keyring); reach that user manager
      # through its runtime dir. If the operator is logged out, the push
      # timer at pushOnCalendar catches up. $SERVICE_RESULT is set by
      # systemd for ExecStopPost, where the module runs this command.
      backupCleanupCommand = ''
        if [ "''${SERVICE_RESULT:-}" = "success" ]; then
          XDG_RUNTIME_DIR=/run/user/${userUid} ${pkgs.systemd}/bin/systemctl --user start --no-block proton-drive-push.service \
            || echo "proton-backup: no user session to kick the push; the push timer will catch up"
        fi
      '';
    };

    systemd.user = {
      services.proton-drive-push = {
        description = "Mirror the local restic repository to Proton Drive (official CLI)";
        unitConfig.ConditionUser = cfg.user;
        environment = {
          PROTON_BACKUP_REPO = cfg.repositoryPath;
          PROTON_BACKUP_REMOTE_PARENT = cfg.remoteParent;
          PROTON_DRIVE_CLI = "${cfg.cliPackage}/bin/proton-drive";
          PROTON_DRIVE_LOG_LEVEL = "INFO";
        };
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${pushScript}/bin/proton-backup-push";
        };
      };
      timers.proton-drive-push = {
        description = "Daily Proton Drive push of the local restic repository";
        unitConfig.ConditionUser = cfg.user;
        wantedBy = [ "timers.target" ];
        timerConfig = {
          OnCalendar = cfg.pushOnCalendar;
          Persistent = true;
        };
      };
    };
  };
}
