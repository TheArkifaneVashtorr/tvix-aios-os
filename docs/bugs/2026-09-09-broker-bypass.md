# The broker bypass, gathered round 3 (BUG1ac)

Supersedes `docs/bugs/2026-09-09-broker-usage-capture.md` (BUG1a, rejected) and the
withdrawn `BUG1`. Every fact carried forward from the Opus gate's independent
reproduction is labelled "carried"; every fact measured fresh this pass carries
its command and that command's real output. Every `file:line` citation that the
fix stage turns on is backed by a `grep -n` whose output is pasted in this
document — none is counted by hand (BUG1a and BUG1ab were rejected for exactly
that). Prose citations that name a line in passing without a paste (the arm labels,
the timeout and tee sites, the assertion and `bodyPatch`/`denyPaths` ranges) were
each read from the file at HEAD and are correct; only the load-bearing ones carry a
paste.

The question this pass exists to answer, from the plan: **is the fix simply making
`factory-task`'s `:378` branch win, and would doing so break the driver's result
parsing?**

Step 3 (green): `nix develop -c githooks/pre-commit` exits 0; its last line is
`render.test.mjs: all assertions passed`.

---

## `## Observed`

### O1 — the predicate that decides the seat's path is false on the host

The `elif` at `tools/factory/seat/factory-task:378` guards the unit route; the
`else` at `:429` is the direct launch. Measured on the host:

```
$ grep -n 'command -v seat-submit' tools/factory/seat/factory-task
378:elif command -v seat-submit >/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then
```

```
$ command -v seat-submit ; echo "exit=$?"
exit=1
```

`seat-submit` is **not on the operator's host PATH**. It exists only on the
`seat@` unit's PATH (see M2 below). So `command -v seat-submit` fails, the `&&`
short-circuits, and the `else` arm at `:429` runs every time.

```
$ grep -n 'launching dsh-openrouter' tools/factory/seat/factory-task
430:  factory_log "launching dsh-openrouter --model $model --headless in $ws (timeout ${timeout_s}s, log $log)"
```

```
$ grep -nF 'timeout -- "$timeout_s" dsh-openrouter' tools/factory/seat/factory-task
437:        timeout -- "$timeout_s" dsh-openrouter --model "$model" --headless "$brief"
```

There is no `--broker` anywhere in the launcher:

```
$ grep -n -e '--broker' tools/factory/seat/factory-task
(no lines; exit 1)
```

