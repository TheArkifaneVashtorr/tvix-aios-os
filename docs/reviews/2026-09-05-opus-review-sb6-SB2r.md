# Opus gate — seat run sb6, task SB2r — APPROVED

## Summary

Branch `task/SB2r` in `/home/dalhaka/factory/ws/sb6/SB2r`, base `05d7609`
(main), head `f209293`, **one** commit, three files
(`pkgs/dsh-openrouter/dsh-openrouter.sh` +145/-8,
`tests/unit/70-dsh-openrouter.bats` +367/-0, `docs/runbooks/lanes.md` +8/-0).
Reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-sb6-SB2r`.
Nothing under `/home/dalhaka/factory` was written; `/home/dalhaka/factory/ws/sb5/SB2b`
was read with `git show` only. Every wrapper run used a fixture `HOME`, a fake
key file, the bats file's own fake upstream (`tests/mocks/openai-fake.py`), a
fake `ip` and (for the argv rows) a fake interpreter behind
`DSH_OPENROUTER_TEST_SEAM=1`. The operator's real key file was never read and
the real OpenRouter was never contacted.

sb5's MAJOR is closed and closed properly: `--bind-namespace 256.1.1.1` now
exits **2** (it reached the real `--host` argv at SB2b), and dropping the octet
range back to `[0-9]{1,3}` now fails four tests where it left 106/106 green
last round. All six contract items land, all six of sb5's minors are addressed
(five closed, one — the traversal proof — is SB4's by plan), and the credential
half is unchanged and still unbreakable by me: under `--broker` the key file is
never opened, `stat`'ed or `lstat`'ed (strace, with a control run that catches
six syscalls on the same path without `--broker`), `OPENROUTER_KEY_FILE` is
never consulted, a pre-set `sk-or-` value is replaced before anything reads it
and appears nowhere in the fixture `HOME`, and `Bearer injected-by-broker` is
what reaches upstream.

115/115 bats, shellcheck silent, `unit` (321 tests, incl. `--rebuild`),
`host-core` and `lint` all exit 0, `hook-guard.py` byte-identical to base, one
commit, subject byte-identical to the plan's, both trailers, every touched file
inside `touches`. Every required matrix row matched its pre-committed
expectation. Eighteen behaviour-changing mutations, every one killed —
including all of sb5's M-A…M-H (M-H, sb5's survivor, now dies by test 112) and
rt8's M-A on the untouched guard.

No MAJORs. Four minors and two notes below; none of them is a reject.

## Credential path

`pkgs/dsh-openrouter/dsh-openrouter.sh:275-284` — the whole key block
(`:285-311`) sits behind an `if/elif/else`, so under `--broker` there is no
path into `stat`, `head -n 1` or the mode check, and the placeholder is
assigned unconditionally:

```
if [ "$broker" -eq 1 ]; then
  if [ -n "${OPENROUTER_API_KEY:-}" ] && [ "$OPENROUTER_API_KEY" != injected-by-broker ]; then
    printf 'dsh-openrouter: a pre-set OPENROUTER_API_KEY is ignored under --broker (the broker injects the real key)\n' >&2
  fi
  OPENROUTER_API_KEY=injected-by-broker
  export OPENROUTER_API_KEY
  key_source="credential: placeholder (broker injects)"
```

Method for "never read": `strace -f -e trace=openat,open,stat,lstat,newfstatat,statx`
over the wrapper, then `grep 'openrouter/key'` over the trace.

```
### 6a: --broker, mode-000 key file, strace
exit=0  stdout=BROKER-OK
traced syscall lines: 20808
key-path hits: 0
  upstream auth: {'Bearer injected-by-broker'}
```

Control (the instrument is sensitive), same filter, `--broker` removed:

```
### 6b: CONTROL, no --broker, same filter
exit=0  stdout=BROKER-OK
key-path hits: 6
  | newfstatat(AT_FDCWD, ".../.config/openrouter/key", {st_mode=S_IFREG|0600, st_size=18, ...}, 0) = 0
  | newfstatat(AT_FDCWD, ".../.config/openrouter/key", {...}, AT_SYMLINK_NOFOLLOW) = 0
  | statx(AT_FDCWD, ".../.config/openrouter/key", ...) = 0
  upstream auth: {'Bearer sk-or-REAL-SECRET'}
