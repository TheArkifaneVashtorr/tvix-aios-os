---
plan_defect: implementer
mutants_total: 15
mutants_killed: 12
mutants_outside_named: 1
reviewer: opus
majors: 9
minors: 7
---
# Opus gate — seat run cx1, task CX1 — REJECTED

## Summary

Codex produced a well-shaped 13-file flake with the right skeleton, an honest
`docs/VALIDATION.md`, no secrets, a real nixpkgs pin, a correct npm URL and a
tree that is byte-clean under its own `treefmt.toml`. Every red/green claim it
made reproduces exactly. That is the good half.

As handed over the deliverable does not evaluate at all: not one of the 13
files is tracked by git, so the brief's literal Done-means command
`nix build ~/flakes/codex#codex` dies at flake resolution before any other
defect can bite (MAJOR-8). Every number in this review was taken on a tree the
reviewer staged.

Once staged, the tree still fails the brief's "Done means" on all three
measurable clauses, for reasons that survive lifting every sandbox blocker.
With the real hash substituted (`sha256-VIGMufzjNgzG5Ez8WpaVLNXBJD77Q8vkiOEd2oRmPgg=`)
the package does not build: it wraps `vendor/x86_64-unknown-linux-musl/codex/codex`,
a path the archive does not contain (the archive's own `codex-package.json`
declares `"entrypoint": "bin/codex"`), and after that is repaired it fails again
on `libtinfo.so.6`. The flake does not even *evaluate*: `pkgs.nodePackages.prettier`
was removed from the pinned nixpkgs, which takes out `formatter`, `devShells` and
the `lint` check. And `nix flake check` can never be green, because
`config-rejects-typo` is shipped permanently red by design.

The decisive implementer finding is that last one, and it is not a sandbox
casualty. `codex --strict-config` **does** reject misspelt keys — under
`codex exec`, where the typo config yields ``unknown configuration field
`sandbox_workspace_write.network_acess` `` and exit 1 while the rendered config
proceeds. Codex probed `doctor`, then `features` (log:2383, "not supported"),
concluded the binary was at fault, and shipped a check it knew would stay red
rather than trying the next subcommand. Its mirror-image defect is that the green
half is vacuous: `config` only asserts `checks["config.load"].status == "ok"`, and
that field reads `ok` for a config full of misspelt keys — so it proves the TOML
parses and nothing more. Requirement 3 is met by neither half.

One major is *not* the implementer's. Requirement 2 rests on a false premise:
`/etc/codex/config.toml` is a defaults layer that any user's `~/.codex/config.toml`
silently overrides. The file the brief asks for cannot deliver the hardening the
brief asks it to deliver; the layer that outranks the user file is
`/etc/codex/managed_config.toml` (MAJOR-9, measured).

Verdict: REJECTED. `plan_defect: implementer` — majors 3, 5, 6 and 7 need no
lifted blocker to find and carry the verdict on their own. Secondary, and
mandatory for the fix round: the brief carries a **wrong-fact** defect (MAJOR-9),
so CX1b must not simply re-implement requirement 2 as written.

## Contract items

The brief (`/home/dalhaka/factory/probe/codex-first-task.md`), taken literally.

1. **`packages.x86_64-linux.codex` — pinned by hash, fetched from the published
   `@openai/codex` linux-x64 release, autoPatchelf'd, wrapped with `bubblewrap`
   and `ripgrep` on PATH; a bump is one version string and one hash.**
   NOT MET.
   - URL: MET, and correct. `https://registry.npmjs.org/@openai/codex/-/codex-0.153.4-linux-x64.tgz`
     resolves (129,272,137 bytes); the platform package's `package.json` carries
     `"version": "0.153.4-linux-x64"`, which is why the suffixed filename is right.
     No separate `@openai/codex-linux-x64` scope is needed.
   - Hash: NOT MET as landed — `hash = lib.fakeHash`.
   - Build: NOT MET. See MAJOR-1 and MAJOR-2; two independent failures. And
     nothing builds at all before `git add -A` (MAJOR-8).
   - Wrapper: MET *once it builds*, and unchecked. The wrapper prefixes
     `ripgrep-15.1.0/bin` and `bubblewrap-0.11.2/bin`. No check exercises it
     (MAJOR-7; mutants M5b, M6b survive).
   - "one version string and one hash": MET in shape —
     `url` interpolates `finalAttrs.version`, and M10 (version bumped, hash not)
     is caught by the fetch (`curl: (22) ... 404`).
2. **`nixosModules.default` — installs the package and renders
   `/etc/codex/config.toml` with the four settings; leave
   `check_for_update_on_startup` alone.**
   NOT MET — met to the letter, void in effect (MAJOR-9). The rendered file is
   exactly:
   ```toml
   [features]
   plugins = false

   [otel]
   exporter = "none"
   metrics_exporter = "none"
   trace_exporter = "none"

   [sandbox_workspace_write]
   network_access = false
   ```
   `check_for_update_on_startup` is absent. `environment.systemPackages = [ cfg.package ]`.
   But `/etc/codex/config.toml` is a *defaults* layer: a user's
   `~/.codex/config.toml` silently overrides all four settings (measured,
   MAJOR-9), so the hardening is unenforced against exactly the file the brief
   says it outranks. Coverage is also partial on the Nix side: `module-eval`
   asserts `plugins`, `otel.metrics_exporter` and `network_access`, but not
   `otel.exporter` or `otel.trace_exporter` — mutant M2 survives — and no check
   ever places the file at `/etc/codex/` (MINOR-7).
