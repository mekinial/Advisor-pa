# Advisor PA kit

A personal admin team for a financial adviser (Planners Inc / Great Eastern, Singapore): a PA on Telegram plus
specialist agents, running in Claude Code on the adviser's own **Mac or Windows PC**.

- **Set up:** SETUP-GUIDE.md picks the guide (SETUP-GUIDE-MAC.md or SETUP-GUIDE-WINDOWS.md) → then Claude follows
  SETUP-FOR-CLAUDE.md (same file for both).
- **Update:** Mac `./update.sh` · Windows `.\update.cmd` · or tell the PA "update the PA" on Telegram.
- **Run a tool:** Mac `./pa <tool> [args]` · Windows `.\pa.cmd <tool> [args]` (list: run it with no tool).
- **Telegram line:** `pa line start | stop | status` on both.

## What's in here (shared, same for everyone)
- CLAUDE.md: how the PA and agents work, ground rules (draft only, never contact anyone, never connect to GE systems).
- .claude/agents/: follow-up, admin-forms, data-analyst, meeting-prep, client-report, proposal-writer,
  investment-writer, drive-organizer. .claude/skills/: financial-health-check (optional) and
  add-meeting-to-calendar (confirmed meetings + travel buffers on their own calendar).
- setup.sh (Mac) / setup.cmd + setup.ps1 (Windows): first-time setup and background jobs.
- Tools/: Telegram (hq.py, telegram_post.py), daily To message list (daily_reminders.py, todo_list.py,
  top_intros.py, slots.py), week ahead, status board, pipeline updates, background jobs, voice notes, PDFs,
  product-library search, Drive sync, the optional WhatsApp reply check (whatsapp_scan.py) and per-person
  WhatsApp notes (wa_notes.py), the claims / servicing / new-case tracker (cases.py), the Telegram line (line.py;
  Mac also start_line.sh / stop_line.sh) and watchdog.
- scheduled-tasks/: prompts for the Claude desktop app's scheduled tasks.
- templates/: blank client workbook, pipeline, TOP list, Me/Preferences/Voice starters.

## What's NOT in here (private, per adviser, on their own computer only)
config.json, Me.md, Preferences.md, Voice.md, Data/ (clients, pipeline, policies), Drafts/ (everything the
agents write), Forms/Blank/, the Telegram bot token and chat ids (in ~/.claude/channels/telegram/).
These are listed in .gitignore, so they can never be committed or pushed, and updates never touch them.

## Rules that are built in
- Drafts only; nothing is ever sent to clients. Telegram posts go only to their private HQ group, and every tool
  refuses to post if anyone other than them and the bot is in the group.
- No NRIC, policy numbers or bank details in drafts or messages; health notes internal only.
- No AI connection to Great Eastern systems (Lifehub, GE portal): they download files themselves.
