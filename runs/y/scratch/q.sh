#!/usr/bin/env bash
# q.sh: run a command, append "<cmd>\texit <code>" to queries.log, echo output.
cmd="$*"
out=$(bash -c "$cmd" 2>&1); rc=$?
printf '%s\t%s\texit %d\n' "$(date -u +%FT%TZ)" "$cmd" "$rc" >> /tmp/draft-scratch/queries.log
printf '%s\n' "$out"
printf '[exit %d]\n' "$rc"
