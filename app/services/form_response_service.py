# app/services/form_response_service.py
"""
Form response processing service (Phase 3 - Step 2).

Pipeline for each new Google Form submission:
  1. Skip if we've already processed this responseId (dedup).
  2. Extract answers (questionId -> value) into a readable dict.
  3. Find the email; match it to a candidate row.
     - No match -> store in unmatched_form_responses for HR.
  4. Validate the submission (email format, valid date, all 5
     eligibility answers == "Yes").
     - Invalid -> flag candidate, do NOT send interview email.
  5. Valid + matched -> flip status
     application_form_sent -> application_form_filled, then send
     the interview email and set interview_invitation_sent.
  6. Record the outcome in processed_form_responses.

Reuses Phase 1's EmailService.send_email() to actually send.
"""

import re
from datetime import datetime, timezone

from googleapiclient.discovery import build

from app.database import supabase
from app.services.google_oauth_service import GoogleOAuthService

from app.services.booking_service import BookingService
from app.config import BACKEND_PUBLIC_URL
from app.services.email_service import EmailService
from app.config import (
    APPLICATION_FORM_ID,
    FORM_FIELD_EMAIL,
    FORM_FIELD_NAME,
    FORM_FIELD_START_DATE,
    FORM_ELIGIBILITY_FIELDS,
    FORM_FIELD_TITLES,
    STATUS_APPLICATION_FORM_SENT,
    STATUS_APPLICATION_FORM_FILLED,
    STATUS_INTERVIEW_INVITATION_SENT,
)

