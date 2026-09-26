---
plan_defect: none
mutants_total: 1
mutants_killed: 1
mutants_outside_named: 0
model: sonnet
---
# Opus gate — seat run sd10, task SD10 — APPROVED

## Summary

SD10 is the seat-driver plan's docs task: the driver README
(`tools/factory/seat/README.md`) gains "## Ladders", "## Classes", "## Fix
rounds carry the prior attempt", "## Escalation" and "## The drive seat"
after "## Routing", plus "### The spool" and a PATH note inside "## Seat unit
(SB3)"; `docs/runbooks/evidence.md` gains "## The ladder report" after "## The
planning report". I fact-checked every concrete claim in the new prose
against the code and data files on this branch (factory-lib.sh, factory-task,
factory-review, route.py, routing.toml, claims.toml, pkgs/seat/seat-submit.py,
pkgs/seat/seat-spool.py, seat-drive.sh, nixosModules/seatLane.nix,
pkgs/evidence/report.py, pkgs/evidence/tasks.py) and found every flag, file,
line, exit code, table row and claim id it names to be accurate, several down
to byte-identical string matches (the ladder table, the claim ids and
`review_by` dates, the `.escalate` and launch-line shapes, the 15 spool
refusal codes in order, the `10.100.4.2` URL, the `path = [ ... ]` PATH
list). The lint gate is green, `docs/MAP.md` is unchanged, `tasks.py check`
is silent, the tier-word grep prints nothing, the section order matches the
Interfaces list exactly, touches are exactly the two files plus
`docs/OPERATIONS.md`'s derived queue block, and the commit is one commit with
the byte-identical subject and correct trailers. One MINOR: the commit body
narrates the change but does not paste a red/green transcript for the
section's named mutant test, though I ran that test myself (below) and it
behaves exactly as the section describes.

## Contract items

Interfaces (SD10 section), taken literally:

1. **"## Ladders" after "## Routing"** — present, `tools/factory/seat/README.md:499`. Covers `--rung`
   (`README.md:503-505` vs `factory-lib.sh:486` doc-comment and `:497-499`
   parsing), exit 4 on ladder exhaustion (`README.md:508-510` vs
   `factory-lib.sh:777` `'ladder exhausted at rung %s for %s\n'` and the
   `exit 4` at `factory-lib.sh` return path via `factory-task:286,192`), the
   one-variable rule (`README.md:518-521` vs `route.py:132-171`
   `check_ladders`, verified live below), the first rows' committed ladders
   (`README.md:528-538`, verified byte-for-byte against
   `docs/ledger/routing.toml`), `fallback` as sideways
   (`README.md:544-547` vs `factory-lib.sh:781-784` and `route.py:290-294`),
   and the claims (`README.md:549-558`, verified against every field of the
   seven `docs/ledger/claims.toml` rows it names — id, status, class, owner,
   `review_by = 2026-09-20`, `closes_by`). Met.
2. **"## Classes"** — `README.md:559`. `task-classes.toml`, ten classes
   plus `any` (`README.md:562-563` vs `route.py:52-63` `CLASSES` tuple: ten
   named + `any`), first-rule-wins glob matching, most-common-file tie rule,
   `class:` in the `.result` (`README.md:570-573` vs `factory-task:948`
   `printf 'class: %s\n' "$class"`). Met.
3. **"## Fix rounds carry the prior attempt"** — `README.md:575`. `--prior
   <run>/<KEY>` shape and refusal (`README.md:577-578` vs
   `factory-task:78-85`), the `## Prior attempt (<run>/<KEY>)` block
   (`README.md:579` vs `factory_prior_block` in `factory-lib.sh:1306` and
   `factory-task:302-306`), `prior:` recorded in `.result`
   (`README.md:580` vs `factory-task:952-953`), the five parts each capped at
   60 lines / 8,000 bytes total (`README.md:581-598` vs
   `factory-lib.sh:1341,1344,1372,1403,1416` — every `factory_prior_cap 60`
   call — and `factory_prior_byte_cap` at `factory-lib.sh:1268-1289`, whose
   comment states the 8,000-byte bound and whose `if [ ... -gt 8000 ]` enforces
   it), the files read (prior `.result`, newest REJECTED Opus review, the run's
   `.review.md`) and never read (`.log`, transcript, `.dsh-home`) — verified
   against `factory_prior_block`'s body, which touches only `$result`,
   `$opus_file` and `$seat_file`. Met.
