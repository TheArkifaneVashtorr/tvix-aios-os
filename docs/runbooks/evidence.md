# The evidence store and the claims file

Two different things share the word ledger. The **claims file**
(`docs/ledger/claims.toml`) is the list of what we believe about this system
and whether each belief is proven. The **ledger** (`/var/lib/evidence/ledger/`)
is the token and cost record. This page is about the store and the claims file.

## The store

The evidence store is one directory of append-only JSONL files, one per
stream. It lives at `/var/lib/evidence` and is backed up nightly with the
rest of the host. Every row in it records an *observation* — a fact that a
named check actually happened at some revision with some result — never a
belief or a plan. Nothing is ever edited in place: a correction is a new row.

Seven writers append to it:

- the nightly flake check (`helm-flake-check`) records the whole stack green
  or red at a revision;
- the seat integrator records a check after each factory integration;
- the factory's verify step records a check after it runs the flake check;
- Helm's collector records a `helm-status` row whenever a tile changes
  verdict (or an hour passes);
- the two ingests (`evidence ingest openrouter-usage`,
  `evidence ingest otel`) merge the broker's and the collector's raw files
  into `ledger/*`;
- the transcript backfill (`tools/ledger/factory.py backfill`) merges what
  it read from `~/.claude/projects`.

The broker (its `/var/lib/egress-broker/<name>/usage.jsonl`) and the
collector (its `/var/lib/opentelemetry-collector/claude-{metrics,logs}.jsonl`)
are producers that never write the store: their rows reach it only through
the ingests (see [`## Spend`](#spend)).

Read it with one command:

```
evidence bundle --markdown
```

That prints the live generation and revision, `HEAD`, which checks cover
each, the sibling heads, what Helm has been showing since when, and the open
gaps. For one check at one revision there is a narrower command:

```
evidence latest-check --name flake-check --rev $(git rev-parse HEAD)
```

and the raw stream is just JSONL, so `tail` works too:

```
tail -n 3 /var/lib/evidence/checks.jsonl
```

A plan file that has not landed yet can be judged before it is committed:
`python3 pkgs/evidence/tasks.py --root . check --draft FILE` parses `FILE`
wherever it lives outside the plans directory, attaches its tasks to this
tree's graph, and holds it to the same rules as a landed plan — its
`acceptance` names must each be `lint` or a name in `docs/MAP.md`'s Checks
section, its `touches` must be explicit paths, its commit subjects byte-exact
and matching their acceptance, and the file must carry the four house sections
(`## Global Constraints`, `## Assumptions`, `## Waves`, `## Operator`). On
success it prints the draft's `waves:` and `conflicts:` rows; the exit code is
`0` when clean, `1` when any rule fails, and `2` for a usage error (the file is
unreadable, already under the plans directory, or no configured repo matches
`--root`).

## The claims file

A **verified** claim means a named check was green at a revision and the row
records how it was checked (`check:<name>@<rev>`); an operator-judged drill
keeps class `operator` (`operator:<date>`). Prose is never evidence.

**Open a gap** by adding a `[[claim]]` row with `status = "gap"`, an `owner`,
a `review_by` date and a `closes_by` that says what would close it. The hook
refuses two things: a gap past its `review_by` date (extend it with a reason
or close it), and evidence that is prose instead of `check:<name>@<rev>` or
`operator:<date>`.

**Close a gap** by flipping the row to `status = "verified"` and giving it
`evidence` of one of those two shapes. Validate the file with:

```
nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"
```

## Task areas

Every task's area is derived from its `touches` through the subsystem manifest
(`docs/ledger/subsystems.toml`): the first row whose `owns` glob matches a
touched file names that file's area, and the task's area is the majority over
its touched files, a tie going to the earliest row. A task whose touches span
two areas must say so with an `**areas:** evidence, factory` field on its
section; `tasks.py check` refuses a two-area task without the declaration as
`tasks: <plan>/<key>: touches span areas … without an areas: declaration`.

The keys typed before the area dimension existed are grandfathered in
`docs/ledger/areas-grandfather.toml`, a list written once at EV2's commit with
the HEAD sha beside it. `check` exempts exactly the listed keys from the
cross-area refusal and nothing else, so a key typed later into an old plan file
is refused like any other.

A key's reserved prefix is its leading letters up to the first digit or hyphen
(`EV1` → `EV`, `SPEC-PL` → `SPEC`, `EVX1` → `EVX`), compared case-insensitively.
A key under a manifest prefix (`IS PL HM SA FA EV GN KN PR`) must sit in a plan
file the subsystem's `plans` list names; `check` refuses it otherwise as
`tasks: <plan>/<key>: prefix <XX> is reserved for <subsystem>, whose plans are
<globs>`.

## The plan-defect ledger

`docs/ledger/plan-defects.toml` records every Opus-gate rejection that names a
plan defect, one `[[rejection]]` row per review: the repo-relative `review`
path (which must exist), its `run` and `key`, the filing `date` (the review
basename's prefix) and a `plan_defect` class drawn from the seven-value enum
`none | vacuous | missing-case | underspecified | wrong-fact | implementer |
process`. A row with two classes names the primary first and the second as
`plan_defect_secondary`. `[meta] front_matter_from` is the date from which a
gate review must carry the front-matter block; earlier files stay byte-unchanged
and are classified by these rows. `tasks.py check` reads the ledger, and the
brief's `Record (7 d)` line counts its rows: `**Record (7 d):** N rej, M plan
(vac a, miss b, under c, fact d)` — N the seven-day rejection total (blocks and
ledger rows; a block on an APPROVED review never counts), M the plan-caused
subset (vacuous/missing-case/underspecified/wrong-fact) and one `vac`/`miss`/
`under`/`fact` tally each. The line is display only: P10 reads the ledger, never
this line.

From `front_matter_from` on, every gate review carries a block — line 1 `---`,
then `key: value` lines, then `---`, with the `# Opus gate — seat run …` header
immediately on the next line (a blank line or prose between the closing `---`
and the header is a shape error). This task's check reads `plan_defect`, the
optional `plan_defect_secondary`, and the optional `mutants_total` /
`mutants_killed` / `mutants_outside_named`, each an ASCII-digits-only
non-negative integer — the rule is `^[0-9]+$`, so a sign, an underscore or a
non-ASCII digit is refused (other keys are ignored). The graph check enforces
the block: a review dated on or after `front_matter_from` must carry one, the
header must follow the block, `plan_defect` must be present and in the enum, a
REJECTED review may not name `plan_defect: none`, a mutant count that is not an
integer is refused, and a ledger row whose review file carries an APPROVED
block is a contradiction (`… a ledger row contradicts an APPROVED block`).
Both the check rule and the graph's `read_reviews` glob `*opus-review*.md`, so
a review whose basename lacks "opus" supplies no verdict and is never block-
validated. The evidence-unit sandbox pins the ledger to the frozen seed:
`flake.nix` copies `tests/evidence/fixtures/ledger/plan-defects-seed.toml` over
`docs/ledger/plan-defects.toml` and sets `EVIDENCE_UNIT_SANDBOX=1`, so the
sandbox never sees the live, growing ledger. A test that hard-codes the live
count passes in the devShell (which reads the live ledger) but fails in the
sandbox — the sandbox is the truth, the devShell run is not. This pin replaced
P3Ar2b's text-scanning guard and its helpers (deleted): rather than scan test
code for literal counts over the live ledger, the environment itself can no
longer reach it. P3Ar's `M11`/`M11b`
(live-ledger class flips) are no longer killable since P3Arb, the frozen-fixture
flips standing in for them — so the gate counts P3Ar's remaining kills, not the
original 42.

## The planning report

`evidence report plans` reproduces the design §7 planning metrics from the
tree, joined to first-gate outcomes, each number with its n and no conclusion
under five chains:

```
nix develop -c python3 pkgs/evidence/evidence.py \
  --store /var/lib/evidence report plans --repo .
```

The four core lines are first-try landing rate (chains approved at their own
first gate ÷ chains gated), plan-caused share of rejections (primary
`plan_defect` in the four plan classes ÷ all rejection rows — every ledger row
plus every REJECTED block, no seven-day window and an APPROVED block never
counts), re-plan rate (chains with a `r`-member ÷ chains gated), and rework
rounds per landed task (members beyond the root ÷ landed chains — rounds are
counted over landed chains only). The rubric join, survivors-outside-the-named-set
and the threshold proposal follow once enough plans are judged. The whole report
is a proxy until telemetry T10a/T10b land.

The design §7 "today" column is superseded by this report's numbers: §7 used
landed chains (58) as its denominator for every row, its rounds figure (30)
matches neither the gated (52) nor the landed (46) reading of the same tree, and
it said "ten typed 2026-09-05 plans" where twelve are typed.
On this tree, over `--plan '2026-09-05-*.md'`, the report prints first-try
28/63, re-plan 10/63 and rework rounds 47/59 = 0.80 — not the design's 28/58,
11/58, 30/58.

## The ladder report

`evidence report ladder` reproduces the seat driver's ladder (spec
2026-09-06-operator-seat-driver-design.md §6) from the `.result` files under
the runs dir, joined to each row's gate review, and adds the orchestrate
section from the drive jobs:

```
nix develop -c python3 pkgs/evidence/evidence.py report ladder --repo . \
  --runs-dir ~/factory/runs --jobs-dir /var/lib/seat/jobs --min-n 5
```

Every `.result` whose `run:` and `key:` parse is a row (the `plan:` line, when
it exists, is matched against `--plan GLOB`). The review for a row is the
matching `docs/reviews/*opus-review*-<run>-<key>.md`'s verdict, else the run's
`<key>.review.md` `FACTORY-REVIEW verdict=` line (`approve` = approved,
`rework`/`reject` = rejected), else none. Each row groups under its
(route, role, kind, size, class, model, effort, rung) tuple — route/role fixed
to openrouter/implement, kind/size parsed from `route: implement/<kind>/<size>`
(`explicit`/absent → `unknown`), class from `class:` (absent → `any`), rung
from `rung:` (absent → 1).

The header line names the spec's §6 and the refusal rule; then one line per
group, sorted by the tuple:

```
<route>/<role>/<kind>/<size>/<class> <model> <effort> rung <N>: \
  n=<n> first-gate <a>/<g> (<pct>%) landed-commits <mean, 2 decimals> \
  fix-rounds <f>/<l> wall-median <s>s out-tokens-median <t>
```

where `g` = rows with a review, `a` = approved among them, `f` = rows whose
key has a chain suffix (`CHAIN_RE`) whose root is in the group and approved,
`l` = approved roots in the group, and the medians run over the rows carrying
the field. **The refusal:** a group with n < `--min-n` (default 5) prints
`<tuple>: insufficient (n=<n>)` and nothing else — no conclusion below five,
as everywhere here.

Then the **orchestrate section**, headed `# orchestrate — drive sessions
(run.meta driver: ⋈ job.json)`: every `<runs-dir>/*/run.meta` carrying a
`driver:` id joins to that id's `<jobs-dir>/<id>/job.json` when its `mode ==
"drive"`; per (model, effort) pair it prints `orchestrate <model> <effort>:
sessions=<distinct ids> runs=<n> tasks=<keys from those runs' group: lines>
first-gate <a>/<g>`, refused under min_n sessions as `insufficient
(n=<sessions>)`, and `orchestrate: no drive session recorded` when no drive
job is readable.

The report is the record that closes the ladder claims (`ladder-*` and
`driver-row-unmeasured` in `docs/ledger/claims.toml`). The `tasks`-stream row
shape (`rung`, `class`, `prior`, `escalate`) is the telemetry sub-project's
own (T2). **The seam:** today `report ladder` reads the `.result` files and
the review files directly; when telemetry T10a lands the join moves onto
`join_tasks_gates`, and these output lines stay (the SD9 docstring names
exactly that).

## The harness report

`evidence report harness` is the seat-harness baseline (SH1): it reads the
store only — `derived/tasks` joined to each row's newest `derived/gates` on
`(run_id, key)` — windowed by `result_mtime[:10]`, and n-gates every group:

```
nix run .#evidence -- report harness --before 2026-09-15 --since 2026-09-01
```

`--before` is exclusive and `--since` inclusive; a row with no `result_mtime`
is out of every bounded window. `--min-n` (default 5) is the per-group gate;
the report reads nothing from the tree (`--repo` is not taken). Its lines, in
order:

1. the header (names the design §6 it proxies);
2. `window: since … before …` — the bounds in force;
3. `population: N task rows, G with a gate verdict`;
4. per group — `all`, then every `task_kind/size` pair present, sorted — either
   `insufficient (n=…)` under `--min-n`, or the three round-kind fractions
   (`first-gate approved a/n (p%)`, `fix-round approved b/m`, `re-plan approved
   c/l`) plus the median output tokens and wall-seconds by verdict (`-` when a
   verdict has no rows);
5. `error_class: …` — a count-descending tally over every windowed row;
6. `plan_defect: …` — over rejected gates, a `None` defect counting as
   `unclassified`;
7. `tags: unmeasured …` — the §2 corpus tags live only in
   `docs/reviews/harness-study/2026-09-07-deepseek-failure-corpus.md`, not in
   the store; `plan_defect` above is the proxy (one primary class per gate vs.
   many tags per run);
8. `rung/class: unmeasured …` — closed by the seat-driver plan's `rung`
   (SD1, SD3) and `class` (SD2) fields, which do not exist yet.

The two `unmeasured` lines stay until their named closes land: SD1–SD3 declare
the rung/class fields (line 8), and nothing in the store carries the corpus
tags (line 7) — the plan-defect proxy remains.

`--split YYYY-MM-DD` adds the before/after measure: the baseline lines (1–8)
print for the *before* window (`result_mtime[:10] < split`, narrowed by
`--since`), and a new block for the *after* window (`>= split`, narrowed by
`--before`); without `--split` the block covers the whole window and the
before figures print `-`. A malformed `--split` exits 2.

Per change, the after-window block prints six line kinds (lines 9–14):

1. `after: since … before …; N task rows, G with a gate verdict, A approved`;
2. one line per change — `touches`, `checks`, `probes`, `unreported` — over
   the after-window rows carrying its field (`touches_extra`, `checks_verified`,
   `probes_verified`, `status`) with the demotion count per `error_class` arm,
   the gate verdicts on those demotions (`agreed` = rejected, `overruled` =
   approved, `ungated` = no gate), and each change's extra (`undisclosed
   extras` = `touches_extra > touches_disclosed`, `verify-timeout`,
   `drift`, `gated`/`approved` for `unreported`);
3. `control false positives: <o> of <A> approved rows` — the overruled
   demotions of every change summed over the after window's approved gated
   rows;
4. one `verdict <change>:` per change — over its gated demotions ordered by
   `result_mtime` (ties by `run_id`, `key`), the first five decide
   `revert (overruled o of 5)` when `o >= 2` (the revert rule) and `keep`
   otherwise; fewer than five → `insufficient (n=k)`; a change with at least
   ten rows carrying its field and zero demotions appends `zero demotions in
   n tasks — keep only if the target tag fell to zero`. A `revert` line drives
   a `<KEY>r` re-plan under rule A1;
5. `success:` the first-gate approved fraction before/after and the output
   tokens per landing (`median usage.out` after) against the before window's
   approved median × 1.5 (`yes`/`no`/`insufficient`);
6. `untargeted:` the three §6 causes never measured in the store, proxied by
   `mutants_outside_named` summed over the after window's gates.

## The usage-ingest timer

The seat broker's `usage.jsonl` reaches the store hourly under the system
timer `usage-ingest.timer`, which runs the oneshot `usage-ingest.service` as
`dalhaka`. The service is conditioned on the source existing
(`ConditionPathExists=/var/lib/egress-broker/seat/usage.jsonl`), so a broker
that has written nothing yet is skipped, not failed; `Persistent = true` runs
a missed hour at the next boot. The calendar is `OnCalendar=hourly`. See the
unit names, next run and calendar with:

```
systemctl list-timers 'usage-ingest*'
```

A cold store (a fresh `/var/lib/evidence` after, say, a reinstall) is filled
by hand with the same command the timer runs:

```
evidence ingest openrouter-usage /var/lib/egress-broker/*/usage.jsonl
```

## Spend

The dollar of record comes from five streams, fed by three raw files:

- `openrouter-usage` (stream `ledger/openrouter-usage`) — the broker's
  `/var/lib/egress-broker/<name>/usage.jsonl` (unbacked);
- `otel-claude` (stream `ledger/otel-claude`) — the collector's
  `/var/lib/opentelemetry-collector/claude-{metrics,logs}.jsonl` (unbacked);
- `factory-run`, `factory-agent` and `main-session` (streams
  `ledger/factory-runs`, `ledger/factory-agents`, `ledger/main-sessions`) —
  the backfill's read of `~/.claude/projects`, which is read in place and
  never copied.

The two raw files under `/var/lib` are never backed up; the store rows are
what survives. The operator runs the four lines in order, each in its own
fenced block:

```
evidence ingest openrouter-usage /var/lib/egress-broker/*/usage.jsonl
```

First line: `ingested <n> rows into ledger/openrouter-usage (0 refused)` — an
exit `0` needs zero refusals; the count is the day's broker rows.

```
evidence ingest otel /var/lib/opentelemetry-collector/claude-*.jsonl
```

First line: `ingested <n> rows into ledger/otel-claude (0 refused, <s>
skipped)` — a torn last line (the collector is still writing) is reported and
skipped, never refused; skips are fine, refusals are not.

```
nix develop -c python3 tools/ledger/factory.py backfill ~/.claude/projects --ledger-dir /var/lib/evidence/ledger
```

First line: `backfill: <w> workflow dirs, <m> main sessions, <l> limit events`
— the per-file MAX dedup fixed the naive sum's 3.5× inflation (concept
2026-09-08d).

```
evidence report spend --since 2026-09-01 --prices docs/ledger/claude-prices.csv
```

First line: `# evidence report spend — dollars and tokens per UTC day,
service, source and role (concept 2026-09-08e); claude appears twice
(transcript rows priced at list, otel rows at Claude Code's own estimate) and
the two are never added; n = rows in the window; refused under 5` — claude's
two rows are never added to each other, and a run under five rows prints
`refused` instead.

The rows exist only after **switch #23** (SP3's telemetry, 2026-09-08, gen
48). Its acceptance is the operator's own read-only check, not a task's:

```
systemctl --failed
systemctl is-active opentelemetry-collector egress-broker-openrouter egress-broker-seat
ss -ltnH | grep 4318
journalctl -u opentelemetry-collector -n 5 --no-pager | grep -c 'Everything is ready'
cat /etc/claude-code/managed-settings.json
systemctl show opentelemetry-collector -p User -p ProtectHome -p IPAddressDeny --value
```

expected: `0 loaded units listed`; `active` ×3; one line
`127.0.0.1:4318`; `1`; one top-level key `env` with SP3's eight variables;
`dalhaka`, `yes`, `any`. Rollback: `sudo
/nix/var/nix/profiles/system-47-link/bin/switch-to-configuration switch`
(gen 47, the pre-#23 generation) — a bare `switch-to-configuration switch`
activates but does not register a generation (session 22's lesson).

**The weekly limit has no durable source.** The 429 tombstones the backfill
lifts out of the transcripts land as `limit-events` rows, and
`report spend`'s last line tallies them (`limits: N rate-limit events
(…)`) — but the weekly percentage itself is screen-only: no export, API or
store row carries it. The scheduled **reset probe** stays the proxy — a
boolean at one instant — until a persisted source exists (claim
`claude-weekly-limit-unmeasured`).

**The manual OpenRouter activity export is retired for cost.** Decision
2026-09-05 answer 4 keeps the weekly download — the `openrouter-usage` rows
are the dollar of record, and the export remains the monthly
**reconciliation** against them (`d5-activity-export` restated the same way
in `docs/ledger/claims.toml`).

After one real session, verify the collector dropped every identity
attribute:

```
grep -c 'user.email' /var/lib/opentelemetry-collector/claude-*.jsonl
```

expected: `:0` per collector file (claim `otel-identity-drop-live`).

## The two tile rules that changed

Docs-only commits no longer turn the Helm board red:

- the **flake-check** tile is green when a recorded check covers a revision
  that differs from `HEAD` only in docs;
- the **drift** tile is green when `HEAD` is ahead of live only in docs.