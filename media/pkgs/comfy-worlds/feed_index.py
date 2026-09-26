"""The per-world feed index: `feed.sqlite` rebuilt from the renders' PNG chunks.

The design reserves `worlds/<world>/feed.sqlite` for sub-project 2 and names
the PNGs' embedded `prompt`/`workflow` chunks as the source of truth for what
produced an image. This module builds that index: it reads the `tEXt`/`iTXt`
chunks ComfyUI writes (PIL writes `iTXt` for a non-Latin-1 prompt), parses the
prompt for the base sampler's seed, and stores one `renders` row per `*.png`
under `worlds/<world>/output`. The PNGs are read-only — the files are the
record and the index is disposable — so this module writes nothing but
`feed.sqlite`. Stdlib only (`sqlite3`, `struct`, `zlib`, `json`, `pathlib`).
"""

import argparse
import json
import pathlib
import sqlite3
import struct
import sys
import time
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS renders(
  name TEXT PRIMARY KEY,
  prompt TEXT,
  workflow TEXT,
  seed INTEGER,
  mtime REAL
);
CREATE TABLE IF NOT EXISTS likes(
  name TEXT PRIMARY KEY REFERENCES renders(name),
  liked_at REAL
);
CREATE TABLE IF NOT EXISTS dislikes(
  name TEXT PRIMARY KEY,
  prompt TEXT NOT NULL,
  disliked_at REAL
);
CREATE TABLE IF NOT EXISTS seen(
  name TEXT PRIMARY KEY,
  seen_at REAL
);
"""


def open_db(root, world):
    """A `sqlite3.Connection` on `<root>/worlds/<world>/feed.sqlite`.

    Creates the file and its schema (`renders`, `likes`, `dislikes`,
    `seen`) when absent. Rows come back as `sqlite3.Row` so callers address
    columns by name.
    """
    db_path = pathlib.Path(root) / "worlds" / world / "feed.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _seed_from_prompt(prompt):
    """`inputs.seed` of the `KSampler` node with the numerically lowest id."""
    try:
        graph = json.loads(prompt)
    except (ValueError, TypeError):
        return None
    if not isinstance(graph, dict):
        return None
    samplers = []
    for node_id, node in graph.items():
        if not isinstance(node, dict) or node.get("class_type") != "KSampler":
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict) or "seed" not in inputs:
            continue
        try:
            key = int(node_id)
        except (ValueError, TypeError):
            continue
        samplers.append((key, inputs["seed"]))
    if not samplers:
        return None
    samplers.sort(key=lambda pair: pair[0])
    seed = samplers[0][1]
    return seed if isinstance(seed, int) else None


def read_chunks(path):
    """`{"prompt", "workflow", "seed"}` from a PNG's `tEXt`/`iTXt` chunks.

    `prompt` and `workflow` are the raw string values ComfyUI embeds under
    those keywords (the workflow as JSON text); `seed` is the base sampler's
    `inputs.seed`, parsed from the `prompt` chunk. A file that is not a PNG
    raises `ValueError`.
    """
    name = pathlib.Path(path).name
    data = pathlib.Path(path).read_bytes()
    if data[: len(PNG_SIGNATURE)] != PNG_SIGNATURE:
        raise ValueError(f"not a PNG: {name}")
    pos = len(PNG_SIGNATURE)
    chunks = {}
    while pos + 12 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        ctype = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if ctype == b"tEXt":
            keyword, _, text = chunk_data.partition(b"\x00")
            chunks[keyword.decode("latin-1")] = text.decode("latin-1")
        elif ctype == b"iTXt":
            keyword, rest = chunk_data.split(b"\x00", 1)
            compression_flag = rest[0]
            rest = rest[2:]  # compression flag + method
            _, rest = rest.split(b"\x00", 1)  # language tag
            _, text = rest.split(b"\x00", 1)  # translated keyword
            if compression_flag:
                text = zlib.decompress(text)
            chunks[keyword.decode("latin-1")] = text.decode("utf-8")
    prompt = chunks.get("prompt")
    workflow = chunks.get("workflow")
    return {
        "prompt": prompt,
        "workflow": workflow,
        "seed": _seed_from_prompt(prompt) if prompt is not None else None,
    }


def rebuild(root, world):
    """Upsert one `renders` row per `output/*.png`, drop rows whose file is
    gone, leave `likes` and `dislikes` untouched, and return the row count.

    Idempotent: running twice on an unchanged directory changes no row. A
    missing `output/` directory yields 0 rows, not an error. The `dislikes`
    rows deliberately carry no foreign key: a dislike must outlive the
    `renders` row this rebuild drops when its PNG is deleted.

    An unreadable file is skipped, never raised on: `read_chunks` keeps its
    contract and raises, and this loop absorbs it. A zero-byte file (a
    generator mid-write) and one that vanishes mid-walk (a concurrent
    dislike) are transient and skipped silently; anything else is corrupt and
    is named once on stderr. The reason is the caller, not politeness --
    `build_server` rebuilds every world before it binds its socket and the
    per-request stamp gate calls this again on every deck and shell GET, so a
    raise here is not one missing row but the whole feed server, for every
    world, refusing to start or answering 500.
    """
    out = pathlib.Path(root) / "worlds" / world / "output"
    rows = []
    if out.is_dir():
        for png in out.glob("*.png"):
            if not png.is_file():
                continue
            # One stat, used for both the skip rules and the row's mtime: the
            # old code stat()ed after reading, so a file deleted in between
            # raised out of the loop.
            try:
                st = png.stat()
            except OSError:
                # Gone between the glob and the stat -- a dislike unlinking
                # while this walk runs. Nothing to index and nothing to say.
                continue
            if st.st_size == 0:
                # A generator mid-write. It becomes a real render on a later
                # rebuild (the stamp gate re-runs on the size change), so
                # naming it every pass would be noise on a healthy system.
                continue
            try:
                chunks = read_chunks(png)
            except OSError:
                # Vanished between the stat and the read: the same transient
                # case as above, reached through a different door.
                continue
            except (ValueError, IndexError, zlib.error) as exc:
                # Genuinely corrupt: bytes that are not a PNG (ValueError), a
                # chunk stream that ends mid-field (IndexError), or unusable
                # compressed text (zlib.error). Named once, then skipped --
                # a file the index has no row for is not a reason for every
                # world's feed to be unreachable (the 2026-09-19 power cut
                # left seven such files and the server would not start).
                print(
                    f"index: skipping unreadable {png.name}: {exc}",
                    file=sys.stderr,
                )
                continue
            rows.append(
                (
                    png.name,
                    chunks["prompt"],
                    chunks["workflow"],
                    chunks["seed"],
                    st.st_mtime,
                )
            )
    conn = open_db(root, world)
    with conn:
        conn.executemany(
            "INSERT INTO renders(name, prompt, workflow, seed, mtime)"
            " VALUES(?, ?, ?, ?, ?)"
            " ON CONFLICT(name) DO UPDATE SET prompt=excluded.prompt,"
            " workflow=excluded.workflow, seed=excluded.seed,"
            " mtime=excluded.mtime",
            rows,
        )
        names = [row[0] for row in rows]
        if names:
            placeholders = ",".join("?" for _ in names)
            conn.execute(
                f"DELETE FROM renders WHERE name NOT IN ({placeholders})", names
            )
        else:
            conn.execute("DELETE FROM renders")
    return conn.execute("SELECT COUNT(*) FROM renders").fetchone()[0]


def newest(conn, limit=50):
    """Rows ordered by `mtime DESC, name` — the placeholder's order, now from
    the index."""
    return conn.execute(
        "SELECT name, prompt, workflow, seed, mtime"
        " FROM renders ORDER BY mtime DESC, name LIMIT ?",
        (limit,),
    ).fetchall()


def deck_page(conn, after=None, limit=10):
    """The deck's rows: `{name, prompt, workflow, seed, mtime, liked,
    unseen}` — every unseen render first (newest first), then the seen
    history behind the same order, so a swipe never dead-ends.

    `after` is the keyset `(unseen-key, mtime, name)` of the last row
    served: only rows that follow it in the deck's order
    (`unseen DESC, mtime DESC, name ASC`) come back. An unseen row has
    `unseen` 1, a seen row 0.
    """
    sql = (
        "SELECT r.name, r.prompt, r.workflow, r.seed, r.mtime,"
        " (l.name IS NOT NULL) AS liked, (s.name IS NULL) AS unseen"
        " FROM renders r"
        " LEFT JOIN likes l ON l.name = r.name"
        " LEFT JOIN seen s ON s.name = r.name"
    )
    params = []
    if after is not None:
        unseen, mtime, name = after
        sql += (
            " WHERE (s.name IS NULL) < ?"
            " OR ((s.name IS NULL) = ? AND r.mtime < ?)"
            " OR ((s.name IS NULL) = ? AND r.mtime = ? AND r.name > ?)"
        )
        params = [unseen, unseen, mtime, unseen, mtime, name]
    sql += " ORDER BY (s.name IS NULL) DESC, r.mtime DESC, r.name ASC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def unseen_count(conn):
    """The renders with no `seen` row — the deck's demand signal (spec §5:
    below the world's low water it starts the comfy-run oneshot)."""
    return conn.execute(
        "SELECT COUNT(*) FROM renders r"
        " LEFT JOIN seen s ON s.name = r.name WHERE s.name IS NULL"
    ).fetchone()[0]


def mark_seen(conn, names):
    """Upsert one `seen` row per name (consume, never serve) and return the
    count written.

    A `seen` row deliberately carries no foreign key: it must outlive the
    `renders` row the rebuild drops when its PNG is deleted (the
    `dislikes` precedent) — a name not in `renders` upserts without error.
    """
    now = time.time()
    with conn:
        conn.executemany(
            "INSERT INTO seen(name, seen_at) VALUES(?, ?)"
            " ON CONFLICT(name) DO UPDATE SET seen_at = excluded.seen_at",
            [(name, now) for name in names],
        )
    return len(names)


def prune(root, world, keep):
    """Delete the oldest UNLIKED renders until at most `keep` remain, and
    return how many were deleted.

    A liked render is never deleted, whatever its age. The likes are the
    search's whole signal, and `mutate._scaffold` builds every job from the
    newest liked render's graph — so deleting one would silently re-point the
    scaffold, which is a failure this project has already had once. The
    consequence is stated rather than hidden: when likes alone exceed `keep`,
    the cap is exceeded too, and nothing is deleted.

    Rebuilds the index first, so the row set matches the directory, and drops
    the rows of what it deleted. `dislikes` is untouched — a dislike must
    outlive the render, exactly as it does for the delete-on-dislike path.
    """
    rebuild(root, world)
    conn = open_db(root, world)
    rows = conn.execute(
        "SELECT r.name FROM renders r"
        " LEFT JOIN likes l ON l.name = r.name"
        " WHERE l.name IS NULL"
        " ORDER BY r.mtime DESC, r.name ASC"
    ).fetchall()
    liked = conn.execute("SELECT COUNT(*) FROM likes").fetchone()[0]
    # The cap counts every stored render; the likes are the part of it that
    # cannot be reclaimed, so only the remainder is available to unliked ones.
    budget = max(0, keep - liked)
    doomed = [row[0] for row in rows[budget:]]
    if not doomed:
        return 0
    out = pathlib.Path(root) / "worlds" / world / "output"
    deleted = []
    for name in doomed:
        try:
            (out / name).unlink(missing_ok=True)
        except OSError as exc:
            print(f"prune: could not delete {name}: {exc}", file=sys.stderr)
            continue
        deleted.append(name)
    if deleted:
        with conn:
            conn.executemany(
                "DELETE FROM renders WHERE name = ?", [(n,) for n in deleted]
            )
    return len(deleted)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="feed-index")
    parser.add_argument("--root", required=True)
    parser.add_argument("--world", required=True)
    parser.add_argument(
        "--keep",
        type=int,
        default=500,
        help="prune: the most renders to store (liked ones are never deleted)",
    )
    parser.add_argument("command", choices=["rebuild", "prune"])
    args = parser.parse_args(argv)
    if args.command == "rebuild":
        print(rebuild(args.root, args.world))
    elif args.command == "prune":
        print(prune(args.root, args.world, args.keep))


if __name__ == "__main__":
    main()
