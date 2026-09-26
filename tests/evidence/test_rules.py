"""Rules-inventory validator tests (plan 2026-09-09-program, KN1 / KN1b).

The validator reads docs/ledger/rules.toml — one [[rule]] row per rule from the
six sources — and checks the row shape, id uniqueness, the class/verdict enums,
and that a row's `source` line actually carries the rule's text.  `load_bearing`
rows whose `check` is empty are owed: reported as a count, never a failure.

KN1b adds the `--verbatim` arm: a row whose `text` is not byte-for-byte in its
`source` (modulo line wrapping) is refused, so a paraphrase can no longer pass
as a mere shared word.  Three ship-file guarantees ride with it: every named
source has at least one row, every repo-local source resolves in the sandbox
(so the checks are exercised, never silently skipped), and no row claims a
measurement the meta-planning packet never made.

EV17 adds the coverage pin: ``EXPECTED_PER_SOURCE`` and ``EXPECTED_IDS`` pin the
inventory per rule and per source, not by source presence alone.  The pin moves
only by a commit that also moves the ledger — the audit (Knowledge) changes both
deliberately.

KN14 adds the audit's ship-file guards (decision 54a): no surviving row keeps an
empty ``verdict``, and no row is both unchecked and unmeasured — the deletion
clause the charter makes of "a rule with no check and no measurement".  The
per-source and per-rule pins move with the audit in the same commit.

KN15 inverts the direction (decision 59a): the eight CLAUDE.md rows re-source
the ledger itself and render into CLAUDE.md's marked block, so the per-source
pin names ``docs/ledger/rules.toml`` where it named ``CLAUDE.md`` (the pin
moves with the ledger, as it did with the audit; the block's own drift tests
live in tests/evidence/test_rules_generate.py).
"""

import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve()
EVIDENCE = HERE.parents[2] / "pkgs" / "evidence"
sys.path.insert(0, str(EVIDENCE))

import rules

ROOT = HERE.parents[2]

# The coverage pin (KN1b's gate, MINOR-1): the inventory is pinned per rule, not
# per source.  These two literals mirror the ledger byte-for-byte, so deleting,
# adding or renaming any one [[rule]] row fails evidence-unit with a diff naming
# the id or the source whose count moved.  The pin moves only by a commit that
# also moves the ledger — the audit (Knowledge) changes both deliberately.
EXPECTED_PER_SOURCE = {
    "docs/brief.md": 11,
    # KN15 inverted the direction (decision 59a): the eight rows once sourced
    # CLAUDE.md:<line> now source the ledger itself — the ledger is the source
    # of record and CLAUDE.md's rules block is its rendering, drift-checked by
    # lint's `rules.py generate --check` (tests/evidence/test_rules_generate.py).
    "docs/ledger/rules.toml": 8,
    "docs/board/operator-model.md": 1,
    "tools/orchestrator-guard.sh": 6,
    "pkgs/dsh-openrouter/hook-guard.py": 6,
    # the harness AGENTS.md (~/flakes/dsh-harness/…) held four rows; the audit
    # (KN14, decision 54a) deleted all four — seat-bootstrap guidance, neither
    # checked nor measured — so that source legitimately holds zero rows now.
    "docs/runbooks/session.md": 4,
    "docs/board/policies.md": 2,
}

