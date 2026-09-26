{
  pkgs,
  lib,
  self,
  nixpkgs,
  system,
}:
let
  lintTools = with pkgs; [
    treefmt
    nixfmt-rfc-style
    shfmt
    shellcheck
    statix
    deadnix
    ruff
    # GN25: the deck client's two new languages (G10 — a new language
    # lands its formatter and linter in the same task as the assets).
    # prettier formats and format-checks the .js/.mjs/.css assets through
    # media/treefmt.toml's js+css blocks and the sweep below; oxlint
    # lints the JavaScript (it parses no css — Decision 15: css gets
    # format-checking only).
    prettier
    oxlint
  ];
  # Task 2 adds pytest-driven checks against pkgs/media-fetch; the
  # package set lands here now so the devShell and later checks share
  # one definition. GN21 adds pytest-timeout so comfy-worlds-unit's
  # --timeout=120 can turn a test that waits forever into a failure
  # instead of a hang (the guard against a retry loop that ignores its
  # own deadline).
  pyEnv = pkgs.python3.withPackages (ps: [
    ps.pytest
    ps.pytest-timeout
  ]);
  # Parametrised over the module so the eval checks can target either
  # nixosModules.default (services.comfyui) or nixosModules.comfyui-worlds
  # (services.comfyui-worlds); `harness` hardcoded `self.nixosModules.default`
  # before W3, which a comfyui-worlds fixture could not evaluate.
  mkHarness = module: import ./checks/eval-harness.nix { inherit nixpkgs system module; };
  harness = mkHarness (import ./nixosModules/comfyui.nix);
  worldsHarness = mkHarness (import ./nixosModules/comfyui-worlds.nix);
  # GN14: the local-model module's own harness (no worlds module imported —
  # the module stands alone), and the harness that evaluates it BESIDE the
  # worlds module so assertion (c) and the derived conflicts list read real
  # worlds config. eval-harness.nix takes exactly one `module` argument and
  # lib.evalModules rejects a nested modules list at this pin, so the
  # worlds module is layered through the extra module's own `imports` key
  # instead — no shared-harness signature change for one check.
  localModelHarness = mkHarness (import ./nixosModules/local-model.nix);
  lmWorldsHarness =
    extra: localModelHarness ({ imports = [ (import ./nixosModules/comfyui-worlds.nix) ]; } // extra);
  # A NixOS assertion (module `assertions = [...]`) is only surfaced when
  # something forces `config.system.build.toplevel` — evaluating it walks
  # every module's `assertions`/`warnings` and throws on a failed one.
  # mkNegative proves an assertion actually fires — not just that *some*
  # error occurred. Accepting any eval failure (an earlier version) made
  # comfyui-assertion-negative-broker pass on an unrelated raw "attribute
  # missing"/"has no value defined" error, staying green even if the
  # module's own assertion were deleted outright — a tautology. So this
  # requires BOTH: (1) forcing the toplevel drvPath throws (the outer,
  # "did the build actually fail" gate), and (2) forcing
  # `config.assertions` through the SAME recipe NixOS's own
  # nixos/modules/system/activation/top-level.nix uses to build
  # `failedAssertions` —
  #   map (x: x.message) (filter (x: !x.assertion) config.assertions)
  # — produces a message containing `expect`.
  #
  # Gate (2) deliberately uses `lib.filter`, not `lib.any`: `filter`
  # forces EVERY entry's `assertion` field to decide the filtered list
  # (same as top-level.nix), whereas `any` short-circuits on the first
  # match. A module bug once let a LATER assertion's own `assertion`
  # field force a value that has no definition for a bad brokerInstance
  # (nixosModules/comfyui.nix's now-fixed, guarded listenAddress
  # assertion): forcing toplevel died on that raw error before ever
  # producing the formatted "Failed assertions:" text an operator would
  # see, but `lib.any` here found assertion #1's own matching message
  # first and returned before ever forcing the broken one — so this
  # check stayed green by evaluation-order accident, proving nothing
  # about what forcing toplevel actually threw. Using `filter` forces
  # the exact same thunks in the exact same way top-level.nix does, so
  # `failedMessages.success` here is genuine evidence the friendly
  # message text is what an operator sees, not an artifact of this
  # check's own traversal order; `failedMessages.success == false`
  # means forcing config.assertions itself threw a raw, non-assertion
  # error — the same failure class the bug above produced — and is
  # reported as its own distinct failure rather than folded into "no
  # matching message".
  # mkNegativeWith is mkNegative parametrised over which harness (and thus
  # which module) it evaluates; mkNegative keeps the pre-W3 five checks
  # against services.comfyui unchanged, while the W3 comfyui-worlds
  # negatives use `mkNegativeWith worldsHarness`.
  mkNegativeWith =
    h: name: extra: expect:
    let
      result = h extra;
      toplevel = builtins.tryEval result.config.system.build.toplevel.drvPath;
      failedMessages = builtins.tryEval (
        map (a: a.message) (lib.filter (a: !a.assertion) result.config.assertions)
      );
    in
    if toplevel.success then
      throw "${name}: the build DID NOT FAIL (${expect})"
    else if !failedMessages.success then
      throw "${name}: the build failed, but forcing config.assertions via top-level.nix's own filter+map recipe ALSO threw a raw (non-assertion) error — the friendly '${expect}' message was never produced, so it is not what an operator running this configuration would actually see"
    else if !(lib.any (lib.hasInfix expect) failedMessages.value) then
      throw "${name}: the build failed with real assertion messages ${
        lib.generators.toPretty { } failedMessages.value
      }, but none contains '${expect}'"
    else
      pkgs.runCommand "${name}-ok" { } "touch $out";
  mkNegative = mkNegativeWith harness;
  hfTokenFile = "/var/lib/secrets/hf";
  mediaFetchModels = pkgs.writeShellApplication {
    name = "media-fetch-models";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 ${./pkgs/media-fetch/fetch.py} "$@"
    '';
  };
  # ComfyUI v0.34.5, packaged nix-native against the host's own
  # nixpkgs (torch-bin cu128 override + hash-pinned wheels, av 17.0.1
  # against FFmpeg 8.1.2) — see
  # pkgs/comfyui/package.nix for the tag/hash record and the
  # verify-first-0 route audit.
  comfyui = import ./pkgs/comfyui/package.nix { inherit pkgs; };
  # The comfyui-worlds derivations: shared verbatim between this flake (as
  # re-exports below) and the W3 module, which imports this same file with
  # the consuming host's pkgs — never self.packages.
  worldsPkgs = import ./pkgs/comfy-worlds { inherit pkgs; };
