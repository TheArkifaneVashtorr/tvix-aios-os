{ config, ... }:

{
  # NVIDIA driver for the RTX 5090. The open kernel module is required on
  # this GPU generation; this also lays the base for local CUDA inference.
  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.graphics.enable = true;
  hardware.nvidia = {
    open = true;
    modesetting.enable = true;
    package = config.boot.kernelPackages.nvidiaPackages.latest;
    nvidiaSettings = true;
  };
}
