# Gaming — what you run

Steam with Proton (including Proton-GE), gamescope, gamemode, MangoHud,
controllers, optional non-Steam launchers and low-latency audio, behind one
module: `nixosModules.default` (`programs.gaming`). Every option that adds a
privilege or opens something inbound defaults off; you turn each on by name.

## Turning it on

On the host that imports this flake (`hosts/core/gaming.nix` on `core`):

```nix
programs.gaming.enable = true;
```

then rebuild:

```
sudo nixos-rebuild switch --flake .#core
```

That alone gives you Steam, Proton-GE, gamescope (installed, not the
gamescope session), gamemode (without the renice wrapper), protontricks and
MangoHud. Nothing is exposed to the network and no capability wrapper is
installed.

## Entering and leaving the profile

`programs.gaming.enable` is turned on in a specialisation profile you enter
by hand, not the base config — `switch-to-configuration test` activates the
profile's units but never *starts* a newly wanted user unit, so right after
entering the profile `gamemoded -s` will not answer yet (drill step 2 warns
rather than fails on this). Run once, right after entering:

```
systemctl --user start gamemoded.service
```

Quit Steam and every game before leaving the profile: leaving removes
`/run/opengl-driver-32`, and a Proton process still holding it open when
that happens is not a state to leave a game or Steam itself in.

## Flipping a switch

Each of these is a separate boolean under `programs.gaming` — set it in
`hosts/core/gaming.nix` and rebuild. They don't depend on each other except
where noted.

| Switch | What it does | Why it's off by default |
|---|---|---|
| `gamescope.capSysNice` | Installs a `cap_sys_nice` wrapper for gamescope | Capability wrapper |
| `gamescope.session.enable` | Steam's gamescope (Big-Picture-style) session | Needs `gamescope.enable` (already on by default) |
| `gamemode.renice` | Lets gamemoded renice game processes | Installs a `CAP_SYS_NICE` wrapper on gamemoded — the upstream nixpkgs default is *on*; this module flips it off unless you ask |
| `controllers.xone` | Xbox wireless dongle/wired driver | Out-of-tree kernel module, blacklists in-tree `xpad` |
| `controllers.xpadneo` | Xbox Bluetooth pads | Out-of-tree kernel module |
| `launchers.heroic` / `.lutris` / `.bottles` | Installs the launcher | Extra attack surface you may not want |
| `firewall.remotePlay` | Opens UDP 27036, TCP 27036, UDP 27031-27035 | Inbound |
| `firewall.localNetworkGameTransfers` | Opens UDP 27036, TCP 27040 | Inbound |
| `firewall.dedicatedServer` | Opens TCP 27015, UDP 27015 | Inbound |
| `lowLatencyAudio.enable` | 256-sample PipeWire quantum | Needs `services.pipewire.enable`; changes system-wide audio latency |

`launchers.heroic` pulls in an Electron build the pinned nixpkgs marks
insecure/EOL; if the rebuild refuses to evaluate, add that Electron version
string to `nixpkgs.config.permittedInsecurePackages` on the host (the
option's own description in `nixosModules/gaming.nix` names it).

If you turn on a switch the module doesn't expect together with another
(for example `gamescope.session.enable` without `gamescope.enable`, or a
Steam port open in `networking.firewall.*` by hand with every
`programs.gaming.firewall.*` switch left off), the **build fails** with a
message naming the mismatch — see `nixosModules/gaming.nix`'s `assertions`.
That's deliberate: the rebuild is the point where a privileged or inbound
change gets caught, not a runtime surprise.

## The gamescope + NVIDIA caveat

Smoke-test gamescope's upscaling before relying on it daily. Driver
versions from 555 onward have reported coredumps when gamescope's
upscaling is combined with explicit sync on NVIDIA
(ValveSoftware/gamescope#1662) — unclear whether that's still live at this
host's driver (570.195.03 at the current pin). `tests/acceptance/gaming.sh`
step 8 is exactly this smoke test; run it (or just `gamescope --
glxgears` — `glxgears` works because the module installs `mesa-demos`)
after any driver or gamescope version bump before trusting gamescope for a
real session, not only once.

## Check it worked

After the rebuild above:

```
command -v steam gamemoded gamescope mangohud
gamemoded -s
ss -ltnu                                                   # loopback listeners from Steam's own client are expected
sudo iptables-save | grep -E '2703[1-6]|27015|27040'       # empty by default
sudo ip6tables-save | grep -E '2703[1-6]|27015|27040'      # empty by default
```

`core` has `iptables-save`/`ip6tables-save` on PATH (nf_tables backend, no
`nft` binary in either profile); where a host has nftables instead, `sudo
nft list ruleset | grep -E '2703[1-6]|27015|27040'` is the equivalent. The
firewall ruleset grep is the guarantee: no Steam port in it with every
`programs.gaming.firewall.*` switch left off. `ss -ltnu` is informational,
not that guarantee — Steam's own client binds loopback sockets (expected),
and its Remote Play / in-home-streaming discovery sockets (TCP+UDP 27036,
UDP 27031-27035, TCP 27015, TCP 27040) bind on *all* interfaces the moment
the client starts, regardless of any `firewall.*` switch, because that's
the client discovering LAN peers, not the firewall admitting anything. A
`ss` diff that only shows those documented discovery ports is expected and
not a break; the firewall ruleset grep above is what actually tells you
whether anything is reachable from outside.

The full drill, including the operator-judged GUI checks (Steam window,
Proton-GE compatibility entry, the gamescope smoke test) is
`tests/acceptance/gaming.sh` — run it from the repo root:

```
cd ~/flakes/gaming && nix develop -c tests/acceptance/gaming.sh
```

## Known limits

- Steam's FHS environment (`buildFHSEnv`) is compatibility, not
  containment — it does not sandbox network, filesystem, or device access
  on its own. See the README's security notes.
- No dedicated gaming user or separate login seat: Steam runs as the
  operator, on the operator's existing session. See the README for why,
  and what stronger separation would look like.
- `steam` and `bottles` are wrapper derivations without a resolvable
  `.version` — that's a nixpkgs eval quirk (a self-updating client / a
  rolling wrapper), not a broken build.