in
{
  # Proof that packageOverrides actually won: `torch.version.cuda`
  # is `null` on the pin's own source torch (CPU-only there) and
  # "12.8" only on torch-bin — so this fails loudly if a dependent
  # ever pulls in the source torch instead (two `torch`s would
  # otherwise silently collide on site-packages/torch and whichever
  # wins decides this). `--help` runs before any heavy import
  # (comfy/cli_args.py parses argv at module import time, and
  # argparse's own `--help` raises SystemExit(0) before anything
  # after that import runs — confirmed by reading main.py at this
  # rev), so this needs no GPU and stays fast in the build sandbox.
  #
  # Getting `comfy.model_management` to import cleanly without a GPU
  # took two real fixes, found by actually running this, not by
  # reading the source alone:
  #   1. That module runs `total_vram = get_total_memory(
  #      get_torch_device()) / ...` at plain module-import time
  #      (comfy/model_management.py:254), and `get_torch_device()`
  #      calls `torch.cuda.current_device()` unless `args.cpu` was
  #      set — first attempt (the plan's literal
  #      `import comfy.model_management` with no argv) failed here
  #      with "RuntimeError: Found no NVIDIA driver on your
  #      system".
  #   2. Setting `sys.argv = ["comfyui", "--cpu"]` alone still
  #      wasn't enough and failed the same way: `comfy/cli_args.py`
  #      only calls `parser.parse_args()` (reading real argv) when
  #      `comfy.options.args_parsing` is true — otherwise (its
  #      default) it parses `[]` and every flag, `--cpu` included,
  #      stays at its default regardless of argv. `main.py` itself
  #      calls `comfy.options.enable_args_parsing()` before ever
  #      importing `comfy.cli_args`; this check must do the same,
  #      in the same order, before `comfy.model_management` pulls
  #      `comfy.cli_args` in transitively.
  # Mirrors exactly how services.comfyui's real unit invokes `--cpu`
  # when `gpu.enable = false` (not an invented flag) — this stays
  # proof of nothing but the CPU path; GPU behaviour is
  # unverifiable in this sandbox by construction and is the VM
  # check's job (Task 3).
  comfyui-package =
    pkgs.runCommand "comfyui-package"
      {
        nativeBuildInputs = [ comfyui ];
      }
      ''
        comfyui --help | grep -q -- --disable-all-custom-nodes

        # The torch contract is `torch.version.cuda`, not the version string.
        # python.nix's header states the rule this check exists to prove: the
        # `-bin` override must win `site-packages/torch`, and the tell is that
        # the pin's source torch is CPU-only and reports cuda None. The exact
        # 12.8 is load-bearing too (sm_120, driver 570.195.03). The version
        # literal was not: source and `-bin` share it, so it discriminated
        # nothing, and it went stale unseen when the worlds moved torch to
        # 2.11 on 2026-09-17. It is recorded below, never asserted.
        #
        # The comparison is in python rather than a `| grep -q` so a mismatch
        # can say what it wanted and what it got: piping the print into grep
        # discarded both, and a failed build logged four unrelated CUDA
        # warnings and nothing else (measured 2026-09-21).
        ${comfyui.passthru.python}/bin/python3 -c '
        import sys
        sys.path.insert(0, "${comfyui.passthru.src}")
        import comfy.options
        comfy.options.enable_args_parsing()
        sys.argv = ["comfyui", "--cpu"]
        import torch
        import comfy.model_management  # noqa: F401 — proves the src imports against this env
        want = "12.8"
        got = torch.version.cuda
        print("comfyui-package: torch %s, cuda %s" % (torch.__version__, got))
        if got != want:
            sys.exit(
                "comfyui-package: torch.version.cuda is %r, want %r -- the source "
                "(CPU-only) torch reports None, so this means the -bin override "
                "stopped winning site-packages/torch" % (got, want)
            )
        '

        # aimdo.so guard (W1 gate minor, a): the compiled cp39-abi3
        # wheel must ship the native library — the py3-none-any fallback
        # wheel has no aimdo.so and would silently weaken the
        # memory/device helper while leaving every W1 check green.
        # comfy_aimdo is a PEP 420 namespace package (its wheel ships no
        # __init__.py), so __file__ is None — resolve the package dir via
        # find_spec(...).submodule_search_locations instead.
        ${comfyui.passthru.python}/bin/python3 -c '
        import importlib.util, pathlib, sys
        spec = importlib.util.find_spec("comfy_aimdo")
        locs = spec.submodule_search_locations if spec is not None else []
        ok = any((pathlib.Path(p) / "aimdo.so").exists() for p in locs)
        sys.exit(0 if ok else 1)
        '

        # Template-wheel guard (W1 gate minor, b): the seven sibling data
        # wheels must match comfyui-workflow-templates' own Requires-Dist
        # pins. A reverted sibling (e.g. -core 0.3.331) otherwise still
        # starts clean and would pass the startup check while breaking
        # the parent's resolution contract.
        ${comfyui.passthru.python}/bin/python3 -c '
        import importlib.metadata as md
        for req in md.requires("comfyui-workflow-templates") or []:
            if "==" not in req:
                continue
            name, _, want = req.partition("==")
            want = want.split(";")[0].strip()
            name = name.strip()
            if not name.startswith("comfyui-workflow-templates-"):
                continue
            got = md.version(name)
            if got != want:
                print("comfyui-package: template wheel %s is %s, parent pins %s" % (name, got, want))
                raise SystemExit(1)
        print("comfyui-package: template wheels match parent Requires-Dist")
        '

        touch $out
      '';
  # The native CLIPLoader node's `type` permits which text-encoder
  # architectures it will load. v0.22.3 predates the `krea2` type
  # (Comfy-Org/Krea-2's Qwen3-VL-based encoder); v0.34.3 adds it
  # (nodes.py CLIPLoader.INPUT_TYPES). Import the real node graph
  # (not the /object_info HTTP route — this runs in the build
  # sandbox with no GPU, exactly like comfyui-package) and assert
  # `krea2` is in the list, so a pin that can't load the Krea-2
  # text encoder fails this check instead of failing on the GPU.
  # Red-first: this check fails at 0.22.3 and goes green only after
  # the v0.34.3 pin lands.
  comfyui-cliploader-krea2 =
    pkgs.runCommand "comfyui-cliploader-krea2"
      {
        nativeBuildInputs = [ comfyui ];
      }
      ''
        ${comfyui.passthru.python}/bin/python3 -c '
        import sys
        sys.path.insert(0, "${comfyui.passthru.src}")
        import comfy.options
        comfy.options.enable_args_parsing()
        sys.argv = ["comfyui", "--cpu"]
        import nodes
        types = nodes.NODE_CLASS_MAPPINGS["CLIPLoader"].INPUT_TYPES()["required"]["type"][0]
        assert "krea2" in types, "CLIPLoader type does not contain krea2: %r" % (types,)
        print("CLIPLoader type:", types)
        '
        touch $out
      '';
  # W1 (2026-09-05-comfy-worlds): "functional" has a test. One CPU start
  # of the real package with --quick-test-for-ci; any import failure or
  # unlisted WARNING is red. checks/startup-allowlist.txt names the
  # lines that may remain and the claim that removes them.
  comfyui-startup-clean =
    pkgs.runCommand "comfyui-startup-clean"
      {
        nativeBuildInputs = [
          self.packages.${system}.comfyui
          pkgs.gnugrep
        ];
        allowlist = ./checks/startup-allowlist.txt;
      }
      ''
        export HOME=$TMPDIR
        mkdir -p base/custom_nodes base/models base/output base/input base/temp base/user
        set +e
        comfyui --cpu --quick-test-for-ci --base-directory "$PWD/base" --user-directory "$PWD/base/user" >startup.log 2>&1
        code=$?
        set -e
        # ANSI colour codes off, so the regexes see plain text.
        sed -e 's/\x1b\[[0-9;]*m//g' startup.log >plain.log
        test "$code" -eq 0 || { echo "comfyui-startup-clean: exit $code"; cat plain.log; exit 1; }
        for bad in 'Traceback' 'IMPORT FAILED' 'ModuleNotFoundError' 'ImportError' 'Please do a: pip install'; do
          if grep -F -q -- "$bad" plain.log; then echo "comfyui-startup-clean: forbidden line: $bad"; cat plain.log; exit 1; fi
        done
        # `grep -v` exits 1 when every line is filtered out, so a
        # comment-only allowlist would kill this under `set -e` with no
        # diagnostic. Each leg tolerates that so the empty regex file is
        # actually produced, and the per-WARNING loop below then refuses
        # on "WARNING not in the allowlist" instead of a silent exit.
        { grep -v '^#' "$allowlist" || true; } | { grep -v '^$' || true; } >allow.re
        grep -n 'WARNING' plain.log | sed 's/^[0-9]*://' | sed 's/^\[WARNING\] //' >warnings.txt || true
        while IFS= read -r line; do
          [ -n "$line" ] || continue
          if ! printf '%s\n' "$line" | grep -E -q -f allow.re; then
            echo "comfyui-startup-clean: WARNING not in the allowlist: $line"; exit 1
          fi
        done <warnings.txt
        for want in 'ComfyUI version: 0.34.5' 'comfy-aimdo version: 0.4.15' 'comfy-kitchen version: 0.2.31' 'comfyui-frontend-package version: 1.49.6' 'comfyui-workflow-templates version: 0.11.55' 'comfyui-embedded-docs version: 0.5.10'; do
          grep -F -q -- "$want" plain.log || { echo "comfyui-startup-clean: missing: $want"; exit 1; }
        done
        cp plain.log $out
      '';
  media-lint = pkgs.runCommand "lint" { nativeBuildInputs = lintTools; } ''
    cp -r ${self}/media src && chmod -R u+w src && cd src
    treefmt --ci --config-file treefmt.toml --tree-root .
    # GN25: the js/css gate reaches the copied tree by find (no git in the
    # sandbox) — prettier format-checks every .js/.mjs/.css under pkgs/
    # and tests/, oxlint lint-checks the JavaScript. Redundant with the
    # treefmt sweep above by design: the sweep is the formatter gate,
    # this is the linter gate (oxlint is no formatter) and the css arm's
    # own row (M4's mutant).
    find pkgs tests -type f \( -name '*.js' -o -name '*.mjs' -o -name '*.css' \) -print0 |
      xargs -0 --no-run-if-empty prettier --check
    find pkgs tests -type f \( -name '*.js' -o -name '*.mjs' \) -print0 |
      xargs -0 --no-run-if-empty oxlint --deny-warnings
    shellcheck githooks/pre-push githooks/pre-commit pkgs/comfy-worlds/init.sh pkgs/comfy-worlds/media-comfy.sh
    if [ -d tests ]; then
      find tests -name '*.sh' -print0 | xargs -0 --no-run-if-empty shellcheck
    fi
    statix check .
    deadnix --fail .
    ruff check .
    ruff format --check .
    touch $out
  '';
  comfyui-eval =
    let
      gpuOn =
        (harness {
          services.comfyui = {
            enable = true;
            models.hfTokenFile = hfTokenFile;
          };
        }).config;
      gpuOff =
        (harness {
          services.comfyui = {
            enable = true;
            models.hfTokenFile = hfTokenFile;
            gpu.enable = false;
          };
        }).config;
      svc = gpuOn.systemd.services.comfyui.serviceConfig;
      start = toString svc.ExecStart;
      env = gpuOn.systemd.services.comfyui.environment or { };
      envStr = lib.concatStringsSep " " (lib.mapAttrsToList (k: v: "${k}=${toString v}") env);
      has = s: lib.hasInfix s start;
      fetchSvc = gpuOn.systemd.services.comfyui-fetch-models.serviceConfig;
      fetchStart = toString fetchSvc.ExecStart;
      fetchEnv = gpuOn.systemd.services.comfyui-fetch-models.environment or { };
      # models.only scopes the fetch unit to the named manifest
      # entries (media-fetch-models --only, once per name).
      onlyOn =
        (harness {
          services.comfyui = {
            enable = true;
            models = {
              inherit hfTokenFile;
              only = [ "krea2-vae" ];
            };
          };
        }).config;
      onlyFetchStart = toString onlyOn.systemd.services.comfyui-fetch-models.serviceConfig.ExecStart;
      onlyTwo =
        (harness {
          services.comfyui = {
            enable = true;
            models = {
              inherit hfTokenFile;
              only = [
                "krea2-vae"
                "krea2-text-encoder"
              ];
            };
          };
        }).config;
      onlyTwoFetchStart = toString onlyTwo.systemd.services.comfyui-fetch-models.serviceConfig.ExecStart;
    in
    assert lib.assertMsg (has "--base-directory /var/lib/comfyui") "eval: --base-directory";
    assert lib.assertMsg (has "--listen 10.100.2.2") "eval: --listen must be the namespace address";
    assert lib.assertMsg (has "--port 8188") "eval: --port";
    assert lib.assertMsg (has "--disable-all-custom-nodes") "eval: --disable-all-custom-nodes";
    assert lib.assertMsg (!has "--cpu") "eval: gpu.enable=true must not pass --cpu";
    assert lib.assertMsg (
      svc.NetworkNamespacePath == "/run/netns/egress-media"
    ) "eval: unit not in the broker netns";
    assert lib.assertMsg (svc.User == "comfyui") "eval: not the comfyui user";
    assert lib.assertMsg (svc.ProtectSystem == "strict") "eval: ProtectSystem";
    assert lib.assertMsg svc.ProtectHome "eval: ProtectHome";
    assert lib.assertMsg (lib.elem "/var/lib/comfyui" svc.ReadWritePaths)
      "eval: ReadWritePaths dataDir";
    assert lib.assertMsg (lib.elem "/var/lib/comfyui/models" svc.ReadOnlyPaths)
      "eval: ReadOnlyPaths models";
    assert lib.assertMsg (lib.elem "/dev/shm" svc.InaccessiblePaths) "eval: InaccessiblePaths /dev/shm";
    assert lib.assertMsg
      (
        lib.elem "AF_UNIX" svc.RestrictAddressFamilies
        && lib.elem "AF_INET" svc.RestrictAddressFamilies
        && lib.elem "AF_INET6" svc.RestrictAddressFamilies
      )
      "eval: RestrictAddressFamilies must include AF_UNIX — libcuda opens an AF_UNIX socket at init; without AF_UNIX cudaGetDeviceCount fails with error 304 (measured on core 2026-09-15)";
    assert lib.assertMsg (svc.DevicePolicy == "closed") "eval: DevicePolicy";
    assert lib.assertMsg (
      svc.DeviceAllow == [
        "char-nvidiactl rw"
        "char-nvidia-frontend rw"
        "char-nvidia-uvm rw"
        "char-nvidia-caps rw"
      ]
    ) "eval: DeviceAllow (gpu.enable=true)";
    # The inference process needs no egress: offline by construction
    # (no HF/transformers network calls possible even though it shares
    # the broker's netns) — only the fetch unit still proxies.
    assert lib.assertMsg (env.HF_HUB_OFFLINE == "1") "eval: HF_HUB_OFFLINE";
    assert lib.assertMsg (env.TRANSFORMERS_OFFLINE == "1") "eval: TRANSFORMERS_OFFLINE";
    assert lib.assertMsg (env.HF_HUB_DISABLE_TELEMETRY == "1") "eval: HF_HUB_DISABLE_TELEMETRY";
    assert lib.assertMsg (!(env ? "HTTPS_PROXY")) "eval: comfyui.service must carry no HTTPS_PROXY";
    assert lib.assertMsg (!(env ? "HTTP_PROXY")) "eval: comfyui.service must carry no HTTP_PROXY";
    assert lib.assertMsg (
      fetchEnv ? "HTTPS_PROXY"
    ) "eval: comfyui-fetch-models must keep its own HTTPS_PROXY";
    assert lib.assertMsg (
      env.XDG_CACHE_HOME == "/var/lib/comfyui/cache"
    ) "eval: XDG_CACHE_HOME under dataDir";
    assert lib.assertMsg (
      !(lib.any (k: lib.hasInfix "TOKEN" k) (lib.attrNames env))
    ) "eval: no TOKEN key in the unit environment";
    assert lib.assertMsg (
      !(lib.hasInfix "TOKEN" envStr)
    ) "eval: no TOKEN value leaked into the unit environment";
    assert lib.assertMsg (lib.elem "127.0.0.1:8188" gpuOn.systemd.sockets.comfyui-proxy.listenStreams)
      "eval: proxy socket";
    assert lib.assertMsg (
      gpuOn.services.egress-broker.instances.media.inject ? "huggingface.co"
    ) "eval: inject key must be the host";
    assert lib.assertMsg (
      gpuOn.services.egress-broker.instances.media.inject."huggingface.co".valueFile == hfTokenFile
    ) "eval: inject valueFile";
    assert lib.assertMsg (!gpuOn.virtualisation.podman.enable) "eval: podman must be gone";
    assert lib.assertMsg (
      !gpuOn.hardware.nvidia-container-toolkit.enable
    ) "eval: nvidia-container-toolkit must be gone";
    assert lib.assertMsg (
      fetchSvc.NetworkNamespacePath == "/run/netns/egress-media"
    ) "eval: fetch unit not confined";
    assert lib.assertMsg (lib.hasInfix "--cafile" fetchStart) "eval: fetch unit --cafile";
    assert lib.assertMsg (lib.elem "/var/lib/comfyui/models" fetchSvc.ReadWritePaths)
      "eval: fetch unit ReadWritePaths models";
    # gpu.enable = false: --cpu present, no nvidia DeviceAllow.
    assert lib.assertMsg (lib.hasInfix "--cpu" (
      toString gpuOff.systemd.services.comfyui.serviceConfig.ExecStart
    )) "eval: gpu.enable=false must pass --cpu";
    assert lib.assertMsg (
      gpuOff.systemd.services.comfyui.serviceConfig.DeviceAllow == [ ]
    ) "eval: gpu.enable=false must not DeviceAllow any nvidia device";
    assert lib.assertMsg (
      !(lib.hasInfix "--only" fetchStart)
    ) "eval: default models.only ([ ]) must render no --only in the fetch unit's ExecStart";
    assert lib.assertMsg (lib.hasInfix "--only krea2-vae" onlyFetchStart)
      "eval: models.only = [ \"krea2-vae\" ] must render --only krea2-vae into the fetch unit's ExecStart";
    assert lib.assertMsg
      (
        lib.hasInfix "--only krea2-vae" onlyTwoFetchStart
        && lib.hasInfix "--only krea2-text-encoder" onlyTwoFetchStart
      )
      "eval: models.only with two names must render each as its own --only flag in the fetch unit's ExecStart";
    assert lib.assertMsg (lib.any (
      r: lib.hasInfix "/var/lib/comfyui/models/diffusion_models" r
    ) gpuOn.systemd.tmpfiles.rules) "eval: tmpfiles must create the models/diffusion_models subfolder";
    builtins.seq gpuOn.system.build.toplevel.drvPath (
      pkgs.runCommand "comfyui-eval-ok" { } "touch $out"
    );

  comfyui-assertion-negative-listen = mkNegative "comfyui-assertion-negative-listen" {
    services.comfyui = {
      enable = true;
      models.hfTokenFile = hfTokenFile;
      proxy.listen = "0.0.0.0:8188";
    };
  } "proxy.listen must be loopback";

  # brokerInstance = "nope" names an instance nothing else in this
  # harness declares (only "media" gets hostAddress/namespaceAddress,
  # in checks/eval-harness.nix) — this is what actually trips the
  # brokerInstanceOk assertion in nixosModules/comfyui.nix now (see
  # its WHY comment); before that fix, this passed on an unrelated
  # raw eval error regardless of the assertion's own presence.
  comfyui-assertion-negative-broker = mkNegative "comfyui-assertion-negative-broker" {
    services.comfyui = {
      enable = true;
      models.hfTokenFile = hfTokenFile;
      brokerInstance = "nope";
    };
  } "names no services.egress-broker.instances entry with hostAddress and namespaceAddress defined";

  comfyui-assertion-negative-token = mkNegative "comfyui-assertion-negative-token" {
    services.comfyui = {
      enable = true;
      models.hfTokenFile = "/nix/store/abc-hf";
    };
  } "must be a path outside the Nix store";

  # listen.address defaults to the broker instance's namespaceAddress
  # (10.100.2.2 in this harness); an explicit override to anything
  # else must trip the fourth assertion in nixosModules/comfyui.nix,
  # proving a caller cannot bind ComfyUI to a host-reachable address
  # (e.g. 0.0.0.0, which would also be reachable on the veth toward
  # the host at namespaceAddress's peer).
  comfyui-assertion-negative-listen-address = mkNegative "comfyui-assertion-negative-listen-address" {
    services.comfyui = {
      enable = true;
      models.hfTokenFile = hfTokenFile;
      listen.address = "0.0.0.0";
    };
  } "must equal the broker instance's namespaceAddress";

  # gpu.enable defaults true; without an NVIDIA driver configured
  # (checks/eval-harness.nix sets services.xserver.videoDrivers =
  # [ "nvidia" ] itself, so this overrides it back to empty with
  # mkForce), the gpu assertion in nixosModules/comfyui.nix must
  # fire. `hardware.nvidia.package != null` cannot be used to prove
  # this (nixos/modules/hardware/video/nvidia.nix defaults it to a
  # non-null derivation unconditionally) — this check is what
  # exposed that the previous assertion was vacuous.
  comfyui-assertion-negative-gpu = mkNegative "comfyui-assertion-negative-gpu" {
    services.comfyui = {
      enable = true;
      models.hfTokenFile = hfTokenFile;
    };
    services.xserver.videoDrivers = lib.mkForce [ ];
  } "requires an NVIDIA driver configured on the host";

  # services.comfyui-worlds: one definition renders, per world, the
  # ComfyUI generator (user unit), the ONE feed app (comfy-feed.service,
  # user unit), the target that starts both — and NO Caddy configuration
  # at all (GN26: the LAN face is services.lan-access's).
  # This check forces the toplevel drvPath (the repo's shape) inside
  # worldsHarness — which evaluates nixosModules.comfyui-worlds — and
  # asserts the rendered unit/option fragments. The mutation proofs in
  # this task remove `Conflicts` and the Caddy block from the module here
  # and watch this go red.
  # GN14 — the local model unit, proven at eval: the ExecStart literals
  # (loopback bind, port, --no-webui, -c, -ngl, the idle flag the step-1
  # probe found in the built server's --help), the ExecStartPre guard with
  # path and digest, the derived Conflicts= list (both generators —
  # evaluated over lmWorldsHarness, where the worlds module is imported
  # beside it, because the default is derived FROM the worlds config),
  # wantedBy = [] (on-demand, never started by a target), and every
  # hardening member by name, one assertion per member: a member with no
  # assertion is a member that can be deleted silently (G12's invariant-2
  # claim and environment-review.md:418's closure rest on these lines).
  # localModelHarness carries the module ALONE (every option at its default
  # except enable/modelPath/sha256), so the literals assert the defaults;
  # lmModelBesideWorlds (below, same two-module harness as
  # lmWorldsHarness) carries the full host shape for the conflicts default.
  local-model-eval =
    let
      # 64 lowercase hex — the measured sha256 of "not a real gguf"
      # (GN14 step 1's probe), a stand-in digest for eval only.
      probeDigest = "20f7fea9a3ca4565833ecfdb6593541843dc9ae9bebcefbff1d353b5c1391f94";
      modelPath = "/home/alice/models/author.gguf";
      lmCfg =
        (localModelHarness {
          services.local-model = {
            enable = true;
            inherit modelPath;
            sha256 = probeDigest;
          };
        }).config;
      unit = lmCfg.systemd.user.services.comfy-author-model;
      svc = unit.serviceConfig;
      start = toString svc.ExecStart;
      pre = toString svc.ExecStartPre;
      # The conflicts default is derived from the configured worlds, so the
      # assertion needs the worlds module beside local-model — the
      # lmWorldsHarness shape (both modules), with the worlds configured the
      # way the host wires them.
      besideWorlds =
        (lmWorldsHarness {
          services.local-model = {
            enable = true;
            inherit modelPath;
            sha256 = probeDigest;
          };
          services.comfyui-worlds = {
            enable = true;
            operatorUser = "alice";
            root = "/home/alice/comfyui";
            feedPort = 8288;
            worlds = {
              sfw.comfyPort = 8188;
              nsfw.comfyPort = 8189;
            };
          };
          users.users.alice = {
            isNormalUser = true;
          };
        }).config;
      besideUnit = besideWorlds.systemd.user.services.comfy-author-model;
    in
    assert lib.assertMsg (lib.hasInfix "--host 127.0.0.1" start) "local-model eval: --host loopback";
    assert lib.assertMsg (lib.hasInfix "--port 8790" start) "local-model eval: --port 8790 default";
    assert lib.assertMsg (lib.hasInfix "--no-webui" start) "local-model eval: --no-webui";
    assert lib.assertMsg (lib.hasInfix "--model ${modelPath}" start) "local-model eval: --model";
    assert lib.assertMsg (lib.hasInfix "-c 8192" start) "local-model eval: -c contextSize default";
    assert lib.assertMsg (lib.hasInfix "-ngl 999" start) "local-model eval: -ngl gpuLayers default";
    # The idle flag: the step-1 probe found --sleep-idle-seconds in the
    # built llama-server's --help at the pin (grep output in the commit
    # body), so it renders; FACTORY-PROBE idle-flag-rendered=1.
    assert lib.assertMsg (lib.hasInfix "--sleep-idle-seconds 600" start)
      "local-model eval: --sleep-idle-seconds idleSleepSeconds default";
    assert lib.assertMsg (lib.hasInfix "comfy-model-guard" pre) "local-model eval: ExecStartPre guard";
    assert lib.assertMsg (lib.hasInfix modelPath pre) "local-model eval: guard carries the model path";
    assert lib.assertMsg (lib.hasInfix probeDigest pre) "local-model eval: guard carries the digest";
    assert lib.assertMsg (
      besideUnit.conflicts == [
        "comfyui-nsfw.service"
        "comfyui-sfw.service"
      ]
    ) "local-model eval: conflicts must default to every configured generator";
    assert lib.assertMsg (unit.wantedBy == [ ]) "local-model eval: wantedBy empty (on-demand)";
    # Each hardening member by name — never "the hardening members" as a
    # shape: dropping one must be red on that member's own line.
    assert lib.assertMsg (svc.ProtectSystem == "strict") "local-model eval: ProtectSystem strict";
    assert lib.assertMsg (svc.ProtectHome == "read-only") "local-model eval: ProtectHome read-only";
    assert lib.assertMsg svc.NoNewPrivileges "local-model eval: NoNewPrivileges";
    assert lib.assertMsg svc.PrivateTmp "local-model eval: PrivateTmp";
    assert lib.assertMsg (!svc.PrivateDevices) "local-model eval: PrivateDevices false (the GPU)";
    assert lib.assertMsg (
      (unit.unitConfig.ConditionUser or "") == "operator"
    ) "local-model eval: ConditionUser operatorUser";
    assert lib.assertMsg (
      svc.ReadWritePaths == [ "%h/.cache" ]
    ) "local-model eval: ReadWritePaths %h/.cache only";
    # InaccessiblePaths equal as a set, one assertion per entry: dropping
    # any single path is red on that path's own line (M11 drops
    # -/var/lib/secrets — invariant 2 is enforced here, not asserted in
    # prose); the length, asserted last, pins the set exactly, so an ADDED
    # entry is red on the length line while a dropped one is red on its own.
    assert lib.assertMsg (lib.elem "-/run/baskets" svc.InaccessiblePaths)
      "local-model eval: InaccessiblePaths must carry -/run/baskets";
    assert lib.assertMsg (lib.elem "-/var/lib/baskets" svc.InaccessiblePaths)
      "local-model eval: InaccessiblePaths must carry -/var/lib/baskets";
    assert lib.assertMsg (lib.elem "-/var/lib/helm" svc.InaccessiblePaths)
      "local-model eval: InaccessiblePaths must carry -/var/lib/helm";
    assert lib.assertMsg (lib.elem "-/var/lib/egress-broker" svc.InaccessiblePaths)
      "local-model eval: InaccessiblePaths must carry -/var/lib/egress-broker";
    assert lib.assertMsg (lib.elem "-/var/lib/secrets" svc.InaccessiblePaths)
      "local-model eval: InaccessiblePaths must carry -/var/lib/secrets";
    assert lib.assertMsg (
      lib.length svc.InaccessiblePaths == 5
    ) "local-model eval: InaccessiblePaths must be exactly the five entries";
    # GN14 probe 1 (measured, scratch VM at this pin): a user unit's
    # IPAddressDeny=/IPAddressAllow= are a silent no-op ("unit configures an
    # IP firewall, but not running as root") — the recorded fallback omits
    # both; the no-egress property rests on the loopback bind, and this
    # absence assertion keeps the omission deliberate.
    assert lib.assertMsg (!(svc ? IPAddressDeny))
      "local-model eval: IPAddressDeny must stay omitted (probe-1 fallback: the user manager cannot attach the BPF program)";
    assert lib.assertMsg (
      !(svc ? IPAddressAllow)
    ) "local-model eval: IPAddressAllow must stay omitted (probe-1 fallback)";
    builtins.seq lmCfg.system.build.toplevel.drvPath (
      pkgs.runCommand "local-model-eval-ok" { } "touch $out"
    );

  # The four GN14 negatives: each names the option value it refuses.
  local-model-assertion-negative-store-path =
    mkNegativeWith localModelHarness "local-model-assertion-negative-store-path"
      {
        services.local-model = {
          enable = true;
          modelPath = "/nix/store/0000000000000000000000000000000-m.gguf/m.gguf";
          sha256 = "20f7fea9a3ca4565833ecfdb6593541843dc9ae9bebcefbff1d353b5c1391f94";
        };
      }
      "outside /nix/store";

  local-model-assertion-negative-digest =
    mkNegativeWith localModelHarness "local-model-assertion-negative-digest"
      {
        services.local-model = {
          enable = true;
          modelPath = "/home/alice/models/m.gguf";
          sha256 = "nothex";
        };
      }
      "64";

  # Port collision needs the worlds module beside local-model — the
  # lmWorldsHarness shape. GN22: the fixture pins the feedPort arm — the
  # model port equals the ONE feed port (8288), not a comfyPort, so the
  # check forces the whole worldsPorts list (a comfyPort collision would
  # short-circuit lib.elem before the top-level feedPort is ever read,
  # hiding a mutant that still reads the dead per-world feedPort).
  local-model-assertion-negative-port-collision =
    mkNegativeWith lmWorldsHarness "local-model-assertion-negative-port-collision"
      {
        services.local-model = {
          enable = true;
          modelPath = "/home/alice/models/m.gguf";
          sha256 = "20f7fea9a3ca4565833ecfdb6593541843dc9ae9bebcefbff1d353b5c1391f94";
          port = 8288;
        };
        services.comfyui-worlds = {
          enable = true;
          feedPort = 8288;
          worlds.sfw.comfyPort = 8188;
        };
      }
      "collides";

  local-model-assertion-negative-listen-address =
    mkNegativeWith localModelHarness "local-model-assertion-negative-listen-address"
      {
        services.local-model = {
          enable = true;
          modelPath = "/home/alice/models/m.gguf";
          sha256 = "20f7fea9a3ca4565833ecfdb6593541843dc9ae9bebcefbff1d353b5c1391f94";
          listenAddress = "192.168.1.5";
        };
      }
      "loopback";

  comfy-worlds-eval =
    let
      # GN26: no enableLan arm — the module has no LAN options at all. The
      # harness evaluates the module ALONE (no lan-access import), so the
      # no-Caddy asserts below prove the module's silence rather than a
      # second module's override.
      worldsCfg =
        enableRefresh:
        (worldsHarness {
          services.comfyui-worlds = {
            enable = true;
            operatorUser = "alice";
            root = "/home/alice/comfyui";
            # GN22: one feed server — feedPort is top-level (required),
            # feedListenAddress rides its loopback default, and the worlds
            # carry only comfyPort (GN26: the LAN names moved to
            # services.lan-access on the host; worlds.<w>.host is gone and
            # its resurrection is a failed tryEval below).
            feedPort = 8288;
            worlds = {
              sfw.comfyPort = 8188;
              nsfw.comfyPort = 8189;
            };
            refresh.enable = enableRefresh;
          };
          users.users.alice = {
            isNormalUser = true;
          };
        }).config;
      c = worldsCfg false;
      cRefresh = worldsCfg true;
      # GN52 — the cards-enabled arm: the same two-world shape with the
      # card unit on and the lookup host inside the stub broker's allow
      # (huggingface.co, Assumption 10). The unit's proof lives here
      # because the VM node keeps cards.enable off (no broker instance in
      # that VM; the VM step exercises the offline arm by hand).
      cCards =
        (worldsHarness {
          services.comfyui-worlds = {
            enable = true;
            operatorUser = "alice";
            root = "/home/alice/comfyui";
            feedPort = 8288;
            worlds = {
              sfw.comfyPort = 8188;
              nsfw.comfyPort = 8189;
            };
            cards = {
              enable = true;
              lookupUrl = "https://huggingface.co/api/by-hash/{sha256}";
            };
          };
          users.users.alice = {
            isNormalUser = true;
          };
        }).config;
      gen = w: c.systemd.user.services."comfyui-${w}";
      # GN22: the ONE feed unit (comfy-feed.service) — `or null` keeps the
      # absent-unit case an assertion failure with a message, never a raw
      # attribute-missing error.
      feedUnit = c.systemd.user.services.comfy-feed or null;
      mutate = w: c.systemd.user.services."comfy-mutate-${w}";
      genSfw = gen "sfw";
      genNsfw = gen "nsfw";
      genSfwStart = toString genSfw.serviceConfig.ExecStart;
      genNsfwStart = toString genNsfw.serviceConfig.ExecStart;
      genSfwPre = toString genSfw.serviceConfig.ExecStartPre;
      feedStart = if feedUnit != null then toString feedUnit.serviceConfig.ExecStart else "";
      mutateSfw = mutate "sfw";
      mutateNsfw = mutate "nsfw";
      mutateSfwStart = toString mutateSfw.serviceConfig.ExecStart;
      mutateNsfwStart = toString mutateNsfw.serviceConfig.ExecStart;
      runSfw = c.systemd.user.services."comfy-run-sfw";
      runNsfw = c.systemd.user.services."comfy-run-nsfw";
      runSfwStart = toString runSfw.serviceConfig.ExecStart;
      runNsfwStart = toString runNsfw.serviceConfig.ExecStart;
      # GN52 — the card unit on the cCards arm: both worlds' units, the
      # argv, and the broker-derived Environment.
      cardsSfw = cCards.systemd.user.services."comfy-cards-sfw";
      cardsSfwStart = toString cardsSfw.serviceConfig.ExecStart;
      cardsSfwEnv = cardsSfw.serviceConfig.Environment;
      pkgNames = map (d: d.name or "") c.environment.systemPackages;
      has = s: t: lib.hasInfix t s;
      etcJson = builtins.fromJSON (builtins.readFile c.environment.etc."comfy-worlds.json".source);
    in
    assert lib.assertMsg (has genSfwStart "--listen 127.0.0.1") "eval: generator --listen";
    assert lib.assertMsg (has genSfwStart "--port 8188") "eval: sfw generator --port";
    assert lib.assertMsg (has genNsfwStart "--port 8189") "eval: nsfw generator --port";
    assert lib.assertMsg (has genSfwStart "--base-directory /home/alice/comfyui/worlds/sfw")
      "eval: --base-directory";
    assert lib.assertMsg (has genSfwStart "--user-directory /home/alice/comfyui/worlds/sfw/lab/user")
      "eval: --user-directory";
    assert lib.assertMsg (has genSfwStart "--disable-auto-launch") "eval: --disable-auto-launch";
    assert lib.assertMsg (!has genSfwStart "--cpu") "eval: cpuOnly false must not pass --cpu";
    assert lib.assertMsg (has genSfwPre "comfy-world-guard /home/alice/comfyui sfw")
      "eval: ExecStartPre guard";
    assert lib.assertMsg (lib.elem "comfyui-nsfw.service" genSfw.conflicts) "eval: sfw Conflicts nsfw";
    assert lib.assertMsg (lib.elem "comfyui-sfw.service" genNsfw.conflicts) "eval: nsfw Conflicts sfw";
    assert lib.assertMsg (genSfw.wantedBy == [ ]) "eval: generator wantedBy empty";
    assert lib.assertMsg (!genSfw.serviceConfig.PrivateDevices) "eval: PrivateDevices false";
    assert lib.assertMsg (
      !(lib.hasAttr "DevicePolicy" genSfw.serviceConfig)
    ) "eval: no DevicePolicy key";
    assert lib.assertMsg (!(lib.hasAttr "DeviceAllow" genSfw.serviceConfig)) "eval: no DeviceAllow key";
    assert lib.assertMsg (genSfw.serviceConfig.ProtectSystem == "strict") "eval: ProtectSystem strict";
    assert lib.assertMsg (
      genSfw.serviceConfig.ProtectHome == "read-only"
    ) "eval: ProtectHome read-only";
    assert lib.assertMsg (lib.elem "/home/alice/comfyui/worlds/sfw" genSfw.serviceConfig.ReadWritePaths)
      "eval: ReadWritePaths world";
    # GN22 — the one feed unit: a single comfy-feed.service serves every
    # world (world-scoped routes), exec'd with --root/--port/--listen and
    # --worlds-file /etc/comfy-worlds.json; no per-world comfy-feed-<w> unit
    # may exist beside it, and the sandbox names EVERY world dir.
    assert lib.assertMsg (feedUnit != null) "eval: the one comfy-feed unit must exist";
    assert lib.assertMsg (has feedStart "comfy-feed --root /home/alice/comfyui --port 8288")
      "eval: feed ExecStart root and port";
    assert lib.assertMsg (has feedStart "--listen 127.0.0.1") "eval: feed --listen loopback";
    assert lib.assertMsg (has feedStart "--worlds-file /etc/comfy-worlds.json")
      "eval: feed --worlds-file";
    assert lib.assertMsg (
      !(c.systemd.user.services ? "comfy-feed-sfw")
    ) "eval: no per-world comfy-feed-sfw unit";
    assert lib.assertMsg (
      !(c.systemd.user.services ? "comfy-feed-nsfw")
    ) "eval: no per-world comfy-feed-nsfw unit";
    assert lib.assertMsg (feedUnit.unitConfig.ConditionUser == "alice") "eval: feed ConditionUser";
    assert lib.assertMsg (feedUnit.wantedBy == [ ]) "eval: feed on-demand (wantedBy empty)";
    assert lib.assertMsg (
      feedUnit.serviceConfig.ProtectSystem == "strict"
    ) "eval: feed ProtectSystem strict";
    assert lib.assertMsg (
      feedUnit.serviceConfig.ProtectHome == "read-only"
    ) "eval: feed ProtectHome read-only";
    assert lib.assertMsg
      (lib.elem "/home/alice/comfyui/worlds/sfw" feedUnit.serviceConfig.ReadWritePaths)
      "eval: feed ReadWritePaths sfw world";
    assert lib.assertMsg
      (lib.elem "/home/alice/comfyui/worlds/nsfw" feedUnit.serviceConfig.ReadWritePaths)
      "eval: feed ReadWritePaths nsfw world";
    assert lib.assertMsg (lib.elem "%h/.cache" feedUnit.serviceConfig.ReadWritePaths)
      "eval: feed ReadWritePaths %h/.cache";
    assert lib.assertMsg (
      c.services.comfyui-worlds.feedListenAddress == "127.0.0.1"
    ) "eval: feedListenAddress default loopback";
    assert lib.assertMsg (has mutateSfwStart "comfy-mutate --world sfw")
      "eval: comfy-mutate sfw --world";
    assert lib.assertMsg (has mutateNsfwStart "--world nsfw") "eval: comfy-mutate nsfw --world";
    assert lib.assertMsg (has mutateSfwStart "--n 3") "eval: comfy-mutate --n 3";
    assert lib.assertMsg (has mutateSfwStart "--comfy-url http://127.0.0.1:8188")
      "eval: comfy-mutate sfw --comfy-url 8188";
    assert lib.assertMsg (has mutateNsfwStart "--comfy-url http://127.0.0.1:8189")
      "eval: comfy-mutate nsfw --comfy-url 8189";
    assert lib.assertMsg (
      mutateSfwStart != mutateNsfwStart
    ) "eval: comfy-mutate per-world --comfy-url differ";
    assert lib.assertMsg (
      mutateSfw.wantedBy == [ ]
    ) "eval: comfy-mutate units are on-demand (wantedBy empty)";
    assert lib.assertMsg (
      mutateNsfw.wantedBy == [ ]
    ) "eval: comfy-mutate nsfw on-demand (wantedBy empty)";
    assert lib.assertMsg (
      mutateSfw.serviceConfig.ProtectHome == "read-only"
    ) "eval: comfy-mutate ProtectHome read-only";
    assert lib.assertMsg
      (lib.elem "/home/alice/comfyui/worlds/sfw" mutateSfw.serviceConfig.ReadWritePaths)
      "eval: comfy-mutate ReadWritePaths world";
    assert lib.assertMsg
      (lib.elem "/home/alice/comfyui/worlds/nsfw" mutateNsfw.serviceConfig.ReadWritePaths)
      "eval: comfy-mutate nsfw ReadWritePaths world";
    assert lib.assertMsg (lib.elem "comfy-mutate" pkgNames) "eval: comfy-mutate in systemPackages";
    # GN16 — the author CLI joins the one systemPackages list.
    assert lib.assertMsg (lib.elem "comfy-author" pkgNames) "eval: comfy-author in systemPackages";
    # GN52 — the card unit behind cards.enable, the cCards arm first so a
    # module without the cards options fails on the unknown option here:
    # the unit exists for both worlds, its ExecStart names the tool, the
    # world, the root, the lookup template and the flagged timeout, its
    # Environment carries the broker's proxy + CA (the probe's exact pair,
    # from the named instance), the world dir is its only ReadWritePath,
    # and the hardening members are each asserted by name — a member with
    # no assertion is a member that can be deleted silently.
    assert lib.assertMsg (
      cCards.systemd.user.services ? "comfy-cards-sfw"
    ) "eval: cards on must render the comfy-cards-sfw unit";
    assert lib.assertMsg (
      cCards.systemd.user.services ? "comfy-cards-nsfw"
    ) "eval: cards on must render the comfy-cards-nsfw unit";
    assert lib.assertMsg
      (has cardsSfwStart "comfy-cards --world sfw --root /home/alice/comfyui --lookup-url https://huggingface.co/api/by-hash/{sha256}")
      "eval: comfy-cards sfw ExecStart";
    assert lib.assertMsg (has cardsSfwStart "--timeout 30") "eval: comfy-cards --timeout 30";
    assert lib.assertMsg (lib.elem "HTTPS_PROXY=http://10.100.2.1:3130" cardsSfwEnv)
      "eval: comfy-cards unit must carry HTTPS_PROXY";
    assert lib.assertMsg (lib.elem "SSL_CERT_FILE=/var/lib/egress-broker/media/ca/ca.pem" cardsSfwEnv)
      "eval: comfy-cards unit must carry SSL_CERT_FILE";
    assert lib.assertMsg (
      cardsSfw.serviceConfig.ReadWritePaths == [ "/home/alice/comfyui/worlds/sfw" ]
    ) "eval: comfy-cards ReadWritePaths the world dir only";
    assert lib.assertMsg cardsSfw.serviceConfig.PrivateDevices
      "eval: comfy-cards PrivateDevices (the lookup touches no GPU)";
    assert lib.assertMsg (cardsSfw.wantedBy == [ ]) "eval: comfy-cards on-demand (wantedBy empty)";
    assert lib.assertMsg (
      cardsSfw.serviceConfig.ProtectHome == "read-only"
    ) "eval: comfy-cards ProtectHome read-only";
    # GN52 — the card tool's offline arm is the operator's hand tool:
    # comfy-cards rides systemPackages unconditionally, while the unit
    # exists only behind cards.enable (the off-state's half — the cCards
    # arm above proves the on-state).
    assert lib.assertMsg (lib.elem "comfy-cards" pkgNames) "eval: comfy-cards in systemPackages";
    assert lib.assertMsg (
      !(c.systemd.user.services ? "comfy-cards-sfw")
    ) "eval: no comfy-cards-sfw unit when cards are off";
    # GN17 — the per-world supervisor unit comfy-run-<w>: the turn-taking
    # argv (model unit, generator unit, the queue's own comfy-url), the
    # two-empty halt's SuccessExitStatus = "3" (the STRING, so the unit
    # file renders SuccessExitStatus=3 and this assertion compares against
    # the same "3" the module wrote), no Restart= of any value (a restart
    # directive would respin the loop forever and silently defeat the
    # halt), and each sandbox member asserted by name on its own line — a
    # member with no assertion is a member that can be deleted silently.
    assert lib.assertMsg (c.systemd.user.services ? "comfy-run-sfw") "eval: comfy-run-sfw unit";
    assert lib.assertMsg (c.systemd.user.services ? "comfy-run-nsfw") "eval: comfy-run-nsfw unit";
    assert lib.assertMsg (has runSfwStart "comfy-run --world sfw") "eval: comfy-run sfw ExecStart";
    assert lib.assertMsg (has runNsfwStart "--world nsfw") "eval: comfy-run nsfw ExecStart";
    assert lib.assertMsg (has runSfwStart "--low-water 2") "eval: comfy-run --low-water 2";
    assert lib.assertMsg (has runSfwStart "--model-unit comfy-author-model.service")
      "eval: comfy-run --model-unit";
    assert lib.assertMsg (has runSfwStart "--model-url http://127.0.0.1:8790")
      "eval: comfy-run --model-url";
    assert lib.assertMsg (has runSfwStart "--generator-unit comfyui-sfw.service")
      "eval: comfy-run --generator-unit";
    assert lib.assertMsg (has runSfwStart "--n-prompts 8") "eval: comfy-run --n-prompts 8";
    assert lib.assertMsg (has runSfwStart "--window 20") "eval: comfy-run --window 20";
    assert lib.assertMsg (has runSfwStart "--n-variants 3") "eval: comfy-run --n-variants 3";
    assert lib.assertMsg (has runSfwStart "--tick 120") "eval: comfy-run --tick 120";
    # GN21 — the two model-facing budgets are separate knobs, rendered
    # into every supervisor unit so a later edit cannot drop either
    # silently: --model-wait is the wait budget (a server that does not
    # exist yet), --model-timeout the read timeout handed to a live,
    # generating one.
    assert lib.assertMsg (has runSfwStart "--model-wait 120") "eval: comfy-run --model-wait 120";
    assert lib.assertMsg (has runSfwStart "--model-timeout 300") "eval: comfy-run --model-timeout 300";
    assert lib.assertMsg (has runNsfwStart "--model-wait 120") "eval: comfy-run nsfw --model-wait 120";
    assert lib.assertMsg (has runNsfwStart "--model-timeout 300")
      "eval: comfy-run nsfw --model-timeout 300";
    # GN52 — the raised history (Decision 8) rides the supervisor's argv:
    # world.author.historyBatches, default 100, rendered for every world.
    assert lib.assertMsg (has runSfwStart "--history 100") "eval: comfy-run --history 100";
    assert lib.assertMsg (has runNsfwStart "--history 100") "eval: comfy-run nsfw --history 100";
    assert lib.assertMsg (has runSfwStart "--comfy-url http://127.0.0.1:8188")
      "eval: comfy-run sfw --comfy-url";
    assert lib.assertMsg (has runNsfwStart "--comfy-url http://127.0.0.1:8189")
      "eval: comfy-run nsfw --comfy-url";
    # The unit renders absolute store paths for the three binaries it
    # execs (the --*-bin defaults are the bare interactive names); the
    # store prefix is the proof the unit does not rely on PATH.
    assert lib.assertMsg (has runSfwStart "--systemctl /nix/store/")
      "eval: comfy-run --systemctl absolute";
    assert lib.assertMsg (has runSfwStart "--author /nix/store/") "eval: comfy-run --author absolute";
    assert lib.assertMsg (has runSfwStart "--mutate /nix/store/") "eval: comfy-run --mutate absolute";
    assert lib.assertMsg (runSfw.wantedBy == [ ]) "eval: comfy-run on-demand (wantedBy empty)";
    assert lib.assertMsg (runSfw.unitConfig.ConditionUser == "alice") "eval: comfy-run ConditionUser";
    assert lib.assertMsg (
      runSfw.serviceConfig.ProtectSystem == "strict"
    ) "eval: comfy-run ProtectSystem strict";
    assert lib.assertMsg (
      runSfw.serviceConfig.ProtectHome == "read-only"
    ) "eval: comfy-run ProtectHome read-only";
    assert lib.assertMsg runSfw.serviceConfig.PrivateDevices
      "eval: comfy-run PrivateDevices true (the supervisor touches no GPU)";
    assert lib.assertMsg runSfw.serviceConfig.NoNewPrivileges "eval: comfy-run NoNewPrivileges";
    assert lib.assertMsg runSfw.serviceConfig.PrivateTmp "eval: comfy-run PrivateTmp";
    assert lib.assertMsg (
      runSfw.serviceConfig.ReadWritePaths == [ "/home/alice/comfyui/worlds/sfw" ]
    ) "eval: comfy-run ReadWritePaths the world dir only";
    assert lib.assertMsg (
      runNsfw.serviceConfig.ReadWritePaths == [ "/home/alice/comfyui/worlds/nsfw" ]
    ) "eval: comfy-run nsfw ReadWritePaths the world dir only";
    assert lib.assertMsg (
      runSfw.serviceConfig.SuccessExitStatus == "3"
    ) "eval: comfy-run SuccessExitStatus 3 (the string)";
    assert lib.assertMsg (
      !(runSfw.serviceConfig ? Restart)
    ) "eval: comfy-run must carry no Restart= (it would defeat the halt)";
    assert lib.assertMsg (lib.elem "comfy-run" pkgNames) "eval: comfy-run in systemPackages";
    # The supervisor is NOT in the target's wants (GN43 reverted 2026-09-21):
    # comfy-run starts comfy-author-model, whose Conflicts= stops the generator
    # inside the start transaction, and a model that fails leaves the generator
    # down with nothing to restart it — comfy-worlds-vm timed out at 600 s.
    # The negative half is the load-bearing one; re-adding comfy-run-<w> here
    # fails this assertion before it can reach the VM.
    assert lib.assertMsg (
      c.systemd.user.targets."comfy-world-sfw".wants == [
        "comfyui-sfw.service"
        "comfy-feed.service"
      ]
    ) "eval: sfw target wants the generator and the one feed, never the supervisor";
    assert lib.assertMsg (
      c.systemd.user.targets."comfy-world-nsfw".wants == [
        "comfyui-nsfw.service"
        "comfy-feed.service"
      ]
    ) "eval: nsfw target wants the generator and the one feed, never the supervisor";
    assert lib.assertMsg (lib.elem "media-comfy" pkgNames) "eval: media-comfy in systemPackages";
    assert lib.assertMsg (lib.elem "comfy-worlds-init" pkgNames)
      "eval: comfy-worlds-init in systemPackages";
    # GN18 — the owed PATH fix (spec §4 Change 7): media-fetch-models lands
    # beside the author and the supervisor in the one systemPackages list,
    # through the single worldsPkgs member (not a second inline builder).
    assert lib.assertMsg (lib.elem "media-fetch-models" pkgNames)
      "eval: media-fetch-models in systemPackages";
    # GN26: the old comfy-secrets group / tmpfiles asserts are gone with
    # the block they guarded — the no-group / no-tmpfiles arms live with the
    # other no-Caddy asserts below.
    assert lib.assertMsg (
      c.environment.etc."comfy-worlds.json".mode == "0644"
    ) "eval: comfy-worlds.json mode 0644";
    assert lib.assertMsg
      (
        etcJson.root == "/home/alice/comfyui"
        && etcJson.feedPort == 8288
        &&
          etcJson.worldsOrder == [
            "nsfw"
            "sfw"
          ]
        && etcJson.worlds.sfw.comfyPort == 8188
        && etcJson.worlds.nsfw.comfyPort == 8189
        && !(etcJson.worlds.sfw ? "feedPort")
        && !(etcJson.worlds.nsfw ? "feedPort")
      )
      "eval: comfy-worlds.json names the feed port, worldsOrder and both worlds' comfyPort (no per-world feedPort)";
    # GN23 — the deck's low-water knob rides the JSON per world: the feed
    # server reads it from the file (the unit's ExecStart is untouched).
    # `or null` keeps the absent-key case an assertion failure with this
    # message, never a raw attribute-missing error.
    assert lib.assertMsg (
      (etcJson.worlds.sfw.deckLowWater or null) == 5 && (etcJson.worlds.nsfw.deckLowWater or null) == 5
    ) "eval: comfy-worlds.json carries each world's deckLowWater (the deck's low-water knob)";
    # GN24 — the flip guard rides the JSON top level: the activate route
    # (POST /w/<w>/activate) reads the knob from the file, so no unit argv
    # changes with it. `or null` keeps the absent-key case an assertion
    # failure with this message, never a raw attribute-missing error.
    assert lib.assertMsg (
      (etcJson.flipGuardSeconds or null) == 30
    ) "eval: comfy-worlds.json carries flipGuardSeconds (the activate flip guard)";
    # GN26 — the worlds module renders NO Caddy configuration at all: the
    # LAN face is services.lan-access's (one site, one credential, on the
    # host). Proven on a harness that evaluates the module ALONE (no
    # lan-access import), so the silence is proven, not assumed.
    assert lib.assertMsg (
      !c.services.caddy.enable
    ) "eval: the worlds module must not enable Caddy (the LAN face is services.lan-access's)";
    assert lib.assertMsg (
      c.services.caddy.virtualHosts == { }
    ) "eval: the worlds module must render no Caddy virtual host";
    # M8's line: a stale password-file guard ExecStartPre (or the group's
    # SupplementaryGroups) left behind in systemd.services.caddy.serviceConfig
    # is red here even though caddy itself stays disabled — and worldsPkgs
    # would carry a dead derivation. `or { }` keeps the disabled-unit case an
    # assertion failure with a message, never a raw attribute-missing error.
    assert lib.assertMsg
      (
        let
          sc = c.systemd.services.caddy.serviceConfig or { };
        in
        !(sc ? ExecStartPre) && !(sc ? SupplementaryGroups)
      )
      "eval: the worlds module must render no caddy.serviceConfig (the guard's ExecStartPre/SupplementaryGroups died with the LAN block)";
    assert lib.assertMsg (
      !(c.users.groups ? "comfy-secrets")
    ) "eval: the worlds module must create no comfy-secrets group";
    assert lib.assertMsg (
      !(lib.any (r: has r "/var/lib/comfy-secrets") c.systemd.tmpfiles.rules)
    ) "eval: the worlds module must render no /var/lib/comfy-secrets tmpfiles rule";
    assert lib.assertMsg (
      c.networking.firewall.allowedTCPPorts == [ ]
    ) "eval: the worlds module must open no global firewall port";
    assert lib.assertMsg (
      c.networking.firewall.interfaces == { }
    ) "eval: the worlds module must open no interface-scoped firewall port";
    # W5 — refresh.enable renders the weekly probe user unit + timer only
    # when enabled, with the five ReadWritePaths it needs under
    # ProtectHome=read-only, and puts comfy-upstream-probe on PATH.
    assert lib.assertMsg (
      !(c.systemd.user.timers ? "comfy-upstream-probe")
    ) "eval: refresh off must not define the probe timer";
    assert lib.assertMsg (
      cRefresh.systemd.user.timers ? "comfy-upstream-probe"
    ) "eval: refresh on must define the probe timer";
    assert lib.assertMsg (
      !(lib.elem "comfy-upstream-probe" pkgNames)
    ) "eval: refresh off must not put comfy-upstream-probe on PATH";
    assert lib.assertMsg (lib.elem "comfy-upstream-probe" (
      map (d: d.name or "") cRefresh.environment.systemPackages
    )) "eval: refresh on must put comfy-upstream-probe on PATH";
    let
      probeUnit = cRefresh.systemd.user.services.comfy-upstream-probe;
      probeRW = probeUnit.serviceConfig.ReadWritePaths;
      probeStart = toString probeUnit.serviceConfig.ExecStart;
      probeEnv = probeUnit.serviceConfig.Environment or [ ];
      probeTimer = cRefresh.systemd.user.timers.comfy-upstream-probe;
      # A brokerInstance naming no egress-broker instance must be refused
      # (the module's assertion), not silently render a proxy-less unit.
      nope =
        builtins.tryEval
          (worldsHarness {
            services.comfyui-worlds = {
              enable = true;
              operatorUser = "alice";
              root = "/home/alice/comfyui";
              feedPort = 8288;
              worlds = {
                sfw.comfyPort = 8188;
                nsfw.comfyPort = 8189;
              };
              refresh = {
                enable = true;
                brokerInstance = "nope";
              };
            };
            users.users.alice = {
              isNormalUser = true;
            };
          }).config.system.build.toplevel.drvPath;
      # GN26 — retirement proofs: worlds.<w>.host and lan.* are GONE, and
      # a fixture setting either must fail to evaluate (unknown option).
      # A re-added option would make the tryEval succeed and the assert
      # below fail — the retirement is guarded, not assumed.
      hostResurrected =
        builtins.tryEval
          (worldsHarness {
            services.comfyui-worlds = {
              enable = true;
              operatorUser = "alice";
              root = "/home/alice/comfyui";
              feedPort = 8288;
              worlds.sfw = {
                comfyPort = 8188;
                host = "sfw.core.lan";
              };
            };
            users.users.alice = {
              isNormalUser = true;
            };
          }).config.system.build.toplevel.drvPath;
      lanResurrected =
        builtins.tryEval
          (worldsHarness {
            services.comfyui-worlds = {
              enable = true;
              operatorUser = "alice";
              root = "/home/alice/comfyui";
              feedPort = 8288;
              worlds.sfw.comfyPort = 8188;
              lan.enable = true;
            };
            users.users.alice = {
              isNormalUser = true;
            };
          }).config.system.build.toplevel.drvPath;
    in
    assert lib.assertMsg (lib.all (p: lib.elem p probeRW) [
      "-%h/factory/ws/comfy-refresh"
      "-%h/factory/runs/comfy-refresh"
      "-%h/.cache/nix"
      "-%h/.local/state/nix"
      "-/var/lib/evidence"
    ]) "eval: probe ReadWritePaths must carry the flake-check / evidence paths";
    assert lib.assertMsg (has probeStart "--repo /home/alice/flakes/media")
      "eval: probe ExecStart --repo";
    assert lib.assertMsg (probeUnit.unitConfig.ConditionUser == "alice") "eval: probe ConditionUser";
    assert lib.assertMsg (
      probeUnit.serviceConfig.ProtectHome == "read-only"
    ) "eval: probe ProtectHome read-only";
    assert lib.assertMsg (probeTimer.wantedBy == [ "timers.target" ]) "eval: probe timer wantedBy";
    assert lib.assertMsg (
      probeTimer.timerConfig.OnCalendar == "Sun *-*-* 04:00:00"
    ) "eval: probe timer OnCalendar default";
    assert lib.assertMsg probeTimer.timerConfig.Persistent "eval: probe timer Persistent";
    # GN7 — the probe's egress crosses the broker: its unit must carry
    # the proxy + CA it reads from the named broker instance, and an
    # unknown brokerInstance must be refused by the module's assertion.
    assert lib.assertMsg (lib.elem "HTTPS_PROXY=http://10.100.2.1:3130" probeEnv)
      "eval: probe unit must carry HTTPS_PROXY";
    assert lib.assertMsg (lib.elem "SSL_CERT_FILE=/var/lib/egress-broker/media/ca/ca.pem" probeEnv)
      "eval: probe unit must carry SSL_CERT_FILE";
    assert lib.assertMsg (!nope.success) "eval: unknown brokerInstance must be refused";
    # GN26 — the retirement proofs: both fixtures above must FAIL (unknown
    # option), so a resurrected worlds.<w>.host or lan.* turns these red.
    assert lib.assertMsg (
      !hostResurrected.success
    ) "eval: worlds.<w>.host must stay retired (the LAN names are services.lan-access's)";
    assert lib.assertMsg (
      !lanResurrected.success
    ) "eval: services.comfyui-worlds.lan.* must stay retired (the LAN face is services.lan-access's)";
    builtins.seq c.system.build.toplevel.drvPath (
      pkgs.runCommand "comfy-worlds-eval-ok" { } "touch $out"
    );

  # GN22: the comfyPort duplicate — the new spelling of the ports assertion
  # (comfyPort pairwise distinct, the one feedPort apart from them all; the
  # feedPort arm itself has its own negative below). GN26: no host lines —
  # the LAN names moved to services.lan-access on the host.
  comfy-worlds-assertion-negative-ports =
    mkNegativeWith worldsHarness "comfy-worlds-assertion-negative-ports"
      {
        services.comfyui-worlds = {
          enable = true;
          feedPort = 8288;
          worlds = {
            sfw.comfyPort = 8188;
            nsfw.comfyPort = 8188;
          };
        };
      }
      "comfyPort must be pairwise distinct across all worlds and apart from feedPort";

  # GN22: the feedPort arm — a feedPort colliding with a world's comfyPort is
  # refused by its own assertion, not only by the pairwise-distinct one.
  comfy-worlds-assertion-negative-feed-port =
    mkNegativeWith worldsHarness "comfy-worlds-assertion-negative-feed-port"
      {
        services.comfyui-worlds = {
          enable = true;
          feedPort = 8188;
          worlds.sfw.comfyPort = 8188;
        };
      }
      "feedPort must not collide with any world's comfyPort";

  # GN22: the feed bind address is loopback (127.x.x.x or ::1) — a dotted
  # quad that is not 127/8 is refused at eval, before any unit renders.
  comfy-worlds-assertion-negative-listen-address =
    mkNegativeWith worldsHarness "comfy-worlds-assertion-negative-listen-address"
      {
        services.comfyui-worlds = {
          enable = true;
          feedPort = 8288;
          feedListenAddress = "192.168.1.5";
          worlds.sfw.comfyPort = 8188;
        };
      }
      "feedListenAddress must be loopback";

  # GN26 retirements (rubric A7), both with nothing worlds-side left to
  # guard:
  #   - comfy-worlds-assertion-negative-password-path guarded
  #     lan.passwordFileDir's absolute-path assertion; the rule it guarded
  #     is now lanAccess.nix's A4 (proved by the lan-access family's own
  #     lan-assertion-negative), and the option is gone with the whole
  #     lan block, so the check retires.
  #   - comfy-worlds-assertion-negative-hosts guarded the hostsDistinct
  #     assertion; worlds.<w>.host is gone (Decision 7), so the check
  #     retires. The retirement itself is guarded by comfy-worlds-eval's
  #     hostResurrected/lanResurrected tryEval asserts.

  comfy-worlds-assertion-negative-name =
    mkNegativeWith worldsHarness "comfy-worlds-assertion-negative-name"
      {
        services.comfyui-worlds = {
          enable = true;
          feedPort = 8288;
          worlds.Bad_Name.comfyPort = 8188;
        };
      }
      "invalid world name";

  # GN52 — the card unit's host rule: the lookup URL's host must be listed
  # in the named broker instance's allow (the operator's decision). The
  # stub broker's allow carries huggingface.co, so example.invalid
  # discriminates the host rule from "any https host" (a listed host is
  # the scheme and placeholder fixtures' job).
  comfy-worlds-assertion-negative-cards-host =
    mkNegativeWith worldsHarness "comfy-worlds-assertion-negative-cards-host"
      {
        services.comfyui-worlds = {
          enable = true;
          feedPort = 8288;
          cards = {
            enable = true;
            lookupUrl = "https://example.invalid/{sha256}";
          };
        };
      }
      "which services.egress-broker.instances.media.allow does not list";

  # GN52 — the scheme rule: http on a LISTED host is still refused — the
  # fixture discriminates the scheme rule from the host rule (a listed
  # host with the wrong scheme, not an unknown host).
  comfy-worlds-assertion-negative-cards-scheme =
    mkNegativeWith worldsHarness "comfy-worlds-assertion-negative-cards-scheme"
      {
        services.comfyui-worlds = {
          enable = true;
          feedPort = 8288;
          cards = {
            enable = true;
            lookupUrl = "http://huggingface.co/{sha256}";
          };
        };
      }
      "must be an https:// URL";

  # GN52 — the placeholder rule: a listed host, https, but no {sha256} —
  # the template the tool would fetch with never receives a hash.
  comfy-worlds-assertion-negative-cards-placeholder =
    mkNegativeWith worldsHarness "comfy-worlds-assertion-negative-cards-placeholder"
      {
        services.comfyui-worlds = {
          enable = true;
          feedPort = 8288;
          cards = {
            enable = true;
            lookupUrl = "https://huggingface.co/x";
          };
        };
      }
      "must contain {sha256} exactly once";

  media-fetch-unit =
    pkgs.runCommand "media-fetch-unit-tests"
      {
        nativeBuildInputs = [ pyEnv ];
      }
      ''
        mkdir -p pkgs tests
        cp -r ${self}/media/pkgs/media-fetch pkgs/media-fetch
        cp -r ${self}/media/tests/media-fetch tests/media-fetch
        pytest tests/media-fetch -q
        touch $out
      '';

  media-fetch-bats =
    pkgs.runCommand "media-fetch-bats-tests"
      {
        nativeBuildInputs = [
          pkgs.bats
          pkgs.python3
          mediaFetchModels
        ];
      }
      ''
        cp -r ${self}/media/tests tests
        chmod -R u+w tests
        patchShebangs tests/mocks
        bats tests/media-fetch/fetch.bats
        touch $out
      '';

  comfy-worlds-unit =
    pkgs.runCommand "comfy-worlds-unit"
      {
        nativeBuildInputs = [
          pkgs.bats
          pkgs.git
          pyEnv
          pkgs.coreutils
          pkgs.jq
        ];
        worldsJson = pkgs.writeText "comfy-worlds-json-fixture" (
          builtins.toJSON {
            root = "$root";
            feedPort = 8288;
            worldsOrder = [
              "nsfw"
              "sfw"
            ];
            worlds = {
              sfw = {
                comfyPort = 8188;
              };
              nsfw = {
                comfyPort = 8189;
              };
            };
          }
        );
      }
      ''
                mkdir -p pkgs tests
                cp -r ${self}/media/pkgs/comfy-worlds pkgs/comfy-worlds
                cp -r ${self}/media/pkgs/media-fetch pkgs/media-fetch
                cp -r ${self}/media/tests/comfy-worlds tests/comfy-worlds
                export HOME=$TMPDIR
                # GN14: model-guard.bats calls the BUILT comfy-model-guard by bare
                # name — no built binary is otherwise on PATH here (interpolation
                # does not reach inside a .bats file), so the check exports the
                # guard's bin dir before the sweep.
                export PATH=${worldsPkgs.comfy-model-guard}/bin:$PATH
                bats tests/comfy-worlds
                # The packaged command must carry every binary it runs: an
                # undeclared one (findutils, W2b) works on core by ambient PATH
                # and dies at exit 127 half-way through a 127 GB adopt. W3
                # tightens this to a bare PATH with NOTHING on it, which only
                # passes because every wrapper execs an absolute interpreter.
                root=$TMPDIR/bare-root
                mkdir -p "$root/output" "$root/models/checkpoints"
                echo img >"$root/output/a.png"
                printf 'mm' >"$root/models/checkpoints/m.safetensors"
                env -i HOME=$TMPDIR PATH=/no-such-dir GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@x GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@x \
                  ${worldsPkgs.comfy-worlds-init}/bin/comfy-worlds-init --root "$root" --adopt sfw >bare.log 2>&1 \
                  || { echo "comfy-worlds-unit: the built comfy-worlds-init needs a binary it does not declare:"; cat bare.log; exit 1; }
                test ! -e "$root/models"
                env -i HOME=$TMPDIR PATH=/no-such-dir COMFY_WORLDS_JSON=$worldsJson \
                  ${worldsPkgs.media-comfy}/bin/media-comfy status >media.log 2>&1 \
                  || { echo "comfy-worlds-unit: the built media-comfy needs a binary it does not declare:"; cat media.log; exit 1; }
                env -i HOME=$TMPDIR PATH=/no-such-dir \
                  ${worldsPkgs.comfy-feed}/bin/comfy-feed --help >feed.log 2>&1 \
                  || { echo "comfy-worlds-unit: the built comfy-feed needs a binary it does not declare:"; cat feed.log; exit 1; }
                # GN6: the packaged mutator must find feed_index.py and queue.py
                # through FEED_INDEX_PY / FEED_QUEUE_PY (mutate.py imports both at
                # module load), so `--help` under a bare PATH proves the env seams
                # resolve — a bare /nix/store/queue.py is the failure this catches.
                env -i HOME=$TMPDIR PATH=/no-such-dir \
                  ${worldsPkgs.comfy-mutate}/bin/comfy-mutate --help >mutate.log 2>&1 \
                  || { echo "comfy-worlds-unit: the built comfy-mutate needs a binary it does not declare:"; cat mutate.log; exit 1; }
                # GN16: the packaged author must find feed_index.py AND feed.py
                # through FEED_INDEX_PY / FEED_SERVE_PY (author.py imports both at
                # module load), so `--help` under a bare PATH proves both env seams
                # resolve — a FileNotFoundError naming a bare /nix/store/feed.py is
                # exactly what this line catches.
                env -i HOME=$TMPDIR PATH=/no-such-dir \
                  ${worldsPkgs.comfy-author}/bin/comfy-author --help >author.log 2>&1 \
                  || { echo "comfy-worlds-unit: the built comfy-author needs a binary it does not declare:"; cat author.log; exit 1; }
                # GN17: the packaged supervisor must find queue.py through
                # FEED_QUEUE_PY (and queue.py its feed_index through FEED_INDEX_PY)
                # at module load, so `--help` under a bare PATH proves both env
                # seams resolve — the same failure class the author row above
                # catches.
                env -i HOME=$TMPDIR PATH=/no-such-dir \
                  ${worldsPkgs.comfy-run}/bin/comfy-run --help >run.log 2>&1 \
                  || { echo "comfy-worlds-unit: the built comfy-run needs a binary it does not declare:"; cat run.log; exit 1; }
                # GN48: the packaged card tool must find mutate.py through
                # FEED_MUTATE_PY (and mutate.py its feed_index.py/queue.py
                # through FEED_INDEX_PY/FEED_QUEUE_PY) at module load, so
                # `--help` under a bare PATH proves all three env seams
                # resolve — the same failure class the rows above catch.
                env -i HOME=$TMPDIR PATH=/no-such-dir \
                  ${worldsPkgs.comfy-cards}/bin/comfy-cards --help >cards.log 2>&1 \
                  || { echo "comfy-worlds-unit: the built comfy-cards needs a binary or seam it does not declare:"; cat cards.log; exit 1; }
                # GN4b: the packaged feed must find queue.py through FEED_QUEUE_PY
                # (and queue.py its feed_index through FEED_INDEX_PY): the two are
                # single-file store paths whose parent is /nix/store, so the
                # sibling fallback can never resolve there. `queue --run-once` on
                # an unreachable loopback port with no queued jobs must print the
                # clean counts and exit 0 — a FileNotFoundError naming a bare
                # /nix/store/queue.py or /nix/store/feed_index.py is the failure
                # this line exists to catch.
                env -i HOME=$TMPDIR PATH=/no-such-dir \
                  ${worldsPkgs.comfy-feed}/bin/comfy-feed queue --run-once \
                  --world sfw --root "$root" --base-url http://127.0.0.1:1 >queue.log 2>&1 \
                  || { echo "comfy-worlds-unit: the packaged comfy-feed cannot import queue.py (FEED_QUEUE_PY):"; cat queue.log; exit 1; }
                [ "$(cat queue.log)" = "submitted=0 unreachable=0 changed=0" ] \
                  || { echo "comfy-worlds-unit: unexpected comfy-feed queue --run-once output:"; cat queue.log; exit 1; }
                cat queue.log
                # GN25: the packaged feed's two new env seams (FEED_APP_JS /
                # FEED_APP_CSS) resolve under a bare PATH — the FEED_QUEUE_PY rows'
                # pattern, raised to a whole serve: the check starts the BUILT
                # comfy-feed on a scratch root, GETs the mounted asset through the
                # wrapper's own HTTP route, and kills it. A dropped export (M6) is
                # a 404 on /assets/app.js under the packaged path.
                feedRoot=$TMPDIR/feed-assets-root
                mkdir -p "$feedRoot"
                assetsJson=$TMPDIR/comfy-worlds-assets.json
                printf '%s' '{"worlds":{"sfw":{"comfyPort":18188},"nsfw":{"comfyPort":18189}}}' >"$assetsJson"
                env -i HOME=$TMPDIR PATH=/no-such-dir \
                  ${worldsPkgs.comfy-feed}/bin/comfy-feed serve --root "$feedRoot" --port 18288 \
                  --listen 127.0.0.1 --worlds-file "$assetsJson" --engage-url "" >assets.log 2>&1 &
                feed_pid=$!
                if ! python3 - <<'PYEOF'
        import sys
        import time
        import urllib.request

        for _ in range(100):
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:18288/assets/app.js", timeout=2
                ) as resp:
                    body = resp.read()
                    ctype = resp.headers.get("Content-Type", "")
                    if resp.status != 200 or not body or not ctype.startswith("text/javascript"):
                        sys.exit(
                            "assets row: status %s type %r len %d"
                            % (resp.status, ctype, len(body))
                        )
                sys.exit(0)
            except Exception:
                time.sleep(0.1)
        sys.exit("assets row: the built comfy-feed never answered on 18288")
        PYEOF
                then
                  echo "comfy-worlds-unit: the packaged comfy-feed's asset seams failed (FEED_APP_JS/FEED_APP_CSS):"
                  cat assets.log
                  kill "$feed_pid" 2>/dev/null || true
                  exit 1
                fi
                kill "$feed_pid" 2>/dev/null || true
                wait "$feed_pid" 2>/dev/null || true
                # W3 adds pytest files to tests/comfy-worlds; pyEnv carries pytest
                # and (GN21) pytest-timeout, so a test that waits forever fails at
                # the --timeout deadline instead of hanging the whole check.
                # A POSIX glob test that is immune to the build shell's nullglob
                # setting: an unmatched glob iterates once with the literal
                # pattern, whose -e test is false, and a matched glob breaks on
                # the first real file.
                found=
                for f in tests/comfy-worlds/test_*.py; do
                  [ -e "$f" ] && found=1 && break
                done
                if [ -n "$found" ]; then pytest tests/comfy-worlds -q --timeout=120; fi
                touch $out
      '';

  # W5: the weekly probe. The pytest file loads probe.py by path and
  # monkeypatches its two seams (fetch_json/fetch_text, run) onto the
  # fixtures, so this unit runs offline and spawns nothing.
  comfy-upstream-probe-unit =
    pkgs.runCommand "comfy-upstream-probe-unit"
      {
        nativeBuildInputs = [ pyEnv ];
      }
      ''
        mkdir -p pkgs tests
        cp -r ${self}/media/pkgs/comfy-upstream-probe pkgs/comfy-upstream-probe
        cp -r ${self}/media/tests/comfy-upstream-probe tests/comfy-upstream-probe
        pytest tests/comfy-upstream-probe -q
        touch $out
      '';

  # End-to-end proof on real systemd, not just eval: services.comfyui
  # serves through the loopback socket proxy inside a stand-in
  # namespace this test builds itself, fails closed with no broker in
  # the path, and renders a real image on CPU. See
  # tests/integration/comfyui-vm.nix for the design note.
  comfyui-vm = import ./tests/integration/comfyui-vm.nix {
    inherit pkgs;
    module = import ./nixosModules/comfyui.nix;
  };

  # End-to-end proof on real systemd for services.comfyui-worlds: one
  # generator at a time, the per-world tree and feed, the Caddy sites
  # with per-world passwords, the single listener, and the
  # missing-password refusal. See tests/integration/comfy-worlds-vm.nix.
  comfy-worlds-vm = import ./tests/integration/comfy-worlds-vm.nix {
    inherit pkgs;
    module = import ./nixosModules/comfyui-worlds.nix;
  };
}
