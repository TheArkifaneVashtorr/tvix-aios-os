# Opus gate — seat run bk4, task B1c — APPROVED

## Summary

B1c fixes the one MAJOR that stopped B1b. The "only the ledger survives under
`/var/lib/lanes/*`" claim is now a derivation, not an echo: `host-core` reads
`c.systemd.tmpfiles.rules`, extracts the child of every `d /var/lib/lanes/<name>/<child> …`
rule, and requires each one to be covered by a `/var/lib/lanes/*/<child>` exclude
pattern (`flake.nix:772-791`, asserted at `flake.nix:900-901`). The M-H mutation —
adding a fourth lane child `spool` to `nixosModules/modelLane.nix:210` — now turns
`host-core` **red naming `spool`**, and deleting the assertion with that mutation
in place turns it **green** (M-G): the assertion is exactly what catches it. That
is the red-before-green the contract asked for, and it is reproducible in both
directions.

The three minors the plan folded in are all real and all pinned:
`core-backup-wiring` now bites on the runbook's lane-ledger bullet
(`flake.nix:2069-2070`) and on the broker sentence (`flake.nix:2071-2072`) — both
mutations are green on B1b's tree and red on B1c's; the path count reads
**thirteen** and the built unit's include file has exactly thirteen lines; the
runbook states the restic-user/`lane`-group fact and it is true by eval; and
`docs/ledger/claims.toml` opens `backup-user-lane-group-unasserted` (gap,
orchestrator, review 2026-09-19) while `lane-ledger-and-broker-audit-unbacked`
carries the plan's agreed text verbatim.

All four claimed checks are green from a fresh clone, plus `claims-validate`,
`lane-eval`, `claims.py validate --today 2026-09-06`, and the toplevel build. The
substance from B1b is unchanged and still correct: thirteen paths with
`/var/lib/lanes` in and nothing under `/var/lib/egress-broker`; five excludes;
the negative broker assertion still kills M-A. One commit, subject byte-identical
to the plan's, both trailers, every touched file inside the union of B1b's and
B1c's `touches`. `docs/OPERATIONS.md` is untouched.

Six minors, none payload-bearing: three concern the new regex's edges (a `D`-type
rule and a non-lane sibling directly under `/var/lib/lanes` slip past; a child
nested under an already-excluded parent gives a false red), one that the path
count is stated but not asserted, one that leaving the claim open is still caught
by nothing, and a shadowed binding. `githooks/pre-commit` exits 1 on HEAD — the
structural queue-block artifact, proven not B1c's doing (the base is green and
the queue's done-set comes from `git log --format=%s`).

Everything below was run in a throwaway clone of `task/B1c` at 4c832de
(`…/scratchpad/gate-bk4-B1c`) with `XDG_CACHE_HOME` under the scratchpad; nothing
under `/home/dalhaka/factory` was modified (B1b was read through a detached
worktree of a fetched `task/B1b`, removed afterwards).

## What the backup now holds

`nix eval .#nixosConfigurations.core.config.services.proton-backup.paths --json`
— **thirteen**, confirmed line-for-line against the built unit's include file
`/nix/store/j8yslca4gq03pc552j3p0vmp7zr051sg-staticPaths` (13 lines):

```
/home/dalhaka/nixos-agent-env            /home/dalhaka/flakes
/etc/nixos                               /home/dalhaka/strategy
/var/lib/baskets/store                   …/-home-dalhaka-flakes-gaming/memory
…/projects/-home-dalhaka/memory          …/-home-dalhaka-flakes-media/memory
…/-home-dalhaka-nixos-agent-env/memory   …/-home-dalhaka-strategy/memory
/home/dalhaka/.config/basket             /var/lib/evidence
                                         /var/lib/lanes
```

No element starts with `/var/lib/egress-broker`.

`… .exclude --json` — exactly five, matching the built
`/nix/store/bfkdxfidw3n4vqdmxgbwqcryfncsyx35-exclude-patterns`:

```
**/.pytest_cache
**/.ruff_cache
/home/*/.cache
/var/lib/lanes/*/jobs
/var/lib/lanes/*/results
```

**The lane layout, evaluated.** One lane exists on core —
`nix eval … services.model-lanes --apply builtins.attrNames --json` →
`["openrouter"]` — and the tmpfiles rules it renders are exactly three:

```
d /var/lib/lanes/openrouter 2770 root lane -
d /var/lib/lanes/openrouter/jobs 2770 root lane -
d /var/lib/lanes/openrouter/results 2770 root lane -
```

The new derivation maps those to children `["jobs","results"]` (the lane root
yields `null` and is filtered out — it is the ledger's parent), both are matched
by an exclude pattern, so `laneChildrenUnexcluded == [ ]`. **Each lane's
`ledger.jsonl` and nothing else survives under `/var/lib/lanes/*`, and the proof
is now derived from the module that declares the layout — not asserted about it
in a comment.** No payload path is in the backup.

**The restic user sentence is true.** `docs/runbooks/backup.md:36-39` says restic
runs as the operator and reads the lane dirs through the `lane` group.
`nix eval … services.proton-backup.user` → `"dalhaka"`;
`… systemd.services.restic-backups-core-local.serviceConfig.User` → `"dalhaka"`;
`… users.users.dalhaka.extraGroups` → `["networkmanager","wheel","helm","lane","kvm","kvm"]`
against `2770 root:lane` lane dirs (`nixosModules/modelLane.nix:186-188, 205-210`).
The runbook names the gap claim for the missing assertion, as the plan asked.

## Rule behaviour

| # | Contract item | Result |
|---|---|---|
| 1 | `host-core` derives lane children from modelLane's tmpfiles rules and asserts each non-ledger child is excluded; the message names the unexcluded child | **met** — `flake.nix:772-791` + `900-901`; M-H red with `unexcluded lane children: spool`; M-G (delete it, spool present) green, so the assertion is the thing that catches it |
| 2 | `core-backup-wiring` pins the runbook's lanes bullet by its own words and the broker sentence, each with a message; the count sentence says thirteen | **met** — `flake.nix:2069-2072`; M-C and M-D both red with their own messages; `docs/runbooks/backup.md:15` says thirteen and the built include file has 13 lines (count is *stated*, not asserted — MINOR 4) |
| 3 | The runbook states restic runs as the operator via the `lane` group; `claims.toml` opens `backup-user-lane-group-unasserted` (orchestrator, 2026-09-19) | **met** — `docs/runbooks/backup.md:36-39`; `docs/ledger/claims.toml:239-246`, `status = "gap"`, `owner = "orchestrator"`, `review_by = 2026-09-19`, with a `closes_by`; the statement is true by eval |
| — | B1b's payload carried unchanged (paths, excludes, negative broker assertion, claim closure) | **met** — 13 paths, 5 excludes, M-A and M-B still red; `lane-ledger-and-broker-audit-unbacked` (`claims.toml:249-258`) verified with the plan's text byte-for-byte |

## Checks

Fresh clone of `task/B1c` @ 4c832de.

| Check | Result |
|---|---|
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | exit 0 |
| `… core-backup-wiring` | exit 0 |
| `… proton-backup-eval` | exit 0 |
| `… lint` | exit 0 (94 formatted, 0 changed; all checks passed) |
| `… claims-validate` | exit 0 |
| `… lane-eval` | exit 0 |
| `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06 --repo-root .` | exit 0 |
| `nix build .#nixosConfigurations.core.config.system.build.toplevel` | `/nix/store/1w1fz9irpf9a4ygl5csaq2bqwwzkl8d6-nixos-system-core-26.05.20260903.a5cc6f2` |
| `nix develop -c githooks/pre-commit` | **exit 1** — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. Structural, not B1c's: the base 60490b4 runs the same hook to **exit 0**, and the queue's done-set is read from `git log --format=%s` (`pkgs/evidence/tasks.py:192`), so B1c drops out of the queue the instant its own commit subject exists. The only diff the hook wants is dropping `B1c` and its plan file from the two-line block; it cannot be pre-committed, because at commit time the hook regenerates it *back* to including B1c. Same artifact B1b hit. Everything else in the hook passed (treefmt, shellcheck, statix, deadnix, ruff, render.test.mjs). |

## Red before green

Both halves are reproducible.

**The lane-layout assertion.** On B1b's tree (fetched `task/B1b` @ d6cec02,
detached worktree), adding the fourth lane child

