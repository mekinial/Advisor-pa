# Setup steps for Claude (run on the adviser's Mac or Windows PC, in this folder)

**First, check which computer this is** (your environment says the platform: darwin = Mac, win32 = Windows).
Commands below are written for your own shell tool and work the same on both (`./pa …`; on Windows your shell is
Git Bash). Where the two differ, the step says **Mac:** / **Windows:**. When you tell HER a command to type
herself, use her form: Mac Terminal `./pa <tool>`; Windows PowerShell `.\pa.cmd <tool>`. Her guide is
SETUP-GUIDE-MAC.md or SETUP-GUIDE-WINDOWS.md.

She typed "Set me up, follow SETUP-FOR-CLAUDE.md". Walk her through these steps in order. Ask ONE question at a
time, in plain words, and wait. Do the typing yourself where you can; she approves. Log progress with
`./pa hq_status` once Telegram works. Ground rules from CLAUDE.md apply throughout (never contact anyone, never
connect to GE systems, never print or paste the bot token back to her).

If a step fails, explain in one line, fix it if you can, and keep a short list of anything left for the end.

## 0. Check the basics
- Setup has been run (`.venv/` exists). If not: **Mac** `./setup.sh` · **Windows** `./setup.cmd nopause`
  (or ask her to run `.\setup.cmd` in PowerShell).
- `claude --version`, `bun --version` (or ~/.bun/bin/bun), `git --version` all work; **Mac** also `tmux -V`.
  Missing ones: give her the install line from Part 1 of her guide (SETUP-GUIDE-MAC.md / SETUP-GUIDE-WINDOWS.md).

## 1. About her (Me.md and config.json)
Ask, one by one, and fill Me.md and config.json "me":
- Full name (for PDFs), what clients call her, her group name (e.g. "Jane HQ").
- How she titles client meetings in Google Calendar, and which calendar events to ignore (team, training, personal).
- Meeting times she likes to offer and never offers → config.json "schedule" (candidates + blocks, 24h) and Me.md.
- Where she's based → config.json "top": where_near line, near_postal_sectors (first 2 digits of nearby postal
  codes; suggest the ones around her area and let her confirm), near_areas.
- Her intro line for transferred clients (default: "I'm <short name> from Great Eastern, your new servicing adviser").
- Whether she wants the financial health check skill (FIC). If she has her own method, note it in Me.md.
Show her the finished Me.md and the "me", "top", "schedule" parts of config.json before moving on.

## 2. Telegram
1. Install the plugin. These are slash commands, so SHE types them in this chat (you can't run them yourself):
   `/plugin marketplace add anthropics/claude-plugins-official` (if needed), then
   `/plugin install telegram@claude-plugins-official`. If the plugin's own commands don't show up afterwards, she
   types `/exit`, starts `claude` again in this folder and says "carry on with SETUP-FOR-CLAUDE.md from step 2".
   Read the plugin's README (in ~/.claude/plugins/) for the exact configure and pairing commands of the installed
   version, and follow them (again, she types any slash commands):
   - configure the bot token (she pastes it; never repeat it back),
   - she sends a DM to her bot, then pair her account so access.json "allowFrom" holds only her user id,
   - set the DM policy to allowlist.
   **If she already has a bot and group running:** reuse them. Ask what currently runs the bot (another Claude Code
   chat with the Telegram plugin, another app or service). Only ONE program may read a bot's messages, so that one
   must be stopped for good before this PA takes over (or she makes a new bot for the PA). If the Telegram plugin
   is already configured on this computer with that bot, keep its token and pairing and skip the configure step.
2. The HQ group: she created it with only herself + the bot, bot is admin, Topics on, and sent "hello".
   An existing group is fine if it has ONLY her and the bot (every PA tool refuses to post otherwise); if others are
   in it, she makes a new group just for the PA. She sends a fresh "hello" in it right before the next command.
   Make sure no Telegram line is running (`./pa line stop`), then run `./pa hq_setup`. It saves the group id
   and adds the group to the plugin's access.json (only her, no @mention needed). Then `./pa hq_setup --check`.
3. Test: `./pa telegram_post main "👋 Your PA is connected"` and `./pa telegram_post admin "Admin topic test"`.
   She should see one message in General and one in a new "🗂 Admin" topic.
4. Start the line so she can see it the first time, and answer Claude Code's first-run questions (trust each
   folder, channel confirmation) with her watching. The line reads a fixed set of folders (Telegram inbox, its memory
   folder, the product and forms libraries in config.json); they are created if missing so she trusts them all now.
   If she later changes those library paths in config.json, do this visible start once more.
   - **Mac:** `./pa line start`, then she runs `tmux attach -t pa-line` in Terminal, answers any question there,
     then Ctrl-b, d to leave it running.
   - **Windows:** `./pa line start --visible`. A console window titled "PA - Telegram line" opens; she answers any
     question in it, then minimises it (closing it stops the line). From the next start on it runs hidden.
