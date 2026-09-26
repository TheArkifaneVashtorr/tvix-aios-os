---
reviewer: opus
majors: 2
minors: 6
---
# Opus gate — seat run sb5, task SB2b — REJECTED

## Summary

Branch `task/SB2b` in `/home/dalhaka/factory/ws/sb5/SB2b`, base `421c3a0`
(main), head `4611aa8`, one commit, two files
(`pkgs/dsh-openrouter/dsh-openrouter.sh` +108/-4,
`tests/unit/70-dsh-openrouter.bats` +265/-0, insertions only). Reviewed in a
fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-sb5-SB2b`.
Nothing under `/home/dalhaka/factory` was touched; every run used a fixture
`HOME`, a fake key file, the bats file's own fake upstream
(`tests/mocks/openai-fake.py`), a fake `ip` and (for the argv rows) a fake
interpreter. The operator's real key file was never read and the real
OpenRouter was never contacted.

sb4's MAJOR is fixed and the fix is real: deleting the `NODE_EXTRA_CA_CERTS`
guard now fails three tests (M-A), where it left 95/95 green last round. Six of
the seven contract items land, six of sb4's minors are closed, and the
credential half got strictly stronger — under `--broker` a pre-set
`OPENROUTER_API_KEY=sk-or-fixture` is now replaced before anything can read it,
the fake upstream sees `Bearer injected-by-broker`, and `sk-or-fixture` appears
nowhere in the fixture `HOME`. The key file is still never opened, `stat`'ed or
`lstat`'ed under `--broker` (strace, with a control run that catches six
syscalls on the same path without `--broker`). All five claimed checks pass,
106/106 bats, shellcheck clean, `hook-guard.py` byte-identical, one commit,
subject byte-identical, both trailers.

One MAJOR, and it is narrow: contract item (3) says `--bind-namespace` accepts
"only a dotted IPv4 address"; the shape regex checks the dotted-quad *shape*
but not the octet range, so `--bind-namespace 256.1.1.1` is accepted (exit 0)
and reaches the real exec argv as `--host 256.1.1.1`. The gate's required
matrix pre-committed `256.1.1.1 → 2`; observed `0`. That is a required row
failing and a contract item not fully met, so it is a reject under the gate
rule. There is no security consequence — the contract already permits any
non-loopback IPv4, so an out-of-range string adds nothing an in-range one
could not do, and Node fails closed on it — the loss is that a typo surfaces
as an opaque Node bind/DNS error inside a namespace instead of the one-line
`die 2` the plan asked for. The fix is one line: swapping the regex for an
octet-ranged one refuses all three invalid rows and leaves 106/106 green (I
ran it, below).

## Credential path (what `--broker` reads and sends)

`pkgs/dsh-openrouter/dsh-openrouter.sh:265-272` — the whole key block
(`:273-300`) is behind an `if/elif/else`, so under `--broker` there is no path
into `stat`, `head -n 1` or the mode check, and the placeholder is now
assigned **unconditionally**:

```
if [ "$broker" -eq 1 ]; then
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then
    printf 'dsh-openrouter: a pre-set OPENROUTER_API_KEY is ignored under --broker (the broker injects the real key)\n' >&2
  fi
  OPENROUTER_API_KEY=injected-by-broker
  export OPENROUTER_API_KEY
  key_source="placeholder (broker injects)"
```

Method for "never read": `strace -f -e trace=openat,open,stat,lstat,newfstatat,statx`
over the wrapper, then `grep 'openrouter/key'` over the trace.

```
### 7a: --broker, mode-000 key file, strace
  exit=0  stdout=BROKER-OK
  traced syscall lines: 20564
  key-path hits: 0
   authorization: 'Bearer injected-by-broker'
   authorization: 'Bearer injected-by-broker'
```

Control (the instrument is sensitive), same filter, `--broker` removed:

```
### 7b: no --broker, 0600 key, same filter
  key-path hits: 6
