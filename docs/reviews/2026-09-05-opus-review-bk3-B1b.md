# Opus gate — seat run bk3, task B1b — REJECTED

## Summary

B1b does the substantive thing the 23:50 addendum asked for: `/var/lib/lanes`
joins the restic paths, `/var/lib/egress-broker` does not, the two lane payload
directories are excluded, the runbook says so naming the decision, and the claim
closes as verified. All four claimed checks are green from a fresh clone, the
toplevel builds, the commit subject is byte-identical to the plan's and carries
both trailers, and every touched file is inside `touches` (`docs/OPERATIONS.md`
only as the two-line derived queue block). Red-before-green is real: B1's tree
(`bk2`, 9a547a0) carrying the broker path, with B1b's `flake.nix` on top, dies
with exactly the new negative assertion's message.

One MAJOR stops it. Contract item 2 has two halves — assert the five patterns,
**and** assert that nothing under `/var/lib/lanes/*` survives the excludes
except the ledger. The first half is met by an exact-equality assertion
(`flake.nix:859-869`) and is solid. The second half is not met: the assertion
written for it (`flake.nix:875-880`) tests `elem "…/jobs"` and `elem "…/results"`
against the *same list* the line above has already pinned by equality, so it is
logically subsumed and can never fail on its own. Deleting it entirely leaves
`host-core` green (M-G), and the property its message claims to prove —
"they are the only non-ledger children of the known lane layout" — is pinned by
nothing: adding a fourth lane child directory to `nixosModules/modelLane.nix`
keeps `host-core`, `core-backup-wiring` and `lane-eval` all green (M-H), and
that new directory would silently join the backup. The plan offered a fixture
listing in `proton-backup-eval` or "an assertion over the known lane layout";
what landed is neither — it never reads the layout.

Four minors, all documentation or check-strength, none payload-bearing.

Everything below was run in a throwaway clone of `task/B1b` at d6cec02
(`…/scratchpad/gate-bk3-B1b`); nothing under `/home/dalhaka/factory` was touched.

## What the backup now holds

`nix eval .#nixosConfigurations.core.config.services.proton-backup.paths --json`
— **thirteen** paths (twelve on base, `/var/lib/lanes` added; the base twelve
all survive), confirmed against the built unit's `staticPaths` file:

```
/home/dalhaka/nixos-agent-env          /home/dalhaka/flakes
/etc/nixos                             /home/dalhaka/strategy
/var/lib/baskets/store                 …/-home-dalhaka-flakes-gaming/memory
…/projects/-home-dalhaka/memory        …/-home-dalhaka-flakes-media/memory
…/-home-dalhaka-nixos-agent-env/memory …/-home-dalhaka-strategy/memory
/home/dalhaka/.config/basket           /var/lib/evidence
                                       /var/lib/lanes            ← new
```

No element starts with `/var/lib/egress-broker`. Live (`/run/current-system`)
carries the same list minus `/var/lib/lanes` — twelve — so the count moved
12 → 13 (see MINOR 1).

`… .exclude --json` — exactly five, no CA pattern:

```
["**/.pytest_cache","**/.ruff_cache","/home/*/.cache",
 "/var/lib/lanes/*/jobs","/var/lib/lanes/*/results"]
```

**Restating the three defaults was necessary.** `services.proton-backup.exclude`
is a plain `lib.mkOption { type = listOf str; default = [...]; }`
(`nixosModules/protonBackup.nix:35-42`) — a definition *replaces* the default,
it does not merge. Proved by deleting the three default lines from
`hosts/core/proton-backup.nix` and re-evaluating:
`["/var/lib/lanes/*/jobs","/var/lib/lanes/*/results"]` — the defaults are gone.

