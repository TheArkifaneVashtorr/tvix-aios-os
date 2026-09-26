# Opus re-gate — wave 1 (eight task units)

Scope: the eight wave-1 units as merged at `5a0e664`. Repo has since moved to
`76d1620` (integ/a2 carries N4, N7); every line cited below was re-read at
`76d1620` and is unchanged. Nothing in the working tree or any branch was
modified — spot checks ran in throwaway checkouts, removed after.

Words used once, then dropped: **check** = `nix build .#checks.x86_64-linux.<name>`,
the repo's gate runner. **Red-before-green** = the test was shown to fail before
the fix existed (the rule of record, `docs/decisions/2026-09-03-test-based-reality-amendments.md`).
**Mutation** = a deliberate one-line break, to see whether any test notices.

Panel: three independent voters per surviving finding, each reproducing on their
own checkout. Fifteen findings went to vote; **none was refuted**. Three drew one
dissent each (recorded in §4).

---

## 1. Verdict per unit

| Unit | Verdict | Red-before-green verified? | Checks run / pass |
|---|---|---|---|
| N1 — dsh seat wrapper: cache, model set, skills warning (`c579081`) | **rework** | yes, with a caveat — case 1 is red only when `/tmp/dsh-openrouter-cache-$(id -u)` is absent; on this host it passed against the parent commit | unit, host-core, lint — 3/3 pass |
| N2 — Helm control surface: anti-framing headers, refresh target, argv (`ede7014`, `bfe0016`) | **approve** | yes — both refresh sites and the header set independently mutation-proven | helm-unit, helm-control-vm, host-core, lint — 4/4 pass |
| N3 — broker data policy covers agent jobs; fails closed on streamed bodies (`eacdb1a`) | **rework** | yes — 4 failed / 26 passed reverted, 30 passed restored | addon, integration, lane-eval, lane-vm, host-core, lint — 6/6 pass |
| N5 — CLAUDE.md gotchas + board block (`359929c`) | **approve** | n/a and not claimed — no check reads CLAUDE.md; proven by reverse-applying the whole change (lint still green) with a control mutation showing lint is alive | lint — 1/1 pass |
| N6 — ledger extractor + `rollup --week` (`5b6ff57`, `3bd9d27`) | **rework** | yes — reverting only the fix's implementation turns the check red 5-for-5, one failure per closed finding | ledger-unit, lint — 2/2 pass (ledger-unit re-run green at `76d1620`) |
| N8 — D9 measurement: red-before-green per Helm commit (`f77b281`) | **approve** | yes — all seven code-commit rows independently reproduced, decisive lines verbatim | lint — 1/1 pass (plus 13 re-measurement runs) |
| N10 — Claude factory: scheduler, per-task worktrees, integration (`7f1b430`, `97004fa`) | **rework** | yes — reverting implementation only fails `factory-unit` at render.test.mjs:414, exactly as the plan predicted | factory-unit, lint — 2/2 pass (factory-unit re-run green at `76d1620`) |
| N11 — declare the factory root `~/factory` via tmpfiles (`a2f8177`) | **approve** | yes — reconstructed red (host-core fails on the new assertion), plus two mutations both caught | host-core, lint — 2/2 pass |

Approve 4, rework 4. No rejects: no unit contains a security defect, and no
commit message overstates what was tested.

---

## 2. Surviving blocker/major findings

Fifteen majors survived the panel. None is a blocker (nothing ships a live
security hole); all four rework units are held by the same class of defect —
a load-bearing control with no test that can fail on it, or a number that is
wrong on first real use.

### N1 — seat wrapper (3)

