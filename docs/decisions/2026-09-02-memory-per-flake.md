# Decision 2026-09-02 — Claude memory: separate per flake, never shared

**Operator, 2026-09-02 late:** "the area the memories are stored in is not
accessible from any flake; I only need a builder here" — then: "the other
flakes can have memory files, I just want them separated."

**Recorded:** Claude memory lives under `~/.claude/projects/<folder-slug>/memory`
(0700 chain, operator-only), one directory per folder a session opens. Each
flake (nixos-agent-env, ~/flakes/gaming, ~/flakes/media, ~/strategy) has its
own; none is linked, copied or symlinked into another; no flake, basket,
workspace or container can reach any of them; no memory plumbing goes into
flakes. Each memory directory is backed up individually (nightly restic,
ciphertext, runs as the operator); the host pre-creates the directories so a
folder never opened does not make the backup report a missing path. The
workspaces mini-phase must not mount, copy or link a memory directory.
