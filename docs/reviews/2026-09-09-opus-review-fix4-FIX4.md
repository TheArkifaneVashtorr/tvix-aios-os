---
plan_defect: none
mutants_total: 5
mutants_killed: 4
mutants_outside_named: 2
model: opus
---
# Opus gate — seat run fix4, task FIX4 — APPROVED

## Summary

The contract is met literally and the mechanism is real. I re-greped the pinned
dsh store path the wrapper resolves
(`/nix/store/ljwbhn6qwcdddf7zb4glisgcsxxrzn43-dsh-0.1.2-rc.1/lib/node_modules/dsh-wrapper/node_modules/@deepseek-ai`,
from `pkgs/dsh-openrouter/default.nix:82`'s `DSH_OPENROUTER_BIN_JS`) and
confirmed the host fence end to end: `requestRejection` refuses with 403 before
authentication, `resolveLanTrust` under `--host 127.0.0.1` yields exactly the
CLI's `--trusted-host` values, and `--trusted-host` is the only producer. Three
of the plan's dsh line ranges are wrong (MINOR-2); the mechanism they describe
is right and the fix is unaffected.

Red before green reproduced independently on both arms: bats T1 fails against
the base wrapper with the branch's tests, and — I did run the second VM build —
the base wrapper answers `403` / `forbidden` on `/api/directoryPicker/list`
through the namespace relay, where the branch answers `401` / `unauthorized`.
Both named bats mutants die; the VM is its own mutant and dies. `unit`,
`seat-vm` and `lint` are green by `--rebuild`; `docs/MAP.md` regenerates
byte-identical; `tasks.py check` is silent. One commit, subject byte-identical,
both trailers, nothing outside `touches`.

The duplicated exec line is acceptable, not a MAJOR: an `exec` never returns, so
the trailing exec serves only the non-namespace branch, `shellcheck -S style` is
clean on it, and the argv is pinned by T1/T2. I record the drift risk as
MINOR-1.

## Contract items

Taken from the section's **The fix** and **Interfaces** paragraphs, literally.

1. **Under `--bind-namespace` the web exec line passes
   `--trusted-host "${bind_namespace}:${web_port}"` before `"$@"`** — MET.
   `pkgs/dsh-openrouter/dsh-openrouter.sh:799`:
   ```
   exec "$node_bin" --expose-internals "$bin_js" --profile web --patch "$overlay" --host 127.0.0.1 --trusted-host "${bind_namespace}:${web_port}" "$@"
   ```
   The authority is always concrete: `:220-222` dies 2 when `--bind-namespace`
   is given without `--port`, so `web_port` is non-empty on this path (pinned by
   the existing test "SB6b: --bind-namespace without --port dies 2 before socat").
2. **`--host 127.0.0.1` stays** — MET, on both exec lines (`:799`, `:801`); T1
   still asserts `--host 127.0.0.1` and `!= --host 10.100.4.2`
   (`tests/unit/70-dsh-openrouter.bats:1469-1470`).
3. **The socat relay stays** — MET. `:791` is unchanged from the base
   (`git diff` shows the socat line untouched), and T1 still pins
   `TCP-LISTEN:43210,bind=10.100.4.2,fork,reuseaddr` and `TCP:127.0.0.1:43210`
   (`:1479-1481`).
4. **`seat-run` untouched** — MET. `git diff 9f8dcad..HEAD --stat` lists three
   files; `pkgs/seat/seat-run.py` is not among them.
5. **No `--trusted-host` without `--bind-namespace`** — MET.
   `pkgs/dsh-openrouter/dsh-openrouter.sh:801` is the base line verbatim; asserted
   by T2 at `tests/unit/70-dsh-openrouter.bats:1503`.
6. **"Nothing else changes"** — MET. The wrapper diff is +8 lines: one exec and
   seven comment lines. No other production file changed.
7. **Interfaces: "one flag on the dsh command line, only under
   `--bind-namespace`; the seat's API answers through the relay exactly as on
   loopback"** — MET and tested. The flag is a producer of exactly one value:
   `dsh-web-app/lib/startup.js:46` `trustedHosts: options.trustedHost ?? []`,
   fed to `resolveLanTrust(ctx.webServer.host, config.trustedHosts)` at
   `dsh-web-app/lib/index.js:181`; with `--host 127.0.0.1` (≠ the all-interfaces
   host) `lanAddresses` is `[]` (`index.js:92`), so `trustedHosts` is exactly the
   flag's values. "Exactly as on loopback" is exercised by VM V1/V2 (401 +
   `unauthorized`, and explicitly not `forbidden`).