**N1-1 · The test suite reaches outside its temp root and can leave the live seat unlaunchable**
`tests/unit/70-dsh-openrouter.bats:32`
- *What*: `teardown()` runs `rm -rf "/tmp/dsh-openrouter-cache-$(id -u)"` — the operator's live seat cache, outside the suite's `mktemp -d` root. The documented acceptance command `nix develop -c bats tests/unit` on core therefore deletes it. Case 1 (`:298`) only asserts the shared path exists / is 700 / is owned by you, so it is green against code that does nothing.
- *Evidence*: all three voters reproduced. A canary file placed in the live cache was deleted by a suite run while the seat (`dsh-openrouter --headless`, pid 900708) was running. At `c579081^` — a wrapper with zero `XDG_CACHE_HOME` code — the same case prints `ok 1` when the path pre-exists and `not ok 1 … [ -d … ]' failed` when it does not. Two escalations beyond the original report: the symlink case at `:316` plants the symlink *at the live path*, and during that window a seat launch hits `dsh-openrouter.sh:217` and refuses to start; and on a host where the seat has ever run, `:313` and `:316` fail against **correct** code.
- *Fix*: give the wrapper an overridable cache root (e.g. `DSH_CACHE_ROOT`, default `/tmp`) so the seat keeps one warm cache; scope the test to `$TMPHOME`; assert the directory did not exist before the run; delete the `/tmp` `rm -rf` from teardown. (Do **not** default to `TMPDIR` — one voter showed that follows `PrivateTmp` and fragments the warm cache H4 exists to give.)

**N1-2 · `chmod` runs before the ownership guard, so the guard is dead code and the documented exit 5 becomes a bare exit 1**
`pkgs/dsh-openrouter/dsh-openrouter.sh:219`
- *What*: the plan's `mkdir -p -m 700` was implemented as `mkdir -p` + `chmod 700` placed **ahead** of the `stat`/`die 5` guard at `:220`. Under `set -euo pipefail`, a pre-existing foreign-owned directory at the predictable `/tmp` path dies at `chmod` with a raw permission error, never reaching the guard. `usage():58` documents 5 as the bad-value code.
- *Evidence*: shipped wrapper, `XDG_CACHE_HOME=/var/empty` → `chmod: changing permissions of '/var/empty': Operation not permitted`, rc=1. Same input against the plan's ordering → rc=5, `is not owned by you`. Deleting `:220` outright leaves all 26 bats cases green.
- *Fix*: `mkdir -p --`, then the `stat`/`die 5` guard, then `chmod 700 --` (safe once ownership is established). Note the wrinkle a voter found: the plan's literal `mkdir -p -m 700` trips shellcheck SC2174 inside `writeShellApplication` and also would not correct the mode of a pre-existing dir — the fix is the **order**, not the primitive. Add the red case: `XDG_CACHE_HOME=/var/empty … ; [ "$status" -eq 5 ]`.
- *Dissent*: one voter refuted on impact (both orderings abort at the same point; nothing consumes exit 5; the symlink race is not closed by the suggested fix either). Upheld: the guard the plan demanded cannot fire, and its removal is invisible to the suite.

