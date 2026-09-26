---
plan_defect: wrong-fact
mutants_total: 2
mutants_killed: 2
mutants_outside_named: 2
model: opus
---
# Opus gate — seat run hh1f, task HH1b — REJECTED

## Summary

The section was implemented literally and well: `dbus_signature_for` is exactly
the pure function the Interfaces describe, the two new tests are real (they go
red for the right reason, and each named mutant kills exactly one of them), the
`(options,) = args` unpack is gone, the flake and hook wiring is complete, the
MAP is regenerated, one commit, both trailers, subject byte-identical. Every one
of the section's own acceptance checks is green in a fresh clone.

But the task's stated purpose — its own subject line, "so BindShortcuts's four
arguments no longer crash the probe" — is measurably not achieved, and I
measured it rather than reasoned about it. The line the section prescribes,
`pkgs/helm-home/probe.py:121`, still raises on the very first portal call. Run
against the shipped package's own Python and typelibs
(`/nix/store/x7wdrklayy2m2253bb4wsi2v06b0nivs-helm-home-0.1`), with the exact
payloads `pkgs/helm-home/portal.py:108-116` and `:120-123` hand to
`PortalBus.call`:

```
boxed BindShortcuts OK: (oa(sa{sv})sa{sv})
shipped BindShortcuts -> TypeError: argument value: Expected GLib.Variant, but got str
shipped CreateSession -> TypeError: argument value: Expected GLib.Variant, but got str
```

The signature string HH1b introduces is **correct** — line 1 proves it: with the
`a{sv}` values boxed, the four-argument payload builds as
`(oa(sa{sv})sa{sv})`. What still fails is the values. PyGObject's `a{sv}`
constructor requires every value to be a `GLib.Variant`; `portal.py` is
stdlib-only by Global Constraint and therefore hands plain `str` and `dict`,
and nothing between it and `GLib.Variant(...)` boxes them. So the probe cannot
issue `BindShortcuts` (the crash HH1's MAJOR named, now a `TypeError` at the
same line instead of a `ValueError` one line above) and — this is new
information — it cannot issue `CreateSession` either. HH1's review asserted
twice that the old adapter "works for `CreateSession`"
(`~/factory/runs/hh1/HH1.review.md:1616`, `:1728`); measured on the pin, it
never did.

That is a MAJOR, and it is the **plan's**, not the implementer's: the section's
Interfaces dictate the replacement line character for character, the implementer
wrote it, and the plan's own residual paragraph mis-states what the change would
buy ("this round removes the *known-wrong* case (BindShortcuts crashing
outright)" — it does not; it changes which exception is raised). No acceptance
check can see it, by the plan's own Global Constraint that no test imports
`probe.py`, which is exactly why a gate measurement rather than a check is the
right instrument here.

**REWORK** — one MAJOR, on a fix whose other five requirements are all met.

## Diff against the section

Fresh clone of `task/HH1b` at `b26b8a4`, base `e716308` from `HH1b.result`.

```
$ git -C <clone> log --oneline -3
b26b8a4 helm-home: PortalBus.call builds the D-Bus signature per method instead of assuming CreateSession's shape, so BindShortcuts's four arguments no longer crash the probe (test: helm-home-unit, helm-home-package, lint)
e716308 program: charter, the program plan (increments 0–1 and increment 2's specs), HH1b, the closeout rows (test: lint)
969bc0a integrate UI1 into integ/ui1

$ git -C <clone> rev-list --count e716308..HEAD
1

$ git -C <clone> diff --stat e716308..HEAD
 docs/MAP.md                          |   4 +
 flake.nix                            |  36 ++++-
 githooks/pre-commit                  |   4 +-
 pkgs/helm-home/package.nix           |  77 ++++++++++
 pkgs/helm-home/portal.py             | 125 +++++++++++++++++
 pkgs/helm-home/probe.py              | 264 +++++++++++++++++++++++++++++++++++
 pkgs/helm-home/probe_result.py       |  88 ++++++++++++
 tests/helm-home/test_portal.py       | 170 ++++++++++++++++++++++
 tests/helm-home/test_probe_result.py | 127 +++++++++++++++++
 9 files changed, 891 insertions(+), 4 deletions(-)
```

