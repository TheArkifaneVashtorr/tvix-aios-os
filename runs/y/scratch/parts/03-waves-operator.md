
## Waves

Derived on the F4 snapshot by `tasks.py`'s own code, three ways, outputs pasted verbatim (`/tmp/draft-scratch/queries.log` holds every command with its exit code):

1. **The live-tree draft check** — `python3 pkgs/evidence/tasks.py --root . --runs-dir /nonexistent --store /nonexistent check --draft /tmp/draft-scratch/2026-09-11-generation.md` (the draft copied under this plan's basename, Assumption 29):
```
<<CHECK-DRAFT-LIVE>>
```
   Every line is a MAP-currency line for a check this plan creates or moves (`core-media-wiring` by GN10; media's checks by GN12), an artefact of checking before landing: `draft_rules` reads `docs/MAP.md`'s Checks section, which the task that adds the check regenerates in its own commit (G5's exemption). No unknown key: EV10 and EV15 are typed in the landed Evidence plan (Assumption 2), GN9 is typed here.
2. **The scratch-copy form** (rubric row 13; `cp -a` of the tree to `/tmp/draft-scratch/tree`, the draft placed as `docs/superpowers/plans/2026-09-11-generation.md`, a one-repo `--repos` file naming that copy): `check` →
```
<<CHECK-SCRATCH>>
```
   `waves --repo nixos-agent-env --json` →
```
<<WAVES-SCRATCH>>
```
   No `GN` group appears in this repo's waves: GN1–GN9 leave this repo's list on their `**repo:** media` line, GN10 is `blocked` on GN9 until media's `main` carries it (Assumption 16), GN11 on EV10 and GN10, GN12 on GN11. New `conflicts` rows the draft adds (the rows with a `GN` key; the 411 pre-existing rows are Assumption 1's):
```
<<CONFLICTS-NEW>>
```
3. **The media-side waves** — `tasks.wave_structure` over the nine `repo: media` sections parsed from the draft with state `ready` (the media repo has no path here, so `waves --repo media` prints `[]`; the function is the tool's own peel-off, run by `python3 -c` over `parse_plan`):
```
<<WAVES-MEDIA-SYNTH>>
```

Read as a schedule: **wave 1** `"GN1 GN7"` — one seat group (both touch media's `flake.nix`; GN1 first by key order); **wave 2** `"GN2" "GN3" "GN5"` — three seats in parallel; **wave 3** `"GN4" "GN6"` — two seats; **wave 4** `"GN8"` — after EV15 has landed here (the landing order puts Evidence first, Assumption 4); **wave 5** `"GN9"`; then, in this repo, **GN10** (switch #N), the landing act, **GN11**, **GN12** (switch #N+1). Two seats in one group serialise in key order inside one workspace; two groups in one wave run at once.

## Cross-plan

Ordering for every live overlap with this plan's `touches` (Assumption 17), who goes first and why:

- **`flake.nix` — GN10, GN12 × PL2–PL5 (`blocked`), EV16, FIX6, N13, N15, N17, HH2, HH3, IS4, EV1 (`ready`), HH6, HH8, HH9, SP5, EV6, IS5b, FA23 (`blocked`).** The published batch order (Platform's chain first, then single-attribute check additions — EV16, HM3, GN10, KN13 — then VM hunks, then GN11/GN12, KN15–KN19, FA23 last: `2026-09-11-evidence.md`, Cross-plan) stands; GN10 adds one input line, one module line and one check attribute — three hunks that rebase in minutes; GN12 restructures `checks.${system}` into a `let … in` and is last of its group. Before every GN launch on this file the orchestrator waits for any `running`/`ran` key sharing it (Dispatch).
- **`hosts/core/default.nix` — GN10 × PL4 (`blocked`), EV1 (`ready`).** Additive `imports`; PL4 first when it is `ready` before GN10, else GN10 first — either rebases one line.
- **`hosts/core/proton-backup.nix`, `docs/ledger/repos.toml`, `docs/ledger/plan-status.toml` — GN10/GN11 × PL6 (`blocked`).** PL6 first (increment 2; GN11 copies its row shape, Assumption 12); each is an additive row or path.
- **`docs/ledger/subsystems.toml` — GN11 × EV10, FA13, PL1 (`ready`).** EV10 first (it alone turns `subsystems-manifest` green and every later editor integrates against it — GN11 `dependsOn: EV10`); FA13 and PL1 append to their own rows; GN11 edits only the Generation row and re-runs `subsystems.py write`.
- **`docs/MAP.md` — GN10, GN12 × every key that regenerates it.** Regeneration only: whichever lands last re-runs `repomap.py --root . write`.
- **`docs/runbooks/backup.md` — GN10 × none open.**
- **Evidence (`EV`):** GN8 `dependsOn: EV15` (the `feed` surface and the five fields, Assumption 9); GN11 `dependsOn: EV10` (the plans-directory glob). **Helm (`HM`):** HM8's `/v1/engage` is the endpoint GN8 posts to (Assumption 33); the feed link or embed is Helm's; nothing here touches a Helm file. **Platform (`PL`):** the landing act copies PL Q6(b)'s shape; `pkgsHost` is introduced by GN12 unless Platform's chain has a binding of that name by then (Step 0 measures). **Isolation (`IS`):** the LAN face (question 3) is IS's increment-4 task; GN10's `lan.enable = false` is the assertion it flips. **Factory (`FA`):** `factory-dispatch` for a ledger-less sibling (Assumption 36 i).

## Operator

Every step is one command with its acceptance after the arrow; nothing here is a seat's act (G1). Unit names come from `docs/runbooks/media-worlds.md`, which GN10 writes from `nix eval` (its Interfaces 6); the ports below are GN10's literals (`sfw` 8288/8388, `nsfw` 8289/8389).

**Before any wave (A3, A9).**
0. `ls ~/factory/runs | grep -c '^gn'` → `0` (the run names of Dispatch are free); `git -C ~/flakes/media status --short` → empty. Wave 2 starts three seats: if the board's last top-up line is older than the activity export's last ingested day (`evidence bundle --markdown`, the spend row), top up first — a proxy: the export is a manual download and the balance itself is never read.

**After GN10 integrates — switch #N.**
1. `nix build .#checks.x86_64-linux.core-media-wiring -L --no-link && nix build .#checks.x86_64-linux.host-core -L --no-link && nix build .#checks.x86_64-linux.core-backup-wiring -L --no-link` → all three build.
2. `nix build .#nixosConfigurations.core.config.system.build.toplevel -o /tmp/gn10-result && nix store diff-closures /run/current-system /tmp/gn10-result` → **prediction** (A2): `+ comfyui-<version>` with its torch/CUDA closure (gigabytes), `+ comfy-worlds-init`, `+ media-comfy`, `+ comfy-upstream-probe`, `+ media-fetch-models`, `+ comfy-feed`, `+ comfy-feed-index`, `+ comfy-mutate`, a second `python3` from media's own nixpkgs pin (Assumption 25; gone after GN12), and the `egress-broker-media` and `comfy-upstream-probe` units in `etc`; **no `caddy` line** (question 3(a)). The measured delta in GN10's commit body is pasted beside this line before the switch; a mismatch is a finding against this plan.
3. `readlink /nix/var/nix/profiles/system` → `system-<N-1>-link` — the rollback target; it goes into the board line.
4. `sudo nix-env -p /nix/var/nix/profiles/system --set /tmp/gn10-result && sudo /tmp/gn10-result/bin/switch-to-configuration switch` → then `systemctl is-active egress-broker-media.service` → `active`; `ip netns list | grep -c egress-media` → `1`; `systemctl list-timers comfy-upstream-probe.timer --no-legend | wc -l` → `1` (spec §5 Q8 measured: a system timer, started by the switch).
5. `systemctl --user list-units 'comfy-*' --all --no-legend | awk '{print $1, $4}'` → every unit `inactive` (a switch starts no user unit), the names as the runbook lists them.
6. `ls /home/dalhaka/comfyui/models | wc -l` → above `0` (A3: the models the media drills fetched; if `0`, run media's runbook fetch first — the operator's act through media's own path, not this plan's).
7. `systemctl --user start <sfw generator unit>` then `curl --noproxy '*' -s http://127.0.0.1:8288/system_stats | head -c 120` → JSON beginning `{"system"` (ComfyUI up on the world's port).
8. `journalctl --user -u <sfw generator unit> --no-pager | grep -i aimdo` → paste; a line naming aimdo loaded and no `IMPORT FAILED` is the claim's evidence (step 23).
9. `systemctl --user start <sfw feed unit>` then `curl --noproxy '*' -s http://127.0.0.1:8388/healthz` → `ok sfw`.
10. `ls /home/dalhaka/comfyui/worlds/sfw/output | wc -l` → above `0` (the generator has rendered), then `curl --noproxy '*' -s http://127.0.0.1:8388/ | grep -c '<article'` → above `0`.
11. `N=$(curl --noproxy '*' -s http://127.0.0.1:8388/ | grep -o 'name="name" value="[^"]*"' | head -1 | cut -d'"' -f4); curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' -d "name=$N" http://127.0.0.1:8388/like` → `303`; `python3 -c "import sqlite3; print(sqlite3.connect('/home/dalhaka/comfyui/worlds/sfw/feed.sqlite').execute('select count(*) from likes').fetchone()[0])"` → `1`.
12. `curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' -d "name=$N" http://127.0.0.1:8388/regenerate` → `303`; within a minute `curl --noproxy '*' -s http://127.0.0.1:8388/jobs | python3 -c "import json,sys; print([(j['kind'], j['state']) for j in json.load(sys.stdin)])"` → `[('regenerate', 'done')]` (or `submitted` while ComfyUI renders), and one more PNG in `output/`.
13. `curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' -d "name=$N" -d "prompt=a red fox, drill" http://127.0.0.1:8388/edit` → `303`; the `/jobs` line → an `edit` row.
14. `systemctl --user start comfy-mutate-sfw.service; systemctl --user show -p Result --value comfy-mutate-sfw.service` → `success`; the `/jobs` line → eight `mutate` rows. Then determinism: `B=$(systemctl --user show -p ExecStart --value comfy-mutate-sfw.service | sed -n 's/.*path=\([^ ;]*\).*/\1/p'); "$B" --world sfw --root /home/dalhaka/comfyui --dry-run --seed 1 >/tmp/m1; "$B" --world sfw --root /home/dalhaka/comfyui --dry-run --seed 1 >/tmp/m2; cmp /tmp/m1 /tmp/m2 && echo identical` → `identical`.
15. `sudo systemctl start comfy-upstream-probe.service; systemctl show -p Result --value comfy-upstream-probe.service` → `success`; `journalctl -u comfy-upstream-probe.service --no-pager | tail -5` → the probe's proposal lines, no traceback; `sudo grep -c 'api.github.com' /var/lib/egress-broker/media/audit.jsonl` → above `0` (a count over a local audit log that never leaves the machine).
16. `P=$(systemctl show -p ExecStart --value comfy-upstream-probe.service | sed -n 's/.*path=\([^ ;]*\).*/\1/p'); env -u HTTPS_PROXY -u SSL_CERT_FILE "$P"; echo "exit $?"` → `exit 2` with `probe: HTTPS_PROXY is unset — invariant 3 …` on stderr — run as the operator outside the namespace, which is also the proof that the direct path is gone.
17. `journalctl --user -u <sfw feed unit> --no-pager | grep -c 'engage: dropped'` → above `0` after the first hour (the drop path is the measured behaviour until Helm's HM8 lands); after HM8: `grep -c '"surface": "feed"' /var/lib/evidence/ledger/engagement.jsonl` → above `0` (a count; no row opened).
18. `FEED_PORT=8388 ROOT=/home/dalhaka/comfyui PROBE_BIN="$P" MUTATE_BIN="$B" bash ~/flakes/media/tests/acceptance/media-worlds.sh; echo "exit $?"` → fourteen `PASS` lines, `exit 0` — the composed drill (70b).
   **Rollback #N:** `sudo /nix/var/nix/profiles/system-<N-1>-link/bin/switch-to-configuration switch` (step 3's generation); `/home/dalhaka/comfyui` is untouched by a generation change; `feed.sqlite` is rebuildable (`comfy-feed-index rebuild --root /home/dalhaka/comfyui --world sfw`).

**The landing act (question 2(a); the orchestrator's, after step 18 and the operator's "test passed"; no key).**
19. `R=$(git -C ~/flakes/media rev-parse HEAD); git fetch ~/flakes/media main && git tag "absorbed/media-$R" FETCH_HEAD && git checkout -b absorb/media main && git merge -s ours --no-commit --allow-unrelated-histories FETCH_HEAD && git read-tree --prefix=media/ -u FETCH_HEAD && nix develop -c treefmt && git add -A media && nix develop -c git commit -m "generation: media absorbed as media/ (landing act, tag absorbed/media-$R)"` → then `git cat-file -p HEAD | grep -c '^parent'` → `2`; `git merge-base --is-ancestor "$R" HEAD && echo reachable` → `reachable` (48a); `git ls-files media | wc -l` → `97`; `nix build .#checks.x86_64-linux.lint -L --no-link` → builds — if it does not (treefmt or statix over `media/`), a `GN13` (`plan-append`, 53a) is typed before GN11 dispatches, never a letter suffix; then `git checkout main && git merge --ff-only absorb/media`, and the board line names the tag.

**After GN12 integrates — switch #N+1.**
20. `nix build .#nixosConfigurations.core.config.system.build.toplevel -o /tmp/gn12-result && nix store diff-closures /run/current-system /tmp/gn12-result` → **prediction**: the ComfyUI closure moves to `nixpkgs-host`'s python and torch (one `comfyui-…` line with two versions, the second `python3` line gone), no unit added or removed, no `caddy`; GN12's measured delta beside it.
21. `readlink /nix/var/nix/profiles/system` → `system-<N>-link`; switch as in step 4 → steps 9 and 15 repeat green (`ok sfw`, `success`).
22. `mv ~/flakes/media ~/factory/archive/media-$R` → the operator's act (nothing in this plan deletes the clone); afterwards `evidence bundle --markdown` shows no `media` sibling head and `docs/ledger/repos.toml`'s `media` row already points here (GN11).
23. The claim (A8), in the board commit after step 8's line: `docs/ledger/claims.toml`, the `aimdo-native-load-unmeasured` row becomes `status = "verified"`, `class = "operator"`, `evidence = "operator:<date> media acceptance drill on core, step 8: the sfw generator's journal names aimdo loaded (plan 2026-09-11-generation.md)"`; `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"` → silent.
   **Rollback #N+1:** `sudo /nix/var/nix/profiles/system-<N>-link/bin/switch-to-configuration switch`; in the tree, in this order, `git revert <GN12 commit>` (the `media` input returns), `git revert <GN11 commit>`, `git revert -m 1 <landing merge>`; the archived clone comes back by `mv`.

## Dispatch

The run names must not exist under `~/factory/runs` (`BUG-run-name-reuse`; Operator step 0). Media waves launch by hand `factory-wave` lines — `factory-dispatch` cannot query a ledger-less sibling (Assumption 14) — from this repo's checkout, against the media clone, with this plan as `FACTORY_PLAN`; the gate is Sonnet (Assumption 35). Commit the regenerated board block before every dispatch (G6, the orchestrator's).

```
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw1 /home/dalhaka/flakes/media "GN1 GN7" --then "gate each, integrate and fast-forward each"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw2 /home/dalhaka/flakes/media "GN2" "GN3" "GN5" --then "gate each, integrate and fast-forward each"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw3 /home/dalhaka/flakes/media "GN4" "GN6" --then "gate each, integrate and fast-forward each"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw4 /home/dalhaka/flakes/media "GN8" --then "gate, integrate and fast-forward"      # after EV15 has landed on this repo's main
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-generation.md tools/factory/seat/factory-wave gnw5 /home/dalhaka/flakes/media "GN9" --then "gate, integrate and fast-forward"
tools/factory/seat/factory-dispatch gnw6 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md --dry-run
tools/factory/seat/factory-dispatch gnw6 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md
tools/factory/seat/factory-dispatch gnw7 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md --dry-run      # after the landing act; prints GN11
tools/factory/seat/factory-dispatch gnw8 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-generation.md --dry-run      # prints GN12
```

The dry run on the scratch copy today (`FACTORY_PYTHON3_CMD=python3 FACTORY_TOOLBOX_REPO=/tmp/draft-scratch/tree tools/factory/seat/factory-dispatch gnw6 /tmp/draft-scratch/tree docs/superpowers/plans/2026-09-11-generation.md --dry-run --repo-name nixos-agent-env`, the copy's `repos.toml` row pointed at the copy):
```
<<DRYRUN>>
```
— the expected answer while GN9 has not landed on media's `main`; once it has, the same line prints `would run: factory-wave gnw6 /home/dalhaka/nixos-agent-env "GN10"`.

**Landing recipe, per key (A1), in order:** (1) keep only the one commit the section names — `git -C ~/factory/ws/<run>/<KEY> log --format='%h %s' <base>..task/<KEY>` shows one line, else `git -C ~/factory/ws/<run>/<KEY> reset --hard <that sha>` (three seats appended a fabricated board commit on 2026-09-05); (2) if the base moved under a file the task touches, the **integrator** merges — `git -C ~/factory/ws/<run>/<KEY> fetch ~/flakes/media main && git -C ~/factory/ws/<run>/<KEY> merge --no-edit FETCH_HEAD` for a media key, `… fetch ~/nixos-agent-env main …` for GN10–GN12 — never the seat (GN-E); (3) `tools/factory/seat/factory-review <run> <repo> <KEY>` and commit the review; (4) `tools/factory/seat/factory-integrate <run> <repo> <KEY>` then `git -C ~/flakes/media pull --ff-only ~/factory/base/media integ/<run>` (media) or `git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>` (this repo), gated on both exit codes; (5) dispatch what it unblocks (A7): GN1 → GN2, GN3, GN5; GN7 with GN1 → nothing more; GN2 + GN3 → GN4; GN2 + GN5 → GN6; GN4 (+ EV15) → GN8; GN4, GN6, GN7, GN8 → GN9; GN9 → GN10 (then switch #N); GN10 (+ EV10, the landing act) → GN11; GN11 → GN12 (then switch #N+1). **Relaunch after a rejection** (A6): `FACTORY_PLAN=<this plan> tools/factory/seat/factory-task <run>b <repo> <KEY>b --prior <run>/<KEY>` — a media fix round carries `**repo:** media` in its own section, appended at re-plan; the dead seat's diff stays in `~/factory/ws/<run>/<KEY>`.

## Anticipation

- **The tree this draft could not read.** Every media section's Step 0 re-measures its quoted facts (GN-A); a drifted fact stops the task `failed` with `fact drift`, and the orchestrator re-plans that key rather than letting the seat improvise. Prepared: the Facts list per section is the exact command set.
- **The probe moves to system scope** (GN7): a system timer starts at switch #N (Operator step 4), where the old user timer did not; the probe's output directory must be writable from the unit (Interfaces 3's `ReadWritePaths`), and the VM check needs the `media` instance stub — GN7's Step 0 measures both.
- **The packaging fix lands first** (GN1) and its executable proof is GN3's `comfy-feed --help`; until GN3, M8 is killed by a probe only — said in GN1.
- **`comfy-worlds-unit` cannot see a test directory outside its copy block** (Assumption 21): GN1's copy-the-directory rule covers GN2–GN8's files; a task that still needs a `flake.nix` edit discloses it with a `Deviation:` line.
- **GN1's fixture PNG is not a ComfyUI render.** The chunk keyword `prompt` and the API-graph shape (Assumption 22) are what ComfyUI writes; the drill's step 12 (a real render regenerated) is the live proof, and a mismatch there is a `fact drift` against Assumption 22, not a seat's fault.
- **Two writers of `feed.sqlite`** (the feed's worker and `comfy-mutate-<w>.service`): WAL and a 5 s timeout (GN1), 503 `busy` on the page (GN3); the drill's step 14 is that path.
- **HM8's endpoint does not exist yet** — GN8 drops and keeps counts; Operator step 17 measures the drop line before HM8 and the row after; a changed URL or verb in HM8 as landed is a one-line option default (Assumption 33).
- **EV15 lands before GN8** by the published order; if Evidence stalls, GN8 stays `blocked` and waves 1–3 run regardless (GN9 waits).
- **GN10's lock may drift** if media's `main` moves between GN9's landing and GN10's launch — the seat's `nix flake lock` pins whatever `main` is then; the runbook's `media nixpkgs:` line and the check record it.
- **The `media` broker instance's `allow` is the probe's six hosts only** (Assumption 24): `media-fetch-models` on core would need its own widening — a later task, named in Not in this plan, never a silent edit to GN10's list (the check pins it by equality).
- **Switch #N's closure is large** (the ComfyUI/torch closure): Operator step 2's prediction names it so the diff-closures output is read, not feared; a `caddy` line there is a finding.
- **The landing act may not be lint-clean** (treefmt/statix over 97 files): a `GN13` `plan-append` before GN11 (Operator step 19), never a suffix.
- **`nixpkgs-host` may refuse the ComfyUI closure** (Assumption 25): GN12's Step 1 measures before any move and stops `failed` with the error; question 2(b) is the prepared fallback.
- **Name collisions on absorption**: `lint` → `media-lint` by rule, the `assert` refuses any other (GN12 M3).
- **Dispatch of a ledger-less sibling** (Assumption 36 i): the hand lines above; `factory-dispatch` for GN10–GN12 only.
- **Questions pre-asked:** the three above, each with a default; Assumptions 29–35 carry every other call with a veto surface. **Claims to close:** `aimdo-native-load-unmeasured` (Operator 23). **Switch deltas:** two, predicted (Operator 2, 20) and measured in GN10's and GN12's commit bodies. **Hooks, deny rules:** none added (A13, A14 do not fire). **Handoff line for the board (A11):** "generation: on the seat: <wave> (<keys>); in gate: <keys>; next: <the unblocked wave or the switch>; media main: `git -C ~/flakes/media log --oneline -1`".

## Not in this plan

- Helm's swipe view, the feed link or embed, and the `media-refresh` tile (WH2) — Helm (`HM`; 14c, 15a).
- The engagement kind and its validator (EV14, EV15), the `proposals` stream and `pkgs/evidence/SCHEMA.md` — Evidence (`EV`).
- The task-graph parser, the prefix guard, `--draft`, and `factory-dispatch` for ledger-less siblings — Evidence and Factory (Assumption 36).
- `factory-review`'s trailer comparison (the W6 false-MAJOR class) — Factory, closed by FIX7.
- The local inference stack and Phase 5 local weights — "no work scheduled until the mutator's model phase" (17c, charter).
- Network-namespace confinement of a world (design: out of scope); the driver-580 / CUDA 13 path stays the probe's to propose and the operator's to switch.
- The generation lab (`docs/concepts/2026-09-06a-generation-lab.md`, "brainstorm owed before a spec").
- The LAN face — Caddy, `tls internal`, `basic_auth`, the password files, the host names (question 3; Isolation's increment 4).
- Widening the `media` instance for `media-fetch-models` or `services.comfyui`'s `huggingface.co` injection (Assumption 24) — a later Generation task with its own `allow` and `inject` and an A3 item for the token.
- WH1 and WH2 as typed in media's plan — superseded (Assumption 30), left as history.
- The superseded `2026-09-02-media-flake.md` plan and media's own `docs/OPERATIONS.md` — frozen with the clone's history at absorption.
- The `seat-vm` eval red at HEAD (the board's HELD line) — Isolation/Seat; every check here is built by name.
- The Fable price row and `dsh-openrouter.sh` (FA11) the spec's cost note mentions — Factory.
