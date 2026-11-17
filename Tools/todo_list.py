"""the adviser's "To message" to-do list: what's on each day's list, and what they have done or skipped.

State: Drafts/Follow-ups/todo-list.json   Log: Drafts/Follow-ups/contact-log.csv
Used by daily_reminders.py (builds the daily Telegram list) and week_ahead.py, and from the chat:

  ./pa todo_list done 1 3 5          mark numbers on the latest list as done (names work too: done Jason)
  ./pa todo_list skip 2 [--days 3]   hide for N days (default 3), then it comes back
  ./pa todo_list undo 3              back to open
  ./pa todo_list add "<name>" "<what>" [--date YYYY-MM-DD]   a follow-up that shows on that day
  ./pa todo_list open                list everything still open
  ./pa todo_list replied "Tan Ah Beng", Jason   they replied: no nudge (full name = one person; commas split names)
  ./pa todo_list nudges              preview who gets a "no reply yet" nudge today

Nudges (14 Nov 2026, the adviser's ask): anyone they messaged (TOP intro, birthday review, follow-up) who hasn't been marked
"replied" NUDGE_DAYS after they marked them done gets ONE short nudge on the daily list.

Rules: anything not marked shows again under "Still open" for up to 7 days, then drops off (logged as expired).
Nothing here sends a message to anyone.
"""
import sys, os, json, csv, datetime, hashlib, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "Drafts", "Follow-ups", "todo-list.json")
LOG = os.path.join(ROOT, "Drafts", "Follow-ups", "contact-log.csv")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C  # this adviser's settings (config.json)
XLSX = C.POLICIES_XLSX
CARRY_DAYS, SKIP_DAYS, NUDGE_DAYS = 7, 3, 4
NUDGE_SECTION = "🔁 Nudge (no reply yet)"
NUDGE_FROM = "2000-01-01"  # only messages marked done from here on
NUDGE_TYPES = ("👋 New clients (TOP)", "🎂 Birthday review", "📌 Follow-ups")
NO_NUDGE = C.upper_set(C.LISTS["no_nudge"])  # config.json lists.no_nudge (friends etc. they check themselves)


def today():
    return datetime.date.today()


def load():
    if os.path.exists(STORE):
        return json.load(open(STORE, encoding="utf-8"))
    return {"items": {}, "lists": {}}


def save(st):
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    tmp = STORE + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


def log(day, item, status):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["Date", "Name", "Type", "Detail", "Status"])
        w.writerow([str(day), item["name"], item["section"], item.get("detail", ""), status])


def register(st, key, section, name, label, detail, url, flag, day=None):
    """Add an item to the list (first time only; re-runs keep its status)."""
    day = str(day or today())
    if key not in st["items"]:
        st["items"][key] = dict(section=section, name=name, label=label, detail=detail, url=url, flag=flag,
                                show_from=day, status="open", added=day)
    return st["items"][key]


def _who(it):
    return " ".join(str(it["name"]).upper().replace(",", "").split())


def add_nudges(st, day=None, dry=False):
    """Register one nudge per person whose message was marked done >= NUDGE_DAYS ago with no reply. Returns names."""
    d = day or today()
    replied = {_who(it) for it in st["items"].values() if it.get("replied")}
    nudged = {_who(it) for k, it in st["items"].items() if k.startswith("N|")}
    out = {}
    for k, it in st["items"].items():
        w = _who(it)
        if (it["section"] not in NUDGE_TYPES or it["status"] != "done" or not it.get("done")
                or it["done"] < NUDGE_FROM or w in replied or w in nudged or w in NO_NUDGE):
            continue
        if (d - datetime.date.fromisoformat(it["done"])).days >= NUDGE_DAYS:
            out.setdefault(w, it)
    for w, it in out.items():
        base = (it.get("url") or "").split("?text=")[0] or None
        first = it["label"]
        url = base
        if base and "wa.me" in base:
            url = base + "?text=" + urllib.parse.quote(f"Hi {first}, just floating this up 😊")
        if not dry:
            register(st, f"N|{w}|{it['done']}", NUDGE_SECTION, it["name"], first,
                     f"sent {datetime.date.fromisoformat(it['done']):%d %b}, no reply yet", url, "", d)
    return [it["label"] for it in out.values()]


def _words(s):
    return " ".join(str(s).upper().replace(",", " ").replace("(", " ").replace(")", " ").split()).split()


