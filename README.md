# nixos-agent-env

Declarative NixOS environments running AI agent harnesses (Claude Cowork, dsh, Hermes
Agent, OpenClaw) in graded isolation over encrypted, classified data baskets, behind a
TLS-terminating egress broker and a classification-routing model gateway.

Governing spec: `docs/brief.md`. Design: `docs/superpowers/specs/`. Decisions awaiting
operator confirmation: `docs/decisions/`. Upstream verification:
`docs/upstream-verification-2026-09-02.md`.

Status lives on the board: `docs/OPERATIONS.md` START HERE, and
`evidence bundle --markdown` for the live facts.

Git is local-only: `githooks/pre-push` refuses every remote except exact URLs listed
in `githooks/allowed-remotes.txt`, and refuses public forges unconditionally. Run
`git config core.hooksPath githooks` after any fresh clone (the Phase 1 devShell will
enforce this automatically).

## License

GPL-3.0-only: the full text is `LICENSE` at the repository root (the GNU General Public
License, version 3, verbatim, byte-identical to the fork it will be published beside).
Vendored code keeps its own licence: `pkgs/dsh` (`@deepseek-ai/dsh`, MIT),
`pkgs/proton-drive-cli` (`ProtonDriveApps/sdk`, MIT) and `pkgs/dsh-harness/skills` (an
adapted copy of `superpowers`, MIT © 2025 Jesse Vincent — `pkgs/dsh-harness/README.md`).
