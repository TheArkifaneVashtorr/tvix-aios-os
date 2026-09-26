# aiosd — the tvix-aios daemon (step 1: parses aios.json and exits), built as
# the root Cargo workspace from the publish-gate export against the fork's
# crates (plan 2026-09-22-tvix-aios-step1, OS2; spec 2026-09-22-tvix-aios §2, §5).
#
# Returns four derivations. `src`: the export view of this tree — exactly the
# paths `publish.py export-list` prints, byte for byte, with the fork linked at
# ./tvix (never a tracked path); a red publish gate fails it with the
# validator's own report in the log. `lock`: Cargo.lock regenerated offline
# against the fork's own Cargo.lock (every crate the fork pins is the
# registry) — the one way a lock is ever produced here, because no seat can
# reach crates.io:
#   cp "$(nix build .#aios-lock --print-out-paths --no-link)" Cargo.lock
# `workspace`: `cargo build`, `cargo clippy -D warnings` and `cargo test` of
# every member, every binary under bin/. `forkSrc`: the fork for a hand
# `cargo` session (`nix build .#tvix-aios-src -o tvix`; the pre-commit hook's
# statix and deadnix skip that link and git ignores it).
{
  pkgs,
  self,
  tvix,
}:
let
  src =
    pkgs.runCommand "aios-export-src"
      {
        nativeBuildInputs = [ pkgs.python3 ];
      }
      ''
        export PYTHONDONTWRITEBYTECODE=1
        mkdir -p work/pkgs
        cp -r ${self}/pkgs/evidence work/pkgs/evidence
        find ${self} -type f -printf '%P\n' | LC_ALL=C sort > files.txt
        python3 work/pkgs/evidence/publish.py export-list ${self}/docs/ledger/publish.toml --tree ${self} --files files.txt > export.txt
        mkdir $out
        while IFS= read -r p; do
          mkdir -p "$out/$(dirname "$p")"
          cp "${self}/$p" "$out/$p"
        done < export.txt
        ln -s ${tvix} $out/tvix
      '';
  # Every crate the fork's Cargo.lock pins, fetched from crates.io by the
  # checksums in that lock (nixpkgs importCargoLock): the offline registry the
  # lock generator resolves against, so our lock is always a subset of the fork's.
  forkVendor = pkgs.rustPlatform.importCargoLock { lockFile = "${tvix}/Cargo.lock"; };
  lock =
    pkgs.runCommand "aios-cargo-lock"
      {
        nativeBuildInputs = [
          pkgs.cargo
          pkgs.rustc
        ];
      }
      ''
        cp -Lr --reflink=auto ${forkVendor} cargo-vendor-dir
        chmod -R u+w cargo-vendor-dir
        cp -r ${src} src && chmod -R u+w src && cd src
        mkdir -p .cargo
        cat > .cargo/config.toml <<EOF
        [source.crates-io]
        replace-with = "vendored-sources"

        [source.vendored-sources]
        directory = "$NIX_BUILD_TOP/cargo-vendor-dir"
        EOF
        export CARGO_HOME="$NIX_BUILD_TOP/cargo-home"
        cargo generate-lockfile --offline
        cp Cargo.lock $out
      '';
  workspace = pkgs.rustPlatform.buildRustPackage {
    pname = "aios-workspace";
    version = "0.1.0";
    inherit src;
    cargoLock.lockFile = ../../Cargo.lock;
    nativeBuildInputs = [ pkgs.clippy ];
    cargoBuildFlags = [ "--workspace" ];
    cargoTestFlags = [ "--workspace" ];
    # The linter lands with the language (CLAUDE.md): clippy runs here, where
    # the vendored registry exists, never in `lint`, which has no registry.
    preCheck = ''
      cargo clippy --workspace --all-targets --offline -- -D warnings
    '';
    meta = {
      description = "tvix-aios: the daemon and every workspace binary";
      license = pkgs.lib.licenses.gpl3Only;
      mainProgram = "aiosd";
    };
  };
  forkSrc = pkgs.runCommand "tvix-aios-src" { } "ln -s ${tvix} $out";
in
{
  inherit
    src
    lock
    workspace
    forkSrc
    ;
}
