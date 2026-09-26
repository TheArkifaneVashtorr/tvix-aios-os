# Concept 2026-09-02i — VM image provenance pin

**Class:** supply-chain hardening atop the Cowork VM. **Status:** proposed
(orchestrator-originated, from the field-fix round).

**Origin (orchestrator, 2026-09-02):** fixing the "Sending…" hang
(`docs/research-2026-09-02-cowork-sending-hang.md`) required allowlisting
`downloads.claude.ai` so the Cowork VM's rootfs (~1.3 GB, plus `vmlinuz`/
`initrd`) can download at first session start. That's the minimum fix — it
still means every fresh session start (or any rootfs cache eviction) is a
runtime dependency on an outside host being reachable and serving exactly
the bytes the app's manifest expects, over a broker hop that has to stay
correctly configured. The manifest itself already carries everything needed
to pin and verify that download instead of trusting it live.

**Idea:** at the claude-desktop package pin currently in the flake (`2479d511`),
the VM bundle manifest inside `app.asar` names an exact version:
`` sha:`2a762adfc2eea13eca0d113a2e6452ff00ae3f62` ``. The manifest is a full
history of published bundles (each entry keyed by its own sha and
`publishedAt`); the pinned entry's `files.unix` splits by CPU arch
(`arm64`/`x64`), and each arch's file list carries per-file `{name, size,
rawSize, checksum}` entries — `checksum` (confirmed 64 hex chars, i.e.
sha256-shaped; the field is not literally named `sha256`) — for
`rootfs.img` (x64: 1,286,740,082 bytes; arm64 differs), `vmlinuz`, and
`initrd`. Each file entry also carries a `rawChecksum` (a second checksum,
confirmed present, over the ~10 GiB decompressed image — `rawSize:
10737418240` — rather than the compressed bytes on the wire) and a
`deltas:[{fromSha, checksum, size}]` list (confirmed present) for fetching
an incremental patch from a previously-cached older sha instead of the full
file. A pin that only stages the three full files per arch is incomplete if
the helper's cache already holds an older rootfs and prefers a delta fetch
from `downloads.claude.ai` over the full one — the local mirror/FOD needs to
either cover the delta path too (mirror the specific `fromSha` deltas the
helper would pick) or force it: e.g. by never pre-seeding an older sha into
the helper's cache, so it always resolves to the fully-pinned file. A Nix
fixed-output derivation (or an explicit prefetch step) pulls this host's
arch's three files once, verified against the manifest's own `checksum`
fields, and serves them from a local mirror on an address already inside
the broker's allowlist (a loopback/local origin, not `downloads.claude.ai`)
— or, more simply, stages them content-addressed in the Nix store and
satisfies whatever cache path the `cowork-linux-helper` checks before
downloading (the digest only has `[Bundle:status] rootfs.img missing` and
`startVM: rootfs not found`; the actual lookup path — `~/.cache`, an XDG
dir, or something else — is not yet confirmed and would need grepping the
helper binary/logs before building this, and confirming whether it ever
attempts a delta fetch is part of that same grep). Either shape gets the
same property: **first boot has no runtime dependency on
`downloads.claude.ai`** — the broker rule can even be tightened or dropped
once this lands, shrinking the allowlist back down instead of growing it.

**Payoffs:**
1. Removes a live runtime dependency on an external host from the boot path
   of every Cowork session — no more "download denied → hang forever"
   failure mode, and no download-progress wait on a slow link either.
2. Content-addressed images are exactly the kind of fixed, reproducible seed
   `concept-2026-09-02h-proving-grounds.md` wants for deterministic
   experiment runs — a pinned, checksum-verified rootfs is a stronger
   starting point than "whatever downloads.claude.ai currently serves."
3. Makes a claude-desktop pin bump an explicit, greppable event instead of a
   silent behavior change: bumping the pin means re-grepping `app.asar`'s
   manifest for the new `sha`/checksums, which becomes one line in the
   upgrade runbook rather than something nobody notices until the next
   "Sending…" hang.

**Dependencies:** none blocking — buildable directly against the current
claude-desktop pin's `app.asar`, no other mini-phase required. Interacts
with the broker allowlist (Task 1 of the field-fix plan) only in that this
concept is the path to eventually removing `downloads.claude.ai` from it
rather than keeping it forever.

**Earliest landing:** after the operator gate on this field-fix round closes
(need a live confirmation the current allowlist-based fix actually works
before hardening the same code path further). A follow-on task, not urgent —
the current fix is sufficient and correct; this is defense in depth plus a
proving-grounds prerequisite.
