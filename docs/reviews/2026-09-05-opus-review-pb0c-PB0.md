---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run pb0c, task PB0 — APPROVED

## Summary

PB0 relocks `~/flakes/gaming`'s `nixpkgs` from `ac62194c` (25.05 head) to
`a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4`, which `git ls-remote` confirms is
the *current* `refs/heads/nixos-26.05` head as of this review (the branch has
not moved since planning). One commit on base `cb51a61`, touching exactly
`flake.nix` (the `inputs.nixpkgs.url` rev) and `flake.lock` (the single
`nixpkgs` node: `rev`, `narHash`, `lastModified`, in both `locked` and
`original`). Nothing else in the lock changed — the lock has only two nodes,
`nixpkgs` and `root`. Subject byte-identical to the plan's; `Co-Authored-By`
and `Generated-By` trailers present; the implementer workspace is clean.

The claim under test — a two-release move (25.05 → 25.11 → 26.05) forcing no
module change — is *shown*, not believed. `nix flake check -L` is green on base
at 25.05 and green on HEAD at 26.05; all 11 checks were also built individually
and all pass; `nix flake show` evaluates every output on the new pin; the
flake's `nixpkgs` reports `lib.version = 26.05.20260903.a5cc6f2`, so the checks
really evaluate against the new release, and every check derivation path differs
from its base counterpart (the checks are pin-sensitive, not cached-vacuous).
Mutation B (below) proves a removed/renamed option would fail the very check
that is green, so "no option renamed or removed" is a tested statement.

Two things the commit body understates, both minor and neither blocking: a
second piece of upstream drift went unrecorded (heroic no longer needs the
`electron-36.9.5` insecure-package permission), and `nix flake check` proves
*evaluation*, not that the gaming packages build — the latter is PB1's
toplevel build, and it is a cold 1.76 GiB closure on this host.

## Checks

All run in a throwaway clone of the workspace, `XDG_CACHE_HOME` under the
session scratchpad. **Wall times are warm-store**: the implementer's run already
realized these derivations, so these are re-verification times, not cold-build
times. The proxy stands in for "the check set passes from scratch"; the gap is
download/build time only, not verdict.

`nix flake check -L` on HEAD (task/PB0, 26.05): **exit 0, 25 s**, "running 11
flake checks".
`nix flake check -L` on base (cb51a61, 25.05): **exit 0, 19 s**, "running 11
flake checks".
`nix flake show`: every output evaluates on 26.05 — `nixosModules.{default,
gaming}`, `devShells.x86_64-linux.default`, and all 11 checks.

Per-check `nix build .#checks.x86_64-linux.<name> -L --no-link` at HEAD:

| check | verdict | wall |
|---|---|---|
| `lint` (treefmt --ci, shellcheck, shellcheck -x on tests, statix, deadnix) | PASS | 1 s |
| `drill-unit` | PASS | 0 s |
| `gaming-eval` | PASS | 6 s |
| `gaming-eval-everything` | PASS | 7 s |
| `gaming-eval-session-no-cap` | PASS | 6 s |
| `gaming-assertion-negative-1` (session without gamescope) | PASS | 2 s |
| `gaming-assertion-negative-2` (graphics disabled) | PASS | 2 s |
| `gaming-assertion-negative-3` (steam port without switch) | PASS | 2 s |
| `gaming-assertion-negative-4` (wrapper without capSysNice) | PASS | 2 s |
| `gaming-assertion-negative-5` (renice without switch) | PASS | 2 s |
| `gaming-assertion-negative-6` (audio without pipewire) | PASS | 1 s |

11/11 PASS. `lint` passing at 26.05 is itself a non-obvious result: `treefmt
--ci` reformats nothing, i.e. the `nixfmt` shipped by 26.05 formats these files
exactly as committed.

The gaming flake has no VM test; its check set is the eleven above.

## Drift and warnings

Every `evaluation warning` emitted during `nix flake check -L` at 26.05,
verbatim:

```
evaluation warning: nixfmt-rfc-style is now the same as pkgs.nixfmt which should be used instead.
evaluation warning: programs.gaming: gamescope.capSysNice installs a cap_sys_nice wrapper
evaluation warning: programs.gaming: gamemode.renice installs a CAP_SYS_NICE wrapper on gamemoded
```

