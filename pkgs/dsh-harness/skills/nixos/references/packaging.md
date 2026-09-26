verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Packaging new software or overriding an existing derivation.

## _stdenv.mkDerivation_ phases

The standard phases run in order: `unpackPhase`, `patchPhase`,
`configurePhase`, `buildPhase`, `checkPhase` (only when `doCheck`),
`installPhase`, `fixupPhase`. Each has a `pre`/`post` hook
(`preInstall`/`postInstall`, …) so a custom phase can still run the
default logic either side of it. `installPhase` is the one every custom
builder gets wrong first: nothing after it creates `$out` for you.

**Right:** `installPhase` puts something at `$out`.

```nix package
pkgs.stdenv.mkDerivation {
  pname = "greeter";
  version = "1";
  dontUnpack = true;
  installPhase = ''
    mkdir -p $out/bin
    cat > $out/bin/greet <<'EOF'
    #!/bin/sh
    echo hi
    EOF
    chmod +x $out/bin/greet
  '';
}
```

**Wrong:** an `installPhase` that runs but never writes `$out` — the
exact error at this pin (the builder "succeeded" from the shell's point
of view; Nix still has no output to store):

```text
$ nix build --offline .#broken
error: builder for '/nix/store/...-broken-1.drv' failed to produce
       output path for output 'out' at
       '/nix/store/....drv.chroot/root/nix/store/...-broken-1'
```

## Fetchers and hashes

Every fetcher (`fetchurl`, `fetchFromGitHub`, `fetchzip`, …) is a
fixed-output derivation (FOD): its `hash`/`sha256` is not a checksum
Nix trusts blindly, it is the _only_ thing allowed to vary between "this
build" and "the network" — an FOD is the one derivation shape allowed to
touch the network at all, and only because its output is pinned by that
hash. You cannot compute the right hash without fetching once, so you
never guess it (SKILL.md rule 5): put `lib.fakeHash` in, build, and Nix
reports the real hash in the mismatch. This is the one recipe in this
skill that cannot run offline — obtaining a hash means fetching once —
so it is shown below as a `text` block instead of an executed one,
marked as such on the block's own first line; every other example here
still runs at the pin.

```text
cannot run offline — obtaining a hash means fetching once
$ nix build --offline .#pkg   # src = fetchurl { hash = lib.fakeHash; ... };
error: hash mismatch in fixed-output derivation
       '/nix/store/...-pkg.drv':
         specified: sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
            got:    sha256-WJG1tSLV3whtD/CxEPvZ0hu0/HFjrzTQgoai6Eb2vgM=
```

Paste the `got:` value in as `hash = "sha256-...";` and rebuild — still
with `--offline` if you like, it makes no difference here: `--offline`
only disables substituters, it does not stop a fixed-output
derivation's own builder from reaching the network, which is exactly
why the first build above fetched anyway despite the flag. `nix hash
path --offline` hashes something already on disk (a local source
tree); `nix-prefetch-url <url>` fetches and hashes in one step when you
already know the URL and just need the hash.

## `writeShellApplication` / `writeText` / `runCommand`

`pkgs.writeText name text` writes `text` to `$out` verbatim.
`pkgs.runCommand name attrs script` runs `script` in a bare build
environment (no phases) with `attrs` merged into the derivation.
`pkgs.writeShellApplication` wraps a `text` script with `set -euo
pipefail`, an interpreter line, and a `checkPhase` that runs it through
`shellcheck` at build time — the right default for any script this
skill or a generated module ships, never a hand-rolled `writeScriptBin`.

```nix expr
(pkgs.writeShellApplication {
  name = "greet";
  runtimeInputs = [ pkgs.coreutils ];
  text = "echo hi";
}).name
```

## `buildGoModule` / `buildRustPackage` / `buildNpmPackage`

Each vendors a language ecosystem's dependencies into one more FOD, so
each has its own hash argument, obtained the same fake-hash way as any
fetcher: `vendorHash` (Go), `cargoHash` (Rust; _cargoLock.lockFile_ is
the alternative when the crate already ships a _Cargo.lock_),
`npmDepsHash` (`buildNpmPackage`, needs a committed `package-lock.json`).
`vendorHash = null` tells `buildGoModule` not to fetch dependencies at
all — the build then relies on a `vendor/` directory already committed
inside `src` (a module with no dependencies is only the degenerate
case). It is not "skip the hash check": with no `vendor/` present the
build simply fails.