EXPECTED_IDS = [
    "R-conv-brief3-re-ratified",
    "R-conv-commit-subject",
    "R-conv-commit-trailers",
    "R-conv-lint-two-points",
    "R-conv-new-language-formatter",
    "R-conv-queue-derived",
    "R-guard-helm-control",
    "R-guard-host-rules",
    "R-guard-model-fail-closed",
    "R-guard-no-history-rewrite",
    "R-guard-no-mutating-systemctl",
    "R-guard-no-nixos-rebuild",
    "R-guard-no-sudo",
    "R-guard-plan-append-only",
    "R-guard-plan-write-tools",
    "R-guard-protected-paths",
    "R-guard-ritual-override",
    "R-guard-self-protect",
    "R-invariant-basket-tmpfs",
    "R-invariant-credential-plaintext",
    "R-invariant-egress-chokepoint",
    "R-invariant-no-promotion",
    "R-invariant-policy-nix",
    "R-invariant-publish-gate",
    "R-invariant-reproducible",
    "R-practice-brief8-no-secrets",
    "R-practice-brief8-pin-inputs",
    "R-practice-build-only",
    "R-practice-devshell-path",
    "R-practice-hardware-config-verbatim",
    "R-practice-home-readonly",
    "R-practice-privacy-first",
    "R-practice-statix-header",
    "R-practice-test-passed-gate",
    "R-ritual-file-commit-reviews",
    "R-ritual-heredoc-lesson",
    "R-ritual-stop-derived",
    "R-ritual-ten-steps",
]


def _counts_per_source(rows):
    counts = Counter()
    for r in rows:
        path, _line = rules._source_parts(str(r.get("source", "")))
        if path is None:
            continue
        key = "AGENTS.md" if path.endswith("AGENTS.md") else path
        counts[key] += 1
    return counts


def _row(**kw):
    base = {
        "id": "r-example",
        "text": "decrypted basket contents live only in tmpfs",
        "source": "docs/brief.md:68",
        "origin": "2026-09-02",
        "class": "invariant",
        "load_bearing": True,
        "measured": "UNMEASURED: phase-1 operator acceptance",
        "check": "",
        "verdict": "",
        "note": "",
    }
    base.update(kw)
    return base


def render(rows):
    lines = []
    for r in rows:
        lines.append("[[rule]]")
        lines.append(f'id = "{r["id"]}"')
        lines.append(f'text = """{r["text"]}"""')
        lines.append(f'source = "{r["source"]}"')
        lines.append(f'origin = "{r["origin"]}"')
        lines.append(f'class = "{r["class"]}"')
        lines.append("load_bearing = %s" % ("true" if r["load_bearing"] else "false"))
        lines.append(f'measured = """{r["measured"]}"""')
        lines.append(f'check = "{r["check"]}"')
        lines.append(f'verdict = "{r["verdict"]}"')
        lines.append(f'note = """{r.get("note", "")}"""')
    return "\n".join(lines) + "\n"


def write(tmp_path, rows):
    p = tmp_path / "rules.toml"
    p.write_text(render(rows))
    return p


def test_source_line_must_contain_the_rule_text(tmp_path):
    src = tmp_path / "brief.md"
    src.write_text("line one\nline two\nunrelated words here\n")
    rows = [
        _row(
            text="decrypted basket contents live only in tmpfs",
            source=f"{src}:3",
        )
    ]
    errs = rules.validate(rows, repo_root=tmp_path)
    assert any("source" in e and "line" in e for e in errs)


def test_verdict_must_be_in_enum(tmp_path):
    rows = [_row(verdict="maybe")]
    errs = rules.validate(rows, repo_root=tmp_path)
    assert any("verdict" in e for e in errs)


def test_ids_must_be_unique(tmp_path):
    rows = [_row(id="r-dup"), _row(id="r-dup")]
    errs = rules.validate(rows, repo_root=tmp_path)
    assert any("duplicate" in e for e in errs)


def test_class_must_be_in_enum(tmp_path):
    rows = [_row(**{"class": "custom"})]
    errs = rules.validate(rows, repo_root=tmp_path)
    assert any("class" in e for e in errs)


VERBATIM_SOURCE = (
    "Everything you do is build-only: never `sudo`, `nixos-rebuild`, "
    "`systemctl start/stop/restart`, or basket mount/teardown — the operator "
    "switches and runs the acceptance scripts.\n"
)


