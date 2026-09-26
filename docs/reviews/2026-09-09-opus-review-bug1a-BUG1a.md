---
plan_defect: implementer
plan_defect_secondary: wrong-fact
mutants_total: 0
mutants_killed: 0
mutants_outside_named: 0
model: opus
---
# Opus gate — seat run bug1a, task BUG1a — REJECTED

## Summary

The document's **central conclusion is true and I reproduced it independently**: `seat-submit`
is not on the host PATH, `tools/factory/seat/factory-task` carries no `--broker` anywhere, and
the `else` arm at `:429` launches `dsh-openrouter --model … --headless` direct to
`openrouter.ai`. Every task the driver has dispatched — including this gather task's own model
call — bypassed every broker. Five of the six `## Observed` commands reproduce; three of them
byte-for-byte. Every one of the ~20 `file:line` citations in `## Mechanism` is correct **except
the one the whole document turns on**.

It is rejected on three MAJORs.

1. The load-bearing citation is false. The document (and the commit body, which is what the
   ledger will carry) names `factory-task:362` as the `elif command -v seat-submit …` predicate
   and quotes that line's text. Line 362 is `if [ "$seat_arm" = codex ]; then`. The predicate is
   at `:378`. A Pro fix stage typed from this document is pointed at the codex arm.
2. The plan's numbered requirement 5 ("whether the seat lane's broker has ever served a request,
   **and what would make it**") is answered by reasoning, not measurement, against the Global
   Constraint that says a gather stage measures. The one command that answers it —
   `journalctl -u 'seat@*'`, which the seat never ran — shows two `seat@` jobs ran on 2026-09-08
   and **both died at boot with `EROFS … mkdtemp '/tmp/dsh-spill-XXXXXX'`**, before any model
   call. The document prescribes the `seat@` route as the fix direction without recording that
   the only `seat@` jobs this host has ever run failed on it.
3. The document frames brief §3 invariant 2 as something *a fix must not break*. By its own
   `## Mechanism` 3, that invariant **is breached right now**, and has been for every dispatched
   task. So is invariant 3. The document never says so, and the plan's own gloss of invariant 2
   is what let it not say so.

On the orchestrator's two "go further" questions, precisely and in the brief's own words:

**Invariant 2 — "No agent process holds a provider credential on disk or in its environment in
plaintext. Credentials are injected at an egress proxy." VIOLATED**, for every task the factory
driver has dispatched. `pkgs/dsh-openrouter/dsh-openrouter.sh:325` resolves
`key_file=${OPENROUTER_KEY_FILE:-…/openrouter/key}` and `:343` runs
`export OPENROUTER_API_KEY=$key` into the harness. Measured: `/home/dalhaka/.config/openrouter/key`
is a plaintext 73-byte file, `mode=600 owner=dalhaka`, readable by every process running as the
operator — which is every headless seat; and the run banner records the resolution.
The credential is not injected at an egress proxy; it is read from disk by the agent process and
placed in that process's environment.

**Invariant 3 — "Every byte leaving the machine crosses one chokepoint that can log the request
and refuse it." VIOLATED for dsh's traffic.** dsh (DeepSeek Harness) is a harness explicitly in
scope, brief §2. Its model calls left the machine from the host netns straight to
`openrouter.ai:443`. Nothing logged them — `/var/lib/egress-broker/seat/` has never held an
`audit.jsonl`, and the openrouter instance's last row is the agent lane on 2026-09-04 — and
nothing was positioned to refuse them.

**And the consequence neither the orchestrator nor the findings named.** The live seat policy
does more than log:

    "body_patch": { "openrouter.ai": { "merge": { "provider": { "data_collection": "deny",
                    "zdr": true } }, "path_prefixes": ["/api/v1/chat/completions"] } }

Because no seat request crossed the broker, **every DeepSeek seat request this operation has
made went to OpenRouter without the `data_collection: deny` / `zdr: true` provider directive**,
without the `allow: ["openrouter.ai"]` host restriction, and without the
`deny_paths … /api/v1/messages` refusal. The missing `usage.jsonl` is the cheapest of the four
consequences. This is a data-handling fact, not a spend fact, and it belongs in BUG1b's brief.

