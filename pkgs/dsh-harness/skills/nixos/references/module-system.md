verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-04

## Read when

Writing a NixOS or nixpkgs module.

## `options`, `config`, `imports`

A module is `{ ... }` or a function of named args returning an attribute
set with any of `options` (declarations, via `lib.mkOption`), `config`
(definitions — values assigned to declared options), and `imports` (a
list of other modules, evaluated and merged in). `config` may also be
written flat, without the `config =` wrapper, when the module has no
`options`/`imports` at that level — the shorthand this skill's own
"nix module" doc-test blocks use.

```nix module
{ config, lib, ... }:
{
  options.services.example.message = lib.mkOption {
    type = lib.types.str;
    default = "hi";
    description = "Greeting to log at activation.";
  };
  config.environment.etc."example-message".text = config.services.example.message;
}
```

## `types.*` and submodules

`lib.types.str`/`lib.types.int`/`lib.types.bool`/`lib.types.path`/
`lib.types.package`/`lib.types.enum` (given a list of allowed values)/
`lib.types.nullOr`/`lib.types.listOf`/`lib.types.attrsOf` (each given
the element type they wrap) cover most options. `lib.types.submodule`
(given `{ options = ...; }`) types a nested attribute set as its own
mini-module — used as the element type of a `lib.types.listOf` (a list
of structured records) or a `lib.types.attrsOf` (a name-keyed map of
them), each entry getting its own `options`/`config` and its own merge
behaviour.

## `mkOption` and `mkEnableOption`

```nix expr
lib.mkOption {
  type = lib.types.bool;
  default = false;
  description = "Whether to do the thing.";
}
```

`lib.mkEnableOption` (given a short description) is shorthand for a
`lib.types.bool` option defaulting to `false` with a generated
description built from that text — reach for it for any plain on/off
toggle instead of hand-writing the `lib.mkOption` above.

## Priorities

Every definition has a numeric priority; **lower wins**. In order,
lowest number first:

