"""Publish manifest validator tests (plan 2026-09-21-publish-gate, PG1).

Every test's docstring names the one-line mutant that turns it red; every
fixture carries the row that makes the assertion discriminate.
"""

import os
import pathlib
import stat
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
SRC = next(
    p
    for p in (
        HERE.parents[2] / "pkgs" / "evidence" / "publish.py",
        pathlib.Path("pkgs/evidence/publish.py"),
    )
    if p.exists()
)
FIXTURE = HERE.parents[2] / "tests" / "fixtures" / "publish"

MANIFEST = """\
publish  = ["pub/*", "README.md"]
withhold = ["publish.toml", "priv/*"]
pending  = []

[deny]
literals = ["nobody@example.invalid", "900000001"]
words    = ["plantedword"]
patterns = ["PLANTED-[0-9]{4}"]
"""


def make_tree(root, files, manifest=MANIFEST):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode())
    root.mkdir(parents=True, exist_ok=True)
    (root / "publish.toml").write_text(manifest)
    return root


def run(tree, *extra, manifest=None):
    manifest = str(tree / "publish.toml") if manifest is None else manifest
    r = subprocess.run(
        [sys.executable, str(SRC), "validate", manifest, "--tree", str(tree), *extra],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return r.returncode, r.stdout.splitlines(), r.stderr


def test_clean_tree_exits_0_with_only_the_counts_line(tmp_path):
    """Mutant: omit the counts line on a clean run, or print it first."""
    t = make_tree(
        tmp_path,
        {
            "pub/a.txt": "clean\n",
            "README.md": "clean\n",
            "priv/x": "nobody@example.invalid\n",
        },
    )
    assert run(t) == (0, ["published 2 withheld 2 pending 0"], "")


def test_unclassified_and_ambiguous_are_defects(tmp_path):
    """Mutant: drop the zero-match branch (loses `unclassified`) or report only the first match (loses `ambiguous`)."""
    m = MANIFEST.replace(
        'withhold = ["publish.toml", "priv/*"]',
        'withhold = ["publish.toml", "priv/*", "pub/both.txt"]',
    )
    t = make_tree(
        tmp_path, {"pub/both.txt": "x\n", "stray.txt": "x\n", "README.md": "x\n"}, m
    )
    assert run(t)[:2] == (
        1,
        [
            "ambiguous pub/both.txt publish,withhold",
            "unclassified stray.txt",
            "published 1 withheld 1 pending 0",
        ],
    )


def test_literal_is_exact_bytes_case_sensitive(tmp_path):
    """Mutant: compare case-insensitively — line 2 is reported too."""
    t = make_tree(
        tmp_path,
        {
            "pub/a.txt": "x\nNobody@Example.Invalid\nnobody@example.invalid\n",
            "README.md": "x\n",
        },
    )
    assert run(t)[1][:-1] == ["pub/a.txt:3 literals[0]"]


def test_word_is_bounded_and_case_sensitive(tmp_path):
    """Mutant: drop the \\b anchors — lines 1 and 2 are reported; lower-case the data — line 3 is."""
    t = make_tree(
        tmp_path,
        {
            "pub/a.txt": "plantedwords\nunplantedword\nPlantedword\nthe plantedword\n",
            "README.md": "x\n",
        },
    )
    assert run(t)[1][:-1] == ["pub/a.txt:4 words[0]"]


def test_pattern_is_a_regex_and_ids_are_zero_based(tmp_path):
    """Mutant: match patterns as literals — line 2 goes unreported; number rules from 1 — `patterns[1]`."""
    t = make_tree(
        tmp_path, {"pub/a.txt": "PLANTED-12\nPLANTED-1234\n", "README.md": "x\n"}
    )
    assert run(t)[1][:-1] == ["pub/a.txt:2 patterns[0]"]


def test_second_literal_has_index_1_and_lines_are_one_based(tmp_path):
    """Mutant: count newlines after the match (line 4) or from zero (line 2)."""
    t = make_tree(tmp_path, {"pub/a.txt": "a\nb\n900000001\nd\n", "README.md": "x\n"})
    assert run(t)[1][:-1] == ["pub/a.txt:3 literals[1]"]


def test_two_rules_on_one_line_print_two_ids(tmp_path):
    """Mutant: stop at the first matching rule per line."""
    t = make_tree(
        tmp_path,
        {"pub/a.txt": "nobody@example.invalid plantedword\n", "README.md": "x\n"},
    )
    assert run(t)[1][:-1] == ["pub/a.txt:1 literals[0]", "pub/a.txt:1 words[0]"]


def test_report_never_contains_a_matched_value(tmp_path):
    """Mutant: append the matched text after the rule id (spec §6)."""
    t = make_tree(
        tmp_path,
        {
            "pub/a.txt": "nobody@example.invalid\n900000001\nplantedword\nPLANTED-1234\n",
            "README.md": "x\n",
        },
    )
    rc, out, err = run(t)
    text = "\n".join(out) + err
    for value in ("nobody@example.invalid", "900000001", "plantedword", "PLANTED-1234"):
        assert value not in text
    assert rc == 1 and len(out) == 5


def test_withheld_paths_are_never_read(tmp_path):
    """Mutant: scan every classified path — priv/hit prints `priv/hit:1 literals[0]` and priv/locked raises PermissionError."""
    t = make_tree(
        tmp_path,
        {
            "pub/a.txt": "x\n",
            "README.md": "x\n",
            "priv/hit": "nobody@example.invalid\n",
            "priv/locked": "x\n",
        },
    )
    os.chmod(t / "priv" / "locked", 0)
    try:
        result = run(t)
    finally:
        os.chmod(t / "priv" / "locked", stat.S_IRUSR | stat.S_IWUSR)
    assert result == (0, ["published 2 withheld 3 pending 0"], "")


def test_pending_arms(tmp_path):
    """Mutants, one per line: skip the existence check (`pending-missing` lost); skip the publish check (`pending-not-public` lost); skip the match check (`stale-pending` lost); scan a pending path like a published one (`pub/hit.txt:1 literals[0]` gained)."""
    m = MANIFEST.replace(
        "pending  = []",
        'pending  = ["pub/hit.txt", "pub/clean.txt", "priv/p", "pub/gone.txt"]',
    )
    t = make_tree(
        tmp_path,
        {
            "pub/hit.txt": "nobody@example.invalid\n",
            "pub/clean.txt": "x\n",
            "priv/p": "x\n",
            "README.md": "x\n",
        },
        m,
    )
    assert run(t)[:2] == (
        1,
        [
            "pending-missing pub/gone.txt",
            "pending-not-public priv/p",
            "stale-pending pub/clean.txt",
            "published 1 withheld 2 pending 2",
        ],
    )


def test_counts_exclude_pending_from_published(tmp_path):
    """Mutant: count pending paths as published — `published 2`."""
    m = MANIFEST.replace("pending  = []", 'pending  = ["pub/hit.txt"]')
    t = make_tree(tmp_path, {"pub/hit.txt": "900000001\n", "README.md": "x\n"}, m)
    assert run(t) == (0, ["published 1 withheld 1 pending 1"], "")


def test_manifest_must_classify_withhold(tmp_path):
    """Mutant: drop the self-classification rule (spec §6)."""
    m = MANIFEST.replace(
        'publish  = ["pub/*", "README.md"]',
        'publish  = ["pub/*", "README.md", "publish.toml"]',
    ).replace('withhold = ["publish.toml", "priv/*"]', 'withhold = ["priv/*"]')
    t = make_tree(tmp_path / "one", {"README.md": "x\n"}, m)
    rc, out, _ = run(t)
    assert rc == 1 and out[:-1] == ["manifest-not-withheld publish.toml publish"]
    t2 = make_tree(
        tmp_path / "two",
        {"README.md": "x\n"},
        MANIFEST.replace(
            'withhold = ["publish.toml", "priv/*"]', 'withhold = ["priv/*"]'
        ),
    )
    rc, out, _ = run(t2)
    assert rc == 1 and out[:-1] == [
        "manifest-not-withheld publish.toml unclassified",
        "unclassified publish.toml",
    ]


def test_malformed_manifests_exit_2_with_nothing_on_stdout(tmp_path):
    """Mutant: exit 1 on a malformed manifest (a check would read it as a real red)."""
    cases = {
        "not-toml": "publish = [\n",
        "unknown-key": "export = []\n" + MANIFEST,
        "double-star": MANIFEST.replace('"pub/*"', '"pub/**"'),
        "bad-glob-char": MANIFEST.replace('"pub/*"', '"pub/[a]"'),
        "pending-glob": MANIFEST.replace("pending  = []", 'pending  = ["pub/*"]'),
        "non-string": MANIFEST.replace('"README.md"', "1"),
        "bad-regex": MANIFEST.replace('"PLANTED-[0-9]{4}"', '"PLANTED-("'),
        "unknown-deny-key": MANIFEST + "tokens = []\n",
    }
    for name, text in cases.items():
        t = make_tree(tmp_path / name, {"README.md": "x\n"}, text)
        rc, out, err = run(t)
        assert (rc, out) == (2, []), name
        assert err.startswith("publish: "), name


def test_manifest_outside_the_tree_exits_2(tmp_path):
    """Mutant: skip the containment rule — the self-classification arm silently passes on a manifest the tree does not hold."""
    t = make_tree(tmp_path / "tree", {"README.md": "x\n"})
    (tmp_path / "elsewhere.toml").write_text(MANIFEST)
    rc, out, _ = run(t, manifest=str(tmp_path / "elsewhere.toml"))
    assert (rc, out) == (2, [])


def test_files_list_is_the_universe_when_given(tmp_path):
    """Mutant: ignore --files and walk — pub/extra.txt (a hit, unlisted) is reported and counted."""
    t = make_tree(
        tmp_path,
        {"pub/a.txt": "x\n", "README.md": "x\n", "pub/extra.txt": "900000001\n"},
    )
    (tmp_path / "list.txt").write_text("pub/a.txt\nREADME.md\npublish.toml\n")
    assert run(t, "--files", str(tmp_path / "list.txt")) == (
        0,
        ["published 2 withheld 1 pending 0"],
        "",
    )


def test_a_checkout_uses_git_ls_files_and_a_plain_dir_walks(tmp_path):
    """Mutant: walk a checkout — the untracked pub/untracked.txt (a hit) is reported; never walk — the plain dir reports `published 0`."""
    repo = make_tree(tmp_path / "repo", {"pub/tracked.txt": "x\n", "README.md": "x\n"})
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig"),
    }
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, env=env)
    (repo / "pub" / "untracked.txt").write_text("900000001\n")
    assert run(repo) == (0, ["published 2 withheld 1 pending 0"], "")
    plain = make_tree(tmp_path / "plain", {"pub/a.txt": "x\n", "README.md": "x\n"})
    assert run(plain) == (0, ["published 2 withheld 1 pending 0"], "")