As a contract for a Pro fix stage: the shape is right and the defect site is right, but it is
not yet sound to type from — it points at a wrong line, it omits that the prescribed route has
a live boot failure on this host, and it understates the breach from "telemetry gap" to
"invariant". Those three are a short fix round, not a re-plan.

## Contract items

The section's numbered requirements ("What this stage must establish, each with the command and
its real output"):

| # | Requirement | Met | Evidence |
|---|---|---|---|
| 1 | Where a seat's model call actually goes; name the file and line that settles it | **partly** | Conclusion right, citation wrong — MAJOR-1. The direct arm is settled by `factory-task:429` (`else`) / `:437` (the command); the predicate is `:378`, not `:362` |
| 2 | Which instance writes `usage.jsonl`, under what path | yes | `nixosModules/egressBroker.nix:30` → `usage_log = "/var/lib/egress-broker/${name}/usage.jsonl"`; `pkgs/broker/policy.py:102-103`, `:174-206`, `:520-522` — all four citations verified correct |
| 3 | Whether that instance ran during the seat window (`systemctl status`, `journalctl`) | yes | `## Observed` 4 and 5. The `systemctl` half I could not re-run (barred to this gate); corroborated independently below |
| 4 | Whether the writing code is reached; if the broker served nothing, say so and stop | yes | It served nothing; the document says so and stops. Correct |
| 5 | The `/var/lib/egress-broker/seat/` question — has that broker ever served a request, **and what would make it** | **no** | First half measured and correct; second half is reasoning with no command, and is refuted as complete — MAJOR-2 |

Interfaces (the required shape): `## Observed` present, `## Mechanism` present with file:line,
`## Where the defect is` present and naming a single site, `## What a fix must not break`
present, `## Unmeasured` present with two `UNMEASURED:` labels. Shape: **met**. Content of the
last section: MAJOR-3.

Global Constraints: no behaviour changed (one file, a document — verified by the diffstat); no
module, package, test or check touched; the obvious fix is described, not applied. **Met**,
except "a gather stage measures rather than reasons" — MAJOR-2, MINOR-4, MINOR-5.

## Red before green

The section names no test: *"Tests … none — this stage adds no behaviour and no test."* There is
no assertion to make fail, so red-before-green is **not applicable** and its absence is not a
finding. The section replaces it explicitly: *"A findings file whose claims cannot be re-run is
the failure mode here, and the gate is instructed to re-run them."* I ran every command in the
document that this gate is permitted to run — six of eight — plus eleven more of my own. Results:

| Claim | Command | Reproduces |
|---|---|---|
| 1 | `find /var/lib/egress-broker -name 'usage*.jsonl'` | **yes**, empty, exit 0 |
| 2 | `find /var/lib/egress-broker -maxdepth 2 \| sort` | **yes**, byte-for-byte, all 9 lines |
| 3a | `stat -c '%n %y' …/openrouter/audit.jsonl` | **yes**, byte-for-byte (`2026-09-04 16:50:27.490403735 -0500`) |
| 3b | `tail -1 …/openrouter/audit.jsonl` | **yes**, byte-for-byte (client `10.100.3.2`, the openrouter lane's `namespaceAddress`, `hosts/core/lanes.nix:15`) |
| 3c | `date -d @1788558627.491594 …` | **yes**, `2026-09-04 16:50:27 CDT` |
| 4 | `systemctl status …` | **not re-run** — `systemctl` is barred to this gate. Corroborated instead: `/etc/systemd/system/` holds exactly `egress-broker-openrouter.service` and `egress-broker-seat.service`, no `cowork` unit (the document's claim holds); zero traffic since is corroborated by the seat instance having no `audit.jsonl` at all and the openrouter instance's last row being 2026-09-04 |
| 5 | `journalctl -u egress-broker-seat --since '2026-09-08 21:00'` | **substantively yes**; the paste is labelled "output (full…)" and is not full — MINOR-3. The inference drawn from it is wrong — MINOR-6 |
| 6a | `grep -E 'launching\|key from\|key file' ~/factory/runs/sp2/wave-group-1.log` | **substantively yes**; the real run returns four lines, the document pastes three — MINOR-3 |
| 6b | `grep -a '^seat:' ~/factory/runs/sp2/*.result` | **yes**, no lines, exit 1 |
| 6c | `command -v seat-submit` | **yes**, no lines, exit 1 |

## Mutants

**mutants_total 0, mutants_killed 0, mutants_outside_named 0.** The section names no assertion
and no mutant, by design ("none — this stage adds no behaviour and no test"), and there is no
executable artifact in the diff to mutate. Mutation testing is vacuous here and its absence is
not a finding; the re-run table above is the substitute the section itself prescribes.

## Checks

The section's acceptance is `lint`. All run in a fresh clone of `task/BUG1a` at `56c2d45`.

| Check | Command | Result |
|---|---|---|
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass**, exit 0 |
| lint gate | `nix develop -c githooks/pre-commit` | **pass** on the second run, exit 0, last line `render.test.mjs: all assertions passed`. The first run exits 1 with `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the regeneration is exactly one line — `BUG1a` and `2026-09-09-bugs.md` leaving the queue because the task is now done in history. That is the landing-time board update the orchestrator owns and the section forbids the seat to commit ("no board commit"). **Not a red check and not a finding against the seat.** |
| repomap | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | **clean**, exit 0 — `docs/bugs/` is not mapped, so `docs/MAP.md` is correctly absent from the diff |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | **silent**, exit 0 |
| ruff | n/a | no Python in the diff |

No red check.

## Touches and commit

`touches: docs/bugs/2026-09-09-broker-usage-capture.md`. The diff is exactly that file, 279
insertions, nothing else:

    docs/bugs/2026-09-09-broker-usage-capture.md | 279 +++++++++++++++++++++++++++
    1 file changed, 279 insertions(+)

Nothing outside `touches`. The plan file is untouched. No board commit. Exactly one commit,
`56c2d45`. The subject is **byte-identical** to the section's (`cmp` against the section's text:
identical). Both trailers present after a blank line: `Generated-By: dsh 0.1.2-rc.1 /
deepseek/deepseek-v4-pro-0813 (seat headless, factory run bug1a)` and `Co-Authored-By: Claude
Fable 5.1 <noreply@anthropic.com>`.

The body states the why and the defect site. It does **not** paste the green — MINOR-1 — and it
repeats the wrong line number — MAJOR-1. Two process notes on the run, neither the seat's doing,
in MINOR-7.

## Findings

### MAJOR-1 — the document's load-bearing citation is false; a fix typed from it is aimed at the codex arm

`docs/bugs/2026-09-09-broker-usage-capture.md:185-189` (and the commit body, verbatim):

    1. **The task launcher picks a path on `command -v seat-submit`.**
       `tools/factory/seat/factory-task:362` —
       `elif command -v seat-submit >/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then`

The quoted text is not at `:362`. In the branch under review:

    362: if [ "$seat_arm" = codex ]; then
    378: elif command -v seat-submit >/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then
    429: else
    430:   factory_log "launching dsh-openrouter --model $model --headless in $ws …"
    437:         timeout -- "$timeout_s" dsh-openrouter --model "$model" --headless "$brief"

    $ grep -n 'command -v seat-submit' tools/factory/seat/factory-task
    378:elif command -v seat-submit >/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then

Line 362 is the *codex* arm's predicate. The error is repeated at `:235` ("the `else` branch of
the `seat-submit` presence test at `:362`") and in the commit message, which is where it will
outlive this branch. The section's own test is that a claim carries "that command's real
output"; this one carries a quotation that the named line does not contain.

The defect *site* — `:429` — is right, and I confirm it independently:

    $ grep -n -e '--broker' tools/factory/seat/factory-task
    (no lines)
    $ command -v seat-submit ; echo $?
    1

`seat-submit` is on the `seat@` unit's PATH only (`nixosModules/seatLane.nix:206`, inside the
`path = [ … ]` at `:202-207`) and is not in `environment.systemPackages` on core, so the `elif`
at `:378` short-circuits false and `:429` always runs. Both of the document's supporting
citations for that are correct (`seatLane.nix:202-207`, `factory-wave:192-194`).

The fix: `:362` → `:378`, in the document and in the commit body.

### MAJOR-2 — requirement 5's second half is reasoning; one command shows the prescribed route has never once booted on this host

The section's requirement 5: *"Establish whether the seat lane's broker has ever served a
request, **and what would make it**."* The document answers the first half from the absence of
the file (`:37-38`, correct) and the second half at `:263-267` by prescribing the `seat@` route,
with no command:

    The correct fix therefore routes the task through the `seat@` unit (the
    spool/`seat-submit` arm), so the request crosses the broker's netns with the
    placeholder key, exactly as `seat-run.py` and `seatLane.nix` already implement.

`journalctl -u 'seat@*'` — the direct measurement for requirement 5, absent from the document —
shows the `seat@` route has been exercised twice and has never once reached a model call:

    Sep 08 21:26:56 core systemd[1]: Started Operator seat job 20260909-022656-2b03ec behind its own egress broker.
    Sep 08 21:26:56 core seat-run[1575901]: http://10.100.4.2:43210
    Sep 08 21:27:13 core systemd[1]: Started Operator seat job 20260909-022712-d7a01d behind its own egress broker.
    Sep 08 21:27:17 core seat-run[1576466]: dsh-openrouter: deepseek/deepseek-v4-pro-0813 via https://openrouter.ai/api/v1, workspace-write, credential: placeholder (broker injects), workspace /home/dalhaka/nixos-agent-env
    Sep 08 21:27:17 core seat-run[1576466]: Error: dsh: plugin tree failed to load: failed to apply loader entry include (cordis:include): failed to apply loader entry spill-local (@deepseek-ai/dsh-spill-local): EROFS: read-only file system, mkdtemp '/tmp/dsh-spill-XXXXXX'
    Sep 08 21:27:17 core systemd[1]: seat@20260909-022712-d7a01d.service: Main process exited, code=exited, status=1/FAILURE
    Sep 08 21:27:17 core systemd[1]: seat@20260909-022712-d7a01d.service: Consumed 5.546s CPU time … 983B incoming IP traffic, 411B outgoing IP traffic.
    Sep 08 22:55:57 core systemd[1]: seat@20260909-022656-2b03ec.service: Consumed 5.630s CPU time over 1h 29min … 53.5K incoming IP traffic, 25K outgoing IP traffic.

Three facts this changes for BUG1b, none of them in the document:

- **`seat@` jobs have run, and moved IP traffic, and still produced no broker audit line.** The
  document's framing — "no seat request ever crossed a broker" *because* the spool was never
  used — is not the whole account. The spool *was* used, twice, by the operator; the jobs died
  at boot.
- **The credential half of the seat path is proven to work.** `credential: placeholder (broker
  injects)` is in that journal. That is a measured green flag for the fix direction and it is
  worth more to BUG1b than the paragraph of reasoning that replaced it.
- **The prescribed route has an open boot defect on this host.** The plan's own Assumption 3
  argues headless is unaffected (spill-local is not loaded in the headless profile) and both
  failures above are `profiles/web/#spill-local` — so the fix is probably still viable. But the
  document neither cites that assumption nor measures a headless `seat@` boot, and it does not
  tell the fix stage that the route it names has a zero-for-two record. Either measurement or an
  `UNMEASURED:` label was owed here; neither is present.

### MAJOR-3 — the document reports a live invariant breach as a future risk

`docs/bugs/2026-09-09-broker-usage-capture.md:250-256`:

    ## What a fix must not break

    Brief §3 invariant 2: **the broker's injected credentials are never visible to
    the network-capable process.** Today the broker injects the real
    `Authorization` header at egress …

Two problems, one of them the plan's.

**The quoted invariant is not invariant 2.** `docs/brief.md:69-70` reads:

    2. No agent process holds a provider credential on disk or in its environment in
       plaintext. Credentials are injected at an egress proxy.

The gloss in the document is the plan section's own wording, copied verbatim from its Interfaces
line, so the seat did as it was told — hence `plan_defect_secondary: wrong-fact`. But the gloss
is a statement about the broker path only, and the real invariant is a statement about *every
agent process*.

**Under the real text, the invariant is breached today**, by the very mechanism the document
itself establishes at `:197-203`. `pkgs/dsh-openrouter/dsh-openrouter.sh:325` resolves the key
file, `:343` runs `export OPENROUTER_API_KEY=$key`, and the run log records it:

    dsh-openrouter: deepseek/deepseek-v4-pro-0813 via https://openrouter.ai/api/v1, workspace-write, key from /home/dalhaka/.config/openrouter/key, workspace /home/dalhaka/factory/ws/bug1a/BUG1a

    $ stat -c '%n mode=%a owner=%U size=%s' /home/dalhaka/.config/openrouter/key
    /home/dalhaka/.config/openrouter/key mode=600 owner=dalhaka size=73

That is an agent process holding a provider credential on disk in plaintext and in its
environment in plaintext, not injected at an egress proxy. Invariant 3 ("Every byte leaving the
machine crosses one chokepoint that can log the request and refuse it") is breached in the same
stroke, for dsh, a harness named in scope at `docs/brief.md:58-59`: nothing logged those bytes
and nothing could have refused them.

The document says none of this. It has "what a fix must not break" and no "what is broken now".
For a document whose only job is to be the contract a fix is typed from, that inverts the
severity: BUG1b is not adding telemetry, it is closing two invariant breaches.

**And a fourth consequence the document does not reach at all.** The live seat policy
(`/nix/store/v3gv7f3ib89da1dl9qk5jxc1968l575i-egress-policy-seat.json`, the `BROKER_POLICY` of
the running unit) is not only a logger:

    "allow": ["openrouter.ai"],
    "body_patch": { "openrouter.ai": { "merge": { "provider": { "data_collection": "deny", "zdr": true } },
                    "path_prefixes": ["/api/v1/chat/completions"] } },
    "deny_paths": { "openrouter.ai": { "path_prefixes": ["/api/v1/messages"] } },

Every seat request bypassed all three. So every DeepSeek seat request this operation has made
reached OpenRouter **without the `data_collection: deny` / `zdr: true` provider merge**, without
the host allowlist, and without the `/api/v1/messages` refusal. That is a data-handling
consequence, and it is larger than the missing `usage.jsonl` the bug was opened for. It belongs
in BUG1b's brief.

### MINOR-1 — the commit body pastes no green

Step 3 of the section: *"`nix develop -c githooks/pre-commit` (the lint gate is the only check a
docs-only change needs; **paste its last line**)."* The body pastes no line from the hook. The
gate ran it and it is green (Checks above), so nothing is concealed; the step is simply unmet.

### MINOR-2 — the defect site's command is one line off

`:230-233` and `:189` present `dsh-openrouter --model "$model" --headless "$brief"` as the
content of `:429`. Line 429 is `else`; the log line is `:430` and the command is `:437`. Naming
the `else` as the site is defensible shorthand — the orchestrator uses it too — but the quoted
command is not on the quoted line.

### MINOR-3 — two outputs presented as verbatim are edited

`:109` labels its journal paste "output (**full**; only start/stop, no request lines)". The real
output carries one more line, dropped from the paste:

    Sep 08 22:55:57 core systemd[1]: egress-broker-seat.service: Consumed 13.865s CPU time over 1d 15h 5min 6.521s wall clock time, 82.1M memory peak, 27.4M read from disk, 932K written to disk.

`:147` pastes three lines for the `grep`; the command returns four — the fourth is a false
positive on `key file` inside the seat's own prose ("Let me read the key files first."). Neither
edit changes a conclusion; both break the rule that the paste is the command's real output, and
§5's is labelled "full" while it is not.

### MINOR-4 — three claims carry no command

- `:173-177` — "The same launch line appears in `~/factory/runs/sp1/wave-group-1.log` (SP1
  itself) and `~/factory/runs/sp1b/` (SP1b)". True in substance (I ran it: the `sp1` log carries
  the identical `launching dsh-openrouter …` line; `sp1b` has no `wave-group` log at all, but
  `SP1b.log` carries the `key from /home/dalhaka/.config/openrouter/key` banner), but no command
  and no output are given, and the second path names a directory that does not contain what the
  sentence says it does.