```

`OPENROUTER_KEY_FILE` pointed at a second secret under `--broker`: **0**
strace hits on `alt.key`, 0 on the default path, `sk-or-ALT-SECRET` absent from
the upstream capture. Key file **absent** under `--broker`: exit 0,
`BROKER-OK`. A pre-set `OPENROUTER_API_KEY=sk-or-fixture` under `--broker`:
upstream got `Bearer injected-by-broker`, and `grep -rl sk-or-fixture` over the
whole fixture `HOME` returned nothing.

Non-broker paths are untouched: the env-key path still sends
`Bearer sk-or-envkey` with the banner `key from OPENROUTER_API_KEY
(environment)`; the key-file path still prints exactly the one deprecation line
on stderr.

## Rule behaviour

Fixtures: bats-shaped fixture `HOME`; `make_key`; fake `ip` on `PATH`;
`make_ca`; a recording fake interpreter via `DSH_OPENROUTER_NODE` +
`DSH_OPENROUTER_TEST_SEAM=1`; `dsh-openrouter --broker --dump-config` unless
noted. Every row's expectation was pre-committed by the gate brief.

| row | expected | observed | exit |
|---|---|---|---|
| **1. bind** `256.1.1.1` | 2 | `--bind-namespace needs a dotted IPv4 address (got '256.1.1.1')`, argv empty | **2** |
| `999.999.999.999` | 2 | same message | 2 |
| `300.300.300.300` | 2 | same message | 2 |
| `01.2.3.4` (leading zero) | 2 | same message | 2 |
| `''` (empty) | 2 | `… (got '')` | 2 |
| `0.0.0.0` | 2 | `must be a dotted IPv4 address that is not 0.0.0.0 or loopback (got '0.0.0.0')` | 2 |
| `127.0.0.1` | 2 | same message | 2 |
| `127.255.255.255` | 2 | same message (whole `127.*` block) | 2 |
| `--profile` (flag-shaped) | 2 | `needs a dotted IPv4 address (got '--profile')` | 2 |
| **`10.100.4.2`** | accepted, on the real argv | `--host 10.100.4.2` recorded by the fake interpreter | **0** |
| `255.255.255.255` | say | accepted, `--host 255.255.255.255` | 0 |
| `1.2.3` (three octets) | 2 | `needs a dotted IPv4 address` | 2 |
| `1.2.3.4.5` | 2 | same | 2 |
| `' 10.100.4.2'` (leading space) | say | refused (`^…$` anchors) | 2 |
| `'10.100.4.2 '` (trailing space) | say | refused | 2 |
| `::1` / `fe80::1` (IPv6) | 2 | `needs a dotted IPv4 address (got '::1')` | 2 |
| `'10.0.0.1 --danger-full-access'` | 2 | refused (no argv injection) | 2 |
| `8.8.8.8` | contract allows any non-loopback IPv4 | accepted, `--host 8.8.8.8` | 0 |
| `0.1.2.3` (0.0.0.0/8) | say | accepted — MINOR-2 | 0 |
| `$'1.2.3.4\n5.6.7.8'` (embedded newline) | say | refused (bash `$` is end-of-string) | 2 |
| no flag at all | `--host 127.0.0.1` | `--host 127.0.0.1` on the argv | 0 |
| `--bind-namespace` without `--broker` | 2 | `the browser UI binds 127.0.0.1 only; --bind-namespace needs --broker` | 2 |
| **2. routes** one default via the proxy host | allowed | launched | 0 |
| **two defaults, one via the proxy host** | **5** | `--broker outside a broker namespace` | **5** |
| two defaults, proxy host first | 5 | same | 5 |
| two defaults **both** via the proxy host (duplicate) | say | refused (`n -eq 1`) | 5 |
| none (empty output) | 5 | refused | 5 |
| `default dev veth0 scope link` (`via` absent) | 5 | refused | 5 |
| `default via` (`via` last token, no gateway) | say | `via_gw` stays empty ⇒ refused | 5 |
| `default via 10.100.4.11` vs proxy `10.100.4.1` | 5 | refused (no prefix confusion) | 5 |
| synthetic `default via 192.168.1.1 dev via 10.100.4.1 x` | 5 | refused (walk takes the FIRST `via`) | 5 |
| ECMP `default` + `nexthop via 10.100.4.1 …` | 5 | two lines ⇒ n≠1 ⇒ refused | 5 |
| leading whitespace on the route line | say | accepted (tokenised) | 0 |
| `ip` exits non-zero | 5 | refused | 5 |
| `ip` missing from `PATH` | 5, not a crash | refused | 5 |
| real host `ip`, real default route, proxy `10.100.4.1` | 5 | refused | 5 |
| **3. ignored key** `OPENROUTER_API_KEY=sk-or-fixture` | line printed **once**, placeholder upstream | line count 1; `Bearer injected-by-broker`; secret absent from `HOME` | 0 |
| **`OPENROUTER_API_KEY=injected-by-broker`** (SB1's production shape) | **no line** | line count **0** | **0** |
| `OPENROUTER_API_KEY` unset | no line | line count 0 | 0 |
| `OPENROUTER_API_KEY=''` | say | line count 0; placeholder upstream | 0 |
| **4. banner** under `--broker` | exactly `credential: placeholder (broker injects)` | `… workspace-write, credential: placeholder (broker injects), workspace …` (count 1) | 0 |
| the old `key from …` wording for that path | gone | `grep -c 'key from'` on that run: **0** | — |
| non-broker env-key banner | unchanged | `key from OPENROUTER_API_KEY (environment)` | 0 |
| non-broker key-file banner | unchanged | `key from <path>` + the deprecation line | 0 |
| **5. seam** `DSH_OPENROUTER_NODE` set, no flag | fake NOT used, one stderr line | fake-used=no, real dump printed, seam-line count 1 | 0 |
| `DSH_OPENROUTER_NODE` + `DSH_OPENROUTER_TEST_SEAM=1` | fake used | fake-used=YES | 0 |
| `…_TEST_SEAM=0` / `=yes` (not `1`) | ignored | fake-used=no, seam-line 1 | 0 |
| neither set | packaged interpreter | fake-used=no, seam-line 0, real dump | 0 |
| `TEST_SEAM=1`, `NODE` unset | packaged interpreter | fake-used=no, seam-line 0 | 0 |
| SB1's unit sets either variable? | no | `nixosModules/seatLane.nix:137-153` sets **neither** (grep over the whole tree: the only mentions are the wrapper and the bats file) | — |
| **6. credential** key file never opened/stat'ed under `--broker` | 0 hits, control shows 6 | holds (block above) | — |
| **7. CA** unset / empty / missing file / a directory | 5 | `needs NODE_EXTRA_CA_CERTS…` / `… is not an existing file` | 5 |
| CA a readable file | proceeds | launched | 0 |
| **7. proxy** `http://10.100.4.1:3141` and `…/` | ok | launched | 0 |
| `https://` / `socks5://` / no port / `http://:3141` / `http://u:p@h:3141` / `HTTP://` / `:abc` / `…/p` | 5 | each `must be http://<host>:<port>` | 5 |
| unset / empty | 5 | `(got '')` | 5 |
| lowercase `https_proxy` only | honoured | launched | 0 |
| `HTTPS_PROXY` right, `https_proxy` wrong | HTTPS wins | launched | 0 |
| `HTTPS_PROXY` wrong, `https_proxy` right | HTTPS wins ⇒ refuse | `--broker outside a broker namespace` | 5 |
| `http://broker.host:3141` (hostname) | must not bypass | form ok, then namespace refusal | 5 |
| **7. deprecation** key-file path | one stderr line, stdout clean | `the key file is deprecated; seat jobs run behind the broker (docs/runbooks/seat.md)` | 0 |
| **7. guards** RT5rb's 89 + SB2/SB2b's 17 + SB2r's 9 | all green | 115/115 | 0 |
| `hook-guard.py` vs base | byte-identical | `git diff 05d7609..HEAD -- …/hook-guard.py` empty | — |
| **9. production shape** SB1's `seatLane.nix:137-153` environment (CA/base swapped for fixtures) | allowed, placeholder upstream, **silent** | `PROD-OK`, `Bearer injected-by-broker`, ignored-key line **0**, seam line **0**, banner present | 0 |
| same, web mode `--bind-namespace 10.100.4.2` | `--host 10.100.4.2` | `--expose-internals … --profile web --patch … --host 10.100.4.2 --no-open --port 43210` | 0 |
| same, `HTTPS_PROXY=http://10.100.9.1:3141` (not the route's via) | 5 | `--broker outside a broker namespace` | 5 |
| **8. runbook** names the bind rule and the seam flag | yes | `docs/runbooks/lanes.md:400-406` (quoted under Findings) | — |

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| command | exit |
|---|---|
| `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | 0 (silent) |
| `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 0 — **115/115** (89 RT5rb + 17 SB2/SB2b + 9 SB2r) |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0 — **321 ok, 0 not ok** |
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 |
| `nix develop -c githooks/pre-commit` | 1, then 0 |

The lint gate's first run in a fresh clone regenerates the derived board block:
`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. The
diff is one line — `SB2r` dropping out of the queued list and `SB4` taking its
place now that this commit is in the tree. `git add docs/OPERATIONS.md` then
re-run gives `All checks passed!` and exit 0. That is the one-shot the plan's
Global Constraints describe; `docs/OPERATIONS.md` is correctly **not** in the
commit. Reverted; the tree is clean at `f209293`.

Implementer's claims, checked. "All six contract items implemented" — **true**
(1 bind octet range + empty, 2 exactly-one-default-route pinned, 3 ignored-key
line conditional, 4 contracted banner string, 5 seam behind the flag, 6 runbook
line). "Six+ tests shown red-first" — **eight of the nine new tests are red on
SB2b's wrapper** (below); the ninth (112) is red under the mutation the plan
names for it. "unit, host-core, lint" — true, `unit` including `--rebuild`.

Commit convention: one commit; subject `diff`ed byte-for-byte against the
plan's line 151 — identical; `Generated-By:` and `Co-Authored-By: Claude Fable
5.1 <noreply@anthropic.com>` both present; the three changed files are exactly
the plan's `touches`.

## Red before green

SB2r's tests kept, the wrapper swapped for SB2b's
(`git -C /home/dalhaka/factory/ws/sb5/SB2b show task/SB2b:pkgs/dsh-openrouter/dsh-openrouter.sh`,
read-only), `git add` before the run (flakes only see tracked files), tree hash
asserted different from the `f209293` baseline (`e47cc3b` → `328538f`).

```
ok    100 --bind-namespace 0.0.0.0 is rejected
ok    101 --bind-namespace --profile (a flag-shaped value) is rejected
ok    102 --bind-namespace 127.0.0.1 (loopback) is rejected
ok    103 --bind-namespace 10.100.4.2 with --broker is accepted
ok    104 --broker reads the gateway as the token after via, never a substring
ok    105 --broker with HTTPS_PROXY=https://... exits 5 on the http:// form
ok    106 --broker with HTTPS_PROXY=socks5://... exits 5 on the http:// form
not ok 107 --bind-namespace 256.1.1.1 (an out-of-range octet) is rejected
not ok 108 --bind-namespace 999.999.999.999 (all octets out of range) is rejected
not ok 109 --bind-namespace 300.300.300.300 (all octets out of range) is rejected
not ok 110 --bind-namespace 01.2.3.4 (a leading zero) is rejected
not ok 111 --bind-namespace '' (an empty value) is rejected
ok    112 --broker with two default routes (one via the proxy host) exits 5
not ok 113 --broker with a pre-set placeholder OPENROUTER_API_KEY stays silent (no ignored-key line)
not ok 114 --broker launch banner prints 'credential: placeholder (broker injects)'
not ok 115 DSH_OPENROUTER_NODE without DSH_OPENROUTER_TEST_SEAM is ignored: the real interpreter runs
```

Eight red, one green — and the green one is the honest case, stated plainly
because the plan's Step 1 asked for the two-default-routes test to be red on
SB2b too. Test **112 is green on SB2b's wrapper because SB2b's `[ "$n" -eq 1 ]`
was already correct**; sb5's finding was that nothing *pinned* it (M-H
survived). Its red proof is therefore the mutation, not the old wrapper — and
M-B/M-H now kill it (below). Same shape as the 96/97/98 note in sb5's review.

Wrapper restored from `HEAD`; tree hash back to `e47cc3b`; 115/115 green;
`git status --porcelain` empty.

## Mutation table

Method per row: `git checkout HEAD -- .` → apply → `git add -A` → **tree hash
asserted different from the `f209293` baseline `e47cc3b`** → a fresh
`nix develop -c bats tests/unit/70-dsh-openrouter.bats` (so the flake rebuilds
`dsh-openrouter` from the dirty tracked tree) → revert → `git status` asserted
empty at the end.

**Method honesty.** Two rows first read as 0-red. Neither was a survivor: the
package build itself failed on the wrapper's own shellcheck (`SC2034`, an
unused variable the mutation orphaned), so bats never ran a single test. I
re-ran both in build-valid forms and both die. A 0-red row is reported as VOID,
never as SURVIVED, and both VOID rows are listed.

**SB2r's five (seven rows — the bind item run three ways):**

| row | mutation | tree | result |
|---|---|---|---|
| M-A | octet range dropped, back to `^[0-9]{1,3}(\.[0-9]{1,3}){3}$` | `02bb773` | **KILLED — 107, 108, 109, 110** (sb5's MAJOR is closed) |
| M-A2 | the explicit `[ -z ]` guard at `:169-171` deleted | `28e43b4` | SURVIVED, **equivalent mutant** — see NOTE-1 |
| M-A2'' | the empty value truly accepted (`bind_seen -eq 1` → `… && [ -n "$bind_namespace" ]`, SB2b's defect) | `b05fbe5` | **KILLED — 111** |
| M-A3 | leading-zero octets accepted (`[01]?[0-9]?[0-9]` alternative) | `e1ec958` | **KILLED — 110** |
| M-B | route count `-eq 1` → `-ge 1` | `af371d3` | **KILLED — 112** |
| M-C | ignored-key line printed unconditionally | `07227c4` | **KILLED — 113** |
| M-D | banner string changed (`(broker injects)` → `(the broker injects)`) | `3ca5239` | **KILLED — 99, 114** |
| M-E | the `DSH_OPENROUTER_TEST_SEAM` check removed (seam honoured unconditionally) | `f7322f4` | **KILLED — 115** |
| M-E2 | the seam's "ignored" stderr line removed (extra row) | `094f29b` | **KILLED — 115** |

**sb5's M-A…M-H re-applied on this tree, plus sb4's and rt8's:**

| row | mutation | tree | result |
|---|---|---|---|
| sb5 M-A | the `NODE_EXTRA_CA_CERTS` guard (both lines) deleted | `fbe7f0f` | KILLED — 96, 97, 98 |
| sb5 M-B | placeholder only when unset (`${OPENROUTER_API_KEY:-injected-by-broker}`) | `cf655af` | KILLED — 99 |
| sb5 M-C | the whole `--bind-namespace` validation removed | `4b1a57f` | KILLED — 100, 101, 102, 107, 108, 109, 110 |
| sb5 M-D | route check back to a substring, walk deleted | `cbe002d` | **VOID** — build refused (`SC2034: via_gw appears unused`), bats never ran |
| sb5 M-D' | gateway match back to a substring (walk kept, so the mutant builds) | `243110a` | **KILLED — 104** |
| sb5 M-E | proxy form check → `[ -n "$proxy" ]` (+ scheme-agnostic host split) | `6e04e55` | KILLED — 105, 106 |
| sb5 M-F | `--host` stays `127.0.0.1` | `fd407f2` | KILLED — 93 |
| sb5 M-G | the ignored-key stderr line removed | `d1944b8` | KILLED — 99 |
| **sb5 M-H** | **`-eq 1` → `-ge 1`** (sb5's one survivor) | `af371d3` | **KILLED — 112** |
| sb4 M-A | key block not skipped under `--broker` (`broker -eq 1` → `-eq 9`) | `b9220ec` | KILLED — 90, 99, 114 |
| rt8 M-A | `json.load` moved back outside the guard in the untouched `hook-guard.py` | `919ed8e` | KILLED — 76, 77 |
| (M-A2' ) | `bind_seen -eq 1` → `[ -n "$bind_namespace" ]` | `dc8237d` | **VOID** — build refused (`SC2034: bind_seen`); superseded by M-A2'' above |

**18 of 18 behaviour-changing rows killed.** Two rows void (the package's own
shellcheck refused the mutant before any test ran; both re-run in build-valid
form and die), one equivalent mutant (NOTE-1). Every row's tree hash differed
from the baseline, and the final `git status --porcelain` was empty.

## Findings

No MAJORs.

### MINOR-1 — `--broker` still launches on the bare host when `HTTPS_PROXY` names the host's own default gateway

`pkgs/dsh-openrouter/dsh-openrouter.sh:315-352`. The namespace assertion
compares the default route's gateway against a host the **caller** supplies via
`HTTPS_PROXY`, so it is self-referential. With the real `ip` on this host:

```
### bare host: real ip, no fake, --broker, HTTPS_PROXY=http://10.100.4.1:3141
real host default routes:
  | default via 192.0.2.x dev eno1 proto dhcp src 192.0.2.x97 metric 100
exit=5  msg=dsh-openrouter: --broker outside a broker namespace

### bare host, HTTPS_PROXY pointed at the host's OWN default gateway
host gateway=192.0.2.x  default routes=1
exit=0
```

The gate brief's required row ("real host `ip`, real default route → 5") passes;
this is the extra row. I am **not** calling it a MAJOR, for three reasons.
(a) It is exactly what the plan contracted at SB2b — "exactly one default route
whose `via` is the proxy host" — and SB2r was scoped to the *count* half of
that rule, which it now pins; the check is unchanged from the wrapper sb5
examined and passed on this point. (b) There is no credential consequence: the
same code path exports `OPENROUTER_API_KEY=injected-by-broker`, so a bare-host
`--broker` launch holds a placeholder with no value and its requests fail
upstream auth — it fails open on the namespace claim and closed on the secret.
(c) The real answer is SB4's VM traversal proof (sb5's MINOR-6, still open by
plan): a check that the request actually leaves through the broker, not that
two environment variables agree with a route. Worth one line in SB4's evidence
so the property is asserted somewhere, and worth knowing that `--broker` is a
*declaration* by the unit, not an independent proof of confinement.

### MINOR-2 — `0.0.0.0/8` other than `0.0.0.0` itself is accepted

`pkgs/dsh-openrouter/dsh-openrouter.sh:171-175`. The `case` arm excludes the
literal `0.0.0.0` and all of `127.*`, but `0.1.2.3` (RFC 1122 "this network",
not a bindable unicast address) passes the octet regex:

```
0.1.2.3    exit=0 argv=[--host 0.1.2.3]
```

The contract says "not `0.0.0.0`", literally, so this is inside the letter of
item 1 — and the production caller supplies `cfg.namespaceAddress`, never a
hand-typed value. One more `case` arm (`0.*`) would close it if the orchestrator
wants the rule to read "a real unicast IPv4".

### MINOR-3 — the runbook line calls it "the lane's unit"; it is the seat's

`docs/runbooks/lanes.md:400-406`:

```
**Seat jobs behind the broker** (`--broker`, what the lane's unit starts)
hold no key of their own and bind the UI to the namespace rather than
127.0.0.1: `--bind-namespace ADDR` (with `--broker` only) takes a real
dotted IPv4 — four octets each 0-255, no leading zeros, not `0.0.0.0`, not
`127.0.0.0/8`, not empty — and anything else exits 2. `DSH_OPENROUTER_NODE`
is a test-only interpreter seam, honoured only when
`DSH_OPENROUTER_TEST_SEAM=1` is also set; the seat unit sets neither.
```

Contract item 6 is met in full — both the bind rule and the seam flag are
named, accurately. The nit is "what the lane's unit starts": `--broker` is
started by `seat@<job>` via `pkgs/seat/seat-run.py:86,97`, not by a lane unit.
The paragraph's own last clause says "the seat unit", so the file contradicts
itself by four words. One-word fix, whenever the file is next open.

### MINOR-4 — `DSH_OPENROUTER_TEST_SEAM` is a second unauthenticated env var, not an authentication

`pkgs/dsh-openrouter/dsh-openrouter.sh:702-708`. Contract item 5 is met and
pinned (M-E dies; test 115 proves the fake is not used and the real dump is
produced), and it does what the plan wanted: a stray `DSH_OPENROUTER_NODE` in
someone's environment can no longer swap the interpreter, and SB1's unit sets
neither variable (verified against `nixosModules/seatLane.nix:137-153`, and a
tree-wide grep finds the name only in the wrapper and the bats file). What it
is not is a privilege boundary — anyone who can set one variable can set two.
That is fine, because such a caller can already exec any binary directly; it is
worth being explicit that the flag buys tidiness against accident, not defence
against intent. No action needed.

### NOTE-1 — the explicit empty-value guard is redundant (an equivalent mutant)

`pkgs/dsh-openrouter/dsh-openrouter.sh:169-171`:

```
  if [ -z "$bind_namespace" ]; then
    die 2 "--bind-namespace needs a dotted IPv4 address (got '')"
  fi
```

Deleting these three lines leaves **115/115 green** and changes no observable
behaviour: the octet regex at `:174` already refuses the empty string, and the
two `die 2` messages are byte-identical when `$bind_namespace` is empty. The
load-bearing half of the empty-value fix is the `bind_seen` gate at `:167`
(replacing SB2b's `[ -n "$bind_namespace" ]`), and *that* is pinned — M-A2''
dies by test 111. So contract item 1's "not empty" is genuinely covered; the
explicit guard is documentation, not a second gate. Recorded so a future
mutation round is not surprised by a 0-red row here.

### NOTE-2 — `NODE_EXTRA_CA_CERTS` as a symlink to a readable file is accepted

Unchanged from SB2b (`-f` follows symlinks); consistent with the contract,
which asks for "an existing file".

## Verdict

**APPROVED.** sb5's reject reason is fixed and the fix is real, not cosmetic:
`--bind-namespace 256.1.1.1` reached the real `--host` argv at SB2b and now
exits 2, and the mutation that reverts it fails four tests where the same
mutation was invisible last round. All six contract items land and each is
pinned by a mutation that dies — the octet range (M-A), the empty value
(M-A2''), leading zeros (M-A3), the one-default-route count (M-B, which is
sb5's surviving M-H), the conditional ignored-key line (M-C), the contracted
banner string (M-D), the seam flag (M-E). sb5's other seven mutations, sb4's
and rt8's all still die; nothing regressed; `hook-guard.py` is byte-identical.

The credential path is what it has to be and I could not break it: under
`--broker` the key file is never opened or `stat`'ed (strace, with a control
that catches six syscalls on the same path), `OPENROUTER_KEY_FILE` is never
consulted, a pre-set `sk-or-` value is replaced before anything reads it and
appears nowhere in the fixture `HOME`, and only the placeholder reaches
upstream. The production shape now launches **silently** — SB1's unit sets the
placeholder, so the ignored-key line is reserved for the real leak it is meant
to signal, and the seam line never fires because the unit sets neither
variable. All five claimed checks pass (115/115 bats, 321 unit tests including
`--rebuild`, `host-core`, `lint`, shellcheck silent), the pre-commit hook is the
expected one-shot, and the commit convention holds byte-for-byte.

Four minors, none of them blocking. MINOR-1 is the one to carry forward: the
namespace assertion is a declaration checked against caller-supplied inputs, so
SB4's VM must be the place where "the request actually traversed the broker"
becomes evidence — it is on the plan already as sb5's MINOR-6. MINOR-2 (one
more `case` arm for `0.*`), MINOR-3 (four words in
`docs/runbooks/lanes.md:400`) and MINOR-4/NOTE-1/NOTE-2 (notes, no action) can
ride along with any later touch of these files. Nothing here needs a re-plan.
