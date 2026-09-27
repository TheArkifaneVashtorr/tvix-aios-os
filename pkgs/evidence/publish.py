"""The publish manifest validator (plan 2026-09-21-publish-gate, PG1; spec
docs/superpowers/specs/2026-09-21-publish-gate-design.md §4–§6, brief §3.7).

`docs/ledger/publish.toml` classifies every tracked path as `publish` or
`withhold` (fnmatch globs: `*` spans `/`, no `**`, the CLASS_GLOB_RE
character set), names the `pending` paths (exact tracked paths that classify
`publish` and still carry a deny match — public by intent, counted, never
exported) and carries the `[deny]` table: `literals` (exact bytes), `words`
(word-bounded, case-sensitive), `patterns` (regex).

`validate <manifest> --tree <dir> [--files <list>]` runs four arms over the
universe (`--files`; else `git ls-files` when `<dir>/.git` exists; else a walk
of `<dir>` that never enters `.git`): 1 classification — `unclassified <p>`,
`ambiguous <p> publish,withhold`, and the manifest's own tree-relative path
must classify withhold (`manifest-not-withheld <p> <list>`); 2 deny scan over
every published, non-pending path — `<p>:<line> <list>[<i>]`, the rule id and
never the matched text; 3 pending — `pending-missing`, `pending-not-public`,
`stale-pending`; 4 counts — `published N withheld N pending N`, always the
last stdout line (published = publish-classified minus pending).

Exit 0 with only the counts line; exit 1 with the defect lines (arm order, each
arm sorted) then the counts line and one stderr line naming brief §3.7; exit 2
with one `publish: <reason>` line on stderr and nothing on stdout when the
manifest or the tree is unusable. The only import from `tasks` is
CLASS_GLOB_RE — no matcher is copied (subsystems.py's shape).

`export-list <manifest> --tree <dir> [--files <list>]` runs the same four
arms; exit 0 prints every published path (publish-classified minus pending)
sorted, and nothing else; exits 1 and 2 are `validate`'s, byte for byte — a
red tree yields no list.

`export <manifest> --tree <dir> --out <dir> [--files <list>]` (spec §5, the
phase-2 contract PL24 builds) runs the same four arms first: on any defect
the report is `validate`'s and NOTHING is written — not even the `--out`
directory — so a red tree can never leave a partial export behind. On a
clean tree `prepare_out` gates `--out` (refused when it exists and is not
an empty directory), then exactly the published paths are copied into it
with `shutil.copy2` (data and mode bits), parents created as needed, and
nothing else — no `.git`, no marker file.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import pathlib
import re
import shutil
import subprocess
import sys

import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tasks import CLASS_GLOB_RE

LISTS = ("publish", "withhold", "pending")
DENY = ("literals", "words", "patterns")
GLOB_LISTS = ("publish", "withhold")


class ManifestError(Exception):
    """A manifest or tree the validator cannot use (exit 2)."""


def _str_list(table: dict, key: str, where: str) -> list[str]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ManifestError(f"{where}.{key} must be a list of strings")
    return value


def load_manifest(path: str) -> dict:
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as e:
        raise ManifestError(f"cannot read {path}: {e.strerror}") from e
    except tomllib.TOMLDecodeError as e:
        raise ManifestError(f"{path}: not valid TOML: {e}") from e
    unknown = set(data) - set(LISTS) - {"deny"}
    if unknown:
        raise ManifestError(f"unknown top-level key(s): {', '.join(sorted(unknown))}")
    out: dict = {name: _str_list(data, name, "manifest") for name in LISTS}
    for name in GLOB_LISTS:
        for glob in out[name]:
            if "**" in glob or CLASS_GLOB_RE.match(glob) is None:
                raise ManifestError(f"{name}: bad glob {glob!r}")
    for p in out["pending"]:
        if any(ch in p for ch in "*?["):
            raise ManifestError(f"pending: {p!r} must be an exact path, not a glob")
    deny = data.get("deny", {})
    if not isinstance(deny, dict):
        raise ManifestError("deny must be a table")
    unknown = set(deny) - set(DENY)
    if unknown:
        raise ManifestError(f"deny: unknown key(s): {', '.join(sorted(unknown))}")
    out["deny"] = {name: _str_list(deny, name, "deny") for name in DENY}
    rules = []
    for i, lit in enumerate(out["deny"]["literals"]):
        rules.append((f"literals[{i}]", re.compile(re.escape(lit.encode()))))
    for i, word in enumerate(out["deny"]["words"]):
        rules.append(
            (f"words[{i}]", re.compile(rb"\b" + re.escape(word.encode()) + rb"\b"))
        )
    for i, pat in enumerate(out["deny"]["patterns"]):
        try:
            rules.append((f"patterns[{i}]", re.compile(pat.encode())))
        except re.error as e:
            raise ManifestError(f"deny.patterns[{i}]: invalid regex: {e}") from e
    out["rules"] = rules
    return out


def universe(tree: str, files: str | None) -> list[str]:
    if files is not None:
        try:
            text = pathlib.Path(files).read_text()
        except OSError as e:
            raise ManifestError(f"cannot read --files {files}: {e.strerror}") from e
        return sorted({ln for ln in text.splitlines() if ln})
    if os.path.exists(os.path.join(tree, ".git")):
        res = subprocess.run(
            ["git", "-C", tree, "ls-files", "-z"], capture_output=True, check=False
        )
        if res.returncode != 0:
            raise ManifestError(f"git ls-files failed in {tree}")
        return sorted({p.decode() for p in res.stdout.split(b"\0") if p})
    out = []
    for root, dirs, names in os.walk(tree):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for n in names:
            out.append(os.path.relpath(os.path.join(root, n), tree))
    return sorted(out)


def classify(path: str, manifest: dict) -> list[str]:
    return [
        name
        for name in GLOB_LISTS
        if any(fnmatch.fnmatch(path, g) for g in manifest[name])
    ]


def scan(data: bytes, rules) -> list[tuple[int, str]]:
    hits = set()
    for rule_id, rx in rules:
        for m in rx.finditer(data):
            hits.add((data.count(b"\n", 0, m.start()) + 1, rule_id))
    return sorted(hits)


def _run(manifest_path: str, tree: str, files: str | None):
    manifest = load_manifest(manifest_path)
    if not os.path.isdir(tree):
        raise ManifestError(f"no such tree: {tree}")
    own = os.path.relpath(os.path.realpath(manifest_path), os.path.realpath(tree))
    if own.startswith(".."):
        raise ManifestError(
            f"the manifest {manifest_path} must lie inside --tree {tree}"
        )
    paths = universe(tree, files)
    arm1, arm2, arm3 = [], [], []
    publish, withhold = [], []
    for p in paths:
        lists = classify(p, manifest)
        if not lists:
            arm1.append(f"unclassified {p}")
        elif len(lists) > 1:
            arm1.append(f"ambiguous {p} {','.join(lists)}")
        elif lists == ["publish"]:
            publish.append(p)
        else:
            withhold.append(p)
    own_lists = classify(own, manifest)
    if own_lists != ["withhold"]:
        what = (
            own_lists[0]
            if len(own_lists) == 1
            else ("ambiguous" if own_lists else "unclassified")
        )
        arm1.append(f"manifest-not-withheld {own} {what}")
    pending = set(manifest["pending"])
    publish_set = set(publish)
    path_set = set(paths)
    for p in sorted(pending):
        if p not in path_set:
            arm3.append(f"pending-missing {p}")
        elif p not in publish_set:
            arm3.append(f"pending-not-public {p}")
    for p in publish:
        if p == own:
            continue  # the manifest holds the deny values and is never scanned
        try:
            data = pathlib.Path(tree, p).read_bytes()
        except OSError as e:
            raise ManifestError(f"cannot read {p}: {e.strerror}") from e
        hits = scan(data, manifest["rules"])
        if p in pending:
            if not hits:
                arm3.append(f"stale-pending {p}")
            continue
        arm2.extend(f"{p}:{line} {rule_id}" for line, rule_id in hits)
    counts = (len(publish_set - pending), len(withhold), len(pending & publish_set))
    return sorted(arm1) + arm2 + sorted(arm3), counts, sorted(publish_set - pending)


def validate(manifest_path: str, tree: str, files: str | None):
    defects, counts, _published = _run(manifest_path, tree, files)
    return defects, counts


def export_list(manifest_path: str, tree: str, files: str | None):
    """The export's dry run (spec §5 `export`, phase 2; plan
    2026-09-22-tvix-aios-step1, OS1): `validate`'s defects and counts, and the
    published paths — publish-classified minus pending — sorted in byte order,
    or `[]` whenever there is any defect: a red gate yields no export at all."""
    defects, counts, published = _run(manifest_path, tree, files)
    return defects, counts, ([] if defects else published)


def prepare_out(out: str) -> None:
    """Decide whether `--out` may hold the export, before anything is
    copied (PL24, spec §5): refused when it exists and is not a directory,
    or exists and is a non-empty directory; created when absent; accepted
    when present and empty. The tool never distinguishes "a directory an
    earlier invocation of this tool created" from "an empty directory that
    existed for any other reason" — the two are indistinguishable from the
    filesystem alone and treating them alike is strictly safer, and no
    marker file is written into `--out` (spec §5: export creates nothing
    else there)."""
    if os.path.lexists(out):
        if not os.path.isdir(out):
            raise ManifestError(f"--out {out} exists and is not a directory")
        if os.listdir(out):
            raise ManifestError(f"--out {out} exists and is not empty")
    else:
        os.makedirs(out)


def export(manifest_path: str, tree: str, out: str, files: str | None):
    """Spec §5 `export` (PL24): `validate` first — on any defect the report
    is returned untouched and nothing is written, not even the `--out`
    directory itself; on a clean tree `prepare_out` gates `--out`, then
    exactly the published paths (publish-classified minus pending) are
    copied byte for byte, mode bits included, parents created as needed."""
    defects, counts, published = export_list(manifest_path, tree, files)
    if defects:
        return defects, counts
    prepare_out(out)
    for p in published:
        dest = os.path.join(out, p)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(os.path.join(tree, p), dest)
    return defects, counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="publish")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, help_ in (
        ("validate", "classify every path, scan the published ones, count"),
        (
            "export-list",
            "validate, then print every published path (the export's dry run)",
        ),
        (
            "export",
            "validate, then copy the published paths byte for byte into --out",
        ),
    ):
        p = sub.add_parser(name, help=help_)
        p.add_argument("manifest")
        p.add_argument("--tree", required=True)
        p.add_argument("--files", default=None)
        if name == "export":
            p.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "export":
            defects, (published, withheld, pending) = export(
                args.manifest, args.tree, args.out, args.files
            )
        else:
            defects, (published, withheld, pending), paths = export_list(
                args.manifest, args.tree, args.files
            )
    except ManifestError as e:
        print(f"publish: {e}", file=sys.stderr)
        return 2
    if args.cmd == "export-list" and not defects:
        for path in paths:
            print(path)
        return 0
    for line in defects:
        print(line)
    print(f"published {published} withheld {withheld} pending {pending}")
    if defects:
        print(
            "publish: the tree fails the publish gate (brief §3.7): the lines above",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
