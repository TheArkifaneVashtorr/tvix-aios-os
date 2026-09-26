"""Plan-judgement ingest: a field allowlist that refuses free text (plan 2026-09-06-planning-agent, P6).

A judgement file is ``docs/reviews/plan-judgements/<date>-<name>.md``: line 1
``---``, then one ``key: value`` per line, then a closing ``---``, prose after.
The block may hold only the 14 allowlisted fields (plus the optional, never
stored, ``date``), every string value <= 200 bytes, and each value must match
its class; the prose is never read, so a body, an erratum, a reason or a note
cannot ride a field into the stream.
``ingest judgements <repo>`` appends one row per judgement FILE (keyed by
``judgement_path``, not ``(plan, revision)`` -- a full re-draft after a
``revise`` verdict carries ``revision: 0`` on both rounds, so that key used to
collapse the two into one and discard whichever the dedup saw first) to the
``plans`` stream; ``validate_judgement(fields, repo=None) -> list[str]`` is
the fence. ``evidence report plans`` selects the latest judgement per plan by
``judged_ts`` -- see ``report.py``'s ``_latest_by_plan``.

The fence is widened (operator decision 2026-09-17) to accept real shapes the
authoring tools actually write, without ever editing the judgement records
themselves: ``_canonicalize`` rewrites those shapes into the ones the rest of
this module already understood --

* ``plan``: an absolute scratch/batch path is accepted only when its basename
  already landed under ``docs/superpowers/plans/``; it is rewritten to that
  repo-relative path. A basename with no landed copy is never accepted (a
  named refusal, not silence) -- see ``_canonicalize``.
* ``author``: ``fable``/``hand``/``dsh:<model>`` may carry one or more
  hyphenated authoring-method suffixes (``fable-lane``,
  ``fable-workflow-revision``); the full string is kept (``streams.AUTHOR_RE_SRC``).
* ``tasks``: a bracketed or bare comma-separated task-id list reduces to its
  LENGTH; the ids themselves are never stored.
* ``judges``: the same bare comma list real files write (no brackets) parses
  like the bracketed form.
* ``self_score``: a 14-item 0-3 list reduces to its SUM (0-42 by
  construction); the Python-style ``None`` spelling is treated as ``null``.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import subprocess
import sys

import evidence
import streams

MAX_BYTES = 200
PLAN_PATH_RE = re.compile(r"^docs/[A-Za-z0-9._/-]{1,190}$")
JUDGEMENT_PATH_RE = re.compile(
    r"^docs/reviews/plan-judgements/[A-Za-z0-9._-]{1,150}\.md$"
)
AUTHOR_RE = re.compile(streams.AUTHOR_RE_SRC)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EFFORTS = {"off", "low", "medium", "high", "xhigh", "max", "unknown"}
DECISIONS = {"dispatch", "revise", "revise-exhausted", "panel-short"}
JUDGES = {"sonnet", "opus", "deepseek", "fable"}
DROPPED = {"implementer", "reviewer", "whole"}
FIELDS = streams.judgement_fields()
# The assembled row `validate_judgement` sees: the 14 fields plus the transport
# fields the ingest adds before appending, plus the optional `date` some real
# files carry (accepted and bounded, but never stored -- see `_canonicalize`
# and `_row_fields`).
ROW_KEYS = set(FIELDS) | {"kind", "judged_ts", "judgement_path", "date"}


class DuplicateKey(Exception):
    """A front-matter key appeared twice in one block."""

    def __init__(self, key):
        super().__init__(key)
        self.key = key


def run(argv, timeout=20.0):
    """The subprocess seam (mirrors the sibling modules)."""
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_list(value):
    """``[a, b, c]`` -> ``["a", "b", "c"]``, ``[]`` -> ``[]``, else None."""
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [t.strip() for t in inner.split(",")]


def parse_list_loose(value):
    """``parse_list``, widened to also accept a bare, unbracketed comma list --
    real judgement files write ``judges: sonnet, sonnet, opus`` and
    ``tasks: SH1, SH2, SH3`` with no brackets, alongside the bracketed form.
    A value with no comma (a plain scalar, or a single bad token) is never
    treated as a one-item list; nor is one with an empty item (a stray
    trailing comma)."""
    ls = parse_list(value)
    if ls is not None:
        return ls
    v = value.strip()
    if "," not in v or v.startswith("[") or v.endswith("]"):
        return None
    parts = [t.strip() for t in v.split(",")]
    if any(not t for t in parts):
        return None
    return parts


def parse_front_matter(text):
    """The block's fields as a str->str dict, or None when there is no block.
    Raises `DuplicateKey` when a key appears twice in one block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if not line.strip():
            continue
        if ":" not in line:
            return None  # a malformed line inside the block is not a block
        key, _, value = line.partition(":")
        key = key.strip()
        if key in fields:
            raise DuplicateKey(key)
        fields[key] = value.strip()
    return None  # opened fence, never closed


