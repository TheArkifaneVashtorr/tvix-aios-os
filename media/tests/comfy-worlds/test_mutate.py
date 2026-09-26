"""Unit tests for pkgs/comfy-worlds/mutate.py.

Loaded by path (like tests/comfy-worlds/test_feed_placeholder.py) so this test
file works both under `pytest tests/comfy-worlds` from the repo root and inside
checks.comfy-worlds-unit, which copies pkgs/comfy-worlds and tests/comfy-worlds
into a fresh tree without installing anything.

The grammar is a pure function: no ComfyUI, no model, no filesystem. The golden
test locks the exact `random.Random(seed)` output so any drift in the mutation
order, the RNG seeding, or the category application is a red test.
"""

import importlib.util
import json
import pathlib
import random
import re
import sqlite3
import sys

import pytest

from test_queue import FakeComfy

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "comfy-worlds" / "mutate.py"
spec = importlib.util.spec_from_file_location("mutate", SRC)
mutate = importlib.util.module_from_spec(spec)
# The frozen dataclass `Variant` looks itself up via `sys.modules` when the
# module is executed, so the path-loaded module must be registered first.
sys.modules[spec.name] = mutate
spec.loader.exec_module(mutate)

LORA = re.compile(r"<lora:([^:>]+):([^>]+)>")

PROMPT = "a golden hour photo of a cat, <lora:detail:0.5>, award-winning"
RULES = {
    "swaps": [["golden hour", "blue hour"], ["a cat", "a dog"]],
    "lora": {"detail": [0.3, 0.9]},
    "samplers": ["euler", "dpmpp_2m", "uni_pc"],
    "seed": "derive",
}

# The literal list `mutate(PROMPT, RULES, seed=1, n=3)` must produce.
EXPECTED_SEED1 = [
    mutate.Variant(
        prompt="a blue hour photo of a cat, <lora:detail:0.45304141544365306>, "
        "award-winning",
        sampler="dpmpp_2m",
        seed=3268308804,
    ),
    mutate.Variant(
        prompt="a golden hour photo of a dog, <lora:detail:0.773234010681308>, "
        "award-winning",
        sampler="euler",
        seed=2095328386,
    ),
    mutate.Variant(
        prompt="a golden hour photo of a dog, <lora:detail:0.6644627977711562>, "
        "award-winning",
        sampler="euler",
        seed=2988579416,
    ),
]

# GN39's second golden: the same grammar plus an enabled loraStack, drawn
# from the same one stream. The stack's draws sit AFTER the seed (Decision
# 3), so the first variant's prompt/sampler/seed are EXPECTED_SEED1's
# first verbatim — the pre-stack draws never move — and every later
# candidate is shifted by the stack draws before it. From this commit any
# reordering of the draw — a strength drawn before its member, the stack
# drawn before the seed, a missing round(…, 3) — is red by name.
STACK_POOL = (
    {
        "name": "krea2-lora-inkwash",
        "dest": "loras/krea2_inkwash.safetensors",
        "category": None,
        "incompatible": frozenset(),
    },
    {
        "name": "krea2-lora-inkline",
        "dest": "loras/krea2_inkline.safetensors",
        "category": None,
        "incompatible": frozenset(),
    },
    {
        "name": "krea2-lora-darkbrush",
        "dest": "loras/krea2_darkbrush.safetensors",
        "category": None,
        "incompatible": frozenset(),
    },
)

RULES_WITH_STACK = {
    "swaps": [["golden hour", "blue hour"], ["a cat", "a dog"]],
    "lora": {"detail": [0.3, 0.9]},
    "samplers": ["euler", "dpmpp_2m", "uni_pc"],
    "seed": "derive",
    "loraStack": {
        "count": (1, 3),
        "strength": (0.5, 0.9),
        "pool": STACK_POOL,
        "weights": None,
    },
}

# The literal list `mutate(PROMPT, RULES_WITH_STACK, seed=1, n=3)` must
# produce — locks the exact `random.Random(seed)` output with the stack in,
# so any drift in the draw's stream position or its rounding is a red test.
EXPECTED_SEED1_LORASTACK = [
    mutate.Variant(
        prompt="a blue hour photo of a cat, <lora:detail:0.45304141544365306>, "
        "award-winning",
        sampler="dpmpp_2m",
        seed=3268308804,
        loras=(("krea2-lora-inkline", 0.815), ("krea2-lora-inkwash", 0.511)),
    ),
    mutate.Variant(
        prompt="a golden hour photo of a dog, <lora:detail:0.6644627977711562>, "
        "award-winning",
        sampler="euler",
        seed=2988579416,
        loras=(("krea2-lora-darkbrush", 0.592), ("krea2-lora-inkline", 0.861)),
    ),
    mutate.Variant(
        prompt="a blue hour photo of a cat, <lora:detail:0.3152675165960765>, "
        "award-winning",
        sampler="uni_pc",
        seed=3784870617,
        loras=(
            ("krea2-lora-inkwash", 0.669),
            ("krea2-lora-inkline", 0.589),
            ("krea2-lora-darkbrush", 0.698),
        ),
    ),
]


def test_same_seed_same_variants():
    assert mutate.mutate(PROMPT, RULES, seed=1, n=3) == EXPECTED_SEED1


def test_same_seed_same_variants_with_stack():
    assert mutate.mutate(PROMPT, RULES_WITH_STACK, seed=1, n=3) == (
        EXPECTED_SEED1_LORASTACK
    )


def test_different_seed_differs():
    assert mutate.mutate(PROMPT, RULES, seed=1, n=3) != mutate.mutate(
        PROMPT, RULES, seed=2, n=3
    )


def test_exactly_n_distinct():
    variants = mutate.mutate(PROMPT, RULES, seed=1, n=5)
    assert len(variants) == 5
    assert len(set(variants)) == 5


def test_swap_either_direction():
    rules = {
        "swaps": [["golden hour", "blue hour"]],
        "lora": {},
        "samplers": ["euler"],
        "seed": "derive",
    }
    left = mutate.mutate("golden hour at dusk", rules, seed=1, n=1)[0].prompt
    right = mutate.mutate("blue hour at dawn", rules, seed=1, n=1)[0].prompt
    assert "blue hour" in left and "golden hour" not in left
    assert "golden hour" in right and "blue hour" not in right


def test_lora_strength_within_range():
    rules = {
        "swaps": [],
        "lora": {"detail": [0.3, 0.9]},
        "samplers": ["euler"],
        "seed": "derive",
    }
    variants = mutate.mutate("<lora:detail:0.5> a portrait", rules, seed=1, n=5)
    for v in variants:
        strength = float(LORA.search(v.prompt).group(2))
        assert 0.3 <= strength <= 0.9


def test_rule_never_fires_is_error():
    swap_rules = {
        "swaps": [["golden hour", "blue hour"]],
        "lora": {},
        "samplers": ["euler"],
        "seed": "derive",
    }
    with pytest.raises(mutate.RuleNeverFires) as exc:
        mutate.mutate("a plain photo", swap_rules, seed=1, n=1)
    assert exc.value.category == "swaps"

    lora_rules = {
        "swaps": [],
        "lora": {"detail": [0.3, 0.9]},
        "samplers": ["euler"],
        "seed": "derive",
    }
    with pytest.raises(mutate.RuleNeverFires) as exc:
        mutate.mutate("a plain photo", lora_rules, seed=1, n=1)
    assert exc.value.category == "lora"


def test_missing_table_refused(tmp_path):
    path = tmp_path / "manifest.toml"
    path.write_text("[other]\nkey = 1\n")
    with pytest.raises(ValueError, match="no \\[mutate\\] table in"):
        mutate.load_rules(str(path))


def test_keep_seed_policy():
    rules = {
        "swaps": [],
        "lora": {"detail": [0.3, 0.9]},
        "samplers": ["euler"],
        "seed": "keep",
    }
    variants = mutate.mutate("<lora:detail:0.5> a portrait", rules, seed=7, n=3)
    assert all(v.seed == 7 for v in variants)


def test_degenerate_ruleset_raises_variants_exhausted():
    rules = {
        "swaps": [["a cat", "a dog"]],
        "lora": {},
        "samplers": ["euler"],
        "seed": "keep",
    }
    with pytest.raises(mutate.VariantsExhausted) as exc:
        mutate.mutate("a cat on a roof", rules, seed=7, n=3)
    assert exc.value.requested == 3
    assert exc.value.distinct == 1
    assert exc.value.attempts == mutate._MAX_DRAWS


def test_swap_applies_once_when_token_repeats():
    rules = {
        "swaps": [["a cat", "a dog"]],
        "lora": {},
        "samplers": ["euler"],
        "seed": "derive",
    }
    variant = mutate.mutate("a cat and a cat", rules, seed=1, n=1)[0].prompt
    assert variant.count("a dog") == 1
    assert variant.count("a cat") == 1


# GN1's two-KSampler fixture (base-plus-refiner shape, trimmed): node 3 (the
# base sampler, numerically lowest id) and node 10 (the refiner) both carry
# `sampler_name = "euler"` so the sampler-substitution tests can assert a
# change to every KSampler node, and both carry a seed. Node 6 is the positive
# CLIPTextEncode ("a red apple"), node 7 the negative ("blurry").
WORLD_PROMPT = json.dumps(
    {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42,
                "sampler_name": "euler",
                "positive": ["6", 0],
                "negative": ["7", 0],
            },
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red apple"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry"}},
        "10": {
            "class_type": "KSampler",
            "inputs": {"seed": 99, "sampler_name": "euler", "positive": ["6", 0]},
        },
    }
)

# A [mutate] table whose swap fires on the extracted positive text and whose
# samplers list is the single "dpmpp_2m" (so the sampler substitution is
# observable in every KSampler node).
MUTATE_RULES_TOML = (
    '[mutate]\nswaps = [["a red apple", "a green apple"]]\nsamplers = ["dpmpp_2m"]\n'
)


def _make_world(base, renders, likes, rules_toml=None, dislikes=None):
    """Build `<base>/worlds/sfw/feed.sqlite` with the given `renders`,
    `likes` and (optionally) `dislikes` rows, and (optionally) a
    `lab/manifest.toml`. Returns the root path.

    The `dislikes` table is created unconditionally, in the real schema's
    own shape (Assumption 9): `name` is the PRIMARY KEY with NO foreign key
    — a dislike outlives the `renders` row the rebuild drops — and `prompt`
    is the extracted TEXT, not a graph. `dislikes` rows are
    `(name, prompt)` pairs.
    """
    root = pathlib.Path(base)
    db = root / "worlds" / "sfw" / "feed.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.executescript(
        "CREATE TABLE renders(name TEXT PRIMARY KEY, prompt TEXT, workflow TEXT,"
        " seed INTEGER, mtime REAL);"
        "CREATE TABLE likes(name TEXT PRIMARY KEY REFERENCES renders(name),"
        " liked_at REAL);"
        "CREATE TABLE dislikes(name TEXT PRIMARY KEY, prompt TEXT NOT NULL,"
        " disliked_at REAL);"
    )
    for name, prompt, seed in renders:
        conn.execute(
            "INSERT INTO renders(name, prompt, workflow, seed, mtime)"
            " VALUES(?, ?, ?, ?, 0.0)",
            (name, prompt, prompt, seed),
        )
    for name in likes:
        conn.execute("INSERT INTO likes(name, liked_at) VALUES(?, 0.0)", (name,))
    for name, prompt in dislikes or []:
        conn.execute(
            "INSERT INTO dislikes(name, prompt, disliked_at) VALUES(?, ?, 0.0)",
            (name, prompt),
        )
    conn.commit()
    conn.close()
    if rules_toml is not None:
        lab = root / "worlds" / "sfw" / "lab"
        lab.mkdir(parents=True, exist_ok=True)
        (lab / "manifest.toml").write_text(rules_toml)
    return str(root)


def _jobs(base):
    conn = sqlite3.connect(pathlib.Path(base) / "worlds" / "sfw" / "feed.sqlite")
    conn.row_factory = sqlite3.Row
    return conn


def test_loop_enqueues_n_per_like(tmp_path):
    root = _make_world(
        tmp_path,
        [("a.png", WORLD_PROMPT, 42), ("b.png", WORLD_PROMPT, 43)],
        ["a.png", "b.png"],
        MUTATE_RULES_TOML,
    )
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    count = (
        _jobs(root)
        .execute("SELECT COUNT(*) FROM jobs WHERE kind = 'mutate'")
        .fetchone()[0]
    )
    assert count == 6


def test_dry_run_writes_nothing_and_is_deterministic(tmp_path, capsys):
    root = _make_world(
        tmp_path,
        [("a.png", WORLD_PROMPT, 42)],
        ["a.png"],
        MUTATE_RULES_TOML,
    )
    args = [
        "--world",
        "sfw",
        "--root",
        root,
        "--dry-run",
        "--seed",
        "1",
        "--comfy-url",
        "http://127.0.0.1:1",
    ]
    mutate.main(args)
    out1 = capsys.readouterr().out
    mutate.main(args)
    out2 = capsys.readouterr().out
    assert out1 == out2
    assert out1 != ""
    count = _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert count == 0


def test_no_likes_exit_3(tmp_path):
    root = _make_world(tmp_path, [("a.png", WORLD_PROMPT, 42)], [], MUTATE_RULES_TOML)
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            ["--world", "sfw", "--root", root, "--comfy-url", "http://127.0.0.1:1"]
        )
    assert exc.value.code == 3


