#!/usr/bin/env bash
# zcode-hooks.sh -- the ZCode adapter for this repo's Claude Code hooks.
# ZCode's hook contract differs from Claude Code's in two ways that matter:
# stdout is parsed as strict JSON (plain text is discarded) and a deny or
# block comes from exit code 2, not from a decision object. Three
# subcommands wrap the three wired events (.zcode/config.json mirrors
# .claude/settings.json):
#
#   session-start [repo]  tools/session-start.sh's plain-text brief as one
#                         {"additionalContext":"..."} object. The JSON string
#                         escaping is bash-only (backslash, quote, newline,
#                         tab, CR -- every control byte that markdown output
#                         can contain); any failure prints nothing and exits
#                         0, and AGENTS.md names the by-hand fallback.
#   guard                 tools/orchestrator-guard.sh's deny decision
#                         translated to exit 2 with the reason on stderr;
#                         allows and the guard's own stderr pass untouched.
#                         The guard's fail-closed EXIT trap prints a deny
#                         decision on its own faults, so a faulting guard
#                         still denies through here.
#   stop [repo]           tools/ritual.sh stop's {"decision":"block",...}
#                         translated to exit 2 (ZCode reads that as a request
#                         to continue, capped at three -- under the ritual's
#                         own RITUAL_MAX_BLOCKS of two).
set -u
self_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo=${2:-$(cd -- "$self_dir/.." && pwd -P)}
payload=$(cat 2>/dev/null)

case ${1:-} in
  session-start)
    out=$(printf '%s' "$payload" | bash "$self_dir/session-start.sh" "$repo") || exit 0
    [ -n "$out" ] || exit 0
    esc=${out//\\/\\\\}
    esc=${esc//\"/\\\"}
    esc=${esc//$'\n'/\\n}
    esc=${esc//$'\t'/\\t}
    esc=${esc//$'\r'/\\r}
    printf '{"additionalContext":"%s"}\n' "$esc"
    ;;
  guard)
    out=$(printf '%s' "$payload" | bash "$self_dir/orchestrator-guard.sh")
    case "$out" in
      *'"permissionDecision":"deny"'*)
        reason=$(printf '%s' "$out" | sed -n 's/.*"permissionDecisionReason":"\([^"]*\)".*/\1/p')
        printf 'orchestrator-guard (zcode): %s\n' "${reason:-refused}" >&2
        exit 2
        ;;
    esac
    ;;
  stop)
    out=$(printf '%s' "$payload" | bash "$self_dir/ritual.sh" stop "$repo")
    case "$out" in
      *'"decision":"block"'*)
        reason=$(printf '%s' "$out" | sed -n 's/.*"reason":"\([^"]*\)".*/\1/p')
        printf 'ritual (zcode): %s\n' "${reason:-blocked}" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    printf 'usage: zcode-hooks.sh session-start [repo] | guard | stop [repo]\n' >&2
    exit 1
    ;;
esac
exit 0
