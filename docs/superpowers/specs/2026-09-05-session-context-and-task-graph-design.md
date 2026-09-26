# Session context and the derived task graph — design (approved in brainstorm, 2026-09-05; plan next)

What a fresh Fable session receives at `/new`, how it gets there without anyone
remembering a command, and how the many plans across five repos become one
dependency-aware queue that is derived from files rather than typed into the
board. Operator's objective, verbatim in spirit: enough to function and to find
where to find things; automate as much document maintenance as possible; a
seamless `/new`; one task list that understands dependency and plans for
parallel development; consider a graph database and a code graph.

## Decisions taken in the brainstorm

- **Scope: all five repos, read-only from here.** nixos-agent-env, `~/flakes/media`,
  `~/flakes/gaming`, `~/flakes/nixos-skill`, `~/flakes/dsh-harness`. Sibling repos
  are parsed, never written. No cross-repo dependency edges in this round.
  Memory stays per flake (decision 2026-09-02-memory-per-flake).
- **No database.** The graph is built in memory on every run from plan files,
  seat result files, gate reviews, `runs.jsonl` and the claims file. Weighed and
  declined: neo4j (in the pin, 2026.02.2, a JVM daemon: a unit, a port and a sync
  job on the live host for ~150 nodes), memgraph (not in the pin), kuzu 0.11.3
  (embedded Cypher file; only worth it if ad-hoc graph queries become a real
  need — the derived JSON can be loaded into it later without changing anything
  here).
- **No syntax-level code graph.** The flake's option tree and check set are the
  code graph of a Nix repo; a generated repo map with paths and one-line
  descriptions replaces hand-written architecture prose.
- **The hook fires on compact too**, so facts return after every context
  summarisation, not only at `/new`.
- **The project-status memory file is deleted**; the bundle and the task brief
  supersede it. Memory keeps preferences, lessons, the gen 28 restore point and
  vision notes only.

## What exists today (2026-09-05)

Injected at `/new`: CLAUDE.md (7.9 KB), the memory index (1.4 KB) with memory
files recalled by relevance (up to ~30 KB), the superpowers session hook (~3 KB),
and an instruction to read the board's START HERE — 14 KB today, in a 1041-line
file with eight stacked START HERE blocks; 118 of the last 381 commits edited the
board. Evidence plan E8 (board → 48 lines, one START HERE, lint-enforced) and E9b
(`evidence bundle --markdown`) are approved at gate and integrate with wave 3.
Task state lives in five places: plan headings (`dependsOn`, `touches`), gate
review files, seat result files under `~/factory/runs/<run>/<KEY>.result`,
`runs.jsonl` in `/var/lib/evidence`, and START HERE prose. Plan checkboxes are
never ticked. Typed headings (`### KEY (kind, size) — title`) exist in three
plans; the other 31 plans across the repos have untyped `### ` headings and no
dependency lines. `nix flake show` takes 62 s on core.

## 1. The session-start hook

A tracked `.claude/settings.json` registers a `SessionStart` hook (matchers
`startup|clear|resume|compact`) running `tools/session-start.sh`. The script
prints, in order:

1. the board's single `## START HERE` block from `docs/OPERATIONS.md`;
2. `evidence bundle --markdown` (live generation and revision, HEAD, which checks
   cover each, sibling heads, Helm verdicts and since when, open gaps);
3. `evidence tasks --brief` (landed / ready / blocked / rejected / unknown counts
   per repo, the next runnable wave, operator-owned items);
4. one line: `Where everything is: docs/runbooks/session.md`.

Rules: never fails the session (each step guarded; a missing `evidence` binary
prints `unavailable: <reason>` and the board still prints); output capped at
6 KB with a final `…truncated` line when cut; silent when `FACTORY_RUN` is set
or the checkout is a linked worktree (`git rev-parse --git-common-dir` is not
`.git`), so seat and factory agents never pay for it; never evaluates the flake;
wall-time target under two seconds.

Budget after this lands (today → target): CLAUDE.md 7.9 KB → ~4 KB; START HERE
14 KB (by instruction) → ~3 KB (injected); bundle 0 → ~2 KB; task brief 0 →
~1 KB; memory index unchanged, status file removed.

## 2. CLAUDE.md shrinks to rules and pointers

Keep: what this is and the one rule; the invariants pointer; Commands; the
gotchas; How work is done here. Replace the Architecture section and the
check-name list with one line pointing at the generated `docs/MAP.md`. Sequenced
after E9b's own CLAUDE.md edit integrates.

