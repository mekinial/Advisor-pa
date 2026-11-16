"""Local search over her own copy of the GE Product Library (folder: config.json files.product_library). She
downloads the documents herself; nothing here logs in to or automates any GE system. Nothing leaves this computer.

  ./pa library_search index                 add/refresh text of new or changed PDFs, Word, PowerPoint files
  ./pa library_search search "<words>" [--plan "<part of plan name>"] [--n 10]
  ./pa library_search plans [<filter>]      list plans (folders) and their files

Index: _index.db (SQLite full-text search, one row per page). Search shows plan, file, page and a snippet;
then open that page of the PDF to read the exact wording before answering a product question.
"""
import os, sys, sqlite3, re, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C
ROOT = C.PRODUCT_LIBRARY
DB = os.path.join(ROOT, "_index.db")


def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, mtime REAL, pages INT)")
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(section, plan, file, page UNINDEXED, path UNINDEXED, text, tokenize='porter unicode61')")
    return c


def office_text(path):
    """Plain text from .docx/.pptx (zip of XML). Old .doc/.ppt are skipped."""
    out = []
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if re.match(r"(word/document|ppt/slides/slide\d+)\.xml$", n))
        for n in names:
            xml = z.read(n).decode("utf-8", "ignore")
            out.append(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml)))
    return out


def index():
    from pypdf import PdfReader
    import logging; logging.getLogger("pypdf").setLevel(logging.ERROR)
    c = db()
    known = dict(c.execute("SELECT path, mtime FROM files"))
    done, seen = 0, set()
    for dp, _, fs in os.walk(ROOT):
        for f in fs:
            p = os.path.join(dp, f)
            ext = f.lower().rsplit(".", 1)[-1]
            if f.startswith("_") or ext not in ("pdf", "docx", "pptx"):
                continue
            rel = os.path.relpath(p, ROOT)
            seen.add(rel)
            mt = os.path.getmtime(p)
            if known.get(rel) == mt:
                continue
            parts = rel.split(os.sep)
            sec, plan = (parts[0], parts[1]) if len(parts) > 2 else (parts[0], "")
            try:
                texts = [(pg.extract_text() or "") for pg in PdfReader(p).pages] if ext == "pdf" else office_text(p)
            except Exception as e:
                texts = []
                print("  could not read:", rel, type(e).__name__)
            c.execute("DELETE FROM pages WHERE path=?", (rel,))
            c.executemany("INSERT INTO pages VALUES (?,?,?,?,?,?)",
                          [(sec, plan, f, i + 1, rel, t) for i, t in enumerate(texts) if t.strip()])
            c.execute("INSERT OR REPLACE INTO files VALUES (?,?,?)", (rel, mt, len(texts)))
            done += 1
            if done % 50 == 0:
                c.commit(); print(f"  indexed {done} files...", flush=True)
    gone = [r for r in known if r not in seen]  # files deleted, renamed or moved since the last index
    for r in gone:
        c.execute("DELETE FROM pages WHERE path=?", (r,))
        c.execute("DELETE FROM files WHERE path=?", (r,))
    c.commit()
    n = c.execute("SELECT count(*) FROM files").fetchone()[0]
    print(f"Indexed {done} new/changed files, removed {len(gone)} that are gone; {n} files in the index")


def search(q, plan=None, n=10):
    c = db()
    terms = " ".join(f'"{w}"' for w in re.findall(r"[\w$%.-]+", q))
    sql = ("SELECT plan, file, page, path, snippet(pages, 5, '[', ']', ' … ', 18) FROM pages WHERE pages MATCH ?"
           + (" AND plan LIKE ?" if plan else "") + " ORDER BY rank LIMIT ?")
    args = [terms] + ([f"%{plan}%"] if plan else []) + [n]
    rows = c.execute(sql, args).fetchall()
    if not rows:
        print("No matches. Try fewer or different words."); return
    for pl, f, pg, path, snip in rows:
        print(f"- {pl} | {f} | p.{pg}\n  {snip}\n  {os.path.join(ROOT, path)}")


def plans(flt=""):
    for sec in sorted(os.listdir(ROOT)):
        sp = os.path.join(ROOT, sec)
        if not os.path.isdir(sp):
            continue
        for pl in sorted(os.listdir(sp)):
            if flt.lower() in (sec + " " + pl).lower():
                print(f"{sec} / {pl} ({len(os.listdir(os.path.join(sp, pl)))} files)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "index":
        index()
    elif a[0] == "search" and len(a) > 1:
        plan = a[a.index("--plan") + 1] if "--plan" in a else None
        n = int(a[a.index("--n") + 1]) if "--n" in a else 10
        search(a[1], plan, n)
    elif a[0] == "plans":
        plans(a[1] if len(a) > 1 else "")
    else:
        sys.exit(__doc__)
