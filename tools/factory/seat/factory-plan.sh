#!/usr/bin/env bash
# factory-plan <run> <repo-path> <spec> <name>
#
# Runs a headless planning seat for one spec (plan 2026-09-06-planning-agent,
# P8): sizes the spec by word count (one shared rule, factory_plan_size),
# routes the seat's model and effort through the `plan` role (which has no row
# yet, so it resolves to the openrouter default), composes the planning packet
# with factory-plan-brief, then hands that packet to factory-task as an ad-hoc
# task whose single commit lands the draft at
# docs/reviews/plan-drafts/<date>-<name>-<model>.md on branch
# task/PLAN-<name>. The orchestrator judges the draft afterwards; this script
# only runs the drafting seat.
#
# <spec> is resolved relative to FACTORY_TOOLBOX_REPO, exactly as
# factory-plan-brief resolves it, so the two agree whether run from the repo
# root or from a clone. <name> must be one safe path component:
# ^[a-z0-9][a-z0-9-]{0,63}$.
#
# Env:
#   FACTORY_PLAN_BRIEF    the planning-brief script path (tests override it)
#   FACTORY_BIN_OVERRIDE  the directory factory-task lives in (factory-lib.sh's
#                         seam; the tests override it so they never reach the
#                         real driver)
#   FACTORY_TOOLBOX_REPO  the tree whose docs/ledger/routing.toml and
#                         tools/factory/plan/seat-plan.md the run reads, and
#                         the root <spec> is resolved against (exported to the
#                         brief child)
#
# Exit codes: 0 the drafting seat ran (its FACTORY-RESULT is parsed by
# factory-task, which exec's over this process); 2 a refusal (a bad name, a
# missing/unreadable spec, an L spec that must be split before a plan is
# written, or a failing brief -- whatever exit the brief itself takes); 3 a
# routing-table failure (factory_route's own message, already on stderr).
set -euo pipefail

here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=./factory-lib.sh
# shellcheck disable=SC1091
. "$here/factory-lib.sh"

# The lib's FACTORY_TOOLBOX_REPO default is a plain assignment; export it so
# the brief child inherits the SAME tree this script routed and read from
# (from a clone the brief would otherwise re-derive its own root and split).
export FACTORY_TOOLBOX_REPO

usage() {
  cat <<'USAGE' >&2
usage: factory-plan <run> <repo-path> <spec> <name>
USAGE
}

[ $# -eq 4 ] || {
  usage
  exit 2
}
run=$1
repo_path=$2
spec=$3
name=$4

# <name> becomes the branch ref task/PLAN-<name> and a path component in the
# draft's out name, so it must be one safe component: a leading [a-z0-9], then
# [a-z0-9-], at most 64 characters -- never a /, a space or an empty string.
[[ $name =~ ^[a-z0-9][a-z0-9-]{0,63}$ ]] ||
  factory_die 2 "factory-plan: bad name: $name"

# Resolve <spec> against the toolbox tree the way factory-plan-brief does
# (realpath -m of "$tree_root/$spec"), so an absolute path or a traversing
# ../.. is not silently accepted against the CWD while the brief refuses it.
spec_path=$(realpath -m -- "$FACTORY_TOOLBOX_REPO/$spec")
[ -r "$spec_path" ] || factory_die 2 "no such spec: $spec"

# Size the spec with the one shared rule. An L spec is split into sub-project
# plans before any plan is drafted, so no seat runs for it.
size=$(factory_plan_size "$spec_path")
[ "$size" = L ] && factory_die 2 "factory-plan: an L spec is split before a plan is written"

# Route the planning seat through the `plan` role. No `plan` row exists and
# none is written here (a row lands only once a commit cites the measurement
# plan's report, design §6.2), so this resolves to the openrouter default.
# A table failure aborts with factory_route's own message, already on stderr.
route_line=$(factory_route --route openrouter plan docs "$size")
read -r model effort <<<"$route_line"

# The draft's path: the model id with its / turned into -, so the model never
# becomes a subdirectory inside the draft name.
out="docs/reviews/plan-drafts/$(date -u +%F)-$name-${model//\//-}.md"

# Compose the planning packet. factory-plan-brief sizes the spec itself (the
# shared rule), composes the whole packet, and refuses on a broken graph. Any
# brief failure -- its exit 2 refusal, or its exit 3 mid-packet fault -- is
# this script's exit 2, with the brief's own stderr still on ours; exit 3
# stays reserved here for a routing-table failure only.
if ! brief=$("${FACTORY_PLAN_BRIEF:-$here/factory-plan-brief.sh}" "$spec" "$out"); then
  exit 2
fi

# The drafting seat: a factory-task whose brief is seat-plan.md (the seat's own
# constraints, held outside docs/superpowers/plans/ so the graph never sees it)
# plus the packet as ad-hoc task text, with the routed model passed explicitly
# (so the .result records route: explicit) and the routed effort in the env.
FACTORY_PLAN=$FACTORY_TOOLBOX_REPO/tools/factory/plan/seat-plan.md \
  FACTORY_TASK_TEXT=$brief \
  OPENROUTER_REASONING_EFFORT=$effort \
  exec "$FACTORY_BIN/factory-task" "$run" "$repo_path" "PLAN-$name" --model "$model"
