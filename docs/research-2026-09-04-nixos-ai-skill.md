# Research digest — marceloeatworld/nixos-ai-skill, 2026-09-04

One inspection pass plus three adversarial reviews (security, threat-model, value), against a
**read-only clone at HEAD 419d422**. Nothing was installed, executed or fetched; upstream
files were read as data. Every number is measured on that clone unless marked otherwise. A
*skill* is a folder of instructions injected into the model's context, so its files steer the
model as directly as a prompt does.

## 1. What it is

- **Provenance.** 155 commits, HEAD 419d422 (2026-09-04 06:24 UTC, `github-actions[bot]`);
  151 bot, 4 by one person ("Marcelo", last 2026-07-11). **No commit is signed** —
  `git log --format=%G?` returns `N` 155 times. Personal account, no org, no releases, no
  tags.
- **Automation.** One workflow, `.github/workflows/update-references.yml`: daily cron
  `0 6 * * *` (:6), `permissions: contents: write` (:9-10), `actions/checkout@v5` — a
  mutable tag (:20), run `scripts/generate-references.sh` (:23), commit and push gated only
  on `git status --porcelain references/` being non-empty (:25-43). **No model is in the
  pipeline**: no API key, no secret, no model call anywhere. The generator clones four repos
  in the official NixOS org (`generate-references.sh:31-47`) and `cat`s selected files behind
  a 3-line header (:80-121). Nothing in the chain is pinned: mutable action tag, four
  `--depth 1` clones of default branches, unsigned bot commit.
- **Content.** 43 reference files, 23,972 lines / 845,422 chars (~211k tokens); SKILL.md is
  134 lines of routing tables plus a "live fetching" block (:117-134) telling the model to
  pull unpinned `master` from raw.githubusercontent.com. The nixpkgs manual comes from
  **master** but is headed with **stable** URLs.
- **Install/update.** `install.sh --claude` targets `$HOME/.claude/skills/nixos` (:48); with
  no flag, `.agents/skills/nixos` **relative to CWD** (:74-76); `rm -rf "$TARGET"` when
  `$TARGET/.git` is absent (:87); it `source`s the repo-supplied `references/.wiki-version`
  (:98). README advertises `curl … | bash`; the update path is `git pull` (:83).
- **Licence.** None. No LICENSE or COPYING was added in any of the 155 commits, and no
  copyright, SPDX or ShareAlike notice appears anywhere — only a "Credits" list. It
  redistributes the full text of nix.dev, nix-pills, the NixOS manual and the release wiki.
  (Upstream licence identifiers and the GitHub API `license` field: **not verified** here.)

## 2. Benefits (weighted)

- **Medium.** The framing's LLM worry is wrong in the repo's favour: content is mechanical
  `clone` + `cat` of official NixOS-org repos, so there is no hallucination vector; the
  failure mode is staleness and wrong-branch labelling, not invention.
- **Medium.** The generator encodes a working per-repo path selection and exits 1 when an
  expected upstream path disappears (:452-456) — a fail-loud idea worth stealing.
- **Low.** Topic breadth the operator's skill lacks (installation, containers,
  cross-compilation, kubernetes, release process, 20 Nix Pills) — none load-bearing here:
  `kubernetes`, `crossSystem`, `pkgsCross`, `raspberry`, `terraform`, `nix-channel` have
  **zero** hits across nixos-agent-env.
- **Low.** No injection payload at this rev: keyword, invisible-character and header scans
  are clean; the only agent-directed text is the generator's own `DO NOT EDIT MANUALLY`
  header (quoted, not followed) and SKILL.md's live-fetch block.

## 3. Risks per seat

- **HIGH, both — wrong for this pin.** `references/nixos-testing.md` teaches a
  `containers = { … }` / systemd-nspawn VM-test API and a `#test-opt-containers` anchor
  under a `manual/nixos/stable/#sec-nixos-tests` header. At the host pin ac62194c (25.05)
  there are **zero** occurrences of `nspawn` or `test-opt-containers` in the corresponding
  chapters; the pinned example offers `nodes` only. Reconstructed diff against the pinned
  chapters: 389 skill lines absent from the pin, 107 pinned lines missing. Also false at the
  pin: `services.timekpr.enable`, `networking-scripted.target`, `nixos-26.05` channel names.
  This is the API behind `helm-control-vm`, `lane-vm` and `proton-backup-vm`.
