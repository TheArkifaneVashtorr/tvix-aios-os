# Opus gate — seat run hr1, task H2 — REJECTED

## Summary

H1 (`22880ee`) is **APPROVED**; H2 (`c7c45d6`) is **REJECTED**, so the header carries H2's key and the
run's verdict is REJECTED. H1's archive move is clean and proven load-bearing: the suite runs 98/98 from
`archive/2026-09-05-planning-factory/tests/`, two independent mutations each kill it, `factory/` is gone,
the grep gate is silent, and the README/CHANGELOG/AGENTS.md edits say what the decision says. H2 pastes the
plan's routing block into all four files and the routed command reproduces byte-for-byte, but the block
asserts a mechanism that does not exist — `FACTORY_ROUTING_TABLE` is read nowhere in
`tools/factory/seat/factory-lib.sh` and I proved by experiment that setting it changes nothing — and the
rewritten "Model Selection" section builds its whole escalation story on a `size` knob that the live table
ignores in every cell but one, while two "most capable available model" instructions survive elsewhere in
the same skill (one of them pointing back at the section that no longer defines the idea). The fix is small
and local to H2's four files (plus, optionally, one env-var read in `factory-lib.sh`); H1 needs nothing.

## H1

**Verdict: APPROVED.** Commit `22880ee`, subject byte-identical to the plan's (`cmp` against the plan
string: identical), `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer present, plus a
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run hr1)` line that
the harness's own AGENTS.md convention asks for.

- `factory/` is gone from the tree; `archive/2026-09-05-planning-factory/` holds `dark-factory.js`,
  `README.md` and 15 `tests/*.test.mjs`. Sixteen of eighteen moved files are `R100` renames — the script
  and thirteen tests moved verbatim; only `changelog.test.mjs` (R098) and `skill-catalog.test.mjs` (R099)
  changed, each by exactly one extra `..` level in its repo-root resolution, which is what the deeper path
  requires.
- `nix develop /home/dalhaka/nixos-agent-env -c node --test archive/2026-09-05-planning-factory/tests/*.test.mjs`
  → `tests 98 / pass 98 / fail 0`, RC=0. The notes' 98/98 is exact.
- `grep -rn 'factory/dark-factory\|factory/tests' . --exclude-dir=.git --exclude-dir=archive` prints
  **nothing** (rc=1) — stricter than the plan's "only CHANGELOG history lines" allowance, because the
  2026-09-04 CHANGELOG entries never named those paths.
- README's factory section is now a five-line "Archived: planning factory" pointer plus an explicit
  statement that the repo's check surface is empty (it ships no `flake.nix`) — the plan asked the author to
  "say which", and he did. The role→model table is out of the README; its only surviving copy is inside
  `archive/.../README.md`, which the grep gate excludes by design.
- CHANGELOG has the dated `## 2026-09-05` section with the commit's subject as its one line.
- The archive README states what the factory was, the decision path with its addendum, the 2026-09-04 spend,
  and the still-working test command including the `XDG_CACHE_HOME` prefix for a read-only `$HOME`.

## H2

