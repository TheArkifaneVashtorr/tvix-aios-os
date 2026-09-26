# Opus gate — seat run mcf2, task P1flashb — APPROVED

## Summary

The fix round does exactly what the rejection asked and nothing else. One commit
(`68781466b28d39897bddbcca7de4fffde93290c6`) on top of base `6e28748`, touching one file,
`tools/factory/seat/launch-today.sh`, +8/-5, mode `100755` preserved. The task's green is
green: `grep -n 'factory/bin' tools/factory/seat/launch-today.sh` prints nothing and exits 1,
where P1flash's branch printed one line and base prints three. The header text is byte-identical
to the plan's quoted string with the one mandated clause substitution (`never the unversioned
bin under ~/factory.`), and every header line is inside 80 columns (72 / 73 / 63 / 39). The
`here=` line is the byte-identical sibling idiom, sits immediately after `set -euo pipefail`,
all three dispatches call `"$here/factory-wave"`, and the a1/s1/b1 run lines are byte-identical
to base's once the dispatch path is normalised. shellcheck, `githooks/pre-commit`, and
`nix build .#checks.x86_64-linux.lint` all pass in a throwaway clone. The script was not
executed.

The delta against the rejected branch is a two-line diff — the reworded clause plus a split at
the sentence boundary — which is the minimal change that clears the rejection. Nothing else on
P1flash's branch was disturbed: `diff` of P1flash's file against HEAD's shows one line replaced
by two, and nothing more.

The round hit a second latent contradiction in the plan, and handled it the way the first one
should have been handled. Step 1 says to re-wrap "so every line is ≤ 80 columns (measure each
line with `awk '{ if (length($0) > 80) print NR": "length($0) }'` — it must print nothing)".
Run against the whole file that awk cannot print nothing: lines 8 and 12–18 are pre-existing
code lines of 84–156 columns, and Step 1's own "keep everything else" plus the run-lines-intact
requirement forbid touching them (base's own header was 92/104 columns, so the whole-file
reading never held even before the change). The implementer worked this out explicitly
(transcript:978–1057), scoped the measurement to the header comment it was re-wrapping — the
same scope this gate used on P1flash — and stated the residual whole-file awk output plainly in
its own report rather than quietly reporting a clean run. That is the correct horn and the
correct disclosure, and it is the judgement call P1flash lost the first round on.

## Usage

```
usage: {"model": "deepseek/deepseek-v4-flash", "events": 1259, "input": 128529, "output": 32469, "cacheRead": 900864, "reasoning": 0, "duration_s": 347.936}
```

- input: 128529 (cacheRead 900864)
- output: 32469 (reasoning 0)
- wall clock: 347.936 s (driver `wall_s: 349`, `exit_code: 0`)

## Checks

Run in a throwaway `--local` clone of the workspace at `task/P1flashb`, head `6878146`, with
`XDG_CACHE_HOME` under the session scratch. Tooling only via `nix develop -c`.

| check | result |
|---|---|
| exactly one commit on top of base `6e287487` | PASS: `git rev-list --count 6e287487..HEAD` = 1, `6878146` only |
| `git show --stat HEAD` — files touched | PASS: exactly `tools/factory/seat/launch-today.sh`, 1 file, 8 insertions / 5 deletions |
| commit subject byte-identical to P1flash's | PASS: `diff` of `%s` from `task/P1flash` (`c9db99e`) and HEAD is empty — `seat: launch-today.sh dispatches from its own directory, not ~/factory/bin (test: lint)` |
| `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer | PASS (plus the permitted `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run mcf2)` above it) |
| mode preserved | PASS: `100755` |
| **`grep -n 'factory/bin' tools/factory/seat/launch-today.sh`** | **PASS: prints nothing, exit 1** |
| the clause reads `never the unversioned bin under ~/factory.` | PASS: line 4, `# scripts beside it, never the unversioned bin under ~/factory.` |
| header text vs the plan's string with the mandated substitution | PASS: unwrapped and `diff`ed against the expected string — byte-identical |
| header lines ≤ 80 columns (awk) | PASS: lines 2/3/4/5 = 72 / 73 / 63 / 39. **Whole-file max = 156 at line 16**; the whole-file awk prints lines 8 (84), 12 (114), 13 (97), 14 (86), 15 (93), 16 (156), 17 (93), 18 (94) — all pre-existing code lines, byte-identical to base (see Findings, D1) |
| `here=` line present, immediately after `set -euo pipefail` | PASS: line 7, `here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)` after line 6 — byte-identical to `factory-task:27` and `factory-wave:19` |
| three `"$here/factory-wave"` dispatches intact | PASS: lines 12, 14, 16 — all three, quoted |
| `set -euo pipefail` intact | PASS: line 6, unchanged |
| a1/s1/b1 run lines byte-identical to base apart from the dispatch path | PASS: with `"$HOME/factory/bin/factory-wave"` and `"$here/factory-wave"` both normalised to a token, `diff` base↔HEAD shows only the header block and the added `here=` line. Group lists, repo paths, `FACTORY_BRIEF_EXTRA`, redirections, `&`, and all four `echo` lines are byte-identical |
| delta vs the rejected P1flash branch is minimal | PASS: `diff` of P1flash's file against HEAD's is one line replaced by two — the reworded clause and the sentence-boundary split. Nothing else |
| `nix develop -c shellcheck tools/factory/seat/launch-today.sh` | PASS (exit 0, no output) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | PASS (exit 0) |
| `nix develop -c githooks/pre-commit` | PASS: treefmt 78 files 0 changed, statix/deadnix/ruff clean, 26 files already formatted, `render.test.mjs` all assertions passed |
| script not executed | PASS: no invocation in the 1203-line transcript; `~/factory/runs/{a1,s1,b1}.wave.log` still dated 2026-09-04 13:59 / — / 14:34, a day before this 13:04–13:10 run |
| hard rules (`sudo`, `nixos-rebuild`, `systemctl`, `mount --`, `basket `, `nix-env`, `rm -rf`) | PASS: zero fixed-string hits across all 1203 transcript lines; the diff contains none |
| other workspaces untouched | PASS: `/home/dalhaka/factory/ws/mcp/P1pro` still at `63cfb99` with only its own pre-existing untracked `.scratch/` |
| clone working tree clean after checks | PASS |

