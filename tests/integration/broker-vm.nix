{
  pkgs,
  egressBrokerModule,
}:
let
  testCerts =
    pkgs.runCommand "test-certs"
      {
        nativeBuildInputs = [ pkgs.openssl ];
      }
      ''
        mkdir -p $out
        openssl req -x509 -newkey rsa:2048 -nodes -days 2 \
          -keyout $out/ca.key -out $out/ca.crt -subj "/CN=test-ca"
        for h in allowed.test denied.test; do
          openssl req -newkey rsa:2048 -nodes \
            -keyout $out/$h.key -out $out/$h.csr -subj "/CN=$h" \
            -addext "subjectAltName=DNS:$h"
          openssl x509 -req -in $out/$h.csr -CA $out/ca.crt -CAkey $out/ca.key \
            -CAcreateserial -days 2 -copy_extensions copy -out $out/$h.crt
        done
      '';
  # Deterministic 3 MiB payload (plan Task 3: proves the broker streams large
  # bodies via stream_large_bodies instead of buffering them, and that the
  # audit log's bytes_in falls back to Content-Length for a streamed body
  # whose raw_content mitmproxy never buffered). Lives in its own directory
  # (served via nginx `root`, not `alias`) because gixy's alias_traversal
  # check refuses an `alias` on a location that doesn't end in "/".
  bigFileDir = pkgs.runCommand "big-file-dir" { } ''
    mkdir -p $out
    head -c 3145728 /dev/zero > $out/big
  '';
