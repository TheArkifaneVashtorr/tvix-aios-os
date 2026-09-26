#!/usr/bin/env bats
# The seat driver (tools/factory/seat/, plan N17) is the operator's manual
# per-task tool: a versioned copy of the unversioned ~/factory/bin/ scripts
# that turn a plan's task sections into headless dsh-openrouter runs. It is
# gated on shellcheck+ruff by checks.lint and exercised here by its few
# deterministic behaviours -- factory-brief is pure text composition (no
# network) and factory-ws's first gate is the "is this a git repository"
# refusal, both safe to run in the build sandbox.
#
# Every script is invoked through bash directly, the way checks.unit's
# sandbox runs them (no /usr/bin/env there), and FACTORY_ROOT is overridden
# to the test tmpdir so nothing here ever touches the operator's real
# ~/factory or the network.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup_file() {
  bats_require_minimum_version 1.5.0
  # No test in this file may write to the operator's real runs dir
  # ($HOME/factory/runs). Snapshot it once, before any test runs, so
  # teardown_file can prove none gained an entry.
  if [ -d "$HOME/factory/runs" ]; then
    LC_ALL=C ls -A1 "$HOME/factory/runs" 2>/dev/null |
      LC_ALL=C sort >"$BATS_FILE_TMPDIR/runs.before"
  else
    : >"$BATS_FILE_TMPDIR/runs.before"
  fi
}

teardown_file() {
  if [ -d "$HOME/factory/runs" ]; then
    LC_ALL=C ls -A1 "$HOME/factory/runs" 2>/dev/null |
      LC_ALL=C sort >"$BATS_FILE_TMPDIR/runs.after"
  else
    : >"$BATS_FILE_TMPDIR/runs.after"
  fi
  if ! diff -u "$BATS_FILE_TMPDIR/runs.before" "$BATS_FILE_TMPDIR/runs.after" >&2; then
    printf 'a test wrote to the real ~/factory/runs\n' >&2
    return 1
  fi
}

setup() {
  REAL_BASH="$(command -v bash)"
  PLAN="$BATS_TEST_TMPDIR/plan.md"
  # P11 (A5): factory-task and factory-wave now refuse to run without a named
  # plan, so give every test a readable (initially empty) plan file and export
  # it as FACTORY_PLAN; tests that need it genuinely unset use `env -u`.
  : >"$PLAN"
  export FACTORY_PLAN="$PLAN"
  # Every test runs against an isolated factory root under the tmpdir, never
  # the operator's ~/factory (factory-lib.sh derives FACTORY_RUNS from
  # FACTORY_ROOT). A test may still override FACTORY_ROOT for a nested layout;
  # these exports are the fail-closed default so no test can leak by omission.
  export FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"
  export FACTORY_RUNS="$BATS_TEST_TMPDIR/factory/runs"
}

@test "factory-brief renders the task section, WORKSPACE RULES and REPO NOTES deterministically" {
  cat >"$PLAN" <<'EOF'
## Global Constraints

- Constraint one.

## Assumptions

1. Assumption one.

### N17 (code, M) — the seat driver joins the repo

The seat driver spec body.

EOF
  FACTORY_RUN=run7 \
    FACTORY_MODEL=deepseek/deepseek-v4-pro-0813 \
    FACTORY_BRIEF_EXTRA="repo notes text" \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" N17
  [ "$status" -eq 0 ]
  # The plan's Global Constraints and Assumptions sections are rendered.
  [[ "$output" == *"## Global Constraints"* ]]
  [[ "$output" == *"- Constraint one."* ]]
  [[ "$output" == *"## Assumptions"* ]]
  [[ "$output" == *"1. Assumption one."* ]]
  # The task's own section heading and body are rendered.
  [[ "$output" == *"### N17 (code, M) — the seat driver joins the repo"* ]]
  [[ "$output" == *"The seat driver spec body."* ]]
  # The fixed WORKSPACE RULES block is appended.
  [[ "$output" == *"## WORKSPACE RULES"* ]]
  # FACTORY_BRIEF_EXTRA surfaces as the REPO NOTES section.
  [[ "$output" == *"## REPO NOTES (these override the WORKSPACE RULES above where they conflict)"* ]]
  [[ "$output" == *"repo notes text"* ]]
  # The commit-trailer lines in WORKSPACE RULES are filled with the supplied
  # run/model, no literal placeholder is left behind, and BOTH trailers are
  # requested in this order: Generated-By, then Co-Authored-By.
  [[ "$output" == *"Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run run7)"* ]]
  [[ "$output" == *"Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"* ]]
  [[ "$output" == *"Generated-By: dsh 0.1.2-rc.1"*"Co-Authored-By: Claude Fable 5.1"* ]]
  [[ "$output" != *"<RUN>"* ]]
  [[ "$output" != *"<model>"* ]]
}

@test "factory-ws refuses a path that is not a git repository" {
  notrepo="$BATS_TEST_TMPDIR/notrepo"
  mkdir -p "$notrepo"
  FACTORY_ROOT="$BATS_TEST_TMPDIR/factory" \
    run "$REAL_BASH" "$SEAT/factory-ws" run7 "$notrepo" N17
  [ "$status" -eq 2 ]
  [[ "$output" == *"is not a git repository"* ]]
  # The refusal fires before any clone, so no base workspace tree is created.
  [ ! -e "$BATS_TEST_TMPDIR/factory" ]
}

@test "factory-ws clones a real git repo into a base and creates the workspace on task/<KEY>, printing its path" {
  # This is the case the refuse-only test cannot cover: the "is this a git
  # repository" gate must admit a real repository (not just reject a non-repo,
  # which an always-refusing gate would too). Mutate that gate to `false` and
  # this case goes red while the refusal case above stays green.
  repo="$BATS_TEST_TMPDIR/srcrepo"
  mkdir -p "$repo"
  git -C "$repo" init --quiet
  printf 'hello\n' >"$repo/README"
  git -C "$repo" add README
  git -C "$repo" -c user.name="Seat Test" -c user.email="seat@example.com" \
    commit --quiet -m "initial"
  FACTORY_ROOT="$BATS_TEST_TMPDIR/factory" \
    run "$REAL_BASH" "$SEAT/factory-ws" run7 "$repo" N17
  [ "$status" -eq 0 ]
  # The base clone of the real repo exists, and the workspace is a git
  # repository checked out on the task/<KEY> branch.
  [ -d "$BATS_TEST_TMPDIR/factory/base/srcrepo" ]
  [ "$(git -C "$BATS_TEST_TMPDIR/factory/ws/run7/N17" rev-parse --abbrev-ref HEAD)" = "task/N17" ]
  # The workspace path is the script's stdout, i.e. the last line of the
  # merged stream after all its stderr logs.
  [[ "${lines[-1]}" == "$BATS_TEST_TMPDIR/factory/ws/run7/N17" ]]
}

@test "factory-integrate records one check observation per check it runs, at the integration head" {
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  git -C "$src" commit -q --allow-empty -m "init"
  git clone -q "$src" "$root/base/src"
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  echo x >"$root/ws/r1/K1/x"; git -C "$root/ws/r1/K1" add x
  git -C "$root/ws/r1/K1" commit -q -m "k1: add x (test: unit, lint)"
  rec="$BATS_TEST_TMPDIR/rec.sh"; log="$BATS_TEST_TMPDIR/rec.log"
  printf '#!%s\nprintf "%%s\\n" "$*" >>%q\n' "$REAL_BASH" "$log" >"$rec"
  chmod +x "$rec"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true FACTORY_EVIDENCE_CMD="$rec" EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev" \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 0 ]
  head=$(git -C "$root/base/src" rev-parse integ/r1)
  run cat "$log"
  [[ "$output" =~ ^--store\ $BATS_TEST_TMPDIR/ev\ record-check\ --name\ custom\ --rev\ $head\ --ok\ --class\ nix-check\ --src\ seat-integrate\ --duration\ [0-9]+$ ]]
}

@test "factory-integrate records a failed check as --fail and exits 1" {
  # The passing custom-branch case above only drives an `ok` verdict. This
  # case runs the same fixture with FACTORY_CHECK_CMD=false so the check
  # fails: the integrator must still record the observation (marked --fail,
  # not --ok) and exit 1 so the check verdict stands. A wrong verdict here
  # would write a false green into the evidence store.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  git -C "$src" commit -q --allow-empty -m "init"
  git clone -q "$src" "$root/base/src"
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  echo x >"$root/ws/r1/K1/x"; git -C "$root/ws/r1/K1" add x
  git -C "$root/ws/r1/K1" commit -q -m "k1: add x (test: unit, lint)"
  rec="$BATS_TEST_TMPDIR/rec.sh"; log="$BATS_TEST_TMPDIR/rec.log"
  printf '#!%s\nprintf "%%s\\n" "$*" >>%q\n' "$REAL_BASH" "$log" >"$rec"
  chmod +x "$rec"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=false FACTORY_EVIDENCE_CMD="$rec" EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev" \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 1 ]
  head=$(git -C "$root/base/src" rev-parse integ/r1)
  run cat "$log"
  [ "${#lines[@]}" -eq 1 ]
  [[ "$output" =~ ^--store\ $BATS_TEST_TMPDIR/ev\ record-check\ --name\ custom\ --rev\ $head\ --fail\ --class\ nix-check\ --src\ seat-integrate\ --duration\ [0-9]+$ ]]
}

@test "factory-integrate records one observation per check in the nix-build loop, at the integration head" {
  # The FACTORY_CHECK_CMD case above only drives the "custom" branch. This
  # case exercises the real check loop (the branch that runs for this repo):
  # nix is shadowed on PATH so the loop still runs once per collected check
  # ("lint", "unit") but performs no actual build, and each iteration must
  # still record one observation naming the integration head.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  git -C "$src" commit -q --allow-empty -m "init"
  git clone -q "$src" "$root/base/src"
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  echo x >"$root/ws/r1/K1/x"; git -C "$root/ws/r1/K1" add x
  git -C "$root/ws/r1/K1" commit -q -m "k1: add x (test: unit, lint)"
  rec="$BATS_TEST_TMPDIR/rec.sh"; log="$BATS_TEST_TMPDIR/rec.log"
  printf '#!%s\nprintf "%%s\\n" "$*" >>%q\n' "$REAL_BASH" "$log" >"$rec"
  chmod +x "$rec"
  mkdir -p "$BATS_TEST_TMPDIR/bin"
  printf '#!%s\nexit 0\n' "$REAL_BASH" >"$BATS_TEST_TMPDIR/bin/nix"
  chmod +x "$BATS_TEST_TMPDIR/bin/nix"
  PATH="$BATS_TEST_TMPDIR/bin:$PATH" FACTORY_ROOT="$root" FACTORY_EVIDENCE_CMD="$rec" EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev" \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 0 ]
  head=$(git -C "$root/base/src" rev-parse integ/r1)
  run sort "$log"
  [ "${#lines[@]}" -eq 2 ]
  [[ "${lines[0]}" =~ ^--store\ $BATS_TEST_TMPDIR/ev\ record-check\ --name\ lint\ --rev\ $head\ --ok\ --class\ nix-check\ --src\ seat-integrate\ --duration\ [0-9]+$ ]]
  [[ "${lines[1]}" =~ ^--store\ $BATS_TEST_TMPDIR/ev\ record-check\ --name\ unit\ --rev\ $head\ --ok\ --class\ nix-check\ --src\ seat-integrate\ --duration\ [0-9]+$ ]]
}

@test "factory-integrate still exits 0 when the recorder fails, keeping the check verdict" {
  # factory_record_check's contract is "never fails the caller": a recording
  # problem is logged and the check verdict stands. A recorder that exits
  # non-zero must not change the integrator's exit status; only a stderr note
  # is emitted.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  git -C "$src" commit -q --allow-empty -m "init"
  git clone -q "$src" "$root/base/src"
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  echo x >"$root/ws/r1/K1/x"; git -C "$root/ws/r1/K1" add x
  git -C "$root/ws/r1/K1" commit -q -m "k1: add x (test: unit, lint)"
  rec="$BATS_TEST_TMPDIR/rec.sh"
  printf '#!%s\nexit 7\n' "$REAL_BASH" >"$rec"
  chmod +x "$rec"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true FACTORY_EVIDENCE_CMD="$rec" EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev" \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 0 ]
  [[ "$output" == *"evidence: could not record custom@"* ]]
}

