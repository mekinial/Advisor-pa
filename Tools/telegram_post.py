"""Post an agent update to the adviser's own Telegram, in that agent's topic.

Usage:
  ./pa telegram_post "<agent>" "<message>" [--file PATH] [--button "Label|https://..."]

  <agent>   one of: follow-up, data-analyst, admin-forms, reports, meetings, marketing, main
            HQ has 4 topics: To message, Meetings & reports (reports, meetings),
            Admin (follow-up, data-analyst, admin-forms), Marketing (later). main = General.
  <message> plain text, keep it short: lead with what needs their action
  --file    attach one file (PDF, xlsx, docx, image...) under 50 MB
  --button  add a tap-to-open link button (can be given more than once)
  --ask     "Yes, send the Alex invite|No, not yet"  answer buttons under the message. Tapping one sends that
            text into the chat as the adviser's own message, so the Telegram line receives it like a typed reply.
            Make each answer name the item ("Yes, send the Alex invite") so it can be matched.
  --clear   take the answer buttons away (post this with the confirmation once they have answered). Telegram keeps
            showing old answer buttons until a message removes them, so without this they pop up again.

Sends ONLY to the bot's single allowlisted user (the adviser). Never to clients or anyone else.
Never put NRIC, policy numbers, bank details or health details in a post.
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hq  # HQ target + safety check (only the adviser and the bot in the group) + API calls

TOPICS = {  # agent name -> HQ topic (4 topics + General, agreed 12 Nov 2026; names in hq.HQ_TOPICS)
    "main": None,                 # General = the main chat
    "to-message": "to-message",   # people to WhatsApp
    "follow-up": "admin",
    "data-analyst": "admin",
    "admin-forms": "admin",
    "admin": "admin",
    "reports": "work",
    "meetings": "work",
    "work": "work",
    "marketing": "marketing",
}
TIMEOUT = 60  # uploads can be slow


def parse(args):
    """(agent, text, files, link buttons, answer buttons) from the command line, or exit with the usage."""
    files, buttons, asks = [], [], []
    clear = "--clear" in args
    args = [x for x in args if x != "--clear"]
    for flag, bucket in (("--file", files), ("--button", buttons), ("--ask", asks)):
        while flag in args:
            i = args.index(flag); bucket.append(args[i + 1]); del args[i:i + 2]
    if len(args) != 2 or args[0] not in TOPICS:
        sys.exit(__doc__)
    return args[0], args[1], files, buttons, asks, clear


def markup(buttons, asks, clear=False):
    if clear:  # removes the answer buttons from the chat (a message can carry only one kind of buttons)
        return {"remove_keyboard": True}
    if asks:  # reply keyboard: a tap sends the label as the adviser's message (link buttons can't be combined with it)
        opts = [o.strip() for a in asks for o in a.split("|") if o.strip()]
        return {"keyboard": [[{"text": o}] for o in opts], "one_time_keyboard": True,
                "resize_keyboard": True, "is_persistent": False}
    if buttons:
        return {"inline_keyboard": [[{"text": b.split("|", 1)[0], "url": b.split("|", 1)[1]}] for b in buttons]}
    return None


def main():
    agent, text, files, buttons, asks, clear = parse(sys.argv[1:])
    token, chat, base = hq.connect()
    if not token:
        sys.exit(f"Not sent: {hq.PROBLEM}")
    thread = hq.topic_id(token, chat, base, TOPICS[agent]) if TOPICS[agent] else None
    mk = markup(buttons, asks, clear)
    if files:
        fields = {"chat_id": chat, "caption": text[:1024]}
        if thread: fields["message_thread_id"] = str(thread)
        if mk: fields["reply_markup"] = json.dumps(mk)
        r = hq.api_file(token, "sendDocument", fields, files[0], _timeout=TIMEOUT)
    else:
        msg = {"chat_id": chat, "text": text, "disable_web_page_preview": True}
        if thread: msg["message_thread_id"] = thread
        if mk: msg["reply_markup"] = mk
        r = hq.api(token, "sendMessage", _timeout=TIMEOUT, **msg)
    if r.get("ok"):
        print(f"Posted to Telegram ({agent + ' topic' if thread else 'main chat'})")
    else:
        sys.exit(f"Not sent: {r.get('description')}")


if __name__ == "__main__":
    main()
