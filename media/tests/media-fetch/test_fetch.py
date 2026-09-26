"""Unit tests for pkgs/media-fetch/fetch.py.

Loaded by path (like nixos-agent-env's tests/helm/test_collect.py) so this
test file works both under `pytest tests/media-fetch` from the repo root and
inside the checks.media-fetch-unit sandbox, which copies pkgs/media-fetch
and tests/media-fetch into a fresh tree without installing anything.
"""

import hashlib
import importlib.util
import io
import os
import pathlib
import urllib.error


class FakeOpener:
    """Module-level url -> bytes opener for the store-mode tests; fetch.open_url
    calls build_opener(cafile).open(url, timeout=...)."""

    def __init__(self, payloads):
        self.payloads = payloads

    def open(self, url, timeout=None):
        return io.BytesIO(self.payloads[url])


HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "media-fetch" / "fetch.py"
spec = importlib.util.spec_from_file_location("fetch", SRC)
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


def test_manifest_parses(tmp_path):
    p = tmp_path / "m.toml"
    p.write_text(
        '[[model]]\nname="a"\nurl="https://x/a.bin"\nsha256="'
        + "0" * 64
        + '"\ndest="ckpt/a.bin"\nsize=3\nlicense="MIT"\ngated=false\nenabled=true\n'
    )
    assert fetch.load_manifest(p)[0]["dest"] == "ckpt/a.bin"


def test_fetch_ok_and_skip(monkeypatch, tmp_path):
    data = b"abc"
    sha = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(fetch, "open_url", lambda url, cafile: io.BytesIO(data))
    m = {
        "name": "a",
        "url": "https://x/a",
        "sha256": sha,
        "dest": "ckpt/a.bin",
        "size": 3,
        "gated": False,
        "enabled": True,
    }
    assert fetch.fetch_one(m, tmp_path, None, log=lambda s: None) == "OK"
    assert (tmp_path / "ckpt/a.bin").read_bytes() == data
    assert fetch.fetch_one(m, tmp_path, None, log=lambda s: None) == "SKIP"


def test_fetch_wrong_hash_fails_and_leaves_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch, "open_url", lambda url, cafile: io.BytesIO(b"abc"))
    m = {
        "name": "a",
        "url": "u",
        "sha256": "f" * 64,
        "dest": "a.bin",
        "size": 3,
        "gated": False,
        "enabled": True,
    }
    assert fetch.fetch_one(m, tmp_path, None, log=lambda s: None) == "FAIL"
    assert not (tmp_path / "a.bin").exists() and not list(tmp_path.glob("*.part"))


def test_refuses_to_overwrite_different_existing(monkeypatch, tmp_path):
    (tmp_path / "a.bin").write_bytes(b"other")
    monkeypatch.setattr(fetch, "open_url", lambda url, cafile: io.BytesIO(b"abc"))
    m = {
        "name": "a",
        "url": "u",
        "sha256": hashlib.sha256(b"abc").hexdigest(),
        "dest": "a.bin",
        "size": 3,
        "gated": False,
        "enabled": True,
    }
    assert fetch.fetch_one(m, tmp_path, None, log=lambda s: None) == "FAIL"
    assert (tmp_path / "a.bin").read_bytes() == b"other"


def test_401_is_clear_fail(monkeypatch, tmp_path):
    def boom(url, cafile):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(fetch, "open_url", boom)
    logs = []
    m = {
        "name": "g",
        "url": "u",
        "sha256": "0" * 64,
        "dest": "g.bin",
        "size": 1,
        "gated": True,
        "enabled": True,
    }
    assert fetch.fetch_one(m, tmp_path, None, log=logs.append) == "FAIL"
    assert any("401" in line and "gated" in line for line in logs)


