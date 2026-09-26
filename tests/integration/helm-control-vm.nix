{
  pkgs,
  helmModule,
}:
let
  # The v0 test's fake basket (tests/integration/helm-vm.nix): a stub whose
  # doctor output feeds the basket-doctor tile without touching real
  # hardware.
  fakeBasket = pkgs.writeShellScriptBin "basket" ''
    echo "PASS swap        no swap devices"
    echo "WARN vsock       module absent in VM"
  '';
in
pkgs.testers.runNixOSTest {
  name = "helm-control";
  nodes.machine =
    { pkgs, lib, ... }:
    {
      imports = [ helmModule ];
      users.users.alice = {
        isNormalUser = true;
        uid = 1000;
      };
      system.configurationRevision = "deadbeef";
      # Exactly one real specialisation ("alt"), allowlisted by the fixed
      # literal (D1), whose only difference from base is the marker it
      # forces. Everything else -- the polkit rule, helm-switch@, helm-serve,
      # every agent unit -- must therefore be byte-identical across the two
      # toplevels, and a switch between them must restart nothing (asserted
      # below via cmp, unit-file stability and NRestarts).
      # mkForce is load-bearing here: environment.etc.<name>.text is a
      # lines-typed option, so without it the specialisation's marker would
      # merge with base's into "base\nalt" and fail the module's own marker
      # assertion (the null-collapse trap's sibling, docs/…/gotchas).
      environment.etc."helm/profile".text = "base";
      specialisation.alt.configuration.environment.etc."helm/profile".text = lib.mkForce "alt";
      security.polkit.enable = true;
      services.helm = {
        enable = true;
        operatorUser = "alice";
        repo = "/var/lib/fake-repo";
        basketPackage = fakeBasket;
        # v0 test settings (tests/integration/helm-vm.nix): no restic repo,
        # no nightly flake check, no broker instances, no system timers.
        restic.repository = "/var/lib/no-such-repo";
        restic.passwordFile = "/etc/no-such-file";
        flakeCheck.enable = false;
        timers.system = [ ];
        timers.user = [ "helm-collect.timer" ];
        brokerInstances = [ ];
        control = {
          enable = true;
          # D1: the allowlist is a fixed literal covering exactly the one
          # declared specialisation.
          profiles = [
            "base"
            "alt"
          ];
          workspaces.demo = {
            path = "/var/lib/fake-repo";
            # plan Task 4's workspace shape; /action/open is never exercised
            # in this VM (headless -- no display to open a terminal on).
            devShell = null;
          };
        };
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
    machine.succeed(
        "su alice -c 'cd /var/lib/fake-repo && git init -q && "
        "git -c user.email=a@b -c user.name=a commit -q --allow-empty -m init'"
    )
    machine.succeed("loginctl enable-linger alice")
    machine.wait_until_succeeds("systemctl --user -M alice@ is-active timers.target")
    machine.succeed("systemctl --user -M alice@ start helm-collect.service")
    machine.wait_for_file("/var/lib/helm/index.html")

    # D7 (consolidated): a switch never starts a newly enabled user unit in
    # an already-running session -- start helm-serve explicitly, exactly the
    # way the runbook tells the operator to after the enabling switch.
    machine.succeed("systemctl --user -M alice@ start helm-serve.service")

    # The control page on an accepted Host: the v0 dashboard plus the
    # injected control sections -- one switch form per profile, one open form
    # per workspace, the per-boot token embedded in every form, and nothing
    # executable in the page (forms only: no <script, no src=, no
    # href="http).
    machine.wait_until_succeeds(
        "curl -fsS -H 'Host: localhost:7700' -o /dev/null http://127.0.0.1:7700/"
    )
    token = machine.succeed("cat /run/user/1000/helm/token").strip()

    def get_page():
        return machine.succeed("curl -fsS -H 'Host: localhost:7700' http://127.0.0.1:7700/")


    page = get_page()
    assert 'action="/action/switch"' in page, (
        "control sections missing from the served page: " + page[:400]
    )
    assert page.count('action="/action/switch"') == 2, "one switch form per profile (base, alt)"
    assert page.count('action="/action/open"') == 1, "one open form per workspace (demo)"
    assert f'value="{token}"' in page, "the per-boot token must be embedded in the forms"
    assert "<script" not in page and "src=" not in page and 'href="http' not in page

    def marker():
        return machine.succeed("cat /etc/helm/profile").strip()


    assert marker() == "base"

    # The agent-unit guard's observable consequence (consolidated D2/D4):
    # across the switches below, no unit matching the agent prefix may
    # restart, appear or disappear -- in the system manager AND alice's user
    # manager (the Rust switch-to-configuration reloads user units as well,
    # so the user scope is half the invariant, not an afterthought).
    # Recorded after helm-serve is up and before any switch runs; re-checked
    # after everything below.
    AGENT_PREFIXES = ("egress-", "cowork", "basket", "restic-backups-", "helm-")
    SCOPES = [("", "system"), ("--user -M alice@", "user")]


    def agent_unit_names(scope, which):
        # list-unit-files names every installed unit file (stable across a
        # switch); list-units --all names every loaded one (picks up the
        # helm-switch@<profile> instances the switches instantiate).
        # Templates ("helm-switch@.service") are skipped: systemctl show
        # cannot address a template name, and only instances ever run -- the
        # loaded sweep below covers those.
        if which == "files":
            listing = machine.succeed(f"systemctl {scope} list-unit-files --no-legend --no-pager")
        else:
            listing = machine.succeed(f"systemctl {scope} list-units --all --no-legend --plain")
        names = set()
        for line in listing.splitlines():
            fields = line.split()
            if fields and fields[0].startswith(AGENT_PREFIXES) and "@." not in fields[0]:
                names.add(fields[0])
        return sorted(names)


    def nrestarts(scope, unit):
        return machine.succeed(f"systemctl {scope} show -p NRestarts --value {unit}").strip()


    agent_files_before = {label: agent_unit_names(scope, "files") for scope, label in SCOPES}
    agent_nrestarts_before = {
        label: {
            u: nrestarts(scope, u)
            for u in sorted(
                set(agent_unit_names(scope, "files")) | set(agent_unit_names(scope, "loaded"))
            )
        }
        for scope, label in SCOPES
    }


    def post(headers, data, prefix="curl"):
        header_args = " ".join(f"-H '{h}'" for h in headers)
        code = machine.succeed(
            f"{prefix} -sS -o /tmp/helm-post.html -w '%{{http_code}}' -X POST {header_args} "
            f"--data '{data}' http://127.0.0.1:7700/action/switch"
        ).strip()
        return code, machine.succeed("cat /tmp/helm-post.html")


    GOOD = ["Host: localhost:7700", "Sec-Fetch-Site: same-origin"]

    # The headline act: a real `switch-to-configuration test` into the alt
    # specialisation, driven through the loopback page the way the
    # operator's click is. The POST blocks until the unit is done; the
    # response is the full page with the success banner (K15: "Now running:
    # alt"); the marker flips; and the activation repoints
    # /run/current-system at the alt toplevel -- asserted as an observable
    # outcome, never by reading switch-to-configuration's source
    # (consolidated D4).
    base_system = machine.succeed("readlink /run/current-system").strip()
    code, body = post(GOOD, f"profile=alt&token={token}")
    assert code == "200", (code, body[:400])
    assert "Now running: alt" in body, body[:400]
    assert marker() == "alt"
    assert machine.succeed("readlink /run/current-system").strip() != base_system

    # ... and back to base ("Now, not forever", K3: the boot default never
    # changed; the machine itself returns to base and /run/current-system
    # lands exactly where it started).
    code, body = post(GOOD, f"profile=base&token={token}")
    assert code == "200", (code, body[:400])
    assert "Now running: base" in body, body[:400]
    assert marker() == "base"
    assert machine.succeed("readlink /run/current-system").strip() == base_system

    # The negative matrix (plan Task 4 / consolidated test #11): every
    # rejected request is a 403 and -- on an accepted Host -- the FULL
    # rendered page with the deny banner (K5: never a bare status line), and
    # the marker never moves.
    def assert_full_deny_page(body):
        assert "<!doctype html>" in body, body[:400]
        assert "Request rejected" in body, body[:400]


    # 1. a foreign Origin, rejected even alongside Sec-Fetch-Site:
    #    same-origin (the forged pair a real browser never sends).
    code, body = post(
        ["Host: localhost:7700", "Sec-Fetch-Site: same-origin", "Origin: http://evil.example"],
        f"profile=alt&token={token}",
    )
    assert code == "403", (code, body[:400])
    assert_full_deny_page(body)
    assert marker() == "base"

    # 2. a wrong Host: the DNS-rebinding defense answers with a minimal
    #    page that never carries the per-boot token or any form (the one
    #    deliberate non-full-page 403 -- a full page embeds the token).
    code, body = post(
        ["Host: evil.example:7700", "Sec-Fetch-Site: same-origin"],
        f"profile=alt&token={token}",
    )
    assert code == "403", (code, body[:400])
    assert "<!doctype html>" in body, body[:400]
    assert token not in body and "<form" not in body
    assert marker() == "base"

    # 3. a missing token.
    code, body = post(GOOD, "profile=alt")
    assert code == "403", (code, body[:400])
    assert_full_deny_page(body)
    assert marker() == "base"

    # 4. a profile outside the allowlist.
    code, body = post(GOOD, f"profile=nope&token={token}")
    assert code == "403", (code, body[:400])
    assert_full_deny_page(body)
    assert marker() == "base"

    # 5. neither Sec-Fetch-Site nor Origin: no same-origin evidence at all.
    code, body = post(["Host: localhost:7700"], f"profile=alt&token={token}")
    assert code == "403", (code, body[:400])
    assert_full_deny_page(body)
    assert marker() == "base"

    # Busy: the switch lock held by another holder answers 409 as the full
    # page with the busy banner (D8/K5), and the marker still does not move.
    code, body = post(
        GOOD,
        f"profile=alt&token={token}",
        prefix="flock /run/user/1000/helm/switch.lock curl",
    )
    assert code == "409", (code, body[:400])
    assert "A switch is already in progress" in body, body[:400]
    assert marker() == "base"

    # Live polkit denials as alice: the rule grants exactly verb=start on
    # the enumerated instances, to the operator. Both switches above ran
    # through that grant (the positive control -- this is not "nothing can
    # ever start these units"); these prove it is not broader than
    # written.
    #
    # A polkit refusal needs a LOADED unit to be observable, and systemd
    # garbage-collects a finished oneshot instance -- on a not-loaded unit
    # KillUnit refuses with ENOENT before consulting polkit (a fail-closed
    # refusal, but not the polkit one). So the strict verb-scoping pin runs
    # against a deliberately failed instance: root starts helm-switch@nope,
    # the switch script's own allowlist gate refuses to run anything
    # (exit 2: the unit FAILED, nothing was executed, no journal begin/end
    # pair), and a failed unit stays loaded. On it, alice's start is
    # denied by ENUMERATION (nope is not in the allowlist) and her
    # kill/set-property by VERB -- each pinned by its MESSAGE, not just
    # the exit code: on start@nope a bare exit-code check would be masked
    # by the very same gate 2 that produced the failed unit (nonzero
    # either way); only "denied"/"not authorized" proves polkit refused
    # the method call.
    machine.succeed("systemctl start helm-switch@nope.service || true")
    machine.wait_until_succeeds("systemctl is-failed helm-switch@nope.service")
    for denied in [
        "systemctl start helm-switch@nope.service",
        "systemctl kill helm-switch@nope.service",
        "systemctl set-property helm-switch@nope.service Nice=1",
    ]:
        rc, out = machine.execute(f"su alice -c '{denied}' 2>&1")
        assert rc != 0, (denied, out)
        lowered = out.lower()
        assert "denied" in lowered or "authoriz" in lowered, (denied, out)

    # The plan's own probes against the ALLOWLISTED instance: @alt was
    # collected after its successful switch, so alice's interference here
    # is refused the way systemd refuses anything on a not-loaded unit (or
    # by polkit, should the instance still be loaded) -- a live refusal
    # either way, marker untouched, nothing executed.
    for denied in [
        "systemctl kill helm-switch@alt.service",
        "systemctl set-property helm-switch@alt.service Nice=1",
    ]:
        rc, out = machine.execute(f"su alice -c '{denied}' 2>&1")
        assert rc != 0, (denied, out)
        lowered = out.lower()
        assert ("denied" in lowered or "authoriz" in lowered) or "not loaded" in lowered, (
            denied,
            out,
        )

    # The journal state machine's raw material (D8): every completed switch
    # left a closed begin/end pair -- exactly two of each, one per switch,
    # none left dangling by any rejected request (nothing rejected ever
    # ran).
    journal = machine.succeed("journalctl -u 'helm-switch@*' --no-pager")
    begins = [l for l in journal.splitlines() if "helm-switch: begin" in l]
    ends = [l for l in journal.splitlines() if "helm-switch: end" in l]
    assert len(begins) == 2, journal
    assert len(ends) == 2, journal

    # D1's artifact consequence: the polkit rule and the helm-switch@ unit
    # text are byte-identical between the base toplevel and the alt
    # specialisation's (a derived allowlist would have made them differ
    # inside the specialisation -- B1's self-trip and M4's narrowing, caught
    # here at the artifact level the way helm-control-eval catches it at
    # eval level).
    machine.succeed(
        "diff -r /run/current-system/etc/polkit-1/rules.d "
        "/run/current-system/specialisation/alt/etc/polkit-1/rules.d"
    )
    machine.succeed(
        "cmp /run/current-system/etc/systemd/system/helm-switch@.service "
        "/run/current-system/specialisation/alt/etc/systemd/system/helm-switch@.service"
    )

    # The NRestarts re-check (baselines recorded above): no agent unit
    # restarted across the switches and none appeared or disappeared, in
    # either manager.
    for scope, label in SCOPES:
        files_after = agent_unit_names(scope, "files")
        assert files_after == agent_files_before[label], (
            label,
            agent_files_before[label],
            files_after,
        )
        for unit, before in agent_nrestarts_before[label].items():
            after = nrestarts(scope, unit)
            assert after == before, (label, unit, before, after)
        # Belt-and-braces beyond "unchanged" for the units the switches
        # legitimately ran (instances that were never in the baseline):
        # every loaded agent SERVICE shows zero restarts. NRestarts is a
        # service property -- a timer has none (empty output) and no
        # restart semantics, so only .service units carry this assertion.
        for unit in agent_unit_names(scope, "loaded"):
            if not unit.endswith(".service"):
                continue
            assert nrestarts(scope, unit) == "0", (label, unit)

    # The same per-boot token still serves the page: helm-serve itself was
    # not restarted by either switch (a restart would have rotated the
    # token), and the forms-only invariant holds on the post-switch page
    # too. /action/open is deliberately NOT exercised anywhere above: the
    # VM is headless (that surface is acceptance's, on the real desktop).
    page = get_page()
    assert page.count('action="/action/switch"') == 2
    assert page.count('action="/action/open"') == 1
    assert f'value="{token}"' in page
    assert "<script" not in page and "src=" not in page and 'href="http' not in page
  '';
}
