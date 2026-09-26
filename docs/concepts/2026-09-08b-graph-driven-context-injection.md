# Concept 2026-09-08b — graph-driven context injection into the seat brief, then selection over injection policies

**Class:** driver/harness feature (a `factory-brief` step), with a measurement
layer above it (a `report harness --split` arm per policy).

**Status:** proposed 2026-09-08, from the operator's question during the
SB5/SB6 row-3 reading ("an evolutionary setup with prompt/context injection
mutations using code graphs"; Temporal and PostgreSQL asked about in the same
breath and set aside — see Dependencies).

**Origin:** rubric row 3 says the seat brief alone must land the task — paths,
signatures, code or test bodies, no "read X and copy its shape". Today the
orchestrator satisfies it by hand: it runs `factory-brief <plan> <KEY>`, reads
the output with the rest of the plan hidden, and pastes into a `<KEY>b`
section every fact a seat would otherwise invent, each with the command that
measured it. SB5b and SB6b (2026-09-08) are two such sections; the readers
that gathered their facts followed one recipe every time: the section's
`touches` → the symbols in those files → their definitions, callers and the
tests that cover them → line-numbered pastes. That recipe is a graph query.

**Idea:** (1) a code graph over the tree — tree-sitter for bash, python and
nix, file nodes from `touches`, symbol nodes (functions, bats `@test` names,
nix attribute paths, systemd option paths), edges for definition, call,
test-covers and imports; (2) `factory-brief --facts` walks it from the
section's `touches` and appends a generated `## Facts (measured)` block —
each entry a `sed -n 'a,bp'`/`grep -n` paste with its command, exactly the
shape the hand-written `<KEY>b` sections use — so the section's prose stays
the contract and the facts stay current at launch time (a wrong-fact class
that today costs a gate); (3) the injection *policy* (how many neighbours,
tests before code, callers included or not, line numbers on or off, the
budget in lines) is a named row, and `report harness --split` measures each
policy change the way it measures every other harness change; (4) only then
the evolutionary layer: mutate the policy, select on outcomes. Its enabling
piece is a fitness cheaper than an Opus gate (~$6, ~30 tasks a week ⇒ n ≈ 5
per arm per week at most): the driver's own `checks_verified`, a local
mutant-kill proxy, the DeepSeek `plan_defect` classifier (the 2026-09-08
audit: 44/66 six-way, 50/66 binary — noisy but free).

**Payoff:** the row-3 work leaves the orchestrator's hands (two hours of
Fable reading per plan today); wrong-fact rejections (10 of 55 plan-caused
this week) drop because facts are measured at launch, not at planning; and
the policy becomes a measured dial rather than a style.

**Dependencies:** the seat-harness mechanisms on main (SH1–SH6: `report
harness --split`, `touches` enforcement); the seat-driver plan's class
derivation (SD2: `touches` → class is the same walk's first step); a parser
package in the devShell (tree-sitter grammars for bash, python, nix — a new
language means its formatter and linter land in the same task). Not Temporal:
the durability class it would buy (chains dying with a session) is what SD6's
spool and SD7's drive mode close with systemd; revisit only if the unattended
drive seat's stall count per week stays above a handful. Not PostgreSQL: the
store stays files (SQLite in the store directory if queries ever hurt).

**Earliest landing:** a spec after the seat-as-driver chain (SB5b, SB6b,
SD1–SD11), beside the media specialisation; the graph and the `--facts` step
are one S-to-M code task each, the measurement row a docs task, the
evolutionary layer its own spec once a proxy fitness has been measured
against five real gates.