def test_non_utf8_bytes_are_scanned_as_bytes(tmp_path):
    """Mutant: decode as UTF-8 before scanning — line 2 raises UnicodeDecodeError (exit 1, empty stdout)."""
    t = make_tree(
        tmp_path, {"pub/a.bin": b"\xff\xfe\n\xff 900000001\n", "README.md": "x\n"}
    )
    assert run(t)[1][:-1] == ["pub/a.bin:2 literals[1]"]


def test_report_is_sorted_by_path_line_and_rule(tmp_path):
    """Mutant: emit in walk or dict order — pub/b.txt before pub/a.txt."""
    t = make_tree(
        tmp_path,
        {
            "pub/b.txt": "900000001\n",
            "pub/a.txt": "x\nnobody@example.invalid\n",
            "README.md": "x\n",
        },
    )
    assert run(t)[1] == [
        "pub/a.txt:2 literals[0]",
        "pub/b.txt:1 literals[1]",
        "published 3 withheld 1 pending 0",
    ]


def test_stderr_names_the_brief_on_a_red_run(tmp_path):
    """Mutant: drop the closing stderr line — the check log ends without the rule it enforces (spec §9)."""
    t = make_tree(tmp_path, {"stray.txt": "x\n", "README.md": "x\n"})
    rc, _, err = run(t)
    assert rc == 1 and "brief §3.7" in err


