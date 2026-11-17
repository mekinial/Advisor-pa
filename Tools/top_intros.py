"""Intro + meeting-request drafts for transferred policyholders (TOP). Drafts only - nothing is sent.

Input:  Drafts/Follow-ups/top-list-YYYY-MM-DD.csv  (Name, Postal code - typed from the GE portal list)
Data:   "Client Policies.xlsx" (All Policies, Contacts)
Output: Drafts/Follow-ups/top-intros-YYYY-MM-DD.md  and  .html (tap-to-open WhatsApp links)

Reason to meet, strongest first:
  1. Lapsed hospital plan (SupremeHealth)   2. Other lapsed policy
  3. Protection plan terminated in the last 18 months
  4. Yearly / half-yearly / quarterly premium due in the next 30 days
  5. Investment-linked plan (fund update)   6. Savings / endowment plan (update)
  7. Children's plan (Junior Protector)     8. Age 50+ (retirement)   9. General intro
Usage: py top_intros.py [YYYY-MM-DD]   (date = "today" for due-date maths and file names)
"""
import sys, os, csv, datetime, calendar, html, urllib.parse
from collections import defaultdict
from openpyxl import load_workbook

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C  # this adviser's settings (config.json)
XLSX = C.POLICIES_XLSX
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Drafts", "Follow-ups")
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
FLAGS = {a for a in sys.argv[1:] if a.startswith("--")}
TODAY = datetime.date.fromisoformat(ARGS[0]) if ARGS else datetime.date.today()
STEP = {"Yearly": 12, "Half Yearly": 6, "Quarterly": 3}
DUE_WINDOW, BDAY_WINDOW, TERM_LOOKBACK = 30, 45, 548

ILP = ("INVEST ADVANTAGE", "SMART INVEST", "SMART PROTECT", "GREATLINK")
SAVINGS = ("WEALTH ADVANTAGE", "WEALTH MULTIPLIER", "FLEXI CASHBACK", "PRIME REWARDS", "CASHBACK")
PROTECTION = ("TERM", "PROTECTOR", "TOTALCARE", "SUPREMEHEALTH", "CRITICAL", "MULTIPLIER 20", "EARLY MULTIPLIER",
              "CARESHIELD", "ELDERSHIELD", "ACCIDENT", "PAYASSURE", "HOSPITAL")
SENSITIVE = ("PINKLIFE",)  # never named in client messages
# Maternity plans ARE raised (with the mother only): baby's hospital + life plan follow-up
# should happen 15 days after the due date (the adviser's rule, 12 Nov 2026).


def d(x):
    return x.date() if isinstance(x, datetime.datetime) else x


def fmt(x):
    return f"{x.day} {x:%b}"


def add_months(x, n, day):
    m = x.month - 1 + n
    y, m = x.year + m // 12, m % 12 + 1
    return datetime.date(y, m, min(day, calendar.monthrange(y, m)[1]))


def next_due(issue, step, expiry):
    k = 0
    while True:
        due = add_months(issue, k * step, issue.day)
        if expiry and due >= expiry:
            return None
        if due >= TODAY:
            return due
        k += 1


def short(p):
    """Client-friendly product name."""
    n = p.strip()
    u = n.upper()
    if "SUPREMEHEALTH" in u:
        return "SupremeHealth hospital plan"
    if "TOTALCARE" in u:
        return "TotalCare rider"
    fixed = {"PAYASSURE POLICY": "PayAssure plan", "GREATLINK SUPREMELIFE": "GreatLink SupremeLife"}
    if u in fixed:
        return fixed[u]
    keep = {"GREAT", "ADLS", "(SP)", "(RSP)", "(RP)", "(SGD)", "II", "III"}
    n = " ".join(w if w.upper() in keep or w.startswith("(") or not w.isupper() or len(w) <= 3
                 else w.capitalize() for w in n.split())
    return n.replace("Eldershield", "ElderShield").replace("Careshield", "CareShield").replace("  ", " ")


def names(lst):
    lst = list(dict.fromkeys(lst))
    return lst[0] if len(lst) == 1 else ", ".join(lst[:-1]) + " and " + lst[-1]