def _people_matching(st, ref):
    """People whose name or label contains every word of ref as a whole word ('Jason Woo' -> WOO KAH LOK, JASON)."""
    want = _words(ref)
    return {_who(it) for it in st["items"].values()
            if want and all(w in set(_words(it["name"]) + _words(it["label"])) for w in want)}


def resolve_refs(st, args):
    """Turn 'replied' arguments into people. A quoted or comma-separated name is matched as ONE name
    (14 Nov 2026 fix: it used to match each word separately, so 'Tan Ah Beng' also hit Calvin Tan Beng Hock).
    An unquoted 'Jason Mei' that isn't one person falls back to one person per word, only if every word is unique."""
    _, nums = latest(st) if st["lists"] else (None, {})
    people, bad = [], []
    chunks = []
    for a in args:  # a full name with a comma ("WOO KAH LOK, JASON") stays whole when it is one person
        chunks += [a] if len(_people_matching(st, a)) == 1 else a.split(",")
    chunks = [c.strip(" .") for c in chunks]
    for c in [c for c in chunks if c]:
        toks = c.split()
        if all(t.isdigit() for t in toks):
            for t in toks:
                k = nums.get(t)
                (people.append(_who(st["items"][k])) if k else bad.append(f"'{t}' is not on the latest list"))
            continue
        hit = _people_matching(st, c)
        if len(hit) == 1:
            people.append(hit.pop()); continue
        per = [_people_matching(st, t) for t in toks] if len(toks) > 1 else []
        if per and all(len(p) == 1 for p in per) and len({next(iter(p)) for p in per}) == len(per):
            people += [next(iter(p)) for p in per]
        else:
            bad.append(f"'{c}' matches {len(hit)} people")
    return list(dict.fromkeys(people)), bad


def mark_replied(st, args):
    """'replied Jason' -> every item for that person gets replied=today; open nudges for them are closed."""
    done = []
    people, bad = resolve_refs(st, args)
    for w in people:
        first = None
        for k, it in st["items"].items():
            if _who(it) != w:
                continue
            first = first or it
            if it["status"] == "done" or k.startswith("N|"):
                it["replied"] = str(today())
            if k.startswith("N|") and it["status"] == "open":
                it["status"] = "done"; it["done"] = str(today())
        log(today(), first, "replied")
        done.append(first["label"])
        if any(_who(it) == w and it["section"] == TOP_SECTION for it in st["items"].values()):
            top_to_pipeline(first)
    return done, bad


TOP_SECTION = "👋 New clients (TOP)"


def _pipeline_name(it):
    """'WOO KAH LOK, JASON' -> 'Jason Woo Kah Lok' (the way names read in the pipeline)."""
    n = it["name"]
    if "," in n:
        last, first = n.split(",", 1); n = first.strip() + " " + last.strip()
    return " ".join(p.capitalize() for p in n.split())


def top_to_pipeline(it):
    """14 Nov 2026 (the adviser): a TOP client who replies to the intro joins the pipeline as 'Review due', so they get a
    stage and a review date like their own clients. Skipped if they're already in the pipeline."""
    import subprocess
    name = _pipeline_name(it)
    r = subprocess.run(C.PY + [os.path.join(os.path.dirname(__file__), "pipeline_update.py"),
                        name, "--new", "--stage", "Review due", "--source", "TOP (transferred)",
                        "--note", "TOP client, replied to intro", "--next", "Book first review",
                        "--next-date", str(today() + datetime.timedelta(7))], capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout or r.stderr).strip().splitlines()
    print(f"Pipeline: {out[-1] if out else 'no output'}")


def due_today(st, day=None):
    """(new_today, still_open) item keys for the day's list. Expires items older than CARRY_DAYS."""
    d = day or today()
    new, old = [], []
    for k, it in st["items"].items():
        if it["status"] != "open":
            continue
        sf = datetime.date.fromisoformat(it["show_from"])
        if sf > d:
            continue
        if sf == d:
            new.append(k)
        elif (d - sf).days <= CARRY_DAYS:
            old.append(k)
        else:
            it["status"] = "expired"
            log(d, it, "expired")
    old.sort(key=lambda k: st["items"][k]["show_from"])
    return new, old


def latest(st):
    if not st["lists"]:
        sys.exit("No list has been posted yet.")
    day = max(st["lists"])
    return day, st["lists"][day]


