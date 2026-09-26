---
plan_defect: none
mutants_total: 0
mutants_killed: 0
mutants_outside_named: 0
model: opus
---
# Opus gate — seat run bug1ac, task BUG1ac — APPROVED

## Summary

**Every item of the BUG1ab rejection is closed, and — for the first time in this chain —
every line number in the document reproduces exactly.** I re-ran all 47 pasted commands in a
fresh clone of `task/BUG1ac` at `af2d235`, plus the live host reads (`systemctl`, `journalctl`,
`find`/`ls`/`stat` on `/var/lib/egress-broker`) and the `time nix run` measurement. Not one
citation is off by a line; not one paste is fabricated. The two prior rounds were rejected for
hand-counted line numbers, and this round has none.

MAJOR-1 is closed by measurement and an honest label: the enclosing block of
`package-lock.json:1109` is `@deepseek-ai/dsh-base` (`:1054`), the headless profile bundles
`dsh-base`, the round-2 mechanism is explicitly withdrawn, and the Assumption-3 conclusion now
carries `UNMEASURED:` with `seatLane.nix:231` `PrivateTmp = true` (grep pasted) and "no headless
job has run through the unit" as the two facts that moot it after switch #24. I went further
than the section required and read the on-disk profile trees
(`~/.local/share/dsh-openrouter/profiles/{headless,web}/cordis.yml` are both the empty `[]`
root; the tree is composed at runtime from `package.json`'s bundles) — **the question genuinely
cannot be settled from files, so `UNMEASURED:` is the correct label, not an evasion.**

MAJOR-2 is closed in full: `grep -rn 'command -v seat-submit' tools/` and
`sed -n '109,117p' tools/factory/seat/seat-drive.sh` are pasted and byte-identical to mine;
three routes are named with file, line, switch-requirement and blast radius; `seat-drive.sh:113`
is recorded as the second consumer route 1 would affect, with the provenance answer the section
asked for; route 3's `nix run` cost is measured (`real 0m1.046s`; my re-run `real 0m1.000s`) and
its working-tree skew stated; and the unit's hardening is pasted and read line by line for
`nix build`, `git`, the workspace and `~/.cache`, with `UNMEASURED:` where the file cannot show
it. All five MINORs are closed.

`lint` is green, the hook is green to `render.test.mjs: all assertions passed`, repomap is
clean, `tasks check` is silent, the diff is exactly the one file in `touches`, and the subject
is byte-identical to the section's.

Five MINORs remain, all cosmetic or residual; none of them changes a fact the fix stage turns
on. **Approved.**

## Contract items

The section's numbered "what to change" list, taken literally.

| # | Requirement | Met | Evidence |
|---|---|---|---|
| 1 | MAJOR-1: run the two greps; rewrite the paragraph to say what they show; then EITHER measure a headless plugin load OR label the conclusion `UNMEASURED:` with `seatLane.nix:231` (grep pasted) and "no headless job has run" | **yes** | Doc `:206-233` pastes `grep -n 'dsh-spill-local'`, the `awk` enclosing-block command and `sed -n '1054,1059p'`; all three reproduce **byte-identically** (below). `:228-233` withdraws the round-2 mechanism in its own words. `:239` `**UNMEASURED:**`; `:252-256` pastes `grep -n 'PrivateTmp'` → `231:          PrivateTmp = true;` (identical); `:262-265` states fact 2. Residual: the subsection **heading** still asserts the withdrawn conclusion — MINOR-1 |
| 2 | MAJOR-2: paste `grep -rn 'command -v seat-submit' tools/` and `sed -n '109,117p' seat-drive.sh`; three routes each with file, line, switch, blast radius, what item 2 breaks; route 1 via `modelLane.nix:194-198` (grep pasted) with `seat-drive.sh:113` in its blast radius and the behaviour-vs-provenance answer; route 2 the seam as kill-switch with the proof kept; route 3 `seat-drive.sh:109-117` copied into `factory-task`, no switch, `time nix run … -- --help` measured and the working-tree skew stated; the unit's hardening pasted via `sed -n '205,275p'` with a per-line reading for `nix build`/`git`/workspace/`~/.cache` and `UNMEASURED:` where unshowable | **yes** | Doc `:615-620` (the `grep -rn`, three hits, "two *executable* consumers … the third grep hit is README prose") and `:631-641` (the `sed`) both reproduce byte-identically. Route 1 `:643-676` with `grep -n 'systemPackages' nixosModules/modelLane.nix` → `194:` and `sed -n '194,198p'` pasted (identical), `grep` on `seatLane.nix` → no lines (I reproduce exit 1), "**Needs a switch**", `seat-drive.sh:113` named, "a change in *provenance*, not in behaviour … one system closure". Route 2 `:678-688`. Route 3 `:690-715` with the `time` block (mine: `real 0m1.000s`) and the `$FACTORY_TOOLBOX_REPO` working-tree statement (`factory-lib.sh:27` verified). Hardening `:717-826`: the paste, then `:211`, `:231-232`, `:240-246`, `:268-272`, `:273` each read against `nix build`/`git`/workspace/`~/.cache`, three `UNMEASURED:` labels. Residual: the paste is 69 of the command's 71 lines — MINOR-3 |
| 3 | MINOR-1: the hook's last line in BOTH the commit body and the document | **yes** | Doc `:18-19`: "`nix develop -c githooks/pre-commit` exits 0; its last line is `render.test.mjs: all assertions passed`". Commit body: "runs green to its last line `render.test.mjs: all assertions passed`". I ran it: exit 0, that exact last line |
| 3 | MINOR-2: `:418` → `:404` with `grep -n -- '--timeout'` pasted | **yes** | Doc `:392` "`--timeout "$timeout_s"` **to `seat-submit`** (`:404`, pasted below, of the call at `:397-405`)"; the grep at `:406-409` → `404:        --timeout "$timeout_s" \`. Mine is identical, and `sed -n '395,415p'` confirms the call spans exactly `:397-405` |
| 3 | MINOR-3: item 2 gains the stderr divergence, each line from a pasted grep | **yes** | Doc `:411-451`: `factory-task:438` (grep pasted, two hits `372`/`438`), `:405` (`grep -n -F '2>"$submit_err"'` → `405`), `:412` (grep → `412`), `seat-submit.py:148-151` (`sed` pasted), `seat-run.py:144` (grep pasted). Every one reproduces byte-identically |
| 3 | MINOR-4: mark the `ls -la` paste as the sandbox's userns view and state the host's owners | **yes** | Doc `:78-96`: the `nobody nogroup` paste is labelled "the **sandbox's user-namespace view**" and the host owners (`egress-broker`, `root`) are pasted beside it, attributed to the gate. My host run: `drwxr-xr-x 3 egress-broker egress-broker` / `drwxr-xr-x 5 root root` — exactly those |
| 3 | MINOR-5: rewrite the opening promise to say which citations are grep-backed; `brief.md:58-59` → `:59-60` | **yes** | Doc `:5-11` now scopes the promise to "Every `file:line` citation **that the fix stage turns on**" and names the classes carried without a paste. Doc `:884` "brief.md:59-60 … `:58` is blank and the 'Harnesses in scope' sentence spans `:59`–`:60`" — verified: `:58` blank, `:59-60` the sentence |

**Interfaces** ("the same document, same four sections plus `## The fix, as options`; no new
file"): `## Observed` `:23`, `## Mechanism` `:267`, `## Where the defect is` `:598`,
`## The fix, as options` `:612`, plus `## What is broken now` `:862`, `## What a fix must not
break` `:900`, `## Unmeasured` `:922`. **Shape met.** The diff creates the file because BUG1ab
never landed; the path is the one the contract names.

**BUG1's five establishments**, all present and re-verified in this recreated document:
item 1 → `## The fix, as options`; item 2 → M3; item 3 → M7; item 4 → M6; item 5 → M4.

**Global Constraints:** one document, no module, package, test or check touched; no behaviour
changed; the fix is described, not applied; no switch, no `systemctl start/stop`, no seat
launch. **Met.**

### The BUG1ab rejection, item by item

| Item | Closed | Where |
|---|---|---|
| MAJOR-1 — the spill-local attribution, inverted by its own evidence | **yes** | `:204-265`. The enclosing block is named (`dsh-base`, `:1054`, closes `:1165`), `dsh-web-app:3958` is named as not listing it, the round-2 mechanism is quoted and withdrawn, and the conclusion is `UNMEASURED:` with both mooting facts |
| MAJOR-2 — incomplete options, false blast radius | **yes** | `:612-826`. Three routes; `seat-drive.sh:113` named as the second consumer; the categorical "package/config change" gone (route 1 is now "a module + config change"); the unit's netns and hardening named and read line by line |
| MINOR-1 — no green pasted | **yes** | Document `:18-19` and the commit body |
| MINOR-2 — `:418` | **yes** | `:392`, `:406-409` |
| MINOR-3 — the stderr divergence | **yes** | `:411-451` and again in the fix section at `:846-851` |
| MINOR-4 — the sandbox ownership paste | **yes** | `:78-96` |
| MINOR-5 — the opening promise, `brief.md:58-59` | **yes** | `:5-11`, `:884` |

The review's round-2 phrases are gone from the document except where it quotes them to withdraw
them (`grep -n -e 'exactly two ways' -e 'nothing else consumes'` → one hit, `:617`, inside "round
2's … was false").

## Red before green

The section names no test: *"**Tests …** none — a gather stage adds no behaviour."* Matrix items
2 and 3 are `none` by contract; the diff contains no executable artifact, so there is no
assertion that could be made to fail. **Red-before-green is not applicable and its absence is
not a finding.** The section states the substitute: *"Judged at the gate by re-running every
command this round adds and by whether each of the seven review items is closed as stated."*
That is what I ran — every command, in a fresh clone at `af2d235`, plus the live host reads.

| Citation / paste | Command I ran | Result |
|---|---|---|
| `factory-task:378` | `grep -n 'command -v seat-submit' tools/factory/seat/factory-task` | **byte-identical** |
| host PATH | `command -v seat-submit; echo exit=$?` | **`exit=1`** — reproduces |
| `factory-task:430`, `:437` | `grep -n 'launching dsh-openrouter'`, `grep -nF 'timeout -- "$timeout_s" dsh-openrouter'` | **byte-identical** |
| no `--broker` | `grep -n -e '--broker' tools/factory/seat/factory-task` | **no lines, exit 1** |
| tee sites `:372`/`:406`/`:438` | `grep -nF '\| tee -a -- "$log"'` | **byte-identical** |
| extraction `:481`/`:489`/`:490` | `grep -nE 'result_line=\$\(\|extract_field\(\)'`, `grep -n "grep -E '^FACTORY-RESULT"` | **correct** (`sed -n '486,495p'` confirms) |
| `:404` `--timeout` | `grep -n -- '--timeout' tools/factory/seat/factory-task` | **byte-identical** |
| `:405`, `:412` | `grep -n -F '2>"$submit_err"'`, `grep -n -F 'tee -a -- "$log" <"$submit_err"'` | **byte-identical** |
| `:960` | `grep -nF 'seat: unit seat@'` | **byte-identical** |
| arm boundaries `:361`/`:378`/`:397-405`/`:407`/`:429`/`:439` | `sed -n '355,380p'`, `'395,415p'`, `'425,442p'` | **every one correct** |
| `package-lock.json` `:1109`, `:3162`, `:3164` | `grep -n 'dsh-spill-local' pkgs/dsh/package-lock.json` | **byte-identical** |
| the enclosing block | `grep -n '^    "' … \| awk -F: '$1<1109' \| tail -3` | **byte-identical** (`1054: … dsh-base`) |
| `:1054-1059`, `:1165`, `:3958` | `sed -n '1054,1059p'`, `sed -n '1163,1167p'`, `grep -n '"node_modules/@deepseek-ai/dsh-web-app"'` | **all correct** — base closes `:1165`, web-app opens `:3958` |
| `seatLane.nix:231` | `grep -n 'PrivateTmp' nixosModules/seatLane.nix` | **byte-identical** |
| `seatLane.nix:22`, `:206`, `:202` | `grep -n -e 'seatSubmit'`, `grep -n -e 'path = \['` | **byte-identical**; `sed -n '202,207p'` confirms the list contents M2 describes |
| no `systemPackages` in `seatLane.nix` | `grep -n 'systemPackages' nixosModules/seatLane.nix` | **no lines, exit 1** |
| `modelLane.nix:194-198` | `grep -n 'systemPackages'`, `sed -n '194,198p'` | **byte-identical** |
| `seatLane.nix:90`, `:173`, `:106`, `:105`, `:112`, `:121` | `grep -n -e 'injected-by-broker' -e 'valueFile' -e 'allow = \[' -e 'bodyPatch' -e 'denyPaths'` | **all byte-identical**; `cfg.host` default `:33` = `"openrouter.ai"`, so "names openrouter.ai only" is right |
| `seatLane.nix:94-100`, `:112-118`, `:121-123` | `sed -n '94,100p'`, `sed -n '112,123p'` | **all three ranges exact** |
| the hardening paste | `sed -n '205,275p' nixosModules/seatLane.nix` | content identical; **2 trailing lines dropped** — MINOR-3 |
| `:211`, `:232`, `:240-246`, `:268-272`, `:273` | `grep -n -e 'NetworkNamespacePath' -e 'ProtectSystem' -e 'ReadWritePaths' -e 'InaccessiblePaths' -e 'NoNewPrivileges'`, `sed -n '240,246p'`, `'268,273p'` | **every line number exact** |
| `seat-drive.sh:109-117` | `sed -n '109,117p' tools/factory/seat/seat-drive.sh` | **byte-identical** |
| the three consumers | `grep -rn 'command -v seat-submit' tools/` | **same three hits** (`seat-drive.sh:113`, `README.md:708`, `factory-task:378`) |
| `dsh-openrouter.sh:319`, `:321`, `:325`, `:343` | four `grep -nF`s | **all byte-identical**; `sed -n '318,322p'`/`'342,345p'` confirm `:320` export and `:344` `key_source` |
| `dsh-openrouter.sh:48` | `sed -n '44,50p'` | **correct** — `--denials` at `:48` |
| `seat-submit.py` `:15`/`:27`/`:32`/`:98`/`:148`, `:154`, `:145`, `:125`, `:148-151` | `grep -nF 'stdout.txt'`, `'exit_code.txt'`, `'return 124'`, `'return 3'`, `sed -n '148,151p'` | **all byte-identical**; `sed -n '115,160p'` confirms the 124-after-`systemctl stop` and the `int(raw)`/ValueError fallback the doc describes |
| `seat-run.py:137`, `:144`, `:149`, `:92`/`:108`/`:121` | `grep -nF 'capture_output=True'`, `grep -n -F 'stderr.txt'`, `sed -n '144,152p'`, `grep -n -e '"--broker"'` | **all correct** — `result.txt` is written at `:149`, after `subprocess.run` returns |
| `policy.py:380-404`, `:110`, `:159`, `:174`, `:203`, `:513-518`, `:521`, `:522`, `:32` | `grep -n` × 5 plus `sed -n '380,406p'`, `'513,523p'`, `'108,112p'`, `'159,172p'` | **all correct** — `_inject` ends `:404` (`http_connect` at `:406`), `response()` at `:520` calls `_audit` `:521` then `_record_usage` `:522` |
| `egressBroker.nix:30` | `grep -n -e 'usage_log' nixosModules/egressBroker.nix` | **byte-identical** |
| `brief.md:70`, `:72`, `:59-60` | `grep -n`, `awk` over `57..74` | **all correct**; `:58` is blank, the invariant-2 sentence spans `:70-71` |
| O2 — broker dirs | `find … -name 'usage*.jsonl'`, `find … -maxdepth 2 \| sort`, `stat -c` | **reproduces byte-for-byte**, both timestamps included |
| O2 — `ls -la /var/lib/egress-broker/seat/` | same command on the host | **content reproduces**; the ownership skew is now correctly labelled |
| O3 — the unit | `systemctl list-units --no-pager 'seat@*'` | **reproduces**: `seat@20260909-093539-dc8d7a.service loaded active running` |
| O3 — the journal | `journalctl -u 'seat@*' --no-pager -n 60 \| tail -14` | **reproduces**; the doc's elision is marked `...` |
| O3 — the CDT/UTC note | `date` → `Wed Sep 9 05:37:09 AM CDT 2026`, job id `…-093539` vs journal `04:35:39` | **the doc's note is right**: the journal renders CDT, the job id stamps UTC |
| O4 — the key file | `stat -c '%n %a owner=%U size=%s' ~/.config/openrouter/key` | the gate can read it: `600 owner=dalhaka size=73` — **exactly the carried value**; the doc's "the house guard refused this pass" is recorded honestly |
| O5 — the two profiles | `cat …/profiles/{headless,web}/package.json` | **reproduces byte-for-byte** |
| route 3's cost | `time nix run /home/dalhaka/nixos-agent-env#seat-submit -- --help` | **reproduces**: usage text, `real 0m1.000s` (doc: `0m1.046s`) |
| `factory-lib.sh:27` | `grep -n 'FACTORY_TOOLBOX_REPO' tools/factory/seat/factory-lib.sh` | **correct** — `27:FACTORY_TOOLBOX_REPO=${FACTORY_TOOLBOX_REPO:-/home/dalhaka/nixos-agent-env}` |

**Beyond the section**, to test the `UNMEASURED:` label rather than accept it: the on-disk
profile trees are `[]` —

    $ cat ~/.local/share/dsh-openrouter/profiles/headless/cordis.yml
    # dsh profile root — an empty entry list. The tree is composed as patches:
    # each bundle in package.json's dsh.profile.bundles, then cordis.patch.yml, then any
    # --patch overlays. Edit cordis.patch.yml, not this file.
    []

— so no file on disk names the loader entries, and `--dump-config` is pinned to the **web**
profile (`pkgs/dsh-openrouter/dsh-openrouter.sh:760`,
`exec "$node_bin" "$bin_js" --profile web --patch "$overlay" --dump-config`). The document's
`UNMEASURED:` is therefore the **correct** label and not an evasion, though its stated reason is
imprecise — MINOR-4.

## Mutants

**mutants_total 0, mutants_killed 0, mutants_outside_named 0.** Matrix items 2 and 3 are `none`
by contract: the section names no assertion and no mutant, and the diff (one Markdown file)
contains no executable artifact to mutate. Mutation testing is vacuous here and its absence is
not a finding.

## Checks

Acceptance is `lint`. All run in the fresh clone of `task/BUG1ac` at `af2d235`, with
`XDG_CACHE_HOME` under the session scratch.

| Check | Command | Result |
|---|---|---|
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass**, exit 0. (The build log carries `Found 0 warnings and 1 error` twice — those are the deliberate negative fixtures `tests/lint/fixtures/js/bad.mjs` and `workflow-bad.js`; the derivation succeeds) |
| lint gate | `nix develop -c githooks/pre-commit` | **pass**, exit 0, last line `render.test.mjs: all assertions passed`. As in both prior rounds the first run exits 1 with `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the regeneration is exactly one line — `BUG1ac` leaving the derived queue and `FIX1` entering it. That is the orchestrator's landing-time board update, which the section forbids the seat to commit. **Not a red check and not a finding against the seat.** With that one line staged, the hook is green |
| repomap | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | **clean**, exit 0 — `docs/bugs/` is not mapped |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | **silent**, exit 0 |
| ruff | n/a | no Python in the diff |

No red check.

**On the seat's queue-block note.** The commit body says the regeneration was skipped because
the workspace's directory basename (`BUG1ac`) broke `tasks.py`'s repo-key lookup, letting the
withdrawn `BUG1b` leak into the queue. In this clone (basename `gate-bug1ac-BUG1ac`) the
regenerated block contains **`BUG2 FIX1 HH1 HH2 HH3 HH4 PW1glm PW1kimi PW1pro SP4`** — `BUG1b`
does **not** leak, and `tasks check` is silent. So the tooling behaviour the seat describes does
not reproduce here; per the orchestrator this is a tooling matter and not a finding against the
seat, and the seat was right not to commit the board either way. The workspace
`/home/dalhaka/factory/ws/bug1ac/BUG1ac` is otherwise clean: `git status --porcelain` shows one
untracked scratch file, `.commit-msg-BUG1ac.txt` (the commit message the seat passed to
`git commit -F`), and nothing else — no stray edit, no modified tracked file.

## Touches and commit

`touches: docs/bugs/2026-09-09-broker-bypass.md`. The diff is exactly that file:

    docs/bugs/2026-09-09-broker-bypass.md | 932 ++++++++++++++++++++++++++++++++++
    1 file changed, 932 insertions(+)

Nothing outside `touches`; `docs/MAP.md` correctly unchanged (repomap clean); the plan file
untouched; no board commit. Exactly one commit
(`git rev-list --count 237b3c0..HEAD` → `1`), `af2d235`. The subject is **byte-identical** to
the section's (`cmp` against the section's text: identical, including the em dash and the
apostrophe in "unit's"). Both trailers present after a blank line:

    Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run bug1ac)
    Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>

The body walks MAJOR-1, MAJOR-2 and MINOR-1…5 in order and says how each is closed, states the
why, and pastes the green (`render.test.mjs: all assertions passed`) — exactly what Step 4 asks.
Its account is accurate against what I measured; the one over-claim of round 2 ("settled by
measurement rather than reasoning") is gone.

## Findings

### MINOR-1 — the O5 heading still asserts the conclusion the section labels `UNMEASURED:`

`docs/bugs/2026-09-09-broker-bypass.md:164`:

    ### O5 — the headless profile does not load the spill-local plugin

That heading is carried verbatim from round 2
(`/home/dalhaka/factory/ws/bug1ab/BUG1ab/docs/bugs/2026-09-09-broker-bypass.md:144` — the same
string), while the body under it, `:239-241`, now says the opposite:

    **`UNMEASURED:`** whether a `--headless` run actually loads the
    `spill-local` loader entry.

It sits in `## Observed`, the section reserved for measured fact, and the plan's Global
Constraint is *"A claim without a command is a guess and must be labelled one."* A reader who
scans headings — and FIX1 is typed from this document — takes away the exact certainty the
BUG1ab gate refuted.

It is a MINOR and not a MAJOR because the section's two operative duties are both discharged, at
length, in that same subsection: the paragraph is rewritten to say what the commands show
(`:228-233`, withdrawing the round-2 mechanism in its own words) and the conclusion is labelled
`UNMEASURED:` with both mooting facts. No claim anywhere else in the document rests on the
heading — M7's "(b) the headless profile does not load the web app (O5)" is a different claim,
and it is supported by the pasted `package.json`. The repair is one line: *"O5 — the spill-local
attribution, corrected; whether a headless run loads it is unmeasured."*

### MINOR-2 — "the post-#24 journal **above** shows" a string the paste does not contain

`docs/bugs/2026-09-09-broker-bypass.md:166`:

    The post-#24 journal above shows the EROFS came from `profiles/web/#spill-local`.

Two things. The pasted journal (doc `:132-142`, `journalctl … -n 60 | tail -12`) does **not**
contain `profiles/web/#spill-local`; its EROFS line ends at `mkdtemp '/tmp/dsh-spill-XXXXXX'`.
And the trace is **pre**-#24 (`Sep 08 21:27:17`), which the document's own O3 says.

The claim itself is **true** — I found the string outside the pasted window:

    $ journalctl -u 'seat@*' --no-pager --since '2026-09-08' | grep -n 'profiles/'
    20:Sep 08 21:27:17 core seat-run[1576466]:     at file:///home/dalhaka/factory/drive/20260909-022712.dsh-home/profiles/web/#spill-local
    21:Sep 08 21:27:17 core seat-run[1576466]:     at file:///home/dalhaka/factory/drive/20260909-022712.dsh-home/profiles/web/#include

so nothing downstream is wrong. Recorded because the sentence attributes to a pasted output a
string that output does not carry — the same class the round exists to eliminate, at a place
where the fact happens to hold. The repair is to paste the two `at file://…` lines, which are
better evidence than the ones shown.

### MINOR-3 — the hardening paste is 69 of the command's 71 lines, unmarked

`docs/bugs/2026-09-09-broker-bypass.md:717` announces `$ sed -n '205,275p'
nixosModules/seatLane.nix` and the fence ends at `:786` with `NoNewPrivileges = true;`. The real
command emits two more lines:

    $ diff <(sed -n '205,275p' nixosModules/seatLane.nix) <doc paste>
    @@ -67,5 +67,3 @@
                 "-/run/dbus/system_bus_socket"
               ];
               NoNewPrivileges = true;
    -          # AF_NETLINK: the wrapper's `--broker` route check (`ip route`) must
    -          # be able to inspect the namespace's default route on every launch

Both dropped lines are comment; every directive the section named (`:211`, `:231-232`,
`:240-246`, `:268-272`, `:273`) is present and correct, and the elision is not marked `...` as
the journal paste's is. No conclusion changes. Worth one note for the fix stage: the comment
runs on to `RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX AF_NETLINK"` at
`nixosModules/seatLane.nix:277` — one line past the range the section asked for, and a sixth
constraint on what a headless task may do (`AF_UNIX` admits the nix daemon socket; nothing else
is admitted).

### MINOR-4 — "exposes no plugin/profile-listing flag" is refuted by the usage text the sentence cites

`docs/bugs/2026-09-09-broker-bypass.md:243-247`:

    The only way to measure it is a
    `dsh-openrouter --headless` boot in a scratch `DSH_HOME`, and `dsh-openrouter.sh`
    exposes no plugin/profile-listing flag — the wrapper's own usage (`--help`) offers
    `--model`, `--permission`, `--denials` and `-- web-app flags` …

The enumeration omits two flags, one of which is a profile dump, and it is in the very usage
block the sentence points at (`dsh-openrouter.sh:47`, inside the doc's own cited `:44-50`):

    $ sed -n '47p' pkgs/dsh-openrouter/dsh-openrouter.sh
    and exits. --dump-config prints the composed profile (no secrets) and exits.

**The conclusion survives, and I verified why the document does not say:**

    $ grep -n 'dump-config' pkgs/dsh-openrouter/dsh-openrouter.sh
    136:    --dump-config)
    760:    exec "$node_bin" "$bin_js" --profile web --patch "$overlay" --dump-config

`--dump-config` is pinned to `--profile web`, so it cannot answer the **headless** question —
and the on-disk `cordis.yml` for both profiles is the empty `[]` root, the tree being composed
at runtime from `package.json`'s bundles. So `UNMEASURED:` is right. The finding is that the
document asserts a flag does not exist when it does, and omits the fact (`:760`) that actually
rescues the claim. One sentence closes it.

### MINOR-5 — `ProtectSystem`'s reading has a self-correcting first clause

`docs/bugs/2026-09-09-broker-bypass.md:801-806`:

    nothing in `$HOME`
    or the workspace is affected by `ProtectSystem` *directly*, but a task that
    writes anywhere outside the `ReadWritePaths` below gets EROFS.

`ProtectSystem = "strict"` mounts the whole hierarchy read-only bar `/dev`, `/proc`, `/sys` and
`ReadWritePaths`, so `$HOME` **is** affected by it directly — that is precisely why `:240-246`
must list `~/factory` and the rest. The second clause states the correct rule and the per-line
readings that follow are right (the workspace under `~/factory/ws` writable, `~/.cache` not),
so nothing the fix stage needs is wrong; the first clause is loose wording in a document that is
otherwise careful.

## Verdict

**APPROVED.** Both MAJORs of the BUG1ab rejection are closed by measurement, all five MINORs are
closed, and — the thing the two prior rounds failed at — every single line number in the 932-line
document reproduces exactly against the tree at `af2d235`. `lint` and the hook are green, the
diff is one file inside `touches`, the subject is byte-identical, both trailers are present, and
no board commit was made.

The five MINORs are all one-sentence repairs and none of them changes a fact FIX1 turns on;
FIX1's own Facts 1–7 are each independently verified above and can be typed from this document
as it stands. The orchestrator may want MINOR-1's heading corrected at landing so the file does
not carry a headline the file itself refutes, and MINOR-3's note about
`seatLane.nix:277` `RestrictAddressFamilies` added to FIX1's Fact 7 — the sixth hardening line,
one past the range this section asked the seat to read.

`plan_defect: none` — the section named its seven items precisely, in commands the gate could
re-run, and the seat executed each one.
