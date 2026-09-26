verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-04

## Read when

Touching `./flake.nix` or `./flake.lock`.

## Inputs

```nix expr
{
  github = "github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d";
  git-file = "git+file:///home/user/repo?ref=main&rev=<40-hex>";
  path = "path:/home/user/repo";
}
```

`github:` fetches a tarball of that rev (fast, no `.git` needed).
`git+file:` (and plain `git+https:`) clones and checks out a rev, and
respects `?dir=`, `?ref=`, `?shallow=1` — like every git-backed input,
it sees only what git tracks (or has staged), never an untracked file.
A directory argument with **no scheme** is auto-detected: if it is
itself a git repository, Nix treats it exactly like a `git+file:` input
(same tracked-files filtering) — see the tracked-files gotcha below. An
explicit `path:` scheme opts *out* of that detection: the path fetcher
copies the directory to the store as-is, untracked files included, with
no git filtering at all — the one escape hatch from the tracked-files
trap.

`follows` pins one input's transitive dependency to another already-named
input, so two inputs that each depend on `nixpkgs` do not each drag in
their own copy:

```nix expr
{
  inputs.llm-agents.url = "github:example/llm-agents";
  inputs.llm-agents.inputs.nixpkgs.follows = "nixpkgs";
}
```

A `follows` is a lock-file decision, not a runtime one — it only changes
which locked input satisfies the dependency, so it must be re-resolved
(`nix flake lock`) whenever the top-level input's rev changes.

## Lock semantics

`./flake.lock` records, per input, the resolved `rev`, `narHash` (a hash
of the fetched tree's contents, checked on every fetch) and
`lastModified`. `nix flake check`/`nix build`/`nix develop` all read
the lock file and never re-resolve a `github:`/`git:` input's rev
unless told to (`nix flake update`). A plain `nix build` silently
writes a *new* lock
entry if the flake reference in `./flake.nix` itself changed; use
`nix build --no-update-lock-file` in any CI/check context that must not
touch the lock. This repo's own lock-guard check asserts the locked
`nixpkgs` rev against the pin for exactly this reason.

## Outputs schema

`outputs = { self, nixpkgs, ... }: { ... }` returns an attribute set. The
recognised top-level output shapes:

```text
packages.<system>.<name>            devShells.<system>.<name>
checks.<system>.<name>               apps.<system>.<name>
nixosConfigurations.<name>           nixosModules.<name>
overlays.<name>                      lib
templates.<name>
```

`nix flake show` lists what a given flake actually exposes.

```bash cmd
nix flake show --json
```

## Commands

```bash cmd
nix build .#checks.x86_64-linux.lint --offline -L --no-link
nix eval .#nixosConfigurations.core.config.system.stateVersion --offline
nix develop -c bash
nix run .#some-app --offline
nix flake check --offline --no-build
```

`nix build --offline` disables substituters and treats already-downloaded
inputs as up to date — it does not stop a fixed-output derivation from
downloading if its hash forces a rebuild (see the packaging reference).
`nix flake check --no-build` evaluates every check derivation without
building any of them — fast for catching eval errors before spending
build time.

## Registry

`nix registry list` shows the flake registry (short names like `nixpkgs`
resolving to a pinned flake reference); a bare `nixpkgs#hello` outside a
flake's own inputs resolves through it and is therefore **not** pinned to
this repo's lock file — never use an unqualified registry reference
inside a checked-in `./flake.nix`; always name the input.

## The tracked-files gotcha

A flake evaluated from a local directory that is a git repository sees
only the files git tracks (or has staged) — not the working tree as a
whole. A file you just created or edited and have not `git add`ed is
invisible to the build, and the failure looks like a missing file, not a
permissions or syntax error:

**Right:** stage the file first.

```bash cmd
git add data.txt
nix build .#default --offline
```

**Wrong:** build with an untracked file the flake reads.

```text
$ nix build .#default --offline
error:
       … while calling the 'readFile' builtin
         at /nix/store/<hash>-source/flake.nix:3:37:
            2|   outputs = { self }: {
            3|     packages.x86_64-linux.default = builtins.readFile ./data.txt;
             |                                     ^
            4|   };

       error: opening file '/nix/store/<hash>-source/data.txt': No such
       file or directory
```

The store path in the error is the git-filtered copy Nix made of the
repo — `./data.txt` was never part of it. Nix does not print a "Git
tree is dirty" warning for a merely untracked file (that warning is
reserved for a tracked file with staged or working changes — see
`self`'s `rev`/`dirtyRev` below); an untracked file just silently drops
out of the build. `git add` (staging is enough; committing is not
required) before every `nix build`/`nix flake check` — or, if the
directory argument would otherwise resolve through the git filter,
prefix it with the explicit `path:` scheme (`path:.`/`path:/abs/path`)
to opt out of tracked-files filtering entirely and read the working
tree as-is. "As-is" is literal: the store copy `path:` makes includes
`.git` and everything `.gitignore` excludes — measured, a throwaway
repo's `path:.` closure held `.git`, `.gitignore`, and a gitignored
file none of the git-filtered forms above ever see. That copies the
whole git history into the world-readable store on every eval, and
puts anything `.gitignore` was hiding (the usual home of secrets and
local config) there too. Reach for `path:` on a scratch tree, not a
repo with history or ignored secrets; `git add` stays the default.

## `self`'s `rev` and `dirtyRev`

The flake's own `self` output carries `rev`, the commit hash of its own
repo — available when the tracked files match HEAD (no staged or
modified tracked file). A merely **untracked** file does not count:
`self`'s `rev` is still there even while `git status` shows an
untracked file, because the git-filtered tree Nix hashes never included
it.

When a tracked file *is* staged or modified, `self`'s `rev` is simply
absent — accessing it is `error: attribute 'rev' missing`, and Nix
prints `warning: Git tree '<path>' is dirty` to stderr first. `self`
carries `dirtyRev` (and `dirtyShortRev`), suffixed `-dirty`, in that
same dirty case. None of this depends on `--impure` in either
direction: `dirtyRev` appears whenever the tree is dirty whether or not
`--impure` is passed, and `--impure` does not resurrect `rev` or
otherwise change which of the two attributes exists — it governs
unrelated impurities (reading the environment, `builtins`' own
`currentTime`, `<nixpkgs>` lookups), not this choice. Do not read
`self`'s `rev` for anything that must be reproducible in CI: a dirty
tree is easy to produce by accident in an interactive session, and
reaching for `--impure` when that happens will not make `rev`
reappear.

## Sources

- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (flakes chapter, `nix flake` reference)
- `/nix/store/ccppgf5px2d3ig46swcqy0jkiq3nw5bm-nix-2.28.5-doc`
  (`nix3-flake`, `nix3-build`, `nix3-develop` man pages)
- `lib/flake.nix`, `lib/flake-version-info.nix` in the pinned nixpkgs
  source
