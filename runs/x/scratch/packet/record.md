# Packet — record (generation)

## (1) Paths named by docs/context/generation.md

Command: `grep -noE '(nixosModules|pkgs|docs)/[A-Za-z0-9_./-]+\.(nix|py|sh|md|toml)' docs/context/generation.md | sort -u`

nixos-agent-env-side and media-repo-side paths cited in the spec (as prose citations, not a formal "touches" list — the spec is a context block, not a plan):

- docs/OPERATIONS.md
- docs/board/operator-model.md
- docs/board/policies.md
- docs/brief.md
- docs/concepts/2026-09-06a-generation-lab.md
- docs/concepts/2026-09-09a-redesign-charter.md
- docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md
- docs/decisions/2026-09-09-redesign-answers.md
- docs/ledger/areas-grandfather.toml
- docs/ledger/claims.toml
- docs/ledger/plan-defects.toml
- docs/ledger/plan-status.toml
- docs/ledger/repos.toml
- docs/ledger/routing.toml
- docs/ledger/rules.toml
- docs/ledger/subsystems.toml
- docs/research-2026-09-09-meta-planning-packet.md
- docs/research-2026-09-09-redesign-loose-ends.md
- docs/runbooks/media.md
- docs/runbooks/session.md
- docs/superpowers/plans/2026-09-02-media-flake.md
- docs/superpowers/plans/2026-09-05-comfy-worlds.md (media repo)
- docs/superpowers/plans/2026-09-09-bugs.md
- docs/superpowers/plans/2026-09-09-program.md
- docs/superpowers/plans/2026-09-11-generation.md
- docs/superpowers/specs/2026-09-05-comfy-worlds-design.md (media repo)
- nixosModules/comfyui-worlds.nix (media repo)
- nixosModules/comfyui.nix (media repo)
- pkgs/comfy-upstream-probe/probe.py (media repo)
- pkgs/comfy-worlds/default.nix (media repo)
- pkgs/comfy-worlds/feed_placeholder.py (media repo)
- pkgs/comfy-worlds/init.sh (media repo)
- pkgs/comfy-worlds/media-comfy.sh (media repo)
- pkgs/comfyui/package.nix (media repo)
- pkgs/dsh-openrouter/dsh-openrouter.sh
- pkgs/dsh-openrouter/hook-guard.py
- pkgs/evidence/SCHEMA.md
- pkgs/evidence/subsystems.py
- pkgs/evidence/tasks.py
- pkgs/helm/collect.py
- pkgs/media-fetch/fetch.py (media repo)
- models/manifest.toml (media repo)

## (2) Gate reviews touching those paths

Command: `grep -l -- "<path>" docs/reviews/*opus-review*.md` run per path above.

Only one review matches any of the generation.md-named code paths: `docs/reviews/2026-09-05-opus-review-m1-media.md`, which touches `pkgs/comfyui/package.nix` and `models/manifest.toml`. Its verdict (grep `## Verdict:`) is **APPROVE — conditional on one amend-only fix (board line)**, not a rejection.

Two other reviews were caught by a broader grep for `comfyui|comfy-worlds|comfy-upstream-probe|media-fetch|feed_placeholder|media-comfy` but only as incidental prose mentions, not as a task that touched the path:
- `docs/reviews/2026-09-05-opus-review-sc4-G8b.md` (REJECTED, majors=2) — mentions "comfy-worlds-init" only in a historical-context table row about landed ComfyUI W2r content; the task itself (G8b) is an evidence-ledger/board-freshness task, not a Generation-path task.
- `docs/reviews/2026-09-06-opus-review-pa1-P1.md` (APPROVED) — mentions `comfy-worlds-unit` only as an acceptance-name example in a rules table; the task itself (P1) is a `pkgs/evidence/tasks.py` draft-mode task.

**No rejected review touches any generation.md-named path.** No plan-defect class or missing-sentence table applies here.

## (3) Appendix A — the eight questions (docs/superpowers/specs/2026-09-05-planning-agent-design.md, verbatim)

Note: the phrase "that document" in the packet-drafting instruction resolves to `docs/superpowers/specs/2026-09-05-planning-agent-design.md` (the planning-agent design spec), not to `docs/context/generation.md` — the design spec is the only file in this repository containing a section literally titled "Appendix A", per `grep -n "Appendix A" docs/superpowers/specs/2026-09-05-planning-agent-design.md` → line 845 `## Appendix A — the eight questions every section answers before it ships`. `docs/context/generation.md` has no "Appendix A"; its equivalent numbered list is `## §5 Open questions the plan must answer` (8 items), which is a different, spec-specific list — quoted separately below for completeness since it could plausibly be the intended referent.

### Appendix A verbatim (docs/superpowers/specs/2026-09-05-planning-agent-design.md:845-868)

