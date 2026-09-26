---
plan_defect: none
mutants_total: 4
mutants_killed: 3
mutants_outside_named: 1
model: opus
---
# Opus gate — seat run hh1g, task HH1c — APPROVED

## Summary

The MAJOR is closed, and I measured it rather than reasoned about it. Run under
the shipped package's own interpreter and typelibs
(`/nix/store/3vhwqypslvfwgvdn93rch52g362aq16n-helm-home-0.1`), with the payloads
transcribed from `pkgs/helm-home/portal.py` (`:126-130` and `:114-123`) rather
than borrowed from the probe's own self-test, and with the HH1b line kept as a
live control in the same process:

```
HH1c boxed CreateSession OK: (a{sv})
HH1b unboxed CreateSession -> TypeError: argument value: Expected GLib.Variant, but got str
HH1c boxed BindShortcuts OK: (oa(sa{sv})sa{sv})
HH1b unboxed BindShortcuts -> TypeError: argument value: Expected GLib.Variant, but got str
```

Lines 2 and 4 are HH1b's MAJOR-1, reproduced verbatim — the instrument is the
same one that rejected the last round, and it still fires. Lines 1 and 3 are
what this round ships: both portal calls build, with the type strings the
section names. **MAJOR-1 is closed.**

The rest of the round is clean. One commit, subject byte-identical to the
section (`md5sum` equal on each), both trailers in policy order with the model
from `HH1c.result`, nine files all inside the chain's `touches` union, no
undeclared touch. All three acceptance checks green in a fresh clone with
`--rebuild`. The section's three named kill-mutants all die with the exact
messages the commit body pastes; the fourth survives, by design, exactly as the
section predicts.

Two things worth more than their size. First, HH1b's other two minors are
genuinely closed, not waved at: `test_dbus_signature_for_unknown_raises` pins
the `KeyError` arm (mutant c kills it), and `pkgs.git` is gone from
`helm-home-unit`'s inputs. Second — this is the structural gain — the seam HH1b
could not close is now closed. HH1b's mutant (c), reverting `PortalBus.call` to
the unboxed line, *survived* every check because no test could reach
`probe.py`. I re-ran that same mutant here (mutant e, outside the named set):
`helm-home-package` now **kills** it, while `helm-home-unit` still cannot see it
(`18 passed`). The call site the last two rounds broke is under CI for the first
time.

Three minors, none gating and none owed on this commit: MINOR-3 from HH1b is
still open and its prescribed route is the reason (below); the commit body
claims a `githooks/pre-commit` exit 0 that does not reproduce at HEAD; and the
package output became non-deterministic under `--rebuild` this round.

**APPROVED.**

## Diff against the section

Fresh clone of `task/HH1c` at `466b4fa`, base `bd5beb7` from `HH1c.result`.

```
$ git -C <clone> log --oneline -3
466b4fa helm-home: box the portal payload per D-Bus signature so CreateSession and BindShortcuts build, with a bus-free self-test in the package check (test: helm-home-unit, helm-home-package, lint)
bd5beb7 program: plan revised against the panel's 35 errata; HH1b gated rework, HH1c typed; the round-1 judgement filed (test: lint)
e716308 program: charter, the program plan (increments 0–1 and increment 2's specs), HH1b, the closeout rows (test: lint)

$ git -C <clone> rev-list --count bd5beb7..HEAD
1

$ git -C <clone> diff --stat bd5beb7..HEAD
 docs/MAP.md                          |   4 +
 flake.nix                            |  33 ++-
 githooks/pre-commit                  |   4 +-
 pkgs/helm-home/package.nix           |  77 +++++++
 pkgs/helm-home/portal.py             | 131 ++++++++++++
 pkgs/helm-home/probe.py              | 389 +++++++++++++++++++++++++++++++++++
 pkgs/helm-home/probe_result.py       |  88 ++++++++
 tests/helm-home/test_portal.py       | 179 ++++++++++++++++
 tests/helm-home/test_probe_result.py | 127 ++++++++++++
 9 files changed, 1028 insertions(+), 4 deletions(-)
```

