{
  config,
  lib,
  ...
}:
let
  cfg = config.services.lan-access;
  hostname = config.networking.hostName;

  # The one host-side directory Caddy may traverse to reach a site's bcrypt
  # hash file. /var/lib/secrets is 0710 root:egress-broker (seatLane.nix), which
  # the `caddy` user/group cannot traverse, so lan-access keeps its own dir.
  hashDir = "/var/lib/lan-access";

  isLoopback = addr: addr == "127.0.0.1" || addr == "::1";

  # Each site's rendered vhost name: <name>.<hostname>.local.
  vhostName = name: "${name}.${hostname}.local";

  # Caddy's internal CA root, inside its own StateDirectory. tests/integration
  # /lan-vm.nix reads this same path, so if nixpkgs ever moves caddy's data dir
  # the VM test fails loudly rather than the bootstrap quietly serving a 404.
  caRootDir = "/var/lib/caddy/.local/share/caddy/pki/authorities/local";

  # A caBootstrap site gets a SECOND vhost, keyed with the explicit http://
  # scheme. That prefix is what stops Caddy's auto-HTTPS from owning port 80
  # for this hostname, and it is part of the vhost ATTRIBUTE NAME -- so
  # renderedHosts is built through this same function or assertion A3
  # subtracts the wrong string and reports the site's own vhost as foreign.
  bootstrapVhostName = name: "http://${vhostName name}";

  bootstrapSites = lib.filterAttrs (_: site: site.caBootstrap) cfg.sites;

  # A plainHttp address is its own vhost, keyed http://<addr>, so it wins port
  # 80 for that Host over Caddy's implicit redirect while every other name --
  # the site's own .local included -- keeps redirecting to https. Flattened to
  # (siteName, addr) pairs because one site may list several addresses.
  plainPairs = lib.concatLists (
    lib.mapAttrsToList (name: site: map (addr: { inherit name site addr; }) site.plainHttp) cfg.sites
  );
  plainVhostName = addr: "http://${addr}";
