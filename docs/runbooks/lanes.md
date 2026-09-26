# Model lanes — the OpenRouter/DeepSeek lane

A "lane" (`services.model-lanes`, `nixosModules/modelLane.nix`) is a broker-
fronted path to one remote model, for `permitted`-class work only. This repo
currently declares one: `openrouter` → `deepseek/deepseek-v4-flash`
(`hosts/core/lanes.nix`), decided in
`docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md` and
designed in
`docs/superpowers/specs/2026-09-03-data-and-models-system-design.md` §8. The
module and client landed 2026-09-03 (`f5b20d8`, `f23fcdc`). The job unit,
`lane-<name>@.service`, is `wantedBy` nothing — jobs run one at a time,
only when you start one. The broker instance backing it is a different
story: `hosts/core/lanes.nix` also declares
`services.egress-broker.instances.openrouter`, and that *does* come up on
its own at every switch, same as any other broker instance — see
`docs/runbooks/switch-helm-gaming.md` §7 for the two units, and for the
firewall-backend side effect (declaring a broker instance turns on the
nftables backend for `networking.firewall`, replacing `firewall.service`
with `nftables.service`) that switch measured.

## What a lane is, and what it never does

A lane is an agent with an egress class, same shape as `lib/mkAgent.nix`.
Three invariants, each enforced in more than one place:

- **No agent, script or lane process ever holds the OpenRouter key.** The
  key lives only in `/var/lib/secrets/openrouter-key`, read by the egress
  broker (`nixosModules/egressBroker.nix`) inside its own netns, and
  injected as the `Authorization` header on the way out. `lane-run.py`
  (`pkgs/lane/lane-run.py`) builds every request with **no** `Authorization`
  header — see its module docstring — and the "agent" job kind hands the
  Claude CLI a dummy `ANTHROPIC_AUTH_TOKEN` the broker overwrites. Nothing
  in the job file, the unit's environment, or the ledger ever carries the
  real key.
- **Only `openrouter.ai` is reachable from the lane's netns.** The lane's
  broker instance (`services.egress-broker.instances.openrouter`, rendered
  by the module from `hosts/core/lanes.nix`) has an allowlist of exactly
  that one host — asserted at eval time
  (`nixosModules/modelLane.nix`'s "allow list must be exactly `[ host ]`"
  check) and proven at the packet level by `checks.lane-vm`
  (`tests/integration/lane-vm.nix`), which runs the real broker + netns +
  nftables stack in a VM against a fake `openrouter.ai` and shows nothing
  else is routable from inside. `lane-<name>@.service` runs with
  `NetworkNamespacePath` pointed at that netns and
  `RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX"` — it has no other
  way out.
