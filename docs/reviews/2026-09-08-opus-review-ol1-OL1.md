---
plan_defect: vacuous
plan_defect_secondary: wrong-fact
mutants_total: 9
mutants_killed: 9
mutants_outside_named: 5
model: opus
---
# Opus gate — seat run ol1, task OL1 — APPROVED

## Summary

The central question resolves against the orchestrator's worst case: `flake-check=pass` is
**not fabricated**. `nix flake check -L` really ran (`~/factory/runs/ol1/OL1.log:1819`) and
really printed `all checks passed!` (`:1832`). What the seat did wrong is name it in
`FACTORY-CHECKS` as if it were a `checks.${system}` attribute; it is a *command* from the
section's Step 3, not a check the flake defines, so the driver's attribute-resolving verifier
recorded `flake-check=not-run:absent` and classed the run `checks-unverifiable`. That is a
reporting-protocol slip (MINOR-1), not a false gate claim.

Held to fresh scepticism, the two real acceptance checks are genuine. I rebuilt both from a
fresh clone at `2022032` with `--rebuild`: `lint` exit 0, `lab-vm` exit 0. `lab-vm` is not
theatre — it boots a QEMU machine, imports `nixos-agent-env.nixosModules.evidenceStore` from
the pinned revision, runs the real `evidence` CLI inside the guest and reads back
`/var/lib/evidence/checks.jsonl`. Its Y1 mutant (`enable = false`) turns the guest's
`record-check` into `evidence: command not found`, which is only possible if the *pinned
module* is what puts that binary on the guest's PATH. All nine named mutants die.

The two deviations from the section's literal Interfaces are both forced, both disclosed in
the commit body, and both — I verified — correct. The plan's supplied lint guard is a
**vacuous test**, and the plan's supplied `tests/lab-vm.nix` template **fails the plan's own
`checks.lint`**. The seat found the first unaided and fixed both. Failure class seen for this
first Codex run through the arm: `result-protocol-naming` (a check name reported that is not a
flake attribute) — no substance failure, unlike the DeepSeek classes.

No MAJORs. APPROVED.

## Contract items

Section `### OL1 (code, S)`, plan `docs/superpowers/plans/2026-09-08-openai-lab.md:188-301`.

| # | contract item (plan line) | met | evidence |
|---|---|---|---|
| 1 | Create `flake.nix`, `flake.lock`, `treefmt.toml`, `tests/lab-vm.nix` (`:193`) | yes | diff creates exactly those four, 362 insertions |
| 2 | `outputs = { self, nixos-agent-env, nixpkgs }:` (`:197`) | yes | `flake.nix:9-14` (nixfmt splits the pattern over lines) |
| 3 | input `git+file:///home/dalhaka/nixos-agent-env?ref=main&rev=d2ad5c79…` (`:197`) | yes | `flake.nix:5` verbatim; `flake.lock:136` `"rev": "d2ad5c79dd4e6cdfa24e0ed20629ae1632908237"`, `:143` same in `original` |
| 4 | pin is a real commit exporting the module (Assumption 1) | yes | `git -C ~/nixos-agent-env cat-file -t d2ad5c79…` → `commit`; that rev's `flake.nix:697` `evidenceStore = import ./nixosModules/evidenceStore.nix;` |
| 5 | `nixpkgs.follows = "nixos-agent-env/nixpkgs-host"` (`:197`) | yes | `flake.nix:6`; `flake.lock:228-235` root node `"nixpkgs": ["nixos-agent-env","nixpkgs-host"]` |
| 6 | `formatter.${system} = pkgs.treefmt;` (`:197`) | yes | `flake.nix:27` — untested (MINOR-4) |
| 7 | `treefmt.toml` exactly the plan's block (`:201-210`) | yes | `cmp` of plan lines 202-209 against the file: **byte-identical** |
| 8 | `lintTools = [ treefmt nixfmt-rfc-style statix deadnix ruff ]` (`:218`) | yes | `flake.nix:18-24` |
| 9 | `checks.lint` = the plan's derivation (`:222-232`) | yes, one deviation | `flake.nix:29-38`; the guard line `:36` is rewritten — see MAJOR-none / MINOR-2 and §Mutants O4 |
| 10 | `lab-vm = import ./tests/lab-vm.nix { inherit pkgs nixos-agent-env system; }` (`:233`) | yes | `flake.nix:39` verbatim |
| 11 | `devShells.default.packages = lintTools ++ [ python3 pytest git ]` (`:235-237`, D5) | yes | `flake.nix:41-47` |
| 12 | `tests/lab-vm.nix` header `{ pkgs, nixos-agent-env, system }:` (`:246`) | yes | `tests/lab-vm.nix:1-5` |
| 13 | one node importing `nixos-agent-env.nixosModules.evidenceStore`, `enable`/`owner`/`group` (`:249-258`) | yes | `tests/lab-vm.nix:9-16` verbatim |
| 14 | `testScript` exactly the plan's (`:259-269`) | yes | `tests/lab-vm.nix:17-27` verbatim, incl. `systemctl is-system-running --wait` (erratum 20) |
| 15 | Step 1.1 red before any file (`:278`) | yes | reproduced: `git init` in an empty dir, `nix flake check` → `path "…" does not contain a 'flake.nix', searching up` / `error: … is not part of a flake …`, exit 1 |
| 16 | Step 2 flip to `enable = true` (`:291`) | yes | `tests/lab-vm.nix:12` |
| 17 | Step 3 green: `lint`, `lab-vm`, `nix flake check -L` (`:292`) | yes | all three re-run by me, §Checks |
| 18 | Step 4 one commit, subject, trailers (`:293`) | yes | §Touches and commit |
| 19 | `touches` = the four files (`:299`) | yes | diff --stat lists exactly them |
| 20 | acceptance `lint, lab-vm` (`:300`) | yes | both exit 0 under `--rebuild` |

