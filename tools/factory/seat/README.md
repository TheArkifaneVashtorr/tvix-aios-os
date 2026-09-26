# tools/factory/seat — the operator's manual per-task tool

This directory is the **operator's manual per-task tool** for running
implementation tasks through the headless `dsh-openrouter` seat (DeepSeek via
OpenRouter, not Claude). It is a versioned copy of the scripts that ran the
whole 2026-09-04 fix round from `~/factory/bin/` while that tree was
unversioned; land N17 brings them into the repo under `tools/factory/seat/`
so they are gated on shellcheck and ruff like everything else here.

**The in-factory successors are N10 and F8**: these scripts are a manual
precursor of the scheduler plan tasks N10/F8 add to
`tools/factory/dark-factory.js` (`docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md`,
`docs/decisions/2026-09-04-parallel-agent-workflows.md`). Once
`dark-factory.js` grows a scheduler of its own, that is what day-to-day task
work runs through; until then this driver is how tasks get run against the
seat. Nothing here changes behaviour from the `~/factory/bin/` originals — the
scripts still run against the operator's own `~/factory` root at run time
(`FACTORY_ROOT`, default `$HOME/factory`), not against this repo.

Everything here runs **as the operator, with the operator's own OpenRouter
key** (`~/.config/openrouter/key`) — there is no broker, no netns, no lane.
`dsh-openrouter`'s own refusal list is the only guardrail against pointing
this at local-only data (see `docs/runbooks/lanes.md`). Nothing under
`~/nixos-agent-env` or `~/flakes` is ever edited directly — every task runs
in its own disposable clone under `~/factory/ws/<run>/<KEY>`.

## Layout

```
~/factory/                         (the runtime root; FACTORY_ROOT)
  base/<repo-name>/          a git clone --local of the real repo, kept in
                              sync with its current HEAD before each task
  ws/<run>/<KEY>/             one task's disposable clone, branch task/<KEY>
  runs/<run>/<KEY>.log         full seat transcript (stdout+stderr)
  runs/<run>/<KEY>.result      parsed FACTORY-RESULT + branch head + log +
                                diffstat + usage
  runs/<run>/<KEY>.dsh-home/   that task's own isolated DSH_HOME (default)
  runs/<run>/<KEY>.pid         this task's own pid while its seat runs (removed
                                on exit; a SIGKILL or reboot can strand it, and
                                the in-flight reader reaps a stranded `.pid`
                                once its pid is dead and older than the stale
                                threshold)
  runs/<run>/<KEY>.review.md   factory-review's output
  runs/<run>/<KEY>.gate        the reviewer's pid while a review gate runs
                                (removed on exit)
  runs/<run>/run.meta          the run's identity and intent: run, repo, plan
                                (the absolute path of FACTORY_PLAN), base
                                (the HEAD sha), pid, launched, one %q-quoted
                                group: line per wave group (a quote or a
                                backslash in a group survives verbatim), and
                                then: only when --then was given
                                (factory-wave --then)
  runs/<run>/integrate.log     factory-integrate's full log

tools/factory/seat/           (this repo) the scripts themselves
```

`~/factory` and everything directly under it is mode 0700.

## The scripts

- **`factory-brief <plan.md> <KEY>`** — prints the exact prompt for one
  task: the plan's Global Constraints and Assumptions sections, the task's
  own `### KEY ...` section, and a fixed WORKSPACE RULES block (work only
  in the current directory, TDD, commit convention, the FACTORY-RESULT
  summary format). If `KEY` has no section in the plan, set
  `FACTORY_TASK_TEXT` to supply an ad-hoc task instead of failing.
