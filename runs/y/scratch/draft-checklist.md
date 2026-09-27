# Draft checklist — 2026-09-11-generation.md (draft-0), Appendix A's eight questions per section, and the self-score

Draft: `/tmp/draft-scratch/draft-0.md` (also copied as `/tmp/draft-scratch/2026-09-11-generation.md` for the `--draft` check). Environment: the F4 snapshot at `c9c5bd7`, no media tree, no nix (Assumptions 1–3 of the draft). The eight questions (design Appendix A): 1 mutant per assertion; 2 discriminating fixture row; 3 rules not spellings; 4 interface reads/emits/consumers; 5 facts with commands and anchor text; 6 no step output fails its own acceptance; 7 fix-round items (n/a: first plan, no fix round); 8 `factory-brief` is the whole contract.

## GN1 — the feed index and the packaged directory
1. Yes — M1–M8 named per assertion (seed-from-last, seed-from-insertion-first, ignore-iTXt, keep-gone-rows, order-asc, tiebreak-dropped, png-touched, raise-on-non-png, timeout-dropped, single-file-interpolation); M8's executable killer is GN3's, stated.
2. Yes — `"9"` inserted before `"3"` (id order ≠ insertion order); two PNGs with equal mtime and `b` inserted before `a`; a junk `.png`; a held write lock.
3. Yes — "every chunk", "the numerically lowest id", "class_type starts with KSampler", "every `.py` in one store directory", no name lists.
4. Yes — reads the PNGs read-only and `feed.sqlite`; emits `ValueError`/`OperationalError` arms and exit 2 with its stderr line; consumers GN2–GN6.
5. Yes — Facts list the commands (`grep -n '\${\./' …`, the cp block, `ls tests/comfy-worlds/`, the sdxl.json counts), sources Assumptions 20–22; the seat pastes at Step 0.
6. No conflict — the green greps are counts the change produces.
7. n/a.
8. Yes — Files/Interfaces/Steps carry the fixture writer, DDL, signatures and the commit script; the section names no other file to copy from.

## GN2 — the job queue
1. Yes — M1–M8 (seed-first-only, no-sampler-tolerated, check-dropped, loopback-rule-dropped, 4xx-as-unreachable, json-error-escapes, poll-aborts, run-once-raises).
2. Yes — two samplers with `"9"` first; `bogus` kind; 400 with a body; a 200 non-JSON body; two submitted jobs with the first failing; the fake down.
3. Yes — host rule (`127.0.0.1`/`localhost`), the four enumerated arms are exception classes and status ranges, "every KSampler-class node", "the remaining jobs are still polled".
4. Yes — reads `feed.sqlite`, POSTs `/prompt`, GETs `/history/<id>`; every arm's state and return value; consumers GN4, GN6.
5. Yes — Step 0's three commands; the stdlib `queue` fact by `python3 -c`.
6. No conflict.
7. n/a.
8. Yes — the fake's shape is written out (not borrowed); DDL and signatures inline.

## GN3 — the feed page
1. Yes — M1–M6 with M3a–M3f one per HTML rule arm.
2. Yes — three mtimes; a liked row; one payload per rule (script, formaction, meta refresh, on-handler, `//`, `data:`); a held lock; a non-loopback URL.
3. Yes — the zero-outbound property is a rule over every attribute value with a closed tag set, replacing the three-spelling list (2026-09-14 erratum 22).
4. Yes — routes, status codes (200/303/404/405/413/501→gone/503), `Cache-Control`, exit 2 on a missing world dir; consumers GN4, GN8, Helm's link.
5. Yes — Facts commands (`grep -n 'feed_placeholder\|comfy-feed' …`, the guard tests to move); Helm's rule quoted for the seat.
6. No conflict; a possible `flake.nix` edit outside `touches` is pre-disclosed with a `Deviation:` line.
7. n/a — but the two deleted placeholder tests name their replacements.
8. Yes.

## GN4 — the three verbs
1. Yes — M1–M7 and the negative control.
2. Yes — unknown name; the same name twice; stored seed 42 vs injected 777; two positive encoders with identical text plus a negative one; 70000 bytes; no `Content-Length`; a handler that raises once.
3. Yes — "every `CLIPTextEncode` node whose text equals the stored prompt"; a byte cap for every POST; `parse_qs`.
4. Yes — every route's arms (303/400/404/409/411/413), the worker's loop contract, `GET /jobs` fields; consumers GN8, GN9, the drill.
5. Yes — Step 0 greps of GN2/GN3's signatures.
6. No conflict.
7. n/a.
8. Yes — the fake is imported from GN2's test file in the same copied directory, named.

