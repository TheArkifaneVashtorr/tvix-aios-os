# Decision — the generation lab's brainstorm answers (operator, 2026-09-06 ~01:00 CDT)

**Context.** Concept `docs/concepts/2026-09-06a-generation-lab.md` closed with
six brainstorm questions. The operator answered five in one message; the sixth
(what the lab table may hold) stands at the recommendation until said otherwise.

## Answers

1. **Which competition.** None chosen; "we can pick one later, I didn't have a
   specific need." The lab is built competition-agnostic; a target is picked
   when one appears.
2. **What "grade" means.** As recommended: prompt adherence by the local
   vision judge, aesthetics by a small scorer, the operator's picks as the
   truth that overrides both.
3. **Search first; and bins that could be LoRAs.** Search over the LoRAs on
   disk first; in addition the lab stores the operator's generated and picked
   images into organised bins (by subject, style, character, pose — the bins
   the operator would train a LoRA from) so each bin is a ready training set
   when training comes into scope.
4. **SFW only for competition work; the two worlds are one definition.** The
   point of the two worlds is that one version pin has the same effect on both
   ("the pin has the same effect on both corpses"). For the NSFW world the
   whole loop — prompt generation, image review, prompt mutation — runs on
   LOCAL models only, because the remote models the project uses refuse the
   topic. The SFW world may use whatever the routing table allows.
5. **The lab table** — recommendation stands: parameters, scores and image
   hashes in the store; prompt text only inside the world's own lab
   repository, on the machine.
6. **Models and assets arrive by hand** for now; a download-only broker
   allowlist for civitai.com later. In addition the lab does the algorithmic
   analysis the operator named: from the rounds table it infers which LoRAs
   carry the most value (contribution to picks and scores), recommends what to
   acquire or drop, and adapts the model set to a fixed disk budget (a set
   amount of space, evicting the least valuable).

## Consequences

- The lab plan (after the worlds' waves 2–3) carries these as constraints:
  a competition-agnostic loop; three grading signals with picks on top; a
  bins directory per world with a manifest (a bin = a candidate LoRA dataset);
  the NSFW variant local-only end to end; a rounds table of numbers and hashes;
  a LoRA value analysis and a disk-budget policy.
- The local judge and the local prompt model become dependencies of the
  NSFW variant: both must be packaged in the media flake and fit the card
  beside Krea 2 by loading and unloading.
