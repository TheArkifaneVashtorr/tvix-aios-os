#!/usr/bin/env bash
# A writer that still hard-codes the store root instead of honouring the env.
set -euo pipefail
store="${EVIDENCE_STORE:-/var/lib/evidence}"
printf '%s\n' "$store"
