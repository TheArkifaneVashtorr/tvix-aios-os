# Opus gate — seat run mcp, task P1pro — APPROVED

## Summary

P1pro is a correct, exactly-scoped XS change. One commit
(`63cfb99233569c9d9a746dcd7accad4ecaf70dc2`) touching one file,
`tools/factory/seat/launch-today.sh`, +7/-5. The `here=` line uses the byte-identical
idiom already in all six sibling seat scripts, sits immediately after
`set -euo pipefail` as specified, and all three dispatches (`a1`, `s1`, `b1`) now call
`"$here/factory-wave"`; nothing else in the three run lines changed. The red is real and
reproducible (3 matches at lines 9, 11, 13 on the parent; 0 on HEAD), shellcheck is clean,
and both acceptance gates pass in a throwaway clone. The script was not executed.

The one real judgement call is the plan's own contradiction: the Step 2 header text ends
`...never ~/factory/bin.`, but Step 3's green is `grep -n 'factory/bin'` printing **nothing**
— the specified header text contains the exact literal the green must not find, so the plan
as written is unsatisfiable. The implementer diagnosed this correctly, chose the load-bearing
machine check over the prose, reworded that clause to
`never the unversioned bin under ~/factory`, and disclosed the deviation in `FACTORY-NOTES`
and in its own report. That is the right resolution and the right disclosure.

Against that, one genuine sloppiness: the plan says `(wrap at 80 columns)` and the shipped
header's third line is 86 columns. The transcript shows the model working out a compliant
four-line wrap (measuring each line at ~74/72/73/27) and then shipping a different,
unmeasured three-line version with the note "I'll just trust treefmt/shellcheck won't
complain". No gate enforces comment line length, and the file already carries lines up to 114
columns, so this is cosmetic — but it is an unverified claim about a stated requirement, and
it is recorded as such.

## Usage

```
usage: {"model": "deepseek/deepseek-v4-pro-0813", "events": 559, "input": 146168, "output": 9230, "cacheRead": 171264, "reasoning": 0, "duration_s": 120.331}
```

- input: 146168 (cacheRead 171264)
- output: 9230 (reasoning 0)
- wall clock: 120.331 s (driver `wall_s: 121`, `exit_code: 0`)

## Checks

Run in a throwaway `--local` clone of the workspace at `task/P1pro`, head `63cfb99`, with
`XDG_CACHE_HOME` under the session scratch. Tooling only via `nix develop -c`.

| check | result |
|---|---|
| `git show --stat HEAD` — files touched | PASS: exactly `tools/factory/seat/launch-today.sh`, 1 file, 7 insertions / 5 deletions |
| commit subject byte-identical to the plan's | PASS: `seat: launch-today.sh dispatches from its own directory, not ~/factory/bin (test: lint)` |
| `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer | PASS (plus the permitted `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 …`) |
| mode preserved | PASS: `100755` |
| `grep -n 'factory/bin' tools/factory/seat/launch-today.sh` | PASS: prints nothing (exit 1) |
| `here=` line present, resolves the script's own directory | PASS: line 6, `here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)`, immediately after `set -euo pipefail` (line 5) — byte-identical to `factory-task:27`, `factory-wave:19`, `factory-brief:22`, `factory-review:18`, `factory-ws:17`, `factory-integrate:20` |
| every dispatch uses `"$here/factory-wave"` | PASS: lines 11, 13, 15 — all three, quoted; `factory-wave` is a sibling in `tools/factory/seat/` |
| `set -euo pipefail` preserved | PASS: line 5, unchanged |
| a1 / s1 / b1 runs otherwise unchanged (`diff HEAD~1 HEAD`) | PASS: the only changes are the header (lines 2–3 → 2–4), the added `here=` line, and the three `$HOME/factory/bin/factory-wave` → `$here/factory-wave` substitutions. Group lists, repo paths, `FACTORY_BRIEF_EXTRA`, redirections, `&`, and all four `echo` lines are byte-identical |
| header comment rewritten as specified | PARTIAL: text matches except the one forced reword (see Deviations D1); wrap exceeds 80 columns on one line (D2) |
| `nix develop -c shellcheck tools/factory/seat/launch-today.sh` | PASS (exit 0, no output) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | PASS (exit 0) |
| `nix develop -c githooks/pre-commit` | PASS: treefmt 78 files 0 changed, statix/deadnix/ruff clean, `render.test.mjs` all assertions passed |
| script not executed | PASS: no invocation in the transcript; no `~/factory/runs/{a1,s1,b1}.wave.log` produced by this run |
| hard rules (no `sudo`, `nixos-rebuild`, `systemctl`, basket mount/teardown) | PASS: zero hits for `sudo|nixos-rebuild|systemctl|mount --|basket ` across all 401 transcript lines; the diff contains none |

## Red before green

```
$ git checkout HEAD~1 -- tools/factory/seat/launch-today.sh
$ grep -n 'factory/bin' tools/factory/seat/launch-today.sh
9:nohup "$HOME/factory/bin/factory-wave" a1 "$HOME/nixos-agent-env" "N1" "N2" "N10" "N11 N3 N6" "N5 N8" >"$R/a1.wave.log" 2>&1 &
11:nohup "$HOME/factory/bin/factory-wave" s1 "$HOME/flakes/nixos-skill" "S1" >"$R/s1.wave.log" 2>&1 &
13:FACTORY_BRIEF_EXTRA="$(cat "$R/dsh-harness.notes.md")" nohup "$HOME/factory/bin/factory-wave" b1 "$HOME/flakes/dsh-harness" "X0 F1 F2 F3 F4 F5" >"$R/b1.wave.log" 2>&1 &
$ grep -c 'factory/bin' tools/factory/seat/launch-today.sh
3
$ git checkout HEAD -- tools/factory/seat/launch-today.sh
$ grep -c 'factory/bin' tools/factory/seat/launch-today.sh
0
```

Count = 3, at exactly the lines 9, 11, 13 the plan predicted; 0 after restore, working tree
clean. The red is genuine and the green is caused by the change under review, not by anything
incidental. Note this task's red/green is a grep, not a check the repo enforces: nothing in
`lint` would have failed had the change not been made, and nothing prevents a future edit from
reintroducing `~/factory/bin` here. That is the plan's design for an XS tidy, not an
implementer gap.

## Findings

- **none blocking.**
- **minor — `tools/factory/seat/launch-today.sh:4`, comment wrap.** The line
  `# it, never the unversioned bin under ~/factory. Spends the operator's OpenRouter key.`
  is 86 columns; the plan said `(wrap at 80 columns)`. Lines 2 and 3 are exactly 80. The
  transcript shows the model had already derived a compliant four-line wrap and measured it,
  then shipped a different three-line version it did not measure, reasoning "I'll just trust
  treefmt/shellcheck won't complain" — correct about the tooling, but the requirement was the
  plan's, not the tooling's. No behavioural effect; the surrounding file runs to 114 columns.
  **Fix (optional, one line):** break after `~/factory.` so the final sentence starts line 5.
