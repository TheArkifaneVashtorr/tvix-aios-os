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

## The two caps

Two concurrency caps share one declaration (`services.seat-lane` in
`nixosModules/seatLane.nix`), and the relation between them is asserted at eval
so the collision is unrepresentable rather than merely corrected:

- **`services.seat-lane.waveJobs`** (int, default 8) — the *wave cap*: how many
  groups one `factory-wave` runs at once. The switch writes it to
  `/etc/seat-lane/wave-jobs`, which `factory-wave` reads (after a deliberate
  `FACTORY_JOBS` override, before its literal-5 last resort).
- **`services.seat-lane.maxUnits`** (int, default `waveJobs + 1` = 9) — the
  *running-unit cap*: how many `seat@*` units may be `active` or `activating`
  at once. The switch writes it to `/etc/seat-lane/max-units`, which
  `seat-submit`/`seat-spool` read.

The unit cap is always the wave cap **plus one** because a drive seat is itself
a `seat@` unit: a full wave of `waveJobs` job units plus the driver is
`waveJobs + 1` units, so the cap must be at least that or it would refuse the
last job the wave cap explicitly allows. An assertion refuses any configuration
with `maxUnits <= waveJobs` at eval, naming both values.

Raise them **together, in Nix config only**: set `services.seat-lane.waveJobs`
higher and `maxUnits` follows as `waveJobs + 1` — or set both explicitly,
keeping `maxUnits = waveJobs + 1`. Never edit `/etc/seat-lane/*` by hand; those
files are runtime copies the switch regenerates.

The cap is enforced by whichever actor actually **starts** a unit, not by the
client that merely spools one:

- **The started path** (`seat-submit` without `--no-start`, i.e. the operator
  or a host-side driver) counts `systemctl list-units 'seat@*'
  --state=active,activating` before `systemctl start` and refuses with exit 3
  when the count has reached the cap (`<n> seat units running, cap <max>`) or
  when the count cannot be read (`cannot count seat units …`, fail closed).
- **The `--no-start` path never counts and never refuses**: inside a `seat@`
  unit `systemctl` is denied by design, so a count there would refuse every
  seat-dispatched task. It always writes its marker and returns.
- **`seat-spool`** (the host-side actor that turns a marker into a running
  unit) enforces the cap before each start. Above the cap it does not hang and
  does not silently drop: it writes the job's `result.txt` carrying
  `FACTORY-RESULT status=failed` and a note naming the cap and the observed
  count, removes the marker, and logs `seat-spool: refused <id>: <n> seat units
  running, cap <max>` — so a waiting `--wait` returns promptly with a failed
  result instead of a 900 s timeout.

A malformed cap value refuses instead of falling open: a non-numeric or empty
`SEAT_MAX_UNITS`, or a garbled `/etc/seat-lane/max-units`, exits 3 naming the
value — nothing silently reverts to the default 5.

`seat-submit`'s exit codes are stable: **exit 3 is the running-unit cap
refusal and nothing else** (`<n> seat units running, cap <max>`, or
`cannot count seat units …` when the count or the cap is unreadable); **exit 4**
is "the started unit ended without a result" (the `_poll` path that dumps the
`journalctl` tail) — a caller can always tell "cap full, retry later" from "the
unit produced no result".

## Start a web seat and open it

```
nix run ~/nixos-agent-env#seat-submit -- web --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter --model deepseek/deepseek-v4-pro-0813 --effort medium --port 43210
```

`seat-submit web` prints the job id, starts `seat@<id>`, and returns 0; read
the URL with `journalctl -u seat@<id>.service | grep http://` or `cat
/var/lib/seat/jobs/<id>/url.txt`, then open THAT URL in Firefox — it is
dsh's own line with the namespace address in place of 127.0.0.1 and it
carries `?token=<per-process token>`; the bare `http://10.100.4.2:43210`
answers `401 dsh web authentication required` (FIX2, 2026-09-09). The web
mode passes no `--model`, so your saved picker selection decides the model.

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