def _path_ok(value):
    """A repo-relative `plan`/`spec` path: rooted under `docs/`, no `..` segment."""
    return (
        isinstance(value, str)
        and PLAN_PATH_RE.match(value)
        and all(seg != ".." for seg in value.split("/"))
    )


def _canonicalize(fields, repo=None):
    """Rewrite the widened real-world shapes into the canonical ones the rest
    of this module already checks, so no other check needs to change. Returns
    `(fields, errors)`; the caller's dict is never mutated. `errors` holds
    exactly the reasons a canonicalization step itself refuses a value (today,
    only an absolute `plan` path with no landed copy) -- it never silently
    drops a value it cannot resolve."""
    fields = dict(fields)
    errors = []

    # plan: an absolute scratch/batch path is accepted only when its basename
    # already landed under docs/superpowers/plans/; rewritten to that
    # repo-relative path. A basename with no landed copy is refused by name,
    # never silently laundered (`fields["plan"]` becomes None so the
    # downstream `_path_ok` check below is skipped rather than adding a
    # second, redundant "plan: invalid path" for the same reason).
    value = fields.get("plan")
    if (
        isinstance(value, str)
        and os.path.isabs(value)
        and not value.lstrip("/").startswith("docs/")
    ):
        # a foreign scratch/batch root (/home/..., /tmp/...), not a mistyped
        # docs/ path with a stray leading slash -- the latter falls through
        # to the ordinary `_path_ok` check below unchanged, which already
        # refuses any leading "/".
        target = f"docs/superpowers/plans/{os.path.basename(value)}"
        if repo is not None and (pathlib.Path(repo) / target).is_file():
            fields["plan"] = target
        else:
            errors.append(f"plan: {value} has no landed copy at {target}")
            fields["plan"] = None

    # tasks: a task-id list (bracketed or bare) is reduced to its length; the
    # ids themselves are never stored. A plain integer (already the count) is
    # left alone.
    value = fields.get("tasks")
    if value is not None and _as_int(value) is None:
        ls = parse_list_loose(value)
        if ls is not None:
            fields["tasks"] = str(len(ls))

    # judges: the same bare comma list real files write for `tasks` also
    # appears here; canonicalize to the bracketed form the existing check and
    # `_row_fields` already parse.
    value = fields.get("judges")
    if value is not None and parse_list(value) is None:
        ls = parse_list_loose(value)
        if ls is not None:
            fields["judges"] = "[" + ", ".join(ls) + "]"

    # self_score: a 14-item 0-3 per-criterion self-review list reduces to its
    # sum (0-42 by construction); the Python-style `None` spelling is treated
    # as the `null` this field already accepts.
    value = fields.get("self_score")
    if value == "None":
        fields["self_score"] = "null"
    elif value is not None:
        ls = parse_list(value)
        if ls is not None and len(ls) == 14:
            vals = [_as_int(t) for t in ls]
            if all(v is not None and 0 <= v <= 3 for v in vals):
                fields["self_score"] = str(sum(vals))

    return fields, errors


