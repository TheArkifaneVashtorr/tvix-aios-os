# Wave a7 — loose ends after the fix round (supplementary plan, 2026-09-04)

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

## Tasks (all in ~/nixos-agent-env; red first; commit through `nix develop -c git commit -F <msgfile>`)

### N13 (code, S) — the broker denies /api/v1/messages on the openrouter instance (O3 resolved: fail closed)
Nothing uses the Anthropic-style messages path (the Claude-Code-through-OpenRouter kind was a dead end; the seat and the lane use chat completions). Replace the `patchMessagesPath = false` half-measure with a deny: in nixosModules/modelLane.nix (lane wiring) and pkgs/broker/policy.py, a request to `/api/v1/messages` on the openrouter instance is denied before credential injection with audit reason `path-not-permitted`; keep the chat prefix list as is. Red first: the lane VM test (tests/integration/lane-vm.nix) gains a probe that POSTs to /api/v1/messages through the broker and asserts a deny in the audit log and no upstream arrival; today it is allowed. Update the host-core assertion in flake.nix that pins the ZDR scope in the SAME commit (the Opus review of W2-N3 warned it goes red otherwise). Update docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md with a dated addendum and docs/runbooks/lanes.md.
**touches:** pkgs/broker/policy.py, tests/broker/test_policy.py, nixosModules/modelLane.nix, tests/integration/lane-vm.nix, flake.nix, docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md, docs/runbooks/lanes.md
**acceptance:** lane-vm, lane-eval, addon, host-core, lint
**commit subject:** `broker: /api/v1/messages is denied on the openrouter lane — fail closed, nothing consumes it (test: lane-vm, lane-eval, addon, host-core, lint)`

### N14 (code, S) — the seat asks for reasoning effort medium by default (D6 follow-through)
N4 measured that the seat sends `"reasoning": {"effort": "none"}` on every request (settings default `reasoningEffort: off`), and the day's transcripts show zero reasoning tokens. In pkgs/dsh-openrouter/dsh-openrouter.sh set the default reasoning effort to `medium` (env override `OPENROUTER_REASONING_EFFORT`, values off|low|medium|high; `--help` documents it). Red first: the existing N4 bats case in tests/unit/70-dsh-openrouter.bats pins "none" — change it to pin "medium" and show it red before the wrapper change; add a case for the override. Record in the commit body that the quality/cost effect is unmeasured (dated debt) and how to measure it (one fix-round task with medium vs none, tokens and verdict).
**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats, docs/runbooks/lanes.md
**acceptance:** unit, lint
**commit subject:** `dsh: the seat requests reasoning effort medium by default, overridable (test: unit, lint)`

### N15 (code, S) — hook guard and denials reader on python3Minimal
The N7 hook guard pulled full python3 (139 MiB) into the system closure. In pkgs/dsh-openrouter/default.nix build hook-guard.py and dsh-denials.py with python3Minimal (they use only json, os, re, sys, time, zstd via the zstd binary or the stdlib — verify; if the reader needs the zstandard module, keep the zstd binary as a runtime input and pipe). Expose `passthru.guardPython` on the package. Red first: a host-core eval assertion in flake.nix that `dsh-openrouter.passthru.guardPython == pkgs.python3Minimal` (today: full python3 → red). Record `nix path-info -S` of the package before/after in the commit body.
**touches:** pkgs/dsh-openrouter/default.nix, flake.nix
**acceptance:** host-core, unit, lint
**commit subject:** `dsh: hook guard and denials reader run on python3Minimal — closure shrinks (test: host-core, unit, lint)`

### N16 (code, M) — the ledger ingests OpenRouter-reported cost; the price table becomes the fallback (O2)
OpenRouter reports `usage.cost` per request: lane job results carry it (see a lane-wait result: `"usage": {"cost": 9.9e-07, ...}`), and the activity export CSV carries it per request for seat sessions. In tools/ledger/factory.py: (1) when extracting lane job results (`/var/lib/lanes/<lane>/results` or the spool the runbook names — read docs/runbooks/lanes.md), record `cost_usd` from `usage.cost` when present; (2) accept the OpenRouter activity export CSV as an input (`--activity <csv>`), join to seat sessions by date+model (document the residual: per-session attribution is approximate when several sessions share a day+model), and prefer reported cost over the price table wherever it exists; (3) `rollup --costs` prints reported vs estimated totals separately and names unpriced counts. Red first: fixtures for a lane result with cost, an activity CSV, and a session with neither. Fold in the N6 minors the Opus review listed (docs/reviews/2026-09-04-opus-review-a3-N6-round2.md: no-start session on the --week path; boundary notes). Update tools/ledger/schema.md.
**touches:** tools/ledger/factory.py, tests/ledger/test_factory.py, tools/ledger/schema.md, tests/ledger/fixtures
**acceptance:** ledger-unit, lint
**commit subject:** `ledger: OpenRouter-reported cost is ingested from lane results and the activity export; the price table is the fallback (test: ledger-unit, lint)`

### N17 (code, M) — the seat driver joins the repo
`~/factory/bin/` (factory-lib.sh, factory-brief, factory-ws, factory-task, factory-wave, factory-integrate, factory-review, factory-usage.py, launch-today.sh, README at ~/factory/README.md) ran the whole fix round headless through the seat and is unversioned. Copy it into tools/factory/seat/ (keep names), make it shellcheck-clean under the repo's lint (add the directory to githooks/pre-commit and the flake lint check's shellcheck and ruff lists), and add tests/unit/80-seat-driver.bats: factory-brief renders a plan section with the WORKSPACE RULES block and REPO NOTES (deterministic, no network); factory-ws refuses a non-repo path; the wave-group grouping helper if one exists. Red first (no tests exist). Write tools/factory/seat/README.md from ~/factory/README.md, stating that N10/F8 are the in-factory successors and this is the operator's manual per-task tool. Do NOT change behaviour.
**touches:** tools/factory/seat/, tests/unit/80-seat-driver.bats, githooks/pre-commit, flake.nix, docs/runbooks/lanes.md
**acceptance:** unit, lint
**commit subject:** `factory: the headless seat driver joins the repo with tests and lint coverage (test: unit, lint)`

### N18 (code, S) — tidy batch
(1) tests/unit/70-dsh-openrouter.bats case "--dump-config mounts the hooks bridge" is red on the host only because the devShell's long TMPDIR makes the YAML value fold (`configPath: >-` + newline): assert on the parsed YAML value (python/yq via the devShell) instead of a one-line substring — red first on a long TMPDIR. (2) tools/factory/dark-factory.js: the board rule A1 — refuse `args.fixRounds` above 2 in validateGraph (message names the cap); the implementer prompt must not print "Named checks for this task: none." for a task whose checks are ["none"] — print the literal list; tests in tests/factory/render.test.mjs red first. (3) CLAUDE.md: the check-name list gains the checks added since (factory-unit, ledger-unit, helm-unit, helm-eval, helm-vm, helm-control-eval, helm-control-vm, helm-control-assertion-negative-*, lane-polkit-unit, lane-vm and any others `nix flake show` lists — read flake.nix). Document the `~/factory` root and `dsh-openrouter --denials` in the Commands section.
**touches:** tests/unit/70-dsh-openrouter.bats, tools/factory/dark-factory.js, tests/factory/render.test.mjs, CLAUDE.md
**acceptance:** unit, factory-unit, lint
**commit subject:** `tidy: hooks-bridge test parses YAML; fixRounds capped at 2 in code; check-less prompt wording; CLAUDE.md check list (test: unit, factory-unit, lint)`
