# 2026-09-22 — a public project: subscription seats, a vote, a public ledger

## The operator's words

"So you can remove the rule about nothing leaving the computer. This is now going to be
a public project. The main focus will be providing useful opensource, easy to use nixos
memory safe AI native operating system that comes with several AI native features such
as image, video, audio, text and code generation. The central point of the project is
democratically deciding what we build and users being able to donate token to the
project, this grants permission to run VMs on their hardware as 'contributing' we control
the planning, the distribution of work and the ledger. Reconsider your operating
protocols around this." On what a token is: "The object is to capitalize on subscription
based LLMs. People are building their own OS but contributing the code to the project."

Confirmed reading (operator, same hour): each contributor's seat runs on their own
machine under their own subscription, takes tasks they accept from the public queue, and
the project reviews, merges and credits.

## Where the private posture was encoded (measured 2026-09-22)

brief §1:30 and :46 (self-hosted only, nothing to GitHub); invariant 7 (the publish
gate, kept as the mechanism); `docs/ledger/publish.toml` (58 publish paths, 11 withhold
globs covering the board, plans, reviews, research, every ledger, hosts, keys, `.claude/`);
rules.toml rows R-invariant-publish-gate, R-practice-brief8-no-secrets and the
operator-only guard rows (kept: they govern the live host and secrets, not the roadmap);
the evidence streams `operator` and `engagement` (operator behaviour, stay local); memory
`working-style.md` ("privacy/security outrank everything").

## Decisions

1. Brief §1's self-hosted-only constraint is removed; §2 gains the project paragraph;
   goal 3 is reworded to a contributor's seat on their own machine and subscription.
2. Invariant 7 stands. The publish default flips: plans, reviews, research, decisions
   and the routing/task-status/plan-status/rules ledgers become `publish`; keys, host
   hardware identity, credentials, `.claude/`, the board and the operator streams stay
   withheld. The manifest edit is a typed PG-family task after the goal-1 plan lands.
3. Operator-only stays for the live host, switches, secrets and the invariants' veto. It
   stops being the rule for the roadmap: proposals, a vote by ledger identities with a
   landed contribution, a public decision file. Spec §11.
4. A contributor's seat authenticates with their own login on their own hardware on tasks
   they accepted; no allowance is routed through anyone else's broker. This is the
   provider-terms line and the design line at once.
5. The goal-1 plan in flight (`aios-public-build`) stays valid: its brief §1 amendment
   becomes this removal.

## Risks

- Provider terms on automated use of consumer subscriptions vary and change; the design
  keeps to individual use on the contributor's machine, and the README must say so.
- A public ledger of per-contributor token counts is personal data under some regimes;
  identities are handles, never emails (loose-ends 32a), and a contributor can withdraw
  their rows.
- The vote's electorate is derived from the ledger; a sybil with many small landings
  gains votes. One landed contribution per identity is the floor, not the design.
