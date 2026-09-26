---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run hr1, task H2b — APPROVED

## Summary

H2b (`a2a71bd`) clears all three of H2's findings with evidence. `FACTORY_ROUTING_TABLE` is no longer a
phantom: I re-ran the experiment that failed at the H2 gate against RT4's `factory-lib.sh` and a fixture
table now wins (`zz/gate-fixture-model high` instead of the production row) — the sentence in the block
becomes true on `main` the moment RT4 lands, and is still false against today's `main` copy of the library,
which I also measured. The `size`-escalation story is gone: the seven lines that told an agent to route at
"the smallest `size`", "a larger `size`", "a mid `size`" are replaced by the rule the plan asked for — role,
kind and size are read off the `### KEY (kind, size)` heading, the table decides, a fix round keeps the same
row, a model change is a `routing.toml` row change justified by a measurement. Both stray free-choice
instructions are gone, and the implementer swept further than the plan asked: the process diagram, the
`BLOCKED` handler and the rounds-4-5 escalation step also stopped promising a capability bump. One commit on
base, exactly the four planned files, subject byte-identical, trailers present, grep gate red→green, archive
suite 98/98.

What remains is residue outside the assigned touches, not a surviving blocker: two prompt templates in the
same skill directory still carry the advice this change removed, and the grep gate's pattern set is literal
enough that it cannot see them. Findings 1 and 2 below name them for a follow-up round.

## Checks

Throwaway clone of the implementer workspace at `…/scratchpad/gate-hr1-H2b`; tooling via
`nix develop /home/dalhaka/nixos-agent-env -c` with `XDG_CACHE_HOME` under the scratchpad. Nothing was
written to `~/nixos-agent-env` (`git status` clean), nothing to the workspace (clean, HEAD still
`a2a71bd08be0`), nothing to `~/flakes/dsh-harness`; no seat launched; no `sudo`; RT4's workspace and the H2
workspace were read only (a `git fetch` out of each into the throwaway clone).

