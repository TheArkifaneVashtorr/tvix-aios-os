# Telemetry store — design (draft for the operator)

**Date:** 2026-09-05. **Status:** draft for the operator's review; nothing here is
built. **Asked for by:** the operator ("evaluate data sources that can be used as
monitors to improve performance of the system, look for areas of improvement,
create a plan for a central data storage system that avoids user data, suggest
potential ways the data can be properly utilized"). **Inputs:** six read-only
inventories (evidence, factory, security, process, host, policy) taken on core on
2026-09-05, plus the designer's own reads of the repo and metadata-only
measurements on the host (§9 lists how each number was taken). No transcript,
prompt, result body or log body was opened for this document. **Revision 2**
(same day, ~23:30 CDT) folds two critiques; §10 lists what changed and what was
rejected. Where an inventory number could not be re-derived by a command on the
machine it was replaced by one that can, and §9 gives the command.

**User data, for this document:** anything the operator or an agent produces or
consumes — prompt and response bodies, transcript text, file contents, images,
basket payloads, personal material, keys. Counts, timestamps, durations, token
numbers, model ids, exit codes, verdicts, check names, hashes, sizes and unit
states are not user data. Every stream below holds only the second kind, and a
check enforces it (§3.5).

## 0. The short version

- The store already exists: `/var/lib/evidence`, append-only JSONL, one file per
  stream, flock on append, envelope `{v, ts, kind}` set by the writer
  (`pkgs/evidence/evidence.py`, `pkgs/evidence/SCHEMA.md`). Two streams are live
  (`checks`: 87 rows; `helm-status`: 20 rows). Two are designed and empty
  (`runs`: 0 rows; `ledger/`: 0 files).
- The richest operational facts on the machine are not in it: 202 seat result
  files, 131 gate reviews, an 8,832-row OpenRouter activity export, two broker
  audit logs (4,932 rows), the Helm collector's numeric detail (discarded every
  5 minutes), and every incident of the last two days (recorded as prose on the
  board).
- This design adds nine streams to the same directory and puts every writer —
  including the two that bypass the library today (`pkgs/helm/collect.py:738`,
  `tools/ledger/factory.py:74`) — behind one validating function. No declared
  field is free text: every string is an enum, an id, a model id, a 40-hex rev,
  a timestamp, a hash or a declared, rooted path. A nightly audit re-checks
  every row, quarantines what got past the writers, and records its verdict as
  a check. Two oneshot user timers (audit, rollup) and one report command. No
  daemon, no database server, no listener, no model in the loop; nothing is
  sent to any service — the store leaves the machine only inside the nightly
  restic ciphertext (§3.6). SQLite is not adopted now (§3.2).
- The first payoffs are cheap: an `error_class` on every seat result (today a
  seat that died on a 402 is recorded `failed` with `exit_code=0`, and one that
  died on a provider error is recorded `done`), gate verdicts and mutation counts
  as fields instead of prose, and cost per task by (model, effort, kind, size) at
  n ≥ 5 without bespoke comparison runs.

## 1. Sources evaluated

Verdicts: **adopt now** (a field-only source, or a derivation that already
exists), **after a change** (the change is named), **never** (content; the
derivation column says what may be kept, if anything). Volumes are as measured
on 2026-09-05 unless marked; "growth" is the rate at that day's activity.

