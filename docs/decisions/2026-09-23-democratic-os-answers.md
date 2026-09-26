# 2026-09-23 — the democratic OS: the operator's answers to the packet's seventeen questions

Input: `docs/research-2026-09-23-democratic-os-packet.md`. That packet came from six
web researchers each checked by a skeptic, an internal reader, and six attackers
each checked by a defender: 58 attacks, 57 standing, 2 fatal. The operator
answered on the evening of 2026-09-23. Where an answer went against the packet's
recommendation, this record says so and states the risk once, as it was stated to
the operator.

## The model (the operator's words)

"People can volunteer tokens but cannot decide what they are used for. We will add a
way to gather information, the same way you speced to gather information about me
and the same way you ask me questions we will ask them through helm. It's a
democratic opensource operation system."

## Answers

**Q1. What a donor donates: consumer subscriptions, as specced.** This goes
against the recommendation (a metered API key plus local models).
- **The risk as stated.** Z.ai forbids "bulk or automated usage on behalf of
  others". Google forbids third-party tools except its unmodified CLI. Anthropic
  enforced against subscriptions in third-party harnesses in 2026. OpenAI and
  GitHub are grey (packet §2). The ban risk falls on donors, and the dogfood puts
  it on the operator's own accounts first.

**Q2. Donor consent per assignment: none, as specced.** Donors choose only a
budget. This goes against the recommendation (accept or refuse, plus standing
opt-outs).
- **The risk as stated.** It drops the OS spec's "tasks they accepted" line, the
  only line the tolerating providers leave open.

**Q3. Ask Anthropic and OpenAI in writing** for an open-source permission. Do not
wait for the answer.

**Q4. Build now.** The recommendation was to count donor demand among the named
invitees first; the operator chose to build without that number.

**Safeguard taken: tell donors plainly.** At sign-up the OS shows each
provider's clause and the ban risk, and the donor confirms. Offered and not taken:
excluding the providers that forbid donation in writing, and running the dogfood
on an API key.

**Q5. Donation never buys a vote.** This is an invariant. Donors get a
non-binding survey channel through the Helm.

**Q6. Nobody holds a binding vote in v1.** Answers are advisory. The franchise
later requires sustained work (several substantive landings over 90 days or more),
accountable vouching and a cooling period.

**Q7. Answers rank project-written goals quarterly.** Never contributor-written
plan text. Per-task queue order is not voted.

**Q8/Q9. Neutral ballots, decided by lazy consensus.**
- Contributor ballots carry no "(Recommended)" badge and no default-if-silent. Of
  the operator's own 64 answers, 58 took the recommendation, and 69 of 77 loose
  ends settled by default.
- The project's proposal stands unless a quorum of 3×√N/2 overturns it within 7
  days, followed by a timelock. The ballot is pinned to the plan commit.
- Bridging aggregation (the Community Notes kind) arrives once there are about 30
  voters.

**Q10/Q12/Q16. Identity and privacy.**
- In v1 the operator vouches for each identity, known out of band. An accountable
  invite tree comes later.
- Ballots are secret, with voter verification.
- The project keeps only answers and a withdrawable consent row, aggregated.
  Contributors are never profiled the way the operator model profiles the
  operator.

**Q11. The operator's powers: constitution first.** A short constitution is written
before anything launches. It covers:
- published admission criteria;
- the duty to give a reason for not signing a release;
- a supermajority plus the operator for changes to invariants.

**Q13/Q14. Verification.**
- Tests are pinned to the plan commit.
- TDD is split: a core seat writes the red test, and the donor writes only the
  fix. The research found that about half of unscripted agents tamper with their
  own tests.
- Sensitive task classes are never leased to outside machines.
- An isolated gate with two model vendors reviews every outside result, and a
  cumulative-diff audit runs before each release. No outside result is accepted
  until that gate exists.

**Q15/Q17. The metric, the stop rule and legal footing.**
- The metric counts all operator and orchestrator minutes, plus spend, per landed
  task. The baseline is measured now.
- Onboarding pauses if the metric is not below baseline after 20 outside landings.
- A DCO sign-off check applies now.
- A fiscal host (for example the Software Freedom Conservancy) comes before any
  binding vote.

## The operator's condition for handing over authority

"I'd feel more comfortable giving up the authority once I know the constitution, legal
standing and voting are safe and free from manipulation."

So the constitution hands authority over in stages, and each stage opens only on
evidence the operator accepts. Until then the operator holds final authority, and
the constitution says so openly. No voting system is manipulation-free, so "safe"
is made measurable:

- **Legal standing:** a fiscal host or legal entity is signed, the DCO is enforced,
  and the licence and liability position is reviewed by someone qualified.
- **Voting integrity:**
  - an adversarial audit of the voting system with no fatal finding left open;
  - a live red-team drill in which planted sybils and a coordinated bloc fail to
    swing an advisory round;
  - several advisory rounds run with their integrity measured and published.
- **The constitution itself:** audited like the specs. Amendments need the
  operator's signature while the operator holds authority.

The handover steps are gated on that evidence, and each is reversible if a later
audit fails:

1. Advisory answers are published.
2. Goal ranking becomes binding, with the operator's veto kept.
3. The veto narrows to invariants.
4. Release signing is shared k-of-n.

## Amendment: an immutable core, the rest in tiers