@test "factory_seed_dsh_home copies settings.yaml without the saved model selection and symlinks the rest" {
  src="$BATS_TEST_TMPDIR/shared"
  mkdir -p "$src/sessions"
  printf 'ui-onboarding:\n  welcomeNoticeVersion: 2026-08-13.1\nagent-default-model:\n  provider: openrouter\n  model: deepseek/deepseek-v4-pro-0813\n  reasoningEffort: medium\nother-key: 1\n' >"$src/settings.yaml"
  printf 'x' >"$src/some-other-file"
  printf 'route' >"$src/openrouter-route.yml"
  dst="$BATS_TEST_TMPDIR/task-home"
  FACTORY_SHARED_DSH_HOME_SRC="$src" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_seed_dsh_home '$dst'"
  [ "$status" -eq 0 ]
  [ -f "$dst/settings.yaml" ]
  [ ! -L "$dst/settings.yaml" ]
  run grep -c 'agent-default-model\|deepseek-v4-pro\|reasoningEffort\|provider: openrouter' "$dst/settings.yaml"
  [ "$output" = "0" ]
  run grep -c 'welcomeNoticeVersion: 2026-08-13.1' "$dst/settings.yaml"
  [ "$output" = "1" ]
  run grep -c '^other-key: 1$' "$dst/settings.yaml"
  [ "$output" = "1" ]
  [ -L "$dst/some-other-file" ]
  [ ! -e "$dst/sessions" ]
  [ ! -e "$dst/openrouter-route.yml" ]
  run stat -c %a "$dst/settings.yaml"
  [ "$output" = "600" ]
}

@test "factory_seed_dsh_home with no settings.yaml in the source creates none" {
  src="$BATS_TEST_TMPDIR/shared2"
  mkdir -p "$src"
  printf 'x' >"$src/some-other-file"
  dst="$BATS_TEST_TMPDIR/task-home2"
  FACTORY_SHARED_DSH_HOME_SRC="$src" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_seed_dsh_home '$dst'"
  [ "$status" -eq 0 ]
  [ ! -e "$dst/settings.yaml" ]
  [ -L "$dst/some-other-file" ]
}

@test "factory-task dispatches to the seat directory it was run from, not to FACTORY_ROOT/bin" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"
  # The build sandbox copies the source tree read-only; make the copy writable
  # so the stub below can overwrite factory-ws in place.
  chmod -R u+w "$seat_copy"
  # The marker is written to stderr: factory-task captures factory-ws's
  # stdout into $ws, so only a stderr line is observable in the merged output.
  printf '#!%s\necho DISPATCHED-TO-COPY >&2; exit 7\n' "$REAL_BASH" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws" "$root/runs"   # no bin/
  repo="$BATS_TEST_TMPDIR/repo"; git init -q "$repo"
  FACTORY_ROOT="$root" run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 7 ]
  [[ "$output" == *DISPATCHED-TO-COPY* ]]
}

@test "factory_route picks the most specific matching row, first row on ties" {
  toml="$BATS_TEST_TMPDIR/routing.toml"
  cat >"$toml" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/a"
effort = "low"

[[route]]
role = "implement"
kind = "any"
size = "any"
model = "m/b"
effort = "off"

[[route]]
role = "implement"
kind = "docs"
size = "any"
model = "m/c"
effort = "high"

[[route]]
role = "implement"
kind = "any"
size = "XS"
model = "m/d"
effort = "xhigh"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement docs XS '$toml'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/c high" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement code S '$toml'"
  [ "$output" = "m/b off" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route review code S '$toml'"
  [ "$output" = "m/a low" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement docs S '$toml'"
  [ "$output" = "m/c high" ]
}

@test "factory_route rejects a malformed or missing table" {
  # No default (any/any/any) row.
  nodefault="$BATS_TEST_TMPDIR/no-default.toml"
  cat >"$nodefault" <<'EOF'
[[route]]
role = "implement"
kind = "docs"
size = "any"
model = "m/x"
effort = "off"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route any any any '$nodefault'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"no default"* ]]

  # A row missing the effort key.
  missing="$BATS_TEST_TMPDIR/missing-effort.toml"
  cat >"$missing" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/x"

[[route]]
role = "implement"
kind = "any"
size = "any"
model = "m/y"
effort = "off"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route any any any '$missing'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"row 1"* ]]
  [[ "$output" == *"effort"* ]]

  # An effort value outside the five levels.
  badeffort="$BATS_TEST_TMPDIR/bad-effort.toml"
  cat >"$badeffort" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/x"
effort = "max"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route any any any '$badeffort'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"effort"* ]]

  # Missing file.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route any any any '$BATS_TEST_TMPDIR/nope.toml'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"no routing table"* ]]

  # An unknown role word is rejected (the enumeration is what RT2 must extend;
  # a botched extension would silently accept a typo'd role).
  badrole="$BATS_TEST_TMPDIR/bad-role.toml"
  cat >"$badrole" <<'EOF'
[[route]]
role = "builder"
kind = "any"
size = "any"
model = "m/x"
effort = "off"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/y"
effort = "off"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route builder any any '$badrole'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"unknown role"* ]]

  # An empty value (here: model = "") is rejected; the empty string matches no
  # char of [A-Za-z0-9._:/-]+, so it must not sail through as "valid".
  emptymodel="$BATS_TEST_TMPDIR/empty-model.toml"
  cat >"$emptymodel" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = ""
effort = "off"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route any any any '$emptymodel'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"bad value"* ]]
}

@test "factory_route_check validates the committed routing table" {
  # The unit-check sandbox now copies docs/ledger/routing.toml (flake.nix), so
  # this validates the committed table both in the sandbox and locally. The
  # skip below is a defensive guard against a flake-copy regression, not the
  # path a healthy build takes.
  real="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
  [ -f "$real" ] || skip "docs/ledger/routing.toml not copied into the unit-check sandbox"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$real'"
  [ "$status" -eq 0 ]
}

@test "factory_task_kind_size parses (kind, size) from the heading, any any otherwise" {
  plan="$BATS_TEST_TMPDIR/ksplan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body.

### K2: thing

body2.
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_kind_size '$plan' K1"
  [ "$output" = "docs XS" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_kind_size '$plan' K2"
  [ "$output" = "any any" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_kind_size '$plan' MISSING"
  [ "$output" = "any any" ]
}

@test "factory-task resolves model and effort through routing.toml and records the route" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  # The copied scripts keep their `#!/usr/bin/env bash` shebang, which the
  # build sandbox has no /usr/bin/env to honour; factory-task invokes
  # factory-brief by that shebang, so repoint it to the sandbox bash.
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  # factory-ws prints a workspace path and succeeds, so factory-task runs to
  # completion and writes the .result file.
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  # factory-task reads the routing table at $FACTORY_TOOLBOX_REPO/docs/ledger/
  # routing.toml. The unit-check sandbox does not copy the checkout's docs/,
  # so use a fixture that mirrors the committed table's rows (the committed
  # table itself is pinned shape-wise by the factory_route_check test above).
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
role = "implement"
kind = "any"
size = "XS"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
role = "implement"
kind = "code"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
role = "review"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  # Plan with a (docs, XS) and a (code, M) heading.
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body one.

### K2 (code, M) — t

body two.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  # A fake dsh-openrouter records the --model argument and
  # OPENROUTER_REASONING_EFFORT, then prints a valid FACTORY-RESULT block.
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'model=%s\\n' "\$2" >> "\$REC"
printf 'effort=%s\\n' "\${OPENROUTER_REASONING_EFFORT:-}" >> "\$REC"
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  rec1="$BATS_TEST_TMPDIR/rec1"; rec2="$BATS_TEST_TMPDIR/rec2"; rec3="$BATS_TEST_TMPDIR/rec3"; rec4="$BATS_TEST_TMPDIR/rec4"; rec5="$BATS_TEST_TMPDIR/rec5"

  # (docs, XS), no overrides -> Flash at off, route implement/docs/XS.
  REC="$rec1" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  run cat "$rec1"
  [[ "$output" == *"model=deepseek/deepseek-v4-flash"* ]]
  [[ "$output" == *"effort=off"* ]]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"model: deepseek/deepseek-v4-flash"* ]]
  [[ "$output" == *"effort: off"* ]]
  [[ "$output" == *"route: implement/docs/XS"* ]]

  # OPENROUTER_MODEL override wins and marks the route explicit.
  REC="$rec2" OPENROUTER_MODEL=x/y FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" \
    FACTORY_PLAN="$plan" FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= \
    run "$REAL_BASH" "$seat_copy/factory-task" r2 "$repo" K1
  [ "$status" -eq 0 ]
  run cat "$rec2"
  [[ "$output" == *"model=x/y"* ]]
  run cat "$root/runs/r2/K1.result"
  [[ "$output" == *"model: x/y"* ]]
  [[ "$output" == *"route: explicit"* ]]

  # (code, M) -> Pro at medium, route implement/code/M.
  REC="$rec3" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r3 "$repo" K2
  [ "$status" -eq 0 ]
  run cat "$rec3"
  [[ "$output" == *"model=deepseek/deepseek-v4-pro-0813"* ]]
  [[ "$output" == *"effort=medium"* ]]
  run cat "$root/runs/r3/K2.result"
  [[ "$output" == *"model: deepseek/deepseek-v4-pro-0813"* ]]
  [[ "$output" == *"effort: medium"* ]]
  [[ "$output" == *"route: implement/code/M"* ]]

  # --model flag beats the route and marks the route explicit. This is the
  # flag path, distinct from the OPENROUTER_MODEL env path above; the route
  # must not clobber an operator's explicit --model choice.
  REC="$rec4" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r4 "$repo" K1 --model x/y
  [ "$status" -eq 0 ]
  run cat "$rec4"
  [[ "$output" == *"model=x/y"* ]]
  run cat "$root/runs/r4/K1.result"
  [[ "$output" == *"model: x/y"* ]]
  [[ "$output" == *"route: explicit"* ]]

  # OPENROUTER_REASONING_EFFORT, when set to a NON-empty value, beats the
  # route's effort while the model still comes from the route (docs/XS -> flash
  # at route effort off, overridden to high).
  REC="$rec5" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT=high OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r5 "$repo" K1
  [ "$status" -eq 0 ]
  run cat "$rec5"
  [[ "$output" == *"model=deepseek/deepseek-v4-flash"* ]]
  [[ "$output" == *"effort=high"* ]]
  run cat "$root/runs/r5/K1.result"
  [[ "$output" == *"model: deepseek/deepseek-v4-flash"* ]]
  [[ "$output" == *"effort: high"* ]]
  [[ "$output" == *"route: implement/docs/XS"* ]]
}

@test "factory_route --route claude picks the claude row, rows without route resolve under openrouter, and route=other is rejected" {
  toml="$BATS_TEST_TMPDIR/routing-route.toml"
  cat >"$toml" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"

[[route]]
route = "claude"
role = "review"
kind = "code"
size = "any"
model = "opus"
effort = "high"

[[route]]
route = "claude"
role = "implement"
kind = "any"
size = "any"
model = "sonnet"
effort = "high"
EOF
  # --route claude resolves the most specific claude row: review/code/any -> opus high.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route claude review code any '$toml'"
  [ "$status" -eq 0 ]
  [ "$output" = "opus high" ]
  # Without --route the openrouter default wins over every claude row.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route review code any '$toml'"
  [ "$output" = "deepseek/deepseek-v4-pro-0813 medium" ]
  # A claude implement/any/any row is visible under --route claude but not by default.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route claude implement docs XS '$toml'"
  [ "$output" = "sonnet high" ]

  # A row with no route key still resolves under openrouter.
  noroute="$BATS_TEST_TMPDIR/no-route.toml"
  cat >"$noroute" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "m/b"
effort = "off"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/a"
effort = "low"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement code S '$noroute'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/b off" ]

  # route = "other" is rejected.
  badroute="$BATS_TEST_TMPDIR/bad-route.toml"
  cat >"$badroute" <<'EOF'
[[route]]
route = "other"
role = "any"
kind = "any"
size = "any"
model = "m/x"
effort = "low"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/y"
effort = "low"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route any any any '$badroute'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"unknown route"* ]]
}

@test "factory_route rejects --route claude when there is no claude default row" {
  toml="$BATS_TEST_TMPDIR/no-claude-default.toml"
  cat >"$toml" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/a"
effort = "low"

[[route]]
route = "claude"
role = "review"
kind = "code"
size = "any"
model = "opus"
effort = "high"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route claude any any any '$toml'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"no default"* ]]
}

@test "factory_route honors FACTORY_ROUTING_TABLE as the default table and an explicit FILE still wins" {
  # The H2 gate (docs/reviews/2026-09-05-opus-review-hr1-H2.md) flagged that
  # FACTORY_ROUTING_TABLE was promised by the harness prose but read nowhere.
  # Here it must name the default routing table: with no positional FILE,
  # factory_route reads the table FACTORY_ROUTING_TABLE points at, not the
  # FACTORY_TOOLBOX_REPO default, so the fixture's default row wins.
  envfx="$BATS_TEST_TMPDIR/env-routing.toml"
  cat >"$envfx" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "x/env-model"
effort = "low"

[[route]]
role = "implement"
kind = "code"
size = "any"
model = "x/env-code"
effort = "high"
EOF
  # No FILE argument: the env var names the table, implement/code/S -> env-code.
  FACTORY_ROUTING_TABLE="$envfx" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement code S"
  [ "$status" -eq 0 ]
  [ "$output" = "x/env-code high" ]
  # Another lookup so the test does not depend on one row: review (no
  # implement/code row) falls to the default row named by the env table.
  FACTORY_ROUTING_TABLE="$envfx" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route review any S"
  [ "$status" -eq 0 ]
  [ "$output" = "x/env-model low" ]
  # An explicit FILE still wins over the env var.
  explicit="$BATS_TEST_TMPDIR/explicit-routing.toml"
  cat >"$explicit" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "x/explicit-model"
effort = "off"
EOF
  FACTORY_ROUTING_TABLE="$envfx" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement code S '$explicit'"
  [ "$status" -eq 0 ]
  [ "$output" = "x/explicit-model off" ]
}

