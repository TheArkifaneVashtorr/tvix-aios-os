# The OpenAI lab spike — design (spec for the planning agent, 2026-09-08)

**Operator, 2026-09-08 ~18:55 CDT (the board's paraphrase):** a fresh flake
pinned to this repo, built end to end by the OpenAI agent already under
measurement here, each task gated the same way a DeepSeek seat's is.

**The question.** Can the OpenAI agent on core — GPT-6 through Codex CLI,
running as the `FACTORY_SEAT=codex` arm of `tools/factory/seat` that landed
CX2/CX2b on `~/flakes/codex` — build something on a *fresh* target the house
would review and keep, three small tasks in a row, with no help beyond what
the driver already gives every seat? `~/flakes/codex` proved the arm can
land one fix round on an existing, already-scaffolded flake; this spike asks
whether the arm can also scaffold, extend and document a small NixOS-facing
project from nothing.

**The measurement.** The same gate record the DeepSeek seats already carry,
so a `codex` row sits beside `deepseek/deepseek-v4-pro-0813` and
`deepseek/deepseek-v4-flash` with no new column: first-try yield (approved
without a fix round, from the review front matter), named mutants dead over
mutants named, rounds to land per task (rung 1 vs. a `<KEY>b` fix round vs. a
`<KEY>r` re-plan), and the `evidence report ladder` row grouped by `route,
role, kind, size, class, model, effort, rung` for `route = codex/<kind>/<size>`
(the fence CA3 already accepts). Three tasks is not a sample size that
settles anything; it is enough to write three more rows next to CX2/CX2b's
two and see whether the shape holds on work Codex did not already half-own.

## The three tasks

**(1) OL1 — the flake.** `~/flakes/openai-lab` (already initialised:
`README.md`, `AGENTS.md`, `.gitignore`, one commit) gains a `flake.nix`.
Inputs: `nixos-agent-env` as `git+file:///home/dalhaka/nixos-agent-env?ref=main&rev=d2ad5c79dd4e6cdfa24e0ed20629ae1632908237`
(pinned by exact revision, never a mutable branch reference alone) and
`nixpkgs.follows = "nixos-agent-env/nixpkgs-host"` — the pin
`nixosConfigurations.core` itself evaluates against, so the one module this
flake imports is evaluated the same way the parent evaluates it. Outputs:
`checks.lint` (the parent's own four linters — treefmt, shellcheck, statix,
deadnix — plus ruff, run over the lab's own tree, mirroring
`~/flakes/codex`'s `checks.lint`, which wraps its formatter set the same
way); `checks.lab-vm`, a `pkgs.testers.runNixOSTest` whose machine imports
`nixos-agent-env.nixosModules.evidenceStore` with
`services.evidence-store.enable = true` and whose `testScript` proves, from
inside the machine, that `evidence record-check --name lab --rev <40 hex>
--ok --class unit --src lab` appends one row to
`/var/lib/evidence/checks.jsonl` readable back as JSON with `class: "unit"`
— proving the pin and the module both work, not merely that they evaluate;
`devShells.default` with the four linters, `python3` and `pytest`. A
`flake.lock` ships with the commit.

**(2) OL2 — the extractor, `tools/codex_limits.py`.** Stdlib only, matching
the house rule for `pkgs/evidence` and `tools/factory/seat`. Reads Codex
rollout files named on argv — never a default path under `~/.codex`; the
operator always supplies the paths, the same discipline
`factory-codex-usage.py` already keeps for the session's own rollout.
Filters to `rate_limits` records only and writes one JSONL row per record —
`{ts, session, limit_id, used_percent, window_minutes, resets_at}` — to
stdout; never prints any other field a rollout line might carry. A file that
is not JSONL is refused: exit 2, one line on stderr. This is the missing
producer the spend-telemetry plan named and could not close: "Codex spend |
`out:` no producer — the rollout carries tokens … and a weekly percentage,
no dollars" (`docs/superpowers/plans/2026-09-08-spend-telemetry.md`) and the
judge's row 28, "no task in the plan writes Codex `rate_limits` rows into
any stream, so the row has no producer." `tests/test_codex_limits.py` covers
it with fixtures typed from this shape, one mutant per assertion; `checks.unit`
runs pytest over them.

**(3) OL3 — the runbook, `docs/runbook.md`.** How to bump the pin (edit the
`rev`, `nix flake lock --update-input nixos-agent-env`, `nix flake check`);
how a task is dispatched under `FACTORY_SEAT=codex` (the launch line, the
brief contract, the landing recipe); where the gate record lives (the same
review directory and ledger the DeepSeek seats use, never a lab-local copy).
`checks.unit` gains a grep gate proving the runbook still names its three
required commands.

## Constraints

Brief §3 invariants bind the agent exactly as they bind every seat: nothing
here widens Codex's reach, moves a key, or opens a network path the broker
does not already know about. Codex runs unsandboxed as the operator, under
`--sandbox danger-full-access`, by the 2026-09-07 decision
(`docs/decisions/2026-09-07-codex-stays-an-operator-app.md`, point 4) — that
acceptance is not re-litigated here. Nothing leaves the machine but the
model call itself. No key, token, or path under `/var/lib/secrets` in this
repo or its fixtures. Everything Codex lands stays in `~/flakes/openai-lab`
until the operator says otherwise — no wiring into core, Helm, or the
broker.

**Not in scope.** Wiring the lab into `nixosConfigurations.core` or Helm;
the evidence store's own fence gaining a `codex-limit` kind (that is a
nixos-agent-env task, later, once OL2's shape is measured against a real
rollout); anything that reads or writes `~/.codex` directly from this lab's
own checks (OL2 takes paths on argv; its tests fixture the shape, they never
touch a real session file).

## Open decisions for the operator

1. **OL2's exact record shape is unmeasured, not assumed-and-verified.** No
   `rate_limits` line, nor its field names, appears anywhere in
   `nixos-agent-env` today — `factory-codex-usage.py` reads `turn_context`
   and `token_count` events only, and the codex-driver-arm plan's own
   rollout survey (Assumption 4, 239 lines) names no `rate_limits` kind. The
   spend-telemetry plan and the board both name the shape
   (`limit_id`/`used_percent`/`window_minutes`/`resets_at`) as the thing to
   build toward, but nobody has read it off a real rollout — doing so here
   would mean opening a file under `~/.codex`, which this spike's own
   constraints forbid. OL2's fixtures are typed from the named shape; the
   first real measurement against a rollout the operator points at is owed
   as part of landing OL2, not before it.
