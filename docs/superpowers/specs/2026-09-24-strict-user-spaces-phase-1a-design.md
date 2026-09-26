# Strict user spaces, phase 1a: the home classified, the user side declared, a guest that holds nothing — design

**Status:** draft, 2026-09-24, derived from the approved parent spec at HEAD
`acf1c7b1`. Not yet judged.

## 1. Purpose, and the parent it derives from

The parent is `docs/superpowers/specs/2026-09-24-strict-user-spaces-design.md`.
This spec covers three pieces of it, the ones the parent's §10 steps 1 and 4
dispatch first:

- **US0** (parent §3, lines 185-192): every top-level entry of `~` classified
  as config, data or cache, in a list the operator confirms.
- **US1** (parent §3 and §10 step 1): the operator's user side, declared host
  only, with no behaviour change beyond the declaration.
- **Phase 1a** (parent §4, lines 206-225): the seat guest boots and holds
  nothing of the host.

It closes the parent's goal-metric row P3 ("A seat reads `~` minus explicit
blocks", parent line 45) **for the guest artifact**. The live seat keeps
running as a host unit until Phase 1b makes `seat@` start the guest. Until
then, P3 stays open on the running host.

**Decisions that bind this phase** (parent §16, lines 798-801):

- **Q3.** The guest gets a closure-only store image and a guest-local daemon
  on a per-job writable overlay. No host daemon socket reaches it. Checks
  that need KVM run in the host gate.
- **Q4.** home-manager as a NixOS module, pinned by rev, following nixpkgs.
  §2 fact 2 says which nixpkgs that has to be.
- **Q1**, default applied (parent line 664): no GPU in any guest.
- **Q8** (line 803): `mutableUsers` stays `true`. This phase touches no
  password.
- **Q12 does not bind here.** Parent §16 (line 794) switches the boot-menu
  editor off "now", but neither §4's Phase 1a list nor §10's order places it.
  See §7.

**The gate** (parent lines 264-266): Phase 1a's tasks are typed only after
the operator's probe closes the two `microvm-cloud-hypervisor-*-unmeasured`
claims. Until then, US0 and US1 are the only tasks dispatched.

## 2. What exists

Each fact below was re-measured at `acf1c7b1` on 2026-09-24. Commands run in
the devShell with `XDG_CACHE_HOME` set.

1. **The operator's account.** It is declared at `hosts/core/default.nix:166-178`
   with uid 1000 and `extraGroups` `networkmanager` and `wheel`, and at line
   177 with `packages = [ ]`. `hosts/core/agent-prereqs.nix:49` adds `kvm`. It
   is the only normal user:
   `nix eval --json .#nixosConfigurations.core.config.users.users --apply 'u: builtins.length (builtins.filter (n: u.${n}.isNormalUser) (builtins.attrNames u))'`
   → `1`.
2. **The host's nixpkgs is `nixpkgs-host`, not `nixpkgs`.** `mkCore` calls
   `nixpkgs-host.lib.nixosSystem` (`flake.nix:1930-1932`), and core is
   `mkCore` (`flake.nix:2071`). `nixpkgs-host` is pinned at `flake.nix:6`
   (`a5cc6f2c…`). The input named `nixpkgs` is a different rev (`flake.nix:5`,
   locked as node `nixpkgs_4`, from
   `jq '.nodes.root.inputs' flake.lock`).
   `nix eval --raw .#nixosConfigurations.core.config.system.nixos.release`
   → `26.05`. Q4's "following nixpkgs" therefore means following
   `nixpkgs-host`. Following the input literally named `nixpkgs` would build
   the user side against a second package set.
3. **Neither new input exists.**
   `grep -c 'microvm\|home-manager' flake.lock` → `0`, and `flake.nix` has no
   match. No home-manager or microvm.nix source is in the local store
   (`ls -d /nix/store/*home-manager*` is empty, and no `-source` path holds
   `nixos-modules/microvm/options.nix`). Every option name this spec uses from
   either project is therefore **read from the pinned rev by the task that
   adds the input**, never assumed from this text.
