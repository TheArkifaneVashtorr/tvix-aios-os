# Phase 1 acceptance — what you run

One command, YubiKey A inserted, from the repo root:

    nix develop -c tests/acceptance/phase1.sh

It will: encrypt a throwaway basket → ask sudo to mount it decrypted into
tmpfs (touch the YubiKey when it blinks) → tear the mount down and prove it
is gone → ask you to unplug the key and prove decryption then fails.

Expected final line: `PHASE 1 ACCEPTANCE: PASS`.

If you see FAIL anywhere, copy the output back to Claude; nothing on your
system is left mounted or decrypted either way (everything lives in a
temp dir that is deleted on exit, and the tmpfs is torn down by the test).

Notes for later phases, no action now: tmpfs pages can reach swap; core
runs no swap today, and a swap-free (or encrypted-swap) assertion becomes
part of the basketStore NixOS module in Phase 3/4.
