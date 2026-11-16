"""Telegram line watchdog. Run every 5 minutes by launchd (job "com.advisorpa.watchdog", set up by setup.sh).
It restarts the line when:
  1. the line isn't running at all;
  2. it has waited 15+ min for an approval nobody answered (Drafts/Status/stuck-alert.json from tg_stuck_alert.py);
  3. it is hung: her last message started a turn, the turn never finished, and there has been no activity
     for 20+ min (read from the activity log Drafts/Office/events.jsonl, session id from tg-line.json).
After a restart the line reloads the recent chat (tg_line_hooks.py) and a "🔄 Back" line is posted in General.
Never starts a second copy. Logs to Drafts/Status/watchdog.log.
The line itself runs in a hidden tmux session called "pa-line" (Tools/start_line.sh). To look at it:
tmux attach -t pa-line (leave again with Ctrl-b then d).
"""
import os, sys, json, time, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C

ROOT = C.ROOT
ST = os.path.join(ROOT, "Drafts", "Status")
LOGF = os.path.join(ST, "watchdog.log")
STUCK = os.path.join(ST, "stuck-alert.json")
LINE = os.path.join(ST, "tg-line.json")
EVENTS = os.path.join(ROOT, "Drafts", "Office", "events.jsonl")
PY = C.PY
OFF = os.path.join(ST, "line-off")   # stop_line.sh creates this so the watchdog leaves the line stopped


def log(t):
    os.makedirs(ST, exist_ok=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(time.strftime("%d/%m/%Y %H:%M:%S") + "  " + t + "\n")


def line_pids():
    out = subprocess.run(["pgrep", "-f", "claude.*--channels"], capture_output=True, text=True).stdout
    return [p for p in out.split() if p.isdigit() and int(p) != os.getpid()]


def start():
    subprocess.run(["/bin/bash", os.path.join(ROOT, "Tools", "start_line.sh")], capture_output=True, timeout=60)


def post(text):
    subprocess.run(PY + [os.path.join(ROOT, "Tools", "telegram_post.py"), "main", text], capture_output=True, timeout=90)


def restart(reason, note):
    log(f"Telegram line {reason} - restarting")
    subprocess.run(["/bin/bash", os.path.join(ROOT, "Tools", "stop_line.sh"), "--keep-on"], capture_output=True, timeout=60)
    time.sleep(4)
    start()
    time.sleep(45)
    post(note)


def hung_minutes():
    """Minutes since the line's last activity, if its current turn never finished; else 0."""
    try:
        sid = json.load(open(LINE))["session_id"][:8]
        with open(EVENTS, "rb") as f:
            f.seek(0, 2); f.seek(max(0, f.tell() - 400_000))
            lines = f.read().decode("utf-8", "ignore").splitlines()[1:]
    except Exception:
        return 0
    evs = []
    for ln in lines:
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if e.get("s") == sid:
            evs.append(e)
    if not evs:
        return 0
    last_prompt = max((i for i, e in enumerate(evs) if e["ev"] == "UserPromptSubmit"), default=-1)
    if last_prompt < 0 or any(e["ev"] == "Stop" for e in evs[last_prompt:]):
        return 0
    return (time.time() - evs[-1]["t"]) / 60


def main():
    if os.path.exists(OFF):
        return  # she stopped the line on purpose
    if not line_pids():
        log("Telegram line was down - restarted")
        start()
        return
    if os.path.exists(STUCK) and time.time() - os.path.getmtime(STUCK) > 15 * 60:
        os.remove(STUCK)
        restart("waited 15 min for an approval", "🔄 Back: a step needed your OK and nobody answered, so I skipped it "
                "and restarted. I still remember our chat; tell me if you want to retry it.")
        return
    m = hung_minutes()
    if m > 20:
        restart(f"hung for {m:.0f} min", "🔄 Back: I got stuck on your last message and restarted. "
                "I still remember our chat; resend it if I don't pick it up.")


if __name__ == "__main__":
    main()