**What survives under `/var/lib/lanes/*`.** The on-disk layout is
`/var/lib/lanes/<lane>/{ledger.jsonl, jobs/, results/}` and nothing else —
`nixosModules/modelLane.nix:205-210` declares exactly those three tmpfiles
entries, and `pkgs/lane/lane-run.py:62-65` / `lane-submit.py:66-71` construct
only `lane_dir`, `jobs_dir`, `results_dir`, `ledger_path`. The agent job's repo
snapshot and the `dsh` job's per-job home live *under* `jobs/<id>/`, so they
fall inside the `jobs` exclude. With `*` not crossing `/`, the two patterns
cover both child directories, leaving **each lane's `ledger.jsonl` and nothing
else**. The ledger carries metadata only — `_append_ledger` writes
`{ts, job, kind, model, provider, usage, wall_s}` (chat/agent) or
`{…, exit, wall_s}` (dsh) at `lane-run.py:196-206, 303-313, 458-468`; no prompt,
no completion, no repo content. **No payload-bearing path is in the backup.**

**Readability (not asserted anywhere).** restic runs as `User=dalhaka`
(`hosts/core/proton-backup.nix:27` → `nixosModules/protonBackup.nix:86-92`), not
as root — the plan's spec sentence ("restic runs as root (system unit)") is
wrong. It happens to work: lane dirs are `2770 root:lane`, the unit sets
`UMask=0027` so the ledger is group-readable, and
`nix eval … users.users.dalhaka.extraGroups` returns
`["networkmanager","wheel","helm","lane","kvm","kvm"]`. See MINOR 4.

## Rule behaviour

| # | Contract item | Result |
|---|---|---|
| 1 | `paths` gains `/var/lib/lanes` only; broker is not a path; `host-core` asserts no path starts with `/var/lib/egress-broker` | **met** — `flake.nix:847-858`; M-A kills the broker path |
| 2a | `exclude` is exactly the five patterns; CA pattern dropped | **met** — exact-equality assertion `flake.nix:859-869`; M-B and M-C both die |
| 2b | `host-core` asserts nothing but the ledger survives under `/var/lib/lanes/*` | **NOT met** — `flake.nix:875-880` is subsumed by 2a; M-G and M-H survive (MAJOR 1) |
| 3 | Runbook names `/var/lib/lanes` (ledger; jobs/results excluded) and states in one sentence, naming the decision, that the broker audit logs are never backed up; `core-backup-wiring` green | **met in substance** — `docs/runbooks/backup.md:30-34`, check green; but the sentence and the bullet are pinned by nothing (MINOR 2, MINOR 3), and the path count is wrong (MINOR 1) |
| 4 | Claim closes verified with the plan's text; `claims.py validate` green | **met** — `docs/ledger/claims.toml:239-247`, text byte-for-byte as the plan; validate exit 0; verified 10 → 11, gap 16 → 15 |

## Checks

Fresh clone of `task/B1b` @ d6cec02, `XDG_CACHE_HOME` under the scratchpad.

| Check | Result |
|---|---|
| `nix build .#checks.x86_64-linux.host-core -L --no-link` | exit 0 |
| `… core-backup-wiring` | exit 0 |
| `… proton-backup-eval` | exit 0 |
| `… lint` | exit 0 (94 formatted, 0 changed; all checks passed) |
| `… claims-validate` | exit 0 |
| `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-05 --repo-root .` | exit 0 |
| `nix develop -c githooks/pre-commit` | **exit 1** — "tasks: docs/OPERATIONS.md queue block was stale and has been regenerated". **Pre-existing and structural, not B1b's fault**: the same hook on the base commit 7d54467 also exits 1 the same way. The block is derived from the tree *including* HEAD's own commit subject, so B1b drops out of the queue the moment its commit exists; the block committed was correct at hook time. |
| `nix build .#nixosConfigurations.core.config.system.build.toplevel --no-link --print-out-paths` | `/nix/store/sd61sha7vn13pr7ggq75wqh5frmcw4jl-nixos-system-core-26.05.20260903.a5cc6f2` |

`nix store diff-closures /run/current-system <toplevel>`:

