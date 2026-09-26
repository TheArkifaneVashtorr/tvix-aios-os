# Opus gate — a8 H2b

**Approve.** The H2 rework is done and the security follow-up is real, red-first,
and verified inert against my own payload. Real repo (`b29579a`) and
`/home/dalhaka/factory/ws/a8/H2b` (`3d92991`) untouched; all work in throwaway
clones.

**Amend verified.** `de3345f` has tree `7e63762` — byte-identical to the original
`54ee7bc` — same parent `99056c2`, body unchanged; only the subject moved to
`(test: unit, helm-control-eval, host-core, lint)`.

**Green at `3d92991`:** `unit`, `helm-unit`, `helm-control-eval`, `host-core`,
`lint` all exit 0.

**The fix.** `nixosModules/helm.nix:30` mints the map as a store file
(`pkgs.formats.json`), `:188` substitutes only that path;
`pkgs/helm/helm-open-workspace.sh:21` holds a path, `:36,41-44` read it with
`jq`. Absolute binaries survive (`:76,78,81,83` of the rendered script:
`/run/current-system/sw/bin/{bash,nix}`), the JSON is `-r--r--r-- root` in the
store *and* a registered runtime reference (GC-safe), and `$cmd` reaches exactly
two places — `bash -ic "$cmd"` — and nothing else.

**My payload re-run.** `command = "'; touch …/HELM_PWNED; :'"` on a real host
workspace. Branch: `HELM_PWNED` absent from the rendered script entirely; the
launcher hands `bash` exactly `[-ic] ['; touch …/HELM_PWNED; :']` — one argv
word, byte-intact, nothing executed. Old code, same payload: `bash -n` passes
(silent), and opening an *unrelated* workspace creates the file at line 19 before
argv is built (exit 127).

## Mutation table

| # | Mutation | Caught |
|---|---|---|
| R1 | reverse-apply both source files, keep tests | **yes**, blunt — `unit` #99–107 red |
| R1b | old launcher+module *and* old inline-splice renderer (the faithful red) | **yes, surgical** — only #103 red, at `bats:128` `bash -n`: "unexpected EOF while looking for matching `\"'" |
| M3 | pre-H2 hardcoded-claude launcher vs H2b's tests | **yes** — #101 red; the old `:88` was green here. Nit closed |
| M1c | module-only: splice `builtins.toJSON` back in | **partly** — `unit`/`host-core`/`helm-control-eval` pass; only `lint` (deadnix "Unused let binding: workspacesJson") |
| M1d | …and delete the now-unused binding | **no** — all four green. But fail-closed and loud: every workspace → `jq: Could not open file {…}` → exit 2 |
| M2 | drop `"$cmd"` quoting at both exec sites | **yes** — `lint` SC2086 (`:70`,`:75`) and `host-core`; `unit` passes |

**Follow-up (not blocking):** M1d is the one hole — the guard lives in
`tests/unit/81-…bats`, which renders the template itself and so cannot see the
*module's* substitution regress. A one-line `helm-control-eval` assertion that
the rendered launcher's `WORKSPACES_JSON_FILE` matches `^/nix/store/` would close
it. Also incidental, not a boundary: `writeShellApplication`'s shellcheck flagged
my payload (SC2288) on the old code — a quieter payload builds clean.

**Nit:** the subject still lists `helm-unit`, which touches no changed code.
Harmless — `unit` is named first this time.

**Scope/trailers:** 3 files, no docs, no host change (`hosts/core/helm.nix` sets
no `command`). `Co-Authored-By` + `Generated-By` on both commits.
