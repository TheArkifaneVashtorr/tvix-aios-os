"""comfy-upstream-probe: the deterministic weekly proposal.

Reads the ComfyUI pin from `pkgs/comfyui/package.nix` plus a closed table of
watched wheel files, reads the newest upstream tag's `requirements.txt` (never
PyPI latest for those), reads the NVIDIA production branch row, and — in dry
run — prints one line per component; otherwise clones a throwaway workspace,
rewrites the version/rev/hash literals, re-derives each hash, commits, runs
`nix flake check -L`, records one `proposals` heartbeat/row per run via the
`evidence` CLI, and writes a report + (on red) a brief.

Stdlib only: the unit runs under bare `pkgs.python3`.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

# PyPI distribution name -> deps file. "Current" for these is the version the
# newest ComfyUI tag's requirements.txt pins (never PyPI latest).
DEPS = {
    "comfyui-frontend-package": "pkgs/comfyui/deps/comfyui-frontend-package.nix",
    "comfyui-workflow-templates": "pkgs/comfyui/deps/comfyui-workflow-templates.nix",
    "comfyui-embedded-docs": "pkgs/comfyui/deps/comfyui-embedded-docs.nix",
    "comfy-kitchen": "pkgs/comfyui/deps/comfy-kitchen.nix",
    "comfy-aimdo": "pkgs/comfyui/deps/comfy-aimdo.nix",
    "comfy-angle": "pkgs/comfyui/deps/comfy-angle.nix",
}

# The seven data wheels follow comfyui-workflow-templates' own Requires-Dist
# (PyPI JSON info.requires_dist of the parent at its target version). One entry
# per sibling file present under deps/ (read once, at W5 time).
TEMPLATE_PARTS = {
    "comfyui-workflow-templates-core": "pkgs/comfyui/deps/comfyui-workflow-templates-core.nix",
    "comfyui-workflow-templates-json": "pkgs/comfyui/deps/comfyui-workflow-templates-json.nix",
    "comfyui-workflow-templates-media-api": "pkgs/comfyui/deps/comfyui-workflow-templates-media-api.nix",
    "comfyui-workflow-templates-media-video": "pkgs/comfyui/deps/comfyui-workflow-templates-media-video.nix",
    "comfyui-workflow-templates-media-image": "pkgs/comfyui/deps/comfyui-workflow-templates-media-image.nix",
    "comfyui-workflow-templates-media-other": "pkgs/comfyui/deps/comfyui-workflow-templates-media-other.nix",
    "comfyui-workflow-templates-media-assets-01": "pkgs/comfyui/deps/comfyui-workflow-templates-media-assets-01.nix",
}

# Deliberately NOT watched: av (pinned against the flake's own FFmpeg build),
# spandrel, cython-for-av, ffmpeg-8-headless.

COMFYUI_FILE = "pkgs/comfyui/package.nix"

GITHUB_TAGS_URL = "https://api.github.com/repos/Comfy-Org/ComfyUI/tags?per_page=20"
RAW_REQ_TMPL = (
    "https://raw.githubusercontent.com/Comfy-Org/ComfyUI/{tag}/requirements.txt"
)
PYPI_LATEST_TMPL = "https://pypi.org/pypi/{dist}/json"
PYPI_VERSION_TMPL = "https://pypi.org/pypi/{dist}/{version}/json"
NVIDIA_URL = "https://www.nvidia.com/en-us/drivers/unix/"

USER_AGENT = "comfy-upstream-probe"

DRIVER_HASH_KEYS = (
    "sha256_64bit",
    "openSha256",
    "settingsSha256",
    "persistencedSha256",
)

_V_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_VERSION_RE = re.compile(r'version = "([^"]+)"')
_REV_RE = re.compile(r'rev = "([0-9a-f]+)"')
_HASH_RE = re.compile(r'hash = "sha256-[A-Za-z0-9+/=]+"')
_REQ_PIN_RE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*==\s*([^\s;#]+)", re.MULTILINE)
_PRODUCTION_RE = re.compile(
    r"Latest Production Branch Version:</span>\s*<a[^>]*>([0-9.]+)</a>"
)
_CHECK_NAME_RE = re.compile(
    r"^checking derivation checks\.[A-Za-z0-9_-]+\.([A-Za-z0-9_-]+)\.\.\.\s*$",
    re.MULTILINE,
)
# The store path is /nix/store/<32-char base32 hash>-<name>.drv; capture only
# the <name> after the hash prefix so the check name (not the hash) is matched.
_BUILDER_FAIL_RE = re.compile(
    r"error: builder for '[^']*/[A-Za-z0-9]{32}-([A-Za-z0-9_-]+)\.drv' failed"
)
_ATTR_RE = re.compile(r'^\s*([a-z]+)\s*=\s*"([^"]+)";\s*$', re.MULTILINE)


def _open(url):
    """Open `url` through the broker's HTTPS proxy, refusing direct egress.

    The proxy and CA come from the unit's Environment (invariant 3: the probe's
    egress crosses the egress broker, never the host's default route). A missing
    or unreadable pair is a hard refusal raised before any socket is opened —
    there is deliberately no fallback to the system trust store.
    """
    proxy = os.environ.get("HTTPS_PROXY")
    ca_file = os.environ.get("SSL_CERT_FILE")
    if not proxy or not ca_file:
        raise RuntimeError(
            "comfy-upstream-probe: refusing direct egress — HTTPS_PROXY and SSL_CERT_FILE must name the broker (invariant 3)"
        )
    if not os.access(ca_file, os.R_OK):
        raise RuntimeError(
            "comfy-upstream-probe: SSL_CERT_FILE %s is not a readable CA bundle"
            % ca_file
        )
    try:
        context = ssl.create_default_context(cafile=ca_file)
    except (OSError, ssl.SSLError):
        raise RuntimeError(
            "comfy-upstream-probe: SSL_CERT_FILE %s is not a readable CA bundle"
            % ca_file
        )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"https": proxy}),
        urllib.request.HTTPSHandler(context=context),
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def fetch_json(url):
    """Return the parsed JSON object at `url` (seam for tests)."""
    return json.loads(_open(url))


def fetch_text(url):
    """Return the decoded text at `url` (seam for tests)."""
    return _open(url)


def run(argv, cwd=None, check=False):
    """Run `argv`, returning a CompletedProcess (seam for tests)."""
    return subprocess.run(argv, cwd=cwd, check=check, capture_output=True, text=True)


def _name_to_file(name):
    if name == "comfyui":
        return COMFYUI_FILE
    if name in DEPS:
        return DEPS[name]
    if name in TEMPLATE_PARTS:
        return TEMPLATE_PARTS[name]
    raise KeyError("not a watched pin: %s" % name)


def _version_of(text):
    m = _VERSION_RE.search(text)
    if m is None:
        raise ValueError("no version literal found")
    return m.group(1)


def read_pins(repo):
    """Return {comfyui: {version, rev}, <dist>: {version}} from the closed table."""
    repo = pathlib.Path(repo)
    pkg = (repo / COMFYUI_FILE).read_text()
    rev_m = _REV_RE.search(pkg)
    if rev_m is None:
        raise ValueError("no rev literal found in package.nix")
    pins = {"comfyui": {"version": _version_of(pkg), "rev": rev_m.group(1)}}
    for name, rel in {**DEPS, **TEMPLATE_PARTS}.items():
        pins[name] = {"version": _version_of((repo / rel).read_text())}
    return pins


def rewrite_pins(repo, pins):
    """Rewrite the version/rev/hash literals named in `pins`, nothing else."""
    repo = pathlib.Path(repo)
    for name, fields in pins.items():
        path = repo / _name_to_file(name)
        text = path.read_text()
        for key, value in fields.items():
            if key == "version":
                text = _VERSION_RE.sub('version = "%s"' % value, text, count=1)
            elif key == "rev":
                text = _REV_RE.sub('rev = "%s"' % value, text, count=1)
            elif key == "hash":
                text = _HASH_RE.sub('hash = "%s"' % value, text, count=1)
        path.write_text(text)


def newest_comfyui_tag(tags):
    """Return (tag_name, commit_sha) of the newest strict vX.Y.Z tag."""
    candidates = []
    for tag in tags:
        m = _V_TAG_RE.match(tag.get("name", ""))
        if m:
            candidates.append((tuple(int(x) for x in m.groups()), tag))
    if not candidates:
        raise ValueError("no vX.Y.Z tag found")
    candidates.sort(key=lambda kv: kv[0], reverse=True)
    best = candidates[0][1]
    return best["name"], best["commit"]["sha"]


def parse_requirements_pins(text):
    """Map every `name==version` line in a requirements.txt to its pin."""
    return {m.group(1): m.group(2) for m in _REQ_PIN_RE.finditer(text)}


def parse_production_driver(page):
    """Return the version in the first `Latest Production Branch Version:` row."""
    m = _PRODUCTION_RE.search(page)
    if m is None:
        raise ValueError("no Latest Production Branch Version row found")
    return m.group(1)


def parse_check_log(text):
    """Return {check_name: bool} from a `nix flake check -L` log."""
    names = _CHECK_NAME_RE.findall(text)
    failed = set(_BUILDER_FAIL_RE.findall(text))
    return {name: not (name in failed or (name + "-ok") in failed) for name in names}


def render_report(date, bumps, verdicts, workspace, branch):
    lines = ["# comfy-upstream-probe report — %s" % date, ""]
    lines.append("## bumps")
    if bumps:
        for name, (old, new) in bumps.items():
            lines.append("- %s: %s -> %s" % (name, old, new))
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## checks")
    for name in sorted(verdicts):
        lines.append("- %s: %s" % (name, "GREEN" if verdicts[name] else "RED"))
    lines.append("")
    lines.append("## accept")
    lines.append("```")
    lines.append("git -C ~/flakes/media merge --ff-only %s %s" % (workspace, branch))
    lines.append("```")
    return "\n".join(lines) + "\n"


def render_brief(date, verdicts, log_text):
    red = sorted(n for n, ok in verdicts.items() if not ok)
    lines = [
        "# comfy-upstream-probe brief — %s" % date,
        "",
        "Red checks; run as a bounded seat task M-refresh-%s from the proposal branch."
        % date,
    ]
    for name in red:
        lines.append("")
        lines.append("## %s" % name)
        lines.extend(ln for ln in log_text.splitlines() if name in ln)
    lines.append("")
    lines.append("Pins diff and proposal branch are in the full report.")
    return "\n".join(lines) + "\n"


def render_driver_stanza(version, hashes):
    for key in DRIVER_HASH_KEYS:
        if key not in hashes:
            raise ValueError("missing driver hash: %s" % key)
    lines = [
        "  hardware.nvidia.package = config.boot.kernelPackages.nvidiaPackages.mkDriver {",
        '    version = "%s";' % version,
        '    sha256_64bit = "%s";' % hashes["sha256_64bit"],
        '    openSha256 = "%s";' % hashes["openSha256"],
        '    settingsSha256 = "%s";' % hashes["settingsSha256"],
        '    persistencedSha256 = "%s";' % hashes["persistencedSha256"],
        "  };",
    ]
    return "\n".join(lines) + "\n"


def heartbeat_row(repo):
    return {
        "kind": "proposal",
        "repo": repo,
        "branch": None,
        "bumps": [],
        "checks_green": None,
    }


def record(store, rev, verdicts, proposal_row):
    """Record one proposals row + one record-check per check via `evidence`.

    Uses `evidence --store <store> …`; returns None, or the "not recorded"
    string when the CLI is absent (never fails on a missing CLI).
    """
    evidence = shutil.which("evidence")
    if evidence is None:
        return "not recorded (no evidence CLI on PATH)"
    cp = run(
        [
            evidence,
            "--store",
            store,
            "record",
            "proposals",
            "--json",
            json.dumps(proposal_row),
        ]
    )
    if cp.returncode != 0:
        print("evidence: proposals row rejected: %s" % (cp.stderr or cp.stdout).strip())
    for name in sorted(verdicts, key=lambda n: verdicts[n]):
        cp = run(
            [
                evidence,
                "--store",
                store,
                "record-check",
                "--name",
                name,
                "--rev",
                rev or "",
                "--ok" if verdicts[name] else "--fail",
                "--class",
                "nix-check",
                "--src",
                "comfy-refresh",
            ]
        )
        if cp.returncode != 0:
            print(
                "evidence: record-check %s rejected: %s"
                % (name, (cp.stderr or cp.stdout).strip())
            )
    return None


def _record_and_report(store, rev, verdicts, proposal_row):
    msg = record(store, rev, verdicts, proposal_row)
    if msg:
        print("evidence: %s" % msg)


def _fixture_fetchers(fixtures_dir):
    """Serve fetch_json/fetch_text from local fixture files (--fixtures)."""
    fixtures = pathlib.Path(fixtures_dir)

    def fj(url):
        if url == GITHUB_TAGS_URL:
            return json.loads((fixtures / "tags.json").read_text())
        m = re.match(r"https://pypi\.org/pypi/([^/]+)/([^/]+)/json", url)
        if m:
            return json.loads(
                (fixtures / ("%s-%s.json" % (m.group(1), m.group(2)))).read_text()
            )
        m = re.match(r"https://pypi\.org/pypi/([^/]+)/json", url)
        if m:
            return json.loads((fixtures / (m.group(1) + ".json")).read_text())
        raise ValueError("no fixture for %s" % url)

    def ft(url):
        if url.endswith("/requirements.txt"):
            tag = url.split("/")[-2]
            return (fixtures / ("requirements-%s.txt" % tag)).read_text()
        if url == NVIDIA_URL:
            return (fixtures / "nvidia-unix.html").read_text()
        raise ValueError("no fixture for %s" % url)

    return fj, ft


def _resolve_upstream(pins, fetch, fetch_text_fn):
    """Return (rows, comfyui_rev, driver); rows are (name, current, target)."""
    tag_name, rev = newest_comfyui_tag(fetch(GITHUB_TAGS_URL))
    version = tag_name[1:]
    req_pins = parse_requirements_pins(fetch_text_fn(RAW_REQ_TMPL.format(tag=tag_name)))

    templates_target = req_pins.get("comfyui-workflow-templates")
    if templates_target is None:
        templates_target = fetch(
            PYPI_LATEST_TMPL.format(dist="comfyui-workflow-templates")
        )["info"]["version"]
    requires = {}
    tj = fetch(
        PYPI_VERSION_TMPL.format(
            dist="comfyui-workflow-templates", version=templates_target
        )
    )
    for req in tj["info"].get("requires_dist") or []:
        name, sep, spec = req.partition("==")
        if name and sep:
            requires[name.strip()] = spec.split(";")[0].strip()

    rows = [("comfyui", pins["comfyui"]["version"], version)]
    for name in DEPS:
        target = req_pins.get(name)
        if target is None:
            target = fetch(PYPI_LATEST_TMPL.format(dist=name))["info"]["version"]
        rows.append((name, pins[name]["version"], target))
    for name in TEMPLATE_PARTS:
        if name not in requires:
            raise ValueError("parent Requires-Dist has no pin for %s" % name)
        rows.append((name, pins[name]["version"], requires[name]))

    driver = parse_production_driver(fetch_text_fn(NVIDIA_URL))
    return rows, rev, driver


def _sri_from_hex(hexdigest):
    cp = run(
        ["nix", "hash", "convert", "--hash-algo", "sha256", "--to", "sri", hexdigest]
    )
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout)
    return cp.stdout.strip()


def _prefetch(url, unpack=False):
    argv = ["nix-prefetch-url"]
    if unpack:
        argv.append("--unpack")
    argv.append(url)
    cp = run(argv)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout)
    return _sri_from_hex(cp.stdout.strip())


def _deps_attrs(text):
    out = {}
    for m in _ATTR_RE.finditer(text):
        if m.group(1) in ("python", "abi", "platform"):
            out[m.group(1)] = m.group(2)
    return out


def _derive_wheel_hash(dist, version, deps_text, fetch):
    """Return (sri, wheel_filename) for the wheel the deps file selects."""
    pj = fetch(PYPI_VERSION_TMPL.format(dist=dist, version=version))
    attrs = _deps_attrs(deps_text)
    platform = attrs.get("platform")
    python = attrs.get("python", "py3")
    abi = attrs.get("abi")
    for u in pj.get("urls", []):
        fn = u["filename"]
        if not fn.endswith(".whl"):
            continue
        if platform:
            if fn.endswith("-%s-%s-%s.whl" % (python, abi, platform)):
                return _sri_from_hex(u["digests"]["sha256"]), fn
        elif fn.endswith("-py3-none-any.whl"):
            return _sri_from_hex(u["digests"]["sha256"]), fn
    raise ValueError("no matching wheel for %s==%s" % (dist, version))


def _driver_hashes(version):
    base = "https://download.nvidia.com/XFree86/Linux-x86_64/%s" % version
    return {
        "sha256_64bit": _prefetch("%s/NVIDIA-Linux-x86_64-%s.run" % (base, version)),
        "openSha256": _prefetch(
            "https://github.com/NVIDIA/open-gpu-kernel-modules/archive/%s.tar.gz"
            % version,
            unpack=True,
        ),
        "settingsSha256": _prefetch(
            "https://github.com/NVIDIA/nvidia-settings/archive/%s.tar.gz" % version,
            unpack=True,
        ),
        "persistencedSha256": _prefetch(
            "https://github.com/NVIDIA/nvidia-persistenced/archive/%s.tar.gz" % version,
            unpack=True,
        ),
    }


def _proposal_row(repo, branch, bumps, checks_green, red_checks, workspace, driver):
    row = {
        "kind": "proposal",
        "repo": repo,
        "branch": branch,
        "bumps": [{"name": n, "from": o, "to": t} for n, (o, t) in bumps.items()],
        "checks_green": checks_green,
        "red_checks": red_checks,
        "workspace": workspace,
    }
    if driver is not None:
        row["driver"] = driver
    return row


def _reports_dir(args):
    d = pathlib.Path(args.reports).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _comfyui_rewrite(rows, comfyui_rev):
    old, new = rows[0][1], rows[0][2]
    if old == new:
        return {}
    return {
        "comfyui": {
            "version": new,
            "rev": comfyui_rev,
            "hash": _prefetch(
                "https://github.com/Comfy-Org/ComfyUI/archive/%s.tar.gz" % comfyui_rev,
                unpack=True,
            ),
        }
    }


def _propose(args, repo_name, repo, rows, comfyui_rev, driver, date):
    """Clone, rewrite, hash, commit, check, record, report. Returns exit code."""
    branch = "propose/comfyui-%s" % date
    parent = pathlib.Path(args.workspace).expanduser() / date
    parent.mkdir(parents=True, exist_ok=True)
    clone = parent / "media"
    if clone.exists():
        shutil.rmtree(clone)
    if run(["git", "clone", "-q", str(repo), str(clone)]).returncode != 0:
        return 2
    if run(["git", "-C", str(clone), "checkout", "-q", "-b", branch]).returncode != 0:
        return 2

    bumps = {n: (o, t) for n, o, t in rows if o != t}
    rewrite = _comfyui_rewrite(rows, comfyui_rev)
    for name, old, new in rows[1:]:
        if old == new:
            continue
        deps_text = (repo / _name_to_file(name)).read_text()
        sri, _ = _derive_wheel_hash(name, new, deps_text, fetch_json)
        rewrite[name] = {"version": new, "hash": sri}
    rewrite_pins(clone, rewrite)

    if run(["git", "-C", str(clone), "add", "-A"]).returncode != 0:
        return 2
    msg = "comfyui: propose %s" % ", ".join(
        "%s %s -> %s" % (n, o, t) for n, o, t in rows if o != t
    )
    if run(["git", "-C", str(clone), "commit", "-q", "-m", msg]).returncode != 0:
        return 2
    head = run(["git", "-C", str(clone), "rev-parse", "HEAD"]).stdout.strip()

    check_cp = run(["nix", "flake", "check", "-L"], cwd=str(clone))
    log = check_cp.stdout + check_cp.stderr
    verdicts = parse_check_log(log)
    checks_green = check_cp.returncode == 0

    reports = _reports_dir(args)
    (reports / ("%s.md" % date)).write_text(
        render_report(date, bumps, verdicts, str(clone), branch)
    )
    (reports / ("%s.full.log" % date)).write_text(log)
    if not checks_green:
        (reports / ("%s.brief.md" % date)).write_text(render_brief(date, verdicts, log))

    row = _proposal_row(
        repo_name,
        branch,
        bumps,
        checks_green,
        sorted(n for n, ok in verdicts.items() if not ok),
        str(clone),
        {"host": args.host_driver, "upstream": driver},
    )
    _record_and_report(args.evidence_store, head, verdicts, row)
    return 0 if checks_green else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="comfy-upstream-probe")
    parser.add_argument("--repo", default="~/flakes/media")
    parser.add_argument("--workspace", default="~/factory/ws/comfy-refresh")
    parser.add_argument("--reports", default="~/factory/runs/comfy-refresh")
    parser.add_argument("--evidence-store", default="/var/lib/evidence")
    parser.add_argument("--host-driver", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--date", default=None)
    parser.add_argument("--fixtures", default=None)
    args = parser.parse_args(argv)
    date = args.date or datetime.date.today().isoformat()
    repo = pathlib.Path(args.repo).expanduser()

    if args.fixtures:
        fetch_json_local, fetch_text_local = _fixture_fetchers(args.fixtures)
    else:
        fetch_json_local, fetch_text_local = fetch_json, fetch_text

    try:
        pins = read_pins(repo)
        rows, comfyui_rev, driver = _resolve_upstream(
            pins, fetch_json_local, fetch_text_local
        )
    except AssertionError:
        raise
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        print("comfy-upstream-probe: lookup failed: %s" % exc, file=sys.stderr)
        return 2

    if args.dry_run:
        for name, current, target in rows:
            if current == target:
                print("%s current" % name)
            else:
                print("%s %s -> %s" % (name, current, target))
        if args.host_driver:
            print(
                "nvidia-driver current"
                if args.host_driver == driver
                else "nvidia-driver %s -> %s" % (args.host_driver, driver)
            )
        else:
            print("nvidia-driver: host version unknown (pass --host-driver)")
        return 0

    repo_name = "media"
    bumps = {n: (o, t) for n, o, t in rows if o != t}
    reports = _reports_dir(args)

    if not bumps:
        if args.host_driver and args.host_driver != driver:
            hashes = _driver_hashes(driver)
            stanza = render_driver_stanza(driver, hashes)
            lines = [
                "# comfy-upstream-probe report — %s" % date,
                "",
                "No ComfyUI pin moved. NVIDIA driver bump:",
                "```nix",
                stanza.rstrip("\n"),
                "```",
            ]
            (reports / ("%s.md" % date)).write_text("\n".join(lines) + "\n")
            row = {
                "kind": "proposal",
                "repo": "nixos-agent-env",
                "branch": None,
                "bumps": [],
                "checks_green": None,
                "driver": {"host": args.host_driver, "upstream": driver},
            }
            _record_and_report(args.evidence_store, None, {}, row)
            return 0
        (reports / ("%s.md" % date)).write_text(
            "# comfy-upstream-probe report — %s\n\nNo ComfyUI pin moved; pins current.\n"
            % date
        )
        _record_and_report(args.evidence_store, None, {}, heartbeat_row(repo_name))
        return 0

    return _propose(args, repo_name, repo, rows, comfyui_rev, driver, date)


if __name__ == "__main__":
    sys.exit(main())
