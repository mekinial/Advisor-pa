"""the adviser's voice: her own Telegram messages, kept so drafts can sound like her.

  voice.py samples [--n 40]   print her latest N messages (style reference for drafters)
  voice.py new                print messages since the last Voice.md refresh, then mark them as seen
  voice.py count              how many samples are stored

Samples are captured automatically by tg_line_hooks.py into Drafts/Status/voice-samples.jsonl.
Internal and local only. Use them for STYLE (words, length, tone, emojis), never copy their content
(names, client facts, health notes) into a draft.
"""
import sys, os, json, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VS = os.path.join(ROOT, "Drafts", "Status", "voice-samples.jsonl")
MARK = os.path.join(ROOT, "Drafts", "Status", "voice-mark.json")


def load():
    out = []
    try:
        for ln in open(VS, encoding="utf-8"):
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    except FileNotFoundError:
        pass
    return out


def show(rows):
    for e in rows:
        print(f"[{time.strftime('%d %b %H:%M', time.localtime(e['t']))}] {e['text']}")


args = sys.argv[1:] or ["samples"]
rows = load()
if args[0] == "samples":
    n = int(args[args.index("--n") + 1]) if "--n" in args else 40
    show(rows[-n:])
elif args[0] == "new":
    last = 0
    try:
        last = json.load(open(MARK))["t"]
    except Exception:
        pass
    fresh = [e for e in rows if e["t"] > last]
    show(fresh)
    print(f"-- {len(fresh)} new message(s) since last refresh")
    if fresh:
        json.dump({"t": fresh[-1]["t"]}, open(MARK, "w"))
elif args[0] == "count":
    print(len(rows))
else:
    print(__doc__)
