#!/usr/bin/env bats
# IS22: tests/unit/guard-differential.sh — the differential harness that
# answers "do these two guard implementations agree?", verdict for verdict
# and reason for reason, over a corpus built mechanically from three sources
# (the sweep fixture, the payloads extracted from
# 91-orchestrator-guard.bats and 93-house-guard.bats, and a generated
# protected-path matrix). The harness is proven on bash against bash — the
# same guard on both sides must be zero divergences — because a harness that
# cannot show itself green on a known-identical pair is worth nothing. The
# mutants below are the plan's three: M1 (verdicts compared, reasons ignored),
# M2 (scan stopped early, a late divergence missed) and M3 (corpus typed by
# hand instead of extracted, a case added later silently uncovered).
#
# IS22c: the second source also extracts the Write/Edit/MultiEdit payloads
# (builder calls, inline python3 json.dumps payloads, single-quoted JSON
# literals) and counts every site it cannot extract as an exclusion. The
# C-* cases are named after the mutants they kill (M4–M26, the plan's
# IS22c section): C-counts, C-bytes, C-empty, C-gate, C-excl, C-builders,
# C-literal, C-paths, C-synth, C-fault.

GUARD="$BATS_TEST_DIRNAME/../../tools/orchestrator-guard.sh"
HARNESS="$BATS_TEST_DIRNAME/guard-differential.sh"
B91="$BATS_TEST_DIRNAME/91-orchestrator-guard.bats"
B93="$BATS_TEST_DIRNAME/93-house-guard.bats"
SWEEP_TXT="$BATS_TEST_DIRNAME/91-orchestrator-guard-sweep.txt"

# The corpus the harness builds from the three mechanical sources, pinned to
# exact counts so a sweep row, a @test payload added to 91/93, or a generator
# arm changes the number and this file must be consciously updated — the
# added case is never silently uncovered (M3). G11: re-run --corpus-stats and
# paste the numbers here when they move. WRITE/EDIT/MULTIEDIT count corpus
# entries by tool; EXCLUDED counts the extraction sites the harness names
# rather than drops.
SWEEP_ROWS=455
BATS91_PAYLOADS=363
BATS93_PAYLOADS=10
GENERATED=876
WRITE=8
EDIT=23
MULTIEDIT=4
EXCLUDED=8

# make_mutant EXPR OUT — a copy of the guard with the sed expression EXPR
# applied: a deliberately-broken second implementation.
make_mutant() {
  sed "$1" "$GUARD" >"$2"
}

# wrap CMD — the Claude Code Bash payload JSON for CMD (these fixtures carry
# no quotes or backslashes, so the two expansions escape enough).
wrap() {
  local p=$1
  p=${p//\\/\\\\}
  p=${p//\"/\\\"}
  printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$p"
}

# stat_of KEY — the value of one `KEY N` line of --corpus-stats in $output
# (empty when the line is missing, so an arithmetic test on it fails).
stat_of() {
  printf '%s\n' "$output" | awk -v k="$1" '$1 == k { print $2 }'
}

# save_dump — keep the --corpus-dump $output in $DUMP for the grep counts.
save_dump() {
  DUMP="$BATS_TEST_TMPDIR/dump"
  printf '%s\n' "$output" >"$DUMP"
}

# count_x LINE — how many whole lines of $DUMP equal LINE exactly.
count_x() {
  grep -cxF -- "$1" "$DUMP" || true
}

# count_f TEXT — how many lines of $DUMP contain TEXT.
count_f() {
  grep -cF -- "$1" "$DUMP" || true
}

@test "usage: the harness needs two implementations and faults (exit 2) on a missing one" {
  [ -x "$HARNESS" ]
  run bash "$HARNESS"
  [ "$status" -eq 2 ]
  [[ "$output" == *"usage:"* ]]
  run bash "$HARNESS" /nonexistent-impl-a "$GUARD"
  [ "$status" -eq 2 ]
  [[ "$output" == *"/nonexistent-impl-a"* ]]
}

@test "probe: the generated corpus holds at least 600 payloads" {
  run bash "$HARNESS" --corpus-size
  [ "$status" -eq 0 ]
  [ "$output" -ge 600 ]
}

@test "C-counts (M3, M4, M12): every source extracted and counted, tools counted per corpus entry" {
  run bash "$HARNESS" --corpus-stats
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | awk '{ printf "%s ", $1 }')" = "sweep bats-91 bats-93 generated write edit multiedit excluded total " ]
  [ "$(stat_of sweep)" -eq "$SWEEP_ROWS" ]
  [ "$(stat_of bats-91)" -eq "$BATS91_PAYLOADS" ]
  [ "$(stat_of bats-93)" -eq "$BATS93_PAYLOADS" ]
  [ "$(stat_of generated)" -eq "$GENERATED" ]
  [ "$(stat_of write)" -eq "$WRITE" ]
  [ "$(stat_of edit)" -eq "$EDIT" ]
  [ "$(stat_of multiedit)" -eq "$MULTIEDIT" ]
  [ "$(stat_of excluded)" -eq "$EXCLUDED" ]
  [ "$(stat_of total)" -eq $((SWEEP_ROWS + BATS91_PAYLOADS + BATS93_PAYLOADS + GENERATED)) ]
}

@test "C-bytes (M4, M5, M6, M7): the Write/Edit/MultiEdit payloads equal the bats builders' own bytes" {
  run bash "$HARNESS" --corpus-dump
  [ "$status" -eq 0 ]
  save_dump
  eval "$(sed -n '/^wpayload() {/,/^}/p' "$B91")"
  eval "$(sed -n '/^epayload() {/,/^}/p' "$B91")"
  eval "$(sed -n '/^meditpayload() {/,/^}/p' "$B91")"
  declare -F wpayload epayload meditpayload
  [ "$(count_x "$(wpayload ".claude/ritual-override" "allow")")" -eq 1 ]
  [ "$(count_x "$(epayload ".claude/ritual-override" "allow" "deny")")" -eq 1 ]
  [ "$(count_x "$(meditpayload ".claude/ritual-override" "allow" "deny")")" -eq 1 ]
  # 91:470, the escaped-quote adversarial MultiEdit, emitted from its dict text
  [ "$(count_f '"edits":[{"old_string":"say \"hi\"\n### A1 (code, S) — first task","new_string":"say \"hi\""}]}}')" -eq 1 ]
}