Deviation A — `tests/lab-vm.nix:6` adds `assert system == pkgs.stdenv.hostPlatform.system;`,
absent from the plan's template. Disclosed in the commit body ("Assert system matches the
package set to consume the template's otherwise unused argument, which deadnix rejected").
**Verified necessary** — see mutant O1.

Deviation B — `flake.nix:36` replaces the plan's `grep -Fq '&rev=…' flake.nix` with
`grep -E '^[[:space:]]*nixos-agent-env\.url = ' flake.nix | grep -Fq '&rev=…'`. Disclosed
("The supplied pin grep matched its own source … (vacuous-test)"). **Verified necessary** —
see mutant O4.

## Red before green

- **Step 1.1 (the section's own stated red command).** Reproduced in a fresh empty git dir:

  ```
  path ".../emptyred" does not contain a 'flake.nix', searching up
  error: path ".../emptyred" is not part of a flake (neither it nor its parent
  directories contain a 'flake.nix' file)
  EXIT=1
  ```

- **Y1 red (the bootstrap state).** Base has no implementation at all, so the section's red is
  the branch's own `tests/lab-vm.nix` with `enable = false`. Applied to the branch tree:

  ```
  vm-test-run-openai-lab-vm> machine: must succeed: evidence record-check --name lab --rev 000…0 --ok --class unit --src lab
  vm-test-run-openai-lab-vm> machine # bash: line 1: evidence: command not found
  vm-test-run-openai-lab-vm> !!! Traceback (most recent call last):
  error: Cannot build '/nix/store/70jd846alphmbrz7vjl2kbldwczwydj6-vm-test-run-openai-lab-vm.drv'.
  EXIT=1
  ```

  Reverted (`enable = true`): `nix build .#checks.x86_64-linux.lab-vm -L --no-link --rebuild`
  exit 0, guest completes `record-check` and `cat /var/lib/evidence/checks.jsonl`.
  **This is the discriminating fact for the orchestrator's doubt: the check fails exactly when
  the pinned module is disabled, so it does boot the pinned module.**

- **`lint` red/green.** Every arm shown red below and green on the clean tree
  (`--rebuild`, exit 0, `All checks passed!`).

No test in this section is vacuous **as shipped**. The plan's *stated red procedure* for
Y3–Y6, however, is (MINOR-3).

## Mutants

Each applied in the fresh clone, run through the acceptance check named, then reverted.

### Named by the section (9 / 9 killed)

| # | mutant | check | result | evidence |
|---|---|---|---|---|
| Y1 | `enable = false` | lab-vm | KILLED | `machine # bash: line 1: evidence: command not found`, exit 1 |
| Y2 | call `--class vm`, keep the `"class":"unit"` assertion | lab-vm | KILLED | `vm-test-run-openai-lab-vm> AssertionError`, exit 1 |
| Y3 | mis-indented copy `tests/_fixture.nix` (`sed 's/^  name =/name =/'`) | lint | KILLED | `formatted 3 files (1 changed)` / `Error: unexpected changes detected, --fail-on-change is enabled`, exit 1 |
| Y4a | delete `&rev=d2ad5c79…` from the URL only (`flake.nix:5`) | lint | KILLED | all lint tools green (`All checks passed!`), builder then exits 1 on the guard; `nix build` exit 1 |
| Y4b | swap the URL sha for another 40-hex (`1b35447cee…`) | lint | KILLED | same shape: tools green, guard fails, exit 1 — the guard is exact-sha, not mere `&rev=` presence |
| Y5a | `_fixture.nix` = `{ ... }: 1` | lint | KILLED | `[10] Warning: Found empty pattern in function argument … ╭─[ ./_fixture.nix:1:1 ]`, exit 1 |
| Y5b | `_fixture.nix` = an unused `let` binding | lint | KILLED | nixfmt-clean form isolates the arm: `Warning: Unused declarations were found. ╭─[./_fixture.nix:2:3] … Unused let binding: unused`, exit 1. (The plan's literal one-liner `let unused = 1; in 2` is also red, but killed by the treefmt arm first — `formatted 3 files (1 changed)` — before deadnix runs.) |
| Y6a | `_fixture.py` = `import os` (format-clean) | lint | KILLED | `F401 [*] \`os\` imported but unused --> _fixture.py:1:8 … Found 1 error.`, exit 1 |
| Y6b | `_fixture.py` = `import os` + `x=  1` | lint | KILLED | `formatted 3 files (1 changed)` / `Error: unexpected changes detected`, exit 1 (the `ruff format` arm, reached through treefmt's python formatter) |

### Outside the named set (5 tried; 2 killed, 3 survived)

| # | mutant | check | result | what it proves |
|---|---|---|---|---|
| O1 | delete `tests/lab-vm.nix:6` — i.e. **the plan's literal template** | lint | KILLED | `Warning: Unused declarations were found. ╭─[./tests/lab-vm.nix:4:3] … Unused lambda pattern: system`, exit 1. The section's own Interfaces block cannot pass the section's own `checks.lint`. Deviation A is forced. |
| O2 | `owner = "dalhaka"; group = "users";` (the module defaults) | lab-vm | **SURVIVED** (exit 0) | Assumption 1's premise ("a bare `runNixOSTest` machine has neither — only `root`/`root` are guaranteed") is not borne out: `systemd.tmpfiles` and `record-check` both succeed with the defaults. The `root`/`root` override is inert. Plan wrong-fact, no code consequence — MINOR-5. |
| O3 | `--name other` in the call, keep the `"name":"lab"` assertion | lab-vm | KILLED | `vm-test-run-openai-lab-vm> AssertionError`, exit 1 — the second assertion is load-bearing too, not only Y2's class one. |
| O4 | restore **the plan's literal guard** `grep -Fq '&rev=d2ad5c79…' flake.nix` with the URL's rev deleted | lint | **SURVIVED** (exit 0) | Direct confirmation of the seat's claim. `flake.nix:5` reads `…?ref=main` with no rev, and lint still prints `All checks passed!` and exits 0, because the grep matches its own text inside the copied `flake.nix`. The plan shipped a vacuous test; Deviation B fixes it. |
| O5 | leave `_fixture.nix` / `_fixture.py` **untracked**, i.e. the plan's Step 1.3 method ("never `git add`ed") | lint | **SURVIVED** (exit 0) | `git status --short` shows `?? _fixture.nix` / `?? _fixture.py`; `nix build .#checks.x86_64-linux.lint` exits 0 in silence, because `${self}` on a dirty git tree excludes untracked files. The plan's stated red procedure cannot redden `checks.lint` — MINOR-3. |

None of the three survivors is an implementation defect: two are the plan's own text failing
(O4, O5) and one is a plan assumption whose premise is false but whose instruction the seat
followed literally (O2).

## Checks

Run from the fresh clone `…/scratchpad/gate/ol1-OL1/gate-ol1-OL1` at `2022032`, tree clean.

| check | command | result |
|---|---|---|
| `lint` | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass**, exit 0 — `formatted 2 files (0 changed)`, `All checks passed!` (statix), two `warning: No Python files found under the given path(s)` (the two ruff arms; expected, no `.py` ships in OL1) |
| `lab-vm` | `nix build .#checks.x86_64-linux.lab-vm -L --no-link --rebuild` | **pass**, exit 0 in 18.3 s — boots, `wait_for_unit multi-user.target` 15.18 s, `systemctl is-system-running --wait`, `evidence record-check …` 0.18 s, `cat /var/lib/evidence/checks.jsonl`, both asserts hold |
| `nix flake check -L` | in the clone | exit 0, `all checks passed!` — but the tail reads `running 0 flake checks...` because both derivations were already realised. Caveat, not a failure: the same line appears in the seat's own run (`OL1.log:1831-1832`). It proves evaluation; the two `--rebuild` builds above prove the building. |
| `flake-check` (as a check attribute) | — | **absent by design.** No such attribute exists; the flake defines `checks.x86_64-linux.{lint,lab-vm}` only (`flake.nix:28-40`), and the section's acceptance is `lint, lab-vm` (`:300`). MINOR-1. |
| `githooks/pre-commit` | — | **not applicable.** `ls githooks` → no such directory; D6 (`plan:34`) explicitly ships no hook for the lab. |
| `ruff check` / `ruff format --check` | — | **not applicable** (no python file in this task's diff), and both ran inside `checks.lint` anyway. |
| `repomap.py write` / `git diff --exit-code docs/MAP.md` | — | **not applicable.** No `pkgs/` and no `docs/` in the lab repo; D2 (`plan:30`) exempts a task attributed to another repo from MAP membership. |
| `tasks.py --root . check` | in `~/nixos-agent-env` | exit 0, silent apart from the known `evaluation warning: nixfmt-rfc-style …` |

No red check.

## Touches and commit

`git diff d3789ab..HEAD --stat`:

```
 flake.lock       | 277 +++++++++++++++++++++++++++++++++++++++++++++++++++++++
 flake.nix        |  49 ++++++++++
 tests/lab-vm.nix |  28 ++++++
 treefmt.toml     |   8 ++
 4 files changed, 362 insertions(+)
```

- Every file is inside `touches: flake.nix, flake.lock, treefmt.toml, tests/lab-vm.nix`
  (`plan:299`). No file outside it. No `docs/MAP.md` (D2). No deviation to record.
- Exactly one commit: `git rev-list --count d3789ab..HEAD` → `1`.
- Subject byte-identical to `plan:301` — `cmp` against the plan's literal string:
  `SUBJECT BYTE-IDENTICAL`.
- Body states the why, pastes the Y1–Y6 red observations and the green commands
  (`nix build … lint`, `… lab-vm`, `nix flake check -L`), and discloses both deviations.
- Trailers, after one blank line, in order (`cat -A`):
  `Generated-By: codex-cli 0.153.4 / gpt-6-astra (codex exec, factory run ol1)$` then
  `Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>$` — matching Global Constraints
  (`plan:39`), `<ver>` = `FACTORY_SEAT_VERSION` = 0.153.4.
- No board commit; `~/flakes/openai-lab` itself untouched (`git log --oneline -1` there is
  still `d3789ab`, `git status --short` empty).
- Plan file untouched: `git -C ~/nixos-agent-env status --short -- docs/superpowers/plans/2026-09-08-openai-lab.md` empty; last commit touching it is `e4258e0` (the Ship commit).

## Findings

**MINOR-1 — a check name reported that the flake does not define.**
`~/factory/runs/ol1/OL1.result:2`: `FACTORY-CHECKS lint=pass lab-vm=pass flake-check=pass`.
`flake.nix:28-40` defines `checks.x86_64-linux.lint` and `checks.x86_64-linux.lab-vm` and
nothing else; the section's acceptance is `lint, lab-vm` (`plan:300`). The claim is **not
fabricated** — `OL1.log:1819` `nix flake check -L` … `:1832` `all checks passed!` — but naming
a Step-3 *command* in a field the driver resolves as a flake attribute produced
`checks_verified: … flake-check=not-run:absent` and `error_class=checks-unverifiable`.
Failure class for the Codex arm's ledger: **result-protocol-naming**. The fix belongs in the
Global Constraints result-block rule (`plan:45`), which does not say the names must be the
section's acceptance names.

**MINOR-2 — the section's Interfaces shipped a vacuous lint guard; the seat replaced it.**
`plan:230` `grep -Fq '&rev=d2ad5c79dd4e6cdfa24e0ed20629ae1632908237' flake.nix` — proved
vacuous by mutant O4: with `flake.nix:5` reduced to `…?ref=main` the check still exits 0 with
`All checks passed!`, because the copied `flake.nix` contains the sha inside the guard itself.
Shipped instead, `flake.nix:36`:
`grep -E '^[[:space:]]*nixos-agent-env\.url = ' flake.nix | grep -Fq '&rev=d2ad5c79…'` —
killed by both Y4a and Y4b. Recorded as the plan's `vacuous` defect, not against the seat.
Carry the corrected form into OL2/OL3, which reuse this derivation.

**MINOR-3 — the section's stated red procedure for Y3–Y6 cannot redden `checks.lint`.**
`plan:280` — "prove Y3–Y6 with transient fixtures (added, run, removed — **never `git add`ed**)".
Mutant O5: with `?? _fixture.nix` / `?? _fixture.py` untracked, `nix build
.#checks.x86_64-linux.lint -L --no-link` exits 0, since `${self}` on a dirty git tree excludes
untracked files — the same "flakes only see tracked files" rule the Global Constraints state
at `plan:39`. The seat consequently proved Y3–Y6 by running the tools directly in the
worktree (`OL1.log:1410-1437`, `nix develop -c deadnix --fail .` at `:1391`), never through the
acceptance check. I closed the gap: `git add`ing each fixture makes `checks.lint` red every
time (§Mutants Y3, Y5a, Y5b, Y6a, Y6b). The arms are load-bearing; only the stated procedure
was not. Fix the plan's wording for OL2/OL3.

**MINOR-4 — three stated Interface contracts with no test.**
`flake.nix:6` `nixpkgs.follows = "nixos-agent-env/nixpkgs-host"` (`plan:197`, Assumption 3),
`flake.nix:27` `formatter.${system} = pkgs.treefmt;` (`plan:197`), and the `devShells.default`
package list incl. `git` (`plan:236`, D5). No check asserts any of them: `checks.lint`'s only
content assertion is the pin grep, and `checks.lab-vm` asserts nothing about them. Swapping the
`follows` for a plain nixpkgs would go unnoticed by `lint` and `lab-vm`. `nix flake check`
does *evaluate* `devShells.x86_64-linux.default`, so a broken package name would be caught
there but not by either acceptance check.

**MINOR-5 — Assumption 1's stated reason for the `root`/`root` override is false.**
`plan:49` — "A bare `runNixOSTest` machine has neither — only `root`/`root` are guaranteed
anywhere, so `tests/lab-vm.nix` overrides both". Mutant O2: with
`owner = "dalhaka"; group = "users";` (the module's own defaults, `evidenceStore.nix:35,40`)
the VM check still exits 0 — `systemctl is-system-running --wait`, `record-check` and the
read-back all succeed. The override at `tests/lab-vm.nix:13-14` is inert. The seat followed the
contract literally, so nothing is owed here; correct the assumption before OL2/OL3 lean on it.

No MAJOR findings.

## Verdict

**APPROVED.** Every numbered contract item is met, the two deviations from the section's
literal Interfaces are forced, disclosed and independently verified necessary, all nine named
mutants die through their acceptance check, both acceptance checks are green on `--rebuild`
from a fresh clone, the touches list holds exactly, and the commit is one commit with a
byte-identical subject and both trailers. The orchestrator's central doubt is answered: the
`flake-check=pass` claim is true about a command the section asked for and misnamed as a check
attribute (MINOR-1), and `lab-vm` genuinely boots the pinned `evidence-store` module — proved
by Y1's `evidence: command not found` and by O3's second assertion. The plan, not the seat, is
what needs correcting before OL2 and OL3 inherit it: MINOR-2 (vacuous guard), MINOR-3
(un-reddenable red procedure), MINOR-5 (false assumption).