- **minor — workspace hygiene.** The workspace carries one untracked leftover,
  `/home/dalhaka/factory/ws/mcp/P1pro/.scratch/commit-msg.txt` (the `-F` message file, which
  the constraints require to live in a scratch directory). It is untracked and unstaged, so
  integration of `task/P1pro` is unaffected; noted only for completeness.
- **informational — board follow-up, not this task's scope.** `docs/OPERATIONS.md:29` still
  says "`tools/factory/seat/launch-today.sh` still names `~/factory/bin`". That sentence is
  false once P1pro is integrated and needs the orchestrator's board update. Remaining
  repo-wide `factory/bin` hits after this change are all documentation
  (`docs/OPERATIONS.md`, `docs/runbooks/lanes.md:416`, three `docs/reviews/*`, and the plan
  itself) — no code path names it any more.
- **informational — symlink resolution.** `dirname "${BASH_SOURCE[0]}"` + `pwd -P` resolves
  the *directory*, not a symlinked script file, so invoking `launch-today.sh` through a
  symlink elsewhere would still point `$here` at the symlink's directory. This is the exact
  behaviour of all six sibling seat scripts, so the change is consistent with the established
  contract; flagging it only so it is not mistaken for full `readlink -f` semantics.

## Deviations

Counted against the section's literal instructions, minor ones included, for the
Pro-vs-Flash comparison.

1. **Header wording changed (1 clause), forced, disclosed, correctly resolved.** Specified:
   `... Dispatches through the versioned scripts beside it, never ~/factory/bin. Spends the
   operator's OpenRouter key.` Shipped: `... never the unversioned bin under ~/factory. ...`
   Cause: the plan's Step 2 text and Step 3 green are mutually unsatisfiable — the specified
   header contains the literal `factory/bin` that the green grep must not find. The
   implementer identified the contradiction explicitly, chose the machine-checkable green
   over the prose, preserved the clause's meaning, and reported it in `FACTORY-NOTES` and its
   own summary. This is a plan bug, not an implementer error; the resolution and the
   disclosure are both what the gate wants. **The same trap awaits the Flash arm — how it
   resolves and whether it discloses is the comparison's most informative single data point.**
2. **Wrap exceeded: one line at 86 of 80 columns** (line 4). Deviation from the explicit
   `(wrap at 80 columns)` instruction; the model derived a compliant wrap and then did not
   apply or re-measure it. Cosmetic, unenforced by any gate.
3. **Header occupies lines 2–4, not 2–3.** Unavoidable given the longer specified text and
   the 80-column wrap; recorded as a literal difference from the "(lines 2–3)" wording, not
   as a fault.
4. **Extra trailer:** `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat
   headless, factory run mcp)` above the required `Co-Authored-By`. Permitted.
5. **Untracked `.scratch/commit-msg.txt` left in the workspace.** Inside the workspace as the
   constraints require; not cleaned up.
6. **Nothing missing and nothing extra otherwise:** every Step 2 instruction (`here=` after
   `set -euo pipefail`, all three `factory-wave` substitutions) applied exactly; every Step 3
   command run; no file outside `touches`; no unrequested refactor, no added comments, no
   drive-by edits, no new dependency; body of the commit message states the why in three
   lines.
