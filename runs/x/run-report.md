# run x — draft-packet on fx/F1

## Outcome: STOPPED at step 1

Step 1's check failed: `evidence bundle --markdown` exited 2 (it must exit 0).
Error, verbatim:

```
python3: can't open file '/usr/pkgs/evidence/evidence.py': [Errno 2] No such file or directory
bundle exit 2
```

So steps 3–5 were not run. The `draft-packet` workflow was **not** invoked: no run ID,
no journal, no usage block, no scratch output.

## Step 0

```
$ git fetch origin fx/F1
From https://github.com/TheArkifaneVashtorr/tvix-aios-os
 * branch            fx/F1      -> FETCH_HEAD
$ git checkout -B fx/F1 origin/fx/F1
Reset branch 'fx/F1'
branch 'fx/F1' set up to track 'origin/fx/F1'.
Your branch is up to date with 'origin/fx/F1'.
$ git log -1 --format=%H
4a7374ca4842568fdc7f45caac02b503bfb80c35
$ git status --short
(no output)
```

Result: PASS (commit starts with 4a7374c, tree clean).

## Step 1

```
$ pwd -P
/home/user/tvix-aios-os
$ command -v nix; readlink -f "$(command -v nix)"
/usr/local/bin/nix
/home/user/tvix-aios-os/tools/cloud/nix
$ command -v evidence; readlink -f "$(command -v evidence)"
/usr/local/bin/evidence
/home/user/tvix-aios-os/tools/cloud/evidence
$ readlink -f /home/dalhaka/nixos-agent-env
/home/user/tvix-aios-os
$ echo "HOME=$HOME"; readlink -f ~/nixos-agent-env
HOME=/root
/home/user/tvix-aios-os
$ readlink -f /var/lib/evidence
/home/user/tvix-aios-os/evidence
$ python3 -c "import duckdb; print(duckdb.__version__)"
1.5.5
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check; echo "check exit $?"
check exit 0
$ evidence bundle --markdown > /dev/null; echo "bundle exit $?"
python3: can't open file '/usr/pkgs/evidence/evidence.py': [Errno 2] No such file or directory
bundle exit 2
```

Result: FAIL — all path requirements and `check exit 0` hold, duckdb 1.5.5 present,
but `bundle exit 2`. The `evidence` wrapper resolves `evidence.py` relative to
`/usr` (apparently from the `/usr/local/bin` symlink location) instead of the
checkout, i.e. `/usr/pkgs/evidence/evidence.py`. Not investigated further or
worked around, per instructions.

## Environment (step 2 items)

- `claude --version`: `2.1.283 (Claude Code)`
- Model: session configured model `claude-opus-5-5`; `get_session` reports
  `session_context.model` = `claude-opus-5-5`, `last_served_model` = `claude-opus-5-5`
- `echo "$CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"`: `80`
- `nproc`: `4`
- `free -g`:

```
               total        used        free      shared  buff/cache   available
Mem:              15           0          14           0           0          15
Swap:              0           0           0
```

- Start time: `2026-09-27T00:40:45Z` (taken right after step 1 failed; step 0 began ~00:40:20Z per session creation time)

## Errors / refusals / tool failures

Only the step 1 `evidence bundle` failure above. No tool calls were refused.
