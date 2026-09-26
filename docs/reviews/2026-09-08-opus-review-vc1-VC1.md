---
plan_defect: none
mutants_total: 10
mutants_killed: 7
mutants_outside_named: 7
---
# Opus gate — seat run vc1, task VC1 — APPROVED

## Summary

The section's contract is met literally and nothing else moved. The diff is twelve lines in three
files: six `-days 2` → `-days 3650` and six guard lines
(`openssl x509 -in <cert> -noout -checkend 31536000`), one per certificate each `testCerts` block
writes — in `broker-vm.nix` inside the host loop after each leaf plus one for `$out/ca.crt`, in
`lane-vm.nix` and `seat-vm.nix` one for `ca.crt` and one for the single leaf. No VM script, CA
bundle wiring or assertion changed.

I reproduced the calendar's red myself: at the base `4491aa2`, without `--rebuild` (so the store's
cached fixture is used), `nix build .#checks.x86_64-linux.lane-vm -L --no-link` exits 1 with the
nightly's own line — Assumption 1 held for the reviewer too, so the commit body's claim is true and
not a substitution. At the branch head all three VM checks are green with `--rebuild`.

Ten mutants: the three the section names plus seven of my own. The two survivors are not defects —
they are the section's own discrimination arms (a guard pointed at the wrong file, a guard disarmed),
whose kill criterion is the shipped code's shape, and the shipped shape is proven live by the mutants
that do die on every one of the six `openssl` lines.

## Contract items

