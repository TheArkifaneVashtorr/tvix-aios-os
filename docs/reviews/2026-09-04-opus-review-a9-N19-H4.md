# Opus gate — a9 / N19 + H4

**N19 — REQUEST CHANGES (bug fixed, premise false).**
**H4 — APPROVE (two doc nits).**

## Mutation table

| # | Task | Change | Caught | Evidence |
|---|---|---|---|---|
| R1 | N19 | revert `dsh-openrouter.sh`, keep tests | yes | `unit-tests> not ok 57`; instrumented run prints `dsh: UNSUPPORTED_REASONING_EFFORT … "xhigh"` — the field bug verbatim |
| M1 | N19 | drop `xhigh: high` (dsh-openrouter.sh:336) | yes | bats: `not ok 1 … status -eq 0` |
| M2 | N19 | `xhigh: medium` | yes | `AssertionError: {'effort': 'medium'}` (wire body) |
| R2 | H4 | revert `render.py` | yes | helm-unit `1 failed, 116 passed` — `test_empty_workspaces_hides_the_workspaces_section` |
| M3 | H4 | `if workspaces:` → `if True:` (render.py:208) | yes | same test fails |
| R3 | H4 | restore four workspaces in `hosts/core/helm.nix` | yes | `error: host-core: helm control.workspaces must pin the empty map` |
| M4 | H4 | restore **one** workspace | yes | same assertion |

## N19

- Test is genuine: `tests/mocks/openai-fake.py:112` stores the parsed JSON body; `tests/unit/70-dsh-openrouter.bats:288` asserts `body["reasoning"]["effort"] == "high"`. M2 proves it.
- **Blocker.** Commit body cites `openrouter.ai/docs/features/reasoning-tokens` — 404. The live page (`/docs/use-cases/reasoning-tokens`) lists effort values `max, xhigh, high, medium, low, minimal, none`. The vendored catalog agrees: `pi-ai/dist/providers/data/openrouter.json` maps this model `xhigh → "xhigh"` (and `low`/`medium` → `null`). So "OpenRouter accepts only low/medium/high; xhigh is not accepted" is wrong, it silently downgrades a deliberate pick, and it is written into `docs/runbooks/lanes.md:308-315` as operator fact. Suggest `xhigh: xhigh`, assert `"xhigh"`, fix the URL, correct the runbook, and date the debt that the fake upstream verifies nothing about real acceptance.
- Verified sound: picker levels are exactly the declared five (`models.js:548` drops levels whose map value is `null`; `dsh-llm-pi-ai/lib/index.js:557` nulls undeclared ones), so `minimal`/`max` are unreachable. `OPENROUTER_REASONING_EFFORT=xhigh` reaches the wire as `high` (probed) but is untested.

## H4

- Correct and complete. Capability intact: `tests/integration/helm-control-vm.nix:59` still declares `workspaces.demo`.
- Nit: `docs/runbooks/helm-v1.md:196` says "Three steps print SKIP"; four now fire (helm-v1.sh:462, 500, 580, 610).
- Nit: the operator question in `docs/OPERATIONS.md` (A/B/C) is answered C with no `docs/decisions` entry.

## Both

Merge clean in either order (no flake.nix conflict — N19 branches off `main~1`). Merged tree: `lint`, `unit`, `helm-unit`, `host-core`, `helm-control-eval` all green. Trailers and subjects match convention.
