#!/usr/bin/env bash
# PL19 (docs/superpowers/plans/2026-09-11-platform.md): assemble the
# publish-gate export the export-eval check evaluates — the sandboxed half
# of that check. This script builds a clean clone of the export: every path
# `publish.py export-list` prints, plus a fixed, named allowlist of files
# the flake's own outputs reference but docs/ledger/publish.toml cannot
# publish yet, git-committed so the tree stands on its own.
#
# Why assembly here and evaluation in flake.nix: the plan's design ran
# `nix flake show` and `nix flake check --no-build` inside this derivation's
# sandbox, which this host's daemon cannot serve — a sandboxed build mounts
# neither the nix daemon socket nor the store database, and __noChroot is
# refused for an untrusted user (measured 2026-09-26 on this checkout). So
# the check splits along that line: git and python run here, and the
# assembled export is evaluated by the ambient evaluator, which imports
# this derivation's flake.nix and calls its outputs function directly
# (the same assert-forcing shape as fleet-eval and the Helm declaration
# checks; builtins.getFlake refuses a ref that carries a derivation
# context, measured 2026-09-26).
#
# Allowlist entries are debt made visible, not debt excused: every entry
# names the subsystem whose own task should promote it out of `pending`,
# and a promoted file makes its copy a harmless overwrite, never a
# failure — the list shrinks as those tasks land. flake.nix and
# flake.lock are copied regardless of the manifest's classification: a
# flake needs its own manifest, and flake.nix's own pending status is the
# plan's named follow-on (Operator Question 1), not this check's to solve.
#
# Args: $1 = the flake source tree (${self}). Env: $out = the assembled,
# git-committed export. Facts print to the build log.
set -euo pipefail

src="$1"
: "${out:?runCommand exports out}"

# A hermetic git: no system or global config leaks in or out, and the
# identity is fixed so the snapshot commits are reproducible.
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=export-eval
export GIT_AUTHOR_EMAIL=export-eval@localhost
export GIT_COMMITTER_NAME=export-eval
export GIT_COMMITTER_EMAIL=export-eval@localhost

work="$PWD/source"
mkdir -p "$work"
cp -a "$src"/. "$work"/
# The dirty-tree source copy carries a read-only .git (nix includes it so
# self.dirtyRev can exist), and the snapshot repo below is this script's
# own — drop it before git init owns the directory.
chmod -R u+w "$work"
rm -rf "$work/.git"

# publish.py classifies git-tracked paths and a store path carries no
# .git, so the copy becomes a repo before the manifest runs over it.
git -C "$work" init -q
git -C "$work" add -A
git -C "$work" commit -qm "export-eval: source snapshot"

# The allowlist: pending files flake.nix itself references. Grouped by
# owner; comments name the subsystem whose task should promote the file.
allowlist="$PWD/allowlist.txt"
cat >"$allowlist" <<'EOF'
# Helm Home (F18-accepted deny matches): flake.nix imports this file
# unconditionally as the `helm` output.
helm.nix
# Media (each pending on its own deny match): the media checks block and
# the two modules core's module list names.
media/checks.nix
media/nixosModules/comfyui-worlds.nix
media/nixosModules/local-model.nix
# Helm Home: the declaration-check fixtures must evaluate (good-core
# included, which passes on the export as well — the synthetic stand-in
# for the missing core that PL21 added — so no exception is named here).
tests/helm-home/declarations/bad-block.nix
tests/helm-home/declarations/bad-field.nix
tests/helm-home/declarations/bad-profile.nix
tests/helm-home/declarations/bad-program.nix
tests/helm-home/declarations/bad-seat.nix
tests/helm-home/declarations/good-core.nix
# Platform's own hosts-layer follow-ons (seat, telemetry): the checks
# tree imports both VM tests.
tests/integration/seat-vm.nix
tests/integration/telemetry-vm.nix
EOF

cd "$work"
python3 pkgs/evidence/publish.py export-list docs/ledger/publish.toml --tree . >export-list.txt

total="$(wc -l <export-list.txt)"
hosts_n="$(grep -c '^hosts/' export-list.txt || true)"
if [ "$hosts_n" -ne 0 ]; then
  echo "export-eval: export-list prints $hosts_n hosts/ paths — the privacy floor broke" >&2
  exit 1
fi
echo "export-eval: export-list prints $total paths, $hosts_n of them hosts/"

mkdir -p "$out"
while IFS= read -r p; do
  mkdir -p "$out/$(dirname "$p")"
  cp "$p" "$out/$p"
done <export-list.txt

# A flake needs its own manifest even while both files sit in `pending`.
cp flake.lock "$out/flake.lock"
cp flake.nix "$out/flake.nix"

missing=0
while IFS= read -r line; do
  case "$line" in
    '' | '#'*) continue ;;
  esac
  if [ ! -f "$line" ]; then
    echo "export-eval: allowlist entry missing from the source: $line" >&2
    missing=1
    continue
  fi
  mkdir -p "$out/$(dirname "$line")"
  cp "$line" "$out/$line"
done <"$allowlist"
if [ "$missing" -ne 0 ]; then
  exit 1
fi

# The clean clone: commit the export so the tree is a repo of its own.
git -C "$out" init -q
git -C "$out" add -A
git -C "$out" commit -qm "export-eval: the publish-gate export"
echo "export-eval: assembled and committed $(git -C "$out" ls-files | wc -l) files at $(git -C "$out" rev-parse --short HEAD)"
