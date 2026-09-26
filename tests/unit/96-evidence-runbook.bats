#!/usr/bin/env bats
# SP5 (docs, S): the evidence runbook's `## Spend` section is the spend
# pipeline's contract -- the five streams and the raw file feeding each, the
# four operator lines (each in its own fenced block, byte for byte) with their
# expected first lines, switch #23's acceptance and rollback, the weekly-limit
# caveat and the manual export kept for monthly reconciliation. Every fenced
# command the section carries must map to a real subcommand: the rows below
# assert the heading, run each mapped --help, prove a bogus verb is caught
# (negative control), name the four words the section must carry, and pin the
# store section's seven writers.

RUNBOOK="$BATS_TEST_DIRNAME/../../docs/runbooks/evidence.md"
EVIDENCE="$BATS_TEST_DIRNAME/../../pkgs/evidence/evidence.py"
LEDGER="$BATS_TEST_DIRNAME/../../tools/ledger/factory.py"

setup() {
  bats_require_minimum_version 1.5.0
}

# The body of a file's `## Spend` section: the lines after the `## Spend`
# heading up to (not including) the next `## ` heading.
spend_section() {
  awk '
    /^## Spend$/ { in_spend = 1; next }
    in_spend && /^## / { exit }
    in_spend { print }
  ' "$1"
}

# The fenced command lines of a file's `## Spend` section: the lines inside a
# ``` fence (fence markers excluded), in order.
spend_fence_lines() {
  spend_section "$1" | awk '
    /^```/ { in_fence = !in_fence; next }
    in_fence { print }
  '
}

# Map one fenced spend line to its --help gate and run it: `evidence <verb>
# <target> ...` becomes `python3 "$EVIDENCE" <verb> <target> --help` and the
# ledger line becomes `python3 "$LEDGER" backfill --help`. Non-zero when the
# mapped --help exits non-zero; lines with neither prefix pass untouched.
gate_spend_line() {
  local line=$1
  case "$line" in
    "evidence "*)
      set -- $line
      run python3 "$EVIDENCE" "$2" "$3" --help
      [ "$status" -eq 0 ]
      ;;
    "nix develop -c python3 tools/ledger/factory.py "*)
      run python3 "$LEDGER" backfill --help
      [ "$status" -eq 0 ]
      ;;
  esac
}

# Gate every fenced spend line of $1; non-zero at the first failure.
gate_spend_file() {
  local line
  while IFS= read -r line; do
    gate_spend_line "$line" || return 1
  done <<<"$(spend_fence_lines "$1")"
}

@test "the runbook has exactly one ## Spend heading" {
  run grep -c '^## Spend' "$RUNBOOK"
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]
}

@test "the four operator lines sit in the spend fences, byte for byte" {
  local line
  for line in \
    'evidence ingest openrouter-usage /var/lib/egress-broker/*/usage.jsonl' \
    'evidence ingest otel /var/lib/opentelemetry-collector/claude-*.jsonl' \
    'nix develop -c python3 tools/ledger/factory.py backfill ~/.claude/projects --ledger-dir /var/lib/evidence/ledger' \
    'evidence report spend --since 2026-09-01 --prices docs/ledger/claude-prices.csv'; do
    spend_fence_lines "$RUNBOOK" | grep -Fqx "$line" || return 1
  done
}

@test "every fenced spend command maps to a subcommand whose --help exits 0" {
  run gate_spend_file "$RUNBOOK"
  [ "$status" -eq 0 ]
}

@test "a bogus spend verb exits non-zero (negative control)" {
  local fake="$BATS_TEST_TMPDIR/bogus.md"
  cat >"$fake" <<'EOF'
## Spend

```
evidence ingest openrouter /bogus
```

## The next section
EOF
  run gate_spend_file "$fake"
  [ "$status" -ne 0 ]
}

@test "the spend section names limit-events, the reset probe, reconciliation and switch-to-configuration" {
  local word
  for word in 'limit-events' 'reset probe' 'reconciliation' 'switch-to-configuration'; do
    spend_section "$RUNBOOK" | grep -Fq "$word" || return 1
  done
}

@test "the store section counts seven writers" {
  run grep -c 'Seven writers' "$RUNBOOK"
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]
}