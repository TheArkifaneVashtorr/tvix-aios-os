# Opus gate — a3 chain W2-N3 → N7b (`task/N7b`, 2 commits on 3e48ba6)

**Verdict: approve.** Both units close their findings, both are red-before-green
under my own mutations, and nothing weakens the broker chokepoint.

## Blockers / majors

None.

## Evidence

**W2-N3 (`48e9796`).** `renderPolicy` is extracted from `policyFile` and re-used
by a new `internal`/`readOnly` option `services.egress-broker.policy`
(`nixosModules/egressBroker.nix:15,99,114`), so the Nix→wire mapping is
assertable at eval time with no IFD; `flake.nix:684-689` asserts
`body_patch."openrouter.ai".path_prefixes == [ "/api/v1/chat/completions" ]` and
`inject."openrouter.ai".paths == [ "/" ]`. `lane-vm` gains step 2b
(`tests/integration/lane-vm.nix:289-315`): two in-netns `curl`s through
`10.100.30.1:3199`, one to `/api/v1/chat/completions` with **no** `provider`
key, one to the unlisted `/api/v1/models`. It proves broker-side enforcement —
the probe body cannot supply `zdr` (the marker `zdr-direct-probe` pins that the
asserted record is the probe's, not the lane client's), and the unlisted path is
asserted byte-equal to what was sent.

Mutations I ran (all in throwaway worktrees, since removed; the clone and the
real repo were never modified — both verified clean afterwards):

| Mutation | Result |
|---|---|
| `body_patch = { };` in `renderPolicy` | `lane-vm` **FAIL**, exit 1, `AssertionError: {"messages":[{"content":"zdr-direct-probe",...}],"model":"m"}` at testScript line 76. Step 2's old `"zdr": true` assertion still passed — exactly the vacuity the finding named. |
| `path_prefixes` → `path_prefixes_RENAMED` | `lane-vm` **FAIL**, exit 1, at line 79: `policy.py:213` defaults a missing key to `["/"]`, so the rename over-patches and the models probe catches it. The rename that used to leave every check green is now caught. |
| drop `paths` from the inject render | `host-core` **FAIL** at `flake.nix:687`. |
| move `self._inject(flow)` above the streamed-body kill in `policy.py:244` | `addon` **FAIL**, 1 failed / 29 passed, on the new `assert "Authorization" not in f.request.headers` (`tests/broker/test_policy.py:604`). The folded-in credential assertion is load-bearing, not vacuous: `_inject` really is reached only after the kill's early `return`. |

**N7b (`c5537a8`).** Added `pkgs/dsh-openrouter` to `ruff check`/`ruff format
--check` in `flake.nix:860-861` and `githooks/pre-commit:21-22`, and brought the
hook's list up to the flake's (`tools/ledger tests/ledger`). The two invocations
are now **byte-identical** (verified by `diff` of the two line pairs). Red-first:
an unused `import shutil` in `pkgs/dsh-openrouter/hook-guard.py` → `lint` FAILS at
`c5537a8` (`F401 … Found 1 error`) and **PASSES** at the parent `48e9796`. Note
`treefmt` already ran `ruff format` on `*.py` repo-wide, so the real new coverage
is `ruff check` (lint rules) — which is what the probe exercised.

**Green at HEAD (`c5537a8`), all run by me:** `lane-vm` 0 (log confirms step 2b's
two probes actually executed in the VM), `lane-eval` 0, `host-core` 0, `addon` 0
(30 passed), `lint` 0, `unit` 0. Regression guard on the touched module:
`module-eval`, `integration`, `lane-assertion-negative` — all pass.

**No scope creep:** diff is confined to the spec's files plus
`tests/broker/test_policy.py` (the spec's own "fold in if cheap"). `pkgs.curl` is
added to the VM node only. `renderPolicy` is a pure extraction — the emitted JSON
is unchanged. Commit subjects follow `<area>: summary (test: …)`; both carry
`Co-Authored-By` and `Generated-By`.

## Minors (one line each)

- `nixosModules/egressBroker.nix:99` — `policy` has no `default = { }`, so reading it on a host with zero instances throws "used but not defined".
- `flake.nix:687` — direct attribute access means a dropped key surfaces as a raw `attribute 'paths' missing`, not the friendly `assertMsg`; a `?` guard would keep the message.
- `flake.nix:686` — the assertion hard-pins the current ZDR scope, so resolving O3 (`patchMessagesPath = true`, `nixosModules/modelLane.nix:184`) turns `host-core` red until the assertion is updated in the same commit; intentional, but it needs a board line.
- `flake.nix:662` vs `:690` — the let-bound `p` is shadowed two lines later by a lambda parameter `p`; rename one.
- `tests/integration/lane-vm.nix:309` — `by_path` is last-wins and silently drops any record whose body contains a newline; the `zdr-direct-probe` marker saves the chat case, the models case has no equivalent guard.
- Nothing pins `githooks/pre-commit`'s ruff list to `flake.nix`'s; they are identical today but can drift again with no test noticing.
