"""Case tracker (1.5.0): claims, servicing requests and pending new cases, and what each one is still waiting on.

State: Drafts/Cases/cases.json   Log: Drafts/Cases/case-log.csv   (never in Data/)
Used from the chat. Its own HQ topic "📎 Claims & servicing" gets ONE board message on days when a case
needs something (and every Monday): `./pa cases post` (run by daily_reminders.py each morning).

  ./pa cases open "<client>" claim|servicing|new "<short title>" [--item "client: signed claim form"] ...
  ./pa cases item <id> "clinic: medical report" [...]     add things it is waiting on
  ./pa cases got <id> <number or words> [...]             that item came in
  ./pa cases chased <id>                                   the adviser chased today: restart the clock
                                (same as: checked <id>, after checking a status with the insurer)
  ./pa cases submitted <id>                                everything is with the insurer now; check back later
  ./pa cases note <id> "<short line>"
  ./pa cases close <id> ["<outcome>"]
  ./pa cases ask <id>            first WhatsApp draft to the client: everything they need to send, once
  ./pa cases list [all]          open cases (all = closed ones too)
  ./pa cases show <id>
  ./pa cases due                 preview what needs doing today
  ./pa cases post [--dry] [--force]   post today's board to the Claims & servicing topic

An item is "<who>: <what>". who = client (they send or sign it), clinic (clinic/hospital report or memo),
me (the adviser has to do it), insurer (waiting on the insurance company; "ge" also works).
Chase rhythm: client every 3 days, clinic every 5, insurer every 7 (after "submitted"), "me" items show every day.
After chasing someone the adviser says "chased C3" (cases chased C3) and the clock restarts.

Rules: titles and items name the document or request, never the medical condition ("hospital claim",
"medical report"), no NRIC, policy or bank numbers. Nothing here sends a message or talks to any insurer system.
"""
import sys, os, json, csv, datetime, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C

ROOT = C.ROOT
INSURER = (C.ME.get("company") or "the insurer").strip()  # shown on the board, e.g. "with Great Eastern since 3 Dec"
STORE = os.path.join(ROOT, "Drafts", "Cases", "cases.json")
LOG = os.path.join(ROOT, "Drafts", "Cases", "case-log.csv")
KINDS = {"claim": "Claim", "servicing": "Servicing", "new": "New case"}
WHO = {"client": 3, "clinic": 5, "insurer": 7}  # days between chases (config.json cases.chase_days)
WHO.update({k: int(v) for k, v in ((C.CFG.get("cases") or {}).get("chase_days") or {}).items() if k in WHO})
WHO["me"] = 0  # the adviser's own items show every day
WHO_ALIASES = {"hospital": "clinic", "doctor": "clinic", "i": "me", "adviser": "me", "ge": "insurer",
               "company": "insurer", INSURER.lower(): "insurer", "customer": "client"}


def today():
    return datetime.date.today()


def load():
    if os.path.exists(STORE):
        return json.load(open(STORE, encoding="utf-8"))
    return {"next": 1, "cases": {}}


def save(st):
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    tmp = STORE + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


def log(case, what):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["Date", "Case", "Client", "Type", "Title", "What happened"])
        w.writerow([str(today()), case["id"], case["client"], KINDS[case["kind"]], case["title"], what])


def parse_item(text):
    who, sep, what = text.partition(":")
    w = who.strip().lower()
    w = WHO_ALIASES.get(w, w)
    if not sep or w not in WHO:
        sys.exit(f'Item must start with who it is waiting on, e.g. "client: signed form" (client, clinic, me, insurer). Got: {text}')
    return dict(who=w, what=what.strip(), asked=str(today()), got=None)


def get(st, cid):
    c = st["cases"].get(cid.upper().lstrip("#"))
    if not c:
        sys.exit(f"No case {cid}. Run: ./pa cases list")
    return c


def waiting(c):
    return [(i, it) for i, it in enumerate(c["items"], 1) if not it["got"]]


