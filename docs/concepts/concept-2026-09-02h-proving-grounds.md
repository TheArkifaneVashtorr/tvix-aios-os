# Concept 2026-09-02h — proving grounds (seeded capability experiments)

**Class:** experiment harness atop workspaces. **Status:** proposed (operator-originated).

**Origin (operator, 2026-09-02):** "centralized controllable isolation of Claude
and its files will allow us to test dark factory setups more deterministically —
different models start from the same point to achieve the same goal based on a
spec sheet and gather valuable data in terms of capabilities."

**Idea:** sealed workspaces make experiment seeds content-addressed: a run
provably starts from a byte-identical workspace (`content_sha256` is the fixed
point). Harness: `experiment.toml` declares {seed basket hash, spec document,
executable acceptance tests, matrix: model × effort × settings × harness,
N trials per cell}. Runner per cell: clone seed → fresh CLAUDE_CONFIG_DIR (+
CLAUDE_CODE_PROJECT_DIR_NAME) → headless run against the spec → score = tests
passed, tokens, wall-clock, diff surface. Report distributions, never single
runs — controlled initial conditions ≠ determinism.

**Two payoffs beyond benchmarking:**
1. Harness × model on identical seeds — the brief's multi-harness environment
   becomes an instrument.
2. Router policy tuning by measurement (Phase 5): local models (DeepSeek-32B,
   Hermes-14B) vs frontier on identical seeds → the classification table's
   local-vs-frontier boundary gets evidence instead of intuition.

**Dependencies:** workspaces mini-phase (`basket seal`, launcher). Results
surface as a Helm matrix tile. **Earliest landing:** right after workspaces;
the runner is one factory task.

## Queued experiments (append-only)

- **2026-09-03 — code graph vs none (operator question).** Prediction
  (orchestrator): a precise, on-demand structural tool (language-server or
  tree-sitter grade "who calls this / where is it defined / what breaks if I
  change it") gives a small gain on cross-file refactors and none on
  NixOS-shaped work, where the exact graph already exists as `nix why-depends`,
  `path-info`, `diff-closures` and option evaluation; embedding RAG over code
  gives no gain and costs tokens (chunks cut functions, hits are look-alikes,
  indexes go stale). Design: identical seeds, arms = {none, LSP/tree-sitter
  tool on demand, embedding RAG pre-injected}, tasks = one cross-file refactor
  and one NixOS module task, N trials, score = tests passed, tokens, wall
  clock. Lands after the NixOS-skill eval harness exists (it is the same
  runner with a different arm).