One commit. This is a fix round, so the contract is the chain's union
(`tasks.py touches … HH1c` → the ten paths of HH1a/HH1b/HH1c). All nine files
are in it; the tenth, `docs/OPERATIONS.md`, is simply unused. **No undeclared
touch**, and the plan file is untouched.

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` — both 190 bytes, `md5sum` `879fa39dd335dc0f1430a40ebf8d6f30`
on each. The body pastes Step 1's two reds, Step 3's four green lines and the
four mutant results; every one of them reproduces below. The last two lines, in
the policy order (`docs/board/policies.md:30-36`):

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run hh1g)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `HH1c.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`), the run equal to `hh1g`. Correct.

**The carry from HH1b is clean.** Fetched `task/HH1b` from
`~/factory/ws/hh1f/HH1b` (read-only); `FETCH_HEAD` is `b26b8a4`.
`git diff FETCH_HEAD:<f> HEAD:<f>` is **empty** for `pkgs/helm-home/package.nix`,
`pkgs/helm-home/probe_result.py`, `tests/helm-home/test_probe_result.py`,
`githooks/pre-commit` and `docs/MAP.md`. `portal.py` gains six docstring lines
and nothing else — no signature change, as the section says. `test_portal.py`
gains the four lines of `test_dbus_signature_for_unknown_raises`. `flake.nix`
carries exactly the two declared edits (below). Nothing was smuggled in behind
the carry.

**`probe.py` is +191/−66 against HH1b, and all of it is the section's.** The 66
deletions are a hoist, not a rewrite: `import gi`, the two `PORTAL_*` constants
and the whole `PortalBus` class move from inside `main()` to module scope, and
`self_check()` loses its local `gi` imports. That is what makes `_box` and the
bus-free `self_test()` reachable as module-level functions; the Global
Constraint permits it (`probe.py` is one of the two files allowed to import
`gi`, and no test imports it). Everything below `out = args.out or _default_out()`
in `main()` is untouched. The additions are `_box`, `_box_arg`, `FakeConnection`,
`self_test`, the `--self-test` flag and its dispatch — nothing else.

**Interfaces, item by item.**

| interface item | status |
|---|---|
| `helm-home-probe --self-test` exists, exits 0, no bus | MET — `probe.py:76-80`, `:238-265`; run through the package below, `EXIT=0`, stderr empty |
| prints exactly `CreateSession (a{sv})` and `BindShortcuts (oa(sa{sv})sa{sv})` | MET — those two lines and nothing else on stdout |
| any boxing failure exits 1 with the `TypeError` | MET — measured by mutants a and b, each an uncaught `TypeError` that fails the check |
| `_box` / `_box_arg` present, per the section's type rules | MET — `probe.py:106-146` (`GLib.Variant` passthrough, `bool`→`b`, `int`→`i`, `str`→`s`, `dict` and the `(name, dict)` list recursed, else a `TypeError` naming the method and the slot), `:149-161` |
| `PortalBus.call` boxes every argument | MET — `probe.py:170-183`; `grep -n 'options,) = args' pkgs/helm-home/probe.py` → **empty (exit 1)** |
| the self-test fixture mirrors `portal.py`'s real shapes | MET — `:246-256` uses `portal.request_tokens`, the same options dict, `portal.shortcut_request("<Super>Return")`, `""`, `{"handle_token": …}` |
| `portal.dbus_signature_for("NoSuchMethod")` raises `KeyError("NoSuchMethod")` | MET — `portal.py:61`, now asserted at `tests/helm-home/test_portal.py:175-179` (`excinfo.value.args == ("NoSuchMethod",)`) |
| `flake.nix`'s `helm-home-package` runs the self-test and greps the two lines | MET — `flake.nix:1172-1178`, two `grep -F` lines, positive greps (no `! grep` under errexit) |
| `pkgs.git` gone from the check's inputs | MET — `helm-home-unit`'s `nativeBuildInputs` is `[ helmPython ]`; the four remaining `pkgs.git` in `flake.nix` are `evidence-unit`'s and three unrelated derivations |
| `docs/MAP.md` regenerated | MET — `repomap.py --root <clone> check` → silent, `EXIT=0` |

One thing I checked rather than assumed: `lines=$(helm-home-probe --self-test)`
could have swallowed a non-zero exit. It does not — a failing command
substitution in an assignment fails under the builder's `set -e`, and mutants a
and b prove it empirically (both turn the check red).

```
$ /nix/store/3vhwqypslvfwgvdn93rch52g362aq16n-helm-home-0.1/bin/helm-home-probe --self-test
CreateSession (a{sv})
BindShortcuts (oa(sa{sv})sa{sv})
EXIT=0   (stderr empty)
```

## Red before green

Reproduced independently, by the section's own mutant (a) — `_box` returns the
`dict` unboxed — and the real check, not the commit body's paste:

```
$ nix build <clone>#checks.x86_64-linux.helm-home-package -L --no-link
helm-home-package> Traceback (most recent call last):
helm-home-package>   File ".../helm-home-0.1/lib/helm-home/probe.py", line 271, in main
helm-home-package>     return self_test()
helm-home-package>   File ".../helm-home-0.1/lib/helm-home/probe.py", line 246, in self_test
helm-home-package>     "CreateSession",
helm-home-package>   File ".../helm-home-0.1/lib/helm-home/probe.py", line 174, in call
helm-home-package>   File ".../gi/overrides/GLib.py", line 144, in _create
helm-home-package>     return self._LEAF_CONSTRUCTORS[format](value)
helm-home-package> TypeError: argument value: Expected GLib.Variant, but got str
EXIT=1
```

The red is the section's predicted red, at the first call (`CreateSession`) and
at the same `gi/overrides/GLib.py:144` leaf constructor HH1b's gate named.
Restored (`git checkout`), same command → `EXIT=0` with the two type strings.

The unit-side red is the one the section says goes green immediately, so I
showed it the way Step 1 prescribes — by breaking the arm (mutant c, `raise
KeyError(method)` → `return ""`):

```
$ nix build <clone>#checks.x86_64-linux.helm-home-unit -L --no-link
helm-home-unit> E       Failed: DID NOT RAISE KeyError
helm-home-unit> tests/helm-home/test_portal.py:177: Failed
helm-home-unit> FAILED tests/helm-home/test_portal.py::test_dbus_signature_for_unknown_raises - Failed: DID NOT RAISE KeyError
helm-home-unit> 1 failed, 17 passed in 0.05s
EXIT=1
```

`17 passed` is HH1b's baseline, so the new test is the whole of the delta and is
not vacuous. Restored → `18 passed`.

## Checks

Fresh clone, `XDG_CACHE_HOME` under the gate scratch directory. All three of the
section's `acceptance` names, `--rebuild` so nothing is a cache echo.

| check | command | result |
|---|---|---|
| helm-home-unit | `nix build <clone>#checks.x86_64-linux.helm-home-unit -L --no-link --rebuild` | **PASS** — `helm-home-unit> 18 passed in 0.02s`, `EXIT=0` |
| helm-home-package | `… helm-home-package -L --no-link --rebuild` | **PASS** — `helm-home-package> CreateSession (a{sv})` / `helm-home-package> BindShortcuts (oa(sa{sv})sa{sv})`, `EXIT=0` |
| the package's own installCheck | `nix build <clone>#packages.x86_64-linux.helm-home -L --no-link` | **PASS** — `helm-home> Running phase: installCheckPhase` / `helm-home> Gtk 4.22.4 Adw 1.9.3 portal org.freedesktop.portal.GlobalShortcuts` |
| lint | `… lint -L --no-link --rebuild` | **PASS** — `EXIT=0` |
| MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root <clone> check` | silent, `EXIT=0` |
| lint gate | `nix develop -c githooks/pre-commit` | `EXIT=1`, and only on `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; every formatter and linter arm green. MINOR-1 below. Restored; the clone ends `git status --porcelain` empty |

