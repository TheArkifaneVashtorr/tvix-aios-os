# checks.comfy-worlds-vm — the end-to-end NixOS VM proof for
# services.comfyui-worlds on CPU, with a logged-in operator user (alice, uid
# 1000, linger enabled — the helm-control-vm.nix pattern). This proves, on
# real systemd, the things pure evaluation cannot see:
#
#   - comfy-worlds-init builds the per-world tree (models + git lab) that the
#     generator's ExecStartPre guard demands;
#   - one generator at a time: starting sfw answers on 8188, starting nsfw
#     answers on 8189 and stops sfw (the journal shows the stop, `is-active`
#     reads `inactive`, and 8188 refuses);
#   - a workflow saved through ComfyUI's HTTP API lands under the nsfw lab's
#     user directory (worlds/nsfw/lab/user/default/workflows);
#   - a render dropped into nsfw/output appears on the feed with its prompt
#     text (after `index --rebuild`);
#   - GN26: the LAN face is services.lan-access's — ONE site
#     (worlds.core.local) fronting the ONE feed server with ONE credential
#     (401 without it, 200 with it, a wrong password refused), behind
#     Caddy's internal CA;
#   - Caddy answers the :80 redirect beside :443 (lanAccess.nix leaves
#     auto_https untouched; the worlds module's hostwide disable_redirects
#     died with its Caddy block), the world ports bind 127.0.0.1 only, and
#     the firewall opens 80+443 on the LAN interface (eth1) only;
#   - with the lab repo gone, the generator refuses to start and names
#     comfy-worlds-init;
#   - a missing bcrypt hash file makes caddy refuse to (re)load with an
#     error naming the file, and start again once the file is back.
#   - GN14: the local model unit trades the GPU with the generator through
#     systemd Conflicts= (both directions: starting the model stops the
#     renderer, starting the renderer stops the model), the digest guard
#     refuses a corrupted GGUF at start, and probe 1's fallback is pinned
#     (IPAddressDeny omitted -- the user manager cannot attach the BPF
#     program; measured on this pin's test VM).
#   - GN52: the card tool's offline arm by hand — a real safetensors
#     fixture (8-byte header length, JSON header, the data bytes the
#     offsets name) behind a [[model]] row; comfy-cards reads the header,
#     decides the trigger, writes it into lab/manifest.toml and the
#     sidecar under lab/cards/. cards.enable stays OFF here (no broker
#     instance in this VM; the unit's proof is comfy-worlds-eval's cCards
#     arm) — the offline arm is the operator's hand tool.
#
# The accepted cost matches tests/integration/comfyui-vm.nix: the torch-bin
# cu128 closure lands in the image even on CPU, and this test starts two
# generators (8096 MB / 24 GB, long first waits). See the design:
# docs/superpowers/specs/2026-09-05-comfy-worlds-design.md (§7 "Proof").
{ pkgs, module }:
let
  worldsPkgs = import ../../pkgs/comfy-worlds { inherit pkgs; };
