{
  pkgs,
  egressBrokerModule,
  modelLaneModule,
}:
let
  # Single-host variant of tests/integration/broker-vm.nix's testCerts: only
  # "openrouter.test" is needed here (this lane's broker instance allows
  # exactly one host).
  testCerts =
    pkgs.runCommand "lane-vm-test-certs"
      {
        nativeBuildInputs = [ pkgs.openssl ];
      }
      ''
        mkdir -p $out
        openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
          -keyout $out/ca.key -out $out/ca.crt -subj "/CN=lane-vm-test-ca"
        openssl req -newkey rsa:2048 -nodes \
          -keyout $out/openrouter.test.key -out $out/openrouter.test.csr \
          -subj "/CN=openrouter.test" -addext "subjectAltName=DNS:openrouter.test"
        openssl x509 -req -in $out/openrouter.test.csr -CA $out/ca.crt -CAkey $out/ca.key \
          -CAcreateserial -days 3650 -copy_extensions copy -out $out/openrouter.test.crt
        openssl x509 -in $out/ca.crt -noout -checkend 31536000
        openssl x509 -in $out/openrouter.test.crt -noout -checkend 31536000
      '';
  # Fixture data (not a secret): the "OpenRouter" answer the fake upstream
  # hands back so step 1 below can prove the full round trip, not just that
  # *a* 200 came back.
  fakeAnswer = builtins.toJSON {
    id = "gen-1";
    model = "deepseek/deepseek-v4-flash";
    provider = "DeepSeek";
    choices = [
      {
        message = {
          role = "assistant";
          content = "vm-fake-answer";
        };
      }
    ];
    usage = {
      prompt_tokens = 3;
      completion_tokens = 2;
      total_tokens = 5;
    };
  };
  chatJob = builtins.toJSON [
    {
      role = "user";
      content = "hi";
    }
  ];
  # Step 2b probe bodies: a chat request with NO provider key (the only way
  # to prove the broker -- not the lane client, which sends its own provider
  # block -- enforces the ZDR patch) and a plain body for the unlisted
  # /api/v1/models path that must arrive unpatched.
  zdrProbeBody = builtins.toJSON {
    model = "m";
    messages = [
      {
        role = "user";
        content = "zdr-direct-probe";
      }
    ];
  };
  modelsProbeBody = builtins.toJSON { model = "m"; };
  # Step 2c probe body: an Anthropic-style messages request. Nothing consumes
  # OpenRouter's /api/v1/messages path (O3 resolved: fail closed), so the
  # broker must deny it -- this probe proves the deny reaches the client and
  # the fake upstream never sees the request at all.
  messagesProbeBody = builtins.toJSON {
    model = "m";
    max_tokens = 16;
    messages = [
      {
        role = "user";
        content = "messages-direct-probe";
      }
    ];
  };
  # A plain stdlib TLS server, not nginx: nginx's $request_body is only
  # populated for locations that force the body to be read (proxy_pass and
  # friends) -- a bare `return 200 ...` location never reads it, so
  # $request_body stayed "-" in every access_log line no matter where
  # log_format was placed (tried commonHttpConfig too). This logs the
  # request path, the Authorization header and the raw POST body verbatim,
  # one record per POST (path, then header, then body, then a "---"
  # separator), which is exactly what steps 2 and 2b below need to prove.
  fakeUpstream = pkgs.writeText "lane-vm-fake-upstream.py" ''
    import http.server
    import ssl

    ANSWER = ${builtins.toJSON fakeAnswer}.encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            with open("/var/log/lane-vm-fake-upstream.log", "a") as f:
                f.write(self.path + "\n")
                f.write(self.headers.get("Authorization", "") + "\n")
                f.write(body.decode("utf-8", "replace") + "\n---\n")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(ANSWER)

    httpd = http.server.HTTPServer(("0.0.0.0", 443), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain("${testCerts}/openrouter.test.crt", "${testCerts}/openrouter.test.key")
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    httpd.serve_forever()
  '';
  # T3: stands in for the real `claude` binary lane-run.py's "agent" job
  # kind shells out to (nixosModules/modelLane.nix's `path =
  # [ "/run/current-system/sw" ]` is exactly what makes an
  # environment.systemPackages entry named "claude" reachable from the
  # unit -- the same mechanism the operator's real one relies on). Prints
  # a --output-format-json-shaped blob to stdout and touches a file in its
  # own cwd, which is the only thing that actually proves the unit's cwd
  # was the copied repo snapshot and not some other directory.
  fakeClaude = pkgs.writeShellScriptBin "claude" ''
    set -euo pipefail
    echo "vm-agent-edit" > edited-by-agent.txt
    cat <<'JSON'
    {"result": "vm-agent-result", "usage": {"input_tokens": 1, "output_tokens": 1}}
    JSON
  '';
in
pkgs.testers.runNixOSTest {
  name = "lane-openrouter";
  nodes.machine =
    { pkgs, ... }:
    {
      imports = [
        egressBrokerModule
        modelLaneModule
      ];
      security.pki.certificateFiles = [ "${testCerts}/ca.crt" ];
      networking.hosts."127.0.0.1" = [ "openrouter.test" ];

      environment = {
        etc = {
          "lane-vm-job.json".text = chatJob;
          "lane-vm-zdr-probe.json".text = zdrProbeBody;
          "lane-vm-models-probe.json".text = modelsProbeBody;
          "lane-vm-messages-probe.json".text = messagesProbeBody;
          # T3: a plain-text prompt file, not an inline `<<<` heredoc in the
          # testScript -- keeps the su -c command a single-quoted string
          # with no nested quoting, the same shape every other
          # machine.succeed(...) call in this file already uses.
          "lane-vm-agent-prompt.txt".text = "edit the file";
        };
        # T3: the agent kind's `claude` (see fakeClaude above) -- on the
        # real host this is the operator's own system profile; here it's
        # a package like any other, reachable the same way.
        systemPackages = [
          fakeClaude
          # Step 2b: the direct in-netns probe proving the broker (not the
          # client) enforces the ZDR patch. ip(8) is already present for
          # the egress-netns unit; curl is not, so it's added here.
          pkgs.curl
        ];
      };

      users.users.operator = {
        isNormalUser = true;
        uid = 2000;
      };
      users.users.bystander = {
        isNormalUser = true;
        uid = 2001;
      };

      services.model-lanes.openrouter = {
        host = "openrouter.test";
        model = "test/model-flash";
        keyFile = "/run/lane-secret";
        hostAddress = "10.100.30.1";
        namespaceAddress = "10.100.30.2";
        listenPort = 3199;
        operatorUser = "operator";
      };

      systemd.services = {
        "egress-broker-openrouter" = {
          after = [ "lane-secret.service" ];
          requires = [ "lane-secret.service" ];
        };
        fake-upstream = {
          description = "Fake TLS OpenRouter-compatible upstream for the lane VM test";
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            ExecStart = "${pkgs.python3}/bin/python3 ${fakeUpstream}";
            Restart = "on-failure";
          };
        };
        # Stands in for the operator's real one-time procedure (digest
        # docs/research-2026-09-03-openrouter-deepseek.md): a root-only key
        # file the lane module's tmpfiles rule resets to 0440
        # root:egress-broker. Not a real credential -- a fixture string this
        # test greps for to prove it never leaves the broker.
        lane-secret = {
          wantedBy = [ "multi-user.target" ];
          before = [ "egress-broker-openrouter.service" ];
          serviceConfig = {
            Type = "oneshot";
            RemainAfterExit = true;
          };
          script = ''
            umask 077
            echo "vm-lane-fake-key" > /run/lane-secret
            chown root:egress-broker /run/lane-secret
            chmod 0440 /run/lane-secret
          '';
        };
        # T2 fix round (major finding): real, pre-existing files at two of
        # the paths lane-openrouter@'s InaccessiblePaths hides, so the
        # sandbox probe below (step 3b) proves a real "exists and is
        # readable" is transformed into "unreadable to this unit" -- not
        # just that the path was already absent on a fresh VM (the "-"
        # prefix on those entries means "tolerate a missing source", which
        # would make a hidden-but-absent path indistinguishable from a
        # working hide).
        lane-vm-fixtures = {
          description = "Fixture local-only trees lane-openrouter@ must never see (T2 fix round)";
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            Type = "oneshot";
            RemainAfterExit = true;
          };
          script = ''
            mkdir -p /run/baskets /var/lib/secrets
            echo "LANE-VM-FIXTURE-BASKET" > /run/baskets/marker
            echo "LANE-VM-FIXTURE-SECRET" > /var/lib/secrets/marker
            chmod 0644 /run/baskets/marker /var/lib/secrets/marker
            # T3: a --repo source for the agent-kind job below -- world-
            # readable so the operator (not root) can `lane-submit --repo`
            # it, outside every FORBIDDEN_REPO_PREFIXES entry on purpose
            # (this is what "permitted" is supposed to look like).
            mkdir -p /var/lib/lane-vm-agent-repo
            echo "agent repo fixture" > /var/lib/lane-vm-agent-repo/README.md
            chmod 0755 /var/lib/lane-vm-agent-repo
            chmod 0644 /var/lib/lane-vm-agent-repo/README.md
          '';
        };
      };
    };
  testScript = ''
    machine.wait_for_unit("fake-upstream.service")
    machine.wait_for_unit("egress-broker-openrouter.service")
    machine.wait_for_unit("lane-vm-fixtures.service")
    machine.wait_until_succeeds(
        "test -f /var/lib/egress-broker/openrouter/ca/ca-bundle.crt"
    )
    # The T2 fix round's public copy (nixosModules/egressBroker.nix's
    # ExecStartPost) -- the file lane-openrouter@'s SSL_CERT_FILE actually
    # points at, since the private confdir tree is InaccessiblePaths-hidden
    # from that unit (see step 1 below, and lane-eval's cross-check).
    machine.wait_until_succeeds(
        "test -f /var/lib/egress-broker-ca-bundle/openrouter/ca-bundle.crt"
    )
    # The fixtures are real files at real, pre-existing host paths -- readable
    # here, from OUTSIDE lane-openrouter@'s sandbox -- so step 3b below proves
    # a transformation, not an already-missing path.
    machine.succeed("grep -q LANE-VM-FIXTURE-BASKET /run/baskets/marker")
    machine.succeed("grep -q LANE-VM-FIXTURE-SECRET /var/lib/secrets/marker")

    # 1. the operator submits a "permitted" chat job; the unit runs; the
    #    result file carries the fake upstream's answer end to end.
    job_id = machine.succeed(
        "su - operator -c 'lane-submit openrouter --kind chat --class permitted "
        "--model test/model-flash < /etc/lane-vm-job.json'"
    ).strip()
    machine.wait_until_succeeds(
        f"test -f /var/lib/lanes/openrouter/results/{job_id}.json"
    )
    result = machine.succeed(
        f"cat /var/lib/lanes/openrouter/results/{job_id}.json"
    )
    assert "vm-fake-answer" in result, result

    # 2. the fake upstream saw the broker-injected credential (this process
    #    never held it -- see the lane-secret script above) and the
    #    provider block this lane's client always sends.
    api_log = machine.succeed("cat /var/log/lane-vm-fake-upstream.log")
    assert "Bearer vm-lane-fake-key" in api_log, api_log
    assert '"data_collection": "deny"' in api_log, api_log
    assert '"zdr": true' in api_log, api_log

    # 2b. the broker -- not the client -- enforces the ZDR patch (W2-N3,
    #     rework of the vacuous zdr assertion in step 2 above): a request
    #     from INSIDE the broker's netns with a JSON body carrying NO
    #     provider key still reaches the fake upstream with "zdr": true
    #     merged in at the chokepoint, and a companion request to an
    #     unlisted path (/api/v1/models) arrives byte-for-byte unpatched.
    #     Step 2's zdr assertion can never prove the broker does the
    #     enforcement -- the lane client sends "zdr": true itself -- but
    #     these probes' bodies have no provider key at all, so the only
    #     place "zdr": true can come from is egressBroker.nix's
    #     body_patch wire format.
    machine.succeed(
        "ip netns exec egress-openrouter curl -s --max-time 15 "
        "-x http://10.100.30.1:3199 "
        "--cacert /var/lib/egress-broker-ca-bundle/openrouter/ca-bundle.crt "
        "-X POST -H 'content-type: application/json' "
        "--data-binary @/etc/lane-vm-zdr-probe.json "
        "https://openrouter.test/api/v1/chat/completions"
    )
    machine.succeed(
        "ip netns exec egress-openrouter curl -s --max-time 15 "
        "-x http://10.100.30.1:3199 "
        "--cacert /var/lib/egress-broker-ca-bundle/openrouter/ca-bundle.crt "
        "-X POST -H 'content-type: application/json' "
        "--data-binary @/etc/lane-vm-models-probe.json "
        "https://openrouter.test/api/v1/models"
    )
    # Each POST logs three lines (path, Authorization header, raw body) then
    # a "---" separator; pair each path with the body the upstream saw.
    api_log2 = machine.succeed("cat /var/log/lane-vm-fake-upstream.log")
    records = [r.strip().split("\n") for r in api_log2.split("---\n") if r.strip()]
    by_path = {r[0]: r[2] for r in records if len(r) == 3}
    chat_body = by_path["/api/v1/chat/completions"]
    assert "zdr-direct-probe" in chat_body, chat_body
    assert '"zdr": true' in chat_body, chat_body
    assert '"data_collection": "deny"' in chat_body, chat_body
    models_body = by_path["/api/v1/models"]
    assert models_body == '{"model":"m"}', models_body

    # 2c. /api/v1/messages is denied at the broker, fail closed (N13, O3
    #     resolved): nothing consumes OpenRouter's Anthropic-style
    #     /api/v1/messages path -- the seat and the lane both use chat
    #     completions -- so a POST through the broker to that path is
    #     refused with audit reason "path-not-permitted" BEFORE the key is
    #     injected, and must never reach the fake upstream.
    deny_resp = machine.succeed(
        "ip netns exec egress-openrouter curl -s --max-time 15 "
        "-x http://10.100.30.1:3199 "
        "--cacert /var/lib/egress-broker-ca-bundle/openrouter/ca-bundle.crt "
        "-X POST -H 'content-type: application/json' "
        "--data-binary @/etc/lane-vm-messages-probe.json "
        "https://openrouter.test/api/v1/messages"
    )
    assert "egress-broker: denied" in deny_resp, deny_resp
    machine.succeed(
        "jq -es '[.[] | select(.path==\"/api/v1/messages\" and "
        ".verdict==\"deny\" and .reason==\"path-not-permitted\")] "
        "| length == 1' /var/lib/egress-broker/openrouter/audit.jsonl"
    )
    api_log3 = machine.succeed("cat /var/log/lane-vm-fake-upstream.log")
    assert "/api/v1/messages" not in api_log3, api_log3

    # 3. neither the unit's own rendered config nor any job file on disk
    #    ever carries the key -- only the broker's key file and its audit
    #    of the injected header (already proven allowlist-only by
    #    checks.integration) hold it.
    machine.fail("systemctl cat 'lane-openrouter@.service' | grep -q vm-lane-fake-key")
    machine.fail("grep -rq vm-lane-fake-key /var/lib/lanes/openrouter/jobs")

    # 3b. T2 fix round (major finding): InaccessiblePaths itself denies
    #     access to real, pre-existing local-only paths -- proven by
    #     execution, not by lane-eval's build-time echo of the option
    #     value. Kept alongside the real agent job in step 4.5 below (T3
    #     fix round fixed the job-dir permissions bug this comment used to
    #     describe) as a second, more direct proof: this probe carries the
    #     REAL InaccessiblePaths value lane-openrouter@ rendered (read live
    #     via `systemctl show`,
    #     not retyped by hand -- a future change to
    #     nixosModules/modelLane.nix's list is caught here automatically,
    #     same as lane-eval's own cross-check) plus the same
    #     ProtectSystem=strict/ProtectHome=yes the real unit sets, so this
    #     exercises the sandbox systemd actually built for the lane, not a
    #     parallel guess.
    # "show" (unlike "cat" in step 3 above) needs a concrete unit name, not
    # the bare template -- an instance name that was never started still
    # resolves its static ExecStart-independent properties from the
    # template on disk, so this never actually runs a job.
    inaccessible = machine.succeed(
        "systemctl show 'lane-openrouter@sandbox-probe.service' "
        "-p InaccessiblePaths --value"
    ).strip()
    assert inaccessible, "lane-openrouter@ rendered an empty InaccessiblePaths"
    probe_status, probe_out = machine.execute(
        "systemd-run --wait --pipe --collect --unit=lane-vm-sandbox-probe "
        "--property=ProtectSystem=strict --property=ProtectHome=yes "
        "--property='InaccessiblePaths=" + inaccessible + "' -- "
        "/bin/sh -c 'rc=0; cat /run/baskets/marker 2>&1 || rc=1; echo ---; "
        "cat /var/lib/secrets/marker 2>&1 || rc=1; exit $rc'"
    )
    assert probe_status != 0, f"sandbox probe should have failed: {probe_out}"
    assert "LANE-VM-FIXTURE" not in probe_out, probe_out

    # 4. a local-only job is refused at runtime (belt-and-braces: the
    #    module's own build-time assertion is checks.lane-assertion-negative)
    #    and produces no ledger line.
    local_job_id = machine.succeed(
        "su - operator -c 'lane-submit openrouter --kind chat --class local-only "
        "--model test/model-flash < /etc/lane-vm-job.json'"
    ).strip()
    machine.wait_until_succeeds(
        f"test -f /var/lib/lanes/openrouter/results/{local_job_id}.json"
    )
    refused = machine.succeed(
        f"cat /var/lib/lanes/openrouter/results/{local_job_id}.json"
    )
    assert "error" in refused, refused

    # 4.5 T3: an "agent" job kind runs `claude -p` under the sandbox
    #     against a repo snapshot lane-submit copied and hardened (2770
    #     dirs / 0660 files, group lane) -- proves the DynamicUser unit
    #     can actually create its config dir and read/write the snapshot
    #     (T3 fix round blocker B: the job dir used to be 0755, owned by
    #     the operator with no group-write for "lane", so this failed
    #     with PermissionError and no result file before the fix).
    #     --keep-snapshot so step 4.6 below can inspect the file the fake
    #     `claude` touched in its own cwd.
    agent_job_id = machine.succeed(
        "su - operator -c 'lane-submit openrouter --kind agent --class permitted "
        "--model test/model-flash --repo /var/lib/lane-vm-agent-repo "
        "--keep-snapshot < /etc/lane-vm-agent-prompt.txt'"
    ).strip()
    machine.wait_until_succeeds(
        f"test -f /var/lib/lanes/openrouter/results/{agent_job_id}.json"
    )
    agent_result = machine.succeed(
        f"cat /var/lib/lanes/openrouter/results/{agent_job_id}.json"
    )
    assert "vm-agent-result" in agent_result, agent_result
    assert "error" not in agent_result, agent_result

    # 4.6 the snapshot survives (--keep-snapshot) and holds the file the
    #     fake claude touched in its cwd -- proof the unit's cwd really
    #     was the copied repo, not some other directory.
    machine.succeed(
        "grep -q vm-agent-edit "
        f"/var/lib/lanes/openrouter/jobs/{agent_job_id}/repo/edited-by-agent.txt"
    )

    # 5. the ledger carries exactly the two successful jobs from steps 1
    #    and 4.5 -- the refused job in step 4 never appended a line.
    ledger = machine.succeed("cat /var/lib/lanes/openrouter/ledger.jsonl")
    lines = [line for line in ledger.splitlines() if line.strip()]
    assert len(lines) == 2, ledger
    assert job_id in lines[0], ledger
    assert agent_job_id in lines[1], ledger

    # 6. an unrelated user cannot start a job on this lane's template unit
    #    (polkit rule gates verb=start to operatorUser only); the operator
    #    themselves CAN start (positive control -- the grant actually
    #    exists, this isn't "nothing can ever start this unit") but the
    #    same rule never grants stop/restart/kill, even to the operator.
    #    Re-running job_id's already-completed job is a harmless no-op
    #    from the ledger's perspective (its own assertion above already
    #    ran) -- these two run after it on purpose.
    machine.fail(
        f"su - bystander -c 'systemctl start lane-openrouter@{job_id}.service'"
    )
    machine.succeed(
        f"su - operator -c 'systemctl start lane-openrouter@{job_id}.service'"
    )
    machine.fail(
        f"su - operator -c 'systemctl stop lane-openrouter@{job_id}.service'"
    )
  '';
}