Line numbers are in the fresh clone
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/8bb55291-5990-42c5-a75b-90b0f0bca390/scratchpad/gate/gate-vc1-VC1`
at `f08e963`.

| # | contract (Interfaces, taken literally) | met | evidence |
|---|---|---|---|
| 1 | the CA's `openssl req -x509 … -days 3650` in each of the three blocks | yes | `tests/integration/broker-vm.nix:13`, `tests/integration/lane-vm.nix:17`, `tests/integration/seat-vm.nix:18` — all three read `openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \` |
| 2 | the leaf's `openssl x509 -req … -CAcreateserial -days 3650` in each block | yes | `broker-vm.nix:20` (`-CAcreateserial -days 3650 -copy_extensions copy -out $out/$h.crt`), `lane-vm.nix:23`, `seat-vm.nix:24` |
| 3 | six `-days 2` gone, none left | yes | `grep -rn 'days 2' tests/integration/*.nix` → no match; `git diff base..HEAD` shows exactly six `-days 2` → `-days 3650` hunks |
| 4 | one guard line per certificate the block produces, `openssl x509 -in $out/<name>.crt -noout -checkend 31536000` | yes | `lane-vm.nix:24,25` (`ca.crt`, `openrouter.test.crt`), `seat-vm.nix:25,26` (same), `broker-vm.nix:21,23` (`$out/$h.crt`, `$out/ca.crt`) |
| 5 | in `broker-vm.nix` the leaf guard sits **inside** the loop after each leaf, plus one for `$out/ca.crt` | yes | `broker-vm.nix:14` `for h in allowed.test denied.test; do` … `:20` leaf written … `:21` `openssl x509 -in $out/$h.crt -noout -checkend 31536000` … `:22` `done` … `:23` `openssl x509 -in $out/ca.crt -noout -checkend 31536000`. Mutant O1 proves the in-loop guard is live |
| 6 | each guard sits **after** the certificate it names | yes | in all three files every guard line is below the `-out` that writes its file; mutant M2 shows the opposite order dies with `No such file or directory` |
| 7 | "nothing else in the three files changes; the VM scripts, the CA bundle wiring and every assertion stay byte for byte" | yes | `git diff 4491aa2..HEAD --stat` → `broker-vm.nix 6 ++++--`, `lane-vm.nix 6 ++++--`, `seat-vm.nix 6 ++++--`; every hunk is inside the `testCerts` `runCommand` string |
| 8 | Assumption 2 — `pkgs.openssl` already in `nativeBuildInputs` supplies `x509 -checkend` | yes | `broker-vm.nix:9`, `lane-vm.nix:13`, `seat-vm.nix:14` `nativeBuildInputs = [ pkgs.openssl ];`; the guard runs and prints `Certificate will not expire` in every green build log |

## Red before green

The section's Step 1 red is the calendar's, gated on Assumption 1 ("if green, the mutant of Step 4
supplies the red"). I did not take the seat's word: fresh clone at the base commit
`4491aa253392dc5e71dc06d8ec8ac3020bacd81e`, `-days 2` still on `lane-vm.nix:17,23`,
`nix build .#checks.x86_64-linux.lane-vm -L --no-link` **without** `--rebuild` so the store's
cached fixture is reused:

```
vm-test-run-lane-openrouter> machine # [   11.912573] mitmdump[657]: [09:18:22.372][10.100.30.2:40470] Server TLS handshake failed. Certificate verify failed: certificate has expired
…
> AssertionError: {"error": "HTTP 502: <html>\n<head>\n    <title>502 Bad Gateway</title>\n</head>\n<body>\n    <h1>502 Bad Gateway</h1>\n    <p>Certificate verify failed: certificate has expired</p>\n</body>\n</html>", "ts": 1788859108.400443}
error: Cannot build … vm-test-run-lane-openrouter.drv   (exit 1)
```

Same failure class, same string, as the nightly of 2026-09-08 08:01Z. So Assumption 1 held at review
time as well — the commit body's "the cache had not been rebuilt, so the same red reproduced here
(Step 1) rather than the mutant of Step 4" is accurate, and the body correctly did **not** claim the
Assumption-1 substitution.

Green at the head, same command with `--rebuild` (fresh certs, fresh guard):
`vm-test-run-lane-openrouter> test script finished in 13.22s` … `(finished: cleanup, in 0.10 seconds)`,
exit 0. Red → change → green, with the change being the only difference.

The guard's own red is not calendar-bound: mutant M1 below fails the derivation today.

## Mutants

Each mutant in its own fresh clone of the branch, `git add -A` before the build (flakes see only
tracked files), the clone discarded afterwards; the reviewed tree was never edited.

| # | named? | mutation | test that must kill it | result |
|---|---|---|---|---|
| M1 | yes (row 1) | `lane-vm.nix:23` `-days 3650` → `-days 2` (leaf only) | `nix build .#checks.x86_64-linux.lane-vm -L --no-link` | **KILLED.** `lane-vm-test-certs> Certificate will not expire` (the CA) then `lane-vm-test-certs> Certificate will expire`; `error: Cannot build '/nix/store/h9l59d7r…-lane-vm-test-certs.drv'. Reason: builder failed with exit code 1.` Every VM derivation is reported only as `Reason: 1 dependency failed` — **no VM booted**, exactly as the section demands |
| M2 | yes (row 2, arm a) | the leaf guard moved above the `openssl x509 -req` that writes it (`lane-vm.nix`) | `lane-vm` | **KILLED.** `lane-vm-test-certs> Could not open file or uri for loading certificate from /nix/store/pidcrz2z…-lane-vm-test-certs/openrouter.test.crt: No such file or directory`, `builder failed with exit code 1` |
| M3 | yes (row 2, arm b) | the leaf guard repointed at `ca.crt` (so only `ca.crt` is guarded) **and** `-days 2` restored on the leaf | `lane-vm` | **SURVIVED — as the section predicts** ("a short-lived leaf passes"). Build exit 0, VM green today, `grep -c 'will expire'` = 0. This arm is the discrimination, not a kill target: it shows the guard must name the leaf. The shipped code does (`lane-vm.nix:25`, `seat-vm.nix:26`, `broker-vm.nix:21`), and M1/O1/O5 prove that guard is live, so the assertion holds |
| O1 | no | `broker-vm.nix:20` leaf `-days 2` (inside the host loop) | `integration` | **KILLED.** `test-certs> Certificate will expire`, `error: Cannot build '/nix/store/8lwvja8z…-test-certs.drv'` — the in-loop guard is load-bearing |
| O2 | no | `seat-vm.nix:18` CA `-days 2` | `seat-vm` | **KILLED.** `seat-vm-test-certs> Certificate will expire` |
| O3 | no | `broker-vm.nix:13` CA `-days 2` | `integration` | **KILLED.** `test-certs> Certificate will expire` |
| O4 | no | `lane-vm.nix:17` CA `-days 2` | `lane-vm` | **KILLED.** `lane-vm-test-certs> Certificate will expire` |
| O5 | no | `seat-vm.nix:24` leaf `-days 2` | `seat-vm` | **KILLED.** `seat-vm-test-certs> Certificate will expire` |
| O6 | no | both `lane-vm.nix` guards slackened to `-checkend 0`, leaf `-days 2` | `lane-vm` | **SURVIVED** by construction — a 2-day cert is not expired *today*. Shows `31536000` is the load-bearing constant, and that a disarmed guard is invisible to the suite (MINOR-1) |
| O7 | no | both `lane-vm.nix` guard lines deleted | `lane-vm` | **SURVIVED** by construction — exit 0. Nothing outside the guard notices the guard's removal (MINOR-1) |

M1 and O1–O5 together cover **all six** `openssl` lines the section names: each one, reverted alone,
fails its own `*-test-certs` derivation with `Certificate will expire` before any VM starts. The
guard is therefore live on every certificate the three blocks write, including both leaves in
`broker-vm.nix`'s loop.

mutants_total 10, mutants_killed 7, mutants_outside_named 7. No named mutant survives against its
own kill criterion; the one named survivor (M3) is the section's stated "a short-lived leaf passes"
arm, whose criterion the shipped code satisfies.

## Checks

Run in the fresh clone at `f08e963`.

| check | command | result |
|---|---|---|
| `lane-vm` | `nix build .#checks.x86_64-linux.lane-vm -L --no-link --rebuild` | **exit 0** — `vm-test-run-lane-openrouter> test script finished in 13.22s` / `kill QemuMachine (pid 45)` / `(finished: cleanup, in 0.10 seconds)` |
| `seat-vm` | `nix build .#checks.x86_64-linux.seat-vm -L --no-link --rebuild` | **exit 0** — `vm-test-run-seat-behind-broker> test script finished in 23.92s` / `(finished: cleanup, in 0.12 seconds)` |
| `integration` (broker-vm.nix, Assumption 3) | `nix build .#checks.x86_64-linux.integration -L --no-link --rebuild` | **exit 0** — `vm-test-run-egress-broker> test script finished in 21.80s` / `(finished: cleanup, in 0.09 seconds)` |
| lint gate | `nix develop -c githooks/pre-commit` | exit 1 on one line only: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`. The regeneration removes exactly `VC1` and `2026-09-08-vm-test-certs.md` from the queue line, because `tasks.py` reads "landed" from `git log` subjects (`pkgs/evidence/tasks.py:618`, `:1508`) and this branch carries VC1's subject. The same hook at the base `4491aa2` is **exit 0** (`render.test.mjs: all assertions passed`), verified in a separate checkout; with the regenerated board staged the hook is **exit 0**. Committing the board would have been the breach (Global Constraints) — **not a finding** |
| board / MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0, no diff (no new files) |
| task metadata | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | exit 0, silent (the only output is nix's own `Git tree … is dirty` / `nixfmt-rfc-style` warnings) |
| ruff | n/a | no python in the diff; `githooks/pre-commit` runs ruff over the tree anyway and is green once the board is staged |

## Touches and commit

- Diff files: `tests/integration/broker-vm.nix`, `tests/integration/lane-vm.nix`,
  `tests/integration/seat-vm.nix` — exactly the section's `touches`, nothing outside it, no
  `docs/MAP.md` change needed, no board commit, the plan file untouched.
- `git rev-list --count 4491aa2..HEAD` → **1**.
- Subject byte-identical: `git log -1 --format=%s` compared with the section's string via `cmp` →
  identical (em dash and all).
- Body: states the why (the nightly's expired two-day fixture), records that Assumption 1 held and
  the red came from the failing VM test rather than the mutant, lists the three greens and the
  pre-commit green, and reports the Step 4 mutant's red and its revert.
- Trailers: a blank line, then `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat
  headless, factory run vc1)` and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` as the
  last two lines (`git log -1 --format=%B | tail -4 | cat -A`).
- `checks_scope: dirty` is the branch-diff property (the committed diff touches test files), not an
  uncommitted change: `git status --porcelain` in the fresh clone is empty before the hook runs.

## Findings

**MINOR-1 — the guard is its own only test.** `tests/integration/lane-vm.nix:24-25` (same at
`seat-vm.nix:25-26`, `broker-vm.nix:21,23`): deleting both guard lines (mutant O7) or slackening the
threshold to `-checkend 0` with a `-days 2` leaf (mutant O6) leaves `lane-vm` **exit 0** today, so a
later edit that drops or disarms the guard re-opens the whole class silently and is caught again only
by the calendar. This is the plan's own D2 trade-off ("the guard IS the test") and no contract
requires more; recorded, not owed.

**MINOR-2 — the 365-day window is wider than the failure mode.** `31536000` accepts any certificate
with more than a year left, so a future `-days 400` fixture would pass the guard and still expire
inside a long-lived store cache. The section specifies that constant verbatim and the seat
implemented it verbatim; a plan-side note, not an implementer defect.

**MINOR-3 — the body's red is elided, not pasted.** The commit body renders the Step 1 red as
``AssertionError: {... "Certificate verify failed: certificate has expired" ...}`` rather than the
literal line Step 5 asks for. The elision is faithful — I reproduced the full line at the base
(above) and it matches — but the paste is not verbatim.

No MAJORs.

## Verdict

**APPROVED.** Every numbered contract item is met at the line level; all six `-days` lines are
guarded and each, mutated alone, kills its own derivation before a VM boots; the red existed
independently of the seat's word and the three VM checks are green under `--rebuild`; one commit,
byte-exact subject, both trailers, no file outside `touches`, no board commit. The only red command
is the derived board queue block, which the Global Constraints forbid the seat to commit and which is
green at the base and green again once staged.
