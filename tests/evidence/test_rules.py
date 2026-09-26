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
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve()
EVIDENCE = HERE.parents[2] / "pkgs" / "evidence"
sys.path.insert(0, str(EVIDENCE))

import rules

ROOT = HERE.parents[2]


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
        "CLAUDE.md",
        "tools/orchestrator-guard.sh",
        "pkgs/dsh-openrouter/hook-guard.py",
        "docs/board/policies.md",
        "docs/board/operator-model.md",
        "docs/runbooks/session.md",
    ):
        assert p in sources, f"{p} must have at least one row"
    assert any(p.endswith("AGENTS.md") for p in sources), (
        "the harness AGENTS.md must be inventoried"
    )


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
