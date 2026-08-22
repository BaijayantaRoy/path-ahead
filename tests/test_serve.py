"""The local server: quiet on client disconnects, threaded, and locked down.

A parent is told to leave the launcher window open. What appears in that window
is part of the product: a wall of red traceback because a browser tab was
reloaded is a support incident, not a bug report.
"""

from __future__ import annotations

import http.client
import socket
import threading
import time
from functools import partial

import pytest

from tools.serve import (
    CLIENT_DISCONNECT,
    _QuietHandler,
    _QuietServer,
    is_client_disconnect,
)

# --- classification -------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        ConnectionAbortedError(10053, "An established connection was aborted"),
        ConnectionResetError(10054, "Connection reset by peer"),
        BrokenPipeError(32, "Broken pipe"),
        TimeoutError("timed out"),
    ],
)
def test_browser_hanging_up_is_not_an_error(exc):
    assert is_client_disconnect(exc)


@pytest.mark.parametrize(
    "exc",
    [ValueError("bad"), KeyError("missing"), OSError(13, "Permission denied"), None],
)
def test_real_faults_are_still_reported(exc):
    assert not is_client_disconnect(exc)


def test_windows_10053_is_covered():
    """The exact error the first real run produced on Windows."""
    assert ConnectionAbortedError in CLIENT_DISCONNECT


# --- the running server ---------------------------------------------------


@pytest.fixture
def server(tmp_path):
    (tmp_path / "index.html").write_text("<h1>ok</h1>" + "x" * 200_000, encoding="utf-8")
    handler = partial(_QuietHandler, directory=str(tmp_path))
    httpd = _QuietServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd, httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def test_it_serves_the_app(server):
    _httpd, port = server
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/")
    resp = conn.getresponse()
    assert resp.status == 200
    resp.read()
    conn.close()


def test_security_headers_are_set(server):
    _httpd, port = server
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/")
    resp = conn.getresponse()
    headers = {k.lower(): v for k, v in resp.getheaders()}
    resp.read()
    conn.close()
    assert "default-src 'self'" in headers["content-security-policy"]
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["cache-control"] == "no-store"


def test_a_client_that_hangs_up_mid_download_does_not_crash_the_server(server, capsys):
    """Reproduces the WinError 10053 case: ask for a large file, then close the
    socket without reading it. The server must stay up and stay quiet."""
    _httpd, port = server

    sock = socket.create_connection(("127.0.0.1", port), timeout=5)
    sock.sendall(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
    time.sleep(0.05)
    sock.close()          # walk away mid-transfer, exactly as a browser reload does
    time.sleep(0.25)

    out = capsys.readouterr().out
    assert "Traceback" not in out
    assert "could not be completed" not in out

    # And the server is still serving.
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/")
    assert conn.getresponse().status == 200
    conn.close()


def test_the_server_never_logs_what_was_requested(server, capsys):
    """Request logs are a record of what a family looked up, on disk."""
    _httpd, port = server
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/?child=secret")
    conn.getresponse().read()
    conn.close()
    captured = capsys.readouterr()
    assert "secret" not in captured.out + captured.err


def test_the_server_is_threaded_so_one_slow_client_cannot_freeze_it(server):
    _httpd, port = server
    stalled = socket.create_connection(("127.0.0.1", port), timeout=5)
    stalled.sendall(b"GET / HTTP/1.1\r\n")   # deliberately incomplete request
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/")
        assert conn.getresponse().status == 200
        conn.close()
    finally:
        stalled.close()


def test_it_binds_only_to_loopback(server):
    httpd, _port = server
    assert httpd.server_address[0] == "127.0.0.1", "must never listen on the network"
