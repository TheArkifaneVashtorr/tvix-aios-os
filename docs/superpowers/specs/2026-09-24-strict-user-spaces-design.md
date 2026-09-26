# Strict user spaces: agents in guests, rules at the push, no imperative root — design

**Status:** draft revision 1, 2026-09-24, approved in outline by the operator the
same day, revised against three blind judge verdicts (§15). Operator answers
taken: every human account, the operator's included, loses imperative root,
with a YubiKey break-glass; one spec in three phases, seats first. The origin is
the operator's direction recorded in commit `f759673e`: agents run in VMs built
from the operator's declared user side, without the operator's data; workflow
rules are enforced at git push; users are prevented from tampering with the
system. That commit also holds the guard port (IS23r, IS28, IS29) until this
spec decides it (Q13).

## 1. The premise

Today three different things share one trust domain: the operator's home, the
agents that change the system, and the rules that keep the agents honest.

- A seat runs as a hardened systemd unit inside the operator's home. It can read
  everything there that is not explicitly blocked.
- The repo's workflow rules (plan headings are append-only, the board is derived,
  history is never rewritten) are enforced by a Bash command-line pattern matcher.
  It has a documented bypass.
- The operator's account is in `wheel`, so any process running as the operator
  can become root with one password.

This design separates them into three sides with one owner each, and moves each
rule to the place where it cannot be bypassed:

- **The user side** is the operator's. It is declared once, in Nix.
- **The system side** is the agents'. It changes only through spec → plan →
  seat → gate → signed generation → switch.
- **The operator's data** is everything in `~` that is not declared. It never
  enters an agent's guest.

**The goal metric** is the number of paths by which an agent or a human can
change the running system, the shared history, or the operator's data without
passing a gate, a signature or a logged key touch. The target is zero. The
baseline is the eight paths below; each phase's acceptance (§9) closes the rows
it names.

| # | Path today | Closed by |
|---|---|---|
| P1 | An operator-uid process reaches root with the operator's password (`wheel` sudo, polkit admin) | T1, T5 |
| P2 | A seat writes the operator's checkout and `~/flakes` directly | Phase 1b, Phase 2 |
| P3 | A seat reads `~` minus explicit blocks | Phase 1a |
| P4 | An interpreter write bypasses the guard's plan rule | Phase 2 (R2) |
| P5 | A history rewrite or ref write in the one checkout, with no remote to refuse it | Phase 2 (R1, R5) |
| P6 | Host tools run git in a directory the agent wrote | Phase 1b |
| P7 | A hand-edited `/etc` file or unit file goes unnoticed | T4 |
| P8 | The console: the boot-menu editor gives root with no key | Q12 |

## 2. What exists

