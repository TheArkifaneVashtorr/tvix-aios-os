# dsh-openrouter: the pinned DeepSeek Harness (../dsh) booted on the host for
# the operator's own interactive work, routed to OpenRouter. The script next
# to this file carries the whole contract (refusal list, key handling, what
# is and is not confined); this wrapper only supplies its runtime: the
# harness's bin.js, a Node that takes --expose-internals on its command
# line, and bubblewrap for the harness's own tool sandbox (its Landlock
# fallback ships as a static binary inside the package). It lives in its
# own directory on purpose: ../dsh packs its whole directory as the
# harness's source, so a file added there would change the dsh store path
# the live lane unit references -- and the host toplevel with it.
#
# N7 adds hook-guard (hook-guard.py next to this file): a deny-only
# PreToolUse hook the wrapper mounts through the hooks bridge dsh ships
# (@deepseek-ai/dsh-hooks-claude-code). It is exposed both as the wrapper's
# runtimeEnv.DSH_HOOK_GUARD and, via the symlinkJoin below, as a sibling
# `hook-guard` on PATH so tests/unit/70-dsh-openrouter.bats can drive it
# directly without a flake.nix wiring change (flake.nix is held by other
# tasks in this wave -- see the plan's N10 note).
#
# N7 round 2 adds dsh-denials.py: the reader for hook-guard's denial
# records (now a stderr-only JSON line dsh itself captures into the session
# transcript's `hook/result.stderrSummary` -- see hook-guard.py's module
# docstring for why the workspace-file approach was dropped on review).
# `dsh-openrouter --denials` execs it via runtimeEnv.DSH_DENIALS_READER; the
# same symlinkJoin exposes it as a sibling `dsh-denials` so the bats suite
# can drive it directly. It shells out to `zstd -dc`, hence `zstd` in the
# wrapper's runtimeInputs (its PATH is what a direct `dsh-denials` inherits
# when exec'd from the wrapper, and what the devShell already supplies when
# a test drives it standalone).
{
  lib,
  runCommand,
  writeShellApplication,
  symlinkJoin,
  writers,
  nodejs_22,
  bubblewrap,
  coreutils,
  findutils,
  zstd,
  jq,
  socat,
  dsh,
  harnessPayload ? null,
  python3Minimal,
  buildPackages,
}:
# SA8 (decision 36a): harnessPayload is the store-path input that carries the
# seat's mind (skills/ and AGENTS.md). Null keeps today's warn path alive; a
# non-null value must carry an AGENTS.md and a non-empty skills/ or the
# evaluation fails here rather than deploying an empty mind.
assert lib.assertMsg (
  harnessPayload == null
  || (
    builtins.pathExists "${harnessPayload}/AGENTS.md"
    && builtins.pathExists "${harnessPayload}/skills"
    && builtins.readDir "${harnessPayload}/skills" != { }
  )
) "dsh-openrouter: harnessPayload must carry AGENTS.md and a non-empty skills/ (decision 36a)";
let
  # N15: both Python scripts are stdlib-only -- hook-guard.py imports
  # json/os/re/sys/time/tomllib, and dsh-denials.py imports glob/json/os/subprocess/sys
  # and shells out to the zstd binary (already in the wrapper's runtimeInputs)
  # rather than importing the zstandard module -- so neither needs full
  # python3 (139 MiB). Reuse makePythonWriter to swap only the interpreter,
  # keeping the flake8 self-check and its E501 ignore (ruff is this repo's
  # line-length gate; flake8's 79-col default fights it over hook-guard's
  # long deny-reason literals).
  # buildPackages is the *build-time* flake8 the self-check runs: it stays on
  # full python3 (the interpreter swap is exactly what we do NOT want there --
  # python3Minimal drops zlib, so the bootstrap toolchain behind
  # python3Minimal.pkgs.flake8 cannot build). build-time-only, so it never
  # enters the system closure, which gains only python3Minimal.
  writePython3MinimalBin =
    name:
    writers.makePythonWriter python3Minimal python3Minimal.pkgs buildPackages.python3Packages
      "/bin/${name}";
  hookGuard = writePython3MinimalBin "hook-guard" {
    flakeIgnore = [ "E501" ];
  } (builtins.readFile ./hook-guard.py);
  denialsReader = writePython3MinimalBin "dsh-denials" {
    flakeIgnore = [ "E501" ];
  } (builtins.readFile ./dsh-denials.py);
  # SA6 (decisions 58a/60a): seat-hooks is the one packaged command the
  # wrapper's hooks.json points SessionStart, PreCompact and Stop at. Like the
  # guard and the reader it is stdlib-only (json/os/subprocess/sys), so it
  # joins the wrapper's runtime on python3Minimal rather than full python3.
  seatHooks = writePython3MinimalBin "seat-hooks" {
    flakeIgnore = [ "E501" ];
  } (builtins.readFile ./seat-hooks.py);
  wrapper = writeShellApplication {
    name = "dsh-openrouter";
    runtimeInputs = [
      nodejs_22
      bubblewrap
      coreutils
      findutils
      zstd
      jq
    ];
    runtimeEnv = {
      DSH_OPENROUTER_BIN_JS = "${dsh}/lib/node_modules/dsh-wrapper/node_modules/@deepseek-ai/dsh/lib/bin.js";
      DSH_HOOK_GUARD = "${hookGuard}/bin/hook-guard";
      DSH_DENIALS_READER = "${denialsReader}/bin/dsh-denials";
      DSH_SEAT_HOOKS = "${seatHooks}/bin/seat-hooks";
    }
    # SA8: the payload export is bound only when harnessPayload is a path.
    # Null leaves the variable absent so the wrapper's warn path keeps
    # working (Interface 3) and a hand-set value on the null package is not
    # clobbered by a baked-in empty export -- the bound package alone
    # carries the store path.
    // lib.optionalAttrs (harnessPayload != null) {
      DSH_HARNESS_PAYLOAD = "${harnessPayload}";
    };
    # writeShellApplication prepends its own shebang and `set` line; the
    # script keeps a shebang of its own so shellcheck and shfmt read it as
    # bash in the repo. Drop it here rather than ship two.
    text = lib.removePrefix "#!/usr/bin/env bash\n" (builtins.readFile ./dsh-openrouter.sh);
    meta = {
      description = "DeepSeek Harness on the host, routed to OpenRouter (operator's interactive agent)";
      mainProgram = "dsh-openrouter";
      platforms = [ "x86_64-linux" ];
    };
  };
  # SB6b: expose exactly one socat binary (a symlink) rather than the whole
  # socat package, whose sibling binaries must not land on the seat unit's
  # PATH (see the join's SB4b comment below).
  socatBin = runCommand "dsh-openrouter-socat-bin" { } ''
    mkdir -p $out/bin
    ln -s ${socat}/bin/socat $out/bin/socat
  '';
