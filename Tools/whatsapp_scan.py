"""WhatsApp reply check (optional; turn on with config.json "whatsapp": {"enabled": true}).

For everyone they have messaged (TOP intros, birthday reviews, follow-ups marked done), it works out WHO SENT THE
LAST MESSAGE in WhatsApp and sorts them:
  your turn  = they sent last (or there's an unread message)   -> added to their To message list
  waiting    = the adviser sent last                                   -> listed oldest first, for a nudge
  unsure     = couldn't tell, or not found in WhatsApp
Read only, always: it never opens a chat, never types, never clicks, never sends anything, and never keeps message
text. The report holds names and dates only.

How it reads WhatsApp (picked automatically by the computer it runs on):
  Mac      WhatsApp's own chat-list database on the Mac (ChatStorage.sqlite). A temporary copy is read for
           "who sent last + when + unread", then deleted; the message text column is never read.
           Needs Full Disk Access for the PA's Python once: run `./pa whatsapp_scan where` for the exact steps.
  Windows  The WhatsApp desktop chat list through Windows accessibility (what screen readers use). Only scrolls
           the list; needs WhatsApp open and signed in, and `pip install uiautomation`.

  ./pa whatsapp_scan run              full check: to-do list + CSV + report + Telegram (Admin topic)
  ./pa whatsapp_scan run --dry-run    print the sort only, change nothing
  ./pa whatsapp_scan run --no-post    everything except the Telegram post
  ./pa whatsapp_scan test             can WhatsApp be read here? (counts chats, shows no names or text)
  ./pa whatsapp_scan where            (Mac) where the database is and how to allow access
"""
import sys, os, re, csv, json, time, glob, shutil, sqlite3, tempfile, datetime, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C

ROOT = C.ROOT
TOOLS = os.path.join(ROOT, "Tools")
FU = os.path.join(ROOT, "Drafts", "Follow-ups")
CSV_PATH = os.path.join(FU, "top-already-messaged.csv")
LOG = os.path.join(FU, "contact-log.csv")
TODO = os.path.join(FU, "todo-list.json")
WCFG = C.CFG.get("whatsapp") or {}
SKIP = C.upper_set(C.LISTS.get("telegram_only", {}).keys())  # Telegram-only people are not checked
LOOKBACK_DAYS = int(WCFG.get("lookback_days", 180))
PY = C.PY


def norm(s):
    s = re.sub(r"[@,.\-’'()]", " ", str(s).upper())
    return s.split()


def core(name):
    """Name without a saved tag: 'Tan Ah Beng (TOP Mary)' -> TAN AH BENG."""
    return norm(re.sub(r"\([^)]*\)", " ", str(name)))


# ================================================================ Mac: WhatsApp's chat database
APPLE_EPOCH = datetime.datetime(2001, 1, 1)


def mac_db():
    """Path of WhatsApp's ChatStorage.sqlite on this Mac (config whatsapp.db overrides), or None."""
    if WCFG.get("db"):
        p = C.path(WCFG["db"])
        return p if os.path.exists(p) else None
    home = os.path.expanduser("~")
    pats = [os.path.join(home, "Library", "Group Containers", "group.net.whatsapp.WhatsApp.shared", "ChatStorage.sqlite"),
            os.path.join(home, "Library", "Group Containers", "*hatsApp*", "ChatStorage.sqlite"),
            os.path.join(home, "Library", "Containers", "*hatsApp*", "Data", "Library", "**", "ChatStorage.sqlite")]
    for p in pats:
        hits = sorted(glob.glob(p, recursive=True), key=lambda x: os.path.getmtime(x), reverse=True)
        if hits:
            return hits[0]
    return None


def _cols(cur, table):
    return {r[1].upper() for r in cur.execute(f"PRAGMA table_info({table})")}


def _date(v):
    try:
        return (APPLE_EPOCH + datetime.timedelta(seconds=float(v))).date() if v not in (None, "") else None
    except (TypeError, ValueError, OverflowError):
        return None


