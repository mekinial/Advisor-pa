# Changelog

## 1.2 (16 Nov 2026)
- Product questions: answers about a client's policy now use the version of the plan they bought (checked against
  the issue date), and every answer says whether its source is client-facing ✅ or internal 🔒.
- Library search: `index` now also drops files that were deleted, renamed or moved (no more results pointing to
  missing files).

## 1.1 (16 Nov 2026)
- New, optional: WhatsApp reply check (Tools/whatsapp_scan.py), for Mac and Windows. Sorts everyone she has
  messaged into your turn / waiting / unsure by who sent the last message, adds "your turn" people to the To message
  list and posts a report to the Admin topic. Read only, never reads message text.
  Mac: reads WhatsApp's chat database (needs Full Disk Access once). Windows: reads the WhatsApp chat list.
  Turn on with config.json "whatsapp": {"enabled": true}, then ./setup.sh background (runs 4:07am).

## 1.0 (16 Nov 2026)
- First version for Mac: Telegram PA (HQ group, 4 topics, answer buttons, voice notes, background jobs,
  screenshot/status), daily To message list (premium, birthday, TOP intros with free times, done/skip/replied,
  nudges), morning brief, evening wrap, week ahead, meeting briefs, status board with away mode, pipeline updates,
  8 specialist agents, optional financial health check, product-library search, Drive sync, watchdog.
