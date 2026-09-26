# Plan judging instructions

Read this file together with the rubric in `tools/factory/plan/rubric.md`.

Refute first: default to the lower score when unsure. Score all 14 rows 0–3 with one reason each; list errata as {criterion, task, finding, fix}; count wrongFacts; say dispatchable (true only if every row ≥ 1 and rows 2, 3, 5, 6, 7, 13 ≥ 2).

## Implementer lens

You are a blind implementer with no session context. For three sections chosen at random, run tools/factory/seat/factory-brief <draft> <KEY> from the repo (read-only; it reads any plan path and prints to stdout — the rules name it as allowed) and try to land the task from that text alone: list every path, signature, command or fact you would have had to invent. Score row 3 from that list first; then the rest.

## Reviewer lens

You are the Opus gate rehearsing its mutation table. For every assertion the draft names, write the one-line mutant the draft names and one it does not; mark each survivor. For every rule, write one spelling outside it. A proof shape the draft names ("a fixture listing, or an assertion over the layout") is not a mutant: write the mutant that shape would need, and if the draft did not name it, mark it a survivor. Score rows 5, 6 and 7 from the survivors first; then the rest.

## Whole lens

Judge the whole plan against the spec and the tree: re-run three cited commands and count wrong facts (row 2). For row 13, copy the tree with its .git to ${SCRATCH}/tree (cp -a ${REPO} ${SCRATCH}/tree), place the draft under ${SCRATCH}/tree/docs/superpowers/plans/, write a one-repo file — printf '[[repo]]\nname = "nixos-agent-env"\npath = "%s"\n' ${SCRATCH}/tree > ${SCRATCH}/repos.toml — and run, from ${REPO}: nix develop -c python3 pkgs/evidence/tasks.py --root ${SCRATCH}/tree --repos ${SCRATCH}/repos.toml --runs-dir /nonexistent --store /nonexistent check, then conflicts and waves --repo nixos-agent-env --json the same way (the --root-only form re-reads the live tree through docs/ledger/repos.toml and cannot see the draft; after P1, tasks.py check --draft replaces this). Read the Waves, Operator and Dispatch sections against §4 and §5 of the design (rows 8, 10, 11); the invariants (row 9); the decisions (row 14).