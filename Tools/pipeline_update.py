"""Update one client's row in Data/pipeline.csv after a meeting or chat (the adviser approved this on 12 Nov 2026).

  ./pa pipeline_update "<client>" [--stage "<Stage>"] [--next "<next action>"] [--next-date YYYY-MM-DD]
                                         [--note "<one short line>"] [--met YYYY-MM-DD] [--new] [--source "<src>"] [--dry]

- <client>: any part of the name ("Alex", "Woo Kah Lok"). Must match exactly ONE row, otherwise nothing is
  changed and the candidates are listed. --new adds a row instead (Stage defaults to "Lead - revive"... use --stage).
- --met sets Last Contact (default today when --note is given). --note is appended to Key Notes as "12 Nov: ...".
- Keeps a daily backup in Drafts/Pipeline backups/ and logs every change in Drafts/Meetings/pipeline-changes.md.
- Never write NRIC, policy numbers, bank details or long health details here.
"""
import sys, os, csv, datetime, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "Data", "pipeline.csv")
BACKUPS = os.path.join(ROOT, "Drafts", "Pipeline backups")
CHANGES = os.path.join(ROOT, "Drafts", "Meetings", "pipeline-changes.md")
STAGES = ["In progress", "Review due", "Lead - revive", "Referral", "Client (closed)", "Not interested", "To sort"]


def opt(args, name):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return None


def main():
    a = sys.argv[1:]
    dry, new = "--dry" in a, "--new" in a
    a = [x for x in a if x not in ("--dry", "--new")]
    stage, nxt, nd, note, met, source = (opt(a, k) for k in ("--stage", "--next", "--next-date", "--note", "--met", "--source"))
    if len(a) != 1:
        sys.exit(__doc__)
    who = a[0].strip()
    today = datetime.date.today()
    if stage and stage not in STAGES:
        sys.exit(f"Unknown stage '{stage}'. Use one of: {', '.join(STAGES)}")
    for v in (nd, met):
        if v: datetime.date.fromisoformat(v)
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f); cols = r.fieldnames; rows = list(r)
    words = who.lower().split()
    hits = [x for x in rows if all(w in x["Client"].lower() for w in words)]
    if new:
        if hits:
            sys.exit(f"Not added: already in the pipeline as {', '.join(h['Client'] for h in hits)}")
        row = {c: "" for c in cols}; row.update(Client=who, Stage=stage or "Lead - revive", Source=source or "Added from chat",
                                                Priority="Medium"); rows.append(row)
    elif len(hits) != 1:
        sys.exit(f"Not changed: '{who}' matches {len(hits)} rows" +
                 (": " + "; ".join(h["Client"] for h in hits[:8]) if hits else ". Use --new to add them."))
    else:
        row = hits[0]
    before = dict(row)
    if stage: row["Stage"] = stage
    if nxt is not None: row["Next Action"] = nxt
    if nd is not None: row["Next Action Date"] = nd
    if met or note: row["Last Contact"] = met or str(today)
    if note:
        when = datetime.date.fromisoformat(met) if met else today
        stamp = f"{when.day} {when:%b}: {note.strip()}"
        row["Key Notes"] = (row["Key Notes"] + " | " if row["Key Notes"] else "") + stamp
    diff = [f"{c}: '{before.get(c, '')}' -> '{row[c]}'" for c in cols if before.get(c, "") != row[c]]
    if not diff:
        print("Nothing to change"); return
    if dry:
        print("DRY RUN, would change " + row["Client"] + ":\n  " + "\n  ".join(diff)); return
    os.makedirs(BACKUPS, exist_ok=True)
    bk = os.path.join(BACKUPS, f"pipeline-{today}.csv")
    if not os.path.exists(bk):
        shutil.copy2(CSV, bk)
    tmp = CSV + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL); w.writeheader(); w.writerows(rows)
    os.replace(tmp, CSV)
    os.makedirs(os.path.dirname(CHANGES), exist_ok=True)
    with open(CHANGES, "a", encoding="utf-8") as f:
        f.write(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} **{row['Client']}**: " + "; ".join(diff) + "\n")
    print(f"Updated {row['Client']}: " + "; ".join(d.split(':')[0] for d in diff))


if __name__ == "__main__":
    main()
