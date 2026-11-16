"""Daily WhatsApp reminder list (drafts only - nothing is sent).

Reads "Client Policies.xlsx" (sheets: All Policies, Contacts) and writes
Drafts/Reminders/reminders-YYYY-MM-DD.html with one tap-to-open WhatsApp link per client.

Rules (agreed with the adviser, 12 Nov 2026):
- Premium reminder 14 days before each due date, for in-force regular-premium policies paid
  Yearly / Half Yearly / Quarterly. Monthly and single-premium policies get none.
  General insurance (no premium status) is treated as a yearly renewal.
- Birthday review invite 30 days before the birthday.
- Only contacts with "Send reminders" = Yes (i.e. clients with policies in the file, not herself).
- No policy numbers in messages.

Usage:  py daily_reminders.py [YYYY-MM-DD] [--days N]
  default date = today; --days N previews N days starting at that date (one combined file).
  Without --days, it also catches up any days missed since the last run (max 7).
"""
import sys, os, datetime, calendar, html, urllib.parse
from collections import defaultdict
from openpyxl import load_workbook

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C  # this adviser's settings (config.json)
XLSX = C.POLICIES_XLSX
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Drafts", "Reminders")
STATE = os.path.join(OUT_DIR, "last-run.txt")
PREMIUM_LEAD, BIRTHDAY_LEAD = 14, 30
STEP = {"Yearly": 12, "Half Yearly": 6, "Quarterly": 3}
# 14 Nov 2026 (the adviser): friends / ex-advisers who get NO "birthday review" invite; they get a plain birthday
# wish on the day instead (added to the To message list by todo_list.py add). Upper-case policyholder names.
NO_BIRTHDAY_REVIEW = C.upper_set(C.LISTS["no_birthday_review"])  # config.json lists.no_birthday_review
FREQ_WORD = {"Yearly": "yearly", "Half Yearly": "half-yearly", "Quarterly": "quarterly"}


def add_months(d, n, day):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return datetime.date(y, m, min(day, calendar.monthrange(y, m)[1]))


