# Opus gate 2 — a4/N7c (f606690) — REWORK (one test; no implementation change)

## Round-1 items: all four done, and the honest gap is now closed by observation
Workspace file gone — the only surviving mention of `DSH_HOOK_DENIAL_LOG` in code is the
test's *negative* grep (`tests/unit/70-dsh-openrouter.bats:600`); `dsh-openrouter.sh:372,378`
emit `exec '$hook_guard'`, a nix-store path, so hooks.json names nothing writable.
`hook-guard.py:205` prints the record on **every** deny, after stdout — a stderr failure
cannot suppress an already-emitted decision, and the guard exits 0 (probed with stderr closed
and with a closed pipe: exit 0 both times). I re-verified the live probe myself: HOOKPROBE4
`session.jsonl.zstd` seq 659 carries `stderrSummary` with the verbatim record for `sudo true`.
Round 1's code-only claim is now measured. Deny rules are byte-identical to 560d025 (diffed the
`PROTECTED_ABSOLUTE`→verdict region); the dropped tautological test asserted only the
now-nonexistent log-failure path, so no coverage was lost. Reader run against that **real**
transcript prints the record and resolves `<- sudo true` via `sourceEventSeqs`.

## Red before green (four files reverse-applied, tests kept)
`unit` fails 78 (`:564`, no stderr record), 80 (`:601`, grep finds the log path), 81 (`:628`)
and 82 (`:641`, `dsh-denials` absent). Restored: `unit` 0, `lint` 0.

| # | Mutation | Caught by |
|---|---|---|
| M1 | guard drops the stderr record (`hook-guard.py:205` → `pass`) | not ok 78 |
| M2 | reader ignores denies (`dsh-denials.py:88` never matches) | not ok 81, 82 |
| M3 | **slice** the JSON to 400 (`_denial_record` → `_record_json(...)[:400]`) | **nothing — suite green** |

## The one defect
M3 survives. With it, a 600-char path yields `Unterminated string starting at: char 70` —
exactly the failure `hook-guard.py:162-188`'s docstring exists to prevent — yet every test
passes, because the only record assertion (`:563`, `< 400`) uses `sudo id`, ~120 chars. The
truncation loop is load-bearing by the author's own argument and has never been shown to fail.
Add one case: deny a `write` to `/etc/` + 600 chars, assert stderr parses as JSON and is < 400.
(Unmutated, that path is correct — I measured 382 chars, valid JSON, for a quoted/backslashed
600-char path.)

## Notes, not blockers
- `dsh-denials.py:123` swallows unreadable transcripts; a corrupt file prints the same "no
  denial records found" as a clean tree (verified). An audit reader should warn per skip.
- Record carries the full denied command, but `tool/call.arguments` already stores it verbatim
  — no new exposure. No secrets in reader or fixture (grepped).
- `docs/OPERATIONS.md:5` still says the fix is in progress — orchestrator's file.

Security, lint (0), commit subject and `Co-Authored-By` trailer: all sound.
