# Decision 2026-09-21 — the card tool reaches CivitAI on two hosts, one per world

**Status:** adopted on the operator's word, 2026-09-21, answering open question 1
of `docs/superpowers/plans/2026-09-21-lora-cards-and-coupling.md` and §9.1 of
`docs/superpowers/specs/2026-09-21-lora-cards-and-coupling-design.md`:
"do both, normal for SFW, red for NSFW. They can test in SFW and they are
mirrors of one another." Append-only; supersede with a dated entry if it
changes. Extends `2026-09-15-media-allowlist-huggingface.md`, which set the
shape: literal hosts, named per unit, on the media broker instance.

## What was decided

| world | host the card unit may reach |
|---|---|
| sfw | `civitai.com` |
| nsfw | `civitai.red` |

Both join the media broker's allowlist; neither is a wildcard and no other
CivitAI host is allowed. The plan's recommendation was `civitai.com` alone,
with `civitai.red` named on the board as a third-party mirror; the operator's
answer supersedes that on the ground that the two are mirrors of one another,
which makes the SFW world a test surface for a tool that will run against
both.

## Why it is two hosts and not one

The operator's stated use is rehearsal: the card pass can be exercised end to
end in the SFW world, on the normal host, before it runs in the NSFW world at
all. That only works if the SFW world has a host of its own — a single
allowlisted host shared by both worlds would make every rehearsal a live run
against the same endpoint the NSFW world uses.

## What this does not decide

Whether the mirror serves identical data. "They are mirrors of one another" is
the operator's premise, not a measurement, and no task in the plan compares a
response from one host against the other. If a card built from `civitai.red`
differs from the same model's card on `civitai.com`, nothing in this decision
detects it. Worth a probe in GN49 rather than an assumption.

The trust boundary is unchanged and is not softened by allowing a second host:
typed scalars only cross into the manifest (`category`, `trigger`, `requires`,
the version id), free text stays in the per-model sidecar, and nothing an
uploader wrote on either host reaches the author's context or a prompt. Two
hosts means two sources of attacker-chosen trigger tokens, not two levels of
trust.

## How an audit measures it

`grep -n 'civitai' hosts/core/*.nix` names exactly these two literals and no
wildcard; the card unit's per-world host comes from its world's setting rather
than a shared default; and `instances.media.allow` gains these two entries and
nothing else.
