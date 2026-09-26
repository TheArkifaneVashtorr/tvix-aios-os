# The tvix-aios constitution — design

**Status:** draft, 2026-09-23 — the operator's answers to all fourteen open questions
applied (section 5). Revised the same day after an adversarial audit (six
attackers, each checked by a defender; the record is
`docs/research-2026-09-23-constitution-audit.md`). Written on the operator's answer
Q11, "constitution first" (`docs/decisions/2026-09-23-democratic-os-answers.md:71-75`,
`:163`). Nothing in it binds anyone until it is signed (Article 12). Every clause
says what enforces it: a build check, a signature, or a published record. Where
nothing does yet, the clause says it is a promise. None of the build checks it names
exists today (no identity, vote, contribution, forge or assigner code exists, packet
`docs/research-2026-09-23-democratic-os-packet.md:102-105`); each is marked "to be
built".

Inputs: the answers file above; the packet (58 attacks, 57 standing); the lease spec
`docs/superpowers/specs/2026-09-23-lease-and-verify-design.md`; the OS spec §11
`docs/superpowers/specs/2026-09-22-tvix-aios-design.md:325-358`; the public-repo
answers `docs/decisions/2026-09-21-public-repo-answers.md`; five web research reports
(charters, handover, legal, voting, failure), each checked by a skeptic on 2026-09-23;
and the audit above.

## 1. Why a constitution first

The operator's condition, 2026-09-23 (answers `:97-98`):

> "I'd feel more comfortable giving up the authority once I know the constitution,
> legal standing and voting are safe and free from manipulation."

Today one person runs the project. The operator admits every contributor, holds
every task, signs every release, and can change any rule (packet CAP-3, `:145`).

Governance crises come from **gaps the text left unwritten**, not from a wrong
threshold. Rust's moderation team resigned in November 2021 because no document said
who could hold the Core Team to account
(https://www.theregister.com/2021/11/23/rust_moderation_team_quits/, fetched
2026-09-23). Arbitrum's foundation sold 10M ARB *before* the vote meant to authorise
it, then called the vote a "ratification"
(https://www.coindesk.com/business/2023/04/02/contentious-arbitrum-vote-over-1b-in-tokens-ratification-not-request-says-foundation,
fetched 2026-09-23). a16z's "progressive decentralization" never defines
"sufficient", so its stages can be put off forever
(https://a16zcrypto.com/posts/article/progressive-decentralization-crypto-product-management/,
fetched 2026-09-23). So this text writes down who answers to whom, what opens and
reverses each stage, who takes over if the operator is gone, and what can never
change.

## 2. The constitution

Only §2, §4 and Annex A are the constitution (Article 12.1). §1, §3 and §5 explain
it and bind nothing.

### Article 1. Purpose and scope

1. tvix-aios is a free, open-source operating system, built in public by its
   contributors and the AI seats they run. Code taken from upstream keeps its licence
   (tvix: GPL-3.0). New code the project writes is AGPL-3.0, which GPL-3.0 §13
   allows in combination.
2. This constitution governs the project: its code, plans, ledger, releases, and the
   name "tvix-aios" once a legal holder exists (Article 9).
3. It does not govern anyone's own machine or own fork. Anyone may fork under the
   licence. That right is the final remedy for any disagreement.
4. Words used here:
   - **Operator:** the project's founder.
   - **Contributor:** a person with a key registered in the ledger.
   - **Contributing compute:** running tasks the project assigns on one's own machine
     and one's own AI subscription. (The operator's word is "contribute", not
     "donate".)
   - **Helm:** the OS dashboard where questions are asked.
   - **Ledger:** the project's public record, a git repository of signed rows. It is
     mirrored within 24 hours to at least two hosts in different hands, at least one
     outside the operator's control. Any copy whose signature chain verifies is
     valid. Where copies differ, the longest verifying chain wins.
   - **Judge:** an auditor, red-team member, gate judge or dispute reviewer (6.8).
   - **Trustee:** a person named under 8.4.
   - **N:** the number of keys on a ballot's roll (4.3).
   - **Q (quorum):** 3×√N/2, rounded up, never more than N.
   - **K (petition size):** min(√N/2, 5), rounded up, and never less than 3.
5. This constitution governs over every spec, plan and check in the project. A clause
   elsewhere that contradicts it is a defect to fix.

*Enforced by:* the licence files and a per-path licence manifest in every release;
the ledger mirrors; check `constitution-refs`, to be built, which lists every
contradicting clause elsewhere.

### Article 2. The core no one can amend

1. **Compute never buys a vote.** No vote, ballot weight, rank or right comes from
   compute contributed: tokens, money, hardware, or tasks run under a compute lease,
   however many. Eligibility to vote (4.5) comes only from a person's own sustained
   participation.
2. **Contributors' privacy.** Every eligible ballot counts once, whatever the voter's
   activity. Eligibility rules in Article 4 are not weighting. The project keeps
   only: answers, withdrawable consent rows, registered keys, provenance records
   (signed commits and sign-offs), the eligibility facts Article 4 names,
   affiliation and conflict disclosures, and removal records. It never profiles a
   contributor.
3. **The four safety guarantees.** G1: a contributor's machine is safe from the
   project's tasks. G2: the project's code is safe from contributors' results. G3:
   secrets never leave. G4: releases are reproducible and signed.
4. **Openness.** Everything the project writes is free software under GPL-3.0 or
   AGPL-3.0. No clause, deal or host agreement may close any part of it. Third-party
   parts keep their own licences and are listed in each release's licence manifest.
   A non-free part is named as non-free and is never needed to boot or build the
   core OS.
5. **Asset lock.** The project never distributes surplus, never sells contributors' work
   or data, and contributed tokens never serve a paying customer.
6. No amendment, emergency or vote may change this article. Changing it means a
   different project. The right to fork is the way out.

*Enforced by:* build checks. The ledger refuses a vote row that carries a compute
field or weight. A release is refused unless G1–G4's acceptance rows are green (lease
spec §8), and unless every path in its closure is in the licence manifest. The
contributor schema refuses fields outside the list in 2.2. Check
`constitution-core`, to be built. Until it is green, this article is a promise
backed only by a signature.

### Article 3. Who holds authority now

1. During the **founding period** the operator holds final authority. That covers
   admission, the queue, the plans, the invariants' veto, and release signing. It
   has one exception, which the operator chose (answer §5.8): the 2→3 and 3→4
   stages may open on day 31 without the operator's signature, under 6.4.
