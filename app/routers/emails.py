# # app/routers/emails.py
# """
# Email API endpoints for Phase 1.
# Handles sending emails and retrieving email logs.
# """

# from fastapi import APIRouter, HTTPException, status
# from datetime import datetime



# from app.database import supabase
# from app.schemas.email import (
#     SendEmailRequest,
#     SendEmailResponse,
#     EmailTypesListResponse,
#     EmailTypeDefinition,
# )
# from app.services.email_service import EmailService
# from app.services.email_validator import EmailValidator
# from app.config import (
#     EMAIL_TYPES,
#     APPLICATION_FORM_URL,
#     STATUS_APPLICATION_FORM_SENT,
#     STATUS_SELECTED,
#     STATUS_REGISTRATION_SENT,
#     STATUS_ONBOARDING_SENT,
# )


# router = APIRouter(
#     prefix="/api/emails",
#     tags=["Emails"],
# )


# @router.post("/send", response_model=SendEmailResponse)
# async def send_email(request: SendEmailRequest):
#     """
#     Send an email to a candidate.
    
#     Args:
#         request: SendEmailRequest with candidate_id, email_type, extra_data
    
#     Returns:
#         SendEmailResponse with success status and email_log_id
    
#     Raises:
#         400: If validation fails
#         404: If candidate not found
#         500: If email sending fails
#     """
    
#     try:
#         # Step 1: Get candidate from database
#         candidate_response = supabase.table("candidates").select("*").eq(
#             "id", request.candidate_id
#         ).execute()
        
#         if not candidate_response.data or len(candidate_response.data) == 0:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Candidate with ID {request.candidate_id} not found"
#             )
        
#         candidate = candidate_response.data[0]
        
#         # Step 2: Validate email type against candidate status
#         if not EmailValidator.can_send_email(request.email_type, candidate["candidate_status"]):
#             error_msg = EmailValidator.get_validation_error(
#                 request.email_type,
#                 candidate["candidate_status"]
#             )
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=error_msg
#             )
        
#         # Auto-fill the application form URL so HR doesn't type it.
#         # It's the same form for every candidate.
#         if request.email_type == "application_form":
#             if request.extra_data is None:
#                 request.extra_data = {}
#             if not request.extra_data.get("form_url"):
#                 request.extra_data["form_url"] = APPLICATION_FORM_URL
        
#         # Step 3: Send email through service
#         success, message, email_log_id = EmailService.send_email(
#             candidate_id=request.candidate_id,
#             candidate_name=candidate["name"],
#             recipient_email=candidate["email"],
#             email_type=request.email_type,
#             extra_data=request.extra_data,
#         )
        
#         if not success:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=message
#             )
        
#         # Step 4: Update candidate status if email sent successfully
#         # For now, just update response_status to "pending" for selection emails
#         if request.email_type == "selection_email":
#             supabase.table("candidates").update({
#                 "response_status": "pending",
#                 "initial_email_sent_at": datetime.utcnow().isoformat(),
#                 "updated_at": datetime.utcnow().isoformat(),
#             }).eq("id", request.candidate_id).execute()
            
#             # Add to follow_up_logs for tracking
#             supabase.table("followup_logs").insert({
#                 "candidate_id": request.candidate_id,
#                 "action": "selection_email",
#                 "email_status": "sent",
#                 "remarks": "Selection email sent",
#             }).execute()
#         if request.email_type == "application_form":
#             supabase.table("candidates").update({
#             "candidate_status": STATUS_APPLICATION_FORM_SENT,
#             "updated_at": datetime.utcnow().isoformat(),
#         }).eq("id", request.candidate_id).execute()
            
            
#        # Selection email sent -> candidate is now "selected".
#         if request.email_type == "selection_email":
#             supabase.table("candidates").update({
#                 "candidate_status": STATUS_SELECTED,
#                 "updated_at": datetime.utcnow().isoformat(),
#             }).eq("id", request.candidate_id).execute()
 
#         # Registration email (with PDF) sent -> "registration_sent".
#         # HR will manually mark registration_form_filled once the
#         # candidate emails back the scanned form.
#         if request.email_type == "registration_form":
#             supabase.table("candidates").update({
#                 "candidate_status": STATUS_REGISTRATION_SENT,
#                 "updated_at": datetime.utcnow().isoformat(),
#             }).eq("id", request.candidate_id).execute()
 
#         # Onboarding email sent -> "onboarding_sent" (final step).
#         if request.email_type == "onboarding_email":
#             supabase.table("candidates").update({
#                 "candidate_status": STATUS_ONBOARDING_SENT,
#                 "updated_at": datetime.utcnow().isoformat(),
#             }).eq("id", request.candidate_id).execute()
 
        
#         return SendEmailResponse(
#             success=True,
#             message=message,
#             email_log_id=email_log_id,
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Unexpected error: {str(e)}"
#         )


# @router.get("/logs/{candidate_id}")
# async def get_email_logs(candidate_id: str, limit: int = 50, offset: int = 0):
#     """
#     Get email logs for a candidate.
    