def test_missing_comfy_url_exits_2(tmp_path, capsys):
    root = _make_world(
        tmp_path, [("a.png", WORLD_PROMPT, 42)], ["a.png"], MUTATE_RULES_TOML
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(["--world", "sfw", "--root", root])
    assert exc.value.code == 2
    assert "--comfy-url" in capsys.readouterr().err


def test_missing_table_exit_2(tmp_path, capsys):
    root = _make_world(
        tmp_path,
        [("a.png", WORLD_PROMPT, 42)],
        ["a.png"],
        "[other]\nkey = 1\n",
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            ["--world", "sfw", "--root", root, "--comfy-url", "http://127.0.0.1:1"]
        )
    assert exc.value.code == 2
    assert "no [mutate] table" in capsys.readouterr().err


def test_variant_sampler_lands_in_every_ksampler(tmp_path):
    fake = FakeComfy()
    fake.start()
    try:
        # samplers = ["dpmpp_2m"]: every submitted body's node 3 AND node 10
        # must carry the variant sampler.
        root = _make_world(
            tmp_path, [("a.png", WORLD_PROMPT, 42)], ["a.png"], MUTATE_RULES_TOML
        )
        mutate.main(
            ["--world", "sfw", "--root", root, "--n", "1", "--comfy-url", fake.url]
        )
        assert fake.prompts
        for body in fake.prompts:
            assert body["prompt"]["3"]["inputs"]["sampler_name"] == "dpmpp_2m"
            assert body["prompt"]["10"]["inputs"]["sampler_name"] == "dpmpp_2m"
        # samplers absent: the nodes keep their stored "euler".
        fake.prompts.clear()
        root2 = _make_world(
            tmp_path / "nosampler",
            [("a.png", WORLD_PROMPT, 42)],
            ["a.png"],
            '[mutate]\nswaps = [["a red apple", "a green apple"]]\n',
        )
        mutate.main(
            ["--world", "sfw", "--root", root2, "--n", "1", "--comfy-url", fake.url]
        )
        assert fake.prompts
        for body in fake.prompts:
            assert body["prompt"]["3"]["inputs"]["sampler_name"] == "euler"
            assert body["prompt"]["10"]["inputs"]["sampler_name"] == "euler"
    finally:
        fake.stop()


def _graph(text):
    """A minimal prompt graph whose positive CLIPTextEncode carries `text`."""
    return json.dumps(
        {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 1,
                    "sampler_name": "euler",
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                },
            },
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": text}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry"}},
        }
    )


def test_positive_text_lowest_nonempty_clip_not_negative():
    # The stored positive prompt is the lowest-id CLIPTextEncode whose text is
    # non-empty and not the base KSampler's negative prompt: node 6, not the
    # negative node 7.
    assert mutate._positive_text(json.loads(WORLD_PROMPT)) == "a red apple"
    # When the negative prompt has a LOWER id than the positive, it must still
    # be skipped: node 2 is the negative ("blurry"), so node 5 is the positive.
    neg_first = {
        "1": {"class_type": "KSampler", "inputs": {"seed": 1, "negative": ["2", 0]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "a green pear"}},
    }
    assert mutate._positive_text(neg_first) == "a green pear"


# Three discriminating CLIPTextEncode nodes: node 4 is empty (the lowest id of
# the three), node 6 and node 8 hold distinct non-empty text. The base KSampler
# (node 1) links its negative prompt to node 2 ("blurry"), which is excluded.
# The extraction rule must skip the empty node and return the lowest-id
# non-empty text, so reversing the sort or dropping the non-empty guard changes
# the answer.
THREE_CLIP = {
    "1": {"class_type": "KSampler", "inputs": {"seed": 1, "negative": ["2", 0]}},
    "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red apple"}},
    "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "a green pear"}},
}


def test_positive_text_skips_empty_and_picks_lowest_of_two_eligible():
    assert mutate._positive_text(THREE_CLIP) == "a red apple"


def test_substitute_writes_seed_into_every_ksampler():
    variant = mutate.Variant(prompt="a red apple", sampler=None, seed=12345)
    workflow = mutate._substitute(json.loads(WORLD_PROMPT), "a red apple", variant)
    assert workflow["3"]["inputs"]["seed"] == 12345
    assert workflow["10"]["inputs"]["seed"] == 12345


# A thin ruleset under seed = "keep": a like whose text matches one swap pair
# can yield only 2 distinct variants (one swap outcome x two samplers) and is
# exhausted at n=3; a like matching both pairs yields 4 and is healthy.
EXHAUST_RULES = (
    '[mutate]\nswaps = [["a", "x"], ["b", "y"]]\n'
    'seed = "keep"\nsamplers = ["euler", "dpmpp_2m"]\n'
)


def test_exhausted_like_skipped_healthy_like_counted(tmp_path, capsys):
    root = _make_world(
        tmp_path,
        [("small.png", _graph("a"), 1), ("big.png", _graph("a b"), 2)],
        ["small.png", "big.png"],
        EXHAUST_RULES,
    )
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    captured = capsys.readouterr()
    assert captured.out.strip() == "mutated 1 likes into 3 jobs"
    assert "mutate: small.png: 3 requested, 2 distinct after 50 draws" in captured.err
    count = (
        _jobs(root)
        .execute("SELECT COUNT(*) FROM jobs WHERE kind = 'mutate'")
        .fetchone()[0]
    )
    assert count == 3


def test_skip_reasons_logged(tmp_path, capsys):
    root = _make_world(
        tmp_path,
        [
            ("unparse.png", "not a json graph", 1),
            ("nopos.png", _graph(""), 2),
            ("nulllike.png", WORLD_PROMPT, None),
            ("good.png", WORLD_PROMPT, 42),
        ],
        ["unparse.png", "nopos.png", "nulllike.png", "good.png"],
        MUTATE_RULES_TOML,
    )
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    captured = capsys.readouterr()
    assert "mutate: unparse.png: skipped (unparseable graph)" in captured.err
    assert "mutate: nopos.png: skipped (no positive text)" in captured.err
    assert "mutate: nulllike.png: skipped (no seed)" in captured.err
    assert captured.out.strip() == "mutated 1 likes into 3 jobs"
    count = (
        _jobs(root)
        .execute("SELECT COUNT(*) FROM jobs WHERE kind = 'mutate'")
        .fetchone()[0]
    )
    assert count == 3


def test_all_exhausted_exit_3(tmp_path, capsys):
    root = _make_world(
        tmp_path,
        [("c.png", _graph("a"), 1), ("d.png", _graph("a"), 2)],
        ["c.png", "d.png"],
        EXHAUST_RULES,
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--n",
                "3",
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 3
    captured = capsys.readouterr()
    assert "no like mutated in sfw" in captured.out
    assert "mutate: c.png: 3 requested, 2 distinct after 50 draws" in captured.err
    assert "mutate: d.png: 3 requested, 2 distinct after 50 draws" in captured.err
    count = (
        _jobs(root)
        .execute("SELECT COUNT(*) FROM jobs WHERE kind = 'mutate'")
        .fetchone()[0]
    )
    assert count == 0


def test_rule_never_fires_exit_2(tmp_path, capsys):
    root = _make_world(
        tmp_path,
        [("a.png", _graph("a plain photo"), 1)],
        ["a.png"],
        '[mutate]\nswaps = [["golden hour", "blue hour"]]\n',
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            ["--world", "sfw", "--root", root, "--comfy-url", "http://127.0.0.1:1"]
        )
    assert exc.value.code == 2
    assert "rule can fire" in capsys.readouterr().err


# --- comfy-mutate --seed-file (GN15): authored base prompts through the
# grammar, deterministic, enqueued as kind `mutate` with an `authored:` source.


def _write_seed_file(path, prompts):
    """The author's batch shape: `{"prompts": [str, …]}`."""
    path.write_text(json.dumps({"prompts": prompts}))
    return str(path)


def _set_times(root, liked_at=None, mtimes=None):
    """Give individual `likes.liked_at` / `renders.mtime` values distinct
    times, so `ORDER BY … DESC LIMIT 1` has a unique winner."""
    conn = sqlite3.connect(pathlib.Path(root) / "worlds" / "sfw" / "feed.sqlite")
    for name, when in (liked_at or {}).items():
        conn.execute("UPDATE likes SET liked_at = ? WHERE name = ?", (when, name))
    for name, when in (mtimes or {}).items():
        conn.execute("UPDATE renders SET mtime = ? WHERE name = ?", (when, name))
    conn.commit()
    conn.close()


def _graph_with_marker(text, marker):
    """`_graph(text)` plus one marker node unique to this graph, so a test can
    tell which render's graph a job's workflow was scaffolded from."""
    graph = json.loads(_graph(text))
    graph[marker] = {"class_type": "LoadImage", "inputs": {"image": f"{marker}.png"}}
    return json.dumps(graph)


AUTHORED = ["a red apple on a hill", "a red apple in the snow"]


def test_seed_file_expands_each_prompt(tmp_path):
    root = _make_world(
        tmp_path,
        [("a.png", WORLD_PROMPT, 42), ("b.png", WORLD_PROMPT, 43)],
        ["a.png", "b.png"],
        MUTATE_RULES_TOML,
    )
    seed_file = _write_seed_file(tmp_path / "batch.json", AUTHORED)
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    rows = _jobs(root).execute("SELECT kind, source FROM jobs").fetchall()
    assert len(rows) == 6
    assert all(row["kind"] == "mutate" for row in rows)
    assert all(row["source"] == "authored:batch.json" for row in rows)


def test_seed_file_uses_no_new_job_kind(tmp_path):
    # The live worlds' jobs table carries CHECK(kind IN
    # ('regenerate','edit','mutate')); a new kind would never reach it. The
    # test pins every enqueued row to that enum (and would also see the
    # sqlite3.IntegrityError a widened kind raises on a fresh table).
    root = _make_world(
        tmp_path, [("a.png", WORLD_PROMPT, 42)], ["a.png"], MUTATE_RULES_TOML
    )
    seed_file = _write_seed_file(tmp_path / "batch.json", AUTHORED)
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    kinds = {row[0] for row in _jobs(root).execute("SELECT DISTINCT kind FROM jobs")}
    assert kinds
    assert kinds <= {"regenerate", "edit", "mutate"}


def test_seed_file_deterministic(tmp_path):
    root_a = _make_world(
        tmp_path / "a", [("a.png", WORLD_PROMPT, 42)], ["a.png"], MUTATE_RULES_TOML
    )
    root_b = _make_world(
        tmp_path / "b", [("a.png", WORLD_PROMPT, 42)], ["a.png"], MUTATE_RULES_TOML
    )
    seed_file = _write_seed_file(tmp_path / "batch.json", AUTHORED)

    def args(root):
        return [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--seed",
            "7",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]

    mutate.main(args(root_a))
    mutate.main(args(root_b))
    query = "SELECT kind, source, prompt, seed FROM jobs ORDER BY seed, prompt"
    rows_a = [tuple(row) for row in _jobs(root_a).execute(query)]
    rows_b = [tuple(row) for row in _jobs(root_b).execute(query)]
    assert len(rows_a) == 6
    assert rows_a == rows_b


def test_seed_file_scaffolds_from_newest_like(tmp_path):
    root = _make_world(
        tmp_path,
        [
            ("old.png", _graph_with_marker("a red apple", "20"), 42),
            ("new.png", _graph_with_marker("a red apple", "21"), 43),
        ],
        ["old.png", "new.png"],
        MUTATE_RULES_TOML,
    )
    _set_times(root, liked_at={"old.png": 1.0, "new.png": 2.0})
    seed_file = _write_seed_file(tmp_path / "batch.json", ["a red apple at dusk"])
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "2",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    rows = _jobs(root).execute("SELECT prompt FROM jobs").fetchall()
    assert len(rows) == 2
    for row in rows:
        workflow = json.loads(row["prompt"])
        assert "21" in workflow
        assert "20" not in workflow


def test_seed_file_no_likes_uses_newest_render(tmp_path):
    root = _make_world(
        tmp_path,
        [
            ("old.png", _graph_with_marker("a red apple", "20"), 42),
            ("new.png", _graph_with_marker("a red apple", "21"), 43),
        ],
        [],
        MUTATE_RULES_TOML,
    )
    _set_times(root, mtimes={"old.png": 1.0, "new.png": 2.0})
    seed_file = _write_seed_file(tmp_path / "batch.json", ["a red apple at dusk"])
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "2",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    rows = _jobs(root).execute("SELECT prompt FROM jobs").fetchall()
    assert len(rows) == 2
    for row in rows:
        workflow = json.loads(row["prompt"])
        assert "21" in workflow
        assert "20" not in workflow


def test_seed_file_no_renders_refused(tmp_path, capsys):
    root = _make_world(tmp_path, [], [], MUTATE_RULES_TOML)
    seed_file = _write_seed_file(tmp_path / "batch.json", AUTHORED)
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--seed-file",
                seed_file,
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    assert "sfw" in capsys.readouterr().err


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(None, id="missing-file"),
        pytest.param("{not json", id="unparseable-json"),
        pytest.param(json.dumps(["a red apple"]), id="bare-array"),
        pytest.param(json.dumps({"prompts": []}), id="empty-prompts"),
        pytest.param(json.dumps({"prompts": ["a red apple", 5]}), id="non-string"),
        pytest.param(json.dumps({"prompts": [""]}), id="empty-string"),
    ],
)
def test_seed_file_bad_shape_refused(tmp_path, capsys, content):
    root = _make_world(
        tmp_path, [("a.png", WORLD_PROMPT, 42)], ["a.png"], MUTATE_RULES_TOML
    )
    path = tmp_path / "batch.json"
    if content is not None:
        path.write_text(content)
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--seed-file",
                str(path),
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    assert "seed file" in capsys.readouterr().err
    count = _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert count == 0


def test_seed_file_distinct_seeds_per_prompt(tmp_path):
    root = _make_world(
        tmp_path, [("a.png", WORLD_PROMPT, 42)], ["a.png"], MUTATE_RULES_TOML
    )
    # Structurally identical prompts: with a constant base seed the two RNG
    # streams would coincide and the seed sets would collide.
    seed_file = _write_seed_file(tmp_path / "batch.json", AUTHORED)
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--seed",
            "100",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    distinct = (
        _jobs(root).execute("SELECT COUNT(DISTINCT seed) FROM jobs").fetchone()[0]
    )
    assert distinct == 6


# The scaffold's LoRA stack is inherited, not chosen: _scaffold takes the
# newest LIKED render's graph, so on 2026-09-20 every one of 1355 renders
# carried the same two act LoRAs and liking anything in the feed put them
# straight back. stripLoras is the interim control beside the stack axis:
# delete the loader chain and rewire whatever consumed it. Since GN40 the
# axis's seam is _substitute's own fourth parameter, so the control is the
# loops' composition — substitute, then _strip_loras on the copy — which
# the helper below performs and these tests exercise.


