---
reviewer: opus
majors: 1
minors: 7
---
# Opus gate — seat run og1, task OG1b — REJECTED

## Summary

One commit (`8bea7c6`) on base `d664bf3`, subject md5 byte-identical to the
plan's (`7b1b679d…`), `Generated-By` + `Co-Authored-By` trailers present, touches
a strict subset of OG1b's declared list, `docs/MAP.md` regeneration disclosed in
FACTORY-NOTES and proved forced. `.claude/settings.json` keeps G6's SessionStart
entry byte-for-byte; `flake.nix` is the one sanctioned `cp` line. Five of the six
findings are genuinely fixed and each is killed by a mutation: path
normalisation (MAJOR 1), sudo command-position anchors (MINOR 3),
protected-prefix coverage (MINOR 4), the malformed-`{` warning (MINOR 5), and the
escape-aware MultiEdit extraction (MINOR 6) — I re-tested MINOR 6 with a fixture
whose file actually carries the quote and it denies in all four orderings.
30/30 bats green, `unit` (tests 158–187), `lint` and shellcheck pass, 10–39 ms
per call against a 33 KB real plan file.

It is rejected on **MAJOR 2, which is not fixed — only widened**. The implementer
kept the enumerate-the-flags shape the OG1 review called out and under-enumerated
it. `git --work-tree=. commit --amend` is ALLOWED, and `--work-tree=…` is named
verbatim in the plan's own OG1b pattern spec. So are `git -P commit --amend`
(`-P` is git's short form of `--no-pager`; the guard lists `-p|--paginate` and not
`-P`), `git --literal-pathspecs …`, `git --exec-path=… …`,
`git --no-replace-objects …`, `git --icase-pathspecs rebase -i`,
`git --namespace=n push`. I ran each against a throwaway repo: they are working
amends — the head moves. The gate brief's rule is explicit: a surviving `--amend`
bypass is a MAJOR.

## Fixes verified

Payloads fed on stdin exactly as Claude Code sends them (compact JSON,
`ensure_ascii=False`), guard run as `env CLAUDE_PROJECT_DIR=<fake project> bash
tools/orchestrator-guard.sh`. Fixture: `docs/superpowers/plans/x.md` with two
typed headings (`A1`, `B2`), a `docs/notes/plans/x.md` decoy, a symlink
`linkdir/into-plans.md` → the plan, and a symlink `plans/link.md` → outside.

