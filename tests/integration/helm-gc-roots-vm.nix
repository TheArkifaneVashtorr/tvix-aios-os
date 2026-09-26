{
  pkgs,
  helmModule,
}:
let
  # The v0 test's fake basket (tests/integration/helm-vm.nix): a stub
  # whose doctor output feeds the basket-doctor tile without touching
  # real hardware. Inlined byte-for-byte so this section is self-contained.
  fakeBasket = pkgs.writeShellScriptBin "basket" ''
    echo "PASS swap        no swap devices"
    echo "WARN vsock       module absent in VM"
  '';

  # Build-time-only fixtures, same shape as the bug: checkX's OUTPUT never
  # references btX (the `cat` is consumed, not embedded), so btX is a
  # build-time-only dependency exactly as nixpkgs' stdenv paths are
  # build-time-only dependencies of a real check.
  mkBt = name: pkgs.runCommand "helm-gc-roots-bt-${name}" { } "echo ${name} > $out";
  mkCheck =
    name: bt:
    pkgs.runCommand "helm-gc-roots-check-${name}" { } ''
      cat ${bt} >/dev/null   # a build input of the derivation; never appears in $out
      touch $out
    '';
  btA = mkBt "a";
  btB = mkBt "b";
  btC = mkBt "c";
  btD = mkBt "d";
  btE = mkBt "e";
  btF = mkBt "f";
  btNeg = mkBt "neg";
  checkA = mkCheck "a" btA;
  checkB = mkCheck "b" btB;
  checkC = mkCheck "c" btC;
  checkD = mkCheck "d" btD;
  checkE = mkCheck "e" btE;
  checkF = mkCheck "f" btF;
  checkNeg = mkCheck "neg" btNeg;

  # M7's fixture pair. checkBad's own output is never rooted by any arm
  # (it is deliberately absent from every rooting call below), so by the
  # time the M7 arm runs -- after Night 4's zero-path flip and four
  # `nix-collect-garbage` calls -- the collection has taken both checkBad's
  # output and the build-time stdenv outputs sitting in its .drv's closure
  # (a .drv's store-DB references are its input .drv FILES and input
  # SOURCES, never the outputs of its input derivations, so those outputs
  # ride only in the registration and die unrooted). Filtered, rooting
  # checkBad's closure is then a harmless no-op: --include-outputs lists
  # only currently-valid outputs, so nothing dead is ever realised. Step 6
  # removes the `.drv` filter and rebuilds this check: unfiltered, the
  # closure's .drv paths reach --realise directly, and realising a .drv
  # whose output is gone forces the daemon to REBUILD the whole build-time
  # closure offline (stdenv, bootstrap chain and all) -- exactly the
  # offline-fatal class of build the filter exists to avoid -- which fails
  # or times out inside the VM and turns this exact line red.
  #
  # (The plan's original fixture was an `exit 1` builder, which can never
  # ride in virtualisation.additionalPaths: regInfo's closureInfo
  # (exportReferencesGraph) BUILDS the outputs of every .drv root it is
  # handed, so an unbuildable output turns the whole check red at
  # flake-build time, before any VM boots. Everything here is therefore
  # host-buildable, and the offline-fatal rebuild comes from the
  # post-collection store state instead.)
  btBad = mkBt "bad";
  checkBad = mkCheck "bad" btBad;

  # A tiny, self-contained, zero-inputs flake (no `inputs = { }`, so
  # evaluating and building it needs no network at all) that stands in
  # for the real repo's own `flake.nix` for Interface 2's end-to-end
  # wiring proof: `helm-flake-check.service` is started for real, against
  # this flake, inside the VM.
  fixtureFlakeOk = pkgs.writeText "gc-roots-fixture-flake-ok.nix" ''
    {
      outputs = _: {
        checks.x86_64-linux.gcRootsFixture = derivation {
          name = "gc-roots-fixture-check";
          system = "x86_64-linux";
          builder = "/bin/sh";
          args = [ "-c" "echo ok > $out" ];
        };
      };
    }
  '';
  # Deliberately invalid Nix -- makes `nix flake check`/`nix eval` fail at
  # evaluation, for the "eval failure keeps yesterday's roots" arm.
  fixtureFlakeBroken = pkgs.writeText "gc-roots-fixture-flake-broken.nix" ''
    { this is not valid nix
  '';
in
pkgs.testers.runNixOSTest {
  name = "helm-gc-roots";
  nodes.machine =
    { pkgs, ... }:
    {
      imports = [ helmModule ];
      users.users.alice = {
        isNormalUser = true;
        uid = 1000;
      };
      services.helm = {
        enable = true;
        operatorUser = "alice";
        repo = "/var/lib/fake-repo";
        basketPackage = fakeBasket;
        restic.repository = "/var/lib/no-such-repo";
        restic.passwordFile = "/etc/no-such-file";
        flakeCheck.enable = true;
        timers.system = [ ];
        timers.user = [ ];
        brokerInstances = [ ];
        api.enable = false;
      };
      # git: the testScript's own `su alice -c 'git …'` fixture-repo setup
      # runs on the general system PATH, not flakeCheck's own wrapped one
      # (helm-vm.nix:33-37 carries the same package for the same reason).
      # experimental-features: the helm module itself never sets this
      # (`grep experimental-features nixosModules/helm.nix` finds
      # nothing) -- core's own host config does, but this minimal VM only
      # imports helmModule, so `nix flake check`/`nix eval` inside the
      # service would refuse "flakes"/"nix-command" without it (same
      # fix tests/integration/fleet-vm.nix:118-125 already uses).
      environment.systemPackages = [ pkgs.git ];
      nix.settings.experimental-features = [
        "nix-command"
        "flakes"
      ];
      # The NixOS test VM shares the HOST's /nix/store read-only over 9p
      # by default (qemu-vm.nix: mountHostNixStore defaults true), so a
      # plain `nix-collect-garbage` could never delete anything (EROFS)
      # and the service arm's `nix flake check` could never build. The
      # writable-store overlay gives the VM a deletable store view:
      # GC deletions work as whiteouts, builds land in the upper layer.
      # register-nix-paths still load-dbs the additionalPaths closure into
      # the VM's own Nix DB at boot, which is what makes every fixture
      # below valid-but-unrooted at boot (every other host path is
      # visible via 9p but unregistered, i.e. garbage by definition --
      # the additionalPaths option's own documentation).
      virtualisation.writableStore = true;
      virtualisation.additionalPaths = [
        checkA
        checkB
        checkC
        checkD
        checkE
        checkF
        checkNeg
        checkA.drvPath
        checkB.drvPath
        checkC.drvPath
        checkD.drvPath
        checkE.drvPath
        checkF.drvPath
        checkNeg.drvPath
        btA
        btB
        btC
        btD
        btE
        btF
        btNeg
        checkBad.drvPath
        btBad.drvPath # M7's arm: registered at boot, never rooted
        fixtureFlakeOk
        fixtureFlakeBroken
      ];
    };
  testScript = ''
    machine.wait_for_unit("multi-user.target")
    machine.succeed("test -e ${checkA}", "test -e ${checkNeg}")   # additionalPaths landed

    # Test scaffolding (not the contract under test), all created before
    # the first collection:
    # 1. The service arm at the very end copies both fixture flakes into
    #    /var/lib/fake-repo, long after four `nix-collect-garbage` runs
    #    have swept every unrooted path. Pin both fixture files with
    #    their own plain indirect GC root (outside rootClosure's
    #    generations mechanism, so no generation flip can ever release
    #    them).
    # 2. The registration that load-dbs additionalPaths into the VM's
    #    Nix DB carries no deriver field (measured: registration lines
    #    are path/narHash/narSize/refs), so gc-keep-derivations has
    #    nothing to keep: the first collection takes every fixture .drv
    #    that is not itself rooted. Nightly rootClosure arguments must
    #    stay VALID across collections, so pin exactly the .drvs later
    #    arms pass as arguments (A/E/F for Nights 2-3, checkBad for the
    #    M7 arm) with direct gcroots symlinks. This keeps each pinned
    #    .drv FILE (and what it references) alive; the .drvs' OUTPUTS
    #    stay unrooted and die on schedule, which is the point.
    machine.succeed(
        "nix-store --add-root /var/lib/helm/gc-roots-vm-fixture-flakes "
        "--realise ${fixtureFlakeOk} ${fixtureFlakeBroken}",
        "mkdir -p /nix/var/nix/gcroots/auto "
        "&& for d in ${checkA.drvPath} ${checkE.drvPath} ${checkF.drvPath} ${checkBad.drvPath}; do "
        "ln -sfn $d /nix/var/nix/gcroots/auto/gc-roots-vm-$(basename $d); done",
    )

    # --- Night 1: root every fixture meant to survive at least one arm.
    # checkNeg is deliberately excluded -- it is never rooted, ever. ---
    machine.succeed(
        "helm-flake-check-root /var/lib/helm/flake-check-roots "
        "${checkA.drvPath} ${checkB.drvPath} ${checkC.drvPath} "
        "${checkD.drvPath} ${checkE.drvPath} ${checkF.drvPath}"
    )
    machine.succeed("nix-collect-garbage")
    machine.succeed(
        "test -e ${checkA}", "test -e ${checkB}", "test -e ${checkC}",
        "test -e ${checkD}", "test -e ${checkE}", "test -e ${checkF}",
    )   # every rooted fixture survived the very first collection
    machine.fail("test -e ${checkNeg}")   # negative: never rooted, a plain collection takes it

    # --- Night 2: drop B, C, D -- keep A, E, F (D2's core property). ---
    machine.succeed(
        "helm-flake-check-root /var/lib/helm/flake-check-roots "
        "${checkA.drvPath} ${checkE.drvPath} ${checkF.drvPath}"
    )
    machine.succeed("nix-collect-garbage")
    machine.succeed("test -e ${checkA}", "test -e ${checkE}", "test -e ${checkF}")
    machine.fail("test -e ${checkB}")
    machine.fail("test -e ${checkC}")
    machine.fail("test -e ${checkD}")   # yesterday's roots released, not kept forever

    # --- One bad path in the batch makes the call FAIL overall, but the
    # flip still happens and the batch's valid member still gets rooted
    # -- D2's guarantee applies to a broken run's pins too. A and E are
    # deliberately left out of this call too, so their release is also
    # re-proved here. ---
    machine.fail(
        "helm-flake-check-root /var/lib/helm/flake-check-roots "
        "/nix/store/00000000000000000000000000000000-does-not-exist "
        "${checkF.drvPath}"
    )
    machine.succeed("nix-collect-garbage")
    machine.fail("test -e ${checkA}")
    machine.fail("test -e ${checkE}")
    machine.succeed("test -e ${checkF}")   # the batch's valid member still got rooted

    # --- A successful run with ZERO paths still flips onto an empty
    # generation, releasing even the last surviving root. ---
    machine.succeed("helm-flake-check-root /var/lib/helm/flake-check-roots")
    machine.succeed("nix-collect-garbage")
    machine.fail("test -e ${checkF}")   # the sole survivor above is now gone too

    # --- A stale "generations/<pid>" left by a run that crashed before
    # its own flip is swept on the next call, not left forever. ---
    machine.succeed(
        "mkdir -p /var/lib/helm/flake-check-roots/generations/99999 "
        "&& touch /var/lib/helm/flake-check-roots/generations/99999/stale"
    )
    machine.succeed("helm-flake-check-root /var/lib/helm/flake-check-roots")
    machine.fail("test -e /var/lib/helm/flake-check-roots/generations/99999")

    # --- M7's discriminator: the `.drv` filter is the bug-fixing line,
    # so it gets a standing behavioural test of its own. By now the four
    # collections above have taken checkBad's own output and the
    # build-time stdenv outputs in its closure (see the fixture comment),
    # while the gcroots scaffolding pin keeps checkBad.drv itself valid.
    # Filtered (today's code), rooting checkBad's closure is a harmless
    # no-op: --include-outputs lists only currently-valid outputs, so
    # nothing dead is ever realised. Step 6 removes the `.drv` filter and
    # rebuilds this check: unfiltered, the closure's .drv paths reach
    # --realise directly and force offline rebuilds of the whole
    # build-time closure, turning this exact line red. ---
    machine.succeed("helm-flake-check-root /var/lib/helm/flake-check-roots ${checkBad.drvPath}")

    # --- The real wiring, exercised behaviourally through the actual user
    # service, not just Interface 4's text-presence grep. A fresh roots
    # directory first, so a populated "current" below can only be this
    # service run's own doing, never a leftover from a direct call
    # above. ---
    machine.succeed("rm -rf /var/lib/helm/flake-check-roots")
    machine.succeed("mkdir -p /var/lib/fake-repo && chown alice /var/lib/fake-repo")
    machine.succeed("su alice -c 'cd /var/lib/fake-repo && git init -q && git -c user.email=a@b -c user.name=a commit -q --allow-empty -m init'")
    machine.succeed("cp ${fixtureFlakeOk} /var/lib/fake-repo/flake.nix")
    machine.succeed("chown alice /var/lib/fake-repo/flake.nix")
    machine.succeed("su alice -c 'cd /var/lib/fake-repo && git add flake.nix && git -c user.email=a@b -c user.name=a commit -q -m fixture-ok'")
    machine.succeed("loginctl enable-linger alice")
    # The unit's ReadWritePaths carries helm.nix's dash-prefixed
    # "-%h/.cache/nix" (tolerate-if-missing): the home cache is writable
    # only when it already exists at unit start. On core the operator's
    # own ~/.cache/nix is what makes that entry bite; a fresh VM user has
    # no ~/.cache at all, so without this line nix's fetcher cache (the
    # first write of even `nix eval` on the git+file repo) dies on the
    # read-only home ProtectHome gives it. Test scaffolding, matching the
    # state the real unit runs in.
    machine.succeed("su alice -c 'mkdir -p /home/alice/.cache/nix'")
    machine.wait_until_succeeds("systemctl --user -M alice@ is-active timers.target")
    machine.succeed("systemctl --user -M alice@ start helm-flake-check.service")
    machine.succeed("test -e /var/lib/helm/flake-check.json")   # flakeCheck itself ran
    machine.succeed("test ! -e /var/lib/helm/flake-check-roots.err")   # rooting reported no failure
    machine.succeed("test -L /var/lib/helm/flake-check-roots/current")   # only this run could have created it (dir was removed above)
    # trailing slash: GNU find without -H/-L does not follow a
    # command-line symlink, so `find .../current` would list nothing.
    machine.succeed("find /var/lib/helm/flake-check-roots/current/ -maxdepth 1 -name 'root-*' | grep -q .")   # something got rooted
    gen_before = machine.succeed("readlink /var/lib/helm/flake-check-roots/current").strip()

    # --- A broken flake (eval failure) KEEPS yesterday's roots -- the
    # generation from the successful run above is untouched: same
    # generation name (the stamp a leftover-roots false pass could not
    # fake), not merely "some root-* files still exist". ---
    machine.succeed("cp ${fixtureFlakeBroken} /var/lib/fake-repo/flake.nix")
    machine.succeed("chown alice /var/lib/fake-repo/flake.nix")
    machine.succeed("su alice -c 'cd /var/lib/fake-repo && git add flake.nix && git -c user.email=a@b -c user.name=a commit -q -m fixture-broken'")
    machine.succeed("systemctl --user -M alice@ start helm-flake-check.service")
    machine.succeed("test -e /var/lib/helm/flake-check-roots.eval.err")   # the enumeration failure is visible, correctly named
    machine.fail("test -e /var/lib/helm/flake-check-roots.err")   # this run never reached the rooting call at all
    gen_after = machine.succeed("readlink /var/lib/helm/flake-check-roots/current").strip()
    assert gen_before == gen_after, f"eval failure must keep yesterday's generation: {gen_before!r} != {gen_after!r}"
  '';
}
