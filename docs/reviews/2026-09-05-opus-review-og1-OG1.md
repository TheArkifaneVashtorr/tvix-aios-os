# Opus gate — seat run og1, task OG1 — REJECTED

## Summary

One commit (`e0f18751`) on base `2492b28`, subject byte-identical to the plan's,
`Co-Authored-By` trailer present. Touches are a subset of OG1's declared set with
the two sanctioned substitutions: `tools/orchestrator-guard.sh` in place of the
`.py` the plan named (bash chosen, measured, and justified in the commit body),
and `docs/MAP.md` regenerated. `.claude/settings.json` keeps G6's SessionStart
entry byte-for-byte and adds exactly the two PreToolUse matchers; the `flake.nix`
change is exactly one `cp` line plus its two comment lines. `unit` (19 new
`91-orchestrator-guard` tests), `lint`, the pre-commit gate and `shellcheck` all
pass; red-before-green and six mutations are all real. Wall time 11–37 ms/call,
far inside the 300 ms budget. The deny JSON is byte-identical in shape to the dsh
guard's `_deny`.

It is rejected on **three MAJOR bypasses**, all of which the task brief named in
advance and none of which the bats file exercises: a plan-heading edit escapes
the guard entirely if the path carries a `..` or `./` segment or is a symlink
into the plans directory, and `git -c … commit --amend` (and `git -C … push`)
escapes the history rules. The operator asked for a ban; these are the two things
the ban is *for*. The reference implementation the plan pointed at
(`pkgs/dsh-openrouter/hook-guard.py`) already does the normalisation this one
skips (`_resolve` = `expanduser` + `normpath`, then `realpath` in
`_edit_verdict`), so the fix is a port, not an invention.

## Guard behaviour (the payload table)

Payloads fed on stdin exactly as Claude Code sends them (compact JSON,
`ensure_ascii=False`), guard run as `env CLAUDE_PROJECT_DIR=<fake project> bash
tools/orchestrator-guard.sh`. Fake project has
`docs/superpowers/plans/x.md` with two typed headings (`A1`, `B2`).

| # | Payload | Expected | Observed | Verdict |
|---|---------|----------|----------|---------|
| a | `Edit` rewriting `### A1 (code, S) — first task` in a plan | deny | **DENY**, reason names `docs/ledger/task-status.toml` | pass |
| b | `Edit` deleting that heading line | deny | **DENY** | pass |
| c | `Write` of the whole file with `A1` dropped | deny | **DENY** | pass |
| d | `MultiEdit`, one offending edit between two benign ones | deny | **DENY** | pass |
| e | `Edit` appending a new `### C3 (code, S) — …` section | allow | allow | pass |
| f | `Edit` of body text under a heading | allow | allow | pass |
| g | `Edit` rewriting the same heading in `docs/other.md` (non-plan) | allow | allow | pass |
| h1 | Bash `sudo nixos-rebuild switch` | deny | **DENY** `sudo is refused (an operator action)` | pass |
| h2 | Bash `systemctl --user restart helm-serve` | deny | **DENY** `systemctl restart is refused …` | pass |
| h3 | Bash `systemctl status x` | allow | allow | pass |
| h4 | Bash `git commit --amend` / `git push` / `git rebase -i main` / `git reset --hard` | deny | **DENY**, all four, `history rules of the house` | pass |
| h5 | Bash `git status`, `git log --oneline -5` | allow | allow | pass |
| h6 | Bash `echo x \| tee /var/lib/secrets/y` | deny | **DENY** | pass |
| h7 | Bash `echo x > /run/baskets/y` | deny | **DENY** | pass |
| i | malformed input `this is not json` | allow + stderr warn | allow, `orchestrator-guard: malformed hook input (allowing)` | pass |
| j | deny JSON shape | matches `hook-guard.py` `_deny` | `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}` — identical key order and nesting | pass |
| k | wall time, 10 calls each | < 300 ms | `git status` 11 ms; heading `Edit` 25 ms; `MultiEdit` 37 ms | pass |