@test "C-empty (M8): an empty argument is an argument, never a skipped call" {
  run bash "$HARNESS" --corpus-dump
  [ "$status" -eq 0 ]
  save_dump
  # 91:418, 461, 486, 493, 501, 510, 1648, 1656, 1664, 1672, 1893, 1912 and 93:149
  [ "$(count_f '"new_string":""')" -eq 13 ]
}

@test "C-gate (M9): a builder name followed by bare words (its definition comment) is never a call" {
  run bash "$HARNESS" --corpus-dump
  [ "$status" -eq 0 ]
  save_dump
  [ "$(count_f '"file_path":"FILE"')" -eq 0 ]
}

@test "C-excl (M10, M23, M24): every site the harness cannot extract is one named exclusion line" {
  run bash "$HARNESS" --corpus-dump
  [ "$status" -eq 0 ]
  save_dump
  [ "$(count_x '# excluded 91-orchestrator-guard.bats:1379 unresolved $cmd')" -eq 1 ]
  [ "$(count_x '# excluded 91-orchestrator-guard.bats:1388 unresolved $cmd')" -eq 1 ]
  [ "$(count_x '# excluded 91-orchestrator-guard.bats:1513 unresolved $cmd')" -eq 1 ]
  [ "$(count_x '# excluded 91-orchestrator-guard.bats:1525 unresolved $cmd')" -eq 1 ]
  [ "$(count_x '# excluded 91-orchestrator-guard.bats:1698 runtime-built JSON')" -eq 1 ]
  [ "$(count_x '# excluded 93-house-guard.bats:98 runtime-built JSON')" -eq 1 ]
  [ "$(count_x '# excluded 93-house-guard.bats:99 runtime-built JSON')" -eq 1 ]
  [ "$(count_x '# excluded 93-house-guard.bats:174 unresolved $content')" -eq 1 ]
  [ "$(grep -c '^# excluded ' "$DUMP" || true)" -eq 8 ]
  [ "$(count_f '"command":"$cmd"')" -eq 0 ]
  [ "$(count_f '"content":"$content"')" -eq 0 ]
}

@test "C-builders (M11): builders are discovered by rule over 91 then 93, first definition kept" {
  local expected
  expected=$(awk '
    FNR == 1 { name = "" }
    name == "" && /^[A-Za-z_][A-Za-z0-9_]*\(\)[[:space:]]*\{/ {
      name = $1; sub(/\(\).*/, "", name); body = ""; next
    }
    name != "" && /^\}/ {
      if (body ~ /tool_name/ && !(name in seen)) { seen[name] = 1; print name }
      name = ""; next
    }
    name != "" { body = body $0 "\n" }
  ' "$B91" "$B93")
  [ -n "$expected" ]
  run bash "$HARNESS" --builders
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | awk '{ print $1 }')" = "$expected" ]
  local l
  for l in 'bpayload Bash 1' 'wpayload Write 2' 'epayload Edit 3' 'meditpayload MultiEdit 3' \
    'hg_bash bash 2' 'hg_edit edit 3' 'hg_write write 2'; do
    [ "$(printf '%s\n' "$output" | grep -cxF -- "$l" || true)" -eq 1 ]
  done
}

