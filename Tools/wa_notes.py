"""Per-person WhatsApp notes (1.5.0).

After the nightly WhatsApp check reads a chat with a client or prospect, a short dated summary is kept here so
drafts and briefs have context without reopening WhatsApp. Internal only: never sent or shown to clients.
No NRIC, policy numbers, bank details, phone numbers (scrubbed automatically); health = one short plain line at most.

  ./pa wa_notes add "<name>" "<summary>" [--last them|me] [--date YYYY-MM-DD] [--chat-date YYYY-MM-DD]
                                         (--chat-date: date of the last message in the chat, for quiet-client checks)
  ./pa wa_notes show "<name>"          print that person's notes (newest last)
  ./pa wa_notes known "<chat name>"    is this a pipeline/TOP/client name? prints the match
  ./pa wa_notes list                    everyone with notes, latest date
  ./pa wa_notes untracked [--n 10]      clients in the client list with no WhatsApp record yet
  ./pa wa_notes nochat "<name>"         searched WhatsApp, no chat found (skipped for 90 days)
  ./pa wa_notes seen "<name>" YYYY-MM-DD   last chat date -> pipeline Last Contact (only if newer)
  ./pa wa_notes intros                  open first messages (TOP intros) on the To message list
  ./pa wa_notes existing "<name>" YYYY-MM-DD "<why>"   already has a chat: close the first message

Client list = Contacts sheet of the policies file (rows with "Has policies in this file" = Yes) plus pipeline rows
in Review due / In progress / Client (closed). Tracked = top-already-messaged.csv, a notes file, or a no-chat mark
from the last 90 days.

Files: Drafts/WhatsApp Notes/<Name>.md (one per person; a saved tag like "(TOP Mary)" is dropped).
"""
import sys, os, re, csv, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C

ROOT = C.ROOT
NOTES = os.path.join(ROOT, "Drafts", "WhatsApp Notes")
PIPE = os.path.join(ROOT, "Data", "pipeline.csv")
TOPCSV = os.path.join(ROOT, "Drafts", "Follow-ups", "top-already-messaged.csv")
NOCHAT = os.path.join(NOTES, "_no-chat.csv")
POLICIES = C.POLICIES_XLSX
CLIENT_STAGES = ("Review due", "In progress", "Client (closed)")
BLOCK = [(re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.I), "[NRIC removed]"),
         (re.compile(r"(?<!\d)(\+?65[ -]?)?[689]\d{3}[ -]?\d{4}(?!\d)"), "[phone removed]"),
         (re.compile(r"\b\d{9,}\b"), "[number removed]")]


def words(s):
    return re.sub(r"[^A-Z ]", " ", re.sub(r"\([^)]*\)", " ", str(s).upper())).split()


def clean_name(s):
    s = re.sub(r"\([^)]*\)", "", str(s)).replace(",", " ")
    return " ".join(s.split()).strip() or str(s).strip()


def path_for(name):
    n = clean_name(name)
    safe = re.sub(r'[<>:"/\\|?*]', "", n)
    os.makedirs(NOTES, exist_ok=True)
    want = set(words(n))
    files = [f for f in os.listdir(NOTES) if f.endswith(".md")]
    for f in files:  # reuse an existing file for the same person
        if set(words(f[:-3])) == want:
            return os.path.join(NOTES, f), n
    near = [f for f in files if len(want) >= 2 and (want <= set(words(f[:-3])) or set(words(f[:-3])) <= want)]
    if len(near) == 1:  # "Mary Tan" finds "Mary Tan Hui Ling"
        return os.path.join(NOTES, near[0]), near[0][:-3]
    return os.path.join(NOTES, safe + ".md"), n


def scrub(t):
    for rx, rep in BLOCK:
        t = rx.sub(rep, t)
    return " ".join(t.split())


