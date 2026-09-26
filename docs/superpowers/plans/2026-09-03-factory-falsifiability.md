# Dark factory — falsifiability in the review and verify prompts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Executor: `tools/factory/dark-factory.js` in this repo (host `core`, build-only).

**Goal:** the factory enforces decision `docs/decisions/2026-09-03-test-based-reality-amendments.md`: the code-review gate must demonstrate that each load-bearing test fails under a mutation, reports tests that cannot fail as `vacuous-test` (major), and the verify step reports the count.

**Spec:** the decision; `tools/factory/dark-factory.js` review prompt (the "tests are real" sentence) and verify prompt; `tests/factory/render.test.mjs` byte-exact assertions.

### Task 1 (code)
- [ ] Review prompt (code kind) gains, verbatim: `For every load-bearing test in the diff, MUTATE the code under test (revert one line, flip one condition) and re-run the test: it must go red. A test that stays green is a finding of severity major, class "vacuous-test", naming the test and the mutation. Report the mutations you ran.` Findings schema gains an optional `class` string. Verify prompt gains: `Count review findings of class "vacuous-test" across this run and report vacuous_tests: <n>.` The return value carries `vacuous_tests`. `render.test.mjs` asserts the exact sentences and the field. Commit `factory: review gate mutates load-bearing tests; vacuous-test findings counted per run (test: factory-unit, lint)`.
