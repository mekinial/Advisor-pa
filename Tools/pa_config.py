"""This adviser's own settings, read from config.json in the PA folder (copy config.example.json to start).

Everything personal lives in config.json, Me.md, Preferences.md, Voice.md, Data/ and Drafts/. Those are never
part of the shared kit (see .gitignore), so updating the kit never touches them and never shares them.

    import pa_config as C
    C.ME["short_name"], C.POLICIES_XLSX, C.LISTS["no_nudge"], C.PY, C.run_hidden([...])
"""
import os, sys, json, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"
PY = [sys.executable, "-X", "utf8"]          # same Python that is running now (the kit's .venv)

DEFAULTS = {
    "me": {"full_name": "", "short_name": "", "company": "Great Eastern", "firm": "Planners Inc · Great Eastern Financial Advisers",
           "intro": "I'm {short_name} from Great Eastern, your new servicing adviser", "hq_name": "HQ"},
    "files": {"policies_xlsx": "Data/Client Policies.xlsx", "product_library": "~/Documents/GE Product Library",
              "forms_library": "~/Documents/GE Forms Library", "google_drive": ""},
    "lists": {"no_birthday_review": [], "no_nudge": [], "telegram_only": {}},
    "top": {"per_day": 5, "where_near": "", "where_far": "I can meet somewhere near you, or in town if that's easier ☺️",
            "near_postal_sectors": [], "near_areas": []},
    "schedule": {"meeting_minutes": 90,
                 "candidates": {"mon": ["12:00", "19:30"], "tue": ["12:00", "19:30"], "wed": ["12:00", "19:30"],
                                "thu": ["12:00", "19:30"], "fri": ["12:00"], "sat": ["11:00", "17:00"], "sun": ["14:00", "16:00"]},
                 "blocks": {}, "calendar_skip_words": []},
    "drive_sync": {},
}


def _merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = _merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) and k not in ("telegram_only", "drive_sync", "blocks", "candidates") else v
    return out


def load():
    f = os.path.join(ROOT, "config.json")
    user = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    return _merge(DEFAULTS, user)


CFG = load()
ME = CFG["me"]
LISTS = CFG["lists"]
TOP = CFG["top"]
SCHEDULE = CFG["schedule"]


def path(p):
    """~ and relative paths (relative = inside the PA folder)."""
    if not p:
        return ""
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


POLICIES_XLSX = path(CFG["files"]["policies_xlsx"])
PRODUCT_LIBRARY = path(CFG["files"]["product_library"])
FORMS_LIBRARY = path(CFG["files"]["forms_library"])
TG_INBOX = os.path.join(os.path.expanduser("~"), ".claude", "channels", "telegram", "inbox")


def upper_set(names):
    return {" ".join(str(n).upper().replace(",", "").split()) for n in names}


def intro():
    return ME["intro"].format(short_name=ME.get("short_name") or "your adviser", full_name=ME.get("full_name", ""))


def claude_bin():
    """The claude command line (installed by the native installer or npm)."""
    for c in (shutil.which("claude"), os.path.expanduser("~/.local/bin/claude"), os.path.expanduser("~/.claude/local/claude"),
              "/opt/homebrew/bin/claude", "/usr/local/bin/claude", os.path.expanduser("~/.local/bin/claude.exe")):
        if c and os.path.exists(c):
            return c
    return "claude"


def _flags(detach=False):
    if IS_WIN:
        return {"creationflags": 0x08000000 | (0x00000008 if detach else 0)}  # no window (+ detached)
    return {"start_new_session": True} if detach else {}


def run_hidden(cmd, **kw):
    """subprocess.run without a console window popping up on Windows."""
    return subprocess.run(cmd, **_flags(), **kw)


def start_detached(cmd, **kw):
    """Start a process that keeps running after this one exits."""
    return subprocess.Popen(cmd, **_flags(detach=True), **kw)


def pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if IS_WIN:
        out = run_hidden(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