**N1-3 · The one payload shape the seat is actually deployed in has no test; the `find -H` that makes it work is unguarded**
`pkgs/dsh-openrouter/dsh-openrouter.sh:239`
- *What*: production deploys `skills`/`AGENTS.md` as symlinks (`~/flakes/dsh-harness/README.md`, and the live seat is wired that way today). The emptiness probe honours that only because of `find -H`; the bats case at `:340` covers absent, dangling, empty and plain-non-empty-directory, never symlink-to-non-empty.
- *Evidence*: mutation `find -H` → `find` leaves all 26 cases green while a real deployment prints `… /skills is empty: the seat has no skill catalog` — a warning telling the operator to redo a deployment already in place. Unmutated behaviour is correct today; only unguarded. The proposed case is red under the mutation and green at HEAD.
- *Fix*: add the deployed shape to the case at `:361` (payload dir + non-empty AGENTS.md outside `$DSH_HOME`, both `ln -s`'d in; assert the output names neither path), or replace `find` with a bash glob probe (`shopt -s nullglob dotglob`) that removes the `-H` subtlety and the `findutils` dependency at once.
- *Dissent*: one voter refuted as "coverage gap on correct code, outside the written acceptance". Upheld: U6's value is a warning the operator can trust, and the regression channel is unguarded.

### N3 — egress broker (1)

**N3-1 · Both new options' Nix→policy-JSON wiring is exercised by zero checks; `lane-vm`'s ZDR assertion is satisfied by the client, not the broker**
`nixosModules/egressBroker.nix:19` (and `:15`)
- *What*: the commit renames the wire-format key carrying brief §3 invariant 5 (`path_prefix` → `path_prefixes`) and adds `inject.<host>.paths`. `addon` is pure Python over hand-written dicts; `host-core` (`flake.nix:673`) and `lane-eval` (`flake.nix:1164`) assert only `inject.<host>.valueFile`; `lane-vm` asserts `"zdr": true` in the fake upstream's log, which `pkgs/lane/lane-run.py:98` already puts in every client body.
- *Evidence*: all three voters. Renaming the emitted key leaves addon, lane-eval, host-core, lint and the full `lane-vm` VM run at exit 0. Two voters ran a **stronger** mutation — disconnecting the body patch entirely (`body_patch = { }`, or making `_patch_body` an immediate `return`) — and `lane-vm` still passed, exit 0, ~14 s. So the broker's enforcement of a §3 non-negotiable has no test that can fail on it.
- *Fix*: make `lane-vm` prove the **broker** patches: push a body with **no** `provider` key through `/run/netns/egress-openrouter` and assert the upstream log shows `"zdr": true`, plus a companion request to an unlisted path arriving unpatched. Cheaper complement: expose the generated policy attrset as an internal read-only option and assert `body_patch.<host>.path_prefixes` / `inject.<host>.paths` next to `flake.nix:673`.
- *Calibration*: two voters downgraded the "credential fails open" direction — nothing in-tree sets `inject.paths` narrower than the default `["/"]`, so dropping the key is a no-op **today**; and breaking `path_prefixes` fails toward over-patching, not toward no ZDR. The untested-invariant claim stands on its own.

### N6 — ledger (2)

**N6-1 · `rollup --week` applies no time window — it reports lifetime totals under the name of a weekly rollup**
`tools/ledger/factory.py:398`
- *What*: `_rollup_week` reads all four ledger files whole and sums everything; `rollup` uses `week` only to pick a view; `--week` is a bare `store_true`. No code path inspects `started`. The output names no window.
- *Evidence*: all three voters. A dsh session started 2024-01-01 (in=1,000,000) is counted in full in the 2026-09-04 "weekly" rollup. The `--costs` total inherits the same lifetime scope. `backfill` is designed to ingest every past `wf_*` dir at once, so the **first** real `rollup --week` after a backfill reports the whole history as "the week".
- *Fix*: `--since`/`--until`, default trailing 7 days UTC; filter dsh sessions on `started` and factory records on their run's `started`; print the window bounds as the first line. Wrinkle a voter flagged: run `started` is ISO-8601 (`:189`), dsh `started` is epoch ms (`:303`), and `factory-agents.jsonl` carries no timestamp — agents must be joined to their run by `run_id`.

**N6-2 · `rollup --costs` silently prints a confident total for unpriced sessions, and cannot read the O2 artifact it is specified to read**
`tools/ledger/factory.py:336` (and `:348`, `:522`)
- *What*: (a) `_load_prices` requires `in_per_1m,out_per_1m,cache_read_per_1m` — a hand-maintained rate table — while the plan, the docstring and `schema.md:18,:102` all name the input `<openrouter-activity.csv>`, which carries per-day cost. (b) `_cost_for` returns `None` on a `(date, model)` miss and `rollup` skips those sessions, then prints a bare total.
- *Evidence*: all three voters, against the repo's own fixtures. All-mismatch CSV → `cost: 0.000000 USD` for real tokens. **Partial** match (the case plan line 885 says to expect — "Three sessions used another provider") → `cost: 0.000798 USD` instead of `0.004788`: precise, confident, silently understated. Activity-export-shaped CSV → unhandled `KeyError: 'in_per_1m'`. `schema.md:20-21` declares a local price table "deliberately absent … goes stale"; `schema.md:102` then specifies one. Coverage is a single all-rows-match test (`tests/ledger/test_factory.py:140`), whose substring assertion would not even notice an added unpriced-count suffix.
- *Fix*: never print a bare total when any session is unpriced — `cost: 0.004788 USD (2 of 5 sessions unpriced: no row for (2026-09-04, …))`; raise a named error listing the columns found when the CSV is the wrong shape; and either consume the real activity export (sum its `cost` column) or rename the argument and the `schema.md` heading to `<price-table.csv>`.

### N10 — Claude factory (4)

**N10-1 · Every wave branch is merged regardless of the review verdict, and the run then tells the operator to fast-forward it**
`tools/factory/dark-factory.js:362`
- *What*: `integrateWave()` builds its merge list from `branchOf` with no status predicate; `branchOf` (`:490`) is populated for every result carrying a branch. A task the gate rejected with a blocker (`unapproved`) or whose reviewer died twice (`unreviewed` — the documented API-529 case at `:410`) is merged `--no-ff`, the wave records `ok: true`, and the log at `:514` prints an unqualified `git merge --ff-only` into the live-host checkout.
- *Evidence*: all three voters drove the real script. Blocker on A every round → statuses `{A: unapproved, B/C: approved}`, merge list still `A, B, C`, `integrations[0].ok = true`, closing log naming no withheld key while `:529` prints `unreviewed=none`. Reviews all returning null → every task `unreviewed`, all merged. A wave-2 task is then dispatched onto that tip and told at `:400` it "already contains every dependency's merged work". One voter proved causality: adding only `.filter((t) => statusOf.get(t.key) === 'approved')` flips it (merge list `B, C`; nothing to integrate in the unreviewed case).
- *Fix*: filter the merge list by verdict and `log()` each withheld branch with its status; make the not-delivered line name the non-approved keys instead of printing a bare fast-forward command.
- *Bound*: `allOk` at `:502` does keep `delivered` false, so the script does not fast-forward by itself — the exposure is the instruction it prints and the wave-2 contamination.

**N10-2 · A task group swallowed by `parallel()` vanishes from `tasks[]` and makes the delivery gate vacuously true**
`tools/factory/dark-factory.js:502` (driver at `:488`)
- *What*: `allOk` quantifies over `results`, which the driver shortens on a null slice with one `log()` line. `every()` over the shortened array is satisfied, so the run spawns the delivery agent, fast-forwards into the live repo's current branch, and returns `delivered: true` with a declared task absent.
- *Evidence*: all three voters, using the harness's documented `parallel()` semantics (a thrown thunk resolves to null). Four tasks in, three out; `delivered: true`; deliver agent actually spawned; closing summary `verify=pass, unreviewed=none`. The suite cannot reach the path — the stub at `tests/factory/render.test.mjs:183` is a bare `Promise.all`. Partial mitigation a voter found: a lost task that others depend on marks dependents `blocked`; the silent window is leaf tasks.
- *Fix*: push an `{status: 'unreported'}` entry per task in a null slice and add `results.length === A.tasks.length` to the gate; cover with a scenario whose `parallel` stub is `thunks.map((t) => t().catch(() => null))`.

**N10-3 · The delivery gate's task-approval term is untested — deleting it leaves the whole suite green**
`tools/factory/dark-factory.js:502`
- *What*: `results.every((r) => r.status === 'approved')` is the only barrier between a reviewer-rejected task and an auto fast-forward into the repo the live host builds from (given N10-1, that branch carries the rejected commit). The only two `delivered === false` scenarios also stub integration red, so `integrations.every(i => i.ok)` alone carries both assertions.
- *Evidence*: all three voters. Replacing `:502` with `integrations.every((i) => i.ok)` → `factory-unit` green, exit 0. The control mutation (reversed merge-order comparator at `:363`) fails at `render.test.mjs:459`, so the suite is not inert. The mutant is not equivalent: with a blocker on A and integration/verify green, the original yields `delivered: false` and no deliver spawn, the mutant yields `delivered: true` and spawns it.
- *Fix*: one scenario — `review:A` returns a blocker every round while `integrate:w1` and `verify` stay green; assert `delivered === false`, no `deliver` call, and (after N10-1) that A is absent from the `integrate:w1` merge list.

**N10-4 · `RULES_ORCH`'s closing clause contradicts the integfix instructions it is injected into**
`tools/factory/dark-factory.js:113`
- *What*: the block ends "…never edit tracked files by hand — the checked-out tree changes only through the merge your instructions name", and `:379` then tells the integration-fix agent "Resolve conflicts by keeping BOTH sides' intent". Resolving a conflict is by definition hand-editing tracked files. `:81` calls violating any rule "a critical failure". Same defect class as the previous round's major, relocated rather than removed.
- *Evidence*: two voters rendered the real prompts and confirmed both strings in one template literal; the integrator role does not contradict (`:365` tells it `git merge --abort`), so integfix is the sole site. Nothing pins the text: a voter made the clause maximally contradictory ("NEVER resolve a merge conflict…") and the suite stayed green — `render.test.mjs:517` checks only two removed strings.
- *Trim*: the baseline half of the original claim is over-stated — committing an untracked plan file edits no tracked file. Severity rests on integfix.
- *Fix*: "…NEVER rebase/amend/rewrite history. Do not edit a tracked file except to resolve a merge conflict your instructions name, and commit nothing but that resolution or a file your instructions name." Then assert positively that the integfix prompt does not forbid conflict resolution.
- *Dissent*: one voter refuted — the clause opens "Do exactly the git operations your instructions below name", the path fails closed (integration-failed, operator sees it), and the suggested wording *loosens* a guard rail. Upheld on the narrow ground that the text is unpinned and self-contradictory at the one place recovery happens; treat the wording choice as the operator's call.

---

## 3. Minors worth a tidy task

- **N1** `warns on stderr` asserts against bats' merged `$output`; dropping `>&2` from `warn()` still passes.
- **N1** `findutils` is used at runtime but is not a `runtimeInput` — under a trimmed PATH the payload probe reports a deployed catalog as missing.
- **N1** `--help` still names `deepseek/deepseek-v4-pro-0813` as the `OPENROUTER_MODELS` default; the code now composes four extras.
- **N1** the new comment cites `tools/factory/dark-factory.js` for a role→model map that file does not contain (it lives in `~/flakes/dsh-harness/README.md`).
- **N2** `http.server`'s own `send_error` responses (501/414/400) bypass the `_send` header chokepoint — move the four headers into an `end_headers()` override.
- **N2** the argv test sentinels only `helm_open_workspace_bin`; hard-coding `kgx_bin` inside `spawn_open` leaves 114 passed.
- **N3** the streamed-body test uses a GET and configures no inject spec, so kill-before-credential-injection is unasserted (deleting the `return` at `policy.py:262` passes).
- **N3** fail-closed covers only patched paths: `/api/v1/messages` is still injected-but-unpatched and unkilled by design — tracked residual pending O3/N9.
- **N3** `_patch_body` silently skips non-JSON content types and non-dict bodies, contradicting the option's "whatever it sends".
- **N5** the new CLAUDE.md cache clause points agents at a stable world-writable `/tmp` path without naming the symlink/ownership guards the wrapper applies there.
- **N5** "the seat wrapper now does" was false when `359929c` landed (N1 had not arrived) — a wave-ordering hazard, not a live defect.
- **N6** the findings-derived fix-rounds branch is unreachable (`"task": None` hardcoded); a `"task": "T9"` mutation survives the suite.
- **N6** factory-lane `wall_s` sums concurrent agent spans (75.0) while the run record already stores the true span (105.0).
- **N6** `backfill` crashes on a workflow dir with no `journal.jsonl`, after writing partial ledger output.
- **N6** the per-role view drops `reasoning`/`cache_write`, and the unlabelled `cost:` line covers only the dsh lane in a report that now totals both.
- **N6** the fix commit amended its own governing plan section — spec edits belong to the orchestrator.
- **N8** "none of the Helm tests is a change-detector" generalises from one measured check per commit while subjects name up to five.
- **N8** the `b678875` row reads as a flat "red" when only 3/4 negatives are module-level — **promote to tracked debt**: `helm-control-assertion-negative-profiles` self-asserts in `flake.nix:1090` and proves nothing about `nixosModules/helm.nix`.
- **N8** two quoted "decisive output lines" embed non-reproducible pytest timings.
- **N8** the board's "all eight … mutation-checked" contradicts its own "18d7a17 is n/a", and that commit is not docs-only (597-line acceptance script).
- **N10** the "byte-identical to the pre-split text" comment is false, and `extraRules` are no longer last.
- **N10** scenario 12's `forbidden` list covers two of the three implementer-only clauses.
- **N10** the concurrency guard's red state is an infinite hang, not an assertion failure — bound the loop with `step = Math.max(1, CONCURRENCY)`.
- **N10** `t.key` is validated only as a non-empty string but is interpolated verbatim into `git checkout -B`.
- **N10** `parallelSafe: true` is documented as "runs alongside anything" but an explicit `touches` list overrides it.
- **N10** the whole-run verifier still runs when every wave failed to integrate, and the summary prints `verify=pass`.
- **N10** the determinism claim in the scheduler header does not extend to the `tasks[]` order (completion order, not key order).
- **N11** the runbook's `git clone --local` hardlinks the object store, handing a workspace-write-confined seat a write path into the live `~/nixos-agent-env` — use `--no-hardlinks`.
- **N11** the commit body records no red observation; worth folding "Red: …" into the commit-convention paragraph so the whole factory emits it.

---

## 4. Refuted findings

**None.** All fifteen findings that went to vote survived. Three drew a single
dissent apiece and were upheld 2-1; the dissents are recorded because each
narrows the claim:

- **N1-2 (chmod ordering)** — dissent: both orderings abort at the same point, nothing consumes exit 5, and the suggested `mkdir -p -m 700` does not close the symlink race either. Upheld: the guard cannot fire and its deletion is invisible to the suite; severity is diagnostics, not exploitability.
- **N1-3 (`find -H`)** — dissent: correct behaviour today, warn-only, and the deployed-symlink case is outside the written N1 acceptance. Upheld as an unguarded regression channel on a warning the operator is meant to trust.
- **N10-4 (`RULES_ORCH`)** — dissent: the clause is subordinated to "do exactly the operations your instructions name", the path fails closed, and the proposed wording loosens a guard rail. Upheld narrowly: the text is unpinned and self-contradictory at the recovery step. The baseline half of the original finding is dropped as over-stated.

Also trimmed rather than refuted: N3's "credential containment fails open" (a
no-op today — nothing sets `inject.paths`), and N3's rename failing toward
over-patching rather than toward no ZDR.