def has(p, keys):
    return any(k in p.upper() for k in keys)


wb = load_workbook(XLSX, read_only=True, data_only=True)
POL = list(wb["All Policies"].iter_rows(values_only=True))[1:]
CON = list(wb["Contacts"].iter_rows(values_only=True))[1:]
lists = sorted(f for f in os.listdir(OUT) if f.startswith("top-list-") and f.endswith(".csv"))
if not lists:
    raise SystemExit("No TOP list yet (Drafts/Follow-ups/top-list-YYYY-MM-DD.csv; see templates/top-list-TEMPLATE.csv).")
TOP = list(csv.DictReader(open(os.path.join(OUT, lists[-1]), encoding="utf-8")))


def match(n, full):
    return bool(full) and (full.upper() == n or full.upper().startswith(n))


people = []
for row in TOP:
    n = row["Name"].strip().upper()
    c = next((c for c in CON if match(n, c[0])), None)
    own = [p for p in POL if match(n, p[0])]
    # de-dup rows that appear twice (with/without leading zero on policy no.)
    seen, ps = set(), []
    for p in own:
        key = (str(p[1]).lstrip("0"), p[2])
        if key not in seen:
            seen.add(key); ps.append(p)
    as_la = sorted({(p[0], p[2]) for p in POL if match(n, p[10]) and not match(n, p[0])})
    full = c[0] if c else row["Name"]
    first = (row.get("Call name") or "").strip() or (c[6] if c and c[6] else None)
    mobile = c[1] if c else None
    wa = c[2] if c else None
    bday = d(c[3]) if c else None
    age = None
    if bday:
        age = TODAY.year - bday.year - ((TODAY.month, TODAY.day) < (bday.month, bday.day))
    people.append(dict(full=full, first=first, check=(c[7] if c else None), mobile=mobile, wa=wa, bday=bday,
                       age=age, postal=row["Postal code"].strip(), area=(row.get("Area") or "").strip(), flag=(row.get("Flag") or "").strip(), ps=ps, as_la=as_la))

# households: same postal code or same mobile
by_postal, by_mobile = defaultdict(list), defaultdict(list)
for p in people:
    if p["postal"]:
        by_postal[p["postal"]].append(p["full"])
    if p["mobile"]:
        by_mobile[p["mobile"]].append(p["full"])

INTRO = "Hi {n}! " + C.intro() + " 😊"
# Ask (12 Nov 2026): make the meeting normal, keep it small, offer two real free times (Tools/slots.py).
ASK = "I'm meeting all my new clients for a quick 20-min handover review. Would {a} or {b} work better? {where}"
ASK_NOSLOT = "I'm meeting all my new clients for a quick 20-min handover review. When would be a good time for you this week or next? {where}"
# Where to meet: config.json top (near_postal_sectors = first 2 digits of nearby postal codes, near_areas = street
# names for people without a postal code). Mention their area only to people living nearby; everyone else: near them or town.
NEAR_SECTORS = {str(s) for s in C.TOP["near_postal_sectors"]}  # config.json top.near_postal_sectors
WHERE_FAR = C.TOP["where_far"]
WHERE_NEAR = C.TOP["where_near"] or WHERE_FAR  # e.g. "I stay at <area>, so I'm nearby and happy to meet somewhere close to you ☺️"


NEAR_AREAS = tuple(a.upper() for a in C.TOP["near_areas"])  # config.json top.near_areas


def where(postal, area=""):
    """Near = postal sector in NEAR_SECTORS, or (no postal) the street in the TOP list's Area column is nearby."""
    pc = (postal or "").strip()
    if len(pc) == 6:
        return WHERE_NEAR if pc[:2] in NEAR_SECTORS else WHERE_FAR
    return WHERE_NEAR if any(a in (area or "").upper() for a in NEAR_AREAS) else WHERE_FAR
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slots as _slots