def _lora_chain_graph():
    """UNET -> lora -> lora -> KSampler.model, the live nsfw shape."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "base.safetensors"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "clip.safetensors"}},
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["2", 0], "text": "a cat"},
        },
        "10": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": "a.safetensors",
                "strength_model": 0.8,
            },
        },
        "11": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["10", 0],
                "lora_name": "b.safetensors",
                "strength_model": 0.6,
            },
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["11", 0],
                "positive": ["3", 0],
                "seed": 1,
                "sampler_name": "euler",
            },
        },
    }


def _substituted_and_stripped(graph, positive_text, variant):
    """The loops' composition since GN40: `_substitute` (the axis's own
    seam, four parameters — `lora_stack` last), then the interim control
    applied to the copy — the two lines both `main` and `_run_seed_file`
    run when a world sets `stripLoras`."""
    out = mutate._substitute(graph, positive_text, variant)
    mutate._strip_loras(out)
    return out


def test_strip_loras_removes_the_loader_nodes():
    variant = mutate.Variant(prompt="a dog", sampler="euler", seed=7)
    out = _substituted_and_stripped(_lora_chain_graph(), "a cat", variant)
    assert [k for k, n in out.items() if "Lora" in n["class_type"]] == []


def test_strip_loras_rewires_the_sampler_back_to_the_unet():
    variant = mutate.Variant(prompt="a dog", sampler="euler", seed=7)
    out = _substituted_and_stripped(_lora_chain_graph(), "a cat", variant)
    # The whole point: the KSampler must not dangle at a deleted node.
    assert out["6"]["inputs"]["model"] == ["1", 0]


def test_strip_loras_leaves_everything_else_alone():
    variant = mutate.Variant(prompt="a dog", sampler="dpmpp_2m", seed=7)
    out = _substituted_and_stripped(_lora_chain_graph(), "a cat", variant)
    assert out["3"]["inputs"]["text"] == "a dog"
    assert out["6"]["inputs"]["seed"] == 7
    assert out["6"]["inputs"]["sampler_name"] == "dpmpp_2m"
    assert out["3"]["inputs"]["clip"] == ["2", 0]


def test_strip_loras_off_is_todays_behaviour():
    variant = mutate.Variant(prompt="a dog", sampler="euler", seed=7)
    kept = mutate._substitute(_lora_chain_graph(), "a cat", variant)
    assert kept["6"]["inputs"]["model"] == ["11", 0]
    assert sorted(k for k, n in kept.items() if "Lora" in n["class_type"]) == [
        "10",
        "11",
    ]


def test_strip_loras_on_a_graph_with_none_is_a_no_op():
    graph = _lora_chain_graph()
    del graph["10"]
    del graph["11"]
    graph["6"]["inputs"]["model"] = ["1", 0]
    variant = mutate.Variant(prompt="a dog", sampler="euler", seed=7)
    out = _substituted_and_stripped(graph, "a cat", variant)
    assert out["6"]["inputs"]["model"] == ["1", 0]


def test_load_rules_defaults_strip_loras_off(tmp_path):
    manifest = tmp_path / "manifest.toml"
    manifest.write_text('[mutate]\nsamplers = ["euler"]\n')
    assert mutate.load_rules(str(manifest))["stripLoras"] is False


def test_load_rules_reads_strip_loras(tmp_path):
    manifest = tmp_path / "manifest.toml"
    manifest.write_text('[mutate]\nsamplers = ["euler"]\nstripLoras = true\n')
    assert mutate.load_rules(str(manifest))["stripLoras"] is True


# --- GN46: the pair is refused at load, by name — the four arms of
# stripLoras x loraStack, the no-LoRA spelling pinned, and the composition
# order settled by a test.
#
# (false, None) is today, (true, None) the strip, (false, table) the draw;
# (true, table) — a world saying "no LoRAs" and "draw a stack" at once — is
# a configuration error, refused by name, never silently resolved. A world
# that wants no LoRAs with the axis on spells it count = [0, 0].


def test_strip_loras_with_enabled_stack_refused_at_load(tmp_path):
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        "[mutate]\nstripLoras = true\n\n[mutate.loraStack]\nenable = true\n"
        "count = [1, 1]\nstrength = [0.5, 0.9]\n\n" + DARKBRUSH
    )
    with pytest.raises(ValueError) as exc:
        mutate.load_rules(str(manifest))
    assert "stripLoras = true and [mutate.loraStack] enable = true" in str(exc.value)
    assert "count = [0, 0]" in str(exc.value)


def test_strip_loras_with_inert_stack_still_loads(tmp_path):
    # The negative control for the arm: inert is inert. An enable = false
    # table — here with bounds that would never validate — beside
    # stripLoras = true loads, and the strip still applies.
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        "[mutate]\nstripLoras = true\n\n[mutate.loraStack]\nenable = false\n"
        "count = [3, 1]\n\n" + DARKBRUSH
    )
    rules = mutate.load_rules(str(manifest))
    assert rules["stripLoras"] is True
    assert rules["loraStack"] is None


def test_count_zero_zero_renders_without_loaders(tmp_path):
    # The no-LoRA spelling: count = [0, 0] is legal (lo 0, hi 0, pool 1),
    # every candidate draws the empty stack, and the rebuild's empty arm
    # deletes the loaders and leaves the KSampler at the UNETLoader. One
    # variant: under seed = "keep" with no swaps and no samplers the empty
    # stack makes every candidate identical, so n = 2 would exhaust.
    root = _make_world(
        tmp_path,
        [("a.png", json.dumps(KREA2_CHAIN), 42)],
        ["a.png"],
        '[mutate]\nseed = "keep"\n\n[mutate.loraStack]\nenable = true\n'
        "count = [0, 0]\nstrength = [0.5, 0.9]\n\n" + DARKBRUSH,
    )
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "1",
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    rows = (
        _jobs(root).execute("SELECT prompt FROM jobs WHERE kind = 'mutate'").fetchall()
    )
    assert len(rows) == 1
    for row in rows:
        graph = json.loads(row["prompt"])
        assert not any(
            isinstance(node, dict) and node.get("class_type") == "LoraLoaderModelOnly"
            for node in graph.values()
        )
        assert graph["11"]["inputs"]["model"] == ["1", 0]


def test_stack_pass_then_strip_leaves_no_loader():
    # The composition order, settled by a test: the stack pass rebuilds the
    # chain (fresh ids above 11), then the strip walks each consumer back
    # through the WHOLE rebuilt chain to the source — the inherited pair's
    # survival was an old binary, never the walk.
    out = mutate._substitute(
        KREA2_CHAIN, "a neon koi", _stack_variant(THREE_LORAS), lora_stack=KREA2_STACK
    )
    mutate._strip_loras(out)
    assert _loaders(out) == []
    assert out["11"]["inputs"]["model"] == ["1", 0]


def test_refused_pair_exits_2_from_the_seed_file(tmp_path, capsys):
    root = _make_world(
        tmp_path,
        [("a.png", json.dumps(KREA2_CHAIN), 42)],
        ["a.png"],
        "[mutate]\nstripLoras = true\n\n[mutate.loraStack]\nenable = true\n"
        "count = [1, 1]\nstrength = [0.5, 0.9]\n\n" + DARKBRUSH,
    )
    seed_file = _write_seed_file(tmp_path / "batch.json", ["a neon koi"])
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--seed-file",
                seed_file,
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    assert "stripLoras = true and [mutate.loraStack] enable = true" in (
        capsys.readouterr().err
    )
    assert _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


# --- GN38: the [mutate.loraStack] grammar — the LoRA pool and its bounds.
#
# The axis's own table, distinct from [mutate].lora (which rewrites inline
# <lora:NAME:strength> prompt TAGS and keeps its meaning): a pool of LoRAs
# derived from the [[model]] entries — a rule, never a second list of names —
# plus the bounds a variant's stack is drawn within. Inert by default: the
# table absent, or enable = false, and rules["loraStack"] is None and the
# module's behaviour is byte-identical to today.


def _stack_manifest(stack_toml, models_toml):
    """A manifest with a [mutate] table, the given [mutate.loraStack] body and
    the given [[model]] entries."""
    return (
        '[mutate]\nsamplers = ["euler"]\n\n[mutate.loraStack]\n'
        f"{stack_toml}\n{models_toml}"
    )


# GN47: the three enabled loras/ fixtures are CARDed rows — three distinct
# categories, so no same-category exclusion changes an existing draw.
DARKBRUSH = """\
[[model]]
name = "krea2-lora-darkbrush"
dest = "loras/krea2_darkbrush.safetensors"
enabled = true
category = "style"
"""

PARKED = """\
[[model]]
name = "krea2-lora-parked"
dest = "loras/krea2_parked.safetensors"
enabled = false
"""

INKWASH = """\
[[model]]
name = "krea2-lora-inkwash"
dest = "loras/krea2_inkwash.safetensors"
enabled = true
category = "body"
"""

INKLINE = """\
[[model]]
name = "krea2-lora-inkline"
dest = "loras/krea2_inkline.safetensors"
enabled = true
category = "detail"
"""

BASE = """\
[[model]]
name = "krea2-base"
dest = "checkpoints/krea2_fp8.safetensors"
enabled = true
"""

TWO_LORAS = DARKBRUSH + INKWASH


def test_lora_stack_pool_is_enabled_loras_entries_in_order(tmp_path):
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        _stack_manifest(
            "enable = true\ncount = [1, 3]\nstrength = [0.5, 0.9]\n",
            PARKED + INKWASH + BASE + INKLINE + DARKBRUSH,
        )
    )
    stack = mutate.load_rules(str(manifest))["loraStack"]
    # The disabled loras/ row and the enabled checkpoints/ row are excluded;
    # the three enabled loras/ rows stay in manifest order (all three carded,
    # so the pool keeps its shape — GN47 adds the card's own typed fields).
    assert [entry["name"] for entry in stack["pool"]] == [
        "krea2-lora-inkwash",
        "krea2-lora-inkline",
        "krea2-lora-darkbrush",
    ]
    assert stack["pool"][0] == {
        "name": "krea2-lora-inkwash",
        "dest": "loras/krea2_inkwash.safetensors",
        "category": "body",
        "incompatible": frozenset(),
        "trigger": None,
        "requires": (),
        "version": None,
    }
    assert stack["count"] == (1, 3)
    assert stack["strength"] == (0.5, 0.9)
    assert stack["weights"] is None


def test_lora_stack_reads_category_and_incompatible(tmp_path):
    tagged = (
        "[[model]]\n"
        'name = "krea2-lora-darkbrush"\n'
        'dest = "loras/krea2_darkbrush.safetensors"\n'
        "enabled = true\n"
        'category = "position"\n'
        'incompatible = ["krea2-lora-inkwash"]\n'
    )
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        _stack_manifest(
            "enable = true\ncount = [1, 2]\nstrength = [0.5, 0.9]\n",
            tagged + INKWASH,
        )
    )
    stack = mutate.load_rules(str(manifest))["loraStack"]
    by_name = {entry["name"]: entry for entry in stack["pool"]}
    assert by_name["krea2-lora-darkbrush"]["category"] == "position"
    assert by_name["krea2-lora-darkbrush"]["incompatible"] == frozenset(
        {"krea2-lora-inkwash"}
    )
    assert by_name["krea2-lora-inkwash"]["category"] == "body"


def test_lora_stack_absent_is_none(tmp_path):
    manifest = tmp_path / "manifest.toml"
    manifest.write_text('[mutate]\nsamplers = ["euler"]\n')
    assert mutate.load_rules(str(manifest))["loraStack"] is None


@pytest.mark.parametrize(
    "stack_toml",
    [
        pytest.param(
            "enable = false\ncount = [3, 1]\nstrength = [0, 9]\n", id="disabled"
        ),
        pytest.param(
            "count = [1, 3]\nstrength = [0.5, 0.9]\n", id="enable-absent-defaults-off"
        ),
    ],
)
def test_lora_stack_inert_is_none_without_validating(tmp_path, stack_toml):
    # An inert table is inert: enable = false (or absent) means None, and the
    # table's other keys are NOT validated — a parked world whose bounds would
    # refuse still loads.
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(_stack_manifest(stack_toml, DARKBRUSH))
    assert mutate.load_rules(str(manifest))["loraStack"] is None


@pytest.mark.parametrize(
    "stack_toml, models_toml, message",
    [
        pytest.param(
            "enable = true\ncount = [1, 5]\nstrength = [0.5, 0.9]\n",
            TWO_LORAS,
            "count hi 5 exceeds the 2 enabled loras/ rows",
            id="count-hi-exceeds-pool",
        ),
        pytest.param(
            "enable = true\ncount = [3, 1]\nstrength = [0.5, 0.9]\n",
            TWO_LORAS,
            "count lo 3 exceeds hi 1",
            id="count-lo-above-hi",
        ),
        pytest.param(
            "enable = true\ncount = [1, 2]\nstrength = [0, 1]\n",
            TWO_LORAS,
            "strength lo 0 must be positive",
            id="strength-lo-not-positive",
        ),
        pytest.param(
            "enable = true\ncount = [1, 2]\nstrength = [0.5, 0.9]\n",
            '[[model]]\nname = "krea2-lora-darkbrush"\n'
            'dest = "loras/krea2_darkbrush.safetensors"\nenabled = true\n'
            'incompatible = ["no-such-lora"]\n',
            "no-such-lora",
            id="unknown-incompatible",
        ),
        pytest.param(
            "enable = true\ncount = [1, 2]\nstrength = [0.5, 0.9]\n",
            '[[model]]\nname = "krea2-lora-darkbrush"\n'
            'dest = "loras/krea2_darkbrush.safetensors"\nenabled = true\n'
            'incompatible = ["krea2-lora-darkbrush"]\n',
            "names itself",
            id="self-incompatible",
        ),
        pytest.param(
            'enable = "yes"\ncount = [1, 2]\nstrength = [0.5, 0.9]\n',
            TWO_LORAS,
            "enable must be a boolean",
            id="enable-not-boolean",
        ),
        pytest.param(
            "enable = true\nstrength = [0.5, 0.9]\n",
            TWO_LORAS,
            "count is required",
            id="count-missing",
        ),
        pytest.param(
            "enable = true\ncount = [1, 2]\n",
            TWO_LORAS,
            "strength is required",
            id="strength-missing",
        ),
    ],
)
def test_lora_stack_refused_at_load(tmp_path, stack_toml, models_toml, message):
    # Refused at load, never discovered at draw: every violation is a named
    # ValueError whose message carries the offending key and the reason.
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(_stack_manifest(stack_toml, models_toml))
    with pytest.raises(ValueError, match=re.escape(message)):
        mutate.load_rules(str(manifest))


# The krea2-lora5 shape (measured against the in-repo fixture
# media/workflows/krea2/krea2_fp8_lora5.api.json, which the check's sandbox
# never copies — hence this inline literal): UNETLoader -> two
# LoraLoaderModelOnly nodes -> the KSampler's model input.
KREA2_CHAIN = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux.safetensors"}},
    "2": {
        "class_type": "LoraLoaderModelOnly",
        "inputs": {
            "model": ["1", 0],
            "lora_name": "krea2_darkbrush.safetensors",
            "strength_model": 0.8,
        },
    },
    "3": {
        "class_type": "LoraLoaderModelOnly",
        "inputs": {
            "model": ["2", 0],
            "lora_name": "krea2_inkwash.safetensors",
            "strength_model": 0.6,
        },
    },
    "9": {"class_type": "CLIPTextEncode", "inputs": {"text": "a neon koi"}},
    "11": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["3", 0],
            "positive": ["9", 0],
            "seed": 42,
            "sampler_name": "euler",
        },
    },
}


def test_substitute_default_is_byte_identical(tmp_path):
    # Spec §10's regression guard, written first: with no [mutate.loraStack]
    # table, _substitute's output is today's bytes — the loader chain verbatim,
    # only the seed written. Green by construction the day it lands; its
    # load-bearing turn is GN40's mutant M8, the day the stack pass fires on
    # an untagged world.
    manifest = tmp_path / "manifest.toml"
    manifest.write_text('[mutate]\nseed = "keep"\n')
    rules = mutate.load_rules(str(manifest))
    variant = mutate.mutate("a neon koi", rules, seed=1, n=1)[0]
    assert variant == mutate.Variant(prompt="a neon koi", sampler=None, seed=1)
    workflow = mutate._substitute(KREA2_CHAIN, "a neon koi", variant)
    expected = json.loads(json.dumps(KREA2_CHAIN))
    expected["11"]["inputs"]["seed"] = 1
    assert json.dumps(workflow, sort_keys=True) == json.dumps(expected, sort_keys=True)
    assert workflow["11"]["inputs"]["model"] == ["3", 0]
    assert workflow["2"]["inputs"]["lora_name"] == "krea2_darkbrush.safetensors"


# --- GN39: the draw — Variant gains its LoRA stack, weighted, conflict-free,
# inside bounds.
#
# Every fixture here is a rules dict carrying the NORMALIZED loraStack shape
# `_lora_stack` returns (count/strength tuples, a pool of member dicts,
# weights None or a name -> float dict) — the draw reads the normalized
# shape, never TOML, so these tests exercise the draw alone. The stack is
# drawn from the one random.Random(seed) stream AFTER the seed (Decision 3):
# the position the second golden lock below freezes.


def _pool_entry(name, category=None, incompatible=()):
    """One normalized pool member — the shape `_lora_stack` returns."""
    return {
        "name": name,
        "dest": f"loras/{name}.safetensors",
        "category": category,
        "incompatible": frozenset(incompatible),
    }


def _stack_rules(
    pool, count=(1, 3), strength=(0.5, 0.9), weights=None, seed_policy="derive"
):
    """Rules whose `loraStack` is the normalized shape `load_rules` returns."""
    return {
        "swaps": [],
        "lora": {},
        "samplers": [],
        "seed": seed_policy,
        "loraStack": {
            "count": tuple(count),
            "strength": tuple(strength),
            "pool": tuple(pool),
            "weights": weights,
        },
    }


def test_stack_within_bounds():
    # A 4-member pool, count [1, 3], strength [0.5, 0.9]: every variant's
    # stack holds 1-3 distinct pool members, every strength in range and
    # rounded to exactly three decimals.
    rules = _stack_rules([_pool_entry(n) for n in ("a", "b", "c", "d")])
    variants = mutate.mutate("a cat", rules, seed=1, n=30)
    assert len(variants) == 30
    for variant in variants:
        assert 1 <= len(variant.loras) <= 3
        names = [name for name, _ in variant.loras]
        assert len(set(names)) == len(names)
        for name, strength in variant.loras:
            assert name in {"a", "b", "c", "d"}
            assert 0.5 <= strength <= 0.9
            assert strength == round(strength, 3)


def test_fixed_seed_reproduces_batch():
    # Two identical calls over a stack-bearing ruleset: identical lists,
    # stacks included — the draw is deterministic in the caller's seed.
    rules = _stack_rules([_pool_entry(n) for n in ("a", "b", "c", "d")])
    first = mutate.mutate("a cat", rules, seed=1, n=10)
    second = mutate.mutate("a cat", rules, seed=1, n=10)
    assert first == second
    # count lo is 1, so every variant carries a non-empty stack.
    assert all(variant.loras for variant in first)


def test_stack_order_is_draw_order():
    # The tuple's order is the draw order, and the draw sits AFTER the seed
    # on the one stream (Decision 3): replaying the stream — seed draw first,
    # then one member followed by one strength per slot — must reproduce
    # every variant's names in order.
    pool = ("a", "b", "c", "d")
    rules = _stack_rules([_pool_entry(n) for n in pool], count=(2, 2))
    variants = mutate.mutate("a cat", rules, seed=11, n=5)
    assert len(variants) == 5
    rng = random.Random(11)
    for variant in variants:
        rng.randrange(2**32)  # the derived seed, drawn before the stack
        target = rng.randint(2, 2)
        names = []
        for _ in range(target):
            candidates = [n for n in pool if n not in names]
            name = rng.choices(candidates)[0]
            rng.uniform(0.5, 0.9)  # the strength, drawn after its member
            names.append(name)
        assert [name for name, _ in variant.loras] == names


def test_conflicts_never_cooccur():
    # Two position-category LoRAs in a 4-member pool: no stack ever holds
    # both — one category per stack, by declaration.
    pool = [
        _pool_entry("a", category="position"),
        _pool_entry("b", category="position"),
        _pool_entry("c"),
        _pool_entry("d"),
    ]
    rules = _stack_rules(pool)
    variants = mutate.mutate("a cat", rules, seed=1, n=30)
    for variant in variants:
        names = {name for name, _ in variant.loras}
        assert not {"a", "b"} <= names


def test_incompatible_symmetric():
    # The operator writes each incompatible pair once; the rule reads both
    # directions. Both fixtures in one test so the direction that regresses
    # is named.
    for declared_on in ("a", "b"):
        if declared_on == "a":
            pool = [
                _pool_entry("a", incompatible=["b"]),
                _pool_entry("b"),
                _pool_entry("c"),
                _pool_entry("d"),
            ]
        else:
            pool = [
                _pool_entry("a"),
                _pool_entry("b", incompatible=["a"]),
                _pool_entry("c"),
                _pool_entry("d"),
            ]
        rules = _stack_rules(pool)
        variants = mutate.mutate("a cat", rules, seed=1, n=30)
        for variant in variants:
            names = {name for name, _ in variant.loras}
            assert not {"a", "b"} <= names, f"incompatible declared on {declared_on}"


def test_overconstrained_pool_raises_variants_exhausted():
    # Every member one category, count floor 2: the floor is unreachable —
    # every candidate fails mid-fill, the shared _MAX_DRAWS budget raises
    # the same named VariantsExhausted as the degenerate ruleset, and the
    # fill loop terminates instead of hanging.
    pool = [_pool_entry(n, category="position") for n in ("a", "b", "c", "d")]
    rules = _stack_rules(pool, count=(2, 2))
    with pytest.raises(mutate.VariantsExhausted) as exc:
        mutate.mutate("a cat", rules, seed=1, n=1)
    assert exc.value.requested == 1
    assert exc.value.distinct == 0
    assert exc.value.attempts == mutate._MAX_DRAWS


def test_liked_lora_drawn_more():
    # A weighted pool: a (0.9) is drawn more often than b (0.1) over a
    # seeded run — an ordering, never a probability. Seeds 4 and 5 x 30
    # variants (the shared _MAX_DRAWS budget caps one call at 50) give 60:
    # weighted, a draws 30 times to b's 6; with the weights ignored the
    # same seeds draw a 23 to b's 34 — the ordering flips, so a uniform
    # draw is red here.
    pool = [_pool_entry(n) for n in ("a", "b", "c", "d")]
    rules = _stack_rules(pool, weights={"a": 0.9, "b": 0.1, "c": 1.0, "d": 1.0})
    counts = {}
    drawn = 0
    for seed in (4, 5):
        for variant in mutate.mutate("a cat", rules, seed=seed, n=30):
            drawn += 1
            for name, _ in variant.loras:
                counts[name] = counts.get(name, 0) + 1
    assert drawn == 60
    assert counts["a"] > counts["b"]


def test_strength_only_stacks_are_distinct():
    # seed = "keep", no swaps/lora/samplers, a 1-member pool with count [1, 1]:
    # variants differ ONLY in strength. A names-only `seen` would collapse
    # them all into one and exhaust; the strength is part of the variant's
    # identity, so n distinct variants are collected.
    rules = _stack_rules([_pool_entry("a")], count=(1, 1), seed_policy="keep")
    variants = mutate.mutate("a cat", rules, seed=7, n=3)
    assert len(variants) == 3
    assert len(set(variants)) == 3
    assert [tuple(name for name, _ in v.loras) for v in variants] == [
        ("a",),
        ("a",),
        ("a",),
    ]
    strengths = [v.loras[0][1] for v in variants]
    assert len(set(strengths)) == 3


# --- GN40: the graph rewiring — loader chains rebuilt at any count,
# branches refused by name.
#
# Spec §7's pass, inside _substitute behind its fourth parameter (the
# seam, Decision 4): `lora_stack` is the NORMALIZED table load_rules
# returns for an enabled [mutate.loraStack] (GN38's shape), and the
# rebuild follows variant.loras (GN39's draw — loader order is draw
# order). None — today at both call sites and in every prior test —
# changes nothing: GN38's byte-identity guard above. The fixtures are
# inline literals to the measured shapes (Assumption 7): KREA2_CHAIN is
# krea2-lora5's chain trimmed to two loaders; KREA2_NO_LORA is the lora0
# graph — no loader at all, its KSampler taking model straight from the
# UNETLoader.

KREA2_NO_LORA = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux.safetensors"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "clip.safetensors"}},
    "3": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["2", 0], "text": "a neon koi"},
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["2", 0], "text": "blurry"},
    },
    "5": {"class_type": "VAELoader", "inputs": {"vae_name": "vae.safetensors"}},
    "6": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": ["3", 0],
            "negative": ["4", 0],
            "seed": 42,
            "sampler_name": "euler",
        },
    },
}

# The pass reads the pool's dests only, and the dest BASENAME is the
# loader's lora_name — Decision 1's measured pair: dest
# "loras/krea2_darkbrush.safetensors" carries lora_name
# "krea2_darkbrush.safetensors"; the manifest name, the dest and the
# basename are three different strings.
KREA2_STACK = {
    "count": (1, 3),
    "strength": (0.5, 0.9),
    "pool": (
        {
            "name": "krea2-lora-darkbrush",
            "dest": "loras/krea2_darkbrush.safetensors",
            "category": None,
            "incompatible": frozenset(),
        },
        {
            "name": "krea2-lora-inkwash",
            "dest": "loras/krea2_inkwash.safetensors",
            "category": None,
            "incompatible": frozenset(),
        },
        {
            "name": "krea2-lora-inkline",
            "dest": "loras/krea2_inkline.safetensors",
            "category": None,
            "incompatible": frozenset(),
        },
    ),
    "weights": None,
}

THREE_LORAS = (
    ("krea2-lora-darkbrush", 0.8),
    ("krea2-lora-inkwash", 0.6),
    ("krea2-lora-inkline", 0.7),
)


def _stack_variant(loras):
    """A Variant carrying the given stack, nothing else moved."""
    return mutate.Variant(prompt="a neon koi", sampler=None, seed=1, loras=loras)


def _loaders(out):
    """The graph's LoraLoaderModelOnly node ids, numerically sorted."""
    return sorted(
        (
            key
            for key, node in out.items()
            if isinstance(node, dict)
            and node.get("class_type") == "LoraLoaderModelOnly"
        ),
        key=int,
    )


