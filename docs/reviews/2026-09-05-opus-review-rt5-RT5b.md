---
reviewer: opus
majors: 2
minors: 5
mutants_total: 15
mutants_killed: 13
---
# Opus gate — seat run rt5, task RT5b — REJECTED

## Summary

RT5b does what the fix round was asked to do. Every spelling MAJOR-1 named is
now refused — quoted (`"`/`'`), equals, `env`-prefixed, tab-separated,
`\`-newline continuation, `bash -c '…'` nesting — and MAJOR-2's two vacuous
spots are gone: the former survivors M5 (`--model=`) and M10 (dead
`OPENROUTER_MODEL=`) both die, as do three new mutations (quote group,
continuation strip, nested walk). The wrapper is byte-identical to RT5's
already-gated version; `default.nix` names `tomllib`; `lanes.md` states the
rule; one commit on `5be9e4e`, five files, all inside RT5b's `touches`,
subject byte-identical. `unit`, `host-core`, `lint`, ruff, shellcheck and
`tests/lane/test_forbidden_lists_agree.py` are green in a fresh clone on
NixOS 26.05 (python 3.14, the store guard runs under `python3-minimal-3.14.7`).

It is rejected on a **new** hole the fix round itself introduced.

- **MAJOR-1 — the recursive model walk crashes the guard, and a crashed guard
  ALLOWS.** `_walk_model_ids` recurses; at a `tool_input` nesting depth of 995
  or more it raises `RecursionError`, the process exits 1 with an empty stdout,
  and the pinned harness treats that as a non-blocking error and runs the tool
  (`@deepseek-ai/dsh-hook-protocol`: "exit 2 blocks … every other exit is a
  non-blocking error"; `dsh-hooks-claude-code` blocks only on
  `merged.decision === "deny" | "ask"`). A `subagent` payload carrying
  `"model": "z-ai/glm-5.3"` **at the top level** plus deep nesting under any
  other key is therefore allowed — the identical payload is DENIED by RT5's
  flat-read guard, so this is a regression inside the fix round, and it fails
  the gate's own requirement that a nested model deny "at any depth". The same
  crash-to-allow shape reaches the fail-closed table rule: a routing table that
  is not valid UTF-8 raises `UnicodeDecodeError`, which
  `except (OSError, tomllib.TOMLDecodeError)` does not catch, so an explicit
  model is ALLOWED where the interface says an unparsable table must DENY. Root
  cause is one thing: nothing contains the guard's exceptions, and the plan's
  Step 3 says "never raise".

Everything else is minors. The fix is small but it is a design point, so under
rule A1 it goes back to the plan as RT5c — named in Findings.

## Rule behaviour

Driven by hand, `python3 pkgs/dsh-openrouter/hook-guard.py --routing-table <path>`
with `{"hook_event_name":"PreToolUse","tool_name":…,"tool_input":…}` on stdin;
table = the committed `docs/ledger/routing.toml` unless stated. 43 payloads,
**0 mismatches** against the gate's required matrix.

| payload | want | got |
| --- | --- | --- |
| `--model "z-ai/glm-5.3"` | deny | **DENY** |
| `--model 'z-ai/glm-5.3'` | deny | **DENY** |
| `--model=z-ai/glm-5.3` | deny | **DENY** |
| `--model="z-ai/glm-5.3"` / `--model='z-ai/glm-5.3'` | deny | **DENY** |
| `OPENROUTER_MODEL="z-ai/glm-5.3" dsh-openrouter` | deny | **DENY** |
| `OPENROUTER_MODEL='z-ai/glm-5.3' dsh-openrouter` | deny | **DENY** |
| `env OPENROUTER_MODEL=z-ai/glm-5.3 dsh-openrouter` | deny | **DENY** |
| `export OPENROUTER_MODEL=z-ai/glm-5.3; dsh-openrouter` | deny | **DENY** |
| ``--model \`` + newline + `z-ai/glm-5.3` | deny | **DENY** |
| `--model` + TAB + `z-ai/glm-5.3` | deny | **DENY** |
| `--model  z-ai/glm-5.3` (two spaces) | deny | **DENY** |
| `bash -c 'dsh-openrouter --model z-ai/glm-5.3 …'` | deny | **DENY** |
| `--model=Z-AI/GLM-5.3` (case variant, not a row) | deny | **DENY** |
| `--model z-ai/glm-5.3:free` (not a row) | deny | **DENY** |
| `--model deepseek/deepseek-v4-flash` | allow | ALLOW |
| `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 …` | allow | ALLOW |
| a command naming no model / `git status` | allow | ALLOW |
| `--model-name x`, `--model-name z-ai/glm-5.3` | must not match | ALLOW |
| `subagent` `model: z-ai/glm-5.3` | deny | **DENY** `sub-agent model z-ai/glm-5.3 is not a row of <table> (route openrouter); pick a role and let the table choose` |
| `subagent` `provider: anthropic` + `model: opus` (claude row) | deny | **DENY** |
| `subagent` `model: Z-AI/GLM-5.3` / `…:free` | deny | **DENY** |
| `subagent_fork` `model: moonshotai/kimi-k3` | deny | **DENY** |
| `workflow` `steps[0].model` non-row | deny | **DENY** |
| `workflow` `config.model` non-row | deny | **DENY** |
| `workflow` non-row nested 4 deep under arbitrary keys | deny | **DENY** |
| `workflow` `steps[*].model` all rows | allow | ALLOW |
| `subagent` row model / no model | allow | ALLOW |
| missing table + explicit model | deny | **DENY** `routing table unreadable at /nonexistent/rt5b.toml` |
| missing table + no model | allow | ALLOW |
| malformed TOML + explicit model (structured and bash) | deny | **DENY** `routing table unreadable at …` |
| malformed TOML + no model | allow | ALLOW |
| table = a directory | deny | **DENY** unreadable |
| table = `/dev/null` (parses, zero rows) + explicit model | deny | **DENY** not-a-row |
| `FACTORY_ROUTING_TABLE=` empty, no flag, row model | allow (default path) | ALLOW |
| `FACTORY_ROUTING_TABLE=` empty, no flag, non-row model | deny | **DENY**, naming `$HOME/nixos-agent-env/docs/ledger/routing.toml` |
| **`subagent` `model: z-ai/glm-5.3` + 995-deep nesting** | **deny** | **ALLOW — MAJOR-1** (exit 1, `RecursionError`, empty stdout) |
| **explicit model + non-UTF-8 table** | **deny (unparsable)** | **ALLOW — MAJOR-1** (exit 1, `UnicodeDecodeError`) |

