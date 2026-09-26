---
reviewer: opus
majors: 1
minors: 6
---
# Opus gate — seat run sb4, task SB2 — REJECTED

## Summary

Branch `task/SB2` in `/home/dalhaka/factory/ws/sb4/SB2`, base `e78217a`, head
`6253496`, one commit, two files (`pkgs/dsh-openrouter/dsh-openrouter.sh` +78,
`tests/unit/70-dsh-openrouter.bats` +109). Reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-sb4-SB2`.
Nothing under `/home/dalhaka/factory` was touched; every run used a fixture
`HOME`, a fake key file, the bats file's own fake upstream
(`tests/mocks/openai-fake.py`), and a fake `ip` on `PATH`. The operator's real
key file was never read and the real OpenRouter was never contacted (proved
below with `strace -e trace=connect`: zero non-`AF_UNIX` `connect()` calls in
the one test that boots the real harness).

The credential half is right and I could not break it. Under `--broker` the key
file is never opened, never `stat`'ed, and never `lstat`'ed — proved with
`strace` against a control run that shows the same filter catching six syscalls
on the key path when `--broker` is absent. The placeholder reaches the fake
upstream as `Bearer injected-by-broker`. The namespace refusal holds under every
route shape I could produce, including a missing `ip`. All five claimed checks
pass, shellcheck is clean, the six new tests are genuinely red on main's
wrapper, `hook-guard.py` is byte-identical to base, and the commit subject is
byte-identical to the plan's.

One MAJOR: contract item (2) is half untested. The `NODE_EXTRA_CA_CERTS`
requirement can be deleted from the wrapper entirely and all 95 tests stay
green (mutation M-C2, the row the gate's matrix required to die). The
implementation of that requirement is correct today; nothing pins it tomorrow.
That is a required mutation surviving, so this is a reject under the gate rule,
and the fix is one bats test.

## Credential path (what `--broker` reads and sends)

`pkgs/dsh-openrouter/dsh-openrouter.sh:252-255` — under `--broker` the whole
key block (`:256-283`) is skipped by an `if/elif/else`, so there is no path
into `stat`, `head -n 1`, or the mode check.

Method for "never read": `strace -f -e trace=openat,open,stat,lstat,newfstatat,statx`
over the wrapper (the fixture key file was mode 000 in one run and absent in
another), then `grep 'openrouter/key'` over 20 564 traced syscall lines.

```
### 1a: mode-000 key file, strace
exit=0
BROKER-OK
authorization= 'Bearer injected-by-broker'
authorization= 'Bearer injected-by-broker'
total syscall lines: 20564
NONE -- key path never appears in any openat/open/stat/lstat/newfstatat/statx
```

Control run, same strace filter, same fixture, `--broker` removed (this proves
the instrument is sensitive, not that the syscalls are missing):

```
### 1-control: no --broker, 0600 key file, same strace filter
-- key path lines seen by strace: 6
3226943 newfstatat(AT_FDCWD, ".../.config/openrouter/key", {st_mode=S_IFREG|0600, ...}, 0) = 0
3226943 newfstatat(AT_FDCWD, ".../.config/openrouter/key", {st_mode=S_IFREG|0600, ...}, AT_SYMLINK_NOFOLLOW) = 0
3226943 newfstatat(AT_FDCWD, ".../.config/openrouter/key", {st_mode=S_IFREG|0600, ...}, 0) = 0
-- authorization seen by the fake: 'Bearer sk-or-REAL-SECRET'
```

Key file **absent** under `--broker`: exit 0, `Bearer injected-by-broker`.
`OPENROUTER_KEY_FILE` is likewise never consulted under `--broker`.

What can still leave the process: a pre-set `OPENROUTER_API_KEY`. With
`OPENROUTER_API_KEY=sk-or-fixture` in the environment, `--broker` forwards it
verbatim (`Bearer sk-or-fixture` reached the fake upstream) while the launch
banner says `key from injected-by-broker`. This matches the contract as
written ("set to `injected-by-broker` **if unset**") and SB1's unit sets the
placeholder, so it is MINOR-1, not a MAJOR — the wrapper sources no key of its
own under `--broker`.

`--dump-config` under `--broker`: `apiKeyEnv: OPENROUTER_API_KEY` (line 67 of
the dump), zero occurrences of `sk-or-`, `injected-by-broker` or the proxy URL
in the dump, and a recursive scan of the fixture `HOME` after the run finds the
proxy URL and the placeholder in no file at all.

## Rule behaviour

Fixtures: bats-shaped fixture `HOME`; `make_key`; fake `ip` on `PATH`;
`make_ca`; `dsh-openrouter --broker --dump-config` unless noted.

| row | expected | observed | exit |
|---|---|---|---|
| `--broker`, key mode 000, headless via fake | 0, `Bearer injected-by-broker`, no key read | as expected; 0 strace hits on the key path | 0 |
| `--broker`, key file absent | same | `BROKER-NOKEYFILE-OK`, `Bearer injected-by-broker` | 0 |
| `--broker`, `OPENROUTER_API_KEY=sk-or-fixture` | contract: pass through | `Bearer sk-or-fixture` upstream; banner says `key from injected-by-broker` | 0 |
| no `HTTPS_PROXY` | 5 | `--broker needs HTTPS_PROXY (or https_proxy) set to http://<host>:<port>` | 5 |
| `HTTPS_PROXY=` (empty) | 5 | same message | 5 |
| `https_proxy` lowercase | accepted | launched | 0 |
| `HTTPS_PROXY=https://10.100.4.1:3141` | 5 | `HTTPS_PROXY must be http://<host>:<port> (got 'https://…')` | 5 |
| `HTTPS_PROXY=socks5://10.100.4.1:3141` | 5 | same shape message | 5 |
| `HTTPS_PROXY=http://10.100.4.1` (no port) | 5 | same shape message | 5 |
| `HTTPS_PROXY=http://:3141` (empty host) | 5 | same shape message | 5 |
| `HTTPS_PROXY=http://*:3141` (glob host) | must not bypass | `--broker outside a broker namespace` (bash does not re-glob the expansion inside the quoted `case` pattern — verified separately: NOMATCH) | 5 |
| `HTTPS_PROXY=http://broker.host:3141` (hostname) | contract compares to the proxy host string | `--broker outside a broker namespace` — a hostname never equals the route's numeric `via`, so a named proxy is always refused | 5 |
| `NODE_EXTRA_CA_CERTS` unset | 5 | `--broker needs NODE_EXTRA_CA_CERTS set to the broker's CA bundle` | 5 |
| `NODE_EXTRA_CA_CERTS` empty string | 5 | same | 5 |
| `NODE_EXTRA_CA_CERTS` missing file | 5 | `NODE_EXTRA_CA_CERTS (…) is not an existing file` | 5 |
| `NODE_EXTRA_CA_CERTS` a directory | say | `-f` rejects it: `… is not an existing file` | 5 |
| route (a) `default via 10.100.4.1 dev veb0`, proxy `10.100.4.1` | allowed | launched | 0 |
| route (b) `via 192.168.1.1` | 5 | `--broker outside a broker namespace` | 5 |
| route (c) two default routes | 5 | same | 5 |
| route (c2) two routes, one correct | 5 | same | 5 |
| route (d) no default route (empty output) | 5 | same | 5 |
| route (e) `ip` exits non-zero | 5 | same | 5 |
| route (f) `ip` missing from `PATH` | 5, not a crash, not an allow | `ip: command not found` then `--broker outside a broker namespace` | 5 |
| route ECMP `default\n\tnexthop via 10.100.4.1 …` | conservative refusal | two lines ⇒ n≠1 ⇒ refused | 5 |
| route `default dev veb0 scope link` (no via) | 5 | same | 5 |
| route `via 10.100.4.11` vs proxy `10.100.4.1` | 5 (no prefix confusion) | same | 5 |
| synthetic `default via 192.168.1.1 dev via 10.100.4.1 x` | should refuse | **accepted** — substring match, see MINOR-3 (real `ip` cannot emit this) | 0 |
| `--bind-namespace 10.100.4.2 --broker` web argv | `--host 10.100.4.2` | `exec node --expose-internals … --host 10.100.4.2 --no-open --port 43210` | — |
| `--broker` alone, web argv | `--host 127.0.0.1` | `… --host 127.0.0.1 --no-open --port 43210` | — |
| `--bind-namespace` without `--broker` | 2 | `the browser UI binds 127.0.0.1 only; --bind-namespace needs --broker` | 2 |
| `--host` passthrough (pre-existing) | 2 | `the browser UI binds 127.0.0.1 only; --host is not accepted` | 2 |
| `--bind-namespace` with no value | 2 | `--bind-namespace needs a value` | 2 |
| `--bind-namespace 0.0.0.0` | say | accepted, argv `--host 0.0.0.0` — see MINOR-2 | — |
| `--bind-namespace 'not an address'` / `'--profile'` / `'10.100.4.2 --danger-full-access'` | say | accepted, each stays exactly one argv element (`--host 'not an address'`); no argv injection, no shell expansion (`$(touch /tmp/pwned-sb2)` created nothing) | — |
| key-file path without `--broker` | exactly one added stderr line | stdout byte-identical to main's wrapper; stderr diff is exactly `0a1 > dsh-openrouter: the key file is deprecated; seat jobs run behind the broker (docs/runbooks/seat.md)` | 0 |
| `OPENROUTER_API_KEY` env path | no deprecation line | 0 occurrences | 0 |
| `--broker` | no deprecation line | 0 occurrences | 0 |
| hooks.json under `--broker`, routing table path with a quote and a space | RT5rb escaping holds | parses; `exec '…/hook-guard' --routing-table '/tmp/…/a "quoted" path/routing.toml'`, all three matchers | 0 |
| production shape: SB1's unit `Environment` verbatim + fake ip/upstream | allowed | `PROD-OK`, `Bearer injected-by-broker` | 0 |
| same, `HTTPS_PROXY=http://10.100.9.1:3141` (not the route's via) | 5 | `--broker outside a broker namespace` | 5 |

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| command | exit |
|---|---|
| `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | 0 (silent) |
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 0 — 95/95 (89 RT5rb + 6 SB2) |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0 — 286 tests |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 |
| `nix develop -c githooks/pre-commit` | 1 then 0 |

The lint gate's first run in a fresh clone regenerates the derived board block
(`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`) —
the diff is only SB2 dropping out of the queued list now that its commit is in
the tree. That is the one-shot the plan's Global Constraints describe; the
second run is exit 0 with `All checks passed!`. `docs/OPERATIONS.md` is
correctly **not** in the commit (it is not in `touches`, and board commits are
dropped at integration). I reverted it; the tree is clean at `6253496`.

Implementer's claims, checked: "6 new bats tests (95/95 pass)" — true.
"unit, host-core, lint pass" — true, including `--rebuild`.
"`DSH_OPENROUTER_BIN_JS` cannot be env-stubbed (runtimeEnv re-exports it)" —
**true**, and stronger than stated: a `PATH`-level fake `node` is also useless,
because `writeShellApplication` prepends `runtimeInputs` (which carry
`nodejs_22`) to `PATH`, so the fake is shadowed. I confirmed this by putting a
fake `node` recording `argv` in the same directory as the fake `ip`: the fake
never ran. The `bash -x` trace is therefore a defensible way to pin the argv;
see MINOR-5 for its one weakness.

## Red before green

`git show e78217a:pkgs/dsh-openrouter/dsh-openrouter.sh` into the clone in place
of SB2's, SB2's tests kept, `git add` (flakes only see tracked files), then
`nix develop -c bats tests/unit/70-dsh-openrouter.bats`:

```
not ok 90 --broker skips the key block: a mode-000 key file launches headless and sends the placeholder credential
not ok 91 --broker without HTTPS_PROXY exits 5
not ok 92 --broker with a default route via another gateway exits 5
not ok 93 --bind-namespace with --broker replaces the web --host 127.0.0.1 with the namespace address
not ok 94 --bind-namespace without --broker is rejected like --host
not ok 95 the key-file path prints a deprecation line on stderr
```

Exactly the six new tests, and no other test regressed. Restored to `6253496`,
95/95 green.

## Mutation table

Applied to the wrapper, `git add`ed, tree hash asserted changed before each
run, reverted after. Full bats file each time.

| mutation | expected | result |
|---|---|---|
| M-A key block not skipped under `--broker` (`broker -eq 1` → `-eq 9`) | dies | killed by 90 |
| M-B placeholder not set (`${OPENROUTER_API_KEY:-}`) | dies | killed by 90 |
| M-C `[ -n "$proxy" ] \|\| die 5` removed | dies | **survived — equivalent mutant** (see below) |
| M-C1b (extra) whole `HTTPS_PROXY` requirement removed: emptiness **and** shape check | dies | **survived — equivalent mutant** |
| M-C2 the `NODE_EXTRA_CA_CERTS` requirement removed (both lines) | dies | **SURVIVED — real** → MAJOR-1 |
| M-D route check accepts any single default route | dies | killed by 92 |
| M-D2 route check removed entirely | dies | killed by 92 |
| M-E `--bind-namespace` ignored (`--host 127.0.0.1`) | dies | killed by 93 |
| M-F `--bind-namespace` accepted without `--broker` | dies | killed by 94 |
| M-G deprecation line removed | dies | killed by 95 |
| M-H exit codes swapped 5 ↔ 2 | dies | killed by 91, 92, 94 |
| rt8 M-A `json.loads` hoisted out of `main()`'s `BaseException` region (hook-guard.py) | dies | killed by 76, 77 |

Killed 9 of 12. M-C and M-C1b are **equivalent mutants**, not gaps: I ran the
mutated wrappers directly and every input the removed guard covered is still
refused with exit 5 by the checks that remain (`[ -n "$proxy_host" ]` and the
route comparison):

```
### M-C1b
  HTTPS_PROXY unset, CA ok            exit=5  --broker: HTTPS_PROXY must be http://<host>:<port> (got '')
  HTTPS_PROXY=socks5://10.100.4.1:1   exit=5  --broker outside a broker namespace
```

M-C2 is a real survivor — behaviour changes and no test notices:

```
### M-C2
  HTTPS_PROXY unset, CA ok            exit=5  --broker needs HTTPS_PROXY …
  CA unset, proxy ok                  exit=0
  CA missing file, proxy ok           exit=0
```

## Findings

### MAJOR-1 — the `NODE_EXTRA_CA_CERTS` half of contract item (2) has no test; the guard can be deleted and the suite stays green

`pkgs/dsh-openrouter/dsh-openrouter.sh:301-302`

```
  [ -n "${NODE_EXTRA_CA_CERTS:-}" ] || die 5 "--broker needs NODE_EXTRA_CA_CERTS set to the broker's CA bundle"
  [ -f "$NODE_EXTRA_CA_CERTS" ] || die 5 "--broker: NODE_EXTRA_CA_CERTS ($NODE_EXTRA_CA_CERTS) is not an existing file"
```

Evidence: mutation M-C2 deletes both lines; `nix develop -c bats
tests/unit/70-dsh-openrouter.bats` is 95/95 green with the guard gone, and the
mutated wrapper then launches (`exit=0`) with `NODE_EXTRA_CA_CERTS` unset and
with it pointing at a missing file — see the M-C2 block above. Every SB2 test
that exercises the broker path (`tests/unit/70-dsh-openrouter.bats:1360, 1385,
1396, 1408`) sets `NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt"` and none removes it,
so the negative case is never taken. The `make_ca` helper at
`tests/unit/70-dsh-openrouter.bats:1355` exists only to satisfy the guard, never
to test it.

Why it matters rather than being pedantry: that bundle is the only thing that
makes the harness trust the broker's terminating CA. The guard is the seat's
fail-fast for a unit that lost `NODE_EXTRA_CA_CERTS`; unpinned, a later
refactor of this block (SB4/SB5 both touch this area) removes it silently and
the failure surfaces as an opaque TLS error inside a namespace instead of a
one-line refusal. The plan's Interfaces line names `NODE_EXTRA_CA_CERTS`
alongside `HTTPS_PROXY` in the same `die 5` clause; the Step-1 test list names
only the `HTTPS_PROXY` case, which is how this got missed — the implementation
itself is correct.

Fix: two tests appended next to the existing ones, same fixture, e.g.

```bash
@test "--broker without NODE_EXTRA_CA_CERTS exits 5" {
  make_key; make_ip 10.100.4.1
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=http://10.100.4.1:3141 \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"NODE_EXTRA_CA_CERTS"* ]]
}

@test "--broker with a NODE_EXTRA_CA_CERTS that is not an existing file exits 5" {
  make_key; make_ip 10.100.4.1
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/nope.crt" run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"is not an existing file"* ]]
}
```

Both are red under M-C2 and green on HEAD (I ran the equivalent commands by
hand; see the Rule behaviour rows).

### MINOR-1 — a pre-set `OPENROUTER_API_KEY` passes through `--broker` while the banner claims the placeholder

`pkgs/dsh-openrouter/dsh-openrouter.sh:252-255`. With
`OPENROUTER_API_KEY=sk-or-fixture` set, the fake upstream received
`Bearer sk-or-fixture` and stderr said `key from injected-by-broker`. The
contract says "set to `injected-by-broker` **if unset**", so the forwarding is
compliant and SB1's unit sets the placeholder; the *banner* is not — it names a
credential that is not the one being sent. No test covers this input at all.
Fix: either set `key_source=$OPENROUTER_API_KEY (environment, behind broker)`
when the variable was already set, or (better, and still contract-compatible)
overwrite it unconditionally under `--broker` so the seat can never carry an
operator key into the namespace — then assert both in a test.

### MINOR-2 — `--bind-namespace` takes any string unvalidated

`pkgs/dsh-openrouter/dsh-openrouter.sh:121-125` and `:677`. `0.0.0.0` is
accepted and reaches `--host 0.0.0.0`, binding the UI to every address the
namespace holds rather than the one the module intends; `--profile` becomes
`--host --profile`. There is **no** injection risk — the value stays exactly one
argv element (proved by `bash -x`: `--host '10.100.4.2 --danger-full-access'`)
and `$(…)` is never expanded. The contract does not require validation, and
SB1's `seat-run` supplies the address, so this is hardening: a
`case $bind_namespace in *[!0-9.]*|'') die 2 …` (or the same IPv4 shape check
the module uses) would close it.

### MINOR-3 — the route match is a substring test, not a field test

`pkgs/dsh-openrouter/dsh-openrouter.sh:313-315`:
`case " $the_route " in *" via $proxy_host "*)`. A default-route line that
contains `" via <proxy_host> "` anywhere is accepted; I got an allow out of the
synthetic `default via 192.168.1.1 dev via 10.100.4.1 x`. Real `iproute2`
cannot emit that (an interface named `via` is possible but the operator would
have to create it), so this is hardening only. Fix: parse the field —
`read -r _ via gw _ <<<"$the_route"; [ "$via" = via ] && [ "$gw" = "$proxy_host" ]`.

### MINOR-4 — `[ -n "$proxy" ]` at `:292` is dead weight

Every input it catches is already refused by `:299`'s `[ -n "$proxy_host" ]`
with a message that also names `HTTPS_PROXY` (mutations M-C and M-C1b are
equivalent). Harmless, but it means the "without `HTTPS_PROXY`" test at
`tests/unit/70-dsh-openrouter.bats:1385` does not pin the line it appears to.

### MINOR-5 — test 93 does not pin an exit status and green depends on the real harness failing to bind

`tests/unit/70-dsh-openrouter.bats:1408-1424`. The `bash -x` approach is
justified (I confirmed both that `DSH_OPENROUTER_BIN_JS` is re-exported by
`runtimeEnv` and that a `PATH` fake `node` is shadowed by `runtimeInputs`), but
the test asserts only on trace substrings, runs the real Node harness under a
15 s `timeout`, and passes while the process dies `Node.js v22.23.2` after
`EADDRNOTAVAIL`. Network hygiene is fine — `strace -f -e trace=connect,socket`
over exactly that command shows **zero** non-`AF_UNIX` `connect()` calls, so
nothing reaches openrouter.ai even outside the build sandbox. Suggested
tightening: also assert the trace contains `--profile web` and that the run
ends within the timeout, and pin `OPENROUTER_BASE_URL` at the fake for symmetry
with every other transport test in the file.

### MINOR-6 — `--broker` proves the proxy variables are *set*, never that traffic uses them

By design (the plan gives the traversal proof to SB4's VM), but worth stating
so it is not assumed done: in my row-1 run `HTTPS_PROXY=http://10.100.4.1:3141`
pointed at nothing that exists, and the request still reached the fake upstream
directly. The wrapper's check is a declaration. SB4 must show the audit line,
and the plan amendment about `NODE_USE_ENV_PROXY=1` / `AF_NETLINK` in
`RestrictAddressFamilies` (without which this wrapper's `ip` call dies on every
launch, giving `die 5` in production) belongs to SB1.

## Verdict

**REJECTED** — one MAJOR. The credential contract is met and proved: under
`--broker` the key file is never opened or `stat`'ed (strace, with a sensitive
control), the placeholder is what leaves the process, and the wrapper refuses
outside a broker namespace under every route shape including a missing `ip`.
`hook-guard.py` is byte-identical, RT5rb's 89 tests stay green, the escaping
holds under `--broker`, the deprecation line is byte-exact with stdout
unchanged against main, one commit, subject byte-identical, both trailers,
every touched file inside `touches`, all five checks green. The reject is
narrow: mutation M-C2 — the `NODE_EXTRA_CA_CERTS` requirement, half of contract
item (2) — survives the whole suite, which the gate's matrix required to die.
Land it as an SB2b fix round: the two bats tests in MAJOR-1, and fold MINOR-1
(the banner, or an unconditional placeholder) while the file is open. Everything
else here is hardening the next round may take or leave.