- **Only `permitted`-class data reaches it.** `services.model-lanes.<name>.
  allowedClasses` accepts only `[ "permitted" ]` — anything else fails the
  build (`checks.lane-assertion-negative` is the negative proof: a lane
  declared with `allowedClasses = [ "local-only" ]` does not evaluate).
  `lane-run.py` checks the job's own `class` field again at runtime as a
  backstop, refusing (exit 3, a result file with an `error` key, no
  request sent) anything that isn't exactly `"permitted"`. Per the decision
  record: this repo, `~/flakes/*`, their factory transcripts, eval seeds/
  results and rollups may reach the lane. Claude memory directories,
  baskets, `~/strategy` economics/income data, Helm history, broker audit
  logs and backup state are `local-only` and must never be handed to a lane
  job — `lane-submit`'s `--repo` flag for the `agent` kind refuses paths
  under (or equal to) `~/.claude`, `~/.codex`, `/run/baskets`,
  `/var/lib/baskets`, `~/strategy`, `/var/lib/helm`,
  `/var/lib/egress-broker`, `/var/lib/lanes` and `/var/lib/secrets`
  outright, and refuses any symlink inside a
  permitted `--repo` whose target resolves outside it
  (`pkgs/lane/lane-submit.py`, `FORBIDDEN_REPO_PREFIXES`), but that is a
  convenience check, not the control. The control is upstream of the flag:
  every job template in `tools/lane/jobs/` and every hand-run `lane-submit`
  call passes `--class permitted` because **the operator (or the script
  running on the operator's behalf) is the one asserting the class of
  whatever it hands over** — the flag records a claim already made by the
  person choosing what to submit, not a check the lane can make on your
  behalf. Point `--repo` or stdin at anything you have not already
  classified as `permitted` and this control does nothing for you.
- **Nothing outside the lane's own network namespace can even reach the
  proxy.** The broker's listen port is bound in the host's namespace
  (`hostAddress:listenPort`, e.g. `10.100.3.1:3131`), but the first rules of
  its `input-<name>` nftables chain drop every packet to that port whose
  input interface isn't the lane's own veth (`nixosModules/egressBroker.nix`)
  — a `curl -x http://10.100.3.1:3131 ...` or a raw `/dev/tcp` connect from
  an ordinary host process (any uid, not just non-operator ones) is refused
  before it ever reaches mitmproxy, so nothing on the host can ride the
  broker's credential injection except a process actually inside
  `/run/netns/egress-openrouter`. Proven by `checks.integration`
  (`tests/integration/broker-vm.nix`): a host-namespace `curl` through the
  proxy and a host-namespace raw TCP connect to the port both fail, while
  the in-namespace request still succeeds. This rule is rendered for every
  broker instance, not only this lane's — the same fix landed for Cowork's
  instance too.
- **The job unit cannot see anything the lane must never touch.** The
  `lane-<name>@.service` template's `InaccessiblePaths` makes these paths
  `ENOENT` for the running job, not merely read-only: `/run/baskets` and
  `/var/lib/baskets` (decrypted basket contents — invariant 1, a mounted
  basket must not be stat-able by an unrelated process), `/var/lib/helm`
  (Helm's collected host state), `/var/lib/egress-broker` (the broker's own
  audit log and its CA's private key — the public-only CA bundle the lane
  needs for TLS is published to a sibling path outside this tree instead),
  and `/var/lib/secrets` (every provider key file, including the one this
  lane's own broker instance injects). `/home` is listed too, on top of
  `ProtectHome`, so the list reads as the complete contract rather than
  "whatever ProtectHome happens to also cover". `ProtectSystem = "strict"`
  hides the rest of the filesystem read-only; `InaccessiblePaths` is what
  makes these specific trees invisible rather than merely unwritable.

## The operator's seat is a lane too

The operator's interactive DeepSeek seat is now a lane of its own:
`services.seat-lane` (`nixosModules/seatLane.nix`) declares the broker instance
`seat` over 10.100.4.x, and `seat@<id>` runs the seat as the operator inside
the `egress-seat` namespace, with the key never in the unit — the broker
injects it from the root-only file at egress. The commands live in
`docs/runbooks/seat.md`; it is **not** the seat *driver* under
`tools/factory/seat/` (see below), which submits headless jobs to it.

## The per-model ZDR exception (the seat's planning prompts)

Every chat request to the seat's broker is stamped
`provider: { zdr: true, data_collection: "deny" }` — the data policy described
in the next section, copied verbatim from the model lane. There is exactly one
named exception, declared in `nixosModules/seatLane.nix` (IS4):

- **What it is:** the seat instance's `bodyPatch.<host>.exceptModels` carries
  one id, `anthropic/claude-fable-5.1`. A request whose body names that model
  exactly is forwarded with its body *unpatched* — the broker skips the
  zero-data-retention merge for it and writes an audit line (`reason:
  zdr-exception`, naming host, path and model; the key is never logged). It is
  fail closed: no prefix or glob matching, so `anthropic/claude-fable-5.1-
  preview` is still patched, and a body with no model, a non-string model, or
  one that does not parse is patched (or denied) exactly as before.
- **Why it exists:** the operator's decision of 2026-09-10. The ZDR patch is
  why every Anthropic-model endpoint on the lane returns `HTTP 404 — No
  endpoints found matching your data policy (Zero data retention)`; the
  planning prompts — the seat's own context blocks — are the one payload the
  operator accepted routing without ZDR, and no other model is acceptable.
- **What it costs in retention:** for Anthropic endpoints, a request that
  skips the patch is retained by the provider for 30 days instead of nothing.
  Every other request, from every other model, on this lane keeps ZDR and the
  training opt-out unchanged.
- **How to remove it:** delete the `exceptModels = [ … ];` line (and the
  comment above it) in `nixosModules/seatLane.nix`'s seat `bodyPatch`.
  `seat-eval` asserts the list is exactly that one id, so widening it — or
  copying it onto another broker instance — fails the build; removing it
  reverts the seat to the all-requests-ZDR behaviour.

## The key file and the tmpfiles rule

`/var/lib/secrets/openrouter-key` was created by the operator, root-only,
before this lane existed (board: 2026-09-03, `root:root 0400`, 73 bytes,
prefix verified, never displayed). The lane module's own tmpfiles rule
resets it to `0440 root:egress-broker` at every switch —

    z /var/lib/secrets/openrouter-key 0440 root egress-broker -

— so the broker's own user can read it and nothing else can. The module
asserts `keyFile` is never a `/nix/store` path (a store path would copy the
secret into the world-readable store); this repo never contains the key
itself, only the path to it. Vault of record: Proton Pass.

## OpenRouter account settings — set these by hand, and record the date here

Two account-level settings on openrouter.ai, on top of what every request
already carries (next section).

- **Zero Data Retention, "Non-frontier" model group** (covers DeepSeek):
  OpenRouter dashboard → Settings → Privacy. Routes only to provider
  endpoints that store nothing of the request.
  https://openrouter.ai/docs/guides/features/zdr
- **Training opt-out**, paid-models toggle: same Settings → Privacy page.
  https://openrouter.ai/docs/guides/privacy/provider-logging

Date set: **2026-09-04** (operator, board entry "O1 DONE", 20:14 CDT).

**Why the lane also asks for both on every request**, instead of trusting
the account setting alone: an account toggle is one click, made once, that
nothing in this repo can verify stayed on — a UI bug, a support agent, or
the operator's own future self resetting it would silently widen what a
provider retains, with no build-time or run-time signal here. The
per-request `provider: { zdr: true, data_collection: "deny" }` block
(`pkgs/lane/lane-run.py`, `run_chat`) is the belt to the account setting's
braces: OpenRouter's own docs note a request can only turn ZDR *on*, never
off, so the two together can't be silently weakened to less than the
stricter of the two. `lane-run.py` sends this block unconditionally — there
is no job field that can remove or override it.

## Submitting a job

Two operator/orchestrator binaries, both from `pkgs/lane/lane-submit.py`
(`nixosModules/modelLane.nix` wraps the same file twice):
`lane-submit <lane> ...` writes the job file and starts it; `lane-wait
<lane> <job-id>` polls for and prints the result. `lane-submit` itself
blocks until the job unit finishes (it's a `systemctl start` on a oneshot
unit) and only then prints the job id, so `lane-wait` right afterward
returns immediately — it's there for a second terminal, a script, or a job
you fire and check on later.

**A chat job** — a plain OpenAI-style messages array on stdin:

    echo '[{"role":"user","content":"Reply with the single word OK."}]' \
      | lane-submit openrouter --kind chat --class permitted \
          --model deepseek/deepseek-v4-flash
    # prints a 12-char job id, e.g. 3f9a1c7e2b04

    lane-wait openrouter 3f9a1c7e2b04
    # prints results/3f9a1c7e2b04.json: {"output": "OK", "usage": {...},
    # "model": "...", "provider": "...", "ts": ...}

Add `--schema a-json-schema-file.json` for a structured JSON-schema reply
(passed through as `response_format`). Three ready-made chat job templates
live in `tools/lane/jobs/`: `run-summary.sh <lane> <workflow-transcript-dir>`
(one dark-factory run's `journal.jsonl` → a terse summary), `findings-
classify.sh <lane> <findings.json>` (review findings → the defect classes
in the data-and-models spec §6, schema-enforced), and `repo-coherence.sh
<lane> [repo-root]` (docs/runbooks + docs/superpowers/specs + nixosModules +
hosts in one large-context request, looking for the class of
documentation-vs-implementation contradiction the pre-switch audit found by
hand).

**An agent job** — experimental, see the next section — needs `--repo`:

    echo '{"prompt":"List every *.nix file that imports egressBroker.nix."}' \
      | lane-submit openrouter --kind agent --class permitted \
          --model deepseek/deepseek-v4-flash --repo ~/flakes/nixos-skill

`lane-submit` copies `--repo` (with `.git` intact) into the job's own
directory before starting the unit — the agent never sees your live working
tree, and `--repo` under `~/.claude`, `~/.codex`, `/var/lib/baskets`
or `~/strategy` is refused outright, matching the classification
boundary above.

## Reading a result, the ledger

Every result lands at `/var/lib/lanes/<lane>/results/<job-id>.json` — either
`{output, usage, model, provider, ts}` on success, or `{error, ts}` on
refusal or failure (`lane-wait`'s own exit code is non-zero whenever
`error` is present, so a script can check it without parsing JSON). What
reaches `/var/lib/lanes/<lane>/ledger.jsonl` depends on the job kind, as
`pkgs/lane/lane-run.py:446-470` implements it:

- a `chat` job appends its ledger line only on success —
  `{ts, job, kind, model, provider, usage, wall_s}` — never on an HTTP
  failure after retries;
- a `dsh` job appends its line whatever the exit code — it carries `exit`
  (and `wall_s`) but **no `usage`** — so a failed dsh job still counts a
  line;
- a refused job (bad class) writes only the result file's `error` key and
  never touches the ledger.

So `ledger.jsonl`'s line count is not a completed-job count: a failed dsh
job is counted, a failed chat job is not. The dsh append-whatever-the-exit-
code behaviour is what the code does today; changing it is a later code
task, not something this runbook promises. This spool is the raw material
for the factory-wide ledger (`tools/ledger/factory.py`, store
`/var/lib/evidence/ledger`) — until that rollup exists, `ledger.jsonl` is
the only per-lane spend record; read it directly (`jq -s .
/var/lib/lanes/openrouter/ledger.jsonl`) for now.

## The batch lane

The batch lane is the OpenRouter lane's asynchronous endpoint,
`POST https://openrouter.ai/api/beta/batches`, the provider's batch API
(decision 30b, corrected 2026-09-10 to run on the existing OpenRouter lane,
not Claude Code and not a second vendor). Where the interactive path forwards
one plan through `factory_route`'s default openrouter ladder and FA1's rung-3
claude terminus (the operator watching), the batch path asks for
`--route openrouter-batch` and gets the Fable `:batch` id at **50 % of
standard pricing** — measured live in
`docs/research-2026-09-11-batch-lane.md` (§4: $0.349 vs $0.699 for one
increment's 13,979 output tokens). The routing row,
`anthropic/claude-fable-5.1:batch`, resolves only on an explicit
`--route openrouter-batch`; the default caller keeps the Flash ladder.

**Submit** — one inline `requests` array, no JSONL file upload (`endpoint`
and `model` must be serialised before `requests`; the API stream-parses):

    curl -sS -x http://10.100.4.1:3141 https://openrouter.ai/api/beta/batches \
      -H "Content-Type: application/json" \
      -d '{"endpoint":"/v1/chat/completions",
           "model":"anthropic/claude-fable-5.1:batch",
           "requests":[{"custom_id":"p-1",
             "body":{"messages":[{"role":"user","content":"…"}],"max_tokens":N}}]}'

`202 Accepted` returns a batch object with `status: "validating"` and a
`completion_window` of `24h`. The key is injected at the broker on the way
out; the command carries no `Authorization` header.

**Collect** — poll the same id with
`GET https://openrouter.ai/api/beta/batches/<id>`. Status runs
`validating → in_progress → finalizing → completed` (terminal: `completed`,
`failed`, `expired`, `cancelled`). **Results land inline** in the terminal
response's `results[]` — there is no on-disk result file and no separate
download endpoint. Each result maps back to its input by `custom_id` and
carries exactly one of `response` (its `body` a Chat Completions object,
`status_code` 200, `provider` `Anthropic`) or `error`. The batch's
`usage.cost` is the authoritative bill (a 26-token probe cost $0.00039, the
50 % rate).

**Cancelling** — there is no cancel verb on the lane's API: `DELETE
/api/beta/batches/<id>` returns 404 (measured), and the batch quickstart
documents submit / list / poll only. A batch you must not run is not
cancelled over the API; it is either left to reach a terminal status or left
to `expire` at the 24 h window. Plan batch submissions so an abandoned batch
expires on the window rather than expecting a mid-flight kill.

## The shadow period

For the first two weeks after a lane starts taking real jobs, treat every
output as **unverified**, not as ground truth: store it, and where a Tier A
deterministic answer exists or a Sonnet sample can be run on the same
input, compare them by hand and log the agreement on the board (Lane L).
No lane output substitutes for Tier A work or a Sonnet review during this
window, whatever the job template's own docstring says about what it's
"for" — the templates describe intended future use, not current trust
level. There is no automated shadow-vs-truth diff tool yet (that lands with
the ledger, T1); until then this is an operator/orchestrator discipline,
not something the build enforces. The lane graduates past shadow mode on
measured agreement, recorded as a board decision — not on a calendar date
alone.

## Working with dsh yourself, on the host (`dsh-openrouter`)

The lane is a batch shape — task in, diff out — and that is right for the
factory. For your own hands there is `dsh-openrouter` (pkgs/dsh-openrouter;
a system command on `core` since the 2026-09-03 evening switch, also in
the devShell and as `nix run ~/nixos-agent-env#dsh-openrouter`): the same
pinned DeepSeek Harness, booted in the directory you are in, routed
straight to OpenRouter. It is **not a lane**: no namespace, no broker, the
harness reaches openrouter.ai by itself with a key you hold. What it keeps
from the lane is the data contract, and it tests it
(`tests/unit/70-dsh-openrouter.bats`, run by `checks.unit`):

- it refuses to start inside a local-only tree (`~/.claude`, `/run/baskets`,
  `/var/lib/baskets`, `~/strategy`, `/var/lib/helm`, `/var/lib/egress-broker`,
  `/var/lib/lanes`, `/var/lib/secrets`) — and checks that *before* it
  reads the key;
- the key comes from `OPENROUTER_API_KEY` or from `~/.config/openrouter/key`
  (override with `OPENROUTER_KEY_FILE`), which must be a regular file, yours,
  mode 0600 or 0400; it is never printed;
- telemetry is off, the web-search/fetch tool is off, the browser UI binds
  127.0.0.1 only behind a per-launch token, and `--dump-config` shows the
  exact route it composed (no secrets in it);
- the harness's own sandbox (bubblewrap, then Landlock) confines tool calls
  to the working tree — `workspace-write` by default; `--permission
  danger-full-access` is a per-launch opt-in, `read-only` the cautious one;
- a deny-only hook set (`pkgs/dsh-openrouter/hook-guard.py`) refuses
  `sudo`, `nixos-rebuild`, `systemctl start/stop/restart/reload/enable/
  disable`, reading the OpenRouter key file, and any edit/write outside the
  working tree or under a protected path; and (RT5) it refuses a sub-agent or
  nested-seat launch whose explicit `model` is not an OpenRouter row of the
  routing table (`docs/ledger/routing.toml`, `${FACTORY_ROUTING_TABLE:-
  $HOME/nixos-agent-env/docs/ledger/routing.toml}`), failing closed when the
  table is missing or unparsable — see "Reading the denial audit" below for
  where a refusal is recorded.
- the guard parses its payload fail-closed (RT5rb): its model rule walks
  `tool_input` to a depth budget of exactly **64** (a model at depth 64 is
  named in the reason, depth 65 is the budget overrun), and a payload that
  *cannot be parsed* — larger than 4 MiB, nested past the guard's parse-depth
  limit, malformed JSON, or whose top level is not a JSON object — is denied
  with `payload could not be parsed: <too large|too deep|ExceptionName>`.
  A non-object `tool_input` on a sub-agent tool (`subagent`, `subagent_fork`,
  `workflow`) is denied as `model rule could not be evaluated: tool_input is
  not an object`. When the payload does not parse the tool name is unknown, so
  that denial applies to every tool — an accepted over-denial, because a
  non-zero exit with empty stdout is what the harness reads as *allow*.
- the hook set is a heuristic plus an audit trail, not a boundary. The model
  rule scans the ids a bash command or structured launch spells out, and shell
  substitution is out of reach of a string scan — `--model $(echo …)`,
  `--model $X`, `--model $'…'`, `--mod''el …` all pass. The real wall is the
  lane's netns (with file mode, PAM and the wrapper's refusal list beside it);
  a nested-seat launch outside a lane rides on the key holder's own judgement.

**Reading the denial audit.** Every refusal from the hook set above prints
one compact JSON record (`{ts, event, tool, reason, subject}`, under 400
chars) to the hook's own stderr — never to a file in the workspace. A round
1 version logged to a dotfile there instead; that was dropped on review
2026-09-04 because the audited model's own edit/write checks never covered
that file, so it could erase or overwrite its own trail, and because an
untracked file in whatever tree happened to be current is exactly the kind
of tree dirt a factory run's `git status --porcelain` gate exists to catch.
dsh's own hook bridge (`@deepseek-ai/dsh-hook-protocol`) captures a hook's
stderr and stores it verbatim as `stderrSummary` on that call's
`hook/result` event, inside the session transcript
(`$DSH_HOME/sessions/<cwd-key>/<session-id>/session.jsonl.zstd`) — a root
the harness's own sandbox never lets a tool call write to. That transcript
is the audit of record. Read it back with:

    dsh-openrouter --denials        # last 20 denials across every session under $DSH_HOME
    dsh-openrouter --denials 100    # last 100

Each line is the denial's timestamp, the guard's JSON record, and (when the
transcript's `sourceEventSeqs` links it back) the denied command or path
after `<-`. No secrets are printed: the record only ever names the command
or path that was refused, never a credential value.

**One-time: the key file.** The key at `/var/lib/secrets/openrouter-key` is
the broker's (root:egress-broker); this tool needs a copy that is *yours*.
Paste it again from Proton Pass:

    (umask 077; mkdir -p ~/.config/openrouter; IFS= read -r -s k; printf '%s' "$k" > ~/.config/openrouter/key; echo saved)

paste at the blank line (Ctrl+Shift+V), Enter. `stat -c %a
~/.config/openrouter/key` must say `600`.

**Using it.** From the repo you want to work on:

    dsh-openrouter                       # browser UI; dsh prints the token URL and opens it
    dsh-openrouter -- --no-open --port 8787
    dsh-openrouter --headless "Explain what tests/unit/40-lock.bats covers."
    dsh-openrouter --model deepseek/deepseek-v4-pro --permission read-only
    dsh-openrouter --dump-config         # the composed profile, to check the route

In the browser UI's model picker only OpenRouter routes exist: dsh's
built-in "DeepSeek official" route (DeepSeek's own platform, its own key)
is removed by the wrapper, because a click on one of its entries ended in
"no API key for provider route deepseek-official" on the first evening.
The picker's default entries are the dsh factory's role→model map
(`dsh-openrouter.sh:178`): `deepseek/deepseek-v4-pro-0813` (the default,
dated id as the pin), `deepseek/deepseek-v4-flash` (structured backend
worker), `moonshotai/kimi-k3` (product/UX/frontend), `z-ai/glm-5.3`
(feasibility/routine), and `z-ai/glm-5.3-flash` (cheap routine). Rates:
`docs/ledger/openrouter-prices.csv` (dated rows; `tools/ledger/factory.py
rollup --costs` reads it) — hand-multiplied dollar figures are not written
in prose. `--model ID` or `OPENROUTER_MODEL` changes
the default; `OPENROUTER_MODELS` (space-separated ids that exist on
OpenRouter) replaces the extra list, and empty offers nothing extra. A
choice made in the UI's picker is saved under DSH_HOME and wins on later
launches. The factory lane (`services.model-lanes.openrouter`) stays on
Flash: batch jobs are graded by checks, not by taste. Whether the account's
Non-frontier ZDR group covers the Moonshot and Z.ai entries is unverified —
an operator check (claims file: open a gap when you rely on them).

Reasoning effort defaults to `medium` (the seat *asks* the model to reason,
where the whole 2026-09-03 day ran with the harness default `off` and the
transcripts counted zero reasoning tokens). Precedence: an explicit
`OPENROUTER_REASONING_EFFORT` > a saved selection > the `medium` route
default. The wrapper writes an explicitly set level into the agent selection
(`agent-default-model.reasoningEffort` in `settings.yaml`) before launch, so
it is not shadowed by a saved or launch-written `medium` (field finding N21;
before this fix a saved preference silently overrode the env var). This
rewrite is persistent: one run with `OPENROUTER_REASONING_EFFORT=high`
rewrites the operator's saved picker choice, and the settings.yaml file keeps
that `high` on every later launch until the picker is changed again (review
2026-09-05).
`OPENROUTER_REASONING_EFFORT` takes `off` | `low` | `medium` | `high` |
`xhigh`; `off` is the explicit "no reasoning" request
(`reasoning: {effort: "none"}` on the wire). OpenRouter accepts the five
levels the picker offers — `low`, `medium`, `high`, and `xhigh` — each
passed through on the wire unmangled: the live catalog
(https://openrouter.ai/docs/use-cases/reasoning-tokens) lists `max, xhigh,
high, medium, low, minimal, none`, and `xhigh` is a value this model's
catalog entry accepts, so a saved `xhigh` is sent as `xhigh`, never
downgraded (field bug N19, generation 37 — a saved `xhigh` died with
`UNSUPPORTED_REASONING_EFFORT`, and the first fix wrongly aliased it to
`high`; `max` and `minimal` are not exposed by the picker). **Unmeasured
(dated debt 2026-09-04):** the fake upstream the seat's tests run against
records what the seat *sends* on the wire — it verifies a request carries
the effort it was told to, not what OpenRouter *does* with it. Whether
OpenRouter in fact honours each level for DeepSeek, and what `medium` (the
default) over `none` costs in reasoning tokens, is unverified. **Unmeasured
(dated debt 2026-09-05):** the ledger records **no reasoning tokens** for
this route — `reasoningTokens` appears in zero usage records even when
reasoning *content* was streamed, so a `reasoning 0` is an accounting gap,
not evidence of no reasoning. Measure it with one fix-round task: run the
same headless job twice, once with `OPENROUTER_REASONING_EFFORT=off` and
once with `medium`, and compare reasoning/output tokens and the final
verdict from the ledger.

Each launch takes a free port (dsh prints the URL), so two sessions — two
repos, or an old window you forgot — run side by side; `-- --port N` pins
one. If a launch ever dies with `EADDRINUSE 127.0.0.1:3080`, an older
wrapper is running: close that window or add `-- --port 0`.

**Rolling back a switch that brought a new wrapper:** every NixOS switch is
a generation; the one before the dsh-seat switch is 28 (commit ac4171f,
git tag `live-gen28-2026-09-03`). To return to it exactly:

    sudo /nix/var/nix/profiles/system-28-link/bin/switch-to-configuration switch

A plain `nixos-rebuild switch --rollback` also works right after a single
switch, but names no generation, so prefer the explicit path.

The first line it prints names the model, the base URL, the permission
mode, where the key came from and the workspace. The second reminds you
that **zero-data-retention is an account setting here**: the lane stamps
ZDR on every request at its broker; this path cannot (dsh's provider
config carries headers, not body fields), so the account-level ZDR and
training opt-out in "OpenRouter account settings" above are what protect
these requests. Flip them before the first real session, and keep to
`permitted` material — the refusal list stops the obvious mistakes, not a
`cp` of a basket into your working tree.

**Seat jobs behind the broker** (`--broker`, what the lane's unit starts)
hold no key of their own and bind the UI to the namespace rather than
127.0.0.1: `--bind-namespace ADDR` (with `--broker` only) takes a real
dotted IPv4 — four octets each 0-255, no leading zeros, not `0.0.0.0`, not
`127.0.0.0/8`, not empty — and anything else exits 2. `DSH_OPENROUTER_NODE`
is a test-only interpreter seam, honoured only when
`DSH_OPENROUTER_TEST_SEAM=1` is also set; the seat unit sets neither.

Sessions, settings and the route overlay live under
`~/.local/share/dsh-openrouter` (0700; `DSH_HOME` overrides). The harness
reads a `.env` in the working directory and in that home for variables
that are *unset*; the key and the telemetry switch are exported by the
wrapper first, so a repo's `.env` cannot redirect them.

What was measured on 2026-09-03 (all against a scripted fake upstream on
loopback, `tests/mocks/openai-fake.py`, so no key of value was involved):
the headless mode sends `Authorization: Bearer <the file's key>` and the
requested model to `/api/v1/chat/completions` and prints the answer; the
bash tool ran inside the working tree under `workspace-write` and its
write to `/tmp` never reached the host; the browser UI booted on
127.0.0.1, answered 401 without its token, served the app with it, and a
chat turn there produced a bash tool call that ran in the workspace and
fed its output back.
Not measured until you run it with the real key: OpenRouter's own
behaviour (routing, cost per session, the account ZDR setting taking
effect) — the first real session is that measurement; the lane's
`ledger.jsonl` does not see these requests, the OpenRouter activity page
does.

## Factory runs: the declared `~/factory` root

The dsh factory runs from `~/factory` — a directory the host config
declares via tmpfiles (`d /home/dalhaka/factory 0700 dalhaka users -`,
plus `base/` and `ws/`), not a gitignored dotdir inside a repo
(`docs/decisions/2026-09-04-parallel-agent-workflows.md`; O11). Start
`dsh-openrouter` from `~/factory` so each session's working tree is owned
by that root, outside every git repo.

- Base clones are `git clone --local ~/nixos-agent-env
  ~/factory/base/nixos-agent-env` — one per repo a run touches.
- Workspaces live under `ws/<run-id>/<task-key>`.
- Retention is manual until a factory-gc exists.

## The seat driver is versioned at `tools/factory/seat/`

The unversioned `~/factory/bin/` scripts that ran the whole 2026-09-04 fix
round headless through the `dsh-openrouter` seat are now checked in at
`tools/factory/seat/` (plan N17) — same names, behaviour unchanged, gated on
shellcheck + ruff by `checks.lint` and exercised by
`tests/unit/80-seat-driver.bats`. They are the operator's manual per-task
tool; the in-factory successors are N10/F8, which grow a scheduler inside
`tools/factory/dark-factory.js`. The scripts still operate against the
runtime `~/factory` root (`FACTORY_ROOT`), not against this repo.

## The "agent" job kind is a dead end (`/api/v1/messages` is denied)

`--kind agent` runs the Claude Code CLI (`claude -p`, from the operator's
own system profile — deliberately not a Nix runtime input of this package,
see `nixosModules/modelLane.nix`) with `ANTHROPIC_BASE_URL` pointed at
`https://openrouter.ai/api` — OpenRouter's Anthropic-compatible surface, i.e.
`/api/v1/messages`. **That path is denied at the broker** (fail closed,
decision addendum 2026-09-04 in
`docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md`): the
Claude-Code-through-OpenRouter route returned empty results and was replaced
by the `dsh` job kind, and the seat and the lane both use
`/api/v1/chat/completions`, so nothing consumes `/api/v1/messages`. A request
to that path is refused before the key is injected and audited
`path-not-permitted` — which is what closed the three credential-injected,
unpatched `/api/v1/messages` requests U7 found. Keep using `--kind chat`
(or `--kind dsh` for harness jobs); `--kind agent` remains only as a
transport-shaped fixture in `checks.lane-vm`, where its fake `claude` never
reaches the network. It was unverified in two further ways even before the
deny:

- **Tool-call fidelity.** Nothing in this repo has yet confirmed DeepSeek,
  through that compatibility surface, produces tool calls the Claude Code
  CLI can execute reliably — file edits, bash invocations, multi-turn tool
  loops. `checks.lane-vm` proves the transport (broker injects the header,
  netns is closed, `local-only` is refused) but its fake upstream returns a
  canned answer, not a real DeepSeek tool-use trace.
- **It is not yet an implementer seat.** Per the factory model policy
  (`docs/decisions/2026-09-02-factory-model-policy.md`) and the data-and-
  models spec §9, Tier C roles (Fable plans and judges gates, Opus reviews
  code, Sonnet implements) are fixed until proving-grounds evidence says
  otherwise. That evidence is plan task T4 (in `~/flakes/nixos-skill`): a
  `deepseek` arm on the NixOS-skill eval seeds, scored by the same `nix
  flake check --offline` every other arm uses, reported as a paired
  Sonnet-vs-DeepSeek difference. No factory task assigns `--kind agent`
  jobs real implementation work until that report lands and the board
  records a decision on it.

Use `--kind chat` (or `--kind dsh` for harness jobs) for anything that matters.