in
pkgs.testers.runNixOSTest {
  name = "egress-broker";
  nodes.machine =
    { pkgs, ... }:
    {
      imports = [ egressBrokerModule ];
      security.pki.certificateFiles = [ "${testCerts}/ca.crt" ];
      networking.hosts."127.0.0.1" = [
        "allowed.test"
        "denied.test"
      ];
      services.nginx = {
        enable = true;
        virtualHosts."allowed.test" = {
          onlySSL = true;
          sslCertificate = "${testCerts}/allowed.test.crt";
          sslCertificateKey = "${testCerts}/allowed.test.key";
          root = "${bigFileDir}";
          locations = {
            "/auth".extraConfig = ''
              default_type text/plain;
              return 200 "auth=$http_authorization";
            '';
            "/".extraConfig = ''
              default_type text/plain;
              return 200 "ok-allowed";
            '';
            # No extraConfig: falls through to the virtualHost's `root`
            # above, serving bigFileDir/big for GET /big.
            "/big" = { };
          };
        };
        virtualHosts."denied.test" = {
          onlySSL = true;
          sslCertificate = "${testCerts}/denied.test.crt";
          sslCertificateKey = "${testCerts}/denied.test.key";
          locations."/".extraConfig = ''
            default_type text/plain;
            return 200 "should-never-be-reachable";
          '';
        };
      };
      services.egress-broker.instances.agent1 = {
        hostAddress = "10.100.0.1";
        namespaceAddress = "10.100.0.2";
        allow = [ "allowed.test" ];
        inject."allowed.test".valueFile = "/run/broker-secret";
      };
      systemd.services = {
        "egress-broker-agent1" = {
          after = [ "broker-secret.service" ];
          requires = [ "broker-secret.service" ];
        };
        broker-secret = {
          wantedBy = [ "multi-user.target" ];
          serviceConfig.Type = "oneshot";
          serviceConfig.RemainAfterExit = true;
          script = ''
            umask 037
            echo "vm-test-secret" > /run/broker-secret
            chown root:egress-broker /run/broker-secret
          '';
        };
        # Throwaway unit proving BindReadOnlyPaths lands on NixOS's
        # *symlinked* /etc/ssl/certs/ca-certificates.crt -- the one
        # known-unknown of plan Task 2 (docs/superpowers/plans/
        # 2026-09-02-phase4b-cowork-sending-hang.md). Not wantedBy anything;
        # the testScript starts it explicitly. Same BindReadOnlyPaths shape
        # cowork.nix uses for real, against this test's own broker instance.
        overlay-probe = {
          description = "proves the broker CA overlay lands on the real ca-certificates.crt path";
          after = [ "egress-broker-agent1.service" ];
          requires = [ "egress-broker-agent1.service" ];
          serviceConfig = {
            Type = "oneshot";
            ProtectSystem = "strict";
            BindReadOnlyPaths = [
              "/var/lib/egress-broker/agent1/ca/ca-bundle.crt:/etc/ssl/certs/ca-certificates.crt"
            ];
          };
          script = ''
            set -euo pipefail
            # A line from THIS run's mitmproxy CA (regenerated every build, so
            # it can't be baked in at eval time) must appear verbatim in the
            # file the bind mount put at /etc/ssl/certs/ca-certificates.crt --
            # proving the overlay reached the real, symlinked destination
            # rather than silently no-op'ing onto an unused mount point.
            line=$(sed -n '2p' /var/lib/egress-broker/agent1/ca/ca.pem)
            grep -qF "$line" /etc/ssl/certs/ca-certificates.crt
          '';
        };
      };
      environment.systemPackages = [
        pkgs.curl
        pkgs.jq
      ];
    };
  testScript = ''
    machine.wait_for_unit("nginx.service")
    machine.wait_for_unit("egress-broker-agent1.service")
    machine.wait_until_succeeds(
        "test -f /var/lib/egress-broker/agent1/ca/mitmproxy-ca-cert.pem"
    )

    proxy = "-x http://10.100.0.1:3128 --cacert /var/lib/egress-broker/agent1/ca/mitmproxy-ca-cert.pem"
    curl = "ip netns exec egress-agent1 curl -s " + proxy

    # 1. allowlisted host succeeds through the broker
    out = machine.succeed(curl + " https://allowed.test/")
    assert "ok-allowed" in out, out

    # 2. credential injection reaches the upstream
    out = machine.succeed(curl + " https://allowed.test/auth")
    assert "auth=Bearer vm-test-secret" in out, out

    # 3. non-allowlisted host is denied at CONNECT (curl surfaces a proxy
    #    CONNECT 403 as an error message, not as an HTTP status code)
    out = machine.succeed(curl + " -S https://denied.test/ 2>&1 || true")
    assert "403" in out, out

    # 4. domain fronting: outer name allowed, inner Host denied -> 403
    out = machine.succeed(
        curl + " -H 'Host: denied.test' -o /dev/null -w '%{http_code}' https://allowed.test/ || true"
    )
    assert "403" in out, out

    # 4b. host-header routing trick (review r2-1-1): an absolute-form plain
    #     HTTP URL to a denied host with an allowlisted Host header must be
    #     refused before any connection, never credential-injected.
    code = machine.succeed(
        curl + " -H 'Host: allowed.test' -o /dev/null -w '%{http_code}' http://denied.test/ || true"
    )
    assert code.strip() == "403", f"host-header trick got {code}"
    machine.succeed(
        "jq -es '[.[] | select(.verdict==\"deny\" and (.reason | startswith(\"host-header-mismatch\")))] | length >= 1' /var/lib/egress-broker/agent1/audit.jsonl"
    )

    # 5. audit log carries correct verdicts, and the fronting denial names the mismatch
    machine.succeed(
        "jq -es '[.[] | select(.verdict==\"allow\")] | length >= 2' /var/lib/egress-broker/agent1/audit.jsonl"
    )
    machine.succeed(
        "jq -es '[.[] | select(.verdict==\"deny\" and (.reason | test(\"mismatch\")))] | length >= 1' /var/lib/egress-broker/agent1/audit.jsonl"
    )

    # 6. the netns has no route around the broker: direct traffic fails
    machine.fail(
        "ip netns exec egress-agent1 curl -s --max-time 3 https://allowed.test/"
    )

    # 7. no secret material in the audit log
    machine.fail("grep -q vm-test-secret /var/lib/egress-broker/agent1/audit.jsonl")

    # 8. broker CA overlay bundle (plan Task 2, cowork-sending-hang): the
    #    ExecStartPost export additionally writes ca-bundle.crt = the
    #    system CA bundle + this broker's CA, for Cowork's guest trust path.
    machine.wait_until_succeeds(
        "test -f /var/lib/egress-broker/agent1/ca/ca-bundle.crt"
    )
    ca_line = machine.succeed("sed -n '2p' /var/lib/egress-broker/agent1/ca/ca.pem").strip()
    machine.succeed(
        f"grep -qF '{ca_line}' /var/lib/egress-broker/agent1/ca/ca-bundle.crt"
    )
    machine.succeed(
        "[ \"$(grep -c 'BEGIN CERTIFICATE' /var/lib/egress-broker/agent1/ca/ca-bundle.crt)\" -ge 100 ]"
    )

    # 9. the overlay-probe unit proves a BindReadOnlyPaths mount of that
    #    same file lands on the real, symlinked
    #    /etc/ssl/certs/ca-certificates.crt destination -- the known-unknown
    #    this task exists to settle.
    machine.succeed("systemctl start overlay-probe.service")

    # 10. large body streaming (plan Task 3, cowork-sending-hang): a 3 MiB
    #     response is not buffered whole by mitmproxy (stream_large_bodies=1m)
    #     -- the client still receives every byte, unmodified.
    machine.succeed(curl + " -o /tmp/big.out https://allowed.test/big")
    size = machine.succeed("stat -c %s /tmp/big.out").strip()
    assert size == "3145728", size

    # 11. because that body was streamed, mitmproxy never buffered
    #     raw_content -- prove the audit log's bytes_in fell back to the
    #     Content-Length header rather than reporting 0.
    machine.succeed(
        "jq -es '[.[] | select(.path==\"/big\" and .verdict==\"allow\")] "
        "| length == 1 and .[0].bytes_in == 3145728' "
        "/var/lib/egress-broker/agent1/audit.jsonl"
    )

    # 12. assertions 10/11 alone would pass identically if the body had been
    #     buffered instead of streamed (a buffered raw_content is also
    #     3145728 bytes long). The mitmdump log line below is the only
    #     observable that distinguishes streamed from buffered at the
    #     broker, so it is the actual regression guard for the
    #     `--set stream_large_bodies=1m` line in egressBroker.nix.
    machine.succeed(
        "journalctl -u egress-broker-agent1 --no-pager "
        "| grep -q 'Streaming response from allowed.test'"
    )

    # 13. deny of a >1 MiB request body must not crash mitmproxy (plan Task
    #     3 review fix): mitmproxy cannot both answer with a 403 and stream
    #     (or buffer-then-restream past the same 1m limit) a request body,
    #     so policy.py's _deny_request kills flows whose body might stream
    #     instead. The client gets the connection closed rather than an
    #     HTTP 403 (ErrorCode.KILL carries no HTTP status), so this checks
    #     the audit log and the absence of a crash traceback, not the curl
    #     exit code. Reuses /tmp/big.out (3 MiB, from step 10) as the body
    #     for both a fronted request (outer name allowed, inner Host
    #     denied) and a plain, non-allowlisted host.
    machine.execute(
        curl + " --max-time 15 -H 'Host: denied.test' --data-binary @/tmp/big.out "
        "-o /dev/null https://allowed.test/"
    )
    machine.execute(
        curl
        + " --max-time 15 -X POST --data-binary @/tmp/big.out -o /dev/null http://denied.test/"
    )
    machine.succeed(
        "jq -es '[.[] | select(.verdict==\"deny\" and .bytes_out==3145728)] "
        "| length >= 2' /var/lib/egress-broker/agent1/audit.jsonl"
    )
    machine.fail(
        "journalctl -u egress-broker-agent1 --no-pager | grep -q 'mitmproxy has crashed'"
    )

    # 14. plan Task 1: a host-namespace process must not be able to spend the
    #     injected credential. The broker binds hostAddress:listenPort in the
    #     HOST namespace (mitmproxy is not itself inside egress-agent1), so
    #     without a firewall rule scoped to the veth, any local uid could
    #     proxy through it exactly like the in-namespace client above. Both
    #     the CONNECT/HTTP path and a raw TCP handshake must fail from the
    #     host's own namespace; the in-namespace path (checks 1-2 above)
    #     must keep succeeding.
    machine.fail(
        "curl -sS --max-time 5 -x http://10.100.0.1:3128 "
        "--cacert /var/lib/egress-broker/agent1/ca/mitmproxy-ca-cert.pem "
        "https://allowed.test/"
    )
    machine.fail("timeout 5 bash -c 'exec 3<>/dev/tcp/10.100.0.1/3128'")
  '';
}
