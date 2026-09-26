{
  config,
  lib,
  pkgs,
  claude-desktop,
  ...
}:
let
  cfg = config.services.cowork;
  netnsPath = "/var/run/netns/egress-${cfg.brokerInstance}";
  waypipeSocket = "/run/claude-gui/wp.sock";
  basketRunPath = "/run/baskets/${cfg.basket}";

  brokerExists = cfg.enable && config.services.egress-broker.instances ? ${cfg.brokerInstance};
  broker =
    if brokerExists then config.services.egress-broker.instances.${cfg.brokerInstance} else null;
  proxyUrl =
    if broker == null then null else "http://${broker.hostAddress}:${toString broker.listenPort}";

  # commandLineArgs is a claude-desktop package.nix build argument (a single
  # string prepended verbatim to the Electron wrapper's --add-flags), not a
  # programs.claude-desktop module option (verified against the pin: only
  # `enable`, `package`, `cowork.enable`, `cowork.kvmUsers` exist there) --
  # so the proxy is wired via a package override, not a module option.
  claudeDesktopPkg =
    if proxyUrl == null then
      null
    else
      claude-desktop.packages.${pkgs.stdenv.hostPlatform.system}.default.override {
        commandLineArgs = "--proxy-server=${proxyUrl} --ozone-platform=wayland --disable-gpu";
      };

  # Idempotent per-start: delete-then-add so re-running (every service start)
  # never fails on an already-present cert. Electron/Chromium reads the NSS
  # sql db under $HOME/.pki/nssdb for its own TLS trust (verified: no
  # NODE_EXTRA_CA_CERTS-equivalent for the Electron shell itself -- that env
  # var only reaches the sandboxed harness via managed-settings' env block).
  # NEVER an --ignore-certificate-errors flag: this is the actual trust path.
  importBrokerCa = pkgs.writeShellScript "cowork-import-broker-ca" ''
    set -euo pipefail
    ca="/var/lib/egress-broker/${cfg.brokerInstance}/ca/ca.pem"
    if [ ! -s "$ca" ]; then
      echo "cowork: broker CA not exported yet at $ca -- is egress-broker-${cfg.brokerInstance} healthy?" >&2
      exit 1
    fi
    # The NSS db holds ONLY our broker CA, so rebuild it from scratch every
    # start: a half-initialized db makes certutil prompt in a retry loop
    # (90s CPU spin until unit timeout — field bug 2026-09-02). No error
    # swallowing: any failure here must kill the start loudly.
    rm -rf "$HOME/.pki/nssdb"
    mkdir -p "$HOME/.pki/nssdb"
    nssdb="sql:$HOME/.pki/nssdb"
    ${pkgs.nss.tools}/bin/certutil -N -d "$nssdb" --empty-password </dev/null
    ${pkgs.nss.tools}/bin/certutil -A -n egress-broker-ca -t "CT,C,C" \
      -i "$ca" -d "$nssdb" </dev/null
  '';

  # The basket is mounted by the operator's cowork-up (YubiKey in hand,
  # Task 3), never at boot -- fail loudly rather than let Cowork start
  # against an empty/missing workspace directory.
  checkBasketMounted = pkgs.writeShellScript "cowork-check-basket" ''
    set -euo pipefail
    if ! ${pkgs.util-linux}/bin/mountpoint -q "${basketRunPath}"; then
      echo "cowork: basket '${cfg.basket}' is not mounted at ${basketRunPath} -- run cowork-up first (needs the YubiKey)" >&2
      exit 1
    fi
  '';
  # Phase 4b rescope: Cowork gets the SAME rendered managed-settings JSON
  # claudeManagedSettings.nix would otherwise write machine-wide, but
  # provisioned as claude-app's own user-scope ~/.claude/settings.json
  # instead. Per docs/research-2026-09-02-phase4.md, Cowork reads
  # proxy/strictness config from managed settings AND from the running
  # user's ~/.claude/settings.json, and per the derisk managed-settings
  # research the security-relevant keys (env masking, strictAllowlist,
  # sandbox.network, the three allowManaged*Only lock keys) are honored only
  # from user/managed/CLI scope -- a project-level .claude/settings.json
  # (e.g. one planted inside the workspace basket) cannot override them. So
  # this file confers the same brief §7 Phase 4 guarantee while confining
  # the blast radius to claude-app instead of every Claude Code session on
  # the host (see hosts/core/default.nix for why enable stays false there).
  claudeManagedSettingsCfg = config.services.claude-managed-settings;

  # Login handoff: the app xdg-opens claude.com auth URLs in an external
  # browser (field log 2026-09-02). Inside the netns that browser must exist
  # and speak through the broker. xdg-open probes `chromium-browser` first,
  # so ship a proxied wrapper under exactly that name; it renders through the
  # same waypipe relay as the app.
  # -u LD_LIBRARY_PATH: the Electron wrapper (claude-desktop, invoking
  # xdg-open -> this script) exports LD_LIBRARY_PATH from its OWN nixpkgs
  # (glibc 2.42 world); host chromium is built against glibc 2.40 and
  # inheriting that var makes it abort with
  # "GLIBC_ABI_DT_X86_64_PLT not found" (reproduced 2026-09-02, fixed by
  # unsetting it -- verified with `chromium --version`).
  bubbleBrowser = pkgs.writeShellScriptBin "chromium-browser" ''
    exec ${pkgs.coreutils}/bin/env -u LD_LIBRARY_PATH ${pkgs.chromium}/bin/chromium \
      --proxy-server=${if proxyUrl == null then "" else proxyUrl} \
      --ozone-platform=wayland --disable-gpu "$@"
  '';

  # Session keyring so the app can persist its sign-in (org.freedesktop.secrets
  # was failing; the app warned logins would not be saved — field log
  # 2026-09-02). The login keyring auto-creates/unlocks with an empty password:
  # its at-rest protection is the claude-app home's permissions for now;
  # relocating it into the sealed basket is queued for the workspaces phase.
  coworkLaunch =
    if claudeDesktopPkg == null then
      null
    else
      pkgs.writeShellScript "cowork-launch" ''
        printf "" | ${pkgs.gnome-keyring}/bin/gnome-keyring-daemon --unlock --components=secrets >/dev/null 2>&1 || true
        keyring_env=$(${pkgs.gnome-keyring}/bin/gnome-keyring-daemon --start --components=secrets 2>/dev/null) || true
        if [ -n "$keyring_env" ]; then
          eval "$keyring_env"
          export GNOME_KEYRING_CONTROL
        fi
        exec ${pkgs.waypipe}/bin/waypipe --no-gpu --socket ${waypipeSocket} server -- ${claudeDesktopPkg}/bin/claude-desktop
      '';
