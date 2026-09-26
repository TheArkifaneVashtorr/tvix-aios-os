verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-05

## Read when

The pin has moved — a new nixpkgs rev, a new nix version, or both. This is the agent-facing
procedure behind spec §13; procedural reference, no idiom pair. Do not skip a step because a later
one looks like it would catch the same problem — each step catches a different failure mode.

## 1. Bump the lock

```bash cmd
nix flake update nixpkgs
```

Update the literal pinned rev everywhere it is asserted, not only in `./flake.lock`:
`checks/lock-guard.nix`'s expected rev (checked against `./flake.lock` by `lock-guard`), and
SKILL.md's "Pin" section (unverified — no check compares that prose to either literal). A stale
assertion in either place makes every later step below pass against the wrong claim.

## 2. Run the checks and expect red

```bash cmd
nix flake check -L --offline
```

`--offline` here is required, not incidental — but every check in this
suite already builds inside a Nix sandbox, where `nix` disables the same
network-dependent features on its own whenever `!haveInternet()`
(`src/nix/main.cc`), unconditionally true in a sandbox. So a plain,
un-flagged `nix config show` reports the same four values as `--offline`
does here; the check below proves the sandbox-forced defaults, not the
flag itself:

```bash verify
plain=$(NIX_CONFIG="experimental-features = nix-command" nix config show)
offline=$(NIX_CONFIG="experimental-features = nix-command" nix config show --offline)
[ "$plain" = "$offline" ] || {
  echo "refresh.md: plain vs --offline diverged in-sandbox — !haveInternet() claim is stale" >&2
  exit 1
}
for expected in 'connect-timeout = 1' 'download-attempts = 0' \
  'substitute = false' 'tarball-ttl = 4294967295'; do
  grep -qxF "$expected" <<<"$offline" || {
    echo "refresh.md: nix config show --offline no longer reports '$expected'" >&2
    exit 1
  }
done
```

What `--offline` itself provably does, even here, is honour
`!settings.X.overridden` on each of those four (same file): an
already-explicit nix.conf value survives the flag untouched — so it
never clobbers an operator's own config. Set via `NIX_CONFIG`, since
the sandbox has no ambient config file to override:

```bash verify
overrides='experimental-features = nix-command
substitute = true
connect-timeout = 5
download-attempts = 5
tarball-ttl = 3600'
values=$(NIX_CONFIG="$overrides" nix config show --offline)
for expected in 'connect-timeout = 5' 'download-attempts = 5' \
  'substitute = true' 'tarball-ttl = 3600'; do
  grep -qxF "$expected" <<<"$values" || {
    echo "refresh.md: --offline overrode an explicit setting — !overridden guard is stale" >&2
    exit 1
  }
done
```

(Unverified by CI, no check here has real internet: on a live shell at
this pin, with defaults untouched, plain `nix config show` gives
`connect-timeout = 0`, `download-attempts = 5`, `substitute = true`,
`tarball-ttl = 3600` — differs from the sandbox above only because
`haveInternet()` succeeds there.) That is nix's own help text for the
flag, pinned below, not restated here:

```bash verify
nix flake check --help 2>&1 | tr -s ' \t\n' ' ' | grep -qF \
  'Disable substituters and consider all previously downloaded files up-to-date.' || {
  echo "refresh.md: nix's own --offline help text no longer matches the quoted sentence" >&2
  exit 1
}
```

In short: no substitution, and anything cached already counts as
current, so a refresh measures the pin you declared. Two things it does
**not** stop, marked not demonstrated since neither reproduces inside a
network-less check: a first fetch of a never-seen URL (unverified by
CI, measured manually against a loopback server outside this repo), and
a fixed-output derivation's network access — whatever nix.conf(5)'s own
`sandbox` entry says, grepped verbatim below (its wording is what
matters, not a paraphrase):

```bash verify
phrase='fixed-output derivations do not run in private network'
phrase="$phrase namespace to ensure they can access the network"
zcat "$NIX_MAN_CONF" | tr -s ' \t\n' ' ' | grep -qF "$phrase" || {
  echo "refresh.md: nix.conf(5)'s sandbox entry no longer exempts" >&2
  echo "fixed-output derivations from the private network namespace" >&2
  exit 1
}
```

`checks/doctests.nix`'s static token gate and structural `outputHash`
check (spec §7) stand between a "nix package" block regaining a fetcher
and a build reaching the network — not this flag. Run it anyway, here
and in step 6: it keeps the refresh honest about the pin.

Immediately after step 1 this is *expected* to fail — `lock-guard` until
its literal is updated, `doctests`/`citations` wherever the pin changed
behaviour, `pin-renames` whenever it renamed an option or reshaped its
release notes. Nothing red here means nothing real changed or step 1
didn't take; don't treat an all-green first run as a shortcut.

## 3. Read the failure list

Read `pin-renames` first, before touching any content: it is the deprecation detector
doctests/citations cannot be, because it names a rename the moment it appears in
`nixos/modules/rename.nix` via any of `lib.mkRenamedOptionModule`, `lib.mkRenamedOptionModuleWith`,
`lib.mkAliasOptionModule`/`MD`, `lib.mkChangedOptionModule`, or `lib.mkMergedOptionModule` —
whether or not a reference cites the old path yet — and it lists every release-notes section id
and title the new pin added, dropped, or retitled. Any other `imports` entry it doesn't recognize
still fails the check, named by position — but a recognized `lib.mkRemovedOptionModule` removal
does not: it has no new path to record, so pin-renames stays green and `citations` is the only
thing left watching for a reference that still cites the removed path. Its failure message is
already the diff to act on (shape unverified): update every reference citing the old path, and its
release-notes counterpart. Fix the rename list before `doctests`/`citations`, since a rename it
just named is usually the root cause of several of their failures, not a separate one.