@test "C-literal (M14, M15): single-quoted JSON literals reach the corpus byte for byte" {
  run bash "$HARNESS" --corpus-dump
  [ "$status" -eq 0 ]
  save_dump
  # 91:534 (three segments joined into one word, $PLAN resolved) and 91:549
  # (malformed, emitted as written)
  [ "$(grep -cxE '\{"tool_name":"Read","tool_input":\{"file_path":"/[^"]*/project/docs/superpowers/plans/test\.md"\}\}' "$DUMP" || true)" -eq 1 ]
  [ "$(count_x '{"tool_name":"Bash", broken')" -eq 1 ]
}

@test "C-paths (M13): names are replaced longest first, so \$PLAN never eats \$PLANS_DIR" {
  run bash "$HARNESS" --corpus-dump
  [ "$status" -eq 0 ]
  save_dump
  [ "$(count_f 'S_DIR')" -eq 0 ]
  [ "$(count_f '/project/docs/superpowers/plans/quoted.md","edits":[')" -eq 1 ]
}

@test "C-synth (M16–M22, M28–M30): scopes, the \${NAME} form, the one-pass argv scan and json_esc on a fixture" {
  local h="$BATS_TEST_TMPDIR/h"
  mkdir -p "$h"
  cp "$HARNESS" "$SWEEP_TXT" "$B93" "$h/"
  # The fixture's @test lines are written as `%test` and rewritten on the way
  # out: bats would otherwise preprocess them as this file's own tests.
  {
    sed -n '/^wpayload() {/,/^}/p' "$B91"
    sed 's/^%test /@test /' <<'EOF'
setup() {
  DIRV="/fixed"
}
%test "one" {
  f="/a/one.md"
  run_guard "$(wpayload "$f" "${DIRV}/x")"
}
%test "two" {
  run_guard "$(wpayload "$f" "two")"
}
%test "three" {
  g="/a/g.md"
  for g in 1 2; do
    run_guard "$(wpayload "$g" "loop")"
  done
}
%test "four" {
  DIRV="/shadow"
  run_guard "$(wpayload "/a/four.md" "$DIRV")"
}
%test "five" {
  p=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1],"description":sys.argv[2]}},ensure_ascii=False,separators=(",",":")))' 'sys.argv[2]' 'sys.argv[1]')
  run_guard "$p"
}
%test "six" {
  run_guard "$(wpayload "/a/six.md" $'a"b\\c\td\ne')"
}
EOF
  } >"$h/91-orchestrator-guard.bats"
  [ "$(sed -n '4p' "$h/91-orchestrator-guard.bats")" = 'setup() {' ]
  [ "$(grep -c '^@test ' "$h/91-orchestrator-guard.bats")" -eq 6 ]
  run bash "$h/guard-differential.sh" --corpus-stats
  [ "$status" -eq 0 ]
  [ "$(stat_of bats-91)" -eq 4 ]
  [ "$(stat_of bats-93)" -eq "$BATS93_PAYLOADS" ]
  run bash "$h/guard-differential.sh" --corpus-dump
  [ "$status" -eq 0 ]
  save_dump
  [ "$(count_x '{"tool_name":"Write","tool_input":{"file_path":"/a/one.md","content":"/fixed/x"}}')" -eq 1 ]
  [ "$(count_x '{"tool_name":"Write","tool_input":{"file_path":"/a/four.md","content":"/shadow"}}')" -eq 1 ]
  [ "$(count_x '{"tool_name":"Bash","tool_input":{"command":"sys.argv[2]","description":"sys.argv[1]"}}')" -eq 1 ]
  [ "$(count_x '{"tool_name":"Write","tool_input":{"file_path":"/a/six.md","content":"a\"b\\c\td\ne"}}')" -eq 1 ]
  [ "$(count_x '# excluded 91-orchestrator-guard.bats:12 unresolved $f')" -eq 1 ]
  [ "$(count_x '# excluded 91-orchestrator-guard.bats:17 unresolved $g')" -eq 1 ]
  # the six line equals the python builder's own bytes
  eval "$(sed -n '/^wpayload() {/,/^}/p' "$B91")"
  [ "$(count_x "$(wpayload "/a/six.md" $'a"b\\c\td\ne')")" -eq 1 ]
  # The panel's r3 errata, on an extended copy (the fixture above stays as
  # the plan pins it): a carriage return (M28: json_esc drops \r), a builder
  # name glued to an identifier is no call (M30: the left name boundary
  # dropped), and 93 redefining 91's wpayload differently leaves 91's
  # definition in the table (M29: last definition kept).
  sed 's/^%test /@test /' >>"$h/91-orchestrator-guard.bats" <<'EOF'
