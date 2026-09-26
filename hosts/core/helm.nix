{ basket-pkg, ... }:
{
  # Helm: localhost-only status page (docs/superpowers/specs/2026-09-02-helm-design.md).
  # Open http://localhost:7700 in Firefox; `helm-status` prints the same tiles.
  services.helm = {
    enable = true;
    basketPackage = basket-pkg;
    # Helm v1 control surface (switch plan Task 5 / consolidated plan D1):
    # the loopback page gains the profile switch and the workspace launcher.
    # The allowlist is a FIXED literal -- D1 forbids deriving it from
    # config.specialisation (specialisations do not nest, so a derived list
    # would diverge inside every specialisation's own eval). "media" stays
    # OUT of profiles until round 2 wires specialisation.media; it is present
    # here only as a workspace.
    control = {
      enable = true;
      profiles = [
        "base"
        "gaming"
      ];
      # Removed by operator decision 2026-09-04, Helm Home replaces it: the
      # workspace buttons leave the live page (an empty map hides the
      # Workspaces section entirely). The module capability -- the launcher
      # and its tests -- stays intact.
      workspaces = { };
    };
  };
}
