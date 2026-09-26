"""The review-migration script (plan 2026-09-06-telemetry-store-1, T3).

`migrate_reviews <repo> [--check]` walks `<repo>/docs/reviews/*opus-review*.md`
in name order and completes each file's block: a blockless REVIEW_RE H1 gets a
block prepended (`reviewer: opus`, the parsed `majors`/`minors` counts, the two
mutation keys only when they parse); an existing block has its missing keys
appended before the closing `---`. A legacy H1 (neither `---` nor REVIEW_RE) is
skipped and counted. The script never writes `plan_defect` or
`plan_defect_secondary`.
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve()
FIXTURES = HERE.parent / "fixtures" / "reviews-migrate"

FMF_LEDGER = "[meta]\nfront_matter_from = 2026-09-07\n"


def _load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "migrate_reviews.py",
        pathlib.Path("pkgs/evidence/migrate_reviews.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("migrate_reviews", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_reviews"] = mod
    spec.loader.exec_module(mod)
    return mod, src


mig, SRC = _load()
import tasks as tk

# Fixture basename -> corpus basename under docs/reviews/ (all dated before
# front_matter_from so `tasks.check` never requires plan_defect).
CORPUS = {
    "h1-markers.md": "2026-09-05-opus-review-r1-K1.md",
    "h1-no-markers.md": "2026-09-05-opus-review-r2-K2.md",
    "block-five-keys.md": "2026-09-05-opus-review-r3-K3.md",
    "legacy-h1.md": "2026-09-05-opus-review-r4-K4.md",
    "migrated.md": "2026-09-05-opus-review-r5-K5.md",
    "majors-none.md": "2026-09-05-opus-review-r6-K6.md",
}


def _make_repo(root, fixture_names):
    """Create `root/repo/docs/reviews/` populated from the named fixtures."""
    repo = root / "repo"
    (repo / "docs" / "reviews").mkdir(parents=True, exist_ok=True)
    for fn in fixture_names:
        (repo / "docs" / "reviews" / CORPUS[fn]).write_text((FIXTURES / fn).read_text())
    return repo


def _graph(repo):
    return {
        "generated": "t",
        "repos": [
            {
                "name": "repo",
                "path": str(repo),
                "tasks": [],
                "legacy": [],
                "untracked_plans": [],
            }
        ],
    }


def _after_close(text: bytes) -> bytes:
    """The bytes after the last ``---`` fence line (the block's closing fence),
    the whole text when no fence is present."""
    fences = list(re.finditer(rb"(?m)^---[ \t]*\n", text))
    if not fences:
        return text
    return text[fences[-1].end() :]


def test_migrate_counts_markers_and_mutations(tmp_path, capsys):
    # A blockless REVIEW_RE H1 gets a block prepended with reviewer, the parsed
    # counts (MAJOR markers, MINOR markers) and the mutation pair; the H1 is
    # unchanged. An indented marker and a lowercase "major" count too. Mutants:
    # count inline mentions -> the "six minors" sentence inflates minors; swap
    # killed/total -> 12/14 flips; anchor at column 0 -> the indented minor
    # drops; drop re.I -> the lowercase major drops.
    repo = _make_repo(tmp_path, ["h1-markers.md"])
    d = repo / "docs" / "reviews"
    (d / "2026-09-05-opus-review-r9-K9.md").write_text(
        "# Opus gate \u2014 seat run r9, task K9 \u2014 APPROVED\n\n"
        "  - MINOR 4: indented\n"
        "**major (reject)** x\n"
    )
    assert mig.main([str(repo)]) == 0
    base = (d / "2026-09-05-opus-review-r1-K1.md").read_text()
    assert base.splitlines()[1:7] == [
        "reviewer: opus",
        "majors: 2",
        "minors: 3",
        "mutants_total: 14",
        "mutants_killed: 12",
        "---",
    ]
    assert (
        base.splitlines()[7]
        == "# Opus gate \u2014 seat run r1, task K1 \u2014 APPROVED"
    )
    extra = (d / "2026-09-05-opus-review-r9-K9.md").read_text()
    assert "majors: 1\n" in extra
    assert "minors: 1\n" in extra


def test_migrate_null_and_none_counts(tmp_path):
    # No markers and no "none" heading -> null; a "## Majors" heading followed
    # by "none" and a "### Minors" heading followed by "None." -> 0 each (the
    # heading level is any 1-6 hashes, case-insensitive). Mutant: write 0 for
    # no markers -> the null assertion fails; restrict the heading to "##" or
    # drop re.I -> the "minors: 0"/"majors: 0" assertions fail.
    repo = _make_repo(tmp_path, ["h1-no-markers.md", "majors-none.md"])
    assert mig.main([str(repo)]) == 0
    no_markers = (
        repo / "docs" / "reviews" / "2026-09-05-opus-review-r2-K2.md"
    ).read_text()
    assert "majors: null\n" in no_markers
    assert "minors: null\n" in no_markers
    assert "mutants_" not in no_markers  # no mutation form -> no mutant keys
    majors_none = (
        repo / "docs" / "reviews" / "2026-09-05-opus-review-r6-K6.md"
    ).read_text()
    assert "majors: 0\n" in majors_none
    assert "minors: 0\n" in majors_none


def test_migrate_block_five_keys_appends(tmp_path):
    # An existing five-key block keeps its keys in place and only gains the
    # missing reviewer/majors/minors before the closing fence. plan_defect is
    # never added to a migrated blockless file. Mutants: overwrite -> the five
    # keys are no longer "in place"; add plan_defect: none -> the h1-markers
    # block gains a plan_defect line.
    repo = _make_repo(tmp_path, ["block-five-keys.md", "h1-markers.md"])
    assert mig.main([str(repo)]) == 0
    five = (repo / "docs" / "reviews" / "2026-09-05-opus-review-r3-K3.md").read_text()
    assert five.splitlines()[1:9] == [
        "plan_defect: vacuous",
        "plan_defect_secondary: missing-case",
        "mutants_total: 4",
        "mutants_killed: 3",
        "mutants_outside_named: 1",
        "reviewer: opus",
        "majors: null",
        "minors: null",
    ]
    markers = (
        repo / "docs" / "reviews" / "2026-09-05-opus-review-r1-K1.md"
    ).read_text()
    assert "plan_defect" not in markers


def test_migrate_skips_legacy_h1(tmp_path, capsys):
    # A legacy H1 is left byte-for-byte and counted. Mutant: migrate it -> the
    # "skipped legacy 1" summary and the byte-identity assertion both fail.
    repo = _make_repo(tmp_path, ["legacy-h1.md"])
    assert mig.main([str(repo)]) == 0
    assert "skipped legacy 1" in capsys.readouterr().out
    text = (repo / "docs" / "reviews" / "2026-09-05-opus-review-r4-K4.md").read_text()
    assert text == (FIXTURES / "legacy-h1.md").read_text()


def test_migrate_idempotent_and_check(tmp_path, capsys):
    # A second run is byte-identical and --check exits 0; --check on an
    # unmigrated corpus exits 1, lists the files, and writes nothing. Mutants:
    # restamp -> the byte comparison fails; write under --check -> the fresh
    # files change.
    fixtures = [
        "h1-markers.md",
        "h1-no-markers.md",
        "block-five-keys.md",
        "migrated.md",
        "majors-none.md",
        "legacy-h1.md",
    ]
    repo = _make_repo(tmp_path, fixtures)
    d = repo / "docs" / "reviews"
    original = {fn: (FIXTURES / fn).read_bytes() for fn in fixtures}
    assert mig.main([str(repo)]) == 0
    # The body (every byte after the closing `---`) is identical to the
    # original fixture, the trailing newline included; a blocked fixture grows
    # by exactly the added key lines. Mutant: rejoin through
    # "\n".join(splitlines()) -> the trailing newline is dropped and both
    # assertions go red.
    for fn in fixtures:
        migrated = (d / CORPUS[fn]).read_bytes()
        assert _after_close(migrated) == _after_close(original[fn]), fn
    blocked_orig = original["block-five-keys.md"]
    blocked_mig = (d / CORPUS["block-five-keys.md"]).read_bytes()
    assert len(blocked_mig) - len(blocked_orig) == len(
        b"reviewer: opus\nmajors: null\nminors: null\n"
    )

    before = {p.name: p.read_bytes() for p in d.glob("*.md")}
    assert mig.main([str(repo)]) == 0
    for p in d.glob("*.md"):
        assert p.read_bytes() == before[p.name]
    assert mig.main([str(repo), "--check"]) == 0

    fresh = _make_repo(tmp_path / "b", ["h1-markers.md", "h1-no-markers.md"])
    fresh_bytes = {
        p.name: p.read_bytes() for p in (fresh / "docs" / "reviews").glob("*.md")
    }
    assert mig.main([str(fresh), "--check"]) == 1
    out = capsys.readouterr().out
    assert "would change: docs/reviews/2026-09-05-opus-review-r1-K1.md" in out
    for p in (fresh / "docs" / "reviews").glob("*.md"):
        assert p.read_bytes() == fresh_bytes[p.name]


def test_migrated_corpus_passes_tasks_check(tmp_path):
    # After a run, `tasks.check` over the fixture repo is silent — nothing the
    # migration writes violates the gate lint (a mutant that e.g. breaks a key
    # rule would surface an error here).
    repo = _make_repo(
        tmp_path,
        [
            "h1-markers.md",
            "h1-no-markers.md",
            "block-five-keys.md",
            "migrated.md",
            "majors-none.md",
            "legacy-h1.md",
        ],
    )
    (repo / "docs" / "ledger").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "ledger" / "plan-defects.toml").write_text(FMF_LEDGER)
    assert mig.main([str(repo)]) == 0
    errs = tk.check(_graph(repo))
    assert errs == []
