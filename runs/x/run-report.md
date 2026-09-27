# Run x — draft-packet workflow

## Step 0 — snapshot checkout

```
$ git fetch origin fx/F4
From https://github.com/TheArkifaneVashtorr/tvix-aios-os
 * branch            fx/F4      -> FETCH_HEAD
$ git checkout -B fx/F4 origin/fx/F4
Reset branch 'fx/F4'
branch 'fx/F4' set up to track 'origin/fx/F4'.
Your branch is up to date with 'origin/fx/F4'.
$ git log -1 --format=%H
c9c5bd7c04940631a1fb6d2878eab0eadb537cc4
$ git status --short
(empty)
```

## Step 1 — environment check

```
$ pwd -P
/home/user/tvix-aios-os
$ command -v nix; readlink -f "$(command -v nix)"
/usr/local/bin/nix
/home/user/tvix-aios-os/tools/cloud/nix
$ command -v evidence; cat "$(command -v evidence)"
/usr/local/bin/evidence
#!/bin/sh
exec /home/user/tvix-aios-os/tools/cloud/evidence "$@"
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
bundle exit 0
```

All step 1 requirements met (duckdb present, 1.5.5).

## Step 2 — environment record

- `claude --version`: `2.1.283 (Claude Code)`
- Model (from `get_session`): `session_context.model` = `claude-opus-5-5`, `external_metadata.last_served_model` = `claude-opus-5-5`, `configured_model` = `claude-opus-5-5`; effort_level `high`, permission_mode `auto`
- `echo "$CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"`: `80`
- `nproc`: `4`
- `free -g`:

```
               total        used        free      shared  buff/cache   available
Mem:              15           0          14           0           0          15
Swap:              0           0           0
```

- Start time: `2026-09-27T02:14:21Z`

## Step 3 — scratch directory

`mkdir -p /tmp/draft-scratch` — created (empty before the workflow ran).

## Step 4 — workflow launch

`Workflow` called once with name `draft-packet`, args:

```json
{"spec": "docs/context/generation.md", "name": "generation", "date": "2026-09-14", "scratch": "/tmp/draft-scratch", "repo": "/home/user/tvix-aios-os"}
```

Launch output: `Workflow launched in background. Task ID: wbn35qbex`, `Run ID: wf_0ca413a5-0ea`.
No interrupt, no re-run.

## Step 5 — result

- End time: `2026-09-27T03:03:06Z`
- Run ID: `wf_0ca413a5-0ea` (task ID `wbn35qbex`)
- Journal: `/root/.claude/projects/-home-user-tvix-aios-os/9aaa8216-2c22-554f-a920-3aab9f99f8ed/subagents/workflows/wf_0ca413a5-0ea/journal.jsonl` (13 lines, 13148 bytes; copied to `runs/x/journal/journal.jsonl`)

### Usage block (verbatim)

```
<usage><agent_count>6</agent_count><agents_done>6</agents_done><agents_error>0</agents_error><agents_skipped>0</agents_skipped><agents_empty_result>0</agents_empty_result><subagent_tokens>1023664</subagent_tokens><tool_uses>147</tool_uses><duration_ms>2909399</duration_ms></usage>
```

### Returned result (verbatim)

```
{"draft":"/tmp/draft-scratch/draft-0.md","packet":["/tmp/draft-scratch/packet/mechanical.md","/tmp/draft-scratch/packet/record.md","/tmp/draft-scratch/packet/field.md","/tmp/draft-scratch/packet/operator.md","/tmp/draft-scratch/packet/target.md"],"outputTokensByPhase":{"packet":36968,"draft":219843},"spent":258753}
```

### Errors, refusals, tool failures

- None reported by the workflow: `agents_error` 0, `agents_empty_result` 0, `agents_skipped` 0.
- All `*.err` files in the scratch directory are 0 bytes (`packet/check.err`, `packet/graph.err`, `brief-GN1..4.err`, `check-draft.err`). `packet/check.out` is also 0 bytes.
- A case-insensitive grep of the journal for `error|refus|denied` matches 3 lines. All 3 are prose inside the agents' result digests ("with no errors", "refusing a key…", "factory-task refuses", "not refused"), not tool failures.
- `git status --short` after the workflow showed only `?? runs/`. The workflow wrote nothing else into the repository.

### Observations (recorded, not acted on)

- `draft-0.md` and `2026-09-11-generation.md` in scratch are the same size (88192 bytes). The plan filename carries the date `2026-09-11`, while the `date` arg was `2026-09-14`.
- The workflow cloned a working tree into `/tmp/draft-scratch/tree` (it has its own `.git/` directory; `repos.toml` names it `nixos-agent-env`). Scratch is 63M in total, with 915 files. Copying it into `runs/x/scratch/` per step 5 puts a nested git repository at `runs/x/scratch/tree`. `git add` records that as an embedded-repo gitlink, not as its files (see step 6).

## Step 6 — commit

Branch: `run/F4-x-0927030335`. `git add runs/x` printed (verbatim):

```
warning: adding embedded git repository: runs/x/scratch/tree
hint: You've added another git repository inside your current repository.
hint: Clones of the outer repository will not contain the contents of
hint: the embedded repository and will not know how to obtain it.
hint: If you meant to add a submodule, use:
hint: 
hint: 	git submodule add <url> runs/x/scratch/tree
hint: 
hint: If you added this path by mistake, you can remove it from the
hint: index with:
hint: 
hint: 	git rm --cached runs/x/scratch/tree
hint: 
hint: See "git help submodule" for more information.
```

So this commit holds `runs/x/scratch/tree` only as a gitlink (the clone's HEAD commit), not its files. The clone itself stayed in `/tmp/draft-scratch/tree`. After staging, `git status --short` listed only `runs/x/` paths.
