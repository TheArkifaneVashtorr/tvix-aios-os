# Concept 2026-09-02g — hardware identity ledger

**Class:** repo data file + CLI guard. **Status:** proposed.

**Origin data (today):** "key B is in" — but the serial said it was key A again,
twice. Physical YubiKeys are indistinguishable; roles ("basket key A/B/C") exist
only in human memory, which is exactly where this project stores nothing else.

**Idea:** `keys.toml` in the repo — the authoritative role→serial ledger:

    [keys]
    basket-a = { serial = 00000000, enrolled = "2026-09-02" }
    # basket-b / basket-c filled at enrollment

`tools/enroll-yubikey.sh` gains a guard: read the connected key's serial first;
refuse to enroll a serial already holding another role; on success, append the
new role→serial line (a reviewed commit, like all policy). `basket doctor` gains
a probe: connected key's serial must map to a known role. Physical keys get a
matching sticker the day they're enrolled.

**Test:** enroll with a ledgered serial under a new name → refusal naming the
existing role; doctor with an unledgered key connected → WARN.

**Earliest landing:** with YubiKey B's real enrollment — the guard prevents the
exact confusion that just happened from ever recurring.