4. **The home.** `ls -A ~ | wc -l` → `55` top-level entries. The three mixed
   directories hold `34` (`~/.config`), `27` (`~/.local/share`) and `16`
   (`~/.local/state`) entries, by the same count.
5. **A seat reads `~` today.** `nixosModules/seatLane.nix:387` runs the seat as
   `cfg.operatorUser`. `ReadWritePaths` at line 417 lists four operator-home
   paths. The comment at line 444 says `/home` is not hidden. The
   `InaccessiblePaths` at line 452 cover secrets and control sockets, not
   `~`. Every name US0 lists is already visible to a seat through `ls ~`.
6. **The store holds withheld files.**
   `nix flake metadata --json . | jq -r .path` gives the flake's source copy,
   and `ls <that>/keys.toml` succeeds. `keys.toml` is tracked
   (`git ls-files | grep keys.toml`). `stat -c %a /nix/store` → `1775`, so the
   store is world-readable.
7. **The placement words.** `nixosModules/basketStore.nix:62-68` declares the
   enum `host | microvm | bubblewrap` with default `"bubblewrap"`. Assertion
   A2 (lines 98-104) refuses a `local-only` basket unless `egress == "none"`.
   `nixosModules/aios.nix:120` renders every seat as `"bubblewrap"`, line 92
   describes `vm` as "plan B's", and line 33 renders `vms = { }`. The parent
   §2 missed one consumer: **`lib/mkAgent.nix:5`** defaults
   `placement ? "bubblewrap"`. It is used by `assertion-positive`
   (`flake.nix:2486-2503`), and `grep -rn bubblewrap --include=*.nix` finds
   no other placement use.
8. **Core declares no agent and no `aios`.**
   `nix eval --json .#nixosConfigurations.core.config.services.baskets.agents --apply builtins.attrNames`
   → `[]`, and
   `nix eval --json .#nixosConfigurations.core.options --apply 'o: o ? aios'`
   → `false`. The placement changes below therefore cannot change core's
   toplevel.
9. **The probe gate is open.** `docs/ledger/claims.toml:470` and `:480` hold
   the two claims, with `status = "gap"`, `owner = "operator"` and
   `review_by = 2026-10-20`. The probe is `docs/runbooks/aios.md:72`
   onwards, which also says that nothing running as an agent may boot a VM on
   the host (lines 77-78).
10. **The build sandbox has KVM.** `nix show-config | grep system-features` →
    `benchmark big-parallel kvm nixos-test`.
11. **Nothing is signed today.** `git log -3 --format='%G? %h'` → `N` on
    each commit. Parent §2 (lines 145-152) records that no FIDO2 credential
    exists yet.
12. **One input lives in the operator's home.** `gaming.url` is a `git+file`
    URL into a clone under the operator's home (`flake.nix:23`).

## 3. Design for this phase

### 3.1 US0: the home-classes list

- **The file** is TOML, with one `[[entry]]` per top-level name of `~`. Each
  entry carries `name`, `class` (`config | data | cache | split`) and an
  optional `note`.
  - A `split` entry carries `children`, each classed `config`, `data` or
    `cache`. It is allowed only for the three mixed directories of §2 fact 4
    (O2).
- **Where it lives.** The file lives on the host only, at the path O1 fixes.
  It is **never** tracked and never referenced by any Nix expression, so it
  can reach neither a seat clone nor the store (§2 fact 6). The names it holds
  are already visible to a seat (§2 fact 5). The exposure it guards against is
  publication and the world-readable store, not seats.
- **The checker** is `tools/home-classes` (devShell). It is the only thing
  that reads the file, and it takes the file's path at run time.
  - `check` exits 0 when every entry of `ls -A ~` has a row, when every
    `split` child of `ls -A` in that directory has a row, and when the file's
    sha256 equals the confirmed hash.
  - Otherwise it exits 1 and names the unclassified entry or the hash
    mismatch.
  - A row naming an entry that no longer exists is reported and does not
    fail.
  - The checker prints names only to its own terminal, never to an evidence
    stream.
