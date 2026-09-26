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
        openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
          -keyout $out/ca.key -out $out/ca.crt -subj "/CN=seat-vm-test-ca"
        openssl req -newkey rsa:2048 -nodes \
          -keyout $out/openrouter.test.key -out $out/openrouter.test.csr \
          -subj "/CN=openrouter.test" -addext "subjectAltName=DNS:openrouter.test"
        openssl x509 -req -in $out/openrouter.test.csr -CA $out/ca.crt -CAkey $out/ca.key \
          -CAcreateserial -days 3650 -copy_extensions copy -out $out/openrouter.test.crt
        openssl x509 -in $out/ca.crt -noout -checkend 31536000
        openssl x509 -in $out/openrouter.test.crt -noout -checkend 31536000
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

    # SA7 step 15: the one brief that asks the seat to remember something is
    # answered with a canned bash tool call that writes the note through
    # $DSH_HOME/memory -- the seat's memory link -- so the test can prove the
    # write lands under the evidence store, never the workspace. The probe
    # fires only on the first turn (no tool result yet); the second turn
    # answers the ordinary text so the run reaches quiescence.
    MEMORY_BRIEF = "note.txt"

    def _memory_probe(body):
        messages = body.get("messages") or []
        # The harness also sends a title-generation request whose system
        # prompt asks for a concise session title and whose user message
        # embeds the brief as a JSON array; skip it -- it expects a plain-text
        # title, never a tool call. Only the chat turn (the raw brief) fires.
        if any(
            m.get("role") == "system" and "concise title" in str(m.get("content", ""))
            for m in messages
        ):
            return False
        if any(m.get("role") == "tool" for m in messages):
            return False
        for m in messages:
            if m.get("role") != "user":
                continue
            content = m.get("content")
            if isinstance(content, str) and MEMORY_BRIEF in content:
                return True
            if isinstance(content, list) and any(
                (c.get("text") or "").find(MEMORY_BRIEF) >= 0
                for c in content
                if isinstance(c, dict)
            ):
                return True
        return False

    def _memory_tool_call(body):
        name = "bash"
        for tool in body.get("tools") or []:
            candidate = (tool.get("function") or {}).get("name", "")
            if "bash" in candidate:
                name = candidate
                break
        return {
            "index": 0,
            "id": "call_memory_note",
            "type": "function",
            "function": {
                "name": name,
                "arguments": json.dumps(
                    {
                        "command": 'echo note > "$DSH_HOME/memory/note.txt"',
                        "description": "write a memory note",
                    }
                ),
            },
        }

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
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except ValueError:
                body = {}
            usage = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            if _memory_probe(body):
                call = _memory_tool_call(body)
                self.wfile.write(
                    _sse(_chunk(0, {"role": "assistant", "tool_calls": [call]}))
                )
                self.wfile.write(_sse(_chunk(0, {}, "tool_calls", usage)))
            else:
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
      # SD5: the probe's `nix store ping` needs the nix-command/flakes
      # experimental features the real host's /etc/nix/nix.conf already carries
      # (the VM's nix.conf is generated from nix.* and defaults to disabled).
      nix.settings.experimental-features = [
        "nix-command"
        "flakes"
      ];

      environment.systemPackages = [
        seatSubmit
        pkgs.curl
        pkgs.jq
        pkgs.iproute2
        # SD5: step 9's probe resolves git and nix by name out of the unit's
        # /run/current-system/sw -- the real host's profile carries both, so
        # the VM's profile must too (bash is in the base profile already).
        pkgs.git
        pkgs.nix
      ];

      users.users.alice = {
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
        operatorUser = "alice";
        # IS20 (answer 11): the seat's namespace additionally reaches Helm's v2
        # API port (7710) on the host-side address -- the network half this VM
        # proves (step 13). Helm's control page (7700) must stay dropped.
        helmApiPort = 7710;
        # IS1c: the cap-refusal step (11b) needs the cap reachable with a small
        # number of long-running seats. 2 keeps the probe's own spooled
        # follow-on (step 9, which sees one active `seat@probe` while the
        # marker is written) below the cap, and 2 held web seats reach it in
        # step 11b.
        # IS10: waveJobs must stay below maxUnits (the `maxUnits > waveJobs`
        # relation, IS3). 1 keeps the cap reachable with two held seats here
        # (IS1c's step 11b); the wave cap is irrelevant in this VM, which
        # never runs factory-wave.
        waveJobs = 1;
        maxUnits = 2;
        # SA4: the port range the spool allocates from, held at two ports so
        # step 14's two --port-less web seats exhaust it (maxUnits = 2 admits
        # exactly two seats, and the range must hold at least that many). The
        # value deliberately does NOT overlap the default range's first two
        # ports (43210/43211): the two ports step 14 reads back therefore
        # reveal which range is in effect -- 43298/43299 proves the spool read
        # /etc/seat-lane/port-range, while a fallback to the default would
        # allocate 43210/43211 instead.
        portRange = "43298-43299";
      };

      # The wrapper's `--broker` route composes `baseURL: OPENROUTER_BASE_URL`;
      # production's default https://openrouter.ai/api/v1 happens to match
      # the default host, but this VM's host is openrouter.test, so pin the
      # base URL to the fake. Test-only: nothing in seatLane.nix is touched.
      #
      # The unit here is otherwise the SHIPPED one -- no ReadWritePaths
      # override, no /tmp admission. The harness's spill store writes to an
      # absolute /tmp/dsh-spill-XXXXXX prefix (a literal inside
      # @deepseek-ai/dsh-spill-local), so the unit needs its own instance /tmp
      # from the module's PrivateTmp rather than the VM patching the hardening
      # it is meant to prove.
      systemd.services = {
        "seat@" = {
          environment.OPENROUTER_BASE_URL = "https://openrouter.test/api/v1";
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
        # IS20 (answer 11): fixture HTTP servers standing in for Helm's two
        # ports on the host-side address — the v2 API (7710, which the seat's
        # namespace must reach) and the control page (7700, which input-seat
        # must keep dropping from the namespace).
        helm-api-7710 = {
          description = "Fixture HTTP server on Helm's v2 API port (7710)";
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            ExecStart = "${pkgs.python3}/bin/python3 -m http.server 7710 --bind 10.100.4.1";
          };
        };
        helm-page-7700 = {
          description = "Fixture HTTP server on Helm's control page port (7700)";
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            ExecStart = "${pkgs.python3}/bin/python3 -m http.server 7700 --bind 10.100.4.1";
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
    import time

    machine.wait_for_unit("fake-upstream.service")
    machine.wait_for_unit("egress-netns-seat.service")
    machine.wait_for_unit("egress-broker-seat.service")
    machine.wait_for_unit("seat-secret.service")
    machine.wait_until_succeeds(
        "test -f /var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt"
    )

    # Fixtures the operator's submission references: a workspace and a dsh
    # home under /home/alice/factory (the module's own ReadWritePaths, where
    # production actually writes them), plus the brief the fake upstream
    # answers. Created here so the submission's --workspace check passes and
    # the unit (as alice) can write DSH_HOME and the cache.
    machine.succeed("mkdir -p /home/alice/factory/ws /home/alice/factory/dsh")
    machine.succeed("chown -R alice /home/alice/factory")
    machine.succeed(
        "printf 'Reply with the single word ok.\\n' > /home/alice/factory/brief"
    )
    machine.succeed("chown alice /home/alice/factory/brief")
    # SB4b (module bug 1): the seat unit's ReadWritePaths carries the "-"
    # prefix on the four home paths, so a fresh machine WITHOUT ~/factory,
    # ~/nixos-agent-env, ~/flakes or ~/.local/share/dsh-openrouter starts the
    # unit cleanly (no 226/NAMESPACE). This test creates ~/factory (the
    # fixture directory above) but still NONE of ~/nixos-agent-env, ~/flakes or
    # ~/.local/share/dsh-openrouter, so the "-" prefix is still proven for
    # those three; the assertion below (Result == success) is what shows it.

    # 1. the operator submits a headless job; the unit runs the real harness
    #    behind the broker, answers, and its output lands on stdout.
    submit = machine.succeed(
        "su - alice -c 'seat-submit headless "
        "--workspace /home/alice/factory/ws --dsh-home /home/alice/factory/dsh "
        "--model deepseek/deepseek-v4-flash --effort off --brief /home/alice/factory/brief'"
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
        "su - alice -c 'seat-submit web "
        "--workspace /home/alice/factory/ws --dsh-home /home/alice/factory/dsh "
        "--model deepseek/deepseek-v4-flash --effort off --port 43201'"
    ).strip().splitlines()[0]
    machine.wait_until_succeeds(
        f"test -f /var/lib/seat/jobs/{web_id}/url.txt"
    )
    url = machine.succeed(f"cat /var/lib/seat/jobs/{web_id}/url.txt").strip()
    assert "?token=" in url, url
    assert url.startswith("http://10.100.4.2:43201/?token="), url
    # The served page, not the string: the token URL answers a 303 that issues a
    # dsh-auth- session cookie (a fresh token, not the loopback line or the old
    # constructed host).
    headers = machine.succeed(
        f"curl -s --max-time 5 -o /dev/null -D - \"$(cat /var/lib/seat/jobs/{web_id}/url.txt)\""
    )
    assert "303" in headers, headers
    assert "set-cookie: dsh-auth-" in headers, headers
    # ...and follows to a 200 ONLY with the cookie jar (a bare -L lands on 401).
    machine.succeed(
        f"curl -sL --max-time 5 -c /tmp/seat-vm-web.jar -b /tmp/seat-vm-web.jar "
        f"-o /dev/null -w '%{{http_code}}' \"$(cat /var/lib/seat/jobs/{web_id}/url.txt)\" | grep -q '^200$'"
    )
    # The host (the operator's browser) reaches it...
    machine.wait_until_succeeds(
        "curl -s --max-time 5 -o /dev/null http://10.100.4.2:43201/"
    )
    # ...but without the token the served page is a 401 whose body says so -- the
    # fact the old body-discarding `curl -s` (no --fail) could never catch.
    machine.wait_until_succeeds(
        "curl -s --max-time 5 http://10.100.4.2:43201/ | grep -q 'authentication required'"
    )
    # FIX4: the API route behind the relay answers 401 (authentication), not
    # 403 forbidden -- the host fence now trusts the namespace authority the
    # browser sends, so the request reaches auth instead of being refused.
    machine.wait_until_succeeds(
        "test \"$(curl -s --max-time 5 -o /dev/null -w '%{http_code}' http://10.100.4.2:43201/api/directoryPicker/list)\" = 401"
    )
    machine.wait_until_succeeds(
        "curl -s --max-time 5 http://10.100.4.2:43201/api/directoryPicker/list | grep -q 'unauthorized'"
    )
    machine.wait_until_succeeds(
        "! curl -s --max-time 5 http://10.100.4.2:43201/api/directoryPicker/list | grep -q 'forbidden'"
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

    # IS26: the seat's shutdown inhibitor is actually held, outside the
    # sandbox (the companion seat-inhibit@{web_id} template runs unsandboxed
    # because seat@ itself can never reach logind through the hidden system
    # bus -- the probes at step 9 prove the hiding). While the web seat runs:
    # logind carries a block inhibitor whose Who names the seat, and the
    # companion unit that holds it is active.
    machine.wait_until_succeeds(
        f"systemd-inhibit --list | grep -q 'seat@{web_id}'", timeout=30
    )
    machine.succeed(
        f"test \"$(systemctl show 'seat-inhibit@{web_id}.service' -p ActiveState --value)\" = active"
    )
    # SB6b: the forwarder belongs to the unit -- stopping the unit ends it and
    # frees the namespace port (KillMode=control-group, pinned by seat-eval).
    machine.succeed("pgrep -x socat")
    machine.succeed(f"systemctl stop seat@{web_id}")
    machine.wait_until_fails("pgrep -x socat", timeout=30)
    # IS26 (M5): BindsTo is what releases the lock -- the companion is
    # stopped with its seat, the wrapped sleep dies, and logind drops the
    # inhibitor without any cleanup code. The "absent" half of the pair.
    machine.wait_until_fails(
        f"systemd-inhibit --list | grep -q 'seat@{web_id}'", timeout=30
    )
    machine.fail("ip netns exec egress-seat ss -ltn | grep -q ':43201 '")

    # 7. the audit log carries both requests: the injected chat call (allow)
    #    and the denied messages probe (already pinned in step 4).
    machine.succeed(
        "jq -es '[.[] | select(.host==\"openrouter.test\" and "
        ".verdict==\"allow\")] | length >= 1' /var/lib/egress-broker/seat/audit.jsonl"
    )

    # 8. SB6b: a unit that fails at start is reported by seat-submit at once
    #    (exit 4 -- exit 3 is reserved for the running-unit cap, IS1), not
    #    after its poll timeout. The drop-in adds a required
    #    ReadWritePaths entry that does not exist -> status=226/NAMESPACE,
    #    Result=exit-code (the sb8 gate's MF2 measurement).
    machine.succeed("mkdir -p /run/systemd/system/seat@.service.d")
    machine.succeed(
        "printf '[Service]\\nReadWritePaths=/nonexistent-seat-negative\\n' "
        "> /run/systemd/system/seat@.service.d/sb6b-negative.conf"
    )
    machine.succeed("systemctl daemon-reload")
    t0 = time.monotonic()
    rc, out = machine.execute(
        "su - alice -c 'seat-submit headless --workspace /home/alice/factory/ws --dsh-home /home/alice/factory/dsh "
        "--model deepseek/deepseek-v4-flash --effort off --brief /home/alice/factory/brief --timeout 120' 2>&1"
    )
    elapsed = time.monotonic() - t0
    assert rc == 4, (rc, out)
    assert "Result=exit-code" in out, out
    assert elapsed < 60, elapsed
    machine.succeed("rm /run/systemd/system/seat@.service.d/sb6b-negative.conf")
    machine.succeed("systemctl daemon-reload")

    # PL16: two fixture steps precede the step 9 probe. (a) A dummy-token
    # hosts.yml under the operator's real $HOME -- never a real credential --
    # so the probe's gh_home_read line proves raw reads of ~/.config/gh stay
    # possible (the accepted, pre-existing gap: home is deliberately NOT
    # hidden, Base/seatLane.nix's own /home comment).
    machine.succeed("mkdir -p /home/alice/.config/gh")
    machine.succeed(
        "printf 'github.com:\\n  oauth_token: dummy-gh-fixture-token\\n' "
        "> /home/alice/.config/gh/hosts.yml"
    )
    machine.succeed("chown -R alice /home/alice/.config")
    # PL16: (b) a REAL user@1000.service session bus, the same mechanism the
    # operator's own host runs (F11): linger keeps the user manager alive
    # without a login, and it owns /run/user/1000/bus. The hide the probe
    # proves below is namespace-scoped, so the bus must first be shown live
    # -- a probe that reads "hidden" against a bus that never existed would
    # prove nothing. Linger keeps the user manager alive without a login;
    # user@1000.service owns /run/user/1000/bus.
    machine.succeed("loginctl enable-linger alice")
    machine.succeed("systemctl start user@1000.service")
    machine.wait_for_file("/run/user/1000/bus")
    # The liveness control runs AS THE BUS OWNER (su -
    # alice), never as root: dbus-broker refuses user-bus connections
    # from other uids, root included -- measured, every root-side connect
    # from the driver reset with EPIPE while the broker stayed up -- and the
    # probe below runs as alice too, so the owner is the honest positive
    # control. `list`, never `status`: status exits 1 against a live bus
    # even on the operator's own host ("Failed to get credentials: Object is
    # remote", measured), while list completes a real handshake (connect +
    # Hello + ListNames, exit 0 as the owner, measured). wait_until_succeeds
    # covers dbus.socket's activation window: the first connection races
    # the broker takeover (measured: "Transport endpoint is not connected").
    machine.wait_until_succeeds(
        "su - alice -c 'busctl --address=unix:path=/run/user/1000/bus list >/dev/null'"
    )

    # 9. SD5: a probe from INSIDE the real template's sandbox. A per-instance
    #    drop-in keeps the template's User, namespace, ProtectSystem,
    #    ReadWritePaths, InaccessiblePaths, path and environment (only the
    #    ExecStart differs; the probe instance runs probe.sh, never seat-run),
    #    so each probe line below proves a claim the module makes, not a
    #    systemd-run replica.
    machine.succeed("mkdir -p /run/systemd/system/seat@probe.service.d")
    machine.succeed(
        "printf '[Service]\\nExecStart=\\nExecStart=/var/lib/seat/probe.sh\\n' "
        "> /run/systemd/system/seat@probe.service.d/override.conf"
    )
    machine.succeed(
        "cat > /var/lib/seat/probe.sh <<'SEAT_PROBE_EOF'\n"
        "#!/bin/sh\n"
        "out=/var/lib/seat/probe.out\n"
        ": > \"$out\"\n"
        "bash -c true; echo \"bash=$?\" >> \"$out\"\n"
        "git --version >/dev/null 2>&1; echo \"git=$?\" >> \"$out\"\n"
        "nix store ping --store daemon >/dev/null 2>&1; echo \"nix=$?\" >> \"$out\"\n"
        "seat-submit --help >/dev/null 2>&1; echo \"seat_submit=$?\" >> \"$out\"\n"
        "if test -d \"$DSH_CACHE_ROOT\" && touch \"$DSH_CACHE_ROOT/w\"; then\n"
        "  echo \"cache=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"cache=1\" >> \"$out\"\n"
        "fi\n"
        "if systemctl start seat@nope >/dev/null 2>&1; then\n"
        "  echo \"systemctl=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"systemctl=1\" >> \"$out\"\n"
        "fi\n"
        "# systemd hides the socket by mounting /systemd/inaccessible/sock over\n"
        "# it -- still a *socket* node (so `test -S` cannot tell), but mode 0000\n"
        "# (so `test -r` is false). 1 = hidden.\n"
        "if test -r /run/dbus/system_bus_socket; then\n"
        "  echo \"dbus=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"dbus=1\" >> \"$out\"\n"
        "fi\n"
        "# SD6: the spool is the one host-side actor the seat may reach -- a\n"
        "# --no-start submit writes the marker to /var/lib/seat/spool and returns\n"
        "# the id; seat-spool.path starts it, never a systemctl call from here.\n"
        "spooled_id=$(seat-submit headless --no-start \\\n"
        "  --workspace /home/alice/factory/ws --dsh-home /home/alice/factory/dsh \\\n"
        "  --model deepseek/deepseek-v4-flash --effort off --brief /home/alice/factory/brief)\n"
        "echo \"spooled=$spooled_id\" >> \"$out\"\n"
        "# OG3r: ReadOnlyPaths mounts the house guard read-only into every job, so\n"
        "# no process in the unit can write it (guard_write=1), unlink or rename it\n"
        "# (guard_rename=1) — however a command spells its path — while reading it\n"
        "# stays allowed (guard_read=0). `touch` (not `: >`, whose special-builtin\n"
        "# redirection failure would abort the sh script) returns non-zero on the\n"
        "# read-only mount.\n"
        "if touch /home/alice/nixos-agent-env/tools/orchestrator-guard.sh 2>/dev/null; then\n"
        "  echo \"guard_write=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"guard_write=1\" >> \"$out\"\n"
        "fi\n"
        "if mv /home/alice/nixos-agent-env/tools/orchestrator-guard.sh /home/alice/nixos-agent-env/tools/guard.renamed 2>/dev/null; then\n"
        "  echo \"guard_rename=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"guard_rename=1\" >> \"$out\"\n"
        "fi\n"
        "if cat /home/alice/nixos-agent-env/tools/orchestrator-guard.sh >/dev/null 2>&1; then\n"
        "  echo \"guard_read=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"guard_read=1\" >> \"$out\"\n"
        "fi\n"
        "# PL16: the unit's GH_CONFIG_DIR pins gh's config lookup at a fresh,\n"
        "# root-owned tmpfiles dir -- gh resolves no hosts.yml through it. The\n"
        "# dir must exist, be empty, and be unwritable by the seat (root-owned\n"
        "# 0555: a touch inside it fails).\n"
        "echo \"gh_config_dir=$GH_CONFIG_DIR\" >> \"$out\"\n"
        "if test -d \"$GH_CONFIG_DIR\" && test -z \"$(ls -A \"$GH_CONFIG_DIR\")\"; then\n"
        "  echo \"gh_config_empty=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"gh_config_empty=1\" >> \"$out\"\n"
        "fi\n"
        "if touch \"$GH_CONFIG_DIR/probe\" 2>/dev/null; then\n"
        "  echo \"gh_config_write=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"gh_config_write=1\" >> \"$out\"\n"
        "fi\n"
        "# PL16 (accepted gap, restated): a raw read of the operator's own\n"
        "# ~/.config/gh/hosts.yml still succeeds -- home is deliberately NOT\n"
        "# hidden (Base) so a seat can edit the operator's clones; the guard is\n"
        "# gh's config RESOLUTION, not file visibility.\n"
        "if cat \"$HOME/.config/gh/hosts.yml\" >/dev/null 2>&1; then\n"
        "  echo \"gh_home_read=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"gh_home_read=1\" >> \"$out\"\n"
        "fi\n"
        "# PL16: the operator's REAL session bus (the Secret Service transport,\n"
        "# F11/F12) is hidden by the template's fourth InaccessiblePaths entry.\n"
        "# An explicit --address, never env-var bus discovery, so the probe\n"
        "# proves the mount, not a PATH/env accident; `list` completes a real\n"
        "# handshake (connect + Hello + ListNames). 1 = hidden.\n"
        "if busctl --address=\"unix:path=/run/user/1000/bus\" list >/dev/null 2>&1; then\n"
        "  echo \"sessionbus=0\" >> \"$out\"\n"
        "else\n"
        "  echo \"sessionbus=1\" >> \"$out\"\n"
        "fi\n"
        "SEAT_PROBE_EOF\n"
    )
    machine.succeed("chmod 755 /var/lib/seat/probe.sh")
    # OG3r: the probe instance's ReadOnlyPaths mounts this exact file read-only;
    # the fixture creates it (one line, alice-owned 0644) so the probe can
    # prove the mount blocks write/rename while still allowing read.
    machine.succeed(
        "mkdir -p /home/alice/nixos-agent-env/tools "
        "&& printf '#!/usr/bin/env bash\\n' > /home/alice/nixos-agent-env/tools/orchestrator-guard.sh "
        "&& chown -R alice /home/alice/nixos-agent-env"
    )
    machine.succeed("systemctl daemon-reload")
    machine.succeed("systemctl start seat@probe.service")
    # The probe runs asynchronously (Type=simple); wait for all sixteen lines so
    # the assertions below read a complete file, never a partially-written one.
    machine.wait_until_succeeds(
        "test \"$(wc -l < /var/lib/seat/probe.out)\" = 16"
    )
    machine.succeed("grep -qx 'bash=0' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'git=0' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'nix=0' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'seat_submit=0' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'cache=0' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'systemctl=1' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'dbus=1' /var/lib/seat/probe.out")
    # OG3r: the mount holds the guard read-only — a write to it fails (1), a
    # rename over a sibling fails (1), and reading it still succeeds (0).
    machine.succeed("grep -qx 'guard_write=1' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'guard_rename=1' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'guard_read=0' /var/lib/seat/probe.out")
    # PL16: the unit arm's gh guard -- GH_CONFIG_DIR pins the literal the
    # module sets (Interfaces 3), the tmpfiles dir exists and is empty, a
    # write inside it fails (root-owned 0555), a raw hosts.yml read still
    # succeeds (the accepted gap), and the operator's live session bus --
    # proven up before the probe, from outside the namespace -- is unreachable
    # from inside the unit (1 = hidden).
    machine.succeed(
        "grep -qx 'gh_config_dir=/var/lib/seat/gh-config-empty' /var/lib/seat/probe.out"
    )
    machine.succeed("grep -qx 'gh_config_empty=0' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'gh_config_write=1' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'gh_home_read=0' /var/lib/seat/probe.out")
    machine.succeed("grep -qx 'sessionbus=1' /var/lib/seat/probe.out")

    # SD6: the --no-start submit inside the seat unit spooled a job; the
    # seat-spool.path unit started it (no systemctl from inside the sandbox),
    # the fake upstream answered, and the marker was consumed.
    spooled_id = machine.succeed(
        "sed -n 's/^spooled=//p' /var/lib/seat/probe.out"
    ).strip()
    machine.wait_until_succeeds(
        f"test -f /var/lib/seat/jobs/{spooled_id}/result.txt"
    )
    machine.succeed(
        f"grep -q vm-seat-answer /var/lib/seat/jobs/{spooled_id}/stdout.txt"
    )
    machine.succeed(f"test -f /var/lib/seat/jobs/{spooled_id}/.spooled")
    machine.succeed(f"test ! -e /var/lib/seat/spool/{spooled_id}")
    machine.succeed(
        f"journalctl -u seat-spool.service | grep -q 'started seat@{spooled_id}'"
    )

    # 10. SD6: a bad job is refused, never started: alice writes a marker for
    #    a job.json whose mode is invalid; seat-spool refuses it (bad-mode),
    #    unlinks the marker, writes no .spooled, and starts nothing.
    bad_id = "20260906-000000-abcdef"
    machine.succeed(
        f"su - alice -c 'mkdir -m 700 /var/lib/seat/jobs/{bad_id}'"
    )
    machine.succeed(
        f"su - alice -c 'printf \"{{\\\"mode\\\":\\\"evil\\\"}}\\n\" "
        f"> /var/lib/seat/jobs/{bad_id}/job.json'"
    )
    machine.succeed(f"touch /var/lib/seat/spool/{bad_id}")
    machine.wait_until_succeeds(
        f"journalctl -u seat-spool.service | grep -q 'refused {bad_id}: bad-mode'"
    )
    machine.succeed(
        f"test \"$(systemctl show 'seat@{bad_id}.service' -p ActiveState --value)\" = inactive"
    )
    machine.fail(f"test -e /var/lib/seat/jobs/{bad_id}/.spooled")
    machine.fail(f"test -e /var/lib/seat/spool/{bad_id}")

    # 11. SD6: a second marker for the already-spooled (finished) job is
    #    refused as already-started -- exactly one seat@ instance per marker.
    machine.succeed(f"touch /var/lib/seat/spool/{spooled_id}")
    machine.wait_until_succeeds(
        f"journalctl -u seat-spool.service | grep -q 'refused {spooled_id}: already-started'"
    )
    machine.fail(f"test -e /var/lib/seat/spool/{spooled_id}")

    # 11b. IS1c: the spool enforces the running-unit cap (decision 72a). With
    #     the cap at 2 (set above) and two long-running web seats holding both
    #     slots, a spooled headless submit is refused BY THE SPOOL (seat-submit
    #     --no-start never counts, so it still returns an id): a result.txt
    #     carrying FACTORY-RESULT status=failed appears promptly (no 900 s
    #     hang), the marker is consumed, and the refused job is never started.
    cap_web_ids = []
    for _port in ("43204", "43205"):
        _id = machine.succeed(
            "su - alice -c 'seat-submit web "
            "--workspace /home/alice/factory/ws --dsh-home /home/alice/factory/dsh "
            "--model deepseek/deepseek-v4-flash --effort off --port "
            f"{_port}'"
        ).strip().splitlines()[0]
        machine.wait_until_succeeds(
            f"test -f /var/lib/seat/jobs/{_id}/url.txt"
        )
        cap_web_ids.append(_id)
    cap_id = machine.succeed(
        "su - alice -c 'seat-submit headless --no-start "
        "--workspace /home/alice/factory/ws --dsh-home /home/alice/factory/dsh "
        "--model deepseek/deepseek-v4-flash --effort off "
        "--brief /home/alice/factory/brief'"
    ).strip()
    machine.wait_until_succeeds(
        f"grep -q 'FACTORY-RESULT status=failed' /var/lib/seat/jobs/{cap_id}/result.txt"
    )
    machine.succeed(
        f"grep -q '2 seat units running, cap 2' /var/lib/seat/jobs/{cap_id}/result.txt"
    )
    machine.fail(f"test -e /var/lib/seat/spool/{cap_id}")
    machine.succeed(
        f"journalctl -u seat-spool.service | grep -q 'refused {cap_id}:'"
    )
    machine.fail(f"test -e /var/lib/seat/jobs/{cap_id}/.spooled")
    machine.succeed(
        f"test \"$(systemctl show 'seat@{cap_id}.service' -p ActiveState --value)\" = inactive"
    )
    # Release the two held slots before the drive step.
    for _id in cap_web_ids:
        machine.succeed(f"systemctl stop seat@{_id}")

    # 12. SD7: the drive job mode. A fixture home carries the driver's skill
    #     set (three one-line files); seat-submit drive requires it and a
    #     port, seat-run adds --model before the `--` so the wrapper writes
    #     the explicit model into the home's settings.yaml (never the saved
    #     selection), and the web seat answers on the port exactly as step 6.
    machine.succeed("mkdir -p /home/alice/factory/drive-home/skills/driving /home/alice/factory/drive-home/skills/planning")
    machine.succeed("printf 'driving\\n' > /home/alice/factory/drive-home/skills/driving/SKILL.md")
    machine.succeed("printf 'planning\\n' > /home/alice/factory/drive-home/skills/planning/SKILL.md")
    machine.succeed("printf 'agents\\n' > /home/alice/factory/drive-home/AGENTS.md")
    # SD7b: a pre-held selection the drive job must overwrite -- seat-run passes
    # --model, so the wrapper writes the explicit model over this saved choice
    # (nothing automated inherits the operator's saved picker selection).
    machine.succeed(
        "printf 'agent-default-model:\\n  model: some/other\\n' "
        "> /home/alice/factory/drive-home/settings.yaml"
    )
    machine.succeed("chown -R alice /home/alice/factory/drive-home")
    drive_id = machine.succeed(
        "su - alice -c 'seat-submit drive "
        "--workspace /home/alice/factory/ws --dsh-home /home/alice/factory/drive-home "
        "--model deepseek/deepseek-v4-flash --effort off --port 43202'"
    ).strip().splitlines()[0]
    machine.wait_until_succeeds(
        f"test -f /var/lib/seat/jobs/{drive_id}/url.txt"
    )
    url = machine.succeed(f"cat /var/lib/seat/jobs/{drive_id}/url.txt").strip()
    assert "?token=" in url, url
    assert url.startswith("http://10.100.4.2:43202/?token="), url
    # Same served-page proof as the web step: 303 + dsh-auth- cookie, then 200
    # only through the cookie jar.
    headers = machine.succeed(
        f"curl -s --max-time 5 -o /dev/null -D - \"$(cat /var/lib/seat/jobs/{drive_id}/url.txt)\""
    )
    assert "303" in headers, headers
    assert "set-cookie: dsh-auth-" in headers, headers
    machine.succeed(
        f"curl -sL --max-time 5 -c /tmp/seat-vm-drive.jar -b /tmp/seat-vm-drive.jar "
        f"-o /dev/null -w '%{{http_code}}' \"$(cat /var/lib/seat/jobs/{drive_id}/url.txt)\" | grep -q '^200$'"
    )
    machine.wait_until_succeeds(
        "curl -s --max-time 5 -o /dev/null http://10.100.4.2:43202/"
    )
    machine.wait_until_succeeds(
        "curl -s --max-time 5 http://10.100.4.2:43202/ | grep -q 'authentication required'"
    )
    # FIX4: the drive seat's API route answers 401 (authentication) through the
    # relay, not 403 forbidden.
    machine.wait_until_succeeds(
        "test \"$(curl -s --max-time 5 -o /dev/null -w '%{http_code}' http://10.100.4.2:43202/api/directoryPicker/list)\" = 401"
    )
    machine.wait_until_succeeds(
        "curl -s --max-time 5 http://10.100.4.2:43202/api/directoryPicker/list | grep -q 'unauthorized'"
    )
    machine.wait_until_succeeds(
        "! curl -s --max-time 5 http://10.100.4.2:43202/api/directoryPicker/list | grep -q 'forbidden'"
    )
    # The loopback guard holds for the drive seat too: disjoint by address,
    # never 0.0.0.0 (or the IPv6 wildcard), exactly as step 6 pinned web.
    listen = machine.succeed("ip netns exec egress-seat ss -ltn")
    assert "127.0.0.1:43202" in listen, listen
    assert "10.100.4.2:43202" in listen, listen
    assert "0.0.0.0:43202" not in listen, listen
    assert "[::]:43202" not in listen, listen
    # rule 2 reached the wrapper: seat-run passed --model, the wrapper wrote
    # the explicit model into the (fresh) home's settings.yaml.
    machine.succeed(
        "grep -q 'model: deepseek/deepseek-v4-flash' /home/alice/factory/drive-home/settings.yaml"
    )
    machine.fail("grep -q 'some/other' /home/alice/factory/drive-home/settings.yaml")

    # A drive submit with a home lacking the skill set is refused (exit 2)
    # before any job directory is created.
    jobs_before = machine.succeed("ls -1 /var/lib/seat/jobs | wc -l").strip()
    rc, out = machine.execute(
        "su - alice -c 'seat-submit drive --workspace /home/alice/factory/ws --dsh-home /home/alice/factory/dsh "
        "--model deepseek/deepseek-v4-flash --effort off --port 43203' 2>&1"
    )
    assert rc == 2, (rc, out)
    assert "lacks skills/driving/SKILL.md" in out, out
    jobs_after = machine.succeed("ls -1 /var/lib/seat/jobs | wc -l").strip()
    assert jobs_before == jobs_after, (jobs_before, jobs_after)

    # 13. IS20 (answer 11): the seat's namespace reaches Helm's v2 API port
    #     (7710) on the host-side address — the network half of answer 11 —
    #     and nothing else new: Helm's control page (7700) stays unreachable.
    machine.wait_for_unit("helm-api-7710.service")
    machine.wait_for_unit("helm-page-7700.service")
    _api_rc, api_code = machine.execute(
        "ip netns exec egress-seat curl -s -o /dev/null -w '%{http_code}' http://10.100.4.1:7710/"
    )
    assert api_code == "200", f"expected 200 from 10.100.4.1:7710, got {api_code}"
    rc2, out2 = machine.execute(
        "ip netns exec egress-seat curl -m 3 -s -o /dev/null -w '%{http_code}' http://10.100.4.1:7700/"
    )
    assert out2 != "200", f"expected 7700 refused from the seat, got {out2}"
    assert rc2 in (7, 28), f"expected 7700 refused from the seat, got exit {rc2}"

    # 14. SA4: the port range is a lane option (portRange) the spool reads from
    #     /etc/seat-lane/port-range, proven by two --port-less web seats binding
    #     two distinct ports inside the declared range (seat-submit prints
    #     `port=<n>` on its second stdout line, SA3 decision 13b). The fixture
    #     sets portRange to "43298-43299", so the two allocated ports reveal
    #     which range is in effect: 43298/43299 proves the spool read the file,
    #     while a fallback to the default (43210-43219) would allocate
    #     43210/43211 and fail this step. (The running-unit cap, maxUnits = 2,
    #     is checked by the spool before the port allocator, so a third
    #     --port-less seat is refused as "2 seat units running, cap 2" -- step
    #     11b's proof -- never "no free port": the width assertion above makes a
    #     narrower-than-maxUnits range unrepresentable, so the cap is always the
    #     binding constraint. The distinct-port read-back is what proves the
    #     range here.)
    # The drive seat from step 12 is still running and would hold one of the
    # two cap slots (maxUnits = 2), so stop it first -- step 14 needs both
    # slots for its two web seats, and nothing in step 13 or 15 uses it.
    machine.succeed(f"systemctl stop seat@{drive_id}")
    range_web_ids = []
    range_ports = []
    for _ in range(2):
        _out = machine.succeed(
            "su - alice -c 'seat-submit web "
            "--workspace /home/alice/factory/ws --dsh-home /home/alice/factory/dsh "
            "--model deepseek/deepseek-v4-flash --effort off'"
        )
        _id = _out.splitlines()[0].strip()
        _port = int(_out.splitlines()[1].split("=", 1)[1].strip())
        range_web_ids.append(_id)
        range_ports.append(_port)
        machine.wait_until_succeeds(
            f"test -f /var/lib/seat/jobs/{_id}/url.txt"
        )
    # Two distinct ports, both inside the declared two-port range.
    assert set(range_ports) == { 43298, 43299 }, range_ports
    listen = machine.succeed("ip netns exec egress-seat ss -ltn")
    assert "127.0.0.1:43298" in listen, listen
    assert "127.0.0.1:43299" in listen, listen
    assert "10.100.4.2:43298" in listen, listen
    assert "10.100.4.2:43299" in listen, listen
    # Release the two held ports before the memory step (it submits a headless
    # job that would otherwise hit the cap of 2).
    for _id in range_web_ids:
        machine.succeed(f"systemctl stop seat@{_id}")

    # 15. SA7 (decision 59a): the seat's memory lives under the evidence store,
    #     never the tree. The wrapper links $DSH_HOME/memory into
    #     /var/lib/evidence/seat-memory/<cwd-key> (created 0700 by tmpfiles,
    #     granted to seat@ by ReadWritePaths); a headless job whose brief asks
    #     the seat to remember a note -- the fake upstream answers with a canned
    #     bash tool call that writes it through that link -- proves the note
    #     lands under the evidence store while the workspace's git status stays
    #     clean. git init the workspace so the clean-status assertion is not
    #     vacuous (a note dropped in the tree would show as untracked).
    machine.succeed("git init -q /home/alice/factory/ws")
    machine.succeed(
        "printf '%s\\n' 'echo note > \"$DSH_HOME/memory/note.txt\"' "
        "> /home/alice/factory/memory-brief"
    )
    machine.succeed("chown alice /home/alice/factory/memory-brief")
    memory_submit = machine.succeed(
        "su - alice -c 'seat-submit headless "
        "--workspace /home/alice/factory/ws --dsh-home /home/alice/factory/dsh "
        "--model deepseek/deepseek-v4-flash --effort off --brief /home/alice/factory/memory-brief'"
    )
    memory_job_id = memory_submit.strip().splitlines()[0].strip()
    machine.wait_until_succeeds(
        f"test -f /var/lib/seat/jobs/{memory_job_id}/exit_code.txt"
    )
    # SA7b (decision 59a, fix round): the headless job's launch line, which
    # dsh-openrouter always prints to stderr, names the permission mode the
    # harness actually ran at. A job seat must run at the shipped default
    # (workspace-write) -- the fix delivers the memory link at that mode, so
    # pinning danger-full-access here would pass the note write for the wrong
    # reason (MAJOR-1).
    machine.succeed(
        f"grep -q ', workspace-write,' /var/lib/seat/jobs/{memory_job_id}/stderr.txt"
    )
    machine.succeed("test -f /var/lib/evidence/seat-memory/*/note.txt")
    machine.succeed(
        "test -z \"$(git -C /home/alice/factory/ws status --porcelain)\""
    )
    # The wrapper staged the note under the workspace at workspace-write and
    # relocated it into the evidence store on exit; the staged directory must
    # be gone, not merely git-ignored.
    machine.succeed("test ! -e /home/alice/factory/ws/.dsh-seat-memory")
  '';
}
