---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run ev1, task R8 — REJECTED

Branch head `9a0e19a9ef86` (`~/factory/ws/ev1/R8`, `task/R8`). Reviewer: Opus, high effort, throwaway clone; checks re-run by ref.

## Summary

The implementation is right and the named checks are green — unit, lint and the full pre-commit gate all pass on a clean tree, red-before-green reproduces exactly as the plan predicts, and a direct probe of `_bash_verdict` shows every spelling the plan's Interfaces line names (127.0.0.1 / localhost / [::1] / 0.0.0.0 on :7700, `/run/user/<uid>/helm/token`, `$XDG_RUNTIME_DIR/helm/token`) refused while ComfyUI's :8188 stays allowed. The runbook paragraph is verbatim and its added lead sentence checks out against helm-v1.md and nixosModules/helm.nix:672. What blocks approval is test strength, not behaviour: of seven mutations, three survived, and one of them matters — deleting the `/run/user/\\d+/helm/token` rule leaves both new tests green, because the single payload naming that path also names the port. The token half of "the Helm control port and its token" is unpinned, which is precisely the vacuous-test case the TDD constraint names. One extra assertion (`cat /run/user/1000/helm/token` on its own) closes it; the `[::1]` case is a second line worth adding at the same time. Not blocker-grade — nothing here is wrong or unsafe, and the fix is two lines in one file with no implementation change.

## Checks

- green — unit: nix build .#checks.x86_64-linux.unit -L --no-link → exit 0, /nix/store/3pz9gsn1asm3hx4b6j0nq5v18bpdl518-unit-tests. Also ran the file directly: nix develop -c bats tests/unit/70-dsh-openrouter.bats -f "hook-guard" → 13/13 ok, including the two new cases.
- green — lint: nix build .#checks.x86_64-linux.lint -L --no-link → exit 0.
- green — pre-commit gate: nix develop -c githooks/pre-commit → exit 0 ("formatted 72 files (0 changed)", "All checks passed!", "20 files already formatted", "render.test.mjs: all assertions passed").
- green — touches contract: Exactly the three files in the plan's touches list; no file outside it. git show --stat: docs/runbooks/helm.md 14+, pkgs/dsh-openrouter/hook-guard.py 11+, tests/unit/70-dsh-openrouter.bats 10+.
- green — commit subject + trailer: Subject byte-identical to the plan's. Trailers: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run ev1)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` — the both-trailers convention established by commit "factory: seat-made commits carry both trailers" (21 prior commits in history do the same). Not a deviation.
- green — hard rules: Diff contains no bypass flag, no 2>/dev/null, no secrets, no sudo/systemctl/nixos-rebuild invocation, no placeholder text. Guard stays stdlib-only (json/os/re/sys/time); host-core's python3Minimal assertion at flake.nix:698-704 still holds.
- green — behaviour probe (implementation correctness): Driving _bash_verdict directly at HEAD: DENY for `cat /run/user/1000/helm/token`, `curl -s http://[::1]:7700/`, `curl http://0.0.0.0:7700/action/switch`, `cat ${XDG_RUNTIME_DIR}/helm/token`, `curl -s http://127.0.0.1:7700`; ALLOW for `curl -s http://127.0.0.1:8188/object_info`, `curl -s http://localhost:77001/`, `helm-status`. Every spelling the plan's Interfaces line names is refused. (Indirected forms — `PORT=7700; curl …:$PORT` — pass, as expected for a string heuristic the plan itself calls a tripwire.)
- green — runbook accuracy: docs/runbooks/helm.md:44-56. The required paragraph is verbatim from the plan. The added lead sentence checks out against docs/runbooks/helm-v1.md:3-8 (Profile above the nine tiles) and :93-94 (switch-to-configuration `test`, boot menu untouched). Token path `%t/helm/token` = /run/user/<uid>/helm/token per nixosModules/helm.nix:672, so the regex targets the real file.

## Red before green

Kept the tests at HEAD, reverse-applied only the implementation: `git checkout HEAD~1 -- pkgs/dsh-openrouter/hook-guard.py`, then `nix develop -c bats tests/unit/70-dsh-openrouter.bats -f "Helm control|other loopback"`. Decisive output: `not ok 1 hook-guard denies a command aimed at the Helm control port or its token` / `# (from function 'guard_denies' in file tests/unit/70-dsh-openrouter.bats, line 636, in test file tests/unit/70-dsh-openrouter.bats, line 667)` — i.e. the guard emitted nothing for the curl-to-7700 payload, exactly the reason the plan's Step 2 states. `ok 2 hook-guard leaves other loopback ports alone` (the allow case is a regression pin and correctly passes both before and after). Restored with `git checkout HEAD -- …`; `git status --porcelain` empty before every check run.

## Mutation table

