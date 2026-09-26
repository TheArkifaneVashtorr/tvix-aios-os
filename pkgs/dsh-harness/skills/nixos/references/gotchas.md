verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-04

## Read when

Before committing anything — a final pass over traps that do not fit any
single reference above because each is a surprise about how two systems
interact, not a fact about one option or one command.

Procedural reference — no idiom pair; each item below points at the
reference with the full explanation where one exists.

## `2>/dev/null` on a gated command

A command whose entire job is to refuse loudly — a lint gate, an
assertion-bearing build, `nix flake check --offline` — must be allowed
to print that refusal. Redirecting its stderr away turns a caught
problem into a transcript that looks identical to success; never pipe
a gated command's stderr to `/dev/null`, in a runbook or in an agent's
own retry loop.

## statix and the module-header shape

A NixOS module with no named arguments still needs a real function
head — write `_:`, never `{ ... }:`. The latter evaluates fine (an
attrset pattern that matches anything, binding nothing) but `statix
check` flags it: a no-op destructuring pattern is exactly the shape
that pattern exists to catch, so writing it on a module that
deliberately ignores its arguments reads to the linter as a mistake
rather than an intentional no-args module.

## `environment.etc` `lines` merge needs `mkForce`

`environment.etc.<name>.text` is `lib.types.lines` — two modules
setting the same `<name>` do not conflict and neither wins by default,
they **concatenate** with `"\n"` between (module-system reference).
Expecting "the last module wins" here silently produces both texts
joined instead of an error to catch the mistake:

```nix module
{ config, lib, ... }:
{
  imports = [
    { environment.etc."example".text = "a"; }
    { environment.etc."example".text = lib.mkForce "b"; }
  ];
  assertions = [
    {
      assertion = config.environment.etc."example".text == "b";
      message = "mkForce should suppress the lower-priority definition";
    }
  ];
}
```

Drop the `lib.mkForce` above and the assertion fails: the merged value
becomes `"a\nb"` instead of replacing the base module's text — the
default is additive, not overriding, for every `lines`-typed option
this pin ships, not only `environment.etc`.

## Specialisation closures inside `nix store diff-closures`

`nix store diff-closures <before> <after>` is closure-inclusive: a
specialisation's toplevel is reachable from its parent's, so diffing
two _base_ generations reports package changes pulled in only through
a specialisation too — a diff that looks like "the base config changed"
can really mean "a specialisation changed and nothing at the base did"
(activation-and-switch reference has the full mechanism).

## User timers/services not started by a switch

A switch reloads a logged-in user's unit files but does not start a
unit that is newly enabled in that reload — nothing to diff against, so
nothing decides to start it (activation-and-switch reference, the
user-manager step). Expect a brand-new user timer or service to sit
inert until the next login, `loginctl enable-linger`, or a manual
`systemctl --user daemon-reload && systemctl --user start` — a switch
alone is not enough, however loudly it reports success.

## Graphics-stack renames at this pin

Three different things happen to the pre-rename _hardware.opengl_ names
at this pin, and only one of them is a build failure. `hardware.opengl.
{enable,driSupport32Bit,package,package32,extraPackages,extraPackages32}`
are **renamed**, via `lib.mkRenamedOptionModule`, onto their
`hardware.graphics.*` equivalents — a config still using the old name
still evaluates and still sets the new option. What a **definition** of
the old name produces is a `warnings` entry in `config` (`lib/modules.nix`
line ~1844, the `doRename` binding), routed through `lib.showWarnings` to
_builtins.warn_ (`lib/trivial.nix` lines ~778 and ~962) — the exact text
nix 2.28.5 prints at this pin, byte for byte:

```text
evaluation warning: The option `hardware.opengl.enable' defined in \
`<file>' has been renamed to `hardware.graphics.enable'.
```

(one logical warning line, wrapped above for width). Verified empirically
by evaluating a minimal `nixosSystem` with `hardware.opengl.enable =
true;` at this pin. A build that succeeds is not evidence a
legacy name is still current; grep build output for "has been renamed
to" (not "Obsolete option"), or for the option's own name. A second,
separate trace — 'Obsolete option ... is used. It was renamed to ...'
(`lib/modules.nix` line ~1541, `mkRenamedOptionModule`'s own `use`
binding) — fires only when something **reads** the old option's value
(e.g. another module evaluating _hardware.opengl.enable_ itself), not
merely when a config defines it — most single-file configs will only
ever see the definition warning above.
`hardware.opengl.{driSupport,s3tcSupport}` are actually **removed**, via
`lib.mkRemovedOptionModule`, and fail with that removal's own message
(e.g. "The setting can be removed."). _services.xserver.displayManager.
auto_ is removed the same way, with a message pointing at
`services.displayManager.autoLogin`. Only a name that is neither renamed
nor removed produces the "option does not exist" error a plain typo
would (debugging reference) — a renamed option gives the weakest signal
of the three, a build-succeeding warning, which is exactly why it is
easy to miss.
Verify any xserver/graphics option that reads like older documentation
before using it (SKILL.md rule 1), and do not treat a green build as
proof the option you wrote is still the current one — this subsystem has
moved more than most between releases.

