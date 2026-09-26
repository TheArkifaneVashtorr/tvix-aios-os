# checks.comfyui-vm — end-to-end NixOS VM proof for services.comfyui on
# CPU, no GPU and no real egress-broker module involved (that module lives
# in nixos-agent-env and is a separate wiring factory's responsibility; see
# docs/superpowers/specs/2026-09-02-media-flake-design-rev3.md, "Testing").
#
# The node builds its OWN stand-in for what the real broker instance
# normally provides — a network namespace (`egress-media`) joined to the
# default namespace by a veth pair at 10.100.2.1/2 — via two systemd units
# defined right here in the test, `egress-netns-media.service` (creates the
# namespace and veth) and `egress-broker-media.service` (a no-op the real
# comfyui.service unit merely requires/orders after; see
# nixosModules/comfyui.nix). services.comfyui itself is exercised
# unmodified, with `gpu.enable = false` so it runs `--cpu`.
#
# This proves, on real systemd (not just module eval):
#   - the unit actually starts and serves through the loopback socket
#     proxy, not just that its ExecStart evaluates to the right string
#     (checks.comfyui-eval already covers that at eval time);
#   - the namespace is genuinely isolated — no egress without a broker in
#     the path — independent of whatever HTTPS_PROXY the unit sets;
#   - a real end-to-end generation (EmptyImage -> SaveImage, no model, no
#     GPU) produces a file, owned by the service user, under dataDir;
#   - the unit's own environment carries no credential.
{ pkgs, module }:
let
  emptyImageGraph = builtins.fromJSON (builtins.readFile ./workflows/empty-image.json);
  promptBody = pkgs.writeText "comfyui-vm-prompt.json" (
    builtins.toJSON {
      prompt = emptyImageGraph;
      client_id = "comfyui-vm-test";
    }
  );
