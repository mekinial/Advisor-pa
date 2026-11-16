# Advisor PA: setup guide (MacBook)

About 60–90 minutes, best done together in person. You'll need: the MacBook (plugged in), her phone with
Telegram, her Claude Pro login, and her Google account. Claude does most of the typing; she approves.

What she gets: a PA on Telegram that she chats with from her phone, plus the specialist agents (follow-up,
forms, numbers, meeting briefs, client reports, proposals, investment write-ups, Drive tidy-up), the daily
"To message" list (premium and birthday reminders, TOP intros), morning brief, evening wrap, week ahead,
voice notes, background jobs and the optional financial health check.

**Her client data stays on her Mac.** The kit holds no client information (not yours, not anyone's). Her own
clients, settings and drafts live in files that are never uploaded and never touched by updates.

---

## Part 1: Install the basics (15 min)

Open **Terminal** (Cmd+Space, type Terminal). Paste each line, press Enter, wait for it to finish.

1. Homebrew (the Mac's app installer; asks for her Mac password once):
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   At the end it prints 2 lines starting with `echo` under "Next steps": run those too.
2. Git, Python, tmux:
   ```
   brew install git python@3.12 tmux
   ```
3. Claude Code:
   ```
   curl -fsSL https://claude.ai/install.sh | bash
   ```
4. Bun (the Telegram plugin needs it):
   ```
   curl -fsSL https://bun.sh/install | bash
   ```
5. Also install, if she doesn't have them: **Google Chrome** (used to make PDFs), **Google Drive for desktop**
   (only if she wants files synced to Drive) and the **Claude desktop app** (for the scheduled tasks).
6. Close Terminal and open it again (so the new commands are found).

## Part 2: Get the kit (5 min)

```
git clone https://github.com/<your-github-name>/advisor-pa.git ~/AdvisorPA
cd ~/AdvisorPA
./setup.sh
```
If GitHub asks her to sign in: she needs read access to your private repo. Add her GitHub account as a
collaborator first (GitHub repo → Settings → Collaborators), or see "Updates" below for other options.

`setup.sh` makes the Python environment, the folders, and her own private files (config.json, Me.md,
Preferences.md, Voice.md, a blank client workbook and pipeline).

## Part 3: Telegram bot and HQ group (15 min, on her phone)

1. In Telegram, open **@BotFather** → `/newbot` → pick a name (e.g. "<Her name> HQ") and a username ending
   in `bot`. BotFather replies with a **token**. Keep it private: don't paste it anywhere except in step 5 below.
2. Create a **new group** with only her and the new bot. Name it e.g. "<Her name> HQ".
3. Group settings → make the bot an **admin** → turn **Topics** on.
4. Send "hello" in the group.
5. On the Mac, in Terminal:
   ```
   cd ~/AdvisorPA
   claude
   ```
   Trust the folder when asked, sign in to her Claude account, then type:
   **Set me up, follow SETUP-FOR-CLAUDE.md**
   Claude walks through the rest: installing the Telegram plugin (she pastes the token when it asks),
   pairing her Telegram account, connecting the HQ group, her settings, her client data, the scheduled tasks
   and the background jobs. It asks her questions one at a time.

## Part 4: Her client data (15–30 min, inside the same Claude chat)

Claude asks for her own client list and pipeline (her Excel file or a Google Sheet download) and fills
`Data/Client Policies.xlsx` and `Data/pipeline.csv` from it. It shows her what it mapped before saving.
- The workbook needs, per policy: policyholder, product, status, issue date, premium frequency/status/expiry.
  Per contact: mobile/WhatsApp link, birthday, "Call them" name, "Send reminders" = Yes.
- **GE systems:** GE does not allow AI tools to be connected to its platforms. Claude will never log in to or
  browse Lifehub or the GE portal. She downloads any report or product document herself and gives Claude the file.
- TOP clients: she types or exports her TOP list as `Drafts/Follow-ups/top-list-YYYY-MM-DD.csv`
  (columns: Name, Postal code, Call name, Area, Flag; see templates/top-list-TEMPLATE.csv).

## Part 5: Keep it running

- The Mac must be **awake, signed in and online** for the PA to answer and for the daily tasks to run. When it
  sleeps, messages wait and are picked up when it wakes (scheduled tasks catch up when the Claude app is open).
- On a MacBook: keep it plugged in, and in System Settings → Battery → Options, turn on "Prevent automatic sleeping
  on power adapter when the display is off". Closing the lid still sleeps it. (She changes this herself.)
- The **Claude desktop app** must be open for the scheduled tasks (8am list, briefs, wraps).
- Handy commands (in Terminal, inside ~/AdvisorPA):
  - Start / stop the Telegram line: `Tools/start_line.sh` · `Tools/stop_line.sh`
  - See the line working: `tmux attach -t pa-line` (leave with Ctrl-b, then d)
  - Get the latest version: `./update.sh` (or tell the PA on Telegram "update the PA")

## Updates

When you improve the kit, you push to the GitHub repo; she runs `./update.sh` (or asks the PA to). Only the
shared code changes. Her config.json, Me.md, Preferences.md, Voice.md, Data/ and Drafts/ are never part of the
repo and never touched.

## Not included in this version

- **WhatsApp reply checker**: the Windows version reads the WhatsApp app in a Windows-only way. A Mac version
  needs building and testing on her Mac.
- Agent Office view and reel generators (left out on purpose).
- Anything that logs in to GE systems (left out on purpose, see Part 4).

## If something goes wrong

- Telegram not answering: `Tools/start_line.sh`, then `tmux attach -t pa-line` to see what it's doing.
  The watchdog restarts it every 5 minutes if it's down.
- "Not sent: HQ must contain only you and the bot": someone else is in the group. Remove them.
- Anything else: open `claude` in ~/AdvisorPA and describe the problem.
