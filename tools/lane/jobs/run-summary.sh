#!/usr/bin/env bash
# Lane L round 1 plan, Task 3: pack a dark-factory workflow transcript dir's
# journal into a Tier B "chat" job (data-and-models spec §6) asking the
# lane's model for a terse run summary a board line can quote.
#
# Usage (on the live host, where lane-submit/jq are in
# environment.systemPackages -- nixosModules/modelLane.nix):
#   run-summary.sh <lane> <workflow-transcript-dir> [--model M]
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: run-summary.sh <lane> <workflow-transcript-dir> [--model M]" >&2
  exit 1
fi
lane="$1"
dir="$2"
shift 2
model="${LANE_MODEL:-deepseek/deepseek-v4-flash}"
if [[ "${1:-}" == "--model" ]]; then
  model="$2"
fi

journal="${dir%/}/journal.jsonl"
if [[ ! -f "$journal" ]]; then
  echo "run-summary: no journal.jsonl under ${dir}" >&2
  exit 1
fi

schema_file=$(mktemp)
trap 'rm -f "$schema_file"' EXIT
cat >"$schema_file" <<'EOF'
{
  "type": "object",
  "properties": {
    "summary": { "type": "string" },
    "tasks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "key": { "type": "string" },
          "status": { "type": "string" }
        },
        "required": ["key", "status"]
      }
    },
    "risks": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["summary", "tasks", "risks"]
}
EOF

instructions='You summarize a dark-factory workflow run for a terse operator board line. Cite only run ids, task keys and statuses that literally appear in the journal below -- never invent a task, commit, or outcome. Each journal line is one JSONL event.'

jq -n --arg instructions "$instructions" --rawfile journal "$journal" '
  [
    { role: "system", content: $instructions },
    { role: "user", content: $journal }
  ]
' | lane-submit "$lane" --kind chat --class permitted --model "$model" --schema "$schema_file"
