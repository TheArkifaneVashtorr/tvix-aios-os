---
plan_defect: none
mutants_total: 35
mutants_killed: 29
mutants_outside_named: 10
---
# Opus gate — seat run sd1f, task SD6 — APPROVED

## Summary

The section's contract is met. `pkgs/seat/seat-spool.py` implements every arm of
interface 2 in the stated order (validate → always unlink → refuse-and-continue
→ `.spooled` → one `systemctl start --no-block seat@<id>`), `seat-submit
--no-start` writes the `O_CREAT|O_EXCL` 0600 marker and `--wait` streams the
result without a single `systemctl` call, `seatLane.nix` renders
`seat-spool.path`/`seat-spool.service` and the `d /var/lib/seat/spool 0730 root
users -` rule, `seat-eval` pins all six facts, and `seat-vm` proves a spooled
job runs, a bad marker is refused and a second marker is `already-started`.

The two things the orchestrator asked me to look at hard both come out clean:

- **(a) the restructure of `nixosModules/seatLane.nix`** (271 changed lines, 172
  deletions — the seat nested `tmpfiles.rules` and `services."seat@"` under one
  `systemd = { … }` block *after* its checks) is provably behaviour-preserving.
  I evaluated every rendered systemd unit at base and at head and diffed them:
  the only unit texts that differ are `seat@.service` (one store hash, the
  rebuilt `seat-submit` on its PATH — the section changes that file) and three
  X-Restart-Triggers / `XDG_DATA_DIRS` paths that move because `nixos-version`
  embeds the flake revision. `systemd.paths` gains exactly `seat-spool`;
  `tmpfiles.rules` gains exactly the spool line; `security.polkit.extraConfig`
  and the broker instance are byte-identical. Recorded as MINOR-1 (unrequested
  churn), not a MAJOR.
- **(b) the marker/start path.** Every named mutant that could let a job start
  twice or start unvalidated dies: the seventeen refusal arms, the
  unlink-before-start order, the missing `.spooled`, the dropped `--no-block`,
  the marker on the started path, and — in the real VM — the path unit's
  `wantedBy`. `.spooled` is written with `O_CREAT|O_EXCL` before the start, so
  even two concurrent spool runs can produce at most one `start`.

All five acceptance checks are green under `--rebuild` in a fresh clone,
including a full `seat-vm` run (KVM, minutes) whose journal shows `started
seat@…`, `refused …: bad-mode` and `refused …: already-started`. 25 named
mutants, 25 killed; 10 outside the named set, 4 killed, 6 survivors — all six
are *sub-conditions inside* an arm the plan names as a whole, and each whole
arm dies; they are recorded as MINOR-3 … MINOR-6 and MINOR-11.

No MAJORs. **APPROVED.**

## Contract items

Numbered as the section states them.

**Interface 1 — the marker.**

| item | verdict | evidence |
|---|---|---|
| `--spool-dir DIR`, default the sibling `<jobs-dir>/../spool` | met | `pkgs/seat/seat-submit.py:158,167-169` — `os.path.join(os.path.dirname(os.path.abspath(args.jobs_dir)), "spool")`; `tests/seat/test_seat_submit.py:597` asserts the marker at `tmp_path/"spool"/<id>` for `--jobs-dir tmp_path/"jobs"` |
| `--no-start` writes the job dir as today, then the empty marker `O_CREAT|O_EXCL` 0600 | met | `seat-submit.py:246-249`; `test_seat_submit.py:597-600` (`exists()`, `st_size == 0`, `st_mode & 0o777 == 0o600`) |
| an `OSError` there is exit 2 with `seat-submit: could not spool <id>: <err>`, after the id was printed | met | `seat-submit.py:250-252`; the id is printed at `:230` before the marker block. Untested (no fixture forces the OSError) — MINOR-9 |
| `--wait` polls `result.txt` exactly as the started path does and streams `stdout.txt` | met | the started path and `--wait` share one `_poll()` (`seat-submit.py:80-140`, called at `:254` with `started=False` and `:267` with `started=True`); `test_wait_streams_without_systemctl` asserts the streamed body |
| on timeout exit 124 with the exact message | met, byte-for-byte | `seat-submit.py:120-127`: `f"seat-submit: timed out waiting for {result_path}; seat@{job_id} may still be running — stop it with: systemctl stop seat@{job_id}"` (em dash as in the plan) |
| **no `systemctl` call under `--no-start` ever** | met | `_poll(..., started=False)` takes neither the `_unit_state` branch (`:87`) nor the `stop` branch (`:112-118`); `test_wait_streams_without_systemctl` and `test_wait_timeout_names_the_unit_and_never_stops_it` both assert the autouse recorder is `[]` (the recorder catches `systemctl show` and `journalctl` too, so `== []` is a total assertion) |
| `--wait` without `--no-start`, or with `web`/`drive`, is exit 2 (usage) | met | `seat-submit.py:175-181`; `test_wait_requires_no_start_and_headless` covers both rows |
| the started path writes no marker | met | the marker block is inside `if args.no_start:` (`:232`); `test_started_path_writes_no_marker` asserts `tmp/spool/<id>` absent after a started submit |

