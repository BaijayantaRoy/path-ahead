#!/usr/bin/env bash
#  PathAhead launcher (macOS / Linux). Self-heals if something is missing.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo
  echo "  PathAhead is not set up on this computer yet."
  echo "  Please run  ./PathAhead_Install.sh  first."
  echo
  exit 1
fi

# Self-heal: make sure dependencies and data are present and current.
./.venv/bin/python -m pip install -r requirements.txt --quiet >/dev/null 2>&1 || true

echo
echo "  Starting PathAhead..."
echo "  Your browser will open in a moment. Nothing you type leaves this computer."
echo "  Press Ctrl+C to stop."
echo
exec ./.venv/bin/python app/cli.py serve --port 8902