- **HIGH, both — unauthenticated instruction swap.** Nothing auto-pulls here; a change lands
  when the operator runs `git pull` or re-runs the installer. The defect is that this routine
  action silently replaces instruction text with no diff and no signature, from a repo whose
  every commit is unsigned and whose pushes are unreviewed.
- **HIGH, both — fails the operator's own gates on day one.** ~1,100 fenced blocks, none
  carrying an executable kind → doctests; SKILL.md 134 lines against the 120-line router cap
  and 27 of 43 references over 250 → budget; `services.timekpr` unresolvable at the pin →
  citations; and no `verified:` pin stamp anywhere.
- **HIGH, dsh — worst chain.** Instruction files reach the model verbatim. The PreToolUse
  hooks *do* gate `bash` and `edit|write`, but hook-guard is a string deny-list (sudo,
  nixos-rebuild, systemctl mutators, six literal spellings of `~/.config/openrouter/key`)
  **with no egress term** — `curl`/`wget` are not denied, web tools are off, and the seat
  runs on the host, not the lane netns, so bash egress is unbrokered; its own docstring calls
  it "a heuristic and an audit trail, NOT a boundary." A second credential at
  `~/.local/share/dsh-openrouter/.credentials.yaml` (0600) matches no spelling in the key
  rule. ~211k tokens also bill the operator's OpenRouter key per read.
- **MEDIUM, both — install path executes repo content.** `install.sh:98` sources
  `references/.wiki-version`; whatever a future commit puts there runs in the operator's
  shell during the installer's "Verifying…" step.
- **MEDIUM, name/path collision.** SKILL.md:2 declares `name: nixos`. The **live** collision
  is on dsh (`~/flakes/dsh-harness/skills/nixos` exists); on Claude it is prospective —
  `~/.claude/skills` does not exist yet, but the spec designates `~/.claude/skills/nixos`,
  exactly install.sh's `--claude` target. Likeliest accident is neither: run with no flag
  from `~/nixos-agent-env`, it drops an untracked skill tree inside the live host flake.
- **MEDIUM, Claude — pre-authorised fetch.** SKILL.md:117-134's live-fetch instruction is
  already allowed by `WebFetch(domain:raw.githubusercontent.com)`
  (`settings.local.json:7`), so unpinned master docs enter context with no prompt.
- **MEDIUM, both — the auto-update is 74% noise and pin-irrelevant.** 114 of 155 commits
  touch only `references/.wiki-version`; 40 touch any `.md`. Cadence is one commit/day. The
  90-day content delta is 200 insertions / 118 deletions across 13 files — ~2.2 lines/day
  against 23,972 lines — sampled as `nixos-26.05` channel prose (this project is flakes-only)
  and a URL fix. And it never carries the class that would justify it: the generator
  sparse-checks out the directory containing release-notes and copies none; across 43 files
  there are **zero** mentions of `mkRenamedOptionModule` or renamed/obsolete options.
- **MEDIUM, both — coverage runs the wrong way.** `NetworkNamespacePath`, `DynamicUser`,
  `X-Restart-Triggers`, `restartIfChanged`, `diff-closures`, `polkit`, `cudaPackages`,
  `linger`, `show-trace`, `why-depends`: zero files each. The operator's 20 eval tasks are
  named after exactly these concepts.
- **MEDIUM, both — licence.** Vendoring the files, or the script, repeats the no-licence
  redistribution inside a repo the operator controls.
- **LOW, both.** The clean injection scan describes 419d422, not the repo.

## 4. Mitigations (cost → residual)

