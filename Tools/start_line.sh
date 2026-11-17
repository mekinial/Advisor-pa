#!/bin/bash
# Starts the Telegram line: Claude Code with the Telegram channel, running in a hidden tmux session "pa-line".
# Keep only ONE copy running: two copies on the same bot token fight over messages (this script checks).
# It runs unattended, so --permission-mode auto lets the safety checker decide instead of waiting for a click,
# and --add-dir gives it the folder where Telegram photos/files land (plus her product/forms libraries).
# ADMIN_TEAM_LINE=telegram tells the hooks (tg_line_hooks.py, tg_stuck_alert.py) that this is the Telegram line.
# Look at it:  tmux attach -t pa-line   (leave again: Ctrl-b then d).  Stop it:  Tools/stop_line.sh
# Same thing on any computer: ./pa line start | stop | status
DIR="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.bun/bin:$PATH"
mkdir -p "$DIR/Drafts/Status"
rm -f "$DIR/Drafts/Status/line-off"

if pgrep -f "claude.*--channels" >/dev/null 2>&1; then
  echo "Telegram line is already running."; exit 0
fi
command -v tmux >/dev/null || { echo "tmux is not installed (brew install tmux)"; exit 1; }
tmux has-session -t pa-line 2>/dev/null && tmux kill-session -t pa-line

# The folders are created now if missing, so the set never changes later: each new folder makes Claude Code ask
# "trust this folder?" at the next start, and a hidden line can't answer that.
ADD=("$HOME/.claude/channels/telegram/inbox")
ADD+=("$HOME/.claude/projects/$(echo "$DIR" | sed 's#[^A-Za-z0-9-]#-#g')/memory")
PY="$DIR/.venv/bin/python"; [ -x "$PY" ] || PY=python3
while IFS= read -r d; do [ -n "$d" ] && ADD+=("$d"); done < <(
  "$PY" -c "import sys; sys.path.insert(0, sys.argv[1]); import pa_config as C; print(C.PRODUCT_LIBRARY); print(C.FORMS_LIBRARY)" "$DIR/Tools" 2>/dev/null)
for d in "${ADD[@]}"; do mkdir -p "$d"; done

CMD="cd $(printf %q "$DIR") && export ADMIN_TEAM_LINE=telegram && claude --channels plugin:telegram@claude-plugins-official --permission-mode auto --add-dir"
for d in "${ADD[@]}"; do CMD+=" $(printf %q "$d")"; done
tmux new-session -d -s pa-line -x 200 -y 50 "$CMD"
echo "Telegram line started (tmux session pa-line)."