## 3. The board keeps E8's shape with one generated block

Inside START HERE the Queued paragraph becomes a block between
`<!-- tasks:begin -->` and `<!-- tasks:end -->`, rewritten by
`evidence tasks --write-board`. Operator-owned and parked items already come from
the claims file (E8). Hand-written residue: a **Now** paragraph of at most ten
lines for context no file can derive, and the static "How work runs" and "Where
things are" sections. The pre-commit hook regenerates the block and refuses a
commit where it drifts; the E8 shape guard (one START HERE, ≤160 lines) stays.

## 4. Memory

Delete `project-status.md`. Add one index line: session facts come from the hook
output, never from memory. Everything else stays.

## 5. `evidence tasks` — inputs and nodes

`pkgs/evidence/tasks.py`, stdlib only, beside `claims.py`; the `evidence` CLI
gains a `tasks` subcommand. Repos come from `docs/ledger/repos.toml`
(`[[repo]] name, path, plans = "docs/superpowers/plans/*.md"`), this repo first.

- Node `<repo>/<KEY>` from `### KEY (kind, size) — title`; `kind ∈ {code, docs}`,
  `size ∈ {XS, S, M, L}`.
- Edges from `**dependsOn:** A, B` (keys within the same repo; `none` allowed).
- File claims from `**touches:**`, checks from `**acceptance:**`, and the plan's
  `**commit subject:**` line, all as the seat driver already reads them.
- A plan with no typed heading is a **legacy** plan: its status comes from a
  front-matter line `status: done | superseded | open` added once by hand in
  this round (this repo's 23 legacy plans and the siblings' 8). Missing front
  matter → status `legacy-unknown`, counted and printed, never an error.

## 6. Status precedence

Highest wins:

1. **landed** — the plan's commit subject appears byte-identical in the repo's
   `main` history (the gates already refuse a differing subject).
2. **approved** / **rejected** — a review file whose first line matches
   `# Opus gate — seat run <run>, task <KEY> — APPROVED|REJECTED`.
3. **ran** — a seat result file `~/factory/runs/*/<KEY>.result` whose
   `workspace:` clone has origin `~/factory/base/<repo name>`; `FACTORY-RESULT
   status=` is carried as detail. A result whose origin does not match is not
   attributed.
4. **recorded** — a `runs.jsonl` `factory-run` row naming the key.
5. **ready** if every dependency is landed, else **blocked**.

Chains: `E7 → E7b → E7r` (suffix `b`, `c`, … for fix rounds, `r` for a re-plan)
are one chain; the chain's state is its last key's; a dependency on `E7` is
satisfied when any member lands (rule A1).

## 7. Outputs

- `--brief` markdown for the hook; `--json` for tools.
- `--waves --repo <name>` prints Kahn waves as the seat driver's quoted groups
  (`"E1" "E3 E4"`); `--factory-args` prints the `tasks[]` JSON
  `tools/factory/dark-factory.js` takes by hand today. Two tasks in one wave with
  overlapping `touches` serialise in key order, as the dark factory does.
- `--conflicts` lists tasks in different plans (same repo) whose `touches`
  overlap: what may run together and what must wait.
- `--write-board` regenerates the marked block in `docs/OPERATIONS.md`.
- `--check` exits non-zero on: a dependency to an unknown key, a cycle, a code
  task without acceptance, board drift. Runs in `githooks/pre-commit` and in the
  `evidence-unit` check (with fixture repos; the sandbox has no `~/factory`).

## 8. The repo map

`tools/docs/repo-map.py` writes `docs/MAP.md`: nixosModules, pkgs, checks,
tests, hosts, tools — path plus each file's first comment line. Check names are
read statically from `flake.nix`; the `lint` check receives
`builtins.attrNames checks` from Nix and fails when the map's list differs, so
the map cannot name a check that does not exist. Regenerated by the pre-commit
hook, drift refused.

## 9. Testing — red first, mutation at the gate

- Parser fixtures: typed plan; legacy plan with and without front matter; the
  chain `E7 → E7b → E7r`; a heading with `dependsOn: none`.
- Precedence: a fixture repo with a landed subject, a REJECTED review, a result
  file, a `runs.jsonl` row — assert the winner; a result file with a foreign
  origin is not attributed.
- Graph: two-plan Kahn waves; a cycle fails `--check`; unknown key fails; code
  task without acceptance fails; a `touches` overlap serialises.
- Board drift: `--check` fails on a one-character-stale block, passes after
  `--write-board`.
