# GN12: the five packages media's flake published (media/flake.nix packages
# block), re-exported as host-flake outputs built against the consuming flake's
# pkgs (pkgsHost). Not the whole worldsPkgs set — comfy-feed, the guards and
# comfy-mutate stay module-internal.
{ pkgs }:
let
  worldsPkgs = import ./pkgs/comfy-worlds { inherit pkgs; };
in
{
  comfyui = import ./pkgs/comfyui/package.nix { inherit pkgs; };
  # GN18: media-fetch-models is defined once in worldsPkgs
  # (pkgs/comfy-worlds/default.nix) and re-exported here by inherit — the
  # inline builder this file carried is gone.
  # GN48: comfy-cards joins the re-exports so `nix run .#comfy-cards`
  # works from the repo before any switch.
  inherit (worldsPkgs)
    comfy-cards
    comfy-worlds-init
    media-comfy
    media-fetch-models
    comfy-upstream-probe
    ;
}