def validate_judgement(fields, repo=None):
    """Every reason the row is refused; [] means it ingests. `fields` is the
    assembled row: the raw str->str block fields plus `kind`, `judged_ts` and
    `judgement_path`, so no field can bypass the fence. `repo` (the ingest's
    repo root) is used only to resolve an absolute `plan` path against
    `docs/superpowers/plans/`; every other check is unaffected by it."""
    errors = []
    fields, canon_errors = _canonicalize(fields, repo)
    errors.extend(canon_errors)

    # the fence: only the allowlisted names may appear at all.
    for key in fields:
        if key not in ROW_KEYS:
            errors.append(f"unknown field {key}")

    # every string value is bounded, so free text cannot ride in a field.
    for key, value in fields.items():
        if isinstance(value, str):
            n = len(value.encode("utf-8"))
            if n > MAX_BYTES:
                errors.append(f"{key}: {n} bytes (limit {MAX_BYTES})")

    for key in FIELDS:
        if key not in fields:
            errors.append(f"missing {key}")

    # plan was already resolved by `_canonicalize` above; a value that
    # couldn't be resolved is left as None there (and already named in
    # canon_errors), so this only re-checks a plan that canonicalized cleanly
    # (or was already a plain repo-relative path).
    value = fields.get("plan")
    if value is not None and not _path_ok(value):
        errors.append("plan: invalid path")

    value = fields.get("spec")
    if value is not None and not _path_ok(value):
        errors.append("spec: invalid path")

    # date: optional and never stored (2026-09-09-program.md carries one
    # beside judged_ts), but still bounded/shaped -- not a free-text escape
    # hatch just because it is dropped before the typed row is built.
    value = fields.get("date")
    if value is not None and (not isinstance(value, str) or not DATE_RE.match(value)):
        errors.append("date: invalid (YYYY-MM-DD)")

    value = fields.get("judgement_path")
    if value is not None and (
        not isinstance(value, str) or not JUDGEMENT_PATH_RE.match(value)
    ):
        errors.append("judgement_path: invalid path")

    value = fields.get("author")
    if value is not None and (not isinstance(value, str) or not AUTHOR_RE.match(value)):
        errors.append("author: invalid (fable | hand | dsh:<model>)")

    value = fields.get("effort")
    if value is not None and value not in EFFORTS:
        errors.append("effort: invalid (off|low|medium|high|xhigh|max|unknown)")

    for key in ("words", "tasks", "revision"):
        value = fields.get(key)
        n = _as_int(value)
        if value is not None and (n is None or n < 0):
            errors.append(f"{key}: invalid integer (>= 0)")

    for key in ("threshold", "total"):
        value = fields.get(key)
        if value is not None and _as_int(value) is None:
            errors.append(f"{key}: invalid integer")

    value = fields.get("self_score")
    if value is not None and value != "null":
        n = _as_int(value)
        if n is None or not 0 <= n <= 42:
            errors.append("self_score: invalid (0-42 or null)")

    value = fields.get("decision")
    if value is not None and value not in DECISIONS:
        errors.append(
            "decision: invalid (dispatch|revise|revise-exhausted|panel-short)"
        )

    value = fields.get("judges")
    if value is not None:
        ls = parse_list(value)
        if ls is None or len(ls) > 3 or any(j not in JUDGES for j in ls):
            errors.append("judges: invalid (0-3 of sonnet|opus|deepseek|fable)")

    value = fields.get("judges_dropped")
    if value is not None:
        ls = parse_list(value)
        if ls is None or any(j not in DROPPED for j in ls):
            errors.append("judges_dropped: invalid (implementer|reviewer|whole)")

    scores = None
    value = fields.get("scores")
    if value is not None:
        ls = parse_list(value)
        if ls is None:
            errors.append("scores: invalid list")
        elif len(ls) != 14:
            errors.append(f"scores: must be exactly 14 entries (got {len(ls)})")
        else:
            vals = []
            for t in ls:
                n = _as_int(t)
                if n is None or not 0 <= n <= 3:
                    vals = None
                    break
                vals.append(n)
            if vals is None:
                errors.append("scores: entries must be integers 0-3")
            else:
                scores = vals

    total = fields.get("total")
    if total is not None and scores is not None:
        tn = _as_int(total)
        if tn is not None and tn != sum(scores):
            errors.append(f"total {tn} does not equal scores sum {sum(scores)}")

    # the declared-kind fence (T1): only on a clean row, so the messages above
    # stay byte-identical, then every reason from `streams.validate`.
    if errors:
        return errors
    typed = {"kind": "plan-judgement", **_row_fields(fields, repo=repo)}
    if fields.get("judged_ts") is not None:
        typed["judged_ts"] = fields["judged_ts"]
    if fields.get("judgement_path") is not None:
        typed["judgement_path"] = fields["judgement_path"]
    errors.extend(streams.validate("plan-judgement", typed))
    return errors