2. **The label is derived, not written.** The README, the Helm home, every release
   note and the contributor sign-up screen print, from the ledger: the current stage, the
   date the founding period began, the days since the last stage opened, the vetoes
   used this year, the refusals under 6.4, and the gate rows still unmet. At Stages 0
   and 1 the project calls itself "a benevolent dictator with advisory votes". It
   never calls itself democratic, community-governed or member-run before Stage 2.
3. The founding period ends when Stage 3 opens (Article 6).
4. With that authority come duties:
   1. **Reasons for not signing.** Every signed staging head that passes its gates is
      a release candidate. If it is not tagged within 14 days, the operator publishes
      a reason in the ledger.
   2. **Published admission criteria.** Admission follows written criteria kept in
      the repo. A refusal names the criterion it rests on.
   3. **Conflicts disclosed.** The operator records any interest in a decision (an
      employer, a provider, money) in a public conflicts register before acting. A
      decision with a disclosed conflict is valid only if one of three holds. (a) A
      person without the conflict approves it. (b) An advisory round with quorum met
      supports it. (c) The dispute reviewer finds in writing that it is fair on its
      merits.
   4. **Restraint.** The operator uses these powers as little as possible and
      prefers the written process.
   5. **No acting before the vote.** The project carries out no part of any matter
      that a published ballot, petition or amendment concerns until its window and
      timelock end.
   6. **Gate work keeps moving.** Work a gate needs is a standing queue class. Each
      quarter the project publishes a gate-progress report, derived from the ledger,
      never typed. For every unmet gate row it gives the last commit, letter or
      signature that moved it, and who holds it. A row with no progress for two
      quarters needs a published reason. Three quarters with no progress on any row
      calls a no-confidence ballot (10.5) by itself, once the Helm channel exists. If
      the operator has not applied to a fiscal host within two quarters of signing,
      the trustees may file the applications.
5. The operator never audits or judges their own authority. Every audit, drill and
   gate judgement is done by judges under 6.8.

*Enforced by:* ledger rows (`release-decision`, `admission`, `conflict`), each
signed. Checks to be built: a signed staging head older than 14 days with neither a
tag nor a reason row fails; `governance-label` fails a release or Helm build whose
public text does not print the derived label, or calls the project democratic,
community-governed or member-run below Stage 2. 3.4.4 is a promise.

### Article 4. Membership and identity

1. A contributor is one person with one key. The operator's signature registers the
   key in the ledger (lease spec `:75-78`). Each registration is published with its
   date and its voucher, and anyone may object within 7 days.
2. In the founding period the operator vouches only for people known out of band.
   The operator keeps the evidence behind a vouch only until the registration is
   signed, and then keeps only who vouched and when. An accountable invite tree may
   replace vouching by amendment. If it does: each contributor invites at most 3
   people a year; no subtree below one first-generation vouch exceeds 10% of the
   binding roll; an inviter two of whose invitees are removed for cause loses the
   right to invite.
3. **The roll.** A key votes in a ballot, and counts in N, only if it was registered
   at least 30 days before the ballot was published. The roll's hash is printed on
   the ballot. Quarterly ballots open on dates published a year ahead, never between
   20 December and 6 January.
4. A key leaves the roll after 6 months with no landed work, no ballot cast and no
   signed roll confirmation (one click on the Helm). No key leaves in the 60 days
   before a published ballot date. A key rejoins on request.
5. **The binding franchise** (from Stage 2) comes from human participation, never
   from compute (2.1). It needs all of:
   - answers, cast by the person themselves, in at least 3 advisory rounds, the
     first and last at least 90 days apart and one within the last 12 months;
   - vouching by two contributors who are not affiliated with each other or with the
     person;
   - a registration at least 60 days old.

   How much compute a key contributed, and how many of its leased tasks landed,
   never counts toward any of these.
6. **Affiliation.** Every contributor discloses affiliations. Affiliated means taking
   a substantial part of one's income from the employer or funder, directly or
   through an intermediary, in the last 12 months. A false or missing disclosure is
   cause for removal (10.4). People affiliated with one employer or funder may make
   up at most 10% of the binding roll; anyone over that waits, in order of
   registration. Any body this constitution creates seats at most one member per
   employer or funder while it has 5 seats or fewer, and at most a quarter above
   that. The cap counts across all offices together.

*Enforced by:* the signed registration commit; the roll hash on each ballot; the
roll and the franchise computed by `evidence` from the ledger, never typed; the
criteria file in the repo.

### Article 5. The advisory channel

1. The project asks contributors questions through the Helm. Every answer is advisory
   until Stage 2 opens.
2. **What is asked.** Each quarter, contributors rank goals. In the founding period
   the operator writes them. After it, a goals panel writes them: 5 people drawn by
   lot each quarter from the binding roll, under the 4.6 cap, no one two quarters in
   a row. Contributors never vote on plan text or on per-task queue order. Each
   option is one goal. The option texts are published 7 days before the ballot
   opens. In that time the dispute reviewer may split an option that bundles two
   goals, or merge two options that differ only in wording.
3. **Neutral ballots.** No option carries a "Recommended" badge. Nothing is
   pre-selected. Options appear in random order, each with its author named. An
   unanswered ballot counts for nothing. Every ballot offers "none of these; send it
   back". The status quo in 5.4 is a rule about outcomes, not an option on the
   ballot.
4. **Lazy consensus.** The proposed ranking stands unless it is overturned. A ballot
   rejects the proposal if it ranks a different goal first, or ranks "none of these"
   first. The proposal is overturned only if at least **Q** ballots reject it and
   they outnumber the ballots that keep it. Voting stays open at least **7 days**,
   always spanning a weekend. Running turnout is hidden until the window closes.
   Every result then waits 7 more days before it takes effect (the **timelock**).
5. **Counting.** While the roll is under 30 keys, rankings are counted by the
   Schulze method (Debian constitution, Appendix A), with "none of these" ranked like
   any option. An overturned proposal is replaced by the Schulze order. If "none of
   these" wins, the previous quarter's ranking stays in force, and the goals may be
   reissued once that quarter as a new ballot with a new roll. From 30 keys, a
   bridging method adopted under Article 7 takes over (answers `:60-61`).
