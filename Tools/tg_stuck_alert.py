"""Notification hook: when the Telegram line is waiting for an approval, point the adviser to the Allow/Deny buttons.

The Telegram plugin itself sends "🔐 Permission: <tool>" with ✅ Allow / ❌ Deny buttons to the adviser's PRIVATE chat with
the bot (not HQ). This hook adds a pointer in HQ General and writes Drafts/Status/stuck-alert.json.
If nobody answers within 15 minutes, Tools/telegram_watchdog.py restarts the line (chat memory is reloaded).
Does nothing unless ADMIN_TEAM_LINE=telegram. At most one pointer every 10 minutes.
"""
import sys, os, json, time, subprocess

if os.environ.get("ADMIN_TEAM_LINE") != "telegram":
    sys.exit(0)
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
kind = data.get("notification_type", "")
msg = (data.get("message") or "").strip()
if kind and kind not in ("permission_prompt", "elicitation_dialog"):
    sys.exit(0)
if not kind and "permission" not in msg.lower() and "approv" not in msg.lower():
    sys.exit(0)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
stamp = os.path.join(ROOT, "Drafts", "Status", "stuck-alert.json")
os.makedirs(os.path.dirname(stamp), exist_ok=True)
try:
    if time.time() - json.load(open(stamp)).get("t", 0) < 600:
        sys.exit(0)
except Exception:
    pass
json.dump({"t": time.time(), "msg": msg[:200]}, open(stamp, "w"))

text = ("🔐 I need your OK for one step. Tap ✅ Allow or ❌ Deny in your private chat with the bot "
        "(the bot). If there's no answer in 15 min, I'll skip it, restart and tell you here.")
subprocess.run([sys.executable, "-X", "utf8", os.path.join(ROOT, "Tools", "telegram_post.py"), "main", text],
               capture_output=True, timeout=60)
with open(os.path.join(ROOT, "Drafts", "Status", "watchdog.log"), "a", encoding="utf-8") as f:
    f.write(time.strftime("%d/%m/%Y %H:%M:%S") + f"  Telegram line waiting for approval: {msg[:150]}\n")
