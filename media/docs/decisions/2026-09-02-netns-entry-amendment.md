# Decision: unit-level `NetworkNamespacePath` + `--network host` replaces `--network ns:<path>`

**Superseded 2026-09-02** by the nix-native rework (`docs/superpowers/specs/2026-09-02-media-flake-design-rev3.md`, rev 3.1): `comfyui.service` no longer runs a container at all, so there is no podman `--network` flag left to amend — `NetworkNamespacePath` on the unit (this decision's own point) is simply how the service enters the namespace now, unconditionally; the podman-vs-systemd distinction this file records is historical.

**Date:** 2026-09-02. **Status:** amends
`docs/superpowers/specs/2026-09-02-media-flake-design.md` (rev 2.1), which
still reads `--network ns:/run/netns/egress-media` in its architecture
diagram and Module section. This file is the record; the wiring plan
(nixos-agent-env) carries the same paragraph into the spec text itself, per
`docs/superpowers/plans/2026-09-02-media-flake.md`'s Task 4 instruction not
to write outside this repo.

## What the spec said

Rev 2.1 has the ComfyUI container joining the broker's namespace directly
via podman's own `--network ns:/run/netns/egress-media` flag, with the unit
otherwise running in the host's default network namespace like any other
system service.

## Why that doesn't work

`--network ns:<path>` is podman's *rootful* namespace-join mechanism: it
calls `setns(2)` on the target namespace file from inside podman's own
namespace-management code, which needs `CAP_SYS_ADMIN` in the *host's*
user namespace to attach to a namespace it doesn't own. `comfyui.service`
runs rootless (as the unprivileged system user `comfyui` — see
`docs/superpowers/specs/2026-09-02-media-flake-design.md`'s UID-mapping
decision), and rootless podman's whole security model is that it never
holds that capability: it only ever operates inside the *user* namespace
its own `newuidmap`/`newgidmap`-mapped subuid range gives it. A rootless
`podman run --network ns:/run/netns/egress-media` fails outright —
rootless podman cannot join a network namespace it did not create itself
and does not own, root-owned or not.

## The amendment

Move the namespace entry up a layer, from podman's flag to systemd's own
mechanism: the **unit** enters the namespace before podman (or anything
else) ever starts, via `systemd.services.comfyui.serviceConfig.NetworkNamespacePath
= "/run/netns/egress-media"`. systemd performs this `setns(2)` itself, as
part of process setup, using systemd's own (root) privilege — before it
execs into the unprivileged `User=comfyui` the rest of the unit's
`serviceConfig` drops to. By the time `podman` itself runs, it is already
inside the target network namespace; from podman's point of view there is
now only one namespace to worry about — its own process's — so the
container just needs `--network host` (share the invoking process's
already-correct namespace) instead of trying to `setns` into a second one
itself.

Net effect: exactly the isolation the spec's architecture describes (the
container's only network is the broker's namespace, no route out except
through the broker, loopback reachability only via the socket proxy) — the
same set of syscalls happen, just issued by systemd (which has the
privilege) instead of by podman (which, rootless, does not). Nothing about
the security boundary changes: `NetworkNamespacePath` is applied before
`User=` drops privileges, so the unit cannot be tricked into entering some
other namespace by anything the unprivileged `comfyui` user controls, and
the container still never binds a host interface (verified by the
`comfyui-assertion-negative-listen` check and the `comfyui-netns-vm` VM
test named in the design spec's Testing section, which lives in the
wiring plan since it needs the real broker module).

## What changed as a result

- `nixosModules/comfyui.nix`: `systemd.services.comfyui.serviceConfig.NetworkNamespacePath
  = netns` (`netns = "/run/netns/egress-${cfg.brokerInstance}"`); the
  podman `runArgs` use `"--network" "host"`, never `"--network" "ns:…"`.
- `comfyui-fetch-models.service` gets the identical treatment — it is a
  plain (non-containerized) process, so this was always going to be a
  `NetworkNamespacePath` on the unit, but it's worth noting here that this
  amendment makes the container unit and the fetch unit use the *same*
  confinement mechanism rather than two different ones.
- `checks/eval-harness.nix` / `flake.nix`'s `comfyui-eval` check asserts
  both halves directly: `svc.NetworkNamespacePath == "/run/netns/egress-media"`
  and the generated podman argv `has "--network host"` (and does NOT
  contain `ns:`).
- The design spec's own text (rev 2.1) is unchanged by this task — Task 4
  of the plan deliberately keeps that edit out of this repo (this repo does
  not own the spec file) and defers it to the host-wiring plan, which reads
  this file and copies the paragraph in.