def test_chain_two_to_three():
    # A 2-loader chain rebuilt at 3: exactly 3 loaders, chained in tuple
    # order (draw order is loader order), the first from the old source
    # verbatim, the KSampler's model at the new last node, strengths and
    # lora_names written per entry (the dest basenames, never the dests).
    out = mutate._substitute(
        KREA2_CHAIN, "a neon koi", _stack_variant(THREE_LORAS), lora_stack=KREA2_STACK
    )
    assert _loaders(out) == ["12", "13", "14"]  # fresh, above the max key 11
    assert out["12"]["inputs"]["model"] == ["1", 0]
    assert out["12"]["inputs"]["lora_name"] == "krea2_darkbrush.safetensors"
    assert out["12"]["inputs"]["strength_model"] == 0.8
    assert out["13"]["inputs"]["model"] == ["12", 0]
    assert out["13"]["inputs"]["lora_name"] == "krea2_inkwash.safetensors"
    assert out["13"]["inputs"]["strength_model"] == 0.6
    assert out["14"]["inputs"]["model"] == ["13", 0]
    assert out["14"]["inputs"]["lora_name"] == "krea2_inkline.safetensors"
    assert out["14"]["inputs"]["strength_model"] == 0.7
    assert out["11"]["inputs"]["model"] == ["14", 0]
    assert "2" not in out
    assert "3" not in out


def test_chain_to_zero():
    # §7's own empty arm: the enabled zero-LoRA draw deletes the loaders
    # and puts the sampler's model back at the source, verbatim.
    out = mutate._substitute(
        KREA2_CHAIN, "a neon koi", _stack_variant(()), lora_stack=KREA2_STACK
    )
    assert _loaders(out) == []
    assert out["11"]["inputs"]["model"] == ["1", 0]
    assert "2" not in out
    assert "3" not in out


