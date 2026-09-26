---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run ev1, task R4 — APPROVED

Branch head `20bb77492ece` (`~/factory/ws/ev1/R4`, `task/R4`). Reviewer: Opus, high effort, throwaway clone; checks re-run by ref.

## Summary

R4 is correct and I could not break it. The guard moved from the flake check into nixosModules/helm.nix exactly as specified, and the check became the honest tryEval its three siblings use. Red-before-green is real: reverting only nixosModules/helm.nix while keeping the rewritten check at HEAD produces `error: helm-control-assertion-negative-profiles: profiles=[base nope] DID NOT FAIL the build`. A direct probe confirms the bad fixture now fails on the new assertion in the BASE evaluation naming `nope`, with zero failing assertions in the alt child -- the non-nesting / marker-skip claim is proven, not merely asserted. All five mutations (guard polarity, all->any, dropped base exemption, deleted guard, vacuous membership test) were killed by the acceptance set. All four named checks are green, plus nine adjacent checks the acceptance line does not name (helm-control-vm, the other three helm-control negatives, helm-eval, helm-assertion-negative, core-gaming-wiring, core-backup-wiring, module-eval) to rule out a regression in configs the module now constrains. Two minors, neither blocking: the negative check does not verify the failure reason (it stayed green under the inverted-guard mutation -- helm-control-eval and host-core caught that one), and the marker guard is fail-open if /etc/helm/profile is ever declared with .source instead of .text. Both are plan-level hardening, not implementer error. The throwaway clone has been deleted.

## Checks

- green — helm-control-assertion-negative-profiles: nix build .#checks.x86_64-linux.helm-control-assertion-negative-profiles -L --no-link -> exit 0 in the throwaway clone at 20bb774.
- green — helm-control-eval: exit 0; the positive fixture [base alt] with specialisation.alt still evaluates and the alt child is skipped.
- green — host-core: exit 0; built nixos-system-core-25.05.20260102.ac62194.drv for base and the gaming child -- core's [base gaming] passes, gaming child (marker "gaming") is skipped.
- green — lint (nix develop -c githooks/pre-commit): 'formatted 75 files (0 changed)', 'All checks passed!', '23 files already formatted', 'render.test.mjs: all assertions passed', EXIT=0.
- green — helm-control-vm (regression probe, not in acceptance): exit 0 -- the VM node declares specialisation.alt and forces its marker, so the new assertion does not break it.
- green — helm-control-assertion-negative-enable / -agentunit / -workspace (regression probes): all exit 0; the agentunit check's message-infix assertion on 'egress-broker-cowork.service' still holds with the extra module assertion present.
- green — helm-eval, helm-assertion-negative, core-gaming-wiring, core-backup-wiring, module-eval (regression probes): all exit 0.

## Red before green

In the throwaway clone at 20bb774 I reverse-applied only the implementation and kept the test at HEAD: `git checkout HEAD~1 -- nixosModules/helm.nix` (flake.nix, which carries the rewritten check, stayed at HEAD), then `nix build .#checks.x86_64-linux.helm-control-assertion-negative-profiles -L --no-link`. Decisive output line: `error: helm-control-assertion-negative-profiles: profiles=[base nope] DID NOT FAIL the build` (exit 1) -- exactly the failure the plan's Step 2 predicts. Restored with `git checkout HEAD -- nixosModules/helm.nix` and re-ran green. I also probed which assertion fails at HEAD (a temporary flake.nix edit, reverted): `error: PROBE-BASE[services.helm.control.profiles names a profile that is not a declared specialisation: nope] ALTCHILD[]` -- the bad fixture fails on the new assertion in the BASE evaluation, and the alt child has zero failing assertions, i.e. the marker guard skips the child exactly as the Interfaces section specifies. The bare tryEval alone could not have shown that.

## Mutation table

