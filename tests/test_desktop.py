"""Tests for desktop.py -- the packaged, double-clickable build.

The packaging itself cannot be tested here (PyInstaller needs a minute and a
platform), but everything that decides whether the packaged app is SAFE can
be, and those are the parts worth guarding: where it binds, what headers it
sends, and whether it can be tricked into serving something outside the app.

The binding test in particular is the one that matters. A one-character
change from "127.0.0.1" to "" would put a child's half-finished answers on
every network the machine is attached to, and it would look completely
normal in review.
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import desktop


@pytest.fixture()
def running_server(tmp_path):
    """Start the real server on a free port, serving a temporary web root."""
    web = tmp_path / "web"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>t</title>ok", encoding="utf-8")
    (web / "assets" / "x.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("must never be served", encoding="utf-8")

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    httpd, actual = desktop._bind(web, port)
    import threading

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{actual}", tmp_path, httpd
    finally:
        httpd.shutdown()
        httpd.server_close()


def _get(url: str):
    return urllib.request.urlopen(url, timeout=5)


# --- where it listens ------------------------------------------------------


def test_the_server_binds_loopback_and_not_every_interface(running_server):
    """The single most consequential line in this file.

    Binding "" or "0.0.0.0" would expose whatever a child has typed to every
    other device on the network -- a school LAN, a shared flat, a cafe. The
    app promises the opposite in its own startup banner, so this asserts the
    socket the server actually bound.

    An earlier version of this test tried to prove the negative by binding
    0.0.0.0 on the same port and expecting success. That is not the test it
    looks like: 0.0.0.0 includes 127.0.0.1, so the kernel refuses the second
    bind either way and the assertion failed against a perfectly correct
    server. Reading the bound address is both simpler and actually true.
    """
    base, _, httpd = running_server
    host, port = httpd.server_address[:2]

    assert host == "127.0.0.1", f"server bound {host}, which is reachable from other machines"
    assert _get(base + "/").status == 200

    # And nothing answers on this host's routable address, if it has one.
    lan_ip = _first_non_loopback_ipv4()
    if lan_ip:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.5)
            assert s.connect_ex((lan_ip, port)) != 0, (
                f"the app answered on {lan_ip}:{port} -- other devices on this "
                "network can read what is typed into it"
            )


def _first_non_loopback_ipv4() -> str | None:
    """This machine's routable IPv4, or None (CI containers often have none)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("192.0.2.1", 9))  # TEST-NET-1: routed nowhere, never sent
            ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None


# --- what it sends ---------------------------------------------------------


def test_every_response_carries_the_no_external_resources_policy(running_server):
    base, _, _httpd = running_server
    headers = _get(base + "/").headers
    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "connect-src 'self'" in csp, "the page must not be able to call out"
    assert "font-src 'self'" in csp, "webfonts from a CDN would leak the reader's IP"
    assert headers.get("Referrer-Policy") == "no-referrer"
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"


def test_nothing_is_cached_so_a_data_update_is_never_missed(running_server):
    base, _, _httpd = running_server
    assert _get(base + "/").headers.get("Cache-Control") == "no-store"


def test_the_server_does_not_announce_its_python_version(running_server):
    """Version banners are free reconnaissance and buy the reader nothing."""
    base, _, _httpd = running_server
    server = _get(base + "/").headers.get("Server", "")
    assert "Python" not in server
    assert server.startswith("PathAhead")


# --- what it refuses to serve ---------------------------------------------


def test_a_path_traversal_cannot_escape_the_web_root(running_server):
    """`secret.txt` sits one level above the web root and must stay there."""
    base, _, _httpd = running_server
    for attempt in ("/../secret.txt", "/..%2fsecret.txt", "/%2e%2e/secret.txt"):
        try:
            body = _get(base + attempt).read()
        except urllib.error.HTTPError as exc:
            assert exc.code in (400, 403, 404), f"{attempt} gave {exc.code}"
            continue
        assert b"must never be served" not in body, f"{attempt} escaped the web root"


# --- how it finds its files ------------------------------------------------


def test_resource_root_is_the_source_tree_when_not_frozen():
    assert desktop.resource_root() == Path(desktop.__file__).resolve().parent


def test_resource_root_follows_pyinstaller_when_frozen(monkeypatch, tmp_path):
    """PyInstaller unpacks a one-file build to a temp dir and sets _MEIPASS.

    Getting this wrong means the packaged app looks in the directory the
    user happened to double-click from, finds nothing, and reports itself
    broken -- on their machine only, which is the worst place to discover it.
    """
    monkeypatch.setattr(desktop.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert desktop.resource_root() == tmp_path


def test_a_missing_web_root_fails_with_a_human_explanation(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(desktop, "resource_root", lambda: tmp_path)
    assert desktop.main(["--no-browser"]) == 1
    err = capsys.readouterr().err
    assert "packaged" in err, "the error blames the user rather than the build"


def test_a_bad_port_argument_is_rejected_rather_than_crashing(capsys):
    assert desktop.main(["--port", "not-a-number"]) == 2
    assert "--port needs a number" in capsys.readouterr().err
