verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Confining a unit with `serviceConfig` sandboxing directives.

Every directive below is a freeform `serviceConfig` key (not a catalogued
option — `citations` cannot check its name; `systemd-analyze verify` and
`systemd-analyze security <unit>` are the tools that do). All of them are
enforced at process-start/runtime, never at `nix eval`/`nix build` time —
a typo or an over-tight combination only shows up when the unit actually
runs, which is why the vm-tests reference is where you prove a hardened
unit still does its job.

## `ProtectSystem` / `ProtectHome`

`ProtectSystem = "strict"` remounts almost everything read-only
(`/usr`, `/boot`, `/etc`, and — unlike `"full"` — `/`); a service that
needs to write anywhere must be told where with `ReadWritePaths`,
`StateDirectory`, or `RuntimeDirectory`. `ProtectHome = true` makes
`/home`, `/root`, `/run/user` empty and inaccessible (`"read-only"`:
readable; `"tmpfs"`: an empty tmpfs instead of hidden).

**Right:** declare the one path the service needs to write.

```nix module
{ pkgs, ... }:
{
  systemd.services.example = {
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      DynamicUser = true;
      ProtectSystem = "strict";
      StateDirectory = "example";
      ExecStart = "${pkgs.coreutils}/bin/touch /var/lib/example/marker";
    };
  };
}
```

**Wrong:** `ProtectSystem = "strict"` with no writable path declared —
confirmed at this pin with a `runNixOSTest` boot (the unit's own
`journalctl`, not a `nix eval` error):

```text
touch: cannot touch '/var/lib/example-marker': Read-only file system
example.service: Main process exited, code=exited, status=1/FAILURE
example.service: Failed with result 'exit-code'.
```

`systemctl status` on a unit failing this way shows `status=1/FAILURE`
from the *program*, not systemd itself — the sandbox did not refuse to
start the unit, it made one syscall inside it fail.

## `DynamicUser`

Allocates a UID/GID for the unit's lifetime only, with no entry in
`/etc/passwd`. Per `systemd.exec(5)`, it implies (all non-optional; none
of these can be turned back off while `DynamicUser` is on):
`ProtectSystem = "strict"`, `ProtectHome = "read-only"` (not `true` — the
service can still *read* `/home`/`/root`, just not write there),
`RemoveIPC = true`, `NoNewPrivileges = true`, `RestrictSUIDSGID = true`,
and `PrivateTmp = "disconnected"` unless `PrivateTmp` was itself set to
`true` explicitly. Persistent state needs `StateDirectory`/
`RuntimeDirectory` (systemd creates and `chown`s them to the per-start
dynamic UID) — a literal path outside those is inaccessible on the next
start under a different UID even if it was writable on this one.

## `PrivateTmp`, `NoNewPrivileges`

`PrivateTmp = true` gives the unit its own `/tmp` and `/var/tmp`,
invisible to and from every other unit — breaks anything relying on a
well-known `/tmp` path shared with another process. `NoNewPrivileges =
true` blocks `execve` from ever raising privileges (setuid/setgid
binaries, file capabilities) for this process tree — a service that
itself execs a setuid helper (not `sudo` inside a container, an actual
setuid binary) fails with `EPERM` from that exec, not from systemd.

## `CapabilityBoundingSet`