def _join(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def last_chase(c):
    """Latest day the adviser asked or chased: opened, item added, 'chased' or 'submitted'."""
    days = [c.get("chased") or c["opened"]] + [it["asked"] for _, it in waiting(c)]
    if c.get("submitted"):
        days.append(c["submitted"])
    return datetime.date.fromisoformat(max(days))


def chase_line(c, day):
    """(detail, WhatsApp message or None, due today?) for one open case."""
    wait = waiting(c)
    age = (day - datetime.date.fromisoformat(c["opened"])).days
    what = "claim" if c["kind"] == "claim" else "request" if c["kind"] == "servicing" else "application"
    since = (day - last_chase(c)).days
    head = f"{c['id']} {c['title']}: "
    if c.get("submitted") and not wait:
        sub = datetime.date.fromisoformat(c["submitted"])
        due = since >= WHO["insurer"]
        return head + f"with {INSURER} since {sub:%d %b}" + (", check the status" if due else ""), None, due
    if not wait:
        return head + "everything is in, ready for you to submit", None, True
    mine = [it["what"] for _, it in wait if it["who"] == "me"]
    theirs = [it for _, it in wait if it["who"] in ("client", "clinic")]
    ge = [it["what"] for _, it in wait if it["who"] == "insurer"]
    due = bool(mine) or any(since >= WHO[it["who"]] for it in theirs) or bool(ge and since >= WHO["insurer"])
    bits = []
    if mine:
        bits.append("you: " + _join(mine))
    cl = [it["what"] for it in theirs if it["who"] == "client"]
    cn = [it["what"] for it in theirs if it["who"] == "clinic"]
    if cl:
        bits.append("client: " + _join(cl))
    if cn:
        bits.append("clinic: " + _join(cn))
    if ge:
        bits.append(INSURER + ": " + _join(ge))
    detail = head + "waiting on " + "; ".join(bits) + (f" (day {age})" if age else "")
    msg = None
    if any(since >= WHO[it["who"]] for it in theirs):  # a message only when a chase is really due
        parts = []
        if cl:
            parts.append(f"just checking on the {_join(cl)} for your {what}")
        if cn:
            parts.append(("and " if cl else "") + f"any news from the clinic on the {_join(cn)}"
                         + ("" if cl else f" for your {what}"))
        msg = f"Hi {c['label']}, " + " ".join(parts) + ("?" if cn else "") + " 😊 Let me know if you need any help with it"
    return detail, msg, due


def board(day=None):
    """(text, buttons, open count, due count) for today's Claims & servicing board."""
    import html
    day = day or today()
    cs = [c for c in load()["cases"].values() if c["status"] == "open"]
    todo, wait_, buttons = [], [], []
    for c in cs:
        detail, msg, due = chase_line(c, day)
        (todo if due else wait_).append((c, detail, msg))
    lines = [f"<b>📎 Claims &amp; servicing — {day:%a %d %b}</b> ({len(cs)} open)"]
    if todo:
        lines += ["", "<b>To do today</b>"]
        for n, (c, detail, msg) in enumerate(todo, 1):
            lines.append(f"{n}. {html.escape(c['label'])} — {html.escape(detail)}"
                         + ("" if not msg or c.get("wa") else " · no mobile"))
            if msg and c.get("wa"):
                buttons.append({"text": f"{n}. {c['label']}", "url": c["wa"] + "?text=" + urllib.parse.quote(msg)})
    if wait_:
        lines += ["", "<b>Waiting, nothing to do today</b>"]
        lines += [f"• {html.escape(c['label'])} — {html.escape(detail)}" for c, detail, _ in wait_]
    lines += ["", "Tap a name: WhatsApp opens with the chase message ready.",
              "Then tell me in General: <code>chased C1</code> · <code>got C1 signed form</code> · "
              "<code>submitted C1</code> · <code>close C1</code>"]
    return "\n".join(lines), buttons, len(cs), len(todo)


def post(dry=False, force=False):
    """One board message in the Claims & servicing topic, only when something needs doing (or Monday, or --force)."""
    text, buttons, n_open, n_due = board()
    if not n_open:
        return "No open cases; nothing posted"
    st = load()
    if st.get("posted") == str(today()) and not (force or dry):
        return "Cases board already posted today (use --force to post again)"
    if not (n_due or force or today().weekday() == 0):
        return f"{n_open} open case(s), nothing to do today; nothing posted"
    if dry:
        print(text); print("buttons:", len(buttons))
        return f"DRY RUN: {n_open} open, {n_due} to do today, nothing sent"
    import hq
    token, chat, base = hq.connect()
    if not token:
        return f"Not sent: {hq.PROBLEM}"
    msg = dict(chat_id=chat, text=text, parse_mode="HTML", disable_web_page_preview=True,
               reply_markup={"inline_keyboard": [buttons[i:i + 2] for i in range(0, len(buttons), 2)]})
    thread = hq.topic_id(token, chat, base, "cases")
    if thread:
        msg["message_thread_id"] = thread
    r = hq.api(token, "sendMessage", **msg)
    if r.get("ok"):
        st["posted"] = str(today()); save(st)
    return (f"Posted to Claims & servicing: {n_open} open, {n_due} to do today" if r.get("ok")
            else f"Telegram error: {r.get('description')}")


def find_contact(name):
    try:
        import todo_list as td
        c = td.find_contact(name)
    except Exception:
        c = None
    if not c:
        return name, name.split()[0].title(), None
    wa = c.get("WhatsApp link") or None
    try:
        from daily_reminders import TELEGRAM_ONLY
        wa = TELEGRAM_ONLY.get(str(c.get("Policyholder", "")).upper(), wa)
    except Exception:
        pass
    return c.get("Policyholder") or name, c.get("Call them") or name.split()[0].title(), wa


def show(c):
    out = [f"{c['id']} · {KINDS[c['kind']]} · {c['label']} ({c['client']}) · {c['title']} · opened {c['opened']}"
           + (f" · submitted {c['submitted']}" if c.get("submitted") else "")
           + (f" · CLOSED {c['closed']}: {c.get('outcome', '')}" if c["status"] == "closed" else "")]
    for i, it in enumerate(c["items"], 1):
        out.append(f"   {i}. [{'x' if it['got'] else ' '}] {it['who']}: {it['what']}"
                   + (f" (in {it['got']})" if it["got"] else f" (asked {it['asked']})"))
    for n in c.get("notes", []):
        out.append(f"   note {n}")
    return "\n".join(out)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd, rest = a[0].lower(), a[1:]
    st = load()
    if cmd == "open":
        items = []
        while "--item" in rest:
            i = rest.index("--item"); items.append(parse_item(rest[i + 1])); del rest[i:i + 2]
        if len(rest) < 3 or rest[1].lower() not in KINDS:
            sys.exit('usage: open "<client>" claim|servicing|new "<short title>" [--item "client: ..."]')
        full, label, wa = find_contact(rest[0])
        cid = f"C{st['next']}"; st["next"] += 1
        c = dict(id=cid, client=full, label=label, wa=wa, kind=rest[1].lower(), title=rest[2], opened=str(today()),
                 status="open", items=items, notes=[])
        st["cases"][cid] = c
        save(st); log(c, "opened" + (f" with {len(items)} item(s)" if items else ""))
        print(f"Opened {cid}: {label}, {c['title']} ({KINDS[c['kind']].lower()}), waiting on {len(items)} item(s)"
              + ("" if wa else " · no WhatsApp number on file"))
    elif cmd == "item" and len(rest) >= 2:
        c = get(st, rest[0])
        new = [parse_item(t) for t in rest[1:]]
        c["items"] += new
        save(st); log(c, "added: " + "; ".join(f"{i['who']}: {i['what']}" for i in new))
        print(f"{c['id']}: added {len(new)}, now waiting on {len(waiting(c))}")
    elif cmd == "got" and len(rest) >= 2:
        c = get(st, rest[0]); hit = []
        for r in rest[1:]:
            w = waiting(c)
            m = [it for i, it in w if str(i) == r] or [it for i, it in w if r.lower() in it["what"].lower()]
            if len(m) != 1:
                print(f"'{r}' matches {len(m)} waiting items"); continue
            m[0]["got"] = str(today()); hit.append(m[0]["what"])
        save(st)
        if hit:
            log(c, "received: " + "; ".join(hit))
        left = waiting(c)
        print(f"{c['id']}: got {_join(hit) if hit else 'nothing'}. "
              + (f"Still waiting on {_join(f'{it['who']}: {it['what']}' for _, it in left)}" if left
                 else "Everything is in: ready to submit (then: cases submitted " + c["id"] + ")"))
    elif cmd in ("chased", "checked") and rest:
        c = get(st, rest[0]); c["chased"] = str(today())
        save(st); log(c, "chased")
        print(f"{c['id']}: chased today, clock restarted")
    elif cmd == "submitted" and rest:
        c = get(st, rest[0]); c["submitted"] = str(today())
        for _, it in waiting(c):
            if it["who"] == "me":
                it["got"] = str(today())
        save(st); log(c, "submitted to " + INSURER)
        print(f"{c['id']}: marked submitted. I'll remind you to check the status in {WHO['insurer']} days")
    elif cmd == "note" and len(rest) >= 2:
        c = get(st, rest[0]); c.setdefault("notes", []).append(f"{today()}: {rest[1]}")
        save(st); log(c, "note: " + rest[1])
        print(f"{c['id']}: noted")
    elif cmd == "close" and rest:
        c = get(st, rest[0]); c["status"] = "closed"; c["closed"] = str(today())
        c["outcome"] = rest[1] if len(rest) > 1 else ""
        save(st); log(c, "closed" + (": " + c["outcome"] if c["outcome"] else ""))
        days = (today() - datetime.date.fromisoformat(c["opened"])).days
        print(f"{c['id']} closed after {days} day(s): {c['label']}, {c['title']}")
    elif cmd == "ask" and rest:
        c = get(st, rest[0])
        cl = [it["what"] for _, it in waiting(c) if it["who"] == "client"]
        cn = [it["what"] for _, it in waiting(c) if it["who"] == "clinic"]
        if not cl and not cn:
            sys.exit(f"{c['id']}: nothing is waiting on the client or clinic")
        what = "claim" if c["kind"] == "claim" else "request" if c["kind"] == "servicing" else "application"
        lines = [f"Hi {c['label']}, for your {what} I'll need these from you:"]
        lines += [f"{n}. {w[0].upper() + w[1:]}" for n, w in enumerate(cl, 1)]
        if cn:
            lines.append(("Also from" if cl else "From") + " the clinic/hospital: " + _join(cn))
        lines.append("You can just send photos here. Once I have everything I'll submit it for you 😊")
        msg = "\n".join(lines)
        print(msg)
        print("\nWhatsApp: " + (c["wa"] + "?text=" + urllib.parse.quote(msg) if c.get("wa") else "no number on file"))
    elif cmd == "list":
        cs = [c for c in st["cases"].values() if c["status"] == "open" or "all" in rest]
        for c in cs:
            print(show(c))
        print(f"{sum(c['status'] == 'open' for c in cs)} open case(s)")
    elif cmd == "show" and rest:
        print(show(get(st, rest[0])))
    elif cmd == "due":
        n = 0
        for c in st["cases"].values():
            if c["status"] != "open":
                continue
            detail, msg, due = chase_line(c, today())
            if due:
                n += 1; print(f"- {c['label']} — {detail}" + (f"\n    msg: {msg}" if msg else ""))
        print(f"{n} to do today")
    elif cmd == "post":
        print(post(dry="--dry" in rest, force="--force" in rest))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