## `system.stateVersion` is fixed at install, never bumped

It selects the on-disk/data-format defaults some services use to stay
compatible with what was first installed (postgresql's data directory
version is the classic case) — it is not a "which NixOS release am I
on" marker and bumping it after an upgrade can silently change a
service's default data format out from under existing state. Set it
once, at first install, and leave it.

## `hardware-configuration.nix` is exempt from formatting

Whatever `nixos-generate-config` writes for a host is verbatim
generator output, including its own comments — reformatting it earns
nothing (the generator does not read the formatted version back) and
makes a future re-generation's diff noisy for no reason. Exclude it
from the formatter's tree instead of asking it to match this skill's
own style.

## _builtins.getFlake_ impurity

A plain-path argument to _builtins.getFlake_ needs `nix eval --impure`
(nix-cli reference) and reads the working tree fresh each call — it is
the right tool for a one-off ad hoc evaluation outside any flake's own
`outputs`, never inside one: an `outputs` function already receives
every input, itself included as `self`, pre-fetched and pure, so
reaching for _builtins.getFlake_ from inside it re-fetches what is
already sitting in scope, impurely.

## nix-ld for a downloaded binary

"Could not start dynamically linked executable" or a bare exit 127 from
a file that is present and executable means the _loader_ is missing,
not the binary — `programs.nix-ld.enable` (debugging reference has the
full recipe and the verification step). It is never a reason to loosen
any network-egress control a machine enforces elsewhere.

## PATH in units

`systemd.services.<name>.path`/`runtimeInputs`/a literal
`/run/current-system/sw/bin/<tool>` — never the internal
_config.system.path_ attribute from a package itself reachable via
`environment.systemPackages` (systemd-units reference has the exact
infinite-recursion error this produces). A unit with no `path` set sees
no `/run/current-system/sw/bin` at all; "command not found" from a unit
that works fine typed at a shell is this, almost always.

## Read-only nix cache under an agent sandbox

`nix` keeps its binary-cache and eval caches in SQLite databases under
`$XDG_CACHE_HOME/nix` (default `~/.cache/nix`: `binary-cache-v6.sqlite`,
`fetcher-cache-v3.sqlite`, `eval-cache-v5/`), and an agent sandbox can
mount that directory read-only even while the workspace the agent is
editing stays writable. The symptom is `attempt to write a readonly database`
from a `nix build` or `nix eval` whose expression is fine — a SQLite
failure from one of those caches, not an error in the inputs (the
flake registry is a separate, unrelated file — a `flake-registry.json`
symlink under the same cache directory, plus a user registry at
`~/.config/nix/registry.json` — and is not what throws this
error). It is a sandbox artifact, not a broken store: point the cache
at a directory the agent can write (export `XDG_CACHE_HOME` to a
scratch directory inside the workspace) instead of reading it as a nix
defect, rebuilding anything, or loosening the sandbox to make the
default path writable.

## The bash tool and the file tool split /tmp

An agent edits the same task through two tools — a shell (bash) and a
file editor — and their `/tmp` are two different views of the
filesystem, not one shared directory: a file the shell writes under
`/tmp` may not exist for the editor, and the reverse. Never use `/tmp`
as a hand-off point between tools; make a scratch directory inside the
workspace and pass that path, so every tool reads and writes the same
bytes.

## Sources

- `nixos/modules/hardware/graphics.nix` (the _hardware.opengl_ →
  `hardware.graphics.enable`-family renames)
- `lib/modules.nix` (`doRename`'s `warnings` entry, line ~1844;
  `mkRenamedOptionModule`'s own `use` trace, line ~1541)
- `nixos/modules/rename.nix` (_services.xserver.displayManager.auto_
  removed in favour of `services.displayManager.autoLogin`)
- `nixos/modules/misc/version.nix` (`system.stateVersion`'s own
  description)
- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (state version compatibility guidance)
