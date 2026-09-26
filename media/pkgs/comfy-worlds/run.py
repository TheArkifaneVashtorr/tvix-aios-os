r"""comfy-run: the per-world authoring supervisor (GN17, spec §4 Change 5).

The loop that advances a world. Each iteration: when the queue is at or
below `--low-water`, start the model unit, run comfy-author against the
loopback model, stop the model unit, start the generator unit — systemd's
`Conflicts=` trades the GPU between them — and, when the author carried at
least one prompt, expand the batch through `comfy-mutate --seed-file`. Then
`queue.run_once` and `--tick` seconds of sleep.

The supervisor NEVER reasons about VRAM: it starts and stops units and
`Conflicts=` does the rest (the spec's bold). It is a user unit itself,
started by the operator beside the mutator, `wantedBy = []`.

The halt is the two-consecutive-empty rule: two author exit-3 batches in
a row exit 3 with one journal line naming the cause. `SuccessExitStatus
= "3"` leaves the unit `inactive` rather than `failed`, and the module
deliberately sets no `Restart=` — a restart directive would respin the
loop forever and silently defeat the halt.

Exit grammar (GN16's author grammar feeds it, so a "zero prompts on
exit 0" branch would be dead code and is deliberately absent):

- **0** — the loop ended at `--max-batches` (the test seam; unbounded in
  the unit, where only the halt or an abort ends it).
- **3** — the halt: two consecutive authoring batches yielded zero
  prompts (both were author exit 3, the one and only empty outcome).
- **4** — a loud abort: a `systemctl` call failed, or comfy-author
  exited 2 (a bad invocation — the world was never configured — is not
  an empty batch and never a spin; the author's own cause line, which
  names the file, is echoed to stderr before the abort line), or
  comfy-mutate failed on the batch.

GN45 gives the loop a voice: every phase transition of the batch
grammar above writes `<root>/worlds/<world>/run-status.json` — a
current-value cell (never a log) the feed reads. The write is atomic
(a `.tmp` sibling renamed over the cell, so a reader never sees a
partial file) and never fatal: a status failure is swallowed whole,
because generation outranks telemetry.

GN51: the supervisor draws before it authors (spec §3.3) — each
authoring iteration runs `comfy-mutate --draw-stacks` first and hands
the drawn stacks file to comfy-author as `--stacks-file` (the draw's
exit 3, no loraStack, authors uncoupled; any other exit aborts). The
raised history (Decision 8) is forwarded as `--history`, and
`--draw-seed` names the draw's seed (the 32-bit clock by default).

Seam: queue.py is loaded by path (`FEED_QUEUE_PY`, the same seam
comfy-mutate reads, and queue.py loads feed_index via `FEED_INDEX_PY`);
the wrapper exports both. Stdlib only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
_queue_path = os.environ.get("FEED_QUEUE_PY") or str(_HERE / "queue.py")
_queue_spec = importlib.util.spec_from_file_location("queue", _queue_path)
queue = importlib.util.module_from_spec(_queue_spec)
_queue_spec.loader.exec_module(queue)

_HALT_CAUSE = "two consecutive authoring batches yielded zero prompts"
# GN16's exit-0 grammar: the last stdout line is `authored <n> <path>`
# with n >= 1.
_AUTHORED = re.compile(r"^authored (\d+) (\S+)$")
# GN50's draw grammar: the last stdout line is `drawn <n> <path>`.
_DRAWN = re.compile(r"^drawn (\d+) (\S+)$")


def _status_path(args):
    """`<root>/worlds/<world>/run-status.json` — the phase cell's path
    (GN45 Interfaces 1)."""
    return pathlib.Path(args.root) / "worlds" / args.world / "run-status.json"


def _write_status(args, phase, queued, batch):
    try:
        _write_status_file(args, phase, queued, batch)
    except OSError:
        # Interfaces 3: telemetry never aborts the loop — generation
        # outranks status, so a write failure is swallowed whole.
        pass


def _write_status_file(args, phase, queued, batch):
    """One atomic status write: `{"phase", "queued", "batch", "ts"}` with
    the phase from the closed enum (Interfaces 2) and the ts an RFC3339
    UTC stamp. The cell lands through a `.tmp` sibling renamed over it,
    so a reader never sees a partial file (Interfaces 1)."""
    doc = {
        "phase": phase,
        "queued": queued,
        "batch": batch,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    path = _status_path(args)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _parse_args(argv):
    parser = argparse.ArgumentParser(prog="comfy-run")
    parser.add_argument("--world", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--n-prompts",
        type=int,
        default=8,
        help="base prompts the author asks the model for (M)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=20,
        help="liked/disliked verdict window the author reads (K)",
    )
    parser.add_argument(
        "--history",
        type=int,
        default=100,
        help="prior authored batches the author checks for duplicates"
        " (the raised value; Decision 8)",
    )
    parser.add_argument(
        "--draw-seed",
        type=int,
        default=None,
        help="the coupled draw's seed (default: the clock, 32-bit)",
    )
    parser.add_argument(
        "--n-variants",
        type=int,
        default=3,
        help="variants per authored prompt comfy-mutate enqueues (N)",
    )
    parser.add_argument(
        "--low-water",
        type=int,
        default=2,
        help="author a batch when at most this many jobs are queued",
    )
    parser.add_argument(
        "--tick",
        type=int,
        default=120,
        help="seconds between iterations",
    )
    parser.add_argument(
        "--model-url",
        required=True,
        help="the loopback model URL forwarded to comfy-author",
    )
    parser.add_argument(
        "--model-wait",
        type=int,
        default=120,
        help="seconds comfy-author keeps retrying a model that does not"
        " exist yet (the wait budget; GN21)",
    )
    parser.add_argument(
        "--model-timeout",
        type=int,
        default=300,
        help="seconds one request may wait on a live, generating model"
        " (the read timeout; terminal, never retried; GN21)",
    )
    parser.add_argument(
        "--model-unit",
        required=True,
        help="the model user unit started around each authoring batch",
    )
    parser.add_argument(
        "--generator-unit",
        required=True,
        help="the generator user unit restarted after each authoring batch",
    )
    parser.add_argument(
        "--comfy-url",
        required=True,
        help="the generator's loopback base URL (queue.submit's guard)",
    )
    # The three binaries: bare names for interactive use, absolute store
    # paths as rendered in the unit (never a PATH lookup there).
    parser.add_argument("--systemctl", default="systemctl")
    parser.add_argument("--author", default="comfy-author")
    parser.add_argument("--mutate", default="comfy-mutate")
    parser.add_argument(
        "--model-path",
        default=None,
        help="forwarded to comfy-author for the batch file's provenance",
    )
    parser.add_argument(
        "--model-sha256",
        default=None,
        help="forwarded to comfy-author for the batch file's provenance",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="stop after this many iterations (a test seam)",
    )
    return parser.parse_args(argv)


def _systemctl(args, verb, unit):
    """`systemctl --user <verb> <unit>` — a nonzero exit aborts loudly
    (exit 4, one stderr line naming the unit), never a spin."""
    argv = [args.systemctl, "--user", verb, unit]
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        print(
            f"comfy-run: systemctl --user {verb} {unit} failed with exit"
            f" {proc.returncode} in world {args.world}; aborting",
            file=sys.stderr,
        )
        sys.exit(4)


def _author_argv(args, stacks_path=None):
    argv = [
        args.author,
        "--world",
        args.world,
        "--root",
        args.root,
        "--n",
        str(args.n_prompts),
        "--window",
        str(args.window),
        "--model-wait",
        str(args.model_wait),
        "--model-timeout",
        str(args.model_timeout),
        "--model-url",
        args.model_url,
    ]
    if stacks_path is not None:
        argv += ["--history", str(args.history), "--stacks-file", stacks_path]
    else:
        argv += ["--history", str(args.history)]
    if args.model_path:
        argv += ["--model-path", args.model_path]
    if args.model_sha256:
        argv += ["--model-sha256", args.model_sha256]
    return argv


def _run_author(args, stacks_path=None):
    """comfy-author with its stderr echoed (its named cause lines belong in
    this unit's journal too). Returns `(exit code, stdout)`."""
    proc = subprocess.run(
        _author_argv(args, stacks_path), capture_output=True, text=True, check=False
    )
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode, proc.stdout


def _run_draw(args):
    """GN51: the supervisor draws before it authors (spec §3.3) —
    `comfy-mutate --draw-stacks` writes the stacks file the author is
    told about. Returns its path, or `None` when the world has no
    enabled [mutate.loraStack] (the draw's own empty arm, exit 3:
    authoring continues uncoupled). Any other exit is a loud abort, and
    so is an exit 0 whose last line is not the `drawn <n> <path>`
    grammar — a draw that violates its own grammar changes nothing here."""
    seed = args.draw_seed
    if seed is None:
        seed = int(time.time()) & 0xFFFFFFFF
    argv = [
        args.mutate,
        "--draw-stacks",
        str(args.n_prompts),
        "--world",
        args.world,
        "--root",
        args.root,
        "--comfy-url",
        args.comfy_url,
        "--seed",
        str(seed),
    ]
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    code = proc.returncode
    if code == 3:
        print(
            f"comfy-run: world {args.world} has no loraStack; authoring uncoupled",
            file=sys.stderr,
        )
        return None
    if code != 0:
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        print(
            f"comfy-run: comfy-mutate --draw-stacks exited {code} in"
            f" world {args.world}; aborting",
            file=sys.stderr,
        )
        sys.exit(4)
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    match = _DRAWN.match(lines[-1]) if lines else None
    if match is None:
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        print(
            f"comfy-run: comfy-mutate --draw-stacks exited {code} in"
            f" world {args.world}; aborting",
            file=sys.stderr,
        )
        sys.exit(4)
    return match.group(2)


def _run_mutate(args, batch_path):
    """`comfy-mutate --seed-file <batch>` — a nonzero exit aborts loudly."""
    argv = [
        args.mutate,
        "--seed-file",
        batch_path,
        "--n",
        str(args.n_variants),
        "--world",
        args.world,
        "--root",
        args.root,
        "--comfy-url",
        args.comfy_url,
    ]
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print(
            f"comfy-run: comfy-mutate exited {proc.returncode} on"
            f" {batch_path} in world {args.world}; aborting",
            file=sys.stderr,
        )
        sys.exit(4)


def _parse_authored(stdout):
    """`(n, path)` from the author's last stdout line, or `None` when it is
    not `authored <n> <path>`. GN16 guarantees `n >= 1` on exit 0."""
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return None
    match = _AUTHORED.match(lines[-1])
    if match is None:
        return None
    return int(match.group(1)), match.group(2)


def main(argv=None):
    args = _parse_args(argv)
    empty_streak = 0
    batches = 0
    queued = 0
    try:
        while args.max_batches is None or batches < args.max_batches:
            batches += 1
            conn = queue.open_db(args.root, args.world)
            queued = len(queue.pending(conn))
            if queued <= args.low_water:
                # The turn-taking: draw the stacks first (GN51 — the
                # author is told the draw's words before it writes), then
                # start the model, author, hand the GPU back (stop model /
                # start generator), then expand the batch. The supervisor
                # only starts and stops units — Conflicts= trades.
                _write_status(args, "authoring", queued, batches)
                stacks_path = _run_draw(args)
                _systemctl(args, "start", args.model_unit)
                code, stdout = _run_author(args, stacks_path)
                _systemctl(args, "stop", args.model_unit)
                _systemctl(args, "start", args.generator_unit)
                if code == 3:
                    # The one and only empty batch (GN16: exit 0 always
                    # carries n >= 1, exit 2 is an abort below).
                    empty_streak += 1
                    if empty_streak >= 2:
                        print(
                            f"comfy-run: halting in world {args.world}: {_HALT_CAUSE}",
                            file=sys.stderr,
                        )
                        sys.exit(3)
                elif code == 0:
                    authored = _parse_authored(stdout)
                    if authored is not None and authored[0] > 0:
                        _write_status(args, "mutating", queued, batches)
                        _run_mutate(args, authored[1])
                        empty_streak = 0
                    # No zero-prompt branch on exit 0: GN16's grammar makes
                    # it impossible; an author that violates its own grammar
                    # changes nothing here (no mutate, the streak stands).
                else:
                    # Exit 2 (or anything else) is a bad invocation, not an
                    # empty batch: the same loud stop a failed systemctl
                    # takes. The author's own cause line was echoed above.
                    print(
                        f"comfy-run: comfy-author exited {code} in world"
                        f" {args.world} (bad invocation); aborting",
                        file=sys.stderr,
                    )
                    sys.exit(4)
            _write_status(args, "rendering", queued, batches)
            queue.run_once(conn, args.comfy_url)
            _write_status(args, "waiting", queued, batches)
            time.sleep(args.tick)
            conn.close()
    except SystemExit as exc:
        # GN45 Interfaces 3: both terminal exits stamp the cell `halted`
        # before the raise — the two-empty halt (3) and the loud abort
        # (4), whose cause line was already printed above.
        if exc.code in (3, 4):
            _write_status(args, "halted", queued, batches)
        raise


if __name__ == "__main__":
    main()