def add(name, text, last=None, date=None, chat_date=None):
    p, n = path_for(name)
    d = date or datetime.date.today().isoformat()
    new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8") as f:
        if new:
            f.write(f"# {n}: WhatsApp notes\n\nInternal only. Short dated summaries of what the chat showed. Never client-facing.\n\n")
        tag = []
        if last:
            tag.append(f"last message: {'them' if last == 'them' else 'me'}")
        if chat_date:
            tag.append(f"on {datetime.date.fromisoformat(chat_date)}")
        f.write(f"- {d}" + (f" ({' '.join(tag)})" if tag else "") + f": {scrub(text)}\n")
    print(f"Saved note for {n} → {p}")


def show(name):
    p, n = path_for(name)
    if not os.path.exists(p):
        print(f"No WhatsApp notes for {n} yet."); return
    print(open(p, encoding="utf-8").read())


def known(chat):
    cw = set(words(chat))
    tag = re.search(r"\(([^)]*)\)", str(chat))
    hits = []
    if tag and "TOP" in tag.group(1).upper():
        hits.append(f"TOP client (tag: {tag.group(1)})")
    for src, col in ((PIPE, "Client"), (TOPCSV, "Name")):
        if not os.path.exists(src):
            continue
        for r in csv.DictReader(open(src, encoding="utf-8")):
            nm = r.get(col) or ""
            for part in re.split(r"\s*&\s*|\s+and\s+", re.sub(r"\([^)]*\)", "", nm)):
                pw = set(words(part))
                if not pw:
                    continue
                if (len(pw) >= 2 and pw <= cw) or (len(cw) >= 2 and cw <= pw) or (len(pw) == 1 and len(cw) == 1 and pw == cw):
                    extra = f", stage {r.get('Stage')}" if r.get("Stage") else ""
                    hits.append(f"{os.path.basename(src)}: {nm}{extra}")
                    break
    print("\n".join(dict.fromkeys(hits)) if hits else "not found (judge from the preview: client, prospect or personal?)")


def lst():
    if not os.path.isdir(NOTES):
        print("No notes yet."); return
    for f in sorted(os.listdir(NOTES)):
        if f.endswith(".md"):
            ds = re.findall(r"^- (\d{4}-\d{2}-\d{2})", open(os.path.join(NOTES, f), encoding="utf-8").read(), re.M)
            print(f"{f[:-3]}: {ds[-1] if ds else '?'}")


def _tracked():
    t = []
    if os.path.exists(TOPCSV):
        t += [set(words(r["Name"])) for r in csv.DictReader(open(TOPCSV, encoding="utf-8"))]
    if os.path.isdir(NOTES):
        t += [set(words(f[:-3])) for f in os.listdir(NOTES) if f.endswith(".md")]
    if os.path.exists(NOCHAT):
        cut = str(datetime.date.today() - datetime.timedelta(days=90))
        t += [set(words(r["Name"])) for r in csv.DictReader(open(NOCHAT, encoding="utf-8")) if r["Checked"] >= cut]
    return t


def _same(a, b):
    return bool(a and b) and min(len(a), len(b)) >= 2 and (a <= b or b <= a)


def clients():
    out = []
    try:
        import openpyxl
        ws = openpyxl.load_workbook(POLICIES, read_only=True)["Contacts"]
        for r in ws.iter_rows(min_row=2, values_only=True):
            if r[0] and str(r[5]).strip().lower() == "yes":
                out.append((str(r[0]).strip(), "client (has policies)"))
    except Exception as e:
        print(f"(couldn't read the Contacts sheet: {e})")
    if os.path.exists(PIPE):
        for r in csv.DictReader(open(PIPE, encoding="utf-8")):
            if r.get("Stage") in CLIENT_STAGES:
                out.append((r["Client"].strip(), f"pipeline: {r['Stage']}"))
    seen_w, res = [], []
    for n, why in out:
        w = set(words(n))
        if w and not any(_same(w, s) for s in seen_w):
            seen_w.append(w); res.append((n, why))
    return res


def untracked(n=10):
    t = _tracked()
    todo = [(c, why) for c, why in clients() if not any(_same(set(words(c)), x) for x in t)]
    print(f"{len(todo)} clients with no WhatsApp record yet. Next {min(n, len(todo))}:")
    for c, why in todo[:n]:
        print(f"{clean_name(c).title()}  |  {why}")


