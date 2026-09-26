{
  pkgs,
  egressBrokerModule,
  seatLaneModule,
  seatSubmit,
}:
let
  # Single-host variant of tests/integration/lane-vm.nix's testCerts: only
  # "openrouter.test" is needed here (the seat's broker instance allows
  # exactly one host, openrouter.test in this VM).
  testCerts =
    pkgs.runCommand "seat-vm-test-certs"
      {
        nativeBuildInputs = [ pkgs.openssl ];
      }
      ''
        mkdir -p $out
        openssl req -x509 -newkey rsa:2048 -nodes -days 2 \
          -keyout $out/ca.key -out $out/ca.crt -subj "/CN=seat-vm-test-ca"
        openssl req -newkey rsa:2048 -nodes \
          -keyout $out/openrouter.test.key -out $out/openrouter.test.csr \
          -subj "/CN=openrouter.test" -addext "subjectAltName=DNS:openrouter.test"
        openssl x509 -req -in $out/openrouter.test.csr -CA $out/ca.crt -CAkey $out/ca.key \
          -CAcreateserial -days 2 -copy_extensions copy -out $out/openrouter.test.crt
      '';
  # The one-turn answer the fake upstream hands back (streamed, the same SSE
  # wire shape tests/mocks/openai-fake.py uses because the real dsh harness
  # requests `stream: true` and only strips a streamed completion -- a plain
  # JSON 200 would not parse). Every POST gets it; the content is what the
  # testScript greps for to prove the full round trip, not just that *a* 200
  # came back.
  fakeContent = "vm-seat-answer";
  # A TLS server, not nginx (same reason as lane-vm.nix: nginx never reads a
  # request body for a bare `return 200`), which (1) answers dsh's discovery
  # probe GET /api/v1/models with a one-model listing, (2) answers every POST
  # with a streamed chat completion carrying `fakeContent`, and (3) logs the
  # request path and the Authorization header verbatim so the test can prove
  # the BROKER replaced the placeholder with the injected key.
  fakeUpstream = pkgs.writeText "seat-vm-fake-upstream.py" ''
    import http.server
    import json
    import ssl

    CONTENT = ${builtins.toJSON fakeContent}

    def _sse(obj):
        return b"data: " + json.dumps(obj).encode("utf-8") + b"\n\n"

    def _chunk(index, delta, finish=None, usage=None):
        body = {
            "id": f"chatcmpl-fake-{index}",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "fake/model",
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }
        if usage is not None:
            body["usage"] = usage
        return body

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_a):
            pass

        def _log(self, body):
            with open("/var/log/seat-vm-fake-upstream.log", "a") as f:
                f.write(self.command + " " + self.path + "\n")
                f.write(self.headers.get("Authorization", "") + "\n")
                if body:
                    f.write(body + "\n")
                f.write("---\n")

        def do_GET(self):
            self._log(None)
            if self.path.rstrip("/").endswith("/models"):
                body = json.dumps(
                    {"object": "list", "data": [{"id": "fake/model", "object": "model"}]}
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            self._log(raw.decode("utf-8", "replace"))
            usage = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(
                _sse(_chunk(0, {"role": "assistant", "content": CONTENT}))
            )
            self.wfile.write(_sse(_chunk(0, {}, "stop", usage)))
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    httpd = http.server.HTTPServer(("0.0.0.0", 443), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain("${testCerts}/openrouter.test.crt", "${testCerts}/openrouter.test.key")
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    httpd.serve_forever()
  '';
in
pkgs.testers.runNixOSTest {
  name = "seat-behind-broker";
  nodes.machine =
    { pkgs, ... }:
    {
      imports = [
        egressBrokerModule
        seatLaneModule
      ];
      security.pki.certificateFiles = [ "${testCerts}/ca.crt" ];
      networking.hosts."127.0.0.1" = [ "openrouter.test" ];
      # The "no route" / "second namespace" probes below rely on the host
      # actually forwarding cross-namespace packets far enough to hit the
      # forward-seat drop (rather than silently dying at ip_forward=0).
      boot.kernel.sysctl."net.ipv4.ip_forward" = 1;

      environment.systemPackages = [
        seatSubmit
        pkgs.curl
        pkgs.jq
        pkgs.iproute2
      ];

      users.users.dalhaka = {
        isNormalUser = true;
        uid = 1000;
      };

      services.seat-lane = {
        enable = true;
        host = "openrouter.test";
        keyFile = "/var/lib/secrets/openrouter-key";
        hostAddress = "10.100.4.1";
        namespaceAddress = "10.100.4.2";
        listenPort = 3141;
        operatorUser = "dalhaka";
      };

      # The wrapper's `--broker` route composes `baseURL: OPENROUTER_BASE_URL`;
      # production's default https://openrouter.ai/api/v1 happens to match
      # the default host, but this VM's host is openrouter.test, so pin the
      # base URL to the fake. Test-only: nothing in seatLane.nix is touched.
      #
      # ProtectSystem=strict makes /tmp read-only for the seat unit (there is
      # no PrivateTmp and /tmp is not one of the module's ReadWritePaths).
      # The harness writes its DSH_HOME (/tmp/dsh) and its nix fetcher cache
      # (XDG_CACHE_HOME under /tmp) on every launch, so this VM admits /tmp
      # read-write for the test fixture paths -- the module's own list is
      # unchanged (ReadWritePaths is a list; the fixture APPENDS /tmp).
      systemd.services = {
        "seat@" = {
          environment.OPENROUTER_BASE_URL = "https://openrouter.test/api/v1";
          serviceConfig.ReadWritePaths = [ "/tmp" ];
        };
        "egress-broker-seat" = {
          after = [ "seat-secret.service" ];
          requires = [ "seat-secret.service" ];
        };
        fake-upstream = {
          description = "Fake TLS OpenRouter-compatible upstream for the seat VM test";
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            ExecStart = "${pkgs.python3}/bin/python3 ${fakeUpstream}";
            Restart = "on-failure";
          };
        };
        # Stands in for the operator's root-only one-time procedure (the same
        # shape as lane-vm's lane-secret): a fixture string the test greps for
        # to prove it never leaves the broker. Not a real credential.
        seat-secret = {
          wantedBy = [ "multi-user.target" ];
          before = [ "egress-broker-seat.service" ];
          serviceConfig = {
            Type = "oneshot";
            RemainAfterExit = true;
          };
          script = ''
            umask 077
            mkdir -p /var/lib/secrets
            # The directory itself is declared by the seat module's tmpfiles
            # rule (SB4b: 0710 root:egress-broker -- the broker must traverse
            # it to reach the key, or it crash-loops on PermissionError). The
            # fixture only writes the key file: 0440 root:egress-broker,
            # exactly as the runbook's tmpfiles rule resets it on the real
            # host (the module's input); nothing here invents a directory
            # mode.
            echo "sk-or-vm-fixture" > /var/lib/secrets/openrouter-key
            chown root:egress-broker /var/lib/secrets/openrouter-key
            chmod 0440 /var/lib/secrets/openrouter-key
          '';
        };
      };
    };
  testScript = ''
    machine.wait_for_unit("fake-upstream.service")
    machine.wait_for_unit("egress-netns-seat.service")
    machine.wait_for_unit("egress-broker-seat.service")
    machine.wait_for_unit("seat-secret.service")
    machine.wait_until_succeeds(
        "test -f /var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt"
    )

    # Fixtures the operator's submission references: a workspace and a dsh
    # home under /tmp (admitted read-write above), plus the brief the fake
    # upstream answers. Created here so the submission's --workspace check
    # passes and the unit (as dalhaka) can write DSH_HOME and the cache.
    machine.succeed("mkdir -p /tmp/ws /tmp/dsh")
    machine.succeed("chown dalhaka /tmp/ws /tmp/dsh")
    machine.succeed("printf 'Reply with the single word ok.\\n' > /tmp/brief")
    machine.succeed("chown dalhaka /tmp/brief")
    # SB4b (module bug 1): the seat unit's ReadWritePaths carries the "-"
    # prefix on the four home paths, so a fresh machine WITHOUT ~/factory,
    # ~/nixos-agent-env, ~/flakes or ~/.local/share/dsh-openrouter starts the
    # unit cleanly (no 226/NAMESPACE). This test deliberately creates NONE of
    # them: the assertion below (Result == success) is what proves the "-"
    # prefix did its job.

    # 1. the operator submits a headless job; the unit runs the real harness
    #    behind the broker, answers, and its output lands on stdout.
    submit = machine.succeed(
        "su - dalhaka -c 'seat-submit headless "
        "--workspace /tmp/ws --dsh-home /tmp/dsh "
        "--model deepseek/deepseek-v4-flash --effort off --brief /tmp/brief'"
    )
    job_id = submit.strip().splitlines()[0].strip()
    assert "vm-seat-answer" in submit, submit
    # SB4b (module bug 1): the unit reached success (never 226/NAMESPACE) --
    # the ReadWritePaths "-" prefixes tolerated the absent home paths.
    machine.succeed(
        f"test \"$(systemctl show 'seat@{job_id}.service' -p Result --value)\" = success"
    )
    # SB4b (module bug 2): the broker started exactly once -- no crash-loop
    # on PermissionError reading the key through a non-traversable secrets
    # directory.
    machine.succeed(
        "test \"$(systemctl show egress-broker-seat.service -p NRestarts --value)\" = 0"
    )

    # 2. the fake upstream saw the broker-injected credential -- this process
    #    (the seat unit) only ever held the placeholder.
    api_log = machine.succeed("cat /var/log/seat-vm-fake-upstream.log")
    assert "Bearer sk-or-vm-fixture" in api_log, api_log
    assert "injected-by-broker" not in api_log, api_log

    # 3. the unit's rendered environment holds only the placeholder, never
    #    the real key -- the real key is confined to the broker's root-only
    #    secret file, unreadable to the unit (InaccessiblePaths).
    env = machine.succeed(
        f"systemctl show 'seat@{job_id}.service' -p Environment --value"
    )
    assert "OPENROUTER_API_KEY=injected-by-broker" in env, env
    assert "sk-or-vm-fixture" not in env, env
    machine.fail("systemctl cat 'seat@.service' | grep -q sk-or-vm-fixture")
    machine.fail("grep -rq sk-or-vm-fixture /var/lib/seat/jobs")

    # 4. /api/v1/messages is denied at the broker, fail closed, BEFORE the
    #    key is injected (lane-vm step 2c shape; the seat's denyPaths is the
    #    lane's list).
    deny_resp = machine.succeed(
        "ip netns exec egress-seat curl -s --max-time 15 "
        "-x http://10.100.4.1:3141 "
        "--cacert /var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt "
        "-X POST -H 'content-type: application/json' "
        "--data '{\"model\":\"m\"}' "
        "https://openrouter.test/api/v1/messages"
    )
    assert "egress-broker: denied" in deny_resp, deny_resp
    machine.succeed(
        "jq -es '[.[] | select(.path==\"/api/v1/messages\" and "
        ".verdict==\"deny\" and .reason==\"path-not-permitted\")] "
        "| length == 1' /var/lib/egress-broker/seat/audit.jsonl"
    )
    api_log2 = machine.succeed("cat /var/log/seat-vm-fake-upstream.log")
    assert "/api/v1/messages" not in api_log2, api_log2

    # 5. any other host is unreachable from the namespace: its only route is
    #    the broker's veth gateway, and the host drops anything forwarded on
    #    veb-seat (egressBroker's forward-seat chain).
    machine.fail(
        "ip netns exec egress-seat curl -s --max-time 5 -o /dev/null https://example.test/"
    )

    # 6. the web seat: dsh binds loopback (its guard), the unit-owned
    #    forwarder relays the namespace address to it, the host side reaches
    #    it (the output-seat chain), and a second namespace does not
    #    (forwarded traffic is dropped at veb-seat).
    web_id = machine.succeed(
        "su - dalhaka -c 'seat-submit web "
        "--workspace /tmp/ws --dsh-home /tmp/dsh "
        "--model deepseek/deepseek-v4-flash --effort off --port 43201'"
    ).strip()
    machine.wait_until_succeeds(
        f"test -f /var/lib/seat/jobs/{web_id}/url.txt"
    )
    url = machine.succeed(f"cat /var/lib/seat/jobs/{web_id}/url.txt").strip()
    assert url == "http://10.100.4.2:43201", url
    # The host (the operator's browser) reaches it...
    machine.wait_until_succeeds(
        "curl -s --max-time 5 -o /dev/null http://10.100.4.2:43201/"
    )
    # SB4b (item 4): dsh honours its loopback guard. Inside the unit's
    # namespace dsh listens on 127.0.0.1:<port> ONLY, and the forwarder
    # listens on the namespace address 10.100.4.2:<port> ONLY. Neither binds
    # 0.0.0.0 (the mutation that would expose dsh's remote-code-execution
    # surface to the network) -- so the two listeners are disjoint by
    # address, which is what proves the guard is honoured.
    listen = machine.succeed("ip netns exec egress-seat ss -ltn")
    assert "127.0.0.1:43201" in listen, listen
    assert "10.100.4.2:43201" in listen, listen
    assert "0.0.0.0:43201" not in listen, listen
    assert "[::]:43201" not in listen, listen
    # ...but a second namespace cannot: create one whose only route to
    # 10.100.4.2 is via the host, and prove the host-side forward path drops
    # the forwarded packet (the spoofed/second-source isolation the task
    # requires).
    machine.succeed("ip netns add seat-vm-probe")
    machine.succeed("ip link add vp type veth peer name vp-p")
    machine.succeed("ip link set vp-p netns seat-vm-probe")
    machine.succeed("ip addr add 10.100.5.1/30 dev vp")
    machine.succeed("ip link set vp up")
    machine.succeed("ip netns exec seat-vm-probe ip addr add 10.100.5.2/30 dev vp-p")
    machine.succeed("ip netns exec seat-vm-probe ip link set vp-p up")
    machine.succeed("ip netns exec seat-vm-probe ip link set lo up")
    machine.succeed("ip netns exec seat-vm-probe ip route add 10.100.4.0/30 via 10.100.5.1")
    machine.fail(
        "ip netns exec seat-vm-probe curl -s --max-time 5 -o /dev/null http://10.100.4.2:43201/"
    )

    # 7. the audit log carries both requests: the injected chat call (allow)
    #    and the denied messages probe (already pinned in step 4).
    machine.succeed(
        "jq -es '[.[] | select(.host==\"openrouter.test\" and "
        ".verdict==\"allow\")] | length >= 1' /var/lib/egress-broker/seat/audit.jsonl"
    )
  '';
}
