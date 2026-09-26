# Decision 2026-09-15 — the media broker allows huggingface.co for the fetch unit

**Status:** adopted by the orchestrator on the operator's word ("you should have an
api token … to fetch models with") at 11:35 CDT, session 26. Amends
`2026-09-06-generation-lab-brainstorm.md` ("models and assets arrive by hand for
now; a download-only broker allowlist for civitai.com later"). Append-only;
supersede with a dated entry if it changes.

## What changes

`services.egress-broker.instances.media.allow` on core goes from `[ ]` to exactly
`[ "huggingface.co" "us.aws.cdn.hf.co" ]` — the repository host and the xet CDN
host its `resolve/main/…` downloads 302 to (measured 2026-09-15 on three URLs;
no third host). `hosts/core/lanes.nix` carries the list; the check
`core-comfyui-wiring` asserts it exactly and asserts `inject == { }`.

The consumer is the media flake's `comfyui-fetch-models.service`: a hand-run
oneshot inside netns `egress-media`, `--only` the twelve Krea-2 manifest rows
(`services.comfyui.models.only`, asserted non-empty and manifest-valid by the
same check), sha256-verified before a file is placed, no partial file kept.

## What does not change

- No credential at this instance. Krea-2 (`Comfy-Org/Krea-2`) is public and
  ungated. A Hugging Face token for gated repositories, if ever wanted, is a
  root-owned file outside the store named by `services.comfyui.models.hfTokenFile`,
  placed by the operator; civitai.com stays closed (`models.civitai.enable = false`).
- The inference process is offline by construction: `comfyui.service` carries
  `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1` and
  no proxy environment (the fetch unit keeps its own).
- The matcher is host-exact (no suffix or wildcard); CONNECT is 443 only; every
  request writes an audit row under `/var/lib/egress-broker/media/`.

## Residual exposure, stated

Anything running in `egress-media` as the `comfyui` user can issue any method and
any path to the two hosts; the allowlist is host-level and `denyPaths` only
subtracts. Anonymous exfiltration to Hugging Face still needs a token, which the
instance does not hold; everything else on the internet stays refused with a
logged 403. Accepted as the price of fetching 16 GiB through the chokepoint
instead of around it.

Why: the operator wants the Krea-2 models fetched, not carried by hand; the
brief's invariant 3 is kept (one chokepoint, logged, refusable), and the record
of what is allowed is a diff, not a memory.
