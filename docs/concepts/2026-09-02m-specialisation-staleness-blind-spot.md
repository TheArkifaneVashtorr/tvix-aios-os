# Concept 2026-09-02m — a specialisation is a snapshot; the drift tile can't see it go stale

**Class:** Helm coverage gap (drift tile) surfaced while writing the switch
runbook. **Status:** proposed (wiring round 1 Task 2 origin).

**Origin (2026-09-02, writing `docs/runbooks/switch-helm-gaming.md`):**
`specialisation.<name>.configuration` is built as part of the *same*
`nixosSystem` evaluation as the base toplevel — `/nix/var/nix/profiles/system/specialisation/<name>`
is a store path baked in at the last `nixos-rebuild switch`, not something
`switch-to-configuration test` re-evaluates when you run it. So: the
operator does the wiring-round-1 switch, later commits land in this repo
that touch `hosts/core/gaming.nix` (Lane H iterating on
`programs.gaming.*`), and the operator enters `gaming` by hand again with
the *same* `sudo .../specialisation/gaming/bin/switch-to-configuration
test` command from the runbook — it silently activates the **old**
snapshot. Nothing says so.

The reason nothing says so: Helm's **drift** tile
(`pkgs/helm/collect.py:tile_drift`) compares one thing —
`nixos-version --configuration-revision` (which reads
`config.system.configurationRevision`, `self.rev`, baked in once at
evaluation time) against `git rev-parse HEAD` in the repo. That value is
**identical** whether you're standing in `base` or in `gaming`, because
both specialisations came out of the same flake evaluation and inherit the
same top-level `system.configurationRevision = self.rev or self.dirtyRev`
(confirmed: no per-specialisation override exists anywhere in
`hosts/core/*.nix`, only `/etc/helm/profile` gets `lib.mkForce`d). A drift
tile reading `ok` right now only proves the *base* toplevel matches HEAD —
it says nothing about whether the `gaming` (or, later, `media`) sub-toplevel
you're about to enter was built from that same HEAD or from three commits
ago. There is no tile, no marker file, no assertion anywhere that a
specialisation's own store path is fresh relative to git.

**Idea:** either (a) a `helm-collect` reading of
`readlink /run/current-system/specialisation/<active>` compared against a
recorded "built at rev X" marker per specialisation (stamp it the way
`system.configurationRevision` is stamped, but scoped — e.g.
`environment.etc."helm/profile-rev".text = self.rev or self.dirtyRev`,
written identically in base and every specialisation, which would at least
let a future tile assert "the currently active `/etc/helm/profile`'s
recorded rev == HEAD"); or (b), cheaper and matching the "the runbook is
truth until v1 exists" posture of this round, a runbook-only mitigation:
tell the operator to run a full `nixos-rebuild switch` (not just
`switch-to-configuration test` against an old specialisation directory)
whenever they've pulled or committed changes to `hosts/core/gaming.nix`
since their last switch, before trusting a manual profile entry. Option (a)
is the real fix and belongs naturally in Helm v1, which already adds a
profile tile and a `last switch from <rev>` field
(`2026-09-02-helm-v1-switch-design.md` line 183) — this concept's
contribution is narrower and testable on its own: assert, at VM-test level,
that entering a specialisation whose store path predates a new commit does
**not** flip the drift tile, i.e. prove the blind spot exists before
proving the v1 fix closes it (same "prove the failure detector detects"
shape as concepts `2026-09-02j`/`2026-09-02l`).

**Payoff:** without this, an operator could test a stale gaming build for
weeks, see `helm-status` all green throughout (drift included), and
reasonably conclude the machine is running current code when the
specialisation directory they're actually standing in is not. The failure
mode is quiet — no red tile, no error, just silently testing old code —
which is exactly the kind of gap the house style asks concepts to name
before it costs a debugging session.

**Dependencies:** Helm v1's profile tile and `last switch from <rev>` field
(design already covers the fix); `checks.helm-vm`'s fixture user/timer
pattern (Helm Task 4) for the negative-proof VM assertion in option (a).

**Earliest landing:** with the Helm v1 factory, as an addition to its
already-planned profile tile — no new module surface needed, just the
per-specialisation rev marker and one VM assertion that a stale
specialisation doesn't turn the drift tile red on its own (it shouldn't;
the point is that *nothing* currently tells the operator it's stale at
all, which the v1 tile's "last switch from `<rev>`" field would fix by
being comparable against `git rev-parse HEAD` in the runbook or a future
tile, not by the drift tile itself changing meaning).
