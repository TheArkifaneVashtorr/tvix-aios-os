# Amendment 2026-09-02 — hardware key not required for basket crypto

**RETRACTED same day.** The directive "it doesn't need to be age locked" was a
terminology collision: the operator read "age" as age/identity verification, not
as the `age` encryption tool. Clarified: the operator wants the YubiKey. The
YubiKey requirement and `tests/acceptance/phase1.sh` are restored as the Phase 1
acceptance path; the softkey variant remains only as a hardware-free automated
test. The throwaway software identity generated during this detour
(`~/.config/basket/identity-core.txt`) was deleted — nothing persistent was ever
encrypted to it. Lesson recorded: explain tool names in plain language.

Original (retracted) text follows for the record.

---

Operator directive (mid-Phase-1 acceptance): "It doesn't need to be age locked" —
issued while the YubiKey was absent from USB and unprovisioned for age.

**Applied reading (chosen to keep maximum security at zero cost):** basket
encryption stays (age, unchanged CLI, unchanged tests); the *hardware* requirement
is dropped. The operator identity is a software age key at
`~/.config/basket/identity-core.txt` (mode 0600, generated at first acceptance run).
Acceptance test: `tests/acceptance/phase1-softkey.sh` — same brief §7 substance,
no hardware, no sudo.

**Consequences, stated plainly:**

- Invariant 4 now reads "reproducible from `flake.lock` + `baskets.lock` + the
  identity file". The identity file must be backed up out of band and must never
  be placed inside any basket or the repo.
- At-rest protection of baskets is now only as strong as protection of that file
  (i.e., of the disk it sits on). Full-disk encryption status of `core` is the
  operator's side of that ledger.
- YubiKeys can rejoin at any time with zero rework: age is multi-recipient, so
  hardware keys become *additional* recipients on the next re-encryption (see
  concept `basket rekey`). Nothing in Phases 2–9 depends on which kind of
  recipient decrypts.
- The hardware acceptance script (`tests/acceptance/phase1.sh`) remains in the
  repo, unused, for that future.

**If the directive meant "no encryption at all":** say so explicitly and baskets
become plain archives (lock/verify/tmpfs semantics unchanged); not applied because
it removes real protection for no gain while encryption is already free here.
