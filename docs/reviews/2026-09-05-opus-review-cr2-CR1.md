---
reviewer: opus
majors: null
minors: null
mutants_total: 17
mutants_killed: 14
---
# Opus gate — seat run cr2, task CR1 — REJECTED

## Summary

One commit, `c62b113`, on base `5addb14`; subject byte-identical to the plan's,
`Co-Authored-By: Claude Fable 5.1` trailer present, `tools/ritual.sh` mode
`100755`. `unit` and `lint` both build green in the sandbox (177 bats tests),
`nix develop -c githooks/pre-commit` exits 0, `shellcheck tools/ritual.sh
tools/session-start.sh` is silent. Red before green is genuine on both files.
The mechanism is sound in the small and the mutation score is high (14 of 17
killed). It is rejected on four defects found by running the hooks by hand
against real data rather than fixtures:

1. **The SessionStart in-flight part is unusable on the real host.** Against
   `/home/dalhaka/factory/runs` it emits 196 lines / 13 639 bytes, 170 of them
   long-dead historical logs; `SESSION_START_CAP_INFLIGHT` (1200) cuts it at
   line 16, inside run `a1`'s 28-hour-old corpses. All 26 genuinely running
   lines (e.g. `sc9 G12r - running`) are truncated away. The part therefore
   costs 1200 chars of the brief at every session start and shows *nothing*
   in flight — the opposite of §3.3's purpose. Rendered proof below.
2. **The Stop block's `reason` is not JSON-escaped**, so any path git quotes
   (a space, a non-ASCII byte, a quote, a backslash) makes stdout invalid JSON.
   Per the hooks documentation an unparseable stdout on exit 0 is "a
   non-blocking error" — so the hook silently **fails open on exactly the check
   it exists for**.
3. **`tools/session-start.sh` and `tools/ritual.sh` now hang forever when stdin
   is a terminal** (unconditional `input=$(cat)`). That breaks the ritual's own
   step 9, `bash tools/session-start.sh | head -60`, and the command every
   previous gate (sc1/G6, sc3/G10b, sc4/G8c) used to verify the script by hand.
   A regression to a script that worked at base.
4. **A missing or crashing `evidence` blocks** with "the board's queue block is
   stale", contradicting spec §4 ("a failing `evidence` degrade[s] to allow with
   a printed warning"). Verified: `RITUAL_EVIDENCE=/nonexistent/evidence` on a
   clean tree emits a block.

Plus: Step 0 was **not performed** (see below), the handoff omits §3.2's
newest-log-entry line, `flake.nix` is touched outside the declared `touches`,
and the SessionStart in-flight part carries no test at all (two mutations
survive).

## Hook protocol (real or assumed shapes)

**Step 0 was skipped.** The transcript is explicit
(`/home/dalhaka/factory/runs/cr2/CR1.log`, lines 148–152, 3190–3193): "Real
Claude hook stdin could not be captured in this headless build sandbox (no
operator session); the Stop/PreCompact/SessionStart field shapes were taken from
design §3.5". The plan made recording real stdin a precondition for writing the
tests; it did not happen, and the result note does not flag it as an unmet
step.

I verified the shapes independently against the Claude Code hooks documentation
rather than accept them:

| shape used | real? | evidence |
|---|---|---|
| Stop block = **top-level** `{"decision":"block","reason":"…"}`, exit 0 | **real** | the hooks guide states PostToolUse and Stop hooks use a *top-level* `decision: "block"` field — not `hookSpecificOutput` |
| Stop input `session_id` | real, always present (common field) | |
| Stop input `stop_hook_active`, JSON boolean | real | documented and parsed with `jq -r '.stop_hook_active'` in the guide's own example |
| `PreCompact` matcher `"manual\|auto"` | real; regex alternation is supported | |
| PreCompact input `trigger` | **not confirmed** in the documented input schema (the `manual`/`auto` values are documented as *matcher* values). Impact is nil: the handoff prints `trigger: ` empty |
| SessionStart input `source` ∈ `startup\|resume\|clear\|compact` | real (the docs also list `fork`) | |
| unparseable stdout on exit 0 | **ignored, non-blocking error** | this is what makes Finding 2 a fail-open |
| extra text before the JSON on stdout | **not tolerated** — if stdout does not begin with `{`, all of stdout is treated as plain text and the JSON is dropped | |

