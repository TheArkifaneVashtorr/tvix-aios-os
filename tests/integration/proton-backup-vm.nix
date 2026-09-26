{
  pkgs,
  protonBackupModule,
}:
let
  mockCli = pkgs.writeShellScriptBin "proton-drive" (builtins.readFile ../mocks/proton-drive-mock.sh);
in
pkgs.testers.runNixOSTest {
  name = "proton-backup";
  nodes.machine =
    { pkgs, ... }:
    {
      imports = [ protonBackupModule ];
      users.users.alice = {
        isNormalUser = true;
        uid = 1000;
      };
      environment.etc."restic-password" = {
        text = "vm-test";
        mode = "0644";
      };
      systemd.tmpfiles.rules = [
        "d /var/lib/mock-remote 0777 root root -"
      ];
      systemd.user.services.proton-drive-push.environment = {
        MOCK_REMOTE_ROOT = "/var/lib/mock-remote";
        MOCK_CALLS = "/var/lib/mock-remote/calls.log";
      };
      services.proton-backup = {
        enable = true;
        user = "alice";
        passwordFile = "/etc/restic-password";
        paths = [
          "/etc/hostname"
          "/var/lib/sample"
        ];
        cliPackage = mockCli;
      };
      environment.systemPackages = [ pkgs.jq ];
    };
  testScript = ''
    machine.wait_for_unit("multi-user.target")
    machine.succeed("mkdir -p /var/lib/sample && echo hello > /var/lib/sample/f.txt")
    machine.succeed("loginctl enable-linger alice")
    machine.wait_until_succeeds("systemctl --user -M alice@ is-active timers.target")
    # 1. the restic job initializes and backs up into the local repository as alice
    machine.succeed("systemctl start restic-backups-core-local.service")
    machine.succeed("test -f /var/lib/restic/core/config")
    machine.succeed(
        "su alice -c 'RESTIC_PASSWORD_FILE=/etc/restic-password restic -r /var/lib/restic/core snapshots --json | jq -e \"length == 1\"'"
    )
    # 2. the cleanup kick reached alice's user manager and the push ran with the mock CLI
    machine.wait_until_succeeds("grep -q 'filesystem upload' /var/lib/mock-remote/calls.log")
    machine.succeed("test -f /var/lib/mock-remote/my-files/backups/core/config")
    machine.succeed("test $(ls /var/lib/mock-remote/my-files/backups/core/snapshots | wc -l) -eq 1")
    machine.fail("test -e /var/lib/mock-remote/my-files/backups/core/locks")
    # 3. the push unit itself reports parity OK (user-unit journal entries carry
    #    _SYSTEMD_USER_UNIT and are readable by root from the system journal).
    #    The kick above is systemctl --user start --no-block, so the oneshot
    #    unit (a few more mock CLI subprocess calls after the upload the
    #    previous assertions already observed) may still be finishing and
    #    journald catching up -- wait rather than a one-shot check.
    machine.wait_until_succeeds(
        "journalctl _SYSTEMD_USER_UNIT=proton-drive-push.service | grep -q 'proton-backup-push: OK snapshots=1 remote=1'"
    )
    # 4. restore drill from the local repository
    machine.succeed(
        "su alice -c 'RESTIC_PASSWORD_FILE=/etc/restic-password restic -r /var/lib/restic/core restore latest --target /tmp/restore'"
    )
    machine.succeed("grep -q hello /tmp/restore/var/lib/sample/f.txt")
    # 5. rclone is gone from the closure of this configuration
    machine.fail("command -v rclone")
  '';
}