@test "factory_route_check honors FACTORY_ROUTING_TABLE as the default table" {
  # factory_route_check's default FILE must follow the same env-var override:
  # pointing FACTORY_ROUTING_TABLE at a valid two-route fixture must pass, and
  # at a table missing a claude default row must fail (proving the env table,
  # not the committed one, was read).
  valid="$BATS_TEST_TMPDIR/env-check-valid.toml"
  cat >"$valid" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "x/env-model"
effort = "low"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
EOF
  FACTORY_ROUTING_TABLE="$valid" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check"
  [ "$status" -eq 0 ]

  noclude="$BATS_TEST_TMPDIR/env-check-noclude.toml"
  cat >"$noclude" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "x/env-model"
effort = "low"
EOF
  FACTORY_ROUTING_TABLE="$noclude" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check"
  [ "$status" -eq 3 ]
}

@test "route.py validates the committed table and cross-checks factory_route's lookup, when route.py is present" {
  # The unit-check sandbox now copies tools/factory/route.py and the table
  # (flake.nix), so this cross-check runs against the committed table both in
  # the sandbox and locally; the two implementations must agree or this stays
  # red. The skips below are defensive guards against a flake-copy regression.
  route_py="$SEAT/../route.py"
  [ -f "$route_py" ] || skip "tools/factory/route.py not copied into the unit-check sandbox"
  table="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
  [ -f "$table" ] || skip "docs/ledger/routing.toml not copied into the unit-check sandbox"

  # The committed table parses and every row is valid.
  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' check"
  [ "$status" -eq 0 ]

  # A malformed row fails check with exit 1 naming the offending row number.
  bad="$BATS_TEST_TMPDIR/route-bad.toml"
  cat >"$bad" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/a"
effort = "low"

[[route]]
route = "other"
role = "any"
kind = "any"
size = "any"
model = "m/b"
effort = "low"
EOF
  run "$REAL_BASH" -c "python3 '$route_py' --file '$bad' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"row 2"* ]]

  # lookup claude review docs S -> sonnet medium (the claude review/docs row).
  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup claude review docs S"
  [ "$status" -eq 0 ]
  [ "$output" = "sonnet medium" ]

  # Six fixed tuples: the bash lookup and the python lookup print identical lines.
  while read -r route role kind size; do
    [ -n "$route" ] || continue
    a=$("$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route '$route' '$role' '$kind' '$size' '$table'")
    b=$(python3 "$route_py" --file "$table" lookup "$route" "$role" "$kind" "$size")
    [ "$a" = "$b" ] || {
      printf 'factory_route and route.py disagree for %s/%s/%s/%s: %q vs %q\n' "$route" "$role" "$kind" "$size" "$a" "$b" >&2
      return 1
    }
  done <<'EOF'
claude review code S
claude review docs XS
claude implement code M
claude verify code L
claude audit any any
openrouter implement docs XS
openrouter review code S
EOF
}

@test "factory_route and route.py agree on a discriminating tie (earliest row wins)" {
  # The committed table's one genuine tie has the same model+effort in both
  # rows, so no lookup can observe the tie order. This fixture has two rows of
  # equal specificity (implement/docs/any and implement/any/XS, both spec 2)
  # with DIFFERENT models, so a flipped tie-break in either implementation
  # diverges here: flipping route.py's `spec > best_spec` to `>=` makes its
  # lookup print m/second while bash still prints m/first.
  route_py="$SEAT/../route.py"
  tie="$BATS_TEST_TMPDIR/tie.toml"
  cat >"$tie" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/default"
effort = "low"

[[route]]
role = "implement"
kind = "docs"
size = "any"
model = "m/first"
effort = "high"

[[route]]
role = "implement"
kind = "any"
size = "XS"
model = "m/second"
effort = "xhigh"
EOF
  bash_out=$("$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement docs XS '$tie'")
  py_out=$(python3 "$route_py" --file "$tie" lookup openrouter implement docs XS)
  [ "$bash_out" = "m/first high" ] || {
    printf 'factory_route tie: expected "m/first high", got %q\n' "$bash_out" >&2
    return 1
  }
  [ "$py_out" = "m/first high" ] || {
    printf 'route.py tie: expected "m/first high", got %q\n' "$py_out" >&2
    return 1
  }
  [ "$bash_out" = "$py_out" ] || {
    printf 'factory_route and route.py disagree on the tie: %q vs %q\n' "$bash_out" "$py_out" >&2
    return 1
  }
}

@test "route.py check rejects a row missing any required key, a bad route, or a bad effort" {
  route_py="$SEAT/../route.py"

  # A row missing each of the five required keys (role/kind/size/model/effort)
  # fails check with exit 1 naming the row and the missing key. `route` is the
  # one key that may be omitted: it defaults to openrouter, in both route.py
  # and the bash lookup (pinned by the no-route fixture in the --route test).
  for key in role kind size model effort; do
    bad="$BATS_TEST_TMPDIR/check-missing-$key.toml"
    {
      printf '[[route]]\nroute = "openrouter"\nrole = "any"\nkind = "any"\nsize = "any"\nmodel = "m/a"\neffort = "low"\n\n'
      printf '[[route]]\n'
      for k in role kind size model effort; do
        [ "$k" = "$key" ] && continue
        case $k in
          role) v=implement ;;
          kind) v=any ;;
          size) v=any ;;
          model) v=m/b ;;
          effort) v=off ;;
        esac
        printf '%s = "%s"\n' "$k" "$v"
      done
    } >"$bad"
    run "$REAL_BASH" -c "python3 '$route_py' --file '$bad' check"
    [ "$status" -eq 1 ] || {
      printf 'missing %s: check exited %d, expected 1\n' "$key" "$status" >&2
      return 1
    }
    [[ "$output" == *"row 2"* ]] || {
      printf 'missing %s: output %q does not name row 2\n' "$key" "$output" >&2
      return 1
    }
    [[ "$output" == *"missing one of"* ]] || {
      printf 'missing %s: output %q does not name the missing key\n' "$key" "$output" >&2
      return 1
    }
  done

  # route = "other" is rejected with exit 1 naming the row.
  badroute="$BATS_TEST_TMPDIR/check-bad-route.toml"
  cat >"$badroute" <<'EOF'
[[route]]
route = "other"
role = "any"
kind = "any"
size = "any"
model = "m/x"
effort = "low"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/y"
effort = "low"
EOF
  run "$REAL_BASH" -c "python3 '$route_py' --file '$badroute' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"row 1"* ]]
  [[ "$output" == *"unknown route"* ]]

  # An effort outside the five words is rejected with exit 1 naming the row.
  badeffort="$BATS_TEST_TMPDIR/check-bad-effort.toml"
  cat >"$badeffort" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/x"
effort = "max"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/y"
effort = "low"
EOF
  run "$REAL_BASH" -c "python3 '$route_py' --file '$badeffort' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"row 1"* ]]
  [[ "$output" == *"bad effort"* ]]

  # A row without a route key passes check: it defaults to openrouter, and
  # both the openrouter default (row 2) and claude default (row 3) are present
  # so the two no-default probes succeed.
  noroute="$BATS_TEST_TMPDIR/check-no-route.toml"
  cat >"$noroute" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "m/b"
effort = "off"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/a"
effort = "low"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
EOF
  run "$REAL_BASH" -c "python3 '$route_py' --file '$noroute' check"
  [ "$status" -eq 0 ]
}

@test "route.py honors FACTORY_ROUTING_TABLE as the default table and an explicit --file still wins" {
  route_py="$SEAT/../route.py"
  # With no --file, FACTORY_ROUTING_TABLE names the table (H2 gate):
  # the fixture's claude default row drives the lookup.
  envfx="$BATS_TEST_TMPDIR/env-routing.toml"
  cat >"$envfx" <<'EOF'
[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "x/env-model"
effort = "high"
EOF
  FACTORY_ROUTING_TABLE="$envfx" run "$REAL_BASH" -c "python3 '$route_py' lookup claude review code S"
  [ "$status" -eq 0 ]
  [ "$output" = "x/env-model high" ]
  # An explicit --file still wins over the env var.
  explicit="$BATS_TEST_TMPDIR/explicit-routing.toml"
  cat >"$explicit" <<'EOF'
[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "x/explicit-model"
effort = "off"
EOF
  FACTORY_ROUTING_TABLE="$envfx" run "$REAL_BASH" -c "python3 '$route_py' --file '$explicit' lookup claude review code S"
  [ "$status" -eq 0 ]
  [ "$output" = "x/explicit-model off" ]
}

@test "factory-task submits through seat-submit when it is on PATH and records the seat: line" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  # Routing fixture: (docs, XS) -> deepseek-v4-flash at off, so the routed
  # model/effort can be observed in the args handed to the fake seat-submit.
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  # The fake seat-submit records its argv, the --brief file's content (so the
  # composed brief, the workspace and the isolated DSH_HOME can all be pinned),
  # and prints a job id then a valid FACTORY-RESULT block.
  cat >"$bin/seat-submit" <<FAKE
#!$REAL_BASH
printf 'args=%s\\n' "\$*" >> "\$REC"
brief=
prev=
for a in "\$@"; do
  if [ "\$prev" = "--brief" ]; then brief="\$a"; fi
  prev="\$a"
done
printf 'brief_begin\\n' >> "\$REC"
cat -- "\$brief" >> "\$REC"
printf 'brief_end\\n' >> "\$REC"
printf '20260905-120000-abcdef\\n'
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/seat-submit"
  # A fake dsh-openrouter that would leave a marker if the old path ran.
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
: > "\$DSH_CALLED"
printf 'FACTORY-RESULT status=done\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  rec="$BATS_TEST_TMPDIR/rec"
  dsh_called="$BATS_TEST_TMPDIR/DSH_CALLED"
  REC="$rec" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    DSH_CALLED="$dsh_called" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  # dsh-openrouter must NOT have been called; seat-submit must have been, and
  # with the routed model/effort.
  [ ! -e "$dsh_called" ]
  run cat "$rec"
  [[ "$output" == *"--model deepseek/deepseek-v4-flash"* ]]
  [[ "$output" == *"--effort off"* ]]
  # F2 / M12 / M13 / M14: the isolated DSH_HOME, the workspace and the composed
  # brief are all handed to seat-submit intact (never the shared home, never
  # /tmp, never a placeholder brief).
  [[ "$output" == *"--dsh-home $root/runs/r1/K1.dsh-home"* ]]
  [[ "$output" == *"--workspace $BATS_TEST_TMPDIR/ws"* ]]
  [[ "$output" == *"brief_begin"*"body one."*"brief_end"* ]]
  [[ "$output" == *"## WORKSPACE RULES"* ]]
  # The .result keeps today's shape (the seat's stdout.txt content was parsed
  # for the FACTORY-RESULT block) and adds the one seat: line.
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=done"* ]]
  [[ "$output" == *"seat: unit seat@20260905-120000-abcdef"* ]]
  [[ "$output" == *"model: deepseek/deepseek-v4-flash"* ]]
  [[ "$output" == *"route: implement/docs/XS"* ]]
}

@test "factory-task reads the job id from stdout alone, not a stderr warning line" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  # F1: seat-submit may write a warning to stderr before the id lands on
  # stdout. The .result's seat: line must name the id from stdout, never the
  # stderr text.
  cat >"$bin/seat-submit" <<FAKE
#!$REAL_BASH
printf 'seat-submit: warning: something about the job\\n' >&2
printf '20260905-120000-abcdef\\n'
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/seat-submit"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
: > "\$DSH_CALLED"
printf 'FACTORY-RESULT status=done\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  dsh_called="$BATS_TEST_TMPDIR/DSH_CALLED"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    DSH_CALLED="$dsh_called" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  [ ! -e "$dsh_called" ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"seat: unit seat@20260905-120000-abcdef"* ]]
  [[ "$output" != *"seat: unit seat@seat-submit: warning"* ]]
}

@test "factory-task records a failed submit when seat-submit prints no valid job id" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  # A first stdout line that is not a job id: the submit has produced no usable
  # id, so factory-task must record a failure and a "no job id" seat: line
  # rather than recording the garbage as the unit name.
  cat >"$bin/seat-submit" <<FAKE
