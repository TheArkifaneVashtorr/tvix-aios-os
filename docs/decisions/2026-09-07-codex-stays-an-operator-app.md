# Decision 2026-09-07 — Codex stays an operator app and an agent under study; Codex on core is parked

**Operator, 2026-09-07 ~18:55 CDT, after CX1b's gate:** "I don't currently
have any desire to switch the core to codex. It was to plan for fable token
depletion. You may continue to use codex as an agent and collect information
about it. You may archive the plan for the codex agent to be core."

**Reading recorded.**

1. **Purpose.** The Codex flake (`~/flakes/codex`, five commits ending
   a58b3aa, gated APPROVED in
   `docs/reviews/2026-09-07-opus-review-cx1b-CX1b.md`) exists as a fallback
   for the day the Claude (Fable) budget is exhausted: a fresh machine, or a
   depleted week, brings Codex up from `git clone` plus `nix build`. It is
   not a plan to make Codex core's model, and no NixOS module for Codex is
   imported by `nixosConfigurations.core`.
2. **What stays.** `~/flakes/codex` keeps its `packages.codex`,
   `nixosModules.default` (renders `/etc/codex/managed_config.toml`, the
   layer that outranks `~/.codex/config.toml`) and the throwaway
   `nixosConfigurations.test` as a build-only proof. The installed operator
   app stays the standalone, self-updating `~/.local/bin/codex`.
3. **Parked.** "The module onto core is a plan and a switch" — struck from
   the board's next-turn block; a `parked` entry on the board; revisited
   only on the operator's word. The CX1b MINORs (MAP.md, a wider precedence
   check, checks that dial `api.openai.com`, the bwrap-capable builder)
   stay listed as an optional XS task on the flake, not owed.
4. **Continues.** Codex as an agent under measurement: the `codex` arm of
   the seat driver (a `.result` row and a telemetry row per run, the
   session's token counters from `~/.codex/sessions`), sequenced after the
   seat-harness wave that owns the driver files; classification probes;
   every task gated as any seat's. Codex runs stay outside the seat lane and
   the broker (decision 2026-09-02: the invariants bind agents, not operator
   apps; a Codex task under `danger-full-access` is an agent with the
   operator's rights, so the agent-VM question stays open — see the board's
   2026-09-07 turn — and is the operator's).

**Facts CX1/CX1b established, for whoever picks the flake up:** under
`codex exec --sandbox workspace-write` on this host the nix daemon socket,
DNS and `.git` are unreachable (`--add-dir` cannot lift it); under
`danger-full-access` Codex closed all thirteen review items in ~40 minutes
(1.72 M session tokens, 1.64 M cached, 82 k billed); `--strict-config`
rejects a misspelt key under `exec`, not `doctor`; the npm tarball's
entrypoint is `vendor/x86_64-unknown-linux-musl/bin/codex` and its bundled
zsh needs `ncurses`.
