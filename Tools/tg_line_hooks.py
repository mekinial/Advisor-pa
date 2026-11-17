"""Hooks for the Telegram line only (does nothing unless ADMIN_TEAM_LINE=telegram, set by ./pa line start / Tools/start_line.sh).

- SessionStart     : saves the line's session id (for the watchdog) and loads the recent chat back in, so a
                     restart doesn't wipe what the adviser and the PA were talking about.
- UserPromptSubmit : logs the adviser's incoming Telegram message.
- PreToolUse       : logs the PA's Telegram replies.
Log: Drafts/Status/tg-chat.jsonl (local only, last 600 lines kept). Internal working file: never share it.
"""
import sys, os, json, time, re

if os.environ.get("ADMIN_TEAM_LINE") != "telegram":
    sys.exit(0)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "Drafts", "Status")
LOG = os.path.join(DIR, "tg-chat.jsonl")
LINE = os.path.join(DIR, "tg-line.json")
os.makedirs(DIR, exist_ok=True)

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ev = d.get("hook_event_name", "")


def log(who, text):
    text = (text or "").strip()
    if not text:
        return
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": round(time.time()), "who": who, "text": text[:1500]}, ensure_ascii=False) + "\n")
    try:  # trim
        lines = open(LOG, encoding="utf-8").readlines()
        if len(lines) > 700:
            open(LOG, "w", encoding="utf-8").writelines(lines[-600:])
    except Exception:
        pass


if ev == "SessionStart":
    json.dump({"session_id": d.get("session_id", ""), "started": time.time()}, open(LINE, "w"))
    rows = []
    try:
        for ln in open(LOG, encoding="utf-8").readlines()[-40:]:
            e = json.loads(ln)
            if time.time() - e["t"] < 3 * 86400:
                when = time.strftime("%a %H:%M", time.localtime(e["t"]))
                rows.append(f"[{when}] {'Adviser' if e['who'] != 'pa' else 'You'}: {e['text'][:400]}")
    except Exception:
        pass
    ctx = ("You were restarted. Recent Telegram chat with the adviser (newest last), so you can carry the conversation on. "
           "Don't repeat old replies; if your last turn looks unfinished, finish it.\n" + "\n".join(rows)) if rows else ""
    if ctx:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))
elif ev == "UserPromptSubmit":
    p = d.get("prompt", "")
    m = re.search(r"<channel[^>]*>(.*?)</channel>", p, re.S)
    if m or "<channel" in p:
        body = m.group(1) if m else re.sub(r"<[^>]+>", "", p)
        if "image_path" in p or "attachment_file_id" in p:
            body = (body.strip() + " [sent a photo/file]").strip()
        log("adviser", body)
        try:  # keep the adviser's own words for Voice.md learning (style only; internal, local)
            t = body.strip()
            if t and "[sent a photo/file]" not in t:
                vs = os.path.join(DIR, "voice-samples.jsonl")
                with open(vs, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"t": round(time.time()), "text": t[:800]}, ensure_ascii=False) + "\n")
                lines = open(vs, encoding="utf-8").readlines()
                if len(lines) > 3500:
                    open(vs, "w", encoding="utf-8").writelines(lines[-3000:])
        except Exception:
            pass
elif ev == "PreToolUse":
    tool = d.get("tool_name", "")
    if "telegram" in tool and tool.endswith("__reply"):
        log("pa", (d.get("tool_input") or {}).get("text", ""))
