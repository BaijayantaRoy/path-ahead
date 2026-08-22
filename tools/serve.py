"""Run the local app.

There is no web framework here, and that is deliberate. The browser build is
fully client-side, so serving it locally is literally serving static files.
That means Tier A (a link a parent taps, hosted free on GitHub Pages) and
Tier B (an app installed on their own machine) are the *same artifact*, tested
once, with no server-side code path that only exists in one of them.

It also means nothing a user types is ever sent anywhere -- there is nowhere
for it to be sent to.

Two robustness notes, both learned from a real run:

  * Browsers routinely abandon a connection mid-transfer -- a reload, a
    navigation, a cancelled fetch. Python's default handler prints a full
    traceback for that. It is harmless, but a wall of red text in the window a
    parent was told to leave open is a support incident waiting to happen, so
    client disconnects are swallowed silently and everything else is reported
    as one readable line.
  * The server is threaded. Single-threaded, one stalled connection freezes the
    whole app for everyone.
"""

from __future__ import annotations

import contextlib
import http.server
import socket
import sys
import threading
import webbrowser
from functools import partial
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

#: Ports to try, in order, before giving up. 8902 is the documented default.
PORT_ATTEMPTS = 8

#: Exceptions that mean "the browser went away", not "something is wrong".
CLIENT_DISCONNECT = (
    ConnectionAbortedError,   # Windows: WinError 10053
    ConnectionResetError,     # Windows: WinError 10054 / POSIX: ECONNRESET
    BrokenPipeError,          # POSIX
    TimeoutError,
)


def is_client_disconnect(exc: BaseException | None) -> bool:
    """Was this the browser hanging up, rather than a fault worth showing?"""
    return isinstance(exc, CLIENT_DISCONNECT)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the app, sets conservative headers, and stays quiet.

    The request-log suppression is a privacy choice, not a tidiness one: a
    local request log is a record of what a family looked up, sitting on disk.
    """

    protocol_version = "HTTP/1.1"
    server_version = "PathAhead"
    sys_version = ""

    def log_message(self, *args, **kwargs) -> None:
        return

    def copyfile(self, source, outputfile) -> None:
        """Send a file, tolerating the browser closing the connection."""
        with contextlib.suppress(CLIENT_DISCONNECT):
            super().copyfile(source, outputfile)

    def handle_one_request(self) -> None:
        try:
            super().handle_one_request()
        except CLIENT_DISCONNECT:
            self.close_connection = True

    def end_headers(self) -> None:
        # No caching of the pack, so a data update is picked up on reload.
        self.send_header("Cache-Control", "no-store")
        # The app needs nothing external; say so, and mean it.
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; form-action 'none'; base-uri 'none'",
        )
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()


class _QuietServer(http.server.ThreadingHTTPServer):
    """Threaded, and it does not shout about a browser closing a tab."""

    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address) -> None:
        exc = sys.exc_info()[1]
        if is_client_disconnect(exc):
            return  # the browser went away; nothing is wrong
        print(f"  (a request could not be completed: {type(exc).__name__}: {exc})", flush=True)


def _bind(port: int) -> tuple[_QuietServer, int]:
    """Bind the first free port from `port`, so a stale instance is not fatal."""
    handler = partial(_QuietHandler, directory=str(REPO / "web"))
    last: OSError | None = None
    for candidate in range(port, port + PORT_ATTEMPTS):
        try:
            return _QuietServer(("127.0.0.1", candidate), handler), candidate
        except OSError as exc:
            last = exc
            if exc.errno not in (48, 98, 10048):  # EADDRINUSE across platforms
                raise
            print(f"  port {candidate} is busy, trying {candidate + 1}...", flush=True)
    raise SystemExit(
        f"\n  Could not find a free port between {port} and {port + PORT_ATTEMPTS - 1}.\n"
        f"  PathAhead may already be running in another window. ({last})\n"
    )


def serve(pack_dir: str | Path, port: int = 8902, open_browser: bool = True) -> int:
    from tools.build_pack import build

    web_root = REPO / "web"
    if not web_root.exists():
        print("web/ is missing -- nothing to serve", file=sys.stderr)
        return 1

    # Compile the pack straight into the web root so the browser build always
    # runs against the same data the CLI just validated.
    built = build(pack_dir, web_root / "data")
    print(f"  data     {built['bundle'].name}", flush=True)

    httpd, actual_port = _bind(port)
    url = f"http://127.0.0.1:{actual_port}/"
    # flush=True: without it Python buffers when the launcher's output is
    # redirected to a file, and the user stares at an empty window wondering
    # whether anything happened.
    print(f"\n  PathAhead is running at {url}", flush=True)
    print("  Nothing you type leaves this computer.", flush=True)
    print("  Leave this window open while you use it. Press Ctrl+C to stop.\n", flush=True)

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.", flush=True)
    finally:
        httpd.shutdown()
        httpd.server_close()
    return 0


def _port_is_free(port: int) -> bool:  # used by tests
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(serve(REPO / "packs" / "singapore"))