- `:139` — "The wave-2 run … was dispatched 21:23". True (`~/factory/runs/sp2/run.meta`:
  `launched: 2026-09-09T02:23:36Z` = 21:23:36 CDT), no command given.
- `:98-101` — the `## Observed` 4 narrative, treated in MINOR-5.

Per the plan's Global Constraints, "A claim without a command is a guess and must be labelled
one."

### MINOR-5 — the cowork unit's absence is explained wrongly

`:99-101`: "There is no `cowork` service unit (Cowork's broker is provisioned differently — see
`hosts/core/default.nix`, the `brokerInstance "cowork"` comment)." It is not provisioned
differently; it is off. `hosts/core/default.nix:104` is `cowork.enable = false`, and
`nixosModules/cowork.nix:173` declares `egress-broker.instances.${cfg.brokerInstance}` inside
that module's enable-guarded `config`, so with `enable = false` the instance is never declared
and no unit is rendered. The `brokerInstance = "cowork"` at `hosts/core/default.nix:98` belongs
to `claude-managed-settings`, which is also `enable = false`.

### MINOR-6 — the right conclusion about SP1 being live, drawn from evidence that does not support it

`:133-135`: "Two policy.py store paths appear across the restart … The switch that put
`4jy9nhhnc…` live is #23." The conclusion is **true** — but not from that journal. mitmdump
flushes its `Loading script` line at exit, so each line is attributed to the process that just
stopped: the line logged at 22:56:11 belongs to the process started 22:55:58 (`4jy9nhhnc`, SP1's),
and the line logged at **22:56:18 belongs to the process started 22:56:12 and names
`f5azl4d1…` — the pre-SP1 script**. The currently running process (started 22:56:19) has not
flushed its line at all, so the pasted output ends on the *old* script and says nothing about
what is live. The claim is settled instead by a command the document does not carry:

    $ grep -n 'ExecStart' /etc/systemd/system/egress-broker-seat.service
    13:ExecStart=… mitmdump … -s /nix/store/4jy9nhhnc3knn4vqjd41ssiclz5lc0g3-policy.py

SP1's policy *is* live on both instances, and `readlink /nix/var/nix/profiles/system` →
`system-48-link` as the document says. Right answer, wrong proof.

### MINOR-7 — two process notes on the run itself, neither the seat's doing

- **The routing decision the plan rests on was discarded.** `~/factory/runs/bug1a/run.meta` and
  the result record `model: deepseek/deepseek-v4-pro-0813`, `rung: 2`. `docs/ledger/routing.toml`
  rung 1 for `implement/docs/any` is `deepseek/deepseek-v4-flash`; rung 2 is the fix round, and
  BUG1a is a first attempt. The plan's Dispatch says in terms: *"do not override the model on the
  launch line, or the routing decision this plan rests on is silently discarded."* It was. Not a
  gating fault — Pro is the stronger model and the work is the better for it — but the plan's
  own premise (that a `docs` kind routes a gather stage to Flash) is now untested, and the
  operator should know the first gather stage was not the experiment the plan describes.
- **This task demonstrated its own bug.** `~/factory/runs/bug1a/wave-group-1.log`:
  `factory-task: launching dsh-openrouter --model deepseek/deepseek-v4-pro-0813 --headless …`
  and `key from /home/dalhaka/.config/openrouter/key`. The gather task that documented the
  bypass was itself dispatched through it, at 956 events and 2.33 M cached tokens that no broker
  recorded.

## Verdict

**REJECTED.** Three MAJORs, all of them a short fix round on one file — no re-plan, no re-gather.
BUG1a's measurement is largely sound and its defect site is correct and independently confirmed;
what it needs before BUG1b can be typed from it is:

1. `:362` → `:378` in the document and in the commit body (MAJOR-1).
2. Requirement 5's second half answered with `journalctl -u 'seat@*'` and its real output: the
   two `seat@` jobs, the `credential: placeholder (broker injects)` banner that proves the
   credential half of the route, and the `EROFS … /tmp/dsh-spill-XXXXXX` boot failure — with
   either a measured headless `seat@` boot or an `UNMEASURED:` label saying the prescribed route
   has never completed on this host and why the plan's Assumption 3 expects headless to differ
   (MAJOR-2).
3. A `## What is broken now` statement quoting brief §3 invariants 2 and 3 in their own words,
   with the `export OPENROUTER_API_KEY=$key` at `dsh-openrouter.sh:343` and the `stat` of the key
   file as its evidence, and the seat policy's `body_patch` / `allow` / `deny_paths` as the
   consequences that outrank the missing `usage.jsonl` (MAJOR-3).

`plan_defect: implementer` — the wrong line number and the unmeasured answer to a numbered
requirement are the seat's, against a section that stated both duties plainly.
`plan_defect_secondary: wrong-fact` — the section's Interfaces line glosses brief §3 invariant 2
as "the broker's injected credentials are never visible to the network-capable process", which is
not what invariant 2 says, and that gloss is why the document reports a live breach as a future
risk.