in
symlinkJoin {
  name = "dsh-openrouter";
  paths = [
    wrapper
    hookGuard
    denialsReader
    seatHooks
    # SB4b: socat joins the wrapper package as a runtime sibling (not a
    # writeShellApplication runtimeInput -- those are forced onto the wrapper's
    # own PATH and would shadow the fake socat the bats test puts on PATH to
    # pin the forwarder argv). Under --bind-namespace the wrapper spawns
    # `socat` from its ambient PATH to relay the namespace address to dsh's
    # loopback; joining it here puts it on the seat unit's PATH (harnessPackage)
    # while keeping it shadowable by a test fake. Only ever exec'd with
    # --bind-namespace. SB6b: joining the whole socat package put `socat1
    # filan procan socat-broker.sh socat-chain.sh socat-mux.sh` onto the seat
    # unit's PATH and onto /run/current-system/sw/bin beside
    # hosts/core/agent-prereqs.nix's own socat (the buildEnv "colliding
    # subpath (ignored)" warning at the host's eval); one symlink keeps the
    # collision to bin/socat and the shadowable-by-a-test-fake property.
    socatBin
  ];
  inherit (wrapper) meta;
  passthru = {
    # N15: which interpreter the hook/denials scripts shebang, asserted by the
    # host-core check so full python3 can never creep back via these two.
    guardPython = python3Minimal;
  };
}