#     Args:
#         candidate_id: ID of candidate
#         limit: Number of records to return
#         offset: Number of records to skip
    
#     Returns:
#         List of email logs
#     """
    
#     try:
#         # Verify candidate exists
#         candidate_response = supabase.table("candidates").select("id").eq(
#             "id", candidate_id
#         ).execute()
        
#         if not candidate_response.data or len(candidate_response.data) == 0:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Candidate with ID {candidate_id} not found"
#             )
        
#         # Get email logs
#         response = supabase.table("email_logs").select("*").eq(
#             "candidate_id", candidate_id
#         ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
#         return {
#             "data": response.data,
#             "total": len(response.data),
#             "limit": limit,
#             "offset": offset,
#         }
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error fetching email logs: {str(e)}"
#         )


# @router.get("/logs")
# async def get_all_email_logs(
#     email_type: str = None,
#     status: str = None,
#     limit: int = 50,
#     offset: int = 0
# ):
#     """
#     Get all email logs with optional filtering.
    
#     Args:
#         email_type: Filter by email type
#         status: Filter by status (sent, failed, pending)
#         limit: Number of records to return
#         offset: Number of records to skip
    
#     Returns:
#         List of email logs
#     """
    
#     try:
#         query = supabase.table("email_logs").select("*")
        
#         if email_type:
#             query = query.eq("email_type", email_type)
        
#         if status:
#             query = query.eq("status", status)
        
#         response = query.order("created_at", desc=True).range(
#             offset, offset + limit - 1
#         ).execute()
        
#         return {
#             "data": response.data,
#             "total": len(response.data),
#             "limit": limit,
#             "offset": offset,
#         }
    
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error fetching email logs: {str(e)}"
#         )


# @router.get("/types")
# async def get_email_types() -> EmailTypesListResponse:
#     """
#     Get list of available email types.
    
#     Returns:
#         List of email type definitions with descriptions
#     """
    
#     try:
#         email_types = [
#             EmailTypeDefinition(
#                 key=key,
#                 name=value["name"],
#                 description=value["description"],
#                 allowed_statuses=value["allowed_statuses"],
#                 subject=value["subject"],
#                 requires_extra_data=value.get("requires_extra_data", []),
#             )
#             for key, value in EMAIL_TYPES.items()
#         ]
        
#         return EmailTypesListResponse(
#             email_types=email_types,
#             total=len(email_types),
#         )
    
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error fetching email types: {str(e)}"
#         )


# @router.get("/types/{email_type}")
# async def get_email_type_info(email_type: str):
#     """
#     Get detailed information about a specific email type.
    
#     Args:
#         email_type: Email type key
    
#     Returns:
#         Email type definition
#     """
    
#     try:
#         if email_type not in EMAIL_TYPES:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Email type '{email_type}' not found"
#             )
        
#         email_def = EMAIL_TYPES[email_type]
        
