# Concept 2026-09-02e — declarative trust graph (`trustRoots.nix`)

**Class:** infrastructure (NixOS module, Phase 4 window). **Status:** proposed.

**Origin data (today):** three of the Phase 2 factory's field bugs were trust-store
plumbing, not logic: mitmproxy validates upstream certs against its *bundled*
certifi store, ignoring the OS trust the VM test had extended (fixed by pointing
it at `/etc/ssl/certs/ca-certificates.crt`); CN-only test certs were rejected for
lacking a SAN; and the managed-settings research showed Claude's inner sandbox
`tlsTerminate` accepts `{caCertPath, caKeyPath}` — i.e. it can be handed the
broker's CA. Trust relationships are currently configured in four unrelated
places with four different idioms.

**Idea:** one module declares the trust graph, everything else is generated:

```
trustRoots = {
  broker.trusts     = [ "system" ];             # + org CA later
  agents.<class>.trusts = [ "broker:<netns>" ]; # broker CA into env trust store
  claudeInner.trusts = [ "broker:<netns>" ];    # via managed tlsTerminate paths
  vmTests.trusts    = [ "throwaway" ];          # test CAs, same mechanism
};
```

The module renders: `security.pki` entries, mitmproxy
`ssl_verify_upstream_trusted_ca` args, managed-settings `tlsTerminate` objects,
and guest/env CA bundles for virtiofs delivery. Who-trusts-whom becomes a single
reviewable diff (invariant 5 applied to trust, not just egress policy), and a CA
rotation is one attrset change.

**Test:** a VM test asserting each declared edge works and — the sharp half —
each *undeclared* edge fails (an agent env must NOT trust a CA nobody granted it).

**Earliest landing:** Phase 4 (managed settings already need broker-CA
distribution); the broker module's CA handling refactors into it then.
