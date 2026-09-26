# Fix wave a3 — Opus re-gate findings on wave 1 (supplementary plan)

## Global Constraints

- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown, no reading `/var/lib/secrets/*`. The operator switches (§C).
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null` a gated command.
- Each task's spec names its own commit subject; use that subject's prefix, not `args.prefix`, when they differ. Trailer exactly `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- TDD: the failing check first, shown red, then green. A load-bearing test counts only once it has been shown to fail.
- Claude agents **never** write inside `~/flakes/dsh-harness`. Claude agents may write in `~/flakes/nixos-skill` (S1 only), in its own factory run.
- Every measurement names what it stands in for and the gap (`docs/decisions/2026-09-03-test-based-reality-amendments.md`).
- **One writer per tree.** After N10, an implementer works only in the isolated worktree it was started in, on exactly one branch named by its task key; it never merges, never moves another branch, and never writes in `${REPO}`'s own checkout. A task's `touches` list is a contract: if the work turns out to need a file outside it, stop and report a deviation rather than write it — another agent may hold that file in the same wave.

## Assumptions (stated, not verified here)

1. The seat is relaunched after N1/N7 land — `OPENROUTER_MODELS`, `XDG_CACHE_HOME` and the hook config are all consumed at launch (H7's refutation), so nothing in N1/N7 affects a running session. Operator action O9.
2. `dsh` stays pinned at `0.1.2-rc.1`; the hooks-bridge package name, the `- insert:` patch shape and the `hookSpecificOutput.permissionDecision` contract were read from that pin (see N7) and must be re-read if the pin moves.
3. Whether OpenRouter honours a `provider` block on `/api/v1/messages` is **unknown** (O3). N3 therefore ships the *mechanism* and leaves the `/api/v1/messages` prefix switched off in `hosts/core` behind an option, defaulting false.
4. The dsh transcripts the ledger reads are the durable ones under `$DSH_HOME/sessions/<slug>/<uuid>/session.jsonl.zstd` — the review's flat `transcripts/*.jsonl` corpus was a scratch export (H10 vote 3 corrected the glob).
5. The dsh factory's `args.tasks` contract is `{key,title,role,kind,spec,dependsOn}` with `role ∈ {deepseekPro, deepseekFlash, kimi, glm, glmFlash}` and `kind ∈ {backend, frontend, structured, routine}` (`factory/dark-factory.js:40-62`). F9 adds `touches` and `parallelSafe`; the §B list below already carries them, so **X0's entry validation must ignore unknown extra fields rather than reject them**, or §B cannot be dispatched.
6. Parallel implementers are a decision, not a preference: `docs/decisions/2026-09-04-parallel-agent-workflows.md` (operator, 2026-09-04) overrules this plan's earlier "keep implementers sequential" call. N10 lands it here; F3/F8/F9 land it on the dsh side.

---

## Tasks (from docs/reviews/2026-09-04-opus-regate-wave1.md §5; findings in §2 there — read both)

### W2-N1a (fix, S, DeepSeek impl / Opus review) — seat cache block — reachable ownership guard, test-scoped cache root

**key**: `W2-N1a`
**title**: seat cache block — reachable ownership guard, test-scoped cache root
**files**: `pkgs/dsh-openrouter/dsh-openrouter.sh`, `tests/unit/70-dsh-openrouter.bats`
**red-first test**: two cases, both failing today. (1) `XDG_CACHE_HOME=<a dir you do not own> run dsh-openrouter --dump-config` → assert `status -eq 5` and output contains `not owned by you` (today: status 1, `chmod: … Operation not permitted`). (2) with the default cache root pointed at `$TMPHOME` via a new `DSH_CACHE_ROOT` knob, assert the directory did **not** exist before the run and does after, 700, owned by the caller (today: no such knob; the case reads the shared `/tmp` path and passes on inherited state).
**also**: reorder to `mkdir -p --` → `stat`/`die 5` → `chmod 700 --` (not `mkdir -p -m 700`: SC2174, and it will not correct an existing dir's mode); delete `rm -rf "/tmp/dsh-openrouter-cache-$(id -u)"` from `teardown()`; keep `/tmp` as the seat's default so the warm cache is not fragmented.
**acceptance checks**: `unit`, `host-core`, `lint`

### W2-N1b (fix, S, DeepSeek impl / Opus review) — payload warning — deployed-symlink case, real stderr assertion, declared `findutils`, honest `--help`

**key**: `W2-N1b`
**title**: payload warning — deployed-symlink case, real stderr assertion, declared `findutils`, honest `--help`
**files**: `tests/unit/70-dsh-openrouter.bats`, `pkgs/dsh-openrouter/dsh-openrouter.sh`, `pkgs/dsh-openrouter/default.nix`
**red-first test**: build the production shape — a payload dir with a file and a non-empty `AGENTS.md` **outside** `$DSH_HOME`, both `ln -s`'d in — run `--dump-config` and assert the output names neither `$dsh_home/skills` nor `$dsh_home/AGENTS.md`. Show it red by mutating `find -H` → `find` (or by replacing `find` with a `shopt -s nullglob dotglob` glob probe and dropping the dependency). Second case: `run --separate-stderr`, assert the warning is on `$stderr` and absent from `$output` (red today with `>&2` removed).
**also**: add `findutils` to `runtimeInputs` if `find` is kept; fix the `--help` `OPENROUTER_MODELS` default text and assert it names the same list the default composes; re-point the role→model comment at `~/flakes/dsh-harness/README.md`.
**acceptance checks**: `unit`, `lint`

### W2-N3 (fix, S, DeepSeek impl / Opus review) — prove the broker enforces the ZDR patch — Nix→policy wire format under test

**key**: `W2-N3`
**title**: prove the broker enforces the ZDR patch — Nix→policy wire format under test
**files**: `tests/integration/lane-vm.nix`, `nixosModules/egressBroker.nix`, `flake.nix`
**red-first test**: from inside `/run/netns/egress-openrouter`, `curl --cacert <broker ca-bundle>` a body with **no** `provider` key to `https://openrouter.test/api/v1/chat/completions`; assert the fake upstream's log shows `"zdr": true` for that request, and that a companion request to an unlisted path (`/api/v1/models`) arrives unpatched. Show red by emitting `body_patch = { }` from `egressBroker.nix` (today: `lane-vm` stays green, ~14 s). Cheap complement, no IFD: expose the generated policy attrset as an internal read-only option and assert `body_patch.<host>.path_prefixes == [ "/api/v1/chat/completions" ]` and `inject.<host>.paths == [ "/" ]` beside `flake.nix:673`.
**also (fold in if cheap)**: make the streamed-body pytest a POST with an `inject` spec and assert `Authorization` is absent from the killed flow.
**acceptance checks**: `lane-vm`, `lane-eval`, `host-core`, `addon`, `lint`

### W2-N6a (fix, S, DeepSeek impl / Opus review) — `rollup --week` gets a real window

**key**: `W2-N6a`
**title**: `rollup --week` gets a real window
**files**: `tools/ledger/factory.py`, `tests/ledger/test_factory.py`, `tools/ledger/schema.md`
**red-first test**: a ledger with one in-window and one out-of-window dsh session (and one out-of-window factory run); assert the out-of-window records are excluded from every lane, role and fix-round total, and that the first output line names the window bounds. Red today: the 2024 session is counted in full and no window line is printed.
**also**: `--since`/`--until`, default trailing 7 days UTC; join agents to their run by `run_id` for windowing (agents carry no timestamp; run `started` is ISO-8601, dsh `started` is epoch ms).
**acceptance checks**: `ledger-unit`, `lint`

### W2-N6b (fix, S, DeepSeek impl / Opus review) — `rollup --costs` stops printing confident wrong dollars

**key**: `W2-N6b`
**title**: `rollup --costs` stops printing confident wrong dollars
**files**: `tools/ledger/factory.py`, `tests/ledger/test_factory.py`, `tools/ledger/schema.md`
**red-first test**: (1) a price CSV covering one of two sessions → assert the cost line names the unpriced count and the missing `(date, model)` key, and does **not** print a bare total (today: a silently understated `cost: 0.000798 USD`). (2) an activity-export-shaped CSV (`date,model,tokens,cost`) → assert a named error listing the columns found (today: unhandled `KeyError: 'in_per_1m'`). Use exact-line assertions, not substrings — the current test would pass a suffix change.
**also**: either consume the real O2 activity export (sum its `cost` column, joined on date+model) or rename the argument and the `schema.md` heading to `<price-table.csv>` and reconcile it with `schema.md:20-21`.
**acceptance checks**: `ledger-unit`, `lint`

### W2-N10a (fix, S, DeepSeek impl / Opus review) — factory integration/delivery gate honours verdicts and accounts for every task

**key**: `W2-N10a`
**title**: factory integration/delivery gate honours verdicts and accounts for every task
**files**: `tools/factory/dark-factory.js`, `tests/factory/render.test.mjs`
**red-first test**: two scenarios, both green today. (1) `review:A` returns a blocker every round while `integrate:w1` and `verify` stay green → assert `delivered === false`, no `deliver` spawn, and A absent from the `integrate:w1` merge list, with a log line naming A as withheld. (2) `parallel` stubbed as `thunks.map((t) => t().catch(() => null))` with `impl:B` throwing → assert `tasks[]` still has four entries, B at `status: 'unreported'`, and `delivered === false`.
**also**: filter `integrateWave`'s merge list by `statusOf === 'approved'`; add `results.length === A.tasks.length` to `allOk`; make the not-delivered line name the non-approved keys instead of printing a bare `git merge --ff-only`; skip Verify when nothing integrated and report `verify=skipped`.
**acceptance checks**: `factory-unit`, `lint`

### W2-N10b (fix, S, DeepSeek impl / Opus review) — orchestration rules stop forbidding the conflict resolution they demand

**key**: `W2-N10b`
**title**: orchestration rules stop forbidding the conflict resolution they demand
**files**: `tools/factory/dark-factory.js`, `tests/factory/render.test.mjs`
**red-first test**: assert positively that the `integfix:w1` prompt does not contain a clause forbidding hand-edits to tracked files, and that the `forbidden` list at `render.test.mjs:517` includes all three implementer-only clauses. Red today (and a maximally contradictory clause currently passes the suite untouched).
**also**: reword the `RULES_ORCH` closing clause to permit exactly the conflict resolution `:379` names and nothing else; fix the "byte-identical" comment and restore `extraRules` to last; add a branch-name regex to `validateGraph` for `t.key`.
**acceptance checks**: `factory-unit`, `lint`

### N7b (fix, S, DeepSeek impl / Opus review) — ruff covers the seat's hook guard

**files**: `flake.nix` (the `lint` check's ruff invocation), `githooks/pre-commit`
**red-first test**: add a temporary ruff violation (e.g. an unused import) to `pkgs/dsh-openrouter/hook-guard.py`, run `nix build .#checks.x86_64-linux.lint -L --no-link` and `nix develop -c githooks/pre-commit`; both must stay GREEN today (that is the defect: the script is not covered). Then add `pkgs/dsh-openrouter` to both ruff target lists (keep the two lists identical), show both go RED on the violation, remove the violation, green.
**acceptance checks**: `lint`, `unit`
**commit subject**: `lint: ruff covers pkgs/dsh-openrouter (test: lint, unit)`
