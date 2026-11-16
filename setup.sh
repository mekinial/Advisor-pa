#!/bin/bash
# One-time setup on a Mac. Safe to run again (never overwrites her own files).
#   ./setup.sh              Python environment, folders, her own config/template files
#   ./setup.sh background   background jobs (launchd): Telegram line at login, watchdog every 5 min,
#                           Drive sync every 10 min. Run this AFTER Telegram is set up and tested.
#   ./setup.sh remove-background   turn those background jobs off again
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
LA="$HOME/Library/LaunchAgents"
JOBS="com.advisorpa.line com.advisorpa.watchdog com.advisorpa.drivesync"

say() { printf "\n\033[1m%s\033[0m\n" "$1"; }

plist() {  # label, interval-seconds (0 = at login only), command...
  local label="$1" every="$2"; shift 2
  local args=""; for a in "$@"; do args+="<string>$a</string>"; done
  local when="<key>RunAtLoad</key><true/>"
  [ "$every" != "0" ] && when+="<key>StartInterval</key><integer>$every</integer>"
  cat > "$LA/$label.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$label</string>
<key>ProgramArguments</key><array>$args</array>
<key>WorkingDirectory</key><string>$DIR</string>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.bun/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
$when
<key>StandardOutPath</key><string>$DIR/Drafts/Status/$label.log</string>
<key>StandardErrorPath</key><string>$DIR/Drafts/Status/$label.log</string>
</dict></plist>
EOF
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$LA/$label.plist"
  echo "  on: $label"
}

if [ "$1" = "background" ]; then
  mkdir -p "$LA" "$DIR/Drafts/Status"
  say "Turning on background jobs"
  plist com.advisorpa.line 0 /bin/bash "$DIR/Tools/start_line.sh"
  plist com.advisorpa.watchdog 300 "$DIR/.venv/bin/python" -X utf8 "$DIR/Tools/telegram_watchdog.py"
  plist com.advisorpa.drivesync 600 "$DIR/.venv/bin/python" -X utf8 "$DIR/Tools/drive_sync.py"
  echo "Done. They run while the Mac is awake and signed in. Turn off: ./setup.sh remove-background"
  exit 0
fi
if [ "$1" = "remove-background" ]; then
  for j in $JOBS; do launchctl bootout "gui/$(id -u)/$j" 2>/dev/null || true; rm -f "$LA/$j.plist"; echo "  off: $j"; done
  exit 0
fi

say "1/4 Checking tools"
[ "$(uname)" = "Darwin" ] || echo "Note: this setup is written for macOS."
if ! command -v brew >/dev/null; then
  echo "Homebrew is missing. Install it from https://brew.sh (one command), then run ./setup.sh again."; exit 1
fi
PYV=$(python3 -c 'import sys; print(sys.version_info >= (3, 11))' 2>/dev/null || echo False)
[ "$PYV" = "True" ] || brew install python@3.12
command -v tmux >/dev/null || brew install tmux
command -v bun >/dev/null || [ -x "$HOME/.bun/bin/bun" ] || echo "Note: the Telegram plugin needs Bun. Install: curl -fsSL https://bun.sh/install | bash"
command -v claude >/dev/null || echo "Note: Claude Code isn't on the PATH yet. Install: curl -fsSL https://claude.ai/install.sh | bash"
[ -d "/Applications/Google Chrome.app" ] || echo "Note: Google Chrome is used to make PDFs. Install it if you want PDF reports."

say "2/4 Python environment (.venv)"
PYBIN=$(command -v python3.12 || command -v python3)
[ -x .venv/bin/python ] || "$PYBIN" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
echo "  ok"

say "3/4 Folders"
mkdir -p Data/Clients Data/Investments Forms/Blank \
  Drafts/{Reminders,Follow-ups,Meetings,Analysis,Forms,"Client Reports",Investment\ Reports,Drive,Status,Jobs,Office,"Pipeline backups","Game Plan"}
echo "  ok"

say "4/4 Your own files (kept private, never part of updates)"
copy_once() { if [ -e "$2" ]; then echo "  kept:    $2"; else cp "$1" "$2"; echo "  created: $2"; fi; }
copy_once config.example.json config.json
copy_once templates/Me.example.md Me.md
copy_once templates/Preferences.example.md Preferences.md
copy_once templates/Voice.example.md Voice.md
copy_once "templates/Client Policies TEMPLATE.xlsx" "Data/Client Policies.xlsx"
copy_once templates/pipeline-TEMPLATE.csv Data/pipeline.csv
chmod +x pa update.sh setup.sh Tools/*.sh

say "Setup done."
echo "Next: open Claude Code here (type: claude) and say:  Set me up, follow SETUP-FOR-CLAUDE.md"