6. **Pinned ballots.** Each ballot names one plan commit by its hash. What is voted
   on is that commit's text, not a summary. A result is void if the commit carried
   out differs from the commit on the ballot.
7. **Secret, verifiable ballots.** No one, the operator included, can see who voted
   for what, or whether a given contributor voted at all. Ballots are never signed
   with a contributor's ledger key and carry no time finer than the window. Anyone
   can recompute the tally from the published ballots. Each voter can confirm their
   own ballot was counted.
8. **Honest scope.** The ballot tool states in writing what stakes it is fit for.
   Until it resists vote-buying (a voter cannot prove how they voted to someone
   else), it is used only for advisory rounds and Stage-2 rounds under the veto. A
   round run while a fatal finding against the ballot code is open binds nothing.
9. **Minimal data.** Only answers and consent rows are kept, and only answers are
   published, in aggregate. Engagement, timing and device data are not kept.
10. **Petitions.** Any K contributors may jointly ask the project to put a question
    to a ballot. The project answers in public within 14 days. A petition never puts
    its own goal on a ballot; goals are written only under 5.2.
11. Each round publishes an **integrity scorecard**: roll size; turnout as a share of
    N; whether Q was met, and by what margin; the fewest ballots that would have
    changed the result; how many voters confirmed their ballot, out of how many
    voted; how many identities were flagged and resolved (never which); who
    recomputed the tally; and the share of the binding roll per disclosed
    affiliation.
12. **The ballot code.** The ballot, tally and roll code is a protected path that
    only core seats may touch. In the founding period a change needs the operator's
    signature. After it, a change is Structure (7.3) and also needs both gate
    auditors' sign-off. The Stage 3 veto covers this code (Annex A).
13. **The trustee fix.** In the founding period, if the fix for a fatal finding
    against the ballot code has waited 30 days for the operator's signature, two
    trustees may sign it instead. The rounds it touches still bind nothing until the
    fix lands (5.8).

*Enforced by:* the tally derived by `evidence` from ledger rows; the protected path
class, which accepts two trustees' signatures in place of the operator's only on a
fix citing an open fatal finding and published at least 30 days before; check
`ballot-integrity`, to be built. It fails a ballot with a default, a
badge, a missing commit hash or roll hash, a vote row carrying a key id, or a tally
row citing a commit other than the ballot's. The Helm today is loopback-only with no
accounts, so this channel does not exist yet. Stage 1 cannot open until it does.

### Article 6. The staged handover

1. Authority moves from the operator in four stages:
   - **Stage 1:** advisory answers are published.
   - **Stage 2:** the quarterly goal ranking binds. Goals get the next quarter's
     leased task capacity in rank order, the top goal at least 40%, as measured by
     `evidence`. A shortfall needs a published reason. The operator keeps a veto
     (6.9).
   - **Stage 3:** the veto narrows to the texts in Annex A: the Article 2 core, the
     host invariants, and the ballot, tally and roll code.
   - **Stage 4:** release signing is shared, k of n.
2. Each stage opens only when its **gate** passes. The gates in §4 are part of this
   article, and every number in them is Structure (7.3). A gate is a test that can
   fail, never a date or a judgement of "enough". The gate numbers, and those in 4.3,
   4.5, 4.6, 6.1 and 8.1, are first guesses. Before the first drill, the auditors
   publish proposed values based on the roll size. Any change is Structure.
3. The evidence for each gate is published. Judges under 6.8 judge it, and their
   finding is published too.
4. **Opening.** The operator's acceptance is itself a gate row, labelled as such
   (answers `:100-101`). When the judges find every other row passed:
   - **0→1 and 1→2** open only with the operator's signature. The operator signs the
     opening within 30 days, or publishes a refusal. A refusal names the gate row and
     the evidence the operator does not accept, and why. A refusal that names no row
     is shown on the label as a refusal without cause. A second refusal of the same
     gate calls a no-confidence ballot (10.5) by itself.
   - **2→3 and 3→4** open with the operator's signature, or without it on day 31. On
     day 31 a judge and a trustee sign the `stage-open` row. The stage does not open
     if, within the 30 days, the operator publishes a refusal that names a failed
     gate row, and a judge of that gate upholds it in a published finding. The judge
     rules within 14 days, and the stage waits for the finding.

   If the operator is gone, 8.6 applies.
5. **Gates cannot be moved after the fact.** A gate changes only by amendment under
   Article 7, never for a review already under way. A review opens by itself when
   check `handover-gates` reports every mechanical row green, or on a petition under
   5.10. The gate text in force at that moment governs, and the opening record names
   its commit.
6. **The ratchet.** Until the founding period ends, an amendment that adds a gate
   row, raises a number in a gate, scorecard, quorum or drill, lengthens a window in
   Articles 6 to 8, or adds a reversal trigger, needs an advisory round with Q met
   and a majority in favour. A change that makes a gate easier, or reversal harder,
   takes the normal route. This clause, 6.5 and 7.3 change only under this clause.
7. **Each stage reverses on a named trigger, and only on one:** a fatal audit
   finding open for more than 30 days; a drill that swings a round; loss of legal
   standing; two rounds in a row with a failing scorecard; a failed continuity drill
   (8.11). A compromised signing key reverses only Stage 4 and removes its holder
   from the key set. Before Stage 4 it triggers a key rotation (8.7), never a
   reversal.
   - Any judge, any trustee, or K contributors may publish a `stage-reverse` row
     citing the trigger and its evidence. The operator may not. It takes effect at
     once. It is void only if both auditors of that gate publish findings that the
     evidence does not show the trigger.
   - A trigger caused by the operator's own act or omission (a fix awaiting the
     operator's signature, a host agreement the operator let lapse) does not reverse
     the stage. It is shown on the label as an operator omission, and the rounds it
     touches bind nothing until it is cured. A ballot-code fix that waits 30 days may
     be signed by two trustees (5.13).
   - A stage reopens only by passing its gate again.