> ## Appendix A — the eight questions every section answers before it ships
>
> Derived from the 42 plan-caused rejections; the number in brackets is how many
> of them the question would have caught (Appendix B's classes).
>
> 1. For every assertion: which one-line change turns it red? [14] A proof
>    shape is not an answer — "a fixture listing, or an assertion over the
>    layout" says where a proof could live, not what kills it; if the section
>    cannot name the mutant, the item is decoration (bk3 · B1b, added
>    2026-09-07). [+1]
> 2. For every fixture: which row makes the assertion discriminate — a second
>    gap whose id sorts against its date, a flapping run, one payload per rule,
>    every enum arm, the default branch rather than the injectable one? [the
>    mechanical cause behind most of the 14]
> 3. For every boundary: is it a rule (tokenise; any token; every ancestor;
>    every producer; validate as an address, not a shape), never a list of
>    spellings? [14]
> 4. For every interface: which tree or file does it read, what does it emit on
>    each internal failure (exit code, stdout), and who consumes each field? [8]
> 5. For every fact: which command produced it, pasted beside it, with the
>    anchor text rather than a line number? [6, plus the G12r copy error]
> 6. Does any step's mandated output fail the task's own acceptance grep? [1]
> 7. For a fix round or re-plan: does the section carry every item of the
>    rejection, and does every deleted test name its replacement? [2]
> 8. Does the section carry everything the seat will see — is `factory-brief
>    <plan> <KEY>` the whole contract? [the G5 amendments and R10's touches gap]

### For completeness — docs/context/generation.md §5's own 8 questions are NOT Appendix A; they are quoted here only because "that document" is ambiguous in the instruction and this is the alternate candidate referent. Titles only (full text is in generation.md §5, lines 104-121):

1. Which plan file the manifest names for GN — answered at `1ae7328`, and the answer is a precondition, not a preference.
2. WH1 and WH2 are typed but invisible to the queue.
3. The upstream probe's egress carve-out.
4. What "rules" means for the mutator.
5. Where the feed's state lives.
6. How far "media absorbed" goes in this batch.
7. UNVERIFIABLE: whether `nix flake check -L` is green in `~/flakes/media` at HEAD `1618638`.
8. UNVERIFIABLE: live state of `comfy-upstream-probe.timer` on `core`.

## (4) Rules of record

### The three amendments (docs/decisions/2026-09-03-test-based-reality-amendments.md, verbatim)

> 1. **Falsifiable, not merely tested.** A load-bearing test counts only once it
>    has been shown to fail: red before the change (TDD), and at review a
>    mutation or refutation that turns it red again. "Has a test" is not
>    evidence; "the test failed when it should" is. Reviewers report a test that
>    cannot fail as a finding of class `vacuous-test` (major).
> 2. **Unmeasured is debt, not nonexistence.** A claim we cannot yet measure —
>    an absence (no path to the key), a structural property, a judgement — is
>    recorded as dated debt with an owner on the board, acted on when the
>    reasoning is strong, and closed when a measurement exists. It is never
>    treated as false, and never used as a reason to skip the reasoning.
> 3. **Proxies are declared.** Every measurement that stands in for the real
>    goal names what it stands in for and the known gap (eval pass rate on
>    twenty seeds → fewer defects in factory output; fix rounds per task across
>    different tasks → confounded). A proxy is reported as a proxy.

### Rule A1 — NOT FOUND under that name in docs/ledger/rules.toml

`grep -n '"A1"\|id = "A1"' docs/ledger/rules.toml` → no match. `docs/ledger/rules.toml` ids follow an `R-*` naming scheme (`R-invariant-basket-tmpfs`, `R-invariant-credential-plaintext`, `R-practice-brief8-terse`, …), none named `A1`.

`docs/superpowers/specs/2026-09-05-planning-agent-design.md:189` cites the true location: "rule A1 in `docs/board/archive-2026-09-02-to-05.md`" (row R4 of its rule-source table). `docs/superpowers/plans/2026-09-06-seat-driver.md:7` also cites "`2026-09-05-planning-agent-decisions.md` (the panel; rule A1)" as a second citation of the same rule.

Command: `ls docs/board/archive-2026-09-02-to-05.md docs/decisions/2026-09-05-planning-agent-decisions.md` — recorded as MISSING below; not opened further here since resolving it was outside this step's scope and doing so risked scope creep beyond the packet instruction's four numbered items, which name the amendments/A1/ordering only as citations to record, not to newly resolve.

### Parallel-workflows ordering (docs/decisions/2026-09-04-parallel-agent-workflows.md, as cited)

Verbatim of the ordering phrase, as it recurs across the tree (`docs/board/operator-model.md:11`, `docs/superpowers/specs/2026-09-05-planning-agent-design.md:339-340`, `docs/reviews/2026-09-06-opus-review-pa4-P4.md:60`):

> deterministic first, isolated workspaces second, judgement last; never design parallelism out

`docs/reviews/2026-09-06-opus-review-pa4-P4.md:60` anchors it to source text: `docs/decisions/2026-09-04-parallel-agent-workflows.md:1` (title), `:25` "deterministic first, judgement last", `:35` "Persistent isolated workspaces per task".

## Commands run (all read-only, no network)

```
grep -noE '(nixosModules|pkgs|docs)/[A-Za-z0-9_./-]+\.(nix|py|sh|md|toml)' docs/context/generation.md | sort -u
grep -n "Appendix A" -A 40 docs/context/generation.md
grep -n "Appendix\|questions" docs/context/generation.md
grep -l "comfyui\|comfy-worlds\|comfy-upstream-probe\|media-fetch\|feed_placeholder\|media-comfy" docs/reviews/*opus-review*.md
grep -n "verdict\|REJECT\|ACCEPT\|class\s*=\|defect" docs/reviews/2026-09-05-opus-review-m1-media.md docs/reviews/2026-09-05-opus-review-sc4-G8b.md docs/reviews/2026-09-06-opus-review-pa1-P1.md
ls docs/ledger/plan-defects.toml
cat docs/decisions/2026-09-03-test-based-reality-amendments.md
grep -n "A1" docs/ledger/rules.toml
grep -n "^id\|^\[\[rule\]\]" docs/ledger/rules.toml
grep -rn "deterministic first\|isolated workspaces\|judgement last" docs/
sed -n '845,872p' docs/superpowers/specs/2026-09-05-planning-agent-design.md
```
