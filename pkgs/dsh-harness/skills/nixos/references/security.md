verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Writing firewall rules, a polkit rule, a setuid wrapper, or a user/group.

## Firewall composition: chains AND across hooks

At this pin, `networking.firewall.package` defaults to
`pkgs.iptables` — the nftables backend is opt-in
(`networking.nftables.enable = true`), not yet the default this
25.05-era pin ships. Under nftables, the generated `nixos-fw` table
chains a packet through **two separate hooks**, each `policy drop`: a
`prerouting`/`mangle+10` reverse-path chain first (drops or logs a
spoofed source before it reaches filtering), then the `input`/`filter`
chain. A packet must be accepted by **both** — a rule in
`networking.firewall.extraInputRules` cannot rescue a packet the
reverse-path chain already dropped, and
`networking.firewall.checkReversePath` is therefore not just an
input-chain option, it gates a chain the input chain never sees.
`networking.firewall.extraCommands`/`networking.firewall.extraStopCommands`
are **iptables-only** — set with `networking.nftables.enable = true`, they
fail a build-time assertion.

`extraInputRules` is itself declared unconditionally (so setting it
without nftables enabled evaluates clean, no assertion trips) but its
whole config block — the one that actually renders it into a table — is
gated `mkIf (cfg.enable && config.networking.nftables.enable)`; without
that second flag this "looks right, evaluates green" block installs
**no nftables ruleset at all**, silently, because the iptables backend
(this pin's default) never reads `extraInputRules` in the first place:

```nix module
{
  networking.nftables.enable = true;
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 443 ];
    extraInputRules = ''
      ip saddr 10.0.0.0/8 tcp dport 8080 accept
    '';
  };
}
```

## `security.polkit.extraConfig`: duktape ES5

`security.polkit.extraConfig` is raw JavaScript, executed by
polkit's bundled **duktape** engine — ES5, not the ES2015+ a modern
`node`/browser accepts. `===`, `!==`, and `.indexOf(...)` work;
_Array.prototype.includes_, template literals, `let`/`const`,
arrow functions, and `.startsWith`/`.endsWith` do not exist. Every rule
is a function passed to polkit's own `addRule`; the first one to `return`
a `Result` (`YES`/`NO`/`AUTH_ADMIN`/…) for an action wins — later rules
never run for that decision.

**Right** (ES5: `.indexOf`, no `includes`):

```text
polkit.addRule(function(action, subject) {
  if (action.id.indexOf("org.freedesktop.systemd1.") === 0 &&
      subject.isInGroup("wheel")) {
    return polkit.Result.YES;
  }
});
```

**Wrong:** _Array.prototype.includes_ does not exist in duktape's ES5 —
but calling `polkit.addRule(fn)` only _registers_ `fn`, it does not
invoke it, so this loads and compiles without error (not a `nix eval`
error either, since the string is opaque `lib.types.lines` to the
module system, nor a startup error — polkit parses the file fine).
The `TypeError` only fires **at the next authorization check that
reaches this rule** — a real action lookup, subject and all — which is
why it shows up as a runtime failure in polkit's own journal, not
anything visible when the unit starts or the config switches:

```text
polkit.addRule(function(action, subject) {
  var allowed = ["wheel", "operators"];
  if (allowed.includes(subject.user)) {
    return polkit.Result.YES;
  }
});
```

```text
polkitd[1234]: Error evaluating admin rules: TypeError: undefined not \
callable (property 'includes' of [object Array])
```

(one logical journal line, wrapped above for width — reproduced verbatim
with `pkgs.duktape`'s own `duk` CLI at this pin: `duktape-2.7.0`, the
exact engine `polkitd` embeds.)

## `security.wrappers`

Installs a small statically-linked (musl) setuid/setcap C wrapper at
`/run/wrappers/bin` (the internal, fixed _security.wrapperDir_) that
execs the real program after stripping the `LD_*`/glibc-unsafe environment
variables a setuid process must not inherit. Use it only for a program
**users invoke directly** and that genuinely needs a privilege bit —
`ping` (raw sockets), `fusermount`, `sudo`/`su`-alikes. A service you
control does not need a wrapper: give the _unit_ the one capability it
needs (`AmbientCapabilities`/`CapabilityBoundingSet` — systemd-hardening
reference) instead, which stays scoped to that process tree and is
visible in the unit file rather than a separate wrapper declaration.

```nix module
{
  security.wrappers.example = {
    owner = "root";
    group = "root";
    capabilities = "cap_net_bind_service+ep";
    source = "/nix/store/xxxxx-example/bin/example";
  };
}
```

## `users.users`: uids/groups, `DynamicUser` vs fixed

`users.users.<name>.uid`/`users.groups.<name>.gid` left
`null` get a free id picked on activation — stable across switches
(ids are recorded, not recomputed each time) but **not guaranteed
identical** across a from-scratch install versus an incremental one; pin
a fixed uid/gid for anything another config (a bind mount owner, a
`DeviceAllow` by uid) depends on by number. `isSystemUser = true`
only changes which id range a `null` uid is picked from — it does not by
itself lock the account down; a systemd service should prefer
`serviceConfig.DynamicUser = true` (systemd-hardening reference) over a
declared system user whenever nothing else on the machine needs a stable
uid to point at that service's files.

## Secrets never in the store

Anything written through the module system into `config` (a string, a
path assigned via `environment.etc.*.text`, a `writeText`) ends up in
`/nix/store`, world-readable and copied into every closure that
references it — including this repo's own doc-tests' derivations, which
is exactly why they are built with placeholders only. A real secret
needs an out-of-store mechanism (a file the module reads by path at
_activation_ time, never at eval time — `LoadCredential=`,
`EnvironmentFile=` pointing outside the store) — none of which this pin
skill demonstrates further; that mechanism is a per-project decision,
not a general NixOS idiom.

## `security.pam.services`

`nixos/modules/security/pam.nix` (2000+ lines) generates every PAM
service file from `security.pam.services`. Pointer only: read
that module's own option descriptions before touching PAM directly —
its size and the security blast radius of a wrong PAM stack are both too
large for a summary here to be safe.

## Sources

- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (firewall, polkit options)
- `nixos/modules/services/networking/firewall-nftables.nix` (the
  rpfilter/prerouting chain, the input chain, the iptables-only
  assertion on `extraCommands`; `extraInputRules` declared at line 26,
  gated by that file's own `mkIf (cfg.enable && config.networking.nftables.enable)`
  at line 65)
- `nixos/modules/services/networking/nftables.nix`
  (`networking.nftables.enable` default; `mkIf cfg.enable` gates its own
  ruleset-building `config` block)
- `nixos/modules/security/polkit.nix` (`extraConfig` as raw JS, the
  duktape engine)
- upstream `polkit`, `src/polkitbackend/polkitbackendduktapeauthority.c`
  at the `126` tag (this pin's version): `duk_peval_lstring` only
  compiles/registers rules (its own error is "Error compiling script
  ...", a syntax error, not this case); `duk_pcall_prop` — invoked once
  per authorization check — is what throws and logs "Error evaluating
  admin rules: %s" through `polkit_backend_authority_log`, which
  `syslog()`s the message (in `src/polkitbackend/polkitbackendauthority.c`)
- `nixos/modules/security/wrappers/default.nix` (the musl static
  wrapper, `unsecvars`)
- `nixos/modules/security/pam.nix` (pointer only — not read in depth)
