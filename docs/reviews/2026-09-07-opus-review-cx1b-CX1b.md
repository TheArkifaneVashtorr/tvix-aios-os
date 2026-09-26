---
plan_defect: none
mutants_total: 27
mutants_killed: 27
mutants_outside_named: 4
reviewer: opus
majors: 0
minors: 6
---
# Opus gate — seat run cx1b, task CX1b — APPROVED

## Summary

CX1b closes all thirteen fix-round items and meets every clause of the brief's
"Done means", measured on a clone of `/home/dalhaka/flakes/codex` at `a58b3aa`.
`nix build .#codex` exits 0 and `./result/bin/codex --version` prints the
literal `codex-cli 0.153.4`; `nix flake check -L` prints `all checks passed!`
and every one of the seven checks the README names passes when forced to
re-execute with `--rebuild`; `nixosConfigurations.test` evaluates to
`/nix/store/0lq29bwxbfv4l3sq3yw2wx5268j8ilvh-nixos-system-nixos-26.05.20260903.a5cc6f2.drv`.

The two findings that carried the CX1 rejection are genuinely repaired, not
worked around. Requirement 3 is now built on `codex --strict-config exec`: the
typo arm makes the binary print ``unknown configuration field
`sandbox_workspace_write.network_acess` `` and exit 1 *before* a session starts,
and the valid arm reaches `model: gpt-6-astra` with no `Error loading
config.toml` — and, critically, the valid arm is no longer vacuous: rendering
`network_acess` from the module turns `config` red (mutant 6). Requirement 2 was
re-scoped rather than re-implemented: the module renders only
`/etc/codex/managed_config.toml`, and `config-precedence` proves the layer wins
by running the real binary under `bwrap` with a user config that sets
`network_access = true`. I reproduced that proof by hand: with the rendered file
mounted at `/etc/codex/managed_config.toml` the banner reads `sandbox:
workspace-write [workdir, /tmp, $TMPDIR]` and the script exits 0; with the same
bytes mounted at `/etc/codex/config.toml` it reads `(network access enabled)`
and exits 1. That is exactly the "red without the managed file, green with it"
the brief demanded.

The tree is committed (five commits, one per language-plus-tooling pair, every
subject in `<area>: summary (test: <check names>)` form, every one carrying
`Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>`), the working tree is
clean, `core.hooksPath = githooks` is set in the deliverable's own `.git/config`,
and the hook works: in a scratch clone a formatting break makes `git commit`
exit 1 with `Error: unexpected changes detected, --fail-on-change is enabled`,
and a clean change commits with `all checks passed!`.

Codex did most of the red-before-green work itself, in the open: the transcript
carries a 12-mutant probe harness (log:4239-4269) that asserts
`test "$status" -ne 0` for every arm, and its ledger at log:4924-4935,
log:5452-5453 and log:6986-6987 shows sixteen rows all `exit=1`. Four of the
formatter arms are attested by the gate rather than by the implementer — see
MINOR-6. I re-derived 27 mutants of my own on independent copies; all 27 die. No
mutant survived. A second reader re-derived every consequential measurement from
scratch on a separate clone and ran 17 further mutants (16 mutations plus a
no-op baseline); all 16 died and the baseline stayed green.

No secrets, no remote, nothing pushed, no read of `~/.codex/auth.json`. I found
no MAJOR, and neither did the second reader. Six MINORs, none of which bears on
the verdict.

Verdict: APPROVED. `plan_defect: none` — the brief's one wrong fact (MAJOR-9 of
CX1) was corrected in the fix-round brief, and the deliverable both implements
the correction and states it in the README.

## Fix-round items

1. **`git add -A`, tree tracked, `nix build` verified — CLOSED.**
   `git -C /home/dalhaka/flakes/codex status --short` -> empty; 15 tracked
   files; `git count-objects` is no longer zero (five commits).
   `nix build .#codex -L` in the clone -> exit 0, output
   `/nix/store/xzw9kw8sv1mdv32c2giariaxjdj0kl72-codex-0.153.4`, the same store
   path the deliverable's own `result` symlink points at.

2. **Real hash, `# BLOCKED:` comment gone — CLOSED.**
   `pkgs/codex/default.nix:17`:
   `hash = "sha256-VIGMufzjNgzG5Ez8WpaVLNXBJD77Q8vkiOEd2oRmPgg=";`
   `grep -rn 'fakeHash\|BLOCKED'` over the tree -> no output.

