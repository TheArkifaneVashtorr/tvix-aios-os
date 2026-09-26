# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is, and the one rule that matters most

A NixOS flake building AI-agent environments in graded isolation: encrypted
"baskets", a TLS-terminating egress broker, build-time classification
assertions, and the host config itself. **The host `core` runs LIVE from this
repo** (`nixosConfigurations.core`). Everything you do is build-only: never
`sudo`, `nixos-rebuild`, `systemctl start/stop/restart`, or basket
mount/teardown — the operator switches and runs the acceptance scripts.
Governing spec: `docs/brief.md` (§3 invariants). Board of record:
`docs/OPERATIONS.md`.

## Commands

All tooling lives in the devShell; nothing (not even `jq`, `python3`, `bats`)
is on the host PATH. `grep` on this host is ugrep.

```bash
nix develop -c githooks/pre-commit          # the full lint gate (treefmt, shellcheck, statix, deadnix, ruff)
nix flake check -L                           # every check, incl. NixOS VM tests (minutes)
nix build .#checks.x86_64-linux.<name> -L --no-link   # one check
nix develop -c bats tests/unit               # all bats unit tests; one file: bats tests/unit/50-doctor.bats
nix develop -c tests/run-mount-tests.sh      # mount lifecycle under both propagation modes (userns, no root)
nix develop -c pytest tests/broker -q        # broker policy tests
evidence bundle --markdown                     # live facts: generation, heads, checks covering HEAD, Helm since-when, open gaps
nix develop -c python3 pkgs/evidence/tasks.py --root . brief   # the task queue / status brief
python3 pkgs/evidence/repomap.py --root . write                # regenerate docs/MAP.md
nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"
dsh-openrouter --denials [N]                  # read back the seat hook guard's denial audit (docs/runbooks/lanes.md)
nix run ~/nixos-agent-env#seat-submit -- web --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter --model deepseek/deepseek-v4-pro-0813 --effort medium --port 43210   # OPERATOR ONLY — a web seat behind the broker; the URL: journalctl -u seat@<id>.service (docs/runbooks/seat.md)
nix build .#nixosConfigurations.core.config.system.build.toplevel   # what a switch would activate
nix store diff-closures /run/current-system ./result               # prove the change is only what you meant
nix develop -c git commit -F <msgfile>       # commits must go through the devShell so the hook has its tools
```

Gotchas that have cost real time: `git add` new files before any `nix build`
(flakes only see tracked files); statix rejects `{ ... }:` module headers —
write `_:`; never `2>/dev/null` a gated command (it once swallowed a lint
refusal); `hosts/core/hardware-configuration.nix` is verbatim generator output
and exempt from formatting; a NixOS switch does not start newly enabled *user*
timers in an already-logged-in session; under an agent harness's sandbox
`$HOME` is read-only, so set a stable `XDG_CACHE_HOME` under `/tmp`; an agent's
shell tool and its file tools may see *different* `/tmp`, so name one
per-session scratch directory and use it for both.

## Where things are

`docs/MAP.md` is generated and always current: modules, packages, every check
name, tests, hosts, tools (regenerate: `python3 pkgs/evidence/repomap.py write`).
Facts at session start come from the hook `tools/session-start.sh` (runbook
`docs/runbooks/session.md`): the board's START HERE, `evidence bundle`, and the
task brief `evidence tasks --root . brief`.

## How work is done here

Phases with acceptance tests (brief §7), each gated on the operator saying
"test passed". The orchestrator writes plans, specs, decisions, concepts and
runbooks; agents write and review all code (`tools/factory/dark-factory.js`
through the Workflow tool, models per role fixed). Day-to-day tasks run through
the seat driver, gated by `factory-review`. TDD: the failing check first, and a
load-bearing test counts only once it has been shown to fail (red before the
change). New language ⇒ its formatter and linter land in the same task. Commit
subjects: `<area>: summary (test: <check names>)`, with the `Co-Authored-By`
trailer. The queue is derived by `evidence tasks`, never typed into the board.
The operator reads tool names literally; terse reports, decisions and risks at
the end of a turn.