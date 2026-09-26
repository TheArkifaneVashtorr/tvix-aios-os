#!/usr/bin/env bats
# PL16: the direct arm's gh guard. factory-task's FACTORY_SEAT_UNIT=0 arm
# launches dsh-openrouter in a plain subshell that inherits the operator's
# whole ambient environment -- the one place an ambient GH_TOKEN/GITHUB_TOKEN
# would leak straight through, and the one place gh's default config lookup
# would resolve the operator's real ~/.config/gh/hosts.yml. The guard: the
# launch strips both token variables (env -u) and pins GH_CONFIG_DIR at a
# fresh, empty directory, so gh inside the launched seat can discover no
# credential the operator holds. This file proves the strip by dumping the
# whole child environment from a fake dsh-openrouter and asserting on it --
# red against the unguarded launch (both tokens verbatim in the dump, no
# GH_CONFIG_DIR line), green after the guard.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
EV="$BATS_TEST_DIRNAME/../../pkgs/evidence"

@test "factory-task direct arm strips GH_TOKEN/GITHUB_TOKEN and pins GH_CONFIG_DIR at an empty dir" {
  REAL_BASH="$(command -v bash)"
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  # The copied scripts keep their `#!/usr/bin/env bash` shebang, which the
  # build sandbox has no /usr/bin/env to honour; factory-task invokes
  # factory-brief by that shebang, so repoint it to the sandbox bash.
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  # factory-ws prints a workspace path and succeeds, so factory-task runs to
  # completion through the direct arm.
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  # The toolbox holds the routing table (one default row) and the task-classes
  # rules, the same fixture shape 85-task-class.bats uses for the direct arm.
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger" "$fx/pkgs/evidence"
  cp "$EV"/*.py "$fx/pkgs/evidence/"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  cat >"$fx/docs/ledger/task-classes.toml" <<'EOF'
[[rule]]
class = "bats-test"
glob = "tests/unit/*"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

**touches:** tests/unit/x.bats
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  # A fake dsh-openrouter dumps its whole environment, then reports a clean
  # result so factory-task exits 0 and the dump is complete.
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
env > "\$REC"
printf 'FACTORY-RESULT status=done\n'
printf 'FACTORY-CHECKS unit=pass\n'
printf 'FACTORY-COMMITS 1\n'
printf 'FACTORY-NOTES ok\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  rec="$BATS_TEST_TMPDIR/env-dump"

  # Both token variables sit in the calling shell's environment: the launch
  # must strip them, not inherit them (the PL16 red run shows the unguarded
  # launch passing both through verbatim).
  REC="$rec" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= FACTORY_SEAT_UNIT=0 \
    GH_TOKEN=leaked-gh-token GITHUB_TOKEN=leaked-github-token \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  [ -s "$rec" ]

  # Neither token may reach the launched seat's environment.
  run grep -c '^GH_TOKEN=' "$rec"
  [ "$output" = "0" ]
  run grep -c '^GITHUB_TOKEN=' "$rec"
  [ "$output" = "0" ]

  # GH_CONFIG_DIR must point at an existing, empty directory (a root-owned
  # fresh dir in production, the unit arm's tmpfiles equivalent): gh resolves
  # no hosts.yml through it.
  gh_dir=$(sed -n 's/^GH_CONFIG_DIR=//p' "$rec")
  [ -n "$gh_dir" ]
  [ -d "$gh_dir" ]
  [ -z "$(ls -A "$gh_dir")" ]
}
