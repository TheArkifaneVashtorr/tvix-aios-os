#!/usr/bin/env bash
# launch-today.sh -- the 2026-09-04 fix-round launch, kept as the worked example
# of three concurrent seat runs. Dispatches through the versioned scripts beside
# it, never the unversioned bin under ~/factory. Spends the operator's OpenRouter key.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
PLAN=$HOME/nixos-agent-env/docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md
R=$HOME/factory/runs
mkdir -p "$R"
export FACTORY_PLAN=$PLAN FACTORY_TIMEOUT=14400
nohup "$here/factory-wave" a1 "$HOME/nixos-agent-env" "N1" "N2" "N10" "N11 N3 N6" "N5 N8" >"$R/a1.wave.log" 2>&1 &
echo "a1  nixos-agent-env wave 1 (N1 | N2 | N10 | N11>N3>N6 | N5>N8)  pid $!  log $R/a1.wave.log"
nohup "$here/factory-wave" s1 "$HOME/flakes/nixos-skill" "S1" >"$R/s1.wave.log" 2>&1 &
echo "s1  nixos-skill S1                                          pid $!  log $R/s1.wave.log"
FACTORY_BRIEF_EXTRA="$(cat "$R/dsh-harness.notes.md")" nohup "$here/factory-wave" b1 "$HOME/flakes/dsh-harness" "X0 F1 F2 F3 F4 F5" >"$R/b1.wave.log" 2>&1 &
echo "b1  dsh-harness chain X0>F1>F2>F3>F4>F5                     pid $!  log $R/b1.wave.log"
echo "watch: tail -f $R/a1.wave.log   (per-task logs: $R/<KEY>.log, results: $R/<KEY>.result)"
