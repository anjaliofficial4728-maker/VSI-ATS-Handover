# app/schemas/email.py
"""
Email request/response schemas for validation.
Used by the email API endpoints.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class SendEmailRequest(BaseModel):
    """Request to send an email to a candidate"""
    candidate_id: str
    email_type: str  # e.g., 'application_form', 'interview_invitation'
    extra_data: Optional[Dict[str, Any]] = None
    
    class Config:
        example = {
            "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
            "email_type": "interview_invitation",
            "extra_data": {
                "interview_date": "2026-07-20",
                "interview_time": "10:00 AM",
                "meeting_link": "https://meet.google.com/xxx-xxxx-xxx"
            }
        }


class SendEmailResponse(BaseModel):
    """Response after sending email"""
    success: bool
    message: str
    email_log_id: Optional[str] = None
    error: Optional[str] = None


class EmailTypeDefinition(BaseModel):
    """Definition of an email type"""
    key: str
    name: str
    description: str
    allowed_statuses: list[str]
    subject: str
    requires_extra_data: Optional[list[str]] = None


class EmailTypesListResponse(BaseModel):
    """List of available email types"""
    email_types: list[EmailTypeDefinition]
    total: int


class EmailLogQueryParams(BaseModel):
    """Query parameters for fetching email logs"""
    candidate_id: Optional[str] = None
    email_type: Optional[str] = None
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0
