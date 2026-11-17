#!/bin/bash
# Get the latest version of the PA kit (Mac, or Git Bash on Windows; on Windows you can also double-click update.cmd).
# Only the shared code changes: her config.json, Me.md, Preferences.md, Voice.md, Data/ and Drafts/ are never
# touched (they are not part of the kit; see .gitignore).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
PY="$DIR/.venv/bin/python"; [ -x "$PY" ] || PY="$DIR/.venv/Scripts/python.exe"
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
    echo "Restarting the Telegram line so it uses the new version..."
    "$PY" -X utf8 Tools/line.py stop --keep-on; sleep 3; "$PY" -X utf8 Tools/line.py start
  fi
fi
