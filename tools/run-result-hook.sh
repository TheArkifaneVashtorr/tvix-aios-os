#!/usr/bin/env bash
# run-result-hook.sh -- a UserPromptSubmit hook (.claude/settings.json).
#
# In the desktop app every bash-tagged block the orchestrator prints gets a Run
# button, and each run's output comes back as a prompt that begins with
# `<bash-input>`. When the orchestrator answered such a result by re-listing
# the blocks it had already given, the operator pressed them again (2026-09-21:
# two `gh pr close` commands ran three times each). This hook injects the rule
# as additionalContext on exactly those prompts and stays silent otherwise.
#
# Hooks run outside the devShell (no jq): the prompt field is matched on the
# raw stdin JSON with bash alone. Exit 0 always; empty output means no context.
set -u

input=$(cat 2>/dev/null || true)
[ -n "$input" ] || exit 0

# The prompt field, at any nesting, whose value starts with the Run-button tag.
# JSON leaves `<` unescaped, so the literal sequence is stable.
if [[ $input =~ \"prompt\"[[:space:]]*:[[:space:]]*\"\<bash-input\> ]]; then
  cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "This prompt is a Run-button result: the operator pressed a command block you printed earlier, and its output came back. Reply with what that result means and nothing more, and never repeat a command block already given in this conversation; print the NEXT block only if it has not been printed yet; if the result says the step is already done, say so in one line and print no block. One command per message, or one combined block, is the rule (memory: run-button-commands)."
  }
}
JSON
fi
exit 0