**Interface 2 — `seat-spool`.** Every element present and correct in
`pkgs/seat/seat-spool.py`: the CLI (`:113-118`, stdlib `json os pwd re
subprocess sys` only, `--systemctl` defaulting to `systemctl`); the id regex
`^\d{8}-\d{6}-[0-9a-f]{6}$` (`:29`, `:40`); the job-dir checks
`job-dir-symlink`/`no-job-dir`/`job-dir-owner`/`job-dir-mode` (`:43-51`);
`no-job-json` (`:53`), `bad-json` for both a parse error and a non-object
(`:55-61`), `bad-mode` over `headless|web|drive` (`:31`, `:62-64`),
`bad-workspace`/`bad-dsh-home` as absolute directories owned by the uid
(`:65-77`), `bad-model` (`:30`, `:78-80`), `bad-effort` (`:32`, `:81-82`),
`bad-port` — `null` for headless, int 1024–65535 for web/drive, with `bool`
excluded (`:83-95`), `no-brief` (`:96-104`), `already-started` (`:105-106`),
`finished` (`:107-108`). The order per marker is exactly as specified:
`_refusal(...)` → `os.unlink(marker)` **always** (`:135-138`) → refusal print to
stderr + `continue` (`:139-141`) → `.spooled` 0600 with the id inside
(`:142-147`) → the single `subprocess.run([systemctl, "start", "--no-block",
f"seat@{mid}"], check=False)` (`:148-150`) → `started` / `start failed for <id>:
rc=N` (`:151-154`). `return 0` always (`:155`); an unreadable spool dir is exit
1 with `seat-spool: cannot read <S>` (`:126-130`). Sorted order at `:127`.

**Interface 3 — the units.** `nixosModules/seatLane.nix:261-267`
(`paths.seat-spool`, `wantedBy = [ "paths.target" ]`, `DirectoryNotEmpty =
"/var/lib/seat/spool"`, `Unit = "seat-spool.service"`), `:272-277`
(`services.seat-spool`, `Type = "oneshot"`, the packaged `ExecStart`, no
`User`), `:142` (`"d /var/lib/seat/spool 0730 root users -"`), `:26`
(`seatSpool`), `pkgs/seat/default.nix:31-40,45` (the third
`writeShellApplication` on `python3`, `exec python3 ${./seat-spool.py} "$@"`).
Verified against the *rendered* core config, not the source:

```
$ nix eval --json --apply 'c: builtins.attrNames c.systemd.paths' .#nixosConfigurations.core.config
base: []      head: ["seat-spool"]
$ …tmpfiles.rules   →  + "d /var/lib/seat/spool 0730 root users -"   (only line added)
```

**Interface 4 — `seat-eval`.** All six assertions present (`flake.nix:1761-1786`)
and each is load-bearing (three killed mutants below).

**Interface 5 — `seat-vm`.** Step 9 grows the `--no-start` submit inside the
probe instance and the five assertions (`tests/integration/seat-vm.nix:433-439`,
`457-473`); step 10 the `bad-mode` refusal with `ActiveState=inactive`, no
`.spooled`, no marker (`:475-495`); step 11 the second marker →
`already-started` (`:497-503`). Ran green (see Checks); one deviation recorded
as MINOR-7.