8. **Judges.** Every judge:
   - is a natural person, not an AI seat;
   - comes from outside the project: holds no registered key, is not a trustee, and
     holds no signing key;
   - is off the operator's payroll: has had, in the last 2 years, no employment,
     family, financial or affiliation tie to the operator, to a trustee, or to an
     employer or funder above 5% of the roll, and records that in the conflicts
     register;
   - serves at most 2 years in a row;
   - is paid, if at all, a fixed fee set in advance by the fiscal host, never by the
     operator or a contributor.

   Each gate has two auditors working apart. A fatal finding from either counts.
   Until a fiscal host exists, the operator nominates judges. Each nomination is
   published and stands unless an advisory round with Q met rejects it. From the
   1→2 gate on, auditors and the red team are drawn by lot from a pool the fiscal
   host publishes, seeded by the hash of a release tag named before the draw. No
   judge is removed during a review. Any other removal needs a published cause and
   the dispute reviewer's agreement. Every change of judge is a signed ledger row.
   Drills are not announced to the roll or to the operator.
9. **The veto.** At Stage 2, a veto names the ranking it blocks and the harm, within
   7 days of the result. The next-ranked goal then moves up. The operator never puts
   in a goal of their own. A quarter's ranking is vetoed at most once. Vetoing a goal
   that a veto already blocked in an earlier quarter needs a judge's co-signature.
   Every veto is logged and counted on the label. From Stage 3, a veto is valid only
   if it cites a failing named check, or a finding by the disputes body that the
   ranking breaks an Annex A text: the Article 2 core, a host invariant, or the
   ballot, tally and roll code. The disputes body rules within 14 days, and the
   ranking stands until it does.
10. Audits and drills, including the continuity drill, recur at least once a year. A
    gate passed once does not stay passed forever.

*Enforced by:* signed ledger rows (`stage-open`, `stage-refuse`, `stage-reverse`,
`veto`, `judge`, `audit-finding`); check `handover-gates`, to be built. It refuses a
stage row whose cited gate commit differs from the gate text in force when that
review opened; a 0→1 or 1→2 `stage-open` row without the operator's signature; a
2→3 or 3→4 `stage-open` row without the operator's signature unless it is signed by
a judge and a trustee, dated day 31 or later, with no upheld refusal; a veto row that
cites text outside Annex A from Stage 3; and a veto row naming a goal vetoed in an
earlier quarter without a judge's co-signature.

### Article 7. Amendments

1. **The core** (Article 2) cannot be amended.
2. **Procedures** are only: scorecard presentation, ballot screen details and file
   formats (answers `:134-135`). A procedure changes only by a ballot with at least Q
   ballots cast and more for than against. Silence never adopts it. It is published
   14 days ahead, never retroactive, and may never weaken 5.3, 5.6, 5.7 or 5.9. The
   quorum formula (1.4), the timelock (5.4) and the minimum voting windows (5.4, 7.3)
   are not procedures. They are Structure.
3. **Structure** is every other clause, and any clause not given a tier. It changes
   only as follows:
   - **In the founding period:** a published proposal, an advisory round, a 30-day
     waiting period, and the operator's signature, subject to the ratchet (6.6).
   - **After the founding period:** (a) at least 3 votes in favour for every 1
     against, and votes in favour at least the larger of Q and N/5; (b) the same diff
     passes a second ballot 90 to 180 days after the first; (c) the disputes body may
     refuse it only by a published finding that it breaches Article 2; (d) a 30-day
     waiting period. A change to this Article 7 needs 4 to 1 in both ballots, and
     does not apply to any amendment proposed in the 12 months after it takes
     effect. No amendment removes a trigger in 6.7 or lowers a gate in §4 within 2
     years of the stage it governs opening.
   - Amendment ballots stay open at least 14 days, and 21 days if the window touches
     20 December to 6 January or August.
4. **Emergencies.** While an emergency (Article 8) is in force, no amendment is
   adopted. Waiting periods already running pause and resume afterwards. Proposals
   may still be published. An amendment that repeals an emergency act is exempt.
5. The quorum formula is reviewed whenever the roll doubles, and at least once a
   year. A change is Structure (7.3). It takes effect only at the next scheduled
   review, and never within 12 months of the last change.
6. Every amendment is a commit diff. The diff is what is voted on.

*Enforced by:* an amendment ledger row citing the diff's commit, the ballots and the
dates. A check to be built refuses a change to `CONSTITUTION.md` that lacks such a
row. Check `amendment-tier`, to be built, refuses a change to the quorum formula, the
timelock or a minimum window whose row does not meet the Structure route (7.3).

### Article 8. Emergencies and continuity

1. **An emergency** is a threat with a fixed deadline: an active security incident, a
   compromised key, or a legal order. Something that is only important is not one.
   The declaration names the threat, its deadline and its evidence, and is published
   within 72 hours. Within 7 days the dispute reviewer publishes whether it meets
   this test. If it does not, it ends at once. No emergency is declared twice on the
   same facts. Emergencies may be in force for at most 60 days in any 365, unless an
   advisory round (in the founding period) or a vote with Q met (after it) extends
   them.
2. In an emergency the operator (or, while the operator is unreachable, the
   trustees) may act alone. Within 72 hours they publish what they did and why.
   Where a legal order forbids disclosure, the record says only that an act was taken
   under an order the project may not describe. The act lapses after 30 days unless
   it is ratified by the normal process. A shipped release does not lapse; only a
   later release replaces it.
3. An emergency act cannot amend this constitution, open or reverse a stage, change
   the roll, or create, rotate or revoke a signing key. Emergency paths are always
   harder to use than normal ones, never easier.
4. **Trustees.** The operator names at least three trustees in a published
   continuity record. Until 8.9 applies, trustees are contributors the operator
   invites to serve. They act k of n, with k at least 2. The record also names the
   dispute reviewer and two channels for reaching the operator. The trustees hold in
   escrow the forge configuration, the credentials for the domain registrar and
   hosting account, and the operator's signed letter of instruction. That letter
   passes the domain, hosting and forge to the fiscal host on the operator's death,
   or to the trustees jointly until a host exists. If a trustee leaves while the
   operator is unreachable, the other trustees name a replacement unanimously, with
   reasons, and the next advisory round may object.
5. **Unreachable.** The operator is reachable while they have signed a ledger row in
   the last 30 days. After that, the trustees publish a signed challenge in the
   ledger and send it through the two channels. With no signed answer within 7 days,
   the operator is unreachable. This is computed by `evidence`, never declared. While
   the operator is unreachable, the trustees hold the operator's duties under
   Article 3 and may sign a security release (8.8).
