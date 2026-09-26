# Concept — the private overlay as a gated phase

**Date:** 2026-09-11
**Status:** typed, not built

A *private overlay* is the brief's "Remote access from outside the LAN"
(`docs/brief.md` §10, at `docs/research-2026-09-10-oauth-router-spike.md` §10),
typed as its own gated phase and deliberately not built here. Phase 10 expands
the surface the host exposes across the WAN; IS14 rewrites the brief's §10 in
place and Answer 20 names "a declared private overlay as its own later gated
phase". This concept fixes the contract of that phase — its technology, its
key handling, what it exposes, what it never exposes, and how the operator's
acceptance drill proves it — so a later task can implement it against a settled
shape. As a concept it builds nothing; every wire, key and check named here is
a promise for a future task, and terms 2 and 6 are load-bearing constraints
that task must not weaken.

The private overlay's contract, in six numbered terms.

1. **Technology (question 4):** WireGuard, declared as
   `networking.wireguard.interfaces.<name>` in Nix. The alternative is a
   coordinated mesh (a central node that relays and routes between peers); it
   is not recommended because its coordinator necessarily sees peer metadata —
   who connects to whom, when, and from where — which the brief's invariant
   "nothing leaves the machine" forbids. WireGuard keeps each peer's
   configuration local and static, with no coordinator in the data path.

2. **Keys outside the store:** the private key lives at
   `privateKeyFile` under `/var/lib/secrets/`, mode `0400 root:root`, and the
   module this phase adds must assert
   `!(lib.hasPrefix "/nix/store" privateKeyFile)` at eval time — a key that
   ever lands in the Nix store is a security failure, not a convenience. Peers'
   public keys are Nix literals in the module, so the only non-Nix secret is
   the single private keyfile on disk. Nothing here trades the brief's
   "nothing leaves the machine" posture for reachability: the key material
   stays local, and the operator creates the keyfile outside any task.

3. **What it exposes:** exactly the `services.lan-access` sites, and only to
   exactly the declared peers. The overlay is a transport for the host's
   existing site set; it adds no new endpoints. Whatever a site authenticates
   internally still authenticates through the overlay — no site bypasses its
   own auth because it arrived over WireGuard.

4. **What it never exposes:** the brokers (`10.100.3.1:3131`,
   `10.100.4.1:3141`), Helm's ports 7700 and 7710 except through a site, SSH
   unless a site explicitly declares it, and any port that no site declares.
   The overlay cannot widen the host's attack surface beyond the site surface;
   the sieve rule is "a port is reachable from outside the LAN if and only if
   a site says so".

5. **Acceptance drill and gate:** from a peer outside the LAN, IS12's
   Interfaces 2–6 succeed exactly the same way they succeed on the LAN; from a
   non-peer, `wg show` shows no handshake. The operator runs the drill from a
   real remote peer and the negative from a machine with no key, then says
   "test passed" — the phase does not land until both halves are demonstrated.

6. **Its future checks, named now:** `overlay-eval`, `overlay-assertion-negative`,
   `overlay-vm` — reserved names, none exists yet. `overlay-eval` evaluates the
   module including term 2's store-path assertion;
   `overlay-assertion-negative` proves that assertion fires when given a store
   path; `overlay-vm` drives the overlay plus the LAN's existing VM host
   checks.

### What this concept does not do

It types a phase and registers itself in the ledger; it builds neither the
module, the checks, the keyfile, nor any `networking.wireguard` stanza. It does
not copy, print or store any credential, and it does not promote agent-authored
code between baskets. Its terms are the shape a future task implements; the
drill in term 5 is the operator's gate, run from a real peer only after that
future task lands the module and the checks — never before, and never in this
phase.