- **The confirmation** is a row in `docs/ledger/claims.toml`,
  `home-classes-confirmed`, with `class = "operator"` and
  `evidence = "operator:<date> sha256:<hex>"`. The orchestrator writes it on
  the operator's pasted `sha256sum` line. How it is signed is O3.

### 3.2 US1: the user side, declared

- **The input.** `home-manager`, pinned by rev on its `release-26.05` branch,
  with `inputs.nixpkgs.follows = "nixpkgs-host"` (§2 fact 2).
- **Layout.** `users/operator/default.nix` imports two parts, as parent §3
  sets out:
  - `tools.nix`: the shell, the CLI tools, and Claude Code's user
    preferences and skills.
  - `desktop.nix`: host only.
- **`tools.nix` is user-agnostic.** It names no user and no home path. It
  reads only `config.home.*`, so the guest can import it for a user that is
  not the operator (§3.3 b).
- **Host wiring.** Core's module list gains home-manager's NixOS module and
  `home-manager.users.<operator>`, which imports both parts.
  `useGlobalPkgs = true` and `useUserPackages = true` (option names read from
  the pinned rev).
- **Content of the first version.** Parent §3 applies: every setting is
  written fresh in Nix, never copied from `~`. The first version declares the
  CLI tools the guest needs, which are packages already in the host closure,
  so no package version changes. It also declares the Claude Code preferences
  the operator names. A file that a tool rewrites at run time (a settings file
  the tool edits itself) would become a read-only store link. It is declared
  only when the operator accepts that. Otherwise it is listed in the plan as
  left imperative.
- **Clobbering.** The first activation meets files that already exist. The
  policy for them is O4.
- **No lockout, by construction.** A check, `user-side-no-lockout`, evaluates
  core with and without the user-side module. It requires these values to be
  equal:
  - `security.pam.services`, `security.sudo`, `security.polkit.extraConfig`
    and `boot.loader`;
  - the operator's `extraGroups`, `uid` and five password options.

  The home-manager module is allowed to change only `users.users.<operator>.packages`,
  and only under `useUserPackages`.
- **Publication.** `users/*` needs a `publish` row in `docs/ledger/publish.toml`
  and an `owns` row in `docs/ledger/subsystems.toml`, in US1's own commit.

### 3.3 Phase 1a: the seat guest

**(a) The input.** microvm.nix, pinned by rev, with
`inputs.nixpkgs.follows = "nixpkgs-host"`. The hypervisor is whichever backend
the probe's evidence names: cloud-hypervisor, or qemu with the same
declaration (parent §11).

**(b) `nixosModules/seatGuest.nix` and the image.**

- The guest is `nixpkgs-host.lib.nixosSystem` over microvm.nix's guest module,
  `seatGuest.nix`, home-manager's NixOS module, and `users/operator/tools.nix`.
- The tools part is bound to a guest user `seat`, whose home is `/seat`. No
  guest user has a home under `/home`, and the operator's user is not declared
  in the guest.