---

## 5. Recommended fix tasks (paste-ready)

Seven tasks. `W2-N1a`/`W2-N1b` and `W2-N10a`/`W2-N10b` overlap files and must
serialise (declare `touches`).

---
**key**: `W2-N1a`
**title**: seat cache block — reachable ownership guard, test-scoped cache root
**files**: `pkgs/dsh-openrouter/dsh-openrouter.sh`, `tests/unit/70-dsh-openrouter.bats`
**red-first test**: two cases, both failing today. (1) `XDG_CACHE_HOME=<a dir you do not own> run dsh-openrouter --dump-config` → assert `status -eq 5` and output contains `not owned by you` (today: status 1, `chmod: … Operation not permitted`). (2) with the default cache root pointed at `$TMPHOME` via a new `DSH_CACHE_ROOT` knob, assert the directory did **not** exist before the run and does after, 700, owned by the caller (today: no such knob; the case reads the shared `/tmp` path and passes on inherited state).
**also**: reorder to `mkdir -p --` → `stat`/`die 5` → `chmod 700 --` (not `mkdir -p -m 700`: SC2174, and it will not correct an existing dir's mode); delete `rm -rf "/tmp/dsh-openrouter-cache-$(id -u)"` from `teardown()`; keep `/tmp` as the seat's default so the warm cache is not fragmented.
**acceptance checks**: `unit`, `host-core`, `lint`

---
**key**: `W2-N1b`
**title**: payload warning — deployed-symlink case, real stderr assertion, declared `findutils`, honest `--help`
**files**: `tests/unit/70-dsh-openrouter.bats`, `pkgs/dsh-openrouter/dsh-openrouter.sh`, `pkgs/dsh-openrouter/default.nix`
**red-first test**: build the production shape — a payload dir with a file and a non-empty `AGENTS.md` **outside** `$DSH_HOME`, both `ln -s`'d in — run `--dump-config` and assert the output names neither `$dsh_home/skills` nor `$dsh_home/AGENTS.md`. Show it red by mutating `find -H` → `find` (or by replacing `find` with a `shopt -s nullglob dotglob` glob probe and dropping the dependency). Second case: `run --separate-stderr`, assert the warning is on `$stderr` and absent from `$output` (red today with `>&2` removed).
**also**: add `findutils` to `runtimeInputs` if `find` is kept; fix the `--help` `OPENROUTER_MODELS` default text and assert it names the same list the default composes; re-point the role→model comment at `~/flakes/dsh-harness/README.md`.
**acceptance checks**: `unit`, `lint`

---
**key**: `W2-N3`
**title**: prove the broker enforces the ZDR patch — Nix→policy wire format under test
**files**: `tests/integration/lane-vm.nix`, `nixosModules/egressBroker.nix`, `flake.nix`
**red-first test**: from inside `/run/netns/egress-openrouter`, `curl --cacert <broker ca-bundle>` a body with **no** `provider` key to `https://openrouter.test/api/v1/chat/completions`; assert the fake upstream's log shows `"zdr": true` for that request, and that a companion request to an unlisted path (`/api/v1/models`) arrives unpatched. Show red by emitting `body_patch = { }` from `egressBroker.nix` (today: `lane-vm` stays green, ~14 s). Cheap complement, no IFD: expose the generated policy attrset as an internal read-only option and assert `body_patch.<host>.path_prefixes == [ "/api/v1/chat/completions" ]` and `inject.<host>.paths == [ "/" ]` beside `flake.nix:673`.
**also (fold in if cheap)**: make the streamed-body pytest a POST with an `inject` spec and assert `Authorization` is absent from the killed flow.
**acceptance checks**: `lane-vm`, `lane-eval`, `host-core`, `addon`, `lint`

---
**key**: `W2-N6a`
**title**: `rollup --week` gets a real window
**files**: `tools/ledger/factory.py`, `tests/ledger/test_factory.py`, `tools/ledger/schema.md`
**red-first test**: a ledger with one in-window and one out-of-window dsh session (and one out-of-window factory run); assert the out-of-window records are excluded from every lane, role and fix-round total, and that the first output line names the window bounds. Red today: the 2024 session is counted in full and no window line is printed.
**also**: `--since`/`--until`, default trailing 7 days UTC; join agents to their run by `run_id` for windowing (agents carry no timestamp; run `started` is ISO-8601, dsh `started` is epoch ms).
**acceptance checks**: `ledger-unit`, `lint`

---
**key**: `W2-N6b`
**title**: `rollup --costs` stops printing confident wrong dollars
**files**: `tools/ledger/factory.py`, `tests/ledger/test_factory.py`, `tools/ledger/schema.md`
**red-first test**: (1) a price CSV covering one of two sessions → assert the cost line names the unpriced count and the missing `(date, model)` key, and does **not** print a bare total (today: a silently understated `cost: 0.000798 USD`). (2) an activity-export-shaped CSV (`date,model,tokens,cost`) → assert a named error listing the columns found (today: unhandled `KeyError: 'in_per_1m'`). Use exact-line assertions, not substrings — the current test would pass a suffix change.
**also**: either consume the real O2 activity export (sum its `cost` column, joined on date+model) or rename the argument and the `schema.md` heading to `<price-table.csv>` and reconcile it with `schema.md:20-21`.
**acceptance checks**: `ledger-unit`, `lint`

---
**key**: `W2-N10a`
**title**: factory integration/delivery gate honours verdicts and accounts for every task
**files**: `tools/factory/dark-factory.js`, `tests/factory/render.test.mjs`
**red-first test**: two scenarios, both green today. (1) `review:A` returns a blocker every round while `integrate:w1` and `verify` stay green → assert `delivered === false`, no `deliver` spawn, and A absent from the `integrate:w1` merge list, with a log line naming A as withheld. (2) `parallel` stubbed as `thunks.map((t) => t().catch(() => null))` with `impl:B` throwing → assert `tasks[]` still has four entries, B at `status: 'unreported'`, and `delivered === false`.
**also**: filter `integrateWave`'s merge list by `statusOf === 'approved'`; add `results.length === A.tasks.length` to `allOk`; make the not-delivered line name the non-approved keys instead of printing a bare `git merge --ff-only`; skip Verify when nothing integrated and report `verify=skipped`.
**acceptance checks**: `factory-unit`, `lint`

---
**key**: `W2-N10b`
**title**: orchestration rules stop forbidding the conflict resolution they demand
**files**: `tools/factory/dark-factory.js`, `tests/factory/render.test.mjs`
**red-first test**: assert positively that the `integfix:w1` prompt does not contain a clause forbidding hand-edits to tracked files, and that the `forbidden` list at `render.test.mjs:517` includes all three implementer-only clauses. Red today (and a maximally contradictory clause currently passes the suite untouched).
**also**: reword the `RULES_ORCH` closing clause to permit exactly the conflict resolution `:379` names and nothing else; fix the "byte-identical" comment and restore `extraRules` to last; add a branch-name regex to `validateGraph` for `t.key`.
**acceptance checks**: `factory-unit`, `lint`