#         return EmailTypeDefinition(
#             key=email_type,
#             name=email_def["name"],
#             description=email_def["description"],
#             allowed_statuses=email_def["allowed_statuses"],
#             subject=email_def["subject"],
#             requires_extra_data=email_def.get("requires_extra_data", []),
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error fetching email type: {str(e)}"
#         )
# app/routers/emails.py
"""
Email API endpoints for Phase 1.
Handles sending emails and retrieving email logs.
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime



from app.database import supabase
from app.schemas.email import (
    SendEmailRequest,
    SendEmailResponse,
    EmailTypesListResponse,
    EmailTypeDefinition,
)
from app.services.email_service import EmailService
from app.services.email_validator import EmailValidator
from app.config import (
    EMAIL_TYPES,
    APPLICATION_FORM_URL,
    APPLICATION_FORM_FULL_TIME_URL,
    STATUS_APPLICATION_FORM_SENT,
    STATUS_SELECTED,
    STATUS_REGISTRATION_SENT,
    STATUS_ONBOARDING_SENT,
)


router = APIRouter(
    prefix="/api/emails",
    tags=["Emails"],
)


@router.post("/send", response_model=SendEmailResponse)
async def send_email(request: SendEmailRequest):
    """
    Send an email to a candidate.
    
    Args:
        request: SendEmailRequest with candidate_id, email_type, extra_data
    
    Returns:
        SendEmailResponse with success status and email_log_id
    
    Raises:
        400: If validation fails
        404: If candidate not found
        500: If email sending fails
    """
    
    try:
        # Step 1: Get candidate from database
        candidate_response = supabase.table("candidates").select("*").eq(
            "id", request.candidate_id
        ).execute()
        
        if not candidate_response.data or len(candidate_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {request.candidate_id} not found"
            )
        
        candidate = candidate_response.data[0]
        
        # Step 2: Validate email type against candidate status
        if not EmailValidator.can_send_email(request.email_type, candidate["candidate_status"]):
            error_msg = EmailValidator.get_validation_error(
                request.email_type,
                candidate["candidate_status"]
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Auto-fill the correct application form URL so HR doesn't need to paste it.
        # Full-time submissions are reviewed manually in the linked Google Sheet.
        if request.email_type in ("application_form", "application_form_full_time"):
            if request.extra_data is None:
                request.extra_data = {}
            if not request.extra_data.get("form_url"):
                request.extra_data["form_url"] = (
                    APPLICATION_FORM_FULL_TIME_URL
                    if request.email_type == "application_form_full_time"
                    else APPLICATION_FORM_URL
                )
        
        # Step 3: Send email through service
        success, message, email_log_id = EmailService.send_email(
            candidate_id=request.candidate_id,
            candidate_name=candidate["name"],
            recipient_email=candidate["email"],
            email_type=request.email_type,
            extra_data=request.extra_data,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=message
            )
        
        # Step 4: Update candidate status if email sent successfully
        # For now, just update response_status to "pending" for selection emails
        if request.email_type == "selection_email":
            supabase.table("candidates").update({
                "response_status": "pending",
                "initial_email_sent_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", request.candidate_id).execute()
            
            # Add to follow_up_logs for tracking
            supabase.table("followup_logs").insert({
                "candidate_id": request.candidate_id,
                "action": "selection_email",
                "email_status": "sent",
                "remarks": "Selection email sent",
            }).execute()
        if request.email_type in ("application_form", "application_form_full_time"):
            supabase.table("candidates").update({
            "candidate_status": STATUS_APPLICATION_FORM_SENT,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", request.candidate_id).execute()
            
            
       # Selection email sent -> candidate is now "selected".
        if request.email_type == "selection_email":
            supabase.table("candidates").update({
                "candidate_status": STATUS_SELECTED,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", request.candidate_id).execute()
 
        # Registration email (with PDF) sent -> "registration_sent".
        # HR will manually mark registration_form_filled once the
        # candidate emails back the scanned form.
        if request.email_type == "registration_form":
            supabase.table("candidates").update({
                "candidate_status": STATUS_REGISTRATION_SENT,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", request.candidate_id).execute()
 
        # Onboarding email sent -> "onboarding_sent" (final step).
        if request.email_type == "onboarding_email":
            supabase.table("candidates").update({
                "candidate_status": STATUS_ONBOARDING_SENT,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", request.candidate_id).execute()
 
        
        return SendEmailResponse(
            success=True,
            message=message,
            email_log_id=email_log_id,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/logs/{candidate_id}")
async def get_email_logs(candidate_id: str, limit: int = 50, offset: int = 0):
    """
    Get email logs for a candidate.
    
    Args:
        candidate_id: ID of candidate
        limit: Number of records to return
        offset: Number of records to skip
    
    Returns:
        List of email logs
    """
    
    try:
        # Verify candidate exists
        candidate_response = supabase.table("candidates").select("id").eq(
            "id", candidate_id
        ).execute()
        
        if not candidate_response.data or len(candidate_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {candidate_id} not found"
            )
        
        # Get email logs
        response = supabase.table("email_logs").select("*").eq(
            "candidate_id", candidate_id
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "data": response.data,
            "total": len(response.data),
            "limit": limit,
            "offset": offset,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching email logs: {str(e)}"
        )


@router.get("/logs")
async def get_all_email_logs(
    email_type: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get all email logs with optional filtering.
    
    Args:
        email_type: Filter by email type
        status: Filter by status (sent, failed, pending)
        limit: Number of records to return
        offset: Number of records to skip
    
    Returns:
        List of email logs
    """
    
    try:
        query = supabase.table("email_logs").select("*")
        
        if email_type:
            query = query.eq("email_type", email_type)
        
        if status:
            query = query.eq("status", status)
        
        response = query.order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()
        
        return {
            "data": response.data,
            "total": len(response.data),
            "limit": limit,
            "offset": offset,
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching email logs: {str(e)}"
        )


@router.get("/types")
async def get_email_types() -> EmailTypesListResponse:
    """
    Get list of available email types.
    
    Returns:
        List of email type definitions with descriptions
    """
    
    try:
        email_types = [
            EmailTypeDefinition(
                key=key,
                name=value["name"],
                description=value["description"],
                allowed_statuses=value["allowed_statuses"],
                subject=value["subject"],
                requires_extra_data=value.get("requires_extra_data", []),
            )
            for key, value in EMAIL_TYPES.items()
        ]
        
        return EmailTypesListResponse(
            email_types=email_types,
            total=len(email_types),
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching email types: {str(e)}"
        )


@router.get("/types/{email_type}")
async def get_email_type_info(email_type: str):
    """
    Get detailed information about a specific email type.
    
    Args:
        email_type: Email type key
    
    Returns:
        Email type definition
    """
    
    try:
        if email_type not in EMAIL_TYPES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email type '{email_type}' not found"
            )
        
        email_def = EMAIL_TYPES[email_type]
        
        return EmailTypeDefinition(
            key=email_type,
            name=email_def["name"],
            description=email_def["description"],
            allowed_statuses=email_def["allowed_statuses"],
            subject=email_def["subject"],
            requires_extra_data=email_def.get("requires_extra_data", []),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching email type: {str(e)}"
        )
