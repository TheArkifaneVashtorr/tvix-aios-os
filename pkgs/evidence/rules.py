"""rules — validate docs/ledger/rules.toml, the house rule inventory (plan 2026-09-09-program, KN1).

One ``[[rule]]`` row per rule, drawn from the six sources (CLAUDE.md, brief §3/§8,
the harness AGENTS.md, the orchestrator guard, the hook-guard table, the board and
the runbooks).  The validator checks the row shape, id uniqueness, the class and
verdict enums, a well-formed ``source`` (``path:line``), and — when the source file
is resolvable under ``--root`` — that the cited line carries a word of the rule's
text.  A missing source file is a *warning*, never an error: the harness AGENTS.md
and the store-path hook-guard table legitimately live outside the repo, and the
evidence-unit sandbox must still validate a partial checkout.

``--verbatim`` strengthens the source check from "a shared word" to the whole of
``text``: for every row whose ``source`` resolves, ``text`` must appear
byte-for-byte in the cited file, modulo line wrapping (every run of whitespace is
collapsed to one space before the search).  A row whose text paraphrases, drops or
fabricates words is refused with the row id, the cited line and the first
differing character.  This is what lets KN1's paraphrases through no longer — the
word check alone accepted any single word the row's prose shared with its source.

``load_bearing`` rows whose ``check`` is empty are *owed*: reported as a count on
stdout (exit 0) so the operator sees the number, not a failure — the operator fills
the verdicts through the dialog (decision 59a's generator later reads the result).

``generate`` (KN15, decision 59a: "one rules source generates CLAUDE.md and
AGENTS.md, drift fails lint") inverts the old direction: the ledger is the
source of record and the target file is its rendering.  Rows carrying
``origin_target = "claude"`` (KN16 adds further targets) render as one bullet
each, in ledger order, ``text`` verbatim, between ``<!-- rules:begin -->`` and
``<!-- rules:end -->`` — the marked block and nothing else is written, the
shape of ``tasks.py``'s board splice.  A row whose ``source`` is the ledger
itself (``docs/ledger/rules.toml:<line>``) is verbatim-checked against the
ledger like any resolvable source: its text lives there now and the generated
file is the rendering, so ``--check`` — not the verbatim arm — is what fails
when the two drift apart.
"""

from __future__ import annotations

import argparse
import difflib
import pathlib
import re
import sys

import tomllib

FIELDS = (
    "id",
    "text",
    "source",
    "origin",
    "class",
    "load_bearing",
    "measured",
    "check",
    "verdict",
)
CLASSES = ("invariant", "practice", "guard", "convention", "ritual")
VERDICTS = ("", "keep", "amend", "retire")
BEGIN, END = "<!-- rules:begin -->", "<!-- rules:end -->"
TARGETS = ("claude",)  # KN16 adds "agents", "agents-commit"
ID_RE = re.compile(r"^R-[a-z0-9][a-z0-9-]*$")
ORIGIN_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WORD = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9-]{3,}")
WHITESPACE = re.compile(r"\s+")


def load(path) -> list[dict]:
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("rule", [])


def _source_parts(source: str) -> tuple[str | None, int | None]:
    path, sep, line = source.rpartition(":")
    if not sep or not line.isdigit():
        return None, None
    return path, int(line)


def _resolve(path: str, root: pathlib.Path | None) -> pathlib.Path:
    p = pathlib.Path(path).expanduser()
    if p.is_absolute():
        return p
    return (root / p) if root else p


def _word_in(text: str, line: str) -> bool:
    words = WORD.findall(text)
    low = line.lower()
    return any(w.lower() in low for w in words)


def _flat(text: str) -> str:
    """Collapse every run of whitespace (newlines, tabs, indentation) to one space.

    This is the "modulo line wrapping" reading of byte-for-byte: the exact words and
    punctuation (backticks, em-dashes, parentheses, `⇒`) must survive in order, but
    the 80-column wrapping a source file adds is not part of the rule's text.
    """
    return WHITESPACE.sub(" ", text).strip()


def _first_diff_char(flat_text: str, flat_file: str) -> str:
    """The first character of ``flat_text`` that ends its match against the file.

    When ``flat_text`` is not a substring of ``flat_file``, find the longest prefix
    of ``flat_text`` that *is* a substring and return the character after it — the
    first place the row's text diverges from anything the file actually says.
    """
    for k in range(len(flat_text), -1, -1):
        if flat_text[:k] in flat_file:
            if k < len(flat_text):
                return flat_text[k]
            return "<matched>"
    return flat_text[0] if flat_text else "<empty>"


def owed(rows: list[dict]) -> int:
    return sum(
        1 for r in rows if r.get("load_bearing") and not (r.get("check") or "").strip()
    )


def splice(text: str, block: str) -> str | None:
    """Replace the marked block; None when a marker is missing or misordered."""
    ib, ie = text.find(BEGIN), text.find(END)
    if ib < 0 or ie < 0 or ie < ib:
        return None
    return text[:ib] + BEGIN + "\n" + block + END + text[ie + len(END) :]


def render(rows: list[dict], target: str) -> str:
    return "".join(f"- {r['text']}\n" for r in rows if r.get("origin_target") == target)


