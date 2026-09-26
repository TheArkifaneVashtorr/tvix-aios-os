# NixOS skill for the dark factory — design (rev 2.1)

**Status:** rev 2.1 — adversarial review (6 lenses, 24 findings) folded in rev 2,
confirmation pass (3 lenses, 23/23 addressed, 6 new items folded — §17); READY for the operator's spec gate.
**Origin:** operator, 2026-09-03 ("if it was well organized and didn't flood
context a nixos skill would be amazing — retrofitting the documentation to be
AI friendly"). Brainstorm decisions: general NixOS knowledge pinned to what
this machine runs (not project conventions); fully curated by agents, no
generator; measured by evals AND by the next two factory runs; its own repo
`~/flakes/nixos-skill`; then re-shaped for an agent-only audience (executable
examples, build-graded evals, explicit loading by role).

## 1. Goal and consumers

A Claude Code skill, `nixos`, that gives an agent working on any NixOS flake
on this machine correct, pin-accurate knowledge in a few thousand tokens,
loaded on demand, never all at once. Its consumers, in order of importance:

| consumer | role in the dark factory | what it needs |
|---|---|---|
| Sonnet implementer | writes modules, packages, VM tests, services | task-shaped idioms that build at the pin; the verify-before-use loop |
| Opus reviewer | adversarial code gate | a checklist of the defects NixOS code actually has here |
| Sonnet docs reviewer | one-pass review of runbooks/plans | the CLI and activation facts a runbook's commands rely on |
| Sonnet verifier | mechanical checks | the exact commands: build, closure diff, activation diff |
| orchestrator (Fable) sessions in each flake | plans and specs | the router and the options map |

There are no human readers. Prose exists to make a model act correctly, not
to teach. The operator's only contact with the skill is one install command,
the eval report and the board.

## 2. Non-goals

- No project conventions (baskets, broker, Helm, "build-only" rules): those
  stay in each repo's CLAUDE.md.
- No generated option index: the full options reference (~10k options) stays
  in the store where it already is; the skill teaches how to query it.
- No network at build, test or refresh time. Every source is a store path at
  the pin. (Enforced structurally, §7: no fetchers, no fixed-output
  derivations in examples — `--offline` alone does not block a fixed-output
  derivation's own download.)
- No description tuning for triggering: factory agents load it explicitly.

## 3. Pin

Everything is written against and tested at one pin, the host's:

- nixpkgs `ac62194c3917d5f474c1a844b6fd6da2db95077d` (NixOS 25.05, the
  `nixpkgs-host` input of nixos-agent-env and the `nixpkgs` input of
  `~/flakes/gaming`)
- nix 2.28.5
- systemd 257.10, kernel 6.12.63 (named where behaviour depends on them)

Sources available offline in that closure: the NixOS manual and options
reference (`nixos-manual-html`, `options.html` with per-option anchors), the
nix manual and man pages (`nix-2.28.5-doc`, `nix-2.28.5-man`), the nixpkgs
source itself (`lib/`, `nixos/modules/`, `pkgs/`, `doc/`), and the built
`nixos-configuration-reference-manpage`.

## 4. Repository layout (`~/flakes/nixos-skill`)

```
flake.nix            devShell (lint gate + python3 + the claude CLI on PATH) and checks
flake.lock           nixpkgs pinned to the host rev (lock guard check, as in gaming/media)
treefmt.toml         nixfmt, shfmt, ruff format; markdownlint for prose
githooks/pre-commit  refuses commits outside the devShell; runs the gate
CLAUDE.md            this repo's own conventions (short)
skills/nixos/        the skill (SKILL.md + references/)
tools/               doctest.py, citations.py, budget.sh, router.py, run-evals.sh, report.py
evals/               tasks/<name>/{seed/, TASK.md, expected.md}, results/<date>.json
docs/                this spec (copy), the plan, runbook, board
```

The skill is installed for interactive sessions by one operator command
(`mkdir -p ~/.claude/skills && ln -s ~/flakes/nixos-skill/skills/nixos
~/.claude/skills/nixos`; `~/.claude/skills` does not exist today). Factory
agents are given the path explicitly (§10) and never depend on the symlink.

## 5. The skill

### 5.1 `SKILL.md` — the router (≤ 120 lines)

Frontmatter `name: nixos`, a plain description (what it is, which pin). Body:

1. **The pin** (3 lines): versions, and the sentence "if `nix --version` or
   the flake's nixpkgs rev differs, trust the store over this skill and say
   so".
2. **Five rules that always apply** (one line each, with the command):
   verify an option before using it (`nix eval`/`nixos-option` recipe); read
   the module source at the pin before overriding its behaviour; flakes see
   only tracked files; prefer build-time assertions to runtime checks; never
   guess a hash — obtain it (the fake-hash build loop, `nix hash`,
   `nix-prefetch-url`; see the §7 exception for how this recipe is shown).
3. **Task → files table**: one row per task shape seen in this project's
   plans, naming one to three references, ≤ 12 words of "read when". Rows
   include the combinations that actually occur: "hardened service with new
   module options" → module-system, systemd-units, systemd-hardening;
   "service in a network namespace or with a polkit rule" → add security;
   "VM test with a negative proof" → vm-tests, module-system; "package a
   Python tool with CUDA" → packaging, python-and-cuda. Every row's names are
   reference file stems, so a script can resolve them (§10, `router` check).
4. **Role entries**: implementing a plan task → router + the task's
   references (`skillRefs`, or pick from the table by the task's title and
   spec text); reviewing code → `review-checklist` + `gotchas`; reviewing a
   runbook or plan → `nix-cli` + `activation-and-switch`; verifying →
   `verify`.

### 5.2 References (each ≤ 250 lines, self-contained, one "read when" line)

| file | read when | contents (bounded) |
|---|---|---|
| `nix-language.md` | writing or reading any Nix expression | syntax, laziness, `with`/`inherit`/`rec`/`let`, paths vs strings and store copies, string contexts, common eval errors with their messages, `builtins` that matter |
| `flakes.md` | touching `flake.nix`/`flake.lock` | inputs (github/git+file/path), `follows`, lock semantics, outputs schema, `nix build/eval/develop/run/flake check`, `--offline`/`--no-update-lock-file`, registry, tracked-files gotcha, `self.rev`/`dirtyRev` |
| `module-system.md` | writing a NixOS/nixpkgs module | options/config/imports, `types.*`, submodules, `mkOption`/`mkEnableOption`, priorities (`mkDefault` 1000, plain 100, `mkForce` 50, `mkOverride`), merge semantics per type (`lines` concatenate, `listOf` append, `attrsOf` union, `bool`/`str` conflict), `mkIf`/`mkMerge`, assertions/warnings, `_module.args`, specialisation, `config` vs `options` recursion traps |
| `nixos-options-map.md` | looking for "the option for X" | subsystem → option prefixes → module path in `nixos/modules/` at the pin; the query recipes (`nixos-option`, `nix eval .#nixosConfigurations.<h>.options.<path>.{type,default,description}`) |
| `systemd-units.md` | adding a unit, timer, socket, drop-in, tmpfiles rule | `systemd.services.<n>` fields vs raw `serviceConfig`; **PATH in units**: system and user units do not see `/run/current-system/sw/bin` — use `path = [ pkgs.x ]`, `runtimeInputs`, or an absolute `/run/current-system/sw/bin/<tool>` path, never `config.system.path` from a package that is itself in `environment.systemPackages` (eval cycle); user units + `ConditionUser` + linger + what a switch does not start; timers (`OnCalendar`/`OnBootSec`/`OnUnitActiveSec`/`Persistent`; a monotonic timer whose time has passed elapses on activation); socket activation; template units (`name@.service`, `%i` validation by regex plus allowlist, per-instance verbs, `journalctl -u 'name@*'`, matching an exact instance in a polkit rule); `systemd.packages` + drop-ins (`ExecStart=` reset); `tmpfiles.rules` (`d`/`z`/`L+`, mode adjustment of existing dirs) |
| `systemd-hardening.md` | confining a unit | every hardening directive used in this environment with what it blocks and the error you see when it blocks too much (`ProtectHome`, `ProtectSystem`, `DynamicUser`, `PrivateTmp`, `NoNewPrivileges`, `CapabilityBoundingSet`, `RestrictAddressFamilies`, `RestrictNamespaces`, `DeviceAllow` device groups, `UMask`, `ReadWritePaths`/`BindReadOnlyPaths`), `NetworkNamespacePath` and why rootless tools cannot `setns` a root-owned netns, `systemd-analyze security` reading, SupplementaryGroups vs DynamicUser |
| `activation-and-switch.md` | reasoning about what a switch/test does | `nixos-rebuild` verbs, `switch-to-configuration` rules at the pin (restart/reload/stop, `X-Restart-Triggers`, `restartIfChanged`/`reloadIfChanged`, sockets, user managers), specialisations (snapshot semantics — a specialisation directory is built at the last switch, not re-evaluated; `test` never touches the bootloader), generations and rollback, GC roots, `nix store diff-closures` (a base closure contains its specialisations'), the activation diff of two store paths |
| `packaging.md` | packaging or overriding software | `stdenv.mkDerivation` phases, fetchers and hashes (shown per §7's exception), `writeShellApplication`/`writeText`/`runCommand`, `buildGoModule`/`buildRustPackage`/`buildNpmPackage`, `override` vs `overrideAttrs`, overlays, `allowUnfree`/`permittedInsecurePackages`, FODs and `outputHash`, `passthru.tests`, `meta` |
| `python-and-cuda.md` | Python packages, torch, CUDA, NVIDIA | `python3.withPackages`, `buildPythonPackage` (pyproject/wheel formats), `packageOverrides` and the torch/torch-bin rule (prove with `torch.version.cuda`), `cudaPackages`/`cudaSupport`, `hardware.nvidia` open modules, `hardware.graphics.enable32Bit`, `nvidiaPackages.mkDriver`, build-tool version fixes (`av`/Cython-style) |
| `vm-tests.md` | writing or debugging a NixOS VM test | `pkgs.testers.runNixOSTest`/`nixosTest`, node config, `testScript` API (`succeed`/`fail`/`wait_for_unit`/`wait_for_open_port`/`wait_until_succeeds`), multi-node, users and lingering, `--offline` reproducibility, running interactively (`driverInteractive`), time and flakiness, negative proofs |
| `debugging.md` | any eval/build/exec failure | `--show-trace` reading, `nix repl` on a flake, `nix eval --json`, `nix why-depends`, `nix log`, `nix path-info -S`, infinite recursion patterns, "attribute missing" vs "option does not exist", sandbox failures, IFD; **foreign dynamically-linked binaries**: "Could not start dynamically linked executable" / exit 127 → `programs.nix-ld`, verify the binary through the real loader before shipping, never a reason to relax network controls |
| `nix-cli.md` | invoking nix | the nix 2.28 commands and flags that matter (`-L`, `--no-link`, `-o`, `--impure`, `--offline`, `--rebuild`, `--print-out-paths`, `--json`), `nix develop -c`, store commands, `nix-collect-garbage` and roots |
| `security.md` | firewall, polkit, wrappers, users | nftables/firewall composition (chains AND across hooks), `security.polkit.extraConfig` (duktape ES5: no `includes`, `===` fine, `indexOf`), `security.wrappers` (setuid/caps; when not to), `users.users` uids/groups, `DynamicUser` vs fixed users, secrets never in the store; `security.pam` as a one-line pointer only |
| `gotchas.md` | before committing anything | the traps generalised: `2>/dev/null` on gated commands, statix `{ ... }:`, `environment.etc` `lines` merge needs `mkForce`, specialisation closures in `diff-closures`, user timers not started by a switch, `services.xserver` renames at 25.05, `system.stateVersion`, hardware-configuration exemption, `builtins.getFlake` impurity, nix-ld for downloaded binaries, PATH in units |
| `review-checklist.md` | reviewing NixOS changes (Opus gate) | ordered checks: every option exists at the pin (command), priorities and merges are the intended ones (`lines` merge, `mkForce`), hardening is complete for the unit's job and the unit can still reach its tools (PATH), assertions cover the negative, tests discriminate (mutation survivors), closure and activation diffs match the plan (specialisation nesting), user units are started as documented, no secrets, no network at build |
| `verify.md` | mechanical verification | the exact commands and what "good" looks like: `nix flake check -L`, toplevel build, `nix store diff-closures`, activation diff of `/run/current-system` vs the new toplevel (units, `/etc`, tmpfiles), eval of a specialisation's marker |
| `refresh.md` | the pin moved | the procedure: bump the lock, run the checks, read the failure list (doc-tests, citations), fix each file, re-stamp, rerun evals and the isolation probe, record the delta in the results |

Seventeen files. A task loads the router plus one to three references:
roughly 3k–15k tokens depending on task shape (a hardened service with new
options is the common three-file case). The whole tree is never loaded.

## 6. Content rules

- **Stamp.** First line of every reference:
  `verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03`. Rewritten on refresh.
- **Citations.** Last section of every reference, `## Sources`, lists the
  pinned sources used: manual section ids, module paths under
  `nixos/modules/`, man pages. Machine-checked (§8).
- **Names in a fixed form** so scripts can find them: options as
  `` `services.foo.bar` `` (full path, backticked), lib functions as
  `` `lib.mkForce` ``, CLI commands always with their flags attached —
  `` `nix build --offline` ``, never a bare `` `--offline` `` — so the check
  can ask the right subcommand's `--help`.
- **Executable examples.** Every code block is tagged (§7). Prose examples
  that cannot be executed are written as `text` blocks, which the check
  ignores; the reviewer spot-checks that literal error strings match what
  nix 2.28.5 prints at the pin.
- **One right, one wrong.** For the idiom files — `nix-language`, `flakes`,
  `module-system`, `systemd-units`, `systemd-hardening`, `packaging`,
  `python-and-cuda`, `security`, `vm-tests` — each idiom shows the correct
  form and the common wrong form with the exact error it produces at the
  pin. The procedural files (`nixos-options-map`, `activation-and-switch`,
  `debugging`, `nix-cli`, `gotchas`, `review-checklist`, `verify`,
  `refresh`) are exempt.
- **Voice.** Imperative, explains why in one sentence, no history, no
  alternatives that don't apply at the pin. No project names.
- **Budgets.** Router ≤ 120 lines; reference ≤ 250 lines; a line ≤ 100
  characters. Breach fails a check. A file that cannot fit is split, never
  compressed into ambiguity.

## 7. Executable examples (doc-tests)

Every fenced block carries an info string of the form `nix <kind>` or
`bash <kind>` or `text`:

| kind | how the check exercises it | what it catches |
|---|---|---|
| `nix module` | wrapped as one module of a minimal `lib.nixosSystem` at the pin (`boot.loader.grub.enable = false`, a root fs, `system.stateVersion`), evaluated to `config.system.build.toplevel.drvPath` (no build; a few seconds each) | missing/renamed options, type errors, merge conflicts, assertion failures |
| `nix expr` | `nix eval --offline` of the expression with `pkgs`/`lib` in scope | wrong function names, wrong arity, wrong types |
| `nix package` | `nix build --offline` of the derivation, **after a static gate**: the block may not contain any fetcher (`fetch*`, `builtins.fetch*`, `fetchTarball`), `requireFile`, `dockerTools.pullImage`, `outputHash*`, `hash =`, `sha256 =` or `url =` — the check fails on sight, because a fixed-output derivation may download even under `--offline`. The gate is defence in depth: any FOD-shaped builder it misses still has to build offline in the sandbox, where its download fails and so does the check, so "no network reaches a doc-test" holds even where the token list is incomplete. Package examples use `writeText`/`runCommand`/`writeShellApplication` and sources already in the pinned store |
| `nix vmtest` | evaluate the test's driver derivation (no VM run) | node-config and option errors; Python script errors surface only at run time and are covered by the VM-graded eval tasks (§9) |
| `bash cmd` | shellcheck; and for every line whose first word is `nix`, the citations check asks that subcommand's `--help` for each flag | syntax, quoting, non-existent subcommands and flags |
| `text` | not checked | prose-only illustrations: error messages, outputs, and the one recipe that cannot run offline — the fake-hash loop for obtaining a hash (a wrong hash makes nix download, which is exactly what offline tests forbid); marked as such in the block's first line |

`tools/doctest.py` extracts the blocks into a generated Nix file under the
check's build directory and the flake check `doctests` evaluates or builds
them. An untagged code block fails the check (no unverified examples).

What doc-tests prove and do not prove: names, types, merges and buildability
at the pin. They do not prove runtime or activation behaviour. Guidance about
runtime behaviour (units, timers, switch semantics) is Opus-reviewed prose
against the pinned sources, and the VM-graded eval tasks (§9) are the
runtime evidence; the skill says so in its router.

## 8. Tests (flake checks; all offline)

| check | what it proves |
|---|---|
| `doctests` | every tagged example passes its kind's exercise (§7), including the static fetcher gate |
| `citations` | every backticked option path exists in the pin's options set (the minimal `lib.nixosSystem`'s `options` evaluated offline, same wrapper as the doc-tests); every `lib.*` name resolves; every `nix <subcommand> …` citation names a real subcommand and every attached flag appears in that subcommand's `--help` output (nix 2.28.5, run offline); every cited module path exists in the pinned source; every reference has a stamp and a `## Sources` |
| `budget` | line limits and line lengths (§6) |
| `lint` | treefmt (nixfmt, shfmt, ruff format), markdownlint, shellcheck, statix, deadnix, ruff check — also the pre-commit hook |
| `lock-guard` | the flake's nixpkgs rev equals the host pin |
| `router` | every reference file is listed in `SKILL.md` and vice versa; every name in a task→files row and every `skillRefs:` name in `evals/tasks/*/TASK.md` is an existing reference stem; role entries present |

## 9. Evals — proving grounds, first subject

Each eval is a factory-shaped task in a sealed seed flake at the pin:

```
evals/tasks/<name>/seed/     a minimal flake (nixpkgs pinned; sometimes a small existing module);
                             no CLAUDE.md, no docs, no memory — the without-arm must be skill-free
evals/tasks/<name>/TASK.md   frontmatter: skillRefs: [module-system, systemd-units]  (what the with-arm injects; same name as §10)
                             grader: check | vm                              (see below)
                             body: the task as a plan would state it, incl. the check that must pass
evals/tasks/<name>/expected.md   what a passing result contains (for the report, not the grader)
```

The grader is the seed's own `nix flake check` after the agent's changes,
plus the assertions a task declares. Tasks whose subject is runtime
behaviour (units, timers, hardening, VM tests, activation) declare
`grader: vm`: their seed's check boots a NixOS VM and asserts unit state,
so the skill's runtime guidance is scored by execution, not by eval. At
least six of the twenty tasks are `vm`-graded. Score per run: pass/fail,
output tokens, wall clock, fix iterations. Twenty tasks at launch across
the reference set (module with assertions, hardened service + timer, VM
test with a negative proof, package override, Python package with
`packageOverrides`, specialisation with a marker, firewall rule, polkit
rule for a template unit, debugging a broken flake, …). A task must be
solvable in one agent session.

`tools/run-evals.sh` runs the matrix with the Claude Code CLI headless
(`claude -p`, `/run/current-system/sw/bin/claude`), each run in a fresh copy
of the seed and a fresh `CLAUDE_CONFIG_DIR`:

- **Auth bootstrap.** A fresh config dir is not logged in. Once, the operator
  runs `claude setup-token` and stores the long-lived token in a file
  outside every repo (`~/.config/nixos-skill/claude-token`, mode 0600); the
  runner exports `CLAUDE_CODE_OAUTH_TOKEN` from that file into each session's
  environment before invoking `claude -p` (the CLI's own `setup-token` output
  names this variable; the mechanism the workspaces design verified on
  2026-09-02) and runs a one-line `claude -p`
  precheck before spending the budget. The token never enters a seed, a
  result file or the repo.
- **Isolation probe.** Depends on the operator's real install (§15 step 2
  precedes the evals). The runner plants a canary sentence in the installed
  `SKILL.md` (a fixed phrase that exists nowhere else) and runs two
  positive-control sessions: a fresh `CLAUDE_CONFIG_DIR` session asked for
  the canary must NOT produce it; a session with the with-arm injection (§10
  prompt text) MUST. The CLI has no "list skills" command at v2.1.258, so a
  self-report is not used. If the fresh-dir session knows the canary, the
  runner retries with a `HOME` override containing an empty `.claude`; if
  that also fails it refuses to run the without-arm and says so. Both probe
  results are recorded in every results file.
- model ∈ {sonnet} at launch (haiku, opus optional flags)
- skill ∈ {with, without}: "with" injects the router path and the task's
  `skillRefs` files into the prompt with the same template the factory uses (§10)
- trials: 5 per cell, paired by task; sessions run 4 in parallel; `--tasks`
  and `--trials` flags scale the run down for a smoke test

Results go to `evals/results/<date>.json`; `tools/report.py` renders pass
rates, token and time distributions per cell, the paired per-task
differences and their confidence interval (§12). Runs are not a flake check
(they cost tokens and need the CLI); they are the operator-visible
acceptance artifact and the release gate.

## 10. Loading by role (change to nixos-agent-env `tools/factory/dark-factory.js`)

New optional arg `skills: { nixos: "/home/dalhaka/flakes/nixos-skill/skills/nixos" }`
and a new optional per-task field `skillRefs: ["systemd-units", "vm-tests"]`
(reference stems, chosen by the plan author). `kind` stays what it is
(`code`|`docs`, the review path) and is never used for routing. When
`skills` is present the script injects into each role's prompt:

- implementer: "Read `<path>/SKILL.md` first. Then read these references:
  `<path>/references/<stem>.md` …" (from `skillRefs`); when the task has no
  `skillRefs`: "…then pick from the router's task → files table using this
  task's title and spec text. Name the files you read in your report."
- Opus code reviewer: "Read `<path>/references/review-checklist.md` and
  `gotchas.md`; apply the checklist in order."
- docs reviewer: "Read `<path>/references/nix-cli.md` and
  `activation-and-switch.md` before checking any command in the document."
- verifier: "Follow `<path>/references/verify.md`."

The change is one small task in nixos-agent-env with a check that the
rendered prompts contain the paths for each role. The skill-writing tasks
themselves (§10.1) are classified `kind: code` so they get the Opus
adversarial gate; only the runbook/README task is `docs`.

### 10.1 Build plan sizing (for the operator's gate; the plan itself follows)

| task | kind | deliverable |
|---|---|---|
| T0 (nixos-agent-env) | code | `skills`/`skillRefs` in dark-factory.js + prompt check |
| T1 | code | repo bootstrap: flake, devShell, lint gate, hooks, `budget`, `router`, `lock-guard` checks, doctest/citation tool skeletons with their unit tests |
| T2 | code | router + `nix-language`, `flakes`, `module-system`, `nix-cli` |
| T3 | code | `systemd-units`, `systemd-hardening`, `activation-and-switch`, `security` |
| T4 | code | `packaging`, `python-and-cuda`, `vm-tests`, `debugging` |
| T5 | code | `nixos-options-map`, `gotchas`, `review-checklist`, `verify`, `refresh` |
| T6 | code | `doctests` + `citations` checks complete and green over all files |
| T7 | code | twenty eval seeds with graders (≥ 6 VM-graded), `run-evals.sh` (auth bootstrap, isolation probe, parallelism), `report.py` |
| T8 | docs | runbook (install, run evals, refresh), README, board copy |

Extrapolated from the logged runs (Helm 22 agents / 2.05M tokens / 105 min
for 6 tasks; media rework 18 / 2.16M / 164 min for 4; wiring round 1 8 /
0.8M / 53 min for 2): about 4–5 agents and 0.4–0.5M tokens per code task →
**≈ 40 agents, ≈ 4M Sonnet/Opus tokens, ≈ 5–6 h sequential** for T0–T8,
before the eval run (§14). Fix rounds capped at 2 as usual.

## 11. Install and interactive use

`mkdir -p ~/.claude/skills && ln -s ~/flakes/nixos-skill/skills/nixos
~/.claude/skills/nixos` — one operator command in the runbook, followed by
the acceptance step "a fresh Claude Code session in any flake lists `nixos`
among available skills" (verifies that a symlinked skill directory is
discovered; if not, the runbook falls back to a tmpfiles `L+` rule or a copy,
and the spec is amended). Interactive sessions rely on the description; that
is a convenience, not the design's load path.

## 12. Measurement and release criterion

1. **Evals (§9).** Paired design: for each of the 20 tasks, the with-arm
   and without-arm pass rates over 5 trials give one per-task difference.
   Release requires (a) the mean per-task difference at Sonnet to be
   positive with a 95 % bootstrap confidence interval whose lower bound is
   at least +10 points (the report prints the interval; a bare threshold is
   not a test), and (b) median output tokens per passing run no more than
   20 % above the without-arm. Sequential rule: the runner evaluates the
   interval when 10, 15 and 20 tasks are complete (all trials, both arms) and may stop
   early once the interval is clearly above or clearly below the bar (with five
   coarse per-task differences a bootstrap interval rarely resolves, so early
   stops are expected only at the later checkpoints);
   otherwise it runs all 20. The report is committed.
2. **Production.** Wiring round 2 and Helm v1 run with `skills.nixos` set
   and `skillRefs` on every task. The board records agents, fix rounds, Opus
   findings by class, tokens and wall clock next to the earlier runs (Helm
   22 agents / 2 rounds at the cap; wiring round 1 8 agents / 0 rounds;
   media rework 18 agents / 2 rounds). Interpretation is qualitative —
   different tasks — but a fall in fix rounds on NixOS-shaped defects
   (PATH in units, merge semantics, hardening) is the signal sought.

## 13. Refresh when the pin moves

Bump `flake.lock`; `nix flake check` fails wherever the pin changed
behaviour (doc-tests, citations, lock-guard); a factory task fixes each
failing file from the new pin's sources, re-stamps it, reruns the isolation
probe and the evals and records the delta. `refresh.md` is the agent-facing
version of this paragraph.

## 14. Risks, costs and open questions

- **Symlinked skill discovery** is unverified until install (§11 has the
  fallback); **config-dir isolation** for the without-arm is unverified until
  the probe (§9 has the fallback and the refusal).
- **Headless auth**: depends on `claude setup-token` producing a token the
  `-p` mode accepts from a seeded config dir; T7 verifies this before any
  budget is spent, and the runbook records the CLI version.
- **Doc-test cost**: a `lib.nixosSystem` eval per module snippet is seconds
  each; ~150 snippets ≈ minutes. Package snippets are trivial builders only.
- **Eval run cost**: 20 tasks × 2 arms × 5 trials = 200 headless sessions.
  At an estimated 30–50k output tokens per session (small tasks, one
  session each) that is ≈ 6–10M Sonnet tokens and, at 4 sessions in
  parallel and ~5 min each, ≈ 4–5 h wall clock; the sequential stop rule
  usually ends it earlier, and `--trials 3` gives a cheaper first look
  (≈ 4–6M). The board logs the actual numbers.
- **Build cost**: ≈ 40 agents / ≈ 4M tokens / 5–6 h (§10.1).
- **Runtime claims** are Opus-reviewed prose plus VM-graded evals, not
  doc-tests (§7); the router says so.
- **Skill vs CLAUDE.md overlap**: `gotchas.md` generalises lessons that also
  live in nixos-agent-env's CLAUDE.md and memory; the skill states the
  general rule, CLAUDE.md the project's instance. Acceptable duplication.

## 15. Acceptance (operator, plain language)

1. `cd ~/flakes/nixos-skill && nix flake check -L` — all green (doc-tests,
   citations, budget, lint, lock-guard, router).
2. `mkdir -p ~/.claude/skills && ln -s ~/flakes/nixos-skill/skills/nixos
   ~/.claude/skills/nixos`; a fresh session in `~/flakes/gaming` lists the
   `nixos` skill.
3. `claude setup-token` once (interactive), store it as the runbook says;
   the runner's precheck and isolation probe both report OK.
4. The eval report in `evals/results/` shows the with-arm ahead by the
   §12 interval.
5. Nightly backup covers the repo (already inside `~/flakes`).

## 16. Queued for later (not in this spec)

- Proving-grounds experiment "code graph vs embedding RAG vs none" on this
  runner (docs/concepts/concept-2026-09-02h-proving-grounds.md, queued
  2026-09-03).

## 17. Changes from rev 1 (adversarial review, 2026-09-03)

Confirmed blockers: F1 routing by `task.kind` was unimplementable →
`skillRefs` + router phrases (§5.1, §10); F3 `--offline` does not stop
fixed-output downloads → static fetcher gate, no FODs in examples (§2, §7);
F4 fresh config dirs have no auth → `setup-token` bootstrap + precheck (§9,
§15); F5 `~/.claude/skills` missing → `mkdir -p` (§4, §11, §15); F6
underpowered bare threshold → paired design, 5 trials, bootstrap interval,
sequential stop, costs stated (§9, §12, §14); F7 without-arm isolation
unverified → probe with fallback and refusal (§9). Majors: F8 honest token
budget and combo rows; F9 PATH-in-units bullet and the systemd split; F10
Opus reads `gotchas` too; F11 docs-reviewer role; F12/F21 flags cited with
their command and checked via the subcommand's `--help`, bash blocks
included; F13 the hash-loop recipe as a documented `text` exception; F14
runtime claims scoped, VM-graded eval tasks; F15 sizing table (§10.1); F16
reference tasks are `kind: code`; F17 `skillRefs:` in TASK.md; F18 template
units; F19 nix-ld. Minors: F20 rule scoped; F22 skill-free seeds; F23 pam
as a pointer; F24 reviewer spot-checks error strings. Refuted: F2 (vmtest
eval-only does catch node-config errors; the runtime residue is now covered
by VM-graded evals).

Rev 2.1 (confirmation pass, 3 Sonnet lenses: 23/23 findings addressed with a
mechanism; new items folded): headless auth is the CLI's own
`CLAUDE_CODE_OAUTH_TOKEN` export per session, not a config-dir file (§9);
the isolation probe is a canary positive control because the CLI has no
"list skills" command (§9), and the install step now precedes the evals in
§15; `skillRefs` is the one field name in both repos (§9, §8); the fetcher
gate names `requireFile`/`pullImage`/`hash =`/`sha256 =` and states the
offline build as its backstop (§7); sequential checkpoints at 10/15/20 with
the expectation stated (§12).
