{ pkgs, proton-drive-cli-pkg, ... }:

{
  environment.systemPackages = with pkgs; [
    # Proton suite (official apps). rclone retired 2026-09-02: Proton's
    # anti-abuse wall blocks the unofficial bridge (Code 9001); the official
    # CLI (services.proton-backup.cliPackage) is the sanctioned transport.
    protonmail-desktop
    proton-pass
    protonmail-bridge
  ];

  # Daily client-side-encrypted backup: restic -> /var/lib/restic/core, then
  # the official Proton Drive CLI mirrors the ciphertext to
  # /my-files/backups/core (nixosModules/protonBackup.nix; runbook:
  # docs/runbooks/backup.md). What persists where: local repo + remote
  # mirror are ciphertext; the only key is ~/.config/restic/password (Proton
  # Pass + paper); the backup never contains that file.
  #
  # Host-wiring plan Task 1 / docs/decisions/2026-09-02-memory-per-flake.md:
  # ~/flakes (nixos-agent-env's sibling repos, ~/flakes/gaming pinned as this
  # flake's `gaming` input) and ~/strategy join the backup, plus each flake's
  # own Claude memory directory -- separate per flake, never shared, never
  # linked into any flake (see the decision doc).
  services.proton-backup = {
    enable = true;
    user = "dalhaka";
    cliPackage = proton-drive-cli-pkg;
    paths = [
      "/home/dalhaka/nixos-agent-env"
      "/etc/nixos"
      "/var/lib/baskets/store"
      "/home/dalhaka/.claude/projects/-home-dalhaka/memory"
      "/home/dalhaka/.claude/projects/-home-dalhaka-nixos-agent-env/memory"
      "/home/dalhaka/.config/basket"
      "/home/dalhaka/flakes"
      "/home/dalhaka/strategy"
      "/home/dalhaka/.claude/projects/-home-dalhaka-flakes-gaming/memory"
      "/home/dalhaka/.claude/projects/-home-dalhaka-flakes-media/memory"
      "/home/dalhaka/.claude/projects/-home-dalhaka-strategy/memory"
      "/var/lib/evidence"
      # The lane ledgers are the audit records worth the backup (decision
      # 2026-09-05-audit-logs-backed-up.md); empty dirs back up fine -- the
      # exit-3 failure mode is a missing path, not an empty one. Each lane's
      # jobs/ and results/ are excluded below. The broker audit logs never
      # leave the machine (decision addendum): /var/lib/egress-broker is NOT
      # a path.
      "/var/lib/lanes"
    ];

    # A definition replaces the module's default exclude list, so the three
    # defaults are restated. The two new patterns keep each lane's job payloads
    # and model output out of the backup, leaving only its ledger.jsonl under
    # /var/lib/lanes/* (docs/decisions/2026-09-05-audit-logs-backed-up.md).
    exclude = [
      "**/.pytest_cache"
      "**/.ruff_cache"
      "/home/*/.cache"
      "/var/lib/lanes/*/jobs"
      "/var/lib/lanes/*/results"
    ];
  };

  # Pre-create the three per-flake memory directories (and their parents) so
  # a folder never opened by a Claude session cannot make restic report a
  # missing path. 0700 dalhaka:users, deliberately operator-only -- this is
  # NOT a claim that it matches how the two pre-existing memory dirs above
  # (-home-dalhaka and -home-dalhaka-nixos-agent-env) are set up: those are
  # 0755 today and are left alone here (audit F16).
  systemd.tmpfiles.rules = [
    "d /home/dalhaka/.claude/projects/-home-dalhaka-flakes-gaming 0700 dalhaka users -"
    "d /home/dalhaka/.claude/projects/-home-dalhaka-flakes-gaming/memory 0700 dalhaka users -"
    "d /home/dalhaka/.claude/projects/-home-dalhaka-flakes-media 0700 dalhaka users -"
    "d /home/dalhaka/.claude/projects/-home-dalhaka-flakes-media/memory 0700 dalhaka users -"
    "d /home/dalhaka/.claude/projects/-home-dalhaka-strategy 0700 dalhaka users -"
    "d /home/dalhaka/.claude/projects/-home-dalhaka-strategy/memory 0700 dalhaka users -"
  ];
}
