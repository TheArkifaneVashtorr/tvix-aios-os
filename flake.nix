{
  description = "NixOS agent environments with encrypted data baskets";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/34ab99075ac4f7e40cf037eef32cb1c360bb85e9";
    nixpkgs-host.url = "github:NixOS/nixpkgs/a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4";
    # NOTE (deviation from plan Step 1): llm-agents.inputs.nixpkgs.follows =
    # "nixpkgs-host" is NOT set. llm-agents' package set is built as one
    # mutually-recursive callPackages call, so evaluating even a single
    # package (claude-code) forces evaluation of its siblings (e.g.
    # agent-browser), which needs `pnpmConfigHook`. The nixpkgs-host pin
    # (a5cc6f2c37bf, 2026-09-03) does carry `pnpmConfigHook`
    # (pnpm-config-hook), but claude-code is pulled from llm-agents' own
    # pinned nixpkgs instead -- kept unfollowed because llm-agents' own
    # nixpkgs carries the unfree allowance and the rev its lock tested. A
    # foreign-pkgs systemPackages entry is a normal, supported pattern.
    llm-agents.url = "github:numtide/llm-agents.nix/06830d044f23ec9bc55cec62771122d2941c634d";
    claude-desktop.url = "github:nmcbride/claude-desktop-nix/6f8ddddf46a9ca42157f6a52b934153e26ee3146";

    # OS2 (2026-09-22-tvix-aios-step1): the tvix fork, an untouched upstream
    # mirror consumed for its crates (nix-compat, tvix-eval) as path
    # dependencies of the root Cargo workspace (pkgs/aiosd/default.nix).
    # `flake = false`: the fork has no flake.nix. Pinned to one commit; its
    # lock node is written from a local prefetch's narHash (docs/runbooks/
    # aios.md), which nix resolves from the store without reaching GitHub.
    tvix-aios = {
      url = "github:TheArkifaneVashtorr/tvix-aios/9fbca101331eecbf5c1cd44861f3d24aff101b82";
      flake = false;
    };

    # US1 (plan 2026-09-24-strict-user-spaces-1a.md): home-manager, the user
    # side's declarer, pinned to release-26.05 (spec §3.2). "Following
    # nixpkgs" here means the host's own pin: this flake's nixpkgs for the
    # host is the separate `nixpkgs-host` input (§2 fact 2, F5), so the
    # follows points there, keeping one package set for host and homes
    # alike. The lock node is written by hand from the prefetch JSON
    # (docs/runbooks/aios.md, the F19 recipe); nix resolves it from the
    # store without ever reaching GitHub.
    home-manager = {
      url = "github:nix-community/home-manager/a6631107a83ceab5872f298a2ea710859c80c4cb";
      inputs.nixpkgs.follows = "nixpkgs-host";
    };

    # SG1 (plan 2026-09-24-strict-user-spaces-1a.md): microvm.nix, the seat
    # guest's hypervisor backend, pinned (spec §3.3 a) and following
    # nixpkgs-host like home-manager, keeping one package set for host and
    # guest alike. The backend itself is read from the ledger at evaluation,
    # never typed into a file (D14). The lock node is written by hand from
    # the prefetch JSON (docs/runbooks/aios.md, the F19 recipe); nix resolves
    # it from the store without ever reaching GitHub.
    microvm = {
      url = "github:astro/microvm.nix/f5dd93cd4305a43ae4e9977549cd0e0c08d2ef82";
      inputs.nixpkgs.follows = "nixpkgs-host";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      nixpkgs-host,
      llm-agents,
      claude-desktop,
      tvix-aios,
      home-manager,
      ...
    }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      # PL5 (2026-09-11-platform.md): the host package set. dsh-harness-src is
      # built on nixpkgs-host (43b, Interface 5) so the sibling's catalog
      # invariants are checked by the same stdenv that builds the host.
      # GN12: media's packages and checks build against this same nixpkgs-host
      # set (43b puts absorbed subsystems on nixpkgs-host) rather than media's
      # now-retired flake/lock. allowUnfree because torch-bin's dependency
      # closure pulls triton-bin (nixpkgs marks it unfreeRedistributable).
      pkgsHost = import nixpkgs-host {
        inherit system;
        config.allowUnfree = true;
      };
      # OS2 (2026-09-22-tvix-aios-step1): the tvix-aios workspace — the export
      # view of this tree, the offline lock generator, the workspace build and
      # the fork source for a hand cargo session (pkgs/aiosd/default.nix).
      aios = import ./pkgs/aiosd {
        inherit pkgs self;
        tvix = tvix-aios;
      };
      basketRuntimeInputs = with pkgs; [
        age
        age-plugin-yubikey
        coreutils
        gnutar
        jq
        util-linux
      ];
      dshHost = pkgs.callPackage ./pkgs/dsh { };
      # The operator's interactive seat for DeepSeek on the host (2026-09-03):
      # the same pinned harness the lane runs, routed straight to OpenRouter.
      dshOpenrouter = pkgs.callPackage ./pkgs/dsh-openrouter { dsh = dshHost; };
      # SA8: the same package with a harness payload bound -- the good fixture
      # (skills/ non-empty) and the broken one (no skills/) -- the seam the
      # build asserts and the wrapper deploys. The broken fixture feeds
      # checks.seat-assertion-negative's payloadAttempt arm.
      dshOpenrouterWithPayload = pkgs.callPackage ./pkgs/dsh-openrouter {
        dsh = dshHost;
        harnessPayload = ./tests/fixtures/harness-payload;
      };
      dshOpenrouterBrokenPayload = pkgs.callPackage ./pkgs/dsh-openrouter {
        dsh = dshHost;
        harnessPayload = ./tests/fixtures/harness-payload-broken;
      };
      # SA8b: two Nix-built negative payloads for the two conjuncts a tracked
      # fixture file cannot express -- git carries no empty directory, so
      # "skills/ present but empty" and "skills/ present, AGENTS.md absent"
      # must be synthesized here rather than checked in as fixture dirs.
      harnessPayloadNoAgents = pkgs.runCommand "harness-payload-no-agents" { } ''
        mkdir -p $out/skills/smoke
        : > $out/skills/smoke/SKILL.md
      '';
      harnessPayloadEmptySkills = pkgs.runCommand "harness-payload-empty-skills" { } ''
        mkdir -p $out/skills
        : > $out/AGENTS.md
      '';
      dshOpenrouterNoAgentsPayload = pkgs.callPackage ./pkgs/dsh-openrouter {
        dsh = dshHost;
        harnessPayload = harnessPayloadNoAgents;
      };
      dshOpenrouterEmptySkillsPayload = pkgs.callPackage ./pkgs/dsh-openrouter {
        dsh = dshHost;
        harnessPayload = harnessPayloadEmptySkills;
      };
      # PL5 (2026-09-11-platform.md): the dsh-harness catalog builder. The
      # sibling ships no flake (A20), so its "build gate" is this derivation:
      # dshHarnessBuilder copies the payload (AGENTS.md, README.md, CHANGELOG.md,
      # skills/) verbatim and enforces the catalog invariants (Interfaces 2-4),
      # exiting non-zero with a `dsh-harness: ...` message on the first
      # violation. checks.dsh-harness-eval and its negative arms invoke this
      # same body, so a mutation is refused by the exact code that ships.
      dshHarnessBuilder = ''
        dshHarnessBuilder() {
          local src="$1" out="$2"
          mkdir -p "$out"
          cp -r "$src"/{AGENTS.md,README.md,CHANGELOG.md,skills} "$out"/
          # Interface 2a: every skills/*/SKILL.md carries a `name:` line whose
          # value equals its directory name (an empty directory has no SKILL.md
          # and is Interface 4's count mismatch, not a missing name).
          for sf in "$src"/skills/*/SKILL.md; do
            [ -f "$sf" ] || continue
            dn="$(basename "$(dirname "$sf")")"
            nv="$(grep '^name: ' "$sf" | head -n1 | sed 's/^name: //' || true)"
            if [ -z "$nv" ]; then
              echo "dsh-harness: skills/$dn/SKILL.md: missing name:" >&2
              exit 1
            fi
            if [ "$nv" != "$dn" ]; then
              echo "dsh-harness: skills/$dn/SKILL.md: name '$nv' != directory '$dn'" >&2
              exit 1
            fi
          done
          # Interface 2b: every such file carries a `description:` line.
          for sf in "$src"/skills/*/SKILL.md; do
            [ -f "$sf" ] || continue
            dn="$(basename "$(dirname "$sf")")"
            if ! grep -q '^description: ' "$sf"; then
              echo "dsh-harness: skills/$dn/SKILL.md: missing description:" >&2
              exit 1
            fi
          done
          # Interface 3: no file under skills/ carries the stripped `superpowers:`
          # prefix.
          hit="$(grep -rl 'superpowers:' "$src"/skills 2>/dev/null | head -n1 || true)"
          if [ -n "$hit" ]; then
            echo "dsh-harness: $hit: superpowers: prefix present" >&2
            exit 1
          fi
          # Interface 4: skills/ holds exactly as many directories as SKILL.md files.
          dirs="$(find "$src"/skills -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
          files="$(find "$src"/skills -name SKILL.md | wc -l | tr -d ' ')"
          if [ "$dirs" != "$files" ]; then
            echo "dsh-harness: $dirs skill dirs, $files SKILL.md files" >&2
            exit 1
          fi
        }
      '';
      dshHarnessSrc =
        pkgsHost.runCommand "dsh-harness-src"
          {
            src = ./pkgs/dsh-harness;
            nativeBuildInputs = [
              pkgsHost.gnugrep
              pkgsHost.findutils
            ];
          }
          ''
            ${dshHarnessBuilder}
            dshHarnessBuilder "$src" "$out"
          '';
      # SB3 + SB1 (2026-09-05-seat-behind-broker): the seat's operator CLI
      # (seat-submit) and the seat@<job> unit entry (seat-run) both come from
      # the one pkgs/seat attrset; packages.seat-submit/seat-run inherit from
      # it below.
      seatTools = pkgs.callPackage ./pkgs/seat { };
      basket = pkgs.writeShellApplication {
        name = "basket";
        runtimeInputs = basketRuntimeInputs;
        text = builtins.readFile ./pkgs/basket/basket.sh;
      };
      protonBackupPush = pkgs.writeShellApplication {
        name = "proton-backup-push";
        runtimeInputs = with pkgs; [
          coreutils
          findutils
          gnugrep
          jq
          util-linux
        ];
        text = builtins.readFile ./pkgs/proton-backup/push.sh;
      };
      lintTools = with pkgs; [
        treefmt
        nixfmt-rfc-style
        shfmt
        shellcheck
        statix
        deadnix
        ruff
        # P12: prettier (format) and oxlint (lint) gate every tracked
        # JavaScript file through treefmt and the lint check (tests/lint/
        # js-lint.sh, run after tests/lint/bats-and-chain.sh below).
        prettier
        oxlint
        # OS2 (2026-09-22-tvix-aios-step1): rustfmt formats every tracked *.rs
        # through treefmt ([formatter.rust]); clippy runs inside the workspace
        # build, where the vendored registry is, never in lint.
        rustfmt
      ];
      # G5: docs/MAP.md's Checks section must equal the flake's real check set.
      checkNamesFile = pkgs.writeText "check-names" (
        nixpkgs.lib.concatMapStrings (n: n + "\n") (builtins.attrNames self.checks.${system})
      );
      brokerPython = pkgs.python3.withPackages (
        ps: with ps; [
          mitmproxy
          pytest
        ]
      );
      helmPython = pkgs.python3.withPackages (ps: [ ps.pytest ]);
      ledgerPython = pkgs.python3.withPackages (ps: [ ps.pytest ]);
      # The data-analysis stack the `data` plugin's skills drive (explore-data,
      # statistical-analysis, create-viz, build-dashboard). It joins the
      # devShell's ONE Python env rather than riding beside it: two
      # python3.withPackages envs in a single mkShell both ship bin/python3 and
      # whichever lands on PATH first shadows the other -- which is why
      # `python3` in this shell was brokerPython's env, with no pandas in it.
      # checks.devshell-python pins both halves.
      dataPythonPackages =
        ps: with ps; [
          duckdb
          matplotlib
          pandas
          plotly
          scipy
          seaborn
        ];
      devPython = pkgs.python3.withPackages (
        ps:
        [
          ps.mitmproxy
          ps.pytest
        ]
        ++ dataPythonPackages ps
      );
      devShellPackages =
        basketRuntimeInputs
        ++ lintTools
        ++ [
          basket
          protonBackupPush
          pkgs.bats
          pkgs.yubikey-manager
          # devPython is a superset of brokerPython and ledgerPython (mitmproxy
          # + pytest); those two stay bound for the checks, which want their own
          # small closures, but the shell carries one env so nothing shadows.
          devPython
          pkgs.zstd
          dshOpenrouter
          # OS2: a hand cargo session (docs/runbooks/aios.md); a seat never runs
          # cargo outside nix, since no crate registry is reachable from a seat.
          pkgs.cargo
          pkgs.rustc
          pkgs.clippy
          # PL16 (brief §2 goal 1): gh reads the OS repo's private GitHub
          # mirror -- Actions runs now, issues/PRs at goal 3. devShell only,
          # never environment.systemPackages: the host closure stays free of
          # it, and the seat@ unit (seatLane.nix) pins GH_CONFIG_DIR at an
          # empty root-owned dir so no seat can resolve the operator's gh
          # identity.
          pkgs.gh
        ];
      helmCollect = pkgs.writeShellApplication {
        name = "helm-collect";
        runtimeInputs = with pkgs; [
          python3
          restic
          git
          systemd
          coreutils
        ];
        # See nixosModules/helm.nix for why /run/current-system/sw/bin is
        # appended here: the drift tile needs `nixos-version` on PATH, and
        # that command reaches PATH only via /run/current-system/sw/bin.
        text = ''
          export PATH="$PATH:/run/current-system/sw/bin"
          export PYTHONPATH=${./pkgs/evidence}''${PYTHONPATH:+:$PYTHONPATH}
          exec python3 ${./pkgs/helm/collect.py} "$@"
        '';
      };
      helmStatus = pkgs.writeShellApplication {
        name = "helm-status";
        runtimeInputs = [ helmCollect ];
        text = ''exec helm-collect --print "$@"'';
      };
      # Helm v1 (plan Task 1): the control backend. serve.py does `import
      # render` (the T1 renderer) and runs with its own directory on sys.path
      # -- `python3 <dir>/serve.py` puts the script's dir first -- so the
      # whole pkgs/helm tree, not just serve.py, must land in the store
      # beside it; a bare ${./pkgs/helm/serve.py} would leave that import
      # unresolved at runtime. The interpolation copies only git-tracked
      # files, which is why render.py must be tracked for this to build.
      helmServe = pkgs.writeShellApplication {
        name = "helm-serve";
        runtimeInputs = [
          pkgs.python3
          pkgs.systemd
        ];
        text = ''exec python3 ${./pkgs/helm}/serve.py "$@"'';
      };
      # Helm v2 API (HM3): like helmServe, api.py `import serve` and
      # discovers its api_*.py route siblings, so the whole pkgs/helm
      # directory must land beside it.
      helmApi = pkgs.writeShellApplication {
        name = "helm-api";
        runtimeInputs = [ pkgs.python3 ];
        text = ''
          # HM8b: api_engage.py's `import evidence` (/v1/engage) needs
          # pkgs/evidence on sys.path, same as helmCollect above (Opus gate
          # docs/reviews/2026-09-16-opus-review-s28hm-HM8.md, MAJOR-1c).
          export PYTHONPATH=${./pkgs/evidence}''${PYTHONPATH:+:$PYTHONPATH}
          exec python3 ${./pkgs/helm}/api.py "$@"
        '';
      };
      # Helm Home (HH1): the raise-key probe. A GTK4 application that asks the
      # xdg-desktop-portal GlobalShortcuts interface for the raise key and
      # records bind/activation/focus as a verdict; later tasks add the
      # a11y probe (HH6) and the shell itself (HH7) to this package.
      helmHome = pkgs.callPackage ./pkgs/helm-home/package.nix { };
      managedSettingsSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.claudeManagedSettings
          (
            { config, ... }:
            {
              boot.loader.grub.enable = false;
              fileSystems."/".device = "none";
              fileSystems."/".fsType = "tmpfs";
              system.stateVersion = "25.11";
              services = {
                egress-broker.instances.cowork = {
                  hostAddress = "10.100.1.1";
                  namespaceAddress = "10.100.1.2";
                  listenPort = 3129;
                  # Derived from allowedDomains rather than a separate
                  # literal, so this test system proves the two lists are
                  # identical by construction -- see checks.managed-settings,
                  # which asserts this equality too (regression guard).
                  allow = config.services.claude-managed-settings.allowedDomains;
                };
                claude-managed-settings = {
                  enable = true;
                  brokerInstance = "cowork";
                };
              };
            }
          )
        ];
      };
      managedSettingsBadSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.claudeManagedSettings
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            services.claude-managed-settings = {
              enable = true;
              brokerInstance = "no-such-instance";
            };
          })
        ];
      };
      coworkEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit claude-desktop; };
        modules = [
          self.nixosModules.basketStore
          self.nixosModules.egressBroker
          self.nixosModules.cowork
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            services.cowork.enable = true;
          })
        ];
      };
      protonBackupEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.protonBackup
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.tester = {
              isNormalUser = true;
              uid = 1000;
            };
            services.proton-backup = {
              enable = true;
              user = "tester";
              paths = [ "/etc" ];
              cliPackage = pkgs.writeShellScriptBin "proton-drive" "true";
            };
          })
        ];
      };
      helmEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          # helm.api's ReadWritePaths names config.services.evidence-store
          # (HM8's engagement ledger), so the fixture must load evidenceStore
          # for that attribute to resolve.
          self.nixosModules.evidenceStore
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            # The fixture names services.helm.operatorUser explicitly (PL18
            # made the module default neutral, "operator"); the module adds
            # that user to the "helm" group -- NixOS requires every
            # users.users entry to resolve isNormalUser xor isSystemUser, so
            # this isolated eval stub (unlike hosts/core, which already
            # declares its operator fully) must declare it too, the same way
            # protonBackupEvalSystem declares "tester" above.
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.helm = {
              enable = true;
              operatorUser = "alice";
              basketPackage = basket;
              api = {
                enable = true;
                links.feed = "http://127.0.0.1:8080/";
              };
            };
          })
        ];
      };
      evidenceEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.evidenceStore
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            # NixOS requires every users.users entry to resolve isNormalUser
            # xor isSystemUser (same reason as helmEvalSystem).
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            # PL18: the module default went neutral ("operator"); the
            # fixture names its own declared user explicitly.
            # Faithful to the host (hosts/core/default.nix sets evidence-store.group
            # = "helm"), so the assert below pins the rendered "helm" group, not the
            # module default "users".
            services.evidence-store = {
              enable = true;
              owner = "alice";
              group = "helm";
            };
          })
        ];
      };
      helmBadSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.helm = {
              enable = true;
              operatorUser = "alice";
              basketPackage = basket;
              listen = "0.0.0.0:7700";
            };
          })
        ];
      };
      # Helm v2 API (HM3): two negative fixtures, one per new assertion. Each
      # sets api.enable and trips exactly one guard -- a non-loopback
      # api.listen, or api.port colliding with the control port.
      helmApiBadListenSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.evidenceStore
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.helm = {
              enable = true;
              operatorUser = "alice";
              basketPackage = basket;
              api = {
                enable = true;
                listen = "0.0.0.0:7710";
              };
            };
          })
        ];
      };
      helmApiBadPortSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.evidenceStore
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.helm = {
              enable = true;
              operatorUser = "alice";
              basketPackage = basket;
              api = {
                enable = true;
                port = 7700;
              };
            };
          })
        ];
      };
      # IS13b: the negative fixture for the lan-site-upstream assertion -- Helm's
      # listen is loopback (so the loopback assertion passes) but the lan-access
      # site "dash" fronts Helm's port under a name other than "helm" with an
      # upstream that is not byte-equal to listen (X1), which the fixed
      # quantifier refuses regardless of the site's name.
      helmLanMismatchSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.helm = {
              enable = true;
              operatorUser = "alice";
              basketPackage = basket;
              listen = "127.0.0.1:7700";
            };
            services.lan-access = {
              enable = true;
              interface = "eth1";
              sites.dash = {
                upstream = "[::1]:7700";
                hashFile = "/var/lib/lan-access/dash.bcrypt";
                user = "alice";
              };
            };
          })
        ];
      };
      # IS13b: X2 -- the same mismatch under a different site name ("helm-page"),
      # proving the fixed assertion is a quantifier over every site rather than
      # a two-name special case.
      helmLanMismatchRenamedSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.helm = {
              enable = true;
              operatorUser = "alice";
              basketPackage = basket;
              listen = "127.0.0.1:7700";
            };
            services.lan-access = {
              enable = true;
              interface = "eth1";
              sites.helm-page = {
                upstream = "[::1]:7700";
                hashFile = "/var/lib/lan-access/helm-page.bcrypt";
                user = "alice";
              };
            };
          })
        ];
      };
      # IS13b: the positive fixture -- a site on Helm's port whose upstream is
      # byte-equal to listen, alongside one on another port (exempt from the
      # port-suffix predicate), both of which the fixed assertion lets through.
      helmLanOkSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.helm = {
              enable = true;
              operatorUser = "alice";
              basketPackage = basket;
              listen = "127.0.0.1:7700";
            };
            services.lan-access = {
              enable = true;
              interface = "eth1";
              sites.dash = {
                upstream = "127.0.0.1:7700";
                hashFile = "/var/lib/lan-access/dash.bcrypt";
                user = "alice";
              };
              sites.other = {
                upstream = "127.0.0.1:9999";
                hashFile = "/var/lib/lan-access/other.bcrypt";
                user = "alice";
              };
            };
          })
        ];
      };
      # Helm v1 control (plan Task 3 / consolidated D1/D2/D3). The positive
      # harness declares one marker-only specialisation "alt" and the fixed
      # literal profiles ["base" "alt"]; every negative harness is a separate
      # system so each fails for exactly one reason.
      helmControlSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          (
            { lib, ... }:
            {
              boot.loader.grub.enable = false;
              fileSystems."/".device = "none";
              fileSystems."/".fsType = "tmpfs";
              system.stateVersion = "25.11";
              users.users.alice = {
                isNormalUser = true;
                uid = 1000;
              };
              security.polkit.enable = true;
              environment.etc."helm/profile".text = "base";
              specialisation.alt.configuration.environment.etc."helm/profile".text = lib.mkForce "alt";
              services.helm = {
                enable = true;
                operatorUser = "alice";
                basketPackage = basket;
                control = {
                  enable = true;
                  profiles = [
                    "base"
                    "alt"
                  ];
                };
              };
            }
          )
        ];
      };
      helmControlBadProfilesSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          (
            { lib, ... }:
            {
              boot.loader.grub.enable = false;
              fileSystems."/".device = "none";
              fileSystems."/".fsType = "tmpfs";
              system.stateVersion = "25.11";
              users.users.alice = {
                isNormalUser = true;
                uid = 1000;
              };
              environment.etc."helm/profile".text = "base";
              specialisation.alt.configuration.environment.etc."helm/profile".text = lib.mkForce "alt";
              services.helm = {
                enable = true;
                operatorUser = "alice";
                basketPackage = basket;
                control = {
                  enable = true;
                  # G1: "nope" is not a declared specialisation.
                  profiles = [
                    "base"
                    "nope"
                  ];
                };
              };
            }
          )
        ];
      };
      helmControlBadEnableSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            environment.etc."helm/profile".text = "base";
            # control.enable without services.helm.enable must be refused.
            services.helm.control.enable = true;
          })
        ];
      };
      helmControlAgentUnitBadSystemA = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.helm
          (
            { lib, ... }:
            {
              boot.loader.grub.enable = false;
              fileSystems."/".device = "none";
              fileSystems."/".fsType = "tmpfs";
              system.stateVersion = "25.11";
              users.users.alice = {
                isNormalUser = true;
                uid = 1000;
              };
              environment.etc."helm/profile".text = "base";
              specialisation.alt.configuration = {
                environment.etc."helm/profile".text = lib.mkForce "alt";
                # D2 "changed": the specialisation edits an egress- agent unit.
                systemd.services.egress-broker-cowork.serviceConfig.Nice = 1;
              };
              services.egress-broker.instances.cowork = {
                hostAddress = "10.100.1.1";
                namespaceAddress = "10.100.1.2";
                listenPort = 3129;
                allow = [ "example.com" ];
              };
              services.helm = {
                enable = true;
                operatorUser = "alice";
                basketPackage = basket;
                control = {
                  enable = true;
                  profiles = [
                    "base"
                    "alt"
                  ];
                };
              };
            }
          )
        ];
      };
      helmControlAgentUnitBadSystemB = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          (
            { lib, ... }:
            {
              boot.loader.grub.enable = false;
              fileSystems."/".device = "none";
              fileSystems."/".fsType = "tmpfs";
              system.stateVersion = "25.11";
              users.users.alice = {
                isNormalUser = true;
                uid = 1000;
              };
              environment.etc."helm/profile".text = "base";
              specialisation.alt.configuration = {
                environment.etc."helm/profile".text = lib.mkForce "alt";
                # D2 "new": an agent-prefixed unit defined as an attrset with
                # no .text. The presence-aware guard must flag it even though
                # a naive (a.text or null) != (b.text or null) would collapse
                # "absent" and "attrset-without-text" into null == null.
                systemd.units."egress-broker-cowork.service" = {
                  enable = false;
                };
              };
              services.helm = {
                enable = true;
                operatorUser = "alice";
                basketPackage = basket;
                control = {
                  enable = true;
                  profiles = [
                    "base"
                    "alt"
                  ];
                };
              };
            }
          )
        ];
      };
      helmControlBadWorkspaceSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            environment.etc."helm/profile".text = "base";
            services.helm = {
              enable = true;
              operatorUser = "alice";
              basketPackage = basket;
              control = {
                enable = true;
                profiles = [ "base" ];
                workspaces."Bad Name".path = "/var/lib/fake";
              };
            };
          })
        ];
      };
      # Helm Home (HH3 / D-H4): the services.helm.home module's fixtures. The
      # positive harness is helmControlSystem's node (polkit, the "alt"
      # specialisation, profiles ["base" "alt"]) plus helmHome and a two-entry
      # flakes list; every negative harness changes exactly one rule so each
      # fails for exactly one reason (E/P/R/S/D -- D-H4's four rules plus the
      # seats enum, which is a type error, not an assertion).
      helmHomeNode =
        { pkgs, lib, ... }:
        {
          boot.loader.grub.enable = false;
          fileSystems."/".device = "none";
          fileSystems."/".fsType = "tmpfs";
          system.stateVersion = "25.11";
          users.users.alice = {
            isNormalUser = true;
            uid = 1000;
          };
          security.polkit.enable = true;
          environment.etc."helm/profile".text = "base";
          specialisation.alt.configuration.environment.etc."helm/profile".text = lib.mkForce "alt";
          services.helm = {
            enable = true;
            operatorUser = "alice";
            basketPackage = basket;
            control = {
              enable = true;
              profiles = [
                "base"
                "alt"
              ];
            };
            home = {
              enable = true;
              package = pkgs.writeShellScriptBin "helm-home" ":";
            };
          };
        };
      helmHomeSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.helmHome
          helmHomeNode
          (_: {
            services.helm.home.flakes = [
              {
                path = "/var/lib/fake-repo";
                profile = "alt";
                seats = [ "deepseek" ];
              }
              { path = "/var/lib/other"; }
            ];
          })
        ];
      };
      helmHomeBadEnableSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.helmHome
          helmHomeNode
          (
            { lib, ... }:
            {
              # (E): home enabled with control off must be refused.
              services.helm.control.enable = lib.mkForce false;
            }
          )
        ];
      };
      helmHomeBadPathSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.helmHome
          helmHomeNode
          (_: {
            # (P): one relative path beside one absolute.
            services.helm.home.flakes = [
              {
                path = "relative/x";
                profile = "alt";
                seats = [ "deepseek" ];
              }
              { path = "/var/lib/other"; }
            ];
          })
        ];
      };
      helmHomeBadProfileSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.helmHome
          helmHomeNode
          (_: {
            # (R): a profile outside the declared [ base alt ].
            services.helm.home.flakes = [
              {
                path = "/var/lib/fake-repo";
                profile = "nope";
                seats = [ "deepseek" ];
              }
              { path = "/var/lib/other"; }
            ];
          })
        ];
      };
      helmHomeBadSeatsSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.helmHome
          helmHomeNode
          (_: {
            # (S): one valid seat beside one invalid -- a type error.
            services.helm.home.flakes = [
              {
                path = "/var/lib/fake-repo";
                profile = "alt";
                seats = [
                  "claude"
                  "gpt"
                ];
              }
              { path = "/var/lib/other"; }
            ];
          })
        ];
      };
      helmHomeBadDuplicateSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.helm
          self.nixosModules.helmHome
          helmHomeNode
          (_: {
            # (D): two entries with the same path (different profiles).
            services.helm.home.flakes = [
              {
                path = "/var/lib/fake-repo";
                profile = "alt";
                seats = [ "deepseek" ];
              }
              {
                path = "/var/lib/fake-repo";
                profile = "base";
              }
            ];
          })
        ];
      };
      laneEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.modelLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.model-lanes.testlane = {
              host = "example.com";
              model = "test/model-flash";
              keyFile = "/var/lib/secrets/testlane-key";
              hostAddress = "10.100.9.1";
              namespaceAddress = "10.100.9.2";
              listenPort = 3199;
              operatorUser = "alice";
            };
          })
        ];
      };
      laneBadSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.modelLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.model-lanes.testlane = {
              host = "example.com";
              model = "test/model-flash";
              keyFile = "/var/lib/secrets/testlane-key";
              hostAddress = "10.100.9.1";
              namespaceAddress = "10.100.9.2";
              listenPort = 3199;
              operatorUser = "alice";
              allowedClasses = [ "local-only" ];
            };
          })
        ];
      };
      # Two negative systems for checks.seat-assertion-negative (SB1): a store
      # path as keyFile (the secret would land in the world-readable store) and
      # a real-looking key merged into the seat@ unit's environment (a seat/
      # agent process must never hold a key -- the broker injects at egress).
      seatBadKeySystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/nix/store/00000000000000000000000000000000-openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
            };
          })
        ];
      };
      seatBadEnvSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
            };
            systemd.services."seat@".environment.OPENROUTER_API_KEY =
              nixpkgs.lib.mkForce "sk-or-v1-real-looking-key-1234567890abcdef";
          })
        ];
      };
      # IS1b: the running-unit cap refuses below 1 at eval. A zero cap would
      # make seat-submit refuse every launch (fail closed) -- this negative
      # system feeds checks.seat-assertion-negative to prove that refusal fires.
      seatMaxUnitsZeroSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              maxUnits = 0;
            };
          })
        ];
      };
      # IS3b: the wave cap itself must be at least 1 at eval. waveJobs = 0
      # derives maxUnits to 1 and satisfies every other assertion -- including
      # the strict maxUnits > waveJobs relation (1 > 0) -- so it evaluates
      # green, yet factory-wave:139-141 rejects a non-positive cap at every
      # dispatch. This negative system feeds checks.seat-assertion-negative to
      # prove the refusal fires.
      seatWaveJobsZeroSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              waveJobs = 0;
            };
          })
        ];
      };
      # IS3b: the positive side of the boundary -- waveJobs = 1 is legitimate
      # (one wave group at a time), derives maxUnits to 2, and must evaluate
      # green. This fixture feeds checks.seat-eval's tryEval so a mutant that
      # writes the assertion as `> 1` instead of `>= 1` fails on it, proving
      # the boundary admits 1 rather than merely being present.
      seatWaveJobsOneSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              waveJobs = 1;
            };
          })
        ];
      };
      # IS20: three negative systems for checks.seat-assertion-negative's new
      # helmApiPort arms (answer 11a) -- the option is refused at eval when it
      # collides with Helm's control page (7700), the broker's own listenPort
      # (3141), or a moved services.helm.port (a second accept at a dport
      # input-seat already handles is unrepresentable).
      #
      # seatHelmPort7700System moves services.helm.port to 7701 so the literal
      # 7700 arm is distinct from the services.helm.port arm: 7700 must be
      # refused as a port even when Helm's page has moved elsewhere (R8's
      # tool-layer refusal of 7700, mirrored at the network half).
      seatHelmPort7700System = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          self.nixosModules.helm
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              helmApiPort = 7700;
            };
            services.helm.port = 7701;
          })
        ];
      };
      seatHelmPortBrokerSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              helmApiPort = 3141;
            };
          })
        ];
      };
      seatHelmPortMovedSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          self.nixosModules.helm
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              helmApiPort = 7701;
            };
            services.helm.port = 7701;
          })
        ];
      };
      # IS20 (answer 11): the positive fixture -- helmApiPort = 7710 evaluates
      # green and feeds checks.seat-eval's fixture arm, which asserts the accept
      # is rendered inside input-seat (scoped to the namespace address, before
      # the drop) and admitted by nixos-fw.
      seatHelmPortSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              helmApiPort = 7710;
            };
          })
        ];
      };
      # IS3: the unit cap must strictly exceed the wave cap by the driver's own
      # slot, so a configuration where maxUnits equals waveJobs (8) is refused
      # at eval -- the collision between the two caps becomes unrepresentable.
      seatMaxUnitsEqWaveSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              maxUnits = 8;
            };
          })
        ];
      };
      # SA4: the port range seat-spool allocates from must hold at least
      # maxUnits ports (decision 13b). A range one port too narrow (8 against
      # the default maxUnits 9) would refuse the last seat the cap admits --
      # the same off-by-one shape IS3 fixed for the caps. This negative system
      # feeds checks.seat-assertion-negative's portRangeAttempt arm to prove
      # the width assertion fires.
      seatPortRangeNarrowSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              portRange = "43210-43217";
            };
          })
        ];
      };
      # SA4: the port range must also lie inside webPortRange, or the UI is
      # allocated a port the output-seat firewall chain drops. 44210-44219 is
      # ten wide (passes the width assertion) but entirely outside the default
      # 43200-43299. This negative system feeds checks.seat-assertion-negative's
      # portRangeOutsideAttempt arm to prove the containment assertion fires.
      seatPortRangeOutsideSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              portRange = "44210-44219";
            };
          })
        ];
      };
      # SA4: the positive side of the width boundary -- a range exactly as wide
      # as maxUnits (43210-43218, nine ports against the default maxUnits 9)
      # must evaluate green. This fixture feeds checks.seat-eval's tryEval so a
      # mutant that writes the width assertion as `>` instead of `>=` fails on
      # it, proving the boundary admits equality rather than merely being
      # present (mirroring seatWaveJobsOneSystem).
      seatPortRangeExactSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.alice = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "alice";
              portRange = "43210-43218";
            };
          })
        ];
      };
      phase3BadSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.basketStore
          self.nixosModules.egressBroker
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            services = {
              egress-broker.instances.work = {
                hostAddress = "10.100.0.1";
                namespaceAddress = "10.100.0.2";
                allow = [ "example.com" ];
              };
              baskets = {
                definitions.notes-local = {
                  classification = "local-only";
                  mount = "/data/notes";
                };
                agents.leaky = {
                  baskets = [ "notes-local" ];
                  egress = "broker:work";
                };
              };
            };
          })
        ];
      };
      # OS10 (plan 2026-09-22-aios-daemon-dispatch; spec 2026-09-22-tvix-aios
      # §2 goal 6, §4): the aios.seats fixtures for
      # checks.aios-classification-negative. The positive system declares a
      # class and a seat that reads it through a declared egress instance;
      # the two negative ones bind an undeclared path into a seat's baskets
      # list (invariant 8) and a local-only class into a seat with an off-box
      # egress (basketStore's A2, the classification assertion).
      aiosSeatBase = _: {
        boot.loader.grub.enable = false;
        fileSystems."/".device = "none";
        fileSystems."/".fsType = "tmpfs";
        system.stateVersion = "25.11";
        aios.egress.work = {
          hostAddress = "10.100.0.1";
          namespaceAddress = "10.100.0.2";
          allow = [ "example.com" ];
        };
      };
      aiosSeatDeclaredSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.aios
          aiosSeatBase
          (_: {
            aios.data.notes = {
              classification = "redacted";
              mount = "/data/notes";
            };
            aios.seats.reader = {
              harness = "dsh";
              role = "implement";
              baskets = [ "notes" ];
              egress = "work";
            };
          })
        ];
      };
      aiosSeatUndeclaredSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.aios
          aiosSeatBase
          (_: {
            aios.seats.leaky = {
              harness = "dsh";
              role = "implement";
              baskets = [ "/data/undeclared/notes" ];
              egress = "work";
            };
          })
        ];
      };
      aiosSeatLocalOnlyOffboxSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.aios
          aiosSeatBase
          (_: {
            aios.data.notes = {
              classification = "local-only";
              mount = "/data/notes";
            };
            aios.seats.leaky = {
              harness = "dsh";
              role = "implement";
              baskets = [ "notes" ];
              egress = "work";
            };
          })
        ];
      };
      # FL1 (plan 2026-09-24-fleet-and-forge.md): the fleet fixtures. The
      # three machines' keys and the deploy key are public test material
      # (F23, generated on the host for this plan; private halves deleted) on
      # TEST-NET-1 addresses -- no real identity, no deny value. mkFleetEval
      # wraps the module in the minimal eval harness every other fixture
      # here uses; the three systems feed checks.fleet-eval and the arms
      # of checks.fleet-assertion-negative.
      fleetFixture = {
        deployKeys = [
          "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBsCvg7ed6UUs7JOwbF9jJQiMok+UFpdq0ZcRRP6jzbf fleet-fixture-deploy"
        ];
        lan = {
          subnet = "192.0.2.0/24";
          gateway = "192.0.2.1";
          nameservers = [ "192.0.2.1" ];
        };
        machines = {
          core.roles = [ "operator" ];
          forge = {
            roles = [ "forge" ];
            address = "192.0.2.10";
            prefix = 24;
            interface = "eth1";
            hostKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILI+XsoX/3cLjEKKe/6FuKD91bemmU/of1raCjTOMQOB";
            efi = true;
            stateVersion = "25.11";
          };
          lab = {
            roles = [ "forge" ];
            address = "192.0.2.11";
            prefix = 24;
            interface = "eth1";
            hostKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHm7m00e2naloG1lBVeaovQtDipZNjtMKtakBm1qVNoI";
            efi = false;
            stateVersion = "25.11";
          };
        };
      };
      mkFleetEval =
        hostName: extra:
        nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [
            self.nixosModules.fleet
            (_: {
              boot.loader.grub.enable = false;
              fileSystems."/".device = "none";
              fileSystems."/".fsType = "tmpfs";
              system.stateVersion = "25.11";
              networking.hostName = hostName;
              fleet = fleetFixture;
            })
            extra
          ];
        };
      fleetEvalCore = mkFleetEval "core" { };
      fleetEvalForge = mkFleetEval "forge" {
        networking.interfaces.eth1.ipv4.addresses = [
          {
            address = "192.0.2.10";
            prefixLength = 24;
          }
        ];
      };
      fleetEvalLab = mkFleetEval "lab" {
        networking.interfaces.eth1.ipv4.addresses = [
          {
            address = "192.0.2.11";
            prefixLength = 24;
          }
        ];
      };
      # FL7 (plan 2026-09-24-fleet-and-forge.md): the mirror fixtures -- the
      # mirror block the operator's core declares (§Operator step 10) on an
      # operator machine (where the module must render the user units) and
      # the identical block on the forge (a deploy-accepting machine, where
      # it must render nothing); runAs names the fixture's own tester user.
      fleetMirrorFixture = {
        machine = "forge";
        repo = "operator/nixos-agent-env.git";
        user = "forgejo";
        keyFile = "/home/tester/.ssh/forge-mirror";
        checkout = "/home/tester/nixos-agent-env";
        onCalendar = "hourly";
        runAs = "tester";
      };
      fleetEvalCoreMirror = mkFleetEval "core" {
        fleet.mirror = fleetMirrorFixture;
        users.users.tester = {
          isNormalUser = true;
        };
      };
      fleetEvalForgeMirror = mkFleetEval "forge" (
        {
          networking.interfaces.eth1.ipv4.addresses = [
            {
              address = "192.0.2.10";
              prefixLength = 24;
            }
          ];
        }
        // {
          fleet.mirror = fleetMirrorFixture;
          users.users.tester = {
            isNormalUser = true;
          };
        }
      );
      # FL5 (plan 2026-09-24-fleet-and-forge.md): the bootstrap fixtures --
      # the join template (pkgs/fleet/fleet-join.nix) with the fixture deploy
      # key substituted and no parent import, plus the same system with
      # fleet-join.enable = false (what the first deploy switches to, D7/D8;
      # FL6's VM test imports the identical substituted module as the
      # forge's initial state). replaceVars yields the substituted file as a
      # derivation, so import it as the module (a bare derivation would be
      # merged attrset-by-attrset, its `system` string colliding with
      # system.stateVersion).
      fleetJoinEval = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          (import (
            pkgs.replaceVars ./pkgs/fleet/fleet-join.nix {
              DEPLOY_KEYS = ''[ "${builtins.head fleetFixture.deployKeys}" ]'';
              PARENT_IMPORTS = "";
            }
          ))
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
          })
        ];
      };
      fleetJoinOff = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          (import (
            pkgs.replaceVars ./pkgs/fleet/fleet-join.nix {
              DEPLOY_KEYS = ''[ "${builtins.head fleetFixture.deployKeys}" ]'';
              PARENT_IMPORTS = "";
            }
          ))
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            fleet-join.enable = false;
          })
        ];
      };
      # FL9 (plan 2026-09-24-fleet-and-forge.md): the copy's trust rule.
      # fleet deploy copies with --no-check-sigs, which the receiving daemon
      # honours for trusted users only; so deploy is the only trusted user
      # besides root in every spelling nix reads (trusted-users,
      # extra-trusted-users, nix.extraOptions), and signatures stay
      # required. checks.fleet-eval applies it to the forge and the
      # bootstrap, and refuses each widened fixture below -- one per clause,
      # so every clause and every connective can fail the check.
      fleetTrustOk =
        c:
        builtins.filter (u: u != "root") c.nix.settings.trusted-users == [ "deploy" ]
        && (c.nix.settings.extra-trusted-users or [ ]) == [ ]
        && !(nixpkgs.lib.hasInfix "trusted-users" c.nix.extraOptions)
        && c.nix.settings.require-sigs;
      fleetTrustWidened =
        builtins.mapAttrs (_: m: (fleetEvalForge.extendModules { modules = [ m ]; }).config)
          {
            trusted-users = {
              nix.settings.trusted-users = [ "@wheel" ];
            };
            extra-trusted-users = {
              nix.settings.extra-trusted-users = [ "@wheel" ];
            };
            extraOptions = {
              nix.extraOptions = "extra-trusted-users = @wheel";
            };
            require-sigs = {
              nix.settings.require-sigs = false;
            };
          };
      # IS11: services.lan-access fixtures. The positive lanEvalSystem (three
      # sites, incl. the [::1] IPv6 arm of A1) and the lanDisabledSystem control
      # (the same three sites, enable = false) feed checks.lan-eval; the five
      # negative systems feed checks.lan-assertion-negative (A1 IPv4, A4 wrong
      # dir -- a store path and /var/lib/secrets --, and the two A3 arms -- a
      # bare foreign host and a host spelled like a site).
      lanEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            services.lan-access = {
              enable = true;
              interface = "eth1";
              sites = {
                helm = {
                  upstream = "127.0.0.1:7700";
                  hashFile = "/var/lib/lan-access/helm.bcrypt";
                  user = "alice";
                };
                feed = {
                  upstream = "127.0.0.1:8188";
                  hashFile = "/var/lib/lan-access/feed.bcrypt";
                  user = "alice";
                };
                api = {
                  upstream = "[::1]:7710";
                  hashFile = "/var/lib/lan-access/api.bcrypt";
                  user = "alice";
                };
              };
            };
          })
        ];
      };
      lanDisabledSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            services.lan-access = {
              enable = false;
              interface = "eth1";
              sites = {
                helm = {
                  upstream = "127.0.0.1:7700";
                  hashFile = "/var/lib/lan-access/helm.bcrypt";
                  user = "alice";
                };
                feed = {
                  upstream = "127.0.0.1:8188";
                  hashFile = "/var/lib/lan-access/feed.bcrypt";
                  user = "alice";
                };
                api = {
                  upstream = "[::1]:7710";
                  hashFile = "/var/lib/lan-access/api.bcrypt";
                  user = "alice";
                };
              };
            };
          })
        ];
      };
      lanBadUpstreamSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            services.lan-access = {
              enable = true;
              interface = "eth1";
              sites.helm = {
                upstream = "0.0.0.0:7700";
                hashFile = "/var/lib/lan-access/helm.bcrypt";
                user = "alice";
              };
            };
          })
        ];
      };
      lanHashInStoreSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            services.lan-access = {
              enable = true;
              interface = "eth1";
              sites.helm = {
                upstream = "127.0.0.1:7700";
                hashFile = "${pkgs.writeText "h" "x"}";
                user = "alice";
              };
            };
          })
        ];
      };
      lanHashOutsideDirSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            services.lan-access = {
              enable = true;
              interface = "eth1";
              sites.helm = {
                upstream = "127.0.0.1:7700";
                hashFile = "/var/lib/secrets/helm.bcrypt";
                user = "alice";
              };
            };
          })
        ];
      };
      lanForeignHostSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            services.lan-access = {
              enable = true;
              interface = "eth1";
              sites.helm = {
                upstream = "127.0.0.1:7700";
                hashFile = "/var/lib/lan-access/helm.bcrypt";
                user = "alice";
              };
            };
            services.caddy.virtualHosts."public.example".listenAddresses = [ ];
          })
        ];
      };
      lanForeignSiteNameSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.lanAccess
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            networking.hostName = "core";
            services.lan-access = {
              enable = true;
              interface = "eth1";
              sites = {
                helm = {
                  upstream = "127.0.0.1:7700";
                  hashFile = "/var/lib/lan-access/helm.bcrypt";
                  user = "alice";
                };
                api = {
                  upstream = "[::1]:7710";
                  hashFile = "/var/lib/lan-access/api.bcrypt";
                  user = "alice";
                };
              };
            };
            services.caddy.virtualHosts."feed.core.local".listenAddresses = [ "0.0.0.0" ];
          })
        ];
      };
      # HH3 / D-H4: the host core's specialArgs and module list, lifted out of
      # the inline nixosConfigurations.core so mkCore can evaluate the host
      # "with" and "without" the helmHome module for the reversibility check.
      coreSpecialArgs = {
        claude-code-pkg = self.lib.patchSeries.applyTo "claude-code" llm-agents.packages.x86_64-linux.claude-code;
        proton-drive-cli-pkg = self.packages.x86_64-linux.proton-drive-cli;
        basket-pkg = self.packages.x86_64-linux.basket;
        # The operator's DeepSeek seat (pkgs/dsh-openrouter), a plain command on
        # the host since the 2026-09-03 evening switch ("no nix run").
        dsh-openrouter-pkg = self.packages.x86_64-linux.dsh-openrouter;
        inherit claude-desktop;
        # GN12: comfyui builds against nixpkgs-host now (media/packages.nix), as a
        # host-flake package; the media input and its flake/lock are retired.
        comfyui-pkg = self.packages.x86_64-linux.comfyui;
        # FL5 (plan 2026-09-24-fleet-and-forge.md): the fleet command, for
        # hosts/core/fleet.nix to install on the operator's machine.
        fleet-pkg = self.packages.x86_64-linux.fleet;
      };
      # US1 (plan 2026-09-24-strict-user-spaces-1a.md): the host's module list,
      # split in two. coreModulesBase is everything core always had (its body
      # is the pre-US1 coreModules, unchanged); userSideModules is the user
      # side -- home-manager's NixOS module over the binding file
      # hosts/core/user-side.nix; coreModules is their concatenation, so every
      # existing use of coreModules (nixosConfigurations.core,
      # helm-home-reversible's two arms) keeps the full list, and the
      # no-lockout check can evaluate the host with and without the user side.
      coreModulesBase = [
        ./hosts/core
        self.nixosModules.basketStore
        self.nixosModules.egressBroker
        # claudeManagedSettings is NOT listed separately here: cowork.nix
        # now imports it directly (nixosModules/cowork.nix, so it can
        # consume services.claude-managed-settings.settingsFile without
        # duplicating the generator), and listing the same file both ways
        # trips NixOS's module-key dedup ("option already declared") since
        # a raw-path import and an applied-function import get different
        # keys.
        self.nixosModules.cowork
        self.nixosModules.protonBackup
        self.nixosModules.helm
        self.nixosModules.evidenceStore
        self.nixosModules.modelLane
        self.nixosModules.seatLane
        self.nixosModules.claudeTelemetry
        # SP9 (plan 2026-09-08-spend-telemetry): the otel-ingest timer module,
        # in the host's list (hosts/core/default.nix only flips enable).
        self.nixosModules.otelIngest
        # FL1 (plan 2026-09-24-fleet-and-forge.md): the one declared fleet
        # list, pinned identities and the deploy user (hosts/fleet.json).
        self.nixosModules.fleet
        ./hosts/fleet.nix
        ./media/nixosModules/comfyui-worlds.nix
        # GN19: the local author model unit (llama-server on loopback,
        # digest-guarded weights), wired beside the worlds module so the
        # model unit's derived Conflicts= can read the configured worlds.
        ./media/nixosModules/local-model.nix
        # The drift tile shells out to `nixos-version
        # --configuration-revision`; that reads this option, which
        # nixpkgs otherwise leaves unset on a plain flake checkout.
        # self.rev is only set for a clean git tree; self.dirtyRev covers
        # a dirty one (both require the tree to have a commit at all,
        # hence the "dirty" fallback for a fresh checkout with no HEAD).
        (_: {
          system.configurationRevision = self.rev or self.dirtyRev or "dirty";
        })
      ];
      userSideModules = [
        home-manager.nixosModules.home-manager
        ./hosts/core/user-side.nix
      ];
      coreModules = coreModulesBase ++ userSideModules;
      mkCore =
        modules:
        nixpkgs-host.lib.nixosSystem {
          system = "x86_64-linux";
          specialArgs = coreSpecialArgs;
          inherit modules;
        };
      forgeModules = [
        ./hosts/forge
        self.nixosModules.fleet
        self.nixosModules.lanAccess
        self.nixosModules.protonBackup
      ];
      mkForge =
        modules:
        nixpkgs-host.lib.nixosSystem {
          system = "x86_64-linux";
          specialArgs = {
            inherit (coreSpecialArgs) proton-drive-cli-pkg;
          };
          inherit modules;
        };
      # PL17 (docs/superpowers/plans/2026-09-11-platform.md): the operator's
      # machine lives in hosts/private.nix — everything that reads hosts/*
      # or evaluates the real nixosConfigurations. privateOut guards the
      # import with pathExists, so a public export (hosts/* is 100%
      # withheld) still evaluates every flake output with
      # nixosConfigurations = { }; the checks side (privateChecks, inside
      # checks.${system}'s let) is a never-forced thunk on such a tree.
      hostsPrivatePath = ./hosts/private.nix;
      privateOut =
        if builtins.pathExists hostsPrivatePath then
          import hostsPrivatePath {
            inherit
              self
              nixpkgs
              pkgs
              system
              mkCore
              mkForge
              coreModules
              coreModulesBase
              forgeModules
              ;
            inherit dshOpenrouter fleetFixture;
            inherit seatHelmPortSystem seatPortRangeExactSystem seatWaveJobsOneSystem;
          }
        else
          { nixosConfigurations = { }; };
    in
    {
      packages.${system} = {
        inherit basket;
        default = basket;
        proton-drive-cli = pkgs.callPackage ./pkgs/proton-drive-cli { };
        proton-backup-push = protonBackupPush;
        helm-collect = helmCollect;
        helm-status = helmStatus;
        helm-serve = helmServe;
        helm-api = helmApi;
        helm-home = helmHome;
        # A plain command for `nix run .#helm-home-probe` before HH7 flips the
        # package's mainProgram over to the full Helm Home shell.
        helm-home-probe = pkgs.writeShellApplication {
          name = "helm-home-probe";
          runtimeInputs = [ helmHome ];
          text = ''exec helm-home-probe "$@"'';
        };
        # T3 (Lane L round 1 plan) replaces this stub with the real
        # OpenRouter client; nixosModules/modelLane.nix references the same
        # file so lane-<name>@.service's ExecStart path never has to change.
        lane-run = pkgs.callPackage ./pkgs/lane/lane-run.nix { };
        dsh = dshHost;
        dsh-openrouter = dshOpenrouter;
        # PL5 (2026-09-11-platform.md): the validated dsh-harness catalog, built
        # on nixpkgs-host (Interface 5) so the sibling's invariants are checked
        # by the same stdenv that builds the host.
        dsh-harness-src = dshHarnessSrc;
        # SB3 + SB1 (2026-09-05-seat-behind-broker): the seat's operator CLI
        # (seat-submit) and the seat@<job> unit entry (seat-run). seatLane.nix
        # builds seat-run via its own callPackage, so these packages stay a
        # stable path for the eval check.
        inherit (seatTools) seat-submit seat-run;
        # OS2 (2026-09-22-tvix-aios-step1): the Rust workspace, its lock
        # generator and the fork's source (pkgs/aiosd/default.nix).
        aios-workspace = aios.workspace;
        aios-lock = aios.lock;
        tvix-aios-src = aios.forkSrc;
        evidence = pkgs.writeShellApplication {
          name = "evidence";
          runtimeInputs = [
            pkgs.python3
            pkgs.git
          ];
          text = ''exec python3 ${./pkgs/evidence}/evidence.py "$@"'';
        };
        # FL5 (plan 2026-09-24-fleet-and-forge.md): the fleet command --
        # deploy, enroll, keys and join-script over the declared list
        # (pkgs/fleet/fleet.py, stdlib Python). `nix` comes from the host's
        # PATH, as `nix build` does everywhere else on core.
        fleet = pkgs.writeShellApplication {
          name = "fleet";
          runtimeInputs = [
            pkgs.python3
            pkgs.openssh
            pkgs.git
          ];
          text = ''exec python3 ${./pkgs/fleet}/fleet.py "$@"'';
        };
      }
      # GN12: media's five packages (media/packages.nix), built against pkgsHost.
      // (import ./media/packages.nix { pkgs = pkgsHost; });

      nixosModules = {
        egressBroker = import ./nixosModules/egressBroker.nix;
        basketStore = import ./nixosModules/basketStore.nix;
        claudeManagedSettings = import ./nixosModules/claudeManagedSettings.nix;
        cowork = import ./nixosModules/cowork.nix;
        protonBackup = import ./nixosModules/protonBackup.nix;
        helm = import ./nixosModules/helm.nix;
        helmHome = import ./nixosModules/helmHome.nix;
        modelLane = import ./nixosModules/modelLane.nix;
        seatLane = import ./nixosModules/seatLane.nix;
        lanAccess = import ./nixosModules/lanAccess.nix;
        evidenceStore = import ./nixosModules/evidenceStore.nix;
        claudeTelemetry = import ./nixosModules/claudeTelemetry.nix;
        usageIngest = import ./nixosModules/usageIngest.nix;
        # SP9 (plan 2026-09-08-spend-telemetry): the otel-ingest timer that
        # drains the collector's Claude telemetry hourly.
        otelIngest = import ./nixosModules/otelIngest.nix;
        # FL1 (plan 2026-09-24-fleet-and-forge.md): the fleet module.
        fleet = import ./nixosModules/fleet.nix;
        # PL14: gaming, absorbed in-repo from the retired sibling flake
        # (git subtree add, 2026-09-21 profile-switching abandonment). The
        # module is exposed for a future consumer; core no longer imports
        # it (the specialisation that did is retired with it).
        gaming = import ./gaming/nixosModules/gaming.nix;
        # OS10 (plan 2026-09-22-aios-daemon-dispatch): options.aios — the
        # declaration surface (spec 2026-09-22-tvix-aios §4), step 3's slice.
        aios = import ./nixosModules/aios.nix;
      };

      lib = {
        mkAgent = import ./lib/mkAgent.nix;
        patchSeries =
          let
            ps = import ./lib/patchSeries.nix { inherit (nixpkgs) lib; };
          in
          ps
          // {
            applyTo = name: ps.applySeries (self + "/patches/" + name);
          };
      }
      // import ./lib/checkHelmDeclaration.nix {
        inherit pkgs;
        inherit (nixpkgs) lib;
      };

      helm = import ./helm.nix;

      # PL17: core and forge are declared in hosts/private.nix (see
      # hostsPrivatePath above); with that file absent the output is { }.
      inherit (privateOut) nixosConfigurations;

      phase3NegativeDemo = phase3BadSystem;

      devShells.${system}.default = pkgs.mkShell {
        packages = devShellPackages;
        # SA8: mirror checks.${system}.unit's runCommand env (below) so a
        # devShell `bats` run sees the same harness-payload seam the
        # sandboxed check does. dshOpenrouterWithPayload shares dshHost with
        # dshOpenrouter (already in devShellPackages above), so realizing it
        # here costs no more than the wrapper's own rebuild.
        DSH_OPENROUTER_PAYLOAD_FIXTURE = ./tests/fixtures/harness-payload;
        DSH_OPENROUTER_WITH_PAYLOAD = dshOpenrouterWithPayload;
        shellHook = ''
          git config core.hooksPath githooks
        '';
      };

      checks.${system} =
        let
          hostChecks = {
            # The devShell's Python is load-bearing for the data skills, and "the
            # stack is in the shell" is only true of the env that actually wins
            # PATH. Assert there is exactly one python3 env in the shell, that it
            # is devPython, and that every module those skills import resolves.
            devshell-python =
              let
                pythonEnvs = builtins.filter (p: nixpkgs.lib.getName p == "python3") devShellPackages;
              in
              if pythonEnvs != [ devPython ] then
                throw "devshell-python: the devShell must carry exactly one python3 env and it must be devPython (a second env is shadowed on PATH); found ${
                  toString (map (p: p.name) pythonEnvs)
                }"
              else
                pkgs.runCommand "devshell-python-check" { nativeBuildInputs = [ devPython ]; } ''
                  export MPLCONFIGDIR="$PWD/mpl"
                  python3 -c 'import duckdb, pandas, plotly, scipy, seaborn, pytest, mitmproxy'
                  python3 -c 'import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot'
                  touch $out
                '';
            proton-drive-cli = self.packages.${system}.proton-drive-cli;

            assertion-positive =
              (nixpkgs.lib.nixosSystem {
                inherit system;
                modules = [
                  self.nixosModules.basketStore
                  self.nixosModules.egressBroker
                  (self.lib.mkAgent {
                    name = "offline-agent";
                    baskets = [
                      "notes-local"
                      "workspace"
                    ];
                  })
                  (self.lib.mkAgent {
                    name = "online-agent";
                    baskets = [ "workspace" ];
                    egress = "broker:work";
                  })
                  (_: {
                    boot.loader.grub.enable = false;
                    fileSystems."/".device = "none";
                    fileSystems."/".fsType = "tmpfs";
                    system.stateVersion = "25.11";
                    services = {
                      egress-broker.instances.work = {
                        hostAddress = "10.100.0.1";
                        namespaceAddress = "10.100.0.2";
                        allow = [ "example.com" ];
                      };
                      baskets.definitions = {
                        notes-local = {
                          classification = "local-only";
                          mount = "/data/notes";
                        };
                        workspace = {
                          classification = "permitted";
                          mount = "/data/workspace";
                          access = "rw";
                        };
                      };
                    };
                  })
                ];
              }).config.system.build.toplevel;

            assertion-negative =
              let
                attempt = builtins.tryEval phase3BadSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "assertion-negative: a local-only basket reached a network-capable agent and the build DID NOT FAIL"
              else
                pkgs.runCommand "assertion-negative-ok" { } "touch $out";

            # OS10 (plan 2026-09-22-aios-daemon-dispatch; spec 2026-09-22-tvix-aios
            # §2 goal 6): a seat's declared inputs are the classes it names,
            # and nothing else. A path in a seat's baskets list fails evaluation
            # with the invariant-8 message; a local-only class in a seat with an
            # off-box egress fails with the classification assertion's message
            # (basketStore A2); the declared fixture evaluates and the daemon
            # accepts the aios.json it renders.
            aios-classification-negative =
              let
                failing = sys: map (a: a.message) (builtins.filter (a: !a.assertion) sys.config.assertions);
                undeclared = builtins.tryEval aiosSeatUndeclaredSystem.config.system.build.toplevel.drvPath;
                offbox = builtins.tryEval aiosSeatLocalOnlyOffboxSystem.config.system.build.toplevel.drvPath;
                i8 = "aios.seats.leaky.baskets names '/data/undeclared/notes', which is not a declared aios.data class — a seat reads only the classes declared for it (brief §3 invariant 8)";
                a2 = "agent 'leaky' has egress 'broker:work' but mounts local-only basket 'notes'";
              in
              assert nixpkgs.lib.assertMsg (
                !undeclared.success
              ) "aios-classification-negative: a seat naming a path as its input evaluated";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem i8 (failing aiosSeatUndeclaredSystem))
                "aios-classification-negative: the undeclared-class refusal did not carry the invariant-8 message";
              assert nixpkgs.lib.assertMsg (!offbox.success)
                "aios-classification-negative: a local-only class reached a seat with an off-box egress and the build DID NOT FAIL";
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.any (nixpkgs.lib.hasPrefix a2) (failing aiosSeatLocalOnlyOffboxSystem))
                "aios-classification-negative: the local-only refusal did not carry the classification assertion's message";
              builtins.seq aiosSeatDeclaredSystem.config.system.build.toplevel.drvPath (
                pkgs.runCommand "aios-classification-negative" { } ''
                  ${aios.workspace}/bin/aiosd ${aiosSeatDeclaredSystem.config.aios.declaration} > out.txt
                  grep -Fx 'aiosd: declaration ok version=1 vms=0 seats=1 workflows=0 worlds=0 egress=1 classes=1 guard-rules=0' out.txt
                  touch $out
                ''
              );

            manifests-validate =
              let
                demo =
                  (nixpkgs.lib.nixosSystem {
                    inherit system;
                    modules = [
                      self.nixosModules.basketStore
                      (_: {
                        boot.loader.grub.enable = false;
                        fileSystems."/".device = "none";
                        fileSystems."/".fsType = "tmpfs";
                        system.stateVersion = "25.11";
                        services.baskets.definitions.demo = {
                          classification = "redacted";
                          mount = "/data/demo";
                        };
                      })
                    ];
                  }).config.services.baskets.manifestsPackage;
              in
              pkgs.runCommand "manifests-validate" { nativeBuildInputs = [ basket ]; } ''
                for f in ${demo}/*.json; do
                  basket validate-manifest "$f"
                done
                touch $out
              '';

            lint =
              pkgs.runCommand "lint"
                {
                  nativeBuildInputs = lintTools ++ [ pkgs.python3 ];
                }
                ''
                  cp -r ${self} src && chmod -R u+w src && cd src
                  treefmt --ci --config-file treefmt.toml --tree-root .
                  shellcheck pkgs/basket/basket.sh pkgs/proton-backup/push.sh pkgs/dsh-openrouter/dsh-openrouter.sh pkgs/helm/helm-switch.sh pkgs/helm/helm-open-workspace.sh tests/mocks/proton-drive-mock.sh githooks/pre-push githooks/pre-commit pkgs/fleet/mirror.sh
                  # The seat driver's entry scripts are extensionless (factory-brief,
                  # -ws, -task, -wave, -integrate, -review), so the `find tools
                  # -name '*.sh'` sweep below misses them; their .sh sibling is swept.
                  shellcheck tools/factory/seat/factory-brief tools/factory/seat/factory-ws tools/factory/seat/factory-task tools/factory/seat/factory-wave tools/factory/seat/factory-integrate tools/factory/seat/factory-review tools/debug/bug-note tools/debug/investigate tools/fleet tools/home-classes
                  find tests -name '*.sh' -print0 | xargs -0 --no-run-if-empty shellcheck
                  # T3 (Lane L round 1 plan): the first tools/*.sh scripts this
                  # repo actually gates on shellcheck (tools/lane/jobs/*.sh) --
                  # widened to the whole directory, not just that subdir, so the
                  # pre-existing cowork-up.sh/cowork-down.sh/enroll-yubikey.sh/
                  # reset-yubikey-piv.sh (already clean; verified before this
                  # change) are gated too from here on.
                  find tools -name '*.sh' -print0 | xargs -0 --no-run-if-empty shellcheck
                  # Every host's hardware-configuration.nix is exempt from
                  # these two style linters: hosts/core's is a byte-for-byte
                  # copy of nixos-generate-config output (plan: hosts/core
                  # must stay verbatim) and hosts/forge's is the marked
                  # placeholder `fleet enroll` replaces verbatim. FL5 adds
                  # pkgs/fleet/fleet-join.nix, the bootstrap module TEMPLATE:
                  # its @DEPLOY_KEYS@ / @PARENT_IMPORTS@ placeholders are not
                  # parseable Nix until substituted, so the linters skip it.
                  statix check . -i hosts/core/hardware-configuration.nix -i hosts/forge/hardware-configuration.nix -i pkgs/fleet/fleet-join.nix
                  deadnix --fail . --exclude hosts/core/hardware-configuration.nix hosts/forge/hardware-configuration.nix pkgs/fleet/fleet-join.nix
                  ruff check pkgs/broker tests/broker pkgs/helm tests/helm pkgs/lane tests/lane tests/mocks tools/ledger tests/ledger pkgs/dsh-openrouter tools/factory/seat tools/factory/route.py pkgs/evidence tests/evidence pkgs/seat tests/seat pkgs/helm-home tests/helm-home tests/unit/fixtures pkgs/fleet pkgs/home-classes
                  ruff format --check pkgs/broker tests/broker pkgs/helm tests/helm pkgs/lane tests/lane tests/mocks tools/ledger tests/ledger pkgs/dsh-openrouter tools/factory/seat tools/factory/route.py pkgs/evidence tests/evidence pkgs/seat tests/seat pkgs/helm-home tests/helm-home tests/unit/fixtures pkgs/fleet pkgs/home-classes
                  # KN13 (b) R-practice-hardware-config-verbatim, FL2
                  # Interface 3: every host's hardware-configuration.nix is
                  # pinned by hosts/hardware-pins.sha256 (the exact producer:
                  # `sha256sum hosts/*/hardware-configuration.nix >
                  # hosts/hardware-pins.sha256`, what `fleet enroll` runs); a
                  # pinned file that changed fails, and a host directory
                  # without a pin line fails.
                  sha256sum -c --quiet hosts/hardware-pins.sha256
                  for f in hosts/*/hardware-configuration.nix; do grep -q "  $f\$" hosts/hardware-pins.sha256 || { echo "lint: $f has no line in hosts/hardware-pins.sha256" >&2; exit 1; }; done
                  # KN13 (b) R-practice-brief8-no-secrets: no secret material in
                  # the tree. The arms mirror pkgs/evidence/streams.py SECRET_RE
                  # minus its prose-prone tokens (Bearer, \beyJ, \bage1); a new
                  # prefix goes into both in one commit. docs/ is excluded because
                  # it is prose that legitimately quotes these very shapes (the
                  # plan specs document the arms and their mutants), not material.
                  if grep -rEn -e 'sk-or-v[0-9]+-[A-Za-z0-9]{16}' -e 'sk-ant-api[0-9]{2}-[A-Za-z0-9_-]{16}' -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' -e 'AGE-SECRET-KEY-1[A-Z0-9]{16}' --exclude-dir=.git --exclude-dir=docs .; then
                    echo "lint: secret material in the tree (brief §8): the lines above" >&2
                    exit 1
                  fi
                  # Board shape (plan 2026-09-05-evidence-store, E8/D5): the board carries the
                  # plan; facts come from `evidence bundle`. One START HERE, one screen or two.
                  test "$(grep -c '^## START HERE' docs/OPERATIONS.md)" -eq 1 || {
                    echo "lint: docs/OPERATIONS.md must have exactly one '## START HERE' heading" >&2
                    exit 1
                  }
                  test "$(wc -l <docs/OPERATIONS.md)" -le 160 || {
                    echo "lint: docs/OPERATIONS.md must be at most 160 lines (log and archive live under docs/board/)" >&2
                    exit 1
                  }
                  # KN17 (50a/51a): the board is the derived page and nothing else —
                  # a fixed header, one marked block, nothing after the end marker but
                  # a trailing newline, the block within the board cap
                  # (tests/lint/now-paragraph.sh, --self-test first so the guard is
                  # never swallowed).
                  bash tests/lint/now-paragraph.sh --self-test
                  bash tests/lint/now-paragraph.sh
                  # P2: no '] && [' chains in bats tests (vacuous under errexit).
                  bash tests/lint/bats-and-chain.sh
                  # P12: prettier + oxlint gate every tracked JS file. The
                  # self-test runs first (on its own line, not joined by `&&`:
                  # under errexit a failing first command in an `a && b` list is
                  # swallowed, which would silently gut the vacuous-gate guard);
                  # the project sweep runs only if it passes.
                  bash tests/lint/js-lint.sh --self-test
                  bash tests/lint/js-lint.sh
                  # T1W: no writer outside evidence.py may reopen the store for
                  # writing or hard-code the store root. Same self-test-first
                  # discipline as js-lint.sh: the fixture sweep runs on its own
                  # line so the vacuous-gate guard is never swallowed.
                  bash tests/lint/store-writers.sh --self-test
                  bash tests/lint/store-writers.sh
                  # ER1 (plan 2026-09-24-retro-fixes): the publish and
                  # subsystems validators run in lint too, on the sandbox's
                  # own tree (no git — publish-manifest.sh enumerates with
                  # find, same contract as store-writers.sh). Self-test
                  # first, on its own line, never joined by `&&`.
                  bash tests/lint/publish-manifest.sh --self-test
                  bash tests/lint/publish-manifest.sh
                  # G5: the derived task graph must be well-formed. The repos file
                  # points tasks.py at THIS copy of the tree ($PWD after `cd src`),
                  # not ~/nixos-agent-env, so the sandbox checks the tree under test
                  # rather than exiting 0 for zero repos.
                  repos_file="$(mktemp)"
                  printf '[[repo]]\nname = "nixos-agent-env"\npath = "%s"\n' "$PWD" >"$repos_file"
                  python3 pkgs/evidence/tasks.py --root . --repos "$repos_file" --runs-dir /nonexistent --store /nonexistent check
                  rm -f "$repos_file"
                  # G5: docs/MAP.md's Checks section must equal the flake's real check set.
                  awk '/^## Checks/{s=1;next} /^## /{s=0} s&&/^- /{sub(/^- /,"");print}' docs/MAP.md | sort >map-checks
                  sort ${checkNamesFile} >flake-checks
                  # KN13 Interface 3: every non-empty check value in the ledger
                  # must name a flake check (decision 54a resolution). The same
                  # checkNamesFile list is what MAP.md's Checks section is diffed
                  # against, so a check name that resolves nowhere is refused here.
                  grep '^check = "' docs/ledger/rules.toml | sed 's/^check = "//;s/"$//' | grep -v '^$' | sort -u >rule-checks
                  if comm -23 rule-checks flake-checks | grep -q .; then
                    echo "lint: docs/ledger/rules.toml names a check the flake does not define: $(comm -23 rule-checks flake-checks | tr '\n' ' ')" >&2
                    exit 1
                  fi
                  diff -u flake-checks map-checks || { echo "lint: docs/MAP.md Checks section differs from the flake's checks (regenerate: python3 pkgs/evidence/repomap.py write)" >&2; exit 1; }
                  # G5: the repo map must be current.
                  python3 pkgs/evidence/repomap.py --root . check
                  # KN15 (decision 59a): CLAUDE.md's rules block is generated
                  # from docs/ledger/rules.toml (origin_target = "claude" rows);
                  # drift in either direction fails lint. --check, never a bare
                  # generate: a writing verb in lint would "fix" drift silently
                  # instead of refusing it.
                  python3 pkgs/evidence/rules.py generate docs/ledger/rules.toml --target claude --out CLAUDE.md --check --root .
                  touch $out
                '';
            addon =
              pkgs.runCommand "broker-addon-tests"
                {
                  nativeBuildInputs = [ brokerPython ];
                }
                ''
                  cp -r ${self}/pkgs/broker broker
                  cp -r ${self}/tests/broker tests-broker
                  cd .
                  pytest tests-broker -q
                  touch $out
                '';
            # The plan test loads .claude/workflows/plan.js verbatim and runs it
            # with stub globals, so this check fails the moment a prompt site
            # drifts from its judgement or a criterion row moves. The graph
            # soundness and registry drift checks below are live here too.
            factory-unit =
              pkgs.runCommand "factory-unit"
                {
                  # factory-registry.py check resolves each agents.toml row by
                  # shelling out to route.py (python3), so python3 must be on PATH.
                  nativeBuildInputs = [
                    pkgs.nodejs
                    pkgs.python3
                  ];
                }
                ''
                  mkdir -p tools/factory/plan tools/factory/seat .claude/workflows tests/factory docs/ledger pkgs/evidence
                  cp ${self}/tools/factory/route.py tools/factory/route.py
                  cp ${self}/docs/ledger/routing.toml docs/ledger/routing.toml
                  cp -r ${self}/tests/factory/fixtures tests/factory/fixtures
                  cp ${self}/tests/factory/plan.test.mjs tests/factory/plan.test.mjs
                  cp ${self}/.claude/workflows/plan.js .claude/workflows/plan.js
                  cp ${self}/tools/factory/plan/rubric.md tools/factory/plan/rubric.md
                  cp ${self}/tools/factory/plan/judge-prompt.md tools/factory/plan/judge-prompt.md
                  cp ${self}/tools/factory/plan/seat-plan.md tools/factory/plan/seat-plan.md
                  # The registry and its generated shims, plus each row's prompt
                  # file, so factory-registry.py check can resolve and compare them.
                  cp ${self}/tools/factory/agents.toml tools/factory/agents.toml
                  cp -r ${self}/.claude/agents .claude/agents
                  cp ${self}/tools/factory/seat/README.md tools/factory/seat/README.md
                  cp ${self}/tools/factory/seat/factory-graph.py tools/factory/seat/factory-graph.py
                  cp ${self}/tools/factory/seat/factory-registry.py tools/factory/seat/factory-registry.py
                  cp ${self}/tools/factory/seat/factory-artifact.py tools/factory/seat/factory-artifact.py
                  # pkgs/evidence/judgements.py `import evidence`s at module top, so
                  # its --fields subprocess needs the sibling on the import path.
                  cp ${self}/pkgs/evidence/judgements.py pkgs/evidence/judgements.py
                  cp ${self}/pkgs/evidence/evidence.py pkgs/evidence/evidence.py
                  cp ${self}/pkgs/evidence/streams.py pkgs/evidence/streams.py
                  node tests/factory/plan.test.mjs
                  # The graph soundness check runs over every .claude/workflows/*.toml
                  # in the tree. None exists at this landing, and without nullglob the
                  # loop would copy the literal pattern and the check would exit 2 on
                  # ``unreadable`` -- so zero graphs must be a real no-op.
                  mkdir -p .claude/workflows .claude/agents
                  shopt -s nullglob
                  graphs=( ${self}/.claude/workflows/*.toml )
                  for f in "''${graphs[@]}"; do cp "$f" .claude/workflows/; done
                  if [ "''${#graphs[@]}" -gt 0 ]; then python3 tools/factory/seat/factory-graph.py check .claude/workflows/*.toml; else echo "graphs: none"; fi
                  python3 tools/factory/seat/factory-registry.py check
                  echo "registry: ok"
                  touch $out
                '';
            helm-unit =
              pkgs.runCommand "helm-unit-tests"
                {
                  nativeBuildInputs = [ helmPython ];
                }
                ''
                  mkdir -p pkgs tests
                  cp -r ${self}/pkgs/helm pkgs/helm
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  cp -r ${self}/tests/helm tests/helm
                  pytest tests/helm -q
                  touch $out
                '';
            helm-home-unit = pkgs.runCommand "helm-home-unit" { nativeBuildInputs = [ helmPython ]; } ''
              mkdir -p pkgs tests
              cp -r ${self}/pkgs/helm-home pkgs/helm-home
              cp -r ${self}/pkgs/evidence pkgs/evidence
              cp -r ${self}/tests/helm-home tests/helm-home
              export HOME=$TMPDIR GIT_CONFIG_GLOBAL=$TMPDIR/.gitconfig
              pytest tests/helm-home -q
              touch $out
            '';
            helm-home-package = pkgs.runCommand "helm-home-package" { nativeBuildInputs = [ helmHome ]; } ''
              lines=$(helm-home-probe --self-test)
              echo "$lines"
              echo "$lines" | grep -F 'CreateSession (a{sv})'
              echo "$lines" | grep -F 'BindShortcuts (oa(sa{sv})sa{sv})'
              touch $out
            '';
            evidence-unit =
              pkgs.runCommand "evidence-unit"
                {
                  nativeBuildInputs = [
                    helmPython
                    # E9's bundle tests build a throwaway repo and run git diff.
                    pkgs.git
                  ];
                }
                ''
                  export HOME=$TMPDIR
                  export GIT_CONFIG_GLOBAL=$TMPDIR/.gitconfig
                  export EVIDENCE_UNIT_SANDBOX=1
                  mkdir -p pkgs tests docs docs/superpowers
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  cp -r ${self}/tests/evidence tests/evidence
                  # PG1: the negative fixture, so test_publish.py's fixture test runs here too.
                  mkdir -p tests/fixtures
                  cp -r ${self}/tests/fixtures/publish tests/fixtures/publish
                  # E2's validator resolves parked claims' decision files.
                  cp -r ${self}/docs/decisions docs/decisions
                  cp -r ${self}/docs/ledger docs/ledger
                  # Pin the plan-defect ledger to the frozen seed so the sandbox
                  # never sees the live, growing ledger (P3Ar3): a test that
                  # hard-codes a live count fails here and passes nowhere else.
                  # `cp -r` preserves the store's read-only modes (0555 dirs, 0444
                  # files), so make both writable before overwriting with the seed.
                  chmod u+w docs/ledger docs/ledger/plan-defects.toml
                  cp ${self}/tests/evidence/fixtures/ledger/plan-defects-seed.toml docs/ledger/plan-defects.toml
                  cp -r ${self}/docs/superpowers/plans docs/superpowers/plans
                  cp ${self}/docs/MAP.md docs/MAP.md
                  # The widened plan-judgement validator's own real-corpus tests
                  # (2026-09-17) read every file under docs/reviews/plan-judgements/
                  # straight from the tree rather than a fixture copy, and resolve
                  # each one's `plan` field against docs/superpowers/plans/ above.
                  mkdir -p docs/reviews
                  cp -r ${self}/docs/reviews/plan-judgements docs/reviews/plan-judgements
                  # KN1/KN1b: the rules inventory's validator resolves each row's
                  # `source` in-tree, so copy the cited files. The harness AGENTS.md
                  # (~/flakes/dsh-harness/AGENTS.md) is the one legitimately external
                  # source and stays a warning, never a verbatim failure.
                  cp ${self}/CLAUDE.md CLAUDE.md
                  cp ${self}/docs/brief.md docs/brief.md
                  cp -r ${self}/docs/board docs/board
                  mkdir -p docs/runbooks tools pkgs/dsh-openrouter
                  cp ${self}/docs/runbooks/session.md docs/runbooks/session.md
                  cp ${self}/tools/orchestrator-guard.sh tools/orchestrator-guard.sh
                  cp ${self}/pkgs/dsh-openrouter/hook-guard.py pkgs/dsh-openrouter/hook-guard.py
                  pytest tests/evidence -q
                  touch $out
                '';
            # PT11 (plan 2026-09-22-planning-patterns, spec §4.3): the six pattern
            # docs are held against the outcomes ledger — every exemplar's key
            # approved at its first gate, every anti-pattern's key rejected with a
            # readable in-tree review, every mechanical predicate discriminating by
            # at least the standing threshold. The rate lines are in the build log
            # (`-L`). The ledger is derived and committed by hand between waves, so
            # a regenerated ledger can turn this red: that is a docs fix round, not
            # a check defect. `docs/reviews` is copied for path existence only —
            # the checker never reads a review's text.
            planning-patterns =
              pkgs.runCommand "planning-patterns"
                {
                  nativeBuildInputs = [ helmPython ];
                }
                ''
                  # The store copy is read-only; never leave a __pycache__ behind.
                  export PYTHONDONTWRITEBYTECODE=1
                  mkdir -p pkgs docs/ledger docs/superpowers
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  cp -r ${self}/docs/planning docs/planning
                  cp ${self}/docs/ledger/plan-outcomes.jsonl docs/ledger/plan-outcomes.jsonl
                  cp -r ${self}/docs/superpowers/plans docs/superpowers/plans
                  cp -r ${self}/docs/reviews docs/reviews
                  python3 pkgs/evidence/patterns.py check --root .
                  touch $out
                '';
            # PR1: the subsystem manifest and the every-path-owned check. The
            # `--files` list is the flake source's regular files, which is the
            # tracked set; validate asserts every path matches exactly one row,
            # write --check asserts docs/subsystems.md is the generated page.
            subsystems-manifest =
              pkgs.runCommand "subsystems-manifest"
                {
                  nativeBuildInputs = [
                    ledgerPython
                  ];
                }
                ''
                  mkdir -p pkgs docs
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  cp -r ${self}/docs/ledger docs/ledger
                  cp ${self}/docs/subsystems.md docs/subsystems.md
                  find ${self} -type f -printf '%P\n' > files.txt
                  python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --files files.txt
                  python3 pkgs/evidence/subsystems.py write docs/ledger/subsystems.toml --files files.txt --check docs/subsystems.md
                  touch $out
                '';
            # PG1 (plan 2026-09-21-publish-gate, brief §3.7): the publish
            # manifest and the every-path-classified check. The flake source is
            # the tracked tree, so its regular files are the classification
            # universe; the manifest is read from inside it so its own path is
            # classified too (spec §6). The validator prints paths, line numbers
            # and rule ids, never a matched value.
            publish-gate =
              pkgs.runCommand "publish-gate"
                {
                  nativeBuildInputs = [
                    ledgerPython
                  ];
                }
                ''
                  export PYTHONDONTWRITEBYTECODE=1
                  mkdir -p pkgs
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  find ${self} -type f -printf '%P\n' | LC_ALL=C sort > files.txt
                  python3 pkgs/evidence/publish.py validate ${self}/docs/ledger/publish.toml --tree ${self} --files files.txt
                  touch $out
                '';
            # PG1: the negative control — the same validator over a fixture tree
            # whose manifest plants one defect of every kind (two invented
            # literals, a word, a pattern, an unclassified path, an ambiguous
            # path, a stale pending entry, a withheld file that must never be
            # read). Green only when validate exits exactly 1 and prints exactly
            # tests/fixtures/publish/expected.txt, which names paths and rule
            # ids and never a planted value (assertion-negative's shape, in a
            # script because the property lives in the validator's report).
            publish-gate-negative =
              pkgs.runCommand "publish-gate-negative"
                {
                  nativeBuildInputs = [
                    ledgerPython
                  ];
                }
                ''
                  export PYTHONDONTWRITEBYTECODE=1
                  mkdir -p pkgs tests/fixtures
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  cp -r ${self}/tests/fixtures/publish tests/fixtures/publish
                  rc=0
                  python3 pkgs/evidence/publish.py validate tests/fixtures/publish/publish.toml --tree tests/fixtures/publish > out.txt 2> err.txt || rc=$?
                  if [ "$rc" -ne 1 ]; then
                    echo "publish-gate-negative: validate exited $rc, expected 1 — the planted defects were NOT refused" >&2
                    cat out.txt err.txt >&2
                    exit 1
                  fi
                  diff -u tests/fixtures/publish/expected.txt out.txt || {
                    echo "publish-gate-negative: the report differs from tests/fixtures/publish/expected.txt" >&2
                    exit 1
                  }
                  if grep -F -e 'nobody@example.invalid' -e '900000001' -e 'plantedword' -e 'PLANTED-1234' -e 'PLANTEDGH_0123456789' out.txt err.txt; then
                    echo "publish-gate-negative: the report echoed a planted value (spec §6)" >&2
                    exit 1
                  fi
                  touch $out
                '';
            # OS2 (plan 2026-09-22-tvix-aios-step1; spec 2026-09-22-tvix-aios §2,
            # goal 1): the Rust workspace builds from the publish-gate export
            # against the fork's crates (aios.workspace: cargo build, clippy
            # -D warnings, cargo test), the fork input is locked to the public
            # GitHub fork and not a local path, and the built daemon accepts the
            # empty declaration and refuses an unknown field. "A clean clone of
            # the export evaluates the flake" stays a recorded gap until
            # flake.nix and flake.lock leave `pending` (docs/ledger/claims.toml,
            # aios-public-flake-eval-unmeasured).
            aios-public-build =
              let
                lockData = builtins.fromJSON (builtins.readFile ./flake.lock);
                node = lockData.nodes.${lockData.nodes.root.inputs."tvix-aios"};
              in
              assert nixpkgs.lib.assertMsg
                (
                  node.locked.type == "github"
                  && node.locked.owner == "TheArkifaneVashtorr"
                  && node.locked.repo == "tvix-aios"
                )
                "aios-public-build: the tvix-aios input must be locked to the public GitHub fork (spec §5, brief §2), not a local path";
              pkgs.runCommand "aios-public-build" { } ''
                ${aios.workspace}/bin/aiosd ${./pkgs/aiosd/tests/fixtures/empty.json} > out.txt
                grep -Fx 'aiosd: declaration ok version=1 vms=0 seats=0 workflows=0 worlds=0 egress=0 classes=0 guard-rules=0' out.txt
                if ${aios.workspace}/bin/aiosd ${./pkgs/aiosd/tests/fixtures/unknown-field.json} 2> err.txt; then
                  echo "aios-public-build: an unknown field was NOT refused" >&2
                  exit 1
                fi
                grep -q '^aiosd: declaration refused: ' err.txt
                touch $out
              '';
            claims-validate =
              pkgs.runCommand "claims-validate"
                {
                  nativeBuildInputs = [ pkgs.python3 ];
                }
                ''
                  cp -r ${self} src && cd src
                  python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --repo-root .
                  touch $out
                '';
            rules-validate =
              pkgs.runCommand "rules-validate"
                {
                  nativeBuildInputs = [ pkgs.python3 ];
                }
                ''
                  cp -r ${self} src && cd src
                  python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . --verbatim
                  touch $out
                '';
            # KN13 (decision 54a): every load-bearing rule names a check, and a
            # non-zero owed count is a failure. The validator prints the count on
            # stdout and exits 0 (Evidence's exit code, Not in this plan), so this
            # check captures the report and refuses a non-zero count itself. It
            # does not run --verbatim and does not fail on errs or on a validator
            # exit of 1 -- those are rules-validate's job (EV16).
            rules-owed =
              pkgs.runCommand "rules-owed"
                {
                  nativeBuildInputs = [ ledgerPython ];
                }
                ''
                  mkdir -p pkgs docs
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  cp -r ${self}/docs/ledger docs/ledger
                  report=$(python3 pkgs/evidence/rules.py validate docs/ledger/rules.toml --root . || true)
                  owed=$(printf '%s\n' "$report" | sed -n 's/^owed: \([0-9][0-9]*\) .*/\1/p')
                  [ -n "$owed" ] || { echo "rules-owed: the validator printed no owed: line" >&2; exit 1; }
                  [ "$owed" = 0 ] || { echo "rules-owed: $owed load-bearing rules without a check (decision 54a)" >&2; exit 1; }
                  touch $out
                '';
            # T1 (2026-09-03-lane-l-round1) / N6 (2026-09-04-dsh-review-fix-round):
            # the ledger extractor (tools/ledger/factory.py) with pytest. zstd is a
            # build input because extract-dsh decompresses session transcripts with
            # `zstd -dc` (the durable dsh layout is session.jsonl.zstd, per H10
            # vote 3), and the two-session fixture exercises both the plain and the
            # compressed path.
            ledger-unit =
              pkgs.runCommand "ledger-unit"
                {
                  nativeBuildInputs = [
                    ledgerPython
                    pkgs.zstd
                  ];
                }
                ''
                  cp -r ${self}/tools/ledger ledger
                  mkdir -p pkgs
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  cp -r ${self}/tests/ledger tests-ledger
                  cp -r ${self}/docs/ledger docs-ledger
                  pytest tests-ledger -q
                  touch $out
                '';
            # EV6 (decisions 46a/47a): the patches ledger's validator and its tests.
            # The `review_by` staleness rule takes `--today`; the flake sandbox has
            # no clock, so `today` is the build date (`date +%F`, coreutils is on
            # the stdenv PATH). With the ledger empty at landing the rule is
            # vacuous; a committed row with a past `review_by` fails the build, and
            # the recipe refusal keeps the first real row out until the Platform
            # series registers a `patches/<pkg>/unpack.sh`.
            patches-ledger =
              pkgs.runCommand "patches-ledger"
                {
                  nativeBuildInputs = [ ledgerPython ];
                }
                ''
                  mkdir -p pkgs tests docs
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  cp -r ${self}/tests/evidence tests/evidence
                  cp -r ${self}/docs/ledger docs/ledger
                  python3 pkgs/evidence/patches.py validate docs/ledger/patches.toml --root . --today "$(date +%F)"
                  pytest tests/evidence/test_patches.py -q
                  touch $out
                '';
            helm-eval =
              let
                c = helmEvalSystem.config;
              in
              assert nixpkgs.lib.assertMsg (
                c.services.static-web-server.listen == "127.0.0.1:7700"
              ) "helm-eval: static-web-server listen";
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.elem "helm" c.systemd.services.static-web-server.serviceConfig.SupplementaryGroups)
                "helm-eval: SupplementaryGroups";
              assert nixpkgs.lib.assertMsg (
                c.systemd.user.timers ? helm-collect && c.systemd.user.timers ? helm-flake-check
              ) "helm-eval: user timers";
              assert nixpkgs.lib.assertMsg (c.users.groups ? helm) "helm-eval: helm group";
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.any (
                  r: nixpkgs.lib.hasInfix "2750" r && nixpkgs.lib.hasInfix "helm" r
                ) c.systemd.tmpfiles.rules)
                # Regression guard for the review finding on the first helm
                # commit: without the setgid bit (2750, not 0750) on
                # /var/lib/helm, files written by helm-collect/helm-flake-check
                # inherit the writer's primary group (not "helm"), so the
                # DynamicUser static-web-server (SupplementaryGroups=helm only)
                # can't read them and the dashboard 403s.
                "helm-eval: /var/lib/helm tmpfiles rule must be setgid (2750) and group helm";
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.any (
                  r: nixpkgs.lib.hasInfix "cache/nix" r
                ) c.systemd.user.services.helm-flake-check.serviceConfig.ReadWritePaths)
                # Regression guard for the review finding on the helm-flake-check
                # commit: ProtectHome=read-only blocks the fetcher-cache write
                # `nix flake check` makes on every run (new repo rev, always a
                # cache miss), so without a writable %h/.cache/nix the nightly
                # check fails every night with a SQLite "readonly database"
                # error.
                "helm-eval: helm-flake-check must have a writable nix cache under ReadWritePaths";
              assert nixpkgs.lib.assertMsg
                (
                  c.systemd.user.services.helm-collect.serviceConfig.UMask == "0027"
                  && c.systemd.user.services.helm-flake-check.serviceConfig.UMask == "0027"
                )
                # Major fix, plan Task 0: without an explicit UMask=0027 these
                # units inherit whatever umask systemd defaults to, which can
                # widen or narrow the 0640/group-helm files write_atomic writes
                # (write_atomic's own os.fchmod is the other half of this fix).
                "helm-eval: both user units must set UMask=0027";
              assert nixpkgs.lib.assertMsg
                (c.systemd.user.services.helm-collect.environment.RESTIC_CACHE_DIR or null == "/var/lib/helm-cache")
                # Major fix, plan Task 0: ProtectHome=read-only leaves restic
                # with no writable cache otherwise.
                "helm-eval: helm-collect.service must set RESTIC_CACHE_DIR=/var/lib/helm-cache";
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.any (
                  r: nixpkgs.lib.hasInfix "/var/lib/helm-cache" r && nixpkgs.lib.hasInfix "0700" r
                ) c.systemd.tmpfiles.rules)
                # Audit F17: restic's cache dir must sit outside /var/lib/helm
                # (the served document root), 0700 so only operatorUser can read
                # it.
                "helm-eval: /var/lib/helm-cache tmpfiles rule (0700) must exist for the restic cache";
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.elem "-/var/lib/helm-cache" c.systemd.user.services.helm-collect.serviceConfig.ReadWritePaths)
                # Dashed like helm-flake-check's ReadWritePaths entries and
                # static-web-server's BindReadOnlyPaths above: tmpfiles runs
                # during activation, before this unit's first start, so the dir
                # should already exist by the time it matters -- the dash is
                # belt-and-braces against the same activation-ordering race,
                # not evidence it's expected to be missing.
                "helm-eval: helm-collect.service's ReadWritePaths must include -/var/lib/helm-cache";
              assert nixpkgs.lib.assertMsg
                (
                  c.environment.etc."helm/config.json".mode == "0644"
                  && c.environment.etc."helm/config.json".group == "+0"
                )
                # Audit F1: a switch never re-credentials a running session's
                # supplementary groups, so gating this paths-only file on group
                # "helm" stranded helm-collect/helm-status until relogin. Assert
                # the "group" option itself (the string the etc module actually
                # chowns the copied file to, default "+${toString gid}"), not
                # just "gid" -- a definition that overrode "group" directly
                # (bypassing "gid") would slip past a gid-only check while still
                # gating the file on a real group.
                "helm-eval: /etc/helm/config.json must be 0644 with no group";
              assert nixpkgs.lib.assertMsg
                (
                  c.systemd.services.static-web-server.serviceConfig.BindReadOnlyPaths == [
                    "-/var/lib/helm"
                  ]
                )
                # Audit F26: the undashed upstream default fails the unit if
                # /var/lib/helm doesn't exist yet (a fresh switch can race
                # tmpfiles vs. the socket); "-" tolerates that.
                "helm-eval: static-web-server BindReadOnlyPaths must be exactly [ \"-/var/lib/helm\" ]";
              assert nixpkgs.lib.assertMsg (
                nixpkgs.lib.elem "-/var/lib/evidence" c.systemd.user.services.helm-flake-check.serviceConfig.ReadWritePaths
                && nixpkgs.lib.elem "-/var/lib/evidence" c.systemd.user.services.helm-collect.serviceConfig.ReadWritePaths
              ) "helm-eval: both Helm units must be able to write the evidence store";
              assert nixpkgs.lib.assertMsg (
                (c.services.helm.configJsonValue.evidence_dir or null) == "/var/lib/evidence"
              ) "helm-eval: /etc/helm/config.json must carry evidence_dir = /var/lib/evidence";
              assert nixpkgs.lib.assertMsg (
                c.services.helm.evidenceDir == "/var/lib/evidence"
              ) "helm-eval: services.helm.evidenceDir must default to /var/lib/evidence";
              assert nixpkgs.lib.assertMsg (c.systemd.services ? helm-api) "helm-eval: helm-api unit";
              assert nixpkgs.lib.assertMsg (
                c.users.users ? helm-api && c.systemd.services.helm-api.serviceConfig.User == "helm-api"
              ) "helm-eval: helm-api user";
              assert nixpkgs.lib.assertMsg (
                (c.services.helm.configJsonValue.api or { }).listen or null == "127.0.0.1:7710"
              ) "helm-eval: config.json api.listen must be 127.0.0.1:7710";
              assert nixpkgs.lib.assertMsg (
                ((c.services.helm.configJsonValue.api or { }).links or { }).feed or null == "http://127.0.0.1:8080/"
              ) "helm-eval: config.json api.links must carry the feed link";
              # HM5b: the seat job spool must be seat-submit's own jobs directory
              # (DEFAULT_JOBS_DIR = "/var/lib/seat/jobs", pkgs/seat/seat-submit.py:60),
              # never the seat-lane spool — core sets nothing for services.helm.seats,
              # so the rendered config.json spool_dir is the default.
              assert nixpkgs.lib.assertMsg (
                ((c.services.helm.configJsonValue.seats or { }).spool_dir or null) == "/var/lib/seat/jobs"
              ) "helm-eval: config.json seats.spool_dir must default to /var/lib/seat/jobs";
              # HM5: the seat polkit rule keys on the helm-api system user alone
              # (never operatorUser -- the desktop password must not gate a seat
              # start) and must never name helm-switch (the operator's switch stays
              # AUTH_ADMIN_KEEP). In this api-only fixture the extraConfig is the
              # seat rule alone, so "no helm-switch" is scoped to the seat rule.
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.hasInfix "subject.user === \"helm-api\"" c.security.polkit.extraConfig)
                "helm-eval: seat polkit rule";
              assert nixpkgs.lib.assertMsg (
                !nixpkgs.lib.hasInfix "helm-switch" c.security.polkit.extraConfig
              ) "helm-eval: seat polkit rule must not name helm-switch";
              builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "helm-eval-ok" { } "touch $out");
            # The nightly must build every check, not stop at the first failure.
            # `nix flake check` without --keep-going aborts on the first failed
            # build, so one red check hides every check behind it and the single
            # flake-check row says only "fail" -- measured 2026-09-21, when
            # comfyui-vm hid subsystems-manifest hid comfyui-package hid
            # evidence-unit, each found only by fixing the one above it, across
            # four nights that all reported one line. This greps the module's own
            # rendered script rather than re-asserting a string the module never
            # reads, so deleting the flag fails here.
            # NOT a fix for an eval abort: evaluation still dies on the first
            # error (that was 09-18 to 09-21). Per-check rows are the fix for
            # that half, and are not built.
            helm-nightly-keep-going = pkgs.runCommand "helm-nightly-keep-going" { } ''
              exec=${nixpkgs.lib.head (nixpkgs.lib.splitString " " helmEvalSystem.config.systemd.user.services.helm-flake-check.serviceConfig.ExecStart)}
              grep -q -- '--keep-going' "$exec" || {
                echo "helm-nightly-keep-going: the nightly's nix flake check has no --keep-going;" >&2
                echo "one failing check would hide every check behind it. Its invocation is:" >&2
                grep -n 'nix flake check' "$exec" >&2
                exit 1
              }
              grep -q -- '--log-file' "$exec" || {
                echo "helm-nightly-keep-going: the nightly no longer hands the full log to the recorder (ER7)" >&2
                exit 1
              }
              grep -q -- 'helm-flake-check-root /var/lib/helm/flake-check-roots' "$exec" || {
                echo "helm-nightly-keep-going: the nightly no longer roots its build-time closure (BUG-nightly-offline-after-gc)" >&2
                exit 1
              }
              record_line=$(grep -n -- 'record-check --name flake-check' "$exec" | head -1 | cut -d: -f1 || true)
              root_line=$(grep -n -- 'helm-flake-check-root /var/lib/helm/flake-check-roots' "$exec" | head -1 | cut -d: -f1 || true)
              if [ -z "$record_line" ] || [ -z "$root_line" ] || [ "$root_line" -le "$record_line" ]; then
                echo "helm-nightly-keep-going: the rooting call must render after record-check (D3, BUG-nightly-offline-after-gc)" >&2
                exit 1
              fi
              touch $out
            '';
            evidence-eval =
              let
                c = evidenceEvalSystem.config;
              in
              assert nixpkgs.lib.assertMsg
                (
                  nixpkgs.lib.elem "d /var/lib/evidence 0750 alice helm -" c.systemd.tmpfiles.rules
                  && nixpkgs.lib.elem "d /var/lib/evidence/ledger 2770 alice helm -" c.systemd.tmpfiles.rules
                )
                "evidence-eval: the store dir is 0750 alice:helm and its ledger 2770 alice:helm -- setgid and group-writable so helm-api can write engagement.jsonl under ProtectSystem=strict (HM8)";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.any (
                p: (p.pname or p.name or "") == "evidence"
              ) c.environment.systemPackages) "evidence-eval: the evidence CLI must be installed";
              builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "evidence-eval-ok" { } "touch $out");
            helm-assertion-negative =
              let
                attempt = builtins.tryEval helmBadSystem.config.system.build.toplevel.drvPath;
                lanAttempt = builtins.tryEval helmLanMismatchSystem.config.system.build.toplevel.drvPath;
                lanRenamedAttempt = builtins.tryEval helmLanMismatchRenamedSystem.config.system.build.toplevel.drvPath;
                lanOkAttempt = builtins.tryEval helmLanOkSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "helm-assertion-negative: services.helm.listen on 0.0.0.0 DID NOT FAIL the build"
              else if lanAttempt.success then
                throw "helm-assertion-negative: a lan-access site fronting Helm's port with an upstream that is not services.helm.listen DID NOT FAIL the build"
              else if lanRenamedAttempt.success then
                throw "helm-assertion-negative: a lan-access site fronting Helm's port under a different name with an upstream that is not services.helm.listen DID NOT FAIL the build"
              else if !lanOkAttempt.success then
                throw "helm-assertion-negative: a lan-access site whose upstream matches services.helm.listen, alongside one on another port, DID FAIL the build"
              else
                pkgs.runCommand "helm-assertion-negative-ok" { } "touch $out";
            helm-api-assertion-negative-listen =
              let
                attempt = builtins.tryEval helmApiBadListenSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "helm-api-assertion-negative-listen: services.helm.api.listen on 0.0.0.0 DID NOT FAIL the build"
              else
                pkgs.runCommand "helm-api-assertion-negative-listen-ok" { } "touch $out";
            helm-api-assertion-negative-port =
              let
                attempt = builtins.tryEval helmApiBadPortSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "helm-api-assertion-negative-port: services.helm.api.port == port DID NOT FAIL the build"
              else
                pkgs.runCommand "helm-api-assertion-negative-port-ok" { } "touch $out";
            # Helm v1 control (plan Task 3 / consolidated D1/D2/D3). The positive
            # check proves the polkit rule, the switch unit, the user service and
            # the config.json control section all render from the fixed literal
            # allowlist, and that the base and the "alt" specialisation produce
            # byte-identical polkit text (the D1/M4 regression guard).
            helm-control-eval =
              let
                c = helmControlSystem.config;
                alt = c.specialisation.alt.configuration;
                polkit = c.security.polkit.extraConfig;
                altPolkit = alt.security.polkit.extraConfig;
                switchUnit = c.systemd.services."helm-switch@";
                switchExec = switchUnit.serviceConfig.ExecStart;
                switchBin = nixpkgs.lib.head (nixpkgs.lib.splitString " " switchExec);
                serveExec = c.systemd.user.services.helm-serve.serviceConfig.ExecStart;
                configJsonPath = c.environment.etc."helm/config.json".source;
                # The rendered launcher, straight from the module's own
                # substitution (writeShellApplication keeps its text). The bats
                # suite re-renders the template itself and so cannot see the
                # module substitute an empty string or inline JSON for the
                # workspaces file — this eval check reads the module's actual
                # output, so only a real /nix/store/ path passes (H2b M1d).
                launcher =
                  nixpkgs.lib.findFirst (p: (p.name or "") == "helm-open-workspace")
                    (throw "helm-control-eval: helm-open-workspace not found in environment.systemPackages")
                    c.environment.systemPackages;
                launcherText = launcher.text;
              in
              assert nixpkgs.lib.assertMsg (
                polkit == altPolkit
              ) "helm-control-eval: base and alt polkit text must be byte-identical (D1/M4)";
              assert nixpkgs.lib.assertMsg (
                c.services.static-web-server.enable == false
              ) "helm-control-eval: static-web-server must be off under control.enable";
              assert nixpkgs.lib.assertMsg (!(c.systemd.services ? "static-web-server"))
                "helm-control-eval: static-web-server.service must not exist under control.enable — the helm module's own SupplementaryGroups/BindReadOnlyPaths serviceConfig must not outlive the upstream unit (a stray serviceConfig renders 'no ExecStart' and a bad unit file)";
              assert nixpkgs.lib.assertMsg (
                c.systemd.services ? "helm-switch@"
              ) "helm-control-eval: helm-switch@ must exist";
              assert nixpkgs.lib.assertMsg (
                c.systemd.user.services ? helm-serve
              ) "helm-control-eval: helm-serve user service must exist";
              assert nixpkgs.lib.assertMsg (
                switchUnit.serviceConfig.Type == "oneshot" && switchUnit.serviceConfig.TimeoutStartSec == "5min"
              ) "helm-control-eval: helm-switch@ must be oneshot with a 5min timeout";
              assert nixpkgs.lib.assertMsg
                (builtins.match ".*WORKSPACES_JSON_FILE='/nix/store/.*" launcherText != null)
                "helm-control-eval: the rendered helm-open-workspace launcher must substitute WORKSPACES_JSON_FILE with an absolute /nix/store/ path (never inline JSON or an empty string — H2b M1d)";
              builtins.seq c.system.build.toplevel.drvPath (
                pkgs.runCommand "helm-control-eval-ok"
                  {
                    nativeBuildInputs = [ pkgs.jq ];
                    passAsFile = [
                      "polkit"
                      "switchExec"
                      "serveExec"
                    ];
                    inherit polkit switchExec serveExec;
                  }
                  ''
                    # The rendered rule must enumerate exactly the two allowed
                    # instances, gate on verb + user, and approve only via
                    # AUTH_ADMIN_KEEP (the desktop password, D-H1) -- never a
                    # bare YES and never a bare NO.
                    grep -F 'var allowed = ["helm-switch@base.service", "helm-switch@alt.service"];' "$polkitPath"
                    grep -F 'action.lookup("verb") !== "start"' "$polkitPath"
                    grep -F 'subject.user !== "alice"' "$polkitPath"
                    grep -F 'return polkit.Result.AUTH_ADMIN_KEEP;' "$polkitPath"
                    grep -F 'return undefined;' "$polkitPath"
                    if grep -F 'allowed.indexOf(unit) !== -1) { return polkit.Result.YES; }' "$polkitPath"; then
                      echo "helm-control-eval: the rule still returns YES" >&2
                      exit 1
                    fi
                    # The switch unit runs the generated switch script for %i.
                    grep -q 'helm-switch %i' "$switchExecPath"
                    # D-H1: the read-only helm-serve carries no --token-file (a
                    # stale unit line would mint a per-boot token the page no
                    # longer needs).
                    if grep -F -- '--token-file' "$serveExecPath"; then
                      echo "helm-control-eval: helm-serve's ExecStart still passes --token-file" >&2
                      exit 1
                    fi
                    # The generated switch script maps every profile to
                    # switch-to-configuration with the test action only.
                    grep -F 'switch-to-configuration' "${switchBin}"
                    grep -F '"$bin" test' "${switchBin}"
                    # config.json carries the control section serve.py consumes.
                    jq -e '.control.profiles == ["base","alt"]' '${configJsonPath}'
                    jq -e '.control.marker == "/etc/helm/profile"' '${configJsonPath}'
                    jq -e '.control.kgx_bin == "/run/current-system/sw/bin/kgx"' '${configJsonPath}'
                    jq -e '.control.helm_open_workspace_bin == "/run/current-system/sw/bin/helm-open-workspace"' '${configJsonPath}'
                    jq -e '.control.listen == "127.0.0.1:7700"' '${configJsonPath}'
                    jq -e '.control.host_aliases == ["localhost","127.0.0.1"]' '${configJsonPath}'
                    jq -e '.control.workspaces == {}' '${configJsonPath}'
                    touch $out
                  ''
              );
            helm-control-assertion-negative-profiles =
              let
                # G1 (D1): every non-base profile must be a declared specialisation --
                # asserted by the MODULE (nixosModules/helm.nix), not by this check.
                attempt = builtins.tryEval helmControlBadProfilesSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "helm-control-assertion-negative-profiles: profiles=[base nope] DID NOT FAIL the build"
              else
                pkgs.runCommand "helm-control-assertion-negative-profiles-ok" { } "touch $out";
            helm-control-assertion-negative-enable =
              let
                attempt = builtins.tryEval helmControlBadEnableSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "helm-control-assertion-negative-enable: control.enable without services.helm.enable DID NOT FAIL the build"
              else
                pkgs.runCommand "helm-control-assertion-negative-enable-ok" { } "touch $out";
            helm-control-assertion-negative-agentunit =
              let
                badA = helmControlAgentUnitBadSystemA.config;
                badB = helmControlAgentUnitBadSystemB.config;
                attemptA = builtins.tryEval badA.system.build.toplevel.drvPath;
                attemptB = builtins.tryEval badB.system.build.toplevel.drvPath;
                failing =
                  c:
                  nixpkgs.lib.concatStringsSep "\n" (
                    map (a: a.message) (nixpkgs.lib.filter (a: !a.assertion) c.assertions)
                  );
              in
              if attemptA.success then
                throw "helm-control-assertion-negative-agentunit: fixture A (changed egress- unit) DID NOT FAIL the build"
              else if attemptB.success then
                throw "helm-control-assertion-negative-agentunit: fixture B (attrset null-collapse trap) DID NOT FAIL the build"
              else if !(nixpkgs.lib.hasInfix "egress-broker-cowork.service" (failing badA)) then
                throw "helm-control-assertion-negative-agentunit: fixture A failed but did not name egress-broker-cowork.service (got: ${failing badA})"
              else if !(nixpkgs.lib.hasInfix "egress-broker-cowork.service" (failing badB)) then
                throw "helm-control-assertion-negative-agentunit: fixture B failed but did not name egress-broker-cowork.service (got: ${failing badB})"
              else
                pkgs.runCommand "helm-control-assertion-negative-agentunit-ok" { } "touch $out";
            helm-control-assertion-negative-workspace =
              let
                attempt = builtins.tryEval helmControlBadWorkspaceSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "helm-control-assertion-negative-workspace: workspaces.\"Bad Name\" DID NOT FAIL the build"
              else
                pkgs.runCommand "helm-control-assertion-negative-workspace-ok" { } "touch $out";
            # Helm Home (HH3 / D-H4). The positive check proves the module renders
            # home.json and the autostart desktop entry and installs the package,
            # and that control.workspaces stays parked at { } (this module never
            # touches it); the five negative checks each fail for exactly one rule,
            # and the reversibility check proves a disabled home is the host
            # without the module.
            helm-home-eval =
              let
                c = helmHomeSystem.config;
                homeJson = c.environment.etc."helm/home.json";
              in
              assert nixpkgs.lib.assertMsg (
                homeJson.mode == "0644"
              ) "helm-home-eval: helm/home.json must be mode 0644";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "/bin/helm-home"
                c.environment.etc."xdg/autostart/helm-home.desktop".text
              ) "helm-home-eval: the autostart entry must Exec the package's /bin/helm-home";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "OnlyShowIn=GNOME;"
                c.environment.etc."xdg/autostart/helm-home.desktop".text
              ) "helm-home-eval: the autostart entry must carry OnlyShowIn=GNOME;";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.any (
                p: (p.name or "") == "helm-home"
              ) c.environment.systemPackages) "helm-home-eval: the helm-home package must be a system package";
              assert nixpkgs.lib.assertMsg (
                c.services.helm.control.workspaces == { }
              ) "helm-home-eval: the helmHome module must leave services.helm.control.workspaces empty";
              builtins.seq c.system.build.toplevel.drvPath (
                pkgs.runCommand "helm-home-eval-ok"
                  {
                    nativeBuildInputs = [ pkgs.jq ];
                    passAsFile = [ "homeJson" ];
                    homeJson = homeJson.text;
                  }
                  ''
                    jq -e '.schema == 1' "$homeJsonPath"
                    jq -e '.flakes|length == 2' "$homeJsonPath"
                    jq -e '.flakes[0].declaration == "/var/lib/fake-repo#helm"' "$homeJsonPath"
                    jq -e '.flakes[0].profile == "alt"' "$homeJsonPath"
                    jq -e '.flakes[0].seats == ["deepseek"]' "$homeJsonPath"
                    jq -e '.flakes[1].declaration == "/var/lib/other#helm"' "$homeJsonPath"
                    jq -e '.flakes[1].profile == null' "$homeJsonPath"
                    jq -e '.flakes[1].seats == []' "$homeJsonPath"
                    touch $out
                  ''
              );
            helm-home-assertion-negative-enable =
              let
                c = helmHomeBadEnableSystem.config;
                attempt = builtins.tryEval c.system.build.toplevel.drvPath;
                failing = nixpkgs.lib.concatStringsSep "\n" (
                  map (a: a.message) (nixpkgs.lib.filter (a: !a.assertion) c.assertions)
                );
              in
              if attempt.success then
                throw "helm-home-assertion-negative-enable: home enabled with control.enable=false DID NOT FAIL the build"
              else if
                !(nixpkgs.lib.hasInfix "services.helm.home requires services.helm.enable and services.helm.control.enable" failing)
              then
                throw "helm-home-assertion-negative-enable: failed but did not name the rule (got: ${failing})"
              else
                pkgs.runCommand "helm-home-assertion-negative-enable-ok" { } "touch $out";
            helm-home-assertion-negative-path =
              let
                c = helmHomeBadPathSystem.config;
                attempt = builtins.tryEval c.system.build.toplevel.drvPath;
                failing = nixpkgs.lib.concatStringsSep "\n" (
                  map (a: a.message) (nixpkgs.lib.filter (a: !a.assertion) c.assertions)
                );
              in
              if attempt.success then
                throw "helm-home-assertion-negative-path: relative/x DID NOT FAIL the build"
              else if !(nixpkgs.lib.hasInfix "every path must be absolute; offenders: relative/x" failing) then
                throw "helm-home-assertion-negative-path: failed but did not name the rule (got: ${failing})"
              else
                pkgs.runCommand "helm-home-assertion-negative-path-ok" { } "touch $out";
            helm-home-assertion-negative-profile =
              let
                c = helmHomeBadProfileSystem.config;
                attempt = builtins.tryEval c.system.build.toplevel.drvPath;
                failing = nixpkgs.lib.concatStringsSep "\n" (
                  map (a: a.message) (nixpkgs.lib.filter (a: !a.assertion) c.assertions)
                );
              in
              if attempt.success then
                throw "helm-home-assertion-negative-profile: profile=nope DID NOT FAIL the build"
              else if
                !(nixpkgs.lib.hasInfix "profile must be null or one of base alt; offenders: nope" failing)
              then
                throw "helm-home-assertion-negative-profile: failed but did not name the rule (got: ${failing})"
              else
                pkgs.runCommand "helm-home-assertion-negative-profile-ok" { } "touch $out";
            helm-home-assertion-negative-seats =
              let
                attempt = builtins.tryEval helmHomeBadSeatsSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "helm-home-assertion-negative-seats: seats=[claude gpt] DID NOT FAIL the build"
              else
                pkgs.runCommand "helm-home-assertion-negative-seats-ok" { } "touch $out";
            helm-home-assertion-negative-duplicate =
              let
                c = helmHomeBadDuplicateSystem.config;
                attempt = builtins.tryEval c.system.build.toplevel.drvPath;
                failing = nixpkgs.lib.concatStringsSep "\n" (
                  map (a: a.message) (nixpkgs.lib.filter (a: !a.assertion) c.assertions)
                );
              in
              if attempt.success then
                throw "helm-home-assertion-negative-duplicate: two entries with path=/var/lib/fake-repo DID NOT FAIL the build"
              else if !(nixpkgs.lib.hasInfix "a path is declared twice" failing) then
                throw "helm-home-assertion-negative-duplicate: failed but did not name the rule (got: ${failing})"
              else
                pkgs.runCommand "helm-home-assertion-negative-duplicate-ok" { } "touch $out";
            lane-eval =
              let
                c = laneEvalSystem.config;
                unit = c.systemd.services."lane-testlane@";
                sc = unit.serviceConfig;
                i = c.services.egress-broker.instances.testlane;
                # T2 fix round: the public, non-private copy egressBroker.nix's
                # ExecStartPost writes outside the tree InaccessiblePaths hides
                # below -- see nixosModules/modelLane.nix's caBundle comment.
                caBundle = "/var/lib/egress-broker-ca-bundle/testlane/ca-bundle.crt";
              in
              assert nixpkgs.lib.assertMsg
                (
                  i.hostAddress == "10.100.9.1"
                  && i.namespaceAddress == "10.100.9.2"
                  && i.listenPort == 3199
                  && i.allow == [ "example.com" ]
                )
                "lane-eval: egress-broker instance 'testlane' must be rendered from the lane's address block and allow == [ host ]";
              assert nixpkgs.lib.assertMsg (
                i.inject."example.com".valueFile == "/var/lib/secrets/testlane-key"
              ) "lane-eval: egress-broker instance 'testlane' must inject from the lane's keyFile";
              assert nixpkgs.lib.assertMsg (i.denyPaths."example.com".pathPrefixes == [ "/api/v1/messages" ])
                "lane-eval: egress-broker instance 'testlane' must deny /api/v1/messages (fail closed, O3 resolved -- nothing consumes the Anthropic-style messages path)";
              assert nixpkgs.lib.assertMsg (c.users.groups ? lane) "lane-eval: lane group must exist";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "lane" c.users.users.alice.extraGroups)
                "lane-eval: operatorUser must be a member of group lane";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.any
                (r: nixpkgs.lib.hasInfix "/var/lib/secrets/testlane-key" r && nixpkgs.lib.hasInfix "0440" r)
                c.systemd.tmpfiles.rules
              ) "lane-eval: tmpfiles must reset the key file to 0440 root:egress-broker";
              assert nixpkgs.lib.assertMsg
                (
                  # 2770, not 2750, on the lane dir itself (T3 fix, found by
                  # checks.lane-vm): lane-run.py appends to
                  # ledger.jsonl right there, not just under jobs/ or results/.
                  nixpkgs.lib.any (r: r == "d /var/lib/lanes/testlane 2770 root lane -") c.systemd.tmpfiles.rules
                  && nixpkgs.lib.any (
                    r: r == "d /var/lib/lanes/testlane/jobs 2770 root lane -"
                  ) c.systemd.tmpfiles.rules
                  && nixpkgs.lib.any (
                    r: r == "d /var/lib/lanes/testlane/results 2770 root lane -"
                  ) c.systemd.tmpfiles.rules
                )
                "lane-eval: /var/lib/lanes/testlane and its jobs/results subdirs must be tmpfiles-declared with the exact spool permissions";
              assert nixpkgs.lib.assertMsg (
                unit.requires == [ "egress-broker-testlane.service" ]
                && unit.after == [ "egress-broker-testlane.service" ]
              ) "lane-eval: lane-testlane@ must Require+After egress-broker-testlane.service";
              assert nixpkgs.lib.assertMsg
                (
                  sc.Type == "oneshot"
                  && sc.NetworkNamespacePath == "/run/netns/egress-testlane"
                  && sc.DynamicUser == true
                  && nixpkgs.lib.elem "lane" sc.SupplementaryGroups
                  && sc.TimeoutStartSec == "30min"
                )
                "lane-eval: lane-testlane@ must run oneshot in the broker's netns as a dynamic user in group lane, capped at 30min";
              assert nixpkgs.lib.assertMsg (
                sc.ExecStart == "${self.packages.${system}.lane-run}/bin/lane-run testlane %i"
              ) "lane-eval: lane-testlane@ ExecStart must be lane-run's stable path, lane name, then %i";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.any
                (p: nixpkgs.lib.hasPrefix "dsh" (p.pname or p.name or ""))
                c.systemd.services."lane-testlane@".path
              ) "lane-eval: the lane unit's PATH must carry the dsh harness package (dsh job kind)";
              assert nixpkgs.lib.assertMsg (
                sc.ReadWritePaths == [ "/var/lib/lanes/testlane" ]
              ) "lane-eval: lane-testlane@ ReadWritePaths must be exactly /var/lib/lanes/testlane";
              assert nixpkgs.lib.assertMsg (
                sc.NoNewPrivileges == true
                && sc.ProtectSystem == "strict"
                && sc.ProtectHome == true
                && sc.PrivateTmp == true
                && sc.CapabilityBoundingSet == ""
                && sc.RestrictAddressFamilies == "AF_INET AF_INET6 AF_UNIX"
              ) "lane-eval: lane-testlane@ must carry the same hardening as the Helm units";
              assert nixpkgs.lib.assertMsg
                (
                  sc.InaccessiblePaths == [
                    "-/run/baskets"
                    "-/var/lib/baskets"
                    "-/var/lib/helm"
                    "-/var/lib/egress-broker"
                    "-/var/lib/secrets"
                    "-/home"
                  ]
                )
                # T2 (plan Task 2, brief §3 invariants 1/2): ProtectSystem=strict
                # + ProtectHome=true make these read-only or empty, not invisible
                # -- a lane job's own agent-authored code could still list them.
                # InaccessiblePaths makes every path in this list ENOENT to the
                # unit: decrypted basket contents (invariant 1: tmpfs, lifetime
                # of the mounting agent only -- never another process's to
                # stat()), Helm's collected state, the broker's own audit trail
                # and CA material, provider credentials, and the operator's
                # home.
                "lane-eval: lane-testlane@ InaccessiblePaths must hide baskets, Helm state, broker state, secrets and /home";
              assert nixpkgs.lib.assertMsg
                (
                  # Path-component-aware, not a raw string hasPrefix: naive
                  # string prefixing would false-positive on
                  # "/var/lib/egress-broker" against
                  # "/var/lib/egress-broker-ca-bundle/..." (a sibling directory,
                  # sharing a string prefix but not a path ancestor) -- exactly
                  # the public/private split this fix round introduced, so the
                  # check has to know a directory boundary from a shared
                  # substring.
                  !(nixpkgs.lib.any (
                    p:
                    let
                      hidden = nixpkgs.lib.removePrefix "-" p;
                    in
                    unit.environment.SSL_CERT_FILE == hidden
                    || nixpkgs.lib.hasPrefix (hidden + "/") unit.environment.SSL_CERT_FILE
                  ) sc.InaccessiblePaths)
                )
                # T2 fix round (Opus re-gate of 90d9e86, blocker): this class of
                # bug -- hiding a tree the unit's own env vars still point into
                # -- broke checks.lane-vm silently because lane-eval only ever
                # restated the InaccessiblePaths list, never cross-checked it
                # against anything the unit actually reads. Generic (not
                # hardcoded to today's caBundle value) so a future path change
                # on either side of this contract fails HERE, at eval time, not
                # as a TLS error three retries deep in a VM test.
                "lane-eval: no InaccessiblePaths entry may be a prefix of SSL_CERT_FILE -- the unit must still be able to read its own broker's CA bundle";
              assert nixpkgs.lib.assertMsg (sc.UMask == "0027")
                # T2: without this the ledger/result files this unit writes
                # under /var/lib/lanes/<name> inherit whatever umask systemd
                # defaults to (0022 -- world-readable), same class of fix as
                # helm-eval's UMask assertion above.
                "lane-eval: lane-testlane@ must set UMask=0027 so the ledger and results are group-only";
              assert nixpkgs.lib.assertMsg
                (builtins.attrNames c.services.egress-broker.instances == builtins.attrNames c.services.model-lanes)
                # T2: brokerInstance is gone -- the instance name IS the lane
                # name now, so this must hold structurally, not just for
                # "testlane" by coincidence.
                "lane-eval: services.egress-broker.instances keys must be exactly the lane names";
              assert nixpkgs.lib.assertMsg (
                unit.environment.HTTPS_PROXY == "http://10.100.9.1:3199"
                && unit.environment.HTTP_PROXY == "http://10.100.9.1:3199"
              ) "lane-eval: lane-testlane@ must point HTTPS_PROXY/HTTP_PROXY at the broker instance";
              assert nixpkgs.lib.assertMsg (
                unit.environment.NODE_USE_ENV_PROXY == "1"
              ) "lane-eval: lane-testlane@ must set NODE_USE_ENV_PROXY=1 (dsh ignores HTTPS_PROXY without it)";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "/lib/proxy-shim.cjs" (
                unit.environment.NODE_OPTIONS or ""
              )) "lane-eval: lane-testlane@ must preload the dsh proxy shim via NODE_OPTIONS";
              assert nixpkgs.lib.assertMsg (
                unit.environment.SSL_CERT_FILE == caBundle
                && unit.environment.NIX_SSL_CERT_FILE == caBundle
                && unit.environment.NODE_EXTRA_CA_CERTS == caBundle
              ) "lane-eval: lane-testlane@ must point every CA env var at the broker instance's ca-bundle.crt";
              assert nixpkgs.lib.assertMsg (
                unit.environment.LANE_NAME == "testlane"
                && unit.environment.LANE_HOST == "example.com"
                && unit.environment.LANE_MODEL == "test/model-flash"
                && unit.environment.LANE_CLASSES == "permitted"
              ) "lane-eval: lane-testlane@ must export LANE_NAME/LANE_HOST/LANE_MODEL/LANE_CLASSES";
              assert nixpkgs.lib.assertMsg (
                nixpkgs.lib.hasInfix "lane-testlane@" c.security.polkit.extraConfig
                && nixpkgs.lib.hasInfix "\"start\"" c.security.polkit.extraConfig
                && nixpkgs.lib.hasInfix "subject.user == \"alice\"" c.security.polkit.extraConfig
                && nixpkgs.lib.hasInfix "polkit.Result.YES" c.security.polkit.extraConfig
              ) "lane-eval: polkit rule must gate verb=start on lane-testlane@*.service to operatorUser alice";
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.hasInfix ''ip daddr ${i.hostAddress} tcp dport ${toString i.listenPort} iifname != "veb-testlane" drop'' c.networking.nftables.tables.egress-broker.content)
                "lane-eval: input-testlane must drop any non-veb-testlane iifname headed for the broker's own hostAddress:listenPort (plan Task 1: a host-namespace connection must not spend the injected credential)";
              builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "lane-eval-ok" { } "touch $out");
            lane-assertion-negative =
              let
                attempt = builtins.tryEval laneBadSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "lane-assertion-negative: services.model-lanes.testlane.allowedClasses = [ \"local-only\" ] DID NOT FAIL the build"
              else
                pkgs.runCommand "lane-assertion-negative-ok" { } "touch $out";
            lane-unit =
              pkgs.runCommand "lane-unit-tests"
                {
                  nativeBuildInputs = [
                    helmPython
                    pkgs.git
                  ];
                }
                ''
                  mkdir -p pkgs tests
                  cp -r ${self}/pkgs/lane pkgs/lane
                  cp -r ${self}/tests/lane tests/lane
                  # tests/lane/test_forbidden_lists_agree.py reads the guard and
                  # wrapper script by repo-relative path, so the dsh-openrouter
                  # sources must be present in the sandbox too.
                  cp -r ${self}/pkgs/dsh-openrouter pkgs/dsh-openrouter
                  pytest tests/lane -q
                  touch $out
                '';
            seat-assertion-negative =
              let
                keyAttempt = builtins.tryEval seatBadKeySystem.config.system.build.toplevel.drvPath;
                envAttempt = builtins.tryEval seatBadEnvSystem.config.system.build.toplevel.drvPath;
                maxUnitsAttempt = builtins.tryEval seatMaxUnitsZeroSystem.config.system.build.toplevel.drvPath;
                maxUnitsEqWaveAttempt = builtins.tryEval seatMaxUnitsEqWaveSystem.config.system.build.toplevel.drvPath;
                waveJobsAttempt = builtins.tryEval seatWaveJobsZeroSystem.config.system.build.toplevel.drvPath;
                helmPort7700Attempt = builtins.tryEval seatHelmPort7700System.config.system.build.toplevel.drvPath;
                helmPortBrokerAttempt = builtins.tryEval seatHelmPortBrokerSystem.config.system.build.toplevel.drvPath;
                helmPortMovedAttempt = builtins.tryEval seatHelmPortMovedSystem.config.system.build.toplevel.drvPath;
                payloadAttempt = builtins.tryEval dshOpenrouterBrokenPayload.drvPath;
                noAgentsAttempt = builtins.tryEval dshOpenrouterNoAgentsPayload.drvPath;
                emptySkillsAttempt = builtins.tryEval dshOpenrouterEmptySkillsPayload.drvPath;
                portRangeAttempt = builtins.tryEval seatPortRangeNarrowSystem.config.system.build.toplevel.drvPath;
                portRangeOutsideAttempt = builtins.tryEval seatPortRangeOutsideSystem.config.system.build.toplevel.drvPath;
              in
              if keyAttempt.success then
                throw "seat-assertion-negative: services.seat-lane.keyFile = a store path DID NOT FAIL the build"
              else if envAttempt.success then
                throw "seat-assertion-negative: a real-looking key merged into the seat@ unit environment DID NOT FAIL the build"
              else if maxUnitsAttempt.success then
                throw "seat-assertion-negative: services.seat-lane.maxUnits = 0 DID NOT FAIL the build (the maxUnits >= 1 assertion is missing or wrong)"
              else if maxUnitsEqWaveAttempt.success then
                throw "seat-assertion-negative: services.seat-lane.maxUnits = waveJobs (8) DID NOT FAIL the build (the maxUnits > waveJobs assertion is missing or wrong)"
              else if waveJobsAttempt.success then
                throw "seat-assertion-negative: services.seat-lane.waveJobs = 0 DID NOT FAIL the build (the waveJobs >= 1 assertion is missing or wrong)"
              else if helmPort7700Attempt.success then
                throw "seat-assertion-negative: services.seat-lane.helmApiPort = 7700 (control page) DID NOT FAIL the build"
              else if helmPortBrokerAttempt.success then
                throw "seat-assertion-negative: services.seat-lane.helmApiPort = 3141 (broker listenPort) DID NOT FAIL the build"
              else if helmPortMovedAttempt.success then
                throw "seat-assertion-negative: services.seat-lane.helmApiPort = 7701 (services.helm.port moved) DID NOT FAIL the build"
              else if payloadAttempt.success then
                throw "seat-assertion-negative: a harness payload without skills/ DID NOT FAIL the build (the harnessPayload assertion is missing or wrong)"
              else if noAgentsAttempt.success then
                throw "seat-assertion-negative: a harness payload without AGENTS.md DID NOT FAIL the build"
              else if emptySkillsAttempt.success then
                throw "seat-assertion-negative: a harness payload with an empty skills/ DID NOT FAIL the build"
              else if portRangeAttempt.success then
                throw "seat-assertion-negative: services.seat-lane.portRange one port narrower than maxUnits DID NOT FAIL the build (the width assertion is missing or wrong)"
              else if portRangeOutsideAttempt.success then
                throw "seat-assertion-negative: services.seat-lane.portRange outside webPortRange DID NOT FAIL the build (the containment assertion is missing or wrong)"
              else
                pkgs.runCommand "seat-assertion-negative-ok" { } "touch $out";
            # IS11: the rendered Caddyfile is asserted through the vhost extraConfig
            # this module sets (no IFD -- reading config.services.caddy.configFile
            # would import its derivation), plus the renderedHosts list and the
            # firewall guard. lanDisabledSystem is the negative control: it must
            # leave caddy off and the firewall closed.
            lan-eval =
              let
                c = lanEvalSystem.config;
                lac = c.services.lan-access;
                hn = c.networking.hostName;
                helmName = "helm.${hn}.local";
                feedName = "feed.${hn}.local";
                apiName = "api.${hn}.local";
                helmConf = c.services.caddy.virtualHosts.${helmName}.extraConfig;
                feedConf = c.services.caddy.virtualHosts.${feedName}.extraConfig;
                apiConf = c.services.caddy.virtualHosts.${apiName}.extraConfig;
                d = lanDisabledSystem.config;
              in
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "tls internal" helmConf)
                "lan-eval: rendered Caddyfile lacks 'tls internal'";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "basic_auth" helmConf)
                "lan-eval: rendered Caddyfile lacks 'basic_auth'";
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.hasInfix "{file./var/lib/lan-access/helm.bcrypt}" helmConf)
                "lan-eval: basic_auth block does not read its hash from a file";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "reverse_proxy 127.0.0.1:7700" helmConf)
                "lan-eval: rendered Caddyfile lacks 'reverse_proxy 127.0.0.1:7700'";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "reverse_proxy [::1]:7710" apiConf)
                "lan-eval: rendered Caddyfile lacks 'reverse_proxy [::1]:7710'";
              assert nixpkgs.lib.assertMsg (
                !(nixpkgs.lib.hasInfix "/nix/store" helmConf)
                && !(nixpkgs.lib.hasInfix "/nix/store" feedConf)
                && !(nixpkgs.lib.hasInfix "/nix/store" apiConf)
              ) "lan-eval: a basic_auth block contains a /nix/store path";
              assert nixpkgs.lib.assertMsg (
                nixpkgs.lib.sort nixpkgs.lib.lessThan lac.renderedHosts == nixpkgs.lib.sort nixpkgs.lib.lessThan [
                  helmName
                  feedName
                  apiName
                ]
              ) "lan-eval: renderedHosts must be exactly the three site names";
              assert nixpkgs.lib.assertMsg (
                c.networking.firewall.interfaces.eth1.allowedTCPPorts == [
                  80
                  443
                ]
              ) "lan-eval: the LAN interface firewall must open exactly 80/443";
              assert nixpkgs.lib.assertMsg (
                d.services.caddy.enable == false
              ) "lan-eval: lan-access disabled must leave services.caddy.enable false";
              assert nixpkgs.lib.assertMsg (
                (d.networking.firewall.interfaces.eth1 or { }).allowedTCPPorts or [ ] == [ ]
              ) "lan-eval: lan-access disabled but firewall opens 80/443";
              assert nixpkgs.lib.assertMsg (d.services.lan-access.renderedHosts == [ ])
                "lan-eval: lan-access disabled but renderedHosts is non-empty: ${nixpkgs.lib.concatStringsSep ", " d.services.lan-access.renderedHosts}";
              builtins.seq c.system.build.toplevel.drvPath (
                builtins.seq d.system.build.toplevel.drvPath (pkgs.runCommand "lan-eval-ok" { } "touch $out")
              );
            lan-assertion-negative =
              let
                upstreamAttempt = builtins.tryEval lanBadUpstreamSystem.config.system.build.toplevel.drvPath;
                hashStoreAttempt = builtins.tryEval lanHashInStoreSystem.config.system.build.toplevel.drvPath;
                hashOutsideDirAttempt = builtins.tryEval lanHashOutsideDirSystem.config.system.build.toplevel.drvPath;
                foreignHostAttempt = builtins.tryEval lanForeignHostSystem.config.system.build.toplevel.drvPath;
                foreignSiteNameAttempt = builtins.tryEval lanForeignSiteNameSystem.config.system.build.toplevel.drvPath;
              in
              if upstreamAttempt.success then
                throw "lan-assertion-negative: services.lan-access.sites.helm.upstream = 0.0.0.0:7700 DID NOT FAIL the build"
              else if hashStoreAttempt.success then
                throw "lan-assertion-negative: services.lan-access.sites.helm.hashFile = /var/lib/secrets/helm.bcrypt DID NOT FAIL the build"
              else if hashOutsideDirAttempt.success then
                throw "lan-assertion-negative: services.lan-access.sites.helm.hashFile = /var/lib/secrets/helm.bcrypt DID NOT FAIL the build"
              else if foreignHostAttempt.success then
                throw "lan-assertion-negative: a non-loopback Caddy virtual host outside lan-access DID NOT FAIL the build"
              else if foreignSiteNameAttempt.success then
                throw "lan-assertion-negative: a hand-added feed.core.local with listenAddresses 0.0.0.0 DID NOT FAIL the build"
              else
                pkgs.runCommand "lan-assertion-negative-ok" { } "touch $out";
            # FL1 (plan 2026-09-24-fleet-and-forge.md): the fleet module's
            # positive eval check, over the three fixture machines. Core is
            # the operator machine (no sshd, no deploy user, the other two
            # machines' keys in knownHosts and /etc/hosts); forge and lab are
            # deploy-accepting (sshd pinned to the declared address, the nft
            # input rule, the deploy user with the declared keys, the two
            # NOPASSWD sudo commands, trusted-users). The third machine is
            # what makes "every other machine" observable: with one machine
            # beside core, "all" and "all but self" collapse into one entry.
            fleet-eval =
              let
                core = fleetEvalCore.config;
                forge = fleetEvalForge.config;
                lab = fleetEvalLab.config;
                deploySudoRules = builtins.filter (
                  r: builtins.elem "deploy" r.users
                ) forge.security.sudo.extraRules;
                keysUsers = builtins.attrNames forge.users.users;
                join = fleetJoinEval.config;
                joinOff = fleetJoinOff.config;
                joinDeployRules = builtins.filter (r: builtins.elem "deploy" r.users) join.security.sudo.extraRules;
                coreMirror = fleetEvalCoreMirror.config;
              in
              assert nixpkgs.lib.assertMsg (
                !core.services.openssh.enable
              ) "fleet-eval: an operator machine must not run services.openssh";
              assert nixpkgs.lib.assertMsg (
                builtins.attrNames core.programs.ssh.knownHosts == [
                  "forge"
                  "lab"
                ]
              ) "fleet-eval: core's knownHosts must be exactly [ forge lab ]";
              assert nixpkgs.lib.assertMsg (
                core.programs.ssh.knownHosts.forge.hostNames == [
                  "forge"
                  "192.0.2.10"
                ]
              ) "fleet-eval: knownHosts.forge.hostNames must be exactly [ forge 192.0.2.10 ]";
              assert nixpkgs.lib.assertMsg (
                core.programs.ssh.knownHosts.forge.publicKey == fleetFixture.machines.forge.hostKey
              ) "fleet-eval: knownHosts.forge.publicKey must be fleet.machines.forge.hostKey";
              assert nixpkgs.lib.assertMsg (
                core.programs.ssh.knownHosts.lab.hostNames == [
                  "lab"
                  "192.0.2.11"
                ]
              ) "fleet-eval: knownHosts.lab.hostNames must be exactly [ lab 192.0.2.11 ]";
              assert nixpkgs.lib.assertMsg (
                core.programs.ssh.knownHosts.lab.publicKey == fleetFixture.machines.lab.hostKey
              ) "fleet-eval: knownHosts.lab.publicKey must be fleet.machines.lab.hostKey";
              assert nixpkgs.lib.assertMsg (
                core.networking.hosts."192.0.2.10" == [ "forge" ]
              ) "fleet-eval: networking.hosts.192.0.2.10 must be exactly [ forge ]";
              assert nixpkgs.lib.assertMsg (
                core.networking.hosts."192.0.2.11" == [ "lab" ]
              ) "fleet-eval: networking.hosts.192.0.2.11 must be exactly [ lab ]";
              assert nixpkgs.lib.assertMsg (
                !(core.users.users ? deploy)
              ) "fleet-eval: an operator machine must have no deploy user";
              assert nixpkgs.lib.assertMsg (
                builtins.attrNames forge.programs.ssh.knownHosts == [ "lab" ]
              ) "fleet-eval: forge's knownHosts must be exactly [ lab ] (never the machine itself)";
              assert nixpkgs.lib.assertMsg forge.services.openssh.enable
                "fleet-eval: a deploy-accepting machine must run services.openssh";
              assert nixpkgs.lib.assertMsg (
                !forge.services.openssh.openFirewall
              ) "fleet-eval: services.openssh.openFirewall must be false (the nft input rule owns port 22)";
              assert nixpkgs.lib.assertMsg (
                forge.services.openssh.listenAddresses == [
                  {
                    addr = "192.0.2.10";
                    port = 22;
                  }
                ]
              ) "fleet-eval: openssh listenAddresses must be exactly the declared address on port 22";
              assert nixpkgs.lib.assertMsg (
                !forge.services.openssh.settings.PasswordAuthentication
              ) "fleet-eval: openssh settings.PasswordAuthentication must be false";
              assert nixpkgs.lib.assertMsg (
                !forge.services.openssh.settings.KbdInteractiveAuthentication
              ) "fleet-eval: openssh settings.KbdInteractiveAuthentication must be false";
              assert nixpkgs.lib.assertMsg (
                forge.services.openssh.settings.PermitRootLogin == "no"
              ) "fleet-eval: openssh settings.PermitRootLogin must be \"no\"";
              assert nixpkgs.lib.assertMsg forge.networking.nftables.enable
                "fleet-eval: a deploy-accepting machine must enable networking.nftables";
              assert nixpkgs.lib.assertMsg
                (nixpkgs.lib.hasInfix ''iifname "eth1" ip saddr 192.0.2.0/24 tcp dport 22 accept'' forge.networking.firewall.extraInputRules)
                "fleet-eval: the nft input rule must admit port 22 from the LAN subnet on the declared interface";
              assert nixpkgs.lib.assertMsg (
                !(nixpkgs.lib.elem 22 forge.networking.firewall.allowedTCPPorts)
              ) "fleet-eval: port 22 must not be in networking.firewall.allowedTCPPorts";
              assert nixpkgs.lib.assertMsg (
                !(nixpkgs.lib.elem 22 (forge.networking.firewall.interfaces.eth1.allowedTCPPorts or [ ]))
              ) "fleet-eval: port 22 must not be in the eth1 interface's allowedTCPPorts";
              assert nixpkgs.lib.assertMsg (
                forge.users.users.deploy.openssh.authorizedKeys.keys == fleetFixture.deployKeys
              ) "fleet-eval: the deploy user's authorized keys must be exactly fleet.deployKeys";
              assert nixpkgs.lib.assertMsg forge.users.users.deploy.isNormalUser
                "fleet-eval: the deploy user must be a normal user";
              assert nixpkgs.lib.assertMsg (
                builtins.length deploySudoRules == 1
                &&
                  (builtins.head deploySudoRules).commands == [
                    {
                      command = "/run/current-system/sw/bin/nix-env --profile /nix/var/nix/profiles/system --set /nix/store/*";
                      options = [ "NOPASSWD" ];
                    }
                    {
                      command = "/nix/store/*/bin/switch-to-configuration switch";
                      options = [ "NOPASSWD" ];
                    }
                  ]
              ) "fleet-eval: exactly one sudo rule must name deploy, carrying exactly the two NOPASSWD commands";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "deploy" forge.nix.settings.trusted-users)
                "fleet-eval: nix.settings.trusted-users must contain deploy";
              # FL9: the copy's trust rule on the declared forge.
              assert nixpkgs.lib.assertMsg (fleetTrustOk forge)
                "fleet-eval: deploy must be the only trusted user besides root (trusted-users, extra-trusted-users, nix.extraOptions), with require-sigs on";
              assert nixpkgs.lib.assertMsg (builtins.all (
                n: n == "deploy" || forge.users.users.${n}.openssh.authorizedKeys.keys == [ ]
              ) keysUsers) "fleet-eval: no user other than deploy may carry authorized keys";
              assert nixpkgs.lib.assertMsg (
                builtins.attrNames lab.programs.ssh.knownHosts == [ "forge" ]
              ) "fleet-eval: lab's knownHosts must be exactly [ forge ]";
              assert nixpkgs.lib.assertMsg (
                lab.services.openssh.listenAddresses == [
                  {
                    addr = "192.0.2.11";
                    port = 22;
                  }
                ]
              ) "fleet-eval: lab's openssh listenAddresses must be exactly its declared address on port 22";
              # FL5 (plan 2026-09-24-fleet-and-forge.md): the bootstrap module
              # (pkgs/fleet/fleet-join.nix, substituted with the fixture
              # deploy key) -- the same deploy user with the same keys, the
              # module's two sudo commands plus nixos-generate-config and
              # nothing else, deploy trusted, sshd closed to passwords; and
              # with fleet-join.enable = false the bootstrap renders nothing
              # (what the first deploy replaces it with).
              assert nixpkgs.lib.assertMsg (
                (join.users.users ? deploy)
                && join.users.users.deploy.openssh.authorizedKeys.keys == fleetFixture.deployKeys
              ) "fleet-eval: the bootstrap's deploy user must carry exactly fleet.deployKeys";
              assert nixpkgs.lib.assertMsg
                (
                  builtins.length joinDeployRules == 1
                  &&
                    (builtins.head joinDeployRules).commands == (
                      (builtins.head deploySudoRules).commands
                      ++ [
                        {
                          command = "/run/current-system/sw/bin/nixos-generate-config --show-hardware-config";
                          options = [ "NOPASSWD" ];
                        }
                      ]
                    )
                )
                "fleet-eval: the bootstrap's sudo commands must be the module's two plus nixos-generate-config, nothing else";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "deploy" join.nix.settings.trusted-users)
                "fleet-eval: the bootstrap must trust the deploy user";
              assert nixpkgs.lib.assertMsg (fleetTrustOk join)
                "fleet-eval: the bootstrap must trust deploy alone besides root, with require-sigs on";
              # FL9's negative arms: each widened fixture breaks one clause
              # of the rule, so a dropped clause or an || in place of an &&
              # lets that fixture through.
              assert nixpkgs.lib.assertMsg
                (builtins.all (n: !(fleetTrustOk fleetTrustWidened.${n})) (builtins.attrNames fleetTrustWidened))
                "fleet-eval: the trust rule must refuse every widened fixture (trusted-users, extra-trusted-users, nix.extraOptions, require-sigs)";
              assert nixpkgs.lib.assertMsg (
                !join.services.openssh.settings.PasswordAuthentication
              ) "fleet-eval: the bootstrap's sshd must refuse passwords";
              assert nixpkgs.lib.assertMsg (
                !(joinOff.users.users ? deploy)
              ) "fleet-eval: the bootstrap switched off must render no deploy user";
              assert nixpkgs.lib.assertMsg (
                !joinOff.services.openssh.enable
              ) "fleet-eval: the bootstrap switched off must run no sshd";
              # FL7 (plan 2026-09-24-fleet-and-forge.md): the mirror -- an
              # operator machine's user timer pushing main and the live-*
              # tags to the forge. The URL's host is the machine's NAME
              # (networking.hosts resolves it, /etc/ssh/ssh_known_hosts pins
              # it), never its address; the service is oneshot gated on the
              # declared runAs user; no mirror block (fleetEvalCore) and a
              # deploy-accepting machine (fleetEvalForgeMirror) render
              # nothing.
              assert nixpkgs.lib.assertMsg (
                coreMirror.systemd.user.services ? "fleet-mirror"
              ) "fleet-eval: a mirror block must render the fleet-mirror user service";
              assert nixpkgs.lib.assertMsg
                (
                  coreMirror.systemd.user.services."fleet-mirror".environment.FLEET_MIRROR_URL
                  == "ssh://forgejo@forge/operator/nixos-agent-env.git"
                )
                "fleet-eval: FLEET_MIRROR_URL must be ssh://forgejo@forge/operator/nixos-agent-env.git (the machine's name, never its address)";
              assert nixpkgs.lib.assertMsg (
                coreMirror.systemd.user.services."fleet-mirror".environment.FLEET_MIRROR_KEY
                == "/home/tester/.ssh/forge-mirror"
              ) "fleet-eval: FLEET_MIRROR_KEY must be the declared keyFile";
              assert nixpkgs.lib.assertMsg (
                coreMirror.systemd.user.services."fleet-mirror".serviceConfig.Type == "oneshot"
              ) "fleet-eval: the mirror service must be a oneshot";
              assert nixpkgs.lib.assertMsg (
                coreMirror.systemd.user.services."fleet-mirror".unitConfig.ConditionUser == "tester"
              ) "fleet-eval: the mirror service must be conditioned on the declared runAs user";
              assert nixpkgs.lib.assertMsg (
                coreMirror.systemd.user.timers."fleet-mirror".timerConfig.OnCalendar == "hourly"
              ) "fleet-eval: the mirror timer must fire on the declared OnCalendar";
              assert nixpkgs.lib.assertMsg coreMirror.systemd.user.timers."fleet-mirror".timerConfig.Persistent
                "fleet-eval: the mirror timer must be persistent";
              assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "timers.target"
                coreMirror.systemd.user.timers."fleet-mirror".wantedBy
              ) "fleet-eval: the mirror timer must be wanted by timers.target";
              assert nixpkgs.lib.assertMsg (
                !(fleetEvalCore.config.systemd.user.services ? "fleet-mirror")
              ) "fleet-eval: no mirror block must render no fleet-mirror unit";
              assert nixpkgs.lib.assertMsg (
                !(fleetEvalForgeMirror.config.systemd.user.services ? "fleet-mirror")
              ) "fleet-eval: a deploy-accepting machine never mirrors";
              builtins.seq core.system.build.toplevel.drvPath (
                builtins.seq forge.system.build.toplevel.drvPath (
                  builtins.seq lab.system.build.toplevel.drvPath (
                    builtins.seq join.system.build.toplevel.drvPath (
                      builtins.seq joinOff.system.build.toplevel.drvPath (
                        pkgs.runCommand "fleet-eval-ok" { } "touch $out"
                      )
                    )
                  )
                )
              );
            # FL1 (plan 2026-09-24-fleet-and-forge.md): one arm per rule of
            # the fleet module's assertions (Interface 3) -- a machine not
            # declared, both roles at once, a missing/malformed host key, a
            # bad address, an address outside the LAN subnet, an address the
            # interfaces do not carry, empty deploy keys, an operator machine
            # declaring an address, and a foreign sudo rule naming deploy.
            # Each arm must FAIL the evaluation; a green arm is the check's
            # red. Every arm is otherwise a valid machine (the forge arms
            # carry the fixture's eth1 wiring; the bad-address arm widens the
            # LAN to /23, where the spilled 256 still lands inside, so the
            # ONLY refusal is the one the arm names) -- each arm discrimina-
            # tes its rule, so deleting that rule turns it green.
            fleet-assertion-negative =
              let
                operatorSshdSystem = mkFleetEval "core" { services.openssh.enable = true; };
                bothRolesSystem = mkFleetEval "core" {
                  fleet.machines.core = nixpkgs.lib.mkForce {
                    roles = [
                      "operator"
                      "forge"
                    ];
                    address = "192.0.2.20";
                    prefix = 24;
                    interface = "eth1";
                    hostKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHm7m00e2naloG1lBVeaovQtDipZNjtMKtakBm1qVNoI";
                    efi = true;
                    stateVersion = "25.11";
                  };
                  networking.interfaces.eth1.ipv4.addresses = [
                    {
                      address = "192.0.2.20";
                      prefixLength = 24;
                    }
                  ];
                };
                missingHostkeySystem = mkFleetEval "forge" {
                  fleet.machines.forge.hostKey = nixpkgs.lib.mkForce null;
                  networking.interfaces.eth1.ipv4.addresses = [
                    {
                      address = "192.0.2.10";
                      prefixLength = 24;
                    }
                  ];
                };
                badKeyShapeSystem = mkFleetEval "forge" {
                  fleet.machines.forge.hostKey = nixpkgs.lib.mkForce "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBsCvg7ed6UUs7JOwbF9jJQiMok+UFpdq0ZcRRP6jzbf= with-a-comment";
                  networking.interfaces.eth1.ipv4.addresses = [
                    {
                      address = "192.0.2.10";
                      prefixLength = 24;
                    }
                  ];
                };
                badAddressSystem = mkFleetEval "forge" {
                  fleet.machines.forge.address = nixpkgs.lib.mkForce "192.0.2.256";
                  fleet.lan.subnet = nixpkgs.lib.mkForce "192.0.2.0/23";
                  networking.interfaces.eth1.ipv4.addresses = nixpkgs.lib.mkForce [
                    {
                      address = "192.0.2.256";
                      prefixLength = 23;
                    }
                  ];
                };
                outsideSubnetSystem = mkFleetEval "forge" {
                  fleet.lan = nixpkgs.lib.mkForce {
                    subnet = "198.51.100.0/24";
                    gateway = "192.0.2.1";
                    nameservers = [ "192.0.2.1" ];
                  };
                  networking.interfaces.eth1.ipv4.addresses = [
                    {
                      address = "192.0.2.10";
                      prefixLength = 24;
                    }
                  ];
                };
                addressUnconfiguredSystem = mkFleetEval "forge" {
                  networking.interfaces.eth1.ipv4.addresses = nixpkgs.lib.mkForce [ ];
                };
                noDeployKeysSystem = mkFleetEval "forge" {
                  fleet.deployKeys = nixpkgs.lib.mkForce [ ];
                  networking.interfaces.eth1.ipv4.addresses = [
                    {
                      address = "192.0.2.10";
                      prefixLength = 24;
                    }
                  ];
                };
                undeclaredHostSystem = mkFleetEval "core" { networking.hostName = nixpkgs.lib.mkForce "ghost"; };
                operatorWithAddressSystem = mkFleetEval "core" {
                  fleet.machines.core.address = nixpkgs.lib.mkForce "192.0.2.1";
                };
                foreignSudoRuleSystem = mkFleetEval "forge" {
                  security.sudo.extraRules = [
                    {
                      users = [ "deploy" ];
                      commands = [
                        {
                          command = "/run/current-system/sw/bin/id";
                          options = [ "NOPASSWD" ];
                        }
                      ];
                    }
                  ];
                  networking.interfaces.eth1.ipv4.addresses = [
                    {
                      address = "192.0.2.10";
                      prefixLength = 24;
                    }
                  ];
                };
                operatorSshdAttempt = builtins.tryEval operatorSshdSystem.config.system.build.toplevel.drvPath;
                bothRolesAttempt = builtins.tryEval bothRolesSystem.config.system.build.toplevel.drvPath;
                missingHostkeyAttempt = builtins.tryEval missingHostkeySystem.config.system.build.toplevel.drvPath;
                badKeyShapeAttempt = builtins.tryEval badKeyShapeSystem.config.system.build.toplevel.drvPath;
                badAddressAttempt = builtins.tryEval badAddressSystem.config.system.build.toplevel.drvPath;
                outsideSubnetAttempt = builtins.tryEval outsideSubnetSystem.config.system.build.toplevel.drvPath;
                addressUnconfiguredAttempt = builtins.tryEval addressUnconfiguredSystem.config.system.build.toplevel.drvPath;
                noDeployKeysAttempt = builtins.tryEval noDeployKeysSystem.config.system.build.toplevel.drvPath;
                undeclaredHostAttempt = builtins.tryEval undeclaredHostSystem.config.system.build.toplevel.drvPath;
                operatorWithAddressAttempt = builtins.tryEval operatorWithAddressSystem.config.system.build.toplevel.drvPath;
                foreignSudoRuleAttempt = builtins.tryEval foreignSudoRuleSystem.config.system.build.toplevel.drvPath;
                # FL7 (plan 2026-09-24-fleet-and-forge.md): the mirror
                # assertion arms -- a machine the declaration does not name,
                # a repo without the .git suffix, and a runAs user that is
                # not declared. Each arm is otherwise a valid mirror block
                # (the tester user declared, the other two fields legal), so
                # each arm discriminates its rule and deleting that rule
                # turns it green.
                mirrorGhostMachineAttempt =
                  builtins.tryEval
                    (mkFleetEval "core" {
                      fleet.mirror = fleetMirrorFixture // {
                        machine = "ghost";
                      };
                      users.users.tester = {
                        isNormalUser = true;
                      };
                    }).config.system.build.toplevel.drvPath;
                mirrorBadRepoAttempt =
                  builtins.tryEval
                    (mkFleetEval "core" {
                      fleet.mirror = fleetMirrorFixture // {
                        repo = "operator/nixos-agent-env";
                      };
                      users.users.tester = {
                        isNormalUser = true;
                      };
                    }).config.system.build.toplevel.drvPath;
                mirrorUnknownUserAttempt =
                  builtins.tryEval
                    (mkFleetEval "core" {
                      fleet.mirror = fleetMirrorFixture // {
                        runAs = "nobody-here";
                      };
                      users.users.tester = {
                        isNormalUser = true;
                      };
                    }).config.system.build.toplevel.drvPath;
              in
              if operatorSshdAttempt.success then
                throw "fleet-assertion-negative: operator-sshd DID NOT FAIL the build"
              else if bothRolesAttempt.success then
                throw "fleet-assertion-negative: both-roles DID NOT FAIL the build"
              else if missingHostkeyAttempt.success then
                throw "fleet-assertion-negative: missing-hostkey DID NOT FAIL the build"
              else if badKeyShapeAttempt.success then
                throw "fleet-assertion-negative: bad-key-shape DID NOT FAIL the build"
              else if badAddressAttempt.success then
                throw "fleet-assertion-negative: bad-address DID NOT FAIL the build"
              else if outsideSubnetAttempt.success then
                throw "fleet-assertion-negative: outside-subnet DID NOT FAIL the build"
              else if addressUnconfiguredAttempt.success then
                throw "fleet-assertion-negative: address-unconfigured DID NOT FAIL the build"
              else if noDeployKeysAttempt.success then
                throw "fleet-assertion-negative: no-deploy-keys DID NOT FAIL the build"
              else if undeclaredHostAttempt.success then
                throw "fleet-assertion-negative: undeclared-host DID NOT FAIL the build"
              else if operatorWithAddressAttempt.success then
                throw "fleet-assertion-negative: operator-with-address DID NOT FAIL the build"
              else if foreignSudoRuleAttempt.success then
                throw "fleet-assertion-negative: foreign-sudo-rule DID NOT FAIL the build"
              else if mirrorGhostMachineAttempt.success then
                throw "fleet-assertion-negative: mirror-ghost-machine DID NOT FAIL the build"
              else if mirrorBadRepoAttempt.success then
                throw "fleet-assertion-negative: mirror-bad-repo DID NOT FAIL the build"
              else if mirrorUnknownUserAttempt.success then
                throw "fleet-assertion-negative: mirror-unknown-user DID NOT FAIL the build"
              else
                pkgs.runCommand "fleet-assertion-negative-ok" { } "touch $out";
            seat-unit =
              pkgs.runCommand "seat-unit-tests"
                {
                  nativeBuildInputs = [ helmPython ];
                }
                ''
                  mkdir -p pkgs tests
                  cp -r ${self}/pkgs/seat pkgs/seat
                  cp -r ${self}/tests/seat tests/seat
                  pytest tests/seat -q
                  touch $out
                '';
            lane-vm = import ./tests/integration/lane-vm.nix {
              inherit pkgs;
              egressBrokerModule = self.nixosModules.egressBroker;
              modelLaneModule = self.nixosModules.modelLane;
            };
            seat-vm = import ./tests/integration/seat-vm.nix {
              inherit pkgs;
              egressBrokerModule = self.nixosModules.egressBroker;
              seatLaneModule = self.nixosModules.seatLane;
              seatSubmit = seatTools.seat-submit;
            };
            lan-vm = import ./tests/integration/lan-vm.nix {
              inherit pkgs;
              lanAccessModule = self.nixosModules.lanAccess;
            };
            # FL6 (plan 2026-09-24-fleet-and-forge.md, D8): the two-machine
            # fleet test -- enrol the forge, pin its host key, refuse the
            # undeclared deploy key, deploy the declared specialisation (D8:
            # the module's sshd, firewall, deploy user and sudo set replace
            # the bootstrap in one switch) and roll back to the bootstrap.
            fleet-vm = import ./tests/integration/fleet-vm.nix {
              inherit pkgs;
              fleetModule = self.nixosModules.fleet;
              fleetPackage = self.packages.${system}.fleet;
              fleetJoinTemplate = ./pkgs/fleet/fleet-join.nix;
            };
            basket-vm = import ./tests/integration/basket-vm.nix {
              inherit pkgs;
              basketPackage = basket;
            };
            # Invariant aggregates (IS19) — one named check per brief §3 invariant
            # 1, 2, 3, 5, so the rules audit has a single `check` name per row
            # (docs/ledger/rules.toml rows R-invariant-basket-tmpfs,
            # R-invariant-credential-plaintext, R-invariant-egress-chokepoint,
            # R-invariant-policy-nix). Each aggregate is a runCommand whose only
            # job is to depend on the checks that prove its invariant: it builds
            # green iff every component builds green (a red component fails the
            # aggregate's derivation) and runs nothing of its own —
            # `echo $deps > $out` stringifies the component list, which forces
            # them as build inputs. Membership rule: an aggregate lists every
            # check whose task's `Tests` line names a mutant of that invariant.
            # The lists below are that rule's extension at this task's base; a
            # later task that adds such a check appends its name here in the same
            # commit — a name absent from this file makes the aggregate fail eval.
            # Note that `lane-vm` (the model *lane* VM, tests/integration/lane-vm.nix)
            # and `lan-vm` (IS12's *LAN* access test) differ by one letter, and only
            # `lane-vm` is a member — `lan-vm` proves ingress, not egress.
            # Invariant 1 (R-invariant-basket-tmpfs): "Decrypted basket contents exist
            # only for the lifetime of the agent that mounted them, and only in tmpfs."
            invariant-basket-tmpfs = pkgs.runCommand "invariant-basket-tmpfs" {
              deps = [
                self.checks.${system}.basket-vm
                self.checks.${system}.unit
              ];
            } "echo $deps > $out";
            # Invariant 2 (R-invariant-credential-plaintext): "No agent process holds a
            # provider credential on disk or in its environment in plaintext.
            # Credentials are injected at an egress proxy."
            invariant-credential-plaintext = pkgs.runCommand "invariant-credential-plaintext" {
              deps = [
                self.checks.${system}.seat-assertion-negative
                self.checks.${system}.lane-assertion-negative
                self.checks.${system}.module-eval
                self.checks.${system}.addon
              ];
            } "echo $deps > $out";
            # Invariant 3 (R-invariant-egress-chokepoint): "Every byte leaving the
            # machine crosses one chokepoint that can log the request and refuse it."
            invariant-egress-chokepoint = pkgs.runCommand "invariant-egress-chokepoint" {
              deps = [
                self.checks.${system}.addon
                self.checks.${system}.integration
                self.checks.${system}.lane-vm
                self.checks.${system}.seat-vm
              ];
            } "echo $deps > $out";
            # Invariant 5 (R-invariant-policy-nix): "Policy — which data class may
            # reach which model — is Nix configuration, reviewable in a diff. Not a
            # runtime setting, not a dotfile an agent can edit."
            invariant-policy-nix = pkgs.runCommand "invariant-policy-nix" {
              deps = [
                self.checks.${system}.assertion-negative
                self.checks.${system}.lane-assertion-negative
                self.checks.${system}.seat-assertion-negative
                self.checks.${system}.manifests-validate
              ];
            } "echo $deps > $out";
            telemetry-vm = import ./tests/integration/telemetry-vm.nix {
              inherit pkgs;
              claudeTelemetryModule = self.nixosModules.claudeTelemetry;
              evidenceStoreModule = self.nixosModules.evidenceStore;
            };
            integration = import ./tests/integration/broker-vm.nix {
              inherit pkgs;
              egressBrokerModule = self.nixosModules.egressBroker;
            };
            proton-backup-vm = import ./tests/integration/proton-backup-vm.nix {
              inherit pkgs;
              protonBackupModule = self.nixosModules.protonBackup;
            };
            helm-vm = import ./tests/integration/helm-vm.nix {
              inherit pkgs;
              # HM8c: the VM enables services.helm.api, whose ReadWritePaths names
              # config.services.evidence-store -- load evidenceStore beside helm so
              # that attribute resolves (the review's MAJOR-2 missed this fixture).
              # HM12: imports alone leave the tmpfiles rule under lib.mkIf cfg.enable
              # unrun, so /var/lib/evidence/ledger never exists and helm-api fails
              # mount namespacing (226/NAMESPACE) -- enable the store here too, the
              # same fix HM11 applied to helm-control-vm.
              helmModule = {
                imports = [
                  self.nixosModules.helm
                  self.nixosModules.evidenceStore
                ];
                services.evidence-store = {
                  enable = true;
                  # The VM's operator is alice (tests/integration/helm-vm.nix:24);
                  # group helm so helm-api (group helm) can write the ledger under
                  # ProtectSystem.
                  owner = "alice";
                  group = "helm";
                };
              };
            };
            # Helm v1 (plan Task 4 / consolidated D4): the real runtime proof —
            # a `switch-to-configuration test` into a real specialisation driven
            # through the loopback page, the full negative matrix, live polkit
            # denials, the agent-unit NRestarts invariants and the D1 allowlist
            # stability at the artifact level. Long: it builds two toplevels.
            helm-control-vm = import ./tests/integration/helm-control-vm.nix {
              inherit pkgs;
              # HM11: services.helm.api's ReadWritePaths names
              # config.services.evidence-store (HM8b, nixosModules/helm.nix:930)
              # -- load evidenceStore beside helm here too, the same gap HM8c
              # closed for helm-vm just above. The store is also *enabled* (as
              # on hosts/core) so its tmpfiles rule creates /var/lib/evidence/
              # ledger at boot -- without it the unit's ReadWritePaths source
              # doesn't exist and helm-api fails at NAMESPACE setup.
              helmModule = {
                imports = [
                  self.nixosModules.helm
                  self.nixosModules.evidenceStore
                ];
                services.evidence-store = {
                  enable = true;
                  # The VM's operator is alice (tests/integration/helm-control-vm.nix:42); group helm so
                  # helm-api (group helm) can write the ledger under ProtectSystem.
                  owner = "alice";
                  group = "helm";
                };
              };
            };
            # GC1: the nightly's own GC-roots contract, proved in a VM --
            # rooted fixtures survive `nix-collect-garbage`, dropped ones
            # are released, a broken batch still flips, a zero-path run
            # releases everything, stale generations are swept, a `.drv`
            # never reaches --realise, and an eval failure keeps
            # yesterday's roots (BUG-nightly-offline-after-gc).
            helm-gc-roots-vm = import ./tests/integration/helm-gc-roots-vm.nix {
              inherit pkgs;
              helmModule = self.nixosModules.helm;
            };
            managed-settings =
              let
                # Compare against the module's *rendered* default instead of a
                # stale literal (it drifted twice already: 62ccfc4, ed2ec8b) --
                # plan Task 1. Also prove the cowork broker instance's allow list
                # can't silently diverge from claude-managed-settings.allowedDomains:
                # managedSettingsSystem's test module derives `allow` FROM
                # allowedDomains (see above), so this equality holds by
                # construction and this check is a regression guard against a
                # future edit reintroducing a separate literal.
                managedDomains = managedSettingsSystem.config.services.claude-managed-settings.allowedDomains;
                brokerAllow = managedSettingsSystem.config.services.egress-broker.instances.cowork.allow;
                expectedDomainsJSON = builtins.toJSON managedDomains;
              in
              if brokerAllow != managedDomains then
                throw "managed-settings: egress-broker cowork instance allow list has drifted from claude-managed-settings.allowedDomains"
              else
                pkgs.runCommand "managed-settings-check"
                  {
                    nativeBuildInputs = [ pkgs.jq ];
                  }
                  ''
                    f=${managedSettingsSystem.config.environment.etc."claude-code/managed-settings.json".source}
                    jq -e '.allowManagedPermissionRulesOnly == true' "$f"
                    jq -e '.allowManagedHooksOnly == true' "$f"
                    jq -e '.allowManagedMcpServersOnly == true' "$f"
                    jq -e '.sandbox.network.allowManagedDomainsOnly == true' "$f"
                    jq -e '.sandbox.network.strictAllowlist == true' "$f"
                    jq -e '.sandbox.filesystem.allowManagedReadPathsOnly == true' "$f"
                    jq -e '.permissions.disableBypassPermissionsMode == "disable"' "$f"
                    jq -e --argjson expected '${expectedDomainsJSON}' '.sandbox.network.allowedDomains == $expected' "$f"
                    jq -e '.env.HTTPS_PROXY == "http://10.100.1.1:3129"' "$f"
                    jq -e '.env.HTTP_PROXY == "http://10.100.1.1:3129"' "$f"
                    jq -e '.env.NODE_EXTRA_CA_CERTS == "/var/lib/egress-broker/cowork/ca/ca.pem"' "$f"
                    touch $out
                  '';
            cowork-eval =
              let
                unitText = coworkEvalSystem.config.systemd.units."cowork.service".text;
                userUnitText = coworkEvalSystem.config.systemd.user.units."cowork-display.service".text;
                # Root-cause regression guard (2026-09-02 "Sending..." hang): the
                # Cowork VM image + Claude Code harness bundle are fetched from
                # downloads.claude.ai at first session start (see
                # docs/research-2026-09-02-cowork-sending-hang.md). Eval-time
                # JSON of the rendered broker allow list, grepped below, so a
                # future edit that drops the domain fails this check instead of
                # silently reintroducing the hang.
                brokerAllowJSON = builtins.toJSON coworkEvalSystem.config.services.egress-broker.instances.cowork.allow;
                # Field bug 2026-09-02 ("Claude Code crashed", exit 127): the
                # desktop spawns a downloaded generic-Linux Claude Code binary on
                # the host, which NixOS cannot start without nix-ld. cowork.nix
                # must keep declaring it; evaluate to a string so dropping it
                # fails this check at eval time with a message, not a grep.
                nixLdEnabled =
                  if coworkEvalSystem.config.programs.nix-ld.enable then
                    "true"
                  else
                    throw "cowork-eval: cowork.nix must enable programs.nix-ld (the desktop app runs a downloaded dynamically-linked Claude Code binary on the host; exit 127 / stub-ld field bug 2026-09-02)";
                # Field bug 2026-09-02 19:20: the upstream module's systemPackages
                # entry exposed the proxied app (and its .desktop launcher) to the
                # operator, who started a second instance outside the bubble. Only
                # cowork.service may run the app: no package named claude-desktop
                # may be in the system profile.
                noHostInstall =
                  if
                    builtins.any (
                      p: (p.pname or p.name or "") == "claude-desktop"
                    ) coworkEvalSystem.config.environment.systemPackages
                  then
                    throw "cowork-eval: claude-desktop must not be in environment.systemPackages (operator-launchable host instance outside the netns, field bug 2026-09-02)"
                  else
                    "true";
              in
              pkgs.runCommand "cowork-eval-check"
                {
                  passAsFile = [
                    "unitText"
                    "userUnitText"
                  ];
                  inherit
                    unitText
                    userUnitText
                    nixLdEnabled
                    noHostInstall
                    ;
                }
                ''
                  grep -q '^NetworkNamespacePath=/var/run/netns/egress-cowork$' "$unitTextPath"
                  grep -q '^User=claude-app$' "$unitTextPath"
                  grep -q '^Group=claude-app$' "$unitTextPath"
                  # ExecStart wraps the actual waypipe invocation inside a
                  # generated launch script (dbus-run-session for the session
                  # bus, ed2ec8b/9bb86a9), so it no longer names waypipe/
                  # claude-desktop directly -- resolve that script's store path
                  # out of the unit text and check ITS content for the wiring
                  # this line used to assert directly (pre-existing drift found
                  # while making this check green for Task 1, unrelated to the
                  # downloads.claude.ai allowlist below).
                  grep -q '^ExecStart=.*dbus-run-session -- .*-cowork-launch$' "$unitTextPath"
                  launchScript=$(sed -n 's/^ExecStart=.*-- \(\S*cowork-launch\)$/\1/p' "$unitTextPath")
                  grep -q 'waypipe --no-gpu --socket /run/claude-gui/wp.sock server -- .*/bin/claude-desktop$' "$launchScript"
                  grep -q '^ProtectSystem=strict$' "$unitTextPath"
                  grep -q '/dev/kvm rw' "$unitTextPath"
                  grep -q '/dev/vhost-vsock rw' "$unitTextPath"
                  grep -q '^ExecStart=.*waypipe --no-gpu --socket /run/claude-gui/wp.sock client$' "$userUnitTextPath"
                  # Field bug 2026-09-02 19:32: stale relay socket after a killed
                  # client -> EADDRINUSE -> app dies. The relay must clear it.
                  grep -q '^ExecStartPre=.*/rm -f /run/claude-gui/wp.sock$' "$userUnitTextPath"
                  # Field bug 2026-09-02 19:36: a 0755 relay socket is unreachable for
                  # claude-app (EACCES); the directory is the boundary, so the relay
                  # must create the socket with a permissive umask.
                  grep -q '^UMask=0000$' "$userUnitTextPath"
                  grep -q '"downloads.claude.ai"' <<<'${brokerAllowJSON}'
                  # Broker CA overlay (plan Task 2, cowork-sending-hang): the
                  # Cowork VM helper reads the HOST file
                  # /etc/ssl/certs/ca-certificates.crt and installs every cert
                  # in it into the guest's trust store, so the broker CA must
                  # land there -- scoped to this unit's own mount namespace,
                  # never host-wide.
                  grep -q '^BindReadOnlyPaths=/var/lib/egress-broker/cowork/ca/ca-bundle.crt:/etc/ssl/certs/ca-certificates.crt$' "$unitTextPath"
                  # Session shell (plan Task 4, cowork-sending-hang): the desktop
                  # app resolves its session environment by running
                  # "$SHELL -l -i -c env"; systemd otherwise exports the
                  # claude-app system user's login shell (nologin), which fails
                  # every session start (journal: "Attempted login by UNKNOWN
                  # (UID: 991)"). NixOS renders one Environment="K=V" line per
                  # variable, so a plain literal match is exact here.
                  grep -q '^Environment="SHELL=/bin/sh"$' "$unitTextPath"
                  # In-bubble browser (plan Task 4): the Electron wrapper exports
                  # LD_LIBRARY_PATH from claude-desktop's own nixpkgs (glibc 2.42
                  # world); host chromium (glibc 2.40) inherits it via xdg-open
                  # and aborts with GLIBC_ABI_DT_X86_64_PLT (reproduced
                  # 2026-09-02). Resolve the chromium-browser wrapper out of the
                  # unit's own rendered PATH (not a hardcoded store path) and
                  # grep its script for the fix, so this fails if the wrapper is
                  # ever dropped from the unit's PATH or the fix is reverted.
                  pathLine=$(grep '^Environment="PATH=' "$unitTextPath")
                  pathValue=''${pathLine#Environment=\"PATH=}
                  pathValue=''${pathValue%\"}
                  browserScript=""
                  IFS=':' read -ra pathDirs <<<"$pathValue"
                  for d in "''${pathDirs[@]}"; do
                    if [ -x "$d/chromium-browser" ]; then
                      browserScript="$d/chromium-browser"
                      break
                    fi
                  done
                  if [ -z "$browserScript" ]; then
                    echo "cowork-eval: chromium-browser wrapper not found on cowork.service's PATH" >&2
                    exit 1
                  fi
                  grep -q 'env -u LD_LIBRARY_PATH' "$browserScript"
                  [ "$nixLdEnabled" = "true" ]
                  [ "$noHostInstall" = "true" ]
                  touch $out
                '';
            # Phase 4b rescope: asserts hosts/core does NOT write the lockdown
            # machine-wide (services.claude-managed-settings.enable = false
            # there), and that Cowork still gets the identical rendered JSON,
            # provisioned as claude-app's user-scope settings via a systemd
            # tmpfiles rule -- the orchestrator blast-radius fix this rescope is
            # for.
            managed-settings-user-scope =
              let
                # Evaluated against the module (coworkEvalSystem), not hosts/core:
                # since decision 2026-09-02-cowork-tier-parked the bubble is off
                # on core, but the module's user-scope contract must keep holding.
                coreCfg = coworkEvalSystem.config;
                etcHasManagedSettings = coreCfg.environment.etc ? "claude-code/managed-settings.json";
                tmpfilesRules = coreCfg.systemd.tmpfiles.rules;
                settingsRule = nixpkgs.lib.lists.findFirst (
                  r: nixpkgs.lib.strings.hasInfix ".claude/settings.json" r
                ) null tmpfilesRules;
                settingsFile = coreCfg.services.claude-managed-settings.settingsFile;
              in
              if etcHasManagedSettings then
                throw "managed-settings-user-scope: the cowork module writes /etc/claude-code/managed-settings.json machine-wide"
              else if settingsRule == null then
                throw "managed-settings-user-scope: no systemd.tmpfiles rule provisions claude-app's .claude/settings.json"
              else
                pkgs.runCommand "managed-settings-user-scope-check"
                  {
                    nativeBuildInputs = [ pkgs.jq ];
                  }
                  ''
                    f=${settingsFile}
                    jq -e '.env.HTTPS_PROXY == "http://10.100.1.1:3129"' "$f"
                    jq -e '.env.HTTP_PROXY == "http://10.100.1.1:3129"' "$f"
                    jq -e '.sandbox.network.allowManagedDomainsOnly == true' "$f"
                    jq -e '.allowManagedPermissionRulesOnly == true' "$f"
                    touch $out
                  '';
            managed-settings-assertion-negative =
              let
                attempt = builtins.tryEval managedSettingsBadSystem.config.system.build.toplevel.drvPath;
              in
              if attempt.success then
                throw "managed-settings-assertion-negative: brokerInstance named a nonexistent egress-broker instance and the build DID NOT FAIL"
              else
                pkgs.runCommand "managed-settings-assertion-negative-ok" { } "touch $out";
            module-eval =
              (nixpkgs.lib.nixosSystem {
                inherit system;
                modules = [
                  self.nixosModules.egressBroker
                  (_: {
                    boot.loader.grub.enable = false;
                    fileSystems."/".device = "none";
                    fileSystems."/".fsType = "tmpfs";
                    system.stateVersion = "25.11";
                    services.egress-broker.instances.smoke = {
                      hostAddress = "10.100.0.1";
                      namespaceAddress = "10.100.0.2";
                      allow = [ "example.com" ];
                    };
                  })
                ];
              }).config.system.build.toplevel;
            unit =
              pkgs.runCommand "unit-tests"
                {
                  nativeBuildInputs = [
                    pkgs.bats
                    basket
                    protonBackupPush
                    # tests/unit/70-dsh-openrouter.bats boots the real harness against
                    # tests/mocks/openai-fake.py (python3) on the sandbox's loopback.
                    dshOpenrouter
                    pkgs.python3
                    # the --denials reader (dsh-denials, joined into dshOpenrouter
                    # above) shells out to `zstd -dc` to read a fixture transcript
                    # under tests/fixtures/dsh-sessions -- same reason as
                    # ledger-unit's pkgs.zstd above.
                    pkgs.zstd
                    # tests/unit/80-seat-driver.bats drives factory-ws's "is this a
                    # git repository" gate, so git must be on the sandbox PATH.
                    pkgs.git
                    # tests/unit/90-session-start.bats reads .claude/settings.json
                    # (the hook wiring file) with jq, so jq must be on the sandbox
                    # PATH for those cases to run rather than skip.
                    pkgs.jq
                  ]
                  ++ basketRuntimeInputs;
                  # SA8: the payload seam -- the good fixture's store path (for
                  # the bats case that binds DSH_HARNESS_PAYLOAD by hand) and the
                  # packaged wrapper with the payload baked into its runtimeEnv
                  # (for the case that proves the export, not a hand-set
                  # variable, is what deploys).
                  DSH_OPENROUTER_PAYLOAD_FIXTURE = ./tests/fixtures/harness-payload;
                  DSH_OPENROUTER_WITH_PAYLOAD = dshOpenrouterWithPayload;
                }
                ''
                  cp -r ${self}/tests tests
                  chmod -R u+w tests
                  # tests/unit/80-helm-switch.bats and 81-helm-open-workspace.bats
                  # read the script templates from pkgs/helm, substituting the
                  # @PLACEHOLDERS@ the way nixosModules/helm.nix will -- copy
                  # them in at the repo-relative path the tests resolve from
                  # tests/unit (templates are only read, never executed there).
                  mkdir -p pkgs
                  cp -r ${self}/pkgs/helm pkgs/helm
                  # tests/unit/82-factory-dispatch.bats runs the REAL task graph
                  # (pkgs/evidence/tasks.py) against a fixture repo, so the graph
                  # and its ledger must be present for those tests to run rather
                  # than skip -- mirror how 80-seat-driver's routing table is
                  # copied in.
                  cp -r ${self}/pkgs/evidence pkgs/evidence
                  # tests/unit/80-seat-driver.bats resolves the seat driver at
                  # the repo-relative ../../tools/factory/seat (scripts run via
                  # bash, so no /usr/bin/env patch is needed) -- copy it in.
                  mkdir -p tools/factory
                  cp -r ${self}/tools/factory/seat tools/factory/seat
                  # tests/unit/80-seat-driver.bats asserts on the seat's plan file
                  # (no typed task heading), so copy it in or the test would skip
                  # in the sandbox (P8b MAJOR-1: a skip there lets a typed heading
                  # into the file with a green unit check).
                  cp -r ${self}/tools/factory/plan tools/factory/plan
                  # tests/unit/99-jaz-{blind,build,fixtures}.bats run the JAZ
                  # experiment's scripts at ../../tools/experiments/jaz -- copy
                  # them in or every case fails on a missing file.
                  mkdir -p tools/experiments
                  cp -r ${self}/tools/experiments/jaz tools/experiments/jaz
                  # tests/unit/89-agent-registry.bats runs the registry checker with
                  # no --registry override against the committed registry, so copy it
                  # in or the drift-check cases fail on a missing file (FA13b).
                  cp ${self}/tools/factory/agents.toml tools/factory/agents.toml
                  # route.py validates the committed table and cross-checks the
                  # bash lookup in the same test file; copy it and the table so
                  # those two tests run for real rather than skipping.
                  cp ${self}/tools/factory/route.py tools/factory/route.py
                  mkdir -p docs
                  cp -r ${self}/docs/ledger docs/ledger
                  # tests/unit/96-now-paragraph.bats runs tests/lint/now-paragraph.sh
                  # against the real board, so copy it in like the ledger above.
                  cp ${self}/docs/OPERATIONS.md docs/OPERATIONS.md
                  # tests/unit/90-session-start.bats reads the hook wiring file at
                  # ../../.claude/settings.json (the four events and their scripts),
                  # so copy it in or those cases fail on a missing file (P8b: a skip
                  # proves nothing).
                  mkdir -p .claude
                  cp ${self}/.claude/settings.json .claude/settings.json
                  # tests/unit/89-agent-registry.bats drift-checks the committed
                  # .claude/agents/<name>.md shims (no --shims override), so copy the
                  # directory in or those cases fail on a missing file (FA13b).
                  cp -r ${self}/.claude/agents .claude/agents
                  # tests/unit/96-plan-graph.bats (FA21) and 94-bug-graph.bats (FA19)
                  # walk the committed workflow graphs, so copy the directory in or
                  # those graph cases fail on a missing file (P8b: a skip proves nothing).
                  # tests/unit/94-bug-graph.bats opens the committed
                  # .claude/workflows/bug.toml directly (FA19b MAJOR-1), so copy the
                  # directory in or those cases fail on a missing file instead of
                  # running (a deletion red must reach the runner, not a stale twin).
                  cp -r ${self}/.claude/workflows .claude/workflows
                  # tests/unit/90-session-start.bats resolves the SessionStart hook
                  # at ../../tools/session-start.sh (run via bash, same as above).
                  cp ${self}/tools/session-start.sh tools/session-start.sh
                  # tests/unit/92-ritual.bats resolves the reset ritual at
                  # ../../tools/ritual.sh (also run via bash); session-start.sh
                  # shells out to it at $self_dir/ritual.sh, so it must sit beside it.
                  cp ${self}/tools/ritual.sh tools/ritual.sh
                  # tests/unit/91-orchestrator-guard.bats resolves the PreToolUse
                  # guard at ../../tools/orchestrator-guard.sh (run via bash, too).
                  cp ${self}/tools/orchestrator-guard.sh tools/orchestrator-guard.sh
                  # tests/unit/98-run-result-hook.bats resolves the UserPromptSubmit
                  # hook at ../../tools/run-result-hook.sh, and 90-session-start.bats's
                  # "every hook command names a script that exists in the tree" walks
                  # the settings' hook commands and stats each one — so the script
                  # missing from this sandbox failed seven cases at once while the
                  # tree itself was fine (c2ab844 added the hook and not this line).
                  cp ${self}/tools/run-result-hook.sh tools/run-result-hook.sh
                  # tests/unit/99-bug-note.bats resolves the debug tools at
                  # ../../tools/debug/<x>, so copy the directory in whole.
                  cp -r ${self}/tools/debug tools/debug
                  # tests/unit/99-fleet.bats resolves the fleet command at
                  # ../../pkgs/fleet/fleet.py and the shim at ../../tools/fleet
                  # (the template beside fleet.py, read at runtime by
                  # join-script), so both must sit at those repo-relative paths.
                  mkdir -p pkgs
                  cp -r ${self}/pkgs/fleet pkgs/fleet
                  cp ${self}/tools/fleet tools/fleet
                  # tests/unit/99-home-classes.bats resolves the checker at
                  # ../../pkgs/home-classes/home_classes.py and the shim at
                  # ../../tools/home-classes, so both must sit at those
                  # repo-relative paths (US0, the user-spaces plan).
                  cp -r ${self}/pkgs/home-classes pkgs/home-classes
                  cp ${self}/tools/home-classes tools/home-classes
                  # tests/unit/91-orchestrator-guard.bats reads the runbook's recipe
                  # section at ../../docs/runbooks/session.md (the sweep fixture is
                  # pinned to it), so copy it in like the resolves above.
                  mkdir -p docs/runbooks
                  cp ${self}/docs/runbooks/session.md docs/runbooks/session.md
                  # tests/unit/96-evidence-runbook.bats greps the runbook's ## Spend
                  # section and its Seven writers line, so it must be in the
                  # sandbox next to session.md or those tests fail on a missing
                  # file instead of running (P8b: a skip proves nothing).
                  cp ${self}/docs/runbooks/evidence.md docs/runbooks/evidence.md
                  # tests/unit/98-otel-ingest.bats drives the otel-ingest
                  # module's ingest payload against a fake collector dir and
                  # pins the unit's shape on the module's text, so the module
                  # must sit at the repo-relative path the test resolves from
                  # tests/unit (P8b: a missing file there is a red test, not a
                  # skip).
                  mkdir -p nixosModules
                  cp ${self}/nixosModules/otelIngest.nix nixosModules/otelIngest.nix
                  # tests/unit/96-evidence-runbook.bats gates the backfill line's
                  # --help through tools/ledger/factory.py, so the extractor must
                  # be copied in too (pkgs/evidence was copied above for the
                  # ingests' --help).
                  mkdir -p tools/ledger
                  cp ${self}/tools/ledger/factory.py tools/ledger/factory.py
                  # tests/unit/91-orchestrator-guard.bats also asserts the sweep
                  # fixture holds every command in the byte-frozen cr17/cr18 review
                  # tables, so those two review files must sit beside it too.
                  mkdir -p docs/reviews
                  cp ${self}/docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md
                  cp ${self}/docs/reviews/2026-09-06-opus-review-cr18-CR2r2.md docs/reviews/2026-09-06-opus-review-cr18-CR2r2.md
                  # tests/mocks/proton-drive-mock.sh keeps its literal
                  # #!/usr/bin/env bash shebang (it also runs as-is from the
                  # devShell and the VM test); the build sandbox has no
                  # /usr/bin/env, so patch it here the way stdenv would.
                  patchShebangs tests/mocks
                  bats tests/unit
                  touch $out
                '';
            proton-backup-eval =
              let
                resticUnitText =
                  protonBackupEvalSystem.config.systemd.units."restic-backups-core-local.service".text;
                pushUnitText = protonBackupEvalSystem.config.systemd.user.units."proton-drive-push.service".text;
                pushTimerText = protonBackupEvalSystem.config.systemd.user.units."proton-drive-push.timer".text;
              in
              pkgs.runCommand "proton-backup-eval-check"
                {
                  passAsFile = [
                    "resticUnitText"
                    "pushUnitText"
                    "pushTimerText"
                  ];
                  inherit resticUnitText pushUnitText pushTimerText;
                }
                ''
                  grep -q 'RESTIC_REPOSITORY=/var/lib/restic/core' "$resticUnitTextPath"
                  grep -q '^User=tester$' "$resticUnitTextPath"
                  grep -q -- '--read-data-subset=10%' "$resticUnitTextPath"
                  ! grep -qi 'RCLONE' "$resticUnitTextPath"
                  grep -q '^ConditionUser=tester$' "$pushUnitTextPath"
                  grep -q 'PROTON_BACKUP_REPO=/var/lib/restic/core' "$pushUnitTextPath"
                  grep -q '^OnCalendar=\*-\*-\* 00:30:00$' "$pushTimerTextPath"
                  touch $out
                '';
            helm-declaration =
              let
                # PL21 (docs/superpowers/plans/2026-09-11-platform.md): the
                # second argument is self with a synthetic stand-in for the
                # `core` attribute name — added only when the real one is
                # absent, so the full tree evaluates the exact same real
                # nixosConfigurations as before (the `?` guard makes the
                # merge a no-op there) while a host-less export, whose
                # nixosConfigurations is legitimately { }, still satisfies
                # O2's builtins.attrNames membership test for good-core's
                # offers.profiles = [ "core" ]. Only the attribute NAME is
                # synthetic; nothing about core's real configuration is
                # read or asserted here.
                goodErrs = self.lib.helmDeclarationErrors (import ./tests/helm-home/declarations/good-core.nix) (
                  self
                  // {
                    nixosConfigurations =
                      self.nixosConfigurations // (if self.nixosConfigurations ? core then { } else { core = { }; });
                  }
                );
                missingOffersErrs = self.lib.helmDeclarationErrors {
                  name = "inline-offers-missing";
                  summary = "s";
                  why = "w";
                  created = "2026-09-02";
                  owner = "o";
                  writtenAgainst = null;
                  state = "s";
                  updated = "2026-09-09";
                  card = {
                    blocks = [ "why" ];
                    notes = "n";
                  };
                } self;
              in
              assert nixpkgs.lib.assertMsg (
                goodErrs == [ ]
              ) "helm-declaration: good-core must yield no errors, got ${builtins.toJSON goodErrs}";
              assert nixpkgs.lib.assertMsg (missingOffersErrs == [ "missing field offers" ])
                "helm-declaration: a declaration missing offers must yield exactly [ \"missing field offers\" ], got ${builtins.toJSON missingOffersErrs}";
              self.lib.checkHelmDeclaration self.helm self;
            helm-declaration-negative-profile =
              let
                decl = import ./tests/helm-home/declarations/bad-profile.nix;
                errs = self.lib.helmDeclarationErrors decl self;
                attempt = builtins.tryEval (self.lib.checkHelmDeclaration decl self).drvPath;
              in
              if
                errs != [
                  "offers.profiles names nope, which the flake does not export (nixosModules or nixosConfigurations)"
                ]
              then
                throw "helm-declaration-negative-profile: expected exactly the O2 nope string, got ${builtins.toJSON errs}"
              else if attempt.success then
                throw "helm-declaration-negative-profile: checkHelmDeclaration DID NOT throw"
              else
                pkgs.runCommand "helm-declaration-negative-profile-ok" { } "touch $out";
            helm-declaration-negative-program =
              let
                decl = import ./tests/helm-home/declarations/bad-program.nix;
                errs = self.lib.helmDeclarationErrors decl self;
                attempt = builtins.tryEval (self.lib.checkHelmDeclaration decl self).drvPath;
              in
              if
                errs
                != [ "offers.run \"Nothing\" runs no-such-program, which is not a package or app of the flake" ]
              then
                throw "helm-declaration-negative-program: expected exactly the O3 no-such-program string, got ${builtins.toJSON errs}"
              else if attempt.success then
                throw "helm-declaration-negative-program: checkHelmDeclaration DID NOT throw"
              else
                pkgs.runCommand "helm-declaration-negative-program-ok" { } "touch $out";
            helm-declaration-negative-seat =
              let
                decl = import ./tests/helm-home/declarations/bad-seat.nix;
                errs = self.lib.helmDeclarationErrors decl self;
                attempt = builtins.tryEval (self.lib.checkHelmDeclaration decl self).drvPath;
              in
              if errs != [ "offers.seats holds gpt, not one of claude, deepseek" ] then
                throw "helm-declaration-negative-seat: expected exactly the O4 gpt string, got ${builtins.toJSON errs}"
              else if attempt.success then
                throw "helm-declaration-negative-seat: checkHelmDeclaration DID NOT throw"
              else
                pkgs.runCommand "helm-declaration-negative-seat-ok" { } "touch $out";
            helm-declaration-negative-block =
              let
                decl = import ./tests/helm-home/declarations/bad-block.nix;
                errs = self.lib.helmDeclarationErrors decl self;
                attempt = builtins.tryEval (self.lib.checkHelmDeclaration decl self).drvPath;
              in
              if
                errs != [ "card.blocks holds banner, not one of why, state, do, notes, cost, lastRun, terminal" ]
              then
                throw "helm-declaration-negative-block: expected exactly the C2 banner string, got ${builtins.toJSON errs}"
              else if attempt.success then
                throw "helm-declaration-negative-block: checkHelmDeclaration DID NOT throw"
              else
                pkgs.runCommand "helm-declaration-negative-block-ok" { } "touch $out";
            helm-declaration-negative-field =
              let
                decl = import ./tests/helm-home/declarations/bad-field.nix;
                errs = self.lib.helmDeclarationErrors decl self;
                attempt = builtins.tryEval (self.lib.checkHelmDeclaration decl self).drvPath;
              in
              if errs != [ "unknown field colour" ] then
                throw "helm-declaration-negative-field: expected exactly [ \"unknown field colour\" ], got ${builtins.toJSON errs}"
              else if attempt.success then
                throw "helm-declaration-negative-field: checkHelmDeclaration DID NOT throw"
              else
                pkgs.runCommand "helm-declaration-negative-field-ok" { } "touch $out";

            patch-series-apply = pkgs.runCommand "patch-series-apply" { } ''
              test -e ${coreSpecialArgs.claude-code-pkg}
              touch $out
            '';
            patch-series-eval =
              (import ./tests/integration/patch-series.nix {
                inherit pkgs;
                patchSeries = self.lib.patchSeries;
              }).eval;
            patch-series-negative =
              (import ./tests/integration/patch-series.nix {
                inherit pkgs;
                patchSeries = self.lib.patchSeries;
              }).negative;
            # PL5 (2026-09-11-platform.md): dsh-harness builds from this flake on
            # nixpkgs-host. Arm (i) asserts the package carries the payload and not
            # archive/ (Interface 1); arms (ii)/(iii) run the SAME builder body on a
            # source with one `name:`/`description:` line removed and assert it is
            # refused with its own message (Interface 2a/2b, erratum 10).
            dsh-harness-eval =
              let
                srcNoName = pkgsHost.runCommand "dsh-harness-src-no-name" { } ''
                  cp -r ${./pkgs/dsh-harness} $out
                  chmod -R u+w "$out"
                  f="$(find "$out"/skills -name SKILL.md | head -n1)"
                  sed -i '/^name: /d' "$f"
                '';
                srcNoDesc = pkgsHost.runCommand "dsh-harness-src-no-desc" { } ''
                  cp -r ${./pkgs/dsh-harness} $out
                  chmod -R u+w "$out"
                  f="$(find "$out"/skills -name SKILL.md | head -n1)"
                  sed -i '/^description: /d' "$f"
                '';
              in
              pkgsHost.runCommand "dsh-harness-eval"
                {
                  nativeBuildInputs = [
                    pkgsHost.gnugrep
                    pkgsHost.findutils
                    pkgsHost.gnused
                  ];
                }
                ''
                  ${dshHarnessBuilder}
                  mkdir -p "$out"
                  # Arm (i): the package built, and carries the payload (Interface 1).
                  for f in AGENTS.md README.md CHANGELOG.md skills; do
                    if [ ! -e "${dshHarnessSrc}/$f" ]; then
                      echo "dsh-harness-eval: $f missing from dsh-harness-src" >&2
                      exit 1
                    fi
                  done
                  if [ -e "${dshHarnessSrc}/archive" ]; then
                    echo "dsh-harness-eval: archive/ is present in dsh-harness-src" >&2
                    exit 1
                  fi
                  # Arm (ii): a source with one `name:` line removed is refused.
                  if ( dshHarnessBuilder "${srcNoName}" "$out/noname" ) 2>"$out/noname.log"; then
                    echo "dsh-harness-eval: a SKILL.md without name: was accepted" >&2
                    exit 1
                  else
                    if ! grep -q 'missing name:' "$out/noname.log"; then
                      echo "dsh-harness-eval: name mutation refused with the wrong message" >&2
                      exit 1
                    fi
                    echo "refused as required: $(cat "$out/noname.log")"
                  fi
                  # Arm (iii): a source with one `description:` line removed is refused.
                  if ( dshHarnessBuilder "${srcNoDesc}" "$out/nodesc" ) 2>"$out/nodesc.log"; then
                    echo "dsh-harness-eval: a SKILL.md without description: was accepted" >&2
                    exit 1
                  else
                    if ! grep -q 'missing description:' "$out/nodesc.log"; then
                      echo "dsh-harness-eval: description mutation refused with the wrong message" >&2
                      exit 1
                    fi
                    echo "refused as required: $(cat "$out/nodesc.log")"
                  fi
                  touch "$out"
                '';
            # PL14b: the collision guard's host×media arm, dropped by PL14's
            # rewrite, restored as one pairwise function; this permanent
            # regression check proves each pair still catches a synthetic
            # collision, on two-key fixtures called in isolation (plain
            # assertMsg -- pairwiseCollisions returns a list, never throws,
            # so no tryEval is needed, mirroring the *-assertion-negative
            # idiom).
            core-collision-guard-negative =
              let
                hostFixtureA = {
                  "probe-collision-a" = null;
                  "host-only-a" = null;
                };
                mediaFixtureA = {
                  "probe-collision-a" = null;
                  "media-only-a" = null;
                };
                hostFixtureB = {
                  "probe-collision-b" = null;
                  "host-only-b" = null;
                };
                gamingFixtureB = {
                  "probe-collision-b" = null;
                  "gaming-only-b" = null;
                };
                mediaFixtureC = {
                  "probe-collision-c" = null;
                  "media-only-c" = null;
                };
                gamingFixtureC = {
                  "probe-collision-c" = null;
                  "gaming-only-c" = null;
                };
                caseHostMedia = pairwiseCollisions hostFixtureA mediaFixtureA { };
                caseHostGaming = pairwiseCollisions hostFixtureB { } gamingFixtureB;
                caseMediaGaming = pairwiseCollisions { } mediaFixtureC gamingFixtureC;
                caseDisjoint =
                  pairwiseCollisions
                    {
                      "host-only-a" = null;
                    }
                    {
                      "media-only-a" = null;
                    }
                    {
                      "gaming-only-b" = null;
                    };
              in
              assert nixpkgs.lib.assertMsg (caseHostMedia == [ "probe-collision-a" ])
                "core-collision-guard-negative: a host×media check-name collision DID NOT get caught (the arm PL14b restored)";
              assert nixpkgs.lib.assertMsg (
                caseHostGaming == [ "probe-collision-b" ]
              ) "core-collision-guard-negative: a host×gaming check-name collision DID NOT get caught";
              assert nixpkgs.lib.assertMsg (
                caseMediaGaming == [ "probe-collision-c" ]
              ) "core-collision-guard-negative: a media×gaming check-name collision DID NOT get caught";
              assert nixpkgs.lib.assertMsg (
                caseDisjoint == [ ]
              ) "core-collision-guard-negative: disjoint check names reported as colliding (a false positive)";
              pkgs.runCommand "core-collision-guard-negative-check" { } "touch $out";
          }
          # PL19 (plan 2026-09-11-platform.md): the export-eval check that
          # closes claim aios-public-flake-eval-unmeasured — "a clean
          # clone of the publish-gate export evaluates this flake" becomes
          # a standing, re-run fact, the sibling aios-public-build already
          # is for the workspace build. The plan's design ran `nix flake
          # show` and `nix flake check --no-build` inside the check's own
          # sandbox; measured on this host (2026-09-26) that half cannot
          # run there: a sandboxed build mounts neither the nix daemon
          # socket nor the store database, and __noChroot is refused for
          # an untrusted user. So the check splits along that line — the
          # sandboxed half (exportTree, tests/acceptance/export-eval.sh:
          # git and python only) assembles the export and git-commits it,
          # and this half evaluates it here, in the ambient evaluator,
          # the same assert-forcing shape as fleet-eval and
          # helm-declaration. forcedOutputs is `nix flake show`'s walk of
          # every top-level output at the rehearsal's measured depths
          # (attrNames for attrsets, WHNF for module functions and plain
          # outputs, drvPath for derivations); the checks walk is
          # `nix flake check --no-build`'s, forcing every check's
          # drvPath under tryEval and holding the failing set to exactly
          # [ ] — PL21 removed the one accepted exception (good-core
          # now validates against a synthetic stand-in for core when
          # the export carries none, so the set must be empty). The
          # export's own export-eval is excluded from that walk:
          # asserting on it would recurse into its own assembled export;
          # nobody else forces it.
          #
          # Measured 2026-09-26 on a clean clone of the real export: the
          # exportTree derivation is realised at EVAL time (converting the
          # derivation to a path via string interpolation for `import`,
          # below, is IFD), and export-eval.sh's build runs
          # publish.py export-list against docs/ledger/publish.toml — a
          # withheld file (spec docs/superpowers/specs/2026-09-21-publish-
          # gate-design.md §6; docs/ledger/publish.toml withholds itself).
          # A public export therefore cannot evaluate this check at all,
          # so it is defined only when the manifest is present, the same
          # builtins.pathExists gate hostsPrivatePath uses for
          # hosts/private.nix's twelve checks (PL17) — this one keyed on
          # the manifest itself rather than hosts/private.nix, since it
          # reads no hosts/* path.
          // nixpkgs.lib.optionalAttrs (builtins.pathExists ./docs/ledger/publish.toml) {
            export-eval =
              let
                exportTree = pkgs.runCommand "export-eval-tree" {
                  nativeBuildInputs = [
                    pkgs.git
                    pkgs.python3
                  ];
                } "bash ${./tests/acceptance/export-eval.sh} ${self}";
                # builtins.getFlake refuses a ref whose string carries a
                # derivation context ("the string 'path:…' is not allowed
                # to refer to a store path", measured 2026-09-26), so the
                # export's outputs function is imported and called
                # directly: the export's flake.lock is the byte-identical
                # copy the script made, so this flake's own locked inputs
                # are its inputs, and self binds recursively the way
                # nix's flake machinery binds it. The call site sits in
                # the same file as the outputs header it must mirror, so
                # the two cannot drift apart unreviewed.
                exportFlake = (import (exportTree + "/flake.nix")).outputs {
                  self = exportFlake // {
                    outPath = toString exportTree;
                  };
                  inherit
                    nixpkgs
                    nixpkgs-host
                    llm-agents
                    claude-desktop
                    tvix-aios
                    home-manager
                    ;
                };
                exportChecks = builtins.removeAttrs exportFlake.checks.${system} [ "export-eval" ];
                # The walk is `nix flake check --no-build`'s per-check forcing.
                # Nix 2.34's tryEval catches throw-based failures (every
                # assert-shaped check, helm-declaration included) but NOT
                # missing-attribute errors (measured 2026-09-26: tryEval
                # ({}.core) escapes); addErrorContext rides the raw error so
                # even the uncatchable class names the check that failed.
                checkFails =
                  name:
                  builtins.addErrorContext "export-eval: check ${name} fails to evaluate on the export" (
                    !(builtins.tryEval (builtins.seq exportChecks.${name}.drvPath null)).success
                  );
                failing = nixpkgs.lib.naturalSort (builtins.filter checkFails (builtins.attrNames exportChecks));
                forcedOutputs = [
                  (builtins.attrNames exportFlake.lib)
                  (nixpkgs.lib.mapAttrsToList (_: v: builtins.seq v null) exportFlake.nixosModules)
                  (nixpkgs.lib.mapAttrsToList (_: v: builtins.seq v.drvPath null) exportFlake.packages.${system})
                  (nixpkgs.lib.mapAttrsToList (_: v: builtins.seq v.drvPath null) exportFlake.devShells.${system})
                  (builtins.seq exportFlake.formatter.${system}.drvPath null)
                  (builtins.seq exportFlake.helm null)
                  (builtins.seq exportFlake.phase3NegativeDemo null)
                  (builtins.attrNames exportFlake.nixosConfigurations)
                ];
              in
              assert builtins.deepSeq forcedOutputs true;
              assert nixpkgs.lib.assertMsg (
                builtins.attrNames exportFlake.nixosConfigurations == [ ]
              ) "export-eval: the export carries nixosConfigurations — hosts/* must never publish";
              assert nixpkgs.lib.assertMsg (failing == [ ])
                "export-eval: the export's failing-check set must be exactly [ ] (helm-declaration passed ever since PL21 gave good-core a synthetic stand-in for the missing core); got ${builtins.toJSON failing}";
              pkgs.runCommand "export-eval" { } ''
                echo "export-eval: the publish-gate export evaluates clean; failing checks: ${builtins.concatStringsSep ", " failing}"
                touch $out
              '';
          };
          mediaChecks = import ./media/checks.nix {
            pkgs = pkgsHost;
            inherit (pkgsHost) lib;
            nixpkgs = nixpkgs-host;
            inherit self system;
          };
          gamingChecks = import ./gaming/checks.nix {
            pkgs = pkgsHost;
            inherit (pkgsHost) lib;
            nixpkgs = nixpkgs-host;
            inherit self system;
          };
          # PL17: the operator's own twelve checks, from the same withheld
          # file privateOut reads. The binding follows the media/gaming
          # shape on purpose: repomap's _flake_check_sources lists
          # `<name>Checks = import ./x` files as check sources, so
          # docs/MAP.md's Checks section keeps naming all twelve. The
          # import is unguarded HERE but a thunk — it is forced only in the
          # pathExists branch of the merge below, so a tree without
          # hosts/private.nix never evaluates it.
          privateChecks = import ./hosts/private.nix {
            inherit
              self
              nixpkgs
              pkgs
              system
              mkCore
              mkForge
              coreModules
              coreModulesBase
              forgeModules
              dshOpenrouter
              fleetFixture
              seatHelmPortSystem
              seatPortRangeExactSystem
              seatWaveJobsOneSystem
              ;
          };
          # PL14b: one function, all three pairs -- host×media, host×gaming,
          # media×gaming. PL14's rewrite had dropped the host×media term the
          # fork point carried (intersectLists hostChecks mediaChecks), so a
          # host/media name collision would silently shadow in `//` with no
          # throw; core-collision-guard-negative (inside hostChecks) is the
          # permanent regression check proving each pair is still caught.
          pairwiseCollisions =
            a: b: c:
            nixpkgs.lib.unique (
              nixpkgs.lib.intersectLists (builtins.attrNames a) (builtins.attrNames b)
              ++ nixpkgs.lib.intersectLists (builtins.attrNames a) (builtins.attrNames c)
              ++ nixpkgs.lib.intersectLists (builtins.attrNames b) (builtins.attrNames c)
            );
          collisions = pairwiseCollisions hostChecks mediaChecks gamingChecks;
        in
        if collisions != [ ] then
          throw "core-media-wiring: media/gaming check name(s) ${builtins.concatStringsSep ", " collisions} collide with a host check of the same name — rename in media/checks.nix or gaming/checks.nix"
        else if builtins.pathExists hostsPrivatePath then
          hostChecks
          // mediaChecks
          // gamingChecks
          // builtins.removeAttrs privateChecks [ "nixosConfigurations" ]
        else
          hostChecks // mediaChecks // gamingChecks;

      formatter.${system} = pkgs.treefmt;
    };
}