## Red before green

```
$ git show 6e287487:tools/factory/seat/launch-today.sh | grep -n 'factory/bin'
9:nohup "$HOME/factory/bin/factory-wave" a1 "$HOME/nixos-agent-env" ... >"$R/a1.wave.log" 2>&1 &
11:nohup "$HOME/factory/bin/factory-wave" s1 "$HOME/flakes/nixos-skill" "S1" >"$R/s1.wave.log" 2>&1 &
13:FACTORY_BRIEF_EXTRA=... nohup "$HOME/factory/bin/factory-wave" b1 ... >"$R/b1.wave.log" 2>&1 &
count=3

$ git show FETCH_HEAD:tools/factory/seat/launch-today.sh | grep -n 'factory/bin'   # task/P1flash, c9db99e
4:# scripts beside it, never ~/factory/bin. Spends the operator's OpenRouter key.
count=1

$ grep -n 'factory/bin' tools/factory/seat/launch-today.sh                          # HEAD, 6878146
count=0, exit 1
```

Three states, three counts: base 3, the rejected branch 1, HEAD 0. The red is genuine at both
stages and lands on exactly the lines the plan predicted; the green is caused by the change
under review. As in both prior arms, this task's red/green is a grep, not a check the repo
enforces — nothing in `lint` would fail if the change were reverted, and nothing prevents a
future edit from reintroducing `~/factory/bin` here. That is the plan's design for an XS tidy,
not an implementer gap.

## Findings

- **none blocking.**
- **notable, in the branch's favour — the second plan contradiction was found, resolved on the
  right horn, and disclosed.** Step 1's awk, read over the whole file, cannot print nothing:
  lines 8 and 12–18 are 84–156 columns and are the very lines Step 1 forbids touching (base's
  own header was 92/104 columns, so the whole-file reading was never satisfiable, before or
  after). The implementer reasoned this through at length (transcript:978, 982, 995, 1037,
  1041, 1057), scoped the measurement to the header it was re-wrapping — the scope this gate
  used on P1flash — and put the residual whole-file awk output in its own report:
  "The whole-file awk still flags pre-existing >80 code lines 8/12–18, byte-identical to base
  whose own header was 92/104 cols". No overclaim; `FACTORY-CHECKS lint=pass` and
  `FACTORY-NOTES` are both true. This is the same class of trap as round one, resolved the
  other way round.
- **notable — the fix is genuinely minimal.** Against the rejected branch the diff is one line
  replaced by two. The gate review's suggested fix said to keep "the existing compliant wrap",
  which is not possible — swapping the longer clause into P1flash's line 4 takes it to 102
  columns — and the implementer measured that before deciding to split (transcript:299–320),
  rather than assuming. The split falls at a sentence boundary, leaving
  `# Spends the operator's OpenRouter key.` on its own line: not the tightest possible fill,
  but a defensible one and inside the constraint.
- **informational — Pro's workspace was read.** The implementer located
  `/home/dalhaka/factory/ws/mcp/P1pro` and read its `launch-today.sh` to see how the Pro arm
  folded the same text (transcript:275–291). Read-only; the Pro workspace is unmodified and
  still at `63cfb99`. It did **not** copy Pro's fold — it noticed the folds differ and kept its
  own. For the comparison's purposes: the plan and the P1flash review already quote Pro's
  clause verbatim, so nothing was learned that the task did not hand over; recorded so the
  cross-arm read is on the record rather than implied.
- **informational — trailer policy conflict, correctly resolved.** `AGENTS.md` asks for exactly
  one machine-set trailer and no `Co-Authored-By`; the task constraints require both, in order.
  The implementer noted the conflict and followed the more specific instruction
  (transcript:1160), matching P1flash and P1pro.
