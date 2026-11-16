"""Sunday-night "week ahead" message for HQ's General chat (one message, read in a minute).

  ./pa week_ahead [--meetings-file PATH] [--telegram] [--date YYYY-MM-DD]

--meetings-file: plain text, one client meeting per line (e.g. "Tue 17 Nov 7:30pm · <you> x Nelson"), written by
the scheduled task from Google Calendar. Without --telegram it only prints. Sends only to HQ.
"""
import sys, os, csv, html, datetime
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import daily_reminders as dr
import hq
import todo_list as td

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = os.path.join(ROOT, "Data", "pipeline.csv")


def opt(a, k):
    if k in a:
        i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v


def names(lst, n=6):
    lst = list(dict.fromkeys(lst))
    return ", ".join(lst[:n]) + (f" +{len(lst) - n}" if len(lst) > n else "")


def main():
    a = sys.argv[1:]
    send = "--telegram" in a
    a = [x for x in a if x != "--telegram"]
    mf, ds = opt(a, "--meetings-file"), opt(a, "--date")
    today = datetime.date.fromisoformat(ds) if ds else datetime.date.today()
    start, end = today + datetime.timedelta(1), today + datetime.timedelta(7)
    L = [f"<b>🗓 Week ahead — {start:%a %d %b} to {end:%a %d %b}</b>", ""]

    # meetings
    meet = [x.strip() for x in open(mf, encoding="utf-8")] if mf and os.path.exists(mf) else []
    meet = [x for x in meet if x]
    L.append(f"<b>📅 Client meetings ({len(meet)})</b>")
    L += [f"• {html.escape(x, quote=False)}" for x in meet] or ["• None booked yet"]

    # who to message
    items = dr.build(start, end)
    prem = [((c or {}).get("Call them") or n.title()) for _, k, n, c, _, _ in items if k == "Premium due"]
    bday = [((c or {}).get("Call them") or n.title()) for _, k, n, c, _, _ in items if k == "Birthday review"]
    st = td.load()
    fups = [it["label"] for it in st["items"].values()
            if it["status"] == "open" and it["section"] == "📌 Follow-ups" and str(start) <= it["show_from"] <= str(end)]
    _, still = td.due_today(st, today)
    still += [k for k, it in st["items"].items() if it["status"] == "open" and it["show_from"] == str(today)]
    L += ["", "<b>📲 To message this week</b>"]
    L.append(f"• 💰 {len(set(prem))} premium reminders" + (f": {html.escape(names(prem), quote=False)}" if prem else ""))
    L.append(f"• 🎂 {len(set(bday))} birthday reviews" + (f": {html.escape(names(bday), quote=False)}" if bday else ""))
    if fups:
        L.append(f"• 📌 {len(fups)} follow-ups: {html.escape(names(fups), quote=False)}")
    L.append(f"• 👋 {dr.TOP_PER_DAY} new TOP clients a day")
    if still:
        L.append(f"• ⏳ {len(still)} still open from this week")

    # pipeline focus
    with open(PIPE, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    pri = {"High": 0, "Medium": 1, "Low": 2}
    stg = {"In progress": 0, "Referral": 1, "Review due": 2, "Lead - revive": 3}
    act = [r for r in rows if r["Stage"] in stg and r["Next Action"]]
    act.sort(key=lambda r: (r["Next Action Date"] or "9999", pri.get(r["Priority"], 3), stg[r["Stage"]], r["Client"]))
    L += ["", "<b>🎯 Pipeline: top 5 next steps</b>"]
    for r in act[:5]:
        when = ""
        if r["Next Action Date"]:
            when = f" (by {datetime.date.fromisoformat(r['Next Action Date']):%a %d %b})"
        L.append(f"• {html.escape(r['Client'], quote=False)} — {html.escape(r['Next Action'], quote=False)}{when}")

    # last 7 days
    if os.path.exists(td.LOG):
        since = str(today - datetime.timedelta(6))
        log = [r for r in csv.DictReader(open(td.LOG, encoding="utf-8")) if r["Date"] >= since]
        c = Counter("skip" if r["Status"].startswith("skip") else r["Status"] for r in log)
        if log:
            L += ["", f"<b>✅ Last 7 days</b>: {c['done']} messaged · {c['skip']} skipped · {c['expired']} dropped off"]
    text = "\n".join(L)
    if not send:
        print(text); return
    token, chat, base = hq.connect()
    if not token:
        sys.exit(f"Telegram not sent: {hq.PROBLEM}")
    r = hq.api(token, "sendMessage", chat_id=chat, text=text, parse_mode="HTML", disable_web_page_preview=True)
    print("Posted week ahead to General" if r.get("ok") else f"Not sent: {r.get('description')}")


if __name__ == "__main__":
    main()
