#!/usr/bin/env bash
# Lane L round 1 plan, Task 3: pack a JSON array of review findings into a
# Tier B "chat" job that classifies each one into the defect classes named
# in docs/superpowers/specs/2026-09-03-data-and-models-system-design.md §6
# ("classify findings into defect classes ... for the rollups"). Output is
# checked by a Tier A rule where one exists (§6): here, that a
# classification is one of the five enumerated classes -- enforced by the
# schema's enum, not left to the model.
#
# Usage (on the live host, where lane-submit/jq are in
# environment.systemPackages -- nixosModules/modelLane.nix):
#   findings-classify.sh <lane> <findings.json> [--model M]
#
# <findings.json> is a JSON array; each element's own fields (file, title,
# summary, ...) are passed through verbatim to the model -- this script does
# not assume a specific finding shape beyond "an array of objects".
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: findings-classify.sh <lane> <findings.json> [--model M]" >&2
  exit 1
fi
lane="$1"
findings_file="$2"
shift 2
model="${LANE_MODEL:-deepseek/deepseek-v4-flash}"
if [[ "${1:-}" == "--model" ]]; then
  model="$2"
fi

if [[ ! -f "$findings_file" ]]; then
  echo "findings-classify: no such file: ${findings_file}" >&2
  exit 1
fi

schema_file=$(mktemp)
trap 'rm -f "$schema_file"' EXIT
cat >"$schema_file" <<'EOF'
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "index": { "type": "integer" },
      "class": {
        "type": "string",
        "enum": [
          "PATH-in-unit",
          "merge semantics",
          "hardening gap",
          "test strength",
          "docs"
        ]
      }
    },
    "required": ["index", "class"]
  }
}
EOF

instructions='Classify each finding below into exactly one defect class: "PATH-in-unit" (a systemd unit or script that assumed a PATH entry that is not actually there), "merge semantics" (NixOS option/attrset merge behaved differently than the author assumed -- mkForce, mkMerge, list vs. set), "hardening gap" (a missing or wrong systemd sandboxing/permission setting), "test strength" (a test that does not actually exercise the behavior it claims to, a tautology, or missing coverage), or "docs" (documented behavior that does not match what the code does). Reply with one {index, class} object per finding, index matching its position (0-based) in the input array below.'

jq -n --arg instructions "$instructions" --slurpfile findings "$findings_file" '
  [
    { role: "system", content: $instructions },
    { role: "user", content: ($findings[0] | tojson) }
  ]
' | lane-submit "$lane" --kind chat --class permitted --model "$model" --schema "$schema_file"
