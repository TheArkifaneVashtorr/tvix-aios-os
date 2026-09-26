# The debug sweep: one command from found bugs to a reviewed batch — design

**Status:** draft, 2026-09-23. Operator answers taken the same day: one command
run by hand (a script now, a devShell CLI once it matures), investigations on
`claude -p` with Sonnet, a light run record, never a fix.

## 1. The premise

Every worker here finds bugs: seats, gates, planners, Sonnet agents and the
orchestrator. Only the orchestrator records them. `docs/ledger/bugs.toml` holds
26 rows (9 open), and every one was typed by hand in a commit. The machine
signals nobody reads until someone looks cover 14 days to 2026-09-23:

| signal | where | 14 days |
|---|---|---|
| seat runs failed or partial | `derived/tasks` `error_class` | ~97 (probe-mismatch 24, probe-missing 19, no-result-line 19, template-echo 4, …) |
| gates rejected | `derived/gates` | 201 |
| checks failing | `checks`, `ok=false` | 29 (flake-check 9, unit 8, …) |
| open bugs with no task | `bugs.toml` `task = ""` | 4 today |

A worked example from today. EV21 (run `s37ev`) ended `no-result-line` after
51 minutes. Its seat's mutant script was refused with the message *plan files
change only through the Edit and Write tools*. That is the generic fallback
reason in `tools/orchestrator-guard.sh:770-775`, and it fired on a `cp` that
touched no plan. The seat spent the rest of its budget puzzling over the wrong
message. Diagnosing it took four hops: the `.result`, the session transcript,
the guard source and the fallback. None of the hops needs judgement a script
cannot hand to a model. The sweep exists to do those hops for every such
failure, in bulk, and put the answers in front of the operator at once.

## 2. The shape

Two verbs, one folder, one report.

**2.1 `tools/debug/bug-note "<symptom>" [--evidence <path | run/KEY | commit>]`**
appends one JSON line to `~/factory/debug/inbox.jsonl`: time, the reporter
(`$FACTORY_SEAT`, the agent label, or `operator`), the symptom and the
evidence. It is cheap enough for any worker to call mid-task and never touches
the repo. Seat briefs, gate prompts and planner prompts gain one line telling
them to call it for a defect outside their task. Recording it never counts as
fixing it.

**2.2 `tools/debug/investigate [--since <date>] [--limit N] [--dry-run]`** is the
one command.

1. **Harvest.** Unprocessed inbox lines, plus the signals in §1 since the last
   batch: failed and partial `derived/tasks` rows grouped by `error_class`,
   `checks` failing on a commit that main still carries, and open bug rows
   with no task. Rejected gates are *not* harvested. Rejections are the gate
   working, and their fixes already have a path (the fix round).
2. **Deduplicate.** Each item gets a signature: the error class plus key for
   seat runs, check name plus first failing line for checks, the bug id, or a
   normalized symptom for notes. Items whose signature matches an open
   `bugs.toml` row, or a diagnosis in an earlier batch, are folded in as more
   evidence, not re-investigated. Seven `probe-missing` partials are one item
   with seven pieces of evidence.
3. **Investigate.** Each item gets one `claude -p --model sonnet` run in a
   throwaway clone under `~/factory/debug/<batch>/<ITEM>/ws`. The prompt
   carries the four systematic-debugging phases: reproduce, compare with a
   working case, test one hypothesis at a time, and only then propose. It may
   read, build, run tests and try mutants in the clone. Its tool allowlist
   excludes commits, pushes and every path outside the clone and the run's
   read-only evidence (`~/factory/runs`, `/var/lib/evidence`). At most three
   run at once, so a large batch stays inside the subscription's 5-hour window
   (nine parallel runs exhausted it on 2026-09-11).
   **Rungs.** Rung 1 is Sonnet. An item that ends `unknown`, or `probable`
   with an impact in the batch's top third, climbs to rung 2, a fresh Opus run
   that reads rung 1's diagnosis as its prior (the factory's `--prior`
   pattern) and is told what rung 1 could not show. There is no rung 3: an
   item still `unknown` after Opus goes to the report as `unknown` with both
   rungs' evidence. That is an honest answer the operator can act on (for
   example, by adding logging). The rung and model of every diagnosis are
   recorded in its `.result`.