def test_shipped_negative_fixture_reports_every_planted_defect():
    """Mutant: any edit to the shipped fixture or to the validator that changes the report — the same diff publish-gate-negative makes, here so evidence-unit and the check cannot disagree."""
    assert FIXTURE.is_dir(), (
        "tests/fixtures/publish must be copied into the sandbox (flake.nix evidence-unit)"
    )
    rc, out, err = run(FIXTURE)
    assert rc == 1
    assert out == (FIXTURE / "expected.txt").read_text().splitlines()
    for value in ("nobody@example.invalid", "900000001", "plantedword", "PLANTED-1234"):
        assert value not in "\n".join(out) + err


# --- export-list (plan 2026-09-22-tvix-aios-step1, OS1): the export's dry run ---


def run_export(tree, *extra, manifest=None):
    manifest = str(tree / "publish.toml") if manifest is None else manifest
    r = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "export-list",
            manifest,
            "--tree",
            str(tree),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return r.returncode, r.stdout.splitlines(), r.stderr


def test_export_list_prints_exactly_the_published_paths_sorted(tmp_path):
    """Mutant: the withhold filter dropped (priv/x.md listed), or the sort dropped (pub/b.txt before pub/a.txt: b is created first)."""
    t = make_tree(
        tmp_path,
        {
            "pub/b.txt": "b\n",
            "pub/a.txt": "a\n",
            "README.md": "r\n",
            "priv/x.md": "x\n",
        },
    )
    rc, out, err = run_export(t)
    assert rc == 0 and err == ""
    assert out == ["README.md", "pub/a.txt", "pub/b.txt"]