```
dsh: 49.4 KiB          python3-minimal: ∅ → 3.13.15, 25.3 MiB
hook: 43.2 KiB         seat: ∅ → ε        seat-run.py: ∅ → ε
egress-policy-seat.json: ∅ → ε            unit-seat: ∅ → .service
unit-egress-broker-seat.service: ∅ → ε    unit-egress-netns-seat.service: ∅ → ε
unit-script-egress-netns-seat: ∅ → ε      unit-script-egress-netns-seat-pre: ∅ → ε
```

That is **entirely SB1's seat units** (already on main, ahead of live) — the
restic change does not appear, because `diff-closures` groups by store-path name
and both the old and the new `exclude-patterns` / `staticPaths` derivations carry
the same name with no version. Diffed directly instead:

```
restic-backups-core-local.service  (live → new): only --exclude-file= and ExecStartPre= hashes change
exclude-patterns:  three lines → five (the two /var/lib/lanes/* patterns appended)
staticPaths:       twelve lines → thirteen (/var/lib/lanes appended)
```

So the restic delta is exactly the two data files plus the unit text that points
at them; everything else in the closure delta is what main already carried
beyond live.

## Closure diff

Backup content changes on the next switch, and only in one direction: restic
begins walking `/var/lib/lanes`, descends into each lane directory, skips `jobs/`
and `results/`, and picks up `ledger.jsonl`. Nothing leaves the backup. The
broker tree is untouched — it was never a path and now cannot become one without
`host-core` failing. No secret enters the backup: the ledger is metadata, the CA
tree is not reachable, and `~/.config/restic/password` remains outside every
path.

## Red before green

The plan's Step 1 is reproducible and real:

```
clone @ 9a547a0 (task/B1, run bk2 — the tree that carries /var/lib/egress-broker)
git checkout d6cec02 -- flake.nix          # B1b's host-core assertions only
                                            # (flake.nix is byte-identical between the two bases)
nix build .#checks.x86_64-linux.host-core -L --no-link   → exit 1
  host-core: no restic path may start with /var/lib/egress-broker
  (the broker audit logs never leave the machine by decision 2026-09-05 addendum)
```

Restoring `hosts/core/proton-backup.nix` to B1b's version (i.e. HEAD) → green.

## Mutation table

Eleven mutations, six killed.

| # | Mutation | Expected | Observed |
|---|---|---|---|
| M-A | `/var/lib/egress-broker` added to `paths` | red | **killed** — `host-core` exit 1, "no restic path may start with /var/lib/egress-broker (… decision 2026-09-05 addendum)" |
| M-B | `/var/lib/lanes/*/results` dropped from `exclude` | red | **killed** — `host-core` exit 1, "exclude must be exactly the three module defaults plus …/jobs and …/results" |
| M-C | `/var/lib/lanes/*/jobs` dropped | red | **killed** — same assertion, exit 1 |
| M-D | `/var/lib/lanes` removed from `paths` | red | **killed** — "host-core: /var/lib/lanes must be a restic path (each lane's ledger is the audit record)" |
| M-D2 | `/var/lib/lanes` → `/var/lib/lanes/` (trailing slash) | (say) | **killed by `host-core`** (the assertion is `lib.elem`, string equality) with the same message. Note `core-backup-wiring` stays green — see MINOR 2 |
| M-E1 | the broker sentence removed from the runbook, bullet kept | (say) | **survives** — `core-backup-wiring` exit 0. Nothing checks it (MINOR 3) |
| M-E2 | the whole lanes bullet removed, exclude sentence kept | plan expected red | **survives** — `core-backup-wiring` exit 0, because `/var/lib/lanes` is an infix of the exclude sentence's `/var/lib/lanes/*/jobs` (MINOR 2) |
| M-E3 | bullet **and** every `/var/lib/lanes` mention removed (my control) | red | **killed** — "core-backup-wiring: docs/runbooks/backup.md does not name these backup paths: /var/lib/lanes". The check is not vacuous overall |
| M-F | the claim left at its base `gap` state | (say) | **survives** — `claims.py validate` exit 0 *and* `claims-validate` exit 0. Nothing forces the closure; `review_by = 2026-09-19` is not yet stale |
| M-G | delete the whole "known lane layout" assertion (`flake.nix:870-880`) | should be red if load-bearing | **survives** — `host-core` exit 0. The assertion is subsumed by the equality assertion above it (MAJOR 1) |
| M-H | add a fourth lane child dir `"d /var/lib/lanes/${name}/spool 2770 root lane -"` to `nixosModules/modelLane.nix:210` | should be red per the assertion's own message | **survives** — `host-core` exit 0, `core-backup-wiring` exit 0, `lane-eval` exit 0 (`lane-eval` uses `lib.any`, presence not exhaustiveness, `flake.nix:1421-1429`). The new directory would join the backup unexcluded (MAJOR 1) |