3. **A check that the rendered config passes `codex --strict-config doctor`, red
   first: prove a config with a misspelt key makes the check fail before the real
   one makes it pass.**
   NOT MET, both halves. The red half (`config-rejects-typo`) is shipped red and
   stays red (MAJOR-3). The green half (`config`) is vacuous (MAJOR-5). The
   requirement is achievable — measured below.
4. **A formatter and a linter for every language introduced, wired into
   `treefmt.toml` and a pre-commit hook, in the same commit as the language.**
   NOT MET. Nix (nixfmt + statix + deadnix), shell (shfmt + shellcheck),
   TOML (taplo fmt + taplo check), Markdown (prettier + markdownlint), JSON
   (prettier --write + prettier --check) are all wired, and every arm genuinely
   kills a mutant once the check can run (M8, M9c, M13, M14, M15b, M16). But the
   `lint` check cannot run at all as shipped (MAJOR-6), the flake it lives in does
   not evaluate (MAJOR-4), there are no commits (MAJOR-8), and "in the same
   commit" is unreachable *by construction*: the shipped `githooks/pre-commit`
   runs `nix flake check`, which can never be green while `config-rejects-typo`
   exists (MINOR-6).

**Done means:**
- `nix build ~/flakes/codex#codex` prints `codex-cli 0.153.4` — NOT MET as
  submitted; MET after `git add -A` plus three one-line source repairs (real
  hash, `bin/codex` entrypoint, `ncurses`) — measured: `codex-cli 0.153.4`,
  exit 0.
- `nix flake check` green — NOT MET, and unreachable without changing
  `config-rejects-typo` (and without the `prettier` and lint-cache repairs).
- module evaluates in `nixosConfigurations.test` — MET (evaluation only; the
  rendered layer is ineffective, MAJOR-9).
  `nix eval $S/tree#nixosConfigurations.test.config.system.build.toplevel.drvPath`
  -> `"/nix/store/dq25y0pj3g2b4r1nad140gc8f1h18pia-nixos-system-nixos-26.05.20260903.a5cc6f2.drv"`.
- README says how to bump — MET, and the recipe it gives is the command that
  actually produced the real hash.

## Majors