for i, p in enumerate(people):
    ps = p["ps"]
    infc = [x for x in ps if x[4] == "Inforce"]
    lapsed = [x for x in ps if x[4] == "Lapsed" and not has(x[2], SENSITIVE)]
    term = [x for x in ps if x[4] == "Terminated" and has(x[2], PROTECTION) and not has(x[2], SENSITIVE)
            and d(x[6]) and (TODAY - d(x[6])).days <= TERM_LOOKBACK]
    old_term = [x for x in ps if x[4] == "Terminated" and x not in term]
    dues = []
    for x in infc:
        if x[7] == "Regular" and x[8] in STEP and x[5]:
            exp = d(x[6]) if x[6] and d(x[6]).year < 9999 else None
            nd = next_due(d(x[5]), STEP[x[8]], exp)
            if nd and (nd - TODAY).days <= DUE_WINDOW and not has(x[2], SENSITIVE):
                dues.append((nd, x))
    dues.sort()
    ilp = [x for x in infc if has(x[2], ILP)]
    sav = [x for x in infc if has(x[2], SAVINGS) and not has(x[2], ILP)]
    junior = [x for x in infc if "JUNIOR" in x[2].upper()]

    n = p["first"] or "there"
    body, reason, tier = [], [], None
    if lapsed:
        hosp = [x for x in lapsed if "SUPREMEHEALTH" in x[2].upper()]
        if hosp:
            rider = [x for x in ps if "TOTALCARE" in x[2].upper() and x[4] != "Inforce"]
            extra = ", along with the TotalCare rider" if rider else ""
            body.append(f"Going through your policies, I noticed your SupremeHealth hospital plan has lapsed{extra}. "
                        "It's an important one, so I'd like to go through your options with you soon.")
            others = [x for x in lapsed if x not in hosp and "TOTALCARE" not in x[2].upper()]
            reason.append("Hospital plan LAPSED" + (" + TotalCare ended" if rider else ""))
            if others:
                reason.append("also lapsed: " + names(short(x[2]) for x in others))
            tier = 1
        else:
            pl = names(short(x[2]) for x in lapsed)
            verb = "shows" if len(set(x[2] for x in lapsed)) == 1 else "show"
            body.append(f"Going through your policies, I noticed your {pl} {verb} as lapsed. "
                        "I'd like to go through your options with you soon.")
            reason.append(f"LAPSED: {pl}")
            tier = 2
    elif term:
        pl = names(short(x[2]) for x in term)
        body.append(f"Going through your policies, I noticed your {pl} shows as terminated. "
                    "I'd like to check that was intended, and that you're still properly covered.")
        reason.append(f"TERMINATED (recent): {pl}")
        tier = 3
    mat = sorted((x for x in infc if "MATERNITY" in x[2].upper()), key=lambda x: d(x[5]))
    kids = [(x[10], d(x[13])) for x in ps if "JUNIOR" in x[2].upper() and x[13]]
    mat_open = bool(mat) and not any(dob >= d(mat[-1][5]) for _, dob in kids)
    p["mat"], p["kids"], p["mat_open"] = mat, kids, mat_open
    if mat_open:
        line = ("I saw you have a Maternity Care plan with us. I'd love to hear how you and your little one are doing, "
                "and make sure baby's hospital and life plans are in place.")
        body.append(("Also, " + line[0].lower() + line[1:]) if tier else line)
        reason.append(f"Maternity Care from {fmt(d(mat[-1][5]))} {d(mat[-1][5]).year}, no plan for baby in file: follow up hospital + life plan")
        tier = tier or 2.5
    if dues:
        nd, x = dues[0]
        if tier:
            body.append(f"Also, your {short(x[2])} premium is coming up on {fmt(nd)}.")
        else:
            body.append(f"Just a heads up, your {short(x[2])} premium is coming up on {fmt(nd)}.")
            tier = 4
        seen_p = list(dict.fromkeys(f"{fmt(a)} ({short(b[2])})" for a, b in dues))
        reason.append("Premium due " + "; ".join(seen_p[:3]) + (f" + {len(seen_p) - 3} more" if len(seen_p) > 3 else ""))
    if not tier and ilp:
        pl = names(short(x[2]) for x in ilp)
        body.append(f"I saw you have your {pl} with us, and I'd like to give you an update on how it's doing.")
        reason.append(f"Investment update: {pl}"); tier = 5
    if not tier and sav:
        k = len(sav)
        what = f"your {short(sav[0][2])} savings plan" if k == 1 else f"{'two' if k == 2 else k} savings plans"
        body.append(f"I saw you have {what} with us, and I'd like to give you an update on how {'it is' if k == 1 else 'they are'} doing.")
        reason.append(f"Savings plan update: {names(short(x[2]) for x in sav)}"); tier = 6
    if not tier and junior:
        body.append("I'll be taking care of your plans from now on, including the ones for your little one.")
        reason.append("Has Junior Protector (children's) plan"); tier = 7
    if not tier and p["age"] and p["age"] >= 65:
        body.append("I'll be taking care of your plans from now on, and I'd like to make sure everything is still "
                    "set up the way you want for you and your family.")
        reason.append(f"Age {p['age']}: review plans for self and family"); tier = 8
    elif not tier and p["age"] and p["age"] >= 50:
        body.append("I'll be taking care of your plans from now on, and I'd like to see if there's anything "
                    "you're planning for in the next few years, like retirement.")
        reason.append(f"Age {p['age']}: retirement planning"); tier = 8
    if not tier:
        if len(infc) == 1:
            body.append(f"I'll be taking care of your {short(infc[0][2])} from now on, including any claims or changes.")
            reason.append(f"Only 1 policy ({short(infc[0][2])}): coverage review")
        elif ps:
            body.append("I'll be taking care of your policies from now on, including any claims or changes.")
            reason.append("General intro / review")
        else:  # transferred to them, so they do have GE policies; just not in the workbook yet
            body.append("I'll be taking care of your policies from now on, including any claims or changes.")
            reason.append("NO POLICIES IN FILE: general intro (check GE portal)")
        tier = 9
    two = _slots.pick(i, TODAY)
    w = where(p["postal"], p.get("area", ""))
    ask = ASK.format(a=two[0], b=two[1], where=w) if two else ASK_NOSLOT.format(where=w)
    p["msg"] = "\n\n".join([INTRO.format(n=n)] + body + [ask])
    p["_parts"], p["_where"] = [INTRO.format(n=n)] + body, w  # slots redone after sorting (see below)
    p["reason"] = "; ".join(reason)
    p["tier"] = tier
    p["inforce"] = sorted({short(x[2]) for x in infc})

    checks = []
    if not p["first"]:
        checks.append("No call name in Contacts: replace \"there\" with their name")
    if p["check"]:
        checks.append("Name flagged \"Please check\": confirm what they like to be called")
    if lapsed:
        checks.append("Lapse date not in the file: check in the GE portal that reinstatement is still possible")
    if dues:
        checks.append("Check whether the premium is already on GIRO / paid")
    if tier in (5, 6):
        checks.append("Get latest policy/fund values from the GE portal before the meeting. Don't quote figures in the message")
    if old_term:
        checks.append("Older terminated/matured: " + names(short(x[2]) for x in old_term))
    if p["as_la"]:
        checks.append("Also insured under policies owned by: " + names(sorted({o for o, _ in p["as_la"]})))
    fam = [x for x in by_postal.get(p["postal"], []) if x != p["full"]]
    if fam:
        checks.append("Same address as " + names(fam) + ": consider meeting together")
    shared = [x for x in by_mobile.get(p["mobile"], []) if x != p["full"]]
    if shared:
        checks.append("SAME MOBILE as " + names(shared) + ": send one combined message")
    if not p["mobile"]:
        checks.append("No mobile number on file")
    elif not str(p["mobile"]).startswith("+65"):
        checks.append(f"Overseas number ({p['mobile']}): may be living abroad")
    if not p["ps"]:
        checks.append("Get policy details from GE portal \"View details\" to add a reason to meet")
    if p["bday"]:
        nb = p["bday"].replace(year=TODAY.year) if not (p["bday"].month == 2 and p["bday"].day == 29) else datetime.date(TODAY.year, 3, 1)
        if nb < TODAY:
            nb = nb.replace(year=TODAY.year + 1)
        if (nb - TODAY).days <= BDAY_WINDOW:
            checks.append(f"Birthday {fmt(nb)}: good second touch point if no reply")
    if p["mat_open"]:
        checks.append("Confirm the expected delivery date and that baby arrived safely before sending. "
                      "Baby's hospital + life plan follow-up is due 15 days after the due date")
    for kid, dob in p["kids"]:
        if not any(match(kid.upper(), x[10]) and x[4] == "Inforce" and has(x[2], ("SUPREMEHEALTH", "HOSPITAL")) for x in POL):
            checks.append(f"Child {kid.title()} (born {fmt(dob)} {dob.year}) has a Junior Protector but no hospital plan in the file")
    if any(has(x[2], SENSITIVE) for x in ps):
        checks.append("Has a women's (PinkLife) plan: kept out of the message on purpose")
    p["checks"] = checks

