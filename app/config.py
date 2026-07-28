# app/config.py
"""
Configuration for the application.
Includes email type definitions for Phase 1.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path as _Path

# Load environment variables from backend/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# ============== Supabase Configuration ==============
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ============== Email Configuration ==============
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")       # HR email verified in Brevo
SENDER_NAME = os.getenv("SENDER_NAME", "HR Team")

# ============== Email Type Definitions ==============
# These define the workflow for each email type
EMAIL_TYPES = {
    "application_form": {
        "key": "application_form",
        "name": "Application Form Email",
        "description": "Send application form to new applicants",
        "allowed_statuses": ["applied"],
        "subject": "Complete Your Application - {{company_name}}",
        "requires_extra_data": ["form_url"],
        "template": "application_form.html"
    },
    "interview_invitation": {
        "key": "interview_invitation",
        "name": "Interview Invitation Email",
        "description": "Invite candidate to interview",
        "allowed_statuses": ["applied", "screening_passed"],
        "subject": "Interview Invitation - {{company_name}}",
        "requires_extra_data": ["interview_date", "interview_time"],
        "template": "interview_invitation.html"
    },
    "interview_confirmation": {
        "key": "interview_confirmation",
        "name": "Interview Confirmation Email",
        "description": "Confirm interview details and meeting link",
        "allowed_statuses": ["interview_scheduled"],
        "subject": "Interview Confirmed - {{company_name}}",
        "requires_extra_data": ["interview_date", "interview_time", "meeting_link"],
        "template": "interview_confirmation.html"
    },

    "selection_email": {
        "key": "selection_email",
        "name": "Selection Email",
        "description": "Send selection offer to an interview-cleared candidate",
        "allowed_statuses": ["interview_cleared"],
        "subject": "Congratulations! You've Been Selected - {{company_name}}",
        "requires_extra_data": ["role"],
        "template": "selection_email.html"
    },


    "registration_form": {
        "key": "registration_form",
        "name": "Registration Form Email",
        "description": "Send the registration form PDF to a selected candidate",
        "allowed_statuses": ["selected"],
        "subject": "Registration Form - {{company_name}}",
        "requires_extra_data": [],
        "template": "registration_form.html"
    },


    "onboarding_email": {
        "key": "onboarding_email",
        "name": "Onboarding Email",
        "description": "Send onboarding resources to a registered candidate",
        "allowed_statuses": ["registration_form_filled"],
        "subject": "Welcome to VSI - Onboarding Details - {{company_name}}",
        "requires_extra_data": [],
        "template": "onboarding_email.html"
    },


    "reminder_email": {
        "key": "reminder_email",
        "name": "Reminder Email",
        "description": "Send reminder about pending response",
        "allowed_statuses": ["applied", "interview_scheduled", "selected"],
        "subject": "Reminder: Your Response is Pending - {{company_name}}",
        "requires_extra_data": [],
        "template": "reminder_email.html"
    }
}

# ============== Candidate Status Mapping ==============
# Valid candidate statuses in the system
VALID_CANDIDATE_STATUSES = [
    "applied",
    "screening_passed",
    "interview_scheduled",
    "interview_passed",
    # ---- Phase 3 additions ----
    "application_form_sent",
    "application_form_filled",
    "interview_invitation_sent",
    "interview_confirmed",
    "interview_cleared",
    "selected",
    "registration_sent",
    "registration_form_filled",
    "onboarding_sent",
    # ---- original tail ----
    "hired",
    "rejected",
]
 

# ============== Email Status Constants ==============
EMAIL_STATUS_PENDING = "pending"
EMAIL_STATUS_SENT = "sent"
EMAIL_STATUS_FAILED = "failed"

VALID_EMAIL_STATUSES = [EMAIL_STATUS_PENDING, EMAIL_STATUS_SENT, EMAIL_STATUS_FAILED]

# ============== Validation ==============
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env")

if not BREVO_API_KEY or not SENDER_EMAIL:
    raise ValueError("Brevo email credentials not found in .env")

# ============== Optional Configuration ==============
# Company name used in email templates
COMPANY_NAME = os.getenv("COMPANY_NAME", "Virtual Solutions India")

# Email retry settings
EMAIL_RETRY_ATTEMPTS = int(os.getenv("EMAIL_RETRY_ATTEMPTS", "3"))
EMAIL_RETRY_DELAY = int(os.getenv("EMAIL_RETRY_DELAY", "5"))  # seconds

# Template directory
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
# ============================================================
# Phase 3 - Step 1: Google OAuth configuration
#
#     DO NOT create a new config.py with only this content.
#     COPY the block below and PASTE it at the BOTTOM of your
#     existing app/config.py (the one that already has
#     SUPABASE_URL, BREVO_API_KEY, EMAIL_TYPES, etc).
#
#     Your existing config.py already does `import os` and
#     `from dotenv import load_dotenv` + `load_dotenv()` near
#     the top, so you do NOT need to add those again.
# ============================================================


# ---- Google OAuth credentials (from Google Cloud Console) ----
# These come from the OAuth client you created ("vsi-backend").
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Must match EXACTLY the redirect URI you registered in the
# Google Cloud Console OAuth client. Character for character.
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/api/oauth/google/callback",
)

# The scopes we request. Read-only for forms; read/write for
# calendar (needed later to create the Meet event). Nothing here
# can edit or delete your form.
GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/forms.body.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# The single Google account we connect during development.
# Set this to the Gmail address you used to create the form and
# the Cloud project. Later, to switch to the HR account, you only
# change this value (and re-authorize) — no code changes.
GOOGLE_ACCOUNT_EMAIL = os.getenv("GOOGLE_ACCOUNT_EMAIL", "")

# The form we read application responses from (the /edit-URL id).
APPLICATION_FORM_ID = os.getenv(
    "APPLICATION_FORM_ID",
    "1dkK8Gmtdwgtg_dvsi-Dx3u9FynR0x0bpLMDCHxeXSyc",
)

# Fernet key used to encrypt the OAuth token before storing it in
# Supabase. Generate ONE key and keep it stable — if it changes,
# previously stored tokens can't be decrypted and you'll have to
# reconnect. Generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")

# Where to send the user's browser after a successful connect.
# Points back to your frontend so they see a friendly page.
OAUTH_SUCCESS_REDIRECT = os.getenv(
    "OAUTH_SUCCESS_REDIRECT",
    "http://localhost:5174/",
)
# ============================================================
# Phase 3 - Step 2: Form field mapping & status config
#
# COPY the block below and PASTE it at the BOTTOM of your
# existing app/config.py (below the Step 1 Google block you
# already added).
# ============================================================


# ---- Application form question-ID -> meaning mapping ----
# IDs from the NEW form (Internship application form), via /form-schema.
FORM_FIELD_EMAIL = "61c73e81"          # "Email"
FORM_FIELD_NAME = "6a2f8ab5"           # "Name"
FORM_FIELD_START_DATE = "20c8a719"     # "When can you start?"

# The five eligibility questions that must all be "Yes" for a
# submission to count as valid.
FORM_FIELD_TIMINGS_OK = "033f6ddd"       # 10 AM-5 PM timings?
FORM_FIELD_UNPAID_OK = "79a53575"        # 3-month unpaid structure?
FORM_FIELD_CONTINUATION_OK = "7779e121"  # performance-based continuation?
FORM_FIELD_HAS_LAPTOP = "12e6c36a"       # own laptop?
FORM_FIELD_HAS_INTERNET = "09fdfdff"     # stable internet?

# All the "must be Yes" eligibility fields, checked together.
FORM_ELIGIBILITY_FIELDS = [
    FORM_FIELD_TIMINGS_OK,
    FORM_FIELD_UNPAID_OK,
    FORM_FIELD_CONTINUATION_OK,
    FORM_FIELD_HAS_LAPTOP,
    FORM_FIELD_HAS_INTERNET,
]

# Full ID -> human title map, for logging / readable answers.
FORM_FIELD_TITLES = {
    "6a2f8ab5": "Name",
    "61c73e81": "Email",
    "11c2cd54": "Phone number",
    "15cce698": "Current City",
    "4bcca2a0": "Year of graduation",
    "32ccbbdd": "Preferred Internship Duration",
    "40410bc5": "Position(s) interested in",
    "033f6ddd": "OK with 10-5 timings",
    "79a53575": "OK with 3-month unpaid structure",
    "7779e121": "OK with performance-based continuation",
    "479d70c1": "Why join this internship",
    "12e6c36a": "Has own laptop",
    "09fdfdff": "Stable internet",
    "20c8a719": "When can you start",
}


# ---- New candidate statuses introduced by the form workflow ----
# Phase 1 already had: applied, screening_passed, interview_scheduled,
# interview_passed, selected, hired, rejected.
# These extend the pipeline for the form/interview flow.
STATUS_APPLICATION_FORM_SENT = "application_form_sent"
STATUS_APPLICATION_FORM_FILLED = "application_form_filled"
STATUS_INTERVIEW_INVITATION_SENT = "interview_invitation_sent"

# How often the background poller checks for new form responses.
FORM_POLL_INTERVAL_MINUTES = int(os.getenv("FORM_POLL_INTERVAL_MINUTES", "5"))
# ============================================================
# Phase 3 - Step 3: Booking configuration
#
# COPY the block below and PASTE it at the BOTTOM of your
# existing app/config.py (below the Step 2 block).
# ============================================================

import datetime as _dt

# The interview time slots offered on the booking page (1:1).
INTERVIEW_SLOTS = ["1:30 PM", "2:30 PM", "3:30 PM", "4:30 PM"]

# The single bookable day. Defaults to tomorrow (computed at import).
# You can override with a fixed date via env, format YYYY-MM-DD.
_env_date = os.getenv("INTERVIEW_BOOKING_DATE", "")
if _env_date:
    INTERVIEW_BOOKING_DATE = _env_date
else:
    INTERVIEW_BOOKING_DATE = (
        _dt.date.today() + _dt.timedelta(days=1)
    ).isoformat()

# Public base URL of the BACKEND, used to build the booking link
# placed in the interview email. Locally this is localhost:8000;
# in production set BACKEND_PUBLIC_URL to your Railway URL.
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://vsi-ats-handover.onrender.com")

# New status set when a candidate confirms their interview slot.
STATUS_INTERVIEW_CONFIRMED = "interview_confirmed"
# ============================================================
# Auto-fill form URL + auto-advance status
#
# COPY this block and PASTE it at the BOTTOM of app/config.py
# (below your Step 3 booking block).
# ============================================================

# The single application form URL sent to every candidate.
# Because it's the same form for everyone, we store it here so HR
# doesn't have to paste it each time. Override per-environment via
# the APPLICATION_FORM_URL env var if the form link ever changes.
APPLICATION_FORM_URL = os.getenv(
    "APPLICATION_FORM_URL",
    "https://forms.gle/b8q8k5xa7JoY2Sup8",
)
# ============================================================
# Phase 3 - Step 4: Calendar configuration
#
# COPY the block below and PASTE it at the BOTTOM of app/config.py
# (below the auto-fill / APPLICATION_FORM_URL block).
# ============================================================

# Timezone for interview calendar events. Mumbai / India = Asia/Kolkata.
INTERVIEW_TIMEZONE = os.getenv("INTERVIEW_TIMEZONE", "Asia/Kolkata")

# Interview length in minutes (used to compute the event end time).
INTERVIEW_DURATION_MINUTES = int(os.getenv("INTERVIEW_DURATION_MINUTES", "45"))

 
# Path to the registration form PDF that gets attached to the
# registration email. Place the file here in your backend.
REGISTRATION_FORM_PDF_PATH = str(
    _Path(__file__).resolve().parent / "assets" / "Registration_Form.pdf"
)
 
# Statuses set after each Step 5/6 email sends successfully.
STATUS_SELECTED = "selected"
STATUS_REGISTRATION_SENT = "registration_sent"
STATUS_ONBOARDING_SENT = "onboarding_sent"
 