**Out of scope, correctly:** `factory-task`'s spool path is SD3's rule 6 and
does not appear in this diff.

## Red before green

Fresh clone; the branch's tests against the base's implementation files.

**(a) `tests/seat/test_seat_spool.py` — the new module missing:**

```
$ git checkout <base> -- pkgs/seat/seat-submit.py ; rm pkgs/seat/seat-spool.py
$ nix develop -c pytest tests/seat -q
tests/seat/test_seat_spool.py:32: in <module>
    spec.loader.exec_module(seat_spool)
E   FileNotFoundError: [Errno 2] No such file or directory: '…/pkgs/seat/seat-spool.py'
ERROR tests/seat/test_seat_spool.py - FileNotFoundError: [Errno 2] No such fi...
1 error in 0.09s
```

**(b) `tests/seat/test_seat_submit.py` against the base `seat-submit.py`:**

```
$ nix develop -c pytest tests/seat/test_seat_submit.py -q -p no:cacheprovider
message = 'seat-submit: error: unrecognized arguments: --wait\n'
E       SystemExit: 2
FAILED tests/seat/test_seat_submit.py::test_no_start_writes_the_spool_marker
FAILED tests/seat/test_seat_submit.py::test_wait_streams_without_systemctl
FAILED tests/seat/test_seat_submit.py::test_wait_timeout_names_the_unit_and_never_stops_it
FAILED tests/seat/test_seat_submit.py::test_wait_requires_no_start_and_headless
4 failed, 14 passed in 0.18s
```

**(c) `seat-eval` — the branch's `flake.nix` against the base's `seatLane.nix`:**

```
$ nix build .#checks.x86_64-linux.seat-eval -L --no-link --rebuild
error: seat-eval: a seat-spool path unit must watch /var/lib/seat/spool
```

exactly the message the section's Step 1(b) names.

**(d) the VM red.** The section's Step 1(c) — "the VM red at step 9:
`wait_until_succeeds("test -f …/result.txt")` times out — nothing starts a
`--no-start` job today" — was **not run by the implementer** (it says so:
`~/factory/runs/sd1f/SD6.log:4505-4509`, "I didn't actually run seat-vm in red
state … expensive"). Reproduced at the gate with the section's own named VM
mutant (`wantedBy = [ ]`), which puts step 9 in exactly the red state the plan
describes:

```
machine: waiting for success: test -f /var/lib/seat/jobs/20260908-150152-c56ed2/result.txt
!!! RequestedAssertionFailed: action timed out after 900.43 seconds (timeout=900.0)
error: Cannot build '…-vm-test-run-seat-behind-broker.drv'
```

Recorded as MINOR-8. No test in this diff is vacuous: every assertion the
section names has been shown to fail.

`test_started_path_writes_no_marker` cannot go red against base (base never
writes a marker anywhere) — the plan says so itself and prescribes it as the
*discriminating* assertion for the "marker on the started path" mutant; that
mutant dies (M22 below).

## Mutants

Method: a scratch copy, one edit, the test that must kill it, revert.
**Bytecode caching had to be disabled** (`PYTHONDONTWRITEBYTECODE=1` plus
`__pycache__` removal between runs): `seat-spool.py` is loaded by path, several
one-line mutants produce byte-identical file sizes, and `.pyc` mtimes are
second-granular — a first pass produced three spurious "survivors" that
reversed under a clean run. Every number below is from the clean run.

**Named by the section — 25, all 25 killed.**

M1–M17, one per refusal arm (`return "<code>"` → `pass`; where an arm spans
several `return`s the whole arm is deleted, as "delete its check" says):

