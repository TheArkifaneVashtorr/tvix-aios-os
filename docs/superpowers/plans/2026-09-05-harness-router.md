# The dsh harness archives its planning factory and routes through the table (plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox syntax. The seat driver reads the `### KEY (kind, size) — title` sections below. **These tasks run in `~/flakes/dsh-harness`** (`factory-wave hr1 ~/flakes/dsh-harness "H1 H2"`), a repo without a flake: its check surface is `nix develop /home/dalhaka/nixos-agent-env -c node --test <tests>` and its own `githooks/pre-commit`.

**Goal:** decision `docs/decisions/2026-09-05-dsh-harness-factory-parked.md` (addendum): the three-model planning factory is archived in place, and every place the harness tells an agent how to choose a sub-agent's model points at `docs/ledger/routing.toml` in `~/nixos-agent-env` through the pure-bash lookup, OpenRouter route only.

## Global Constraints

- Build-only; never `sudo`, `nixos-rebuild`, `systemctl`. Work only in the workspace `factory-ws` gives you (a clone of `~/flakes/dsh-harness`). Commits via `nix develop /home/dalhaka/nixos-agent-env -c git commit -F <msgfile>` (that devShell has the tools this repo's hooks need) with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer; the harness's `githooks/pre-commit` runs on commit — read it first.
- Read-only: `~/nixos-agent-env` (the table and `tools/factory/seat/factory-lib.sh`); never write there.

## Tasks

### H1 (code, S) — archive the planning factory in place

**dependsOn:** none
**repo:** dsh-harness

**Files (in ~/flakes/dsh-harness):**
- Move: `factory/dark-factory.js` → `archive/2026-09-05-planning-factory/dark-factory.js`; `factory/tests/*.test.mjs` → `archive/2026-09-05-planning-factory/tests/` (git mv; fix the tests' relative imports of the script so `nix develop /home/dalhaka/nixos-agent-env -c node --test archive/2026-09-05-planning-factory/tests/*.test.mjs` still passes)
- Create: `archive/2026-09-05-planning-factory/README.md` (what this was, why archived — the decision path above — and the command that still runs its tests)
- Modify: `README.md` (the "Factory (multi-model dark factory)" section becomes a short "Archived: planning factory" pointer; the role→model table is removed; the check-surface sentence points at the archive tests or is dropped if the check surface is now empty — say which), `CHANGELOG.md` (one dated line), `githooks/pre-commit` / `pre-push` only if they reference `factory/tests` (update the path)

- [ ] **Step 1: Red** — before moving anything, run the repo's check surface as the README states it and record the pass; after the `git mv`, the OLD command must fail (`factory/tests` gone) and the NEW command under `archive/…` must pass — both recorded.
- [ ] **Step 2: Move, fix imports, write the archive README, update README/CHANGELOG/hooks.** `grep -rn 'factory/dark-factory\|factory/tests' . --exclude-dir=.git --exclude-dir=archive` must print nothing afterwards except CHANGELOG history lines.
- [ ] **Step 3: Green** — the archive tests pass; the repo's own pre-commit passes; `git status` clean after commit.
- [ ] **Step 4: Commit** — subject below; body: the decision path and the archive test command.

**touches:** factory/dark-factory.js, factory/tests, archive/2026-09-05-planning-factory, README.md, CHANGELOG.md, githooks/pre-commit, githooks/pre-push
**acceptance:** node-test
**commit subject:** `factory: the three-model planning factory is archived under archive/2026-09-05-planning-factory (decision 2026-09-05, nixos-agent-env) (test: node-test)`

### H2 (docs, S) — the harness's agents choose sub-agent models through the routing table

**dependsOn:** H1
**repo:** dsh-harness

**Files (in ~/flakes/dsh-harness):** `skills/using-superpowers/references/dsh-tools.md` ("Subagents" section), `skills/subagent-driven-development/SKILL.md` ("Model Selection" section), `AGENTS.md` (the role-name paragraph and the `Generated-By` model wording), `README.md` (a "Model routing" section)

**Interfaces:** the text an agent follows, verbatim in each place with wording adapted to the section:

```markdown
Choose a sub-agent's model from the routing table, never from memory:
`. ~/nixos-agent-env/tools/factory/seat/factory-lib.sh && factory_route --route openrouter <role> <kind> <size>`
prints `MODEL EFFORT`. Roles: implement | review | verify | research | baseline | audit; kind: code | docs;
size: XS | S | M | L (from the task's `### KEY (kind, size)` heading; `any` when unknown). Pass the model as the
sub-agent's `model` override and the effort as `OPENROUTER_REASONING_EFFORT`. Rows with `route = "claude"` are not
reachable from this seat and are never requested. `FACTORY_ROUTING_TABLE` overrides the table path. Kimi K3 and
GLM 5.3 are picker extras with no row yet; do not select them by hand.
```

- [ ] **Step 1** Replace every hard-coded model id or role-map reference in the four files with the block above (adapted); `grep -rn 'deepseek/deepseek\|moonshotai/\|z-ai/\|deepseekPro\|glmFlash' AGENTS.md README.md skills/ ` must print nothing (the archive directory is excluded from this rule).
- [ ] **Step 2** Verify the command works from this repo's checkout on the host: `bash -c '. ~/nixos-agent-env/tools/factory/seat/factory-lib.sh && factory_route --route openrouter implement docs XS && factory_route --route openrouter review code S'` → `deepseek/deepseek-v4-flash off` and `deepseek/deepseek-v4-pro-0813 medium`; paste into the commit body.
- [ ] **Step 3** The repo's pre-commit passes; commit.

**touches:** skills/using-superpowers/references/dsh-tools.md, skills/subagent-driven-development/SKILL.md, AGENTS.md, README.md
**acceptance:** pre-commit
**commit subject:** `docs: sub-agent models come from nixos-agent-env's routing table (factory_route --route openrouter), no model ids in prose (test: pre-commit)`

## After the first gate (2026-09-05 evening)

H1 APPROVED (touches corrected: it also edited `AGENTS.md` and `skills/using-superpowers/references/dsh-tools.md`, forced by its own grep gate). H2 REJECTED on text: (1) `FACTORY_ROUTING_TABLE` did not exist — RT4 in `2026-09-05-seat-routing.md` implements it in `~/nixos-agent-env`; (2) the rewritten "Model Selection" escalated by `size`, which the table barely uses, and reintroduced free choice; (3) two "most capable available model" instructions survived (`SKILL.md:462`, `:572`). The harness has no `githooks/`, so "pre-commit" is not a check there: the acceptance is the grep gate plus the archive test suite.

### H2b (docs, S) — H2 fix round: the block's promise is true, no size escalation, no stray free choice

**dependsOn:** none (H1 is on the harness's `main`; RT4 lands in nixos-agent-env before this is gated)
**repo:** dsh-harness

**Files (in ~/flakes/dsh-harness):** `skills/using-superpowers/references/dsh-tools.md`, `skills/subagent-driven-development/SKILL.md`, `AGENTS.md`, `README.md`

- [ ] **Step 1** Fresh workspace from the harness `main` (H1 present); `git fetch -q /home/dalhaka/factory/ws/hr1/H2 task/H2 && git cherry-pick -n FETCH_HEAD`; read the review in full.
- [ ] **Step 2** "Model Selection" in `SKILL.md`: replace the escalation-by-size bullets with the rule — role, kind and size are read off the task's `### KEY (kind, size)` heading (`any` when absent); the table decides; a fix round keeps the same row; a model change is a row change in `~/nixos-agent-env/docs/ledger/routing.toml` justified by a measurement, never a per-task choice. Replace the two surviving "most capable available model" instructions (around lines 462 and 572) with a reference to that rule. Keep the routing block; its `FACTORY_ROUTING_TABLE` sentence is now true (RT4).
- [ ] **Step 3** Gates: `grep -rn 'deepseek/deepseek\|moonshotai/\|z-ai/\|deepseekPro\|glmFlash\|most capable available model\|fast, cheap model' AGENTS.md README.md skills/` prints nothing; `nix develop /home/dalhaka/nixos-agent-env -c node --test archive/2026-09-05-planning-factory/tests/*.test.mjs` still 98 passing; the routed command from the block reproduces (paste into the commit body). One commit, subject byte-identical to H2's.

**touches:** skills/using-superpowers/references/dsh-tools.md, skills/subagent-driven-development/SKILL.md, AGENTS.md, README.md
**acceptance:** grep-gate, node-test
**commit subject:** `docs: sub-agent models come from nixos-agent-env's routing table (factory_route --route openrouter), no model ids in prose (test: pre-commit)`

### H2c (docs, XS) — the skill's prompt templates follow the same rule; the gate sees the whole tree

**dependsOn:** H2b (on the harness's `main`)

**repo:** dsh-harness

Gate for H2b (`docs/reviews/2026-09-05-opus-review-hr1-H2b.md`): APPROVED, with two majors outside H2b's files — `skills/subagent-driven-development/re-review-prompt.md:105` ("scoped re-reviews of small fix diffs take a cheap-to-mid tier", plus a dangling cross-reference) and `skills/subagent-driven-development/implementer-prompt.md:89` ("re-dispatch with a more capable model"), contradicting SKILL.md's rule; and the grep gate was too narrow to see them.

**Files (in ~/flakes/dsh-harness):** `skills/subagent-driven-development/re-review-prompt.md`, `skills/subagent-driven-development/implementer-prompt.md`, `skills/subagent-driven-development/SKILL.md` (line ~186's imperative "Use the least powerful model…" becomes the heading→table rule's opening sentence; the "Review tasks" bullet stops claiming `size` carries scaling), `README.md` ("Model routing": the gate command below)

- [ ] **Step 1** Replace the two template sentences with the rule (a fix round keeps the same row; escalation is a row change in the table, never a per-dispatch choice) and fix the dangling cross-reference. **Step 2** The gate, whole tree minus the archive: `grep -rn -i 'more capable\|most capable\|cheap-to-mid\|mid-tier\|least powerful\|fast, cheap model\|deepseek/deepseek\|moonshotai/\|z-ai/\|deepseekPro\|glmFlash' --exclude-dir=.git --exclude-dir=archive .` prints nothing; record red (before) and green (after). Archive suite still 98/98. One commit.

**touches:** skills/subagent-driven-development/re-review-prompt.md, skills/subagent-driven-development/implementer-prompt.md, skills/subagent-driven-development/SKILL.md, README.md
**acceptance:** grep-gate, node-test
**commit subject:** `docs: the skill's prompt templates follow the routing rule too; the model-choice gate covers the whole tree (test: grep-gate)`
