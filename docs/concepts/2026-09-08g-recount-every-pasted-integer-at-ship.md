# Concept 2026-09-08g — every pasted integer in a plan (test counts, file counts, row counts) needs a live re-run at Ship, not just its commands

**Class:** planning-process fix (a rubric/process concept, no spec item of its
own).

**Status:** proposed 2026-09-08, from the Helm Home sub-project 1 judging
round (`docs/reviews/plan-judgements/2026-09-08-helm-home-1.md`, criterion 2
across all three judges) and observed while shipping
`docs/superpowers/plans/2026-09-08-helm-home-1.md`.

**Origin:** the draft's Assumption 4 and HH2's own "Facts (planning time)"
line both stated `grep -c 'def test_' tests/helm/test_serve.py` → `61`; a live
re-run at Ship (`nix develop -c grep -c 'def test_' tests/helm/test_serve.py`,
confirmed twice) returned `62` — and the same 62 was already true at the
packet's own HEAD (`git show 0c8eeec:tests/helm/test_serve.py | grep -c
'def test_'` → `62`), so this was not drift between packet and Ship, it was a
miscount at drafting time that three judging passes (two Sonnet, one Opus)
each caught independently. The same packet carried two more wrong integers of
the identical shape: `hosts/core/default.nix`'s `imports` list was stated as
nine files when it is ten (`./telemetry.nix` was left uncounted), and the
plan's own "graph on the draft" section stated the cross-plan `conflicts` row
count as 16 when a live re-run on a scratch copy printed 17 (the seventeenth
row, `CR4b × SP5: flake.nix ~ flake.nix`, touches neither plan's own keys, so
it is easy to have skipped while eyeballing the output). All three errors sit
in the same class: a small integer, cited as evidence, computed once by
counting a command's output by eye rather than by piping it through `wc -l`
or reading the tool's own count. Unlike a stale filename or a moved line
number, a miscounted integer looks exactly as plausible as the correct one to
a reader who does not re-run the command — it fails only re-verification, not
inspection.

**Idea:** distinguish two different reliability problems a plan's "Facts
(planning time)" citations can have. Concept 2026-09-08f already covers the
first — a fact is true at packet time but the underlying *state* moves before
Ship (a plan's status, a chain's key, a tree that gained commits). This
concept covers a different, narrower failure: the fact was *never* true,
because the count was produced by running a command and reading its output
inexactly (by eye, or by a `grep -c` invocation whose exact scope differs
subtly from what the surrounding prose describes) rather than by piping the
same command through a counting tool and using that number verbatim. The fix
is not "re-run before Ship" (2026-09-08f's fix) but "when citing a count,
paste the counting command's own output, not a number typed after reading
it" — e.g. `grep -c 'def test_' tests/helm/test_serve.py` piped to a single
integer stdout line, copied verbatim into the Assumption, rather than
eyeballing a multi-page grep listing and writing down a tally. The same
discipline applies to file-list counts (`ls | wc -l` rather than counting an
`imports = [ ... ]` block by eye) and to tool-output row counts (`| wc -l`
rather than counting printed lines in a terminal scrollback). A judge or a
Ship-phase re-run can always catch these after the fact — as happened here,
at some cost in review rounds — but the cheaper fix is to never hand-tally a
count that a pipe could produce exactly.

**Payoff:** removes an entire class of criterion-2 findings (three of them in
this single plan, independently found by all three judges) before judging
ever runs, saving a judging round's worth of scrutiny on facts that are
mechanical to get right the first time. It also means a plan's Tests-table
arithmetic (e.g. "the twelve `test_validate_*` plus ... equals 61") is
trustworthy on first read, rather than needing the reader to independently
recompute the total before trusting the deletions it enumerates.

**Dependencies:** none — a drafting-discipline note for whichever phase of the
`plan` skill assembles "Facts (planning time)" / Assumptions blocks, not a
code change.

**Earliest landing:** immediate — a habit for the next plan's Facts-gathering
step (pipe every cited count through a counting tool, paste its literal
output). If pasted-but-wrong integers keep recurring after this note exists,
promote it to an explicit checklist line in the planning skill's packet
assembly instructions, the way 2026-09-08f's Ship-checklist idea was proposed
for cross-plan sequencing rules.