| Finding | Probe | Expected | Observed |
|---|---|---|---|
| MAJOR 1 | `Edit` via `…/plans/../plans/x.md`, heading removed | deny | **DENY** |
| MAJOR 1 | `Edit` via `…/superpowers/./plans/x.md` | deny | **DENY** |
| MAJOR 1 | `Write` through a symlink **into** the plans dir | deny | **DENY** |
| MAJOR 1 | absolute path into the plans dir | deny | **DENY** |
| MAJOR 1 | `…/plans//x.md` (doubled slash) | deny | **DENY** |
| MAJOR 1 | relative `docs/superpowers/plans/x.md` | deny | **DENY** |
| MAJOR 1 | `…/docs/../docs/superpowers/plans/x.md` | deny | **DENY** |
| MAJOR 1 | `docs/notes/plans/x.md`, heading removed | allow | allow |
| MAJOR 1 | symlink **from** the plans dir to a file outside | deny (brief) | **allow** — see MINOR 8 |
| MAJOR 2 | `git -c core.editor=true commit --amend` | deny | **DENY** |
| MAJOR 2 | `git -C /home/x push` | deny | **DENY** |
| MAJOR 2 | `git --no-pager rebase -i` | deny | **DENY** |
| MAJOR 2 | `git -c a=b -C . reset --hard` | deny | **DENY** |
| MAJOR 2 | `git --git-dir=.git commit --amend` | deny | **DENY** |
| MAJOR 2 | `git -c a=b status`, `git -C . log -1` | allow | allow |
| MINOR 3 | `grep -rn sudo docs/brief.md` | allow | allow |
| MINOR 3 | `echo 'never sudo here'` | allow | allow |
| MINOR 3 | `cat docs/decisions/x.md \| grep sudo` | allow | allow |
| MINOR 3 | `rg nixos-rebuild docs/` | allow | allow |
| MINOR 3 | `sudo x`, `x; sudo y`, `x && sudo y`, `(sudo y)`, `x \|\| sudo y`, `\nsudo y` | deny | **DENY** ×6 |
| MINOR 4 | `tee -a /var/lib/secrets/x` | deny | **DENY** |
| MINOR 4 | `cp k /run/baskets/x` | deny | **DENY** |
| MINOR 4 | `mv k /var/lib/lanes/x` | deny | **DENY** |
| MINOR 4 | `install -m600 k /var/lib/secrets/x` | deny | **DENY** |
| MINOR 4 | `>  /var/lib/helm/x`, `>>/var/lib/helm/x` | deny | **DENY** ×2 |
| MINOR 5 | `{"tool_name":"Bash", broken` | allow + stderr | allow, `orchestrator-guard: malformed hook input (allowing)` |
| MINOR 5 | `this is not json`, empty input | allow + stderr | allow + warn |
| MINOR 6 | `MultiEdit`, single edit, `\"` inside the *offending* `old_string` | deny | **DENY** |
| MINOR 6 | `MultiEdit`, quote-carrying edit first, heading removal second | deny | **DENY** |
| MINOR 6 | `MultiEdit`, heading removal first, quote-carrying edit second | deny | **DENY** |
| MINOR 6 | `MultiEdit`, escaped backslash in `new_string`, heading rewritten | deny | **DENY** |
| MINOR 6 | `MultiEdit`, benign quote edit only | allow | allow |

MINOR 6 note: my first probe appeared to fail-open. It was my fixture's fault —
the `old_string` did not exist in the file, so the edit legitimately did not
apply. With a fixture whose plan body actually contains `body "quoted" one`, the
guard denies in every ordering. The chosen approach is the escape-aware
extraction (not the documented fail-closed alternative), and the file header at
`tools/orchestrator-guard.sh:182-186` says so.

## Bypass attempts

