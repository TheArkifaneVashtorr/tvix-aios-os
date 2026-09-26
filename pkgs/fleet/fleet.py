#!/usr/bin/env python3
"""fleet -- deploy, enroll, keys and join-script over the declared list.

The one declared list is hosts/fleet.json (the same shape nixosModules/
fleet.nix declares as options.fleet): every command reads and validates it
first and refuses (exit 2) naming the field on any violation. Deploy and
enroll speak one SSH shape (Interface 2) whose only trust root is the
declaration -- never the user's or the system's known_hosts.

Exit codes (shared with FL6 and FL8): 0 done; 2 refused before any
connection; 3 refused at the host; 4 a step failed after the connection;
5 the post-switch confirmation failed. Every refusal is one line on stderr
beginning "fleet: "; progress lines on stdout begin "fleet: <step>: ".
"""

import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEPLOY_ROLES = ("forge",)
ROLES = ("operator", "forge")

NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
HOST_KEY_RE = re.compile(r"^ssh-ed25519 [A-Za-z0-9+/]+=*$")
DEPLOY_KEY_RE = re.compile(
    r"^(sk-ssh-ed25519@openssh\.com|ssh-ed25519) [A-Za-z0-9+/]+=* [^ ]+$"
)
STATE_VERSION_RE = re.compile(r"^[0-9]{2}\.[0-9]{2}$")
DECIMAL_RE = re.compile(r"^[0-9]+$")
CIDR_RE = re.compile(r"^([^/]+)/(3[0-2]|[0-2]?[0-9])$")

GENERATOR = "sudo -n /run/current-system/sw/bin/nixos-generate-config"
STATEVERSION_GREP = (
    "grep -o 'system.stateVersion = \"[0-9.]*\"' /etc/nixos/configuration.nix"
)