def due_dates_between(issue, step, start, end, expiry):
    """All due dates (anniversaries of issue every `step` months) within [start, end]."""
    out, k = [], 0
    d = issue
    # jump close to start
    k = max(0, ((start.year - issue.year) * 12 + start.month - issue.month) // step - 1)
    while True:
        d = add_months(issue, k * step, issue.day)
        if d > end: break
        if d >= start and d > issue and (expiry is None or d <= expiry):
            out.append(d)
        k += 1
    return out


def fmt(d): return d.strftime("%d/%m/%Y")


def load():
    wb = load_workbook(XLSX, read_only=True, data_only=True)
    ph = wb["Contacts"]
    hdr = [c.value for c in next(ph.iter_rows(max_row=1))]
    contacts = {}
    for r in ph.iter_rows(min_row=2, values_only=True):
        rec = dict(zip(hdr, r))
        if rec.get("Send reminders") == "Yes":
            contacts[rec["Policyholder"]] = rec
    pol = wb["All Policies"]
    phdr = [c.value for c in next(pol.iter_rows(max_row=1))]
    policies = [dict(zip(phdr, r)) for r in pol.iter_rows(min_row=2, values_only=True)]
    return contacts, policies


# 14 Nov 2026 (the adviser): no WhatsApp, Telegram only. Telegram can't prefill text, so the button just opens the chat.
TELEGRAM_ONLY = {" ".join(k.upper().split()): v for k, v in C.LISTS["telegram_only"].items()}  # config.json lists.telegram_only


def wa_link(contact, text):
    if contact and str(contact.get("Policyholder", "")).upper() in TELEGRAM_ONLY:
        return TELEGRAM_ONLY[str(contact["Policyholder"]).upper()]
    link = contact.get("WhatsApp link") if contact else None
    return f"{link}?text={urllib.parse.quote(text)}" if link else None


def top_not_introduced():
    """14 Nov 2026 (the adviser): transferred (TOP) clients who haven't had her intro yet must get one in ANY first
    message (premium / birthday), config.json me.intro.
    TOP = in TOP-contacts-phone.vcf; introduced = in top-already-messaged.csv or their TOP intro marked done."""
    import re, json, csv
    fu = os.path.join(os.path.dirname(OUT_DIR), "Follow-ups")
    top, done = {}, set()
    if not os.path.exists(os.path.join(fu, "TOP-contacts-phone.vcf")):
        return {}  # optional file (vCard export of TOP clients, NOTE "Previous adviser: <name>"); none = no intro swap
    try:
        card = {}
        for line in open(os.path.join(fu, "TOP-contacts-phone.vcf"), encoding="utf-8"):
            if line.startswith("FN:"):
                card = {"fn": line[3:].strip()}
            elif line.startswith("NOTE:") and "Previous adviser:" in line:
                m = re.match(r"(.*?) \(TOP .*\)$", card.get("fn", ""))
                prev = line.split("Previous adviser:")[1].split("(")[0].strip().split()
                if m:
                    top[" ".join(m.group(1).upper().replace(",", "").split())] = prev[-1] if prev else ""
        done |= {" ".join(r["Name"].upper().replace(",", "").split())
                 for r in csv.DictReader(open(os.path.join(fu, "top-already-messaged.csv"), encoding="utf-8"))}
        st = json.load(open(os.path.join(fu, "todo-list.json"), encoding="utf-8"))
        done |= {" ".join(k[2:].upper().replace(",", "").split()) for k, v in st["items"].items()
                 if k.startswith("T|") and v.get("status") == "done"}
    except Exception as e:
        print("TOP intro check skipped:", type(e).__name__, e)
    return {n: prev for n, prev in top.items() if n not in done}


def with_intro(text, call, prev):
    """Swap the plain "Hi X," opener for the adviser's intro (TOP clients not yet introduced)."""
    who = f", taking over from {prev}" if prev else ""
    for opener in (f"Hi {call}, ", f"Hi {call}! "):
        if text.startswith(opener):
            rest = text[len(opener):]
            return (f"Hi {call}! {C.intro()}{who} \U0001F60A\n\n"
                    + rest[0].upper() + rest[1:])
    return text


def build(start, end):
    contacts, policies = load()
    intro = top_not_introduced()
    items = []  # (remind_date, kind, name, contact, text, detail)

    # premiums
    groups = defaultdict(list)
    for p in policies:
        if p["Status"] != "Inforce": continue
        if p["Premium status"] not in ("Regular", None): continue
        freq = p["Premium frequency"]
        if freq not in STEP or not p["Issue date"]: continue
        if p["Premium status"] is None and p["Policy type"] != "General": continue
        issue = p["Issue date"].date()
        exp = p["Premium expiry date"].date() if p["Premium expiry date"] else None
        if p["Policy type"] == "General": exp = None  # end of cover = renewal, not end of premiums
        for due in due_dates_between(issue, STEP[freq], start + datetime.timedelta(PREMIUM_LEAD),
                                     end + datetime.timedelta(PREMIUM_LEAD), exp):
            groups[(p["Policyholder"], due, p["Policy type"] == "General")].append((p["Product name"], freq))
    for (name, due, gi), prods in groups.items():
        c = contacts.get(name)
        call = (c or {}).get("Call them") or "there"
        products = " and ".join(sorted({x[0] for x in prods}))
        if gi:
            text = (f"Hi {call}, just a friendly reminder that your {products} "
                    f"{'policies are' if len(prods) > 1 else 'policy is'} due for renewal on {fmt(due)}. "
                    "Let me know if anything has changed or if you have any questions!")
        else:
            words = sorted({FREQ_WORD[x[1]] for x in prods})
            text = (f"Hi {call}, just a friendly reminder that the {'/'.join(words)} premium for your "
                    f"{products} is due on {fmt(due)}. Let me know if you have any questions!")
        key = " ".join(name.upper().replace(",", "").split())
        if key in intro:
            text = with_intro(text, call, intro[key])
        items.append((due - datetime.timedelta(PREMIUM_LEAD), "Premium due", name, c, text,
                      f"Due {fmt(due)} - {products}"))

    # birthdays
    for name, c in contacts.items():
        dob = c.get("Birth date")
        if not dob: continue
        if name.upper() in NO_BIRTHDAY_REVIEW: continue
        dob = dob.date()
        for y in (start.year, start.year + 1):
            try: bd = dob.replace(year=y)
            except ValueError: bd = datetime.date(y, 3, 1)  # 29 Feb
            rd = bd - datetime.timedelta(BIRTHDAY_LEAD)
            if start <= rd <= end:
                call = c.get("Call them") or name.title()
                text = (f"Hi {call}! Your birthday is coming up next month \U0001F389 Before then, I'd love to "
                        "catch up over coffee and do a quick review of your coverage, to make sure everything "
                        "still fits where you are now. Are you free sometime in the next few weeks?")
                key = " ".join(name.upper().replace(",", "").split())
                if key in intro:
                    text = with_intro(text, call, intro[key])
                items.append((rd, "Birthday review", name, c, text, f"Birthday {bd.strftime('%d %b')}"))
    items.sort(key=lambda x: (x[0], x[1], x[2]))
    return items


def write_html(items, start, end, path):
    title = f"Reminders {fmt(start)}" + (f" to {fmt(end)}" if end != start else "")
    rows = []
    for rd, kind, name, c, text, detail in items:
        link = wa_link(c, text)
        check = " <span class='chk'>check name</span>" if c and c.get("Name to check") else ""
        btn = (f"<a class='btn' href='{html.escape(link)}'>Open WhatsApp</a>" if link
               else "<span class='nolink'>No mobile on file</span>")
        rows.append(f"<div class='card'><div class='top'><span class='tag {'b' if kind.startswith('B') else 'p'}'>"
                    f"{kind}</span> <b>{html.escape(name)}</b>{check}<span class='d'>{fmt(rd)}</span></div>"
                    f"<div class='det'>{html.escape(detail)}</div><div class='msg'>{html.escape(text)}</div>{btn}</div>")
    body = "\n".join(rows) or "<p>No reminders today.</p>"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{title}</title><style>
body{{font-family:system-ui,sans-serif;max-width:720px;margin:0 auto;padding:16px;background:#f6f7f9;color:#1d2433}}
h1{{font-size:20px}} .card{{background:#fff;border-radius:10px;padding:12px 14px;margin:10px 0;box-shadow:0 1px 3px #0001}}
.top{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}} .d{{margin-left:auto;color:#667;font-size:13px}}
.tag{{font-size:12px;padding:2px 8px;border-radius:10px;color:#fff}} .p{{background:#1f4e78}} .b{{background:#c2185b}}
.det{{color:#556;font-size:13px;margin:4px 0}} .msg{{background:#eef6ee;border-radius:8px;padding:8px 10px;font-size:14px;margin:6px 0}}
.btn{{display:inline-block;background:#25d366;color:#fff;text-decoration:none;padding:7px 14px;border-radius:8px;font-weight:600}}
.nolink{{color:#a33;font-size:13px}} .chk{{background:#fff2cc;font-size:11px;padding:1px 6px;border-radius:6px}}
</style></head><body><h1>{title}</h1><p>{len(items)} message(s) to review. Tap a button to open the chat with the message typed; edit if needed, then send.</p>
{body}</body></html>""")


def main():
    args = sys.argv[1:]
    days = None
    telegram = "--telegram" in args
    if telegram: args.remove("--telegram")
    dry = "--dry" in args
    if dry: args.remove("--dry")
    if "--days" in args:
        i = args.index("--days"); days = int(args[i + 1]); del args[i:i + 2]
    today = datetime.date.fromisoformat(args[0]) if args else datetime.date.today()
    os.makedirs(OUT_DIR, exist_ok=True)
    if days:
        start, end = today, today + datetime.timedelta(days - 1)
        path = os.path.join(OUT_DIR, f"preview-{today}-{days}d.html")
    else:
        start = end = today
        if os.path.exists(STATE):
            last = datetime.date.fromisoformat(open(STATE).read().strip())
            if last < today: start = max(last + datetime.timedelta(1), today - datetime.timedelta(6))
        path = os.path.join(OUT_DIR, f"reminders-{today}.html")
    items = build(start, end)
    write_html(items, start, end, path)
    if not days:
        open(STATE, "w").write(str(today))
    n_p = sum(1 for x in items if x[1] == 'Premium due'); n_b = sum(1 for x in items if x[1] == 'Birthday review')
    print(f"{len(items)} reminders ({n_p} premium, {n_b} birthday) {fmt(start)}-{fmt(end)}")
    print(path)
    if telegram:
        print(send_telegram(items))
    elif dry:
        print(send_telegram(items, dry=True))




# Telegram lives in hq.py (refactored 16 Nov 2026). These names stay so older callers keep working.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -P runs leave Tools off the path
import hq
from hq import HQ_TOPICS, topic_id
_call = hq.api
TG_PROBLEM = None


def _tg():
    """HQ token, chat and state folder after the safety check (see hq.connect). Sets TG_PROBLEM."""
    global TG_PROBLEM
    r = hq.connect()
    TG_PROBLEM = hq.PROBLEM
    return r


TOP_PER_DAY = int(C.TOP["per_day"])  # transferred (TOP) clients added to each day's list, highest priority first


def top_today(base, today):
    """The next TOP_PER_DAY transferred clients not shown before (each person appears once).
    Re-running on the same day shows the same people. Returns (people, module globals, shown, file)."""
    import json, runpy
    f = os.path.join(base, "top-shown.json")
    shown = json.load(open(f)) if os.path.exists(f) else {}
    argv = sys.argv
    sys.argv = [argv[0]]  # top_intros reads its own flags; give it none (no files written, nothing sent)
    try:
        g = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "top_intros.py"),
                           run_name="top_lib")
    finally:
        sys.argv = argv
    people = g["people"]
    todays = {n for n, d in shown.items() if d == str(today)}
    pick = [p for p in people if p["full"] in todays] if todays else \
           [p for p in people if p["full"] not in shown][:TOP_PER_DAY]
    return pick, g, shown, f


SECTION_ORDER = ["📌 Follow-ups", "🔁 Nudge (no reply yet)", "💰 Premium due", "🎂 Birthday review", "👋 New clients (TOP)", "⏳ Still open"]


def send_telegram(items, dry=False):
    """ONE daily list in HQ's "To message" topic: follow-ups due, premium reminders, birthday reviews,
    today's TOP intros, and anything not yet marked done/skip ("Still open", up to 7 days), numbered,
    with one WhatsApp button per person (2 per row). She replies "done 1 3" / "skip 2" in General
    (todo_list.py). Splits into extra messages only if there are more than 14 people."""
    import json, time
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import todo_list as td
    day = datetime.date.today()
    token, chat, base = _tg() if not dry else (None, None, os.path.join(os.path.expanduser("~"), ".claude", "channels", "telegram", "hq"))
    if not token and not dry:
        return f"Telegram not sent: {TG_PROBLEM}"
    st = td.load()
    for rd, kind, name, c, text, detail in items:
        who = (c or {}).get("Call them") or name.title()
        if kind == "Premium due":
            due, _, prods = detail.partition(" - ")
            dd = datetime.datetime.strptime(due.replace("Due ", ""), "%d/%m/%Y")
            prods = prods if len(prods) <= 40 else prods[:38] + "…"
            key, sec, det = f"P|{name}|{dd:%Y-%m-%d}", "💰 Premium due", f"due {dd:%d %b} · {prods}"
        else:
            key, sec, det = f"B|{name}|{rd.year}", "🎂 Birthday review", detail.replace("Birthday ", "bday ")
        td.register(st, key, sec, name, who, det, wa_link(c, text),
                    "⚠️ name" if c and c.get("Name to check") else "", day)
    top, left, g, shown, sf = [], 0, None, {}, None
    try:
        top, g, shown, sf = top_today(base, day)
        left = sum(1 for p in g["people"] if p["full"] not in shown and p not in top)
    except Exception as e:  # TOP list missing or broken: still send the reminders
        print("TOP intros skipped:", type(e).__name__, e)
    for p in top:
        if p.get("slots") and not dry:  # hold their offered times so nobody else is offered them
            g["_slots"].hold(p["full"], p["slots"])
        what = p["reason"].split(";")[0]
        if p["tier"] in (8, 9) or what.startswith(("Savings", "Investment")):
            what = ""
        chk = g["key_check"](p)
        url = p["wa"] + "?text=" + urllib.parse.quote(p["msg"]) if p["wa"] else None
        td.register(st, "T|" + p["full"], "👋 New clients (TOP)", p["full"], p["first"] or p["full"].title(), what,
                    url, " · ".join(x for x in (p.get("flag", ""), ("⚠️ " + chk) if chk else "") if x), day)
    try:
        td.add_nudges(st, day)
    except Exception as e:
        print("Nudges skipped:", type(e).__name__, e)
    new, old = td.due_today(st, day)
    rows = sorted(new, key=lambda k: SECTION_ORDER.index(st["items"][k]["section"])) + old
    if not rows:
        td.save(st)
        return "Nothing to message today; no Telegram post"

    thread = topic_id(token, chat, base, "to-message") if not dry else None
    CH, sent, failed, nums = 14, 0, 0, {}
    for start in range(0, len(rows), CH):
        part = rows[start:start + CH]
        head = f"<b>📲 To message — {day:%a %d %b}</b> ({len(rows)})"
        if len(rows) > CH:
            head += f" · part {start // CH + 1}"
        lines, buttons, section = [head], [], None
        for n, k in enumerate(part, start + 1):
            it = st["items"][k]
            sec = "⏳ Still open" if k in old else it["section"]
            if sec == "👋 New clients (TOP)" and left:
                sec += f" · {left} more to come"
            if sec != section:
                section = sec
                lines += ["", f"<b>{html.escape(sec)}</b>"]
            since = f"since {datetime.date.fromisoformat(it['show_from']):%a}" if k in old else ""
            extra = " · ".join(x for x in (it["detail"], it["flag"], since, "" if it["url"] else "no mobile") if x)
            lines.append(f"{n}. {html.escape(it['label'])}" + (f" — {html.escape(extra)}" if extra else ""))
            if it["url"]:
                buttons.append({"text": f"{n}. {it['label']}", "url": it["url"]})
            nums[str(n)] = k
        lines += ["", "Tap a name: WhatsApp opens with the message ready.",
                  "Then reply in General: <code>done 1 3</code> · <code>skip 2</code> · <code>replied Jason</code> (they replied: no nudge)"]
        msg = dict(chat_id=chat, text="\n".join(lines), parse_mode="HTML", disable_web_page_preview=True,
                   reply_markup={"inline_keyboard": [buttons[i:i + 2] for i in range(0, len(buttons), 2)]})
        if thread:
            msg["message_thread_id"] = thread
        if dry:
            print(msg["text"]); print("buttons:", len(buttons)); sent += 1; continue
        r = _call(token, "sendMessage", **msg)
        sent += bool(r.get("ok"))
        failed += not r.get("ok")
        if not r.get("ok"):
            print("Telegram error:", r.get("description"))
        time.sleep(1.1)
    if dry:
        return f"DRY RUN: {len(rows)} people, nothing saved or sent"
    st["lists"][str(day)] = nums
    td.save(st)
    if top and sf and not failed:
        for p in top:
            shown.setdefault(p["full"], str(day))
        json.dump(shown, open(sf, "w"))
    return f"Sent to Telegram: {sent} message(s), {len(rows)} people ({len(new)} new, {len(old)} still open)" + \
           (f", {failed} failed" if failed else "")


if __name__ == "__main__":
    main()