The second and third are the module's own authored warnings (`warnings` in
`nixosModules/gaming.nix`), present identically at 25.05 — not drift. The first
is **new at 26.05**: the base log contains no such line. It comes from
`lintTools` in `flake.nix` listing `nixfmt-rfc-style`, now an alias of
`pkgs.nixfmt`. Harmless today; `lint` stays green.

No renamed-option warning appeared. That absence is evidence rather than
silence: `gaming-eval*` force `system.build.toplevel.drvPath`, which runs
nixpkgs' `showWarnings`, and the module's own two warnings did print in the
same logs — so a `mkRenamedOptionModule` warning on any option the module sets
would have printed too.

Option paths the module sets or reads, all of which the green eval exercises:
`programs.steam.{enable,extraCompatPackages,protontricks.enable,
gamescopeSession.enable,remotePlay.openFirewall,
localNetworkGameTransfers.openFirewall,dedicatedServer.openFirewall,
extraPackages}`, `programs.gamescope.{enable,capSysNice}`,
`programs.gamemode.{enable,settings,enableRenice}`, `hardware.xone.enable`,
`hardware.xpadneo.enable`, `hardware.graphics.enable`,
`services.pipewire.{enable,extraConfig.pipewire}`, `security.wrappers`,
`networking.firewall.{allowedTCPPorts,allowedUDPPorts,allowedUDPPortRanges}`,
`environment.systemPackages`. Packages forced: `proton-ge-bin`, `mangohud`,
`mesa-demos`, `heroic`, `lutris`, `bottles`, `mesa`, `pkgsi686Linux.mesa`. All
resolve at `a5cc6f2c`.