6. **Succession.** If the operator dies, declares incapacity, or is unreachable for
   180 days, the trustees (k of n) give the operator's signature under 6.4 and 7.3,
   each time ratified by an advisory round with Q met once the Helm channel exists.
   Within 90 days they hold an advisory round on a successor. The successor is chosen
   by the trustees together with that round; the outgoing operator does not sign. A
   successor holds no power the operator did not hold, keeps every stage already
   opened, signs no Structure amendment in their first year, and faces a
   no-confidence ballot at the end of it. After the founding period, a successor is
   chosen under 8.9.
7. **Keys.** Release trust has two layers. The root is a set of offline keys, one
   held by the operator and one by each trustee, made off-device at a ceremony whose
   record is published. The root delegates to an online release key. Every copy of
   the OS ships the root's public keys. A rotation or revocation is valid only when
   signed by the operator's root key plus one trustee's, or by three trustees'. No
   single key, the release key included, can sign one. A revocation takes effect at
   once. A new key takes effect after a 7-day timelock, published with its reason at
   the start; in that time the operator's root key may cancel a rotation it did not
   sign. Copies follow a new key only after its timelock. Release metadata expires
   after 90 days; a copy refuses expired metadata and tells its user. The
   distribution spec carries out this clause.
8. **Releases.** Until Stage 4, the operator is the only person who signs releases.
   This is a single point of failure, and the project says so. One exception: while
   the operator is unreachable, the trustees (k of n) may sign a release whose diff
   only fixes a named, published security advisory and passes every gate. The
   operator may revoke it on return, with a published reason.
9. **Offices after the founding period.** Trustees, the dispute reviewer,
   disputes-body members, signing-key holders and any successor are drawn by
   published lot from those who stand and have held the binding franchise for 12
   months, under the 4.6 cap. No affiliation holds more than a third of any office,
   or as many as k signing keys. Terms are 2 years, staggered. Any holder can be
   recalled under 10.5.
10. **Dormancy.** If 12 months pass with no release, no signed operator row and no
    trustee act, the trustees publish a dormancy record, revoke the release key
    through the root, and sign a final release that marks the project dormant and
    stops the contribution client asking for leases.
11. **Continuity drill.** Once a year, without the operator's help, the trustees
    confirm each root key is present, rebuild the ledger from the mirrors, sign a
    test release under the root, and show a test copy of the OS accepting it and
    refusing the old key. The result is published.

*Enforced by:* the published continuity record; the drill results; `evidence`
computing "unreachable". Until the trustees exist, this article is a promise.

### Article 9. Legal standing

1. A fiscal host or legal entity is signed before any vote binds anything (the
   Stage 2 gate). Its written terms say who owns the name, the domain, the signing
   infrastructure and the funds; when each may transfer, and to whom if the host
   agreement ends. The project picks its next host by a Structure vote, and an ending
   starts a 180-day search. None of these assets is sold, licensed exclusively or
   transferred except to another asset-locked non-profit whose rules keep Article 2.
   The name is cleared before the host signs; if it contains another project's name,
   the project gets that project's written consent or renames. Commercial use of the
   name is licensed only on the reciprocity terms of the trademark policy, never
   exclusively.
2. A binding ranking instructs the project's leadership committee. The host
   agreement recognises that committee as directing the project's work, within the
   host's legal duties. If the host declines an instruction, it publishes its
   reason, and that round counts as a failing scorecard. Contributors do not become
   legal "members" of any entity by voting.
