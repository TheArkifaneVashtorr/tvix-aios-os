# Concept 2026-09-03b — the operator's seat is the lane's harness minus the lane

**Class:** operator tooling / budget instrument.
**Status:** built (`dsh-openrouter`, pkgs/dsh-openrouter; first use 2026-09-03).

**Origin (2026-09-03, evening):** the Claude weekly limit sat near its cap
with four days to the reset, and the operator asked for "a working dsh
agent, not even in the VM, just in general, so I can work using OpenRouter".
The lane already ran the DeepSeek Harness as a batch job — snapshot in,
diff out, every byte through a namespace and a broker — which is the right
shape for a factory and the wrong shape for a person: a task file, a submit,
a wait, a `jq .diff`, a `git apply`. What the operator needed was the same
pinned harness, in the directory they are in, talking to DeepSeek, now.

**Idea:** ship the harness twice from one package and let the *contract*
travel, not the plumbing. `dsh-openrouter` boots `pkgs/dsh` on the host with
a route overlay to OpenRouter, and keeps the parts of the lane that are about
*data* rather than *transport*: the refusal list (Claude memory, mounted and
stored baskets, `~/strategy`, Helm, broker, lane spools, secrets — it will not
start inside any of them, and checks that before it reads the key), the
key-by-environment-variable seam (a file that is the operator's alone, 0600,
never printed; or `OPENROUTER_API_KEY`), telemetry off, the web-search/fetch
tool off, the browser UI on loopback with a token. What it drops is the
namespace and the broker — and says so on every launch: zero-data-retention
is an account setting here, not a stamp on each request. The harness's own
sandbox (bubblewrap, then Landlock) confines tool calls to the working tree;
danger-full-access is a per-launch opt-in. Two proofs make it real: a bats
suite that boots the real harness against a scripted fake upstream on
loopback (the key travels as `Authorization: Bearer`, the model is the one
asked for, the answer comes back), shown to fail under two mutations; and a
by-hand tool loop where the bash tool wrote inside the workspace and its
write to `/tmp` never reached the host.

**Payoff:** DeepSeek does the day-to-day editing for cents while the Claude
budget is spent on judgement — the factory model policy's split, applied to
the operator's own hands. The same overlay shape serves a future `lane-shell`
(the interactive lane: a unit with a pty in the broker's namespace) without
changing what the operator types.

**Dependencies:** pkgs/dsh at 0.1.2-rc.1 (its web profile needs Node's
`--expose-internals` on the command line; a pin bump re-checks that);
bubblewrap on the host; the operator's OpenRouter account settings (ZDR,
training opt-out) — docs/runbooks/lanes.md.

**Earliest landing:** landed 2026-09-03 (`packages.dsh-openrouter`, devShell,
`checks.unit`); the interactive lane is a later concept.
