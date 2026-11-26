# Changelog

## 1.5.0 (26 Nov 2026)
- **Richer meeting briefs**: one-page layout with logistics (place, hard stop, who pays), purpose (intro vs review),
  the person (birthday soon, life details), a policies table, fund mix with % and equity share, gaps to ask about (cover
  not in the insurer file), light talking points, the close, and which numbers to check in the insurer portal.
- **Claims, servicing and pending new cases tracker** (`./pa cases`). One checklist per case ("client: signed claim
  form", "clinic: medical report", "me: fill in the form", "insurer: …"), built from the insurer's own form. `cases ask`
  drafts ONE WhatsApp message listing everything the client must send. A new HQ topic **📎 Claims & servicing** gets one
  board each morning only when a case needs a chase (client every 3 days, clinic 5, insurer 7 after submitting;
  config.json cases.chase_days), plus every Monday. Updates in plain words: "got C1 bill", "chased C1", "submitted C1",
  "close C1 paid". Never names a medical condition, never talks to any insurer system.
- **Nightly WhatsApp check can read chats** (optional, off by default: config.json whatsapp.read_chats). New scheduled
  task scheduled-tasks/nightly-whatsapp-check.md (4:30am) opens recent and quiet client/prospect chats in WhatsApp Web,
  reads one screen, keeps a short private note per person (new `./pa wa_notes`), and decides from the conversation
  (not who spoke last): REPLY / BUMP / NONE, with a draft in the adviser's voice on the To message list. It also
  checks clients with no WhatsApp record yet, closes first messages for people who already have a chat, takes off
  reminders already sent, closes premium reminders when a payment shows, flags claims/servicing requests, and adds or
  updates calendar events. REPLY chats are marked unread again. Opening a chat shows blue ticks; nothing is ever sent.
- **To message list:** `todo_list add --draft "<message>"` (a context draft; a "Your turn:" / "Bump:" draft replaces
  the generic nudge and older Your-turn line, so one line, one message), `todo_list paid "<name>"` (closes the soonest
  premium reminder) and `todo_list answered "<name>" [--since <date>]` (the adviser already replied: Your-turn / nudge
  lines come off). The combined message prefers the context draft. Offered times in a message still waiting to be
  sent (e.g. a carried-over intro) are swapped for fresh free times if they are today or already past.
- **WhatsApp reply check script:** people the adviser already answered (they sent the last message) have their
  "Your turn" / nudge lines taken off the list automatically.
- **New skill add-meeting-to-calendar:** confirmed client meetings go on the adviser's own Google Calendar (no guests,
  no invite): intro 30 min vs review 2 h, 🚗 travel buffers before and after in-person meetings (30 min, 45 for
  far areas), one 🎧 15-min "find a quiet spot" block before a Zoom call, none for phone calls. Events the PA made are
  updated when details change (place agreed, time moved); the adviser's own events are never touched. Automatic only
  if config.json calendar.auto_add_confirmed is true, otherwise offered first. New config.json `calendar` settings
  (home_area, far_areas, lengths, buffers).
- CLAUDE.md, setup guides (Mac, Windows, for Claude), README and config.example.json updated for all of the above.

## 1.4.7 (19 Nov 2026)
- Appointment times: everyone is offered the earliest free weekday + weekend time. Unconfirmed offers never block
  each other (the same time can go to several people until one confirms and it lands in the calendar), so dates no
  longer drift further and further out.

## 1.4.6 (19 Nov 2026)
- One message per person: if someone has several things on the daily To message list (premium, birthday,
  follow-up, intro), they get one line and one combined WhatsApp message. If they messaged last, the button just
  opens the chat (no prefilled text). `done 3` marks all of that person's items.
- First messages: while a transferred client's intro is unsent, their premium / birthday reminders are folded into
  it, so no second "first message" without an intro. If the intro expires unsent, the reminders come back.
- Appointment times: offered within the next 1–2 weeks, as soon as possible. A time offered to someone who never
  replied counts as free again (it only stays held once they reply). Before, unanswered offers kept times blocked
  and later people were pushed weeks out.
