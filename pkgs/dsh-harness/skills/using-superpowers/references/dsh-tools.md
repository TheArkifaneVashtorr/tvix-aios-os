# DSH (DeepSeek Harness) Tool Mapping

Skills speak in actions ("dispatch a subagent", "create a todo", "read a
file"). On the DeepSeek Harness these resolve to the tools below. This is the
harness's own tool set, so prefer the native tool over running something in a
shell.

| Action skills request | DSH equivalent |
| --- | --- |
| Invoke a skill | `skill` — pass the exact skill name from the session skill catalog; load its full instructions before acting on a task it matches |
| Dispatch a subagent (`Task` / general-purpose) | `subagent` (background by default; returns a durable id to steer/collect), or `subagent_fork` when the child must inherit this conversation's context |
| Fan out to many subagents at once | `workflow` — a JS coordinator script, or `dispatching-parallel-agents` via several `subagent` calls |
| Create / update a todo | `todo_write` — sends the COMPLETE list every call; it replaces, never patched in place |
| Read / write / edit a file | `read`, `write`, `edit` (edit is literal find-and-replace) |
| Run a shell command | `bash` — each call is a fresh shell; pass `workdir` instead of `cd`. Long-running work: `run_in_background: true` then `job_output` / `job_kill` |
| Find files by name / search contents | `glob` (path patterns), `grep` (ripgrep) |
| Clarify intent / ask the human | `ask_user_question` |
| Present a plan for approval (plan mode) | `exit_plan_mode` — sends the complete plan and leaves plan mode only on approval |
| Pursue one long-running objective across turns | goal tools: `create_goal`, `get_goal`, `update_goal` |
| Track / stop a background job | `job_list`, `job_output`, `job_kill` |
| Web fetch / search | `web_fetch`, `web_search` — NOTE: the operator's `dsh-openrouter` seat disables the harness's own web tools; treat web as unavailable there |
| Checkpoint / human gate between tasks | No native checkpoint. Use `todo_write` progress + stop at phase boundaries; this repo's convention is "gates hold — the operator says 'test passed' before the next phase" |

## Subagents

DSH ships first-class subagents: `subagent` (isolated context; returns its
result), `subagent_fork` (inherits this conversation's completed turns),
`workflow` (fan-out orchestration), and `list_agents` / `send_message` /
`interrupt_agent` to steer and stop them.

Choose a sub-agent's model from the routing table, never from memory:
`. ~/nixos-agent-env/tools/factory/seat/factory-lib.sh && factory_route --route openrouter <role> <kind> <size>`
prints `MODEL EFFORT`. Roles: implement | review | verify | research | baseline | audit | plan; kind: code | docs;
size: XS | S | M | L (from the task's `### KEY (kind, size)` heading; `any` when unknown). Pass the model as the
sub-agent's `model` override and the effort as `OPENROUTER_REASONING_EFFORT`. Rows with `route = "claude"` are not
reachable from this seat and are never requested. `FACTORY_ROUTING_TABLE` overrides the table path. Kimi K3 and
GLM 5.3 are picker extras with no row yet; do not select them by hand.

## Task lists

Use the native `todo_write` tool. Older Superpowers docs may say `TodoWrite` —
treat that as "create/update a todo via `todo_write`".

## Plan mode

The `writing-plans` / `executing-plans` skills' "checkpoint" and "present the
plan" steps map to `exit_plan_mode` (interactive) or `todo_write` + a terse
turn report (headless). There is no persistent on-disk checkpoint file.
