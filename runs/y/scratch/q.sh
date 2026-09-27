#!/usr/bin/env bash
# q.sh: run one command, print its output, append the command and exit code to queries.log
cmd="$1"
cd /home/user/tvix-aios-os || exit 99
bash -c "$cmd" 2>&1
rc=$?
printf '%s\t;; exit %d\n' "$cmd" "$rc" >> /tmp/draft-scratch/queries.log
exit $rc