3. **Wrap `.../bin/codex`, fail loudly on a layout change — CLOSED.**
   `pkgs/codex/default.nix:41`
   `makeWrapper "$out/libexec/codex/vendor/x86_64-unknown-linux-musl/bin/codex" \`
   and `:36` `test -x "$out/libexec/codex/vendor/x86_64-unknown-linux-musl/bin/codex"`.
   The brief allowed either derivation from `codex-package.json` or an
   `installPhase` assertion; the assertion is live — mutant 2 (path put back to
   `codex/codex`) dies in `installPhase`, before `makeWrapper` is reached:

   ```text
   > Running phase: installPhase
   error: Cannot build '/nix/store/ln2lpzzq3mjsvn68g50pijn9k5a9vs6b-codex-0.153.4.drv'.
   ```

4. **`ncurses` added, `stdenv.cc.cc.lib` kept, `sourceProvenance` — CLOSED.**
   `pkgs/codex/default.nix:24-27` `buildInputs = [ stdenv.cc.cc.lib ncurses ];`
   and `:52` `sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];`
   inside `meta`. Mutant 1 (drop `ncurses`) reproduces CX1's MAJOR-2 exactly:
   `libtinfo.so.6 -> not found!` / `auto-patchelf could not satisfy dependency`.

5. **`nodePackages.prettier` -> `prettier`; flake check clean at eval — CLOSED.**
   `flake.nix:35` is `prettier`. `grep -rn nodePackages` over the tree hits only
   the prose line `docs/VALIDATION.md:19`. `nix flake check -L` evaluates
   `formatter`, `devShells`, `packages`, `nixosConfigurations`, `nixosModules`
   and all seven checks and prints `all checks passed!`.

6. **Requirement 2 re-scoped to the managed layer, with a precedence proof —
   CLOSED, and the proof is real.**
   `nixosModules/default.nix:36-37`:

   ```nix
   environment.etc."codex/managed_config.toml".source =
     toml.generate "codex-managed-config.toml" cfg.settings;
   ```

   `nix eval` over `config.environment.etc` attribute names matching `codex`
   returns exactly `["codex/managed_config.toml"]` — `/etc/codex/config.toml` is
   no longer rendered. The rendered bytes are the four required settings and
   nothing else (no `check_for_update_on_startup`):

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

   `checks.config-precedence` (`flake.nix:75-83`, `tests/precedence.sh`) writes a
   *user* config containing `network_access = true`
   (`tests/precedence.sh:10`), mounts the module's rendered file at
   `/etc/codex/managed_config.toml` inside `bwrap --unshare-net ... --ro-bind
   "$work_dir/etc" /etc` (`:12`, `:17-19`) and asserts
   `! grep -Fq 'network access enabled'` (`:30`). I ran the mechanism by hand
   against the Nix-built wrapper (substituting an absolute coreutils `PATH`,
   because `/run/current-system/sw/bin` is not bound into the namespace):

   ```text
   mode=managed -> model: gpt-6-astra
                   sandbox: workspace-write [workdir, /tmp, $TMPDIR]        exit 0
   mode=system  -> model: gpt-6-astra
                   sandbox: workspace-write [workdir, /tmp, $TMPDIR] (network access enabled)
                                                                            exit 1
   ```

   and inside `nix build` as mutant 5 (`… ${renderedConfig} system`):

   ```text
   codex-config-precedence> sandbox: workspace-write [workdir, /tmp, $TMPDIR] (network access enabled)
   MUT=M4-user-wins CHECK=config-precedence EXIT=1
   ```

   The second reader added the stronger arm the Done criterion literally names —
   deleting the whole `if [[ $mode == managed ]] … fi` block at
   `tests/precedence.sh:11-15` so that *no* file is mounted under `/etc/codex`:
   `MUT=P1-no-etc-file EXIT=1`, decisive line
   `codex-config-precedence> sandbox: workspace-write [workdir, /tmp, $TMPDIR] (network access enabled)`.
   The mounted file is `${renderedConfig}` = `flake.nix:26` =
   `testHost.config.environment.etc."codex/managed_config.toml".source`, i.e.
   the module's own output, not a hand-written fixture.
   The README states the correction (`README.md:28-30`): "The original brief's
   claim that `/etc/codex/config.toml` outranks `~/.codex/config.toml` is wrong:
   it is a defaults layer, and the user wins."

7. **Requirement 3 rewritten around `codex --strict-config exec`; both arms
   green in `nix flake check` — CLOSED.**
   `tests/config.sh:18-19` runs
   `timeout 15 "$codex_bin" --strict-config exec --sandbox read-only
   --skip-git-repo-check 'Reply OK.'` in a disposable `HOME`/`CODEX_HOME`.
   Red arm (`config-rejects-typo`, `tests/config.sh:22-26`): `status -eq 1`, the
   exact diagnostic, and *no* `^model:` line. Built:

   ```text
   codex-config-typo> Error loading config.toml:
   codex-config-typo> /build/tmp.Pbef5aRAoB/codex/config.toml:10:1: unknown configuration field `sandbox_workspace_write.network_acess`
   codex-config-typo> 10 | network_acess = false
   ```

   exit 0 for the check. Green arm (`config`, `:28-29`): absence of
   `Error loading config.toml` plus `^model:` — never exit 0 of the binary:

   ```text
   codex-config-valid> OpenAI Codex v0.153.4
   codex-config-valid> model: gpt-6-astra
   codex-config-valid> sandbox: read-only
   ```

   exit 0. `tests/doctor.sh` was deleted rather than demoted; the README records
   why (`README.md:60-61`: "Doctor's `config.load = ok` only proves TOML parsing
   and is not used as schema validation"). Both arms are load-bearing: mutant 6
   (module renders `network_acess`) reddens `config`; mutant 26 (drop
   `--strict-config`) reddens `config-rejects-typo`, and the second reader
   pinned the decisive line for that one — without `--strict-config` the
   misspelt config is *accepted* and the typo arm reaches
   `codex-config-typo> model: gpt-6-astra`.

8. **Wrapper-PATH contract check — CLOSED.**
   `flake.nix:84-87` + `tests/wrapper-path.sh:5-6`
   (`grep -F 'PATH=' "$wrapper" | grep -Fq "$helper_dir"` for each of
   `${pkgs.bubblewrap}/bin` and `${pkgs.ripgrep}/bin`). The generated wrapper
   prefixes `ripgrep-15.1.0/bin` and `bubblewrap-0.11.2/bin` and execs
   `.../vendor/x86_64-unknown-linux-musl/bin/codex`. CX1's two survivors are
   dead: mutants 10 and 11 (`bubblewrap` / `ripgrep` removed from `makeBinPath`)
   both give `MUT=… CHECK=wrapper-path EXIT=1`. By hand,
   `bash tests/wrapper-path.sh <wrapper> /nix/store/nonexistent-bwrap/bin` -> exit 1.

9. **`module-eval` asserts all three exporters; package from the flake's own
   output — CLOSED.**
   `flake.nix:91-93` asserts `otel.metrics_exporter`, `otel.exporter` and
   `otel.trace_exporter` all `== "none"`; `flake.nix:61-64` sets
   `programs.codex.package = lib.mkDefault self.packages.${pkgs.stdenv.hostPlatform.system}.codex`
   and `nixosModules/default.nix:14-17` no longer carries a
   `pkgs.callPackage ../pkgs/codex { }` default. CX1's surviving mutant M2 is
   dead — renaming `exporter` to `exporterr` gives
   `MUT=M19-exporterr CHECK=module-eval EXIT=1`; so is
   `trace_exporter = "otlp"`:

   ```text
   error: string '"otlp"' is not equal to string '"none"'
   ```

   Removing the flake's `programs.codex.package` line is also caught:
   `error: The option 'programs.codex.package' was accessed but has no value defined.`

10. **`lint` runs under nix; a red per language arm — CLOSED.**
    `flake.nix:109-110`:

    ```text
    export XDG_CACHE_HOME="$TMPDIR/cache"
    codex-treefmt --no-cache --tree-root . --walk filesystem --fail-on-change
    ```

    `grep -rn TREEFMT_CACHE_DIR` -> none. The check runs and passes:
    `traversed 15 files / emitted 14 files for processing / formatted 14 files
    (0 changed)`. Codex showed a red per *language* in-session (log:4924-4935 and
    the two later rounds, all `exit=1`) — but not per tool; four formatter arms
    have no implementer red, see MINOR-6. I re-derived one red per arm
    independently — nixfmt, statix (`[23] Warning: Unnecessary concatenation
    with empty list`), deadnix (`Unused let binding: unusedBinding`), shellcheck
    (`SC2086 (info): Double quote to prevent globbing and word splitting`),
    treefmt/TOML (`toml: table nix already exists`), taplo
    (`error: conflicting keys … duplicate key`), markdownlint
    (`README.md:5 error MD001/heading-increment`), prettier/JSON
    (`[warn] Code style issues found in the above file`). All eight redden
    `lint`. The second reader closed the remaining arms — `shfmt`,
    `taplo fmt`, `prettier` on Markdown and (again) `deadnix --fail` — so every
    wired arm is now attested red by the gate.

11. **`chmod +x tests/lint-nix.sh` — CLOSED.** All five test scripts are mode
    755 (`stat -c %a`): `config.sh 755`, `lint-nix.sh 755`, `precedence.sh 755`,
    `version.sh 755`, `wrapper-path.sh 755`.

12. **Commits, subjects, trailer, hook installed — CLOSED.**
    Five commits, one per language-plus-tooling pair, each adding its language's
    files together with its `treefmt.toml` arms:

    ```text
    e12c468 toml: add formatting and lint gate (test: lint)                    [.gitignore, treefmt.toml]
    dd3b2e4 shell: add strict config and wrapper probes with tooling
            (test: version, config, config-rejects-typo, config-precedence, wrapper-path, lint)
                                                       [githooks/pre-commit, tests/*.sh, treefmt.toml]
    305f6de nix: package pinned Codex and enforce managed settings
            (test: version, config, config-rejects-typo, config-precedence, wrapper-path, module-eval, lint)
                                            [flake.nix, nixosModules/, pkgs/, treefmt.toml]
    853a760 json: pin nixpkgs and validate lock formatting (test: lint)        [flake.lock, treefmt.toml]
    a58b3aa docs: record precedence and red-green evidence with prose tooling (test: lint)
                                                       [README.md, docs/*.md, treefmt.toml]
    ```

    Every one ends with `Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>`
    (5/5). `/home/dalhaka/flakes/codex/.git/config` carries
    `hooksPath = githooks` under `[core]`. Hook proven functional in a scratch
    clone — see "Red before green". See MINOR-2 for the one qualification.

13. **`docs/VALIDATION.md` corrected — CLOSED.** `docs/VALIDATION.md:6-15`
    is a section headed "Correction to session 01a07d94" that says plainly
    "Neither command was executed. Transcript line 326 ran `nix store ping`;
    line 406 reported daemon socket access denied", and adds what that did and
    did not prove. Both citations check out against the CX1 transcript. The rest
    of the file is this round's measurements, including a 15-row
    deliberate-failure table (`:64-80`) and the toplevel drvPath (`:88`), which
    matches my own `nix eval` byte for byte.

## Done criteria

| Clause | Result |
| --- | --- |
| `nix build ~/flakes/codex#codex` -> `--version` prints `codex-cli 0.153.4` | **MET** — `nix build .#codex -L` exit 0; `./result/bin/codex --version` -> `codex-cli 0.153.4`, exit 0 |
| `nix flake check` green with every check the README names | **MET** — `all checks passed!`, exit 0; the README names `version, config, config-rejects-typo, config-precedence, wrapper-path, module-eval, lint` and each, forced with `--rebuild`, exits 0 |
| `nixosConfigurations.test` evaluates | **MET** — `"/nix/store/0lq29bwxbfv4l3sq3yw2wx5268j8ilvh-nixos-system-nixos-26.05.20260903.a5cc6f2.drv"`, exit 0 |
| the precedence check is red without the managed file and green with it | **MET** — measured in-check (mutant 5), by hand, and with the file removed entirely (second reader, `P1-no-etc-file`); the failing banner is `(network access enabled)` |
| the README says how to bump | **MET** — `README.md:64-75`: change only `version` and `src.hash`, hash from `nix store prefetch-file --json <url>` |
| commit subjects `<area>: summary (test: <check names>)` with the trailer | **MET** — 5/5 subjects and 5/5 trailers |
| the hook installed | **MET** — `core.hooksPath = githooks` in the deliverable's `.git/config`; proven to reject and to pass |

## Majors

None.

I tried to manufacture one and failed on each attempt; so did the second reader.
The candidates chased and what killed them:

- *"the green strict-config arm is vacuous again"* — refuted: rendering
  `network_acess` from the module turns `config` red (mutant 6, decisive line
  ``unknown configuration field `sandbox_workspace_write.network_acess` `` in
  the `codex-config-valid` builder log).
- *"the typo arm's `sed` still silently no-ops"* — refuted: `tests/config.sh:12`
  guards it with `grep -q '^network_access = false$'` before the `sed`, and the
  check dies at that guard with no codex output at all when the key is renamed
  away (mutant 7) or its value flipped (mutant 8).
- *"the precedence check only proves the file's contents"* — refuted: the user
  config in `tests/precedence.sh:10` sets `network_access = true`, and moving
  the managed bytes to the defaults path — or removing them entirely — makes the
  banner say `(network access enabled)` and the check exit 1.
- *"`nix flake check` was green only because the store was warm"* — refuted: I
  re-ran every check with `--rebuild`, which forces re-execution; all seven
  still exit 0.
- *"`nix flake check` is vacuous — it prints `running 0 flake checks...`"* —
  refuted by the second reader: with `flake.nix:70` mutated to expect
  `0.149.0`, `nix flake check -L` exits 1 with
  `error: failed to build attribute 'checks.x86_64-linux.version' … > Expected
  codex-cli 0.149.0; got codex-cli 0.153.4`. The command does gate.
- *"the wrapper test greps a file instead of exercising PATH"* — the brief
  explicitly allowed either ("or grep the generated wrapper for both store
  paths"), and the grep discriminates: both removal mutants die.
- *"the hook has a hole for newly staged files"* — refuted by experiment: adding
  an unformatted `docs/NEW.md` and `tests/new.toml` and committing gives exit 1
  (`traversed 17 files / formatted 12 files (2 changed) / docs/NEW.md:1 error
  MD041 / Error: failed to finalise formatting: formatting failures detected`),
  HEAD unmoved.
- *"`module-eval` is eval-only, so it cannot fail"* — refuted:
  `MUT=M1-drop-exporter EXIT=1` at `flake.nix:92`.
- *"the `version` check is a tautology because it compares against
  `${codex.version}`"* — not a defect: the original brief's requirement 1 asks
  for "a version bump is one version string and one hash", which is exactly what
  tying the assertion to `codex.version` implements, and the binary does print
  the literal `codex-cli 0.153.4` today.
- *"the module lost `/etc/codex/config.toml`, so the original requirement 2 is
  unmet"* — the fix-round brief re-scoped it ("render `/etc/codex/
  managed_config.toml` (or both files)"), and CX1's MAJOR-9 established that the
  defaults layer cannot deliver the hardening. Rendering only the effective
  layer is the correct reading.

## Minors

**MINOR-1 — `docs/MAP.md` is not complete.** It lists 12 entries for 15 tracked
files: `README.md`, `.gitignore` and `docs/MAP.md` itself are absent, and the
two new tests (`tests/precedence.sh`, `tests/wrapper-path.sh`) are appended at
`:13-14` after `docs/VALIDATION.md` rather than beside the other tests, so the
file order the rest of the list follows is broken. Nothing checks MAP currency.

**MINOR-2 — the bootstrap history is only meaningful at HEAD.** Commit
`e12c468 toml: … (test: lint)` names a check that does not exist at that commit
(`flake.nix` first appears at `305f6de`), and `githooks/pre-commit:5-6`
deliberately does `unset GIT_INDEX_FILE` so that each commit was gated against
the *complete working tree*, not against its own tree. Codex discloses this
(`docs/VALIDATION.md:94-98`: "Earlier bootstrap commits depend on the other
tracked working files; the final commit is the complete standalone flake"), so
it is honest, and it is the only way to satisfy "in the same commit as the
language" while bootstrapping a repository. But `git bisect` and per-commit
`nix flake check` are not usable on this history.

**MINOR-3 — three checks run a binary that attempts outbound network.** The
builder logs for `config`, `config-rejects-typo` and `config-precedence` all
carry
`ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket
… url: wss://api.openai.com/v1/responses`. On this host `nix config show` gives
`sandbox = true`, so nothing leaves the machine (and `config-precedence`
additionally uses `bwrap --unshare-net`, whose failure mode is
`failed to lookup address information: Try again`); on a builder with sandboxing
disabled these checks would make real egress attempts during `nix flake check`.
Related: each run is bounded by `timeout 15` (`tests/config.sh:18`,
`tests/precedence.sh:22`), so a slow or loaded builder can redden `config` for
reasons that have nothing to do with the config.

**MINOR-4 — `config-precedence` needs nested unprivileged user namespaces.** It
runs `bwrap` inside the Nix build sandbox (`flake.nix:78`,
`tests/precedence.sh:17`). It works here, and `README.md:52` discloses the
requirement, but it makes `nix flake check` non-portable in a way none of the
other six checks are.

**MINOR-5 — precedence coverage is one setting wide.** `tests/precedence.sh`
asserts the managed layer wins only for `sandbox_workspace_write.network_access`.
Setting `features.plugins = true` in the module leaves `config-precedence` green
(measured: `MUT=M3b-plugins-true CHECK=config-precedence EXIT=0`); it is caught
only by `module-eval`, which tests Nix-level values, not the runtime layer
order. The `[features]` and `[otel]` hardening therefore has no runtime
precedence proof.

**MINOR-6 — four lint arms have no implementer-side red; the gate supplied it.**
Raised by the second reader against the draft's own wording. `treefmt.toml:1-57`
wires twelve `[formatter.*]` arms, and Codex's in-session mutant harness
(log:4239-4269) mutates exactly twelve *names*, but those names are per language
plus a few tools: the complete ledger is sixteen rows at log:4924-4935
(`config, config-rejects-typo, config-precedence, wrapper-bwrap, wrapper-rg,
module-exporter, module-trace, lint-nix, lint-shell, lint-toml, lint-markdown,
lint-json`), log:5452-5453 (`lint-taplo, lint-statix`) and log:6986-6987 (the
two split-formatter re-runs). There is no `deadnix`, `shfmt`, `taplo fmt` or
`prettier`-on-Markdown row. The house rule "a load-bearing test counts only once
it has been shown to fail" is therefore satisfied for those four arms by the
review, not by the implementer. None is vacuous — all four were reddened on
independent clones with
`nix build path:<copy>#checks.x86_64-linux.lint --no-link -L`:

```text
MUT=L2-deadnix     EXIT=1  ERRO formatter | deadnix: failed to apply with options
                           [--fail flake.nix …]: exit status 1
                           Warning: Unused declarations were found.
                           flake.nix:9:7 unusedBinding = 1;
MUT=L3-shfmt       EXIT=1  ERRO file has changed path=tests/precedence.sh
                           prev_size=1377 current_size=1373
                           formatted 14 files (1 changed)
                           Error: unexpected changes detected, --fail-on-change is enabled
MUT=L10-prettier-md EXIT=1 ERRO file has changed path=README.md
                           prev_size=3907 current_size=3897
                           Error: unexpected changes detected
MUT=L11-taplo-fmt  EXIT=1  ERRO file has changed path=tests/mutant.toml
                           prev_size=6 current_size=8
                           emitted 15 files
                           Error: unexpected changes detected
```

Logs under
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/864c1483-64cc-448c-96a6-49e716f68be5/scratchpad/cx1b-review/mut2/`.
Not a violation of the deliverable's Done criteria — the fix-round item asked
for a red per *language* arm, which is present — so it does not move the
verdict.

## Mutation table

Base is the clone at `a58b3aa`, whose baseline is
`version 0 | config 0 | config-rejects-typo 0 | config-precedence 0 |
wrapper-path 0 | module-eval 0 | lint 0` (each forced with `--rebuild`).
Each row: fresh `git clone` of that base, mutate, `git add -A`,
`nix build path:<copy>#checks.x86_64-linux.<check> --no-link -L`.

| # | Mutant | Named? | Check | Decisive line | Killed |
| --- | --- | --- | --- | --- | --- |
| 1 | pkg: drop `ncurses` from `buildInputs` | yes | version | `libtinfo.so.6 -> not found!` / `auto-patchelf could not satisfy dependency` | yes |
| 2 | pkg: entrypoint back to `.../codex/codex` | yes | version | fails in `installPhase` (the `test -x` assertion) | yes |
| 3 | module: drop `features.plugins = false` | yes | module-eval | `error: attribute 'features' missing` | yes |
| 4 | module: `features.plugins = true` | yes | module-eval | assertion `(! …features.plugins)` fails | yes |
| 5 | check: precedence mounts `/etc/codex/config.toml` instead of the managed file | yes | config-precedence | `sandbox: workspace-write [...] (network access enabled)` | yes |
| 6 | module: render `network_acess` | yes | config | ``unknown configuration field `sandbox_workspace_write.network_acess` `` in the *valid* arm | yes |
| 7 | module: rename the key to `allow_network` (typo `sed` no-ops) | yes | config-rejects-typo | dies at the `grep -q '^network_access = false$'` guard, no codex output | yes |
| 8 | module: `network_access = true` (the `sed` pattern misses) | yes | config-rejects-typo | same guard | yes |
| 9 | test: delete the `sed -i` line from `tests/config.sh` | yes | config-rejects-typo | valid config in typo mode -> `status -eq 1` fails | yes |
| 10 | pkg: `bubblewrap` out of `makeBinPath` | yes | wrapper-path | builder exit 1 | yes |
| 11 | pkg: `ripgrep` out of `makeBinPath` | yes | wrapper-path | builder exit 1 | yes |
| 12 | `flake.nix`: nixfmt-breaking edit | yes | lint | `Error: unexpected changes detected, --fail-on-change is enabled` | yes |
| 13 | module: drop `otel.trace_exporter` | yes | module-eval | `error: attribute 'trace_exporter' missing` | yes |
| 14 | module: all three exporters `"otlp"` | yes | module-eval | `string '"otlp"' is not equal to string '"none"'` | yes |
| 15 | module: `trace_exporter = "otlp"` only | yes | module-eval | same | yes |
| 16 | module: rename `exporter` -> `exporterr` (CX1's survivor M2) | yes | module-eval | eval failure | yes |
| 17 | module: `[ ] ++ [ cfg.package ]` | yes | lint | `[23] Warning: Unnecessary concatenation with empty list` | yes |
| 18 | `tests/config.sh`: `cp $config_file` unquoted | yes | lint | `SC2086 (info): Double quote to prevent globbing and word splitting` | yes |
| 19 | `README.md`: h2 -> h4 | yes | lint | `README.md:5 error MD001/heading-increment` | yes |
| 20 | `flake.lock` collapsed to one line | yes | lint | `[warn] Code style issues found in the above file` | yes |
| 21 | `treefmt.toml`: duplicate `[formatter.nix]` | yes | lint | `toml: table nix already exists` | yes |
| 22 | new `tests/mutant.toml` with a duplicate key | yes | lint | `error: conflicting keys … duplicate key` (taplo) | yes |
| 23 | module: rename the etc entry to `codex/other.toml` | **no** | module-eval | `error: attribute '"codex/managed_config.toml"' missing` | yes |
| 24 | `flake.nix`: drop `programs.codex.package = … self.packages…` | yes | module-eval | `The option 'programs.codex.package' was accessed but has no value defined` | yes |
| 25 | pkg: version -> `0.153.5`, hash untouched | **no** | version | `curl: (22) The requested URL returned error: 404` | yes |
| 26 | `tests/config.sh`: drop `--strict-config` | **no** | config-rejects-typo | typo config accepted -> `codex-config-typo> model: gpt-6-astra`, `status -eq 1` fails | yes |
| 27 | `flake.nix`: unused `let` binding | **no** | lint | `Unused let binding: unusedBinding` (deadnix) | yes |

`mutants_total: 27`, `mutants_killed: 27`, `mutants_outside_named: 4`
(rows 23, 25, 26, 27). No survivors. The second reader ran a further 16 mutants
plus a no-op baseline on a separate clone; all 16 died, the baseline stayed
green. Those are listed in "Second reader" and are not counted in the totals
above.

One candidate was discarded after checking the tool rather than the tree:
`actual=$($1 --version)` in `tests/version.sh` (unquoted expansion in command
position) leaves `lint` green — shellcheck 0.11.0 does not report it, the same
tool behaviour the CX1 gate recorded. It is not a gap in the tree, so it is not
counted.

## Red before green

Every red/green pair Codex claims reproduces. Run against the Nix-built wrapper
`/nix/store/xzw9kw8sv1mdv32c2giariaxjdj0kl72-codex-0.153.4/bin/codex` and the
module's rendered file
`/nix/store/7sxc8fjmi8p5dasb9czq1kn9jfbb97md-codex-managed-config.toml`:

```text
$ bash tests/version.sh <wrapper> 0.149.0
Expected codex-cli 0.149.0; got codex-cli 0.153.4
exit=1
$ bash tests/version.sh <wrapper> 0.153.4
exit=0

$ bash tests/config.sh <wrapper> <cfg> valid
model: gpt-6-astra
exit=0
$ bash tests/config.sh <wrapper> <cfg> typo
Error loading config.toml:
/tmp/tmp.Qq6FmaTJnW/codex/config.toml:10:1: unknown configuration field `sandbox_workspace_write.network_acess`
exit=0

$ bash tests/wrapper-path.sh <wrapper> <bubblewrap>/bin <ripgrep>/bin
exit=0
$ bash tests/wrapper-path.sh <wrapper> /nix/store/nonexistent-bwrap/bin
exit=1

$ bash <precedence.sh, absolute coreutils PATH> <wrapper> <cfg> managed
model: gpt-6-astra
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
exit=0
$ bash <precedence.sh, absolute coreutils PATH> <wrapper> <cfg> system
model: gpt-6-astra
sandbox: workspace-write [workdir, /tmp, $TMPDIR] (network access enabled)
exit=1
```

(The by-hand precedence run needs an absolute `coreutils/bin` in the bwrap
`PATH`; the script passes `"$PATH"` through, and on the host `timeout` lives
under `/run/current-system/sw/bin`, which is not bound into the namespace —
`bwrap: execvp timeout: No such file or directory`. Inside the Nix build sandbox
`PATH` is store-only, so the check itself is unaffected.)

The pre-commit hook, in a scratch clone with `git config core.hooksPath githooks`:

```text
$ printf '\n\n\n' >> flake.nix && git add -A && git commit -m "test: hook must reject (test: lint)"
formatted 14 files (1 changed) in 260ms
Error: unexpected changes detected, --fail-on-change is enabled
commit-exit=1

$ printf -- '- `README.md`: reviewer scratch line.\n' >> docs/MAP.md && git add -A && git commit -m "docs: reviewer scratch commit (test: lint)"
formatted 1 files (0 changed) in 192ms
all checks passed!
commit-exit=0   -> 408d188
```

Codex's own reds are in the transcript, not merely asserted: the probe harness
at log:4239-4269 builds twelve mutated copies and asserts
`test "$status" -ne 0` on each, and the ledgers at log:4924-4935,
log:5452-5453 and log:6986-6987 print sixteen `exit=1` rows covering
`config, config-rejects-typo, config-precedence, wrapper-bwrap, wrapper-rg,
module-exporter, module-trace, lint-nix, lint-shell, lint-toml, lint-markdown,
lint-json, lint-taplo, lint-statix` and the two split-formatter re-runs. The
`lint-shell` arm's SC2086 is visible at log:5018. Four formatter arms are absent
from that ledger and were closed by the gate instead — MINOR-6.

## Second reader

A second reader re-derived every consequential measurement from scratch on an
independent clone
(`…/scratchpad/cx1b-review/clone-skeptic`, HEAD `a58b3aa`) and returned a
verdict of APPROVED, concurring with this gate.

**Refuted: nothing.** No claim in the draft was overturned, and no MAJOR was
manufacturable. Seven candidate MAJORs were chased and killed, three of them
attacks this gate had not tried: that `nix flake check` might be vacuous
(killed — a mutated `version` expectation makes it exit 1), that the pre-commit
hook might not see newly staged files (killed — a fresh unformatted
`docs/NEW.md` + `tests/new.toml` makes the commit exit 1 and leaves HEAD
unmoved), and that `module-eval` might be unable to fail (killed —
`MUT=M1-drop-exporter EXIT=1`).

**Confirmed:** every measurement in "Facts measured", the seven Done criteria,
the three named items (6, 7, 10), the commit/trailer/hook facts (5/5 subjects
match `^[a-z-]+: .+ \(test: [a-z0-9-]+(, [a-z0-9-]+)*\)$`, 5/5 carry the
byte-exact trailer), the spot checks on items 1-5, 9, 11 and 13, and the safety
and hygiene results (no remote, no push, no PR, no `sudo`/`nixos-rebuild`/
`systemctl` invocation, no credential material in the tree or transcript;
`grep -rIn 'dsh|Cowork|Claude Code|claude'` over the tree returns nothing,
satisfying the original brief's exclusivity rule). The deliverable was not
modified by either reader: `git -C /home/dalhaka/flakes/codex status --short` is
empty and HEAD is still `a58b3aa`.

**Added:** one finding, recorded above as **MINOR-6** — the draft's sentence
"Codex showed a red per arm in-session" is true per language, not per tool; four
formatter arms (`deadnix --fail`, `shfmt`, `taplo fmt`, `prettier --write` on
Markdown) have no implementer-side red and were closed by the review instead.
Non-gating. Two of the draft's existing entries were also sharpened with second
reader evidence: item 6 now cites the `P1-no-etc-file` mutant (no managed file
mounted at all -> `(network access enabled)`, exit 1), which is the Done
criterion read literally, and item 7 / mutant 26 now cite the decisive line
showing that without `--strict-config` the misspelt config is accepted.

Second reader mutants (all on `clone-skeptic`, all killed; a no-op baseline
stayed green): `P1-no-etc-file`, `P2-defaults-layer`, `S1-module-typo`,
`S2-no-strict-config`, `M1-drop-exporter`, and eleven lint arms — `L1-statix`,
`L2-deadnix`, `L3-shfmt`, `L4-markdownlint`, `L5-treefmt-config`,
`L6-prettier-json`, `L7-shellcheck`, `L8-nixfmt`, `L9-taplo-check`,
`L10-prettier-md`, `L11-taplo-fmt`. Every wired arm can fail.

## Facts measured

| Fact | Value |
| --- | --- |
| Deliverable HEAD | `a58b3aa`, five commits, working tree clean (`git status --short` empty) |
| Tracked files | 15 |
| `core.hooksPath` in the deliverable | `githooks` (in `.git/config`) |
| Remotes | none (`git remote -v` empty) — nothing pushed |
| `nix build .#codex -L` | exit 0 -> `/nix/store/xzw9kw8sv1mdv32c2giariaxjdj0kl72-codex-0.153.4` (identical to the deliverable's own `result`) |
| `./result/bin/codex --version` | `codex-cli 0.153.4`, exit 0 |
| Wrapper | prefixes `ripgrep-15.1.0/bin` and `bubblewrap-0.11.2/bin`; execs `.../vendor/x86_64-unknown-linux-musl/bin/codex` |
| `nix flake check -L` | `all checks passed!`, exit 0 |
| Per check, forced `--rebuild` | `version 0 / config 0 / config-rejects-typo 0 / config-precedence 0 / wrapper-path 0 / module-eval 0 / lint 0` |
| `nixosConfigurations.test` toplevel drvPath | `/nix/store/0lq29bwxbfv4l3sq3yw2wx5268j8ilvh-nixos-system-nixos-26.05.20260903.a5cc6f2.drv` (matches `docs/VALIDATION.md:88`) |
| `environment.etc` keys matching `codex` | `["codex/managed_config.toml"]` — the defaults file is no longer rendered |
| Rendered managed config | `[features] plugins=false`; `[otel] exporter/metrics_exporter/trace_exporter="none"`; `[sandbox_workspace_write] network_access=false`; no `check_for_update_on_startup` |
| Managed vs user config, by hand under bwrap | managed wins: no `(network access enabled)`; the same bytes at `/etc/codex/config.toml` lose to the user file; with no `/etc/codex` file at all the user file also wins |
| `lint` run | `traversed 15 files / emitted 14 files for processing / formatted 14 files (0 changed)` |
| `TREEFMT_CACHE_DIR` in the tree | 0 occurrences; `XDG_CACHE_HOME="$TMPDIR/cache"` + `--no-cache` at `flake.nix:109-110` |
| `nodePackages` in the tree | one prose mention, `docs/VALIDATION.md:19`; `flake.nix:35` uses `prettier` |
| `fakeHash` / `# BLOCKED` | 0 occurrences |
| Test-script modes | all five 755 |
| `flake.lock` | rev `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4`, matches the `flake.nix` input; byte-identical to `~/flakes/gaming/flake.lock` |
| Host nix sandbox | `sandbox = true`, `filter-syscalls = true` |
| Secrets | none — `grep -rInE 'auth\.json\|OPENAI_API_KEY\|sk-[A-Za-z0-9]\|CODEX_ACCESS_TOKEN\|bearer\|password\|secret\|token'` over the tree returns no output |
| `auth.json` in the transcript | only lines 591 and 791, both quotations of the CX1 review and the brief; no read of the file |
| `git diff --check` | exit 0 |
| Trailer | `Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>` on 5/5 commits |
| Claims in the final message | all independently verified except three that only the transcript can attest: "exit 1 before repair" for the first build, "exit 1 during three repair iterations" for `nix flake check`, and "five successful commit hooks". Nothing in the final message is refuted. |

## What remains

Nothing gating. For the orchestrator, if it wants a follow-up task:

1. `docs/MAP.md` -> add `README.md`, `.gitignore` and `docs/MAP.md`, and move the
   two new test entries next to the other tests (MINOR-1).
2. Extend `tests/precedence.sh` to assert the managed layer also wins for
   `features.plugins` and the OTel exporters — the natural probe is a user
   config setting `plugins = true` and a `codex features`/banner assertion
   (MINOR-5).
3. Decide whether `nix flake check` should contain checks that dial
   `api.openai.com` at all (MINOR-3) and whether `config-precedence` should be
   gated on a `bwrap`-capable builder (MINOR-4).
4. Note for the seat harness, not for this deliverable: require the implementer's
   red-before-green ledger to have one row per wired *tool*, not per language, so
   the gate is not the first thing to prove a formatter arm can fail (MINOR-6).
