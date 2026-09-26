# Opus gate — a8 H2 / H3

**H2 = rework (commit-subject amend only; code approved). H3 = approve.**

Checks at each head, in throwaway clones (real repo and both task repos untouched):
H2 `unit`/`helm-unit`/`helm-control-eval`/`host-core`/`lint` all exit 0; H3 the
same five all exit 0. Merge of the two branches: clean (`ort`, no conflict) even
though both edit `docs/runbooks/helm-v1.md` and `tests/acceptance/helm-v1.sh` —
the hunks are disjoint (H2 intro/Open-button/step-8; H3 the D5 failure note at
`docs/runbooks/helm-v1.md:115-128`). All five checks pass on the merged tree.

## Mutation table

| # | Mutation | Check | Caught |
|---|---|---|---|
| R2 | reverse-apply launcher to parent (+restore `@CLAUDE_BIN@` sed) | `unit` | **yes** — 6 of 8 red: `#99,100,102,103,104,106` on `args=-ic claude` vs `args=-i` |
| R2b | same tree, `helm-unit` | `helm-unit` | **no — 115 passed.** H2's tests are bats under `unit` |
| H2-M1 | `claude` back in the two default argvs (`:70`,`:75`) | `unit` | **yes** — `#99,100,103,104,106` |
| H2-M2 | drop both `[[ -n $cmd ]]` branches | `unit` | **yes** — `#101,102` |
| H3-M1 | header back to `no-referrer` | `helm-unit` | **yes** — `test_send_carries_anti_framing_headers`: `assert 'no-referrer' == 'same-origin'` |
| H3-M2 | `origin != "null"` bypass in `validate_post` | `helm-unit` | **yes** — `test_validate_rejects_null_origin_as_foreign`: `(0,'') == (403,'foreign-origin')` |

## H2

Argv contract is right: `pkgs/helm/helm-open-workspace.sh:66-75` — `bash -i`,
`nix develop .#$devshell -c bash -i`, and `-ic "$cmd"` only when `command` is
set. `@BASH_BIN@`/`@NIX_BIN@` stay absolute (`nixosModules/helm.nix:178-186`);
`@CLAUDE_BIN@` is gone repo-wide. `command` option `nixosModules/helm.nix:413-422`
(nullOr str, default null); `hosts/core/helm.nix:21-35` sets none, so unchanged
in effect (pinned by `flake.nix:708-736`).

**Rework:** the subject says `(test: helm-unit, …)`. `helm-unit` is
`pytest tests/helm` (`flake.nix:904-915`) and passes with the implementation
reverted. The load-bearing check is `unit`. Amend to `(test: unit, helm-control-eval, host-core, lint)`.

**Nit:** bats `:88` ("command claude, devShell null") also passes against the old
launcher — only `:96` discriminates. Not blocking.

**Security (follow-up, pre-existing class):** `readonly WORKSPACES_JSON='@WORKSPACES_JSON@'`
(`:19`) is a single-quoted literal and `builtins.replaceStrings` does no shell
escaping. I reproduced a breakout: `command = "'; touch /tmp/HELM_PWNED; :'"`
→ generated script is syntactically valid and touches the file *before* the
intended `bash -ic`. `path`/`basket` have had this since 420a3b7, and the values
are operator-authored Nix (no privilege boundary crossed), but `command` is the
field most likely to contain quotes. Fix: `lib.escapeShellArg`, or read the JSON
from a `formats.json` store file. Not a blocker for H2. `"$cmd"` itself is one
argv word — no splitting.

## H3

`pkgs/helm/serve.py:434` is the only source change; `git diff 99056c2 HEAD --
pkgs/helm/serve.py` is that hunk alone — **`validate_post` is byte-identical**,
`:184` still refuses any Origin outside `accepted_origins`. New guard at
`tests/helm/test_serve.py:341-364` pins `Origin: null` refused under both header
shapes. Note it is a *regression* guard, not red-first for the fix (it passes on
main too) — correct choice, and it is what catches H3-M2.

**Citation: accurate.** MDN *Referrer-Policy* § "Effect on the `Origin` header":
for non-GET/HEAD requests not in `cors` mode (HTML form submissions) the UA sets
`Origin: null` under `no-referrer`; under `same-origin` only when cross-origin.
MDN *Origin* lists referrer policy among the `null` causes. One narrowing: this
is spec-mandated UA behaviour (Fetch, "append a request `Origin` header"), not
Firefox-specific — Chrome does the same. The runbook's "Firefox note" framing is
fine for the operator; the commit body's "documented Firefox behaviour" is
narrow but not wrong. `same-origin` also nulls the Origin cross-origin, which
the check still refuses — no weakening.

`helm-control-vm` (named in the subject) was not run here; it asserts no
Referrer-Policy anywhere, so it is unaffected.