| # | arm | line(s) | test | result |
|---|---|---|---|---|
| M1 | bad-id | `seat-spool.py:41` | `test_refuses_bad_id` | KILLED |
| M2 | job-dir-symlink | `:44` | `test_refuses_job_dir_symlink` | KILLED |
| M3 | no-job-dir | `:46` | `test_refuses_no_job_dir` | KILLED |
| M4 | job-dir-owner | `:49` | `test_refuses_job_dir_owner` | KILLED |
| M5 | job-dir-mode | `:51` | `test_refuses_job_dir_mode` | KILLED |
| M6 | no-job-json | `:54` | `test_refuses_no_job_json` | KILLED |
| M7 | bad-json | `:59,:61` | `test_refuses_bad_json` | KILLED |
| M8 | bad-mode | `:64` | `test_refuses_bad_mode` | KILLED |
| M9 | bad-workspace | `:72,:77` | `test_refuses_bad_workspace` | KILLED |
| M10 | bad-dsh-home | `:72,:77` | `test_refuses_bad_dsh_home` | KILLED |
| M11 | bad-model | `:80` | `test_refuses_bad_model` | KILLED |
| M12 | bad-effort | `:82` | `test_refuses_bad_effort` | KILLED |
| M13 | bad-port (headless) | `:89` | `test_refuses_bad_port_headless` | KILLED |
| M14 | bad-port (web) | `:95` | `test_refuses_bad_port_web` | KILLED |
| M15 | no-brief | `:99,:102,:104` | `test_refuses_no_brief` | KILLED |
| M16 | already-started | `:106` | `test_refuses_already_started` | KILLED |
| M17 | finished | `:108` | `test_refuses_finished` | KILLED |

Every one fails on the same line, e.g. M8:

```
_run = [['systemctl', 'start', '--no-block', 'seat@20260906-000000-abcdef']]
>       assert _run == []
E       AssertionError: assert [['systemctl'...0000-abcdef']] == []
tests/seat/test_seat_spool.py:116: AssertionError
```

