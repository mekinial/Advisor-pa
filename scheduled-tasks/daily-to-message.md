Build today's client "To message" list for the adviser in <PA>/Me.md. Drafts only: never send any WhatsApp message, email or contact any client yourself, and never change her calendar. Work in <PA>.

0. Free times for intro messages: list her Google Calendar events from tomorrow through 12 days from now (Asia/Singapore). Write <PA>/Drafts/Reminders/busy.json as a JSON list of {"start": "YYYY-MM-DDTHH:MM", "end": "YYYY-MM-DDTHH:MM", "title": "..."} for every timed event that blocks her time. Leave out events marked free/transparent and events Me.md says can move, EXCEPT exams (e.g. "CMFAS"), which count as busy all day (00:00 to 23:59). Overwrite the file each day.
1. Run: cd <PA> && ./pa daily_reminders --telegram
   It reads Data/Client Policies.xlsx, writes Drafts/Reminders/reminders-YYYY-MM-DD.html, catches up missed days, adds the next transferred (TOP) clients (two free times from busy.json + her rules in config.json), carries over anything not yet marked done/skip, and posts ONE numbered list with WhatsApp buttons into the "📲 To message" topic of her private HQ group. It prints "Sent to Telegram: ...", "Telegram not sent: ..." or "Nothing to message today".
2. Nothing to message: end with "Nothing to message today".
3. Sent: end with a one-line summary (e.g. "To message list sent: 2 premium, 1 birthday, 5 TOP, 3 still open").
4. Telegram failed: send the HTML file with SendUserFile (status "proactive", display "render") as a backup, with a one-line caption saying why.
5. Script fails (e.g. the Excel file is open or missing): report the error in one or two lines; don't edit the spreadsheet or the script; don't re-run more than once.

No policy numbers, NRIC or bank details in anything you write.