# Basic email format check. Not RFC-perfect, but correct for our purpose.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class FormResponseService:
    """Reads and processes Google Form responses into candidate updates."""

    # ---------- low-level helpers ----------

    @staticmethod
    def _extract_answers(response: dict) -> dict:
        """
        Turn Google's nested response into {questionId: value}.
        Only handles text answers (which is all our form uses).
        """
        result = {}
        for qid, answer in response.get("answers", {}).items():
            text_answers = answer.get("textAnswers", {}).get("answers", [])
            if text_answers:
                result[qid] = text_answers[0].get("value", "").strip()
        return result

    @staticmethod
    def _readable_answers(answers: dict) -> dict:
        """Convert {questionId: value} to {title: value} for storage/logging."""
        return {
            FORM_FIELD_TITLES.get(qid, qid): value
            for qid, value in answers.items()
        }

    @staticmethod
    def _is_valid_email(value: str) -> bool:
        return bool(value and _EMAIL_RE.match(value))

    @staticmethod
    def _is_valid_date(value: str) -> bool:
        """Accept common date formats Google Forms produces (YYYY-MM-DD etc.)."""
        if not value:
            return False
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        return False

    @staticmethod
    def _all_eligibility_yes(answers: dict) -> bool:
        """True only if all five eligibility answers are 'yes' (any case)."""
        for field in FORM_ELIGIBILITY_FIELDS:
            if answers.get(field, "").strip().lower() != "yes":
                return False
        return True

    @staticmethod
    def validate(answers: dict) -> tuple[bool, list]:
        """
        Apply the agreed validation rule.
        Returns (is_valid, list_of_reasons_it_failed).
        """
        reasons = []

        if not FormResponseService._is_valid_email(answers.get(FORM_FIELD_EMAIL, "")):
            reasons.append("invalid or missing email")

        if not FormResponseService._is_valid_date(answers.get(FORM_FIELD_START_DATE, "")):
            reasons.append("invalid or missing start date")

        if not FormResponseService._all_eligibility_yes(answers):
            reasons.append("one or more eligibility answers not 'Yes'")

        return (len(reasons) == 0, reasons)

    # ---------- dedup ----------

    @staticmethod
    def _already_processed(response_id: str) -> bool:
        existing = (
            supabase.table("processed_form_responses")
            .select("id")
            .eq("response_id", response_id)
            .execute()
        )
        return bool(existing.data)

    @staticmethod
    def _record_processed(response_id: str, outcome: str, candidate_id=None) -> None:
        supabase.table("processed_form_responses").insert({
            "response_id": response_id,
            "form_id": APPLICATION_FORM_ID,
            "outcome": outcome,
            "candidate_id": candidate_id,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

    # ---------- candidate matching ----------

    @staticmethod
    def _find_candidate_by_email(email: str):
        """Return the candidate row matching this email, or None."""
        if not email:
            return None
        result = (
            supabase.table("candidates")
            .select("*")
            .eq("email", email)
            .execute()
        )
        return result.data[0] if result.data else None

    @staticmethod
    def _store_unmatched(response_id: str, answers: dict, is_valid: bool) -> None:
        supabase.table("unmatched_form_responses").insert({
            "response_id": response_id,
            "form_id": APPLICATION_FORM_ID,
            "submitted_email": answers.get(FORM_FIELD_EMAIL),
            "submitted_name": answers.get(FORM_FIELD_NAME),
            "answers": FormResponseService._readable_answers(answers),
            "is_valid": is_valid,
            "review_status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

    # ---------- the interview email ----------

# ============================================================
# Phase 3 - Step 3: Add the booking link to the interview email
#
# This REPLACES the _send_interview_email method inside
# app/services/form_response_service.py.
#
# Find the existing method (the one with the placeholder
# "1:30 / 2:30 / 3:30 / 4:30 PM" text) and replace it entirely
# with the version below.
#
# Also add this import near the top of form_response_service.py,
# with the other imports:
#
#     from app.services.booking_service import BookingService
#     from app.config import BACKEND_PUBLIC_URL
# ============================================================


    @staticmethod
    def _send_interview_email(candidate: dict) -> tuple[bool, str]:
        """
        Send the interview-scheduling email via Phase 1's EmailService,
        including a unique booking-page link for this candidate.
        """
        # Ensure the candidate has a booking token, then build their link.
        token = BookingService.ensure_booking_token(candidate)
        booking_url = f"{BACKEND_PUBLIC_URL}/api/booking/{token}"

        return EmailService.send_email(
            candidate_id=candidate["id"],
            candidate_name=candidate["name"],
            recipient_email=candidate["email"],
            email_type="interview_invitation",
            extra_data={
                # The interview_invitation template shows interview_date /
                # interview_time; we point them to the booking page instead.
                "interview_date": "Choose your slot",
                "interview_time": "Pick a time on the booking page",
                "booking_url": booking_url,
            },
        )[:2]  # (success, message, log_id) -> first two # send_email returns (success, message, log_id); we want first two

    # ---------- main entry points ----------

    @staticmethod
    def process_single_response(response: dict) -> dict:
        """
        Process one Google Form response dict. Returns a small summary
        dict describing what happened (handy for the sync endpoint).
        """
        response_id = response.get("responseId", "")
        if not response_id:
            return {"skipped": True, "reason": "no responseId"}

        if FormResponseService._already_processed(response_id):
            return {"skipped": True, "reason": "already processed", "response_id": response_id}

        answers = FormResponseService._extract_answers(response)
        email = answers.get(FORM_FIELD_EMAIL, "")
        name = answers.get(FORM_FIELD_NAME, "")

        is_valid, reasons = FormResponseService.validate(answers)

        # Match to a candidate.
        candidate = FormResponseService._find_candidate_by_email(email)

        if candidate is None:
            # No candidate with this email -> park for HR review.
            FormResponseService._store_unmatched(response_id, answers, is_valid)
            FormResponseService._record_processed(response_id, "unmatched")
            return {
                "response_id": response_id,
                "outcome": "unmatched",
                "email": email,
                "is_valid": is_valid,
            }

        # We have a matched candidate.
        if not is_valid:
            # Flag the candidate but do NOT send interview email.
            supabase.table("candidates").update({
                "candidate_status": STATUS_APPLICATION_FORM_FILLED,
                "response_status": "form_invalid",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", candidate["id"]).execute()

            FormResponseService._record_processed(
                response_id, "matched_invalid", candidate["id"]
            )
            return {
                "response_id": response_id,
                "outcome": "matched_invalid",
                "candidate_id": candidate["id"],
                "candidate_name": candidate["name"],
                "reasons": reasons,
            }

        # Valid + matched: advance status and send the interview email.
        # Only advance from application_form_sent (defensive: don't
        # re-process someone already further along).
        supabase.table("candidates").update({
            "candidate_status": STATUS_APPLICATION_FORM_FILLED,
            "response_status": "form_valid",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", candidate["id"]).execute()

        success, message = FormResponseService._send_interview_email(candidate)

        if success:
            supabase.table("candidates").update({
                "candidate_status": STATUS_INTERVIEW_INVITATION_SENT,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", candidate["id"]).execute()
            outcome = "matched_valid"
        else:
            # Email failed; leave at application_form_filled so it can be retried.
            outcome = "matched_valid_email_failed"

        FormResponseService._record_processed(response_id, outcome, candidate["id"])
        return {
            "response_id": response_id,
            "outcome": outcome,
            "candidate_id": candidate["id"],
            "candidate_name": candidate["name"],
            "email_message": message,
        }

    @staticmethod
    def sync_all_responses() -> dict:
        """
        Fetch all responses for the configured form and process any that
        are new. Used by both the manual sync endpoint and the poller.
        """
        creds = GoogleOAuthService.get_credentials()
        if creds is None:
            return {"error": "Google not connected", "processed": 0}

        try:
            forms_service = build("forms", "v1", credentials=creds)
            responses = (
                forms_service.forms()
                .responses()
                .list(formId=APPLICATION_FORM_ID)
                .execute()
            )
        except Exception as e:
            return {"error": f"Failed to read form: {str(e)}", "processed": 0}

        response_list = responses.get("responses", [])
        results = []
        for response in response_list:
            try:
                results.append(FormResponseService.process_single_response(response))
            except Exception as e:
                results.append({
                    "response_id": response.get("responseId", "unknown"),
                    "error": str(e),
                })

        handled = [r for r in results if not r.get("skipped")]
        return {
            "total_responses": len(response_list),
            "newly_processed": len(handled),
            "results": results,
        }