# Opus gate — a4/N7c (75104e9) — REWORK

## Citations: all three verified
`dsh-hooks-claude-code/lib/index.js:183` — `runHook(ctx.shell, hook, {...})`, options carry
`payload/env/cwd/signal` and **no `sandboxPolicy`**. `dsh-bash-sandbox/lib/index.js:137-141` —
`sandboxPolicy: request.sandboxPolicy ?? this.ctx.sandboxPolicy.resolve()` (ambient fallback).
`dsh-sandbox-local/lib/index.js:33-37` — under `workspace-write`, bwrap gets exactly
`--tmpfs /tmp` + `--bind workspaceRoot workspaceRoot` over a `--ro-bind / /`. Diagnosis is right.

## Is the transcript already a sufficient audit? Yes.
HOOKPROBE session, decompressed: `tool/call` seq 1093 carries `{"command":"sudo true"}`;
`hook/invoked` seq 1094 (`matcher:"bash"`); `hook/result` seq 1095 `decision:"deny"`;
`tool/result` seq 1096 carries the verbatim reason `Error: sudo is refused (an operator
action)`, `isError:true`, `sourceEventSeqs:[1093]`. Command + decision + reason + timestamps,
in `$DSH_HOME/sessions` — outside both writable roots, so the model cannot touch it.

## The better mechanism already exists in the pin
`dsh-hook-protocol/lib/index.js:332-345` `appendHookResult` writes
`stderrSummary = summarizeStderr(output.stderr, ...)` **into the `hook/result` event**;
`:296` caps it at 500 chars; `:102-126` `parseHookOutput` records stderr at exit 0 without
letting it affect the decision. A guard that prints its JSON record to **stderr** gets a
durable audit line inside the un-writable transcript, for free. The branch already added a
stderr writer (`hook-guard.py:145-151`) — but only on the failure path.

## Why the workspace file is the wrong home
- **(a) erasable by the audited party.** Probed the guard directly: `rm -f
  .dsh-hook-denials.log`, `: > .dsh-hook-denials.log`, and `write` to
  `$workspace/.dsh-hook-denials.log` — **all three allowed** (exit 0, no deny). `_bash_verdict`
  covers only sudo/nixos-rebuild/systemctl/key-file; `_edit_verdict` blocks only *outside* the
  project dir. The log sits inside it by construction.
- **(b) unmitigated tree dirt.** `workspace=$(pwd -P)` (`dsh-openrouter.sh:163`), log at `:347`.
  No `.gitignore` entry added. `tools/factory/dark-factory.js:348` and `:574` both require
  `git status --porcelain` empty — a seat run in a factory workspace now breaks integration.
- **(c) scattered.** One log per workspace ever used, vs. one `sessions/` tree.

## Recommendation
Drop the workspace file. Emit the denial record on **stderr** (transcript, model-unreachable),
keep the transcript as the audit of record, add a documented `dsh-openrouter journal`/`denials`
reader (`session.jsonl.zstd`, filter `hook/result.decision=="deny"` joined to `tool/call`).
Retarget the two new tests: stderr-always (not only on write failure), and hooks.json carrying
no `DSH_HOOK_DENIAL_LOG` at all. Honest gap: the stderr→`stderrSummary` path is code-verified,
**not observed** — no existing session carries a `stderrSummary`; one headless probe closes it.

## Verification
RED (guard+wrapper hunks reverse-applied, tests kept): `unit` fails — `not ok 81 hooks.json's
denial log lives under the workspace`, and the stderr case on
`[[ "$stderr" == *"DSH_HOOK_DENIAL_LOG"* ]]`. GREEN at 75104e9: `unit` exit 0; lint exit 0.

| # | Mutation | Test that dies |
|---|---|---|
| M1 | `hooks_log=$DSH_HOME/hook-denials.log` | "denial log lives under the workspace" |
| M2 | swallow `OSError` silently (main's `return`) | "still denies, and reports on stderr" |
| M3 | failure message to stdout not stderr | "still denies, and reports on stderr" |
| M4 | log failure aborts the process | "still denies, and reports on stderr" |
| M5 | only the `bash` matcher gets the env var | "denial log lives under the workspace" |
| M6 | drop `[ ! -e "$blocked/x.log" ]` | **none** — dir is 0500; tautological |

(Test "--dump-config mounts the hooks bridge" fails under bare `bats` in this environment at
baseline too — environmental, not a branch defect; it passes under `nix build …#unit`.)