Asked "immutable or mutable?", the operator chose an immutable core with tiers:

1. **The immutable core.** No amendment inside the project can touch it: donation
   never buys a vote; contributors' privacy; the four safety guarantees; GPL
   openness. Changing any of these means a different project, and the GPL's right
   to fork is the valve.
2. **Structure** (authority, the handover gates, membership) changes by a
   supermajority, a long waiting period, and the operator's signature during the
   founding period.
3. **Procedures and numbers** (quorum, windows, ballot mechanics) change by a
   simpler process, always public and never retroactive.

The core invariants are also enforced as build checks, not only as text. For
example, the ledger refuses a vote weighted by donation.

## Against exploiter economics

The operator: "Is there a way to prevent people from, not making a profit but making
a certain amount of profit with what gets built? I want to avoid exploiter
economics."

A profit cap in the code licence is not possible. tvix is GPL-3, and GPL-3 forbids
further restrictions (§7, §10). A field-of-use restriction also leaves the Open
Source Definition. So the operator chose three levers that work within the GPL:

1. **A non-profit asset lock, in the immutable core.** The project never
   distributes surplus, never sells donors' work or data, and donated tokens never
   serve a paying customer.
2. **AGPL-3 for the project's new code.** GPL-3 §13 permits combining with
   AGPL-3. Anyone who runs the OS as a service must share their changes.
3. **A trademark policy.** The name is held by the fiscal host, and commercial use
   of the name is conditioned on reciprocity terms.

A non-open-source licence (copyfarleft or noncommercial) was offered and not taken.
All three levers need legal review at the fiscal-host step.

## The word, and what earns a vote

The operator: "I would prefer they contribute rather than donate. I donating feels
weird." And: "Technical definition if they contribute they can vote. I can't stop
that. It makes me worried."

1. **The word is "contribute".** Running assigned tasks on one's own machine and
   subscription is "contributing compute", and the core invariant reads "compute
   never buys a vote".
2. **Human participation earns the franchise; compute never does.** From Stage 2,
   a binding vote needs:
   - answers the person cast themselves in at least 3 advisory rounds, the first
     and last at least 90 days apart;
   - vouching by two unaffiliated contributors;
   - a registration at least 60 days old.

   How much compute a key contributed, and how many of its leased tasks landed, never
   counts. Binding votes exist only after the operator's evidence gates open, and
   they never reach the immutable core.

## The constitution's fourteen open questions (draft §5), answered

The operator went through them the same evening. Most took the draft's
recommendation; the two marked below did not.

1. **The Stage 3 veto** covers the immutable core, the host invariants, and the
   ballot, tally and roll code.
2. **The founding period** ends at Stage 3.
3. **Vote-buying resistance** is required from Stage 3.
4. **Token counts** are published as aggregates only, never per contributor.
5. **The first-guess numbers** stay as placeholders. The auditors propose values
   before the first drill.
6. **Trustees** are contributors the operator invites. **Judges** come from outside
   the project and are off the operator's payroll.
7. **Fiscal host:** apply to Commonhaus and SPI in parallel, after clearing the
   project's name ("tvix" is upstream's).
8. **Opening a stage.** 0→1 and 1→2 need the operator's signature. 2→3 and 3→4
   open on day 31 once the judges find every row passed, unless the operator names a
   failed row and a judge upholds it.
9. **A fatal ballot-system fix the operator has not signed:** after 30 days, two
   trustees may sign it. *Against the recommendation*, which was to leave the
   affected rounds non-binding. The affected rounds still bind nothing until the
   fix lands.
10. **A second veto of the same goal** in a later quarter needs a judge's
    co-signature. *Against the recommendation*, which was to allow it with logging.
11. **Providers whose terms forbid contributed compute** stay in with disclosure,
    and are revisited with counsel at the fiscal-host step.
12. **Petitions** get a public answer only during the founding period.
13. **The privacy keep-list** is the minimal working list: answers, consent rows,
    keys, sign-offs, eligibility facts, disclosures and removal records. Never a
    profile.
14. **The quorum formula, the timelock and the minimum windows** are Structure
    tier.

## Public evidence

The operator: "I think it's important that we provide all the evidence the people
need to understand the project is serious."

A public evidence page is generated from the ledger, never written by hand. It
shows:

- the pace (landed tasks per week), the change failure rate, lead time and time to
  restore (the DORA-style measures);
- maintainer attention per landed task;
- check health on main;
- the governance stage and the Article 3.2 label;
- links to every audit, packet and decision.

Operator-side data appears only as **weekly aggregates with no personal detail**:
spend per landed task and maintainer minutes per task. There are no transcripts, no
per-session data, and nothing about the operator's personal usage. This is the
operator's answer.

Prerequisite: a public home. The repo has no remote yet, and the Forgejo server
(answered "build now") does not exist.

## What follows

1. The constitution, first (Q11). Nothing launches before it exists.
2. The lease spec is amended from the packet's §5 edits that these answers keep:
   donor disclosure, the verification rules from Q13/Q14, the stop rule and the
   metric. The consent and donation-lane edits are not applied (Q1, Q2).
3. The governance spec: the Helm survey channel, quarterly goal ranking, neutral
   ballots, identity and privacy.
4. Each spec gets the five-lens adversarial audit before its plan.
