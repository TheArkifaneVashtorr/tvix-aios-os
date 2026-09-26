# Opus gate — seat run rt5, task RT5 — REJECTED

## Summary

The structured half of the rule is right and well tested: a `subagent` /
`subagent_fork` / `workflow` launch whose `tool_input.model` is not the `model`
of an `openrouter` row of `docs/ledger/routing.toml` is denied with the plan's
exact wording, claude rows (`fable`/`sonnet`/`opus`) never allow, no model
allows, a missing or malformed table fails closed for an explicit model, every
denial is audited, and the wrapper puts `--routing-table '<resolved>'` on all
three matchers. Verified first-hand, not read: 43 payloads through the guard, a
synthetic dsh transcript read back by `dsh-denials`, three `--dump-config` runs,
four checks, a red run against the base guard, and ten mutations.

It is rejected on the *other* half — the nested-seat bash rule, which the plan
calls "how a launch would bypass the sub-agent tools" and which is the **only**
barrier on that path (`dsh-openrouter.sh:94` accepts any `--model` value without
consulting the table).

- **MAJOR-1** — the bash scan is defeated by the two most ordinary spellings of
  the same command: `--model "z-ai/glm-5.3"` / `--model 'z-ai/glm-5.3'` /
  `OPENROUTER_MODEL="z-ai/glm-5.3"` and a `\`-newline continuation are all
  **ALLOWED**, and each is what the shell then executes as that model. The
  continuation case is one the gate enumerated as must-deny.
- **MAJOR-2** — the nested-seat rule is partly vacuous: mutations M5 (drop the
  `--model=` equals form) and M10 (make the `OPENROUTER_MODEL=` regex match
  nothing) both **survive** the committed suite. The one `OPENROUTER_MODEL`
  test asserts *allow*, so it passes with that half of the rule dead — no test
  in the tree fails if `OPENROUTER_MODEL=<non-row>` stops being denied.

Fix round is small and local to `_MODEL_FLAG` / `_OPENROUTER_MODEL_ENV` plus
three tests; everything else here can stand.

## Rule behaviour (payload table)

Driven by hand: `python3 pkgs/dsh-openrouter/hook-guard.py --routing-table <path>`
with a `{"hook_event_name":"PreToolUse","tool_name":…,"tool_input":…}` document
on stdin (`main()` reads `--routing-table` / `--routing-table=` from argv, then
`$FACTORY_ROUTING_TABLE`, then `$HOME/nixos-agent-env/docs/ledger/routing.toml`).
Table = the committed `docs/ledger/routing.toml` unless stated.

| # | tool | input | want | got |
| --- | --- | --- | --- | --- |
| 1 | `subagent` | `model: z-ai/glm-5.3` | deny | **DENY** `sub-agent model z-ai/glm-5.3 is not a row of <table> (route openrouter); pick a role and let the table choose` |
| 2 | `subagent` | `model: deepseek/deepseek-v4-flash` | allow | ALLOW (no output) |
| 3 | `subagent` | no `model` | allow | ALLOW |
| 4 | `subagent` | `model: opus` (claude row) | deny | **DENY** `opus is not a row of …` |
| 5 | `subagent_fork` | `model: z-ai/glm-5.3` | deny | **DENY** |
| 6 | `workflow` | `model: z-ai/glm-5.3` | deny | **DENY** |
| 7 | `subagent` | explicit model, table path missing | deny | **DENY** `routing table unreadable at /nonexistent/routing.toml` |
| 8 | `subagent` | no model, table path missing | allow | ALLOW |
| 9 | `subagent` | explicit model, malformed TOML | deny | **DENY** `routing table unreadable at …` |
| 10 | `subagent` | no model, malformed TOML | allow | ALLOW |
| 11 | `bash` | `dsh-openrouter --model moonshotai/kimi-k3 --headless x` | deny | **DENY** |
| 12 | `bash` | `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 dsh-openrouter --headless x` | allow | ALLOW |
| 13 | `bash` | `OPENROUTER_MODEL=z-ai/glm-5.3 dsh-openrouter …` | deny | **DENY** |
| 14 | `bash` | `dsh-openrouter --model=z-ai/glm-5.3 …` (equals form) | deny | **DENY** |
| 15 | `bash` | `bash -c 'dsh-openrouter --model z-ai/glm-5.3 …'` (nested) | deny | **DENY** (string scan) |
| 16 | `bash` | `sudo ls` / `git status` / `edit /etc/passwd` | deny / allow / deny | unchanged from base |

Message wording matches the plan byte for byte, including `(route openrouter);
pick a role and let the table choose` and `routing table unreadable at <path>`.

**Audit.** Every denial above emitted the JSON record on stderr
(`{"ts","event":"PreToolUse","tool","reason","subject"}`, 334 chars for case 1
with my long clone path; ~290 with the real seat path; the existing truncation
loop keeps it under 400). Read back end to end: I built a session transcript
with a `hook/result` event carrying that verbatim `stderrSummary` and ran
`dsh-denials` against a throwaway `DSH_HOME` — it printed
`1788560000.140  {…"tool":"subagent"…"subject":"z-ai/glm-5.3"}`, exit 0. So a
model denial reaches `dsh-openrouter --denials` like every other rule.

**Rule surface is real, not imagined.** The pinned harness
(`dsh-0.1.2-rc.1`) defines `TOOL_SUBAGENT` and `TOOL_WORKFLOW`, and the harness
reference (`~/factory/base/dsh-harness/skills/using-superpowers/references/dsh-tools.md`)
names `subagent`, `subagent_fork`, `workflow` and says the model is passed as
"the sub-agent's `model` override" — the key the guard reads.

## Bypass attempts

Each row is a command a seat model could type; "shell result" is what bash
would actually execute.

| attempt | shell result | want | got |
| --- | --- | --- | --- |
| `model: Z-AI/GLM-5.3` (case variant, subagent) | — | deny | **DENY** (exact match is the rule; a case variant is not a row) |
| `--model Z-AI/GLM-5.3` (bash) | runs that id | deny | **DENY** |
| `--model  z-ai/glm-5.3` (two spaces) | runs it | deny | **DENY** |
| `--model\tz-ai/glm-5.3` (tab) | runs it | deny | **DENY** |
| `--model \`⏎`z-ai/glm-5.3` (continuation) | runs it | deny | **ALLOW — MAJOR-1** |
| `env OPENROUTER_MODEL=z-ai/glm-5.3 dsh-openrouter …` | runs it | deny | **DENY** |
| `export OPENROUTER_MODEL=z-ai/glm-5.3; dsh-openrouter …` | runs it | deny | **DENY** |
| `tool_input.provider=anthropic` + `model: opus` | — | deny | **DENY** (on the model alone) |
| `tool_input.provider=z-ai` + `model: deepseek/deepseek-v4-flash` | — | ? | ALLOW — `provider` is never read (MINOR-1) |
| `--model "z-ai/glm-5.3"` (double quotes) | runs it | deny | **ALLOW — MAJOR-1** |
| `--model 'z-ai/glm-5.3'` (single quotes) | runs it | deny | **ALLOW — MAJOR-1** |
| `OPENROUTER_MODEL="z-ai/glm-5.3" dsh-openrouter` | runs it | deny | **ALLOW — MAJOR-1** |
| `-m z-ai/glm-5.3` | `unknown option -m`, dies | n/a | ALLOW (not a bypass: the wrapper has no `-m`) |
| `model: 7` / `{"id": …}` / `""` | — | allow | ALLOW (non-string / empty is "no explicit model") |
| tool named `Subagent` / `task` / `agent` | — | — | ALLOW (only the three lowercase dsh tools are matched; matches the plan) |
| `workflow` with `models: [...]` or `config.model` | — | ? | ALLOW — only a flat `model` is inspected (MINOR-2) |

`_MODEL_FLAG = --model(?:=|\s+)([A-Za-z0-9._:/-]+)`: a quote or a backslash is
outside the id charset and `\s+` cannot cross a backslash, so the capture never
starts and the command sails through. The wrapper does not re-check the model
against the table (`dsh-openrouter.sh:94-99` just assigns `model=$2`), so
nothing behind the hook catches it.

## Checks

Clone of the workspace at `task/RT5` (`0574e86`, one commit on `b01bd08`),
`XDG_CACHE_HOME` under the session scratchpad, everything via `nix develop -c`.

| check | result |
| --- | --- |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass — new tests run: 93 "denies a subagent model that is not an OpenRouter row", 97 "fails closed on a missing routing table", 101/102 the two hooks.json tests |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | pass |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | **fails in a fresh clone** — only `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; treefmt/shellcheck/statix/deadnix/ruff all clean. The block is derived from the tree, and RT5 leaves the queue once its own commit exists, so the committed block is inherently one state behind. Pre-existing generator behaviour, not RT5's doing; the `lint` check does not run it. |
| `ruff check` + `ruff format --check` on `hook-guard.py` | pass |
| `shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | pass |
| `pytest tests/lane/test_forbidden_lists_agree.py` | pass. It asserts the three edit/write deny-lists agree (`lane-submit.py` `FORBIDDEN_REPO_PREFIXES`, `hook-guard.py` `PROTECTED_ABSOLUTE`, the wrapper's `forbidden=(…)`). The model rule adds no path prefix, so **no mirror was needed** — correctly left alone. |
| wrapper `--dump-config`, by hand, three runs | matchers exactly `bash`, `edit\|write`, `subagent\|subagent_fork\|workflow`; **all three** commands are `exec '<guard>' --routing-table '<path>'`. Unset env → `$HOME/nixos-agent-env/docs/ledger/routing.toml`; `FACTORY_ROUTING_TABLE=` **empty** → the same default path (`:-` semantics, as the RT4 gate asked); `FACTORY_ROUTING_TABLE=/custom/t.toml` → `/custom/t.toml`. |

Empty-value follow-through: the wrapper never hands the guard an empty path. If
the guard is driven bare with `FACTORY_ROUTING_TABLE=` set empty it uses
`os.environ.get(...)`, which returns `""` rather than the default — it then
denies every explicit model as `routing table unreadable at ` (fail closed, so
no hole, but it does not mirror the wrapper's `:-`; MINOR-3).

## Red before green

Checked out `b01bd08`'s `hook-guard.py` and `dsh-openrouter.sh` under HEAD's
test file and ran `nix develop -c bats tests/unit/70-dsh-openrouter.bats`:

```
not ok 54 hook-guard denies a subagent model that is not an OpenRouter row of the routing table
not ok 57 hook-guard denies a claude row's model (unreachable from this seat)
not ok 58 hook-guard fails closed on a missing routing table: an explicit model is denied as unreadable
not ok 59 hook-guard denies a subagent_fork and a workflow model not in the table
not ok 60 hook-guard denies a bash --model nested-seat launch whose model is not a row
not ok 62 --dump-config … sub-agent matchers passing one routing table
not ok 63 hooks.json's hook commands carry no denial log path -- just the guard and its routing table
```

Seven of the eleven new assertions fail on base; the four that pass are the
allow-side controls (base allows everything, which is the point of the red run).
Independently, every deny payload in the table above was **ALLOWED** by the base
guard. Green: same file, HEAD — 69/69 ok.

## Mutation table

Apply → `bats tests/unit/70-dsh-openrouter.bats` → revert. Each mutation was
asserted to have actually changed the tree before the run.

| # | mutation | result |
| --- | --- | --- |
| M1 | the `_MODEL_TOOLS` branch in `main()` removed | **RED** (4: 54, 57, 58, 59) |
| M2 | `route = "claude"` rows no longer skipped | **RED** (1: 57) |
| M3 | unreadable table → allow (fail open) | **RED** (1: 58) |
| M4 | the `_bash_model_verdict` call removed | **RED** (1: 60) |
| M5 | `--model=` equals form unmatched (`(?:=\|\s+)` → `\s+`) | **SURVIVED** |
| M6 | denial record not written to stderr | **RED** (2: 52, 53) |
| M7 | wrapper drops the `subagent\|subagent_fork\|workflow` matcher | **RED** (2: 62, 63) |
| M8 | guard ignores `--routing-table`, falls back to env/HOME | **RED** (6: 54, 55, 57, 59, 60, 61) |
| M9 | only `subagent` guarded; fork/workflow free | **RED** (1: 59) |
| M10 | `OPENROUTER_MODEL=` regex made to match nothing | **SURVIVED** |

8/10 killed. The two survivors are exactly the untested spellings of the
nested-seat rule (MAJOR-2). M6 is killed only by the pre-existing bash-denial
record tests — the audit record for a *model* denial is proved by my hand run
and the `dsh-denials` read-back above, not by a test.

## Findings

**MAJOR-1 — the nested-seat rule is bypassed by quoting or a line
continuation; nothing behind it catches the model.**
`pkgs/dsh-openrouter/hook-guard.py:100-102`:

```python
_MODEL_FLAG = re.compile(r"--model(?:=|\s+)([A-Za-z0-9._:/-]+)")
_OPENROUTER_MODEL_ENV = re.compile(r"OPENROUTER_MODEL=([A-Za-z0-9._:/-]+)")
```

`dsh-openrouter --model "z-ai/glm-5.3" --headless x`,
`--model 'z-ai/glm-5.3'`, `OPENROUTER_MODEL="z-ai/glm-5.3" dsh-openrouter`, and
`--model \`+newline+`z-ai/glm-5.3` are all allowed by the guard and all run GLM
5.3 when the shell executes them. `dsh-openrouter.sh:94` takes `--model $2`
verbatim, so the hook is the only gate on this path. The continuation case is
one the gate listed as must-deny. Fix: strip `\`+newline before scanning, and
allow an optional matching `'`/`"` around the id in both patterns (then add the
four cases as tests). The plan's "same rule for shell commands" is not met
until the ordinary quoted spelling is refused.