Message wording is the plan's, byte for byte. Every denial emitted the JSON
record on stderr (`{ts,event,tool,reason,subject}`, valid JSON, 241 chars for a
workflow denial with my clone path) — the audit path `dsh-openrouter --denials`
reads is unchanged from RT5, where it was verified end to end.

Depth was bisected: the first crashing depth is **995**; depth 900 still denies
correctly. `json.loads` itself parses depth 3000 fine, and the traceback frames
are `main → _model_verdict → _walk_model_ids` only — the crash is the new walk,
not the JSON parser. RT5's guard (`task/RT5`), which read a flat `model`, denies
the same depth-3000 payload with exit 0.

## Bypass attempts

| attempt | shell would run | want | got |
| --- | --- | --- | --- |
| `--model $(echo z-ai/glm-5.3)` | that model | deny | ALLOW — known limit, undocumented at the claim site (MINOR-4) |
| `X=z-ai/glm-5.3; --model $X` | that model | deny | ALLOW — same |
| `X=…; OPENROUTER_MODEL=$X dsh-openrouter` | that model | deny | ALLOW — same |
| `--model $'z-ai/glm-5.3'` (ANSI-C quoting) | that model | deny | ALLOW — same |
| `--mod''el z-ai/glm-5.3` (quote splice in the flag) | that model | deny | ALLOW — same |
| `dsh-openrouter --model=Z-AI/GLM-5.3` | that id | deny | **DENY** |
| `--model "z-ai"/glm-5.3`, `--model z-ai/'glm-5.3'` | that model | deny | **DENY** (on a partial capture; see MINOR-5) |
| `--model z\-ai/glm-5.3`, `z-ai\/glm-5.3` | that model | deny | **DENY** (partial capture) |
| `--model "z-ai/glm-5.3"''` | that model | deny | **DENY** |
| `eval "$(printf 'OPENROUTER_MODEL=…')" dsh-openrouter` | that model | deny | **DENY** (string scan) |
| `cat <<EOF … --model z-ai/glm-5.3 … EOF` | nothing | n/a | DENY (over-broad, harmless) |
| `-m z-ai/glm-5.3` | nothing — the wrapper has no `-m`, unknown option exits 2 | n/a | ALLOW (not a bypass) |
| **995-deep `tool_input` + top-level non-row `model`** | — | **deny** | **ALLOW — MAJOR-1** |

