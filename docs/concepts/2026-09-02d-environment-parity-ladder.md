# Concept 2026-09-02d — the environment-parity ladder

**Class:** testing infrastructure / project doctrine. **Status:** partially adopted.

**Origin data (today):** the mount code passed every test and then failed on the
real host twice, for two different environment-shaped reasons: tmpfs remount
breaks *only* inside user namespaces; `mount --move` breaks *only* under systemd's
shared mount propagation. Each fix was correct for the environment it was tested
in and wrong for the one it wasn't.

**Idea:** privileged or environment-sensitive behavior is only "real" (per the
operating directive) at the rung of this ladder that matches production, and every
phase's suites must name their rung:

1. **Nix sandbox** — pure logic (unit tests, addon tests).
2. **userns, private propagation** — mount/net mechanics, unprivileged.
3. **userns, shared propagation** — systemd-host mount semantics (added today
   after the field failure; would have caught `--move` before the operator did).
4. **NixOS VM test** — real systemd, real root, real units, still fully automated
   (`checks.integration`, introduced in Phase 2).
5. **Host acceptance** — real hardware (YubiKey, real internet), operator-run.

Rule of thumb established: a bug found at rung N adds a permanent regression test
at the *lowest* rung that can express it — never only at rung N. (The propagation
bug now lives at rung 3, cheap and fast, though it was found at rung 5.)

**Earliest landing:** doctrine now; mechanically, Phase 3's `basket doctor` probes
(see [invariant-preflight](2026-09-02-invariant-preflight.md)) become rung-5
checks, and every new module ships a rung-4 VM test.
