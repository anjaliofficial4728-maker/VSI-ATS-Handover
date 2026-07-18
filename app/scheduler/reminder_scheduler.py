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


def check_pending_candidates():
    """
    Check for pending candidates and send reminders.
    
    This job runs periodically to:
    1. Find candidates with response_status = 'pending'
    2. Check if reminder interval has elapsed
    3. Send reminder email using new generic EmailService
    4. Update follow_up_logs
    5. Respect max reminder limit (3 reminders)
    """

    try:
        response = (
            supabase
            .table("candidates")
            .select("*")
            .eq("response_status", "pending")
            .execute()
        )

        pending_candidates = response.data
        print(f"[Scheduler] Pending candidates found: {len(pending_candidates)}")

        for candidate in pending_candidates:
            try:
                # Calculate next reminder time
                if candidate["last_followup_sent_at"]:
                    reference_time = datetime.fromisoformat(
                        candidate["last_followup_sent_at"]
                    )
                else:
                    reference_time = datetime.fromisoformat(
                        candidate["initial_email_sent_at"]
                    )

                # Check if reminder interval has elapsed (1 minute for demo)
                reminder_interval = timedelta(minutes=1)
                
                if datetime.now(timezone.utc) >= reference_time + reminder_interval:
                    # Check max reminder limit
                    if candidate["followup_count"] >= 3:
                        print(
                            f"[Scheduler] Maximum reminders reached for {candidate['name']} "
                            f"(followup_count: {candidate['followup_count']})"
                        )
                        continue

                    # Send reminder using new EmailService
                    success, message, email_log_id = EmailService.send_email(
                        candidate_id=candidate["id"],
                        candidate_name=candidate["name"],
                        recipient_email=candidate["email"],
                        email_type="reminder_email",
                        extra_data=None,
                    )

                    if success:
                        # Update candidate followup count and timestamp
                        supabase.table("candidates").update({
                            "followup_count": candidate["followup_count"] + 1,
                            "last_followup_sent_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }).eq("id", candidate["id"]).execute()

                        # Add entry to follow_up_logs for tracking
                        supabase.table("followup_logs").insert({
                            "candidate_id": candidate["id"],
                            "action": "reminder_email",
                            "email_status": "sent",
                            "remarks": f"Reminder #{candidate['followup_count'] + 1} sent",
                        }).execute()

                        print(
                            f"[Scheduler] Reminder sent to {candidate['name']} "
                            f"(Reminder #{candidate['followup_count'] + 1})"
                        )
                    else:
                        print(
                            f"[Scheduler] Failed to send reminder to {candidate['name']}: {message}"
                        )

                else:
                    # Not yet time to send reminder
                    time_until_next = (reference_time + reminder_interval) - datetime.now(timezone.utc)
                    print(
                        f"[Scheduler] Skipping {candidate['name']} "
                        f"(next reminder in {time_until_next.seconds}s)"
                    )

            except Exception as e:
                print(f"[Scheduler] Error processing candidate {candidate.get('name', 'unknown')}: {str(e)}")
                continue

    except Exception as e:
        print(f"[Scheduler] Error checking pending candidates: {str(e)}")


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