def test_no_loaders_gains_chain():
    # The lora0 shape: no loader existed, so a chain is inserted where
    # none was — from the UNETLoader the KSampler models from, the sampler
    # repointed, nothing else moved (the CLIPTextEncode texts and the
    # VAELoader untouched).
    out = mutate._substitute(
        KREA2_NO_LORA,
        "a neon koi",
        _stack_variant(THREE_LORAS[:2]),
        lora_stack=KREA2_STACK,
    )
    assert _loaders(out) == ["7", "8"]  # fresh, above the max key 6
    assert out["7"]["inputs"]["model"] == ["1", 0]
    assert out["7"]["inputs"]["lora_name"] == "krea2_darkbrush.safetensors"
    assert out["8"]["inputs"]["model"] == ["7", 0]
    assert out["8"]["inputs"]["lora_name"] == "krea2_inkwash.safetensors"
    assert out["6"]["inputs"]["model"] == ["8", 0]
    assert out["3"]["inputs"]["text"] == "a neon koi"
    assert out["4"]["inputs"]["text"] == "blurry"
    assert out["5"] == KREA2_NO_LORA["5"]
    assert out["6"]["inputs"]["positive"] == ["3", 0]
    assert out["6"]["inputs"]["negative"] == ["4", 0]


def test_multi_consumer_last_loader():
    # §7: "the spec does not assume only one" — two KSamplers both taking
    # model from the last loader are both repointed at the new chain's end.
    graph = json.loads(json.dumps(KREA2_CHAIN))
    graph["12"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": ["3", 0],
            "positive": ["9", 0],
            "seed": 7,
            "sampler_name": "euler",
        },
    }
    out = mutate._substitute(
        graph,
        "a neon koi",
        _stack_variant(THREE_LORAS[:1]),
        lora_stack=KREA2_STACK,
    )
    assert _loaders(out) == ["13"]  # fresh, above the max key 12
    assert out["11"]["inputs"]["model"] == ["13", 0]
    assert out["12"]["inputs"]["model"] == ["13", 0]


def test_samplers_from_two_model_sources_refused():
    # No loaders and two samplers modeling from different nodes: a branch
    # before any chain — refused with both source ids, never a guess.
    graph = json.loads(json.dumps(KREA2_NO_LORA))
    graph["8"] = {
        "class_type": "UNETLoader",
        "inputs": {"unet_name": "other.safetensors"},
    }
    graph["9"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": ["8", 0],
            "positive": ["3", 0],
            "seed": 1,
            "sampler_name": "euler",
        },
    }
    with pytest.raises(mutate.LoraChainUnsupported) as exc:
        mutate._substitute(
            graph,
            "a neon koi",
            _stack_variant(THREE_LORAS[:1]),
            lora_stack=KREA2_STACK,
        )
    assert sorted(exc.value.node_ids) == ["1", "8"]


def test_branched_chain_refused():
    # A mid-chain loader feeding a second consumer: refused with both ids
    # in the message, never rewired on a guess (the RuleNeverFires style).
    graph = json.loads(json.dumps(KREA2_CHAIN))
    graph["12"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": ["2", 0],
            "positive": ["9", 0],
            "seed": 1,
            "sampler_name": "euler",
        },
    }
    with pytest.raises(mutate.LoraChainUnsupported) as exc:
        mutate._substitute(
            graph,
            "a neon koi",
            _stack_variant(THREE_LORAS[:1]),
            lora_stack=KREA2_STACK,
        )
    assert list(exc.value.node_ids) == ["2", "12"]
    assert "nodes 2, 12" in str(exc.value)
    assert "two consumers" in str(exc.value)


def test_two_roots_refused():
    # Two loaders both fed by the UNETLoader: two chain roots, refused
    # with the loader ids.
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux.safetensors"}},
        "2": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": "a.safetensors",
                "strength_model": 0.8,
            },
        },
        "3": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": "b.safetensors",
                "strength_model": 0.6,
            },
        },
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": "a neon koi"}},
        "11": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["9", 0],
                "seed": 1,
                "sampler_name": "euler",
            },
        },
    }
    with pytest.raises(mutate.LoraChainUnsupported) as exc:
        mutate._substitute(
            graph,
            "a neon koi",
            _stack_variant(THREE_LORAS[:1]),
            lora_stack=KREA2_STACK,
        )
    assert sorted(exc.value.node_ids) == ["2", "3"]


def test_fresh_ids_skip_collisions():
    # The collision belt: keys "7" and "07" beside 1..6 and a high "40" —
    # the inserted ids start above the LARGEST numeric key, exist as keys
    # afterward, and no existing node is overwritten in any spelling.
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux.safetensors"}},
        "2": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": "krea2_darkbrush.safetensors",
                "strength_model": 0.8,
            },
        },
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "clip.safetensors"}},
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["3", 0], "text": "a neon koi"},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["3", 0], "text": "blurry"},
        },
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": "vae.safetensors"}},
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["9", 0], "vae": ["6", 0]},
        },
        "07": {"class_type": "LoadImage", "inputs": {"image": "src.png"}},
        "9": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["2", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "seed": 1,
                "sampler_name": "euler",
            },
        },
        "40": {
            "class_type": "SaveImage",
            "inputs": {"images": ["7", 0], "filename_prefix": "out"},
        },
    }
    out = mutate._substitute(
        graph,
        "a neon koi",
        _stack_variant(THREE_LORAS[:2]),
        lora_stack=KREA2_STACK,
    )
    # The loader at "2" is deleted; the numeric keys left top out at 40,
    # so the fresh ids are 41 and 42 — not len(graph)+1, not 7 nor 07.
    assert _loaders(out) == ["41", "42"]
    assert out["41"]["inputs"]["model"] == ["1", 0]
    assert out["42"]["inputs"]["model"] == ["41", 0]
    assert out["9"]["inputs"]["model"] == ["42", 0]
    # Nothing overwritten, in any spelling.
    assert out["6"]["class_type"] == "VAELoader"
    assert out["7"]["class_type"] == "VAEDecode"
    assert out["07"]["class_type"] == "LoadImage"
    assert out["40"]["class_type"] == "SaveImage"
    assert "2" not in out


def test_no_ksampler_is_noop():
    # Decision 6: a graph with no KSampler at all is a stated no-op —
    # nothing consumes a model chain, so the pass leaves it
    # byte-identical (the live loops never scaffold from such a graph:
    # no positive text).
    graph = json.loads(json.dumps(KREA2_CHAIN))
    del graph["11"]
    out = mutate._substitute(
        graph,
        "a neon koi",
        _stack_variant(THREE_LORAS[:1]),
        lora_stack=KREA2_STACK,
    )
    assert json.dumps(out, sort_keys=True) == json.dumps(graph, sort_keys=True)
    assert _loaders(out) == ["2", "3"]  # the old chain, untouched


# Interfaces 1's own treatment in the loops: a refused graph is caught
# beside RuleNeverFires, printed to stderr, exit 2 — a configuration
# error, never a silent skip and never a partial batch.

STACK_AXIS_TOML = (
    '[mutate]\nseed = "keep"\n\n[mutate.loraStack]\nenable = true\n'
    "count = [1, 2]\nstrength = [0.5, 0.9]\n\n" + DARKBRUSH + INKWASH
)


def _branched_graph():
    """KREA2_CHAIN plus a second consumer of its first loader — the branch."""
    graph = json.loads(json.dumps(KREA2_CHAIN))
    graph["12"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": ["2", 0],
            "positive": ["9", 0],
            "seed": 1,
            "sampler_name": "euler",
        },
    }
    return json.dumps(graph)


def test_refused_chain_exits_2_from_the_likes(tmp_path, capsys):
    root = _make_world(
        tmp_path, [("a.png", _branched_graph(), 42)], ["a.png"], STACK_AXIS_TOML
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--n",
                "1",
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "lora chain unsupported" in captured.err
    assert "nodes 2, 12" in captured.err
    assert _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_refused_chain_exits_2_from_the_seed_file(tmp_path, capsys):
    root = _make_world(
        tmp_path, [("a.png", _branched_graph(), 42)], ["a.png"], STACK_AXIS_TOML
    )
    seed_file = _write_seed_file(tmp_path / "batch.json", ["a neon koi"])
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--seed-file",
                seed_file,
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    assert "lora chain unsupported" in capsys.readouterr().err
    assert _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


# --- GN41: the verdict weighting — the world's own likes and dislikes
# bias the draw.
#
# Spec §8: the weight is not an operator knob and not a guess — it is the
# world's own verdict history, read at draw time from feed.sqlite, per
# LoRA (a LoRA that appears in liked renders becomes likelier EVERYWHERE,
# not only in the set it was seen in), with the dislikes limit stated
# rather than papered over, a fixed Beta(2,2) prior, and a cold start
# that is exactly the uniform fallback GN39 ships. The manifest below
# enables a three-LoRA pool (a, b, c) whose dest basenames are
# "a.safetensors", "b.safetensors", "c.safetensors" — the loader's
# lora_name is the dest BASENAME, never the manifest name (Assumption 8).

WEIGHTS_TOML = (
    '[mutate]\nseed = "keep"\n\n[mutate.loraStack]\nenable = true\n'
    "count = [1, 2]\nstrength = [0.5, 0.9]\n\n"
    '[[model]]\nname = "a"\ndest = "loras/a.safetensors"\nenabled = true\n'
    'category = "act"\n\n'
    '[[model]]\nname = "b"\ndest = "loras/b.safetensors"\nenabled = true\n'
    'category = "body"\n\n'
    '[[model]]\nname = "c"\ndest = "loras/c.safetensors"\nenabled = true\n'
    'category = "style"\n'
)


def _lora_graph(*filenames):
    """A minimal graph whose LoraLoaderModelOnly chain carries the given
    lora_name files — the measured krea2 loader shape (Assumption 7), so
    the graph doubles as a scaffold for the threaded-path tests."""
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux.safetensors"}},
    }
    prev = "1"
    for index, filename in enumerate(filenames, start=2):
        graph[str(index)] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": [prev, 0],
                "lora_name": filename,
                "strength_model": 0.8,
            },
        }
        prev = str(index)
    graph["9"] = {"class_type": "CLIPTextEncode", "inputs": {"text": "a neon koi"}}
    graph["11"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": [prev, 0],
            "positive": ["9", 0],
            "seed": 42,
            "sampler_name": "euler",
        },
    }
    return json.dumps(graph)


def _world_rules_and_weights(root):
    """The threaded weights for a WEIGHTS_TOML world: load_rules, then the
    exact call both loops run after it — the threading line, made here
    because the tests are the caller."""
    manifest = pathlib.Path(root) / "worlds" / "sfw" / "lab" / "manifest.toml"
    rules = mutate.load_rules(str(manifest))
    conn = mutate.queue.open_db(root, "sfw")
    weights = mutate.lora_stack_weights(conn, rules["loraStack"]["pool"])
    return rules, weights


def test_weights_exact_values(tmp_path):
    # One liked render carrying a's file beside a FOREIGN loader (a gains
    # one full like — the foreign file is not in the pool, and a like
    # shared by two LoRAs is not half a like each), one disliked render
    # carrying b's file, nothing carrying c: Beta(2,2) arithmetic,
    # deterministic, no statistics.
    root = _make_world(
        tmp_path,
        [
            ("liked.png", _lora_graph("a.safetensors", "x.safetensors"), 42),
            ("disliked.png", _lora_graph("b.safetensors"), 43),
        ],
        ["liked.png"],
        WEIGHTS_TOML,
        [("disliked.png", "the extracted text, never a graph")],
    )
    _, weights = _world_rules_and_weights(root)
    assert weights == {"a": 0.6, "b": 0.4, "c": 0.5}


def test_cold_start_is_uniform(tmp_path, capsys):
    # No verdict touches any pool LoRA (the one liked render carries only
    # a foreign file): every weight is exactly 0.5, and the draw through
    # the threaded path reproduces the unweighted GN39 draw
    # byte-identically — the fallback (weights None) and the cold path
    # are one code path.
    graph = _lora_graph("x.safetensors")
    root = _make_world(tmp_path, [("a.png", graph, 42)], ["a.png"], WEIGHTS_TOML)
    _, weights = _world_rules_and_weights(root)
    assert weights == {"a": 0.5, "b": 0.5, "c": 0.5}
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--dry-run",
            "--seed",
            "1",
            "--n",
            "5",
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    threaded = capsys.readouterr().out
    assert threaded != ""
    manifest = pathlib.Path(root) / "worlds" / "sfw" / "lab" / "manifest.toml"
    unweighted = mutate.load_rules(str(manifest))  # weights None
    lines = []
    for variant in mutate.mutate("a neon koi", unweighted, seed=1, n=5):
        loras = ",".join(f"{n}@{s}" for n, s in variant.loras) or "-"
        lines.append(
            f"a.png loras={loras} {variant.seed} {variant.sampler} {variant.prompt}"
        )
    assert threaded == "\n".join(lines) + "\n"


def test_liked_lora_outdraws_disliked(tmp_path):
    # Ten liked renders carrying a, ten disliked carrying b, c unjudged:
    # the weights are the exact Beta(2,2) ratios, and over a seeded
    # 60-variant draw through mutate() with the weights threaded the
    # liked LoRA outdraws the unjudged one, which outdraws the disliked
    # one (§10's ordering, over a seeded run).
    root = _make_world(
        tmp_path,
        [(f"liked{i}.png", _lora_graph("a.safetensors"), i) for i in range(10)]
        + [
            (f"disliked{i}.png", _lora_graph("b.safetensors"), 100 + i)
            for i in range(10)
        ],
        [f"liked{i}.png" for i in range(10)],
        WEIGHTS_TOML,
        [(f"disliked{i}.png", "the extracted text") for i in range(10)],
    )
    rules, weights = _world_rules_and_weights(root)
    assert weights == {"a": 12 / 14, "b": 2 / 14, "c": 0.5}
    rules["loraStack"]["weights"] = weights
    counts = {"a": 0, "b": 0, "c": 0}
    drawn = 0
    for seed in (4, 5):
        for variant in mutate.mutate("a cat", rules, seed=seed, n=30):
            drawn += 1
            for name, _ in variant.loras:
                counts[name] += 1
    assert drawn == 60
    assert counts["a"] > counts["c"] > counts["b"]