TIERS = {1: "Hospital plan lapsed", 2: "Policy lapsed", 2.5: "Maternity: baby's hospital + life plan", 3: "Policy recently terminated", 4: "Premium due in the next 30 days",
         5: "Investment update", 6: "Savings plan update", 7: "Children's plan", 8: "Retirement (age 50+)", 9: "General intro"}
people.sort(key=lambda p: (p["tier"], p["full"]))

# No double booking (14 Nov 2026): in priority order, everyone not yet on a To message list (and anyone
# holding times) gets two times nobody else holds or has been given in this run. daily_reminders.py holds
# them (slots.hold) once the person goes on the list.
try:
    import json as _json
    _shown = _json.load(open(os.path.join(os.path.expanduser("~"), ".claude", "channels", "telegram", "hq",
                                          "top-shown.json")))
except Exception:
    _shown = {}
_holds, _taken = _slots.load_holds(), set()
try:
    import csv as _csv
    _messaged = {r["Name"] for r in _csv.DictReader(open(os.path.join(OUT, "top-already-messaged.csv"), encoding="utf-8"))}
except Exception:
    _messaged = set()
# Who gets the nearest times: people already holding times, then people from earlier lists, then new people
# in list order (the next ones to be shown), so a late name on the list never pushes today's people out.
for p in sorted(people, key=lambda q: (q["full"] not in _holds, q["full"] not in _shown)):
    p["slots"] = []
    # 14 Nov 2026: people from earlier lists get times too, except those they have already WhatsApp'd
    # (top-already-messaged.csv): their intro is sent, so their message is left as it was.
    if p["full"] in _messaged and p["full"] not in _holds:
        continue
    two = _slots.pick_for(p["full"], TODAY, _taken)
    p["slots"] = [s.strftime("%Y-%m-%dT%H:%M") for s in two] if two else []
    ask = ASK.format(a=_slots.say(two[0]), b=_slots.say(two[1]), where=p["_where"]) if two \
        else ASK_NOSLOT.format(where=p["_where"])
    p["msg"] = "\n\n".join(p["_parts"] + [ask])

