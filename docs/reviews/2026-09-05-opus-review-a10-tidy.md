# Opus gate — a10 tidy wave (A10T1, A10T2)

**Approve both**, with two one-line fixes before integration. Real repo and both
`~/factory/ws/a10/*` branches untouched; all work in throwaway clones under the
scratchpad, now removed.

## A10T1 — `helm-control-eval` pins the workspaces JSON to a store path

Closes H2b/M1d exactly. `flake.nix:1044-1053` reads the launcher out of
`environment.systemPackages` (`findFirst` on `p.name or ""`, safe on non-attrsets
— `tryEval ("s".name or "d")` = `"d"`), `flake.nix:1073-1075` asserts the module's
*own* substituted text. Green at `1ee7489`: `helm-control-eval`, `host-core`,
`lint` all exit 0.

**Nit (not blocking):** the regex is unanchored and does not pin the closing
quote, so a comment containing the literal, or a value like
`/nix/store/x'; evil; '`, would pass. Inert today — `nixosModules/helm.nix:30`
mints the path via `pkgs.formats.json`, so it cannot contain a quote.

## A10T2 — the positive `factory-ws` case

`tests/unit/80-seat-driver.bats:74-96` builds a real repo in the tmpdir and
asserts base clone, `task/N17` checkout and the printed path. Green at `58a3fd0`
as test #105; `unit` and `lint` exit 0.

**Fix before merge:** the trailing newline was *not* added — the file still ends
`}` with no `\n` (`od -c` last bytes `] ] \n }`). `lint` cannot see it:
`treefmt.toml`'s shell formatter includes only `*.sh` plus the two githooks.

## Mutation table

| # | Mutation | Caught |
|---|---|---|
| T1-M1 | module substitutes `""` (`helm.nix:188`) | **yes** — eval error, the new assert message |
| T1-M2 | module substitutes `/tmp/helm-workspaces.json` | **yes** — same assert |
| T1-M3 | module splices `builtins.toJSON controlWorkspaces` (the real M1d) | **yes** — same assert |
| T1-R1 | T1-M1 with `main`'s `flake.nix` (assert removed) | **no** — exit 0. The assert is load-bearing; red-before-change proven |
| T2-M1 | git gate → `false` (`factory-ws:45`) | **yes, surgical** — only #105 red, at `bats:88` `[ "$status" -eq 0 ]`; #104 (refusal) stays green |
| T2-M2 | drop `printf '%s\n' "$ws"` (`factory-ws:117`) | **yes** — #105 red at `bats:95`, the `${lines[-1]}` assertion |
| T2-R1 | T2-M1 with `main`'s bats file | **no** — exit 0. The new case is the only thing holding that gate |

## Scope, conventions, trailers

Each is one commit, one file, no docs, no host change. Subjects follow
`<area>: summary (test: …)` and name exactly the checks I ran green.

**Fix before merge (both):** only `Generated-By:` is present. All 42 landed dsh
commits on `main` carry `Co-Authored-By: Claude Fable 5.1` as well — including
a8/H2b and all three a9 branch commits, added on the branch, not at integration.
`factory-brief`'s WORKSPACE RULES (`:86-88`) only asks for `Generated-By`, so
this will recur until that template is amended.