- The root filesystem is tmpfs, and there is no persistent volume.
- The NIC, share and vsock options are empty: `microvm.interfaces = [ ]`,
  `microvm.shares = [ ]`, and no vsock CID (vsock is Phase 1b's).
- There is no GPU device (Q1).
- The flake exports the runner as `packages.x86_64-linux.seat-guest`. It is
  built per commit, and core's toplevel never references it in this phase.

**(c) The store** (Q3):

- **A read-only store image.** It is microvm.nix's store-on-disk image, never
  a share of the host's `/nix/store`. Its root set is:
  - the guest toplevel, which includes the tools part;
  - the devShell's `inputDerivation`;
  - the source of every pinned input except `self` and `gaming` (O6).
- **The flake's own source copy is never in it.** That rules out `self`
  and any derivation whose `src` is the whole tree.
- **A writable overlay** on top of the image (O5), discarded at power-off.
- **A guest-local `nix-daemon`** over that store, with `substituters = [ ]`
  and `sandbox = true`. A build whose inputs are all in the image succeeds.
  Anything else fails in the guest and is left to the host gate. The host
  daemon's socket never exists in the guest, because no share exists (b).

**(d) Placement.**

- `basketStore.nix`'s enum becomes `host | microvm`, with default `microvm`
  (parent §12). `lib/mkAgent.nix`'s default follows it.
- The `placement` submodule of `aios.seats.<n>` gains `vm = { channels; }`
  beside `unit`. Declaring both is refused.
- `aios.nix:120` passes the declared placement through: `unit` renders as
  `host`, and `vm` renders as `microvm` together with its channels.
- `aios.json`'s schema is unchanged in this phase, and `vms` stays `{ }`. The
  daemon places nothing until Phase 1b.

**(e) The egress assertion, re-expressed for guests** (parent line 222).

- `services.baskets.agents.<n>` gains `channels`, a list over the enum
  `[ "broker" ]` with default `[ ]`.
- An agent is **egress-capable** when `egress != "none"` or `channels != [ ]`.
- A2 refuses a `local-only` basket in any egress-capable agent. A guest that
  has no NIC but has a broker channel is therefore refused, whatever its
  `egress` string says.
- A new assertion, A5, refuses a `broker` channel whose agent's `egress` does
  not name a `broker:<instance>`. The broker instance is the channel's far
  end.

**(f) The checks.**

- **`seat-guest-closure`** runs at build time, with no VM. It reads the
  closure of the store image. It refuses `self.outPath`, the `gaming` input's
  `outPath`, and any store path holding a file byte-equal to a tracked file
  that `publish.toml` withholds.
- **`seat-guest-boot`** is a sandboxed check with
  `requiredSystemFeatures = [ "kvm" ]` (§2 fact 10). It boots the runner. A
  oneshot probe unit writes key=value lines to the serial console and powers
  off. The lines cover:
  - whether `/home` exists;
  - `findmnt -t virtiofs,9p,nfs,fuse` (must be empty);
  - `ip -o link` (only `lo`);
  - whether `/dev/vsock` exists;
  - whether `self`'s store path exists;
  - the nix-daemon socket's owner, which must be the guest's own
    `nix-daemon.socket`;
  - the two offline-build outcomes of §4 A7.

  The check greps the console for every expected line.
- **`guest-egress-negative`** is an evaluation that must fail with A2's
  message.
- **The live run on core.** Agents may not boot a VM on the host (§2 fact 9),
  so the operator runs `nix run .#seat-guest` once from a desktop shell and
  pastes the probe lines. The orchestrator records them as a claim row,
  `seat-guest-boundary-on-core`, with `class = "operator"`.

## 4. Acceptance

Each item has an accepted arm and a refused arm. A check that always passes,
or always fails, fails its item.

- **A1 — US0 coverage.**
  - Accepted: `home-classes check` exits 0 on the confirmed file.
  - Refused: after the operator creates a new top-level entry, the check
    exits 1 and names it. After a byte of the file changes, the check exits 1
    on the hash.
- **A2 — US0 stays out of the tree.**
  - Accepted: the confirmation row carries the sha256 of the confirmed file.
  - Refused: `git ls-files` and the flake's source copy
    (`nix flake metadata --json . | jq -r .path`) do not contain the file,
    and `grep -rn` over tracked `*.nix` finds no reference to its path.
- **A3 — US1 declared.**
  - Accepted:
    `nix eval --json .#nixosConfigurations.core.config.home-manager.users --apply builtins.attrNames`
    returns the operator alone, and `tools.nix` evaluates for the guest user
    `seat` with home `/seat`.
  - Refused: the check `user-side-agnostic` evaluates `tools.nix` with the
    home `/nonexistent`. It fails when any generated file or activation script
    contains `/home/`, and a fixture `tools.nix` holding a literal home path
    turns it red.
- **A4 — US1 cannot lock anyone out.**
  - Accepted: `user-side-no-lockout` is green on core.
  - Refused: a fixture user side that adds `extraGroups = [ "audio" ]` for
    the operator turns it red.
- **A5 — the guest holds nothing of the host.**
  - Accepted: `seat-guest-boot` prints each expected line:
    - `/home` absent;
    - no virtiofs, 9p, nfs or fuse mount;
    - only `lo`;
    - no `/dev/vsock`;
    - the nix-daemon socket owned by the guest.

    Every data-class path of US0 lies under `/home`. With `/home` absent and
    no host filesystem mounted anywhere, every such path is absent, so no
    list has to enter the store.
  - Refused: a fixture guest that declares a user with home `/home/probe`
    turns `seat-guest-boot` red.
- **A6 — a closure-only store.**
  - Accepted: `seat-guest-closure` finds the guest toplevel and the devShell's
    `inputDerivation` in the image.
  - Refused: a fixture image whose root set adds `self` turns it red, and so
    does a fixture adding a copy of `keys.toml`.
- **A7 — a guest-local daemon.**
  - Accepted: in the guest, `nix build --offline` of a `runCommand` over the
    image's nixpkgs-host source succeeds.
  - Refused: a fixed-output fetch fails, and no substituter is contacted.
- **A8 — the egress assertion.**
  - Accepted: `assertion-positive` gains a `microvm` agent with no channels
    and a `local-only` basket, and it still evaluates.
  - Refused: `guest-egress-negative` (the same agent with
    `channels = [ "broker" ]` and `egress = "none"`) fails evaluation with A2's
    message. A5's fixture (a broker channel with `egress = "none"` and no
    `local-only` basket) fails with A5's message.
