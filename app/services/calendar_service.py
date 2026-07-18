# app/services/calendar_service.py
"""
Google Calendar service (Phase 3 - Step 4).

Creates a Calendar event with a Google Meet link for a confirmed
interview, inviting both the candidate and HR. Returns the Meet link
so it can be placed into the confirmation email.

Uses the calendar.events scope that was authorized back in Step 1.
"""

import uuid
from datetime import datetime, timedelta

from googleapiclient.discovery import build

from app.services.google_oauth_service import GoogleOAuthService
from app.config import (
    GOOGLE_ACCOUNT_EMAIL,
    INTERVIEW_TIMEZONE,
    INTERVIEW_DURATION_MINUTES,
)


class CalendarService:
    """Creates interview calendar events with Meet links."""

    # Slot label -> 24h start time. Keep in sync with INTERVIEW_SLOTS.
    _SLOT_TO_24H = {
        "1:30 PM": "13:30",
        "2:30 PM": "14:30",
        "3:30 PM": "15:30",
        "4:30 PM": "16:30",
    }

    @staticmethod
    def _parse_start(interview_date: str, slot_time: str) -> datetime:
        """
        Combine the booking date (YYYY-MM-DD) and slot label into a
        naive datetime (local to INTERVIEW_TIMEZONE). We send the
        timezone separately to Google, so a naive local time is correct.
        """
        hhmm = CalendarService._SLOT_TO_24H.get(slot_time)
        if not hhmm:
            # Fallback: try to parse "1:30 PM" directly.
            parsed = datetime.strptime(slot_time, "%I:%M %p")
            hhmm = parsed.strftime("%H:%M")

        return datetime.strptime(f"{interview_date} {hhmm}", "%Y-%m-%d %H:%M")

    @staticmethod
    def create_interview_event(candidate: dict, interview_date: str, slot_time: str) -> str | None:
        """
        Create the calendar event + Meet link.

        Returns the Meet join URL on success, or None on failure
        (booking should still succeed even if this fails).
        """
        creds = GoogleOAuthService.get_credentials()
        if creds is None:
            print("[Calendar] Google not connected; skipping event creation.")
            return None

        try:
            start_dt = CalendarService._parse_start(interview_date, slot_time)
            end_dt = start_dt + timedelta(minutes=INTERVIEW_DURATION_MINUTES)

            service = build("calendar", "v3", credentials=creds)

            event_body = {
                "summary": f"Interview - {candidate['name']} (VSI)",
                "description": (
                    f"Interview with {candidate['name']} for Virtual Solutions India.\n\n"
                    "Please join via the Google Meet link at the scheduled time."
                ),
                "start": {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": INTERVIEW_TIMEZONE,
                },
                "end": {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": INTERVIEW_TIMEZONE,
                },
                # Invite both the candidate and HR (the connected account).
                "attendees": [
                    {"email": candidate["email"]},
                    {"email": GOOGLE_ACCOUNT_EMAIL},
                ],
                # Ask Google to create a Meet conference for this event.
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid.uuid4()),
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 60},
                        {"method": "popup", "minutes": 10},
                    ],
                },
            }

            created = (
                service.events()
                .insert(
                    calendarId="primary",
                    body=event_body,
                    conferenceDataVersion=1,   # required to create Meet links
                    sendUpdates="all",         # email the invite to attendees
                )
                .execute()
            )

            # Extract the Meet link from the created event.
            meet_link = created.get("hangoutLink")
            if not meet_link:
                # Fallback: dig into conferenceData entry points.
                for entry in created.get("conferenceData", {}).get("entryPoints", []):
                    if entry.get("entryPointType") == "video":
                        meet_link = entry.get("uri")
                        break

            print(f"[Calendar] Event created for {candidate['name']}: {meet_link}")
            return meet_link

        except Exception as e:
            print(f"[Calendar] Failed to create event: {e}")
            return None