| mutation | killed | by |
|---|---|---|
| pkgs/dsh-openrouter/hook-guard.py:72 — port constant `:7700` → `:7701` | yes | bats "hook-guard denies a command aimed at the Helm control port or its token" → not ok |
| pkgs/dsh-openrouter/hook-guard.py:73 — delete the whole `r"\|/run/user/\d+/helm/token"` alternative | NO | none — both tests still ok; the only payload naming that path also contains `127.0.0.1:7700`, so the port alternative masks it |
| pkgs/dsh-openrouter/hook-guard.py:72 — delete the `\|\[::1\]` alternative | NO | none — both tests still ok; no payload uses the `[::1]:7700` spelling the plan's Interfaces line names |
| pkgs/dsh-openrouter/hook-guard.py:74 — delete the `r"\|\$\{?XDG_RUNTIME_DIR\}?/helm/token"` alternative | yes | bats "hook-guard denies a command aimed at the Helm control port or its token" → not ok (second assertion, `cat $XDG_RUNTIME_DIR/helm/token`) |
| pkgs/dsh-openrouter/hook-guard.py:72 — widen the port to `(?:7700\|8188)` (over-deny) | yes | bats "hook-guard leaves other loopback ports alone" → not ok |
| pkgs/dsh-openrouter/hook-guard.py:72 — `\|localhost\|` → `\|Localhost\|` | yes | bats "hook-guard denies a command aimed at the Helm control port or its token" → not ok (third assertion, `wget -qO- localhost:7700/`) |
| pkgs/dsh-openrouter/hook-guard.py:100 — deny reason text replaced with `"nope"` | NO | none — `guard_denies` only asserts a non-empty `permissionDecisionReason`; matches the file's pre-existing convention for all five older deny cases |

## Findings

- **major** `tests/unit/70-dsh-openrouter.bats:667` — Vacuous coverage of the token-path half of the guard. The only assertion that names `/run/user/1000/helm/token` is the curl payload, which also contains `127.0.0.1:7700`; the port alternative matches first, so deleting `r"|/run/user/\d+/helm/token"` (hook-guard.py:73) leaves both new tests green. Half of what the task's own title promises ("…and its token") is therefore unpinned: a later refactor can drop the literal-path rule silently, and `cat /run/user/1000/helm/token` — the exact read that hands any uid-1000 process the switch credential — would go from denied to allowed with no test noticing. Measured: mutation 2 survived. **Fix:** Split the first assertion so one payload exercises the path alone, e.g. add `guard_denies "$(guard_payload bash '{"command":"cat /run/user/1000/helm/token"}')"` (keep the combined curl case as the realistic one). Re-run the mutation to confirm it now fails.
- **minor** `tests/unit/70-dsh-openrouter.bats:666` — The `[::1]:7700` and `0.0.0.0:7700` spellings are unasserted. `[::1]:7700` is named explicitly in the plan's Interfaces line; deleting `|\[::1\]` from hook-guard.py:72 keeps both tests green (mutation 3 survived). The implementation is correct — a direct probe denies `curl -s http://[::1]:7700/` — but nothing holds it there. **Fix:** Add `guard_denies "$(guard_payload bash '{"command":"curl -s http://[::1]:7700/state"}')"` to the deny case.
- **minor** `pkgs/dsh-openrouter/hook-guard.py:100` — The deny reason string specified by the plan ("the Helm control port and its token are refused (an operator action)") is not asserted anywhere; replacing it with "nope" keeps both tests green (mutation 7 survived). The reason is what `dsh-openrouter --denials` shows the operator, so it is the audit's only human-readable field. Note this matches the file's existing convention — none of the five older deny cases assert their reason — so it is a pre-existing pattern, not a regression introduced here. **Fix:** Optional, and worth doing file-wide rather than for this case alone: extend `guard_denies` to take an optional expected substring for `permissionDecisionReason`.
- **minor** `docs/runbooks/helm.md:47` — Wording: "the buttons, banners and guarantees are `docs/runbooks/helm-v1.md`" — a list of things is equated with a file path. Reads as a dropped preposition. **Fix:** "…the buttons, banners and guarantees are in `docs/runbooks/helm-v1.md`."

## Deviations

Three declared in FACTORY-NOTES, all accepted. (1) Helper names: the plan's snippet used `assert_denied`/`assert_allowed` and a `{"tool_name":"Bash"}` payload; neither exists — the file's helpers are `guard_payload`/`guard_denies`/`guard_allows` and the guard matches lowercase `"bash"` (hook-guard.py:232), so the plan's literal text could not have run. Using the file's helpers is the correct reading, and the implementer said so. (2) `## The Profile card` section created in helm.md because the file had none; the plan said "one paragraph under the Profile card". The required paragraph is verbatim; the one added lead sentence is accurate against helm-v1.md:3-8 and :93-94 and deliberately avoids touching the "nine tiles" heading E5 will rename. Accepted. (3) `-f "Helm control"` matched only the deny test during the red step, so the red proof covered one test rather than two — I re-ran the red step myself with `-f "Helm control|other loopback"` and confirmed both the failure and that the allow case is a genuine pass, not a filter artefact. Undeclared but harmless: the regex also covers `0.0.0.0:7700`, a superset of the plan's three spellings. No file outside `touches` was edited.