4. **Diagnose.** Each run ends by writing `<ITEM>.diagnosis.json`: symptom,
   repro command (one that exits 0 while the defect exists, the `bugs.toml`
   `repro` convention), root cause with `file:line` evidence, a confidence
   (`confirmed` = reproduced and the cause shown, `probable`, `unknown`), the
   proposed fix in prose, and a draft task section in the plan format with
   touches, acceptance, a red-first test and mutants. A draft that fails
   `tasks.py check --draft` is marked `draft-invalid` and kept, not dropped.
5. **Report.** One Opus pass merges the diagnoses into
   `docs/diagnoses/<date>-batch.md`. Items that share a root cause are merged
   (several symptoms, one cause, one proposed task). The report is ordered by
   impact (occurrences × cost of the failure) and ends with the one question
   per item the operator must answer: *launch, hold, or drop*. The Opus pass
   invents nothing. Every claim in the report cites a diagnosis file.

**2.3 The run record.** `~/factory/debug/<batch>/` holds `batch.meta` (start,
harvest window, item count, the command line), one `<ITEM>.log`, and one
`<ITEM>.result` per item with status, confidence, wall time and the
`claude -p` usage (tokens and cost from `--output-format json`). An
interrupted batch resumes: items with a `.result` are skipped. It lives outside
`~/factory/runs/` on purpose. Everything there is ingested as seat tasks and
listed as in flight, and diagnoses are neither. The usage rows land in the
evidence store as their own kind, so what debugging costs is measured like
everything else.

## 3. The operator's part

The sweep proposes and never acts. The operator reads the batch report and
marks each item launch, hold or drop. For the launched items the orchestrator
writes the `bugs.toml` rows and the task sections (agents cannot write under
`docs/superpowers/plans/`, and the ledger stays one reviewed commit), runs
`tasks.py check`, and dispatches them as one wave. Dropped and held items are
recorded in the report's front matter so the next batch does not raise them
again.

## 4. What it must not do

- Commit, push, or edit any file outside its clone and `~/factory/debug/`.
- Write `bugs.toml` or a plan file. Those are the orchestrator's, after the
  operator's word.
- Re-investigate a signature that already has a diagnosis or an open bug row,
  unless `--recheck <signature>` names it.
- Present a `probable` or `unknown` diagnosis as `confirmed`. The repro command
  is what makes a diagnosis confirmed, and it is run, not quoted.

## 5. Acceptance

- `bug-note` from inside a seat, a Sonnet agent and the operator's shell each
  append a line; a malformed call is refused with one line and appends nothing.
- `investigate --dry-run` over the live store prints the harvested items and
  their signatures without starting a model. The seven-plus `probe-missing`
  partials fold into one item.
- A real batch over today's backlog produces a report in which the EV21 item
  names `tools/orchestrator-guard.sh` and the fallback reason, with a repro
  that exits 0 on the current tree.
- Killing the command mid-batch and re-running it skips finished items.
- After a batch, `git status` in the repo is clean apart from the new report,
  and no commit exists that the operator did not make.
- The batch's `claude -p` usage appears in the evidence store.

## 6. Not in this design

- Fixing anything, or opening fix rounds automatically.
- A timer or any unattended trigger (a later spec, once batches prove useful).
- Rejected gate verdicts as a signal.
- The devShell CLI packaging (after the script matures; the file layout above
  is the contract it keeps).
- A Helm tile. The board's derived block can show "diagnoses awaiting review"
  later from the report's front matter.