## GN5 — the rules mutator
1. Yes — M1–M8 and the negative control.
2. Yes — `reddish fox, red` (whole-token vs substring); two samplers; a `LoraLoader` node; a token no encoder carries; a graph without a sampler; all-empty rules.
3. Yes — tokenise on commas and whitespace, every encoder, every LoRA node, every sampler, `RuleNeverFires` for a category that changed nothing.
4. Yes — reads `manifest.toml`'s `[mutate]`; `ValueError`/`FileNotFoundError` arms; `applied` shape; consumers GN6.
5. Yes — `grep -n 'manifest.toml\|lab' pkgs/comfy-worlds/init.sh`, `python3 -c "import tomllib"`.
6. No conflict.
7. n/a.
8. Yes.

## GN6 — comfy-mutate and its unit
1. Yes — M1–M10 (seed-ignored, dry-run-enqueues, wrong-kind, exit-0-on-no-likes, sampler-first-only, time-in-output, unit-wanted, conditionuser-dropped, readwritepaths-widened, protecthome-dropped).
2. Yes — no likes; a liked render without a graph; two samplers; the harness config with one world; equality on `ReadWritePaths` (a second path fails).
3. Yes — the newest liked render by a stated SQL; unit fields asserted by equality; `--comfy-url` validated by the loopback rule.
4. Yes — exit 0/2/3 with stderr texts; the unit's fields; the option and its default; consumers GN9, the drill.
5. Yes — `grep -ln 'comfy-worlds-eval' flake.nix checks/*.nix`, the existing units' hardening lines, the wrapper attrset.
6. No conflict — the dry-run output has no timestamp by contract (M6 proves it).
7. n/a.
8. Yes — `factory-brief <draft> GN6` reproduces the section whole (41,612 characters: Global Constraints, Assumptions, the section, the last probe; no GN7 text).

## GN7 — the probe through the broker, inside the namespace
1. Yes — M1–M11 (fall-back-to-direct, refusal-after-socket, ca-unchecked, hostname-allowed, public-allowed, proxy-ignored, one-direct-call-left, env-extra, containment-check, user-unit-kept, namespace-dropped).
2. Yes — a socket that raises; a hostname; a public literal; a recording fake proxy; a third `environment` entry; the user unit left beside the system one.
3. Yes — a literal loopback-or-private address rule, not a host list; "every fetch goes through `_open`"; list equality on the environment.
4. Yes — the four refusals before any socket, exit 2; the unit's namespace, user, environment, `ReadWritePaths` rule; consumers GN10's check, the drill.
5. Yes — `grep -n 'urlopen(' …`, the seven-line host grep, the unit and schedule greps, the output-directory grep, the stub's location; Assumption 10's nftables rule and the seatLane pattern are quoted with their commands.
6. No conflict.
7. n/a.
8. Yes.