def test_verbatim_refuses_paraphrase(tmp_path):
    """A row whose text paraphrases its source (not byte-for-byte) is refused under --verbatim."""
    src = tmp_path / "CLAUDE.md"
    src.write_text(VERBATIM_SOURCE)
    rows = [
        _row(
            id="R-paraphrase",
            text="Everything is build-only: never sudo, nixos-rebuild, or systemctl.",
            source=f"{src}:1",
        )
    ]
    errs = rules.validate(rows, repo_root=tmp_path, verbatim=True)
    assert any("R-paraphrase" in e for e in errs), errs
    assert any("byte-for-byte" in e or "verbatim" in e for e in errs), errs


def test_verbatim_accepts_verbatim_text(tmp_path):
    """The source's own wording (modulo line wrap) passes byte-for-byte."""
    src = tmp_path / "CLAUDE.md"
    src.write_text(VERBATIM_SOURCE)
    text = (
        "Everything you do is build-only: never `sudo`, `nixos-rebuild`, "
        "`systemctl start/stop/restart`, or basket mount/teardown — the "
        "operator switches and runs the acceptance scripts."
    )
    rows = [_row(id="R-verbatim", text=text, source=f"{src}:1")]
    assert rules.validate(rows, repo_root=tmp_path, verbatim=True) == []


def test_verbatim_accepts_wrapped_source(tmp_path):
    """Line wrapping in the source file is tolerated; the words are what must match."""
    src = tmp_path / "brief.md"
    src.write_text(
        "1. Decrypted basket contents exist only for the lifetime of the agent that mounted them,\n"
        "   and only in tmpfs.\n"
    )
    rows = [
        _row(
            id="R-wrapped",
            text="Decrypted basket contents exist only for the lifetime of the agent that mounted them, and only in tmpfs.",
            source=f"{src}:1",
        )
    ]
    assert rules.validate(rows, repo_root=tmp_path, verbatim=True) == []


def test_shipped_inventory_validates(tmp_path):
    rows = rules.load(ROOT / "docs" / "ledger" / "rules.toml")
    assert rows, "the shipped inventory must not be empty"
    assert rules.validate(rows, repo_root=ROOT) == []
    # every text is byte-for-byte in its source (mutant A: a paraphrase breaks it)
    assert rules.validate(rows, repo_root=ROOT, verbatim=True) == []
    # every repo-local source must resolve here (mutant C: the skip itself fails).
    # The harness AGENTS.md lives outside the repo and is the one legitimate gap.
    unresolved = rules.unresolved_sources(rows, repo_root=ROOT)
    missing = [u for u in unresolved if "AGENTS.md" not in u]
    assert missing == [], f"repo-local sources must resolve in the sandbox: {missing}"


def test_owed_counts_only_load_bearing_rows_without_a_check(tmp_path):
    rows = [
        _row(id="r-bearing-checked", load_bearing=True, check="lint", text="x"),
        _row(id="r-bearing-unchecked", load_bearing=True, check="", text="x"),
        _row(id="r-not-bearing", load_bearing=False, check="", text="x"),
    ]
    assert rules.owed(rows) == 1


def _sources(rows):
    out = {}
    for r in rows:
        path, line = rules._source_parts(str(r.get("source", "")))
        if path is not None:
            out.setdefault(path, []).append(line)
    return out


def _brief_section_bounds():
    bounds = {}
    for i, line in enumerate((ROOT / "docs" / "brief.md").read_text().splitlines(), 1):
        m = re.match(r"^## (\d+)\.\s*", line)
        if m:
            bounds[int(m.group(1))] = i
    return bounds


