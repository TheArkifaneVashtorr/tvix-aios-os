{
  pkgs,
  lanAccessModule,
}:
pkgs.testers.runNixOSTest {
  name = "lan-access";
  nodes.server =
    { pkgs, ... }:
    {
      imports = [ lanAccessModule ];
      networking.hostName = "server";
      # The module's `tls internal` renders an internal CA whose root caddy
      # would otherwise auto-install into the system trust store; NixOS's
      # /etc is read-only, so that install fails and blocks caddy from ever
      # binding its ports. The drill's row 2 installs the root by hand, so
      # skip the auto-install here (Interface 6's "trusted only where the
      # operator installs it").
      services.caddy.globalConfig = "skip_install_trust";
      services.lan-access = {
        enable = true;
        interface = "eth1";
        sites.helm = {
          upstream = "127.0.0.1:7700";
          hashFile = "/var/lib/lan-access/helm.bcrypt";
          user = "tester";
          # Interface 9: the CA bootstrap -- /ca.crt over plain HTTP, behind
          # the same credential, so a phone can fetch the root it must trust
          # without a file transfer and without clicking past a warning.
          caBootstrap = true;
          # Interface 10: the site also answers on a bare address over plain
          # HTTP, so a device that cannot resolve the .local name (or trust
          # the internal CA) still reaches it with the password alone.
          plainHttp = [ "server" ];
        };
      };
      systemd = {
        # Writes the bcrypt hash before caddy loads its config (a oneshot, since
        # systemd.tmpfiles cannot run a program). The plaintext "secret" is a
        # fixture, never a credential. Wanted at boot rather than Required-by
        # caddy: a hard `requiredBy` would re-run this oneshot on every caddy
        # restart and overwrite the malformed hash Interface 8 plants.
        services = {
          lan-vm-hash = {
            before = [ "caddy.service" ];
            wantedBy = [ "multi-user.target" ];
            serviceConfig.Type = "oneshot";
            script = ''
              install -d -m 0710 -o root -g caddy /var/lib/lan-access
              ${pkgs.caddy}/bin/caddy hash-password --plaintext secret > /var/lib/lan-access/helm.bcrypt
              chown caddy:caddy /var/lib/lan-access/helm.bcrypt
              chmod 0400 /var/lib/lan-access/helm.bcrypt
            '';
          };
          # The declared loopback upstream the site reverse-proxies.
          upstream-7700 = {
            wantedBy = [ "multi-user.target" ];
            script = "cd ${pkgs.writeTextDir "index.html" "LAN-VM-BODY"}; exec ${pkgs.python3}/bin/python3 -m http.server 7700 --bind 127.0.0.1";
          };
          # An undeclared listener that binds 0.0.0.0: the firewall must still hide it.
          undeclared-8080 = {
            wantedBy = [ "multi-user.target" ];
            script = "exec ${pkgs.python3}/bin/python3 -m http.server 8080 --bind 0.0.0.0";
          };
        };
      };
    };
  nodes.client =
    { pkgs, ... }:
    {
      environment.systemPackages = [ pkgs.curl ];
      # The test driver numbers nodes in attr-name order (client < server), so
      # `server` lands on 192.168.1.2 while `client` takes .1. Point the vhost
      # name at the server's actual address (network.nix only wires `server`,
      # not `helm.server.local`).
      networking.hosts."192.168.1.2" = [ "helm.server.local" ];
    };
  testScript = ''
    start_all()
    server.wait_for_unit("caddy.service")
    server.wait_for_unit("upstream-7700.service")
    server.wait_for_unit("undeclared-8080.service")

    # Interface 1: copy the internal CA root to the client (the same file the
    # drill's row 2 names), so the client can trust caddy's internal CA.
    root_cert = server.succeed(
        "cat /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt"
    )
    client.succeed("cat > /tmp/root.crt <<'LANVMROOT'\n" + root_cert + "\nLANVMROOT\n")

    # Interface 2: no credentials -> 401.
    code = client.succeed(
        "curl --cacert /tmp/root.crt -s -o /dev/null -w '%{http_code}' https://helm.server.local/"
    )
    assert code.strip() == "401", f"expected 401, got {code.strip()}"

    # Interface 3: credentials -> 200 and body LAN-VM-BODY.
    code = client.succeed(
        "curl --cacert /tmp/root.crt -u tester:secret -s -o /dev/null -w '%{http_code}' https://helm.server.local/"
    )
    assert code.strip() == "200", f"expected 200, got {code.strip()}"
    body = client.succeed(
        "curl --cacert /tmp/root.crt -u tester:secret -s https://helm.server.local/"
    )
    assert body.strip() == "LAN-VM-BODY", f"expected LAN-VM-BODY, got {body.strip()}"

    # Interface 4: the undeclared listener is refused (the firewall hides it
    # even though it binds 0.0.0.0).
    rc, code = client.execute(
        "curl -m 3 -s -o /dev/null -w '%{http_code}' http://server:8080/"
    )
    assert code.strip() == "000", f"expected no response (000) on :8080, got {code.strip()}"

    # Interface 5: plain HTTP serves no body (Caddy's redirect).
    code = client.succeed(
        "curl -s -o /dev/null -w '%{http_code}' http://helm.server.local/"
    )
    assert code.strip() == "308", f"expected 308 on http://, got {code.strip()}"
    nbytes = client.succeed("curl -s http://helm.server.local/ | wc -c")
    assert nbytes.strip() == "0", f"expected 0 bytes on http://, got {nbytes.strip()}"

    # Interface 9: the CA bootstrap. /ca.crt is the ONE path plain HTTP
    # serves, and it is behind the same credential as everything else.
    code = client.succeed(
        "curl -s -o /dev/null -w '%{http_code}' http://helm.server.local/ca.crt"
    )
    assert code.strip() == "401", f"expected 401 on the unauthenticated bootstrap, got {code.strip()}"

    code = client.succeed(
        "curl -u tester:secret -s -o /dev/null -w '%{http_code}' http://helm.server.local/ca.crt"
    )
    assert code.strip() == "200", f"expected 200 on the authenticated bootstrap, got {code.strip()}"

    # The bytes served are the real root, and they are sufficient to trust the
    # https site -- the whole point of the bootstrap. Fetched over plain HTTP,
    # written to disk, then used as the only CA for a TLS connection.
    client.succeed(
        "curl -u tester:secret -s http://helm.server.local/ca.crt > /tmp/bootstrap.crt"
    )
    head = client.succeed("head -1 /tmp/bootstrap.crt")
    assert head.strip() == "-----BEGIN CERTIFICATE-----", f"not a PEM certificate: {head.strip()}"
    # Compared against the SERVER's own file, not the heredoc copy above --
    # that copy gains a trailing newline from its own delimiter, so a byte-exact
    # cmp against it tests the test rather than the route.
    served = client.succeed("cat /tmp/bootstrap.crt")
    assert served.strip() == root_cert.strip(), "the bootstrap served bytes that are not the server's root"
    code = client.succeed(
        "curl --cacert /tmp/bootstrap.crt -s -o /dev/null -w '%{http_code}' https://helm.server.local/"
    )
    assert code.strip() == "401", f"the bootstrapped root did not validate the site, got {code.strip()}"

    # And the bootstrap opens NOTHING else: every other path still redirects
    # with an empty body (Interface 5 above still holds, asserted here against
    # a path that is not /ca.crt).
    code = client.succeed(
        "curl -u tester:secret -s -o /dev/null -w '%{http_code}' http://helm.server.local/ca.crt/../"
    )
    assert code.strip() in ("308", "404"), f"the bootstrap leaked a second path, got {code.strip()}"

    # Interface 10: the plain-HTTP address serves the whole site, behind the
    # same credential, with no TLS and no name resolution involved.
    code = client.succeed(
        "curl -s -o /dev/null -w '%{http_code}' http://server/"
    )
    assert code.strip() == "401", f"expected 401 on plain http, got {code.strip()}"

    code = client.succeed(
        "curl -u tester:secret -s -o /dev/null -w '%{http_code}' http://server/"
    )
    assert code.strip() == "200", f"expected 200 on authenticated plain http, got {code.strip()}"

    body = client.succeed("curl -u tester:secret -s http://server/")
    assert body.strip() == "LAN-VM-BODY", f"plain http served the wrong upstream: {body.strip()}"

    # The named host is NOT changed by this: it still redirects to https, so
    # opting one address into plain HTTP does not downgrade the site itself.
    code = client.succeed(
        "curl -s -o /dev/null -w '%{http_code}' http://helm.server.local/"
    )
    assert code.strip() == "308", f"the named host stopped redirecting, got {code.strip()}"

    # Interface 6: without --cacert the TLS handshake fails (internal CA).
    rc, _ = client.execute("curl -s https://helm.server.local/")
    assert rc == 60, f"expected exit 60 without --cacert, got {rc}"

    # Interface 7: the rendered sites table.
    sites = server.succeed("cat /etc/lan-access/sites")
    assert sites.strip() == "helm 127.0.0.1:7700", sites

    # Interface 8: a malformed hash fails closed. Caddy may refuse the config
    # outright (connection refused) or serve 401 -- either is fail-closed, so
    # the restart itself is allowed to fail and the curl is read with execute.
    server.succeed("printf 'not-a-bcrypt-hash' > /var/lib/lan-access/helm.bcrypt")
    server.execute("systemctl restart caddy.service")
    rc, code = client.execute(
        "curl --cacert /tmp/root.crt -u tester:secret -s -o /dev/null -w '%{http_code}' https://helm.server.local/"
    )
    assert code.strip() != "200", f"malformed hash must fail closed, got {code.strip()}"
    # Re-run the oneshot to regenerate the hash; caddy serves again.
    server.succeed("systemctl restart lan-vm-hash.service caddy.service")
    code = client.succeed(
        "curl --cacert /tmp/root.crt -u tester:secret -s -o /dev/null -w '%{http_code}' https://helm.server.local/"
    )
    assert code.strip() == "200", f"expected 200 after rehash, got {code.strip()}"
  '';
}
