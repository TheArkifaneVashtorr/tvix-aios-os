# Concept 2026-09-02c — `basket rekey` (recipient agility)

**Class:** CLI subcommand + lock-file semantics. **Status:** proposed.

**Origin data (today):** the recipient set changed mid-phase (YubiKey out,
software key in) and may change again (hardware keys re-added, a key lost or
compromised, node3's operator key). Today that means manually re-encrypting every
basket.

**Idea:** `basket rekey <store> --recipients <new-file> --identity <old-key>` —
decrypt each payload in memory, re-encrypt to the new recipient set, update
`payload_sha256` in `baskets.lock`. The deterministic-content design already pays
off here: `content_sha256` is computed over the plaintext tar, so re-keying
provably changes *only* the envelope — a rekey diff shows every content hash
untouched, which is exactly the reviewable evidence invariant 5 wants for a
security-sensitive operation. Add `basket recipients <store>` to list which
recipient set each payload was last encrypted to (age headers carry stanzas per
recipient), so "who can open what" is measurable, not assumed.

**Earliest landing:** Phase 2 window (small, self-contained, CLI-only) or bundled
with the first real recipient change. Test: rekey a store, verify old identity
fails, new succeeds, all content hashes identical.