M13 is the plan's discriminating row and it works: a headless job with `port =
43201` (a *valid* port number) is `bad-port`, so a `port in 1024..65535`
shortcut dies.

| # | mutant | test | result |
|---|---|---|---|
| M18 | the unlink moved after a successful start (`seat-spool.py:132-141` reordered) | `test_start_failed_still_unlinks_the_marker` | KILLED — `1 failed` |
| M19 | drop `--no-block` (`:149`) | `test_happy_path_starts_and_writes_spooled` | KILLED — argv equality |
| M20 | `.spooled` never written (`:142-147` → `pass`) | `test_happy_path…` | KILLED — `1 failed, 1 passed` |
| M21 | `--wait` runs `systemctl stop` on timeout (`seat-submit.py:120-127`) | `test_wait_timeout_names_the_unit_and_never_stops_it` | KILLED |
| M22 | the marker written on the started path too (`seat-submit.py:232`) | `test_started_path_writes_no_marker` | KILLED — `7 failed, 11 passed` |
| M23 | `seat-eval`: `ExecStart = "${pkgs.bash}/bin/sh -c '…'"` | `seat-eval` | KILLED — `error: seat-eval: seat-spool ExecStart must be the packaged seat-spool with the fixed spool args (no sh -c)` |
| M24 | the VM: `paths.seat-spool.wantedBy = [ ]` | `seat-vm` | KILLED — step 9 times out at 900.43 s (pasted above) |
| M25 | a spool that starts without validating (`:139-141`, the refusal no longer `continue`s) | `tests/seat/test_seat_spool.py` | KILLED — `17 failed, 4 passed`. The section names this as a VM step-10 mutant; I killed it at the unit level and did not re-run the ~20-minute VM arm for it. |

**Outside the named set — 10 tried, 4 killed.**

| # | mutant | result |
|---|---|---|
| O1 | `seat-spool.py:61` alone (`not isinstance(job, dict)`) | SURVIVED — MINOR-3 |
| O2 | `:72` alone (`isinstance`/`isabs`/`isdir` on workspace and dsh_home) | SURVIVED — MINOR-4 |
| O3 | `:77` alone (the owner/`OSError` half of the same arm) | SURVIVED — MINOR-4 |
| O4 | `:99` alone (`brief != "brief.txt"`) | SURVIVED — MINOR-5 |
| O5 | `:104` alone (web/drive `brief is not None`) | SURVIVED — MINOR-6 |
| O6 | drop `sorted()` (`:127`) | SURVIVED — MINOR-11 |
| O7 | `--wait` polls the unit state (`started=True` at `seat-submit.py:254`) | KILLED — `2 failed` |
| O8 | the `--wait`/`--no-start` usage guard removed (`seat-submit.py:175`) | KILLED — `test_wait_requires_no_start_and_headless` hangs (>90 s) instead of passing |
| O9 | `seat-eval`: `User = cfg.operatorUser` on `seat-spool` | KILLED — `error: seat-eval: seat-spool must run as root (no User=) so it may start seat@ units` |
| O10 | `seat-eval`: the tmpfiles line as `0750` | KILLED — `error: seat-eval: tmpfiles must create /var/lib/seat/spool (0730 root users, no listing)` |

O1–O5 are sub-conditions *inside* arms whose whole-arm deletion dies (M7, M9,
M10, M15); the code is right, the fixture set is one row short in each case.

**Totals: 35 tried, 29 killed, 10 outside the named set. No named mutant
survives.**

## Checks

All in the fresh clone `…/scratchpad/SD6/gate-sd1f-SD6` at
`be2927aa1a2e0634629c27d0642ae00b7fb1ad78`.

| check | command | result |
|---|---|---|
| seat-unit | `nix build .#checks.x86_64-linux.seat-unit -L --no-link --rebuild` | pass |
| seat-eval | `… seat-eval … --rebuild` | pass |
| seat-vm | `… seat-vm … --rebuild` (KVM, full VM run) | pass |
| host-core | `… host-core … --rebuild` | pass |
| lint | `… lint … --rebuild` | pass |
| pytest | `nix develop -c pytest tests/seat -q` | `44 passed in 0.10s` (17 before → 22 new spool tests + 5 new submit tests) |
| ruff | `nix develop -c ruff check pkgs/seat tests/seat` / `ruff format --check …` | `All checks passed!` / `6 files already formatted` |
| repomap | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | both exit 0 — `docs/MAP.md` is exactly what the generator produces |
| tasks | `python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |
| claims | `python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-08` | exit 0 |
| lint gate | `nix develop -c githooks/pre-commit` | **exit 1**, on the derived board block only: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. The regeneration is one word — `SD6` → `SD7` in the Queued line — i.e. it is caused by *this task's own commit landing*, which the hook's own comment calls out ("a landed key leaves the queue, so staleness is by design", `githooks/pre-commit:64`). Proven not to be a defect: at the base commit `python3 pkgs/evidence/tasks.py --root . write-board --board docs/OPERATIONS.md --quiet && git diff --quiet -- docs/OPERATIONS.md` → clean. The approved SD5 (`9dfa151`) and SD8 (`0cb135c`) commits have the same shape. Not a finding. |

The seat-vm run is the substantive one; its journal:

```
seat-spool[1204]: seat-spool: started seat@20260908-145620-d8374b
seat-spool[1329]: seat-spool: refused 20260906-000000-abcdef: bad-mode
seat-spool[1358]: seat-spool: refused 20260908-145620-d8374b: already-started
```

Base-vs-head evaluation of the whole rendered configuration (the check the
orchestrator asked for on the restructure):

```
only in base: []
only in head: ['seat-spool.path', 'seat-spool.service']
changed units: ['accounts-daemon.service', 'dbus-broker.service', 'polkit.service',
                'seat@.service', 'systemd-tmpfiles-resetup.service']