#!$REAL_BASH
printf 'garbage\\n'
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/seat-submit"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
: > "\$DSH_CALLED"
printf 'FACTORY-RESULT status=done\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  dsh_called="$BATS_TEST_TMPDIR/DSH_CALLED"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    DSH_CALLED="$dsh_called" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=failed"* ]]
  [[ "$output" == *"seat: submit failed (no job id)"* ]]
  [[ "$output" != *"garbage"* ]]
}

@test "factory-task keeps the old path when FACTORY_SEAT_UNIT=0 even when seat-submit is present" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
: > "\$DSH_CALLED"
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  # A fake seat-submit that would leave a marker if the submit path ran.
  cat >"$bin/seat-submit" <<FAKE
#!$REAL_BASH
: > "\$SEAT_CALLED"
printf '20260905-120000-abcdef\\n'
FAKE
  chmod +x "$bin/seat-submit"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  dsh_called="$BATS_TEST_TMPDIR/DSH_CALLED"
  seat_called="$BATS_TEST_TMPDIR/SEAT_CALLED"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    DSH_CALLED="$dsh_called" SEAT_CALLED="$seat_called" \
    FACTORY_SEAT_UNIT=0 OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  # dsh-openrouter ran, seat-submit did not, and there is no seat: line.
  [ -e "$dsh_called" ]
  [ ! -e "$seat_called" ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=done"* ]]
  [[ "$output" != *"seat: unit seat@"* ]]
}

@test "factory-review resolves role review through routing.toml and launches the seat with the route effort" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  # factory-ws prints a workspace path and succeeds, so factory-review runs to
  # completion and launches the (fake) review seat.
  mkdir -p "$BATS_TEST_TMPDIR/wspath"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/wspath" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  # A fixture table whose review row DIFFERS from implement: role review must
  # resolve review/any/any (flash/high), not the implement row (pro/off), and
  # the route's effort must reach the launch environment.
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "review"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "high"

[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "off"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/ws/r1/K1" "$root/runs"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'model=%s\\n' "\$2" >> "\$REC"
printf 'effort=%s\\n' "\${OPENROUTER_REASONING_EFFORT:-}" >> "\$REC"
printf 'FACTORY-REVIEW verdict=approve\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  rec="$BATS_TEST_TMPDIR/rec"
  REC="$rec" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-review" r1 "$repo" K1
  [ "$status" -eq 0 ]
  run cat "$rec"
  [[ "$output" == *"model=deepseek/deepseek-v4-flash"* ]]
  [[ "$output" == *"effort=high"* ]]
}

@test "factory-wave writes run.meta recording identity, base SHA, quoted groups, pid and --then before dispatch" {
  # A fake ps reports the wave as already a session leader so the setsid
  # re-exec path never fires in the sandbox; a fake setsid must not be called
  # (it exits 9, so a stray re-exec would fail the run).
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\\n' "\${pid:-0}"
FAKE
  chmod +x "$bin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$bin/setsid"
  chmod +x "$bin/setsid"
  repo="$BATS_TEST_TMPDIR/repo"
  git init -q -b main "$repo"
  git -C "$repo" config user.email t@x; git -C "$repo" config user.name t
  printf 'x\n' >"$repo/f"; git -C "$repo" add f; git -C "$repo" commit -qm init
  sha=$(git -C "$repo" rev-parse HEAD)
  # A fake factory-task writes a done .result and records whether run.meta
  # existed at ITS launch and whether the recorded pid was then alive.
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
run="\$1"; key="\$3"
d="\$FACTORY_ROOT/runs/\$run"
if [ -f "\$d/run.meta" ]; then printf 'run.meta-present\\n' >> "\$REC"; else printf 'run.meta-absent\\n' >> "\$REC"; fi
p=\$(sed -n 's/^pid: //p' "\$d/run.meta" 2>/dev/null | head -n1)
if [ -n "\$p" ] && kill -0 "\$p" 2>/dev/null; then printf 'pid-alive\\n' >> "\$REC"; else printf 'pid-not-alive\\n' >> "\$REC"; fi
mkdir -p "\$d"
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 0
RESULT
FAKE
  chmod +x "$fact/factory-task"
  root="$BATS_TEST_TMPDIR/factory"
  rec="$BATS_TEST_TMPDIR/rec"
  REC="$rec" PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" --then "gate; ff; dispatch G12b" "K1 K2"
  [ "$status" -eq 0 ]
  [ -f "$root/runs/r1/run.meta" ]
  run cat "$root/runs/r1/run.meta"
  [[ "$output" == *"run: r1"* ]]
  [[ "$output" == *"repo: $repo"* ]]
  [[ "$output" == *"base: $sha"* ]]
  [[ "$output" == *'group: K1\ K2'* ]]
  [[ "$output" == *"launched: "* ]]
  [[ "$output" == *"then: gate; ff; dispatch G12b"* ]]
  # pid is the wave's own pid, a positive integer (never 0 -- the reader treats
  # 0 as dead).
  p=$(sed -n 's/^pid: //p' "$root/runs/r1/run.meta")
  [[ "$p" =~ ^[1-9][0-9]*$ ]]
  # run.meta existed before the first task ran, and its pid was alive then.
  run cat "$rec"
  [[ "$output" == *"run.meta-present"* ]]
  [[ "$output" == *"pid-alive"* ]]
  [[ "$output" != *"run.meta-absent"* ]]
  [[ "$output" != *"pid-not-alive"* ]]
}

@test "factory-wave writes one quoted group: line per wave group, so parallel and a chain differ" {
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\\n' "\${pid:-0}"
FAKE
  chmod +x "$bin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$bin/setsid"
  chmod +x "$bin/setsid"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 0
RESULT
FAKE
  chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"
  git init -q -b main "$repo"
  git -C "$repo" config user.email t@x; git -C "$repo" config user.name t
  printf 'x\n' >"$repo/f"; git -C "$repo" add f; git -C "$repo" commit -qm init
  root="$BATS_TEST_TMPDIR/factory"
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1" "K2"
  [ "$status" -eq 0 ]
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r2 "$repo" "K1 K2"
  [ "$status" -eq 0 ]
  run cat "$root/runs/r1/run.meta"
  [[ "$(grep -cxF 'group: K1' <<< "$output")" -eq 1 ]]
  [[ "$(grep -cxF 'group: K2' <<< "$output")" -eq 1 ]]
  [[ "$(grep -cxF 'group: K1\ K2' <<< "$output")" -eq 0 ]]
  run cat "$root/runs/r2/run.meta"
  [[ "$(grep -cxF 'group: K1\ K2' <<< "$output")" -eq 1 ]]
  [[ "$(grep -cxF 'group: K1' <<< "$output")" -eq 0 ]]
}

@test "factory-wave re-execs under setsid -w when it is not a session leader" {
  # ps reports a foreign session id, so factory-wave must re-exec; the fake
  # setsid records its argv (which must include -w) and exits before running
  # the wave's body.
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
printf '999999\\n'
FAKE
  chmod +x "$bin/ps"
  rec="$BATS_TEST_TMPDIR/setsid-args"
  cat >"$bin/setsid" <<FAKE
#!$REAL_BASH
printf '%s\\n' "\$*" >"$rec"
exit 0
FAKE
  chmod +x "$bin/setsid"
  # FACTORY_BIN_OVERRIDE is set so no test here can ever reach the real
  # factory-task (the file header's promise).
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  printf '#!%s\nexit 0\n' "$REAL_BASH" >"$fact/factory-task"; chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; git init -q -b main "$repo"
  root="$BATS_TEST_TMPDIR/factory"
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" --then "gate" "K1"
  [ "$status" -eq 0 ]
  run cat "$rec"
  [[ "$output" == *"-w -- $SEAT/factory-wave r1 $repo --then gate K1"* ]]
  [ ! -e "$root/runs/r1/run.meta" ]
}

@test "setsid -w keeps the wave's exit code when the launcher gives it a process group" {
  command -v setsid >/dev/null 2>&1 && command -v ps >/dev/null 2>&1 || skip "no real setsid/ps in this sandbox"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
sleep 4
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=failed
FACTORY-CHECKS unit=fail
FACTORY-COMMITS 0
FACTORY-NOTES boom
wall_s: 4
RESULT
FAKE
  chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; git init -q -b main "$repo"
  root="$BATS_TEST_TMPDIR/factory"
  start=$(date +%s)
  run bash -c 'set -m; FACTORY_ROOT="$1" FACTORY_BIN_OVERRIDE="$2" bash "$3" r1 "$4" "K1"; echo "RC=$?"' \
    _ "$root" "$fact" "$SEAT/factory-wave" "$repo"
  end=$(date +%s)
  [ "$status" -eq 0 ]
  [[ "$output" == *"RC=1"* ]]
  [ "$((end - start))" -ge 4 ]
}

@test "the wave survives its launcher's process group being SIGKILLed and writes its result" {
  command -v setsid >/dev/null 2>&1 && command -v ps >/dev/null 2>&1 || skip "no real setsid/ps in this sandbox"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
sleep 2
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 2
RESULT
FAKE
  chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; git init -q -b main "$repo"
  root="$BATS_TEST_TMPDIR/factory"
  bash -c '
    set -m
    FACTORY_ROOT="$1" FACTORY_BIN_OVERRIDE="$2" bash "$3" r1 "$4" "K1" &
    launcher=$!
    sleep 1
    kill -KILL -"$launcher" 2>/dev/null || true
    wait "$launcher" 2>/dev/null || true
  ' _ "$root" "$fact" "$SEAT/factory-wave" "$repo"
  for _ in $(seq 1 50); do [ -f "$root/runs/r1/K1.result" ] && break; sleep 0.1; done
  [ -f "$root/runs/r1/K1.result" ]
}

@test "factory-wave --then: absent when not given, last wins when doubled, single-line only" {
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\\n' "\${pid:-0}"
FAKE
  chmod +x "$bin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$bin/setsid"
  chmod +x "$bin/setsid"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 0
RESULT
FAKE
  chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"
  git init -q -b main "$repo"
  git -C "$repo" config user.email t@x; git -C "$repo" config user.name t
  printf 'x\n' >"$repo/f"; git -C "$repo" add f; git -C "$repo" commit -qm init
  root="$BATS_TEST_TMPDIR/factory"

  # No --then: the then: line is absent.
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 0 ]
  run cat "$root/runs/r1/run.meta"
  [[ "$output" != *"then:"* ]]

  # --then twice: the last wins.
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r2 "$repo" --then first --then second "K1"
  [ "$status" -eq 0 ]
  run cat "$root/runs/r2/run.meta"
  [[ "$output" == *"then: second"* ]]
  [[ "$output" != *"then: first"* ]]

  # --then '' : given but empty -> a present, empty then: value.
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r3 "$repo" --then "" "K1"
  [ "$status" -eq 0 ]
  run cat "$root/runs/r3/run.meta"
  [[ "$output" == *"then: "* ]]
  [[ "$output" != *"then: first"* ]]
  [[ "$output" != *"then: second"* ]]

  # A multi-line value breaks the one-key-per-line contract -> exit 2, no meta.
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r4 "$repo" --then $'a\nb\nc' "K1"
  [ "$status" -eq 2 ]
  [ ! -f "$root/runs/r4/run.meta" ]
}

@test "factory-wave refuses a group or --then whose byte %q cannot round-trip (exit 2)" {
  # MINOR-7 (write side): a group or --then value carrying a newline, tab or any
  # byte %q renders as $'...' cannot survive the reader's eval-free unquote, so
  # it is refused at write time -- one refusal line per offending value -- and no
  # run.meta is written. (Mutation: the refusal removed lets a newline group
  # through, and the reader's xargs unquote then misreads it.)
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\n' "\${pid:-0}"
FAKE
  chmod +x "$bin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$bin/setsid"
  chmod +x "$bin/setsid"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$fact/factory-task"; chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; git init -q -b main "$repo"
  root="$BATS_TEST_TMPDIR/factory"

  # A group holding a newline.
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" $'a\nb'
  [ "$status" -eq 2 ]
  [ ! -f "$root/runs/r1/run.meta" ]

  # A --then value holding a tab.
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r2 "$repo" --then $'a\tb' "K1"
  [ "$status" -eq 2 ]
  [ ! -f "$root/runs/r2/run.meta" ]
}

@test "factory-task writes <KEY>.pid while it runs and removes it on exit" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
role = "review"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  # The fake seat observes the <KEY>.pid file's presence while it runs.
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
if [ -f "\$PIDFILE" ]; then printf 'pid-present\\n' >> "\$REC"; else printf 'pid-absent\\n' >> "\$REC"; fi
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  rec="$BATS_TEST_TMPDIR/rec"
  pidfile="$root/runs/r1/K1.pid"
  REC="$rec" PIDFILE="$pidfile" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  run cat "$rec"
  [[ "$output" == *"pid-present"* ]]
  # The pid file is removed once the task exits.
  [ ! -e "$pidfile" ]
}

