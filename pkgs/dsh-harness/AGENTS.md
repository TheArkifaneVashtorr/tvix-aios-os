# AGENTS.md

Bootstrap + durable memory for the DeepSeek Harness (DSH) seat. Canonical copy
lives in this repo; deploy it to the harness's global instruction file so it
loads every session: `$DSH_HOME/AGENTS.md` (for `dsh-openrouter`,
`~/.local/share/dsh-openrouter/AGENTS.md`).

## Skills first (the superpowers bootstrap)

The skills in this repo's `skills/` directory are ported from the operator's
Fable 5.1 Claude Code setup. Deployed to the DSH skill root
(`~/.local/share/dsh-openrouter/skills` or `~/.agents/skills`), the DeepSeek
seat sees the same catalog. Before any response or action — including
clarifying questions — check the session skill catalog and invoke every skill
that matches via the `skill` tool. Tool-name mapping for this harness is in
`skills/using-superpowers/references/dsh-tools.md`.

## Durable memory index

The operator's Claude memory (working style, factory policy, project status,
field lessons, host/keys) stays in the Claude version — `~/nixos-agent-env`
(`CLAUDE.md`, `docs/OPERATIONS.md` START HERE) and `~/.claude` memory. Never
copy `~/.claude/projects/*/memory` into a repo: it is `local-only`.

## DSH-specific notes

- Web tools (`web_search` / `web_fetch`) are disabled in the `dsh-openrouter`
  seat; treat them as unavailable.
- Choose a sub-agent's model from the routing table, never from memory:
  `. ~/nixos-agent-env/tools/factory/seat/factory-lib.sh && factory_route --route openrouter <role> <kind> <size>`
  prints `MODEL EFFORT`. Roles: implement | review | verify | research | baseline | audit | plan; kind: code | docs;
  size: XS | S | M | L (from the task's `### KEY (kind, size)` heading; `any` when unknown). Pass the model as the
  sub-agent's `model` override and the effort as `OPENROUTER_REASONING_EFFORT`. Rows with `route = "claude"` are not
  reachable from this seat and are never requested. `FACTORY_ROUTING_TABLE` overrides the table path. Kimi K3 and
  GLM 5.3 are picker extras with no row yet; do not select them by hand.
- The archived planning factory's self-test suite still runs from its archive
  path (see `archive/2026-09-05-planning-factory/README.md`); a bare `node
  --check` on the script can never pass because it is an async-function body
  (top-level `await`/`return`).
- The driver seat's four verbs — brief, dispatch, gate and integrate a typed
  plan's tasks — are the `driving` skill (`skills/driving`).

## Commit convention

Every commit this seat authors carries exactly ONE machine-set trailer and no
`Co-Authored-By` line:

    Generated-By: <harness> / <model> (<context>)

The factory fills in all three parts — the harness identity (`args.harness`, e.g.
`dsh 0.1.2-rc.1`), the model id (routed via `factory_route --route openrouter`
from the routing table above, not from memory), and the seat/run context
(`args.factoryContext`, e.g. `seat headless, factory run b8`) — so an
implementer never writes or guesses its own trailer. Subject
`<prefix>: <summary> (test: <check names>)`, with a body paragraph stating the
WHY.