Or capture that diff as a file: `tools/auto-propose.py` (decision item 3's "auto-propose", per
S13's spec) writes `pin-renames`' renames/sections/`imports` diff plus `upstream-manifest`'s
missing-path list — not a `doctests`/`citations` list — to one file under `proposals/`, never
editing `skills/nixos/references/`. It cannot name a removed option either (same no-new-path reason
as pin-renames itself); `citations` alone still catches one, when a reference cites the removed
path. Exits non-zero on a missing manifest path either way. Exercised offline by
`tests/test_auto_propose.py` and `./flake.nix`'s `auto-propose` check; its live mode is not.

`doctests` names the exact `file:index` of every block that no longer evaluates, builds, or (`bash
cmd`) shellchecks — a rename surfaces here as a "nix module"/"nix expr" block throwing.
`citations` lists, per file, every option path, lib function name, `nix` subcommand/flag, and
`nixos/modules/...` path that no longer matches the new source — read the whole list first, since
one rename in module-system.md's priorities table can break three unrelated files that cite the
same name.

## 4. Fix each named file from the new pin's own sources

Never edit a block to make the check pass without first confirming the
new correct form against the pin itself — the nixpkgs source tree, the
rendered manual, and the nix docs, all at the *new* rev, the same way
this skill was written the first time:

```bash cmd
nix eval --impure --raw --expr \
  '(builtins.getFlake (toString ./.)).inputs.nixpkgs.outPath'
```

gives the new pin's nixpkgs source tree (module paths, `lib/*.nix`); the
manual and nix's own docs come from building against it directly rather
than trusting a memorised store path, since the hash changes with rev:

```nix expr
let
  nixosMin =
    modules:
    lib.nixosSystem {
      system = pkgs.system;
      modules = [
        {
          fileSystems."/".device = "/dev/null";
          boot.loader.grub.enable = false;
          system.stateVersion = "25.05";
          nixpkgs.hostPlatform = pkgs.system;
        }
      ] ++ modules;
    };
in
(nixosMin [ ]).config.system.build.manual.manualHTML.outPath
```

`pkgs.nix.doc`/`pkgs.nix.man` give the nix command and man pages the
same way, at whatever nix version this pkgs's `nix` package now is.

## 5. Re-stamp every file actually touched

Replace the `verified: nixpkgs … · nix … · …` first line with the new
rev, the new nix version (`nix --version`), and today's date — on every
reference and SKILL.md if either changed, not only the ones with a
failing check, since a reference that still evaluates fine can still be
citing a fact (a version number in prose, a behaviour description) that
quietly changed underneath it.

## 6. Rerun the checks until green

```bash cmd
nix flake check -L --offline
```

Same requirement as step 2, same caveat: `--offline` isn't baked into
any derivation here, so type it on every invocation, including this
fix-and-rerun loop — it stops Nix's own downloader, not a
fixed-output derivation's builder (step 2's measured breakdown). A "nix
package" block that regained a fetcher while options moved underneath
it is caught by `checks/doctests.nix`'s fetcher gates, not by this
flag; type it anyway, since it keeps this rerun honest about the pin.

## 7. Rerun the isolation probe

The probe (spec §9) depends on the installed SKILL.md's content — if
this refresh touched SKILL.md at all, the symlinked install already
sees the new file, but the probe itself has not re-run since (an
operator step, unverified by any check here). Rerun it before trusting
any eval numbers gathered after this refresh; a stale probe result from
before the refresh proves nothing about the file now installed.

## 8. Rerun the evals and record the delta

Run the same eval matrix again (`tools/run-evals.sh` — a separate
budget-spending step, never triggered automatically by a refresh, and
unverified by any check here) and compare the new results file's
per-cell pass rates, token and time distributions against the previous
one; note the delta — improved, regressed, or unchanged within the
confidence interval — alongside the new results, so a later refresh has
the same trend line to check against, not just the latest snapshot.

## Sources

- `pkgs.nix.doc` at this pin (`nix3-flake-lock`, `nix3-flake-check`) —
  its store path lives in exactly one place, the block below, so it
  cannot drift out of sync with a second copy
- `nixos/modules/rename.nix` — the deprecation helpers step 3's
  `pin-renames` paragraph names (`lib.mkRenamedOptionModule` and the
  rest)

`pkgs.nix.doc`'s own `outPath` at this pin, and confirmation `pkgs.nix`
still has the `.man` output step 4 also cites:

```nix expr
if
  pkgs.nix.doc.outPath == "/nix/store/ccppgf5px2d3ig46swcqy0jkiq3nw5bm-nix-2.28.5-doc"
  && pkgs.nix ? man
then
  true
else
  throw ''
    refresh.md: pkgs.nix.doc's store path changed (or pkgs.nix lost its
    .man output) — re-verify this Sources entry and step 4's
    pkgs.nix.doc/pkgs.nix.man claim against the new pin''
```