class Refused(Exception):
    """One refusal line plus its exit code (2-5)."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def refuse(code, message):
    raise Refused(code, message)


class SshRefused(Exception):
    """ssh itself failed (exit 255); the last stderr line is carried."""


# -- the declaration ---------------------------------------------------------


def is_ipv4(address):
    parts = address.split(".")
    return len(parts) == 4 and all(
        DECIMAL_RE.match(p) is not None and int(p) <= 255 for p in parts
    )


def is_cidr(cidr):
    match = CIDR_RE.match(cidr)
    return match is not None and is_ipv4(match.group(1))


def ip_to_int(address):
    value = 0
    for part in address.split("."):
        value = value * 256 + int(part)
    return value


def int_to_ip(value):
    return ".".join(str((value >> shift) & 255) for shift in (24, 16, 8, 0))


def in_subnet(address, cidr):
    network, plen = cidr.split("/")
    mask = (0xFFFFFFFF << (32 - int(plen))) & 0xFFFFFFFF
    return (ip_to_int(address) & mask) == (ip_to_int(network) & mask)


def network_address(address, prefix):
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return f"{int_to_ip(ip_to_int(address) & mask)}/{prefix}"


def accepts_deploys(machine):
    return any(role in DEPLOY_ROLES for role in machine.get("roles", []))


def validate(data):
    where = "hosts/fleet.json"
    if not isinstance(data, dict):
        refuse(2, f"{where}: the declaration must be one JSON object")
    machines = data.get("machines")
    if not isinstance(machines, dict):
        refuse(2, f"{where}: machines must be an object of machine entries")
    deploy_keys = data.get("deployKeys", [])
    if not isinstance(deploy_keys, list) or not all(
        isinstance(k, str) for k in deploy_keys
    ):
        refuse(2, f"{where}: deployKeys must be a list of strings")
    for i, key in enumerate(deploy_keys):
        if DEPLOY_KEY_RE.match(key) is None:
            refuse(
                2,
                f"{where}: deployKeys[{i}]: must be '<type> <base64> <comment>'"
                " with type one of sk-ssh-ed25519@openssh.com, ssh-ed25519",
            )
    any_deploys = False
    for name, machine in machines.items():
        if not isinstance(machine, dict):
            refuse(2, f"{where}: {name} must be an object")
        roles = machine.get("roles")
        if (
            not isinstance(roles, list)
            or not roles
            or not all(isinstance(r, str) for r in roles)
        ):
            refuse(2, f"{where}: {name}.roles: must be a non-empty list of roles")
        for role in roles:
            if role not in ROLES:
                refuse(
                    2, f"{where}: {name}.roles: {role} is not one of operator, forge"
                )
        if accepts_deploys(machine):
            if "operator" in roles:
                refuse(
                    2,
                    f"{where}: {name}.roles: never both operator and a"
                    " deploy-accepting role",
                )
            any_deploys = True
            address = machine.get("address")
            if not isinstance(address, str) or not is_ipv4(address):
                refuse(
                    2,
                    f"{where}: {name}.address: must be an IPv4 dotted quad"
                    " (four decimal parts 0-255)",
                )
            prefix = machine.get("prefix")
            if not isinstance(prefix, int) or isinstance(prefix, bool):
                refuse(2, f"{where}: {name}.prefix: must be an integer 8-30")
            if not 8 <= prefix <= 30:
                refuse(2, f"{where}: {name}.prefix: must be an integer 8-30")
            interface = machine.get("interface")
            if not isinstance(interface, str) or not interface:
                refuse(2, f"{where}: {name}.interface: must be a string")
            host_key = machine.get("hostKey")
            if not isinstance(host_key, str) or HOST_KEY_RE.match(host_key) is None:
                refuse(
                    2,
                    f"{where}: {name}.hostKey: must be 'ssh-ed25519 <base64>'"
                    " with no comment",
                )
            state_version = machine.get("stateVersion")
            if (
                not isinstance(state_version, str)
                or STATE_VERSION_RE.match(state_version) is None
            ):
                refuse(
                    2,
                    f"{where}: {name}.stateVersion: must be a NixOS stateVersion"
                    " in YY.MM form",
                )
        else:
            for field in (
                "address",
                "prefix",
                "interface",
                "hostKey",
                "efi",
                "stateVersion",
            ):
                if machine.get(field) is not None:
                    refuse(
                        2,
                        f"{where}: {name}.{field}: an operator machine has no"
                        " address and no host key",
                    )
    lan = data.get("lan")
    if lan is not None:
        if not isinstance(lan, dict):
            refuse(2, f"{where}: lan must be an object")
        subnet = lan.get("subnet")
        if not isinstance(subnet, str) or not is_cidr(subnet):
            refuse(2, f"{where}: lan.subnet: must be an IPv4 subnet in CIDR form")
        gateway = lan.get("gateway")
        if not isinstance(gateway, str) or not is_ipv4(gateway):
            refuse(2, f"{where}: lan.gateway: must be an IPv4 address")
        nameservers = lan.get("nameservers")
        if not isinstance(nameservers, list) or not all(
            isinstance(n, str) and is_ipv4(n) for n in nameservers
        ):
            refuse(2, f"{where}: lan.nameservers: must be a list of IPv4 addresses")
    if any_deploys:
        if not deploy_keys:
            refuse(
                2,
                f"{where}: deployKeys must not be empty when a machine accepts deploys",
            )
        if lan is None:
            refuse(
                2,
                f"{where}: lan must be declared when a machine accepts deploys",
            )
        for name, machine in machines.items():
            if accepts_deploys(machine):
                subnet = lan["subnet"]
                if not in_subnet(machine["address"], subnet):
                    refuse(
                        2,
                        f"{where}: {name}.address {machine['address']} lies outside"
                        f" lan.subnet {subnet}",
                    )


def load_declaration(repo):
    path = repo / "hosts" / "fleet.json"
    if not path.is_file():
        refuse(2, f"{repo} is not a checkout with hosts/fleet.json")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        refuse(2, f"hosts/fleet.json: not valid JSON ({exc})")
    validate(data)
    return data


def write_json(repo, data):
    """The one canonical writer: indent 2, sorted keys, one newline."""
    path = repo / "hosts" / "fleet.json"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".fleet.json.")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def write_pins(repo):
    """hosts/hardware-pins.sha256, regenerated from every host's hardware
    file, sorted by path, in sha256sum's '<hex>  <path>' format."""
    lines = []
    for path in sorted((repo / "hosts").glob("*/hardware-configuration.nix")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(repo)}")
    (repo / "hosts" / "hardware-pins.sha256").write_text("\n".join(lines) + "\n")