def generate(path, rows: list[dict], target: str, check: bool = False) -> int:
    p = pathlib.Path(path)
    try:
        text = p.read_text()
    except OSError:
        print(f"rules: generate: cannot read {path}", file=sys.stderr)
        return 1
    new = splice(text, render(rows, target))
    if new is None:
        print(
            f"rules: generate: {path}: missing markers {BEGIN} … {END}", file=sys.stderr
        )
        return 1
    if check:
        if new == text:
            return 0
        sys.stdout.writelines(
            difflib.unified_diff(
                text.splitlines(True),
                new.splitlines(True),
                f"{path} (file)",
                f"{path} (ledger)",
            )
        )
        return 1
    p.write_text(new)
    return 0


def unresolved_sources(rows: list[dict], repo_root=None) -> list[str]:
    """Source files that could not be resolved (warnings, never errors)."""
    root = pathlib.Path(repo_root) if repo_root else None
    out: list[str] = []
    for r in rows:
        src = str(r.get("source", ""))
        path, _line = _source_parts(src)
        if path is None:
            continue
        if not _resolve(path, root).exists():
            out.append(f"rules: {r.get('id', '<no id>')}: source not found at {src}")
    return out


def verbatim_errors(rows: list[dict], repo_root=None) -> list[str]:
    """Rows whose ``text`` is not byte-for-byte in a resolvable ``source``.

    Unresolvable sources are skipped here (they stay warnings via
    ``unresolved_sources``), so a partial checkout does not fail the verbatim pass
    on rows it cannot read — but every repo-local row is held to the byte.
    """
    root = pathlib.Path(repo_root) if repo_root else None
    out: list[str] = []
    for r in rows:
        rid = str(r.get("id", "<no id>"))
        src = str(r.get("source", ""))
        path, line = _source_parts(src)
        if path is None:
            continue
        resolved = _resolve(path, root)
        if not resolved.exists():
            continue
        try:
            content = resolved.read_text(errors="ignore")
        except OSError:
            continue
        text = str(r.get("text", ""))
        if _flat(text) not in _flat(content):
            diff = _first_diff_char(_flat(text), _flat(content))
            out.append(
                f"rules: {rid}: text is not byte-for-byte in {path} (near line {line}); "
                f"first differing character {diff!r}"
            )
    return out


def validate(rows: list[dict], repo_root=None, verbatim=False) -> list[str]:
    errs: list[str] = []
    seen: set[str] = set()
    root = pathlib.Path(repo_root) if repo_root else None
    for r in rows:
        rid = str(r.get("id", "<no id>"))

        def say(msg, rid=rid):
            errs.append(f"rules: {rid}: {msg}")

        for key in FIELDS:
            if key not in r:
                say(f"missing {key}")
        if not ID_RE.match(rid):
            say("id must match ^R-[a-z0-9][a-z0-9-]*$")
        if rid in seen:
            say("duplicate id")
        seen.add(rid)
        if r.get("class") not in CLASSES:
            say(f"class must be one of {', '.join(CLASSES)}")
        if r.get("verdict") not in VERDICTS:
            say("verdict must be one of '', keep, amend, retire")
        if "origin_target" in r and r.get("origin_target") not in TARGETS:
            say(f"origin_target must be one of {', '.join(TARGETS)}")
        if not isinstance(r.get("load_bearing"), bool):
            say("load_bearing must be a bool")
        origin = r.get("origin")
        if not isinstance(origin, str) or not ORIGIN_RE.match(origin):
            say("origin must be a YYYY-MM-DD date")
        src = r.get("source")
        if not isinstance(src, str) or not src:
            say("source must be path:line")
            continue
        path, line = _source_parts(src)
        if path is None or line is None:
            say("source must be path:line")
            continue
        resolved = _resolve(path, root)
        if resolved.exists():
            try:
                content = resolved.read_text(errors="ignore").splitlines()
            except OSError:
                say(f"source unreadable: {path}")
                continue
            if (
                line < 1
                or line > len(content)
                or not _word_in(str(r.get("text", "")), content[line - 1])
            ):
                say("source line does not contain the rule text")
    if verbatim:
        errs.extend(verbatim_errors(rows, repo_root=root))
    return errs


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="rules")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("file")
    v.add_argument("--root", default=None)
    v.add_argument("--verbatim", action="store_true")
    g = sub.add_parser("generate")
    g.add_argument("file")
    g.add_argument("--target", choices=TARGETS, default="claude")
    g.add_argument("--out", required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--root", default=None)
    a = p.parse_args(argv)
    rows = load(a.file)
    root = a.root or str(pathlib.Path(a.file).resolve().parents[2])
    if a.cmd == "generate":
        # --root is accepted for symmetry with validate (the ledger path and
        # --out are both taken relative to the caller's cwd); the drift check
        # itself needs no root.
        return generate(a.out, rows, a.target, check=a.check)
    errs = validate(rows, repo_root=root, verbatim=a.verbatim)
    for e in errs:
        print(e, file=sys.stderr)
    for w in unresolved_sources(rows, repo_root=root):
        print(w, file=sys.stderr)
    print(f"owed: {owed(rows)} load-bearing rules without a check")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