def _row_fields(fields, repo=None):
    """The 14 typed fields, assuming `validate_judgement(fields, repo) == []`.
    Re-applies `_canonicalize` (idempotent) so a caller may pass either the
    raw front-matter fields or an already-canonicalized dict; `date`, when
    present, is never one of the 14 and is simply not copied."""
    fields, _ = _canonicalize(fields, repo)
    out = {}
    for key in ("plan", "spec", "author", "effort", "decision"):
        out[key] = fields[key]
    for key in ("words", "tasks", "threshold", "revision", "total"):
        out[key] = int(fields[key])
    out["self_score"] = (
        None if fields["self_score"] == "null" else int(fields["self_score"])
    )
    out["judges"] = parse_list(fields["judges"])
    out["judges_dropped"] = parse_list(fields["judges_dropped"])
    out["scores"] = [int(t) for t in parse_list(fields["scores"])]
    return out


def judged_ts(repo, rel_path):
    """The file's first git commit time in RFC3339 Z, or its mtime when git says
    nothing (the file is uncommitted or the tree is not a repository). Git's
    `%cI` renders a non-UTC committer offset verbatim (e.g. `...-05:00`), not
    as `Z` -- this repo's real commits do exactly that -- so the raw value is
    converted to UTC before returning; `streams.py`'s `TS_RE` accepts only the
    `Z` form."""
    try:
        cp = run(
            [
                "git",
                "-C",
                repo,
                "log",
                "--diff-filter=A",
                "--format=%cI",
                "--",
                rel_path,
            ]
        )
    except (OSError, subprocess.SubprocessError):
        cp = None
    if cp is not None and cp.returncode == 0 and cp.stdout.strip():
        raw = cp.stdout.strip().splitlines()[-1]
        when = datetime.datetime.fromisoformat(raw).astimezone(datetime.timezone.utc)
        return when.strftime("%Y-%m-%dT%H:%M:%SZ")
    mtime = os.path.getmtime(os.path.join(repo, rel_path))
    return datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def ingest_judgements(store, repo):
    """Ingest every judgement file under `<repo>/docs/reviews/plan-judgements/`,
    appending one `plans` row per FILE (keyed by `judgement_path`, never
    `(plan, revision)` -- a plan re-drafted after a `revise` verdict and
    re-judged carries `revision: 0` on both rounds, so that key silently
    collapsed the two into one and threw away whichever the dedup saw first;
    every judgement file is its own record and none is discarded here).
    Returns 1 when any file is refused, 0 otherwise (a missing directory is 0).
    """
    repo_arg = str(repo)
    repo = pathlib.Path(repo)
    jdir = repo / "docs" / "reviews" / "plan-judgements"
    if not jdir.is_dir():
        print(f"no judgements under {repo_arg}")
        return 0
    existing = {
        r.get("judgement_path")
        for r in evidence.read(store, "plans")
        if r.get("kind") == "plan-judgement"
    }
    failed = False
    for path in sorted(jdir.glob("*.md")):
        rel = path.relative_to(repo).as_posix()
        try:
            text = path.read_text()
        except OSError:
            continue
        try:
            fields = parse_front_matter(text)
        except DuplicateKey as dup:
            print(f"refused {rel}: duplicate key {dup.key}", file=sys.stderr)
            failed = True
            continue
        if fields is None:
            print(f"refused {rel}: no front-matter block", file=sys.stderr)
            failed = True
            continue
        judged = judged_ts(str(repo), rel)
        row = {
            "kind": "plan-judgement",
            **fields,
            "judged_ts": judged,
            "judgement_path": rel,
        }
        errors = validate_judgement(row, repo=repo)
        if errors:
            print(f"refused {rel}: {'; '.join(errors)}", file=sys.stderr)
            failed = True
            continue
        row_fields = _row_fields(fields, repo=repo)
        key = rel  # judgement_path: every file is its own record
        if key in existing:
            print(f"skipped {rel} (present)")
            continue
        evidence.append(
            store,
            "plans",
            {
                "kind": "plan-judgement",
                **row_fields,
                "judged_ts": judged,
                "judgement_path": rel,
            },
        )
        existing.add(key)
        print(f"ingested {rel}")
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="judgements")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    )
    parser.add_argument(
        "--fields",
        action="store_true",
        help="print the 14 allowlisted field names, one per line",
    )
    sub = parser.add_subparsers(dest="command")
    jp = sub.add_parser(
        "judgements", help="ingest plan-judgement files into the plans stream"
    )
    jp.add_argument("repo")
    args = parser.parse_args(argv)
    if args.fields:
        for name in FIELDS:
            print(name)
        return 0
    if args.command != "judgements":
        parser.error("a command is required (judgements), or --fields")
    return ingest_judgements(args.store, args.repo)


if __name__ == "__main__":
    raise SystemExit(main())
