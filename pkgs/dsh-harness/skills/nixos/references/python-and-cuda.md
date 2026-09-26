verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Packaging a Python tool, or wiring up torch, CUDA, or the NVIDIA driver.

## _python3.withPackages_ and `buildPythonPackage`

`pkgs.python3.withPackages (ps: [ ps.numpy ps.requests ])` builds one
interpreter with those packages on its _sys.path_ — the right shape for
`environment.systemPackages` or a `writeShellApplication`'s
`runtimeInputs`; never install a Python package into
`environment.systemPackages` directly, it will not be on any
interpreter's path. `pkgs.python3Packages.buildPythonPackage` builds one
package; `pyproject = true` (PEP 517/518, most packages now) reads
`build-system` for its build backend, `dependencies` for runtime
requirements — the older `format = "setuptools"`/`format = "wheel"`
shapes still exist for packages that predate a _pyproject.toml_.

```nix expr
(pkgs.python3.withPackages (ps: [ ps.requests ])).name
```

## `packageOverrides` and the torch / torch-bin rule

`torch` builds PyTorch from source — hours, and CUDA support needs
`cudaSupport = true` plus a matching `cudaCapabilities` list for the
actual GPU. `torch-bin` installs the upstream prebuilt wheel — minutes,
CUDA already compiled in, no `cudaSupport` flag to set, but it is
**unfree** at this pin (`torch`'s own _meta.license_ is free;
`torch-bin`'s is `[ free unfree unfree ]`), so swapping it in needs
`nixpkgs.config.allowUnfree = true` (or an `allowUnfreePredicate` naming
`"torch"` — see packaging.md's `allowUnfree` section) or the eval
refuses with "has an unfree license ..., refusing to evaluate." Prefer
`torch-bin` unless a patch or a source-only fix is needed. Swap it in
for every package (including transitive dependents) that pulls in
`torch` with _python3.override_'s own `packageOverrides` argument — a
`self: super:` function, the same fixed-point shape as an overlay but
scoped to one interpreter's package set. Prove the swap actually took
by comparing derivations, not by reading an attribute (like `pname`)
that reads the same either way:

```nix module
{ pkgs, ... }:
let
  py = pkgs.python3.override {
    packageOverrides = self: super: { torch = super.torch-bin; };
  };
in
{
  nixpkgs.config.allowUnfree = true;
  assertions = [
    {
      assertion = py.pkgs.torch.drvPath == pkgs.python3Packages.torch-bin.drvPath;
      message = "packageOverrides did not swap torch for torch-bin";
    }
  ];
}
```

**Wrong:** `packageOverrides` given a one-argument function (the
`self: super:` shape is not optional — it is how the fixed point sees
its own overridden set as `self`) — the exact error at this pin:

```text
$ nix eval --impure --expr \
    '((import <nixpkgs> {}).python3.override {
       packageOverrides = super: { torch = super.torch-bin; };
     }).pkgs.torch.pname'
error: attempt to call something which is not a function but a set:
       { torch = «thunk»; }
       at /nix/store/...-source/lib/fixed-points.nix:337:18
```

After building, prove CUDA actually linked in — a Nix-level `version`
attribute is just the package version string; the proof is the Python
runtime's own _torch.version.cuda_, `None` for a CPU-only build:

```bash cmd
python3 -c 'import torch; print(torch.version.cuda)'
```

## `cudaPackages` / `cudaSupport`

`pkgs.cudaPackages` is the CUDA toolkit set at this pin's default
version; `pkgs.cudaPackages_12_6`-style pinned sets exist alongside it
for a package that needs an exact major.minor. _config.cudaSupport_
(set the same way as `allowUnfree`, under `nixpkgs.config`) is the
global flag most CUDA-aware packages branch on (`torch`'s `source`
build, `numba`, `tensorflow`); it does not by itself make a _specific_
package build with CUDA; check each package's own `cudaSupport ?
_config.cudaSupport_ default.

```nix expr
pkgs.cudaPackages.cudaMajorMinorVersion
```

## `hardware.nvidia.*` open modules

`hardware.nvidia.open` defaults to `null` on driver versions ≥ 560 (the
common case now), which the module's own assertion below then rejects
— it must be set, `true` for the open-source kernel
module (required on Turing-or-later GPUs run in some configurations,
recommended generally) or `false` for the proprietary one. Also set
`services.xserver.videoDrivers` to include `"nvidia"` — the driver
module's own config is gated on that list containing `"nvidia"`, not on
`hardware.nvidia.*` being set at all.

```nix module
{ ... }:
{
  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.nvidia.open = true;
  nixpkgs.config.allowUnfree = true;
}
```

**Wrong:** `hardware.nvidia.open` left unset — the exact assertion at
this pin:

```text
$ nix eval --impure --expr \
    '(import <nixpkgs/nixos/lib/eval-config.nix> {
       system = "x86_64-linux";
       modules = [
         { fileSystems."/".device = "/dev/null";
           boot.loader.grub.enable = false;
           system.stateVersion = "25.05"; }
         { services.xserver.videoDrivers = [ "nvidia" ]; }
       ];
     }).config.system.build.toplevel'
error:
       Failed assertions:
       - You must configure `hardware.nvidia.open` on NVIDIA driver
       versions >= 560.
       It is suggested to use the open source kernel modules on Turing
       or later GPUs (RTX series, GTX 16xx), and the closed source
       modules otherwise.
```

`hardware.nvidia.package` defaults to
_config.boot.kernelPackages.nvidiaPackages.stable_ — or `.dc` instead,
when `hardware.nvidia.datacenter.enable` is on — override it to pin
a different channel (`.beta`, `.production`, `.legacy_470`, …) or to
build one nixpkgs does not package yet with `pkgs.linuxPackages`'s
_nvidiaPackages.mkDriver_ (same fake-hash-then-real-hash flow as any
other fetcher, so only its shape is shown, evaluated but never built):

```nix expr
(pkgs.linuxPackages.nvidiaPackages.mkDriver {
  version = "999.99";
  sha256_64bit = pkgs.lib.fakeHash;
  useSettings = false;
  usePersistenced = false;
}).version
```

## `hardware.graphics.enable32Bit`

Needed for any 32-bit binary that touches the GPU (Steam, Wine, most
proprietary game clients) — it pulls in the 32-bit build of the driver
and OpenGL/Vulkan libraries alongside the 64-bit ones.
`hardware.graphics.enable` must also be on; `enable32Bit` alone does
nothing.

```nix module
{ ... }:
{
  hardware.graphics.enable = true;
  hardware.graphics.enable32Bit = true;
}
```

## Build-tool version fixes (the Cython-pin pattern)

Some Python packages generate C sources with a specific Cython major
version and fail against nixpkgs' current default `cython`. The fix is
never patching the generated `.c` — override the package's
`build-system` input to an older Cython nixpkgs still carries
(`pkgs.python3Packages.cython_0` alongside the current
`pkgs.python3Packages.cython`). `av` (PyAV) does **not** need this fix
at this pin — its own `build-system` is `[ cython setuptools ]`, both
current; `spacy` is one package that genuinely carries the `cython_0`
pin at this rev (see Sources), so the shape below is shown generically
against `av` rather than claiming `av` needs it. Keep every existing
`build-system` entry when swapping the Cython version in — replacing
the list outright silently drops a build input like `setuptools`:

```nix module
{ pkgs, ... }:
let
  original = pkgs.python3Packages.av;
  swapped = original.overridePythonAttrs (old: {
    build-system = (builtins.filter (p: (p.pname or "") != "cython") old.build-system) ++ [
      pkgs.python3Packages.cython_0
    ];
  });
in
{
  assertions = [
    {
      assertion = swapped.drvPath != original.drvPath;
      message = "build-system override did not change the derivation";
    }
  ];
}
```

## Sources

- `nixos/modules/hardware/video/nvidia.nix` (`hardware.nvidia.*`, the
  `open` assertion, `nvidiaEnabled`/`videoDrivers` gating)
- `nixos/modules/hardware/graphics.nix` (`enable32Bit`)
- `pkgs/development/interpreters/python/cpython/default.nix`
  (`packageOverrides` argument)
- `pkgs/top-level/python-packages.nix` (`torch`, `torch-bin`,
  `torchWithCuda`)
- `pkgs/os-specific/linux/nvidia-x11/generic.nix` (`mkDriver`'s args)
- `pkgs/development/python-modules/av/default.nix` (current
  `build-system`, showing it does _not_ carry the Cython pin)
- `pkgs/development/python-modules/spacy/default.nix` (a package that
  genuinely carries the `cython_0` build-system pin at this rev)
- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (CUDA, _config.cudaSupport_)
