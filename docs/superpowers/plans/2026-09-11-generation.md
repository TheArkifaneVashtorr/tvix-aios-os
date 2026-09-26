# Plan 2026-09-11 — Generation (GN): the loop closes, the worlds reach core, media comes home

**Charter:** `docs/concepts/2026-09-09a-redesign-charter.md` — §2 row Generation (`:52`: `~/flakes/media`, the prompt mutator; `generation`, Sonnet gate; `GN`; answers 14–17), §5, §6 increment 3 (`:175-180`: "comfy-worlds sub-projects 2 and 3, the on-demand units and Caddy on core, the rules mutator, media absorbed (`GN`)"), `:65` (siblings retire once absorbed), `:67-68` (Phase 5 local weights deferred).
**Decisions:** `docs/decisions/2026-09-09-redesign-answers.md` — 14c, 15a, 16b, 17c, 18b, 20b, 35b, 41a, 43b, 44, 48a, 63a, 70b; §4 (OpenRouter only), §5–§6 (the drafter) — see `## Decisions relied on`.
**Context block:** `docs/context/generation.md` §1–§6. Its §5 questions: 1 answered by `1ae7328` (the GN row names this file); 2, 3, 6 asked below (Q3, Q2, Q1); 4 and 5 answered as the block's own defaults (rules only; the feed's state at the design's reserved `worlds/<world>/feed.sqlite`); 7 and 8 carried as unverified assumptions.
**Program plan:** `docs/superpowers/plans/2026-09-09-program.md` — `## Global Constraints` G1–G12 quoted verbatim below (`factory-brief` reads that section from this file).
**Author:** Fable, batch-plan fill pass, 2026-09-11 (outline pass and cross-plan audit before it); revision 1 on 2026-09-14 against `docs/reviews/plan-judgements/2026-09-12-batch-generation.md` (at `662e87f`); revision 2 the same day against `…/2026-09-14-batch-generation.md`, its 26 errata re-measured at `4068f86` (nixos-agent-env) and `1618638` (media), ledger `generation.errata.md` beside this file. **Status:** draft — full task bodies; lands under `docs/superpowers/plans/` only by the operator's act.
**Repos:** a section marked `**repo:** media` lands in `~/flakes/media` (`docs/ledger/repos.toml:11-12`, no `ledger = true`) under that flake's own checks; every such section — fix rounds included — carries the field itself (a fix round does not inherit it: the SD11b/c lesson). Its `touches` are relative to that workspace. Sections without the field land here.

## Operator questions

Three questions (the rubric's cap), numbered 1–3 here; each is bounded, carries a recommendation, and says what changes in which task if the answer differs. Silence means the recommendation. The fill's Q3 (Caddy's LAN face) is Assumption 20 and, because it is a live conflict between two decisions of record and the charter's own increment order, it is also question 3's option (c) below; the fill's Q4 is question 3.

1. **Absorption order** (block §5 Q6; charter `:179-180` names "media absorbed" in this increment). **(a)** last — GN11/GN12 close the plan after the loop, the wiring and the first switch's drill; **(b)** first — the subtree before any loop work, every later task touching `media/…` here; **(c)** not this increment — GN11–GN12 to increment 4 beside the other siblings (charter `:189-191`, `PL`). **Recommendation: (a):** the loop's tasks run under media's own 21 checks; 35b gives each absorption its own gate and switch, which belongs at a plan's end; (b) re-drafts every `touches` line and blocks wave 1 on Platform; (c) drops the one deliverable the charter names for this increment. Drafted on (a). (b) is a re-draft of every `touches` line; (c) drops GN11–GN12 and Assumption 21's landing act, nothing else (GN10's input stays).
2. **The upstream probe's egress** (block §5 Q3: the design's carve-out at `design:252-255` cites a decision that says the opposite, `2026-09-02-invariants-bind-agents-not-operator-apps.md:17-18`). **(a)** broker it — GN7 as typed, the instance and allowlist in GN10, `refresh.enable = true`; **(b)** record the carve-out — GN7 becomes a Knowledge docs task (a dated `docs/decisions/` file), GN10 enables the timer with direct egress as WH1 typed it; **(c)** defer — `refresh.enable = false`, GN7 dropped, the timer uninstalled as today. **Recommendation: (a):** invariant 3 as the standing decision reads it, and the probe's hosts are six read-only public names — `grep -o 'https://[a-z.]*' ~/flakes/media/pkgs/comfy-upstream-probe/probe.py | sort -u` prints seven lines, `https://api.github.com`, `https://download.nvidia.com`, `https://github.com`, `https://pypi`, `https://pypi.org`, `https://raw.githubusercontent.com`, `https://www.nvidia.com` (re-run 2026-09-14); `https://pypi` is the `re.match(r"https://pypi\.org/…")` literals at `probe.py:318` and `:323`, not a fetched host, so the reduction `| sed 's|https://||' | grep -v '^pypi$'` yields the six GN10 pins — a small allowlist, not a new lane. Drafted on (a). (b) re-kinds GN7 to `docs` in another subsystem's directory and GN10 enables the timer without the instance; (c) removes GN7 and GN10's `refresh` stanza.
3. **WH1 and WH2, and WH1's Caddy** (block §5 Q2: both typed at `~/flakes/media/docs/superpowers/plans/2026-09-05-comfy-worlds.md:979,1040` with headings `HEADING_RE` cannot parse, invisible to every queue). **(a)** supersede — GN10 carries WH1's content under the grammar (the stanza is inlined there) with `lan.enable = false` (Assumption 20); WH2's `media-refresh` tile touches Helm-owned `pkgs/helm/collect.py` and an Evidence-owned `SCHEMA.md` row, so it is Helm's to type — the Helm draft does not carry it (Assumption 23), so WH2 is deferred, not lost: GN11's plan-status note names it; **(b)** re-type them here as `WH1`/`WH2` — a non-reserved prefix inside a GN plan, which G7's guard allows and the board renders as foreign; (b) adds two sections, WH2 with `**areas:** helm, evidence`; **(c)** WH1 as typed, Caddy on — `lan.enable = true`, 443 on `eno1`, `tls internal`, the basic-auth files: 14c ("Caddy fronts the worlds"), 16b ("host-level Caddy wired into `core`") and charter `:179` read literally, against charter `:186-188`, which places "LAN access with per-site auth and the amended brief §10 and loopback assertion" in increment 4 under `IS`; the module renders Caddy only under `lan.enable` (Assumption 9), so there is no "Caddy without the LAN face" to ship. **Recommendation: (a):** the charter's increment order is the later, more specific ruling, and nothing in sub-projects 2/3 needs the face. (c) makes GN10 a cross-area task with `IS` and `KN` (the brief §10 amendment, the loopback assertion), flips GN10 term 3's assertion to `lan.enable == true`, and the drill runs with `COMFY_LAN=on` (GN9). Drafted on (a).

## Charter-to-task map

| Charter / decision | Tasks |
|---|---|
| Sub-project 2 — job queue, per-world index, feed app with like / regenerate / edit prompt (`design:8-10`, `:319-323`; 15a) | GN1 (index), GN2 (queue), GN3 (feed), GN4 (verbs) |
| Sub-project 3 — prompt mutation from likes (`design:323-325`), rules form (17c) | GN5 (grammar), GN6 (loop) |
| The feed as "the component Helm reaches" (14c), "Helm links or embeds" (15a) | GN3/GN4 provide the loopback URL, `/healthz` and the view; Helm embeds later (`## Cross-plan`) |
| Engagement — opens, dwell, likes per day as counts, never content (18b) | GN8 — the feed posts counts to Helm's `/v1/engage` (the Helm draft assigns that POST to GN, `drafts-r2/2026-09-11-helm.md:100`); the stream row is Evidence's writer's (Assumption 22) |
| Invariant 3 for the probe (block Q3; question 2) | GN7, with the host side in GN10 |
| The runbook and the falsifiable drill (70b) | GN9; `## Operator` |
| "The on-demand units and Caddy on core" (16b; charter `:179`) | GN10 — units on; the Caddy half ships only under question 3(c) (Assumption 20: the module renders Caddy only with the LAN face, which charter `:186-188` gives to increment 4) |
| "Media absorbed" (charter `:179-180`, `:65`; 35b, 41a, 43b, 44, 48a) | GN11 (subtree, input retired, ledgers), GN12 (outputs folded on `nixpkgs-host`) |
| Every path this plan creates here is owned (block §1; `subsystems-manifest`) | GN10's files fall under Platform's `hosts/core/*` and `flake.nix`; GN11 adds `media/*` to the GN row |
| Phase 5 local weights, the model mutator (17c; charter `:67-68`) | none — `## Not in this plan` |

## Decisions relied on

- **14c** Caddy as designed stays in the module; the feed is the component Helm reaches (GN3). **15a** sub-projects 2/3 as specified; W6c landed first (`1618638`). **16b** on-demand units plus host-level Caddy into `core`, no specialisation (GN10; the parked round-2 wiring plan stays parked). **17c** rules now (GN5, GN6); the model phase is not here. **18b** counts, never content (GN8). **20b** LAN now — placed by the charter in increment 4 under `IS` (Assumption 20).
- **35b, 41a, 43b, 44, 48a** one repo; each sibling absorbed with its own gate and switch; landed keys frozen as history; absorbed code on `nixpkgs-host`; a true subtree merge, every cited hash reachable (GN11, GN12, Assumption 21).
- **63a / G7** `GN` reserved; the GN row's `plans` names this file (`1ae7328`), so `GN` keys here pass, and `repo: media` sections meet no guard (media has no `docs/ledger/`). **7a / G9** GN10–GN12 declare `**areas:**`; no tracked path here derives `generation` (block §3). **70b** one composed drill; `## Operator`.
- **§4 (OpenRouter only)** no task here makes a model call (a rules mutator, a model-free probe, a file-serving feed); the deferred model phase is local inference, not a lane. **§5–§6** no task depends on which model drafts.

## Assumptions

Measured 2026-09-10 by the context block unless marked; re-run at commit time (G11). Anchors: nixos-agent-env `1ae7328`/`e535e53` era (the fill pass read `21f6a6a`; revision 1 re-measured at `662e87f`, revision 2 at `4068f86`, both 2026-09-14), media `1618638`. Assumptions 20–23 are the revisions': one demoted question and three measured facts the tasks lean on.

