# DSH debt measurements

Append-only record. One section per measurement task; each row names the exact
command run and the decisive output line, and every proxy names what it stands
in for and the gap
(`docs/decisions/2026-09-03-test-based-reality-amendments.md`).

## 2026-09-04 — D9: red-before-green for the eight Helm commits

Closes review debt D9 ("Red-before-green for 6 of 8 Helm commits — the rest
rest on commit bodies"). Method is the review's own mutation check: for each
commit, in a throwaway checkout at the commit (`git clone --local` into the
session scratch dir — never the live tree), the commit's **implementation**
hunks were reverse-applied while its **test** hunks stayed in place, then the
named check was run against the implementation-less tree. `red` = the check
fails without the implementation (the test detects it — load-bearing);
`already-green` = it passes (the test is a change-detector that mirrors the
code and cannot fail); `n/a` = docs-only, no flake-gated test to reverse.

What this stands in for: the commit bodies' "tests first / shown red" claims.
Gap: reverse-applying a whole implementation file is coarser than the point
mutations some bodies describe (e.g. flipping one argv or dropping one gate);
where the body names a specific mutation the exact hunk was reversed instead.

| commit | subject checks | reverse-applied (impl) | command (in scratch checkout) | decisive output line | result |
|---|---|---|---|---|---|
| `420a3b7` | unit, lint | `pkgs/helm/helm-switch.sh`, `pkgs/helm/helm-open-workspace.sh` (both new) | `nix build .#checks.x86_64-linux.unit -L --no-link` | `sed: can't read /build/tests/unit/../../pkgs/helm/helm-open-workspace.sh: No such file or directory` (every 80/81 case fails in `setup`; lint too: `openBinaryFile: does not exist`) | red |
| `7f5c329` | helm-unit, lint | `pkgs/helm/serve.py`, `pkgs/helm/render.py` (both new) | `nix build .#checks.x86_64-linux.helm-unit -L --no-link` | `E FileNotFoundError: [Errno 2] No such file or directory: '/build/pkgs/helm/serve.py'` → `1 error in 0.18s` (test_serve.py cannot collect) | red |
| `b678875` | helm-control-eval, helm-control-assertion-negative-profiles/enable/agentunit/workspace, lint | guard assertions in `nixosModules/helm.nix` (`assertions = […] ++ agentUnitGuardAssertions`) + the profiles check's inline `nonBase == specialisations` assertion in `flake.nix` | `nix build .#checks.x86_64-linux.helm-control-assertion-negative-agentunit -L --no-link` (and `-enable`, `-workspace`, `-profiles`) | `error: helm-control-assertion-negative-agentunit: fixture A (changed egress- unit) DID NOT FAIL the build` (all four negatives throw "DID NOT FAIL the build") | red |
| `5c0c44d` | helm-unit | `pkgs/helm/render.py` (reverted to the TDD stub) | `nix build .#checks.x86_64-linux.helm-unit -L --no-link` | `17 failed, 94 passed in 9.28s` (the 17 test_render_control cases) | red |
| `54b1c4d` | helm-control-vm | `nixosModules/helm.nix` (re-added `ProtectHome = "yes"; PrivateTmp = "yes";`) | `nix build .#checks.x86_64-linux.helm-control-vm -L --no-link` | `helm-serve: switch alt http=500 unit_exit=1 from=localhost:7700` (activation dies in the mount namespace, page answers 500) | red |
| `667f25d` | host-core, helm-control-eval | `hosts/core/helm.nix` (the control attrset) | `nix build .#checks.x86_64-linux.host-core -L --no-link` | `error: host-core: services.helm.control must be enabled (the loopback switch + workspace surface)` | red |
| `18d7a17` | lint | — (docs/acceptance/runbook/board) | — | — | n/a |
| `cf21507` | helm-control-eval, helm-eval, host-core, unit, lint | `nixosModules/helm.nix` (un-gated `static-web-server` serviceConfig — the module hunk the review mutated) | `nix build .#checks.x86_64-linux.helm-control-eval -L --no-link` | `error: helm-control-eval: static-web-server.service must not exist under control.enable — the helm module's own SupplementaryGroups/BindReadOnlyPaths serviceConfig must not outlive the upstream unit (a stray serviceConfig renders 'no ExecStart' and a bad unit file)` | red |

**Result.** All seven code commits are `red` — every named behavioural test
fails for the right reason when its implementation is reversed, so none of
the Helm tests is a change-detector; `18d7a17` is docs-only (`n/a`). The two
reproductions the review asked for hold: `cf21507` (reverse the module hunk →
`helm-control-eval` red) and `b678875` (remove the guard → all four
`helm-control-assertion-negative-*` fixtures throw "DID NOT FAIL the build").

Two nuances worth recording:

- **`b678875`'s profiles guard lives in the check, not the module.** The
  `enable`/`agentunit`/`workspace` negatives guard assertions in
  `nixosModules/helm.nix`; the `profiles` negative is enforced only by the
  check's own inline `nonBase == specialisations` assertion in `flake.nix`
  (the module accepts a non-specialisation profile like `"nope"` — nothing in
  `helm.nix` compares `control.profiles` to `config.specialisation`). A real
  host config with a bogus profile would pass `nixos-rebuild` and fail only at
  `nix flake check`.
- **`lint` is a gate, not a change-detector for the impl.** For `7f5c329`,
  reverse-applying `serve.py`/`render.py` leaves `ruff` green (it lints the
  files that remain, and does not resolve `import serve`); the behavioural
  signal is entirely `helm-unit`. The `lint` entries in the commit subjects
  gate formatting/syntax, not behaviour.
