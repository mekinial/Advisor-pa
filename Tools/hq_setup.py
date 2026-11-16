"""One-time: connect her private Telegram group ("HQ") to the PA.

Before running:
  1. The Telegram plugin is configured with her bot token and she has paired her own account in a DM with the bot
     (access.json "allowFrom" holds exactly her user id).
  2. She created a Telegram group with ONLY herself and the bot, made the bot an admin, turned Topics on,
     and sent any message (e.g. "hello") in the group.
  3. The Telegram line is NOT running (Tools/stop_line.sh), so this script can read the bot's new messages once.

  ./pa hq_setup          find the group, save its id (hq/hq.json) and let the plugin listen there (access.json)
  ./pa hq_setup --check  only run the safety check (2 members, she is in it, Topics on)

Never prints the bot token. Changes only ~/.claude/channels/telegram/access.json (adds the one group) and hq/hq.json.
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hq


def main():
    root = hq.tg_root()
    acc_f = os.path.join(root, "access.json")
    os.makedirs(hq.hq_dir(), exist_ok=True)
    if "--check" in sys.argv:
        token, chat, _ = hq.connect()
        print("Safety check OK: group " + chat if token else "Safety check failed: " + str(hq.PROBLEM))
        return
    token = None
    for line in open(os.path.join(root, ".env"), encoding="utf-8"):
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"')
    acc = json.load(open(acc_f, encoding="utf-8"))
    owner = (acc.get("allowFrom") or [None])[0]
    if not token or not owner or len(acc.get("allowFrom") or []) != 1:
        sys.exit("First set up the bot token and pair your own account in a DM with the bot (allowFrom must hold only you).")
    r = hq.api(token, "getUpdates", timeout=0, allowed_updates=["message", "my_chat_member"])
    if not r.get("ok"):
        sys.exit("Couldn't read the bot's messages: " + str(r.get("description")) +
                 " (is the Telegram line still running? Stop it first: Tools/stop_line.sh)")
    groups = {}
    for u in r.get("result", []):
        m = u.get("message") or u.get("my_chat_member") or {}
        c = m.get("chat") or {}
        frm = (m.get("from") or {}).get("id")
        if c.get("type") in ("group", "supergroup") and str(frm) == str(owner):
            groups[c["id"]] = c.get("title", "")
    if not groups:
        sys.exit("No group message from you found. Send 'hello' in the new group (bot added as admin), then run this again.")
    if len(groups) > 1:
        sys.exit("More than one group found: " + ", ".join(f"{t} ({i})" for i, t in groups.items()) +
                 ". Remove the bot from the others, send 'hello' in HQ, and run again.")
    gid, title = next(iter(groups.items()))
    json.dump({"chat_id": gid, "title": title}, open(os.path.join(hq.hq_dir(), "hq.json"), "w"))
    acc.setdefault("groups", {})[str(gid)] = {"requireMention": False, "allowFrom": [str(owner)]}
    json.dump(acc, open(acc_f, "w", encoding="utf-8"), indent=2)
    print(f"Saved HQ group '{title}' ({gid}) and allowed the plugin to listen there (only you).")
    tok, chat, _ = hq.connect()
    print("Safety check OK" if tok else "Safety check: " + str(hq.PROBLEM) +
          " (fix it in Telegram, then run ./pa hq_setup --check)")


if __name__ == "__main__":
    main()