| Attempt | Result | Severity |
|---|---|---|
| `Write`, content identical except `(code, S)` → `(code, M)` | **DENY** | ok |
| `Edit` whose `old_string` spans the heading **plus** the preceding line | **DENY** | ok |
| `Edit` renaming the key `A1` → `A9` | **DENY** | ok |
| `Edit` dropping only the type from the heading | **DENY** | ok |
| `Edit` with `replace_all` mangling every `### ` | **DENY** | ok |
| `git   commit   --amend` (multiple spaces) | **DENY** | ok |
| `GIT_EDITOR=true git commit --amend` (env prefix) | **DENY** | ok |
| `command git commit --amend`, `\git commit --amend` | **DENY** | ok |
| `/run/current-system/sw/bin/git commit --amend` | **DENY** | ok |
| `git --git-dir .git commit --amend` (space form) | **DENY** | ok |
| decoy `"file_path"` / `"tool_name"` embedded in `new_string` and in a command | **DENY** | ok |
| pretty-printed multi-line payload, heading removed | **DENY** | ok |
| **`git --work-tree=. commit --amend`** | **ALLOWED** | **MAJOR** |
| **`git -P commit --amend`** | **ALLOWED** | **MAJOR** (same root) |
| **`git --literal-pathspecs commit --amend`** | **ALLOWED** | **MAJOR** (same root) |
| **`git --exec-path=/x commit --amend`** | **ALLOWED** | **MAJOR** (same root) |
| `git --no-replace-objects commit --amend` | **ALLOWED** | same root |
| `git -c a=b --work-tree=. commit --amend` | **ALLOWED** | same root |
| `cd /tmp && git --work-tree=. commit --amend` | **ALLOWED** | same root |
| `git --icase-pathspecs rebase -i`, `git --namespace=n push` | **ALLOWED** | same root |
| `/run/current-system/sw/bin/git push` / `… rebase -i` | **ALLOWED** | MINOR 7 (also allowed by OG1 — not a regression) |
| `git commit\`⏎`  --amend` (no space before the backslash) | **ALLOWED** | MINOR (also allowed by OG1; `git commit \`⏎`--amend` denies) |
| `Write` through a symlink **from** the plans dir outward | **ALLOWED** | MINOR 8 |
| `cp /var/lib/secrets/x /tmp/y` (read *from* a protected path) | **DENIED** | MINOR 9, over-reach |
| `sed -i '/### A1/d' plans/x.md`, `rm plans/x.md`, `git checkout HEAD~1 -- plans/x.md` | **ALLOWED** | NOTE — outside the plan's declared interface |

The four MAJOR spellings are not theoretical. Against a throwaway repo in the
scratch dir: `git --work-tree=. commit --amend -m …` → head moved; `git -P commit
--amend` → head moved; `--literal-pathspecs` and `--exec-path=` likewise. git
2.50.1, the host's own.

## Checks

| Check | Command | Result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass — tests 158–187 are the 30 `91-orchestrator-guard` tests, all `ok` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | clean |
| pre-commit | `nix develop -c githooks/pre-commit` | **exit 1** — `tasks: docs/OPERATIONS.md queue block was stale`; passes (exit 0) once the block is regenerated. Structural, not the implementer's: `landed_subjects()` reads git log, so OG1b's key drops out of the queue the moment its commit exists. Base `d664bf3` passes clean. |
| `docs/MAP.md` forced? | reverted MAP to base, `python3 pkgs/evidence/repomap.py check` | `docs/MAP.md is stale` → forced; clean at HEAD |
| wall time, 10 calls each | `git status` 10.6–11.7 ms; deny-sudo 9.8–10.7 ms; heading `Edit` 25.2–27.4 ms; `Write` 20.8–21.9 ms; `MultiEdit` ×2 31.7–33.3 ms; `Write` of the real 33 673-byte `2026-09-05-seat-routing.md` 37.9–39.4 ms | all far under 300 ms |

Red before green: OG1b's bats file run against **OG1's** guard (fetched from
`ws/og1/OG1`) fails 8 of the 11 new tests — 7 (git global options), 9 (sudo in
prose), 11 (tee -a/cp/mv/install/wide redirect), 19 (MultiEdit escaped quote),
21–23 (`..`, `./`, symlink), 28 (malformed `{`). The three that were already
green are allow-side regression tests. Honest red.

## Mutation table

Each applied to `tools/orchestrator-guard.sh`, `bats
tests/unit/91-orchestrator-guard.bats` run, then reverted. The clone was left
clean.

| # | Mutation | Failures | Killed by |
|---|---|---|---|
| 1 | `missing_headings()` reports nothing | 8 | all four heading tests + the three path-shape tests + MultiEdit-quote |
| 2 | `git … commit --amend` pattern neutered | 2 | 4, 7 |
| 3 | `sudo` pattern neutered | 2 | 1, 10 |
| 4 | deny JSON `permissionDecision` → `"block"` | 16 | every deny test |
| 5 | `is_plan_file` reduced to "any `*.md`" | 2 | 20, 24 (over-reach guards are load-bearing) |
| 6 | malformed input `exit 3` instead of warn-and-allow | 2 | 27, 28 |
| **7** | **`resolve_path` returns the raw path (normalisation removed)** | **3** | 21, 22, 23 |
| **8** | **`GIT_CMD` → `git[[:space:]]+` (flag tolerance removed)** | **1** | 7 |
| **9** | **`sudo` anchors loosened back (`[[:space:]]` in the leading class)** | **1** | 9 |
| 10 | `multiedit_after` extraction reverted to `[^"]*` | 1 | 19 |
| 11 | `cp\|mv\|install` protected-write rule removed | 1 | 11 |
| 12 | malformed-`{` completeness check removed | 1 | 28 |
| 13 | `apply_edit` made a no-op | 7 | 12, 13, 18, 19, 21, 22, 23 |
| 14 | `tee` protected-write rule removed | 1 | 11 |
| 15 | redirect rule loses the wide-space tolerance | 1 | 11 |
| 16 | `is_plan_file` stops canonicalising the *plans dir* side | **0** | **survivor** — no-op under the fixture (`BATS_TEST_TMPDIR` is already canonical); see MINOR 10 |

The three mutations the gate brief demanded (7, 8, 9) each kill a test. Fifteen
of sixteen killed; the survivor is a fixture no-op, not a hole in the guard.

## Findings

**MAJOR — `--amend` still escapes; MAJOR 2 was widened, not fixed.**
`tools/orchestrator-guard.sh:59`, `GIT_CMD`. The fix enumerates
`-c V`, `-C V`, `-C…`, `--no-pager`, `--git-dir=V`, `-p`, `--paginate` — and
stops. Git's global option set is much larger, and the plan's own OG1b spec
named one of the missing ones: "`git` followed by any number of `-c k=v`,
`-C path`, `--no-pager`, `--git-dir=…`, **`--work-tree=…`** tokens, then the
subcommand." Verified working amends that the guard allows:
`git --work-tree=. commit --amend`, `git -P commit --amend`,
`git --literal-pathspecs commit --amend`, `git --exec-path=… commit --amend`,
`git --no-replace-objects commit --amend`, and `git -c a=b --work-tree=. commit
--amend`; also `git --namespace=n push` and `git --icase-pathspecs rebase -i`.
The OG1 review offered the durable alternative and the implementer took the
brittle branch: "or better, tokenise and find the first non-option word after
`git`." That is the fix. An enumeration will keep leaking; git ships more global
options than a regex will ever carry, and a guard that is *for* banning `--amend`
must not be defeated by `-P`.

**MINOR 7 — `/…/bin/git push` and `/…/bin/git rebase` are allowed.**
Lines 120 and 125 anchor push/rebase on `(^|[;&|()[:space:]])`, and `/` is in
neither branch; the `commit --amend` and `reset --hard` patterns carry no such
anchor and do catch the absolute path. Inherited from OG1 verbatim, so not a
regression, but the same tokenise fix removes it. Asymmetric anchoring across
four rules that share one purpose is itself the smell.

**MINOR 8 — a symlink *from* the plans dir outward escapes the heading rule.**
`resolve_path` follows the link, so `Write` on
`docs/superpowers/plans/link.md` (target outside) is judged by the target's
location and allowed. I do not grade this a MAJOR: it cannot alter a real
regular-file plan, and planting such a link needs a Bash `ln` the guard does not
police anyway (see the NOTE). The brief asked for a deny; if the decision is to
deny, the rule is "canonicalise `..`/`./`/relative segments, then check whether
*either* the lexical path *or* its realpath sits in the plans dir" — deny if
either does. State the choice in the header either way; today it is unstated.

**MINOR 9 — the protected-prefix `cp|mv|install` rule denies reads.**
`cp /var/lib/secrets/x /tmp/y` is refused, because the regex anchors on the first
argument that starts with a prefix rather than on the *last* argument. Deny-only,
so the blast radius is an annoyed orchestrator, not a broken host — but the
orchestrator legitimately copies out of `/var/lib/egress-broker/*/audit.jsonl`.
Match the final path token instead.

**MINOR 10 — mutation 16 survives.** `is_plan_file` canonicalises `$1` but the
comparison would still hold if the *plans-dir* side stopped canonicalising,
because the fixture's `CLAUDE_PROJECT_DIR` is already canonical. Add one test
whose project dir is reached through a symlink (`ln -s "$PROJECT" "$link"`,
`CLAUDE_PROJECT_DIR=$link`) and the mutation dies.

**MINOR 11 — the runbook and the commit body over-promise on git.**
`docs/runbooks/session.md` says `git commit --amend`, `git push`, `git rebase`,
`git reset --hard` are refused, full stop. Four ordinary spellings are not. Same
prose-vs-implementation gap the OG1 review raised as MINOR 4; narrow the prose or
widen the rule (widen it).

**NOTE — headings are still removable through `Bash`.** `sed -i '/### A1/d'
docs/superpowers/plans/x.md`, `rm`, a `python3 -c` write, and `git checkout HEAD~1
-- <plan>` are all allowed. This is outside the plan's declared interface
(Edit/Write/MultiEdit only), so it is not counted against OG1b — but it is
squarely inside the operator's ask ("can you ban your ability to do that?"), and
the guard as shipped is a speed bump on a determined session rather than a ban.
It wants a plan-level decision, not a patch: either extend the Bash rule to any
command whose text names a path under `docs/superpowers/plans/` with a mutating
verb, or state plainly in the runbook that the guard covers the tool path only.

**NOTE — `pre-commit` is red on the committed tree, blamelessly.**
`pkgs/evidence/tasks.py:137 landed_subjects()` reads git log subjects, so once
OG1b's commit exists the key is "landed" and the generated queue block in
`docs/OPERATIONS.md` no longer lists it. The board is the orchestrator's file and
is not in OG1b's touches; regenerating it at merge clears the gate (verified:
exit 0 after regeneration). Not a defect — but it means "pre-commit passes" is
only true pre-commit, and the merge step must include the board regeneration.

## Deviations

Accepted:

- `tools/orchestrator-guard.sh` (bash) rather than the plan's `.py` — carried
  from OG1, sanctioned there, re-measured here at 10–39 ms/call.
- `docs/MAP.md` outside OG1's declared touches — inside OG1b's, forced by
  `repomap check` (proved), and disclosed in FACTORY-NOTES as the gate asked.
- `flake.nix`: exactly the one `cp` line plus its two comment lines, mirroring
  G6's.
- `.claude/settings.json`: G6's SessionStart entry byte-for-byte, plus the two
  PreToolUse matchers and nothing else.
- MINOR 6 solved by the escape-aware extraction rather than the documented
  fail-closed fallback; the plan allowed either and the header states which.

Not accepted:

- The plan's OG1b step 1(b) spells the git pattern with `--work-tree=…` in it.
  The implementation omits it, and the omission is a working `--amend`. MAJOR.

Verdict: **REJECTED** (second rejection ⇒ re-plan, rule A1).

**The design change for the re-plan.** Stop specifying the git rule as a flag
enumeration — that is what failed twice. Specify it as a tokeniser:

1. Normalise the command once: drop `\`+newline pairs, tabs → spaces.
2. Find each `git` **word** — at a command boundary (`^`, `;`, `&`, `|`, `(`,
   `)`, newline, or after `env`/`command`/a `VAR=value` prefix) or as the
   basename of a path token (`…/git`).
3. From there, walk tokens forward, skipping every token that starts with `-`,
   and additionally skipping the following token when the option is one of
   `-c -C --git-dir --work-tree --exec-path --namespace --config-env` in their
   space-separated form.
4. The first non-option token is the subcommand. Deny on
   `commit` (when `--amend` appears in the remaining tokens), `push`, `rebase`,
   `reset --hard`.

Acceptance for the re-plan: a table-driven bats case listing at minimum
`--work-tree=.`, `-P`, `--literal-pathspecs`, `--exec-path=`,
`--no-replace-objects`, `--namespace=`, `--icase-pathspecs`, an absolute-path
`git`, and the space-separated `--git-dir .git` / `--work-tree .` forms — each
denied — against positive controls (`git -c a=b status`, `git -C . log -1`,
`git --work-tree=. status`, `git commit -m x`) that must stay allowed. Add the
symlinked-project-dir test (MINOR 10) so mutation 16 dies, fix MINOR 9's last-token
match, and settle MINOR 8 in the header. Everything else in OG1b is sound and
should be carried forward unchanged.
