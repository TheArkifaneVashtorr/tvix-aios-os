# Draft checklist — Appendix A's eight questions per section (draft-0.md, 2026-09-27)

Q1 mutant per assertion · Q2 discriminating fixture per fixture · Q3 rules not spellings · Q4 interfaces (what it reads, what it emits on each failure, who consumes) · Q5 facts pasted with commands, anchors not line numbers · Q6 no step's output fails its own acceptance grep · Q7 fix round / re-plan carries every item (n/a: this is neither) · Q8 `factory-brief <draft> <KEY>` is the whole contract (verified: each key's brief reproduces its section through the `**commit subject:**` line; SD8's fenced `## ` line was the one truncation found and removed).

## SD1 — the ladder is data
1. yes — Tests rows 1–9 each name the one-line change (rung-N → last row; top-rung fallback; specificity without class; fallback → model; each check rule deleted; models reading rung 2; a claim row dropped).
2. yes — three rungs with distinct (model, effort); the class row later than the `any` row it must beat; rung 2 without fallback beside rung 3 with one; the two-variable vs zero-variable fixtures differing only in effort; the committed table's `--rung 2 orchestrate` (`top 1`); the inline-comment fixture.
3. yes — the ladder key is a rule over five fields; validation rules r1–r7 are stated as rules with exact messages; the class enum is one tuple shared by name and order.
4. yes — both lookups' stdout/stderr/exit (0/3/4), the messages, the file resolution, the consumers (factory-task/review, seat-submit drive, the dark factory, the hook guard's tolerant read).
5. yes — nine facts, each with its command; anchors are text (`unknown key`, `cur[key] = val`, `Change rows here, nowhere else`); line numbers appear only as the command's own output beside the anchor.
6. yes — the routing comment is a whole line (an inline `#` would fail both parsers — checked and pinned in row 6); `claims.py validate --today` is run in Step 5 and Step 6; `factory-unit`'s render test reads `models`, unchanged by construction (row 8).
7. n/a.
8. yes — brief = GC + Assumptions + SD1 (3,780 words): the fixture table, the rows table, the rules and the messages are all inside the section.

## SD2 — the technical class
1. yes — rows 1–10 (tie → later class; last-row-wins per path; default to first row; no `/` crossing; reorder; drop duplicate rule / absent-table error; drop grouping; drop the cap; exit 0 on unknown key; omit the json field).
2. yes — one path per class for the tie; a path two rows match; an unmatched path; a nested path; three tables (duplicate, empty globs, absent); the long-key plan against the cap.
3. yes — first matching row, most paths, earliest on a tie, `fnmatchcase` — a rule, and the table's globs are policy in the repo.
4. yes — `load_task_classes` → list/None/ValueError with exact reasons; `check`'s line; the brief line and its omission rule; the `class` subcommand's exit codes; consumers (SD7's `factory_py`, SD9's fence).
5. yes — the table is MISSING (command shown); the brief's 1,275 bytes and the 1,400 cap; the regexes' anchors; `evidence-unit` copies `docs/ledger`.
6. yes — the brief stays under the hook's cap by rule (row 8); `HEADING_RE`/`FIELD_RE` are untouched so no plan re-parses differently; the fixture plan's headings live under `tests/evidence/fixtures/plans/`, outside the plans glob.
7. n/a.
8. yes — the toml is printed whole in the section; the rule, the messages and the fixture plan's three tasks are named.