- **A9 — the placement words.**
  - Accepted: `assertion-positive` builds with `mkAgent`'s new default.
  - Refused: an agent declaring `placement = "bubblewrap"` fails the enum,
    and an `aios` seat declaring both `unit` and `vm` is refused.
- **A10 — on core.**
  - Accepted: the operator's live run prints the same lines as A5, and they
    are recorded as `seat-guest-boundary-on-core`.
  - Refused: A5's `/home` fixture, run the same way, prints `home=present`.

## 5. Failure modes and rollback

**The predicted host closure delta.**

- *Phase 1a changes no host store path.* Core imports neither `aios`, nor
  microvm.nix, nor `seatGuest.nix`, and it declares no basket agent (§2
  fact 8). The enum and the assertions change only evaluation.
  - Measured by: `nix build .#nixosConfigurations.core.config.system.build.toplevel`,
    then `nix store diff-closures /run/current-system ./result`, which should
    print nothing attributable to a 1a commit.
- *US1's delta is home-manager's own paths only:* its generation, its files
  and activation script, the `home-manager-<operator>.service` unit, and the
  per-user profile. No package line should show a version change, because
  the declared tools are already in the closure. The plan's operator step
  runs the same `diff-closures`. Any line outside home-manager's names is a
  red result, and the switch waits.

**No switch-time lockout in this phase.** No PAM, sudo, polkit, group, password
or boot-loader value changes, and A4 asserts it at build time. The worst
switch-time outcome is a failed `home-manager-<operator>.service`, which leaves
the login, the session and `wheel` sudo as they were.

**Failure modes:**

- **Activation refuses to clobber an existing file.** The unit fails and the
  file is untouched. Under O4's recommendation it is renamed aside instead.
  Rollback: the previous generation, or US1's revert commit.
- **A tool cannot write its read-only settings link.** The file goes back to
  imperative, a one-line revert of its declaration (§3.2).
