# US1 (plan 2026-09-24-strict-user-spaces-1a.md; parent spec §3): the
# operator's user side in two parts -- tools.nix (the shell and the CLI set,
# shared shape with guests; a guest imports tools.nix alone) and desktop.nix
# (host only). Published and user-agnostic: no name, no home path, no
# interpolated source path (a path in `imports` is read at evaluation and
# leaves no reference to the flake source).
_: {
  imports = [
    ./tools.nix
    ./desktop.nix
  ];
}
