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
    (_: {
      boot.loader.grub.enable = false;
      fileSystems."/".device = "none";
      fileSystems."/".fsType = "tmpfs";
      system.stateVersion = "25.11";
      nixpkgs.config.allowUnfree = true;
    })
    extra
  ];
}
