# Changelog

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
