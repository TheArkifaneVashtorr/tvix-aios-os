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
        # helm-serve re-reads the system journal for the switch state
        # (read_state's begin/end pairs -- D8). Production's operator is in
        # wheel, which systemd counts as a journal-access group; alice needs
        # the same read here WITHOUT wheel's admin rights, because the
        # session-less refusal below depends on alice not being an admin.
        extraGroups = [ "systemd-journal" ];
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
            # The workspace launcher is exercised by its own bats suite and
            # helm-control-eval's launcher assertion; D-H1 parked the page
            # rendering, so /action/open is deliberately never exercised in
            # this VM (headless -- no display to open a terminal on, and the
            # page no longer carries a form anyway).
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

    # D-H1: the control page on an accepted Host is the v0 dashboard plus
    # the read-only Profile section -- no <form, no action=, nothing
    # executable in the page (no <script, no src=, no href="http), and no
    # per-boot token file anywhere.
    machine.wait_until_succeeds(
        "curl -fsS -H 'Host: localhost:7700' -o /dev/null http://127.0.0.1:7700/"
    )

    def get_page():
        return machine.succeed("curl -fsS -H 'Host: localhost:7700' http://127.0.0.1:7700/")


    page = get_page()
    assert "<form" not in page, "the page must be read-only (no <form): " + page[:400]
    assert "action=" not in page, "the page must carry no action=: " + page[:400]
    assert "<script" not in page and "src=" not in page and 'href="http' not in page
    machine.fail("test -e /run/user/1000/helm/token")

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

    base_system = machine.succeed("readlink /run/current-system").strip()

    # (b) D-H1: every POST is read-only. An accepted Host answers 405 with
    # the plain-text "read-only" body; a rebound Host answers the 403
    # minimal page. The marker never moves.
    code = machine.succeed(
        "curl -sS -o /dev/null -w '%{http_code}' -X POST -H 'Host: localhost:7700' "
        "--data 'profile=alt' http://127.0.0.1:7700/action/switch"
    ).strip()
    assert code == "405", code
    code = machine.succeed(
        "curl -sS -o /dev/null -w '%{http_code}' -X POST -H 'Host: evil.example:7700' "
        "--data 'profile=alt' http://127.0.0.1:7700/action/switch"
    ).strip()
    assert code == "403", code

    # (c) D-H1's proof: a session-less operator start of the ALLOWED unit is
    # refused. polkit now returns AUTH_ADMIN_KEEP for verb=start on the
    # enumerated instances, so alice -- with no polkit agent in this
    # headless context -- gets "Interactive authentication required." from
    # systemd and the unit never runs: no journal begin, marker untouched.
    rc, out = machine.execute("su alice -c 'systemctl start helm-switch@alt.service' 2>&1")
    assert rc != 0, (rc, out)
    # D-H1: polkit returned AUTH_ADMIN_KEEP, so systemd demands interactive
    # authentication; a session-less (non-interactive) caller is refused for
    # want of an enabled interactive-authentication path. "interactive
    # authentication" is the AUTH refusal's fingerprint -- the enumeration
    # denials elsewhere say "denied"/"not authorized" without it.
    assert "interactive authentication" in out.lower(), out
    # No switch has run yet, so the journal has no begin line. journalctl
    # exits 1 on an empty boot-scoped filter — that is expected here and is
    # exactly what we assert (the refused start left nothing behind).
    _, jr = machine.execute("journalctl -u 'helm-switch@*' --no-pager")
    assert "helm-switch: begin" not in jr, jr
    assert marker() == "base"

    # (d) the positive control as root: the D4 activation proof. A real
    # `switch-to-configuration test` into the alt specialisation, then back
    # to base -- asserted by the observable marker and the
    # /run/current-system repoint, never by reading switch-to-configuration's
    # source.
    machine.succeed("systemctl start helm-switch@alt.service")
    assert marker() == "alt"
    assert machine.succeed("readlink /run/current-system").strip() != base_system
    machine.succeed("systemctl start helm-switch@base.service")
    assert marker() == "base"
    assert machine.succeed("readlink /run/current-system").strip() == base_system

    # The negative matrix (plan Task 4 / consolidated test #11): alice's
    # start of the non-allowlisted instance is refused by ENUMERATION, and
    # her kill/set-property by VERB. A polkit refusal needs a LOADED unit to
    # be observable, and systemd garbage-collects a finished oneshot
    # instance -- on a not-loaded unit KillUnit refuses with ENOENT before
    # consulting polkit (a fail-closed refusal, but not the polkit one). So
    # the strict verb-scoping pin runs against a deliberately failed
    # instance: root starts helm-switch@nope, the switch script's own
    # allowlist gate refuses to run anything (exit 2: the unit FAILED,
    # nothing was executed, no journal begin/end pair), and a failed unit
    # stays loaded. On it, alice's start is denied by ENUMERATION (nope is
    # not in the allowlist) and her kill/set-property by VERB -- each pinned
    # by its MESSAGE, not just the exit code.
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
    # left a closed begin/end pair -- exactly two of each, one per root
    # switch in (d), none left dangling by the refused session-less start
    # or any rejected request (nothing rejected ever ran).
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

    # (f) the read-only state is still served: /control.json's last_switch
    # names base -- the root switches in (d) are the only completed ones.
    last_to = machine.succeed(
        "curl -fsS -H 'Host: localhost:7700' http://127.0.0.1:7700/control.json "
        "| jq -r '.last_switch.to'"
    ).strip()
    assert last_to == "base", last_to
  '';
}
