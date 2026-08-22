#!/usr/bin/env python3
"""Build web/index.html from modular source files in web/src/.

Architecture
------------
PathAhead maintains a strict zero-runtime-dependency, single-file distribution
posture for web/index.html so it can be served air-gapped on loopback, USB, or
GitHub Pages with zero network requests.

During development, maintaining 5,800+ lines in a single file increases cognitive
load. This tool splits and compiles modular source components with byte-exact fidelity:
  - web/src/head.html   -- Doctype, meta tags, title, CSP
  - web/src/styles.css  -- Theme tokens, layout, card styling, media queries
  - web/src/body.html   -- SVG definitions, view templates, headers, footer
  - web/src/app.js      -- Client router, scoring algorithms, UI renderers

Usage:
  python tools/build_web.py          # Compile web/src/ -> web/index.html
  python tools/build_web.py --split  # Split web/index.html -> web/src/
  python tools/build_web.py --check  # Verify web/index.html matches web/src/ (for CI)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO / "web" / "index.html"
SRC_DIR = REPO / "web" / "src"

HEAD_FILE = SRC_DIR / "head.html"
CSS_FILE = SRC_DIR / "styles.css"
BODY_FILE = SRC_DIR / "body.html"
JS_FILE = SRC_DIR / "app.js"

STYLE_OPEN = "<style>\n"
STYLE_CLOSE = "\n</style>\n</head>\n<body>\n"
SCRIPT_OPEN = "\n<script>\n"
SCRIPT_CLOSE = "\n</script>\n</body>\n</html>\n"


def split_index_html() -> None:
    """Split web/index.html into web/src/ components with exact fidelity."""
    if not INDEX_HTML.exists():
        print(f"Error: {INDEX_HTML} not found.", file=sys.stderr)
        sys.exit(1)

    SRC_DIR.mkdir(parents=True, exist_ok=True)
    raw = INDEX_HTML.read_text(encoding="utf-8").replace("\r\n", "\n")

    p1 = raw.find("<style>")
    p2 = raw.find("</style>")
    p3 = raw.find("<script>")
    p4 = raw.rfind("</script>")

    if p1 == -1 or p2 == -1 or p3 == -1 or p4 == -1:
        print("Error: Could not locate boundary tags in web/index.html", file=sys.stderr)
        sys.exit(1)

    head = raw[:p1].rstrip("\n") + "\n"
    css = raw[p1 + len("<style>") : p2].strip("\n") + "\n"
    
    # Body between </head>\n<body> and <script>
    body_part = raw[p2 + len("</style>") : p3]
    if "</head>" in body_part:
        body_part = body_part[body_part.find("<body>") + len("<body>") :]
    body = body_part.strip("\n") + "\n"

    js = raw[p3 + len("<script>") : p4].strip("\n") + "\n"

    HEAD_FILE.write_text(head, encoding="utf-8")
    CSS_FILE.write_text(css, encoding="utf-8")
    BODY_FILE.write_text(body, encoding="utf-8")
    JS_FILE.write_text(js, encoding="utf-8")

    print(f"Successfully split {INDEX_HTML} into {SRC_DIR}")


def assemble_index_html() -> str:
    """Assemble components into a single index.html string."""
    for f in (HEAD_FILE, CSS_FILE, BODY_FILE, JS_FILE):
        if not f.exists():
            print(f"Error: Missing component file {f}", file=sys.stderr)
            sys.exit(1)

    head = HEAD_FILE.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n")
    css = CSS_FILE.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    body = BODY_FILE.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    js = JS_FILE.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")

    return f"{head}\n<style>\n{css}\n</style>\n</head>\n<body>\n{body}\n<script>\n{js}\n</script>\n</body>\n</html>\n"


def build_index_html() -> None:
    """Compile web/src/ into web/index.html."""
    assembled = assemble_index_html()
    INDEX_HTML.write_text(assembled, encoding="utf-8")
    print(f"Wrote {INDEX_HTML} ({len(assembled.splitlines())} lines)")


def check_index_html() -> None:
    """Verify that web/index.html matches web/src/."""
    if not INDEX_HTML.exists():
        print(f"FAIL: {INDEX_HTML} does not exist.", file=sys.stderr)
        sys.exit(1)

    assembled = assemble_index_html().replace("\r\n", "\n")
    current = INDEX_HTML.read_text(encoding="utf-8").replace("\r\n", "\n")

    if assembled == current:
        print("OK: web/index.html is in exact sync with web/src/ components.")
    else:
        print("FAIL: web/index.html has diverged from web/src/.", file=sys.stderr)
        print("Run 'python tools/build_web.py' to rebuild from src/ or 'python tools/build_web.py --split' to refresh src/.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", action="store_true", help="Split web/index.html into web/src/ components")
    parser.add_argument("--check", action="store_true", help="Check that web/index.html matches web/src/")
    args = parser.parse_args()

    if args.split:
        split_index_html()
    elif args.check:
        check_index_html()
    else:
        build_index_html()


if __name__ == "__main__":
    main()
