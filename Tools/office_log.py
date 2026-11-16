"""Activity logger for the Agent Office view (Tools/office_server.py). Run by Claude Code hooks.

Reads the hook's JSON from stdin and appends ONE short line to Drafts/Office/events.jsonl:
  time, session, which agent (worked out from the files/tools it touches), what it is doing (a few words).
Never logs prompt text, file contents, commands or client details - only labels like "Writing notes".
Always exits 0 and never prints, so it can never block or slow down an agent. Local only.
"""
import sys, os, json, time, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Drafts", "Office")
EVENTS = os.path.join(OUT, "events.jsonl")
SESS = os.path.join(OUT, "sessions.json")

AGENTS = ["coordinator", "follow-up", "meeting-prep", "data-analyst", "admin-forms",
          "client-report", "proposal-writer", "investment-writer", "drive-organizer"]

# (pattern found in a path / command / tool name) -> agent.  First match wins.
RULES = [
    (r"Drafts[\\/]+Follow-ups|todo_list\.py|daily_reminders\.py|top_intros\.py|week_ahead\.py", "follow-up"),
    (r"Drafts[\\/]+Meetings|pipeline_update\.py|create_event|list_events", "meeting-prep"),
    (r"Drafts[\\/]+Analysis", "data-analyst"),
    (r"Drafts[\\/]+Forms|Forms[\\/]+Blank", "admin-forms"),
    (r"Drafts[\\/]+Client Reports|make_pdf\.py", "client-report"),
    (r"Drafts[\\/]+Game Plan", "proposal-writer"),
    (r"Drafts[\\/]+Investment Reports", "investment-writer"),
    (r"Drafts[\\/]+Drive|google_drive|[Dd]rive_", "drive-organizer"),
]

VERB = {"Read": "Reading", "Write": "Writing", "Edit": "Editing", "Grep": "Searching files", "Glob": "Looking for files",
        "WebSearch": "Searching the web", "WebFetch": "Reading a web page", "Agent": "Handing off work",
        "AskUserQuestion": "Asking the adviser a question", "Skill": "Opening a playbook"}


def label(tool, ti):
    """A few safe words: the tool's verb plus a file NAME (no folders, no content)."""
    if tool in ("Bash", "PowerShell"):
        d = (ti.get("description") or "").strip()
        return (d[:60] or "Running a command")
    if tool in ("Read", "Write", "Edit"):
        f = os.path.basename(ti.get("file_path") or "")
        return f"{VERB[tool]} {f}"[:60]
    if tool in VERB:
        return VERB[tool]
    if "telegram" in tool.lower():
        return "Telegram"
    if "calendar" in tool.lower():
        return "Checking calendar"
    if "chrome" in tool.lower() or "Browser" in tool:
        return "Using the browser"
    if "drive" in tool.lower():
        return "Google Drive"
    if "sheets" in tool.lower():
        return "Google Sheets"
    if "update_plan" in tool or "wrap_up" in tool:
        return "Updating the to-do list"
    return tool.split("__")[-1].replace("_", " ")[:40]


def place(tool, ti):
    """Which building in the Agent Town the errand happens at."""
    t, cmd = tool.lower(), str(ti.get("command", "")) + " " + str(ti.get("file_path", ""))
    if tool in ("Agent", "AskUserQuestion", "Skill") or "update_plan" in t or "wrap_up" in t or "session" in t:
        return "hq"
    if "telegram" in t or "telegram_post" in cmd or "senduserfile" in t:
        return "post"
    if "calendar" in t or "slots.py" in cmd:
        return "townhall"
    if "sheets" in t.lower() or "pipeline_update" in cmd or re.search(r"\.(csv|xlsx)\b", cmd, re.I):
        return "bank"
    if "make_pdf" in cmd or cmd.lower().strip().endswith(".pdf"):
        return "print"
    if "drive" in t.lower() or "library_search" in cmd:
        return "archive"
    if tool in ("WebSearch", "WebFetch") or "chrome" in t or "browser" in t:
        return "web"
    if tool in ("Read", "Grep", "Glob") or "library_search" in cmd:
        return "library"
    return "workshop"


def who(text):
    for pat, ag in RULES:
        if re.search(pat, text, re.I):
            return ag
    return None


def main():
    try:
        h = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return
    ev = h.get("hook_event_name", "")
    sid = (h.get("session_id") or "")[:8]
    os.makedirs(OUT, exist_ok=True)
    try:
        sess = json.load(open(SESS, encoding="utf-8"))
    except Exception:
        sess = {}
    rec = {"t": round(time.time(), 1), "s": sid, "ev": ev}
    tool = h.get("tool_name", "")
    ti = h.get("tool_input") or {}
    sub = h.get("agent_type") or ""          # set when the call comes from inside a subagent
    if ev == "PreToolUse":
        hint = " ".join(str(ti.get(k, "")) for k in ("file_path", "path", "command", "description", "subagent_type")) + " " + tool
        ag = sub if sub in AGENTS else (who(hint) or sess.get(sid) or "coordinator")
        rec.update(agent=ag, what=label(tool, ti), place=place(tool, ti))
        if tool == "Agent" and ti.get("subagent_type") in AGENTS:   # a hand-off: walk over to that desk
            rec.update(to=ti["subagent_type"], what=f"Briefing {ti['subagent_type']}")
    elif ev == "UserPromptSubmit":
        rec.update(agent=sess.get(sid, "coordinator"), what="She sent a message")
    elif ev in ("Stop", "SessionEnd"):
        rec.update(agent=sess.get(sid, "coordinator"), what="Done, waiting")
    elif ev == "SubagentStart":
        ag = sub if sub in AGENTS else "coordinator"
        rec.update(agent=ag, what="Starting work")
    elif ev == "SubagentStop":
        ag = sub if sub in AGENTS else "coordinator"
        rec.update(agent=ag, what="Finished, reporting back", to="coordinator")
    else:
        return
    if ev == "PreToolUse" and rec["agent"] != "coordinator" and not sub:
        sess[sid] = rec["agent"]                 # a chat that touched follow-up files is the follow-up desk
        try:
            json.dump(sess, open(SESS, "w", encoding="utf-8"))
        except Exception:
            pass
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    # keep the log small: trim to the last 3000 lines now and then
    if os.path.getsize(EVENTS) > 600_000:
        lines = open(EVENTS, encoding="utf-8").readlines()[-3000:]
        open(EVENTS, "w", encoding="utf-8").writelines(lines)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