def test_proxy_env_reaches_opener(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://10.100.2.1:3130")
    seen = {}

    class FakeOpener:
        def open(self, url, timeout=None):
            seen["url"] = url
            return io.BytesIO(b"")

    monkeypatch.setattr(
        fetch,
        "build_opener",
        lambda cafile: (
            seen.__setitem__("proxy", fetch.proxy_from_env()),
            FakeOpener(),
        )[1],
    )
    fetch.open_url("https://huggingface.co/x", None)
    assert (
        seen["proxy"] == {"https": "http://10.100.2.1:3130"}
        and seen["url"] == "https://huggingface.co/x"
    )


def test_reverify_rehashes_present_file_and_reports_ok(monkeypatch, tmp_path):
    """--reverify (fetch_one(..., reverify=True)) must re-hash a file that
    is already present against the manifest and report OK, not the plain
    SKIP a non-reverify run gives — proving it actually re-hashed rather
    than trusting the file's mere existence. The network is never touched
    (open_url stays unset/would raise if called): the file is already on
    disk with the right content."""
    data = b"abc"
    sha = hashlib.sha256(data).hexdigest()
    (tmp_path / "ckpt").mkdir()
    (tmp_path / "ckpt/a.bin").write_bytes(data)

    def boom(url, cafile):
        raise AssertionError(
            "reverify of a present, correct file must not hit the network"
        )

    monkeypatch.setattr(fetch, "open_url", boom)
    m = {
        "name": "a",
        "url": "https://x/a",
        "sha256": sha,
        "dest": "ckpt/a.bin",
        "size": 3,
        "gated": False,
        "enabled": True,
    }
    logs = []
    assert fetch.fetch_one(m, tmp_path, None, log=logs.append, reverify=True) == "OK"
    assert any("OK" in line and "a" in line for line in logs)
    assert not any(line.startswith("media-fetch: SKIP") for line in logs)


def test_reverify_still_fails_on_corrupted_present_file(monkeypatch, tmp_path):
    """A present file whose bytes no longer match the manifest hash must
    still FAIL under --reverify (this is the case --reverify exists to
    catch: bit-rot or a truncated prior download that a plain run's
    existence check alone would have accepted as SKIP)."""
    (tmp_path / "a.bin").write_bytes(b"corrupted")
    m = {
        "name": "a",
        "url": "u",
        "sha256": hashlib.sha256(b"abc").hexdigest(),
        "dest": "a.bin",
        "size": 3,
        "gated": False,
        "enabled": True,
    }
    assert (
        fetch.fetch_one(m, tmp_path, None, log=lambda s: None, reverify=True) == "FAIL"
    )


def test_unverified_hash_is_rejected(monkeypatch, tmp_path):
    m = {
        "name": "u",
        "url": "u",
        "sha256": "UNVERIFIED",
        "dest": "u.bin",
        "size": 1,
        "gated": False,
        "enabled": True,
    }
    assert fetch.fetch_one(m, tmp_path, None, log=lambda s: None) == "FAIL"


def test_place_one_fetches_into_store_and_links_relative(monkeypatch, tmp_path):
    payload = b"model-bytes"
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(
        fetch,
        "build_opener",
        lambda cafile: FakeOpener({"https://x/a.safetensors": payload}),
    )
    store = tmp_path / "store"
    world = tmp_path / "worlds" / "sfw" / "models"
    m = {
        "name": "a",
        "url": "https://x/a.safetensors",
        "sha256": digest,
        "dest": "checkpoints/a.safetensors",
        "enabled": True,
    }
    assert fetch.place_one(m, store, world, None, log=lambda s: None) == "OK"
    target = store / digest / "a.safetensors"
    link = world / "checkpoints" / "a.safetensors"
    assert target.read_bytes() == payload
    assert (
        link.is_symlink()
        and os.readlink(link) == "../../../../store/" + digest + "/a.safetensors"
    )
    assert link.resolve() == target.resolve()
    assert fetch.place_one(m, store, world, None, log=lambda s: None) == "SKIP"


def test_adopted_entry_without_url_needs_the_store_file(tmp_path):
    store = tmp_path / "store"
    world = tmp_path / "w" / "models"
    m = {
        "name": "b",
        "sha256": "0" * 64,
        "dest": "loras/b.safetensors",
        "source": "adopted",
        "enabled": True,
    }
    assert fetch.place_one(m, store, world, None, log=lambda s: None) == "FAIL"
    (store / ("0" * 64)).mkdir(parents=True)
    (store / ("0" * 64) / "b.safetensors").write_bytes(b"x")
    assert fetch.place_one(m, store, world, None, log=lambda s: None) == "OK"
    assert (world / "loras" / "b.safetensors").is_symlink()


def test_link_never_replaces_a_regular_file(tmp_path):
    store = tmp_path / "store"
    world = tmp_path / "w" / "models"
    (store / ("1" * 64)).mkdir(parents=True)
    (store / ("1" * 64) / "c.bin").write_bytes(b"c")
    (world / "vae").mkdir(parents=True)
    (world / "vae" / "c.bin").write_bytes(b"old")
    m = {
        "name": "c",
        "sha256": "1" * 64,
        "dest": "vae/c.bin",
        "source": "adopted",
        "enabled": True,
    }
    assert fetch.place_one(m, store, world, None, log=lambda s: None) == "FAIL"
    assert (world / "vae" / "c.bin").read_bytes() == b"old"


def test_only_unknown_name_fails_closed(tmp_path, capsys):
    """A typo in --only must not silently fetch nothing with exit 0 — main()
    must refuse before any fetch is attempted when a --only name is not in
    the manifest, printing the offending name(s) to stderr."""
    manifest = tmp_path / "m.toml"
    manifest.write_text(
        '[[model]]\nname="krea2-vae"\nurl="https://x/a.bin"\nsha256="'
        + "0" * 64
        + '"\ndest="vae/a.bin"\nsize=3\nlicense="MIT"\ngated=false\nenabled=true\n'
    )
    dest = tmp_path / "out"
    rc = fetch.main(
        [
            "--manifest",
            str(manifest),
            "--dest",
            str(dest),
            "--only",
            "krea2-vaeX",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "media-fetch: unknown --only name(s):" in err and "krea2-vaeX" in err
    assert not dest.exists()


def test_only_disabled_row_refused(tmp_path, capsys):
    """A --only name that names a real but *disabled* manifest row must
    refuse exactly like an unknown name (exit 1, the name on stderr), not
    silently fetch nothing at exit 0 — "unknown" is computed against the
    manifest's enabled rows, never every row."""
    manifest = tmp_path / "m.toml"
    manifest.write_text(
        '[[model]]\nname="krea2-vae"\nurl="https://x/a.bin"\nsha256="'
        + "0" * 64
        + '"\ndest="vae/a.bin"\nsize=3\nlicense="MIT"\ngated=false\nenabled=false\n'
    )
    dest = tmp_path / "out"
    rc = fetch.main(
        [
            "--manifest",
            str(manifest),
            "--dest",
            str(dest),
            "--only",
            "krea2-vae",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "media-fetch: unknown --only name(s):" in err and "krea2-vae" in err
    assert not dest.exists()


def test_only_disabled_row_refused_store_mode(tmp_path, capsys):
    """The --store/--link-into path shares the same refusal as --dest."""
    manifest = tmp_path / "m.toml"
    manifest.write_text(
        '[[model]]\nname="krea2-vae"\nurl="https://x/a.bin"\nsha256="'
        + "0" * 64
        + '"\ndest="vae/a.bin"\nsize=3\nlicense="MIT"\ngated=false\nenabled=false\n'
    )
    store = tmp_path / "store"
    world = tmp_path / "w" / "models"
    rc = fetch.main(
        [
            "--manifest",
            str(manifest),
            "--store",
            str(store),
            "--link-into",
            str(world),
            "--only",
            "krea2-vae",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "media-fetch: unknown --only name(s):" in err and "krea2-vae" in err
    assert not store.exists() and not world.exists()


def test_only_with_adopt_from_is_refused(tmp_path, capsys):
    """`--adopt-from` writes a fresh manifest from the files it finds, so a
    `--only` name has nothing to resolve against — the combination is refused
    (exit 2, like the other bad flag pairs) rather than silently ignored while
    everything under the source directory is adopted anyway."""
    src = tmp_path / "models"
    (src / "vae").mkdir(parents=True)
    (src / "vae" / "a.bin").write_bytes(b"a")
    store = tmp_path / "store"
    world = tmp_path / "w" / "models"
    out = tmp_path / "out.toml"
    try:
        fetch.main(
            [
                "--adopt-from",
                str(src),
                "--store",
                str(store),
                "--link-into",
                str(world),
                "--manifest-out",
                str(out),
                "--only",
                "a",
            ]
        )
        raise AssertionError("expected SystemExit from parser.error")
    except SystemExit as exc:
        assert exc.code == 2
    assert "--only cannot be combined with --adopt-from" in capsys.readouterr().err
    assert not out.exists() and not store.exists()


def test_adopt_dir_moves_hashes_links_and_writes_manifest(tmp_path):
    src = tmp_path / "models"
    (src / "checkpoints").mkdir(parents=True)
    (src / "loras").mkdir()
    (src / "checkpoints" / "x.safetensors").write_bytes(b"xx")
    (src / "loras" / "y.safetensors").write_bytes(b"yy")
    store = tmp_path / "store"
    world = tmp_path / "worlds" / "sfw" / "models"
    out = tmp_path / "manifest.toml"
    lines = []
    assert fetch.adopt_dir(src, store, world, out, log=lines.append) == 0
    hx = hashlib.sha256(b"xx").hexdigest()
    hy = hashlib.sha256(b"yy").hexdigest()
    assert (store / hx / "x.safetensors").read_bytes() == b"xx" and not (
        src / "checkpoints" / "x.safetensors"
    ).exists()
    assert (world / "loras" / "y.safetensors").resolve() == (
        store / hy / "y.safetensors"
    ).resolve()
    text = out.read_text()
    assert (
        'dest = "checkpoints/x.safetensors"' in text
        and f'sha256 = "{hx}"' in text
        and 'source = "adopted"' in text
    )
    assert any(
        line.startswith("ADOPT checkpoints/x.safetensors -> " + hx[:12])
        for line in lines
    )
    models = fetch.load_manifest(out)
    assert {m["name"] for m in models} == {"x", "y"}
    assert (
        fetch.adopt_dir(src, store, world, out, log=lines.append) == 1
    )  # manifest exists: refuse