in
pkgs.testers.nixosTest {
  name = "comfyui-vm";

  nodes.machine =
    { pkgs, ... }:
    {
      imports = [
        module
        (import ../../checks/stub-broker.nix)
      ];

      # allowUnfree is already set on the `pkgs` this VM is built from
      # (pkgs.testers.nixosTest below, same externally-created instance flake.nix
      # uses for every other check) — setting `nixpkgs.config` again here
      # trips NixOS's own externally-created-instance assertion.

      # Stand-in broker-instance record: same shape
      # services.egress-broker.instances.media provides for real, on the
      # real host. Only hostAddress/namespaceAddress/listenPort are read by
      # nixosModules/comfyui.nix; the units below actually create the
      # addresses this describes.
      services.egress-broker.instances.media = {
        hostAddress = "10.100.2.1";
        namespaceAddress = "10.100.2.2";
        listenPort = 3130;
      };

      systemd.services.egress-netns-media = {
        description = "Stand-in netns + veth for the media broker instance (test-defined, not the real broker module)";
        serviceConfig = {
          Type = "oneshot";
          RemainAfterExit = true;
          # Absolute path: systemd service units on NixOS do not inherit
          # environment.systemPackages' PATH, and `ip netns exec` re-execs
          # its argv via the same (empty here) PATH, so every `ip` call —
          # outer and inner — needs the store path spelled out.
          ExecStart = pkgs.writeShellScript "egress-netns-media-start" ''
            set -euo pipefail
            ip=${pkgs.iproute2}/bin/ip
            "$ip" netns add egress-media
            "$ip" link add veb-media type veth peer name ven-media
            "$ip" link set ven-media netns egress-media
            "$ip" addr add 10.100.2.1/30 dev veb-media
            "$ip" link set veb-media up
            "$ip" netns exec egress-media "$ip" addr add 10.100.2.2/30 dev ven-media
            "$ip" netns exec egress-media "$ip" link set ven-media up
            "$ip" netns exec egress-media "$ip" link set lo up
          '';
          ExecStop = pkgs.writeShellScript "egress-netns-media-stop" ''
            ${pkgs.iproute2}/bin/ip netns del egress-media
          '';
        };
      };

      systemd.services.egress-broker-media = {
        description = "No-op stand-in for the real egress-broker instance (test-defined): comfyui.service only needs this unit to exist and succeed, never a live proxy, since nothing in this VM test fetches through it";
        after = [ "egress-netns-media.service" ];
        requires = [ "egress-netns-media.service" ];
        serviceConfig = {
          Type = "oneshot";
          RemainAfterExit = true;
          ExecStart = "${pkgs.coreutils}/bin/true";
        };
      };

      services.comfyui = {
        enable = true;
        gpu.enable = false;
      };

      environment.systemPackages = [
        pkgs.curl
        pkgs.jq
        pkgs.iproute2
      ];

      # The torch-bin cu128 closure lands in the VM image regardless of
      # gpu.enable (the package is the same; only the runtime flag
      # differs) — several GB. diskSize >= 16 GB and a long first boot are
      # the accepted cost (spec rev 3.1, "Testing").
      virtualisation.memorySize = 6144;
      virtualisation.diskSize = 16384;
    };

  testScript = ''
    import json

    machine.wait_for_unit("comfyui.service")

    stats_json = machine.wait_until_succeeds(
        "curl -fsS http://127.0.0.1:8188/system_stats", timeout=600
    )
    stats = json.loads(stats_json)
    assert stats["system"]["comfyui_version"] == "0.34.5", (
        f"expected comfyui_version 0.34.5, got: {stats['system']}"
    )
    assert "cpu" in stats["devices"][0]["name"], (
        f"expected a cpu device, got: {stats['devices']}"
    )

    ss_out = machine.succeed("ss -ltn")
    assert "127.0.0.1:8188" in ss_out, f"proxy socket not listening on loopback: {ss_out}"
    assert "0.0.0.0:8188" not in ss_out, f"ComfyUI leaked onto a wildcard listener: {ss_out}"
    assert "*:8188" not in ss_out, f"ComfyUI leaked onto a wildcard listener: {ss_out}"

    # Fail-closed, made differential so it can actually fail (a plain
    # `curl https://example.com` fails identically in EITHER namespace here
    # — this VM has no DNS resolver at all, and a netns doesn't isolate
    # /etc/resolv.conf without a matching /etc/netns/<name>/resolv.conf —
    # so that alone would prove nothing about the namespace under test).
    # IP literals only, no hostnames, to keep DNS out of the picture:
    #   - the machine's own test-VLAN address (192.168.1.1, assigned by
    #     the NixOS test driver's default vlan) is reachable from the
    #     default namespace ...
    machine.succeed("ping -c1 -W2 192.168.1.1")
    #   - ... but NOT from inside egress-media, which has no interface
    #     onto that network at all;
    machine.fail("ip netns exec egress-media ping -c1 -W2 192.168.1.1")
    #   - the namespace's only reachable peer is the broker's host-side
    #     veth address (10.100.2.1) ...
    machine.succeed("ip netns exec egress-media ping -c1 -W2 10.100.2.1")
    #   - ... and it carries no default route out at all, so nothing
    #     beyond that one peer is even attempted.
    machine.fail("ip netns exec egress-media ip route get 1.1.1.1")
    # This set goes red immediately if egress-netns-media (or any future
    # replacement) ever grows a default route, NAT, or a second interface.

    # Verify-first item 0 (pkgs/comfyui/package.nix header) found that
    # server.py:244-249 registers app/assets/api/routes.py's HTTP
    # download route (GET /api/assets/{uuid}/content, alongside its
    # listing route GET /api/assets) UNCONDITIONALLY — the only thing
    # closing it is app/assets/api/routes.py's module-level
    # `_ASSETS_ENABLED = False`, flipped only by `--enable-assets`
    # (comfy/cli_args.py, off by default; nixosModules/comfyui.nix's
    # ExecStart never passes it, and rev 3.1 dropped `extraArgs` so a
    # user can't add it either). _require_assets_feature_enabled answers
    # 503 today; it answers 200 the moment --enable-assets is ever
    # passed. Pin that closure here so a future ExecStart edit that adds
    # the flag fails this check instead of shipping a live file-serving
    # route with every other check still green.
    machine.fail("curl -fsS http://127.0.0.1:8188/api/assets")
    # Paired with an ungated route (already asserted above) to prove the
    # fail above is the gate, not a dead server.
    machine.succeed("curl -fsS http://127.0.0.1:8188/system_stats")

    machine.succeed(
        "curl -fsS -X POST -H 'content-type: application/json' "
        "--data-binary @${promptBody} http://127.0.0.1:8188/prompt"
    )
    machine.wait_until_succeeds(
        "ls /var/lib/comfyui/output/vmtest_*.png", timeout=300
    )

    owner = machine.succeed(
        "stat -c %U /var/lib/comfyui/output/vmtest_*.png"
    ).strip()
    assert owner == "comfyui", f"output PNG owned by {owner!r}, expected comfyui"

    env_out = machine.succeed("systemctl show comfyui -p Environment --value")
    assert "TOKEN" not in env_out, f"comfyui.service environment leaked a TOKEN key: {env_out}"

    # comfy/cli_args.py's --database-url default is computed from
    # __file__ inside the read-only Nix store and can never be opened;
    # nixosModules/comfyui.nix overrides it to point at dataDir. Assert
    # the failure this would otherwise cause is actually gone (not just
    # that the unit is "active", which systemd reports regardless) and
    # that the database file was actually created where dataDir expects it.
    machine.fail(
        "journalctl -u comfyui --no-pager | grep -q 'Failed to initialize database'"
    )
    machine.succeed("test -f /var/lib/comfyui/user/comfyui.db")
  '';
}
