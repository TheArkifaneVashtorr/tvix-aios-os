"""Rules generate tests (plan 2026-09-11-knowledge, KN15).

`rules.py generate` renders the ledger into a marked block of a target file:
every row whose `origin_target` matches is one bullet, in ledger order, `text`
verbatim, between `<!-- rules:begin -->` and `<!-- rules:end -->` — and
nothing else in the file moves. `--check` exits 0 when the block is current
and 1 with a diff naming the file when not, which is the verb `lint` runs, so
hand-edited drift in either direction (file or ledger) fails the build.

The fixture uses two rows whose texts differ (so render order is observable)
plus one unmarked row (so non-rendering is observable), and a file with prose
before and after the markers (so a splice that eats prose is caught).
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
EVIDENCE = HERE.parents[2] / "pkgs" / "evidence"
sys.path.insert(0, str(EVIDENCE))

import rules

ROOT = HERE.parents[2]

ROW = (
    "[[rule]]\n"
    'id = "R-{i}"\n'
    'text = "{t}"\n'
    'source = "docs/ledger/rules.toml:3"\n'
    'origin = "2026-09-14"\n'
    'class = "practice"\n'
    "load_bearing = false\n"
    'measured = "fixture"\n'
    'check = ""\n'
    'verdict = "keep"\n'
    "{extra}\n"
)
LEDGER = (
    ROW.format(i="a", t="Never sudo.", extra='origin_target = "claude"')
    + ROW.format(i="b", t="Red first.", extra='origin_target = "claude"')
    + ROW.format(i="c", t="Unrendered.", extra="")
)
FILE = (
    "# Title\n"
    "prose before\n"
    "<!-- rules:begin -->\n"
    "stale\n"
    "<!-- rules:end -->\n"
    "prose after\n"
)


def _fixture(tmp_path, body=FILE):
    (tmp_path / "rules.toml").write_text(LEDGER)
    f = tmp_path / "CLAUDE.md"
    f.write_text(body)
    return f, rules.load(tmp_path / "rules.toml")


def test_generate_replaces_only_the_block(tmp_path):
    f, rows = _fixture(tmp_path)
    assert rules.generate(f, rows, "claude") == 0
    t = f.read_text()
    assert t.startswith("# Title\nprose before\n")
    assert t.endswith("prose after\n")


def test_rows_render_in_ledger_order_verbatim(tmp_path):
    f, rows = _fixture(tmp_path)
    rules.generate(f, rows, "claude")
    assert (
        "<!-- rules:begin -->\n- Never sudo.\n- Red first.\n<!-- rules:end -->"
        in f.read_text()
    )


def test_unmarked_rows_are_not_rendered(tmp_path):
    f, rows = _fixture(tmp_path)
    rules.generate(f, rows, "claude")
    assert "Unrendered." not in f.read_text()


def test_check_is_0_when_current_and_1_with_a_diff_when_not(tmp_path, capsys):
    f, rows = _fixture(tmp_path)
    rules.generate(f, rows, "claude")
    assert rules.generate(f, rows, "claude", check=True) == 0
    f.write_text(f.read_text().replace("- Red first.\n", ""))
    assert rules.generate(f, rows, "claude", check=True) == 1
    assert "CLAUDE.md" in capsys.readouterr().out


def test_missing_markers_and_missing_file_exit_1(tmp_path, capsys):
    f, rows = _fixture(tmp_path, body="no markers\n")
    assert rules.generate(f, rows, "claude", check=True) == 1
    assert "missing markers" in capsys.readouterr().err
    assert rules.generate(tmp_path / "absent.md", rows, "claude") == 1


def test_deleting_a_rendered_row_turns_check_red(tmp_path):
    f, rows = _fixture(tmp_path)
    rules.generate(f, rows, "claude")
    assert rules.generate(f, rows[1:], "claude", check=True) == 1


def test_validate_refuses_an_origin_target_outside_targets(tmp_path):
    """Interface 6: a row whose origin_target is not in TARGETS is a validate
    error naming the id (KN16 adds targets; a typo must not silently unrender
    a rule)."""
    _f, rows = _fixture(tmp_path)
    rogue = dict(rows[0])
    rogue["id"] = "R-rogue"
    rogue["origin_target"] = "agents"
    errs = rules.validate([rogue], repo_root=tmp_path)
    assert any("R-rogue" in e and "origin_target" in e for e in errs), errs


def test_zero_marked_rows_render_an_empty_block_that_stays_current(tmp_path):
    """Interface 6: zero rows for a target is an empty block between the
    markers, and --check compares exactly that — current, not an error."""
    f, rows = _fixture(tmp_path)
    assert rules.generate(f, rows[2:], "claude") == 0  # only the unmarked row
    assert "<!-- rules:begin -->\n<!-- rules:end -->" in f.read_text()
    assert rules.generate(f, rows[2:], "claude", check=True) == 0


def test_shipped_claude_md_is_current():
    assert (
        rules.generate(
            ROOT / "CLAUDE.md",
            rules.load(ROOT / "docs/ledger/rules.toml"),
            "claude",
            check=True,
        )
        == 0
    )