```nix expr
(pkgs.buildGoModule {
  pname = "example";
  version = "1.0";
  src = pkgs.emptyDirectory;   # stand-in for a real source tree
  vendorHash = lib.fakeHash;   # then paste the reported hash, as above
}).pname
```

## `override` vs `overrideAttrs`

`.override { ... }` re-calls the package's own `callPackage` function
with different _arguments_ (only names that function actually takes —
build-time feature flags, alternate dependencies). `.overrideAttrs (old:
{ ... })` changes the _derivation attributes_ `mkDerivation` was given
(`pname`, `patches`, `postInstall`, …) after the fact, regardless of
what the original function's arguments were.

```nix expr
[
  (pkgs.zlib.override { shared = false; }).pname
  (pkgs.hello.overrideAttrs (old: { pname = "hello-custom"; })).pname
]
```

**Wrong:** `.override` with a name the function does not take — the
exact error at this pin (from `pkgs/by-name/he/hello/package.nix`,
whose `callPackage` head has no `nonexistentArg`):

```text
$ nix eval --impure --expr \
    '(import <nixpkgs> {}).hello.override { nonexistentArg = true; }'
error: function 'anonymous lambda' called with unexpected argument
       'nonexistentArg'
       at /nix/store/...-source/pkgs/by-name/he/hello/package.nix:1:1
```

## Overlays

`nixpkgs.overlays` is a list of `final: prev: { ... }` functions; each
sees the _previous_ layer as `prev` and the _fully overlaid_ set as
`final` (so one overlay's replacement is visible to a package defined by
a later overlay, and to that package's own dependents via `final`).
Applied once, in list order, before any module's `pkgs` argument is
built — every module in the same evaluation sees the overlaid package.

```nix module
{ pkgs, ... }:
{
  nixpkgs.overlays = [
    (final: prev: { hello = prev.hello.overrideAttrs (old: { pname = "hello-x"; }); })
  ];
  assertions = [
    {
      assertion = pkgs.hello.pname == "hello-x";
      message = "overlay did not apply";
    }
  ];
}
```

## `allowUnfree` / `permittedInsecurePackages`

Both live under `nixpkgs.config` (a freeform attrset, so the sub-keys
themselves are not catalogued options): `allowUnfree = true` lets an
eval proceed past a package's _meta.license_ unfree check;
`permittedInsecurePackages = [ "name-version" ]` does the same for a
package nixpkgs has flagged insecure, one exact `pname-version` string
at a time — never a blanket allow.

```nix module
{ pkgs, ... }:
{
  nixpkgs.config.allowUnfree = true;
  nixpkgs.config.permittedInsecurePackages = [ "example-1.0" ];
  assertions = [
    {
      assertion = pkgs.config.allowUnfree == true;
      message = "allowUnfree did not propagate";
    }
  ];
}
```

## FODs, _passthru.tests_, `meta`

A fixed-output derivation is any derivation with `outputHash` set
(directly, or via a fetcher) — same hash-obtained-not-guessed rule as
above, whether or not it is called through a named fetcher function.
_passthru.tests_ attaches a package's own test derivations (often
`callPackage ./tests { }`) as an attribute of the package itself,
without them being build inputs — so `nix build .#pkg` never runs them,
while `nix build .#pkg.tests.<name>` builds the package and then runs
that one test against it. _meta.license_, _meta.description_,
_meta.mainProgram_ (the binary `nix run` executes with no `#output`
given) drive the unfree/insecure checks above and `nix run`/`nix
search`; set _meta.mainProgram_ whenever the package name and the binary
name differ.

## Sources

- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (_stdenv.mkDerivation_, overlays, `nixpkgs.config`)
- `pkgs/by-name/he/hello/package.nix` (the `.override` arity error)
- `pkgs/development/libraries/zlib/default.nix` (`shared`/`static`
  override args)
- `pkgs/build-support/go/module.nix` (`vendorHash`)
- `pkgs/build-support/rust/build-rust-package/default.nix` (`cargoHash`)
- `pkgs/build-support/node/build-npm-package/default.nix` (`npmDepsHash`)
