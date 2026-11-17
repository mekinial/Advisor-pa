"""Shared status board + away mode for the Admin Team (every chat, desktop or Telegram).

  ./pa hq_status start <agent> "<what>"     a longer task has started
  ./pa hq_status done  <agent> "<what>"     a task is finished (say where the result is)
  ./pa hq_status needs <agent> "<what>"     something waits for the adviser's yes / input
  ./pa hq_status show [--hours 24]          what happened recently (answer "what's the status?")
  ./pa hq_status away on|off|status         the adviser is out (on) / back at the desk (off)

Every line goes to Drafts/Status/board.jsonl. While away mode is ON, start/done/needs are ALSO posted to
HQ on Telegram, in the agent's topic (via telegram_post.py), so they can follow from their phone.
"needs" is always posted when away. Keep <what> to one short line: no NRIC, policy numbers, bank or health details.
"""
import sys, os, json, time, subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "Drafts", "Status")
BOARD = os.path.join(DIR, "board.jsonl")
AWAY = os.path.join(DIR, "away.json")
POST = os.path.join(ROOT, "Tools", "telegram_post.py")

# agent -> telegram_post.py target (topic)
TOPIC = {
    "coordinator": "main", "main": "main", "drive-organizer": "main",
    "follow-up": "follow-up", "data-analyst": "data-analyst", "admin-forms": "admin-forms",
    "client-report": "reports", "proposal-writer": "reports", "investment-writer": "reports", "reports": "reports",
    "meeting-prep": "meetings", "meetings": "meetings", "marketing": "marketing",
}
ICON = {"start": "⏳", "done": "✅", "needs": "🙋 Needs you:"}


def away():
    try:
        return json.load(open(AWAY, encoding="utf-8")).get("on", False)
    except Exception:
        return False


def post(agent, text):
    r = subprocess.run([sys.executable, "-X", "utf8", POST, TOPIC.get(agent, "main"), text],
                       capture_output=True, text=True, timeout=90)
    return (r.stdout or r.stderr).strip()


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    os.makedirs(DIR, exist_ok=True)
    cmd = a[0]
    if cmd == "away":
        mode = a[1] if len(a) > 1 else "status"
        if mode in ("on", "off"):
            json.dump({"on": mode == "on", "since": datetime.now().isoformat(timespec="minutes")},
                      open(AWAY, "w", encoding="utf-8"))
        print(f"Away mode is {'ON: updates go to Telegram' if away() else 'OFF: updates stay on the desktop'}")
        return
    if cmd == "show":
        hours = float(a[a.index("--hours") + 1]) if "--hours" in a else 24
        cut = time.time() - hours * 3600
        rows = []
        try:
            for ln in open(BOARD, encoding="utf-8"):
                try:
                    e = json.loads(ln)
                except ValueError:
                    continue
                if e["t"] >= cut:
                    rows.append(e)
        except FileNotFoundError:
            pass
        if not rows:
            print(f"Nothing logged in the last {hours:g} h."); return
        # open = started but not done (same agent) + all needs not followed by a done
        for e in rows[-40:]:
            when = datetime.fromtimestamp(e["t"]).strftime("%a %H:%M")
            print(f"{when}  {ICON[e['kind']]} {e['agent']}: {e['what']}")
        print(f"\nAway mode: {'ON' if away() else 'OFF'}")
        return
    if cmd in ICON and len(a) >= 3:
        agent, what = a[1], " ".join(a[2:]).strip()[:300]
        rec = {"t": round(time.time()), "kind": cmd, "agent": agent, "what": what}
        with open(BOARD, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if away():
            print("Logged. " + post(agent, f"{ICON[cmd]} {agent}: {what}"))
        else:
            print("Logged (away mode off, not posted).")
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