def pick(st, nums, refs):
    """Resolve '1', '3', 'Jason' against the latest list. Returns keys, problems."""
    keys, bad = [], []
    for r in refs:
        r = r.strip(",. ")
        if not r:
            continue
        if r.isdigit():
            k = nums.get(r)
            (keys.append(k) if k else bad.append(f"no #{r} on the list"))
        else:
            hits = [k for k in nums.values() if r.lower() in (st["items"][k]["label"] + " " + st["items"][k]["name"]).lower()]
            if len(hits) == 1:
                keys.append(hits[0])
            else:
                bad.append(f"'{r}' matches {len(hits)} people")
    return keys, bad


def contacts():
    from openpyxl import load_workbook
    wb = load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb["Contacts"]
    hdr = [c.value for c in next(ws.iter_rows(max_row=1))]
    return [dict(zip(hdr, r)) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]


def find_contact(name):
    words = name.lower().split()
    hits = [c for c in contacts()
            if all(w in (str(c.get("Policyholder") or "") + " " + str(c.get("Call them") or "")).lower() for w in words)]
    return hits[0] if len(hits) == 1 else None


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd, rest = a[0].lower(), a[1:]
    st = load()
    if cmd in ("done", "skip", "undo"):
        days = SKIP_DAYS
        if "--days" in rest:
            i = rest.index("--days"); days = int(rest[i + 1]); del rest[i:i + 2]
        day, nums = latest(st)
        refs = [x for r in rest for x in r.replace(",", " ").split()]
        keys, bad = pick(st, nums, refs)
        names = []
        for k in keys:
            it = st["items"][k]
            if cmd == "done":
                it["status"] = "done"; it["done"] = str(today())
            elif cmd == "skip":
                it["status"] = "open"; it["show_from"] = str(today() + datetime.timedelta(days))
            else:
                it["status"] = "open"; it["show_from"] = min(it["show_from"], str(today()))
            log(today(), it, cmd if cmd != "skip" else f"skip {days}d")
            names.append(it["label"])
        save(st)
        verb = {"done": "Done", "skip": f"Skipped, back on {(today() + datetime.timedelta(days)):%a %d %b}", "undo": "Back to open"}[cmd]
        out = f"{verb}: {', '.join(names)}" if names else "Nothing changed"
        left = sum(1 for k in nums.values() if st["items"][k]["status"] == "open"
                   and datetime.date.fromisoformat(st["items"][k]["show_from"]) <= today())
        print(out + (f". Still open on the {day[8:]}/{day[5:7]} list: {left}" if names else "") +
              (f" (couldn't match: {'; '.join(bad)})" if bad else ""))
    elif cmd == "add":
        if len(rest) < 2:
            sys.exit('usage: add "<name>" "<what>" [--date YYYY-MM-DD]')
        d = today()
        if "--date" in rest:
            i = rest.index("--date"); d = datetime.date.fromisoformat(rest[i + 1]); del rest[i:i + 2]
        name, what = rest[0], rest[1]
        c = find_contact(name)
        url = c.get("WhatsApp link") if c and c.get("WhatsApp link") else None
        try:  # Telegram-only people (daily_reminders.TELEGRAM_ONLY)
            from daily_reminders import TELEGRAM_ONLY
            url = TELEGRAM_ONLY.get(str((c or {}).get("Policyholder", "")).upper(), url)
        except Exception:
            pass
        label = (c.get("Call them") if c and c.get("Call them") else name)
        key = "F|" + name.lower() + "|" + hashlib.md5(what.encode()).hexdigest()[:6]
        it = register(st, key, "📌 Follow-ups", (c or {}).get("Policyholder") or name, label, what, url, "", d)
        it["show_from"] = str(d); it["status"] = "open"
        save(st)
        print(f"Added: {label}, {what}, on the {d:%a %d %b} list" + ("" if url else " (no WhatsApp number on file)"))
    elif cmd == "replied":
        names, bad = mark_replied(st, rest)
        save(st)
        print((f"Replied: {', '.join(names)} (no nudge for them)" if names else "Nothing changed")
              + (f" (couldn't match: {'; '.join(bad)})" if bad else ""))
    elif cmd == "nudges":
        n = add_nudges(st, dry=True)
        print(f"Nudges today: {', '.join(n)}" if n else "No nudges due today")
    elif cmd == "open":
        new, old = due_today(st)
        later = [k for k, it in st["items"].items() if it["status"] == "open" and it["show_from"] > str(today())]
        for k in new + old:
            it = st["items"][k]; print(f"- {it['label']}: {it['section']} {it['detail']} (since {it['show_from']})")
        print(f"{len(new) + len(old)} open now, {len(later)} scheduled later")
        save(st)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
