import datetime as dt
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "pkgs" / "evidence"))

import patches


def write(tmp_path, text, *files):
    p = tmp_path / "patches.toml"
    p.write_text(text)
    for f, content in files:
        fp = tmp_path / f
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
    return p


ONE = """[[patch]]
file = "patches/dsh/0001-fix.patch"
package = "dsh"
reason = "x"
upstream = "local"
added = 2026-09-15
review_by = 2026-10-15
added_in = "abc1234"
"""


def test_empty_ledger_passes(tmp_path):
    rows = patches.load(write(tmp_path, "# header only\n"))
    assert rows == []
    assert patches.validate(rows, root=tmp_path) == []
    assert patches.validate(rows, today=dt.date(2026, 9, 15), root=tmp_path) == []


def test_repo_patches_ledger_is_empty_and_valid():
    rows = patches.load(ROOT / "docs" / "ledger" / "patches.toml")
    assert rows == []
    assert patches.validate(rows, root=ROOT) == []


def test_missing_file_refused(tmp_path):
    rows = patches.load(write(tmp_path, ONE))
    errs = patches.validate(rows, root=tmp_path)
    assert any("dsh" in e and "file does not exist" in e for e in errs)


def test_duplicate_number_refused(tmp_path):
    text = (
        ONE
        + """
[[patch]]
file = "patches/dsh/0001-other.patch"
package = "dsh"
reason = "y"
upstream = "local"
added = 2026-09-15
review_by = 2026-10-15
added_in = "abc1234"
"""
    )
    p = write(
        tmp_path,
        text,
        ("patches/dsh/0001-fix.patch", "x"),
        ("patches/dsh/0001-other.patch", "y"),
    )
    rows = patches.load(p)
    errs = patches.validate(rows, root=tmp_path)
    assert any("dsh" in e and "duplicate" in e and "0001" in e for e in errs)


def test_expired_review_by_refused(tmp_path):
    p = write(tmp_path, ONE, ("patches/dsh/0001-fix.patch", "x"))
    rows = patches.load(p)
    errs = patches.validate(rows, today=dt.date(2026, 10, 16), root=tmp_path)
    assert any("review_by" in e and "past" in e and "2026-10-15" in e for e in errs)
    not_stale = patches.validate(rows, today=dt.date(2026, 10, 14), root=tmp_path)
    assert not any("past" in e for e in not_stale)
    no_today = patches.validate(rows, root=tmp_path)
    assert not any("past" in e for e in no_today)


def test_no_recipe_refused(tmp_path):
    p = write(tmp_path, ONE, ("patches/dsh/0001-fix.patch", "x"))
    rows = patches.load(p)
    errs = patches.validate(rows, root=tmp_path)
    assert any("no apply recipe for dsh" in e for e in errs)


def test_missing_field_refused(tmp_path):
    bad = ONE.replace('reason = "x"\n', "")
    rows = patches.load(write(tmp_path, bad, ("patches/dsh/0001-fix.patch", "x")))
    errs = patches.validate(rows, root=tmp_path)
    assert any("dsh" in e and "missing reason" in e for e in errs)


def test_bad_upstream_refused(tmp_path):
    bad = ONE.replace('upstream = "local"', 'upstream = "bogus"')
    rows = patches.load(write(tmp_path, bad, ("patches/dsh/0001-fix.patch", "x")))
    errs = patches.validate(rows, root=tmp_path)
    assert any("upstream must be one of" in e for e in errs)


def test_bad_number_refused(tmp_path):
    bad = ONE.replace("0001-fix.patch", "fix.patch")
    rows = patches.load(write(tmp_path, bad, ("patches/dsh/fix.patch", "x")))
    errs = patches.validate(rows, root=tmp_path)
    assert any("numbered" in e for e in errs)


def test_dates_must_be_toml_dates(tmp_path):
    bad = ONE.replace("added = 2026-09-15", 'added = "not-a-date"').replace(
        "review_by = 2026-10-15", 'review_by = "not-a-date"'
    )
    rows = patches.load(write(tmp_path, bad, ("patches/dsh/0001-fix.patch", "x")))
    errs = patches.validate(rows, root=tmp_path)
    assert any("added must be a TOML date" in e for e in errs)
    assert any("review_by must be a TOML date" in e for e in errs)