### The mechanism, re-greped in the pinned store path

`grep -n 'isTrustedApiRequest\|requestRejection\|forbidden\|unauthorized' …/dsh-client-connection/lib/index.js`:
```
178:function isTrustedApiRequest(request, trustedHosts) {
183:	if (!isLoopbackHostname(hostUrl.hostname) && !isTrustedAuthority(hostUrl, trustedHosts)) return false;
530:	requestRejection(request) {
531:		if (!isTrustedApiRequest(request, this.trustedHosts)) return 403;
582:				res.end(rejection === 401 ? "unauthorized" : "forbidden");
709:				res.end(rejection === 401 ? "unauthorized" : "forbidden");
```
and `:532` `return this.browserAuth.isAuthenticated(request) ? void 0 : 401;` —
the fence does run before authentication, exactly as the section says.
`dsh-client-connection/lib/client.js:4371` is `case "directoryPicker/list":` as
cited. `--trusted-host <authority...>` is declared at
`dsh-web-app/lib/startup.js:22`.

I also checked that the variadic `<authority...>` does not swallow the seat's
next argument. Against the bundled commander, both orderings parse identically:
```
["--host","127.0.0.1","--trusted-host","10.100.4.2:43210","--no-open","--port","43210"]
  => {"open":false,"host":"127.0.0.1","trustedHost":["10.100.4.2:43210"],"port":"43210"}
```

## Red before green

