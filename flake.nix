{
  description = "NixOS agent environments with encrypted data baskets";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/34ab99075ac4f7e40cf037eef32cb1c360bb85e9";
    nixpkgs-host.url = "github:NixOS/nixpkgs/a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4";
    # NOTE (deviation from plan Step 1): llm-agents.inputs.nixpkgs.follows =
    # "nixpkgs-host" is NOT set. llm-agents' package set is built as one
    # mutually-recursive callPackages call, so evaluating even a single
    # package (claude-code) forces evaluation of its siblings (e.g.
    # agent-browser), which needs `pnpmConfigHook` -- not present in the
    # nixpkgs-host pin (ac62194c3917, 2026-01-02; pnpmConfigHook landed in
    # nixpkgs later). Following broke `nix build` with:
    #   error: lib.customisation.callPackageWith: Function called without
    #   required argument "pnpmConfigHook" at packages/agent-browser/package.nix:9
    # claude-code is pulled from llm-agents' own pinned nixpkgs instead --
    # a foreign-pkgs systemPackages entry is a normal, supported pattern,
    # and llm-agents' own nixpkgs already carries the unfree allowance
    # claude-code needs.
    llm-agents.url = "github:numtide/llm-agents.nix/4ab625e16a6cc52fe3f606b95f1e2ac20dafa80b";
    claude-desktop.url = "github:nmcbride/claude-desktop-nix/2479d51149838ddf049fdcd8cefe360ce904ed00";
    # ~/flakes/gaming is a READ-ONLY sibling repo (host-wiring plan Task 1):
    # pinned by ref so `nix flake lock` records the exact rev, no `follows`
    # (the gaming flake's own nixpkgs is already the same rev as
    # nixpkgs-host -- see checks.core-gaming-wiring's lock-node assertion).
    gaming.url = "git+file:///home/dalhaka/flakes/gaming?ref=main";
  };

  outputs =
    {
      self,
      nixpkgs,
      nixpkgs-host,
      llm-agents,
      claude-desktop,
      gaming,
    }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
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
      # darkFactorySyntaxCheckSrc: the lint check's `node --check` syntax
      # gate on tools/factory/dark-factory.js (F35), assembled the same way
      # every other script-from-source derivation in this file is (compare
      # `basket`/`protonBackupPush` above): builtins.readFile on a Nix path.
      # That's deliberate, not just consistency. The old sed pipeline (still
      # used by githooks/pre-commit, which has no `self`/Nix-path access)
      # does fail on a missing source -- errexit aborts the brace group
      # before the trailing `echo '}'` runs, so node --check dies -- but
      # only by accident, and with a misleading "SyntaxError: Unexpected end
      # of input" that gives no hint the real problem is a missing file.
      # Reading the source through a Nix path moves the failure to
      # *evaluation*, with an unambiguous "error: opening file '...': No
      # such file or directory".
      darkFactorySyntaxCheckSrc = pkgs.writeText "dark-factory-syntax-check.js" (
        "async function __dark_factory_syntax_check() {\n"
        + builtins.replaceStrings [ "export const meta" ] [ "const meta" ] (
          builtins.readFile ./tools/factory/dark-factory.js
        )
        + "\n}\n"
      );
      lintTools = with pkgs; [
        treefmt
        nixfmt-rfc-style
        shfmt
        shellcheck
        statix
        deadnix
        ruff
        # nodejs: `node --check` syntax-checks tools/factory/dark-factory.js
        # (F35) -- the factory script is never executed by this repo's own
        # test suite, so this is the only gate on a syntax error in it.
        nodejs
        # P12: prettier (format) and oxlint (lint) gate every tracked
        # JavaScript file through treefmt and the lint check (tests/lint/
        # js-lint.sh, run after tests/lint/bats-and-chain.sh below).
        prettier
        oxlint
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
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            # services.helm.operatorUser defaults to "dalhaka" and the
            # module adds that user to the "helm" group -- NixOS requires
            # every users.users entry to resolve isNormalUser xor
            # isSystemUser, so this isolated eval stub (unlike hosts/core,
            # which already declares dalhaka fully) must declare it too,
            # the same way protonBackupEvalSystem declares "tester" above.
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            services.helm = {
              enable = true;
              basketPackage = basket;
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
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            services.evidence-store.enable = true;
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
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            services.helm = {
              enable = true;
              basketPackage = basket;
              listen = "0.0.0.0:7700";
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
              users.users.dalhaka = {
                isNormalUser = true;
                uid = 1000;
              };
              security.polkit.enable = true;
              environment.etc."helm/profile".text = "base";
              specialisation.alt.configuration.environment.etc."helm/profile".text = lib.mkForce "alt";
              services.helm = {
                enable = true;
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
              users.users.dalhaka = {
                isNormalUser = true;
                uid = 1000;
              };
              environment.etc."helm/profile".text = "base";
              specialisation.alt.configuration.environment.etc."helm/profile".text = lib.mkForce "alt";
              services.helm = {
                enable = true;
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
            users.users.dalhaka = {
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
              users.users.dalhaka = {
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
              users.users.dalhaka = {
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
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            environment.etc."helm/profile".text = "base";
            services.helm = {
              enable = true;
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
            users.users.dalhaka = {
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
            };
          })
        ];
      };
      # tests/lane/polkit.test.mjs (T2): the REAL rendered polkit grant, not
      # a hand-copied re-implementation. Sourced from host `core`'s own
      # config (not laneEvalSystem's "testlane" harness above) because it's
      # the "openrouter" lane's actual unit-name prefix and operatorUser
      # that ships -- the same instance checks.host-core already reads.
      lanePolkitRules = pkgs.writeText "lane-polkit-rules.js" self.nixosConfigurations.core.config.security.polkit.extraConfig;
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
            users.users.dalhaka = {
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
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/nix/store/00000000000000000000000000000000-openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "dalhaka";
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
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              keyFile = "/var/lib/secrets/openrouter-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3141;
              operatorUser = "dalhaka";
            };
            systemd.services."seat@".environment.OPENROUTER_API_KEY =
              nixpkgs.lib.mkForce "sk-or-v1-real-looking-key-1234567890abcdef";
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
        # T3 (Lane L round 1 plan) replaces this stub with the real
        # OpenRouter client; nixosModules/modelLane.nix references the same
        # file so lane-<name>@.service's ExecStart path never has to change.
        lane-run = pkgs.callPackage ./pkgs/lane/lane-run.nix { };
        dsh = dshHost;
        dsh-openrouter = dshOpenrouter;
        # SB3 + SB1 (2026-09-05-seat-behind-broker): the seat's operator CLI
        # (seat-submit) and the seat@<job> unit entry (seat-run). seatLane.nix
        # builds seat-run via its own callPackage, so these packages stay a
        # stable path for the eval check.
        inherit (seatTools) seat-submit seat-run;
        evidence = pkgs.writeShellApplication {
          name = "evidence";
          runtimeInputs = [
            pkgs.python3
            pkgs.git
          ];
          text = ''exec python3 ${./pkgs/evidence}/evidence.py "$@"'';
        };
      };

      nixosModules = {
        egressBroker = import ./nixosModules/egressBroker.nix;
        basketStore = import ./nixosModules/basketStore.nix;
        claudeManagedSettings = import ./nixosModules/claudeManagedSettings.nix;
        cowork = import ./nixosModules/cowork.nix;
        protonBackup = import ./nixosModules/protonBackup.nix;
        helm = import ./nixosModules/helm.nix;
        modelLane = import ./nixosModules/modelLane.nix;
        seatLane = import ./nixosModules/seatLane.nix;
        evidenceStore = import ./nixosModules/evidenceStore.nix;
      };

      lib.mkAgent = import ./lib/mkAgent.nix;

      nixosConfigurations.core = nixpkgs-host.lib.nixosSystem {
        system = "x86_64-linux";
        specialArgs = {
          claude-code-pkg = llm-agents.packages.x86_64-linux.claude-code;
          proton-drive-cli-pkg = self.packages.x86_64-linux.proton-drive-cli;
          basket-pkg = self.packages.x86_64-linux.basket;
          # The operator's DeepSeek seat (pkgs/dsh-openrouter), a plain command on
          # the host since the 2026-09-03 evening switch ("no nix run").
          dsh-openrouter-pkg = self.packages.x86_64-linux.dsh-openrouter;
          inherit claude-desktop;
        };
        modules = [
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
          gaming.nixosModules.default
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
      };

      phase3NegativeDemo = phase3BadSystem;

      devShells.${system}.default = pkgs.mkShell {
        packages =
          basketRuntimeInputs
          ++ lintTools
          ++ [
            basket
            protonBackupPush
            pkgs.bats
            pkgs.yubikey-manager
            brokerPython
            ledgerPython
            pkgs.zstd
            dshOpenrouter
          ];
        shellHook = ''
          git config core.hooksPath githooks
        '';
      };

      checks.${system} = {
        host-core =
          let
            c = self.nixosConfigurations.core.config;
            i = c.services.egress-broker.instances.openrouter;
            p = c.services.egress-broker.policy.openrouter;
            # Helm v1 control wiring (switch plan Task 5 / consolidated D1):
            # the host enables the loopback switch with the FIXED profile
            # allowlist; workspaces now pin the empty map (H4, operator
            # decision 2026-09-04 -- the workspace buttons left the live page
            # until Helm Home ships).
            hc = c.services.helm.control;
            gamingSpec = c.specialisation.gaming.configuration;
            polkit = c.security.polkit.extraConfig;
            # Contract item 2's proof: the lane's child directories derived from
            # the very tmpfiles rules modelLane renders for a lane, so a fourth
            # child added to modelLane's tmpfiles is caught the moment it lands.
            # Each lane rule `d /var/lib/lanes/<name>(/<child>)? …` either
            # declares the lane root (no child — the ledger's parent, exempt) or
            # a child directory; every child must be matched by an exclude
            # pattern /var/lib/lanes/*/<child>.
            laneChildrenUnexcluded =
              let
                childOf =
                  r:
                  let
                    m = builtins.match "d /var/lib/lanes/([^/ ]+)(/([^ ]+))? ?.*" r;
                  in
                  if m == null then null else builtins.elemAt m 2;
                children = builtins.filter (c: c != null) (map childOf c.systemd.tmpfiles.rules);
              in
              builtins.filter (
                child: !(nixpkgs.lib.elem "/var/lib/lanes/*/${child}" c.services.proton-backup.exclude)
              ) children;
          in
          assert nixpkgs.lib.assertMsg (
            i.allow == [ "openrouter.ai" ]
          ) "host-core: egress-broker instance 'openrouter' allow list must be exactly [ \"openrouter.ai\" ]";
          assert nixpkgs.lib.assertMsg (
            i.inject."openrouter.ai".valueFile == "/var/lib/secrets/openrouter-key"
          ) "host-core: egress-broker instance 'openrouter' must inject from /var/lib/secrets/openrouter-key";
          # The Nix->policy wire format under test (W2-N3, N13), asserted on
          # the internal read-only option egressBroker.nix exposes rather than
          # by reading the generated JSON derivation (no IFD): bodyPatch's
          # pathPrefixes -> body_patch.<host>.path_prefixes (the ZDR patch is
          # scoped to /api/v1/chat/completions only), denyPaths' pathPrefixes
          # -> deny_paths.<host>.path_prefixes (/api/v1/messages is DENIED,
          # fail closed -- O3 resolved: nothing consumes that path, so it is
          # not patched), and inject's default paths -> [ "/" ] (the
          # credential is NOT scoped to the patched path, it must keep
          # flowing to the lane's other calls).
          assert nixpkgs.lib.assertMsg
            (
              p.body_patch."openrouter.ai".path_prefixes == [ "/api/v1/chat/completions" ]
              && p.deny_paths."openrouter.ai".path_prefixes == [ "/api/v1/messages" ]
              && p.inject."openrouter.ai".paths == [ "/" ]
            )
            "host-core: broker policy wire format must be body_patch.openrouter.ai.path_prefixes == [ \"/api/v1/chat/completions\" ], deny_paths.openrouter.ai.path_prefixes == [ \"/api/v1/messages\" ] and inject.openrouter.ai.paths == [ \"/\" ]";
          assert nixpkgs.lib.assertMsg (builtins.any (p: (p.pname or p.name or "") == "dsh-openrouter")
            c.environment.systemPackages
          ) "host-core: dsh-openrouter must be a system package (the operator's DeepSeek seat, 2026-09-03)";
          # N15: hook-guard.py and dsh-denials.py must run on the minimal
          # interpreter, or the seat's Python hooks drag full python3 (139 MiB)
          # into the host toplevel alongside the harness. `dshOpenrouter`
          # (pkgs/dsh-openrouter) is the same package hosts/core installs via
          # the dsh-openrouter-pkg specialArg above.
          assert nixpkgs.lib.assertMsg (dshOpenrouter.passthru.guardPython == pkgs.python3Minimal)
            "host-core: dsh-openrouter.passthru.guardPython must be pkgs.python3Minimal -- hook-guard and dsh-denials are stdlib-only scripts and must not pull full python3 into the system closure";
          assert nixpkgs.lib.assertMsg (
            hc.enable == true
          ) "host-core: services.helm.control must be enabled (the loopback switch + workspace surface)";
          assert nixpkgs.lib.assertMsg
            (
              hc.profiles == [
                "base"
                "gaming"
              ]
            )
            "host-core: helm control.profiles must be exactly [ \"base\" \"gaming\" ] -- the fixed literal (D1), never derived from config.specialisation; media joins only when round 2 wires specialisation.media";
          assert nixpkgs.lib.assertMsg (hc.workspaces == { })
            "host-core: helm control.workspaces must pin the empty map -- the workspace buttons leave the live page until Helm Home ships (operator decision 2026-09-04)";
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.hasInfix "helm-switch@base.service" polkit
            && nixpkgs.lib.hasInfix "helm-switch@gaming.service" polkit
          ) "host-core: the polkit rule must enumerate the base and gaming switch instances";
          assert nixpkgs.lib.assertMsg
            (
              gamingSpec.services.helm.control.profiles == hc.profiles
              &&
                gamingSpec.systemd.services."helm-switch@".serviceConfig.ExecStart
                == c.systemd.services."helm-switch@".serviceConfig.ExecStart
              && gamingSpec.security.polkit.extraConfig == polkit
            )
            "host-core: the gaming specialisation must inherit the identical profiles allowlist, helm-switch@ ExecStart and polkit rule (D1: byte-identical in every toplevel)";
          assert nixpkgs.lib.assertMsg
            (
              nixpkgs.lib.any (r: r == "d /home/dalhaka/factory 0700 dalhaka users -") c.systemd.tmpfiles.rules
              && nixpkgs.lib.any (
                r: r == "d /home/dalhaka/factory/base 0700 dalhaka users -"
              ) c.systemd.tmpfiles.rules
              && nixpkgs.lib.any (
                r: r == "d /home/dalhaka/factory/ws 0700 dalhaka users -"
              ) c.systemd.tmpfiles.rules
            )
            "host-core: the factory root /home/dalhaka/factory (and base/, ws/) must be tmpfiles-declared 0700 dalhaka:users (O11: a declared root outside every repo, docs/decisions/2026-09-04-parallel-agent-workflows.md)";
          assert nixpkgs.lib.assertMsg c.services.evidence-store.enable
            "host-core: services.evidence-store must be enabled on core";
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "/var/lib/evidence" c.services.proton-backup.paths)
            "host-core: /var/lib/evidence must be a restic path (the store is the record)";
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "/var/lib/lanes" c.services.proton-backup.paths)
            "host-core: /var/lib/lanes must be a restic path (each lane's ledger is the audit record)";
          # The 2026-09-05 addendum (decision 2026-09-05-audit-logs-backed-up.md)
          # reversed the broker half: the broker audit logs never leave the
          # machine, so /var/lib/egress-broker must NOT be a restic path.
          assert nixpkgs.lib.assertMsg
            (
              !(nixpkgs.lib.any (
                p: nixpkgs.lib.hasPrefix "/var/lib/egress-broker" p
              ) c.services.proton-backup.paths)
            )
            "host-core: no restic path may start with /var/lib/egress-broker (the broker audit logs never leave the machine by decision 2026-09-05 addendum)";
          assert nixpkgs.lib.assertMsg
            (
              c.services.proton-backup.exclude == [
                "**/.pytest_cache"
                "**/.ruff_cache"
                "/home/*/.cache"
                "/var/lib/lanes/*/jobs"
                "/var/lib/lanes/*/results"
              ]
            )
            "host-core: services.proton-backup.exclude must be exactly the three module defaults plus /var/lib/lanes/*/jobs and /var/lib/lanes/*/results (the five patterns; job payloads and model output stay out of the backup)";
          # The known lane layout is /var/lib/lanes/<lane>/{ledger.jsonl, jobs/,
          # results/}: the lane root <lane> holds ledger.jsonl (the ledger's
          # parent, exempt) and every deeper directory is a lane child. Derive
          # the children from the very tmpfiles rules modelLane renders for a
          # lane (every `d /var/lib/lanes/<name>/<child> …` line) and require
          # each one to be matched by an exclude pattern /var/lib/lanes/*/<child>,
          # so under /var/lib/lanes/* nothing beside each lane's ledger.jsonl
          # survives the excludes (contract item 2). A new lane child directory
          # added to modelLane's tmpfiles without a matching exclude would
          # silently join the backup — name it here and fail the build.
          assert nixpkgs.lib.assertMsg (laneChildrenUnexcluded == [ ])
            "host-core: every lane child directory declared in modelLane's tmpfiles must be covered by a /var/lib/lanes/*/<child> exclude pattern (so under /var/lib/lanes/* only each lane's ledger.jsonl survives the backup); unexcluded lane children: ${toString laneChildrenUnexcluded}";
          c.system.build.toplevel;
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
              shellcheck pkgs/basket/basket.sh pkgs/proton-backup/push.sh pkgs/dsh-openrouter/dsh-openrouter.sh pkgs/helm/helm-switch.sh pkgs/helm/helm-open-workspace.sh tests/mocks/proton-drive-mock.sh githooks/pre-push githooks/pre-commit
              # The seat driver's entry scripts are extensionless (factory-brief,
              # -ws, -task, -wave, -integrate, -review), so the `find tools
              # -name '*.sh'` sweep below misses them; their .sh sibling is swept.
              shellcheck tools/factory/seat/factory-brief tools/factory/seat/factory-ws tools/factory/seat/factory-task tools/factory/seat/factory-wave tools/factory/seat/factory-integrate tools/factory/seat/factory-review
              find tests -name '*.sh' -print0 | xargs -0 --no-run-if-empty shellcheck
              # T3 (Lane L round 1 plan): the first tools/*.sh scripts this
              # repo actually gates on shellcheck (tools/lane/jobs/*.sh) --
              # widened to the whole directory, not just that subdir, so the
              # pre-existing cowork-up.sh/cowork-down.sh/enroll-yubikey.sh/
              # reset-yubikey-piv.sh (already clean; verified before this
              # change) are gated too from here on.
              find tools -name '*.sh' -print0 | xargs -0 --no-run-if-empty shellcheck
              # hosts/core/hardware-configuration.nix is a byte-for-byte copy of
              # nixos-generate-config output (plan: hosts/core must stay verbatim)
              # and is exempt from these two style linters accordingly.
              statix check . -i hosts/core/hardware-configuration.nix
              deadnix --fail . --exclude hosts/core/hardware-configuration.nix
              ruff check pkgs/broker tests/broker pkgs/helm tests/helm pkgs/lane tests/lane tests/mocks tools/ledger tests/ledger pkgs/dsh-openrouter tools/factory/seat tools/factory/route.py pkgs/evidence tests/evidence pkgs/seat tests/seat
              ruff format --check pkgs/broker tests/broker pkgs/helm tests/helm pkgs/lane tests/lane tests/mocks tools/ledger tests/ledger pkgs/dsh-openrouter tools/factory/seat tools/factory/route.py pkgs/evidence tests/evidence pkgs/seat tests/seat
              # See githooks/pre-commit for why this isn't a plain
              # `node --check tools/factory/dark-factory.js` (F35), and
              # darkFactorySyntaxCheckSrc above for why this reads the
              # source through builtins.readFile rather than piping it
              # through sed: a missing/renamed source file fails this
              # derivation's *evaluation*, loudly and unambiguously, instead
              # of relying on node --check to notice via a misleading
              # "Unexpected end of input".
              node --check ${darkFactorySyntaxCheckSrc}
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
              # P2: no '] && [' chains in bats tests (vacuous under errexit).
              bash tests/lint/bats-and-chain.sh
              # P12: prettier + oxlint gate every tracked JS file. The
              # self-test runs first (on its own line, not joined by `&&`:
              # under errexit a failing first command in an `a && b` list is
              # swallowed, which would silently gut the vacuous-gate guard);
              # the project sweep runs only if it passes.
              bash tests/lint/js-lint.sh --self-test
              bash tests/lint/js-lint.sh
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
              diff -u flake-checks map-checks || { echo "lint: docs/MAP.md Checks section differs from the flake's checks (regenerate: python3 pkgs/evidence/repomap.py write)" >&2; exit 1; }
              # G5: the repo map must be current.
              python3 pkgs/evidence/repomap.py --root . check
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
        # T1 (2026-09-03-factory-skills-and-review-gate): the dark-factory
        # script itself has no test harness of its own (it's a Workflow
        # sandbox script, no imports) -- render.test.mjs loads its text
        # verbatim and runs it with stub globals, so this check fails the
        # moment a prompt site drifts from spec §10 or the review-error
        # handling regresses.
        factory-unit =
          pkgs.runCommand "factory-unit"
            {
              # render.test.mjs derives the expected models map from route.py
              # run against the copied table, so python3 must be on PATH.
              nativeBuildInputs = [
                pkgs.nodejs
                pkgs.python3
              ];
            }
            ''
              mkdir -p tools/factory/plan .claude/workflows tests/factory docs/ledger pkgs/evidence
              cp ${self}/tools/factory/dark-factory.js tools/factory/dark-factory.js
              cp ${self}/tools/factory/route.py tools/factory/route.py
              cp ${self}/docs/ledger/routing.toml docs/ledger/routing.toml
              cp -r ${self}/tests/factory/fixtures tests/factory/fixtures
              cp ${self}/tests/factory/render.test.mjs tests/factory/render.test.mjs
              cp ${self}/tests/factory/plan.test.mjs tests/factory/plan.test.mjs
              cp ${self}/.claude/workflows/plan.js .claude/workflows/plan.js
              cp ${self}/tools/factory/plan/rubric.md tools/factory/plan/rubric.md
              cp ${self}/tools/factory/plan/judge-prompt.md tools/factory/plan/judge-prompt.md
              # pkgs/evidence/judgements.py `import evidence`s at module top, so
              # its --fields subprocess needs the sibling on the import path.
              cp ${self}/pkgs/evidence/judgements.py pkgs/evidence/judgements.py
              cp ${self}/pkgs/evidence/evidence.py pkgs/evidence/evidence.py
              node tests/factory/render.test.mjs
              node tests/factory/plan.test.mjs
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
              cp -r ${self}/tests/helm tests/helm
              pytest tests/helm -q
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
              pytest tests/evidence -q
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
              cp -r ${self}/tests/ledger tests-ledger
              cp -r ${self}/docs/ledger docs-ledger
              pytest tests-ledger -q
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
          builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "helm-eval-ok" { } "touch $out");
        evidence-eval =
          let
            c = evidenceEvalSystem.config;
          in
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.elem "d /var/lib/evidence 0750 dalhaka users -" c.systemd.tmpfiles.rules
            && nixpkgs.lib.elem "d /var/lib/evidence/ledger 0750 dalhaka users -" c.systemd.tmpfiles.rules
          ) "evidence-eval: the store and its ledger dir must be created 0750 dalhaka:users";
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.any (
            p: (p.pname or p.name or "") == "evidence"
          ) c.environment.systemPackages) "evidence-eval: the evidence CLI must be installed";
          builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "evidence-eval-ok" { } "touch $out");
        helm-assertion-negative =
          let
            attempt = builtins.tryEval helmBadSystem.config.system.build.toplevel.drvPath;
          in
          if attempt.success then
            throw "helm-assertion-negative: services.helm.listen on 0.0.0.0 DID NOT FAIL the build"
          else
            pkgs.runCommand "helm-assertion-negative-ok" { } "touch $out";
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
                ];
                inherit polkit switchExec;
              }
              ''
                # The rendered rule must enumerate exactly the two allowed
                # instances and gate on verb + user (never a bare NO).
                grep -F 'var allowed = ["helm-switch@base.service", "helm-switch@alt.service"];' "$polkitPath"
                grep -F 'action.lookup("verb") !== "start"' "$polkitPath"
                grep -F 'subject.user !== "dalhaka"' "$polkitPath"
                grep -F 'return polkit.Result.YES;' "$polkitPath"
                grep -F 'return undefined;' "$polkitPath"
                # The switch unit runs the generated switch script for %i.
                grep -q 'helm-switch %i' "$switchExecPath"
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
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "lane" c.users.users.dalhaka.extraGroups)
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
            && nixpkgs.lib.hasInfix "subject.user == \"dalhaka\"" c.security.polkit.extraConfig
            && nixpkgs.lib.hasInfix "polkit.Result.YES" c.security.polkit.extraConfig
          ) "lane-eval: polkit rule must gate verb=start on lane-testlane@*.service to operatorUser dalhaka";
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
        lane-polkit-unit =
          pkgs.runCommand "lane-polkit-unit-tests"
            {
              nativeBuildInputs = [ pkgs.nodejs ];
            }
            ''
              mkdir -p tests/lane
              cp ${self}/tests/lane/polkit.test.mjs tests/lane/polkit.test.mjs
              export LANE_POLKIT_RULES=${lanePolkitRules}
              node tests/lane/polkit.test.mjs
              touch $out
            '';
        seat-eval =
          let
            # SB1: the seat is wired into host `core` itself (hosts/core/seat.nix),
            # so this check asserts on the real evaluated core config -- unlike
            # lane-eval's isolated testlane harness, the collision assertion below
            # needs the co-resident openrouter lane (10.100.3.x) in the same
            # config alongside the seat's 10.100.4.x.
            c = self.nixosConfigurations.core.config;
            unit = c.systemd.services."seat@";
            sc = unit.serviceConfig;
            i = c.services.egress-broker.instances.seat;
            polkit = c.security.polkit.extraConfig;
            caBundle = "/var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt";
            otherInstances = builtins.attrNames c.services.egress-broker.instances;
          in
          assert nixpkgs.lib.assertMsg
            (
              i.hostAddress == "10.100.4.1"
              && i.namespaceAddress == "10.100.4.2"
              && i.listenPort == 3141
              && i.allow == [ "openrouter.ai" ]
            )
            "seat-eval: egress-broker instance 'seat' must take the 10.100.4.x block (host .1, namespace .2, :3141) and allow == [ \"openrouter.ai\" ]";
          assert nixpkgs.lib.assertMsg (
            i.inject."openrouter.ai".valueFile == "/var/lib/secrets/openrouter-key"
          ) "seat-eval: egress-broker instance 'seat' must inject from /var/lib/secrets/openrouter-key";
          assert nixpkgs.lib.assertMsg (
            sc.NetworkNamespacePath == "/run/netns/egress-seat" && sc.User == "dalhaka"
          ) "seat-eval: seat@ must join /run/netns/egress-seat and run as the operator dalhaka";
          assert nixpkgs.lib.assertMsg
            (
              unit.environment.HTTPS_PROXY == "http://10.100.4.1:3141"
              && unit.environment.HTTP_PROXY == "http://10.100.4.1:3141"
              && unit.environment.NO_PROXY == "127.0.0.1,10.100.4.2"
            )
            "seat-eval: seat@ must point HTTPS_PROXY/HTTP_PROXY at the broker and NO_PROXY at loopback + the namespace address";
          assert nixpkgs.lib.assertMsg
            (unit.environment.NODE_EXTRA_CA_CERTS == caBundle && unit.environment.SSL_CERT_FILE == caBundle)
            "seat-eval: seat@ must point NODE_EXTRA_CA_CERTS/SSL_CERT_FILE at the seat's public ca-bundle.crt";
          assert nixpkgs.lib.assertMsg (
            unit.environment.OPENROUTER_API_KEY == "injected-by-broker"
            && unit.environment.NODE_USE_ENV_PROXY == "1"
          ) "seat-eval: seat@ must hold the placeholder credential (never a key) and NODE_USE_ENV_PROXY=1";
          assert nixpkgs.lib.assertMsg (
            unit.environment.FACTORY_ROUTING_TABLE == "/home/dalhaka/nixos-agent-env/docs/ledger/routing.toml"
            && unit.environment.SEAT_NAMESPACE_ADDRESS == "10.100.4.2"
          ) "seat-eval: seat@ must set FACTORY_ROUTING_TABLE and SEAT_NAMESPACE_ADDRESS";
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "/var/lib/secrets" sc.InaccessiblePaths)
            "seat-eval: seat@ InaccessiblePaths must hide /var/lib/secrets";
          assert nixpkgs.lib.assertMsg (
            !(nixpkgs.lib.any (v: nixpkgs.lib.hasInfix "sk-or-" v) (nixpkgs.lib.attrValues unit.environment))
          ) "seat-eval: no seat@ environment value may look like a key (regex sk-or-)";
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "/bin/seat-run %i" sc.ExecStart)
            "seat-eval: seat@ ExecStart must be seat-run's stable path and %i";
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.hasInfix "seat@" polkit
            && nixpkgs.lib.hasInfix "\"start\"" polkit
            && nixpkgs.lib.hasInfix "\"stop\"" polkit
            && nixpkgs.lib.hasInfix "\"restart\"" polkit
            && nixpkgs.lib.hasInfix "subject.user == \"dalhaka\"" polkit
          ) "seat-eval: polkit rule must gate start/stop/restart on seat@*.service to operatorUser dalhaka";
          assert nixpkgs.lib.assertMsg
            (builtins.all (
              n:
              n == "seat"
              || (
                !(nixpkgs.lib.hasPrefix "10.100.4." c.services.egress-broker.instances.${n}.hostAddress)
                && !(nixpkgs.lib.hasPrefix "10.100.4." c.services.egress-broker.instances.${n}.namespaceAddress)
              )
            ) otherInstances)
            "seat-eval: 10.100.4.x must be the seat's own block -- no other egress-broker instance may collide with it";
          builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "seat-eval-ok" { } "touch $out");
        seat-assertion-negative =
          let
            keyAttempt = builtins.tryEval seatBadKeySystem.config.system.build.toplevel.drvPath;
            envAttempt = builtins.tryEval seatBadEnvSystem.config.system.build.toplevel.drvPath;
          in
          if keyAttempt.success then
            throw "seat-assertion-negative: services.seat-lane.keyFile = a store path DID NOT FAIL the build"
          else if envAttempt.success then
            throw "seat-assertion-negative: a real-looking key merged into the seat@ unit environment DID NOT FAIL the build"
          else
            pkgs.runCommand "seat-assertion-negative-ok" { } "touch $out";
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
          helmModule = self.nixosModules.helm;
        };
        # Helm v1 (plan Task 4 / consolidated D4): the real runtime proof —
        # a `switch-to-configuration test` into a real specialisation driven
        # through the loopback page, the full negative matrix, live polkit
        # denials, the agent-unit NRestarts invariants and the D1 allowlist
        # stability at the artifact level. Long: it builds two toplevels.
        helm-control-vm = import ./tests/integration/helm-control-vm.nix {
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
              ]
              ++ basketRuntimeInputs;
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
              # route.py validates the committed table and cross-checks the
              # bash lookup in the same test file; copy it and the table so
              # those two tests run for real rather than skipping.
              cp ${self}/tools/factory/route.py tools/factory/route.py
              mkdir -p docs
              cp -r ${self}/docs/ledger docs/ledger
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
              # tests/unit/91-orchestrator-guard.bats reads the runbook's recipe
              # section at ../../docs/runbooks/session.md (the sweep fixture is
              # pinned to it), so copy it in like the resolves above.
              mkdir -p docs/runbooks
              cp ${self}/docs/runbooks/session.md docs/runbooks/session.md
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
        # Task 3: core is wired onto protonBackup and rclone is retired.
        # lib.getName (not derivation identity) so this holds regardless of
        # which nixpkgs pin built the package that ended up in
        # environment.systemPackages.
        core-backup-wiring =
          let
            coreCfg = self.nixosConfigurations.core.config;
            hasRclone = builtins.any (p: nixpkgs.lib.getName p == "rclone") coreCfg.environment.systemPackages;
            backupDoc = builtins.readFile ./docs/runbooks/backup.md;
            homeSpelling = p: builtins.replaceStrings [ "/home/dalhaka" ] [ "~" ] p;
            undocumented = builtins.filter (
              p: !(nixpkgs.lib.hasInfix p backupDoc || nixpkgs.lib.hasInfix (homeSpelling p) backupDoc)
            ) coreCfg.services.proton-backup.paths;
          in
          if coreCfg.services.proton-backup.enable != true then
            throw "core-backup-wiring: services.proton-backup.enable is not true on core"
          else if !(coreCfg.services.restic.backups ? core-local) then
            throw "core-backup-wiring: services.restic.backups.core-local is missing on core"
          else if coreCfg.services.restic.backups ? proton-drive then
            throw "core-backup-wiring: services.restic.backups.proton-drive is still present (the rclone-era backup was not retired)"
          else if hasRclone then
            throw "core-backup-wiring: rclone is still present in core's environment.systemPackages"
          else if undocumented != [ ] then
            throw "core-backup-wiring: docs/runbooks/backup.md does not name these backup paths: ${toString undocumented}"
          else if !(nixpkgs.lib.hasInfix "each lane's `ledger.jsonl`" backupDoc) then
            throw "core-backup-wiring: docs/runbooks/backup.md must keep the lane-ledger bullet (each lane's `ledger.jsonl`) — /var/lib/lanes is the backup's audit record"
          else if !(nixpkgs.lib.hasInfix "/var/lib/egress-broker" backupDoc) then
            throw "core-backup-wiring: docs/runbooks/backup.md must state that /var/lib/egress-broker is never backed up (decision 2026-09-05 addendum: the broker audit logs never leave the machine)"
          else
            pkgs.runCommand "core-backup-wiring-check" { } "touch $out";
        # Host-wiring plan Task 1: the gaming profile is a specialisation
        # (base unchanged), /etc/helm/profile marks the active profile, the
        # backup paths cover the new repos and every per-flake memory dir,
        # and the flake.lock nixpkgs pin didn't drift when the gaming input
        # was added.
        core-gaming-wiring =
          let
            coreCfg = self.nixosConfigurations.core.config;
            # nixpkgs types options.specialisation.<name>.configuration with
            # `inherit (extendModules {...}) type;` (nixos/modules/system/
            # activation/specialisation.nix): its VALUE is already the merged
            # config attrset, not a submodule wrapper -- there is no extra
            # `.config` to go through (deviation from the plan's literal
            # `.configuration.config...`, which errors here with "attribute
            # 'config' missing"; verified with `nix eval
            # .#nixosConfigurations.core.config.specialisation.gaming.configuration
            # --apply builtins.attrNames`, which lists `programs` etc directly).
            gamingSpec = coreCfg.specialisation.gaming.configuration;
            fw = coreCfg.networking.firewall;
            steamTCPPorts = [
              27015
              27036
              27040
            ];
            steamUDPPorts = [
              27015
              27036
            ];
            hasAny = ps: l: builtins.any (p: builtins.elem p l) ps;
            inSteamRange = builtins.any (r: r.from <= 27035 && r.to >= 27031) fw.allowedUDPPortRanges;
            memoryDirs = [
              "/home/dalhaka/.claude/projects/-home-dalhaka-flakes-gaming/memory"
              "/home/dalhaka/.claude/projects/-home-dalhaka-flakes-media/memory"
              "/home/dalhaka/.claude/projects/-home-dalhaka-strategy/memory"
            ];
            backupPaths = coreCfg.services.proton-backup.paths;
            lockData = builtins.fromJSON (builtins.readFile ./flake.lock);
            # Scoped to nixpkgs-host (what nixosConfigurations.core actually
            # evaluates against) and the gaming input's own transitively-locked
            # nixpkgs (resolved by node id via lockData.nodes.gaming.inputs.nixpkgs,
            # not by the auto-numbered bare "nixpkgs" key, which nix flake lock
            # already hands to llm-agents' unrelated internal pin). This is the
            # guard the plan's Global Constraints describes: no `follows`, so
            # `nix flake lock` may add a same-rev node for gaming's nixpkgs (fine)
            # but it must be the exact same rev as the host pin (blocker
            # otherwise) -- round 2 (Opus re-gate) tightened this from a
            # whitelist-membership test to direct equality, since a whitelist
            # only catches drift the whitelist's author already anticipated. It
            # does NOT cover llm-agents' or claude-desktop's own foreign nixpkgs
            # pins (nodes "nixpkgs" and the other "nixpkgs_*" here) -- those are
            # pre-existing, deliberately separate package sets (see this file's
            # own comment on llm-agents above), unrelated to the gaming input and
            # already present before this task; a literal "every NixOS/nixpkgs
            # node" reading would flag them permanently, for a reason unrelated
            # to gaming. Reported as a deviation from the plan's literal wording.
            gamingNixpkgsNodeName = lockData.nodes.gaming.inputs.nixpkgs;
            gamingNixpkgsRev = lockData.nodes.${gamingNixpkgsNodeName}.locked.rev;
            hostNixpkgsRev = lockData.nodes.nixpkgs-host.locked.rev;
          in
          if coreCfg.programs.gaming.enable != false then
            throw "core-gaming-wiring: base profile has programs.gaming.enable != false"
          else if coreCfg.environment.etc."helm/profile".text != "base" then
            throw "core-gaming-wiring: base /etc/helm/profile is not \"base\""
          else if !(coreCfg.specialisation ? gaming) then
            throw "core-gaming-wiring: no specialisation named \"gaming\""
          else if gamingSpec.programs.gaming.enable != true then
            throw "core-gaming-wiring: specialisation.gaming.configuration.config.programs.gaming.enable is not true"
          else if gamingSpec.environment.etc."helm/profile".text != "gaming" then
            throw "core-gaming-wiring: specialisation.gaming's /etc/helm/profile is not \"gaming\""
          else if hasAny steamTCPPorts fw.allowedTCPPorts then
            throw "core-gaming-wiring: base firewall has a Steam TCP port open"
          else if hasAny steamUDPPorts fw.allowedUDPPorts then
            throw "core-gaming-wiring: base firewall has a Steam UDP port open"
          else if inSteamRange then
            throw "core-gaming-wiring: base firewall has the Steam UDP port range open"
          else if !(nixpkgs.lib.all (d: builtins.elem d backupPaths) memoryDirs) then
            throw "core-gaming-wiring: services.proton-backup.paths is missing a per-flake memory dir"
          else if !(builtins.elem "/home/dalhaka/flakes" backupPaths) then
            throw "core-gaming-wiring: services.proton-backup.paths is missing /home/dalhaka/flakes"
          else if gamingNixpkgsRev != hostNixpkgsRev then
            throw "core-gaming-wiring: flake.lock's gaming-input nixpkgs (${gamingNixpkgsRev}) is not the same rev as nixpkgs-host (${hostNixpkgsRev}) (a second nixpkgs entered the closure at a different rev)"
          else
            pkgs.runCommand "core-gaming-wiring-check" { } "touch $out";
      };

      formatter.${system} = pkgs.treefmt;
    };
}