RANK ={t: i for i, t in enumerate(sorted(TIERS), 1)}

stamp = TODAY.isoformat()
md = [f"# TOP intro messages ({len(people)} transferred policyholders)", "",
      f"Drafts only. Nothing has been sent. Facts come from \"Client Policies.xlsx\". Dates are as of {fmt(TODAY)} {TODAY.year}.",
      "Tap-to-send version: top-intros-" + stamp + ".html (same folder).", "", "## Summary", "",
      "| Reason to meet | People |", "|---|---|"]
for t, label in TIERS.items():
    k = sum(1 for p in people if p["tier"] == t)
    if k:
        md.append(f"| {t}. {label} | {k} |")
md += ["", "## Households (same address or same mobile)", ""]
for code, lst in sorted(by_postal.items()):
    if len(lst) > 1:
        md.append(f"- {code}: {names(lst)}")
for mob, lst in by_mobile.items():
    if len(lst) > 1:
        md.append(f"- Same mobile {mob}: {names(lst)}")
md.append("")
cur = None
for k, p in enumerate(people, 1):
    if p["tier"] != cur:
        cur = p["tier"]; md += [f"## {cur}. {TIERS[cur]}", ""]
    md += [f"### {k}. {p['first'] or p['full'].title()} ({p['full']})",
           f"Why: {p['reason']}", f"In force: {', '.join(p['inforce']) or 'none in file'}", ""]
    md += ["> " + line if line else ">" for line in p["msg"].split("\n")]
    if p["checks"]:
        md += ["", "Check before sending:"] + [f"- {c}" for c in p["checks"]]
    md.append("")
