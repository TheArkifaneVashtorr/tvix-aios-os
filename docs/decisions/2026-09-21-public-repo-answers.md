# The public repo — the operator's answers (2026-09-21)

Decided by the operator on 2026-09-21, in-session, through the multiple-choice
dialog, on the eight answer-first items of
`docs/research-2026-09-21-tvix-aios-loose-ends.md` (the other 69 items take
the defaults printed under them until the operator says otherwise). Recorded
here so a reset does not lose them; each answer is the decision the phase-1
spec and the publish gate cite. The operator's own words are quoted verbatim.
Two answers depart from the document's recommendation; §2 lists them.

## 1. The answers

| # | Topic (loose-ends items) | Answer |
|---|---|---|
| 1 | Where the code lives (15, 18, 22, 28) | **make this repo public** — `nixos-agent-env` is the public repo; the fork `TheArkifaneVashtorr/tvix-aios` stays an exact upstream mirror with nothing committed into it, and becomes a flake input where the public tree needs tvix |
| 2 | Licence (19, 20) | GPL-3.0 for the public repo, and a `LICENSE` file in this repo before any file moves |
| 3 | The `qwen-intl` account (26) | the operator's own: "that was me using Qwen's coding agent"; the two branches and two PRs are the operator's drafts, no access problem; they do not compile, and closing them stays the recommendation (25a) |
| 4 | The public task list (41, 43, 45) | **a filtered copy of the private queue** — the existing list, exported through a field allowlist (key, title, status, size, acceptance check names); models, costs, run ids, seat units, home paths and plan bodies withheld |
| 5 | History (21) | fresh start: the public history begins at one commit of the cleaned snapshot; the private history and every commit message stay here and are never published |
| 6 | The personal workspace (31, 33, 37, 38) | withheld: `docs/board/`, `docs/reviews/`, the handoffs, `hosts/`, `keys/`, `docs/ledger/keys.toml`, and the free-text note fields of the ledger; published: modules, packages, tools, tests, the flake, `docs/concepts/`, `docs/decisions/`, `docs/runbooks/` |
| 7 | The other people (4, 5, 14) | a few people the operator names and invites; read and PRs only; nobody else gets write; widened only after the first outside task lands |
| 8 | Phase 1 (62, 63) | the publish gate — a flake check that fails the build on any private string or any path outside the export allowlist, red on a fixture then green — plus both `LICENSE` files, the export allowlist, the decision files and the three broken citations fixed; nothing pushed; the acceptance test is one `nix build` of the check |

Two further words from the same dialog:

- **Design approved:** "Yes, write the spec" — the spec is
  `docs/superpowers/specs/2026-09-21-publish-gate-design.md`, size M.
- **The planning lane:** asked whether the plan workflow runs on the approved
  spec as a seat, the operator corrected the framing — "You are not using open
  router, fable via anthropic oauth [this chat]". Planning runs in this chat as
  Workflow agents on the operator's Anthropic login; a plan run is never a seat
  or a lane unless the operator launches one.

## 1a. The plan's three questions (answered the same day)

The plan `docs/superpowers/plans/2026-09-21-publish-gate.md` (judged 39/42,
dispatch, revision 0) raised three classification questions the spec's §4
lists left open; the operator answered each with the recommendation:

| # | Paths | Answer |
|---|---|---|
| 9 | `docs/research-*.md`, `docs/context/*`, `docs/bugs/*` (the orchestrator's working record, 34 files) | **withhold** — the same class as the board and the reviews |
| 10 | `media/*` (the absorbed ComfyUI subsystem, 141 files) | **publish**, minus its own `docs/reviews/*`, `docs/superpowers/plans/*`, `docs/OPERATIONS.md` and `research-*` files; the 16 files carrying a home path start in `pending` |
| 11 | the ten ledger files with no free-text note field (`claims`, `bugs`, `patches`, `plan-defects`, `repos`, `subsystems`, `task-classes`, `areas-grandfather`, the two price CSVs) | **publish** — the four note-field files (`plan-status`, `task-status`, `rules`, `routing`) stay withheld |

## 1b. Narrowings made at the gate (the orchestrator's, on a reviewer's finding)

| # | Path | Row it narrows | Why |
|---|---|---|---|
| 12 | `docs/concepts/2026-09-02g-hardware-identity-ledger.md` | row 6 publishes `docs/concepts/*` | the file carries one of the two YubiKey serials in prose; the Opus gate on PG2 (`docs/reviews/2026-09-21-opus-review-pgw2-PG2.md`, MINOR) asked that it be withheld rather than left in `pending`; PG2b withheld it, enumerating the other 36 concept files under `publish` so that a new concept file fails the gate as unclassified until it is placed |
| 13 | `nixosModules/lanAccess.nix`, `media/docs/runbooks/media.md` | row 6 publishes modules and runbooks | both carry the host's LAN address (an option `example` and a runbook sentence); the address is now the sixth deny literal and both files sit in `pending` until a task replaces the example with a documentation-range address and the runbook with a placeholder |

## 2. Departures from the recommendation

| # | Recommended | Decided | What it changes |
|---|---|---|---|
| 1 | a fresh public repo beside the fork, this repo private with no remote (15d, 22a, 28a) | this repo is the public repo | the export is no longer optional: every publish is a snapshot of this tree through the allowlist and the gate, and the gate is the only thing standing between the private record and the public history |
| 4 | a new list of public-only tasks (41a) | a filtered copy of the existing queue | the public renderer is a real phase-2 deliverable (a field allowlist in `tasks.py`'s renderer, gated by the same check), and item 74's contradiction — held keys rendered as ready — must be resolved before the first export |

## 3. What this settles on the record

- The rule that governs this case (item 16): neither `claude-dsh-separation`
  nor the 2026-09-09 absorption rule was written for a public repo; this file
  is the third-case decision. The fork is separation-governed (a mirror, its
  own git, crossings only as a flake input); this repo's public face is a
  one-way export of itself.
- Publication is the operator's per-case action, on the same footing as a
  switch (items 57–59): no agent holds a GitHub credential, no broker allow
  list widens, the operator pushes by hand. The gate exists so that the push
  cannot carry what the operator did not choose to publish.
- Operator-only steps carried by this decision: close the two PRs on the fork;
  name the invitees; create the public remote and push the first snapshot;
  the host memory directory outside git stays where it is (item 35a).
