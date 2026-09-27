Every command is pasted from a dry run here or quoted from the board's RECIPES/the runbooks; nothing is a sentence where a command would do. The plan follows the three defaults until step 1 is answered.

1. **Answer the three questions** (one word each: `high|medium`, `hold|allow`, `derived|heading`). Acceptance: the answers on the board; `high` is a one-line `effort` edit of the `openrouter/orchestrate` row in SD1's commit or a follow-up docs commit whose body cites the answer.
2. **Before wave 1 — the claims file must validate on today's clock** (the pre-commit hook refuses every seat commit otherwise, Assumption 6):
   ```
   nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"; echo exit=$?
   ```
   Expected: no output, `exit=0`. If it prints `gap past review_by` lines (six did at 2026-09-27), the orchestrator extends those dates with a reason in one docs commit first; you re-run the line. Acceptance: `exit=0`.
3. **Launch wave 1** (the Dispatch section's first line without `--dry-run`, in the background):
   ```
   setsid -f bash -c 'exec tools/factory/seat/factory-dispatch sd1 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md >> ~/factory/runs/sd1.dispatch.log 2>&1' </dev/null
   ```
   Acceptance: `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep '^\*\*Running:\*\*'` names `nixos-agent-env/SD1`, `SD2`, `SD3`, `SD5`.
4. **After wave 2 lands — switch #21 (A2).** SD4 (the wrapper and its guard), SD5 (the module, `seat-run`) and SD6 (`seat-submit`, the embedded `route.py`) change the closure:
   ```
   nix build .#nixosConfigurations.core.config.system.build.toplevel
   nix store diff-closures /run/current-system ./result
   ```
   **Predicted delta** (a prediction; the measured delta is recorded beside it on the landed tree before this line ships): added — the `seat-spool` package, `seat-spool.path`, `seat-spool.service`, a `guard-rules.txt` store path; changed — `seat@.service` (InaccessiblePaths, `SEAT_SPOOL`), the `seat` runner package (`seat-run.py`, `seat-submit.py`, `seat-spool.py`, the embedded `route.py`), `dsh-openrouter` and its `hook-guard`; removed — nothing; `python3-minimal` unchanged. Then `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core`. Acceptance: `systemctl status seat-spool.path | head -3` → `active (waiting)`; `systemctl cat seat@.service | grep -c 'run/dbus'` → `1`; `systemctl show seat@.service -p Environment --value | tr ' ' '\n' | grep -c '^SEAT_SPOOL=1$'` → `1`. No user unit needs a hand start (the spool is a system path unit the switch activates). Rollback: `sudo /nix/var/nix/profiles/system-45-link/bin/switch-to-configuration switch` (generation 45 = `a53d2e5`, the live generation on the board; confirm with `nix-env --list-generations -p /nix/var/nix/profiles/system | tail -3` first).
5. **After SD10 lands in `~/flakes/dsh-harness` — deploy the driver's home once** (`git -C ~/flakes/dsh-harness pull --ff-only` first):
   ```
   mkdir -m 700 -p ~/.local/share/dsh-driver && ln -s ~/flakes/dsh-harness/skills ~/.local/share/dsh-driver/skills && ln -sf ~/flakes/dsh-harness/AGENTS.md ~/.local/share/dsh-driver/AGENTS.md
   ```
   Acceptance: `test -r ~/.local/share/dsh-driver/skills/driving/SKILL.md && echo ok` → `ok`. Your interactive seat's home (`~/.local/share/dsh-openrouter`) is untouched.
6. **Start the driver** (after step 4; SD6):
   ```
   nix run ~/nixos-agent-env#seat-submit -- drive --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-driver --port 43210
   ```
   It prints the job id. Acceptance: `cat /var/lib/seat/jobs/<id>/url.txt` → `http://10.100.4.2:43210`; `systemctl show seat@<id> -p ActiveState --value` → `active`; open the URL in the browser. Stop it with `systemctl stop seat@<id>` (your polkit right). Until step 4 the interim web seat is the board's line: `nix run ~/nixos-agent-env#seat-submit -- web --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter --model deepseek/deepseek-v4-pro-0813 --effort medium --port 43210`.
7. **The first driver session measures Assumption 10.** Say `brief`. Acceptance: the seat prints the task brief's `**Next wave**` line. If it reports that `nix develop --offline` failed inside the namespace, stop there — that is the orchestrator's item (the verbs need a devShell-free path), not a seat's. Then ask for one dispatch of a rung-1 task; acceptance: `cat "$(ls -t /var/lib/seat/jobs/*/spool.txt | head -1)"` begins `started`, and the newest `~/factory/runs/*/*.result` carries `rung: 1` and a `class:` line.
8. **Spend before wave 1 (A3, A9).** Four seats start at once (three on Pro medium, one on Flash off — the `unit`/`seat-vm`-heavy tasks are M). The balance is yours to check (the board: $32.23 at 08:55, no preload above $100); at the 2026-09-04 rate ($0.10–0.19 per XS/S run, planning design §1) wave 1 costs of the order of $1 — a proxy: the tree holds no activity-export rows, so spend since the last top-up is unmeasured here.
9. **Rollback per task:** `nix develop -c git revert <the task's commit>` in `~/nixos-agent-env`; the switch rollback is step 4's; `rm -rf ~/.local/share/dsh-driver` removes the driver's home without touching the interactive seat.
10. **The claims SD1 adds** carry `review_by = 2026-10-04`: before that date either `evidence report ladder` shows the rung's row at n ≥ 5 or the orchestrator extends the date with the n it did reach.