## SD3 — the shared rule file, orchestrator guard
1. yes — rows 1–8 (keep literals; fall back when absent; skip unknown kinds; hardcode push; hardcode the alternation; drop a family from the loader; semantic drift caught by the 100+ tests and the 442-row sweep; a forking loader breaks the timing tests).
2. yes — two directories with one in the file; the same command under two files (`git push`); `systemctl-refuse start` only; one bad line per malformed shape.
3. yes — kinds are a closed set with a grammar; a violation is a fault; the guard's semantics are unchanged (a refactor of where lists live, not what they mean).
4. yes — the file path and its override, the fault contract (stderr line + deny + exit 0), `--print-rules`'s canonical form; consumers: the orchestrator guard now, hook-guard in SD4.
5. yes — the literal arrays' anchors, the sweep header, the copy lines in `flake.nix`, the empty `.claude/settings.json` of this snapshot, the env-flag test idiom. The 45-line count was corrected from an arithmetic slip during drafting (20 non-verb lines + 25 verb words).
6. yes — the sweep must stay stderr-silent: the fault path prints on stderr only when the file is bad, which no sweep row can cause (the file is committed and sound); `tests/lint/bats-and-chain.sh` forbids `] && [` chains — the new tests use one `[ … ]` per line.
7. n/a.
8. yes — the file's full content and the loader's contract are in the section.

