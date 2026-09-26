#!/usr/bin/env python3
"""media-fetch-models: download the models named in models/manifest.toml
through whatever HTTP(S) proxy the environment names (the egress broker, in
production), verify each file's sha256 while streaming it, and move it into
place atomically. Refuses to overwrite an existing file whose content
doesn't match the manifest, and refuses to fetch an entry whose sha256 is
the literal string "UNVERIFIED" (a hash the implementer could not confirm
from the model's source page and marked accordingly rather than guessing).

Stdlib only — no third-party dependencies, per the flake's Python policy.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import shutil
import ssl
import sys
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable

CHUNK_SIZE = 1024 * 1024  # 1 MiB


def load_manifest(path: pathlib.Path) -> list[dict]:
    """Parse models/manifest.toml into a list of model dicts (the `[[model]]`
    array-of-tables). Each entry carries name, url, sha256, dest, size,
    license, gated, enabled."""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data.get("model", [])


def proxy_from_env() -> dict:
    """The proxy map urllib would use, straight from HTTP(S)_PROXY /
    NO_PROXY — exposed separately from build_opener so tests can assert on
    it directly."""
    return urllib.request.getproxies()


def build_opener(cafile: str | None):
    """A urllib opener that honours the environment's proxy settings and,
    when given a CA bundle (the broker's, in production), verifies TLS
    against it instead of the system trust store."""
    proxies = proxy_from_env()
    context = (
        ssl.create_default_context(cafile=cafile)
        if cafile
        else ssl.create_default_context()
    )
    return urllib.request.build_opener(
        urllib.request.ProxyHandler(proxies),
        urllib.request.HTTPSHandler(context=context),
    )


def open_url(url: str, cafile: str | None):
    """Open `url` for streaming reads via build_opener(cafile). Tests
    monkeypatch this directly to avoid any real network access."""
    opener = build_opener(cafile)
    return opener.open(url, timeout=60)


def _sha256_file(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def fetch_one(
    m: dict,
    dest_root: pathlib.Path,
    cafile: str | None,
    log: Callable[[str], None] = print,
    reverify: bool = False,
) -> str:
    """Fetch one manifest entry into dest_root/<dest>. Returns "OK" (fetched
    and hash-verified, or — with reverify=True — already present and
    re-hashed against the manifest), "SKIP" (disabled, or already present
    with the manifest's hash and reverify=False), or "FAIL" (any error — the
    destination is left untouched: no partial file, no clobbered existing
    file).

    With reverify=True, a present file is always re-hashed against the
    manifest rather than trusted on sight: a match reports OK (not SKIP) so
    the caller can tell "verified now" from "never checked", and a mismatch
    still reports FAIL exactly as the non-reverify path does — this is the
    case reverify exists to catch (bit-rot, a truncated prior download)."""
    name = m["name"]

    if not m.get("enabled", True):
        log(f"media-fetch: SKIP {name} disabled")
        return "SKIP"

    expected = m["sha256"]
    if expected == "UNVERIFIED":
        log(
            f"media-fetch: FAIL {name} sha256 is UNVERIFIED in the manifest "
            "— refusing to fetch an unverified hash"
        )
        return "FAIL"

    dest_path = dest_root / m["dest"]
    if dest_path.exists():
        if _sha256_file(dest_path) == expected:
            if reverify:
                log(f"media-fetch: OK {name} {expected[:12]} (reverified)")
                return "OK"
            log(f"media-fetch: SKIP {name} present")
            return "SKIP"
        log(
            f"media-fetch: FAIL {name} destination {dest_path} exists with "
            "a different hash than the manifest; refusing to overwrite"
        )
        return "FAIL"

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest_path.with_name(dest_path.name + ".part")

    try:
        src = open_url(m["url"], cafile)
    except urllib.error.HTTPError as e:
        if e.code == 401 and m.get("gated"):
            reason = (
                "HTTP 401 (gated model — set services.comfyui.models.hfTokenFile "
                "to a Hugging Face token file so the broker can inject it)"
            )
        else:
            reason = f"HTTP {e.code} {e.reason}"
        log(f"media-fetch: FAIL {name} {reason}")
        return "FAIL"
    except (urllib.error.URLError, OSError) as e:
        log(f"media-fetch: FAIL {name} {e}")
        return "FAIL"

    try:
        with src, open(part_path, "wb") as out:
            hasher = hashlib.sha256()
            while True:
                chunk = src.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
                out.write(chunk)
    except (urllib.error.URLError, OSError) as e:
        part_path.unlink(missing_ok=True)
        log(f"media-fetch: FAIL {name} {e}")
        return "FAIL"

    digest = hasher.hexdigest()
    if digest != expected:
        part_path.unlink(missing_ok=True)
        log(
            f"media-fetch: FAIL {name} sha256 mismatch: got {digest[:12]}, "
            f"expected {expected[:12]}"
        )
        return "FAIL"

    os.replace(part_path, dest_path)
    log(f"media-fetch: OK {name} {digest[:12]}")
    return "OK"


def store_path(store: pathlib.Path, m: dict) -> pathlib.Path:
    return store / m["sha256"] / pathlib.PurePosixPath(m["dest"]).name


def link_entry(world_models: pathlib.Path, m: dict, target: pathlib.Path, log) -> str:
    """Make world_models/<dest> a RELATIVE symlink to target. A correct link is
    left alone; a wrong link is replaced; a regular file is never replaced."""
    link = world_models / m["dest"]
    link.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(target, link.parent)
    if link.is_symlink():
        if os.readlink(link) == rel:
            return "OK"
        link.unlink()
    elif link.exists():
        log(
            f"media-fetch: FAIL {m['name']} {link} is a regular file, not a link — move it aside"
        )
        return "FAIL"
    os.symlink(rel, link)
    return "OK"


def place_one(m, store, world_models, cafile, log=print, reverify=False) -> str:
    """Store-mode fetch_one: the file lives in the store, the world gets a link."""
    if not m.get("enabled", True):
        log(f"media-fetch: SKIP {m['name']} disabled")
        return "SKIP"
    target = store_path(store, m)
    if not m.get("url"):
        if not target.exists():
            log(
                f"media-fetch: FAIL {m['name']} adopted entry has no url and {target} is missing"
            )
            return "FAIL"
        result = "OK"
    else:
        # fetch_one writes dest_root/<dest>; point it at the store cell with a
        # single-segment dest so the existing verify-while-streaming path is reused.
        cell = dict(m, dest=target.name)
        result = fetch_one(cell, target.parent, cafile, log=log, reverify=reverify)
        if result == "FAIL":
            return result
    return "FAIL" if link_entry(world_models, m, target, log) == "FAIL" else result


def adopt_dir(src, store, world_models, manifest_out, log=print) -> int:
    """Move every regular file under src into the store by hash, link it from
    world_models at the same relative path, write manifest_out. Refuses when
    manifest_out exists. Returns 0, or 1 on refusal / any failure."""
    if pathlib.Path(manifest_out).exists():
        log(f"media-fetch: FAIL {manifest_out} exists; adopt writes a fresh manifest")
        return 1
    entries = []
    for path in sorted(
        p for p in pathlib.Path(src).rglob("*") if p.is_file() and not p.is_symlink()
    ):
        rel = path.relative_to(src).as_posix()
        digest = _sha256_file(path)
        cell = pathlib.Path(store) / digest / path.name
        cell.parent.mkdir(parents=True, exist_ok=True)
        if cell.exists() and _sha256_file(cell) != digest:
            log(f"media-fetch: FAIL {rel}: store cell {cell} holds different bytes")
            return 1
        if not cell.exists():
            shutil.move(str(path), str(cell))
        else:
            path.unlink()
        m = {
            "name": path.stem,
            "sha256": digest,
            "dest": rel,
            "size": cell.stat().st_size,
            "source": "adopted",
            "enabled": True,
        }
        if link_entry(pathlib.Path(world_models), m, cell, log) == "FAIL":
            return 1
        entries.append(m)
        log(f"ADOPT {rel} -> {digest[:12]}")
    lines = [
        "# models of this world — written by media-fetch-models --adopt-from; edit by hand or by the fetcher",
        "",
    ]
    for m in entries:
        lines += [
            "[[model]]",
            f'name = "{m["name"]}"',
            f'sha256 = "{m["sha256"]}"',
            f'dest = "{m["dest"]}"',
            f"size = {m['size']}",
            'source = "adopted"',
            "enabled = true",
            "",
        ]
    pathlib.Path(manifest_out).write_text("\n".join(lines))
    return 0


def _refuse_unknown_only(only: set[str] | None, models: list[dict]) -> bool:
    """Print and return True when `only` names anything outside the
    manifest's *enabled* rows. A name that resolves only to a disabled entry
    must refuse loudly (like a typo) rather than silently fetching nothing
    at exit 0 -- "unknown" is computed against enabled rows, not every row,
    so a disabled row's name is never mistaken for a valid target."""
    if only is None:
        return False
    enabled = {m["name"] for m in models if m.get("enabled", True)}
    unknown = only - enabled
    if unknown:
        print(
            "media-fetch: unknown --only name(s): " + ", ".join(sorted(unknown)),
            file=sys.stderr,
        )
        return True
    return False


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="media-fetch-models")
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--dest", type=pathlib.Path)
    parser.add_argument("--store", type=pathlib.Path)
    parser.add_argument("--link-into", type=pathlib.Path)
    parser.add_argument("--adopt-from", type=pathlib.Path)
    parser.add_argument("--manifest-out", type=pathlib.Path)
    parser.add_argument("--only", action="append", default=None, metavar="NAME")
    parser.add_argument("--cafile", default=None)
    parser.add_argument(
        "--reverify",
        action="store_true",
        help=(
            "Re-hash files already present against the manifest instead of "
            "trusting their existence (reports OK/FAIL instead of SKIP for "
            "them); never touches the network for a file that is present."
        ),
    )
    args = parser.parse_args(argv)

    if args.adopt_from is not None:
        if args.store is None or args.link_into is None or args.manifest_out is None:
            parser.error(
                "--adopt-from requires --store, --link-into and --manifest-out"
            )
        if args.only is not None:
            parser.error("--only cannot be combined with --adopt-from")
        return adopt_dir(args.adopt_from, args.store, args.link_into, args.manifest_out)

    if args.store is not None or args.link_into is not None:
        if args.store is None or args.link_into is None:
            parser.error("--store and --link-into must be used together")
        if args.dest is not None:
            parser.error("--dest cannot be combined with --store/--link-into")
        if args.manifest is None:
            parser.error("--manifest is required with --store/--link-into")

        models = load_manifest(args.manifest)
        only = set(args.only) if args.only else None
        if _refuse_unknown_only(only, models):
            return 1

        failed = False
        for m in models:
            if only is not None and m["name"] not in only:
                continue
            result = place_one(
                m, args.store, args.link_into, args.cafile, reverify=args.reverify
            )
            if result == "FAIL":
                failed = True

        return 1 if failed else 0

    if args.dest is None:
        parser.error("--dest (or --store and --link-into) is required")
    if args.manifest is None:
        parser.error("--manifest is required")

    models = load_manifest(args.manifest)
    only = set(args.only) if args.only else None
    if _refuse_unknown_only(only, models):
        return 1

    failed = False
    for m in models:
        if only is not None and m["name"] not in only:
            continue
        result = fetch_one(m, args.dest, args.cafile, reverify=args.reverify)
        if result == "FAIL":
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