@test "factory-review leaves a <KEY>.gate marker holding its pid while gating and removes it after" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  mkdir -p "$BATS_TEST_TMPDIR/wspath"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/wspath" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "review"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "high"

[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "off"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/ws/r1/K1" "$root/runs"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  # The fake review seat runs while factory-review is gating, recording whether
  # the marker exists and what it holds (the reviewer's own pid).
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
if [ -f "\$GATE" ]; then printf 'gate-content=%s\\n' "\$(cat "\$GATE")" >> "\$REC"; else printf 'gate-absent\\n' >> "\$REC"; fi
printf 'FACTORY-REVIEW verdict=approve\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  rec="$BATS_TEST_TMPDIR/rec"
  gate="$root/runs/r1/K1.gate"
  REC="$rec" GATE="$gate" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-review" r1 "$repo" K1
  [ "$status" -eq 0 ]
  run cat "$rec"
  [[ "$output" == *"gate-content="* ]]
  gp=$(sed -n 's/^gate-content=//p' "$rec")
  [[ "$gp" =~ ^[1-9][0-9]*$ ]]
  # The marker is removed once the gate finishes, never left as a stale "running".
  [ ! -e "$gate" ]
}

@test "factory-review removes the <KEY>.gate marker on SIGTERM" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  mkdir -p "$BATS_TEST_TMPDIR/wspath"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/wspath" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "review"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "high"

[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "off"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/ws/r1/K1" "$root/runs"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  # The fake review seat sleeps long enough for the gate to be observed and
  # then killed; it self-terminates so no child lingers past the test.
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
sleep 3
printf 'FACTORY-REVIEW verdict=approve\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  gate="$root/runs/r1/K1.gate"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    "$REAL_BASH" "$seat_copy/factory-review" r1 "$repo" K1 &
  fr_pid=$!
  for _ in $(seq 1 50); do [ -f "$gate" ] && break; sleep 0.1; done
  [ -f "$gate" ]
  kill -TERM "$fr_pid" 2>/dev/null || true
  wait "$fr_pid" 2>/dev/null || true
  [ ! -e "$gate" ]
}


@test "factory-review arms the gate EXIT trap before writing the marker" {
  # Structural pin (CR9 MAJOR-2): the trap that removes the marker must precede
  # the line that writes it, so a signal between the two cannot strand the
  # marker. Reversing the two lines fails here.
  f="$SEAT/factory-review"
  trap_ln=$(grep -nF 'rm -f -- "$gate_marker"' "$f" | head -1 | cut -d: -f1)
  write_ln=$(grep -nF '>"$gate_marker"' "$f" | head -1 | cut -d: -f1)
  [ -n "$trap_ln" ]
  [ -n "$write_ln" ]
  [ "$trap_ln" -lt "$write_ln" ]
}

@test "factory-review's trap-before-marker order survives a kill between the two" {
  # Behavioural pin (CR9 MAJOR-2): the gate marker is a FIFO, so factory-review's
  # `printf > marker` blocks (no reader) with the trap already armed. SIGTERM then
  # runs the EXIT trap and removes the marker; the reversed order (trap after the
  # write) leaves it stranded behind.
  command -v mkfifo >/dev/null 2>&1 || skip "no mkfifo in this sandbox"
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/ws/r1/K1" "$root/runs/r1"
  mkfifo "$root/runs/r1/K1.gate"
  FACTORY_ROOT="$root" "$REAL_BASH" "$seat_copy/factory-review" r1 "$repo" K1 &
  fr_pid=$!
  sleep 1
  kill -TERM "$fr_pid" 2>/dev/null || true
  wait "$fr_pid" 2>/dev/null || true
  [ ! -e "$root/runs/r1/K1.gate" ]
}

@test "factory-wave writes group: with %q, round-tripping a quote and a backslash" {
  # MINOR-7 (write side): a group holding a quote and a backslash is written with
  # %q (backslash-escaped), never the hand-quoted `group: "..."` that would
  # collapse the embedded quote.
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\n' "\${pid:-0}"
FAKE
  chmod +x "$bin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$bin/setsid"
  chmod +x "$bin/setsid"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 0
RESULT
FAKE
  chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"
  git init -q -b main "$repo"
  git -C "$repo" config user.email t@x; git -C "$repo" config user.name t
  printf 'x\n' >"$repo/f"; git -C "$repo" add f; git -C "$repo" commit -qm init
  root="$BATS_TEST_TMPDIR/factory"
  grp='a"b\c'
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "$grp"
  [ "$status" -eq 0 ]
  run cat "$root/runs/r1/run.meta"
  expected=$(printf 'group: %q' "$grp")
  [[ "$output" == *"$expected"* ]]
  [[ "$output" != *'group: "a"b\c"'* ]]
}

@test "factory-task demotes status=done when the FACTORY-COMMITS claim does not match the branch" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  ws="$BATS_TEST_TMPDIR/ws"; git init -q -b main "$ws"
  git -C "$ws" config user.email t@x; git -C "$ws" config user.name t
  printf 'x\n' >"$ws/f"; git -C "$ws" add f; git -C "$ws" commit -qm base
  base_sha=$(git -C "$ws" rev-parse HEAD)
  git -C "$ws" checkout -qb task/K1
  printf 'y\n' >"$ws/g"; git -C "$ws" add g; git -C "$ws" commit -qm work
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/ws/r1/K1"
  printf 'base_sha=%s\n' "$base_sha" >"$root/ws/r1/K1/.factory-meta"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'FACTORY-RESULT status=done exit_code=124\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 5\\n'
printf 'FACTORY-NOTES finished the work\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=failed exit_code=124"* ]]
  [[ "$output" == *"finished the work"* ]]
  [[ "$output" == *"claimed 5 commits, found 1"* ]]
}

@test "factory-task leaves a failed run's own notes intact, not overwritten by the commit check" {
  # MINOR-1: the commits-mismatch arm must fire only when the seat claimed
  # status=done. A seat that honestly reports status=failed with real notes and
  # a branch holding one checkpoint commit keeps its explanation; the arm does
  # not fire and does not replace the FACTORY-NOTES line. (Mutation: the arm
  # firing on a failed run replaces the notes with the claimed/found line.)
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  ws="$BATS_TEST_TMPDIR/ws"; git init -q -b main "$ws"
  git -C "$ws" config user.email t@x; git -C "$ws" config user.name t
  printf 'x\n' >"$ws/f"; git -C "$ws" add f; git -C "$ws" commit -qm base
  base_sha=$(git -C "$ws" rev-parse HEAD)
  git -C "$ws" checkout -qb task/K1
  printf 'y\n' >"$ws/g"; git -C "$ws" add g; git -C "$ws" commit -qm work
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/ws/r1/K1"
  printf 'base_sha=%s\n' "$base_sha" >"$root/ws/r1/K1/.factory-meta"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'FACTORY-RESULT status=failed\\n'
printf 'FACTORY-CHECKS unit=fail\\n'
printf 'FACTORY-COMMITS 0\\n'
printf 'FACTORY-NOTES the unit check failed on tests/unit/80; see the log\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=failed"* ]]
  [[ "$output" == *"FACTORY-NOTES the unit check failed on tests/unit/80; see the log"* ]]
  [[ "$output" != *"claimed 0 commits"* ]]
}

@test "factory-task never records status=done for a run with no commit" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  ws="$BATS_TEST_TMPDIR/ws"; git init -q -b main "$ws"
  git -C "$ws" config user.email t@x; git -C "$ws" config user.name t
  printf 'x\n' >"$ws/f"; git -C "$ws" add f; git -C "$ws" commit -qm base
  base_sha=$(git -C "$ws" rev-parse HEAD)
  git -C "$ws" checkout -qb task/K1
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/ws/r1/K1"
  printf 'base_sha=%s\n' "$base_sha" >"$root/ws/r1/K1/.factory-meta"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 0\\n'
printf 'FACTORY-NOTES finished the work\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=failed"* ]]
  [[ "$output" == *"no commits"* ]]
}

@test "factory-task rejects a bare-ok result as a template echo, not a completion" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  ws="$BATS_TEST_TMPDIR/ws"; git init -q -b main "$ws"
  git -C "$ws" config user.email t@x; git -C "$ws" config user.name t
  printf 'x\n' >"$ws/f"; git -C "$ws" add f; git -C "$ws" commit -qm base
  base_sha=$(git -C "$ws" rev-parse HEAD)
  git -C "$ws" checkout -qb task/K1
  printf 'y\n' >"$ws/g"; git -C "$ws" add g; git -C "$ws" commit -qm work
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/ws/r1/K1"
  printf 'base_sha=%s\n' "$base_sha" >"$root/ws/r1/K1/.factory-meta"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=failed"* ]]
  [[ "$output" == *"bare result"* ]]
}

@test "factory-task refuses to run when FACTORY_PLAN is unset, exiting 2 before creating a run dir" {
  # Mutation: restore `${FACTORY_PLAN:-default}` so an unset plan falls back to
  # the 2026-09-04 default -> the "is unset" message never prints and a run dir
  # is written, leaving this red.
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"
  FACTORY_ROOT="$root" run env -u FACTORY_PLAN "$REAL_BASH" "$SEAT/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  [[ "$output" == *"FACTORY_PLAN is unset"* ]]
  [ ! -e "$root/runs/r1" ]
}

@test "factory-wave refuses to run when FACTORY_PLAN is unset, exiting 2 before writing run.meta or calling a task" {
  # Mutation: move the check after run.meta is written -> the file exists here,
  # leaving this red.
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\n' "\${pid:-0}"
FAKE
  chmod +x "$bin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$bin/setsid"
  chmod +x "$bin/setsid"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
: > "\$CALLED"
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 0
RESULT
FAKE
  chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; git init -q -b main "$repo"
  root="$BATS_TEST_TMPDIR/factory"
  called="$BATS_TEST_TMPDIR/called"
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" CALLED="$called" \
    run env -u FACTORY_PLAN "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 2 ]
  [[ "$output" == *"FACTORY_PLAN is unset"* ]]
  [ ! -e "$called" ]
  [ ! -e "$root/runs/r1/run.meta" ]
}

@test "factory-wave records plan: in run.meta and passes FACTORY_PLAN through to every task" {
  # Mutation: drop the `plan:` line from run.meta -> the first grep fails.
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\n' "\${pid:-0}"
FAKE
  chmod +x "$bin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$bin/setsid"
  chmod +x "$bin/setsid"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
printf 'plan=%s\n' "\${FACTORY_PLAN:-}" >> "\$REC"
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 0
RESULT
FAKE
  chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; git init -q -b main "$repo"
  root="$BATS_TEST_TMPDIR/factory"
  planfile="$BATS_TEST_TMPDIR/plan.md"
  printf '### K1 (code, M) — t\n\nbody.\n' >"$planfile"
  rec="$BATS_TEST_TMPDIR/rec"
  REC="$rec" PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" FACTORY_PLAN="$planfile" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 0 ]
  run cat "$root/runs/r1/run.meta"
  [[ "$output" == *"plan: $planfile"* ]]
  run cat "$rec"
  [ "$output" = "plan=$planfile" ]
}

@test "factory-integrate refuses a board rewrite outside the queue block but merges an untouched key" {
  # Mutation: drop the queue-block check -> K1 merges cleanly and its subject
  # appears in integ/r1, leaving `REFUSED K1` and the log assertion red.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  mkdir -p "$src/docs"
  printf 'prologue\n<!-- tasks:begin -->\nqueue\n<!-- tasks:end -->\nepilogue\n' >"$src/docs/OPERATIONS.md"
  git -C "$src" add docs/OPERATIONS.md
  git -C "$src" commit -q -m "init"
  git clone -q "$src" "$root/base/src"
  # K1 adds a prose line outside the queue markers.
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  printf 'intruder\n' >>"$root/ws/r1/K1/docs/OPERATIONS.md"
  git -C "$root/ws/r1/K1" add docs/OPERATIONS.md
  git -C "$root/ws/r1/K1" commit -q -m "k1: board prose (test: unit)"
  # K2 only adds a file, never touching the board.
  git clone -q "$src" "$root/ws/r1/K2"
  git -C "$root/ws/r1/K2" config user.name t
  git -C "$root/ws/r1/K2" config user.email t@x
  git -C "$root/ws/r1/K2" checkout -q -b task/K2
  printf 'y\n' >"$root/ws/r1/K2/y"
  git -C "$root/ws/r1/K2" add y
  git -C "$root/ws/r1/K2" commit -q -m "k2: add y (test: unit)"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1 K2
  [ "$status" -eq 1 ]
  [[ "$output" == *"REFUSED K1"* ]]
  [[ "$output" == *"MERGE K2 ok"* ]]
  [[ "$output" == *"refused: 1"* ]]
  run git -C "$root/base/src" log --oneline integ/r1
  [[ "$output" != *"k1: board prose"* ]]
  [[ "$output" == *"k2: add y"* ]]
}

