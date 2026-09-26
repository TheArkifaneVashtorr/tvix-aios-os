import datetime as dt
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()


def load():
    root = HERE.parents[2]
    candidates = [
        root / "pkgs" / "evidence" / "claims.py",
        pathlib.Path("pkgs/evidence/claims.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("claims", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, root


claims, ROOT = load()

GOOD = """
[[claim]]
id = "seat-denials-audited"
text = "every refused seat tool call is recorded in the transcript"
status = "verified"
class = "unit"
evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats"
owner = "orchestrator"
opened = 2026-09-04

[[claim]]
id = "effort-policy-n1"
text = "effort off costs less than medium for equal Opus verdicts"
status = "gap"
class = "unmeasured"
owner = "orchestrator"
opened = 2026-09-05
review_by = 2026-09-12
closes_by = "n >= 5 per arm, verdicts equal, tokens in the ledger"

[[claim]]
id = "zzz-earliest-opened"
text = "ordering pin: an earlier opened date sorts before a later one"
status = "gap"
class = "unmeasured"
owner = "operator"
opened = 2026-09-03
review_by = 2026-09-30
closes_by = "x"

[[claim]]
id = "aaa-same-day"
text = "ordering pin: on an equal opened date the id breaks the tie"
status = "gap"
class = "unmeasured"
owner = "operator"
opened = 2026-09-05
review_by = 2026-09-30
closes_by = "y"

[[claim]]
id = "cowork-tier-a"
text = "the Cowork tier-A bubble is built and verified"
status = "parked"
class = "vm"
owner = "operator"
opened = 2026-09-02
decision = "docs/decisions/2026-09-02-cowork-tier-parked.md"
"""


def write(tmp_path, text):
    p = tmp_path / "claims.toml"
    p.write_text(text)
    return p


def test_good_file_validates_and_open_gaps_sorted(tmp_path):
    rows = claims.load(write(tmp_path, GOOD), repo_root=ROOT)
    assert claims.validate(rows, today=dt.date(2026, 9, 6), repo_root=ROOT) == []
    assert [g["id"] for g in claims.open_gaps(rows)] == [
        "zzz-earliest-opened",
        "aaa-same-day",
        "effort-policy-n1",
    ]


def test_verified_needs_evidence_and_a_real_class(tmp_path):
    bad = GOOD.replace(
        'evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats"\n', ""
    ).replace('class = "unit"', 'class = "unmeasured"', 1)
    errs = claims.validate(
        claims.load(write(tmp_path, bad), repo_root=ROOT), repo_root=ROOT
    )
    assert any("seat-denials-audited" in e and "evidence" in e for e in errs)
    assert any("seat-denials-audited" in e and "unmeasured" in e for e in errs)


def test_claim_class_must_be_a_known_class(tmp_path):
    bad = GOOD.replace('class = "unit"', 'class = "bogus"', 1)
    errs = claims.validate(
        claims.load(write(tmp_path, bad), repo_root=ROOT), repo_root=ROOT
    )
    assert any(
        "seat-denials-audited" in e and "class must be one of" in e for e in errs
    )


def test_verified_evidence_must_be_check_or_operator_form(tmp_path):
    bad = GOOD.replace(
        'evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats"',
        'evidence = "trust me, I looked at it"',
    )
    errs = claims.validate(
        claims.load(write(tmp_path, bad), repo_root=ROOT), repo_root=ROOT
    )
    assert any("seat-denials-audited" in e and "must start with" in e for e in errs)
    short_rev = GOOD.replace(
        'evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats"',
        'evidence = "check:unit@abc tests/x"',
    )
    errs2 = claims.validate(
        claims.load(write(tmp_path, short_rev), repo_root=ROOT), repo_root=ROOT
    )
    assert any("seat-denials-audited" in e and "must start with" in e for e in errs2)
    ok = GOOD.replace(
        'evidence = "check:unit@dd01dfb tests/unit/70-dsh-openrouter.bats"',
        'evidence = "operator:2026-09-04 drill step 7 in Firefox"',
    )
    assert (
        claims.validate(
            claims.load(write(tmp_path, ok), repo_root=ROOT), repo_root=ROOT
        )
        == []
    )


def test_gap_needs_owner_review_by_closes_by(tmp_path):
    bad = GOOD.replace(
        'closes_by = "n >= 5 per arm, verdicts equal, tokens in the ledger"\n', ""
    ).replace("review_by = 2026-09-12\n", "")
    errs = claims.validate(
        claims.load(write(tmp_path, bad), repo_root=ROOT), repo_root=ROOT
    )
    assert any("effort-policy-n1" in e and "closes_by" in e for e in errs)
    assert any("effort-policy-n1" in e and "review_by" in e for e in errs)


def test_stale_gap_fails_only_with_today(tmp_path):
    rows = claims.load(write(tmp_path, GOOD), repo_root=ROOT)
    assert claims.validate(rows, repo_root=ROOT) == []
    errs = claims.validate(rows, today=dt.date(2026, 9, 13), repo_root=ROOT)
    assert errs == [
        "claims: effort-policy-n1: gap past review_by 2026-09-12 (today 2026-09-13) — extend it with a reason or close it"
    ]


def test_parked_needs_an_existing_decision_and_ids_are_unique(tmp_path):
    bad = GOOD.replace(
        "2026-09-02-cowork-tier-parked.md", "2026-09-02-nope.md"
    ).replace('id = "effort-policy-n1"', 'id = "seat-denials-audited"')
    errs = claims.validate(
        claims.load(write(tmp_path, bad), repo_root=ROOT), repo_root=ROOT
    )
    assert any("cowork-tier-a" in e and "decision" in e for e in errs)
    assert any("duplicate id" in e for e in errs)


def test_repo_claims_file_validates_structurally():
    rows = claims.load(ROOT / "docs" / "ledger" / "claims.toml", repo_root=ROOT)
    assert claims.validate(rows, repo_root=ROOT) == []
    assert len(rows) >= 24