## SD4 — hook-guard reads the rule file; the sweep against both
1. yes — rows 1–11 (skip `-c`'s value; drop `..` collapse / ancestors; drop the glob fallback / parent rule; exempt to end of command; allow on a missing field; absolute-only resolution; allow when rules are missing; a different family order; a loosely ported rule vs the 442 rows; drop `--rules`; a raise on a hostile token).
2. yes — `git -c a=b -C . push`; `../plans`; `rm -rf docs`; the glob spelling and the allowed sibling `worktrees/x`; the newline after a commit message; the field-less payload; the relative override path; the 442 rows.
3. yes — the port states every rule as the orchestrator guard states it (tokenise; every token; ancestors; destination-aware families; clause-local flags), fed by the shared file; the sweep parity is the proof, not an enumeration.
4. yes — `--rules` resolution, the load-failure contract (deny every tool with a named reason), the edit/write fail-closed on missing fields, messages byte-identical, exit 0 always, the wrapper's argv; consumers: the seat's every bash/edit/write call.
5. yes — the seams (`_bash_verdict`, `_edit_verdict`, the edit/write arm), `hook_command`'s jq line, `hookGuard`/`DSH_HOOK_GUARD`, the bats idiom, the sweep header, the runbook bullet.
6. yes — `host-core` asserts `guardPython` is python3Minimal: the port stays stdlib (`re`, `os`, `json`, `tomllib`); the 400-char stderr record is kept; the deny JSON stays one line.
7. n/a.
8. yes — the biggest section (3,418 words); the port's rules are all in the Interfaces; the risk (fix rounds on parity) is stated in the Waves/Decisions text, which the seat does not see — the section itself names the parity test's failure output so the seat can iterate.

## SD5 — the spool
1. yes — rows 1–12 (keep the marker; key on job.json; delete a rule; leave a marker; read the brief; mark ready early; call stop; accept both flags; mark on every path; drop the timeout kwarg / swallow the exception; each eval assertion's removal; drop the path unit / skip v3–v4).
2. yes — the port boundaries 43199/43200/43299/43300; `evil` beside a complete job; the raising fake; the `rocket` job; the ordering assertion inside `_mark_ready`.
3. yes — validation v1–v11 in a fixed order with exact reasons; the marker-file protocol (every marker consumed); `InaccessiblePaths` makes the premise true by construction.
4. yes — `seat-submit` flags and exits (2/124), `seat-spool`'s arguments, outputs and always-0 exit, `seat-run`'s timeout contract (124), the units' rendered properties, the VM steps; consumers: the spool (markers), `factory-task` (SD7's `--spool`), `seat-eval`.
5. yes — module anchors (tmpfiles, ExecStart, ReadWritePaths, InaccessiblePaths, polkit), seat-submit's two systemctl calls, seat-run's `subprocess.run` line, the eval idiom, the VM idiom, the tests' fixtures, the board's `nix run` finding.
6. yes — `seat-eval` is the acceptance and its new assertions are listed with the exact literals (`ReadWritePaths` pinned); the `ExecStart` regex admits exactly the form the module renders (a store path, the binary, one flag); the VM's grep for `refused` names the reason v3 produces first (`missing key workspace`) — the test's grep alternation covers the three reasons the fixture could hit.
7. n/a.
8. yes — everything (validation table, unit definitions, VM steps) is inside the section.

## SD6 — the drive job
1. yes — rows 1–10 (write brief.txt; a built-in default; fall back on a failed lookup; accept one of the pair; drop the skill check; accept port 80; omit `--model`; accept any route; per-mode ReadWritePaths / drop the precondition in the VM).
2. yes — the fake `route.py` printing `m/orch` (no default carries it); the same home with and without the skill file; 1023/1024; the enum's two arms; the web job's rendered property beside the drive job's.
3. yes — the lookup is the table (never a default); the precondition is a file's existence and readability, not a name list; the port is validated as an integer range.
4. yes — every exit (2/3), the lookup's argv and fallbacks, job.json's shape, seat-run's argv, spool v12; consumers: seat-run, the spool, the operator's command.
5. yes — the mode choices and web argv anchors, the wrapper's usage line and `model_explicit`, `warn_missing_payload`, the orchestrate row's absence today, the interpreter, the board's `nix run` line.
6. yes — the VM's `machine.fail` on the missing skill and the unchanged job-dir count are post-state probes; `seat-unit`'s pytest names.
7. n/a.
8. yes — after the README move, the section is self-contained and disjoint from SD7.

## SD7 — the climb
1. yes — rows 1–10 (an `r` anywhere; always rung 1; ignore the class; fall back to the top rung; escalate before honouring explicit; review at rung 1 for every key; always pass `--spool`; drop `~` expansion; reorder a toml row; treat exit 4 as done).
2. yes — `P3Ar2b`; distinct models per rung; the class row's distinct model; the two-rung ladder; the one-rung review ladder; the `K1r K2` chain.
3. yes — the rung is a grammar over the key (CHAIN_RE), the class comes from the graph, escalation is a rule on the lookup's exit and message.
4. yes — the four lib functions' outputs and failure behaviour, the `.result` block for escalation (every line), exit 4 in both scripts, the launch line, `SEAT_SPOOL`; consumers: factory-wave (the summary), SD9 (the lines), the operator (the launch line).
5. yes — the call sites, the exit-code case, CHAIN_RE, dark-factory's invoke line, `--factory-args`, `resolve_repo_name`, the argv line, the fake-seat idiom.
6. yes — `route:` keeps T2's regex form on the normal path; the `launch:` line is a free-text line T2's ingest does not read (SD9 says so); shellcheck is in Step 4.
7. n/a.
8. yes — the escalation block is printed whole in the section; the README paragraph for the driver is here too.

## SD8 — `--prior`
1. yes — rows 1–7 (drop the block; select `yes` rows; ignore the runs-dir fallback; append after the rules; pass the brief without the block; choose the oldest; ignore a missing prior; cat the log).
2. yes — one survivor beside two killed mutants; two results with `touch -d` mtimes; the mode-000 log; the review absent vs present under the runs dir.
3. yes — the default prior is "the newest result of any other member of the chain root", never a list of keys; the review path is a glob with one fallback.
4. yes — `--prior`'s exit 2, the default and its disable flag, the block's exact composition (regexes), `--prior-file`'s exit 2, the `prior:` line; consumers: the seat (the brief), SD9 (the line).
5. yes — the review shape's anchors (`### MAJOR-1 —`, the mutant table header, `**no**` count 2), the one filename shape over 164 files, the `diffstat:`/`usage:` order, `.review.md`.
6. yes — the block's heading is written inline in the Interfaces because `factory-brief`'s extractor stops at any `## ` line (found by running it: the first draft's fenced heading truncated SD8's own brief; corrected).
7. n/a.
8. yes — the block template, the regexes and the paths are in the section.

## SD9 — the record
1. yes — rows 1–8 (drop a field from the entry; widen `escalate`; default rung 0; median → mean; `>` for `>=`; divide by zero; drop rung from the key; forward without `--store`; drop the proxy sentence).
2. yes — one row per enum arm; the three `.result` fixtures; the skewed 900/9000 values; exactly five rows; zero approved; two rows differing only in rung.
3. yes — the group key is a tuple rule; role derived from the route string by position; the n-gate is one threshold.
4. yes — the fence entries with classes, the producers with defaults, the report's lines (definitions of every column), exit 0/2; consumers: `evidence report ladder`'s readers (the operator, the routing commits' bodies).
5. yes — the two files MISSING today (commands), the telemetry plan's line anchors, `plans_report`'s signature and `refused` line, the CLI forwarding, the fixture layout.
6. yes — the header line names the class proxy (row 8) — the amendments' "proxies are declared"; the `launch:` line is never ingested.
7. n/a.
8. yes — everything the seat needs, including that the files it edits come from T1/T2 (the section says which plan sections define them; the seat runs after they landed).

## SD10 — the driving skill (dsh-harness)
1. yes — rows 1–5 (a model id in a verb; the word `rung`; a typo in a script name; a description that claims a plan; the node-test count).
2. yes — `planning`'s description beside it (the two-claimants grep); the three scripts' existence.
3. yes — the four verbs are exact commands; the "never" list is the spec's §7 verbatim; the wording rule is a grep over the two files.
4. yes — what each verb runs, what the driver does on exit 4 and on any failure, what it never does; consumers: the operator talking to the drive seat.
5. yes — the harness tree is absent here (said, with the command); the facts come from P13's touches and the H-plan's Global Constraints and Interfaces, each with its command.
6. yes — the harness gate must print nothing: the skill avoids model ids, effort words and the four words; the description claims neither a spec nor a plan.
7. n/a.
8. yes — the verbs, the never-list and the wording rule are in the section; the seat reads the gate first (Step 1).

## Self-score (rubric §5.1), with reasons

| row | score | reason |
|---|---|---|
| 1 spec coverage | 3 | every spec item mapped to a task or an `out:` with a reason; the spec's two wrong sentences named |
| 2 correct facts | 2 | every fact carries its command and anchor text; two arithmetic slips were caught and corrected during drafting (45 rule lines; the inline-comment trap), which is why this is not a 3 |
| 3 self-contained sections | 2 | `factory-brief` reproduces every section whole; SD4's port is specified as rules, not code — a blind seat still has to write ~400 lines of Python from the Interfaces |
| 4 TDD discipline | 3 | a red command with its expected red output per task; green by check name; the docs task's red is the artefact's absence |
| 5 mutants and fixtures | 3 | one mutant per assertion, one discriminating fixture per row, in every table |
| 6 interfaces and error contracts | 3 | exit codes, exact messages, every producer and consumer, the failure behaviour of both guards, the spool's validation order |
| 7 rules not enumerations | 2 | the class rule, the rung grammar, the spool's validation and the escalation are rules; SD4 necessarily carries the orchestrator guard's verb families (a data file both read) — the sweep parity is the proof |
| 8 waves, touches, conflicts | 3 | both forms run and pasted; explicit `touches`; every cross-plan hit sequenced; the SD6/SD7 overlap removed |
| 9 invariant awareness | 3 | §3.2/3.3/3.5 named where they bind; `/run/dbus` is a narrowing; no key, no widening |
| 10 operator steps and rollback | 3 | ten steps, one command each, acceptance probes, the predicted closure delta, the rollback generation |
| 11 anticipation | 3 | every row of §4 answered; the computed hold (stale claims) found and given a command |
| 12 economy | 2 | 20.7k words for ten tasks; the sections restate nothing across each other, but Interfaces and Tests overlap by the format's design |
| 13 format and graph compliance | 3 | `check --draft` exit 0 (both forms); real check names; byte-exact subjects match acceptance; no typed heading under the plans directory |
| 14 judgement calls | 3 | ten decisions each with the alternative; three questions, each with recommendation and default |

Total 38 / 42.