@test "factory-integrate's board guard merges a queue-block-only change and refuses a mixed one" {
  # Mutation: drop the block masking (compare the raw files) -> K3's marker-line
  # edit is read as a rewrite and is REFUSED, leaving `MERGE K3 ok` red.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  mkdir -p "$src/docs"
  printf 'prologue\n<!-- tasks:begin -->\nqueue\n<!-- tasks:end -->\nepilogue\n' >"$src/docs/OPERATIONS.md"
  git -C "$src" add docs/OPERATIONS.md
  git -C "$src" commit -q -m "init"
  git clone -q "$src" "$root/base/src"
  # K3 changes only a line between the markers.
  git clone -q "$src" "$root/ws/r1/K3"
  git -C "$root/ws/r1/K3" config user.name t
  git -C "$root/ws/r1/K3" config user.email t@x
  git -C "$root/ws/r1/K3" checkout -q -b task/K3
  sed -i 's/^queue$/queue2/' "$root/ws/r1/K3/docs/OPERATIONS.md"
  git -C "$root/ws/r1/K3" add docs/OPERATIONS.md
  git -C "$root/ws/r1/K3" commit -q -m "k3: queue only (test: unit)"
  # K4 changes a marker-inside line AND adds a line outside the markers.
  git clone -q "$src" "$root/ws/r1/K4"
  git -C "$root/ws/r1/K4" config user.name t
  git -C "$root/ws/r1/K4" config user.email t@x
  git -C "$root/ws/r1/K4" checkout -q -b task/K4
  sed -i 's/^queue$/queue2/' "$root/ws/r1/K4/docs/OPERATIONS.md"
  printf 'intruder\n' >>"$root/ws/r1/K4/docs/OPERATIONS.md"
  git -C "$root/ws/r1/K4" add docs/OPERATIONS.md
  git -C "$root/ws/r1/K4" commit -q -m "k4: mixed (test: unit)"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K3 K4
  [ "$status" -eq 1 ]
  [[ "$output" == *"MERGE K3 ok"* ]]
  [[ "$output" == *"REFUSED K4"* ]]
}

@test "factory-integrate's board guard compares against the merge base, not origin's moving tip" {
  # Mutation: compare against `origin/main`'s tip instead of the merge base ->
  # main's own board prose (committed after K5 forked) reads as K5's change and
  # K5 is falsely refused, leaving `MERGE K5 ok` red.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  mkdir -p "$src/docs"
  printf 'prologue\n<!-- tasks:begin -->\nqueue\n<!-- tasks:end -->\nepilogue\n' >"$src/docs/OPERATIONS.md"
  git -C "$src" add docs/OPERATIONS.md
  git -C "$src" commit -q -m "init"
  git clone -q "$src" "$root/base/src"
  # K5 forks at init, adds only a file, never touching the board.
  git clone -q "$src" "$root/ws/r1/K5"
  git -C "$root/ws/r1/K5" config user.name t
  git -C "$root/ws/r1/K5" config user.email t@x
  git -C "$root/ws/r1/K5" checkout -q -b task/K5
  printf 'z\n' >"$root/ws/r1/K5/z"
  git -C "$root/ws/r1/K5" add z
  git -C "$root/ws/r1/K5" commit -q -m "k5: add z (test: unit)"
  # After K5 forked, main itself gains a board prose commit.
  printf 'main intruder\n' >>"$src/docs/OPERATIONS.md"
  git -C "$src" add docs/OPERATIONS.md
  git -C "$src" commit -q -m "main board prose"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K5
  [ "$status" -eq 0 ]
  [[ "$output" == *"MERGE K5 ok"* ]]
  run git -C "$root/base/src" log --oneline integ/r1
  [[ "$output" == *"k5: add z"* ]]
}

@test "factory-task records a near-miss result block verbatim as failed" {
  # Mutation: drop the near-miss capture -> the notes read `the seat produced no
  # usable FACTORY-RESULT line; see <log>`, leaving this notes assertion red.
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf '%b\n' "\${PAYLOAD}"
FAKE
  chmod +x "$bin/dsh-openrouter"
  PAYLOAD=$'FACTORY-RESULT: status=done' FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" \
    FACTORY_PLAN="$plan" FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    FACTORY_SEAT_UNIT=0 OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [[ "${lines[0]}" == "FACTORY-RESULT status=failed exit_code=0" ]]
  [[ "$output" == *"FACTORY-NOTES result-misparse: FACTORY-RESULT: status=done"* ]]
}

@test "factory-task records every near-miss spelling verbatim, accepted forms as themselves, and truncates to 200 bytes" {
  # One shared fixture; the fake seat prints whatever PAYLOAD holds. Each arm
  # names the office one-line mutant that flips it.
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf '%b\n' "\${PAYLOAD}"
FAKE
  chmod +x "$bin/dsh-openrouter"
  run_task() {
    PAYLOAD="$1" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
      FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
      OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
      run "$REAL_BASH" "$seat_copy/factory-task" "$2" "$repo" K1
  }

  # The four near-miss spellings, one line each, recorded verbatim.
  run_task $'FACTORY-RESULT status: done' r1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"result-misparse: FACTORY-RESULT status: done"* ]]
  run_task $'FACTORY-RESULT status=succeeded' r2
  [ "$status" -eq 2 ]
  run cat "$root/runs/r2/K1.result"
  [[ "$output" == *"result-misparse: FACTORY-RESULT status=succeeded"* ]]
  run_task $'**FACTORY-RESULT status=done**' r3
  [ "$status" -eq 2 ]
  run cat "$root/runs/r3/K1.result"
  [[ "$output" == *"result-misparse: **FACTORY-RESULT status=done**"* ]]
  run_task $'- FACTORY-RESULT status=done' r4
  [ "$status" -eq 2 ]
  run cat "$root/runs/r4/K1.result"
  [[ "$output" == *"result-misparse: - FACTORY-RESULT status=done"* ]]

  # Accepted forms are recorded as themselves, never re-classified. Mutation:
  # classify by the `FACTORY-RESULT` prefix alone -> `status=done extra=1` is a
  # misparse and `status=partial` leaks a misparse note.
  run_task $'FACTORY-RESULT status=partial\nFACTORY-CHECKS unit=pass\nFACTORY-COMMITS 0\nFACTORY-NOTES partial result' r5
  [ "$status" -eq 1 ]
  run cat "$root/runs/r5/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=partial"* ]]
  [[ "$output" != *"result-misparse"* ]]
  run_task $'FACTORY-RESULT status=done extra=1\nFACTORY-CHECKS unit=pass\nFACTORY-COMMITS 0\nFACTORY-NOTES done with extra' r6
  [ "$status" -eq 0 ]
  run cat "$root/runs/r6/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=done extra=1"* ]]
  [[ "$output" != *"result-misparse"* ]]

  # A template line (with `<`) above a real answer does not re-classify it.
  run_task $'FACTORY-RESULT status=<done|partial|failed>\nFACTORY-RESULT status=done\nFACTORY-CHECKS unit=pass\nFACTORY-COMMITS 0\nFACTORY-NOTES done result' r7
  [ "$status" -eq 0 ]
  run cat "$root/runs/r7/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=done"* ]]
  [[ "$output" != *"result-misparse"* ]]

  # A 300-byte near-miss is truncated to 200 bytes. Mutation: drop the
  # truncation -> the payload stays 300 bytes and the length assertion fails.
  pad=$(printf 'x%.0s' $(seq 1 280))
  run_task "FACTORY-RESULT status=bogus$pad" r8
  [ "$status" -eq 2 ]
  run cat "$root/runs/r8/K1.result"
  notes=$(sed -n 's/^FACTORY-NOTES result-misparse: //p' "$root/runs/r8/K1.result")
  [ "${#notes}" -eq 200 ]
  [[ "$notes" == *"FACTORY-RESULT status=bogus"* ]]
}

@test "factory-brief quotes the exact FACTORY-RESULT grammar in its WORKSPACE RULES summary" {
  # Mutation: delete the grammar sentence -> `no colon, no markdown` vanishes.
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  FACTORY_RUN=r1 FACTORY_MODEL=deepseek/deepseek-v4-pro-0813 \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1
  [ "$status" -eq 0 ]
  [[ "$output" == *"no colon, no markdown"* ]]
}

@test "factory-brief states the grammar in prose before the template, without the literal label" {
  # Mutation: move the sentence back inside the template AND restore the literal
  # "FACTORY-RESULT" label -> the prose sentence then follows the template and
  # its line carries the label, leaving the position and no-label assertions red.
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  FACTORY_RUN=r1 FACTORY_MODEL=deepseek/deepseek-v4-pro-0813 \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1
  [ "$status" -eq 0 ]
  [[ "$output" == *"no colon, no markdown"* ]]
  # The sentence sits in the summary bullet's prose, before the four template
  # lines; the line that carries it must not name the literal label the near-miss
  # classifier scans for (so an echoing seat is not misread as a near miss).
  sentence_line=$(printf '%s\n' "$output" | grep -n 'no colon, no markdown' | cut -d: -f1)
  template_line=$(printf '%s\n' "$output" | grep -n '^FACTORY-RESULT status=<done|partial|failed>$' | cut -d: -f1)
  [ -n "$sentence_line" ]
  [ -n "$template_line" ]
  [ "$sentence_line" -lt "$template_line" ]
  sentence_text=$(printf '%s\n' "$output" | sed -n "${sentence_line}p")
  [[ "$sentence_text" != *"FACTORY-RESULT"* ]]
}

@test "factory-wave makes FACTORY_PLAN absolute once and exports the same value to every task" {
  # Mutation: drop `export FACTORY_PLAN="$plan_abs"` -> the child inherits the
  # raw relative value while run.meta records the absolute path, so the rec
  # reads `plan=plan.md` and the agreement assertion fails.
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\n' "\${pid:-0}"
FAKE
  chmod +x "$bin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$bin/setsid"
  chmod +x "$bin/setsid"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
printf 'plan=%s\n' "\${FACTORY_PLAN:-}" >> "\$REC"
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 0
RESULT
FAKE
  chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; git init -q -b main "$repo"
  root="$BATS_TEST_TMPDIR/factory"
  workdir="$BATS_TEST_TMPDIR/launch"; mkdir -p "$workdir"
  printf '### K1 (code, M) — t\n\nbody.\n' >"$workdir/plan.md"
  rec="$BATS_TEST_TMPDIR/rec"
  # The launch runs with cwd at $workdir so the relative FACTORY_PLAN=plan.md
  # resolves there; the driver must record it absolutely. The driver is run
  # through $REAL_BASH (never exec'd by path: the build sandbox has no
  # /usr/bin/env, so exec'ing its shebang dies 126 — P11b MAJOR-1).
  cd -- "$workdir"
  REC="$rec" PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    FACTORY_PLAN=plan.md \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 0 ]
  meta_plan=$(sed -n 's/^plan: //p' "$root/runs/r1/run.meta")
  [ "$meta_plan" = "$workdir/plan.md" ]
  run cat "$rec"
  [ "$output" = "plan=$workdir/plan.md" ]
}

@test "factory-task refuses a mode-000 (unreadable) FACTORY_PLAN before any workspace or run dir exists" {
  # Mutation: factory_need_file back to `[ -f ]` -> a chmod-000 plan is still a
  # regular file, so the guard passes and the run proceeds, leaving the exit and
  # no-run-dir assertions red.
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  plan000="$BATS_TEST_TMPDIR/plan000.md"
  printf '### K1 (code, M) — t\n\nbody.\n' >"$plan000"
  chmod 000 "$plan000"
  root="$BATS_TEST_TMPDIR/factory"
  FACTORY_ROOT="$root" FACTORY_PLAN="$plan000" \
    run "$REAL_BASH" "$SEAT/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  [[ "$output" == *"no such file"* ]]
  [ ! -e "$root/runs/r1" ]
  [ ! -e "$root/ws" ]
  chmod 644 "$plan000"
}

@test "factory-task records an echoing seat that copies the brief as no-usable-line, not a near miss" {
  # Mutation: put the grammar sentence back inside the template AND restore the
  # literal "FACTORY-RESULT" label -> the copied brief then carries a
  # FACTORY-RESULT line with no '<', so it is read as a near miss and the notes
  # become `result-misparse: ...`, failing the honest-note assertions.
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  # A naive seat that echoes the composed brief back verbatim instead of doing
  # the work: `dsh-openrouter --model M --headless <brief>` -> the brief is $4.
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf '%s\n' "\$4"
FAKE
  chmod +x "$bin/dsh-openrouter"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"the seat produced no usable FACTORY-RESULT line"* ]]
  [[ "$output" != *"result-misparse"* ]]
}

