#!/usr/bin/env bash
# helm-switch — activate a Helm profile via `switch-to-configuration test`.
#
# Template file: nixosModules/helm.nix substitutes @PROFILES@ (the fixed
# literal allowlist — decision D1: never derived from config.specialisation,
# so every toplevel bakes the same script) and @MARKER@ (the /etc/helm/profile
# marker path). The unit runs this as root with an empty environment, so the
# only input that can steer it is the one validated argument.
#
# Invariants enforced here, before anything runs:
#   - a name outside ^[a-z][a-z0-9-]{0,31}$ or not in @PROFILES@ runs NOTHING
#     (exit 2; no audit pair — nothing happened);
#   - the only action ever executed is `switch-to-configuration test` — never
#     switch or boot: the boot default must not change;
#   - a mapped activation binary that is missing fails closed: nothing is
#     executed, the audit pair still closes (the journal state machine reads
#     begin/end pairs — a dangling begin would read as "switching" forever).
set -euo pipefail

readonly PROFILES="@PROFILES@"
readonly MARKER="@MARKER@"
readonly SYSTEM_PROFILE_ROOT=/nix/var/nix/profiles/system
readonly BOOTED_ROOT=/run/booted-system

err() {
  echo "helm-switch: $*" >&2
}

profile=${1:-}

# Gate 1 — shape. systemd escapes %i, but the unit is root: the cost of
# paranoia is one line, and `gaming;reboot` must die here.
if [[ ! $profile =~ ^[a-z][a-z0-9-]{0,31}$ ]]; then
  err "invalid profile name"
  exit 2
fi

# Gate 2 — allowlist. Space-separated literal baked in by the module (D1).
if [[ " $PROFILES " != *" $profile "* ]]; then
  err "profile not in allowlist: $profile"
  exit 2
fi

# Root selection (D4): the system profile root when it carries the
# activation binary, else /run/booted-system — a stage-2 boot has no profile
# generation yet (the VM path), and this is what makes "back to base"
# correct from inside any specialisation. HELM_SWITCH_ROOT_OVERRIDE is a
# test seam: the unit passes an empty environment, so only a root shell
# could ever set it, and the bats suite uses it to point at a stub root
# instead of the live machine's real activation binaries.
if [[ -n ${HELM_SWITCH_ROOT_OVERRIDE:-} ]]; then
  ROOT=$HELM_SWITCH_ROOT_OVERRIDE
elif [[ -x $SYSTEM_PROFILE_ROOT/bin/switch-to-configuration ]]; then
  ROOT=$SYSTEM_PROFILE_ROOT
else
  ROOT=$BOOTED_ROOT
fi

from=$(cat "$MARKER" 2>/dev/null || echo unknown)
echo "helm-switch: begin $from -> $profile root=$ROOT"

if [[ $profile == base ]]; then
  bin=$ROOT/bin/switch-to-configuration
else
  bin=$ROOT/specialisation/$profile/bin/switch-to-configuration
fi

code=0
if [[ -x $bin ]]; then
  "$bin" test || code=$?
else
  err "missing activation binary: $bin (nothing was executed)"
  code=127
fi
echo "helm-switch: end $profile exit=$code"
exit "$code"