4. **"## Escalation"** — `README.md:602`. `<KEY>.escalate`, exit 4, before any
   workspace/log/pid/`.result` (`README.md:604-609` vs
   `factory_task_escalate`'s comment at `factory-lib.sh:146-151` and the
   `exit 4` at `factory-task:192`), the implement `launch:` line's exact
   `Workflow({...})` shape (`README.md:613-617` vs `factory-task:169`
   `launch="Workflow({ scriptPath: ...`), the review form's `opus-gate
   task/<KEY> ~/factory/ws/<run>/<KEY>` (`README.md:621-622` vs
   `factory-review:40` `launch="opus-gate task/$key ~/factory/ws/$run/$key"`
   verbatim), the brief's `**Escalated:**` line placed one line after
   "Rejected, fix round owed" (`README.md:622-624` vs `pkgs/evidence/tasks.py:
   1991-2000`, where the `**Escalated:**` append immediately follows the
   `**Rejected, fix round owed:**` append). Met.
5. **"## The drive seat"** — `README.md:630`. `seat-drive`, the isolated
   home under `~/factory/drive/<stamp>.dsh-home` (`README.md:637-639` vs
   `seat-drive.sh:103-108`), the `orchestrate/any/any` rung-1 resolve
   (`README.md:633-634` vs `seat-drive.sh:77-79`), the
   `http://10.100.4.2:<port>` URL (`README.md:643` vs
   `tests/integration/seat-vm.nix:531` and `tests/seat/test_seat_run.py:219`,
   both asserting exactly that host), the denial-audit command
   (`README.md:646-648`, an existing, unchanged command), the Design-7 list of
   what the driver decides alone vs the operator's (`README.md:657-661` —
   matches `seat-drive.sh`'s own header comment and the escalation/fallback
   behaviour already verified). Met.
6. **"## Seat unit (SB3)" gains the spool and PATH** — the spool subsection
   is present at `README.md:726` inside that section (confirmed by heading
   scan: `## Seat unit (SB3)` then `### The spool` then the next `##`).
   `--no-start` spools an empty 0600 marker at the spool-dir sibling of
   `--jobs-dir` (`README.md:729-732` vs `pkgs/seat/seat-submit.py:23-26,
   271-290`), `--wait` semantics and refusal (`README.md:739-743` vs
   `seat-submit.py:100-140,189-194`), all 15 refusal codes in the exact order
   printed (`README.md:748-752` vs `pkgs/seat/seat-spool.py:41-108`, code for
   code), `journalctl -u seat-spool.service` (`README.md:754`), exit-0 refusal
   and always-unlinked marker (`README.md:756-758` vs
   `seat-spool.py:129-155,170`). The PATH note (`README.md:761-770`) matches
   `nixosModules/seatLane.nix:197-201` — `path = [ "/run/current-system/sw"
   cfg.harnessPackage pkgs.iproute2 seatSubmit ]` — verbatim. Met.
7. **"Adding a row" paragraph names `rung`/`class`/`fallback`** —
   `README.md:456-459`: "A row may also carry a `rung`, a `class` and a
   `fallback` — see "Ladders" and "Classes" below." Met.
8. **`docs/runbooks/evidence.md` gains "## The ladder report" after "## The
   planning report"** — present at `evidence.md:152`, immediately after the
   planning-report section (confirmed by heading order in the diff). The
   command and its defaults (`--runs-dir ~/factory/runs --jobs-dir
   /var/lib/seat/jobs --min-n 5`) match `pkgs/evidence/report.py:918-922`
   exactly; the grouping tuple, the line shape (`n=`, `first-gate a/g (pct%)`,
   `landed-commits`, `fix-rounds f/l`, `wall-median`, `out-tokens-median`) and
   the `insufficient (n=<n>)` refusal match `ladder_report` at
   `report.py:793-829` field-for-field, including the f-string producing the
   exact same tokens; the orchestrate header `# orchestrate — drive sessions
   (run.meta driver: ⋈ job.json)` is byte-identical to `ORCHESTRATE_HEADER` at
   `report.py:58`; the orchestrate line shape and its own `insufficient
   (n=<sessions>)` and "no drive session recorded" strings match
   `report.py:862-889`; the seam sentence matches the `join_tasks_gates`
   reference at `report.py:753` and `evidence.py:210`. Met.
9. **No model id in a sentence a skill could copy; ids stay in the table's
   own quoted lines** — verified live: `grep -n 'more capable\|most
   capable\|mid-tier\|least powerful' tools/factory/seat/README.md
   docs/runbooks/evidence.md` prints nothing (exit 1). The model ids that do
   appear (in the fenced `docs/ledger/routing.toml` excerpt and the existing,
   unchanged "opus-gate"/"opus-review" filename convention) are inside code
   fences/file-glob conventions, not prose sentences a skill would quote out
   of context. Met.