Measured on 2026-09-24 (packet facts re-verified at the lines cited; the
security judge's measurements re-run for revision 1):

- **The operator's account** (`hosts/core/default.nix:165-177`) is a normal
  user, uid 1000, in `networkmanager` and `wheel`, with `packages = [ ]`.
  `hosts/core/agent-prereqs.nix:49` adds `kvm`. It is the only normal user in
  the evaluated configuration. `security.sudo.wheelNeedsPassword = true`,
  `users.mutableUsers = true`, `nix.settings.trusted-users = [ "root" ]`, and
  `security.polkit.adminIdentities = [ "unix-group:wheel" ]` (all by
  `nix eval` on `nixosConfigurations.core`). No root password is declared (all
  five root password options evaluate to `null`). Whether one was set by hand
  cannot be measured from a build. `security.sudo.execWheelOnly = false`, so
  `sudo` stays executable after `wheel` is emptied.
- **How nixpkgs applies users** (the pinned nixpkgs, re-read). Under
  `mutableUsers = true`, `update-users-groups.pl` keeps an existing shadow hash:
  a declared `hashedPassword` is applied only when `mutableUsers` is false
  (lines 299-300). Group membership of a declared user is not merged from the
  live `/etc/group` (lines 161-165), so removing `wheel` from the declaration
  does take effect. `users-groups.nix:1101-1139` asserts, when `mutableUsers`
  is false and `allowNoPasswordLogin` is false (today's value), that root or a
  `wheel` user has a password or key.
- **Boot and console.** `boot.loader.systemd-boot.editor = true`, so anyone at
  the console can edit a kernel command line and get a root shell with no
  password and no key. `configurationLimit = null`, so every kept system
  generation stays in the boot menu. No LUKS device is declared
  (`boot.initrd.luks.devices = { }`). `boot.initrd.systemd.emergencyAccess =
  false`.
- **The home is imperative.** No home-manager and no `homeConfigurations`
  exist. `~` has 55 top-level entries (`ls -A ~ | wc -l`). They mix tool state
  and configuration with the operator's documents, and the largest are caches
  and application state (the desktop app's state alone is 13 GB). Claude Code's
  user settings hold only preferences. The hooks live in the repo's
  `.claude/settings.json`.
- **A seat is a hardened unit, not a guest** (`nixosModules/seatLane.nix`).
  It runs as the operator (`User = cfg.operatorUser`, 387). It uses
  `PrivateTmp` and `ProtectSystem = "strict"` (408-409), and `ReadWritePaths`
  on `/var/lib/seat`, the evidence store, the memory directory, and four
  operator-home paths (`~/factory`, `~/nixos-agent-env`, `~/flakes`,
  `~/.local/share/dsh-openrouter`) (417-430). The guard script is mounted
  read-only (438-440). `/var/lib/secrets` and the two systemd control sockets
  are inaccessible (452-456), and `NoNewPrivileges` is set (457). Nothing in
  that list hides `/nix` or the nix daemon socket, so a seat builds through the
  host's daemon. The comment at 443-444 says `/home` is **not** hidden, because
  the seat "edits the operator's clones". A root `seat-spool` starts `seat@`
  from job files the operator owns (560), and polkit gives the operator `YES`
  on `seat@` start, stop and restart (595-610).
- **Host tools run git in seat workspaces.** `factory-integrate:78` fetches
  `task/<KEY>` straight from the workspace. `factory-task` runs `git -C "$ws"`
  twelve times, and `factory-ws:119` sets `core.hooksPath githooks`, so hook
  scripts come from the workspace's own tree.
- **The store holds the whole flake source.** The flake's source copy in
  `/nix/store` contains every tracked file, withheld ones included (measured:
  `keys.toml` and `docs/ledger/`). `/nix/store` is world-readable.
- **Keys never reach a seat.** The seat's broker injects the credential
  (`seatLane.nix:263`, `inject.<host>.valueFile`) from `/var/lib/secrets`
  (`0710 root egress-broker`, line 321), which the seat cannot see.
- **"bubblewrap" is a word, not a mechanism.**
  `services.baskets.agents.<n>.placement` is an enum of `host | microvm |
  bubblewrap` with default `"bubblewrap"` (`nixosModules/basketStore.nix:62-68`).
  `nixosModules/aios.nix:120` renders every seat as `"bubblewrap"`. Nothing in
  `pkgs/` or `tools/` places an agent with bubblewrap. The only bubblewrap in the
  tree is dsh's own internal tool sandbox (`pkgs/dsh-openrouter/default.nix:6,95`).
  `aios.seats.<n>.placement` offers only `unit`, and its description says "`vm`
  is plan B's" (`aios.nix:90-99`). The rendered declaration carries `vms = { }`
  (`aios.nix:33`). The basket invariant assertion (`basketStore.nix:98-104`)
  refuses a `local-only` basket in any agent whose `egress` is not `"none"`.
- **No VM backend is wired.** microvm.nix is not an input (`flake.nix` and
  `flake.lock` have no match). Two claims are open gaps owned by the operator:
  `microvm-cloud-hypervisor-virtiofs-unmeasured` and `-vsock-unmeasured`
  (`docs/ledger/claims.toml:470-486`, review by 2026-10-20). The probe is in
  `docs/runbooks/aios.md`, "The VM backend on core". The fallback is the qemu
  backend with the same declaration (`2026-09-22-tvix-aios-design.md` §9).
- **The guard matches command lines, not writes**
  (`tools/orchestrator-guard.sh`, rules in `docs/runbooks/session.md`). It
  protects plan headings, the ritual override and the host's state
  directories. It refuses history rewrites, `sudo`, `nixos-rebuild` and mutating
  `systemctl`. Concept `2026-09-22e` records one verified bypass,
  `python3 -c "shutil.copyfile(…)"`, which wrote a protected plan path with no
  refusal, and names likely variants (`perl -e`, `ruby -e`, a heredoc into an
  interpreter). No task types a fix yet.
- **The guard port is held.** IS23r (the Rust guard), IS28 (its rules as a
  NixOS option) and IS29 (a generated differential corpus) are `held`
  (`docs/ledger/task-status.toml:705-730`). IS24 (the cutover) depends on all
  three (`docs/superpowers/plans/2026-09-11-isolation.md:2244-2247`). IS25
  depends on IS24.
- **Switching needs `wheel` today.** The switch between the running
  generation's profiles, `helm-switch@<profile>`, is granted to the operator as
  `AUTH_ADMIN_KEEP` in polkit. With `adminIdentities` set to `wheel`, that
  means the operator's own password. The `seat@` and `lane-openrouter@` grants
  are plain `YES` for the operator. The printer-admin rule grants the `wheel`
  group.
- **The YubiKeys.** The operator's two enrolled keys (`keys.toml`) serve basket
  unlock through PIV (`hosts/core/agent-prereqs.nix:46-47`, pcscd for
  age-plugin-yubikey). No FIDO2 credential exists yet. The fleet spec
  (`2026-09-23-fleet-and-forge-design.md` §2) plans one `ed25519-sk` key per
  YubiKey. `security.pam.u2f.enable = false`. Its module defaults are
  `control = "sufficient"`, and each service's `u2f.enable` defaults to the
  global switch (`security/pam.nix:230-233`), so enabling it globally adds a
  touch-sufficient line to every PAM service.
- **The flake has an input outside the repo.** The `gaming` input is a
  `git+file` URL into a clone under the operator's home (`flake.nix`). The
  operator's checkout has no git remote.
- **The tamper concepts** are proposed, not built:
  - `docs/concepts/2026-09-02f-audit-reconcile.md`: cross-log reconciliation,
    which alarms on an agent-only record.
  - `docs/concepts/2026-09-02k-post-switch-activation-audit.md`:
    declared-vs-live units.

## 3. Ownership

**The user side** is one declared module, `users/operator/`. It is split into
two parts:

- **`tools`**: the shell, the CLI tools, and Claude Code's settings and skills.
  Guests import this part.
- **`desktop`**: the session, the GUI apps and their preferences. This part is
  host only.

It is **re-declared, never copied from `~`**. Each setting is written fresh in
Nix from what the operator wants, so no data, token or history file enters the
public tree or a guest through it. A push touching `users/operator/` is refused
unless its commits are signed by one of the operator's keys (§5, rule R4).

**The system side** is everything else in the flake. It changes only through
the factory: spec → plan → seat → gate → signed commit on `main` → signed
generation → switch.

**The operator's data** is everything under `~` that the user side does not
declare. It is never mounted, shared or copied into a guest. No path under
`/home` exists inside any guest.

**The first task (US0)** classifies every top-level entry of `~` as *config*
(to be re-declared in the user side), *data* (never enters a guest), or *cache*
(rebuildable, never shared). The operator confirms the list. Because the list
names the operator's own directories, it is **not tracked**: a `withhold` row
would keep it out of publication but not out of seat clones or the store's
source copy (§2). It is a host-only file outside the repo, at a path the plan
fixes, read by host tests. The tracked ledger carries only its hash and the
operator's signed confirmation.

## 4. Phase 1 — each seat job is a guest

Every seat job runs in a microVM built from the user side's `tools` part plus a
system-side guest module (`nixosModules/seatGuest.nix`). It uses microvm.nix with
cloud-hypervisor, and qemu is the fallback with the same declaration. This is
the seat guest that tvix-aios plan B types: `aios.seats.<n>.placement.vm` names
it, and `aios.nix` renders the seat's real placement instead of the constant
`"bubblewrap"`.

Phase 1 is too large for one plan of about twelve tasks, so it is two
sub-phases, each with its own acceptance (§9).

### Phase 1a — the guest boots, and holds nothing of the host

- microvm.nix as a rev-pinned input; the backend chosen by the probe.
- `seatGuest.nix`, the per-generation guest image, and `aios.nix` rendering the
  declared placement. `basketStore.nix`'s enum change (§12).
- **The store:** only the guest's closure, never the host's whole `/nix/store`.
  A per-generation read-only store image (microvm.nix's store-on-disk or a
  closure-only share) holds the guest system, the user side's `tools` part, the
  devShell, and the flake's pinned inputs at the generation's commit. It never
  holds the flake's own source copy. A per-job writable overlay sits on top
  (Q3). Anything outside that closure is built by the host gate.
- **No network interface** (`microvm.interfaces = [ ]`). No LAN route can exist,
  because no route exists at all.
- **No `/home` and no host socket:** no nix daemon, D-Bus, systemd or Wayland
  socket.
- **No persistent disk.** The guest's writable state dies with the job.
- **The basket assertion is re-expressed** for guests: a guest's `egress` is
  derived from its channels, so a guest with a broker channel is never
  `"none"`, and a `local-only` basket is refused in it. A negative build test
  proves the refusal.

### Phase 1b — the job runs, and nothing the guest writes runs on the host

- **The runner's uid.** The guest runner and its virtiofsd run as a per-seat
  system uid, never as the operator. The per-job parameters (workspace, vsock
  CID, outbox) are runtime arguments to one closure per generation, validated
  by root: each path must be a real directory under `/var/lib/seat/ws/<id>`,
  owned by that uid, reached with no symlink component. CIDs are allocated by
  root from a pool, recorded in a root-written CID → seat → KEY map, and never
  reused while a broker maps them. Whether microvm.nix's virtiofsd runs as
  root by default is measured by the probe, not assumed.
- **The workspace is guest-local.** The host hands the job's base commit in as
  a read-only `git bundle`. The guest clones it onto its own writable overlay.
  Work comes back only as a `git bundle` in the outbox. The host runs
  `git bundle verify`, then fetches into a host-owned repository with
  `-c core.fsmonitor= -c core.hooksPath=/dev/null` and
  `protocol.file.allow=never`. The host never runs git, a hook or a tree script
  in a directory the guest can write. `factory-integrate`, `factory-task` and
  `factory-ws` move their `git -C "$ws"` calls to that host-owned repository.
- **An outbox:** a per-job share, written by the guest, read by one ingester.
  The ingester opens files with `O_NOFOLLOW` and accepts regular files only (no
  symlink, FIFO or hardlink). Each seat has an allowlist of row kinds, which
  never includes `breakglass`, switch or gate kinds. Seat-memory writes are
  quarantined until the gate's verdict. The guest never mounts the evidence
  store or the memory directory itself.
- **One vsock channel**, on which a host-side forwarder connects only to the
  seat's broker listener. The credential stays in the broker, exactly as today.
  Every host `AF_VSOCK` listener checks the peer CID against the root-written
  map, because under qemu's vhost-vsock a guest can reach every host listener.
- **Lifecycle.** `seat@<id>` starts the guest's runner instead of the harness
  process. `KillMode = control-group` still ends everything. One image is built
  per generation, not one per job.
- **The host gate's builds are not guest-contained.** The gate re-runs every
  check on the host, and a fixed-output derivation in agent-authored nix has
  network through the host daemon, off the broker. This is true today. Phase
  1b records it as an inv. 3 gap with a claim row. Closing it (a no-NIC builder
  guest for gate builds) is not in this design (§14).

**Gate.** Phase 1a types its tasks only after the operator's probe closes both
claims. The probe is the runbook's, run from a desktop shell outside every seat.
Until then, US0 and the user-side module (US1) are the only tasks dispatched.

## 5. Phase 2 — the rules move to the push

**The forge on core.** A bare repository, `/var/lib/forge/nixos-agent-env.git`,
is owned by a dedicated system user `forge`. No other account can write it. A
push reaches it only through a socket-activated receive service running as
`forge`: over a Unix socket for host users, and over the vsock forwarder for
guests. Because receive-pack never runs in the pusher's own process, the hook
cannot be skipped by writing refs directly. Core still accepts no inbound
network connection.

**Who may push which ref.** Each ref namespace maps to its peers, and every
other peer is refused:

- host users by `SO_PEERCRED` uid, on an allowlist (the operator, and the
  orchestrator's uid once Phase 3 gives it one);
- guests by CID, looked up in the root-written CID → seat → KEY map. The
  forwarder learns the CID from a per-CID socket path, never from anything the
  guest sends. A seat may push only `task/<its own KEY>`.

Each push's peer (uid or CID), ref and signing key are recorded in the push log.

**The hook's trust roots.** The rule program, the allowed-signers files (the
gate key, the operator's keys) and the generators' reference versions come from
the running generation's closure only, never from the pushed tree. The hook
never executes pushed code as `forge`.

**Seats stop writing the operator's checkout.**

- A seat guest clones from the forge and pushes `task/<KEY>` over vsock. This
  replaces Phase 1b's bundle hand-back; the receive side runs in the forge's
  bare repository, so no guest-written config reaches a host git process.
- The `ReadWritePaths` rows for `~/nixos-agent-env` and `~/flakes` are removed,
  and in Phase 1 guests they never existed.
- The operator's checkout becomes an ordinary clone of the forge.
- `factory-integrate` reads task branches from the forge.

**The gate's key.** R1 below trusts one signing key. Its custodian is Q11. Two
constraints hold for every option: no process running as the operator's uid
can read or use the key, and a commit that changes the host's evaluated
toplevel needs a logged operator touch before it can land on `main`.

**One rule program, `push-rules`,** runs as the pre-receive hook. It is the same
rule set the lease spec's Forgejo hook applies to contributors'
`results/<key-id>/` branches (`2026-09-23-lease-and-verify-design.md` §4-§6), so
our seats and strangers' machines are held to one standard.

- **R1 — refs.** Only a commit signed by the gate's key, carrying a
  `Gate-Target: main` trailer, may become the tip of `main`, and only by
  fast-forward. A gate-signed commit for another target cannot be
  fast-forwarded to `main`. `task/<KEY>` takes its own seat's push, and
  `orch/*` takes the orchestrator's (Q5). Nothing else is writable.
- **R2 — typed plan headings.** In every file under `docs/superpowers/plans/`,
  the old tree's `### ` headings appear unchanged in the new tree, compared as
  a multiset (a duplicated heading cannot lose one copy). New headings may be
  added. A plan file may not be deleted, renamed, or change mode or type (no
  symlink), and neither may the `plans/` directory. This is the guard's plan
  rule, moved from the write to the push.
- **R3 — derived files.** The board and every generated file whose drift `lint`
  already checks must equal its generator's output over the pushed tree. The
  pushed generators run in a throwaway sandbox with no network, as a uid that
  is not `forge`, and the hook compares outputs only. A push that changes a
  generator and its output together is therefore accepted.
- **R4 — the user side.** Every commit touching `users/operator/` is signed by
  one of the operator's registered keys (the FIDO2 `ed25519-sk` keys, one per
  YubiKey).
- **R5 — history.** No non-fast-forward update, no deletion of `main`,
  `staging` or a tag, and no tag rewrite (`receive.denyNonFastForwards`,
  `receive.denyDeletes`, and R1 for tags).
- **R6 — the guard's other protected files.** The ritual override follows R2's
  shape: it is never changed by a push that the gate did not sign.

**The guard.** R2 makes the guard's plan rule redundant at the push, but the
guard's other refusals (`sudo`, `nixos-rebuild`, mutating `systemctl`, the
state directories) cover paths no push rule reaches while the orchestrator runs
on the host as the operator. Whether the guard stays load-bearing, and the port
stays held, until Phase 3 and the `wheel` removal is Q13.

## 6. Phase 3 — the orchestrator in a guest

The orchestrator (Claude Code, and later the desktop app, Q9) runs in a
long-lived guest built from the full user side's `tools` part plus an
orchestrator system module. **Phase 3 needs its own follow-on spec** before a
plan can type it: its persistent volume, the terminal attach and its broker are
not specified here. This section fixes only what that spec must meet:

- the same forge and rules: the orchestrator clones from the forge and pushes
  `orch/*`, under its own uid on the push allowlist;
- a persistent volume of its own for session state; hooks from the repo's
  `.claude/settings.json` as today;
- only the declared evidence streams shared read-only (never the engagement
  rows, which are operator data under inv. 8); rows go out through the outbox,
  as in Phase 1b;
- its network is its own broker over vsock (credential: Q10);
- the host terminal attaches to the guest's terminal over vsock, with OSC and
  DCS sequences filtered on the attach path (no clipboard write from the
  guest). The host's `~` is absent from the guest.

It comes last. The host keeps Claude Code installed until Phase 3's acceptance
has held for seven days.

## 7. Tamper safeguards, for every human account

**Scope.** T1-T5 protect against processes: in-session ones running as the
operator, agents, and remote ones. A person at the console is in scope only as
far as Q12 decides.

**T1 — no imperative root.**

- The operator's account loses `wheel`, and so does every future human account.
  One human account exists today. The declared removal takes effect even under
  `mutableUsers = true` (§2).
- Root is locked. A declared `hashedPassword = "!"` is a no-op on a live host
  under `mutableUsers = true` (§2), so the lock is one logged break-glass step,
  `passwd -l root`, taken in T5's order. T4 then asserts that root's shadow
  field starts with `!`.
- The running state is checked by acceptance, not assumed from the declaration:
  `id <operator>` shows no `wheel`, and `su -` fails.

**T2 — break-glass.** `sudo` stays available to the operator through one rule.
The PAM table is explicit: `pam_u2f` with `control = "required"`, `cue = true`,
and `origin` and `appid` pinned, on the services Q14 names (recommended: `sudo`
and `polkit-1`). Every other service has `u2f.enable = false`, set per service,
so login, the greeter and the screen locker never need a key. A check asserts
the per-service table. The authfile lists a FIDO2 credential on each of the
operator's two enrolled keys, so either key works. The second factor is Q6, and
where the authfile lives is Q7. The break-glass rule sets `timestamp_timeout=0`,
so no use rides an earlier touch.

Every use is logged in two places:

- a `pam_exec` line in the journal, written as root before the session opens,
  so the log does not depend on the evidence store being up;
- a `breakglass` row in a root-owned evidence stream: time, key id, and the
  command taken from sudo's own log (`pam_exec` cannot see it). No seat or
  operator-uid writer may emit that row kind.

A reconcile (T4) matches the two logs. Every use is also published on
constitution Article 8's schedule: a record within 72 hours and a review within
7 days. That applies whether or not the use meets Article 8.1's test for an
emergency. A use that turns out not to be one opens a task to make the normal
path cover that case, so break-glass never becomes a routine path. It stays
harder than the normal path (Article 8.3).

**T3 — normal paths without root.**

- **The switch.** A root unit, `system-switch.service`, takes a commit, never a
  prebuilt toplevel. As a dedicated builder uid it evaluates and builds from
  `git+file:///var/lib/forge/nixos-agent-env.git?rev=<commit>`, verifies the
  commit is on `main` with a gate signature, and requires the permanent
  lockout check (T5) green for that commit. Its `--rollback` form returns only
  to the previous signed generation. It records `(commit, toplevel)` in a
  root-owned evidence stream. Polkit grants the operator `start` on that one
  unit as `AUTH_SELF` (under Q14's recommendation, a password and a touch),
  never `YES` while an agent shares the operator's uid.
- **The `gaming` input** is a `git+file` path outside the forge, so a lock bump
  brings unreviewed code into a root build. It is an inv. 6 gap with a claim
  row until the gaming flake has its own forge repository.
- **`helm-switch@<profile>`** stays `AUTH_ADMIN_KEEP` until Phase 3 moves the
  orchestrator out of the operator's uid. Then it becomes `YES`: it moves only
  between the running signed generation's own specialisations, and
  `AUTH_ADMIN_KEEP` cannot be satisfied once `wheel` has no members.
- **Unchanged:** the `seat@` and lane grants, which are already scoped to the
  operator.
- **Printer administration** loses its `wheel` holder with the `wheel` removal
  and becomes a break-glass act, until a task declares printers.

**T4 — reconcile.** A root-run job under the periodic-jobs home
(`2026-09-23-periodic-jobs-design.md`), run after every switch and nightly,
performs five checks:

- (a) `/run/current-system` is a toplevel recorded by `system-switch` in its
  root-owned stream, and its commit's signature verifies;
- (b) every NixOS-managed `/etc` entry resolves into that toplevel's `etc`, and
  every other file under `/etc` is on a declared allowlist of stateful files;
- (c) the unit files under `/etc/systemd/system` match the toplevel's units
  (concept 02k's declared-vs-live);
- (d) the journal's break-glass lines, the root-owned evidence rows and sudo's
  own log agree (concept 02f's cross-log match, where a record in only one log
  is the alarm). Journal lines match only on trusted fields (`_UID=0`, `_EXE`),
  so a `logger` line cannot stand in for one;
- (e) after T1's lock, root's shadow field starts with `!`, and `wheel` has no
  members.

A finding becomes an evidence row and a red Helm tile. The first version
reports only and never repairs.

**T5 — lockout safety.** The steps sit in §10's order. What each guards:

1. **A rehearsed recovery before the first PAM change.** Before T2's first
   switch, the operator boots the previous generation from the boot menu once,
   confirms `wheel` sudo, and boots back. T2 is the first lockout point, and
   this is its recovery.
2. **Break-glass while `wheel` is still present.** The operator runs one real
   `sudo` with each enrolled key on the live host.
3. **A permanent lockout check**, not a one-off VM test: a flake check boots the
   final configuration with a test credential standing in for the touch (as the
   fleet spec's VM test stands in a test key). The operator has no `wheel`,
   `sudo` without the second factor fails, a second `sudo` within 5 s needs a
   new touch, login needs no key, and `system-switch` works. `system-switch`
   refuses any commit without it green (T3), so a later nixpkgs bump that
   breaks `pam_u2f` cannot be activated.
4. **The restore point.** A generation is tagged (`live-gen<N>-pre-wheel`). Its
   system profile generation link is kept, not only a GC root on the tag,
   because the link is what keeps the boot entry. The runbook forbids collecting
   it, like the gen 28 tag.
5. **A second rehearsal on the restore point.** The operator boots the tagged
   generation from the boot menu, confirms `wheel` sudo works there, and boots
   back.
6. **Root is locked** (T1's break-glass `passwd -l root`).
7. **Removing `wheel` is the last commit of the whole spec.**

## 8. Invariants preserved

| Rule | How it holds |
|---|---|
| Brief inv. 1 (tmpfs baskets) | Unchanged. A basket mounted into a guest arrives over virtiofs from host tmpfs (brief §5.2). The decrypt path itself is not in this design. The `local-only` assertion is re-expressed for guests: a broker channel is egress (§4, Phase 1a). |
| Inv. 2 (no credential in an agent) | Unchanged for seats (the broker injects over vsock). Phase 3 extends it to the orchestrator (Q10). |
| Inv. 3 (one chokepoint) | Strengthened for the seat's own traffic: a guest has no NIC, so vsock to its broker is its only egress. Not closed for the host gate's builds of agent-authored nix (fixed-output fetches), a gap that exists today and is recorded as a claim row (Phase 1b). |
| Inv. 4 (reproducible, no imperative setup) | Strengthened: the user side becomes declared. FIDO2 enrolment is a per-key hand step, like basket enrolment, and its output is declared. The root lock is one logged imperative step, asserted by T4 (e). |
| Inv. 5 (policy is Nix) | Strengthened: push rules and placement are Nix-built, and the hook reads them from the running closure. The rules stop depending on which command an agent types. |
| Inv. 6 (no promotion without review) | Strengthened: R1 means only the gate key lands on `main`, and host-closure changes also need an operator touch (§5). The `gaming` input is a recorded gap (T3). |
| Inv. 7 (publish gate) | This spec carries no private literal. The home-classes list is untracked (§3). |
| Inv. 8 (no model reads undeclared user data) | Made structural for seats: no `/home` in any guest, and a closure-only store, so nothing ever added to the host store reaches a guest. Phase 3 carries it to the orchestrator. Today a seat can read `~` minus explicit blocks. |
| Constitution Art. 2, G1–G4 | G1: the same guest boundary, with the same closure-only store, runs on a contributor's machine. G2: `push-rules` is the lease spec's contributor hook. G3: keys stay in brokers, guests have no route, and the gate key is out of every operator-uid process (Q11). G4: `system-switch` builds and activates only gate-signed commits. The constitution binds nobody until signed (its Article 12), but this design meets it now. |

## 9. Acceptance

- **US0.** The home-classes list covers every top-level entry of `~`, is absent
  from the tracked tree, and the operator's confirmation is a signed ledger row
  carrying its hash.
- **Phase 1a:**
  - From inside a seat guest, every path on the data list is absent. So is
    `/home`, and a read by absolute host path fails.
  - A store path outside the guest's closure (for example the flake's own
    source copy) is absent in the guest.
  - The guest's process list and mounts show no nix daemon, D-Bus or systemd
    socket, and no network interface.
  - The build refuses a `local-only` basket in a guest with a broker channel.
- **Phase 1b:**
  - A request to a LAN address and one to a non-allowlisted internet host both
    fail, while the broker's allowlisted host answers (the tvix-aios §9
    negative arm).
  - A `core.fsmonitor` value and a hook planted in the guest's repository do
    not run on the host: their marker file is absent after the host fetches the
    job's bundle.
  - A symlink, a FIFO and a forbidden row kind (`breakglass`) in the outbox are
    each rejected by the ingester, and a seat-memory write stays quarantined
    until the verdict.
  - The runner and virtiofsd run as the seat's uid, not the operator's, and a
    job file naming a workspace outside `/var/lib/seat/ws/<id>` is refused.
  - Under qemu, a guest cannot connect to a host vsock listener other than its
    broker's.
  - A real plan key runs through a seat guest, passes the gate and lands on
    `main`.
- **Phase 2**, each rule with an accepted and a refused arm, so an always-deny
  `push-rules` fails:
  - R1: a gate-signed fast-forward to `main` with `Gate-Target: main` is
    accepted; a force-push to `main`, a `main` update not signed by the gate
    key, and a gate-signed commit for another target are refused.
  - Peers: a seat's push to its own `task/<KEY>` is accepted; its push to
    another seat's branch, and a push from a host uid off the allowlist, are
    refused.
  - R2: a push adding a new heading and appending under an existing one is
    accepted; a push that rewrites or removes a typed heading is refused,
    including when the file was written by `python3 -c` (the bypass in concept
    2026-09-22e: the local write succeeds, and the push does not), and so are
    a plan file's deletion, rename, or replacement by a symlink.
  - R3: a push whose board equals the generator's output is accepted, and so is
    one that changes a generator and its regenerated output together; a
    hand-edited board is refused.
  - R4: an operator-signed commit touching `users/operator/` is accepted; an
    unsigned one is refused.
  - R5: a fast-forward to a task branch is accepted; a tag deletion or rewrite
    is refused.
  - R6: a gate-signed change to the ritual override is accepted; any other is
    refused.
  - The same accepted and refused pushes hold when `push-rules` runs as a
    Forgejo pre-receive hook in a VM test.
- **Phase 3:** its follow-on spec writes the acceptance. The goal-level arm: a
  full orchestrator session runs from inside the guest (the SessionStart hook,
  a plan section appended, a push to `orch/*` landed, and the Stop ritual), and
  the host's `~` is absent from the guest.
- **Tamper:**
  - `sudo` without the key fails, a second `sudo` within 5 s needs a new touch,
    and `su -` fails.
  - Login, the greeter and the screen locker carry no `pam_u2f` line (the
    per-service check).
  - A logged break-glass works with each enrolled key and yields a matching
    journal line and root-owned evidence row; a `logger` line alone raises the
    reconcile alarm.
  - A hand-edited `/etc` file, and a unit file placed by hand, are both caught
    by the next reconcile.
  - `system-switch` refuses an unsigned commit, a commit whose lockout check is
    not green, and any prebuilt toplevel.
  - Both boot-menu rehearsals (T5.1, T5.5) are recorded as ledger rows.

## 10. Order and first version

The order. T-steps are placed explicitly; each numbered step lands before the
next begins unless it says "in parallel".

1. **US0 and US1**: the home-classes list, and the user side declared, host
   only, with no behaviour change beyond declaration.
2. **T4** (report-only reconcile), in parallel with everything below.
3. **T5.1** (the rehearsed boot-menu rollback), then **T2** (break-glass, the
   explicit PAM table and its check), then **T5.2** (one real `sudo` with each
   key).
4. **Phase 1a**, after the operator's probe closes both claims.
5. **Phase 1b.** The first version lands here.
6. **Phase 2**, including the gate key's custodian (Q11). Phase 2 needs only
   the socket-activated receive service, so it does not wait for Phase 1 if
   the probe fails (§11).
7. **T3**: `system-switch` (it builds from the forge, so it needs Phase 2) and
   the lockout check (**T5.3**) it requires. `helm-switch` keeps
   `AUTH_ADMIN_KEEP`.
8. **Phase 3**, under its follow-on spec. `helm-switch` becomes `YES` when its
   acceptance holds.
9. **The lockout sequence**: T5.4 (restore point and its generation link),
   T5.5 (the second rehearsal), T5.6 (root locked), and T5.7, the **`wheel`
   removal, the last commit of the spec**. The guard port's fate (Q13) is
   settled here under the default.

**The first version** is Phase 1b for one lane: the OpenRouter dsh seat in a
guest, with one real task landed through it. The other seat arms follow once
that task has landed.

## 11. Failure modes and rollback

- **The probe fails on cloud-hypervisor.** Use qemu with the same declaration.
  If both fail, Phase 1 halts, seats stay units, and Phase 2 still proceeds: it
  needs only the socket-activated receive service, not vsock.
- **Guest cost.** Boot time and the memory of many concurrent guests are
  measured on the first ten tasks. The seat cap is re-derived from guest memory,
  never assumed.
- **Building inside the guest is slow** (Q3). Fall back to Q3's default. The
  gate re-runs every check on the host regardless, so the seat's
  `FACTORY-CHECKS` stay evidence, never proof.
- **A `push-rules` bug refuses legitimate pushes.** The rules are a Nix package
  with their own tests, pinned per generation. Recovery is a switch to the
  previous generation, or a logged break-glass.
- **T2's first switch breaks a PAM stack.** The previous boot-menu generation,
  rehearsed in T5.1.
- **A later generation breaks `pam_u2f` after the `wheel` removal.**
  `system-switch` refuses it (the lockout check). If one is activated anyway,
  the boot menu's previous generation.
- **The forge repository is lost.** It is added to the backup paths
  (`services.proton-backup`), and every clone holds the full history.
- **A YubiKey is lost.** The other enrolled key covers it. If both are lost, the
  boot menu's restore-point generation (T5.4) is the last resort. That entry is
  also physical-console root; Q12 decides whether to keep it or move recovery
  to a live USB.
- **Emergency mode with root locked.** `sulogin` refuses a locked root and
  `emergencyAccess` is already false. Recovery is the previous generation, or a
  live USB (no disk encryption today).
- **Reconcile false positives.** The `/etc` allowlist grows only by a reviewed
  commit, and the first version never repairs.
- **Rollback per phase:**
  - Phase 1: set the seat's `placement` back to `unit`.
  - Phase 2: switch back to a generation without the forge. The guard is still
    there as a backstop.
  - Phase 3: the host's Claude Code is kept for seven days.
  - Tamper: boot the tagged generation.

## 12. What this supersedes

- **The guard port, per Q13.** Under the default, IS23r, IS28 and IS29 stay
  `held`, not withdrawn, and the guard's bypasses stay tracked defects, until
  Phase 3's acceptance and the `wheel` removal. Then IS23r and IS28 are
  withdrawn, IS24 (the cutover) and IS25 with them, because nothing remains to
  cut over. The running IS23r seat's output is kept as a reference and is not
  gated or landed. `push-rules`' test corpus is its own Phase 2 task, drawing
  on IS29's design: generated pushes, each expected to be refused or accepted,
  including the verified bypass of concept 2026-09-22e and its named variants.
  Concept 2026-09-22e is answered by neither of its two fixes: enforcement
  moves to the push. These ledger rows are the orchestrator's to write once
  this spec is approved.
- **The `bubblewrap` placement.**
  - `basketStore.nix`'s default `"bubblewrap"` (no implementation) is replaced:
    the enum becomes `host | microvm`, with default `microvm`. The change must
    not relax the `local-only` assertion (Phase 1a).
  - `aios.nix` renders each seat's declared placement.
  - Brief §5.1 tier D ("ad-hoc shells: bubblewrap") is superseded for agents:
    an agent's ad-hoc shell runs in a guest.
  - dsh's own internal tool sandbox is untouched. It belongs to the harness, not
    to placement.
- **CLAUDE.md's rule that the operator switches** becomes: the operator starts
  `system-switch`.

## 13. Open questions

Each has options, a recommendation and a default. The default applies if the
operator does not answer. Questions marked **(before planning)** change a
task's touches or acceptance: the plan's first step records an answer or the
confirmed default for each before its task map, as the fleet-and-forge plan
did.

1. **GPU and the worlds in guests.** Recommendation: no GPU in any guest in this
   spec. The worlds stay host units under their own spec. A task that needs the
   GPU is not guest-placeable, which is derived at plan-check time as the lease
   spec derives "leasable". Default: the same.
2. **Where the forge lives.** Recommendation: a local bare repository on core
   now. `push-rules` runs unchanged as Forgejo's pre-receive hook when the forge
   host of the fleet spec exists, and core's repository then becomes its
   mirror. Default: the same.
3. **Nix in the guest (before planning).** Recommendation: the closure-only
   store image of Phase 1a, plus a guest-local daemon on the per-job writable
   overlay, discarded with the job, and no host daemon socket. A build needing
   anything outside the image fails in the guest and is left to the host gate.
   Checks that need KVM (the NixOS VM tests) run in the gate on the host. The
   first ten tasks are measured, and if the p90 wall time exceeds 1.5× today's,
   the plan revisits. Default: the same.
4. **How the user side is declared (before planning).** Recommendation:
   home-manager as a NixOS module, pinned by rev and following nixpkgs. It is
   the maintained way to declare per-user files such as Claude Code's settings.
   Default: plain NixOS (packages, `/etc`, and tmpfiles links), if the operator
   declines a new input.
5. **The orchestrator's own commits after Phase 2 (before planning).**
   Recommendation: the orchestrator pushes `orch/*`, and a gate-lite
   (`push-rules` plus `lint`) lands it on `main` with the gate key, **only if
   the commit leaves the host's evaluated toplevel unchanged**. A commit that
   changes it goes through the full gate and the operator's touch (§5).
   Default: the same.
6. **Break-glass factors.** Recommendation: a touch plus the operator's
   password, so neither a stolen key nor an unlocked session suffices alone.
   Default: the same.
7. **The `pam_u2f` authfile.** Recommendation: a tracked file with a `withhold`
   row, so the host rebuilds from the flake plus a YubiKey (inv. 4). Default:
   the same.
8. **`mutableUsers` (before planning).** Options: (a) keep `true`: passwords
   stay imperative, the root lock is T1's one logged step, and T4 (e) asserts
   it; (b) `false`: this requires `users.allowNoPasswordLogin = true` (the
   nixpkgs assertion fails otherwise, because no root or `wheel` user will
   have a password), which switches off nixpkgs' own lockout guard, so T5.3's
   check becomes the replacement guard, and the operator's password hash must
   be a declared file (age-encrypted to the YubiKeys, not imperative state).
   Recommendation: (a) for this spec, (b) as its own later task. Default: (a).
9. **The desktop app in a guest.** Recommendation: Phase 3's follow-on spec
   uses Claude Code over a vsock terminal, and the desktop app follows over
   waypipe on vsock as its own task. Default: the same.
10. **The orchestrator's credential (before planning, for Phase 3's spec).**
    Recommendation: behind its own broker, as seats' credentials are. Default:
    held on the guest's own volume, recorded as an inv. 2 gap with a claim row.
11. **Who holds the gate's signing key (before planning).** Options: (a) a
    dedicated system user, `gate-sign`, holds an SSH signing key no other uid
    can read; it signs only a verdict delivered through a root-owned spool,
    and for a commit that changes the host's toplevel it also waits for a
    logged operator touch; (b) the key is on the YubiKeys, and the operator
    touches every landing on `main`; (c) a key readable by the operator's uid,
    as the draft left it, which lets any agent running as the operator sign
    `main` and start `system-switch` (the security judge's blocker).
    Recommendation: (a), which keeps landings unattended and puts a human only
    on changes to the host. Default: (a). Option (c) is not offered as a
    default.
12. **Is physical access to the console in scope?** Options: (a) set
    `systemd-boot.editor = false` now, keep the boot menu's restore point as
    the recovery, and state that a person at the console who picks the restore
    point has root (T1-T5 cover processes, not the console); (b) (a) plus disk
    encryption and a live-USB recovery, dropping the restore point after 30
    days of green break-glass; (c) change nothing, and keep console attackers
    out of scope. Recommendation: (a): one line closes the keyless editor path,
    and recovery keeps working. Default: (a).
13. **Does the guard port's withdrawal wait until Phase 3 (before planning)?**
    Options: (a) IS23r, IS28 and IS29 stay held, and the guard stays
    load-bearing with its bypasses tracked, until Phase 3's acceptance and the
    `wheel` removal; then they are withdrawn; (b) withdraw now for the rules
    the push covers (R2, R3, R5, R6), and keep the guard load-bearing for
    `sudo`, `systemctl` and the state directories; (c) withdraw all now, as the
    draft did. Recommendation: (a): until the orchestrator leaves the
    operator's uid, the guard is the only check on its shell, and holding costs
    nothing. Default: (a).
14. **Which PAM services `pam_u2f` covers (before planning).** Options: (a)
    `sudo` and `polkit-1`, `control = "required"`, every other service off, so
    `system-switch`'s `AUTH_SELF` needs a touch; (b) `sudo` only, so
    `system-switch` needs only the password; (c) the nixpkgs global default
    (touch-sufficient everywhere), which cannot make "`sudo` without the key
    fails" hold. Recommendation: (a). Default: (a).

## 14. Not in this design

- Forgejo, the forge host, and contributor machines (the fleet and lease
  specs).
- Phase 3's design detail: its own follow-on spec (§6).
- GPU passthrough, and isolating the worlds.
- The basket decrypt-to-tmpfs path (brief inv. 1 is specified but not built).
- Secure boot, and disk encryption unless Q12 (b) is chosen. Console access
  beyond Q12.
- A no-NIC builder guest for the host gate's builds (the inv. 3 gap, §4).
- Repairing drift automatically.
- The Rust daemon placing guests. `aiosd` reads the same declaration later.

## 15. Judged

Revision 1. Three blind judges read the draft: facts 6/6 (three minors),
plannability 6/12 (one blocker, four majors), security 5/12 (two blockers,
thirteen majors, a lockout walk). Every security measurement this revision
relies on was re-run first (§2). Dispositions:

| Finding | Disposition |
|---|---|
| Plannability blocker: T1 and T3 unplaced | Fixed: §10 steps 3, 7 and 9 |
| Plannability: Phase 2 refusal-only | Fixed: §9, an accepted arm per rule |
| Plannability: Phase 1 over twelve tasks | Fixed: Phase 1a and 1b (§4) |
| Plannability: open questions change touches | Fixed: §13 marks them "before planning" |
| Plannability: Phase 3 not typeable | Fixed: follow-on spec (§6, §14) |
| Security blocker 1: the gate key's custodian | Operator question Q11, constraints fixed in §5 |
| Security blocker 2: host runs guest-written git | Fixed: bundle hand-back (§4, Phase 1b), acceptance arm |
| Security 3: runner uid, arguments | Fixed: §4, Phase 1b |
| Security 4: whole store shared | Fixed: closure-only store (§4, Phase 1a), acceptance arm |
| Security 5: hook trust roots | Fixed: §5 |
| Security 6: peer-to-ref ACL | Fixed: §5 |
| Security 7: outbox ingest | Fixed: §4, Phase 1b |
| Security 8: gate builds' FOD network | Fixed as a recorded gap (§4, §8, §14) |
| Security 9: PAM scope | Operator question Q14; per-service table and T2 recovery fixed (§7) |
| Security 10: sudo timestamp | Fixed: T2, acceptance |
| Security 11: root lock, Q8 | Fixed: T1 step and T4 (e); Q8 restated |
| Security 12: one-off lockout test | Fixed: permanent check, T5.3 |
| Security 13: console | Operator question Q12; scope stated in §7 |
| Security 14: guard dropped early | Operator question Q13 |
| Security 15: basket assertion | Fixed: §4, Phase 1a |
| Security minors 16-23, fact minors 1-3 | Fixed in place |

## 16. Decided (operator, 2026-09-24)

The four questions the judges raised were answered with their recommendations. Where §13 lists alternatives, these answers win.

- **Q11, the gate's signing key:** held by a dedicated `gate-sign` system user that no agent can read. A commit that changes the host configuration also needs the operator's YubiKey touch. Every other commit lands unattended.
- **Q12, console access:** the systemd-boot editor is switched off now. The boot-menu rollback stays as the recovery path. Full-disk encryption is a separate, later project.
- **Q13, the guard:** it stays load-bearing until Phase 3 and the `wheel` removal. IS23r, IS28 and IS29 stay held until then; they are not withdrawn.
- **Q14, `pam_u2f` scope:** `sudo` and `polkit-1` only, as `required`. Login and screen unlock are unchanged, so a lost key cannot lock the operator out of the session.

The five questions marked "before planning" were answered the same day, each with its recommendation:

- **Q3, Nix in the guest:** the closure-only store image plus a guest-local daemon on the per-job overlay. There is no host daemon socket, and checks that need KVM run in the gate on the host. The first ten tasks are timed, and if the p90 wall time exceeds 1.5× today's, the plan revisits this.
- **Q4, declaring the user side:** home-manager as a NixOS module, pinned by rev and following nixpkgs.
- **Q5, the orchestrator's commits after Phase 2:** it pushes `orch/*`, and a gate-lite (`push-rules` plus `lint`) lands a commit with the gate key only if the host's evaluated toplevel is unchanged. Anything that changes it goes through the full gate plus the operator's touch.
- **Q8, `mutableUsers`:** it stays `true` in this spec. The root lock is T1's one logged step and T4 asserts it. `false`, with a declared, age-encrypted password file, is a later task of its own.
- **Q10, the orchestrator's credential (for Phase 3's follow-on spec):** it sits behind the orchestrator's own broker, the same way seats' credentials do, so invariant 2 stays whole.

With these answered, the spec is ready to plan.
