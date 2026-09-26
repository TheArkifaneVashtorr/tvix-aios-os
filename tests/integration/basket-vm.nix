{
  pkgs,
  basketPackage,
}:
pkgs.testers.runNixOSTest {
  name = "basket";
  nodes.machine =
    { pkgs, ... }:
    {
      environment.systemPackages = [
        basketPackage
        pkgs.age
        pkgs.jq
        pkgs.util-linux
      ];
    };
  testScript = ''
    ID = "work-notes"
    SENTINEL = "SENTINEL-PLAINTEXT-7f3a"
    STORE = "/var/lib/baskets"
    RT = "/run/baskets"
    ENTRY = f"{STORE}/{ID}"
    MNT = f"{RT}/{ID}"
    STAGING = f"{RT}/.basket-tmpfs-{ID}"

    def sentinel_files(include_run):
        # The negative half of invariant 1: no plaintext marker
        # SENTINEL-PLAINTEXT-7f3a on any writable persistent filesystem. While
        # mounted /run is excluded (the material legitimately lives there on the
        # tmpfs); after teardown it is included, so the second call proves
        # teardown left nothing behind anywhere. /nix is always excluded: the
        # test driver itself copies this testScript (which names the sentinel as
        # a literal) into /nix/store, a read-only store the basket never writes.
        args = "--exclude-dir=proc --exclude-dir=sys --exclude-dir=dev --exclude-dir=nix"
        if not include_run:
            args += " --exclude-dir=run"
        rc, out = machine.execute(
            f"grep -rl '{SENTINEL}' / {args} 2>/dev/null"
        )
        return [l for l in out.splitlines() if l.strip()]

    # Fixtures: a software age identity, its recipient, a source directory whose
    # one file carries the plaintext marker SENTINEL-PLAINTEXT-7f3a, and a
    # manifest with examples/manifest.json's four keys (id, classification,
    # mount, access).
    machine.succeed("mkdir -p /root/src /var/lib/baskets")
    machine.succeed("age-keygen -o /root/id.txt 2>/dev/null")
    machine.succeed("age-keygen -y /root/id.txt > /root/recipients.txt")
    machine.succeed(f"printf '{SENTINEL}\\nvm-note\\n' > /root/src/note.txt")
    machine.succeed(
        "cat > /root/manifest.json <<'EOF'\n"
        '{"id":"work-notes","classification":"local-only","mount":"/data/notes","access":"ro"}' + "\n"
        "EOF\n"
    )

    # 1. encrypt writes only ciphertext to the store: the sentinel never
    #    appears in the on-disk payload. The source plaintext is then removed,
    #    so the only plaintext left is whatever the mount later decrypts.
    machine.succeed(
        f"basket encrypt /root/src --manifest /root/manifest.json "
        f"--recipients /root/recipients.txt --store {STORE}"
    )
    machine.succeed(
        f"test \"$(grep -c '{SENTINEL}' {ENTRY}/payload.tar.age)\" = 0"
    )
    machine.succeed("rm -rf /root/src")

    # 7. drop page cache so a hit in it cannot mask a write to a persistent fs.
    machine.succeed("sync")
    machine.succeed("echo 3 > /proc/sys/vm/drop_caches")

    # 2. mount succeeds; the target is tmpfs; the two tmpfs-backed entries are
    #    the hidden staging tmpfs and its bind at $mnt -- a bind of a tmpfs is
    #    reported as tmpfs, so the count is exactly two and no third tmpfs.
    machine.succeed(
        f"basket mount {ENTRY} --identity /root/id.txt --runtime-dir {RT}"
    )
    machine.wait_until_succeeds(f"mountpoint -q {MNT}")
    fstype = machine.succeed(f"findmnt -no FSTYPE --target {MNT}").strip()
    assert fstype == "tmpfs", f"expected FSTYPE tmpfs, got {fstype}"
    machine.succeed(
        "test \"$(findmnt -no TARGET -t tmpfs | grep -c baskets)\" = 2"
    )

    # 3. while mounted: no plaintext on any persistent filesystem (negative),
    #    and the sentinel is inside the mount (positive control -- the negative
    #    grep is not vacuous).
    leaks = sentinel_files(include_run=False)
    assert not leaks, (
        f"expected 0 files carrying the sentinel {SENTINEL} outside /run, "
        f"got {len(leaks)}: {leaks}"
    )
    note = machine.succeed(f"grep -c '{SENTINEL}' {MNT}/note.txt || true").strip()
    assert note == "1", f"expected the sentinel inside the mount, got {note}"

    # 4. lock then verify: the at-rest store still matches its lock.
    machine.succeed(f"basket lock {STORE} --out {STORE}/baskets.lock")
    machine.succeed(f"basket verify {STORE} --lock {STORE}/baskets.lock")

    # 5. teardown unmounts and removes both the mount and the staging directory,
    #    and then nothing anywhere (including /run) carries the sentinel.
    machine.succeed(f"basket teardown {ID} --runtime-dir {RT}")
    rc, _ = machine.execute(f"findmnt --target {MNT}")
    assert rc != 0, f"expected {MNT} not to be a mountpoint after teardown"
    rc, _ = machine.execute(f"test -e {MNT}")
    assert rc != 0, f"expected {MNT} to be removed after teardown"
    rc, _ = machine.execute(f"test -e {STAGING}")
    assert rc != 0, f"expected {STAGING} to be removed after teardown"
    leaks_after = sentinel_files(include_run=True)
    assert not leaks_after, (
        f"expected 0 files carrying the sentinel {SENTINEL} after teardown, "
        f"got {len(leaks_after)}: {leaks_after}"
    )

    # 6. no swap is active (basket doctor demands it), so paging cannot push
    #    tmpfs pages onto disk and undercut the tmpfs-only claim.
    machine.succeed("test \"$(swapon --show | wc -l)\" = 0")
  '';
}
