verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Any eval, build, or exec failure.

## `--show-trace`

By default, Nix collapses a run of repeated "while evaluating …"/"while
calling …" frames above the final `error:` line into one `(N duplicate
frames omitted)` line; `--show-trace` prints every frame instead. It is
a real, working flag on every evaluating command at this pin (it sets
the documented `show-trace` nix.conf setting, and any such setting is
also exposed as a generic `--<name>` command-line flag) — but it never
appears in `nix eval --help`'s own text, so this reference's flag
check (every `--flag` on a `nix` line verified against that
subcommand's own `--help`) cannot see it, which is why the command
below leaves it off so the line stays checked; add `--show-trace`
yourself when a real trace is deep enough to collapse (the
infinite-recursion example just below is only two frames — too shallow
for the collapsing, and so too shallow to show a difference either
way):

```bash cmd
nix eval --offline --impure --expr 'let x = { a = x.a; }; in x.a'
```

## `nix repl` on a flake

`nix repl .` loads the current directory's flake outputs as REPL
variables (`legacyPackages`, `nixosConfigurations`, …); `nix repl
--expr 'import <nixpkgs> {}'` loads a plain (non-flake) package set the
same way. Once inside, `:r` reloads after an edit, `:q` quits — faster
than a full `nix eval` per attempt when narrowing down which attribute
in a large expression is wrong.

## `nix eval --json`

Machine-readable output for scripting or for pasting an exact value
into a bug report — pairs with the devShell's `python3 -m json.tool`.

```bash cmd
nix eval --offline --json --expr '{ x = 1; }'
```

## `nix why-depends`, `nix log`, `nix path-info -rSh`

Covered in full in the nix-cli reference; the debugging-specific use:
`nix why-depends --derivation <a> <b>` when a closure is bigger than
expected and you need to know which input pulled in which; `nix log
<drv-or-path>` to read a *previous* build's output without rebuilding
(the message a sandboxed build failure leaves is often the only
evidence, since the sandbox is gone once the builder exits); `nix
path-info -S <path>` alone only prints one number, the whole closure's
total size — to see whether a suspiciously large closure is one big
output or many small ones added up, add `-r` for a per-path breakdown:
`nix path-info -rSh <path>`.

## Infinite recursion

`config`/`options` reference each other lazily; reading a value back
out of its own definition (see the module-system reference's recursion
trap) or any other true self-reference produces this, not a stack
overflow:

```text
$ nix eval --impure --expr 'let x = { a = x.a; }; in x.a'
error:
       … while evaluating the attribute 'a'
         at «string»:1:11:
            1| let x = { a = x.a; }; in x.a
             |           ^

       … while evaluating the attribute 'a'
         at «string»:1:11:
            1| let x = { a = x.a; }; in x.a
             |           ^

       error: infinite recursion encountered
       at «string»:1:11:
            1| let x = { a = x.a; }; in x.a
             |           ^
```

## "attribute … missing" vs "option … does not exist"

Both mean "that name is not there", from two different evaluators: a
plain attribute-set lookup failing (`{ a = 1; }.b`) says "attribute 'b'
missing" — the nix-language reference has the exact form. A NixOS
**module system** lookup failing (a typo'd option path anywhere under
`config`/`options`, including inside a `nixosTest` node) says "The
option 'foo.bar' does not exist" instead, because the module system
validates every defined path against every declared option before it
ever becomes a plain attribute set — see the vm-tests reference for the
exact text from a typo'd node option. Seeing "attribute … missing"
where you expected "option … does not exist" (or the reverse) usually
means the path you are on is not where you think: plain Nix attrset vs.
evaluated module `config`.

## Sandbox failures

A build sees only its declared inputs and `$TMPDIR`/`$out` — nothing
else on the host filesystem, network included (the one exception is a
fixed-output derivation's own fetch; see the packaging reference). A
build reaching for an undeclared host path fails from inside the
builder, not from Nix itself, and `nix log` is how you read that
failure after the fact:

```text
$ nix build --offline .#sandbox-demo   # builder: cat /etc/hostname > $out
error: builder for '/nix/store/...-sandbox-demo.drv' failed with exit
       code 1; last 1 log lines:
       > cat: /etc/hostname: No such file or directory
       For full logs, run:
         nix log /nix/store/...-sandbox-demo.drv
```

## Import-from-derivation (IFD)

`import` (or *builtins.readFile*, string interpolation, …) on a
derivation's output forces that derivation to build **during
evaluation**, before the rest of the expression can proceed — useful,
but a build every eval pays for and a common source of "why is this
`nix flake check` so slow". `nix eval --option
allow-import-from-derivation false` turns it into a hard error instead
of a silent build, which is how to find every IFD site in an
expression:

```text
$ nix eval --impure --option allow-import-from-derivation false \
    --expr 'import (derivation-that-produces-a-nix-file)'
error: cannot build '/nix/store/....drv^out' during evaluation because
       the option 'allow-import-from-derivation' is disabled
```

## Foreign dynamically-linked binaries

A prebuilt binary from outside the store (a downloaded release, a
language ecosystem's own installer) is linked against
`/lib64/ld-linux-x86-64.so.2` or similar — a path that does not exist
on NixOS, whose libraries all live under hashed `/nix/store` paths
instead. Running it directly fails as "Could not start dynamically
linked executable" (or a plain exit 127, depending on the shell) even
though the file is present and executable — the shell is reporting the
*interpreter's* absence, not the binary's. `programs.nix-ld.enable`
installs a real loader at a fixed path and points `NIX_LD`/
`NIX_LD_LIBRARY_PATH` at it (env vars `environment.sessionVariables`
already sets); `programs.nix-ld.libraries` is the extra shared library
set the foreign binary needs beyond nix-ld's own defaults (`zlib`,
`pkgs.stdenv.cc.cc`, `openssl`, `systemd`, …) — the loader itself is
glibc's own dynamic linker, symlinked in separately by the module, not
a member of that list.

```nix module
{ pkgs, ... }:
{
  programs.nix-ld.enable = true;
  programs.nix-ld.libraries = [ pkgs.zlib ];
}
```

Verify a binary through the real loader before shipping the
configuration that needs it — do not add libraries speculatively:

```bash cmd
"$NIX_LD" --library-path "$NIX_LD_LIBRARY_PATH" ./foreign-binary --version
```

nix-ld exists to run an already-trusted foreign binary locally; it is
never a reason to relax any network-egress control this machine
enforces elsewhere — what a binary can link against and what it can
reach over the network are unrelated questions.

## Sources

- `/nix/store/ccppgf5px2d3ig46swcqy0jkiq3nw5bm-nix-2.28.5-doc`
  (evaluation errors, `--show-trace`, IFD)
- `nixos/modules/programs/nix-ld.nix` (`NIX_LD`, `NIX_LD_LIBRARY_PATH`,
  default `libraries`)
