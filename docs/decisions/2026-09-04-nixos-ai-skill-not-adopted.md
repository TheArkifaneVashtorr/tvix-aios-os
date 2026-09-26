# Decision — the third-party `nixos-ai-skill` is not adopted; its update idea becomes auto-propose (2026-09-04)

**Question (operator):** adopt https://github.com/marceloeatworld/nixos-ai-skill, an
auto-updating NixOS skill maintained by an anonymous account, for the Claude seat and
the DeepSeek (dsh) seat? "Automatically updating via GitHub Actions is a risk, using
another anonymous person's repo is a risk, but an auto-updating skill sounds good."

**Inspected:** revision 419d422 (2026-09-04), cloned read-only, never installed. Digest:
`docs/research-2026-09-04-nixos-ai-skill.md` (an Opus inspection, three lenses, three
adversarial skeptics; every structural finding confirmed against the clone).

**Facts that decide it:** the pipeline is mechanical (clone + concatenate four official
NixOS-org repos; no model, so hallucination is not the risk); the content is nixpkgs
*master* shelved under stable-looking URLs and teaches a VM-test API absent at this
host's pin ac62194c, the API three live checks here use; 155 of 155 commits are
unsigned and bot-authored; the installer's update path is an unauthenticated `git pull`;
no licence in any commit; it fails four of this repo's own gates (pin every input to an
exact rev; doc-tested examples; citation checks; the review checklist); the auto-update
is ~74 % metadata bumps and about 2.2 content lines a day, and it drops the release
notes it fetches, so option renames never reach the skill.

**Decision:**
1. **Claude seat — not adopted**, neither wholesale nor as pasted text: it carries a
   stranger's text across the data/instruction boundary by design and would ship
   master-labelled-stable guidance for the exact API live checks depend on.
2. **dsh seat — not adopted, unconditionally**: verbatim instruction delivery, deny-list
   hooks with no egress term, a second credential file, host bash, per-token billing on
   the operator's key. A daily unsigned upstream is the wrong input to that stack.
3. **The idea is kept as auto-PROPOSE in the operator's own skill repo**
   (`~/flakes/nixos-skill`), built fresh (the third-party script is unlicensed): a job
   computes a diff and a lock bump; nothing a session reads changes until the operator
   accepts it. Its `refresh.md` §2–§3 is already the better detector (doctests and
   citation checks go red semantically at a new pin). Two additions earn their keep:
   extend the manifest to `rename.nix` and `release-notes/rl-*.section.md` in the pinned
   nixpkgs (the deprecation class the third-party pipeline cannot carry), and fail loud
   when an expected upstream path disappears.

**Falsifiable acceptance for (3):** a pin bump that renames an option produces a proposed
diff naming the rename before any session sees it; a removed upstream manual path turns
the refresh check red.

**Not recorded as coverage gaps:** installation, containers, cross-compilation,
kubernetes, release process — no human readers (spec), zero hits here.
