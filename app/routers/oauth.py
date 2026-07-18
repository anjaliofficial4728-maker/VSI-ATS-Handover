# app/routers/oauth.py
"""
Google OAuth API endpoints.

Flow:
  1. Frontend opens  GET /api/oauth/google/authorize
     -> we redirect the browser to Google's login/consent screen.
  2. Google redirects back to  GET /api/oauth/google/callback?code=...
     -> we exchange the code, store the encrypted token, then
        redirect the browser to the frontend success page.
  3. Frontend can check  GET /api/oauth/google/status
     -> tells it whether Google is connected.

Plus a temporary verification endpoint:
     GET /api/oauth/google/test-form
     -> reads the configured form and returns its responses,
        so we can confirm OAuth + Forms API work before building
        anything on top. Remove or lock this down later.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from googleapiclient.discovery import build

from app.services.google_oauth_service import GoogleOAuthService
from app.config import APPLICATION_FORM_ID, OAUTH_SUCCESS_REDIRECT
from app.services.form_response_service import FormResponseService

router = APIRouter(
    prefix="/api/oauth/google",
    tags=["Google OAuth"],
)


@router.get("/authorize")
def authorize():
    """Redirect the user to Google's consent screen."""
    try:
        auth_url = GoogleOAuthService.build_authorization_url()
        return RedirectResponse(url=auth_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build authorization URL: {str(e)}",
        )


@router.get("/callback")
def callback(code: str = None, error: str = None):
    """
    Google redirects here after the user grants (or denies) access.
    On success we store the token and bounce back to the frontend.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google returned an error: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No authorization code provided by Google.",
        )

    try:
        account_email = GoogleOAuthService.exchange_code_and_store(code)
        print(f"[OAuth] Connected Google account: {account_email}")
        # Send the browser back to the frontend.
        return RedirectResponse(url=f"{OAUTH_SUCCESS_REDIRECT}?google_connected=1")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete OAuth: {str(e)}",
        )


@router.get("/status")
def connection_status():
    """Report whether a Google account is connected."""
    connected = GoogleOAuthService.is_connected()
    return {"connected": connected}


@router.get("/test-form")
def test_form_read():
    """
    TEMPORARY verification endpoint.

    Reads the configured application form's metadata and its
    responses, proving OAuth + Forms API work end to end.
    """
    creds = GoogleOAuthService.get_credentials()
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google is not connected. Visit /api/oauth/google/authorize first.",
        )

    try:
        forms_service = build("forms", "v1", credentials=creds)

        # Form structure (question titles, etc.)
        form_meta = forms_service.forms().get(formId=APPLICATION_FORM_ID).execute()

        # All submitted responses.
        responses = (
            forms_service.forms()
            .responses()
            .list(formId=APPLICATION_FORM_ID)
            .execute()
        )

        response_list = responses.get("responses", [])

        return {
            "form_title": form_meta.get("info", {}).get("title", "(untitled)"),
            "question_count": len(form_meta.get("items", [])),
            "response_count": len(response_list),
            "responses": response_list,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read form: {str(e)}",
        )


@router.get("/form-schema")
def form_schema():
    """
    TEMPORARY helper.

    Returns the mapping of questionId -> question title for the
    configured form, so we know which answer is the email, name, etc.
    Used once to build Step 2's field mapping. Remove later.
    """
    creds = GoogleOAuthService.get_credentials()
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google is not connected. Visit /api/oauth/google/authorize first.",
        )

    try:
        forms_service = build("forms", "v1", credentials=creds)
        form_meta = forms_service.forms().get(formId=APPLICATION_FORM_ID).execute()

        mapping = []
        for item in form_meta.get("items", []):
            title = item.get("title", "(no title)")
            question = item.get("questionItem", {}).get("question", {})
            question_id = question.get("questionId")
            if question_id:
                mapping.append({"questionId": question_id, "title": title})

        return {
            "form_title": form_meta.get("info", {}).get("title", "(untitled)"),
            "questions": mapping,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read form schema: {str(e)}",
        )
# ============================================================
# Phase 3 - Step 2: Form sync endpoints
#
# COPY the two route functions below and PASTE them at the
# BOTTOM of your existing app/routers/oauth.py (below the
# /form-schema endpoint).
#
# Also add this import near the top of oauth.py, with the
# other imports:
#
#     from app.services.form_response_service import FormResponseService
# ============================================================


@router.post("/sync-responses")
def sync_responses():
    """
    Manually trigger processing of all form responses.
    Reads the form, processes any new submissions (match, validate,
    update status, send interview email), and returns a summary.
    """
    result = FormResponseService.sync_all_responses()
    if result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )
    return result


@router.get("/unmatched-responses")
def get_unmatched_responses():
    """
    List form submissions whose email didn't match any candidate,
    for HR to review.
    """
    from app.database import supabase
    result = (
        supabase.table("unmatched_form_responses")
        .select("*")
        .eq("review_status", "pending")
        .order("created_at", desc=True)
        .execute()
    )
    return {"count": len(result.data), "responses": result.data}