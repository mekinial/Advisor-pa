"""Telegram line watchdog. Run every 5 minutes in the background (Mac: launchd job "com.advisorpa.watchdog" from
./setup.sh background; Windows: Task Scheduler task "AdvisorPA watchdog" from setup.cmd background).
It restarts the line when:
  1. the line isn't running at all;
  2. it has waited 15+ min for an approval nobody answered (Drafts/Status/stuck-alert.json from tg_stuck_alert.py);
  3. it is hung: their last message started a turn, the turn never finished, and there has been no activity
     for 20+ min (read from the activity log Drafts/Office/events.jsonl, session id from tg-line.json).
After a restart the line reloads the recent chat (tg_line_hooks.py) and a "🔄 Back" line is posted in General.
Never starts a second copy. Logs to Drafts/Status/watchdog.log.
It also spots a line that is stuck on a start-up question (e.g. "trust this folder?") and says so once instead of
restarting it every 5 minutes, because restarting can't answer the question.
Start/stop go through Tools/line.py (Mac: hidden tmux session "pa-line"; Windows: hidden console window).
"""
import os, sys, json, time, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C
import line as L

ROOT = C.ROOT
ST = os.path.join(ROOT, "Drafts", "Status")
LOGF = os.path.join(ST, "watchdog.log")
STUCK = os.path.join(ST, "stuck-alert.json")
LINE = os.path.join(ST, "tg-line.json")
EVENTS = os.path.join(ROOT, "Drafts", "Office", "events.jsonl")
PY = C.PY
OFF = L.OFF                          # "./pa line stop" creates this so the watchdog leaves the line stopped
STARTUP_FLAG = os.path.join(ST, "startup-stuck.flag")


def log(t):
    os.makedirs(ST, exist_ok=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(time.strftime("%d/%m/%Y %H:%M:%S") + "  " + t + "\n")


def line_pids():
    return L.pids()


def start():
    L.start()


def post(text):
    C.run_hidden(PY + [os.path.join(ROOT, "Tools", "telegram_post.py"), "main", text], capture_output=True, timeout=90)


def restart(reason, note):
    log(f"Telegram line {reason} - restarting")
    L.stop(keep_on=True)
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
        return  # they stopped the line on purpose
    if not line_pids():
        log("Telegram line was down - restarted")
        start()
        return
    if os.path.exists(STUCK) and time.time() - os.path.getmtime(STUCK) > 15 * 60:
        os.remove(STUCK)
        restart("waited 15 min for an approval", "🔄 Back: a step needed your OK and nobody answered, so I skipped it "
                "and restarted. I still remember our chat; tell me if you want to retry it.")
        return
    # A copy that started after the saved session never reached SessionStart (tg_line_hooks.py writes tg-line.json),
    # so it is waiting on a start-up question in its window. Say so once; don't restart it.
    try:
        saved = json.load(open(LINE)).get("started", 0)
    except Exception:
        saved = 0
    proc = L.started_at()
    if proc and proc > saved + 60:
        if time.time() - proc > 10 * 60 and not os.path.exists(STARTUP_FLAG):
            open(STARTUP_FLAG, "w").close()
            log("Telegram line stuck at start-up (a question on screen?) - not restarting")
            post("⚠️ The Telegram line is stuck at start-up (probably a question on screen, like trusting a folder). "
                 "At the computer: ./pa line stop, then ./pa line start --visible and answer it.")
        return
    if os.path.exists(STARTUP_FLAG):
        os.remove(STARTUP_FLAG)
    m = hung_minutes()
    if m > 20:
        restart(f"hung for {m:.0f} min", "🔄 Back: I got stuck on your last message and restarted. "
                "I still remember our chat; resend it if I don't pick it up.")


if __name__ == "__main__":
    main()
