# Defects found while planning (2026-09-27, tree 4a7374ca) — not filed with tools/debug/bug-note

The drafting prompt says a defect found while planning is noted with
`BUG_NOTE_REPORTER=plan/<phase> tools/debug/bug-note "<symptom>" --evidence <path>`, which
appends to `~/factory/debug/inbox.jsonl`. The user request for this run forbids creating or
changing anything outside the repository except `runs/y/` and this scratch directory, so the
lines are recorded here instead, in the shape the tool would have appended. None of them is a
task of the plan unless the spec names it (D8 explains the one that the spec's own VM test
forces into SD5).

1. `tools/debug/bug-note` does not exist in this tree (`ls tools/debug` → no such directory), and
   the prompt's format reference `docs/superpowers/plans/2026-09-11-defects.md` (the DF8d
   commit-body recipe, DF13, HM7c) is absent (`ls docs/superpowers/plans` — 38 files, none dated
   2026-09-11; `grep -rn 'DF8d\|DF13\|HM7c' docs tools .claude` matches only the four workflow
   scripts' prompt text). The plan states the commit-body recipe in its own words (Global
   Constraints). Evidence: /tmp/draft-scratch/queries.log (the `ls` and `grep` lines).
   `{"reporter":"plan/draft","symptom":"draft prompt cites docs/superpowers/plans/2026-09-11-defects.md and tools/debug/bug-note; neither exists in the tree","evidence":"/tmp/draft-scratch/queries.log"}`

2. Latent production defect in the seat unit: `pkgs/dsh-openrouter/dsh-openrouter.sh` runs
   `mkdir -p -- "$XDG_CACHE_HOME"` with `XDG_CACHE_HOME=${XDG_CACHE_HOME:-/tmp/dsh-openrouter-cache-$(id -u)}`
   under `writeShellApplication`'s errexit, while `nixosModules/seatLane.nix` renders
   `ProtectSystem = "strict"` with `/tmp` absent from `ReadWritePaths`; `tests/integration/seat-vm.nix`
   admits `/tmp` for its fixtures ("ProtectSystem=strict makes /tmp read-only for the seat unit"),
   so the VM never exercises the production sandbox. Predicted: every real `seat@` job on core dies
   at the cache mkdir. Unmeasured on core (no real job has run through `seat@` yet, board 2026-09-06).
   The spec's own seat-vm bullet ("a drive job answers on 10.100.4.2:<port>") cannot be honest
   without the production sandbox, so SD5 sets `XDG_CACHE_HOME=/var/lib/seat/cache` and drops the
   `/tmp` admission (Decision D8).
   `{"reporter":"plan/draft","symptom":"seat@ unit: wrapper cache dir under /tmp is unwritable under ProtectSystem=strict without /tmp in ReadWritePaths; the VM masks it by admitting /tmp","evidence":"/tmp/draft-scratch/queries.log"}`

3. Spec wrong fact (already on the board): the seat-driver spec's Risks say the integrator refuses
   out-of-`touches` commits; `factory-integrate` refuses only `docs/OPERATIONS.md changed outside the
   queue block` (`grep -n REFUSED tools/factory/seat/factory-integrate`). Decision D11.

4. Spec self-contradiction: the ladder table's `implement/docs/any` (Flash off → Pro medium) and
   `review/any/any` (Pro medium → opus high) rungs change two variables, against the spec's own
   one-variable rule. Decision D1 (a route change is one variable; the docs ladder becomes three rungs).

5. Telemetry plan T2 names the task's kind `"kind"` in the `task-result` fields, which collides with
   the envelope's `kind`; the fixture store on core carries `task_kind`
   (`describe select * from read_json_auto('evidence/derived/tasks.jsonl')`). Decision D10; SD8 greps
   the landed `streams.py` first.

6. `route.py check` accepts an unknown row key silently (`rung = 2` on a fixture → rc=0, and `lookup`
   picks the row as most specific) while `factory_route` refuses any unknown key with exit 3 — the
   two implementations disagree on a table with a new key today (SD1's red).

7. `githooks/pre-commit`'s `ruff check`/`ruff format --check` lists lack `pkgs/seat tests/seat`
   while `flake.nix`'s `lint` includes them (`grep -n ruff githooks/pre-commit` vs the lint block):
   the hook and the check disagree on the Python they lint. Not this plan's; noted.
