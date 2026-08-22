"""PathAhead as a double-clickable desktop app.

The entry point for the packaged build: one file, no Python installed, no
terminal, no internet. Double-click it and the browser opens on a working
copy of PathAhead.

WHAT THIS IS NOT
    Not a second implementation, and not a different product. It serves the
    same `web/index.html` that GitHub Pages serves, against the same compiled
    pack, through the same loopback server `tools/serve.py` already uses. The
    packaged build and the hosted build are one artifact tested once -- which
    is the whole reason the browser build has no server-side code path.

WHY PACKAGE IT AT ALL
    Three reasons, all about who can actually use the thing:

      * A family with a slow or metered connection, or none at the moment
        they need it. Everything is local; the app works with the network
        cable out.
      * A shared or school computer where installing Python is not on the
        table.
      * The privacy promise, made checkable. "Nothing you type leaves this
        device" is easy to say and hard for a non-technical reader to verify
        on a website. An executable they can run with the wifi off is a
        claim they can test themselves in ten seconds.

WHAT IT BUNDLES
    The browser app, its assets, and a PRE-COMPILED pack. Not the YAML
    sources and not PyYAML: compiling at build time rather than at launch
    means a faster start, a smaller binary, and one less thing that can fail
    on a stranger's machine.

    It deliberately does NOT bundle any local-only data overlay. See
    tools/build_desktop.py, which refuses to build if one is present unless
    told otherwise in as many words. Redistributing figures PathAhead is not
    free to redistribute would be exactly as wrong inside an .exe as inside a
    git repository, and rather harder to notice.
"""

from __future__ import annotations

import http.server
import os
import socket
import sys
import threading
import webbrowser
from functools import partial
from pathlib import Path

#: Ports to try, in order. Matches tools/serve.py so the two behave alike.
PORT_ATTEMPTS = 8
DEFAULT_PORT = 8902

CLIENT_DISCONNECT = (
    ConnectionAbortedError,
    ConnectionResetError,
    BrokenPipeError,
    TimeoutError,
)


def resource_root() -> Path:
    """Where the bundled `web/` directory lives, frozen or not.

    PyInstaller unpacks a one-file build into a temporary directory and
    points `sys._MEIPASS` at it. Running from a source checkout, the same
    files sit next to this script. Resolving both here keeps every other
    function identical in the two cases -- the alternative is a `if frozen`
    branch at each use site, which is how the two paths quietly diverge.
    """
    bundled = getattr(sys, "_MEIPASS", None)
    return Path(bundled) if bundled else Path(__file__).resolve().parent


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the app, sets conservative headers, and stays quiet.

    Identical posture to tools/serve.py's handler, and for the same reasons:
    the request-log suppression is a privacy choice, not a tidiness one. A
    local request log is a record of what a family looked up, sitting on
    their disk.
    """

    protocol_version = "HTTP/1.1"
    server_version = "PathAhead"
    sys_version = ""

    def log_message(self, *args, **kwargs) -> None:
        return

    def copyfile(self, source, outputfile) -> None:
        import contextlib

        with contextlib.suppress(CLIENT_DISCONNECT):
            super().copyfile(source, outputfile)

    def handle_one_request(self) -> None:
        try:
            super().handle_one_request()
        except CLIENT_DISCONNECT:
            self.close_connection = True

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        # The app needs nothing external; say so, and mean it. index.html
        # carries the same policy as a <meta> so the guarantee survives being
        # opened without this server at all.
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "font-src 'self'; connect-src 'self'; form-action 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()


class _QuietServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address) -> None:
        exc = sys.exc_info()[1]
        if isinstance(exc, CLIENT_DISCONNECT):
            return
        print(f"  (a request could not be completed: {type(exc).__name__}: {exc})", flush=True)


def _bind(web_root: Path, port: int) -> tuple[_QuietServer, int]:
    """Bind the first free port from `port`.

    Binds 127.0.0.1 explicitly, never 0.0.0.0. On a shared network -- a
    school, a library, a home with guests -- binding all interfaces would put
    a child's half-finished answers on the LAN. Loopback means the only
    machine that can reach this server is the one it is running on.
    """
    handler = partial(_QuietHandler, directory=str(web_root))
    last: OSError | None = None
    for candidate in range(port, port + PORT_ATTEMPTS):
        try:
            return _QuietServer(("127.0.0.1", candidate), handler), candidate
        except OSError as exc:
            last = exc
            if exc.errno not in (48, 98, 10048):  # EADDRINUSE across platforms
                raise
    raise SystemExit(
        f"\n  Could not find a free port between {port} and {port + PORT_ATTEMPTS - 1}.\n"
        f"  PathAhead may already be running in another window. ({last})\n"
    )


def _wait_for_exit() -> None:
    """Keep the window open until the user closes it.

    A packaged app is usually launched by double-click, so there is no shell
    to return to and no Ctrl+C convention the reader necessarily knows. On
    Windows a bare `return` would close the console instantly and the app
    would appear to have crashed.
    """
    try:
        if sys.stdin and sys.stdin.isatty():
            input()
        else:
            threading.Event().wait()
    except (KeyboardInterrupt, EOFError):
        pass


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    open_browser = "--no-browser" not in argv
    port = DEFAULT_PORT
    if "--port" in argv:
        try:
            port = int(argv[argv.index("--port") + 1])
        except (IndexError, ValueError):
            print("  --port needs a number, e.g. --port 8902", file=sys.stderr)
            return 2

    web_root = resource_root() / "web"
    if not (web_root / "index.html").exists():
        print(
            "  This build is missing its web files, which means it was packaged\n"
            "  incorrectly rather than that you did anything wrong.\n"
            f"  Looked in: {web_root}",
            file=sys.stderr,
        )
        return 1

    httpd, actual_port = _bind(web_root, port)
    url = f"http://127.0.0.1:{actual_port}/"

    print()
    print("  PathAhead")
    print("  =========")
    print()
    print(f"  Running at {url}")
    print()
    print("  Nothing you type here leaves this computer. There is no account,")
    print("  no tracking, and nothing is sent anywhere -- you can disconnect")
    print("  from the internet and it will keep working.")
    print()
    print("  These are last year's published figures, not a prediction, and")
    print("  this is not advice. Check anything that matters against the")
    print("  official source, which every figure links to.")
    print()
    print("  Leave this window open while you use PathAhead.")
    print("  Close it, or press Ctrl+C, to stop.")
    print(flush=True)

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    try:
        _wait_for_exit()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n  Stopped.", flush=True)
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


if __name__ == "__main__":
    # Windows double-click launches with no console attached in --windowed
    # builds; this build is deliberately a console app so the reader can see
    # the privacy statement and the URL. os.environ guard keeps that readable
    # if a launcher redirects output.
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(main())