**MAJOR-2 — the nested-seat rule is vacuously tested.** M5 and M10 survive: no
test fails when the `--model=` form stops matching, and none fails when the
`OPENROUTER_MODEL=` pattern stops matching anything at all — the single
`OPENROUTER_MODEL` test asserts *allow*
(`tests/unit/70-dsh-openrouter.bats`, "allows a bash OPENROUTER_MODEL
nested-seat launch whose model is a row"), which a dead rule also satisfies.
House rule: a load-bearing test counts only once it has been shown to fail. Add
a deny test for `OPENROUTER_MODEL=<non-row>`, one for `--model=<non-row>`, and
one for a malformed (not merely missing) table — all three behaviours are
correct today and none is pinned.

**MINOR-1 — `tool_input.provider` is never read.** The plan says
"`tool_input.model` (or `tool_input.provider`+`model`)". `_model_verdict` reads
only `model`, so `provider: z-ai` + an allowed model id passes. Harmless if the
tool has no `provider` parameter — but then say so in the comment rather than
leaving the plan's clause silently unimplemented.

**MINOR-2 — only a flat `model` is inspected.** A `workflow` payload carrying
per-step models (`models: [...]`, `config.model`) is allowed. Whether dsh's
`workflow` tool can carry a per-step model was not established either way; if it
can, the matcher covers the tool but not its payload.

**MINOR-3 — `:-` semantics not mirrored in the guard's bare fallback.**
`os.environ.get("FACTORY_ROUTING_TABLE", default)` returns `""` for an empty
env var, where the wrapper's `${FACTORY_ROUTING_TABLE:-…}` gives the default.
Fails closed (denies every explicit model with `unreadable at `), so it is a
usability wart, not a hole; one `or` would align it with RT4.

**MINOR-4 — stale justification comment.** `pkgs/dsh-openrouter/default.nix:45`
still says hook-guard "imports json/os/re/sys/time"; it now also imports
`tomllib`. That comment is the argument that `python3Minimal` suffices, so it
should name the new import (it does work — the tests run the store-built guard).

**Good, and worth keeping.** The deny message is the plan's wording exactly;
fail-closed covers both `OSError` and `TOMLDecodeError` while a *missing* model
still allows (so an unreadable table cannot brick the seat's default route);
claude rows are excluded at parse time rather than by a second lookup; the
wrapper resolves the path once and hands the same one to all three matchers
(M8's six kills show the tests actually pin that); and the nested `bash -c '…'`
case is caught by the string scan.

## Deviations

- `docs/OPERATIONS.md` (one generated line) is in the commit beyond the plan's
  `touches`. Allowed and disclosed in FACTORY-NOTES; it is the lint gate's
  regenerated queue block.
- `git show --stat HEAD` = the four planned files plus that one — no extras.
  Subject byte-identical to the plan; `Co-Authored-By: Claude Fable 5.1` trailer
  present (plus a `Generated-By: dsh …` line, the seat's convention).
- Stdlib only (`json`, `os`, `re`, `sys`, `time`, `tomllib`); no new package
  inputs; `docs/runbooks/lanes.md` states the new rule and the table path.
  `githooks/pre-commit`, `flake.nix`, `pkgs/evidence/*` untouched, as required.
- Gate procedure ran outside the workspace throughout: a throwaway clone under
  the session scratchpad, no writes to `/home/dalhaka/factory/ws/rt5/RT5`, no
  `sudo`, nothing on the live host.
