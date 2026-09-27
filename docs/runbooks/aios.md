# tvix-aios — the workspace, the fork input, the lock

The OS's Rust code lives in one Cargo workspace at the repository root
(`Cargo.toml`; members under `pkgs/`, today `pkgs/aiosd`). It builds only from
the publish-gate export — the paths `publish.py export-list` prints — so a
file the gate withholds is not part of the OS, and a red gate stops the build
(spec `docs/superpowers/specs/2026-09-22-tvix-aios-design.md` §2, goal 1).

## Build and test

- `nix build .#aios-workspace` — `cargo build`, `cargo clippy -D warnings`
  and `cargo test` of every member; the binaries land under `result/bin/`.
- `nix build .#checks.x86_64-linux.aios-public-build -L --no-link` — the
  goal-1 check: the workspace above, the lock node's public-fork assertion,
  and the built daemon run against two fixtures.
- `result/bin/aiosd <aios.json>` — exit 0 and one `aiosd: declaration ok …`
  line on stdout; 1 when the file cannot be read; 2 with
  `aiosd: declaration refused: …` on stderr for anything else; 64 for a
  usage error.

## The fork input

`inputs.tvix-aios` in `flake.nix` is the upstream mirror
`github:TheArkifaneVashtorr/tvix-aios`, pinned to one commit, `flake = false`
(the fork has no flake.nix). Its crates (`nix-compat`, `tvix-eval`) are path
dependencies at `tvix/…` in the workspace manifest; the flake links the input
at `./tvix` inside every build's source, so no tracked `tvix` path exists.

A seat cannot reach GitHub, and `nix` resolves a locked input from the store
whenever a tree with the node's `narHash` is already there. To move the pin
from a shell that can read the mirror clone:

1. `nix flake prefetch --json "git+file://$HOME/flakes/tvix-aios?rev=<rev>"` —
   prints `narHash`, `lastModified` and the store path (the clone's `canon`
   is the mirror's).
2. Put `<rev>` in the input's `url`, then write the lock node in place:

   ```
   nix develop -c jq -S --indent 2 '.nodes."tvix-aios" = {"flake": false, "locked": {"lastModified": <lastModified>, "narHash": "<narHash>", "owner": "TheArkifaneVashtorr", "repo": "tvix-aios", "rev": "<rev>", "type": "github"}, "original": {"owner": "TheArkifaneVashtorr", "repo": "tvix-aios", "rev": "<rev>", "type": "github"}} | .nodes.root.inputs."tvix-aios" = "tvix-aios"' flake.lock > flake.lock.new && mv flake.lock.new flake.lock
   ```

3. `nix flake metadata --json | jq '.locks.nodes."tvix-aios".locked'` — the
   node as written; no network is used.
4. Regenerate the lock (below) and run the check.

With network, `nix flake lock --update-input tvix-aios` after the `url`
change writes the same node.

## Cargo.lock

No seat can reach crates.io, so the lock is never produced by a hand `cargo`
run. The flake generates it offline against the fork's own `Cargo.lock`
(every crate the fork pins, fetched by checksum):

```
cp "$(nix build .#aios-lock --print-out-paths --no-link)" Cargo.lock
```

Run it after any change to a `Cargo.toml`, then `git add Cargo.lock`. A crate
the fork's lock does not pin cannot be resolved this way: adding one is a plan
change, because the fork's lock is the registry by design.

## A hand cargo session

`nix develop` carries cargo, rustc, clippy and rustfmt. A hand session needs
the fork at `./tvix`: `nix build .#tvix-aios-src -o tvix`. The link is
gitignored, treefmt's rust formatter excludes it, and the pre-commit hook's
statix and deadnix skip it (statix panics on the fork's own test suite when it
walks that link). `cargo test --offline --workspace` works when the crates
are already in `~/.cargo/registry`; otherwise use the nix build above.

## The VM backend on core

Plan B (spec 2026-09-22-tvix-aios §8 step 4) types the seat guest only once
two facts are measured on `core`'s kernel: that microvm.nix's
cloud-hypervisor backend gives the guest a virtiofs share and a vsock
channel. Nothing that runs as an agent may boot a VM or reach the network,
so the probe is the operator's, from a desktop shell outside every seat.

1. A scratch flake, outside this repository (`~/flakes/microvm-probe`):

   ```nix
   {
     inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
     inputs.microvm.url = "github:astro/microvm.nix";
     inputs.microvm.inputs.nixpkgs.follows = "nixpkgs";
     outputs = { nixpkgs, microvm, ... }: {
       nixosConfigurations.probe = nixpkgs.lib.nixosSystem {
         system = "x86_64-linux";
         modules = [
           microvm.nixosModules.microvm
           {
             networking.hostName = "probe";
             users.users.root.initialPassword = "probe";
             microvm.hypervisor = "cloud-hypervisor";
             microvm.vsock.cid = 42;
             microvm.shares = [ {
               proto = "virtiofs";
               tag = "probe";
               source = "/tmp/microvm-probe-share";
               mountPoint = "/mnt/probe";
             } ];
             environment.systemPackages = [ nixpkgs.legacyPackages.x86_64-linux.socat ];
             system.stateVersion = "25.11";
           }
         ];
       };
       packages.x86_64-linux.probe =
         self.nixosConfigurations.probe.config.microvm.declaredRunner;
     };
   }
   ```

   `mkdir -p /tmp/microvm-probe-share && nix flake lock`, then
   `nix eval .#nixosConfigurations.probe.config.microvm.hypervisor` — it
   prints `"cloud-hypervisor"`. The option names above are microvm.nix's as
   its README spells them on 2026-09-22; a renamed option is a correction to
   this file, never to the claim rows.
2. `nix run .#probe` — the guest boots to a login prompt (`root`/`probe`).
3. In the guest: `findmnt -t virtiofs /mnt/probe` — the expected line names
   `/mnt/probe` with `FSTYPE virtiofs`. That line, pasted, flips
   `microvm-cloud-hypervisor-virtiofs-unmeasured`.
4. In the guest: `socat VSOCK-LISTEN:5000 -`; on the host, cloud-hypervisor's
   vsock is hybrid Unix-socket vsock (Firecracker-style), not AF_VSOCK — dial
   the runner's `notify.vsock` Unix socket instead of `VSOCK-CONNECT`: write
   `CONNECT 5000\n`, read back `OK <n>\n`, then the guest's stream follows
   on the same socket (e.g. `(printf 'CONNECT 5000\n'; sleep 3) | socat -
   UNIX-CONNECT:$RUN_DIR/notify.vsock`, `$RUN_DIR` being the runner's cwd).
   Native `socat - VSOCK-CONNECT:42:5000` fails ENODEV against
   cloud-hypervisor even with `/dev/vhost-vsock` present; keep that native
   dial only for the qemu fallback in step 5, whose vhost-vsock-pci is real
   AF_VSOCK. Either way, the exchange, pasted, flips
   `microvm-cloud-hypervisor-vsock-unmeasured`.
5. If step 3 or 4 fails, change `microvm.hypervisor` to `"qemu"` and repeat:
   the row records which backend passed; the declaration plan B renders is
   the same either way (spec §9).

The rows: `docs/ledger/claims.toml`, `microvm-cloud-hypervisor-virtiofs-unmeasured`
and `microvm-cloud-hypervisor-vsock-unmeasured`; the flip is the
orchestrator's commit on the operator's pasted lines, evidence class
`operator`.

**Measured 2026-09-24**: both rows verified on core, cloud-hypervisor
backend, via `~/flakes/microvm-probe/probe.sh` — the working recipe (a
script, not the inline flake above, which needed fixes to run). Three facts
learned along the way, all load-bearing for the seat-guest design:

(a) The runbook's flake as written above does not evaluate:
`outputs = { nixpkgs, microvm, ... }` uses `self` unbound (`self` must be
named in the `outputs` arguments to reference `self.nixosConfigurations...`
in `packages`).

(b) microvm.nix's `virtiofsd-run` wrapper is a supervisord wrapper whose
conf pins `user=root`, so it fails as a non-root user
("Can't drop privilege as nonroot user") — exactly the case an agent or an
operator desktop shell runs under. Running virtiofsd directly as the user,
with the same flags the wrapper's supervisord.conf would have used plus
`--sandbox=none --inode-file-handles=never` (no root to build the
namespace/mount sandbox virtiofsd otherwise wants), works.

(c) cloud-hypervisor's vsock is hybrid Unix-socket vsock
(Firecracker-style), not AF_VSOCK: the host-side native
`socat - VSOCK-CONNECT:42:5000` fails ENODEV even with `/dev/vhost-vsock`
present. The host instead dials the runner's `notify.vsock` Unix socket,
writes `CONNECT <port>\n`, reads back `OK <n>\n`, and the guest's stream
follows on that same socket. (qemu's vhost-vsock-pci, the step-5 fallback,
remains real AF_VSOCK — the broker's dial recipe differs by backend.)

## Publishing a snapshot to the public mirror **(operator)**

The publish gate (`docs/ledger/publish.toml`, `pkgs/evidence/publish.py`)
is the only thing that leaves this machine: `export` copies exactly the
published paths — publish-classified minus pending — byte for byte with
their mode bits into a directory the public mirror then commits. One
command runs the first three steps of the recipe and prints the fourth:

    nix develop -c tools/publish-snapshot <public-repo>

1. **Export** — `python3 pkgs/evidence/publish.py export
   docs/ledger/publish.toml --tree . --out <fresh dir>`: a red tree writes
   nothing, not even the directory, and a `--out` that exists and is not an
   empty directory is refused, so no partial export can ever lie around.
2. **Commit** — the export becomes the mirror's work tree
   (`git --git-dir=<public-repo>/.git --work-tree=<export> add -A`, then
   commit) with all four git identity variables hard-set to the mirror's
   identity, `TheArkifaneVashtorr <TheArkifaneVashtorr@users.noreply.github.com>`
   — never the ambient git config, so no private name or email can leak
   into the public history; the message never quotes this repo, so no
   private commit id or subject is published either (decision 5).
3. **Prove** — a clean `git clone` of the mirror, then the per-check eval
   `tests/acceptance/ci-eval.sh` there (PL26, the same script CI runs): the
   export is the whole public tree, so it must stand on its own — the script
   prints one named `<check> PASS` or `<check> FAIL` line per check, never
   one `all checks passed!` blob, and its exit code is 0 only when every
   check evaluates (1 names at least one FAIL; 2 means even the check list
   could not be enumerated) (with
   `docs/ledger/publish.toml` withheld, the export's flake drops the
   publish-gate-only checks by design).
4. **Push** — yours alone; `tools/publish-snapshot` stops before this step
   and prints the exact command, because the push needs a credential and
   no credential ever passes through the tool:

       git -C <public-repo> -c credential.helper='!gh auth git-credential' push

Initialising the mirror's history the first time (a fresh `git init` plus
the first snapshot, or a clone of the existing private mirror) is the
operator's too — a one-time setup step outside this recurring recipe.