An explicit allowlist of Linux capabilities the unit may ever hold, even
if `User`/`Group` would otherwise grant them (e.g. running as root
without this still cannot exceed the set). `CapabilityBoundingSet = ""`
(nixpkgs' most common value) drops every capability — a program that
then calls a privileged operation sees the same `EPERM` it would from an
unprivileged process, not a systemd-level refusal. Needing one back
(binding a low port without `AmbientCapabilities`, say) is
`CapabilityBoundingSet = [ "CAP_NET_BIND_SERVICE" ]`, not turning the
directive off.

## `RestrictAddressFamilies`, `RestrictNamespaces`

`RestrictAddressFamilies = [ "AF_INET" "AF_INET6" "AF_UNIX" ]` seccomp-
filters the `socket()` syscall to those families only; a call for a
family not listed fails the syscall with `EAFNOSUPPORT` — an ordinary
errno the program's own error path sees and can log (`socket: Address
family not supported by protocol`), not a kill. (`SIGSYS` — a
seccomp-filter default-action process kill, `code=killed,
status=31/SYS` in `systemctl status` — is what an unlisted
`SystemCallFilter=` entry gets instead, unless that directive's own
`SystemCallErrorNumber=` is set to something other than `kill`.) Before
adding a new outbound protocol, add its family here or every `socket()`
call for it fails at that one syscall — sockets already open, or handed
in via socket activation, are unaffected either way. `RestrictNamespaces
= true` blocks every `unshare`/`clone`-with-namespace-flags call — the
program's own `unshare(2)`/`clone(2)` call fails with `EPERM` — for
every namespace type (mount, net, pid, user, …); a unit that itself
creates namespaces (a container runtime, `NetworkNamespacePath` sharing)
needs the specific namespace types it uses listed instead of `true`.

## `DeviceAllow`

Cgroup device-list entries; the default (once any `DeviceAllow` is set)
is deny-all, so listing anything switches the unit to allowlist mode for
every device. Groups: `char-<name>`/`block-<name>` match a udev device
tag, a literal `/dev/foo` matches one node. Some other directives grant
one implicitly — `ProtectClock = true` (**off by default**; it is not
implied by `DynamicUser` or anything else, it must be set explicitly)
adds `char-rtc r` on its own, seen as a comment across many services in
this nixpkgs tree; `DeviceAllow = "char-usb_device rw"` is how a real
service here reaches one physical device class.

## `UMask`, `ReadWritePaths`/`BindReadOnlyPaths`

`UMask` (default `0022`) sets the process's file-creation mask —
`"0077"` for anything creating files another local user should never
read. `ReadWritePaths`/`ReadOnlyPaths` punch a hole in `ProtectSystem`
for specific paths; `BindReadOnlyPaths = [ "/etc/resolv.conf" ]` bind-
mounts one host path in read-only regardless of what else is hidden —
the way a unit under `ProtectSystem = "strict"` still resolves names.

## `NetworkNamespacePath`

Joins the unit to a network namespace that already exists at a
`/run/netns/<name>`-style path (created and pinned by another unit or
`ip netns add`) instead of the host's default namespace — the unit
starts inside it, with only whatever nftables/routes that namespace has.
A rootless tool (a container run as a normal user, a bare `unshare`)
cannot join a **root-owned** namespace this way: `setns(2)` into a
network namespace requires `CAP_SYS_ADMIN` in the user namespace that
owns the *target* namespace, which a non-root caller does not have over
one root created — only a unit itself running with root or the matching
capability can use `NetworkNamespacePath` against a root-owned netns;
podman's own `--network ns:<path>` hits the same wall run rootless.

## `systemd-analyze security`

`systemd-analyze security <unit>` scores a running or installed unit's
hardening against every directive above and lists which are unset —
read it after writing a hardened unit, not instead of testing that the
unit's actual job still works (a service that scores perfectly and
cannot write its own state file has failed, just quietly).

```bash cmd
systemd-analyze security example.service
```

## `SupplementaryGroups` vs `DynamicUser`

`DynamicUser` still honours `SupplementaryGroups` — the dynamic user is
added to each named group for the unit's run — but every group named
must already exist statically (declared under `users.groups`);
`DynamicUser`
allocates the *user*, never a group on the fly to satisfy this list.

## Sources

- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (`systemd.services.*.serviceConfig`)
- `/nix/store/k9cmnypyppj2dza7ak4p924lr3g3wxfn-systemd-257.10-man`
  (`systemd.exec(5)`: `DynamicUser=` implications, `ProtectClock=`
  default, `RestrictAddressFamilies=`/`SystemCallErrorNumber=` behavior)
- upstream `systemd` source, `src/shared/seccomp-util.c`,
  `seccomp_restrict_namespaces` (the `unshare`/`setns` rules are added
  with `SCMP_ACT_ERRNO(EPERM)`, at the systemd v257 tag)
- `nixos/modules/services/misc/atuin.nix` (a full hardening block:
  `CapabilityBoundingSet`, `ProtectSystem`, `RestrictAddressFamilies`,
  `RestrictNamespaces`, `UMask`, …)
- `nixos/modules/services/monitoring/prometheus/exporters/rtl_433.nix`
  (`DeviceAllow = "char-usb_device rw"`)
- `nixos/modules/services/web-apps/cryptpad.nix` (the `ProtectClock` →
  implicit `char-rtc` `DeviceAllow` comment, repeated across this tree)
