Post the adviser's "week ahead" summary to her private Telegram group HQ. Read only; never contact clients, never change her calendar. Folder: <PA>.

1. List her Google Calendar events for the next 7 days (tomorrow through 7 days from now), Asia/Singapore.
2. Keep only client meetings and work events she attends (Me.md says how she titles client meetings and what to ignore).
3. Write them to <PA>/Drafts/Meetings/week-ahead-meetings.txt, one per line, like "Tue 17 Nov 7:30pm · <you> x Nelson" (empty file if none).
4. Run: cd <PA> && ./pa week_ahead --meetings-file "Drafts/Meetings/week-ahead-meetings.txt" --telegram
5. End with one line: "Week ahead posted" or the error. If the script fails, report it in one or two lines; don't edit scripts or data, don't re-run more than once.