@test "factory-integrate counts a refused key in refused: only, never in conflicts:" {
  # Mutation: `conflicts = (#keys - #merged)` -> K1's refusal also inflates
  # conflicts to 1, leaving `conflicts: 0` red.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  mkdir -p "$src/docs"
  printf 'prologue\n<!-- tasks:begin -->\nqueue\n<!-- tasks:end -->\nepilogue\n' >"$src/docs/OPERATIONS.md"
  git -C "$src" add docs/OPERATIONS.md
  git -C "$src" commit -q -m "init"
  git clone -q "$src" "$root/base/src"
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  printf 'intruder\n' >>"$root/ws/r1/K1/docs/OPERATIONS.md"
  git -C "$root/ws/r1/K1" add docs/OPERATIONS.md
  git -C "$root/ws/r1/K1" commit -q -m "k1: board prose (test: unit)"
  git clone -q "$src" "$root/ws/r1/K2"
  git -C "$root/ws/r1/K2" config user.name t
  git -C "$root/ws/r1/K2" config user.email t@x
  git -C "$root/ws/r1/K2" checkout -q -b task/K2
  printf 'y\n' >"$root/ws/r1/K2/y"
  git -C "$root/ws/r1/K2" add y
  git -C "$root/ws/r1/K2" commit -q -m "k2: add y (test: unit)"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1 K2
  [ "$status" -eq 1 ]
  [[ "$output" == *"REFUSED K1"* ]]
  [[ "$output" == *"refused: 1"* ]]
  [[ "$output" == *"conflicts: 0"* ]]
}

@test "factory-integrate still prints refused: N when every key is refused" {
  # Mutation: restore the early exit without a refused: line -> the summary
  # lacks `refused: 1` and the assertion fails.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  mkdir -p "$src/docs"
  printf 'prologue\n<!-- tasks:begin -->\nqueue\n<!-- tasks:end -->\nepilogue\n' >"$src/docs/OPERATIONS.md"
  git -C "$src" add docs/OPERATIONS.md
  git -C "$src" commit -q -m "init"
  git clone -q "$src" "$root/base/src"
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  printf 'intruder\n' >>"$root/ws/r1/K1/docs/OPERATIONS.md"
  git -C "$root/ws/r1/K1" add docs/OPERATIONS.md
  git -C "$root/ws/r1/K1" commit -q -m "k1: board prose (test: unit)"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 1 ]
  [[ "$output" == *"REFUSED K1"* ]]
  [[ "$output" == *"refused: 1"* ]]
}

@test "factory-integrate refuses a key with no merge base, never silently merging it" {
  # Mutation: restore `[ -n "$mb" ] && <guard>` -> an unrelated-history branch
  # skips the board guard and is merged, leaving `REFUSED K1` red.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  printf 'x\n' >"$src/f"; git -C "$src" add f; git -C "$src" commit -q -m init
  git clone -q "$src" "$root/base/src"
  # K1 is an unrelated history (its own init), so it shares no merge base with
  # origin/main.
  mkdir -p "$root/ws/r1/K1"
  git init -q "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  printf 'u\n' >"$root/ws/r1/K1/u"
  git -C "$root/ws/r1/K1" add u
  git -C "$root/ws/r1/K1" commit -q -m "unrelated"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 1 ]
  [[ "$output" == *"REFUSED K1"* ]]
  [[ "$output" == *"no merge base"* ]]
  [[ "$output" == *"refused: 1"* ]]
}

@test "factory-task folds a control byte in a near miss and refuses the status:done spelling" {
  # Two unpinned clauses (P11 review MINOR-6/7): (a) `tr '[:cntrl:]' ' '`
  # dropped -> the tab and ESC survive verbatim, failing the folded assertion;
  # (b) ACCEPTED loosened to `status[:=]` -> `FACTORY-RESULT status:done`
  # (colon, no space) is accepted as done instead of a near miss.
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf '%b\n' "\${PAYLOAD}"
FAKE
  chmod +x "$bin/dsh-openrouter"
  run_task() {
    PAYLOAD="$1" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
      FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
      OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
      run "$REAL_BASH" "$seat_copy/factory-task" "$2" "$repo" K1
  }

  # status:done (colon, no space) is a near miss, never accepted as done.
  run_task $'FACTORY-RESULT status:done' r1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=failed"* ]]
  [[ "$output" == *"result-misparse: FACTORY-RESULT status:done"* ]]

  # A tab and an ESC byte in a near miss are folded to spaces in the note.
  run_task $'FACTORY-RESULT status=bogus\tand\x1b[31mred\x1b[0m tail' r2
  [ "$status" -eq 2 ]
  run cat "$root/runs/r2/K1.result"
  [[ "$output" == *"result-misparse: FACTORY-RESULT status=bogus and [31mred [0m tail"* ]]
  [[ "$output" != *$'\t'* ]]
}

@test "no bats test launches a driver through its own shebang" {
  # P11b MAJOR-1: one test invoked the driver through its own path (as the
  # command, via bash's exec builtin) instead of as an argument to an
  # interpreter, so the kernel read the driver's #!/usr/bin/env bash shebang
  # and the build sandbox -- which has no /usr/bin/env -- died 126 before the
  # driver body ran. Every launch must hand an interpreter, as the other tests
  # do. Two greps enforce it structurally: (a) no line may exec a quoted word
  # (a driver path run directly), and (b) no line may use a SEAT-path as the
  # command word rather than as the interpreter's argument. Mutation: revert
  # the absolute-plan test to exec its driver-path argument as the command ->
  # grep (a) finds the exec and this test fails, leaving unit red.
  driver_bats="$BATS_TEST_DIRNAME/80-seat-driver.bats"
  ritual_bats="$BATS_TEST_DIRNAME/92-ritual.bats"
  run grep -nE 'exec[[:space:]]*"' "$driver_bats" "$ritual_bats"
  [ "$status" -eq 1 ]
  run grep -nE '(run|exec)[[:space:]]+"\$SEAT/' "$driver_bats" "$ritual_bats"
  [ "$status" -eq 1 ]
}

@test "factory-integrate counts a skipped key in skipped: and exits non-zero without printing the fast-forward recipe" {
  # Mutation: drop the skip from the exit code -> a run that dropped a key exits
  # 0 (red); and drop the recipe gate -> the fast-forward line prints even
  # though NOPE was skipped (red).
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  printf 'x\n' >"$src/f"; git -C "$src" add f; git -C "$src" commit -q -m init
  git clone -q "$src" "$root/base/src"
  # K2 exists and merges; NOPE has no workspace dir, so it is skipped.
  git clone -q "$src" "$root/ws/r1/K2"
  git -C "$root/ws/r1/K2" config user.name t
  git -C "$root/ws/r1/K2" config user.email t@x
  git -C "$root/ws/r1/K2" checkout -q -b task/K2
  printf 'y\n' >"$root/ws/r1/K2/y"
  git -C "$root/ws/r1/K2" add y
  git -C "$root/ws/r1/K2" commit -q -m "k2: add y (test: unit)"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" NOPE K2
  [ "$status" -eq 1 ]
  [[ "$output" == *"SKIP NOPE"* ]]
  [[ "$output" == *"skipped: 1"* ]]
  [[ "$output" == *"MERGE K2 ok"* ]]
  [[ "$output" != *"pull --ff-only"* ]]
}

@test "the fast-forward recipe prints when every key merged" {
  # Mutation: gate the recipe the wrong way -> a clean single-key merge loses the
  # fast-forward line (red), or a skipped key gains it (the previous test's).
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  printf 'x\n' >"$src/f"; git -C "$src" add f; git -C "$src" commit -q -m init
  git clone -q "$src" "$root/base/src"
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  printf 'y\n' >"$root/ws/r1/K1/y"
  git -C "$root/ws/r1/K1" add y
  git -C "$root/ws/r1/K1" commit -q -m "k1: add y (test: unit)"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 0 ]
  [[ "$output" == *"pull --ff-only"* ]]
}

@test "a symlinked FACTORY_PLAN is recorded by its real path, basename included" {
  # Mutation: factory_abs_plan resolves only the directory (cd -P dirname plus
  # the basename as given) -> the symlinked basename survives, so run.meta
  # records .../link.md and the equality assertion fails.
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\n' "\${pid:-0}"
FAKE
  chmod +x "$bin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$bin/setsid"
  chmod +x "$bin/setsid"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 0
RESULT
FAKE
  chmod +x "$fact/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; git init -q -b main "$repo"
  root="$BATS_TEST_TMPDIR/factory"
  real="$BATS_TEST_TMPDIR/real"; mkdir -p "$real"
  printf '### K1 (code, M) — t\n\nbody.\n' >"$real/p.md"
  ln -s "$real/p.md" "$BATS_TEST_TMPDIR/link.md"
  PATH="$bin:$PATH" FACTORY_ROOT="$root" FACTORY_BIN_OVERRIDE="$fact" \
    FACTORY_PLAN="$BATS_TEST_TMPDIR/link.md" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 0 ]
  meta_plan=$(sed -n 's/^plan: //p' "$root/runs/r1/run.meta")
  [ "$meta_plan" = "$real/p.md" ]
}

@test "factory-task absolutises its own FACTORY_PLAN through realpath before composing the brief" {
  # Mutation: factory-task keeps plan=$FACTORY_PLAN as given -> factory-brief
  # receives the symlink path, so the rec reads .../link.md and the equality
  # assertion fails.
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  cat >"$seat_copy/factory-brief" <<FAKE
#!$REAL_BASH
printf '%s\n' "\$1" >"\$BRIEF_REC"
FAKE
  chmod +x "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  real="$BATS_TEST_TMPDIR/real"; mkdir -p "$real"
  printf '### K1 (code, M) — t\n\nbody one.\n' >"$real/p.md"
  ln -s "$real/p.md" "$BATS_TEST_TMPDIR/link.md"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'FACTORY-RESULT status=done\nFACTORY-CHECKS unit=pass\nFACTORY-COMMITS 1\nFACTORY-NOTES ok\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  brief_rec="$BATS_TEST_TMPDIR/brief.rec"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$BATS_TEST_TMPDIR/link.md" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= BRIEF_REC="$brief_rec" \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  run cat "$brief_rec"
  [ "$output" = "$real/p.md" ]
}

@test "route.py and factory_route accept the plan role and refuse the planner role" {
  # The plan role (P8) is a new recognized word in BOTH enumerations. Mutant:
  # add "plan" to only one of the two lists -- route.py's ROLES tuple or
  # factory_route's case arm -- and the fixture with a plan row passes one
  # check while the other still refuses it (one of the two exit-0 asserts
  # below goes red).
  route_py="$SEAT/../route.py"
  withplan="$BATS_TEST_TMPDIR/with-plan.toml"
  cat >"$withplan" <<'EOF'
[[route]]
route = "openrouter"
role = "plan"
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$withplan'"
  [ "$status" -eq 0 ]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$withplan' check"
  [ "$status" -eq 0 ]

  # "planner" is not a role word: both lookups must refuse it, each naming its
  # own row and word.
  planner="$BATS_TEST_TMPDIR/planner.toml"
  cat >"$planner" <<'EOF'
[[route]]
route = "openrouter"
role = "planner"
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$planner'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"unknown role"* ]]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$planner' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"unknown role 'planner'"* ]]
}

@test "role plan resolves to the openrouter default row, not a typed plan row" {
  # No plan row exists in the committed table (design §6.2: a row lands only
  # once a commit cites the measurement plan's report), so a plan lookup must
  # fall through to the default (any/any/any) row. Mutant: write a plan row
  # into docs/ledger/routing.toml and this assert changes to that row's model
  # -- which is the whole point: the lookup is the default by design, not a
  # typed row.
  table="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
  [ -f "$table" ] || skip "docs/ledger/routing.toml not copied into the unit-check sandbox"
  route_py="$SEAT/../route.py"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route openrouter plan docs S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-pro-0813 medium" ]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter plan docs S"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-pro-0813 medium" ]
}

