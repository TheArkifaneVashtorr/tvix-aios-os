# Minimal NixOS system for eval-only checks: no store build, no VM. Every
# checks.*-eval derivation forces `.config.system.build.toplevel.drvPath`,
# which makes the module system evaluate the unit definitions (ExecStart,
# serviceConfig, etc.) without ever building or running them — safe under
# the "build-only, never start a unit" constraint.
#
# stubBroker (checks/stub-broker.nix) supplies the
# services.egress-broker.instances option shape so services.comfyui can be
# evaluated against a real submodule; the "media" instance below is the
# same broker instance the host wiring plan will declare for real
# (hostAddress/namespaceAddress/listenPort per the spec), plus the model
# hosts the module's fetch path needs: huggingface.co (weights) and the
# Docker Hub hosts the container runtime needs to pull the pinned image
# (registry-1.docker.io, auth.docker.io, production.cloudflare.docker.com,
# docker.io) — listed here so the intent is visible even though the stub
# module does nothing with `allow`.
{
  nixpkgs,
  system,
  module,
}:
extra:
nixpkgs.lib.nixosSystem {
  inherit system;
  modules = [
    module
    (import ./stub-broker.nix)
    (_: {
      boot.loader.grub.enable = false;
      fileSystems."/".device = "none";
      fileSystems."/".fsType = "tmpfs";
      system.stateVersion = "25.11";
      nixpkgs.config.allowUnfree = true;
      # services.comfyui defaults gpu.enable = true, which sets
      # hardware.nvidia-container-toolkit.enable = true; that module asserts
      # an actual nvidia driver is configured (hardware.nvidia.datacenter.enable
      # or "nvidia" in videoDrivers) unless suppressed. The real host this
      # module targets has an RTX 5090 and does set this for real, so this
      # stand-in mirrors that rather than suppressing the assertion.
      services.xserver.videoDrivers = [ "nvidia" ];
      # hardware.nvidia's own module asserts this is set explicitly on
      # driver versions >= 560 (the real host's RTX 5090 needs the open
      # kernel modules — Blackwell has no closed-source driver option).
      hardware.nvidia.open = true;
      services.egress-broker.instances.media = {
        hostAddress = "10.100.2.1";
        namespaceAddress = "10.100.2.2";
        listenPort = 3130;
        allow = [
          "huggingface.co"
          "registry-1.docker.io"
          "auth.docker.io"
          "production.cloudflare.docker.com"
          "docker.io"
        ];
      };
    })
    extra
  ];
}