def read_mac(db=None):
    """[{name, date, who, note}] for one-to-one chats, from a temporary copy of the database (deleted after)."""
    db = db or mac_db()
    if not db:
        raise SystemExit("WhatsApp's chat database wasn't found on this Mac (is WhatsApp desktop installed and signed in?). "
                         "Run ./pa whatsapp_scan where")
    tmp = tempfile.mkdtemp(prefix="wa-")
    try:
        try:
            for ext in ("", "-wal", "-shm"):
                if os.path.exists(db + ext):
                    shutil.copy2(db + ext, os.path.join(tmp, "c.sqlite" + ext))
        except PermissionError:
            raise SystemExit("macOS blocked reading WhatsApp's database. Allow Full Disk Access for the PA's Python: "
                             "run ./pa whatsapp_scan where")
        con = sqlite3.connect(os.path.join(tmp, "c.sqlite"))
        cur = con.cursor()
        s, m = _cols(cur, "ZWACHATSESSION"), _cols(cur, "ZWAMESSAGE")
        need_s, need_m = {"Z_PK", "ZPARTNERNAME"}, {"ZCHATSESSION", "ZISFROMME", "ZMESSAGEDATE"}
        if not need_s <= s or not need_m <= m:
            raise SystemExit("WhatsApp's database layout is different from what this tool knows "
                             f"(missing: {sorted((need_s - s) | (need_m - m))}). The check needs updating for this WhatsApp version.")
        where = []
        if "ZSESSIONTYPE" in s:
            where.append("COALESCE(s.ZSESSIONTYPE, 0) = 0")          # one-to-one chats only (no groups/broadcasts)
        if "ZREMOVED" in s:
            where.append("COALESCE(s.ZREMOVED, 0) = 0")
        if "ZCONTACTJID" in s:
            where.append("COALESCE(s.ZCONTACTJID, '') NOT LIKE '%@g.us'")
            where.append("COALESCE(s.ZCONTACTJID, '') NOT LIKE '%status%'")
        unread = "COALESCE(s.ZUNREADCOUNT, 0)" if "ZUNREADCOUNT" in s else "0"
        # last real message per chat (system notices have no sender and are skipped where the type column exists)
        mtype = "AND COALESCE(m.ZMESSAGETYPE, 0) NOT IN (6, 10)" if "ZMESSAGETYPE" in m else ""
        sql = f"""
            SELECT s.ZPARTNERNAME, {unread},
                   (SELECT m.ZISFROMME FROM ZWAMESSAGE m WHERE m.ZCHATSESSION = s.Z_PK {mtype}
                    ORDER BY m.ZMESSAGEDATE DESC LIMIT 1),
                   (SELECT m.ZMESSAGEDATE FROM ZWAMESSAGE m WHERE m.ZCHATSESSION = s.Z_PK {mtype}
                    ORDER BY m.ZMESSAGEDATE DESC LIMIT 1)
            FROM ZWACHATSESSION s {('WHERE ' + ' AND '.join(where)) if where else ''}"""
        out = []
        for name, unread_n, from_me, when in cur.execute(sql):
            if not name or when is None:
                continue
            if unread_n and int(unread_n) > 0:
                who, note = "them", "unread"
            elif from_me in (1, "1", True):
                who, note = "me", ""
            elif from_me in (0, "0", False):
                who, note = "them", ""
            else:
                who, note = "unsure", "no sender on last message"
            out.append(dict(name=str(name), date=_date(when), who=who, note=note))
        con.close()
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # the copy held message text: never leave it behind


def where_help():
    db = mac_db()
    real = os.path.realpath(sys.executable)
    print("WhatsApp database: " + (db or "NOT FOUND (install WhatsApp desktop from the App Store and sign in)"))
    print("PA Python to allow:  " + real)
    print("\nTo allow it (once): System Settings > Privacy & Security > Full Disk Access > + > press Cmd+Shift+G,\n"
          "paste the Python path above, Open, and make sure its switch is on. Then run: ./pa whatsapp_scan test\n"
          "(If Homebrew later upgrades Python, the path changes and this needs doing again.)")


# ================================================================ Windows: accessibility scan of the chat list
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MEDIA = re.compile(r"^(\d+ )?(photos?|videos?|sticker|gif|audio|voice (call|message)|missed (voice|video) call|"
                   r"video (call|note)|location|live location|contact|document|poll|.*\.(pdf|docx?|xlsx?|jpe?g|png))\b", re.I)