- **The probe fails on both backends.** Phase 1a halts. US0 and US1 stand, and
  seats stay units (parent §11).
- **`seat-guest-boot` cannot start a hypervisor in the sandbox.** Fall back to
  O7's default, the operator-run probe. A5's refused arm then runs the same
  way.
- **The image is large, because nixpkgs-host's source and the devShell sit in
  one image.** Its size is measured and recorded in the plan's first
  `seat-guest` build. It is one image per commit, collected like any other
  output, and never `-d` (the gen 28 rule).
- **An option name differs at the pinned rev.** The task adding the input
  records the real names, and this spec's names are corrected by a follow-up
  commit, never assumed (§2 fact 3).
- **The guest-local daemon is too slow.** That is measured on Phase 1b's first
  ten tasks against Q3's 1.5× threshold. No task runs in a guest in this
  phase.

**Rollback per piece:**

- US0: delete the host file and supersede the claim row.
- US1: revert its commit, then switch.
- Phase 1a: revert. Nothing live depends on it.

## 6. Open questions

Each question has a recommendation and a default. The default applies if the
operator does not answer. Q1, Q3, Q4 and Q8 are decided (§1) and are not
reopened.

- **O1 — where the list lives.**
  - Recommendation: `$XDG_STATE_HOME/user-spaces/home-classes.toml`, mode
    0600, owned by the operator. The names are already visible to seats
    (§2 fact 5), and a root-owned path would need `sudo` to confirm.
  - Default: the same.
- **O2 — granularity.**
  - Recommendation: top level, plus `split` rows for the three mixed
    directories (34, 27 and 16 entries).
  - Default: top level only, with each mixed directory classed `data`, the
    class that never enters a guest.
- **O3 — "signed" confirmation.** Nothing can sign today (§2 fact 11).
  - Recommendation: record the operator row now, plus a gap claim
    `home-classes-confirmation-unsigned` (owner: the operator). The claim is
    closed by a signature from the FIDO2 `ed25519-sk` key once the fleet spec
    enrols it.
  - Default: the same.
- **O4 — clobber policy.**
  - Recommendation: set `home-manager.backupFileExtension` to one fixed
    suffix, so the first activation keeps each replaced file beside it, and
    have the checker's `check` verb report those backups.
  - Default: no suffix. Activation then fails closed on any existing file,
    and the operator moves each one by hand.
- **O5 — what backs the writable overlay.**
  - Recommendation: tmpfs in guest RAM, sized with the guest. Its memory cost
    feeds Phase 1b's seat-cap derivation (parent §11).
  - Default: the same.
- **O6 — which pinned inputs enter the image.**
  - Recommendation: every input except `self` and `gaming`, which is a
    `git+file` clone in the operator's home (§2 fact 12) and is not needed by
    the devShell.
  - Default: the same.
- **O7 — where the boot check runs.**
  - Recommendation: the sandboxed `kvm` check of §3.3 f.
  - Default: an operator-run script that uses the same probe unit, if the
    first sandboxed boot cannot start the chosen hypervisor.

## 7. Not in this phase

These are later plans, each in the parent:

- **Phase 1b** (parent §4, lines 227-262): the job running in the guest, the
  bundle hand-back, the outbox and its ingester, the vsock broker channel, the
  per-seat runner uid, and `seat@` starting the guest. Also P3's closure on
  the live host.
- **Phase 2** (§5): the forge, `push-rules` R1-R6, and the gate key's custodian.
- **Phase 3** (§6): the orchestrator in a guest, under its own follow-on spec.
- **T1, T3, T4, T5** (§7): the `wheel` removal and root lock, `system-switch`,
  reconcile, and the lockout sequence. **T2** (break-glass) also stays in the
  parent's §10 step 3.
- **Q12's editor switch-off** (§16): decided but not placed by the parent's
  §10. It belongs in its own one-line task, outside this plan.
- **Moving the operator's packages** from the system closure to the user side,
  and declaring the desktop part beyond what exists today.
