# Lease and verify: other people's machines run our tasks, safely — design

**Status:** draft, 2026-09-23. Operator answers taken the same evening
(`docs/decisions/2026-09-23-fix-what-wastes-seats.md` §3, and this design's
approval). The first of the distributed-OS specs. Coordination, distribution, the
contributor host and governance follow as their own specs.

## 1. The premise

The operator's test for the OS: it is pointless unless it can route workloads to
other people's machines **safely**, efficiently and quickly, and share the
improvements across every copy. Today one machine does all the work. `core` runs
the task graph, isolated seats (`nixosModules/seatLane.nix`), the gate
(`factory-review`), integration (`factory-integrate`) and the evidence store.
Everything in that chain assumes one host. It uses a netns-and-broker pair per
host, YubiKey-gated baskets, and `~/factory/base/<repo>`.

The OS spec already settles part of the answer
(`docs/superpowers/specs/2026-09-22-tvix-aios-design.md:325-358`). A contributor's
seat runs on their own machine under their own subscription, the project's broker
never sees their credential, and claiming a task is a signed ledger row. What it
does not say is how a task reaches that machine, how the result comes back, and why
the project may trust it. That is this spec.

**Contributors donate tokens, not direction** (the operator, correcting the first
draft the same evening): "People can volunteer tokens but cannot decide what they
are used for. … It's a democratic opensource operation system." A contributor's
machine runs the OS, and its seats spend the contributor's own subscription on
whatever the project assigns. The contributor chooses only how much to give. The
project's direction is set democratically: contributors are asked questions through
the Helm, the way the operator is measured and asked today, and their answers steer
the queue. That channel is the governance spec. This spec only guarantees that a
donated machine runs what it is assigned, and nothing it picks.

**Safety means four guarantees,** each an acceptance row in §8:

- **G1** — the contributor's machine is safe from our tasks.
- **G2** — our code is safe from their results.
- **G3** — secrets never leave.
- **G4** — improvements are reproducible and signed.

**The goal metric** is operator minutes per landed task. Adding machines must push
it down.

## 2. What carries over unchanged

Measured, not assumed:

- **The task unit** is a plan section, `### KEY` with touches, acceptance checks,
  probes and a commit subject (`tools/factory/seat/factory-brief`).
- **The result** is a `task/<KEY>` branch plus the `.result` lines (`FACTORY-RESULT`,
  `FACTORY-CHECKS`). The daemon spec keeps this contract (§5, `:151-204`).
- **Re-verification** works because every acceptance check is a Nix derivation. Core
  can rebuild any result's checks itself (`factory-integrate:6-9`). At p90 that costs
  about 250 s for `unit`, 407 s for `flake-check` and 11 s for `lint` (evidence
  `checks` stream, 3454 rows).
- **Staging** reuses integration's merge-then-check shape: `integ/<run>` and its
  fast-forward.

**What is missing:** signing of any kind (no commit signing, no Nix secret key),
cross-machine matching (the daemon's scheduler is local), and any join between
operator attention and a landed task.

## 3. The coordinator: Forgejo on its own server

The coordinator is a separate small NixOS host, `hosts/forge`, built from this
flake and reachable from the internet. It runs Forgejo (`services.forgejo`, self
hosted, no GitHub) and holds three things: the public repo, a ledger repo, and the
lease rules.

It also runs the lease assigner (§4), which holds the forge's lease-signing key. It
never runs contributor code and never holds a model key. **Core never accepts
an inbound connection:** it talks to the forge outbound only.

Accounts use SSH keys. The same public key that authenticates a push also signs
the contributor's commits and ledger rows (git's SSH signing). A key is registered
in the ledger repo by a commit the operator signs. That registration is the whole
trust list.

## 4. The lease is an assignment

A donated machine never chooses a task. It asks for work: it pushes a signed
request to `requests/<key-id>` in the ledger repo, carrying what it can run (model
families its subscription reaches, task classes, the budget left today). A small
**lease assigner** on the forge host answers it. The assigner takes the next
leasable task in the project's queue order that the request's capabilities meet and
writes `leases/KEY` itself, signed with the forge's lease key. The lease commit
carries:

- the key, and the plan commit the task section is read at;
- the assigned machine's key ID;
- an expiry (the task's timeout plus a margin).

The machine fetches its assignment and runs it. It may decline only for lack of
capability (a check it cannot build, a model it cannot reach), never by preference.
A decline is recorded, and the task goes back to the queue.

A Forgejo pre-receive hook refuses every contributor push to `leases/`, so only the
assigner's key writes there. The assigner writes a lease only when no unexpired
lease exists for `KEY` and the plan commit is on `main`. Git's atomic ref update
makes that check-and-write a lock. An expired lease may be reassigned, and the
reassignment is recorded.

**Queue order is the project's,** the derived queue `tasks.py` computes today. The
governance spec later decides how the contributors' answers feed it. A task is
**leasable** only when its
acceptance checks can run anywhere. The 21 host-bound checks (core's configuration,
KVM, the live system; `docs/research-2026-09-21-tvix-aios-loose-ends.md:552`, item
56) make a task local-only. This is decided at plan-check time as a derived
property of the section, never by the claimant.

## 5. The contributor side

Donation is unattended. The contributor sets a budget (tokens or hours a day) and
nothing else. The OS asks for work while budget remains and runs what it is
assigned. The contributor's machine runs the OS's own seat lane: the same isolation
our seats have, with its own local broker holding the contributor's own
subscription key (G3, and §11 of the OS spec). The brief is built only from the public repo at the leased
plan commit. Any section or file under the publish gate's withhold list
(`docs/ledger/publish.toml`) never enters a brief. The task runs with no credential
of ours and no network access beyond its own broker's allowlist (G1).

The result is a branch, `results/<key-id>/KEY`: the task's signed commits, with the
`.result` lines as a final commit or note. Forgejo's branch rules let a
contributor's key push only under its own `results/<key-id>/` prefix. Nobody but
core's gate key can push `staging` or `main`.

## 6. Verification, on core

Core polls the forge outbound and, for each new result:

1. **Checks provenance.** The commits are signed by the lease holder's registered
   key, and the branch forks from the leased plan commit.
2. **Checks scope.** The diff touches only the section's `touches` (the scope rule
   `factory-integrate` already enforces).
3. **Re-runs every acceptance check from Nix** inside an isolation boundary on core:
   a basket or microVM, never a plain build on the host. Their code is untrusted
   even while we only run its tests (G2). The result's own `FACTORY-CHECKS` line is
   evidence, never proof.
4. **Gates the result** with the same review as today (`factory-review`), including
   red-before-green.
5. **Lands it on `staging`** by core's gate key, as a signed merge, on a pass. A
   failure at any step becomes a verdict on the lease: the rows land in the evidence
   store, and the task returns to the queue.

## 7. Promotion and the release

The operator promotes `staging` by signing a release tag. Every copy of the OS
follows only tags signed by the operator's key. It either rebuilds from source (Nix
makes that reproducible) or substitutes from a binary cache signed with the
project's Nix signing key, which this spec creates (G4). How copies of the OS pick
up releases is the distribution spec's; this spec fixes only that nothing unsigned
is ever a release.

## 8. Acceptance

- **G1.** A leased task on the contributor host cannot read outside its workspace,
  reach any host but its own broker's allowlist, or see a key it did not bring. This
  is the seat lane's existing negative tests, run on the contributor host
  configuration.
- **G2.**
  - A result signed by an unregistered key is refused by core.
  - A result touching files outside `touches` is refused.
  - A result whose `.result` claims a passing check that fails when core re-runs it
    is refused, and the failure is recorded against the lease.
  - A test that tries to read `~` or open a socket during core's re-run is contained
    by the isolation boundary.
- **G3.** A brief built for a lease contains no withheld path and no credential,
  checked by the publish gate over every brief. Core holds no contributor
  credential, and the forge holds no model key.
- **G4.**
  - `staging` and `main` refuse any push not signed by core's gate key.
  - A release tag not signed by the operator is ignored by a test OS copy.
  - A build of a release reproduces bit for bit on a second machine.
- **The lock.** Two requests answered at once: exactly one lease ref exists per
  key afterwards. An expired lease is reassignable, and the reassignment is
  recorded.
- **No choosing.** A contributor push to `leases/` is refused by the forge. A
  machine that fetches a lease and does not run it (other than a recorded capability
  decline) loses the lease at expiry, and the pattern is visible in the evidence
  store. Assignments follow the project's queue order.
- **Leasability.** A section whose acceptance checks include a host-bound check is
  not leasable, and `tasks.py check` says why.
- **The metric.** Each landed task has an operator-minutes figure derived from its
  approval events. Reporting it per week is in the first version, not a later
  addition.
- **The dogfood.** Our own seats on core take at least one real task through the
  full lease path (forge, lease, result branch, verify, staging, promotion) before
  any outside machine is registered.

## 9. First version

Two machines the operator owns: the forge server and core. Core plays both parts,
contributor and verifier, so the protocol is proven end to end before trust is
extended. Outside contributors stay named invitees, admitted after the first
outside task lands (`docs/decisions/2026-09-21-public-repo-answers.md`).

## 10. Not in this design

- How contributors are asked questions through the Helm, how their answers are
  measured and weighed, and how those answers set the queue order the assigner
  follows. That is the governance spec, the democratic half of the OS, and the next
  one. The same goes for the contributor guide and the public ledger's
  `contribution`/`vote` streams.
- Distributing releases to other copies of the OS (the distribution spec).
- Leasing tasks with host-bound checks, and leasing to machines without the OS's
  seat lane.
- The Rust daemon implementing this protocol. The contract here is
  implementation-free, so `aiosd` takes it over unchanged (plan B).
- Payment, reputation or ranking of contributors.
- GitHub or any third-party forge.