in
{
  imports = [
    claude-desktop.nixosModules.default
    ./claudeManagedSettings.nix
  ];

  options.services.cowork = {
    enable = lib.mkEnableOption "Claude Cowork: dedicated UID, broker netns, waypipe display, one rw basket";

    basket = lib.mkOption {
      type = lib.types.str;
      default = "cowork-workspace";
      description = "services.baskets.definitions name mounted as Cowork's only workspace (rw).";
    };

    brokerInstance = lib.mkOption {
      type = lib.types.str;
      default = "cowork";
      description = "services.egress-broker.instances name providing Cowork's netns and proxy/CA settings.";
    };

    shareGroup = lib.mkOption {
      type = lib.types.str;
      default = "claude-gui";
      description = "Group shared between claude-app and operatorUser for the waypipe socket directory.";
    };

    operatorUser = lib.mkOption {
      type = lib.types.str;
      default = "operator";
      description = "The human user whose graphical session runs the waypipe client.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = config.services.egress-broker.instances ? ${cfg.brokerInstance};
        message = "services.cowork.brokerInstance '${cfg.brokerInstance}' has no matching services.egress-broker.instances entry";
      }
    ];

    services = {
      # Points claudeManagedSettings.nix's generator at the SAME broker
      # instance Cowork itself uses, so settingsFile's proxy/CA env matches
      # the netns Cowork actually runs in. mkDefault so a host can repoint
      # it; NOT setting `enable` here (stays false, i.e. no machine-wide
      # /etc/claude-code/managed-settings.json write) -- only settingsFile is
      # consumed, below.
      claude-managed-settings.brokerInstance = lib.mkDefault cfg.brokerInstance;

      # Default broker instance for Cowork's netns + proxy (plan Task 2
      # bullet 7); mkDefault so a host can override any field (e.g.
      # hosts/core keeps this, but a different deployment could repoint it).
      egress-broker.instances.${cfg.brokerInstance} = lib.mkDefault {
        hostAddress = "10.100.1.1";
        namespaceAddress = "10.100.1.2";
        listenPort = 3129;
        allow = [
          "api.anthropic.com"
          "claude.ai"
          "statsig.anthropic.com"
          "assets-proxy.anthropic.com"
          "claude.com"
          # Cowork VM image (rootfs.img ~1.3 GB) + Claude Code harness bundle;
          # from audit-log denies 2026-09-02 (96 CONNECT denies at every
          # session start -- see docs/research-2026-09-02-cowork-sending-hang.md).
          "downloads.claude.ai"
        ];
      };

      baskets = {
        definitions.${cfg.basket} = {
          classification = "permitted";
          mount = "/data/cowork";
          access = "rw";
        };
        agents.cowork = {
          baskets = [ cfg.basket ];
          egress = "broker:${cfg.brokerInstance}";
          placement = "host";
        };
      };
    };

    programs = {
      # The upstream module is imported only for its Cowork plumbing (the
      # /usr/share/OVMF + /usr/libexec/virtiofsd symlinks, vhost_vsock, the
      # kvm group). Its one other effect is `environment.systemPackages =
      # [ cfg.package ]`, which would put the proxied app -- launcher entry
      # and all -- into every user's PATH and the GNOME app menu. Field bug
      # 2026-09-02 19:20: the operator clicked that menu entry, got a second
      # Claude Desktop running as themselves on the HOST (full home, no
      # netns), proxied at the broker but without the broker CA
      # (ERR_CERT_AUTHORITY_INVALID). Only cowork.service may run the app,
      # so hand the module an empty package; cowork-launch references the
      # real proxied build directly.
      claude-desktop = {
        enable = true;
        cowork.kvmUsers = [ "claude-app" ];
        package = pkgs.emptyDirectory;
      };

      # The desktop app downloads a generic-Linux Claude Code binary
      # (claude-code-releases/.../linux-x64/claude, dynamically linked
      # against glibc only: librt libc libpthread libdl libm) and spawns it
      # ON THE HOST for every session; the VM is a separate sandbox. NixOS
      # refuses such binaries without the nix-ld loader shim -- field bug
      # 2026-09-02: every session died with exit 127 "Could not start
      # dynamically linked executable ... stub-ld" and the UI said "Claude
      # Code crashed". Verified before enabling: the exact installed binary
      # (sha256 71d5bfd7...) prints "2.1.255 (Claude Code)" when run through
      # glibc's real ld-linux, which is all nix-ld provides. nix-ld is not a
      # privilege boundary (static binaries and patchelf already run), so
      # this widens nothing the netns/broker layer relies on.
      nix-ld.enable = true;
    };

    users = {
      groups = {
        claude-app = { };
        ${cfg.shareGroup} = { };
      };
      users.claude-app = {
        isSystemUser = true;
        group = "claude-app";
        home = "/var/lib/claude-app";
        createHome = true;
        extraGroups = [
          "kvm"
          cfg.shareGroup
        ];
      };
    };

    systemd = {
      tmpfiles.rules = [
        "d /run/claude-gui 0770 root ${cfg.shareGroup} -"
        # User-scope managed-settings lockdown (Phase 4b rescope; see the
        # let-binding comment above): claude-app's own ~/.claude/settings.json,
        # a symlink into the Nix store so it's read-only and always matches
        # the current generation. "L+" replaces any pre-existing path there
        # on every activation/boot -- it must never drift from what this
        # module renders. No secrets in the JSON, so a plain store symlink
        # (world-readable store path) is fine.
        "d /var/lib/claude-app/.claude 0750 claude-app claude-app -"
        "L+ /var/lib/claude-app/.claude/settings.json - - - - ${claudeManagedSettingsCfg.settingsFile}"
      ];

      # Operator-started only (cowork-up needs the YubiKey to mount the
      # basket) -- deliberately not wantedBy anything.
      services.cowork = {
        description = "Claude Cowork (broker-netns-confined, waypipe display)";
        requires = [ "egress-broker-${cfg.brokerInstance}.service" ];
        after = [ "egress-broker-${cfg.brokerInstance}.service" ];
        # dbus-run-session execs `dbus-daemon` from PATH (field bug: exit 127).
        # bubbleBrowser: xdg-open finds chromium-browser for login handoff.
        path = [
          pkgs.dbus
          bubbleBrowser
        ];
        environment = {
          HOME = "/var/lib/claude-app";
          # waypipe server sets WAYLAND_DISPLAY for the child it execs itself
          # (verified: `waypipe --help` / man page -- server mode "sets up
          # its own Wayland compositor socket"); XDG_RUNTIME_DIR is what
          # needs to be ours so that socket (and waypipe's own state) lands
          # under the unit's RuntimeDirectory instead of a shared default.
          XDG_RUNTIME_DIR = "/run/claude-app";
          # The desktop app resolves its session environment by running
          # "$SHELL -l -i -c env" (CLAUDE_DESKTOP_RESOLVING_ENVIRONMENT).
          # Without this, systemd exports the claude-app system user's
          # actual login shell -- nologin -- so that probe failed at every
          # session start (journal: "Attempted login by UNKNOWN (UID:
          # 991)"). /bin/sh always exists on NixOS (environment.binsh).
          SHELL = "/bin/sh";
        };
        serviceConfig = {
          Type = "simple";
          User = "claude-app";
          Group = "claude-app";
          SupplementaryGroups = [
            "kvm"
            "video"
            "render"
            cfg.shareGroup
          ];
          NetworkNamespacePath = netnsPath;
          RuntimeDirectory = "claude-app";
          RuntimeDirectoryMode = "0700";
          WorkingDirectory = "/var/lib/claude-app";
          # ExecStartPre runs with the same User/Group as ExecStart, except
          # entries prefixed "+" which run privileged. The first entry
          # re-asserts the lockdown symlink on EVERY start: claude-app owns
          # its ~/.claude dir, so a prior session could have replaced
          # settings.json — tmpfiles alone would only fix that at boot
          # (review finding, wf_7f70131b-d9a).
          ExecStartPre = [
            "+${pkgs.coreutils}/bin/ln -sfn ${claudeManagedSettingsCfg.settingsFile} /var/lib/claude-app/.claude/settings.json"
            # A crashed run leaves Chromium's single-instance lock behind;
            # the next launch then defers to the dead instance and exits 0
            # with no window (field bug 2026-09-02). Clear it every start.
            "${pkgs.coreutils}/bin/rm -f /var/lib/claude-app/.config/Claude/SingletonLock /var/lib/claude-app/.config/Claude/SingletonSocket /var/lib/claude-app/.config/Claude/SingletonCookie"
            checkBasketMounted
            importBrokerCa
          ];
          # dbus-run-session: Electron/GTK expect a session bus; a system
          # service has none, and its absence spams errors and destabilizes
          # startup (field log 2026-09-02).
          ExecStart = "${pkgs.dbus}/bin/dbus-run-session -- ${coworkLaunch}";
          Restart = "no";
          NoNewPrivileges = true;
          ProtectSystem = "strict";
          ReadWritePaths = [
            "/var/lib/claude-app"
            basketRunPath
            # PrivateTmp's mount still inherits ProtectSystem=strict's
            # read-only default here; dbus-daemon binds its socket in /tmp
            # (field bug 2026-09-02: "Read-only file system").
            "/tmp"
          ];
          DeviceAllow = [
            "/dev/kvm rw"
            "/dev/vhost-vsock rw"
            "char-drm rw"
          ];
          # Overlays the broker's CA-augmented bundle (egressBroker.nix's
          # ExecStartPost) onto the exact host path the Cowork VM helper
          # reads (readSystemCACertificates / installHostCACertificates,
          # docs/research-2026-09-02-cowork-sending-hang.md) before pushing
          # certs into the guest's trust store. Scoped to THIS unit's own
          # mount namespace only (ProtectSystem=strict above already gives
          # cowork.service a private view of /etc) -- the host's real
          # /etc/ssl/certs/ca-certificates.crt, and every other unit's view
          # of it, is untouched; security.pki.* is never set. Never a
          # --ignore-certificate-errors bypass: this is the actual trust
          # path, the same as importBrokerCa above for the Electron shell's
          # own NSS db.
          BindReadOnlyPaths = [
            "/var/lib/egress-broker/${cfg.brokerInstance}/ca/ca-bundle.crt:/etc/ssl/certs/ca-certificates.crt"
          ];
        };
      };

      # Operator's session-side waypipe client. ConditionUser scopes this to
      # operatorUser's own `systemd --user` instance (systemd.user.services
      # is otherwise generated for every user's instance identically).
      user.services.cowork-display = {
        description = "waypipe client: display Cowork on the operator desktop";
        partOf = [ "graphical-session.target" ];
        unitConfig.ConditionUser = cfg.operatorUser;
        serviceConfig = {
          # waypipe's client does not unlink its socket when it is killed
          # (cowork-down SIGKILLs its workers); the next start then fails
          # with EADDRINUSE while the stale file still passes cowork-up's
          # "relay socket present" wait, so the confined server connects to
          # nobody (ECONNREFUSED) and the app dies -- field bug 2026-09-02
          # 19:32 (SIGTRAP core). Clear it first; the client recreates it.
          ExecStartPre = "${pkgs.coreutils}/bin/rm -f ${waypipeSocket}";
          ExecStart = "${pkgs.waypipe}/bin/waypipe --no-gpu --socket ${waypipeSocket} client";
          # The socket is created by the operator's user with the manager's
          # default umask (0022 -> 0755): claude-app, a different user, then
          # gets EACCES on connect and the app dies (field bug 2026-09-02
          # 19:36). The access boundary is the socket DIRECTORY (0770
          # root:shareGroup, see tmpfiles above), so the socket itself may be
          # world-writable; nobody outside shareGroup can reach it.
          UMask = "0000";
          Restart = "no";
        };
      };
    };
  };
}