Green on the three the section names.

## Mutants

Each applied in the clone, run through the check that should see it, then
reverted. `mutants_total: 4` counts the section's Step 4 set (a, b, c and the
declared survivor d); one more was run outside it.

| # | mutant | named? | outcome |
|---|---|---|---|
| **a** | `_box` returns the `dict` unchanged | yes (Step 4a) | **KILLED** — `helm-home-package` red: `TypeError: argument value: Expected GLib.Variant, but got str`, at `self_test` → `call` → `GLib.py:144`, on `CreateSession`. Matches the commit body |
| **b** | `_box` boxes `str` as `("i")` | yes (Step 4b) | **KILLED** — `helm-home-package` red: `helm-home-package> TypeError: Must be number, not str` at `probe.py:248`. Matches the commit body |
| **c** | `portal.py:61` `raise KeyError(method)` → `return ""` | yes (Step 4c) | **KILLED** — `helm-home-unit` red: `Failed: DID NOT RAISE KeyError`, `1 failed, 17 passed in 0.05s`, killing exactly the one new test |
| **d** | the self-test call removed from the check's body, with `_box` broken (mutant a) as well | yes (Step 4d, declared survivor) | **SURVIVES by design** — `nix build … helm-home-package` → `EXIT=0` with a broken boxer. The check's own body is not under test; the operator's raise-key drill (§Operator step 2) stays the live measurement. Recorded, exactly as the section says |
| e | `PortalBus.call` reverted to HH1b's `tuple(args)` — the line the last round shipped | OUTSIDE | **KILLED** by `helm-home-package` (`TypeError: argument value: Expected GLib.Variant, but got str`); `helm-home-unit` still `18 passed`. This is HH1b's *surviving* mutant (c); it now dies. The regression that produced two rejections is pinned by a check for the first time |