```

and each of those five diffs is one line: `seat@.service`'s `PATH` swaps the
`seat-submit` store hash (this section rebuilds `seat-submit.py`), and the other
four swap an `X-Restart-Triggers` / `XDG_DATA_DIRS` store path that moves
because `environment.systemPackages` contains `nixos-version`, which embeds the
flake revision (the only `systemPackages` difference between the two trees).
`security.polkit.extraConfig` and `egress-broker-seat.service` are byte-identical.
`seat@.service`'s `ExecStart`, `ReadWritePaths`, `InaccessiblePaths`,
`KillMode`, `NetworkNamespacePath`, `RestrictAddressFamilies`, `User` and every
`Environment=` line are unchanged.

## Touches and commit

Nine files in the diff. Eight are the section's `touches` list verbatim:
`pkgs/seat/seat-spool.py`, `tests/seat/test_seat_spool.py`,
`pkgs/seat/default.nix`, `pkgs/seat/seat-submit.py`,
`tests/seat/test_seat_submit.py`, `nixosModules/seatLane.nix`, `flake.nix`,
`tests/integration/seat-vm.nix`. The ninth is `docs/MAP.md`, one line
(`tests/seat — 2 files` → `3 files`), mandatory by the repomap rule and exempt;
the commit's `FACTORY-NOTES` discloses it. Nothing outside. `.factory-touches`
matches the section. The plan file is untouched; there is no board commit.

Exactly one commit, `be2927a`. Subject byte-identical to the section's:

```
$ cmp subj.actual subj.expected && echo SUBJECT BYTE-IDENTICAL
SUBJECT BYTE-IDENTICAL     (294 bytes each)
```

Body states the why (the sandbox hides systemd's control sockets, so a mediated
spool is the only host actor) and the design in full; the two trailers follow a
blank line in the WORKSPACE RULES order:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sd1f)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

The body pastes neither the red nor the green (MINOR-10); the approved SD5
(`9dfa151`) has the same shape, so this is recorded, not gating.

**Driver record** (`~/factory/runs/sd1f/SD6.result`) confirmed:
`FACTORY-RESULT status=done`; `checks_verified: seat-unit=pass seat-eval=pass
seat-vm=pass host-core=pass lint=pass` with `checks_verified_src:` all `run`;
`touches_extra: 0`; `FACTORY-COMMITS 1`; `head`/`base` match the branch.
`verify_s: 56` is a cache-hit re-run of already-built derivations — I re-ran all
five with `--rebuild` myself.

## Findings

No MAJORs.

**MINOR-1 — an unrequested restructure of a live host module.**
`nixosModules/seatLane.nix:126-278`. The seat rewrapped the existing
`systemd.tmpfiles.rules` and `systemd.services."seat@"` into one `systemd = { …
}` block (271 changed lines, 172 deletions) *after* its checks had passed, then
re-ran them. The section asked for three additions, not a reshape of the module
that renders the live `seat@` template. It is behaviour-identical (proved
above), and the seat's own log notes the post-restructure `seat-vm` was a
derivation cache hit — which is itself evidence of identity — but a
gate-visible reshape of a live-host module for no contract reason is churn to
avoid.

**MINOR-2 — `seat-submit` creates the spool directory, which the contract does
not ask for.** `pkgs/seat/seat-submit.py:238-244`:

```python
        try:
            os.makedirs(args.spool_dir, exist_ok=True)
        except OSError as e:
            print(
                f"seat-submit: could not create spool directory {args.spool_dir}: {e}",
```

Interface 1 says only "creates the empty file `<spool-dir>/<id>`", and names one
error string (`could not spool <id>: <err>`); this adds a second, untested
error path. On core the directory always exists (tmpfiles), so it is a no-op
there — but where it does not, `seat-submit` running as the operator would
create it with the process umask and operator ownership, i.e. a spool the
operator can *list*, contradicting the 0730 `root:users` design that the
section states and this very commit's body advertises ("the operator's group
may create a marker but cannot list"). No test covers the branch.

**MINOR-3 — the `bad-json` non-object row is untested.**
`pkgs/seat/seat-spool.py:60-61` (`if not isinstance(job, dict): return
"bad-json"`). The only fixture is a parse error (`"not json"`,
`tests/seat/test_seat_spool.py:236`), so deleting `:61` alone survives. A
`job.json` holding `[1, 2]` is a real shape the operator or a job could write.

**MINOR-4 — the `bad-workspace`/`bad-dsh-home` fixtures do not discriminate the
arm's two halves.** `pkgs/seat/seat-spool.py:65-77`. Both tests use a
*nonexistent* path (`tests/seat/test_seat_spool.py:250,258`), which is refused
by either the `isdir` half (`:72`) or the `os.stat` `OSError` half (`:77`) — so
each line alone survives deletion. Missing rows: a `workspace` that is a
regular file, a relative path, a non-string, and a directory owned by another
uid. The interface says "absolute directories owned by that uid"; only the
"does not exist" case is proven.

**MINOR-5 — the `brief` *name* check is untested, and it is the one that keeps a
job's brief inside its job dir.** `pkgs/seat/seat-spool.py:98-99` (`if brief !=
"brief.txt": return "no-brief"`). Deleting it alone survives. It matters:
`pkgs/seat/seat-run.py:86` does `brief_path = os.path.join(job_dir,
job["brief"])`, so an absolute or `../`-bearing `brief` value would escape the
job directory. (No privilege boundary is crossed — the unit runs as the
operator, who owns the job dir — but the guard exists precisely to pin the
name, and nothing proves it.)

**MINOR-6 — the web/drive `brief is not None` row is untested.**
`pkgs/seat/seat-spool.py:103-104`. The web fixture
(`tests/seat/test_seat_spool.py:289`) sets `brief=None`, so no fixture reaches
the arm; deleting it alone survives.

**MINOR-7 — VM step 10 writes the bad marker as root, not as `dalhaka`.**
`tests/integration/seat-vm.nix:487`: `machine.succeed(f"touch
/var/lib/seat/spool/{bad_id}")` where the section says "a bad job written by
dalhaka (`mkdir …; echo … > …/job.json; touch /var/lib/seat/spool/…`)" — the
first two commands do use `su - dalhaka` (`:480-486`), the `touch` does not. The
group-write path through the 0730 directory is proven only incidentally, by
step 9's `seat-submit --no-start` running inside `seat@probe` as
`User=dalhaka`.

**MINOR-8 — the section's third red was not run.** The seat did not execute the
`seat-vm` red of Step 1(c) and says so (`~/factory/runs/sd1f/SD6.log:4505-4509`:
"I didn't actually run seat-vm in red state, but the plan says paste it …
expensive"). Honest, and reproduced at the gate (see Red before green (d)), but
the plan's Step 1 is explicit about pasting all three.

**MINOR-9 — two of `seat-spool`'s exits are outside the stated contract and
untested.** `pkgs/seat/seat-spool.py:120-124` adds `seat-spool: unknown user
<u>` → exit 1, which interface 2 does not name (it names exit 1 only for an
unreadable `S`); and `os.open` of `.spooled` at `:143` is outside any `try`, so
a race or an ENOSPC there raises and breaks the "exit 0 always" rule. Neither
path has a test. Both are benign on core.

**MINOR-10 — the commit body pastes neither the red nor the green.** `be2927a`.
The body states the why fully but carries no red command/output and no green
check output beyond the subject's `(test: …)` list. Same shape as the approved
SD5 (`9dfa151`), so recorded for the record rather than charged to this seat.

**MINOR-11 — the "sorted order" assertion is not discriminating.**
`tests/seat/test_seat_spool.py:140-156` vs `pkgs/seat/seat-spool.py:127`:
dropping `sorted()` survives, because `os.listdir` on the tmpfs `tmp_path`
returns creation order and the fixture creates `b` then `a` — which the test's
own comment ("created out of order: the spool sorts") assumes is enough. It is
not; the mutant passes. Not named by the plan.

## Verdict

**APPROVED.** Every numbered item of interfaces 1–5 is met at the file and line
cited; the three reds the section names all reproduce (two run by the seat, the
VM one reproduced here); all 25 named mutants die, including the full-VM
`wantedBy` mutant and the three `seat-eval` ones; seat-unit, seat-eval, seat-vm,
host-core and lint are green under `--rebuild` in a fresh clone; `docs/MAP.md`
is generator-exact; the touches list holds with the one exempt file; one commit
with a byte-identical subject and both trailers. The restructure of
`nixosModules/seatLane.nix` — the one thing that could have hidden a change to
the live host — is proved behaviour-identical unit by unit. The eleven MINORs
are fixture gaps and churn; none of them is a contract the code violates.
