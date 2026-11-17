# Advisor PA: setup guide for a Windows PC

(Setting up on a Mac? Use SETUP-GUIDE-MAC.md instead.)

About 60–90 minutes, best done together in person. You'll need: the PC or laptop (Windows 10 or 11, plugged in),
their phone with Telegram, their Claude Pro login, and their Google account. Claude does most of the typing; they approve.
Nothing in this guide needs administrator rights except installing the apps in Part 1 (Windows may ask "Allow this
app to make changes?": they click Yes).

What they get: a PA on Telegram that they chat with from their phone, plus the specialist agents (follow-up,
forms, numbers, meeting briefs, client reports, proposals, investment write-ups, Drive tidy-up), the daily
"To message" list (premium and birthday reminders, TOP intros), morning brief, evening wrap, week ahead,
voice notes, background jobs and the optional financial health check.

**Their client data stays on their PC.** The kit holds no client information (not yours, not anyone's). Their own
clients, settings and drafts live in files that are never uploaded and never touched by updates.

---

## Part 1: Install the basics (15 min)

Open **PowerShell**: Start menu → type `PowerShell` → open **Windows PowerShell** (not "as administrator").
Paste each line (Ctrl+V, or right-click), press Enter, wait for it to finish. `winget` is Windows' own app installer.

1. Git (Claude Code needs it on Windows; it also brings Git Bash):
   ```
   winget install --id Git.Git -e
   ```
2. Python 3.12 and the GitHub sign-in tool:
   ```
   winget install --id Python.Python.3.12 -e
   winget install --id GitHub.cli -e
   ```
3. Claude Code:
   ```
   irm https://claude.ai/install.ps1 | iex
   ```
   If it says a folder is not in your PATH, follow what it shows (or let Claude fix it later in the setup chat).
4. Bun (the Telegram plugin needs it):
   ```
   irm bun.sh/install.ps1 | iex
   ```
5. Also install, if they don't have them: **Google Drive for desktop** (only if they want files synced to
   Drive) and the **Claude desktop app** (for the scheduled tasks). PDFs are printed with Microsoft Edge, which
   every Windows PC has (Google Chrome works too).
6. **Close PowerShell and open it again** (so the new commands are found). Check: `git --version`,
   `py -3.12 --version`, `claude --version` and `bun --version` each print a version.
   If `winget` itself is "not recognized": open the Microsoft Store, search **App Installer**, update it, try again.

## Part 2: Get the kit (5 min)

First they accept the GitHub invite to the private repo (email from GitHub, or github.com/notifications).
Then, in PowerShell:
```
gh auth login
```
Pick: GitHub.com → HTTPS → Yes (authenticate Git) → Login with a web browser. It shows a code; the browser opens,
they sign in to their GitHub account and enter the code. Then:
```
gh repo clone mekinial/advisor-pa $HOME\AdvisorPA
cd $HOME\AdvisorPA
.\setup.cmd
```
(After this, `.\update.cmd` can pull updates without asking them to sign in again.)

`setup.cmd` makes the Python environment, the folders, and their own private files (config.json, Me.md,
Preferences.md, Voice.md, a blank client workbook and pipeline). The PA folder is `C:\Users\<their name>\AdvisorPA`.
Keep it there, outside OneDrive: their client files shouldn't sync to the cloud, and OneDrive can lock files while
the PA is using them. Setup may take 5–10 minutes the first time (the voice-note transcriber is a big download).

## Part 3: Telegram bot and HQ group (15 min, on their phone)

1. In Telegram, open **@BotFather** → `/newbot` → pick a name (e.g. "<Their name> HQ") and a username ending
   in `bot`. BotFather replies with a **token**. Keep it private: don't paste it anywhere except in step 5 below.
2. Create a **new group** with only them and the new bot. Name it e.g. "<Their name> HQ".
3. Group settings → make the bot an **admin** → turn **Topics** on.
4. Send "hello" in the group.
5. On the PC, in PowerShell:
   ```
   cd $HOME\AdvisorPA
   claude
   ```
   Trust the folder when asked, sign in to their Claude account, then type:
   **Set me up, follow SETUP-FOR-CLAUDE.md**
   Claude walks through the rest: installing the Telegram plugin (they paste the token when it asks),
   pairing their Telegram account, connecting the HQ group, their settings, their client data, the scheduled tasks
   and the background jobs. It asks them questions one at a time.

## Part 4: Their client data (15–30 min, inside the same Claude chat)

Claude asks for their own client list and pipeline (their Excel file or a Google Sheet download) and fills
`Data\Client Policies.xlsx` and `Data\pipeline.csv` from it. It shows them what it mapped before saving.
- The workbook needs, per policy: policyholder, product, status, issue date, premium frequency/status/expiry.
  Per contact: mobile/WhatsApp link, birthday, "Call them" name, "Send reminders" = Yes.
- **Close Excel** before the daily list runs: a workbook that is open in Excel can't be read.
- **GE systems:** GE does not allow AI tools to be connected to its platforms. Claude will never log in to or
  browse Lifehub or the GE portal. They download any report or product document themselves and give Claude the file.
- TOP clients: they type or export their TOP list as `Drafts\Follow-ups\top-list-YYYY-MM-DD.csv`
  (columns: Name, Postal code, Call name, Area, Flag; see templates\top-list-TEMPLATE.csv).

## Their own files, and how the PA learns

Every adviser has their own copy of these, made on their computer during setup. Nothing is shared between
advisers, nothing goes to GitHub, and updates never touch them.

| File / folder | What it is | How it gets filled |
|---|---|---|
| Me.md | Who they are: name, what clients call them, how they title meetings, events to ignore, where they're based | Claude asks during setup. To change it later, just tell the PA |
| Preferences.md | Their likes and dislikes for drafts | **Learns from corrections**: each time they correct something ("too formal", "no emojis for older clients"), the PA adds a dated rule and replies "📌 Noted for next time" |
| Voice.md | How they write, so drafts sound like them | **Learns from their Telegram messages** (writing style only, kept on their computer). Once a day the PA adds a line if it notices something new |
| config.json | Settings: meeting times to offer, their area, friends who get a plain birthday wish, Drive sync, WhatsApp check | Claude fills it in during setup. Change it any time by asking the PA |
| Data\ | Their client workbook and pipeline | Filled from their own client list in Part 4. Meeting notes they send update the pipeline |
| Drafts\ | Everything the agents write | Drafts only: nothing is ever sent from here |
| Forms\Blank\ | Blank forms to pre-fill | They put in forms they downloaded themselves |
| The bot and HQ group | Their own Telegram bot (Part 3), paired to their own account only | Never share a bot or group with another adviser |

The PA also keeps its own memory notes on their computer for things it works out along the way.
**The more they correct it, the better it gets:** say what's wrong in plain words and it remembers.

## Part 5: Keep it running

- The PC must be **on, signed in and online** for the PA to answer and for the daily tasks to run. When it
  sleeps, messages wait and are picked up when it wakes (scheduled tasks catch up when the Claude app is open).
- Sleep (they change this themselves): Settings → System → Power (& battery) → Screen and sleep → "When plugged in,
  put my device to sleep after" → **Never**. The screen can still turn off. On a laptop, closing the lid sleeps
  it unless they change "Choose what closing the lid does" in Control Panel → Power Options.
- Windows Update sometimes restarts the PC overnight. After they sign in again, the line starts by itself.
- The **Claude desktop app** must be open for the scheduled tasks (8am list, briefs, wraps).
- Background jobs (turned on by Claude at the end of setup with `.\setup.cmd background`):
  - **Telegram line at sign-in:** a shortcut "AdvisorPA Telegram line" in their Startup folder.
  - **Watchdog** every 5 min, **Drive sync** every 10 min, optional **WhatsApp check** at 4:07am: Task Scheduler
    tasks named "AdvisorPA …". Turn them all off with `.\setup.cmd remove-background`.
- Handy commands (in PowerShell, inside $HOME\AdvisorPA):
  - Start / stop / check the Telegram line: `.\pa.cmd line start` · `.\pa.cmd line stop` · `.\pa.cmd line status`
  - See the line working: `.\pa.cmd line stop`, then `.\pa.cmd line start --visible` (a window opens; leave it
    open, or minimise it; closing the window stops the line)
  - Get the latest version: `.\update.cmd` (or double-click update.cmd, or tell the PA on Telegram "update the PA")

## Updates

When you improve the kit, you push to the GitHub repo; they run `.\update.cmd` (or ask the PA to). Only the
shared code changes. Their config.json, Me.md, Preferences.md, Voice.md, Data\ and Drafts\ are never part of the
repo and never touched.

## Optional: WhatsApp reply check

Each night at 4:07am it checks who sent the last WhatsApp message for everyone they have messaged from the To
message list, and posts "your turn / waiting / unsure" to the Admin topic ("your turn" people also go on the next
day's list). It is read only: it never opens a chat, types or sends, and it never reads message text.
- On Windows it reads the chat list of the **WhatsApp desktop app** (Microsoft Store) the way a screen reader does,
  so WhatsApp desktop must be **open and signed in** at 4:07am (leave it open, minimised is fine).
- Test: `.\pa.cmd whatsapp_scan test` should say "OK: read N chats". Claude then turns it on during setup.

## Not included in this version

- Agent Office view and reel generators (left out on purpose).
- Anything that logs in to GE systems (left out on purpose, see Part 4).

## If something goes wrong

- Telegram not answering: `.\pa.cmd line status`. Not running → `.\pa.cmd line start`. Running but silent →
  `.\pa.cmd line stop`, then `.\pa.cmd line start --visible` and look at the window: a start-up question waiting
  for an answer (e.g. "trust this folder?") is the usual cause after an update. The watchdog restarts a line that
  is down every 5 minutes, and posts in General if it sees one stuck on a start-up question.
- "running scripts is disabled on this system": use the `.cmd` files (`.\setup.cmd`, `.\pa.cmd`, `.\update.cmd`),
  which don't need any PowerShell setting changed.
- "Not sent: HQ must contain only you and the bot": someone else is in the group. Remove them.
- Windows Security or SmartScreen asks about Python or Bun the first time: that's expected for newly installed apps.
- Anything else: open `claude` in $HOME\AdvisorPA and describe the problem.