if __name__ == "__main__":  # skipped when daily_reminders imports this for the daily list
    open(os.path.join(OUT, f"top-intros-{stamp}.md"), "w", encoding="utf-8").write("\n".join(md))

# HTML: one card per person with a tap-to-open WhatsApp link (message pre-filled, you still press send)
cards = []
cur = None
for k, p in enumerate(people, 1):
    if p["tier"] != cur:
        cur = p["tier"]; cards.append(f"<h2>{cur}. {html.escape(TIERS[cur])}</h2>")
    link = (p["wa"] + "?text=" + urllib.parse.quote(p["msg"])) if p["wa"] else None
    btn = f'<a class="btn" href="{html.escape(link)}" target="_blank">Open in WhatsApp</a>' if link else '<span class="warn">No mobile</span>'
    chk = "".join(f"<li>{html.escape(c)}</li>" for c in p["checks"])
    cards.append(f"""<div class="card"><label><input type="checkbox" data-k="{html.escape(p['full'])}"> <b>{k}. {html.escape(p['first'] or p['full'].title())}</b>
<span class="full">{html.escape(p['full'])}</span></label><div class="why">{html.escape(p['reason'])}</div>
<pre>{html.escape(p['msg'])}</pre>{'<ul>' + chk + '</ul>' if chk else ''}{btn}</div>""")
page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TOP intros {stamp}</title><style>
body{{font-family:system-ui,sans-serif;max-width:760px;margin:0 auto;padding:16px;background:#f6f6f8;color:#222}}
h2{{margin-top:28px;font-size:18px}} .card{{background:#fff;border-radius:10px;padding:14px;margin:10px 0;box-shadow:0 1px 3px #0002}}
.full{{color:#777;font-size:12px;margin-left:6px}} .why{{font-size:13px;color:#a33;margin:6px 0}}
pre{{white-space:pre-wrap;font-family:inherit;background:#eef7ee;padding:10px;border-radius:8px}}
ul{{font-size:13px;color:#555;padding-left:18px}} .btn{{display:inline-block;background:#25d366;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none}}
.warn{{color:#a33}} .done{{opacity:.45}}</style></head><body>
<h1>TOP intro messages</h1><p>{len(people)} people, as of {fmt(TODAY)} {TODAY.year}. Drafts only: each button opens WhatsApp with the message filled in, and you press send. Tick a box once sent (saved in this browser only).</p>
{''.join(cards)}
<script>document.querySelectorAll('input[type=checkbox]').forEach(b=>{{const k='top:'+b.dataset.k;
try{{b.checked=localStorage.getItem(k)==='1'}}catch(e){{}}const c=b.closest('.card');c.classList.toggle('done',b.checked);
b.onchange=()=>{{try{{localStorage.setItem(k,b.checked?'1':'0')}}catch(e){{}}c.classList.toggle('done',b.checked)}}}})</script></body></html>"""
if __name__ == "__main__":
    open(os.path.join(OUT, f"top-intros-{stamp}.html"), "w", encoding="utf-8").write(page)
    print(f"{len(people)} people")
    for t, label in TIERS.items():
        print(f"  {RANK[t]}. {label}: {sum(1 for p in people if p['tier'] == t)}")

# --- Telegram: one topic per reason, one message per client with a WhatsApp button --------------
# Usage: py top_intros.py [date] --telegram   (skips anyone already sent; add --resend to send all again)
TG_ICONS = {1: "🏥", 2: "⚠️", 2.5: "👶", 3: "❌", 4: "💰", 5: "📈", 6: "🏦", 7: "🧒", 8: "🌅", 9: "👋"}
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hq  # HQ Telegram: safety check + API calls (refactored 16 Nov 2026)


def tier_topic(token, chat, ids, t):
    """Thread id of the TOP topic for tier t (created on first use); ids = the top-topics.json dict."""
    return hq.named_topic(token, chat, ids, str(t), f"{TG_ICONS[t]} TOP · {TIERS[t]}")


def send_telegram():
    import json, time
    token, chat, base = hq.connect()
    if not token:
        return f"Telegram not sent: {hq.PROBLEM}"
    tf, sf = os.path.join(base, "top-topics.json"), os.path.join(base, "top-sent.json")
    ids = json.load(open(tf)) if os.path.exists(tf) else {}
    done = set() if "--resend" in FLAGS else set(json.load(open(sf)) if os.path.exists(sf) else [])
    todo = [p for p in people if p["full"] not in done]
    for t in sorted({p["tier"] for p in todo}):
        tier_topic(token, chat, ids, t)
    json.dump(ids, open(tf, "w"))
    sent = failed = 0
    for p in todo:
        who = p["first"] or p["full"].title()
        lines = [f"<b>{html.escape(who)}</b> ({html.escape(p['full'].title())})", html.escape(p["reason"])]
        lines += [f"• {html.escape(c)}" for c in p["checks"]]
        lines.append(f"<blockquote expandable>{html.escape(p['msg'])}</blockquote>")
        if not p["wa"]:
            lines.append("No mobile on file. Contact another way.")
        msg = dict(chat_id=chat, text="\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)
        if ids.get(str(p["tier"])):
            msg["message_thread_id"] = ids[str(p["tier"])]
        if p["wa"]:
            msg["reply_markup"] = {"inline_keyboard": [[{"text": "Open WhatsApp ↗", "url": p["wa"] + "?text=" + urllib.parse.quote(p["msg"])}]]}
        r = hq.api(token, "sendMessage", **msg)
        if not r.get("ok") and "message_thread_id" in msg:
            msg.pop("message_thread_id"); r = hq.api(token, "sendMessage", **msg)
        if r.get("ok"):
            sent += 1; done.add(p["full"])
            json.dump(sorted(done), open(sf, "w"))
        else:
            failed += 1; print("  failed:", p["full"], r.get("description"))
        time.sleep(1.1)
    where = "in topics" if ids else "in the main chat (Topics not turned on)"
    return f"Sent to Telegram: {sent} of {len(todo)} {where}" + (f", {failed} failed" if failed else "") + \
           (f" ({len(people) - len(todo)} already sent before, skipped)" if len(people) > len(todo) else "")


def key_check(p):
    """The one check that matters most, kept short for the digest."""
    for c in p["checks"]:
        for k, s in (("SAME MOBILE", "same phone as " + c.split("as ", 1)[-1].split(":")[0].title()),
                     ("delivery", "confirm baby arrived safely first"), ("reinstatement", "check reinstatement in portal"),
                     ("No mobile", "no mobile"), ("View details", "no policy data"), ("Overseas", "overseas number"),
                     ("Please check", "check name")):
            if k in c:
                return s
    return ""


def digest_telegram():
    """One message per topic: numbered list + one WhatsApp button per client. Replaces the previous digest."""
    import json, time
    token, chat, base = hq.connect()
    if not token:
        return f"Telegram not sent: {hq.PROBLEM}"
    tf, df = os.path.join(base, "top-topics.json"), os.path.join(base, "top-digest-ids.json")
    ids = json.load(open(tf)) if os.path.exists(tf) else {}
    only = {float(a.split("=", 1)[1]) for a in FLAGS if a.startswith("--only=")}  # e.g. --only=9: post just that topic, keep the rest
    old = json.load(open(df)) if os.path.exists(df) else []
    if not only:
        for m in old:  # replace, don't pile up
            hq.api(token, "deleteMessage", chat_id=chat, message_id=m)
    new, n = (list(old) if only else []), 0
    for t in sorted({p["tier"] for p in people}):
        if only and t not in only:
            n += sum(1 for p in people if p["tier"] == t)
            continue
        tier_topic(token, chat, ids, t)
        json.dump(ids, open(tf, "w"))
        grp = [p for p in people if p["tier"] == t]
        CH = 15  # Telegram caps the size of the button block; long WhatsApp links fit ~15 per message
        for ci in range(0, len(grp), CH):
            n = post_chunk(token, chat, ids, t, grp, ci, CH, n, new, df)
    return f"Posted topic summaries ({n} clients); message ids saved for next replace"


def post_chunk(token, chat, ids, t, grp, ci, CH, n, new, df):
    import json, time
    if True:
        part = grp[ci:ci + CH]
        cont = f", {ci + 1}–{ci + len(part)}" if len(grp) > CH else ""
        lines, buttons = [f"<b>{TG_ICONS[t]} {html.escape(TIERS[t])} ({len(grp)}{cont})</b>", ""], []
        for p in part:
            n += 1
            who = p["first"] or p["full"].title()
            what = p["reason"].split(";")[0]
            if t in (8, 9) or what.startswith(("Savings", "Investment")):
                what = ""
            chk = key_check(p)
            extra = " · ".join(x for x in (what, ("⚠️ " + chk) if chk else "") if x)
            lines.append(f"{n}. <b>{html.escape(who)}</b>" + (f" — {html.escape(extra)}" if extra else ""))
            if p["wa"]:
                buttons.append({"text": f"{n}. {who}", "url": p["wa"] + "?text=" + urllib.parse.quote(p["msg"])})
        msg = dict(chat_id=chat, text="\n".join(lines), parse_mode="HTML", disable_web_page_preview=True,
                   reply_markup={"inline_keyboard": [buttons[i:i + 2] for i in range(0, len(buttons), 2)]})
        if ids.get(str(t)):
            msg["message_thread_id"] = ids[str(t)]
        r = hq.api(token, "sendMessage", **msg)
        if r.get("ok"):
            new.append(r["result"]["message_id"])
        else:
            print("  failed:", TIERS[t], r.get("description"))
        json.dump(new, open(df, "w"))
        time.sleep(1.1)
    return n


def cleanup_blast():
    """Delete the 98 one-per-client messages sent on 12 Nov. Finds them safely: a bot message whose button
    already equals that client's exact WhatsApp link answers 'message is not modified', so nothing else is touched."""
    import json
    token, chat, base = hq.connect()
    if not token:
        return f"Telegram not sent: {hq.PROBLEM}"
    probe = hq.api(token, "sendMessage", chat_id=chat, text="Tidying up…", disable_notification=True)
    if not probe.get("ok"):
        return "Could not reach Telegram: " + str(probe.get("description"))
    top = probe["result"]["message_id"]
    hq.api(token, "deleteMessage", chat_id=chat, message_id=top)
    # Sent in `people` order, so walking ids downward meets them in reverse. Only ever try the ONE expected
    # markup: re-applying a message's own markup is a no-op ("not modified"), so nothing gets changed.
    expected = list(reversed(people))
    found, misses, mid = [], 0, top - 1
    while expected and misses < 30 and mid > top - 400:
        p = expected[0]
        mk = ({"inline_keyboard": [[{"text": "Open WhatsApp ↗", "url": p["wa"] + "?text=" + urllib.parse.quote(p["msg"])}]]}
              if p["wa"] else {"inline_keyboard": []})
        r = hq.api(token, "editMessageReplyMarkup", chat_id=chat, message_id=mid, reply_markup=mk)
        desc = str(r.get("description", ""))
        if "not modified" in desc:
            found.append(mid); expected.pop(0); misses = 0
        elif r.get("ok"):
            # a bot message without a button (e.g. a chat reply) just got one added: take it off again
            hq.api(token, "editMessageReplyMarkup", chat_id=chat, message_id=mid, reply_markup={"inline_keyboard": []})
            print(f"  skipped bot message {mid} (button added then removed)")
            misses += 1
        else:
            misses += 1  # someone else's message, or already gone
        mid -= 1
    if expected:
        return f"Stopped: matched {len(found)} of {len(people)}, next expected {expected[0]['full']}. Nothing deleted."
    deleted = sum(bool(hq.api(token, "deleteMessage", chat_id=chat, message_id=m).get("ok")) for m in found)
    return f"Deleted {deleted} of {len(people)} one-per-client messages"


if "--telegram" in FLAGS:
    print(send_telegram())
if "--digest" in FLAGS:
    print(digest_telegram())
if "--cleanup" in FLAGS:
    print(cleanup_blast())
