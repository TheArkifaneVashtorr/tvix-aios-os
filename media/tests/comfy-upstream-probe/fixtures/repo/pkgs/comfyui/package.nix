# Fixture copy of pkgs/comfyui/package.nix at its pre-W1 state.
# Minimal: holds only the literals read_pins/rewrite_pins touch, so a rewrite
# leaves no stray old version in prose that would fail the assertions.
{ pkgs }:
let
  version = "0.34.3";
  src = pkgs.fetchFromGitHub {
    owner = "Comfy-Org";
    repo = "ComfyUI";
    rev = "87465b8f1f64a27a46f16f22b13b410494dca66d";
    hash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
  };
in
pkgs.stdenvNoCC.mkDerivation {
  pname = "comfyui";
  inherit version src;
}