One commit. Eight of the nine files are the section's `touches` list verbatim;
the ninth, `docs/MAP.md`, is named in the section's Files line as "regenerated —
exempt" and is the Global Constraints' standing exemption. **No undeclared
touch.** `docs/OPERATIONS.md` is not in the diff and the plan file is untouched.

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` — both 215 bytes, `md5sum` `e3f27b29…` on each. Body
pastes Step 1's red, Step 3's two green lines and Step 4's two mutant
assertions, all of which I reproduce below. The last two lines, in the
policy order (`docs/board/policies.md:30-36`):

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run hh1f)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `HH1b.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`) and the run equal to `hh1f`. Correct.

**The carry is clean.** The section says five files restore byte-for-byte from
HH1's rejected commit and two take this round's edits. Fetched `task/HH1` from
`~/factory/ws/hh1/HH1` (read-only) into the clone; `FETCH_HEAD` is `73e8e5b`, as
the section states. `git diff FETCH_HEAD:<f> HEAD:<f>` is **empty** for
`pkgs/helm-home/package.nix`, `pkgs/helm-home/probe_result.py` and
`tests/helm-home/test_probe_result.py`. The other three carry exactly the
declared edits and nothing else:

```
-            (options,) = args
-                GLib.Variant("(a{sv})", (options,)),
+                GLib.Variant(portal.dbus_signature_for(method), tuple(args)),
```

`portal.py` gains the sixteen lines of `dbus_signature_for` and nothing else;
`test_portal.py` gains the twelve lines of the two new tests and nothing else.
Nothing was smuggled in behind the restore.

**Interfaces, item by item.**

| interface item | status |
|---|---|
| `portal.dbus_signature_for(method) -> str`, pure, stdlib | MET — `pkgs/helm-home/portal.py:42-55` |
| `"CreateSession"` → `"(a{sv})"` | MET — `:51-52`, asserted at `tests/helm-home/test_portal.py:164` |
| `"BindShortcuts"` → `"(oa(sa{sv})sa{sv})"` | MET — `:53-54`, asserted at `test_portal.py:170`; and measured to be the *right* string (## Summary, line 1 of the probe output) |
| any other method raises `KeyError(method)` | MET in code (`:55`) — but no test reaches it; mutant (d) below survives |
| `PortalBus.call` uses it, `(options,) = args` gone | MET — `pkgs/helm-home/probe.py:115-127`; `grep -n 'options,) = args' pkgs/helm-home/probe.py` → **empty (exit 1)** |
| `FakeBus` needs no edit | MET — `test_portal.py` diff is the two new tests only |
| flake.nix: the `helmHome` binding, two packages, two checks | MET — `:166`, `:672`/`:675-679`, `:1163` (`helm-home-unit`, at eight spaces) and `:1181` (`helm-home-package = helmHome;`) |
| flake.nix: both ruff lists gain `pkgs/helm-home tests/helm-home` | MET — `:1045`, `:1046` |
| `githooks/pre-commit`: the same two entries | MET — `:25`, `:26` |
| `docs/MAP.md` regenerated | MET — `nix develop -c python3 pkgs/evidence/repomap.py --root . check` → silent, `EXIT=0`; the diff adds `pkgs/helm-home`, both check names and `tests/helm-home` |

`import portal` sits inside `main()` (`probe.py:101`) and `PortalBus.call`
reaches it as a closure free variable — I checked the semantics rather than
assuming them (`def main(): import json as portal; class B: def call(self):
return portal.dumps` resolves). Not a defect.

## Red before green

Reproduced independently, by deleting only the `dbus_signature_for` definition
(`sed -i '42,57d' pkgs/helm-home/portal.py`) and running the real check:

```
$ nix build <clone>#checks.x86_64-linux.helm-home-unit -L --no-link
helm-home-unit> E       AttributeError: module 'portal' has no attribute 'dbus_signature_for'
helm-home-unit> tests/helm-home/test_portal.py:170: AttributeError
helm-home-unit> FAILED tests/helm-home/test_portal.py::test_dbus_signature_for_create_session - AttributeError: module 'portal' has no attribute 'dbus_signature_for'
helm-home-unit> FAILED tests/helm-home/test_portal.py::test_dbus_signature_for_bind_shortcuts - AttributeError: module 'portal' has no attribute 'dbus_signature_for'
helm-home-unit> 2 failed, 15 passed in 0.04s
EXIT=1
```

Both new tests go red, with the exact line the section's Step 1 predicts, and
the surviving **15 passed** is HH1's own baseline — so the two tests are the
whole of the delta and neither is vacuous. `git checkout -- pkgs/helm-home/portal.py`,
then the same command → `17 passed in 0.02s`, `EXIT=0`. Red before green,
measured, not taken from the commit body.

## Checks

Fresh clone, `XDG_CACHE_HOME` under the gate scratch directory. All three of the
section's `acceptance` names, `--rebuild` so nothing is a cache echo.

| check | command | result |
|---|---|---|
| helm-home-unit | `nix build <clone>#checks.x86_64-linux.helm-home-unit -L --no-link --rebuild` | **PASS** — `helm-home-unit> 17 passed in 0.02s`, `EXIT=0` |
| helm-home-package | `… helm-home-package -L --no-link --rebuild` | **PASS** — `helm-home> Running phase: installCheckPhase` / `helm-home> Gtk 4.22.4 Adw 1.9.3 portal org.freedesktop.portal.GlobalShortcuts`, `EXIT=0` |
| lint | `… lint -L --no-link --rebuild` | **PASS** — `EXIT=0` |
| MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root . check` | silent, `EXIT=0` |
| lint gate | `nix develop -c githooks/pre-commit` | `EXIT=1`, and only on `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; every formatter and linter arm green. The regenerated block drops `HH1b` (the branch's own subject makes it look landed) and adds `HH5 HH6` — the structural per-branch behaviour recorded on every review in this chain. Restored; the clone ends `git status --porcelain` empty |

Green on the three the section names.

## Mutants

Each applied in the clone, run through `helm-home-unit`, then reverted.
`mutants_total: 2` counts the section's Step 4 named pair; two more were run
outside it.

| # | mutant | named? | outcome |
|---|---|---|---|
| **a** | `dbus_signature_for` returns `"(a{sv})"` unconditionally (BindShortcuts arm dropped) | yes (Step 4a) | **KILLED** — `helm-home-unit> E       AssertionError: assert '(a{sv})' == '(oa(sa{sv})sa{sv})'` / `tests/helm-home/test_portal.py:170: AssertionError` / `FAILED …::test_dbus_signature_for_bind_shortcuts` / `1 failed, 16 passed in 0.05s`. Byte-identical to the commit body's paste |
| **b** | `dbus_signature_for` returns `"(oa(sa{sv})sa{sv})"` unconditionally (CreateSession arm dropped) | yes (Step 4b) | **KILLED** — `helm-home-unit> E       AssertionError: assert '(oa(sa{sv})sa{sv})' == '(a{sv})'` / `test_portal.py:164: AssertionError` / `FAILED …::test_dbus_signature_for_create_session` / `1 failed, 16 passed in 0.04s` |
| c | `probe.py:115-121` reverted to `(options,) = args` + hardcoded `"(a{sv})"` — the section's own predicted survivor | OUTSIDE | **SURVIVES** — `helm-home-unit> 17 passed in 0.02s`, `EXIT=0`. Exactly as Step 4's note says: no test imports `probe.py`, so the call site is outside unit reach. A documented gap, not a defect |
| d | `raise KeyError(method)` at `portal.py:55` replaced by `return "(a{sv})"` (the fail-closed arm dropped) | OUTSIDE | **SURVIVES** — `17 passed in 0.02s`. The Interfaces make the `KeyError` a contract term; the section's Tests row 13 names no mutant for it, so nothing pins it. Recorded as MINOR-1 |

Both named mutants die, each killing exactly the one test it targets and leaving
the other 16 green — the discrimination the Tests row promises. The two
survivors are both structural gaps in what the unit suite can reach, one of them
predicted by the section itself.

## Defects

**MAJOR-1 — `pkgs/helm-home/probe.py:121`: the probe still cannot make a portal
call; the fix changes the exception, not the outcome. Plan defect
(`variant-boxing`), not implementer defect.**

`GLib.Variant(portal.dbus_signature_for(method), tuple(args))` is handed
`args` built by `portal.py`, which is stdlib-only and therefore builds plain
Python values: `portal.py:120-123` passes
`[{"handle_token": <str>, "session_handle_token": <str>}]` and `:108-116`
passes `[<str>, [("raise", {"description": <str>, …})], "", {"handle_token": <str>}]`.
PyGObject's `a{sv}` leaf constructor requires each value to be a
`GLib.Variant`. Measured with the shipped package's own interpreter and
typelibs, feeding `dbus_signature_for`'s own output the payloads `portal.py`
actually produces:

```
boxed BindShortcuts OK: (oa(sa{sv})sa{sv})
shipped BindShortcuts -> TypeError: argument value: Expected GLib.Variant, but got str
shipped CreateSession -> TypeError: argument value: Expected GLib.Variant, but got str
```

(`gi/overrides/GLib.py:144`, `_LEAF_CONSTRUCTORS[format](value)`.) Three
consequences, in order of weight:

1. **The commit's own subject claim is false.** "BindShortcuts's four arguments
   no longer crash the probe" — they still do, at `probe.py:121`, one line below
   where they used to and with `TypeError` instead of `ValueError`.
2. **HH1's MAJOR is not closed as it was written.** Its harm sentence is "The
   probe can never actually bind the raise key"
   (`~/factory/runs/hh1/HH1.review.md:1666`). That is still true after this
   round. Only the arity half of the diagnosis is fixed.
3. **New information the previous gate got wrong.** HH1's review states twice
   that the old adapter "works for `CreateSession`" (`:1616`, `:1728`).
   Measured on the pin, it does not: `CreateSession` fails with the same
   `TypeError`. So the probe has never issued a single portal call, and the
   §Operator step 2 raise-key measurement this plan defers to would have died on
   the first call, before reaching anything this round touches.

**Why the plan and not the implementer.** The section's Interfaces prescribe the
replacement line character for character and the implementer wrote precisely
that. The plan's residual paragraph names the right gap (no gi-level coverage)
but draws the wrong conclusion from it — "this round removes the *known-wrong*
case (BindShortcuts crashing outright)". It does not remove it; it renames it.
The plan reasoned about the GVariant construction from the interface XML without
measuring PyGObject's boxing rule, and the one gate instrument that could see it
is a measurement, not a check.

**The shape of the fix** (for the next round to size, not a prescription): the
boxing has to happen where `gi` is available, i.e. in `PortalBus.call` in
`probe.py` — walk `args` and wrap every `a{sv}` value in `GLib.Variant("s", v)`
(or the right leaf type) before constructing. To keep it under CI rather than
under the operator's eye, the decision of *which* leaves are `v` is pure and can
live in `portal.py` next to `dbus_signature_for` with its own unit test; only
the wrapping call stays in the gi adapter. That would also give mutant (c) above
something to die against.

**MINOR-1 — `pkgs/helm-home/portal.py:55`: the `KeyError` arm is an interface
term with no test.** The Interfaces say "any other `method` raises
`KeyError(method)`", and it is the fail-closed behaviour the section argues for
explicitly. Mutant (d) — replace the raise with `return "(a{sv})"` — leaves
`17 passed`. The section's Tests row 13 names only the two positive assertions,
so this is the plan's seam and not the implementer's; a one-line
`pytest.raises(KeyError)` would close it. Recorded, not gating.

**MINOR-2 — `flake.nix:1168-1169`: the `helm-home-unit` derivation carries
`pkgs.git` "for HH10's accept tests", which do not exist.** Carried verbatim
from HH1's approved wiring (`git diff FETCH_HEAD:flake.nix` — the binding is
unchanged in substance), so nothing is owed on this commit; noted so it is not
mistaken later for a live dependency.

**MINOR-3 — `docs/OPERATIONS.md` (not in the diff): the branch's lint gate exits
1 on its first run**, on the queue-block regeneration alone. Structural for
every task branch here, anticipated by the Global Constraints, handled
downstream. Recorded, not gating. Nth occurrence in this chain.

## Verdict

**REWORK.**

Everything the section asked for in letter is present, green and pinned — one
commit, byte-identical subject, both trailers in policy order, no undeclared
touch, red reproduced independently, both named mutants killed, all three
acceptance checks green in a fresh clone — but the change does not do what its
own subject says it does: measured against the shipped package, `BindShortcuts`
still crashes at `pkgs/helm-home/probe.py:121` with `TypeError: Expected
GLib.Variant, but got str`, and so does `CreateSession`, which the previous gate
believed worked. The signature string is right; the values are not boxed, and
`portal.py` cannot box them. That is one MAJOR, attributable to the plan
(`plan_defect: variant-boxing`), and it is the same bug class HH1 was rejected
for, one exception deep.