def test_dislikes_row_without_renders_contributes_nothing(tmp_path):
    # The post-rebuild shape (Assumption 9): the PNG was deleted and the
    # rebuild dropped the renders row, but rebuild leaves dislikes
    # untouched — so the dislikes table can carry a name with no renders
    # row. The JOIN drops it and no code path invents its LoRAs.
    root = _make_world(
        tmp_path,
        [("liked.png", _lora_graph("a.safetensors"), 42)],
        ["liked.png"],
        WEIGHTS_TOML,
        [("ghost.png", "a dislike whose render is gone")],
    )
    _, weights = _world_rules_and_weights(root)
    assert weights == {"a": 0.6, "b": 0.5, "c": 0.5}


def test_unparseable_liked_graph_skipped(tmp_path):
    # A liked row whose prompt is not JSON: skipped, never raised — the
    # module's own tolerance — so a world of only that carries no verdict
    # and every weight is the 0.5 prior.
    root = _make_world(
        tmp_path,
        [("broken.png", "not a json graph", 42)],
        ["broken.png"],
        WEIGHTS_TOML,
    )
    _, weights = _world_rules_and_weights(root)
    assert weights == {"a": 0.5, "b": 0.5, "c": 0.5}


def test_weights_threaded_into_seed_file_branch(tmp_path):
    # The LIVE path (Assumption 10) is the seed-file branch: the verdict
    # history must weight the draw there too. Two identical batch runs
    # enqueue identical jobs, and the enqueued graphs carry the seeded
    # ordering — the liked LoRA outdraws the unjudged one, which
    # outdraws the disliked one.
    renders = [(f"liked{i}.png", _lora_graph("a.safetensors"), i) for i in range(10)]
    renders += [
        (f"disliked{i}.png", _lora_graph("b.safetensors"), 100 + i) for i in range(10)
    ]
    dislikes = [(f"disliked{i}.png", "the extracted text") for i in range(10)]
    root_a = _make_world(
        tmp_path / "a",
        renders,
        [f"liked{i}.png" for i in range(10)],
        WEIGHTS_TOML,
        dislikes,
    )
    root_b = _make_world(
        tmp_path / "b",
        renders,
        [f"liked{i}.png" for i in range(10)],
        WEIGHTS_TOML,
        dislikes,
    )
    batch = _write_seed_file(
        tmp_path / "batch.json", [f"a neon koi {i}" for i in range(10)]
    )

    def args(root):
        return [
            "--world",
            "sfw",
            "--root",
            root,
            "--seed",
            "10",
            "--seed-file",
            batch,
            "--n",
            "3",
            "--comfy-url",
            "http://127.0.0.1:1",
        ]

    mutate.main(args(root_a))
    mutate.main(args(root_b))
    query = "SELECT kind, source, prompt, seed FROM jobs ORDER BY seed, prompt"
    rows_a = [tuple(row) for row in _jobs(root_a).execute(query)]
    rows_b = [tuple(row) for row in _jobs(root_b).execute(query)]
    assert len(rows_a) == 30
    assert rows_a == rows_b
    counts = {"a": 0, "b": 0, "c": 0}
    for row in rows_a:
        workflow = json.loads(row[2])
        for node in workflow.values():
            if (
                isinstance(node, dict)
                and node.get("class_type") == "LoraLoaderModelOnly"
            ):
                lora = node["inputs"]["lora_name"].removesuffix(".safetensors")
                counts[lora] += 1
    assert counts["a"] > counts["c"] > counts["b"]


# --- GN47: the LoRA cards — the pool's own grammar. §3.1's three typed
# fields on a [[model]] row (category: one of five; trigger: a token;
# requires: 1-8 words, position and act cards only; unmatched: a bool;
# version: an id), the pool rule (a row with no card is not in the pool),
# the draw clamped to the carded pool, and the one stderr line that names
# the uncarded rows — a report, never an exit.


def _model_row(name, dest=None, **extra):
    """One [[model]] row as TOML: an installed loras/ row by default (name,
    dest, enabled = true) plus the given card keys, values rendered through
    json.dumps (a TOML-compatible spelling of our strings, lists and
    bools)."""
    dest = dest if dest is not None else f"loras/{name}.safetensors"
    lines = ["[[model]]", f'name = "{name}"', f'dest = "{dest}"', "enabled = true"]
    for key, value in extra.items():
        lines.append(f"{key} = {json.dumps(value)}")
    return "\n".join(lines) + "\n"


def _card_stack(tmp_path, models, count="count = [1, 1]"):
    """load_rules over a manifest whose [mutate.loraStack] is enabled with
    the given [[model]] rows and count; returns the normalized stack."""
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        _stack_manifest(f"enable = true\n{count}\nstrength = [0.5, 0.9]\n", models)
    )
    return mutate.load_rules(str(manifest))["loraStack"]


def test_pool_is_carded_rows_only(tmp_path):
    # §3.1: "a row with no card is not in the pool". The carded row
    # (category present, unmatched absent) is the pool; the no-category row
    # and the unmatched row are installed, enabled loras/ rows — outside
    # the pool, named in `uncarded` in manifest order; the disabled row and
    # the checkpoints/ row are not installed rows at all.
    models = (
        INKWASH
        + _model_row("krea2-lora-plain")
        + _model_row("krea2-lora-orphan", category="act", unmatched=True)
        + PARKED
        + BASE
    )
    stack = _card_stack(tmp_path, models)
    assert [entry["name"] for entry in stack["pool"]] == ["krea2-lora-inkwash"]
    assert stack["uncarded"] == ("krea2-lora-plain", "krea2-lora-orphan")


@pytest.mark.parametrize("category", ["position", "act", "body", "style", "detail"])
def test_category_arms_all_load(tmp_path, category):
    # The five enum arms each load and the entry carries its category.
    stack = _card_stack(tmp_path, _model_row("krea2-lora-inkwash", category=category))
    assert stack["pool"][0]["category"] == category


def test_category_outside_the_five_refused(tmp_path):
    # A category outside the enum is refused at load, by name.
    with pytest.raises(
        ValueError, match=re.escape("one of position, act, body, style, detail")
    ):
        _card_stack(tmp_path, _model_row("krea2-lora-inkwash", category="pose"))


@pytest.mark.parametrize(
    "trigger, ok",
    [
        pytest.param("n3lson,", True, id="legal-comma"),
        pytest.param("f1lledmouth,", True, id="legal-digit-comma"),
        pytest.param("Face Details", True, id="legal-inner-space"),
        pytest.param("<lora:x>", False, id="lora-tag"),
        pytest.param("a" * 65, False, id="too-long"),
        pytest.param(" lead", False, id="leading-edge-space"),
        pytest.param("lead ", False, id="trailing-edge-space"),
        pytest.param("a\nb", False, id="newline"),
        pytest.param("a<b>", False, id="outside-the-class"),
    ],
)
def test_trigger_token_rule(tmp_path, trigger, ok):
    # A legal token loads and the entry carries it; every illegal one is
    # refused with the token message. The trailing-edge-space arm (the class
    # alone accepts it) discriminates the strip clause from the character
    # class; the outside-the-class arm (a legal first char, illegal later
    # chars) discriminates the class itself.
    models = _model_row("krea2-lora-inkwash", category="body", trigger=trigger)
    if ok:
        stack = _card_stack(tmp_path, models)
        assert stack["pool"][0]["trigger"] == trigger
    else:
        with pytest.raises(ValueError, match=re.escape("is not a token")):
            _card_stack(tmp_path, models)


def test_requires_only_on_position_and_act(tmp_path):
    # requires rides only on position and act cards — a detail card or a
    # row with no category at all is refused — and is 1-8 words of the word
    # class: a bad character or a nine-item list is refused the same way.
    def load_with(**extra):
        return _card_stack(tmp_path, _model_row("krea2-lora-inkwash", **extra))

    stack = load_with(category="act", requires=["bent over"])
    assert stack["pool"][0]["requires"] == ("bent over",)
    for extra in ({"category": "detail"}, {}):
        with pytest.raises(
            ValueError, match=re.escape("only position and act cards carry requires")
        ):
            load_with(requires=["bent over"], **extra)
    with pytest.raises(ValueError, match=re.escape("must be 1-8 words")):
        load_with(category="act", requires=["anal*"])
    with pytest.raises(ValueError, match=re.escape("must be 1-8 words")):
        load_with(
            category="act",
            requires=[
                "one",
                "two",
                "three",
                "four",
                "five",
                "six",
                "seven",
                "eight",
                "nine",
            ],
        )


def test_unmatched_and_version_typed(tmp_path):
    # unmatched is a bool and version is an id (1-32 chars of letters,
    # digits, . _ -): anything else is refused at load, by name.
    with pytest.raises(ValueError, match=re.escape("unmatched must be true or false")):
        _card_stack(
            tmp_path, _model_row("krea2-lora-inkwash", category="body", unmatched="yes")
        )
    with pytest.raises(ValueError, match=re.escape("version is not an id")):
        _card_stack(
            tmp_path, _model_row("krea2-lora-inkwash", category="body", version="v1/2")
        )
    stack = _card_stack(
        tmp_path, _model_row("krea2-lora-inkwash", category="body", version="12345")
    )
    assert stack["pool"][0]["version"] == "12345"


def test_count_ceiling_counts_installed_rows(tmp_path):
    # The ceiling counts INSTALLED rows (pool + uncarded), never the pool
    # alone: three enabled rows, one carded — count hi 3 loads (the draw
    # clamps to the pool's 1), hi 4 is refused naming the 3 installed.
    models = INKWASH + _model_row("krea2-lora-plain") + _model_row("krea2-lora-orphan")
    stack = _card_stack(tmp_path, models, count="count = [1, 3]")
    assert stack["uncarded"] == ("krea2-lora-plain", "krea2-lora-orphan")
    with pytest.raises(
        ValueError, match=re.escape("count hi 4 exceeds the 3 enabled loras/ rows")
    ):
        _card_stack(tmp_path, models, count="count = [1, 4]")


def test_draw_clamps_to_the_carded_pool():
    # A two-entry pool with count (3, 3): the randint is always drawn (the
    # stream position never moves) but the target is CLAMPED to the pool's
    # size — three variants, each with exactly the two pool members, no
    # VariantsExhausted. Without the clamp every candidate fails its fill.
    rules = _stack_rules([_pool_entry("a"), _pool_entry("b")], count=(3, 3))
    variants = mutate.mutate(PROMPT, rules, seed=1, n=3)
    assert len(variants) == 3
    for variant in variants:
        assert len(variant.loras) == 2
        assert {name for name, _ in variant.loras} == {"a", "b"}


def test_empty_pool_draws_empty_stacks():
    # §4's first failure mode, defused: an empty carded pool with count
    # (1, 3) draws the EMPTY stack — the clamp, never an exhaustion — and
    # every variant renders LoRA-less.
    rules = _stack_rules([], count=(1, 3))
    variants = mutate.mutate(PROMPT, rules, seed=1, n=3)
    assert len(variants) == 3
    assert all(variant.loras == () for variant in variants)


def test_all_uncarded_manifest_renders_without_loaders(tmp_path, capsys):
    # §4's first failure mode end to end: a world whose enabled rows carry
    # no card at all (pool empty, every row uncarded) still renders through
    # --seed-file — every job's graph has no LoraLoaderModelOnly node and
    # the KSampler models from the chain's source — with the one stderr
    # line naming the pool's absence.
    root = _make_world(
        tmp_path,
        [("a.png", json.dumps(KREA2_CHAIN), 42)],
        ["a.png"],
        '[mutate]\nseed = "derive"\n\n[mutate.loraStack]\nenable = true\n'
        "count = [1, 2]\nstrength = [0.5, 0.9]\n\n"
        + _model_row("krea2-lora-darkbrush")
        + _model_row("krea2-lora-inkwash"),
    )
    seed_file = _write_seed_file(tmp_path / "batch.json", ["a neon koi"])
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--seed-file",
            seed_file,
            "--seed",
            "1",
            "--n",
            "3",
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    rows = (
        _jobs(root).execute("SELECT prompt FROM jobs WHERE kind = 'mutate'").fetchall()
    )
    assert len(rows) == 3
    for row in rows:
        graph = json.loads(row["prompt"])
        assert not any(
            isinstance(node, dict) and node.get("class_type") == "LoraLoaderModelOnly"
            for node in graph.values()
        )
        assert graph["11"]["inputs"]["model"] == ["1", 0]
    assert "have no card and are out of the pool" in capsys.readouterr().err


def test_uncarded_line_names_three_and_counts(tmp_path, capsys):
    # Four uncarded rows: the stderr line counts all four, names the first
    # three (manifest order, comma-joined) and ends with the ellipsis —
    # never a fourth name, never an exit.
    models = "".join(_model_row(f"krea2-lora-uncarded{i}") for i in range(4))
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        _stack_manifest(
            "enable = true\ncount = [1, 2]\nstrength = [0.5, 0.9]\n", models
        )
    )
    rules = mutate.load_rules(str(manifest))
    mutate._report_uncarded(rules, "sfw")
    assert capsys.readouterr().err == (
        "mutate: 4 enabled LoRAs in sfw have no card and are out of the pool:"
        " krea2-lora-uncarded0, krea2-lora-uncarded1, krea2-lora-uncarded2, …\n"
    )


# --- GN50: the coupled draw — the mutator's half. The draw happens first
# (`draw_stacks`, the `--draw-stacks` arm) and the author is told; a batch
# may carry one `{loras, requires, triggers}` entry per prompt, and
# comfy-mutate binds that same stack instead of drawing its own:
# `requires` is checked per variant against the mutated prompt (a miss
# drops the stack and counts), the triggers are prepended at enqueue —
# never written by the author — and the models are written from the bound
# stack (GN40's `_rebuild_lora_chain`, unchanged).

