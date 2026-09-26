verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Reviewing a NixOS change (the Opus gate) — apply every item below, in
this order, against the diff. Procedural reference — no idiom pair;
each item names the reference with the full explanation.

## 1. Every load-bearing test is falsifiable

For every load-bearing test in the diff, mutate the code under test
(revert the fix, invert a condition, drop the assertion) and run it —
show the test actually go red, not just reason about whether it would.
A test that cannot be made to fail this way is a `vacuous-test` major
(nixos-agent-env/docs/decisions/2026-09-03-test-based-reality-amendments.md):
it does not count as evidence toward accepting the change, however
green it reports. Do this before any of the items below — a change
resting on a test that never goes red is not ready for the rest of this
checklist.

## 2. Every option exists at the pin

Confirm each new or changed option path — do not trust an author's
citation, re-run it (`core` stands in below for the flake's own host
name):

```bash cmd
nix eval .#nixosConfigurations.core.options.services.openssh.enable.type --offline
```

(nixos-options-map reference for the general recipe and the module map;
SKILL.md rule 1). A path that only "looks right" because it reads like
an older tutorial is exactly what the gotchas reference's renamed-option
section catches.

## 3. Priorities and merges are the intended ones

For every option touched by more than one module or definition: is it a
`lib.types.lines`/`listOf`/`attrsOf` (additive — two definitions merge,
neither wins) or a scalar (conflicting unless one uses `lib.mkForce`/
`lib.mkDefault`)? A diff that adds a second definition to an
`environment.etc.<name>.text`-shaped option without `lib.mkForce`
usually means the author expected replacement and got concatenation
instead (gotchas, module-system references) — flag it even when the
build succeeds, since this class of mistake does not fail evaluation.

## 4. Hardening is complete, and the unit can still reach its tools

Every `serviceConfig` hardening directive the unit's job allows should
be present (systemd-hardening reference); then confirm the unit still
has a `path`/`runtimeInputs`/absolute-binary way to reach every tool it
execs (systemd-units reference, PATH in units) — a unit hardened to
`ProtectSystem = "strict"` that also cannot find `jq` on its `PATH`
fails for a different reason than the one under review, and both need
catching in the same pass, not the first one found and stop.

## 5. Assertions cover the negative

A module that changes behaviour under a condition should carry an
`assertions` entry (or an existing one should still apply) for the case
that condition being false or malformed produces — not just a happy
path that evaluates because nothing yet contradicts it (module-system
reference). A reviewer accepting a module with no assertion should be
able to say why none is needed, not just note that eval succeeded.

## 6. Tests discriminate (mutation survivors)

Item 1 applied specifically to VM tests: the same falsifiability check,
scoped to a `fail(...)`/`wait_for_unit`-style assertion instead of a
generic load-bearing test. A `machine.succeed(...)`-only test proves the
happy path exists; it
does not prove the change under review actually does anything (vm-tests
reference, negative proofs). Mentally revert the one line the change
depends on (a hardening directive, an assertion condition, a firewall
rule) and ask whether the paired test would then fail — a test that
would still pass with the fix backed out is a survivor: it did not
discriminate, and needs a `fail(...)`/`wait_for_unit`-style assertion
added before this change can be accepted on its evidence.

## 7. Closure and activation diffs match the plan

`nix store diff-closures <before> <after>` should show only the package
changes the plan describes — nothing extra pulled in, nothing expected
missing. Because the diff is closure-inclusive, a change confined to a
specialisation can appear in a base-to-base diff too (activation-and-
switch reference); check which generation actually carries a reported
package before treating it as a base-config regression. Pair this with
the activation diff recipe (verify reference) for what will actually
restart/reload on the next switch, not only what changed in the store.

## 8. User units are started as documented

If the plan or runbook claims a switch alone starts a newly-enabled user
service or timer, that claim is wrong (systemd-units, gotchas
references) — the review should require the plan to say a login,
`loginctl enable-linger`, or a manual `systemctl --user start` happens
too, or to show the unit was already enabled before this change.

## 9. No secrets

Nothing in the diff should place an actual secret value into anything
the module system writes to `config` — `environment.etc.<name>.text`,
a `writeText`, a literal in a unit's `ExecStart` — since every one of
those lands in `/nix/store`, world-readable (security reference).
Placeholders only; a real secret needs an out-of-store mechanism read
at activation time, which is a decision for the plan, not something a
reviewer approves by omission.

## 10. No network at build

Nothing offline-built should reach the network to satisfy this change —
no bare fetcher/`requireFile`/`outputHash`/`hash =`/`sha256 =`/`url =`
outside a properly pinned, reviewed fixed-output derivation (packaging
reference's static gate). Confirm with an actual offline build of the
repo's own checks rather than reading the diff for fetcher calls — this
is a generic recipe, not one tied to any one flake's check names:

```bash cmd
nix flake check --offline -L
```

## Sources

- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (module system, options)
- `/nix/store/ccppgf5px2d3ig46swcqy0jkiq3nw5bm-nix-2.28.5-doc`
  (`nix3-eval`, `nix3-flake-check`, `nix3-build`)
