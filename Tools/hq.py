"""HQ Telegram: the ONE place that talks to the Telegram API (refactored 16 Nov 2026).

Every Admin Team post goes through here: telegram_post.py, daily_reminders.py (daily To message list),
week_ahead.py and top_intros.py. Other scripts post by running telegram_post.py.

    import hq
    token, chat, base = hq.connect()          # None token = not safe to send; hq.PROBLEM says why
    thread = hq.topic_id(token, chat, base, "admin")
    hq.api(token, "sendMessage", chat_id=chat, text="…", message_thread_id=thread)

Safety (checked on every connect): the target is the adviser's private "HQ" group only (id in hq/hq.json); it must
have exactly 2 members (the adviser + the bot), the adviser must be in it, and Topics must be on. Otherwise nothing is sent.
The bot token is read from ~/.claude/channels/telegram/.env and never printed.
"""
import json, os, time, urllib.request, uuid

PROBLEM = None   # why the last connect() refused, or None

HQ_TOPICS = {  # HQ layout (agreed 12 Nov 2026): General + these. Ids kept in hq/topics.json
    "to-message": "📲 To message",       # everyone to WhatsApp today: premium, birthday, TOP intros
    "work": "📅 Meetings & reports",     # briefs, agendas, PDFs
    "admin": "🗂 Admin",                 # numbers, forms, follow-up drafts
    "marketing": "📣 Marketing",         # only created once marketing posts something
    "cases": "📎 Claims & servicing",    # 1.5.0: claims / servicing / pending new cases board (cases.py)
}


def tg_root():
    return os.path.join(os.path.expanduser("~"), ".claude", "channels", "telegram")


def hq_dir():
    """State folder shared by all posting scripts (topic ids, digest ids, TOP lists)."""
    return os.path.join(tg_root(), "hq")


def _request(token, method, body, content_type, timeout):
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=body,
                                 headers={"Content-Type": content_type})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def _error(e):
    """Telegram's own error reply if there is one, else a short description."""
    body = getattr(e, "read", lambda: b"")()
    try:
        return json.loads(body)
    except Exception:
        return {"ok": False, "description": type(e).__name__}


def api(token, method, _tries=3, _timeout=30, **params):
    """One JSON API call. If Telegram says 'Too Many Requests', waits as told and retries (up to 3 tries), so a
    topic is never skipped (a skipped createForumTopic made posts land in General). Never raises."""
    for attempt in range(_tries):
        try:
            return _request(token, method, json.dumps(params).encode(), "application/json", _timeout)
        except Exception as e:
            r = _error(e)
            wait = (r.get("parameters") or {}).get("retry_after")
            if r.get("error_code") == 429 and wait and attempt < _tries - 1:
                time.sleep(wait + 1); continue
            return r


def api_file(token, method, fields, path, file_field="document", _timeout=60):
    """Multipart call that uploads one file (e.g. sendDocument). fields = other form fields (strings). Never raises."""
    b = uuid.uuid4().hex
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    with open(path, "rb") as fh:
        data = fh.read()
    parts.append((f'--{b}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{os.path.basename(path)}"\r\n'
                  "Content-Type: application/octet-stream\r\n\r\n").encode() + data + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    try:
        return _request(token, method, b"".join(parts), f"multipart/form-data; boundary={b}", _timeout)
    except Exception as e:
        return _error(e)


def connect():
    """(token, chat id, state folder) for HQ, after the safety check. On any failed check returns
    (None, None, state folder) and sets PROBLEM."""
    global PROBLEM
    PROBLEM = None
    root, base = tg_root(), hq_dir()
    token = None
    for line in open(os.path.join(root, ".env"), encoding="utf-8"):
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"')
    allow = json.load(open(os.path.join(root, "access.json"), encoding="utf-8")).get("allowFrom") or []
    cfg = os.path.join(base, "hq.json")
    if not token or len(allow) != 1 or not os.path.exists(cfg):
        PROBLEM = "no bot token, owner or HQ group configured"
        return None, None, base
    gid = json.load(open(cfg))["chat_id"]
    for attempt in range(3):  # a dropped connection must not read as "Topics off"
        rc = api(token, "getChatMemberCount", chat_id=gid)
        rm = api(token, "getChatMember", chat_id=gid, user_id=int(allow[0]))
        rf = api(token, "getChat", chat_id=gid)
        bad = [r for r in (rc, rm, rf) if not r.get("ok")]
        if not bad:
            break
        time.sleep(5 * (attempt + 1))
    if bad:
        PROBLEM = f"couldn't reach Telegram ({bad[0].get('description', 'no answer')}); nothing sent"
        return None, None, base
    count = rc.get("result")
    status = rm.get("result", {}).get("status")
    forum = rf.get("result", {}).get("is_forum")
    if count != 2 or status not in ("creator", "administrator", "member"):
        PROBLEM = f"HQ must contain only you and the bot (members: {count}); nothing sent"
        return None, None, base
    if not forum:
        PROBLEM = "Topics is turned off in HQ; nothing sent"
        return None, None, base
    return token, str(gid), base


def _load(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def topic_id(token, chat, base, key):
    """Thread id of one HQ topic (created on first use). None = post in General."""
    f = os.path.join(base, "topics.json")
    ids = _load(f, {})
    if key not in ids:
        r = api(token, "createForumTopic", chat_id=chat, name=HQ_TOPICS[key])
        if not r.get("ok"):
            return None
        ids[key] = r["result"]["message_thread_id"]
        json.dump(ids, open(f, "w"))
    return ids[key]


def named_topic(token, chat, ids, key, name):
    """Make sure ids[key] holds a thread id for a topic called name (creates it if missing). Used for the TOP tier
    topics, whose ids live in their own file. Returns the id or None."""
    if key not in ids:
        r = api(token, "createForumTopic", chat_id=chat, name=name)
        if r.get("ok"):
            ids[key] = r["result"]["message_thread_id"]
    return ids.get(key)
