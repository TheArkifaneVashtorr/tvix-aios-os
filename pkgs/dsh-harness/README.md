# dsh-harness

The DeepSeek Harness (DSH) setup for the operator's seats, ported from the
Fable 5.1 Claude Code setup and kept in its own git so the Claude version
(`~/nixos-agent-env`, `~/.claude`) stays untouched.

## Contents

- `skills/` — the skill catalog:
  - the `superpowers` workflow set (14 skills) copied from
    `superpowers@claude-plugins-official` v6.3.0 (MIT © 2025 Jesse Vincent),
    then adapted for DSH: the 26 `superpowers:` cross-skill prefixes are
    stripped to bare skill names (dsh's skill-name grammar forbids a colon);
    the cross-skill file paths keep their `../<skill>/…` form — dsh resolves a
    skill's relative paths against that skill's own directory, and `../`
    reaches the sibling skill in the vendored layout;
  - the `nixos` skill copied from `~/flakes/nixos-skill/skills/nixos`;
  - `driving` — the four verbs that run, gate and land a typed plan's tasks
    (brief, dispatch, gate and integrate as calls to `tools/factory/seat`),
    written for the operator's seat, not the vendored superpowers set;
  - `using-superpowers/references/dsh-tools.md` — the action→tool map for DSH
    (the one DSH-specific file; the other skill bodies are otherwise as-copied).
- `AGENTS.md` — the bootstrap + durable-memory index, deployable to
  `$DSH_HOME/AGENTS.md`.

## Deploy (manual symlinks — flake deferred)

flake packaging is explicitly deferred — this repo ships no `flake.nix`; the
`git+file://…?ref=main` input pattern in `~/nixos-agent-env/flake.nix` is the
model to copy when it is done. Until then, deploy by manual symlink.

DSH discovers skills from `.dsh/skills` (per project), `$DSH_HOME/skills`
(`~/.local/share/dsh-openrouter/skills` for `dsh-openrouter`), and
`~/.agents/skills`. To make these skills available to every repo:

    ln -s ~/flakes/dsh-harness/skills ~/.local/share/dsh-openrouter/skills

To load the bootstrap memory every session:

    ln -sf ~/flakes/dsh-harness/AGENTS.md ~/.local/share/dsh-openrouter/AGENTS.md

## Re-sync the nixos skill

    rm -rf ~/flakes/dsh-harness/skills/nixos
    cp -R ~/flakes/nixos-skill/skills/nixos ~/flakes/dsh-harness/skills/nixos

## Deliberately not ported

`host-and-keys` (secrets / YubiKey ledger, local-only), `project-status` (dated
handoff → `docs/OPERATIONS.md` START HERE), the `feature-dev` named subagents
and `code-review` slash command (DSH subagents are prompt-driven; the factory
already encodes those roles).

## Model routing

The seat's sub-agents choose their model from the routing table, never from
memory:

    . ~/nixos-agent-env/tools/factory/seat/factory-lib.sh && factory_route --route openrouter <role> <kind> <size>

prints `MODEL EFFORT`. Roles: implement | review | verify | research | baseline | audit | plan; kind: code | docs;
size: XS | S | M | L (from the task's `### KEY (kind, size)` heading; `any` when unknown). Pass the model as the
sub-agent's `model` override and the effort as `OPENROUTER_REASONING_EFFORT`. Rows with `route = "claude"` are not
reachable from this seat and are never requested. `FACTORY_ROUTING_TABLE` overrides the table path. Kimi K3 and
GLM 5.3 are picker extras with no row yet; do not select them by hand.

The `plan` role routes kind `docs`, sized by the spec's word count
(the S/M/L boundary from the `wc -w` of the spec); it has no row in the table
yet, so its lookup falls through to the openrouter default. It is added to
`~/nixos-agent-env/docs/ledger/routing.toml` when the operator decides a row
for it.

The table lives in `~/nixos-agent-env/docs/ledger/routing.toml`; change rows
there, nowhere else. A task's rung is the table's own rung number, read by
the driver scripts from the task's key, never chosen by a prompt.

A whole-tree model-choice gate (a case-insensitive `grep -rn` over the tree
minus `.git` and the archive) must print nothing. It matches any per-dispatch
tier-escalation wording and every retired picker model id — the exact
alternation ships in the commit that introduced it — so no prompt template,
README, or skill reference can reintroduce a per-dispatch model choice or a
stale model id. The routing table stays the one place a model is chosen.

## Archived: planning factory

The multi-model planning→build factory (parallel planning lenses, consolidation,
build, wave-scheduled cross-review) is archived in place at
`archive/2026-09-05-planning-factory/` (operator decision 2026-09-05). See that
directory's `README.md` for what it was, why it was archived, and the command
that still runs its tests. Nothing in this repo dispatches it, and its
role→model map is retired with it.

The repo's own check surface is now empty: the factory's self-test suite was the
only build gate this repo carried (it ships no `flake.nix`), and it moved into
the archive — the command that still runs those tests lives in the archive's
own `README.md`.
