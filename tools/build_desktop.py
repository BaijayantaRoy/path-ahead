"""Package PathAhead as a single self-contained executable.

    python tools/build_desktop.py

Produces `build/dist/PathAhead` (or `PathAhead.exe` on Windows): one file,
no Python required on the target machine, no installer, no internet.

WHAT GOES IN
    desktop.py, the browser app (web/index.html and web/assets/), and a pack
    compiled fresh at build time into web/data/. Nothing else -- no YAML
    sources, no PyYAML, no test fixtures, no docs.

WHAT DOES NOT GO IN, AND THE CHECK THAT ENFORCES IT
    Any local-only data overlay (packs/*/local/). Those hold figures a person
    may keep for their own private study but that PathAhead is not free to
    redistribute -- see docs/LOCAL_DATA.md.

    An .exe is a redistribution like any other, and a worse one to get wrong:
    a reviewer can read a git diff, but nobody inspects the innards of a
    binary before forwarding it to a WhatsApp group. So this script builds
    from a CLEAN pack by default, and refuses outright if an overlay is
    present, rather than quietly excluding it and letting the maintainer
    believe their local figures made it in.

    `--include-local` overrides that, for a build you are keeping to
    yourself. It stamps the filename and prints a warning, because the whole
    risk is forgetting which build is which three weeks later.

CROSS-COMPILING
    You cannot. PyInstaller freezes the interpreter it is running on, so a
    Windows .exe must be built on Windows, a macOS binary on macOS. That is a
    PyInstaller property, not a choice made here. `.github/workflows/
    release.yml` builds all three on GitHub's runners for exactly this
    reason -- it is the only way to get a Windows .exe without a Windows
    machine.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

BUILD = REPO / "build"
DIST = BUILD / "dist"
WORK = BUILD / "work"
PACK_DIR = REPO / "packs" / "singapore"
WEB_DATA = REPO / "web" / "data"


def find_local_overlays() -> list[Path]:
    """Every local-only overlay currently on this machine."""
    return sorted((REPO / "packs").glob("*/local/*.json"))


def build_pack(include_local: bool) -> None:
    """Compile the pack into web/data/, and verify what came out.

    The verification is the point. `engine/loader.py` merges an overlay
    silently when one exists -- correct for a person running the app, wrong
    for a binary about to be handed to someone else -- so this asserts the
    property it needs rather than trusting the absence of a directory it
    checked a moment ago.
    """
    from engine import load_pack
    from tools.build_pack import build

    built = build(PACK_DIR, WEB_DATA)
    print(f"  pack      {built['bundle'].name}")

    pack = load_pack(PACK_DIR)
    carried = [s["id"] for s in pack.schools if s.get("cutoff_current")]
    if carried and not include_local:
        raise SystemExit(
            f"\n  REFUSING TO BUILD: the compiled pack carries cut-off figures for\n"
            f"  {len(carried)} school(s), e.g. {carried[:3]}.\n\n"
            "  Those come from a local overlay and are not PathAhead's to\n"
            "  redistribute. Move packs/*/local/ aside and build again, or pass\n"
            "  --include-local if this build is for you alone and will not be\n"
            "  shared. See docs/LOCAL_DATA.md.\n"
        )
    if carried:
        print(f"  WARNING   {len(carried)} schools carry local cut-off figures - DO NOT SHARE THIS BUILD")
    else:
        print("  pack      no cut-off figures (safe to distribute)")


def run_pyinstaller(name: str) -> Path:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        raise SystemExit(
            "\n  PyInstaller is not installed. It is a build-time tool only and is\n"
            "  deliberately not in requirements.txt -- running PathAhead needs\n"
            "  nothing but the standard library.\n\n"
            "      pip install pyinstaller\n"
        ) from None

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", name,
        "--distpath", str(DIST),
        "--workpath", str(WORK),
        "--specpath", str(BUILD),
        "--noconfirm",
        "--clean",
        # The browser app and the compiled pack, bundled as data. os.pathsep
        # because PyInstaller's separator differs on Windows.
        "--add-data", f"{REPO / 'web' / 'index.html'}{_sep()}web",
        "--add-data", f"{REPO / 'web' / 'assets'}{_sep()}web/assets",
        "--add-data", f"{WEB_DATA}{_sep()}web/data",
        # Nothing here imports these; excluding them keeps the binary small
        # and, more usefully, keeps a stray import from silently pulling a
        # 40 MB scientific stack into a tool that needs none of it.
        "--exclude-module", "tkinter",
        "--exclude-module", "unittest",
        "--exclude-module", "pydoc",
        "--exclude-module", "doctest",
        "--exclude-module", "yaml",
        "--console",
        str(REPO / "desktop.py"),
    ]
    print("  building  (this takes a minute)")
    subprocess.run(cmd, check=True, cwd=REPO)
    target = DIST / (f"{name}.exe" if sys.platform == "win32" else name)
    fallback = DIST / name
    if not target.exists() and fallback.exists() and sys.platform == "win32":
        fallback.rename(target)
    if not target.exists():
        raise SystemExit(f"  PyInstaller finished but {target} is missing")
    return target


def _sep() -> str:
    return ";" if sys.platform == "win32" else ":"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--include-local",
        action="store_true",
        help="bundle local-only data overlays. For personal builds ONLY; the "
             "result must not be shared. See docs/LOCAL_DATA.md.",
    )
    ap.add_argument("--name", default="PathAhead", help="executable name (default: PathAhead)")
    args = ap.parse_args()

    overlays = find_local_overlays()
    if overlays and not args.include_local:
        print(f"  note      {len(overlays)} local overlay file(s) present; they will NOT be bundled")

    name = args.name + ("-LOCAL-DO-NOT-SHARE" if args.include_local else "")

    shutil.rmtree(WORK, ignore_errors=True)
    BUILD.mkdir(exist_ok=True)

    build_pack(include_local=args.include_local)
    produced = run_pyinstaller(name)

    size_mb = produced.stat().st_size / 1_048_576
    print()
    print(f"  Built     {produced}")
    print(f"  Size      {size_mb:.1f} MB")
    print()
    print("  Double-click it. A browser opens on PathAhead, served from the")
    print("  machine it is running on. No install, no Python, no internet.")
    if args.include_local:
        print()
        print("  THIS BUILD CARRIES LOCAL-ONLY DATA. Keep it to yourself.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
