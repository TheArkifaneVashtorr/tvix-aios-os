_:

# The operator's day-to-day Claude: the desktop app on the host, as the
# operator, unconfined (decision 2026-09-02,
# docs/decisions/2026-09-02-cowork-tier-parked.md). Its Code tab is Claude
# Code with a GUI -- sessions on any folder, builds and sudo in the
# integrated terminal -- and replaces the bare CLI as the primary interface.
# Its Cowork tab is Anthropic's VM-sandboxed task runner (needs kvm +
# vhost_vsock + the OVMF/virtiofsd symlinks the upstream module provides).
# No broker, no netns here: this machine is single-purpose and the tier-A
# bubble (nixosModules/cowork.nix) remains available if that changes.
{
  programs = {
    claude-desktop = {
      enable = true;
      cowork.kvmUsers = [ "dalhaka" ];
    };
    # The app downloads its own generic-Linux Claude Code harness and runs it
    # on the host; NixOS cannot start it without the nix-ld loader shim
    # (field bug 2026-09-02: exit 127 "Could not start dynamically linked
    # executable"). Verified: that binary needs glibc only.
    nix-ld.enable = true;
  };
}
