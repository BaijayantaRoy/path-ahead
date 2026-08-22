#!/usr/bin/env bash
# ====================================================================
#  PathAhead installer (macOS / Linux)
#
#  About three minutes, roughly 40 KB. There is no AI model to
#  download, because PathAhead does not need one to work.
# ====================================================================
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "  PathAhead - setting up"
echo "  ---------------------------------------------------------------"
echo

# --- 1. Is Python here? ---------------------------------------------
PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)' 2>/dev/null; then
      PY="$candidate"; break
    fi
  fi
done

if [ -z "$PY" ]; then
  cat <<'MSG'
  Python 3.10 or newer was not found on this computer.

  It is free:
    macOS   - install from https://www.python.org/downloads/
              (or, if you use Homebrew:  brew install python)
    Linux   - sudo apt install python3 python3-venv     (Debian/Ubuntu)
              sudo dnf install python3                  (Fedora)

  Then run this installer again.
MSG
  exit 1
fi
echo "  Found $("$PY" --version)"

# --- 2. Private folder for the dependencies -------------------------
echo "  Creating a private folder for PathAhead's dependencies..."
"$PY" -m venv .venv

echo "  Installing dependencies (small - about 40 KB)..."
./.venv/bin/python -m pip install --upgrade pip --quiet
./.venv/bin/python -m pip install -r requirements.txt --quiet

# --- 3. Prepare the data --------------------------------------------
echo "  Preparing the education data..."
if ! ./.venv/bin/python app/cli.py build --out web/data; then
  echo "  The data pack failed its own checks and was not installed."
  echo "  Please report this - it is a bug, not something you did."
  exit 1
fi

chmod +x PathAhead_Start.sh 2>/dev/null || true

cat <<'MSG'

  ---------------------------------------------------------------
  Done. Now run  ./PathAhead_Start.sh  to open PathAhead.

  Nothing you type into PathAhead ever leaves this computer.
  ---------------------------------------------------------------
MSG
