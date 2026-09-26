# The seat behind its broker — the operator's runbook

`services.seat-lane` (`nixosModules/seatLane.nix`) runs the operator's DeepSeek
seat behind its own egress-broker instance `seat`: the unit `seat@<job>` runs
as the operator inside the `egress-seat` network namespace and reaches
`openrouter.ai` only through the broker, which injects the key from the
root-only file at egress. The seat never holds a key, and the unit starts only
when you start it.

## What runs where

```
nix run ~/nixos-agent-env#seat-submit -- --help
```

The broker instance `seat` maps 10.100.4.1 → 10.100.4.2 on port 3141 with an
allowlist of exactly `openrouter.ai`; each job is a `seat@<id>` unit (job ids
are minted as `%Y%m%d-%H%M%S-<6hex>`) whose job directory is
`/var/lib/seat/jobs/<id>/` (`job.json brief stdout.txt stderr.txt exit_code.txt
result.txt url.txt`); the two key files are the root-only
`/var/lib/secrets/openrouter-key` (injected by the broker, hidden from the unit
by `InaccessiblePaths`) and `~/.config/openrouter/key` (the wrapper's fallback,
deleted in §g); `/var/lib/seat/jobs` is **not** backed up (`proton-backup.nix`
covers only `/var/lib/evidence` and `/var/lib/lanes`), so the spec's sessions
exclusion is moot.

## Before the first job

```
systemctl show -p ActiveState,Result seat@<id> && journalctl -u seat@<id>.service
```

Until SD5 lands and switch #22 activates a writable cache root, a job's harness
dies on its cache directory under `/tmp` (read-only inside the `seat@` unit,
which declares `ProtectSystem=strict`), so `result.txt` reads `status=failed`
and `stderr.txt` names the cache path — expect that today, not a working job.

## Start a web seat and open it

```
nix run ~/nixos-agent-env#seat-submit -- web --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter --model deepseek/deepseek-v4-pro-0813 --effort medium --port 43210
```

`seat-submit web` prints the job id, starts `seat@<id>`, and returns 0; read
the URL with `journalctl -u seat@<id>.service | grep http://` or `cat
/var/lib/seat/jobs/<id>/url.txt`, then open `http://10.100.4.2:43210` in
Firefox — the web mode passes no `--model`, so your saved picker selection
decides the model.

## Run a headless job by hand

```
printf 'Reply with the single word ok.\n' > /tmp/brief && nix run ~/nixos-agent-env#seat-submit -- headless --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter --model deepseek/deepseek-v4-flash --effort off --brief /tmp/brief
```

`seat-submit headless` polls `result.txt` every 2 s for up to 10,800 s and
returns the job's exit code, with the answer printed to stdout. (Note the
`--brief` file lives on the host `/tmp`, distinct from the unit's read-only
namespace.)

## Watch the audit

```
nix develop -c jq -c 'select(.verdict=="allow")' /var/lib/egress-broker/seat/audit.jsonl
```

One JSON object per line (`ts instance client method host host_header sni path
bytes_out bytes_in verdict reason`) is appended to the broker audit as each
request passes or is refused; the hook guard's separate denial audit is read with
`dsh-openrouter --denials 20`.

## Stop a job

```
systemctl stop seat@<id>
```

`dalhaka` is granted `start`/`stop`/`restart` of `seat@*.service` through polkit
(no sudo, no password), and because the unit declares no `KillMode`/`ExecStop`
the control-group default ends every process of the job.

## Delete the key file after the first successful jobs

```
rm ~/.config/openrouter/key
```

While `~/.config/openrouter/key` exists the wrapper prints
`dsh-openrouter: the key file is deprecated; seat jobs run behind the broker
(docs/runbooks/seat.md)`; once it is gone the wrapper dies `4` with
`no key: export OPENROUTER_API_KEY, or create …`, so let §(c) and §(d) succeed
first, then flip the claim row `seat-key-exception-undecided` to
`status = "verified"`, `class = "operator"`,
`evidence = "operator:<date> …"`.

## Roll back

```
sudo /nix/var/nix/profiles/system-<N>-link/bin/switch-to-configuration switch
```

Every switch is a generation; the board names N at switch time (46 live today,
45 its rollback), and `switch-to-configuration` against the previous generation
is the house form — never `nixos-rebuild switch --rollback`.