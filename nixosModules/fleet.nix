# FL1 (plan 2026-09-24-fleet-and-forge.md): the fleet module -- the one
# declared list of machines (fleet.machines, hosts/fleet.json), the pinned
# identities around it (host keys, the LAN, the deploy keys) and the deploy
# user every deploy-accepting machine carries. An operator machine renders
# none of the deploy surface: no sshd, no deploy user, no sudo rule.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.fleet;
  hostName = config.networking.hostName;

  # The one list in this file: a role accepts deploys iff it is in it.
  deployRoles = [ "forge" ];
  acceptsDeploys = m: lib.any (r: lib.elem r deployRoles) m.roles;

  # An address, not a shape: exactly four '.'-separated decimal parts, each
  # 0-255 after lib.toInt ("256.1.1.1" and "1.2.3" are both refused).
  isIPv4 =
    a:
    (builtins.match "^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+$" a != null)
    && lib.all (p: lib.toInt p <= 255) (lib.splitString "." a);

  ipToInt = a: lib.foldl (acc: o: acc * 256 + o) 0 (map lib.toInt (lib.splitString "." a));

  # 2^n by repeated doubling (this lib has no pow).
  pow2 = n: lib.foldl (acc: _: acc * 2) 1 (lib.genList (_: 0) n);

  # a lies inside cidr: the network halves of both addresses, compared under
  # the subnet's mask (bitAnd, arithmetic -- never a spelling list).
  inSubnet =
    a: cidr:
    let
      parts = lib.splitString "/" cidr;
      n = lib.toInt (lib.elemAt parts 1);
      mask = 4294967296 - (pow2 (32 - n));
    in
    (lib.bitAnd (ipToInt a) mask) == (lib.bitAnd (ipToInt (lib.head parts)) mask);

  isCIDR =
    cidr:
    let
      m = builtins.match "^([^/]+)/(3[0-2]|[0-2]?[0-9])$" cidr;
    in
    m != null && isIPv4 (lib.head m);

  keyRe = "^ssh-ed25519 [A-Za-z0-9+/]+=*$";
  deployKeyRe = "(sk-ssh-ed25519@openssh\\.com|ssh-ed25519) [A-Za-z0-9+/]+=* [^ ]+";

  # Every machine other than this one: what knownHosts and networking.hosts
  # render from. The machine itself never enters its own maps.
  others = lib.filterAttrs (n: _: n != hostName) cfg.machines;

  # The deploy user's sudo allowance, byte for byte: exactly two NOPASSWD
  # commands. The module's rule set is tagged by this exact structure (rule
  # (i) below), so a foreign rule naming deploy is refused at evaluation.
  sudoRule = {
    users = [ "deploy" ];
    groups = [ ];
    host = "ALL";
    runAs = "ALL:ALL";
    commands = [
      {
        command = "/run/current-system/sw/bin/nix-env --profile /nix/var/nix/profiles/system --set /nix/store/*";
        options = [ "NOPASSWD" ];
      }
      {
        command = "/nix/store/*/bin/switch-to-configuration switch";
        options = [ "NOPASSWD" ];
      }
    ];
  };

  anyDeploys = lib.any acceptsDeploys (lib.attrValues cfg.machines);
  deployAcceptors = lib.concatStringsSep ", " (
    lib.filter (name: acceptsDeploys cfg.machines.${name}) (lib.attrNames cfg.machines)
  );

  # Rules (b), (d), (e) and (g) -- one rule over every machine, never a
  # spelling list: the per-machine list is flattened from mapAttrsToList so
  # every rule runs over every declared machine.
  perMachineAssertions =
    name: m:
    [
      {
        # (b) at least one role, and never operator beside a deploy-accepting
        # role.
        assertion = m.roles != [ ] && !(lib.elem "operator" m.roles && acceptsDeploys m);
        message = "fleet: fleet.machines.${name}.roles must hold at least one role and never both operator and a deploy-accepting role (one of ${toString deployRoles})";
      }
    ]
    ++ (
      if acceptsDeploys m then
        [
          {
            # (d) address is an IPv4 address.
            assertion = m.address != null && isIPv4 m.address;
            message = "fleet: fleet.machines.${name}.address must be an IPv4 dotted quad (four decimal parts 0-255), got '${toString m.address}'";
          }
          {
            # (d) prefix, interface and efi are declared.
            assertion = m.prefix != null && m.interface != null && m.efi != null;
            message = "fleet: fleet.machines.${name} accepts deploys and must declare prefix, interface and efi (got prefix = ${toString m.prefix}, interface = ${toString m.interface}, efi = ${toString m.efi})";
          }
          {
            # (d) hostKey: type and base64, no comment.
            assertion = m.hostKey != null && builtins.match keyRe m.hostKey != null;
            message = "fleet: fleet.machines.${name}.hostKey must be 'ssh-ed25519 <base64>' with no comment, got '${toString m.hostKey}'";
          }
          {
            # (d) stateVersion is YY.MM.
            assertion = m.stateVersion != null && builtins.match "^[0-9]{2}\\.[0-9]{2}$" m.stateVersion != null;
            message = "fleet: fleet.machines.${name}.stateVersion must be a NixOS stateVersion in YY.MM form, got '${toString m.stateVersion}'";
          }
        ]
        ++ lib.optionals (cfg.lan != null) [
          {
            # (g) the address lies inside fleet.lan.subnet, by arithmetic.
            assertion = m.address != null && inSubnet m.address cfg.lan.subnet;
            message = "fleet: fleet.machines.${name}.address ${toString m.address} lies outside fleet.lan.subnet ${cfg.lan.subnet}";
          }
        ]
      else
        # (e) an operator machine declares none of the deploy-accepting
        # fields.
        map
          (
            field:
            let
              value = builtins.getAttr field m;
            in
            {
              assertion = value == null;
              message = "fleet: ${name} has the operator role and declares ${field}; an operator machine has no address and no host key";
            }
          )
          [
            "address"
            "prefix"
            "interface"
            "hostKey"
            "efi"
            "stateVersion"
          ]
    );

  # Rules (a), (c) and (h) -- this host's own rules, plus (i) over every
  # sudo rule in the configuration.
  thisHostAssertions =
    let
      declared = cfg.machines ? ${hostName};
      m = cfg.machines.${hostName} or null;
    in
    [
      {
        # (a) this host is declared.
        assertion = declared;
        message = "fleet: ${hostName} is not declared in fleet.machines (hosts/fleet.json); every host that imports this module must be declared";
      }
      # (i) no sudo rule outside the module's own names deploy: every rule
      # whose users contain deploy must be exactly the one this module
      # renders.
      {
        assertion = lib.all (
          rule: !(lib.elem "deploy" rule.users) || rule == sudoRule
        ) config.security.sudo.extraRules;
        message = "fleet: ${hostName}: security.sudo.extraRules carries a rule for the deploy user that the fleet module did not render";
      }
    ]
    ++ lib.optionals declared (
      [
        {
          # (c) an operator machine never enables services.openssh. A machine
          # holding operator beside a deploy-accepting role is already
          # refused by (b), so (c) keys on the pure operator machine (the
          # both-roles arm of checks.fleet-assertion-negative must fail for
          # (b) and (b) alone).
          assertion = acceptsDeploys m || !(lib.elem "operator" m.roles) || !config.services.openssh.enable;
          message = "fleet: ${hostName} has the operator role and enables services.openssh; core never accepts an inbound connection";
        }
      ]
      ++ lib.optionals (acceptsDeploys m) [
        {
          # (h) the declared address is actually configured on the declared
          # interface.
          assertion =
            m.address != null
            && m.interface != null
            && builtins.any (entry: entry.address == m.address) (
              config.networking.interfaces.${m.interface}.ipv4.addresses or [ ]
            );
          message = "fleet: ${hostName} declares ${toString m.address} on ${toString m.interface} but networking.interfaces.${toString m.interface}.ipv4.addresses does not carry it";
        }
      ]
    );

  # Rule (f) -- the shared identities, required once any machine accepts
  # deploys: at least one well-formed deploy key, and the LAN declared.
  deployIdentityAssertions = lib.optionals anyDeploys (
    [
      {
        assertion = cfg.deployKeys != [ ];
        message = "fleet: fleet.deployKeys must not be empty when a machine accepts deploys (${deployAcceptors} do)";
      }
      {
        assertion = cfg.lan != null && isCIDR cfg.lan.subnet;
        message = "fleet: fleet.lan must be declared with a subnet of the form <IPv4>/<0-32> when a machine accepts deploys (${deployAcceptors} do)";
      }
    ]
    ++ map (k: {
      assertion = builtins.match deployKeyRe k != null;
      message = "fleet: fleet.deployKeys entry '${k}' must be '<type> <base64> <comment>' with type one of sk-ssh-ed25519@openssh.com, ssh-ed25519";
    }) cfg.deployKeys
  );

  # FL7 (plan 2026-09-24-fleet-and-forge.md): the mirror script -- the
  # packaged form of pkgs/fleet/mirror.sh (git and ssh on its PATH), the
  # ExecStart of the fleet-mirror user unit below.
  mirrorScript = pkgs.writeShellApplication {
    name = "fleet-mirror";
    runtimeInputs = [
      pkgs.git
      pkgs.openssh
    ];
    text = builtins.readFile ../pkgs/fleet/mirror.sh;
  };

  # The mirror block's own rules: every field is validated at evaluation
  # whenever a mirror is declared, on any machine (the units render only on
  # an operator machine; the assertions never depend on the rendering).
  mirrorAssertions = lib.optionals (cfg.mirror != null) [
    {
      # The pushed-to machine is declared and carries the pinned identity
      # (address and host key): networking.hosts resolves its name and
      # /etc/ssh/ssh_known_hosts pins it, so the URL never needs an address.
      assertion =
        cfg.machines ? ${cfg.mirror.machine}
        && cfg.machines.${cfg.mirror.machine}.address != null
        && cfg.machines.${cfg.mirror.machine}.hostKey != null;
      message = "fleet: mirror.machine: must name a declared machine with a non-null address and hostKey, got '${toString cfg.mirror.machine}'";
    }
    {
      assertion = builtins.match "^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+\\.git$" cfg.mirror.repo != null;
      message = "fleet: mirror.repo: must be '<owner>/<repo>.git' over [A-Za-z0-9._-] parts, got '${toString cfg.mirror.repo}'";
    }
    {
      assertion = lib.hasPrefix "/" cfg.mirror.keyFile;
      message = "fleet: mirror.keyFile: must be an absolute path, got '${toString cfg.mirror.keyFile}'";
    }
    {
      assertion = lib.hasPrefix "/" cfg.mirror.checkout;
      message = "fleet: mirror.checkout: must be an absolute path, got '${toString cfg.mirror.checkout}'";
    }
    {
      assertion = config.users.users ? ${cfg.mirror.runAs};
      message = "fleet: mirror.runAs: must name a declared user (config.users.users), got '${toString cfg.mirror.runAs}'";
    }
  ];