3970392 newfstatat(AT_FDCWD, ".../.config/openrouter/key", {st_mode=S_IFREG|0600, st_size=18, ...}, 0) = 0
3970392 newfstatat(AT_FDCWD, ".../.config/openrouter/key", {st_mode=S_IFREG|0600, ...}, AT_SYMLINK_NOFOLLOW) = 0
3970429 statx(AT_FDCWD, ".../.config/openrouter/key", ...) = 0
   authorization: 'Bearer sk-or-REAL-SECRET'
```

Key file **absent** under `--broker`: exit 0, `BROKER-OK`.
`OPENROUTER_KEY_FILE` pointed at a second secret under `--broker`: **0** strace
hits on that path, upstream got `Bearer injected-by-broker`.

The pre-set-key hole from sb4 (MINOR-1) is closed and I could not reopen it:

```
### 2a: --broker, OPENROUTER_API_KEY=sk-or-fixture, headless
  exit=0   stdout: BROKER-OK
  stderr:  dsh-openrouter: a pre-set OPENROUTER_API_KEY is ignored under --broker (the broker injects the real key)
           dsh-openrouter: ... key from placeholder (broker injects), workspace ...
  upstream authorization: 'Bearer injected-by-broker'  (x2)
  grep sk-or-fixture in the capture:      0
  grep -rl sk-or-fixture over $HOME:      ABSENT everywhere
  grep -rl injected-by-broker over $HOME: only capture.json (the fake's own log)
```

Without `--broker` the old paths are untouched: a pre-set env key still reaches
upstream as `Bearer sk-or-envkey` with the banner `key from OPENROUTER_API_KEY
(environment)` and no "ignored" line; the key-file path still prints exactly
the one deprecation line on stderr with `--dump-config` stdout unchanged.

## Rule behaviour

Fixtures: bats-shaped fixture `HOME`; `make_key`; fake `ip` on `PATH`;
`make_ca`; `make_fake_node` via `DSH_OPENROUTER_NODE`;
`dsh-openrouter --broker --dump-config` unless noted.

| row | expected | observed | exit |
|---|---|---|---|
| **1. CA** `NODE_EXTRA_CA_CERTS` unset | 5 | `--broker needs NODE_EXTRA_CA_CERTS set to the broker's CA bundle` | 5 |
| CA empty string | 5 | same message | 5 |
| CA missing file | 5 | `NODE_EXTRA_CA_CERTS (…/nope.crt) is not an existing file` | 5 |
| CA a directory | 5 | `… is not an existing file` (`-f` rejects it) | 5 |
| CA a readable file | proceeds | dump printed, 587 lines | 0 |
| CA a symlink to a readable file | say | accepted (`-f` follows) | 0 |
| **2. key** `--broker`, key mode 000, headless | 0, `Bearer injected-by-broker`, no key read | as expected; 0 strace hits | 0 |
| `--broker`, key file absent | same | `BROKER-OK` | 0 |
| `--broker`, `OPENROUTER_API_KEY=sk-or-fixture` | placeholder upstream, ignored-key line, truthful banner, secret absent from `HOME` | all four hold (block above) | 0 |
| `--broker`, `OPENROUTER_KEY_FILE=…/alt.key` | never opened | 0 strace hits on `alt.key` | 0 |
| no `--broker`, `OPENROUTER_API_KEY=sk-or-envkey` | unchanged | `Bearer sk-or-envkey`, banner `key from OPENROUTER_API_KEY (environment)`, no ignored line | 0 |
| **3. bind** `--bind-namespace 0.0.0.0` | 2 | `must be a dotted IPv4 address that is not 0.0.0.0 or loopback (got '0.0.0.0')` | 2 |
| `--bind-namespace 127.0.0.1` | 2 | same message | 2 |
| `--bind-namespace 127.1.2.3` | say | refused (whole `127.*` block) | 2 |
| `--bind-namespace --profile` | 2 | `needs a dotted IPv4 address (got '--profile')` | 2 |
| `--bind-namespace 10.100.4.2` | accepted | launched, `--host 10.100.4.2` on the argv | 0 |
| **`--bind-namespace 256.1.1.1`** | **2** | **accepted, `--host 256.1.1.1` on the real exec argv** — MAJOR-1 | **0** |
| `--bind-namespace 999.999.999.999` | 2 (same rule) | accepted, `--host 999.999.999.999` | 0 |
| `--bind-namespace 300.300.300.300` | 2 (same rule) | accepted, `--host 300.300.300.300` | 0 |
| `--bind-namespace ::1` (IPv6 literal) | say | `needs a dotted IPv4 address (got '::1')` | 2 |
| `--bind-namespace fe80::1` | say | same | 2 |
| `--bind-namespace ''` (empty value) | say | validation **and** the `--broker` requirement are both skipped (`[ -n … ]`); `--host` falls back to `127.0.0.1`, so it degrades safe — MINOR-4 | 0 |
| `--bind-namespace 1.2.3` / `1.2.3.4.5` | 2 | `needs a dotted IPv4 address` | 2 |
| `--bind-namespace '10.0.0.1 --danger-full-access'` | 2 | `needs a dotted IPv4 address` (sb4's argv-injection row now dies earlier) | 2 |
| `--bind-namespace 8.8.8.8` | contract allows any non-loopback IPv4 | accepted, `--host 8.8.8.8` | 0 |
| `--bind-namespace` without `--broker` | 2 | `the browser UI binds 127.0.0.1 only; --bind-namespace needs --broker` | 2 |
| **4. route** synthetic `default via 192.168.1.1 dev via 10.100.4.1 x` | 5 | `--broker outside a broker namespace` (sb4's MINOR-3 closed) | 5 |
| `default via 10.100.4.1 dev veb0 proto static` | accepted | launched | 0 |
| two default routes (both correct) | 5 | refused | 5 |
| two default routes (wrong, then correct) | 5 | refused | 5 |
| no default route (empty output) | 5 | refused | 5 |
| `default dev veb0 scope link` (no `via`) | 5 | refused | 5 |
| `default via` (`via` last token, no gateway) | say | `via_gw` stays empty ⇒ refused | 5 |
| `default via 10.100.4.11` vs proxy `10.100.4.1` | 5 | refused (no prefix confusion) | 5 |
| ECMP `default\n\tnexthop via 10.100.4.1 …` | 5 | two lines ⇒ n≠1 ⇒ refused | 5 |
| `ip` exits non-zero | 5 | refused | 5 |
| `ip` missing from `PATH` | 5, not a crash | `ip: command not found` then `--broker outside a broker namespace` | 5 |
| real host `ip` (no fake), real default route | 5 | refused — the bare-host launch dies | 5 |
| correct `via`, `HTTPS_PROXY` with a trailing slash | say | accepted (`proxy_host` is parsed before the slash) | 0 |
| `default via 10.100.4.1 dev via proto static` (interface literally named `via`) | say | accepted — the walk takes the FIRST `via`, which is the real gateway | 0 |
| leading whitespace on the route line | say | accepted (tokenised, not column-matched) | 0 |
| **5. proxy** `http://10.100.4.1:3141` | ok | launched | 0 |
| `http://10.100.4.1:3141/` | ok | launched | 0 |
| `https://10.100.4.1:3141` | 5 | `HTTPS_PROXY must be http://<host>:<port> (got 'https://…')` | 5 |
| `socks5://10.100.4.1:3141` | 5 | same shape message | 5 |
| `http://10.100.4.1` (no port) | 5 | same | 5 |
| unset / empty | 5 | `(got '')` — the one form check covers it; sb4's dead line is gone | 5 |
| lowercase `https_proxy` | honoured | launched | 0 |
| both set, `HTTPS_PROXY` right and `https_proxy` wrong | HTTPS wins | launched | 0 |
| both set, `HTTPS_PROXY` **wrong** and `https_proxy` right | HTTPS wins ⇒ refuse | `--broker outside a broker namespace` — `HTTPS_PROXY` wins | 5 |
| `http://:3141` (no host) / `http://u:p@h:3141` / `HTTP://…` / `http://h:abc` / `…:3141/p` | 5 | each `must be http://<host>:<port>` | 5 |
| `http://broker.host:3141` (hostname) / `http://*:3141` (glob) | must not bypass | form ok, then `--broker outside a broker namespace` | 5 |
| **6. bind test** see "Red before green" and MUTATION M-F | argv/exit/base-URL pinned | pinned via a fake interpreter, no `bash -x` | — |
| **7. key file** never opened under `--broker` | 0 hits, control shows 6 | holds (block above) | — |
| **8.** RT5rb's 89 + SB2's six present and green; `hook-guard.py` byte-identical | yes | tests 1-89 and 90-95 all `ok`; `git diff --exit-code` on `hook-guard.py` is empty | 0 |
| hooks.json under `--broker`, routing table path with a quote and a space | escaping holds | all three matchers: `exec '…/hook-guard' --routing-table '…/a "quoted" path/routing.toml'` | 0 |
| **9.** production shape: SB1's `nixosModules/seatLane.nix:137-153` `environment` verbatim (CA + base URL swapped for fixtures) + fake `ip`/upstream | allowed, placeholder upstream | `PROD-OK`, `Bearer injected-by-broker` (x2) | 0 |
| same, web mode with `--bind-namespace 10.100.4.2` | `--host 10.100.4.2` | `--expose-internals … --profile web --patch … --host 10.100.4.2 --no-open --port 43210` | 0 |
| same, `HTTPS_PROXY=http://10.100.9.1:3141` (not the route's `via`) | 5 | `--broker outside a broker namespace` | 5 |

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| command | exit |
|---|---|
| `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | 0 (silent) |
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 0 — 106/106 (89 RT5rb + 6 SB2 + 11 SB2b) |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0 — 312 tests |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 |
| `nix develop -c githooks/pre-commit` | 1, then 0 |

The lint gate's first run in a fresh clone regenerates the derived board block
(`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`);
the diff is one line, SB2b dropping out of the queued list and SB4 taking its
place now that this commit is in the tree. It stays "stale" until the file is
staged — `git add docs/OPERATIONS.md` then re-run gives `All checks passed!`
and exit 0. That is the one-shot the plan's Global Constraints describe;
`docs/OPERATIONS.md` is correctly not in the commit. I reverted it; the tree is
clean at `4611aa8`.

Implementer's claims, checked: "106/106 bats green" — **true**. "all seven
contract-item mutations killed by a test" — **six of seven**: items 1, 2, 4, 5,
6 and the bind-flag half of 3 are each killed (M-A, M-B, M-D, M-E, M-F, M-C);
the octet-range half of item 3 is neither implemented nor tested (MAJOR-1), and
the "exactly one default route" half of item 4 is implemented but unpinned
(M-H survives — MINOR-3). "unit, host-core, lint" — true, `unit` including
`--rebuild`.

## Red before green

Two runs, SB2b's tests kept, wrapper swapped, `git add` before each (flakes
only see tracked files), `nix develop -c bats tests/unit/70-dsh-openrouter.bats`.

**(a) main's wrapper** (`git show 421c3a0:pkgs/dsh-openrouter/dsh-openrouter.sh`,
the branch's base, which has no `--broker` at all) — all seventeen broker tests
red, nothing else regressed:

```
not ok 90 --broker skips the key block: a mode-000 key file launches headless and sends the placeholder credential
not ok 91 --broker without HTTPS_PROXY exits 5
not ok 92 --broker with a default route via another gateway exits 5
not ok 93 --bind-namespace with --broker passes --host 10.100.4.2 on the real web argv and exits 0
not ok 94 --bind-namespace without --broker is rejected like --host
not ok 95 the key-file path prints a deprecation line on stderr
not ok 96 --broker without NODE_EXTRA_CA_CERTS exits 5
not ok 97 --broker with a missing NODE_EXTRA_CA_CERTS file exits 5
not ok 98 --broker with a NODE_EXTRA_CA_CERTS that is a directory exits 5
not ok 99 --broker replaces a pre-set OPENROUTER_API_KEY with the placeholder and says so
not ok 100 --bind-namespace 0.0.0.0 is rejected
not ok 101 --bind-namespace --profile (a flag-shaped value) is rejected
not ok 102 --bind-namespace 127.0.0.1 (loopback) is rejected
not ok 103 --bind-namespace 10.100.4.2 with --broker is accepted
not ok 104 --broker reads the gateway as the token after via, never a substring
not ok 105 --broker with HTTPS_PROXY=https://... exits 5 on the http:// form
not ok 106 --broker with HTTPS_PROXY=socks5://... exits 5 on the http:// form
```

**(b) SB2's rejected wrapper** (`git show task/SB2:…` from
`/home/dalhaka/factory/ws/sb4/SB2`, read-only) — six red:

```
not ok  93 --bind-namespace with --broker passes --host 10.100.4.2 on the real web argv and exits 0
not ok  99 --broker replaces a pre-set OPENROUTER_API_KEY with the placeholder and says so
not ok 100 --bind-namespace 0.0.0.0 is rejected
not ok 101 --bind-namespace --profile (a flag-shaped value) is rejected
not ok 102 --bind-namespace 127.0.0.1 (loopback) is rejected
not ok 104 --broker reads the gateway as the token after via, never a substring
```

Worth stating plainly, because the plan's Step 1 asked for all of SB2b's tests
to be "red on SB2": tests **96, 97, 98** (the three CA cases) and **105, 106**
(the proxy-form cases) are **green** on SB2's wrapper. That is not a missing
red proof — SB2's *implementation* of both guards was already correct; sb4's
MAJOR was that nothing pinned them. Their red proof is therefore the mutation,
not the old wrapper: M-A kills 96/97/98 and M-E kills 105/106, below. Both
wrappers restored; tree clean, 106/106 green.

## Mutation table

Applied to the wrapper, `git add`ed, the tree hash asserted different from the
`4611aa8` baseline (`bf64730…`) before each run, reverted after. Full bats file
each time.

| mutation | expected | tree | result |
|---|---|---|---|
| M-A the `NODE_EXTRA_CA_CERTS` guard (both lines) deleted | ≥3 tests fail | `9f1d582` | **killed by 96, 97, 98** — sb4's MAJOR is closed |
| M-B placeholder only when unset (`${OPENROUTER_API_KEY:-injected-by-broker}`) | dies | `52656e2` | killed by 99 |
| M-C `--bind-namespace` validation block removed | dies | `244f8e5` | killed by 100, 101, 102 |
| M-D route check back to a substring test (`case " $routes " in *" via $proxy_host "*`) | dies | `19df682` | killed by 104 |
| M-E proxy form check → `[ -n "$proxy" ]` (+ scheme-agnostic host split) | dies | `e30e46d` | killed by 105, 106 |
| M-F `--host` stays `127.0.0.1` | dies | `7236f31` | killed by 93 |
| M-G the ignored-key stderr line removed | dies (or say unpinned) | `83e89b6` | killed by 99 |
| M-H exactly-one-default-route relaxed (`-eq 1` → `-ge 1`) | dies (or say unpinned) | `71c6594` | **SURVIVED — unpinned**, see MINOR-3 |
| sb4 M-A key block not skipped under `--broker` (`broker -eq 1` → `-eq 9`) | dies | `e0603f9` | killed by 90, 99 |

Killed 8 of 9. Every mutation changed the file (the script aborts otherwise)
and every tree hash differed from the baseline.

Extra probe, to size MAJOR-1: replacing the shape regex with an octet-ranged
one (`^((25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])$`)
refuses all three invalid rows and leaves **106/106 green** — no test churn, one
line:

```
  [--bind-namespace 256.1.1.1]       exit=2
  [--bind-namespace 999.999.999.999] exit=2
  [--bind-namespace 300.300.300.300] exit=2
  [--bind-namespace 8.8.8.8]         exit=0 argv-host=--host 8.8.8.8
```

## Findings

### MAJOR-1 — `--bind-namespace` validates the dotted-quad shape but not the octet range: `256.1.1.1` is accepted and reaches `--host`

`pkgs/dsh-openrouter/dsh-openrouter.sh:164-170`

```
if [ -n "$bind_namespace" ]; then
  case $bind_namespace in
    0.0.0.0 | 127.*) die 2 "--bind-namespace must be a dotted IPv4 address that is not 0.0.0.0 or loopback (got '$bind_namespace')" ;;
  esac
  [[ $bind_namespace =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] ||
    die 2 "--bind-namespace needs a dotted IPv4 address (got '$bind_namespace')"
fi
```

`[0-9]{1,3}` accepts `256`–`999`. Evidence — the real exec argv, recorded by
the fake interpreter the round itself introduced:

```
  [--bind-namespace 256.1.1.1]       exit=0 argv-host=--host 256.1.1.1
  [--bind-namespace 999.999.999.999] exit=0 argv-host=--host 999.999.999.999
  [--bind-namespace 300.300.300.300] exit=0 argv-host=--host 300.300.300.300
```

The gate's required matrix pre-committed `256.1.1.1 → 2`; observed `0`. Plan
contract item (3) says the flag "accepts only a dotted IPv4 address that is not
`0.0.0.0`, not loopback and not a flag-shaped string; anything else → `die 2`",
and the wrapper's own message says "must be a dotted IPv4 address" while
accepting a string that is not one. No test covers the octet range, so M-C
(validation removed) is still killed by 100/101/102 and this gap is invisible
to the suite.

What it is **not**: a security hole. The contract already permits any
non-loopback IPv4 (`8.8.8.8` is accepted by design, since SB1's `seat-run`
supplies the address), so an out-of-range string can do nothing an in-range one
could not; there is no argv injection (the value stays exactly one argv
element, and the flag-shaped and space-carrying cases now die 2); and Node
fails closed on `--host 256.1.1.1` — a `dns.lookup` that cannot resolve inside
the seat namespace. What it costs is exactly what sb4's MAJOR cost: the
fail-fast the plan asked for. A mistyped address becomes an opaque Node error
in a namespace instead of one line on stderr.

Fix: the regex above (one line) plus one bats test asserting
`--bind-namespace 256.1.1.1` exits 2 — I ran the regex against the full file
and it is 106/106 green.

### MINOR-1 — the banner says `key from placeholder (broker injects)`, not the plan's `credential: placeholder (broker injects)`

`pkgs/dsh-openrouter/dsh-openrouter.sh:272` and `:692,:698`. Contract item (2)
names the literal string `credential: placeholder (broker injects)`; the
wrapper reuses the existing `key from %s` banner, so the line reads
`… workspace-write, key from placeholder (broker injects), workspace …`. It is
truthful — which is the substance of the requirement, and test 99 pins
`placeholder (broker injects)` — but it is not the string the plan wrote, and
"key from placeholder" is a slightly odd way to say the seat holds no key.

### MINOR-2 — the ignored-key line fires on *every* production launch, so it can never signal a real leak

`pkgs/dsh-openrouter/dsh-openrouter.sh:267-269`. SB1's unit sets
`OPENROUTER_API_KEY = "injected-by-broker"`
(`nixosModules/seatLane.nix:145`), so `[ -n "${OPENROUTER_API_KEY:-}" ]` is
always true in the seat and every job's journal gets:

```
dsh-openrouter: a pre-set OPENROUTER_API_KEY is ignored under --broker (the broker injects the real key)
```

I saw it in the row-9 production-shape run. The message is misleading (nothing
was ignored — the value already *was* the placeholder) and it burns the one
signal that would have told the operator a real key had been carried into the
namespace. Guard it: only warn when
`[ "${OPENROUTER_API_KEY:-}" != injected-by-broker ]`, and pin that with a test
so the placeholder case is silent.

### MINOR-3 — the "exactly one default route" half of contract item (4) is implemented but unpinned; M-H survives

`pkgs/dsh-openrouter/dsh-openrouter.sh:355`:
`[ "$n" -eq 1 ] || die 5 "--broker outside a broker namespace"`. Relaxing it to
`-ge 1` leaves **106/106 green** and does change behaviour — the loop keeps the
last line's `via`, so a second default route alongside the right one is then
accepted:

```
### HEAD                              ### under M-H (-eq 1 -> -ge 1)
 two routes, both correct    exit=5     exit=0
 two routes, wrong→correct   exit=5     exit=0
 two routes, correct→wrong   exit=5     exit=5
```

No bats test feeds the wrapper two default routes (test 92 feeds one wrong
one). This is the same shape as the defect that rejected SB2 — a contract half
that is correct today and pinned by nothing tomorrow — and the plan does state
"requires exactly one default route" in item (4). I am recording it as a minor
only because the gate's own mutation row for M-H allows "or say unpinned"; if
the orchestrator applies the sb4 rule literally it belongs in the same fix
round as MAJOR-1, and it is one test (`make_ip_line` with two lines).

### MINOR-4 — `--bind-namespace ''` skips both the `--broker` requirement and the validation

`pkgs/dsh-openrouter/dsh-openrouter.sh:156` and `:164` both gate on
`[ -n "$bind_namespace" ]`, so an explicitly empty value passes without
`--broker` and without validation. It degrades safe —
`--host "${bind_namespace:-127.0.0.1}"` falls back to loopback — but
`--bind-namespace ''` exiting 0 while `--bind-namespace 127.0.0.1` exits 2 is
an inconsistency worth one `case` arm.

### MINOR-5 — `DSH_OPENROUTER_NODE` is a new production seam with no guard

`pkgs/dsh-openrouter/dsh-openrouter.sh:686`:
`node_bin=${DSH_OPENROUTER_NODE:-node}`, used by all three `exec` lines. This
is the right answer to sb4's MINOR-5 (a `PATH`-level fake `node` is shadowed by
`runtimeInputs`, and `DSH_OPENROUTER_BIN_JS` is re-exported by `runtimeEnv`), and
it buys a real argv/exit-status assertion. But it also lets any caller replace
the interpreter the wrapper execs, where before it was pinned to the runtime
`PATH`. No escalation follows — a caller who can set the variable can already
run the binary directly, `pkgs/dsh-openrouter/default.nix` is untouched so
nothing sets it, and SB1's unit `environment` does not carry it — so this is a
note, not a defect. Worth one sentence in the wrapper's header comment (or in
SB5's runbook) so a later reader knows it is a test seam, not an option.

### MINOR-6 — `--broker` still proves the proxy variables are *set*, never that traffic uses them

Unchanged from sb4 and by design (the plan gives the traversal proof to SB4).
In every row above, `HTTPS_PROXY=http://10.100.4.1:3141` pointed at nothing
that exists and the request still reached the fake upstream directly. SB1 has
since added `NODE_USE_ENV_PROXY = "1"` (`nixosModules/seatLane.nix:150`), which
is the mechanism — SB4's VM must show the audit line.

## Verdict

**REJECTED** — one MAJOR, and a narrow one. sb4's reject reason is genuinely
fixed: M-A now kills three tests where it left 95/95 green. The credential path
is stronger than the contract required and I could not break it — under
`--broker` the key file is never opened or `stat`'ed (strace, with a sensitive
control), `OPENROUTER_KEY_FILE` is never consulted, a pre-set `sk-or-` value is
replaced before anything reads it and appears nowhere in the fixture `HOME`,
and the placeholder is what reaches upstream. `--broker` refuses outside a
broker namespace under every route shape I could produce, including the
synthetic two-`via` line sb4 got an allow out of, a missing `ip`, and the real
host route. `hook-guard.py` is byte-identical, RT5rb's 89 and SB2's six are
untouched and green, the hooks.json escaping holds under `--broker`, the
non-broker paths are unchanged, one commit, subject byte-identical, both
trailers, every touched file inside `touches`, all five checks green.

The reject is one line of regex: contract item (3) promises "only a dotted IPv4
address" and `--bind-namespace 256.1.1.1` is accepted onto the real exec argv,
against a required matrix row that pre-committed exit 2. It has no security
consequence — the contract already allows any non-loopback IPv4 and Node fails
closed on the invalid string — but it is a contract item not met and a required
row failing, which is a reject under the gate rule and consistent with how SB2
was judged. Land it as SB2c: the octet-ranged regex, one bats test for
`256.1.1.1`, and while the file is open fold MINOR-3 (two default routes, one
test) and MINOR-2 (silence the ignored-key line when the value is already the
placeholder — it fires on every production launch today). MINOR-1, 4, 5 and 6
are take-or-leave.