%test "seven" {
  run_guard "$(wpayload "/a/seven.md" $'x\ry')"
  run_guard "$(my_wpayload "/a/eight.md" "glued")"
}
EOF
  {
    cat "$B93"
    printf '\n%s\n' 'wpayload() {'
    printf '%s\n' \
      "  python3 -c 'import json,sys;print(json.dumps({\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":sys.argv[1],\"old_string\":sys.argv[2],\"new_string\":sys.argv[3]}},ensure_ascii=False,separators=(\",\",\":\")))' \"\$1\" \"\$2\" \"\$3\"" \
      '}'
  } >"$h/93.new"
  mv -f "$h/93.new" "$h/93-house-guard.bats"
  run bash "$h/guard-differential.sh" --builders
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | grep -cxF 'wpayload Write 2' || true)" -eq 1 ]
  [ "$(printf '%s\n' "$output" | grep -c '^wpayload ' || true)" -eq 1 ]
  run bash "$h/guard-differential.sh" --corpus-dump
  [ "$status" -eq 0 ]
  save_dump
  [ "$(count_x '{"tool_name":"Write","tool_input":{"file_path":"/a/seven.md","content":"x\ry"}}')" -eq 1 ]
  [ "$(count_x "$(wpayload "/a/seven.md" $'x\ry')")" -eq 1 ]
  [ "$(count_f '/a/eight.md')" -eq 0 ]
}

@test "C-fault (M25, M26): an unreadable bats file or an unsupported builder is exit 2, stdout empty" {
  local f="$BATS_TEST_TMPDIR/f"
  mkdir -p "$f"
  cp "$HARNESS" "$SWEEP_TXT" "$B91" "$f/"
  run bash "$f/guard-differential.sh" --corpus-dump
  [ "$status" -eq 2 ]
  [ "$output" = "guard-differential: bats file not readable: $f/93-house-guard.bats" ]
  run bash "$f/guard-differential.sh" --builders
  [ "$status" -eq 2 ]
  [ "$output" = "guard-differential: bats file not readable: $f/93-house-guard.bats" ]
  cp "$B93" "$f/"
  rm -f "$f/91-orchestrator-guard.bats"
  # 91 may end without a newline: start the appended builder on a line of its own
  {
    cat "$B91"
    printf '\n%s\n' 'rpayload() {'
    printf '%s\n' \
      "  python3 -c 'import json,sys;print(json.dumps({\"tool_name\":\"Read\",\"tool_input\":{\"file_path\":sys.argv[1]}},ensure_ascii=False,separators=(\",\",\":\")))' \"\$1\"" \
      '}'
  } >"$f/91-orchestrator-guard.bats"
  run bash "$f/guard-differential.sh" --builders
  [ "$status" -eq 2 ]
  [ "$output" = "guard-differential: builder rpayload has unsupported tool Read" ]
  run bash "$f/guard-differential.sh" --corpus-dump
  [ "$status" -eq 2 ]
  [ "$output" = "guard-differential: builder rpayload has unsupported tool Read" ]
  # a Write builder that takes one argument cannot feed the two-field emitter
  # (the panel's r3 erratum: M27, the arity check dropped)
  rm -f "$f/91-orchestrator-guard.bats"
  {
    cat "$B91"
    printf '\n%s\n' 'xpayload() {'
    printf '%s\n' \
      "  python3 -c 'import json,sys;print(json.dumps({\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":sys.argv[1],\"content\":\"\"}},ensure_ascii=False,separators=(\",\",\":\")))' \"\$1\"" \
      '}'
  } >"$f/91-orchestrator-guard.bats"
  run bash "$f/guard-differential.sh" --builders
  [ "$status" -eq 2 ]
  [ "$output" = "guard-differential: builder xpayload takes 1 arguments, Write needs 2" ]
}