- New: `./pa todo_list away "<name>" --until <date>` for clients who are overseas: off the list till then.
- Fix: `daily_reminders --telegram --dry` no longer posts for real.

## 1.4.5 (17 Nov 2026)
- Answer buttons no longer keep popping up after a tap: `telegram_post --clear` removes them, and the PA posts
  its one-line result with it after every answer.

## 1.4.4 (17 Nov 2026)
- Both setup guides: new section "Their own files, and how the PA learns" (Me.md, Preferences.md, Voice.md,
  config.json, Data, Drafts, Forms/Blank, their own bot). Setup now ends by telling them how corrections teach the PA.

## 1.4.3 (17 Nov 2026)
- Gender-neutral wording everywhere (guides, agents, scheduled tasks, tools): the kit is for any adviser, so it
  says "they" / "the adviser" instead of "she" / "her". No behaviour change.

## 1.4.2 (17 Nov 2026)
- Telegram line: the folders it reads (Telegram inbox, its memory folder, product and forms libraries) are now
  created up front, so she trusts them all at the first visible start. Before, a folder that appeared later made the
  hidden line wait on a "trust this folder?" question nobody could see.
- Setup guides checked end to end: Mac (Homebrew "Next steps", version checks, macOS pop-ups to expect), Windows
  (PATH note, paste tip), SETUP-FOR-CLAUDE (she types the /plugin commands; scheduled tasks added in the Claude app
  with the PA folder chosen; when to re-run the visible start; Windows hides the line after setup).

## 1.4.1 (17 Nov 2026)
- "Update the PA" from Telegram now restarts the line straight away on both Mac and Windows (`./pa line restart`
  runs on its own, so stopping the line no longer cuts off the update; before, the watchdog brought it back
  within 5 minutes).
- Windows: PDFs also find Edge/Chrome in their other install folders; `pa` falls back to the py launcher before
  setup; update.sh says "run setup first" if there's no Python environment; guides mention keeping the PA folder
  out of OneDrive.

## 1.4 (17 Nov 2026)
- **Windows support.** The kit now runs on a Mac or a Windows 10/11 PC. New SETUP-GUIDE-WINDOWS.md (the Mac guide
  is now SETUP-GUIDE-MAC.md; SETUP-GUIDE.md says which to use). SETUP-FOR-CLAUDE.md covers both.
- Windows: `setup.cmd` (first-time setup; `setup.cmd background` turns on the line at sign-in, watchdog, Drive sync and
  WhatsApp check with Task Scheduler, no administrator rights), `pa.cmd` (run a tool from PowerShell), `update.cmd`.
  The Telegram line runs hidden in its own console window; `--visible` shows it for first-run questions.
- One command for the Telegram line on both: `./pa line start | stop | status` (Tools/line.py; the Mac still uses
  tmux underneath). Inside Claude Code `./pa …` works on both (Claude Code uses Git Bash on Windows).
- Watchdog: also spots a line stuck on a start-up question (e.g. "trust this folder?") and posts once instead of
  restarting it every 5 minutes.
- Daily list: a new setup without a TOP list now says "No TOP list yet" instead of an error.
- .gitattributes keeps the right line endings for each system.

## 1.3 (16 Nov 2026)
- Financial health check: the FIC importer now reads every table by column heading, so a moved or added column can't
  shift the numbers; it stops and names the heading if one it needs is missing.
- Reads the v3 FIC in one go (Export!A1:AM115) and still reads v2. New from v3: policy Status / Type / Whose Policy /
  Hospital Ward / Rider dropdowns, a legacy target, the date of the review, holdings and risk profile from the
  Investments tab.
- Leaves out policies that aren't in force or that cover a spouse, child or parent (and says so). Flags cash values
  and holdings over a year old, policies with no type, and sample figures left in a renamed copy.

## 1.2.1 (16 Nov 2026)
- Telegram: a dropped connection no longer shows as "Topics is turned off"; the safety check retries 3 times and
  says "couldn't reach Telegram" if it still can't get an answer.

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
