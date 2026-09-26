# Decision 2026-09-03 — three amendments to "if it cannot be measured or tested it isn't real"

**Decided by the operator, 2026-09-03** ("I agree with the amendments, please
adjust accordingly"), after the day's re-gates found passing tests that could
not fail (a VM probe that 404s for every directory, a budget test asserting
inside a subshell, a polkit check by substring, a citation scanner that stops
after the first fenced block) and a real security hole (the broker port
reachable from every local uid) that no test had measured.

The rule stands. It is amended:

1. **Falsifiable, not merely tested.** A load-bearing test counts only once it
   has been shown to fail: red before the change (TDD), and at review a
   mutation or refutation that turns it red again. "Has a test" is not
   evidence; "the test failed when it should" is. Reviewers report a test that
   cannot fail as a finding of class `vacuous-test` (major).
2. **Unmeasured is debt, not nonexistence.** A claim we cannot yet measure —
   an absence (no path to the key), a structural property, a judgement — is
   recorded as dated debt with an owner on the board, acted on when the
   reasoning is strong, and closed when a measurement exists. It is never
   treated as false, and never used as a reason to skip the reasoning.
3. **Proxies are declared.** Every measurement that stands in for the real
   goal names what it stands in for and the known gap (eval pass rate on
   twenty seeds → fewer defects in factory output; fix rounds per task across
   different tasks → confounded). A proxy is reported as a proxy.

**Tracked number:** per review round, how many passing assertions were shown
vacuous (2026-09-03: about six of forty new ones). The factory ledger records
`vacuous-test` findings so the count is generated, not remembered.

**Where it applies:** brief §8's working rules (this decision is the
amendment; the brief text is not edited), CLAUDE.md's "How work is done here",
the dark-factory review and verify prompts, the NixOS skill's
`review-checklist` reference, and the orchestrator's own gate judgements.
