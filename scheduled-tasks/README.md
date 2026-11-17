# Scheduled tasks

Prompts for the Claude desktop app's scheduled tasks. They need the Google Calendar connector, so they run in
the Claude app, not launchd. During setup Claude creates them from these files. Times are Singapore time.
`<PA>` means the PA folder: replace it with the real full path when creating the task, in quotes
(Mac e.g. "/Users/jane/AdvisorPA"; Windows e.g. "C:\Users\jane\AdvisorPA": the tasks' shell on Windows is Git Bash,
which accepts that form in quotes). The computer must be awake and the Claude app open for them to run.

| Task | When | File |
|---|---|---|
| Daily To message list | 8:03am daily | daily-to-message.md |
| Morning brief | 8:30am daily | morning-brief.md |
| Nightly meeting briefs | 9:07pm daily | nightly-meeting-briefs.md |
| Evening wrap | 9:43pm daily | evening-wrap.md |
| Week ahead | Sunday 8:01pm | sunday-week-ahead.md |
| Auto-resume after usage limit (optional) | every 30 min | auto-resume.md |
