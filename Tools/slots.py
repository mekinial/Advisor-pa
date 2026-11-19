"""Pick two meeting times to offer in intro messages ("Tue 17 Nov, 7.30pm or Sat 21 Nov, 11am").

Their weekly rules come from config.json "schedule" (set up with them, edit any time):
- candidates: start times that may be offered per weekday (24h), e.g. "tue": ["11:00", "19:30"].
- blocks: times never offered per weekday, e.g. "fri": [["19:00", "23:59"]] for a standing evening plan.
- meeting_minutes: meeting + travel buffer (default 90).
Plus anything busy in Google Calendar: Drafts/Reminders/busy.json, written each morning by the 8am task
([{"start": "2026-11-18T09:00", "end": "2026-11-18T21:00", "title": "..."}], all-day busy days as 00:00-23:59).

Offers one weekday slot + one weekend slot where possible, 2 to 10 days ahead, and rotates the choice per
person so five people don't all get the same two times.
"""
import os, json, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUSY = os.path.join(ROOT, "Drafts", "Reminders", "busy.json")
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C
LEN = datetime.timedelta(minutes=int(C.SCHEDULE.get("meeting_minutes", 90)))  # meeting + travel buffer
_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
# weekday -> candidate start times (24h). Mon=0 ... Sun=6
CANDIDATES = {i: list(C.SCHEDULE.get("candidates", {}).get(d, [])) for i, d in enumerate(_DAYS)}
RULE_BLOCKS = {i: [tuple(b) for b in C.SCHEDULE.get("blocks", {}).get(d, [])] for i, d in enumerate(_DAYS)}  # weekday -> [(start, end)]


def _t(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    return datetime.datetime.combine(day, datetime.time(h, m))


def busy_ranges():
    out = []
    if os.path.exists(BUSY):
        try:
            for e in json.load(open(BUSY, encoding="utf-8")):
                out.append((datetime.datetime.fromisoformat(e["start"]), datetime.datetime.fromisoformat(e["end"])))
        except Exception:
            pass
    return out


def free_slots(today=None, lo=2, hi=10):
    today = today or datetime.date.today()
    busy = busy_ranges()
    slots = []
    for k in range(lo, hi + 1):
        day = today + datetime.timedelta(k)
        for hhmm in CANDIDATES.get(day.weekday(), []):
            s = _t(day, hhmm); e = s + LEN
            blocks = [(_t(day, a), _t(day, b)) for a, b in RULE_BLOCKS.get(day.weekday(), [])] + busy
            if all(e <= bs or s >= be for bs, be in blocks):
                slots.append(s)
    return slots


def say(s):
    h = s.hour % 12 or 12
    t = f"{h}{'.%02d' % s.minute if s.minute else ''}{'am' if s.hour < 12 else 'pm'}"
    return f"{s:%a} {s.day} {s:%b} at {t}"


def pick(i=0, today=None):
    """Two offers for person number i: (weekday slot, Saturday slot), rotated. Strings, or None if none free."""
    sl = free_slots(today)
    wk = [s for s in sl if s.weekday() < 5]
    sat = [s for s in sl if s.weekday() >= 5]  # weekend: Sat or Sun afternoon
    if wk and sat:
        a, b = sorted([wk[i % min(len(wk), 4)], sat[i % min(len(sat), 4)]])
    elif len(sl) >= 2:
        a, b = sl[(2 * i) % len(sl)], sl[(2 * i + 1) % len(sl)]
        a, b = min(a, b), max(a, b)
    else:
        return None
    return say(a), say(b)


# --- Held slots (14 Nov 2026: "don't want to double book") -------------------------------------------
# Once a time is offered to someone (their intro goes on the To message list), it is held for them in
# Drafts/Reminders\slot-holds.json and never offered to anyone else until it has passed.
# {"FULL NAME": ["2026-11-19T19:30", "2026-11-21T11:00"]}
HOLDS = os.path.join(ROOT, "Drafts", "Reminders", "slot-holds.json")


def load_holds():
    try:
        return json.load(open(HOLDS, encoding="utf-8"))
    except Exception:
        return {}


def hold(name, slots):
    """Hold these times (datetimes or ISO strings) for this person. Replaces their earlier hold."""
    h = load_holds()
    h[name] = [s if isinstance(s, str) else s.strftime("%Y-%m-%dT%H:%M") for s in slots]
    os.makedirs(os.path.dirname(HOLDS), exist_ok=True)
    json.dump(h, open(HOLDS, "w", encoding="utf-8"), indent=1)


from collections import Counter
_USE = Counter()  # how often each time was offered in this run


def replied_names():
    """People who have replied (todo_list 'replied'), upper-case, spaces normalised."""
    try:
        st = json.load(open(os.path.join(ROOT, "Drafts", "Follow-ups", "todo-list.json"), encoding="utf-8"))
    except Exception:
        return set()
    return {" ".join(str(it["name"]).upper().replace(",", "").split()) for it in st.get("items", {}).values() if it.get("replied")}


def pick_for(name, today=None, taken=None, hi=14):
    """Two different times for this person: (weekday, weekend) where possible, as soon as possible.

    1.4.6 (19 Nov 2026): appointments are aimed within the next week or two. A time offered to someone who
    hasn't replied or confirmed counts as open again:
    - Another person's held times only block if that person has REPLIED (an open conversation). Confirmed
      meetings are in Google Calendar (busy.json) anyway.
    - Their own hold is reused only if both times are still free AND within the next `hi` days.
    - Times already given out in this run (`taken`) are avoided where possible, but never at the cost of pushing
      someone past `hi` days: then the least-offered times are reused.
    - Only if the next `hi` days are truly full (calendar + rules + replied holds) does it look further ahead.
    Returns [datetime, datetime] or None."""
    today = today or datetime.date.today()
    taken = taken if taken is not None else set()
    sl = free_slots(today, 2, hi)
    now = datetime.datetime.combine(today, datetime.time(0))
    holds = load_holds()
    replied = replied_names()
    norm = lambda n: " ".join(str(n).upper().replace(",", "").split())
    mine = [datetime.datetime.fromisoformat(s) for s in holds.get(name, [])]
    others = {datetime.datetime.fromisoformat(s) for n, v in holds.items()
              if n != name and norm(n) in replied for s in v}
    if len(mine) == 2 and all(s > now and s in sl and s not in others for s in mine):
        taken.update(mine)
        return mine
    open_ = [s for s in sl if s not in others]
    cand = [s for s in open_ if s not in taken]
    if len(cand) < 2:  # all given out this run: reuse the least-offered times first (spreads people out)
        cand = sorted(open_, key=lambda s: (_USE[s], s))
    far = hi
    while len(cand) < 2 and far < 90:
        far += 7
        cand = [s for s in free_slots(today, 2, far) if s not in others]
    wk = [s for s in cand if s.weekday() < 5]
    we = [s for s in cand if s.weekday() >= 5]
    if wk and we:
        two = sorted([wk[0], we[0]])
    elif len(cand) >= 2:
        two = cand[:2]
    else:
        return None
    taken.update(two)
    for s in two:
        _USE[s] += 1
    return two


if __name__ == "__main__":
    print(f"busy.json: {'found' if os.path.exists(BUSY) else 'missing (rules only)'}")
    for s in free_slots():
        print(" ", say(s))
    for i in range(5):
        print(i + 1, pick(i))
