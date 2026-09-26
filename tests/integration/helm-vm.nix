{
  pkgs,
  helmModule,
}:
let
  fakeBasket = pkgs.writeShellScriptBin "basket" ''
    echo "PASS swap        no swap devices"
    echo "WARN vsock       module absent in VM"
  '';
in
pkgs.testers.runNixOSTest {
  name = "helm";
  nodes.machine =
    { pkgs, ... }:
    {
      imports = [ helmModule ];
      users.users.alice = {
        isNormalUser = true;
        uid = 1000;
      };
      system.configurationRevision = "deadbeef";
      services.helm = {
        enable = true;
        operatorUser = "alice";
        repo = "/var/lib/fake-repo";
        basketPackage = fakeBasket;
        restic.repository = "/var/lib/no-such-repo";
        restic.passwordFile = "/etc/no-such-file";
        flakeCheck.enable = false;
        timers.system = [ ];
        timers.user = [ "helm-collect.timer" ];
        brokerInstances = [ ];
      };
      environment.systemPackages = [
        pkgs.curl
        pkgs.git
        pkgs.jq
      ];
    };
  testScript = ''
    machine.wait_for_unit("multi-user.target")
    machine.succeed("mkdir -p /var/lib/fake-repo && chown alice /var/lib/fake-repo")
    machine.succeed("su alice -c 'cd /var/lib/fake-repo && git init -q && git -c user.email=a@b -c user.name=a commit -q --allow-empty -m init'")
    machine.succeed("loginctl enable-linger alice")
    machine.wait_until_succeeds("systemctl --user -M alice@ is-active timers.target")
    machine.succeed("systemctl --user -M alice@ start helm-collect.service")
    machine.wait_for_file("/var/lib/helm/index.html")
    machine.wait_for_unit("static-web-server.socket")
    page = machine.succeed("curl -fsS http://127.0.0.1:7700/")
    assert "Helm" in page and "<script" not in page and "src=" not in page
    st = machine.succeed("cat /var/lib/helm/status.json")
    tiles = {t["name"]: t for t in __import__("json").loads(st)["tiles"]}
    assert set(tiles) == {
        "backup-snapshot",
        "backup-parity",
        "timers",
        "basket-doctor",
        "broker",
        "gpu",
        "host",
        "drift",
        "flake-check",
    }
    assert tiles["basket-doctor"]["status"] == "warn"
    assert tiles["timers"]["status"] == "ok"
    # deadbeef (system.configurationRevision above) vs the fake repo's real
    # HEAD -- must be "fail" for the right reason (the two revisions
    # genuinely differ, summary names both), not because nixos-version
    # itself was unreachable (Blocker fix, plan Task 0: that would show up
    # as "unknown", not "fail", so the status check below already catches
    # a regression there -- the summary check pins the *reason*).
    assert tiles["drift"]["status"] == "fail", tiles["drift"]
    assert "≠" in tiles["drift"]["summary"], tiles["drift"]
    listeners = machine.succeed("ss -ltn")
    assert "127.0.0.1:7700" in listeners and "0.0.0.0:7700" not in listeners and "*:7700" not in listeners
    machine.succeed("stat -c %a /var/lib/helm/status.json | grep -qx 640")
    machine.fail("su nobody -s /bin/sh -c 'cat /var/lib/helm/status.json'")
    # brokerInstances = [] above -> broker_audit_paths is empty -> the tile
    # must read "unknown", not "0 allow, 0 deny" (audit F20).
    assert tiles["broker"]["status"] == "unknown", tiles["broker"]
    # F1: /etc/helm/config.json holds paths only (no secret bytes -- the
    # restic password is referenced by path); world-readable so a switch
    # never strands a running session (or user@1000.service) behind a group
    # it was never re-credentialed into.
    machine.succeed("stat -c %a:%U /etc/helm/config.json | grep -qx '644:root'")
    machine.succeed("su nobody -s /bin/sh -c 'cat /etc/helm/config.json >/dev/null'")
    # F17: restic's own cache dir sits outside the served document root.
    # A GET of the (always empty, directory-index-off) /cache/ prefix can
    # never fail regardless of where the cache dir actually lives -- that
    # probed nothing. Two probes that can each fail on a real regression:
    #  - /var/lib/helm/cache is where the cache dir lived before this fix
    #    (nested under the served root, i.e. reachable); asserting it does
    #    not exist catches a regression back to that path.
    #  - with the cache dir at its current /var/lib/helm-cache, a file
    #    written there must not be reachable at either URL shape a
    #    misconfigured root could expose it under: /helm-cache/<file>
    #    would resolve if static-web-server's root were ever widened from
    #    /var/lib/helm to /var/lib (root = /var/lib -> /var/lib/helm-cache/
    #    hangs off "/helm-cache/"), and /cache/<file> is the URL shape the
    #    old, in-root /var/lib/helm/cache bug above would have produced.
    machine.fail("test -e /var/lib/helm/cache")
    machine.succeed("su alice -c 'touch /var/lib/helm-cache/blob'")
    machine.fail("curl -fsS http://127.0.0.1:7700/helm-cache/blob")
    machine.fail("curl -fsS http://127.0.0.1:7700/cache/blob")
    machine.succeed("stat -c %a:%U /var/lib/helm-cache | grep -qx '700:alice'")
  '';
}