# -- the one SSH shape -------------------------------------------------------


class Ssh:
    """One connection: a private tmp dir, a known_hosts of exactly one line
    (the declaration's key in deploy, the scanned key in enroll), the pinned
    option list, and NIX_SSHOPTS for nix copy. Closed with `ssh -O exit` and
    removed at process exit, whatever way the command ends."""

    def __init__(self, name, address, host_key, identity):
        self.name = name
        self.address = address
        self.tmp = Path(tempfile.mkdtemp(prefix="fleet-"))
        self.known_hosts = self.tmp / "known_hosts"
        self.known_hosts.write_text(f"{name},{address} {host_key}\n")
        self.base = [
            "ssh",
            "-i",
            str(identity),
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            f"UserKnownHostsFile={self.known_hosts}",
            "-o",
            "GlobalKnownHostsFile=/dev/null",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "ControlMaster=auto",
            "-o",
            f"ControlPath={self.tmp}/cm-%C",
            "-o",
            "ControlPersist=120",
            f"deploy@{address}",
        ]
        self.sshopts = " ".join(self.base[1:-1])
        self.closed = False
        self.ever_ran = False
        atexit.register(self.cleanup)

    def run(self, command):
        self.ever_ran = True
        proc = subprocess.run(
            self.base + ["--", command],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 255:
            lines = proc.stderr.strip().splitlines()
            raise SshRefused(lines[-1] if lines else "ssh failed")
        if proc.returncode != 0:
            return None
        return proc.stdout

    def close(self):
        if not self.closed and self.ever_ran:
            self.closed = True
            subprocess.run(
                self.base + ["-O", "exit"],
                capture_output=True,
                text=True,
                check=False,
            )

    def cleanup(self):
        self.close()
        shutil.rmtree(self.tmp, ignore_errors=True)


def must_run(ssh, command):
    """run(), with a refusal at the host (exit 3) if ssh itself failed."""
    try:
        return ssh.run(command)
    except SshRefused as exc:
        refuse(3, f"refused: {exc}")


def identity_file(value):
    path = Path(value).expanduser()
    if not path.is_file():
        refuse(2, f"identity {value} is missing; create it per docs/runbooks/fleet.md")
    return path


# -- keys add ----------------------------------------------------------------


def cmd_keys_add(repo, args):
    decl = load_declaration(repo)
    keyfile = Path(args.pubkey_file)
    try:
        line = keyfile.read_text().strip()
    except OSError:
        refuse(2, f"keys: cannot read {args.pubkey_file}")
    if DEPLOY_KEY_RE.match(line) is None:
        refuse(
            2,
            f"keys: {args.pubkey_file} is not a deploy key '<type> <base64> <comment>'",
        )
    fields = line.split()
    comment = fields[2]
    keys = decl.setdefault("deployKeys", [])
    if any(" ".join(k.split()[:2]) == " ".join(fields[:2]) for k in keys):
        print(f"fleet: keys: already declared {comment}")
        return
    keys.append(line)
    write_json(repo, decl)
    print(f"fleet: keys: added {comment}")


# -- join-script -------------------------------------------------------------


def cmd_join_script(repo, args):
    decl = load_declaration(repo)
    keys = decl.get("deployKeys") or []
    if not keys:
        refuse(2, "join-script: no deployKeys declared; run fleet keys add first")
    template = Path(__file__).with_name("fleet-join.nix").read_text()
    keys_literal = "[ " + " ".join(json.dumps(k) for k in keys) + " ]"
    rendered = template.replace("@DEPLOY_KEYS@", keys_literal).replace(
        "@PARENT_IMPORTS@", "./configuration.nix"
    )
    sys.stdout.write(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "[ \"$(id -u)\" = 0 ] || { echo 'fleet-join: run with sudo' >&2; exit 2; }\n"
        "cat >/etc/nixos/fleet-join.nix <<'FLEET_JOIN_EOF'\n"
        + rendered
        + "FLEET_JOIN_EOF\n"
        "nixos-rebuild switch -I nixos-config=/etc/nixos/fleet-join.nix\n"
        "printf 'fleet-join: host key %s\\n' "
        '"$(ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub'
        " | awk '{print $2}')\"\n"
        "printf 'fleet-join: address %s\\n' "
        '"$(ip -o -4 addr show scope global'
        ' | awk \'{print $4 " on " $2; exit}\')"\n'
    )


# -- enroll ------------------------------------------------------------------


def cmd_enroll(repo, args):
    decl = load_declaration(repo)
    name = args.name
    address = args.address
    if NAME_RE.match(name) is None:
        refuse(2, f"enroll: {name} is not a machine name (^[a-z][a-z0-9-]*$)")
    if not is_ipv4(address):
        refuse(2, f"enroll: {address} is not an IPv4 address")
    if args.role not in DEPLOY_ROLES:
        refuse(2, f"enroll: --role {args.role} is not a deploy-accepting role")
    state_version = args.state_version
    if state_version is not None and STATE_VERSION_RE.match(state_version) is None:
        refuse(
            2,
            f"enroll: --state-version {state_version} must be a NixOS stateVersion"
            " in YY.MM form",
        )
    identity = identity_file(args.identity)
    lan = decl.get("lan")
    if lan is not None and not in_subnet(address, lan["subnet"]):
        refuse(
            2,
            f"enroll: {address} is outside the declared lan.subnet {lan['subnet']}",
        )
    print(f"fleet: enroll: scan: ssh-keyscan -t ed25519 -T 5 {address}")
    proc = subprocess.run(
        ["ssh-keyscan", "-t", "ed25519", "-T", "5", address],
        capture_output=True,
        text=True,
        check=False,
    )
    scanned_lines = [
        line for line in proc.stdout.splitlines() if line and not line.startswith("#")
    ]
    ed_lines = [
        line
        for line in scanned_lines
        if line.split()[:2] == [address, "ssh-ed25519"] and len(line.split()) == 3
    ]
    if not ed_lines:
        refuse(3, f"enroll: no ed25519 host key from {address}")
    scanned = ed_lines[0]
    fields = scanned.split()
    host_key = f"{fields[1]} {fields[2]}"
    ssh = Ssh(name, address, host_key, identity)
    scanned_file = ssh.tmp / "scanned"
    scanned_file.write_text(scanned + "\n")
    fp_proc = subprocess.run(
        ["ssh-keygen", "-lf", str(scanned_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    fp_tokens = [t for t in fp_proc.stdout.split() if t.startswith("SHA256:")]
    if not fp_tokens:
        refuse(3, f"enroll: no fingerprint from ssh-keygen for {address}")
    scanned_fingerprint = fp_tokens[0]
    expected = args.fingerprint
    if expected is None:
        if not sys.stdin.isatty():
            refuse(2, "enroll: --fingerprint is required when stdin is not a terminal")
        expected = input("fingerprint (SHA256:...): ")
    if not expected.startswith("SHA256:"):
        expected = "SHA256:" + expected
    if scanned_fingerprint != expected:
        refuse(
            3,
            f"refused: host key fingerprint {scanned_fingerprint} does not match"
            f" {expected}",
        )
    print(f"fleet: enroll: hardware: {GENERATOR} --show-hardware-config")
    hardware = must_run(ssh, f"{GENERATOR} --show-hardware-config")
    if hardware is None or not hardware.startswith("# Do not modify this file!"):
        refuse(
            4,
            f"enroll: the hardware config from {address} does not start with the"
            " generator header",
        )
    print(f"fleet: enroll: interface: ip -o -4 addr show to {address}/32")
    ip_out = must_run(ssh, f"ip -o -4 addr show to {address}/32")
    iface_fields = None
    for line in (ip_out or "").splitlines():
        parts = line.split()
        if len(parts) >= 4 and "/" in parts[3]:
            iface_fields = parts
            break
    if iface_fields is None:
        refuse(
            4,
            f"enroll: {address} is not configured on any interface of the machine",
        )
    interface = iface_fields[1]
    prefix = int(iface_fields[3].split("/")[1])
    print("fleet: enroll: gateway: ip -4 route show default")
    route_out = must_run(ssh, "ip -4 route show default")
    gateway = None
    for line in (route_out or "").splitlines():
        parts = line.split()
        if parts[:2] == ["default", "via"]:
            gateway = parts[2]
            break
    if gateway is None:
        refuse(4, f"enroll: no default route on {address}")
    print("fleet: enroll: nameservers: cat /etc/resolv.conf")
    resolv = must_run(ssh, "cat /etc/resolv.conf")
    nameservers = [
        line.split()[1]
        for line in (resolv or "").splitlines()
        if line.split()[:1] == ["nameserver"]
    ]
    if not nameservers:
        refuse(4, f"enroll: no nameserver in /etc/resolv.conf on {address}")
    print("fleet: enroll: firmware: test -d /sys/firmware/efi && echo efi || echo bios")
    firmware = must_run(ssh, "test -d /sys/firmware/efi && echo efi || echo bios")
    efi = (firmware or "").strip() == "efi"
    if state_version is None:
        print(f"fleet: enroll: stateVersion: {STATEVERSION_GREP}")
        grep_out = must_run(ssh, STATEVERSION_GREP)
        match = re.search(r'system.stateVersion = "([0-9.]*)"', grep_out or "")
        if match is None or STATE_VERSION_RE.match(match.group(1)) is None:
            refuse(
                4,
                f"enroll: cannot read system.stateVersion from"
                f" /etc/nixos/configuration.nix on {address}; pass"
                " --state-version",
            )
        state_version = match.group(1)
    hw_path = repo / "hosts" / name / "hardware-configuration.nix"
    print(f"fleet: enroll: write: {hw_path}")
    hw_path.parent.mkdir(parents=True, exist_ok=True)
    hw_path.write_text(hardware)
    machines = decl.setdefault("machines", {})
    if name in machines:
        entry = {"roles": machines[name].get("roles", [args.role])}
    else:
        entry = {"roles": [args.role]}
    entry.update(
        {
            "address": address,
            "prefix": prefix,
            "interface": interface,
            "hostKey": host_key,
            "efi": efi,
            "stateVersion": state_version,
        }
    )
    machines[name] = entry
    if decl.get("lan") is None:
        decl["lan"] = {
            "subnet": network_address(address, prefix),
            "gateway": gateway,
            "nameservers": nameservers,
        }
    write_json(repo, decl)
    write_pins(repo)
    ssh.close()
    print(
        f"fleet: enrolled {name} at {address} ({interface}/{prefix},"
        f" efi={str(efi).lower()}, stateVersion={state_version})"
    )
    print(
        f"fleet: commit: git add hosts/{name} hosts/fleet.json"
        " hosts/hardware-pins.sha256"
    )


# -- deploy ------------------------------------------------------------------


def cmd_deploy(repo, args):
    decl = load_declaration(repo)
    machines = decl["machines"]
    name = args.name
    machine = machines.get(name)
    if machine is None or not accepts_deploys(machine):
        refuse(2, f"deploy: {name} is not declared with a deploy-accepting role")
    hw = repo / "hosts" / name / "hardware-configuration.nix"
    if not hw.is_file() or hw.read_text().startswith("# PLACEHOLDER"):
        refuse(
            2,
            f"deploy: {name} is not enrolled (hosts/{name}/"
            "hardware-configuration.nix is the placeholder)",
        )
    identity = identity_file(args.identity)
    address = machine["address"]
    if args.toplevel:
        new = args.toplevel
        if not (Path(new) / "bin" / "switch-to-configuration").exists():
            refuse(2, f"deploy: {new} is not a NixOS system")
    else:
        attr = f"nixosConfigurations.{name}.config.system.build.toplevel"
        print(
            f"fleet: deploy: build: nix build {repo}#{attr} --no-link --print-out-paths"
        )
        proc = subprocess.run(
            ["nix", "build", f"{repo}#{attr}", "--no-link", "--print-out-paths"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            refuse(4, "deploy: build failed")
        new = proc.stdout.strip().splitlines()[0]
    ssh = Ssh(name, address, machine["hostKey"], identity)
    print(f"fleet: deploy: connect: deploy@{address}")
    previous = must_run(ssh, "readlink -f /run/current-system")
    if previous is None:
        refuse(3, f"refused: {name} did not answer readlink")
    previous = previous.strip()
    print(f"fleet: deploy: previous: {previous}")
    if (
        subprocess.run(
            ["nix", "path-info", previous],
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    ):
        print(f"fleet: deploy: diff-closures: nix store diff-closures {previous} {new}")
        diff = subprocess.run(
            ["nix", "store", "diff-closures", previous, new],
            capture_output=True,
            text=True,
            check=False,
        )
        if diff.returncode == 0:
            sys.stdout.write(diff.stdout)
    else:
        print(
            f"fleet: deploy: diff-closures: the machine's current system"
            f" {previous} is not in the local store; skipped"
        )
    print(
        f"fleet: deploy: copy: nix copy --no-check-sigs --to ssh-ng://deploy@{address} {new}"
    )
    env = dict(os.environ, NIX_SSHOPTS=ssh.sshopts)
    if (
        subprocess.run(
            [
                "nix",
                "copy",
                "--no-check-sigs",
                "--to",
                f"ssh-ng://deploy@{address}",
                new,
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        ).returncode
        != 0
    ):
        refuse(4, "deploy: copy failed")
    print(
        f"fleet: deploy: profile: nix-env --profile /nix/var/nix/profiles/system --set {new}"
    )
    if (
        must_run(
            ssh,
            "sudo -n /run/current-system/sw/bin/nix-env"
            " --profile /nix/var/nix/profiles/system"
            f" --set {new}",
        )
        is None
    ):
        refuse(4, "deploy: profile failed")
    print(f"fleet: deploy: switch: {new}/bin/switch-to-configuration switch")
    if must_run(ssh, f"sudo -n {new}/bin/switch-to-configuration switch") is None:
        refuse(4, "deploy: switch failed")
    print("fleet: deploy: confirm: readlink -f /run/current-system")
    try:
        current = ssh.run("readlink -f /run/current-system")
    except SshRefused:
        refuse(5, f"deploy: {name} did not answer after the switch")
    if current is None or current.strip() != new:
        got = current.strip() if current else "<no answer>"
        refuse(
            5,
            f"deploy: {name} answers but /run/current-system is {got}, not {new}",
        )
    ssh.close()
    print(f"fleet: deployed {name} {new}")
    print(f"fleet: previous: {previous}")


# -- main --------------------------------------------------------------------


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="fleet",
        description="deploy, enroll, keys and join-script over the declared list"
        " (hosts/fleet.json)",
    )
    parser.add_argument(
        "--repo", default=".", help="the checkout holding hosts/fleet.json"
    )
    keys = parser.add_subparsers(dest="command", required=True)
    keys_parser = keys.add_parser("keys", help="manage the deploy keys")
    keys_sub = keys_parser.add_subparsers(dest="keys_command", required=True)
    add = keys_sub.add_parser("add", help="append a deploy key to the declaration")
    add.add_argument("pubkey_file", help="a file holding one public key line")
    keys.add_parser("join-script", help="print the console bootstrap script")
    enroll = keys.add_parser(
        "enroll", help="fetch a machine's facts and add it to the declaration"
    )
    enroll.add_argument("name")
    enroll.add_argument("address")
    enroll.add_argument("--fingerprint")
    enroll.add_argument("--role", default="forge")
    enroll.add_argument("--identity", default="~/.ssh/fleet-deploy")
    enroll.add_argument("--state-version")
    deploy = keys.add_parser("deploy", help="build, copy and switch a machine")
    deploy.add_argument("name")
    deploy.add_argument("--toplevel")
    deploy.add_argument("--identity", default="~/.ssh/fleet-deploy")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    repo = Path(args.repo)
    if args.command == "keys" and args.keys_command == "add":
        cmd_keys_add(repo, args)
    elif args.command == "join-script":
        cmd_join_script(repo, args)
    elif args.command == "enroll":
        cmd_enroll(repo, args)
    elif args.command == "deploy":
        cmd_deploy(repo, args)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Refused as refused:
        print(f"fleet: {refused.message}", file=sys.stderr)
        sys.exit(refused.code)