def _window():
    import ctypes
    import uiautomation as auto
    w = auto.WindowControl(searchDepth=1, Name="WhatsApp")
    if not w.Exists(5):
        return None
    if ctypes.windll.user32.IsIconic(w.NativeWindowHandle):
        ctypes.windll.user32.ShowWindow(w.NativeWindowHandle, 4)  # SW_SHOWNOACTIVATE: restore, don't steal focus
        time.sleep(2)
    return w


def _texts(c, out, d=0):
    for ch in c.GetChildren():
        if ch.ControlTypeName in ("TextControl", "ImageControl"):
            out.append(ch)
        if d < 12:
            _texts(ch, out, d + 1)
    return out


def parse_date(s, today):
    s = s.strip().lower()
    if re.fullmatch(r"\d{1,2}:\d{2}( ?[ap]m)?", s):
        return today
    if s == "yesterday":
        return today - datetime.timedelta(1)
    if s in WEEKDAYS:
        back = (today.weekday() - WEEKDAYS.index(s)) % 7 or 7
        return today - datetime.timedelta(back)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return datetime.date(int(m[3]), int(m[2]), int(m[1]))
    return None


def read_row(r, today):
    """-> dict(name, date, who, note) or None. who: 'them' | 'me' | 'unsure'. Preview text is NOT kept.
    WhatsApp hides the ticks from accessibility, but a ticked preview starts ~20px further right than the name
    (tick icon); media previews have their own icon (~20px), so media they sent is ~40px."""
    t = _texts(r, [])
    t = [x for x in t if not re.fullmatch(r"\d+ unread messages?", x.Name or "")]
    unread = bool(re.match(r"\d+ unread message", r.Name or ""))
    texts = [x for x in t if x.ControlTypeName == "TextControl"]
    if len(texts) < 2:
        return None
    name, nr = texts[0].Name, texts[0].BoundingRectangle
    date = None
    for x in texts[1:4]:
        date = parse_date(x.Name or "", today)
        if date:
            break
    prev = [x for x in t if x.BoundingRectangle.top >= nr.bottom - 2]
    if not prev:
        return dict(name=name, date=date, who="unsure", note="no preview")
    first = (prev[0].Name or "").strip()
    joined = " ".join((x.Name or "") for x in prev).replace("\xa0", " ").strip()
    off = prev[0].BoundingRectangle.left - nr.left
    note = ""
    if unread:
        who, note = "them", "unread"
    elif re.match(r"Draft\s*:", joined) or any((x.Name or "").strip() == "Draft" for x in prev[:2]):
        who, note = "unsure", "draft hides last message"
    elif joined.startswith("You reacted"):
        who, note = "them", "you only reacted to their last message"
    elif joined.startswith("Reacted"):
        who, note = "them", "they reacted"
    elif joined.startswith("You deleted"):
        who = "me"
    elif joined.startswith("This message was deleted"):
        who = "them"
    elif off < 10:
        who = "them"
    elif off >= 32:
        who = "me"
    elif MEDIA.match(first or joined):
        who = "them"  # media icon only, no tick
    elif 14 <= off <= 28:
        who = "me"    # tick
    else:
        who, note = "unsure", f"odd layout ({off}px)"
    return dict(name=name, date=date, who=who, note=note)


def read_windows(stop_before, today, max_rounds=400):
    try:
        import uiautomation  # noqa: F401
    except ImportError:
        raise SystemExit("The Windows WhatsApp check needs one extra package: pip install uiautomation")
    w = _window()
    if not w:
        raise SystemExit("WhatsApp isn't open (or isn't signed in)")
    grid = w.DataGridControl(Name="Chat list", searchDepth=40)
    if not grid.Exists(10):
        raise SystemExit("couldn't find the WhatsApp chat list (is it on the Chats tab?)")
    for _ in range(60):  # back to the top
        rows = grid.GetChildren()
        top = rows[0]
        top.GetScrollItemPattern().ScrollIntoView(); time.sleep(0.4)
        if grid.GetChildren()[0].Name == top.Name:
            break
    seen, out = set(), []
    for _ in range(max_rounds):
        rows = grid.GetChildren()
        new = 0
        for r in rows:
            if r.Name in seen:
                continue
            seen.add(r.Name); new += 1
            try:
                info = read_row(r, today)
            except Exception:
                info = None
            if info:
                out.append(info)
        dated = [x["date"] for x in out[-15:] if x["date"]]
        if not new or (len(dated) >= 5 and max(dated) < stop_before):
            break
        rows[-1].GetScrollItemPattern().ScrollIntoView(); time.sleep(0.8)
    for _ in range(60):  # leave the list at the top again
        rows = grid.GetChildren()
        top = rows[0]
        top.GetScrollItemPattern().ScrollIntoView(); time.sleep(0.3)
        if grid.GetChildren()[0].Name == top.Name:
            break
    return out


