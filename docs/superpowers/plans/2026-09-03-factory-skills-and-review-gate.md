# Dark factory — skill injection by role and a review gate that cannot be skipped — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Executor: `tools/factory/dark-factory.js` in this repo (host `core`, build-only).

**Goal:** `tools/factory/dark-factory.js` can hand each role the right file of the `nixos` skill (spec `docs/superpowers/specs/2026-09-03-nixos-skill-design.md` §10), and a review agent that errors can never leave a task recorded as approved (defect found 2026-09-03: four Opus reviews died with API 529 and the tasks were logged "approved" with `review = null`).

**Architecture:** the prompt builders stay inside the one Workflow script (the sandbox cannot import modules), so the test loads the script's text with stub globals and asserts on the prompts actually rendered; no behaviour of the factory changes except the two specified.

**Tech Stack:** JavaScript (Workflow script sandbox: no Node APIs, no `Date.now`, top-level `return`), Node 22 in the devShell for the test and `node --check`, Nix `runCommand` check.

**Spec:** `docs/superpowers/specs/2026-09-03-nixos-skill-design.md` §10; `docs/decisions/2026-09-02-factory-model-policy.md`.

## Global Constraints
- Build-only; never sudo/nixos-rebuild/systemctl start/stop. Do not launch the factory from inside the factory.
- Keep every existing prompt text byte-identical except for the appended skill lines when `args.skills` is set (resume caches key on prompt text).
- Commit subject `factory: … (test: factory-unit, lint)`; through the devShell; `git add` before `nix build`.

---

### Task 1: skills by role, and errored reviews are "unreviewed"

**Files:**
- Modify: `tools/factory/dark-factory.js`
- Create: `tests/factory/render.test.mjs`, `tests/factory/fixtures/args-skills.json`
- Modify: `flake.nix` (`checks.factory-unit`: `runCommand` with `pkgs.nodejs` running the test against the script; `lint` already has `node --check`), `githooks/pre-commit` (run the test)

**Interfaces (Produces):**
- `args.skills` — `{ nixos: "/abs/path/to/skills/nixos" }` (optional). `tasks[].skillRefs` — `["systemd-units", "vm-tests"]` (optional; reference stems).
- Injected text (exact, appended after the task spec of each prompt; `<P>` = `args.skills.nixos`):
  - implementer / fix agent: `SKILL: read <P>/SKILL.md first, then these references: <P>/references/<stem>.md, … Name the files you read in your report.` — when `skillRefs` is absent the second sentence is `then pick from the router's task → files table using this task's title and spec text.`
  - code reviewer (Opus): `SKILL: read <P>/references/review-checklist.md and <P>/references/gotchas.md; apply the checklist in order.`
  - docs reviewer: `SKILL: read <P>/references/nix-cli.md and <P>/references/activation-and-switch.md before checking any command.`
  - verifier: `SKILL: follow <P>/references/verify.md.`
  - When `args.skills` is absent nothing is appended (prompts unchanged).
- Review errors: `spawn()` returning `null` for a review → `log("<key>: review agent returned no result — retrying once")`, one retry with the same prompt; if still `null`, the task's `status` is `"unreviewed"`, `review` is `null`, and the run's final `log` and return list it under `unreviewed: [keys]`. `"unreviewed"` is never counted as approved by the summary. (Keep the existing `reviewNote` handling for `approved=false` without blocking findings.)

- [ ] **Step 1 (red): the test.** `tests/factory/render.test.mjs`: reads `tools/factory/dark-factory.js`, strips the leading `export const meta = { … }` literal (from `export const meta` to the first line that is exactly `}`), wraps the rest in `(async () => { … })()` via `new Function` with stub globals injected as parameters: `agent` (records every prompt + opts, returns canned results: baseline `{head:"abc", lint_green:true}`, implementer `{commit:"abc", blocked:false, deviations:""}`, review `{approved:true, findings:[]}` — and, in a second scenario, `null` for every review), `parallel` (runs thunks), `pipeline`, `phase`, `log` (records lines), `workflow`, `budget` (`{ total: null, spent: () => 0, remaining: () => Infinity }`), `args` from the fixture (two tasks: one with `skillRefs`, one without; `skills.nixos = "/skills/nixos"`). Assertions: implementer prompt for task A contains `/skills/nixos/SKILL.md` and `/skills/nixos/references/systemd-units.md`; task B's contains `pick from the router`; the code-review prompt contains `review-checklist.md` and `gotchas.md`; the docs-review prompt contains `nix-cli.md`; the verifier prompt contains `verify.md`; with `skills` absent, no prompt contains `SKILL:`; scenario 2: every task status is `"unreviewed"`, the log contains `retrying once`, and the return value's `unreviewed` lists both keys. Run `nix develop -c node tests/factory/render.test.mjs` → red (fails on the missing behaviour).
- [ ] **Step 2: implement** in `dark-factory.js`: a `skillLines(role, task)` helper returning the exact strings above; append to the four prompt sites; the review retry and `"unreviewed"` status; extend the final `log` and return. Test green; `node --check` green.
- [ ] **Step 3: check + hook.** `checks.factory-unit = pkgs.runCommand "factory-unit" { nativeBuildInputs = [ pkgs.nodejs ]; } "cd ${./.} && node tests/factory/render.test.mjs && touch $out"` (copy the two files into the build dir rather than `cd`-ing into the store if needed); pre-commit runs the same test. `nix build .#checks.x86_64-linux.factory-unit -L --no-link` green; lint gate green.
- [ ] **Step 4: commit** `factory: skills and skillRefs injection by role; a review that errors is retried once and then recorded "unreviewed", never approved; prompt-rendering test (test: factory-unit, lint)`.

## Self-review
Spec §10 role entries → the four injected lines; `skillRefs` optional → router fallback sentence; defect → retry + `"unreviewed"`; tests load the real script text so a drifted prompt site fails the test. Names: `skillLines`, `factory-unit`, `render.test.mjs`.
