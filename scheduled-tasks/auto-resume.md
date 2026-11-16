Optional: this uses some of her Claude usage every 30 minutes. On the Pro plan, consider leaving it off.

Auto-resume check: some of her Claude Code chats in <PA> may have stopped mid-task because the usage limit ran out (or a temporary API error). Wake them up now that the limit has reset. Be quick and cheap: do nothing else.

1. mcp__ccd_session_mgmt__list_sessions (limit 25). Keep sessions that are NOT archived, have isRunning false, lastActivityAt within the last 12 hours, and a title other than "Auto-resume after usage limit".
2. For each, mcp__ccd_session_mgmt__list_events (limit 3). It counts as stopped if the last entry is an error ("usage limit", "limit reached", "resets", "rate limit", "overloaded", "API Error") or the last assistant message says it stopped because of the limit. Leave it alone if it finished, asked her a normal question, or she wrote after it.
3. For each stopped session, mcp__ccd_session_mgmt__send_message with: "Auto-resume: your usage limit has reset (or the API error has cleared). Please continue exactly where you left off. If you were waiting on the adviser, just restate the question in one line." At most one per session per run; never if the last entry is already an unanswered "Auto-resume:" message.
4. If the Telegram line (tmux session pa-line) stopped on the limit, post once per 12 hours: cd <PA> && ./pa telegram_post main "🔋 Usage limit has reset, I'm back. Resend anything you sent while I was paused."
5. Archive (mcp__ccd_session_mgmt__archive_session) old runs of this task and of the other scheduled tasks that were last active more than 24 hours ago. Never archive any other chat.
6. If nothing stopped, finish with "Nothing to resume." Never contact clients, never edit files.