## GN8 — engagement counts to Helm
1. Yes — M1–M10 (leak-prompt, leak-names, bounds-dropped, raise-on-error, reset-on-drop, no-periodic-thread, no-sigterm-handler, non-loopback-allowed, execstart-without-flag, previous-day-resent-forever).
2. Yes — 0/86400/-1/86401; likes on a named render; a closed port; a `day_fn` that changes; a subprocess under SIGTERM.
3. Yes — "exactly these five keys", loopback rule, every exception caught, cumulative snapshot resent (idempotent under Helm's keyed replace).
4. Yes — the body, the endpoint option and default, the drop line, the thread and the signal; consumers Helm's HM8, the drill's step 17.
5. Yes — Step 0 greps; the five names quoted from this repo's EV14 (the seat cannot read this repo; the literal is in the section).
6. No conflict.
7. n/a.
8. Yes.

## GN9 — the runbook and the drill
1. Yes — M1, M2 by `--self-test`; M3, M4 by the live drill (stated, with the Operator steps that kill them).
2. Yes — an empty `PATH` for the self-test arm.
3. Yes — steps read their inputs from the environment with `:?` refusals; helpers defined only if absent.
4. Yes — the script's exit code, `PASS`/`FAIL:` lines, the required variables; consumers the composed drill (70b).
5. Yes — the section and step counts by `grep -c`, the flag/helper idiom grep.
6. No conflict — shellcheck is the acceptance and the block quotes every variable.
7. n/a.
8. Yes — the new steps are literal shell in the section, helpers included.

## GN10 — the worlds on core
1. Yes — M1–M11 each naming the throw arm it trips; the negative control names the existing backup check's message.
2. Yes — two worlds (a shared port); a seventh host and a dropped host (equality both ways); an `inject` entry; a third environment entry; the runbook's port text and the rev digit.
3. Yes — "every `comfy-` user unit", "every world's ports distinct", "every world named in the runbook", list equality on the six hosts — rules over sets; the six-host `allow` is a security allowlist pinned exactly.
4. Yes — the check's inputs (`self.nixosConfigurations.core.config`, `flake.lock`, the runbook), its arms and messages; consumers `host-core`, `core-backup-wiring`, the drill.
5. Yes — Facts commands on `flake.nix`, `hosts/core/*`, `docs/runbooks/backup.md`, and the option set by `nix eval … --apply builtins.attrNames` after the lock.
6. No conflict — the runbook lines the check reads are written from the same `nix eval` values.
7. n/a.
8. Yes — the host file and the check are inlined verbatim; the seat re-measures option names.

## GN11 — the absorption's record
1. Yes — M1–M6; M6 killed by a probe only (no unused-entry rule), stated.
2. Yes — the duplicate-key counter (the repointed row must not re-read this repo's plans); `untracked_plans`; a typed heading in the record (G7).
3. Yes — `media/*` one glob; the media row's `plans` a glob matching nothing; every path resolves to one row.
4. Yes — validator exit 0, `check` empty, `json` shapes; consumers `subsystems-manifest`, the brief.
5. Yes — the Base commands (`git log --merges`, `git tag -l`, `git ls-files media | wc -l`), the manifest/repos/plan-status greps, PL6's row shape by `sed`.
6. No conflict.
7. n/a.
8. Yes — PL6's shape is quoted into the section (the 2026-09-12 erratum 2/8 fix), not referenced.

## GN12 — media absorbed into this flake
1. Yes — M1–M6; M1's lone-`.lock` variant killed by a probe (stated, r2 erratum 6); M4 by the two derivation probes.
2. Yes — the one real collision `lint`; an unrewritten `${self}` path; a dropped package; the media lock node left.
3. Yes — "every `${self}/<p>` gains `media/`", "every colliding name gains `media-`", an `assert` refusing any collision, "built from `nixpkgs-host`" proven by `drvPath` membership.
4. Yes — what each new file receives and exports; `nix eval` shapes; the 43b measurement's stop condition; consumers `core-media-wiring`, the drill, Platform's `pkgsHost`.
5. Yes — Step 0's counts (`${self}` occurrences, 21/5/3, the `comm` collision set, `pkgsHost` absent, the two pins).
6. No conflict — MAP is regenerated in the same commit and `lint` diffs it.
7. n/a.
8. Partly — the bodies are "moved verbatim" from `media/flake.nix`, a file the seat has (it is in its workspace after the landing act), with the rewrite rules stated; the attribute names are measured, not listed (the tree was unreadable here). The weakest section on row 3.

## Self-score (rubric §5.1), with reasons

| row | score | reason |
|---|---|---|
| 1 spec coverage | 3 | every §1–§6 item and every §5 question maps to a key, a question or a named out |
| 2 correct facts | 2 | every fact carries its command; the media facts are quotations from the record (Assumptions 18–28), not re-measurements — the seat re-measures (GN-A), but a judge with the media tree may find a drifted one |
| 3 self-contained sections | 2 | this-repo sections inline everything; media sections state signatures, DDL, tests and mutants but must measure unit and option names at Step 0; GN12 moves bodies it could not read |
| 4 TDD discipline | 3 | a red command and its expected output in every section; green by check name |
| 5 mutants and fixtures | 3 | one mutant per assertion, discriminating rows named, negative controls; the few probe-only kills are stated |
| 6 interfaces and error contracts | 2 | every enum arm and exit code where the code is new; GN10/GN12 depend on option names measured at Step 0 |
| 7 rules, not enumerations | 3 | value-based HTML rule, "every node" rules, set rules in the check, an `assert` for collisions; the driver guards exist and are cited as facts |
| 8 waves, touches, conflicts | 3 | derived by `tasks.py`'s own code three ways, pasted; conflicts run and sequenced; explicit touches |
| 9 invariant awareness | 3 | invariant 3 bound to GN7/GN10 with the nftables fact, invariant 6 to GN8; no `/var/lib/secrets`; `sudo` only in Operator |
| 10 operator steps and rollback | 3 | 24 numbered commands with acceptance, two predicted deltas, two rollback generations, the landing act with its falsifiers |
| 11 anticipation | 3 | dispatch lines and the dry run, the landing recipe, the relaunch, the claim, the questions, the deltas, fifteen named rows |
| 12 economy | 1 | 23.7k words: twelve sections with full mutant tables plus a verbatim Global Constraints block and 36 assumptions; nothing is an appendix, but it is long |
| 13 format and graph compliance | 3 | scratch-copy `check` empty, every probe parses, `check --draft` prints only the six MAP-currency lines it explains |
| 14 judgement calls | 3 | three questions with recommendation and default; seven applied recommendations with veto surfaces; three defects listed |

Total 37 of 42.