in
{
  options.services.lan-access = {
    enable = lib.mkEnableOption "LAN-exposed sites fronted by Caddy with an internal CA and one basic_auth each";
    interface = lib.mkOption {
      type = lib.types.str;
      description = "The LAN interface whose firewall opens ports 80/443 for the rendered sites.";
    };
    sites = lib.mkOption {
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            upstream = lib.mkOption {
              type = lib.types.str;
              description = "The loopback upstream each site reverse-proxies (127.0.0.1:<port> or [::1]:<port>).";
            };
            hashFile = lib.mkOption {
              type = lib.types.str;
              description = "Path to a bcrypt hash file under /var/lib/lan-access/, read by Caddy's {file.<path>} placeholder at config load.";
            };
            user = lib.mkOption {
              type = lib.types.str;
              description = "The basic_auth username for this site.";
            };
            plainHttp = lib.mkOption {
              type = lib.types.listOf lib.types.str;
              default = [ ];
              example = [ "192.168.1.100" ];
              description = ''
                Extra Host values -- a bare LAN address, or any name -- this
                site also answers on over plain HTTP, behind the same
                basic_auth, with no TLS and no name resolution involved.

                For a device that cannot resolve the site's .local name or
                trust the internal CA, this is the way in: an internal CA
                issues certificates for names, never for addresses, so an
                https URL built from an IP can never present a valid one and
                the redirect to it is a dead end.

                The cost is real and is the whole cost: basic_auth over plain
                HTTP sends the password base64-encoded in clear text on every
                request, and the proxied responses are unencrypted, so anyone
                on the same network can read both. The site's own .local name
                is unaffected and keeps its 308 to https -- opting one address
                in does not downgrade the site.
              '';
            };
            caBootstrap = lib.mkOption {
              type = lib.types.bool;
              default = false;
              description = ''
                Serve Caddy's internal CA root at http://<site>/ca.crt over
                plain HTTP, behind this site's own basic_auth, so a new device
                can fetch the root it must trust without an out-of-band file
                transfer and without clicking past a certificate warning.

                Only that one path is served without TLS; every other path on
                port 80 keeps its 308 to the https site. A CA root is a public
                certificate and carries no private key, so plain HTTP costs no
                secrecy -- but the first fetch is unverified by construction
                (trust on first use), which is the same exposure as installing
                the root from a file someone handed you.
              '';
            };
          };
        }
      );
      default = { };
      description = "The LAN-exposed sites, one per name.";
    };
    renderedHosts = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      internal = true;
      readOnly = true;
      description = "The Caddy virtual host names this module renders; assertion A3 subtracts these from services.caddy.virtualHosts to guard foreign sites.";
    };
  };

  # renderedHosts has no `default`: it is read-only, so a default would be a
  # second definition beside the one below and trip the read-only merge guard.
  # It is gated on cfg.enable so a disabled module reports [ ] (Interface 1).
  config = lib.mkMerge [
    {
      services.lan-access.renderedHosts = lib.mkIf cfg.enable (
        lib.sort lib.lessThan (
          (lib.mapAttrsToList (name: _: vhostName name) cfg.sites)
          ++ (lib.mapAttrsToList (name: _: bootstrapVhostName name) bootstrapSites)
          ++ (map (p: plainVhostName p.addr) plainPairs)
        )
      );
    }
    (lib.mkIf cfg.enable {
      assertions =
        # A1 (loopback upstream) and A4 (under /var/lib/lan-access/) fire once
        # per site.
        lib.concatLists (
          lib.mapAttrsToList (name: site: [
            {
              # builtins.match is POSIX ERE, where `\[` is not a valid escape
              # (Nix rejects `^\[::1\]:[0-9]+$` as an invalid regex). A bracket
              # expression is the spelling for a literal bracket: `[[]` matches
              # `[` and `[]]` matches `]`.
              assertion =
                (builtins.match "^127\\.0\\.0\\.1:[0-9]+$" site.upstream) != null
                || (builtins.match "^[[]::1[]]:[0-9]+$" site.upstream) != null;
              message = "services.lan-access.sites.${name}.upstream must be a loopback address, got '${site.upstream}'";
            }
            {
              assertion = lib.hasPrefix "${hashDir}/" site.hashFile;
              message = "services.lan-access.sites.${name}.hashFile must lie under ${hashDir}/ (the directory caddy may traverse), got '${site.hashFile}'";
            }
          ]) cfg.sites
        )
        # A3 -- the guard on the host: any Caddy virtual host this module did
        # not render must bind loopback-only (listenAddresses != [ ] and every
        # address 127.0.0.1/::1). nixpkgs' listenAddresses defaults to [ ], which
        # renders no `bind` and therefore binds everything.
        ++ lib.mapAttrsToList (name: vh: {
          assertion =
            (builtins.elem name cfg.renderedHosts)
            || (vh.listenAddresses != [ ] && lib.all isLoopback vh.listenAddresses);
          message = "a Caddy virtual host outside services.lan-access binds a non-loopback address: ${name}";
        }) config.services.caddy.virtualHosts;

      services.caddy = lib.mkIf (cfg.sites != { }) {
        enable = true;
        # Keyed by the vhost name so hostName defaults to it (vhost-options.nix),
        # and so renderedHosts -- built the same way -- matches name for name.
        virtualHosts =
          (lib.mapAttrs' (
            name: site:
            lib.nameValuePair (vhostName name) {
              extraConfig = ''
                tls internal
                basic_auth {
                  ${site.user} {file.${site.hashFile}}
                }
                reverse_proxy ${site.upstream}
              '';
            }
          ) cfg.sites)
          # The CA bootstrap vhost: /ca.crt is the one path port 80 serves, and
          # it carries the site's own basic_auth. `handle` blocks are mutually
          # exclusive, so the catch-all below cannot also match /ca.crt -- every
          # other path keeps the 308 the https site expects. `rewrite` is what
          # keeps the URL /ca.crt while the file on disk stays root.crt, so no
          # directory listing and no second file are ever reachable.
          // (lib.mapAttrs' (
            name: site:
            lib.nameValuePair (bootstrapVhostName name) {
              # nixpkgs derives the access-log filename from the vhost name,
              # which here carries the http:// prefix and renders as
              # `access-http:__<host>.log`. Named explicitly instead.
              logFormat = "output file /var/log/caddy/access-${name}-bootstrap.log";
              extraConfig = ''
                handle /ca.crt {
                  basic_auth {
                    ${site.user} {file.${site.hashFile}}
                  }
                  root * ${caRootDir}
                  rewrite * /root.crt
                  file_server
                }
                handle {
                  redir https://{host}{uri} 308
                }
              '';
            }
          ) bootstrapSites)
          # The plain-HTTP addresses: the whole site, same credential, no TLS.
          // (lib.listToAttrs (
            map (p: {
              name = plainVhostName p.addr;
              value = {
                logFormat = "output file /var/log/caddy/access-${p.name}-plain.log";
                extraConfig = ''
                  basic_auth {
                    ${p.site.user} {file.${p.site.hashFile}}
                  }
                  reverse_proxy ${p.site.upstream}
                '';
              };
            }) plainPairs
          ));
      };

      networking.firewall.interfaces.${cfg.interface}.allowedTCPPorts = lib.mkIf (cfg.sites != { }) [
        80
        443
      ];

      systemd.tmpfiles.rules = [ "d ${hashDir} 0710 root caddy -" ];

      environment.etc."lan-access/sites".text = lib.concatMapStringsSep "\n" (
        name: "${name} ${cfg.sites.${name}.upstream}"
      ) (lib.sort lib.lessThan (builtins.attrNames cfg.sites));
    })
  ];
}