- Hook: `evidence` absent → START HERE plus `unavailable:`; `FACTORY_RUN` set →
  empty output; over-cap output ends with `…truncated`.
- Repo map: `lint` fails when `docs/MAP.md` names a check the flake lacks.

## 10. Sequencing

| wave | tasks | touches | starts |
|---|---|---|---|
| 1 | `tasks.py` parser + graph + tests; `repos.toml`; legacy front matter (this repo and siblings' plans are read-only → siblings' front matter is proposed as a diff, applied by the operator or a sibling task); `tools/docs/repo-map.py` + `docs/MAP.md` | new files, legacy plan headers | now — disjoint from evidence-plan wave 3 |
| 2 | `evidence tasks` CLI wiring; `--check` in pre-commit and `evidence-unit`; `lint` map assertion; `tools/session-start.sh` + `.claude/settings.json`; `docs/runbooks/session.md` | `evidence.py`, `githooks/pre-commit`, `flake.nix` | after evidence-plan wave 3 integrates |
| 3 | CLAUDE.md rewrite; board markers + `--write-board`; memory deletion | `CLAUDE.md`, `docs/OPERATIONS.md` | after E9b's CLAUDE.md and E8's board are on main |

Wave 1 runs beside evidence-plan wave 3 because their `touches` are disjoint —
the situation `--conflicts` will detect automatically afterwards.

## 11. Risks weighed

- **Inference can be wrong.** A subject edited at integration reads as not
  landed. Mitigation: the gates refuse it; the brief prints `unknown` rather
  than guessing and the count is visible.
- **A hook in the repo runs for anyone opening the checkout.** Our own script,
  read-only, capped, silent for factory agents, never evaluates the flake.
- **Sibling drift** degrades to legacy nodes, never an error.
- **The Now paragraph is still a human sentence.** Automation covers queue,
  facts and pointers, not judgement.
- **Board edits this turn would conflict with E8**, which rewrites
  `docs/OPERATIONS.md` from the same base `main` has now (2da430b). This turn's
  board entry is recorded below and moves to `docs/board/log-2026-09.md` after
  wave 3 lands.

## Board entry for this turn (to be moved to the log after E8 integrates)

2026-09-05 (afternoon) — Brainstorm: session context and the derived task
graph. Decisions: all repos read-only; no database (neo4j/memgraph/kuzu
weighed); no syntax code graph; hook on compact; project-status memory to be
deleted. Spec: this file. Concept: `docs/concepts/2026-09-05c-derived-task-graph.md`.
Next: writing-plans → `docs/superpowers/plans/2026-09-05-session-context.md`,
wave 1 dispatchable now beside evidence wave 3.

## Amendments at planning (2026-09-05, plan `docs/superpowers/plans/2026-09-05-session-context.md`)

1. Legacy plan status lives in `docs/ledger/plan-status.toml` for every repo (statuses `done | superseded | parked | open`), not in front matter: legacy plans are historical documents and siblings are read-only.
2. The repo-map generator is `pkgs/evidence/repomap.py` (tests run under the existing `evidence-unit` check), not `tools/docs/repo-map.py`.
3. Scheduling (`waves`, `conflicts`, the factory task list) covers only tasks in state ready or blocked; approved, rejected, ran and recorded tasks are in flight and are listed, never re-dispatched.
4. **§3 amended (2026-09-05 evening, from the G8b gate):** the board's generated queue block covers this repo only and is derived from this tree only (no `repos.toml`, no runs dir, no store), so it is identical on every machine and in every clone; cross-repo and in-flight state live in the session brief the hook prints live. Because a landing removes a key from the queue, the pre-commit hook regenerates the block and, when it changed, exits asking for a re-add rather than merely refusing.
5. **§1 amended (from the G6 gate):** each part of the hook output has its own budget (board, bundle, brief) and the pointer line always prints last; the total cap applies after the parts.
6. **§5–7 amended (2026-09-05 late, from the G11b gate):** a task section may name the repo it runs in (`**repo:**`); its status is derived in that repo (its git log, its result files) and a dependency on it is satisfied when that repo has it landed — in `derive_status` AND in `waves`/`seat_groups`/the factory arguments, which share one notion of "landed" (`landed_here ∪ resolved_elsewhere`). The board's tree-only block cannot see other repos, so it omits tasks whose dependencies live elsewhere and says so in its header; the session brief (live, all repos) shows them. A `repo` value not in `repos.toml` is a `check` error.