# The carded pool the coupled draw reads: three members, three categories
# — inkline (position, a trigger, two requires words), inkwash (act, no
# trigger, one requires word), darkbrush (style, a trigger, no requires).
CARDED_POOL = (
    {
        "name": "krea2-lora-inkline",
        "dest": "loras/krea2_inkline.safetensors",
        "category": "position",
        "incompatible": frozenset(),
        "trigger": "n3lson,",
        "requires": ("bent over", "looking back"),
    },
    {
        "name": "krea2-lora-inkwash",
        "dest": "loras/krea2_inkwash.safetensors",
        "category": "act",
        "incompatible": frozenset(),
        "trigger": None,
        "requires": ("kneeling",),
    },
    {
        "name": "krea2-lora-darkbrush",
        "dest": "loras/krea2_darkbrush.safetensors",
        "category": "style",
        "incompatible": frozenset(),
        "trigger": "d4rk,",
        "requires": (),
    },
)

CARDED_RULES = {
    "swaps": [],
    "lora": {},
    "samplers": ["euler", "dpmpp_2m", "uni_pc"],
    "seed": "keep",
    "loraStack": {
        "count": (2, 2),
        "strength": (0.5, 0.9),
        "pool": CARDED_POOL,
        "weights": None,
    },
}

# The same pool as a manifest: the axis enabled, count [2, 2] — every
# drawn stack holds exactly two of the three members. seed = "keep" with
# three samplers keeps three bound variants distinct per slot.
CARDED_TOML = (
    '[mutate]\nseed = "keep"\nsamplers = ["euler", "dpmpp_2m", "uni_pc"]\n\n'
    "[mutate.loraStack]\nenable = true\ncount = [2, 2]\nstrength = [0.5, 0.9]\n\n"
    '[[model]]\nname = "krea2-lora-inkline"\n'
    'dest = "loras/krea2_inkline.safetensors"\nenabled = true\n'
    'category = "position"\ntrigger = "n3lson,"\n'
    'requires = ["bent over", "looking back"]\n\n'
    '[[model]]\nname = "krea2-lora-inkwash"\n'
    'dest = "loras/krea2_inkwash.safetensors"\nenabled = true\n'
    'category = "act"\nrequires = ["kneeling"]\n\n'
    '[[model]]\nname = "krea2-lora-darkbrush"\n'
    'dest = "loras/krea2_darkbrush.safetensors"\nenabled = true\n'
    'category = "style"\ntrigger = "d4rk,"\n'
)


def _write_seed_file_with_stacks(path, prompts, stacks):
    """The author's batch with the draw's stacks bound: one
    `{loras, requires, triggers}` entry per prompt."""
    path.write_text(json.dumps({"prompts": prompts, "stacks": stacks}))
    return str(path)


def _job_loaders(graph):
    """The graph's LoraLoaderModelOnly nodes."""
    return [
        node
        for node in graph.values()
        if isinstance(node, dict) and node.get("class_type") == "LoraLoaderModelOnly"
    ]


def test_bound_stack_skips_the_draw():
    # A bound stack consumes none of the stream: the prompt, sampler and
    # seed draws are EXPECTED_SEED1's verbatim (the no-axis golden) and
    # every variant carries the caller's stack — the author's draw, never
    # a fresh one of the mutator's own.
    bound = (("krea2-lora-inkline", 0.7),)
    out = mutate.mutate(PROMPT, RULES_WITH_STACK, seed=1, n=3, stack=bound)
    assert [(v.prompt, v.sampler, v.seed) for v in out] == [
        (e.prompt, e.sampler, e.seed) for e in EXPECTED_SEED1
    ]
    assert all(v.loras == bound for v in out)


def test_draw_stacks_shape_and_determinism():
    # Two fresh Random(2) streams draw equal lists, and every entry is
    # the drawn stack's own facts: two loras inside the strength bounds,
    # requires in stack order then each member's own order, triggers only
    # from the members that carry one. Seed 2's first entry draws inkline
    # before inkwash, so the requires order is inkline's two words then
    # inkwash's one, and inkwash's absent trigger is not in the list.
    first = mutate.draw_stacks(CARDED_RULES, 3, random.Random(2))
    assert first == mutate.draw_stacks(CARDED_RULES, 3, random.Random(2))
    pool_names = {entry["name"] for entry in CARDED_POOL}
    for entry in first:
        assert len(entry["loras"]) == 2
        for name, strength in entry["loras"]:
            assert name in pool_names
            assert 0.5 <= strength <= 0.9
        assert entry["checkpoint"] is None
    entry = first[0]
    assert [name for name, _ in entry["loras"]] == [
        "krea2-lora-inkline",
        "krea2-lora-inkwash",
    ]
    assert entry["requires"] == ["bent over", "looking back", "kneeling"]
    assert entry["triggers"] == ["n3lson,"]


def test_draw_stacks_dedups_shared_requires_words():
    # Two members sharing the word "kneeling" — inkwash (act) and kneeler
    # (detail), different categories so they co-occur in one stack: the
    # shared word appears once in the entry's requires. Seed 1 over ten
    # slots draws the pair once.
    pool = CARDED_POOL + (
        {
            "name": "krea2-lora-kneeler",
            "dest": "loras/krea2_kneeler.safetensors",
            "category": "detail",
            "incompatible": frozenset(),
            "trigger": None,
            "requires": ("kneeling",),
        },
    )
    rules = dict(CARDED_RULES)
    rules["loraStack"] = dict(CARDED_RULES["loraStack"], pool=pool)
    entries = mutate.draw_stacks(rules, 10, random.Random(1))
    for entry in entries:
        words = entry["requires"]
        assert len(words) == len({w.lower() for w in words})
    shared = [
        e
        for e in entries
        if {"krea2-lora-inkwash", "krea2-lora-kneeler"}
        <= {name for name, _ in e["loras"]}
    ]
    assert shared
    assert shared[0]["requires"] == ["kneeling"]


def test_draw_stacks_cli_writes_the_file_and_prints_the_grammar(tmp_path, capsys):
    # The --draw-stacks arm: the file lands under lab/prompts as
    # stacks-<UTC>.json carrying {ts, world, seed, stacks}, the last
    # stdout line is the grammar `drawn <N> <path>`, and a second run
    # with the same seed writes an equal stacks array.
    root = _make_world(
        tmp_path, [("a.png", json.dumps(KREA2_CHAIN), 42)], ["a.png"], CARDED_TOML
    )
    args = [
        "--world",
        "sfw",
        "--root",
        root,
        "--draw-stacks",
        "2",
        "--seed",
        "1",
        "--comfy-url",
        "http://127.0.0.1:1",
    ]
    mutate.main(args)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    match = re.match(r"^drawn 2 (\S+)$", line)
    assert match
    payload = json.loads(pathlib.Path(match.group(1)).read_text())
    assert payload["world"] == "sfw"
    assert payload["seed"] == 1
    assert len(payload["stacks"]) == 2
    mutate.main(args)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    match = re.match(r"^drawn 2 (\S+)$", line)
    again = json.loads(pathlib.Path(match.group(1)).read_text())
    assert again["stacks"] == payload["stacks"]