So the shapes it guessed are, by luck, the real ones — no MAJOR on shape
correctness. `stop_hook_active` is never read; that is defensible (§3.1 asks
only that the counter be "honoured, not bypassed", and the counter is
unconditional), and I confirmed no loop is possible (case h below). The
skipped Step 0 is recorded as a deviation, not a rejection cause.

Two live-fire notes on the "extra text" rule: `do_stop`'s block path prints the
JSON and nothing else (good), but the override path prints prose on **stdout**
(`ritual: override present - allowing (…)`). That path allows, so it is
harmless, but it is stdout the docs say will be swallowed as plain text; §3.1's
"otherwise nothing, exit 0" would put it on stderr.

## Stop hook cases

Run by hand in a throwaway clone of the workspace, `XDG_STATE_HOME` pointed at
a scratch dir, stdin fed the documented JSON shape.

| case | stdin / fixture | observed | verdict |
|---|---|---|---|
| (a) clean tree, board current | `{"session_id":"sA",…,"stop_hook_active":false}`, stub `evidence` rc 0 | exit 0, **empty stdout**, `last-stop` written | pass, **0.029 s** |
| (b) untracked `docs/reviews/2026-09-05-opus-review-x-Y.md` | | `{"decision":"block","reason":"ritual: commit the review file(s) docs/reviews/2026-09-05-opus-review-x-Y.md"}` | pass, 0.034 s |
| (c) modified `docs/superpowers/plans/2026-09-05-context-reset-ritual.md` | | block, reason `ritual: commit or revert …; uncommitted plan sections are invisible to the seat's clone of main` | pass |
| (d) stale board (`EVIDENCE_RC=1`) | | block naming `write-board` | pass |
| (d') **real** `evidence` on the real tree | | block (genuinely stale block in the clone), **0.159 s** total; `check --board` alone 0.133 s | pass; H2 answered, matches the 0.124 s claim |
| (e) `.claude/ritual-override` present + untracked review | | no block; `ritual: override present - allowing (dalhaka 2026-09-05 17:49:43…)` | pass (but on stdout, see above) |
| (f) three blocks in one session | same `session_id`, dirty review | block, block, **allow**; `ritual.log` gets `ritual: allowed after 2 blocks - …` | pass |
| (f') counter reset | block, block, clean → allow, dirty again → blocks | pass — matches §3.1's "reset when a block's checks pass" | |
| (g) `not json at all` / empty stdin | | exit 0, no `decision`, stderr `ritual: malformed Stop input (no session_id) - allowing` | pass |
| (h) `stop_hook_active: true` | three calls | block, block, allow — identical to (f) | **no loop possible**: the bound is unconditional |
| (i) wall time | every case above | 0.029–0.212 s | pass, well under 1 s |

"Session" is identified by the `session_id` string scraped from stdin with
`sed`; the counter lives at `$statedir/<session_id>.blocks`. Those files are
never reaped (minor, noted below).

Two failures found in this section:

- **JSON escaping (MAJOR).** `printf '{"decision":"block","reason":"%s"}\n'
  "$reason"` with a `git status --short` path. `git` quotes paths containing
  spaces or non-ASCII bytes, so the reason arrives already carrying `"`:

  ```
  {"decision":"block","reason":"ritual: commit the review file(s) "docs/reviews/2026-09-05 draft.md""}
  {"decision":"block","reason":"ritual: commit the review file(s) "docs/reviews/2026-09-05-review\342\200\224x.md""}
  ```

  Both fail `json.load` (`Expecting ',' delimiter: line 1 column 66`). Claude
  Code treats that as a non-blocking error, so the turn ends with the review
  file uncommitted — the precise failure the hook was built to prevent. No test
  covers a quoted path. The fix is one `sed 's/\\/\\\\/g; s/"/\\"/g'` on
  `$reason` (and dropping `core.quotePath` with `-c core.quotePath=false`).

- **`evidence` failure is a block, not an allow (MAJOR).** `collect_unmet`
  cannot distinguish "the board block drifted" (documented exit 1) from
  "`evidence` is gone / crashed" (127, 2). Verified with
  `RITUAL_EVIDENCE=/nonexistent/evidence` and with a stub that prints a
  traceback and exits 2: both emit the stale-board block on a clean tree. Spec
  §4 requires degrade-to-allow-with-warning here, and the whole point is that a
  hook must not block on its own tooling breaking — `evidence` lives in the
  system closure, so a switch or a broken generation makes every turn of every
  session block twice with a reason that will not help. The tests only exercise
  rc 0 and rc 1.

## PreCompact and inflight

`ritual.sh precompact` with `{"session_id":"sP",…,"trigger":"auto"}`, real
`evidence`, a fixture `FACTORY_ROOT` and an untracked review: exit 0 in
**0.212 s**, writes `$XDG_STATE_HOME/nixos-agent-env/ritual/handoff-sP.md`:

```
# Handoff 2026-09-05 17:51:03
trigger: auto
HEAD: c62b113 session: the reset ritual — …
## dirty (what the ritual did not finish)
?? docs/reviews/pending.md
## in flight
r1 K1 - pid 999999 DEAD - log age 0m - then: gate; ff; dispatch G12b - relaunch: factory-wave r1 /home/dalhaka/nixos-agent-env K1 K2
r2 K2 - pid 398511 alive - log age 0m - then: watch
## unmet checks
ritual: commit the review file(s) docs/reviews/pending.md
ritual: the board's queue block is stale - …
```

- **Writes nothing inside the repo**: `git status --short` and `git status
  --short --untracked-files=all` are byte-identical before and after. `grep`
  finds no redirection or `mkdir` under `$repo` anywhere in `ritual.sh`.
- **Missing (spec §3.2, and the gate's own list):** "the first line of the
  newest log entry" from `docs/board/log-2026-09.md`. The handoff has time,
  trigger, HEAD, dirty, in-flight and unmet checks — no board-log line. The
  chronology carrier the spec named is the one thing absent from the handoff.

`inflight` reads `${FACTORY_ROOT:-$HOME/factory}/runs/*/*.log` (that is the env
override — `FACTORY_ROOT`, not a runs-dir variable), skips a key with a
`.result`, takes `pid:` from the run's `run.meta` and `kill -0`s it, else falls
back to log mtime against `RITUAL_STALE_AFTER` (7200). Fixture behaviour is
correct on every case (dead pid → `DEAD` + relaunch, live pid → `alive`, result
present → absent, old log without meta → `DEAD (mtime)`).

Against the **real** runs dir it is a different story — 0.129 s, but:

```
lines=196  bytes=13639   DEAD (mtime)=170   running=26   alive=0
```

and the rendered SessionStart output (real `evidence`, real runs dir) ends:

```
## In flight
a10 integrate - DEAD (mtime) - log age 1015m - relaunch: factory-wave a10
a1 integrate - DEAD (mtime) - log age 1655m - relaunch: factory-wave a1
… fourteen more a1 corpses …
a1 N8.review -
…inflight truncated at 1200 chars (SESSION_START_CAP_INFLIGHT)

Where everything is: docs/runbooks/session.md
```

Every live run (`sc9 G12r - running`, `sc9 wave-group-1 - running`, …) is past
the cut. This is Finding 1: the part never shows in-flight work on the host it
was written for, and it spends the whole 1200-char budget doing it. Nothing in
the tests could catch it — the fixtures have one or two runs. A live-first
ordering, or dropping/collapsing `DEAD (mtime)` entries older than
`stale-after`, is what §3.3 needs; §4's own reasoning ("`tasks.py` stops
reporting the key as `running` once the log is older than `stale-after`") says
as much.

Secondary: for an mtime-DEAD entry the hint is `relaunch: factory-wave a1` —
no repo, no keys, and the run name reused rather than §3.3's `<newname>`. Not
a runnable command. And `kill -0` on a recycled pid owned by another user
returns EPERM, which this code reports as `DEAD`; harmless here (single-user
host) but worth a `2>/dev/null` comment.

## Checks

| check | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link` | **pass** (177 ok, 0 not ok in the sandbox) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | **pass** |
| `nix develop -c githooks/pre-commit` | **exit 0** (regenerates the board block once for my clone's derived state — expected, my tree lacks the store/runs context; restored) |
| `nix develop -c shellcheck tools/ritual.sh tools/session-start.sh` | exit 0, no output |
| `nix develop -c python3 pkgs/evidence/repomap.py --root . check` | exit 0 — `docs/MAP.md` is honestly regenerated |
| `.claude/settings.json` parses; hooks | `SessionStart` (G6's, `startup\|clear\|resume\|compact`, unchanged) + new `PreCompact` (`manual\|auto`) + new `Stop` (no matcher), each `type: command`, `timeout: 10`. Base has no `PreToolUse` (OG1r has not landed) — correct |
| forbidden calls in the hook path | `grep -nE '(^\|[^a-z])nix \|git (commit\|add)\|sudo\|systemctl'` over both scripts → **none** |
| repo writes from a hook | none (grep + the before/after `git status` assertion above) |
| commit hygiene | one commit on `5addb14`; subject byte-identical (diffed against the plan's string); `Co-Authored-By` present; `Generated-By` line as usual |

Locally `bats tests/unit` shows one failure, #144 "basket set and not mounted:
prints the exact sudo mount line and waits for Enter" — a tty-dependent test
unrelated to CR1; the sandboxed `unit` check, which is the acceptance gate,
passes all 177.

## Red before green

- `tools/ritual.sh` moved aside → `bats tests/unit/92-ritual.bats`: **18 of 18
  fail** (exit 127, "Command not found"). Genuine red, though a
  missing-interpreter red is weaker evidence than a behavioural one.
- The two new tests in `tests/unit/90-session-start.bats` run against base
  `5addb14`'s `tools/session-start.sh` (G10b's): **exactly those two fail**
  (`not ok 11 source=compact with a handoff file prints it under ## Handoff`,
  `not ok 12 a last-stop stamp two hours old prints the idle notice`), the ten
  pre-existing ones still pass. Clean red, and G6/G10b's tests are untouched.

## Mutation table

Seventeen mutations, each applied to the shipped script, the owning bats file
run, then the file restored.

| # | mutation | killed by |
|---|---|---|
| M1 | `docs/reviews` dropped from the review status path | 3 tests |
| M2 | the `check --board` branch made unreachable | `a stale board check blocks naming write-board` |
| M3 | `.claude/ritual-override` ignored | `the ritual override file allows and reports the override` |
| M4 | the two-block bound removed (third block still blocks) | `the third block in one session allows…` |
| M5 | the block counter never incremented | `the third block in one session allows…` |
| M6 | board debt `-ge` → `-gt` | `six review commits since the board commit block on debt` |
| M7 | `precompact` also touches `$repo/handoff-leak.md` | `precompact … leaving the repo untouched` |
| M8 | `inflight` reports a dead pid as `alive` | `inflight reports a dead pid with a relaunch hint` |
| M9 | `stop` exits 1 on malformed stdin instead of allowing | `malformed stdin degrades to allow with a warning` |
| M10 | the `DEAD (mtime)` branch removed | `an old log with no run.meta reports DEAD (mtime)` |
| M11 | the `.result` skip removed | `inflight omits a key whose result is already written` |
| M12 | the `relaunch:` hint dropped | `inflight reports a dead pid with a relaunch hint` |
| M13 | the idle line's text changed | `a last-stop stamp two hours old prints the idle notice` |
| M14 | the `## Handoff` heading and `cat` removed | `source=compact with a handoff file prints it…` |
| M16 | the whole ritual part dropped from SessionStart | 2 tests |
| **M15** | **`inflight_out=''` — the in-flight table silently dropped from SessionStart** | **SURVIVES** |
| **M17** | **the `## In flight` heading replaced with `x`** | **SURVIVES** |

14 of 17 killed. The two survivors are the same hole: §3.3's in-flight part of
`session-start.sh` has no test whatsoever — it could vanish or be renamed and
every check stays green. `tools/ritual.sh inflight` is tested; its wiring into
the brief is not. (Plan §5 lists only the handoff and idle tests for
`90-session-start.bats`, so this is a coverage gap rather than a plan
violation — but it is the gap that let Finding 1 ship.)

## Findings

1. **MAJOR — the SessionStart in-flight part shows no in-flight work on the
   real host.** 196 lines / 13 639 bytes from `/home/dalhaka/factory/runs`, 170
   of them `DEAD (mtime)` logs up to 29 hours old; the 1200-char cap truncates
   at line 16 and all 26 `running` lines are lost. Rendered output above.
   Fix: filter or collapse entries older than `RITUAL_STALE_AFTER`, order
   live-first, and cap the DEAD tail (e.g. "+170 dead logs older than 2 h").
   Then test it — M15/M17 must die.
2. **MAJOR — the Stop block's `reason` is not JSON-escaped, so the hook fails
   open on git-quoted paths.** Demonstrated with `docs/reviews/2026-09-05
   draft.md` and an em-dash filename; both produce stdout that `json.load`
   rejects, and the docs say invalid JSON on exit 0 is a non-blocking error.
   Fix: escape `\` and `"` in `$reason` (and pass `-c core.quotePath=false` to
   the `git status` calls); add a test with a space in the path.
3. **MAJOR — `input=$(cat)` makes both scripts hang forever on a terminal.**
   `bash tools/session-start.sh <repo>`, `ritual.sh stop|precompact|inflight`
   all hang under a pty (verified four times each, killed at 4 s; also
   `timeout … script -qec` rc 124 three times). This breaks the ritual's own
   step 9 (`bash tools/session-start.sh | head -60`) and every prior gate's
   manual verification command, and it will eat an agent's Bash timeout. Fix:
   `[ -t 0 ] || input=$(cat)`.
4. **MAJOR — a missing or failing `evidence` produces a wrong block** claiming
   the board is stale, against spec §4's explicit degrade-to-allow. Verified
   with a nonexistent binary and with a stub exiting 2. Fix: capture the exit
   status, treat 1 as drift and anything else as "unavailable → allow with a
   stderr warning"; test rc 127.
5. **MINOR — the handoff omits the newest board-log line** required by §3.2
   (and by this gate's checklist). Everything else §3.2 asks for is present.
6. **MINOR — the `relaunch:` hint for mtime-DEAD runs is not a runnable
   command** (`relaunch: factory-wave a1`, no repo, no keys, and the old run
   name where §3.3 asks for `<newname>`).
7. **MINOR — the override notice goes to stdout** in the Stop path. Harmless
   (that path allows) but the docs are clear that non-JSON stdout is swallowed;
   §3.1 says "otherwise nothing, exit 0". Put it on stderr.
8. **MINOR — `<session_id>.blocks` files are never reaped** from the state
   dir; one file accumulates per session forever.
9. **NOTE — Step 0 was not performed and was not reported as unmet.** The
   plan made recording real Stop/PreCompact/SessionStart stdin a precondition
   for writing the tests. The implementer could not drive an interactive
   `claude` from the seat and substituted the spec's §3.5 shapes. I verified
   the shapes against the hooks documentation and they are real (see above), so
   nothing is broken by this — but the seat should have surfaced it as an
   unmet step rather than recording it only in its own reasoning, and the
   answer to H1's `trigger` sub-question is still unverified.

## Deviations

- **`flake.nix` is touched and is not in CR1's declared `touches`.** The change
  is four lines copying `tools/ritual.sh` into the `unit` check's sandbox,
  mirroring the two adjacent precedents, and it is necessary — without it
  `92-ritual.bats` cannot resolve the script. Correct code, undeclared file:
  the `touches` list is the conflict-detection contract, so this should have
  been disclosed in the result notes (the commit body mentions it only as "the
  unit check now carries ritual.sh").
- **`docs/OPERATIONS.md` is touched** (one line: the generated queue block
  gains `SB3b`). That is the pre-commit hook's forced regeneration and is
  within the allowance for this gate.
- `docs/MAP.md` regenerated and disclosed, as the plan expected; `repomap.py
  check` agrees.
- The eight files in `git show --stat HEAD` are therefore: the six declared
  (`tools/ritual.sh`, `tests/unit/92-ritual.bats`, `tools/session-start.sh`,
  `tests/unit/90-session-start.bats`, `.claude/settings.json`, `docs/MAP.md`)
  plus `docs/OPERATIONS.md` (forced board regeneration) and `flake.nix`
  (undisclosed, necessary).
- No `docs/runbooks/session.md` section and no `CLAUDE.md` line — correct, that
  is CR4's.
- The result note's measurements check out: `check --board` 0.133 s here
  against its 0.124 s, and `ritual.sh stop` 0.159 s with the real `evidence`
  against its 0.14 s.

Verification was done in a throwaway clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/41b897e1-b5cd-4f5d-870c-3dea3b7a3945/scratchpad/gate-cr2-CR1`
with `XDG_STATE_HOME` and `FACTORY_ROOT` pointed at scratch fixtures except
where the real host paths are named above (read-only). The implementer's
workspace was not touched.
