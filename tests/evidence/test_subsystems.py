"""Subsystem manifest tests (PR1, plan 2026-09-09-program).

Every refusal below has a fixture that passes every *other* rule, so the
discriminating row of the manifest validator is the one rule the fixture
breaks. `validate` and `render` are the module's unit-level entry points:
`validate(text, files)` returns a list of refusal lines (empty = clean) and
`render(text, files)` returns the generated markdown byte for byte.
"""

import contextlib
import importlib.util
import io
import pathlib

HERE = pathlib.Path(__file__).resolve()


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "subsystems.py",
        pathlib.Path("pkgs/evidence/subsystems.py"),
    ]
    src = next(p for p in candidates if p.exists())
    spec = importlib.util.spec_from_file_location("subsystems", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sub = load()


def base_text():
    return """\
[[subsystem]]
name = "Alpha"
prefix = "AL"
area = "alpha"
gate = "opus"
owns = ["alpha/*"]
plans = ["docs/superpowers/plans/alpha.md"]
depends = ["Beta"]

[[subsystem]]
name = "Beta"
prefix = "BE"
area = "beta"
gate = "sonnet"
owns = ["beta/*"]
plans = ["docs/superpowers/plans/beta.md"]
depends = ["Gamma"]

[[subsystem]]
name = "Gamma"
prefix = "GA"
area = "gamma"
gate = "sonnet"
owns = ["gamma/*"]
plans = ["docs/superpowers/plans/gamma.md"]
depends = []
"""


def base_files():
    return ["alpha/a.txt", "beta/b.txt", "gamma/g.txt"]


def test_clean_fixture_passes():
    assert sub.validate(base_text(), base_files()) == []


def test_docstring_describes_the_matcher_used():
    import fnmatch

    # Interface 1: one matcher. validate/render match globs with the stdlib
    # fnmatch.fnmatch (imported here, not copied from tasks.py), and the module
    # docstring must say exactly that — it may not name a matcher the code does
    # not call (e.g. tasks.file_class).
    assert sub.fnmatch is fnmatch
    assert "fnmatch.fnmatch" in sub.__doc__
    assert "file_class" not in sub.__doc__


def test_missing_field_refused():
    text = base_text().replace('prefix = "AL"\n', "")
    msgs = sub.validate(text, base_files())
    assert any("missing field" in m for m in msgs)


def test_duplicate_prefix_refused():
    text = base_text().replace('prefix = "GA"\n', 'prefix = "AL"\n')
    msgs = sub.validate(text, base_files())
    assert any("duplicate prefix" in m for m in msgs)


def test_duplicate_area_refused():
    text = base_text().replace('area = "gamma"\n', 'area = "alpha"\n')
    msgs = sub.validate(text, base_files())
    assert any("duplicate area" in m for m in msgs)


def test_unknown_gate_refused():
    text = base_text().replace('gate = "opus"\n', 'gate = "bogus"\n')
    msgs = sub.validate(text, base_files())
    assert any("unknown gate" in m for m in msgs)


def test_cycle_refused():
    # Beta -> Alpha while Alpha -> Beta: a two-node cycle, everything else valid.
    text = base_text().replace('depends = ["Gamma"]\n', 'depends = ["Alpha"]\n', 1)
    msgs = sub.validate(text, base_files())
    assert any("cycle" in m for m in msgs)
    # the fixture still passes every other rule (coverage stays clean)
    assert not any("uncovered" in m or "ambiguous" in m for m in msgs)


def test_dangling_depends_refused():
    text = base_text().replace("depends = []\n", 'depends = ["Delta"]\n')
    msgs = sub.validate(text, base_files())
    assert any("dangling dependency" in m for m in msgs)


def test_no_plans_refused():
    text = base_text().replace(
        'plans = ["docs/superpowers/plans/gamma.md"]\n', "plans = []\n"
    )
    msgs = sub.validate(text, base_files())
    assert any("no plans for" in m for m in msgs)


def test_manifest_without_dependencies_is_clean():
    # every row declaring no dependency is a legal manifest: the validator has
    # no global "no dependencies declared" refusal, so nothing is reported.
    text = base_text()
    text = text.replace('depends = ["Beta"]\n', "depends = []\n")
    text = text.replace('depends = ["Gamma"]\n', "depends = []\n")
    assert sub.validate(text, base_files()) == []


def test_uncovered_path_refused():
    files = base_files() + ["delta/d.txt"]
    msgs = sub.validate(base_text(), files)
    assert any("uncovered: delta/d.txt" in m for m in msgs)


def test_ambiguous_path_refused():
    text = base_text().replace('owns = ["gamma/*"]\n', 'owns = ["gamma/*", "beta/*"]\n')
    msgs = sub.validate(text, base_files())
    assert any("ambiguous: beta/b.txt" in m for m in msgs)


def test_within_row_overlap_counts_once():
    # one path matching two globs of the SAME row is owned once, not ambiguous
    text = base_text().replace(
        'owns = ["alpha/*"]\n', 'owns = ["alpha/*", "alpha/a.txt"]\n'
    )
    msgs = sub.validate(text, base_files())
    assert msgs == []
    # ...and `counts` tallies it once, not per-glob.
    assert sub.counts(text, base_files())[0] == ("Alpha", 1)


def test_render_is_byte_stable():
    a = sub.render(base_text(), base_files())
    b = sub.render(base_text(), base_files())
    assert a == b


def test_render_drops_the_paths_column():
    # the generated table names subsystem/prefix/area/gate/depends and never a
    # per-subsystem path count, so it cannot go stale on unrelated files.
    out = sub.render(base_text(), base_files())
    assert "| Subsystem | Prefix | Area | Gate | Depends |" in out
    assert "| Paths |" not in out


def test_counts_one_line_per_row(tmp_path):
    files = base_files() + ["gamma/g2.txt"]
    pairs = sub.counts(base_text(), files)
    assert pairs == [("Alpha", 1), ("Beta", 1), ("Gamma", 2)]


def test_counts_flag_prints_and_writes_nothing(tmp_path):
    # Interface 3: validate --counts prints one <name>: <n> line per row to
    # stdout and exits 0 without creating a file.
    toml = tmp_path / "subsystems.toml"
    toml.write_text(base_text())
    files = tmp_path / "files.txt"
    files.write_text("\n".join(base_files() + ["gamma/g2.txt"]) + "\n")
    before = {p.name for p in tmp_path.iterdir()}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = sub.main(["validate", str(toml), "--files", str(files), "--counts"])
    assert rc == 0
    assert out.getvalue().splitlines() == ["Alpha: 1", "Beta: 1", "Gamma: 2"]
    assert {p.name for p in tmp_path.iterdir()} == before


def test_counts_flag_validates_first(tmp_path):
    # Interface 2: validate --counts runs the full validation first and prints
    # counts only when the manifest is sound. On a manifest with an uncovered
    # path it exits 1 and prints no count line, exactly as `validate` does.
    toml = tmp_path / "subsystems.toml"
    toml.write_text(base_text())
    files = tmp_path / "files.txt"
    files.write_text("\n".join(base_files() + ["delta/d.txt"]) + "\n")
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = sub.main(["validate", str(toml), "--files", str(files), "--counts"])
    assert rc == 1
    assert out.getvalue() == ""
    assert "uncovered: delta/d.txt" in err.getvalue()


def test_render_is_a_function_of_the_manifest_alone():
    # Interface 1: the generated page depends on docs/ledger/subsystems.toml
    # only, never on the file list. Two renders over *different* file lists
    # of the same manifest must be byte-identical, so `subsystems-manifest`
    # stops going stale when any unrelated file lands in the repo.
    files_a = base_files()
    files_b = base_files() + ["gamma/g2.txt", "gamma/g3.txt"]
    assert sub.render(base_text(), files_a) == sub.render(base_text(), files_b)