in
pkgs.testers.runNixOSTest {
  name = "comfy-worlds-vm";

  nodes.machine =
    { pkgs, ... }:
    {
      # GN26: the LAN face is services.lan-access's — imported beside the
      # worlds module the same way local-model is (checks.nix hands this
      # file exactly one `module` argument; a second module rides the
      # node's own imports list, the GN14 precedent).
      imports = [
        module
        ../../nixosModules/local-model.nix
        ../../../nixosModules/lanAccess.nix
      ];
      # vhostName derives worlds.core.local from hostName; the real host is
      # "core", so the VM mirrors it (Assumption 8's contract).
      networking.hostName = "core";
      # Same accepted cost as tests/integration/comfyui-vm.nix: the torch-bin
      # closure is in the image even on CPU, and this test starts two generators.
      virtualisation.memorySize = 8192;
      virtualisation.diskSize = 24576;
      services = {
        comfyui-worlds = {
          enable = true;
          operatorUser = "alice";
          root = "/home/alice/comfyui";
          cpuOnly = true;
          # GN22: the ONE feed port — one comfy-feed.service serves every
          # world's world-scoped routes under /w/<name>/ on 8288. GN26: no
          # host lines and no lan block — the module renders no Caddy at all.
          feedPort = 8288;
          worlds.sfw.comfyPort = 8188;
          worlds.nsfw.comfyPort = 8189;
        };
        # GN26 — the one site, one credential: worlds.core.local fronting
        # the ONE feed server's 8288 (the Helm shape,
        # hosts/core/lan-access.nix's sites.worlds row; user "alice" is the
        # VM's operator). A4 holds by construction — the hashFile sits
        # under /var/lib/lan-access/.
        lan-access = {
          enable = true;
          interface = "eth1"; # nixos/lib/testing/network.nix: vlan interfaces start at eth1
          sites.worlds = {
            upstream = "127.0.0.1:8288";
            hashFile = "/var/lib/lan-access/worlds.bcrypt";
            user = "alice";
          };
        };
        # GN14: the model unit with a stub llama-server (the real one would
        # need the 22 GB GGUF and a GPU; the turn-taking is systemd's, so
        # the ExecStart binary is irrelevant to what these steps prove). The
        # digest is the real sha256 of the fixture the testScript writes.
        local-model = {
          enable = true;
          operatorUser = "alice";
          modelPath = "/home/alice/models/fake.gguf";
          sha256 = builtins.hashString "sha256" "not a real gguf";
          package = pkgs.writeShellApplication {
            name = "llama-server";
            runtimeInputs = [ pkgs.coreutils ];
            text = "exec ${pkgs.coreutils}/bin/sleep 600";
          };
        };
      };
      users.users.alice = {
        isNormalUser = true;
        uid = 1000;
      };
      networking.extraHosts = "127.0.0.1 worlds.core.local";
      environment.systemPackages = [
        pkgs.curl
        pkgs.jq
        # The nft command for the firewall assertion (step 7); the firewall
        # unit runs it via its absolute store path, so it is not otherwise on
        # the interactive PATH.
        pkgs.nftables
        # The feed's `index --rebuild` (step 5) runs interactively as alice,
        # so comfy-feed must be on the PATH the module otherwise only embeds
        # as an absolute ExecStart.
        worldsPkgs.comfy-feed
        # The like assertion (step 5b) reads the likes count straight from
        # feed.sqlite.
        pkgs.sqlite
        # GN52 step (11) writes the safetensors fixture with python3 (the
        # header length depends on the JSON it serialises, so a shell
        # printf cannot build it honestly).
        pkgs.python3
      ];
      # GN26: the ONE bcrypt file (the hash alone — not the retired
      # user-hash line shape), written before caddy first loads its config
      # (a oneshot, since systemd.tmpfiles cannot run a program). Wanted at
      # boot rather than Required-by caddy: a hard `requiredBy` would re-run
      # this oneshot on every caddy restart and re-create the hash file step
      # (9) moves away (the lan-vm.nix precedent).
      systemd.services.comfy-test-passwords = {
        description = "Test fixture: the one basic_auth bcrypt hash, before caddy first loads its config";
        before = [ "caddy.service" ];
        wantedBy = [ "multi-user.target" ];
        after = [ "systemd-tmpfiles-setup.service" ];
        serviceConfig = {
          Type = "oneshot";
          RemainAfterExit = true;
        };
        path = [
          pkgs.caddy
          pkgs.coreutils
        ];
        script = ''
          caddy hash-password --plaintext "test-worlds" > /var/lib/lan-access/worlds.bcrypt
          chown caddy:caddy /var/lib/lan-access/worlds.bcrypt
          chmod 0400 /var/lib/lan-access/worlds.bcrypt
        '';
      };
    };

  testScript = ''
    import json

    # The operator user is logged in (linger) before any user-scope unit.
    machine.wait_for_unit("multi-user.target")
    machine.wait_for_unit("caddy.service")
    machine.succeed("loginctl enable-linger alice")
    machine.wait_until_succeeds("systemctl --user -M alice@ is-system-running", timeout=120)

    # (1) comfy-worlds-init builds the per-world tree (models + git lab) as alice.
    machine.succeed("runuser -u alice -- comfy-worlds-init --root /home/alice/comfyui")
    machine.succeed("test -d /home/alice/comfyui/worlds/sfw/lab/.git")
    machine.succeed("test -d /home/alice/comfyui/worlds/nsfw/lab/.git")

    # The generator and feed units ReadWritePath "%h/.cache" (ComfyUI's python
    # cache dir); a fresh VM user has no ~/.cache, and a missing ReadWritePath
    # makes the mount namespace fail with status 226/NAMESPACE. A logged-in
    # user has one, so create it before any user unit starts.
    machine.succeed("runuser -u alice -- mkdir -p /home/alice/.cache")

    # (2) start sfw: the generator answers on 8188, the one feed's healthz on
    # 8288 names every world (worldsOrder, comma-joined).
    machine.succeed("systemctl --user -M alice@ start comfy-world-sfw.target")
    stats = machine.wait_until_succeeds("curl -fsS http://127.0.0.1:8188/system_stats", timeout=600)
    statsj = json.loads(stats)
    assert "cpu" in statsj["devices"][0]["name"], (
        f"expected a cpu device, got: {statsj['devices']}"
    )
    health = machine.wait_until_succeeds("curl -fsS http://127.0.0.1:8288/healthz", timeout=60)
    assert health.strip() == "ok nsfw,sfw", f"feed healthz: {health!r}"

    # (3) start nsfw: 8189 answers, 8188 is gone, the sfw generator is
    # inactive and the journal records the stop.
    machine.succeed("systemctl --user -M alice@ start comfy-world-nsfw.target")
    machine.wait_until_succeeds("curl -fsS http://127.0.0.1:8189/system_stats", timeout=600)
    machine.wait_until_succeeds(
        'test "$(systemctl --user -M alice@ is-active comfyui-sfw)" = inactive',
        timeout=60,
    )
    machine.fail("curl -fsS http://127.0.0.1:8188/system_stats")
    machine.wait_until_succeeds(
        "journalctl --no-pager -b | grep -q 'Stopped ComfyUI generator for world sfw'",
        timeout=60,
    )

    # (4) a workflow POSTed on 8189 lands in the nsfw lab's user directory.
    # The /userdata/{file} route matches one path segment, and the handler
    # URL-decodes it (user_manager.py: `if "%" in file: parse.unquote(file)`)
    # — the frontend sends the nested name with the slash encoded as %2F.
    machine.succeed(
        "curl -fsS -X POST -H 'content-type: application/json' "
        "--data-binary '{}' http://127.0.0.1:8189/userdata/workflows%2Ft.json"
    )
    machine.wait_until_succeeds(
        "test -f /home/alice/comfyui/worlds/nsfw/lab/user/default/workflows/t.json",
        timeout=60,
    )

    # (5) a render dropped into nsfw/output appears on the world-scoped nsfw
    # page: the PNG's `prompt` tEXt chunk is the source of truth, so
    # `index --rebuild` pulls it into feed.sqlite and /w/nsfw/ shows it. The
    # sfw page stays empty — one server, world-scoped routes (GN22).
    machine.succeed(
        "printf '%s' 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAonRFWHRwcm9tcHQAeyIzIjogeyJjbGFzc190eXBlIjogIktTYW1wbGVyIiwgImlucHV0cyI6IHsic2VlZCI6IDcsICJwb3NpdGl2ZSI6IFsiNiIsIDBdfX0sICI2IjogeyJjbGFzc190eXBlIjogIkNMSVBUZXh0RW5jb2RlIiwgImlucHV0cyI6IHsidGV4dCI6ICJ2bSBwcm9tcHQgdGV4dCJ9fX1YBXILAAAAAElFTkSuQmCC' "
        "| base64 -d > /home/alice/comfyui/worlds/nsfw/output/vmtest.png"
    )
    machine.succeed(
        "runuser -u alice -- comfy-feed index --rebuild "
        "--world nsfw --root /home/alice/comfyui"
    )
    machine.wait_until_succeeds(
        "curl -fsS http://127.0.0.1:8288/w/nsfw/ | grep -q 'vm prompt text'",
        timeout=60,
    )
    machine.succeed(
        "curl -fsS http://127.0.0.1:8288/w/sfw/ | grep -q 'no renders yet'"
    )

    # (5b) the like verb: POST /w/nsfw/like upserts one likes row for
    # vmtest.png (the name exists in renders from step 5's rebuild, so it is
    # accepted; a second like is idempotent).
    machine.succeed("curl -fsS -X POST -d name=vmtest.png http://127.0.0.1:8288/w/nsfw/like")
    machine.succeed("curl -fsS -X POST -d name=vmtest.png http://127.0.0.1:8288/w/nsfw/like")
    like_count = machine.succeed(
        "runuser -u alice -- sqlite3 /home/alice/comfyui/worlds/nsfw/feed.sqlite"
        " 'select count(*) from likes'"
    ).strip()
    assert like_count == "1", f"likes count: {like_count!r}"

    # (5c) the packaged feed, exercised end-to-end on POST: /w/nsfw/regenerate
    # against the systemd-started comfy-feed.service (the packaged unit, not
    # the source tree) must answer a 303 redirect — with the FEED_QUEUE_PY
    # seam missing this resets the connection — and /w/nsfw/jobs then lists
    # the row.
    machine.succeed(
        "curl -fsS -X POST -d name=vmtest.png http://127.0.0.1:8288/w/nsfw/regenerate"
    )
    machine.succeed("curl -fsS http://127.0.0.1:8288/w/nsfw/jobs | grep -q regenerate")

    # (6) GN26 — the LAN face is services.lan-access's: ONE site
    # (worlds.core.local) fronting the ONE feed, ONE credential. 401 without
    # it, 200 + the feed shell with it, a wrong password refused (bcrypt
    # fails closed).
    worlds_code = machine.succeed(
        "curl -k -s -o /dev/null -w '%{http_code}' https://worlds.core.local/"
    ).strip()
    assert worlds_code == "401", f"worlds without creds answered {worlds_code}"
    # `/` is the world redirect, so the site's page is fetched at its
    # world-scoped path; a redirect-following GET on `/` lands on the ACTIVE
    # world's page (nsfw, started in step 3) — the feed shell served through
    # Caddy.
    sfw_body = machine.succeed("curl -k -s --user alice:test-worlds https://worlds.core.local/w/sfw/")
    assert "sfw" in sfw_body, f"sfw body missing world name: {sfw_body!r}"
    root_body = machine.succeed("curl -k -sL --user alice:test-worlds https://worlds.core.local/")
    assert "nsfw" in root_body, f"/ did not redirect to the active world: {root_body!r}"
    wrong_code = machine.succeed(
        "curl -k -s -o /dev/null -w '%{http_code}' --user alice:wrong-password "
        "https://worlds.core.local/w/sfw/"
    ).strip()
    assert wrong_code == "401", f"wrong password answered {wrong_code}"

    # (7) listeners and firewall: Caddy answers the :80 redirect beside :443
    # (lanAccess.nix leaves auto_https untouched; the worlds module's hostwide
    # disable_redirects died with its Caddy block), the world ports and the
    # one feed port bound to 127.0.0.1 only, 80+443 opened on eth1 only.
    # (sorted() orders "*:443" before "*:80" — '4' sorts before '8'.)
    ss_out = machine.succeed("ss -ltnH")
    listeners = sorted(line.split()[3] for line in ss_out.strip().splitlines())
    non_loopback = [a for a in listeners if not a.startswith(("127.", "[::1]"))]
    assert non_loopback == ["*:443", "*:80"], f"unexpected non-loopback listeners: {non_loopback}"
    for port in ("8188", "8189", "8288"):
        assert not any(a.endswith(":" + port) and not a.startswith("127.") for a in listeners), listeners
    rules = machine.succeed("nft list ruleset")
    assert 'iifname "eth1"' in rules and "80" in rules and "443" in rules, rules
    machine.fail("nft list ruleset | grep -qE '^ *tcp dport (80|443) accept$'")

    # (8) with the guard broken (lab repo gone), starting sfw's generator
    # fails and the journal names comfy-worlds-init.
    machine.succeed("runuser -u alice -- rm -rf /home/alice/comfyui/worlds/sfw/lab/.git")
    machine.fail("systemctl --user -M alice@ start comfyui-sfw")
    machine.wait_until_succeeds(
        "journalctl --no-pager -b | grep -q 'comfy-worlds-init'",
        timeout=60,
    )

    # (9) the missing-hash face: with the bcrypt file gone, caddy refuses to
    # load the config with an error naming the file and the unit ends up
    # down (exit 1, RestartPreventExitStatus=1 — no respin), then starts
    # and answers again once the file is back. NOTE: caddy sends READY=1
    # before provisioning the http app (the admin endpoint comes up first),
    # so `systemctl restart` itself returns 0 — the refusal is the load
    # error + the dead unit, both asserted (measured at this pin; caddy
    # run's exit 1 was re-measured on the host caddy 2.11.4 too).
    machine.succeed(
        "mv /var/lib/lan-access/worlds.bcrypt /var/lib/lan-access/worlds.bcrypt.moved"
    )
    machine.succeed("systemctl restart caddy.service")
    machine.wait_until_fails("systemctl is-active caddy.service", timeout=60)
    machine.wait_until_succeeds(
        "journalctl --no-pager -b -u caddy | grep -q 'placeholder: failed to read file'"
        " && journalctl --no-pager -b -u caddy | grep -q '/var/lib/lan-access/worlds.bcrypt'",
        timeout=60,
    )
    machine.succeed(
        "mv /var/lib/lan-access/worlds.bcrypt.moved /var/lib/lan-access/worlds.bcrypt"
    )
    machine.succeed("systemctl start caddy.service")
    machine.wait_until_succeeds(
        "curl -k -s -o /dev/null -w '%{http_code}' --user alice:test-worlds "
        "https://worlds.core.local/w/sfw/ | grep -qx 200",
        timeout=60,
    )

    # (10) GN14 — the local model unit, on real systemd, against the nsfw
    # generator that step (3) left active. (i) write the fixture GGUF with
    # the digest the module config declares; (ii) make sure the generator is
    # up; (iii) starting the model STOPS the renderer (Conflicts=, one
    # direction); (iv) starting the renderer STOPS the model (the reverse
    # direction); (v) a corrupted file makes the model unit's start fail
    # with the guard's line; (vi) probe 1's fallback: the user manager
    # cannot attach the address-filter BPF program, so IPAddressDeny is
    # deliberately omitted and this pins the omitted state.
    machine.succeed(
        "mkdir -p /home/alice/models && printf 'not a real gguf' "
        "> /home/alice/models/fake.gguf && chown -R alice /home/alice/models"
    )
    machine.succeed("systemctl --user -M alice@ start comfy-world-nsfw.target")
    machine.wait_until_succeeds("curl -fsS http://127.0.0.1:8189/system_stats", timeout=600)

    # (iii) model start stops the renderer.
    machine.succeed("systemctl --user -M alice@ start comfy-author-model.service")
    machine.wait_until_succeeds(
        'test "$(systemctl --user -M alice@ is-active comfyui-nsfw)" = inactive',
        timeout=60,
    )
    machine.wait_until_succeeds(
        "journalctl --no-pager -b | grep -q 'Stopped ComfyUI generator for world nsfw'",
        timeout=60,
    )
    machine.wait_until_succeeds(
        'test "$(systemctl --user -M alice@ is-active comfy-author-model)" = active',
        timeout=60,
    )

    # (iv) the reverse direction: the renderer start stops the model.
    machine.succeed("systemctl --user -M alice@ start comfy-world-nsfw.target")
    machine.wait_until_succeeds(
        'test "$(systemctl --user -M alice@ is-active comfy-author-model)" = inactive',
        timeout=60,
    )
    machine.wait_until_succeeds("curl -fsS http://127.0.0.1:8189/system_stats", timeout=600)

    # (v) corrupt the file; the guard refuses the restart by name.
    machine.succeed("printf 'corrupted' > /home/alice/models/fake.gguf")
    machine.fail("systemctl --user -M alice@ restart comfy-author-model.service")
    machine.wait_until_succeeds(
        "journalctl --no-pager -b | grep -q 'local-model: model digest mismatch for /home/alice/models/fake.gguf'",
        timeout=60,
    )
    machine.succeed("printf 'not a real gguf' > /home/alice/models/fake.gguf")

    # (vi) probe 1's recorded fallback: IPAddressDeny is omitted (a user
    # unit's address filter is a silent no-op -- "unit configures an IP
    # firewall, but not running as root"; measured on this pin's test VM).
    # `show -p IPAddressDeny` answers an empty value, and the model unit's
    # journal carries no IP-firewall warning. The no-egress property rests
    # on the loopback bind (asserted by local-model-eval and assertion (d)).
    ipdeny = machine.succeed(
        "systemctl --user -M alice@ show comfy-author-model -p IPAddressDeny"
    ).strip()
    assert ipdeny in ("IPAddressDeny=", ""), (
        f"IPAddressDeny must be omitted (probe-1 fallback), got: {ipdeny!r}"
    )
    firewall_warnings = machine.succeed(
        "journalctl --no-pager -b -u comfy-author-model | grep -i 'IP firewall' || true"
    ).strip()
    assert firewall_warnings == "", (
        f"the model unit must carry no address-filter directives: {firewall_warnings!r}"
    )

    # (11) GN52 — the card tool's offline arm by hand (cards.enable stays
    # off in this VM: no broker instance here, so the network arm's unit is
    # comfy-worlds-eval's cCards proof). A real safetensors fixture — the
    # 8-byte little-endian header length, the JSON header carrying the
    # single-token modelspec.title, the two data bytes the offsets name —
    # behind a [[model]] row: comfy-cards reads the header, decides the
    # trigger, writes it into lab/manifest.toml and the sidecar under
    # lab/cards/.
    machine.succeed(
        "runuser -u alice -- mkdir -p /home/alice/comfyui/worlds/nsfw/models/loras"
    )
    machine.succeed(
        "runuser -u alice -- python3 -c "
        "\"import json,struct,sys; "
        "h=json.dumps({'__metadata__': {'modelspec.title': 'n3lson,'}, "
        "'w': {'dtype':'F16','shape':[1],'data_offsets':[0,2]}}).encode(); "
        "open(sys.argv[1],'wb').write(struct.pack('<Q', len(h))+h+b'\\x00\\x00')\" "
        "/home/alice/comfyui/worlds/nsfw/models/loras/fixture.safetensors"
    )
    machine.succeed(
        "printf '[[model]]\\nname = \"fixture\"\\ndest = \"loras/fixture.safetensors\"\\n"
        "enabled = true\\nsha256 = \"0000000000000000000000000000000000000000000000000000000000000000\"\\n'"
        " >> /home/alice/comfyui/worlds/nsfw/lab/manifest.toml"
    )
    machine.succeed("runuser -u alice -- comfy-cards --world nsfw --root /home/alice/comfyui")
    machine.succeed(
        'grep -q \'trigger = "n3lson,"\' /home/alice/comfyui/worlds/nsfw/lab/manifest.toml'
    )
    machine.succeed("test -f /home/alice/comfyui/worlds/nsfw/lab/cards/fixture.json")
  '';
}