in
{
  options.fleet = {
    machines = lib.mkOption {
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            roles = lib.mkOption {
              type = lib.types.listOf (
                lib.types.enum [
                  "operator"
                  "forge"
                ]
              );
              description = "The machine's roles; every role other than operator means the machine accepts fleet deploys.";
            };
            address = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "The machine's LAN IPv4 address; required for a deploy-accepting machine, always null for an operator machine.";
            };
            prefix = lib.mkOption {
              type = lib.types.nullOr (lib.types.ints.between 8 30);
              default = null;
              description = "The prefix length of the machine's LAN address; required for a deploy-accepting machine, always null for an operator machine.";
            };
            interface = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "The LAN interface the machine's address is configured on; required for a deploy-accepting machine, always null for an operator machine.";
            };
            hostKey = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "The machine's host key, 'ssh-ed25519 <base64>' with no comment; required for a deploy-accepting machine, always null for an operator machine.";
            };
            efi = lib.mkOption {
              type = lib.types.nullOr lib.types.bool;
              default = null;
              description = "Whether the machine boots via UEFI; required for a deploy-accepting machine, always null for an operator machine.";
            };
            stateVersion = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "The machine's NixOS stateVersion in YY.MM form; required for a deploy-accepting machine, always null for an operator machine.";
            };
          };
        }
      );
      default = { };
      description = "The one declared list of fleet machines, loaded from hosts/fleet.json; the machine whose name equals networking.hostName is this host.";
    };

    deployKeys = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "The SSH public keys authorized for the deploy user, each '<type> <base64> <comment>'; must be non-empty once any machine accepts deploys.";
    };

    lan = lib.mkOption {
      type = lib.types.nullOr (
        lib.types.submodule {
          options = {
            subnet = lib.mkOption {
              type = lib.types.str;
              description = "The LAN subnet in CIDR form: an IPv4 address and a prefix 0-32. Every deploy-accepting machine's address must lie inside it.";
            };
            gateway = lib.mkOption {
              type = lib.types.str;
              description = "The LAN gateway's IPv4 address.";
            };
            nameservers = lib.mkOption {
              type = lib.types.listOf lib.types.str;
              description = "The LAN's nameservers, as IPv4 addresses.";
            };
          };
        }
      );
      default = null;
      description = "The LAN every deploy-accepting machine's address lies inside; must be declared once any machine accepts deploys.";
    };

    thisMachine = lib.mkOption {
      type = lib.types.attrs;
      internal = true;
      readOnly = true;
      description = "This host's fleet.machines entry (the entry named by config.networking.hostName); undefined when the host is not declared.";
    };

    acceptsDeploys = lib.mkOption {
      type = lib.types.bool;
      internal = true;
      readOnly = true;
      description = "Whether this machine holds a role other than operator, i.e. accepts fleet deploys.";
    };

    # FL5 (plan 2026-09-24-fleet-and-forge.md): the command itself, installed
    # where a host sets it (core, through hosts/core/fleet.nix).
    package = lib.mkOption {
      type = lib.types.nullOr lib.types.package;
      default = null;
      description = "the fleet command, installed where set";
    };

    # FL7 (plan 2026-09-24-fleet-and-forge.md): the mirror -- this
    # machine's user timer pushing main and the live-* tags to the forge.
    # An operator machine renders the units; a deploy-accepting machine
    # never does (the assertions still run on every machine).
    mirror = lib.mkOption {
      type = lib.types.nullOr (
        lib.types.submodule {
          options = {
            machine = lib.mkOption {
              type = lib.types.str;
              description = "The declared fleet machine the mirror pushes to; must name a machine with a non-null address and hostKey, so the URL's host can stay the machine's name.";
            };
            repo = lib.mkOption {
              type = lib.types.str;
              description = "The repository on the mirror machine, '<owner>/<repo>.git'.";
            };
            user = lib.mkOption {
              type = lib.types.str;
              default = "forgejo";
              description = "The git SSH user on the mirror machine (the forge's forgejo user).";
            };
            keyFile = lib.mkOption {
              type = lib.types.str;
              description = "The absolute path of the SSH identity the mirror push uses.";
            };
            checkout = lib.mkOption {
              type = lib.types.str;
              description = "The absolute path of the local checkout the mirror timer pushes.";
            };
            onCalendar = lib.mkOption {
              type = lib.types.str;
              default = "hourly";
              description = "The systemd calendar the mirror timer fires on.";
            };
            runAs = lib.mkOption {
              type = lib.types.str;
              description = "The declared user the mirror units run as; the service and timer are gated on it with ConditionUser.";
            };
          };
        }
      );
      default = null;
      description = "The mirror: this machine's user timer pushing main and the live-* tags to the forge; a deploy-accepting machine never renders it.";
    };
  };

  config = lib.mkMerge [
    {
      assertions =
        lib.flatten (lib.mapAttrsToList perMachineAssertions cfg.machines)
        ++ thisHostAssertions
        ++ deployIdentityAssertions
        ++ mirrorAssertions;

      # Rendering for every host: the other machines' pinned identities.
      # Nothing for the machine itself, and nothing for a machine without
      # a host key (an operator machine).
      programs.ssh.knownHosts = lib.mapAttrs (n: m: {
        hostNames = [
          n
          m.address
        ];
        publicKey = m.hostKey;
      }) (lib.filterAttrs (_: m: m.hostKey != null) others);

      networking.hosts = lib.mapAttrs' (n: m: lib.nameValuePair m.address [ n ]) (
        lib.filterAttrs (_: m: m.address != null) others
      );

      fleet.thisMachine = lib.mkIf (cfg.machines ? ${hostName}) cfg.machines.${hostName};

      fleet.acceptsDeploys = cfg.machines ? ${hostName} && acceptsDeploys cfg.machines.${hostName};

      # FL5 (plan 2026-09-24-fleet-and-forge.md): the fleet command itself.
      environment.systemPackages = lib.optional (cfg.package != null) cfg.package;
    }
    # Rendering for a deploy-accepting host: sshd pinned to the declared
    # address, the LAN-scoped nft input rule, and the deploy user. The guard
    # keeps an invalid declaration failing through the assertions (a throw
    # checks.fleet-assertion-negative can catch) rather than a null coerced
    # into sshd's config mid-render.
    (lib.mkIf
      (
        cfg.acceptsDeploys
        && cfg.thisMachine.address != null
        && cfg.thisMachine.interface != null
        && cfg.lan != null
      )
      {
        services.openssh = {
          enable = true;
          openFirewall = false;
          listenAddresses = [
            {
              addr = cfg.thisMachine.address;
              port = 22;
            }
          ];
          settings = {
            PasswordAuthentication = false;
            KbdInteractiveAuthentication = false;
            PermitRootLogin = "no";
          };
        };

        networking.nftables.enable = true;
        networking.firewall.extraInputRules = ''
          iifname "${cfg.thisMachine.interface}" ip saddr ${cfg.lan.subnet} tcp dport 22 accept
        '';

        users.users.deploy = {
          isNormalUser = true;
          description = "fleet deploy user";
          shell = "/run/current-system/sw/bin/bash";
          openssh.authorizedKeys.keys = cfg.deployKeys;
        };

        security.sudo.extraRules = [ sudoRule ];

        nix.settings.trusted-users = [ "deploy" ];
      }
    )
    # FL7 (plan 2026-09-24-fleet-and-forge.md): the mirror rendering -- an
    # operator machine's user timer pushing main and the live-* tags to the
    # forge. The URL's host is the machine's NAME: networking.hosts resolves
    # it and /etc/ssh/ssh_known_hosts pins it, so the allowlist line carries
    # no address. A deploy-accepting machine never mirrors: the assertions
    # above still run there, but the units do not render.
    (lib.mkIf (cfg.mirror != null && !cfg.acceptsDeploys) {
      systemd.user.services.fleet-mirror = {
        description = "fleet: push main and the live-* tags to ${cfg.mirror.machine}";
        unitConfig.ConditionUser = cfg.mirror.runAs;
        environment = {
          FLEET_MIRROR_CHECKOUT = cfg.mirror.checkout;
          FLEET_MIRROR_URL = "ssh://${cfg.mirror.user}@${cfg.mirror.machine}/${cfg.mirror.repo}";
          FLEET_MIRROR_KEY = cfg.mirror.keyFile;
        };
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${mirrorScript}/bin/fleet-mirror";
        };
      };

      systemd.user.timers.fleet-mirror = {
        description = "fleet: the mirror push, ${cfg.mirror.onCalendar}";
        unitConfig.ConditionUser = cfg.mirror.runAs;
        wantedBy = [ "timers.target" ];
        timerConfig = {
          OnCalendar = cfg.mirror.onCalendar;
          Persistent = true;
          RandomizedDelaySec = "5m";
        };
      };
    })
  ];
}