```
d /var/lib/lanes/${name}/spool 2770 root lane -     # nixosModules/modelLane.nix:211
```

leaves `host-core` at **exit 0** — the gap. On B1c's tree the same one-line
mutation gives

```
error: host-core: every lane child directory declared in modelLane's tmpfiles must be covered
by a /var/lib/lanes/*/<child> exclude pattern (so under /var/lib/lanes/* only each lane's
ledger.jsonl survives the backup); unexcluded lane children: spool
```

and deleting `flake.nix:900-901` with the spool line still in place puts
`host-core` back to **exit 0** (and `core-backup-wiring` exit 0) — so the new
assertion, and only it, is what catches the case.

**The two runbook mutations.** On B1b's tree, removing the lane-ledger wording
(keeping the broker sentence) → `core-backup-wiring` **exit 0**; removing the
broker sentence (keeping the bullet) → **exit 0**. On B1c's tree both are red
with their own messages (M-C, M-D below).

## Mutation table

Nine mutations run; six killed, one deliberately-green control, two survivors
reported as minors.

| # | Mutation | Expected | Observed |
|---|---|---|---|
| M-H | `"d /var/lib/lanes/${name}/spool 2770 root lane -"` added to `nixosModules/modelLane.nix:210` | red | **killed** — `host-core` exit 1, `… unexcluded lane children: spool` |
| M-G | delete the new assertion (`flake.nix:900-901`) with the spool line present | should turn the M-H case green | **as contracted** — `host-core` exit 0, `core-backup-wiring` exit 0. The assertion is load-bearing and is the sole catcher |
| M-A | `/var/lib/egress-broker` added to `paths` | red | **killed** — `host-core` exit 1, `no restic path may start with /var/lib/egress-broker (… decision 2026-09-05 addendum)` |
| M-B | `/var/lib/lanes/*/results` dropped from `exclude` | red | **killed** — `host-core` exit 1, `exclude must be exactly the three module defaults plus …/jobs and …/results` (the equality assertion fires first; the new lane-children assertion would catch it too) |
| M-C | the lane-ledger bullet's own words removed from the runbook (broker sentence kept) | red | **killed** — `core-backup-wiring` exit 1, ``must keep the lane-ledger bullet (each lane's `ledger.jsonl`) — /var/lib/lanes is the backup's audit record`` |
| M-D | the broker sentence removed (bullet kept) | red | **killed** — `core-backup-wiring` exit 1, `must state that /var/lib/egress-broker is never backed up (decision 2026-09-05 addendum …)` |
| M-E | `lane-ledger-and-broker-audit-unbacked` returned to its exact base open state (gap + `closes_by`) | (say) | **survives** — `claims.py validate` exit 0 *and* `claims-validate` exit 0. Nothing forces the closure; `review_by = 2026-09-19` is not yet stale. (Reverting `status` to gap while *dropping* `closes_by` is caught by the schema — `claims: lane-ledger-and-broker-audit-unbacked: gap needs closes_by` — but that is the schema, not the claim's substance) |
| P1 | the same spool child declared with tmpfiles type `D` instead of `d` | probe | **survives** — `host-core` exit 0 (MINOR 1) |
| P2 | `"d /var/lib/lanes/shared-cache 2770 root lane -"` — a non-lane directory directly under `/var/lib/lanes` | probe | **survives** — `host-core` exit 0 (MINOR 2) |
| P3 | `"d /var/lib/lanes/${name}/jobs/tmp 2770 root lane -"` — a child *under* an already-excluded parent | probe | **red** — `unexcluded lane children: jobs/tmp`. A false red in the safe direction (MINOR 3) |

## Findings

No MAJORs.

### MINOR 1 — the child regex only recognises tmpfiles type `d`

`flake.nix:784`:

```nix
                    m = builtins.match "d /var/lib/lanes/([^/ ]+)(/([^ ]+))? ?.*" r;
```

The leading literal is `d `. systemd-tmpfiles also creates directories with `D`
(and `v`, `q`, `Q`). Probe P1 — the same `spool` child written
`"D /var/lib/lanes/${name}/spool 2770 root lane -"` — leaves `host-core` at
**exit 0**, and that directory would join the backup unexcluded. The contract
specified the `d …` form and modelLane uses only `d`, so this is inside spec, but
a one-character widening (`"[dDvqQ] /var/lib/lanes/…"`) closes it.

### MINOR 2 — a non-lane directory directly under `/var/lib/lanes` is exempted as if it were a lane root

`flake.nix:783-787`: any rule matching `d /var/lib/lanes/<seg>` with no second
segment yields `null` and is filtered out, on the reasoning that the lane root is
the ledger's parent. Probe P2 adds `"d /var/lib/lanes/shared-cache 2770 root lane -"` —
a sibling of the lanes, not a lane — and `host-core` stays at **exit 0** while
that whole tree would be backed up (nothing excludes it, and it holds no ledger).
Closing it means checking the first segment against
`builtins.attrNames c.services.model-lanes` rather than exempting every
single-segment path.

### MINOR 3 — a child nested under an already-excluded parent gives a false red

`flake.nix:784` captures `([^ ]+)`, which spans `/`. Probe P3 —
`"d /var/lib/lanes/${name}/jobs/tmp …"` — yields child `jobs/tmp` and demands an
exclude pattern `/var/lib/lanes/*/jobs/tmp`, even though `/var/lib/lanes/*/jobs`
already excludes the whole subtree:

```
error: host-core: … unexcluded lane children: jobs/tmp
```

The failure is in the safe direction (a redundant exclude, never a leak), so it
is a nuisance, not a hole. A prefix test (`any (p: hasPrefix p child)`) instead of
exact `elem` would fix it.

### MINOR 4 — the path count is stated, not asserted

`docs/runbooks/backup.md:15` reads "thirteen of them" and is now correct — the
built include file has 13 lines and the bullets enumerate 13 (2 + 2 + 2 + 5 + 1 + 1).
But `core-backup-wiring` (`flake.nix:2050-2074`) only tests that each path is
*named* in the doc plus the two new infix sentences; nothing compares the number.
The next path added re-stales the word silently. One line next to `undocumented`
would pin it.

### MINOR 5 — nothing forces the claim closure (unchanged from B1b)

M-E: restoring `lane-ledger-and-broker-audit-unbacked` to its exact base open
state leaves `claims.py validate` and `claims-validate` at exit 0. The ledger's
schema is enforced; the *decision* to close is not, and `review_by = 2026-09-19`
is still in the future. Same as B1b's M-F; carried, not introduced.

### MINOR 6 — shadowed binding

`flake.nix:786`:

```nix
                children = builtins.filter (c: c != null) (map childOf c.systemd.tmpfiles.rules);
```

The lambda parameter `c` shadows the config binding `c` bound at
`flake.nix:761`. Correct as written (the outer `c` is used outside the lambda),
and `statix`/`deadnix` pass, but in a file where `c` means "core's config"
throughout, one letter apart from a real bug. `x` or `child` would read better.

## Verdict

**APPROVED.** The MAJOR from B1b is fixed and the fix is proven in both
directions: the spool mutation is red naming the child on B1c's tree and green on
B1b's, and deleting the new assertion makes the red case green again. The two
runbook sentences are now pinned by `core-backup-wiring` with their own messages
(both mutations green before, red after), the path count is right against the
built unit, the restic-user sentence is true by eval, and the new gap claim is
opened with owner and review date while the closed claim keeps the plan's agreed
text. Thirteen paths, `/var/lib/lanes` in, nothing under `/var/lib/egress-broker`,
five excludes, no payload path in the backup. Four claimed checks green plus
`claims-validate`, `lane-eval`, `claims.py validate --today 2026-09-06` and the
toplevel; one commit, subject byte-identical to the plan's, both trailers, files
inside `touches`, `docs/OPERATIONS.md` untouched. The only red is
`githooks/pre-commit`'s queue-block regeneration, shown green on the base and
mechanically unavoidable for a task commit.

Six minors, all non-blocking. MINOR 1 and MINOR 2 are the residual edges of the
new regex (a `D`-type rule, and a non-lane directory directly under
`/var/lib/lanes`) — worth folding into whichever task next touches `host-core`,
together with MINOR 3's prefix test. MINOR 4 (assert the count) and MINOR 6 (the
shadowed `c`) are one line each. MINOR 5 is carried from B1b and belongs to the
ledger's design, not this task.
