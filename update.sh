#!/bin/bash
# Get the latest version of the PA kit. Only the shared code changes: her config.json, Me.md, Preferences.md,
# Voice.md, Data/ and Drafts/ are never touched (they are not part of the kit; see .gitignore).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
before=$(git rev-parse --short HEAD)
git pull --ff-only
after=$(git rev-parse --short HEAD)
.venv/bin/pip install -q -r requirements.txt
if [ "$before" = "$after" ]; then
  echo "Already up to date."
else
  echo "Updated. What changed:"; git log --oneline "$before..$after"
  [ -f CHANGELOG.md ] && echo "(details in CHANGELOG.md)"
  if pgrep -f "claude.*--channels" >/dev/null 2>&1; then
    echo "Restarting the Telegram line so it uses the new version..."
    bash Tools/stop_line.sh --keep-on; sleep 3; bash Tools/start_line.sh
  fi
fi
