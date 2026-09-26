#!/usr/bin/env bash
# Lane L round 1 plan, Task 3: pack docs/runbooks, docs/superpowers/specs,
# nixosModules and hosts into one Tier B "chat" job (data-and-models spec
# §6, "large-context whole-repo coherence reviews") asking the lane's model
# to find contradictions between documented and implemented behaviour -- the
# class of defect the pre-switch audit (docs/board, 2026-09-03) found by
# hand. This is the one job template that leans on the lane's large context
# window rather than a small prompt.
#
# Usage (on the live host, where lane-submit/jq are in
# environment.systemPackages -- nixosModules/modelLane.nix):
#   repo-coherence.sh <lane> [repo-root] [--model M]
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: repo-coherence.sh <lane> [repo-root] [--model M]" >&2
  exit 1
fi
lane="$1"
shift
repo_root="."
if [[ $# -gt 0 && "$1" != "--model" ]]; then
  repo_root="$1"
  shift
fi
model="${LANE_MODEL:-deepseek/deepseek-v4-flash}"
if [[ "${1:-}" == "--model" ]]; then
  model="$2"
fi
repo_root="${repo_root%/}"

blob=$(mktemp)
schema_file=$(mktemp)
trap 'rm -f "$blob" "$schema_file"' EXIT

scan_dirs=(
  "$repo_root/docs/runbooks"
  "$repo_root/docs/superpowers/specs"
  "$repo_root/nixosModules"
  "$repo_root/hosts"
)
existing_dirs=()
for d in "${scan_dirs[@]}"; do
  [[ -d "$d" ]] && existing_dirs+=("$d")
done
if [[ ${#existing_dirs[@]} -eq 0 ]]; then
  echo "repo-coherence: none of the expected directories exist under ${repo_root}" >&2
  exit 1
fi

while IFS= read -r -d '' f; do
  {
    echo "===== FILE: ${f#"$repo_root"/} ====="
    cat "$f"
    echo
  } >>"$blob"
done < <(find "${existing_dirs[@]}" -type f \( -name '*.md' -o -name '*.nix' \) -print0 | sort -z)

cat >"$schema_file" <<'EOF'
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "doc": { "type": "string" },
      "code": { "type": "string" },
      "claim": { "type": "string" },
      "contradiction": { "type": "string" },
      "severity": { "type": "string", "enum": ["blocker", "major", "minor"] }
    },
    "required": ["doc", "code", "claim", "contradiction", "severity"]
  }
}
EOF

instructions='Below are this repository'"'"'s runbooks, specs, NixOS modules and host configuration, each preceded by a "===== FILE: <path> =====" marker. Find contradictions where a doc (runbook or spec) claims a behaviour that the module/host code does not actually implement, or implements differently. For each contradiction, cite the exact doc path and code path (from the FILE markers), quote the claim, state the contradiction, and rate its severity. Report nothing you cannot point to a specific file for.'

jq -n --arg instructions "$instructions" --rawfile blob "$blob" '
  [
    { role: "system", content: $instructions },
    { role: "user", content: $blob }
  ]
' | lane-submit "$lane" --kind chat --class permitted --model "$model" --max-tokens 8000 --schema "$schema_file"