**Carried from the gate (independently reproduced twice, not re-measured):** no
`--broker`, `command -v seat-submit` → exit 1, `seatLane.nix:206` puts
`seat-submit` on the unit path only. The defect site is `:429`/`:437`, not the
codex arm at `:362` (BUG1a's miscounted citation).

### O2 — the seat lane's broker has never served a request

```
$ find /var/lib/egress-broker -name 'usage*.jsonl'
(no lines; exit 0)
```

```
$ find /var/lib/egress-broker -maxdepth 2 | sort
/var/lib/egress-broker
/var/lib/egress-broker/cowork
/var/lib/egress-broker/cowork/audit.jsonl
/var/lib/egress-broker/cowork/ca
/var/lib/egress-broker/openrouter
/var/lib/egress-broker/openrouter/audit.jsonl
/var/lib/egress-broker/openrouter/ca
/var/lib/egress-broker/seat
/var/lib/egress-broker/seat/ca
```

```
$ ls -la /var/lib/egress-broker/seat/
total 12
drwxr-xr-x 3 nobody nogroup 4096 Sep  6 09:12 .
drwxr-xr-x 5 nobody nogroup 4096 Sep  6 09:12 ..
drwxr-xr-x 2 nobody nogroup 4096 Sep  8 22:56 ca
```

The ownership columns above (`nobody nogroup`) are the **sandbox's user-namespace
view** — the seat read this directory from inside a user namespace where the
broker's uid is unmapped. On the host the gate measured the owners directly:

```
$ ls -la /var/lib/egress-broker/seat/
drwxr-xr-x 3 egress-broker egress-broker 4096 Sep  6 09:12 .
drwxr-xr-x 5 root          root          4096 Sep  6 09:12 ..
```

The load-bearing content — only a `ca/`, no `audit.jsonl`, no `usage.jsonl` —
reproduces identically either way; only the uid was skewed by the namespace.

The seat instance (`/var/lib/egress-broker/seat/`) holds only a `ca/` directory —
it has **never held `audit.jsonl`, and never held `usage.jsonl`**. For contrast,
the openrouter instance's audit file was last written 2026-09-04, and a `cowork`
instance exists and was last written 2026-09-02 (both pre-date the DeepSeek seat
window that ran continuously from 2026-09-08 21:23):

```
$ stat -c '%n %y %s bytes' /var/lib/egress-broker/*/audit.jsonl
/var/lib/egress-broker/cowork/audit.jsonl 2026-09-02 19:50:27.462071723 -0500 1280869 bytes
/var/lib/egress-broker/openrouter/audit.jsonl 2026-09-04 16:50:27.490403735 -0500 74321 bytes
```

### O3 — switch #24 landed; a `seat@` job now reaches `active` for the first time

The two `seat@` jobs of 2026-09-08 both died at boot on the spill-local EROFS
(carried, and still visible in the journal tail below). After switch #24 a job now
boots and stays `active`. Measured live:

```
$ systemctl list-units --no-pager 'seat@*'
  UNIT                                LOAD   ACTIVE SUB     DESCRIPTION
  seat@20260909-093539-dc8d7a.service loaded active running Operator seat job 20260909-093539-dc8d7a behind its own egress broker
```

```
$ journalctl -u 'seat@*' --no-pager -n 60 2>&1 | tail -12
Sep 08 21:27:17 core seat-run[1576466]:     [cause]: Error: failed to apply loader entry include (cordis:include): failed to apply loader entry spill-local (@deepseek-ai/dsh-spill-local): EROFS: read-only file system, mkdtemp '/tmp/dsh-spill-XXXXXX'
...
Sep 08 21:27:17 core systemd[1]: seat@20260909-022712-d7a01d.service: Main process exited, code=exited, status=1/FAILURE
Sep 09 04:31:02 core systemd[1]: Started Operator seat job 20260909-093102-22caa2 behind its own egress broker.
Sep 09 04:31:02 core seat-run[4192919]: http://10.100.4.2:43210
Sep 09 04:35:00 core systemd[1]: Stopping Operator seat job 20260909-093102-22caa2 ...
Sep 09 04:35:39 core systemd[1]: Started Operator seat job 20260909-093539-dc8d7a behind its own egress broker.
Sep 09 04:35:39 core seat-run[3110]: http://10.100.4.2:43210
```

(Timestamps are CDT = UTC−5; `09:31 UTC` = `04:31 CDT`.) The two post-#24 jobs
are **`drive` (web) jobs** — they print `http://10.100.4.2:43210` and wait for a
browser, they have made no model call, and they are the BUG2 jobs whose
unauthenticated URL is a separate defect. **No headless factory job has ever been
routed through this unit**, because (O1) the predicate that would route it is
false on the host.

### O4 — the credential is plaintext on the host path, and exporter-only after the fix

**Carried from the gate** (the key file's `stat` could not be re-read this pass —
the house guard refuses it, recorded here for honesty):

```
$ stat -c '%n %a owner=%U size=%s' /home/dalhaka/.config/openrouter/key
(nothing; the house guard refuses to read the OpenRouter key file)
```

The gate measured it as `mode=600 owner=dalhaka size=73`. The mechanism is
measured fresh (M1), and the contrast between the two arms' `key_source` is
settled by the wrapper's own lines (M1).

### O5 — the headless profile does not load the spill-local plugin

The post-#24 journal above shows the EROFS came from `profiles/web/#spill-local`.
The headless profile's bundle list carries no web bundle:

```
$ cat ~/.local/share/dsh-openrouter/profiles/headless/package.json
{
  "name": "dsh-profile-headless",
  "private": true,
  "dependencies": {},
  "dsh": {
    "profile": {
      "bundles": [
        "@deepseek-ai/dsh-base",
        "@deepseek-ai/dsh-headless"
      ],
      "patchReload": "startup"
    }
  }
}
```

```
$ cat ~/.local/share/dsh-openrouter/profiles/web/package.json
{
  "name": "dsh-profile-web",
  "private": true,
  "dependencies": {},
  "dsh": {
    "profile": {
      "bundles": [
        "@deepseek-ai/dsh-base",
        "@deepseek-ai/dsh-web-app"
      ],
      "patchReload": "live"
    }
  }
}
```

`@deepseek-ai/dsh-spill-local` is a dependency of `@deepseek-ai/dsh-base`, not of
`@deepseek-ai/dsh-web-app` (round 2 miscounted this — the single dependency
reference sits inside `dsh-base`'s block, not web-app's). Measured:

```
$ grep -n 'dsh-spill-local' pkgs/dsh/package-lock.json
1109:        "@deepseek-ai/dsh-spill-local": "^0.1.2-rc.1",
3162:    "node_modules/@deepseek-ai/dsh-spill-local": {
3164:      "resolved": "https://registry.npmjs.org/@deepseek-ai/dsh-spill-local/-/dsh-spill-local-0.1.2-rc.1.tgz",
```

```
$ grep -n '^    "' pkgs/dsh/package-lock.json | awk -F: '$1<1109' | tail -3
1026:    "node_modules/@deepseek-ai/dsh-attachment-local": {
1041:    "node_modules/@deepseek-ai/dsh-authorization": {
1054:    "node_modules/@deepseek-ai/dsh-base": {
```

```
$ sed -n '1054,1059p' pkgs/dsh/package-lock.json
    "node_modules/@deepseek-ai/dsh-base": {
      "version": "0.1.2-rc.1",
      "resolved": "https://registry.npmjs.org/@deepseek-ai/dsh-base/-/dsh-base-0.1.2-rc.1.tgz",
      "integrity": "sha512-ir6FKWuuO40E5HgB1vsXKUk9oDxrPIlE39TBwazPc8qkgg42NeSM1OmlpCDo4/wdZh50xPxfdI4EVQI7fN8YMg==",
      "license": "MIT",
      "dependencies": {
```

The entry enclosing `:1109` is `node_modules/@deepseek-ai/dsh-base` (opens `:1054`,
closes `:1165`); `dsh-web-app`'s own entry opens at `:3958` and does not list
spill-local. `dsh-base` is bundled by **both** profiles — the headless profile's
`package.json` (pasted above, O5) lists `"@deepseek-ai/dsh-base"` first. So the
round-2 mechanism ("a web-app dependency, which only the `web` profile bundles —
therefore a `--headless` run does not load it") is **not established by dependency
attribution**: a dependency being installed in the lockfile is not the same as a
loader entry being applied, and the enclosing package ships in the headless bundle.

**`UNMEASURED:`** whether a `--headless` run actually loads the
`spill-local` loader entry. The only way to measure it is a
`dsh-openrouter --headless` boot in a scratch `DSH_HOME`, and `dsh-openrouter.sh`
exposes no plugin/profile-listing flag — the wrapper's own usage (`--help`) offers
`--model`, `--permission`, `--denials` and `-- web-app flags`, where `--denials`
lists the last N `PreToolUse` *denial* records (`dsh-openrouter.sh:48`), not a
loader/profile tree. Two facts make the question moot for jobs **after switch
#24**, which is the only regime a fix routes through `seat@` anyway:

```
$ grep -n 'PrivateTmp' nixosModules/seatLane.nix
231:          PrivateTmp = true;
```

1. `seatLane.nix:231` gives the unit a private `/tmp`, so the EROFS
   `mkdtemp('/tmp/dsh-spill-XXXXXX')` that killed the 2026-09-08 boots (O3) can no
   longer hit a read-only `/tmp` — `ProtectSystem = "strict"` (`:232`) makes the
   real `/tmp` read-only, and the private instance is the one writable `/tmp` a
   `dsh-spill-XXXXXX` prefix can reach (SD12's fix).
2. **No headless job has ever run through the unit** (O3) — the two post-#24 jobs
   are `drive` (web) jobs that made no model call — so there is no headless boot
   record to attribute spill-loading to, in either direction.

---

## `## Mechanism`

### M1 — where a headless seat's model call actually goes, and the credential

`pkgs/dsh-openrouter/dsh-openrouter.sh` resolves the credential one of three ways,
and `--broker` is the only path that does not read a real key:

```
$ grep -nF 'OPENROUTER_API_KEY=injected-by-broker' pkgs/dsh-openrouter/dsh-openrouter.sh
319:  OPENROUTER_API_KEY=injected-by-broker
```

```
$ grep -nF 'key_source="credential: placeholder' pkgs/dsh-openrouter/dsh-openrouter.sh
321:  key_source="credential: placeholder (broker injects)"
```

```
$ grep -nF 'key_file=${OPENROUTER_KEY_FILE' pkgs/dsh-openrouter/dsh-openrouter.sh
325:  key_file=${OPENROUTER_KEY_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/openrouter/key}
```

```
$ grep -nF 'export OPENROUTER_API_KEY=$key' pkgs/dsh-openrouter/dsh-openrouter.sh
343:  export OPENROUTER_API_KEY=$key
```

So under `--broker` the wrapper sets `OPENROUTER_API_KEY=injected-by-broker`
(`:319`) and exports it (`:320`); without `--broker` it reads the key file
(`:325`), exports the real key (`:343`), and `key_source="key from $key_file"`
(`:344`). The direct arm (`factory-task:437`) does **not** pass `--broker`, so every
headless factory task to date has held the operator's plaintext key in its
environment and reached `openrouter.ai:443` directly from the host netns.

### M2 — seat-submit is on the `seat@` unit's PATH, not the host's

```
$ grep -n -e 'seatSubmit' nixosModules/seatLane.nix
22:  seatSubmit = (pkgs.callPackage ../pkgs/seat { }).seat-submit;
206:          seatSubmit
```

```
$ grep -n -e 'path = \[' nixosModules/seatLane.nix
202:        path = [
```

The unit's `path` list (`:202-207`) holds `/run/current-system/sw`, the harness
package, `iproute2`, and `seatSubmit` (`:206`). Nothing puts `seat-submit` on the
host's `environment.systemPackages`, and the host PATH (O1) does not contain it.
So the predicate `command -v seat-submit` can only ever be true **inside a seat
unit**, never on the host where `factory-task` launches tasks.

### M3 — how `factory-task` consumes the two arms' output, and what the unit route changes

Both arms write the harness's output into the same `$log`:

```
$ grep -nF '| tee -a -- "$log"' tools/factory/seat/factory-task
372:  ) 2>&1 | tee -a -- "$log"
406:  ) | tee -a -- "$log" >"$submit_out"
438:  ) 2>&1 | tee -a -- "$log"
```

`:372` is the codex arm, `:406` the unit (`seat-submit`) arm, `:438` the direct
arm. The result extraction reads from `$log` in all arms:

```
$ grep -nE 'result_line=\$\(|extract_field\(\)' tools/factory/seat/factory-task
481:extract_field() {
489:result_line=$(
```

```
$ grep -n 'grep -E '\''^FACTORY-RESULT' tools/factory/seat/factory-task
490:  grep -E '^FACTORY-RESULT[[:space:]]+status=(done|partial|failed)([[:space:]]|$)' -- "$log" \
```

The unit arm streams `seat-submit headless` (O-fact): `seat-submit` waits for
`result.txt`, copies `stdout.txt` to its own stdout, and exits with `exit_code.txt`
(these are the SB3 contract, quoted from `pkgs/seat/seat-submit.py`):

```
$ grep -nF 'stdout.txt' pkgs/seat/seat-submit.py
15:the unit's result.txt appears, then copies stdout.txt to its own stdout and
27:and streams stdout.txt exactly as the started path does, but never calls
32:The unit (SB1's seat-run.py) writes stdout.txt, stderr.txt, exit_code.txt and
98:    """Wait for result.txt, stream stdout.txt, and exit with exit_code.txt.
148:    stdout_path = os.path.join(job_dir, "stdout.txt")
```

```
$ grep -nF 'exit_code.txt' pkgs/seat/seat-submit.py
32:The unit (SB1's seat-run.py) writes stdout.txt, stderr.txt, exit_code.txt and
98:    """Wait for result.txt, stream stdout.txt, and exit with exit_code.txt.
154:    exit_path = os.path.join(job_dir, "exit_code.txt")
```

```
$ grep -nF 'return 124' pkgs/seat/seat-submit.py
145:            return 124
```

```
$ grep -nF 'return 3' pkgs/seat/seat-submit.py
125:                return 3
```

So for a headless job that **ends**, the streamed `stdout.txt` lands in `$log`
identically to the direct arm's `tee`, and the unit's harness stdout (the
`FACTORY-RESULT`/`CHECKS`/`COMMITS`/`NOTES` block) is still parsed from `$log`.
The harness writes that block to stdout regardless of arm, so **result parsing is
unchanged** — the plan's stated fear ("a fix that records usage but loses the
factory's result parsing is not a fix") does not materialise for the parsing
itself.

What **does** change, item by item:

- **Exit-code mapping.** The direct arm records `exit_code=${PIPESTATUS[0]}` of the
  `timeout … dsh-openrouter` pipeline (`:439`). The unit arm records
  `exit_code=${PIPESTATUS[0]}` of the `seat-submit headless` pipeline (`:407`),
  which is `seat-submit`'s return value — the harness's exit code written to
  `exit_code.txt` by `seat-run` and re-emitted by `seat-submit` (`_poll` returns
  `int(raw)` from `exit_code.txt`, falling back to 0 on a non-integer). A harness
  crash therefore maps losslessly **when the unit ends cleanly**; the mapping
  differs only in the edge states below.
- **Timeout handling.** The direct arm wraps the harness in GNU `timeout`
  (`:437`), which returns 124 and kills the process on expiry. The unit arm passes
  `--timeout "$timeout_s"` **to `seat-submit`** (`:404`, pasted below, of the call
  at `:397-405`), which polls with that deadline and returns 124 on expiry
  (`seat-submit.py:145`), stopping the unit. There is **no GNU `timeout` around the
  harness inside the unit** — `seat-run` runs `subprocess.run(..., check=False)`
  and only records the code. So a task that overruns its budget is killed by
  `seat-submit` (via `systemctl stop`), not by a signal to the harness — the exit
  code surfaced to `factory-task` is `seat-submit`'s 124, which the direct arm
  would also have surfaced as 124. Net effect on the recorded `exit_code` is
  equivalent; the *how* differs.

```
$ grep -n -- '--timeout' tools/factory/seat/factory-task
404:        --timeout "$timeout_s" \
```

- **The harness's stderr never reaches `$log` on the unit route (a third
  divergence).** The direct arm merges the harness's stdout **and stderr** into the
  task log (`factory-task:438`):

```
$ grep -n -F ') 2>&1 | tee -a -- "$log"' tools/factory/seat/factory-task
372:  ) 2>&1 | tee -a -- "$log"
438:  ) 2>&1 | tee -a -- "$log"
```

  (`:372` is the codex arm, `:438` the direct arm — both merge stderr.) The unit
  arm does **not**: it sends only `seat-submit`'s own stderr to `$submit_err`
  (`factory-task:405`, tee'd into `$log` at `:412`), and `seat-submit` streams
  `stdout.txt` alone back to the caller:

```
$ grep -n -F '2>"$submit_err"' tools/factory/seat/factory-task
405:        2>"$submit_err"
$ grep -n -F 'tee -a -- "$log" <"$submit_err"' tools/factory/seat/factory-task
412:  tee -a -- "$log" <"$submit_err" >/dev/null
```

```
$ sed -n '148,151p' pkgs/seat/seat-submit.py
    stdout_path = os.path.join(job_dir, "stdout.txt")
    if os.path.exists(stdout_path):
        with open(stdout_path, encoding="utf-8") as f:
            sys.stdout.write(f.read())
```

```
$ grep -n -F 'stderr.txt' pkgs/seat/seat-run.py
144:    _write(os.path.join(job_dir, "stderr.txt"), stderr_text)
```

  `seat-run` writes the harness's stderr to `stderr.txt` (`pkgs/seat/seat-run.py:144`);
  `seat-submit`'s own script references `stderr.txt` only in its docstring
  (`pkgs/seat/seat-submit.py:32`) and never streams it back — nothing copies the
  harness's stderr from the job dir into `$log`. On the unit route the harness's
  stderr survives only in the job directory (`stderr.txt`) and the unit's journal,
  never in `$log`. `FACTORY-RESULT` is a stdout block, so result parsing is
  unchanged (above); but today `$log` is where a crashed harness's traceback lands,
  and on the unit route that traceback would land in `stderr.txt` instead — a real,
  code-provable divergence the fix stage must account for.
- **The `.result` net record.** Line 960 records `seat: unit seat@<id>` for the
  unit arm vs nothing for the direct arm:

```
$ grep -nF 'seat: unit seat@' tools/factory/seat/factory-task
960:     printf 'seat: unit seat@%s\n' "$seat_id"
```

  This is additive metadata, not a parsing break.

### M4 — the credential on the fixed path is the broker's placeholder, provable from code

`seat-run` runs the harness with `--broker` (SB1's own command construction):

```
$ grep -n -e '"--broker"' pkgs/seat/seat-run.py
92:            "--broker",
108:                "--broker",
121:                "--broker",
```

The unit pins the placeholder in its environment, never a key:

```
$ grep -n -e 'injected-by-broker' nixosModules/seatLane.nix
90:      # placeholder OPENROUTER_API_KEY=injected-by-broker is the only
173:          OPENROUTER_API_KEY = "injected-by-broker";
```

and an NixOS assertion (`:94-100`) refuses any environment entry containing a
`sk-or-` key. The real key is injected at egress by the broker:

```
$ grep -n -e 'valueFile' nixosModules/seatLane.nix
106:      inject.${cfg.host}.valueFile = cfg.keyFile;
```

```
$ grep -n -e 'def _inject' pkgs/broker/policy.py
380:    def _inject(self, flow):
```

`_inject` (`policy.py:380-404`) writes `Authorization: Bearer <key>` from
`inject.<host>.value_file` at `requestheaders`/`request` time, before the request
leaves the broker — so the harness process sees only `injected-by-broker`, and the
real key exists only in the broker's memory, not in any seat's environment or on
the seat's disk (the broker reads it from `cfg.keyFile` at startup, `policy.py:110`).

### M5 — the data policy that has never once applied to a seat request

The seat broker instance's policy pins the ZDR merge, the host allowlist, and the
`/api/v1/messages` refusal:

```
$ grep -n -e 'bodyPatch' -e 'denyPaths' nixosModules/seatLane.nix
112:      bodyPatch.${cfg.host} = {
121:      denyPaths.${cfg.host} = {
```

```
$ grep -n -e 'allow = \[' nixosModules/seatLane.nix
105:      allow = [ cfg.host ];
```

`bodyPatch` (seatLane.nix:112-118) merges `provider.data_collection = "deny"` and
`provider.zdr = true` onto every `/api/v1/chat/completions` request; `denyPaths`
(`:121-123`) denies `/api/v1/messages`. Because every seat request bypassed the
broker (M1/O1), **none of this ever applied** — carried from the gate, and
re-measured here only as the module lines that pin it.

### M6 — the usage.jsonl write path, and what would finally reach it

```
$ grep -n -e 'usage_log' nixosModules/egressBroker.nix
30:    usage_log = "/var/lib/egress-broker/${name}/usage.jsonl";
```

```
$ grep -n -e 'def _record_usage' -e 'usage_log' pkgs/broker/policy.py
102:        self.usage_log = policy.get(
174:    def _record_usage(self, flow):
```

```
$ grep -n -e 'with open(self.usage_log' pkgs/broker/policy.py
203:            with open(self.usage_log, "a", encoding="utf-8") as f:
```

`_record_usage` (policy.py:174) is called from `response()` (`:522`) after the
audit `allow` line (`:521`), writing one JSONL line to `usage_log`
(`/var/lib/egress-broker/seat/usage.jsonl` for the seat instance). **The writing
code is present and correct**; it has never run because the seat instance has
never served a request (O2).

The streaming tee (the plan's item 4 — whether anything is untested at volume):

```
$ grep -n -e 'def _usage_tee' -e 'def responseheaders' pkgs/broker/policy.py
159:    def _usage_tee(self, flow):
513:    def responseheaders(self, flow):
```

```
$ grep -n -e 'USAGE_TAIL_BYTES' pkgs/broker/policy.py
32:USAGE_TAIL_BYTES = 65536
```

`responseheaders` (`:513-518`) sets `flow.response.stream = self._usage_tee(flow)`
for `text/event-stream` responses on the usage path; the tee forwards every byte
while buffering only the last 64 KiB to find the final usage frame. This SSE
reflect-path logic has **never executed against real seat traffic** (O2 — zero
requests). Whether its 64 KiB tail window reliably captures the last usage frame
for a long multi-tool streaming response — a run the record shows can exceed
5,000 s — is not established by any command this pass could run without launching
a seat, which the Global Constraints forbid:

**`UNMEASURED:`** the SSE usage-tee has never seen real traffic; its correctness
under a long streamed factory response is untested at scale and can only be
established by running one through the broker, which no seat may do.

### M7 — the buffering question (item 3), resolved by the headless profile

`seat-run` buffers the harness's stdout until exit:

```
$ grep -nF 'capture_output=True' pkgs/seat/seat-run.py
137:    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
```

For a headless job this is harmless **when the job ends**: `seat-submit` polls for
`result.txt` (written only after `subprocess.run` returns, `seat-run.py:149`) and
then streams `stdout.txt` (the full buffered stdout) once. The memory-pressure risk
BUG2 named for a long web job does **not** bite a headless factory task the same
way, because: (a) headless output is finite and written to disk at exit; (b) the
headless profile does not load the web app (O5). The one real difference a
long-running *headless* task would see is that `seat-submit`'s poll cannot observe
liveness mid-run (it only sees `result.txt` appear or the timeout), whereas the
direct arm streams live into `$log`. **`UNMEASURED:`** whether a task whose
harness emits progress over its full multi-thousand-second lifetime would exceed
the buffered-output memory budget has not been run; the record's 5,000 s runs
existed but their headless stdout size was never measured against the unit's memory.

---

## `## Where the defect is`

The single site: **`tools/factory/seat/factory-task:378`** — the
`elif command -v seat-submit ...` predicate that is always false on the host. The
direct arm it falls into is `:429`/`:437` (the `else` and its launch line), which
runs `dsh-openrouter --headless` **without `--broker`**, so the seat holds the
operator's plaintext key and reaches `openrouter.ai` from the host netns, bypassing
the broker, its audit log, its usage log, and its data policy. The broker-side
writing code (policy.py) and the seat@ plumbing (seatLane.nix, seat-run.py,
seat-submit.py) are all correct and already implemented; nothing reaches them
because this one predicate never turns true.

---

## `## The fix, as options`

Item 1's question — is the fix making `:378` win via `seat-submit` on PATH, the
`FACTORY_SEAT_UNIT` seam, or neither — answered by measurement. Round 2 named two
ways; the gate measured a third (`seat-drive.sh:109-117`) that round 2 missed, and
showed that round 2's "nothing else consumes a host `seat-submit`" was false. All
three ways, each with its file and line, whether it needs a switch, its blast
radius, and what item 2 says it breaks:

```
$ grep -rn 'command -v seat-submit' tools/
tools/factory/seat/factory-task:378:elif command -v seat-submit >/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then
tools/factory/seat/seat-drive.sh:113:elif command -v seat-submit >/dev/null 2>&1; then
tools/factory/seat/README.md:708:When the seat lane's submit CLI is installed (`command -v seat-submit`
```

Two *executable* consumers of a host `seat-submit`: `factory-task:378` (the
predicate under fix) and `seat-drive.sh:113` (the drive-seat launcher). The third
grep hit is README prose, not a consumer.

```
$ sed -n '109,117p' tools/factory/seat/seat-drive.sh
# seat-submit is a flake package, not on the host PATH (Assumption 8); resolve
# it by name from PATH (or SEAT_SUBMIT), else through `nix run` of the flake.
if [ -n "${SEAT_SUBMIT:-}" ]; then
  seat_cmd=("$SEAT_SUBMIT")
elif command -v seat-submit >/dev/null 2>&1; then
  seat_cmd=(seat-submit)
else
  seat_cmd=(nix run "$FACTORY_TOOLBOX_REPO#seat-submit" --)
fi
```

1. **Put `seat-submit` on the operator's host PATH via the module (a module +
   config change)** — the sibling lane already does exactly this for its own CLI:

```
$ grep -n 'systemPackages' nixosModules/modelLane.nix
194:    environment.systemPackages = [
$ sed -n '194,198p' nixosModules/modelLane.nix
    environment.systemPackages = [
      laneSubmit
      laneWait
      pkgs.jq
    ];
```

   `nixosModules/seatLane.nix` has no such line (`grep -n 'systemPackages'
   nixosModules/seatLane.nix` → no lines; it only puts `seatSubmit` on the unit's
   `path` at `:206`, M2). Copying `modelLane.nix:194-198`'s pattern —
   `environment.systemPackages = [ seatSubmit ];` — makes `command -v seat-submit`
   succeed on the host after the next switch, so `:378`'s first conjunct turns
   true and the second (`FACTORY_SEAT_UNIT:-1 != 0`) is already true. **Needs a
   switch** (the operator's action, which no seat may run). **Blast radius:**
   `factory-task`'s branch selection, and — the consumer round 2 missed —
   `seat-drive.sh:113`, which would then take the PATH copy instead of its
   `nix run` fallback. That is a change in *provenance*, not in behaviour: the
   PATH copy and the live unit's `seat-run` come from **one system closure**
   (both from the same `environment.systemPackages`/`path` evaluation of the
   switched system), whereas the `nix run` copy comes from the working tree of
   `$FACTORY_TOOLBOX_REPO` (`factory-lib.sh:27`, `/home/dalhaka/nixos-agent-env`).
   So `seat-drive` would in fact start using *more* closely the same binary the
   unit runs, not less.

2. **The `FACTORY_SEAT_UNIT` seam (an environment change, not code).** The second
   conjunct is `[ "${FACTORY_SEAT_UNIT:-1}" != "0" ]`. This seam can only
   *disable* the unit route (set it to `"0"`); it cannot *enable* it while the
   first conjunct fails. So it is a **kill-switch, not an activator**: setting
   `FACTORY_SEAT_UNIT=1` changes nothing while `command -v seat-submit` still
   fails (O1). The fix must preserve it as the deliberate opt-out
   (`tools/factory/seat/README.md:708` documents it — pasted at the top of this
   section). **No switch, no file; zero blast radius beyond what it already
   is** — but it is not a fix, it is the escape hatch the fix keeps.

3. **Copy `seat-drive.sh:109-117`'s resolution into `factory-task` (a change to
   one file, no switch).** The predicate's first conjunct is `command -v
   seat-submit`; the house already solved "resolve `seat-submit` from
   `$SEAT_SUBMIT`, else PATH, else `nix run`" in `seat-drive.sh:109-117` (pasted
   above). Making `factory-task` resolve the submit command the same way — with
   the `nix run` arm deliberately *not* copied, because a runtime fallback in the
   launch path is the defect's own shape and it builds from the working tree —
   is a change to `tools/factory/seat/factory-task` alone: no package, no
   `environment.systemPackages`, no module, and **no switch**. Measured cost of
   the `nix run` arm that must *not* be used here:

```
$ time nix run /home/dalhaka/nixos-agent-env#seat-submit -- --help
… (usage text) …

real	0m1.046s
user	0m0.695s
sys	0m0.217s
```

   `nix run "$FACTORY_TOOLBOX_REPO#seat-submit"` builds from the **working tree**
   of `$FACTORY_TOOLBOX_REPO` (`/home/dalhaka/nixos-agent-env`), so that CLI can
   skew from the live unit's `seat-run` — which is why the fix stage should copy
   resolution by `$SEAT_SUBMIT`/PATH (provenance-free) and refuse when neither
   resolves, not copy the `nix run` fallback.

**The blast radius common to every route is the unit itself.** Whichever way the
predicate turns true, routing a headless factory task through `seat@` puts it
inside the unit's namespace and hardening:

```
$ sed -n '205,275p' nixosModules/seatLane.nix
          pkgs.iproute2
          seatSubmit
        ];
        serviceConfig = {
          Type = "simple";
          User = cfg.operatorUser;
          NetworkNamespacePath = netnsPath;
          ExecStart = "${seatRun}/bin/seat-run %i";
          # SB6b: the web forwarder is a background child of the wrapper
          # (dsh-openrouter.sh spawns `socat ... &` before exec'ing node), so it
          # must die with the unit. KillMode=control-group ends every process in
          # the unit's cgroup on stop -- the default `control-group` is the same
          # value, but it is pinned here (seat-eval) because a `process` mode
          # would signal only the main PID and leave the socat forwarder holding
          # the namespace port after the unit stops (proven by seat-vm).
          KillMode = "control-group";
          # SD12: the harness's spill store writes to an absolute
          # /tmp/dsh-spill-XXXXXX prefix -- a literal inside
          # @deepseek-ai/dsh-spill-local's privateRoot, so neither DSH_CACHE_ROOT
          # (SD5) nor TMPDIR can redirect it. ProtectSystem=strict makes the
          # real /tmp read-only, which killed the very first drive boot with
          # EROFS mkdtemp '/tmp/dsh-spill-XXXXXX'. A private instance /tmp
          # (mounted per unit, dies with the unit under KillMode=control-group)
          # is the only writable /tmp such a prefix can ever reach, and it keeps
          # one job from reading another job's spill. The cache, which must
          # outlive a job, stays at DSH_CACHE_ROOT=/var/lib/seat/cache.
          PrivateTmp = true;
          ProtectSystem = "strict";
          # SB4b (module bug 1): every path below may be ABSENT on a fresh
          # machine (the operator's ~/factory, ~/nixos-agent-env, ~/flakes and
          # ~/.local/share/dsh-openrouter are created by other tooling, not
          # this module). ReadWritePaths= fails the unit at NAMESPACE setup
          # (status 226) when a listed path is missing; the "-" prefix makes
          # systemd tolerate an absent path, so seat@ starts on a machine
          # without any of them.
          ReadWritePaths = [
            "/var/lib/seat"
            "-/home/${cfg.operatorUser}/factory"
            "-/home/${cfg.operatorUser}/nixos-agent-env"
            "-/home/${cfg.operatorUser}/flakes"
            "-/home/${cfg.operatorUser}/.local/share/dsh-openrouter"
          ];
          # OG3r: the file the seat's hook runs as the house guard
          # (FACTORY_HOUSE_GUARD, above) is mounted read-only into every job by
          # a kernel mount — no process in the unit can write it, unlink it, or
          # rename over it (EBUSY), however a command spells its path. The "-"
          # prefix tolerates an absent checkout, exactly as the ReadWritePaths
          # entries do, and the copies under ~/factory/ws (the workspace) are
          # untouched.
          ReadOnlyPaths = [
            "-/home/${cfg.operatorUser}/nixos-agent-env/tools/orchestrator-guard.sh"
          ];
          # brief §3 invariant 2: the broker's injected credentials are never
          # visible to the network-capable seat process. (Unlike the lane, the
          # seat deliberately runs in the operator's own home -- it edits the
          # operator's clones -- so /home is NOT hidden here.)
          #
          # SD5: systemd's two control sockets are ALSO hidden, each mounted
          # over with an inaccessible node (the "-" prefix tolerates absence).
          # They make `systemctl` and any direct systemd control impossible from
          # inside a job -- the spool (SD6) is the one host actor the seat may
          # reach, never the service manager. Proven from inside the template by
          # seat-vm step 9's `systemctl=1`/`dbus=1` probes.
          InaccessiblePaths = [
            "/var/lib/secrets"
            "-/run/systemd/private"
            "-/run/dbus/system_bus_socket"
          ];
          NoNewPrivileges = true;
```

For a headless factory task, what each line allows or forbids, **as far as the
file shows** (what it cannot show is marked):

- **`:211` `NetworkNamespacePath = netnsPath`** — the task's network is the unit's
  veth netns, reachable only through the broker; a bare `openrouter.ai` connection
  cannot leave the host netns. `nix build`/`git` do their fetch inside this netns
  and would reach their remotes only if the broker's `allow` admits them
  (`allow = [ cfg.host ]` at `seatLane.nix:105` names `openrouter.ai` only) —
  **`UNMEASURED:`** whether `nix build`'s cache-substituter `fetch` and `git`'s
  remote actually go through, because no headless job has run through the unit
  (O3). The unit's own `path` carries `iproute2` (`:205`) but nothing here grants
  egress beyond the broker's allowlist.
- **`:231-232` `PrivateTmp = true` / `ProtectSystem = "strict"`** — `/tmp` is the
  unit's private instance (writable, dies with the job); the real `/tmp` and the
  whole system tree are read-only. A headless task's spill store and any
  `mkdtemp` land in the private `/tmp` and vanish at job end; nothing in `$HOME`
  or the workspace is affected by `ProtectSystem` *directly*, but a task that
  writes anywhere outside the `ReadWritePaths` below gets EROFS.
- **`:240-246` `ReadWritePaths`** — the only writable paths are `/var/lib/seat`,
  `~/factory`, `~/nixos-agent-env`, `~/flakes`, `~/.local/share/dsh-openrouter`.
  The workspace under `~/factory/ws` is **inside `~/factory`, so it is writable**;
  `~/.cache` is **not** listed and is **not writable** (a `nix` or `git` tool that
  writes `~/.cache` would hit the read-only tree unless `DSH_CACHE_ROOT`/`XDG_*`
  redirect it — SD5 redirects the harness cache to `/var/lib/seat/cache`). `git`
  writes into the workspace (writable) and reads the object store there; `nix
  build` writes into `/home/dalhaka/nixos-agent-env`'s flake store or its own
  `nix` daemon store — **`UNMEASURED:`** whether `nix build`'s daemon round-trip
  (`/nix/store` is not in the writable list) works from inside the unit, since no
  headless job has run through it.
- **`:268-272` `InaccessiblePaths`** — `/var/lib/secrets`,
  `/run/systemd/private`, `/run/dbus/system_bus_socket` are hidden. `git`, `nix
  build` and the workspace touch none of these; but `systemctl`/`dbus` from inside
  the task are impossible by construction (the spool is the one host actor).
- **`:273` `NoNewPrivileges = true`** — the task cannot gain privileges; a
  `nix build` that needs `unshare`/`setuid` helpers or a mount would be refused.

This is a much larger change to what a factory task can do than "only
`factory-task`'s branch selection changes" (round 2's over-strong claim): the
first headless task through the unit is itself the measurement of whether its
`nix build`, `git` and workspace survive these lines, and that measurement does
not exist yet (**`UNMEASURED:`** — O3).

Neither of the three routes *creates* the unit, broker, inject, policy or spool —
those all already exist and are correct (M4, M5, M6). The routes differ only in
how `factory-task`'s predicate at `:378` turns true, and in whether a switch is
needed.

**What item 2 says each route would break:** for a headless job that ends, the
unit route's streamed `stdout.txt` lands in `$log` exactly as the direct arm's
`tee` (M3), so `FACTORY-RESULT`/`CHECKS`/`COMMITS`/`NOTES` parsing, the `touches`
contract check, and the commit-count verification all read the same `$log` and the
same branch — **they do not break**. The three genuine divergences the fix stage
must watch:

- **Exit-code edge states.** A clean end maps the harness code through
  `exit_code.txt` losslessly; a timeout maps to 124 via `seat-submit` (which stops
  the unit) rather than via GNU `timeout` killing the harness — equivalent recorded
  code, different mechanism (M3). A unit that dies before writing `result.txt` maps
  to `seat-submit` exit 3 (seat-submit.py:125), which the direct arm has no analog
  for.
- **The harness's stderr.** The direct arm merges stderr into `$log`
  (`factory-task:438`); the unit arm sends only `seat-submit`'s own stderr to
  `$submit_err` (`:405`, tee'd at `:412`), `seat-submit` streams `stdout.txt`
  alone (`seat-submit.py:148-151`), and `seat-run` writes the harness's stderr to
  `stderr.txt` (`seat-run.py:144`) that nothing copies back (M3) — so a crashed
  harness's traceback lands in `stderr.txt`, not `$log`.
- **Result-streaming liveness.** The direct arm streams the harness live into
  `$log`; the unit route only surfaces `stdout.txt` after the job ends (M7), so a
  long run produces no live log tail during execution. This does not break parsing
  but changes observability during the run.

---

## `## What is broken now` (the brief invariants, in their own words)

```
$ grep -n 'No agent process holds' docs/brief.md
70:2. No agent process holds a provider credential on disk or in its environment in
```

```
$ grep -n 'one chokepoint' docs/brief.md
72:3. Every byte leaving the machine crosses one chokepoint that can log the request and
```

**Invariant 2 is breached right now.** Every headless factory task launches
`dsh-openrouter` without `--broker` (M1, factory-task:437), which reads the real
key from `~/.config/openrouter/key` (dsh-openrouter.sh:325) and exports it into
the harness environment (`:343`). The agent process therefore *does* hold the
provider credential on disk (reads it) and in its environment (exports it) in
plaintext — not injected at an egress proxy. The gate's `stat` measured
`mode=600 owner=dalhaka size=73`; this pass's re-stat was refused by the house
guard (O4), which is itself the guard's correctness, not a gap in the finding.

**Invariant 3 is breached right now, for dsh.** dsh (DeepSeek Harness) is in scope
(brief.md:59-60, carried; `:58` is blank and the "Harnesses in scope" sentence
spans `:59`–`:60`). Its model calls left the machine from the host netns
straight to `openrouter.ai:443`. Nothing logged them (`/var/lib/egress-broker/seat/`
has never held an `audit.jsonl`, O2) and nothing was positioned to refuse them.

**The consequences outrank the missing `usage.jsonl`.** Because no seat request
crossed the broker, the live seat policy's `body_patch` (`provider.data_collection:
"deny"`, `provider.zdr: true`), `allow: ["openrouter.ai"]`, and
`deny_paths` `/api/v1/messages` (M5) have **never applied** to any seat request.
Every DeepSeek seat request reached OpenRouter without the zero-data-retention
directive, without the host allowlist, and without the path refusal. This is a
data-handling fact larger than the missing spend-telemetry line the bug was opened
for.

---

## `## What a fix must not break`

Brief §3 invariant 2, as written ("No agent process holds a provider credential on
disk or in its environment in plaintext; credentials are injected at an egress
proxy"): whatever the fix does, the key must **not move into a seat's environment
or onto a seat's disk**. The fixed path already satisfies this by construction —
`seat-run` passes `--broker` (seat-run.py:92), the unit pins
`OPENROUTER_API_KEY=injected-by-broker` (seatLane.nix:173), the NixOS assertion
refuses any `sk-or-` value in the unit environment (seatLane.nix:94-100), and the
real key is injected at egress by the broker's `_inject` (policy.py:380). The fix
must preserve this; the danger is not the broker path but the temptation to "fix"
telemetry by moving the key into the direct arm, which would invert the invariant
repair.

Brief §3 invariant 3 (one chokepoint that can log and refuse): the fix must route
every seat request through a broker instance, and the `FACTORY_SEAT_UNIT=0` seam
(M3/fix-option 2) must remain available to the operator as a deliberate, rare
kill-switch — not as a default that lets a later regression silently restore the
bypass.

---

## `## Unmeasured`

- **`UNMEASURED:`** the SSE usage-tee (policy.py:159, `responseheaders` at `:513`)
  has never run against real seat traffic; whether its 64 KiB tail window reliably
  captures the last usage frame for a long multi-tool streamed response is untested
  at scale, and can only be established by running one through the broker, which no
  seat may do (M6).
- **`UNMEASURED:`** whether a multi-thousand-second headless task would exceed the
  unit's buffered-stdout memory budget under `capture_output=True`
  (seat-run.py:137) — the record's 5,000 s runs existed, but their headless
  stdout size against the unit's memory was never measured (M7).