# app/scheduler/reminder_scheduler.py
"""
Reminder scheduler using APScheduler.
Updated for Phase 1 - uses new generic EmailService.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
from app.database import supabase
from app.services.email_service import EmailService
from app.services.form_response_service import FormResponseService
from app.config import FORM_POLL_INTERVAL_MINUTES



FIRST_REMINDER_DELAY = timedelta(minutes=5)
SUBSEQUENT_REMINDER_DELAY = timedelta(hours=24)
MAX_REMINDERS = 3


def parse_utc_datetime(value):
    
    """Parse a timestamp and normalize it to UTC."""
    if not value:
        return None

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def check_pending_candidates():
    """Send due reminders only while the candidate remains pending."""

    try:
        response = (
            supabase.table("candidates")
            .select("*")
            .eq("response_status", "pending")
            .execute()
        )

        candidates = response.data or []
        print(f"[Scheduler] Pending candidates found: {len(candidates)}")

        for candidate in candidates:
            try:
                candidate_id = candidate["id"]

                # Re-fetch current data because HR may have changed the status.
                latest_response = (
                    supabase.table("candidates")
                    .select("*")
                    .eq("id", candidate_id)
                    .execute()
                )

                if not latest_response.data:
                    continue

                latest = latest_response.data[0]

                # Stop reminders once HR marks the candidate as responded.
                if latest.get("response_status") != "pending":
                    print(
                        f"[Scheduler] Skipping {latest.get('name')}: "
                        "candidate is no longer pending."
                    )
                    continue

                count = int(latest.get("followup_count") or 0)

                if count >= MAX_REMINDERS:
                    print(
                        f"[Scheduler] Maximum reminders reached for "
                        f"{latest.get('name')}"
                    )
                    continue

                # First reminder: same-day behavior.
                # Later reminders: 24 hours after the previous reminder.
                if count == 0:
                    reference = latest.get("initial_email_sent_at")
                    interval = FIRST_REMINDER_DELAY
                else:
                    reference = latest.get("last_followup_sent_at")
                    interval = SUBSEQUENT_REMINDER_DELAY

                reference_time = parse_utc_datetime(reference)

                if reference_time is None:
                    print(
                        f"[Scheduler] Missing timestamp for "
                        f"{latest.get('name')}; skipping."
                    )
                    continue

                due_time = reference_time + interval

                if datetime.now(timezone.utc) < due_time:
                    print(
                        f"[Scheduler] Reminder not due for "
                        f"{latest.get('name')} until {due_time.isoformat()}"
                    )
                    continue

                # Check status and count once more immediately before sending.
                final_response = (
                    supabase.table("candidates")
                    .select("response_status,followup_count")
                    .eq("id", candidate_id)
                    .execute()
                )

                if not final_response.data:
                    continue

                final_state = final_response.data[0]
                current_count = int(final_state.get("followup_count") or 0)

                if (
                    final_state.get("response_status") != "pending"
                    or current_count != count
                    or current_count >= MAX_REMINDERS
                ):
                    print(
                        f"[Scheduler] Candidate changed before send; "
                        f"skipping {latest.get('name')}."
                    )
                    continue

                success, message, email_log_id = EmailService.send_email(
                    candidate_id=candidate_id,
                    candidate_name=latest["name"],
                    recipient_email=latest["email"],
                    email_type="reminder_email",
                    extra_data=None,
                )

                if not success:
                    print(
                        f"[Scheduler] Failed to send reminder to "
                        f"{latest.get('name')}: {message}"
                    )
                    continue

                sent_at = datetime.now(timezone.utc).isoformat()

                supabase.table("candidates").update({
                    "followup_count": current_count + 1,
                    "last_followup_sent_at": sent_at,
                    "updated_at": sent_at,
                }).eq("id", candidate_id).execute()

                supabase.table("followup_logs").insert({
                    "candidate_id": candidate_id,
                    "action": "reminder_email",
                    "email_status": "sent",
                    "remarks": f"Reminder #{current_count + 1} sent",
                }).execute()

                print(
                    f"[Scheduler] Reminder #{current_count + 1} sent "
                    f"to {latest['name']}"
                )

            except Exception as e:
                print(
                    f"[Scheduler] Error processing "
                    f"{candidate.get('name', 'unknown')}: {e}"
                )

    except Exception as e:
        print(f"[Scheduler] Error checking pending candidates: {e}")



# Initialize scheduler
scheduler = BackgroundScheduler()
def check_form_responses():
    """
    Background job: poll the Google Form for new responses and
    process them (match candidate, validate, update status,
    auto-send interview email for valid submissions).

    Safe to run repeatedly — dedup via processed_form_responses
    means already-handled submissions are skipped.
    """
    try:
        result = FormResponseService.sync_all_responses()
        if result.get("error"):
            print(f"[FormPoller] Skipped: {result['error']}")
            return
        newly = result.get("newly_processed", 0)
        if newly:
            print(f"[FormPoller] Processed {newly} new form response(s)")
        else:
            print("[FormPoller] No new form responses")
    except Exception as e:
        print(f"[FormPoller] Error: {str(e)}")



# Add job: check every minute (adjust interval as needed)
# For production: use 'hours=24' for daily reminders
scheduler.add_job(
    check_pending_candidates,
    "interval",
    minutes=1,
    id="check_pending_candidates",
    name="Check pending candidates and send reminders",
)
scheduler.add_job(
    check_form_responses,
    "interval",
    minutes=FORM_POLL_INTERVAL_MINUTES,
    id="check_form_responses",
    name="Poll Google Form for new responses",
)

# Note: Scheduler is started in main.py