The substitution family (`$(…)`, `$X`, `$'…'`, `--mod''el`) is unfixable by a
regex over the command string and is the same class the module docstring already
disclaims ("A deny-list over shell command strings is a heuristic and an audit
trail, NOT a boundary"). I record it as a known limit, not a finding — except
that `docs/runbooks/lanes.md` now advertises the rule without that caveat
(MINOR-4).

MAJOR-1 is a different class: the structured `subagent`/`workflow` half is the
half the plan treats as the real gate ("the table is applied by the OS, not
followed by prose"), it carries no such disclaimer, and the payload is the
model's own arguments object (`preToolPayload` sets `tool_input: exec.arguments`
at the `tools/pre-execute` seam, before the tool runs). I did not establish
whether dsh's own tool schema would reject a 995-deep argument object before the
hook fires; the hook is the boundary and must not depend on a check it does not
perform.

## Checks

Throwaway clone of `/home/dalhaka/factory/ws/rt5/RT5b` at `task/RT5b`
(`c361cc3`, one commit on `5be9e4e`, which is an ancestor of live main
`b5a23da`); `XDG_CACHE_HOME` under the session scratchpad; everything through
`nix develop -c`.

| check | result |
| --- | --- |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass (172 unit assertions) |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | pass |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 76/76 ok. New, named: 62 "denies every quoted/continued spelling of a bash --model that is not a row", 63 "denies every spelling of a bash OPENROUTER_MODEL that is not a row", 64 the allow controls, 65 provider-present claude row, 66 "walks nested model keys: a workflow steps[*].model", 67 malformed table, 68 empty `FACTORY_ROUTING_TABLE` → default path |
| `nix develop -c githooks/pre-commit` | fails on one line only — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the diff is exactly `RT5b` leaving the derived queue list. treefmt/ruff/shellcheck/statix/deadnix all clean. Pre-existing generator behaviour (identical at RT5's gate); the `lint` check does not run it |
| `ruff check` + `ruff format --check` on `hook-guard.py` | pass |
| `shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | pass |
| `pytest tests/lane/test_forbidden_lists_agree.py -q` | 1 passed — the model rule adds no path prefix, so no mirror was needed |
| wrapper wiring | `pkgs/dsh-openrouter/dsh-openrouter.sh` is **byte-identical** to `task/RT5`, whose `--dump-config` behaviour (three matchers, all `exec '<guard>' --routing-table '<path>'`, `:-` default, empty env → default, custom path honoured) was verified at the previous gate and is re-pinned here by tests 69/70 |

Stdlib only: `json`, `os`, `re`, `sys`, `time`, `tomllib`; no new inputs.
`pkgs/dsh-openrouter/default.nix:45` now names `tomllib`.
`docs/runbooks/lanes.md` lists the rule and the table path.
`githooks/pre-commit`, `flake.nix`, `pkgs/evidence/*` untouched.

## Mutation table

Apply → `nix develop -c bats tests/unit/70-dsh-openrouter.bats` → revert; each
mutation was asserted to have changed the tree before the run (an unapplied
mutation aborts).

| # | mutation | result |
| --- | --- | --- |
| M1 | the `_MODEL_TOOLS` branch in `main()` removed | **RED** (7: 54, 57, 58, 59, 65, 66, 67) |
| M2 | `route = "claude"` rows no longer skipped | **RED** (2: 57, 65) |
| M3 | unreadable table → allow (fail open) | **RED** (2: 58, 67) |
| M4 | the `_bash_model_verdict` call removed | **RED** (3: 60, 62, 63) |
| M5 | `--model=` equals form unmatched (`(=\|\s+)` → `(\s+)`) | **RED** (1: 62) — *was a survivor at RT5* |
| M6 | denial record not written to stderr | **RED** (2: 52, 53) |
| M7 | wrapper's `subagent\|subagent_fork\|workflow` matcher renamed away | **RED** (1: 69) |
| M8 | guard ignores `--routing-table`, falls back to env/HOME | **RED** (11: 54, 55, 57, 59–66) |
| M9 | only `subagent` guarded; fork/workflow free | **RED** (2: 59, 66) |
| M10 | `OPENROUTER_MODEL=` regex made to match nothing | **RED** (1: 63) — *was a survivor at RT5* |
| N1 | quote group made empty-only (`(['"]?)` → `(['"]{0})`) | **RED** (2: 62, 63) |
| N2 | `\`+newline continuation strip removed | **RED** (1: 62) |
| N3 | nested walk reduced to a flat top-level `model` read | **RED** (1: 66) |
| N4 | `(?:env\s+)?` prefix removed from `_OPENROUTER_MODEL_ENV` | **SURVIVED — equivalent mutant** |
| N5 | `.replace("\t", " ")` removed | **SURVIVED — equivalent mutant** |

13/15 killed; both survivors are provably behaviour-preserving, not coverage
holes. `(?:env\s+)?` is an optional unanchored prefix on a pattern that already
matches `OPENROUTER_MODEL=` anywhere in the string, and `\s` in
`--model(=|\s+)` already matches a tab — so the two spellings stay denied with
the mutation applied, which is exactly why tests 62 and 63 (which do exercise
`env OPENROUTER_MODEL=…` and the tab separator) still pass. Both spellings are
therefore pinned; the two code fragments are simply dead. RT5's eight kills all
still hold, and its two survivors are dead.

## Findings

**MAJOR-1 — an unhandled exception makes the guard exit non-zero, and the
harness reads that as "allow"; the new recursive walk is the way to trigger it.**

`pkgs/dsh-openrouter/hook-guard.py:203-219`:

```python
def _walk_model_ids(node):
    if isinstance(node, dict):
        for key, value in node.items():
            ...
            yield from _walk_model_ids(value)
```

`main()` has no exception containment, and `main()`'s only guard is
`except ValueError` around `json.load`. Two demonstrated fail-opens:

1. **Depth.** A `subagent` payload whose `tool_input` is
   `{"model": "z-ai/glm-5.3", "deep": {"a": {"a": … 995 levels … }}}` makes the
   walk raise `RecursionError`; the process exits 1 having written nothing to
   stdout. Bisected first crashing depth: 995 (900 denies correctly).
   `json.loads` parses depth 3000 without complaint, and the traceback contains
   only `main`, `_model_verdict`, `_walk_model_ids` — the parser is not the
   problem. RT5's guard denies the identical payload (exit 0, deny). The gate's
   required matrix says a nested model must be denied *at any depth*.
2. **Encoding.** `_load_openrouter_models` catches
   `(OSError, tomllib.TOMLDecodeError)`. A routing table that is not valid UTF-8
   raises `UnicodeDecodeError` — a `ValueError`, but not a `TOMLDecodeError` —
   so the guard exits 1 and an explicit model is allowed, where the plan's
   interface says a table that is "missing or unparsable" must DENY. (Carried
   from RT5, and not model-reachable under workspace-write, but it is the same
   defect and the same specified rule.)

That a non-zero exit means allow is not inference. The pinned harness
(`dsh-0.1.2-rc.1`) says so twice:
`@deepseek-ai/dsh-hook-protocol/lib/index.js` — "exit 2 blocks with stderr as
the reason; every other exit is a non-blocking error" — and
`@deepseek-ai/dsh-hooks-claude-code/lib/index.js`, whose `tools/pre-execute`
handler blocks only when `merged.decision === "deny"` (or `"ask"`) and otherwise
falls through to `next()`.

**Design change for the re-plan (rule A1 → RT5c).** Not a regex tweak; the guard
needs an error contract it currently lacks:

- Make the model walk **iterative** (an explicit stack/deque) with a bounded
  node and depth budget; exceeding the budget is a **deny**, not a continue and
  not a crash.
- Give `main()` a **per-rule try/except**: for the model rule any unexpected
  exception resolves to deny (`sub-agent model gate failed: <class>` — fail
  closed, same as an unreadable table); for the pre-existing bash/edit rules
  keep today's allow-on-error, which the docstring already promises. `main()`
  must return 0 on every path, so the guard never exits non-zero at all.
- Broaden the table except to `Exception` (or add `UnicodeDecodeError`) so an
  undecodable table is "unreadable", not a crash.
- Tests, each red first: a depth-2000 payload with a non-row `model` → deny; a
  non-UTF-8 table + explicit model → deny; and both asserting **exit status 0**
  (today's tests never assert the status on these paths, which is why a crash
  is invisible to the suite).

**MINOR-1 — the audit record names the wrong model.** `_deny(..., next(_walk_model_ids(tool_input), ""))` takes the *first* id
found, not the offending one. A `workflow` with
`steps: [{model: deepseek/deepseek-v4-flash}, {model: z-ai/glm-5.3}]` denies with
`reason` naming `z-ai/glm-5.3` and `subject` naming `deepseek/deepseek-v4-flash`
(verified). `dsh-openrouter --denials` shows the subject, so the audit points at
an allowed model. Have `_model_verdict` return the offending id alongside the
reason.

**MINOR-2 — `--routing-table ''` is not the default path.** The plan says a
table path of `""` reaching the guard should resolve to the default. That was
implemented for the env var (`os.environ.get(...) or …`, tested at 68) but not
for an explicit empty flag value, which denies every explicit model as
`routing table unreadable at ` (empty). Fail-closed and unreachable through the
wrapper (`${FACTORY_ROUTING_TABLE:-…}` is never empty), so a wart, not a hole.

**MINOR-3 — two dead code fragments that look like coverage.** `(?:env\s+)?` and
`.replace("\t", " ")` are no-ops (N4/N5 above). Either drop them or say in the
comment that they are belt-and-braces, so the next reader does not take them for
the reason those two spellings are caught.

**MINOR-4 — the known limits are not stated where the rule is now claimed.**
`docs/runbooks/lanes.md` states the nested-seat rule without the docstring's
"heuristic, NOT a boundary" caveat, while `--model $(echo …)`, `--model $X`,
`OPENROUTER_MODEL=$X`, `--model $'…'` and `--mod''el …` all pass. One clause in
the runbook naming shell substitution as out of reach would keep the operator
honest about what the line buys.

**MINOR-5 — partial captures produce garbled denial reasons.** `--model z-ai/'glm-5.3'`
denies naming `z-ai/`; `--model z\-ai/glm-5.3` denies naming `z`. Fail-closed
and arguably a feature, but the operator reading the audit sees an id that was
never requested.

**Good, and worth keeping.** Every ordinary spelling MAJOR-1 named is now
refused, by a pattern that is still tight enough that `--model-name` does not
match; the quote is a backreference, so `--model "id'` cannot half-match into a
different id; the nested walk catches `steps[*].model`, `config.model` and
arbitrary depth up to the crash point; the normalisation is one pass over the
string rather than a shell parser; the deny wording, the fail-closed table rule,
the claude-row exclusion, the audit record and the wrapper's single resolved
table are all unchanged from the half RT5 already got right; and the three new
mutations (N1–N3) each die on exactly the test that was written for them, which
is what MAJOR-2 asked for.

## Deviations

- One commit, `c361cc3`, on `5be9e4e`; five files — `pkgs/dsh-openrouter/hook-guard.py`,
  `pkgs/dsh-openrouter/dsh-openrouter.sh`, `pkgs/dsh-openrouter/default.nix`,
  `tests/unit/70-dsh-openrouter.bats`, `docs/runbooks/lanes.md` — exactly RT5b's
  `touches`, nothing more (no `docs/OPERATIONS.md` this time). Subject
  byte-identical to RT5's; `Co-Authored-By: Claude Fable 5.1` present, with the
  seat's `Generated-By: dsh …` line above it.
- Against `task/RT5`, only `hook-guard.py` (+66/−…), the bats file (+75) and the
  `default.nix` comment changed — the wrapper and `lanes.md` are carried
  unmodified, as the plan asked.
- `nix develop -c githooks/pre-commit` exits 1 in a fresh clone on the
  regenerated `docs/OPERATIONS.md` queue block alone. Pre-existing generator
  behaviour, disclosed in FACTORY-NOTES, and not part of the `lint` acceptance
  check. I reverted the regeneration in my clone; the workspace was never
  touched.
- Gate procedure ran entirely in a throwaway clone under the session scratchpad
  with `XDG_CACHE_HOME` there; no writes to `/home/dalhaka/factory/ws/rt5/RT5b`,
  no `sudo`, nothing on the live host.