| # | Check | Result |
| --- | --- | --- |
| 1 | Exactly one commit on base `6308930` | `git rev-list --count 6308930..HEAD` → 1 |
| 2 | `git show --stat HEAD` = the four planned files | `AGENTS.md`, `README.md`, `skills/subagent-driven-development/SKILL.md`, `skills/using-superpowers/references/dsh-tools.md` — exactly, nothing else |
| 3 | Subject byte-identical to H2's / the plan's | `cmp` against the plan string: identical |
| 4 | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` | present (plus the harness's `Generated-By` line) |
| 5 | Grep gate on HEAD (7 patterns over `AGENTS.md README.md skills/`) | silent, rc=1 |
| 6 | Archive suite on HEAD | `tests 98 / pass 98 / fail 0`, RC=0 |
| 7 | Routing block present in all four files | yes — AGENTS.md §"the seat", README §"Model routing", dsh-tools.md §"Subagents", SKILL.md §"Model Selection"; the seven-line block is verbatim-identical in all four |
| 8 | Block states claude rows unreachable / never requested | yes, in all four |
| 9 | Commit body's routed command reproduces | `implement docs S` → `deepseek/deepseek-v4-flash off`; `review docs L` → `deepseek/deepseek-v4-pro-0813 medium` — matches the body byte-for-byte |
| 10 | `FACTORY_ROUTING_TABLE` honored by RT4 | **yes** — see below |
| 11 | Size-escalation prose gone | yes — H2's lines 201/205/208/213/225/228/229 all replaced; no `smallest size` / `larger size` / `mid size` anywhere at HEAD |
| 12 | `most capable available model` / `most capable model` anywhere | rc=1 both — SKILL.md:462 and :572 (H2 line numbers) both rewritten to route the `review` role |
| 13 | "Model Selection" states the four required facts | yes — heading-derived role/kind/size with `any` fallback (SKILL.md:196-199), table decides (198), fix round keeps the row (199), model change = row change justified by a measurement (199-201) |

**Check 10, the experiment that failed at the H2 gate, re-run.** Fixture table with one distinctive default
row (`role/kind/size = any`, `model = "zz/gate-fixture-model"`, `effort = "high"`):

    RT4's lib, FACTORY_ROUTING_TABLE=<fixture>   → zz/gate-fixture-model high     ← override honored
    RT4's lib, no override                       → deepseek/deepseek-v4-pro-0813 medium
    main's lib, FACTORY_ROUTING_TABLE=<fixture>  → deepseek/deepseek-v4-pro-0813 medium   ← still ignored

RT4's `tools/factory/seat/factory-lib.sh:199` reads
`local file=${4:-${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml}}`, with the same
precedence applied at line 352 and documented in the header at 190 and 350 — an explicit 4th positional
`FILE` still wins over the env var, which is the right order. **The block's sentence is therefore true
against RT4 and still false against `main`.** Until RT4 lands in `~/nixos-agent-env`, four harness documents
assert a mechanism the host's live library does not have. The orchestrator sequences that; it is recorded
here as a landing dependency, not a defect in H2b.

## Red before green

The grep gate is the executable gate, and it discriminates in both directions.

| tree | grep gate (7 patterns) |
| --- | --- |
| base `6308930` (main + H1, pre-H2) | **5 hits, rc=0 — red**: `AGENTS.md:29,30` (`deepseekPro`, `glmFlash`), `SKILL.md:188` (`fast, cheap model`), `SKILL.md:192` and `:452` (`most capable available model`) |
| H2 `c7c45d6` (the tree being fixed) | **1 hit, rc=0 — red**: `SKILL.md:462` — `on the most capable available model (see Model Selection)` |
| HEAD `a2a71bd` | **silent, rc=1 — green** |

The second row is the sharper red: it is exactly H2-3's first stray instruction, and it fails on the tree
H2b was dispatched to fix.

**The escalation text is not covered by any pattern**, so I measured it by hand across the same three trees.
H2's `SKILL.md` carried seven size-escalation lines (201, 205, 208, 213, 225, 228, 229 — "route `implement`
at the task's smallest `size`", "at a larger `size`", "Prefer a mid `size`", …); at HEAD a search for
`smallest size`, `larger size` and `mid size` returns nothing, and the replacement text states the rule
instead. Likewise H2-3's second instruction, `SKILL.md:572` "dispatch final code-reviewer, most capable
model", is **not** matched by the gate's `most capable available model` pattern — I searched the bare string
separately: present on the H2 tree, absent at HEAD (rc=1). The implementer fixed it despite the gate being
unable to see it. See finding 3.

## Findings

1. **Major, follow-up round.** The removed advice survives in two prompt templates of the *same* skill, both
   pre-existing on base and both outside H2b's declared `touches`, so this is residue the H2 gate missed
   rather than a regression:
   - `skills/subagent-driven-development/re-review-prompt.md:105` — "`[MODEL]` — REQUIRED: reviewer model per
     SKILL.md Model Selection; scoped re-reviews of small fix diffs take a cheap-to-mid tier". This is the
     H2-2 defect verbatim (pick a tier by diff size) *and* the H2-3 shape (a cross-reference to a section
     that no longer contains the concept). It is read every time a scoped re-review is dispatched.
   - `skills/subagent-driven-development/implementer-prompt.md:89` — "The controller can provide more
     context, re-dispatch with a more capable model, or break the task into smaller pieces." SKILL.md:311-313
     now says the opposite in its `BLOCKED` handler ("a fix round keeps the same row"), so the implementer's
     own prompt promises it an escalation the controller's skill has just abolished.

   Both are one-line edits pointing at `factory_route review <kind> <size>` and at the same-row rule. A
   follow-up H2c should take them plus finding 2's patterns.

2. **Major, methodological.** The grep gate's seven patterns are the literal strings H2's review quoted, so
   the gate can only ever certify that H2's exact defects are gone — it is silent on `more capable model`,
   `most capable model`, `cheap-to-mid tier`, `mid-tier`, and every other phrasing of the same instruction.
   It reported green on a tree that still contains two of them one directory over. Any H2c gate should add
   `more capable\|most capable\|cheap-to-mid\|mid-tier\|least powerful` to the pattern set and drop the
   `AGENTS.md README.md skills/` restriction in favour of the whole tree minus `archive/`.

3. **Minor.** `SKILL.md:186`, the section's opening line, still reads "Use the least powerful model that can
   handle each role to conserve cost and increase speed." — an imperative to select by power, sitting two
   lines above "Choose a sub-agent's model from the routing table, never from memory". A careful reader takes
   it as the table's design rationale; a careless one takes it as licence. Reword to state it as *why the
   rows are what they are*, not as an instruction to the dispatcher.

4. **Minor.** The "Review tasks" bullet (SKILL.md:214-217) says the `size` field "carries the scaling (a small
   mechanical diff is a small `size`, a subtle concurrency change a larger one)". Against today's
   `routing.toml` the `review` role has exactly one OpenRouter row (`review/any/any` → pro medium), so `size`
   changes no review answer at all. The sentence is not the H2-2 defect — it explicitly forbids choosing the
   size by hand and grounds it in the heading — but it still describes a gradient the table does not have.
   Either add review rows with a measurement behind them, or say plainly that `size` is passed through and
   currently only distinguishes implement/code XS.

5. **Minor, inherited.** The commit subject ends `(test: pre-commit)` and `H2b.result` records
   `pre-commit=pass`, in a repo with no `githooks/` and no `core.hooksPath` — the same defect finding 4 of the
   H2 review named. Here it is forced: the plan mandates a byte-identical subject and H2's subject carries the
   string. Not the implementer's fault and not fixable without breaking the byte-identity requirement; when
   the plan next writes a harness subject, the check name should be `grep-gate, node-test`. The result's
   `pre-commit=pass` line should still not have been emitted for a check that cannot run.

6. **Observation, no action.** `skills/using-superpowers/references/codex-tools.md:72,77` carries the same
   tier language ("a deliberate tier instead of silently inheriting the session's most …",
   `default_subagent_model = "<a mid-tier model from your spawn allowlist>"`). That file documents a
   different harness whose sub-agents are not routed by `factory_route`, so it is defensibly out of scope —
   but it is the last place in `skills/` where an agent is told to pick a tier, and a reader who does not
   notice the filename will not notice the distinction either.

## Deviations

- **The implementer exceeded the plan's Step 2, correctly.** The plan named only the escalation bullets and
  lines ~462 and ~572. He also rewrote the process diagram (three `digraph` nodes, "more capable model" →
  "same routed row"), the `BLOCKED` handler's item 2, and the rounds-4-5 escalation paragraph — every place
  the file still promised a capability bump. Without those the section would have contradicted itself. In
  scope (same file, same defect class), and it is why the fix is complete inside `SKILL.md`.
- **The block's `FACTORY_ROUTING_TABLE` sentence is true only against RT4**, which is on branch `task/RT4` in
  `/home/dalhaka/factory/ws/rt4/RT4` and not yet on `~/nixos-agent-env` `main`. Measured in both directions
  (check 10). H2b's four documents ship the claim ahead of the mechanism; the orchestrator sequences RT4's
  landing, and this is recorded, not held against the task — the plan's Step 2 states the dependency
  explicitly.
- **Findings 1, 3, 4 and 6 are all text-only and outside `touches`.** No code in either repo changes. Nothing
  here blocks H2b; finding 1 should become an H2c on the plan.
