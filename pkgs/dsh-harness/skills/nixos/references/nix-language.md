verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Writing or reading any Nix expression.

## Syntax in one pass

Nix is a lazy, purely functional expression language. Attribute sets
`{ a = 1; }`, lists `[ 1 2 3 ]`, functions `x: x + 1` (and
`{ a, b ? 1 }: a + b` for attrset arguments), `let ... in`, `if ... then
... else`, string interpolation `"${expr}"`. Every `.nix` file is a single
expression — there is no statement sequencing, only nested `let`s and
function calls.

```nix expr
let
  square = x: x * x;
in
  square 4
```

## Laziness

A value is not evaluated until something forces it (attribute selection,
string coercion, comparison, a strict builtin). An attribute set can carry
a broken member and still evaluate fine if nothing selects it:

```nix expr
{ a = 1; b = builtins.throw "never forced"; }.a
```

Forcing more than intended is a real failure mode: `builtins.deepSeq a b`,
`nix eval --json` (which serialises every reachable value) and NixOS
module evaluation (which forces every option's merged value to type-check
it) all force far more than a plain attribute select does.

## `with`, `inherit`, `rec`, `let`

- `with expr; body` brings `expr`'s attributes into scope for `body` —
  but only where no lexical binding (`let`, a function argument, or an
  enclosing `rec`) already provides that name. Lexical scope always wins,
  silently, with no error:

```text
$ nix eval --impure --expr 'let a = 1; in with { a = 2; }; a'
1
```

  The `let a = 1` binding shadows the `with`-introduced `a = 2`; nothing
  points this out. Prefer `inherit` or explicit attribute selection over
  `with` when the set's keys might collide with anything in scope.
- `inherit x;` inside an attribute set or `let` is `x = x;` pulled from
  the enclosing scope; `inherit (set) x y;` is `x = set.x; y = set.y;`.
- `rec { ... }` lets the set's own attributes see each other. A plain
  (non-`rec`) attribute set has no self-reference — each attribute only
  sees the enclosing scope, not its siblings.

**Right:** a `rec` set referencing its own attribute.

```nix expr
(rec {
  a = 1;
  b = a + 1;
}).b
```

**Wrong:** the same shape without `rec` — `a` is not in scope for `b`,
because a plain attribute set introduces no bindings for itself:

```text
$ nix eval --impure --expr '{ a = 1; b = a + 1; }'
error: undefined variable 'a'
       at «string»:1:14:
            1| { a = 1; b = a + 1; }
             |              ^
```

  (Use `let a = 1; in { inherit a; b = a + 1; }` when only some
  attributes need to reference others — it avoids making the whole set
  self-referential.)

## Paths vs strings, and store copies

A bare `./foo` or `/abs/path` is a path value, resolved relative to the
file it appears in (not the working directory) and kept distinct from a
string — `./foo == "foo"` is `false`, and path values cannot hold a
string context. The moment a path is coerced into a string —
interpolation (`"${./foo}"`), `toString` inside a derivation, or an
argument that itself expects a string — Nix copies it into the Nix store
and the interpolation becomes that store path, not the original path
text:

```text
$ nix eval --impure --expr 'let p = /etc/hostname; in "cfg is ${p}"'
"cfg is /nix/store/<hash>-hostname"
```

This is why a `path:` flake input, or `./data.txt` read via
`builtins.readFile p`, only ever sees what got copied into the store for
that evaluation — see the flakes reference for the tracked-files
consequence.

## String contexts

A string produced from a derivation or a store path carries a *context*:
a hidden set of store paths it depends on, invisible in the printed text
but tracked by Nix so that using the string (e.g. in a derivation's
`buildInputs` indirectly, or via `builtins.toFile name s`) forces a build
of what it names. `builtins.unsafeDiscardStringContext s` drops that
tracking — never reach for it to silence an "impure" error; the error is
telling you a value depends on something not yet built or not fixed at
eval time.

## Common eval errors, verbatim at this pin

```text
$ nix eval --impure --expr '{ a = 1; }.b'
error: attribute 'b' missing
       at «string»:1:1:
            1| { a = 1; }.b
             | ^
       Did you mean a?

$ nix eval --impure --expr 'let x = x + 1; in x'
error: infinite recursion encountered
       at «string»:1:9:
            1| let x = x + 1; in x
             |         ^

$ nix eval --impure --expr '1 + "a"'
error: cannot add a string to an integer
       at «string»:1:5:
            1| 1 + "a"
             |     ^
```

"attribute missing" (a real attribute path that isn't there) is a
different failure from "option does not exist" (a NixOS `mkOption`
declaration is missing) — the latter is a module-system error, covered
in the module-system and options-map references.

## `builtins` that matter

Evaluation-time reflection and control: `builtins.attrNames attrs`,
`builtins.hasAttr "x" attrs`, `builtins.getAttr "x" attrs`,
`builtins.toJSON x`, `builtins.fromJSON s`, `builtins.tryEval expr`
(catches `throw`/`assert` failures, not every runtime error — a genuine
builtin failure such as division by zero still aborts evaluation),
`builtins.deepSeq a b` (fully forces `a`, then returns `b`),
`builtins.trace msg val` (prints `msg` to stderr, evaluates to `val`).
Prefer the `lib` wrappers (`lib.attrNames`, `lib.optionalString`, …) in
module and package code; reach for the bare `builtins.*` form only where
`lib` has no wrapper or inside `lib` itself.

```nix expr
builtins.attrNames { b = 1; a = 2; }
```

## Sources

- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (language chapter)
- `/nix/store/ccppgf5px2d3ig46swcqy0jkiq3nw5bm-nix-2.28.5-doc`
  (language reference)
- `lib/modules.nix`, `lib/types.nix`, `lib/trivial.nix` in the pinned
  nixpkgs source (`builtins`/`lib` usage patterns)