5. She sends "hi" in General from her phone. The PA should reply within a minute. If not: `./pa line status`, and
   look at the line (Mac: tmux attach; Windows: `./pa line stop` then `./pa line start --visible`).

## 3. Her client data (never invent anything)
- Ask for her client list / policy export and her pipeline (Excel file or a Google Sheet she downloads as .xlsx/.csv).
  She saves it in Data/ or gives you the path.
- Map her columns to the sheets in Data/Client Policies.xlsx (see its "Read me" sheet) and to Data/pipeline.csv.
  Show her the mapping (column → column) and 3 sample rows BEFORE writing. Keep a copy of her original file.
- Contacts: "Send reminders" = Yes for clients who should get premium/birthday reminders. WhatsApp link =
  https://wa.me/<country code + number, digits only>. "Call them" = the name she uses with them.
- Friends who should get a plain birthday wish instead of a review invite → config.json lists.no_birthday_review.
- TOP (transferred) clients: her list as Drafts/Follow-ups/top-list-YYYY-MM-DD.csv (templates/top-list-TEMPLATE.csv).
- GE rule: never log in to or browse Lifehub/the GE portal. If something is missing, ask her to download it.
- Test: `./pa daily_reminders --days 30 --dry` and `./pa top_intros` (if she has a TOP list). Show her a few drafts
  and adjust wording or settings she doesn't like (add a line to Preferences.md for each correction).

## 4. Product library and forms (optional)
- If she has GE product documents or blank forms she downloaded herself, put them in the folders named in
  config.json files.product_library / files.forms_library (or change the paths). Then `./pa library_search index`.
  On Windows, Documents is sometimes inside OneDrive (C:\Users\<her>\OneDrive\Documents): check where her files
  really are and set the paths to match. Best done BEFORE step 2.4; if you change the paths after the line has
  started, restart it visibly once (step 2.4) so she can trust the new folders.

## 5. Google connectors
- In the Claude desktop app (Settings → Connectors) she connects Google Calendar and Google Drive with her own
  Google account. The meeting-prep, briefs, week ahead and drive-organizer use them.

## 6. Scheduled tasks (Claude desktop app)
- Create each task in scheduled-tasks/README.md with the scheduled-tasks tool if you have it. In a Terminal /
  PowerShell chat you usually don't: then walk her through adding each one in the Claude desktop app's scheduled
  tasks (in the Code tab; menu names can change between app versions, so look with her): name, time, the PA folder
  as the task's folder, and the prompt file's text with `<PA>`
  replaced by this folder's full path in quotes. Ask before adding the optional auto-resume task (it uses some of
  her usage every 30 minutes).
- Run the daily To message task once now ("Run now") to test.

## 6b. WhatsApp reply check (optional, ask her)
- Explain in two lines: each night it looks at who sent the last WhatsApp message for everyone she has messaged
  from the To message list, read only, never message text. Ask if she wants it.
- If yes: WhatsApp desktop installed and signed in on this computer.
  - **Mac:** `./pa whatsapp_scan where` shows the database and the Python path; she adds that Python under System
    Settings > Privacy & Security > Full Disk Access (her setting: guide her, don't change it yourself).
  - **Windows:** WhatsApp desktop (Microsoft Store) must be open and signed in; nothing to allow. It must also be
    open at 4:07am for the nightly check (minimised is fine).
  - Then `./pa whatsapp_scan test`: it must say "OK: read N chats".
- If the test says the database layout is different or it isn't found, tell her the check needs adjusting for her
  WhatsApp version, leave it off, and add it to your list for the end (don't guess at other ways to read WhatsApp).
- When the test passes, set config.json whatsapp.enabled = true. Step 7 then schedules it for 4:07am.

## 7. Background jobs
- **Mac:** `./setup.sh background` · **Windows:** `./setup.cmd background` (no administrator rights needed).
  It turns on: the Telegram line at sign-in, the watchdog (every 5 min), Drive sync (every 10 min, only does
  something if config.json drive_sync has entries) and, if enabled, the WhatsApp check at 4:07am.
  (Mac: launchd jobs. Windows: a Startup-folder shortcut for the line and Task Scheduler tasks "AdvisorPA …".)
  Run it again whenever whatsapp.enabled changes. The line already running from step 2.4 carries on (never two
  copies). **Windows:** it is still in a visible window, so afterwards run `./pa line stop` then `./pa line start`
  to have it run hidden.
- Tell her about sleep: the computer must be awake for the PA to answer (Part 5 of her guide). She changes the
  setting herself.

## 8. Finish
- `./pa hq_status done coordinator "PA setup finished"`.
- Tell her in 5 lines: how to chat with the PA (General), what lands in each topic, the daily rhythm, how to say
  "done 1 3" / "skip 2", and "update the PA" for updates. List anything left from your list.
