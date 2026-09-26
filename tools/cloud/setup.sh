#!/usr/bin/env bash
# tools/cloud/setup.sh -- paste into the cloud environment's setup script.
# - Installs duckdb for querying the evidence/ snapshot.
# - Installs jq via apt if it is present (some of the driver scripts' docs
#   assume it; if apt is absent this only reports that and moves on --
#   never fetches a static jq binary from the network).
# - Puts the nix shim (tools/cloud/nix) ahead of any real nix on PATH, so
#   `nix develop -c CMD` in the workflow prompts execs CMD directly.
# - Exports FACTORY_TOOLBOX_REPO (this checkout, not the host's
#   /home/dalhaka/nixos-agent-env, which tools/factory/seat/factory-lib.sh
#   hardcodes as its default), FACTORY_PYTHON3_CMD=python3 (the two env
#   seams factory-lib.sh documents for a sandbox with python but no devShell
#   -- without them factory-dispatch's tasks.py call reaches for a host path
#   that does not exist here) and EVIDENCE_STORE=<this checkout>/evidence.
# - Idempotent: the .bashrc append is guarded by a marker line, so pasting
#   this script twice (a re-provisioned image, a retried setup step) never
#   duplicates the exports.
# - Symlinks $HOME/nixos-agent-env -> this checkout. docs/ledger/repos.toml's
#   `nixos-agent-env` row is `path = "~/nixos-agent-env"` (the OPERATOR'S
#   home path, baked into the committed tree); tasks.py's per-repo scans
#   (`check`'s review/task-classes/area-manifest rules, `brief`, `waves`,
#   `conflicts`) resolve THAT path, not `--root`, so in a cloud clone (a
#   different path, a different $HOME) they silently read nothing -- or, on
#   the measuring host itself, the live host repo instead of this checkout
#   (measured directly: this is why `check` looked red on all three
#   fixtures until the scan was isolated from that path). Refuses to
#   overwrite a REAL directory already at that path -- only ever replaces a
#   symlink (its own, from a prior run) or an absent path.
set -euo pipefail
python3 -m pip install --user duckdb ||
  python3 -m pip install --user --break-system-packages duckdb ||
  echo "tools/cloud/setup.sh: warn: duckdb not installed" >&2
if command -v apt-get >/dev/null 2>&1; then
  apt-get install -y jq || echo "tools/cloud/setup.sh: apt-get install jq failed" >&2
else
  echo "tools/cloud/setup.sh: no apt-get; jq not installed (not fetching a binary)" >&2
fi
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
export PATH="$repo_root/tools/cloud:$PATH"
export FACTORY_TOOLBOX_REPO="$repo_root"
export FACTORY_PYTHON3_CMD=python3
export EVIDENCE_STORE="$repo_root/evidence"
toplevel=$(cd -- "$repo_root" && git rev-parse --show-toplevel 2>/dev/null || true)
toplevel=${toplevel:-$repo_root}
link_target="${HOME:-/root}/nixos-agent-env"
if [ -L "$link_target" ] && [ "$(readlink -f -- "$link_target")" = "$(readlink -f -- "$toplevel")" ]; then
  echo "tools/cloud/setup.sh: $link_target already -> this checkout, nothing to do"
elif [ -e "$link_target" ] && [ ! -L "$link_target" ]; then
  echo "tools/cloud/setup.sh: $link_target exists and is a real directory -- refusing to touch it. tasks.py's per-repo scans need this name to resolve to this checkout (see above); point HOME elsewhere or move that directory, then re-run this script." >&2
else
  ln -sfn "$toplevel" "$link_target"
  echo "tools/cloud/setup.sh: linked $link_target -> $toplevel"
fi
# Idempotent: guarded by a marker comment so a re-run (a second `setup.sh`
# paste, or CI re-provisioning the same image) never appends duplicate lines.
marker="# tools/cloud/setup.sh ($repo_root)"
bashrc="${HOME:-/root}/.bashrc"
if ! grep -qF "$marker" "$bashrc" 2>/dev/null; then
  {
    echo "$marker"
    echo "export PATH=\"$repo_root/tools/cloud:\$PATH\""
    echo "export FACTORY_TOOLBOX_REPO=\"$repo_root\""
    echo "export FACTORY_PYTHON3_CMD=python3"
    echo "export EVIDENCE_STORE=\"$repo_root/evidence\""
  } >>"$bashrc"
fi