def test_draw_stacks_axis_off_exits_3(tmp_path, capsys):
    # A world without an enabled [mutate.loraStack] has nothing to draw:
    # stderr says so, stdout carries the grammar's empty arm, exit 3.
    root = _make_world(
        tmp_path,
        [("a.png", json.dumps(KREA2_CHAIN), 42)],
        ["a.png"],
        MUTATE_RULES_TOML,
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--draw-stacks",
                "2",
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 3
    captured = capsys.readouterr()
    assert captured.out.strip() == "drawn 0 stacks in sfw"
    assert "nothing to draw" in captured.err


def test_draw_stacks_dry_run_writes_nothing(tmp_path, capsys):
    # --dry-run prints the JSON and writes nothing: no lab/prompts
    # directory, no file, no job.
    root = _make_world(
        tmp_path, [("a.png", json.dumps(KREA2_CHAIN), 42)], ["a.png"], CARDED_TOML
    )
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--draw-stacks",
            "2",
            "--seed",
            "1",
            "--dry-run",
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert len(payload["stacks"]) == 2
    prompts_dir = pathlib.Path(root) / "worlds" / "sfw" / "lab" / "prompts"
    assert not prompts_dir.exists()
    assert _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_seed_file_binds_the_batch_stacks(tmp_path, capsys):
    # The binding: slot 0's jobs carry exactly one loader — inkline at
    # the authored strength 0.7 — and slot 1's carry inkwash at 0.6; the
    # draw never enters (count [2, 2] would draw two members), and the
    # bound line counts all six.
    root = _make_world(
        tmp_path, [("a.png", json.dumps(KREA2_CHAIN), 42)], ["a.png"], CARDED_TOML
    )
    seed_file = _write_seed_file_with_stacks(
        tmp_path / "batch.json",
        [
            "a woman bent over looking back at the camera",
            "a woman kneeling on the floor",
        ],
        [
            {
                "loras": [["krea2-lora-inkline", 0.7]],
                "requires": ["bent over", "looking back"],
                "triggers": ["n3lson,"],
            },
            {
                "loras": [["krea2-lora-inkwash", 0.6]],
                "requires": ["kneeling"],
                "triggers": [],
            },
        ],
    )
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--seed",
            "1",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    rows = _jobs(root).execute("SELECT prompt FROM jobs ORDER BY rowid").fetchall()
    assert len(rows) == 6
    seen = {"krea2_inkline.safetensors": 0, "krea2_inkwash.safetensors": 0}
    for row in rows:
        loaders = _job_loaders(json.loads(row["prompt"]))
        assert len(loaders) == 1
        loader = loaders[0]
        seen[loader["inputs"]["lora_name"]] += 1
        strength = loader["inputs"]["strength_model"]
        if loader["inputs"]["lora_name"] == "krea2_inkline.safetensors":
            assert strength == 0.7
        else:
            assert strength == 0.6
    assert seen == {"krea2_inkline.safetensors": 3, "krea2_inkwash.safetensors": 3}
    assert "bound 6 stacks, dropped 0" in capsys.readouterr().out


def test_requires_unmet_drops_the_stack_and_counts(tmp_path, capsys):
    # Slot 0's prompt ignores both of inkline's requires words: its three
    # variants drop the stack (no loader, the KSampler back at the
    # chain's source, no trigger in the text), each drop says so on
    # stderr by slot and variant, and the bound line counts the drops
    # beside slot 1's three bound stacks.
    root = _make_world(
        tmp_path, [("a.png", json.dumps(KREA2_CHAIN), 42)], ["a.png"], CARDED_TOML
    )
    seed_file = _write_seed_file_with_stacks(
        tmp_path / "batch.json",
        ["a woman at a window", "a woman kneeling on the floor"],
        [
            {
                "loras": [["krea2-lora-inkline", 0.7]],
                "requires": ["bent over", "looking back"],
                "triggers": ["n3lson,"],
            },
            {
                "loras": [["krea2-lora-inkwash", 0.6]],
                "requires": ["kneeling"],
                "triggers": [],
            },
        ],
    )
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--seed",
            "1",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    rows = _jobs(root).execute("SELECT prompt FROM jobs ORDER BY rowid").fetchall()
    assert len(rows) == 6
    dropped = 0
    for row in rows:
        graph = json.loads(row["prompt"])
        loaders = _job_loaders(graph)
        if not loaders:
            dropped += 1
            assert graph["11"]["inputs"]["model"] == ["1", 0]
            assert graph["9"]["inputs"]["text"] == "a woman at a window"
        else:
            assert loaders[0]["inputs"]["lora_name"] == "krea2_inkwash.safetensors"
    assert dropped == 3
    captured = capsys.readouterr()
    assert captured.err.count("requires unmet") == 3
    assert (
        "mutate: slot 0 variant 0: requires unmet (bent over, looking back):"
        " stack dropped" in captured.err
    )
    assert "bound 3 stacks, dropped 3" in captured.out


def test_word_rule_is_token_bounded():
    # A whole-token match, case-insensitive: "anal" is not "analog" (the
    # right boundary), "over" is not "leftover" (the left boundary),
    # "Anal" is "ANAL play" (case), and a comma does not extend a word.
    assert mutate._word_in("anal", "an analog camera") is False
    assert mutate._word_in("over", "a leftover on the rail") is False
    assert mutate._word_in("bent over", "she is bent over the rail") is True
    assert mutate._word_in("Anal", "ANAL play") is True
    assert mutate._word_in("kneeling", "kneeling,") is True


def test_triggers_prepended_at_enqueue(tmp_path):
    # Slot 0's bound stack is inkline then darkbrush: its jobs' positive
    # text starts with "n3lson, d4rk, " — each member's trigger that is
    # not None, stack order — and ends with the variant's prompt. Slot 1
    # drops the stack, and a dropped stack's text carries no trigger.
    root = _make_world(
        tmp_path, [("a.png", json.dumps(KREA2_CHAIN), 42)], ["a.png"], CARDED_TOML
    )
    seed_file = _write_seed_file_with_stacks(
        tmp_path / "batch.json",
        ["a woman bent over looking back at the camera", "a woman at a window"],
        [
            {
                "loras": [["krea2-lora-inkline", 0.7], ["krea2-lora-darkbrush", 0.5]],
                "requires": ["bent over", "looking back"],
                "triggers": ["n3lson,", "d4rk,"],
            },
            {
                "loras": [["krea2-lora-inkline", 0.7]],
                "requires": ["bent over", "looking back"],
                "triggers": ["n3lson,"],
            },
        ],
    )
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--seed",
            "1",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    rows = _jobs(root).execute("SELECT prompt FROM jobs ORDER BY rowid").fetchall()
    assert len(rows) == 6
    bound_texts = []
    dropped_texts = []
    for row in rows:
        graph = json.loads(row["prompt"])
        if _job_loaders(graph):
            bound_texts.append(graph["9"]["inputs"]["text"])
        else:
            dropped_texts.append(graph["9"]["inputs"]["text"])
    assert len(bound_texts) == 3
    for text in bound_texts:
        assert text.startswith("n3lson, d4rk, ")
        assert text.endswith("a woman bent over looking back at the camera")
    assert len(dropped_texts) == 3
    for text in dropped_texts:
        assert text == "a woman at a window"


def test_stacks_length_mismatch_exits_2(tmp_path, capsys):
    # One prompt, two entries: the shape is refused before any job.
    root = _make_world(
        tmp_path, [("a.png", json.dumps(KREA2_CHAIN), 42)], ["a.png"], CARDED_TOML
    )
    seed_file = _write_seed_file_with_stacks(
        tmp_path / "batch.json",
        ["a woman kneeling on the floor"],
        [
            {
                "loras": [["krea2-lora-inkwash", 0.6]],
                "requires": ["kneeling"],
                "triggers": [],
            },
            {
                "loras": [["krea2-lora-inkline", 0.7]],
                "requires": [],
                "triggers": [],
            },
        ],
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--seed-file",
                seed_file,
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    assert '"stacks" must be one {loras, requires, triggers} entry per prompt' in (
        capsys.readouterr().err
    )
    assert _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_stack_naming_unknown_lora_exits_2(tmp_path, capsys):
    # A stack naming a LoRA outside the carded pool is refused by slot
    # and name, before any job.
    root = _make_world(
        tmp_path, [("a.png", json.dumps(KREA2_CHAIN), 42)], ["a.png"], CARDED_TOML
    )
    seed_file = _write_seed_file_with_stacks(
        tmp_path / "batch.json",
        ["a woman kneeling on the floor"],
        [
            {
                "loras": [["krea2-lora-ghost", 0.6]],
                "requires": ["kneeling"],
                "triggers": [],
            }
        ],
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--seed-file",
                seed_file,
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    assert "slot 0 names krea2-lora-ghost, not in the carded pool" in (
        capsys.readouterr().err
    )
    assert _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_stacks_without_axis_exits_2(tmp_path, capsys):
    # A batch that carries stacks needs the axis: a world without an
    # enabled [mutate.loraStack] refuses it by name, before any job.
    root = _make_world(
        tmp_path,
        [("a.png", json.dumps(KREA2_CHAIN), 42)],
        ["a.png"],
        MUTATE_RULES_TOML,
    )
    seed_file = _write_seed_file_with_stacks(
        tmp_path / "batch.json",
        ["a woman kneeling on the floor"],
        [
            {
                "loras": [["krea2-lora-inkwash", 0.6]],
                "requires": ["kneeling"],
                "triggers": [],
            }
        ],
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--seed-file",
                seed_file,
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    assert "carries stacks but sfw has no enabled [mutate.loraStack]" in (
        capsys.readouterr().err
    )
    assert _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_seed_file_without_stacks_is_todays_bytes(tmp_path, capsys):
    # The negative guard: a batch without `stacks` runs today's path —
    # the drawn stacks land in the jobs (count [2, 2]: two loaders each)
    # and no `bound` line prints. The pre-GN50 composition — mutate(),
    # then _substitute, the weights threaded exactly as the branch does —
    # reproduces every job byte for byte.
    root = _make_world(
        tmp_path, [("a.png", json.dumps(KREA2_CHAIN), 42)], ["a.png"], CARDED_TOML
    )
    prompts = ["a neon koi", "a neon koi at dusk"]
    seed_file = _write_seed_file(tmp_path / "batch.json", prompts)
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--seed",
            "1",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    captured = capsys.readouterr()
    assert "bound" not in captured.out
    rows = [
        row["prompt"]
        for row in _jobs(root).execute("SELECT prompt FROM jobs ORDER BY rowid")
    ]
    assert len(rows) == 6
    for row in rows:
        assert len(_job_loaders(json.loads(row))) == 2
    rules, weights = _world_rules_and_weights(root)
    rules["loraStack"]["weights"] = weights
    graph = json.loads(json.dumps(KREA2_CHAIN))
    expected = []
    for index, prompt in enumerate(prompts):
        for variant in mutate.mutate(prompt, rules, 1 + index, 3):
            expected.append(
                json.dumps(
                    mutate._substitute(graph, "a neon koi", variant, rules["loraStack"])
                )
            )
    assert rows == expected


# --- GN53: base models — the checkpoint is drawn from its pool and
# written, never inherited. The same card treatment for [[model]] rows
# under diffusion_models/ (the worlds' graphs load the model through
# UNETLoader, the diffusion_models/ folder — a checkpoints/ row is not a
# base model here): the pool is every enabled diffusion_models/ row whose
# unmatched is not true, one checkpoint is drawn per variant — a pool of
# one takes no draw, correct at N = 1 and real the moment a second
# checkpoint is adopted — and the row's dest basename is written into
# every UNETLoader node's unet_name. A graph with no UNETLoader is
# refused by name (BaseModelUnsupported, exit 2), never a silent skip.

DIFF_A = """\
[[model]]
name = "krea2-base"
dest = "diffusion_models/krea2_fp8.safetensors"
enabled = true
"""

DIFF_B = """\
[[model]]
name = "krea2-flux"
dest = "diffusion_models/flux_fp8.safetensors"
enabled = true
"""

DIFF_UNMATCHED = """\
[[model]]
name = "krea2-base-old"
dest = "diffusion_models/krea2_fp8_old.safetensors"
enabled = true
unmatched = true
"""

# The normalized checkpoint entry — the shape `_lora_stack` returns
# (Interfaces 2): name, dest, trigger, version.
CKPT_A = {
    "name": "krea2-base",
    "dest": "diffusion_models/krea2_fp8.safetensors",
    "trigger": None,
    "version": None,
}

CKPT_B = {
    "name": "krea2-flux",
    "dest": "diffusion_models/flux_fp8.safetensors",
    "trigger": None,
    "version": None,
}

# KREA2_STACK plus the one-checkpoint pool: the write pass's own fixture.
KREA2_STACK_WITH_CKPT = dict(KREA2_STACK, checkpoints=(CKPT_A,))


def test_checkpoint_pool_is_enabled_diffusion_models_rows(tmp_path):
    # Interfaces 1-2: the pool is the enabled diffusion_models/ rows whose
    # unmatched is not true, in manifest order — the BASE fixture's
    # checkpoints/ row is excluded (not a base model here) and so is the
    # unmatched row; the entry carries name, dest, trigger, version.
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        _stack_manifest(
            "enable = true\ncount = [1, 2]\nstrength = [0.5, 0.9]\n",
            DIFF_A + BASE + DIFF_UNMATCHED + DIFF_B + DARKBRUSH + INKWASH,
        )
    )
    stack = mutate.load_rules(str(manifest))["loraStack"]
    assert [entry["name"] for entry in stack["checkpoints"]] == [
        "krea2-base",
        "krea2-flux",
    ]
    assert stack["checkpoints"][0] == {
        "name": "krea2-base",
        "dest": "diffusion_models/krea2_fp8.safetensors",
        "trigger": None,
        "version": None,
    }


def test_lora_card_fields_refused_on_a_base_row(tmp_path):
    # Interfaces 2: category, requires and incompatible are LoRA card
    # fields — on a diffusion_models/ row they are a configuration error,
    # refused at load by name.
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        _stack_manifest(
            "enable = true\ncount = [1, 2]\nstrength = [0.5, 0.9]\n",
            DIFF_A + 'category = "act"\n' + DARKBRUSH + INKWASH,
        )
    )
    with pytest.raises(ValueError, match=re.escape("are LoRA card fields")):
        mutate.load_rules(str(manifest))


def test_one_checkpoint_takes_no_draw():
    # Interfaces 4: a pool of exactly one checkpoint takes NO draw — the
    # stream never moves, so the with-stack golden holds field for field,
    # every variant now carrying the one name. A pool of one beside a
    # "one draw of one" would shift every later candidate and break the
    # golden — that is M4's own arm.
    rules = dict(RULES_WITH_STACK)
    rules["loraStack"] = dict(RULES_WITH_STACK["loraStack"], checkpoints=(CKPT_A,))
    variants = mutate.mutate(PROMPT, rules, seed=1, n=3)
    assert [(v.prompt, v.sampler, v.seed, v.loras) for v in variants] == [
        (e.prompt, e.sampler, e.seed, e.loras) for e in EXPECTED_SEED1_LORASTACK
    ]
    assert all(v.checkpoint == "krea2-base" for v in variants)


def test_two_checkpoints_are_drawn():
    # Interfaces 4: two or more checkpoints draw rng.choice over the names,
    # after the stack's draws on the one stream — over seeds 1..20 both
    # names appear.
    rules = dict(RULES_WITH_STACK)
    rules["loraStack"] = dict(
        RULES_WITH_STACK["loraStack"], checkpoints=(CKPT_A, CKPT_B)
    )
    drawn = set()
    for seed in range(1, 21):
        for variant in mutate.mutate(PROMPT, rules, seed=seed, n=3):
            drawn.add(variant.checkpoint)
    assert drawn == {"krea2-base", "krea2-flux"}


def test_substitute_writes_the_checkpoint_node():
    # Interfaces 5: every UNETLoader node takes the row's dest BASENAME
    # (never the dest, never the manifest name); checkpoint None leaves
    # the node's stored file untouched.
    variant = mutate.Variant(
        prompt="a neon koi", sampler=None, seed=1, checkpoint="krea2-base"
    )
    out = mutate._substitute(
        KREA2_CHAIN, "a neon koi", variant, lora_stack=KREA2_STACK_WITH_CKPT
    )
    assert out["1"]["inputs"]["unet_name"] == "krea2_fp8.safetensors"
    plain = mutate.Variant(prompt="a neon koi", sampler=None, seed=1)
    out = mutate._substitute(
        KREA2_CHAIN, "a neon koi", plain, lora_stack=KREA2_STACK_WITH_CKPT
    )
    assert out["1"]["inputs"]["unet_name"] == "flux.safetensors"


def test_no_unetloader_is_refused_by_name(tmp_path, capsys):
    # Interfaces 5: a graph whose model source is a CheckpointLoaderSimple
    # has no UNETLoader to write the drawn checkpoint into — refused by
    # name (BaseModelUnsupported, LoraChainUnsupported's shape), never a
    # silent skip; through --seed-file it is exit 2, the stderr text, and
    # zero jobs.
    graph = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "flux.safetensors"},
        },
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": "a neon koi"}},
        "11": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["9", 0],
                "seed": 42,
                "sampler_name": "euler",
            },
        },
    }
    with pytest.raises(mutate.BaseModelUnsupported) as exc:
        mutate._substitute(
            graph,
            "a neon koi",
            mutate.Variant(
                prompt="a neon koi", sampler=None, seed=1, checkpoint="krea2-base"
            ),
            lora_stack=KREA2_STACK_WITH_CKPT,
        )
    assert exc.value.node_ids == []
    assert "no UNETLoader node to write the checkpoint into" in str(exc.value)
    root = _make_world(
        tmp_path,
        [("a.png", json.dumps(graph), 42)],
        ["a.png"],
        CARDED_TOML + DIFF_A,
    )
    seed_file = _write_seed_file(tmp_path / "batch.json", ["a neon koi"])
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root,
                "--seed-file",
                seed_file,
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    assert "base model unsupported: no UNETLoader node" in capsys.readouterr().err
    assert _jobs(root).execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_draw_stacks_entries_carry_the_checkpoint_and_its_trigger_first():
    # Interfaces 4: the coupled draw's entry carries the drawn checkpoint,
    # and the checkpoint's own trigger — when it has one — leads the
    # triggers list (the base model anchors the render before any LoRA).
    ckpt = dict(CKPT_A, trigger="krea,")
    rules = dict(CARDED_RULES)
    rules["loraStack"] = dict(CARDED_RULES["loraStack"], checkpoints=(ckpt,))
    entries = mutate.draw_stacks(rules, 5, random.Random(3))
    assert len(entries) == 5
    for entry in entries:
        assert entry["checkpoint"] == "krea2-base"
        assert entry["triggers"][0] == "krea,"


def test_binder_writes_the_slot_checkpoint(tmp_path, capsys):
    # Interfaces 6: a slot naming a pool checkpoint binds it — every job's
    # UNETLoader carries the row's dest basename — and a dropped stack
    # keeps its checkpoint (the base model is not a requires question);
    # a slot naming an unknown checkpoint is refused by slot and name,
    # before any job.
    root = _make_world(
        tmp_path,
        [("a.png", json.dumps(KREA2_CHAIN), 42)],
        ["a.png"],
        CARDED_TOML + DIFF_A,
    )
    seed_file = _write_seed_file_with_stacks(
        tmp_path / "batch.json",
        ["a woman bent over looking back at the camera", "a woman at a window"],
        [
            {
                "loras": [["krea2-lora-inkline", 0.7]],
                "requires": ["bent over", "looking back"],
                "triggers": ["n3lson,"],
                "checkpoint": "krea2-base",
            },
            {
                # requires unmet on this slot: the stack drops, the
                # checkpoint stays.
                "loras": [["krea2-lora-inkline", 0.7]],
                "requires": ["bent over", "looking back"],
                "triggers": ["n3lson,"],
                "checkpoint": "krea2-base",
            },
        ],
    )
    mutate.main(
        [
            "--world",
            "sfw",
            "--root",
            root,
            "--n",
            "3",
            "--seed",
            "1",
            "--seed-file",
            seed_file,
            "--comfy-url",
            "http://127.0.0.1:1",
        ]
    )
    rows = _jobs(root).execute("SELECT prompt FROM jobs ORDER BY rowid").fetchall()
    assert len(rows) == 6
    for row in rows:
        graph = json.loads(row["prompt"])
        assert graph["1"]["inputs"]["unet_name"] == "krea2_fp8.safetensors"
    root_b = _make_world(
        tmp_path / "b",
        [("a.png", json.dumps(KREA2_CHAIN), 42)],
        ["a.png"],
        CARDED_TOML + DIFF_A,
    )
    seed_file = _write_seed_file_with_stacks(
        tmp_path / "ghost.json",
        ["a woman kneeling on the floor"],
        [
            {
                "loras": [["krea2-lora-inkwash", 0.6]],
                "requires": ["kneeling"],
                "triggers": [],
                "checkpoint": "ghost-base",
            }
        ],
    )
    with pytest.raises(SystemExit) as exc:
        mutate.main(
            [
                "--world",
                "sfw",
                "--root",
                root_b,
                "--seed-file",
                seed_file,
                "--comfy-url",
                "http://127.0.0.1:1",
            ]
        )
    assert exc.value.code == 2
    assert "slot 0 names checkpoint ghost-base, not in the pool" in (
        capsys.readouterr().err
    )
    assert _jobs(root_b).execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
