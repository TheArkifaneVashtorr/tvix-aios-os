# 2026-09-22 — the objective is tvix-aios; the queue frozen and triaged

## The operator's words

"I feel like there is a fundamental misunderstanding of the long term goals of this
project. Lots of what the system is doing is churn for churn's sake. The goal is
tvix-aios, a Rust-based NixOS AI-native operating system that has all of the needed infra
to run VMs and agent workflows built into the operating system." And, on the ComfyUI
worlds: "It will be a functional part of the operating system."

## What was measured before deciding

- `docs/brief.md` §2 still stated the 2026-08 objective (a graded-isolation lab for
  agent harnesses). Every plan, key and the derived queue descend from that sentence.
  tvix-aios entered the tree on 2026-09-21 as two research packets and one plan.
- Commits since 2026-08-22: 2279. By `<area>:` prefix, docs 797, reviews 111, board 103,
  factory 92, evidence 89, helm 63, generation 61, plans 42, seat 41, knowledge 41,
  ledger 35. Two subjects mention tvix or aios. Roughly half the month is the factory
  writing about itself.
- `~/flakes/tvix-aios` is untouched upstream canon (`9fbca101`), no `flake.nix`, nothing
  of ours in it.
- OpenRouter spend since 2026-08-22: $887.31 over 30,998 rows; $706.90 carries
  `attribution: none`, so cost per plan is not attributable. A gap in the record.
- The Escalated line (35 fix rounds pending `claude/review`) is phantom: every root has
  landed or been superseded by a later round; EV20's own body measured the same. Zero
  live work there.

## Decisions

1. **Brief §2 rewritten** as the tvix-aios objective with four measurable goals; a wave
   that moves none of them is not dispatched (`docs/brief.md` §2). The 2026-08 text is
   kept under a `<details>` block for the record. Invariants §3 unchanged.
2. **Queue frozen** (operator's choice "freeze and triage" over "freeze without triage"
   and "drain then pivot"): every ready or blocked key held in
   `docs/ledger/task-status.toml` since 2026-09-22, then triaged the same day with one
   test — does the task become part of the OS image, or a test of it?
3. **Verdicts on the 23 open keys.**

   | verdict | keys | why |
   |---|---|---|
   | released | IS22 IS23 IS24 IS25 | the guard in Rust: policy enforcement over agent actions is an OS primitive (goal 2) |
   | released | GN49 GN51 GN52 GN53 GN54 | the worlds are a functional part of the OS (operator; goal 4) |
   | withdrawn | PL9 PL10 PL11 PL12 PL13 FA25 EV20 | this flake's test hygiene, driver plumbing, queue bookkeeping: serve no goal |
   | held (salvage) | SP9 KN16 OC10 FA26 | the pattern (telemetry ingest, single-source doc generation, coverage report, guard rules) goes into the OS spec; the code as typed is lab-wired |
   | running, finish | EV19 FA27 FA28 | land if they pass their gate; no fix rounds after |

4. **The escalated fix rounds take no review.** They are closed work; the line is ignored
   until the tool stops printing it. Patterns worth carrying into the OS spec from the
   landed roots: FA13 (role → model registry), IS1/IS3 (agent concurrency cap), IS5/IS11
   (broker metering, LAN ingress auth), OC1/OC9 (evidence schema, request labelling
   through the broker), KN1 (rules ledger → generated docs), PR1 (every path owned by one
   subsystem).
5. **The bash factory is a reference implementation**, not the product: the seat driver,
   integrator and gates keep running tasks, but no further task is typed to improve them
   until the OS spec names the workflow runtime they become.
6. **Next step is the spec**, not a plan: gather and loose-ends for tvix-aios already
   exist (2026-09-21). A design spec under `docs/superpowers/specs/` follows the
   brainstorming path, and only then a plan. Media keys are typed where the worlds live.

## Risks

- Goal 4 was written by the orchestrator from one sentence of the operator's; its
  acceptance wording may not be what the operator means by "functional part".
- The salvage holds expire only by a later decision; a held key older than a fortnight is
  a smell the brief will show.
- Spend attribution is missing for 80% of the OpenRouter ledger; the churn cost is a
  guess until OC-family instrumentation is re-justified against goal 2.

## Addendum, same day: the AIOS notebook concepts

The operator asked what happened to the LM-Notebook AIOS v51 concepts (salvaged
2026-09-19 into `~/flakes/aios`, a git repo with no remote). Measured: the 2026-09-21
gather's aios-lineage dimension carried only the failure record (parse failures,
fabrication) and dismissed the name as a coincidence; the loose-ends asked only about
the name; the board deferred an "ideas lift" to a decision nobody asked for. No design
idea from the notebook reached the packet. That was a miss.

**Decision (operator, 2026-09-22):** fold the concepts in by hand during the spec
brainstorm rather than run a gather over the salvage. Concept inventories of both
families and the merged manifest are the third input to the spec beside the two
2026-09-21 packets; every number the notebook attached stays UNVERIFIED.

## Addendum, same night: baskets and classification are OS features

The operator, after invariant 8 and goal 6 landed: "Revisit the triage: baskets and
classification are OS features, not scaffolding." The morning's assessment had listed
"baskets-as-encrypted-data-subsets" among the things that do not obviously survive. Re-
measured: no withdrawn, held or escalated key concerns baskets, data classes, the
classification assertion or the publish gate's deny scan (PL9–PL13 are Helm and lane
negative-check refactors, not the basket assertion; `assertion-negative`, `basket-vm`
and `invariant-basket-tmpfs` are the live checks and all are landed). So the verdicts
stand as typed and the correction is to the framing and the spec:

- `nixosModules/basketStore.nix` (declarations, the local-only-vs-off-box assertion) and
  `pkgs/basket/basket.sh` (age-encrypted payload, tmpfs, read-only bind) are the
  enforcement of invariants 1 and 8. They are OS subsystems, named `aios.data` in the
  spec (§4), and the model for every world and seat input.
- The classification assertion gains its own acceptance check for goal 6
  (`aios-classification-negative`: an undeclared path bound into a world or seat fails
  the build), typed in the goal-2 plan.
- The daemon observes basket state (mounted, by whom, until when) and refuses to start a
  seat or world whose declared classes are not mounted; mounting stays root-only under
  the operator's YubiKey (invariant 4) until a later spec moves it.