def read_chats(stop_before, today):
    if C.IS_MAC:
        return read_mac(), "WhatsApp's chat database on this Mac"
    if C.IS_WIN:
        return read_windows(stop_before, today), "accessibility scan of the chat list"
    raise SystemExit("The WhatsApp check works on a Mac or a Windows PC only.")


# ================================================================ who they have messaged
def people():
    """{FULL NAME: earliest date messaged} from the CSV, contact-log 'done' rows and done to-do items."""
    ppl = {}

    def put(n, d):
        n = " ".join(str(n).split())
        if n and " ".join(n.upper().replace(",", "").split()) not in SKIP:
            ppl[n] = min(ppl.get(n, d), d) if d and ppl.get(n) else (d or ppl.get(n))
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8"))) if os.path.exists(CSV_PATH) else []
    for r in rows:
        put(r["Name"], r.get("Last WhatsApp") or None)
    if os.path.exists(LOG):
        for r in csv.DictReader(open(LOG, encoding="utf-8")):
            if r.get("Status") == "done":
                put(r["Name"], r["Date"])
    if os.path.exists(TODO):
        for it in json.load(open(TODO, encoding="utf-8"))["items"].values():
            if it.get("status") == "done" and not str(it.get("section", "")).startswith("🔁"):
                put(it["name"], it.get("done"))
    return ppl, rows


def match(person, chats):
    pc = set(core(person))
    best = None
    for c in chats:
        cc = set(core(c["name"]))
        if len(cc) < 2 and len(pc) > 1:
            continue
        if pc <= set(norm(c["name"])) or (len(cc) >= 2 and cc <= pc):
            score = (("TOP" in c["name"].upper()), c["date"] or datetime.date.min)
            if not best or score > best[0]:
                best = (score, c)
    return best[1] if best else None


# ================================================================ the check
def fmt(d):
    return f"{d.day} {d:%b}"


def enabled_or_exit():
    if not WCFG.get("enabled"):
        sys.exit('The WhatsApp check is off. Turn it on in config.json: "whatsapp": {"enabled": true}')


def test():
    today = datetime.date.today()
    chats, how = read_chats(today - datetime.timedelta(30), today)
    n = {k: sum(1 for c in chats if c["who"] == k) for k in ("them", "me", "unsure")}
    dated = [c["date"] for c in chats if c["date"]]
    print(f"OK: read {len(chats)} chats via {how}"
          + (f", newest {fmt(max(dated))} {max(dated).year}" if dated else "")
          + f" (they sent last: {n['them']}, you sent last: {n['me']}, unsure: {n['unsure']}). No names or text shown.")