| # | Source | What it measures | Volume and growth | Sampling cost | Privacy class | Verdict |
|---|---|---|---|---|---|---|
| 1 | `/var/lib/evidence/checks.jsonl` | which named check passed at which 40-hex rev, from which stage (`src`), how long | 87 rows, 20,200 B, 2026-09-05T15:24Z–09-06T01:33Z (~205/day, event-driven); `src`: seat-integrate 76, orchestrator-integrate 8, orchestrator-preswitch 2, helm-nightly 1; 21 check names; 1 of 87 `ok:false`; `duration_s` in 79 (sum 1,183 s, max 119 s); `log_tail` in 1 | none (already written) | operational; `log_tail` is a ≤4,000-char tail of whatever file `--log-tail-file` names (`evidence.py:397` reads any path; a failing lint's tail is source lines by construction) | adopt now (primary). v2 of the row replaces `log_tail` with `log_tail_sha256`, `log_tail_len` and a `fail_class` enum (§3.3); the one v1 row stays and is audited under the v1 shape |
| 2 | `/var/lib/evidence/helm-status.jsonl` | nine tile verdicts, one row per change plus an hourly heartbeat | 20 rows, 4,739 B, 09-05T17:41Z–09-06T02:08Z; 15 change, 5 heartbeat; ≥24/day | none | enums and timestamps only | adopt now (primary) |
| 3 | `/var/lib/evidence/ledger/*.jsonl` | tokens by kind, wall clock, tool calls, review-finding metadata, lane cost (`tools/ledger/schema.md`) | 0 files; the extractor (`tools/ledger/factory.py`, 1,016 lines) has never run against 89 workflow dirs, 963 `agent-*.jsonl`, 240 seat sessions | one backfill run (minutes), then per run | counts, ids, model ids, dollars; `factory-findings.title` is a one-line finding headline written by a reviewer model (prose); the writer (`_write_jsonl` :74, `_merge_jsonl` :80) bypasses `evidence.append()` | adopt now (derived); `title` becomes `title_sha256` (the headline stays in the journal it came from) and the writer goes through the validating function (§3.4) |
| 4 | `runs` stream (`kind: factory-run`) | per run: plan, tasks, fix rounds, verify verdict, agents, output tokens | 0 rows; the dark-factory recorder exists (`dark-factory.js` :658–670) and emits exactly SCHEMA.md's v1 shape (`plan, prefix, baseline, integration_branch, tasks[]{key,status,commit,fixRounds}, verify, delivered, agents, output_tokens, run_id`); claim `factory-run-report-persisted` open | none | ids and counts | adopt the recorder's v1 shape as is (declared before the recorder next runs, §3.3); the seat driver's start/end rows are a second declared shape |
| 5 | `docs/ledger/claims.toml` | proven vs open beliefs | 29 claims: 16 gap, 10 verified, 3 parked | none | process metadata | adopt as an input; never a stream (it is policy, per SCHEMA.md) |
| 6 | `~/factory/runs/<run>/<KEY>.result` | status, checks, commits, model, effort, route, wall, exit code, head/base, diffstat, `usage:` | 202 files in 101 run dirs at 23:30 CDT (200 in 98 at the first sample), 2026-09-04 13:12–09-05; done 192 / failed 7 / partial 1 at the first sample; exit 0 ×195, 1 ×5; `effort:`/`route:` in 51 (none of the eight comparison-arm results carries either — the lines were added to the driver after those runs); no result carries a `plan:` line; `usage:` in all; `wall_s` mean 673 s, max 2,781 s | parse once (ms) | `FACTORY-NOTES` is one agent-written sentence; commit subjects; diffstat file paths; the `FACTORY-CHECKS` names are agent-written map keys; the file itself is written inside the seat unit, whose `ReadWritePaths` include `~/factory` | adopt now (derived): NOTES dropped, diffstat reduced to three counts, commits counted from the list (15 declared counts disagree with the list), check names validated against a key pattern (§3.5) |
| 7 | `~/factory/runs/<run>/run.meta` | run identity, base, groups, pid, `--then` | 0 files; specified by CR3r (`docs/superpowers/plans/2026-09-05-context-reset-ritual.md`) | none | ids, a pid | after CR3r lands (becomes the `runs` start event) |
| 8 | `.marker-*`, `<KEY>.pid`, `<KEY>.gate` | in-flight liveness | 14 marker files today; pid/gate files come with CR3r | stat | pids, mtimes | after CR3r (liveness only; never stored beyond pid and ts) |
| 9 | `*.wave.log` (91, 580 KB), `integrate.log` (48), `*.integrate*.out` (43) | dispatch summary lines; merge and check outcomes | ~90 files per two days | grep | check and branch names; an output tail that can hold a build error (code) | never as text; the same facts arrive through #6 and #1 |
| 10 | `wave-group-N.log` (107, ~20 MB), `<KEY>.launch.log` (23), `<KEY>.log` family (429 top-level today; 6 carry incident suffixes), `<KEY>.review.log` (23) | full agent stdout including reasoning | ~150 MB/day across the run tree (209 MB total) | — | **content** | never; derivation kept: byte size, line count, mtime, and an `error_class` enum computed by the driver from a fixed pattern list at task end (§3.3, `tasks`) |
| 11 | `<KEY>.dsh-home/sessions/**/session.jsonl.zstd` | per-event prompt/response/reasoning (`data`), usage numbers on `assistant/message` | 240 files, 137 MiB compressed, 611,939 events | zstd + json (seconds per file) | **content** | never; derivations kept: `factory-usage.py` (tokens, model, duration — already in #6) and `extract-dsh` (turns, steps, tool-call counts) |
| 12 | `~/factory/runs/<run>/<KEY>.review.md` | the DeepSeek review with a `FACTORY-REVIEW verdict=` line | 23 files | grep one line | review prose (code-level) | adopt the verdict line only (`gates` stream); text never |
| 13 | `~/strategy/ledger/openrouter-activity.csv` | per-request cost, tokens (prompt, completion, **reasoning**, cached), model, provider, finish reason, generation time | 8,832 rows, 2026-08-23–09-05; per day: 09-04 3,769 rows $62.28, 09-05 3,942 rows $66.61; 6,031 rows carry `tokens_reasoning` > 0 (6,340,776 reasoning tokens, 5,492,875 of them on deepseek-v4-pro-20260813); finish: tool_calls 8,353, stop 442, length 21; `generation_time_ms` mean 15,115; 7 models, 19 providers | a manual download by the operator; parse ms | `generation_id`, `user`, `api_key_name`, `app_name` are account identifiers | adopt now (derived to one row per (date, model)). The reader exists: `tools/ledger/factory.py:453 _load_activity` already accepts this export, buckets cost by (date, model) and never reads the four identity columns; the change extends it to the token, finish and provider-count columns and persists the bucket (§3.4) |
| 14 | `docs/ledger/routing.toml`, `docs/ledger/openrouter-prices.csv` | the routing policy (15 rows) and rates (3 dated rows; `cache_read_per_1m` 0.0) | hand-edited | none | configuration | adopt as inputs; never streams; rows change only by commit (§4.1) |
| 15 | `docs/ledger/task-status.toml`, `plan-status.toml`, `repos.toml` | graph inputs | 18 / 191 / 23 lines | none | configuration | not telemetry; read by `tasks.py` |
| 16 | `dark-factory.js` run report | the in-memory report a recorder agent should persist | 0 rows on disk | none | ids and counts | after a change: run the recorder post-switch, or derive from the journals with `tools/ledger/factory.py extract` |
| 17 | `docs/reviews/*opus-review*.md` | gate verdict, majors/minors, mutation results, file:line findings | 131 files at 23:30 CDT (128 at the first sample); 104 first lines parse under `tasks.py` `REVIEW_RE` (`^# Opus gate — seat run …, task … — (APPROVED\|REJECTED)`: 58 APPROVED / 46 REJECTED; the pattern admits no other verdict word); 120 mention mutants but only 3 use the `N/M mutants` form, 16 `N killed`, 4 spelled-out; MAJOR markers in 42 files, MINOR in 53 | parse ms; one front-matter migration | quotes code, commands, paths; no prompt bodies (6 files read in full by the process reader) | after a change: a fixed front-matter block; the store takes only its fields |
| 18 | `git log` — gate-review commits | when a verdict was filed | 62 `docs: gate review` subjects since 09-04; 55 parse as `<run> <key> approved\|rejected` (30 / 25); all 55 have a matching `.result` | ms | subjects | adopt now (derived) |
| 19 | `git log` — landings and churn | landings, board churn, check coverage | 331 commits since 2026-09-04; 59 `integrate <KEY> into integ/<run>` (58 distinct pairs); 45 `docs: board —`; 93 commits touched `docs/OPERATIONS.md` (28 %); 99 touched `docs/reviews`; 269 carry `(test: …)` | ms | subjects | adopt now (derived) |
| 20 | `docs/OPERATIONS.md`, `docs/board/log-2026-09.md` | incidents and decisions as prose | 49 lines / 12 KB; 130 lines / 56 KB | grep | prose | never as a stream source; the `incidents` stream replaces the grep |
| 21 | the three comparison reports (`docs/reviews/2026-09-05-{effort,model,plan-writing}-comparison.md`) | per-arm cost, wall, gate tokens at n = 2 / 2 / 1 | 179 lines | none | numbers and prose | adopt as validation fixtures: `evidence report` must reproduce their per-arm tables (§4.6) |
| 22 | Claude Code transcripts of this project (`~/.claude/projects/-home-dalhaka-nixos-agent-env`) | per-message usage (input, output, cache, thinking), timestamps, tool names; and the message bodies | 15 session files; 322 MB in the directory; 89 workflow dirs; 963 `agent-*.jsonl`; 89 `journal.jsonl` | seconds per file | **content**, with numeric usage fields beside it | never as content; after a decision (Q3): usage-only derivation, which `tools/ledger/factory.py extract` already implements for `agent-*.jsonl` |
| 23 | `/var/lib/egress-broker/openrouter/audit.jsonl` | one row per flow: host, SNI, method, path, bytes, verdict, reason | 296 rows, 74,321 B, 09-03T20:02Z–09-04T21:50Z; allow 247 / deny 45 / error 4; reasons: ok 247, not-allowlisted 43, connect-not-allowlisted 2, upstream-or-client error 4; 3 hosts, 3 paths (3 with a query string); `bytes_out` 62,895,266; `bytes_in` 4,005 (streamed responses report 0 — not a response-size signal) | parse ms; mode 0644 | no bodies by construction (`pkgs/broker/policy.py:91 _audit`); `client`, `host`, `host_header`, `sni` and `path` are verbatim (`:99–104`); two deny reasons embed hostnames (`host-header-mismatch: host=… header=…` :215, `host/sni mismatch: sni=… host=…` :221/:225) | after a change: a daily rollup by (instance, verdict, reason class) with counts, `bytes_out`, query-path count and audit-file age; the reason is mapped by exact prefix to a closed enum and the remainder dropped (§3.3); `client`, `host`, `sni` and `path` never enter the store |
| 24 | `/var/lib/egress-broker/cowork/audit.jsonl` | same | 4,636 rows, 1,280,869 B, 09-02T20:44Z–09-03T00:50Z; allow 3,407 / deny 1,203 / error 26; 16 hosts, 2,224 paths (527 with a query string); `bytes_in` 1,520,915,851. The file has not grown since 2026-09-02 19:50 while the unit logged 14,916 journal lines in 7 days (Cowork tier A is parked, so "no traffic" is plausible; the record cannot say) | same | same | same; the age signal is the point |
| 25 | `/var/lib/lanes/openrouter/ledger.jsonl` (+ `jobs/` 25, `results/` 14) | per job: model, provider, usage incl. cost and `completion_tokens_details.reasoning_tokens`, wall | 13 rows, 4,000 B (2026-09-04); cost sum $0.00002748; a ledger row is `{ts, job, kind, model, provider, usage, wall_s}` (`lane-run.py:196`) or `{…, exit, wall_s}` (`:458`) | ms; group `lane` (the operator is a member) | ledger: counts and cost. `jobs/<id>.json` carries `prompt` (`lane-submit.py:292`); `results/<id>.json` carries `output` (`lane-run.py:189, :296`), `log` (`proc.stderr[-4000:]`, :449) and `diff` (the working tree, :450) — **content** | adopt now — from `ledger.jsonl` only. Today's `extract-lane` (`factory.py:368`) globs `results/*.json` and opens each (`:347`); it is re-pointed at the ledger (§3.4). `jobs/` and `results/` are never opened by anything in this design |
| 26 | seat hook-guard denials (`dsh-openrouter --denials N`) | refused tool calls: ts, event, tool, reason, subject | 2 records across 47 interactive transcripts (35 MB) | seconds (`dsh-denials.py:118` decompresses and parses every `session.jsonl.zstd`; `:63–77` lifts the raw `command`/`file_path` beside each record) | the reason string is **not** a constant: `hook-guard.py:442/:451` interpolate the agent-supplied file path, `:293` the agent-supplied model id; `subject` is the refused command line or path (can embed text) | after a change: the guard itself appends a state row `{ts, event, tool, reason_code, subject_sha256, subject_len}` under `$DSH_HOME` (§3.3); the transcript walk stays an operator-invoked tool and runs in no timer |
| 27 | `tools/orchestrator-guard.sh` denials | the orchestrator's refused commands | nothing persisted (723 lines, no log path) | — | same shape as #26 (`deny "$reason"` at :683/:713 with rule-built strings) | after a change: one JSON line per deny to `$XDG_STATE_HOME/nixos-agent-env/guard-denials.jsonl` with a `reason_code` from a closed table in the guard and the subject hashed at the source; validated at ingest, never written raw |
| 28 | ritual state (`~/.local/state/nixos-agent-env/ritual/`) | forced stops, block counts, last stop, PreCompact handoffs | `ritual.log` 4 lines (all "queue block stale"), 2 `.blocks`, `last-stop`; 0 `handoff-*.md` today | stat | log lines are code templates; a handoff carries work-in-progress text | adopt now for blocks, log, last-stop (condition enum); handoff text never |
| 29 | `basket doctor` (`nix run .#basket -- doctor`) | swap, pcscd, age plugin, kvm, vsock, stale mounts | on demand; Helm's basket-doctor tile runs it every 5 min (20/20 rows ok) | 100 ms | booleans | already in #2; no new stream |
| 30 | nftables counters | packet/byte counts per chain in the broker namespaces | root-only (`nft list ruleset` refused for the operator) | — | counts | never in this round (needs a root snapshot unit; the broker's own counts stand in) |
| 31 | systemd journal | unit lifecycle, restarts, per-unit CPU/memory/IO accounting, log volume | 120.4 MB; 6 boots since 09-02 (five between 08:38 and 08:49 on 09-03, one on 09-05 16:57); egress-broker-openrouter 2,154 lines / 7 d, egress-broker-cowork 14,916, cowork.service 2,677, egress-netns-openrouter 7 | `journalctl -o json` (ms per unit) | `MESSAGE` lines can carry paths | after a change: the collector samples counts only (lines per unit per day, restarts, CPU and memory-peak from the accounting fields); `MESSAGE` never |
| 32 | `nvidia-smi` | GPU utilisation, VRAM, temperature, power, per-process VRAM | 12 %, 23,760 / 32,607 MiB, 44 °C, 53.77 W at 22:07 CDT; one process (python3, 22,780 MiB) | ~50 ms | numbers; a process binary path | adopt now (into `host-metrics` from the collector's existing gpu tile) |
| 33 | ComfyUI `127.0.0.1:8188` `/system_stats`, `/history`, `/queue` | RAM/VRAM free, job status counts, queue depth | `/history` returned 2 entries, both error; `/queue` unsampled; ComfyUI is a bare process (no unit, no journal) | ms, loopback | `/history` embeds the prompt graph in every entry, and so does each item of `/queue`'s `queue_running`/`queue_pending` lists (**content** in the raw response); `/system_stats` (device VRAM totals) and `GET /prompt` (`exec_info.queue_remaining`) carry no prompt by construction | after a change: the collector fetches **only** `/system_stats` and `GET /prompt`; `/history` and `/queue` are never fetched by anything automated, so no response that can carry a prompt is ever in the collector's memory. History ok/error counts are therefore **unmeasured** this round (§2.8, §4.7) |
| 34 | `~/comfyui/comfyui-krea2.log` | prompts executed, models loaded, errors | 493,099 B / 4,156 lines; last write 2026-09-04 23:46; 199 "Prompt executed" lines; 0 OOM markers; no per-line timestamps; the 09-05 OOMs (board: 18:21, 18:30) are in no durable record | grep | error lines embed model/LoRA filenames (content-domain) | never as text; the OOM rate is **unmeasured** today and stays so until #33 |
| 35 | systemd timers and failed units | armed timers, missed runs, failed units | 4 user timers (helm-collect 300 s, proton-drive-push 00:30, helm-flake-check 03:00, tmpfiles weekly); 0 failed units (system and user) at sample | ms | names and states | adopt now (counts into `host-metrics`; Helm's timers tile already reads them) |
| 36 | restic local repo and Proton push | snapshot age, counts, integrity, parity, CPU | 18 MB repo, 6 snapshots, last 2026-09-05 00:00:04, check clean; push 00:31–00:42, snapshots = remote = 6 | ms (unit state), seconds (`restic snapshots`) | ids and counts | adopt now (a `backups` block in `host-metrics`; a nightly `store-backed-up` check row, §4.8) |
| 37 | Nix store size | build-artifact growth | 123 GB (`du`, a full-store walk: minutes) | expensive | a number | after a change: `df` of the store filesystem plus the generation count, daily; never `du` in the 5-minute loop |
| 38 | `/var/lib/helm/status.json` | the tiles' numeric detail (load, memory, VRAM, temperature) and `top_denied` hosts | 5,134 B, rewritten every 300 s (no history) | none | numbers plus denied hostnames (`top_denied`, `collect.py:412`) and up to 2,000 chars of tool stderr in tile details (`:132`) | adopt the numbers into `host-metrics` through an explicit scalar signature — the status object itself is never handed to the writer (§3.4); `top_denied` and `stderr` are forbidden names (§3.5) |
| 39 | `/var/lib/helm-cache`, restic cache | cache sizes | 76 KB; 2.1 MB | stat | sizes | never (no signal in them) |
| 40 | SessionStart hook JSON (`session_id`, `source`) | context resets per day (startup, clear, resume, compact) | one event per session start; `tools/session-start.sh` already reads it | none | an id and an enum | adopt now (`sessions` stream) |

Forty sources. Twelve are content and are refused as such; each refused row names
the derivation that may be kept. Two derivations read a body to lift numbers
(`factory-usage.py` and `tools/ledger/factory.py extract`/`extract-dsh`, both
existing); the rest read a header line, a first line or a file name. Nothing
new reads a body (§7).

## 2. Areas of improvement

Ranked by what the problem cost in the last two days against what the signal
costs to collect. Each item cites its evidence, names the signal that would have
caught it earlier, and states the measurable acceptance that would show it
fixed.

**2.1 Seat deaths are misrecorded, and their causes live only in transcripts.**
Evidence: `cr10/CR2b.result` is `status=failed` with `exit_code=0` (wall 1,340 s,
313,541 input tokens) and `cr11/CR2b.result` is `failed` with `exit_code=1` —
both died on `402 in_flight_budget_exhausted` (board, START HERE "Now.");
`cr13/CR3r.result` is `status=done`, `FACTORY-COMMITS 1`, `exit_code=1` for a run
the board records as a provider error that made no commit ("the seat's echoed
template was parsed as a result"); `mcf/P1flash.result` is `failed` after 1 s with
`usage.model` null (the `UNKNOWN_MODEL` seed bug, board 2026-09-05 ~12:20); five
logs carry `.killed-by-reboot-2026-09-05` (switch #18, board ~17:04); `cr3` and
`cr4` "died silently" because `FACTORY_PLAN` was unset (board launch rule); `bk1`
died mid-task at 12:54. Seventeen task attempts have no `.result` at all (a
`<KEY>.log` with no `<KEY>.result` across 101 run dirs at 23:30 CDT; the
inventory counted 15 earlier in the day; the command is in §9). The board's
time for the 402 incident (~21:50 CDT) and the two result files' mtimes (20:32
and 20:51 CDT) disagree by about an hour: no clock was read. Signal: an
`error_class` enum on every result, computed by the driver at task end from
`exit_code`, `wall_s`, `usage.events` and a fixed pattern list over the log
tail — the enum enters the store, the text does not; plus a `runs` start row
with a machine timestamp. Acceptance: every `status=failed` result and every
attempt without a result (the §9 command's list) is classified without opening
a log by hand; `status=done` with an empty commit list is impossible (CR3r
item 6); the incident time is the row's `ts`, never a board estimate.

**2.2 Rework is the largest spend and it is counted by hand.** Evidence: 131 gate
review files in two days; the title parse (`REVIEW_RE`, §9) reads a verdict
from 104 of them — 58 approved / 46 rejected — and the other 27 carry a
verdict only in prose; OG1 took four rejections before landing, RT5 three, R3
three;
Opus gate tokens per review range 64,589–181,844 in the eight gates the
comparison docs itemise; the model comparison found the gate spend on the Claude
side "the larger cost of the two". Mutation results are in prose in 120 files
and machine-parseable in 19. The chain (`.result` → review → integrate) is joined
by key name and board reading. Signal: a `gates` row per review with verdict,
majors, minors, `mutants_killed/total`, round kind (first / fix / re-plan) and
the review commit time; a `tasks` row per result. Acceptance: fix rounds and
re-plans per landed task, and survivors per gate, print from the store for the
last 7 days with n; the 2026-09-05 chains above appear with the right round
counts (OG1 = 4 rejections, RT5 = 3, R3 = 3); the rejected fraction over the
parsed files equals the title parse's (46 / 104 = 0.44 tonight).

**2.3 Cost per landed task by (model, effort, kind, size) is unknown beyond
n = 2.** Evidence: `routing.toml`'s five openrouter rows rest on two documents at
n = 2 per arm (effort) and n = 2 per arm (model) plus one n = 1 measurement
(m2b); `effort:` and `route:` exist in 51 of 202 results, and in none of the
eight comparison-arm results; the seat's usage line
reports `reasoning: 0` on every result while the activity export itemises
6,340,776 reasoning tokens over 6,031 requests (claim
`reasoning-tokens-not-itemised` is a property of dsh's usage record, not of
OpenRouter); cache reads are unpriced (`cache_read_per_1m` 0.0); reported spend
was $62.28 on 09-04 and $66.61 on 09-05 against 59 landings, and the join is
only at (date, model), so per-landing cost is not attributable today. Signal:
`tasks.usage` per result, `ledger/activity-days` per (date, model), and the
(kind, size) parsed from the result's `route:` line (`implement/<kind>/<size>`;
`unknown` on the ~150 results without the line — no result carries a plan
reference, so the plan heading is not a source). Acceptance: `evidence report
routing` prints, per (route, role, kind, size, model, effort), n, approved
fraction, fix rounds, median wall, median tokens and reported cost share, and
refuses to print a row with n < 5 as anything but "insufficient".

**2.4 Time in gate and the landing pipeline have no timestamps of their own.**
Evidence: from the 55 parseable gate-review commits and their `.result` mtimes,
seat finish → review commit is median 14 min (mean 19, max 58); approve →
integrate commit is median 0 min (mean 2, max 26, n = 23). Those numbers took a
script over three sources; nothing prints them. The gate's own wall time and
tokens are unrecorded except in the three comparison docs. Signal: `gates.ts`,
`gates.review_commit_ts`, `tasks.result_mtime`, `runs` start/end, and the
integrate commit time. Acceptance: a `time-in-gate` figure per landing (median
and p90 over 7 days) prints from the store and matches the script's 14 min on
today's data within a minute.

**2.5 The board churns and the orchestrator's context is consumed
unmeasured.** Evidence: 93 of 331 commits since 09-04 touched
`docs/OPERATIONS.md`; 45 board handoff commits; the Stop hook blocked every turn
end for 35 minutes on 2026-09-05 (19:20–19:55, renderer mismatch, CR5) and
forced through four times (`ritual.log`); the HANDOFF of 18:30 was written at
"~90 %" context. There is no count of compacts, turns or tokens per landing.
Signal: `sessions` rows (startup / clear / resume / compact, one per hook
fire), ritual block rows with the condition, and — after Q3 — usage-only
extraction from the orchestrator's own transcript. Acceptance (of this design):
`evidence report churn` prints compacts per landing (from `sessions`) and board
commits per landing (from the git derivation of §1 rows 19–20: commits touching
`docs/OPERATIONS.md` ÷ `integrate … into integ/` commits, 7-day window) with n.
Separately, an operator expectation, not a test of this design: the ratio
(93 / 59 = 1.6 on 09-04–09-05) should fall to ≤ 1.0 once CR3r's in-flight state
removes the last hand-written status.

**2.6 Helm's two revision tiles are structurally non-green.** Evidence: 18 of 20
`helm-status` rows have `flake-check: warn` and `drift` is `fail` in 9 rows,
`warn` in 5, `ok` in 6; the environment review (2026-09-05) says both tiles
"grade the machine by commit id in a repo that takes 27–112 commits a day" and
"the operator has stopped reading them"; the docs-only rules landed (E5) and the
tiles still warn because the whole `nix flake check` has run at three revisions
in two days (`flake-check` rows: 1 nightly, 2 pre-switch) while the integrator
recorded 76 named checks. Signal: the tile's reason as an enum
(`behind-by-code` / `stale-26h` / `missing`) beside the verdict, and the green
fraction per day. Acceptance: the fraction of `ok` rows per tile per day prints
from the store; a redefinition ("every check named since the last full run is
green at HEAD" = partial cover) is a Helm decision the operator can take on
that number, not on a colour.

**2.7 The broker audit has request classes but no rollup and no liveness
signal.** Evidence: openrouter 247 allow / 45 deny / 4 error (43
`not-allowlisted`); cowork 3,407 / 1,203 / 26; 527 cowork paths carry a query
string; the cowork audit file stopped growing 2026-09-02 19:50 while its unit
kept logging; `bytes_in` is 0 for streamed responses; the raw files have no
rotation (data-and-models spec §10). Signal: a daily `broker-lane` row per
(instance, verdict, reason class) with `bytes_out` and `query_paths`, and
`audit_age_s` beside each instance's `active` state in `host-metrics`.
Acceptance: an audit file older than 24 h while its instance is active and has
served ≥ 1 request that day yields an `audit-stale` incident row; the daily
deny count per reason class prints for both instances back to 2026-09-02.

**2.8 GPU and VRAM headroom for the ComfyUI worlds are not recorded.**
Evidence: two OOMs on 2026-09-05 (18:21: LoRA patching on an fp8-cast
checkpoint with the text encoder resident; 18:30: `batch_size 335` on the live
canvas — board) exist in no file: `comfyui-krea2.log` stopped on 09-04 23:46 and
holds 0 OOM markers; the packaged ComfyUI runs as a bare process; Helm's gpu
tile computes utilisation, VRAM and temperature every 5 minutes and keeps only
`ok`. Sample now: 23,760 / 32,607 MiB used by one 22,780 MiB process. Signal:
`host-metrics.gpu` every 300 s and `host-metrics.comfyui` (VRAM free from
`/system_stats`, `queue_remaining` from `GET /prompt`). The OOM count itself
stays **unmeasured** in this round: the only endpoints that report job errors
(`/history`, `/queue`) carry the prompt graph, and this design fetches neither
(§1 row 33). It becomes measurable when the worlds plan runs ComfyUI under a
user unit: a count of journal lines matching one fixed pattern per cycle, the
`error_class` discipline (a count leaves, the line does not). Until then an OOM
is a hand-recorded `comfyui-oom` incident row. Acceptance: the operator repeats
the 09-05 batch-size OOM once and records the row; the store holds the 300-s
VRAM and queue samples around its `detected_ts`, and the gpu tile's headroom
detail shows the drop. Named gap: at 300 s the series has three points in 15
minutes and cannot show the ramp that caused the OOM (§4.7).

**2.9 The new stores' backup coverage is partly asserted, partly open.**
Evidence: `/var/lib/evidence` is in `services.proton-backup.paths`
(`hosts/core/proton-backup.nix:29–42`, twelve paths tonight; the count drifts,
the check `core-backup-wiring` is the citation); `/var/lib/lanes` and
`/var/lib/egress-broker` are not (claim `lane-ledger-and-broker-audit-unbacked`,
review by 2026-09-19) — and `/var/lib/lanes` holds prompt, response and diff
bodies (§1 row 25), so only its `ledger.jsonl` is a candidate (Q6); `~/factory`
(209 MB, ~150 MB/day) is not, by the N11 decision; restic holds 6 snapshots,
Proton mirrors 6. Signal: a nightly
`store-backed-up` check row (the newest snapshot lists every live stream file)
and a `backups` block in `host-metrics`. Acceptance: the check row exists every
night; a fixture that drops the store from the path list turns the row `fail`.

**2.10 Guard denials are audited on one side only, and at 2 records.**
Evidence: `dsh-openrouter --denials` holds 2 records (both `sudo`), while gate
reviews ran dozens of allow/deny probes in throwaway clones (cr12: a 26-row
over-denial table) that never reach the audit; `tools/orchestrator-guard.sh`
refused three of the orchestrator's own commands on 2026-09-05 (board) and
persists nothing; and the seat guard's reason string is not a constant — it
embeds the refused path or model id (`hook-guard.py:293, :442, :451`), so
"store the reason" would store the subject. Signal: a `guard-denials` row per
refusal on both sides, written by the guard itself with a `reason_code` from a
closed table and the subject hashed before anything else sees it. Acceptance:
the count of denials per `reason_code` per day prints for both guards; a probe
run in a live session appears as a row within the same minute; a fixture whose
denial names a path yields a row that does not contain the path.

**2.11 Measurements are voided by unverified settings.** Evidence: M2 was void
because both arms sent effort `medium` (board 2026-09-05 00:44); the Pro
plan-writing arm was void on a partial read (report §Method); the effort and
model comparisons exist because bespoke runs were needed to get n = 2; and the
eight comparison-arm results themselves carry no `effort:` line (the field
post-dates them), so the arms are told apart only by run name. Signal: every
`tasks` row carries the effort and model the wire actually saw (the
`request/header` value, as m2b confirmed) and the (kind, size) of the `route:`
line. Acceptance: `evidence report compare --by run` reproduces the effort
comparison's per-arm table from the migrated `em`/`ex` rows; `--by effort`
groups a synthetic fixture correctly, and groups the first five routine runs
that carry `effort:` per arm without a bespoke run.

**2.12 The store's own promises are unmeasured.** Evidence: claims
`evidence-flock-effect-unmeasured` (review by 2026-10-03) and
`drift-exact-measure` are open; `runs.jsonl` has 0 rows against a schema. Signal:
the nightly `store-policy` and `store-backed-up` check rows, a freshness rule
on them, and a concurrency test. Acceptance: the two check names appear in
`checks.jsonl` every night with `ok:true`; a `store-policy` row older than 26 h
prints as `unknown` in `evidence bundle` and turns a Helm tile `warn` (a check
that silently stops running must not look like a clean store); a test writes
200 rows from 8 processes and reads back 200 valid rows, and fails when the
flock is removed (or the note that `O_APPEND` suffices is recorded and the
claim closed).

## 3. The central store

### 3.1 Location and shape

The store stays at `/var/lib/evidence`. It exists, it is live, it is on the
restic path list, it has a writer library and CLI (`pkgs/evidence/evidence.py`),
a module (`nixosModules/evidenceStore.nix`), tests (`tests/evidence`, check
`evidence-unit`) and three readers (Helm's collector, `evidence bundle`, the
ledger). A second store would split the readers for no gain.

The shape stays: one JSONL file per stream, append-only under an exclusive
flock, sorted keys, compact separators, the envelope `{v, ts, kind}` written
after the caller's row so a writer cannot forge `v` or `ts`. Stream names match
`^[a-z][a-z0-9-]{0,31}$`. A reader skips a torn line. One change to the
envelope: `v` becomes per stream. Today `evidence.py:28` stamps a module-global
`VERSION = 1` on every stream alike; `append()` gains a one-line lookup in the
version map beside the allowlist (§3.5), so `checks` can move to v2 while
`helm-status` stays at v1.

Two classes of stream, made explicit:

- **Primary** — the row is the only record of the event (a check ran, a tile
  changed, a sample was taken, a session started). Never rewritten. Files sit
  directly in the store directory, as today.
- **Derived** — the row is computed from a file that exists elsewhere (a
  `.result`, a review, the activity export, an audit log). Rebuildable by one
  command, written idempotently by key — the discipline `ledger/` already has.
  Derived streams live under `/var/lib/evidence/derived/`, beside `ledger/`.
  Where the source is not backed up (the run tree, the audit logs, the lane
  ledger, the seat's transcripts), the derived row is the durable copy.

One high-rate stream (`host-metrics`) rotates monthly by file name
(`host-metrics-2026-09.jsonl`); `evidence.read()` globs. Everything else is one
file. Nothing is deleted, with one exception: a row the nightly audit finds in
violation of §3.5 is moved out of its stream into `quarantine/` (§3.6) — the
rule is that nothing *valid* is ever removed. At today's rates the whole store
grows by tens of MB a year (§3.2).

### 3.2 SQLite: not now, and the condition under which it is adopted

The case for SQLite: it is in the stdlib (3.53.3 under the devShell's Python
3.14.7, the same stdlib the Helm units' bare `pkgs.python3` carries), a single
file, no server, and joins across streams become one query.

The case against, today: no report needs an index. Every report in §4 is a full
scan of at most ~10^5 rows joined in memory by run and key. Measured: 105,000
rows of the `host-metrics` shape (a year at one sample per 300 s) are 72.8 MB at
693 B a row and the stdlib reader parses them in 0.53 s. `checks` at today's
event rate (~205/day) is ~75,000 rows a year, ~17 MB. `tasks` at 100 results a
day is 36,000 rows. The two readers with a wall-time budget — the session hook
(2 s, reads `checks` and `helm-status` only) and Helm's collector (every 300 s,
the same two) — never touch the big streams. A second copy of the data is a
second thing to prove consistent, and the project has twice chosen files plus
scripts with an embedded engine as a later step (data-and-models spec §2.3;
session-context spec, "No database").

Decision: JSONL is the store; the reader builds tables in memory. SQLite would
be a **derived, rebuildable cache**, never the store. The trigger is a
conversation, not an automatic switch: when `evidence report` exceeds 2 s wall
on the live store, or a report needs a join the one-pass reader cannot express,
the orchestrator raises it with the measured numbers and the operator decides;
the decision lands as a commit, like every other policy change here. If
adopted: `/var/cache/evidence/telemetry.sqlite` (tmpfiles `0700`,
operator-owned), built by `evidence rebuild --cache`, never written by any
writer, deletable at any time, not backed up. DuckDB and kuzu are not stdlib
and add packages; they stay refused.

### 3.3 Streams

Every row carries `v` (int, per-stream schema version from the version map),
`ts` (RFC3339 `Z`, set at append) and `kind`. Derived rows also carry `src`
(the reader id) and `src_ts` (the source's own time). Enum fields take only
the listed words. Every string field is declared with one of the string
classes of §3.5 (enum, id, model-id, key, rev, ts, hash, rooted path); there
is no free-text class, so "str" in these tables means the id class unless the
row says otherwise. The allowlist in §3.5 is the machine-readable form of
these tables.

**`checks`** (kind `check`) — v2. Fields as SCHEMA.md v1 with three changes:
`src` becomes an enum (`helm-nightly`, `seat-integrate`,
`orchestrator-integrate`, `orchestrator-preswitch`, `dark-factory-verify`,
`evidence-audit`); `run_id` (str or null) is added so a check the integrator
runs ties to its run; and `log_tail` is replaced by `log_tail_sha256`,
`log_tail_len` and `fail_class` (enum `lint`, `unit`, `eval`, `vm`, `build`,
`timeout`, `unknown`, computed where the check ran from the tail's fixed
patterns, the `error_class` discipline). `record-check --log-tail-file` keeps
the argument but binds it: the path must resolve under a declared build-log
root (`$TMPDIR`/the flake-check unit's work dir, the seat's `integrate.log`
dir) and the tail is hashed, never stored; `--log-tail-file /etc/passwd` is
refused with exit 2. The one existing v1 row keeps its `log_tail` and is
audited under the v1 shape; nothing writes v1 again. Primary. Key: none
(observations). Forever.

**`helm-status`** (kind `helm-status`) — unchanged (`tiles` name → enum,
`reason` `change|heartbeat`). Primary. Forever. The writer changes (§3.4): it
calls `evidence.append()` instead of its own `_append_status_row`.

**`runs`** (kind `factory-run`) — two declared shapes under one kind, told
apart by `driver`.

Shape A, `driver: dark-factory` (SCHEMA.md v1, exactly what
`dark-factory.js:658–670` emits today, unchanged): `plan` (rooted path),
`prefix` (id), `baseline` (40-hex), `integration_branch` (id),
`tasks[]{key, status (id ≤ 32), commit (40-hex or null), fixRounds (int)}`,
`verify` (enum `pass|fail|skipped|none`), `delivered` (int), `agents` (int),
`output_tokens` (int), `run_id` (id or null). `driver` is implied by the
presence of `prefix` and stamped by the reader. SCHEMA.md marks this shape
*legacy* the day shape B lands; a later task may move the recorder to shape B
by a real change to `dark-factory.js`, which is not XS. Ordering rule: T1
declares shape A **before** the next dark-factory run, or that run's report is
refused by the writer-side allowlist and lost.

Shape B, `driver: seat` — one row at start, one at end:

| field | type | meaning |
|---|---|---|
| `run_id` | id | the seat run name (`cr15`) |
| `driver` | enum `seat` | which driver |
| `event` | enum `start`, `end` | which edge |
| `repo` | id | repo name per `docs/ledger/repos.toml` |
| `plan` | rooted path (`docs/superpowers/plans/`, ≤ 120) or null | plan file |
| `base` | 40-hex or null | the base commit |
| `groups` | list of lists of task keys (key class, §3.5) | the wave's groups |
| `pid` | int or null | the wave's pid (start only; 0 is never written) |
| `status` | enum `done`, `partial`, `failed`, `killed`, `unknown` | end only |
| `tasks` | list of `{key, status (the tasks enum), commit (40-hex or null), fix_rounds (int)}` | end only |

Key `(run_id, event)`. Start rows are primary (`run.meta` lives under
`~/factory`, which is not backed up); end rows are derived from the `.result`
set. Sources: CR3r's `run.meta` and `factory-wave`'s summary. Forever.

**`tasks`** (kind `task-result`) — one row per `.result` file.

| field | type | meaning |
|---|---|---|
| `run_id`, `key` | id; key | identity |
| `repo`, `plan` | id; rooted path (`docs/superpowers/plans/`, ≤ 120) or null | attributed as `tasks.py` does (workspace origin) |
| `kind`, `size` | enum `code`/`docs`/`unknown`; enum `XS`/`S`/`M`/`L`/`unknown` | parsed from the `route:` line (`implement/<kind>/<size>`); `unknown` when the line is absent (151 of 202 today) — no result carries a plan reference |
| `model` | model-id | the model id the driver launched |
| `effort` | enum `off`/`low`/`medium`/`high`/`xhigh`/`unknown` | the effort the driver set (the wire value, per m2b); `unknown` on every result without an `effort:` line, including all eight comparison arms |
| `route` | pattern `^(explicit\|unknown\|implement/(code\|docs)/(XS\|S\|M\|L))$` | the routing decision |
| `status` | enum `done`/`partial`/`failed`/`skipped`/`unknown` | the driver's status |
| `exit_code` | int or null | the seat's exit code, independent of `status` |
| `wall_s` | int | seat wall clock |
| `commits`, `commits_declared` | int; int | counted from the commit list; the `FACTORY-COMMITS` number |
| `checks` | map (key pattern `^[a-z][a-z0-9-]{0,63}$`, ≤ 64 entries) → enum `pass`/`fail`/`not-run` | the `FACTORY-CHECKS` pairs; a name outside the pattern drops the whole map |
| `checks_parse` | enum `ok`/`refused`/`missing` | whether the map was taken; `refused` is the agent-written line failing the key pattern (the row still lands, the map does not) |
| `head`, `base` | 40-hex or null | branch head and base |
| `files_changed`, `insertions`, `deletions` | int | from the diffstat's summary line |
| `usage` | `{input, output, cache_read, reasoning, events, duration_s}` | the `usage:` line (`factory-usage.py`) |
| `error_class` | enum (table below) | why a task did not finish, without reading its log |
| `seat_unit` | id or null | `seat@<id>` when submitted through the unit |
| `result_path`, `result_mtime` | rooted path (`~/factory/runs/`, ≤ 200); ts | provenance |

Key `(run_id, key)`. Derived from the `.result` file; the durable copy. Forever.

`error_class` is computed by the driver at task end from metadata plus a fixed
pattern list applied to the last 4,000 bytes of the log. The enum leaves the
driver; the text does not.

| class | rule |
|---|---|
| `budget-402` | the tail matches the fixed pattern for `402` with `budget_exhausted` |
| `provider-error` | the tail matches the provider-error pattern list (`502`, `503`, `529`, `upstream`, `provider`) |
| `unknown-model` | the tail matches `UNKNOWN_MODEL` |
| `boot-failure` | `wall_s` < 10 and `usage.events` < 50 and no pattern matched |
| `no-result-line` | the driver synthesised the result block |
| `template-echo` | `status=done` and the commit list is empty (refused going forward by CR3r item 6; classified for the backfill) |
| `timeout` | `exit_code` 124 |
| `submit-failed` | the `seat: submit failed` line |
| `killed` | no `.result` and a log with a `.killed-by-*` suffix (recorded on the `runs` end row) |
| `none` | otherwise |

**`gates`** (kind `gate-verdict`) — one row per review file.

| field | type | meaning |
|---|---|---|
| `run_id`, `key`, `chain_root` | id; key; key | identity; `chain_root` per `tasks.py` `chain_root()` (:79) |
| `round_kind`, `round` | enum `first`/`fix`/`replan`/`unknown`; int | position in the chain (`b`, `c` = fix; `r`, `rb` = re-plan) |
| `reviewer` | enum `opus`/`sonnet`/`deepseek`/`fable`/`unknown` | who judged |
| `route` | enum `claude`/`openrouter` | which route |
| `model` | model-id or null | model id when the file names it |
| `verdict` | enum `approved`/`rejected`/`unknown`/`none` | the verdict. There is no `rework` value: `REVIEW_RE` admits only APPROVED/REJECTED, and no file carries a third word in a parseable place; a re-plan is `round_kind: replan`, not a verdict |
| `majors`, `minors` | int or null | counts |
| `mutants_total`, `mutants_killed` | int or null | the mutation battery |
| `gate_tokens`, `wall_s` | int or null | when the harness reports them |
| `review_path`, `review_sha256` | rooted path (roots `docs/reviews/`, `runs/`; ≤ 200); hash | which file; content hash |
| `review_commit`, `review_commit_ts` | 40-hex or null; ts or null | the `docs: gate review` commit |

Key `review_path`. Derived from a front-matter block at the top of every
`docs/reviews/*opus-review*.md` (keys `run`, `key`, `verdict`, `reviewer`,
`majors`, `minors`, `mutants_killed`, `mutants_total`, between two `---` lines;
the H1 stays so `REVIEW_RE` keeps working), from the DeepSeek `.review.md`
verdict line, and from `git log`. The body of a review never enters the store.
Forever.

**`ledger/*`** (usage and cost) — the five files of `tools/ledger/schema.md`,
unchanged, plus `ledger/activity-days.jsonl` (kind `activity-day`): `date`,
`model`, `requests`, `cost_usd`, `tokens_prompt`, `tokens_completion`,
`tokens_reasoning`, `tokens_cached`, `cancelled`, `finish` (`{tool_calls, stop,
length, other}`), `generation_ms_mean`, `providers` (distinct count). Key
`(date, model)`. Derived from the activity export by extending
`_load_activity` (`factory.py:453`), which already buckets `cost_total` by
(`created_at` date, `model_permaslug`) and never reads `generation_id`,
`user`, `api_key_name` or `app_name`; the extension returns the full bucket
(tokens, `cancelled`, finish counts, `generation_time_ms` mean, distinct
`provider_name` count) and persists it. Two changes to the existing ledger
shapes: `factory-findings.title` becomes `title_sha256` (a reviewer model's
sentence is prose; the hash still deduplicates a finding across rounds, and
the sentence stays in the journal it came from), and `lane-jobs` is derived
from `ledger.jsonl` (`ts, job, kind, model, provider, usage, wall_s, exit`)
instead of `results/*.json`. `factory-*.label` stays: it is the driver's role
label (`recorder`, `implementer`), an id. Per-task usage is `tasks.usage`; per
interactive-seat session is `dsh-sessions.jsonl` (counts).

**`incidents`** (kind `incident`) — one row per incident, hand-recorded or
derived.

| field | type | meaning |
|---|---|---|
| `id` | str | `YYYY-MM-DD-<n>` for hand rows; `auto-<stream>-<key>` for derived |
| `class` | enum: `seat-death-budget`, `seat-death-provider`, `seat-death-boot`, `seat-death-killed`, `dead-launch`, `result-misparse`, `fabricated-commit`, `gate-chain`, `check-red`, `helm-fail`, `audit-stale`, `unit-failed`, `switch-reboot`, `ritual-block`, `guard-denial-burst`, `measurement-void`, `backup-parity`, `comfyui-oom`, `store-policy-violation`, `other` | what kind |
| `severity` | enum `info`/`warn`/`fail` | weight |
| `source` | enum `auto`/`orchestrator`/`operator` | who recorded it |
| `refs` | `{run_id?, key?, rev?, unit?, tile?, instance?, review_path?, stream?, snapshot?}` | what it points at (ids, a rooted path, a restic snapshot id) |
| `detected_ts` | ts | when the source saw it |
| `board_commit` | 40-hex or null | the board commit that carries the prose |
| `resolved_by` | 40-hex, task key, or null | what closed it |

There is no `note` field. The first draft had a 200-char sentence here; a
sentence written by a model into a primary, backed-up, append-only file is
free text by any name, and it moved a record of judgements out of git, where
the board of record and invariant 5's reviewable diffs live. The prose stays on
the board; the row points at the commit. Key `id`. Hand rows are primary;
derived rows are appended once (idempotent by id) by `evidence derive
incidents` from: `tasks.error_class ≠ none`
(`seat-death-*`, `result-misparse`), `checks.ok = false` (`check-red`), a tile
transition to `fail` (`helm-fail`), `broker-lane`/`host-metrics` audit age
(`audit-stale`), failed units (`unit-failed`), a boot-id change
(`switch-reboot`), ritual blocks (`ritual-block`), a `rejected` verdict at
round ≥ 2 (`gate-chain`, info). Forever.

**`host-metrics`** (kind `host-sample`; file per month) — one row per collector
cycle (300 s).

| field | type | meaning |
|---|---|---|
| `load1`, `mem_total_mib`, `mem_avail_mib`, `swap_used_mib` | float; int; int; int | `/proc` values |
| `disk_free_frac` | `{root, nix}` floats | `statvfs` |
| `boot_id` | str (8 hex) | for reboot detection |
| `gpu` | `{util_pct, mem_used_mib, mem_total_mib, temp_c, power_w, procs}` | `nvidia-smi` |
| `comfyui` | `{up, vram_free_mib, vram_total_mib, queue_remaining}` | `/system_stats` and `GET /prompt` only; nulls when down. No history counts (§1 row 33) |
| `units` | `{failed_system, failed_user, timers_armed, timers_total}` | `systemctl` counts |
| `backups` | `{snapshot_age_h, snapshots, remote, parity}` | what the two backup tiles compute |
| `broker` | map (closed key list: `openrouter`, `cowork`; extended by commit) → `{active, audit_age_s, audit_rows}` | liveness of each audit |
| `journal_mib` | int or null | once a day |

Primary. No key (samples). About 700 B a row (measured on the synthetic
shape), ~200 KB a day, ~73 MB a year. Forever, monthly files. The writer is
`record_metrics(store, *, load1, mem_total_mib, …, gpu, comfyui, units,
backups, broker, journal_mib)` — an explicit keyword signature of scalars and
small typed dicts. It is never handed the tile status object, which carries
`top_denied` (five hostnames, `collect.py:412`) and 2,000-char `stderr`
details (`:132`); the cheapest mutation against this design is "pass `status`
through", and §3.5 (h) is the test that catches it.

**`broker-lane`** (kinds `egress-day`, `lane-day`) — daily rollups.

| kind | fields | key |
|---|---|---|
| `egress-day` | `date`, `instance` (enum as `host-metrics.broker`), `verdict` (`allow`/`deny`/`error`), `reason_class` (closed enum, table below), `requests`, `bytes_out`, `bytes_in`, `query_paths`, `distinct_hosts` | `(date, instance, verdict, reason_class)` |
| `lane-day` | `date`, `lane`, `model`, `jobs`, `ok`, `failed`, `cost_usd`, `tokens {prompt, completion, reasoning, cached}`, `wall_s_sum` | `(date, lane, model)` |

`reason_class` is mapped from the audit row's `reason` by **exact prefix**
against the strings `pkgs/broker/policy.py` emits; everything after the prefix
is dropped; no match is `other`; the raw reason is never stored:

| code prefix (verbatim) | `reason_class` |
|---|---|
| `ok` | `ok` |
| `not-allowlisted` | `not-allowlisted` |
| `connect-not-allowlisted` | `connect-not-allowlisted` |
| `host-header-mismatch: ` (:215; carries two hostnames) | `host-header-mismatch` |
| `host/sni mismatch: ` (:221, :225; carries two hostnames) | `host-sni-mismatch` |
| `path-not-permitted` (:241) | `path-not-permitted` |
| `path-not-normalizable` (:239, :288) | `path-not-normalizable` |
| `zdr-unpatchable-body` (:312) | `zdr-unpatchable-body` |
| `zdr-unpatchable-streamed-body` (:346) | `zdr-unpatchable-streamed-body` |
| `upstream or client error` (:386) | `upstream-or-client-error` |
| anything else | `other` |

Derived daily by the rollup timer from the audit logs (mode 0644) and the lane
ledger (group `lane`); the durable copy while the raw files are unbacked.
`host`, `sni`, `path` and `client` never enter the store; the Helm page keeps
`top_denied` for the operator's eyes. Forever.

**`guard-denials`** (kind `guard-denial`) — `ts` (the guard's), `guard`
(`seat-hook`/`orchestrator-guard`), `event` (enum `PreToolUse`/`Stop`/`other`),
`tool` (id ≤ 32), `reason_code` (enum below), `subject_sha256`, `subject_len`,
`session_id` (id or null). Key `(guard, ts, subject_sha256)`. There is no
`reason` string: the seat guard's strings interpolate the refused path
(`hook-guard.py:442, :451`) and the agent-supplied model id (`:293`), so the
string *is* the subject. Each guard maps its rule to a code at the point of
denial and writes `{ts, event, tool, reason_code, subject_sha256, subject_len}`
to its own state file — `hook-guard.py` to `$DSH_HOME/guard-denials.jsonl`
(inside the seat unit's writable set), `orchestrator-guard.sh` to
`$XDG_STATE_HOME/nixos-agent-env/guard-denials.jsonl` — with the human string
going where it goes today (stderr, the transcript). `evidence ingest denials`
reads the two state files through the validating writer. The transcript walk
(`dsh-openrouter --denials`) stays an operator-invoked tool and runs in no
timer. Forever.

`reason_code`: `sudo`, `nixos-rebuild`, `systemctl`, `helm-control`,
`key-file`, `protected-path`, `symlink-escape`, `outside-project`,
`model-not-in-table`, `routing-table-unreadable`, `payload-unparseable`,
`input-too-deep`, `rule-error`, `budget-exceeded`, `other` — one per
`return` in `hook-guard.py` (:219–:228, :365–:374, :400, :442–:451) and per
`deny` call site in `orchestrator-guard.sh` (:683, :713); the mapping table
lives in each guard and is closed.

**`sessions`** (kinds `session-start`, `ritual-event`) — `session-start`:
`session_id`, `source` (`startup`/`clear`/`resume`/`compact`), `repo`.
`ritual-event`: `session_id`, `event` (`block`/`allow-after-max`/
`override-used`/`precompact`), `conditions` (list of `stale-queue`,
`uncommitted-reviews`, `uncommitted-plans`, `uncommitted-board`, `other`).
Primary (hook events). Key `(session_id, ts)`. Forever.

### 3.4 Writers — which tool writes which stream, and the change to each

One rule before the table: **every row enters the store through
`evidence.append()`**, the function that validates (§3.5). Today two writers do
not: `pkgs/helm/collect.py:738 _append_status_row` opens the stream file and
writes the envelope itself, and `tools/ledger/factory.py:74 _write_jsonl` /
`:80 _merge_jsonl` write every `ledger/*` file. Both are changed here.
`helm.nix:112` already embeds the whole `pkgs/evidence` directory for the
collector, so `collect.py` imports `evidence` and calls `append()`; the ledger's
merge (the one rewrite-by-key area) goes through `evidence.validate()` per
record and `evidence.replace_stream()` for the atomic rewrite, both in the same
module. A lint-gate grep refuses `O_APPEND`, `open(…, "a")` and any literal
`/var/lib/evidence` outside `pkgs/evidence/evidence.py` under `pkgs/evidence`,
`pkgs/helm`, `tools/ledger`, `tools/factory` and the two hook scripts; a unit
test runs each writer against a temp store with `os.open` wrapped and asserts
the only opener of a store path is `evidence.append`/`replace_stream`. Hook
scripts and guards that must never block on the store write a *state file*
outside it; the ingest that reads the state file is the validating writer.

| stream | writer today | the change (every row via `append()`) | size |
|---|---|---|---|
| `checks` | `helm-flake-check` (nixosModules/helm.nix:150), `factory_record_check` (tools/factory/seat/factory-lib.sh:58–76), the dark-factory verify prompt, the orchestrator's integrate/preswitch recipes | `record-check` moves to the v2 row (`log_tail` → hash, length, `fail_class`; `--log-tail-file` rooted); the two callers pass `--run <id>` where they have one; nothing else changes at the call sites | S |
| `helm-status` | `pkgs/helm/collect.py:774 record_status` → `_append_status_row` (bypasses the library) | `record_status` calls `evidence.append(store, "helm-status", row)`; `_append_status_row` is deleted | XS |
| `runs` | the dark-factory recorder (`dark-factory.js:658–670`, never ran on core) | shape A declared as is (T1) — no change to `dark-factory.js`; confirm one row lands post-switch. `factory-wave`: after writing `run.meta` (CR3r), `evidence record runs --json <start row>`; after the summary, the end row | XS + XS |
| `tasks` | nobody | `factory-task` (runs on the host as the wave's child, outside the seat unit), after `} >"$result"`: `evidence ingest result "$result" \|\| factory_log "evidence: could not record $key"`; the ingest binds the path to `~/factory/runs/` and validates the `FACTORY-CHECKS` keys; `error_class` is a function in `factory-lib.sh` that prints the enum | S |
| `gates` | nobody | two writers: `evidence ingest reviews <repo> <runs-dir>` in the rollup timer, and one line in `tools/factory/seat/factory-integrate` after the review commit (a runtime writer, listed as such); the front matter in review files is the source change (a migration script plus a lint) | S |
| `ledger/*` | `tools/ledger/factory.py` (never run on core; writes files itself) | `_write_jsonl`/`_merge_jsonl` route through `evidence.validate()` + `replace_stream()`; `extract-lane` re-pointed at `ledger.jsonl`; `_load_activity` extended and given a persist path (`ingest-activity <csv>`, path bound to `~/strategy/ledger/`); the rollup timer runs `extract` per new workflow dir, `extract-dsh` per run's sessions dir, `extract-lane`, `ingest-activity` | S |
| `incidents` | nobody | none for hand rows (`evidence record incidents --json` works once the kind is declared); `evidence derive incidents` in the rollup timer; `audit-store` writes `store-policy-violation` rows | S |
| `host-metrics` | nobody (the collector computes and discards) | `collect.py`: one call to the new `record_metrics(store, *, …scalars…)` beside `record_status`, passing named numbers lifted from the tiles — never `status` itself (§3.3) | S |
| `broker-lane` | nobody | new `evidence rollup egress --date <d>` and `rollup lane`; a user timer `evidence-rollup.timer` (daily 00:10, `Type=oneshot`, `Persistent=true`, `ConditionUser` = operator) in `evidenceStore.nix` | S |
| `guard-denials` | `hook-guard.py` (stderr → transcript), `orchestrator-guard.sh` (nothing) | `hook-guard.py _deny()`: one JSON line `{ts, event, tool, reason_code, subject_sha256, subject_len}` appended to `$DSH_HOME/guard-denials.jsonl` (`hashlib`, in-process, `try/except: pass`); `orchestrator-guard.sh deny()`: the same shape to `$XDG_STATE_HOME/nixos-agent-env/guard-denials.jsonl` (`sha256sum`, `\|\| true`); `evidence ingest denials` in the timer validates both | S |
| `sessions` | nobody (`session-start.sh` already parses the hook JSON; `ritual.sh` already knows the block reason) | one `evidence record sessions --json …` line in each, guarded so a missing `evidence` never fails the hook | XS |
| `store-policy` (a `checks` row) | nobody | `evidence audit-store` in `evidence-audit.timer` (daily 23:40, before the 00:00 restic run; `Persistent=true`) records the check; quarantine on violation (§3.6) | S |

Every writer keeps today's rule: a recording problem is logged and never fails
the caller (the check verdict, the task, the hook stand). Every ingest that
takes a path binds it to a declared root and exits non-zero outside it:
`ingest result` → `~/factory/runs/`, `ingest reviews` → the repo's
`docs/reviews/` and `~/factory/runs/`, `ingest-activity` →
`~/strategy/ledger/`, `ingest denials` → the two state files, `record-check
--log-tail-file` → the build-log roots. `~/strategy` is a hook-guard protected
prefix precisely because agents must not read it; an ingest that took any path
would be a read-a-file-into-the-store gadget for anything running as the
operator.

### 3.5 The user-data exclusion rule, as a check

The rule: a row may hold identifiers, enums, numbers, timestamps, hashes and
sizes. It may not hold prompt, response, transcript, file, image, basket or
key material, and — since any of those can be carried by a sentence, a file
name or an address — it may not hold free text at all. There is no free-text
class in any declared stream.

What the fences are, and what they are not: they are checks on **what a
writer hands to `append()`** and on **what is in the files**. They bind the
writers this design names; they do not bind a uid. The seat agent runs as the
operator (`nixosModules/seatLane.nix:165`, `User = cfg.operatorUser`), so a
process outside the writers can `>>` a row into a stream file with none of the
four fences running. §3.6 says what stops that (the seat unit's sandbox) and
what catches the rest (the audit, which is the enforcement of record).

Enforced in five places, all from one allowlist file
`pkgs/evidence/streams.py` (one dict per kind — two for `factory-run` and for
`check` (v1 read-only, v2) — field → class, nested shapes and map key patterns
spelled out, plus the per-stream version map):

1. **Writer-side.** `append()` validates the row against the kind's allowlist
   before taking the lock: an undeclared kind, an undeclared field, an enum
   value outside its list, a string outside its class, a map key or list
   element outside its pattern (checked at every depth), a map over its entry
   cap, or a row over 16 KB is refused (exit 2, nothing written). `evidence
   record` therefore accepts only declared kinds. Fixture kinds for tests are
   declared in the test. The **string classes**: `enum` (a listed word);
   `id` — `^[A-Za-z0-9._:+-]{1,120}$` (no `/`, no `@`, no space: neither a
   path nor an address can match); `model-id` —
   `^[a-z0-9][a-z0-9._-]{0,63}(/[a-z0-9][a-z0-9._-]{0,63})?$` (at most one
   slash; `deepseek/deepseek-v4-pro-0813`); `key` — a task key,
   `^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$`; `rev` — 40 hex; `ts` — RFC3339 `Z`;
   `hash` — 64 hex; `rooted path` — declared per field with its root(s) and a
   cap, must resolve under the root, no `..`, no `\n`. A string that matches
   no class is refused, not capped. The first draft's id class admitted `/`
   and `@`, which is the shape of an absolute path and of an email address;
   that hole is closed by construction.
2. **Forbidden names**, a second fence independent of the allowlist. The rule
   is an **exact match** on the case-folded field name with `-` and `_`
   normalised, at every depth, including map keys. The list: `prompt`,
   `prompts`, `completion`, `response`, `content`, `text`, `message`,
   `messages`, `body`, `transcript`, `reasoning_text`, `stdout`, `stderr`,
   `log`, `output`, `brief`, `diff`, `patch`, `note`, `notes`, `title`,
   `summary`, `snippet`, `excerpt`, `path`, `file`, `file_path`, `log_path`,
   `cwd`, `host`, `hostname`, `host_header`, `sni`, `url`, `query`, `client`,
   `ip`, `addr`, `peer`, `top_denied`, `subject`, `command`, `cmd`, `argv`,
   `args`, `env`, `basket`, `recipient`, `user`, `api_key`, `key_name`,
   `token`, `secret`, `password`, `email`, `slug`. Declared exceptions, each a
   rooted-path class with its root (the exception is an allowlist entry, and
   the test in the next paragraph keeps the two lists honest):
   `factory-findings.file` (repo-relative, no leading `/`, ≤ 200),
   `tasks.result_path` (`~/factory/runs/`), `gates.review_path`
   (`docs/reviews/`, `runs/`), `tasks.plan`/`runs.plan`
   (`docs/superpowers/plans/`), and `checks.log_tail` **in v1 rows only**
   (read by the audit, written by nobody). Under exact matching
   `subject_sha256`, `subject_len`, `distinct_hosts`, `log_tail_sha256` and
   `query_paths` pass, as intended; `file_path`, `top_denied` and `sni` do not.
3. **Map keys and list elements.** Every map declares a key pattern and an
   entry cap; every list declares its element class. `tasks.checks` keys:
   `^[a-z][a-z0-9-]{0,63}$`, ≤ 64 entries (the `FACTORY-CHECKS` line is
   agent-written inside the seat unit); `host-metrics.broker` and
   `egress-day.instance`: the closed list `openrouter`, `cowork`;
   `runs.groups`: lists of `key`; `helm-status.tiles` keys: the tile-name
   pattern; `incidents.refs` keys: the declared set. A key outside the
   pattern refuses the row — except `tasks.checks`, where the map is dropped
   and `checks_parse: refused` recorded so the rest of the result still lands.
4. **Secret shapes** — a backstop for known shapes, and not the reason any
   field is safe. Every string value is scanned for `sk-or-v1-`, `sk-ant-`,
   `Bearer `, `-----BEGIN`, `AKIA[0-9A-Z]{16}`, `ghp_`, `xox[bp]-`,
   `AGE-SECRET-KEY-` (the basket identity), `age1` at a word start (a
   recipient), `eyJ` at a word start (a JWT); a match is a violation. The
   restic repository password has no shape and no scan can catch it, which is
   why the arbitrary-file channel (`--log-tail-file`) is bound and hashed
   rather than the list lengthened. (DA1 was rejected for a real key *name* in
   a fixture; the name fence above is for that case.)
5. **The audit.** `evidence audit-store` re-runs fences 1–4 over every row of
   every live stream and, unlike the writer, can act on a row that is already
   in a file (§3.6, quarantine).

Where it runs: `tests/evidence/test_streams_policy.py` under `evidence-unit`
(fixtures for every kind, valid and invalid, plus one test that walks every
declared field of every kind in `streams.py` through the name fence — so a
name added to the forbidden list that a declared stream uses fails the suite
rather than the writer at 03:00); the lint-gate grep of §3.4 (no direct opens,
no forbidden name passed by a writer); and `evidence audit-store`, run nightly
by `evidence-audit.timer` at 23:40 over every row of every live stream, whose
verdict is recorded as the check `store-policy` (class `unit`, src
`evidence-audit`). The audit self-attests: it writes its verdict into the
store it audits, as the uid that could have written the bad row. The outer
check is the operator's own periodic read of `evidence bundle`, which prints
the last `store-policy` row and calls it `unknown` past 26 h.

Mutations that make the check falsifiable, each red before the change:
(a) a fixture row gains `"prompt": "x"` → the test fails; (b) a string field
receives a 201-char sentence → fails (no class admits it); (c) `sk-or-v1-abc`
inside `guard-denials.tool` → fails; (d) delete the v1 `log_tail` entry → the
existing `checks` v1 fixture fails under the audit (the allowlist is
load-bearing); (e) delete the forbidden-name list → (a) must still fail through
the allowlist, and deleting the allowlist entry instead must still fail through
the names: each fence is tested with the other removed; (f) a writer that
never calls `append()` — a test module that opens a temp-store file directly →
the direct-open test fails; (g) a hostile `.result` whose `FACTORY-CHECKS` line
carries a 4 KB key → the fixture asserts `checks_parse: refused` and no key
longer than 64 chars in the store; (h) `record_metrics` is handed the tile
status object (with `top_denied` and a `stderr` detail) → the name fence
fails; (i) a path-shaped value (`/home/x/baskets/a.md`) or an address in an id
field → refused by the class, not stored; (j) a row appended to a scratch
store with `>>` and no envelope → the writer tests are blind to it by design,
and `audit-store` on that store reports 1 violation, quarantines it and
records `store-policy` `fail` — an audit test, not a writer test.

### 3.6 Access

- **Who can touch the store, plainly.** The store is owned by the operator's
  uid, and so is every seat agent (`seatLane.nix:165`). A mode cannot separate
  them. What separates them is the seat unit's sandbox: `ProtectSystem=strict`
  with `ReadWritePaths` limited to `/var/lib/seat`, `~/factory`,
  `~/nixos-agent-env`, `~/flakes` and `~/.local/share/dsh-openrouter`
  (`seatLane.nix:169–176`) — the store is **read-only inside the unit** and
  stays so; `evidence-eval` asserts the store path is in no seat
  `ReadWritePaths`/`BindPaths`. What the seat *can* write is a source: a
  `.result` under `~/factory` (hence the key patterns and the rooted ingest),
  and its own `$DSH_HOME` state file (hence the ingest validates it). Inside
  the unit the store is readable — rows are numbers and ids by §3.5, and that
  is the whole reason the exclusion rule is a check and not a hope. Outside
  the unit (an interactive `dsh-openrouter` session on the host, or any script
  the operator runs) the uid is shared, the fences are not in the path, and
  only the audit catches a bad row. The first draft's "no agent process reads
  the store" was false and is withdrawn.
- **The audit is the enforcement of record.** `evidence audit-store` runs at
  23:40 (`evidence-audit.timer`, `Persistent=true`), twenty minutes before the
  00:00 restic snapshot and fifty before the 00:30 Proton push, so a row that
  fails §3.5 is out of the file before the file is copied. On a violation it
  (1) rewrites the stream without the offending rows under the same flock and
  an atomic rename — the one exception to append-only, and the only time a
  row leaves a stream; (2) writes the rows to
  `/var/lib/evidence/quarantine/<stream>-<ts>.jsonl` (`0600`), a directory the
  restic path list does not include (`core-backup-wiring` asserts the
  exclusion) and the readers never glob; (3) appends an `incidents` row
  `store-policy-violation` with `refs.stream`, the row count and, when a
  snapshot was taken between the row's `ts` and now, the snapshot id; (4)
  records `store-policy` `fail`. The operator then reads the quarantine file
  as the operator (it may be user data, that is the point), deletes it, and
  where a snapshot id is named runs `restic forget <id> --prune` and lets the
  next push mirror the repository — the incident row is the checklist. The
  audit runs as the operator uid and could itself write a bad row; the outer
  check is the operator's read (§3.5).
- **Mode.** The module's tmpfiles rule becomes `d ${path} 0700 ${owner} - -`
  and `d ${path}/quarantine 0700 ${owner} - -` (the `group` option goes);
  `append()` and `replace_stream()` set `0600`. Measured today: directory
  `0750 dalhaka:users`, files `0640`; `getent group users` lists no
  supplementary member, so the change removes a dependency on that fact rather
  than closing an open hole — and it changes nothing about the seat, which
  shares the uid. `host-core` asserts the mode in the rendered tmpfiles.
- **No network.** The store is a directory. The units that touch it are named:
  `helm-collect`, `helm-flake-check`, `evidence-rollup`, `evidence-audit` —
  `Type=oneshot` user units with `ConditionUser` = the operator and no
  listener. An eval test in `evidence-eval` asserts, **over those four unit
  names** (not over whatever happens to set `ReadWritePaths`), `Type=oneshot`
  and no `ListenStream`/`ListenDatagram`/socket unit. The non-unit writers
  (`session-start.sh`, `ritual.sh`, `factory-task`, `factory-integrate`,
  `orchestrator-guard.sh`, `hook-guard.py`) are outside any unit assertion and
  are covered by the lint-gate grep instead: no `curl`, `wget`, `urllib`,
  `requests`, `socket` or `http.client` under `pkgs/evidence`, `tools/ledger`,
  `tools/factory` and the two hook scripts; the collector's only sockets are
  loopback reads (ComfyUI on 127.0.0.1:8188). Nothing in this design makes an
  outbound request. Helm's serve unit (DynamicUser) reads `/var/lib/helm`,
  never the store (`grep -n evidence nixosModules/helm.nix` names only the
  collect and flake-check units), so `0700` breaks no reader.
- **Backup.** `/var/lib/evidence` is in `services.proton-backup.paths`
  (`hosts/core/proton-backup.nix:41`), enforced by `checks.core-backup-wiring`;
  restic encrypts client-side, so Proton holds ciphertext only. So every row
  does leave the machine nightly, as ciphertext, under the existing backup
  rule — §7 says the same. `quarantine/` and the cache directory (if SQLite is
  ever adopted, under `/var/cache`) are not backed up.
- **Readers** are the operator's own commands: `evidence bundle`, the Helm
  collector, `tasks.py`, `evidence report`. None prints a row body. A seat
  agent can read the store files directly (above); it finds numbers.
- **Freshness.** `evidence bundle` and a Helm tile print the age of the last
  `store-policy` and `store-backed-up` rows; older than 26 h is `unknown`
  (`warn`), because per CLAUDE.md a switch does not start a newly enabled user
  timer in a logged-in session, and neither timer runs while the operator is
  logged out. `Persistent=true` on both timers covers the missed-window case.

### 3.7 Rebuildability

| stream | primary source | rebuild | class |
|---|---|---|---|
| `checks` | the check run itself (gone) | — | primary, backed up |
| `helm-status` | the collector cycle (gone) | — | primary, backed up |
| `host-metrics` | the sample (gone) | — | primary, backed up |
| `sessions` | the hook event (gone) | — | primary, backed up |
| `incidents` (hand rows) | the orchestrator's record | — | primary |
| `incidents` (auto rows) | the other streams | `evidence derive incidents --since` | derived |
| `runs` start | `run.meta` (unbacked) | the store row is the durable copy | primary |
| `runs` end | `.result` set per run dir | `evidence ingest runs ~/factory/runs` | derived |
| `tasks` | `~/factory/runs/*/*.result` (unbacked) | `evidence ingest results ~/factory/runs` | derived; durable copy |
| `gates` | `docs/reviews` (git, backed up) + `.review.md` (unbacked) | `evidence ingest reviews` | derived |
| `ledger/*` | Claude transcripts, seat sessions, the lane ledger (`ledger.jsonl`, never `results/`), the export | `tools/ledger/factory.py extract*`, `ingest-activity` | derived |
| `broker-lane` | audit logs, lane ledger (unbacked; claim open) | `evidence rollup egress\|lane --since` | derived; durable copy |
| `guard-denials` | the two guard state files (unbacked) | `evidence ingest denials` | derived; durable copy |

`evidence rebuild --derived` deletes and rebuilds every derived file. Acceptance
for the rebuild itself: on a scratch copy of the store, delete `derived/`,
rebuild, sort both trees' rows by key — byte-identical. `quarantine/` is
outside every table above: never rebuilt, never read by a reader, never backed
up, deleted by the operator.

### 3.8 Migration of what exists

| what | rows today | how | result |
|---|---|---|---|
| `checks.jsonl` | 90 | untouched: the rows stay `v: 1` and are audited under the v1 shape (`log_tail` ≤ 4,000 in v1 only); new rows are v2 | as is |
| `helm-status.jsonl` | 21 | untouched | as is |
| `.result` files | 202 in 101 run dirs | `evidence ingest results` (rooted at `~/factory/runs/`) | 202 `tasks` rows; `effort`/`route`/`kind`/`size` `unknown` on 151 (all eight comparison-arm rows among them); `commits` counted from the list (15 declared counts differ); `error_class` from metadata for the 7 failed and the 1 partial; `FACTORY-NOTES` dropped; `checks_parse` per row |
| run dirs without a `.result` | 17 attempts (§9 command) | `evidence ingest runs` | `runs` end rows with `status=killed` where a `.killed-by-*` log exists, else `unknown`; keys listed, no `tasks` row |
| gate reviews | 131 files | a script writes the front matter from the H1 where it parses (104 files: 58 approved, 46 rejected) and `verdict: unknown` on 27 for the orchestrator to fill by hand; `mutants_killed/total` filled where the `N/M` or `N killed` forms exist (19 files), null elsewhere; `review_commit_ts` from the parseable `docs: gate review` commits (65 tonight) | 131 `gates` rows; 23 more from `.review.md` |
| `runs.jsonl` | 0 | shape A declared; nothing to migrate | the next dark-factory run's report lands |
| activity export | 8,832 requests, 8 days | `ingest-activity` | one `activity-day` row per (date, model): at most 8 × 7 |
| Claude workflow transcripts | 89 dirs, 963 agent files | `factory.py extract` per dir (usage fields only) | `factory-runs`, `factory-agents`, `factory-findings` |
| seat sessions | 240 under `~/factory`, 47 interactive | `extract-dsh` (counts only; `role`/`model` null where no `manifest.json`) | `dsh-sessions` |
| broker audit | 296 + 4,636 rows | `rollup egress --since 2026-09-02` | daily rows for two instances |
| lane ledger | 13 rows (`results/` not opened) | `extract-lane` (re-pointed), `rollup lane` | `lane-jobs`, `lane-day` |
| denial records | 2 (in transcripts; no state file exists yet) | one operator-invoked `dsh-openrouter --denials --export-hashed` run that prints state-file rows (subject hashed, reason mapped to a code) for the operator to place in `$DSH_HOME/guard-denials.jsonl`; then `ingest denials` | 2 `guard-denials` rows |
| `claims.toml`, `routing.toml`, the price table | — | untouched | policy inputs |

The migration is one factory task (size M, §5 T6) and is re-runnable: every
ingest is idempotent by key.

## 4. Utilisation

Each use names what it computes, from which streams, and the acceptance that
shows it working. None of them reads a body; none of them changes a policy file
by itself — a report proposes, a commit decides.

**4.1 Routing rows from measured cost and quality.** `evidence report routing`
groups `tasks` ⋈ `gates` ⋈ `ledger/activity-days` by (route, role, kind, size,
model, effort) and prints n, approved fraction at first gate, fix rounds per
landing, median `wall_s`, median input and output tokens, reported cost share
for the (date, model) buckets the group used. A group with n < 5 prints
`insufficient (n=…)` and nothing else; today every openrouter row would print
that (n = 1 to 2 per arm, plus 38 Pro/medium `done` results without a
`kind`/`size`). A row in `routing.toml` changes only by a commit whose body
cites the report line. Acceptance: the report reproduces the model
comparison's per-arm table (Pro 2/2, 0 fix rounds, 351 s; Flash 2/2, 1 fix
round, 901 s) from the migrated store within rounding — the `model:` line is
on every result and the nine arm reviews are in `docs/reviews/`
(`…-mcp-P1pro.md`, `…-mcf2-P1flashb.md`, …), so `model` and the verdict are
real fields, not run-name inference; the `n < 5` refusal is covered by a
fixture. Size S (after T2, T3, T4, T10a).

**4.2 Gate briefs tuned from the mutation-survival record.** `evidence report
gates --survivors` lists, per plan and per touched file class, the mutants that
survived and how often the same class recurs across chains
(`gates.mutants_total − mutants_killed`, joined to `tasks.checks` and the
plan's `acceptance`). The recurring classes become named mutation targets in
the next plan's test spec — the lesson the board already recorded by hand
("every plan assertion must name the mutant that kills it", R3). Acceptance:
for the five chains OG1, RT5, R3, G11, G12 the report's survivor counts equal
a hand count from the review files; the top-3 classes print with n. Size S
(after T3).

**4.3 Retry and relaunch policy from incident classes.** The driver's relaunch
decision becomes a table keyed by `error_class`: `budget-402` → wait for the
`credits restored` incident row then relaunch the same key once;
`provider-error` and `boot-failure` → relaunch once; `killed` → the CR3r
relaunch hint; `unknown-model`, `template-echo`, `no-result-line` → never
relaunch, record `fail`, the orchestrator decides; `timeout` → never. The
table lives in `factory-lib.sh`, unit-tested with synthetic results.
Acceptance: relaunches per class per week print from `runs` ⋈ `tasks`; a
fixture with a `template-echo` result proves no relaunch is issued; the
2026-09-05 sample (7 failed results) classifies to the expected rows. Size S
(after T2, T7).

**4.4 Helm tiles for factory health.** Four tiles from the store, each with
since-when as today: rework ratio (rejected ÷ (approved + rejected), 7 days),
spend per day (reported `cost_usd` from `activity-days`, with "no export since
<date>" when stale), seat deaths per day (`tasks.error_class ≠ none`), time in
gate (median minutes seat-finish → review commit, 7 days). Thresholds: rework
> 0.5 warn; deaths ≥ 3/day warn; export older than 7 days warn. Acceptance:
`helm-unit` fixtures for each tile's three verdicts; on the migrated store the
tiles print today's values: rework = rejected ÷ (approved + rejected) over
rows with a parsed verdict = 46 / 104 = 0.44 tonight (the title parse, §9; the
27 `unknown` rows are excluded and the tile prints "27 unparsed"); time in
gate 14 min. Size S (after T2, T3, T4, T10a).

**4.5 The derived task graph gains duration and cost estimates per size.**
`tasks.py brief` prints, per (kind, size), median and p90 `wall_s` and median
output tokens from `tasks`, and the next wave's expected seat time. (kind,
size) come from the `route:` line and nowhere else (§3.3). Today the store
would say: code/S n = 32, code/XS n = 3, code/M n = 2, docs/S n = 2, docs/XS
n = 1 (the results with a `route:` line at the first sample; 151 rows are
`unknown/unknown` and print as one line). Acceptance: the brief line
appears only when n ≥ 5 for that (kind, size); a fixture proves the p90; the
hook's 1,500-char brief budget is not exceeded. Size XS (after T2).

**4.6 Comparisons at n ≥ 5 without bespoke runs.** `evidence report compare
--by effort|model --kind code --size S` prints the per-arm table the two
comparison docs assembled by hand — approved, fix rounds, cost, wall, gate
tokens, output tokens — from routine runs, with n per arm, and refuses a
conclusion line below n = 5. The effort comparison cannot be reproduced by
`--by effort` from the migrated store: none of the four arm results (`em/X1med`,
`em/X2med`, `ex/X1xhigh`, `ex/X2xhigh`) carries an `effort:` line, both arms
are the same model, and the arm label lives only in the run name. A backfill
that stamps `effort:` from the run name is refused: it would present a
hand-written setting as the wire value, the confusion §2.11 exists to end.
Acceptance, in three parts: `--by run` reproduces the effort comparison's
per-arm rows (medium 2/2, 254 s, 9,042 output tokens; xhigh 2/2, 423 s,
16,031) from the `em`/`ex` rows exactly; `--by effort` groups a synthetic
fixture of two arms correctly and refuses at n = 2; and, forward-looking, the
first five routine results per arm that carry `effort:` group under it with
no bespoke run. The plan-writing rubric scores stay a human judgement outside
the store. Size S (after T2, T3, T4, T10a).

**4.7 Capacity signals for the ComfyUI worlds.** From `host-metrics.gpu` and
`.comfyui`: VRAM headroom p10 over 24 h, queue depth p90 (`queue_remaining`
from `GET /prompt`), and — once a world's model class is named in the sample
(a `model_class` enum the worlds plan can supply through a world label) —
VRAM used per model class. Two named gaps. (1) There is no error fraction and
no OOM rate: the endpoints that report per-job status carry the prompt graph
and are not fetched (§1 row 33); OOMs are hand-recorded `comfyui-oom` incident
rows until ComfyUI runs under a unit and a fixed-pattern journal count exists.
(2) At one sample per 300 s the series supports headroom p10 and post-hoc
counts, not the ramp before an OOM (three points in 15 minutes); T5's own
size fixture forbids the cadence that would show it. If the ramp is wanted,
the worlds plan names an event-triggered sample (a `queue_remaining`
transition, or the unit's journal pattern) and sets the size budget against
that; it is not in this design. Acceptance: the drill in §2.8 (the VRAM and
queue samples around the hand-recorded OOM row); the gpu tile gains a
"headroom p10 24 h" detail. Size S (after T5).

**4.8 Backup verification of the stores.** Nightly, after the local restic run,
the collector runs `restic ls latest --json /var/lib/evidence`, compares the
listed files with the live stream files, and records the check
`store-backed-up` (ok when every live file is present and the snapshot is
< 26 h old). `host-metrics.backups` carries the snapshot age every cycle.
Acceptance: the row exists every night; a fixture that removes the store from
the path list turns it `fail`; the Proton parity tile keeps its own rule. Size
XS (after T5).

## 5. Proposed tasks

Ordered by payoff per effort. "Depends on" is prose; nothing here is a typed
plan heading, and the task graph does not read this file.

Sizes are set against landed comparables in
`docs/superpowers/plans/2026-09-05-evidence-store.md` (E1, the whole store, was
M; E7, the integrator recording every check, was S).

| # | title | size | depends on | acceptance | what makes it falsifiable |
|---|---|---|---|---|---|
| T1 | The fence: `streams.py` allowlist (string classes, map key patterns, per-stream version map, `factory-run` shapes A and B, `check` v1/v2), writer-side validation in `append()`, `validate()` + `replace_stream()` for the ledger merge, forbidden names, secret shapes; every writer routed through the library (`collect.py`, `tools/ledger/factory.py`); the lint-gate grep and the direct-open test | M | nothing | `evidence-unit` gains `test_streams_policy.py` (valid + invalid fixtures per kind, the declared-field walk); `evidence record` refuses an undeclared kind, field, class, key; `collect.py` and `factory.py` have no store opener of their own; shape A accepts the recorder's literal from `dark-factory.js:658–670` | mutations (a)–(i) of §3.5, each red before the change |
| T2 | `tasks` stream: `evidence ingest result` (rooted), `error_class` in the driver, `checks_parse`, one line in `factory-task` | S | T1 | 202 rows from the migration; the 7 failed results classify as listed in §2.1; a synthetic `status=done` with an empty commit list is `template-echo`; `ingest result /etc/passwd` exits non-zero | mutation: drop the exit-124 rule → the timeout fixture is `none`; drop the 4,000-byte bound → a 1 MB fake log makes the test time out; the hostile-`.result` fixture (§3.5 g) |
| T3 | `gates` stream: review front matter (lint + migration script over 131 tracked files, 27 hand-filled verdicts), `ingest reviews`, `.review.md` verdicts, commit times, one line in `factory-integrate` | M | T1 | 131 + 23 rows; 104 parsed automatically (58/46); the lint refuses a new review without the block or with a verdict outside `approved`/`rejected`/`unknown`; `time in gate` prints 14 min on today's data | mutation: a review with `verdict: rework` passes the lint → test fails; remove the H1 → `REVIEW_RE` test fails |
| T4 | `ledger ingest-activity`: extend `_load_activity` (`factory.py:453`, `schema.md` §rollup) to the full per-bucket record and persist it; the rollup timer wiring for `extract*` | S | T1 | `activity-days` rows for 8 days; `tokens_reasoning` total 6,340,776 on the current export; `providers` is a count; `ingest-activity` refuses a path outside `~/strategy/ledger/` | mutation: drop `tokens_reasoning` from the extractor → the 6,340,776 fixture fails; sum `provider_name` as a string list → the class fence fails |
| T5 | `host-metrics` from the collector (`record_metrics` keyword signature, `backups`, `broker` liveness), the two ComfyUI probes (`/system_stats`, `GET /prompt` — first step: confirm both shapes against the packaged ComfyUI), monthly files and the `read()` glob | M | T1 | one row per cycle on core; the ComfyUI block is null when the process is down; row size ≤ 1 KB; no probe response, exception text or tile detail contains a probe body | mutation: sample every 60 s → the size fixture fails; pass `status` to `record_metrics` → the name fence fails (§3.5 h); a fixture `/history`-shaped response with a prompt, if any code path ever fetches it, appears in no output |
| T6 | Migration: `ingest results`, `ingest runs`, `rebuild --derived`, backfill on core | M | T2, T3, T4 | §3.8's counts; `rebuild` is byte-identical on a scratch copy | mutation: skip the sort in `rebuild` → the identity test fails |
| T7 | `incidents` stream (no `note`; `board_commit`) and `derive incidents` | S | T2, T5 | today's record yields ≥ 8 auto rows (7 seat deaths + 1 check-red) and hand rows for the ritual incident, the reboot and the fabricated commits, each pointing at a board commit | mutation: drop the boot-id rule → the reboot fixture yields no row; add a `note` field → the name fence fails |
| T8 | `broker-lane` rollups (prefix-mapped `reason_class`), `evidence-rollup.timer` (`Persistent=true`), audit-age incident | S | T1 | daily rows back to 2026-09-02 for both instances; `audit_age_s` on core; an `audit-stale` row for a fixture with an active instance and a 2-day-old file | mutation: write `host` into the row → the policy test fails; a fixture reason `host/sni mismatch: sni=example.org host=…` → the row carries `host-sni-mismatch` and no hostname; drop the `active` guard → a parked instance raises a false incident |
| T9 | Access: `0700`/`0600`, `quarantine/` tmpfiles line, the by-name oneshot/no-listener eval assertion, the seat-`ReadWritePaths` assertion, the `store-backed-up` check and `quarantine/` exclusion | S | T5 | `host-core` asserts the tmpfiles lines; `evidence-eval` asserts the four units by name and that no seat unit lists the store path writable; the nightly check row exists | mutation: add `ListenStream` to a fixture unit → the eval test fails; add the store to a seat `ReadWritePaths` fixture → fails |
| T10a | The reader/join layer: `evidence.read()` over derived streams and monthly globs, `tasks ⋈ gates ⋈ activity-days` by (run_id, key) and (date, model), the n-gate helper | S | T6 | the join yields one row per `.result` with its gate verdict where a review exists; the n-gate refuses n < 5 | mutation: join on key alone → the fixture with the same key in two runs fails |
| T10b | `evidence report` surfaces: routing, compare (`--by run\|effort\|model`), gates --survivors, time-in-gate, churn | M | T10a | reproduces the model table by model and the effort table by run; the 14-min figure; refuses n < 5 | mutation: lower the n gate to 2 → the refusal fixture fails |
| T11 | Helm factory-health tiles (rework as rejected ÷ parsed, spend, deaths, time in gate) plus the `store-policy`/`store-backed-up` freshness tile | S | T10a | four tiles with since-when; `helm-unit` fixtures for each verdict; a 27-h-old `store-policy` row prints `warn` | mutation: threshold 0.5 → 0.9 on rework → the warn fixture fails; freshness 26 h → 100 h → the stale fixture fails |
| T12 | `tasks.py brief` duration and cost lines per (kind, size) | XS | T6 | lines print only at n ≥ 5; brief budget kept | mutation: print at n ≥ 1 → the fixture with n = 3 fails |
| T13 | `guard-denials`: `reason_code` tables and state files in both guards (`hook-guard.py _deny`, `orchestrator-guard.sh deny`), `ingest denials`, `dsh-openrouter --denials --export-hashed` for the two historical records | S | T1 | a live `sudo` probe on each guard appears as a row within the minute; a fixture denial with a path in its reason yields a row that contains neither the path nor the string; subjects stored as sha256 + length only | mutation: write the reason string → the class fence fails (no class admits it); store the raw subject → the name fence fails |
| T14 | `sessions`: one line in `session-start.sh` and `ritual.sh` | XS | T1 | one row per hook fire on core; a missing `evidence` never blocks the hook (bats) | mutation: remove the guard → the bats case with `SESSION_START_EVIDENCE=/nonexistent` fails |
| T15 | Relaunch policy table in the driver | S | T2, T7 | the table in §4.3; relaunches per class print | mutation: relaunch on `template-echo` → the fixture fails |
| T16 | `runs` shape B start/end rows from `factory-wave` (after CR3r's `run.meta`); the recorder's shape A row confirmed | XS | CR3r landed, T1 | one start and one end row per seat run on core; the recorder's row present after the next dark-factory run | mutation: write `pid: 0` → the reader treats the run as dead and the fixture fails |
| T17 | `evidence audit-store` with quarantine (row excision under flock, `quarantine/` file, `store-policy-violation` incident with the snapshot id, `store-policy` check row), `evidence-audit.timer` at 23:40 (`Persistent=true`), the 26-h freshness rule in `evidence bundle` | S | T1, T7 | on the live store: 0 violations, `store-policy ok`; on a scratch store with one `>>` row: 1 violation, the row in `quarantine/`, the stream valid again, an incident row, `store-policy fail`; the timer fires before `restic-backup` (unit ordering asserted) | mutation (§3.5 j); move the timer to 00:10 → the ordering test fails; skip the rewrite → the "stream valid again" assertion fails |
| T18 | `checks` v2: `log_tail` → `log_tail_sha256` + `log_tail_len` + `fail_class`, `--log-tail-file` bound to the build-log roots, `src` enum, `--run` | S | T1 | new rows carry the three fields and no `log_tail`; the v1 row still audits clean; `record-check --log-tail-file /etc/passwd` exits 2 with nothing written | mutation: drop the root check → the `/etc/passwd` fixture writes a row and the test fails |

T1 first: it is the whole critical path, and at M it is the single largest
task here. T17 and T18 follow it directly. T2–T5 are independent of each other
and can run as one wave after T1. Ordering rule from §3.3: T1 (shape A
declared) lands before any dark-factory run, or that run's report is refused.
The `touches` overlap to watch: T2 and T15 both edit `factory-lib.sh`; T5 and
T11 both edit `collect.py`; T14 edits the two hook scripts CR-series tasks also
edit; T13 edits `hook-guard.py`, which the lanes runbook tests own.

## 6. Open questions for the operator

1. **Store mode.** `0700` operator-only (recommended: no other uid needs to
   read it, and it removes the dependence on the `users` group being empty;
   note it changes nothing for the seat, which shares the operator's uid and
   reads the store either way — §3.6) or keep `0750 users`.
2. **`checks.log_tail` — decided in this revision, no longer open.** The field
   is replaced by a hash, a length and a `fail_class` enum, and the
   `--log-tail-file` argument is bound to the build-log roots (§3.3, T18).
   The reason: `evidence.py:397` reads any path the caller names into a
   durable, backed-up store, and a failing lint's tail is source lines by
   construction. The failing check's last lines stay where they are written
   (the unit's work dir, the seat's `integrate.log`); the next session reads
   them there, not from the store. The operator can reopen this by
   commit.
3. **The orchestrator's own transcripts.** May the ledger's usage-only
   extraction (`extract` reads `message.usage` numbers, timestamps and tool
   names, never message bodies) run over this project's Claude Code session
   files, so context consumption per landing becomes a number? Recommended:
   yes, numbers only, the same code path that already exists for
   `agent-*.jsonl`; the policy check applies to what it writes.
4. **The activity export.** Keep the weekly manual download (recommended for
   this round) or add a broker-audited `GET /api/v1/generation?id=` per request
   later — that is one outbound request per generation and a new egress
   pattern, so it is a separate decision.
5. **Automatic relaunch.** Which classes may relaunch without the orchestrator
   (recommended: `budget-402` after the credits row, `provider-error` and
   `boot-failure` once each; never the rest).
6. **`~/factory/runs` and the lane ledger.** Leave the run tree unbacked and
   let the derived rows be the durable copy (recommended: it is ~150 MB/day of
   transcripts; the store keeps every number from it). For the lane: add
   **only** `/var/lib/lanes/*/ledger.jsonl` to the restic paths, or declare it
   disposable because `lane-day`/`lane-jobs` are the durable copy
   (recommended). The first draft proposed the whole `/var/lib/lanes` tree; it
   is withdrawn — `jobs/` and `results/` hold prompts, responses and
   working-tree diffs (§1 row 25), and ciphertext or not, that is the content
   the rest of this document exists to keep on the machine.
7. **The broker audit logs, in their own terms.** `/var/lib/egress-broker/*/audit.jsonl`
   holds the machine's verbatim egress paths (527 with query strings), client
   addresses, hostnames and SNI values. Should those files leave the machine
   as restic ciphertext under the existing backup rule — yes or no? The
   derived `egress-day` rows are already the durable numbers (§3.7). Not
   recommended; a separate decision from Q6.

## 7. What this design refuses

- **Content analytics.** No stream holds prompt, response, reasoning,
  transcript, file, image or basket bytes, and no reader opens them. The one
  "quality" signal is the gate verdict and its mutation counts, which a
  reviewer already wrote as numbers.
- **Transcript mining.** `session.jsonl.zstd`, `wave-group-*.log`,
  `*.launch.log`, `*.review.log` and the Claude session bodies are read by
  exactly two existing extractors (`factory-usage.py`, `tools/ledger/factory.py
  extract`/`extract-dsh`) that lift numbers, and by nothing new. Lane
  `results/*.json` are read by nothing (`extract-lane` is re-pointed at the
  ledger). `dsh-denials.py`, which walks every seat transcript, runs in no
  timer and is not a writer. The `error_class` pattern list runs inside the
  driver and emits an enum. The ComfyUI probes fetch no endpoint whose body
  can carry a prompt.
- **Anything leaving the machine as a metric.** Nothing is sent to any
  service. The store leaves the machine only inside the nightly restic
  ciphertext, under the existing backup rule (§3.6, `core-backup-wiring`);
  `quarantine/` does not. The store is `local-only` in the sense of the
  2026-09-03 classification: operational fingerprint. If a rollup is ever
  handed to a remote model, that is a decision under invariant 5, not a
  feature of this store.
- **A daemon.** No database server, no metrics agent, no dashboard service
  beyond the Helm page that exists. The only new units are two oneshot user
  timers (`evidence-audit`, `evidence-rollup`).
- **A model in the loop.** Every writer, ingest, rollup and report is a
  deterministic script with tests (data-and-models spec §2.1). Summaries and
  classifications by a model are Tier B work outside this design.
- **Automatic policy changes.** `routing.toml`, the relaunch table and the gate
  briefs change by commit; the store only shows the numbers with their n.
- **Hostnames, paths and addresses in the store.** `top_denied` is a forbidden
  name and stays on the Helm page; the broker's `client`, `host`, `sni` and
  `path` never enter a row and its two hostname-carrying reasons are cut at
  the prefix; the guards' `subject` is hashed at the source and their reason
  strings are replaced by codes; the id class admits neither `/` nor `@`, so
  a path or an address fits no field that is not a declared, rooted path.
- **Free text, by whatever name.** No `note`, no `title`, no `reason` string,
  no log tail. A sentence written by a model belongs in a commit on the board,
  where a diff shows it; the store holds the commit id.

## 8. Risks

- The `error_class` patterns are a guess until the seven failed results and
  the seventeen attempts without a result are classified on real tails; T2's acceptance is
  that classification, done by the driver, not by a person reading logs.
- Front matter on 128 existing reviews is a docs migration in the repo; 27
  files need a hand-filled verdict and most need hand-filled mutation counts.
  The store accepts null and says so; the report prints n accordingly.
- `helm-collect` gains work per cycle (a `restic ls` nightly, two loopback
  requests, a stat per audit file). The tile decorator already degrades a
  failing probe to `unknown`; the sample row does the same with nulls.
- A derived stream is only as complete as its source: `.result` files exist
  for 202 of the 219 attempts the §9 command finds; the `runs` end row carries
  the rest as `killed`/`unknown` and the incident row says so.
- The fences bind writers, not a uid. Inside the seat unit the store is
  read-only by sandbox; outside it, a process of the operator's uid can write
  a row past every fence, and the audit catches it up to twenty minutes before
  the snapshot — a row written between 23:40 and 00:00 is in a snapshot before
  it is quarantined, and the incident row's snapshot id is the operator's
  cue to `restic forget`. The window is a number, not a hope; it can be
  narrowed by moving the audit later at the cost of the derived rows' cutoff.
- The audit self-attests. A stopped `evidence-audit.timer` looks like a clean
  store to anyone who does not check the row's age; the freshness rule (26 h)
  is the whole defence, and it lives in the reader.
- Two ComfyUI endpoint shapes (`/system_stats`, `GET /prompt`) are stated from
  the upstream server code and not verified against the packaged version on
  this machine (its source is not under `~/comfyui`); T5's first step is that
  check, and if `GET /prompt` does not carry `queue_remaining` the queue depth
  is dropped rather than fetched from `/queue`.

## 9. How the numbers were taken (2026-09-05, ~22:00 CDT unless the store's own timestamps say otherwise)

- Store: `wc -l` and a stdlib JSON pass over `/var/lib/evidence/*.jsonl` (field
  presence, `src`, `name`, `ok`, `reason`, tile verdicts); `ls -la` for modes;
  `getent group`.
- Results: `grep -c`/`grep -l` over `~/factory/runs/*/*.result` for the
  `FACTORY-*` header lines and the `key: value` block; `awk` sums of `wall_s`;
  the `usage:` line's numbers with the model id masked; `ls`/`find` counts for
  logs, markers, `dsh-home` dirs and sessions. No log body was opened.
- Reviews: `head -1` of each `docs/reviews/*opus-review*.md` matched against
  `tasks.py`'s `REVIEW_RE`; `grep -l` for mutation phrasings and MAJOR/MINOR
  markers.
- Git: `git log --since=2026-09-04 --format=%ct%x09%s`, subject regexes for
  `integrate`, `docs: board`, `docs: gate review`, `(test: …)`; latencies from
  those times and `.result` mtimes.
- Activity export: a stdlib CSV pass summing `cost_total`, token columns and
  `finish_reason_normalized` per `created_at` date and `model_permaslug`; the
  `user`, `api_key_name`, `app_name` and `generation_id` columns were not read.
- Broker and lane: a stdlib JSON pass over the two `audit.jsonl` files and
  `ledger.jsonl` (verdict, reason prefix, key names, byte sums, distinct
  counts); no host or path value was printed.
- Host: `nvidia-smi --query-gpu`, `systemctl --user list-timers`,
  `systemctl list-units --failed`, `journalctl --disk-usage`, `--list-boots`;
  `wc`/`grep -c` on `comfyui-krea2.log` for two fixed phrases.
- Timing: 105,000 synthetic rows of the `host-metrics` shape written and parsed
  in the scratchpad with the devShell's Python (no real data).
- Re-derivations replacing inventory citations (revision 2, ~23:30 CDT). The
  six inventories are not in the repo (`docs/superpowers/` holds `plans/` and
  `specs/` only), so every load-bearing number from them is re-derived by one
  of these, or dropped:
  - attempts without a result (17):
    `cd ~/factory/runs && for d in */; do for l in "$d"*.log "$d"*.log.killed-by-*; do [ -e "$l" ] || continue; b=$(basename "$l"); case "$b" in *.launch.log|*.review.log|*.wave.log|integrate.log|wave-group-*) continue;; esac; k=${b%%.*}; [ -e "$d$k.result" ] || echo "$d$k"; done; done | sort -u | wc -l`
    (file names only; nothing is opened);
  - results, and the `route:`/`effort:`/`plan:` coverage (202; 51; 51; 0):
    `ls ~/factory/runs/*/*.result | wc -l`; `grep -lE '^route:' … | wc -l`,
    the same for `^effort:` and `^plan:`;
  - review verdicts (131 files; 104 parse; 58/46):
    `for f in docs/reviews/*opus-review*.md; do head -1 "$f"; done | grep -oE '— (APPROVED|REJECTED)' | sort | uniq -c`;
  - git counts since 09-04 (65 gate-review commits, 55 `integrate … into integ/`, 48 `docs: board` tonight; the first sample's 62/59/45 were taken ~5 h earlier):
    `git log --since=2026-09-04 --format=%s | grep -cE '^docs: gate review'`, and the same with `'integrate .* into integ/'` and `'^docs: board'`;
  - the 67 / 44 / 11 approved-family / rejected / rework split of the first
    draft had no re-derivation (the title parse knows two verdict words, and
    67 + 44 + 11 ≠ 128) and is withdrawn.
- Everything else is quoted from the named repo files; where nothing measured
  a thing it is marked **unmeasured** in the text.

## 10. Revision 2 — what changed, and what was rejected

Two critiques (one on user-data paths and invariants, one on achievability of
the acceptances against the data and tooling as they exist) were checked
against the code line by line; every cited line held. Folded:

- **Every writer through `append()`** (§3.4): `collect.py:738` and
  `factory.py:74/80` were outside the fence, as was the proposed
  `record_metrics(cfg, status, now)`; now one validating function, a lint
  grep, a direct-open test, and a keyword-only `record_metrics`.
- **The uid truth** (§3.5, §3.6): seat agents run as the operator; the seat
  unit's `ProtectSystem=strict` keeps the store read-only inside it (asserted
  in eval); outside it only the audit catches a row, so the audit becomes the
  enforcement of record with quarantine, an incident row naming the snapshot,
  a 23:40 slot ahead of the 00:00 restic run, `Persistent=true`, and a 26-h
  freshness rule.
- **`log_tail`** (§3.3, T18, Q2 closed): hash + length + `fail_class`;
  `--log-tail-file` rooted; `/etc/passwd` refused.
- **`guard-denials`** (§3.3, T13): `reason_code` enum and subject hash written
  by each guard to its own state file; `dsh-denials.py`'s transcript walk out
  of every timer.
- **String classes** (§3.5): the id class loses `/` and `@`; `model-id`,
  `key`, `rooted path` per field; no free-text class exists; `incidents.note`
  and `factory-findings.title` gone (`board_commit`, `title_sha256`).
- **Name fence** (§3.5): exact match on a normalised name at every depth,
  including map keys; the list extended (`sni`, `client`, `top_denied`,
  `file_path`, `cwd`, `basket`, `title`, …); the declared-field walk test.
- **Map keys and list elements** (§3.5 point 3): patterns and caps;
  `tasks.checks` drops the map and records `checks_parse: refused`.
- **Q6** rescoped to `ledger.jsonl`; the broker audit is Q7 in its own terms.
- **`extract-lane`** re-pointed at `ledger.jsonl`; `results/` opened by nothing.
- **ComfyUI**: only `/system_stats` and `GET /prompt`; history counts
  unmeasured; the 300-s ramp gap named (§2.8, §4.7).
- **`runs`**: the recorder's SCHEMA.md v1 literal declared as shape A, the
  seat driver's rows as shape B, and the ordering rule (T1 before any
  dark-factory run).
- **Verdicts**: `rework` dropped; rework ratio = rejected ÷ parsed = 46/104;
  the 67/44/11 split withdrawn; 131 files / 104 parse / 27 by hand.
- **Effort comparison** (§2.11, §4.6): reproduced `--by run`; `--by effort`
  gets a synthetic fixture and a forward-looking clause.
- **T4** rewritten around `_load_activity` (`factory.py:453`) with a mutation
  that bites (`tokens_reasoning`).
- **Sizes**: T1, T3, T5 to M; T10 split into T10a/T10b; T17, T18 added; T4,
  T9, T13 to S.
- **`v` per stream**, the `gates` runtime writer named, §2.5 split into an
  acceptance and an expectation, §2.9's "11 paths" replaced by the check
  name, the secret-shape list extended with the age/JWT shapes and demoted
  to a backstop, the SQLite trigger made a decision by commit, every ingest
  rooted, §7's "nothing leaves" corrected, inventory numbers replaced by
  §9 commands.

Rejected, or taken differently, with the reason:

- `/history?max_items=0` for the counts: ComfyUI's `get_history` with
  `max_items=0` returns an empty map, and `/queue`'s items embed the prompt
  graph; neither is fetched, and the counts are declared unmeasured instead.
- "The orchestrator guard shells out to `evidence record`": a guard must never
  block on the store or on the devShell; the state file validated at ingest
  (the critique's other option) is taken.
- "Move the offending *file* to `quarantine/`": rows are excised and the
  stream rewritten, so the valid rows stay readable; the file-level move
  would blind every reader to a stream for a bad row.
- A one-time backfill stamping `effort:` on the em/ex/mcp/mcf2 results from
  the runs' settings: it would record a hand-written setting as the wire
  value, which is the confusion §2.11 records (M2 void); `--by run` gives the
  same table without the claim.
- "Commit the six inventories under `docs/reviews/`": the designer does not
  hold them as files; each load-bearing number is replaced by a command or
  withdrawn (§9).
- `label` on the forbidden-name list: `factory-*.label` is the driver's role
  label (`recorder`, `implementer`), an id, not content; `title`, `summary`,
  `slug`, `snippet`, `excerpt` were added instead.
