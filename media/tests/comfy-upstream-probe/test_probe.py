"""Unit tests for pkgs/comfy-upstream-probe/probe.py.

Loaded by path (like tests/media-fetch/test_fetch.py) so this file works both
under `pytest tests/comfy-upstream-probe` from the repo root and inside the
checks.comfy-upstream-probe-unit sandbox, which copies
pkgs/comfy-upstream-probe and tests/comfy-upstream-probe into a fresh tree.

The probe's only two side-effecting seams are `fetch_json`/`fetch_text`
(network) and `run` (subprocess); every test monkeypatches them, so nothing
here touches the network or spawns a real process.
"""

import importlib.util
import json
import pathlib
import shutil
import urllib.request

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "comfy-upstream-probe" / "probe.py"
spec = importlib.util.spec_from_file_location("probe", SRC)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

TAGS_URL = "https://api.github.com/repos/Comfy-Org/ComfyUI/tags?per_page=20"
TEMPLATES_URL = "https://pypi.org/pypi/comfyui-workflow-templates/0.11.55/json"
ANGLE_URL = "https://pypi.org/pypi/comfy-angle/json"
NVIDIA_URL = "https://www.nvidia.com/en-us/drivers/unix/"

# A real public root CA (Amazon Root CA 3) so `_open`'s
# ssl.create_default_context(cafile=...) has a parseable PEM to load. No test
# here performs a handshake; the file only has to be a valid, readable bundle.
_CA_PEM = """-----BEGIN CERTIFICATE-----
MIIBtjCCAVugAwIBAgITBmyf1XSXNmY/Owua2eiedgPySjAKBggqhkjOPQQDAjA5
MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6b24g
Um9vdCBDQSAzMB4XDTE1MDUyNjAwMDAwMFoXDTQwMDUyNjAwMDAwMFowOTELMAkG
A1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJvb3Qg
Q0EgMzBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABCmXp8ZBf8ANm+gBG1bG8lKl
ui2yEujSLtf6ycXYqm0fc4E7O5hrOXwzpcVOho6AF2hiRVd9RFgdszflZwjrZt6j
QjBAMA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgGGMB0GA1UdDgQWBBSr
ttvXBp43rDCGB5Fwx5zEGbF4wDAKBggqhkjOPQQDAgNJADBGAiEA4IWSoxe3jfkr
BqWTrBqYaGFy+uGh0PsceGCmQ5nFuMQCIQCcAu/xlJyzlvnrxir4tiz+OpAUFteM
YyRIHN8wfdVoOw==
-----END CERTIFICATE-----
"""


@pytest.fixture
def fixtures():
    return HERE.parent / "fixtures"


def fake_fetch_json(fixtures):
    """Map the three JSON URLs the dry run touches to fixture files."""
    mapping = {
        TAGS_URL: "tags.json",
        TEMPLATES_URL: "comfyui-workflow-templates-0.11.55.json",
        ANGLE_URL: "comfy-angle.json",
    }

    def fetch(url):
        if url not in mapping:
            raise AssertionError("unexpected fetch_json url: %s" % url)
        return json.loads((fixtures / mapping[url]).read_text())

    return fetch


def fake_fetch_text(fixtures):
    """Map the requirements and NVIDIA page URLs to fixture files."""

    def fetch(url):
        if url.endswith("/requirements.txt"):
            return (fixtures / "requirements-v0.34.5.txt").read_text()
        if url == NVIDIA_URL:
            return (fixtures / "nvidia-unix.html").read_text()
        raise AssertionError("unexpected fetch_text url: %s" % url)

    return fetch


def copy_repo(src, parent, name="repo"):
    """Copy the fixture repo into a fresh dir named `name` (rewrite_pins mutates it).

    chmod 644/755 afterwards: in the nix sandbox the fixtures arrive via a
    read-only store path and `copytree` preserves those modes, which would
    otherwise make rewrite_pins' `write_text` fail with PermissionError.
    """
    dest = parent / name
    shutil.copytree(src, dest)
    for p in dest.rglob("*"):
        p.chmod(0o755 if p.is_dir() else 0o644)
    return dest


