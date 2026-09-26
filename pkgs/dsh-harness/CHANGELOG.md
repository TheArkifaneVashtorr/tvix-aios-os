# Changelog

## 2026-09-08

- driving: the driving skill for the operator's seat — brief, dispatch, gate and integrate a typed plan's tasks as calls to the tools/factory/seat driver scripts, what the driver decides alone, the rung read from the key; the exit-code table is the driver's own mapping (test: grep-gate node-test)

## 2026-09-06

- planning: the planning skill for house repos (typed plans from approved specs, the reference extractions and the judge prompt); writing-plans re-scoped to repositories without a typed task graph; the role list now includes plan (test: grep-gate node-test)

## 2026-09-05

- factory: the three-model planning factory is archived under archive/2026-09-05-planning-factory (decision 2026-09-05, nixos-agent-env) (test: node-test)

## 2026-09-04

The 2026-09-04 factory chain: one bullet per commit from
`git log --no-merges --format='%h %s' f2018e7..HEAD`, grouped by task.
Task F7's first attempt (5bfc81c, a docs task) was never integrated and has no
entry; its retry F7B produced the docs commit below.

### X0

- 8f6fbdb factory: restore spec in plan projection and validate args.tasks on entry (test: syntax x0-validation)

### F1

- f8273b2 factory: log and summarise review verdicts instead of discarding them (test: syntax f1-review-summary)

### F2

- 9eda1b6 factory: retry dead implementers once, fail dependents, and warn on a dirty session tree (test: syntax f2-implementer-retry f2-tree-guard)

### F3

- b9f749f factory: schedule implementers in deterministic dependency waves, not array order (test: syntax f3-scheduler f2-implementer-retry)

### F4

- 9316214 factory: state the commit convention in the implementer prompt (test: syntax f4-commit-convention)

### F5

- e009b72 factory: bound the planning and consolidation essays with word caps (test: syntax f5-planning-bounds)

### F6

- 4a5f77f skills: re-sync vendored nixos, strip superpowers: prefix, rewrite plugin-relative paths (test: skill-catalog)
- 0e8789a skills: cross-skill references resolve against the referring skill directory; catalog test checks from each SKILL.md; README rationale corrected (test: skill-catalog)

### F6b

- f39690c skills: re-sync vendored nixos from nixos-skill master 962849d (test: skill-catalog)

### F8

- 1bc9113 factory: give each task a persistent isolated clone and integrate deterministically (test: syntax f8-baseline-refusal f8-workspace-isolation f8-integration)

### F9

- 328b664 factory: add parallel-safety annotations and a judge only where they are missing (test: syntax f9-parallel-safety)

### F10

- 2a0568c factory: fix-w<n> task keys are reserved like integration (test: x0-validation)

### Fix rounds

- 6cd29c4 factory: address review — missing role/kind default, one duplicate-key check, blocked propagates, key trimmed once, test-based check surface, delivery gated on a green integration (test: x0-validation, f3-scheduler, f8-integration, f8-baseline-refusal, f8-workspace-isolation)
- 1276b8e factory: address Opus review — leading-glob touches overlap everything; boundary rule tested; idempotent retry; fix task carries fetches; tree guard on the harness repo; cache-safe check surface; reviewer role table (test: f9-parallel-safety, f2-implementer-retry, f2-tree-guard, f8-integration, x0-validation)
- 2199e08 factory: address Opus round 2 — leading-glob touches overlap parallelSafe peers; key regex before rm -rf; fatal: anywhere; reviewer model id (test: f9-parallel-safety x0-validation f2-tree-guard f2-implementer-retry)
- 02162b2 factory: judge-supplied leading globs overlap everything; keys may not be ., .. or integration; docs carry the cache prefix and the key rules (test: f9-parallel-safety x0-validation)

### Docs

- c4518bc docs: README and AGENTS.md describe the factory as built — args.tasks contract, role→model ids, check surface, workspaces, discipline (test: syntax x0-validation f3-scheduler f8-integration f9-parallel-safety)