**Unrecorded drift (finding F1):** at 26.05 `heroic` no longer requires
`nixpkgs.config.permittedInsecurePackages = [ "electron-36.9.5" ]`. Proven by
deleting that line from `gaming-eval-everything` in a scratch copy:
`gaming-eval-everything` still builds, exit 0. The entry is now inert, and the
comment above it in `flake.nix` ("heroic pulls in an electron build nixpkgs
marks insecure at this pin (EOL electron-36.9.5)") is false at the new pin. The
commit body recorded only the nixfmt alias and asserted "no package
disappeared", which is true but incomplete. The module's option description and
`docs/runbooks/gaming.md` are worded conditionally ("may be marked
insecure/EOL … if the build refuses"), so they are not falsified.
`hosts/core/gaming.nix` carries no `permittedInsecurePackages` entry, so PB1 is
unaffected.

**Build-vs-eval gap (finding F3):** `nix flake check` forces `drvPath`, not
builds. `nix build --dry-run` on the default `programs.gaming.enable = true`
toplevel: at 26.05 **292 derivations to build, 967 paths to fetch (1761.57 MiB
download, 5832.73 MiB unpacked)**; the same probe at 25.05 wants 45 built and 8
fetched (that closure is warm on this host). The 26.05 closure is entirely cold
but substitutable from cache.nixos.org for 967 of ~1259 paths; the 292 local
builds include `steam-unwrapped-1.0.0.85` and its FHS-env rootfs (unfree, never
cached). Nothing here indicates a failure — it is the cost, and the residual
risk, that PB1's `system.build.toplevel` build carries.

## Red before green

- **Base green at 25.05:** `nix flake check -L` at `cb51a61`, exit 0, 11
  checks, no nixfmt warning.
- **HEAD green at 26.05:** exit 0, 11 checks, plus the 11 individual builds
  above.
- **Pin actually moved (the specified mutation, A):** in a scratch copy, set
  `inputs.nixpkgs.url` back to the 25.05 head `ac62194c` and `nix flake lock`.
  Nix reported the transition `a5cc6f2c … (2026-09-03) → ac62194c … (2026-01-02)`
  and the lock node returned to `rev ac62194c…` with `narHash
  sha256-16KkgfdYqjaeRGBaYsNrhPRRENs0qzkQVUooNHtoy2w=`, byte-for-byte the base
  lock (4 lines back). The committed lock is therefore the genuine, canonical
  lock for `a5cc6f2c` and not a hand-edit.
- **Pin sensitivity:** every check derivation path differs between base and
  HEAD (e.g. `audio-without-pipewire-ok`: `2sdarv0k…` at 25.05 vs `hmv1pqj1…`
  at 26.05; the devShell: `2ba89p9s…` vs `pb7zzisc…`). The green HEAD run is
  not a reuse of base results.
- **Mutation B — the green check is load-bearing for option existence:** added
  `services.gonePackageXyz.enable = true;` to `nixosModules/gaming.nix` in a
  scratch copy. `nix build .#checks.x86_64-linux.gaming-eval` exits 1 with
  `error: The option 'services.gonePackageXyz' does not exist. Definition
  values:` and `nix flake check` exits 1. So an option removed or renamed at
  26.05 would have failed the check that is green — "no module drift forced" is
  a test result, not an assertion.
- **Mutation C — see F1:** removing the `permittedInsecurePackages` entry leaves
  `gaming-eval-everything` green, which is how the unrecorded drift was found.
- `nix eval` of the flake's own `inputs.nixpkgs.lib.version` →
  `26.05.20260903.a5cc6f2`: the checks evaluate against the intended release.

## Findings

- **F1 (minor, non-blocking, unrecorded drift).** The `electron-36.9.5`
  insecure-package permission is no longer needed by `heroic` at `a5cc6f2c`;
  the `flake.nix` comment claiming it is required "at this pin" is now false.
  The plan asked for each piece of upstream drift to be recorded in the commit
  body and only the nixfmt alias was. Cosmetic and host-neutral; a follow-up,
  not a re-run.
- **F2 (minor, follow-up).** `lintTools` in `flake.nix` still names
  `nixfmt-rfc-style`, now a deprecated alias of `pkgs.nixfmt` (the one new
  warning). One-word fix, correctly out of scope for PB0's "fix only on
  failure" mandate, but it should land before the alias is removed upstream.
- **F3 (scope, disclosed above).** Green `nix flake check` at 26.05 proves
  evaluation, `lint`, `drill-unit` and the six negative assertions — not that
  Steam, Proton-GE, gamescope, heroic, lutris or bottles build. 292 derivations
  and a 1.76 GiB fetch remain untested until PB1 builds the toplevel.
- **F4 (informational).** `checks/eval-harness.nix` pins
  `system.stateVersion = "25.11"`, now two releases behind the pin. It is a
  free-form string, nixpkgs does not validate it against the release, and the
  harness is test-only — no action, noted so it is not mistaken for drift later.
- No finding contradicts the commit body's central claim, and no defect was
  found in the change itself.

## Deviations

- Gate step 5 suggested grepping the new nixpkgs for each option path. I used a
  stronger method instead: a green full evaluation of the module (which errors
  on any option that no longer exists), plus mutation B proving that failure
  mode is live at this pin, plus the argument from `showWarnings` that a rename
  alias would have printed. The `lib.version` smoke was run as specified.
- Wall times are warm-store re-verification, not cold builds (stated in
  ## Checks).
- I did not build `system.build.toplevel` at 26.05 (~1.76 GiB fetch plus 292
  local builds including the Steam FHS env). The plan scopes PB0's acceptance
  to `flake-check` and PB1 to the toplevel build and closure diff; the
  measured cost is reported instead so the gap is named rather than hidden.
- Mutations A, B and C were run in scratch copies under the session scratchpad.
  The implementer workspace was never written to and is clean at
  `3f4d633994f5`.

## For the orchestrator

PB1 must set `nixpkgs-host.url` to
`github:NixOS/nixpkgs/a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` and re-lock the
`gaming` input to PB0's merged `main`; `checks.core-gaming-wiring` resolves
gaming's nixpkgs node by id and throws unless that rev equals `nixpkgs-host`'s.
Deprecation warnings PB1 will meet: the `nixfmt-rfc-style` alias warning (the
host's own `lintTools`/devShell name it too — expect the same line there), and
nothing else from the gaming module. Expect a long first build: the 26.05
closure is cold on `core`.
