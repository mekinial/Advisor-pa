---
name: add-meeting-to-calendar
description: Put a confirmed client meeting or appointment on the adviser's own Google Calendar (no guests, no invite), with travel buffers. Use whenever a date AND time for a meeting is confirmed - a client says yes to an offered slot in a WhatsApp screenshot, the adviser says "X confirmed Thu 3pm", after-meeting notes agree a next meeting, the nightly WhatsApp check reads a confirmed time - and also when they ask "put it in my calendar" / "add to calendar". Also use when the details of a meeting the PA added change (place agreed, time moved, call instead of meeting).
---

# Add confirmed meetings to the adviser's calendar

Settings: config.json `calendar` (see config.example.json) and the adviser's name in `me.short_name`.

**Only automatic if `calendar.auto_add_confirmed` is true** (the adviser agreed to this during setup or later in
chat). If it is false, show the event in one line ("📅 Add Mary, Thu 3 Dec 12pm, Tampines to your calendar?") and
add it only after their yes. Either way this is the adviser's OWN calendar: it is never a client invite.

## When it counts as confirmed
- Both a date and a time are agreed by both sides (the client picked one of the offered slots, or the adviser agreed
  to theirs).
- "Maybe", "let me check", a day with no time, or only the adviser offering = NOT confirmed. Don't add; keep it as a
  follow-up (`./pa todo_list add`).
- If the place isn't settled yet, still add it with location "Place TBC" (or "<area> (place TBC)").

## Steps
1. **Duplicates and clashes**: `list_events` (Google Calendar) for that day. If an event for this person already
   exists at that time, don't add another. If it clashes with something else, still add it but say so in one line.
   Never offer or book inside `schedule.blocks` from config.json.
2. **Create the event** with `create_event` on the primary calendar:
   - summary: `<Client first name> x <me.short_name>: <Intro & get to know | Review | Fact-find | Proposal | Claim docs | ...>`
     (add "(lunch)" / "(call)" / "(Zoom)" if that's the format)
   - Length: the FIRST meet-up with a new or transferred (TOP) client is an intro to get to know each other, not a
     review: title "Intro & get to know", `calendar.intro_minutes` (default 30; a meal: 60). A real review is
     `calendar.review_minutes` (default 120, it includes small talk). A phone call: `calendar.call_minutes`.
     Anything else: `calendar.default_minutes` (default 60), unless the chat says otherwise.
   - start/end: local time (Asia/Singapore unless Me.md says otherwise).
   - location: the place, or "Place TBC".
   - description: one short line of context (e.g. "TOP client, first meet-up; plan to go through existing cover")
     + "Added by PA from confirmed chat." (this marks it as a PA-made event).
   - NO attendees, `notificationLevel: NONE`. Never put NRIC, policy numbers, bank or health details in an event.
3. **Travel buffers**, as separate events so the meeting time itself stays correct (grey colorId 8,
   useDefaultReminders false, no attendees, notificationLevel NONE, description "Added by PA"):
   - **In person:** `🚗 Travel to <First name> (<place>)` just before and `🚗 Travel back from <First name>` just
     after, each `calendar.travel_minutes` long (default 30). Use `calendar.far_travel_minutes` (default 45) when the
     place is in one of `calendar.far_areas` (areas far from `calendar.home_area`). If the place is TBC, use the
     normal length and fix it once the place is known.
   - **Zoom / video call:** ONE block `🎧 Find a quiet spot (Zoom with <First name>)`, `calendar.video_prep_minutes`
     (default 15) before, nothing after.
   - **Phone call:** no buffer.
   If a buffer clashes with something, say so in one line.
4. **Pipeline**: `./pa pipeline_update "<name>" --note "<meeting> booked <date time>, <place>" --next "<meeting>"
   --next-date YYYY-MM-DD`
5. **Tell them in one line** (General): "📅 Added: Mary, Thu 3 Dec 12.30pm, Tampines (+ 🚗 30 min each way)".
   If the place is TBC, say so, so they remember to fix it.

## Changes later
- As soon as new information shows up anywhere (a WhatsApp chat read by the nightly check, the WhatsApp notes,
  a screenshot, their words), update events **the PA added** ("Added by PA" in the description, or a 🚗 / 🎧 block):
  place agreed ("Place TBC" → the venue), time moved, in person ↔ call ↔ Zoom. Use `update_event`
  (notificationLevel NONE) on the meeting AND its buffers (titles carry the place; switch to far-area buffer length
  if needed; in person → Zoom: replace the 🚗 buffers with one 🎧 block; → phone call: no buffer). Never delete a
  buffer yourself: rename one that's no longer needed to "(not needed: now a call)" and tell them. Say each change
  in one line ("📅 Mary: place → Tampines Hub").
- **Events the adviser or anyone else made: never edit, move or delete them.** Tell the adviser instead.
- Cancelled: don't delete; tell them and let them remove it (one tap).

## Client invites (separate, unchanged)
Sending the client a calendar invite still needs the adviser's "yes" for that one invite (meeting-prep), with the
full invite shown first and a known email (never guessed). Offer it in one line after adding the event, only if the
client's email is on file.