- `lib.mkVMOverride` — `10` (used by `nixos-rebuild build-vm`)
- `lib.mkForce` — `50`
- plain assignment (no `mk*` wrapper) — `100`
- `lib.mkDefault` — `1000`
- `lib.mkOptionDefault` — `1500` (an option's own declared `default`)

`lib.mkOverride` (given a priority number and a value) sets any priority
directly. Two definitions at the *same* priority that disagree are a
conflict (below), not a silent pick — priority breaks ties, it does not
silence disagreement between equals.

## Merge semantics per type

- `lib.types.lines` **concatenates** all definitions with `"\n"` between
  them — every module contributing to it is additive, never overriding.
- `lib.types.listOf` **appends**: every definition's list elements are
  concatenated in module-import order.
- `lib.types.attrsOf` **unions** by key: modules setting different keys
  merge; two modules setting the *same* key follow the element type's own
  merge rule (recursing for `attrsOf (submodule ...)`, conflicting for
  `attrsOf str`).
- `lib.types.str`/`lib.types.bool`/most scalar types merge with
  `mergeEqualOption`: multiple definitions at the same priority must be
  *equal*, or it is a conflict — there is no "last one wins".

**Right:** two modules with a priority difference resolve without
ambiguity (`lib.evalModules` stands in for the full `nixosSystem` here —
same merge engine, no bootloader/filesystem boilerplate needed to show
it).

```nix expr
(lib.evalModules {
  modules = [
    { options.x = lib.mkOption { type = lib.types.str; default = ""; }; }
    { x = "a"; }
    { x = lib.mkForce "b"; }
  ];
}).config.x
```

**Wrong:** two modules assign the same `str` option at equal (plain)
priority — the exact conflict at this pin. `nix eval --expr` starts
with no `lib` in scope (unlike this skill's own "nix expr" doc-test
code blocks, which the check that runs them injects `lib` into) — bind
it from the locked flake rev, same as any other ad hoc one-off eval.
(`<nixpkgs>` is *not* pinned: it resolves through `NIX_PATH`/the flake
registry, which is exactly why reading it needs `--impure` — see
flakes.md's `self`'s `rev`/`dirtyRev` section, which lists `<nixpkgs>`
lookups among the impurities `--impure` governs. `builtins.getFlake url`
on a full rev is already locked, so no `--impure` is needed here.)

```text
$ nix eval --offline --expr \
    'let
      lib = (builtins.getFlake "github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d").lib;
    in (lib.evalModules {
    modules = [
      { options.networking.hostName =
          lib.mkOption { type = lib.types.str; default = ""; }; }
      { networking.hostName = "a"; }
      { networking.hostName = "b"; }
    ];
  }).config.networking.hostName'
error:
       … while evaluating the attribute 'value'
         at /nix/store/<hash>-source/lib/modules.nix:1083:7:
         1082|     // {
         1083|       value = addErrorContext "while evaluating …
             |       ^
         1084|       inherit (res.defsFinal') highestPrio;

       … while evaluating the option `networking.hostName':

       … while evaluating the attribute 'mergedValue'
         at /nix/store/<hash>-source/lib/modules.nix:1130:5:
         1129|     # Type-check the remaining definitions, and merge …
         1130|     mergedValue =
             |     ^
         1131|       if isDefined then

       (stack trace truncated; use '--show-trace' to show the full, detailed trace)

       error: The option `networking.hostName' has conflicting definition values:
       - In `<unknown-file>': "b"
       - In `<unknown-file>': "a"
       Use `lib.mkForce value` or `lib.mkDefault value` to change the
       priority on any of these definitions.
```

(Two of the quoted `lib/modules.nix` source lines above are trimmed
with `…` past this skill's 100-column line budget; the elided text is
unrelated commentary/interpolation, not part of the error itself.)

Omitting the `let lib = …; in` binding entirely — pasting only the
`(lib.evalModules { … })` expression, as if `lib` were already in
scope the way it is inside this skill's own "nix expr" doc-test blocks
— does not reach this conflict at all; it fails one step earlier with
`error: undefined variable 'lib'`.

  Fix by wrapping the value that should win in `lib.mkForce` (an
  intentional override) or the value that should yield in
  `lib.mkDefault` (a base-layer default another module can replace).

## `mkIf` and `mkMerge`

`lib.mkIf` (given a condition and a value) contributes that value to the
merge only when the condition is `true` at eval time — the option still
type-checks even when the condition is `false` (the whole module is
still evaluated, just this definition is dropped from the merge).
`lib.mkMerge` (given a list of attribute sets) merges them with normal
option-merge semantics, useful when a single module needs to contribute
several conditional `config` blocks.

## Assertions and warnings

The `assertions` option is a list of records shaped
`{ assertion = bool; message = str; }`; any `false` assertion fails the
whole evaluation with its message printed — always prefer this to a
runtime check for anything the evaluator can already see. `warnings` is
a list of strings printed (not fatal) during evaluation. Both are
internal, undocumented options — they exist and merge like any
`lib.types.listOf`, they just do not appear in the rendered options
manual.

```nix module
{ config, ... }:
{
  config.assertions = [
    {
      assertion = config.networking.hostName != "";
      message = "networking.hostName must be set";
    }
  ];
}
```

## `_module.args`

`_module.args` injects extra named arguments into every module's
function head (beyond the standard `config`/`lib`/`pkgs`/`options`) —
set it from one module, and every other module in the same evaluation
can take that name as a function argument. Used for a shared value (a
constant, a helper function) multiple modules need without importing it
by path.

## Specialisation

`specialisation.<name>.configuration` is itself a NixOS module: the
system built for that name inherits the parent configuration and layers
this module's `config` over it. A specialisation is a fully separate
`system.build.toplevel`, listed as a boot-menu entry alongside the base
generation — see the activation-and-switch reference for when it is
(re)built.

## `config` vs `options` recursion traps

Reading an option's own merged value back out of `config` from inside
that same option's `default =` or `type =` is infinite recursion
(`config` is not fully evaluated until every option's definitions,
including defaults, are resolved). Reading the *declaration* instead —
another option's `type`/`default`/`description` off `options` rather
than its merged value off `config` — is always safe from within an
option declaration; it does not force `config`.

## Sources

- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (writing modules, options)
- `lib/modules.nix` (priorities, `mergeModules`, assertions/warnings
  wiring) and `lib/types.nix` (merge functions per type) in the pinned
  nixpkgs source
- `nixos/modules/misc/assertions.nix`