- **informational — workspace hygiene.** One untracked leftover,
  `/home/dalhaka/factory/ws/mcf2/P1flashb/.scratch/commit-msg.txt` (the `-F` message file the
  constraints require to live in a scratch directory). Untracked and unstaged; integration
  unaffected. Identical to both prior arms.
- **informational — board follow-up, not this task's scope.** `docs/OPERATIONS.md:29` still says
  "`tools/factory/seat/launch-today.sh` still names `~/factory/bin`". That sentence is false
  once this branch is integrated and needs the orchestrator's board update — the same follow-up
  the Pro review raised.
- **informational — symlink resolution.** `dirname "${BASH_SOURCE[0]}"` + `pwd -P` resolves the
  *directory*, not a symlinked script file, so invoking `launch-today.sh` through a symlink
  elsewhere would still point `$here` at the symlink's directory. Identical to all six sibling
  seat scripts, so consistent with the established contract; flagged only so it is not mistaken
  for `readlink -f` semantics.

## Deviations

Counted against the section's literal instructions, minor ones included, in the same style as
the Pro review.

1. **Step 1's awk applied to the header, not the whole file.** Read literally over the file the
   awk prints eight lines and cannot be made to print nothing without rewriting code Step 1
   forbids touching. Diagnosed, resolved on the machine-checkable side of the task (the grep,
   shellcheck, pre-commit and lint are all green), and disclosed in the model's own report. A
   plan bug, not an implementer error; the resolution is what the gate wants.
2. **Header occupies lines 2–5, not P1flash's 2–4, and the "existing compliant wrap" the
   rejection suggested keeping was necessarily changed.** Forced: the substituted clause is 23
   characters longer and would put line 4 at 102 columns. Recorded as a literal difference from
   the review's wording, not as a fault.
3. **Extra trailer:** `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat
   headless, factory run mcf2)` above the required `Co-Authored-By`. Permitted. Same as both
   prior arms.
4. **Untracked `.scratch/commit-msg.txt` left in the workspace.** Inside the workspace as the
   constraints require; not cleaned up. Same as both prior arms.
5. **Read another arm's workspace** (`/home/dalhaka/factory/ws/mcp/P1pro`, read-only) to compare
   header folds. Outside the source the plan named (`ws/mcf2/P1flash`), no modification made,
   and its fold was not adopted.
6. **Nothing missing and nothing extra otherwise:** the clause substitution is exactly the one
   specified, the header is otherwise byte-identical to the plan's string, all four Step 2
   commands were run and their real output reported, one commit with the byte-identical
   subject, no file outside `touches`, no unrequested refactor, no drive-by edits, no new
   dependency; the commit body states the why in seven lines and names the reason for the
   reword.

Deviation count: **5** substantive (1–5), **none blocking** — against P1flash's 4 (1 blocking)
and P1pro's 5 (0 blocking).

## Comparison with P1pro

| | P1pro (Pro) | P1flash + P1flashb (Flash) |
|---|---|---|
| verdict after fix round | APPROVED (first round) | **APPROVED** (second round) |
| rounds needed | **1** | **2** |
| deviations counted | 5 (0 blocking) | round 1: 4 (1 blocking); round 2: 5 (0 blocking) |
| task's stated green (`grep` prints nothing) | achieved in round 1 | not in round 1 (3 → 1); **achieved in round 2 (→ 0)** |
| wrap compliance | **FAIL** — line 4 at 86 of 80; a compliant wrap was derived, then a different one shipped unmeasured | **PASS in both rounds** — round 1: 72/73/79; round 2: 72/73/63/39, measured and stated before shipping |
| header text vs the plan's string | one clause reworded (forced) | round 2: same clause, plus the mandated split — byte-identical after unwrap |
| second contradiction (whole-file awk) | not encountered | **found, scoped to the header, disclosed** |
| `lint` + `pre-commit` + shellcheck | pass | pass in both rounds |
| code change (`here=`, three dispatches, a1/s1/b1 intact) | correct | correct — identical |
| usage: input | 146168 (cacheRead 171264) | **200480** (71951 + 128529; cacheRead 1283584) |
| usage: output | 9230 | **45973** (13504 + 32469) — 5.0× Pro |
| usage: events | 559 | **2016** (757 + 1259) — 3.6× Pro |
| wall clock | 120.331 s | **527.4 s** (179.486 + 347.936) — 4.4× Pro |
| transcript lines | 401 | **1602** (399 + 1203) — 4.0× Pro |
| Opus gate rounds consumed | 1 | 2 |

Read together with the round-one review: Flash was the more literal-minded of the two on the
mechanical requirements and stayed that way — it honoured the verbatim text and the column
limit in both rounds, and in round two it also caught a contradiction Pro never met. What cost
it the comparison was round one's judgement call, and the price of that call is visible here:
two implementer rounds and two gate rounds against Pro's one each, five times the output
tokens, four times the wall clock, and four times the transcript to arrive at a branch that is
now, on the merits, slightly the better of the two (a compliant wrap where Pro's line 4 sits at
86 columns). The cheap model reached the same place; getting a second chance is what made it
expensive. One task is still not a measurement.