**Verdict: REJECTED.** Commit `c7c45d6` touches exactly the four planned files, subject byte-identical
(`cmp`: identical), trailer present. The routing block is present in all four sections
(`skills/using-superpowers/references/dsh-tools.md` "Subagents", `skills/subagent-driven-development/SKILL.md`
"Model Selection", `AGENTS.md`, README's new "Model routing"), it says claude rows are never requested, it
names `FACTORY_ROUTING_TABLE`, and the grep gate is red on H1's tree and green here. What it says is not
all true.

**H2-1 (blocking) — `FACTORY_ROUTING_TABLE` does not exist.** `factory_route` resolves its table as
`local file=${4:-$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml}` (factory-lib.sh:197). The identifier
`FACTORY_ROUTING_TABLE` appears nowhere in `~/nixos-agent-env` outside the plan and the decision — not in
`tools/factory/seat/`, not anywhere else. I copied the table, replaced every `deepseek-v4-flash` with
`zz/fake-model`, exported `FACTORY_ROUTING_TABLE` at it, and re-ran the block's own example: the answer was
still `deepseek/deepseek-v4-flash off`. An agent that believes this sentence and points the variable at a
scratch table gets the production table's answer and no warning — a silent wrong-model failure, which is
exactly what routing-from-a-table was adopted to prevent. The real overrides are `FACTORY_TOOLBOX_REPO`
(repo root) and the optional 4th positional `FILE` argument; both work. Note the block's other two
env-var claims are true (`OPENROUTER_REASONING_EFFORT` and `OPENROUTER_MODEL` are honored per
factory-lib.sh's own header), which makes the invented third one harder for a reader to doubt. The plan and
the decision carry the same sentence, so this is inherited, not invented by the implementer — but four
harness documents that agents follow now assert it, and prose is not evidence.

**H2-2 (blocking) — the rewritten section sells a `size` knob the table does not have.** The section now
reads "route `implement` at the task's smallest `size`", "route at a larger `size`", "re-route the
implementer at least one `size` larger", "prefer a mid `size` over the cheapest row", "a small mechanical
diff does not need a large `size`". Against today's `routing.toml`, `--route openrouter` returns:

    implement code XS -> flash off      implement docs XS..L, any -> flash off
    implement code S/M/L/any -> pro medium
    review    code XS..L, any -> pro medium
    review    docs XS..L, any -> pro medium

`size` changes the answer in exactly one cell (implement/code XS vs the rest) and never for `review`. So
the fix-loop escalation rule ("one `size` larger") is inert in every case it is written for, the review
scaling advice is inert everywhere, and the "mid `size`" floor names a tier that does not exist. Worse, the
block above it says `size` comes from the task's `### KEY (kind, size)` heading — a fact about the task —
while these bullets tell the agent to *choose* a size by how much judgment it thinks the work needs. That
reintroduces the free choice the change was meant to remove, through a different knob, and gives it a false
air of determinism. The old text at least described something real (model tiers); the rewrite describes
something that is not.

**H2-3 (major) — the contradiction the change was supposed to remove is still in the file, twice.**
`skills/subagent-driven-development/SKILL.md:462`: "Dispatch on the most capable available model (see Model
Selection)" — a cross-reference to a section that no longer contains the concept — and line 572 in the
worked example: "dispatch final code-reviewer, most capable model". An agent reading the skill end-to-end
gets the routing block and then, at the point where it actually dispatches the final review, an instruction
to pick the most capable model by hand. `SKILL.md` is inside H2's declared touches, so this was in scope.
Inside the "Model Selection" section itself the free-choice language is genuinely gone ("use a fast, cheap
model", "use a standard model", "use the most capable available model", and the tier-signal list are all
replaced) — the defect is that the sweep stopped at the section boundary.

**On the block's unambiguity (the question the gate was asked):** role and kind derivation is clear; the
`any` fallback is stated only for `size` ("`any` when unknown"), though `factory_route` accepts `any` for
role and kind too, and I confirmed `any` resolves correctly. The roles list omits `orchestrate`, which is
defensible — it has only a `claude` row and the seat cannot reach it.

## Checks

All run from a throwaway clone of the implementer workspace at
`…/scratchpad/gate-hr1-H2`, tooling via `nix develop /home/dalhaka/nixos-agent-env -c` with
`XDG_CACHE_HOME` under the scratchpad. Nothing was written to `~/nixos-agent-env` (status clean) or to the
workspace (status clean, HEAD still `c7c45d6`); no seat launched; no `--no-verify`.

| # | Check | Result |
| --- | --- | --- |
| 1 | H1 subject vs plan, byte compare | identical |
| 2 | H2 subject vs plan, byte compare | identical |
| 3 | Both trailers present | yes (plus the harness's `Generated-By`) |
| 4 | H1 file set ⊆ plan `touches` | **no** — see Deviations |
| 5 | H2 file set = the four planned files | yes, exactly |
| 6 | `factory/` absent at HEAD | yes |
| 7 | Archive suite on HEAD | tests 98 / pass 98 / fail 0, RC=0 |
| 8 | H1 grep gate (`factory/dark-factory\|factory/tests`, archive excluded) | silent, rc=1 |
| 9 | H2 grep gate (`deepseek/deepseek\|moonshotai/\|z-ai/\|deepseekPro\|glmFlash` over AGENTS.md README.md skills/) | silent, rc=1 |
| 10 | `factory_route --route openrouter implement docs XS` / `review code S` from the clone | `deepseek/deepseek-v4-flash off` / `deepseek/deepseek-v4-pro-0813 medium` — matches the plan and the commit body verbatim |
| 11 | `FACTORY_ROUTING_TABLE` honored | **no** — override ignored, production answer returned |
| 12 | Routing block present in all four files, claude rows named unreachable | yes |
| 13 | `githooks/pre-commit` in the clone | **does not exist** — see Deviations |
| 14 | README factory section is an archive pointer; role→model table gone | yes |
| 15 | CHANGELOG dated line | yes |

## Red before green

**H1.** The plan's literal wording ("after the `git mv`, the OLD command must fail") does not hold, and the
implementer noticed it in his own reasoning rather than papering over it: node 24 expands
`factory/tests/*.test.mjs` itself, and an unmatched pattern yields `tests 0 / pass 0 / fail 0`, **RC=0** —
a vacuous pass, not a failure. I re-ran it: old command on HEAD → 0 tests, RC=0. So the exit code is not a
gate in either direction, and neither the commit body nor the result notes claim otherwise (both say only
that the check surface is now empty). The discriminating evidence is the test count, and it is clean and
symmetric, measured on a worktree of each rev:

| | old path command | archive path command |
| --- | --- | --- |
| base `e31370d` | tests 98 / pass 98 | tests 0 |
| HEAD `22880ee` | tests 0 | tests 98 / pass 98 |

**Mutations (H1).** Both kill the suite, so the tests are load-bearing where they now live and the import
fix is itself covered:

- `syntax.test.mjs`: `join(here, '..', 'dark-factory.js')` → `join(here, '.', …)` ⇒ 97 pass / **1 fail**, RC=1.
- `changelog.test.mjs`: revert the archive fix (three `..` back to two) ⇒ 97 pass / **1 fail**, RC=1.
- Restored tree re-runs 98/98, RC=0.

**H2.** The grep gate is the only executable gate, and it is real:

- On base `22880ee`: two hits (`AGENTS.md:29`, `AGENTS.md:30` — `deepseekPro`, `glmFlash`), rc=0 → **red**.
- On HEAD `c7c45d6`: silent, rc=1 → **green**.

The routing command's output was reproduced independently and matches the body's paste exactly. Neither of
these gates can see H2-1, H2-2 or H2-3, which is why the prose judgment is the verdict here.

## Findings

1. **H2-1, blocking.** `FACTORY_ROUTING_TABLE` is a phantom. Either implement it in `factory_route`
   (`local file=${4:-${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml}}`, with a
   test that a pointed-at table wins) or replace the sentence in all four blocks — and in the plan and the
   decision addendum, which are where it came from — with what is true: the table path follows
   `FACTORY_TOOLBOX_REPO`, and a fourth positional argument names a file directly. Same edit either way; do
   it in one place and copy.
2. **H2-2, blocking.** Rewrite the five `size`-escalation bullets so they say what the table does: `size`
   and `kind` come off the task heading, they are not a dial; the only step the OpenRouter rows currently
   make is implement/code XS → flash versus everything else → pro; escalation, if wanted, is a new row with
   a measurement behind it, not a larger letter. If the intent really is a judgment dial, it needs rows
   before it needs prose.
3. **H2-3, major.** Fix `SKILL.md:462` and the example at `:572` to route the final whole-branch review
   (`review`, the task's kind/size) instead of naming "the most capable available model", and drop the now
   dangling "(see Model Selection)" promise.
4. **Minor, H2.** `FACTORY-CHECKS pre-commit=pass` in `H2.result` records a check that cannot have run —
   the repo has no `githooks/` and no `core.hooksPath`. The implementer said so plainly in his transcript
   ("no pre-commit hook is installed (nothing to run)"), so this is a plan/record mismatch rather than a
   false claim by the agent, but the machine-readable line reads as a green gate to anything that consumes
   results. The plan should have given H2 `acceptance: grep` (or the H1 archive suite), and the result line
   should not say `pass` for a check that does not exist.
5. **Minor, H1.** The plan's Step 1 asks for a red that node cannot produce; a check-surface removal is
   proved by test counts, not exit codes. Future archive tasks should state the assertion as "the old path
   runs 0 tests, the new path runs N" or wrap the command so an empty glob is an error.
6. **Observation, no action.** `changelog.test.mjs` and `skill-catalog.test.mjs` still assert against the
   live repo root (CHANGELOG keys, the whole `skills/` tree), not just the archived script. Archiving them
   keeps those assertions running, which is a quiet benefit — but it also means the "archive" suite is now
   the only thing checking the live skills tree in a repo whose README says its check surface is empty.
   Worth a line on the board.

## Deviations

- **H1 touched two files outside its declared `touches`:** `AGENTS.md` and
  `skills/using-superpowers/references/dsh-tools.md`. Both edits were forced by the plan's own Step 2 grep
  gate — each file named `factory/tests` or `factory/dark-factory.js` — so the `touches` list was simply
  incomplete relative to the same task's acceptance. Harmless here (H2 `dependsOn` H1, so the two ran
  sequentially and nothing collided), but a parallel wave with that list would have mis-scheduled.
  Not blocking; fix the plan's `touches`, not the commit.
- **`githooks/pre-commit` / `pre-push` do not exist in this repo**, and never did — the plan's file list and
  H2's `acceptance: pre-commit` both assume a convention borrowed from `~/nixos-agent-env`. Nothing to read,
  nothing to run, nothing to update; the gate step that called for running the hook is not satisfiable and
  is recorded here as unsatisfiable rather than passed. See finding 4.
- **The three blocking/major H2 findings are text-only.** No code in either repo needs to change unless
  finding 1 is resolved by implementing the variable rather than deleting the claim.