**bats T1 (named red).** Fresh copy of the branch, base wrapper restored
(`git checkout 9f8dcad -- pkgs/dsh-openrouter/dsh-openrouter.sh`), branch tests:
```
1..2
not ok 1 --bind-namespace with --broker passes --host 127.0.0.1 and spawns socat with bind, port and target
# (in test file tests/unit/70-dsh-openrouter.bats, line 1472)
#   `[[ "$argv_flat" == *"--trusted-host 10.100.4.2:43210"* ]]' failed
ok 2 --broker without --bind-namespace spawns no socat (dsh still binds 127.0.0.1)
```
Restored to HEAD, same filter, in the clone:
```
ok 1 --bind-namespace with --broker passes --host 127.0.0.1 and spawns socat with bind, port and target
ok 2 --broker without --bind-namespace spawns no socat (dsh still binds 127.0.0.1)
```
T2 passes on the base by construction — its named mutant is "pass it
unconditionally", killed below.

**VM V1 (named red), run rather than taken from the seat's paste.** A second
copy with the base wrapper and the branch's `seat-vm.nix`, with the V1 wait
shortened to `timeout=20` and two probes added so the failure prints its cause:
```
GATE-PROBE-WEB code=403
GATE-PROBE-WEB body=forbidden
machine: waiting for success: test "$(curl -s --max-time 5 -o /dev/null -w '%{http_code}' http://10.100.4.2:43201/api/directoryPicker/list)" = 401
!!! RequestedAssertionFailed: action timed out after 20.59 seconds (timeout=20.0)
error: Cannot build '/nix/store/nm3qrfhid7k5pp2ryhz99kqfmas3x0vb-vm-test-run-seat-behind-broker.drv'.
```
Green, unmodified branch, `--rebuild`:
```
machine: (finished: waiting for success: test "$(curl ... http://10.100.4.2:43201/api/directoryPicker/list)" = 401, in 0.04 seconds)
machine: (finished: waiting for success: curl ... | grep -q 'unauthorized', in 0.03 seconds)
machine: (finished: waiting for success: ! curl ... | grep -q 'forbidden', in 0.03 seconds)
```
and the same three for the drive seat on `:43202` (V2). Only the timeout and the
two probe lines were altered for the red; the assertion itself is the branch's.
So the seat's pasted 900 s timeout is confirmed as the same failure, measured
here in 20 s.

No test in this diff can pass unconditionally: each of T1, T2, V1 and V2 was
shown failing against an implementation that lacks the change.

## Mutants

| # | mutant | named by the section | test that must kill it | result |
|---|---|---|---|---|
| M1 | drop `--trusted-host "${bind_namespace}:${web_port}"` from `dsh-openrouter.sh:799` | yes | bats T1 | **killed** — `line 1472: [[ "$argv_flat" == *"--trusted-host 10.100.4.2:43210"* ]]' failed` |
| M2 | pass `--trusted-host "${bind_namespace}:${web_port}"` on the unconditional exec `:801` too (empty authority off the namespace path) | yes | bats T2 | **killed** — `line 1503: [[ "$argv_flat" != *"--trusted-host"* ]]' failed` |
| M3 | the base wrapper itself (the VM is its own mutant) | yes | seat-vm V1/V2 | **killed** — `GATE-PROBE-WEB code=403` / `body=forbidden`, V1 times out |
| M4 | port-less authority: `--trusted-host "${bind_namespace}"` | no | bats T1 | **killed** — `line 1472 … failed` (note: this mutant would in fact still work at runtime — `isTrustedAuthority` matches a port-less entry on any port — so T1 is stricter than the fence) |
| M5 | move the flag after `"$@"` (violates the section's stated "before `\"$@\"`") | no | T1/T2 | **survived** — and provably not a defect: the commander probe above shows both orderings yield `trustedHost: ["10.100.4.2:43210"]`. Recorded as MINOR-3, not a MAJOR |

`mutants_total: 5`, `mutants_killed: 4`, `mutants_outside_named: 2` (M4, M5).
Every mutant was applied in a scratch copy and reverted; the clone's tree is
clean (`git status --porcelain` empty).

## Checks

All in the fresh clone at `6e6fcdc`, `nix build … -L --no-link --rebuild`.

| check | result |
|---|---|
| `unit` | **pass**, exit 0 — 680 `ok`, zero `not ok` |
| `seat-vm` | **pass**, exit 0 — `test script finished in 37.62s`, all six FIX4 assertions (`43201` and `43202`) succeed in ≤0.04 s each |
| `lint` | **pass**, exit 0 |
| `nix develop -c githooks/pre-commit` | exit 1, **one line only**: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`. The regenerated diff is exactly the queue line dropping `FIX4` and `2026-09-09-bugs.md` — i.e. the block is stale *because FIX4 lands on this branch*. Per the plan's Global Constraint this is the orchestrator's board drift, not the seat's; the seat correctly left `docs/OPERATIONS.md` out of the commit. Everything else in the hook is green (the `tests/lint/fixtures/js/bad.mjs` eslint errors are the lint self-test's expected reds). Recorded as MINOR-5. |
| `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | **exit 0** — no change owed |
| `python3 pkgs/evidence/tasks.py --root . check` | **silent**, exit 0 |
| `shellcheck -S style pkgs/dsh-openrouter/dsh-openrouter.sh` | exit 0 |
| ruff | n/a — no `.py` in the diff |

## Touches and commit

`git diff 9f8dcad..HEAD --stat`:
```
 pkgs/dsh-openrouter/dsh-openrouter.sh |  8 ++++++++
 tests/integration/seat-vm.nix         | 23 +++++++++++++++++++++++
 tests/unit/70-dsh-openrouter.bats     |  6 ++++++
 3 files changed, 37 insertions(+)
```
All three are in the section's `touches`. `docs/MAP.md` is in `touches` by rule
and needs no change (verified above). Nothing outside the list; no Deviation
line is owed. The plan file is untouched; `docs/OPERATIONS.md` is not committed.

Exactly one commit, `6e6fcdc`. Subject compared byte-for-byte against the
section's:
```
$ cmp subj.txt expect.txt && echo "SUBJECT BYTE-IDENTICAL"
SUBJECT BYTE-IDENTICAL
```
Body states the why, and pastes the red (`unit T1 … line 1472`; `seat-vm …
timed out after 900.06s`) and the green. Trailers, after a blank line:
```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run fix4)$
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>$
```

## Findings

No MAJORs.

**MINOR-1 — the duplicated exec line.**
`pkgs/dsh-openrouter/dsh-openrouter.sh:799` and `:801` are the same 11-token
command differing only by `--trusted-host`. It is *correct*: `exec socat … &`
runs in a background subshell so the parent continues, `:799` then replaces the
parent and never returns, and `:801` therefore serves only the non-namespace
case. `shellcheck -S style` is clean and both argvs are pinned by T1/T2. The
cost is drift: a future change to the web exec (a new flag, a different profile,
`--expose-internals` removed) must be made twice or the namespace path silently
diverges. A single exec with a conditional argument array —
```
trust_args=(); [ -n "$bind_namespace" ] && trust_args=(--trusted-host "${bind_namespace}:${web_port}")
exec "$node_bin" --expose-internals "$bin_js" --profile web --patch "$overlay" --host 127.0.0.1 "${trust_args[@]}" "$@"
```
— would remove it. Acceptable as landed; worth a follow-up, not a gate.

**MINOR-2 — three of the plan section's dsh citations are wrong (plan defect,
class `wrong-fact`; non-gating).** The section's item 1 cites
`dsh-client-connection/lib/index.js:571-582` for `isTrustedApiRequest` (it is
`:178-190`; `:571-582` is the `register` route handler) and `:558-563` for the
`forbidden` end (it is `:582`, and `:709` for the index route). Item 2 cites
`dsh-web-app/lib/index.js:150-157` for `resolveLanTrust` (it is `:88-96`,
defined at `:91`) and `startup.js:44-49` for the flag (the `--trusted-host`
option is declared at `:22`; only `trustedHosts: options.trustedHost ?? []` at
`:46` falls in that range). Correct as cited: `index.js:531`, `index.js:181`,
`client.js:4371`, `dsh-openrouter.sh:790-793` and `:202`, the bats anchor
`:1447`, and the seat-vm anchors. The described mechanism is right in every
particular, so nothing downstream is affected — but the section instructed the
seat to re-grep, and a reader taking those ranges at face value lands nowhere.