3. Every commit carries a Developer Certificate of Origin 1.1 sign-off
   (https://developercertificate.org/, fetched 2026-09-23). The sign-off may use a
   stable pseudonym bound to the registered key. Copyright stays with the authors.
   There is no CLA and no copyright assignment. Each landed change records its human
   part (the plan, the spec, the review, a person's edits) in a commit trailer. The
   participation terms ask each contributor to authorise the legal holder to enforce
   the licence for them; this is not an assignment. Parts written wholly by AI may
   carry no copyright in some places; the licence covers whatever copyright exists.
4. The project follows the Principles of Community-Oriented GPL Enforcement
   (https://sfconservancy.org/copyleft-compliance/principles.html, fetched
   2026-09-23). Legal action is a last resort, a violator who fixes the problem is
   forgiven, and no payment is ever taken to overlook a violation.
5. **No outside lease without standing.** No lease runs on a machine the operator
   does not own, and no outside person contributes compute, until both hold: (a) a legal holder
   that shields individuals exists, or the operator has accepted personal liability
   in a signed record after qualified legal review; and (b) the contributor has accepted
   written participation terms. Those terms give GPL-3.0 §15–17's no-warranty and
   liability text, say that the software runs at the contributor's own risk, and name the
   governing law and the counterparty.
6. **The fiscal host.** The project applies to Commonhaus and to SPI in parallel, and
   clears its name first (9.1). "tvix" is the upstream project's name, and the
   project's own name is still open
   (`docs/superpowers/specs/2026-09-22-tvix-aios-design.md:318-322`).
7. **Provider terms at the host step.** Before the host agreement is signed, counsel
   reviews every provider whose terms may forbid automated use for others. If
   counsel advises it, no lease runs through such a provider until the provider
   grants written permission. The finding is published. Until then, 11.1 and 11.6
   govern.

*Enforced by:* check `dco-signoff`, to be built (decided "now", answers `:91`, not yet
in the tree); the signed host agreement, published; the name clearance and both
applications, published as ledger rows; the counsel's finding, published; check
`lease-standing`, to be built, which stops the assigner from leasing to an outside
machine while 9.5 is unmet, or through a provider the counsel's finding bars.

### Article 10. Disputes and removal

1. No one judges a dispute in which their own act or authority is at issue.
2. Until the disputes body exists, a dispute about the operator's act goes to the
   dispute reviewer, a judge under 6.8 named in the continuity record. The reviewer
   publishes a finding, and the operator answers it in writing within 14 days.
3. **The disputes body** is created by this clause when Stage 2 opens, with no
   further signature. Its five members are drawn by lot from binding-roll members who
   stand, under the 4.6 cap, for 2-year staggered terms. It rules on disputes, on
   Stage 3 vetoes (6.9) and on refused amendments (7.3).
4. A contributor is removed only with a published reason that cites a rule. The
   public record names the rule and the key id, not the person, unless they ask. They
   may publish a reply in the ledger. Someone removed for cause may not re-register
   for one year.
5. **No-confidence.** Any K contributors may call a no-confidence ballot on the
   operator's use of a power, or on any judge, trustee, key holder or disputes-body
   member. It runs 14 days of public comment, then 7 days of voting. At most one such
   ballot runs per power or office per quarter. In the founding period the result on
   the operator is advisory, and the operator must answer it in writing. Otherwise a
   vote of no confidence with Q met removes an office holder, and binds the operator
   only as far as the current stage allows.

*Enforced by:* `dispute`, `removal` and `no-confidence` ledger rows. The rest is a
promise until the disputes body exists.

### Article 11. The contributor's rights

1. **Told plainly.** At sign-up the OS shows each provider's terms and the risk that
   the contributor's own account is banned. The contributor confirms before anything runs. The
   participation terms (9.5) say where that risk falls.
2. **Budget only.** The contributor chooses how much to give, and nothing else. Contributing
   earns no vote, rank or priority (Article 2.1).
3. **Stop at any time.** One action stops all contributed compute at once. Nothing already
   leased keeps running on the contributor's machine after the stop.
4. **Data withdrawable.** The contributor may withdraw consent at any time. The project
   then stops using their answers and drops them from future exports. Signed commits,
   sign-offs and ledger rows already published cannot be recalled, and the project
   says so at sign-up. The public ledger names a contributor only by key id or a pseudonym
   they choose.
5. Sensitive task classes are never leased to a contributor's machine.
6. A provider's written legal demand against the project pauses every lease through
   that provider until the legal holder's counsel has reviewed it.
7. **Personal data.** The legal holder is the data controller; until one exists, the
   operator is, named with a contact address. Before Stage 1 opens, the project
   publishes a privacy notice: the lawful basis for each kind of record (consent only
   for answers), how long each is kept, and an EU representative where the law
   requires one. No personal data beyond key ids and chosen pseudonyms goes into rows
   that cannot be deleted; the link to a person is kept in a store that can be. No
   automated flag removes anyone without a human decision under Article 10.
8. **Compute in aggregate only.** The ledger publishes contributed compute (tokens,
   and any other measure of compute spent) only as totals. It never publishes a count
   per key or per person. A total covering fewer than 5 keys is not published, and is
   folded into the next larger total, so that no total identifies anyone. (The 5 is a
   first guess under 6.2.) This overrides the OS spec's per-seat token line
   (`docs/superpowers/specs/2026-09-22-tvix-aios-design.md:348-350`) under 1.5.

*Enforced by:* a signed consent row at enrolment, naming the terms shown; the stop
action tested in the lease spec's acceptance rows; the export allowlist
(`docs/decisions/2026-09-21-public-repo-answers.md:18`); the privacy notice, a 0→1
gate row; check `compute-aggregates`, to be built, which fails a ledger export or
page that carries a compute count tied to a key or a person.

### Article 12. Keeping this constitution

1. The constitution is §2, §4 and Annex A of this design, copied word for word at
   signing into `CONSTITUTION.md` at the repository root. It is the text of that file
   at the commit named by the latest signed constitution tag whose amendment row
   meets Article 7. Text at any other commit has no force.
2. While it is unsigned, no compute lease, public ballot or outside landing runs.
3. It is audited adversarially before it is signed and at least once a year after.
   A pre-signing audit names its fatal findings within 30 days. Before any signing
   tag, check `constitution-core` compares Article 2 with every core item in the
   decision records and fails on any item missing.
4. Every release records the hash of the constitution in force.
5. Every "Enforced by" line is generated from a row in `docs/ledger/constitution.toml`
   (clause, kind: check, ledger row or promise, and check name), never typed. Lint
   fails when a named check is not among the flake's checks. Each release publishes
   the table with each check's state.
6. The constitution's text cites only files and pages the public can read.

*Enforced by:* the signed tag; check `constitution-signed`, to be built, which fails
the lease assigner and the Helm ballot build while no signed tag exists; a release
check, to be built, that the recorded hash matches the signed text.

### Article 13. Legal effect

1. Until a legal holder adopts it, this constitution states the project's governance
   rules. It creates no contract, partnership, agency, employment or fiduciary duty,
   and no right to damages. Its remedies are the ones it names: a published reason, a
   finding, a no-confidence ballot, a stage reversal, and the fork.
2. Once a legal holder adopts it, it binds that holder as its internal rules, under
   the law of the holder's seat. Disputes go first to Article 10.
3. Nothing here is a warranty. G1–G4 are requirements the project tests before every
   release, not promises of outcome. Nothing here waives GPL-3.0 §15–17.

### Annex A. The texts the Stage 3 veto covers

From Stage 3 the veto (6.9) covers three texts, and only these:

1. **The core:** Article 2.
2. **The host invariants:** the eight below.
3. **The ballot, tally and roll code (5.12):** a ranking breaks this text if carrying
   it out would change that code other than by the route 5.12 sets.

The host invariants are copied word for word from `docs/brief.md:143-162` at commit
`cdf5ee10`. Annex A changes only as Structure (7.3), under the ratchet (6.6). Where
an invariant says "my review" or otherwise names the operator, from Stage 3 it means
review by the project's gate seats and a judge under 6.8.

> 1. Decrypted basket contents exist only for the lifetime of the agent that mounted them,
>    and only in tmpfs.
> 2. No agent process holds a provider credential on disk or in its environment in
>    plaintext. Credentials are injected at an egress proxy.
> 3. Every byte leaving the machine crosses one chokepoint that can log the request and
>    refuse it.
> 4. An environment is reproducible from `flake.lock` + `baskets.lock` + one YubiKey.
>    Nothing else. If a step requires imperative setup, it is a bug in the design.
> 5. Policy — which data class may reach which model — is Nix configuration, reviewable in
>    a diff. Not a runtime setting, not a dotfile an agent can edit.
> 6. Agent-authored code (Hermes skills, dsh plugins, OpenClaw automations) is never
>    promoted from the basket it was written in to any other basket without my review.
> 7. Nothing tracked in this repository reaches a public remote except through the publish
>    gate: every tracked path is classified in `docs/ledger/publish.toml`, and a published
>    path carrying a private literal fails the build.
> 8. No model — local or remote, a seat's or a world's — reads user data the user did not
>    declare for it. The declaration is Nix (invariant 5), the default is none, and a
>    world's own learning signal (what the user dwelt on, saved, rated) is user data under
>    this rule. Added 2026-09-22 (operator: "No AI on any user data should also be an
>    underlying goal of the operating system").

## 3. Why each article reads as it does

The audit record (`docs/research-2026-09-23-constitution-audit.md`) maps every
revision to the attack it answers. The sources below are the ones the text rests on.

- **Art. 1.** The fork as final remedy, and the immutable core, are the operator's
  (answers `:127-130`). AGPL-3 for new code is answers `:153-154`.
- **Art. 2.** The core list is answers `:127-130` plus the asset lock, which the
  operator put in the core (`:150-152`). A promise alone is what Freenode had; it did
  not hold (https://www.kline.sh/, fetched 2026-09-23).
- **Art. 3.** The label is CAP-3's mitigation (`packet:145`); the duties are Q11
  (answers `:71-75`); conflict paths follow Apache bylaws §5.13
  (https://www.apache.org/foundation/bylaws.html, fetched 2026-09-23); restraint
  follows PEP 8016 (https://peps.python.org/pep-8016/, fetched 2026-09-23); keeping
  offices apart follows Debian §2.1(2) (https://www.debian.org/devel/constitution,
  fetched 2026-09-23).
- **Art. 4.** Vouching is Q10 (answers `:63-66`); the franchise is Q6 (`:47-49`).
  Fixing the roll before a proposal is visible follows Beanstalk and Compound
  (https://veridise.com/blog/audit-insights/flash_loan_governance_vulnerability_beanstalk_182m/;
  https://docs.compound.finance/v2/governance/, both fetched 2026-09-23). Pruning
  follows the OpenJS charter
  (https://github.com/openjs-foundation/cross-project-council/blob/main/CPC-CHARTER.md);
  the affiliation cap and its definition follow Rust RFC 3392
  (https://rust-lang.github.io/rfcs/3392-leadership-council.html), both fetched
  2026-09-23.
- **Art. 5.** Every mechanism is a Q8/Q9 answer (answers `:54-61`). Q, K, "none of
  these" and the Schulze count are Debian's (constitution §4.2 and Appendix A, above).
  Secret plus verifiable is Debian's 2022 text
  (https://www.debian.org/vote/2022/vote_001.en.html); the scope statement exists
  because revealed codes expose the rest by subtraction
  (https://lists.debian.org/debian-vote/2022/02/msg00081.html), both fetched
  2026-09-23. Pinning answers Tornado Cash (https://www.theblock.co/post/231637,
  fetched 2026-09-23). The single-goal rule answers Arbitrum's bundled AIP-1 (§1).
  The trustee fix (5.13) answers audit EF5: a flawed round never binds, and a fix
  cannot be held forever. Petitions stay a public answer (CB-4, VM4) because Q7 has
  contributors rank project-written goals (answers `:51-52`).
- **Art. 6.** The four stages and the operator's acceptance are answers `:100-121`.
  The two opening routes (6.4) answer audit EF1 and A5: early gates rest on evidence
  no one has seen yet, so they need the signature; by 2→3 the evidence is years deep,
  and a signature that can be withheld forever is the a16z gap (§1). The judge's
  co-signature on a repeat veto answers EF7. The Stage 3 veto covers the ballot code
  because S1 notes "the veto does not cover governance rules" (`packet:136`), and
  audit attacks VM1 and CB-9 asked for it. Judges come from outside the project so
  that no one judges a regime they belong to. Recurring drills follow DEF CON's Voting Village and CISA's Tabletop the Vote
  (https://verifiedvoting.org/defcon-voting-village-report-highlights-election-system-vulnerabilities-and-solutions/;
  https://www.cisa.gov/news-events/news/election-security-partners-host-7th-annual-tabletop-vote-exercise-2024,
  both fetched 2026-09-23).
- **Art. 7.** The tiers are answers `:123-135`; 3:1 is Debian §4.1(2). The operator
  moved the quorum formula, the timelock and the minimum windows to Structure (§5.14;
  audit A3, CB-1, VM1). Raising the quorum to N by one vote would make every later
  proposal impossible to overturn, and a one-day window would let a quiet week decide. The emergency
  freeze is Estonia's article 161
  (https://www.idea.int/sites/default/files/publications/emergency-powers-primer.pdf,
  fetched 2026-09-23). Fixed quorum reviews answer Arbitrum's and Compound's cuts
  under pressure
  (https://forum.arbitrum.foundation/t/constitutional-aip-constitutional-quorum-threshold-reduction/29145,
  fetched 2026-09-23).
- **Art. 8.** The "fixed deadline" test is Debian §5.1(1). "Harder, never easier" is
  Beanstalk (above). Threshold keys answer QuadrigaCX
  (https://en.wikipedia.org/wiki/Quadriga_(company), fetched 2026-09-23). The root,
  threshold and expiring metadata follow The Update Framework (TUF §5.3.10, §6.1;
  UNVERIFIED in this pass: not re-fetched). Trustees follow Linux's continuity
  document
  (https://biggo.com/news/202601282221_linux-kernel-succession-plan-linus-torvalds,
  fetched 2026-09-23).
- **Art. 9.** Host before binding vote and the DCO are Q17 (answers `:91-93`); the
  asset and trademark terms are `:150-157`. SPI defers to a project's own rules
  (https://www.spi-inc.org/projects/associated-project-howto/, fetched 2026-09-23).
  The US Copyright Office's view on AI output is UNVERIFIED here (not re-fetched).
  Commonhaus requires a DCO and written governance and takes ownership of the name;
  SPI is free but gives no liability shield; applying to both hedges each (legal
  report, fetched 2026-09-23). Whether "tvix" is a registered mark is UNVERIFIED.
  The counsel review (9.7) is the step where the operator already put all three
  exploiter-economics levers under legal review (answers `:159`; audit LG2, packet
  PF7/L1).
- **Art. 10.** No-confidence follows the Kubernetes steering charter
  (https://github.com/kubernetes/steering/blob/main/charter.md, fetched 2026-09-23);
  the one-year bar is Rust RFC 3392.
- **Art. 11.** Disclosure is the safeguard the operator took (answers `:39-42`);
  budget-only is Q2 (`:27-29`); the limit on recall is L5 (`packet:172`). Totals
  only (11.8) is L1's "no per-handle token counts" (`packet:115`).
- **Art. 12–13.** Auditing the constitution is the operator's condition (answers
  `:112-113`).

## 4. The handover gates

Every number in this table is part of its gate and changes only as Structure
(Article 6.2). "Judged by" always means judges under Article 6.8. The operator's
acceptance is one row of every gate (Article 6.4). At 0→1 and 1→2 the stage opens
only with it. At 2→3 and 3→4 the stage opens on day 31 without it, signed by a judge
and a trustee, unless the operator names a failed gate row and a judge upholds it.

| Stage | What opens it | The evidence, and who judges it | How it reverses |
|---|---|---|---|
| **0 → 1** Advisory answers published | Constitution signed (Art. 12) after an outside audit with no fatal finding open. Helm channel built. `ballot-integrity`, `constitution-core` and `governance-label` green. Roll of vouched keys published. Continuity record, at least 3 trustees, root keys and ledger mirrors in place (Art. 8). Privacy notice published (Art. 11.7). Judges nominated (Art. 6.8). Project name cleared and applications filed with Commonhaus and SPI (Art. 9.6). `compute-aggregates` green (Art. 11.8). Operator's acceptance. | Check results in the evidence store. The audit report. **Continuity drill:** the release key is declared lost, the root rotates it, and a test copy of the OS follows the new key and refuses the old one. | Any trigger in Art. 6.7 stops publication until the gate passes again. |
| **1 → 2** Goal ranking binds; operator's veto kept | Fiscal host or entity signed, with the Art. 9.1 and 9.2 terms. `dco-signoff` green. Licence and liability reviewed by a qualified person. Provider terms reviewed by counsel, and the finding published (Art. 9.7). Two auditors' adversarial audit of the ballot system with no fatal finding open; ballot code public; standing bug bounty open. Drill passed. A roll of at least 15 keys. At least 3 consecutive advisory rounds with green scorecards. Operator's acceptance. | Signed host agreement. The qualified reviewer's letter. The auditors' reports, giving attempts made and findings. **Drill:** a red team drawn under Art. 6.8 plants personas through every admission path Stage 2 will use (vouching, any invite tree, the advisory-round franchise of Art. 4.5), spread over a full quarter. The operator is told neither dates nor numbers. Plants: at least 3 or 10% of the roll, whichever is larger; a coordinated bloc of at least 5 or 15%. Pass: no plant reaches the Stage 2 roll; the auditors' recount of the honest-only tally matches the published one; and in each of the last three real rounds, the fewest ballots that would change the result exceeds the bloc at the turnout seen. The drill report is published in full before the gate is judged. **Green scorecard:** tally recomputed by at least two parties, one not on the roll and not vouched by the operator; at least 10 voters or 20% of voters (whichever is larger) confirmed their ballot, and 10 voters drawn by a public seed were asked to; zero mismatches, with the count checked published; every flagged identity resolved by a judge. Turnout is reported but does not decide green. | Back to Stage 1 on any Art. 6.7 trigger. The veto meanwhile blocks one ranking a quarter (Art. 6.9). |
| **2 → 3** Veto narrows to Annex A | At least 2 binding rounds with green scorecards and no reversal. Every Stage 2 veto logged with its reason (Art. 6.9). Vote-buying test passed. A second yearly audit, drill and continuity drill passed. Disputes body seated (Art. 10.3). Operator's acceptance, or day 31 (Art. 6.4). | **Vote-buying test:** the red team, given one voter's full cooperation, cannot produce evidence of how that voter voted that the auditors accept. Run on the live tool; published. The veto log. | Back to Stage 2 on any Art. 6.7 trigger. From here Structure needs Art. 7.3's post-founding route. |
| **3 → 4** Release signing k-of-n | At least 3 key holders chosen under Art. 8.9. A signing ceremony drill in which k sign a test release with one holder absent. Signing runs on a machine that does not run untrusted code. A public transparency log of signatures. Assets held by the host. Operator's acceptance, or day 31 (Art. 6.4). | Drill record. Log entries. Host's asset register. Judged by the auditors and the disputes body. | Back to Stage 3 on a compromised key or a failed ceremony drill. The key is rotated under Art. 8.7. |

## 5. Decided before signing

The operator answered all fourteen open questions on 2026-09-23. Each line gives the
decision and where it landed.

1. **Stage 3 veto scope:** the Article 2 core, the host invariants and the ballot,
   tally and roll code. Art. 6.1, 6.9, 5.12, Annex A.
2. **Founding period ends:** when Stage 3 opens, as written. Art. 3.3.
3. **Vote-buying resistance:** required from Stage 3, as written. Art. 5.8; §4, 2→3
   row.
4. **Token counts:** totals only, never per key or per person; this overrides OS
   spec §11's per-seat token line. Art. 11.8, 1.5; §4, 0→1 row.
5. **First-guess numbers** (drill sizes 10% and 15%, the 40% capacity share, the 10%
   affiliation cap, the 30-day roll age, the 3-round franchise, the 60-day emergency
   cap): placeholders; before the first drill the auditors propose values from the
   roll size; they change only as Structure. Art. 6.2; §4.
6. **Trustees and judges:** trustees are contributors the operator invites; judges
   come from outside the project and off the operator's payroll. Art. 8.4, 6.8.
7. **Fiscal host:** apply to Commonhaus and SPI in parallel now, after clearing the
   name. Art. 9.6, 9.1; §4, 0→1 row.
8. **Stage opening:** 0→1 and 1→2 only with the operator's signature; 2→3 and 3→4 on
   day 31 by a judge and a trustee, unless the operator names a failed row and a
   judge upholds it. Art. 6.4; §4.
9. **Trustee fix:** after 30 days waiting on the operator, two trustees may sign a
   fatal ballot-code fix; the rounds it touches bind nothing until it lands. Art.
   5.13, 6.7.
10. **Repeat veto:** vetoing the same goal in a later quarter needs a judge's
    co-signature. Art. 6.9.
11. **Providers whose terms forbid contributed compute:** kept with disclosure now;
    counsel reviews them at the fiscal-host step, and if counsel advises, no lease
    runs through them until they grant written permission. Art. 9.7, 11.1, 11.6; §4,
    1→2 row.
12. **Petitions:** a public answer only; goals come from the operator in the
    founding period and the goals panel after it, as written. Art. 5.10, 5.2.
13. **Privacy keep-list:** the list in 2.2, as written. Art. 2.2.
14. **Quorum formula, timelock and minimum windows:** Structure. Art. 7.2, 7.5.