Each named kill-mutant dies in exactly one check with exactly one message, and
the survivor is the one the section declares. Mutant e is the measurement that
matters most for the chain: unit tests still cannot reach `probe.py` (by Global
Constraint), so `helm-home-package` is the only instrument that can see the call
site — and it now does.

## Defects

None gating.

**MINOR-1 — `docs/OPERATIONS.md`: HH1b's MINOR-3 is not closed, and the
section's route for it is why.** The section's Files line declares the queue
block "regenerated … and committed in the same commit — the G8c route", and its
Step 5 orders `write-board` before the commit. `docs/OPERATIONS.md` is not in
the diff, and at HEAD the branch's lint gate still exits 1 on the block alone.
The commit body does not mention the file. But I regenerated it in the clone
before judging, and the block a task branch derives is branch-local and wrong
for main:

```
-… EV1 EV5 FIX5 FIX5b FIX5c HH1c HH2 HH3 HH4 IS1 IS2 KN1 PR1 …
+… EV1 EV5 FIX5 FIX5b FIX5c HH2 HH3 HH4 HH5 HH6 IS1 IS2 KN1 PR1 …
```

The branch's own commit subject makes HH1c look landed, so the regenerated queue
drops it and pulls HH5 HH6 forward — the same structural behaviour recorded on
HH1b and on every review in this chain. Committing it would have written a false
queue onto main. Skipping it leaves the hook red for one run and the integrator
handles it downstream. The implementer's choice is the better of the two the
section offered; the section is what asked for the worse one. Non-gating, and
nothing is owed on this commit.

**MINOR-2 — the commit body's `githooks/pre-commit exit 0` does not reproduce at
HEAD.** It exits 1, on MINOR-1's queue block alone (every formatter and linter
arm green). Presumably true in the seat's workspace at some point before the
commit; it is not true of the tree that is being merged. A body line that a gate
cannot reproduce is worth naming even when the thing it claims is immaterial —
the three acceptance checks are what gate this task, and they are green.

**MINOR-3 — the package output became non-deterministic this round.**
`nix build .#packages.x86_64-linux.helm-home --rebuild` now fails with
`may not be deterministic: output … differs`. Cause, measured: moving
`import portal` / `import probe_result` to module scope means the
`installCheckPhase` run of `--self-check` imports them while `$out` is still
writable, so `$out/lib/helm-home/__pycache__/{portal,probe_result}.cpython-314.pyc`
land in the output with a wall-clock source-mtime in the header
(`od -N 16` → `2b 0e 0d 0a 00 00 00 00 b3 35 a2 6a …`). Built from HH1b's
`probe.py` the same derivation produces no `__pycache__` at all, so this is new.
No check does `--rebuild` on the package, so nothing is red, and the wrapper and
both self-tests work; a later task can add `dontUsePythonRecompileBytecode`-style
cleanup or a `rm -rf $out/lib/helm-home/__pycache__` in `postFixup`. Recorded,
not gating, not owed here.

## Verdict

**APPROVED.**

HH1b's MAJOR-1 is measurably closed: under the shipped package's own interpreter
both `CreateSession` and `BindShortcuts` build their variants —
`(a{sv})` and `(oa(sa{sv})sa{sv})` — while the HH1b line kept as a control in
the same process still raises `TypeError: Expected GLib.Variant, but got str`.
All three acceptance checks are green in a fresh clone with `--rebuild`
(`18 passed`; the two self-test lines beside the `Gtk 4.22.4 Adw 1.9.3` line;
`lint` exit 0), the three named kill-mutants die with the messages the body
pastes, the declared survivor survives, and the mutant HH1b could not kill now
dies in `helm-home-package`. One commit, byte-identical subject, both trailers
in policy order, every file inside the chain's union. HH1b's MINOR-1 and MINOR-2
are closed; its MINOR-3 remains open because the route the section prescribed
for it would have written a branch-local queue onto main, which is a seam in the
plan, not a fault in the work.