## Findings

### MAJOR 1 — the "nothing but the ledger survives" assertion cannot fail; contract item 2's second half is unmet

`flake.nix:870-880`:

```nix
          # The known lane layout is /var/lib/lanes/<lane>/{ledger.jsonl, jobs/,
          # results/}. The two exclude patterns /var/lib/lanes/*/jobs and
          # /var/lib/lanes/*/results cover exactly the non-ledger children of a
          # lane, so under /var/lib/lanes/* nothing beside ledger.jsonl survives
          # the excludes (asserted over the known layout, contract item 2).
          assert nixpkgs.lib.assertMsg
            (
              nixpkgs.lib.elem "/var/lib/lanes/*/jobs" c.services.proton-backup.exclude
              && nixpkgs.lib.elem "/var/lib/lanes/*/results" c.services.proton-backup.exclude
            )
            "host-core: /var/lib/lanes/*/jobs and /var/lib/lanes/*/results must both be excluded (they are the only non-ledger children of the known lane layout, so only each lane's ledger.jsonl survives under /var/lib/lanes/*)";
```

The condition is `elem` over the very list that `flake.nix:859-869` has just
pinned with `==` to a five-element literal containing both patterns. It is
therefore true whenever the line above it is true — it can never fail
independently, and it never reads the lane layout it names. Two mutations show it:

- **M-G** — delete lines 870-880 outright: `nix build .#checks.x86_64-linux.host-core -L --no-link` → **exit 0**. A test that can be deleted without turning anything red is not a test.
- **M-H** — the property the message claims. Add one line to
  `nixosModules/modelLane.nix:210`,
  `"d /var/lib/lanes/${name}/spool 2770 root lane -"`, so the lane layout gains a
  fourth child that no exclude pattern covers: `host-core` **exit 0**,
  `core-backup-wiring` **exit 0**, `lane-eval` **exit 0**. The invariant
  "only each lane's `ledger.jsonl` survives under `/var/lib/lanes/*`" is pinned
  by a comment, and the next lane subdirectory — a spool, a cache, a scratch
  tree — joins the nightly backup silently.

The plan named the two acceptable proofs: "a fixture directory listing against
the patterns in `proton-backup-eval`, or an assertion over the known lane
layout". What landed is neither. The cheapest fix that would be a proof: derive
the lane children from the config that declares them and require each non-ledger
one to be excluded, e.g. in `host-core`

```nix
let laneChildren = builtins.filter (r: nixpkgs.lib.hasInfix "/var/lib/lanes/" r) c.systemd.tmpfiles.rules;
in assert nixpkgs.lib.assertMsg (nixpkgs.lib.all (r: … the dir it declares is either the lane root or matched by an exclude pattern …) laneChildren) "…";
```

so that M-H turns `host-core` red at the moment `modelLane.nix` grows a child.

### MINOR 1 — the runbook's path count is off by one

`docs/runbooks/backup.md:15` says "twelve of them"; the list is **thirteen**.
The built unit is the arbiter — `staticPaths` in the new toplevel has 13 lines,
and the runbook's own bullets enumerate 13 (2 + 2 + 2 + 5 + 1 + 1). The base was
already stale in a matching way ("eleven" against 12 real paths, because the
evidence-store bullet still said "joins the list once … lands"); B1b correctly
un-staled that bullet but then incremented the count only once where two
increments were owed. No check reads the number.