| mutation | killed | by |
|---|---|---|
| nixosModules/helm.nix:638 marker guard polarity flipped: `!= "base"` -> `== "base"` (check the child, skip the base) | yes | helm-control-eval and host-core. NOT killed by helm-control-assertion-negative-profiles, which still exited 0 -- the bad fixture then fails in the alt CHILD (specialisation = {}), not in the base, and the bare tryEval cannot tell the two apart. helm-control-eval: `Failed assertions: - services.helm.control.profiles names a profile that is not a declared specialisation: alt`; host-core: `... : gaming`. |
| nixosModules/helm.nix:639 `lib.all` -> `lib.any` (one satisfied profile excuses the rest) | yes | helm-control-assertion-negative-profiles -- `error: helm-control-assertion-negative-profiles: profiles=[base nope] DID NOT FAIL the build`, exit 1. |
| nixosModules/helm.nix:639 base exemption dropped: `p == "base" \|\| ` deleted from the predicate | yes | helm-control-eval -- `Failed assertions: - services.helm.control.profiles names a profile that is not a declared specialisation:` (empty list, since the message's own filter still exempts "base"), exit 1. |
| nixosModules/helm.nix:638 marker guard deleted (line replaced by `false`, so the check runs inside specialisation children too) | yes | helm-control-eval (`... : alt`) and host-core (`... : gaming`), both exit 1 -- the guard itself is load-bearing and pinned. |
| nixosModules/helm.nix:639 membership test made vacuous: `config.specialisation ? ${p}` -> `p != ""` | yes | helm-control-assertion-negative-profiles -- `error: ... profiles=[base nope] DID NOT FAIL the build`, exit 1. |

## Findings

- **minor** `/home/dalhaka/nixos-agent-env/flake.nix:1176` — helm-control-assertion-negative-profiles is a bare tryEval with no check of WHY the fixture failed, so it passes for any evaluation error. Mutation M1 (inverting the marker guard to `== "base"`) left this check green: the bad fixture then failed in the alt specialisation child rather than in the base, and the check could not see the difference. Only helm-control-eval and host-core caught it. The sibling helm-control-assertion-negative-agentunit already does the stronger thing (asserts the joined failing-assertion messages contain a specific string). **Fix:** Give this check the agentunit shape: bind `failing = c: lib.concatStringsSep "\n" (map (a: a.message) (lib.filter (a: !a.assertion) c.assertions))` and in the else branch additionally throw unless `lib.hasInfix "is not a declared specialisation: nope" (failing helmControlBadProfilesSystem.config)` -- i.e. require the BASE evaluation to be the one that refuses. The plan's Step 1 prescribed the current shape, so this is a plan-level improvement, not an implementer deviation.
- **minor** `/home/dalhaka/nixos-agent-env/nixosModules/helm.nix:638` — The child-detection guard is fail-open in shape: `config.environment.etc."helm/profile".text or "base"` yields `null` (not the `or` default) when the marker is declared with `.source` instead of `.text`, because the attribute exists with a null value; `null != "base"` is true, so the whole profile check would be skipped for such a config. In practice the pre-existing marker assertion at helm.nix:625-629 evaluates `builtins.match profileNameRegex (... .text or "")` on the same null and errors out first, so the build still fails and no config in the repo is affected -- but the new assertion's own guard does not defend itself. **Fix:** Make the guard fail-closed on an unknown marker, e.g. `let marker = config.environment.etc."helm/profile".text or null; in (marker != null && marker != "base") || lib.all ...`, and reuse the same normalisation in the sibling assertion at helm.nix:627.

## Deviations

The FACTORY-RESULT declared no deviations; FACTORY-NOTES ("Module now owns the G1/D1 assertion; negative check reduced to a tryEval of the bad fixture") restates the spec rather than departing from it. I found none. The diff touches exactly the two files in `touches` (flake.nix, nixosModules/helm.nix), 15 insertions / 9 deletions, and both hunks are byte-equivalent to the plan's Step 1 and Step 3 code blocks. The commit subject is an exact match for the plan's "commit subject" line (verified with diff against the plan text). The trailer block carries `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run ev1)` followed by `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` -- the same pair as the sibling factory commit 6a88cef (E1), and the Co-Authored-By line is exact. The workspace tree is clean (the implementer's commit-msg.txt scratch file was removed). No --no-verify, no `2>/dev/null`, no sudo/nixos-rebuild/systemctl, no secrets, no placeholder text in the log or the diff.
