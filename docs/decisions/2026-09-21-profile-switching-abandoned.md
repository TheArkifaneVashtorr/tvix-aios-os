# Profile switching is abandoned; isolated per-program space replaces it (2026-09-21)

Taken by the operator, 2026-09-21: "all the documentation and wiring for
profile switching — the concept is abandoned and has led to a few wasted
tokens. Having the programs in isolated space is actually better."

## Decision 1 — whole-system profile switching is not the shape

The Helm does not switch the machine between NixOS profiles, and nothing
in this repo carries wiring, options, checks or instructions for doing so.
A program that needs a different environment gets an isolated space of its
own — a lane, a netns, a user unit with its own sandbox — not a different
system-wide configuration the whole host must move into and out of.

Why: switching the system to run one program is the largest possible blast
radius for the smallest possible gain. Every program that wants isolation
pays for it in a mechanism that stops every other program. Isolated space
composes; a profile switch does not.

## Decision 2 — what the measurement says

`helm-switch@` has been invoked **twice**, both on 2026-09-04 at 22:49,
seconds apart, `helm-switch@gaming` then `helm-switch@base` — the
acceptance drill of the day it landed. Nothing in the 17 days since
(journal, read 2026-09-21). It is wired, buildable, gated by polkit, pinned
by seven flake checks and a VM test, documented in two runbooks, and has
never once been used to do work.

The cost was not the switching. It was that the concept kept being
maintained: 37 files carry its wiring, 112 mention it, and every agent that
read the Helm v1 spec or `docs/runbooks/helm-v1.md` learned a procedure the
operator does not use.

## Decision 3 — the gaming specialisation stays, and is not this

> **Superseded 2026-09-25 (operator).** The gaming specialisation is retired too: task
> PL14 (`docs/superpowers/plans/2026-09-11-platform.md`) absorbs the gaming flake under
> `gaming/` unwired and removes the specialisation and its input, so the public flake
> carries no private input. Gaming returns as an app in its own isolated space (brief §2,
> "Product direction"), not as a system profile. The text below is kept for the record.

Measured 2026-09-21 before deciding: `specialisation.gaming`
(`hosts/core/default.nix:45-53`) is a plain NixOS specialisation that names
Helm nowhere. Steam, Proton-GE, gamescope, gamemode and MangoHud live
behind `programs.gaming.enable` from a separate flake input. The NVIDIA
drivers and CUDA are at the **base** level (`hosts/core/graphics.nix:6-12`),
not in the specialisation.

It has two routes in, neither touching `helm-switch@`:

* the boot menu — `nixos-generation-78-specialisation-gaming.conf` exists
  for the current generation, built 2026-09-21 (`bootctl list`);
* direct activation — `/run/current-system/specialisation/gaming/bin/switch-to-configuration test`,
  which is what `helm-switch.sh:62-66` wrapped and what
  `docs/runbooks/switch-helm-gaming.md` documented before Helm v1 existed.

`helm-switch@` was a convenience over a mechanism that works without it.
Removing the convenience removes nothing.

## Decision 4 — the read-only Helm page survives

`nixosModules/helm.nix:859-909` bundles the `helm-switch@` unit in the same
`mkIf` block as `helm-serve` (the 7700 page) and the `static-web-server`
override. The removal **extracts** the switch from that block; it does not
delete the block. The page stays, per the standing decision that the Helm
is the only dashboard
(`docs/decisions/2026-09-17-data-streams-surface-on-helm.md`).

## Decision 5 — wiring and instructions go, history stays

Operator, 2026-09-21: "delete the wiring and instructions, leave the
history."

Deleted or rewritten: live module wiring, host config, the `helm-switch.sh`
template, the Python read paths, the checks that exist solely to pin it, the
`offers.profiles` declaration contract, and the two runbooks that tell
someone to use it.

Left exactly as written: every landed plan, dated decision, spec, concept,
review, research packet and board entry that mentions it — roughly 60 files.
Those are the record of what was decided and when. Rewriting them would
falsify the record rather than remove a feature; this file supersedes them.

`docs/decisions/2026-09-02-helm-is-the-switch.md` is the decision this one
reverses, and stays in place.

## What this does not decide

Whether `services.helm.control` survives as a namespace for the page's own
configuration, or is removed entirely with its surviving fields rehomed.
That is a code-shape call for the plan, not a product call.

The `uid1000-can-switch-profile` claim
(`docs/ledger/claims.toml:184-193`) becomes moot and needs a disposition —
withdrawn against this decision, not silently deleted.
