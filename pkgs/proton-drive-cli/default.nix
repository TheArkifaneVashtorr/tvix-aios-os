{
  lib,
  stdenv,
  stdenvNoCC,
  fetchFromGitHub,
  bun,
  libsecret,
  glib,
  makeShellWrapper,
  writableTmpDirAsHomeHook,
}:
let
  pname = "proton-drive-cli";
  version = "0.8.0";
  sdkVersion = "0.21.0";
  commit = "5491f2e"; # short sha of tag cli/v0.8.0 in the SDK repo (embedded in --version output)

  src = fetchFromGitHub {
    owner = "ProtonDriveApps";
    repo = "sdk";
    tag = "cli/v${version}";
    hash = "sha256-JLyl5I3t5297LEB7ka8RUNwU0BnYy5jeLp3mywoV/YE=";
  };

  # Fixed-output: bun's lockfile-driven installs for the three workspaces the
  # CLI bundles (cli, client/js, incubating/account/js). Hash proven on the
  # 2026-09-02 ad-hoc build of the same tag.
  nodeModules = stdenvNoCC.mkDerivation {
    pname = "${pname}-node-modules";
    inherit version src;
    nativeBuildInputs = [
      bun
      writableTmpDirAsHomeHook
    ];
    dontConfigure = true;
    buildPhase = ''
      runHook preBuild
      export BUN_INSTALL_CACHE_DIR=$(mktemp -d) # keeps the outputHash stable
      cd cli
      bun install --frozen-lockfile --ignore-scripts --no-progress --production
      cd ../client/js
      bun install --frozen-lockfile --ignore-scripts --no-progress --production
      cd ../../incubating/account/js
      bun install --frozen-lockfile --ignore-scripts --no-progress --production
      cd ../../../
      runHook postBuild
    '';
    installPhase = ''
      runHook preInstall
      mkdir -p $out/cli $out/client/js $out/incubating/account/js
      cp -R cli/node_modules $out/cli/
      cp -R client/js/node_modules $out/client/js/
      cp -R incubating/account/js/node_modules $out/incubating/account/js/
      runHook postInstall
    '';
    dontFixup = true;
    outputHashMode = "recursive";
    outputHash = "sha256-iRq1KepMbZpGuBC6FMl+qiwjm81ptwDcP5SmHr/39OE=";
  };
in
stdenv.mkDerivation {
  inherit pname version src;

  nativeBuildInputs = [
    # The SDK README asks for Bun >= 1.3.14 for dev builds; the nixpkgs pin
    # here ships 1.3.13, which produced a working binary on 2026-09-02
    # (keep; revisit if the CLI tag is bumped and this stops working).
    bun
    makeShellWrapper
  ];
  # libsecret + glib are dlopen'd at runtime by the compiled CLI for the
  # OS keychain (PROTON_DRIVE_CREDENTIALS_STORE=keychain, the default).
  buildInputs = [
    libsecret
    glib
  ];

  # Deviation from the plan's transcribed derivation (not present there):
  # stdenv's default fixup-phase `strip -S -p` corrupts the bundle bun
  # embeds into the --compile output -- the stripped binary silently falls
  # back to plain bun's own CLI ("error: Script not found 'filesystem'")
  # instead of running proton-drive.ts. Confirmed by disabling strip and
  # observing the CLI's own --help text return. Bun's compiled executables
  # are not safe to run through a generic ELF stripper.
  dontStrip = true;

  configurePhase = ''
    runHook preConfigure
    cp -R ${nodeModules}/cli/node_modules cli/
    cp -R ${nodeModules}/client/js/node_modules client/js/
    cp -R ${nodeModules}/incubating/account/js/node_modules incubating/account/js
    runHook postConfigure
  '';

  # Same invocation as cli/scripts/build-cli.mjs at this tag, with the
  # version strings pinned (the script derives them from git, unavailable
  # in the sandbox). APP_VERSION name "external-drive-sdkclijs" is the
  # identifier the README assigns to self-built CLIs.
  buildPhase = ''
    runHook preBuild
    cd cli
    bun build \
      --compile \
      --bytecode \
      --target=bun \
      --format=esm \
      --minify \
      --sourcemap=inline \
      --define "APP_VERSION=\"external-drive-sdkclijs@${version}+${commit}\"" \
      --define "SDK_VERSION=\"js@${sdkVersion}+${commit}\"" \
      --define SENTRY_DSN=undefined \
      src/proton-drive.ts \
      --outfile=release/proton-drive
    cd ..
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    install -Dm755 cli/release/proton-drive $out/bin/proton-drive
    wrapProgram $out/bin/proton-drive \
      --prefix LD_LIBRARY_PATH : ${
        lib.makeLibraryPath [
          libsecret
          glib
        ]
      }
    runHook postInstall
  '';

  # Guards against the exact regression review found: the package can build
  # (exit 0) while the compiled binary is silently broken (e.g. dontStrip
  # dropped, a fixup/patchelf change, or a bun bump corrupts --compile's
  # embedded bundle and it falls back to plain bun CLI behavior). Offline:
  # only exercises --help, never proton-drive's own --version (that command
  # phones home to proton.me to check for updates).
  doInstallCheck = true;
  installCheckPhase = ''
    runHook preInstallCheck
    $out/bin/proton-drive filesystem upload --help | grep -q file-conflict-strategy
    runHook postInstallCheck
  '';

  meta = {
    description = "Official Proton Drive command-line client (built from the SDK repository)";
    homepage = "https://proton.me/support/drive-cli";
    license = lib.licenses.mit;
    platforms = [ "x86_64-linux" ];
    mainProgram = "proton-drive";
  };
}