def test_every_named_source_has_a_row():
    """Each named source has at least one row; brief §3 and §8 are both covered."""
    rows = rules.load(ROOT / "docs" / "ledger" / "rules.toml")
    sources = _sources(rows)
    bounds = _brief_section_bounds()

    def has_line(path, lo, hi):
        return any(lo <= ln <= hi for ln in sources.get(path, []))

    assert has_line("docs/brief.md", bounds[3], bounds[4] - 1), (
        "brief §3 must be inventoried"
    )
    assert has_line("docs/brief.md", bounds[8], bounds[9] - 1), (
        "brief §8 must be inventoried"
    )
    for p in (
        # KN15: the rows once sourced CLAUDE.md now source the ledger itself;
        # CLAUDE.md's rules block is the generated rendering of these rows.
        "docs/ledger/rules.toml",
        "tools/orchestrator-guard.sh",
        "pkgs/dsh-openrouter/hook-guard.py",
        "docs/board/policies.md",
        "docs/board/operator-model.md",
        "docs/runbooks/session.md",
    ):
        assert p in sources, f"{p} must have at least one row"
    # The harness AGENTS.md once had to be inventoried (four rows); the audit
    # (KN14, decision 54a) deleted all four — seat-bootstrap guidance, neither
    # checked nor measured — so that source holds zero rows by design now and
    # no longer asserts its presence.  Its rows are gone, not forgotten: the
    # deletion is the commit this test moved with.


def test_inventory_pins_the_count_per_source():
    """Every source's rule count is pinned, and the total is pinned independently."""
    rows = rules.load(ROOT / "docs" / "ledger" / "rules.toml")
    counts = _counts_per_source(rows)
    assert counts == EXPECTED_PER_SOURCE
    assert sum(counts.values()) == 38


def test_every_rule_id_is_pinned():
    """The sorted id list equals the pinned EXPECTED_IDS — one id per [[rule]] row."""
    rows = rules.load(ROOT / "docs" / "ledger" / "rules.toml")
    assert sorted(r["id"] for r in rows) == EXPECTED_IDS


def test_no_unmeasured_measurement():
    """No row claims a measurement the meta-planning packet never made (mutant D)."""
    rows = rules.load(ROOT / "docs" / "ledger" / "rules.toml")
    devshell = next(r for r in rows if r["id"] == "R-practice-devshell-path")
    measured = devshell["measured"]
    # §9.1 measured only jq and python3 — never bats.
    assert "command -v jq python3 bats" not in measured
    assert "`command -v bats`" not in measured
    assert "`command -v jq`" in measured
    assert "`command -v python3`" in measured


# --- KN14: the audit's verdicts (plan 2026-09-11-knowledge, decision 54a) ---


def _unchecked_unmeasured(rows):
    """Ids of rows with no check and no measurement — 54a's deletion population."""
    return [
        str(r.get("id", "<no id>"))
        for r in rows
        if not (r.get("check") or "").strip()
        and str(r.get("measured", "")).startswith("UNMEASURED")
    ]


def test_every_row_has_a_verdict():
    """KN14 Interface 3: after the audit, no shipped row keeps an empty verdict."""
    rows = rules.load(ROOT / "docs" / "ledger" / "rules.toml")
    empty = [str(r.get("id", "<no id>")) for r in rows if r.get("verdict", "") == ""]
    assert not empty, f"{empty[0]} has no verdict"


def test_no_row_is_unchecked_and_unmeasured():
    """KN14 Interface 4: no shipped row is both unchecked and unmeasured (54a)."""
    rows = rules.load(ROOT / "docs" / "ledger" / "rules.toml")
    bad = _unchecked_unmeasured(rows)
    assert not bad, f"{len(bad)} rows: {', '.join(bad)}"


def test_unchecked_unmeasured_discriminates_on_the_intersection():
    """M5 control: the Interface-4 test discriminates on exactly the intersection.

    A row with no check that *was* measured and a row with a check that was
    never measured both stay green; a third row that is neither checked nor
    measured fails.  The shipped-ledger test above therefore flags the
    intersection alone, not either half by itself.
    """
    fixture = [
        _row(
            id="R-ctl-measured-unchecked",
            check="",
            measured="`command -v jq` → /run/current-system/sw/bin/jq",
        ),
        _row(
            id="R-ctl-unmeasured-checked",
            check="lint",
            measured="UNMEASURED: guidance, not enforced by a named check",
        ),
    ]
    assert _unchecked_unmeasured(fixture) == []
    third = _row(
        id="R-ctl-both",
        check="",
        measured="UNMEASURED: not enforced by a named check",
    )
    assert _unchecked_unmeasured(fixture + [third]) == ["R-ctl-both"]
