# Night plan — 2026-09-05 (after switch #13, generation 38)

Operator: "All systems green. Sweep the conversation … find dropped topics/goals
then create a plan for the rest of the night." No switch is needed for any item
below. Everything runs through the gates: red first, Opus review, one bounded fix
round, then re-plan.

## Runs tonight

- **M1 — media flake: Krea2-capable ComfyUI pin** (repo `~/flakes/media`; seat
  driver, Opus gate). Bump the ComfyUI pin from 0.22.3 to 0.34.3 (the release the
  operator generates with from `~/comfyui-krea2`), keep the torch-bin overrides,
  add `text_encoders/qwen3vl_4b_bf16.safetensors` and `vae/qwen_image_vae.safetensors`
  to the manifest with the hashes read from their HF LFS pointers (the operator's
  copies are under `~/comfyui/models`), make `/object_info` list a `krea2`
  CLIPLoader type in a smoke test, run all 11 checks. Acceptance: the flake's
  `packages.comfyui` serves `~/comfyui` on 127.0.0.1:8188 with Krea2 types; then
  the throwaway venv can be retired (operator).
- **M2 — reasoning effort measured** (this repo; seat driver). One XS docs task
  run twice, `OPENROUTER_REASONING_EFFORT=off` and `=medium`: tokens in/out/
  reasoning, wall clock, Opus verdict. Closes N14's dated debt on the board.
- **S15–S19 — nixos-skill round 3** (workflow, Sonnet implements, Opus gates):
  S15 refresh.md prose gated (doctest or citation for every claim); S16 S8's
  wiring gate cannot be satisfied by a comment; S17 runner-unit live-nix proofs
  run in CI or skip with a named reason and a host-side runner; S19 auto-propose
  implemented per S13's spec (manifest += rename.nix + release notes; fail loud on
  a missing upstream path; the proposal lands as a diff, never live). S12's
  commit-metadata conflict waits for the operator.
- **a10 tidy wave** (this repo; seat driver, Opus gate): T1 helm-control-eval
  asserts the rendered `WORKSPACES_JSON_FILE` is a `/nix/store/` path (H2b M1d);
  T2 two-sided test for `factory-ws`'s repo check (N17 nit). **F11** (dsh-harness):
  trailer drift documented in README and the machine-set trailer asserted by a
  test for every commit the factory makes.
- **End of night:** START HERE rewritten as one fresh-session handoff; memory
  consolidation; concept doc `docs/concepts/2026-09-05a-headless-seat-driver.md`.

## Operator, tomorrow

O4 framing test; the OpenRouter activity export (D5) dropped at
`~/strategy/ledger/openrouter-activity.csv` so N16's parser meets a real file;
the S12 decision; restore `xhigh` in the seat or keep medium; brainstorms for
the interpreter model and Helm Home sub-projects 2 and 3.
