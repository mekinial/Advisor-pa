#!/bin/bash
# Stops the Telegram line. The watchdog then leaves it stopped until Tools/start_line.sh is run again.
# (--keep-on is used by the watchdog itself when it restarts the line.)
DIR="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p "$DIR/Drafts/Status"
[ "$1" = "--keep-on" ] || touch "$DIR/Drafts/Status/line-off"
tmux kill-session -t pa-line 2>/dev/null
pkill -f "claude.*--channels" 2>/dev/null
echo "Telegram line stopped."
