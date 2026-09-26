{
  pkgs,
  claude-code-pkg,
  dsh-openrouter-pkg,
  ...
}:

{
  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  environment.systemPackages = [
    claude-code-pkg
    # dsh-openrouter: the DeepSeek Harness on the host for the operator's own
    # work, routed to OpenRouter (docs/runbooks/lanes.md, "Working with dsh
    # yourself"). Reads its key from ~/.config/openrouter/key.
    dsh-openrouter-pkg
  ]
  ++ (with pkgs; [
    bubblewrap
    socat
    git
    nodejs
  ]);

  boot.kernelModules = [ "vhost_vsock" ];

  # Smartcard daemon: required for YubiKey PIV access (age-plugin-yubikey).
  services.pcscd.enable = true;

  users.users.dalhaka.extraGroups = [ "kvm" ];

  # The dsh factory root, declared by the host config rather than hidden as
  # a gitignored dotdir inside a repo. docs/decisions/2026-09-04-parallel-
  # agent-workflows.md's workspaces mechanism: a declared directory outside
  # every git repo removes three failures at once -- a clone inside a
  # checkout is a nested repo git cannot track cleanly; flakes copy every
  # tracked file into the store on each evaluation; untracked files break
  # the clean-tree assertion (F2). /home/dalhaka/factory is deliberately
  # NOT in services.proton-backup.paths (that list is explicit, and these
  # clones are transient -- refreshed or discarded per run).
  systemd.tmpfiles.rules = [
    "d /home/dalhaka/factory 0700 dalhaka users -"
    "d /home/dalhaka/factory/base 0700 dalhaka users -"
    "d /home/dalhaka/factory/ws 0700 dalhaka users -"
  ];
}