## Red before green

The section's only content test is the reviewer-run grep (the lint gate
carries no content assertion of its own — a docs-only edit cannot make it
fail). I ran the section's own mutant to demonstrate the grep can fail and
then pass:

```
$ echo "This picks the more capable model for review." >> tools/factory/seat/README.md
$ grep -n 'more capable\|most capable\|mid-tier\|least powerful' tools/factory/seat/README.md docs/runbooks/evidence.md
tools/factory/seat/README.md:877:the real repo has).This picks the more capable model for review.
$ git checkout -- tools/factory/seat/README.md
$ grep -n 'more capable\|most capable\|mid-tier\|least powerful' tools/factory/seat/README.md docs/runbooks/evidence.md
(nothing; exit 1)
```

Red (the mutant present) fails the grep; green (the mutant reverted) passes
it. The lint gate itself was run clean on HEAD (below).

## Mutants

The section names exactly one mutant: "a 'more capable model' sentence → the
reviewer's grep prints it." Applied and reverted above.

- mutants_total: 1
- mutants_killed: 1 (the grep prints the offending line)
- mutants_outside_named: 0 (no other mutants attempted; the section names
  only this one, and every other contract item was checked by direct
  fact-comparison against the code rather than mutation, per the Required
  matrix's item 1)

## Checks

```
$ nix build .#checks.x86_64-linux.lint -L --no-link --rebuild
... (treefmt, eslint, prettier over the fixture and workflow files) ...
$ echo $?
0
```

```
$ nix develop -c githooks/pre-commit
All checks passed! (nixfmt, 127 files)
js-lint arms pass (the fixture files' intentional errors are expected fixture
content, unrelated to this diff)
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated
$ echo $?
0
```

The "queue block was stale" regeneration is expected noise from reviewing at
a later HEAD than the driver's own pre-commit run: HEAD here already includes
SD10's own commit, so the derived queue no longer lists SD10 as pending (it
lists the tasks that come after it). The committed `docs/OPERATIONS.md` hunk
itself is exactly the queue block regenerated by pre-commit at the time the
driver ran it (SD9 → SD10, nothing outside the `<!-- tasks:begin -->…
<!-- tasks:end -->` block) — confirmed by diff.

```
$ nix develop -c python3 pkgs/evidence/repomap.py --root . write
$ git diff --exit-code docs/MAP.md
$ echo $?
0   (no diff — MAP.md unchanged, correct: no package/module/check/host file added)
```

```
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check
(silent)
$ echo $?
0
```

No Python file is touched by this diff, so `ruff check`/`ruff format --check`
are not applicable (the section's `touches` names only two Markdown files).

## Touches and commit

Touches: `git diff bbb6fb0..HEAD --name-only` → `docs/OPERATIONS.md`,
`docs/runbooks/evidence.md`, `tools/factory/seat/README.md`. The section's
list is `tools/factory/seat/README.md, docs/runbooks/evidence.md`;
`docs/OPERATIONS.md` is the derived queue block, allowed by the plan rule
without needing a commit-body explanation. No file outside the allowed set.

Commit: exactly one commit (`git log bbb6fb0..HEAD --oneline` → 1 line).
Subject is byte-identical (checked with `cat -A`) to the required subject.
Trailers, in order after a blank-line-separated body: `Generated-By:` then
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` — the WORKSPACE
RULES order. The plan file (`docs/superpowers/plans/2026-09-06-seat-driver.md`)
is untouched.

## Findings

MINOR-1 (`docs/reviews/2026-09-08-opus-review-sd10-SD10.md` review note, not
a code file) — the commit body narrates what changed but does not paste a
red/green transcript for the section's named mutant test, as the plan's
Global Constraints ask ("TDD, red first. Paste the red command and its
output, then the change, then the green check by name."). I ran that test
myself under "Red before green" above and it behaves exactly as the section
describes (the mutant is killed, no test is vacuous), so this is a process
gap in the commit message, not a defect in the docs content or an
undischarged test obligation — not gating.

## Verdict

APPROVED. Every Interfaces item is met with a direct file:line citation
against code that already exists on this branch; the one named mutant is
real and dies as described; the lint gate, MAP regeneration, and tasks check
are all green; touches and the commit are exactly as required. One MINOR
(missing red/green paste in the commit body) does not gate.