def nochat(name):
    os.makedirs(NOTES, exist_ok=True)
    new = not os.path.exists(NOCHAT)
    with open(NOCHAT, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["Name", "Checked"])
        w.writerow([clean_name(name), datetime.date.today().isoformat()])
    print(f"Marked {clean_name(name)}: no WhatsApp chat found (skipped for 90 days)")


def seen(name, date):
    d = str(datetime.date.fromisoformat(date))
    cw = set(words(name))
    if not os.path.exists(PIPE):
        print("No pipeline file: nothing to update"); return
    rows = [r for r in csv.DictReader(open(PIPE, encoding="utf-8-sig")) if _same(set(words(r["Client"])), cw)]
    if len(rows) != 1:
        print("Not in the pipeline (or more than one match): nothing to update"); return
    r = rows[0]
    if r.get("Last Contact") and r["Last Contact"] >= d:
        print(f"Pipeline Last Contact already {r['Last Contact']}: unchanged"); return
    import subprocess
    subprocess.run(C.PY + [os.path.join(ROOT, "Tools", "pipeline_update.py"),
                    r["Client"], "--met", d])


TODO = os.path.join(ROOT, "Drafts", "Follow-ups", "todo-list.json")


def intros():
    """Open first-message (TOP intro) items on the To message list: full names, for the nightly existing-chat check."""
    import json
    if not os.path.exists(TODO):
        print("0 open first messages:"); return
    st = json.load(open(TODO, encoding="utf-8"))
    names = [k[2:] for k, v in st["items"].items() if k.startswith("T|") and v["status"] == "open"]
    print(f"{len(names)} open first messages:")
    print("\n".join(names))


def existing(name, date, why):
    """The adviser already has a chat with this person: close their first-message intro as 'not needed' and add
    them to top-already-messaged.csv, so the list treats them as a follow-up, not a first message."""
    import json
    st = json.load(open(TODO, encoding="utf-8")) if os.path.exists(TODO) else {"items": {}}
    nw = set(words(name))
    keys = [k for k, v in st["items"].items() if k.startswith("T|") and _same(set(words(k[2:])), nw)]
    for k in keys:
        it = st["items"][k]
        if it["status"] == "open":
            it["status"] = "not needed"
            it["flag"] = (it.get("flag", "") + " · " if it.get("flag") else "") + f"{datetime.date.today():%d %b}: {why}"
            print(f"Closed first message for {k[2:]}")
    if keys:
        json.dump(st, open(TODO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    full = keys[0][2:] if keys else " ".join(name.upper().replace(",", "").split())
    rows = list(csv.DictReader(open(TOPCSV, encoding="utf-8"))) if os.path.exists(TOPCSV) else []
    os.makedirs(os.path.dirname(TOPCSV), exist_ok=True)
    if not any(_same(set(words(r["Name"])), set(words(full))) for r in rows):
        rows.append({"Name": full.replace(",", ""), "Last WhatsApp": str(datetime.date.fromisoformat(date)), "Status": why})
        with open(TOPCSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["Name", "Last WhatsApp", "Status"]); w.writeheader(); w.writerows(rows)
        print(f"Added {full} to the already-messaged list")


if __name__ == "__main__":
    a = sys.argv[1:]
    def opt(k):
        if k in a:
            i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    last, date, cdate, n = opt("--last"), opt("--date"), opt("--chat-date"), opt("--n")
    if a[:1] == ["add"] and len(a) == 3:
        add(a[1], a[2], last, date, cdate)
    elif a[:1] == ["untracked"]:
        untracked(int(n or 10))
    elif a[:1] == ["nochat"] and len(a) == 2:
        nochat(a[1])
    elif a[:1] == ["seen"] and len(a) == 3:
        seen(a[1], a[2])
    elif a[:1] == ["intros"]:
        intros()
    elif a[:1] == ["existing"] and len(a) == 4:
        existing(a[1], a[2], a[3])
    elif a[:1] == ["show"] and len(a) == 2:
        show(a[1])
    elif a[:1] == ["known"] and len(a) == 2:
        known(a[1])
    elif a[:1] == ["list"]:
        lst()
    else:
        sys.exit(__doc__)
