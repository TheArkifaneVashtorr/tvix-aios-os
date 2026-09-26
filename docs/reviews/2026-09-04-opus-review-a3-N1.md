# Opus gate — W2-N1a → W2-N1b (`task/W2-N1b`, head 7ddbcc6, on main 3e48ba6)

**Verdict: approve.** All three N1 findings are resolved, each with a case
proven red by reverse-applying the implementation. Checks on the branch head:
`unit`, `host-core`, `lint` — 3/3 pass. No security weakening: the diff is
3 files / +84 −24, confined to the cache block, the payload warner, the help
text, comments and `runtimeInputs`; the N7 hook set, the sandbox flags, key
handling and the route overlay are untouched. `DSH_CACHE_ROOT` grants no
capability the caller lacked (`XDG_CACHE_HOME` already overrode the whole
path); the symlink refusal and the ownership guard still run before `chmod`,
and the guard is now reachable — strictly stronger than main.

## Majors

**M-1 · the suite gained a new reach outside its temp root**
`tests/unit/70-dsh-openrouter.bats:331` — `XDG_CACHE_HOME=/etc run dsh-openrouter --dump-config`.
Harmless as run today (uid 1000 / nixbld: `mkdir -p /etc` is a no-op, the
guard dies 5 before `chmod`). Under a uid-0 run the guard *passes* and the
next statement is `chmod 700 -- /etc` on the real host; and in any
environment where the caller owns `/etc` the case fails against correct code
— the inherited-state defect N1-1 named. Not a merge blocker: nix builds run
as nixbld and CLAUDE.md forbids sudo. Fix, one line:
`[ "$(id -u)" -eq 0 ] && skip "the ownership guard needs a non-root caller"`.

## Minors

- `:22` `setup()` unsets `XDG_CACHE_HOME`/`DSH_HOME`/… but not `DSH_CACHE_ROOT`; an exported value leaks into ~40 cases. Better than adding it to the `unset` list: `export DSH_CACHE_ROOT="$TMPHOME"` in `setup()` — that also stops the ~35 non-cache cases creating/`chmod 700`-ing the shared `/tmp/dsh-openrouter-cache-$(id -u)` (create-only, verified harmless).
- `:12` `bats_require_minimum_version 1.5.0` sits inside `setup()`; bats expects it above the first `@test`. Works (the `run` flag parses regardless; the call only silences BW02).
- Removing `>&2` from `die()` (`dsh-openrouter.sh:66`) leaves all 43 cases green — die messages are only ever asserted through merged `$output`.
- `:218` the symlink refusal lost its "(/tmp is world-writable)" rationale; defensible now the root is configurable, but the reason survives only in a comment.
- `findutils` in `runtimeInputs` is undeclared-by-test (see M6 below) — acceptable, it is defensive.

## Mutations (all `nix build .#checks.x86_64-linux.unit`)

| # | mutation | outcome |
|---|---|---|
| M1 | `find -H "$path"` → `find "$path"` | **red** — `not ok 66 a deployed payload … warns nothing` |
| M2 | `chmod` moved ahead of the ownership guard | **red** — `not ok 60 … refused with exit 5` (`[ "$status" -eq 5 ]`) |
| M3 | `>&2` dropped from `die()` (mis-target) | green — recorded as a minor |
| M3b | `>&2` dropped from `warn()` `:242` | **red** — `not ok 67 the payload warning lands on stderr` |
| M4 | `cache_root=/tmp` (knob ignored) | **red** — `not ok 61`, `not ok 63` |
| M5 | `--help` default text reverted | **red** — `not ok 38` |
| M6 | `findutils` dropped from `runtimeInputs` | green — stdenv supplies `find`, and `writeShellApplication` prepends to PATH |
| M7 | whole wrapper reverted to 3e48ba6, new tests kept | **red** — `not ok 38, 60, 61, 63` |

Host canary for N1-1: `nix develop -c bats tests/unit/70-dsh-openrouter.bats`
left `/tmp/dsh-openrouter-cache-1000` at the same inode and content count.

## Out of scope (pre-existing, reproduced on main)

`nix develop -c bats tests/unit` is red on the host at
`:549 --dump-config mounts the hooks bridge …` — identical failure at 3e48ba6
(`:502`), green in the sandbox. Cause: the devShell's long `TMPDIR` makes the
harness fold the YAML value (`configPath: >-` + newline), so the one-line
substring never matches. Worth its own tidy task.

Conventions: subjects `dsh: … (test: …)` matching each unit's acceptance list;
`Co-Authored-By` and `Generated-By` trailers present. No scope creep — the
`--help`/comment fixes are the spec's own "also" items.