1. **Media HEAD is W6c.** `git -C ~/flakes/media log --oneline -1` → `1618638 integrate W6c into integ/w46c`; full hash `16186388126ee80b290381d7230ae90047dbfa56` (`git -C ~/flakes/media rev-parse HEAD`, 2026-09-11). 15a's precondition (W6's fix round first) holds.
2. **97 tracked files in media**, heaviest `pkgs/comfyui/deps` (17). `cd ~/flakes/media && git ls-files | wc -l`.
3. **Media's surface: 3 modules, 5 packages, 21 checks.** `nix eval --raw --impure --expr 'builtins.attrNames (builtins.getFlake "git+file:///home/dalhaka/flakes/media").checks.x86_64-linux'` (and `packages`, `nixosModules`). GN12's acceptance names four of the 21.
4. **No media input, no host integration.** `grep -n -i media flake.nix` → `:1159` (an assertion message), `:3061` (a path string), neither an input; `hosts/core/helm.nix:12-13` says media stays out; `git ls-files hosts/core | grep -c media` → 0 (2026-09-14).
5. **Generation owns nothing; the manifest check is red before this plan.** `docs/ledger/subsystems.toml:213-222` → `owns = []`, `plans` naming `2026-09-02-media-flake.md` and `2026-09-11-generation.md`; `nix develop -c python3 pkgs/evidence/subsystems.py validate --root . docs/ledger/subsystems.toml` → exit 1, ten `uncovered:` lines on 2026-09-14 (nine `docs/context/*.md`, `docs/ledger/areas-grandfather.toml`; nineteen once the batch lands). GN11's `subsystems-manifest` acceptance presumes EV10 has landed.
6. **A `repo: media` section is invisible to this repo's guards.** `pkgs/evidence/tasks.py:1061,1995-1997`: a task attributed elsewhere leaves this repo's task list and the MAP.md acceptance rule; `ls ~/flakes/media/docs/ledger` → no such directory, so `load_manifest` yields `([], [])` there.
7. **A directory entry in `touches` covers every path under it; a glob is refused.** `sed -n '1210,1220p' tools/factory/seat/factory-lib.sh` (prefix match) and `pkgs/evidence/tasks.py` draft rule (b) (`*?[` refused) — measured 2026-09-11. No task here names a directory since the revision moved the subtree landing out of GN11 (Assumption 21).
8. **`comfy-worlds-unit` runs every `tests/comfy-worlds/test_*.py`; each wrapper points at one file.** `sed -n '776,845p' ~/flakes/media/flake.nix` (the check copies `pkgs/comfy-worlds`, `pkgs/media-fetch` and `tests/comfy-worlds` into a fresh tree, runs `bats`, then `pytest tests/comfy-worlds -q` if any `test_*.py` exists; `pyEnv` is `python3.withPackages (ps: [ ps.pytest ])`, `:32`). GN1 and GN5 add a module and a test with no shared-file edit, so stage 1 is parallel.
9. **`lan.enable = false` renders no Caddy at all.** `grep -n 'mkIf cfg.lan.enable' ~/flakes/media/nixosModules/comfyui-worlds.nix` → `:285` (tmpfiles), `:289` (caddy serviceConfig), `:314` (group), `:316` (services.caddy), `:327` (firewall) — measured 2026-09-11. Assumption 20 rests on it, and `comfy-worlds-eval` already asserts it (`~/flakes/media/flake.nix:608-621`, the `cOff` block).
10. **The design reserves the seams this plan fills.** `sed -n '85p;176,180p;319,326p' ~/flakes/media/docs/superpowers/specs/2026-09-05-comfy-worlds-design.md`: `worlds/<world>/feed.sqlite` (index, rebuildable), the PNGs' `prompt`/`workflow` chunks as the source of truth, the queue and the feed app out of sub-project 1's scope.
11. **The placeholder is the whole feed today.** `~/flakes/media/pkgs/comfy-worlds/feed_placeholder.py:1-14` (157 lines: `GET /`, `GET /out/<name>`, `GET /healthz`; `build_server(root, world, systemctl, port=0)` is the seam its test uses). No plan or spec for sub-projects 2/3 exists (`ls ~/flakes/media/docs/superpowers/{plans,specs}` → three and two files, 2026-09-14).
12. **WH1 and WH2 are unparseable.** `grep -n '^### WH' ~/flakes/media/docs/superpowers/plans/2026-09-05-comfy-worlds.md` → `:979`, `:1040`, headings of the form `(code, S, in …)`; `pkgs/evidence/tasks.py:42-43`. WH1 is GN10's starting point.
13. **Zero `GN` keys exist anywhere.** `nix develop -c python3 pkgs/evidence/tasks.py --root . json | grep -c '"key": "GN'` → 0 at `4068f86` (2026-09-14; the nine drafts sit outside the plans glob). The looser `grep -c '"GN'` prints 1 — the subsystems manifest's own `"prefix": "GN"` field in the same single-line JSON, not a key.
14. **Cost of the record.** Twelve W-series runs: input 8,774,292, output 759,481, wall 9,468.95 s, ≈ $6.09 inferred at `docs/ledger/openrouter-prices.csv:3-4` (`grep -h '^usage:' ~/factory/runs/{cw1,cw2,w3b,w5b,w46,w46b,w46c}/*.result`); twelve tasks of the same shape are the same order; review-call cost UNMEASURED.
15. **UNVERIFIED: `nix flake check -L` green in `~/flakes/media` at `1618638`** (minutes of VM builds, not run). Stage 1's commit bodies paste the baseline run of their own acceptance checks before their red; a red baseline is a fix round before this plan.
16. **UNMEASURED: `comfy-upstream-probe.timer` on `core`** — moot until GN10; question 2 decides it.
17. **The two flakes' nixpkgs differ today.** `flake.lock` `nixpkgs-host` → `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` (`flake.nix:6`); `~/flakes/media/flake.lock` `nixpkgs` → `ac62194c3917d5f474c1a844b6fd6da2db95077d` (2026-09-11). WH1's "satisfiable today" no longer holds; GN10 uses `inputs.nixpkgs.follows = "nixpkgs-host"` on the media input, proven the way `core-gaming-wiring` proves gaming's node (`flake.nix:3084-3086`).
18. **The broker's instance option shape.** `services.egress-broker.instances.<name>` has `hostAddress`, `namespaceAddress`, `listenPort`, `allow` (a host list) and `inject`; `host-core` asserts `openrouter`'s `allow == [ "openrouter.ai" ]` (`flake.nix:1104-1106`); `hosts/core/lanes.nix:6` reserves `10.100.2.x` for media. Media's eval harness stubs instance `media` at `10.100.2.1/10.100.2.2:3130` with `allow` = `huggingface.co` plus four Docker registry names (`~/flakes/media/checks/eval-harness.nix:45-56`), and its single-service eval asserts `instances.media.inject ? "huggingface.co"` (`~/flakes/media/flake.nix:381-383`) — the name already carries the model-fetch expectation; GN10 pins the probe's six hosts only and says so. Measured 2026-09-14.
19. **`HTTPS_PROXY` from a broker instance is an existing pattern.** `nixosModules/modelLane.nix:221` and `nixosModules/seatLane.nix:235` render `HTTPS_PROXY = "http://${hostAddress}:${listenPort}"`; `nixosModules/cowork.nix:41` reads the CA at `/var/lib/egress-broker/<instance>/ca/ca.pem`. GN7 copies that shape into `comfyui-worlds.nix`.
20. **(was OQ3) Caddy's LAN face stays off — a stated conflict, carried as question 3(c).** 14c, 16b and charter `:179` say Caddy on core now; charter `:186-188` gives the LAN face to increment 4 under `IS`, and the module renders Caddy only under `lan.enable` (Assumption 9), so both cannot hold in increment 3. GN10 sets `lan.enable = false`, `core-media-wiring` asserts it; Helm and the desktop reach each feed on `127.0.0.1:<feedPort>`; the flip is Isolation's (its draft's IS11 wants GN's sites "loopback or declared LAN sites"; its Q2 lists the feed as a candidate site). Veto surface: answer 3(c).
21. **The subtree lands by an act of record, not inside GN11.** `tools/factory/seat/factory-task:506` counts `git rev-list --count "$base_sha..task/$key"` — every commit a merge brings — and `:756-761` demotes a `done` whose `FACTORY-COMMITS` differs; a `git subtree add` inside GN11 makes G6's one commit uncountable. Platform's Q6 recommends (b) for dsh-harness — the orchestrator lands the merge on a branch and the wiring task runs on top; this plan mirrors it (`## Dispatch`; GN11's Base line). Veto surface: Platform's Q6 answered (a) — GN11 absorbs the merge in-task and its `touches` gains the directory `media` (Assumption 7).
22. **The engagement stream has one writer, and it is not the feed.** The Evidence draft's EV14 term 1 (`drafts-r2/2026-09-11-evidence.md:342`): stream `ledger/engagement`, kind `engagement`, key `(day, surface)`, "the writer's verb is `evidence.replace_stream` … `evidence.append` is not this stream's verb"; its SCHEMA row names the writer "Helm backend via evidence.replace_stream (HM8)" (`:339`); EV15's fields (`:369-391`): `day`, `surface` (enum `home`, `feed`, `seats`), `opens`, `dwell_s`, `feed_likes`. A second process appending raw lines to a file another process rewrites whole with `os.replace` loses rows — so the feed never opens the store. It could not anyway: the feed unit is `ProtectSystem = "strict"` with `ReadWritePaths = [ "<root>/worlds/<w>" "%h/.cache" ]` (`~/flakes/media/nixosModules/comfyui-worlds.nix:83-88`), and `/var/lib/evidence/ledger` (`drwxr-x--- dalhaka users`, 2026-09-14) is read-only inside it (`EROFS`, not `PermissionError`). GN8 therefore posts to Helm's API instead (Assumption 23).
23. **The Helm draft assigns the feed-side POST to GN and carries neither the swipe embed nor WH2's tile.** `grep -c -i 'swipe\|media-refresh\|feedPort\|8288' ~/factory/batch/2026-09-11/drafts-r2/2026-09-11-helm.md` → 0 (2026-09-14); `:100`: "a feed-side `POST /v1/engage` for `feed_likes` is `GN`'s once HM8 lands"; HM8 (`:473-490`): route `POST /v1/engage`, body `{"counter": <one of ("opens","dwell_seconds","feed_likes")>, "n": <int ≥ 1>, "surface": "helm-home"|"feed"}` → `204`, anything else `400` and nothing written (`:482,485`); the API port is `127.0.0.1:7710` (A16, `:77`). The feed has no script (GN3 term 5), so GN8's server posts the `feed` surface itself; until HM8 answers, the feed drops its batches with one journal line and never fails.

## Global Constraints

Quoted verbatim from `docs/superpowers/plans/2026-09-09-program.md:35-46`, each with its line (G12 sits between G7 and G8 there); where a quote names a program-plan key, this plan's reading follows the quotes.

- **G1 Build-only.** Never `sudo`, `nixos-rebuild`, `systemctl start|stop|restart|enable|kill`, basket mount or teardown. The operator switches; a task that needs the live system to change says so in its `## Operator` line and stops. [program.md:35]
- **G2 Red first.** Every check or test a task adds is shown failing before the change that makes it pass, and the red output is pasted in the commit body. A load-bearing test counts only once it has failed (CLAUDE.md). [program.md:36]
- **G3 Trailers.** Both trailers, in this order: the machine-set `Generated-By:` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` (`docs/board/policies.md:30-36`, decision 52a). A gate reads the implement model from the task's own `.result` (FIX7, `6a84fae`). [program.md:37]
- **G4 Subject.** `<area>: summary (test: <check names>)`, the area being the subsystem's prefix in lower case once PR1 lands (`evidence:`, `factory:`, `isolation:`, `knowledge:`, `program:`), the check names being exactly the task's `acceptance` list. Guarded twice: the workspace's `commit-msg` hook that `factory-ws` installs (`tools/factory/seat/factory-ws:131-136`, `factory-commit-msg.sh`) and the gate's convention section, which compares the subject byte for byte with the section's `commit subject` line. [program.md:38]
- **G5 Touches.** Edit only the files the task's `touches` names; a new file is named there too. An undeclared touch demotes the result (`factory-task:857-861`). `git add` every new file before any `nix build` (flakes see tracked files only). **One standing exemption, added 2026-09-10 after it was flagged twice:** the *derived queue block* of `docs/OPERATIONS.md`, and nothing else in that file, when the pre-commit's G8c forces its regeneration — G6 orders that regeneration, so listing the file in every task's `touches` would be noise and omitting it made the gate read a forced, derived, machine-written hunk as an undeclared touch (HH3's minor, PR1's MAJOR). A gate treats a queue-block-only diff there as declared; any other hunk in that file is an undeclared touch as before, and board prose stays the orchestrator's (the rule that refused W6b at the integrator). **`docs/MAP.md` is exempt on the same ground and for the same reason** (KN1's minor): `lint` asserts it is current (`flake.nix:1081-1086`), so any task that adds or renames a module, package, check or test must run `python3 pkgs/evidence/repomap.py --root . write` and commit the result whether or not its `touches` names the file. Both exemptions cover *derived* files a check or hook forces; neither excuses a hand edit. [program.md:39]
- **G6 Commit route.** `nix develop -c git commit -F <msgfile>` on `task/<KEY>`; one commit per task. **A fix round that starts by cherry-picking its predecessor folds that cherry-pick into its own single commit** (`git cherry-pick -n`, or `git reset --soft` back to the base before committing) — added 2026-09-10 after the instruction proved ambiguous: PR1b's seat folded and PR1c's did not, and `factory-task:757` demoted the second for claiming one commit where the branch carried two. The chain's history lives in the plan and the reviews, not in a stack of replayed commits on one task branch. If the pre-commit refuses only on G8c (a stale board queue block), regenerate with `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board` and include the block in the same commit; never `--no-verify`. [program.md:40]
- **G7 Reserved prefixes** (decision 63a): `IS PL HM SA FA EV GN KN PR` and the two-part keys `SPEC-<XX>`, `PLAN-<XX>`. No other plan may define a key under them. **EV2 landed this guard on 2026-09-10 (`f31b8bb`, integrated `776b492`); it is live and no longer a sentence a reviewer enforces by reading the key.** `tasks.py check` refuses a key whose leading letters match a manifest prefix when its plan file matches none of that subsystem's `plans` globs (`pkgs/evidence/tasks.py:1835-1849`), beside the older refusal of a key defined in more than one plan (now `:1758-1766`). `reserved_prefix` reads the letters before the first digit or hyphen, so `SPEC-<XX>` and `PLAN-<XX>` resolve to `SPEC`/`PLAN`, match no manifest row, and pass. The practical consequence, paid for on 2026-09-10: a subsystem's `plans` list must name a plan file BEFORE that plan may hold keys under its prefix — the eight `2026-09-11-*.md` batch outputs were added to `docs/ledger/subsystems.toml` for exactly this reason. Fix rounds add a lower-case letter (`EV1b`); a re-key never reuses a landed key. [program.md:41]
- **G12 Invariants** (brief §3, Assumption 13, re-ratified after the audit per decision 55a): every task here is written against the six verbatim. Where they bind: EV1 reads the broker's usage log locally and writes only the local store (3: nothing leaves the machine; 5: the timer is Nix configuration); EV5 changes a validator, never a credential field (2); IS1 changes no lane boundary and injects nothing (2, 3); IS2 reads and writes documents only, stores and redirects nothing (2, 3, 6); PR1, EV2, EV3, EV4, EV6, FA1, KN1 are configuration and ledgers reviewable in a diff (5); no task promotes agent-authored code between baskets (6); no task touches basket mounting (1) or adds imperative setup (4). [program.md:42]
- **G8 Privacy.** Nothing leaves the machine. IS2 reads and writes nothing outside `docs/`; no credential, token or key is copied, moved, printed or redirected by any task in this plan. [program.md:43]
- **G9 Areas.** From EV2 on, a task whose `touches` fall in two subsystems declares `**areas:**` with both; `tasks.py check` refuses it otherwise. **EV2 landed this on 2026-09-10 (`f31b8bb`); it is enforced in code, not by hand** (`pkgs/evidence/tasks.py:1823-1834`). The refusal fires only while a task's derived state is `ready`, `blocked`, `ran` or `running`, so a landed key is never refused retroactively, and it exempts exactly the twenty-five keys in `docs/ledger/areas-grandfather.toml` — a list frozen at `dbedfe9`, so a key typed later is refused like any other. Note the grandfather ledger is read from the repo's live path rather than the tree under `--root`, so inside a workspace it exempts nothing (`BUG-ledger-read-from-live-path`): declare `**areas:**` rather than relying on the exemption. [program.md:44]
- **G10 Nix hygiene.** Module headers are `_:` never `{ ... }:` (statix); `hosts/core/hardware-configuration.nix` is never touched; a new language brings its formatter and linter in the same task (none is expected here). [program.md:45]
- **G11 Numbers.** Every integer a task pastes (row counts, line numbers, test counts) is re-run at commit time, not copied from this plan (concept 2026-09-08g). Guarded by the gate: the review rubric's "correct facts" row re-runs the commit body's commands, and a pasted integer that does not reproduce is a MAJOR (the record's `wrong-fact` class in `docs/ledger/plan-defects.toml`). [program.md:46]

Where they bind here: G1 — GN10 and GN11 end at the operator's switches, the landing act is the orchestrator's; G4 — every area is `generation:`; G5 — `docs/MAP.md` regenerates in GN12 (the currency assertion is `flake.nix:1391-1393` at `4068f86` — the quote's `:1081-1086` is program.md's own anchor, stale since; that range is `host-core`'s helm block now); invariant 3 — GN7/GN10 broker the probe, GN3/GN4 keep the feed zero-outbound; invariant 6 — GN8 emits counts only; invariant 5 — everything here is Nix configuration, nothing started by a task.

## Waves

Derived from `dependsOn` and touch overlap; five stages and two switches. **Stage 1 (three seats, all `repo: media`, `dependsOn: none`):** GN1 the index, GN5 the grammar, GN7 the probe — no shared file. **Stage 2:** GN2 and GN3 in parallel on GN1; then GN4 on both. **Stage 3:** GN6 (on GN2, GN4, GN5) and GN8 (on GN4 and EV15) in parallel. **Stage 4:** GN9 (on GN2, GN3, GN4, GN6, GN7), then GN10 (on GN9) — the first switch and the drill's first half. **Stage 5:** the landing act (Assumption 21), GN11 (on GN8, GN10, EV10) and the second switch, then GN12 (on GN11), build-only. GN6 and GN7 share media's `flake.nix` and `comfyui-worlds.nix`; touch overlap serialises them (GN7 stage 1, GN6 stage 3 — no cost).

**What `check --draft` prints today, line by line.** `nix develop -c python3 pkgs/evidence/tasks.py --root . --runs-dir /nonexistent --store /nonexistent check --draft <this file>` at `4068f86` (the `--draft` flag exists, `tasks.py:2448`) exits 1 with exactly eight lines: `GN8 dependsOn EV15: unknown key`, `GN11 dependsOn EV10: unknown key`, `GN10 acceptance core-media-wiring not in docs/MAP.md`, `GN11 acceptance core-media-wiring not in docs/MAP.md`, and `GN12 acceptance <name> not in docs/MAP.md` for `comfy-worlds-unit`, `comfy-worlds-eval`, `media-fetch-unit`, `comfy-upstream-probe-unit`. The two unknown keys are defined in the Evidence draft (`drafts-r2/2026-09-11-evidence.md:164`, `:369`) — the nine plans land together in dependency order, so each **resolves when the Evidence plan lands**. The six MAP lines are the draft rule reading today's `docs/MAP.md`: `core-media-wiring` is the check GN10 adds to `flake.nix`, and the four GN12 names are media's checks, which GN12 brings into this flake — each clears when its task regenerates `docs/MAP.md` (G5) and lands. Nothing else prints. GN10 → GN9 is cross-repo: `tasks.py` satisfies a dependency attributed to another repo when its `(repo, root)` is in `extra_landed` (`pkgs/evidence/tasks.py:1000-1005`), so GN10 is `ready` once media `main` carries GN9.

**Why `waves` shows no GN group, even landed.** `waves --repo nixos-agent-env --json` at `4068f86` prints `[[["EV3"], ["HH5"], ["HH6"], ["SPEC-FA"], ["SPEC-PL"], ["SPEC-SA"]], [["EV4"], ["HH7"], ["PLAN-FA"], ["PLAN-PL"], ["PLAN-SA"]], [["EV6", "HH8"], ["HH10"]], [["HH9"]]]` and `waves --repo media --json` prints `[]` (every W key landed). With this file under the plans glob nothing changes: GN1–GN9 carry `repo: media` (listed under `--repo media` only), and GN10–GN12 are `blocked` — GN10 on GN9 until media `main` carries it, GN11 on EV10 — so this repo's `waves` shows GN10 → GN11 → GN12 only after both land. The stage order above is derived from `dependsOn` by hand against the tool's rule (`:1000-1005`), not read off a run.

**Conflicts, measured.** `tasks.py conflicts --repo nixos-agent-env` (no `--json` flag exists; re-run at `4068f86`, identical) prints three rows, `EV6 × HH6|HH8|HH9: flake.nix`. This plan's `flake.nix` touches add GN10/GN11/GN12 × those four (HH6 `ready`; HH8, HH9, EV6 `blocked`; `tasks.py json`); IS5b, a hit on 2026-09-12, is `ran` and out of the rule. GN10 rebases onto `flake.nix` at dispatch (it alone needs a switch); GN11/GN12 follow by `dependsOn`. No open key touches the four `hosts/core/*` files (HH9's is `helm-home.nix`).

## Cross-plan

**`flake.nix` across the batch.** Twenty-four keys in eight sibling drafts touch it (audit check 3) and the drafts publish orders that disagree; this plan claims no slot beyond the rule above — the orchestrator publishes the queue at dispatch.

- **From Platform (`PL`):** PL5 lands dsh-harness under `pkgs/dsh-harness/*`, so no layout precedent; GN11/GN12 use `media/`. **`repos.toml`, `plan-status.toml`: GN11 ↔ PL6** — additive; PL6's row shape (`drafts-r2/2026-09-11-platform.md:411-413`: `path` repointed here, a `plans` glob, a comment; no new field) is what GN11 writes, literally. **`hosts/core/default.nix`: GN10 ↔ PL4**, **`proton-backup.nix`: GN10 ↔ PL6** — different entries; PL first when both are ready. Platform's Q6 answer governs Assumption 21.
- **From Evidence (`EV`):** **EV15** — the counts-only class exists before any producer (18b; invariant 5); GN8 posts HM8's body and never writes the stream (Assumption 22); resolves when Evidence lands. **EV10** — GN11's `subsystems-manifest` acceptance is red until EV10 covers `docs/context/*` and the plans directory (Assumption 5); **`subsystems.toml`: EV10, then PL1, then GN11** appending one `owns` entry and re-running `subsystems.py write`. `repos.toml` and `plan-status.toml` are Evidence's; GN11 declares `evidence`.
- **From Isolation (`IS`):** nothing before the switch. GN10 declares `isolation` because the probe's broker instance lands in `hosts/core/lanes.nix`. The LAN flip (Assumption 20) is Isolation's increment-4 task and amends `core-media-wiring`'s `lan.enable == false` assertion when it lands.
- **From Knowledge (`KN`):** `docs/runbooks/backup.md` gains the two lab paths in GN10 (`core-backup-wiring` refuses an undocumented path, `flake.nix:3021-3022`); declared `knowledge`. If question 2 is answered (b), the decision file is Knowledge's directory.
- **To Helm (`HM`):** the feed's loopback URL per world (`127.0.0.1:<feedPort>`), `/healthz`, and the page as an embeddable view with no external URL — the surface 14c/15a's "Helm links or embeds" consumes; the Helm draft carries no key for the embed or WH2's tile (Assumption 23), so both are a later Helm increment's, depending on GN3 and GN4. **GN8 → HM8:** the feed posts to `127.0.0.1:7710/v1/engage` (Assumption 23) — no `dependsOn` edge, because the feed drops batches quietly until Helm answers; the drill's step 6b reads the result once HM8 is live. **`hosts/core/helm.nix`: GN10 ↔ HM9** — GN10 edits only the comment at `:12-13`; HM9 first if both are ready, since GN10 needs a switch.
- **To Factory (`FA`):** none. The `repo:` attribution is the SD11/P13 precedent (`docs/superpowers/plans/2026-09-06-seat-driver.md:53,556`); every section carries the field, so nothing waits on EV3's inheritance fix.

## Operator

**Drill, first half (after GN10 integrates; switch #N; the increment's composed drill takes these lines).** One command per step, its acceptance after the arrow.
1. Before the switch: `nix build .#nixosConfigurations.core.config.system.build.toplevel -o /tmp/gn10-result && nix store diff-closures /run/current-system /tmp/gn10-result` → the media closure appears (`comfy-feed`, `media-comfy`, `comfy-worlds-init`, `comfy-world-guard`, `comfy-mutate`, `comfy-upstream-probe`, ComfyUI) and no `caddy` line.
2. `nix build .#checks.x86_64-linux.core-media-wiring -L --no-link` → exit 0.
3. `sudo nixos-rebuild switch --flake .#core` (the operator's act) → generation #N.
4. `comfy-worlds-init --adopt sfw` once (runbook), then `media-comfy start sfw` → `systemctl --user is-active comfyui-sfw.service` prints `active`.
5. `curl -s http://127.0.0.1:8288/healthz` → `ok sfw`; `curl -s http://127.0.0.1:8288/ | grep -c 'seed '` → ≥ 1 once a render exists (prompt and seed on the page).
6. Like one render, regenerate it → `curl -s http://127.0.0.1:8288/jobs` shows one `regenerate` row, then a new PNG with a different seed on the page within one generator cycle. Edit its prompt → an `edit` row, then a PNG whose `prompt` chunk carries the edited text.
   6b. (GN8) `systemctl --user restart comfy-feed-sfw.service` (SIGTERM flushes) → `journalctl --user -u comfy-feed-sfw -n 3` shows `engage: posted 2 bodies to http://127.0.0.1:7710/v1/engage` once HM8 is live, and HM8's day file for today carries `"feed": {"opens": ≥ 1, …}`; before HM8 it shows `engage: http://127.0.0.1:7710/v1/engage unreachable — dropped 2 counts` and nothing else fails.
7. `comfy-mutate --world sfw --dry-run --seed 1 > a; comfy-mutate --world sfw --dry-run --seed 1 > b; cmp a b` → exit 0.
8. `systemctl --user start comfy-upstream-probe.timer` (a switch never starts a user timer); `comfy-upstream-probe --dry-run` under the unit's environment → exit 0 and `api.github.com`/`pypi.org` rows in the `media` instance's log; without it → exit 1 with the invariant-3 message (GN7 term 1).
9. The runbook's aimdo step → its `OK` line closes claim `aimdo-native-load-unmeasured` (`docs/ledger/claims.toml:154-162`) with that evidence.

**Second half (after the landing act and GN11; switch #N+1).** 10. `nix flake metadata --json | jq '.locks.nodes | has("media")'` → `false`. 11. `nix store diff-closures /tmp/gn10-result /tmp/gn11-result` → no media line. 12. Steps 4–8 re-run unchanged. GN12 is build-only: `nix store diff-closures /tmp/gn11-result /tmp/gn12-result` → empty.

**Rollback:** the previous generation from the boot menu or `nixos-rebuild --rollback` (the operator's act); the worlds' trees under `~/comfyui/worlds` are not touched by a generation change; `feed.sqlite` is rebuildable (`comfy-feed index --rebuild`) and the lab repos are git. For GN11, `git revert` of its commit plus `git revert -m 1` of the landing merge restores GN10's input-based state and one switch back; nothing under `~/flakes/media` is deleted by this plan — the sibling's retirement is a later operator act (charter `:65`).

## Dispatch

Runs `gn1`…`gn5` (`ls ~/factory/runs | grep -c '^gn'` → 0 on 2026-09-14 — `BUG-run-name-reuse`); fix rounds `<run>f`, relaunches `<run>b`. Gate: Sonnet (`docs/ledger/subsystems.toml:216`); the orchestrator's Opus special case for GN10 and GN11 (a switch follows each). **Step 0** (the orchestrator, after the operator's word): `tasks.py --root . check` empty on the landed batch, `write-board`, then `docs: plan — Generation (GN1–GN12): the feed index, queue, feed and verbs, the rules mutator, the brokered probe, engagement counts, the runbook, the host wiring, media absorbed (test: lint)`.

Media sections land in `~/flakes/media` from this repo's plan, the P13/SD11 form (`2026-09-06-seat-driver.md:53,556`):

```
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gn1 /home/dalhaka/flakes/media "GN1" "GN5" "GN7" --then "gate at Sonnet, integrate, fast-forward media main"
FACTORY_PLAN=… factory-wave gn2 /home/dalhaka/flakes/media "GN2 GN4" "GN3" --then "gate, integrate; GN4 waits for GN3 inside the run"
FACTORY_PLAN=… factory-wave gn3 /home/dalhaka/flakes/media "GN6" "GN8" --then "GN8 only after EV15 is on main; gate, integrate"
FACTORY_PLAN=… factory-task gn4 /home/dalhaka/flakes/media GN9
```

Landing: `factory-integrate <run> /home/dalhaka/flakes/media <KEY>`, then `git -C /home/dalhaka/flakes/media pull --ff-only ~/factory/base/media integ/<run>`.

Host sections, after GN9 is on media `main`: `FACTORY_PLAN=… factory-wave gn4h /home/dalhaka/nixos-agent-env "GN10" --then "gate at Opus, integrate; the operator switches (#N), drill steps 1–9"`. **The landing act** (Assumption 21; the orchestrator, after that drill and EV10): `git -C ~/flakes/media tag absorbed/media-$(git -C ~/flakes/media rev-parse --short main)`; on `absorb/media` from `main`, `git subtree add --prefix=media /home/dalhaka/flakes/media main` (no `--squash`; `git cat-file -p HEAD | grep -c '^parent'` → 2; `git merge-base --is-ancestor 16186388126ee80b290381d7230ae90047dbfa56 HEAD` → 0), a board line, fast-forward. Then `FACTORY_PLAN=… factory-wave gn5 /home/dalhaka/nixos-agent-env "GN11 GN12" --then "gate GN11 at Opus, GN12 at Sonnet; the operator switches (#N+1) after GN11, steps 10–12"`. Before every host launch: the board block committed (G6) and `conflicts` run — wait for any `running`/`ran` key sharing `flake.nix`.

**Relaunch after a death:** `FACTORY_PLAN=… factory-task <run>b <workspace> <KEY> --prior <run>/<KEY>` after a `<KEY>b` section is appended (every media fix round carries `**repo:** media` itself). **A re-plan:** a rejected key re-enters as a Fable re-plan through the lane (charter §5).

## Anticipation

- **GN1's fixture is not a PNG ComfyUI wrote**; drill step 6 reads a real render's chunk — if ComfyUI's key differs from `prompt`, `read_chunks` is one constant away and the drill is the red.
- **GN2's check cannot see `tests/mocks/`** (three directories copied, media `flake.nix:805-808`): exactly one named skip; a second is a MINOR.
- **GN3's VM step is not run red**; the unit suite is the red for the same path (Assumption 15); a red VM baseline is a fix round before GN3.
- **GN8 before EV15 or HM8 on a hand launch**: the media workspace cannot read this repo, so the orchestrator — not the seat — pastes `'engagement' in streams.KINDS` → `True` in the launch note; the feed drops batches until `/v1/engage` answers `204`.
- **GN10's lock may pin a rev past GN9** if media `main` moved: the seat pastes `git -C ~/flakes/media log --oneline -1` and the lock's `rev`; they agree or the run stops.
- **GN10's exact `allow` list bites the first model-fetch wiring** — by design, a visible edit (Assumption 18).
- **The landing act may not be lint-clean**: the fix is a task under the next free number (GN13), never a suffix; GN11 waits.
- **GN11's `subsystems-manifest` is red for reasons outside this plan** until EV10 and the audit's 5c registrations land; the seat stops with `status=partial` if `validate` names paths outside `media/`.
- **A switch starts no user timer**: drill step 8 starts the probe timer by hand (GN9 says so).
- **Claims:** step 9 closes `aimdo-native-load-unmeasured`; nothing else flips. **Questions:** 1–3; the rest are Assumptions 20–23 with veto surfaces.

## Not in this plan

- The mutator's local-model phase and Phase 5 local weights (17c; charter `:67-68`); the LAN face (20b; increment 4, `IS`; Assumption 20).
- Helm's swipe-view embed and WH2's `media-refresh` tile (Helm-owned; not in the Helm draft either, Assumption 23); the engagement stream's definition and data class (Evidence's).
- The generation lab (`docs/concepts/2026-09-06a-generation-lab.md`, idea status) and CivitAI entries; network-namespace confinement of a world (`design:325-326`); the driver-580 / CUDA 13 bump itself (the probe proposes, the operator switches and reboots).
- The other five siblings' absorption (increment 4, `PL`); the `flake.nix` split and import assertion (4a); `pkgs/evidence/tasks.py`'s `HEADING_RE` and `repo:` inheritance (Evidence's).
- Retiring `~/flakes/media` as a working directory after GN11: the operator's act, on the drill's evidence.

---

### GN1 (code, S) — the feed index: feed.sqlite rebuilt from the renders' PNG chunks

**repo:** media
**dependsOn:** none
**touches:** pkgs/comfy-worlds/feed_index.py, tests/comfy-worlds/test_feed_index.py
**acceptance:** comfy-worlds-unit, lint
**commit subject:** `generation: feed.sqlite — the per-world index rebuilt from the PNGs' prompt, workflow and seed chunks (test: comfy-worlds-unit, lint)`

**Why.** The design reserves `worlds/<world>/feed.sqlite` "for sub-project 2 (index, rebuildable)" (`sed -n '85p;178p' docs/superpowers/specs/2026-09-05-comfy-worlds-design.md`) and names the PNGs' `prompt`/`workflow` chunks as the source of truth (`:176-180`), but nothing reads them (`grep -rl sqlite pkgs/ tests/` → empty, 2026-09-11); the placeholder lists files by mtime only (`feed_placeholder.py:43-52`). Every later task of sub-project 2 reads or writes this table, so it lands first, alone (Assumption 8).

**Files.** Create `pkgs/comfy-worlds/feed_index.py` — a stdlib-only module (`sqlite3`, `struct`, `zlib`, `json`, `pathlib`) with `open_db`, `read_chunks`, `rebuild`, `newest` and a `main` for `python3 feed_index.py --root R --world W rebuild`. Create `tests/comfy-worlds/test_feed_index.py` — pytest, loading the module by path as `test_feed_placeholder.py:16-20` does, with a helper that writes a minimal valid PNG carrying `tEXt` chunks.

**Interfaces.**
1. `open_db(root, world)` returns a `sqlite3.Connection` on `<root>/worlds/<world>/feed.sqlite`, creating the file and the schema if absent: `renders(name TEXT PRIMARY KEY, prompt TEXT, workflow TEXT, seed INTEGER, mtime REAL)` and `likes(name TEXT PRIMARY KEY REFERENCES renders(name), liked_at REAL)`. Both `CREATE TABLE IF NOT EXISTS`.
2. `read_chunks(path)` returns `{"prompt": str|None, "workflow": str|None, "seed": int|None}` from the PNG's `tEXt`/`iTXt` chunks with keys `prompt` and `workflow` (ComfyUI's own keys; `iTXt` is what PIL writes for a non-Latin-1 prompt); `seed` is `inputs.seed` of the `KSampler`-class node with the numerically lowest node id in the parsed `prompt` JSON (the base sampler in the base-plus-refiner shape), else `None`. A file that is not a PNG (bad 8-byte signature) raises `ValueError("not a PNG: <name>")`. **The workflow JSON's schema, for this and GN2/GN4/GN6:** an object mapping node id (a string) → `{"class_type": <str>, "inputs": {<name>: <literal or ["<node id>", <output index>]>}}` — `sed -n '1,40p' tests/acceptance/workflows/sdxl.json`: node `"3"` is `KSampler` with `inputs.seed`, `inputs.sampler_name`, `inputs.positive: ["6", 0]`; `"6"`/`"7"` are `CLIPTextEncode` with `inputs.text` (`grep -c class_type` → 7; the file has one `KSampler`, `:31`). The test fixture is `sdxl.json` trimmed to nodes 3, 6, 7 **plus a second `KSampler` node `"10"`** (the refiner shape: `inputs.seed = 99`, `inputs.positive: ["6", 0]`), so a reader that takes the last or the only-first sampler is caught: node 3's seed is 42 in the fixture, node 10's is 99.
3. `rebuild(root, world)` scans `<root>/worlds/<world>/output/*.png`, upserts one `renders` row per file, deletes rows whose file is gone, leaves `likes` rows untouched, and returns the row count. Running it twice on an unchanged directory returns the same count and changes no row (idempotent); a missing `output/` directory yields 0 rows, not an error.
4. `newest(conn, limit=50)` returns rows ordered by `mtime DESC, name` — the placeholder's order, now from the index.
5. The module writes nothing outside `feed.sqlite`; the PNGs are read-only (invariant: the files are the record, the index is disposable) — asserted by `test_rebuild_leaves_the_output_dir_byte_identical`: the sorted listing of `output/` and each file's `(st_mtime_ns, sha256)` before `rebuild` equal those after, and `output/` gains no file.

**Steps.**
1. **Red.** Write `tests/comfy-worlds/test_feed_index.py` with a `png_with_chunks(path, prompt_json, workflow_json, itxt=False)` helper (signature + `IHDR` + one `tEXt` — or `iTXt` when `itxt` — per key + `IEND`, CRCs via `zlib.crc32`) and the tests: `test_rebuild_reads_prompt`, `test_rebuild_reads_workflow`, `test_rebuild_reads_seed`, `test_reads_itxt_chunks`, `test_rebuild_is_idempotent`, `test_rebuild_drops_deleted_files_keeps_likes`, `test_non_png_refused`, `test_missing_output_dir_is_zero`, `test_newest_orders_by_mtime`, `test_rebuild_leaves_the_output_dir_byte_identical`. Run `nix develop -c pytest tests/comfy-worlds/test_feed_index.py -q` → `FileNotFoundError` from `spec_from_file_location` on the missing module (10 errors). Paste the red into the commit body.
2. Create `pkgs/comfy-worlds/feed_index.py` implementing terms 1–5. `nix develop -c ruff check pkgs/comfy-worlds/feed_index.py` clean.
3. **Green.** `nix develop -c pytest tests/comfy-worlds -q` → `10 passed` plus the placeholder's existing two; `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` → the derivation completes, its log showing `pytest tests/comfy-worlds -q` ran (Assumption 8 — the check's glob loop finds the new file); `nix build .#checks.x86_64-linux.lint -L --no-link` green. Paste all three tails.
4. **Mutants** (each: apply, run `nix develop -c pytest tests/comfy-worlds/test_feed_index.py -q`, paste the failing line, revert):
   - **M1 seed-ignored**: return `None` for `seed` regardless of the JSON → `test_rebuild_reads_seed` fails on `assert row["seed"] == 42`. **M1e last-sampler**: take the last `KSampler` node (or iterate in file order and keep overwriting) → the same test fails with `99 != 42`.
   - **M7 png-touched**: `os.utime(path)` on each PNG after reading it (or open it `"ab"`) → `test_rebuild_leaves_the_output_dir_byte_identical` fails on `st_mtime_ns`.
   - **M1b prompt-ignored**: skip the `prompt` chunk → `test_rebuild_reads_prompt` fails on `row["prompt"] is None`. **M1c workflow-ignored**: skip the `workflow` chunk → `test_rebuild_reads_workflow` fails the same way. **M1d itxt-ignored**: read `tEXt` only → `test_reads_itxt_chunks` fails on `row["prompt"] is None`.
   - **M2 no-delete**: drop the `DELETE FROM renders WHERE name NOT IN (...)` statement → `test_rebuild_drops_deleted_files_keeps_likes` fails on the stale row count.
   - **M3 likes-wiped**: add `DELETE FROM likes` inside `rebuild` → the same test fails on `likes` count `0 != 1`.
   - **M4 signature-unchecked**: skip the 8-byte signature test → `test_non_png_refused` fails with `DID NOT RAISE`.
   - **M5 order-asc**: `ORDER BY mtime ASC` → `test_newest_orders_by_mtime` fails on the first name.
5. **Negative control.** `test_rebuild_is_idempotent` must PASS: two `rebuild` calls return equal counts and `SELECT * FROM renders` is byte-identical. Its discriminating row: mutant **M6 mtime-now** (write `time.time()` instead of `st_mtime`) makes the second snapshot differ → the control fails, proving it measures stability, not vacuity. Revert.
6. Commit with the subject above; the body carries Step 1's red, Step 3's green tails and each mutant's failing line.

**probes:**
- sqlite-stdlib-only: `grep -c -E '^(import|from) ' pkgs/comfy-worlds/feed_index.py` :: le 10 :: measured after Step 2; every import must resolve from pyEnv (media flake.nix:32, python3 with pytest only), so no third-party name may appear.

### GN2 (code, M) — the job queue on the world's ComfyUI API

**repo:** media
**dependsOn:** GN1
**touches:** pkgs/comfy-worlds/queue.py, tests/comfy-worlds/test_queue.py, tests/mocks/comfy-api-fake.py
**acceptance:** comfy-worlds-unit, lint
**commit subject:** `generation: the job queue — submit, poll and record a workflow with an explicit seed against ComfyUI on loopback (test: comfy-worlds-unit, lint)`

**Why.** The design scopes "a job queue on ComfyUI's API" into sub-project 2 (`sed -n '319,323p' docs/superpowers/specs/2026-09-05-comfy-worlds-design.md`) and nothing implements it: `grep -rn '/prompt\|/history' pkgs/` → 0 hits (measured 2026-09-11). The generator answers on `127.0.0.1:<comfyPort>` (`nixosModules/comfyui-worlds.nix:58`, `--listen 127.0.0.1 --port …`); regenerate, edit-prompt (GN4) and the mutator (GN6) all need one place that submits a workflow with an explicit seed and records what came back, tested without a model — the check must stay CPU-cheap (`comfy-worlds-unit` is a `runCommand`, `flake.nix:776-778`).

**Files.** Create `pkgs/comfy-worlds/queue.py` — stdlib (`urllib.request`, `json`, `sqlite3`, `time`, `uuid`), imports `feed_index` by relative path for `open_db`. Create `tests/mocks/comfy-api-fake.py` — a stdlib `http.server` faking `POST /prompt` (returns `{"prompt_id": …}`), `GET /history/<id>` (the recorded outputs once `tick()` is called) and `GET /system_stats`; importable (the test starts it in a thread) and runnable. Create `tests/comfy-worlds/test_queue.py`. **Measured constraint:** `comfy-worlds-unit` copies only `pkgs/comfy-worlds`, `pkgs/media-fetch` and `tests/comfy-worlds` (`sed -n '805,808p' flake.nix`) and this task does not touch `flake.nix`; so `tests/mocks/comfy-api-fake.py` is the canonical fake (GN3's VM test and GN4 reuse it) and `test_queue.py` carries a verbatim copy under `# mirror of tests/mocks/comfy-api-fake.py` with `test_fake_mirror_is_current` asserting the two texts identical when the mock file is present — skipped only inside the check, the one permitted skip, named in the commit body.

**Interfaces.**
1. `open_db` gains nothing; `queue.ensure_schema(conn)` creates `jobs(id TEXT PRIMARY KEY, kind TEXT CHECK(kind IN ('regenerate','edit','mutate')), source TEXT, prompt TEXT, seed INTEGER NOT NULL, state TEXT CHECK(state IN ('queued','submitted','done','failed')), prompt_id TEXT, output TEXT, error TEXT, created REAL, updated REAL)`.
2. `enqueue(conn, kind, source, workflow, seed)` → job id; `workflow` is GN1's schema; sets every `KSampler`-class node's `inputs.seed` to `seed` (an explicit integer, never "random"), stores the prompt text, state `queued`. A `seed` that is not an `int` raises `TypeError`; a `workflow` with no `KSampler`-class node raises `ValueError("no KSampler node in workflow")` before any row is written (the rule GN5's `RuleNeverFires` follows: a job that can never pin its seed is an error, not silence); a `kind` outside the enum raises `sqlite3.IntegrityError` from the `CHECK`, and so does a `state` written outside its enum.
3. `submit(conn, job_id, base_url)` POSTs `{"prompt": workflow, "client_id": job_id}` to `<base_url>/prompt` with `timeout=10`, records `prompt_id`, state `submitted`, returns `True`. `base_url` must start with `http://127.0.0.1:` — anything else raises `ValueError("queue: ComfyUI is loopback-only")`. **ComfyUI unreachable** (`urllib.error.URLError`, `ConnectionError`, `TimeoutError`, or an HTTP status ≥ 500): the job **stays `queued`**, `error` = the exception's text, `updated` = now, returns `False` — a world whose generator is stopped (`media-comfy stop`) is the normal case, not a failure; the job is retried on the next `run_once`. A 4xx answer is the job's fault: `failed`, `error` = the body.
4. `poll(conn, base_url)` GETs `/history/<prompt_id>` for each `submitted` job; an entry with `outputs.*.images[0].filename` → state `done`, `output` = that filename; an entry with `status.status_str == "error"` → `failed`, `error` = the message; absent → unchanged; unreachable (the term-3 classes) → the job stays `submitted`, `error` set, and the remaining jobs are still polled. Returns the number of rows changed.
5. `pending(conn)` lists `queued` jobs oldest first; `run_once(conn, base_url)` = submit every `queued` in that order — a `False` from one job does not stop the next — then one `poll`; returns `{"submitted": n, "unreachable": m, "changed": k}` and never raises on a network error.
6. The fake at `tests/mocks/comfy-api-fake.py`: `FakeComfy(port=0)` with `.start()`, `.url`, `.tick(filename)` (moves every submitted id to done with that filename), `.fail(prompt_id, msg)`, `.prompts` (the raw bodies it received, for assertions on the seed).

**Steps.**
1. **Red.** Write `tests/mocks/comfy-api-fake.py` and `tests/comfy-worlds/test_queue.py` with: `test_enqueue_pins_the_seed_in_every_sampler` (GN1's two-`KSampler` fixture: the body the fake receives carries the seed in node `"3"` **and** node `"10"`), `test_enqueue_refuses_non_int_seed`, `test_enqueue_refuses_workflow_without_sampler`, `test_enqueue_refuses_unknown_kind`, `test_state_check_refuses_unknown_state` (a raw `UPDATE jobs SET state='bogus'` → `IntegrityError`), `test_submit_refuses_non_loopback`, `test_submit_then_poll_records_output`, `test_poll_records_failure`, `test_run_once_submits_queued_then_polls`, `test_submit_unreachable_leaves_job_queued` (bind a socket to `127.0.0.1:0`, read its port, close it; two queued jobs; `run_once` against `http://127.0.0.1:<that port>` returns `{"submitted": 0, "unreachable": 2, "changed": 0}`, both rows `queued` with `error` non-empty, and nothing raised). `nix develop -c pytest tests/comfy-worlds/test_queue.py -q` → 10 errors, `FileNotFoundError: … pkgs/comfy-worlds/queue.py`. Paste.
2. Create `queue.py` implementing terms 1–5; the six functional tests use the in-file mirror of the fake, so they run identically from the repo root and inside the check.
3. **Green.** `nix develop -c pytest tests/comfy-worlds -q` → all pass, `0 skipped` (the mirror test finds `tests/mocks/`); `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` green with exactly `1 skipped` (the mirror test) in its log; `nix build .#checks.x86_64-linux.lint -L --no-link` green (ruff covers `tests/mocks/`). Paste all three tails.
4. **Mutants** (apply, `nix develop -c pytest tests/comfy-worlds/test_queue.py -q`, paste, revert):
   - **M1 seed-unpinned**: skip the sampler rewrite → `test_enqueue_pins_the_seed_in_every_sampler` fails: the fake's received body has the original seed. **M1b first-only**: rewrite the first `KSampler` and `break` → the same test fails on node `"10"`'s seed (`99`, not the pinned value).
   - **M7 unreachable-is-failed**: mark the job `failed` on `URLError` → `test_submit_unreachable_leaves_job_queued` fails on `state == 'queued'`. **M7b raise-through**: let `URLError` propagate out of `submit` → the same test fails with the exception and `unreachable` never reaches 2.
   - **M2 seed-any**: drop the `isinstance(seed, int)` check → `test_enqueue_refuses_non_int_seed` `DID NOT RAISE`.
   - **M2b no-sampler-ok**: enqueue when no `KSampler` node exists → `test_enqueue_refuses_workflow_without_sampler` `DID NOT RAISE`. **M2c check-dropped**: remove both `CHECK(... IN (...))` clauses → `test_enqueue_refuses_unknown_kind` and `test_state_check_refuses_unknown_state` `DID NOT RAISE`.
   - **M3 any-host**: drop the loopback prefix check → `test_submit_refuses_non_loopback` `DID NOT RAISE`.
   - **M4 failure-swallowed**: treat `status_str == "error"` as absent → `test_poll_records_failure` fails on `state == 'submitted'`.
   - **M5 poll-first**: swap the order in `run_once` → `test_run_once_submits_queued_then_polls` fails: the job is `submitted`, not `done`, after one call with a pre-ticked fake.
5. **Negative control.** `test_submit_then_poll_records_output` must PASS end to end against the fake; its discriminating row is mutant **M6 fake-blind** (make the fake's `/history` return `{}` always) → the control fails on `state == 'done'`, so a fake that answers nothing cannot pass it.
6. Commit.

**probes:**
- no-random-seed: `grep -c 'randint\|random()' pkgs/comfy-worlds/queue.py` :: le 0 :: the queue never chooses a seed; callers pass one (GN4 draws it, GN5 derives it).

### GN3 (code, M) — the feed: a vertical feed of renders over the index replaces the placeholder

**repo:** media
**dependsOn:** GN1
**touches:** pkgs/comfy-worlds/feed.py, pkgs/comfy-worlds/feed_placeholder.py, pkgs/comfy-worlds/default.nix, tests/comfy-worlds/test_feed.py, tests/comfy-worlds/test_feed_placeholder.py, tests/integration/comfy-worlds-vm.nix
**acceptance:** comfy-worlds-unit, comfy-worlds-vm, lint
**commit subject:** `generation: the feed — a vertical feed of renders over feed.sqlite, zero-outbound, replacing the placeholder (test: comfy-worlds-unit, comfy-worlds-vm, lint)`

**Why.** `comfy-feed` is the placeholder by its own header: "fronts the world's output directory while the real feed (sub-project 2) does not exist yet" (`sed -n '3,4p' pkgs/comfy-worlds/feed_placeholder.py`), wired at `pkgs/comfy-worlds/default.nix:75` (`exec … ${./feed_placeholder.py}`; `:74` is the `];` closing `runtimeInputs`) and started by the module at `nixosModules/comfyui-worlds.nix:82`. It lists filenames and mtimes only (`:83-100`). 14c makes the swipe view "the feed component Helm reaches" and 15a has Helm embed it, so the page must exist here, on the same loopback port, zero-outbound (the placeholder's rule, `:13-14`).

**Files.** Create `pkgs/comfy-worlds/feed.py` — the real server, importing `feed_index` by path; subcommands `serve` (the placeholder's flags) and `index --rebuild`. Modify `pkgs/comfy-worlds/default.nix:75` — `comfy-feed` execs `feed.py serve`. Modify `pkgs/comfy-worlds/feed_placeholder.py` — reduced to a 6-line shim that prints `comfy-feed: the placeholder was replaced by feed.py (GN3)` to stderr and exits 2 (kept; deleted in no task here). Create `tests/comfy-worlds/test_feed.py` — the placeholder's two tests carried over (`test_feed_placeholder.py:66` `test_index_lists_newest_first_and_escapes`, `:85` `test_out_serves_only_basenames`; measured 2026-09-14), plus the new ones. Modify `tests/comfy-worlds/test_feed_placeholder.py` — one test: the shim exits 2 with that message. Modify `tests/integration/comfy-worlds-vm.nix` — step (5) (`:158-165`) asserts the render appears *with its prompt text*, and adds `index --rebuild`.

**Interfaces.**
1. `GET /` — HTML: the world name, the generator's `is-active` state, and the `newest(conn, 50)` rows, each as one `<article>` with `<img src="/out/<name>">`, the prompt text, `seed <n>` and the mtime. Everything through `html.escape`; the page satisfies the zero-outbound rule of term 5. Empty index → the page with `<p>no renders yet</p>`, status 200.
2. `GET /out/<name>` — unchanged from the placeholder (basename only, no `/`, no `..`, 404 otherwise).
3. `GET /healthz` — `ok <world>`, unchanged (the VM test and the drill read it).
4. `comfy-feed serve --world W --root R --port P [--systemctl S]` binds `127.0.0.1:P` and, before serving, runs `feed_index.rebuild` once so a fresh world has an index; `comfy-feed index --rebuild --world W --root R` rebuilds and prints the row count, exits 0.
5. Zero-outbound as one rule over values, not attribute names: `test_page_is_zero_outbound` parses every served page with `html.parser.HTMLParser` (names arrive lower-cased) and asserts (i) every tag is in the closed set `html head meta title body main article img p span form button input a h1 time`; (ii) no attribute name starts with `on`; (iii) **every attribute value of every tag**, whatever the attribute's name (`src`, `href`, `action`, `formaction`, `poster`, `data`, `cite`, `ping`, `content` …), is free of a URL: no match for `^[A-Za-z][A-Za-z0-9+.-]*:` (a scheme before the first `/`) and no leading `//`; (iv) no `meta` tag carries `http-equiv` (the refresh redirect is a navigation without a `src`), and the only `meta` allowed is `charset`; (v) no `srcset`, `style` or `ping` attribute exists. `<SCRIPT>`, `javascript:`, `data:`, `srcset=`, `onerror=`, `<button formaction="https://…">` and `<meta http-equiv="refresh" content="0;url=https://…">` all fall outside it; any value that survives resolves against the page's own loopback origin.
6. The placeholder's `build_server(root, world, systemctl, port=0)` signature is kept in `feed.py`; `test_feed.py` starts it with the placeholder test's helper, carried over verbatim (`test_feed_placeholder.py:37-41`): `def start(root, world, systemctl_bin): srv = feed.build_server(root=root, world=world, systemctl=systemctl_bin); thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start(); return srv`, and reads `srv.server_address[1]` for the port.

**Steps.**
1. **Red.** Write `tests/comfy-worlds/test_feed.py`: the two tests carried over (`test_out_serves_only_basenames` — basename, `..` refused, 404 on unknown — and the escaping half of `test_index_lists_newest_first_and_escapes`), `test_page_lists_prompt_and_seed_from_index`, `test_page_empty_index_200`, `test_page_is_zero_outbound`, `test_serve_rebuilds_index_on_start`, `test_index_rebuild_subcommand_prints_count`. `nix develop -c pytest tests/comfy-worlds/test_feed.py -q` → 7 errors, `FileNotFoundError: … feed.py`. Then edit `tests/integration/comfy-worlds-vm.nix` step (5) to write a PNG with a `prompt` tEXt chunk (the GN1 helper's bytes, inlined as base64) and assert `curl -fsS http://127.0.0.1:8289/ | grep -q 'vm prompt text'`; the check cannot be run red cheaply (a VM build) — record it as **not run red; red proven by the unit suite for the same code path** in the commit body, which is the standing reading for VM steps (Assumption 15). Paste the unit red.
2. Create `feed.py`; rewire `default.nix:75`; reduce the placeholder to the shim; replace `test_feed_placeholder.py`'s body with `test_shim_exits_2`.
3. **Green.** `nix develop -c pytest tests/comfy-worlds -q` → all pass; `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` green (its bare-PATH probe `comfy-feed --help`, `flake.nix:826-828`, now exercises `feed.py`'s argparse); `nix build .#checks.x86_64-linux.comfy-worlds-vm -L --no-link` green with the step-(5) prompt grep in the log; `lint` green. Paste.
4. **Mutants** (apply, `nix develop -c pytest tests/comfy-worlds/test_feed.py -q`, paste, revert):
   - **M1 files-not-index**: list `output/*.png` by mtime instead of `newest(conn)` → `test_page_lists_prompt_and_seed_from_index` fails: no `seed 42` in the body.
   - **M2 no-escape**: drop `html.escape` on the prompt → the same test's `<b>` fixture prompt appears raw; assertion `"&lt;b&gt;" in body` fails.
   - **M3 script-tag**: add `<SCRIPT></SCRIPT>` to the template → `test_page_is_zero_outbound` fails on rule (i). **M3b handler**: add `onerror="x"` to the `<img>` → fails on rule (ii). **M3c scheme**: `href="javascript:void(0)"` on the article anchor → fails on rule (iii). **M3d meta-refresh**: add `<meta http-equiv="refresh" content="0;url=https://example.net/">` to `<head>` → fails on rule (iv) (and on (iii) through `content`). **M3e formaction**: add `formaction="https://example.net/x"` to the like button → fails on rule (iii) — an attribute name outside the old three-name list.
   - **M4 no-rebuild-on-start**: remove the startup `rebuild` → `test_serve_rebuilds_index_on_start` fails: 0 rows after `build_server`.
   - **M5 dotdot**: drop the `..` guard → the carried-over test fails with 200 where 404 was expected.
5. **Negative control.** `test_page_empty_index_200` must PASS (a fresh world renders a page); discriminating row **M6 empty-500** (raise when `newest` returns `[]`) → the control fails on status.
6. Commit.

**probes:**
- placeholder-shim-size: `wc -l < pkgs/comfy-worlds/feed_placeholder.py` :: le 12 :: the placeholder is a shim, not a second server.
- no-external-url-in-source: `grep -c -E 'https?://' pkgs/comfy-worlds/feed.py` :: le 0 :: a second signal beside the rule test — the source names no host either.

### GN4 (code, M) — like, regenerate with a new seed, edit prompt

**repo:** media
**dependsOn:** GN2, GN3
**touches:** pkgs/comfy-worlds/feed.py, tests/comfy-worlds/test_feed.py, tests/integration/comfy-worlds-vm.nix
**acceptance:** comfy-worlds-unit, comfy-worlds-vm, lint
**commit subject:** `generation: like, regenerate with a new seed and edit prompt — the feed writes likes and enqueues jobs (test: comfy-worlds-unit, comfy-worlds-vm, lint)`

**Why.** The design's feed app has "like, regenerate with a new seed, edit prompt" (`sed -n '321,323p' docs/superpowers/specs/2026-09-05-comfy-worlds-design.md`); after GN3 the page is read-only (`grep -c 'do_POST' pkgs/comfy-worlds/feed.py` → 0; the seat re-measures), GN1's `likes` table is empty and GN2's queue has no caller. The three verbs close sub-project 2 and give GN6 its input.

**Files.** Modify `pkgs/comfy-worlds/feed.py` — `do_POST` with three routes, the per-article form buttons in the page, `queue` imported by path. Modify `tests/comfy-worlds/test_feed.py` — the verb tests against the GN2 fake mirror. Modify `tests/integration/comfy-worlds-vm.nix` — a step (5b) after the nsfw render appears: `curl -fsS -X POST -d name=vmtest.png http://127.0.0.1:8289/like` then `sqlite3 …/feed.sqlite 'select count(*) from likes'` → `1` (the VM already has the world tree; `sqlite3` added to the VM's `environment.systemPackages` in the same file).

**Interfaces.**
1. `POST /like` with form field `name` — upserts `likes(name, liked_at=now)`; the name must exist in `renders`, else 404; answers 303 to `/#<name>`. A second like of the same name is idempotent (one row).
2. `POST /regenerate` with `name` — reads the render's `workflow` from the index, draws `seed = secrets.randbelow(2**32)` such that `seed != row.seed`, calls `queue.enqueue(conn, "regenerate", name, workflow, seed)`, answers 303 with the job id in a `?job=<id>` query. No workflow in the index (a PNG without the chunk) → 409 `no workflow recorded for <name>`.
3. `POST /edit` with `name` and `prompt` — replaces `inputs.text` of **every** `CLIPTextEncode` node whose current text equals the render's stored `prompt` (GN1's schema) with the submitted text, then enqueues kind `edit` with a fresh seed as in term 2; an empty `prompt` → 400. The fixture workflow carries two positive `CLIPTextEncode` nodes with the same text (the SDXL refiner shape) and one negative, so "replace only the first" is caught.
4. `GET /jobs` — a plain-text list of `jobs` rows (`id state kind source seed output`) newest first — the operator's view; the page's answer to a verb is the queue's row, never a claim that a render happened (the drill reads this).
5. The page never calls ComfyUI itself: submission and polling stay with `queue.run_once`, which GN6's unit or the operator's `comfy-feed queue --run-once` (added here as a subcommand) invokes. The feed process opens no socket except to `127.0.0.1:<comfyPort>` when that subcommand runs (and, from GN8, to `127.0.0.1:7710`); nothing leaves the machine.
6. Forms are plain `<form method=post action="/like">` with relative actions; GN3 term 5's rule test runs on every page this task renders, including the `/jobs` view.

**Steps.**
1. **Red.** Add to `test_feed.py`: `test_like_writes_one_row_idempotent`, `test_like_unknown_name_404`, `test_regenerate_enqueues_with_different_seed`, `test_regenerate_without_workflow_409`, `test_edit_replaces_prompt_text_and_enqueues`, `test_edit_empty_prompt_400`, `test_jobs_lists_rows`, `test_queue_run_once_reaches_only_loopback` (the fake's `.prompts` receives the body; the `base_url` passed is the fake's `127.0.0.1` URL). `nix develop -c pytest tests/comfy-worlds/test_feed.py -q` → 8 failures with `HTTP Error 501: Unsupported method ('POST')` (no `do_POST`) and 404 on `/jobs`. Paste.
2. Implement terms 1–6 in `feed.py`; add step (5b) and `pkgs.sqlite` to the VM test.
3. **Green.** `nix develop -c pytest tests/comfy-worlds -q` all pass; `comfy-worlds-unit`, `comfy-worlds-vm` (log shows `1` from the likes count), `lint` green. Paste.
4. **Mutants** (apply, `nix develop -c pytest tests/comfy-worlds/test_feed.py -q`, paste, revert):
   - **M1 like-dup**: `INSERT` instead of `INSERT OR REPLACE` → `test_like_writes_one_row_idempotent` fails: `IntegrityError` or count 2.
   - **M2 same-seed**: reuse `row.seed` in regenerate → `test_regenerate_enqueues_with_different_seed` fails on `seed == 42`.
   - **M3 edit-unchanged**: skip the text replacement → `test_edit_replaces_prompt_text_and_enqueues` fails: the fake's body still carries the old prompt. **M3b first-only**: replace the first matching node and `break` → the same test fails on the second positive node's text.
   - **M4 workflow-missing-ok**: enqueue with `workflow=None` → `test_regenerate_without_workflow_409` gets 303.
   - **M5 empty-prompt-ok**: drop the 400 → `test_edit_empty_prompt_400` gets 303.
5. **Negative control.** `test_like_unknown_name_404` must PASS; discriminating row **M6 like-anything** (skip the `renders` existence check) → it gets 303 and fails.
6. Commit.

**probes:**
- no-script-still: `grep -c '<script' pkgs/comfy-worlds/feed.py` :: le 0 :: the verbs are forms; GN3's zero-outbound property survives this task.

### GN5 (code, S) — the mutation grammar: deterministic prompt variants from a rules table

**repo:** media
**dependsOn:** none
**touches:** pkgs/comfy-worlds/mutate.py, tests/comfy-worlds/test_mutate.py
**acceptance:** comfy-worlds-unit, lint
**commit subject:** `generation: the mutation grammar — token swaps, LoRA strengths, samplers and seeds as rules, deterministic by seed (test: comfy-worlds-unit, lint)`

**Why.** Decision 17c is "rules now; the local model as its own phase" (`docs/decisions/2026-09-09-redesign-answers.md:30`), and the loose-ends packet frames the rules as "a mutation grammar over the world's lab repo (token swaps, LoRA strengths, samplers, seeds)" (`docs/research-2026-09-09-redesign-loose-ends.md:187-195`). No such module exists (`ls pkgs/comfy-worlds` → four files, 2026-09-11). The grammar is a pure function, golden-tested with no ComfyUI, model or filesystem — which is what makes the drill's "`--dry-run --seed 1` twice, byte-identical" step falsifiable.

**Files.** Create `pkgs/comfy-worlds/mutate.py` — `load_rules(path)`, `mutate(prompt, rules, seed, n)`, and a `main` reserved for GN6 (this task's `main` only parses `--rules`, `--prompt`, `--seed`, `--n` and prints variants). Create `tests/comfy-worlds/test_mutate.py` with a golden fixture rules dict and expected outputs.

**Interfaces.**
1. Rules are a TOML table (`tomllib`, stdlib) under `[mutate]` in the world's lab `manifest.toml`: `swaps = [["golden hour","blue hour"], …]` (unordered pairs, either direction), `lora = { "<name>" = [min, max] }` (a float range for `<lora:name:strength>` tags), `samplers = ["euler", "dpmpp_2m", …]`, `seed = "derive"|"keep"`. `load_rules` refuses a missing `[mutate]` table with `ValueError("no [mutate] table in <path>")`.
2. `mutate(prompt, rules, seed, n)` returns a list of exactly `n` distinct `Variant(prompt: str, sampler: str|None, seed: int)` built from a `random.Random(seed)` — the same `(prompt, rules, seed, n)` always yields the same list (byte-equal), and two different seeds yield different lists for any non-trivial rules.
3. Each variant applies exactly one rule application per category present: one swap whose left or right token occurs in the prompt, one LoRA strength redrawn within its range for one tag present, one sampler from the list; `mutate` raises `RuleNeverFires(category, detail)` when *no* rule in a category can fire on the prompt (no swap token, no LoRA tag present) — a rule that can never fire is an error, not silence.
4. `seed = "derive"` gives each variant `seed_i = Random(seed).randrange(2**32)` in order; `"keep"` gives every variant the caller's seed (for A/B on text alone).
5. No I/O in `mutate`; `load_rules` reads one file; nothing imports `urllib`.

**Steps.**
1. **Red.** Write `test_mutate.py`: `test_same_seed_same_variants` (golden: a literal expected list for seed 1, n 3), `test_different_seed_differs`, `test_exactly_n_distinct`, `test_swap_either_direction`, `test_lora_strength_within_range`, `test_rule_never_fires_is_error`, `test_missing_table_refused`, `test_keep_seed_policy`. `nix develop -c pytest tests/comfy-worlds/test_mutate.py -q` → 8 errors, `FileNotFoundError: … mutate.py`. Paste.
2. Create `mutate.py` implementing terms 1–5.
3. **Green.** `nix develop -c pytest tests/comfy-worlds -q` all pass; `comfy-worlds-unit` and `lint` green. Paste.
4. **Mutants** (apply, `nix develop -c pytest tests/comfy-worlds/test_mutate.py -q`, paste, revert):
   - **M1 global-random**: use `random.random()` instead of `Random(seed)` → `test_same_seed_same_variants` fails against the golden list.
   - **M2 one-direction**: only swap left→right → `test_swap_either_direction` fails on the reversed fixture.
   - **M3 range-ignored**: emit `max + 1` → `test_lora_strength_within_range` fails.
   - **M4 silent-skip**: return variants when no swap token is present instead of raising → `test_rule_never_fires_is_error` `DID NOT RAISE`.
   - **M5 n-minus-one**: return `n-1` variants → `test_exactly_n_distinct` fails on `len`.
   - **M7 table-optional**: `load_rules` returns `{}` when `[mutate]` is missing instead of raising → `test_missing_table_refused` `DID NOT RAISE` (term 1's refusal; GN6's exit 2 rests on it).
5. **Negative control.** `test_keep_seed_policy` must PASS (every variant carries the caller's seed); discriminating row **M6 keep-derives** (ignore the policy) → the control fails on `seed != 7`.
6. Commit.

**probes:**
- pure-module: `grep -c 'urllib\|subprocess\|sqlite3' pkgs/comfy-worlds/mutate.py` :: le 0 :: the grammar is a pure function; the loop (GN6) does the I/O.

### GN6 (code, S) — the mutator loop: liked renders' prompts through the grammar into the queue

**repo:** media
**dependsOn:** GN2, GN4, GN5
**touches:** pkgs/comfy-worlds/mutate.py, pkgs/comfy-worlds/default.nix, tests/comfy-worlds/test_mutate.py, nixosModules/comfyui-worlds.nix, flake.nix
**acceptance:** comfy-worlds-unit, comfy-worlds-eval, lint
**commit subject:** `generation: comfy-mutate — liked renders' prompts through the grammar into the queue, N per like, on demand (test: comfy-worlds-unit, comfy-worlds-eval, lint)`

**Why.** Sub-project 3 is "prompt mutation from likes" (`sed -n '323,325p' docs/superpowers/specs/2026-09-05-comfy-worlds-design.md`). After GN5 and GN4 the grammar and the likes exist, unconnected: `grep -n 'comfy-mutate' pkgs/comfy-worlds/default.nix nixosModules/comfyui-worlds.nix` → 0 (2026-09-11). The module's units are `wantedBy = []` on-demand user units (`nixosModules/comfyui-worlds.nix:70,93`) and `comfy-worlds-unit` proves every wrapper runs under a bare PATH (`flake.nix:812-828`); the mutator joins both conventions.

**Files.** Modify `pkgs/comfy-worlds/mutate.py` — `main` gains `--world W --root R [--n N] [--dry-run] [--seed S] [--comfy-url U]`: read liked renders (`feed_index.open_db`), load `[mutate]` from `<root>/worlds/<W>/lab/manifest.toml`, mutate, enqueue via `queue.enqueue`, then `queue.run_once` unless `--dry-run`. Modify `pkgs/comfy-worlds/default.nix` — a `comfy-mutate` wrapper (`writeShellApplication`, `runtimeInputs = [ pkgs.python3 ]`, `exec ${pkgs.python3}/bin/python3 ${./mutate.py} "$@"`). Modify `nixosModules/comfyui-worlds.nix` — a `comfy-mutate-<w>.service` per world (oneshot, `wantedBy = []`, `ExecStart = comfy-mutate --world <w> --root <root> --n <cfg.mutate.perLike>`), an option `mutate.perLike` (int, default 3), and `comfy-mutate` on `environment.systemPackages`. Modify `flake.nix` — `comfy-worlds-eval` gains the unit assertions; `comfy-worlds-unit` gains a bare-PATH `comfy-mutate --help` probe beside the `comfy-feed` one (`:826-828`). Modify `tests/comfy-worlds/test_mutate.py` — the loop tests.

**Interfaces.**
1. `comfy-mutate --world W --root R` reads every `likes` row joined to `renders` (prompt, workflow, seed), and for each produces `N = --n` variants via `mutate.mutate(prompt, rules, seed, N)` where `seed` is the render's own seed unless `--seed` overrides it; each variant is enqueued as kind `mutate`, `source` the liked name, its `workflow` the render's (GN1's schema) with exactly these substitutions: every `KSampler` node's `inputs.sampler_name` ← the variant's sampler when not `None`, and `inputs.text` of every `CLIPTextEncode` node equal to the stored prompt ← the variant's prompt (GN4 term 3's rule); `queue.enqueue` pins the seed.
2. `--dry-run` prints one line per variant (`<source> <seed> <sampler> <prompt>`) and writes nothing — the DB is untouched (`jobs` count unchanged), no socket opened.
3. Exit codes: 0 with `mutated K likes into K*N jobs` on stdout; 3 with `no likes in <world>` when the join is empty (not an error, the drill reads it); 2 on `RuleNeverFires` or a missing `[mutate]` table, with the message on stderr.
4. The unit `comfy-mutate-<w>.service` is oneshot, `ConditionUser = operatorUser`, `wantedBy = [ ]`, and `ProtectHome = "read-only"` with `ReadWritePaths = [ "<root>/worlds/<w>" ]` (it writes `feed.sqlite`).
5. `comfy-worlds-eval` asserts, for both units: they exist; `ExecStart` carries `--world sfw` / `--world nsfw` and `--n 3`; `wantedBy == [ ]`; `serviceConfig.ProtectHome == "read-only"`; `serviceConfig.ReadWritePaths == [ "<root>/worlds/<w>" ]`; and `comfy-mutate` on PATH.

**Steps.**
1. **Red.** Add to `test_mutate.py`: `test_loop_enqueues_n_per_like`, `test_dry_run_writes_nothing_and_is_deterministic` (two `--dry-run --seed 1` runs → identical stdout), `test_no_likes_exit_3`, `test_missing_table_exit_2`, `test_variant_sampler_lands_in_every_ksampler` (rules `samplers = ["dpmpp_2m"]`, GN1's two-`KSampler` fixture, the GN2 fake mirror: every body the fake receives has `inputs.sampler_name == "dpmpp_2m"` in node `"3"` **and** node `"10"`; with `samplers` absent the nodes keep `"euler"`). `nix develop -c pytest tests/comfy-worlds/test_mutate.py -q` → 5 failures (`main` rejects `--world`: `unrecognized arguments`). Then add the five eval assertions to `flake.nix` and run `nix build .#checks.x86_64-linux.comfy-worlds-eval -L --no-link` → `error: attribute 'comfy-mutate-sfw' missing`. Paste both reds.
2. Implement terms 1–4; add the wrapper, the option and the units; add the bare-PATH probe to `comfy-worlds-unit`.
3. **Green.** `pytest tests/comfy-worlds -q` all pass; `comfy-worlds-unit` green with `comfy-mutate --help` in the log; `comfy-worlds-eval` green; `lint` green. Paste.
4. **Mutants** (apply, run the named check, paste, revert):
   - **M1 one-per-like**: pass `n=1` regardless of `--n` → `test_loop_enqueues_n_per_like` fails on `count == 6`.
   - **M2 dry-run-writes**: enqueue before checking `--dry-run` → `test_dry_run_writes_nothing_and_is_deterministic` fails on `jobs` count.
   - **M3 exit-0-on-empty**: return 0 with no likes → `test_no_likes_exit_3` fails.
   - **M4 wantedBy-default**: set `wantedBy = [ "default.target" ]` on the unit → `comfy-worlds-eval` fails `eval: comfy-mutate units are on-demand (wantedBy empty)`. **M4b hardening-dropped**: remove `ProtectHome` and `ReadWritePaths` from the unit → `comfy-worlds-eval` fails `eval: comfy-mutate ProtectHome read-only`.
   - **M5 bare-python**: `exec python3 …` in the wrapper → `comfy-worlds-unit` fails: `comfy-mutate needs a binary it does not declare` (`PATH=/no-such-dir`).
   - **M7 sampler-ignored**: drop the `inputs.sampler_name` substitution → `test_variant_sampler_lands_in_every_ksampler` fails: node `"3"` still reads `"euler"`. **M7b sampler-first-only**: substitute the first `KSampler` and `break` → the same test fails on node `"10"`.
5. **Negative control.** `test_dry_run_writes_nothing_and_is_deterministic`'s identical-stdout half must PASS; discriminating row **M6 time-in-output** (print `time.time()` on each line) → the two runs differ and the control fails.
6. Commit.

**probes:**
- mutator-runs-no-model: `grep -c 'openrouter\|anthropic\|llama\|ollama' pkgs/comfy-worlds/mutate.py` :: le 0 :: 17c's rules form; the model phase is not here.

### GN7 (code, S) — the upstream probe's egress crosses the broker

**repo:** media
**dependsOn:** none
**touches:** pkgs/comfy-upstream-probe/probe.py, tests/comfy-upstream-probe/test_probe.py, nixosModules/comfyui-worlds.nix, flake.nix
**acceptance:** comfy-upstream-probe-unit, comfy-worlds-eval, lint
**commit subject:** `generation: the upstream probe refuses direct egress — proxy and CA from its unit, the broker instance the host names (test: comfy-upstream-probe-unit, comfy-worlds-eval, lint)`

**Why.** The probe's `_open` calls `urllib.request.urlopen` directly (`probe.py:93-96`) to six public hosts (question 2), and its unit sets no proxy (`nixosModules/comfyui-worlds.nix:245-268`, no `Environment`). The design claims a carve-out (`design:252-255`) that the cited decision denies: "The media flake stays brokered" (`~/nixos-agent-env/docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md:17-18`). Question 2(a) brokers it, with the pattern next door (Assumption 19).

**Files.** Modify `pkgs/comfy-upstream-probe/probe.py` — `_open` builds an opener from `HTTPS_PROXY` and `SSL_CERT_FILE`, refusing when either is unset; `--dry-run --fixtures` stays offline (the tests monkeypatch `fetch_json`/`fetch_text`, `test_probe.py:9`). Modify `nixosModules/comfyui-worlds.nix` — option `refresh.brokerInstance` (str, default `"media"`), an assertion that the instance exists in `services.egress-broker.instances` when `refresh.enable`, and `Environment = [ "HTTPS_PROXY=http://<hostAddress>:<listenPort>" "SSL_CERT_FILE=/var/lib/egress-broker/<instance>/ca/ca.pem" ]` on the probe unit. Modify `flake.nix` — `comfy-worlds-eval`'s `cRefresh` fixture asserts the two entries (the stub at `checks/eval-harness.nix:45-48` defines instance `media` at `10.100.2.1:3130`); no new `mkNegative` check — the missing-instance refusal is a `builtins.tryEval` inside `comfy-worlds-eval` over a fixture naming `refresh.brokerInstance = "nope"`. Modify `tests/comfy-upstream-probe/test_probe.py` — the refusal tests.

**Interfaces.**
1. `probe._open(url)` reads `HTTPS_PROXY` and `SSL_CERT_FILE`; if either is missing or empty it raises `RuntimeError("comfy-upstream-probe: refusing direct egress — HTTPS_PROXY and SSL_CERT_FILE must name the broker (invariant 3)")` before any socket is opened; if `SSL_CERT_FILE` names a path that does not exist or is not readable (`os.access(path, os.R_OK)` false, or `ssl.create_default_context(cafile=path)` raising `OSError`/`ssl.SSLError`) it raises `RuntimeError("comfy-upstream-probe: SSL_CERT_FILE <path> is not a readable CA bundle")`, also before any socket — never a fallback to the system trust store. With both set and readable, it uses `ProxyHandler({"https": proxy})` and that `ssl` context.
2. `--dry-run --fixtures <dir>` never calls `_open` (unchanged; the fixtures answer), so the unit check stays offline.
3. `services.comfyui-worlds.refresh.brokerInstance` names the instance; when `refresh.enable` the module asserts `config.services.egress-broker.instances ? ${brokerInstance}` with the message `services.comfyui-worlds.refresh.brokerInstance '<name>' has no matching services.egress-broker.instances entry` (the `cowork.nix:156-157` wording).
4. The probe unit's `Environment` carries exactly those two variables; `ReadWritePaths` unchanged (`:261-266`).
5. `refresh.enable = false` renders neither the unit nor the assertion (the existing `mkIf`, `:245`).

**Steps.**
1. **Red.** Add to `test_probe.py`: `test_open_refuses_without_proxy` (env cleared → `RuntimeError`), `test_open_refuses_without_ca`, `test_open_refuses_missing_ca_file` (`SSL_CERT_FILE=<tmp_path>/absent.pem` → the term-1 "not a readable CA bundle" `RuntimeError`; a `chmod 0000` copy of a real PEM likewise), `test_open_builds_proxy_opener` (monkeypatch `urllib.request.build_opener` to capture handlers; assert a `ProxyHandler` with the env's URL is among them and no socket call is made). `nix develop -c pytest tests/comfy-upstream-probe -q` → 4 failures (`DID NOT RAISE`; no `ProxyHandler`). Add the eval assertions and the `"nope"` tryEval → `nix build .#checks.x86_64-linux.comfy-worlds-eval -L --no-link` → `eval: probe unit must carry HTTPS_PROXY`. Paste both.
2. Implement terms 1–5.
3. **Green.** `comfy-upstream-probe-unit`, `comfy-worlds-eval`, `lint` green; the existing sixteen probe tests still pass (`grep -c '^def test_' tests/comfy-upstream-probe/test_probe.py` → 16 at `1618638`). Paste.
4. **Mutants** (apply, run the named check, paste, revert):
   - **M1 proxy-optional**: fall back to a direct opener when `HTTPS_PROXY` is unset → `test_open_refuses_without_proxy` `DID NOT RAISE`.
   - **M2 ca-optional**: default SSL context when `SSL_CERT_FILE` is unset → `test_open_refuses_without_ca` `DID NOT RAISE`. **M2b ca-unchecked**: skip the readability test and hand the path to `ssl` lazily → `test_open_refuses_missing_ca_file` `DID NOT RAISE` (the error would surface only at the first request, inside the timer, as a stack trace).
   - **M3 env-dropped**: remove `Environment` from the unit → `comfy-worlds-eval` fails `eval: probe unit must carry HTTPS_PROXY`.
   - **M4 assertion-dropped**: remove the instance assertion → the `"nope"` tryEval succeeds and `comfy-worlds-eval` fails `eval: unknown brokerInstance must be refused`.
5. **Negative control.** `test_dry_run_targets_the_tags_requirements_not_pypi_latest` (`test_probe.py:105`, existing) must still PASS with a cleared environment — proof the fixtures path never reaches `_open`; discriminating row **M5 fixtures-fetch** (make `fetch_text` call `_open` even under `--fixtures`) → it fails with the term-1 `RuntimeError`.
6. Commit.

**probes:**
- no-direct-urlopen: `grep -c 'urllib.request.urlopen' pkgs/comfy-upstream-probe/probe.py` :: le 0 :: one hit today (probe.py:95, measured 2026-09-14); after the change every request goes through the built opener's open method, so the bare urlopen form is gone.

### GN8 (code, S) — engagement counts posted to Helm's `/v1/engage` on loopback, never content

**repo:** media
**dependsOn:** GN4, EV15
**touches:** pkgs/comfy-worlds/feed.py, tests/comfy-worlds/test_feed.py
**acceptance:** comfy-worlds-unit, lint
**commit subject:** `generation: the feed posts opens, dwell seconds and likes as counts to Helm's /v1/engage on loopback, never content (test: comfy-worlds-unit, lint)`

**Why.** Decision 18b: "a local-only engagement stream, counts never content" (`docs/decisions/2026-09-09-redesign-answers.md`, row 18). The stream has one writer and it is Helm's backend (Assumption 22: EV14 term 1 makes `replace_stream` the verb and "append is not the verb"; the feed unit's sandbox cannot open `/var/lib/evidence` anyway), and the Helm draft assigns the feed-side `POST /v1/engage` to GN (Assumption 23, `helm.md:100`). After GN4 the feed records likes but emits nothing: `grep -c 'engage' pkgs/comfy-worlds/feed.py` → 0 (the seat re-measures). This task posts HM8's body from the server side — the page has no script (GN3 term 5) — and proves no content leaves the process; EV15 stays a dependency so the counts-only class exists before any producer (18b's note; `## Cross-plan`).

**Files.** Modify `pkgs/comfy-worlds/feed.py` — an `Engagement` counter (in-memory: `opens`, `dwell_seconds`, `feed_likes`), incremented by `GET /` (opens), `POST /like` (feed_likes) and a new `POST /dwell` with an integer `seconds` field (dwell is posted by an embedding page or the operator; the feed only counts); `flush()` posts the counters to `--engage-url` (default `http://127.0.0.1:7710/v1/engage`, HM8's route on A16's port, Assumption 23; `''` disables) and resets them; `build_server(root, world, systemctl, port=0, engage_url=None, flush_interval=3600)`; `serve` installs the flush timer and the `SIGTERM` handler. Modify `tests/comfy-worlds/test_feed.py` — the counting, scheduling and privacy tests against an in-file `FakeEngage` (`http.server` on `127.0.0.1:0`, answers `204`, or a configured status, and records every JSON body).

**Interfaces.**
1. A body is exactly `{"counter": <c>, "n": <int ≥ 1>, "surface": "feed"}` with `c` in `("opens", "dwell_seconds", "feed_likes")` — HM8's `COUNTERS` and enum (`helm.md:482,485`), one body per non-zero counter, `Content-Type: application/json`. No other key, ever: no `world`, no name, no prompt, no day (HM8 stamps the day; Evidence keys `(day, surface)`).
2. `flush()` runs (a) every `flush_interval` seconds from a `threading.Timer(flush_interval, tick)` that re-arms itself in `tick` (daemon thread, started by `build_server` when `engage_url` is set), and (b) from `signal.signal(signal.SIGTERM, handler)` installed by `serve`, whose handler flushes, shuts the server down and exits 0. It posts each non-zero counter once with `timeout=5`, then resets all three, and writes one stderr line `engage: posted <k> bodies to <url>`. On `URLError`, `ConnectionError`, `TimeoutError`, `OSError` or any status other than `204`, it writes `engage: <url> unreachable — dropped <sum> counts` (one line, the counters reset, nothing retried, nothing queued — a backlog is state the feed does not keep) and returns; the feed never fails because Helm is absent.
3. `engage_url` must start with `http://127.0.0.1:` or be `None`/`''`; anything else raises `ValueError("feed: engage-url is loopback-only")` in `build_server`, before any thread starts (GN2 term 3's rule).
4. `POST /dwell` accepts `seconds` as a decimal integer in `0..86400` inclusive — `0` and `86400` are accepted, `-1`, `86401` and a non-integer are `400` — and adds it to `dwell_seconds`; answers `204`. No name, prompt or referrer is read from the request.
5. Privacy assertion: `test_engage_body_carries_no_content` drives two `GET /`, one like of a render whose prompt is a marker string, one dwell, then `flush()`, and asserts over every body the fake recorded: `set(body) == {"counter", "n", "surface"}`, `body["surface"] == "feed"`, and none of the marker prompt, the PNG name or the world name appears in `json.dumps(body)`.
6. `engage_url=None` (the default) disables emission: no thread, no handler, no socket — the VM test and every other unit test run so.

**Steps.**
1. **Red.** Add to `test_feed.py`: `test_open_and_like_increment_counters`, `test_dwell_boundaries` (`0`, `86400` → `204`; `-1`, `86401`, `x` → `400`), `test_flush_posts_one_body_per_counter_and_resets` (three bodies after traffic, then a second `flush()` with no traffic posts nothing), `test_engage_body_carries_no_content`, `test_flush_unreachable_drops_quietly` (a closed loopback port, found by bind-and-close → one stderr line, counters zero, no exception), `test_flush_non_204_drops_quietly` (the fake answers `400`), `test_periodic_flush_fires` (`flush_interval=0.2`, one `GET /`, `time.sleep(0.6)` → the fake holds ≥ 1 `opens` body without any explicit `flush()`), `test_sigterm_flushes` (`subprocess.Popen([sys.executable, FEED, "serve", "--world", w, "--root", root, "--port", str(free_port), "--engage-url", fake.url])`, wait for `/healthz`, one `GET /`, `proc.send_signal(signal.SIGTERM)`, `proc.wait(timeout=5)` → `returncode == 0` and the fake holds one `opens` body), `test_engage_url_non_loopback_refused`. `nix develop -c pytest tests/comfy-worlds/test_feed.py -q` → 9 failures: eight on `build_server() got an unexpected keyword argument 'engage_url'`, the subprocess test on `unrecognized arguments: --engage-url` (exit 2). Paste.
2. Implement terms 1–6.
3. **Green.** `pytest tests/comfy-worlds -q` all pass; `comfy-worlds-unit`, `lint` green. Paste. No cross-repo step: the media workspace does not read this repo (the workspace rules); the orchestrator's launch note carries `'engagement' in streams.KINDS` (`## Anticipation`).
4. **Mutants** (apply, `nix develop -c pytest tests/comfy-worlds/test_feed.py -q`, paste, revert):
   - **M1 world-leak**: add `"world": world` to the body → `test_engage_body_carries_no_content` fails on the key set and on the world name.
   - **M2 name-leak**: add `"last_liked": name` → the same test fails on the PNG name.
   - **M3 dwell-unbounded**: drop the range check → `test_dwell_boundaries` gets `204` for `86401`. **M3b off-by-one**: `seconds < 86400` → the same test gets `400` for `86400`.
   - **M4 no-reset**: skip the reset after a post → `test_flush_posts_one_body_per_counter_and_resets` finds a fourth body after the second flush.
   - **M5 catch-narrow**: catch `ConnectionRefusedError` only and re-raise the rest → `test_flush_non_204_drops_quietly` fails with `HTTPError`.
   - **M7 timer-never-armed**: drop the re-arm in `tick` (or never start the first `Timer`) → `test_periodic_flush_fires` fails on `0 bodies`. **M7b no-sigterm**: drop `signal.signal` → `test_sigterm_flushes` fails: `returncode == -15` and no body.
   - **M8 any-host**: drop the loopback prefix check → `test_engage_url_non_loopback_refused` `DID NOT RAISE`.
5. **Negative control.** `test_open_and_like_increment_counters` must PASS (`opens == 2, feed_likes == 1` after two GETs and one like, read from the fake's bodies after one `flush()`); discriminating row **M6 count-never** (never increment) → it fails: no body posted.
6. Commit.

**probes:**
- counter-names: `grep -c '"dwell_seconds"' pkgs/comfy-worlds/feed.py` :: ge 1 :: HM8's counter name (helm draft :482), not EV15's dwell_s — the API maps; the key set itself is proven by the M1/M2 test, not by grep.
- no-store-write: `grep -c '/var/lib/evidence' pkgs/comfy-worlds/feed.py` :: le 0 :: the feed never opens the store — Helm's backend is the writer (Assumption 22) and the unit's sandbox forbids it anyway.
- sigterm-handled: `grep -c 'signal.SIGTERM' pkgs/comfy-worlds/feed.py` :: ge 1 :: term 2 (b) exists in the source; the subprocess test proves it works.

### GN9 (docs, S) — the worlds runbook and the acceptance script for the loop

**repo:** media
**dependsOn:** GN2, GN3, GN4, GN6, GN7
**touches:** docs/runbooks/media.md, tests/acceptance/media-worlds.sh, README.md
**acceptance:** lint
**commit subject:** `generation: worlds runbook and acceptance drill for the feed, the queue, the mutator and the brokered probe (test: lint)`

**Why.** The runbook (`docs/runbooks/media.md`, 405 lines, twelve `## ` sections — `grep -c '^## '` → 12 at `1618638`) knows nothing of the feed's verbs, the queue, `comfy-mutate` or the probe's proxy. The drill `tests/acceptance/media-worlds.sh` has eight steps (`grep -c '^step "'` → 8), two of them Caddy steps (6, 7) that Assumption 20 turns off, and a `--self-test` mode `lint` shellchecks (`flake.nix:305-307`). 70b composes one drill per increment from these lines; GN10 pins the rev this task lands, so the rev carries its own instructions.

**Files.** Modify `docs/runbooks/media.md` — `## The feed, the queue and the mutator` (the page, the three verbs, `/jobs`, `comfy-feed index --rebuild`, `comfy-feed queue --run-once`, `comfy-mutate --dry-run`, the `[mutate]` table with one example) and `## The probe crosses the broker` (the two variables, what a refusal looks like, reading the broker log for `api.github.com`); the LAN section gains "off on core in increment 3; Isolation flips `lan.enable` in increment 4". Modify `tests/acceptance/media-worlds.sh` — steps 6 and 7 `skip` when `COMFY_LAN=off` (default), and steps 9–13: `/healthz` on loopback, the page lists a prompt, like → one `likes` row, regenerate → one `jobs` row with a different seed, `comfy-mutate --dry-run --seed 1` twice byte-identical, `comfy-upstream-probe --dry-run` with the unit's env → 0 and without → 1 with the invariant-3 message. Modify `README.md` — `comfy-mutate` and the feed's routes.

**Interfaces.**
1. Every new drill step follows the file's `step`/`pass`/`fail`/`skip` functions (`:38-64`) and is resolvable under `--self-test` (`command -v` for `sqlite3`, `curl`, `comfy-mutate`, `comfy-upstream-probe`; `test -e` for `feed.sqlite`).
2. Each step's failure text names what to read: the runbook section and the unit's journal line.
3. The runbook's commands are copy-pasteable and every one is a command a later task or the drill runs — no prose-only claim of behaviour.
4. `README.md`'s check table is unchanged in count (21 checks; `nix eval` per Assumption 3) — this task adds no check.

**Steps.**
1. **Red.** `nix develop -c bash tests/acceptance/media-worlds.sh --self-test 2>&1 | grep -c '^FAIL\|^PASS\|^SKIP'` → 8 (paste). Add the five steps and the `COMFY_LAN` skip; `nix develop -c shellcheck tests/acceptance/media-worlds.sh` passes or its line is the red. The docs red: `grep -c 'comfy-mutate' docs/runbooks/media.md README.md` → `0` and `0`. Paste both.
2. Write the two runbook sections and the README lines.
3. **Green.** `--self-test` now prints 13 step lines (`grep -c` → 13); `grep -c '^## ' docs/runbooks/media.md` → 14 (twelve plus the two sections); `grep -c 'comfy-mutate' docs/runbooks/media.md README.md` → both ≥ 1; `nix build .#checks.x86_64-linux.lint -L --no-link` green (treefmt over Markdown, shellcheck over the drill). Paste.
4. **Mutants** (a docs task's mutants are edits that the drill or `lint` refuses):
   - **M1 lan-steps-live**: remove the `COMFY_LAN` skip → `--self-test` on a host without Caddy reports `FAIL` for steps 6 and 7 instead of `SKIP` (paste the two lines).
   - **M2 unquoted-var**: write `$ROOT/worlds/$w/feed.sqlite` unquoted in step 10 → `lint` fails on shellcheck SC2086.
   - **M3 determinism-step-vacuous**: make step 12 compare the first run to itself → the seat proves the step discriminates by running it against GN6's **M6 time-in-output** build and pasting the `FAIL`.
5. **Negative control.** Step 9 must print `PASS` under `--self-test` on a tree where `curl` resolves (`--self-test` resolves `command -v`/`test -e` only, `:59-64`, so a port can never make it fail); discriminating row **M4 no-curl**: `env PATH=/no-such-dir bash tests/acceptance/media-worlds.sh --self-test` → step 9 prints `FAIL`, proving the line measures resolvability and not nothing. The port is proven by the drill's real run (`## Operator` step 5), not here.
6. Commit.

**probes:**
- drill-steps: `grep -c '^step "' tests/acceptance/media-worlds.sh` :: le 13 :: eight before, five added.
- drill-steps-floor: `grep -c '^step "' tests/acceptance/media-worlds.sh` :: ge 13 :: the same measurement bounded from below — the count is exact
- runbook-names-mutator: `grep -c 'comfy-mutate' docs/runbooks/media.md` :: ge 3 :: the command, the dry-run and the unit each appear.
- runbook-sections: `grep -c '^## ' docs/runbooks/media.md` :: ge 14 :: twelve at 1618638 plus the two this task writes.

### GN10 (code, M) — the host wires the worlds: media input, on-demand units, backup paths, the LAN face off

**dependsOn:** GN9
**areas:** platform, knowledge, isolation
**touches:** flake.nix, flake.lock, hosts/core/default.nix, hosts/core/media-worlds.nix, hosts/core/proton-backup.nix, hosts/core/lanes.nix, hosts/core/helm.nix, docs/runbooks/backup.md
**acceptance:** host-core, core-backup-wiring, core-media-wiring, lint
**commit subject:** `generation: the media flake is an input; two ComfyUI worlds' on-demand units, their lab backup paths, the probe's broker instance, the LAN face off (test: host-core, core-backup-wiring, core-media-wiring, lint)`

**Why.** Host integration does not exist (Assumption 4, re-measured 2026-09-14: no input, `git ls-files hosts/core | grep -c media` → 0, `helm.nix:12-13` says media stays out). Decision 16b requires "the worlds' on-demand user units plus host-level Caddy wired into core, no specialisation"; WH1 typed this at `~/flakes/media/docs/superpowers/plans/2026-09-05-comfy-worlds.md:979-1037` in a heading the parser drops (Assumption 12). This task is WH1 under the grammar, with three deltas: `lan.enable = false` (Assumption 20), the probe's broker instance in `lanes.nix` (question 2), and `inputs.nixpkgs.follows = "nixpkgs-host"` because the two locks differ today (Assumption 17). **Scope of the instance:** the `media` broker instance carries only the probe's six hosts here; ComfyUI's and `media-fetch-models`' own egress (`huggingface.co`, the Docker registries the media stub lists, Assumption 18) is out of this task — the task that wires model fetches through the broker amends this `allow` list and the `host-core` assertion that pins it.

**Files.** Modify `flake.nix` — input `media.url = "git+file:///home/dalhaka/flakes/media?ref=main"` with `inputs.nixpkgs.follows = "nixpkgs-host"`; `media.nixosModules.comfyui-worlds` in `nixosConfigurations.core.modules`; `host-core` assertions; a new `core-media-wiring` check beside `core-gaming-wiring` (`:3034`). Modify `flake.lock` — the `media` node (`nix flake update media`). Create `hosts/core/media-worlds.nix`, verbatim:

```nix
{ config, ... }:
{
  # ComfyUI worlds (GN10). Only each world's lab/ is backed up. LAN face off
  # in increment 3 (Assumption 20); Isolation flips lan.enable in increment 4.
  services.comfyui-worlds = {
    enable = true;
    operatorUser = "dalhaka";
    root = "/home/dalhaka/comfyui";
    worlds = {
      sfw = { comfyPort = 8188; feedPort = 8288; host = "sfw.core.lan"; };
      nsfw = { comfyPort = 8189; feedPort = 8289; host = "nsfw.core.lan"; };
    };
    lan.enable = false;
    refresh = {
      enable = true;
      brokerInstance = "media";
      hostDriver = config.hardware.nvidia.package.version;
    };
  };
  # A missing restic path makes restic-backups-core-local exit 3 nightly.
  systemd.tmpfiles.rules = [
    "d /home/dalhaka/comfyui 0755 dalhaka users -"
    "d /home/dalhaka/comfyui/worlds 0755 dalhaka users -"
    "d /home/dalhaka/comfyui/worlds/sfw 0755 dalhaka users -"
    "d /home/dalhaka/comfyui/worlds/sfw/lab 0755 dalhaka users -"
    "d /home/dalhaka/comfyui/worlds/nsfw 0755 dalhaka users -"
    "d /home/dalhaka/comfyui/worlds/nsfw/lab 0755 dalhaka users -"
  ];
}
```

(`host` is a required option of the `worlds` submodule, `nixosModules/comfyui-worlds.nix:155-158`, unused while `lan.enable` is false.) Modify `hosts/core/default.nix:4-16` — `./media-worlds.nix` in `imports`. Modify `hosts/core/proton-backup.nix:29-41` — `"/home/dalhaka/comfyui/worlds/sfw/lab"` and `"/home/dalhaka/comfyui/worlds/nsfw/lab"` appended to `paths`. Modify `hosts/core/lanes.nix` — the block its `:6` comment reserves: `services.egress-broker.instances.media = { hostAddress = "10.100.2.1"; namespaceAddress = "10.100.2.2"; listenPort = 3130; allow = [ "api.github.com" "download.nvidia.com" "github.com" "pypi.org" "raw.githubusercontent.com" "www.nvidia.com" ]; };` (question 2's six, sorted; the stub's addresses, Assumption 18). Modify `hosts/core/helm.nix:12-13` — the comment now reads "media's worlds are wired by media-worlds.nix (GN10); no profile". Modify `docs/runbooks/backup.md` — the two paths (`core-backup-wiring` refuses an undocumented path, `flake.nix:3021-3022`).

**Interfaces.**
1. `nixosConfigurations.core` evaluates with `services.comfyui-worlds.enable = true`, both worlds at `8188/8288` and `8189/8289`, `lan.enable = false`, `refresh.enable = true`, `refresh.brokerInstance = "media"`.
2. `host-core` gains (the WH1 list minus Caddy): `c.services.comfyui-worlds.enable`; both worlds with those ports; both lab paths in `c.services.proton-backup.paths`; the stanza's six tmpfiles rules, each by its literal; `c.systemd.user.targets ? "comfy-world-sfw"`; `c.systemd.user.services ? "comfy-mutate-sfw"`; `c.services.comfyui-worlds.refresh.hostDriver != null`; `c.services.egress-broker.instances.media.allow == [ "api.github.com" "download.nvidia.com" "github.com" "pypi.org" "raw.githubusercontent.com" "www.nvidia.com" ]` (list equality — order and length).
3. `core-media-wiring` (created here), a `throw` chain in the shape of `core-gaming-wiring` (`flake.nix:3065,3084-3086,3108-3109`), inlined: `let lockData = builtins.fromJSON (builtins.readFile ./flake.lock); mediaNode = lockData.nodes.media.locked; mediaNixpkgsNodeName = lockData.nodes.media.inputs.nixpkgs; mediaNixpkgsRev = lockData.nodes.${mediaNixpkgsNodeName}.locked.rev; hostNixpkgsRev = lockData.nodes.nixpkgs-host.locked.rev; in if mediaNode.url or "" != "git+file:///home/dalhaka/flakes/media" then throw "core-media-wiring: flake.lock's media node is not the sibling clone" else if builtins.match "[0-9a-f]{40}" mediaNode.rev == null then throw "core-media-wiring: media node has no 40-hex rev" else if mediaNixpkgsRev != hostNixpkgsRev then throw "core-media-wiring: flake.lock's media-input nixpkgs (${mediaNixpkgsRev}) is not the same rev as nixpkgs-host (${hostNixpkgsRev})" else …`; asserts `!(c.services.caddy.enable or false)` and `c.services.comfyui-worlds.lan.enable == false` with the message `core-media-wiring: the LAN face is Isolation's increment-4 flip; lan.enable must be false here`; asserts Caddy is not in the broker's group (WH1's throw text, `:1035`) — vacuous while Caddy is off, kept for the flip; asserts the probe unit's `serviceConfig.Environment` contains `HTTPS_PROXY=http://10.100.2.1:3130`.
4. `core-backup-wiring` stays green: both new paths appear in `docs/runbooks/backup.md`.
5. Nothing here starts a unit; every world unit is `wantedBy = []`; the timer is installed, not started (`## Operator`).

**Steps.**
1. **Red.** Add the `host-core` assertions from term 2 → `nix build .#checks.x86_64-linux.host-core -L --no-link` → `error: attribute 'comfyui-worlds' missing`. Add `core-media-wiring` → `nix build .#checks.x86_64-linux.core-media-wiring -L --no-link` → `error: attribute 'media' missing` (no lock node). Add the two paths to `proton-backup.nix` only → `core-backup-wiring` → `docs/runbooks/backup.md does not name these backup paths: /home/dalhaka/comfyui/worlds/sfw/lab …`. Paste all three.
2. Add the input and `nix flake update media`; `git add flake.lock`; write `media-worlds.nix`, the import, the lanes instance, the runbook lines, the helm comment. `nix eval .#nixosConfigurations.core.config.services.comfyui-worlds.refresh.brokerInstance` → `"media"`.
3. **Green.** `host-core`, `core-backup-wiring`, `core-media-wiring`, `lint` all green; `nix build .#nixosConfigurations.core.config.system.build.toplevel -o /tmp/gn10-result` and `nix store diff-closures /run/current-system /tmp/gn10-result` — the diff shows `comfy-feed`, `media-comfy`, `comfy-worlds-init`, `comfy-world-guard`, `comfy-mutate`, `comfy-upstream-probe`, the ComfyUI closure, **and no `caddy`**; paste the diff in the commit body.
4. **Mutants** (apply, run the named check, paste, revert):
   - **M1 lan-on**: `lan.enable = true` in `media-worlds.nix` → `core-media-wiring` fails with the term-3 LAN message.
   - **M2 nixpkgs-unfollowed**: drop `inputs.nixpkgs.follows` and re-lock → `core-media-wiring` fails: `media's nixpkgs … != nixpkgs-host …` (the check's message names both revs).
   - **M3 allow-open**: add `"huggingface.co"` to the instance's `allow` → `host-core` fails on the exact six-host list. **M3b ports-swapped**: `feedPort = 8289` on `sfw` and `8288` on `nsfw` → `host-core` fails on the per-world port assertion (`sfw.feedPort == 8288`).
   - **M4 path-undocumented**: remove one lab path from `backup.md` → `core-backup-wiring` fails naming the path.
   - **M5 caddy-in-group**: set `systemd.services.caddy.serviceConfig.SupplementaryGroups = [ "egress-broker" ]` in `media-worlds.nix` → `core-media-wiring` fails with WH1's group message (proves the guard is live even with Caddy's service otherwise unconfigured).
5. **Negative control.** `core-gaming-wiring` must still PASS (`nix build .#checks.x86_64-linux.core-gaming-wiring -L --no-link`); discriminating row **M6 host-rev-drift**: hand-edit `flake.lock`'s `nixpkgs-host` `rev` by one hex digit → it fails on the gaming lock-node assertion, proving the lock-reading pattern GN10 copies is a real check. Restore the lock byte-exactly (`git checkout flake.lock` then redo Step 2's `nix flake update media` if needed).
6. Commit. Then the `## Operator` line: **switch #N** — `sudo nixos-rebuild switch --flake .#core`; acceptance: drill steps 1–9; rollback: the previous generation.

**probes:**
- no-caddy-in-closure: `nix store diff-closures /run/current-system /tmp/gn10-result | grep -c caddy` :: le 0 :: Assumption 20 in one number.
- media-lock-node: `python3 -c "import json;print(json.load(open('flake.lock'))['nodes']['media']['locked']['rev'])" | wc -c` :: le 41 :: a 40-hex rev plus newline.
- media-lock-node-floor: `python3 -c "import json;print(json.load(open('flake.lock'))['nodes']['media']['locked']['rev'])" | wc -c` :: ge 41 :: the same measurement bounded from below — the count is exact

### GN11 (code, M) — media absorbed: the subtree merge, the input retired, the ledgers

**dependsOn:** GN8, GN10, EV10
**areas:** platform, evidence, generation
**touches:** flake.nix, flake.lock, hosts/core/media-worlds.nix, docs/ledger/subsystems.toml, docs/ledger/repos.toml, docs/ledger/plan-status.toml, docs/subsystems.md
**acceptance:** host-core, core-media-wiring, subsystems-manifest, lint
**commit subject:** `generation: ~/flakes/media absorbed by subtree merge under media/ — the input retired, the modules imported in-tree, the row owns it (test: host-core, core-media-wiring, subsystems-manifest, lint)`

**Why.** The charter names "media absorbed" for this increment (`:179-180`) and retires the sibling repos once absorbed (`:65`); 35b/44/48a: one repo, each sibling absorbed by a true subtree merge with its own gate and switch. After GN10 media is an input; Generation owns nothing (Assumption 5), so the landed subtree is uncovered until this task's `owns` line. Platform's absorption sits under `pkgs/dsh-harness/*`, so no layout precedent binds; this plan chooses `media/`. The merge is Assumption 21's landing act, not this commit.

**Base** (verified before Step 1, else the seat stops with `status=partial`): `test -d media/nixosModules && git merge-base --is-ancestor 16186388126ee80b290381d7230ae90047dbfa56 HEAD` → exit 0 (the subtree is in the tree and W6c's hash is reachable — a true merge, not `--squash`, 48a); `git -C ~/flakes/media tag -l 'absorbed/media-*'` non-empty; paste all three. **The seat's paste is a courtesy, not the guard**: what gates is the commit-time re-assertion — Interface 1 and the probe `w6c-reachable` below, which the gate re-runs against the task branch (G11; the gate re-runs every probe) — so a seat that claims the Base and lacks the merge is refused at the gate, never trusted on its report (charter: the seat's self-report is not the signal).

**Files.** Modify `flake.nix` — drop the `media` input; `nixosConfigurations.core.modules` imports `./media/nixosModules/comfyui-worlds.nix`; `core-media-wiring` amended: `!(lockData.nodes ? media)` replaces the lock-node assertions, the nixpkgs-rev assertion becomes `media/flake.lock`'s `nixpkgs` rev `== nixpkgs-host` (kept until GN12 deletes that lock, when the assertion goes too). Modify `flake.lock` — the `media` node gone (`nix flake lock`). Modify `hosts/core/media-worlds.nix` — `refresh.repo = "/home/dalhaka/nixos-agent-env/media"` (the probe's `--repo`; default `/home/dalhaka/flakes/media`, `comfyui-worlds.nix:197-201`). Modify `docs/ledger/subsystems.toml` — the GN row's `owns = [ "media/*" ]` (`*` spans `/` under the validator's `fnmatch`, the file's convention) and `plans` gaining `media/docs/superpowers/plans/2026-09-05-comfy-worlds.md`; `subsystems.py write` regenerates `docs/subsystems.md`. Modify `docs/ledger/repos.toml:10-12` — the `media` row becomes, PL6's shape exactly: `name = "media"`, `path = "~/nixos-agent-env"`, `plans = "media/docs/superpowers/plans/*.md"`, comment `# absorbed 2026-09-xx under media/ (GN11, tag absorbed/media-<rev>); the sibling clone is archived by the operator` — the row reads the media plans from the subtree and the W-series keys resolve `landed` against this repo's history, whose merge made their commits reachable. Modify `docs/ledger/plan-status.toml` — the two media rows (`:151-155` `2026-09-02-media-flake.md`, superseded; `:157-161` `2026-09-02-media-nix-native.md`, done; `grep -n 'repo = "media"'` → `:152`, `:158`) gain `note` text "absorbed under media/ by GN11; landed keys frozen as history (41a)", plus one `[[plan]]` row `repo = "media"`, `file = "2026-09-05-comfy-worlds.md"`, `status = "done"`, `note = "W1–W6c landed; WH1 superseded by GN10, WH2 deferred to Helm (question 3)"`.

**Interfaces.**
1. The Base line holds at Step 1 and at commit: `git merge-base --is-ancestor 16186388126ee80b290381d7230ae90047dbfa56 HEAD` → 0.
2. `nix flake metadata --json | jq '.locks.nodes | has("media")'` → `false`.
3. `nix eval .#nixosConfigurations.core.config.services.comfyui-worlds.enable` → `true` from the in-tree module; the closure is unchanged: `nix build …toplevel -o /tmp/gn11-result && nix store diff-closures /tmp/gn10-result /tmp/gn11-result` → empty for every media package (the same source at the same nixpkgs).
4. `nix develop -c python3 pkgs/evidence/subsystems.py validate --root . docs/ledger/subsystems.toml` → exit 0; `--counts` shows `Generation: <N>` with `N == $(git ls-files media | wc -l)`.
5. `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → exit 0 and `json` shows the media row with `landed: 11` (W1–W6c, read from `media/docs/superpowers/plans/` and resolved against this repo's history); G9's refusal exempts landed keys; they carry no `GN` prefix so G7 does not fire.
6. `media/flake.nix` still evaluates on its own (`nix flake check` from `media/` is *not* required — GN12 retires it); `~/flakes/media` is untouched.

**Steps.**
1. **Red.** Amend `core-media-wiring` first (term 3's lock assertions) → `nix build .#checks.x86_64-linux.core-media-wiring -L --no-link` → `core-media-wiring: flake.lock still carries a media node`. Then, with the subtree in the tree and the GN row still `owns = []`: `nix develop -c python3 pkgs/evidence/subsystems.py validate --root . docs/ledger/subsystems.toml` → `uncovered: media/flake.nix` and one line per subtree file, exit 1. Paste both.
2. Drop the input; import the module in-tree; `nix flake lock`; set `refresh.repo`; write the manifest, repos and plan-status rows; `subsystems.py write`.
3. **Green.** `host-core`, `core-media-wiring`, `subsystems-manifest`, `lint` green; term 3's `diff-closures` empty for media; `validate --counts` → `Generation: N` with `N == $(git ls-files media | wc -l)`; `tasks.py check` exit 0 and `json` → media `landed: 11`. Paste all.
4. **Mutants** (apply, run the named check, paste, revert):
   - **M1 input-kept**: re-add the `media` input and lock → `core-media-wiring` fails `still carries a media node`.
   - **M2 owns-narrow**: `owns = [ "media/pkgs/*" ]` → `subsystems-manifest` fails with `uncovered: media/flake.nix …` lines.
   - **M3 owns-overlap**: add `"media/*"` to Platform's row too → `subsystems-manifest` fails on a path matching two rows (`subsystems.py:5-6`'s rule).
   - **M4 path-kept**: leave the `media` row's `path = "~/flakes/media"` → the record dies with the sibling: `python3 pkgs/evidence/tasks.py --root . --repos <scratch>/repos.toml json` with that row's path pointed at a missing directory → the media row lists **zero** tasks (`Counter()`; measured 2026-09-14 against `~/factory/archive/media-none`), where the repointed row reads `landed: 11`.
   - **M5 repo-default**: drop `refresh.repo` → `host-core` (amended here to assert `--repo /home/dalhaka/nixos-agent-env/media` in the probe's `ExecStart`) fails on the `/home/dalhaka/flakes/media` default.
5. **Negative control.** `core-backup-wiring` must still PASS (untouched here); discriminating row **M6 path-drop**: remove one lab path from `proton-backup.nix` (a file not in this task's touches — done as a scratch mutant only, reverted before commit) → it fails on `paths` vs `backup.md`.
6. Commit. Then the `## Operator` line: **switch #N+1** — acceptance: drill steps 10–12; rollback: this commit reverted, `git revert -m 1 <landing merge>`, and the previous generation.

**probes:**
- subtree-files: `git ls-files media | wc -l` :: ge 97 :: Assumption 2's count plus this plan's additions.
- w6c-reachable: `git merge-base --is-ancestor 16186388126ee80b290381d7230ae90047dbfa56 HEAD && echo 1 || echo 0` :: ge 1 :: the landing merge kept every cited hash (48a); the Base line at commit time.
- media-row-repointed: `grep -c 'plans = "media/docs/superpowers/plans/\*.md"' docs/ledger/repos.toml` :: ge 1 :: PL6's row shape (Cross-plan).

### GN12 (code, M) — media's packages and checks become host-flake outputs on nixpkgs-host

**dependsOn:** GN11
**areas:** platform, generation
**touches:** flake.nix, media/flake.nix, media/flake.lock, media/checks.nix, media/packages.nix
**acceptance:** comfy-worlds-unit, comfy-worlds-eval, media-fetch-unit, comfy-upstream-probe-unit, lint
**commit subject:** `generation: media's packages and checks are host-flake outputs on nixpkgs-host; media/flake.nix retired (test: comfy-worlds-unit, comfy-worlds-eval, media-fetch-unit, comfy-upstream-probe-unit, lint)`

**Why.** After GN11 the subtree carries its own `media/flake.nix` (892 lines at `1618638`) with 5 packages and 21 checks no gate here runs — `nix eval .#checks.x86_64-linux --apply builtins.attrNames | grep -c comfy` → 0 (the seat re-measures). 43b puts absorbed subsystems on `nixpkgs-host`; a second flake in the tree is a second lock to drift. The four named checks guard everything GN1–GN8 landed; they run here or the loop is ungated.

**Files.** Create `media/packages.nix` — exactly the five names media's `packages.${system}` block publishes (`media flake.nix:126-130`): `{ pkgs }: let worldsPkgs = import ./pkgs/comfy-worlds { inherit pkgs; }; in { media-fetch-models = pkgs.writeShellApplication { name = "media-fetch-models"; runtimeInputs = [ pkgs.python3 ]; text = ''exec python3 ${./pkgs/media-fetch/fetch.py} "$@"''; }; comfyui = import ./pkgs/comfyui/package.nix { inherit pkgs; }; inherit (worldsPkgs) comfy-worlds-init media-comfy comfy-upstream-probe; }` — not the whole `worldsPkgs` set (`comfy-feed`, the guards and `comfy-mutate` stay module-internal). Create `media/checks.nix` — `{ pkgs, lib, self, nixpkgs, system }:` returning **these 21 attrs** (media `nix eval … checks.x86_64-linux`, `1618638`; `lint` renamed `media-lint`, term 6): `comfy-upstream-probe-unit comfy-worlds-assertion-negative-{hosts,name,password-path,ports} comfy-worlds-eval comfy-worlds-unit comfy-worlds-vm comfyui-assertion-negative-{broker,gpu,listen,listen-address,token} comfyui-cliploader-krea2 comfyui-eval comfyui-package comfyui-startup-clean comfyui-vm media-lint media-fetch-bats media-fetch-unit`, moved verbatim from `media/flake.nix:301-870` with its `let` helpers carried across: `lintTools = with pkgs; [ treefmt nixfmt-rfc-style shfmt shellcheck statix deadnix ruff ]` (`:20-28`), `pyEnv = pkgs.python3.withPackages (ps: [ ps.pytest ])` (`:32`), `mkHarness = module: import ./checks/eval-harness.nix { inherit nixpkgs system module; }` (`:37`), `harness = mkHarness self.nixosModules.default; worldsHarness = mkHarness self.nixosModules.comfyui-worlds` (`:38-39`, rewritten to the modules by path: `mkHarness (import ./nixosModules)` and `mkHarness (import ./nixosModules/comfyui-worlds.nix)`), `mkNegativeWith = h: name: extra: expect: …` (`:80-98`, verbatim) and `mkNegative = mkNegativeWith harness` (`:99`), `worldsPkgs = import ./pkgs/comfy-worlds { inherit pkgs; }` (`:117`). `${self}` occurs on nine lines (`grep -c '\${self}' media/flake.nix` → 9 at `1618638`); each is rewritten `${self}/media/…` — the seat pastes the nine before/after lines. Modify `flake.nix` — **introduce** `pkgsHost = import nixpkgs-host { inherit system; config.allowUnfree = true; };` in the outputs `let` beside `pkgs = nixpkgs.legacyPackages.${system};` (`:40`; no `pkgsHost` exists today — `grep -n pkgsHost flake.nix` → nothing, 2026-09-14; `allowUnfree` because torch-bin pulls `triton-bin`, media `flake.nix:10-18`); `packages.${system}` gains `(import ./media/packages.nix { pkgs = pkgsHost; })` and `checks.${system}` gains `(import ./media/checks.nix { pkgs = pkgsHost; lib = pkgsHost.lib; nixpkgs = nixpkgs-host; inherit self system; })`; `core-media-wiring` loses the `media/flake.lock` nixpkgs assertion (the lock is gone). Delete `media/flake.nix` and `media/flake.lock` (`git rm`). `docs/MAP.md` regenerated under its exemption (G5): `nix develop -c python3 pkgs/evidence/repomap.py --root . write`.

**Interfaces.**
1. `nix eval .#checks.x86_64-linux --apply 'a: builtins.length (builtins.filter (n: builtins.match "(comfy|media).*" n != null) (builtins.attrNames a))'` → 21 (Assumption 3's count; the seat re-measures against `media/flake.nix`'s attr list before deleting it and pastes both numbers).
2. `nix eval .#packages.x86_64-linux --apply builtins.attrNames` includes exactly `comfy-upstream-probe`, `comfy-worlds-init`, `comfyui`, `media-comfy`, `media-fetch-models` beyond today's names (before/after counts differ by 5).
3. Every media check evaluates against `pkgsHost` only: the probes `checks-on-host-nixpkgs` (≥ 1 reference to `nixpkgs-host`'s `python3`) and `checks-off-eval-nixpkgs` (0 references to `nixpkgs`'s) below, both read from `nix derivation show` of `comfy-worlds-unit`.
4. `test ! -e media/flake.nix && test ! -e media/flake.lock`.
5. The four acceptance checks are green **here**; `core-media-wiring` green; the core closure is unchanged: `nix store diff-closures /tmp/gn11-result /tmp/gn12-result` empty (build-only, the `## Operator` line's third clause).
6. This flake's `lint` and media's collide — `media/checks.nix` renames media's to `media-lint`; `nix eval … attrNames` before and after → after equals before + 21 (no other duplicate).

**Steps.**
1. **Red.** Add the `checks.${system}` import line naming `./media/checks.nix` before the file exists → `nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link` → `error: path '/nix/store/…/media/checks.nix' does not exist`. Paste.
2. Write `media/packages.nix` and `media/checks.nix`; wire both into `flake.nix`; `git rm media/flake.nix media/flake.lock`; amend `core-media-wiring`; regenerate `docs/MAP.md`.
3. **Green.** `nix build .#checks.x86_64-linux.{comfy-worlds-unit,comfy-worlds-eval,media-fetch-unit,comfy-upstream-probe-unit,lint} -L --no-link` all green; term 1's count → 21; term 5's `diff-closures` empty. `lint` covers MAP currency (`flake.nix:1391-1393` at `4068f86`; G5's quoted `:1081-1086` is program.md's stale anchor) and ruff over `media/`. Paste.
4. **Mutants** (apply, run the named check, paste, revert):
   - **M1 wrong-nixpkgs**: pass `pkgs` (the `nixpkgs` set) instead of `pkgsHost` → probe `checks-on-host-nixpkgs` reads 0 and `checks-off-eval-nixpkgs` reads ≥ 1; paste both numbers (a probe, not a check, kills it — the gate re-runs probes).
   - **M2 stale-self-path**: leave one `${self}/pkgs/comfy-worlds` unrewritten → `comfy-worlds-unit` fails `cp: cannot stat '…/pkgs/comfy-worlds'`.
   - **M3 lint-collision**: keep media's check named `lint` → `nix flake show` errors on the duplicate attribute (`error: attribute 'lint' already defined`).
   - **M4 lock-kept**: leave `media/flake.lock` in place → `lint` fails on MAP currency (the map lists a file the layout retired) — if `repomap.py` does not list lock files, the seat substitutes probe `no-inner-flake` below as the killer and says so.
   - **M5 map-stale**: skip the MAP regeneration → `lint` fails on `docs/MAP.md is not current`.
5. **Negative control.** `comfy-worlds-eval` must PASS from the host flake with the stub broker (`media/checks/stub-broker.nix`); discriminating row **M6 stub-dropped**: remove the stub import from `eval-harness.nix` → it fails `option services.egress-broker does not exist`.
6. Commit.

**probes:**
- no-inner-flake: `git ls-files media | grep -c '^media/flake\.'` :: le 0 :: the subtree has no flake of its own.
- media-checks-count: `nix eval .#checks.x86_64-linux --apply 'a: builtins.length (builtins.filter (n: builtins.match "(comfy|media).*" n != null) (builtins.attrNames a))'` :: le 21 :: Assumption 3's surface, now here.
- media-checks-count-floor: `nix eval .#checks.x86_64-linux --apply 'a: builtins.length (builtins.filter (n: builtins.match "(comfy|media).*" n != null) (builtins.attrNames a))'` :: ge 21 :: the same measurement bounded from below — the count is exact
- checks-on-host-nixpkgs: `nix derivation show "$(nix eval --raw .#checks.x86_64-linux.comfy-worlds-unit.drvPath)" | grep -c "$(nix eval --raw --impure --expr '(builtins.getFlake (toString ./.)).inputs.nixpkgs-host.legacyPackages.x86_64-linux.python3.outPath')"` :: ge 1 :: the check's inputs reference the host set's python3 (43b).
- checks-off-eval-nixpkgs: `nix derivation show "$(nix eval --raw .#checks.x86_64-linux.comfy-worlds-unit.drvPath)" | grep -c "$(nix eval --raw --impure --expr '(builtins.getFlake (toString ./.)).inputs.nixpkgs.legacyPackages.x86_64-linux.python3.outPath')"` :: le 0 :: and none from this flake's default set — the pair kills M1.

