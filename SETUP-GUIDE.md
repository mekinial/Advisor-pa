# Advisor PA: setup guide

The kit runs on a **Mac** or a **Windows PC**. Pick the guide for their computer:

- **Mac (MacBook, iMac, Mac mini):** [SETUP-GUIDE-MAC.md](SETUP-GUIDE-MAC.md)
- **Windows 10 or 11 PC / laptop:** [SETUP-GUIDE-WINDOWS.md](SETUP-GUIDE-WINDOWS.md)

Both end the same way: open Claude Code in the PA folder and say **Set me up, follow SETUP-FOR-CLAUDE.md**.
Claude does the rest with them (Telegram, their details, their client data, scheduled tasks, background jobs).

What is the same on both: the PA on Telegram, the agents, the daily To message list, briefs and wraps, the health
check, voice notes, the WhatsApp reply check (optional). What differs is only how things are installed and kept
running in the background:

| | Mac | Windows |
|---|---|---|
| Install apps | Homebrew (`brew install …`) | winget (`winget install …`) |
| First-time setup | `./setup.sh` | `.\setup.cmd` |
| Background jobs | `./setup.sh background` (launchd) | `.\setup.cmd background` (Task Scheduler + Startup folder) |
| Run a tool yourself | `./pa <tool>` in Terminal | `.\pa.cmd <tool>` in PowerShell |
| Telegram line | `./pa line start / stop / status` (hidden tmux window) | `.\pa.cmd line start / stop / status` (hidden console window) |
| Update | `./update.sh` | `.\update.cmd` (or double-click it) |

Inside Claude Code the commands are the same on both (`./pa …`): on Windows Claude Code uses Git Bash.