### MINOR 2 — `core-backup-wiring` does not actually pin the lanes bullet

`flake.nix:2033-2036` tests `hasInfix p backupDoc` for each path. Because
`/var/lib/lanes` is a substring of the exclude sentence's
`/var/lib/lanes/*/jobs` (`docs/runbooks/backup.md:37`), the whole documentation
bullet at :30-34 can be deleted and the check stays green (M-E2) — the plan's B1
Step 3 instructed exactly this mutation as the proof the check bites, and it
would have given a false green. Same reason `/var/lib/lanes/` with a trailing
slash passes it (M-D2; `host-core` catches that one). One line, next to the
existing `undocumented` test:

```nix
else if !(nixpkgs.lib.hasInfix "each lane's `ledger.jsonl`" backupDoc) then
  throw "core-backup-wiring: docs/runbooks/backup.md must keep the lane-ledger bullet"
```

### MINOR 3 — nothing checks the broker sentence

Removing `docs/runbooks/backup.md:31-34` (the "never backed up by decision
2026-09-05-audit-logs-backed-up.md; by its addendum they never leave the
machine" sentence) leaves `core-backup-wiring` green (M-E1) — as expected, since
it greps paths, not sentences. The negative claim in the config is asserted; its
statement to the operator is not. One line to add:

```nix
else if !(nixpkgs.lib.hasInfix "/var/lib/egress-broker" backupDoc) then
  throw "core-backup-wiring: docs/runbooks/backup.md must state that /var/lib/egress-broker is never backed up (decision 2026-09-05 addendum)"
```

### MINOR 4 — restic reads the lane ledgers by group membership, and nothing asserts it

The plan's spec asserts "restic runs as root (system unit), so mode 2770 is
readable". It does not: `services.restic.backups.core-local` inherits
`user = "dalhaka"` (`nixosModules/protonBackup.nix:86-92`,
`hosts/core/proton-backup.nix:27`), confirmed by
`nix eval … systemd.services.restic-backups-core-local.serviceConfig.User` →
`"dalhaka"`. It works only because `dalhaka` is in group `lane`
(`nixosModules/modelLane.nix:186-188`; eval confirms) against `2770 root:lane`
dirs and a `UMask=0027` ledger (`flake.nix:1516`). No assertion ties the backup
user to group `lane`; if `operatorUsers` ever changes, the nightly restic run
starts erroring on every lane directory and the newly-backed-up ledger silently
stops being backed up. Worth one `host-core` line
(`lib.elem "lane" c.users.users.${c.services.proton-backup.user}.extraGroups`).

## Verdict

**REJECTED** — one MAJOR: contract item 2's second half is not met. The
assertion written to prove "nothing but the ledger survives under
`/var/lib/lanes/*`" is logically subsumed by the exact-equality assertion above
it, can be deleted with every check still green (M-G), and does not read the
lane layout at all — so a fourth lane child directory added to
`nixosModules/modelLane.nix` keeps `host-core`, `core-backup-wiring` and
`lane-eval` green and joins the backup unexcluded (M-H).

Everything else is sound and should be kept: the paths, the excludes, the
negative broker assertion (a genuine, well-messaged test), the runbook wording,
the claim closure, the commit. The rework is small and local to `flake.nix`:
replace lines 870-880 with an assertion that derives the lane's children from
`systemd.tmpfiles.rules` (or a fixture listing in `proton-backup-eval`) and
requires each non-ledger child to be covered by an exclude pattern, shown red on
the M-H mutation before it goes green. Fold the four minors in while the file is
open — MINOR 1 is a one-word fix in the same runbook the task already touches,
and MINOR 2/3 are one `else if` each in `core-backup-wiring`; MINOR 4 is out of
`touches` and belongs in a follow-up.