| Measure | Cost | Residual |
|---|---|---|
| Never run install.sh, scripts/, or `curl \| bash`; delete the clone when done | zero | kills the `source .wiki-version` gadget, the `rm -rf $TARGET`, the CWD-relative install; nothing about content. "Read-only clone" is not a control — non-execution is |
| Do not adopt on dsh whatever is decided for Claude | zero; matches the recorded seat separation | removes the only chain with no permission prompt in it |
| Vendor `references/*.md` alone at a pinned rev + narHash, outside every skill root, loaded by nothing | ~1h (one input, a lock-guard-shaped assertion, a file-type check) | risk collapses to the bump moment; gives up auto-update entirely; licence problem remains |
| Re-derive upstream text from the pinned nixpkgs in the store (refresh.md §4) | near zero, offline | removes the master-vs-stable class **and** the licence question — terms flake.lock already declares |
| If adopted anyway: rename to `nixos-docs-upstream`, assert the name, exclude from the dsh re-sync recipe | one sed + one assertion | two near-identical routers still compete; which wins is not measured |

## 5. Recommendation

**Claude seat — do not adopt.** Not wholesale, not cherry-picked as pasted text. Installing
a stranger's auto-pulling repo as a skill carries untrusted text across the data/instruction
boundary by design, and here it would also ship master-labelled-stable guidance for the exact
VM-test API three live checks depend on, fail four of the operator's own gates, and pull
unpinned docs through an already-allowed WebFetch domain.

**dsh seat — do not adopt, unconditionally.** Verbatim instruction delivery, deny-list hooks
with no egress term, a second unguarded credential file, unbrokered host bash, and per-token
billing on the operator's key. A daily unsigned upstream is the wrong input to that stack.

**The "auto-updating skill" idea, on its own.** The appealing part, and the part that does
not work in this form. Under *pin every input to an exact rev*, auto-updating can only mean
**auto-PROPOSE**: a job computes a diff and a lock bump, and nothing a session reads changes
until the operator accepts it. Worth building in the operator's own skill repo — built fresh,
not ported (the script is unlicensed), since `refresh.md` §2-§3 is already a *better*
detector: it goes red semantically at the new pin (doctests throw on removed options;
citations list option paths gone from the pin's option set) rather than diffing prose. Two
additions earn their keep: (a) extend the manifest to `rename.nix` and
`release-notes/rl-*.section.md` in the pinned nixpkgs — the deprecation class this pipeline
structurally cannot carry, and the one `mkRenamedOptionModule` shims keep green in
`citations`; (b) copy the fail-loud idea — exit non-zero when an expected upstream path
disappears, so a reorganised manual breaks the check instead of going stale. Do **not**
record installation/containers/cross-compilation/kubernetes/release-process as coverage gaps
(zero hits for those terms here; the spec says there are no human readers). File a decision
naming rev 419d422 and the numbers above.

## 6. Unverified

- Answer quality for either skill. **No eval has been run** — 20 tasks exist at
  `~/flakes/nixos-skill/evals/tasks/`, `evals/results` does not. The case above rests on
  coverage, pin-correctness and update-signal measurements, not scores.
- Cross-skill routing when two `nixos` descriptions both match.
- Upstream licences of nix.dev / nix-pills / release-wiki, and the GitHub API `license`
  field — network facts, not checkable from the offline clone.
- Whether `main` has branch protection or required review.
- Byte-verification of the other 42 reference files (two were diffed against the pin).
- Fenced-block count: ~1,076 by pairing, ~1,206 by one reviewer's toggle count — immaterial;
  neither includes an executable kind.

## 7. Appendix — skeptic verdicts (one line each; corrections applied above)

- **Evidence/security:** verdict survives; four figures were wrong as worded — the 801-line
  diff arithmetic, the fence count, "both seats" for the path collision, the network-derived
  licence claims; added that no link in the update chain is pinned.
- **Threat-model:** verdict survives; "auto-update writes to both seats" overstates (a
  `git pull` does), "hooks gate tools, not context" is wrong (they gate bash and edits — as a
  deny-list with no egress term), the missed sink is `source references/.wiki-version`, and a
  second credential file is unguarded.
- **Value:** verdict survives and is stronger on value than on security — 74% metadata
  bumps, ~2.2 content lines/day, zero coverage of this project's vocabulary; refuted the
  draft's "record these coverage gaps" and "port the generator" steps.
