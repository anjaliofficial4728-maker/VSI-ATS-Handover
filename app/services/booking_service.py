# app/services/booking_service.py
"""
Interview slot booking service (Phase 3 - Step 3).

Responsibilities:
- Generate a per-candidate booking token (used in the email link).
- Report which slots are still free for the bookable day.
- Atomically book a slot (double-booking prevented by the DB unique
  constraint on (interview_date, slot_time)).
- On success: set status interview_confirmed and send a confirmation
  email immediately.
"""

import secrets
from datetime import datetime, timezone

from app.services.calendar_service import CalendarService

from app.database import supabase
from app.services.email_service import EmailService
from app.config import (
    INTERVIEW_SLOTS,
    INTERVIEW_BOOKING_DATE,
    STATUS_INTERVIEW_CONFIRMED,
)


class BookingService:
    """Handles interview slot availability and booking."""

    # ---------- token ----------

    @staticmethod
    def ensure_booking_token(candidate: dict) -> str:
        """
        Return the candidate's booking token, generating and storing
        one if they don't have it yet.
        """
        token = candidate.get("booking_token")
        if token:
            return token

        token = secrets.token_urlsafe(24)
        supabase.table("candidates").update({
            "booking_token": token,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", candidate["id"]).execute()
        return token

    @staticmethod
    def get_candidate_by_token(token: str):
        """Find the candidate that owns this booking token, or None."""
        if not token:
            return None
        result = (
            supabase.table("candidates")
            .select("*")
            .eq("booking_token", token)
            .execute()
        )
        return result.data[0] if result.data else None

    # ---------- availability ----------

    @staticmethod
    def get_taken_slots() -> set:
        """Return the set of slot_time strings already booked for the day."""
        result = (
            supabase.table("interview_bookings")
            .select("slot_time")
            .eq("interview_date", INTERVIEW_BOOKING_DATE)
            .execute()
        )
        return {row["slot_time"] for row in result.data}

    @staticmethod
    def get_existing_booking(candidate_id: str):
        """Return this candidate's booking if they already have one, else None."""
        result = (
            supabase.table("interview_bookings")
            .select("*")
            .eq("candidate_id", candidate_id)
            .execute()
        )
        return result.data[0] if result.data else None

    @staticmethod
    def get_availability(candidate: dict) -> dict:
        """
        Build the data the booking page needs: each slot + whether it's free,
        plus the candidate's existing booking if any.
        """
        existing = BookingService.get_existing_booking(candidate["id"])
        taken = BookingService.get_taken_slots()

        slots = [
            {"time": slot, "available": slot not in taken}
            for slot in INTERVIEW_SLOTS
        ]
        return {
            "date": INTERVIEW_BOOKING_DATE,
            "slots": slots,
            "already_booked": existing["slot_time"] if existing else None,
        }

    # ---------- booking ----------

    @staticmethod
    def book_slot(candidate: dict, slot_time: str) -> dict:
        """
        Attempt to book slot_time for this candidate.

        Returns a dict: {"success": bool, "message": str, "slot": str|None}.

        Double-booking safety: we rely on the DB unique constraint on
        (interview_date, slot_time). If a concurrent booking already took
        the slot, our insert raises, and we report "slot just taken".
        """
        # Reject unknown slots.
        if slot_time not in INTERVIEW_SLOTS:
            return {"success": False, "message": "Invalid slot.", "slot": None}

        # If the candidate already booked, it's final — return that.
        existing = BookingService.get_existing_booking(candidate["id"])
        if existing:
            return {
                "success": False,
                "message": f"You have already booked {existing['slot_time']}.",
                "slot": existing["slot_time"],
                "already": True,
            }

        # Attempt the atomic insert. The unique constraint does the locking.
        try:
            supabase.table("interview_bookings").insert({
                "candidate_id": candidate["id"],
                "interview_date": INTERVIEW_BOOKING_DATE,
                "slot_time": slot_time,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception:
            # Either the slot was just taken, or this candidate raced
            # themselves. Figure out which for a clear message.
            taken = BookingService.get_taken_slots()
            if slot_time in taken:
                return {
                    "success": False,
                    "message": "Sorry, that slot was just taken. Please pick another.",
                    "slot": None,
                }
            return {
                "success": False,
                "message": "Could not book that slot. Please try again.",
                "slot": None,
            }

        # Booked. Advance status.
        supabase.table("candidates").update({
            "candidate_status": STATUS_INTERVIEW_CONFIRMED,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", candidate["id"]).execute()
 
        # Create the Google Calendar event + Meet link (best-effort:
        # if this fails, the booking is still confirmed).
        meet_link = CalendarService.create_interview_event(
            candidate, INTERVIEW_BOOKING_DATE, slot_time
        )
 
        # Send confirmation email with the real Meet link (or a
        # graceful fallback if the calendar step didn't return one).
        BookingService._send_confirmation_email(candidate, slot_time, meet_link)
 
        return {
            "success": True,
            "message": f"Your interview is confirmed for {slot_time}.",
            "slot": slot_time,
        }

    @staticmethod
    def _send_confirmation_email(candidate: dict, slot_time: str, meet_link: str = None) -> None:
        """Send the interview confirmation email via Phase 1 EmailService."""
        try:
            EmailService.send_email(
                candidate_id=candidate["id"],
                candidate_name=candidate["name"],
                recipient_email=candidate["email"],
                email_type="interview_confirmation",
                extra_data={
                    "interview_date": INTERVIEW_BOOKING_DATE,
                    "interview_time": slot_time,
                    "meeting_link": meet_link or "The meeting link will be shared shortly.",
                },
            )
        except Exception as e:
            print(f"[Booking] Confirmation email failed: {e}")
 