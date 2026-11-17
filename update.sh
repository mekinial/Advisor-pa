#!/bin/bash
# Get the latest version of the PA kit (Mac, or Git Bash on Windows; on Windows you can also double-click update.cmd).
# Only the shared code changes: their config.json, Me.md, Preferences.md, Voice.md, Data/ and Drafts/ are never
# touched (they are not part of the kit; see .gitignore).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
PY="$DIR/.venv/bin/python"; [ -x "$PY" ] || PY="$DIR/.venv/Scripts/python.exe"
[ -x "$PY" ] || { echo "No Python environment yet: run setup first (Mac ./setup.sh, Windows setup.cmd)."; exit 1; }
before=$(git rev-parse --short HEAD)
git pull --ff-only
after=$(git rev-parse --short HEAD)
"$PY" -m pip install -q -r requirements.txt
if [ "$before" = "$after" ]; then
  echo "Already up to date."
else
  echo "Updated. What changed:"; git log --oneline "$before..$after"
  [ -f CHANGELOG.md ] && echo "(details in CHANGELOG.md)"
  if "$PY" -X utf8 Tools/line.py status | grep -q "is running"; then
    # restart runs on its own (detached), because this script may itself be running inside the Telegram line
    echo "Restarting the Telegram line in a few seconds so it uses the new version..."
    "$PY" -X utf8 Tools/line.py restart
  fi
fi