**MAJOR-1 — the package does not build: wrong entrypoint path.**
`pkgs/codex/default.nix` `postFixup` wraps
`$out/libexec/codex/vendor/x86_64-unknown-linux-musl/codex/codex`.
`tar tzf` of the real archive has no `codex/` directory; `codex-package.json`
inside it declares `"entrypoint": "bin/codex"`.
```
$ nix build $S/tree#codex -L
codex> Builder called die: Cannot wrap '/nix/store/36z5.../libexec/codex/vendor/
       x86_64-unknown-linux-musl/codex/codex' because it is not an executable file
error: builder failed with exit code 1
```
Reproduced independently by the second reader down to the same failing store
path (`36z5vyxq91bka9jsk4l1ap9x7a19v3g2-codex-0.153.4`), and the archive has
exactly 8 members with zero matches for the wrapped path.
Fix: `.../bin/codex`. (`installPhase`'s `cp -R vendor` is correct — the npm
tarball's `package/` prefix is stripped by the default `sourceRoot`.)

**MAJOR-2 — the package does not build: missing `ncurses`.**
With MAJOR-1 repaired:
```
> setting interpreter of .../codex-resources/zsh/bin/zsh
>     libtinfo.so.6 -> not found!
> error: auto-patchelf could not satisfy dependency libtinfo.so.6 wanted by
>   .../codex-resources/zsh/bin/zsh
```
`buildInputs = [ stdenv.cc.cc.lib ]` is not enough: the bundled zsh is the one
glibc-dynamic file in the archive (`patchelf --print-needed` -> `libtinfo.so.6
libm.so.6 libc.so.6`). Adding `ncurses` to `buildInputs` builds, and
`./result/bin/codex --version` then prints `codex-cli 0.153.4`. Both readers
reached the same repaired output path
(`s6k7w1wczssrb464sp6xqzdrmrl9fj6m-codex-0.153.4`).
Note the ordering trap that hid this from the first failure: `runHook postFixup`
runs the `postFixup` *attribute* before `postFixupHooks`, so `makeWrapper` died
before autoPatchelf ever ran.

**MAJOR-3 — `nix flake check` is red by construction, and the requirement it
gives up on is achievable.**
On the fully repaired tree (`$S/tree-m`), four checks pass and one does not:
```
version 0 | config 0 | module-eval 0 | lint 0 | config-rejects-typo 1
codex-config-typo> false
```
Codex documented this as an upstream limitation. It is not. `--strict-config` is
wired per subcommand — it is explicitly refused for `mcp`, `features`, `plugin`,
`login` and `sandbox` — and under `exec` it does exactly what the brief asked:
```
valid + --strict-config exec --sandbox read-only --skip-git-repo-check hi
  -> OpenAI Codex v0.153.4 / model: gpt-6-astra          (config accepted)
typo  + --strict-config exec --sandbox read-only --skip-git-repo-check hi
  -> Error loading config.toml:
     .../config.toml:10:1: unknown configuration field `sandbox_workspace_write.network_acess`
        |
     10 | network_acess = false
        | ^^^^^^^^^^^^^
typo  without --strict-config -> accepted, runs
```
Codex tried `doctor`, then `features` (log:2383 -> log:2394, "not supported"),
and stopped. `exec` was one subcommand away. Shipping a check known to be red
also violates the local rule that `nix flake check` is the gate.

**MAJOR-4 — the flake does not evaluate: `pkgs.nodePackages.prettier`.**
```
$ nix flake check $S/tree -L
checking flake output 'formatter'...
error: nodePackages has been removed. Many packages are now available at the
top level (e.g. `pkgs.package-name`).
```
This takes out `formatter`, `devShells.default` and `checks.lint`. In the pinned
nixpkgs the attribute is `pkgs.prettier` (3.8.3); `nodePackages` was removed
`# Added 2026-03-03`. Codex "verified" prettier by running
`/nix/store/adglp5s...-prettier-3.9.6/bin/prettier` — a *host* store path under a
*different* version, not its own pin (log:2825; log:2609 shows
`nodePackages.prettier` going into the flake unverified). The same class of
error was not made for the other eight tools, which all exist under the names
used.

**MAJOR-5 — the green half of requirement 3 is vacuous.**
`tests/doctor.sh` valid mode asserts only
`jq -e '.checks["config.load"].status == "ok"'`. Measured, in a disposable
HOME/CODEX_HOME with no login:

| config | doctor exit | `config.load.status` |
| --- | --- | --- |
| rendered config | 1 | `ok` |
| `network_acess` under `[sandbox_workspace_write]` | 1 | `ok` |
| an unknown extra key (`misspelt_top_key = 1`) | 1 | `ok` |

Exit 1 in all three rows comes from `auth.credentials=fail` plus
`network.websocket_reachability=warning`, i.e. environment, not config.
`config.load` goes non-`ok` only when the TOML fails to *parse*. So the check
that is supposed to prove "the rendered config passes `--strict-config doctor`"
proves "the rendered config is syntactically valid TOML". Mutant M2 —
`otel.exporter` rendered as `exporterr` — passes `config`, passes `module-eval`,
passes `lint`, and would silently leave the OTel exporter enabled on the host.

**MAJOR-6 — the `lint` check cannot run: `TREEFMT_CACHE_DIR` does not exist.**
```
codex-lint> Error: failed to open cache: could not resolve local path for the cache:
  could not create any of the following paths: [/homeless-shelter/.cache/treefmt/eval-cache]
$ treefmt --help | grep -c TREEFMT_CACHE_DIR
0
```
treefmt 2.6.0 offers `--no-cache` (`TREEFMT_NO_CACHE`), `--ci`, `-c/--clear-cache`
and honours `XDG_CACHE_HOME`; there is no `TREEFMT_CACHE_DIR`. Requirement 4's
gate is inert as shipped. With `XDG_CACHE_HOME="$TMPDIR/cache" --no-cache` it
passes (`traversed 13 files / emitted 12 / formatted 12 files (0 changed)`,
exit 0) and every language arm kills its mutant — the wiring is right, the
plumbing is not.

**MAJOR-7 — nothing checks the one runtime property the brief called out.**
"wrap it with `bubblewrap` and `ripgrep` on PATH."
Removing `bubblewrap` (or `ripgrep`) from the wrapper's `makeBinPath` *and* from
the lambda arguments leaves all five checks at their baseline verdicts (M5b, M6b
survive, re-formatted with nixfmt so the mutation is isolated). Removing only the
`makeBinPath` entry is caught, but incidentally, by deadnix ("Unused lambda
pattern: bubblewrap") — a lint accident, not a contract test. The `version` check
runs the wrapper but `--version` does not touch bwrap.
Qualification, established on re-measurement: the brief's "you panic without
`bwrap`" is no longer true of 0.153.4, which bundles its own bwrap and rg — with
`PATH=/var/empty` the unwrapped binary still reports
`runtime.search=ok :: search is OK (bundled)` and `sandbox.helpers=ok`. So this
is an **untested-contract** gap (the brief demanded the wrapper and nothing
asserts it), not a latent runtime hazard. The fix-round item stands; the
justification changes.

**MAJOR-8 — the deliverable does not evaluate as handed over: nothing is tracked
by git.** All 13 files are `??`; `git -C /home/dalhaka/flakes/codex count-objects
-v` -> `count 0, in-pack 0` (no objects at all). Flakes only see tracked files,
so the brief's literal Done-means command fails at resolution, before MAJOR-1/2/4
can be reached:
```
$ nix build $S/asub#codex -L
error: Path 'flake.nix' in the repository "..." is not tracked by Git.
       To make it visible to Nix, run: git -C "..." add "flake.nix"
$ nix flake check $S/asub
(the same error, exit 1)
```
This is the *first* failure of the submission, ahead of MAJOR-1. It also makes
requirement 4's "in the same commit as the language" and the
`<area>: summary (test: <check names>)` convention unevaluable. Caused by the
read-only `.git` (log:285/287/408), which is a real blocker — but a deliverable
that cannot be evaluated by its own acceptance command is a defect of the
handover, not a waiver. Every measurement in this review was taken after the
reviewer staged the tree in a scratch copy.

**MAJOR-9 — the brief's premise for requirement 2 is factually wrong:
`/etc/codex/config.toml` does not outrank `~/.codex/config.toml`.**
It is a *defaults* layer; a user config silently overrides it, so the module's
hardening (`plugins = false`, the three OTel exporters, `network_access = false`)
is unenforced against exactly the file the brief says it outranks. The layer that
does outrank the user file is `/etc/codex/managed_config.toml`.
Measured with the Nix-built 0.153.4 inside an unprivileged bwrap namespace
(`bwrap --dev-bind / / --tmpfs /etc --ro-bind <fixture> /etc/codex ...`; the host
has no `/etc/codex` and none was created). Fixtures: system file
`model="system-layer-model"`, `plugins=false`, `network_access=false`; user file
(`CODEX_HOME/config.toml`) `model="user-layer-model"`, `plugins=true`,
`network_access=true`. From `doctor --json` `.checks["config.load"].details` plus
the `exec --sandbox workspace-write` banner:

| fixture | model in effect | plugins override | sandbox banner |
| --- | --- | --- | --- |
| system only | `system-layer-model` | `plugins=false` | workspace-write |
| system vs user | **`user-layer-model`** | **none** | **network access enabled** |
| managed only | `system-layer-model` | `plugins=false` | workspace-write |
| managed vs user | `system-layer-model` | `plugins=false` | workspace-write |
| user only | `user-layer-model` | none | network access enabled |

Corroborating: the binary's string table carries `/etc/codex/config.toml`,
`/etc/codex/requirements.toml` and `/etc/codex/managed_config.toml`, and
`codex sandbox --help` documents `--include-managed-config` ("Include managed
requirements while resolving an explicit permissions profile"); `codex --help`
documents config only as "loaded from `~/.codex/config.toml`" and states no
precedence. `plan_defect` for this one is **wrong-fact**, against the brief, not
the implementer — though note the implementer could have measured it: the binary
was on PATH for the whole run, it invoked it 17 times, and it ran `ls /etc/codex`
at log:326. A CX1b that implements requirement 2 exactly as written will ship a
system config any user overrides.

## Minors

**MINOR-1 — VALIDATION.md overstates what was measured.** It says "Both
`nix build path:/home/dalhaka/flakes/codex#codex` and `nix flake check
path:/home/dalhaka/flakes/codex` failed before evaluation". Neither command
appears anywhere in the 2940-line transcript; a `grep -nE 'nix (build|flake
check|eval|store ping)'` over it hits prose and README lines only (20, 72-73,
119, 2532, 2688-2691, 2732-2734, 2868-2869) plus the one real invocation. The
only nix invocation Codex ran is `nix store ping` (log:326), which produced the
socket error at log:406. The conclusion is right; the evidence cited for it was
not gathered.

**MINOR-2 — the pre-commit hook is not installed by anything.** `githooks/pre-commit`
exists and is executable; the README tells the operator to run `git config
core.hooksPath githooks` by hand. Matches `~/nixos-agent-env`'s own habit, so
minor — but the brief said "wired into ... a pre-commit hook", and nothing wires it.

**MINOR-3 — `tests/lint-nix.sh` is mode 644** while `doctor.sh` and `version.sh`
are 755. Harmless (it is invoked as `bash tests/lint-nix.sh`), but inconsistent.

**MINOR-4 — the module's default package is a second instantiation.**
`programs.codex.package` defaults to `pkgs.callPackage ../pkgs/codex { }`, which
resolves against the *consumer's* nixpkgs, not the flake's pin. A downstream host
importing `nixosModules.default` gets an unpinned rebuild. The flake never sets
`programs.codex.package = self.packages.${system}.codex`.

**MINOR-5 — the config checks are brittle by construction.** `tests/doctor.sh`
tolerates doctor exit codes ≤ 1 and fails loudly above that; doctor's exit code
is driven by auth and network health, which are environment, not config. Any
future doctor check that exits > 1 inside the nix sandbox turns `config` red for
reasons unrelated to the config. Relatedly, the typo mutation is
`sed -i 's/network_access/network_acess/'`: if the module ever stops rendering
that key the sed silently no-ops and the check compares an unmodified valid
config.

**MINOR-6 — the shipped hook makes committing impossible, so requirement 4 is
unreachable by design.** `githooks/pre-commit` lines 5-6 run `nix fmt --
--fail-on-change` then `nix flake check`. On the fully repaired tree
`nix build .#checks.x86_64-linux.config-rejects-typo` -> `codex-config-typo>
false`, exit 1, and `tests/doctor.sh` typo mode can only pass if doctor reports
`config.load="fail"`, which it does only for unparseable TOML (a key-renaming sed
leaves valid TOML and yields `ok`). So `nix flake check` is red for every tree
state that still contains this check: once the operator follows README.md's
`git config core.hooksPath githooks`, no commit can ever succeed. Corollary of
MAJOR-3; recorded separately because it means "in the same commit as the
language" was not merely unevaluated but foreclosed.

**MINOR-7 — requirement 3's checks never exercise the file the module writes.**
`tests/doctor.sh:9-10` copies the rendered config into a disposable CODEX_HOME
(`mkdir -p "$work_dir/codex"` / `cp "$config_file" "$work_dir/codex/config.toml"`,
then `CODEX_HOME="$work_dir/codex"`), i.e. validates it as a *user* config;
nothing ever places it at `/etc/codex/`. `codex doctor` cannot validate that layer
anyway — in the bwrap run with only `/etc/codex/config.toml` present and an empty
CODEX_HOME, doctor's `config.load` details report
`"config.toml": ["<CODEX_HOME>/config.toml","missing"]` while the system file's
values *were* applied. The layer is read and never named in the report the check
greps. Compounds MAJOR-9.

## Mutation table

Base for every row is `$S/tree-m` = the submitted tree + `git add -A` + the
reviewer's repairs (real hash, `bin/codex` entrypoint, `ncurses`, `prettier`,
lint cache), whose baseline is `version 0 / config 0 / module-eval 0 / lint 0 /
config-rejects-typo 1`. Without the staging nothing resolves and without the
repairs no check can run, so the table measures the *design's* coverage, not the
submission's.

| # | Mutant | Brief names it? | Caught by | Killed |
| --- | --- | --- | --- | --- |
| M1 | module: drop `features.plugins = false` | yes (req 2) | `module-eval` assert | yes |
| M2 | module: render `otel.exporter` as `exporterr` | yes (req 2) | — | **no** |
| M3 | module: `network_access = true` | yes (req 2) | `module-eval`: `assertion '(! ...network_access)' failed` | yes |
| M7 | module: render `network_acess` (misspelt) | yes (req 2/3) | `module-eval` (missing attribute) | yes |
| M12 | module: drop `environment.etc."codex/config.toml"` | yes (req 2) | `config`, `config-rejects-typo`, `module-eval` | yes |
| M5b | pkg: `bubblewrap` removed from wrapper PATH **and** args | yes (req 1) | — | **no** |
| M6b | pkg: `ripgrep` removed from wrapper PATH **and** args | yes (req 1) | — | **no** |
| M10 | pkg: version bumped, hash untouched | yes (req 1) | fetch: `curl: (22) ... 404` → `version`/`config`/`config-rejects-typo` | yes |
| M11 | `flake.lock`: narHash corrupted | no | every check, exit 102 | yes |
| M8 | `flake.nix`: formatting broken | yes (req 4) | `lint` (nixfmt) | yes |
| M15b | module: `[ ] ++ [ cfg.package ]` | yes (req 4) | `lint` (statix, "Unnecessary concatenation with empty list") | yes |
| M9c | `tests/version.sh`: unquoted `$f` in a loop | yes (req 4) | `lint` (shellcheck SC2086) | yes |
| M13 | `docs/MAP.md`: h2 → h4 jump | yes (req 4) | `lint` (markdownlint MD001) | yes |
| M14 | `treefmt.toml`: duplicate `[formatter.nix]` | yes (req 4) | `lint` ("table nix already exists") | yes |
| M16 | `flake.lock`: JSON reflowed to one line | yes (req 4) | `lint` (prettier `json-lint`) | yes |

`mutants_total: 15`, `mutants_killed: 12`, `mutants_outside_named: 1` (M11).
M2, M5b and M6b were each re-run independently by the second reader and produced
a per-check table identical to the baseline.

Two candidate mutants were discarded after checking the tool rather than the
tree: `actual=$($1 --version)` (shellcheck 0.11.0 exits 0 — it does not report an
unquoted expansion in command position) and `cfg.enable == true` (statix flags
only literal-vs-literal boolean comparison; it does flag `[ ] ++ [ x ]`, exit 1).
Both are tool behaviour, not gaps in the tree.

Survivor summary: the three live mutants are all in the two places the brief was
most explicit — the OTel exporter keys and the bwrap/rg wrapper — and all three
are invisible to every check the tree ships. A fourth class of mutation is
untestable by anything in the tree at all: the precedence of the rendered
`/etc/codex/config.toml` (MAJOR-9, MINOR-7).

## Red before green

Every red/green claim in `docs/VALIDATION.md` was re-run against the
Nix-built binary (Codex ran them against `~/.local/bin/codex`). All four
reproduce, with the same exit codes, in both readers' runs:

```
$ bash tests/version.sh $S/result-fixed/bin/codex 0.149.0
Expected codex-cli 0.149.0; got codex-cli 0.153.4
exit=1
$ bash tests/version.sh $S/result-fixed/bin/codex 0.153.4
exit=0
$ bash tests/doctor.sh <bin> <rendered config> valid      -> true    exit=0
$ bash tests/doctor.sh <bin> '[features' valid            -> false   exit=1
$ bash tests/doctor.sh <bin> <rendered config> typo       -> false   exit=1
```

The `lint` arms were never shown to fail by Codex — VALIDATION.md says so
plainly ("Passing static tools without demonstrated failures are not counted as
tests"). This review supplied the missing reds: M8, M9c, M13, M14, M15b, M16 all
turn `lint` red on the repaired tree, so the arms are load-bearing once the check
can run (independently re-confirmed: a nixfmt-breaking edit and an SC2086 in
`tests/version.sh` each take `lint` to exit 1).

Honest accounting: the version and malformed-TOML reds are real. The typo red is
real but permanent — a test that has only ever been red is not a red-then-green
proof, it is an unfinished one, and the brief's rule ("a test counts only once it
has been shown to fail") does not convert a check that cannot pass into a
passing gate.

## Facts measured

| Fact | Value |
| --- | --- |
| Real archive hash | `sha256-VIGMufzjNgzG5Ez8WpaVLNXBJD77Q8vkiOEd2oRmPgg=` |
| URL Codex assumed | `https://registry.npmjs.org/@openai/codex/-/codex-0.153.4-linux-x64.tgz` |
| URL that exists | the same one — **correct**; 129,272,137 bytes; `package.json` `"version": "0.153.4-linux-x64"`, `"license": "Apache-2.0"` (so `meta.license = asl20` is right) |
| Archive layout | 8 members: `package/vendor/x86_64-unknown-linux-musl/{bin/codex, bin/codex-code-mode-host, codex-path/rg, codex-resources/bwrap, codex-resources/zsh/bin/zsh, codex-package.json}` |
| Declared entrypoint | `codex-package.json`: `"entrypoint": "bin/codex"` (package expects `codex/codex`) |
| Tracked files in the deliverable | **none** — `count-objects -v` → `count 0, in-pack 0`; `nix build` → "Path 'flake.nix' ... is not tracked by Git" |
| Build, as submitted (staged, real hash) | **FAIL** — `Cannot wrap '.../codex/codex' because it is not an executable file` |
| Build, entrypoint repaired | **FAIL** — `auto-patchelf could not satisfy dependency libtinfo.so.6` |
| Build, + `ncurses` | **OK** |
| `./result/bin/codex --version` | `codex-cli 0.153.4` (exit 0) — the brief's literal string |
| Wrapper PATH | prefixes `ripgrep-15.1.0/bin` and `bubblewrap-0.11.2/bin`; execs `.../bin/codex` |
| Bundled sandbox survives autoPatchelf/strip | `codex sandbox -- /bin/sh -c 'echo SANDBOX_OK; touch /etc/should-fail'` → `SANDBOX_OK`, then `Read-only file system`, exit 0 |
| `bwrap`/`rg` needed on PATH? | no in 0.153.4 — with `PATH=/var/empty` the unwrapped binary reports `runtime.search=ok (bundled)`, `sandbox.helpers=ok` |
| `nix flake check $S/tree` | **FAIL** at `checking flake output 'formatter'` — `error: nodePackages has been removed` |
| `checks.version` (submitted) | FAIL (package build) |
| `checks.config` (submitted) | FAIL (package build) |
| `checks.config-rejects-typo` (submitted) | FAIL (package build) |
| `checks.module-eval` (submitted) | **PASS** |
| `checks.lint` (submitted) | FAIL at eval (`nodePackages`) |
| `nixosConfigurations.test` toplevel drvPath | `/nix/store/dq25y0pj3g2b4r1nad140gc8f1h18pia-nixos-system-nixos-26.05.20260903.a5cc6f2.drv` |
| Same five checks, fully repaired | `version` PASS, `config` PASS, `module-eval` PASS, `lint` PASS, `config-rejects-typo` **FAIL** |
| `doctor --strict-config --json`, valid config | exit 1 (auth), `config.load = ok` |
| same, `network_acess` typo | exit 1, `config.load = ok` |
| same, unknown extra top-level key | exit 1, `config.load = ok`, summary "config loaded" |
| `--strict-config exec`, valid config | proceeds; `model: gpt-6-astra` |
| `--strict-config exec`, typo config | ``unknown configuration field `sandbox_workspace_write.network_acess` ``, exit 1 |
| `exec` without `--strict-config`, typo config | accepted |
| `/etc/codex/config.toml` vs `~/.codex/config.toml` | **user wins** (model, plugins and workspace network all taken from the user file) |
| `/etc/codex/managed_config.toml` vs `~/.codex/config.toml` | **system wins** |
| `flake.lock` | byte-identical to `~/flakes/gaming/flake.lock`; narHash `sha256-r2f1oUwixlgq9zOdYLqJLfS/lWBT60/IITjhTKI59JU=` is real (nix verified it on fetch); corrupting it reddens every check |
| Pinned nixpkgs tool attrs | `treefmt-2.6.0 nixfmt-1.4.0 statix-0-unstable-2026-05-14 deadnix-1.3.2 shfmt-3.13.1 shellcheck-0.11.0 taplo-0.10.0 prettier-3.8.3 markdownlint-cli-0.48.0`; `nodePackages` **removed** |
| treefmt over the tree | `traversed 13 files / emitted 12 / formatted 12 files (0 changed)`, exit 0 |
| `TREEFMT_CACHE_DIR` in `treefmt --help` | 0 occurrences |
| Build-time network | none beyond the pinned fixed-output fetch (`nix config show sandbox` → true) |
| Secrets | none. Independent greps for `auth.json|OPENAI_API_KEY|sk-|CODEX_ACCESS_TOKEN|bearer|password|secret|token` over the tree → no output |
| Commits | none — `fatal: your current branch 'main' does not have any commits yet` |
| `docs/MAP.md` | present, accurate, ten entries, one per file |

## What the sandbox blocked

Stated as facts, with transcript line numbers. All three are real and all three
are things the brief did not account for; none of them excuses MAJOR-3, MAJOR-5,
MAJOR-7 or MAJOR-9.

1. **DNS.** log:542 ran
   `curl -I --max-time 15 https://registry.npmjs.org/@openai/codex`; log:544:
   `curl: (6) Could not resolve host: registry.npmjs.org`. Also log:1330,
   `"latest version probe": "curl: (6) Could not resolve host: api.github.com"`.
   Consequence: `hash = lib.fakeHash`, and the archive layout was guessed. The
   guess was wrong (MAJOR-1) and incomplete (MAJOR-2). Codex flagged both in
   README.md and VALIDATION.md — "The archive layout still needs verification" —
   which is the right disclosure.
2. **The nix daemon socket.** log:326 ran `... nix store ping ...`; log:406:
   `error: cannot connect to socket at '/nix/var/nix/daemon-socket/socket':
   Operation not permitted`. Consequence: no build, no `flake check`, no `nix
   eval`. This is why MAJOR-4 (`nodePackages`) shipped: a single `nix eval` would
   have caught it. Note that Codex never actually attempted a build or an eval —
   see MINOR-1.
3. **A read-only `.git`.** log:285, log:287, log:408: `Read-only file system
   (os error 30)`; VALIDATION.md quotes `.git/index.lock: Read-only file system`.
   Consequence: nothing staged, nothing committed, hook never installed
   (MAJOR-8, MINOR-2).

Not blocked, and this is the point: the installed `codex-cli 0.153.4` was on
PATH and Codex invoked it 17 times, and it listed `/etc/codex` at log:326.
Everything needed to discover that `--strict-config exec` rejects misspelt keys
(MAJOR-3) and that `/etc/codex/config.toml` loses to the user file (MAJOR-9) was
available for the whole run.

## Fix round

What CX1b must do. Paste-ready.

1. `git add -A` and keep the tree tracked from the first edit onward; nothing in
   this flake can be built or checked otherwise. Verify with
   `nix build ~/flakes/codex#codex` before claiming anything.
2. Replace `hash = lib.fakeHash` with
   `sha256-VIGMufzjNgzG5Ez8WpaVLNXBJD77Q8vkiOEd2oRmPgg=` and delete the
   `# BLOCKED:` comment.
3. In `pkgs/codex/default.nix`, wrap
   `$out/libexec/codex/vendor/x86_64-unknown-linux-musl/bin/codex`, not
   `.../codex/codex`. Derive it from the archive's `codex-package.json`
   (`entrypoint`) rather than hard-coding it a second time, or assert the path
   exists in `installPhase` so a future layout change fails loudly.
4. Add `ncurses` to `buildInputs` (the bundled `codex-resources/zsh` needs
   `libtinfo.so.6`); keep `stdenv.cc.cc.lib`. Add
   `sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];` — the
   nixpkgs convention for a prebuilt-binary package, one line, not required by
   the brief.
5. In `flake.nix`, `nodePackages.prettier` -> `prettier`. Then run
   `nix flake check` and fix anything else that only shows up at eval.
6. **Requirement 2 must be re-scoped, not re-implemented as written.**
   `/etc/codex/config.toml` is a defaults layer any user config overrides
   (MAJOR-9). Render `/etc/codex/managed_config.toml` (measured to outrank
   `~/.codex/config.toml`), or render both, and add a check that proves the
   precedence rather than only the file's contents — e.g. a user-level config
   setting `network_access = true` must **not** win. The brief itself needs the
   same correction; do not treat its parenthetical "(the system layer; it
   outranks `~/.codex/config.toml`)" as fact.
7. Rewrite requirement 3's two checks around `codex --strict-config exec`, which
   does enforce the schema:
   - red: the rendered config with one key misspelt must make
     `codex --strict-config exec --sandbox read-only --skip-git-repo-check <prompt>`
     print ``unknown configuration field `...` `` and exit non-zero before it
     starts a session;
   - green: the rendered config must get past config loading (it will still fail
     later on auth — assert on the *absence* of `Error loading config.toml`, or
     on reaching the `model:` banner line, not on exit 0).
   Keep the `doctor` probe if you like, but demote it: it only proves the TOML
   parses. Both checks must be green in `nix flake check` before this task is
   resubmitted; do not ship a check that is known red.
8. Add a check for requirement 1's wrapper contract: assert that the wrapper puts
   `bwrap` and `rg` on PATH — e.g. run the wrapper with a scrubbed PATH and
   `command -v bwrap rg`, or grep the generated wrapper for both store paths.
   Mutants M5b and M6b must go red. (Justify it as a contract test; 0.153.4
   bundles its own bwrap and rg, so this is not about avoiding a crash.)
9. Extend `module-eval` to assert `otel.exporter` and `otel.trace_exporter`, not
   just `metrics_exporter` (mutant M2 must go red), and set
   `programs.codex.package` from `self.packages.${system}.codex` so a downstream
   consumer gets the pinned build.
10. Fix the `lint` check's sandbox: drop `TREEFMT_CACHE_DIR` (it does not exist)
    and use `export XDG_CACHE_HOME="$TMPDIR/cache"` plus `--no-cache` (or `--ci`).
    Then demonstrate the red for each language arm — one commit's worth of
    deliberate breakage per arm, shown failing, before it counts.
11. `chmod +x tests/lint-nix.sh` for consistency with the other two tests.
12. Commit. One commit per language-plus-tooling pair as the brief requires,
    subjects `<area>: summary (test: <check names>)`, `Co-Authored-By` trailer,
    and install the hook (`git config core.hooksPath githooks`) before the first
    commit — which is only possible once item 7 makes `nix flake check` green
    (MINOR-6).
13. Correct `docs/VALIDATION.md`: it claims `nix build path:...` and
    `nix flake check path:...` were run and failed; they were not run. Say what
    was run (`nix store ping`) and what it proved.

## Second reader

A second reader re-derived every finding from scratch on independent copies of
the tree.

- **Refuted: nothing.** The attempt was made and failed on all seven original
  majors; each reproduced, down to matching store hashes
  (`36z5...` for the failing build, `s6k7w1...` for the repaired one) and
  matching per-check tables.
- **Confirmed:** MAJOR-1 through MAJOR-7 and MINOR-1, plus the facts table (real
  URL and hash, archive layout, the `nixosConfigurations.test` drvPath, the
  per-check outcomes on the submitted tree, all four of Codex's red/green claims,
  the pinned tool versions, the byte-identical `flake.lock`, no secrets, no
  commits). Additionally checked and *not* found to be defects: no build-time
  network beyond the pinned fetch; `meta.license = asl20` matches the archive;
  the bundled bwrap survives autoPatchelf and strip; `nix fmt` works from a
  subdirectory despite `treefmt.toml`'s relative `tests/lint-nix.sh`.
- **Added:** MAJOR-8 (nothing tracked by git — promoted from the draft's MINOR-2,
  because it is the *first* failure of the submission and its repair, `git add
  -A`, was missing from the draft's list of repairs), MAJOR-9 (the brief's
  precedence premise for requirement 2 is false — measured under bwrap),
  MINOR-6 (the shipped hook makes any commit impossible, so requirement 4 is
  foreclosed rather than merely unevaluated), MINOR-7 (requirement 3's checks
  validate the rendered file as a *user* config and never at `/etc/codex/`).
- **Revised:** attribution — `plan_defect` stays `implementer` (majors 3, 5, 6, 7
  carry REJECTED alone), but MAJOR-9 is a **wrong-fact** defect in the brief and
  the fix round must correct the brief, not just the tree. MAJOR-7's stated
  consequence was corrected: 0.153.4 bundles bwrap and rg, so the survivors are an
  untested contract, not a live crash. Requirement 2 regraded MET → NOT MET, and
  requirement 4 PARTIALLY MET → NOT MET. Counts re-derived: majors 7 → 9,
  minors 6 → 7 (old MINOR-2 promoted, two added). Verdict unchanged.
- **Process note:** `/home/dalhaka/flakes/codex` now holds two empty directories,
  `.agents/` and `.codex/`, both timestamped 15:49 — after the last deliverable
  file (15:39) and after the transcript ends, i.e. inside a reviewer probing
  window. Git does not track empty directories, so neither the deliverable nor any
  measurement is affected, but the first reviewer's note "nothing under
  `/home/dalhaka/flakes/codex` was written" is not exactly true. A gate that
  reviews an uncommitted tree should copy first and say so.

## Verdict

REJECTED — nine majors. Four of them (3, 5, 6, 7) required no lifted sandbox
blocker and carry the verdict on their own; two (1, 2) are the guessed archive
layout, disclosed but wrong; one (4) is an evaluation error a single `nix eval`
would have caught; one (8) means the deliverable as handed over cannot be built
at all; and one (9) is a defect in the brief that CX1b must be told about before
it re-renders `/etc/codex/config.toml`.