@test "green: bash against bash over the full corpus — zero divergences, exit 0" {
  run bash "$HARNESS" "$GUARD" "$GUARD"
  [ "$status" -eq 0 ]
  [[ "$output" == *" divergences"* ]]
  [[ "$output" != *"DIVERGENCE"* ]]
  local last re
  last=$(printf '%s\n' "$output" | tail -1)
  re='^corpus ([0-9]+) payloads, ([0-9]+) divergences$'
  [[ "$last" =~ $re ]]
  [ "${BASH_REMATCH[1]}" -ge 600 ]
  [ "${BASH_REMATCH[2]}" -eq 0 ]
}

@test "red: a guard with one PROTECTED_PATHS entry removed diverges, and the harness reports payload, verdicts and reasons" {
  local mutant="$BATS_TEST_TMPDIR/mutant-entry-removed.sh"
  make_mutant "/^  '\.claude\/ritual-override|file'$/d" "$mutant"
  run bash "$HARNESS" "$GUARD" "$mutant"
  [ "$status" -ne 0 ]
  [[ "$output" == *"DIVERGENCE"* ]]
  # the sweep's `rm -rf .claude` names the override's parent directory: impl-a
  # denies with the override reason, the mutant (entry removed) allows
  [[ "$output" == *"$(wrap 'rm -rf .claude')"* ]]
  [[ "$output" == *"impl-a: verdict=deny reason=the ritual override is the operator's; ask for it"* ]]
  [[ "$output" == *"impl-b: verdict=allow reason="* ]]
  local last re
  last=$(printf '%s\n' "$output" | tail -1)
  re='^corpus ([0-9]+) payloads, ([0-9]+) divergences$'
  [[ "$last" =~ $re ]]
  [ "${BASH_REMATCH[1]}" -ge 600 ]
  [ "${BASH_REMATCH[2]}" -ge 100 ]
}

@test "M1: a reason-only divergence (verdicts agree) is still a divergence" {
  local mutant="$BATS_TEST_TMPDIR/mutant-reason-reworded.sh"
  make_mutant 's/^OVERRIDE_REASON=.*/OVERRIDE_REASON="mutant reason text"/' "$mutant"
  local corpus="$BATS_TEST_TMPDIR/corpus-m1"
  {
    wrap 'echo ok'
    wrap 'rm -rf .claude/ritual-override'
  } >"$corpus"
  run bash "$HARNESS" "$GUARD" "$mutant" "$corpus"
  [ "$status" -ne 0 ]
  # both sides deny — only the reason text differs, and that still diverges
  [[ "$output" == *"impl-a: verdict=deny reason=the ritual override is the operator's; ask for it"* ]]
  [[ "$output" == *"impl-b: verdict=deny reason=mutant reason text"* ]]
  [ "$(printf '%s\n' "$output" | grep -c '^DIVERGENCE')" -eq 1 ]
}

@test "M2: a divergence late in an explicit corpus file is still reported (no early stop)" {
  local wrapper="$BATS_TEST_TMPDIR/mutwrap.sh"
  {
    printf '#!/usr/bin/env bash\n'
    printf 'source "%s"\n' "$GUARD"
    printf "PROTECTED_PATHS+=('elsewhere/secret.txt|file')\n"
    printf 'main\n'
  } >"$wrapper"
  local corpus="$BATS_TEST_TMPDIR/corpus-m2"
  {
    wrap 'echo ok'
    wrap 'cat /tmp/notes'
    wrap 'ls -la'
    wrap 'printf x > elsewhere/secret.txt' # the divergence, sorted last
  } >"$corpus"
  run bash "$HARNESS" "$GUARD" "$wrapper" "$corpus"
  [ "$status" -ne 0 ]
  [ "$(printf '%s\n' "$output" | grep -c '^DIVERGENCE')" -eq 1 ]
  [[ "$output" == *"$(wrap 'printf x > elsewhere/secret.txt')"* ]]
  [[ "$output" == *"impl-a: verdict=allow"* ]]
  [[ "$output" == *"impl-b: verdict=deny"* ]]
}

@test "an implementation printing garbage is a harness fault (exit 2), never a silent allow" {
  local stub="$BATS_TEST_TMPDIR/stub-garbage.sh"
  printf '#!/usr/bin/env bash\nprintf garbage\n' >"$stub"
  local corpus="$BATS_TEST_TMPDIR/corpus-garbage"
  wrap 'echo ok' >"$corpus"
  run bash "$HARNESS" "$stub" "$GUARD" "$corpus"
  [ "$status" -eq 2 ]
  [[ "$output" == *"permissionDecision"* ]]
}