Injection probes (decoy `"file_path"` / `"tool_name"` / `"command"` keys embedded
inside `new_string` and inside a Bash command) all still deny — the `sed`
extraction is not steerable by payload content in the orders Claude Code emits.
A pretty-printed (multi-line) payload also still denies.

## Bypass attempts

| Attempt | Payload | Result | Severity |
|---|---|---|---|
| `..` segment | `Write`/`Edit` on `<proj>/docs/superpowers/plans/../plans/x.md`, heading dropped | **ALLOWED** | **MAJOR** |
| `./` segment | `Edit` on `<proj>/docs/superpowers/./plans/x.md`, heading rewritten | **ALLOWED** | **MAJOR** (same root cause) |
| symlink | `Write` on `<proj>/link/x.md` → symlink to the plan, heading dropped | **ALLOWED** | **MAJOR** |
| doubled slash | `<proj>/docs/superpowers/plans//x.md` | denied (bash `dirname` collapses it) | ok |
| relative path | `docs/superpowers/plans/x.md` | **ALLOWED** | minor (Claude Code sends absolute paths, but `hook-guard.py` still joins on `CLAUDE_PROJECT_DIR`) |
| split heading edit, step 1 | `Edit` `### A1 (code, S) — first task` → `### A1 — first task` (drops only the type) | **DENIED** — the heading no longer matches `HEADING_ERE`, so it counts as removed | correct, as hoped |
| `--amend` behind `-c` | `git -c core.editor=true commit --amend` | **ALLOWED** | **MAJOR** |
| `push` behind `-C` | `git -C /home/x push` | **ALLOWED** | **MAJOR** (same root cause) |
| `--amend` behind `\` continuation | `git commit \`⏎`  --amend` | denied | ok |
| `--amend` after `;` | `cd /tmp; git commit --amend` | denied | ok |
| `--amend --no-edit` | denied | ok |
| `sudo` after `;` / `&&` / `env` | `echo hi; sudo reboot`, `true && sudo reboot`, `env sudo reboot` | denied | ok |
| `systemctl` with intervening flags | `systemctl --user --no-block restart helm-serve` | denied | ok |
| `rebase --onto`, `push --force` | denied | ok |
| protected write via `tee -a` | `echo x \| tee -a /var/lib/secrets/y` | **ALLOWED** | minor |
| protected write via `cp` | `cp /tmp/x /var/lib/secrets/y` | **ALLOWED** | minor (out of the plan's stated scope: it says "writes under", the guard implements "redirects and bare `tee` under") |
| protected write with two spaces | `echo x >  /var/lib/secrets/y` | **ALLOWED** | minor |
| malformed JSON that starts with `{` | `{"tool_name":"Bash", broken` | allowed, **no stderr warning** | minor (the plan asks for a warning on malformed input; only non-`{` input warns) |

Root cause of the two MAJOR families:

- `is_plan_file()` compares `dirname -- "$p"` against `"$CLAUDE_PROJECT_DIR/docs/superpowers/plans"` as **raw text**. No `normpath`, no `realpath`. Any path that is not already in canonical form — `..`, `./`, `~`, a symlink, a relative path — misses the comparison and the whole heading rule is skipped. `hook-guard.py` solves exactly this in `_resolve`/`_is_within`/`os.path.realpath`; the port dropped it.
- `bash_verdict()`'s git patterns require the literal adjacency `git<space>commit` / `git<space>push` / `git<space>rebase`. Git's global options sit between (`git -c …`, `git -C …`, `git --no-pager …`), so the pattern misses. `git -c core.editor=true commit --amend` is a working amend.

## Checks

| Check | Command | Result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link` | pass — tests 155–173 are the 19 `91-orchestrator-guard` tests, all `ok` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | pass (`All checks passed!`, 86 formatted, 0 changed) |
| pre-commit | `nix develop -c githooks/pre-commit` | pass, exit 0, no regenerate step needed |
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | clean |
| `docs/MAP.md` forced? | reverted `MAP.md` to base, re-ran the gate | `repomap: docs/MAP.md is stale — run: python3 pkgs/evidence/repomap.py write` → the regeneration is forced, not gratuitous |

Commit subject md5 equals the plan's `**commit subject:**` md5 (`1d37b988…`) —
byte-identical. Trailer `Co-Authored-By: Claude Fable 5.1 …` present, preceded by
the `Generated-By: dsh …` line.

## Red before green

- Base `2492b28` has no `tools/orchestrator-guard.sh` (`git show 2492b28:tools/orchestrator-guard.sh` → `exists on disk, but not in '2492b28'`), so every payload in the table is allowed there by construction.
- Substituting an allow-everything stub (`#!/usr/bin/env bash` / `exit 0`) for the guard at HEAD: **9 of 19 tests fail** — tests 1–5, 7, 8, 11, 13, 17. The ten that stay green are the allow-side tests plus the timing test, which is what an allow-only stub should leave standing. Restoring the guard: 19/19 green.

## Mutation table

Each mutation applied to `tools/orchestrator-guard.sh`, `nix develop -c bats
tests/unit/91-orchestrator-guard.bats` run, then reverted.

| # | Mutation | Failures | Killed by |
|---|---|---|---|
| 1 | `missing_headings()` short-circuited to report nothing | 4 | edit-remove, edit-rewrite, write-drop, multiedit-remove |
| 2 | `git … --amend` pattern deleted | 1 | `bash: git history rewrites are denied` |
| 3 | `sudo` pattern deleted | 1 | `bash: sudo is denied` |
| 4 | deny JSON `permissionDecision` changed to `"block"` | 9 | every deny test (the `denied()` helper asserts the shape) |
| 5 | over-reach: `is_plan_file` reduced to "any `*.md`" | 1 | `an edit outside the plans directory is allowed` — the over-reach guard (test g) is load-bearing |
| 6 | malformed input `exit 3` instead of warn-and-allow | 1 | `malformed JSON is allowed and warns on stderr` |

All six killed. No survivors, no no-op mutations.

## Findings

**MAJOR 1 — the heading rule is bypassed by any non-canonical path.**
`tools/orchestrator-guard.sh`, `is_plan_file()`. A `Write`/`Edit` whose
`file_path` contains a `..` or `./` segment, or is a symlink pointing into
`docs/superpowers/plans/`, is not recognised as a plan file and the append-only
rule never runs — the heading is deleted. Verified on all three shapes.
Fix: canonicalise before comparing — resolve `~`, join a relative path onto
`CLAUDE_PROJECT_DIR`, `normpath`, then compare the `realpath` of the target
against the `realpath` of the plans directory (bash: `readlink -f` / `realpath
-m`, with a fallback that still normalises when the file does not yet exist).
Add tests for all three shapes.

**MAJOR 2 — `git -c … commit --amend` and `git -C … push` are allowed.**
`bash_verdict()`. The patterns demand `git` immediately followed by the
subcommand. Git's global options are legal and common in this repo's own
commands. Fix: allow an intervening run of global options in the pattern
(`git(\s+(-c\s+\S+|-C\s+\S+|--no-pager|--git-dir=\S+|--work-tree=\S+|-p|--paginate))*\s+commit`
and the same for `push`/`rebase`/`reset`), or better, tokenise and find the
first non-option word after `git`. Add a bats case per global-option spelling.

**MINOR 3 — `sudo` fires on any occurrence, including `grep sudo docs/brief.md`
and `echo 'never sudo here'`.** The commit body says the host rules "reuse
`hook-guard.py`'s wording"; they also *changed its semantics*. The reference
`_SUDO = (?:^|[;&|\n()])\s*sudo(?=\s|$)` deliberately excludes a bare preceding
space, with the comment "keeps `echo sudo` from firing". OG1's ERE adds
`[[:space:]]` to that leading class, so a plain space qualifies. Confirmed:
`grep -rn sudo docs/brief.md` → DENY. This repo's own `CLAUDE.md` and runbooks
are full of the word; the orchestrator can no longer grep for it. Same for
`nixos-rebuild`. Drop `[[:space:]]` from the two leading character classes to
match the reference exactly.

**MINOR 4 — the protected-prefix rule covers only redirects and a bare `tee`.**
`tee -a /var/lib/secrets/x`, `cp … /var/lib/secrets/x`, and `>  ` with two spaces
all pass. The plan says "writes under"; the implementation is a narrow glob list.
Not a regression against the dsh guard (which does not check bash writes at all,
only edit/write paths), but the runbook and commit body both promise more than is
delivered. Either widen it or narrow the prose.

**MINOR 5 — malformed JSON that begins with `{` is allowed silently.** The plan
asks for a stderr warning on any internal error. Only input that does not start
with `{` warns; `{"tool_name":"Bash", broken` falls through to an empty
`tool_name` and returns 0 with no output at all. Cheap fix: warn when
`tool_name` extraction yields empty on a `{`-shaped payload.

**MINOR 6 — `MultiEdit` old/new extraction cannot survive an escaped quote.**
`multiedit_after()` greps `"old_string"\s*:\s*"[^"]*"`, so an edit whose
`old_string` contains `\"` is truncated at the escape. The single-edit `Edit`
path uses the careful `json_string()` and does not have this. In practice the
truncation makes the edit *not* apply, so the "after" text keeps the heading and
the call is allowed — i.e. it fails open. My probe (`say "hi"` as the first of
two edits, heading removal as the second) still denied, because the second edit's
capture was clean; a payload where the *offending* edit carries the quote would
not be. Worth a fix and a test.

**NOTE — `docs/MAP.md` regeneration is not disclosed.** It is genuinely forced by
`repomap check` (proved above), so it is acceptable under the brief, but neither
the commit body nor `FACTORY-NOTES` mentions it. Say so next time.

**`docs/ledger/task-status.toml` — 16 lines, comment-only, valid TOML.** Parses
to `{}` under `tomllib`, and the documented row shape (`[[task]]` with `repo`,
`plan`, `key`, `status`, `note`, `decided`) matches G11's `load_task_status`
exactly (`pkgs/evidence/tasks.py:140`, which keys on `(repo, plan, key)` and
reads `status`, `note`, `decided`).

**Merge with G11.** `/home/dalhaka/factory/ws/sc5/G11/docs/ledger/task-status.toml`
also creates this file, header-only, as a **single line** with no trailing
newline:

```
# [[task]] repo, plan, key, status = withdrawn | parked, note, decided
```

OG1's is the 16-line version quoted in the runbook diff (a prose paragraph, then
the same field list as a commented `[[task]]` block). Both are pure comments and
both parse to `{}`, so the merge is a straight "keep OG1's file" — it is a strict
superset in content and the only one that explains *why* the file exists. No
semantic conflict; resolve by taking OG1's side wholesale.

## Deviations

Accepted:

- `tools/orchestrator-guard.sh` (bash) instead of the plan's
  `tools/orchestrator-guard.py`. The plan explicitly permits this "if the
  devShell startup is too slow — measure and state which". Measured and stated in
  the commit body (~5 s for `nix develop -c python3`, ~12 ms for bash); I
  re-measured 11–37 ms/call. Correct call.
- `docs/MAP.md` outside the declared `touches`, forced by the lint gate
  (`repomap check`). Proved forced. Undisclosed in prose — see the note above.
- `flake.nix` touched: exactly the one sanctioned `cp` line for the guard into
  the `unit` sandbox, mirroring G6's line for `session-start.sh`. Nothing else.

Not accepted:

- The plan's interface spec says the heading rule applies to
  "`Edit/Write/MultiEdit` on `docs/superpowers/plans/*.md`". A path-text
  comparison does not implement that predicate; the plan also pointed the
  implementer at `hook-guard.py`, which contains the resolution code. MAJOR 1.
- The plan's Bash rule says "`git commit --amend`, `git push`, `git rebase`,
  `git reset --hard` on this checkout → deny". `git -c … commit --amend` is
  `git commit --amend` on this checkout. MAJOR 2.

Verdict: **REJECTED**. Fix round OG1b: the two MAJORs with a bats case per
bypass shape (`..`, `./`, symlink, relative; `-c`, `-C`, `--no-pager` before
`commit`/`push`/`rebase`/`reset`), plus MINOR 3 (restore the reference's `sudo`
semantics) which the operator will hit within a day. MINOR 4–6 may ride along or
defer; MINOR 5 is two lines.