def run(dry=False, post=True):
    enabled_or_exit()
    today = datetime.date.today()
    ppl, csv_rows = people()
    if not ppl:
        print("Nobody to check yet: no one has been marked done on the To message list.")
        return
    old = {r["Name"]: r for r in csv_rows}
    dates = [datetime.date.fromisoformat(d) for d in ppl.values() if d]
    earliest = today - datetime.timedelta(LOOKBACK_DAYS)
    stop = max(earliest, min(dates) if dates else earliest) - datetime.timedelta(3)
    chats, how = read_chats(stop, today)
    res = {p: match(p, chats) for p in ppl}
    yours = sorted([(p, c) for p, c in res.items() if c and c["who"] == "them"], key=lambda x: x[1]["date"] or today, reverse=True)
    waiting = sorted([(p, c) for p, c in res.items() if c and c["who"] == "me"], key=lambda x: x[1]["date"] or today)
    unsure = [(p, c) for p, c in res.items() if not c or c["who"] == "unsure"]
    if dry:
        for title, grp in (("YOUR TURN", yours), ("WAITING", waiting), ("UNSURE", unsure)):
            print(f"== {title} ({len(grp)})")
            for p, c in grp:
                print(f"  {p}: {fmt(c['date']) if c and c['date'] else '?'} {c['note'] if c else 'not found'}")
        dated = [x["date"] for x in chats if x["date"]]
        print(f"(read {len(chats)} chats via {how}" + (f", back to {fmt(min(dated))})" if dated else ")"))
        return
    # to-do list: only people who are newly 'your turn' (or with a newer message than last time)
    added = []
    for p, c in yours:
        o = old.get(p, {})
        d = c["date"].isoformat() if c["date"] else ""
        if o.get("Status") == "your turn" and d <= (o.get("Last WhatsApp") or ""):  # already on the list
            continue
        subprocess.run(PY + [os.path.join(TOOLS, "todo_list.py"), "replied", p], capture_output=True)
        subprocess.run(PY + [os.path.join(TOOLS, "todo_list.py"), "add", p,
                             f"Your turn: they messaged last ({fmt(c['date']) if c['date'] else '?'}), reply / move to appointment"],
                       capture_output=True)
        added.append(p)
    # CSV
    rows = {r["Name"]: dict(r) for r in csv_rows}
    for p, c in res.items():
        r = rows.setdefault(p, {"Name": p, "Last WhatsApp": ppl.get(p) or "", "Status": ""})
        if c and c["date"]:
            r["Last WhatsApp"] = max(r["Last WhatsApp"] or "", c["date"].isoformat())
        if not c:
            r["Status"] = "not found in WhatsApp list"
        elif c["who"] == "them":
            r["Status"] = "your turn"
        elif c["who"] == "me":
            r["Status"] = f"waiting since {c['date'].isoformat() if c['date'] else '?'}"
        else:
            r["Status"] = f"unsure ({c['note']})"
    out = sorted(rows.values(), key=lambda r: r["Last WhatsApp"] or "", reverse=True)
    os.makedirs(FU, exist_ok=True)
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Name", "Last WhatsApp", "Status"]); w.writeheader(); w.writerows(out)
    # report
    title = lambda p: p.title()
    moved = [title(p) for p, _ in yours if old.get(p, {}).get("Status") not in ("your turn",)]
    quiet = [title(p) for p, _ in waiting if old.get(p, {}).get("Status") == "your turn"]
    L = [f"# WhatsApp reply check, {fmt(today)} {today.year}", "",
         f"Read only ({how}; no chats opened, no message text kept). Sorted by who sent the last message.", ""]
    ch = []
    if moved: ch.append("now your turn: " + ", ".join(moved))
    if quiet: ch.append("you replied, now waiting: " + ", ".join(quiet))
    L += ["Since last check: " + ("; ".join(ch) if ch else "no change"), ""]
    L += [f"## Your turn: reply needed ({len(yours)})", "They sent the last message. Reply or move them to an appointment."]
    L += [f"- {title(p)}: {fmt(c['date']) if c['date'] else '?'}" + (f" ({c['note']})" if c["note"] else "") for p, c in yours]
    L += ["", f"## Waiting on them: nudge, oldest first ({len(waiting)})",
          "You sent the last message. A nudge should pick up where the chat stopped, not repeat the intro."]
    for p, c in waiting:
        d = c["date"]
        L.append(f"- {title(p)}: since {fmt(d)} ({(today - d).days} day{'s' if (today - d).days != 1 else ''} quiet)" if d else f"- {title(p)}: ?")
    L += ["", f"## Not found or unsure ({len(unsure)})"]
    L += [f"- {title(p)}: {c['note'] if c else 'not found in WhatsApp list'}" for p, c in unsure]
    if SKIP:
        L += [f"- {len(SKIP)} Telegram-only contact(s): not checked"]
    if added:
        L += ["", f"Added to today's To message list: {', '.join(title(p) for p in added)}"]
    path = os.path.join(FU, f"whatsapp-scan-{today.isoformat()}.md")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")
    summary = f"WhatsApp reply check: {len(yours)} your turn, {len(waiting)} waiting"
    print(summary + f" → {path}")
    if post:
        subprocess.run(PY + [os.path.join(TOOLS, "telegram_post.py"), "admin", summary, "--file", path])
    return path, summary


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["run"]:
        run(dry="--dry-run" in a, post="--no-post" not in a)
    elif a[:1] == ["test"]:
        test()
    elif a[:1] == ["where"]:
        where_help()
    else:
        sys.exit(__doc__)
