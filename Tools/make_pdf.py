"""Turn a Markdown report into a polished PDF (for the report and meeting agents).

Usage:  ./pa make_pdf "<report.md>" [--title "..."] [--client "..."] [--kind "Portfolio Review"]
Writes  <report>.pdf next to the .md (the .md stays as the editable draft).

- The first "# Heading" is the title unless --title is given.
- Any section whose heading starts with "Check before" (internal notes for the adviser) is
  REMOVED from the PDF automatically. It stays in the .md.
- Printed with Google Chrome or Microsoft Edge (headless), so no extra software is needed.
"""
import sys, os, re, html, subprocess, tempfile, datetime
import markdown

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pa_config as C
ADVISER = C.ME.get("full_name") or "your adviser"


def browser():
    """Chrome or Edge, used headless to print the PDF."""
    for b in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if os.path.exists(b):
            return b
    sys.exit("No Chrome or Edge found to make the PDF. Install Google Chrome.")

DISCLAIMER = ("This document is for discussion purposes and is based on the information available at the date shown. "
              "It does not constitute an offer or a recommendation. Non-guaranteed values and past performance are not "
              "indicative of future results. Any recommendation is subject to a full needs analysis.")

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', Arial, sans-serif; color: #1d2433; font-size: 10.5pt; line-height: 1.5; }
.cover { border-bottom: 3px solid #1f4e78; padding-bottom: 10px; margin-bottom: 18px; }
.kind { color: #1f4e78; font-size: 9pt; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; }
.cover h1 { font-size: 22pt; margin: 4px 0 6px; color: #10243b; }
.meta { color: #5a6475; font-size: 9.5pt; }
h1 { font-size: 16pt; color: #10243b; }
h2 { font-size: 13pt; color: #1f4e78; border-bottom: 1px solid #d8dee8; padding-bottom: 3px; margin-top: 20px; }
h3 { font-size: 11pt; color: #10243b; margin-bottom: 4px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 9.5pt; page-break-inside: avoid; }
th { background: #1f4e78; color: #fff; text-align: left; padding: 6px 7px; font-weight: 600; }
td { border-bottom: 1px solid #e3e7ee; padding: 5px 7px; vertical-align: top; }
tr:nth-child(even) td { background: #f6f8fb; }
blockquote { border-left: 3px solid #1f4e78; margin: 8px 0; padding: 4px 12px; background: #f3f6fa; color: #33405a; }
ul, ol { padding-left: 20px; } li { margin: 2px 0; }
.foot { margin-top: 26px; border-top: 1px solid #d8dee8; padding-top: 8px; color: #6b7487; font-size: 8pt; }
"""


def strip_internal(md_text):
    out, skip, level = [], False, 0
    for line in md_text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            lv = len(m.group(1))
            if re.match(r"(\*\*)?\s*\d*\.?\s*check before", m.group(2), re.I):
                skip, level = True, lv; continue
            if skip and lv <= level:
                skip = False
        if not skip:
            out.append(line)
    return "\n".join(out)


def main():
    a = sys.argv[1:]
    opts = {}
    for k in ("--title", "--client", "--kind"):
        if k in a:
            i = a.index(k); opts[k] = a[i + 1]; del a[i:i + 2]
    if len(a) != 1: sys.exit(__doc__)
    src = a[0]
    text = strip_internal(open(src, encoding="utf-8").read())
    title = opts.get("--title")
    m = re.search(r"^#\s+(.+)$", text, re.M)
    if not title and m: title = m.group(1).strip()
    if m: text = text.replace(m.group(0), "", 1)
    body = markdown.markdown(text, extensions=["tables", "sane_lists"])
    meta = " · ".join(x for x in (
        f"Prepared for {html.escape(opts['--client'])}" if opts.get("--client") else "",
        f"Prepared by {ADVISER}", datetime.date.today().strftime("%d %B %Y")) if x)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="cover"><div class="kind">{html.escape(opts.get('--kind', 'Report'))}</div>
<h1>{html.escape(title or 'Report')}</h1><div class="meta">{meta}</div></div>
{body}
<div class="foot">{DISCLAIMER}</div></body></html>"""
    out = os.path.splitext(os.path.abspath(src))[0] + ".pdf"
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(page); tmp = f.name
    try:
        subprocess.run([browser(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={out}", "file://" + ("/" if os.name == "nt" else "") + tmp.replace("\\", "/")],
                       check=True, timeout=120, capture_output=True)
    finally:
        os.remove(tmp)
    if not os.path.exists(out): sys.exit("PDF was not created.")
    print(out)


if __name__ == "__main__":
    main()