def test_export_list_omits_pending_paths(tmp_path):
    """Mutant: the pending subtraction dropped — pub/leak.txt (public by intent, carrying a planted literal) is listed."""
    manifest = MANIFEST.replace("pending  = []", 'pending  = ["pub/leak.txt"]')
    t = make_tree(
        tmp_path,
        {
            "pub/a.txt": "a\n",
            "pub/leak.txt": "nobody@example.invalid\n",
            "README.md": "r\n",
        },
        manifest=manifest,
    )
    rc, out, err = run_export(t)
    assert rc == 0 and err == ""
    assert out == ["README.md", "pub/a.txt"]


def test_export_list_refuses_a_red_tree_with_the_validate_report(tmp_path):
    """Mutant: the list printed despite a defect, or exit 0 on a red tree — a red gate must never yield a partial export."""
    t = make_tree(tmp_path, {"stray.txt": "x\n", "README.md": "r\n"})
    vrc, vout, _ = run(t)
    assert vrc == 1 and vout == [
        "unclassified stray.txt",
        "published 1 withheld 1 pending 0",
    ]
    rc, out, err = run_export(t)
    assert rc == 1 and out == vout and "brief §3.7" in err


def test_export_list_exits_2_on_an_unusable_manifest(tmp_path):
    """Mutant: ManifestError caught on the validate branch only — a traceback and exit 1 here."""
    t = make_tree(
        tmp_path, {"README.md": "r\n"}, manifest=MANIFEST.replace('"pub/*"', '"pub/**"')
    )
    rc, out, err = run_export(t)
    assert rc == 2 and out == [] and err.startswith("publish: ")


def test_export_list_over_the_shipped_fixture_is_the_negative_report():
    """Mutant: export-list bypassing validate — the fixture's planted defects would be exported."""
    rc, out, _ = run_export(FIXTURE)
    assert rc == 1
    assert out == (FIXTURE / "expected.txt").read_text().splitlines()
