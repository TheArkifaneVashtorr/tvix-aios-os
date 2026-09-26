# Plan 2026-09-11 — Isolation (increment 4: LAN access with per-site auth, the overlay typed, the OAuth/router outcome, the invariants named)

**Plan file:** `docs/superpowers/plans/2026-09-11-isolation.md` — pre-authorized as the second entry of Isolation's `plans` list (`docs/ledger/subsystems.toml:48-51`, added by `1ae7328`), so `IS` keys typed here pass the reserved-prefix refusal (`pkgs/evidence/tasks.py:1835-1849`).

**Charter:** `docs/concepts/2026-09-09a-redesign-charter.md` §2 (the Isolation row: area `isolation`, Opus gate, first-spec answers 11, 20, 44, 57, 72) and §6 **increment 4**. **Decisions:** `docs/decisions/2026-09-09-redesign-answers.md` rows 7, 11, 20, 44, 49, 54, 55, 57, 63, 70, 72, 80; the §4 amendment (OpenRouter only); the §6 amendment (ZDR relaxed at the account, the exception carved in Nix by IS4). **Context block:** `docs/context/isolation.md` (anchor `e535e53`, delta at `22b7b35`); every fact below re-measured at `662e87f` on 2026-09-14.

**Inherits:** the twelve constraints below are quoted verbatim from `docs/superpowers/plans/2026-09-09-program.md` (`factory-brief` carries only this file's section, `tools/factory/seat/factory-brief:51-52`). What each task adds to the *ingress* side — LAN reach — is TLS from an internal CA plus one auth per site, refused at eval when undeclared.

**Author:** Claude Fable 5.1, the batch fill pass (2026-09-11), revised 2026-09-14 against `docs/reviews/plan-judgements/2026-09-12-batch-isolation.md`.
**Status:** DRAFT, revision 1; no key here is dispatched before increment 3's drill passes (charter §6), except the docs keys, which may run during increment 3's waves.

## Global Constraints

Verbatim from `docs/superpowers/plans/2026-09-09-program.md:35-46`; "here" in a quoted line means the program plan, whose keys its examples name.

- **G1 Build-only.** Never `sudo`, `nixos-rebuild`, `systemctl start|stop|restart|enable|kill`, basket mount or teardown. The operator switches; a task that needs the live system to change says so in its `## Operator` line and stops. (G1, program.md:35)
- **G2 Red first.** Every check or test a task adds is shown failing before the change that makes it pass, and the red output is pasted in the commit body. A load-bearing test counts only once it has failed (CLAUDE.md). (G2, program.md:36)
- **G3 Trailers.** Both trailers, in this order: the machine-set `Generated-By:` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` (`docs/board/policies.md:30-36`, decision 52a). A gate reads the implement model from the task's own `.result` (FIX7, `6a84fae`). (G3, program.md:37)
- **G4 Subject.** `<area>: summary (test: <check names>)`, the area being the subsystem's prefix in lower case once PR1 lands (`evidence:`, `factory:`, `isolation:`, `knowledge:`, `program:`), the check names being exactly the task's `acceptance` list. Guarded twice: the workspace's `commit-msg` hook that `factory-ws` installs (`tools/factory/seat/factory-ws:131-136`, `factory-commit-msg.sh`) and the gate's convention section, which compares the subject byte for byte with the section's `commit subject` line. (G4, program.md:38)
- **G5 Touches.** Edit only the files the task's `touches` names; a new file is named there too. An undeclared touch demotes the result (`factory-task:857-861`). `git add` every new file before any `nix build` (flakes see tracked files only). **One standing exemption, added 2026-09-10 after it was flagged twice:** the *derived queue block* of `docs/OPERATIONS.md`, and nothing else in that file, when the pre-commit's G8c forces its regeneration — G6 orders that regeneration, so listing the file in every task's `touches` would be noise and omitting it made the gate read a forced, derived, machine-written hunk as an undeclared touch (HH3's minor, PR1's MAJOR). A gate treats a queue-block-only diff there as declared; any other hunk in that file is an undeclared touch as before, and board prose stays the orchestrator's (the rule that refused W6b at the integrator). **`docs/MAP.md` is exempt on the same ground and for the same reason** (KN1's minor): `lint` asserts it is current (`flake.nix:1081-1086`), so any task that adds or renames a module, package, check or test must run `python3 pkgs/evidence/repomap.py --root . write` and commit the result whether or not its `touches` names the file. Both exemptions cover *derived* files a check or hook forces; neither excuses a hand edit. (G5, program.md:39)
- **G6 Commit route.** `nix develop -c git commit -F <msgfile>` on `task/<KEY>`; one commit per task. **A fix round that starts by cherry-picking its predecessor folds that cherry-pick into its own single commit** (`git cherry-pick -n`, or `git reset --soft` back to the base before committing) — added 2026-09-10 after the instruction proved ambiguous: PR1b's seat folded and PR1c's did not, and `factory-task:757` demoted the second for claiming one commit where the branch carried two. The chain's history lives in the plan and the reviews, not in a stack of replayed commits on one task branch. If the pre-commit refuses only on G8c (a stale board queue block), regenerate with `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board` and include the block in the same commit; never `--no-verify`. (G6, program.md:40)
- **G7 Reserved prefixes** (decision 63a): `IS PL HM SA FA EV GN KN PR` and the two-part keys `SPEC-<XX>`, `PLAN-<XX>`. No other plan may define a key under them. **EV2 landed this guard on 2026-09-10 (`f31b8bb`, integrated `776b492`); it is live and no longer a sentence a reviewer enforces by reading the key.** `tasks.py check` refuses a key whose leading letters match a manifest prefix when its plan file matches none of that subsystem's `plans` globs (`pkgs/evidence/tasks.py:1835-1849`), beside the older refusal of a key defined in more than one plan (now `:1758-1766`). `reserved_prefix` reads the letters before the first digit or hyphen, so `SPEC-<XX>` and `PLAN-<XX>` resolve to `SPEC`/`PLAN`, match no manifest row, and pass. The practical consequence, paid for on 2026-09-10: a subsystem's `plans` list must name a plan file BEFORE that plan may hold keys under its prefix — the eight `2026-09-11-*.md` batch outputs were added to `docs/ledger/subsystems.toml` for exactly this reason. Fix rounds add a lower-case letter (`EV1b`); a re-key never reuses a landed key. (G7, program.md:41)
- **G12 Invariants** (brief §3, Assumption 13, re-ratified after the audit per decision 55a): every task here is written against the six verbatim. Where they bind: EV1 reads the broker's usage log locally and writes only the local store (3: nothing leaves the machine; 5: the timer is Nix configuration); EV5 changes a validator, never a credential field (2); IS1 changes no lane boundary and injects nothing (2, 3); IS2 reads and writes documents only, stores and redirects nothing (2, 3, 6); PR1, EV2, EV3, EV4, EV6, FA1, KN1 are configuration and ledgers reviewable in a diff (5); no task promotes agent-authored code between baskets (6); no task touches basket mounting (1) or adds imperative setup (4). (G12, program.md:42)
- **G8 Privacy.** Nothing leaves the machine. IS2 reads and writes nothing outside `docs/`; no credential, token or key is copied, moved, printed or redirected by any task in this plan. (G8, program.md:43)
- **G9 Areas.** From EV2 on, a task whose `touches` fall in two subsystems declares `**areas:**` with both; `tasks.py check` refuses it otherwise. **EV2 landed this on 2026-09-10 (`f31b8bb`); it is enforced in code, not by hand** (`pkgs/evidence/tasks.py:1823-1834`). The refusal fires only while a task's derived state is `ready`, `blocked`, `ran` or `running`, so a landed key is never refused retroactively, and it exempts exactly the twenty-five keys in `docs/ledger/areas-grandfather.toml` — a list frozen at `dbedfe9`, so a key typed later is refused like any other. Note the grandfather ledger is read from the repo's live path rather than the tree under `--root`, so inside a workspace it exempts nothing (`BUG-ledger-read-from-live-path`): declare `**areas:**` rather than relying on the exemption. (G9, program.md:44)
- **G10 Nix hygiene.** Module headers are `_:` never `{ ... }:` (statix); `hosts/core/hardware-configuration.nix` is never touched; a new language brings its formatter and linter in the same task (none is expected here). (G10, program.md:45)
- **G11 Numbers.** Every integer a task pastes (row counts, line numbers, test counts) is re-run at commit time, not copied from this plan (concept 2026-09-08g). Guarded by the gate: the review rubric's "correct facts" row re-runs the commit body's commands, and a pasted integer that does not reproduce is a MAJOR (the record's `wrong-fact` class in `docs/ledger/plan-defects.toml`). (G11, program.md:46)

Where G12's six invariants bind here: IS18 mounts a basket only inside a VM, never on the host (1); no task copies, prints or stores a credential — IS11 reads a hash file at runtime through Caddy, IS21 leaves the file to the operator (2); IS16 adds no egress path, it refuses one (3); every host change is a module option in a Nix diff (4, 5); no task promotes agent-authored code between baskets (6).

## Operator questions

Three; every other decision the outline asked about is an Assumption (21–27), applied as the outline's own recommendation, with its veto surface.

1. **The operator's words for brief §10 and the loopback assertion** (answer 20, decisions `:33`). Drafts: IS14 Interfaces 4–5, IS13 Interface 3. Recommendation: **approve as written** — IS13 and IS14 dispatch unchanged; on an edit the seat pastes the operator's text into the same interfaces first (a dispatch hold).
2. **Sites on the LAN at the first switch** (IS21). Bound: `{name, loopback upstream}` from {Helm's page `127.0.0.1:7700`; Helm's API `127.0.0.1:7710` once HM3 lands; the ComfyUI feed once GN10 imports it into `core`}. Recommendation: **Helm's page only** — one credential, one site in the drill. Each extra name adds one `sites.<name>` block to IS21's host file and one hash file to its Operator step; **an empty list withdraws IS21** (`docs/ledger/task-status.toml`).
3. **Auth mechanism at the first switch** (IS11). Bound: {password now — Caddy `basic_auth`, a bcrypt hash read at load from a file outside the store, WebAuthn later as its own key; both now — an L-size crossing into Platform's vendored builds}. Recommendation: **password now**; IS11–IS12 are written to it. "Both now" withdraws IS11 for a re-plan (size L is refused).

## Charter-to-task map

| Charter item (§2 answer / §6 increment 4) | Keys |
|---|---|
| 72 — the unit cap | done (IS1c, IS3, IS3b); IS10 repairs the fixture their default broke (the live `flake-check` failure) |
| 44 — the OAuth/router spike | done (IS2); outcome IS16 (the one UNMEASURED item), IS17 (the five closures) |
| 20 — LAN access with per-site auth; brief §10; the loopback assertion; the overlay typed | IS11, IS12, IS21; IS14; IS13; IS15 |
| 11 — a second port allowed to the seat; 7700, its token, `/var/lib/helm` refused | IS20 (network side); R8 stays Seat/Harness's |
| 49, 54, 55 — the re-ratified invariants | IS18 (invariant 1's check), IS19 (one name per measurable invariant); ratification is KN's audit |
| 57 — `danger-full-access` on kernel confinement | out: Not in this plan |

## Decisions relied on

The map above binds answers 11, 20, 44, 49/54/55, 57 and 72 to keys; the rest, each with what it displaces: **7/G9** — every cross-area task declares `**areas:**` (the alternative, splitting along ownership, was declined at IS3; Assumption 21). **63** — keys `IS10`–`IS21`, this plan named in the manifest (Assumption 11). **70** — `## Operator` is this plan's rows of the composed drill. **80** — Q80 closes mechanically on the drill's row 6 (Assumption 26). **§4 amendment** — IS17's recipe names no Anthropic instance; nothing adds a lane or a key. **§6 amendment** — the ZDR exception stays one id (Assumption 5); no task widens `exceptModels`.

## Assumptions

Measured in the block or the fill pass; each re-run at commit time per G11.

1. Isolation owns 38 tracked files, 12,720 lines — `git ls-files` over `docs/ledger/subsystems.toml:16-47`'s globs `| sort -u | wc -l` → 38; `| xargs wc -l | tail -1` → 12720 (block §1).
2. `nixosModules/seatLane.nix` defaults `waveJobs = 8` (`:73`) and `maxUnits = cfg.waveJobs + 1` (`:78`); the assertions sit at `:114-116`, `:123-125`, `:132-134`.
3. `tests/integration/seat-vm.nix:170` hardcodes `maxUnits = 2` with no `waveJobs` override; `flake-check` is `HEAD FAIL @662e87f`, failing since 2026-09-11T08:05:28Z, `services.seat-lane.maxUnits (2) must be greater than services.seat-lane.waveJobs (8)` — `evidence bundle --markdown` (2026-09-14).
4. IS5 and IS5b are `state == "ran"`, ungated and unintegrated (`tasks.py --root . json`, 2026-09-14); IS5b touches `flake.nix`, `nixosModules/seatLane.nix`, `pkgs/broker/policy.py`, `tests/broker/test_policy.py`, `docs/runbooks/lanes.md`.
5. The ZDR exception is one id, `seatLane.nix:182`, pinned at `flake.nix:2252-2269`.
6. Five `*-assertion-negative` checks exist (`flake.nix:1277, 1737, 2187, 2439, 2850`), the broker VM test is the check `integration`, and `grep -c 'basket-vm\|lan-vm\|invariant-' flake.nix` → 0 (2026-09-14).
7. All six invariant rows in `docs/ledger/rules.toml` (`:24, :36, :48, :60, :72, :84`) are `UNMEASURED` with `verdict = ""`, among 63 rows.
8. `tests/run-mount-tests.sh` and `tests/acceptance/phase*.sh` run under no flake check — `grep -c run-mount-tests flake.nix` → 0 (2026-09-14).
9. `docs/brief.md` **has** a §10, `## 10. Out of scope for now`, at `:353-357`, the last section (`grep -n '^## 10' docs/brief.md` → `353`; `wc -l` → 357, 2026-09-14), naming "Remote access from outside the LAN" — IS14 rewrites it in place.
10. The seat lane's proxy listens on `10.100.4.1:3141`; host→namespace is gated by `output-seat` (`nixosModules/seatLane.nix:385-392`: established/related and `tcp dport ${cfg.webPortRange}` to `namespaceAddress`, then drop).
11. `IS` is reserved by `tasks.py check` (`pkgs/evidence/tasks.py:1835-1849`) to the two plans at `docs/ledger/subsystems.toml:48-51`.
12. The cross-area refusal (`tasks.py:1823-1834`) exempts nothing inside a workspace (G9).
13. Helm's loopback assertion is at `nixosModules/helm.nix:488-492`, message ending `Helm is localhost-only until Phase 10`; the same phrase sits in the `listen` description at `:329` (`grep -n 'until Phase 10' nixosModules/helm.nix` → 2 lines, 2026-09-14); `helm-assertion-negative` at `flake.nix:1737-1744` proves `0.0.0.0` fails. HM3 extends the same region for `services.helm.api`.
14. `hosts/core/default.nix:4-17` is the core import list (`./helm.nix`, `./lanes.nix`, `./seat.nix`, …, and `../../nixosModules/usageIngest.nix` at `:16` — EV1's precedent for importing a module without a `flake.nix` touch); there is no `hosts/core/configuration.nix` — `ls hosts/core` (2026-09-14). IS21's touches name `hosts/core/default.nix` (judgement erratum 29).
15. `grep -c 'key = "IS' docs/ledger/plan-defects.toml` → 0.
16. IS2's five deferred questions sit under `## 5.` at `docs/research-2026-09-10-oauth-router-spike.md:327-362`; the last heading is `## 6. Commands run` at `:364` (2026-09-14).
17. `grep -rn 'services.caddy' flake.nix nixosModules hosts | wc -l` → 0 (2026-09-14); GN's Caddy lives in `~/flakes/media`.
18. Helm's API port 7710 is the Helm draft's Operator Q1 default (`~/factory/batch/2026-09-11/drafts-r2/2026-09-11-helm.md:13`; HM3 at `:190` declares `services.helm.api.port`) — an unlanded assumption until HM3 lands; the confirming command is `nix eval .#nixosConfigurations.core.config.services.helm.api.port` → `7710` (IS20 Step 0). Helm's page is `services.helm.port` default 7700, `listen` default `127.0.0.1:${toString cfg.port}` (`nixosModules/helm.nix:318-325`).
19. The broker key file is `/var/lib/secrets/openrouter-key` (`hosts/core/seat.nix:12`), `0440 root:egress-broker`, its directory `d /var/lib/secrets 0710 root egress-broker -` (`nixosModules/seatLane.nix:221`) — traversable by `egress-broker`, not by `caddy`.
20. `basket mount` runs as root (`pkgs/basket/basket.sh:153`), mounts a tmpfs at a hidden staging path and bind-mounts it to `$runtime_dir/$id` (`:159-175`); the `basket` package is `flake.nix:58-62`.
21. (was OQ1) Cross-owner fixes stay under IS keys with `**areas:**` declared — IS10 a Seat/Harness fixture, IS13 a Helm module — the outline's recommendation A, unopposed; the audit kept IS10 canonical (`audit.md:95`); veto surface: a `withdrawn` row in `docs/ledger/task-status.toml` and a `FIX`/`HM` re-type.
22. (was OQ4) IS15's concept assumes WireGuard (declared in Nix, keys outside the store, no coordinator); the alternative, a coordinated mesh, is named in its term 1 — the outline's recommendation, unopposed; veto surface: IS15 Interface 1 before dispatch.
23. (was OQ6) Helm's second port is 7710 — pre-closed by the Helm draft's Q1 default (Assumption 18); veto surface: Platform's `hosts/core/seat.nix` value and IS20's Step 0.
24. (was OQ7) IS2's five deferred questions are accepted at the spike's own defaults (`docs/research-2026-09-10-oauth-router-spike.md:329-362`) — the outline's recommendation, unopposed; veto surface: IS17's `## 7.` text before dispatch.
25. (was OQ8) Invariants 1, 2, 3, 5 get four aggregate checks (option A) — the outline's recommendation, unopposed; veto surface: withdraw IS19 (option B, nothing until KN's audit).
26. (was OQ9) Q80 closes mechanically on the drill's row 6 — the outline's recommendation, unopposed; veto surface: type an XS docs task instead.
27. (was OQ10) IS21's second touch is `hosts/core/default.nix` — answered by judgement erratum 29 (Assumption 14); no question remains.

## Waves

Derived: `tasks.py waves --repo nixos-agent-env --plan 2026-09-11-isolation.md` on a scratch copy holding this draft (2026-09-14) prints `"IS10" "IS11 IS18" "IS14" "IS15" "IS16"` / `"IS12 IS19 IS20" "IS17"` / `"IS21"` (groups by the shared `flake.nix` touch). IS13 is absent because its `dependsOn` names HM3, defined only in this batch's Helm draft (`2026-09-11-helm.md:190`): the edge **resolves when the Helm plan lands** (the nine land together in dependency order); IS13 then peels off in wave 2 behind IS11 and HM3, and IS21 (`dependsOn: IS11, IS12, IS13` — the switch carries the amended assertion) after it. Dispatch holds: IS13 and IS14 on question 1's words; IS21 on question 2's list; IS16 and IS20 on IS5b's integration (Assumption 4); every VM eval on IS10. The single switch follows IS21.

## Cross-plan

`tasks.py conflicts --repo nixos-agent-env` on the live tree (2026-09-14): three hits, none Isolation's (EV6 × HH6/HH8/HH9, `flake.nix`). On the scratch copy holding this draft, the hits naming IS keys: `flake.nix` — IS11, IS12, IS13, IS18, IS19, IS20 × {HH6, HH8, HH9, EV6, IS5b}; `pkgs/broker/policy.py`, `tests/broker/test_policy.py` — IS16 × IS5, IS5b; `docs/runbooks/lanes.md` — IS17 × IS5, IS5b; `nixosModules/seatLane.nix` — IS20 × IS5, IS5b. IS5b (`ran`, Assumption 4) is gated and integrated before IS16, IS17 and IS20 draft; every IS `flake.nix` touch adds a new attribute or region only, so a rebase onto HH*/EV6 is an append. "First" means the earlier key lands and the later rebases.

| Sibling-draft overlap (keys under `~/factory/batch/2026-09-11/drafts-r2/`) | Order and why |
|---|---|
| `nixosModules/helm.nix` — HM3, HM5, IS13 | **HM3 first** (declares `services.helm.api`, extends the assertion region), HM5 (disjoint region), then IS13 (`dependsOn: HM3`). |
| `tests/integration/seat-vm.nix` — IS10, IS20, SA4, SA7 | **IS10 first and canonical** for `:170` (audit 5a: DF2 withdrawn; SA1 `dependsOn: IS10`, `2026-09-11-seat-harness.md:146`; DF1 `dependsOn: EV4, DF3, IS10`, `2026-09-11-defects.md:137`); IS20 adds an arm after SA4/SA7. |
| `nixosModules/seatLane.nix` — IS20, SA1, SA4, SA7 | SA keys first (increment 2); IS20 adds one option, one assertion and one rule — an append. |
| `flake.nix` — PL2–PL5, SA1, SA4, SA8, FA23, HM3, EV16, GN6, GN7, GN10–GN12, KN13, KN15–KN17, KN19, IS11–IS13, IS18–IS20 | one derived queue; PL's keys first (Platform owns the file); Isolation's internal order is `## Waves`. |
| `docs/brief.md` — IS14, KN18 | **KN18 first** (supersedes §4/§7/§9, 55a); IS14 rewrites §10 only. |
| `docs/ledger/subsystems.toml` — PL1, EV10, FA13, GN11, IS15 | IS15 appends one string to Knowledge's `owns`, **last**. |
| `hosts/core/default.nix` — PL4, GN10, IS21 | IS21 adds one import line, **last**. |
| Ownership | IS10/IS20 (`seat`), IS13 (`helm`), IS21 and every `flake.nix` touch (`platform`), IS14/IS15/IS17 (`knowledge`, `evidence`) declare areas. GN's Caddy stays in `~/flakes/media` (Assumption 17); IS11's A3 binds it the day GN10 imports it into `core`. The invariant rows' `check` fields are KN's to write with IS19's names; `plan-defects.toml` rows are EV's; guard paths and verbs (34, 53) are FA's. |

## Operator

**The switch:** exactly one, after IS21 lands; nothing before it changes the live host (every module here defaults to disabled or to its current value). Before the switch line, on the landed tree: `nix build .#nixosConfigurations.core.config.system.build.toplevel` → `./result`; `nix store diff-closures /run/current-system ./result` → paste the measured delta beside this prediction. **Predicted delta** (a prediction, never a fact — design §4 A2): added `caddy` and its closure, `caddy.service`, the `caddy` user and group, `/etc/lan-access/sites`, the `/var/lib/lan-access` tmpfiles line, a `nixos-fw` accept for 80/443 on the LAN interface; `nixos-version` moves; nothing dropped; **no seat-lane or broker unit changes** (IS20 renders only when Platform sets `helmApiPort` in `hosts/core/seat.nix`, not in this plan). Any other line is a finding against IS11/IS21.

**Acceptance drill** (this plan's rows of the composed increment-4 drill, 70b):

1. `nix flake check -L` green at the integration head (`seat-vm`, `lan-vm`, `basket-vm`, `integration`, the four `invariant-*` included); `evidence bundle --markdown` → `flake-check: HEAD PASS`.
2. After the switch and IS21's Operator step, from a LAN client trusting the internal CA's root (`sudo cat /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt` on core, copied by hand): `curl --cacert root.crt https://<site>/` → `401`; with `-u <user>` → `200`; `curl -m 3 http://core:8080/` → `Connection refused`; `curl -si http://<site>/ | head -1` → `308`, never a body.
3. Helm's page opens over the LAN in a browser with the root trusted, and nowhere else.
4. Inside a running seat (once Platform sets `helmApiPort`): `curl -s 10.100.4.1:7710/v1/status | jq 'keys'` lists tiles; `curl -m 3 10.100.4.1:7700/` → refused; `dsh-openrouter --denials 1` shows R8 unchanged.
5. `basket-vm` and `sudo tests/run-mount-tests.sh` agree: no plaintext outside tmpfs, nothing left after teardown.
6. **Q80:** `stat -c '%U:%G %a %n' "$(nix eval --raw .#nixosConfigurations.core.config.services.seat-lane.keyFile)"` → expected `root:egress-broker 440 /var/lib/secrets/openrouter-key` — paste the line; the orchestrator closes the row with it.
7. Say "test passed".

**Rollback:** `nixos-rebuild switch --rollback` (the operator) returns to the generation before the switch — **55** today (`readlink /nix/var/nix/profiles/system` → `system-55-link`, 2026-09-14; re-read it just before switching and quote the number in the board line); the module is inert without `hosts/core/lan-access.nix`; the internal CA's root is removed from each client's trust store; no task stores, moves or prints a credential (G8), so nothing else needs undoing.

**Relaunch** (design §4 A6): if a seat dies mid-run (`budget-402`, `provider-error`), `FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-isolation.md setsid -f bash -c 'exec tools/factory/seat/factory-wave is6b ~/nixos-agent-env <KEY> >> ~/factory/runs/is6b.wave.log 2>&1' </dev/null`; the dead seat's diff stays in `~/factory/ws/is6/<KEY>` and the relaunch's brief points at it.

## Dispatch

Run name `is6` (`ls ~/factory/runs | grep -x is6` → empty on 2026-09-14; the IS runs so far are `is4a is5a is5b`). The seat dispatches after increment 3's drill:

```
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-isolation.md tools/factory/seat/factory-dispatch is6 ~/nixos-agent-env docs/superpowers/plans/2026-09-11-isolation.md --dry-run
```

Expected first line, from `waves --next` on the scratch copy (2026-09-14): `"IS10" "IS11 IS18" "IS14" "IS15" "IS16"` — five groups, the cap. The same line without `--dry-run` launches it; the second call prints `"IS12 IS19 IS20" "IS17"` (IS13 joins once HM3 has landed), the third `"IS21"` (once IS13 has), then nothing. Per landing, in order: (1) keep the one commit — `git -C ~/factory/ws/is6/<KEY> log --format='%h %s' <base>..task/<KEY>`, then `git -C ~/factory/ws/is6/<KEY> reset --hard <that sha>`; (2) if main moved under a touched file, `git -C ~/factory/ws/is6/<KEY> fetch ~/nixos-agent-env main && git -C ~/factory/ws/is6/<KEY> merge --no-edit FETCH_HEAD`; (3) commit the review; (4) `tools/factory/seat/factory-integrate is6 ~/nixos-agent-env <KEY>` then `git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/is6`, gated on both exit codes; (5) dispatch what it unblocks — IS10 → IS20 and every VM eval; IS11 → IS12 (and IS13 with HM3); IS16 → IS17; IS18 → IS19; IS11+IS12+IS13 → IS21. Commit the regenerated board block before every dispatch (G6).

## Anticipation

- **A1, A7** — the dispatch lines and what each landing unblocks, above. **A2** — IS11, IS13, IS20, IS21 touch `nixosModules/` or `hosts/`: build commands, predicted delta, rollback generation under `## Operator`. **A3** — the operator owns the site hash (IS21's Operator step) and the CA root on each client (drill row 2). **A4** — every task's Mutants and Tests lines. **A5** — `FACTORY_PLAN` on every launch line; one commit per task; `FACTORY-RESULT status=<done|partial|failed>` with a space. **A6** — the relaunch line under `## Operator`.
- **A8** — none of `evidence bundle`'s 26 open gaps closes here; the Q80 legacy row (`docs/ledger/plan-status.toml:93`) closes on drill row 6. **A9** — hold IS16 and IS20 until IS5b is integrated; hold any wave while `lint` is red on main. **A10** — three questions with recommendations. **A11** — handoff line for `docs/OPERATIONS.md`: "Isolation 2026-09-11: on the seat: <wave>; in gate: <keys>; next: <wave>; switch after IS21, rollback gen <N>".
- **A14** — IS16 adds one deny (`websocket-upgrade-unlisted`); no runbook recipe, launch line or board command opens a WebSocket through a broker (`grep -rin websocket docs/runbooks tools/factory/seat | wc -l` → 0, 2026-09-14), so nothing the operator or the seat runs is refused by it.

## Not in this plan

- IS1c's three SPEC-SA minors (block §5.2) and R8's token and `/var/lib/helm` refusals — Seat/Harness.
- WebAuthn per site — its own key after question 3; building the overlay — after the operator gates IS15's phase.
- The rules audit, verdicts, dated ruleset, brief §4/§7/§9's supersession — Knowledge (49d, 54a, 55a).
- `plan-defects.toml` rows for IS keys, the Q80 `plan-status.toml` row — Evidence; guard paths and verbs (34, 53) — Factory; FIX-class changes to Isolation files — Factory's bugs plan.
- Answer 57's Isolation half (`seat-eval` pinning the seat unit's confinement set) — the increment after SA's launch change lands.
- IS5/IS5b's gate and integration — the program plan; any Anthropic lane or key (§4 amendment); any widening of `exceptModels` (§6 amendment); a WebSocket/SSE OAuth *decision* — IS16 measures, IS17 records.

## Tasks

### IS10 (code, XS) — seat-vm's fixture follows the raised waveJobs default

**dependsOn:** none
**touches:** `tests/integration/seat-vm.nix`
**acceptance:** seat-vm, lint
**areas:** isolation, seat
**commit subject:** `isolation: seat-vm's fixture sets waveJobs beside maxUnits, so the raised default no longer breaks eval (test: seat-vm, lint)`

**Why.** `checks.x86_64-linux.seat-vm` does not evaluate at HEAD (Assumptions 2–3): the fixture's `maxUnits = 2` inherits `waveJobs = 8` and trips `maxUnits > waveJobs`. Every VM acceptance in this plan (IS12, IS18, IS20) shares this eval, so it is first. The audit made this key the canonical `:170` fix; DF2 is withdrawn and SA1 depends on it.

**Files.** Modify `tests/integration/seat-vm.nix`: one line added beside `:170`, `waveJobs = 1;`, with a two-line comment naming the relation (`maxUnits > waveJobs`, IS3) and why 1 (IS1c's step 11b needs the unit cap reachable with two held seats; the wave cap is irrelevant in the VM, which never runs `factory-wave`).

**Interfaces.**
1. The fixture evaluates under the shipped module: `services.seat-lane.waveJobs = 1`, `maxUnits = 2`, so `2 > 1` holds and both `>= 1` assertions hold.
2. `/etc/seat-lane/wave-jobs` inside the VM reads `1` and `/etc/seat-lane/max-units` reads `2` (`seatLane.nix:147-154` publishes both).
3. Nothing else in the fixture changes; the test script's step 11b (the cap refusal with two held seats) still reaches the cap at 2.

**Steps.**
1. **Red.** `nix build .#checks.x86_64-linux.seat-vm --no-link 2>&1 | grep -F 'maxUnits (2) must be greater than'` → prints `error: Failed assertions: - services.seat-lane.maxUnits (2) must be greater than services.seat-lane.waveJobs (8)`; exit of the build ≠ 0. Also `sed -n '170p' tests/integration/seat-vm.nix` → `        maxUnits = 2;` with no `waveJobs` in `sed -n '160,172p'`. Paste both into the commit body.
2. Add `waveJobs = 1;` directly above `maxUnits = 2;` with the comment.
3. **Green.** `nix build .#checks.x86_64-linux.seat-vm --no-link -L 2>&1 | tail -3` → the test's final `(finished: run the VM test script …)` line and exit 0; `nix eval .#checks.x86_64-linux.seat-vm.nodes.machine.config.services.seat-lane.waveJobs` → `1`; `nix build .#checks.x86_64-linux.lint --no-link` → exit 0.
4. **Mutants.**
   - **M1 (revert the fix):** `git stash` (or delete the added line) then Step 1's command → the same `maxUnits (2) must be greater than … waveJobs (8)` assertion; `git stash pop`.
   - **M2 (fix on the wrong side):** set `waveJobs = 2;` keeping `maxUnits = 2;` → `nix build .#checks.x86_64-linux.seat-vm --no-link 2>&1 | grep -F 'maxUnits (2) must be greater than services.seat-lane.waveJobs (2)'` prints the assertion, proving the strict relation is what the fixture now satisfies, not merely the presence of the option. Revert.
   - **M3 (raise the cap instead):** set `maxUnits = 3;` keeping `waveJobs = 1;` → eval passes but step 11b (`tests/integration/seat-vm.nix:580-610`) holds two web seats and expects the third submit refused with `2 seat units running, cap 2`; at cap 3 that seat starts, `wait_until_succeeds("grep -q 'FACTORY-RESULT status=failed' …")` times out and the check fails — the cap stays 2. Revert.
5. Commit with the subject above; body carries Step 1's red text, Step 3's green tail, and the three mutant lines.

**Negative control.** `nix eval .#nixosConfigurations.core.config.services.seat-lane.maxUnits` → `9` and `.waveJobs` → `8` — the host's defaults are unchanged by this task (a fixture-only diff). Discriminating row: M2 above changes the fixture's evaluation while this eval still prints `9`/`8`, so the control distinguishes the fixture from the module.

**Tests** (assertion → mutant; fixture → discriminating row): `maxUnits > waveJobs` in the VM fixture → M1; strictness of the relation → M2; the cap itself stays 2 (step 11b) → M3; core defaults untouched → the negative control's eval, discriminated by M2.

**probes:**
- seat-vm-fixture-wavejobs: `grep -c 'waveJobs = 1;' tests/integration/seat-vm.nix` :: ge 1 :: expected after Step 2
- seat-vm-fixture-wavejobs-once: `grep -c 'waveJobs = 1;' tests/integration/seat-vm.nix` :: le 1 :: exact count, expected after Step 2
- seat-vm-fixture-maxunits: `grep -c 'maxUnits = 2;' tests/integration/seat-vm.nix` :: ge 1 :: sed -n 170p tests/integration/seat-vm.nix at 662e87f, 2026-09-14
- seat-vm-fixture-maxunits-once: `grep -c 'maxUnits = 2;' tests/integration/seat-vm.nix` :: le 1 :: exact count, the same line

### IS11 (code, M) — services.lan-access: an internal CA and one auth per LAN-exposed site

**dependsOn:** none
**touches:** `nixosModules/lanAccess.nix`, `flake.nix`
**acceptance:** lan-eval, lan-assertion-negative, lint
**areas:** isolation, platform
**commit subject:** `isolation: services.lan-access fronts declared sites with an internal CA and one auth each, and refuses any other non-loopback bind (test: lan-eval, lan-assertion-negative, lint)`

**Why.** Answer 20 (Charter map) has no implementation: no `services.caddy` (Assumption 17), no `lan-*` module (`ls nixosModules | grep -c lan` → 0), no `lan-eval`/`lan-assertion-negative` check (Assumption 6). Question 3's recommendation fixes the auth shape: Caddy `basic_auth` with a bcrypt hash read from a file outside the store — no credential enters `/nix/store` (invariant 2 on the ingress side) and the set of LAN-reachable sites is a Nix diff (invariant 5).

**Files.**
- Create `nixosModules/lanAccess.nix` (header `_:`, G10): options `services.lan-access.{enable, interface, sites}`; `sites.<name> = { upstream; hashFile; user; }`; an internal read-only option `renderedHosts` (`listOf str`, `internal = true; readOnly = true;`) the module sets to the vhost names it renders — the producer A3 subtracts; the Caddy rendering; four assertions A1–A4; `systemd.tmpfiles.rules = [ "d /var/lib/lan-access 0710 root caddy -" ]` (nixpkgs' Caddy runs as user and group `caddy`, `dataDir = "/var/lib/caddy"`; `/var/lib/secrets` is `0710 root egress-broker`, Assumption 19, which `caddy` cannot traverse — hence its own directory); the `environment.etc."lan-access/sites"` listing.
- Modify `flake.nix`: export `nixosModules.lanAccess` beside `seatLane` (`:1030`); add `checks.lan-eval` (a `pkgs.runCommand` over `nixosSystem` fixtures asserting the rendered Caddyfile text) and `checks.lan-assertion-negative`, byte-shaped on `seat-assertion-negative` (`flake.nix:2439-2458`):
  ```nix
  lan-assertion-negative =
    let
      upstreamAttempt = builtins.tryEval lanBadUpstreamSystem.config.system.build.toplevel.drvPath;
      # … one tryEval per arm below …
    in
    if upstreamAttempt.success then
      throw "lan-assertion-negative: services.lan-access.sites.helm.upstream = 0.0.0.0:7700 DID NOT FAIL the build"
    else if hashStoreAttempt.success then throw "…" # each arm its own message
    else pkgs.runCommand "lan-assertion-negative-ok" { } "touch $out";
  ```
  regenerate `docs/MAP.md` (G5's exemption, `lint` asserts it).

**Interfaces.**
1. `services.lan-access.enable` defaults `false`; when false the module sets nothing (`services.caddy.enable` is untouched, no virtual host is rendered, `renderedHosts == [ ]`).
2. `sites.<name>.upstream` is a `str` matching `^127\.0\.0\.1:[0-9]+$` or `^\[::1\]:[0-9]+$` — assertion A1, message `services.lan-access.sites.<name>.upstream must be a loopback address, got '<value>'`.
3. `sites.<name>.hashFile` is a `str` path to a bcrypt hash — A2, `!(lib.hasPrefix "/nix/store" hashFile)`, message `services.lan-access.sites.<name>.hashFile must be outside /nix/store, got '<value>'`; A4, `lib.hasPrefix "/var/lib/lan-access/" hashFile`, message `services.lan-access.sites.<name>.hashFile must lie under /var/lib/lan-access/ (the directory caddy may traverse), got '<value>'`. It is read through Caddy's `{file.<path>}` placeholder at config load, never at eval. Runtime contract: an **absent** file makes `caddy.service` fail to load (every site refuses connections until IS21's Operator step installs it and restarts caddy); a **malformed** hash never admits — bcrypt comparison fails closed, `401` for every credential (IS12 Interface 8).
4. Each site renders `services.caddy.virtualHosts."<name>.<hostname>.local"` (hostname from `config.networking.hostName`) with `tls internal`, `basic_auth { <user> {file.<hashFile>} }`, `reverse_proxy <upstream>`; Caddy's automatic HTTP→HTTPS redirect (308) stays on; the name is appended to `renderedHosts`.
5. A3 — the guard on the host: every name in `builtins.attrNames config.services.caddy.virtualHosts` that is **not** in `config.services.lan-access.renderedHosts` must have `listenAddresses != [ ]` with every address `127.0.0.1` or `::1` (nixpkgs' vhost `listenAddresses` defaults to `[ ]`, which renders no `bind` and binds everything); message `a Caddy virtual host outside services.lan-access binds a non-loopback address: <name>`. GN's future loopback sites pass by construction; a hand-added site, however it is spelled, fails.
6. `services.caddy.enable = true` only when `enable && sites != {}`; `networking.firewall.interfaces.<interface>.allowedTCPPorts = [ 80 443 ]` only under the same condition; no other port opens.
7. `/etc/lan-access/sites` lists `<name> <upstream>` one per line, for the drill's row 2 and for `lan-vm`.

**Steps.**
1. **Red.** `nix build .#checks.x86_64-linux.lan-eval --no-link 2>&1 | tail -1` → `error: flake 'git+file:///…' does not provide attribute 'checks.x86_64-linux.lan-eval'`; the same for `lan-assertion-negative`. `nix eval .#nixosModules.lanAccess 2>&1 | tail -1` → `error: … does not provide attribute 'nixosModules.lanAccess'`. Paste all three.
2. Write `nixosModules/lanAccess.nix` per Interfaces 1–7; `git add` it.
3. Export it in `flake.nix`; add `lan-eval` with a fixture `lanEvalSystem` of three sites — `helm = { upstream = "127.0.0.1:7700"; hashFile = "/var/lib/lan-access/helm.bcrypt"; user = "dalhaka"; }`, `feed = { upstream = "127.0.0.1:8188"; … }` and `api = { upstream = "[::1]:7710"; … }` (the IPv6 arm of A1) — asserting with `lib.assertMsg` that the rendered `config.services.caddy.configFile` text contains `tls internal`, `basic_auth`, `{file./var/lib/lan-access/helm.bcrypt}`, `reverse_proxy 127.0.0.1:7700`, `reverse_proxy [::1]:7710`, contains no `/nix/store` path inside a `basic_auth` block, that `config.services.lan-access.renderedHosts` has exactly three names, and that `config.networking.firewall.interfaces.<interface>.allowedTCPPorts == [ 80 443 ]`. Add `lanDisabledSystem` (`enable = false`) asserting `config.services.caddy.enable == false`.
4. Add `lan-assertion-negative` with five negative systems: `lanBadUpstreamSystem` (`upstream = "0.0.0.0:7700"`), `lanHashInStoreSystem` (`hashFile = "${pkgs.writeText "h" "x"}"`), `lanHashOutsideDirSystem` (`hashFile = "/var/lib/secrets/helm.bcrypt"`), `lanForeignHostSystem` (a hand-written `services.caddy.virtualHosts."public.example"` with `listenAddresses = [ ]`), `lanForeignSiteNameSystem` (a hand-written `services.caddy.virtualHosts."feed.core.local"` — spelled like a site, not declared in `sites` — with `listenAddresses = [ "0.0.0.0" ]`). Each arm `throw`s `lan-assertion-negative: <case> DID NOT FAIL the build` when `tryEval` succeeds.
5. `python3 pkgs/evidence/repomap.py --root . write`.
6. **Green.** `nix build .#checks.x86_64-linux.lan-eval --no-link` → exit 0; `nix build .#checks.x86_64-linux.lan-assertion-negative --no-link` → exit 0; `nix build .#checks.x86_64-linux.lint --no-link` → exit 0. Paste `nix eval --raw .#checks.x86_64-linux.lan-eval.drvPath | wc -c` as the existence proof.
7. **Mutants.**
   - **M1 (drop A1):** delete the upstream assertion → `lan-assertion-negative: services.lan-access.sites.helm.upstream = 0.0.0.0:7700 DID NOT FAIL the build`.
   - **M2 (drop A2):** → `… hashFile = a store path DID NOT FAIL the build`.
   - **M3 (drop A3):** → `… a non-loopback Caddy virtual host outside lan-access DID NOT FAIL the build`.
   - **M4 (drop `tls internal`):** → `lan-eval: rendered Caddyfile lacks 'tls internal'`.
   - **M5 (open the firewall unconditionally):** move `allowedTCPPorts` outside the `enable` guard → `lan-eval` fails on `lanDisabledSystem`: `lan-eval: lan-access disabled but firewall opens 80/443`.
   - **M6 (inline the hash):** render `basic_auth { dalhaka <literal> }` → `lan-eval: basic_auth block does not read its hash from a file`.
   - **M7 (drop the IPv6 alternative):** regex `^127\.0\.0\.1:[0-9]+$` only → `lan-eval` fails at eval on the `api` site: `services.lan-access.sites.api.upstream must be a loopback address, got '[::1]:7710'`.
   - **M8 (drop A4):** → `… hashFile = /var/lib/secrets/helm.bcrypt DID NOT FAIL the build`.
   - **M9 (A3 keyed on spelling):** replace the `renderedHosts` subtraction by "names ending in `.<hostname>.local` are ours" → `lanForeignSiteNameSystem` builds: `… a hand-added feed.core.local with listenAddresses 0.0.0.0 DID NOT FAIL the build`.
   Revert each; run the three checks again → green.
8. Commit with the subject above; body carries Step 1's three errors, Step 6's exits and the nine mutant lines.

**Negative control.** `lanDisabledSystem` and `lanEvalSystem` must both PASS `lan-eval`; M5 turns the disabled fixture red while the enabled one stays green, proving the control discriminates the guard from the rendering.

**Tests** (assertion → mutant; fixture → discriminating row): A1 IPv4 → M1; A1 IPv6 (`api` site) → M7; A2 → M2; A3 → M3; A3's producer → M9; A4 → M8; `tls internal` rendered → M4; firewall guarded by `enable` → M5; hash read from a file → M6; `lanDisabledSystem` (control) → M5.

**probes:**
- lan-module-header: `head -1 nixosModules/lanAccess.nix` :: eq _: :: G10, expected after Step 2
- lan-no-store-in-caddy: `grep -c 'services.caddy' nixosModules/lanAccess.nix` :: ge 1 :: expected after Step 2
- lan-checks-named: `grep -c 'lan-eval =\|lan-assertion-negative =' flake.nix` :: ge 2 :: expected after Step 4
- lan-checks-named-exact: `grep -c 'lan-eval =\|lan-assertion-negative =' flake.nix` :: le 2 :: exact count, expected after Step 4

### IS12 (code, M) — lan-vm: a LAN client is refused without credentials, admitted with them, and reaches nothing undeclared

**dependsOn:** IS11
**touches:** `tests/integration/lan-vm.nix`, `flake.nix`
**acceptance:** lan-vm, lint
**areas:** isolation, platform
**commit subject:** `isolation: lan-vm proves the LAN path — 401 without credentials, 200 with, refused everywhere else (test: lan-vm, lint)`

**Why.** IS11 proves the rendered configuration; nothing proves the wire. No check named `lan-vm` exists (`grep -c 'lan-vm' flake.nix` → 0) and `test -f tests/integration/lan-vm.nix; echo $?` → `1` (`ls tests/integration` → `broker-vm.nix helm-control-vm.nix helm-vm.nix lane-vm.nix proton-backup-vm.nix seat-vm.nix telemetry-vm.nix`, seven entries, 2026-09-14). The drill's row 2 is four `curl`s a human runs once; this task is the same four, run on every `nix flake check` — the mechanical twin, so the operator's switch is not the first time the path is exercised.

**Files.**
- Create `tests/integration/lan-vm.nix`, the skeleton (the `runNixOSTest` form of `tests/integration/broker-vm.nix:19-24`, two nodes):
  ```nix
  { pkgs, lanAccessModule }:
  pkgs.testers.runNixOSTest {
    name = "lan-access";
    nodes.server = { pkgs, ... }: {
      imports = [ lanAccessModule ];
      networking.hostName = "server";
      services.lan-access = { enable = true; interface = "eth1";
        sites.helm = { upstream = "127.0.0.1:7700"; hashFile = "/var/lib/lan-access/helm.bcrypt"; user = "tester"; }; };
      systemd.services.lan-vm-hash = {            # writes the hash before caddy loads its config
        before = [ "caddy.service" ]; requiredBy = [ "caddy.service" ];
        serviceConfig.Type = "oneshot";
        script = ''
          install -d -m 0710 -o root -g caddy /var/lib/lan-access
          ${pkgs.caddy}/bin/caddy hash-password --plaintext secret > /var/lib/lan-access/helm.bcrypt
          chown caddy:caddy /var/lib/lan-access/helm.bcrypt; chmod 0400 /var/lib/lan-access/helm.bcrypt
        '';
      };
      systemd.services.upstream-7700 = { wantedBy = [ "multi-user.target" ]; script = "cd ${pkgs.writeTextDir "index.html" "LAN-VM-BODY"}; exec ${pkgs.python3}/bin/python3 -m http.server 7700 --bind 127.0.0.1"; };
      systemd.services.undeclared-8080 = { wantedBy = [ "multi-user.target" ]; script = "exec ${pkgs.python3}/bin/python3 -m http.server 8080 --bind 0.0.0.0"; };
    };
    nodes.client = { pkgs, ... }: { environment.systemPackages = [ pkgs.curl ]; networking.hosts."192.168.1.1" = [ "helm.server.local" ]; };
    testScript = '' … Interfaces 1–8 as machine.succeed / machine.fail lines … '';
  }
  ```
  The plaintext `secret` is a fixture, never a credential; a oneshot generates the hash in the VM (`systemd.tmpfiles` cannot run a program).
- Modify `flake.nix`: `lan-vm = import ./tests/integration/lan-vm.nix { inherit pkgs; lanAccessModule = self.nixosModules.lanAccess; };` beside `seat-vm` (`flake.nix:2476-2481`); regenerate `docs/MAP.md`.

**Interfaces.**
1. `client` obtains the root: `server.succeed("cat /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt")` copied into `client`'s `/tmp/root.crt` — the same file the drill's row 2 names.
2. `curl --cacert /tmp/root.crt -s -o /dev/null -w '%{http_code}' https://helm.server.local/` from `client` → `401`.
3. The same with `-u tester:secret` → `200` and body `LAN-VM-BODY`.
4. `curl -m 3 -s -o /dev/null -w '%{http_code}' http://server:8080/` → exit 7 (connection refused; the firewall hides the undeclared listener even though it binds `0.0.0.0`).
5. `curl -s -o /dev/null -w '%{http_code}' http://helm.server.local/` → `308` (Caddy's redirect), and `curl -s http://helm.server.local/ | wc -c` → `0` — plain HTTP serves no body.
6. Without `--cacert` the TLS handshake fails: `curl -s https://helm.server.local/; echo $?` → `60` — the CA is internal, trusted only where the operator installs it.
7. `server.succeed("cat /etc/lan-access/sites")` → `helm 127.0.0.1:7700`.
8. Malformed hash (IS11 Interface 3's contract): `server.succeed("printf 'not-a-bcrypt-hash' > /var/lib/lan-access/helm.bcrypt; systemctl restart caddy.service")`, then Interface 3's `curl -u tester:secret` → **not** `200` (`401`, or exit 7 if Caddy refuses the config — either is fail-closed; the script asserts `!= 200`); then the oneshot is re-run (`systemctl restart lan-vm-hash caddy`) and Interface 3 → `200` again.

**Steps.**
1. **Red.** `nix build .#checks.x86_64-linux.lan-vm --no-link 2>&1 | tail -1` → `error: … does not provide attribute 'checks.x86_64-linux.lan-vm'`. Then write the test file with the assertions of Interfaces 2–8 but **without** importing `lanAccessModule` into `server` (so no Caddy runs), wire it in `flake.nix`, and run: `nix build .#checks.x86_64-linux.lan-vm --no-link -L 2>&1 | grep -F 'command `curl --cacert /tmp/root.crt' | head -1` → the test fails at Interface 2 with `Test "…" failed with: command ` curl … ` did not succeed (exit code 7)`. Paste both reds.
2. Import `lanAccessModule` into `server` with the one site, the oneshot and the two listeners; add the client's root-copy step (Interface 1).
3. `python3 pkgs/evidence/repomap.py --root . write`.
4. **Green.** `nix build .#checks.x86_64-linux.lan-vm --no-link -L 2>&1 | grep -E '\(finished: run the VM test script|test script finished' | tail -1` → the finished line, exit 0; `nix build .#checks.x86_64-linux.lint --no-link` → exit 0.
5. **Mutants.**
   - **M1 (no auth):** remove `basic_auth` from the module's rendering (a module-side revert applied in the workspace only) → Interface 2 fails: `expected 401, got 200`. Revert.
   - **M2 (firewall open):** add `networking.firewall.allowedTCPPorts = [ 8080 ];` to `server` → Interface 4 fails: `expected exit 7 on :8080, got 200`. Revert.
   - **M3 (plain HTTP served):** set `services.caddy.virtualHosts."helm.server.local".hostName = "http://helm.server.local"` in the fixture → Interface 5 fails: `expected 308 on http://, got 200`. Revert.
   - **M4 (public CA / no TLS):** replace `tls internal` by nothing in the module → Interface 6's handshake test prints `expected exit 60 without --cacert, got 0` or Interface 2 fails to connect. Revert.
   - **M5 (wrong credentials accepted):** change `-u tester:secret` to `-u tester:wrong` in Interface 3 → `expected 200, got 401` — proves the 200 depends on the hash, not on the header's presence. Revert.
   - **M6 (a valid hash where the malformed one belongs):** in Interface 8 write a second `caddy hash-password --plaintext secret` output instead of `not-a-bcrypt-hash` → the `!= 200` assertion fails with `200`, proving the step reads the file it corrupts. Revert.
6. Commit with the subject above; body carries Step 1's two reds, Step 4's line and the six mutant lines.

**Negative control.** Interface 3 (200 with credentials) and Interface 7 must PASS; M5 turns Interface 3 red while Interface 2 stays green, so the fixture discriminates "auth required" from "auth broken".

**Tests** (assertion → mutant; fixture → discriminating row): 401 without credentials → M1; undeclared port refused → M2; plain HTTP never served → M3; TLS from the internal CA only → M4; 200 with credentials (control) → M5; malformed hash fails closed → M6.

**probes:**
- lan-vm-wired: `grep -c 'lan-vm = import ./tests/integration/lan-vm.nix' flake.nix` :: ge 1 :: expected after Step 1
- lan-vm-wired-once: `grep -c 'lan-vm = import ./tests/integration/lan-vm.nix' flake.nix` :: le 1 :: exact count, expected after Step 1
- lan-vm-two-nodes: `grep -c 'nodes.server\|server =\|client =' tests/integration/lan-vm.nix` :: ge 2 :: expected after Step 2

### IS13 (code, S) — Helm's loopback assertion admits LAN reach only through a lan-access site

**dependsOn:** IS11, HM3
**touches:** `nixosModules/helm.nix`, `flake.nix`
**acceptance:** helm-assertion-negative, host-core, lint
**areas:** isolation, helm, platform
**commit subject:** `isolation: Helm's loopback assertion, amended — LAN reach only as a lan-access site, a direct bind still refused (test: helm-assertion-negative, host-core, lint)`

**Why.** Answer 20 says the loopback assertion is "amended in the operator's words". `nixosModules/helm.nix:488-492` asserts `lib.hasPrefix "127.0.0.1:" cfg.listen || lib.hasPrefix "[::1]:" cfg.listen` with a message ending `Helm is localhost-only until Phase 10` (Assumption 13). "Until Phase 10" is now false in intent — Helm may be reached from the LAN, but only through a `services.lan-access` site whose upstream is Helm's loopback listen. The *condition* stays; the *message* is amended, and a second assertion binds the two modules: a site upstream on Helm's port must equal `services.helm.listen` byte for byte. HM3 extends this region first for `services.helm.api`; IS13 amends what HM3 leaves.

**Files.**
- Modify `nixosModules/helm.nix`: **both** "until Phase 10" sentences — the assertion message at `:491` and the `listen` option's description at `:329` (`grep -n 'until Phase 10' nixosModules/helm.nix` → `329`, `491`, 2026-09-14; re-anchor after HM3 with the same grep, never a line number) — replaced by the operator's approved sentence; one new assertion `helm-lan-site-upstream` in the same `assertions` list.
- Modify `flake.nix`: `helm-assertion-negative` (`:1737-1744`) gains a second arm `helmLanMismatchSystem` — Helm on `127.0.0.1:7700`, a `lan-access` site `helm` whose upstream is `127.0.0.1:7701` — throwing `helm-assertion-negative: a lan-access site named helm with an upstream that is not services.helm.listen DID NOT FAIL the build`.

**Interfaces.**
1. `services.helm.listen` remains loopback-only; the condition at `:490` is unchanged.
2. New assertion: every `services.lan-access.sites.<n>` whose `upstream` ends in `:${toString config.services.helm.port}` has `upstream == config.services.helm.listen`; message `services.lan-access.sites.<n>.upstream (<value>) fronts Helm's port but is not services.helm.listen (<listen>)`.
3. **Draft message for question 1** (verbatim once approved): `services.helm.listen must be loopback (127.0.0.1:<port> or [::1]:<port>), got '<listen>' -- Helm binds loopback only; the LAN reaches it solely as a services.lan-access site, over TLS from the internal CA and behind that site's auth`.
4. The `lan-access` module is not imported by `helm.nix`; the assertion reads `config.services.lan-access.sites or {}` so a system without the module still evaluates.

**Steps.**
1. **Red.** After IS11 and HM3 are in the tree: add the `helmLanMismatchSystem` arm to `helm-assertion-negative` **before** touching `helm.nix`; `nix build .#checks.x86_64-linux.helm-assertion-negative --no-link 2>&1 | grep -F 'DID NOT FAIL'` → `helm-assertion-negative: a lan-access site named helm with an upstream that is not services.helm.listen DID NOT FAIL the build`. Also `grep -c 'until Phase 10' nixosModules/helm.nix` → `2`. Paste both.
2. Add the new assertion and replace both sentences with the approved text.
3. **Green.** `nix build .#checks.x86_64-linux.helm-assertion-negative --no-link` → exit 0; `nix build .#checks.x86_64-linux.host-core --no-link` → exit 0 (core sets no `lan-access`, so Interface 4's `or {}` path is what `host-core` proves); `nix build .#checks.x86_64-linux.lint --no-link` → exit 0. `grep -c 'until Phase 10' nixosModules/helm.nix` → `0`.
4. **Mutants.**
   - **M1 (drop the new assertion):** delete it → Step 1's `DID NOT FAIL` line returns.
   - **M2 (loosen the loopback condition):** change `||` to `|| true` → the existing first arm fails: `helm-assertion-negative: services.helm.listen on 0.0.0.0 DID NOT FAIL the build` — the amendment did not widen what was refused.
   - **M3 (drop the `or {}`):** read `config.services.lan-access.sites` directly → `host-core` fails with `error: attribute 'lan-access' missing`.
   - **M4 (amend the message only):** leave `:329`'s description sentence → Step 3's grep prints `1`, not `0`, and the option's rendered documentation still says Helm waits for Phase 10. Revert each.
5. Commit with the subject above; body carries Step 1's red, Step 3's three exits and grep, and the mutant lines.

**Negative control.** `host-core` PASSES with no `lan-access` declared (Interface 4); M3 turns it red, so the control proves the assertion tolerates the module's absence rather than being vacuous.

**Tests** (assertion → mutant; fixture → discriminating row): site-upstream binding → M1; loopback condition unchanged → M2; absent-module tolerance (control, `host-core`) → M3; both sentences amended → M4.

**probes:**
- helm-phase10-gone: `grep -c 'until Phase 10' nixosModules/helm.nix` :: le 0 :: 2 at 662e87f (lines 329 and 491); expected 0 after Step 2
- helm-neg-arms: `grep -c 'DID NOT FAIL' flake.nix` :: ge 20 :: 19 at 662e87f (2026-09-14); IS13 adds one arm, IS11 and IS20 add more

### IS14 (docs, S) — brief §10: LAN access and the private overlay, in the operator's words

**dependsOn:** none
**touches:** `docs/brief.md`
**acceptance:** lint
**areas:** isolation, knowledge
**commit subject:** `isolation: brief §10 — LAN access under an internal CA and per-site auth, the private overlay as a later gated phase (test: lint)`

**Why.** Answer 20 says brief §10 is "amended in the operator's words". `docs/brief.md:353-357` is `## 10. Out of scope for now`, the last section (Assumption 9), and still lists "Remote access from outside the LAN" — the amendment rewrites §10 in place: what the LAN reaches, under what TLS and auth, the private overlay as its own later gated phase, and the rest of the out-of-scope list kept. KN18 supersedes §4/§7/§9 first (Cross-plan); IS14 touches only §10.

**Files.** Modify `docs/brief.md`: replace `:353-357` with a `## 10. LAN access, and what stays out of scope` section of two paragraphs and the retained list; no other line changes (`git diff --stat` → one file, and `git diff -U0 docs/brief.md | grep -c '^@@'` → 1 hunk).

**Interfaces.**
1. §10 keeps its number and remains the last section (`grep -n '^## ' docs/brief.md | tail -1` → `## 10.`).
2. Paragraph 1 is the LAN policy (Interface 4); paragraph 2 the overlay as a later gated phase, citing `docs/concepts/2026-09-11-private-overlay.md` by path (Interface 5; the path is fixed even if IS15 lands later).
3. The retained out-of-scope list: multi-user; access from outside the LAN except through the overlay once gated; the Pixel; attestation or measured boot.
4. **Draft for question 1** (paragraph 1, verbatim once approved): "The LAN reaches this machine only through sites declared in `services.lan-access`. Each site fronts one loopback upstream, serves TLS from Caddy's internal CA — whose root I install by hand on each client that may see it — and asks for one credential of its own, a password hash kept outside the Nix store, or WebAuthn the day a site needs it. What is not declared is not reachable: the build refuses any other bind off loopback."
5. **Draft paragraph 2:** "A private overlay — WireGuard declared in Nix, keys outside the store, no coordinator — is its own later phase with its own acceptance drill and 'test passed' gate; until it passes, nothing on this machine is reachable from beyond the LAN. Its shape is typed at `docs/concepts/2026-09-11-private-overlay.md`."

**Steps.**
1. **Red.** `grep -c 'services.lan-access' docs/brief.md` → `0`; `grep -c 'Remote access from outside the LAN' docs/brief.md` → `1`; `grep -c 'private-overlay' docs/brief.md` → `0`. Paste the three.
2. Replace `:353-357` with the approved text (Interfaces 3–5).
3. **Green.** `grep -c 'services.lan-access' docs/brief.md` → `1`; `grep -c 'docs/concepts/2026-09-11-private-overlay.md' docs/brief.md` → `1`; `grep -n '^## ' docs/brief.md | tail -1` → `## 10.`; `grep -c 'Remote access from outside the LAN' docs/brief.md` → `0`; `nix build .#checks.x86_64-linux.lint --no-link` → exit 0.
4. **Mutants.**
   - **M1 (append instead of amend):** leave `:353-357` and add a `## 11.` → `grep -n '^## ' docs/brief.md | tail -1` prints `## 11.` and `grep -c 'Remote access from outside the LAN'` → `1` — the contradiction survives; the Step 3 greps catch it.
   - **M2 (drop the concept cite):** remove the path → `grep -c 'docs/concepts/2026-09-11-private-overlay.md' docs/brief.md` → `0`.
   - **M3 (touch another section):** any edit outside `:353-357` → `git diff -U0 docs/brief.md | grep -c '^@@'` → `2`, an undeclared change in KN's region. Revert each.
5. Commit with the subject above; body carries Step 1's and Step 3's greps.

**Negative control.** `grep -c '^## 3. Invariants' docs/brief.md` → `1` before and after — §3 is untouched; M3 discriminates it (a stray edit to §3 changes the hunk count).

**Tests** (assertion → mutant; fixture → discriminating row): §10 amended in place → M1; concept cited by path → M2; single-hunk diff (control) → M3.

**probes:**
- brief-s10-last: `grep -n '^## ' docs/brief.md | tail -1 | grep -c '## 10\.'` :: ge 1 :: the last heading is 353:## 10. Out of scope for now at 662e87f (2026-09-14)
- brief-lan-access: `grep -c 'services.lan-access' docs/brief.md` :: ge 1 :: 0 at 662e87f; expected after Step 2
- brief-lan-access-once: `grep -c 'services.lan-access' docs/brief.md` :: le 1 :: exact count, expected after Step 2

### IS15 (docs, S) — the private overlay, typed as its own gated phase and not built

**dependsOn:** none
**touches:** `docs/concepts/2026-09-11-private-overlay.md`, `docs/ledger/subsystems.toml`
**acceptance:** lint
**areas:** isolation, knowledge, evidence
**commit subject:** `isolation: the private overlay typed as a gated phase — declared, key-outside-store, nothing built (test: lint)`

**Why.** Answer 20 names "a declared private overlay as its own later gated phase". No concept describes it (`ls docs/concepts | grep -c overlay` → 0, 2026-09-14), and Knowledge's `owns` globs stop at `docs/concepts/2026-09-08*` plus `concept-*` (`docs/ledger/subsystems.toml:248`), so a `2026-09-11-*` concept would belong to no subsystem (audit 5f). This task types the phase and registers the file; it builds nothing.

**Files.**
- Create `docs/concepts/2026-09-11-private-overlay.md` (~700 words): the phase's contract (Interfaces 1–6).
- Modify `docs/ledger/subsystems.toml`: append `"docs/concepts/2026-09-11-private-overlay.md",` to Knowledge's `owns` list after `"docs/concepts/concept-*",` (`:248`; re-anchor with `grep -n 'docs/concepts/concept-' docs/ledger/subsystems.toml`), one line, additive; lands after EV10/KN10 (Cross-plan).

**Interfaces** (the concept's numbered contract, in the file itself).
1. **Technology** (question 4): WireGuard as `networking.wireguard.interfaces.<name>`, declared in Nix; the alternative (a coordinated mesh) named in one paragraph with why it is not recommended (a coordinator sees peer metadata; the brief's stance is nothing leaves the machine).
2. **Keys outside the store:** `privateKeyFile` under `/var/lib/secrets/`, `0400 root:root`, an eval assertion `!(lib.hasPrefix "/nix/store" privateKeyFile)` in the module the phase will add; peers' public keys are Nix literals.
3. **What it exposes:** exactly the `services.lan-access` sites, to exactly the declared peers; no site bypasses its auth.
4. **What it never exposes:** the brokers (`10.100.3.1:3131`, `10.100.4.1:3141`), Helm's 7700/7710 except through a site, SSH unless declared, any port not in a site.
5. **Acceptance drill and gate:** from a peer outside the LAN, IS12's Interfaces 2–6 succeed the same way; from a non-peer, `wg show` shows no handshake; then "test passed".
6. **Its future checks, named now:** `overlay-eval`, `overlay-assertion-negative`, `overlay-vm` — reserved names; none exists yet (`grep -c 'overlay-' flake.nix` → 0).

**Steps.**
1. **Red.** `test -f docs/concepts/2026-09-11-private-overlay.md; echo $?` → `1`; `grep -c '2026-09-11-private-overlay' docs/ledger/subsystems.toml` → `0`. Paste both.
2. Write the concept: header (`# Concept — the private overlay as a gated phase`, date, status `typed, not built`), the six numbered terms, a closing "What this concept does not do" list.
3. Append the ledger line; `git add` the concept.
4. **Green.** `nix build .#checks.x86_64-linux.lint --no-link` → exit 0; `grep -c '2026-09-11-private-overlay' docs/ledger/subsystems.toml` → `1`; `grep -c '^[0-9]\. \*\*' docs/concepts/2026-09-11-private-overlay.md` → `6`; `git ls-files docs/concepts/2026-09-11-private-overlay.md | wc -l` → `1`.
5. **Mutants.**
   - **M1 (drop the ledger line):** revert `subsystems.toml` → `grep -c '2026-09-11-private-overlay' docs/ledger/subsystems.toml` → `0`; `python3 -c "import fnmatch,tomllib;d=tomllib.load(open('docs/ledger/subsystems.toml','rb'));print(any(fnmatch.fnmatch('docs/concepts/2026-09-11-private-overlay.md',g) for s in d['subsystem'] for g in s['owns']))"` → `False`.
   - **M2 (a key in the store):** change term 2's path to a `pkgs.writeText` → `grep -c '/var/lib/secrets' docs/concepts/2026-09-11-private-overlay.md` → `0`.
   - **M3 (build something):** add a `networking.wireguard` stanza to any `.nix` file → `git diff --stat | grep -c '\.nix'` → ≥ 1, an undeclared touch. Revert each.
6. Commit with the subject above.

**Negative control.** M1's python one-liner prints `True` after Step 3 — the file is owned; M1 turns it `False`, so the control discriminates registration from mere existence.

**Tests** (assertion → mutant; fixture → discriminating row): registered in the ledger (control) → M1; keys outside the store → M2; nothing built → M3.

**probes:**
- overlay-concept-terms: `grep -c '^[0-9]\. \*\*' docs/concepts/2026-09-11-private-overlay.md` :: ge 6 :: expected after Step 2
- overlay-concept-terms-exact: `grep -c '^[0-9]\. \*\*' docs/concepts/2026-09-11-private-overlay.md` :: le 6 :: exact count, expected after Step 2
- overlay-nothing-built: `grep -rc wireguard flake.nix nixosModules hosts | grep -vc ':0$'` :: le 0 :: all files 0 at 662e87f (re-run at commit)

### IS16 (code, M) — the broker VM proves streams cross the chokepoint: SSE intact, WebSocket upgrades refused or logged

**dependsOn:** none
**touches:** `tests/integration/broker-vm.nix`, `pkgs/broker/policy.py`, `tests/broker/test_policy.py`
**acceptance:** integration, addon, lint
**commit subject:** `isolation: the broker streams SSE through the audit and refuses or logs every WebSocket upgrade (test: integration, addon, lint)`

**Why.** IS2's fifth deferred question (Assumption 16, item 5) is "broker WebSocket/SSE OAuth pass-through — UNMEASURED, needing a VM test before any decision". The addon streams SSE (`pkgs/broker/policy.py:543-548`, `responseheaders` sets `flow.response.stream` to the usage tee when `content-type` starts `text/event-stream`; unit-covered at `tests/broker/test_policy.py:231`), but nothing says what happens to a WebSocket upgrade: `grep -in 'websocket\|upgrade' pkgs/broker/policy.py tests/broker/test_policy.py tests/integration/broker-vm.nix` → no hits. Invariant 3: every byte leaving crosses a chokepoint that can log and refuse; a stream the audit cannot see is a breach the current tests cannot detect.

**Files.**
- Modify `tests/integration/broker-vm.nix`: the `nginx` upstream gains `/events` (three `data:` frames a second apart, `text/event-stream`) and `/ws` (`proxy_pass` to a `python3 -m websockets` echo unit); the `testScript` (`:133`) gains S1–S4.
- Modify `pkgs/broker/policy.py`: in `requestheaders` (`:491`, after `_denied_path` and before the bodyPatch branch) an **upgrade request** is one whose `Upgrade` header value, lower-cased, is `websocket` **and** whose `Connection` header, split on commas and lower-cased, contains the token `upgrade` — both, by rule (RFC 6455 §4.1); any other combination (an `Upgrade: websocket` with `Connection: keep-alive`, a `Connection: upgrade` with no `Upgrade`) is an ordinary request and takes the existing path. An upgrade request to a host not carrying `allow_websocket: true` in the policy JSON is refused with `_deny_request(flow, "websocket-upgrade-unlisted")`; an admitted upgrade is audited `allow`, reason `websocket-upgrade`. The policy key defaults absent (deny), so no rendered policy changes.
- Modify `tests/broker/test_policy.py`: four unit tests, `test_websocket_upgrade_unlisted_denied`, `test_websocket_upgrade_listed_audited`, `test_upgrade_without_connection_token_is_ordinary` (an `Upgrade: websocket` + `Connection: keep-alive` request to an unlisted host is **not** denied and gets no upgrade audit line), `test_sse_tee_forwards_each_frame` (extends `:231`'s shape to assert frame-by-frame forwarding, not just tail capture).

**Interfaces.**
1. An SSE response from an allowlisted host reaches the client incrementally: S1 measures the wall time between first and last byte (≥ 2 s streamed, < 0.5 s buffered) and the usage JSONL gains one row with `streamed: true`.
2. A `GET /ws` with `Upgrade: websocket` to an allowlisted host **without** `allow_websocket` is denied with the broker's 403 and one audit line `verdict: deny, reason: websocket-upgrade-unlisted` (S2).
3. The same upgrade to a host **with** `allow_websocket: true` completes, the echo round-trips one frame, and the audit carries `verdict: allow, reason: websocket-upgrade` (S3).
4. A non-upgrade request is unaffected: the existing `broker-vm` steps all still pass (S4 is the existing script).
5. `renderPolicy` in `egressBroker.nix` is not touched: `allow_websocket` is read from the JSON with `.get(host, {}).get("allow_websocket", False)`; the VM test writes its policy JSON directly, as the existing fixture does.
6. An `Upgrade: websocket` request whose `Connection` header lacks the `upgrade` token is an ordinary request: never denied for the upgrade, no `websocket-*` audit line, injected and forwarded as before.

**Steps.**
1. **Red.** Add the four unit tests first: `nix develop -c pytest tests/broker/test_policy.py -k 'websocket or upgrade_without or sse_tee_forwards' -q 2>&1 | tail -3` → `3 failed, 1 passed` — the three that need the new path fail with `AttributeError`/`AssertionError: expected reason 'websocket-upgrade-unlisted'`; `test_upgrade_without_connection_token_is_ordinary` passes before the change and is kept as the regression that M5 turns red. Then add S1–S3 to the VM script without the addon change: `nix build .#checks.x86_64-linux.integration --no-link -L 2>&1 | grep -F 'websocket-upgrade-unlisted' | head -1` → the S2 assertion failure `expected a deny audit line for the upgrade, found none`. Paste both reds. If S1 is red too (buffered), that measurement is the fact IS17 records; do not change the tee until the red is understood.
2. Implement the `requestheaders` branch and the audit reason.
3. Extend the VM fixture (two nginx locations, the echo unit) and finish S1–S3.
4. **Green.** `nix develop -c pytest tests/broker -q 2>&1 | tail -1` → `N passed` where N = the pre-task count + 4 (measure the pre-task count with `nix develop -c pytest tests/broker -q --collect-only 2>&1 | tail -1`; `grep -c 'def test' tests/broker/test_policy.py` → 47 at 662e87f); `nix build .#checks.x86_64-linux.integration --no-link` → exit 0; `nix build .#checks.x86_64-linux.addon --no-link` → exit 0; `nix build .#checks.x86_64-linux.lint --no-link` → exit 0.
5. **Mutants.**
   - **M1 (admit every upgrade):** make the `allow_websocket` lookup return `True` → `test_websocket_upgrade_unlisted_denied` fails `expected 403, got None`, and S2 fails in the VM.
   - **M2 (deny every upgrade):** return `False` unconditionally → `test_websocket_upgrade_listed_audited` fails `expected reason 'websocket-upgrade', got 'websocket-upgrade-unlisted'`.
   - **M3 (drop the SSE tee):** in `responseheaders` set `flow.response.stream = False` → `test_sse_tee_forwards_each_frame` fails `expected 3 forwarded chunks, got 0` and S1 measures < 0.5 s.
   - **M4 (audit without refusing):** replace `_deny_request` by `_audit(flow, "deny", …)` only → S2's `curl` returns `101`/`200` instead of `403`: `expected 403, got 101`.
   - **M5 (detect on `Upgrade` alone):** drop the `Connection` token test → `test_upgrade_without_connection_token_is_ordinary` fails `expected no deny, got 'websocket-upgrade-unlisted'` — a false-positive deny of an ordinary request. Revert each.
6. Commit with the subject above; body carries Step 1's two reds, Step 4's counts and the five mutant lines, plus S1's measured seconds (the fact IS17 cites).

**Negative control.** S3 (a listed upgrade round-trips) and S4 (the existing steps) must PASS; M2 turns S3 red while S2 stays green, proving the fixture tells "refused because unlisted" from "refused always".

**Tests** (assertion → mutant; fixture → discriminating row): unlisted upgrade denied → M1; listed upgrade admitted and audited (control) → M2; SSE streamed frame by frame → M3; deny is a refusal not a log → M4; both headers required (Interface 6) → M5.

**probes:**
- broker-ws-reason: `grep -c 'websocket-upgrade-unlisted' pkgs/broker/policy.py` :: ge 1 :: 0 at 662e87f; expected after Step 2
- broker-tests-added: `grep -c 'def test' tests/broker/test_policy.py` :: ge 51 :: 47 at 662e87f (2026-09-14) plus the four tests of Step 1

### IS17 (docs, S) — the OAuth/router outcome: IS2's five deferred questions closed on the record

**dependsOn:** IS16
**touches:** `docs/research-2026-09-10-oauth-router-spike.md`, `docs/runbooks/lanes.md`
**acceptance:** lint
**areas:** isolation, knowledge
**commit subject:** `isolation: the OAuth/router spike's five questions closed — no machine read, no new routing, one instance per upstream, streams as measured (test: lint)`

**Why.** The spike's `## 5.` poses five questions and no section records an answer (Assumption 16; `grep -c '^## 7' docs/research-2026-09-10-oauth-router-spike.md` → 0). Assumption 24 accepts the five defaults; item 5's fact is what IS16 measured. `docs/runbooks/lanes.md` has no recipe for "one broker instance per named new upstream" (`grep -c 'per named upstream\|new upstream' docs/runbooks/lanes.md` → 0, 2026-09-14), though that pattern is item 3's whole answer.

**Files.**
- Modify `docs/research-2026-09-10-oauth-router-spike.md`: append `## 7. Outcome (2026-09-11, decision 44 closed)` after `## 6.` — five numbered closures, item 5 quoting IS16's commit body (the S1 seconds, the S2/S3 verdicts).
- Modify `docs/runbooks/lanes.md`: a new section `## Adding a static-key upstream: one broker instance, one key file` before `## Factory runs` (`:518`), the operator's recipe.

**Interfaces.**
1. Closures 1, 2, 4: no machine reads Proton Pass; no OAuth flow is routed through a static-inject broker; the `chatgpt-work` device sign-in is untouched.
2. Closure 3: a new static-key provider gets its own `services.egress-broker.instances.<name>`, `keyFile` under `/var/lib/secrets/`, netns and `HTTPS_PROXY`; never a second host in an existing allowlist; no Anthropic instance is named (§4 amendment).
3. Closure 5: SSE crosses the chokepoint streamed and audited; WebSocket upgrades are denied unless the policy lists `allow_websocket`; both are audit lines — IS16's measured fact, cited with its commit hash.
4. The runbook recipe: six numbered steps, each a Nix edit or an operator step (`install -m 0440 -o root -g egress-broker` for the key file, the switch, the `curl` from inside the netns), and what it never does (paste the key into Nix, share a key file between instances).

**Steps.**
1. **Red.** `grep -c '^## 7\. Outcome' docs/research-2026-09-10-oauth-router-spike.md` → `0`; `grep -c '^## Adding a static-key upstream' docs/runbooks/lanes.md` → `0`; `git log --oneline -1 --grep='isolation: the broker streams SSE' | wc -l` → `1` (if `0`, IS16 has not landed — stop).
2. Append `## 7.` with the five closures; item 5 cites IS16's hash and pastes its S1/S2/S3 lines.
3. Insert the runbook section.
4. **Green.** Both greps → `1`; `grep -c '^[1-5]\. ' <(sed -n '/^## 7\. Outcome/,$p' docs/research-2026-09-10-oauth-router-spike.md)` → `5`; `nix build .#checks.x86_64-linux.lint --no-link` → exit 0.
5. **Mutants.**
   - **M1 (an unmeasured closure):** replace item 5's cited hash with `TBD` → `sed -n '/^## 7/,$p' docs/research-2026-09-10-oauth-router-spike.md | grep -c 'TBD'` → `1`; the gate's correct-facts row re-runs `git show <hash> --stat` and finds no commit.
   - **M2 (name an Anthropic upstream):** add `api.anthropic.com` to the recipe's example → `grep -c 'api.anthropic.com' docs/runbooks/lanes.md` rises by one against the §4 amendment; the pre-task count is measured with the same command at commit.
   - **M3 (a key in Nix):** write the example `keyFile = "${pkgs.writeText …}"` → contradicts `seatLane.nix:89-90`'s assertion, which the recipe must cite; `grep -c 'writeText' docs/runbooks/lanes.md` → ≥ 1. Revert each.
6. Commit with the subject above.

**Negative control.** `grep -c '^## 6\. Commands run' docs/research-2026-09-10-oauth-router-spike.md` → `1` before and after — the appended section leaves §1–§6 unchanged; M1 does not touch it while the greps for `## 7.` do, so the two greps together discriminate "appended" from "rewritten".

**Tests** (assertion → mutant; fixture → discriminating row): closure 5 carries a measured fact → M1; no Anthropic instance → M2; key outside the store → M3; §6 untouched (control) → hunk count via `git diff -U0 -- docs/research-2026-09-10-oauth-router-spike.md | grep -c '^@@'` → `1`.

**probes:**
- spike-outcome-items: `sed -n '/^## 7\. Outcome/,$p' docs/research-2026-09-10-oauth-router-spike.md | grep -c '^[1-5]\. '` :: ge 5 :: expected after Step 2
- spike-outcome-items-exact: `sed -n '/^## 7\. Outcome/,$p' docs/research-2026-09-10-oauth-router-spike.md | grep -c '^[1-5]\. '` :: le 5 :: exact count, expected after Step 2
- lanes-recipe: `grep -c '^## Adding a static-key upstream' docs/runbooks/lanes.md` :: ge 1 :: 0 at 662e87f; expected after Step 3
- lanes-recipe-once: `grep -c '^## Adding a static-key upstream' docs/runbooks/lanes.md` :: le 1 :: exact count, expected after Step 3

### IS18 (code, M) — basket-vm: the mount lifecycle proved in a VM, tmpfs-only and clean on teardown

**dependsOn:** none
**touches:** `tests/integration/basket-vm.nix`, `flake.nix`
**acceptance:** basket-vm, lint
**areas:** isolation, platform
**commit subject:** `isolation: basket-vm proves a mounted basket lives only on tmpfs and leaves nothing on teardown (test: basket-vm, lint)`

**Why.** Invariant 1's ledger row `R-invariant-basket-tmpfs` (`docs/ledger/rules.toml:24`) is `UNMEASURED`: `tests/unit/30-mount.bats` runs under `unit` inside a user namespace and `tests/run-mount-tests.sh` under no check (Assumption 8); neither runs as real root on a real kernel with a persistent filesystem to leak onto — the only place "no plaintext lands on a persistent filesystem" can be measured. No `basket-vm` check exists (Assumption 6). Decision 54a deletes a rule with no check; this is the check.

**Files.**
- Create `tests/integration/basket-vm.nix`: `{ pkgs, basketPackage }: pkgs.testers.runNixOSTest { name = "basket"; nodes.machine = { environment.systemPackages = [ basketPackage pkgs.age pkgs.jq ]; }; testScript = "…steps 1–7…"; }` (IS12's skeleton with one node); the script generates a software age identity in the VM (`age-keygen -o /root/id.txt`) and writes a manifest with `examples/manifest.json`'s four keys.
- Modify `flake.nix`: `checks.basket-vm = import ./tests/integration/basket-vm.nix { inherit pkgs; basketPackage = basket; };` beside `seat-vm`; regenerate `docs/MAP.md`.

**Interfaces** (the VM script's steps).
1. `basket encrypt <src> --manifest m.json --recipients r.txt --store /var/lib/baskets` produces `payload.tar.age`; `grep -c 'SENTINEL-PLAINTEXT-7f3a' /var/lib/baskets/<id>/payload.tar.age` → `0`.
2. `basket mount /var/lib/baskets/<id> --identity /root/id.txt --runtime-dir /run/baskets` succeeds; `findmnt -no FSTYPE --target /run/baskets/<id>` → `tmpfs`; `findmnt -no TARGET -t tmpfs | grep -c baskets` → `1` (`basket.sh:174-175`).
3. `grep -rl 'SENTINEL-PLAINTEXT-7f3a' / --exclude-dir=proc --exclude-dir=sys --exclude-dir=dev --exclude-dir=run 2>/dev/null | wc -l` → `0` while mounted; `grep -c SENTINEL-PLAINTEXT-7f3a /run/baskets/<id>/note.txt` → `1`.
4. `basket verify /var/lib/baskets --lock baskets.lock` after `basket lock` → exit 0.
5. `basket teardown <id> --runtime-dir /run/baskets` → `findmnt --target /run/baskets/<id>` → exit 1 (not a mountpoint); `test -e /run/baskets/<id>; echo $?` → `1`; `test -e /run/baskets/.basket-tmpfs-<id>; echo $?` → `1`; step 3's `grep -rl` repeated **including** `/run` → `0`.
6. `swapon --show | wc -l` → `0` (no swap, as `basket doctor` demands, `basket.sh:351`), so paging cannot undercut the tmpfs-only claim.
7. `sync; echo 3 > /proc/sys/vm/drop_caches` before step 3, so a page-cache hit cannot mask a write.

**Steps.**
1. **Red.** `nix build .#checks.x86_64-linux.basket-vm --no-link 2>&1 | tail -1` → `… does not provide attribute 'checks.x86_64-linux.basket-vm'`. Then write the file with steps 1–7 plus a deliberate `cp /run/baskets/<id>/note.txt /var/tmp/leak` after step 2: `nix build .#checks.x86_64-linux.basket-vm --no-link -L 2>&1 | grep -F 'SENTINEL' | head -1` → step 3 fails `expected 0 files carrying the sentinel, got 1: /var/tmp/leak`. Remove the `cp`. Paste both.
2. Finish the fixture; wire `flake.nix`; `python3 pkgs/evidence/repomap.py --root . write`.
3. **Green.** `nix build .#checks.x86_64-linux.basket-vm --no-link -L 2>&1 | grep -E 'finished: run the VM test script|test script finished' | tail -1` → the finished line, exit 0; `nix build .#checks.x86_64-linux.lint --no-link` → exit 0.
4. **Mutants.**
   - **M1 (leak while mounted):** re-add Step 1's `cp` → step 3 red as in Step 1.
   - **M2 (skip teardown's unmount):** in the workspace, comment out `basket.sh:223-225`'s `umount` loop (a module-side revert, not committed) → step 5 fails `expected /run/baskets/<id> not to be a mountpoint`.
   - **M3 (bind instead of tmpfs):** replace the tmpfs mount with a bind of a persistent dir → step 2 fails `expected FSTYPE tmpfs, got ext4`.
   - **M4 (a sentinel that never existed):** change step 3's marker to one not in the fixture → step 3's positive `grep -c … note.txt` → `0` fails `expected the sentinel inside the mount`, proving the negative grep is not vacuous. Revert each.
5. Commit with the subject above; body carries Step 1's two reds, Step 3's line, the four mutant lines.

**Negative control.** Step 3's positive assertion (`grep -c … /run/baskets/<id>/note.txt` → `1`) must PASS; M4 turns it red while the negative `grep -rl` stays `0`, so the fixture proves the sentinel is real and only in tmpfs.

**Tests** (assertion → mutant; fixture → discriminating row): no plaintext on persistent fs → M1; clean teardown → M2; mount is tmpfs → M3; sentinel present in the mount (control) → M4.

**probes:**
- basket-vm-wired: `grep -c 'basket-vm = import ./tests/integration/basket-vm.nix' flake.nix` :: ge 1 :: 0 at 662e87f; expected after Step 2
- basket-vm-wired-once: `grep -c 'basket-vm = import ./tests/integration/basket-vm.nix' flake.nix` :: le 1 :: exact count, expected after Step 2
- basket-vm-steps: `grep -c 'SENTINEL-PLAINTEXT-7f3a' tests/integration/basket-vm.nix` :: ge 3 :: expected after Step 2

### IS19 (code, S) — one named check per §3 invariant with mechanical coverage

**dependsOn:** IS18
**touches:** `flake.nix`
**acceptance:** invariant-basket-tmpfs, invariant-credential-plaintext, invariant-egress-chokepoint, invariant-policy-nix, lint
**areas:** isolation, platform
**commit subject:** `isolation: one named check per invariant — basket-tmpfs, credential-plaintext, egress-chokepoint, policy-nix (test: invariant-basket-tmpfs, invariant-credential-plaintext, invariant-egress-chokepoint, invariant-policy-nix, lint)`

**Why.** Invariant rows 1, 2, 3, 5 (`docs/ledger/rules.toml:24, :36, :48, :72`) are `UNMEASURED` (Assumption 7) and the ledger's `check` field takes one name; invariants 3 and 5 are covered by several checks with no single name; no `invariant-*` check exists (Assumption 6). Assumption 25: four aggregates, each a `runCommand` depending on exactly the checks that prove its invariant, so the rules audit (KN) has one name per row and 54a measures rather than deletes. Invariants 4 and 6 stay on operator acceptance.

**Files.** Modify `flake.nix`: four attributes in a new `# Invariant aggregates (IS19)` region after `basket-vm`: `invariant-basket-tmpfs` ← `basket-vm`, `unit`; `invariant-credential-plaintext` ← `seat-assertion-negative`, `lane-assertion-negative`, `seat-eval`, `module-eval`, `addon`; `invariant-egress-chokepoint` ← `addon`, `integration`, `lane-vm`, `seat-vm`, `host-core`; `invariant-policy-nix` ← `assertion-negative`, `lane-assertion-negative`, `seat-assertion-negative`, `seat-eval`, `manifests-validate`. Each is `pkgs.runCommand "<name>" { deps = [ <the checks> ]; } "echo $deps > $out"`, so the aggregate builds only when every component builds. Membership rule, stated in the region's comment: an aggregate lists every check whose task's Tests line names a mutant of that invariant; the lists above are the rule's extension at this task's base, and a later task that adds such a check appends its name in the same commit (the comment says so; a name absent from `flake.nix` makes the aggregate fail eval, Interface 3). The comment also spells out that `lane-vm` (the model *lane*, `tests/integration/lane-vm.nix`, existing) and `lan-vm` (IS12's *LAN* access test) differ by one letter, and only `lane-vm` is a member — `lan-vm` proves ingress, not egress. Regenerate `docs/MAP.md`.

**Interfaces.**
1. Each aggregate's name is exactly the string the rules audit will write in the row's `check` field; the four names are fixed here.
2. An aggregate is red whenever any component is red and green otherwise; it runs nothing of its own.
3. Every component named exists in `flake.nix` at this task's base (`grep -c "^\s*$c =" flake.nix` → `1` each); `basket-vm` exists because IS18 precedes.
4. The region's comment lists, per aggregate, the invariant's brief §3 text and rule id.

**Steps.**
1. **Red.** `for c in invariant-basket-tmpfs invariant-credential-plaintext invariant-egress-chokepoint invariant-policy-nix; do nix build .#checks.x86_64-linux.$c --no-link 2>&1 | tail -1; done` → four `does not provide attribute` errors. Paste.
2. Add the four attributes and the comment; `python3 pkgs/evidence/repomap.py --root . write`.
3. **Green.** The Step 1 loop → four exit 0; `nix build .#checks.x86_64-linux.lint --no-link` → exit 0; `nix eval --json .#checks.x86_64-linux --apply 'c: builtins.filter (n: builtins.match "invariant-.*" n != null) (builtins.attrNames c)'` → the four names.
4. **Mutants** (one per aggregate, each a revert in one component, applied in the workspace and reverted):
   - **M1:** IS18's M3 (bind instead of tmpfs) → `nix build .#checks.x86_64-linux.invariant-basket-tmpfs` fails with `basket-vm`'s `expected FSTYPE tmpfs`.
   - **M2:** delete `seatLane.nix:89-90`'s store-path assertion → `invariant-credential-plaintext` fails with `seat-assertion-negative: services.seat-lane.keyFile = a store path DID NOT FAIL the build`.
   - **M3:** IS16's M1 (admit every upgrade) or, if IS16 has not landed, delete `_deny` at `policy.py:298` → `invariant-egress-chokepoint` fails through `addon`.
   - **M4:** in `flake.nix:1277-1284`'s `assertion-negative`, swap the `throw` and the `runCommand` branches → `invariant-policy-nix` fails `assertion-negative: … DID NOT FAIL the build`.
   - **M5 (an empty aggregate):** set one aggregate's `deps = [ ]` → it stays green under M1–M4: `nix build` exits 0 while its component is red. This is the vacuity mutant; the killing check is Interface 3's `grep` plus `nix derivation show .#checks.x86_64-linux.invariant-basket-tmpfs | jq '.[].inputDrvs | length'` → `0` under M5, ≥ 2 after Step 2.
5. Commit with the subject above; body carries Step 1's errors, Step 3's list, and M1–M5.

**Negative control.** All four aggregates PASS at the base; M5 shows an aggregate that passes for the wrong reason, and the `inputDrvs` count discriminates it.

**Tests** (assertion → mutant; fixture → discriminating row): invariant 1 aggregate → M1; 2 → M2; 3 → M3; 5 → M4; non-vacuity (control) → M5.

**probes:**
- invariant-checks-named: `grep -c '^\s*invariant-[a-z-]* =' flake.nix` :: ge 4 :: 0 at 662e87f; expected after Step 2
- invariant-checks-exact: `grep -c '^\s*invariant-[a-z-]* =' flake.nix` :: le 4 :: exact count, expected after Step 2
- invariant-inputdrvs: `nix derivation show .#checks.x86_64-linux.invariant-basket-tmpfs | jq '[.[].inputDrvs | length] | add'` :: ge 2 :: expected after Step 2

### IS20 (code, M) — the seat's namespace admits Helm's second port and nothing else new

**dependsOn:** IS10
**touches:** `nixosModules/seatLane.nix`, `nixosModules/egressBroker.nix`, `flake.nix`, `tests/integration/seat-vm.nix`
**acceptance:** seat-eval, seat-assertion-negative, seat-vm, lint
**areas:** isolation, platform, seat
**commit subject:** `isolation: the seat reaches Helm's second port on the lane's host-side address, never 7700 (test: seat-eval, seat-assertion-negative, seat-vm, lint)`

**Why.** Answer 11 (Charter map). The seat's namespace reaches the host only on the broker's listen port: `nixosModules/egressBroker.nix:194-217`'s `input-seat` chain accepts `iifname "veb-seat" tcp dport 3141 ip saddr 10.100.4.2`, then established/related, then `iifname "veb-seat" drop`; its comment (`:200-205`) states that an accept in one base chain does not short-circuit another base chain of the same hook — so the accept must be rendered **inside** `input-seat` before the drop, and `nixos-fw` must allow the port too (`:188` does that for `listenPort`). Helm's API on `10.100.4.1:7710` (Assumption 18) is therefore unreachable from a seat today; `services.seat-lane` has ten options (`grep -c mkOption nixosModules/seatLane.nix` → 10, 2026-09-14), none a host port. R8 (`hook-guard.py`, Seat/Harness) refuses 7700 at the tool layer; this task adds the network half and pins, as a rule, that no port a refused Helm surface binds becomes the opened one.

**Files.**
- Modify `nixosModules/egressBroker.nix`: the instance submodule (`:44-50`) gains `extraInputRules` (`listOf str`, `default = [ ]`, "nftables rules rendered inside `input-<name>` after the broker accept and before its trailing drop; each must be scoped to `iifname veb-<name>` and `ip saddr namespaceAddress`"); the chain text at `:214-216` renders them between the `listenPort` accept and `ct state established,related accept`.
- Modify `nixosModules/seatLane.nix`: option `helmApiPort` (`nullOr port`, `default = null`, description naming answer 11); one assertion with three arms — `cfg.helmApiPort == null || (cfg.helmApiPort != 7700 && cfg.helmApiPort != cfg.listenPort && cfg.helmApiPort != (config.services.helm.port or 7700))`, message `services.seat-lane.helmApiPort (<n>) must not be Helm's control page (7700 or services.helm.port) nor the broker's listenPort (<listenPort>), answer 11a`; when non-null: `services.egress-broker.instances.seat.extraInputRules = [ "iifname \"veb-seat\" ip saddr ${cfg.namespaceAddress} tcp dport ${toString cfg.helmApiPort} accept" ]`, `networking.firewall.interfaces.veb-seat.allowedTCPPorts = [ cfg.helmApiPort ]`, and `/etc/seat-lane/helm-api-port` beside `wave-jobs` (`:147-154`).
- Modify `flake.nix`: `seat-eval` (asserts on the real core config, `:2226-2232`; `lib.hasInfix` over `c.networking.nftables.tables.egress-broker.content` as `lane-eval` does at `:2184`) gains: on core, `helmApiPort == null` and no `dport 7710` in the table; on a fixture `seatHelmPortSystem` (`helmApiPort = 7710`), `input-seat`'s text contains `iifname "veb-seat" ip saddr 10.100.4.2 tcp dport 7710 accept` **before** its `iifname "veb-seat" drop` (string index compare) and `firewall.interfaces.veb-seat.allowedTCPPorts` contains 7710. `seat-assertion-negative` gains three arms in its shape (`:2439-2458`): `seatHelmPort7700System` (`helmApiPort = 7700`), `seatHelmPortBrokerSystem` (`3141`), `seatHelmPortMovedSystem` (imports `self.nixosModules.helm`, `services.helm.port = 7701`, `helmApiPort = 7701`), each throwing `seat-assertion-negative: services.seat-lane.helmApiPort = <n> (<case>) DID NOT FAIL the build`.
- Modify `tests/integration/seat-vm.nix`: the fixture sets `helmApiPort = 7710` and runs a `python3 -m http.server 7710 --bind 10.100.4.1` unit and a second on `7700`; the script gains two steps — from inside the seat's netns `curl -s -o /dev/null -w '%{http_code}' http://10.100.4.1:7710/` → `200`; `curl -m 3 -s -o /dev/null -w '%{http_code}' http://10.100.4.1:7700/; echo $?` → exit `7` or `28` (refused/dropped).

**Interfaces.**
0. **Step 0** (Assumption 18): `nix eval .#nixosConfigurations.core.config.services.helm.api.port` → `7710` once HM3 has landed; if the attribute is missing, HM3 has not landed — stop, the seat reports it.
1. `helmApiPort = null` renders no rule, no firewall port and no `/etc` file; the shipped nftables text is byte-identical (`seat-eval`'s core arm).
2. `helmApiPort = N` accepts TCP from `namespaceAddress` to `hostAddress:N` on `veb-seat` inside `input-seat` before its drop, plus the `nixos-fw` allow; nothing else new; the return path is `output-seat`'s existing established/related accept.
3. Refused at eval, by rule: N = 7700, N = `services.helm.port` (whatever it is), N = the broker's `listenPort` (a second accept at a dport `input-seat` already handles).
4. R8 in `hook-guard.py` is untouched (`git diff --stat -- pkgs/dsh-openrouter` → empty).

**Steps.**
1. **Red.** Add the three negative arms to `seat-assertion-negative` before touching the module: `nix build .#checks.x86_64-linux.seat-assertion-negative --no-link 2>&1 | tail -1` → `error: The option 'services.seat-lane.helmApiPort' does not exist` (the fixture cannot even set it — paste this as the red); add the two `seat-vm` steps: `nix build .#checks.x86_64-linux.seat-vm --no-link -L 2>&1 | grep -F '7710' | head -1` → the first step fails `expected 200 from 10.100.4.1:7710, got 000` (dropped by `input-seat`). Paste both.
2. Add `extraInputRules`, the option, the assertion, the rule, the firewall port, the `/etc` file.
3. Wire the `seat-eval` arms (Interfaces 1–2) and the `seat-vm` fixture units.
4. **Green.** `nix build .#checks.x86_64-linux.seat-eval --no-link` → exit 0; `… seat-assertion-negative` → exit 0; `… seat-vm -L 2>&1 | grep -E 'finished: run the VM test script' | tail -1` → the line, exit 0; `… lint` → exit 0; `nix eval .#nixosConfigurations.core.config.services.seat-lane.helmApiPort` → `null`.
5. **Mutants.**
   - **M1 (drop the 7700 arm):** → `seat-assertion-negative: services.seat-lane.helmApiPort = 7700 (control page) DID NOT FAIL the build`.
   - **M2 (accept any source):** remove `ip saddr ${cfg.namespaceAddress}` from the rule → `seat-eval` fails `seat-eval: the helmApiPort accept must be scoped to the namespace address`.
   - **M3 (open 7700 too):** add a second rule for `7700` → the `seat-vm` step 2 fails `expected 7700 refused from the seat, got 200`.
   - **M4 (render when null):** drop the `lib.mkIf (cfg.helmApiPort != null)` guard → `seat-eval`'s core arm fails `seat-eval: core renders a helmApiPort rule with helmApiPort = null`.
   - **M5 (drop the listenPort arm):** → `… helmApiPort = 3141 (broker listenPort) DID NOT FAIL the build`.
   - **M6 (literal 7700 only):** replace `config.services.helm.port or 7700` by `7700` → `… helmApiPort = 7701 (services.helm.port moved) DID NOT FAIL the build` — the spelling outside the list.
   - **M7 (a separate base chain):** render the accept as `chain input-seat-helm { … priority filter - 2; … }` instead of inside `input-seat` → `seat-eval`'s index assertion fails (`accept not inside input-seat before its drop`) and `seat-vm` step 1 gets `000` again. Revert each.
6. Commit with the subject above.

**Negative control.** `seat-vm` step 1 (7710 answers `200`) and Interface 1 on core must PASS; M4 turns the core arm red while the VM stays green, so the control separates "inert by default" from "works when set".

**Tests** (assertion → mutant; fixture → discriminating row): 7700 refused at eval → M1; listenPort refused → M5; Helm's moved port refused (the rule) → M6; source-scoped accept → M2; 7700 unreachable on the wire → M3; accept placed before the drop → M7; inert when null (control) → M4.

**probes:**
- seat-helm-option: `grep -c 'helmApiPort' nixosModules/seatLane.nix` :: ge 4 :: 0 at 662e87f; expected after Step 2
- seat-mkoption-count: `grep -c mkOption nixosModules/seatLane.nix` :: ge 11 :: 10 at 662e87f (2026-09-14) plus helmApiPort
- seat-mkoption-exact: `grep -c mkOption nixosModules/seatLane.nix` :: le 11 :: exact count, one option added
- seat-extra-rules: `grep -c 'extraInputRules' nixosModules/egressBroker.nix` :: ge 2 :: 0 at 662e87f; the option and its rendering
- seat-core-inert: `nix eval .#nixosConfigurations.core.config.services.seat-lane.helmApiPort` :: eq null :: expected after Step 2; Platform sets 7710 in hosts/core/seat.nix in a later PL/HM task

### IS21 (code, XS) — core enables lan-access with the sites the operator named

**dependsOn:** IS11, IS12, IS13
**touches:** `hosts/core/lan-access.nix`, `hosts/core/default.nix`
**acceptance:** host-core, lint
**areas:** isolation, platform
**commit subject:** `isolation: core fronts the named sites on the LAN through lan-access (test: host-core, lint)`

**Why.** IS11's module ships disabled and IS12 proves it in a VM; nothing declares it on `core`. `hosts/core/default.nix:4-17` is the import list and there is no `lan-access` anywhere under `hosts/` (`grep -rc 'lan-access' hosts` → all 0, 2026-09-14). Question 2's recommendation: Helm's page only — `helm = { upstream = "127.0.0.1:7700"; hashFile = "/var/lib/lan-access/helm.bcrypt"; user = "dalhaka"; }`. IS13 precedes so the switch carries the amended loopback assertion. The operator's single switch carries it.

**Files.**
- Create `hosts/core/lan-access.nix`: `_: { services.lan-access = { enable = true; interface = "<the LAN interface>"; sites.helm = {…}; }; }` — the interface name is measured by the operator (`ip -br link | awk '$2=="UP"{print $1}'`, an Operator step; the seat writes the value the operator pastes into the task's dispatch note, never guesses).
- Modify `hosts/core/default.nix`: two lines in the `imports` list (`:4-17`) — `./lan-access.nix` and `../../nixosModules/lanAccess.nix`, the second in the form EV1 used for `../../nixosModules/usageIngest.nix` at `:16` (Assumption 14), so no `flake.nix` touch.

**Interfaces.**
1. `nixosConfigurations.core.config.services.lan-access.enable` → `true`; `.sites` has exactly the operator's names (`builtins.attrNames` → `[ "helm" ]`).
2. `config.services.caddy.virtualHosts` on core has exactly one entry, `helm.core.local`, and `config.networking.firewall.interfaces.<interface>.allowedTCPPorts == [ 80 443 ]`.
3. The hash file is an operator artifact under `/var/lib/lan-access/` (IS11's A4; the directory is `0710 root caddy` from IS11's tmpfiles rule, created at the switch) — the task never creates or reads it; until it exists `caddy.service` fails to load its config (IS11 Interface 3), so the Operator step runs right after the switch.
4. `host-core` proves IS13's site-upstream assertion on the real config (for `helm`, `upstream == config.services.helm.listen`); this task adds no assertion of its own (no `flake.nix` touch).

**Steps.**
1. **Red.** `nix eval .#nixosConfigurations.core.config.services.lan-access.enable 2>&1 | tail -1` → `error: attribute 'lan-access' missing` (the module is not imported on core); `test -f hosts/core/lan-access.nix; echo $?` → `1`. Paste both.
2. Create the host file; add the two import lines.
3. **Green.** `nix eval .#nixosConfigurations.core.config.services.lan-access.enable` → `true`; `nix eval --json .#nixosConfigurations.core.config.services.caddy.virtualHosts --apply builtins.attrNames` → `["helm.core.local"]`; `nix build .#checks.x86_64-linux.host-core --no-link` → exit 0; `… lint` → exit 0.
4. **Mutants.**
   - **M1 (wrong upstream):** set `upstream = "127.0.0.1:7701"` → `host-core` fails with IS13's `services.lan-access.sites.helm.upstream (127.0.0.1:7701) fronts Helm's port but is not services.helm.listen (127.0.0.1:7700)`.
   - **M2 (a store-path hash):** `hashFile = "${pkgs.writeText "h" "x"}"` → `host-core` fails with IS11's A2 message; `hashFile = "/var/lib/secrets/helm.bcrypt"` → A4's message.
   - **M3 (an undeclared site):** add `sites.feed` → Interface 1's `attrNames` prints two names; the drill's row 2 would reach a site the operator did not name. Revert each.
5. Commit with the subject above.

**Negative control.** `nix eval .#nixosConfigurations.core.config.services.helm.listen` → `127.0.0.1:7700` before and after — Helm still binds loopback (IS13's condition); M1 discriminates it (the site's upstream and Helm's listen diverge and the build refuses).

**Tests** (assertion → mutant; fixture → discriminating row): upstream bound to Helm's listen → M1; hash outside the store and under the traversable directory → M2; exactly the named sites (control) → M3.

**Operator** (right after the switch): `caddy hash-password --plaintext '<chosen>' | sudo install -m 0400 -o caddy -g caddy /dev/stdin /var/lib/lan-access/helm.bcrypt && sudo systemctl restart caddy.service`; acceptance `sudo stat -c '%U:%G %a' /var/lib/lan-access/helm.bcrypt` → `caddy:caddy 400` and `systemctl is-active caddy.service` → `active`; rollback `sudo rm /var/lib/lan-access/helm.bcrypt` (Caddy then refuses to load — every site refuses connections — which is the signal to roll back the generation).

**probes:**
- core-lan-sites: `nix eval --json .#nixosConfigurations.core.config.services.lan-access.sites --apply builtins.attrNames` :: eq ["helm"] :: expected after Step 2
- core-helm-listen: `nix eval --raw .#nixosConfigurations.core.config.services.helm.listen` :: eq 127.0.0.1:7700 :: nixosModules/helm.nix:325 default at 662e87f

