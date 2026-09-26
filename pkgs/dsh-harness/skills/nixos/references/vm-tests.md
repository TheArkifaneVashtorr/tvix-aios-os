verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Writing or debugging a NixOS VM test.

## `pkgs.testers.runNixOSTest`

Takes one attrset: `name`, `nodes.*` (one NixOS module per machine —
each is evaluated as a complete NixOS configuration, so an option typo
or a type error inside a `nodes.*` module fails at driver-evaluation
time, the same way it would in any other NixOS config), and
`testScript` (Python, run once, with every node bound in scope under
its attribute name — see Multi-node below). `pkgs.nixosTest` is the
older name for the same thing pre-`testers`; both exist at this pin,
prefer `runNixOSTest` in new code. Below, this reference's own doc-test
blocks force only the driver's derivation — the module config is fully
evaluated, but the Python `testScript` itself never actually runs; the
Wrong block just below demonstrates the module-evaluation failure this
gets you for free, and a VM-graded eval task is where the script itself
is proven.

```nix vmtest
{
  name = "example";
  nodes.machine =
    { pkgs, ... }:
    {
      systemd.services.example = {
        wantedBy = [ "multi-user.target" ];
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${pkgs.coreutils}/bin/false";
        };
      };
    };
  testScript = ''
    machine.wait_for_unit("multi-user.target")
    machine.fail("systemctl is-active --quiet example.service")
  '';
}
```

**Wrong:** a typo'd option inside `nodes.*` — this is a full NixOS
eval per node, so it fails exactly like any other "nix module" mistake,
at driver-evaluation time rather than at VM run time:

```text
$ nix eval --impure --expr \
    '(pkgs.testers.runNixOSTest {
       name = "typo-demo";
       nodes.machine = _: { services.openshh.enable = true; };
       testScript = "machine.succeed(\"true\")";
     }).driver.drvPath'
error: The option `nodes.machine.services.openshh' does not exist.
       Definition values:
       - In `the argument that was passed to pkgs.runNixOSTest':
           { enable = true; }
```

(That is the "option does not exist" shape, not "attribute … missing" —
see the debugging reference for the difference and why it matters for
where to look.)

## `testScript` API

`succeed(*cmds)` raises on the first nonzero exit; `fail(*cmds)` raises
as soon as one of the commands exits zero — the negative-proof
primitive. Both default to no timeout (`timeout=None`); the `wait_*`
family below defaults to 900s instead and blocks until it succeeds or
that timeout expires: `wait_for_unit(name)`, `wait_for_open_port(port)`,
`wait_until_succeeds(cmd, timeout=)` (polls), `wait_for_file(path)`,
`wait_until_tty_matches`. `get_unit_info(unit)` is not one of these —
it is a one-shot, non-blocking query with no `timeout` argument at all;
call it after a `wait_for_unit` on the same unit, not instead of one.
`succeed`/`fail` take several commands and run each one _separately_,
each as its own `bash -c 'set -euo pipefail; <cmd>'` — they do not share a shell
process and do not short-circuit on each other; put the steps in one
string joined with `;` or `&&` when a later step must actually depend
on an earlier one running first.

## Multi-node

`nodes.*` for each machine; every node's hostname inside the test
network is its attribute name, referenced from `testScript` the same
way (`server.succeed(...)`, `client.wait_for_unit(...)`). Nodes share a
private test network by default — no other config needed to have one
node reach another by name.

```nix vmtest
{
  name = "multi-node-demo";
  nodes.server =
    { ... }:
    {
      services.openssh.enable = true;
    };
  nodes.client = _: { };
  testScript = ''
    server.wait_for_unit("sshd.service")
    server.wait_for_open_port(22)
    client.succeed("true")
  '';
}
```

## Users and lingering

A test node that logs a user in
(`systemd.services.*.serviceConfig.User`, or an explicit
`machine.succeed("loginctl enable-linger <user>")`) needs the same
linger fact as the real system: a user manager only starts alongside
the system for a user with lingering enabled or an active login session
— see the systemd-units reference for `ConditionUser` and what a switch
does not start; a VM test starting fresh every run makes this easier to
get wrong unnoticed, since the _first_ boot's activation already ran
before the test script does anything.

## `--offline` reproducibility

`nix build --offline .#checks.<system>.<name>` (or `nix flake check
--offline`) for a VM test behaves like any other offline build: every
node's closure must already be buildable from what is pinned and
substitutable — no version drift between what wrote the test and what
runs it. A test that only passes with network reachable (an actual
`curl` to an outside host inside `testScript`, say) is not reproducible
and is not something this skill's own eval tasks accept.

## Running interactively

`.driverInteractive` (alongside `.driver` on the same
`runNixOSTest`/`nixosTest` result) builds a driver that drops into a
Python REPL controlling live VMs instead of running `testScript`
unattended — build it, run the resulting script, and call the same
`machine.succeed(...)`-style methods by hand to reproduce a failure
step by step:

```bash cmd
nix build --offline .#checks.x86_64-linux.example.driverInteractive
./result/bin/nixos-test-driver
```

## Time and flakiness

`wait_for_*`/`wait_until_succeeds` all take a `timeout` in seconds
(defaults vary by call, commonly 900) — raise it for a genuinely slow
operation (a big service's first-start indexing), never to paper over a
race the test should instead wait on properly. `machine.sleep(n)` does
exist (it just runs `sleep n` in the guest) — use it only when guest
time genuinely has to pass, never in place of a `wait_for_unit` /
`wait_until_succeeds` that expresses the real precondition (a
`wait_for_unit` before the `succeed` that depends on it, not a bare
sleep).

## Negative proofs

A test that only calls `succeed` proves the happy path exists; it does
not prove hardening, an assertion, or a firewall rule actually blocks
anything — pair every such change with a `fail(...)` that exercises the
blocked path (the exact command that should now fail, not a weaker
stand-in) so a regression that silently removes the restriction turns
the test red. The `example` test above is exactly this shape: the unit
existing is not the claim, the unit _failing to become active_ is.

## Sources

- `nixos/lib/testing-python.nix`, `nixos/lib/testing/` (`runTest`,
  `driverInteractive`, node/network wiring)
- `pkgs/build-support/testers/default.nix` (`runNixOSTest`, `nixosTest`)
- `nixos/lib/test-driver/src/test_driver/machine.py` (the `Machine`
  method list above)
- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (writing and running NixOS tests)