@test "factory-plan sizes the spec, routes plan/docs, and hands the brief and seat-plan to factory-task" {
  # The end-to-end drafting seat. Mutants, each turning exactly one assert red:
  # drop the FACTORY_PLAN export -> the recorder shows the variable unset;
  # keep the / in the model name -> the draft becomes a subdirectory path.
  # The size S/M/L rule itself is pinned separately (its one home is
  # factory_plan_size), so this test only proves factory-plan hands everything
  # through unchanged.
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger" "$fx/docs/superpowers/specs"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  # <spec> is resolved relative to FACTORY_TOOLBOX_REPO, exactly as
  # factory-plan-brief resolves it, so a repo-relative path (not an absolute
  # one) is what factory-plan reads and hands through.
  printf 'one two three\n' >"$fx/docs/superpowers/specs/spec-s.md"
  printf 'word %.0s' $(seq 1501) >"$fx/docs/superpowers/specs/spec-m.md"
  spec_s="docs/superpowers/specs/spec-s.md"
  spec_m="docs/superpowers/specs/spec-m.md"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  rec_brief="$BATS_TEST_TMPDIR/rec-brief"; rec_task="$BATS_TEST_TMPDIR/rec-task"
  cat >"$bin/factory-plan-brief" <<FAKE
#!$REAL_BASH
printf 'brief-out=%s\n' "\$2" >> "\$REC_BRIEF"
printf 'BRIEF\n'
FAKE
  chmod +x "$bin/factory-plan-brief"
  cat >"$bin/factory-task" <<FAKE
#!$REAL_BASH
printf 'task-key=%s\n' "\$3" >> "\$REC_TASK"
prev=; model=
for a in "\$@"; do
  if [ "\$prev" = "--model" ]; then model="\$a"; fi
  prev="\$a"
done
printf 'task-model=%s\n' "\$model" >> "\$REC_TASK"
printf 'task-effort=%s\n' "\${OPENROUTER_REASONING_EFFORT:-}" >> "\$REC_TASK"
printf 'task-text=%s\n' "\$FACTORY_TASK_TEXT" >> "\$REC_TASK"
printf 'task-plan=%s\n' "\$FACTORY_PLAN" >> "\$REC_TASK"
exit 0
FAKE
  chmod +x "$bin/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"

  # S spec: the default model/effort (no plan row), the packet as task text,
  # and seat-plan.md as the plan.
  REC_BRIEF="$rec_brief" REC_TASK="$rec_task" FACTORY_BIN_OVERRIDE="$bin" \
    FACTORY_PLAN_BRIEF="$bin/factory-plan-brief" FACTORY_TOOLBOX_REPO="$fx" \
    run "$REAL_BASH" "$SEAT/factory-plan.sh" r1 "$repo" "$spec_s" helm-home-1
  [ "$status" -eq 0 ]
  run cat "$rec_task"
  [[ "$output" == *"task-key=PLAN-helm-home-1"* ]]
  [[ "$output" == *"task-model=deepseek/deepseek-v4-pro-0813"* ]]
  [[ "$output" == *"task-effort=medium"* ]]
  [[ "$output" == *"task-text=BRIEF"* ]]
  [[ "$output" == *"task-plan=$fx/tools/factory/plan/seat-plan.md"* ]]
  run cat "$rec_brief"
  out=$(sed -n 's/^brief-out=//p' "$rec_brief")
  [[ "$out" =~ ^docs/reviews/plan-drafts/[0-9]{4}-[0-9]{2}-[0-9]{2}-helm-home-1-deepseek-deepseek-v4-pro-0813\.md$ ]]

  # 1501 words -> M (routed the same default today, so the run just has to
  # reach factory-task unchanged).
  rm -f "$rec_brief" "$rec_task"
  REC_BRIEF="$rec_brief" REC_TASK="$rec_task" FACTORY_BIN_OVERRIDE="$bin" \
    FACTORY_PLAN_BRIEF="$bin/factory-plan-brief" FACTORY_TOOLBOX_REPO="$fx" \
    run "$REAL_BASH" "$SEAT/factory-plan.sh" r2 "$repo" "$spec_m" helm-home-1
  [ "$status" -eq 0 ]
  run cat "$rec_task"
  [[ "$output" == *"task-key=PLAN-helm-home-1"* ]]
}

@test "factory-plan refuses an L spec or a refusing brief before the drafting seat runs" {
  # Three refusals, each exit 2 with the recorder never reaching factory-task.
  # Mutants: route an L spec anyway -> the brief and task run (exit 0, the
  # recorder file appears); ignore the brief's exit -> same; pass the brief's
  # exit through unchanged -> a brief exiting 3 leaves this script exiting 3
  # instead of 2. All are pinned by the exit-2 asserts and [ ! -e "$rec_task" ].
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger" "$fx/docs/superpowers/specs"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  printf 'word %.0s' $(seq 4001) >"$fx/docs/superpowers/specs/spec-l.md"
  printf 'one two three\n' >"$fx/docs/superpowers/specs/spec-s.md"
  spec_l="docs/superpowers/specs/spec-l.md"
  spec_s="docs/superpowers/specs/spec-s.md"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  rec_task="$BATS_TEST_TMPDIR/rec-task"
  cat >"$bin/factory-plan-brief" <<FAKE
#!$REAL_BASH
printf 'BRIEF\n'
FAKE
  chmod +x "$bin/factory-plan-brief"
  cat >"$bin/factory-plan-brief-fail" <<FAKE
#!$REAL_BASH
printf 'factory-plan-brief: refusing -- the graph is not sound\n' >&2
exit 2
FAKE
  chmod +x "$bin/factory-plan-brief-fail"
  cat >"$bin/factory-plan-brief-fail3" <<FAKE
#!$REAL_BASH
printf 'factory-plan-brief: part M3 failed mid-packet\n' >&2
exit 3
FAKE
  chmod +x "$bin/factory-plan-brief-fail3"
  cat >"$bin/factory-task" <<FAKE
#!$REAL_BASH
printf 'ran\n' >> "\$REC_TASK"
exit 0
FAKE
  chmod +x "$bin/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"

  # 4001 words -> L -> refuse before the brief or the seat is reached.
  REC_TASK="$rec_task" FACTORY_BIN_OVERRIDE="$bin" FACTORY_TOOLBOX_REPO="$fx" \
    FACTORY_PLAN_BRIEF="$bin/factory-plan-brief" \
    run "$REAL_BASH" "$SEAT/factory-plan.sh" r1 "$repo" "$spec_l" helm-home-1
  [ "$status" -eq 2 ]
  [[ "$output" == *"an L spec is split before a plan is written"* ]]
  [ ! -e "$rec_task" ]

  # A brief that refuses (unsound graph) is propagated as exit 2, never ignored.
  rm -f "$rec_task"
  REC_TASK="$rec_task" FACTORY_BIN_OVERRIDE="$bin" FACTORY_TOOLBOX_REPO="$fx" \
    FACTORY_PLAN_BRIEF="$bin/factory-plan-brief-fail" \
    run "$REAL_BASH" "$SEAT/factory-plan.sh" r2 "$repo" "$spec_s" helm-home-1
  [ "$status" -eq 2 ]
  [[ "$output" == *"the graph is not sound"* ]]
  [ ! -e "$rec_task" ]

  # Every brief failure is exit 2 -- a brief that exits 3 (a mid-packet part
  # failed) is still this script's exit 2, not 3 (3 stays reserved here for a
  # routing-table failure).
  rm -f "$rec_task"
  REC_TASK="$rec_task" FACTORY_BIN_OVERRIDE="$bin" FACTORY_TOOLBOX_REPO="$fx" \
    FACTORY_PLAN_BRIEF="$bin/factory-plan-brief-fail3" \
    run "$REAL_BASH" "$SEAT/factory-plan.sh" r3 "$repo" "$spec_s" helm-home-1
  [ "$status" -eq 2 ]
  [[ "$output" == *"part M3 failed"* ]]
  [ ! -e "$rec_task" ]
}

@test "factory_plan_size pins the size boundaries: 1500→S, 1501→M, 4000→M, 4001→L" {
  # The S/M/L word-count rule has ONE home now (factory_plan_size in
  # factory-lib.sh, called by both factory-plan and factory-plan-brief).
  # Mutants: -le 1500 -> -lt 1500 turns a 1500-word spec M (red at the first
  # assert); -le 4000 -> -lt 4000 turns a 4000-word spec L (red at the third).
  printf 'word %.0s' $(seq 1500) >"$BATS_TEST_TMPDIR/s1500"
  printf 'word %.0s' $(seq 1501) >"$BATS_TEST_TMPDIR/s1501"
  printf 'word %.0s' $(seq 4000) >"$BATS_TEST_TMPDIR/s4000"
  printf 'word %.0s' $(seq 4001) >"$BATS_TEST_TMPDIR/s4001"
  lib="$SEAT/factory-lib.sh"
  run "$REAL_BASH" -c ". '$lib'; factory_plan_size '$BATS_TEST_TMPDIR/s1500'"
  [ "$status" -eq 0 ]
  [ "$output" = "S" ]
  run "$REAL_BASH" -c ". '$lib'; factory_plan_size '$BATS_TEST_TMPDIR/s1501'"
  [ "$status" -eq 0 ]
  [ "$output" = "M" ]
  run "$REAL_BASH" -c ". '$lib'; factory_plan_size '$BATS_TEST_TMPDIR/s4000'"
  [ "$status" -eq 0 ]
  [ "$output" = "M" ]
  run "$REAL_BASH" -c ". '$lib'; factory_plan_size '$BATS_TEST_TMPDIR/s4001'"
  [ "$status" -eq 0 ]
  [ "$output" = "L" ]
}

@test "factory-plan rejects a name that is not ^[a-z0-9][a-z0-9-]{0,63}$ before composing" {
  # <name> becomes the branch ref task/PLAN-<name> and part of the draft path,
  # so it must be one safe path component. Mutants: drop the validation -> the
  # `a/b` name yields a subdirectory draft path and task/PLAN-a/b, and the
  # empty name yields PLAN- alone, both of which reach the seat (exit 0)
  # instead of this exit-2 refusal.
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  rec_task="$BATS_TEST_TMPDIR/rec-task"
  cat >"$bin/factory-task" <<FAKE
#!$REAL_BASH
printf 'ran\n' >> "\$REC_TASK"
exit 0
FAKE
  chmod +x "$bin/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  spec="$BATS_TEST_TMPDIR/spec.md"; printf 'one two three\n' >"$spec"

  REC_TASK="$rec_task" FACTORY_BIN_OVERRIDE="$bin" \
    run "$REAL_BASH" "$SEAT/factory-plan.sh" r1 "$repo" "$spec" "a/b"
  [ "$status" -eq 2 ]
  [[ "$output" == *"bad name"* ]]
  [ ! -e "$rec_task" ]

  REC_TASK="$rec_task" FACTORY_BIN_OVERRIDE="$bin" \
    run "$REAL_BASH" "$SEAT/factory-plan.sh" r1 "$repo" "$spec" ""
  [ "$status" -eq 2 ]
  [[ "$output" == *"bad name"* ]]
  [ ! -e "$rec_task" ]
}

@test "factory-plan refuses a missing or unreadable spec with exit 2 before routing" {
  # The [ -r ] guard is pinned: it must refuse a missing and an unreadable spec
  # as exit 2 before factory_route (whose failure is the reserved exit 3) or
  # any brief/seat runs. Mutant: [ -r ] -> true -> the missing spec reaches
  # wc/factory_route and dies some other way, breaking these exit-2 asserts.
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger" "$fx/docs/superpowers/specs"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  printf 'one two three\n' >"$fx/docs/superpowers/specs/spec000.md"
  chmod 000 "$fx/docs/superpowers/specs/spec000.md"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  rec_task="$BATS_TEST_TMPDIR/rec-task"
  cat >"$bin/factory-task" <<FAKE
#!$REAL_BASH
printf 'ran\n' >> "\$REC_TASK"
exit 0
FAKE
  chmod +x "$bin/factory-task"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"

  # Unreadable (mode 000): refused before routing, exit 2.
  REC_TASK="$rec_task" FACTORY_BIN_OVERRIDE="$bin" FACTORY_TOOLBOX_REPO="$fx" \
    run "$REAL_BASH" "$SEAT/factory-plan.sh" r1 "$repo" \
      "docs/superpowers/specs/spec000.md" helm-home-1
  [ "$status" -eq 2 ]
  [[ "$output" == *"no such spec:"* ]]
  [ ! -e "$rec_task" ]
  chmod 644 "$fx/docs/superpowers/specs/spec000.md"

  # Missing: refused before routing, exit 2.
  REC_TASK="$rec_task" FACTORY_BIN_OVERRIDE="$bin" FACTORY_TOOLBOX_REPO="$fx" \
    run "$REAL_BASH" "$SEAT/factory-plan.sh" r1 "$repo" \
      "docs/superpowers/specs/missing.md" helm-home-1
  [ "$status" -eq 2 ]
  [[ "$output" == *"no such spec:"* ]]
  [ ! -e "$rec_task" ]
}

@test "seat-plan.md carries the seat constraints and no typed task heading" {
  # The drafting seat's plan file is read only by factory-brief for its
  # ## Global Constraints and ## Assumptions; it must never carry a typed
  # `### KEY (kind, size)` heading or the graph's HEADING_RE would see a task.
  # Mutant: type such a heading into it -> the last assert goes red.
  # The copy list of checks.unit carries tools/factory/plan, so this runs in
  # the acceptance check -- never skips (a skip here would be the MAJOR-1
  # vacuity where the gate passes with a typed heading in the file).
  f="$BATS_TEST_DIRNAME/../../tools/factory/plan/seat-plan.md"
  [ -f "$f" ]
  run grep -c '^## Global Constraints$' "$f"
  [ "$output" = "1" ]
  run grep -c '^## Assumptions$' "$f"
  [ "$output" = "1" ]
  run grep -cE '^### [A-Za-z][A-Za-z0-9-]* \((code|docs), (XS|S|M|L)\)' "$f"
  [ "$output" = "0" ]
}
