# Decision 2026-09-02 — media flake: nix-native, no container

**What the factory found (media T3, Opus gate, unapproved at the cap):** the
chosen image `mmartial/comfyui-nvidia-docker` is a bootstrapper — the digest
pins only the Ubuntu/CUDA base; its entrypoint clones ComfyUI from GitHub at
whatever `main` is on first start, builds a Python environment from PyPI,
installs ComfyUI-Manager (security level `normal`), and needs setuid to
switch users. That contradicts the approved spec on "the digest is the pin",
"nothing fetched at runtime" and the dropped capabilities.

**Operator, 2026-09-02 ~23:00:** first "build our own image with Nix", then,
interrupting: "I don't need comfyui to be containerized but it needs the
memory architecture from our base image" → "same Claude memory setup as the
base."

**Recorded:** ComfyUI runs **nix-native** — pinned in the Nix store at build
time, nothing fetched at runtime, no Manager — as a hardened systemd service
(dedicated user, `ProtectSystem=strict`, GPU devices only, no capabilities)
inside the broker namespace `egress-media`, loopback via the socket proxy.
The factory's manifest, fetch tool, fetch confinement, socket proxy and
broker credential injection are kept. The packaging route (utensils/comfyui-nix
pinned, a newer nixpkgs, or own packaging) is chosen from the Sonnet research
digest docs/research-2026-09-02-comfyui-nix-native.md → media spec rev 3 →
a rework plan for T3. Host wiring of media waits for that rework.

**Also recorded:** every flake is a builder with the base's Claude memory
setup — its own CLAUDE.md with the house rules, board, memory index, and a
separated memory directory backed up on its own
(docs/decisions/2026-09-02-memory-per-flake.md).
