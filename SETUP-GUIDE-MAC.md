# Advisor PA: setup guide for a Mac

(Setting up on a Windows PC? Use SETUP-GUIDE-WINDOWS.md instead.)

About 60–90 minutes, best done together in person. You'll need: the Mac (a MacBook plugged in), their phone with
Telegram, their Claude Pro login, and their Google account. Claude does most of the typing; they approve.

What they get: a PA on Telegram that they chat with from their phone, plus the specialist agents (follow-up,
forms, numbers, meeting briefs, client reports, proposals, investment write-ups, Drive tidy-up), the daily
"To message" list (premium and birthday reminders, TOP intros), morning brief, evening wrap, week ahead,
voice notes, background jobs and the optional financial health check.

**Their client data stays on their Mac.** The kit holds no client information (not yours, not anyone's). Their own
clients, settings and drafts live in files that are never uploaded and never touched by updates.

---

## Part 1: Install the basics (15 min)

Open **Terminal** (Cmd+Space, type Terminal). Paste each line, press Enter, wait for it to finish.

1. Homebrew (the Mac's app installer; asks for their Mac password, and may install Apple's "Command Line Tools"
   first, which can take 10 minutes):
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   At the end it shows a few commands under "Next steps" (to add Homebrew to the PATH): copy and run those too.
2. Git, GitHub sign-in tool, Python, tmux:
   ```
   brew install git gh python@3.12 tmux
   ```
3. Claude Code:
   ```
   curl -fsSL https://claude.ai/install.sh | bash
   ```
   If it says a folder is not in your PATH, run the line it shows.
4. Bun (the Telegram plugin needs it):
   ```
   curl -fsSL https://bun.sh/install | bash
   ```
5. Also install, if they don't have them: **Google Chrome** (used to make PDFs), **Google Drive for desktop**
   (only if they want files synced to Drive) and the **Claude desktop app** (for the scheduled tasks).
6. Close Terminal and open it again (so the new commands are found). Check: `git --version`, `python3.12 --version`,
   `tmux -V`, `claude --version` and `bun --version` each print a version.

## Part 2: Get the kit (5 min)

First they accept the GitHub invite to the private repo (email from GitHub, or github.com/notifications).
Then:
```
gh auth login
```
Pick: GitHub.com → HTTPS → Yes (authenticate Git) → Login with a web browser. It shows a code; the browser opens,
they sign in to their GitHub account and enter the code. Then:
```
gh repo clone mekinial/advisor-pa ~/AdvisorPA
cd ~/AdvisorPA
./setup.sh
```
(After this, `./update.sh` can pull updates without asking them to sign in again.)

`setup.sh` makes the Python environment, the folders, and their own private files (config.json, Me.md,
Preferences.md, Voice.md, a blank client workbook and pipeline).

## Part 3: Telegram bot and HQ group (15 min, on their phone)

1. In Telegram, open **@BotFather** → `/newbot` → pick a name (e.g. "<Their name> HQ") and a username ending
   in `bot`. BotFather replies with a **token**. Keep it private: don't paste it anywhere except in step 5 below.
2. Create a **new group** with only them and the new bot. Name it e.g. "<Their name> HQ".
3. Group settings → make the bot an **admin** → turn **Topics** on.
4. Send "hello" in the group.
5. On the Mac, in Terminal:
   ```
   cd ~/AdvisorPA
   claude
   ```
   Trust the folder when asked, sign in to their Claude account, then type:
   **Set me up, follow SETUP-FOR-CLAUDE.md**
   Claude walks through the rest: installing the Telegram plugin (they paste the token when it asks),
   pairing their Telegram account, connecting the HQ group, their settings, their client data, the scheduled tasks
   and the background jobs. It asks them questions one at a time.

## Part 4: Their client data (15–30 min, inside the same Claude chat)

Claude asks for their own client list and pipeline (their Excel file or a Google Sheet download) and fills
`Data/Client Policies.xlsx` and `Data/pipeline.csv` from it. It shows them what it mapped before saving.
- The workbook needs, per policy: policyholder, product, status, issue date, premium frequency/status/expiry.
  Per contact: mobile/WhatsApp link, birthday, "Call them" name, "Send reminders" = Yes.
- **GE systems:** GE does not allow AI tools to be connected to its platforms. Claude will never log in to or
  browse Lifehub or the GE portal. They download any report or product document themselves and give Claude the file.
- TOP clients: they type or export their TOP list as `Drafts/Follow-ups/top-list-YYYY-MM-DD.csv`
  (columns: Name, Postal code, Call name, Area, Flag; see templates/top-list-TEMPLATE.csv).

## Their own files, and how the PA learns

Every adviser has their own copy of these, made on their computer during setup. Nothing is shared between
advisers, nothing goes to GitHub, and updates never touch them.

| File / folder | What it is | How it gets filled |
|---|---|---|
| Me.md | Who they are: name, what clients call them, how they title meetings, events to ignore, where they're based | Claude asks during setup. To change it later, just tell the PA |
| Preferences.md | Their likes and dislikes for drafts | **Learns from corrections**: each time they correct something ("too formal", "no emojis for older clients"), the PA adds a dated rule and replies "📌 Noted for next time" |
| Voice.md | How they write, so drafts sound like them | **Learns from their Telegram messages** (writing style only, kept on their computer). Once a day the PA adds a line if it notices something new |
| config.json | Settings: meeting times to offer, their area, friends who get a plain birthday wish, Drive sync, WhatsApp check | Claude fills it in during setup. Change it any time by asking the PA |
| Data/ | Their client workbook and pipeline | Filled from their own client list in Part 4. Meeting notes they send update the pipeline |
| Drafts/ | Everything the agents write | Drafts only: nothing is ever sent from here |
| Forms/Blank/ | Blank forms to pre-fill | They put in forms they downloaded themselves |
| The bot and HQ group | Their own Telegram bot (Part 3), paired to their own account only | Never share a bot or group with another adviser |

The PA also keeps its own memory notes on their computer for things it works out along the way.
**The more they correct it, the better it gets:** say what's wrong in plain words and it remembers.

## Part 5: Keep it running

- The Mac must be **awake, signed in and online** for the PA to answer and for the daily tasks to run. When it
  sleeps, messages wait and are picked up when it wakes (scheduled tasks catch up when the Claude app is open).
- On a MacBook: keep it plugged in, and in System Settings → Battery → Options, turn on "Prevent automatic sleeping
  on power adapter when the display is off". Closing the lid still sleeps it. (They change this themselves.)
- The **Claude desktop app** must be open for the scheduled tasks (8am list, briefs, wraps).
- Handy commands (in Terminal, inside ~/AdvisorPA):
  - Start / stop / check the Telegram line: `./pa line start` · `./pa line stop` · `./pa line status`
  - See the line working: `tmux attach -t pa-line` (leave with Ctrl-b, then d)
  - Get the latest version: `./update.sh` (or tell the PA on Telegram "update the PA")

## Updates

When you improve the kit, you push to the GitHub repo; they run `./update.sh` (or ask the PA to). Only the
shared code changes. Their config.json, Me.md, Preferences.md, Voice.md, Data/ and Drafts/ are never part of the
repo and never touched.

## Optional: WhatsApp reply check

Each night at 4:07am it checks who sent the last WhatsApp message for everyone they have messaged from the To
message list, and posts "your turn / waiting / unsure" to the Admin topic ("your turn" people also go on the next
day's list). It is read only: it never opens a chat, types or sends, and it never reads message text.
- Needs **WhatsApp desktop** (Mac App Store) installed and signed in on the Mac.
- macOS asks for one permission: System Settings → Privacy & Security → **Full Disk Access** → add the PA's Python
  (`./pa whatsapp_scan where` prints the exact path and steps). They switch it on themselves.
- Test: `./pa whatsapp_scan test` should say "OK: read N chats". Claude then turns it on during setup.

## macOS pop-ups to expect (they answer them themselves)

- "Terminal would like to access files in your Documents folder": Allow (the product and forms libraries live there).
- "Background Items Added" after `./setup.sh background`: expected, those are the PA's background jobs.
- The first "screenshot" from Telegram asks for **Screen Recording** permission for Terminal (System Settings →
  Privacy & Security); only if they want that feature.

## Not included in this version

- Agent Office view and reel generators (left out on purpose).
- Anything that logs in to GE systems (left out on purpose, see Part 4).

## If something goes wrong

- Telegram not answering: `./pa line start`, then `tmux attach -t pa-line` to see what it's doing (a start-up
  question waiting for an answer is the usual cause after an update).
  The watchdog restarts it every 5 minutes if it's down.
- "Not sent: HQ must contain only you and the bot": someone else is in the group. Remove them.
- Anything else: open `claude` in ~/AdvisorPA and describe the problem.