class FakeCP:
    """Stand-in for the CompletedProcess `probe.run` returns."""

    def __init__(self, returncode, stdout, stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_reads_current_pins_from_the_closed_table(fixtures):
    pins = probe.read_pins(fixtures / "repo")
    assert pins["comfyui"] == {
        "version": "0.34.3",
        "rev": "87465b8f1f64a27a46f16f22b13b410494dca66d",
    }
    assert (
        pins["comfyui-frontend-package"]["version"] == "1.49.6"
        and pins["comfy-aimdo"]["version"] == "0.4.15"
    )
    assert pins["comfyui-workflow-templates-core"]["version"] == "0.3.331"
    assert (
        "av" not in pins and "ffmpeg-8-headless" not in pins
    )  # pinned on purpose, never watched


def test_dry_run_targets_the_tags_requirements_not_pypi_latest(
    fixtures, monkeypatch, capsys
):
    # A cleared proxy/CA environment proves the dry-run path never reaches
    # `_open`: it would otherwise refuse on the missing proxy (invariant 3).
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.setattr(probe, "fetch_json", fake_fetch_json(fixtures))
    monkeypatch.setattr(probe, "fetch_text", fake_fetch_text(fixtures))
    rc = probe.main(
        ["--repo", str(fixtures / "repo"), "--dry-run", "--host-driver", "570.195.03"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "comfyui 0.34.3 -> 0.34.5" in out
    assert (
        "comfyui-workflow-templates 0.11.54 -> 0.11.55" in out
        and "comfyui-workflow-templates-core 0.3.331 -> 0.3.333" in out
    )
    assert (
        "comfyui-frontend-package current" in out and "comfy-kitchen current" in out
    )  # requirements.txt pins 1.49.6 / 0.2.31; PyPI latest is not the target
    assert "1.52.6" not in out
    assert "nvidia-driver 570.195.03 -> 595.99.02" in out and "600.10.01" not in out
    assert "comfy-angle 0.1.1 -> 0.1.2" in out


def test_production_row_not_feature_branch(fixtures):
    page = (fixtures / "nvidia-unix.html").read_text()
    assert probe.parse_production_driver(page) == "595.99.02"


def test_rewrite_pins_changes_only_the_literals(fixtures, tmp_path):
    repo = copy_repo(fixtures / "repo", tmp_path)
    probe.rewrite_pins(
        repo,
        {
            "comfyui": {
                "version": "0.34.5",
                "rev": "7fd919f0caff" + "0" * 28,
                "hash": "sha256-AAAA",
            },
            "comfy-aimdo": {"version": "0.4.16", "hash": "sha256-BBBB"},
        },
    )
    text = (repo / "pkgs/comfyui/package.nix").read_text()
    assert (
        'version = "0.34.5"' in text
        and "7fd919f0caff" in text
        and "sha256-AAAA" in text
        and "0.34.3" not in text
    )
    aimdo = (repo / "pkgs/comfyui/deps/comfy-aimdo.nix").read_text()
    assert 'version = "0.4.16"' in aimdo and "sha256-BBBB" in aimdo
    assert (repo / "pkgs/comfyui/deps/comfy-kitchen.nix").read_text() == (
        fixtures / "repo/pkgs/comfyui/deps/comfy-kitchen.nix"
    ).read_text()


def test_report_and_brief_from_a_red_check_log(fixtures, tmp_path):
    verdicts = probe.parse_check_log((fixtures / "flake-check-red.log").read_text())
    assert verdicts["comfyui-startup-clean"] is False and verdicts["lint"] is True
    report = probe.render_report(
        "2026-09-07",
        {"comfyui": ("0.34.3", "0.34.5")},
        verdicts,
        "/ws/2026-09-07/media",
        "propose/comfyui-2026-09-07",
    )
    assert (
        "git -C ~/flakes/media merge --ff-only /ws/2026-09-07/media propose/comfyui-2026-09-07"
        in report
        and "comfyui-startup-clean: RED" in report
    )
    brief = probe.render_brief(
        "2026-09-07", verdicts, (fixtures / "flake-check-red.log").read_text()
    )
    assert "M-refresh-2026-09-07" in brief and "forbidden line: Traceback" in brief


def test_driver_stanza_needs_all_four_hashes():
    hashes = {
        "sha256_64bit": "sha256-A",
        "openSha256": "sha256-B",
        "settingsSha256": "sha256-C",
        "persistencedSha256": "sha256-D",
    }
    stanza = probe.render_driver_stanza("595.99.02", hashes)
    assert (
        all(k in stanza for k in hashes)
        and 'version = "595.99.02"' in stanza
        and "mkDriver" in stanza
    )
    with pytest.raises(ValueError, match="openSha256"):
        probe.render_driver_stanza(
            "595.99.02", {k: v for k, v in hashes.items() if k != "openSha256"}
        )


def test_records_a_heartbeat_when_nothing_moved(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        probe, "run", lambda argv, cwd=None: calls.append(argv) or FakeCP(0, "{}")
    )
    monkeypatch.setattr(
        probe.shutil,
        "which",
        lambda name: "/bin/evidence" if name == "evidence" else None,
    )
    probe.record(str(tmp_path), None, {}, probe.heartbeat_row("media"))
    rows = [
        json.loads(c[c.index("--json") + 1])
        for c in calls
        if "record" in c and "proposals" in c
    ]
    assert rows == [
        {
            "kind": "proposal",
            "repo": "media",
            "branch": None,
            "bumps": [],
            "checks_green": None,
        }
    ]
    assert not any("record-check" in c for c in calls)


def test_records_only_when_evidence_cli_present(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        probe, "run", lambda argv, cwd=None: calls.append(argv) or FakeCP(0, "{}")
    )
    monkeypatch.setattr(
        probe.shutil,
        "which",
        lambda name: "/bin/evidence" if name == "evidence" else None,
    )
    probe.record(
        str(tmp_path),
        "a" * 40,
        {"lint": True, "comfyui-vm": False},
        {
            "kind": "proposal",
            "repo": "media",
            "branch": "propose/x",
            "bumps": [],
            "checks_green": False,
        },
    )
    names = [c[c.index("--name") + 1] for c in calls if "record-check" in c]
    assert (
        names == ["comfyui-vm", "lint"]
        and any("--fail" in c for c in calls)
        and any("record" in c and "proposals" in c for c in calls)
    )
    calls.clear()
    monkeypatch.setattr(probe.shutil, "which", lambda name: None)
    assert (
        probe.record(str(tmp_path), "a" * 40, {"lint": True}, {"kind": "proposal"})
        == "not recorded (no evidence CLI on PATH)"
        and calls == []
    )


def test_prefetch_converts_nix32_to_sri(monkeypatch):
    calls = []
    nix32 = "06f7alvx8p16k4dcgbjrjrb1kzsbqvpvmvz74pn0i5vjqavgvhqd"

    def fake_run(argv, cwd=None, check=False):
        calls.append(list(argv))
        if argv[0] == "nix-prefetch-url":
            return FakeCP(0, nix32 + "\n")
        if argv[0] == "nix":
            return FakeCP(0, "sha256-stub\n")
        raise AssertionError("unexpected argv: %r" % argv)

    monkeypatch.setattr(probe, "run", fake_run)
    url = "https://github.com/Comfy-Org/ComfyUI/archive/x.tar.gz"
    assert probe._prefetch(url, unpack=True) == "sha256-stub"
    assert calls[0] == ["nix-prefetch-url", "--unpack", url]
    assert calls[1][:3] == ["nix", "hash", "convert"]
    assert calls[1][-1] == nix32


def test_record_and_report_prints_when_not_recorded(monkeypatch, capsys):
    monkeypatch.setattr(probe.shutil, "which", lambda name: None)
    probe._record_and_report("s", None, {}, {"kind": "proposal"})
    assert (
        capsys.readouterr().out == "evidence: not recorded (no evidence CLI on PATH)\n"
    )


def test_record_and_report_silent_when_recorded(monkeypatch, capsys):
    monkeypatch.setattr(
        probe, "run", lambda argv, cwd=None, check=False: FakeCP(0, "{}")
    )
    monkeypatch.setattr(probe.shutil, "which", lambda name: "/bin/evidence")
    probe._record_and_report("s", None, {}, {"kind": "proposal"})
    assert capsys.readouterr().out == ""


def test_every_record_call_site_uses_the_wrapper():
    text = SRC.read_text()
    # `def record(` plus the single call inside `_record_and_report`; the three
    # former `main`/`_propose` call sites must all have switched to the wrapper.
    assert text.count("record(") == 2
    assert text.count("_record_and_report(") >= 4


def test_comfyui_rewrite_skipped_when_version_unchanged(monkeypatch):
    calls = []
    monkeypatch.setattr(
        probe,
        "_prefetch",
        lambda url, unpack=False: calls.append((url, unpack)) or "sha256-X",
    )
    assert probe._comfyui_rewrite([("comfyui", "0.34.5", "0.34.5")], "d" * 40) == {}
    assert calls == []
    got = probe._comfyui_rewrite([("comfyui", "0.34.3", "0.34.5")], "d" * 40)
    assert got == {
        "comfyui": {"version": "0.34.5", "rev": "d" * 40, "hash": "sha256-X"}
    }
    assert calls == [
        (
            "https://github.com/Comfy-Org/ComfyUI/archive/%s.tar.gz" % ("d" * 40),
            True,
        )
    ]


def test_parse_check_log_does_not_cross_contaminate_prefixed_names():
    log = (
        "checking derivation checks.x86_64-linux.lint...\n"
        "checking derivation checks.x86_64-linux.lint-extra...\n"
        "error: builder for '/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-lint-extra.drv' failed with exit code 1;\n"
    )
    assert probe.parse_check_log(log) == {"lint": True, "lint-extra": False}


def test_repo_name_passed_to_propose_is_always_media(fixtures, monkeypatch, tmp_path):
    monkeypatch.setattr(probe, "fetch_json", fake_fetch_json(fixtures))
    monkeypatch.setattr(probe, "fetch_text", fake_fetch_text(fixtures))
    seen = []

    def spy(args, repo_name, repo, rows, comfyui_rev, driver, date):
        seen.append(repo_name)
        return 0

    monkeypatch.setattr(probe, "_propose", spy)
    repo_dir = copy_repo(fixtures / "repo", tmp_path, name="not-media")
    rc = probe.main(
        [
            "--repo",
            str(repo_dir),
            "--host-driver",
            "570.195.03",
            "--reports",
            str(tmp_path / "reports"),
        ]
    )
    assert rc == 0
    assert seen == ["media"]


def test_record_warns_on_a_rejected_row(monkeypatch, tmp_path, capsys):
    def fake_run(argv, cwd=None, check=False):
        if "record-check" in argv:
            return FakeCP(1, "", stderr="rev must be 40 hex")
        return FakeCP(0, "{}")

    monkeypatch.setattr(probe, "run", fake_run)
    monkeypatch.setattr(probe.shutil, "which", lambda name: "/bin/evidence")
    probe.record(str(tmp_path), None, {"lint": True}, {"kind": "proposal"})
    assert (
        "evidence: record-check lint rejected: rev must be 40 hex"
        in capsys.readouterr().out
    )


def test_open_refuses_without_proxy(monkeypatch, tmp_path):
    ca = tmp_path / "ca.pem"
    ca.write_text(_CA_PEM)
    monkeypatch.setenv("SSL_CERT_FILE", str(ca))
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    with pytest.raises(RuntimeError, match="refusing direct egress"):
        probe._open("https://example.com/x")


def test_open_refuses_without_ca(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://10.100.2.1:3130")
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    with pytest.raises(RuntimeError, match="refusing direct egress"):
        probe._open("https://example.com/x")


def test_open_refuses_missing_ca_file(monkeypatch, tmp_path):
    monkeypatch.setenv("HTTPS_PROXY", "http://10.100.2.1:3130")
    # An absent CA path is refused before any socket is opened.
    monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "absent.pem"))
    with pytest.raises(RuntimeError, match="is not a readable CA bundle"):
        probe._open("https://example.com/x")
    # A present but unreadable bundle is refused the same way.
    unreadable = tmp_path / "unreadable.pem"
    unreadable.write_text(_CA_PEM)
    unreadable.chmod(0o000)
    with pytest.raises(RuntimeError, match="is not a readable CA bundle"):
        probe._open("https://example.com/x")


def test_open_builds_proxy_opener(monkeypatch, tmp_path):
    ca = tmp_path / "ca.pem"
    ca.write_text(_CA_PEM)
    monkeypatch.setenv("HTTPS_PROXY", "http://10.100.2.1:3130")
    monkeypatch.setenv("SSL_CERT_FILE", str(ca))
    seen = []

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"ok"

    class _FakeOpener:
        def open(self, req, timeout=None):
            seen.append(("open", req, timeout))
            return _FakeResp()

    def fake_build_opener(*handlers):
        seen.append(("handlers", handlers))
        return _FakeOpener()

    monkeypatch.setattr(probe.urllib.request, "build_opener", fake_build_opener)
    assert probe._open("https://example.com/x") == "ok"
    handlers = seen[0][1]
    proxy_handlers = [h for h in handlers if isinstance(h, urllib.request.ProxyHandler)]
    assert len(proxy_handlers) == 1
    assert proxy_handlers[0].proxies == {"https": "http://10.100.2.1:3130"}
    # The only call after build_opener is the fake opener's `open` — no real
    # socket is ever created.
    assert [e[0] for e in seen[1:]] == ["open"]