- **`factory-ws <run> <repo-path> <KEY> [base-branch]`** — refreshes
  `~/factory/base/<repo-name>` to `<repo-path>`'s current HEAD, then clones
  it into `~/factory/ws/<run>/<KEY>` at `base-branch` (default:
  `integ/<run>` if it exists, else the repo's current branch) and checks
  out `task/<KEY>`. Prints the workspace path.
- **`factory-task <run> <repo-path> <KEY> [--model ID] [--after KEY2]`** —
  `factory-ws`, then the seat headless in that workspace on
  `factory-brief`'s output. `FACTORY_PLAN` is required: unset or empty
  refuses with exit 2 before any workspace or run dir is created, and a
  set-but-unreadable path dies with the same `no such file:` exit 2. It is
  then absolutised through `realpath` (a symlinked plan resolves to the file
  it actually names), the same shared helper `factory-wave` uses, so the
  brief and the routing lookup read one canonical path regardless of the
  caller's cwd.
  `--after KEY2` forks the workspace from
  `task/KEY2` instead (for a chain inside one `factory-wave` group).
  Writes its own pid to `runs/<run>/<KEY>.pid` while it runs (removed on
  exit), then the `.log` and `.result` described above. When `seat-submit`
  is on `PATH` and `FACTORY_SEAT_UNIT` is not `0`, the seat runs through the
  seat unit instead of a direct `dsh-openrouter` launch — see below. When
  the fork point is known, a recording `status=done` is checked against the
  branch: a `FACTORY-COMMITS` claim that does not match
  `git rev-list --count base..head`, a done with no commits, or a bare-`ok`
  result (a template echo) is demoted to `failed` with the lie spelled out.
  The check has two outcomes, both scoped to a `status=done` claim: a claim
  that matches the branch leaves the done standing; any mismatch, including
  a claim of *fewer* commits than the branch holds, demotes to `failed` and
  appends `claimed N commits, found M` to the seat's own `FACTORY-NOTES`
  (never replacing a failing seat's diagnosis). A stray extra commit — the
  `pre-commit` gate's "`git add docs/OPERATIONS.md` and commit again" step
  lands two commits while the seat reports one — is a convention breach, so
  extra commits are not excused. A near-miss `FACTORY-RESULT` line — a colon
  after the label, `status:` instead of `status=`, a status word outside
  `done|partial|failed`, or markdown decoration — is recorded verbatim as
  `FACTORY-RESULT status=failed` (exit 2, notes `result-misparse:` plus the
  line's first 200 bytes), never guessed at; an accepted line is never
  re-classified.
- **`factory-wave <run> <repo-path> "<group>" ["<group>" ...]
[--then <text>]`** — each group is a space-separated chain of keys run
sequentially (later keys `--after` the one before); groups run
concurrently, capped at `FACTORY_JOBS` (default 5). `FACTORY_PLAN` is
required: unset or empty refuses with exit 2 before `run.meta` or any
workspace is written, and its absolute path is recorded as the `plan:` line
of `run.meta` and passed through to every `factory-task` it starts. The
path is absolutised with `realpath`, so a symlinked plan is recorded by the
file it actually names, basename included.
`--then <text>`
records what the orchestrator means to do when the run lands; together
with the run's identity it is written to `runs/<run>/run.meta` at
dispatch time, so the record exists even if the run dies mid-flight (a
reboot included). `--then` is optional and single-line only: omitting it
leaves the `then:` line absent; giving it twice wins the last value; a
value containing a newline is refused (exit 2). When the shell is not
already a session leader, the driver re-execs itself under `setsid -w`,
so a `/new` or a closed terminal does not kill the run — a reboot still
does — while the launcher still sees the wave's exit code and summary.
That detach is the driver's own job now: the board's `setsid -f …` launch
rule is retired and the orchestrator invokes `factory-wave` directly.
Prints one summary line per key; exits non-zero if any task did not reach
`status=done`. The in-flight reader rebuilds a `relaunch:` hint from
`run.meta` — `FACTORY_PLAN=<plan> factory-wave …` (for a pre-P11 run whose
`run.meta` carries no `plan:` line the hint is instead a bash comment,
`# plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave …`, so
pasting it verbatim launches nothing rather than an argv that dies on the
missing plan), with every spliced field — plan, repo, groups, `--then` —
`%q`-quoted. The full hint prints at most once per run (later dead groups
of the same run read `relaunch: as above`), and only when the wave's pid is
dead, no per-key seat is alive, and it names only the groups whose keys
have no done result — a mixed wave (one key landed, one without a
`.result`) lists only the not-yet-landed groups. The hint is a convenience:
it may be cut by the session brief's 1,000-character in-flight cap, and the
authoritative relaunch source is always `~/factory/runs/<run>/run.meta`.
Day-to-day use goes through `factory-dispatch`, which derives the groups.
- **`factory-dispatch <run> <repo-path> <plan-file> [--dry-run] [--all]
[--repo-name NAME]`** — asks the derived task graph for a plan's next
wave and launches it through `factory-wave`, then prints the task brief
(see "Dispatching a plan" below).
- **`factory-integrate <run> <repo-path> KEY...`** — in the *base* clone
  only: resets `integ/<run>` to the repo's current default branch,
  `git merge --no-ff`s each `task/<KEY>` in order (a conflict aborts that
  merge and continues). A key whose branch changes `docs/OPERATIONS.md`
  anywhere outside the `<!-- tasks:begin -->`…`<!-- tasks:end -->` queue
  block (compared against the merge base, never origin's tip), or whose
  branch shares no merge base with the default branch at all (an unrelated
  history), is refused with `REFUSED <KEY>` and a `refused: N` summary
  line, not merged — the board is the orchestrator's to write, not a
  task's, and a refusal is counted once under `refused:`, never also under
  `conflicts:`. A key with no workspace at all (`~/factory/ws/<run>/<KEY>`
  missing) is `SKIP`ped and counted under `skipped:`, and a skip, like a
  refusal or a conflict, makes the integration exit non-zero. Then it runs
  every check named in the merged commits' `(test: ...)` lists plus `lint`,
  once each, against the integration tree. Never touches the real repo; it
  prints the fast-forward command only when every key merged (a skipped,
  refused or conflicted key means the tree is incomplete).
- **`factory-review <run> <repo-path> <KEY> [--model ID]`** — a second
  headless session, in a *fresh* clone of `task/<KEY>` (not the
  implementer's own workspace), reviewing the diff against the plan
  section, proving red-before-green by reverse-applying the test hunk,
  checking the commit convention, and listing blockers/majors/minors.
  Writes `<KEY>.review.md`. Leaves a `runs/<run>/<KEY>.gate` marker holding
  the reviewer's pid for as long as the gate is running (the removal trap is
  armed before the marker is created), so in-flight state can see a review in
  progress even though its output is `.review.md`/`.review.log` rather than a
  `.result`. `SIGKILL` (and a reboot) can still strand the marker; its dead
  pid is what marks it stale — the in-flight reader reaps such markers (and a
  stranded `<KEY>.pid`) once they are older than the stale threshold, counting
  them in one `… and N stale pid files` summary line, and lists a finished gate
  as `gate done` once its `.review.md` is written. A recycled pid — a process
  whose `ps` start time is *after* its pid file was written — is denied
  "alive", so a stale pid file never paints a long-dead run as running. Never
  fixes anything.
- **`factory-usage.py`** — per-task token usage from a dsh transcript.
- **`factory-plan <run> <repo-path> <spec> <name>`** — runs a headless
  planning seat for one spec (plan 2026-09-06-planning-agent, P8): sizes the
  spec by word count (S ≤ 1500 < M ≤ 4000 < L, the one shared
  `factory_plan_size` rule), refuses an L spec (exit 2), routes the seat's
  model and effort through the `plan` role, composes the planning packet with
  `factory-plan-brief`, then hands it to `factory-task` so the seat's one
  commit lands the draft at
  `docs/reviews/plan-drafts/<date>-<name>-<model>.md` on `task/PLAN-<name>`.
  `<spec>` is resolved relative to `FACTORY_TOOLBOX_REPO` (exported to the
  brief child), exactly as the brief resolves it; `<name>` must match
  `^[a-z0-9][a-z0-9-]{0,63}$` (refused as exit 2 otherwise). A failing brief
  — exit 2 or exit 3 — exits 2 with the brief's stderr; exit 3 stays reserved
  for a routing-table failure. The seat's plan is
  `tools/factory/plan/seat-plan.md` (not under `docs/superpowers/plans/`), and
  the packet travels as the ad-hoc task text.
- **`factory-plan-brief <spec> <out> [--since YYYY-MM-DD] [--date
  YYYY-MM-DD]`** — composes the planning packet for the planning agent (see
  "Planning brief" below).
- **`launch-today.sh`** — a dated one-shot from 2026-09-04, kept as a
  worked example, not for reuse.

## Planning brief

`factory-plan-brief` composes the planning packet handed to the planning
agent (plan 2026-09-06-planning-agent, task P2). It **prints** the brief to
stdout and writes nothing under the tree; `<spec>` is a path under
`docs/superpowers/specs/` and `<out>` must sit under `docs/reviews/plan-drafts/`
(both relative to `FACTORY_TOOLBOX_REPO`, which defaults to the repo the script
lives in; each is resolved with `realpath -m` and refused when it traverses
out of its prefix). The tree's Python tools run through `factory_py` —
`FACTORY_PYTHON3_CMD` when set, else the toolbox devShell python.

Every command-backed part captures its standard output alone and prints it in a
`~~~` fence; the part's stderr is captured apart, stripped of nix's own noise
(the "Git tree is dirty" and "evaluation warning" lines), and whatever remains
is printed under the part as a second `stderr:` fence. The whole packet is
composed into a temp file and printed only after the last part succeeded, so a
refusal never leaks a partial packet on stdout. `M8` runs
`tools/ritual.sh inflight`, which shares the session hook's stranded-marker
reaping: it removes dead-pid, stale `.pid`/`.gate` files under the runs dir
(idempotent housekeeping), and writes nothing under the tree.

The packet, in order: thirteen mechanical parts under `## M<n> — <command>`
headings — M1 `tasks.py --root . check` (the graph-soundness gate), M2 the task
brief, M3 the graph JSON's byte count, M4 the wave structure, M5 touch
conflicts, M6 the evidence bundle, M7 claims validation, M8 the reset ritual's
in-flight view, M9 the session-start hook, M10 the `docs/MAP.md` Checks
section, M11 the routing table, M12 recent commits, M13 `factory-brief`'s
shape for one task — then `FIELD` (the driver's contract, pinned by fixed
greps, plus the board's START HERE block and recent board log), `OPERATOR`
(the operator model), `TARGET` (the spec, sized S/M/L by word count), `RUBRIC`,
`CHECKLIST` and `RULES`. `M13` runs `factory-brief` via `bash` (the way
checks.unit's sandbox runs every seat script — its shebang names
`/usr/bin/env`, which the sandbox lacks), and its heading carries the command
exactly as run. `M6` only runs `evidence bundle` when the toolbox tree is the
live host the store describes; against any other tree it prints
`unavailable: evidence describes the live host, not this tree`.

Exit codes: `0` the brief printed; `2` a refusal (a malformed spec/out path, a
malformed `--since`/`--date`, or an unsound graph — nothing is printed to
stdout, and no later part runs); `3` a mandatory file the packet reads is
missing or unreadable, or a part failed mid-packet — again nothing is printed.
M6/M8/M9 and the operator model degrade to `unavailable: <reason>` without
failing the brief; the rubric falls back to the design spec's 5.1 table, and
a design spec without its Appendix A checklist is a refusal (exit 3), never an
`unavailable:`.

## Dispatching a plan

The primary way to run a plan is `factory-dispatch`: it asks
`pkgs/evidence/tasks.py`'s derived graph for the plan's next wave, launches
it through `factory-wave` (each task's model and effort still come from
`docs/ledger/routing.toml` via `factory-task`), waits, and prints the task
brief -- no hand-typed groups:

```
# See what the next wave is without launching anything:
tools/factory/seat/factory-dispatch sc5 ~/nixos-agent-env docs/superpowers/plans/<plan>.md --dry-run

# Actually launch it, then print the brief:
tools/factory/seat/factory-dispatch sc5 ~/nixos-agent-env docs/superpowers/plans/<plan>.md
```

`--dry-run` prints the `would run: factory-wave …` line for the next wave and
exits without launching. Without it, the wave is launched (the graph refuses
a repo it does not know -- `<repo-path>` is matched against its `path` in
`<repo-path>/docs/ledger/repos.toml`, or `--repo-name NAME` overrides the
lookup) and the brief follows; a non-zero `factory-wave` exit is propagated.
`--all` recomputes and launches wave after wave until nothing remains,
stopping at the first wave that does not reach `status=done`, or dying with
`no progress` if the same wave comes straight back after a wave that exited 0.
`--dry-run` is safe to repeat: no seat is launched until a wave is actually
run.

The gate and integration steps stay manual: `factory-review` each landed task
(and the Opus gate), `factory-integrate` the landed tree, then the
fast-forward (below).

## Running a wave (the low-level tool)

`factory-dispatch` composes these; here is the hand-typed form for when you
need one specific group, or to understand what the dispatcher does:

```
run=myrun
repo=~/nixos-agent-env

# One task:
tools/factory/seat/factory-task "$run" "$repo" N1

# A wave: N1 and N2 alone, N11→N3→N6 as one chain, N5→N8 as another —
# five groups running concurrently (cap: FACTORY_JOBS, default 5):
tools/factory/seat/factory-wave "$run" "$repo" "N1" "N2" "N10" "N11 N3 N6" "N5 N8"

# Wave 2, after wave 1's tree is integrated (see below):
tools/factory/seat/factory-wave "$run" "$repo" "N4 N7"

# A review of a landed task (optional, no auto-fix):
tools/factory/seat/factory-review "$run" "$repo" N1

# Integrate everything landed so far:
tools/factory/seat/factory-integrate "$run" "$repo" N1 N2 N10 N11 N3 N6 N5 N8
```

The scripts resolve their siblings relative to their own directory
(`FACTORY_BIN` defaults to the directory of `factory-lib.sh` itself — the
directory of whichever script is actually running — and
`FACTORY_BIN_OVERRIDE` can replace it), so they can be run from this repo's
checkout or invoked by absolute path; they do not read anything from this
repo other than the scripts themselves. `~/factory/bin` is no longer read —
delete it after the switch.

## Fast-forwarding the real branch

`factory-integrate` never touches `<repo-path>`. It prints, and this is the
exact recipe, run by the operator/orchestrator once the integration's
checks are green — chain it on the integrator's exit code, because a failing
check still leaves an `integ/<run>` head behind and a bare pull would land it
(that happened once, on 2026-09-06, with `evidence-unit` red):

```
tools/factory/seat/factory-integrate <run> <repo-path> KEY... \
  && git -C <repo-path> pull --ff-only ~/factory/base/<repo-name> integ/<run>
```

Every check the integrator runs is also recorded in the evidence store with
the integration head (the `integ/<run>` commit those checks were run against),
so Helm's flake-check tile and `evidence bundle` see it once the branch is
fast-forwarded. `FACTORY_EVIDENCE_CMD` overrides the recorder (tests),
`EVIDENCE_STORE` the directory.

## Effort levels

The seat's model picker offers five reasoning-effort levels — `off`, `low`,
`medium`, `high`, `xhigh` — with `medium` the default (the seat *asks* the
model to reason; `off` is the explicit no-reasoning request, sent as `none`
on the wire). `OPENROUTER_REASONING_EFFORT` overrides a saved picker level
by writing the agent selection, so an env-var launch wins regardless of what
`settings.yaml` holds (`env > saved > route default`). The tests' fake
upstream records only what the seat *sends* on the wire — that a request
carries the effort it was told to — not what OpenRouter actually does with
each level.

## Routing

`factory-task` (role `implement`) and `factory-review` (role `review`) no
longer hard-code one model: each resolves the model and reasoning effort for
a task from the table `docs/ledger/routing.toml`, keyed on role × kind ×
size. `FACTORY_ROUTING_TABLE` overrides which table both lookups read (an
explicit `FILE`/`--file` still wins).

- **The table.** Each row is a `[[route]]` block with six keys — `route`,
  `role`, `kind`, `size`, `model`, `effort`. `route` is `openrouter` (the
  DeepSeek models this driver uses) or `claude` (the dark factory's Anthropic
  models); a row without a `route` key defaults to `openrouter`.
  `factory_route [--route R] <role> <kind> <size>` prints `MODEL EFFORT` for
  the winning row **of route R** (default `openrouter`): the most specific
  match wins (specificity = number of fields that are not `any`), ties go to
  the earliest row, and a row with all three fields `any` is that route's
  default and must exist. `kind` and `size` come from the plan's
  `### KEY (kind, size) — title` heading (`factory_task_kind_size`); a
  heading without that parenthetical — or a task not in the plan — resolves
  to `any any`.
- **One table, both routes.** The same table also drives
  `tools/factory/dark-factory.js`: its built-in default `models` map is the
  literal output of `tools/factory/route.py models`, which `route.py` derives
  from the table's `claude` rows, and on every `claude/review/<kind>` gate the
  dark factory uses that row's model. The `models` argument handed to the
  Workflow is `route.py models` output; `route.py check` validates the table
  and `route.py lookup ROUTE ROLE KIND SIZE` mirrors `factory_route` — a test
  cross-checks the two lookups on the same fixture, and `checks.factory-unit`
  refuses any drift between the table and dark-factory.js's built-in default.
- **Precedence.** Model: a `--model` flag, then `OPENROUTER_MODEL`, then the
  table, then the built-in default (reached only when the table is missing or
  malformed, in which case a warning is logged). Effort:
  `OPENROUTER_REASONING_EFFORT` if set, else the table's `effort`. The seat
  is launched with `OPENROUTER_REASONING_EFFORT=$effort` in its environment.
- **Recorded.** `factory-task` writes two extra lines into its `.result`
  file, right after `model:` — `effort: <effort>` and
  `route: <explicit|role/kind/size>` (`explicit` when a flag or env var chose
  the model, otherwise the role/kind/size the table matched). `factory-review`
  resolves the same way with role `review`.
- **Adding a row.** Edit `docs/ledger/routing.toml` only — never the scripts
  — to change which model/effort an existing role/kind/size uses, or to add
  rows for the existing words. The recognized words are enumerated in
  `factory_route` (routes `openrouter`/`claude`; roles `implement`/`review`/
  `verify`/`baseline`/`research`/`audit`/`orchestrate`/`plan`; kinds
  `docs`/`code`; sizes `XS`/`S`/`M`/`L`, plus `any`); to introduce a
  brand-new kind or size, extend that enumeration (and `route.py`'s) at the
  same time as the new row. No `plan` row exists today: `factory-plan` routes
  the planning seat through `plan`, which resolves to the openrouter default;
  a `plan` row lands only once a commit cites the measurement plan's report
  (design §6.2).

The interactive seat the operator opens on core (not headless) is not
governed by this table: it keeps its saved selection. Only the headless
driver reads it.

## Cost

Rates: `docs/ledger/openrouter-prices.csv` (dated rows;
`tools/ledger/factory.py rollup --costs` reads it). Hand-multiplied dollar
figures are not written in prose. The Helm v1 run
(N1–N11-equivalent scope, `tools/factory/dark-factory.js`, Claude) cost
about **$24** in Claude tokens; this driver exists to run comparable work
against DeepSeek Pro instead. Per-task token counts are in each
`runs/<run>/<KEY>.result`'s `usage:` line (tokens only — see
`docs/runbooks/lanes.md` and N6/T1 on why no dollar figure is invented
here; `rollup --costs` prices them from the rates file above).

## DSH_HOME: isolated per task, not shared

Every `factory-task`/`factory-review` run gets its own `DSH_HOME` under
`~/factory/runs/<run>/<KEY>.dsh-home`, seeded with symlinks to the shared
`~/.local/share/dsh-openrouter/{skills,AGENTS.md}` (and anything else the
wrapper does not regenerate at launch) rather than pointing every run at the
operator's own shared `DSH_HOME`.

This was tested, not assumed. `FACTORY_SHARED_DSH_HOME=1 factory-wave smoke
~/nixos-agent-env "SMOKE2" "SMOKE3"` — two headless launches at the same
instant against the operator's own shared `~/.local/share/dsh-openrouter` —
both failed in under a second, each with:

```
Error: dsh: failed to parse overlay /home/dalhaka/.local/share/dsh-openrouter/openrouter-route.yml:
YAMLException: end of the stream or a document separator is expected (12:1)
```

Not a hang, not a silent corruption — a hard parse error. `dsh-openrouter`
regenerates `$DSH_HOME/openrouter-route.yml` with several non-atomic
`cat >`/`cat >>` writes on every launch; two processes doing that to the
same file at the same time interleaved their writes and left invalid YAML
for whichever one read it back. The very same command with the
isolated-by-default `DSH_HOME` (`unset FACTORY_SHARED_DSH_HOME`) succeeded
for both, concurrently. `FACTORY_SHARED_DSH_HOME=1` still exists on
`factory-task`/`factory-review` for a *single* task run against the
operator's own shared home, but `factory-wave` never sets it, so concurrent
groups never share one.

## Seat unit (SB3)

When the seat lane's submit CLI is installed (`command -v seat-submit`
succeeds) and `FACTORY_SEAT_UNIT` is not `0`, `factory-task` submits the task
as a seat job instead of running `dsh-openrouter` directly in the workspace.
The model and effort chosen by `factory_route` are passed to `seat-submit` as
`--model`/`--effort`, the isolated `DSH_HOME` (default
`runs/<run>/<KEY>.dsh-home`) as `--dsh-home`, and the composed brief as
`--brief`; `seat-submit` writes `/var/lib/seat/jobs/<id>/job.json`, starts
`seat@<id>`, and streams the unit's `stdout.txt` back. "It reads the job's
`stdout.txt` as if it were the seat's stdout" — so the `FACTORY-RESULT`
extraction and the `.result` file are unchanged, plus one extra
`seat: unit seat@<id>` line. Set `FACTORY_SEAT_UNIT=0` to force today's
direct-launch path even when `seat-submit` is present. `factory-task` reads the
job id from `seat-submit`'s stdout alone and checks its `YYYYmmdd-HHMMSS-<6
hex>` shape; a submit that prints no valid id is recorded as
`seat: submit failed (no job id)`. A headless job whose `--timeout` expires is
stopped (`systemctl stop seat@<id>`) and the submit exits 124, so a timed-out
run is never orphaned.

## Smoke test (2026-09-04, run "smoke", against the real OpenRouter key)

`FACTORY_TASK_TEXT` stood in for a task not in any plan: create
`tools/factory/SMOKE.txt` with one line, commit it through
`nix develop -c git commit`, print the FACTORY-RESULT lines.

- **(a) `factory-task smoke ~/nixos-agent-env SMOKE`** — succeeded, both
  the `Co-Authored-By` (Global Constraints) and `Generated-By` (WORKSPACE
  RULES) trailers present.
- **(b) DSH_HOME sharing test** — shared failed in under a second on a real
  race; isolated (the default) succeeded for both SMOKE2 and SMOKE3,
  concurrently, with no interference.
- **(c) `factory-integrate smoke ~/nixos-agent-env SMOKE SMOKE2 SMOKE3`**
  — merged cleanly, no conflicts; since every smoke commit says
  `(test: none)`, only `lint` ran, and passed.

Two real bugs turned up and were fixed during this run (both in the scripts,
not in `dsh-openrouter` itself):

1. **Status mis-parsed as `unknown`.** The brief quotes the FACTORY-RESULT
   format as a template, and a headless model's visible reasoning routinely
   echoes that template back while it plans — `factory-task` originally took
   the *first* matching line; fixed to take the *last* line for each label
   that doesn't still contain a stray `<`.
2. **`git fetch --force` after `--` was read as a ref name**, not a flag, in
   `factory-integrate`. And a fresh `git clone` never inherits the source
   repo's *local* git identity, so `git merge --no-ff` failed with
   `Committer identity unknown`; `factory-ws` and `factory-integrate` now
   copy the identity from `<repo-path>`'s local (falling back to global)
   config into every clone they make.

## Headless mode: what it actually needed

`dsh-openrouter --headless "TASK"` takes the task as a single positional
argument (not stdin), prints to stdout, and exits. The driver adds a
per-task `DSH_HOME` on top of the wrapper, and relies on the wrapper for
`XDG_CACHE_HOME`:

- **`XDG_CACHE_HOME`** — the harness sandbox makes `$HOME` read-only for
  model-run commands, so Nix's fetcher cache write is fatal without a
  writable cache dir under a temp root. The wrapper sets it with a `/tmp`
  default (`pkgs/dsh-openrouter/dsh-openrouter.sh:340`); R10 removed the
  driver's own redundant `${XDG_CACHE_HOME:-…}` default, so the driver no
  longer overrides it.
- **A per-task `DSH_HOME`** — see above.

## Commit trailers (the convention)

Every commit made through this driver carries **both** trailers, each on its
own line, in this exact order:

```
Generated-By: dsh <version> / <model> (seat headless, factory run <RUN>)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`factory-brief`'s WORKSPACE RULES block states this explicitly so a headless
run does not have to reason it out. The `Co-Authored-By` trailer matches
`CLAUDE.md`'s requirement that every commit in this repo carry it, while the
`Generated-By` trailer records which harness/model/run actually authored the
work; `factory-task` fills the `<RUN>` and `<model>` placeholders from its
arguments (the `<version>` is pinned to the driver's `dsh` release in the
brief text itself).

One prompt-composition wrinkle remains: `factory-brief` prints the plan's
Global Constraints verbatim, which name the trailer as exactly
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` — written for a
Claude-run task. The WORKSPACE RULES block now asks for the same
`Co-Authored-By` line plus the `Generated-By: dsh ...` line, so the two no
longer conflict; the earlier smoke run had already reasoned toward both
trailers before the brief said so, which is why this was tightened up.

## Toolbox

`python3` and `jq` are not on the bare host `PATH`; every use of either in
this driver goes through `nixos-agent-env`'s devShell
(`cd ~/nixos-agent-env && nix develop -c ...`), regardless of which repo a
task targets. `zstd` and `git` are on the host `PATH` directly. `nix build`
runs directly in a task's workspace (each is a full clone of the same flake
the real repo has).