# Every derivation the comfyui-worlds module and this flake share. The module
# imports this file with the consuming host's pkgs (never self.packages);
# flake.nix re-exports the same attrs so `nix run .#comfy-worlds-init` works.
#
# Every wrapper execs an ABSOLUTE interpreter (`exec ${pkgs.bash}/bin/bash …`
# / `exec ${pkgs.python3}/bin/python3 …`), never a bare `bash`/`python3`
# resolved from PATH: under an empty PATH the bare form dies at
# `bash: command not found` (writeShellApplication only *prepends*
# runtimeInputs to the ambient PATH, so nothing is guaranteed). checks.
# comfy-worlds-unit proves this by running the built command with
# `PATH=/no-such-dir`.
{ pkgs }:
{
  comfy-worlds-init = pkgs.writeShellApplication {
    name = "comfy-worlds-init";
    runtimeInputs = [
      pkgs.git
      pkgs.coreutils
      pkgs.findutils
      pkgs.python3
    ];
    text = ''
      export FETCH_PY=${../media-fetch/fetch.py}
      exec ${pkgs.bash}/bin/bash ${./init.sh} "$@"
    '';
  };

  media-comfy = pkgs.writeShellApplication {
    name = "media-comfy";
    runtimeInputs = [
      pkgs.systemd
      pkgs.jq
      pkgs.coreutils
    ];
    text = ''exec ${pkgs.bash}/bin/bash ${./media-comfy.sh} "$@"'';
  };

  # ExecStartPre of each generator: the tree must exist and the lab must be a
  # git repo. An if-refusal (not `a && b || c`, which shellcheck flags) keeps
  # the named refusal behind a single exit.
  comfy-world-guard = pkgs.writeShellApplication {
    name = "comfy-world-guard";
    runtimeInputs = [ pkgs.coreutils ];
    text = ''
      root=$1; w=$2
      if [ ! -d "$root/worlds/$w/models" ] || [ ! -d "$root/worlds/$w/lab/.git" ]; then
        echo "comfy-worlds: world $w is not initialised under $root: run comfy-worlds-init" >&2
        exit 1
      fi
    '';
  };

  # ExecStartPre of comfy-author-model.service (GN14): the GGUF is declared
  # by path and digest (spec §1.2 — 22 GB of weights never enter the store),
  # so this guard is what makes the declaration verifiable rather than merely
  # imperative: it re-hashes the file on every unit start and refuses loudly
  # when it is absent, unreadable, or drifted — never serves quietly. The
  # comfy-world-guard shape (an if-refusal, not `a && b || c`).
  comfy-model-guard = pkgs.writeShellApplication {
    name = "comfy-model-guard";
    runtimeInputs = [ pkgs.coreutils ];
    text = ''
      path=$1; want=$2
      if [ ! -f "$path" ]; then
        echo "local-model: model file is absent or not a regular file: $path (want sha256 $want)" >&2
        exit 1
      fi
      if ! got=$(sha256sum "$path" | cut -d' ' -f1); then
        echo "local-model: model file is unreadable: $path (want sha256 $want)" >&2
        exit 1
      fi
      if [ "$got" != "$want" ]; then
        echo "local-model: model digest mismatch for $path: got $got, want $want" >&2
        exit 1
      fi
    '';
  };

  comfy-feed = pkgs.writeShellApplication {
    name = "comfy-feed";
    runtimeInputs = [
      pkgs.python3
      pkgs.systemd
    ];
    text = ''
      export FEED_INDEX_PY=${./feed_index.py}
      export FEED_QUEUE_PY=${./queue.py}
      # GN25: the shell mounts the deck client through /assets/app.{js,css},
      # which feed.py serves from these env paths (read at request time) —
      # the same seam shape as FEED_INDEX_PY/FEED_QUEUE_PY, so the packaged
      # app finds its assets without a second derivation.
      export FEED_APP_JS=${./app.js}
      export FEED_APP_CSS=${./app.css}
      exec ${pkgs.python3}/bin/python3 ${./feed.py} "$@"
    '';
  };

  # The mutator loop (GN6): reads liked renders, runs them through the grammar,
  # enqueues one kind=mutate job per variant, and drives queue.run_once once.
  # mutate.py imports feed_index.py and queue.py by path (FEED_INDEX_PY /
  # FEED_QUEUE_PY), so the wrapper exports those store paths the way comfy-feed
  # does; mutate.py itself is the wrapper's own exec target, so its own path
  # needs no export.
  comfy-mutate = pkgs.writeShellApplication {
    name = "comfy-mutate";
    runtimeInputs = [
      pkgs.python3
    ];
    text = ''
      export FEED_INDEX_PY=${./feed_index.py}
      export FEED_QUEUE_PY=${./queue.py}
      exec ${pkgs.python3}/bin/python3 ${./mutate.py} "$@"
    '';
  };

  # The author (GN16): reads the liked/disliked verdict windows, asks the
  # loopback model for bounded base prompts, validates the reply against the
  # world's [author] table and writes the batch file comfy-mutate
  # --seed-file expands. author.py imports feed_index.py (open_db) and
  # feed.py (_parse_graph/_positive_text) by path, so the wrapper exports
  # FEED_INDEX_PY (the existing seam) and FEED_SERVE_PY (feed.py's own
  # module) — two exports, two sources, neither inferred from a sibling
  # path.
  comfy-author = pkgs.writeShellApplication {
    name = "comfy-author";
    runtimeInputs = [
      pkgs.python3
    ];
    text = ''
      export FEED_INDEX_PY=${./feed_index.py}
      export FEED_SERVE_PY=${./feed.py}
      exec ${pkgs.python3}/bin/python3 ${./author.py} "$@"
    '';
  };

  # The per-world supervisor (GN17): owns the turn-taking — starts the model
  # unit, runs comfy-author, stops the model unit, starts the generator
  # (systemd's Conflicts= trades the GPU; the supervisor never reads VRAM) —
  # and the two-consecutive-empty halt. run.py imports queue.py by path
  # (FEED_QUEUE_PY, itself loading feed_index via FEED_INDEX_PY), so the
  # wrapper exports both seams exactly the way comfy-mutate's does.
  comfy-run = pkgs.writeShellApplication {
    name = "comfy-run";
    runtimeInputs = [
      pkgs.python3
    ];
    text = ''
      export FEED_INDEX_PY=${./feed_index.py}
      export FEED_QUEUE_PY=${./queue.py}
      exec ${pkgs.python3}/bin/python3 ${./run.py} "$@"
    '';
  };

  # GN48: the card tool's offline arm. cards.py imports mutate.py by path
  # (FEED_MUTATE_PY — GN47's validators and the installed-row rule are
  # mutate.py's, written once), and mutate.py itself imports feed_index.py
  # and queue.py at load (FEED_INDEX_PY / FEED_QUEUE_PY), so the wrapper
  # exports all three seams — the same shape comfy-mutate's has.
  comfy-cards = pkgs.writeShellApplication {
    name = "comfy-cards";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      export FEED_INDEX_PY=${./feed_index.py}
      export FEED_QUEUE_PY=${./queue.py}
      export FEED_MUTATE_PY=${./mutate.py}
      exec ${pkgs.python3}/bin/python3 ${./cards.py} "$@"
    '';
  };

  # GN18 — the owed PATH fix (spec §4 Change 7): media-fetch-models defined
  # once, here, as a worldsPkgs member wrapping the same
  # pkgs/media-fetch/fetch.py — the absolute-interpreter form this file's
  # header demands (the packages.nix copy it replaces used a bare `python3`).
  # The worlds module puts it on core's PATH beside the author and the
  # supervisor; media/packages.nix re-exports it by inherit, never by a
  # second writeShellApplication.
  media-fetch-models = pkgs.writeShellApplication {
    name = "media-fetch-models";
    runtimeInputs = [ pkgs.python3 ];
    text = ''exec ${pkgs.python3}/bin/python3 ${../media-fetch/fetch.py} "$@"'';
  };

  # The weekly, model-free upstream proposal (W5). The probe reads the ComfyUI
  # pin, the newest tag's requirements.txt, and the NVIDIA production branch
  # row; in dry run it only prints, otherwise it clones a throwaway workspace,
  # re-derives hashes, commits, and runs `nix flake check` there. It needs git,
  # nix (flake check / hash re-derivation) and coreutils (never a model).
  comfy-upstream-probe = pkgs.writeShellApplication {
    name = "comfy-upstream-probe";
    runtimeInputs = [
      pkgs.python3
      pkgs.git
      pkgs.nix
      pkgs.coreutils
    ];
    text = ''exec ${pkgs.python3}/bin/python3 ${../comfy-upstream-probe/probe.py} "$@"'';
  };
}