**MINOR-3 — the contract's "before `\"$@\"`" ordering has no test.**
`tests/unit/70-dsh-openrouter.bats:1472` matches the flag anywhere in the flat
argv, so M5 (the flag moved after `"$@"`) survives. I proved the two orderings
parse identically against the bundled commander, so no behaviour is at risk;
recording it only because the section states the position and nothing pins it.

**MINOR-4 — `tests/unit/70-dsh-openrouter.bats` leaks an ambient
`NODE_EXTRA_CA_CERTS` into the test at `:1569`.** `setup()` at `:28` unsets nine
variables but not `NODE_EXTRA_CA_CERTS`, and the test at `:1569` asserts the
wrapper exits 5 *because* that variable is absent. Reproduced:
```
$ NODE_EXTRA_CA_CERTS=<an existing file> nix develop -c bats --filter 'without NODE_EXTRA_CA_CERTS exits 5' tests/unit/70-dsh-openrouter.bats
not ok 1 --broker without NODE_EXTRA_CA_CERTS exits 5
# (in test file tests/unit/70-dsh-openrouter.bats, line 1574)
#   `[ "$status" -eq 5 ]' failed
```
This is the seat's reported "test 99 fails on a direct `bats` run" and it is
**environmental, pre-existing and outside FIX4's contract**: adding
`NODE_EXTRA_CA_CERTS` to the `:28` unset list would fix it. In my clone the
direct run of the whole file is green (exit 0, zero `not ok`) and the `unit`
check is green, because neither environment exports the variable — which is also
why the check can never catch it. Worth recording so the next seat run in a
sandbox that sets it is not sent chasing a phantom.

**MINOR-5 — `githooks/pre-commit` exits 1 on the board queue block.** See
Checks. The single failing line is G8c and the regenerated diff is exactly
`FIX4`/`2026-09-09-bugs.md` leaving the queue, which is what landing FIX4 on this
branch necessarily does. The seat behaved per the Global Constraint: it did not
stage or commit `docs/OPERATIONS.md` and did not `--no-verify`. Nothing owed by
the seat; the orchestrator's board commit closes it.

## Verdict

**APPROVED.** Every numbered contract item is met at the cited line; both named
bats mutants and the named VM mutant die; the reds were reproduced here, the VM
one by a second build rather than from the seat's paste; `unit`, `seat-vm` and
`lint` are green by `--rebuild`; `MAP.md` and `tasks.py check` are clean; one
commit, byte-identical subject, both trailers, nothing outside `touches`. Five
MINORs, none gating: the exec duplication (MINOR-1), four wrong line ranges in
the plan section (MINOR-2, `wrong-fact`), the untested flag position (MINOR-3),
the bats file's `NODE_EXTRA_CA_CERTS` leak (MINOR-4), and the board queue drift
(MINOR-5).
