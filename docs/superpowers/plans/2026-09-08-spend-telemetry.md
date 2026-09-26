# Spend telemetry — every dollar this operation spends, in the evidence store — plan (2026-09-08, revision 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) and `tools/factory/dark-factory.js` both read the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and `commit subject`. A seat sees only `## Global Constraints`, `## Assumptions` and its own section (`tools/factory/seat/factory-brief <plan> <KEY>` is the whole contract).

**Goal:** every service this operation pays for — OpenRouter (seats and lanes), the Claude subscription (the orchestrator's sessions and the workflow agents), Codex when it runs — records what it spent into `/var/lib/evidence` through the append-only fence, per request where the vendor tells us and per session otherwise, with no new egress and no identity on any wire or disk; one report reads it back by UTC day, service, source and role. The operator (17:15): "start collecting and organizing the data in the database sooner so I don't bankrupt myself".

**Spec:** `docs/concepts/2026-09-08e-capturing-usage.md` (1,102 words, S — `wc -w`). Where a section's mechanism differs from its heading, its first paragraph says so and why (SP2, SP3, SP4, SP5).

**Revision** of the hand-typed draft judged 22/42 (`docs/reviews/plan-judgements/2026-09-08-spend-telemetry.md`, 37 errata, each applied or answered in §Errata applied); the five typed headings SP1–SP5 are byte-identical; scope that outgrew a heading's size is three NEW keys — SP6 (the main-session reader), SP7 (`evidence ingest otel`), SP8 (`evidence ingest openrouter-usage`).

**Packet of record:** `plan-judge/packet/*.md` (2026-09-08 22:09 UTC) and `plan-judge/facts.md` (the orchestrator's measurements 17:05–17:41 CDT); the tree at `a285c7ec26553c1856e3b25a99d91eb675caa115` (`git log -1 --format='%H %s'` → `… docs: plan judgement — the hand-typed spend-telemetry draft scores 22/42, revise …`); `check` empty; live generation 47 = `3c537f9` (`readlink /nix/var/nix/profiles/system` → `system-47-link`).

## Operator questions (each answerable in one word; the default applies if unanswered)

1. **How do Claude Code sessions get the exporter variables — `managed` (an `env`-only `/etc/claude-code/managed-settings.json` written by the telemetry module), `session` (`environment.sessionVariables`, host-wide) or `hand` (your own `~/.claude/settings.json`)?** Facts: a settings `env` block drives the exporter and overrides a conflicting shell export (Assumption 9a); `/etc/claude-code` does not exist on core (`ls /etc/claude-code` → `No such file or directory`); your settings file has no `env` block. **Recommendation: managed** — Claude-Code-scoped, declarative, next launch, no re-login; the build refuses if the cowork lockdown module is ever enabled beside it. **Default: managed.** No invariant (the collector is loopback-only).
2. **Does switch #23 also flip the store to `0700` (decision 2026-09-05 answer 1)?** Fact: `replace_stream` runs `os.chmod(path.parent, 0o750)` on every write (`grep -n 'os.chmod' pkgs/evidence/evidence.py`), so a tmpfiles flip is undone by the first ledger merge. **Recommendation: no** — the fence's chmod changes first, a task of its own. **Default: no.**
3. **Is the main-session reader (SP6: one numbers-only row per `~/.claude/projects/<slug>/<session>.jsonl`, the 429 tombstones from those files) in scope now?** Facts: answer 2 approves "usage-only extraction … numbers only"; concept 2026-09-08d §4: "the Claude side is the expensive side"; this host's thirteen tombstones live in a main-session file. **Recommendation: yes.** **Default: yes** (a `no` withdraws SP6 with a `docs/ledger/task-status.toml` row).

Decided in the plan (§Decisions), for the operator to veto: the broker tee; raw files beside their producers with the ingests as the fence; the collector as the store owner's uid but never a store writer; cost as `num`; the correlation id; the three new keys.

## Spec-to-task map

| spec item | task or `out:` |
|---|---|
| OpenRouter 1 — every completion carries `usage.cost`, the cache split, `reasoning_tokens`, `id`, `provider`; the seat drops them | SP1 (the broker tee — D1); SP8 (the ingest) |
| OpenRouter 2 — the account endpoints need a management key | `out:` no management key exists (§Not in this plan) |
| OpenRouter 3 — no host timer with the key; the manual export kept (answer 4) | §Global Constraints; SP5 keeps the export as reconciliation |
| OpenRouter 4 — the ledger's reader prices by (date, model) | `out:` unchanged; SP4 never prices OpenRouter from a table |
| Claude 5 — transcripts are the ground truth; MAX per field per `message.id` per file; `_read_findings` crashes | SP2 (the fix, the rule, the workflow walk); SP6 (the main-session walk) |
| Claude 6 — OpenTelemetry is real, local, identity ON with no off-switch for the email | SP3 (the collector, the allowlist, the env route); SP7 (the ingest) |
| Claude 7 — the Admin API is API-org only | `out:` nothing to build (Assumption 14) |
| Claude 8 — the weekly limit is screen-only; the 429 tombstone is what the transcript keeps | SP2, SP6 (the `limit-event` rows), SP5 (the runbook, the reset probe as the proxy, a claim row) |
| Recommendation 1 — seat dollars at the source through the broker | SP1, SP8 |
| Recommendation 2 — the activity endpoint later, through a lane | `out:` §Not in this plan |
| Recommendation 3 — fix and run the extractor with the MAX rule tested; re-derive concept 2026-09-08d §4 from the ledger | SP2 (the 2/2/7912 and 100/100/100 fixtures); SP6 (`rollup --week`); the re-derivation is §Operator step 6 (the orchestrator, never a seat) |
| Recommendation 4 — the tombstones in the same pass; no durable source for the weekly percentage; the reset probe stays the proxy | SP2, SP6, SP5 |
| Recommendation 5 — OpenTelemetry: its own phase, loopback collector, identity dropped before writing, a check that proves the drop | SP3 (`telemetry-eval` pins, `telemetry-vm` proves), SP7 |
| the operator's word — a report over all the business spending | SP4, SP5 |
| Codex spend | `out:` no producer — the rollout carries tokens (the codex-driver-arm plan's `.result` `usage:` line) and a weekly percentage, no dollars |

Every task traces back to a row above (SP4 to the operator's word).

## Decisions (judgement calls, each with the reason and the alternative)

- **D1 The broker, not the seat harness.** The broker terminates TLS for seats and lanes alike and already writes one audit line per flow; dsh's `TokenUsage` has no cost field (`tools/ledger/factory.py` docstring) and lives in another repo. Alternative: `factory-usage.py` through dsh — a change in `~/flakes/dsh-harness`, seats only.
- **D2 A tee, not a buffer.** A streamed body is never buffered (`_body_bytes`'s docstring); SP1 replaces the stream flag with a callable that forwards every chunk unchanged and keeps the last 64 KiB. Alternative: `stream = False` — the seat's latency and the addon's documented streaming reasoning change.
- **D3 Raw files beside their producers; the store holds fenced rows only.** `usage.jsonl` beside `audit.jsonl` (0644 under the unit's umask, unbacked like the audit log — answer 5); the collector's OTLP-JSON under its own `StateDirectory`; the ingests run as the operator through `replace_stream`. Alternative: the collector writing under `/var/lib/evidence/otel` — raw OTLP carries shapes the fence forbids and the store is a restic path (`grep -n '"/var/lib/evidence"' hosts/core/proton-backup.nix`).
- **D4 The collector runs as the store owner's uid, hardened, and cannot write the store** (`ProtectSystem=strict`, `ReadWritePaths` = its state dir, `InaccessiblePaths=-/var/lib/evidence`, `ProtectHome=true`, `IPAddressDeny=any` + `IPAddressAllow=localhost`). Alternative: `DynamicUser` — its files are unreadable to the operator and the exporter's file mode is not configurable.
- **D5 The allowlist runs at the data-point and log-record contexts.** Identity rides on every data point and record, not the resource (Assumption 9c); a resource-context `keep_keys` leaves `user.email` in every point. Only named keys survive, a future `user.name` included.
- **D6 The env route is an `env`-only managed-settings file** (question 1); the module's assertion refuses `services.claude-managed-settings.enable` beside it.
- **D7 `cost_usd` is the store class `num`** (`9.9e-07` round-trips through Python's `json`; `activity-day` and `lane-job` already use it). Alternative: a decimal string every consumer would special-case.
- **D8 One correlation id per flow, minted once** (`flow.metadata.setdefault("egress_request_id", uuid4().hex)`); the audit record gains that field. Alternative: reuse mitmproxy's `flow.id` — stable but not a policy field and not in the audit record today.
- **D9 Three new keys** (SP8 the OpenRouter ingest, SP7 the OTLP ingest, SP6 the main-session walk) keep every heading at its size; `streams.py` is edited by SP1 → SP2 → SP7 in that order, never by two seats in one wave. Alternative: grow SP2 and SP3 past their S/M labels.
- **D10 Claude's transcript rows and OTel rows are never added**: two sources (`basis list`, `basis estimate`); the header says so. Alternative: prefer the OTel estimate and drop the transcript total — loses everything before switch #23.
- **D11 SP2 takes none of another open plan's items.** A concurrently-open ledger chain (Assumption 15) owns `_merge_jsonl`'s per-record refusal and the store-writers lint; SP2 and SP6 leave `_merge_jsonl` untouched. Alternative: fold `_merge_jsonl`'s per-record refusal into SP2 — couples this plan to a chain it does not control.
- **D12 Roles come from a tokenising rule with an `unknown` arm**, per source (SP4). Alternative: an exact label→role map — a new label spelling silently becomes `unknown`.

## Global Constraints

- **Build-only.** No `sudo`, `nixos-rebuild`, `systemctl start/stop/restart/enable`, basket mount/teardown; no reading `/var/lib/secrets/*`, `~/.config/openrouter/key`, `~/.config/restic/password`. Never open a transcript, a seat log or a store body (`~/.claude/projects/**`, `~/factory/runs/*/*.log`, `/var/lib/evidence/*.jsonl`): the fixtures here are synthetic and are the contract. No network. Brief §3 invariant 3 binds: no new egress path; the collector listens on loopback only.
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`), exactly one commit on `task/<KEY>`; `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null` a gated command. The subject is the section's `commit subject` byte for byte; the trailers are the WORKSPACE RULES' two lines.
- TDD: the failing check first, shown red, then green; paste the red and the green line in the commit body. Every table row below names the one-line mutant that turns it red; a test that cannot fail is a `vacuous-test` major. Every proxy names what it stands in for and its gap (`docs/decisions/2026-09-03-test-based-reality-amendments.md`).
- **`touches` is a contract.** A file outside it is a deviation (`Deviation: <path> — <reason>` in the commit body); the integrator refuses an undisclosed extra. Exempt: `docs/MAP.md` (regenerate with `python3 pkgs/evidence/repomap.py --root . write` when you add a file or a check) and the queue block of `docs/OPERATIONS.md`; never edit `docs/OPERATIONS.md` outside that block.
- Every stream is declared in `pkgs/evidence/streams.py` `KINDS` first, with a valid and a refused row in `tests/evidence/test_streams_policy.py`, red before its writer; writers under `pkgs/evidence` and `tools/ledger` reach the store only through `evidence.append` / `evidence.replace_stream` (`tests/lint/store-writers.sh` in `lint`: no `open(…, "a")`, no `O_APPEND`, no `/var/lib/evidence` literal outside `evidence.py`; its `ROOTS` exclude `pkgs/broker`). No field named in `streams.FORBIDDEN` (`prompt, response, content, text, message, body, path, file, cwd, host, client, user, email, slug, messages, …`); `ts`/`v`/`kind` are the envelope. **Before any Task section below is written, every new kind's field list is screened against `streams.FORBIDDEN` by name** — `openrouter-usage`'s fields (SP1) are clean; the count fields on `factory-agent` and `main-session` (SP2, SP6) are named `message_count`, not `messages`, for exactly this reason (§Errata applied F).
- Python is stdlib only in `pkgs/evidence`, `tools/ledger` (mitmproxy is the broker's one dependency); `ruff format` (88 columns) rewraps every block below — a reformatting-only difference is not a deviation; run `nix develop -c ruff format <your files>`. New `.py` files under the touched directories are already in `lint`'s ruff list.
- Bats: one `[ … ]` per line, never `] && [`; a negated grep captures its status (`run ! grep …`), never a bare `! grep` (SD7's rejection). Nix: statix rejects `{ ... }:` headers; a check runs as `nix build .#checks.x86_64-linux.<name> -L --no-link`.
- The result block ends your final reply: `FACTORY-RESULT status=done|partial|failed` (a space, no colon); `FACTORY-CHECKS <name>=<pass|fail|not-run> …` naming exactly the section's acceptance; `FACTORY-COMMITS <n>`; `FACTORY-NOTES` one line. Never copy the WORKSPACE RULES or the result template into a project file.
- Privacy over convenience: identity attributes (`user.email`, `user.id`, `user.account_uuid`, `organization.id`) are dropped before anything is written and refused if they reach an ingest; no stream field carries `cwd`, `gitBranch`, `slug`, a prompt or a reply; the broker never records a response's content.

## Assumptions

1. **mitmproxy 12.2.3** (`nix develop -c python3 -c "import mitmproxy.version as v; print(v.VERSION)"`). `Message.stream` is `stream: Callable[[bytes], Iterable[bytes] | bytes] | bool = False`; the proxy layer calls a callable per chunk and once more with `b""` at the end (`proxy/layers/http/__init__.py`: `if callable(self.flow.response.stream):` / `chunks = self.flow.response.stream(event.data)` … `stream(b"")`); `raw_content` is `None` for a streamed body; the `response` hook fires after the last chunk.
2. **The addon today** (`grep -n "def \|\.stream\|audit_log\|egress_audited" pkgs/broker/policy.py`): hooks `http_connect`, `requestheaders`, `request`, `responseheaders`, `response`, `error`; `responseheaders` is `content_type = flow.response.headers.get("content-type", "")` / `if content_type.startswith("text/event-stream"):` / `flow.response.stream = True`; `response` is `self._audit(flow, "allow", "ok")`. `_audit` writes ONE line per flow (`flow.metadata["egress_audited"]`) with exactly `ts, instance, client, method, host, host_header, sni, path, bytes_out, bytes_in, verdict, reason` — no request id — via `open(self.audit_log, "a", encoding="utf-8")`. `_prefix_match(path, prefixes)` takes the RAW path, normalises it and returns `None` when it cannot, else a bool. The policy JSON is `renderPolicy` in `nixosModules/egressBroker.nix` (`instance, allow, inject, body_patch, deny_paths, audit_log = "/var/lib/egress-broker/${name}/audit.jsonl"`), read-only as `services.egress-broker.policy.<name>`, asserted by `host-core` (`p = c.services.egress-broker.policy.openrouter`). The unit runs `User = "egress-broker"` with the addon embedded by store path (`"-s ${../pkgs/broker/policy.py}`) — a change reaches the live broker only at a switch. Live: `audit.jsonl` is `-rw-r--r-- egress-broker` in a `drwxr-xr-x` dir (`ls -la /var/lib/egress-broker/openrouter/`); `/var/lib/egress-broker` is NOT a restic path.
3. **The broker tests** (`sed -n '1,60p' tests/broker/test_policy.py`, 41 tests): `load_addon(tmp_path, monkeypatch, policy)` writes `policy.json` (`audit_log` defaulted to `tmp_path/"audit.jsonl"`), sets `BROKER_POLICY`, loads `pkgs/broker/policy.py`, returns `mod.EgressPolicy(), policy["audit_log"]`; flows from `https_flow(host, path, sni)`, responses `http.Response.make(200, b"ok", {...})`, `audit_lines(path)`. They run in `checks.addon` (`pkgs.runCommand "broker-addon-tests"`, `pytest tests-broker -q`) — never in `unit` (bats).
4. **The SSE wire shape** (`tests/mocks/openai-fake.py`, `tests/integration/seat-vm.nix`): `data: <json>\n\n` chunks whose LAST chunk carries `usage`, then `data: [DONE]\n\n`; OpenRouter also sends comment lines (`: OPENROUTER PROCESSING\n\n`). A real response (`nix develop -c jq -c '{id, provider, model, usage}' /var/lib/lanes/openrouter/results/49d95d752ed6.json`, the orchestrator's read): `{"id":null,"provider":"DeepInfra","model":"deepseek/deepseek-v4-flash","usage":{"prompt_tokens":7,"completion_tokens":2,"total_tokens":9,"cost":9.9E-7,"is_byok":false,"prompt_tokens_details":{"cached_tokens":0,"cache_write_tokens":0,"audio_tokens":0,"video_tokens":0},"cost_details":{"upstream_inference_cost":9.9E-7,"upstream_inference_prompt_cost":6.3E-7,"upstream_inference_completions_cost":3.6E-7},"completion_tokens_details":{"reasoning_tokens":0,"image_tokens":0,"audio_tokens":0}}}` — the top-level `id` can be NULL.
5. **The store** (`pkgs/evidence/streams.py`, `evidence.py`): `KINDS[kind] = {"stream", "v", "key", "fields"}`; classes `"id"` (`ID_RE = ^[A-Za-z0-9._:+-]{1,120}$`), `"model-id"` (`MODEL_ID_RE = ^[a-z0-9][a-z0-9._-]{0,63}(/[a-z0-9][a-z0-9._-]{0,63})?$` — `claude-opus-5[1m]` does NOT match), `"int"`, `"num"` (int or float, never bool), `"bool"`, `"ts"` (RFC3339 `Z`, 0–6 fraction digits), `("null", cls)`, `("enum", (...))`, `("re", r"…")`, `("obj", {...})`, `("list", cls, cap)`; refusals `"{path}: not a num"`, `"{path}: not in enum (a|b)"`, `"{key}: undeclared field"`, `"{key}: forbidden name"`; a MISSING declared field is not refused. `replace_stream(store, stream, rows)` validates every row first, needs a keyed kind, keeps `ts` for unchanged rows, writes atomically; `evidence.read` skips torn lines. `INGEST_MODULES = {"judgements": "judgements", "result": "ingest_result", "reviews": "ingest_reviews"}`; `evidence ingest <name> …` imports `pkgs/evidence/<module>.py` and calls `main(forwarded)` with `--store` forwarded; unknown → `evidence: ingest: unknown target {name} (judgements|result|reviews)` exit 2; no target → `parser.error("ingest requires a target (judgements|result|reviews)")`. The idiom is `ingest_result.py`: `main(argv)` with `argparse.ArgumentParser(prog="evidence ingest")`, `--store` from `EVIDENCE_STORE` or `evidence.DEFAULT_STORE`, one subparser, `ingest(store, paths, root)` realpath-fencing every path (`OutsideRoot` before any write), one stderr line per refusal, one `replace_stream`, stdout `ingested {n} rows into derived/tasks ({refused} refused)`, exit `0 if refused == 0 else 1`, `2` on `OutsideRoot`. `checks.evidence-unit` copies `pkgs/evidence`, `tests/evidence`, `docs/ledger`, `docs/MAP.md` and runs `pytest tests/evidence -q`; the loader idiom is `_load(name)` in `test_streams_policy.py`. Live: `/var/lib/evidence/ledger` is EMPTY (`ls`). **Model-id split rule** (SP7, applied identically by SP2/SP6 for the same vendor's bracketed ids — §Errata applied E): `message.model`/`model` is split at the first `[`; the head must match `MODEL_ID_RE`, the bracketed tail (without its brackets) becomes a sibling `model_suffix` field, absent when there is no `[`.
6. **The ledger extractor** (`tools/ledger/factory.py`): `_read_agent` sums every `type == "assistant"` line's `message.usage` naively (`tokens["in"] += usage.get("input_tokens", 0)` …), counts `tool_use` blocks, `model` from the first line, `"label": None` always; `_read_findings` does `title = finding.get("issue") or finding.get("title")` per finding of a `result` event — a STRING finding raises `AttributeError: 'str' object has no attribute 'get'`; `result` events carry `agentId` and may carry `result.label` (`test_findings_carry_task_round_and_label_when_the_result_has_them`: `"label": "review:N9:r2"`); `backfill(projects_dir, ledger_dir)` globs `**/subagents/workflows/wf_*` ONLY and prints nothing; `_merge_jsonl` = `evidence.replace_stream` on the stream from the path (`_stream_of`); every line is `json.loads`ed unguarded. `checks.ledger-unit` copies `tools/ledger` as `ledger`, `pkgs/evidence`, `tests/ledger` as `tests-ledger`, `docs/ledger`; `pytest tests-ledger -q`. The workflow fixture's agent lines have NO `message.id` (`head -c 700 tests/ledger/fixtures/workflow/agent-a2222222222222222.jsonl`: `type`, `agentId`, `timestamp`, `message{role, model, content, usage{input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens, output_tokens_details{thinking_tokens}}}`). **The MAX-per-`message.id` dedup groups by `(file, message.id)`, never `message.id` alone across files** (§Errata applied G): two files that happen to reuse the same `message.id` each contribute their own per-file maximum, and the run total sums both.
7. **The real transcript shapes** (key names only, the orchestrator's measurement; seats never open transcripts): a main-session assistant line's top-level keys include `cwd, gitBranch, message, requestId, sessionId, timestamp, type, uuid, version`; `message` has `id, model, role, usage`; `usage` `{"input_tokens": 2, "cache_creation_input_tokens": 29050, "cache_read_input_tokens": 34255, "output_tokens": 1138, "output_tokens_details": {"thinking_tokens": 973}, …}`. A workflow agent line adds `agentId`; three consecutive lines shared one `message.id` with output 3 / 3 / 213 and identical input and cache counts — the growing-repeat shape. The 429 tombstone adds `apiErrorStatus: 429`, `error: "rate_limit"`, `isApiErrorMessage: true`, `slug` and `"quotaLimits":{"status":"rejected","resetsAt":1788680400,"unifiedRateLimitFallbackAvailable":false,"rateLimitType":"five_hour","overageStatus":"rejected","overageDisabledReason":"org_level_disabled","isUsingOverage":false}` (seven keys; `resetsAt` epoch seconds). The rule (concept 2026-09-08d §4, corrected): MAX per usage field per `message.id` per FILE; naive summing inflates the main side 3.5×, first-wins understates the gates up to 13×. Main files sit at `<projects>/<slug>/<session>.jsonl`; workflow dirs under `**/subagents/workflows/wf_*`.
8. **Claude Code's OpenTelemetry, documented** (the monitoring-usage page, read 2026-09-08): `CLAUDE_CODE_ENABLE_TELEMETRY=1`; `OTEL_METRICS_EXPORTER` ∈ console|otlp|prometheus|none; `OTEL_LOGS_EXPORTER`; `OTEL_EXPORTER_OTLP_PROTOCOL` ∈ grpc|http/json|http/protobuf; `OTEL_EXPORTER_OTLP_ENDPOINT`; `OTEL_METRIC_EXPORT_INTERVAL` (ms; `OTEL_LOGS_EXPORT_INTERVAL` its logs twin — harmless if a build ignores it); `OTEL_METRICS_INCLUDE_ACCOUNT_UUID` (default true) and its siblings; NO switch omits `user.email` or `user.id`; the content switches `OTEL_LOG_*` default off; the variables CAN be set in `settings.json` under `"env"`; `cost_usd` is the local list-price estimate; no quota is exposed.
9. **Claude Code's OpenTelemetry, measured on this host** (the orchestrator, 2026-09-08 17:37–17:41; `claude` 2.1.258 against `otelcol-contrib` 0.151.0 on loopback; `~/.claude/debug/<session>.txt` `[3P telemetry]` lines; the files holding identity values deleted after the key names were read): (a) a settings-file `env` block drives the exporter (`getOtlpReaders: types=["otlp"], … protocol=http/json, endpoint=http://127.0.0.1:44318`) and WINS over the process environment; `OTEL_METRICS_EXPORTER=console` is not honoured (`types=[]`), `otlp` is; (b) the first export fires at +1.0 s (`First metrics export: SUCCESS`; `FAILED (connect ECONNREFUSED …)` with nothing listening — the session continues); two runs with the `file` exporter ALONE left no file though the exports succeeded — hence `flush_interval: 1s` and an acceptance longer than two intervals; (c) resource attributes on the wire are exactly `host.arch, os.type, os.version, service.name=claude-code, service.version=2.1.258`; every metric data point carries `organization.id, user.email, user.id, session.id, terminal.type` plus `model, query_source, type, start_type`; every log record the same five plus `event.name, event.timestamp, event.sequence` and the event's keys; (d) metrics (scope `com.anthropic.claude_code`): `claude_code.session.count`, `claude_code.cost.usage` (USD), `claude_code.token.usage` (four points per model, `type` ∈ `input, output, cacheRead, cacheCreation`), `claude_code.active_time.total`; events (`event.name` WITHOUT the docs' `claude_code.` prefix): `api_request, assistant_response, user_prompt, hook_registered, hook_execution_start, hook_execution_complete, plugin_loaded` — `user_prompt` and `assistant_response` are emitted even with every content flag unset; (e) `claude_code.cost.usage` equals the run's `total_cost_usd`; `modelUsage` there is keyed `claude-opus-5[1m]`-style. The desktop app runs ITS OWN harness (`find ~/.config/Claude -maxdepth 4 -name claude` → `…/claude-code/2.1.255/claude`); whether it reads the managed file is §Operator step 5's measurement — the plan's one declared proxy gap.
10. **The collector** — nixpkgs-host `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` carries `nixos/modules/services/monitoring/opentelemetry-collector.nix` (`cat /nix/store/nqkh6j5xlyvlw4hlrw4ybpq1cis79szf-source/nixos/modules/services/monitoring/opentelemetry-collector.nix`): options `enable`, `package` (`mkPackageOption pkgs "opentelemetry-collector"` — the core build), `settings` (`pkgs.formats.yaml`), `configFile`, `validateConfigFile` (`default = isStorePath cfg.configFile` — FALSE with `settings`; when true the config is validated at BUILD time by `otelcol validate --config=file:$out`); the unit: `DynamicUser = true`, `ProtectSystem = "full"`, `WorkingDirectory = "%S/opentelemetry-collector"`, `StateDirectory = "opentelemetry-collector"`, `SupplementaryGroups = [ "systemd-journal" ]`, `wantedBy = [ "multi-user.target" ]`. `pkgs.opentelemetry-collector-contrib` is `0.151.0` in the host config (`nix eval --raw .#nixosConfigurations.core.pkgs.opentelemetry-collector-contrib.version`), store name `otelcol-contrib-0.151.0`; its `components` list receiver `otlp`, processors `attributes, batch, filter, transform`, exporters `debug, file`. `/var/lib/opentelemetry-collector` does not exist on core.
11. **The collector, measured with a synthetic payload** (the orchestrator's `probe.py`: OTLP/HTTP JSON POSTs to `/v1/metrics` and `/v1/logs`, `Content-Type: application/json`): the `file` exporter writes ONE JSON object per line in OTLP-JSON shape — `resourceMetrics[{resource{attributes[{key, value}]}, scopeMetrics[{scope{name}, metrics[{name, unit, sum{dataPoints[{attributes, timeUnixNano, asDouble|asInt}], aggregationTemporality, isMonotonic}}]}]}]` and `resourceLogs[{resource, scopeLogs[{scope{name: "com.anthropic.claude_code.events"}, logRecords[{timeUnixNano, body, attributes}]}]}]`; attribute values are typed wrappers (`stringValue`; `intValue` a STRING; `doubleValue`; `boolValue`), `timeUnixNano` a decimal string. A `transform` processor's `keep_keys(attributes, [...])` at `context: resource` kept exactly the listed keys and dropped the four identity keys AND an unlisted `user.name`; `filter/events` with `logs.log_record: ['attributes["event.name"] != "…" and …']` dropped a `user_prompt` record carrying a `prompt` attribute and kept `api_request`; `service.telemetry.metrics.level: none` keeps the collector off `:8888`; the file exporter takes `flush_interval`, `rotation: {max_megabytes, max_backups}`.
12. **The host wiring** — `hosts/core/default.nix` `imports = [ ./hardware-configuration.nix ./agent-prereqs.nix ./graphics.nix ./proton-backup.nix ./firefox.nix ./claude-desktop.nix ./helm.nix ./lanes.nix ./seat.nix ]` (`sed -n '4,14p'`); its services block: `claude-managed-settings = { enable = false; brokerInstance = "cowork"; }`, `evidence-store.enable = true`; `nixosModules/claudeManagedSettings.nix` writes `environment.etc."claude-code/managed-settings.json".source = cfg.settingsFile` under `mkIf cfg.enable`; `flake.nix` exports `nixosModules = { … evidenceStore = import ./nixosModules/evidenceStore.nix; }` and lists `self.nixosModules.evidenceStore` in `nixosConfigurations.core.modules`. `services.evidence-store.owner` defaults to `dalhaka` ("every writer runs as this user"). The eval shape is `checks.seat-eval` (`c = self.nixosConfigurations.core.config; … sc = unit.serviceConfig;` then `assert nixpkgs.lib.assertMsg (…) "seat-eval: …";` chains ending in `pkgs.runCommand … "touch $out"`); the VM shape is `tests/integration/seat-vm.nix` (`pkgs.testers.runNixOSTest { name; nodes.machine = …; testScript = ''…''; }`, wired `seat-vm = import ./tests/integration/seat-vm.nix { inherit pkgs; egressBrokerModule = self.nixosModules.egressBroker; … }`).
13. **Prices** (the Claude API reference cached 2026-06-24, per 1M tokens): `claude-fable-5-1` $10.00 in / $50.00 out / cache read $0.25; `claude-opus-5` $5.00 / $25.00; `claude-sonnet-5` $2.00 / $10.00; `claude-haiku-4-5` $1.00 / $5.00; cache-write rates and the other models' cache-read rates are NOT in that table — those units stay unpriced and named (`tools/ledger/schema.md` Principles: "A dollar total is never printed as confident when any unit is unpriced"). `docs/ledger/openrouter-prices.csv` (three rows, stale 2×) is never consulted by SP4.
14. **What has no producer.** The Anthropic Admin API and the Console CSV are API-organization only; a Max subscription has neither; the weekly limit is screen-only (spec, Claude 7–8). The OpenRouter export on disk ends 2026-09-05 18:52 UTC (`tail -3 ~/Documents/openrouter_activity_2026-09-05.csv`); `GET /api/v1/activity` needs a management key; the manual download stays (answer 4).
15. **The record on these paths** (`packet/record.md` §2): ev1/R5 (a rate dropped and priced nowhere), oi1/DA1 (a fixture carried a real key name), tel1b/T1 (an ENVELOPE/field collision), tel2/T1W (`_merge_jsonl` lacks per-record refusal, plan 2026-09-06-telemetry-store-1). Hence: every fixture here is invented; no field is named `ts`/`v`/`kind`; every unpriced unit is named. **Re-measured live at Ship** (§Errata applied D): `nix develop -c python3 pkgs/evidence/tasks.py --root . brief` today shows `rejected` = 0 and `**Rejected, fix round owed:** media/W3 (W3 by cw2) · media/W5 (W5 by cw2)` — no T1W, no T1Wb; HEAD `5ea2491` ("a chain root may end in a capital letter, so T1Wb and T3Mb close their roots") closed that chain after the packet was taken at `a285c7e`. The record item tel2/T1W above is a plan-defect fact and stands regardless of the chain's current status; §Waves and §Dispatch below state the sequencing rule generally rather than pinned to a status label that can go stale.
16. **The driver and the sandboxes** (`packet/field.md` §2): `FACTORY_PLAN` unset → `factory-task` dies exit 2; `factory-integrate` refuses no merge base, a `docs/OPERATIONS.md` change outside the queue block, undisclosed files outside `touches`; `factory-dispatch <run> <repo> <plan> [--dry-run]` takes the plan's basename and asks `tasks.py --root <repo> waves --repo NAME --plan <basename> --next`; a dry run touches nothing. `ls tests/unit | tail -1` → `95-codex-arm.bats`; the next number is 96. `checks.unit` copies `tests` whole, `pkgs/helm`, `pkgs/evidence`, `tools/factory/seat`, `docs/ledger`, `docs/runbooks/session.md` and a few scripts — NOT `docs/runbooks/evidence.md`, NOT `tools/ledger` (`sed -n '2073,2150p' flake.nix`); a bats test needing a file copies it in with a `cp` line beside the others (P8b: a skip in the sandbox proves nothing). `tools/ledger/factory.py` finds `pkgs/evidence` at `Path(__file__).resolve().parents[2] / "pkgs" / "evidence"`. The `Seats (7 d)` line: `seat_stats(runs_dir, now, days)` sums `usage:`'s `input` + `output` as `billed` (`cacheRead` is in the JSON, not summed); `render_seats_line` prints `f"{r['model']}: {runs}, {r['done']} done, {wall}, {r['billed']} billed"`; `render_brief` calls `seat_stats(graph["runs_dir"])`; the graph has no `store` key (`grep -n '"store"' pkgs/evidence/tasks.py` → nothing) though `build(root, runs_dir, store, …)` has it. `report.py`: `refused: n={n} < {min_n} (no conclusion under {min_n})` (plans); `main` parses `--store` then `plans|harness|ladder`. `docs/runbooks/evidence.md` has seven `## ` sections ending `The harness report`, `The two tile rules that changed` — no `## Spend`; its store section says "Four writers append to it". `docs/ledger/claims.toml`: `d5-activity-export` `verified`, class `unit`; a gap row needs `owner`, `review_by` (a TOML date, not past), `closes_by`; verified evidence must start `check:<name>@<rev>` or `operator:<date>`; the gap `reasoning-tokens-not-itemised` closes by "a usage record for the openrouter route carries reasoning tokens, or the ledger documents that the route never will".

## Waves

Waves follow `dependsOn` (the peel-off groups `tasks.py waves` prints), computed with `nix develop -c python3 pkgs/evidence/tasks.py --root . check --draft <this file>`; the draft's basename equals the existing plan's, so its tasks REPLACE that plan's and every existing `### ` line must appear byte-identical (they do). Pasted in §Dispatch.

| wave | groups | dependsOn | the files that keep them apart |
|---|---|---|---|
| 1 | SP1 | — | the broker, `egressBroker.nix`, `flake.nix`, `streams.py` |
| 2 | SP2 ‖ SP3 ‖ SP8 | SP2: SP1; SP3: SP1; SP8: SP1 | SP2 the ledger and `streams.py`; SP3 the module, `hosts/core/*`, `flake.nix`, the VM; SP8 `evidence.py`, its ingest module, `SCHEMA.md` |
| 3 | SP6 ‖ SP7 | SP6: SP2; SP7: SP2, SP8 | SP6 the ledger only; SP7 `streams.py` (after SP2), `evidence.py` (after SP8), its ingest module |
| 4 | SP4 | SP6, SP7 | `report.py`, `tasks.py`, their tests, the price table |
| 5 | SP5 | SP3, SP4 | the runbook, the bats file, `flake.nix` (two `cp` lines), `claims.toml` |

**Cross-plan** (re-measured at Ship, §Errata applied D): `conflicts` prints no pair with an SP key. T1W (plan 2026-09-06-telemetry-store-1) shared the ledger files and `flake.nix` with SP2/SP6 and SP1/SP3/SP5 while it was open; its chain closed at HEAD `5ea2491` before this file was shipped. The rule below is stated generally so it does not go stale the way a status-pinned gate would.

## Operator

Eight seats, eight Opus gates; one switch (#23) after SP3 lands — it activates SP1's broker change too (the unit embeds `policy.py` by store path, Assumption 2). Nothing touches the live system until you run the lines below.

1. **Before wave 2 (three seats) — the balance glance (A3/A9).** `grep -o 'OpenRouter: \$[0-9]* at [^(]*' docs/OPERATIONS.md` → `OpenRouter: $111 at ~12:10` (the board's last figure; four Pro seats ≈ $18 there). Acceptance: the console balance is above $40; below, hold wave 2 and top up.
2. **After SP3 lands — the switch surface, measured before the switch line ships (A2).** `nix build .#nixosConfigurations.core.config.system.build.toplevel && nix store diff-closures /run/current-system ./result`. **Prediction:** `otelcol-contrib: ∅ → 0.151.0`, `evidence: … KiB → …`, a new `unit-opentelemetry-collector.service: ∅ → ε`, the two broker units rebuilt (the addon's store path and `egress-policy-{openrouter,seat}.json` with the new `usage_log` key), and `etc` gaining `claude-code/managed-settings.json`; a measured line outside this is a finding against the plan. Then `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core` (your line; `sudo systemctl start restic-backups-core-local.service` first if the day's commits matter). Rollback: `sudo /nix/var/nix/profiles/system-47-link/bin/switch-to-configuration switch` — 47 is today's generation (`readlink /nix/var/nix/profiles/system`); read it again before switching if another switch has happened.
3. **Acceptance of switch #23.** `systemctl --failed` → `0 loaded units listed`; `systemctl is-active opentelemetry-collector egress-broker-openrouter egress-broker-seat` → `active` ×3; `ss -ltnH | grep 4318` → one line, `127.0.0.1:4318`; `journalctl -u opentelemetry-collector -n 5 --no-pager | grep -c 'Everything is ready'` → `1`; `cat /etc/claude-code/managed-settings.json` → one top-level key `env` with SP3's eight variables; `systemctl show opentelemetry-collector -p User -p ProtectHome -p IPAddressDeny --value` → `dalhaka`, `yes`, `any`.
4. **The first exported session (the identity proof, live).** A new terminal `claude` session, one question, 15 s (two export intervals), exit. `grep -c '"api_request"' /var/lib/opentelemetry-collector/claude-logs.jsonl` → ≥ 1; `grep -c '"cacheRead"' /var/lib/opentelemetry-collector/claude-metrics.jsonl` → ≥ 1; `grep -c -e 'user.email' -e 'organization.id' -e '"user.id"' -e 'account_uuid' /var/lib/opentelemetry-collector/claude-*.jsonl` → `0` for every file; `grep -c 'isTelemetryEnabled=true' "$(ls -t ~/.claude/debug/*.txt | head -1)"` → ≥ 1.
5. **The desktop Code tab (the declared proxy gap).** A Code-tab session, one question, 15 s, close; `grep -l 'isTelemetryEnabled=true' $(ls -t ~/.claude/debug/*.txt | head -2)` names that session's file. If not, the app's own harness (Assumption 9) ignores the managed file: say "no telemetry line", and a fix round SP3b moves the eight variables to `environment.sessionVariables` (a re-login). Until measured, the gap row `otel-desktop-harness-unmeasured` (SP5) stands.
6. **The ingests and the report (the runbook's lines, SP5).** `evidence ingest otel /var/lib/opentelemetry-collector/claude-*.jsonl` → `ingested <n> rows into ledger/otel-claude (0 refused, <k> skipped)`; after the first seat or lane request since the switch: `evidence ingest openrouter-usage /var/lib/egress-broker/*/usage.jsonl` → `ingested <n> rows into ledger/openrouter-usage (0 refused)`; `cd ~/nixos-agent-env && nix develop -c python3 tools/ledger/factory.py backfill ~/.claude/projects --ledger-dir /var/lib/evidence/ledger` → `backfill: <w> workflow dirs, <m> main sessions, <l> limit events`; `evidence report spend --since 2026-09-01 --prices ~/nixos-agent-env/docs/ledger/claude-prices.csv` → the table (or the refusal line on a quiet day). **The re-derivation of concept 2026-09-08d §4** (recommendation 3): `nix develop -c python3 tools/ledger/factory.py rollup --week --since 2026-09-03 --until 2026-09-08 --ledger-dir /var/lib/evidence/ledger` → the `main sessions:` line; the orchestrator writes the figures into the concept's §4 (a docs commit).
7. **Undo of any landing.** `git -C ~/nixos-agent-env log --merges --oneline -3` (find `integrate <KEY> into integ/<run>`), then `cd ~/nixos-agent-env && nix develop -c git revert -m 1 --no-edit <that sha>`; acceptance `git log -1 --format=%s` → `Revert "integrate <KEY> into integ/<run>"`. A revert of SP1 or SP3 after switch #23 owes a switch back (step 2's rollback line).

## Dispatch

Plan file after Ship: `docs/superpowers/plans/2026-09-08-spend-telemetry.md` (overwritten whole by the Ship phase's `Write`; every existing `### ` line survives). Runs: `sp1`…`sp5` (one per wave); fix rounds `<run>f`; a relaunch after a death `<run>b`.

**Step 0 — the plan's commit.** `nix develop -c python3 pkgs/evidence/tasks.py --root . check` (empty), `… write-board`, then `docs: plan — spend telemetry revised for the judges' 37 errata: SP1–SP5 headings kept, SP6 the main-session reader, SP7 ingest otel, SP8 ingest openrouter-usage; the broker tee, the allowlist at the data-point context, the managed env file (test: lint)`.

**The graph on the draft** — `nix develop -c python3 pkgs/evidence/tasks.py --root . check --draft /tmp/claude-1000/-home-dalhaka-nixos-agent-env/7bbab1b5-44c7-4833-803d-dd872022b9df/scratchpad/plan-judge/draft-0/2026-09-08-spend-telemetry.md` (2026-09-08, HEAD a285c7e; exit 0, nothing else printed) →

```
waves: [[["SP1"]], [["SP2"], ["SP3"], ["SP8"]], [["SP6"], ["SP7"]], [["SP4"]], [["SP5"]]]
conflicts: none
```

**The dry-run line** — `tools/factory/seat/factory-dispatch sp1 /home/dalhaka/nixos-agent-env /tmp/claude-1000/-home-dalhaka-nixos-agent-env/7bbab1b5-44c7-4833-803d-dd872022b9df/scratchpad/plan-judge/draft-0/2026-09-08-spend-telemetry.md --dry-run` (the dispatcher takes the basename and asks the graph under the repo — the live plan's SP1, the same key; Ship re-runs it on the shipped file; `ls ~/factory/runs/sp1` → `No such file or directory` afterwards) →

```
would run: factory-wave sp1 /home/dalhaka/nixos-agent-env "SP1"
```

| wave | dry run (`tools/factory/seat/factory-dispatch <run> ~/nixos-agent-env docs/superpowers/plans/2026-09-08-spend-telemetry.md --dry-run`) | the command to run (the same line without `--dry-run`, in the background, never a foreground tool call) |
|---|---|---|
| 1 | `would run: factory-wave sp1 /home/dalhaka/nixos-agent-env "SP1"` | `… factory-dispatch sp1 …` |
| 2 | after SP1's fast-forward: `… "SP2" "SP3" "SP8"` | `… sp2 …` (Operator step 1 first) |
| 3 | after SP2 and SP8: `… "SP6" "SP7"` (a `no` to question 3 withdraws SP6; the line reads `"SP7"`) | `… sp3 …` |
| 4 | after SP6 and SP7: `… "SP4"` | `… sp4 …` |
| 5 | after SP3 and SP4: `… "SP5"` | `… sp5 …` |

**The sequencing rule for a concurrently-open plan sharing files (Assumption 15, D11).** Before every launch of wave 2, 3 or 5: `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep -F 'Running:'` must name no key that touches this plan's files (today it names none — the one such chain on record, T1W, closed at HEAD `5ea2491` before Ship); if it does, wait for that key's fast-forward. Whichever of {SP2, SP6, SP1, SP3, SP5} and a colliding key lands second merges main into its workspace first (step 2 below) and its landing re-runs the shared checks (the integrator runs every `(test: …)` name plus `lint`). Neither SP2 nor SP6 absorbs another plan's item.

**The landing recipe, per key (design §4 A1; expected conflicts re-measured at Ship — `git log --oneline a285c7e..HEAD --name-only` shows four commits landed since the packet, all four inside `pkgs/evidence` (three named changes, one of them two commits): `c3dc548` tasks.py json output, `8045b2f` repomap, `b520783`+`5ea2491` the brief's fix-round line):**
1. Keep exactly the one commit the section names: `git -C ~/factory/ws/<run>/<KEY> log --format='%h %s' <base>..task/<KEY>` prints one line with the section's subject; a second commit → `git -C ~/factory/ws/<run>/<KEY> checkout -q --detach <the one sha>` then `git -C ~/factory/ws/<run>/<KEY> branch -f task/<KEY> <the one sha>` (the guard refuses `reset --hard`; three seats appended a fabricated board commit on 2026-09-05).
2. If `main` moved under a touched file, `docs/MAP.md` or the queue block: `git -C ~/factory/ws/<run>/<KEY> fetch ~/nixos-agent-env main && git -C ~/factory/ws/<run>/<KEY> merge --no-edit FETCH_HEAD` (a board conflict: `git show FETCH_HEAD:docs/OPERATIONS.md > docs/OPERATIONS.md` then `write-board`; a MAP conflict: `repomap.py --root . write`; then `git add` and `nix develop -c git commit -q --no-edit`). Expected, refreshed at Ship against the four post-packet commits above: `streams.py` for SP2/SP7; `flake.nix` for SP3/SP5; `evidence.py` for SP7; `pkgs/evidence/tasks.py` and `tests/evidence/test_tasks.py` for SP4.
3. The gate: an Opus review in a fresh clone, its mutation table a superset of the section's Tests table, red-before-green re-run; the review committed (`git add docs/reviews/<file> && nix develop -c git commit -q -F <msgfile>`) before the integration.
4. `tools/factory/seat/factory-integrate <run> ~/nixos-agent-env <KEY> && git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>` — gated on both exit codes; never pull after a `CHECK … fail` or a `REFUSED` line.
5. Dispatch what it unblocks (A7): SP1 → wave 2; SP2 + SP8 → wave 3; SP6 + SP7 → SP4; SP3 + SP4 → SP5 (`… waves --repo nixos-agent-env --plan 2026-09-08-spend-telemetry.md --next`).

**Relaunch after a death (A6).** After a `budget-402`, `provider-error` or `boot-failure` row: `FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-08-spend-telemetry.md setsid -f bash -c 'exec tools/factory/seat/factory-wave <run>b /home/dalhaka/nixos-agent-env "<KEY>" >> ~/factory/runs/<run>b.wave.log 2>&1' </dev/null`; a `<KEY>b` section points the next seat at the dead seat's diff (`git fetch -q ~/factory/ws/<run>/<KEY> task/<KEY> && git cherry-pick -n FETCH_HEAD`).

**Fix rounds and re-plans (rule A1).** One fix round `<KEY>b` (every rejection item, every deleted test's replacement), launched `FACTORY_PLAN=<plan> tools/factory/seat/factory-task <run>f ~/nixos-agent-env <KEY>b --prior <run>/<KEY>`; a second rejection closes the chain and `<KEY>r` goes through the pinned planning workflow in replan mode.

**Handoff line for the board (A11):** "spend telemetry: plan `2026-09-08-spend-telemetry.md` (SP1 → SP2 SP3 SP8 → SP6 SP7 → SP4 → SP5; questions 1–3 at their defaults unless answered); on the seat: <keys>; in gate: <keys>; landed: <keys>; switch #23 after SP3; next: <the dispatcher line>."

## Anticipation (design §4 rows whose trigger applies)

| row | trigger here | artefact |
|---|---|---|
| A1 | the plan is written | §Dispatch: run names, the dry-run line per wave, the landing recipe |
| A2 | SP3 touches `nixosModules/`, `hosts/`, `flake.nix`; SP1 the broker module | §Operator step 2: the build commands, the delta as a prediction, the measured delta before the switch ships, the rollback generation's own `switch-to-configuration` |
| A3 | a top-up before a wave that starts more than one seat | §Operator step 1; no credential, DNS name, password file or reboot in the plan |
| A4 | every task | each section's Tests table |
| A5 | waves dispatched to a seat | the deterministic guards are landed (P11 via SH2 → SH3 → SH4/SH5: `FACTORY_PLAN` required, the board refused at integration, a near-miss recorded); the remaining sentences are in §Global Constraints |
| A6 | a death mid-run | the relaunch line in §Dispatch |
| A7 | a landing | §Dispatch step 5 |
| A8 | a task can close a claim | SP5 flips `reasoning-tokens-not-itemised`, restates `d5-activity-export`, opens four gap rows with `closes_by` |
| A9 | a hold is the right call | spend: three seats ≈ $6–15 against $111 — no hold; `lint` on main `ok @08426bb03b9d` (M6) — no hold; no switch before wave 5's tests; the general sequencing rule in §Dispatch is the pre-check |
| A10 | the operator will be asked | three questions, §Operator questions |
| A11 | the session will reset | the handoff line |
| A12 | a re-plan is needed | §Dispatch's rule-A1 paragraph |
| A13 | a hook, or a second reader of something the tree derives | SP3's managed-settings file is read by every Claude Code launch; the degrade is measured — with nothing listening the exporter logs `FAILED (connect ECONNREFUSED)` and the session continues (Assumption 9b); no Claude hook is added; SP4's brief reads the store for the Seats dollars and prints nothing when the stream is absent (`--store /nonexistent` in `lint` and the hook) |
| A14 | a deny rule | none added (the tee forwards every byte; the audit gains a field); the collector's unit refuses its own egress (`IPAddressDeny=any`) — no operator or orchestrator recipe command reaches it |

## Not in this plan

- `GET /api/v1/activity` through a lane with a broker-injected management key (a second secret the operator has not minted); the weekly manual export continues (answer 4).
- Codex dollars (the rollout carries tokens and a weekly percentage); a `codex` row in `report spend` waits for a producer.
- The store's `0700` flip (question 2): one XS task after this plan, on the operator's word.
- The concurrently-open ledger chain's per-record refusal in `_merge_jsonl` and the store-writers lint fix round (D11) — not this plan's item regardless of that chain's current key.
- Pricing OpenRouter from a table; the `cost.usage`, `session.count` and `active_time` metrics in the ingest (the cost metric equals the events' sum — Assumption 9e).
- A SQLite index; the seat harness's own usage line (D1); a Helm tile for spend; a driver guard against two in-flight seats sharing a file across plans (concept 2026-09-08a).

## Errata applied

Full row-by-row detail from the 22/42 judgement lives in `docs/reviews/plan-judgements/2026-09-08-spend-telemetry.md` beside that round; this is the changelog, one clause per item, pointing at the Assumption/Decision/Task that now carries the content — not a restatement of it.

| # | change |
|---|---|
| 1 | SP8/SP7 named as `INGEST_MODULES` entries with the `ingest_result.py` idiom |
| 2, 10, 15, 16, 19, 24 | §Waves/§Dispatch carry the tool's live output; the dry-run line reads `"SP1"` |
| 3 | no two tasks in one wave share a touched file (D9) |
| 4 | `tests/evidence/test_streams_policy.py` everywhere, no `test_streams.py` |
| 5, 29 | SP4 names the producer and rule per source with an `unknown` arm (D12) |
| 6 | `query_source` moved from SP2 to SP7 |
| 7 | §Operator step 2 names the rollback generation (47) |
| 8 | §Decisions D1–D12 and §Operator questions 1–3, each with reason, alternative, recommendation and default |
| 9, 21 | SP1's tee: the fixture drives `responseheaders`, a split usage frame, then `response` (Interfaces, Tests 1–3) |
| 11 | `addon` named in Assumption 3 and SP1's acceptance/subject |
| 12 | SP1's usage file is 0644 under the unit's umask like `audit.jsonl`, no tmpfiles rule (D3) |
| 13 | `limit-event` keyed `(session_id, request_id)`, an idempotency test, a two-tombstone fixture |
| 14, 26 | the collector never writes the store (D3/D4); `telemetry-eval` pins `InaccessiblePaths=-/var/lib/evidence`; SP7 reads it as the operator |
| 17, 27 | the allowlist is a rule (`keep_keys`, D5) at the data-point and log contexts; `telemetry-vm` proves the four identity keys plus `user.name` absent |
| 18 | SP1 Tests 2/13: forwarded bytes and headers unchanged |
| 20 | D8, `_request_id`, the audit record gains `request_id` |
| 22 | SP3's eight variables as an attrset; `telemetry-eval` asserts the name set by equality, no `OTEL_LOG_*` name |
| 23 | `tests/unit/96-evidence-runbook.bats` |
| 25 | `hosts/core/default.nix` in SP3's touches, mutant E (import removed → red) |
| 28 | the codex row is `out:` (Spec-to-task map) |
| 30 | SP4 pastes the exact refusal string, tested byte-for-byte |
| 31 | SP2 Tests row 4: a string-finding fixture, the traceback line as the expected red |
| **A** | SP7's fence/stderr/exit-code contract inlined in its own Interfaces rather than pointed at SP8 across a section boundary a briefed seat never sees |
| **B** | SP4's Interfaces name `model_id` explicitly as the field pricing reads for `factory-agent` rows, noting it equals `role_model` today (§SP4 Interfaces) |
| **C** | this section compressed from a 37-row per-item table into a changelog; per-task Facts lines cite Assumption numbers instead of restating their text |
| **D** | §Waves/§Dispatch's cross-plan paragraph and sequencing rule re-measured live at Ship (Assumption 15) and restated as a general rule rather than a status-pinned gate that could go stale |
| **E** | SP2 and SP6 apply SP7's bracketed-model-id split rule (Assumption 5) to `factory-agent.model` and `main-session.by_model[*].model`, with a `model_suffix` sibling field and a `claude-opus-5[1m]` fixture row in each |
| **F** | `factory-agent.messages`, `main-session.messages` and `main-session.by_model[].messages` renamed to `message_count` everywhere (Interfaces, kind literals, Tests rows) — `messages` sits inside `streams.FORBIDDEN` and the fence refuses it regardless of declared class |
| **G** | the MAX-per-`message.id` dedup is scoped `(file, message.id)`; SP2's `workflow-dedup` fixture gains a second agent file reusing `msg_fixture_grow` at 500, asserting the two files' per-file maxima are summed (`7912 + 500`), not deduplicated globally |
| **H** | SP7's Interfaces name explicit refusal arms for a data point or log record missing `session.id` (`session_id: missing`) or `timeUnixNano` (`timeUnixNano: missing`), each with a planted fixture line and mutant |
| **I** | SP1's `_record_usage` never raises out of the `response` hook: a write failure (`usage_log`'s directory absent, EACCES, ENOSPC) is caught, logged to stderr as one line, and the flow completes; a Tests row drives it with an unwritable directory |
| **J** | SP1 gains a Tests row proving `USAGE_TAIL_BYTES = 65536` is real: a usage frame padded past the cap in one fixture (still `ok`), a usage frame that itself exceeds the cap in another (`unparsed`); mutants against a shrunk constant and a keep-first-64KiB trim |
| **K** | SP3's telemetry checks in scope at the gate: `telemetry-eval` and `telemetry-vm` both added to SP3's `acceptance` and to its commit subject's `(test: …)` list, alongside `host-core, lint` |

---

## Tasks

### SP1 (code, S) — the broker records every OpenRouter response's usage: cost, the cache split, provider and generation id, one JSONL line per request beside the audit line, ingested into the `openrouter-usage` stream

**dependsOn:** none

The heading's "ingested into the `openrouter-usage` stream": this task declares the stream and writes the raw line; the ingest verb is SP8 — one commit per concern. The stream flag exists so the broker never buffers a completion (the seat's latency; the reasoning documented in `_request_body_might_stream` and `_deny_request`): for a completions path it becomes a tee that forwards every byte unchanged, for every other SSE path it stays `True` byte for byte (Assumption 2).

**Files:**
- Create: `tests/broker/test_usage_log.py`, `tests/evidence/fixtures/openrouter-usage/usage.jsonl` (the four-line raw file SP8 reads — one `ok` line with Assumption 4's shape and `"gen_id": null`, one `no-usage`, one `unparsed`, one with `"model": "Bad Model"`; synthetic 32-hex request ids)
- Modify: `pkgs/broker/policy.py`, `nixosModules/egressBroker.nix` (`usage_log` and `usage_path_prefixes` in `renderPolicy`, the `usagePathPrefixes` submodule option), `flake.nix` (two `host-core` assertions), `pkgs/evidence/streams.py` (the kind), `tests/evidence/test_streams_policy.py` (the valid row in the per-kind table; three refused rows)

**Interfaces:**
- Policy JSON gains `usage_log` (the addon defaults it to `os.path.join(os.path.dirname(audit_log), "usage.jsonl")`, so the 41 existing tests need no change) and `usage_path_prefixes` (default `["/api/v1/chat/completions"]` in the addon AND in the Nix option `usagePathPrefixes`); `renderPolicy` renders `usage_log = "/var/lib/egress-broker/${name}/usage.jsonl"; usage_path_prefixes = i.usagePathPrefixes;`.
- `_request_id(self, flow) -> str`: `flow.metadata.setdefault("egress_request_id", uuid.uuid4().hex)` — minted once per flow, whichever hook asks first; `_audit`'s record gains `"request_id": self._request_id(flow)` after `"instance"`.
- `_usage_path(self, flow) -> bool`: `bool(_prefix_match(flow.request.path, self.usage_path_prefixes))`.
- `_usage_tee(self, flow)` returns `tee(data: bytes) -> bytes`: appends `data` to `flow.metadata["egress_usage_tail"]` (a `bytearray`), trims it to the last `USAGE_TAIL_BYTES = 65536`, returns `data` unchanged (`b""` → `b""`); never decodes, never raises.
- `responseheaders`: `if content_type.startswith("text/event-stream"): flow.response.stream = self._usage_tee(flow) if self._usage_path(flow) else True`. `response`: `self._audit(flow, "allow", "ok")` then `self._record_usage(flow)`. `error`: unchanged (no usage line).
- `_record_usage(self, flow)`: no-op unless `_usage_path(flow)`. Source: the tail when `"egress_usage_tail" in flow.metadata` (`streamed = True`), else `flow.response.raw_content` (`streamed = False`; `None` → `unparsed`). Parse: a tail → `_last_usage_frame(tail) -> dict | None` — split on `\n`, walk the lines from the END, take those starting with `data:`, skip `[DONE]`, `json.loads` each (a failure → continue), return the first object whose `usage` is a dict; a buffered body → `json.loads(raw)` when it is an object. `status` ∈ `ok`, `no-usage` (an object without `usage`), `unparsed` (nothing parseable; any exception → `unparsed`, the line still written). The record, keys in order: `ts_epoch` (`time.time()`), `instance`, `request_id`, `streamed`, `http_status`, `status`, `gen_id` (top-level `id`), `model`, `provider`, `cost_usd` (`usage.cost`), `upstream_cost_usd` (`usage.cost_details.upstream_inference_cost`), `is_byok`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `cached_tokens` and `cache_write_tokens` (`usage.prompt_tokens_details.*`), `reasoning_tokens` (`usage.completion_tokens_details.*`) — each null when absent; never the content. Written as `json.dumps(rec) + "\n"` with `open(self.usage_log, "a", encoding="utf-8")` — the process umask decides the mode, no `chmod`. **`_record_usage` never raises out of the `response` hook** (§Errata applied I): the open/write is wrapped `try/except OSError`; on failure it emits one stderr line `egress-broker: usage log write failed: {exc}` and returns without writing — the audit line (already written by the time `_record_usage` runs) and the flow both still complete normally.
- The kind (`streams.py`, after `lane-job`):

```python
    "openrouter-usage": {
        "stream": "ledger/openrouter-usage",
        "v": 1,
        "key": ("instance", "request_id"),
        "fields": {
            "src": ("enum", ("broker",)),
            "instance": "id",
            "request_id": ("re", r"^[0-9a-f]{32}$"),
            "ts_epoch": "num",
            "streamed": "bool",
            "http_status": "int",
            "status": ("enum", ("ok", "no-usage", "unparsed")),
            "gen_id": ("null", "id"),
            "model": ("null", "model-id"),
            "provider": ("null", "id"),
            "cost_usd": ("null", "num"),
            "upstream_cost_usd": ("null", "num"),
            "is_byok": ("null", "bool"),
            "prompt_tokens": ("null", "int"),
            "completion_tokens": ("null", "int"),
            "total_tokens": ("null", "int"),
            "cached_tokens": ("null", "int"),
            "cache_write_tokens": ("null", "int"),
            "reasoning_tokens": ("null", "int"),
        },
    },
```
- `host-core` (beside the `p.body_patch."openrouter.ai".path_prefixes` assertion): `p.usage_log == "/var/lib/egress-broker/openrouter/usage.jsonl" && p.usage_path_prefixes == [ "/api/v1/chat/completions" ]` and the same for `c.services.egress-broker.policy.seat` with `seat` in the path; message `host-core: broker policy must carry usage_log = /var/lib/egress-broker/<name>/usage.jsonl and usage_path_prefixes == [ "/api/v1/chat/completions" ] for openrouter and seat`.

**Facts** — Assumptions 1–5; `grep -n "def responseheaders" -A 4 pkgs/broker/policy.py` → the three-line body; `grep -n '"-s ' nixosModules/egressBroker.nix` → `"-s ${../pkgs/broker/policy.py}"`; `grep -n 'usage' pkgs/broker/policy.py tests/broker/test_policy.py` → nothing today.

**Steps:**
- [ ] Step 1 — the kind and its rows: `nix develop -c pytest tests/evidence/test_streams_policy.py -q -k openrouter` red before the entry (`KeyError: 'openrouter-usage'`), green after.
- [ ] Step 2 — `tests/broker/test_usage_log.py`; `nix develop -c pytest tests/broker -q` → expected red: `AttributeError: 'EgressPolicy' object has no attribute '_request_id'` — paste it.
- [ ] Step 3 — the addon; `nix develop -c ruff format pkgs/broker tests/broker`; `pytest tests/broker -q` → `test_policy.py`'s existing 56 plus every new `test_usage_log.py` test, all green (paste the actual total — do not expect exactly 56).
- [ ] Step 4 — `renderPolicy`, the option, the `host-core` assertions; red first with the assertion and without the render (`nix build .#checks.x86_64-linux.host-core -L --no-link` → `error: … host-core: broker policy must carry usage_log …`), then green.
- [ ] Step 5 — `addon`, `evidence-unit`, `host-core`, `lint` green; one commit.

**Tests** (`tests/broker/test_usage_log.py`; every flow `https_flow("openrouter.test", "/api/v1/chat/completions")` through `addon.requestheaders`, `addon.request`, a response, `addon.responseheaders`, the tee, `addon.response`; `usage_lines(path)` like `audit_lines`):

| # | assertion | fixture row that discriminates | mutant |
|---|---|---|---|
| 1 | an SSE completion → one `ok` line: `cost_usd == 9.9e-07`, `gen_id is None`, `provider == "DeepInfra"`, `model`, the six token fields, `streamed is True`, `http_status == 200` | four chunks: `: OPENROUTER PROCESSING\n\n`, a content frame WITHOUT usage, the usage frame (Assumption 4's object, `"id": null`) split across two chunk calls, `data: [DONE]\n\n`; then `b""` | (A) the tee returns without buffering → `unparsed`; (B) the FIRST `data:` frame → `no-usage`; (C) the tail keeps only the last chunk → `unparsed` |
| 2 | the tee forwards bytes unchanged: `b"".join(returned) == b"".join(sent)`; the end call returns `b""` | the same chunks | the tee returns `b""` for a chunk |
| 3 | a buffered JSON completion → `ok`, `gen_id == "gen-fixture-1"`, `streamed is False`; `f.response.stream` not callable | `"id": "gen-fixture-1"` at the top level and an `id` key inside `usage` | `gen_id` read from `usage.id` |
| 4 | a completions object without `usage` → `no-usage`, every token field null | `{"id": "gen-2", "choices": []}` | the branch raises `KeyError` |
| 5 | `b"<html>"` and an SSE stream with no `data:` frame → two `unparsed` lines, no exception | both | the exception propagates |
| 6 | `GET /api/v1/models` with a `usage` object in its body writes NO line; its SSE variant leaves `f.response.stream is True` | `{"data": [], "usage": {"cost": 1}}` | (D) the path rule removed; the `True` arm dropped |
| 7 | a completions SSE path makes `f.response.stream` callable | as 1 | `stream = True` for every SSE |
| 8 | the audit and usage lines of one flow share a 32-hex `request_id`; two flows differ | two flows | `_request_id` mints per call; the field dropped from `_audit` |
| 9 | no `usage_log` in the policy → `<dir of audit_log>/usage.jsonl`; with the key, that path | `load_addon` with and without | `policy["usage_log"]` (KeyError) |
| 10 | after `os.umask(0o022)` the file's `S_IMODE` is `0o644` | one line | an `os.chmod(path, 0o600)` after the write |
| 11 | a flow with `f.error` set writes no usage line | `addon.error(f)` | `error` calls `_record_usage` |
| 12 | the nested fields come from the nested objects | `cached_tokens: 5`, `reasoning_tokens: 7` planted | `cached_tokens` read from `usage.cached_tokens` (→ null) |
| 13 | `response` leaves `f.response.headers` and `raw_content` byte-identical | as 3 | `response` assigns `flow.response.content` |
| 14 (`test_streams_policy.py`) | the valid row accepted; `cost_usd: "9.9e-07"` → `cost_usd: not a num`; `model: "Bad Model"` → `model: not a model-id`; `status: "weird"` → `status: not in enum (ok|no-usage|unparsed)` | three rows | `cost_usd` declared `("null", "id")` |
| 15 (`host-core`) | both policies carry `usage_log` and the prefix list | the eval | `usage_log` rendered as `audit.jsonl` |
| 16 | `usage_log`'s directory unwritable (`chmod 0o000`) → the flow still completes, `_audit`'s line is still written, stderr carries `usage log write failed`, no exception escapes `response` | an unwritable dir | (I) the exception propagates out of `response` |
| 17 | a usage frame padded past `USAGE_TAIL_BYTES` (65536 bytes of a leading content frame, then the real usage frame) → still `ok`, `cost_usd == 9.9e-07`; a usage frame that itself exceeds the cap → `unparsed` | a padded chunk sequence; an oversized single usage frame | (J) `USAGE_TAIL_BYTES = 64`; the trim keeps the FIRST 64 KiB instead of the last |

**touches:** pkgs/broker/policy.py, tests/broker/test_usage_log.py, nixosModules/egressBroker.nix, flake.nix, pkgs/evidence/streams.py, tests/evidence/test_streams_policy.py, tests/evidence/fixtures/openrouter-usage/usage.jsonl
**acceptance:** addon, evidence-unit, host-core, lint
**commit subject:** `broker: every OpenRouter completion's usage recorded beside the audit line — the SSE tee keeps the last usage frame, a write failure never escapes the response hook, the request id joins both records, the openrouter-usage kind declared (test: addon, evidence-unit, host-core, lint)`

### SP1b (code, S) — SP1 fix round: every nested usage detail guarded like usage itself so the response hook never raises, a broker-minted deny writes no usage row, upstream cost read from its nested field, instance pinned on the record, a non-200 http_status pinned, the kind's request_id regex and key discriminated, the fixture's trailing newline closed; the body pastes red and green

**dependsOn:** none (a fix round stands on its own key; it carries SP1's commit 9f89135 forward)

Rule A1: SP1b is SP1's one fix round; a second rejection closes the chain and SP1 re-plans as SP1r under the pinned planning workflow.

Gate `docs/reviews/2026-09-08-opus-review-sp1-SP1.md` — REJECTED on one MAJOR (`plan_defect: implementer`, secondary `missing-case`); every other contract item met, all 22 named mutants dead, all four checks green under `--rebuild`. Fresh workspace from main: `git fetch -q ~/factory/ws/sp1/SP1 task/SP1 && git cherry-pick -n FETCH_HEAD` carries SP1's commit 9f89135 (base 46f113b) as staged changes — if `docs/OPERATIONS.md` or `docs/MAP.md` conflicts, take main's copy (`git checkout HEAD -- <file>`; regenerate the map with `python3 pkgs/evidence/repomap.py --root . write`). SP1's contract stands; everything below is edited on top of the cherry-pick; ONE commit at the end with this section's subject — SP1's subject is never reused. Line numbers below are 9f89135's.

1. **`_record_usage` raises on a hostile nested detail (MAJOR-1).** `policy.py:217-219` trusts `prompt_tokens_details`, `completion_tokens_details` and `cost_details` (`usage.get(...) or {}`) while only `usage` itself is type-guarded; a non-empty non-dict survives the `or {}` and the following `.get` raises `AttributeError` straight out of `response(flow)` — buffered and streamed alike — and no line is written, the exact hole Errata I closed everywhere else. Fix: guard each of the three the same way `usage` is guarded — `d = usage.get(key); d = d if isinstance(d, dict) else {}` — so a hostile detail degrades to null fields under the outer object's own status, never an exception. Three fixtures (one per detail: a string, a list, a number), each driven buffered and streamed: red before the fix with the review's own `AttributeError: '<type>' object has no attribute 'get'`, zero usage lines; green after — `status` unaffected, the guarded fields null, no exception, `flow.response` untouched. Mutant: drop the `isinstance` guard on any one detail → the fixture's `AttributeError` returns, red.
2. **A broker-minted deny writes a usage row (MINOR-1).** `_deny` (`:270-282`) sets `flow.response` to the synthetic 403 before calling `_audit`; by the time `response()` runs, `_audit`'s `egress_audited` guard (`:126-129`) already fired, so `_audit(flow, "allow", "ok")` no-ops there — but `_record_usage` has no equivalent guard and still writes `status: "unparsed"`, `http_status: 403` for a completions request the broker itself refused. `egress_audited` can't discriminate allow from deny (it is `True` in both cases by then), so the fix is a new flag: `_deny` sets `flow.metadata["egress_denied"] = True` before building the response; `_record_usage` returns immediately when that flag is set — the response is the broker's own, never upstream's. Fixture: a flow denied by `_check`'s allowlist on the completions path, driven `requestheaders` → `response`; assert zero usage lines and one audit line, `verdict: "deny"`. Mutant: drop the flag check from `_record_usage` → the row reappears, red.
3. **`upstream_cost_usd`'s source is untested (MINOR-2).** `:231` already reads `cost_details.get("upstream_inference_cost")` — no code change. Fixture: `usage.cost = 1.0`, `usage.cost_details.upstream_inference_cost = 0.5` (deliberately different); assert `upstream_cost_usd == 0.5`. Mutant: read it flat off `usage.get("upstream_inference_cost")` → the field goes null, red.
4. **`instance` on the record is untested (MINOR-3).** `:222` already sets `"instance": self.instance` — no code change; it is half the kind's `key`. Fixture: `self.instance == "openrouter-fixture"`; assert the field on the written line. Mutant: drop the key from the returned dict → the assertion raises `KeyError`, red.
5. **`http_status` is pinned only at 200 (MINOR-4).** `:225` already reads `flow.response.status_code` live — no code change. Fixture: a 429 JSON error body on the completions path → `status: "no-usage"`, `http_status: 429` (the review's probe 4 shape). Mutant: hardcode `200` → the 429 fixture fails, red.
6. **The kind's `request_id` regex and key are untested (MINOR-5).** `streams.py:527` (`("re", r"^[0-9a-f]{32}$")`) and `:523` (`"key": ("instance", "request_id")`) — no code change; two additions to `tests/evidence/test_streams_policy.py`. Regex: `{**OPENROUTER_USAGE, "request_id": "g" * 32}` — 32 chars, valid `id`-class, outside the hex regex — refused `["request_id: not a re"]`. Key: two rows sharing `instance`, differing only in `request_id`, both passed to `evidence.replace_stream(store, "ledger/openrouter-usage", rows)`; `evidence.read` returns both (2 rows, not 1) — the pair that discriminates a key missing `request_id`. Mutants: widen `request_id`'s class to plain `"id"` → the regex row passes, red; reduce `"key"` to `("instance",)` → the same-instance pair collapses to one row, red.
7. **The fixture is unvalidated and unterminated (MINOR-7).** `tests/evidence/fixtures/openrouter-usage/usage.jsonl`'s last line carries no trailing `\n` (`cat -A … | tail -1` shows no `$`) — indistinguishable from `evidence.read`'s torn-last-line drop, exactly the shape SP8 must tell apart from a genuinely bad row. Fix: append the newline. New test: read the four lines, `json.loads` each, `streams.validate("openrouter-usage", row)` — the first three (`ok`, `no-usage`, `unparsed`) return `[]`; the fourth (`model: "Bad Model"`) returns exactly `["model: not a model-id"]`; assert the file's last byte is `\n`. Mutant: drop the trailing newline again → the last-byte assertion fails, red.

**Facts** (the review and the clone at 9f89135): `sed -n '215,220p' pkgs/broker/policy.py` → the three ungated `usage.get(...) or {}` lines; `sed -n '126,130p;270,283p' pkgs/broker/policy.py` → `_audit`'s `egress_audited` guard and `_deny`'s response-then-audit order; the review's probes reproduce `AttributeError: 'str' object has no attribute 'get'` (buffered, `cost_details`) and `AttributeError: 'list' object has no attribute 'get'` (buffered, `prompt_tokens_details`) and the same raise on the streamed/SSE path, zero usage lines each time, one audit line; `sed -n '520,545p' pkgs/evidence/streams.py` → the kind's `key` and `request_id` regex unchanged since SP1; `cat -A tests/evidence/fixtures/openrouter-usage/usage.jsonl | tail -1` → the last line with no trailing `$`.

**Steps:**
- [ ] Step 1 — the carried commit (`git status --short` shows SP1's nine files staged), then items 1–7's tests written first; `nix develop -c pytest tests/broker/test_usage_log.py -q -k nested_detail` red against the carried code, buffered and streamed — paste the exact `AttributeError` lines the review pasted.
- [ ] Step 2 — implement item 1 (the three `isinstance` guards) and item 2 (`egress_denied`); `nix develop -c pytest tests/broker -q` → green, paste the total.
- [ ] Step 3 — items 3–6 add tests only, no further code change; `nix develop -c pytest tests/broker tests/evidence/test_streams_policy.py -q` → green.
- [ ] Step 4 — item 7: append the newline, add the validate-every-line test; `nix develop -c pytest tests/evidence -q` → green (492 plus the new tests).
- [ ] Step 5 — `nix build .#checks.x86_64-linux.addon -L --no-link`; `… evidence-unit`; `… host-core`; `… lint` — all four green, last line of each pasted; items 1–2's mutants and items 3–7's new mutants run one at a time, killing line pasted, reverted; one commit, SP1b's subject byte for byte.

**touches:** pkgs/broker/policy.py, tests/broker/test_usage_log.py, tests/broker/test_policy.py, nixosModules/egressBroker.nix, flake.nix, pkgs/evidence/streams.py, tests/evidence/test_streams_policy.py, tests/evidence/fixtures/openrouter-usage/usage.jsonl
**acceptance:** addon, evidence-unit, host-core, lint
**commit subject:** `broker: SP1 fix round — every nested usage detail guarded like usage itself so the response hook never raises, a broker-minted deny writes no usage row, cost source, instance, http_status, the request-id regex and key, the fixture newline all pinned (test: addon, evidence-unit, host-core, lint)`

### SP2 (code, S) — the ledger extractor runs on this host: the string-finding crash fixed, the MAX-per-message-id dedup as a tested rule, the 429 tombstones as a `limit-event` stream, and `backfill` over every transcript

**dependsOn:** SP1

The heading's "`backfill` over every transcript": this task keeps `backfill`'s scope (every workflow directory) and makes it run; the main-session files — where this host's thirteen tombstones live — are SP6's walk, so this task stays S. The tombstone reader is one function used by both walks. The dedup rule itself is scoped `(file, message.id)`, never `message.id` alone across files (§Errata applied G) — the heading names the field, not the scope, so this does not touch it.

**Files:**
- Create: `tests/ledger/fixtures/workflow-dedup/journal.jsonl`, `tests/ledger/fixtures/workflow-dedup/agent-a3333333333333333.jsonl` (three assistant lines with `message.id` `msg_fixture_grow` — output 2 / 2 / 7912, input 2000 each, cache_read 4000 each, thinking 0 / 0 / 100; three with `msg_fixture_same` — output 100 / 100 / 100; one line without `message.id`, output 5; one line with `message.model: "claude-opus-5[1m]"`; two 429 tombstones of Assumption 7's shape, `requestId` `req_fixture_1` and `req_fixture_2`, one `sessionId`; one 500 error line without `quotaLimits`), `tests/ledger/fixtures/workflow-dedup/agent-a3333333333333334.jsonl` (a SECOND agent file reusing `message.id` `msg_fixture_grow` with output 500 — proves the dedup groups by `(file, message.id)`, not `message.id` alone, §Errata applied G), `tests/ledger/fixtures/workflow-strfinding/journal.jsonl` (`"findings": ["a string finding", {"severity": "minor", "file": "x.py", "issue": "obj"}, 3]`) with one agent file

- Modify: `tools/ledger/factory.py`, `tools/ledger/schema.md` (the dedup rule under `factory-agents.jsonl`; sections `limit-events.jsonl` and `main-sessions.jsonl`), `tests/ledger/test_factory.py`, `pkgs/evidence/streams.py` (`factory-agent.message_count`, `factory-agent.model_suffix`; the kinds `limit-event`, `main-session`), `tests/evidence/test_streams_policy.py`

**Interfaces:**
- `_usage_groups(lines) -> list[tuple[str | None, dict]]`: for every `type == "assistant"` line with a `message` object, the group id is `(file_path, message.id)` — never `message.id` alone, so two files that happen to share an id each keep their own maximum (Assumption 6, §Errata applied G); a line without a `message.id` is its own group. Per group each field takes the MAX over the group's `usage`: `input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens_details.thinking_tokens`. `_read_agent` sums the groups' maxima across every group in the file (and, when `backfill` walks several agent files for one run, across files too — each file's own per-`message.id` maximum is what gets summed); `message_count` = the number of groups in the file; `tool_uses`, `model`, timestamps unchanged.
- `_model_split(model_id) -> tuple[str, str | None]`: the shared helper (Assumption 5, SP7's rule) — split at the first `[`; the head must match `MODEL_ID_RE` (else the row is refused `model: not a model-id`); the bracketed tail without its brackets is `model_suffix`, `None` when there is no `[`. `_read_agent`'s `model`/`model_suffix` fields both come from this helper; SP6's `by_model[*]` entries reuse it identically.
- `_read_findings`: a `str` finding → `title = finding`, `severity`/`file`/`class` null; a `dict` → as today; anything else → skipped with stderr `factory.py: {journal}: {agentId}: finding {i} is neither a string nor an object, skipped`.
- The label join: `_labels(journal_file) -> dict[agentId, label]` from `result` events' `result.label`; `extract_run` sets `agent["label"] = labels.get(agent_id)`.
- `_limit_event(event, origin) -> dict | None`: for `isApiErrorMessage` true, `apiErrorStatus == 429` and a `quotaLimits` object `q` → a `limit-event` row: `session_id`/`request_id`/`at`/`error_kind` from the line's `sessionId`/`requestId`/`timestamp`/`error`, `api_error_status` 429, and `q`'s seven keys mapped one to one (`rateLimitType → rate_limit_type`, `status → limit_status`, `resetsAt → resets_at`, `overageStatus`, `overageDisabledReason`, `isUsingOverage`, `unifiedRateLimitFallbackAvailable → fallback_available`), `origin` as given; any other error line → `None`. `extract_run` collects them over every agent file (`origin = "agent"`); `extract` merges `limit-events.jsonl`.
- The kinds: `factory-agent.fields` gains `"message_count": "int"` and `"model_suffix": ("null", "id")` (§Errata applied E, F);

```python
    "limit-event": {
        "stream": "ledger/limit-events",
        "v": 1,
        "key": ("session_id", "request_id"),
        "fields": {
            "src": ("enum", ("transcript",)),
            "session_id": "id",
            "request_id": "id",
            "at": "ts",
            "api_error_status": "int",
            "error_kind": ("null", "id"),
            "rate_limit_type": "id",
            "limit_status": "id",
            "resets_at": ("null", "int"),
            "overage_status": ("null", "id"),
            "overage_disabled_reason": ("null", "id"),
            "is_using_overage": ("null", "bool"),
            "fallback_available": ("null", "bool"),
            "origin": ("enum", ("main", "agent")),
        },
    },
    "main-session": {
        "stream": "ledger/main-sessions",
        "v": 1,
        "key": ("session_id",),
        "fields": {
            "src": ("enum", ("transcript",)),
            "session_id": "id",
            "harness_version": ("null", "id"),
            "started": ("null", "ts"),
            "ended": ("null", "ts"),
            "message_count": "int",
            "tool_uses": "int",
            "limit_events": "int",
            "tokens": ("obj", {"in": "int", "out": "int", "cache_read": "int", "cache_write": "int", "thinking": "int"}),
            "by_model": ("list", ("obj", {"model": "model-id", "model_suffix": ("null", "id"), "message_count": "int", "in": "int", "out": "int", "cache_read": "int", "cache_write": "int", "thinking": "int"}), 8),
            "wall_s": "num",
        },
    },
```
  (`main-session` is declared here, red with its rows, so SP6 and SP7 never edit this file in one wave — D9.) The tombstone's `timestamp` has milliseconds — the `ts` class accepts 1–6 fraction digits.

**Facts** — Assumptions 5–7, 15; `grep -n 'title = finding.get\|tokens\["in"\] +=\|"label": None' tools/ledger/factory.py` → the crash line, the naive sum, the null label.

**Steps:**
- [ ] Step 1 — the kinds and their rows: `nix develop -c pytest tests/evidence/test_streams_policy.py -q -k 'limit_event or main_session'` red (`KeyError`), then green.
- [ ] Step 2 — the fixtures and tests; `nix develop -c pytest tests/ledger -q` → expected red lines: `AttributeError: 'str' object has no attribute 'get'` (row 4), `assert 7916 == 7912` (row 1), `KeyError: 'message_count'` (row 3).
- [ ] Step 3 — `factory.py`; `ruff format`; `pytest tests/ledger -q` green with every existing test unchanged (row 2 is the guard).
- [ ] Step 4 — `ledger-unit`, `evidence-unit`, `lint` green; one commit.

**Tests** (`tests/ledger/test_factory.py`):

| # | assertion | fixture row that discriminates | mutant |
|---|---|---|---|
| 1 | the dedup agent row: `tokens.out == 7912 + 500 + 100 + 5`, `tokens.in` the groups' maxima summed, `thinking == 100` | `msg_fixture_grow` in the FIRST agent file (first-wins → 2), `msg_fixture_same` (sum → 300), `msg_fixture_grow` reused at 500 in the SECOND agent file (a global-key mutant would dedup it away) | (A) MAX → first value; (B) MAX → sum; (E) the group key is `message.id` alone, not `(file, message.id)` |
| 2 | the existing `workflow` fixture's totals are unchanged (`test_factory_extract_rollup`) | its lines have no `message.id` | a missing `message.id` groups as one |
| 3 | `message_count == 3` on the dedup row's first file | two ids + one id-less line | `message_count` counts lines |
| 4 | the string-finding journal yields two finding rows (the string's `title_sha256 == sha256("a string finding")`, `severity is None`) and one stderr skip line for `3`; before the fix the traceback ends `AttributeError: 'str' object has no attribute 'get'` | `["a string finding", {…}, 3]` | (C) the `str` arm removed; the skip arm removed |
| 5 | `label == "review:N9:r2"` for the agent whose `result` event carries it, `None` for the other | keyed by `agentId` | the join keyed on `key` |
| 6 | two `limit-event` rows with every field of Assumption 7 (`resets_at == 1788680400`, `origin == "agent"`); `extract` twice → still two | two tombstones, one session | (D) key `(session_id,)`; `resets_at` stored as a string → `resets_at: not a int` |
| 7 | the 500 line yields no limit event | one planted line | the status test dropped |
| 8 | every emitted row validates; no row carries `cwd`, `gitBranch`, `slug` | the tombstone carries all three on the wire | a `cwd` field copied → `cwd: forbidden name` |
| 9 (`test_streams_policy.py`) | valid rows for both kinds; `origin: "other"` → `origin: not in enum (main|agent)`; `factory-agent.message_count: "3"` → `message_count: not a int` | three rows | `origin` declared `"id"` |
| 10 | `model == "claude-opus-5"`, `model_suffix == "1m"` for the bracketed fixture line; the un-bracketed lines carry `model_suffix is None` | the `claude-opus-5[1m]` line | the split at `]` instead of `[`; the name passed through unsplit → `model: not a model-id` |

**touches:** tools/ledger/factory.py, tools/ledger/schema.md, tests/ledger/test_factory.py, tests/ledger/fixtures/workflow-dedup/journal.jsonl, tests/ledger/fixtures/workflow-dedup/agent-a3333333333333333.jsonl, tests/ledger/fixtures/workflow-dedup/agent-a3333333333333334.jsonl, tests/ledger/fixtures/workflow-strfinding/journal.jsonl, tests/ledger/fixtures/workflow-strfinding/agent-a4444444444444444.jsonl, pkgs/evidence/streams.py, tests/evidence/test_streams_policy.py
**acceptance:** ledger-unit, evidence-unit, lint
**commit subject:** `ledger: the extractor runs on this host — string findings accepted, usage deduplicated as MAX per message id per file (summed across files), the bracketed model id split into model/model_suffix, the limit-event and main-session kinds declared, the agent's label joined from the journal (test: ledger-unit, evidence-unit, lint)`

### SP2b (code, S) — SP2 fix round: `factory-finding.severity`/`.file` admit null so a string finding survives `replace_stream`, the discriminating test moved onto `extract` and `backfill` over the string-finding fixture, the quotaLimits-object arm fixtured, five fixtures gain a trailing newline; the body pastes red and green

**dependsOn:** none

Gate `docs/reviews/2026-09-08-opus-review-sp2-SP2.md` — REJECTED on one MAJOR (`plan_defect: missing-case`, secondary `implementer`): `_read_findings` sets `severity`/`file`/`class` to `None` for a string finding exactly as the section's Interfaces said, but `pkgs/evidence/streams.py` never made the matching change — `factory-finding.severity` is bare `"id"` and `.file` is `("path", ("",), 200)`, both non-nullable, and `file` is also one of the three key components. `factory.extract` over the branch's own `workflow-strfinding` fixture therefore raises `streams.StreamRefused: row 0: severity: null not allowed; row 0: file: null not allowed` — the `AttributeError` the task was created to fix was replaced by a `StreamRefused`, not removed, so `backfill` still cannot walk a transcript carrying a string finding. The delivered test (`test_string_finding_is_accepted`) never saw this because it called `factory._read_findings(journal, "run")` directly instead of going through `factory.extract`. Everything else in the section was delivered and well tested: 19 of 22 mutants dead (all 15 named), `ledger-unit`, `evidence-unit` and `lint` green under `--rebuild`, `pre-commit` green, the commit's ten `touches` files exact. Five MINORs; two are carried here (MINOR-4's missing trailing newline on five fixture files, MINOR-2's untested `quotaLimits`-object arm of `_limit_event`); three are judged not carried, with the one-line reason each stated in item 4 below. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/sp2/SP2 task/SP2 && git cherry-pick -n FETCH_HEAD` carries SP2's commit `2d40f41` as staged changes (if `docs/OPERATIONS.md` conflicts, `git checkout HEAD -- docs/OPERATIONS.md`; if `docs/MAP.md` conflicts, `python3 pkgs/evidence/repomap.py --root . write`). SP2's contract stands; these are the corrections (line numbers are `2d40f41`'s):

1. **The kind admits a null `severity` and `file` (MAJOR-1, the plan-defect half).** `pkgs/evidence/streams.py:482` `"severity": "id"` becomes `"severity": ("null", "id")`; `:483` `"file": ("path", ("",), 200)` becomes `"file": ("null", ("path", ("",), 200))`. `file` stays in the key tuple at `:475` (`("run_id", "file", "title_sha256")`) unchanged — `replace_stream`'s `keyed(r)` (`pkgs/evidence/evidence.py:176`, `tuple(r[f] for f in key_fields)`) reads a `None` value as an ordinary hashable tuple element, and `_check_cls`'s null branch (`streams.py:684-686`) is what actually gated the refusal, not the key machinery — so no key-handling code changes, only the two field declarations. New test in `tests/evidence/test_streams_policy.py`: `test_factory_finding_accepts_null_severity_and_file` asserts `streams.validate("factory-finding", {**FACTORY_FINDING, "severity": None, "file": None}) == []`. Mutant **A** revert `:482`/`:483` to SP2's form → `streams.StreamRefused`-shaped refusal returns (`["row 0: severity: null not allowed", "row 0: file: null not allowed"]` from `validate`), the new test red.
2. **The discriminating test moves onto `extract`, not `_read_findings` (MAJOR-1, the implementer half).** `test_string_finding_is_accepted` (`tests/ledger/test_factory.py:1576`) is rewritten to call `factory.extract(STRFINDING_FIXTURE, out)` and read the two rows back from `out / "factory-findings.jsonl"` instead of calling `factory._read_findings` directly; the same assertions move onto the written rows (`title_sha256`, `severity is None`, `file is None`, `class is None` for the string row; `severity`/`file`/`title_sha256` for the dict row) and the stderr skip-line assertion is unchanged. Mutant **A** (above) kills this test too, now that it goes through the store — proving the rewrite is the one that would have caught SP2's defect.
3. **`backfill` proven over the string-finding fixture (test row 8 / the heading's own claim).** New test `test_backfill_walks_workflow_with_string_finding(tmp_path)`: build `tmp_path/proj/subagents/workflows/wf_str/` by copying `STRFINDING_FIXTURE`'s `journal.jsonl` and its one agent file into it (the shape `backfill`'s glob `**/subagents/workflows/wf_*` requires, `tools/ledger/factory.py:385-387`), call `factory.backfill(tmp_path / "proj", ledger_dir)` → returns `1`, raises nothing, and `ledger_dir / "factory-findings.jsonl"` holds 2 rows including the null-severity/null-file one. Mutant **A** (above, reverted) → `backfill` raises `streams.StreamRefused` mid-walk, red — this is the fixture the section's heading promised ("`backfill` over every transcript") and SP2 never actually exercised for the string-finding case.
4. **The MINORs, judged.** Carried: MINOR-4 — the five fixture files (`tests/ledger/fixtures/workflow-dedup/agent-a3333333333333333.jsonl`, `…agent-a3333333333333334.jsonl`, `…/workflow-dedup/journal.jsonl`, `…/workflow-strfinding/journal.jsonl`, `…/workflow-strfinding/agent-a4444444444444444.jsonl`) each gain a trailing newline, closing the same house habit SP1b already closed on its own fixture; no mutant needed, proven by the diff carrying no `\ No newline at end of file` marker (`git diff --check` on the five paths). Carried: MINOR-2 — new test `test_limit_event_requires_quotalimits_dict`: a 429 tombstone (`isApiErrorMessage: true, apiErrorStatus: 429`) with `quotaLimits` ABSENT, and a second with `quotaLimits: "throttled"` (a non-dict) → `factory._limit_event(event, "agent") is None` for both. Mutant **B** `tools/ledger/factory.py:292-293` (`if not isinstance(q, dict): return None`) replaced by `q = q or {}` → both assertions fail (a `limit-event` row is built from `{}.get(...)` → `None` fields instead of being refused), red. Not carried, one line each: MINOR-1 (`_model_split` lacks type annotations and its `None` return sits outside the stated signature) — a cosmetic annotation gap with no behavioural surface and no surviving mutant; deferred to a future pass rather than spent here. MINOR-3 (the dedup fixture repeats the bracketed model id on three lines instead of one) — the review's own measurement says this is behaviourally identical (`_read_agent` keeps the first assistant line's model) and rewriting the fixture risks perturbing the already-passing dedup byte totals for no test gain. MINOR-5 (the same-wave collision with SP8 on `tests/evidence/test_streams_policy.py` / `pkgs/evidence/streams.py`) — this is an integration-order note for whoever merges the two branches, not a defect in SP2's tree in isolation; the review's own merge instructions (keep both `VALID_ROWS` entries and both `KINDS` blocks, re-run `evidence-unit` on the merge result) stand as written and nothing in this fix round changes them.
5. **The commit body** pastes: the red of the new `test_factory_finding_accepts_null_severity_and_file`, `test_string_finding_is_accepted` and `test_backfill_walks_workflow_with_string_finding` against the carried (unfixed) tree — all three fail, the first two with the `null not allowed` refusal, the third with `streams.StreamRefused` raised out of `backfill` — and `test_limit_event_requires_quotalimits_dict` red under mutant **B** applied to the carried tree; the green lines after the last edit (`nix build .#checks.x86_64-linux.ledger-unit -L --no-link`, `… evidence-unit`, `… lint` — the last line of each); the mutant table A–B with the killing line each; SP2's 15 named mutants still die (re-run, not re-pasted). The FACTORY-RESULT block in the grammar: `FACTORY-CHECKS ledger-unit=pass evidence-unit=pass lint=pass`, `FACTORY-COMMITS 1`.

- [ ] **Step 1: The carried commit, then the tests** — `test_factory_finding_accepts_null_severity_and_file`, the rewritten `test_string_finding_is_accepted`, `test_backfill_walks_workflow_with_string_finding`, `test_limit_event_requires_quotalimits_dict`, and the five fixtures' trailing newline; `nix develop -c pytest tests/evidence/test_streams_policy.py tests/ledger/test_factory.py -q` red against the carried (unfixed) tree, pasted verbatim. **Step 2: Implement** item 1's two field declarations. **Step 3: Green** — `nix develop -c ruff format pkgs/evidence tests/evidence tools/ledger tests/ledger` and `ruff check`; `nix develop -c pytest tests/evidence/test_streams_policy.py tests/ledger/test_factory.py -q`; `nix build .#checks.x86_64-linux.ledger-unit -L --no-link`; `… evidence-unit`; `… lint`; `nix develop -c githooks/pre-commit` — every one after the last edit. **Step 4: Mutants** A and B, one at a time, the killing line pasted, reverted; re-run SP2's own 15 named mutants and confirm they still die. **Step 5: One commit**, the subject below, the body per item 5.

**Tests (assertion → mutant; fixture → discriminating row):** `test_factory_finding_accepts_null_severity_and_file` (`streams.validate` returns `[]` for a null-severity/null-file row) → mutant A; the rewritten `test_string_finding_is_accepted` (two rows land in `factory-findings.jsonl` via `factory.extract`, string row's `severity`/`file`/`class` all `None`, `title_sha256` of the raw string, the stderr skip line for the third finding) → mutant A, fixture `tests/ledger/fixtures/workflow-strfinding/journal.jsonl`'s existing `["a string finding", {…}, 3]` list is the discriminating row (unchanged, only the assertion's entry point moves); `test_backfill_walks_workflow_with_string_finding` (`backfill` returns `1`, raises nothing, `factory-findings.jsonl` on disk holds 2 rows) → mutant A, discriminating row: the same fixture copied under a synthesized `subagents/workflows/wf_*` tree; `test_limit_event_requires_quotalimits_dict` (`_limit_event` returns `None` for a 429 with `quotaLimits` absent, and for `quotaLimits` a non-dict string) → mutant B, discriminating rows: two new in-test dicts, no new fixture file.

**touches:** pkgs/evidence/streams.py, tests/evidence/test_streams_policy.py, tests/ledger/test_factory.py, tests/ledger/fixtures/workflow-dedup/agent-a3333333333333333.jsonl, tests/ledger/fixtures/workflow-dedup/agent-a3333333333333334.jsonl, tests/ledger/fixtures/workflow-dedup/journal.jsonl, tests/ledger/fixtures/workflow-strfinding/journal.jsonl, tests/ledger/fixtures/workflow-strfinding/agent-a4444444444444444.jsonl
**acceptance:** ledger-unit, evidence-unit, lint
**commit subject:** `ledger: SP2 fix round — factory-finding's severity and file admit null so a string finding survives replace_stream, the test moved onto extract and backfill over the workflow-strfinding fixture, the quotaLimits-object arm of a 429 tombstone fixtured, five fixtures gain a trailing newline (test: ledger-unit, evidence-unit, lint)`

### SP3 (code, M) — Claude Code's OpenTelemetry into the evidence store: a loopback collector on core that drops identity before writing, pinned by a check and proven by a VM; the session environment carries the exporter variables

**dependsOn:** SP1

The heading's "the session environment": the variables ride an `env`-only `/etc/claude-code/managed-settings.json`, not `environment.sessionVariables` — a settings `env` block drives the exporter and overrides the shell (Assumption 9a), the file is Claude-Code-scoped and declarative, the build refuses two writers of that path (D6; question 1). "Into the evidence store": the collector writes its own `StateDirectory` and cannot open the store; the rows arrive through `evidence ingest otel` (SP7, D3). "Drops identity": an allowlist at the data-point and log-record contexts (D5).

**Files:**
- Create: `nixosModules/claudeTelemetry.nix`, `hosts/core/telemetry.nix`, `tests/integration/telemetry-vm.nix`
- Modify: `hosts/core/default.nix` (`./telemetry.nix` after `./seat.nix` in `imports`), `flake.nix` (`nixosModules.claudeTelemetry = import ./nixosModules/claudeTelemetry.nix;`, listed in `nixosConfigurations.core.modules`; `checks.telemetry-eval`; `checks.telemetry-vm = import ./tests/integration/telemetry-vm.nix { inherit pkgs; claudeTelemetryModule = self.nixosModules.claudeTelemetry; evidenceStoreModule = self.nixosModules.evidenceStore; }`), then `repomap.py --root . write`

**Interfaces** — `services.claude-telemetry`:
- options `enable`; `port` (`types.port`, default `4318`); `user` (`types.str`, default `config.services.evidence-store.owner`); read-only `env` (below) and `settingsFile` (`(pkgs.formats.json {}).generate "claude-code-telemetry-settings.json" { env = cfg.env; }`).
- `env` — exactly these eight names: `CLAUDE_CODE_ENABLE_TELEMETRY = "1"; OTEL_METRICS_EXPORTER = "otlp"; OTEL_LOGS_EXPORTER = "otlp"; OTEL_EXPORTER_OTLP_PROTOCOL = "http/json"; OTEL_EXPORTER_OTLP_ENDPOINT = "http://127.0.0.1:${toString cfg.port}"; OTEL_METRIC_EXPORT_INTERVAL = "5000"; OTEL_LOGS_EXPORT_INTERVAL = "5000"; OTEL_METRICS_INCLUDE_ACCOUNT_UUID = "false";` — no `OTEL_LOG_*` name ever.
- under `mkIf cfg.enable`: `assertions = [ { assertion = !config.services.claude-managed-settings.enable; message = "services.claude-telemetry and services.claude-managed-settings both write /etc/claude-code/managed-settings.json; enable one"; } ]`; `environment.etc."claude-code/managed-settings.json".source = cfg.settingsFile`; `services.opentelemetry-collector = { enable = true; package = pkgs.opentelemetry-collector-contrib; validateConfigFile = true; settings = …; }` with

```nix
settings = {
  receivers.otlp.protocols.http.endpoint = "127.0.0.1:${toString cfg.port}";
  processors = {
    "transform/allowlist" = {
      error_mode = "propagate";
      metric_statements = [
        { context = "resource"; statements = [ (keep keepResource) ]; }
        { context = "datapoint"; statements = [ (keep keepPoint) ]; }
      ];
      log_statements = [
        { context = "resource"; statements = [ (keep keepResource) ]; }
        { context = "log"; statements = [ (keep keepLog) ]; }
      ];
    };
    "filter/events" = {
      error_mode = "propagate";
      logs.log_record = [ ''attributes["event.name"] != "api_request" and attributes["event.name"] != "api_error"'' ];
    };
  };
  exporters = {
    "file/metrics" = { path = "${stateDir}/claude-metrics.jsonl"; flush_interval = "1s"; rotation = { max_megabytes = 64; max_backups = 8; }; };
    "file/logs" = { path = "${stateDir}/claude-logs.jsonl"; flush_interval = "1s"; rotation = { max_megabytes = 64; max_backups = 8; }; };
  };
  service = {
    telemetry.metrics.level = "none";
    pipelines = {
      metrics = { receivers = [ "otlp" ]; processors = [ "transform/allowlist" ]; exporters = [ "file/metrics" ]; };
      logs = { receivers = [ "otlp" ]; processors = [ "transform/allowlist" "filter/events" ]; exporters = [ "file/logs" ]; };
    };
  };
};
```
  where `stateDir = "/var/lib/opentelemetry-collector"`, `keep = keys: ''keep_keys(attributes, [${lib.concatMapStringsSep ", " (k: ''"${k}"'') keys}])''`, `keepResource = [ "service.name" "service.version" "os.type" "host.arch" ]`, `keepPoint = [ "session.id" "terminal.type" "type" "model" "query_source" "start_type" ]`, `keepLog = [ "event.name" "event.timestamp" "event.sequence" "session.id" "terminal.type" "model" "cost_usd" "cost_usd_micros" "duration_ms" "input_tokens" "output_tokens" "cache_read_tokens" "cache_creation_tokens" "request_id" "client_request_id" "speed" "query_source" "effort" "agent.name" "skill.name" ]` (Assumption 9c–d; `prompt.id` is not kept).
- `systemd.services.opentelemetry-collector.serviceConfig`: `DynamicUser = lib.mkForce false; User = cfg.user; SupplementaryGroups = lib.mkForce [ ]; ProtectSystem = lib.mkForce "strict"; ProtectHome = true; PrivateTmp = true; NoNewPrivileges = true; CapabilityBoundingSet = ""; RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX"; IPAddressDeny = "any"; IPAddressAllow = "localhost"; ReadWritePaths = [ stateDir ]; InaccessiblePaths = [ "-/var/lib/evidence" ];` (the module's `StateDirectory`, `WorkingDirectory`, `Restart`, `DevicePolicy` stay).
- `hosts/core/telemetry.nix`: `_: { services.claude-telemetry.enable = true; }` with a comment naming this plan and switch #23.
- `checks.telemetry-eval` (the `seat-eval` shape; `t = c.services.claude-telemetry; o = c.services.opentelemetry-collector; sc = c.systemd.services.opentelemetry-collector.serviceConfig;`), each assertion with a `telemetry-eval: …` message: (1) `t.enable` (`telemetry-eval: services.claude-telemetry must be enabled on core (hosts/core/telemetry.nix imported by hosts/core/default.nix)`); (2) `o.settings.receivers == { otlp.protocols.http.endpoint = "127.0.0.1:4318"; }`; (3) `o.validateConfigFile && lib.hasPrefix "otelcol-contrib" o.package.name`; (4) the four `keep_keys` strings equal the rendered lists, the contexts exactly `resource`/`datapoint` (metrics) and `resource`/`log` (logs); (5) `filter/events`' one statement equals the string above; (6) both exporter paths start `/var/lib/opentelemetry-collector/`, `pipelines.logs.processors == [ "transform/allowlist" "filter/events" ]`, `pipelines.metrics.processors == [ "transform/allowlist" ]`; (7) `sc.User == c.services.evidence-store.owner && sc.DynamicUser == false && sc.ProtectHome == true && sc.ProtectSystem == "strict" && sc.IPAddressDeny == "any" && sc.IPAddressAllow == "localhost" && sc.ReadWritePaths == [ "/var/lib/opentelemetry-collector" ] && lib.elem "-/var/lib/evidence" sc.InaccessiblePaths && sc.SupplementaryGroups == [ ]`; (8) `lib.sort lib.lessThan (builtins.attrNames t.env) ==` the eight names sorted, the endpoint and protocol values as above, `!(lib.any (n: lib.hasPrefix "OTEL_LOG_" n) (builtins.attrNames t.env))`; (9) `c.environment.etc."claude-code/managed-settings.json".source == t.settingsFile && !c.services.claude-managed-settings.enable`; (10) `lib.any (a: lib.hasInfix "enable one" a.message) c.assertions`.
- `tests/integration/telemetry-vm.nix` (`{ pkgs, claudeTelemetryModule, evidenceStoreModule }`): `nodes.machine` imports both modules, `services.claude-telemetry.enable = true`, `users.users.dalhaka = { isNormalUser = true; uid = 1000; }`; a `pkgs.writeText "telemetry-vm-probe.py"` stdlib script (Assumption 11's shape) POSTing to `http://127.0.0.1:4318/v1/metrics` and `/v1/logs`: the five keys `organization.id, user.account_uuid, user.id, user.email, user.name` on the RESOURCE, on the `claude_code.token.usage` DATA POINT (`type: cacheRead`, `model: claude-fable-5-1`, `session.id: sess-x`, `asDouble: 1234`) and on an `api_request` LOG RECORD (`event.name: api_request`, `model`, `cost_usd`, `input_tokens "2"`, `request_id: req_x`, `session.id`), plus a `user_prompt` record carrying `prompt: "SECRET PROMPT CONTENT"`. testScript:

```python
machine.wait_for_unit("opentelemetry-collector.service")
machine.wait_for_open_port(4318)
machine.succeed("${pkgs.python3}/bin/python3 ${probe}")
machine.wait_until_succeeds("test -s /var/lib/opentelemetry-collector/claude-metrics.jsonl")
machine.wait_until_succeeds("test -s /var/lib/opentelemetry-collector/claude-logs.jsonl")
machine.succeed("grep -q -F '\"cacheRead\"' /var/lib/opentelemetry-collector/claude-metrics.jsonl")
machine.succeed("grep -q -F 'api_request' /var/lib/opentelemetry-collector/claude-logs.jsonl")
machine.succeed("grep -q -F 'sess-x' /var/lib/opentelemetry-collector/claude-logs.jsonl")
for key in ["user.email", "user.id", "user.account_uuid", "organization.id", "user.name", "SECRET PROMPT", "user_prompt"]:
    machine.fail(f"grep -q -F '{key}' /var/lib/opentelemetry-collector/claude-metrics.jsonl /var/lib/opentelemetry-collector/claude-logs.jsonl")
machine.succeed("ss -ltnH | grep -q '127.0.0.1:4318'")
machine.fail("ss -ltnH | grep -q '0.0.0.0:4318'")
machine.fail("ss -ltnH | grep -q ':4317'")
machine.succeed("systemctl show opentelemetry-collector -p User --value | grep -qx dalhaka")
```

**Facts** — Assumptions 8–12; `sed -n '4,14p' hosts/core/default.nix` → the imports list; `grep -n 'validateConfigFile' <nixpkgs-host>/nixos/modules/services/monitoring/opentelemetry-collector.nix` → `default = isStorePath cfg.configFile;`; the datapoint and log contexts are the transform processor's documented contexts, proven at build time by `validateConfigFile`.

**Steps:**
- [ ] Step 1 — `telemetry-eval` first, before the host file exists: `nix build .#checks.x86_64-linux.telemetry-eval -L --no-link` → `error: … telemetry-eval: services.claude-telemetry must be enabled on core …` — paste it.
- [ ] Step 2 — the module, the host file, the import, the flake wiring; `telemetry-eval` green; `nix build .#nixosConfigurations.core.config.system.build.toplevel` builds (an OTTL syntax error fails this build: fix the statement, never disable `validateConfigFile`).
- [ ] Step 3 — the VM red: with the contexts set to `resource` only, `nix build .#checks.x86_64-linux.telemetry-vm -L --no-link` → `command `grep -q -F 'user.email' …` unexpectedly succeeded` — paste it; then §Interfaces' contexts, green.
- [ ] Step 4 — `host-core`, `lint` green; `repomap.py write`; one commit whose body pastes both reds and names the two new checks.

**Tests** (the two checks are the tests):

| # | assertion | discriminating input | mutant |
|---|---|---|---|
| 1 | VM: every identity key absent from both files, the point and the event present | the five keys on resource, point and record; `user.name` unlisted | (A) `context = "datapoint"` → `"resource"`; (H) `user.email` added to `keepPoint` |
| 2 | VM: `user_prompt`/`SECRET PROMPT` absent, `api_request` present | the two records | (B) the filter names prefixed `claude_code.` |
| 3 | VM: only `127.0.0.1:4318` listens | `ss` | (D) `endpoint = "0.0.0.0:4318"`; a `grpc` receiver added (`:4317`) |
| 4 | VM: the unit runs as `dalhaka` | `systemctl show` | (G) `DynamicUser` not forced |
| 5 | eval 1 | the core config | (E) `./telemetry.nix` removed from the imports |
| 6 | eval 2–6 | — | the endpoint on `0.0.0.0`; the core package; `validateConfigFile` dropped; a `keep_keys` list gains `user.email`; the datapoint statement removed; the `api_error` arm dropped; an exporter path under `/var/lib/evidence` |
| 7 | eval 7–10 | — | (C) `IPAddressDeny` removed; (J) `ProtectHome` false; `InaccessiblePaths` empty; `SupplementaryGroups` left; (F) `OTEL_LOG_USER_PROMPTS = "1"` added; `OTEL_METRICS_EXPORTER = "console"`; the etc source retargeted; the D6 assertion removed |

**touches:** nixosModules/claudeTelemetry.nix, hosts/core/telemetry.nix, hosts/core/default.nix, flake.nix, tests/integration/telemetry-vm.nix, docs/MAP.md
**acceptance:** telemetry-eval, telemetry-vm, host-core, lint
**commit subject:** `telemetry: Claude Code's OpenTelemetry through a loopback collector that keeps an allowlist of attributes on every data point and record, the exporter variables in an env-only managed-settings file, pinned by telemetry-eval and proven by telemetry-vm (test: telemetry-eval, telemetry-vm, host-core, lint)`

### SP8 (code, S) — `evidence ingest openrouter-usage`: the broker's `usage.jsonl` fenced to `/var/lib/egress-broker`, merged by request id, a torn last line reported and not refused

**dependsOn:** SP1

**Files:**
- Create: `pkgs/evidence/ingest_openrouter_usage.py`, `tests/evidence/test_ingest_openrouter_usage.py`, `tests/evidence/fixtures/openrouter-usage/torn.jsonl` (two good lines, then `{"ts_epoch": 1788906` with no newline)
- Modify: `pkgs/evidence/evidence.py` (`INGEST_MODULES["openrouter-usage"] = "ingest_openrouter_usage"`; the two parenthetical lists become `"|".join(INGEST_MODULES)`), `pkgs/evidence/SCHEMA.md` (a `ledger/openrouter-usage` row: kind, key, fields, writer)

**Interfaces:**
- `evidence ingest openrouter-usage [--root DIR] <path>…` (`main(argv)`, `argparse.ArgumentParser(prog="evidence ingest")`, `--store` as `ingest_result.py`; the subparser with `--root` default `/var/lib/egress-broker`, `paths` `nargs="+"`).
- `ingest(store, paths, root) -> (n, refused, torn)`: every path realpath-fenced under `root` before any read (`OutsideRoot` → stderr `evidence: ingest openrouter-usage: {p} is outside {root}`, exit 2, nothing written); an unreadable path → `…: {p}: not a usage file`, refused; the last line of a file with no trailing `\n` is `torn` — stderr `…: {p}: last line torn (the broker is writing); skipped`, not counted refused; any other non-object line → refused `…: {p}:{lineno}: not JSON`; a row = the object plus `kind: "openrouter-usage"`, `v: 1`, `src: "broker"`; `streams.validate` refusals printed one per reason `…: {p}:{lineno}: {reason}`; one `evidence.replace_stream(store, "ledger/openrouter-usage", rows)`; stdout `ingested {n} rows into ledger/openrouter-usage ({refused} refused)`; exit `0` when `refused == 0`, else `1`.
- `evidence ingest bogus` → stderr ends `(judgements|result|reviews|openrouter-usage)`, exit 2.

**Facts** — Assumption 5; SP1's fixture `tests/evidence/fixtures/openrouter-usage/usage.jsonl` (four lines: `ok`, `no-usage`, `unparsed`, `model: "Bad Model"`).

**Steps:**
- [ ] Step 1 — the tests; `nix develop -c pytest tests/evidence/test_ingest_openrouter_usage.py -q` → `StopIteration` from the loader — paste it.
- [ ] Step 2 — the module and the dispatch; `ruff format`; `pytest tests/evidence -q` green (the existing `test_ingest_table` included).
- [ ] Step 3 — `evidence-unit`, `lint`; one commit.

**Tests:**

| # | assertion | discriminating fixture | mutant |
|---|---|---|---|
| 1 | the four-line file → 3 rows, 1 refused (`model: not a model-id` with `:4:` on stderr), exit 1; `src == "broker"` on every row | the `Bad Model` line | `src` not added; the exit code always 0 |
| 2 | a second run → the same 3 rows | two runs | `append` instead of `replace_stream` (6 rows) |
| 3 | `torn.jsonl` → 2 rows, stderr contains `last line torn`, exit 0 | the truncated last line | the torn rule dropped (`not JSON` → exit 1) |
| 4 | a path outside `--root` → exit 2, no stream file; `--root` given a symlink to the fixture dir → accepted (realpath) | `tmp_path` outside; a symlinked root | the fence removed |
| 5 | `evidence ingest openrouter-usage --help` exit 0; `evidence ingest bogus` stderr ends `openrouter-usage)`, exit 2 | subprocess | the key missing from `INGEST_MODULES` |
| 6 | an empty file → `ingested 0 rows into ledger/openrouter-usage (0 refused)`, exit 0 | an empty file | `replace_stream([])` on a missing path raising |

**touches:** pkgs/evidence/ingest_openrouter_usage.py, pkgs/evidence/evidence.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_ingest_openrouter_usage.py, tests/evidence/fixtures/openrouter-usage/torn.jsonl
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: ingest openrouter-usage — the broker's usage.jsonl fenced to /var/lib/egress-broker and merged by request id, a torn last line reported not refused (test: evidence-unit, lint)`

### SP6 (code, S) — the main-session reader: one numbers-only `main-session` row per session file, the 429 tombstones from those files as `limit-event` rows, `backfill` walks both trees and prints its counts, `rollup --week` prints the main line

**dependsOn:** SP2

Inside decision 2026-09-05 answer 2 (numbers only; bodies never read): the row carries token counts by model, message and tool counts, timestamps, the harness version and the session id (the file's stem) — never `cwd`, `gitBranch`, `slug`, a prompt or a reply. The kinds are SP2's; this task is their writer.

**Files:**
- Create: `tests/ledger/fixtures/projects/-fixture-project/11111111-2222-4333-8444-555555555555.jsonl` (a `user` line; three assistant lines sharing `message.id` `msg_main_grow` for `claude-opus-4-1`, output 2 / 2 / 7912, cache_write 29050 and cache_read 34255 each; one assistant line for `claude-sonnet-4-5[1m]` (the bracketed vendor spelling), output 40, one `tool_use` block; a 429 tombstone (Assumption 7, `requestId` `req_main_1`); a 500 error line without `quotaLimits`; top-level `version: "2.1.258"`, `cwd`, `gitBranch`, `slug` on every line), `…/11111111-2222-4333-8444-555555555555/subagents/workflows/wf_fixture/journal.jsonl` and `agent-a5555555555555555.jsonl` (one assistant line), `tests/ledger/fixtures/projects/-fixture-project/torn.jsonl` (one good assistant line, then a truncated line)
- Modify: `tools/ledger/factory.py`, `tools/ledger/schema.md` (the `main-sessions.jsonl` writer paragraph, the `backfill` line), `tests/ledger/test_factory.py`

**Interfaces:**
- `_read_main_session(session_file) -> tuple[dict, list[dict]]`: lines via `_read_lines`; a non-JSON line is skipped and counted (stderr `factory.py: {file}: {k} unparseable line(s) skipped`, once per file); usage groups by SP2's `_usage_groups` (keyed `(file, message.id)`); `by_model` = one entry per `message.model` in first-seen order, each split into `model`/`model_suffix` by SP2's `_model_split` (a ninth model → the fence's cap refuses the row, named on stderr); `tokens` = the sum over models; `message_count` = groups; `tool_uses` per line; `started`/`ended` = min/max `timestamp`; `wall_s`; `harness_version` = the first line's `version`; `session_id` = `session_file.stem`; `limit_events` = the count of `_limit_event(line, "main")` rows, returned beside the row.
- `backfill(projects_dir, ledger_dir) -> tuple[int, int, int]`: the workflow walk unchanged, then `sorted(projects.glob("*/*.jsonl"))` (files directly under a project directory — an agent file sits deeper and never matches); merges `main-sessions.jsonl` and `limit-events.jsonl`; the CLI prints `backfill: {w} workflow dirs, {m} main sessions, {l} limit events`.
- `rollup --week`: a line `main sessions: {n} sessions, in {in} out {out} cache_read {cr} cache_write {cw} thinking {th}` from rows whose `started` falls in the window (the file's half-open rule).

**Facts** — Assumptions 5, 6, 7, 15; `grep -n 'def backfill' -A 8 tools/ledger/factory.py` → the `**/subagents/workflows/wf_*` glob and `return len(wf_dirs)`.

**Steps:**
- [ ] Step 1 — the fixtures and tests; `nix develop -c pytest tests/ledger -q -k main_session` → `AttributeError: module 'factory' has no attribute '_read_main_session'` — paste it.
- [ ] Step 2 — the reader, the walk, the rollup line; `ruff format`; `pytest tests/ledger -q` green.
- [ ] Step 3 — `ledger-unit`, `lint`; one commit.

**Tests:**

| # | assertion | discriminating fixture | mutant |
|---|---|---|---|
| 1 | the session row: `tokens.out == 7952`, `cache_write == 29050`, `message_count == 2`, two `by_model` entries with `claude-opus-4-1.out == 7912`, the second `model == "claude-sonnet-4-5"` and `model_suffix == "1m"`, `tool_uses == 1`, `harness_version == "2.1.258"`, `session_id` = the file stem, `limit_events == 1` | the growing triple; two models, one bracketed | first-wins (2); sum (7916); `by_model` keyed on the first model only; the bracket split at `]` |
| 2 | one `limit-event` row, `origin == "main"`, `request_id == "req_main_1"`; the 500 line yields none | the two error lines | the 429 test dropped |
| 3 | `streams.validate("main-session", row) == []`; no key of the row or of `by_model[*]` is in `{"cwd","gitBranch","slug","messages"}` | the wire lines carry all three; `by_model[*]` carries `message_count` (not `messages`) | `cwd` copied → `cwd: forbidden name`; `message_count` renamed back to `messages` → `messages: forbidden name` |
| 4 | `backfill(projects, ledger)` → `(1, 2, 1)`; the CLI prints `backfill: 1 workflow dirs, 2 main sessions, 1 limit events` | the fixture tree with `torn.jsonl` beside the session file | the main walk globs `**/*.jsonl` (the agent file becomes a session → 3) |
| 5 | `torn.jsonl` → a row from its one good line and one stderr skip line; no exception | the truncated line | the skip removed (`JSONDecodeError`) |
| 6 | `backfill` twice → the same row counts | two runs | `append` |
| 7 | `rollup --week --since 2026-09-03 --until 2026-09-04` prints `main sessions: 1 sessions, …`; a session started `2026-09-04T00:00:00Z` is outside `--until 2026-09-03` | two sessions on the boundary | `<=` on the far side; the line omitted |

**touches:** tools/ledger/factory.py, tools/ledger/schema.md, tests/ledger/test_factory.py, tests/ledger/fixtures/projects/-fixture-project/11111111-2222-4333-8444-555555555555.jsonl, tests/ledger/fixtures/projects/-fixture-project/torn.jsonl, tests/ledger/fixtures/projects/-fixture-project/11111111-2222-4333-8444-555555555555/subagents/workflows/wf_fixture/journal.jsonl, tests/ledger/fixtures/projects/-fixture-project/11111111-2222-4333-8444-555555555555/subagents/workflows/wf_fixture/agent-a5555555555555555.jsonl
**acceptance:** ledger-unit, lint
**commit subject:** `ledger: the main-session reader — one main-sessions row per session file, numbers only, bracketed model ids split, the 429 tombstones as limit-event rows, backfill walks both trees and prints its counts, rollup --week prints the main line (test: ledger-unit, lint)`

### SP7 (code, S) — `evidence ingest otel`: the collector's OTLP-JSON files mapped to the `otel-claude` kind (`api_request` events and `token.usage` points), the bracketed model id split, an identity attribute refused by rule

**dependsOn:** SP2, SP8

**Files:**
- Create: `pkgs/evidence/ingest_otel.py`, `tests/evidence/test_ingest_otel.py`, `tests/evidence/fixtures/otel/metrics.jsonl` (line 1: one batch, resource `service.version: "2.1.258"`, a `claude_code.token.usage` sum with two points — `type: input`, `asDouble: 10`, and `type: cacheRead`, `asInt: "17584"` — for `model: claude-opus-5[1m]`, `session.id: sess-fixture`, `terminal.type: probe`, `timeUnixNano: "1788906253213778862"`; a `claude_code.cost.usage` metric; line 2: a point carrying `user.email`; line 3: a point carrying `user.name`; line 4: a `claude_code.token.usage` point with every other attribute but NO `session.id`; line 5: a point with no `timeUnixNano`), `tests/evidence/fixtures/otel/logs.jsonl` (an `api_request` record with all twenty kept keys — `request_id: req_fixture`, `cost_usd: 0.0123`, `input_tokens: "2"`, `output_tokens: "77"`, `cache_read_tokens: "1000"`, `duration_ms: "1200"`, `query_source: main`, `agent.name: gate-reviewer`, `skill.name: code-review`, …; a `user_prompt` record; an `api_request` with `model: Claude-X`; an `api_request` without `request_id`; an `api_request` without `session.id`; an `api_request` without `timeUnixNano`)
- Modify: `pkgs/evidence/streams.py` (the `otel-claude` kind), `tests/evidence/test_streams_policy.py`, `pkgs/evidence/evidence.py` (`INGEST_MODULES["otel"] = "ingest_otel"`), `pkgs/evidence/SCHEMA.md`

**Interfaces:**
- The kind:

```python
    "otel-claude": {
        "stream": "ledger/otel-claude",
        "v": 1,
        "key": ("session_id", "sample_id"),
        "fields": {
            "src": ("enum", ("otel",)),
            "session_id": "id",
            "sample_id": "id",
            "sample": ("enum", ("request", "tokens")),
            "at": "ts",
            "model": ("null", "model-id"),
            "model_suffix": ("null", "id"),
            "harness_version": ("null", "id"),
            "terminal_type": ("null", "id"),
            "query_source": ("null", "id"),
            "speed": ("null", "id"),
            "effort": ("null", "id"),
            "agent_name": ("null", "id"),
            "skill_name": ("null", "id"),
            "request_id": ("null", "id"),
            "cost_usd": ("null", "num"),
            "duration_ms": ("null", "int"),
            "input_tokens": ("null", "int"),
            "output_tokens": ("null", "int"),
            "cache_read_tokens": ("null", "int"),
            "cache_creation_tokens": ("null", "int"),
            "token_type": ("null", ("enum", ("input", "output", "cacheRead", "cacheCreation"))),
            "value": ("null", "num"),
        },
    },
```
- `evidence ingest otel [--root DIR] <path>…` (`--root` default `/var/lib/opentelemetry-collector`; the fence, stderr and exit codes: every path realpath-fenced under `--root` before any read — outside it → stderr `evidence: ingest otel: {p} is outside {root}`, exit 2, nothing written; an unreadable path → `…: {p}: not an otel file`, refused; a torn last line (no trailing `\n`) → `…: {p}: last line torn (the collector is writing); skipped`, not refused; one `evidence.replace_stream(store, "ledger/otel-claude", rows)` after every path is read; `--help` exits 0; `evidence ingest bogus` ends `…|otel)`, exit 2 — the same idiom as SP8, inlined here rather than pointed at it because a seat briefed only on SP7 via `factory-brief` never sees SP8's section). Per line: a JSON object with `resourceMetrics` or `resourceLogs`, else refused `not an OTLP export line`. Attribute values: `stringValue` (str), `intValue` (a decimal STRING → int), `doubleValue` (float), `boolValue`; any other wrapper → the row refused `attribute {key}: unsupported value type`. **The identity rule:** any attribute whose key's first `.`-token is `user` or `organization` → the row refused `{key}: identity attribute present (the collector's allowlist is broken)` — `user.name` and `organization.slug` refuse too. **Missing required fields** (§Errata applied H): a data point or log record with no `session.id` attribute → refused `session_id: missing` (the kind's `session_id` is non-nullable); a data point or log record with no numeric `timeUnixNano` → refused `timeUnixNano: missing` (from which `at` and the `tokens` sample's timestamp component of `sample_id` are both derived — neither can be computed without it). Metrics: every data point of `claude_code.token.usage` → a `tokens` row (`token_type` from `type`, `value` from `asDouble` or `int(asInt)`, `sample_id = f"tokens:{type}:{model}:{model_suffix or '-'}:{timeUnixNano}"`); other metrics `skipped`. Logs: a record whose `event.name` is `api_request` → a `request` row (`sample_id = request_id`; absent → refused `request_id: missing`); every other event `skipped`. Model rule: `model` is split at the first `[` (the same `_model_split` helper SP2 uses) — the head must match `MODEL_ID_RE` (else refused `model: not a model-id`), the bracketed tail is `model_suffix` (`1m`), absent → null. `at`: `secs, rem = divmod(int(timeUnixNano), 10**9)` → `strftime("%Y-%m-%dT%H:%M:%S") + f".{rem // 1000:06d}Z"` (integer truncation). `harness_version` = the resource's `service.version`; `terminal_type` from the point's/record's `terminal.type`. Stdout `ingested {n} rows into ledger/otel-claude ({refused} refused, {skipped} skipped)`; exit `0` when `refused == 0`, else `1`; `2` on `OutsideRoot`.

**Facts** — Assumptions 5, 9, 11; `1788906253213778862` → `…213779Z` by float `fromtimestamp` vs `…213778Z` by integer arithmetic (`nix develop -c python3 -c "import datetime; …"`; the fixture pins the latter).

**Steps:**
- [ ] Step 1 — the kind's rows in `test_streams_policy.py` (`sample: "metric"` → `sample: not in enum (request|tokens)`), red then green; `nix develop -c pytest tests/evidence/test_ingest_otel.py -q` → `StopIteration` — paste.
- [ ] Step 2 — the module; `ruff format`; `pytest tests/evidence -q` green.
- [ ] Step 3 — `evidence-unit`, `lint`; one commit.

**Tests:**

| # | assertion | discriminating fixture | mutant |
|---|---|---|---|
| 1 | `metrics.jsonl` → 2 `tokens` rows (`value == 10.0` and `17584`), `model == "claude-opus-5"`, `model_suffix == "1m"`, `harness_version == "2.1.258"`, `terminal_type == "probe"`, `at == "2026-09-08T22:24:13.213778Z"`; 4 refused; `skipped == 1` | `asInt` as a string; `[1m]`; the ns value; the no-`session.id` point; the no-`timeUnixNano` point | `int(float)` for `asInt`; the split at `]`; float division in `at` (`…779Z`); the missing arm dropping the row silently instead of refusing |
| 2 | the `user.email` point and the `user.name` point are both refused with `identity attribute present` | lines 2 and 3 | an exact-match list of four keys (`user.name` lands) |
| 3 | `logs.jsonl` → one `request` row with all twenty fields (`cost_usd == 0.0123`, `input_tokens == 2`, `agent_name == "gate-reviewer"`, `sample_id == "req_fixture"`), 4 refused, 1 skipped | the six records (the four original plus the missing-`session.id` and missing-`timeUnixNano` records) | `intValue` kept as a string → `input_tokens: not a int`; `user_prompt` mapped; the two missing-field arms skipped instead of refused |
| 4 | two runs → the same rows | — | `append` |
| 5 | an unknown wrapper (`arrayValue`) → refused `unsupported value type` | one planted attribute | the wrapper ignored |
| 6 | the fence: a path outside `--root` → exit 2, nothing written; `torn.jsonl`-style truncation → skipped, not refused, exit 0; `--help` exit 0; `evidence ingest bogus` ending `|otel)`, exit 2 | a fixture outside root; a torn line | the fence removed; torn treated as `not JSON` |
| 7 | a point with no `session.id` → refused `session_id: missing`; a record with no `timeUnixNano` → refused `timeUnixNano: missing` | the two planted rows | the arms absent (silently skipped) |

**touches:** pkgs/evidence/ingest_otel.py, pkgs/evidence/streams.py, pkgs/evidence/evidence.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_ingest_otel.py, tests/evidence/test_streams_policy.py, tests/evidence/fixtures/otel/metrics.jsonl, tests/evidence/fixtures/otel/logs.jsonl
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: ingest otel — the collector's OTLP-JSON files mapped to the otel-claude kind (api_request events and token.usage points), the bracketed model id split, missing session_id/timeUnixNano and an identity attribute each refused by rule (test: evidence-unit, lint)`

### SP4 (code, S) — `evidence report spend`: dollars and tokens per day, service and role from the three streams, list price where the vendor gives none, refused under five rows

**dependsOn:** SP6, SP7

The heading's "three streams": the report reads five — `ledger/openrouter-usage`, `ledger/factory-agents` with `ledger/factory-runs` for the day, `ledger/main-sessions`, `ledger/otel-claude` and `ledger/limit-events` for the footer — the task set grew by three keys and the streams with it. Claude's transcript rows and OTel rows are two sources, never added (D10).

**Files:**
- Create: `docs/ledger/claude-prices.csv`, `tests/evidence/fixtures/spend/ledger/{openrouter-usage,factory-runs,factory-agents,main-sessions,otel-claude,limit-events}.jsonl`
- Modify: `pkgs/evidence/report.py`, `pkgs/evidence/tasks.py`, `tests/evidence/test_report.py`, `tests/evidence/test_tasks.py`

**Interfaces:**
- `docs/ledger/claude-prices.csv` — header `date,model,in_per_1m,out_per_1m,cache_read_per_1m,cache_write_per_1m`, rows `2026-06-24,claude-fable-5-1,10.00,50.00,0.25,` · `2026-06-24,claude-opus-5,5.00,25.00,,` · `2026-06-24,claude-sonnet-5,2.00,10.00,,` · `2026-06-24,claude-haiku-4-5,1.00,5.00,,` (Assumption 13; an empty cell is an unpriced unit).
- `evidence report spend [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--prices CSV] [--min-n N]` (`spend_report(store, since, until, prices, min_n=5) -> list[str]`): UTC days, both bounds inclusive; `--since` defaults to the earliest row, `--until` to today. The day of a row: `openrouter-usage.ts_epoch` (UTC); a `factory-agent` → its run's `factory-run-usage.started` joined by `run_id` (none → `undated`); `main-session.started`; `otel-claude.at`. `n` = rows read in the window; `n < min_n` → the header then exactly `refused: n={n} < {min_n} (no conclusion under {min_n})`. **Pricing for `factory-agent` rows reads the row's `model_id` field** (§Errata applied B) — today the extractor sets `model_id` identical to `role_model`, but the two are not verified equal anywhere, so `model_id` is the one field this report consults; a future divergence between them is not this report's problem.
- Header (byte-exact): `# evidence report spend — dollars and tokens per UTC day, service, source and role (concept 2026-09-08e); claude appears twice (transcript rows priced at list, otel rows at Claude Code's own estimate) and the two are never added; n = rows in the window; refused under {min_n}`. Then `window: {since}..{until}`; one line per `(day, service, source, role)`, fields separated by two spaces: `day service source role basis usd in out cache_read cache_write reasoning n` — `usd` to four decimals or `-`; `basis` ∈ `vendor` (openrouter `ok` rows' `cost_usd`), `estimate` (otel `request` rows' `cost_usd`), `list`, `partial` (some unit unpriced), `unpriced` (no price row, or no `--prices`); otel `tokens` rows are never summed. Then `total {since}..{until}: openrouter {usd} vendor · claude transcripts {usd} list · claude otel {usd} estimate`; `unpriced: {model} {unit} {tokens} tokens; …` (per model×unit with tokens > 0 and no rate; `none` when empty); `limits: {k} rate-limit events ({type}: {count}, …)`.
- Pricing: the price row with the greatest `date <= day` per model; `usd = in·in_per_1m/1e6 + out·out_per_1m/1e6 + cache_read·… + cache_write·…`, `math.fsum`; an empty rate → that unit unpriced (its tokens still printed). `thinking` is inside `out`.
- **The otel `tokens` rows are CUMULATIVE counters, measured at SP7's gate (2026-09-09): the same `(session_id, model, model_suffix, token_type)` lands one row per 5-second collector export, with a growing value — 17584 then 31000 were observed for one session. So a `tokens` row's contribution is `MAX` per `(session_id, model, model_suffix, token_type)`, never a sum and never first-wins.** The section's existing rule ("otel `tokens` rows are never summed", mutant G) states only what not to do; this is the positive rule. The discriminating fixture must therefore carry at least two `tokens` rows for ONE key with different values, so that a summing implementation and a MAX implementation give different output — a fixture with one row per key cannot tell them apart, and would leave the rule untested however correct the code. This is the same class of error the house has hit repeatedly: SP6's gate confirmed the analogous MAX-per-message-id rule only because its fixture had growing values.
- Service and role: `openrouter-usage` → `openrouter`, role by instance — `seat` → `seat`, `openrouter` → `lane`, else `unknown`; `factory-agent` → `claude`, role from `label` (null → `unknown`); `main-session` → `claude`, `orchestrate`; `otel-claude` → `claude`, role from `agent_name` (null → `orchestrate`). `role_of_words(s)`: lowercase, split on `[^a-z0-9]+`, the FIRST token in the table wins — `review, reviewer, gate → gate`; `plan, planner, judge, judges, draft, drafter → plan`; `implement, implementer, seat → implement`; `orchestrate, orchestrator → orchestrate`; no hit → `unknown`.
- The Seats line (`tasks.py`): `seat_stats(runs_dir, now=None, days=SEATS_DAYS, store=None)` gains `cache_read` (the `usage:` JSON's `cacheRead`, summed like `billed`) and `usd` — with `store`, `evidence.read(store, "ledger/openrouter-usage")` rows with `instance == "seat"`, `status == "ok"`, `ts_epoch >= cutoff`, grouped by `model`, `math.fsum(cost_usd)`; no rows → `None`. `render_seats_line` prints `…, {billed} billed, {cache_read} cached` and appends `, ${usd:.2f}` only when `usd is not None`. `build()` records `graph["store"] = store`; `render_brief` passes it (`--store /nonexistent` in `lint` and the hook → no `$`).

**Facts** — Assumptions 5, 13, 16; `grep -n 'refused: n=' pkgs/evidence/report.py` → the plans string; `grep -n 'billed' pkgs/evidence/tasks.py tests/evidence/test_tasks.py` → the line format and its pinned tests (updated here).

**Steps:**
- [ ] Step 1 — the fixtures and the tests; `nix develop -c pytest tests/evidence/test_report.py -q -k spend` → `AttributeError: module 'report' has no attribute 'spend_report'`; `pytest tests/evidence/test_tasks.py -q -k seats` → `AssertionError` on the `cached` field — paste both.
- [ ] Step 2 — `report.py`, `tasks.py`; `ruff format`; `pytest tests/evidence -q` green.
- [ ] Step 3 — `evidence-unit`, `lint`; one commit.

**Tests** (fixture: two UTC days; openrouter rows with instances `seat`, `openrouter`, `other`, one `no-usage` row; a run started day 1 with two agents — labels `review:X:r1` and null; a main session day 2; otel `request` rows for `claude-fable-5-1` and `claude-opus-5` plus `tokens` rows; three limit events `five_hour` and one `seven_day`):

| # | assertion | discriminating fixture row | mutant |
|---|---|---|---|
| 0 | every fixture row validates | — | (guards the fixtures) |
| 1 | the openrouter day-1 seat line: `usd` = the `ok` rows' `cost_usd` sum to four decimals; the `no-usage` row adds no usd; roles `seat`, `lane`, `unknown` each on their own line | the `other` instance | (B) `seat`/`lane` swapped; (C) the `unknown` arm removed (`KeyError`) |
| 2 | a row at `ts_epoch` = `2026-09-08T03:00:00Z` lands on `2026-09-08` under `TZ=CST6CDT,M3.2.0,M11.1.0` (`time.tzset()` in the test) | the 03:00 row | (A) `time.localtime` |
| 3 | the factory-agent rows print under day 1 with roles `gate` and `unknown`; without `--prices` `basis unpriced`; with it `claude-fable-5-1` is `list` and `claude-opus-5` `partial` (cache_read unpriced) — pricing reads `model_id` | two models (one row's `role_model` deliberately set to a different string than its `model_id`, so the role_model-instead-of-model_id mutant is live) | (D) `<= day` → `== day` (the 2026-06-24 row never matches); the partial arm prints `list`; pricing reads `role_model` instead of `model_id` |
| 4 | the `unpriced:` footer names `claude-opus-5 cache_read 1000 tokens`, never a zero-token unit | `cache_write 0` on one row | a zero unit named; an unpriced unit priced at 0 |
| 5 | the otel lines: `basis estimate`, `usd` from `request` rows only, `role gate` for `agent_name gate-reviewer`, `orchestrate` for null | a `tokens` row with `value 1e6` | (G) `tokens` rows summed; null → `unknown` |
| 6 | transcript and otel totals separate in `total`; the header contains `never added` | both sources on one day | one `claude` total |
| 7 | four rows in the window → the header and the byte-exact refusal line only; five → the table | `--until` narrowing to four | (E) `< 5` → `< 4`; (F) one byte of the string |
| 8 | `--since 2026-09-08 --until 2026-09-08` includes `23:59:59Z` on the 8th, excludes `00:00:00Z` on the 9th | boundary rows | (L) exclusive `until` |
| 9 | `limits: 4 rate-limit events (five_hour: 3, seven_day: 1)` | the four events | the type grouping dropped |
| 10 | `main-session` rows are `orchestrate`, `basis list` with `--prices` | one session | the role hard-coded `unknown` |
| 11 (`test_tasks.py`) | the Seats line carries `, 4000 cached` and `, $0.12` for the model with rows in a fixture store, no `$` for the other; `store=None` → no `$` | two models, one with rows | (I) `cached` dropped; (J) `$0.00` with no rows |
| 12 | the `total` openrouter figure equals the sum of the day lines' `usd` | two days | a day double-counted |

**touches:** pkgs/evidence/report.py, pkgs/evidence/tasks.py, docs/ledger/claude-prices.csv, tests/evidence/test_report.py, tests/evidence/test_tasks.py, tests/evidence/fixtures/spend/ledger/openrouter-usage.jsonl, tests/evidence/fixtures/spend/ledger/factory-runs.jsonl, tests/evidence/fixtures/spend/ledger/factory-agents.jsonl, tests/evidence/fixtures/spend/ledger/main-sessions.jsonl, tests/evidence/fixtures/spend/ledger/otel-claude.jsonl, tests/evidence/fixtures/spend/ledger/limit-events.jsonl
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: report spend — dollars and tokens per UTC day, service, source and role from five streams, pricing keyed on factory-agent's model_id, list price marked where the vendor gives none, refused under five rows; the Seats line carries cached tokens and dollars (test: evidence-unit, lint)`

### SP5 (docs, S) — the evidence runbook carries spend: the streams, the ingest and backfill lines, the switch #23 acceptance, the manual export retired

**dependsOn:** SP3, SP4

The heading's "the manual export retired": decision 2026-09-05 answer 4 keeps the weekly download, so the runbook retires it for COST only (the `openrouter-usage` rows are the dollar of record) and keeps it as the monthly reconciliation; `d5-activity-export` is restated to say so.

**Files:**
- Create: `tests/unit/96-evidence-runbook.bats`
- Modify: `docs/runbooks/evidence.md` (a `## Spend` section after `## The harness report`; the store section's writer count and list), `docs/ledger/claims.toml`, `flake.nix` (two `cp` lines in `checks.unit` beside the `docs/runbooks/session.md` copy: `cp ${self}/docs/runbooks/evidence.md docs/runbooks/evidence.md` and `mkdir -p tools/ledger && cp ${self}/tools/ledger/factory.py tools/ledger/factory.py`, each with a comment naming this test)

**Interfaces** — the `## Spend` section carries, in order: (1) the five streams and the raw file feeding each (`/var/lib/egress-broker/<name>/usage.jsonl`, `/var/lib/opentelemetry-collector/claude-{metrics,logs}.jsonl` — both unbacked; `~/.claude/projects` — read by the backfill, never copied); (2) the four operator lines, each in its own fenced block, byte for byte: `evidence ingest openrouter-usage /var/lib/egress-broker/*/usage.jsonl`, `evidence ingest otel /var/lib/opentelemetry-collector/claude-*.jsonl`, `nix develop -c python3 tools/ledger/factory.py backfill ~/.claude/projects --ledger-dir /var/lib/evidence/ledger`, `evidence report spend --since 2026-09-01 --prices docs/ledger/claude-prices.csv`, each with its expected first line (§Operator step 6); (3) the switch #23 acceptance (§Operator steps 3–4) and the rollback line; (4) "the weekly limit has no durable source": the tombstones are `limit-events`, the weekly percentage is screen-only, the scheduled reset probe stays the proxy (a boolean at one instant — the declared gap); (5) the manual export: monthly reconciliation, retired for cost; (6) the store section's "Four writers append to it" becomes "Seven writers" — the two ingests and the backfill added, the collector and the broker named as producers that never write the store.
- `docs/ledger/claims.toml`: `d5-activity-export` text → `the openrouter activity CSV exists and rollup --activity parses it (reconciliation only since 2026-09-08; the dollar of record is the broker's openrouter-usage stream)`; `reasoning-tokens-not-itemised` → `status = "verified"`, `class = "unit"`, `evidence = "check:addon@<sha> tests/broker/test_usage_log.py (reasoning_tokens on every openrouter-usage row)"`, the sha from `git log --format=%h -1 --grep='broker: every OpenRouter completion'`; four `gap` rows (`owner = "orchestrator"`, `opened` = the landing day, `review_by = 2026-09-22`): `openrouter-cost-at-the-broker-live` (`closes_by = "the first evidence ingest openrouter-usage after switch #23 reports ≥ 1 row with status ok and a non-null cost_usd"`), `otel-identity-drop-live` (`closes_by = "after one real session the runbook's identity grep prints 0 for every collector file"`), `otel-desktop-harness-unmeasured` (`closes_by = "a desktop Code-tab session's debug log carries isTelemetryEnabled=true, or SP3b moves the variables to environment.sessionVariables"`), `claude-weekly-limit-unmeasured` (`review_by = 2026-10-06`, `closes_by = "a persisted source for the weekly percentage is found, or the reset probe's boolean is recorded as a limit-event row"`).
- `tests/unit/96-evidence-runbook.bats` (`RUNBOOK="$BATS_TEST_DIRNAME/../../docs/runbooks/evidence.md"`, `EVIDENCE=…/pkgs/evidence/evidence.py`, `LEDGER=…/tools/ledger/factory.py`; every test fails, never skips, when a file is absent): (a) `grep -c '^## Spend' "$RUNBOOK"` → `1`; (b) every line inside a ``` fence between `## Spend` and the next `## ` that starts with `evidence ` or `nix develop -c python3 tools/ledger/factory.py ` is runnable: `evidence <verb> <target>` → `python3 "$EVIDENCE" <verb> <target> --help` exit 0; the ledger line → `python3 "$LEDGER" backfill --help` exit 0; (c) a negative control: the same extractor over a temp file whose fence carries `evidence ingest openrouter` exits non-zero; (d) the section names `limit-events`, `reset probe`, `reconciliation`, `switch-to-configuration`; (e) `grep -c 'Seven writers' "$RUNBOOK"` → `1`.

**Facts** — Assumption 16 (the sandbox's copy list, the runbook's sections, the claims grammar); `grep -n 'Four writers' docs/runbooks/evidence.md` → one line.

**Steps:**
- [ ] Step 1 — the bats file; `nix develop -c bats tests/unit/96-evidence-runbook.bats` → `not ok 1 …` (no `## Spend`) — paste; `nix build .#checks.x86_64-linux.unit -L --no-link` red the same way with the `cp` lines in place.
- [ ] Step 2 — the section, the claims rows, the writer count; `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"` silent; `bats` green.
- [ ] Step 3 — `unit`, `claims-validate`, `lint` (treefmt over the markdown); one commit.

**Tests:**

| # | assertion | discriminating input | mutant |
|---|---|---|---|
| 1 | exactly one `## Spend` | the runbook | the heading removed; a second one |
| 2 | every fenced command's `--help` exits 0 | the four lines | `evidence ingest openrouter` in the runbook (exit 2) |
| 3 | the negative control fails | a planted bogus verb | the extractor matching nothing |
| 4 | the four words present | the section | `reset probe` dropped |
| 5 | `claims-validate` green | the rows | `reasoning-tokens-not-itemised` verified with `class = "unmeasured"` (`verified claim cannot have class unmeasured`); a gap without `closes_by` |
| 6 | `unit` fails (not skips) without the `cp` lines | the sandbox | the copy line removed → `grep: …/evidence.md: No such file` |

**touches:** docs/runbooks/evidence.md, tests/unit/96-evidence-runbook.bats, docs/ledger/claims.toml, flake.nix
**acceptance:** unit, claims-validate, lint
**commit subject:** `docs: the evidence runbook carries spend — the streams and their raw files, the ingest and backfill lines with their expected output, switch #23's acceptance and rollback, the manual export kept for reconciliation only; the claims rows; the runbook's commands gated by bats (test: unit, claims-validate, lint)`
