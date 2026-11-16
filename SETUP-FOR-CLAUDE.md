# Setup steps for Claude (run on the adviser's Mac, in this folder)

She typed "Set me up, follow SETUP-FOR-CLAUDE.md". Walk her through these steps in order. Ask ONE question at a
time, in plain words, and wait. Do the typing yourself where you can; she approves. Log progress with
`./pa hq_status` once Telegram works. Ground rules from CLAUDE.md apply throughout (never contact anyone, never
connect to GE systems, never print or paste the bot token back to her).

If a step fails, explain in one line, fix it if you can, and keep a short list of anything left for the end.

## 0. Check the basics
- `./setup.sh` has been run (`.venv/` exists). If not, run it.
- `claude --version`, `tmux -V`, `bun --version` (or ~/.bun/bin/bun), `git --version` all work.
  Missing ones: give her the install line from SETUP-GUIDE.md Part 1.

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
1. Install the plugin: `/plugin marketplace add anthropics/claude-plugins-official` (if needed), then
   `/plugin install telegram@claude-plugins-official`. Read the plugin's README (in ~/.claude/plugins/) for the
   exact configure and pairing commands of the installed version, and follow them:
   - configure the bot token (she pastes it; never repeat it back),
   - she sends a DM to her bot, then pair her account so access.json "allowFrom" holds only her user id,
   - set the DM policy to allowlist.
2. The HQ group: she created it with only herself + the bot, bot is admin, Topics on, and sent "hello".
   Make sure no Telegram line is running (`Tools/stop_line.sh`), then run `./pa hq_setup`. It saves the group id
   and adds the group to the plugin's access.json (only her, no @mention needed). Then `./pa hq_setup --check`.
3. Test: `./pa telegram_post main "👋 Your PA is connected"` and `./pa telegram_post admin "Admin topic test"`.
   She should see one message in General and one in a new "🗂 Admin" topic.
4. Start the line: `Tools/start_line.sh`. Then `tmux attach -t pa-line` with her watching: if Claude Code shows a
   first-run prompt (trust folder, channel confirmation), she answers it there; then Ctrl-b, d to leave it running.
5. She sends "hi" in General from her phone. The PA should reply within a minute. If not, check
   `tmux attach -t pa-line`.

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

## 5. Google connectors
- In the Claude desktop app (Settings → Connectors) she connects Google Calendar and Google Drive with her own
  Google account. The meeting-prep, briefs, week ahead and drive-organizer use them.

## 6. Scheduled tasks (Claude desktop app)
- Create each task in scheduled-tasks/README.md with the scheduled-tasks tool (or tell her how to add it in the app),
  using the prompt file's text with `<PA>` replaced by this folder's full path. Ask before adding the optional
  auto-resume task (it uses some of her usage every 30 minutes).
- Run the daily To message task once now ("Run now") to test.

## 7. Background jobs
- `./setup.sh background` turns on: the Telegram line at login, the watchdog (every 5 min) and Drive sync (every
  10 min, only does something if config.json drive_sync has entries).
- Tell her about sleep: the Mac must be awake for the PA to answer (see SETUP-GUIDE.md Part 5). She changes the
  setting herself.

## 8. Finish
- `./pa hq_status done coordinator "PA setup finished"`.
- Tell her in 5 lines: how to chat with the PA (General), what lands in each topic, the daily rhythm, how to say
  "done 1 3" / "skip 2", and "update the PA" for updates. List anything left from your list.
