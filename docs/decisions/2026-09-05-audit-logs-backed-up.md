# Decision 2026-09-05 — the lane ledgers and the broker audit logs are backed up

**Operator, 2026-09-05 ~12:50 CDT:** "backing them up works." Asked as the open
gap `lane-ledger-and-broker-audit-unbacked` from the environment review: neither
`/var/lib/lanes/<lane>/ledger.jsonl` nor `/var/lib/egress-broker/<instance>/audit.jsonl`
was a restic path, so the two audit records of what agents asked for and what the
broker allowed or denied lived only on `core`'s disk.

**Decision.** Both directories join `services.proton-backup.paths` on `core`:
`/var/lib/lanes` and `/var/lib/egress-broker`. Three things under them are
excluded on purpose: `/var/lib/lanes/*/jobs` and `/var/lib/lanes/*/results` (job
payloads and model output — not audit records, and they grow), and
`/var/lib/egress-broker/*/ca` (each broker instance's CA, private key included:
never leaves the machine, not even inside the restic ciphertext). Directories
rather than files, so a lane or instance that has not written yet cannot make the
nightly restic run exit 3 on a missing path.

**What closes it.** Plan `docs/superpowers/plans/2026-09-05-backup-audit-paths.md`,
task B1: `host-core` asserts the two paths and the six exclude patterns;
`core-backup-wiring` requires the runbook to name the paths; the claim flips to
verified at the integration revision. Rollback is the previous generation; the
snapshots already taken keep whatever they hold.

**Addendum, 2026-09-05 ~23:50 (operator, telemetry-store questions; decision
`2026-09-05-telemetry-store-decisions.md`, answer 5).** The broker half of this
decision is reversed: `/var/lib/egress-broker/*/audit.jsonl` holds the
machine's verbatim egress paths, client addresses, hostnames and SNI values,
and the operator decided it does not leave the machine, not even as restic
ciphertext — the store's derived daily rows are the durable numbers. The lane
half stands, narrowed to the ledger file: of `/var/lib/lanes` only
`*/ledger.jsonl` is worth the backup; `jobs/` and `results/` stay excluded.
B1 (run bk2) was built to the original wording minutes before the reversal;
B1b applies the addendum before anything lands. The claim
`lane-ledger-and-broker-audit-unbacked` closes as "ledger backed up; audit
logs disposable by decision".
