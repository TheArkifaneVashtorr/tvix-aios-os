# Concept 2026-09-08f — a plan's cross-plan sequencing rule must be re-measured at Ship, not carried from the packet

**Class:** planning-process fix (a rubric/process concept, no spec item of its
own).

**Status:** proposed 2026-09-08, from the spend-telemetry plan's revision-1
judging round (`docs/reviews/plan-judgements/2026-09-08-spend-telemetry-r1.md`,
criteria 2 and 8) and applied while shipping
`docs/superpowers/plans/2026-09-08-spend-telemetry.md`.

**Origin:** the plan's packet was taken at `a285c7ec`, when a concurrently-open
chain (T1W, plan 2026-09-06-telemetry-store-1, status `rejected, fix round
owed`) shared ledger files and `flake.nix` with several of this plan's tasks.
The revision-1 draft built a pre-launch gate directly on that status label:
"before every launch of wave 2, 3 or 5, `tasks.py --root . brief | grep -F
'Running:'` must not name T1Wb." By the time the plan reached Ship, HEAD had
moved to `5ea2491` ("a chain root may end in a capital letter, so T1Wb and
T3Mb close their roots"), which closed that chain; a live
`tasks.py --root . brief` at Ship showed `rejected` = 0 and no T1W/T1Wb
anywhere. The gate as drafted could therefore never fire — not because the
underlying hazard was gone (two plans can still collide on shared files), but
because the specific status label the rule was pinned to had gone stale
between packet time and Ship time. The same staleness hit the landing
recipe's expected-conflict list, which named files against the packet's HEAD
while four commits (three inside `pkgs/evidence`) had since landed.

**Idea:** a plan's cross-plan sequencing rule and its landing recipe's
expected-conflict list are measurements, not decisions — they describe the
state of *other* plans and the *current* tree, both of which move on their
own schedule independent of this plan's drafting and judging rounds. Treat
them the same way `waves`/`conflicts` are already treated (§Waves already
says "computed with `tasks.py check --draft`, pasted in §Dispatch" — i.e.
re-run, not hand-typed): the Ship phase re-runs `tasks.py --root . brief` and
`git log --oneline <packet-head>..HEAD --name-only` immediately before
writing the sequencing rule and the landing recipe, and states the rule in a
form that survives the next status change — "no key that touches this plan's
files is `Running`" rather than "T1Wb is not `Running`." A record item about
a *different* plan's defect (here, tel2/T1W's missing per-record refusal in
`_merge_jsonl`) stays true and worth keeping in the Assumptions regardless of
that plan's current chain key or status; only the *gate mechanism* built on
top of it needs to be status-agnostic.

**Payoff:** a plan shipped days or weeks after its packet was taken (normal
for an eight-task, multi-wave plan with operator gates in between) does not
carry a dead pre-check that silently never holds anything back, and its
landing recipe does not send an operator hunting for a merge conflict in a
file that already landed cleanly through an unrelated task. Cheap to apply:
one `tasks.py brief` and one `git log --name-only` at Ship, and phrasing the
rule generically instead of by a specific key or status word.

**Dependencies:** none — a drafting-discipline note for the Ship phase of the
`plan` skill, not a code change. Could be promoted to a checklist line in
`docs/superpowers/plans/` skill instructions (a "Ship checklist" section, as
added to the spend-telemetry plan itself) if it recurs.

**Earliest landing:** immediate — it is a habit for the next plan's Ship
phase, not a task with tests. If it recurs on a third plan, promote it to an
explicit step in the planning skill's Ship-phase instructions.
