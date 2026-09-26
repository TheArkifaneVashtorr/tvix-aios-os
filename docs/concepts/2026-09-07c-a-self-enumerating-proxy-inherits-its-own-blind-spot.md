# Concept 2026-09-07c — a self-enumerating proxy inherits its own blind spot

**Class:** testing/review rule (a sharpening in the spirit of
`docs/concepts/2026-09-07a-a-named-proof-shape-is-not-a-mutant.md` and
`docs/concepts/2026-09-07b-a-reused-mechanism-with-no-producer-is-a-forward-reference.md`).

**Status:** proposed 2026-09-07, from the seat-harness-redesign re-plan
(SH3r, `docs/superpowers/plans/2026-09-07-seat-harness-redesign.md`), drafted
against the judge panel that scored it
(`docs/reviews/plan-judgements/2026-09-07-seat-harness-SH3r.md`).

**Origin:** SH3's chain failed twice on the same shape of gap: a hand-typed
list of "every site that consumes a path list without expanding it" that was
one spelling short each time (SH3: no fixture put a glob in a commit *body*;
SH3b: no fixture put one in a *path*). SH3r's fix does not extend the list —
it replaces the list with a grep,
`grep -nE 'for [A-Za-z_][A-Za-z0-9_]* in \$' tools/factory/seat/factory-lib.sh
tools/factory/seat/factory-task tools/factory/seat/factory-commit-msg.sh`,
asserted as its own numbered row (row 24: zero hits, exit 1) so that a site
added later and left unguarded turns the proxy itself red, not just the
feature it was meant to police. Row 24's own text names the residual gap:
"a consumer written another way is caught by rows 17–22, not here" — the grep
only recognizes one syntactic shape (`for x in $y`), so a loop written as
`while … <<<"$y"` gone wrong in some other fashion, or a consumer added in a
fourth script never named in the grep's argument list, would pass row 24
clean while still being wrong.

**Idea:** when a hand-enumerated list keeps drifting one item short, the fix
worth reaching for is not a longer list but turning the enumeration itself
into an assertion — a command that finds every site matching the *shape* of
the bug, run as a test row, so a new site inherits the check by construction
rather than by someone remembering to add a row. This upgrades the proxy from
"a list a human must keep current" to "a grep a human must keep *matching*,"
and the second failure mode is falsifiable in a way the first is not: the
grep's own blind spot (the syntactic shapes and files it does not cover) is
stateable as one sentence and can be pointed at directly, instead of being an
unknown unknown living in someone's memory of "sites I thought of." The
generalizable rule: any time a plan or review says "here is the list of
places this applies" for a *structural* property (a shape a `grep`, `ast`
walk, or lint rule can recognize), prefer asserting the finder as a row over
asserting the list — and require the row's own commentary to name what
syntactic shape or file scope the finder does *not* reach, exactly as SH3r's
row 24 does for the `for x in $y` shape and its three-file argument list.

**Payoff:** turns a recurring class of "we found one more site" rejections
into a single generalizable review question: for a hand-enumerated
"everywhere this applies" list, is there a mechanical finder for the shape,
and if so, why isn't the finder itself the test? Where a finder isn't
possible (the property is semantic, not syntactic), the plan should say so
explicitly rather than leave the list looking exhaustive.

**Dependencies:** none landed; a natural home is the same judge rubric slot
as concept 2026-09-07b (rubric row 6, or wherever "boundaries stated as rules
not enumerations" is scored — SH3r's own panel already rewarded this move
under exactly that heading in reasons 7/6/7 of judges 1–3).

**Earliest landing:** next planning-agent judge-prompt revision; until then,
apply it by hand: when a re-plan or fix round is triggered by "the
enumeration was one item short," check whether the missing category is
syntactically recognizable, and if so ask for the finder-as-test move before
accepting another hand-typed row.
