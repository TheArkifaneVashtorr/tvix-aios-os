verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-04

## Read when

Invoking `nix` for anything — building, evaluating, developing, or
inspecting the store.

## Flags that matter, always with their command

- `nix build --offline` — disable substituters, treat already-fetched
  inputs as current. Does not stop a fixed-output derivation's own
  download; only the packaging reference's static gate does that.

```bash cmd
nix build --offline nixpkgs#hello --no-link
```

- `nix build -L` (long form `nix build --print-build-logs`) — stream
  build output instead of a spinner; use it on anything you cannot
  otherwise diagnose.

```bash cmd
nix build --offline -L nixpkgs#hello --no-link
```

- `nix build --no-link` — skip creating the `./result` symlink, for a
  check whose only purpose is "does this build".

```bash cmd
nix build --offline --no-link nixpkgs#hello
```

- `nix build -o path` — write the result symlink to `path` instead of
  `./result` (`-o /dev/null`-adjacent uses; more common: a named symlink
  so parallel builds do not clobber `./result`).

```bash cmd
nix build --offline -o /tmp/result-hello nixpkgs#hello
```

- `nix build --print-out-paths` — print the resulting store path(s) to
  stdout, for scripting.

```bash cmd
nix build --offline --print-out-paths --no-link nixpkgs#hello
```

- `nix build --rebuild` — force a derivation already in the store to be
  rebuilt and diffed against the cached output; catches
  non-reproducible builds.

```bash cmd
nix build --offline --rebuild --no-link nixpkgs#hello
```

- `nix build --json` — machine-readable output (also on `nix eval`,
  `nix flake show`); pipe it through the pinned devShell's
  `python3 -m json.tool` to pretty-print (`python3 -m json` alone fails:
  `json` is a package, not a runnable module — `No module named
  json.__main__`).

```bash cmd
nix build --offline --json --no-link nixpkgs#hello | python3 -m json.tool
```

- `nix eval --impure` — allow builtins that read outside the pure
  evaluation model (`builtins.getFlake url` on a plain path, the
  zero-arg builtins.currentSystem, environment variables). Needed for
  the `nixosMin`/`checks/*.nix` style of ad hoc evaluation used
  throughout this skill; never needed for a flake's own `outputs`.

```bash cmd
nix eval --offline --impure --raw --expr '(import <nixpkgs> {}).lib.version'
```

## `nix develop -c`

`nix develop -c <command> [args...]` runs `<command>` inside the
devShell's environment without dropping into an interactive shell —
phrase any command that depends on devShell tooling this way so the
tools it needs are guaranteed present, whatever project's own agent
instructions are driving the session. Bare `nix develop` (no `-c`)
opens an interactive shell instead — never use it from a script or an
agent session; it never returns.

```bash cmd
nix develop -c bash -c 'echo ok'
```

## Store commands

- `nix store gc` — delete unreachable store paths;
  `nix store gc --dry-run` shows what would go without deleting.

```bash cmd
nix store gc --dry-run
```

- `nix store delete <path>` — delete specific paths (refuses if
  anything still roots them). The path below is a placeholder that does
  not exist in the store — safe to run as shown: measured, `nix store
  delete` exits 0 and reports "0.00 MiB freed" for a path that was
  never there, it does not error.

```bash cmd
nix store delete /nix/store/00000000000000000000000000000000-example
```

- `nix store diff-closures <before> <after>` — package-level diff between
  two closures (e.g. two system generations); see the
  activation-and-switch reference. The pair below is a whole system
  against an unrelated tiny package, not two generations — chosen only
  so the example is two genuinely different closures instead of a
  self-diff, which prints nothing; a real before/after would be two
  entries under `/nix/var/nix/profiles/system-*-link`.

```bash cmd
nix store diff-closures /run/current-system /nix/store/na5dnb0l6rjkzrbld3xn4188dd8nknhh-hello-2.12.1
```

- `nix path-info --closure-size <path>` (short `-S`) — prints the sum of
  the NAR sizes of the closure, in raw bytes; add `--human-readable`
  (short `-h`) to get a value like `15.8 GiB` instead of the byte count
  (measured on `/run/current-system` at this pin: `16914740256` plain,
  `15.8 GiB` with `--human-readable`) — `-S` alone is not
  human-readable.

```bash cmd
nix path-info --offline --closure-size /run/current-system
```

```bash cmd
nix path-info --offline --closure-size --human-readable /run/current-system
```

- `nix why-depends --derivation <a> <b>` — why does `<a>`'s closure
  contain `<b>`, at the derivation level (before anything is built).
  Diffing a path against itself always trivially "depends" and shows
  nothing useful, so the example below picks a `<b>` the system does
  not actually pull in, to show the real "does not depend on" output
  too.

```bash cmd
nix why-depends --derivation /run/current-system \
  /nix/store/na5dnb0l6rjkzrbld3xn4188dd8nknhh-hello-2.12.1
```

- `nix copy --to <store-uri> <path>` — copy a store path to another
  store (a directory, another machine over ssh); never used in this
  skill's offline checks, listed for completeness. Illustrative only —
  `<path>` below is a small placeholder (`nixpkgs#hello`'s output), not
  something to run against a whole system closure like
  `/run/current-system` (tens of GiB, copied in full).

```text
nix copy --to file:///tmp/example-store /nix/store/na5dnb0l6rjkzrbld3xn4188dd8nknhh-hello-2.12.1
```

## `nix-collect-garbage` and roots

`nix-collect-garbage` (the pre-flakes command, still current) is mostly
`nix store gc` plus profile pruning:
`nix-collect-garbage --delete-older-than 30d` also expires old *profile
generations* (`nix store gc` alone does not, so old generations keep
every store path they reference alive). A path stays live because
something *roots* it: a profile (`/nix/var/nix/profiles/...`), or a
`result` symlink anywhere on disk (`nix build --no-link` is how you
avoid creating one). The legacy `nix-store --gc --print-roots` lists
every root Nix currently honours — useful for finding a stray `result`
symlink keeping an old generation's closure alive after a switch.

```text
nix-collect-garbage --delete-older-than 30d
nix-store --gc --print-roots
```

## Sources

- `/nix/store/ccppgf5px2d3ig46swcqy0jkiq3nw5bm-nix-2.28.5-doc`
  (command reference, every `nix3-*` page — `nix3-path-info` for
  `--closure-size`/`-S` and `--human-readable`/`-h`)
- `/nix/store/0nrwky0a12lwjvjcx3if3gv2bni2fjmx-nix-2.28.5-man`
  (`nix-collect-garbage(1)`, `nix-store(1)`)
- pinned devShell `python3` (CPython 3.12): `python3 -m json` raises
  "No module named json.__main__" — `json` has no `__main__.py`, only
  `python3 -m json.tool` does.
