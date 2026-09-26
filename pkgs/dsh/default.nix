# DeepSeek Harness (dsh) — DeepSeek's own agent CLI, pinned by the lockfile
# next to this file (generated once with `npm install --package-lock-only`
# against @deepseek-ai/dsh 0.1.2-rc.1; the lockfile IS the pin — every one of
# its ~580 registry tarballs is hash-locked, so the build is offline and
# reproducible). Upstream is a developer preview that promises breaking
# changes and takes no external pull requests: extend it with plugins, bump
# the pin deliberately, expect re-ports (docs/brief.md §4).
#
# Why a wrapper package instead of building the pnpm monorepo: the published
# CLI already carries its ~230 internal @deepseek-ai/* workspace packages as
# ordinary registry dependencies, so a one-line dependency plus a lockfile
# gives buildNpmPackage everything it needs; building from the monorepo
# would mean pnpm workspaces, turbo and native addons for no gain at a pin.
#
# Research digest: docs/research-2026-09-03-dsh.md (dated, cited).
{
  lib,
  buildNpmPackage,
  nodejs_22,
}:
buildNpmPackage {
  pname = "dsh";
  version = "0.1.2-rc.1";
  src = ./.;
  nodejs = nodejs_22;
  # Set by `nix build .#dsh` once: the fixed-output hash of the registry
  # tarballs the lockfile names (fetchNpmDeps). A lockfile change invalidates it.
  npmDepsHash = "sha256-uEZWsnA3QL9Phdhb5JooX68TnuwIwcQDwIYJkKjgbGw=";
  # The wrapper has no build step; the CLI ships prebuilt (lib/bin.js).
  dontNpmBuild = true;
  # Lifecycle scripts of optional native packages are not needed for the CLI
  # to run; refusing them keeps the build hermetic.
  npmFlags = [ "--ignore-scripts" ];
  postInstall = ''
    mkdir -p $out/bin
    ln -s $out/lib/node_modules/dsh-wrapper/node_modules/.bin/dsh $out/bin/dsh
    # Node 22.20 (the host pin) ignores NODE_USE_ENV_PROXY; dsh itself never
    # reads HTTPS_PROXY (verified 2026-09-03 against a logging proxy). This
    # preload makes global fetch use undici's proxy agent from the copy that
    # ships inside dsh, so the lane unit can tunnel every model call through
    # its broker with NODE_OPTIONS=--require $out/lib/proxy-shim.cjs.
    cat > $out/lib/proxy-shim.cjs <<EOF
    const u = require("$out/lib/node_modules/dsh-wrapper/node_modules/undici");
    const p = process.env.HTTPS_PROXY || process.env.https_proxy;
    if (p) u.setGlobalDispatcher(u.EnvHttpProxyAgent ? new u.EnvHttpProxyAgent() : new u.ProxyAgent(p));
    EOF
  '';
  meta = {
    description = "DeepSeek Harness (dsh) CLI, pinned by lockfile";
    homepage = "https://github.com/deepseek-ai/deepseek-harness";
    license = lib.licenses.mit;
    mainProgram = "dsh";
    platforms = [ "x86_64-linux" ];
  };
}
