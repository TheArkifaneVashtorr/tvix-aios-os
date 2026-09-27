# Draft checklist — plan 2026-09-11-generation (draft-0), Appendix A's eight questions per section

Draft: `/tmp/draft-scratch/draft-0.md` (11,498 words, four typed sections). Checked copy: `/tmp/draft-scratch/2026-09-11-generation.md` (the prefix guard keys on the basename; `check --draft` on `draft-0.md` refuses every `GN` key, on the copy it is clean — a harness/guard interplay recorded in the draft's Assumption 19).

## Machine checks run on the draft

- `nix develop -c python3 pkgs/evidence/tasks.py --root . --runs-dir /nonexistent --store /nonexistent check --draft /tmp/draft-scratch/2026-09-11-generation.md` → exit 0; `waves: [[["GN2"]], [["GN3"]]]`; 40 `conflicts:` rows.
- Scratch copy (`cp -a`, one-repo `--repos` file, draft under the plans glob): `check` → empty, exit 0; `conflicts` → 429 lines, 40 with a `GN` key; `waves --repo nixos-agent-env --json` → GN1 in wave 2, GN4 in wave 3 (GN2 attributed to media; GN3 unresolvable without a media graph).
- `tasks.py probes <copy> GN1|GN2|GN3|GN4` → every probe parses (the first draft's numeric `eq` probes were refused with "eq/ne on a number — state a bound (le, ge)" and rewritten as bounds).
- `tools/factory/seat/factory-brief <copy> <KEY>` for each key → exit 0, no stderr, each section ends at `## WORKSPACE RULES` (whole), the `**probes:**` block present, GN4's indented `## ` lines survive, the `body.sh` recipe and Assumption 24 reach the seat.
- `factory-dispatch … --dry-run` on the scratch copy: today `nothing schedulable`; with EV10's subject in the log `would run: factory-wave gn1 … "GN1"`; with GN1's too `"GN4"` (GN3 waits on media).

## GN1 — the manifest row

1. **Mutant per assertion.** Interface 1 (the path resolves to Generation) → M1 drop-owns-line; Interface 2 (the superseded plan refuses a GN key) → M2 keep-superseded-plan; Interface 3 (no `ambiguous:`) → M3 glob-not-path; Interface 4 (mirror current) → M4 stale-mirror. Each names its kill command and expected line.
2. **Discriminating fixture rows.** The guard replay uses key `GN99` (prefix `GN`), not `GNX` (prefix `GNX`, which passes and would make the test vacuous — measured); M3's row is a decision file another row already owns (`2026-09-09-redesign-answers.md`, Program's), so a glob is caught as `ambiguous`, not merely accepted.
3. **Rules, not spellings.** The guard is `reserved_prefix` (letters before the first digit or hyphen) against the row's `plans` globs; coverage is `fnmatch` over the file list; no list of spellings.
4. **Interfaces and error contracts.** Which tree: the workspace's manifest and `git ls-files`; `validate` → stderr lines + exit 1; `write --check` → the stale line + exit 1; `check()` → a list. Consumers: `subsystems-manifest`, `lint`'s `tasks.py check`, the reserved-prefix guard.
5. **Facts with commands.** The row (`awk`), the untyped headings (`grep -c '^### '` → 4), the plan-status rows, the fnmatch `[]`, the guard replay `[]` before / the refusal after (scratch copy), the zero-byte mirror diff, the validator accepting an absent path — each with its command; anchors quoted, no line numbers.
6. **Mandated output vs acceptance grep.** None: the task adds no text a grep forbids; `lint` and `subsystems-manifest` are the acceptance and both are built.
7. **Fix round / re-plan.** Not applicable (first section).
8. **The brief is the whole contract.** `factory-brief` output carries Files (the exact TOML lines), Interfaces, Facts, Steps with the red and green commands, the mutants and the probes; nothing points to another file's shape.

## GN2 — media's nixpkgs onto the host pin (repo: media)

1. **Mutant per assertion.** Interface 1 (the rev) → M1 wrong-rev; Interface 4 (URL and lock cannot drift) → M2 lock-only; Interface 3 (one node moved) → M3 second-node; Interface 2 (21 checks green) → Step 3's run with Step 0 as the control.
2. **Discriminating rows.** M1 uses this repo's *other* nixpkgs rev (`34ab9907…`) so "some rev" and "the host rev" are told apart; Step 0's green at the old rev is the control that makes a Step-3 red attributable to the rev.
3. **Rules.** "The root input whose node's rev begins `ac62194c`" is the rule for the input's name (the seat reads the map); parity is equality of two revs, not a whitelist.
4. **Interfaces and error contracts.** Three failure arms named with the exact `FACTORY-RESULT`/`FACTORY-NOTES` form (base red, new-rev red, already at host rev); which tree: the media workspace; `nix flake check` refusing a mismatched pin is quoted as the mechanism.
5. **Facts with commands.** Host rev (`grep -n 'nixpkgs-host.url'`, `jq`), the old pin (`sed -n '12p' flake.nix`), the judgement's two revs, the 21 check names (quoted from the block, dated), the root-inputs map shape (`jq`); the `nix eval` form is marked as not run here (Assumption 24).
6. **Mandated output vs acceptance.** None.
7. **Fix round / re-plan.** Not applicable; A9 says a red sibling is re-planned, not fix-rounded.
8. **The brief.** Self-contained except the one measured substitution (the input's name), stated as a rule with its reporting form. Weakness acknowledged: the 21-name subject is long; it equals the acceptance list byte for byte.

## GN3 — media on core

1. **Mutant per assertion.** Eight assertions, eight mutants (M1 lan-on, M2 module-dropped, M3 port-collision, M4 port-opened, M5 timer-line-dropped, M6 lock-drift, M7 wrong-user, M8 map-stale) plus the neighbour's parity throw as the control. Known survivor: the eighth assertion's "at least one on-demand unit" has no mutant that makes every comfy unit always-on (the unit names are media's; recorded as a row-5 weakness).
2. **Discriminating rows.** M3 duplicates a port rather than removing a world (so the count-four rule, not the names rule, catches it); M4 opens 443 itself; M5's two arms (declared-enabled, undeclared) both fail the two-sided assertion; M6 uses a rev that exists so the message carries both revs.
3. **Rules.** Ports distinct by `unique`, firewall closed by membership over every world port and 443, the timer "declared and disabled" (two-sided), parity by equality, comfy units by name infix; no list of unit names.
4. **Interfaces and error contracts.** Interface 7: the option-set contract (a set other than the six names stops the task with the list; `enable` if present is set and reported), the module-eval error arm, the fetch-failure arm; Interface 6 names which tree each derivation reads.
5. **Facts with commands.** The gaming input and comment, the parity throw, `coreModules`, the imports list, MAP's Hosts lines, host-core's assertion home, the lanes/seat reservations, helm.nix's loopback message, the option names (quoted, dated), the media rev strings (judgement), `jq` parity `true` — each with its command; nothing from a `nix eval` run here (Assumption 24).
6. **Mandated output vs acceptance.** The new host file changes `docs/MAP.md`; Step 4 regenerates it before `lint`; M8 proves the grep bites.
7. **Fix round / re-plan.** Not applicable.
8. **The brief.** The input lines, the `let` bindings, the eight assertions, the stanza file and the import are verbatim in the section; the only Base-time measurement is the option set, with its contract.

## GN4 — the probe's egress decision (docs)

1. **Mutant per assertion.** Interface 1 (owned path) → M1 wrong-path; Interface 2 (five sections) → M2 no-closing-condition; the hosts count → M3 seventh-host (and the `ge 6` probe catches a dropped host).
2. **Discriminating rows.** M1's path differs by one word and stays under `docs/decisions/`, so the exact-path `owns` line (not a directory glob) is what discriminates; M3's seventh entry is the regex literal the record names as the false host.
3. **Rules.** The decision states the rule (inside the namespace or not at all; the listener answers only from inside) rather than a host list as policy — the six hosts are the closing task's allowlist, quoted from the record.
4. **Interfaces and error contracts.** A docs task: the file's structure is the interface (H1, five H2s, six host bullets); `validate`'s silence is the ownership contract.
5. **Facts with commands.** The 2026-09-02 decision's conclusion (`grep -n 'stays brokered'`), the nft line, the lanes reservation, the six hosts (judgement erratum 7).
6. **Mandated output vs acceptance.** None; `lint` does not read decision files.
7. **Fix round / re-plan.** Not applicable.
8. **The brief.** The file body is verbatim (indented two spaces so the extractor's `## ` rule does not cut the section; the seat de-indents); measured: `factory-brief … GN4` carries the last probe line.

## Plan-level

- Three operator questions, each with a recommendation, a default and the effect of the other answer; five plan decisions with the refused alternative.
- Waves from `tasks.py` in both forms, pasted; the `--plan` form's `[]` and the draft form's `[[["GN2"]], [["GN3"]]]` explained.
- `## Dispatch` with the dry-run lines measured on the scratch copy and the A1 landing recipe (reset, merge main by the integrator, review, integrate, ff); `## Operator` with one command per step, the switch closure as a prediction to be measured, the rollback generation; `## Anticipation` rows A1–A14 where triggered; `## Not in this plan` with the media-side contract.
- Driver guards: P11/P11r are landed (graph states), so no edge and no interim sentence.

## Self-score (rubric §5.1), with reasons

| row | score | reason |
|---|---|---|
| 1 spec coverage | 2 | every §5 item and charter item mapped or `out:` with a reason; sub-projects 2/3 and the mutator are out (media-side), which a judge may read as thin coverage of increment 3 |
| 2 correct facts | 3 | every fact pasted with its command; media facts quoted and dated; the `nix eval` forms explicitly not run here |
| 3 self-contained | 2 | GN1/GN4 land from the brief alone; GN2's input name and GN3's option set are Base measurements with stated contracts |
| 4 TDD | 3 | a red command with expected output per task; GN2's Step 0 measures the base |
| 5 mutants / fixtures | 2 | one mutant per assertion; the on-demand rule in GN3 lacks a killing mutant; GN4's docs mutants are counts |
| 6 interfaces / errors | 2 | failure arms named per task; GN3's comfy-unit producer (the unit names) is media's and unnamed |
| 7 rules | 3 | rules over values; the driver guards are landed tasks, not sentences |
| 8 waves / touches / conflicts | 3 | measured in both forms, pasted, sequenced |
| 9 invariants | 3 | G12 bound per task; no key in Nix; no port, no instance, no widening |
| 10 operator | 2 | one command per step with acceptance and rollback; the unit names are read at step 4, not pre-written |
| 11 anticipation | 3 | every triggered row has its artefact; dry runs measured |
| 12 economy | 2 | 11,498 words for four tasks; the verbatim constraints block and 24 assumptions weigh |
| 13 format / graph | 3 | `check --draft` empty on the basename copy; one-repo `check` empty; probes parse; briefs whole; subjects byte-exact |
| 14 judgement calls | 3 | three bounded questions; every other decision stated with its alternative |

Total 36 of 42.

## Defects met while drafting (not bug-noted: this run may not write outside the repository and the scratch directory)

- `draft-packet`'s required draft path `draft-0.md` is refused by `tasks.py check --draft` for every reserved-prefix key (the guard keys on the basename); the check works only on a copy named after the plan.
- The probe grammar refuses `eq`/`ne` with a numeric value; exact numeric probes must be written as a `ge`/`le` pair.
- `docs/superpowers/plans/2026-09-11-defects.md` (the DF8d recipe the drafting prompt cites) is absent from this tree; the recipe is restated in the draft's Global Constraints.
- This checkout's `nix` is a `nix develop -c` shim with no real nix behind it; `nix eval`/`nix build` cannot be run at draft time.
